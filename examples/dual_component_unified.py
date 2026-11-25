"""Unified Dual Component Architecture Example.

Demonstrates running the API Gateway and the MCP Gateway together in a single Python process,
single event loop, and single port:
1. REST API endpoints and MCP AI tools coexisting effortlessly.
2. Shared Pydantic v2 data models and shared FastAPI dependency injection (Depends).
3. Zero-network in-memory ASGI dispatch (sub-millisecond tool execution).
4. Direct export to Pydantic AI agents via app.to_pydantic_ai_tools().
"""

import asyncio
import json
from typing import Any, Dict

from fastapi import Depends, HTTPException
import httpx
from pydantic import BaseModel, Field

from fastapi_mcp import FastAPIMCP


# 1. Pydantic v2 Models for Products & Analytics
class ProductItem(BaseModel):
    """Product catalog data model."""

    item_id: str = Field(..., description="Unique product SKU")
    title: str = Field(..., description="Product display name")
    unit_price: float = Field(..., gt=0.0, description="Unit price in USD")
    inventory_count: int = Field(..., ge=0, description="Available stock quantity")


class DiscountEvaluation(BaseModel):
    """Discount calculation result."""

    item_id: str
    discounted_price: float
    savings_amount: float
    qualified: bool


# 2. Shared Dependency (Simulated Database Pool)
def get_catalog_database() -> Dict[str, ProductItem]:
    """Provide a shared in-memory product catalog pool."""
    return {
        "SKU-4001": ProductItem(
            item_id="SKU-4001",
            title="Enterprise AI Gateway Appliance",
            unit_price=499.00,
            inventory_count=42,
        ),
        "SKU-4002": ProductItem(
            item_id="SKU-4002",
            title="SCTP DataChannel Transceiver",
            unit_price=129.50,
            inventory_count=150,
        ),
    }


# 3. FastAPIMCP Instance in Unified Dual Mode (Default)
app = FastAPIMCP(
    auto_scan=True,
    mcp_name="UnifiedDualApp",
)


# 4. Dual `@app.api_tool` Endpoint: Serves both REST GET and MCP Tool
@app.api_tool(
    "/catalog/{item_id}",
    methods=["GET"],
    summary="Retrieve product item by SKU from catalog",
)
def get_product(
    item_id: str,
    db: Dict[str, ProductItem] = Depends(get_catalog_database),
) -> ProductItem:
    """Retrieve catalog product details."""
    if item_id not in db:
        raise HTTPException(status_code=404, detail="Product not found")
    return db[item_id]


# 5. Dedicated MCP Tool: Evaluates custom discounts
@app.tool(name="evaluate_discount", description="Compute promotional discount for a product")
def evaluate_discount(
    item_id: str,
    percent_off: float = 15.0,
) -> Dict[str, Any]:
    """Calculate discounted price for a catalog item using shared catalog data."""
    db = get_catalog_database()
    if item_id not in db:
        return {"error": f"Item {item_id} not found", "qualified": False}
    item = db[item_id]
    savings = round(item.unit_price * (percent_off / 100.0), 2)
    final_price = round(item.unit_price - savings, 2)
    return DiscountEvaluation(
        item_id=item_id,
        discounted_price=final_price,
        savings_amount=savings,
        qualified=True,
    ).model_dump()


def _extract_unified_payload(result: Any) -> Dict[str, Any]:
    """Extract dict payload from MCP CallToolResult structure."""
    if hasattr(result, "content") and result.content:
        return json.loads(result.content[0].text)
    return result if isinstance(result, dict) else {}


async def run_demo() -> Dict[str, Any]:
    """Execute end-to-end verification of the unified dual component architecture."""
    # A. Verify in-memory ASGI REST request
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        rest_resp = await client.get("/catalog/SKU-4001")
        rest_status = rest_resp.status_code
        rest_data = rest_resp.json()

    # B. Verify in-memory MCP tool invocation
    tools = await app.list_tools()
    tool_names = [t.name for t in tools]

    # Call evaluate_discount tool directly
    discount_res = await app.call_tool(
        "evaluate_discount",
        {"item_id": "SKU-4001", "percent_off": 20.0},
    )
    discount_data = _extract_unified_payload(discount_res)

    # C. Verify native Pydantic AI export
    pydantic_ai_tools = app.to_pydantic_ai_tools()

    return {
        "rest_status": rest_status,
        "rest_title": rest_data.get("title"),
        "tool_count": len(tools),
        "has_catalog_tool": "get_product" in tool_names,
        "discount_qualified": discount_data.get("qualified"),
        "discount_savings": discount_data.get("savings_amount"),
        "pydantic_ai_tools_count": len(pydantic_ai_tools),
    }


if __name__ == "__main__":
    demo_output = asyncio.run(run_demo())
    print("Unified Dual Component Demo Results:")
    for k, v in demo_output.items():
        print(f"  {k}: {v}")
