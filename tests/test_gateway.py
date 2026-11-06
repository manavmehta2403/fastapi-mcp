"""TDD Test Suite for Industry-Standard Hybrid Gateway and BYOG Architecture."""

import base64
import hashlib
import hmac
import json
import time
from typing import Any, Dict, List, Tuple
from fastapi import FastAPI, HTTPException
import httpx
from mcp.server.mcpserver.exceptions import ToolError
import pytest

from fastapi_mcp import (
    FastAPIMCP,
    GatewayMode,
    AuthMode,
    AuthContext,
    BaseGatewayAdapter,
    DefaultGateway,
    create_gateway_subapp,
)
from fastapi_mcp.gateway import TokenBucketRateLimiter, decode_hs256_jwt


def _generate_test_jwt(payload: Dict[str, Any], secret: str) -> str:
    """Helper to generate HS256 JWT tokens for testing."""
    header = {"alg": "HS256", "typ": "JWT"}
    h_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip("=")
    p_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    signature = hmac.new(
        secret.encode(), f"{h_b64}.{p_b64}".encode(), hashlib.sha256
    ).digest()
    s_b64 = base64.urlsafe_b64encode(signature).decode().rstrip("=")
    return f"{h_b64}.{p_b64}.{s_b64}"


def test_decode_hs256_jwt_scenarios():
    secret = "test_super_secret_signing_key_42"
    valid_payload = {"sub": "user_123", "tenant_id": "tenant_xyz", "exp": time.time() + 3600}
    token = _generate_test_jwt(valid_payload, secret)

    # 1. Valid token
    decoded = decode_hs256_jwt(token, secret)
    assert decoded["sub"] == "user_123"
    assert decoded["tenant_id"] == "tenant_xyz"

    # 2. Expired token
    expired_payload = {"sub": "user_old", "exp": time.time() - 100}
    expired_token = _generate_test_jwt(expired_payload, secret)
    with pytest.raises(ValueError, match="expired"):
        decode_hs256_jwt(expired_token, secret)

    # 3. Wrong secret
    with pytest.raises(ValueError, match="signature verification failed"):
        decode_hs256_jwt(token, "wrong_secret_key")

    # 4. Malformed tokens
    with pytest.raises(ValueError, match="expected 3 parts"):
        decode_hs256_jwt("part1.part2", secret)

    with pytest.raises(ValueError):
        decode_hs256_jwt("???.@@@.!!!", secret)

    # 5. Unsupported algorithm
    bad_header = base64.urlsafe_b64encode(json.dumps({"alg": "RS256"}).encode()).decode()
    with pytest.raises(ValueError, match="Unsupported JWT algorithm"):
        decode_hs256_jwt(f"{bad_header}.eyJzdWIiOiIxIn0.c2ln", secret)


def test_token_bucket_rate_limiter_edge_cases():
    limiter = TokenBucketRateLimiter(rate_limit_per_minute=2)

    # 2 calls allowed
    ok1, _ = limiter.is_allowed("client_a", cost=1.0)
    ok2, _ = limiter.is_allowed("client_a", cost=1.0)
    assert ok1 is True
    assert ok2 is True

    # 3rd call rejected
    ok3, retry_after = limiter.is_allowed("client_a", cost=1.0)
    assert ok3 is False
    assert retry_after > 0.0

    # Unlimited when rate limit <= 0
    unlimited = TokenBucketRateLimiter(rate_limit_per_minute=0)
    assert unlimited.is_allowed("any_client")[0] is True

    # Stale keys cleanup
    limiter._last_cleanup = time.time() - 100.0
    limiter._last_updated["stale_client"] = time.time() - 200.0
    limiter._tokens["stale_client"] = 1.0
    limiter.is_allowed("new_client")
    assert "stale_client" not in limiter._tokens


