"""HTML and CSS templates for FastAPI-MCP documentation and developer studio."""

NAV_CSS = """
<style>

  :root { --fapm-bg: #090d13; --fapm-card: #161b22; --fapm-border: rgba(255, 255, 255, 0.1); --fapm-text: #e6edf3; --fapm-text-muted: #8b949e; --fapm-accent-mcp: #238636; --fapm-accent-rest: #1f6feb; --fapm-accent-studio: #8957e5; }
  .fapm-nav-dock { position: fixed; top: 0; left: 0; right: 0; height: 42px; background: rgba(13, 17, 23, 0.94); backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px); border-bottom: 1px solid var(--fapm-border); display: flex; align-items: center; justify-content: space-between; padding: 0 16px; z-index: 999999; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; box-sizing: border-box; }
  .fapm-nav-dock * { box-sizing: border-box; }
  .fapm-nav-brand { display: flex; align-items: center; gap: 8px; text-decoration: none; }
  .fapm-brand-logo { color: #49cc90; font-weight: 800; font-size: 15px; letter-spacing: -0.5px; }
  .fapm-brand-title { color: #ffffff; font-size: 13px; font-weight: 600; }
  .fapm-badge-ver { background: rgba(255, 255, 255, 0.08); color: #8b949e; font-size: 10px; font-weight: 600; padding: 1px 6px; border-radius: 10px; }
  .fapm-nav-tabs { display: flex; align-items: center; gap: 12px; font-size: 12px; }
  .fapm-tab-group { display: flex; align-items: center; gap: 4px; background: rgba(255, 255, 255, 0.04); padding: 2px 4px; border-radius: 6px; border: 1px solid rgba(255, 255, 255, 0.06); }
  .fapm-group-label { color: #8b949e; font-size: 10px; font-weight: 700; text-transform: uppercase; padding: 0 4px; }
  .fapm-tab-link { color: #c9d1d9; text-decoration: none; padding: 3px 8px; border-radius: 4px; font-weight: 500; transition: background 0.15s, color 0.15s; }
  .fapm-tab-link:hover { color: #ffffff; background: rgba(255, 255, 255, 0.08); }
  .fapm-tab-link.active-rest { background: var(--fapm-accent-rest); color: #ffffff; font-weight: 600; }
  .fapm-tab-link.active-studio { background: var(--fapm-accent-mcp); color: #ffffff; font-weight: 600; }
  .fapm-nav-actions { display: flex; align-items: center; gap: 8px; }
  .fapm-btn-connect { background: rgba(56, 139, 253, 0.12); border: 1px solid rgba(56, 139, 253, 0.35); color: #58a6ff; padding: 3px 10px; border-radius: 6px; font-size: 11px; font-weight: 600; cursor: pointer; transition: all 0.15s ease; }
  .fapm-btn-connect:hover { background: rgba(56, 139, 253, 0.25); color: #ffffff; }

  /* Quick-Connect Modal */
  .fapm-modal-backdrop { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0, 0, 0, 0.7); backdrop-filter: blur(6px); display: none; align-items: center; justify-content: center; z-index: 1000000; }
  .fapm-modal-card { background: #161b22; border: 1px solid #30363d; border-radius: 10px; width: 600px; max-width: 90vw; box-shadow: 0 16px 40px rgba(0,0,0,0.5); overflow: hidden; }
  .fapm-modal-header { padding: 14px 18px; border-bottom: 1px solid #30363d; display: flex; justify-content: space-between; align-items: center; }
  .fapm-modal-title { color: #ffffff; font-size: 14px; font-weight: 700; }
  .fapm-modal-close { background: transparent; border: none; color: #8b949e; font-size: 16px; cursor: pointer; }
  .fapm-modal-close:hover { color: #ffffff; }
  .fapm-modal-tabs { display: flex; background: #0d1117; border-bottom: 1px solid #30363d; padding: 0 8px; }
  .fapm-modal-tab-btn { background: transparent; border: none; color: #8b949e; padding: 10px 14px; font-size: 12px; font-weight: 600; cursor: pointer; border-bottom: 2px solid transparent; }
  .fapm-modal-tab-btn.active { color: #58a6ff; border-bottom-color: #58a6ff; }
  .fapm-modal-body { padding: 16px; }
  .fapm-modal-pane { display: none; }
  .fapm-modal-pane.active { display: block; }
  .fapm-pane-hint { color: #8b949e; font-size: 12px; margin-bottom: 8px; }
  .fapm-code-box { background: #090d13; border: 1px solid #30363d; border-radius: 6px; padding: 12px; position: relative; }
  .fapm-code-box pre { color: #79c0ff; font-family: monospace; font-size: 12px; margin: 0; white-space: pre; overflow-x: auto; }
  .fapm-btn-copy { position: absolute; top: 8px; right: 8px; background: #21262d; border: 1px solid #30363d; color: #c9d1d9; padding: 3px 8px; border-radius: 4px; font-size: 11px; cursor: pointer; }
  .fapm-btn-copy:hover { background: #30363d; color: #fff; }

</style>
"""

