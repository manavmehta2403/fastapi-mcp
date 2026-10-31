import asyncio
import httpx
from fastapi import FastAPI
from fastapi_mcp import FastAPIMCP


def test_coexistence():
    # Regular FastAPI app
    app = FastAPI(title="Coexistence Demo")

    @app.get("/api/v1/status")
    def api_status():
        return {"system": "ok", "version": "1.0.0"}

    # Bind FastMCP and mount at /mcp (streamable-http) and /sse (SSE)
    mcp = FastAPIMCP.bind(
        app,
        name="CoexistenceMCP",
        mount_path=None,
        mount_sse_path=None,
    )
    mcp.mount_to(app, path="/mcp", sse_path="/sse")

    @mcp.tool()
    def get_server_load() -> dict:
        """Fetch current server load."""
        return {"cpu_percent": 24.5, "active_threads": 4}

    async def run_checks():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. Normal FastAPI endpoint works
            resp_api = await client.get("/api/v1/status")
            assert resp_api.status_code == 200
            assert resp_api.json()["system"] == "ok"

            # 2. Verify SSE endpoints are mounted
            # /sse/sse is the SSE stream path
            # /sse/messages/ is the message post path
            routes = [getattr(r, "path", None) for r in app.routes]
            print("Mounted routes in app:", routes)
            assert "/sse" in routes
            assert "/mcp" in routes

            # 3. Call the tool via FastMCP programmatically
            res = await mcp.call_tool("get_server_load")
            assert res.is_error is False
            assert "cpu_percent" in res.content[0].text

        print("test_coexistence passed successfully!")

    asyncio.run(run_checks())


if __name__ == "__main__":
    test_coexistence()
