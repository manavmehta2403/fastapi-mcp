import asyncio
from contextlib import asynccontextmanager
import importlib
import json
import os
import runpy
import sys
from typing import Any, Dict, Optional
import pytest
from fastapi import FastAPI, Depends, Query, Path, Body, Header, HTTPException, Request
from starlette.responses import PlainTextResponse, Response
from pydantic import BaseModel, Field

from fastapi_mcp import FastAPIMCP, RouteScanner, ASGIDispatcher
from fastapi_mcp.scanner import sanitize_tool_name, _extract_param_type
from fastapi_mcp.dispatcher import _serialize_val
from fastapi_mcp.cli import load_app, main as cli_main


# ---------------------------------------------------------------------------
# 1. Tests for __main__.py and CLI edge cases
# ---------------------------------------------------------------------------

def test_main_in_process(monkeypatch):
    """Test running __main__ in-process to achieve 100% coverage on __main__.py."""
    monkeypatch.setattr(sys, "argv", ["fastapi-mcp", "--help"])
    with pytest.raises(SystemExit) as exc_info:
        runpy.run_module("fastapi_mcp.__main__", run_name="__main__")
    assert exc_info.value.code == 0


def test_cli_load_app_variations_and_errors(monkeypatch, capsys):
    """Test CLI app loader edge cases, factories, and error conditions."""
    # 1. Missing colon
    with pytest.raises(ValueError, match="Expected 'module:attribute'"):
        load_app("invalid_format_without_colon")

    # 2. Module not found
    with pytest.raises(RuntimeError, match="Could not import module"):
        load_app("non_existent_module_xyz_123:app")

    # 3. Attribute not found
    with pytest.raises(AttributeError, match="has no attribute"):
        load_app("tests.test_coverage_complete:missing_attr")

    # 4. Factory pattern with ()
    app = load_app("tests.test_coverage_complete:sample_factory_app()")
    assert isinstance(app, FastAPI)

    # 5. Non-FastAPI callable factory
    app2 = load_app("tests.test_coverage_complete:sample_factory_app")
    assert isinstance(app2, FastAPI)

    # 6. Invalid target type (e.g., int)
    monkeypatch.setattr(sys, "argv", ["fastapi-mcp", "inspect", "tests.test_coverage_complete:sample_int_target"])
    with pytest.raises(TypeError, match="must be a FastAPI or FastAPIMCP instance"):
        cli_main()

    # 7. CLI inspect with --json
    monkeypatch.setattr(sys, "argv", ["fastapi-mcp", "inspect", "tests.test_coverage_complete:sample_factory_app()", "--json"])
    cli_main()
    out = capsys.readouterr().out
    data = json.loads(out)
    assert isinstance(data, list)

    # 8. CLI inspect summary
    monkeypatch.setattr(sys, "argv", ["fastapi-mcp", "inspect", "tests.test_coverage_complete:sample_factory_app()"])
    cli_main()
    out_summary = capsys.readouterr().out
    assert "FastAPI-MCP Server" in out_summary
    assert "sample_echo" in out_summary

    # 9. CLI run command with mocked run
    mock_called = {}
    def mock_run(self, transport="stdio", **kwargs):
        mock_called["transport"] = transport

    monkeypatch.setattr(FastAPIMCP, "run", mock_run)
    monkeypatch.setattr(sys, "argv", ["fastapi-mcp", "run", "tests.test_coverage_complete:sample_factory_app()", "--transport", "sse"])
    cli_main()
    assert mock_called.get("transport") == "sse"

    # 10. CLI loading already a FastAPIMCP instance
    monkeypatch.setattr(sys, "argv", ["fastapi-mcp", "inspect", "tests.test_coverage_complete:sample_fastapi_mcp_instance", "--json"])
    cli_main()


def sample_factory_app():
    app = FastAPI(title="FactoryApp")
    @app.get("/echo")
    def sample_echo(msg: str = Query("hello", description="Echo message")):
        return {"echo": msg}
    return app

sample_int_target = 42
sample_fastapi_mcp_instance = FastAPIMCP(mcp_name="PreBuiltMCP")


# ---------------------------------------------------------------------------
# 2. Tests for scanner.py edge cases
# ---------------------------------------------------------------------------

