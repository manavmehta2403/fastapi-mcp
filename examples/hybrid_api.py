"""Hybrid FastAPI + FastMCP API.

Build applications where REST endpoints and MCP tools are first-class citizens.
- `@app.api_tool()`: Dual REST route + MCP tool (one definition, two protocols)
- `@app.tool()`: Pure MCP tool (only accessible by AI agents)
- `@app.get()` / `@app.post()`: Standard FastAPI routes
- `@app.resource()`: MCP resources
"""

from fastapi_mcp import FastAPIMCP
from pydantic import BaseModel, Field

# Create hybrid app
app = FastAPIMCP(
    title="Hybrid AI & Developer Gateway",
    mcp_name="GatewayMCP",
    description="API that serves both human developers via REST and AI agents via MCP."
)

class TranslationRequest(BaseModel):
    text: str = Field(..., description="Text to translate")
    target_language: str = Field("es", description="ISO language code, e.g., 'es', 'fr', 'de'")

# 1. Dual endpoint: accessible as POST /api/translate AND as MCP tool 'translate_text'
@app.api_tool("/api/translate", methods=["POST"], tool_name="translate_text")
async def translate(data: TranslationRequest) -> dict:
    """Translate text into target language."""
    return {
        "original": data.text,
        "translated": f"[{data.target_language.upper()}] {data.text}",
        "language": data.target_language
    }

# 2. Pure MCP tool: agent-only knowledge retrieval (no HTTP route generated)
@app.tool(name="search_internal_knowledge")
async def search_knowledge(query: str, top_k: int = 3) -> list[str]:
    """Search private company knowledge base for relevant context snippets."""
    return [
        f"Result #{i+1} for '{query}': Company policy guidelines and notes."
        for i in range(top_k)
    ]

# 3. Pure REST route: health check
@app.get("/health", tags=["system"])
async def health_check():
    """Standard health check route for load balancers."""
    return {"status": "ok", "mode": "hybrid"}

# 4. MCP Resource
@app.resource("company://config")
def get_company_config() -> str:
    """Expose company configuration as an MCP resource."""
    return '{"support_email": "support@example.com", "tier": "enterprise"}'

# Mount MCP endpoints for web clients
app.mount_mcp(path="/mcp", sse_path="/sse")

if __name__ == "__main__":
    import uvicorn
    print("Running Hybrid API Server...")
    print("  - REST Swagger UI:   http://localhost:8000/docs")
    print("  - MCP Streamable:    http://localhost:8000/mcp")
    print("  - MCP SSE Stream:    http://localhost:8000/sse")
    uvicorn.run(app, host="127.0.0.1", port=8000)
