"""Interactive developer studio and unified documentation navigation for FastAPI-MCP.

Provides:
- `/mcp/ui`: FastAPI-MCP Studio supporting Tools, Resources, Prompts, and Client Configs
- Unified navigation dock connecting REST (/docs, /redoc) and MCP Studio (/mcp/ui)
"""

import copy
from dataclasses import dataclass
import json
from typing import Any, Dict, List, Optional, Tuple
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi_mcp.templates import NAV_CSS, STUDIO_HTML_TEMPLATE


@dataclass
class NavPaths:
    """Configured navigation paths for documentation and studio views."""

    mcp_path: str = "/mcp"
    sse_path: str = "/sse"
    docs_path: str = "/mcp/docs"
    redoc_path: str = "/mcp/redoc"
    ui_path: str = "/mcp/ui"
    rest_docs_url: str = "/docs"
    rest_redoc_url: str = "/redoc"


def _resolve_paths(paths: Optional[NavPaths] = None, **kwargs: Any) -> NavPaths:
    """Resolves NavPaths from dataclass or fallback kwargs."""
    if paths is not None:
        return paths
    return NavPaths(
        mcp_path=kwargs.get("mcp_path", "/mcp"),
        sse_path=kwargs.get("sse_path", "/sse"),
        docs_path=kwargs.get("docs_path", "/mcp/docs"),
        redoc_path=kwargs.get("redoc_path", "/mcp/redoc"),
        ui_path=kwargs.get("ui_path", "/mcp/ui"),
        rest_docs_url=kwargs.get("rest_docs_url", "/docs"),
        rest_redoc_url=kwargs.get("rest_redoc_url", "/redoc"),
    )


