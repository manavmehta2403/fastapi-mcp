"""FastAPI-MCP Gateway: Industry-standard Hybrid Gateway with Pluggable BYOG.

Provides multi-scheme authentication (JWT, API key, dual-mode, On-Behalf-Of delegation),
token-bucket rate limiting, tool RBAC scoping, and exportable ASGI sub-applications.
"""

from abc import ABC, abstractmethod
import base64
from enum import Enum
import hashlib
import hmac
import json
import time
from typing import Any, Dict, List, Optional, Set, Tuple

from fastapi import FastAPI
from pydantic import BaseModel, Field


class GatewayMode(str, Enum):
    """Operational mode of the unified gateway."""

    HYBRID = "hybrid"
    REST_ONLY = "rest_only"
    MCP_ONLY = "mcp_only"
    BYOG = "byog"


class AuthMode(str, Enum):
    """Authentication scheme supported by the gateway."""

    NONE = "none"
    API_KEY = "api_key"
    JWT = "jwt"
    DUAL = "dual"
    CUSTOM = "custom"


class AuthContext(BaseModel):
    """Unified security context for authenticated callers (human or AI agent)."""

    caller_type: str = Field(default="anonymous", description="Caller classification")
    user_id: Optional[str] = Field(default=None, description="Human user identifier")
    agent_id: Optional[str] = Field(default=None, description="AI agent identifier")
    tenant_id: Optional[str] = Field(default=None, description="Tenant organization ID")
    scopes: List[str] = Field(default_factory=list, description="Granted permission scopes")
    is_authenticated: bool = Field(default=False, description="Whether caller is authenticated")
    token_type: Optional[str] = Field(default=None, description="Token type used")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Custom metadata claims")


def decode_hs256_jwt(token: str, secret: str) -> Dict[str, Any]:
    """Decode and verify an HMAC-SHA256 signed JWT token using standard library."""
    parts = token.strip().split(".")
    if len(parts) != 3:
        raise ValueError("Invalid JWT token format: expected 3 parts")

    header_b64, payload_b64, signature_b64 = parts

    def b64url_decode(data: str) -> bytes:
        rem = len(data) % 4
        padded = data + "=" * (4 - rem) if rem else data
        return base64.urlsafe_b64decode(padded)

    try:
        header_bytes = b64url_decode(header_b64)
        payload_bytes = b64url_decode(payload_b64)
        signature = b64url_decode(signature_b64)
        header = json.loads(header_bytes.decode("utf-8"))
        payload = json.loads(payload_bytes.decode("utf-8"))
    except Exception as exc:
        raise ValueError("Corrupted base64 or JSON in JWT token") from exc

    if header.get("alg") != "HS256":
        raise ValueError(f"Unsupported JWT algorithm: {header.get('alg')}")

    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    expected_sig = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()

    if not hmac.compare_digest(expected_sig, signature):
        raise ValueError("JWT signature verification failed")

    exp = payload.get("exp")
    if exp is not None and time.time() > float(exp):
        raise ValueError("JWT token has expired")

    return payload


class TokenBucketRateLimiter:
    """Sliding token-bucket rate limiter with periodic cleanup."""

    def __init__(self, rate_limit_per_minute: int = 60) -> None:
        self.rate_limit_per_minute = rate_limit_per_minute
        self._tokens: Dict[str, float] = {}
        self._last_updated: Dict[str, float] = {}
        self._last_cleanup = time.time()

    def is_allowed(self, key: str, cost: float = 1.0) -> Tuple[bool, float]:
        """Check if request is allowed under the rate limit."""
        if self.rate_limit_per_minute <= 0:
            return True, 0.0

        now = time.time()
        capacity = float(self.rate_limit_per_minute)
        refill_rate = capacity / 60.0

        if now - self._last_cleanup > 60.0:
            stale_keys = [k for k, last in self._last_updated.items() if now - last > 120.0]
            for stale in stale_keys:
                self._tokens.pop(stale, None)
                self._last_updated.pop(stale, None)
            self._last_cleanup = now

        current_tokens = self._tokens.get(key, capacity)
        last_time = self._last_updated.get(key, now)
        elapsed = now - last_time

        refilled = min(capacity, current_tokens + (elapsed * refill_rate))

        if refilled >= cost:
            self._tokens[key] = refilled - cost
            self._last_updated[key] = now
            return True, 0.0

        retry_after = (cost - refilled) / refill_rate
        return False, max(0.1, retry_after)


class BaseGatewayAdapter(ABC):
    """Abstract interface allowing developers to supply their own gateway."""

    @abstractmethod
    async def authenticate(self, headers: Dict[str, str]) -> AuthContext:
        """Authenticate request headers and return caller security context."""

    @abstractmethod
    async def check_rate_limit(self, key: str) -> Tuple[bool, float]:
        """Evaluate rate limits for a given client identifier."""

    @abstractmethod
    async def authorize_tool(
        self,
        tool_name: str,
        required_scopes: List[str],
        auth_context: AuthContext,
    ) -> bool:
        """Determine whether caller is authorized to invoke a tool."""


