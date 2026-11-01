# FastAPI-MCP ⚡🤖

<p align="center">
  <b>The unified bridge between FastAPI and FastMCP / Model Context Protocol.</b><br>
  <i>Serve REST APIs and MCP AI Tools simultaneously from a single server with zero resource overhead.</i>
</p>

<p align="center">
  <a href="#-key-highlights"><img src="https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi&logoColor=white" alt="FastAPI"></a>
  <a href="#-key-highlights"><img src="https://img.shields.io/badge/MCP-Protocol-blueviolet?style=flat" alt="MCP"></a>
  <a href="#-key-highlights"><img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white" alt="Python"></a>
  <a href="#license"><img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License"></a>
</p>

---

## 🌟 Key Highlights

* 🤝 **True Protocol Coexistence**: Serve your REST API (OpenAPI/Swagger docs), MCP Server-Sent Events (SSE), and Streamable HTTP endpoints from a **single Uvicorn process and single port**.
* 🛠️ **Dual `@app.api_tool` Decorator**: Define an endpoint once — it instantly becomes both an HTTP REST endpoint for web clients and an MCP tool for AI agents (Claude, Cursor, Antigravity).
* 🔄 **2-Line Existing App Conversion**: Point to any existing FastAPI application and automatically expose its endpoints as MCP tools with zero changes to your existing code.
* 📖 **Built-in MCP Swagger Explorer (`/mcp/docs`)**: An interactive visual playground for testing MCP tools right alongside FastAPI's `/docs`. Inspect parameters and execute tools live with "Try it out" in your browser.
* ⚡ **Zero-Network In-Memory Dispatch**: In-memory ASGI transport executes tool calls directly without TCP socket loopbacks, preserving FastAPI `Depends()` injections, auth, and Pydantic validation.

---

## 💡 Why a Single Server Architecture? (Resource & Performance Benefits)

Running separate microservices or independent processes for REST and MCP introduces unnecessary infrastructure complexity and resource waste:

### 1. Zero Process Multiplication & Low Memory Footprint
A typical Python web server process uses 60–150 MB of RAM at boot. Running a separate server process for MCP doubles baseline memory consumption and CPU thread contention. With `fastapi-mcp`, everything runs in a **single shared event loop**, conserving memory on budget VMs and cloud containers.

### 2. Zero-Network In-Memory Execution
When an AI agent triggers an MCP tool that maps to a FastAPI route, `fastapi-mcp` dispatches the request through an **in-memory ASGI pipeline (`httpx.ASGITransport`)**:
- No TCP socket handshakes
- No loopback network latency
- Sub-millisecond execution speeds

### 3. Shared Database Pools & Dependencies
Instead of maintaining two independent database connection pools (one for your REST API and one for your MCP server), your MCP tools directly reuse the existing FastAPI `Depends(get_db)` connection pool and caching layers.

### 4. Single Source of Truth for Schemas
You define your Pydantic v2 data models once. Both your OpenAPI specification (`/docs`) and your MCP tool definitions (`/mcp/docs`) are generated from the exact same model definitions without drift.

---

## 🏗️ Architecture Overview

```
                                  +-----------------------+
                                  |   AI Agent / Client   |
                                  | (Claude Desktop, Cursor|
                                  +-----------+-----------+
                                              |
                     +------------------------+-----------------------+
                     | (HTTP / SSE)                                   | (stdio)
                     v                                                v
+--------------------+---------------------+        +-----------------+---------------------+
|        FastAPI ASGI Server (Uvicorn)     |        |      fastapi-mcp CLI (stdio)          |
|  - Swagger UI: /docs                     |        |  (Direct pipe for desktop LLM agents) |
|  - REST Endpoints: /items, /users        |        +-----------------+---------------------+
|  - MCP Streamable: /mcp                  |                          |
|  - MCP SSE Stream: /sse                  |                          |
|  - MCP Swagger Explorer: /mcp/docs       |                          |
+--------------------+---------------------+                          |
                     |                                                |
                     +------------------------+-----------------------+
                                              |
                                              v
                              +---------------+---------------+
                              |    FastAPIMCP Unified Hub     |
                              +---------------+---------------+
                                              |
                    +-------------------------+-------------------------+
                    |                                                   |
                    v                                                   v
+-------------------+--------------------+            +-----------------+-------------------+
|      Route Scanner & Dynamic Tools     |            |         Native MCP Tools            |
| - Inspects Path, Query, Body, Headers  |            | - @app.tool()                       |
| - Filters out Depends(db), Request     |            | - @app.resource()                   |
| - Preserves Pydantic Schema & Docstrings|           | - @app.prompt()                     |
+-------------------+--------------------+            +-----------------+-------------------+
                    |                                                   |
                    v                                                   v
+-------------------+---------------------------------------------------+-------------------+
|                           In-Memory ASGITransport Dispatcher                              |
|   Resolves Depends() -> Validates Schema -> Invokes Route -> Returns Structured Result    |
+-------------------------------------------------------------------------------------------+
```

