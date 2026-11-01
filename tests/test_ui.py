"""Tests for FastAPI-MCP interactive documentation and UI endpoints."""

import asyncio
import httpx
from fastapi import FastAPI
from fastapi_mcp import FastAPIMCP
from fastapi_mcp.ui import (
    _build_tool_example,
    _extract_tool_schema_and_meta,
    _inline_defs,
    _serialize_prompt_for_ui,
    _serialize_resource_for_ui,
    _serialize_tool_for_ui,
    generate_mcp_openapi_spec,
    get_mcp_swagger_html,
    get_official_redoc_html,
    get_official_swagger_ui_html,
    inject_nav_bar_into_html,
)


def test_mcp_swagger_ui():
    """Test official Swagger UI, OpenAPI spec, offline UI, and direct tool execution."""
    app = FastAPI(title="UI Test App")

    @app.get("/calc/add", tags=["Math"])
    def add(a: int, b: int = 5):
        """Add two numbers."""
        return {"sum": a + b}

    @app.get("/text/raw")
    def raw_str():
        """Return raw string."""
        return "plain result"

    FastAPIMCP.bind(app, name="UIExplorerDemo")

    async def run_checks():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. Test /mcp/docs returns 200 and Official Swagger UI
            res_docs = await client.get("/mcp/docs")
            assert res_docs.status_code == 200
            assert "text/html" in res_docs.headers["content-type"]
            assert "MCP Swagger Explorer" in res_docs.text
            assert "UIExplorerDemo" in res_docs.text
            assert "add" in res_docs.text

                        # 1b. Test /mcp/redoc returns 200 and Official ReDoc UI with navigation
            res_mcp_redoc = await client.get("/mcp/redoc")
            assert res_mcp_redoc.status_code == 200
            assert "text/html" in res_mcp_redoc.headers["content-type"]
            assert "redoc" in res_mcp_redoc.text.lower()
            assert "fapm-nav-dock" in res_mcp_redoc.text

            # 1c. Test REST /docs and /redoc have unified navigation dock injected
            res_rest_docs = await client.get("/docs")
            assert res_rest_docs.status_code == 200
            assert "fapm-nav-dock" in res_rest_docs.text

            res_rest_redoc = await client.get("/redoc")
            assert res_rest_redoc.status_code == 200
            assert "fapm-nav-dock" in res_rest_redoc.text

            # 2. Test /mcp/openapi.json returns valid OpenAPI 3.1 schema
            res_spec = await client.get("/mcp/openapi.json")
            assert res_spec.status_code == 200
            spec = res_spec.json()
            assert spec["openapi"] == "3.1.0"
            assert "/mcp/tools/add" in spec["paths"]
            assert spec["paths"]["/mcp/tools/add"]["post"]["tags"] == ["Math"]

            # 3. Test /mcp/ui returns 200 and Standalone Offline Explorer
            res_ui = await client.get("/mcp/ui")
            assert res_ui.status_code == 200
            assert "Offline Mode" in res_ui.text
            assert "UIExplorerDemo" in res_ui.text

            # 4. Test live UI tool execution via /mcp/ui/call
            res_call = await client.post(
                "/mcp/ui/call",
                json={"name": "add", "arguments": {"a": 10, "b": 20}},
            )
            assert res_call.status_code == 200
            data = res_call.json()
            assert data["success"] is True
            assert data["result"]["sum"] == 30

            # 5. Test direct execution via /mcp/tools/add (Swagger UI target)
            res_direct = await client.post(
                "/mcp/tools/add",
                json={"a": 15, "b": 25},
            )
            assert res_direct.status_code == 200
            assert res_direct.json()["result"]["sum"] == 40

            # 6. Test direct execution returning plain non-json string
            res_str = await client.post(
                "/mcp/tools/raw_str",
                json={},
            )
            assert res_str.status_code == 200
            assert "plain result" in str(res_str.json()["result"])

            # 7. Test direct execution with invalid / non-json headers
            res_no_json = await client.post(
                "/mcp/tools/add",
                content=b"invalid body",
                headers={"Content-Type": "text/plain"},
            )
            # Will fail because required param 'a' is missing -> 400
            assert res_no_json.status_code == 400
            assert res_no_json.json()["is_error"] is True

            # 7b. Test malformed json body with application/json header
            res_bad_json = await client.post(
                "/mcp/tools/add",
                content=b"{malformed",
                headers={"Content-Type": "application/json"},
            )
            assert res_bad_json.status_code == 400

            # 8. Test execution of non-existent tool -> 400
            res_missing = await client.post(
                "/mcp/tools/unknown_tool",
                json={},
            )
            assert res_missing.status_code == 400
            assert res_missing.json()["is_error"] is True

        print("test_mcp_swagger_ui passed successfully!")

    asyncio.run(run_checks())