def test_sanitize_tool_name():
    assert sanitize_tool_name("") == "tool"
    assert sanitize_tool_name("???") == "tool"
    assert sanitize_tool_name("valid_name-123") == "valid_name-123"
    assert len(sanitize_tool_name("a" * 100)) == 64


def test_extract_param_type():
    class DummyParamNoAnn:
        pass
    assert _extract_param_type(DummyParamNoAnn()) is Any

    class DummyParamType:
        type_ = int
    assert _extract_param_type(DummyParamType()) is int

    class DummyParamAnn:
        annotation = str
    assert _extract_param_type(DummyParamAnn()) is str


def test_scanner_path_and_tag_filtering():
    app = FastAPI()

    @app.get("/public/data", tags=["public"])
    def public_route(): return {}

    @app.get("/admin/secret", tags=["admin"])
    def admin_route(): return {}

    @app.get("/items/list", tags=["items"])
    def items_route(): return {}

    @app.post("/items/create", tags=["items"])
    def create_route(): return {}

    @app.options("/ignored-options")
    def options_route(): return {}

    # Test wildcard inclusion and tag exclusions
    scanner = RouteScanner(
        app=app,
        include_paths=["/public/*", "/items/list"],
        exclude_tags={"admin"},
        include_methods={"GET"},
    )
    tools = scanner.scan()
    names = [t[0] for t in tools]
    assert "public_route" in names
    assert "items_route" in names
    assert "admin_route" not in names
    assert "create_route" not in names
    assert "options_route" not in names


def test_scanner_tag_inclusions_and_summary_only():
    app = FastAPI()

    @app.get("/allowed", tags=["v1"], summary="Allowed summary only")
    def allowed_route():
        pass  # No docstring, only summary

    @app.get("/disallowed", tags=["v2"])
    def disallowed_route(): return {}

    @app.get("/skipped", tags=["v1"])
    def skipped_route(): return {}

    scanner = RouteScanner(
        app=app,
        include_tags={"v1"},
        exclude_paths=["/skipped"],
    )
    tools = scanner.scan()
    names = [t[0] for t in tools]
    assert "allowed_route" in names
    assert "disallowed_route" not in names
    assert "skipped_route" not in names


def test_scanner_name_collision_and_lambda_fallback():
    app = FastAPI()

    # Route without docstring and same name
    app.add_api_route("/collision", lambda: {"a": 1}, methods=["GET"], name="tool")
    app.add_api_route("/collision2", lambda: {"b": 2}, methods=["GET"], name="tool")

    scanner = RouteScanner(app=app)
    tools = scanner.scan()
    names = [t[0] for t in tools]
    assert "tool" in names
    assert "tool_1" in names


# ---------------------------------------------------------------------------
# 3. Tests for dispatcher.py edge cases
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_dispatcher_serialization_and_multi_body():
    # Test _serialize_val with dict-like object
    class V1Model:
        def dict(self): return {"v1": True}
    assert _serialize_val(V1Model()) == {"v1": True}
    assert _serialize_val("raw_string") == "raw_string"

    app = FastAPI()

    @app.post("/multi-body")
    def multi_body(a: int = Body(...), b: str = Body(...)):
        return {"sum": f"{a}-{b}"}

    @app.post("/optional-body")
    def optional_body(payload: Optional[Dict[str, Any]] = Body(None)):
        return {"got": payload}

    @app.get("/error-404")
    def not_found_route():
        raise HTTPException(status_code=404, detail="Resource not found")

    @app.get("/plain-text", response_class=PlainTextResponse)
    def plain_text():
        return "plain text content"

    @app.get("/bad-json")
    def bad_json():
        return Response(content="not valid json", media_type="application/json")

    mcp = FastAPIMCP.bind(app, auto_scan=True)

    # 1. Multi body dispatch
    res = await mcp.call_tool("multi_body", {"a": 10, "b": "test"})
    assert "10-test" in str(res)

    # 2. Optional body omitted -> line 79 coverage
    res_opt = await mcp.call_tool("optional_body", {})
    assert "got" in str(res_opt)

    # 3. 404 error response parsing
    res_err = await mcp.call_tool("not_found_route")
    assert "404" in str(res_err)
    assert "is_error" in str(res_err)

    # 4. Plain text response parsing
    res_text = await mcp.call_tool("plain_text")
    assert "plain text content" in str(res_text)

    # 5. Bad json with application/json header
    res_bad = await mcp.call_tool("bad_json")
    assert "not valid json" in str(res_bad)


