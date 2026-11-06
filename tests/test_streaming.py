"""Comprehensive TDD tests for Streaming Structured Output (@app.stream_tool) in v0.5.0."""

import asyncio
import json
from typing import Any, Dict
import pytest
from pydantic import BaseModel
from fastapi_mcp import FastAPIMCP, StreamToolSession, collect_stream


def _unwrap(res: Any) -> Dict[str, Any]:
    """Helper to unwrap FastMCP CallToolResult to dict."""
    if hasattr(res, "content") and res.content:
        return json.loads(res.content[0].text)
    if isinstance(res, dict):
        return res
    return {}


class LogRecord(BaseModel):
    timestamp: str
    level: str
    message: str


@pytest.mark.asyncio
async def test_streaming_tool_sequential_chunks():
    """Verify stream_tool yields chunks sequentially with chunk_id metadata."""
    app = FastAPIMCP(auto_scan=False)

    @app.stream_tool(name="tail_logs")
    async def tail_logs(count: int):
        for i in range(count):
            yield {"index": i, "text": f"log line {i}"}

    session = app.call_stream_tool("tail_logs", {"count": 3})
    chunks = []
    async for chunk in session:
        chunks.append(chunk)

    assert len(chunks) == 3
    assert chunks[0]["chunk_id"] == 1
    assert chunks[0]["data"]["index"] == 0
    assert chunks[2]["chunk_id"] == 3
    assert chunks[2]["data"]["index"] == 2


@pytest.mark.asyncio
async def test_streaming_tool_typed_pydantic_models():
    """Verify Pydantic models yielded by generator are automatically serialized to dict."""
    app = FastAPIMCP(auto_scan=False)

    @app.stream_tool(name="stream_typed_logs")
    async def stream_typed_logs():
        yield LogRecord(timestamp="2026-11-03T00:00:00Z", level="INFO", message="Booting")
        yield LogRecord(timestamp="2026-11-03T00:00:01Z", level="WARN", message="High latency")

    session = app.call_stream_tool("stream_typed_logs")
    records = []
    async for chunk in session:
        records.append(chunk["data"])

    assert len(records) == 2
    assert records[0]["level"] == "INFO"
    assert records[1]["level"] == "WARN"


@pytest.mark.asyncio
async def test_streaming_tool_early_abort_aclose():
    """Verify early client termination calls aclose() and triggers generator cleanup."""
    app = FastAPIMCP(auto_scan=False)
    cleaned_up = False

    @app.stream_tool(name="infinite_stream")
    async def infinite_stream():
        nonlocal cleaned_up
        try:
            val = 0
            while True:
                yield {"val": val}
                val += 1
                await asyncio.sleep(0.01)
        finally:
            cleaned_up = True

    session = app.call_stream_tool("infinite_stream")
    async for chunk in session:
        assert chunk["chunk_id"] == 1
        break
    await session.aclose()

    await asyncio.sleep(0.05)
    assert cleaned_up is True

    # Iterating over closed session yields nothing
    with pytest.raises(StopAsyncIteration):
        await session.__anext__()


@pytest.mark.asyncio
async def test_streaming_tool_non_streaming_collector():
    """Verify calling stream_tool via standard call_tool collects bounded items."""
    app = FastAPIMCP(auto_scan=False)

    @app.stream_tool(name="finite_feed", max_buffer=2)
    async def finite_feed():
        for i in range(5):
            yield {"item": i}

    call_res = await app.call_tool("finite_feed", {})
    res = _unwrap(call_res)
    assert "items" in res
    assert res["count"] == 2
    assert res["items"][0] == {"item": 0}
    assert res["items"][1] == {"item": 1}


@pytest.mark.asyncio
async def test_streaming_tool_librarian_indexing_and_execute():
    """Verify Librarian search_api_tools detects streaming tools and executes them safely."""
    app = FastAPIMCP(librarian=True)

    @app.stream_tool(name="librarian_stream")
    async def librarian_stream():
        yield {"chunk": "alpha"}
        yield {"chunk": "beta"}

    catalog = app.get_tool_catalog()
    assert "librarian_stream" in catalog
    assert getattr(catalog["librarian_stream"][2], "_is_streaming", False) is True

    # Ensure librarian meta-tools are registered
    meta_tools = await app.list_tools()
    meta_names = [t.name for t in meta_tools]
    assert "execute_api_tool" in meta_names

    # Verify Librarian execute_api_tool handles streaming tools without JSON error
    raw_res = await app.call_tool(
        "execute_api_tool", {"tool_name": "librarian_stream", "arguments": {}}
    )
    result = _unwrap(raw_res)
    assert "items" in result
    assert result["count"] == 2


@pytest.mark.asyncio
async def test_streaming_tool_exception_propagation():
    """Verify unhandled exceptions in stream generator close session and re-raise."""
    app = FastAPIMCP(auto_scan=False)

    @app.stream_tool(name="faulty_stream")
    async def faulty_stream():
        yield {"chunk": 1}
        raise RuntimeError("Stream broken")

    session = app.call_stream_tool("faulty_stream")
    chunk1 = await session.__anext__()
    assert chunk1["chunk_id"] == 1

    with pytest.raises(RuntimeError, match="Stream broken"):
        await session.__anext__()
