import asyncio
import httpx
from fastapi import FastAPI
from fastapi_mcp import FastAPIMCP


def test_mcp_swagger_ui():
    app = FastAPI(title="UI Test App")

    @app.get("/calc/add")
    def add(a: int, b: int = 5):
        """Add two numbers."""
        return {"sum": a + b}

    mcp = FastAPIMCP.bind(app, name="UIExplorerDemo")
    # mount_to automatically registered /mcp/docs and /mcp/ui/call

    async def run_checks():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. Test /mcp/docs returns 200 and HTML with title
            res_docs = await client.get("/mcp/docs")
            assert res_docs.status_code == 200
            assert "text/html" in res_docs.headers["content-type"]
            assert "MCP Swagger Explorer" in res_docs.text
            assert "UIExplorerDemo" in res_docs.text
            assert "add" in res_docs.text

            # 2. Test live UI tool execution via /mcp/ui/call
            res_call = await client.post(
                "/mcp/ui/call",
                json={"name": "add", "arguments": {"a": 10, "b": 20}},
            )
            assert res_call.status_code == 200
            data = res_call.json()
            assert data["success"] is True
            assert data["result"]["sum"] == 30

        print("test_mcp_swagger_ui passed successfully!")

    asyncio.run(run_checks())


if __name__ == "__main__":
    test_mcp_swagger_ui()