@pytest.mark.asyncio
async def test_dispatcher_dynamic_headers_factory():
    app = FastAPI()

    @app.get("/check-factory-header")
    def check_header(request: Request):
        return {"custom_header": request.headers.get("x-factory-token")}

    mcp = FastAPIMCP.bind(
        app,
        headers_factory=lambda: {"X-Factory-Token": "secret_factory_xyz"},
    )
    res = await mcp.call_tool("check_header")
    assert "secret_factory_xyz" in str(res)


# ---------------------------------------------------------------------------
# 4. Tests for core.py edge cases
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_core_lifespan_and_pure_tools():
    lifespan_visited = []

    @asynccontextmanager
    async def sample_lifespan(app: FastAPI):
        lifespan_visited.append("started")
        yield {"pool": "active"}
        lifespan_visited.append("shutdown")

    mcp_app = FastAPIMCP(mcp_name="LifespanApp", lifespan=sample_lifespan)

    @mcp_app.get("/health")
    def health_check(): return {"status": "ok"}

    # Pure tool
    @mcp_app.tool(name="pure_calculation", description="Pure MCP tool")
    def pure_calculation(x: int, y: int) -> int:
        """Pure MCP calculation."""
        return x * y

    # Resources and Prompts
    @mcp_app.resource("resource://config")
    def get_config(): return "configuration_data"

    @mcp_app.prompt("greeting_prompt")
    def greet(name: str): return f"Hello, {name}!"

    # Trigger lifespan
    async with mcp_app.router.lifespan_context(mcp_app):
        assert "started" in lifespan_visited
        tools = await mcp_app.list_tools()
        names = [t.name for t in tools]
        assert "health_check" in names
        assert "pure_calculation" in names

        # Invoke pure tool
        res = await mcp_app.call_tool("pure_calculation", {"x": 6, "y": 7})
        assert "42" in str(res)

    # Test catalog getter
    catalog = mcp_app.get_tool_catalog()
    assert "pure_calculation" in catalog


@pytest.mark.asyncio
async def test_core_librarian_sync_runner_and_errors():
    app = FastAPI()

    @app.get("/billing/plan", tags=["billing"])
    def get_plan(): return {"plan": "enterprise"}

    @app.post("/billing/charge", tags=["billing"])
    def charge_card(amount: float, dry_run: bool = False):
        if amount < 0:
            raise ValueError("Amount cannot be negative")
        return {"charged": amount}

    mcp = FastAPIMCP.bind(app, librarian=True)

    # 1. Execute unknown tool
    res_err = await mcp.call_tool("execute_api_tool", {"tool_name": "unknown_tool_xyz"})
    assert "not found in catalog" in str(res_err)

    # 2. Execute tool that throws exception
    res_exc = await mcp.call_tool("execute_api_tool", {"tool_name": "charge_card", "arguments": {"amount": -50.0}})
    assert "is_error" in str(res_exc)

    # 3. Search with query matching path
    search_path = await mcp.call_tool("search_api_tools", {"query": "charge"})
    assert "charge" in str(search_path)

    # 4. Search with non-matching query
    search_empty = await mcp.call_tool("search_api_tools", {"query": "non_existent_query_12345"})
    assert '"count": 0' in str(search_empty)

    # 5. Search with non-matching category
    search_cat_empty = await mcp.call_tool("search_api_tools", {"category": "non_existent_category"})
    assert '"count": 0' in str(search_cat_empty)

    # 6. Call catalog tool directly by name in librarian mode with sync runner
    res_direct = await mcp.call_tool("get_plan")
    assert "enterprise" in str(res_direct)

    # 7. Add late api_tool and pure tool when librarian is active
    @mcp.api_tool("/late/tool", methods=["GET"])
    def late_api_tool(): return {"late": True}

    @mcp.tool(name="late_pure_tool")
    def late_pure(): return {"pure": True}

    tools = await mcp.list_tools()
    assert len(tools) == 3


