"""Showcase Hybrid FastAPI + FastMCP Application.

Demonstrates:
- All HTTP Verbs: GET, POST, PUT, PATCH, DELETE
- Parameter Types: Path parameters, Query parameters, Request Body (Pydantic)
- Streaming: Server-Sent Events (SSE) and Chunked Token/Text Streaming
- Dual Endpoints: @app.api_tool() for simultaneous REST + MCP tool exposure
- Pure MCP Tools: @app.tool() for agent-only knowledge/actions
- MCP Resources & Prompts: @app.resource() and @app.prompt()
- Native MCP Protocol Endpoints: /mcp (Streamable HTTP) and /sse (SSE Transport)
"""

import asyncio
from typing import Any, AsyncGenerator, Dict, List, Optional
from fastapi import HTTPException, Path, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from fastapi_mcp import FastAPIMCP

# ---------------------------------------------------------------------------
# 1. Initialize Hybrid Application
# ---------------------------------------------------------------------------
app = FastAPIMCP(
    title="Omni-Channel Hybrid API & MCP Gateway",
    mcp_name="GatewayMCP",
    description=(
        "Full showcase supporting all HTTP verbs (GET, POST, PUT, PATCH, DELETE), "
        "Path/Query parameters, Server-Sent Events, Chunked Streaming, and FastMCP."
    ),
    version="1.0.0",
)


# ---------------------------------------------------------------------------
# 2. Pydantic Request & Response Schemas
# ---------------------------------------------------------------------------
class ItemCreate(BaseModel):
    """Payload to create a new catalog item."""

    name: str = Field(..., description="Item name")
    category: str = Field("electronics", description="Category tag")
    price: float = Field(..., gt=0, description="Unit price in USD")
    tags: List[str] = Field(default_factory=list, description="Descriptive tags")


class ItemUpdate(BaseModel):
    """Payload for full PUT update of an existing item."""

    name: str = Field(..., description="Updated item name")
    category: str = Field(..., description="Updated category tag")
    price: float = Field(..., gt=0, description="Updated unit price")
    in_stock: bool = Field(True, description="Inventory availability flag")


class ItemPatch(BaseModel):
    """Payload for partial PATCH update of an existing item."""

    name: Optional[str] = Field(None, description="Optional new name")
    price: Optional[float] = Field(None, gt=0, description="Optional new price")
    in_stock: Optional[bool] = Field(None, description="Optional availability flag")


class TranslationRequest(BaseModel):
    """Payload for language translation."""

    text: str = Field(..., description="Text string to translate")
    target_language: str = Field("es", description="Target ISO-639-1 language code")


# In-memory mock database
ITEMS_DB: Dict[int, Dict[str, Any]] = {
    1: {
        "id": 1,
        "name": "AI Accelerator Pro",
        "category": "hardware",
        "price": 499.99,
        "in_stock": True,
        "tags": ["gpu", "ai"],
    },
    2: {
        "id": 2,
        "name": "Smart Edge Sensor",
        "category": "iot",
        "price": 89.50,
        "in_stock": True,
        "tags": ["sensor", "edge"],
    },
    3: {
        "id": 3,
        "name": "Neural Compute Stick",
        "category": "hardware",
        "price": 129.00,
        "in_stock": False,
        "tags": ["usb", "ai"],
    },
}


# ---------------------------------------------------------------------------
# 3. Standard REST Routes & All HTTP Verbs
# ---------------------------------------------------------------------------

# VERB: GET (with Query Parameters)
@app.get("/api/items", tags=["items"], summary="List and filter items with Query parameters")
async def list_items(
    category: Optional[str] = Query(None, description="Filter items by category"),
    min_price: Optional[float] = Query(None, ge=0, description="Filter items by minimum price"),
    limit: int = Query(10, ge=1, le=50, description="Maximum number of items to return"),
) -> List[Dict[str, Any]]:
    """Retrieve catalog items filtered by query parameters."""
    results = list(ITEMS_DB.values())
    if category:
        results = [item for item in results if item["category"].lower() == category.lower()]
    if min_price is not None:
        results = [item for item in results if item["price"] >= min_price]
    return results[:limit]


# VERB: GET (with Path Parameter)
@app.get("/api/items/{item_id}", tags=["items"], summary="Get item by ID with Path parameter")
async def get_item(
    item_id: int = Path(..., description="Unique integer ID of the item"),
) -> Dict[str, Any]:
    """Retrieve a single item by its ID."""
    if item_id not in ITEMS_DB:
        raise HTTPException(status_code=404, detail=f"Item with ID {item_id} not found")
    return ITEMS_DB[item_id]