STUDIO_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} - MCP Swagger Explorer & Studio</title>
  {nav_css}
  <style>

    body { margin: 0; padding-top: 42px; background-color: #090d13; color: #e6edf3; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; height: 100vh; display: flex; flex-direction: column; box-sizing: border-box; overflow: hidden; }
    .studio-subbar { height: 44px; background: #111520; border-bottom: 1px solid #30363d; display: flex; align-items: center; justify-content: space-between; padding: 0 16px; box-sizing: border-box; }
    .mcp-primitives-tabs { display: flex; gap: 6px; }
    .prim-tab { background: transparent; border: 1px solid transparent; color: #8b949e; padding: 6px 14px; border-radius: 6px; font-size: 12px; font-weight: 600; cursor: pointer; display: flex; align-items: center; gap: 6px; transition: all 0.15s ease; }
    .prim-tab:hover { color: #ffffff; background: rgba(255, 255, 255, 0.05); }
    .prim-tab.active { background: rgba(35, 134, 54, 0.2); border-color: #238636; color: #34d399; }
    .prim-counter { background: rgba(255, 255, 255, 0.1); color: #c9d1d9; font-size: 10px; padding: 1px 6px; border-radius: 10px; }
    .studio-layout { display: flex; flex: 1; height: calc(100vh - 86px); overflow: hidden; }
    .studio-sidebar { width: 340px; min-width: 280px; max-width: 400px; background: #0d1117; border-right: 1px solid #30363d; display: flex; flex-direction: column; height: 100%; }
    .sidebar-header { padding: 12px 16px; border-bottom: 1px solid #30363d; background: #161b22; }
    .sidebar-title { font-size: 12px; font-weight: 700; color: #fff; display: flex; align-items: center; justify-content: space-between; }
    .offline-tag { font-size: 10px; background: #238636; color: #fff; padding: 2px 6px; border-radius: 8px; font-weight: 600; }
    .search-input { width: 100%; background: #090d13; border: 1px solid #30363d; color: #e6edf3; padding: 7px 10px; border-radius: 6px; font-size: 12px; margin-top: 8px; box-sizing: border-box; outline: none; }
    .search-input:focus { border-color: #58a6ff; }
    .filter-pills { display: flex; gap: 6px; margin-top: 8px; }
    .pill-btn { background: transparent; border: 1px solid #30363d; color: #8b949e; padding: 2px 8px; border-radius: 12px; font-size: 10px; cursor: pointer; }
    .pill-btn.active { background: rgba(56, 139, 253, 0.15); border-color: #58a6ff; color: #58a6ff; }
    .items-list { flex: 1; overflow-y: auto; padding: 8px; }
    .item-card { padding: 10px 12px; border-radius: 6px; cursor: pointer; margin-bottom: 4px; border: 1px solid transparent; transition: background 0.15s; }
    .item-card:hover { background: rgba(255, 255, 255, 0.04); }
    .item-card.active { background: rgba(35, 134, 54, 0.12); border-color: #238636; }
    .item-header-row { display: flex; align-items: center; justify-content: space-between; gap: 6px; }
    .item-name { font-family: monospace; font-size: 13px; font-weight: 600; color: #fff; }
    .badge-type { font-size: 9px; font-weight: 700; padding: 2px 6px; border-radius: 4px; text-transform: uppercase; }
    .badge-dual { background: rgba(129, 140, 248, 0.15); color: #818cf8; border: 1px solid rgba(129, 140, 248, 0.3); }
    .badge-mcp { background: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.3); }
    .badge-res { background: rgba(245, 158, 11, 0.15); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.3); }
    .badge-prompt { background: rgba(236, 72, 153, 0.15); color: #f472b6; border: 1px solid rgba(236, 72, 153, 0.3); }
    .item-subtext { color: #8b949e; font-size: 11px; margin-top: 4px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

    /* Main Workspace */
    .studio-main { flex: 1; display: flex; flex-direction: column; height: 100%; overflow-y: auto; padding: 20px 24px; box-sizing: border-box; background: #090d13; }
    .workspace-card { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 20px; margin-bottom: 20px; }
    .workspace-header { display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid #30363d; padding-bottom: 14px; margin-bottom: 14px; }
    .workspace-title { font-size: 18px; font-family: monospace; font-weight: 700; color: #fff; display: flex; align-items: center; gap: 12px; }
    .workspace-desc { color: #8b949e; font-size: 13px; line-height: 1.5; }
    .param-group { margin-bottom: 12px; }
    .param-label { display: flex; align-items: center; justify-content: space-between; font-size: 12px; font-weight: 600; color: #c9d1d9; margin-bottom: 4px; font-family: monospace; }
    .param-req { color: #f85149; margin-left: 4px; }
    .param-type-badge { color: #8b949e; font-size: 10px; font-weight: normal; }
    .param-input { width: 100%; background: #090d13; border: 1px solid #30363d; color: #e6edf3; padding: 8px 12px; border-radius: 6px; font-size: 13px; box-sizing: border-box; outline: none; }
    .param-input:focus { border-color: #58a6ff; }
    .param-textarea { width: 100%; min-height: 60px; background: #090d13; border: 1px solid #30363d; color: #79c0ff; padding: 8px 12px; border-radius: 6px; font-size: 12px; font-family: monospace; box-sizing: border-box; outline: none; }
    .btn-exec { background: #238636; border: none; color: #ffffff; padding: 9px 18px; border-radius: 6px; font-size: 13px; font-weight: 700; cursor: pointer; display: flex; align-items: center; gap: 8px; transition: background 0.15s; }
    .btn-exec:hover { background: #2ea043; }
    .btn-exec:disabled { opacity: 0.6; cursor: not-allowed; }
    .output-section { background: #090d13; border: 1px solid #30363d; border-radius: 8px; overflow: hidden; margin-top: 16px; }
    .output-bar { padding: 8px 12px; background: #161b22; border-bottom: 1px solid #30363d; display: flex; align-items: center; justify-content: space-between; }
    .status-badge { font-size: 11px; font-weight: 700; padding: 3px 8px; border-radius: 4px; background: #238636; color: #fff; }
    .status-badge.err { background: #da3633; }
    .output-pre { padding: 14px; margin: 0; color: #79c0ff; font-family: monospace; font-size: 12px; white-space: pre-wrap; max-height: 320px; overflow-y: auto; }

    /* Snippet Box */
    .snippet-tabs { display: flex; gap: 6px; border-bottom: 1px solid #30363d; margin-bottom: 10px; }
    .snip-tab { background: transparent; border: none; color: #8b949e; padding: 6px 10px; font-size: 11px; font-weight: 600; cursor: pointer; border-bottom: 2px solid transparent; }
    .snip-tab.active { color: #58a6ff; border-bottom-color: #58a6ff; }
  
</style>
</head>
<body>
  {nav_html}

  <div class="studio-subbar">
    <div class="mcp-primitives-tabs">
      <button class="prim-tab active" id="tab-tools" onclick="switchStudioTab('tools')">
        <span>🛠️ Tools</span>
        <span class="prim-counter" id="cnt-tools">0</span>
      </button>
      <button class="prim-tab" id="tab-resources" onclick="switchStudioTab('resources')">
        <span>📦 Resources</span>
        <span class="prim-counter" id="cnt-resources">0</span>
      </button>
      <button class="prim-tab" id="tab-prompts" onclick="switchStudioTab('prompts')">
        <span>💬 Prompts</span>
        <span class="prim-counter" id="cnt-prompts">0</span>
      </button>
    </div>
    <div style="display:flex; align-items:center; gap:10px;">
      <a href="{openapi_url}" target="_blank" download="mcp-openapi.json" class="fapm-btn-connect" style="text-decoration:none;" title="Download OpenAPI 3.1 JSON Specification">📥 Export Spec</a>
      <span style="font-size: 11px; color: #8b949e;">FastMCP Engine Active</span>
    </div>
  </div>

  <div class="studio-layout">
    <div class="studio-sidebar">
      <div class="sidebar-header">
        <div class="sidebar-title">
          <span id="sidebar-heading">Registered Tools</span>
          <span class="offline-tag">Offline Mode</span>
        </div>
        <input type="text" id="search-input" class="search-input"
               placeholder="🔍 Search items... (/ or Ctrl+K)" oninput="filterActiveItems()">
        <div class="filter-pills" id="tools-filter-pills">
          <button class="pill-btn active" id="pill-all"
                  onclick="setToolFilter('all')">All</button>
          <button class="pill-btn" id="pill-dual"
                  onclick="setToolFilter('dual')">Dual REST+MCP</button>
          <button class="pill-btn" id="pill-mcp"
                  onclick="setToolFilter('mcp')">MCP Dedicated</button>
        </div>
      </div>
      <div class="items-list" id="items-list"></div>
    </div>

    <div class="studio-main" id="studio-main">
      <div id="workspace-content"></div>
    </div>
  </div>

  <script>
    const toolsData = {tools_json};
    const resourcesData = {resources_json};
    const promptsData = {prompts_json};

    const callUrl = "{call_url}";
    const resourceUrl = "{resource_url}";
    const promptUrl = "{prompt_url}";

    let activeStudioTab = 'tools';
    let toolIndex = 0;
    let resourceIndex = 0;
    let promptIndex = 0;
    let toolFilter = 'all';

    document.getElementById('cnt-tools').innerText = toolsData.length;
    document.getElementById('cnt-resources').innerText = resourcesData.length;
    document.getElementById('cnt-prompts').innerText = promptsData.length;

    function switchStudioTab(tab) {
      activeStudioTab = tab;
      document.querySelectorAll('.prim-tab').forEach(b => b.classList.remove('active'));
      document.getElementById('tab-' + tab).classList.add('active');

      const filterPills = document.getElementById('tools-filter-pills');
      const heading = document.getElementById('sidebar-heading');
      if (tab === 'tools') {
        filterPills.style.display = 'flex';
        heading.innerText = 'Registered Tools';
      } else if (tab === 'resources') {
        filterPills.style.display = 'none';
        heading.innerText = 'Registered Resources';
      } else {
        filterPills.style.display = 'none';
        heading.innerText = 'Registered Prompts';
      }

      document.getElementById('search-input').value = '';
      renderSidebar();
      renderWorkspace();
    }

    function setToolFilter(f) {
      toolFilter = f;
      document.querySelectorAll('.pill-btn').forEach(b => b.classList.remove('active'));
      document.getElementById('pill-' + f).classList.add('active');
      renderSidebar();
    }

    function filterActiveItems() {
      renderSidebar();
    }

    function renderSidebar() {
      const q = (document.getElementById('search-input').value || '').toLowerCase();
      const listEl = document.getElementById('items-list');

      if (activeStudioTab === 'tools') {
        let list = toolsData.map((t, idx) => ({ ...t, _origIdx: idx }));
        if (toolFilter === 'dual') list = list.filter(t => t.tool_type === 'REST + MCP');
        if (toolFilter === 'mcp') list = list.filter(t => t.tool_type !== 'REST + MCP');
        if (q) list = list.filter(t => t.name.toLowerCase().includes(q) || (t.description||'').toLowerCase().includes(q));

        if (list.length === 0) {
          listEl.innerHTML = '<div style="color:#8b949e;text-align:center;padding:20px;">No tools found.</div>';
          return;
        }

        listEl.innerHTML = list.map(t => {
          const isDual = t.tool_type === 'REST + MCP';
          const isSel = t._origIdx === toolIndex;
          return `
            <div class="item-card ${isSel ? 'active' : ''}" onclick="selectTool(${t._origIdx})">
              <div class="item-header-row">
                <span class="item-name">${t.name}</span>
                <span class="badge-type ${isDual ? 'badge-dual' : 'badge-mcp'}">${isDual ? 'DUAL' : 'MCP'}</span>
              </div>
              <div class="item-subtext">${t.description || 'No description'}</div>
            </div>
          `;
        }).join('');
      } else if (activeStudioTab === 'resources') {
        let list = resourcesData.map((r, idx) => ({ ...r, _origIdx: idx }));
        if (q) list = list.filter(r => r.name.toLowerCase().includes(q) || r.uri.toLowerCase().includes(q));

        if (list.length === 0) {
          listEl.innerHTML = '<div style="color:#8b949e;text-align:center;padding:20px;">No resources registered.</div>';
          return;
        }

        listEl.innerHTML = list.map(r => {
          const isSel = r._origIdx === resourceIndex;
          return `
            <div class="item-card ${isSel ? 'active' : ''}" onclick="selectResource(${r._origIdx})">
              <div class="item-header-row">
                <span class="item-name">${r.name || r.uri}</span>
                <span class="badge-type badge-res">RESOURCE</span>
              </div>
              <div class="item-subtext">${r.uri}</div>
            </div>
          `;
        }).join('');
      } else {
        let list = promptsData.map((p, idx) => ({ ...p, _origIdx: idx }));
        if (q) list = list.filter(p => p.name.toLowerCase().includes(q));

        if (list.length === 0) {
          listEl.innerHTML = '<div style="color:#8b949e;text-align:center;padding:20px;">No prompts registered.</div>';
          return;
        }

        listEl.innerHTML = list.map(p => {
          const isSel = p._origIdx === promptIndex;
          const argCount = (p.arguments || []).length;
          return `
            <div class="item-card ${isSel ? 'active' : ''}" onclick="selectPrompt(${p._origIdx})">
              <div class="item-header-row">
                <span class="item-name">${p.name}</span>
                <span class="badge-type badge-prompt">${argCount} ARGS</span>
              </div>
              <div class="item-subtext">${p.description || 'Prompt template'}</div>
            </div>
          `;
        }).join('');
      }
    }

    function selectTool(idx) {
      toolIndex = idx;
      renderSidebar();
      renderWorkspace();
    }

    function selectResource(idx) {
      resourceIndex = idx;
      renderSidebar();
      renderWorkspace();
    }

    function selectPrompt(idx) {
      promptIndex = idx;
      renderSidebar();
      renderWorkspace();
    }

    function renderWorkspace() {
      const container = document.getElementById('workspace-content');

      if (activeStudioTab === 'tools') {
        if (toolsData.length === 0) {
          container.innerHTML = `
            <div class="workspace-card" style="text-align:center; padding: 40px 20px;">
              <div style="font-size: 32px; margin-bottom: 12px;">🛠️</div>
              <h3 style="font-size: 16px; margin: 0 0 8px 0; color: #fff;">No MCP Tools Registered</h3>
              <p style="color: #8b949e; font-size: 13px; max-width: 480px; margin: 0 auto 16px auto;">
                Convert standard FastAPI routes using <code>@app.api_tool()</code>, or register dedicated tools with <code>@app.tool()</code>.
              </p>
            </div>
          `;
          return;
        }
        const tool = toolsData[toolIndex];
        if (!tool) {
          container.innerHTML = '<div style="color:#8b949e;padding:20px;">Select a tool.</div>';
          return;
        }
        const isDual = tool.tool_type === 'REST + MCP';
        const rawProps = (tool.input_schema && tool.input_schema.properties) || {};
        const reqs = (tool.input_schema && tool.input_schema.required) || [];

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
              <div class="workspace-title">
                <span>${tool.name}</span>
                <span class="badge-type ${isDual ? 'badge-dual' : 'badge-mcp'}">${isDual ? 'REST + MCP DUAL' : 'MCP DEDICATED'}</span>
              </div>
              <button type="button" class="pill-btn" onclick="copyToolSchema()" title="Copy Tool input schema as JSON">📋 Copy Schema</button>
            </div>
            <div class="workspace-desc">${tool.description || 'No description provided.'}</div>
          </div>

          <div class="workspace-card">
            <div class="snippet-tabs">
              <button class="snip-tab active" id="stab-py" onclick="showSnippet('py', '${tool.name}')">Python Client</button>
              <button class="snip-tab" id="stab-curl" onclick="showSnippet('curl', '${tool.name}')">cURL (JSON-RPC)</button>
              <button class="snip-tab" id="stab-ts" onclick="showSnippet('ts', '${tool.name}')">TypeScript SDK</button>
            </div>
            <div class="fapm-code-box">
              <pre id="code-snippet-pre"></pre>
              <button class="fapm-btn-copy" onclick="copySnippetText(this)">📋 Copy Snippet</button>
            </div>
          </div>

          <div class="workspace-card">
            <h3 style="font-size: 14px; margin-bottom: 12px; color: #fff;">Parameters & Arguments</h3>
            ${Object.keys(rawProps).length > 0 ? `
              <form onsubmit="runTool(event, '${tool.name}')" id="tool-form">
                ${fieldsHtml}
                <button type="submit" class="btn-exec" id="btn-run">⚡ Execute Tool (Ctrl+Enter)</button>
              </form>
            ` : `
              <p style="color: #8b949e; font-size: 13px; margin-bottom: 12px;">This tool accepts no arguments.</p>
              <form onsubmit="runTool(event, '${tool.name}')" id="tool-form">
                <button type="submit" class="btn-exec" id="btn-run">⚡ Execute Tool</button>
              </form>
            `}

            <div class="output-section" id="output-box" style="display: none;">
              <div class="output-bar">
                <span style="font-size: 12px; font-weight: 600; color: #c9d1d9;">Execution Result</span>
                <div style="display: flex; gap: 8px; align-items: center;">
                  <span class="status-badge" id="res-badge">200 OK</span>
                  <button type="button" class="pill-btn" onclick="copyOutputText()">📋 Copy JSON</button>
                </div>
              </div>
              <pre class="output-pre" id="output-text"></pre>
            </div>
          </div>
        `;
        showSnippet('py', tool.name);
      } else if (activeStudioTab === 'resources') {
        if (resourcesData.length === 0) {
          container.innerHTML = `
            <div class="workspace-card" style="text-align:center; padding: 40px 20px;">
              <div style="font-size: 32px; margin-bottom: 12px;">📦</div>
              <h3 style="font-size: 16px; margin: 0 0 8px 0; color: #fff;">No MCP Resources Registered</h3>
              <p style="color: #8b949e; font-size: 13px; max-width: 480px; margin: 0 auto 16px auto;">
                Expose contextual application state, files, or documents to AI models using <code>@app.resource("scheme://path")</code>.
              </p>
            </div>
          `;
          return;
        }
        const res = resourcesData[resourceIndex];
        if (!res) {
          container.innerHTML = '<div style="color:#8b949e;padding:20px;">No resource selected.</div>';
          return;
        }
        container.innerHTML = `
          <div class="workspace-card">
            <div class="workspace-header">
              <div class="workspace-title">
                <span>${res.name || res.uri}</span>
                <span class="badge-type badge-res">MCP RESOURCE</span>
              </div>
            </div>
            <div class="workspace-desc" style="margin-bottom: 12px;">${res.description || 'URI Resource'}</div>
            <div style="font-family: monospace; font-size: 12px; color: #79c0ff; background: #090d13; padding: 6px 10px; border-radius: 4px; display: inline-block;">
              ${res.uri}
            </div>
          </div>

          <div class="workspace-card">
            <button class="btn-exec" onclick="readResourceLive('${res.uri}')" id="btn-read-res">
              ⚡ Read Resource Live
            </button>
            <div class="output-section" id="res-output-box" style="display: none;">
              <div class="output-bar">
                <span style="font-size: 12px; font-weight: 600; color: #c9d1d9;">Resource Contents</span>
                <span class="status-badge" id="res-mime-badge">${res.mime_type || 'text/plain'}</span>
              </div>
              <pre class="output-pre" id="res-output-text"></pre>
            </div>
          </div>
        `;
      } else {
        if (promptsData.length === 0) {
          container.innerHTML = `
            <div class="workspace-card" style="text-align:center; padding: 40px 20px;">
              <div style="font-size: 32px; margin-bottom: 12px;">💬</div>
              <h3 style="font-size: 16px; margin: 0 0 8px 0; color: #fff;">No MCP Prompts Registered</h3>
              <p style="color: #8b949e; font-size: 13px; max-width: 480px; margin: 0 auto 16px auto;">
                Provide standardized, parameterized prompt templates to AI models using <code>@app.prompt("name")</code>.
              </p>
            </div>
          `;
          return;
        }
        const prompt = promptsData[promptIndex];
        if (!prompt) {
          container.innerHTML = '<div style="color:#8b949e;padding:20px;">No prompt selected.</div>';
          return;
        }
        const args = prompt.arguments || [];
        const argsHtml = args.map(a => `
          <div class="param-group">
            <label class="param-label">
              <span>${a.name} ${a.required ? '<span class="param-req">*</span>' : ''}</span>
            </label>
            <input type="text" id="parg-${a.name}" class="param-input" placeholder="${a.description || a.name}" ${a.required ? 'required' : ''}>
          </div>
        `).join('');

        container.innerHTML = `
          <div class="workspace-card">
            <div class="workspace-header">
              <div class="workspace-title">
                <span>${prompt.name}</span>
                <span class="badge-type badge-prompt">MCP PROMPT</span>
              </div>
            </div>
            <div class="workspace-desc">${prompt.description || 'Prompt template'}</div>
          </div>

          <div class="workspace-card">
            <h3 style="font-size: 14px; margin-bottom: 12px; color: #fff;">Prompt Arguments</h3>
            ${args.length > 0 ? `
              <form onsubmit="renderPromptLive(event, '${prompt.name}')">
                ${argsHtml}
                <button type="submit" class="btn-exec" id="btn-render-p">✨ Render Prompt</button>
              </form>
            ` : `
              <p style="color: #8b949e; font-size: 13px; margin-bottom: 12px;">This prompt takes no arguments.</p>
              <form onsubmit="renderPromptLive(event, '${prompt.name}')">
                <button type="submit" class="btn-exec" id="btn-render-p">✨ Render Prompt</button>
              </form>
            `}

            <div class="output-section" id="prompt-output-box" style="display: none;">
              <div class="output-bar">
                <span style="font-size: 12px; font-weight: 600; color: #c9d1d9;">Rendered Messages</span>
                <button type="button" class="pill-btn" onclick="copyPromptText()">📋 Copy</button>
              </div>
              <pre class="output-pre" id="prompt-output-text"></pre>
            </div>
          </div>
        `;
      }
    }

    function showSnippet(type, name) {
      document.querySelectorAll('.snip-tab').forEach(t => t.classList.remove('active'));
      const activeBtn = document.getElementById('stab-' + type);
      if (activeBtn) activeBtn.classList.add('active');

      const pre = document.getElementById('code-snippet-pre');
      const origin = window.location.origin || "http://127.0.0.1:8000";
      if (type === 'py') {
        pre.innerText = `from fastmcp import Client\\n\\nasync with Client("${origin}/mcp") as client:\\n    result = await client.call_tool("${name}", {})\\n    print(result)`;
      } else if (type === 'curl') {
        pre.innerText = `curl -X POST ${origin}/mcp \\\\\\n  -H "Content-Type: application/json" \\\\\\n  -d '{"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "${name}", "arguments": {}}}'`;
      } else {
        pre.innerText = `import { Client } from "@modelcontextprotocol/sdk/client/index.js";\\nimport { StreamableHTTPTransport } from "@modelcontextprotocol/sdk/client/streamableHttp.js";\\n\\nconst client = new Client({ name: "app", version: "1.0.0" });\\nawait client.connect(new StreamableHTTPTransport("${origin}/mcp"));\\nconst res = await client.callTool({ name: "${name}", arguments: {} });`;
      }
    }

    function copySnippetText(btn) {
      const text = document.getElementById('code-snippet-pre').innerText;
      navigator.clipboard.writeText(text).then(() => {
        const orig = btn.innerText;
        btn.innerText = "✓ Copied!";
        setTimeout(() => { btn.innerText = orig; }, 2000);
      });
    }

    async function runTool(e, name) {
      if (e) e.preventDefault();
      const tool = toolsData[toolIndex];
      const props = (tool.input_schema && tool.input_schema.properties) || {};
      const args = {};

      for (const [pname, schema] of Object.entries(props)) {
        const el = document.getElementById('in-' + pname);
        if (!el) continue;
        const val = el.value.trim();
        if (val === '') continue;
        const type = schema.type || 'string';
        if (type === 'integer') args[pname] = parseInt(val, 10);
        else if (type === 'number') args[pname] = parseFloat(val);
        else if (type === 'boolean') args[pname] = val === 'true';
        else if (type === 'object' || schema.$ref) {
          try { args[pname] = JSON.parse(val); }
          catch (err) { alert(`Invalid JSON in ${pname}: ` + err.message); return; }
        } else args[pname] = val;
      }

      const btn = document.getElementById('btn-run');
      const box = document.getElementById('output-box');
      const badge = document.getElementById('res-badge');
      const out = document.getElementById('output-text');

      btn.disabled = true;
      btn.innerText = "Executing...";
      box.style.display = "block";
      badge.className = "status-badge";
      badge.innerText = "Running...";
      out.innerText = "Calling tool...";

      const t0 = performance.now();
      try {
        const resp = await fetch(callUrl, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name: name, arguments: args })
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
        out.innerText = JSON.stringify(data, null, 2);
      } catch (err) {
        btn.disabled = false;
        btn.innerText = "⚡ Execute Tool (Ctrl+Enter)";
        badge.className = "status-badge err";
        badge.innerText = "Network Error";
        out.innerText = "Error: " + err.message;
      }
    }

    async function readResourceLive(uri) {
      const btn = document.getElementById('btn-read-res');
      const box = document.getElementById('res-output-box');
      const out = document.getElementById('res-output-text');
      btn.disabled = true;
      btn.innerText = "Reading...";
      box.style.display = "block";
      out.innerText = "Fetching resource content from server...";

      try {
        const resp = await fetch(resourceUrl + "?uri=" + encodeURIComponent(uri));
        const data = await resp.json();
        btn.disabled = false;
        btn.innerText = "⚡ Read Resource Live";
        if (data.contents && data.contents.length > 0) {
          out.innerText = data.contents.map(c => c.content).join('\\n---\\n');
        } else {
          out.innerText = JSON.stringify(data, null, 2);
        }
      } catch (err) {
        btn.disabled = false;
        btn.innerText = "⚡ Read Resource Live";
        out.innerText = "Error reading resource: " + err.message;
      }
    }

    async function renderPromptLive(e, promptName) {
      if (e) e.preventDefault();
      const prompt = promptsData[promptIndex];
      const args = {};
      for (const a of (prompt.arguments || [])) {
        const el = document.getElementById('parg-' + a.name);
        if (el && el.value.trim() !== '') {
          args[a.name] = el.value.trim();
        }
      }

      const btn = document.getElementById('btn-render-p');
      const box = document.getElementById('prompt-output-box');
      const out = document.getElementById('prompt-output-text');
      btn.disabled = true;
      btn.innerText = "Rendering...";
      box.style.display = "block";
      out.innerText = "Rendering prompt on server...";

      try {
        const resp = await fetch(promptUrl, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name: promptName, arguments: args })
        });
        const data = await resp.json();
        btn.disabled = false;
        btn.innerText = "✨ Render Prompt";
        if (data.messages) {
          out.innerText = data.messages.map(m => `[${m.role.toUpperCase()}]:\\n${m.text}`).join('\\n\\n');
        } else {
          out.innerText = JSON.stringify(data, null, 2);
        }
      } catch (err) {
        btn.disabled = false;
        btn.innerText = "✨ Render Prompt";
        out.innerText = "Error rendering prompt: " + err.message;
      }
    }

    function copyOutputText() {
      const text = document.getElementById('output-text').innerText;
      navigator.clipboard.writeText(text).then(() => alert('Output copied!'));
    }

    function copyPromptText() {
      const text = document.getElementById('prompt-output-text').innerText;
      navigator.clipboard.writeText(text).then(() => alert('Prompt copied!'));
    }

    function copyToolSchema() {
      const tool = toolsData[toolIndex];
      if (!tool) return;
      const schemaStr = JSON.stringify(tool.input_schema || {}, null, 2);
      navigator.clipboard.writeText(schemaStr).then(() => {
        alert("Tool JSON Schema copied to clipboard!");
      });
    }

    document.addEventListener('keydown', (e) => {
      if ((e.key === '/' || (e.ctrlKey && e.key.toLowerCase() === 'k')) &&
          document.activeElement.tagName !== 'INPUT' &&
          document.activeElement.tagName !== 'TEXTAREA') {
        e.preventDefault();
        const inp = document.getElementById('search-input');
        if (inp) { inp.focus(); inp.select(); }
      } else if (e.key === 'Escape') {
        const inp = document.getElementById('search-input');
        if (inp && document.activeElement === inp) {
          inp.value = '';
          filterActiveItems();
          inp.blur();
        }
      } else if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
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