@pytest.mark.asyncio
async def test_default_gateway_authentication_schemes():
    secret = "jwt_signing_secret_999"
    api_key = "sk_live_enterprise_secret_key"
    gw = DefaultGateway(
        auth_mode=AuthMode.DUAL,
        api_keys={api_key},
        jwt_secret=secret,
        rate_limit_per_minute=60,
    )

    # 1. API Key Auth without agent
    ctx_api = await gw.authenticate({"X-API-Key": api_key})
    assert ctx_api.is_authenticated is True
    assert ctx_api.caller_type == "api_client"
    assert ctx_api.token_type == "api_key"

    # 2. API Key Auth with Agent header (OBO)
    ctx_agent_api = await gw.authenticate({
        "X-API-Key": api_key,
        "X-Agent-ID": "claude_desktop_runner",
    })
    assert ctx_agent_api.is_authenticated is True
    assert ctx_agent_api.caller_type == "ai_agent"
    assert ctx_agent_api.agent_id == "claude_desktop_runner"

    # 3. JWT Auth without agent
    jwt_token = _generate_test_jwt(
        {"sub": "usr_human_42", "scopes": "billing:read billing:write", "tenant_id": "corp_a"},
        secret,
    )
    ctx_jwt = await gw.authenticate({"Authorization": f"Bearer {jwt_token}"})
    assert ctx_jwt.is_authenticated is True
    assert ctx_jwt.caller_type == "human"
    assert ctx_jwt.user_id == "usr_human_42"
    assert ctx_jwt.scopes == ["billing:read", "billing:write"]
    assert ctx_jwt.tenant_id == "corp_a"

    # 4. JWT Auth with Agent header (On-Behalf-Of delegation)
    ctx_obo = await gw.authenticate({
        "Authorization": f"Bearer {jwt_token}",
        "X-Agent-ID": "cursor_agent_v3",
    })
    assert ctx_obo.is_authenticated is True
    assert ctx_obo.caller_type == "ai_agent"
    assert ctx_obo.user_id == "usr_human_42"
    assert ctx_obo.agent_id == "cursor_agent_v3"

    # 5. Invalid tokens & missing headers
    ctx_bad = await gw.authenticate({"Authorization": "Bearer invalid.token.payload"})
    assert ctx_bad.is_authenticated is False

    ctx_none = await gw.authenticate({})
    assert ctx_none.is_authenticated is False

    # 6. AuthMode.NONE always returns authenticated
    gw_none = DefaultGateway(auth_mode=AuthMode.NONE)
    ctx_open = await gw_none.authenticate({})
    assert ctx_open.is_authenticated is True


@pytest.mark.asyncio
async def test_gateway_tool_rbac_authorization():
    gw = DefaultGateway()

    # 1. No required scopes -> always authorized
    anon_ctx = AuthContext(is_authenticated=False)
    assert await gw.authorize_tool("read_data", [], anon_ctx) is True

    # 2. Required scopes + Unauthenticated caller -> rejected
    assert await gw.authorize_tool("write_data", ["admin"], anon_ctx) is False

    # 3. Wildcard scope '*' -> authorized for any scope
    admin_ctx = AuthContext(is_authenticated=True, scopes=["*"])
    assert await gw.authorize_tool("write_data", ["billing:write", "users:delete"], admin_ctx) is True

    # 4. Specific scopes matching
    scoped_ctx = AuthContext(is_authenticated=True, scopes=["billing:read", "analytics:view"])
    assert await gw.authorize_tool("view_bill", ["billing:read"], scoped_ctx) is True
    assert await gw.authorize_tool("delete_bill", ["billing:write"], scoped_ctx) is False


@pytest.mark.asyncio
async def test_gateway_middleware_rate_limiting_and_http_pipeline():
    gw = DefaultGateway(
        auth_mode=AuthMode.NONE,
        rate_limit_per_minute=2,
    )
    app = FastAPIMCP(gateway=gw, auto_scan=False)

    @app.get("/ping")
    def ping():
        return {"status": "pong"}

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # First 2 requests pass
        res1 = await client.get("/ping")
        assert res1.status_code == 200

        res2 = await client.get("/ping")
        assert res2.status_code == 200

        # 3rd request rejected with 429 and Retry-After
        res3 = await client.get("/ping")
        assert res3.status_code == 429
        assert "Too Many Requests" in res3.json()["detail"]
        assert "Retry-After" in res3.headers

    metrics = gw.get_metrics()
    assert metrics["total_calls"] == 3
    assert metrics["error_calls"] == 1


