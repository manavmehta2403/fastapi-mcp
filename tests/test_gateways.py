"""Comprehensive TDD tests for Protocol Gateways (gRPC & GraphQL) in v0.6.0."""

import json
from typing import Any, Dict
import httpx
import pytest
from fastapi_mcp import FastAPIMCP, ProtocolGateway


def _unwrap(res: Any) -> Dict[str, Any]:
    """Helper to unwrap FastMCP CallToolResult to dict."""
    if hasattr(res, "content") and res.content:
        return json.loads(res.content[0].text)
    if isinstance(res, dict):
        return res
    return {}


@pytest.mark.asyncio
async def test_mount_grpc_auto_discovery_and_invoke():
    """Verify mount_grpc creates namespaced tools and executes calls with arguments."""
    app = FastAPIMCP(auto_scan=False)
    tools = app.mount_grpc(target="localhost:50051", prefix="billing", services=["InvoiceService"])

    assert len(tools) == 1
    assert tools[0] == "billing_invoiceservice_invoke"

    call_res = await app.call_tool(
        "billing_invoiceservice_invoke", {"payload": {"account_id": "acc_99"}}
    )
    data = _unwrap(call_res)
    assert data["status"] == "grpc_invoked"
    assert data["service"] == "InvoiceService"
    assert data["arguments"]["account_id"] == "acc_99"


@pytest.mark.asyncio
async def test_mount_graphql_operations_and_error_handling():
    """Verify mount_graphql creates query/mutation tools and handles unreachable targets gracefully."""
    app = FastAPIMCP(auto_scan=False)
    tools = app.mount_graphql(url="http://127.0.0.1:59999/graphql", prefix="catalog")

    assert "catalog_query" in tools
    assert "catalog_mutation" in tools

    # Call against an unreachable server to verify resilient error return without crash
    call_res = await app.call_tool("catalog_query", {"query": "{ products { id } }"})
    data = _unwrap(call_res)
    assert data.get("is_error") is True
    assert "unreachable" in data["error"].lower()


@pytest.mark.asyncio
async def test_mount_graphql_successful_dispatch():
    """Verify mount_graphql successfully dispatches when downstream responds."""
    app = FastAPIMCP(auto_scan=False)

    # Use a custom handler or mock via httpx transport
    mock_resp = {"data": {"user": {"name": "Alice"}}}

    def mock_handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer mock_token"
        return httpx.Response(200, json=mock_resp)

    transport = httpx.MockTransport(mock_handler)
    app.mount_graphql(
        url="http://mock-graphql/graphql",
        prefix="users",
        default_headers={"authorization": "Bearer mock_token"},
        transport=transport,
    )

    # Patch the caller's httpx client with mock transport
    catalog = app.get_tool_catalog()
    _, _, caller = catalog["users_query"]

    # Test direct execution with headers
    data = await caller(query="{ user { name } }")
    assert "data" in data
    assert data["data"]["user"]["name"] == "Alice"


@pytest.mark.asyncio
async def test_get_mounted_gateways_catalog():
    """Verify gateway catalog tracks all mounted gRPC and GraphQL services."""
    app = FastAPIMCP(auto_scan=False)
    app.mount_grpc(target="internal-grpc:50051", prefix="auth")
    app.mount_graphql(url="https://api.test/graphql", prefix="store")

    gateways = app.gateways.get_mounted_gateways()
    assert len(gateways) == 2
    types = [g["type"] for g in gateways]
    assert "grpc" in types
    assert "graphql" in types