def test_ui_generators_edge_branches():
    """Unit tests for edge branches in OpenAPI generator and HTML renderers."""
    # Dict tool with various property types
    class DummySchema:
        """Dummy schema for testing model_dump."""
        def model_dump(self):
            """Return schema dict."""
            return {
                "type": "object",
                "properties": {
                    "is_active": {"type": "boolean"},
                },
            }

    class DummyToolObj:
        """Dummy tool object."""
        def __init__(self):
            self.name = "obj_tool"
            self.description = "Tool with model_dump schema"
            self.input_schema = DummySchema()

    dict_tools = [
        DummyToolObj(),
        {
            "name": "complex_tool",
            "description": "A complex tool for testing.\nDetailed line.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "flag": {"type": "boolean", "default": True},
                    "count": {"type": "integer"},
                    "rate": {"type": "number"},
                    "tags": {"type": "array"},
                    "meta": {"type": "object"},
                    "desc": {"type": "string"},
                },
                "required": ["count"],
            },
        },
        {
            "name": "empty_tool",
            "inputSchema": None,
        },
    ]

    spec = generate_mcp_openapi_spec("EdgeApp", dict_tools, mcp_path="/api/mcp")
    assert "/api/mcp/tools/complex_tool" in spec["paths"]
    assert "/api/mcp/tools/empty_tool" in spec["paths"]
    assert spec["paths"]["/api/mcp/tools/complex_tool"]["post"]["tags"] == ["MCP Tools"]

    # Test get_mcp_swagger_html directly
    html_offline = get_mcp_swagger_html(
        title="CustomTitle",
        tools=dict_tools,
        mcp_path="/custom/mcp",
        sse_path="/custom/sse",
        call_url="/custom/call",
    )
    assert "CustomTitle" in html_offline
    assert "/custom/mcp" in html_offline

    # Test get_official_swagger_ui_html fallback without target div
    dummy_spec = {"openapi": "3.1.0", "paths": {}}
    html_fallback = get_official_swagger_ui_html("Test", "/mcp/openapi.json", dummy_spec)
    assert "FastMCP" in html_fallback

    # Test get_official_redoc_html directly
    html_redoc_direct = get_official_redoc_html("DirectRedoc", "/custom/openapi.json")
    assert "DirectRedoc" in html_redoc_direct
    assert "fapm-nav-dock" in html_redoc_direct

    # Test inject_nav_bar_into_html with no <body> tag
    html_no_body = inject_nav_bar_into_html("<div>raw fragment</div>", "rest_swagger")
    assert "fapm-nav-dock" in html_no_body

    # Test _inline_defs with resolved and unresolved $ref
    resolved_ref = _inline_defs({"$ref": "#/$defs/Sub", "extra": 1}, {"Sub": {"type": "string"}})
    assert resolved_ref["type"] == "string"
    assert resolved_ref["extra"] == 1

    unresolved_ref = _inline_defs({"$ref": "#/$defs/Missing"}, {})
    assert unresolved_ref["$ref"] == "#/$defs/Missing"

    # Test _build_tool_example with nested objects and invalid props
    ex_nested = _build_tool_example({
        "obj": {"type": "object", "properties": {"sub_num": {"type": "number"}}},
        "empty_obj": {"type": "object", "properties": None},
        "invalid_prop": "not_a_dict",
    })
    assert ex_nested["obj"]["sub_num"] == 0
    assert ex_nested["empty_obj"] == {}
    assert "invalid_prop" not in ex_nested

    # Test _extract_tool_schema_and_meta with non-dict/non-dump object
    class NonDumpTool:
        """Dummy tool."""
        name = "nondump"
        description = "desc"
        input_schema = "invalid_non_dict"

    _, _, schema_extracted = _extract_tool_schema_and_meta(NonDumpTool())
    assert schema_extracted == {"type": "object", "properties": {}}

    # Test _serialize_tool_for_ui with $defs in dict and object
    t_dict_defs = {
        "name": "dict_defs",
        "input_schema": {
            "type": "object",
            "$defs": {"Node": {"type": "string"}},
            "properties": {"n": {"$ref": "#/$defs/Node"}},
        },
    }
    dumped_dict = _serialize_tool_for_ui(t_dict_defs)
    assert dumped_dict["input_schema"]["properties"]["n"]["type"] == "string"

    class ObjDefsTool:
        """Dummy tool with defs."""
        name = "obj_defs"
        description = "desc"
        input_schema = {
            "type": "object",
            "$defs": {"Leaf": {"type": "integer"}},
            "properties": {"l": {"$ref": "#/$defs/Leaf"}},
        }

    dumped_obj = _serialize_tool_for_ui(ObjDefsTool())
    assert dumped_obj["input_schema"]["properties"]["l"]["type"] == "integer"

    class ObjNoneTool:
        """Dummy tool with None."""
        name = "obj_none"
        description = "desc"
        input_schema = None

    dumped_none = _serialize_tool_for_ui(ObjNoneTool())
    assert dumped_none["name"] == "obj_none"





