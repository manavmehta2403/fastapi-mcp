"""Streaming Structured Output implementation for FastAPI-MCP."""

from dataclasses import dataclass
from typing import Any, AsyncGenerator, Dict, Optional

from pydantic import BaseModel


@dataclass
class StreamChunk:
    """A single chunk emitted over a streaming tool session."""

    chunk_id: int
    data: Any
    is_last: bool = False


class StreamToolSession:
    """Manages an active streaming tool generator session with backpressure and cleanup."""

    def __init__(self, generator: AsyncGenerator[Any, None], max_buffered: int = 100):
        self._generator = generator
        self._max_buffered = max_buffered
        self._closed = False
        self._chunk_counter = 0

    def __aiter__(self) -> "StreamToolSession":
        return self

    async def __anext__(self) -> Dict[str, Any]:
        if self._closed:
            raise StopAsyncIteration

        try:
            item = await self._generator.__anext__()
            self._chunk_counter += 1
            data = item.model_dump() if isinstance(item, BaseModel) else item
            return {"chunk_id": self._chunk_counter, "data": data, "is_last": False}
        except StopAsyncIteration:
            self._closed = True
            raise
        except Exception:
            await self.aclose()
            raise

    async def aclose(self) -> None:
        """Gracefully close the underlying generator and release resources."""
        if not self._closed:
            self._closed = True
            if hasattr(self._generator, "aclose"):
                await self._generator.aclose()


async def collect_stream(
    generator: AsyncGenerator[Any, None], max_items: Optional[int] = None
) -> Dict[str, Any]:
    """Collect items from an async generator into a bounded list for non-streaming callers."""
    items = []
    session = StreamToolSession(generator)
    try:
        async for chunk in session:
            items.append(chunk["data"])
            if max_items and len(items) >= max_items:
                break
    finally:
        await session.aclose()
    return {"items": items, "count": len(items)}
