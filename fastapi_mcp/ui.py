"""Interactive Swagger-style UI for FastMCP / Model Context Protocol.

Provides an interactive playground at `/mcp/docs` (Official Swagger UI)
and `/mcp/ui` (100% Offline Standalone Explorer) where developers can inspect
registered tools, view schemas, fill in parameters, and execute tools live in the browser.
"""

import copy
import json
from typing import Any, Dict, List, Optional, Tuple
from fastapi.openapi.docs import get_swagger_ui_html

OFFLINE_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} - MCP Swagger Explorer</title>
  <style>
    :root {{
      --bg: #0d1117;
      --card-bg: #161b22;
      --border: #30363d;
      --text: #c9d1d9;
      --text-muted: #8b949e;
      --primary: #4990e2;
      --primary-hover: #357ebd;
      --success: #49cc90;
      --badge-tool: #4990e2;
      --code-bg: #090d13;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background-color: var(--bg);
      color: var(--text);
      line-height: 1.5;
    }}
    .top-nav {{
      background: #1b1b1b;
      padding: 12px 24px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-bottom: 2px solid #49cc90;
    }}
    .top-nav-brand {{
      display: flex;
      align-items: center;
      gap: 12px;
    }}
    .top-nav-title {{
      color: #ffffff;
      font-size: 14px;
      font-weight: 600;
    }}
    .top-nav-links {{
      display: flex;
      gap: 16px;
      font-size: 13px;
    }}
    .top-nav-links a {{
      text-decoration: none;
      transition: color 0.15s;
    }}
    .container {{
      max-width: 1050px;
      margin: 24px auto;
      padding: 0 16px;
    }}
    header {{
      margin-bottom: 24px;
      padding-bottom: 16px;
      border-bottom: 1px solid var(--border);
    }}
    h1 {{
      font-size: 24px;
      color: #fff;
      font-weight: 700;
      display: flex;
      align-items: center;
      gap: 10px;
    }}
    .badge {{
      font-size: 11px;
      font-weight: 700;
      padding: 3px 8px;
      border-radius: 12px;
      text-transform: uppercase;
      background: var(--badge-tool);
      color: #fff;
    }}
    .endpoint-info {{
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      margin-top: 10px;
      font-size: 13px;
      color: var(--text-muted);
    }}
    .endpoint-pill {{
      background: #21262d;
      padding: 4px 10px;
      border-radius: 6px;
      border: 1px solid var(--border);
      font-family: monospace;
    }}
    .card {{
      background: var(--card-bg);
      border: 1px solid var(--primary);
      border-radius: 6px;
      margin-bottom: 14px;
      overflow: hidden;
      transition: border-color 0.15s ease;
    }}
    .card-header {{
      padding: 12px 16px;
      background: rgba(73, 144, 226, 0.08);
      display: flex;
      justify-content: space-between;
      align-items: center;
      cursor: pointer;
      user-select: none;
    }}
    .card-title-group {{
      display: flex;
      align-items: center;
      gap: 12px;
    }}
    .tool-method {{
      background: var(--primary);
      color: #fff;
      font-size: 12px;
      font-weight: 700;
      padding: 4px 10px;
      border-radius: 4px;
      font-family: monospace;
    }}
    .tool-name {{
      font-weight: 600;
      font-size: 15px;
      color: #fff;
      font-family: monospace;
    }}
    .tool-desc {{
      color: var(--text-muted);
      font-size: 13px;
      margin-top: 3px;
    }}
    .chevron {{
      transition: transform 0.2s ease;
      color: var(--primary);
      font-size: 12px;
    }}
    .expanded .chevron {{
      transform: rotate(180deg);
    }}
    .card-body {{
      display: none;
      padding: 16px;
      border-top: 1px solid var(--border);
      background: #0d1117;
    }}
    .expanded .card-body {{
      display: block;
    }}
    .params-table {{
      width: 100%;
      border-collapse: collapse;
      margin-bottom: 16px;
      font-size: 13px;
    }}
    .params-table th, .params-table td {{
      padding: 8px 12px;
      text-align: left;
      border-bottom: 1px solid #21262d;
    }}
    .params-table th {{
      color: var(--text-muted);
      font-weight: 600;
    }}
    .param-name {{
      font-family: monospace;
      color: #58a6ff;
      font-weight: 600;
    }}
    .param-type {{
      font-family: monospace;
      color: #ff7b72;
      font-size: 12px;
    }}
    .param-req {{
      color: #f85149;
      font-size: 11px;
      font-weight: 600;
      margin-left: 4px;
    }}
    .form-group {{
      margin-bottom: 12px;
    }}
    .form-label {{
      display: block;
      font-size: 13px;
      font-weight: 500;
      margin-bottom: 6px;
      color: #fff;
    }}
    input[type="text"], input[type="number"], textarea, select {{
      width: 100%;
      padding: 8px 12px;
      background: #161b22;
      border: 1px solid var(--border);
      border-radius: 6px;
      color: #fff;
      font-family: monospace;
      font-size: 13px;
    }}
    input:focus, textarea:focus {{
      outline: none;
      border-color: var(--primary);
      box-shadow: 0 0 0 2px rgba(73, 144, 226, 0.25);
    }}
    textarea {{
      min-height: 80px;
      resize: vertical;
    }}
    .btn {{
      padding: 8px 24px;
      border-radius: 4px;
      font-weight: 700;
      font-size: 13px;
      cursor: pointer;
      border: none;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      transition: background 0.15s ease;
    }}
    .btn-primary {{
      background: var(--primary);
      color: #fff;
    }}
    .btn-primary:hover {{
      background: var(--primary-hover);
    }}
    .output-box {{
      margin-top: 16px;
      background: var(--code-bg);
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 12px;
      font-family: monospace;
      font-size: 12px;
      color: #7ee787;
      white-space: pre-wrap;
      word-break: break-all;
      display: none;
    }}
    .output-header {{
      display: flex;
      justify-content: space-between;
      font-size: 11px;
      font-weight: 700;
      color: var(--text-muted);
      margin-bottom: 6px;
      text-transform: uppercase;
    }}
    .status-badge {{
      background: #238636;
      color: #fff;
      padding: 2px 6px;
      border-radius: 4px;
      font-size: 11px;
    }}
    .output-error {{
      color: #f85149;
      border-color: #f85149;
    }}
    .output-error .status-badge {{
      background: #da3633;
    }}
    .empty-state {{
      text-align: center;
      padding: 48px;
      color: var(--text-muted);
    }}
    .badge-dual {{
      background: #238636 !important;
    }}
    .badge-mcp {{
      background: #1f6feb !important;
    }}
    .quick-connect {{
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 8px;
      margin-bottom: 24px;
      overflow: hidden;
    }}
    .qc-toggle {{
      padding: 12px 16px;
      background: rgba(88, 166, 255, 0.08);
      display: flex;
      justify-content: space-between;
      align-items: center;
      cursor: pointer;
      font-size: 13px;
      font-weight: 600;
      color: #58a6ff;
      user-select: none;
    }}
    .qc-toggle:hover {{
      background: rgba(88, 166, 255, 0.14);
    }}
    .qc-body {{
      display: none;
      padding: 16px;
      border-top: 1px solid var(--border);
      background: #0d1117;
    }}
    .qc-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 16px;
    }}
    @media (max-width: 768px) {{
      .qc-grid {{ grid-template-columns: 1fr; }}
    }}
    .qc-box {{
      background: var(--code-bg);
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 12px;
      position: relative;
    }}
    .qc-box-title {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 12px;
      font-weight: 700;
      margin-bottom: 8px;
    }}
    .qc-pre {{
      margin: 0;
      font-family: monospace;
      font-size: 11px;
      color: #e6edf3;
      white-space: pre;
      overflow-x: auto;
    }}
    .copy-btn {{
      background: #21262d;
      border: 1px solid var(--border);
      color: #c9d1d9;
      padding: 3px 8px;
      border-radius: 4px;
      font-size: 11px;
      cursor: pointer;
    }}
    .copy-btn:hover {{
      background: #30363d;
      color: #fff;
    }}
  </style>
