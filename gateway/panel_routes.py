"""
Gateway Panel Blueprint — serves the channel management + memory UI.

Routes
------
GET  /gateway/panel           — Main panel HTML page
GET  /api/gateway/panel/data  — Aggregate data (channels + sessions + memory stats)
"""

from flask import Blueprint, current_app, jsonify, render_template_string

panel_bp = Blueprint("gateway_panel", __name__)

# ---------------------------------------------------------------------------
# Aggregate data endpoint
# ---------------------------------------------------------------------------

@panel_bp.route("/data", methods=["GET"])
def panel_data():
    """Return channels, sessions, and memory stats for the panel UI."""
    # Channel registry
    registry = current_app.config.get("GATEWAY_CHANNEL_REGISTRY")
    channels = registry.list_channels() if registry else []

    # Sessions
    sm = current_app.config.get("GATEWAY_SESSION_MANAGER")
    if sm is None:
        from services.agent_session_service import session_manager  # type: ignore
        sm = session_manager
    sessions = sm.list_sessions()

    # Memory stats
    mem_store = current_app.config.get("GATEWAY_MEMORY_STORE")
    mem_stats = mem_store.stats() if mem_store is not None else {"document_count": 0, "folder_count": 0}

    return jsonify({
        "channels": channels,
        "sessions": sessions,
        "memory": mem_stats,
    })


# ---------------------------------------------------------------------------
# Panel HTML
# ---------------------------------------------------------------------------

