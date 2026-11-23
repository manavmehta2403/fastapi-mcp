"""Comprehensive TDD tests for Distributed Agent Mesh (app.mount_remote) in v0.7.0."""

import json
from typing import Any, Dict
import httpx
import pytest
from fastapi_mcp import FastAPIMCP, AgentMesh


def _unwrap(res: Any) -> Dict[str, Any]:
    """Helper to unwrap FastMCP CallToolResult to dict."""
    if hasattr(res, "content") and res.content:
        return json.loads(res.content[0].text)
    if isinstance(res, dict):
        return res
    return {}


@pytest.mark.asyncio
async def test_mesh_namespace_isolation_and_dispatch():
    """Verify remote tools are namespaced by prefix and dispatch successfully."""
    app = FastAPIMCP(auto_scan=False)

    def mock_billing(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/mcp/tools/invoice"
        assert request.headers["x-mcp-mesh-hops"] == "1"
        return httpx.Response(200, json={"status": "invoiced", "id": "inv_456"})

    transport = httpx.MockTransport(mock_billing)
    tools = app.mount_remote(
        url="http://billing-svc:8000/mcp",
        prefix="billing",
        tools=["invoice"],
        transport=transport,
    )

    assert "billing_invoice" in tools

    catalog = app.get_tool_catalog()
    _, _, caller = catalog["billing_invoice"]

    res = await caller(payload={"amount": 500.0})
    assert res["status"] == "invoiced"
    assert res["id"] == "inv_456"


@pytest.mark.asyncio
async def test_mesh_circular_routing_detection():
    """Verify mesh detects hop count exceeding max_hops and aborts with loop error."""
    app = FastAPIMCP(auto_scan=False)
    app.mount_remote(url="http://remote-mcp/mcp", prefix="loop", tools=["echo"])

    catalog = app.get_tool_catalog()
    _, _, caller = catalog["loop_echo"]

    # Invoke with hops already at max limit
    loop_res = await caller(payload={}, mesh_hops=5)
    assert loop_res.get("is_error") is True
    assert "circular proxy loop detected" in loop_res["error"]


@pytest.mark.asyncio
async def test_mesh_auth_token_forwarding():
    """Verify configured auth token is forwarded in Authorization Bearer header."""
    app = FastAPIMCP(auto_scan=False)

    def mock_auth(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer secret_mesh_jwt"
        return httpx.Response(200, json={"auth": "valid"})

    transport = httpx.MockTransport(mock_auth)
    app.mount_remote(
        url="http://secure-svc/mcp",
        prefix="secure",
        tools=["verify"],
        token="secret_mesh_jwt",
        transport=transport,
    )

    catalog = app.get_tool_catalog()
    _, _, caller = catalog["secure_verify"]
    res = await caller()
    assert res["auth"] == "valid"


@pytest.mark.asyncio
async def test_mesh_unreachable_downstream_resilience():
    """Verify calling an unreachable remote MCP service returns error cleanly without crash."""
    app = FastAPIMCP(auto_scan=False)
    app.mount_remote(url="http://127.0.0.1:59999/mcp", prefix="dead", tools=["ping"])

    catalog = app.get_tool_catalog()
    _, _, caller = catalog["dead_ping"]

    res = await caller()
    assert res.get("is_error") is True
    assert "unreachable" in res["error"].lower()


@pytest.mark.asyncio
async def test_mesh_downstream_http_error():
    """Verify handling of downstream HTTP error status >= 400."""
    app = FastAPIMCP(auto_scan=False)

    def mock_error(request: httpx.Request) -> httpx.Response:
        del request
        return httpx.Response(500, text="Internal Server Error")

    transport = httpx.MockTransport(mock_error)
    app.mount_remote(
        url="http://error-svc/mcp",
        prefix="err",
        tools=["fail"],
        transport=transport,
    )

    catalog = app.get_tool_catalog()
    _, _, caller = catalog["err_fail"]
    res = await caller()
    assert res.get("is_error") is True
    assert res.get("status_code") == 500
    assert "Internal Server Error" in res["error"]


@pytest.mark.asyncio
async def test_mesh_registry_listing():
    """Verify get_mounted_remotes reflects all mounted remote clusters."""
    app = FastAPIMCP(auto_scan=False)
    app.mount_remote(url="http://cluster-1/mcp", prefix="c1")
    app.mount_remote(url="http://cluster-2/mcp", prefix="c2", token="tok123")

    remotes = app.agent_mesh.get_mounted_remotes()
    assert len(remotes) == 2
    assert remotes[0]["prefix"] == "c1"
    assert remotes[1]["prefix"] == "c2"
    assert remotes[1]["token"] == "***"  # Sensitive tokens masked