def render_nav_bar(
    current_page: str,
    title: str = "FastAPI-MCP Gateway",
    paths: Optional[NavPaths] = None,
    active_openapi_url: Optional[str] = None,
    **kwargs: Any,
) -> str:
    """Generates the unified navigation dock and Quick-Connect client modal HTML."""
    del active_openapi_url
    p = _resolve_paths(paths, **kwargs)

    rest_sw_active = "active-rest" if current_page == "rest_swagger" else ""
    rest_rd_active = "active-rest" if current_page == "rest_redoc" else ""
    is_mcp = current_page in ("mcp_ui", "mcp_swagger", "mcp_redoc")
    mcp_ui_active = "active-studio" if is_mcp else ""

    nav_html = f"""
    <div class="fapm-nav-dock">
      <a href="{p.ui_path}" class="fapm-nav-brand">
        <span class="fapm-brand-logo">⚡ FastMCP</span>
        <span class="fapm-brand-title">{title}</span>
        <span class="fapm-badge-ver">v0.6.0</span>
      </a>

      <div class="fapm-nav-tabs">
        <div class="fapm-tab-group">
          <span class="fapm-group-label">REST API</span>
          <a href="{p.rest_docs_url}" class="fapm-tab-link {rest_sw_active}">Swagger</a>
          <a href="{p.rest_redoc_url}" class="fapm-tab-link {rest_rd_active}">ReDoc</a>
        </div>

        <div class="fapm-tab-group">
          <span class="fapm-group-label">MCP</span>
          <a href="{p.ui_path}" class="fapm-tab-link {mcp_ui_active}">🤖 MCP Studio</a>
        </div>
      </div>

      <div class="fapm-nav-actions">
        <button type="button" class="fapm-btn-connect" onclick="window.fapmToggleModal()">
          🔌 Connect Client
        </button>
      </div>
    </div>

    <div id="fapm-modal-backdrop" class="fapm-modal-backdrop"
         onclick="if(event.target===this)window.fapmToggleModal()">
      <div class="fapm-modal-card">
        <div class="fapm-modal-header">
          <div class="fapm-modal-title">🔌 Connect MCP Client</div>
          <button type="button" class="fapm-modal-close"
                  onclick="window.fapmToggleModal()">✕</button>
        </div>
        <div class="fapm-modal-tabs">
          <button class="fapm-modal-tab-btn active" id="fapm-tbtn-claude"
                  onclick="window.fapmSelectTab('claude')">Claude Desktop</button>
          <button class="fapm-modal-tab-btn" id="fapm-tbtn-cursor"
                  onclick="window.fapmSelectTab('cursor')">Cursor IDE</button>
          <button class="fapm-modal-tab-btn" id="fapm-tbtn-windsurf"
                  onclick="window.fapmSelectTab('windsurf')">Windsurf</button>
          <button class="fapm-modal-tab-btn" id="fapm-tbtn-sse"
                  onclick="window.fapmSelectTab('sse')">SSE Transport</button>
        </div>
        <div class="fapm-modal-body">
          <div id="fapm-pane-claude" class="fapm-modal-pane active">
            <div class="fapm-pane-hint">
              Add this to your <code>claude_desktop_config.json</code>:
            </div>
            <div class="fapm-code-box">
              <pre id="fapm-code-claude"></pre>
              <button class="fapm-btn-copy"
                      onclick="window.fapmCopy('fapm-code-claude', this)">📋 Copy</button>
            </div>
          </div>
          <div id="fapm-pane-cursor" class="fapm-modal-pane">
            <div class="fapm-pane-hint">
              Add this to your <code>.cursor/mcp.json</code>:
            </div>
            <div class="fapm-code-box">
              <pre id="fapm-code-cursor"></pre>
              <button class="fapm-btn-copy"
                      onclick="window.fapmCopy('fapm-code-cursor', this)">📋 Copy</button>
            </div>
          </div>
          <div id="fapm-pane-windsurf" class="fapm-modal-pane">
            <div class="fapm-pane-hint">
              Add this to your Windsurf <code>mcp_config.json</code>:
            </div>
            <div class="fapm-code-box">
              <pre id="fapm-code-windsurf"></pre>
              <button class="fapm-btn-copy"
                      onclick="window.fapmCopy('fapm-code-windsurf', this)">📋 Copy</button>
            </div>
          </div>
          <div id="fapm-pane-sse" class="fapm-modal-pane">
            <div class="fapm-pane-hint">
              Legacy SSE transport configuration:
            </div>
            <div class="fapm-code-box">
              <pre id="fapm-code-sse"></pre>
              <button class="fapm-btn-copy"
                      onclick="window.fapmCopy('fapm-code-sse', this)">📋 Copy</button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <script>
      window.fapmToggleModal = function() {{
        var el = document.getElementById("fapm-modal-backdrop");
        if (!el) return;
        var isHidden = el.style.display === "none" || !el.style.display;
        el.style.display = isHidden ? "flex" : "none";
      }};

      window.fapmSelectTab = function(name) {{
        document.querySelectorAll('.fapm-modal-pane').forEach(function(p) {{
          p.classList.remove('active');
        }});
        document.querySelectorAll('.fapm-modal-tab-btn').forEach(function(b) {{
          b.classList.remove('active');
        }});
        var targetPane = document.getElementById('fapm-pane-' + name);
        var targetBtn = document.getElementById('fapm-tbtn-' + name);
        if (targetPane) targetPane.classList.add('active');
        if (targetBtn) targetBtn.classList.add('active');
      }};

      window.fapmCopy = function(id, btn) {{
        var text = document.getElementById(id).innerText;
        navigator.clipboard.writeText(text).then(function() {{
          var orig = btn.innerText;
          btn.innerText = "✓ Copied!";
          setTimeout(function() {{ btn.innerText = orig; }}, 2000);
        }}).catch(function() {{
          btn.innerText = "Copy manually";
        }});
      }};

      document.addEventListener("DOMContentLoaded", function() {{
        var origin = window.location.origin || "http://127.0.0.1:8000";
        var mcpUrl = origin + "{p.mcp_path}";
        var sseUrl = origin + "{p.sse_path}";

        var claudeCfg = JSON.stringify({{
          mcpServers: {{
            "fastapi-mcp": {{ "url": mcpUrl }}
          }}
        }}, null, 2);

        var cursorCfg = JSON.stringify({{
          mcpServers: {{
            "fastapi-mcp": {{ "url": mcpUrl }}
          }}
        }}, null, 2);

        var windsurfCfg = JSON.stringify({{
          mcpServers: {{
            "fastapi-mcp": {{ "serverUrl": mcpUrl }}
          }}
        }}, null, 2);

        var sseCfg = JSON.stringify({{
          mcpServers: {{
            "fastapi-mcp-sse": {{ "url": sseUrl }}
          }}
        }}, null, 2);

        var elC = document.getElementById("fapm-code-claude");
        if (elC) elC.innerText = claudeCfg;
        var elCu = document.getElementById("fapm-code-cursor");
        if (elCu) elCu.innerText = cursorCfg;
        var elW = document.getElementById("fapm-code-windsurf");
        if (elW) elW.innerText = windsurfCfg;
        var elS = document.getElementById("fapm-code-sse");
        if (elS) elS.innerText = sseCfg;
      }});
    </script>
    """
    return nav_html


