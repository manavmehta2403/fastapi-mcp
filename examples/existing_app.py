"""Converting an Existing FastAPI App to MCP in 2 Lines.

This shows how you can take ANY standard FastAPI application with routes,
Pydantic models, and Depends() injections, and automatically expose it as
an MCP server for LLMs (Claude Desktop, Cursor, Antigravity, etc.).
"""

from fastapi import FastAPI, Depends, Query, Path
from pydantic import BaseModel, Field
from fastapi_mcp import FastAPIMCP

# 1. Existing FastAPI Application
app = FastAPI(title="Inventory Management API", version="1.0.0")

class Item(BaseModel):
    name: str = Field(..., description="Name of the inventory item")
    quantity: int = Field(1, description="Stock quantity", ge=0)
    unit_price: float = Field(..., description="Price per unit", gt=0)

# Mock database dependency
def get_db():
    return {"status": "connected", "storage": "in-memory"}

@app.get("/items/{item_id}", summary="Get inventory item")
async def get_item(
    item_id: int = Path(..., description="The unique ID of the item"),
    db: dict = Depends(get_db)
):
    """Retrieve an inventory item by its ID."""
    return {
        "item_id": item_id,
        "name": f"Widget #{item_id}",
        "quantity": 100,
        "unit_price": 24.50,
        "db": db["status"]
    }

@app.post("/items", summary="Add new inventory item")
async def add_item(
    item: Item,
    warehouse: str = Query("central", description="Target warehouse facility"),
    db: dict = Depends(get_db)
):
    """Add a new item into inventory."""
    return {
        "status": "added",
        "item": item.model_dump(),
        "warehouse": warehouse
    }

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
