"""FastAPI-MCP: Seamless bridge between FastAPI and FastMCP / Model Context Protocol.

Convert existing FastAPI applications to MCP servers with zero code changes,
or build unified APIs where REST endpoints and MCP tools coexist effortlessly.
"""

from .core import FastAPIMCP
from .scanner import RouteScanner
from .dispatcher import ASGIDispatcher
from .gateway import (
    GatewayMode,
    AuthMode,
    AuthContext,
    BaseGatewayAdapter,
    DefaultGateway,
    create_gateway_subapp,
)
from .streaming import (
    StreamChunk,
    StreamToolSession,
    collect_stream,
)
from .jobs import (
    JobProgress,
    JobState,
    JobRegistry,
)
from .events import (
    EventMessage,
    EventSubscription,
    EventBroker,
)
from .webhooks import (
    WebhookManager,
    verify_hmac_signature,
)
from .protocols import (
    ProtocolGateway,
)
from .mesh import (
    AgentMesh,
)

__version__ = "0.9.0"

__all__ = [
    "FastAPIMCP",
    "RouteScanner",
    "ASGIDispatcher",
    "GatewayMode",
    "AuthMode",
    "AuthContext",
    "BaseGatewayAdapter",
    "DefaultGateway",
    "create_gateway_subapp",
    "StreamChunk",
    "StreamToolSession",
    "collect_stream",
    "JobProgress",
    "JobState",
    "JobRegistry",
    "EventMessage",
    "EventSubscription",
    "EventBroker",
    "WebhookManager",
    "verify_hmac_signature",
    "ProtocolGateway",
    "AgentMesh",
]
