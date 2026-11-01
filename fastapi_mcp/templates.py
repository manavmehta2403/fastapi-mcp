"""HTML and CSS templates for FastAPI-MCP documentation and developer studio."""

NAV_CSS = """
<style>
  :root {
    --fapm-bg: #0d1117;
    --fapm-border: rgba(255, 255, 255, 0.1);
    --fapm-text: #e6edf3;
    --fapm-text-muted: #8b949e;
    --fapm-accent-mcp: #238636;
    --fapm-accent-rest: #1f6feb;
    --fapm-accent-studio: #8957e5;
  }
  .fapm-nav-dock {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    height: 42px;
    background: rgba(13, 17, 23, 0.94);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border-bottom: 1px solid var(--fapm-border);
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 16px;
    z-index: 999999;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    box-sizing: border-box;
  }
  .fapm-nav-dock * {
    box-sizing: border-box;
  }
  .fapm-nav-brand {
    display: flex;
    align-items: center;
    gap: 8px;
    text-decoration: none;
  }
  .fapm-brand-logo {
    color: #49cc90;
    font-weight: 800;
    font-size: 15px;
    letter-spacing: -0.5px;
  }
  .fapm-brand-title {
    color: #ffffff;
    font-size: 13px;
    font-weight: 600;
  }
  .fapm-badge-ver {
    background: rgba(255, 255, 255, 0.08);
    color: #8b949e;
    font-size: 10px;
    font-weight: 600;
    padding: 1px 6px;
    border-radius: 10px;
  }
  .fapm-nav-tabs {
    display: flex;
    align-items: center;
    gap: 12px;
    font-size: 12px;
  }
  .fapm-tab-group {
    display: flex;
    align-items: center;
    gap: 4px;
    background: rgba(255, 255, 255, 0.04);
    padding: 2px 4px;
    border-radius: 6px;
    border: 1px solid rgba(255, 255, 255, 0.06);
  }
  .fapm-group-label {
    color: #8b949e;
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    padding: 0 4px;
  }
  .fapm-tab-link {
    color: #c9d1d9;
    text-decoration: none;
    padding: 3px 8px;
    border-radius: 4px;
    font-weight: 500;
    transition: background 0.15s, color 0.15s;
  }
  .fapm-tab-link:hover {
    color: #ffffff;
    background: rgba(255, 255, 255, 0.08);
  }
  .fapm-tab-link.active-rest {
    background: var(--fapm-accent-rest);
    color: #ffffff;
    font-weight: 600;
  }
  .fapm-tab-link.active-mcp {
    background: var(--fapm-accent-mcp);
    color: #ffffff;
    font-weight: 600;
  }
  .fapm-tab-link.active-studio {
    background: var(--fapm-accent-studio);
    color: #ffffff;
    font-weight: 600;
  }
  .fapm-nav-actions {
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .fapm-btn-connect {
    background: rgba(56, 139, 253, 0.12);
    border: 1px solid rgba(56, 139, 253, 0.35);
    color: #58a6ff;
    padding: 3px 10px;
    border-radius: 6px;
    font-size: 11px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.15s ease;
  }
  .fapm-btn-connect:hover {
    background: rgba(56, 139, 253, 0.25);
    color: #ffffff;
  }
  .fapm-link-spec {
    color: #f0883e;
    text-decoration: none;
    font-size: 11px;
    font-weight: 500;
    padding: 3px 6px;
  }
  .fapm-link-spec:hover {
    text-decoration: underline;
  }

  /* Quick-Connect Modal */
  .fapm-modal-backdrop {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.7);
    backdrop-filter: blur(6px);
    display: none;
    align-items: center;
    justify-content: center;
    z-index: 1000000;
  }
  .fapm-modal-card {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 10px;
    width: 600px;
    max-width: 90vw;
    box-shadow: 0 16px 40px rgba(0,0,0,0.5);
    overflow: hidden;
  }
  .fapm-modal-header {
    padding: 14px 18px;
    border-bottom: 1px solid #30363d;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  .fapm-modal-title {
    color: #ffffff;
    font-size: 14px;
    font-weight: 700;
  }
  .fapm-modal-close {
    background: transparent;
    border: none;
    color: #8b949e;
    font-size: 16px;
    cursor: pointer;
  }
  .fapm-modal-close:hover {
    color: #ffffff;
  }
  .fapm-modal-tabs {
    display: flex;
    background: #0d1117;
    border-bottom: 1px solid #30363d;
    padding: 0 8px;
  }
  .fapm-modal-tab-btn {
    background: transparent;
    border: none;
    color: #8b949e;
    padding: 10px 14px;
    font-size: 12px;
    font-weight: 600;
    cursor: pointer;
    border-bottom: 2px solid transparent;
  }
  .fapm-modal-tab-btn.active {
    color: #58a6ff;
    border-bottom-color: #58a6ff;
  }
  .fapm-modal-body {
    padding: 16px;
  }
  .fapm-modal-pane {
    display: none;
  }
  .fapm-modal-pane.active {
    display: block;
  }
  .fapm-pane-hint {
    color: #8b949e;
    font-size: 12px;
    margin-bottom: 8px;
  }
  .fapm-code-box {
    background: #090d13;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 12px;
    position: relative;
  }
  .fapm-code-box pre {
    color: #79c0ff;
    font-family: monospace;
    font-size: 12px;
    margin: 0;
    white-space: pre;
    overflow-x: auto;
  }
  .fapm-btn-copy {
    position: absolute;
    top: 8px;
    right: 8px;
    background: #21262d;
    border: 1px solid #30363d;
    color: #c9d1d9;
    padding: 3px 8px;
    border-radius: 4px;
    font-size: 11px;
    cursor: pointer;
  }
  .fapm-btn-copy:hover {
    background: #30363d;
    color: #fff;
  }
</style>
"""

