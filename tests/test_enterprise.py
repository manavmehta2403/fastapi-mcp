import json
import pytest
from fastapi import FastAPI, Header, HTTPException, Request
from pydantic import BaseModel
from fastapi_mcp import FastAPIMCP


class ItemPayload(BaseModel):
    name: str
    price: float


def parse_mcp_result(res):
    """Helper to extract parsed JSON or text from an MCP CallToolResult."""
    if hasattr(res, "content") and res.content:
        text = res.content[0].text
        try:
            return json.loads(text)
        except Exception:
            return text
    return res


@pytest.mark.asyncio
async def test_librarian_router_pattern():
    """Verify that the Librarian pattern reduces 80+ tools down to 3 meta-tools,

    preventing context bloat while keeping all endpoints discoverable and executable.
    """
    app = FastAPI(title="LargeEnterpriseApp")

    @app.get("/billing/invoices", tags=["billing"])
    async def get_invoices():
        """Retrieve all company invoices."""
        return [{"id": 101, "amount": 450.0}]

    @app.post("/billing/invoices", tags=["billing"])
    async def create_invoice(item: ItemPayload):
        """Create a new billing invoice."""
        return {"created": True, "name": item.name, "amount": item.price}

    @app.get("/users/me", tags=["users"])
    async def get_current_user():
        """Fetch active user profile."""
        return {"username": "alice", "role": "admin"}

    @app.delete("/users/{user_id}", tags=["users"])
    async def delete_user(user_id: int):
        """Delete user account."""
        return {"deleted": user_id}

    # Bind with librarian=True
    mcp = FastAPIMCP.bind(app, librarian=True)

    # 1. Verify that only 3 Librarian meta-tools are exposed to the LLM
    tools = await mcp.list_tools()
    tool_names = [t.name for t in tools]
    assert len(tools) == 3
    assert set(tool_names) == {"list_api_categories", "search_api_tools", "execute_api_tool"}

    # 2. Test list_api_categories meta-tool
    cat_res = await mcp.call_tool("list_api_categories")
    cat_data = parse_mcp_result(cat_res)
    categories = {c["category"]: c["tool_count"] for c in cat_data["categories"]}
    assert "billing" in categories
    assert "users" in categories
    assert cat_data["total_tools"] == 4

    # 3. Test search_api_tools meta-tool
    search_res = await mcp.call_tool("search_api_tools", {"query": "invoice", "category": "billing"})
    search_data = parse_mcp_result(search_res)
    assert search_data["count"] >= 1
    tool_entry = next(t for t in search_data["tools"] if "create" in t["name"])
    assert tool_entry["path"] == "/billing/invoices"
    assert tool_entry["method"] == "POST"
    assert "item" in tool_entry["parameters"]

    # 4. Test execute_api_tool meta-tool
    exec_res = await mcp.call_tool(
        "execute_api_tool",
        {
            "tool_name": tool_entry["name"],
            "arguments": {"item": {"name": "Enterprise Subscription", "price": 999.0}},
        },
    )
    exec_data = parse_mcp_result(exec_res)
    assert exec_data["created"] is True
    assert exec_data["name"] == "Enterprise Subscription"


@pytest.mark.asyncio
async def test_dry_run_simulation_mode():
    """Verify that state-modifying routes expose dry_run simulation

    and return simulated responses with X-Dry-Run header forwarded.
    """
    app = FastAPI(title="MutationApp")

    @app.post("/orders", tags=["orders"])
    async def place_order(item: ItemPayload, request: Request):
        is_dry = request.headers.get("x-dry-run") == "true"
        return {
            "status": "simulated" if is_dry else "executed",
            "item_name": item.name,
            "cost": item.price,
        }

    mcp = FastAPIMCP.bind(app, enable_dry_run=True)

    # 1. Execute normal run
    normal_res = await mcp.call_tool("place_order", {"item": {"name": "Widget", "price": 10.0}})
    normal_data = parse_mcp_result(normal_res)
    assert normal_data["status"] == "executed"
    assert normal_data["item_name"] == "Widget"

    # 2. Execute dry-run simulation
    dry_res = await mcp.call_tool("place_order", {"item": {"name": "Widget", "price": 10.0}, "dry_run": True})
    dry_data = parse_mcp_result(dry_res)
    assert dry_data["dry_run"] is True
    assert dry_data["simulated"] is True
    assert dry_data["result"]["status"] == "simulated"


@pytest.mark.asyncio
async def test_session_context_provider_auth():
    """Verify that callers without HTTP headers (e.g. stdio or SSE) can dynamically inject

    caller authentication identity into FastAPI's ASGI request headers and dependencies.
    """
    app = FastAPI(title="SecuredApp")

    @app.get("/secure/profile")
    async def get_profile(authorization: str = Header(None)):
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Unauthorized")
        token = authorization.split(" ")[1]
        return {"authenticated": True, "tenant": token}

    # Session provider injecting dynamic Bearer token
    def mock_session_auth(kwargs=None):
        return {"Authorization": "Bearer tenant-token-corp-xyz"}

    mcp = FastAPIMCP.bind(app, session_context_provider=mock_session_auth)

    # Calling tool without headers in args gets authenticated via session_context_provider
    res = await mcp.call_tool("get_profile")
    res_data = parse_mcp_result(res)
    assert res_data["authenticated"] is True
    assert res_data["tenant"] == "tenant-token-corp-xyz"

    # Test dynamic update via set_session_context_provider
    mcp.set_session_context_provider(lambda kwargs=None: {"Authorization": "Bearer new-tenant-456"})
    res2 = await mcp.call_tool("get_profile")
    res2_data = parse_mcp_result(res2)
    assert res2_data["authenticated"] is True
    assert res2_data["tenant"] == "new-tenant-456"