def test_mcp_studio_resources_and_prompts():
    """Test MCP Studio Resources, Prompts, and their interactive UI endpoints."""
    # pylint: disable=too-many-statements
    app = FastAPIMCP(title="StudioStudioDemo", mcp_name="StudioDemo")

    @app.tool(name="add_nums")
    def add_nums(a: int, b: int) -> int:
        """Add two integers."""
        return a + b

    @app.resource("system://health")
    def get_health() -> str:
        """System health status."""
        return '{"status": "healthy", "uptime": 1000}'

    @app.prompt("debug_helper")
    def debug_helper(error_log: str, language: str = "python") -> str:
        """Helper to debug code errors."""
        return f"Help me debug this {language} error:\n{error_log}"

    app.mount_mcp()

    async def run_checks():
        # 1. Direct Python SDK Methods
        resources = await app.list_resources()
        assert len(resources) >= 1
        assert any(r.uri == "system://health" for r in resources)

        res_read = await app.read_resource("system://health")
        assert len(res_read) >= 1

        prompts = await app.list_prompts()
        assert len(prompts) >= 1
        assert any(p.name == "debug_helper" for p in prompts)

        p_res = await app.get_prompt(
            "debug_helper", {"error_log": "NullPointer", "language": "java"}
        )
        assert p_res is not None

        # 2. HTTP UI Client Tests
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            # Studio page renders all 3 primitives
            res_ui = await client.get("/mcp/ui")
            assert res_ui.status_code == 200
            assert "add_nums" in res_ui.text
            assert "system://health" in res_ui.text
            assert "debug_helper" in res_ui.text
            assert "Export Spec" in res_ui.text
            assert "Copy Schema" in res_ui.text
            assert "No MCP Tools Registered" in res_ui.text
            assert "No MCP Resources Registered" in res_ui.text
            assert "No MCP Prompts Registered" in res_ui.text

            # Live resource read endpoint
            res_live = await client.get("/mcp/ui/resource?uri=system%3A%2F%2Fhealth")
            assert res_live.status_code == 200
            data_res = res_live.json()
            assert data_res["success"] is True
            assert "healthy" in data_res["contents"][0]["content"]

            # Error reading non-existent resource
            res_err = await client.get("/mcp/ui/resource?uri=nonexistent%3A%2F%2Fpath")
            assert res_err.status_code == 400
            assert res_err.json()["is_error"] is True

            # Live prompt render endpoint
            res_prompt = await client.post(
                "/mcp/ui/prompt",
                json={
                    "name": "debug_helper",
                    "arguments": {"error_log": "SyntaxError", "language": "python"},
                },
            )
            assert res_prompt.status_code == 200
            data_prompt = res_prompt.json()
            assert data_prompt["success"] is True
            assert len(data_prompt["messages"]) >= 1
            assert "SyntaxError" in data_prompt["messages"][0]["text"]

            # Error rendering non-existent prompt
            p_err = await client.post(
                "/mcp/ui/prompt",
                json={"name": "nonexistent_prompt", "arguments": {}},
            )
            assert p_err.status_code == 400
            assert p_err.json()["is_error"] is True

    asyncio.run(run_checks())

    # Serialization helper tests
    class MockRes:
        """Mock Resource for UI serialization."""
        name = "mock_r"
        uri = "mock://res"
        description = "Mock desc"
        mime_type = "application/json"

    s_res = _serialize_resource_for_ui(MockRes())
    assert s_res["name"] == "mock_r"
    assert s_res["uri"] == "mock://res"
    assert s_res["mime_type"] == "application/json"

    class MockArg:
        """Mock Argument for prompt."""
        name = "query"
        description = "search query"
        required = True

    class MockPrompt:
        """Mock Prompt for UI serialization."""
        name = "mock_p"
        description = "Mock prompt desc"
        arguments = [MockArg()]

    s_p = _serialize_prompt_for_ui(MockPrompt())
    assert s_p["name"] == "mock_p"
    assert s_p["arguments"][0]["name"] == "query"
    assert s_p["arguments"][0]["required"] is True


if __name__ == "__main__":
    test_mcp_swagger_ui()
    test_ui_generators_edge_branches()
    test_mcp_studio_resources_and_prompts()