---

## 📦 Installation

```bash
pip install fastapi-fastmcp
```

*(Works with the latest releases of `fastapi`, `mcp`, `pydantic`, `httpx`, and `uvicorn`)*

---

## 🚀 Quickstart Guides

### Pattern 1: Convert an Existing FastAPI App (2 Lines)

Take any existing FastAPI application with routes, database sessions, and dependencies, and expose it to AI agents:

```python
from fastapi import FastAPI, Depends, Query, Path
from pydantic import BaseModel, Field
from fastapi_mcp import FastAPIMCP

app = FastAPI(title="Store API")

class Item(BaseModel):
    name: str = Field(..., description="Product title")
    price: float = Field(..., description="Product price")

def get_db():
    return {"status": "connected"}

@app.get("/items/{item_id}", summary="Get item details")
async def get_item(
    item_id: int = Path(..., description="Unique product ID"),
    verbose: bool = Query(False, description="Include detailed specs"),
    db: dict = Depends(get_db)  # Auto-resolved in-memory, hidden from LLM schema!
):
    """Retrieve item details by ID."""
    return {"id": item_id, "verbose": verbose, "db": db["status"]}

@app.post("/items", summary="Create item")
async def create_item(item: Item, db: dict = Depends(get_db)):
    """Create a new item in the catalog."""
    return {"status": "created", "item": item.model_dump()}

# -------------------------------------------------------------
# 🌟 CONVERT & MOUNT IN 2 LINES:
# -------------------------------------------------------------
mcp = FastAPIMCP.bind(app, name="StoreMCP")
mcp.mount_to(app, path="/mcp", sse_path="/sse")
```

---

### Pattern 2: Hybrid Dual API (`@app.api_tool`)

Build new services where functions are simultaneously REST endpoints and MCP tools:

```python
from fastapi_mcp import FastAPIMCP
from pydantic import BaseModel, Field

# FastAPIMCP is a drop-in replacement for FastAPI
app = FastAPIMCP(title="Hybrid Service", mcp_name="UnifiedServer")

class CalculateRequest(BaseModel):
    x: float = Field(..., description="First operand")
    y: float = Field(..., description="Second operand")
    op: str = Field("add", description="Operation: 'add', 'sub', 'mul', 'div'")

# 1. 🛠️ DUAL ENDPOINT: Accessible via REST POST /math/calc AND as MCP Tool 'calculate'
@app.api_tool("/math/calc", methods=["POST"], tool_name="calculate")
async def calculate(data: CalculateRequest) -> dict:
    """Perform mathematical calculations."""
    if data.op == "add":
        res = data.x + data.y
    elif data.op == "mul":
        res = data.x * data.y
    else:
        res = data.x - data.y
    return {"result": res, "op": data.op}

# 2. 🧩 PURE MCP TOOL: Agent-only tool (hidden from public REST routes)
@app.tool(name="internal_rag_search")
async def internal_search(query: str) -> list[str]:
    """Search internal documentation."""
    return [f"Article match for '{query}'"]

# 3. 🌐 PURE REST ROUTE: Standard FastAPI route
@app.get("/health")
async def health():
    return {"status": "ok"}

# Mount MCP endpoints onto the server
app.mount_mcp(path="/mcp", sse_path="/sse")
```

---

## 🌐 Deployment Options

### Option A: Single Port Deployment (Default & Recommended)
Serve both your REST API and MCP transports from the same port:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

Available endpoints on port 8000:
* **FastAPI Swagger UI**: `http://localhost:8000/docs`
* **MCP Swagger Explorer**: `http://localhost:8000/mcp/docs`
* **MCP Streamable HTTP**: `http://localhost:8000/mcp`
* **MCP Server-Sent Events (SSE)**: `http://localhost:8000/sse`

---

### Option B: Split Port Deployment (Network Segmentation)
If your infrastructure requires keeping internal AI traffic on an isolated private port while serving public REST traffic externally:

```python
import uvicorn
import threading

# Serve REST on public port 8000, and MCP on internal port 9000
def run_rest():
    uvicorn.run(app, host="0.0.0.0", port=8000)

def run_mcp():
    # Run standalone MCP SSE or streamable app on isolated port
    mcp_app = mcp.mcp_server.streamable_http_app()
    uvicorn.run(mcp_app, host="127.0.0.1", port=9000)

if __name__ == "__main__":
    threading.Thread(target=run_mcp, daemon=True).start()
    run_rest()
```

---

## 📖 Dual-Engine MCP Swagger Explorer (`/mcp/docs` & `/mcp/ui`)

FastAPI-MCP provides a seamless, hybrid documentation experience for your Model Context Protocol tools:

1. **Official Swagger UI (`/mcp/docs`)**:
   - The literal, official Swagger UI powered by OpenAPI 3.1.
   - Built-in `curl` command generator, request schema validation, and "Try it out" live execution directly into `/mcp/tools/{tool_name}`.
   - Groups tools cleanly by route tags or under `MCP Tools`.