class DefaultGateway(BaseGatewayAdapter):
    """Batteries-included enterprise Hybrid Gateway adapter."""

    def __init__(
        self,
        *,
        auth_mode: AuthMode = AuthMode.NONE,
        api_keys: Optional[Set[str]] = None,
        jwt_secret: Optional[str] = None,
        rate_limit_per_minute: int = 120,
    ) -> None:
        self.auth_mode = auth_mode
        self.api_keys = api_keys or set()
        self.jwt_secret = jwt_secret
        self.rate_limiter = TokenBucketRateLimiter(rate_limit_per_minute)
        self._call_count = 0
        self._error_count = 0

    def _authenticate_api_key(
        self, token: str, agent_id: Optional[str]
    ) -> AuthContext:
        for valid_key in self.api_keys:
            if hmac.compare_digest(token, valid_key):
                return AuthContext(
                    caller_type="ai_agent" if agent_id else "api_client",
                    agent_id=agent_id,
                    user_id="service_account",
                    token_type="api_key",
                    is_authenticated=True,
                    scopes=["*"],
                )
        return AuthContext(caller_type="anonymous", is_authenticated=False)

    def _authenticate_jwt(
        self, token: str, agent_id: Optional[str]
    ) -> AuthContext:
        if not self.jwt_secret:
            return AuthContext(caller_type="anonymous", is_authenticated=False)
        try:
            payload = decode_hs256_jwt(token, self.jwt_secret)
            scopes = payload.get("scopes") or payload.get("scope", [])
            if isinstance(scopes, str):
                scopes = scopes.split()

            return AuthContext(
                caller_type="ai_agent" if agent_id else "human",
                user_id=str(payload.get("sub", "")),
                agent_id=agent_id or payload.get("agent_id"),
                tenant_id=payload.get("tenant_id"),
                scopes=scopes,
                token_type="jwt",
                is_authenticated=True,
                metadata=payload,
            )
        except ValueError:
            return AuthContext(caller_type="anonymous", is_authenticated=False)

    async def authenticate(self, headers: Dict[str, str]) -> AuthContext:
        """Resolve authentication using JWT, API Key, or On-Behalf-Of delegation."""
        if self.auth_mode == AuthMode.NONE:
            return AuthContext(caller_type="anonymous", is_authenticated=True)

        lowered_headers = {k.lower(): v for k, v in headers.items()}
        auth_header = lowered_headers.get("authorization", "")
        api_key_header = lowered_headers.get("x-api-key", "")
        agent_id = lowered_headers.get("x-agent-id")

        token = ""
        if auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()
        elif api_key_header:
            token = api_key_header.strip()

        if not token:
            return AuthContext(caller_type="anonymous", is_authenticated=False)

        is_jwt_format = token.count(".") == 2
        effective_mode = self.auth_mode
        if self.auth_mode == AuthMode.DUAL:
            effective_mode = AuthMode.JWT if is_jwt_format else AuthMode.API_KEY

        if effective_mode == AuthMode.API_KEY:
            return self._authenticate_api_key(token, agent_id)

        if effective_mode == AuthMode.JWT:
            return self._authenticate_jwt(token, agent_id)

        return AuthContext(caller_type="anonymous", is_authenticated=False)

    async def check_rate_limit(self, key: str) -> Tuple[bool, float]:
        """Check rate limit for client key."""
        allowed, retry_after = self.rate_limiter.is_allowed(key)
        self._call_count += 1
        if not allowed:
            self._error_count += 1
        return allowed, retry_after

    async def authorize_tool(
        self,
        tool_name: str,
        required_scopes: List[str],
        auth_context: AuthContext,
    ) -> bool:
        """Authorize tool execution based on scopes and permissions."""
        del tool_name
        if not required_scopes:
            return True

        if not auth_context.is_authenticated:
            return False

        if "*" in auth_context.scopes:
            return True

        caller_scopes = set(auth_context.scopes)
        return all(req in caller_scopes for req in required_scopes)

    def get_metrics(self) -> Dict[str, Any]:
        """Export gateway runtime performance and call metrics."""
        return {
            "total_calls": self._call_count,
            "error_calls": self._error_count,
            "auth_mode": self.auth_mode.value,
        }


def create_gateway_subapp(
    mcp_app: Any,
    path: Optional[str] = "/mcp",
    sse_path: Optional[str] = "/sse",
    enable_ui: bool = True,
) -> FastAPI:
    """Export an isolated ASGI application containing only the MCP gateway routing plane."""
    subapp = FastAPI(title=f"{getattr(mcp_app, 'mcp_name', 'FastAPIMCP')} Gateway")
    mcp_app.mount_to(subapp, path=path, sse_path=sse_path, enable_ui=enable_ui)
    return subapp