</head>
<body>
  <div class="top-nav">
    <div class="top-nav-brand">
      <span style="color: #49cc90; font-weight: 700; font-size: 17px;">⚡ FastMCP</span>
      <span class="top-nav-title">{title}</span>
      <span style="background: #238636; color: #fff; font-size: 11px; padding: 2px 8px; border-radius: 10px; font-weight: 700;">Offline Mode</span>
    </div>
    <div class="top-nav-links">
      <a href="{docs_path}" style="color: #49cc90; font-weight: 600;">🟢 Official Swagger UI</a>
      <a href="{ui_path}" style="color: #61affe; font-weight: 700; border-bottom: 2px solid #61affe;">⚡ Offline Explorer</a>
      <a href="{openapi_path}" target="_blank" style="color: #ff9800;">📄 openapi.json ↗</a>
      <a href="/docs" target="_blank" style="color: #c9d1d9;">🌐 REST API /docs ↗</a>
    </div>
  </div>

  <div class="container">
    <header>
      <div>
        <h1>
          <span>{title}</span>
          <span class="badge">FastMCP Explorer</span>
        </h1>
        <p style="color: var(--text-muted); margin-top: 6px;">
          Standalone, zero-CDN Model Context Protocol (MCP) interactive playground.
        </p>
        <div class="endpoint-info">
          <span>Official Swagger: <a href="{docs_path}" style="color: #49cc90; text-decoration: none;">{docs_path}</a></span>
          <span>OpenAPI Spec: <a href="{openapi_path}" style="color: #ff9800; text-decoration: none;">{openapi_path}</a></span>
          <span>MCP SSE: <span class="endpoint-pill">{sse_path}</span></span>
          <span>MCP Streamable: <span class="endpoint-pill">{mcp_path}</span></span>
        </div>
      </div>
    </header>

    <div class="quick-connect">
      <div class="qc-toggle" onclick="toggleQuickConnect()">
        <div style="display: flex; align-items: center; gap: 8px;">
          <span>🔌</span>
          <span>Connect Local AI Agents (Claude Desktop &amp; Cursor)</span>
        </div>
        <span id="qc-chevron" style="font-size: 12px;">▼ Show Config</span>
      </div>
      <div id="quick-connect-body" class="qc-body">
        <p style="font-size: 13px; color: var(--text-muted); margin-bottom: 12px;">
          Add this server to your local Claude Desktop or Cursor configuration to let AI agents use these tools:
        </p>
        <div class="qc-grid">
          <div class="qc-box">
            <div class="qc-box-title">
              <span style="color: #58a6ff;">Claude Desktop (claude_desktop_config.json)</span>
              <button class="copy-btn" onclick="copySnippet('claude-cfg', this)">📋 Copy</button>
            </div>
            <pre id="claude-cfg" class="qc-pre">&#123;
  "mcpServers": &#123;
    "fastapi-mcp": &#123;
      "url": "http://127.0.0.1:8000{mcp_path}"
    &#125;
  &#125;