@pytest.mark.asyncio
async def test_core_swagger_ui_endpoints():
    app = FastAPI()

    @app.get("/items/lookup")
    def lookup_item(item_id: int):
        if item_id == 999:
            raise RuntimeError("Database connection timed out")
        if item_id == 777:
            return PlainTextResponse("non-json output string")
        return {"item_id": item_id, "name": f"Item {item_id}"}

    mcp = FastAPIMCP.bind(app, mount_path="/mcp")

    from httpx import ASGITransport, AsyncClient
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # GET /mcp/docs
        resp_docs = await client.get("/mcp/docs")
        assert resp_docs.status_code == 200
        assert "MCP Swagger Explorer" in resp_docs.text

        # POST /mcp/ui/call (success with json)
        call_resp = await client.post("/mcp/ui/call", json={"name": "lookup_item", "arguments": {"item_id": 42}})
        assert call_resp.status_code == 200
        assert call_resp.json()["success"] is True

        # POST /mcp/ui/call (success with non-json text)
        call_text = await client.post("/mcp/ui/call", json={"name": "lookup_item", "arguments": {"item_id": 777}})
        assert call_text.status_code == 200
        assert call_text.json()["success"] is True

        # POST /mcp/ui/call (error caught)
        call_err = await client.post("/mcp/ui/call", json={"name": "lookup_item", "arguments": {"item_id": 999}})
        assert call_err.status_code == 200
        assert call_err.json()["is_error"] is True


def test_scanner_edge_branches():
    """Test scanner branch coverage for lines 138, 142, 161."""
    app = FastAPI()

    @app.delete("/delete-only", tags=["unwanted"])
    def delete_route(): return {}

    route = app.routes[-1]
    scanner = RouteScanner(app=app, include_methods={"GET"}, exclude_tags={"unwanted"})
    assert scanner.should_include_route(route) is False

    # Route with excluded tags
    scanner_tag = RouteScanner(app=app, exclude_tags={"unwanted"})
    assert scanner_tag.should_include_route(route) is False

    # Route with lambda endpoint and no operation_id
    scanner2 = RouteScanner(app=app)
    from fastapi.routing import APIRoute
    lambda_route = APIRoute(
        path="/lambda-path",
        endpoint=lambda: {},
        methods=["GET"],
        operation_id=None,
    )
    name, _, _ = scanner2.convert_route(lambda_route)
    assert "lambda-path" in name


@pytest.mark.asyncio
async def test_core_edge_branches(monkeypatch):
    """Test core.py branch coverage for lines 101, 147, 155, 161, 260, 339, 465, 471."""
    existing_app = FastAPI()
    @existing_app.get("/ping")
    def ping(): return {"ping": "pong"}

    # Line 101: existing_app with auto_scan=True
    mcp_wrapped = FastAPIMCP(existing_app=existing_app, auto_scan=True)
    assert len(mcp_wrapped._tool_catalog) >= 1

    # Line 147 & 155 & 161: _extract_param_schema edge cases
    def no_sig(): pass
    delattr(no_sig, "__annotations__")
    assert mcp_wrapped._extract_param_schema(object()) == {}

    import inspect
    class CustomDefaultObj:
        def __str__(self): return "custom_obj"

    p_no_ann = inspect.Parameter("untyped", inspect.Parameter.KEYWORD_ONLY, default=CustomDefaultObj())
    sig_custom = inspect.Signature(parameters=[p_no_ann])
    def dummy_func(untyped=CustomDefaultObj()): pass
    dummy_func.__signature__ = sig_custom
    res_schema = mcp_wrapped._extract_param_schema(dummy_func)
    assert res_schema["untyped"]["type"] == "Any"
    assert res_schema["untyped"]["default"] == "custom_obj"

    # Line 260: execute_api_tool when async runner raises exception
    librarian_app = FastAPI()
    @librarian_app.get("/async-fail")
    async def async_fail():
        raise RuntimeError("Async execution failed")

    mcp_lib = FastAPIMCP.bind(librarian_app, librarian=True)
    err_res = await mcp_lib.call_tool("execute_api_tool", {"tool_name": "async_fail"})
    assert "is_error" in str(err_res)

    # Line 465: call_tool with arguments=None
    await mcp_lib.call_tool("list_api_categories", arguments=None)

    # Line 339: api_tool when route not in target_app.routes initially
    orphan_mcp = FastAPIMCP()
    decorator = orphan_mcp.api_tool("/orphan", methods=["POST"])
    def orphan_func(): return {}
    # Clear routes to force route_matches to be empty
    orphan_mcp.routes.clear()
    decorator(orphan_func)
    assert "orphan_func" in orphan_mcp._tool_catalog

    # mount_mcp directly and run methods
    orphan_mcp.mount_mcp(path="/mcp-direct", sse_path="/sse-direct")
    mock_run = []
    monkeypatch.setattr(orphan_mcp.mcp_server, "run", lambda transport="stdio", **kw: mock_run.append(transport))
    orphan_mcp.run_stdio()
    assert mock_run == ["stdio"]
    orphan_mcp.run(transport="sse")
    assert mock_run == ["stdio", "sse"]

    mock_async = []
    async def dummy_async_stdio(): mock_async.append("async_stdio")
    monkeypatch.setattr(orphan_mcp.mcp_server, "run_stdio_async", dummy_async_stdio)
    await orphan_mcp.run_stdio_async()
    assert mock_async == ["async_stdio"]


