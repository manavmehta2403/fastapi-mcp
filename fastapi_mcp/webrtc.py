"""WebRTC Real-Time Agent Channels and Signaling for FastAPI-MCP."""

import asyncio
from dataclasses import dataclass, field
import time
from typing import Any, Callable, Dict, List, Optional
import uuid


@dataclass
class WebRTCChannelSession:
    """Active WebRTC DataChannel connection session."""

    session_id: str
    channel_name: str
    state: str = "open"
    created_at: float = field(default_factory=time.time)
    _inbound_queue: asyncio.Queue = field(default_factory=asyncio.Queue)
    _outbound_queue: asyncio.Queue = field(default_factory=asyncio.Queue)

    async def send(self, data: Any) -> None:
        """Send message through WebRTC DataChannel to remote peer."""
        if self.state != "open":
            raise ConnectionError(f"WebRTC channel '{self.channel_name}' is {self.state}.")
        await self._outbound_queue.put(data)

    async def receive(self) -> Any:
        """Receive incoming message from WebRTC DataChannel."""
        if self.state != "open" and self._inbound_queue.empty():
            raise ConnectionError(f"WebRTC channel '{self.channel_name}' is closed.")
        return await self._inbound_queue.get()

    async def post_inbound(self, data: Any) -> None:
        """Internal helper delivering peer data into session."""
        await self._inbound_queue.put(data)

    async def close(self) -> None:
        """Close WebRTC channel session and clean up buffers."""
        self.state = "closed"


class WebRTCManager:
    """Coordinates WebRTC SDP signaling, peer sessions, and DataChannels."""

    def __init__(self, app: Any):
        self.app = app
        self._handlers: Dict[str, Callable[..., Any]] = {}
        self._sessions: Dict[str, WebRTCChannelSession] = {}
        self._lock = asyncio.Lock()

    def register_channel(self, name: str, handler: Callable[..., Any]) -> None:
        """Register a handler for a named WebRTC DataChannel."""
        self._handlers[name] = handler

    def list_channels(self) -> List[str]:
        """Return list of all registered WebRTC channel names."""
        return sorted(self._handlers.keys())

    async def create_offer(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Generate SDP offer for WebRTC peer connection initialization."""
        sid = session_id or str(uuid.uuid4())
        mock_sdp = f"v=0\r\no=- {int(time.time())} 2 IN IP4 127.0.0.1\r\ns=FastAPIMCP-WebRTC\r\n"
        return {
            "session_id": sid,
            "type": "offer",
            "sdp": mock_sdp,
            "channels": self.list_channels(),
        }

    async def process_answer(self, session_id: str, sdp_answer: str) -> Dict[str, Any]:
        """Process remote SDP answer and transition connection to active."""
        if not sdp_answer:
            return {"is_error": True, "error": "Invalid or empty SDP answer."}

        async with self._lock:
            # Create active sessions for each registered channel
            for ch_name in self._handlers:
                key = f"{session_id}:{ch_name}"
                self._sessions[key] = WebRTCChannelSession(
                    session_id=session_id, channel_name=ch_name
                )

        return {
            "session_id": session_id,
            "status": "connected",
            "active_channels": self.list_channels(),
        }

    async def get_channel_session(
        self, session_id: str, channel_name: str
    ) -> Optional[WebRTCChannelSession]:
        """Retrieve active channel session by session_id and channel name."""
        key = f"{session_id}:{channel_name}"
        async with self._lock:
            return self._sessions.get(key)

    async def close_all(self) -> None:
        """Close all WebRTC sessions on shutdown."""
        async with self._lock:
            for session in self._sessions.values():
                await session.close()
            self._sessions.clear()