&#125;</pre>
          </div>
          <div class="qc-box">
            <div class="qc-box-title">
              <span style="color: #7ee787;">Cursor IDE (.cursor/mcp.json)</span>
              <button class="copy-btn" onclick="copySnippet('cursor-cfg', this)">📋 Copy</button>
            </div>
            <pre id="cursor-cfg" class="qc-pre">&#123;
  "mcpServers": &#123;
    "fastapi-mcp": &#123;
      "url": "http://127.0.0.1:8000{mcp_path}"
    &#125;
  &#125;
&#125;</pre>
          </div>
        </div>
      </div>
    </div>

    <div id="tools-container"></div>
  </div>

  <script>
    const toolsData = {tools_json};
    const testCallUrl = "{call_url}";

    function toggleQuickConnect() {{
      const body = document.getElementById("quick-connect-body");
      const chevron = document.getElementById("qc-chevron");
      if (body.style.display === "none" || !body.style.display) {{
        body.style.display = "block";
        chevron.innerText = "▲ Hide Config";
      }} else {{
        body.style.display = "none";
        chevron.innerText = "▼ Show Config";
      }}
    }}

    function copySnippet(elementId, btn) {{
      const text = document.getElementById(elementId).innerText;
      navigator.clipboard.writeText(text).then(() => {{
        const orig = btn.innerText;
        btn.innerText = "✓ Copied!";
        setTimeout(() => {{ btn.innerText = orig; }}, 2000);
      }}).catch(() => {{
        btn.innerText = "Copy manually";
      }});
    }}

    function renderTools() {{
      const container = document.getElementById("tools-container");
      if (!toolsData || toolsData.length === 0) {{
        container.innerHTML = '<div class="empty-state">No MCP tools registered.</div>';
        return;
      }}

      container.innerHTML = toolsData.map((tool, idx) => {{
        const rawProps = tool.input_schema ? tool.input_schema.properties : {{}};
        const props = rawProps || {{}};
        const reqs = (tool.input_schema && tool.input_schema.required) || [];

        const paramRows = Object.entries(props).map(([name, schema]) => {{
          const isReq = reqs.includes(name);
          const type = schema.type || (schema.$ref ? schema.$ref.split('/').pop() : 'any');
          const desc = schema.description || '';
          const def = schema.default !== undefined ? `default: ${schema.default}` : '';
          return `
            <tr>
              <td>
                <span class="param-name">${name}</span>
                ${isReq ? '<span class="param-req">*required</span>' : ''}
              </td>
              <td><span class="param-type">${type}</span></td>
              <td>${desc} ${def ? `<span style="color:#8b949e">(${def})</span>` : ''}</td>
            </tr>
          `;
        }}).join('');

        const inputFields = Object.entries(props).map(([name, schema]) => {{
          const isReq = reqs.includes(name);
          const type = schema.type || 'string';
          const placeholder = schema.default !== undefined ? String(schema.default) : (schema.description || name);
          let inputHtml = '';
          if (type === 'integer' || type === 'number') {{
            inputHtml = `<input type="number" id="input-${idx}-${name}" placeholder="${placeholder}" step="any" ${isReq ? 'required' : ''}>`;
          }} else if (type === 'boolean') {{
            inputHtml = `
              <select id="input-${idx}-${name}">
                <option value="true" ${schema.default === true ? 'selected' : ''}>true</option>
                <option value="false" ${schema.default === false ? 'selected' : ''}>false</option>
              </select>
            `;
          }} else if (type === 'object' || schema.$ref) {{
            inputHtml = `<textarea id="input-${idx}-${name}" placeholder='{"key": "value"}'></textarea>`;
          }} else {{
            inputHtml = `<input type="text" id="input-${idx}-${name}" placeholder="${placeholder}" ${isReq ? 'required' : ''}>`;
          }}

          return `
            <div class="form-group">
              <label class="form-label">${name} ${isReq ? '<span class="param-req">*</span>' : ''}</label>
              ${inputHtml}
            </div>
          `;
        }}).join('');

        return `
          <div class="card" id="card-${idx}">
            <div class="card-header" onclick="toggleCard(${idx})">
              <div class="card-title-group">
                <span class="tool-method ${tool.tool_type === 'REST + MCP' ? 'badge-dual' : 'badge-mcp'}">${tool.tool_type || 'MCP TOOL'}</span>
                <div>
                  <div class="tool-name">${tool.name}</div>
                  <div class="tool-desc">${tool.description || 'No description provided'}</div>
                </div>
              </div>
              <div class="chevron">▼</div>
            </div>
            <div class="card-body">
              <h4 style="margin-bottom: 8px; color: #fff; font-size: 13px;">Parameters</h4>
              ${Object.keys(props).length > 0 ? `
                <table class="params-table">
                  <thead>
                    <tr><th>Parameter</th><th>Type</th><th>Description</th></tr>
                  </thead>
                  <tbody>${paramRows}</tbody>
                </table>
              ` : '<p style="color: #8b949e; font-size: 13px; margin-bottom: 16px;">This tool takes no parameters.</p>'}

              <div style="margin-top: 16px; padding-top: 16px; border-top: 1px solid #21262d;">
                <h4 style="margin-bottom: 12px; color: #fff; font-size: 13px;">Try it out (Execute Live)</h4>
                <form onsubmit="executeTool(event, ${idx}, '${tool.name}')">
                  ${inputFields}
                  <button type="submit" class="btn btn-primary" id="btn-exec-${idx}">
                    ⚡ Execute Tool
                  </button>
                </form>
                <div class="output-box" id="output-${idx}">
                  <div class="output-header">
                    <span>Server Response</span>
                    <span class="status-badge" id="badge-${idx}">200 OK</span>
                  </div>
                  <div id="output-text-${idx}"></div>
                </div>
              </div>
            </div>
          </div>
        `;
      }}).join('');
    }}

    function toggleCard(idx) {{
      const card = document.getElementById(`card-${idx}`);
      card.classList.toggle('expanded');
    }}

    async function executeTool(event, idx, toolName) {{
      event.preventDefault();
      const tool = toolsData[idx];
      const props = (tool.input_schema && tool.input_schema.properties) || {{}};
      const args = {{}};

      for (const [name, schema] of Object.entries(props)) {{
        const el = document.getElementById(`input-${idx}-${name}`);
        if (!el) continue;
        const val = el.value.trim();
        if (val === '') continue;

        const type = schema.type || 'string';
        if (type === 'integer') {{
          args[name] = parseInt(val, 10);
        }} else if (type === 'number') {{
          args[name] = parseFloat(val);
        }} else if (type === 'boolean') {{
          args[name] = val === 'true';
        }} else if (type === 'object' || schema.$ref) {{
          try {{
            args[name] = JSON.parse(val);
          }} catch (e) {{
            alert(`Invalid JSON in field '${name}': ${e.message}`);
            return;
          }}
        }} else {{
          args[name] = val;
        }}
      }}

      const outBox = document.getElementById(`output-${idx}`);
      const outText = document.getElementById(`output-text-${idx}`);
      const btn = document.getElementById(`btn-exec-${idx}`);
      const badge = document.getElementById(`badge-${idx}`);

      btn.disabled = true;
      btn.innerText = "Executing...";
      outBox.style.display = "block";
      outBox.classList.remove('output-error');
      badge.innerText = "Executing...";
      outText.innerText = "Calling MCP tool in-process...";

      const startTime = performance.now();
      try {{
        const resp = await fetch(testCallUrl, {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify({{ name: toolName, arguments: args }})
        }});
        const data = await resp.json();
        const duration = Math.round(performance.now() - startTime);
        btn.disabled = false;
        btn.innerText = "⚡ Execute Tool";

        if (!resp.ok || data.is_error) {{
          outBox.classList.add('output-error');
          badge.innerText = `${resp.status || 400} Error (${duration}ms)`;
        }} else {{
          badge.innerText = `200 OK (${duration}ms)`;
        }}
        outText.innerText = JSON.stringify(data, null, 2);
      }} catch (err) {{
        const duration = Math.round(performance.now() - startTime);
        btn.disabled = false;
        btn.innerText = "⚡ Execute Tool";
        outBox.classList.add('output-error');
        badge.innerText = `Network Error (${duration}ms)`;
        outText.innerText = `Error connecting to test runner: ${err.message}`;
      }}
    }}

    renderTools();
  </script>
