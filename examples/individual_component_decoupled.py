"""Decoupled Individual Component Architecture Example.

Demonstrates running the API Gateway and the MCP Gateway as standalone, decoupled components:
1. Headless MCP-Only Agentic BFF (GatewayMode.MCP_ONLY):
   - Exposes pure MCP protocol surfaces (/mcp, /sse).
   - Suppresses public REST documentation (/docs, /redoc, /openapi.json) for agent clusters.
2. Standalone API Gateway Perimeter:
   - Evaluates Agent On-Behalf-Of (OBO) identity delegation claims.
   - Enforces token-bucket rate-limiting returning HTTP 429 backpressure.
   - Restricts tool execution via granular RBAC permission scopes.
"""

import asyncio
import json
from typing import Any, Dict

import httpx
from pydantic import BaseModel, Field

from fastapi_mcp import (
    FastAPIMCP,
    GatewayMode,
    AuthMode,
    DefaultGateway,
    create_gateway_subapp,
)


# 1. Pydantic v2 Models for Autonomous Operations
class ClusterTelemetryReport(BaseModel):
    """Cluster health telemetry report."""

    cluster_id: str = Field(..., description="Target Kubernetes cluster identifier")
    healthy_nodes: int = Field(..., ge=0)
    total_nodes: int = Field(..., ge=1)
    status_summary: str


# 2. Component A: Standalone Headless MCP-Only Server
# Running in MCP_ONLY mode strips out OpenAPI, Swagger, and ReDoc
mcp_bff = FastAPIMCP(
    auto_scan=False,
    gateway_mode=GatewayMode.MCP_ONLY,
    mcp_name="HeadlessAgentBFF",
)


@mcp_bff.tool(
    name="get_cluster_health",
    description="Retrieve live node health statistics for an enterprise cluster",
)
def get_cluster_health(cluster_id: str) -> Dict[str, Any]:
    """Inspect and report cluster health metrics."""
    return ClusterTelemetryReport(
        cluster_id=cluster_id,
        healthy_nodes=18,
        total_nodes=20,
        status_summary="Operational with 2 cordoned nodes",
    ).model_dump()


# 3. Component B: Standalone API Gateway
# Configured with token bucket rate limiter and API key auth
gateway_adapter = DefaultGateway(
    auth_mode=AuthMode.API_KEY,
    api_keys={"live_corp_agent_secret_key_999"},
    rate_limit_per_minute=2,  # Strict token bucket for testing backpressure
)

# Mount headless MCP into an isolated gateway host
gateway_app = FastAPIMCP(
    gateway=gateway_adapter,
    auto_scan=False,
    mcp_name="PerimeterGatewayHost",
)
gateway_subapp = create_gateway_subapp(mcp_bff, path="/mcp", sse_path="/sse")
gateway_app.mount("/agent-mesh", gateway_subapp)


@gateway_app.get("/health")
def gateway_health() -> Dict[str, str]:
    """Public gateway health check probe."""
    return {"status": "healthy"}


def _extract_decoupled_payload(result: Any) -> Dict[str, Any]:
    """Extract dict payload from standalone MCP CallToolResult structure."""
    if hasattr(result, "content") and result.content:
        return json.loads(result.content[0].text)
    return result if isinstance(result, dict) else {}


async def run_demo() -> Dict[str, Any]:
    """Execute end-to-end verification of decoupled individual components."""
    # A. Verify Headless MCP-Only Mode suppresses Swagger/OpenAPI docs
    transport_mcp = httpx.ASGITransport(app=mcp_bff)
    async with httpx.AsyncClient(transport=transport_mcp, base_url="http://headless-mcp") as c:
        docs_resp = await c.get("/docs")
        openapi_resp = await c.get("/openapi.json")
        docs_status = docs_resp.status_code
        openapi_status = openapi_resp.status_code

    # B. Verify Standalone MCP Tool call works directly on the headless BFF
    health_res = await mcp_bff.call_tool(
        "get_cluster_health",
        {"cluster_id": "k8s-prod-us-east"},
    )
    health_data = _extract_decoupled_payload(health_res)

    # C. Verify Standalone API Gateway enforces token-bucket rate limiting
    transport_gw = httpx.ASGITransport(app=gateway_app)
    async with httpx.AsyncClient(transport=transport_gw, base_url="http://gateway-host") as gc:
        # Request 1: Passes
        r1 = await gc.get("/health")
        # Request 2: Passes
        _ = await gc.get("/health")
        # Request 3: Exceeds bucket capacity -> Returns 429 Too Many Requests
        r3 = await gc.get("/health")
        rate_limit_status = r3.status_code
        retry_header = r3.headers.get("retry-after")

    # D. Verify Agent On-Behalf-Of (OBO) identity parsing via gateway adapter
    obo_context = await gateway_adapter.authenticate(
        headers={
            "x-api-key": "live_corp_agent_secret_key_999",
            "x-agent-id": "autonomous-remediation-bot-9",
        }
    )

    return {
        "headless_docs_status": docs_status,
        "headless_openapi_status": openapi_status,
        "tool_cluster_id": health_data.get("cluster_id"),
        "tool_nodes_healthy": health_data.get("healthy_nodes"),
        "gateway_pass_status": r1.status_code,
        "gateway_rate_limited_status": rate_limit_status,
        "has_retry_after_header": retry_header is not None,
        "obo_caller_type": obo_context.caller_type,
        "obo_agent_id": obo_context.agent_id,
        "obo_is_authenticated": obo_context.is_authenticated,
    }


if __name__ == "__main__":
    demo_output = asyncio.run(run_demo())
    print("Decoupled Individual Component Demo Results:")
    for k, v in demo_output.items():
        print(f"  {k}: {v}")