# VERB: POST (with Request Body)
@app.post("/api/items", tags=["items"], summary="Create item with Request Body", status_code=201)
async def create_item(item: ItemCreate) -> Dict[str, Any]:
    """Create a new item in the catalog."""
    new_id = max(ITEMS_DB.keys(), default=0) + 1
    new_record = {
        "id": new_id,
        "name": item.name,
        "category": item.category,
        "price": item.price,
        "in_stock": True,
        "tags": item.tags,
    }
    ITEMS_DB[new_id] = new_record
    return {"status": "created", "item": new_record}


# VERB: PUT (Full Update with Path Parameter and Body)
@app.put("/api/items/{item_id}", tags=["items"], summary="Full item update (PUT)")
async def update_item(
    item_id: int = Path(..., description="ID of the item to update"),
    item: ItemUpdate = ...,
) -> Dict[str, Any]:
    """Completely replace the record of an existing item."""
    if item_id not in ITEMS_DB:
        raise HTTPException(status_code=404, detail=f"Item with ID {item_id} not found")
    updated_record = {
        "id": item_id,
        "name": item.name,
        "category": item.category,
        "price": item.price,
        "in_stock": item.in_stock,
        "tags": ITEMS_DB[item_id].get("tags", []),
    }
    ITEMS_DB[item_id] = updated_record
    return {"status": "updated", "item": updated_record}


# VERB: PATCH (Partial Update with Path Parameter and Body)
@app.patch("/api/items/{item_id}", tags=["items"], summary="Partial item update (PATCH)")
async def patch_item(
    item_id: int = Path(..., description="ID of the item to patch"),
    patch: ItemPatch = ...,
) -> Dict[str, Any]:
    """Partially update specific fields of an existing item."""
    if item_id not in ITEMS_DB:
        raise HTTPException(status_code=404, detail=f"Item with ID {item_id} not found")
    record = ITEMS_DB[item_id]
    if patch.name is not None:
        record["name"] = patch.name
    if patch.price is not None:
        record["price"] = patch.price
    if patch.in_stock is not None:
        record["in_stock"] = patch.in_stock
    return {"status": "patched", "item": record}


# VERB: DELETE (with Path and Query Parameters)
@app.delete("/api/items/{item_id}", tags=["items"], summary="Delete item (DELETE)")
async def delete_item(
    item_id: int = Path(..., description="ID of the item to remove"),
    hard_delete: bool = Query(False, description="Permanent wipe if true; soft archival if false"),
) -> Dict[str, Any]:
    """Remove or archive an item by ID."""
    if item_id not in ITEMS_DB:
        raise HTTPException(status_code=404, detail=f"Item with ID {item_id} not found")
    removed = ITEMS_DB.pop(item_id)
    return {
        "status": "deleted",
        "hard_delete": hard_delete,
        "deleted_id": item_id,
        "name": removed["name"],
    }


# ---------------------------------------------------------------------------
# 4. Dual Endpoints (@app.api_tool): REST + MCP Tool in One Definition
# ---------------------------------------------------------------------------


@app.api_tool("/api/translate", methods=["POST"], tool_name="translate_text")
async def translate(data: TranslationRequest) -> Dict[str, Any]:
    """Translate text into target language (callable via REST POST and MCP tool)."""
    return {
        "original": data.text,
        "translated": f"[{data.target_language.upper()}] {data.text}",
        "language": data.target_language,
    }


@app.api_tool(
    "/api/items/{item_id}/discount",
    methods=["PATCH"],
    tool_name="apply_item_discount",
)
async def apply_item_discount(
    item_id: int = Path(..., description="ID of item to discount"),
    percentage: float = Query(10.0, ge=1.0, le=90.0, description="Discount percentage"),
) -> Dict[str, Any]:
    """Apply a promotional discount to an item's price."""
    if item_id not in ITEMS_DB:
        raise HTTPException(status_code=404, detail=f"Item {item_id} not found")
    old_price = ITEMS_DB[item_id]["price"]
    new_price = round(old_price * (1.0 - (percentage / 100.0)), 2)
    ITEMS_DB[item_id]["price"] = new_price
    return {
        "item_id": item_id,
        "old_price": old_price,
        "discount_percentage": percentage,
        "new_price": new_price,
    }


