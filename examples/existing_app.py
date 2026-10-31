"""Converting an Existing FastAPI App to MCP in 2 Lines.

This shows how you can take ANY standard FastAPI application with routes across
all HTTP verbs (GET, POST, PUT, PATCH, DELETE, Streaming), Pydantic models,
and Depends() injections, and automatically expose it as an MCP server for LLMs
(Claude Desktop, Cursor, Antigravity, etc.).
"""

import asyncio
from typing import Any, AsyncGenerator, Dict, Optional
from fastapi import FastAPI, Depends, Query, Path, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from fastapi_mcp import FastAPIMCP

# 1. Existing FastAPI Application
app = FastAPI(title="Inventory Management API", version="1.0.0")


class Item(BaseModel):
    """Inventory item schema."""
    name: str = Field(..., description="Name of the inventory item")
    quantity: int = Field(1, description="Stock quantity", ge=0)
    unit_price: float = Field(..., description="Price per unit", gt=0)


class ItemPatch(BaseModel):
    """Partial update schema for inventory item."""
    name: Optional[str] = Field(None, description="Updated item name")
    quantity: Optional[int] = Field(None, description="Updated stock quantity", ge=0)
    unit_price: Optional[float] = Field(None, description="Updated unit price", gt=0)


def get_db() -> Dict[str, str]:
    """Mock database connection dependency."""
    return {"status": "connected", "storage": "in-memory"}


# In-memory storage
INVENTORY: Dict[int, Dict[str, Any]] = {
    101: {"name": "Industrial Sensor", "quantity": 50, "unit_price": 45.00},
    102: {"name": "Relay Controller", "quantity": 20, "unit_price": 12.50},
}


# VERB: GET (Path parameter & Dependency Injection)
@app.get("/items/{item_id}", summary="Get inventory item (GET)")
async def get_item(
    item_id: int = Path(..., description="The unique ID of the item"),
    db: Dict[str, str] = Depends(get_db),
) -> Dict[str, Any]:
    """Retrieve an inventory item by its ID."""
    if item_id not in INVENTORY:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"item_id": item_id, "data": INVENTORY[item_id], "db": db["status"]}


# VERB: POST (Request body & Query parameter)
@app.post("/items", summary="Add new inventory item (POST)")
async def add_item(
    item: Item,
    warehouse: str = Query("central", description="Target warehouse facility"),
    db: Dict[str, str] = Depends(get_db),
) -> Dict[str, Any]:
    """Add a new item into inventory."""
    new_id = max(INVENTORY.keys(), default=100) + 1
    INVENTORY[new_id] = item.model_dump()
    return {"status": "added", "item_id": new_id, "warehouse": warehouse, "db": db["status"]}


# VERB: PUT (Full item update with Path & Body)
@app.put("/items/{item_id}", summary="Replace inventory item (PUT)")
async def replace_item(
    item_id: int = Path(..., description="The unique ID of the item"),
    item: Item = ...,
    db: Dict[str, str] = Depends(get_db),
) -> Dict[str, Any]:
    """Completely replace an existing inventory item."""
    if item_id not in INVENTORY:
        raise HTTPException(status_code=404, detail="Item not found")
    INVENTORY[item_id] = item.model_dump()
    return {
        "status": "replaced",
        "item_id": item_id,
        "data": INVENTORY[item_id],
        "db": db["status"],
    }


# VERB: PATCH (Partial item update with Path & Body)
@app.patch("/items/{item_id}", summary="Update item fields (PATCH)")
async def patch_item(
    item_id: int = Path(..., description="The unique ID of the item"),
    patch: ItemPatch = ...,
    db: Dict[str, str] = Depends(get_db),
) -> Dict[str, Any]:
    """Update specific attributes of an existing inventory item."""
    if item_id not in INVENTORY:
        raise HTTPException(status_code=404, detail="Item not found")
    target = INVENTORY[item_id]
    if patch.name is not None:
        target["name"] = patch.name
    if patch.quantity is not None:
        target["quantity"] = patch.quantity
    if patch.unit_price is not None:
        target["unit_price"] = patch.unit_price
    return {"status": "patched", "item_id": item_id, "data": target, "db": db["status"]}


# VERB: DELETE (Path parameter & Query parameter)
@app.delete("/items/{item_id}", summary="Delete inventory item (DELETE)")
async def delete_item(
    item_id: int = Path(..., description="The unique ID of the item to delete"),
    permanent: bool = Query(False, description="Whether to permanently purge"),
    db: Dict[str, str] = Depends(get_db),
) -> Dict[str, Any]:
    """Remove an item from inventory."""
    if item_id not in INVENTORY:
        raise HTTPException(status_code=404, detail="Item not found")
    removed = INVENTORY.pop(item_id)
    return {
        "status": "deleted",
        "item_id": item_id,
        "permanent": permanent,
        "removed": removed,
        "db": db["status"],
    }


# STREAMING: Server-Sent Events (SSE) route
async def inventory_audit_stream() -> AsyncGenerator[str, None]:
    """Stream real-time inventory scan logs."""
    for idx, (_, data) in enumerate(INVENTORY.items(), 1):
        await asyncio.sleep(0.05)
        item_name = data["name"]
        yield f"event: audit_log\ndata: {{\"audit_index\": {idx}, \"item\": \"{item_name}\"}}\n\n"
    yield "event: audit_finished\ndata: {\"status\": \"complete\"}\n\n"


@app.get("/items/stream/audit", summary="Stream inventory audit (SSE)")
async def stream_audit() -> StreamingResponse:
    """Stream real-time warehouse audit events via SSE."""
    return StreamingResponse(inventory_audit_stream(), media_type="text/event-stream")


# -------------------------------------------------------------
# 2. CONVERT TO MCP IN 2 LINES:
# -------------------------------------------------------------
mcp = FastAPIMCP.bind(app, name="InventoryMCP")
mcp.mount_to(app, path="/mcp", sse_path="/sse")

# Run via stdio when executed directly (e.g., configured in Claude Desktop)
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--stdio":
        mcp.run_stdio()
    else:
        import uvicorn
        print("Starting unified server on http://localhost:8000")
        print("  - REST Swagger UI:   http://localhost:8000/docs")
        print("  - MCP Streamable:    http://localhost:8000/mcp")
        print("  - MCP SSE Stream:    http://localhost:8000/sse")
        uvicorn.run(app, host="127.0.0.1", port=8000)
