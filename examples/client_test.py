"""Example: In-Memory Client Verification.

Demonstrates calling tools programmatically on the hybrid application,
simulating what Claude Desktop or an AI agent does over MCP.
"""

import asyncio
from examples.hybrid_api import app


async def main():
    print("=== Listing Registered MCP Tools ===")
    tools = await app.list_tools()
    for t in tools:
        print(f"\nTool: {t.name}")
        print(f"  Description: {t.description}")
        print(f"  Input Schema: {list(t.input_schema.get('properties', {}).keys())}")

    print("\n=== Invoking 'translate_text' Tool via MCP ===")
    res1 = await app.call_tool(
        "translate_text",
        {"data": {"text": "Hello world from Model Context Protocol!", "target_language": "fr"}}
    )
    print("Translation result:")
    print(res1.content[0].text)

    print("\n=== Invoking 'search_internal_knowledge' Tool via MCP ===")
    res2 = await app.call_tool(
        "search_internal_knowledge",
        {"query": "AI architecture standards", "top_k": 2}
    )
    print("Knowledge search results:")
    for c in res2.content:
        print(f" - {c.text}")


if __name__ == "__main__":
    asyncio.run(main())