</body>
</html>
"""


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
    """Recursively resolves and inlines $ref pointers from $defs to eliminate resolver errors."""
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
    """Generates an OpenAPI 3.1 specification for registered MCP tools.

    Args:
        title: Title of the API documentation.
        tools: List of Tool objects or tool dictionaries.
        mcp_path: Base mount path for the MCP endpoints.
        version: API version string.
        catalog: Optional internal tool catalog to extract route tags and metadata.

    Returns:
        A dictionary compliant with OpenAPI 3.1 schema.
    """
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

        # Extract tags from catalog if available
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
                "Interactive OpenAPI 3.1 documentation for Model Context Protocol (MCP) Tools. "
                "Execute tools directly via Swagger UI or inspect schemas."
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
    mcp_path: str = "/mcp",
    sse_path: str = "/sse",
    ui_path: str = "/mcp/ui",
    catalog: Optional[Dict[str, Any]] = None,
) -> str:
    """Renders the official Swagger UI embedding the generated OpenAPI specification."""
    del mcp_path, sse_path, catalog
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

    docs_url = openapi_url.replace("/openapi.json", "/docs")
    font_stack = (
        "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"
    )
    nav_bar = (
        '<div style="background:#1b1b1b; padding: 12px 24px; display: flex; '
        'justify-content: space-between; align-items: center; border-bottom: 2px solid #49cc90; '
        f'font-family: {font_stack};">\n'
        '  <div style="display: flex; align-items: center; gap: 12px;">\n'
        '    <span style="color: #49cc90; font-weight: 700; font-size: 17px; '
        'letter-spacing: -0.5px;">⚡ FastMCP</span>\n'
        f'    <span style="color: #ffffff; font-size: 14px; font-weight: 600;">{title}</span>\n'
        '    <span style="background: #238636; color: #ffffff; font-size: 11px; '
        'padding: 2px 8px; border-radius: 10px; font-weight: 700;">OAS 3.1</span>\n'
        '  </div>\n'
        '  <div style="display: flex; gap: 16px; font-size: 13px; font-weight: 500;">\n'
        f'    <a href="{docs_url}" style="color: #49cc90; text-decoration: none; '
        'font-weight: 700; border-bottom: 2px solid #49cc90; padding-bottom: 2px;">'
        '🟢 Official Swagger UI</a>\n'
        f'    <a href="{ui_path}" style="color: #61affe; text-decoration: none; '
        'padding-bottom: 2px;">⚡ Offline Explorer</a>\n'
        f'    <a href="{openapi_url}" target="_blank" style="color: #ff9800; '
        'text-decoration: none; padding-bottom: 2px;">📄 openapi.json ↗</a>\n'
        '    <a href="/docs" target="_blank" style="color: #c9d1d9; text-decoration: none; '
        'padding-bottom: 2px;">🌐 REST API /docs ↗</a>\n'
        '    <a href="javascript:void(0)" onclick="alert(\'Claude Desktop & Cursor Config:\\n\\n'
        '{\\n  \\\"mcpServers\\\": {\\n    \\\"fastapi-mcp\\\": {\\n      '
        '\\\"url\\\": \\\"http://127.0.0.1:8000/mcp\\\"\\n    }\\n  }\\n}\')" '
        'style="color: #58a6ff; text-decoration: none; padding-bottom: 2px;">🔌 Connect Client</a>\n'
        '  </div>\n'
        '</div>'
    )
    if '<div id="swagger-ui">' in raw_html:
        return raw_html.replace('<div id="swagger-ui">', f'{nav_bar}\n<div id="swagger-ui">')
    return raw_html


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


def get_mcp_swagger_html(
    title: str,
    tools: list,
    mcp_path: str = "/mcp",
    sse_path: str = "/sse",
    call_url: str = "/mcp/ui/call",
    docs_path: str = "/mcp/docs",
    openapi_path: str = "/mcp/openapi.json",
    ui_path: str = "/mcp/ui",
    catalog: Optional[Dict[str, Any]] = None,
) -> str:
    """Renders the standalone offline Swagger-inspired MCP HTML page."""
    tools_json = json.dumps([_serialize_tool_for_ui(t, catalog=catalog) for t in tools])
    return (
        OFFLINE_HTML_TEMPLATE.replace("{title}", title)
        .replace("{tools_json}", tools_json)
        .replace("{mcp_path}", mcp_path)
        .replace("{sse_path}", sse_path)
        .replace("{call_url}", call_url)
        .replace("{docs_path}", docs_path)
        .replace("{openapi_path}", openapi_path)
        .replace("{ui_path}", ui_path)
    )