_PANEL_HTML = """<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>OmicVerse Gateway</title>
<style>
  :root {
    --bg: #0f1117; --surface: #1a1d27; --border: #2a2d3d;
    --text: #e2e8f0; --muted: #718096; --accent: #6366f1;
    --green: #10b981; --yellow: #f59e0b; --red: #ef4444;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: var(--bg); color: var(--text); font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; font-size: 14px; }
  .layout { display: grid; grid-template-columns: 220px 1fr; min-height: 100vh; }
  .sidebar { background: var(--surface); border-right: 1px solid var(--border); padding: 20px 0; }
  .sidebar-logo { padding: 0 20px 20px; font-weight: 700; font-size: 16px; color: var(--accent); border-bottom: 1px solid var(--border); margin-bottom: 12px; }
  .sidebar-logo span { color: var(--muted); font-size: 11px; display: block; font-weight: 400; margin-top: 2px; }
  .nav-item { padding: 9px 20px; cursor: pointer; color: var(--muted); transition: all .15s; display: flex; align-items: center; gap: 8px; }
  .nav-item:hover, .nav-item.active { color: var(--text); background: rgba(99,102,241,.1); }
  .nav-item.active { border-left: 2px solid var(--accent); }
  .main { padding: 28px; overflow: auto; }
  .page { display: none; } .page.active { display: block; }
  h2 { font-size: 18px; font-weight: 600; margin-bottom: 20px; }
  .cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 14px; margin-bottom: 28px; }
  .card { background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 18px; }
  .card-label { color: var(--muted); font-size: 12px; margin-bottom: 6px; }
  .card-value { font-size: 26px; font-weight: 700; }
  .card-value.green { color: var(--green); } .card-value.accent { color: var(--accent); } .card-value.yellow { color: var(--yellow); }
  table { width: 100%; border-collapse: collapse; background: var(--surface); border-radius: 10px; overflow: hidden; }
  th { text-align: left; padding: 10px 14px; color: var(--muted); font-size: 12px; font-weight: 500; border-bottom: 1px solid var(--border); }
  td { padding: 10px 14px; border-bottom: 1px solid var(--border); font-size: 13px; }
  tr:last-child td { border-bottom: none; }
  .badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 500; }
  .badge-green { background: rgba(16,185,129,.15); color: var(--green); }
  .badge-yellow { background: rgba(245,158,11,.15); color: var(--yellow); }
  .badge-blue { background: rgba(99,102,241,.15); color: var(--accent); }
  .search-bar { display: flex; gap: 8px; margin-bottom: 16px; }
  .search-bar input { flex: 1; background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 8px 12px; color: var(--text); font-size: 13px; outline: none; }
  .search-bar input:focus { border-color: var(--accent); }
  .btn { background: var(--accent); color: #fff; border: none; border-radius: 8px; padding: 8px 16px; cursor: pointer; font-size: 13px; }
  .btn:hover { opacity: .85; }
  .btn-sm { padding: 4px 10px; font-size: 12px; }
  .btn-danger { background: var(--red); }
  .doc-content { white-space: pre-wrap; background: var(--bg); border: 1px solid var(--border); border-radius: 6px; padding: 12px; font-family: monospace; font-size: 12px; max-height: 200px; overflow-y: auto; margin-top: 8px; }
  .modal-overlay { display: none; position: fixed; inset: 0; background: rgba(0,0,0,.6); z-index: 100; align-items: center; justify-content: center; }
  .modal-overlay.open { display: flex; }
  .modal { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 24px; width: 520px; max-width: 95vw; }
  .modal h3 { margin-bottom: 16px; }
  .form-group { margin-bottom: 12px; }
  .form-group label { display: block; color: var(--muted); font-size: 12px; margin-bottom: 4px; }
  .form-group input, .form-group textarea { width: 100%; background: var(--bg); border: 1px solid var(--border); border-radius: 6px; padding: 8px 10px; color: var(--text); font-size: 13px; outline: none; }
  .form-group textarea { height: 120px; resize: vertical; font-family: monospace; }
  .form-group input:focus, .form-group textarea:focus { border-color: var(--accent); }
  .modal-actions { display: flex; gap: 8px; justify-content: flex-end; margin-top: 16px; }
  .btn-ghost { background: transparent; border: 1px solid var(--border); color: var(--text); }
  .snippet mark, .snippet strong { background: rgba(99,102,241,.25); color: var(--accent); border-radius: 2px; }
  #search-results .result-item { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 14px; margin-bottom: 10px; }
  #search-results .result-title { font-weight: 600; margin-bottom: 4px; }
  #search-results .result-meta { font-size: 11px; color: var(--muted); margin-bottom: 6px; }
  .tag { display: inline-block; background: rgba(99,102,241,.12); color: var(--accent); border-radius: 4px; padding: 1px 6px; font-size: 11px; margin-right: 4px; }
  .empty { color: var(--muted); text-align: center; padding: 40px; }
  .refresh-btn { float: right; font-size: 12px; color: var(--muted); cursor: pointer; margin-top: 4px; }
  .refresh-btn:hover { color: var(--text); }
</style>
</head>
<body>
<div class="layout">
  <!-- Sidebar -->
  <nav class="sidebar">
    <div class="sidebar-logo">⬡ OmicVerse Gateway<span>Channel Control Panel</span></div>
    <div class="nav-item active" onclick="showPage('overview')">📊 Overview</div>
    <div class="nav-item" onclick="showPage('channels')">📡 Channels</div>
    <div class="nav-item" onclick="showPage('sessions')">💬 Sessions</div>
    <div class="nav-item" onclick="showPage('memory')">🧠 Memory</div>
  </nav>

  <!-- Main -->
  <main class="main">

    <!-- Overview -->
    <div id="page-overview" class="page active">
      <h2>Gateway Overview <span class="refresh-btn" onclick="loadAll()">↻ refresh</span></h2>
      <div class="cards">
        <div class="card"><div class="card-label">Active Channels</div><div class="card-value green" id="ov-channels">—</div></div>
        <div class="card"><div class="card-label">Sessions</div><div class="card-value accent" id="ov-sessions">—</div></div>
        <div class="card"><div class="card-label">Memory Documents</div><div class="card-value yellow" id="ov-docs">—</div></div>
        <div class="card"><div class="card-label">Memory Folders</div><div class="card-value" id="ov-folders">—</div></div>
      </div>
      <h2 style="margin-top:8px">Recent Sessions</h2>
      <table id="ov-sessions-table">
        <thead><tr><th>Session ID</th><th>Channel</th><th>Messages</th><th>Has Data</th><th>Last Active</th></tr></thead>
        <tbody></tbody>
      </table>
    </div>

    <!-- Channels -->
    <div id="page-channels" class="page">
      <h2>Connected Channels</h2>
      <table id="channels-table">
        <thead><tr><th>Channel</th><th>Scope Type</th><th>Scope ID</th><th>Session ID</th></tr></thead>
        <tbody></tbody>
      </table>
    </div>

    <!-- Sessions -->
    <div id="page-sessions" class="page">
      <h2>Active Sessions</h2>
      <table id="sessions-table">
        <thead><tr><th>Session ID</th><th>Messages</th><th>Has Data</th><th>Tasks</th><th>Active Turn</th><th>Last Active</th><th></th></tr></thead>
        <tbody></tbody>
      </table>
    </div>

    <!-- Memory -->
    <div id="page-memory" class="page">
      <h2>Memory Store <button class="btn btn-sm" onclick="openNewDoc()" style="margin-left:10px">+ New</button></h2>
      <div class="search-bar">
        <input id="mem-search" placeholder="Search memories…" onkeydown="if(event.key==='Enter')searchMemory()">
        <button class="btn" onclick="searchMemory()">Search</button>
      </div>
      <div id="search-results"></div>
      <div id="mem-doc-list"></div>
    </div>

  </main>
</div>

<!-- New/Edit Document Modal -->
<div class="modal-overlay" id="doc-modal">
  <div class="modal">
    <h3 id="modal-title">New Memory</h3>
    <div class="form-group"><label>Title</label><input id="doc-title" placeholder="Analysis title…"></div>
    <div class="form-group"><label>Content (Markdown)</label><textarea id="doc-content" placeholder="Write your memory here…"></textarea></div>
    <div class="form-group"><label>Tags (comma-separated)</label><input id="doc-tags" placeholder="umap, pbmc, clustering"></div>
    <div class="modal-actions">
      <button class="btn btn-ghost" onclick="closeModal()">Cancel</button>
      <button class="btn" onclick="saveDoc()">Save</button>
    </div>
  </div>
</div>

<script>
let _data = {channels:[], sessions:[], memory:{document_count:0, folder_count:0}};
let _allDocs = [];
let _editingDocId = null;

async function api(path, opts={}) {
  const r = await fetch(path, {headers:{'Content-Type':'application/json'}, ...opts});
  return r.json();
}

async function loadAll() {
  const d = await api('/api/gateway/panel/data');
  _data = d;
  renderOverview();
  renderChannels();
  renderSessions();
  await loadDocs();
}

function renderOverview() {
  document.getElementById('ov-channels').textContent = _data.channels.length;
  document.getElementById('ov-sessions').textContent = _data.sessions.length;
  document.getElementById('ov-docs').textContent = _data.memory.document_count;
  document.getElementById('ov-folders').textContent = _data.memory.folder_count;
  const tbody = document.querySelector('#ov-sessions-table tbody');
  tbody.innerHTML = _data.sessions.slice(0,10).map(s => `
    <tr>
      <td><code style="font-size:11px">${s.session_id}</code></td>
      <td>${(s.channel_info||{}).channel ? '<span class="badge badge-blue">'+s.channel_info.channel+'</span>' : '<span class="badge badge-green">web</span>'}</td>
      <td>${s.message_count}</td>
      <td>${s.has_adata ? '<span class="badge badge-yellow">yes</span>' : '—'}</td>
      <td style="color:var(--muted);font-size:12px">${timeAgo(s.last_active)}</td>
    </tr>`).join('') || '<tr><td colspan="5" class="empty">No sessions yet</td></tr>';
}

function renderChannels() {
  const tbody = document.querySelector('#channels-table tbody');
  tbody.innerHTML = _data.channels.map(c => `
    <tr>
      <td><span class="badge badge-blue">${c.channel}</span></td>
      <td>${c.scope_type}</td>
      <td><code>${c.scope_id}</code></td>
      <td><code style="font-size:11px">${c.session_id}</code></td>
    </tr>`).join('') || '<tr><td colspan="4" class="empty">No channels connected</td></tr>';
}

function renderSessions() {
  const tbody = document.querySelector('#sessions-table tbody');
  tbody.innerHTML = _data.sessions.map(s => `
    <tr>
      <td><code style="font-size:11px">${s.session_id}</code></td>
      <td>${s.message_count}</td>
      <td>${s.has_adata ? '<span class="badge badge-yellow">yes</span>' : '—'}</td>
      <td>${s.task_count}</td>
      <td>${s.active_turn_id ? '<span class="badge badge-green">running</span>' : '—'}</td>
      <td style="color:var(--muted);font-size:12px">${timeAgo(s.last_active)}</td>
      <td><button class="btn btn-sm btn-danger" onclick="deleteSession('${s.session_id}')">✕</button></td>
    </tr>`).join('') || '<tr><td colspan="7" class="empty">No sessions yet</td></tr>';
}

async function deleteSession(sid) {
  if (!confirm('Delete session ' + sid + '?')) return;
  await api('/api/gateway/sessions/' + sid, {method:'DELETE'});
  loadAll();
}

async function loadDocs() {
  const d = await api('/api/gateway/memory/documents?limit=50');
  _allDocs = d.documents || [];
  renderDocs(_allDocs);
}

function renderDocs(docs) {
  const el = document.getElementById('mem-doc-list');
  if (!docs.length) { el.innerHTML = '<div class="empty">No memories yet. Create one with "+ New".</div>'; return; }
  el.innerHTML = docs.map(d => `
    <div class="result-item" style="background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:14px;margin-bottom:10px">
      <div style="display:flex;justify-content:space-between;align-items:flex-start">
        <div>
          <div style="font-weight:600;margin-bottom:3px">${esc(d.title)}</div>
          <div style="font-size:11px;color:var(--muted);margin-bottom:6px">
            ${d.folder_path} · ${d.channel ? '<span class="badge badge-blue">'+d.channel+'</span>' : ''} · ${timeAgo(d.updated_at)}
          </div>
          <div>${(d.tags||[]).map(t=>'<span class="tag">'+esc(t)+'</span>').join('')}</div>
        </div>
        <div style="display:flex;gap:6px;flex-shrink:0;margin-left:12px">
          <button class="btn btn-sm" onclick="editDoc('${d.id}')">Edit</button>
          <button class="btn btn-sm btn-danger" onclick="deleteDoc('${d.id}')">Del</button>
        </div>
      </div>
      <div class="doc-content">${esc(d.content).slice(0,400)}${d.content.length>400?'…':''}</div>
    </div>`).join('');
}

async function searchMemory() {
  const q = document.getElementById('mem-search').value.trim();
  if (!q) { renderDocs(_allDocs); document.getElementById('search-results').innerHTML=''; return; }
  const d = await api('/api/gateway/memory/search?q=' + encodeURIComponent(q));
  const results = d.results || [];
  document.getElementById('search-results').innerHTML = results.length
    ? results.map(r => `
      <div class="result-item">
        <div class="result-title">${esc(r.title)}</div>
        <div class="result-meta">${r.folder_path} · ${r.channel ? '<span class="badge badge-blue">'+r.channel+'</span>' : ''} · ${timeAgo(r.updated_at)}</div>
        <div>${(r.tags||[]).map(t=>'<span class="tag">'+esc(t)+'</span>').join('')}</div>
        <div class="doc-content snippet">${r.snippet.replace(/\*\*(.*?)\*\*/g,'<strong>$1</strong>')}</div>
      </div>`).join('')
    : '<div class="empty">No results for "' + esc(q) + '"</div>';
  document.getElementById('mem-doc-list').innerHTML = '';
}

function openNewDoc() {
  _editingDocId = null;
  document.getElementById('modal-title').textContent = 'New Memory';
  document.getElementById('doc-title').value = '';
  document.getElementById('doc-content').value = '';
  document.getElementById('doc-tags').value = '';
  document.getElementById('doc-modal').classList.add('open');
}

function editDoc(id) {
  const d = _allDocs.find(x => x.id === id);
  if (!d) return;
  _editingDocId = id;
  document.getElementById('modal-title').textContent = 'Edit Memory';
  document.getElementById('doc-title').value = d.title;
  document.getElementById('doc-content').value = d.content;
  document.getElementById('doc-tags').value = (d.tags||[]).join(', ');
  document.getElementById('doc-modal').classList.add('open');
}

function closeModal() { document.getElementById('doc-modal').classList.remove('open'); }

async function saveDoc() {
  const title = document.getElementById('doc-title').value.trim();
  const content = document.getElementById('doc-content').value;
  const tags = document.getElementById('doc-tags').value.split(',').map(t=>t.trim()).filter(Boolean);
  if (!title) { alert('Title is required'); return; }
  if (_editingDocId) {
    await api('/api/gateway/memory/documents/' + _editingDocId, {method:'PUT', body:JSON.stringify({title, content, tags})});
  } else {
    await api('/api/gateway/memory/documents', {method:'POST', body:JSON.stringify({title, content, tags, channel:'web'})});
  }
  closeModal();
  await loadDocs();
}

async function deleteDoc(id) {
  if (!confirm('Delete this memory?')) return;
  await api('/api/gateway/memory/documents/' + id, {method:'DELETE'});
  loadDocs();
}

function showPage(name) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  document.getElementById('page-' + name).classList.add('active');
  event.currentTarget.classList.add('active');
}

function timeAgo(ts) {
  if (!ts) return '—';
  const s = Math.floor(Date.now()/1000 - ts);
  if (s < 60) return s + 's ago';
  if (s < 3600) return Math.floor(s/60) + 'm ago';
  if (s < 86400) return Math.floor(s/3600) + 'h ago';
  return Math.floor(s/86400) + 'd ago';
}

function esc(s) {
  return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

loadAll();
setInterval(loadAll, 15000);
</script>
</body>
</html>"""


@panel_bp.route("")
@panel_bp.route("/")
def gateway_panel():
    return render_template_string(_PANEL_HTML)
