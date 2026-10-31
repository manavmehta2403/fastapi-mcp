"""Example: In-Memory Client Verification.

Demonstrates calling tools programmatically on the hybrid application across
all HTTP verbs (GET, POST, PUT, PATCH, DELETE) and pure MCP tools, simulating
what Claude Desktop, Cursor, or an autonomous AI agent does over MCP.
"""

import asyncio
from examples.hybrid_api import app


async def main() -> None:
    """Execute programmatic tool calls on the hybrid application."""
    print("==================================================")
    print("=== 1. Listing Registered FastMCP Tools ===")
    print("==================================================")
    tools = await app.list_tools()
    for t in tools:
        props = list(t.input_schema.get("properties", {}).keys())
        print(f"Tool: {t.name:<30} Schema Inputs: {props}")

    print("\n==================================================")
    print("=== 2. Invoking Dual Tool (POST): translate_text ===")
    print("==================================================")
    res_trans = await app.call_tool(
        "translate_text",
        {"data": {"text": "FastAPI and MCP work together seamlessly", "target_language": "de"}},
    )
    print(res_trans.content[0].text)

    print("\n==================================================")
    print("=== 3. Invoking Auto-Scanned Tool (POST): create_item ===")
    print("==================================================")
    res_create = await app.call_tool(
        "create_item",
        {
            "item": {
                "name": "Quantum Neural Chip",
                "category": "quantum",
                "price": 1299.99,
                "tags": ["quantum", "ai"],
            }
        },
    )
    print(res_create.content[0].text)

    print("\n==================================================")
    print("=== 4. Invoking Auto-Scanned Tool (GET): list_items (Query) ===")
    print("==================================================")
    res_list = await app.call_tool("list_items", {"category": "hardware", "limit": 2})
    print(res_list.content[0].text)

    print("\n==================================================")
    print("=== 5. Invoking Auto-Scanned Tool (PATCH): patch_item ===")
    print("==================================================")
    res_patch = await app.call_tool(
        "patch_item",
        {"item_id": 1, "patch": {"price": 449.50, "in_stock": True}},
    )
    print(res_patch.content[0].text)

    print("\n==================================================")
    print("=== 6. Invoking Pure MCP Tool: search_internal_knowledge ===")
    print("==================================================")
    res_kb = await app.call_tool(
        "search_internal_knowledge",
        {"query": "distributed edge computing", "top_k": 2},
    )
    for c in res_kb.content:
        print(f" - {c.text}")

    print("\n=== In-Memory MCP Client Verification Complete ===")


if __name__ == "__main__":
    asyncio.run(main())
