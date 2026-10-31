import asyncio
import httpx
from pydantic import BaseModel
from fastapi_mcp import FastAPIMCP


def test_hybrid_mode():
    app = FastAPIMCP(title="Hybrid Application", mcp_name="CalculatorService")

    # 1. Dual endpoint: both a REST endpoint AND an MCP tool!
    class MathRequest(BaseModel):
        x: float
        y: float

    @app.api_tool("/math/add", methods=["POST"], tool_name="calculate_add")
    async def add_numbers(data: MathRequest) -> dict:
        """Add two numbers together."""
        return {"result": data.x + data.y, "operation": "add"}

    # 2. Pure MCP tool: only accessible via MCP, not added to FastAPI HTTP routes
    @app.tool(name="secret_agent_tool")
    def agent_tool(query: str) -> str:
        """Internal tool for LLM agent reasoning."""
        return f"Agent reasoned: {query[::-1]}"

    # 3. Pure FastAPI REST route: not converted if auto_scan=False or excluded
    @app.get("/health")
    async def health():
        return {"status": "healthy", "service": "calculator"}

    async def run_checks():
        # A. Test HTTP routes using httpx
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            # Test /health
            r_health = await client.get("/health")
            assert r_health.status_code == 200
            assert r_health.json() == {"status": "healthy", "service": "calculator"}

            # Test /math/add via HTTP POST
            r_add = await client.post("/math/add", json={"x": 15.5, "y": 4.5})
            assert r_add.status_code == 200
            assert r_add.json()["result"] == 20.0

            # Test that secret_agent_tool is NOT an HTTP route
            r_secret = await client.get("/secret_agent_tool")
            assert r_secret.status_code == 404

        # B. Test MCP tools
        tools = await app.list_tools()
        tool_names = [t.name for t in tools]
        print("Hybrid registered tools:", tool_names)

        assert "calculate_add" in tool_names
        assert "secret_agent_tool" in tool_names

        # Call calculate_add via MCP
        res1 = await app.call_tool("calculate_add", {"data": {"x": 100.0, "y": 25.0}})
        assert res1.is_error is False
        assert "125.0" in res1.content[0].text

        # Call secret_agent_tool via MCP
        res2 = await app.call_tool("secret_agent_tool", {"query": "hello world"})
        assert res2.is_error is False
        assert "dlrow olleh" in res2.content[0].text

        print("test_hybrid_mode passed successfully!")

    asyncio.run(run_checks())


if __name__ == "__main__":
    test_hybrid_mode()
