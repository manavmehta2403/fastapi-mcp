"""Comprehensive TDD tests for Async Jobs Protocol (@app.job) in v0.3.0."""

import asyncio
import json
import time
from typing import Any, Dict
import pytest
from fastapi_mcp import FastAPIMCP, JobProgress


def _unwrap(res: Any) -> Dict[str, Any]:
    """Helper to unwrap FastMCP CallToolResult to dict."""
    if hasattr(res, "content") and res.content:
        return json.loads(res.content[0].text)
    if isinstance(res, dict):
        return res
    return {}


@pytest.mark.asyncio
async def test_job_registration_and_immediate_ack():
    """Verify @app.job immediately returns a UUID job_id and does not block."""
    app = FastAPIMCP(auto_scan=False)

    @app.job(name="slow_task", timeout=10)
    async def slow_task(duration: float):
        await asyncio.sleep(duration)
        return {"done": True}

    call_res = await app.call_tool("slow_task", {"duration": 0.05})
    res = _unwrap(call_res)
    assert "job_id" in res
    assert res["status"] == "pending"

    status = _unwrap(await app.call_tool("get_job_status", {"job_id": res["job_id"]}))
    assert status["status"] in ("pending", "running", "completed")

    await asyncio.sleep(0.1)
    status_done = _unwrap(await app.call_tool("get_job_status", {"job_id": res["job_id"]}))
    assert status_done["status"] == "completed"
    assert status_done["result"] == {"done": True}


@pytest.mark.asyncio
async def test_job_progress_streaming_and_status_polling():
    """Verify progress updates are recorded and queryable via get_job_status."""
    app = FastAPIMCP(auto_scan=False)

    @app.job(name="progress_task")
    async def progress_task():
        yield JobProgress(step="Initializing", percent=25.0)
        await asyncio.sleep(0.05)
        yield JobProgress(step="Processing", percent=75.0)
        await asyncio.sleep(0.05)
        yield {"result": "finished"}

    ack = _unwrap(await app.call_tool("progress_task", {}))
    job_id = ack["job_id"]

    await asyncio.sleep(0.02)
    s1 = _unwrap(await app.call_tool("get_job_status", {"job_id": job_id}))
    assert s1["status"] in ("running", "completed")
    if s1["progress"]:
        assert s1["progress"]["percent"] >= 25.0

    await asyncio.sleep(0.15)
    s_final = _unwrap(await app.call_tool("get_job_status", {"job_id": job_id}))
    assert s_final["status"] == "completed"
    assert s_final["result"] == {"result": "finished"}


@pytest.mark.asyncio
async def test_job_sync_worker_execution():
    """Verify sync functions run in executor without blocking event loop."""
    app = FastAPIMCP(auto_scan=False)

    @app.job(name="sync_task")
    def sync_task(val: int):
        time.sleep(0.05)
        return val * 2

    ack = _unwrap(await app.call_tool("sync_task", {"val": 21}))
    job_id = ack["job_id"]
    await asyncio.sleep(0.1)

    s = _unwrap(await app.call_tool("get_job_status", {"job_id": job_id}))
    assert s["status"] == "completed"
    assert s["result"] == 42


@pytest.mark.asyncio
async def test_job_timeout_handling():
    """Verify job times out and reports failure when exceeding timeout."""
    app = FastAPIMCP(auto_scan=False)

    @app.job(name="timeout_task", timeout=0.05)
    async def timeout_task():
        await asyncio.sleep(0.5)
        return "unreachable"

    ack = _unwrap(await app.call_tool("timeout_task", {}))
    job_id = ack["job_id"]
    await asyncio.sleep(0.1)

    s = _unwrap(await app.call_tool("get_job_status", {"job_id": job_id}))
    assert s["status"] == "failed"
    assert "timed out" in s["error"]


@pytest.mark.asyncio
async def test_job_graceful_cancellation_and_cleanup():
    """Verify cancel_job stops execution and marks job cancelled."""
    app = FastAPIMCP(auto_scan=False)
    cancelled = False

    @app.job(name="cancellable_task")
    async def cancellable_task():
        nonlocal cancelled
        try:
            await asyncio.sleep(1.0)
        except asyncio.CancelledError:
            cancelled = True
            raise

    ack = _unwrap(await app.call_tool("cancellable_task", {}))
    job_id = ack["job_id"]
    await asyncio.sleep(0.02)

    cancel_res = _unwrap(await app.call_tool("cancel_job", {"job_id": job_id}))
    assert cancel_res["status"] == "cancelled"

    await asyncio.sleep(0.05)
    assert cancelled is True

    second_cancel = _unwrap(await app.call_tool("cancel_job", {"job_id": job_id}))
    assert second_cancel["status"] == "cancelled"


@pytest.mark.asyncio
async def test_job_registry_ttl_and_lru_eviction():
    """Verify expired jobs and jobs over max_completed are evicted."""
    app = FastAPIMCP(auto_scan=False, job_ttl_seconds=0.05, max_completed_jobs=2)

    @app.job(name="quick_job")
    async def quick_job(i: int):
        return i

    ack1 = _unwrap(await app.call_tool("quick_job", {"i": 1}))
    _unwrap(await app.call_tool("quick_job", {"i": 2}))
    _unwrap(await app.call_tool("quick_job", {"i": 3}))

    await asyncio.sleep(0.02)
    _unwrap(await app.call_tool("quick_job", {"i": 4}))
    await asyncio.sleep(0.08)

    s1 = _unwrap(await app.call_tool("get_job_status", {"job_id": ack1["job_id"]}))
    assert s1.get("is_error") is True

    cancel_err = _unwrap(await app.call_tool("cancel_job", {"job_id": "non_existent"}))
    assert cancel_err.get("is_error") is True


@pytest.mark.asyncio
async def test_job_exception_capture():
    """Verify unhandled exceptions in job coroutines are safely captured as failed status."""
    app = FastAPIMCP(auto_scan=False)

    @app.job(name="failing_task")
    async def failing_task():
        raise ValueError("Simulated DB connection failure")

    ack = _unwrap(await app.call_tool("failing_task", {}))
    await asyncio.sleep(0.05)

    s = _unwrap(await app.call_tool("get_job_status", {"job_id": ack["job_id"]}))
    assert s["status"] == "failed"
    assert "Simulated DB connection failure" in s["error"]


@pytest.mark.asyncio
async def test_job_lifespan_cancel_all():
    """Verify lifespan shutdown cleanly cancels all running jobs."""
    app = FastAPIMCP(auto_scan=False)

    @app.job(name="endless_job")
    async def endless_job():
        await asyncio.sleep(10.0)

    ack = _unwrap(await app.call_tool("endless_job", {}))
    job_id = ack["job_id"]

    await app.job_registry.cancel_all()

    s = _unwrap(await app.call_tool("get_job_status", {"job_id": job_id}))
    assert s["status"] == "cancelled"
