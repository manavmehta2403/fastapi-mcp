"""Interactive Swagger-style UI for FastMCP / Model Context Protocol.

Provides an interactive playground at `/mcp/docs` where developers can inspect
registered tools, view schemas, fill in parameters, and execute tools live in the browser.
"""

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} - MCP Swagger Explorer</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500;600&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg: #0d1117;
      --card-bg: #161b22;
      --border: #30363d;
      --text: #c9d1d9;
      --text-muted: #8b949e;
      --primary: #58a6ff;
      --primary-hover: #1f6feb;
      --success: #238636;
      --success-hover: #2ea043;
      --badge-tool: #8957e5;
      --code-bg: #090d13;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
      background-color: var(--bg);
      color: var(--text);
      line-height: 1.5;
      padding: 24px;
    }
    .container { max-width: 1000px; margin: 0 auto; }
    header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 24px;
      padding-bottom: 20px;
      border-bottom: 1px solid var(--border);
    }
    h1 { font-size: 26px; color: #fff; font-weight: 700; display: flex; align-items: center; gap: 10px; }
    .badge {
      font-size: 11px;
      font-weight: 600;
      padding: 3px 8px;
      border-radius: 12px;
      text-transform: uppercase;
      background: var(--badge-tool);
      color: #fff;
    }
    .endpoint-info {
      display: flex;
      gap: 12px;
      margin-top: 10px;
      font-size: 13px;
      color: var(--text-muted);
    }
    .endpoint-pill {
      background: #21262d;
      padding: 4px 10px;
      border-radius: 6px;
      border: 1px solid var(--border);
      font-family: 'Fira Code', monospace;
    }
    .card {
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 8px;
      margin-bottom: 16px;
      overflow: hidden;
      transition: border-color 0.15s ease;
    }
    .card:hover { border-color: #58a6ff; }
    .card-header {
      padding: 16px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      cursor: pointer;
      user-select: none;
    }
    .card-title-group { display: flex; align-items: center; gap: 12px; }
    .tool-method {
      background: #1f6feb;
      color: #fff;
      font-size: 11px;
      font-weight: 700;
      padding: 3px 8px;
      border-radius: 4px;
      font-family: 'Fira Code', monospace;
    }
    .tool-name { font-weight: 600; font-size: 16px; color: #fff; font-family: 'Fira Code', monospace; }
    .tool-desc { color: var(--text-muted); font-size: 14px; margin-top: 4px; }
    .chevron { transition: transform 0.2s ease; }
    .expanded .chevron { transform: rotate(180deg); }
    .card-body {
      display: none;
      padding: 16px;
      border-top: 1px solid var(--border);
      background: #0d1117;
    }
    .expanded .card-body { display: block; }
    .params-table {
      width: 100%;
      border-collapse: collapse;
      margin-bottom: 16px;
      font-size: 13px;
    }
    .params-table th, .params-table td {
      padding: 10px;
      text-align: left;
      border-bottom: 1px solid #21262d;
    }
    .params-table th { color: var(--text-muted); font-weight: 600; }
    .param-name { font-family: 'Fira Code', monospace; color: #58a6ff; font-weight: 600; }
    .param-type { font-family: 'Fira Code', monospace; color: #ff7b72; font-size: 12px; }
    .param-req { color: #f85149; font-size: 11px; font-weight: 600; margin-left: 4px; }
    .form-group { margin-bottom: 12px; }
    .form-label { display: block; font-size: 13px; font-weight: 500; margin-bottom: 6px; color: #fff; }
    input[type="text"], input[type="number"], textarea, select {
      width: 100%;
      padding: 8px 12px;
      background: #161b22;
      border: 1px solid var(--border);
      border-radius: 6px;
      color: #fff;
      font-family: 'Fira Code', monospace;
      font-size: 13px;
    }
    input:focus, textarea:focus {
      outline: none;
      border-color: var(--primary);
      box-shadow: 0 0 0 2px rgba(88, 166, 255, 0.2);
    }
    textarea { min-height: 80px; resize: vertical; }
    .btn {
      padding: 8px 16px;
      border-radius: 6px;
      font-weight: 600;
      font-size: 13px;
      cursor: pointer;
      border: none;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      transition: background 0.15s ease;
    }
    .btn-primary { background: var(--success); color: #fff; }
    .btn-primary:hover { background: var(--success-hover); }
    .btn-try { background: #21262d; color: #58a6ff; border: 1px solid var(--border); }
    .btn-try:hover { background: #30363d; }
    .output-box {
      margin-top: 16px;
      background: var(--code-bg);
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 12px;
      font-family: 'Fira Code', monospace;
      font-size: 12px;
      color: #7ee787;
      white-space: pre-wrap;
      word-break: break-all;
      display: none;
    }
    .output-header {
      font-size: 11px;
      font-weight: 600;
      color: var(--text-muted);
      margin-bottom: 6px;
      text-transform: uppercase;
    }
    .output-error { color: #f85149; border-color: #f85149; }
    .empty-state { text-align: center; padding: 48px; color: var(--text-muted); }
  </style>
</head>
<body>
  <div class="container">
    <header>
      <div>
        <h1>
          <span>{title}</span>
          <span class="badge">FastMCP Explorer</span>
        </h1>
        <p style="color: var(--text-muted); margin-top: 6px;">
          Interactive Swagger-like playground for Model Context Protocol (MCP) tools.
        </p>
        <div class="endpoint-info">
          <span>REST Docs: <a href="/docs" target="_blank" style="color: #58a6ff; text-decoration: none;">/docs</a></span>
          <span>MCP SSE: <span class="endpoint-pill">{sse_path}</span></span>
          <span>MCP Streamable: <span class="endpoint-pill">{mcp_path}</span></span>
        </div>
      </div>
    </header>

    <div id="tools-container">
      <!-- Tools rendered here via JavaScript -->
    </div>
  </div>

  <script>
    const toolsData = {tools_json};
    const testCallUrl = "{call_url}";

    function renderTools() {
      const container = document.getElementById("tools-container");
      if (!toolsData || toolsData.length === 0) {
        container.innerHTML = '<div class="empty-state">No MCP tools registered.</div>';
        return;
      }

      container.innerHTML = toolsData.map((tool, idx) => {
        const props = tool.input_schema.properties || {};
        const reqs = tool.input_schema.required || [];

        const paramRows = Object.entries(props).map(([name, schema]) => {
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
        }).join('');

        const inputFields = Object.entries(props).map(([name, schema]) => {
          const isReq = reqs.includes(name);
          const type = schema.type || 'string';
          const placeholder = schema.default !== undefined ? String(schema.default) : (schema.description || name);
          
          let inputHtml = '';
          if (type === 'integer' || type === 'number') {
            inputHtml = `<input type="number" id="input-${idx}-${name}" placeholder="${placeholder}" step="any" ${isReq ? 'required' : ''}>`;
          } else if (type === 'boolean') {
            inputHtml = `
              <select id="input-${idx}-${name}">
                <option value="true" ${schema.default === true ? 'selected' : ''}>true</option>
                <option value="false" ${schema.default === false ? 'selected' : ''}>false</option>
              </select>
            `;
          } else if (type === 'object' || schema.$ref) {
            inputHtml = `<textarea id="input-${idx}-${name}" placeholder='{"key": "value"}'></textarea>`;
          } else {
            inputHtml = `<input type="text" id="input-${idx}-${name}" placeholder="${placeholder}" ${isReq ? 'required' : ''}>`;
          }

          return `
            <div class="form-group">
              <label class="form-label">${name} ${isReq ? '<span class="param-req">*</span>' : ''}</label>
              ${inputHtml}
            </div>
          `;
        }).join('');

        return `
          <div class="card" id="card-${idx}">
            <div class="card-header" onclick="toggleCard(${idx})">
              <div class="card-title-group">
                <span class="tool-method">TOOL</span>
                <div>
                  <div class="tool-name">${tool.name}</div>
                  <div class="tool-desc">${tool.description || 'No description provided'}</div>
                </div>
              </div>
              <div class="chevron">▼</div>
            </div>
            <div class="card-body">
              <h4 style="margin-bottom: 8px; color: #fff; font-size: 14px;">Parameters</h4>
              ${Object.keys(props).length > 0 ? `
                <table class="params-table">
                  <thead>
                    <tr><th>Parameter</th><th>Type</th><th>Description</th></tr>
                  </thead>
                  <tbody>${paramRows}</tbody>
                </table>
              ` : '<p style="color: #8b949e; font-size: 13px; margin-bottom: 16px;">This tool takes no parameters.</p>'}

              <div style="margin-top: 16px; padding-top: 16px; border-top: 1px solid #21262d;">
                <h4 style="margin-bottom: 12px; color: #fff; font-size: 14px;">Try it out (Execute Live)</h4>
                <form onsubmit="executeTool(event, ${idx}, '${tool.name}')">
                  ${inputFields}
                  <button type="submit" class="btn btn-primary" id="btn-exec-${idx}">
                    ⚡ Execute Tool
                  </button>
                </form>
                <div class="output-box" id="output-${idx}">
                  <div class="output-header">Live Response</div>
                  <div id="output-text-${idx}"></div>
                </div>
              </div>
            </div>
          </div>
        `;
      }).join('');
    }

    function toggleCard(idx) {
      const card = document.getElementById(`card-${idx}`);
      card.classList.toggle('expanded');
    }

    async function executeTool(event, idx, toolName) {
      event.preventDefault();
      const tool = toolsData[idx];
      const props = tool.input_schema.properties || {};
      const args = {};

      for (const [name, schema] of Object.entries(props)) {
        const el = document.getElementById(`input-${idx}-${name}`);
        if (!el) continue;
        const val = el.value.trim();
        if (val === '') continue;

        const type = schema.type || 'string';
        if (type === 'integer') {
          args[name] = parseInt(val, 10);
        } else if (type === 'number') {
          args[name] = parseFloat(val);
        } else if (type === 'boolean') {
          args[name] = val === 'true';
        } else if (type === 'object' || schema.$ref) {
          try {
            args[name] = JSON.parse(val);
          } catch (e) {
            alert(`Invalid JSON in field '${name}': ${e.message}`);
            return;
          }
        } else {
          args[name] = val;
        }
      }

      const outBox = document.getElementById(`output-${idx}`);
      const outText = document.getElementById(`output-text-${idx}`);
      const btn = document.getElementById(`btn-exec-${idx}`);

      btn.disabled = true;
      btn.innerText = "Executing...";
      outBox.style.display = "block";
      outBox.classList.remove('output-error');
      outText.innerText = "Calling MCP tool in-process...";

      try {
        const resp = await fetch(testCallUrl, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name: toolName, arguments: args })
        });
        const data = await resp.json();
        btn.disabled = false;
        btn.innerText = "⚡ Execute Tool";

        if (!resp.ok || data.is_error) {
          outBox.classList.add('output-error');
        }
        outText.innerText = JSON.stringify(data, null, 2);
      } catch (err) {
        btn.disabled = false;
        btn.innerText = "⚡ Execute Tool";
        outBox.classList.add('output-error');
        outText.innerText = `Error connecting to test runner: ${err.message}`;
      }
    }

    renderTools();
  </script>
</body>
</html>
"""


def get_mcp_swagger_html(
    title: str,
    tools: list,
    mcp_path: str = "/mcp",
    sse_path: str = "/sse",
    call_url: str = "/mcp/ui/call",
) -> str:
    """Renders the interactive MCP Swagger HTML page."""
    import json
    tools_json = json.dumps([t.model_dump() for t in tools])
    return HTML_TEMPLATE.replace("{title}", title)\
                        .replace("{tools_json}", tools_json)\
                        .replace("{mcp_path}", mcp_path)\
                        .replace("{sse_path}", sse_path)\
                        .replace("{call_url}", call_url)