STUDIO_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} - FastAPI-MCP Studio</title>
  {nav_css}
  <style>
    body {
      margin: 0;
      padding-top: 42px;
      background-color: #090d13;
      color: #e6edf3;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      height: 100vh;
      display: flex;
      flex-direction: column;
      box-sizing: border-box;
      overflow: hidden;
    }
    .studio-layout {
      display: flex;
      flex: 1;
      height: calc(100vh - 42px);
      overflow: hidden;
    }
    .studio-sidebar {
      width: 340px;
      min-width: 280px;
      max-width: 400px;
      background: #0d1117;
      border-right: 1px solid #30363d;
      display: flex;
      flex-direction: column;
      height: 100%;
    }
    .sidebar-header {
      padding: 14px 16px;
      border-bottom: 1px solid #30363d;
      background: #161b22;
    }
    .sidebar-title {
      font-size: 13px;
      font-weight: 700;
      color: #fff;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    .offline-tag {
      font-size: 10px;
      background: #238636;
      color: #fff;
      padding: 2px 6px;
      border-radius: 8px;
      font-weight: 600;
    }
    .search-input {
      width: 100%;
      background: #090d13;
      border: 1px solid #30363d;
      color: #e6edf3;
      padding: 8px 12px;
      border-radius: 6px;
      font-size: 12px;
      margin-top: 10px;
      box-sizing: border-box;
      outline: none;
    }
    .search-input:focus {
      border-color: #58a6ff;
    }
    .filter-pills {
      display: flex;
      gap: 6px;
      margin-top: 8px;
    }
    .pill-btn {
      background: transparent;
      border: 1px solid #30363d;
      color: #8b949e;
      padding: 3px 8px;
      border-radius: 12px;
      font-size: 10px;
      cursor: pointer;
    }
    .pill-btn.active {
      background: rgba(56, 139, 253, 0.15);
      border-color: #58a6ff;
      color: #58a6ff;
    }
    .tool-list {
      flex: 1;
      overflow-y: auto;
      padding: 8px;
    }
    .tool-item {
      padding: 10px 12px;
      border-radius: 6px;
      cursor: pointer;
      margin-bottom: 4px;
      border: 1px solid transparent;
      transition: background 0.15s;
    }
    .tool-item:hover {
      background: rgba(255, 255, 255, 0.04);
    }
    .tool-item.active {
      background: rgba(35, 134, 54, 0.12);
      border-color: #238636;
    }
    .tool-item-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 6px;
    }
    .tool-item-name {
      font-family: monospace;
      font-size: 13px;
      font-weight: 600;
      color: #fff;
    }
    .badge-type {
      font-size: 9px;
      font-weight: 700;
      padding: 2px 6px;
      border-radius: 4px;
      text-transform: uppercase;
    }
    .badge-dual {
      background: rgba(129, 140, 248, 0.15);
      color: #818cf8;
      border: 1px solid rgba(129, 140, 248, 0.3);
    }
    .badge-mcp {
      background: rgba(16, 185, 129, 0.15);
      color: #34d399;
      border: 1px solid rgba(16, 185, 129, 0.3);
    }
    .tool-item-desc {
      color: #8b949e;
      font-size: 11px;
      margin-top: 4px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .studio-main {
      flex: 1;
      display: flex;
      flex-direction: column;
      height: 100%;
      overflow-y: auto;
      padding: 20px 24px;
      box-sizing: border-box;
      background: #090d13;
    }
    .workspace-card {
      background: #161b22;
      border: 1px solid #30363d;
      border-radius: 8px;
      padding: 20px;
      margin-bottom: 20px;
    }
    .workspace-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      border-bottom: 1px solid #30363d;
      padding-bottom: 14px;
      margin-bottom: 16px;
    }
    .workspace-tool-name {
      font-size: 20px;
      font-family: monospace;
      font-weight: 700;
      color: #fff;
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .workspace-desc {
      color: #8b949e;
      font-size: 13px;
      line-height: 1.5;
    }
    .workspace-endpoint {
      display: inline-block;
      margin-top: 8px;
      background: #090d13;
      padding: 4px 10px;
      border-radius: 4px;
      border: 1px solid #30363d;
      font-family: monospace;
      font-size: 11px;
      color: #79c0ff;
    }
    .param-group {
      margin-bottom: 14px;
    }
    .param-label {
      display: flex;
      align-items: center;
      justify-content: space-between;
      font-size: 12px;
      font-weight: 600;
      color: #c9d1d9;
      margin-bottom: 4px;
      font-family: monospace;
    }
    .param-req {
      color: #f85149;
      margin-left: 4px;
    }
    .param-type-badge {
      color: #8b949e;
      font-size: 10px;
      font-weight: normal;
    }
    .param-input {
      width: 100%;
      background: #090d13;
      border: 1px solid #30363d;
      color: #e6edf3;
      padding: 8px 12px;
      border-radius: 6px;
      font-size: 13px;
      box-sizing: border-box;
      outline: none;
    }
    .param-input:focus {
      border-color: #58a6ff;
    }
    .param-textarea {
      width: 100%;
      min-height: 70px;
      background: #090d13;
      border: 1px solid #30363d;
      color: #79c0ff;
      padding: 8px 12px;
      border-radius: 6px;
      font-size: 12px;
      font-family: monospace;
      box-sizing: border-box;
      outline: none;
    }
    .param-textarea:focus {
      border-color: #58a6ff;
    }
    .action-row {
      display: flex;
      align-items: center;
      gap: 12px;
      margin-top: 16px;
    }
    .btn-exec {
      background: #238636;
      border: none;
      color: #ffffff;
      padding: 10px 20px;
      border-radius: 6px;
      font-size: 13px;
      font-weight: 700;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 8px;
      transition: background 0.15s;
    }
    .btn-exec:hover {
      background: #2ea043;
    }
    .btn-exec:disabled {
      opacity: 0.6;
      cursor: not-allowed;
    }
    .output-section {
      background: #090d13;
      border: 1px solid #30363d;
      border-radius: 8px;
      overflow: hidden;
      margin-top: 20px;
    }
    .output-bar {
      padding: 10px 14px;
      background: #161b22;
      border-bottom: 1px solid #30363d;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    .status-badge {
      font-size: 11px;
      font-weight: 700;
      padding: 3px 8px;
      border-radius: 4px;
      background: #238636;
      color: #fff;
    }
    .status-badge.err {
      background: #da3633;
    }
    .output-pre {
      padding: 16px;
      margin: 0;
      color: #79c0ff;
      font-family: monospace;
      font-size: 12px;
      white-space: pre-wrap;
      max-height: 380px;
      overflow-y: auto;
    }
    .empty-state {
      text-align: center;
      padding: 40px;
      color: #8b949e;
      font-size: 14px;
    }
  </style>
</head>
<body>
  {nav_html}

  <div class="studio-layout">
    <!-- Left Sidebar -->
    <div class="studio-sidebar">
      <div class="sidebar-header">
        <div class="sidebar-title">
          <span>Registered Tools</span>
          <span class="offline-tag">Offline Mode</span>
        </div>
        <input type="text" id="search-input" class="search-input"
               placeholder="🔍 Filter tools..." oninput="filterTools()">
        <div class="filter-pills">
          <button class="pill-btn active" id="pill-all"
                  onclick="setFilter('all')">All</button>
          <button class="pill-btn" id="pill-dual"
                  onclick="setFilter('dual')">Dual REST+MCP</button>
          <button class="pill-btn" id="pill-mcp"
                  onclick="setFilter('mcp')">MCP Dedicated</button>
        </div>
      </div>
      <div class="tool-list" id="tool-list"></div>
    </div>

    <!-- Main Workspace -->
    <div class="studio-main" id="studio-main">
      <div id="workspace-content"></div>
    </div>
  </div>

  <script>
    const toolsData = {tools_json};
    const testCallUrl = "{call_url}";
    let selectedIndex = 0;
    let currentFilter = 'all';

    function setFilter(f) {
      currentFilter = f;
      document.querySelectorAll('.pill-btn').forEach(b => b.classList.remove('active'));
      document.getElementById('pill-' + f).classList.add('active');
      renderSidebar();
    }

    function filterTools() {
      renderSidebar();
    }

    function renderSidebar() {
      const query = (document.getElementById('search-input').value || '').toLowerCase();
      const listEl = document.getElementById('tool-list');

      let filtered = toolsData.map((t, idx) => ({ ...t, _origIndex: idx }));
      if (currentFilter === 'dual') {
        filtered = filtered.filter(t => t.tool_type === 'REST + MCP');
      } else if (currentFilter === 'mcp') {
        filtered = filtered.filter(t => t.tool_type !== 'REST + MCP');
      }

      if (query) {
        filtered = filtered.filter(t =>
          t.name.toLowerCase().includes(query) ||
          (t.description || '').toLowerCase().includes(query)
        );
      }

      if (filtered.length === 0) {
        listEl.innerHTML = '<div class="empty-state">No matching tools found.</div>';
        return;
      }

      listEl.innerHTML = filtered.map(t => {
        const isDual = t.tool_type === 'REST + MCP';
        const isSel = t._origIndex === selectedIndex;
        return `
          <div class="tool-item ${isSel ? 'active' : ''}" onclick="selectTool(${t._origIndex})">
            <div class="tool-item-header">
              <span class="tool-item-name">${t.name}</span>
              <span class="badge-type ${isDual ? 'badge-dual' : 'badge-mcp'}">${isDual ? 'DUAL' : 'MCP'}</span>
            </div>
            <div class="tool-item-desc">${t.description || 'No description provided'}</div>
          </div>
        `;
      }).join('');
    }

    function selectTool(idx) {
      selectedIndex = idx;
      renderSidebar();
      renderWorkspace();
    }

    function renderWorkspace() {
      const tool = toolsData[selectedIndex];
      const container = document.getElementById('workspace-content');
      if (!tool) {
        container.innerHTML = '<div class="empty-state">Select a tool from the sidebar to inspect and run.</div>';
        return;
      }

      const rawProps = (tool.input_schema && tool.input_schema.properties) || {};
      const reqs = (tool.input_schema && tool.input_schema.required) || [];
      const isDual = tool.tool_type === 'REST + MCP';

      const fieldsHtml = Object.entries(rawProps).map(([name, schema]) => {
        const isReq = reqs.includes(name);
        const type = schema.type || 'string';
        const placeholder = schema.default !== undefined ? String(schema.default) : (schema.description || name);

        let inputControl = '';
        if (type === 'integer' || type === 'number') {
          inputControl = `<input type="number" id="in-${name}" class="param-input" placeholder="${placeholder}" ${isReq ? 'required' : ''}>`;
        } else if (type === 'boolean') {
          inputControl = `
            <select id="in-${name}" class="param-input">
              <option value="true" ${schema.default === true ? 'selected' : ''}>true</option>
              <option value="false" ${schema.default === false ? 'selected' : ''}>false</option>
            </select>
          `;
        } else if (type === 'object' || schema.$ref) {
          inputControl = `<textarea id="in-${name}" class="param-textarea" placeholder='{"key": "value"}'></textarea>`;
        } else {
          inputControl = `<input type="text" id="in-${name}" class="param-input" placeholder="${placeholder}" ${isReq ? 'required' : ''}>`;
        }

        return `
          <div class="param-group">
            <label class="param-label">
              <span>${name} ${isReq ? '<span class="param-req">*</span>' : ''}</span>
              <span class="param-type-badge">${type}</span>
            </label>
            ${inputControl}
          </div>
        `;
      }).join('');

      container.innerHTML = `
        <div class="workspace-card">
          <div class="workspace-header">
            <div class="workspace-tool-name">
              <span>${tool.name}</span>
              <span class="badge-type ${isDual ? 'badge-dual' : 'badge-mcp'}">${isDual ? 'REST + MCP DUAL TOOL' : 'MCP DEDICATED TOOL'}</span>
            </div>
          </div>
          <div class="workspace-desc">${tool.description || 'No description provided.'}</div>
          <div class="workspace-endpoint">POST /mcp/tools/${tool.name}</div>
        </div>

        <div class="workspace-card">
          <h3 style="font-size: 14px; margin-bottom: 14px; color: #fff;">Parameters & Arguments</h3>
          ${Object.keys(rawProps).length > 0 ? `
            <form onsubmit="runTool(event, '${tool.name}')" id="tool-form">
              ${fieldsHtml}
              <div class="action-row">
                <button type="submit" class="btn-exec" id="btn-run">
                  ⚡ Execute Tool (Ctrl+Enter)
                </button>
              </div>
            </form>
          ` : `
            <p style="color: #8b949e; font-size: 13px; margin-bottom: 14px;">This tool does not require any parameters.</p>
            <form onsubmit="runTool(event, '${tool.name}')" id="tool-form">
              <button type="submit" class="btn-exec" id="btn-run">⚡ Execute Tool</button>
            </form>
          `}

          <div class="output-section" id="output-box" style="display: none;">
            <div class="output-bar">
              <span style="font-size: 12px; font-weight: 600; color: #c9d1d9;">Response Output</span>
              <div style="display: flex; gap: 8px; align-items: center;">
                <span class="status-badge" id="res-badge">200 OK</span>
                <button type="button" class="pill-btn" onclick="copyResponse()">📋 Copy JSON</button>
              </div>
            </div>
            <pre class="output-pre" id="output-text"></pre>
          </div>
        </div>
      `;
    }

    async function runTool(e, toolName) {
      if (e) e.preventDefault();
      const tool = toolsData[selectedIndex];
      const props = (tool.input_schema && tool.input_schema.properties) || {};
      const args = {};

      for (const [name, schema] of Object.entries(props)) {
        const el = document.getElementById('in-' + name);
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
          } catch (err) {
            alert(`Invalid JSON in field '${name}': ` + err.message);
            return;
          }
        } else {
          args[name] = val;
        }
      }

      const btn = document.getElementById('btn-run');
      const box = document.getElementById('output-box');
      const badge = document.getElementById('res-badge');
      const outText = document.getElementById('output-text');

      btn.disabled = true;
      btn.innerText = "Executing...";
      box.style.display = "block";
      badge.className = "status-badge";
      badge.innerText = "Running...";
      outText.innerText = "Executing in-process tool runner...";

      const t0 = performance.now();
      try {
        const resp = await fetch(testCallUrl, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name: toolName, arguments: args })
        });
        const data = await resp.json();
        const duration = Math.round(performance.now() - t0);
        btn.disabled = false;
        btn.innerText = "⚡ Execute Tool (Ctrl+Enter)";

        if (!resp.ok || data.is_error) {
          badge.className = "status-badge err";
          badge.innerText = `${resp.status || 400} ERROR (${duration}ms)`;
        } else {
          badge.className = "status-badge";
          badge.innerText = `200 OK (${duration}ms)`;
        }
        outText.innerText = JSON.stringify(data, null, 2);
      } catch (err) {
        const duration = Math.round(performance.now() - t0);
        btn.disabled = false;
        btn.innerText = "⚡ Execute Tool (Ctrl+Enter)";
        badge.className = "status-badge err";
        badge.innerText = `Network Error (${duration}ms)`;
        outText.innerText = `Error: ${err.message}`;
      }
    }

    function copyResponse() {
      const text = document.getElementById('output-text').innerText;
      navigator.clipboard.writeText(text).then(() => alert('Response copied!'));
    }

    document.addEventListener('keydown', (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        const form = document.getElementById('tool-form');
        if (form) form.requestSubmit();
      }
    });

    renderSidebar();
    renderWorkspace();
  </script>
</body>
</html>
"""
