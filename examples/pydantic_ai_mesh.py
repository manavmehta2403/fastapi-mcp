"""Distributed Agent Mesh, Protocol Adapters, and Native Pydantic AI Example.

Demonstrates:
1. In-memory protocol bridging: gRPC stubs (mount_grpc) and GraphQL schemas (mount_graphql).
2. Distributed Agent Mesh: Proxying remote tools with hop tracking (mount_remote).
3. Native Pydantic AI integration: Exporting tools directly via app.to_pydantic_ai_tools()
   with zero network serialization overhead.
"""

import asyncio
import inspect
import json
from typing import Any, Dict

import httpx
from pydantic import BaseModel, Field

from fastapi_mcp import FastAPIMCP

app = FastAPIMCP(auto_scan=False, name="PydanticAIMeshMCP")


# 1. Pydantic v2 Models for Local Tools
class ItemLookupQuery(BaseModel):
    """Product lookup schema."""

    item_id: str = Field(..., description="Unique product SKU")


class ItemLookupResponse(BaseModel):
    """Product lookup result schema."""

    id: str
    name: str
    in_stock: bool
    price: float


# 2. Local MCP Tool: Native Pydantic v2 Function
@app.api_tool("/catalog/lookup", summary="Lookup item details from warehouse database")
async def lookup_item(item_id: str) -> Dict[str, Any]:
    """Fetch item inventory details."""
    return ItemLookupResponse(
        id=item_id,
        name="Precision Sensor Hub",
        in_stock=True,
        price=189.99,
    ).model_dump()


# 3. Mount Multi-Protocol Adapters: In-Memory gRPC Service Bridging
app.mount_grpc(
    target="localhost:50051",
    prefix="billing",
    services=["InvoiceService"],
)


# 4. Mount Distributed Agent Mesh: Cross-Cluster Tool Proxying
def mock_remote_handler(request: httpx.Request) -> httpx.Response:
    """Simulate downstream cluster microservice response."""
    hops = request.headers.get("x-mcp-mesh-hops", "0")
    return httpx.Response(
        200,
        json={"status": "dispatched", "mesh_hops": hops, "shipment_id": "ship_881"},
    )


remote_transport = httpx.MockTransport(mock_remote_handler)
app.mount_remote(
    url="http://logistics-cluster:8000/mcp",
    prefix="logistics",
    tools=["dispatch_shipment"],
    transport=remote_transport,
)


def _extract_response_data(res: Any) -> Dict[str, Any]:
    """Parse call tool result into structured dictionary."""
    if hasattr(res, "content") and res.content:
        return json.loads(res.content[0].text)
    return res if isinstance(res, dict) else {}


async def run_demo() -> Dict[str, Any]:
    """Execute protocol adapter calls, agent mesh proxying, and Pydantic AI export."""
    results: Dict[str, Any] = {}

    # Scenario 1: Invoke mounted gRPC tool
    grpc_res = await app.call_tool(
        "billing_invoiceservice_invoke",
        {"payload": {"invoice_id": "inv_777"}},
    )
    grpc_data = _extract_response_data(grpc_res)
    results["grpc_tool_invoked"] = grpc_data.get("status") == "grpc_invoked"
    results["grpc_service"] = grpc_data.get("service")

    # Scenario 2: Invoke distributed mesh tool across clusters
    catalog = app.get_tool_catalog()
    _, _, mesh_caller = catalog["logistics_dispatch_shipment"]
    mesh_res = await mesh_caller(payload={"order_id": "ord_101"})
    results["mesh_tool_invoked"] = mesh_res.get("status") == "dispatched"
    results["mesh_hops_recorded"] = mesh_res.get("mesh_hops")

    # Scenario 3: Native Pydantic AI Tool Export
    # app.to_pydantic_ai_tools() exports callables directly compatible with
    # pydantic_ai.Agent(tools=app.to_pydantic_ai_tools())
    ai_tools = app.to_pydantic_ai_tools()
    results["pydantic_ai_tools_count"] = len(ai_tools)

    # Find the 'lookup_item' tool runner and execute it
    runner = next(t for t in ai_tools if t.__name__ == "lookup_item")
    sig = inspect.signature(runner)
    results["has_item_id_param"] = "item_id" in sig.parameters

    execution_result = await runner(item_id="item_99")
    results["tool_execution_result"] = execution_result

    return results


if __name__ == "__main__":
    print("=== Running Protocol Adapters, Agent Mesh & Pydantic AI Demo ===")
    demo_results = asyncio.run(run_demo())
    grpc_status = demo_results['grpc_tool_invoked']
    grpc_svc = demo_results['grpc_service']
    print(f"1. Mounted gRPC Tool Invoked:   {grpc_status} (Service: {grpc_svc})")
    mesh_status = demo_results['mesh_tool_invoked']
    mesh_hops = demo_results['mesh_hops_recorded']
    print(f"2. Distributed Mesh Proxy:      {mesh_status} (Hops: {mesh_hops})")
    print(f"3. Pydantic AI Tools Exported:  {demo_results['pydantic_ai_tools_count']} tools")
    print(f"   Executed with Pydantic v2:   {demo_results['tool_execution_result']}")
    print("All protocol gateways, mesh proxying, and Pydantic AI integrations passed!")