2. **100% Offline Standalone Explorer (`/mcp/ui`)**:
   - Zero-CDN, air-gapped standalone HTML/CSS/JS explorer.
   - Styled pixel-for-pixel to match Swagger UI's iconic design and buttons.
   - Connects directly to in-process execution via `/mcp/ui/call`.

3. **Dynamic MCP OpenAPI 3.1 Specification (`/mcp/openapi.json`)**:
   - Machine-readable OpenAPI 3.1 contract of all your MCP tools.
   - Ready for import into Postman, Insomnia, or client SDK generators.

---

## 💻 Claude Desktop & Cursor Integration

Run your FastAPI application directly over `stdio` without needing an active HTTP server:

Add this to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "my-fastapi-app": {
      "command": "python",
      "args": ["-m", "fastapi_mcp.cli", "run", "main:app", "--transport", "stdio"]
    }
  }
}
```

---

## 🛡️ Enterprise Hardening: Solving Production Bottlenecks

In large enterprise microservices with dozens or hundreds of routes, simply dumping every endpoint as an individual MCP tool creates serious production hurdles. `fastapi-mcp` ships with built-in primitives to solve them:

### 1. Librarian Discovery Pattern (Preventing Context Window Bloat)
Exposing 80+ tools dumps 15,000–25,000 tokens into the LLM system prompt on every single turn, degrading reasoning and exploding API bills. 

Activate **Librarian Mode** to condense all catalog tools into **3 lightweight meta-tools**:
```python
mcp = FastAPIMCP.bind(app, librarian=True)
```
The LLM now only sees:
* `list_api_categories()`: Browse high-level domains (e.g. `billing`, `inventory`, `users`) with tool summaries.
* `search_api_tools(query, category)`: Fetch detailed schemas for matching tools on demand.
* `execute_api_tool(tool_name, arguments)`: Dynamically invoke the requested underlying endpoint.

### 2. Dry-Run Simulation Mode (`enable_dry_run=True`)
Allow AI agents to validate parameters and simulate state mutations (`POST`, `PUT`, `DELETE`, `PATCH`) safely:
```python
mcp = FastAPIMCP.bind(app, enable_dry_run=True)
```
* Injects a `dry_run: bool = False` argument into mutation tools.
* Dispatches in-memory with `X-Dry-Run: true` header and `?dry_run=true` query parameter.
* Wraps responses with `{"dry_run": True, "simulated": True, "result": ...}` so agents can test changes before committing them.

### 3. Dynamic Session Context Provider (Multi-Tenant Stdio & SSE Auth)
Desktop agents connecting via `stdio` (like Claude Desktop or Cursor) do not send standard HTTP `Authorization: Bearer <token>` headers. Without caller context, endpoints with `Depends(get_current_user)` fail with 401 Unauthorized.

Inject authentication claims dynamically per session:
```python
def resolve_tenant_context(tool_args: dict) -> dict:
    # Resolve active tenant / user from session or environment
    return {"Authorization": "Bearer session-token-xyz", "X-Tenant-ID": "acme-corp"}

mcp = FastAPIMCP.bind(
    app,
    session_context_provider=resolve_tenant_context,
)

# Or update dynamically during runtime
mcp.set_session_context_provider(lambda kwargs: {"Authorization": "Bearer rotated-token"})
```

---

## 🛠️ CLI Utilities

### 1. Inspect Tools and Schemas
Inspect which tools and schemas are generated from your FastAPI application:
```bash
fastapi-mcp inspect main:app
```

Output:
```text
=== FastAPI-MCP Server: UnifiedServer ===
Found 2 tools:

* Tool: calculate
  Description: [POST /math/calc] Perform mathematical calculations.
  Arguments (1):
    - data: CalculateRequest (required) - Calculation input data

* Tool: internal_rag_search
  Description: Search internal documentation.
  Arguments (1):
    - query: string (required)
```

Export schema as JSON:
```bash
fastapi-mcp inspect main:app --json
```

### 2. Run Directly from CLI
```bash
fastapi-mcp run main:app --transport stdio
fastapi-mcp run main:app --transport sse
```

---

## ⚙️ Route Filtering & Custom Headers

```python
mcp = FastAPIMCP.bind(
    app,
    # Exclude internal routes
    exclude_paths=["/admin/*", "/metrics"],
    # Only expose routes with specific OpenAPI tags
    include_tags={"mcp", "public"},
    # Filter methods
    include_methods={"GET", "POST"},
    # Static auth headers for protected routes
    default_headers={"Authorization": "Bearer internal-service-token"},
    # Or dynamic headers callback
    headers_factory=lambda: {"X-Request-Source": "mcp-agent"}
)
```

---

## 🧪 Running Tests

The test suite covers route auto-scanning, in-memory ASGI dispatch, dual-mode decorators, single-port co-hosting, and the MCP Swagger UI:

```bash
pytest tests/ -v
```

---

## 📄 License

MIT License. See [LICENSE](LICENSE) for details.