def inject_nav_bar_into_html(
    html: str,
    current_page: str,
    title: str = "FastAPI-MCP Gateway",
    paths: Optional[NavPaths] = None,
    active_openapi_url: Optional[str] = None,
    **kwargs: Any,
) -> str:
    """Injects the unified navigation dock into an existing HTML document."""
    p = _resolve_paths(paths, **kwargs)
    nav_html = render_nav_bar(
        current_page=current_page,
        title=title,
        paths=p,
        active_openapi_url=active_openapi_url,
    )

    offset_style = "<style>body { padding-top: 42px !important; margin: 0; }</style>"
    payload = f"{NAV_CSS}\n{offset_style}\n{nav_html}"

    if "<body" in html:
        idx = html.find(">", html.find("<body"))
        if idx != -1:
            return html[: idx + 1] + payload + html[idx + 1 :]
    return payload + html


def _extract_tool_schema_and_meta(tool: Any) -> Tuple[str, str, Dict[str, Any]]:
    """Extract name, doc, and schema dict from a tool dict or Tool object."""
    if isinstance(tool, dict):
        name = tool.get("name", "tool")
        doc = tool.get("description", "") or f"MCP tool: {name}"
        raw_schema = tool.get("input_schema") or tool.get("inputSchema") or {}
    else:
        name = getattr(tool, "name", "tool")
        doc = getattr(tool, "description", "") or f"MCP tool: {name}"
        raw_schema = (
            getattr(tool, "input_schema", None)
            or getattr(tool, "inputSchema", None)
            or {}
        )

    if hasattr(raw_schema, "model_dump"):
        schema_dict = raw_schema.model_dump()
    elif isinstance(raw_schema, dict):
        schema_dict = raw_schema
    else:
        schema_dict = {"type": "object", "properties": {}}

    return name, doc, schema_dict


def _inline_defs(schema: Any, defs: Dict[str, Any]) -> Any:
    """Recursively resolves and inlines $ref pointers from $defs."""
    if isinstance(schema, dict):
        if "$ref" in schema and isinstance(schema["$ref"], str):
            ref = schema["$ref"]
            def_name = ref.split("/")[-1]
            if def_name in defs:
                resolved = _inline_defs(copy.deepcopy(defs[def_name]), defs)
                for k, v in schema.items():
                    if k != "$ref" and k not in resolved:
                        resolved[k] = v
                return resolved
        return {k: _inline_defs(v, defs) for k, v in schema.items() if k != "$defs"}
    if isinstance(schema, list):
        return [_inline_defs(item, defs) for item in schema]
    return schema


def _build_tool_example(props: Dict[str, Any]) -> Dict[str, Any]:
    """Builds example arguments dictionary from property schema definitions."""
    example_body: Dict[str, Any] = {}
    for prop_name, prop_val in props.items():
        if not isinstance(prop_val, dict):
            continue
        p_type = prop_val.get("type", "string")
        if "default" in prop_val:
            example_body[prop_name] = prop_val["default"]
        elif p_type in ("integer", "number"):
            example_body[prop_name] = 0
        elif p_type == "boolean":
            example_body[prop_name] = False
        elif p_type == "array":
            example_body[prop_name] = []
        elif p_type == "object":
            nested_props = prop_val.get("properties")
            if nested_props and isinstance(nested_props, dict):
                example_body[prop_name] = _build_tool_example(nested_props)
            else:
                example_body[prop_name] = {}
        else:
            example_body[prop_name] = "string"
    return example_body