def test_lifespan_and_mounting_fallbacks(monkeypatch):
    """Test unified lifespan execution with session manager and mounting fallbacks."""
    from starlette.testclient import TestClient

    # Lifespan with session manager mounted
    app = FastAPIMCP()
    app.mount_mcp(path="/mcp-test", sse_path="/sse-test")
    with TestClient(app) as client:
        resp = client.get("/mcp-test/docs")
        assert resp.status_code == 200

    # User custom lifespan combined with session manager
    @asynccontextmanager
    async def custom_lifespan(app_inst):
        yield {"custom": True}

    app_custom = FastAPIMCP(lifespan=custom_lifespan)
    app_custom.mount_mcp(path="/mcp-custom")
    with TestClient(app_custom):
        pass

    # TypeError fallbacks in mount_to and mount_mcp
    class FakeMCPServer:
        def sse_app(self, *args, **kwargs):
            if "sse_path" in kwargs:
                raise TypeError("No sse_path")
            return FastAPI()

        def streamable_http_app(self, *args, **kwargs):
            if "streamable_http_path" in kwargs:
                raise TypeError("No streamable_http_path")
            return FastAPI()

    app_fallback = FastAPIMCP()
    monkeypatch.setattr(app_fallback, "mcp_server", FakeMCPServer())
    app_fallback.mount_mcp(path="/mcp-fb", sse_path="/sse-fb", enable_ui=False)

    target = FastAPI()
    app_fallback.mount_to(target, path="/mcp-tgt", sse_path="/sse-tgt", enable_ui=False)


@pytest.mark.asyncio
async def test_version_and_http_query_decorator():
    """Test __version__ and @app.query decorator for RFC 10008 HTTP QUERY method."""
    import re
    from pathlib import Path
    import fastapi_mcp

    # Enforce strict cross-file version synchronization
    root_dir = Path(__file__).resolve().parent.parent
    with open(root_dir / "pyproject.toml", "r", encoding="utf-8") as f:
        pyproj_match = re.search(r'version\s*=\s*"([^"]+)"', f.read())
        pyproj_ver = pyproj_match.group(1) if pyproj_match else None

    with open(root_dir / "fastapi_mcp" / "ui.py", "r", encoding="utf-8") as f:
        ui_match = re.search(r'class="fapm-badge-ver">v?([0-9\.]+)<', f.read())
        ui_ver = ui_match.group(1) if ui_match else None

    assert pyproj_ver == fastapi_mcp.__version__ == ui_ver == "0.5.0"

    app = FastAPIMCP(auto_scan=True)

    class QueryModel(BaseModel):
        filter_text: str

    @app.query("/search-rfc")
    def rfc_search(q: QueryModel):
        return {"found": q.filter_text}

    tools = await app.list_tools()
    assert "rfc_search" in [t.name for t in tools]

    res = await app.call_tool("rfc_search", {"q": {"filter_text": "testing rfc 10008"}})
    assert "testing rfc 10008" in str(res)


