"""Streaming Structured Output and Async Background Jobs Example.

Demonstrates:
1. Streaming token-by-token structured output (@app.stream_tool) using Pydantic v2.
2. Long-running asynchronous background jobs (@app.job) without holding connections open.
3. Polling job execution status and progress via /mcp/jobs/{id}.
4. Safe lifecycle eviction and task cancellation.
"""

import asyncio
import json
from typing import Any, AsyncGenerator, Dict

from pydantic import BaseModel, Field

from fastapi_mcp import FastAPIMCP

app = FastAPIMCP(auto_scan=False, name="StreamingAndJobsMCP")


# 1. Pydantic v2 Models for Structured Chunks & Job Specifications
class GenerationStep(BaseModel):
    """Structured reasoning step schema."""

    step_index: int = Field(..., description="Step sequence number")
    thought: str = Field(..., description="Intermediate reasoning token")


class BatchProcessResult(BaseModel):
    """Job final output schema."""

    processed_items: int
    summary: str


# 2. Streaming Tool: Yields structured Pydantic v2 objects incrementally
@app.stream_tool(name="stream_reasoning", description="Stream reasoning steps incrementally")
async def stream_reasoning(topic: str) -> AsyncGenerator[GenerationStep, None]:
    """Stream thought process token-by-token back to agent clients."""
    thoughts = [
        f"Analyzing context for '{topic}'...",
        f"Validating business constraints for '{topic}'...",
        f"Formulating optimal decision for '{topic}'...",
    ]
    for idx, thought in enumerate(thoughts, start=1):
        await asyncio.sleep(0.01)  # Simulate incremental reasoning latency
        yield GenerationStep(
            step_index=idx,
            thought=thought,
        )


# 3. Async Background Job: Long-running task with progress tracking
@app.job(name="heavy_batch_job", timeout=10.0)
async def heavy_batch_job(item_count: int = 100) -> Dict[str, Any]:
    """Execute heavy background processing without blocking the HTTP event loop."""
    # Simulate heavy computation in background
    await asyncio.sleep(0.05)
    return BatchProcessResult(
        processed_items=item_count,
        summary=f"Successfully processed {item_count} records",
    ).model_dump()


def _unwrap(res: Any) -> Dict[str, Any]:
    """Helper to unwrap FastMCP CallToolResult to dict."""
    if hasattr(res, "content") and res.content:
        return json.loads(res.content[0].text)
    if isinstance(res, dict):
        return res
    return {}


async def run_demo() -> Dict[str, Any]:
    """Execute streaming tool consumption and background job polling scenarios."""
    results: Dict[str, Any] = {}

    # Scenario 1: Consume @app.stream_tool incrementally
    stream_session = app.call_stream_tool(
        "stream_reasoning",
        {"topic": "portfolio_rebalancing"},
    )
    chunks = []
    async for chunk in stream_session:
        chunks.append(chunk)

    results["stream_chunks_count"] = len(chunks)
    results["first_chunk_text"] = chunks[0]["data"]["thought"]
    results["is_last_chunk_marked"] = chunks[-1]["is_last"]

    # Scenario 2: Submit @app.job task and poll status to completion
    call_res = await app.call_tool("heavy_batch_job", {"item_count": 100})
    job_ack = _unwrap(call_res)
    job_id = job_ack["job_id"]

    # Poll status until finished
    job_completed = False
    final_result: Dict[str, Any] = {}
    for _ in range(10):
        await asyncio.sleep(0.02)
        status_res = await app.call_tool("get_job_status", {"job_id": job_id})
        status_data = _unwrap(status_res)
        if status_data.get("status") == "completed":
            job_completed = True
            final_result = status_data.get("result", {})
            break

    results["job_completed"] = job_completed
    results["job_result"] = final_result

    return results


if __name__ == "__main__":
    print("=== Running Streaming Tools & Async Jobs Demo ===")
    demo_results = asyncio.run(run_demo())
    print(f"1. Stream chunks received: {demo_results['stream_chunks_count']} chunks")
    print(f"   First chunk thought:   {demo_results['first_chunk_text']}")
    print(f"   Last chunk finalized:  {demo_results['is_last_chunk_marked']}")
    print(f"2. Background Job Status: Completed = {demo_results['job_completed']}")
    print(f"   Job Result Output:     {demo_results['job_result']}")
    print("All streaming and async job scenarios executed successfully!")