def generate_mcp_openapi_spec(
    title: str,
    tools: List[Any],
    mcp_path: str = "/mcp",
    version: str = "1.0.0",
    catalog: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Generates an OpenAPI 3.1 specification for registered MCP tools."""
    catalog = catalog or {}
    paths: Dict[str, Any] = {}
    global_defs: Dict[str, Any] = {}

    for tool in tools:
        name, doc, raw_schema = _extract_tool_schema_and_meta(tool)
        tool_defs = raw_schema.get("$defs", {})
        if isinstance(tool_defs, dict):
            global_defs.update(tool_defs)

        schema_dict = _inline_defs(raw_schema, {**global_defs, **tool_defs})
        tool_endpoint = f"{mcp_path.rstrip('/')}/tools/{name}"

        tags = ["MCP Tools"]
        if name in catalog:
            _, _, runner = catalog[name]
            runner_tags = getattr(runner, "_mcp_tags", None)
            if runner_tags:
                tags = list(runner_tags)
            elif getattr(runner, "_is_dual_tool", False):
                tags = ["REST + MCP Tools"]
            else:
                tags = ["MCP Dedicated Tools"]

        props = schema_dict.get("properties", {})
        example_body = _build_tool_example(props)

        post_op: Dict[str, Any] = {
            "tags": tags,
            "summary": doc.split("\n")[0] if doc else name,
            "description": doc,
            "operationId": f"mcp_tool_{name}",
            "responses": {
                "200": {
                    "description": "Successful tool execution",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "success": {"type": "boolean"},
                                    "result": {"description": "Tool return value"},
                                },
                                "required": ["success"],
                            }
                        }
                    },
                },
                "400": {
                    "description": "Tool execution error",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "is_error": {"type": "boolean"},
                                    "error": {"type": "string"},
                                },
                                "required": ["is_error", "error"],
                            }
                        }
                    },
                },
            },
        }

        if props or schema_dict.get("type") == "object":
            req_fields = schema_dict.get("required", [])
            post_op["requestBody"] = {
                "description": f"Parameters for {name}",
                "required": bool(req_fields),
                "content": {
                    "application/json": {
                        "schema": schema_dict,
                        "example": example_body,
                    }
                },
            }

        paths[tool_endpoint] = {"post": post_op}

    return {
        "openapi": "3.1.0",
        "info": {
            "title": f"{title} - MCP Swagger Explorer",
            "version": version,
            "description": (
                "OpenAPI 3.1 schema for registered Model Context Protocol (MCP) Tools."
            ),
        },
        "paths": paths,
        "components": {"schemas": global_defs},
        "$defs": global_defs,
    }


def get_official_swagger_ui_html(
    title: str,
    openapi_url: str,
    spec: Dict[str, Any],
    paths: Optional[NavPaths] = None,
    catalog: Optional[Dict[str, Any]] = None,
    **kwargs: Any,
) -> str:
    """Renders Swagger UI for backward-compatibility with tests and legacy callers."""
    del catalog
    swagger_ui_params = {
        "spec": spec,
        "deepLinking": True,
        "displayRequestDuration": True,
        "tryItOutEnabled": True,
    }
    resp = get_swagger_ui_html(
        openapi_url=openapi_url,
        title=title,
        swagger_ui_parameters=swagger_ui_params,
    )
    raw_html = resp.body.decode()
    p = _resolve_paths(paths, **kwargs)

    return inject_nav_bar_into_html(
        html=raw_html,
        current_page="mcp_swagger",
        title=title.replace(" - MCP Swagger Explorer", ""),
        paths=p,
        active_openapi_url=openapi_url,
    )


def get_official_redoc_html(
    title: str,
    openapi_url: str,
    paths: Optional[NavPaths] = None,
    catalog: Optional[Dict[str, Any]] = None,
    **kwargs: Any,
) -> str:
    """Renders ReDoc UI for backward-compatibility with tests and legacy callers."""
    del catalog
    resp = get_redoc_html(
        openapi_url=openapi_url,
        title=title,
    )
    raw_html = resp.body.decode()
    p = _resolve_paths(paths, **kwargs)

    return inject_nav_bar_into_html(
        html=raw_html,
        current_page="mcp_redoc",
        title=title.replace(" - MCP ReDoc", ""),
        paths=p,
        active_openapi_url=openapi_url,
    )


def _serialize_tool_for_ui(
    tool: Any,
    catalog: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Helper to convert any Tool object or dict into a JSON-serializable dictionary."""
    catalog = catalog or {}
    tool_name = (
        getattr(tool, "name", "tool")
        if not isinstance(tool, dict)
        else tool.get("name", "tool")
    )
    is_dual = False
    if tool_name in catalog:
        _, _, runner = catalog[tool_name]
        is_dual = bool(getattr(runner, "_is_dual_tool", False))

    if hasattr(tool, "model_dump"):
        dumped = tool.model_dump()
        raw_in = dumped.get("input_schema")
        if isinstance(raw_in, dict):
            defs = raw_in.get("$defs", {})
            if isinstance(defs, dict) and defs:
                dumped["input_schema"] = _inline_defs(raw_in, defs)
        dumped["tool_type"] = "REST + MCP" if is_dual else "MCP ONLY"
        return dumped
    if isinstance(tool, dict):
        tool_copy = copy.deepcopy(tool)
        raw_in = tool_copy.get("input_schema") or tool_copy.get("inputSchema")
        if isinstance(raw_in, dict):
            defs = raw_in.get("$defs", {})
            if isinstance(defs, dict) and defs:
                tool_copy["input_schema"] = _inline_defs(raw_in, defs)
        tool_copy["tool_type"] = "REST + MCP" if is_dual else "MCP ONLY"
        return tool_copy
    raw_schema = (
        getattr(tool, "input_schema", None)
        or getattr(tool, "inputSchema", None)
    )
    if hasattr(raw_schema, "model_dump"):
        schema_dict = raw_schema.model_dump()
    elif isinstance(raw_schema, dict):
        schema_dict = raw_schema
    else:
        schema_dict = {"type": "object", "properties": {}}
    defs = schema_dict.get("$defs", {})
    if isinstance(defs, dict) and defs:
        schema_dict = _inline_defs(schema_dict, defs)
    return {
        "name": getattr(tool, "name", "tool"),
        "description": getattr(tool, "description", ""),
        "input_schema": schema_dict,
        "tool_type": "REST + MCP" if is_dual else "MCP ONLY",
    }


def _serialize_resource_for_ui(res: Any) -> Dict[str, Any]:
    """Serializes an MCP Resource object into a JSON dictionary."""
    return {
        "name": getattr(res, "name", "") or str(getattr(res, "uri", "")),
        "uri": str(getattr(res, "uri", "")),
        "description": getattr(res, "description", "") or "",
        "mime_type": getattr(res, "mime_type", "text/plain") or "text/plain",
    }


def _serialize_prompt_for_ui(p: Any) -> Dict[str, Any]:
    """Serializes an MCP Prompt object into a JSON dictionary."""
    args = []
    for a in getattr(p, "arguments", []) or []:
        args.append({
            "name": getattr(a, "name", ""),
            "description": getattr(a, "description", "") or "",
            "required": bool(getattr(a, "required", False)),
        })
    return {
        "name": getattr(p, "name", ""),
        "description": getattr(p, "description", "") or "",
        "arguments": args,
    }


def get_mcp_swagger_html(
    title: str,
    tools: list,
    resources: Optional[list] = None,
    prompts: Optional[list] = None,
    call_url: str = "/mcp/ui/call",
    resource_url: str = "/mcp/ui/resource",
    prompt_url: str = "/mcp/ui/prompt",
    openapi_url: Optional[str] = None,
    paths: Optional[NavPaths] = None,
    catalog: Optional[Dict[str, Any]] = None,
    **kwargs: Any,
) -> str:
    """Renders the standalone FastAPI-MCP Studio supporting Tools, Resources, and Prompts."""
    p = _resolve_paths(paths, **kwargs)
    spec_url = openapi_url or f"{p.mcp_path.rstrip('/')}/openapi.json"
    tools_json = json.dumps([_serialize_tool_for_ui(t, catalog=catalog) for t in tools])
    resources_json = json.dumps([_serialize_resource_for_ui(r) for r in (resources or [])])
    prompts_json = json.dumps([_serialize_prompt_for_ui(pr) for pr in (prompts or [])])

    nav_html = render_nav_bar(
        current_page="mcp_ui",
        title=title,
        paths=p,
    )
    return (
        STUDIO_HTML_TEMPLATE.replace("{title}", title)
        .replace("{nav_css}", NAV_CSS)
        .replace("{nav_html}", nav_html)
        .replace("{tools_json}", tools_json)
        .replace("{resources_json}", resources_json)
        .replace("{prompts_json}", prompts_json)
        .replace("{call_url}", call_url)
        .replace("{resource_url}", resource_url)
        .replace("{prompt_url}", prompt_url)
        .replace("{openapi_url}", spec_url)
    )