@pytest.mark.asyncio
async def test_scoped_api_tool_execution_and_rejection():
    secret = "secret_key_rbac_test"
    gw = DefaultGateway(
        auth_mode=AuthMode.JWT,
        jwt_secret=secret,
    )

    app = FastAPIMCP(gateway=gw, auto_scan=False)

    @app.api_tool("/secure/refund", methods=["POST"], required_scopes=["finance:execute"])
    def refund(amount: float):
        """Execute customer refund."""
        return {"refunded": amount}

    # Case 1: Caller with missing scope is denied (HTTP 403)
    read_only_jwt = _generate_test_jwt({"sub": "bob", "scopes": ["finance:read"]}, secret)
    app.session_context_provider = lambda: {"Authorization": f"Bearer {read_only_jwt}"}

    with pytest.raises(ToolError) as exc_info:
        await app.call_tool("refund", {"amount": 50.0})
    assert "lacks required scopes" in str(exc_info.value)

    # Case 2: Caller with valid scope succeeds
    exec_jwt = _generate_test_jwt({"sub": "alice", "scopes": ["finance:execute"]}, secret)
    app.session_context_provider = lambda: {"Authorization": f"Bearer {exec_jwt}"}

    res = await app.call_tool("refund", {"amount": 100.0})
    assert "100.0" in str(res)


@pytest.mark.asyncio
async def test_custom_byog_adapter():
    class CustomKongGateway(BaseGatewayAdapter):
        def __init__(self):
            self.intercepted_calls = []

        async def authenticate(self, headers: Dict[str, str]) -> AuthContext:
            if headers.get("x-kong-token") == "kong_authorized_secret":
                return AuthContext(
                    caller_type="api_client",
                    is_authenticated=True,
                    scopes=["kong:master"],
                )
            return AuthContext(caller_type="anonymous", is_authenticated=False)

        async def check_rate_limit(self, key: str) -> Tuple[bool, float]:
            return True, 0.0

        async def authorize_tool(
            self, tool_name: str, required_scopes: List[str], auth_context: AuthContext
        ) -> bool:
            self.intercepted_calls.append(tool_name)
            return "kong:master" in auth_context.scopes

    byog = CustomKongGateway()
    app = FastAPIMCP(gateway=byog, gateway_mode=GatewayMode.BYOG, auto_scan=False)

    @app.api_tool("/kong/action", methods=["POST"], required_scopes=["kong:master"])
    def kong_action():
        return {"kong": "ok"}

    # Unauthorized call
    app.session_context_provider = lambda: {"x-kong-token": "wrong"}
    with pytest.raises(ToolError) as exc:
        await app.call_tool("kong_action")
    assert "lacks required scopes" in str(exc.value)

    # Authorized call
    app.session_context_provider = lambda: {"x-kong-token": "kong_authorized_secret"}
    res = await app.call_tool("kong_action")
    assert "ok" in str(res)
    assert "kong_action" in byog.intercepted_calls


@pytest.mark.asyncio
async def test_create_gateway_subapp_and_external_mounting():
    mcp_app = FastAPIMCP(mcp_name="PlatformTools", auto_scan=False)

    @mcp_app.tool()
    def calculate_tax(amount: float) -> float:
        return amount * 0.2

    # Export subapp
    subapp = create_gateway_subapp(mcp_app, path="/ai", sse_path="/ai-sse")
    assert isinstance(subapp, FastAPI)
    assert subapp.title == "PlatformTools Gateway"

    # Mount onto external corporate gateway
    corporate_gateway = FastAPI(title="Enterprise API Gateway")
    corporate_gateway.mount("/internal-mcp", subapp)

    transport = httpx.ASGITransport(app=corporate_gateway)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/internal-mcp/ai/ui")
        assert res.status_code == 200


def test_gateway_modes_and_operational_isolation():
    # 1. MCP_ONLY mode strips public Swagger/ReDoc
    mcp_only_app = FastAPIMCP(gateway_mode=GatewayMode.MCP_ONLY, auto_scan=False)
    assert mcp_only_app.docs_url is None
    assert mcp_only_app.redoc_url is None

    # 2. REST_ONLY mode skips mounting MCP transports
    rest_only_app = FastAPIMCP(gateway_mode=GatewayMode.REST_ONLY, auto_scan=False)
    rest_only_app.mount_mcp(path="/mcp", sse_path="/sse")
    route_paths = [r.path for r in rest_only_app.routes]
    assert "/mcp" not in route_paths
    assert "/sse" not in route_paths
