"""Event Subscriptions and Reactive Push Protocol for FastAPI-MCP."""

import asyncio
from dataclasses import dataclass
import fnmatch
import inspect
import time
from typing import Any, Callable, Dict, List, Optional, Set

from pydantic import BaseModel, Field


class EventMessage(BaseModel):
    """Payload container for events dispatched over the event broker."""

    topic: str = Field(description="Event topic or routing key, e.g., 'orders.created'")
    payload: Any = Field(description="Structured event payload")
    timestamp: float = Field(
        default_factory=time.time,
        description="Unix timestamp of event dispatch",
    )


@dataclass
class EventSubscription:
    """Represents an active client queue subscription to a topic pattern."""

    pattern: str
    queue: asyncio.Queue
    max_size: int = 100


class EventBroker:
    """Thread-safe pub/sub event broker with wildcard routing and bounded queues."""

    def __init__(self, default_max_queue_size: int = 256):
        self.default_max_queue_size = default_max_queue_size
        self._subscriptions: List[EventSubscription] = []
        self._handlers: Dict[str, List[Callable[..., Any]]] = {}
        self._registered_topics: Set[str] = set()
        self._lock = asyncio.Lock()

    def register_topic(self, topic: str, handler: Optional[Callable[..., Any]] = None) -> None:
        """Register a recognized topic and optional handler callback."""
        self._registered_topics.add(topic)
        if handler:
            if topic not in self._handlers:
                self._handlers[topic] = []
            self._handlers[topic].append(handler)

    def list_topics(self) -> List[str]:
        """Return list of all registered topics."""
        return sorted(self._registered_topics)

    async def subscribe(self, pattern: str, max_queue_size: Optional[int] = None) -> asyncio.Queue:
        """Subscribe to a topic pattern (supports * wildcards). Returns a bounded queue."""
        q_size = max_queue_size or self.default_max_queue_size
        queue: asyncio.Queue = asyncio.Queue(maxsize=q_size)
        sub = EventSubscription(pattern=pattern, queue=queue, max_size=q_size)
        async with self._lock:
            self._subscriptions.append(sub)
        return queue

    async def unsubscribe(self, pattern: str, queue: asyncio.Queue) -> bool:
        """Remove a subscription by pattern and queue reference."""
        async with self._lock:
            initial_len = len(self._subscriptions)
            self._subscriptions = [
                s for s in self._subscriptions
                if not (s.pattern == pattern and s.queue is queue)
            ]
            return len(self._subscriptions) < initial_len

    async def publish(self, topic: str, payload: Any) -> int:
        """Publish an event to all matching subscriber queues and registered handlers."""
        p_data = payload.model_dump() if hasattr(payload, "model_dump") else payload
        msg = EventMessage(topic=topic, payload=p_data)
        delivered_count = 0

        handlers = self._handlers.get(topic, [])
        for handler in handlers:
            try:
                if inspect.iscoroutinefunction(handler):
                    asyncio.create_task(handler(payload))
                else:
                    loop = asyncio.get_running_loop()
                    loop.run_in_executor(None, handler, payload)
            except Exception:  # pylint: disable=broad-exception-caught
                pass

        async with self._lock:
            for sub in self._subscriptions:
                if fnmatch.fnmatch(topic, sub.pattern):
                    if sub.queue.full():
                        try:
                            sub.queue.get_nowait()
                        except asyncio.QueueEmpty:
                            pass
                    try:
                        sub.queue.put_nowait(msg.model_dump())
                        delivered_count += 1
                    except asyncio.QueueFull:
                        pass

        return delivered_count

    async def close_all(self) -> None:
        """Clear all subscriptions on server shutdown."""
        async with self._lock:
            self._subscriptions.clear()
            self._handlers.clear()
