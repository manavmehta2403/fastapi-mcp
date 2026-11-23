"""Async Jobs Protocol implementation for FastAPI-MCP."""

import asyncio
from dataclasses import dataclass, field
import inspect
import time
from typing import Any, Callable, Dict, Optional
import uuid

from pydantic import BaseModel, Field


class JobProgress(BaseModel):
    """Progress snapshot reported by an asynchronous background job."""

    step: str = Field(description="Current progress stage or checkpoint label")
    percent: float = Field(default=0.0, ge=0.0, le=100.0, description="Percentage of completion")
    message: Optional[str] = Field(default=None, description="Optional informational message")
    details: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary metadata details")


@dataclass
class JobState:
    """Internal state tracked for an asynchronous job."""

    job_id: str
    tool_name: str
    status: str = "pending"
    progress: Optional[JobProgress] = None
    result: Any = None
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    task: Optional[asyncio.Task] = None


class JobRegistry:
    """Thread-safe in-memory registry for tracking background job executions."""

    def __init__(self, ttl_seconds: float = 3600.0, max_completed: int = 1000):
        self.ttl_seconds = ttl_seconds
        self.max_completed = max_completed
        self._jobs: Dict[str, JobState] = {}
        self._lock = asyncio.Lock()

    async def create_job(self, tool_name: str) -> JobState:
        """Create and register a new job state."""
        job_id = str(uuid.uuid4())
        job = JobState(job_id=job_id, tool_name=tool_name)
        async with self._lock:
            self._evict_if_needed_locked()
            self._jobs[job_id] = job
        return job

    async def get_job(self, job_id: str) -> Optional[JobState]:
        """Retrieve a job by its ID if not expired."""
        async with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return None
            if job.completed_at and (time.time() - job.completed_at > self.ttl_seconds):
                del self._jobs[job_id]
                return None
            return job

    async def cancel_job(self, job_id: str) -> Dict[str, Any]:
        """Cancel a running or pending job."""
        async with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return {"is_error": True, "error": f"Job '{job_id}' not found or expired."}

            if job.status in ("completed", "failed", "cancelled"):
                return {
                    "job_id": job_id,
                    "status": job.status,
                    "message": f"Job is already {job.status}.",
                }

            if job.task and not job.task.done():
                job.task.cancel()

            job.status = "cancelled"
            job.completed_at = time.time()
            return {
                "job_id": job_id,
                "status": "cancelled",
                "message": "Job cancellation successfully requested.",
            }

    async def cancel_all(self) -> None:
        """Cancel all pending or running jobs on application shutdown."""
        async with self._lock:
            for job in self._jobs.values():
                if job.task and not job.task.done():
                    job.task.cancel()
                if job.status in ("pending", "running"):
                    job.status = "cancelled"
                    job.completed_at = time.time()

    def _evict_if_needed_locked(self) -> None:
        """Evict expired and oldest completed jobs to maintain bounded memory."""
        now = time.time()
        expired = [
            jid
            for jid, j in self._jobs.items()
            if j.completed_at and (now - j.completed_at > self.ttl_seconds)
        ]
        for jid in expired:
            del self._jobs[jid]

        completed = [
            (jid, j.completed_at or 0.0)
            for jid, j in self._jobs.items()
            if j.status in ("completed", "failed", "cancelled")
        ]
        if len(completed) > self.max_completed:
            completed.sort(key=lambda x: x[1])
            excess = len(completed) - self.max_completed
            for jid, _ in completed[:excess]:
                if jid in self._jobs:
                    del self._jobs[jid]


async def execute_job_worker(
    job: JobState,
    func: Callable[..., Any],
    args: Dict[str, Any],
    timeout: Optional[float] = None,
) -> None:
    """Worker coroutine that drives background job execution and status updates."""
    job.status = "running"

    async def _run() -> Any:
        if inspect.isasyncgenfunction(func):
            last_val = None
            async for item in func(**args):
                if isinstance(item, JobProgress):
                    job.progress = item
                else:
                    last_val = item
            return last_val

        if inspect.iscoroutinefunction(func):
            return await func(**args)

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, lambda: func(**args))

    try:
        if timeout and timeout > 0:
            result = await asyncio.wait_for(_run(), timeout=timeout)
        else:
            result = await _run()
        job.result = result
        job.status = "completed"
    except asyncio.CancelledError:
        job.status = "cancelled"
    except asyncio.TimeoutError:
        job.status = "failed"
        job.error = f"Job timed out after {timeout} seconds."
    except Exception as exc:  # pylint: disable=broad-exception-caught
        job.status = "failed"
        job.error = str(exc)
    finally:
        job.completed_at = time.time()


def register_job_meta_tools(app: Any) -> None:
    """Register get_job_status and cancel_job meta tools onto app."""
    # pylint: disable=protected-access
    if "_job_meta_tools_registered" in app._registered_tool_names:
        return

    async def get_job_status(job_id: str) -> Dict[str, Any]:
        """Retrieve the current execution status, progress, and result of an async job."""
        job = await app.job_registry.get_job(job_id)
        if not job:
            return {
                "is_error": True,
                "job_id": job_id,
                "error": f"Job '{job_id}' not found or has expired.",
            }
        now = time.time()
        elapsed = (job.completed_at or now) - job.created_at
        return {
            "job_id": job.job_id,
            "tool_name": job.tool_name,
            "status": job.status,
            "progress": job.progress.model_dump() if job.progress else None,
            "result": job.result,
            "error": job.error,
            "elapsed_seconds": round(elapsed, 2),
        }

    async def cancel_job(job_id: str) -> Dict[str, Any]:
        """Gracefully cancel a pending or running asynchronous background job."""
        return await app.job_registry.cancel_job(job_id)

    app._tool_catalog["get_job_status"] = (
        "get_job_status",
        "Retrieve current status, progress, and result of an async job.",
        get_job_status,
    )
    app._tool_catalog["cancel_job"] = (
        "cancel_job",
        "Gracefully cancel a pending or running asynchronous background job.",
        cancel_job,
    )

    if not app.librarian:
        app.mcp_server.add_tool(
            get_job_status,
            name="get_job_status",
            description="Retrieve current status, progress, and result of an async job.",
        )
        app.mcp_server.add_tool(
            cancel_job,
            name="cancel_job",
            description="Gracefully cancel a pending or running asynchronous background job.",
        )
        app._registered_tool_names.add("get_job_status")
        app._registered_tool_names.add("cancel_job")

    app._registered_tool_names.add("_job_meta_tools_registered")
