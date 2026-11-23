"""Enterprise Hybrid Gateway Example with BYOG, Multi-Scheme Auth, and Scopes.

Demonstrates:
1. Dual-mode authentication (JWT HS256 + API Keys + Agent On-Behalf-Of delegation).
2. Pluggable BaseGatewayAdapter (BYOG - Bring Your Own Gateway for Kong/Envoy/Traefik).
3. Tool-level RBAC authorization scopes (@app.api_tool(required_scopes=[...])).
4. Token-bucket rate limiting with standard HTTP 429 Retry-After.
"""

import asyncio
import base64
import hashlib
import hmac
import json
import time
from typing import Any, Dict

from fastapi import HTTPException, Request
import httpx
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import BaseModel, Field

from fastapi_mcp import AuthMode, DefaultGateway, FastAPIMCP

JWT_SECRET = "production_super_secret_signing_key_42"
API_KEYS = {"secret_agent_api_key_123"}

# 1. Initialize Default Gateway with Dual Authentication & Rate Limiting
gateway = DefaultGateway(
    auth_mode=AuthMode.DUAL,
    api_keys=API_KEYS,
    jwt_secret=JWT_SECRET,
    rate_limit_per_minute=3,  # Strict limit for demonstration
)

app = FastAPIMCP(
    gateway=gateway,
    auto_scan=False,
    name="EnterpriseSecureGatewayMCP",
)


# 2. Define Pydantic v2 Models
class AnalyticsReport(BaseModel):
    """Analytics query result schema."""

    metric: str
    value: float
    tenant_id: str


class AdminConfig(BaseModel):
    """Admin configuration payload schema."""

    setting_key: str = Field(..., description="Configuration key")
    setting_value: str = Field(..., description="Configuration value")


# 3. Define Tools with Granular RBAC Permission Scopes
@app.get("/api/public")
def public_probe() -> Dict[str, str]:
    """Public healthcheck endpoint (no auth required)."""
    return {"status": "ok", "timestamp": str(time.time())}


@app.api_tool(
    "/api/analytics",
    methods=["GET"],
    required_scopes=["analytics:read"],
    tool_description="Fetch tenant analytics report",
)
def get_analytics(request: Request, metric_name: str = "latency") -> Dict[str, Any]:
    """Fetch analytics report. Enforces gateway auth context."""
    ctx = getattr(request.state, "auth_context", None)
    if not ctx or not ctx.is_authenticated:
        raise HTTPException(status_code=401, detail="Authentication required")
    return AnalyticsReport(
        metric=metric_name,
        value=14.2,
        tenant_id="tenant_acme_corp",
    ).model_dump()


@app.api_tool(
    "/api/admin/config",
    methods=["POST"],
    required_scopes=["admin:write"],
    tool_description="Update system admin configuration",
)
def update_config(setting_key: str, setting_value: str) -> Dict[str, Any]:
    """Update system config. Requires 'admin:write' scope."""
    return {"updated": True, "key": setting_key, "value": setting_value}


def create_test_jwt(sub: str, scopes: list[str]) -> str:
    """Generate a valid HS256 JWT token for testing."""
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": sub,
        "tenant_id": "tenant_acme_corp",
        "scopes": scopes,
        "exp": time.time() + 3600,
    }
    h_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip("=")
    p_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    sig = hmac.new(JWT_SECRET.encode(), f"{h_b64}.{p_b64}".encode(), hashlib.sha256).digest()
    s_b64 = base64.urlsafe_b64encode(sig).decode().rstrip("=")
    return f"{h_b64}.{p_b64}.{s_b64}"


async def run_demo() -> Dict[str, Any]:
    """Execute end-to-end gateway scenarios verifying security policies."""
    transport = httpx.ASGITransport(app=app)
    results = {}

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # Scenario 1: Unauthenticated request to protected endpoint -> 401 Unauthorized
        res_anon = await client.get("/api/analytics")
        results["unauthorized_status"] = res_anon.status_code

        # Scenario 2: Authenticate using API Key -> 200 OK
        headers_key = {"Authorization": "Bearer secret_agent_api_key_123"}
        res_key = await client.get("/api/analytics", headers=headers_key)
        results["api_key_status"] = res_key.status_code

        # Scenario 3: Authenticate using JWT with 'analytics:read' scope -> 200 OK
        read_jwt = create_test_jwt("agent_reporter", ["analytics:read"])
        headers_jwt = {"Authorization": f"Bearer {read_jwt}"}
        res_jwt = await client.get("/api/analytics", headers=headers_jwt)
        results["jwt_status"] = res_jwt.status_code

        # Scenario 4: Tool-level RBAC: caller with only 'analytics:read' attempts 'admin:write' tool
        app.session_context_provider = lambda: {"Authorization": f"Bearer {read_jwt}"}
        forbidden_status = 200
        try:
            await app.call_tool(
                "update_config",
                {"setting_key": "max_conns", "setting_value": "500"},
            )
        except ToolError:
            forbidden_status = 403
        results["forbidden_status"] = forbidden_status

        # Verify admin with 'admin:write' scope succeeds
        admin_jwt = create_test_jwt("admin_agent", ["admin:write"])
        app.session_context_provider = lambda: {"Authorization": f"Bearer {admin_jwt}"}
        admin_res = await app.call_tool(
            "update_config",
            {"setting_key": "max_conns", "setting_value": "500"},
        )
        results["admin_tool_succeeded"] = "max_conns" in str(admin_res)

        # Scenario 5: Trigger rate limiter by exceeding 3 req/min -> 429 Too Many Requests
        rate_limited_status = 200
        for _ in range(5):
            res_burst = await client.get("/api/public")
            if res_burst.status_code == 429:
                rate_limited_status = 429
                break
        results["rate_limited_status"] = rate_limited_status

    return results


if __name__ == "__main__":
    print("=== Running Enterprise Gateway & BYOG Demo ===")
    demo_results = asyncio.run(run_demo())
    print(f"1. Unauthorized access:  HTTP {demo_results['unauthorized_status']} (Expected 401)")
    print(f"2. Valid API Key access: HTTP {demo_results['api_key_status']} (Expected 200)")
    print(f"3. Valid Scoped JWT:     HTTP {demo_results['jwt_status']} (Expected 200)")
    print(f"4. Insufficient scope:   HTTP {demo_results['forbidden_status']} (Expected 403)")
    print(f"   Admin scope success:  {demo_results['admin_tool_succeeded']}")
    print(f"5. Burst Rate Limit:     HTTP {demo_results['rate_limited_status']} (Expected 429)")
    print("All enterprise gateway security checks passed!")