# ---------------------------------------------------------------------------
# 5. Streaming Endpoints: SSE Streams and Chunked Token Streams
# ---------------------------------------------------------------------------


async def sse_event_generator(
    total_events: int = 4, delay_sec: float = 0.05
) -> AsyncGenerator[str, None]:
    """Generate Server-Sent Events with structured event names and JSON data."""
    for i in range(1, total_events + 1):
        await asyncio.sleep(delay_sec)
        msg = f'{{"step": {i}, "status": "processing step {i} of {total_events}"}}'
        yield f"event: task_update\ndata: {msg}\n\n"
    complete_msg = f'{{"status": "completed", "total_steps": {total_events}}}'
    yield f"event: task_complete\ndata: {complete_msg}\n\n"


@app.get("/api/events/sse", tags=["streaming"], summary="Server-Sent Events (SSE) Stream")
async def stream_sse_events(
    events: int = Query(4, ge=1, le=10, description="Number of SSE events to stream"),
) -> StreamingResponse:
    """Stream real-time updates using the W3C Server-Sent Events (SSE) protocol."""
    return StreamingResponse(
        sse_event_generator(total_events=events),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def chunked_token_generator(prompt: str) -> AsyncGenerator[str, None]:
    """Simulate streaming response tokens (e.g., from an LLM inference loop)."""
    tokens = [
        f"Thinking about: '{prompt}'... ",
        "Analyzing parameters. ",
        "Generating hybrid MCP response. ",
        "Execution verified successfully. ",
        "[DONE]",
    ]
    for token in tokens:
        await asyncio.sleep(0.05)
        yield token


@app.get("/api/stream/tokens", tags=["streaming"], summary="Chunked Token/Text Streaming")
async def stream_tokens(
    prompt: str = Query("FastAPI and MCP architecture", description="Seed prompt for streaming"),
) -> StreamingResponse:
    """Stream raw token chunks (simulates LLM or data pipeline streaming)."""
    return StreamingResponse(
        chunked_token_generator(prompt=prompt),
        media_type="text/plain",
        headers={"Transfer-Encoding": "chunked"},
    )


# ---------------------------------------------------------------------------
# 6. Pure MCP Tools, Resources & Prompts (Agent-Only)
# ---------------------------------------------------------------------------


@app.tool(name="search_internal_knowledge")
async def search_knowledge(query: str, top_k: int = 3) -> List[str]:
    """Agent-only tool: Search internal company knowledge base without exposing a REST route."""
    return [
        f"Knowledge snippet #{i+1} for '{query}': Corporate policy guidelines."
        for i in range(top_k)
    ]


@app.resource("company://config")
def get_company_config() -> str:
    """MCP Resource: Expose static company configuration to connected AI agents."""
    return '{"support_email": "support@example.com", "tier": "enterprise", "mcp_version": "2.0"}'


@app.prompt("customer_support_prompt")
def customer_support_prompt(customer_name: str, issue_summary: str) -> str:
    """MCP Prompt: Generate standardized AI prompt for customer support interactions."""
    return (
        f"You are a helpful customer support agent for Enterprise Cloud.\n"
        f"Customer: {customer_name}\n"
        f"Issue: {issue_summary}\n"
        f"Please provide an empathetic, actionable resolution."
    )


# ---------------------------------------------------------------------------
# 7. Mount Native FastMCP Protocol Transports
# ---------------------------------------------------------------------------
app.mount_mcp(path="/mcp", sse_path="/sse")


# ---------------------------------------------------------------------------
# 8. Direct Execution Entrypoint
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    print("\n" + "=" * 65)
    print("  OMNI-CHANNEL FASTAPI + MCP HYBRID SERVER RUNNING")
    print("=" * 65)
    print("  - REST Swagger UI:      http://127.0.0.1:8000/docs")
    print("  - Interactive MCP UI:   http://127.0.0.1:8000/mcp/docs")
    print("  - SSE Stream Route:     http://127.0.0.1:8000/api/events/sse")
    print("  - Token Stream Route:   http://127.0.0.1:8000/api/stream/tokens")
    print("  - MCP Streamable HTTP:  http://127.0.0.1:8000/mcp")
    print("  - MCP SSE Transport:    http://127.0.0.1:8000/sse")
    print("=" * 65 + "\n")
    uvicorn.run(app, host="127.0.0.1", port=8000)
