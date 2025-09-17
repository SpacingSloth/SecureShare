
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["UI"])

@router.get("/ui", response_class=HTMLResponse)
async def ui_home():
    html = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>SecureShare — Files</title>
  <style>
    :root { --bg:#0b0d10; --card:#151a20; --fg:#e7edf3; --muted:#9fb0c3; --btn:#2a7cff; --chip:#2b3340; }
    html,body { height:100%; }
    body { margin:0; background:var(--bg); color:var(--fg); font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial; }
    .wrap { max-width:960px; margin:0 auto; padding:28px 16px; }
    h1 { font-size:22px; margin:0 0 12px; }
    .card { background:var(--card); border-radius:18px; padding:18px; box-shadow:0 10px 30px rgba(0,0,0,.25); }
    .row { display:flex; gap:12px; align-items:center; flex-wrap:wrap; }
    input[type=text] { background:#0f1318; color:var(--fg); border:1px solid #222a33; border-radius:10px; padding:10px 12px; min-width:260px; }
    button, .btn { background:var(--btn); color:white; border:0; border-radius:10px; padding:10px 14px; cursor:pointer; font-weight:600; text-decoration:none; display:inline-block; }
    button.secondary, .chip { background:var(--chip); color:#d7e1ea; }
    table { width:100%; border-collapse: collapse; margin-top:14px; }
    th, td { text-align:left; padding:10px 8px; border-bottom:1px solid #24303d; vertical-align: top; }
    code { background:#0f1318; padding:2px 6px; border-radius:6px; }
    .muted { color:var(--muted); }
    .small { font-size:12px; }
    .mono { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace; }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="row" style="justify-content: space-between;">
      <h1>SecureShare — Your Files</h1>
      <div class="row">
        <input id="token" type="text" placeholder="Paste API token (JWT)" />
        <button onclick="saveToken()">Set token</button>
        <button class="secondary" onclick="clearToken()">Log out</button>
      </div>
    </div>

    <div class="card" style="margin-top:14px;">
      <div class="row">
        <button onclick="loadFiles()">Reload files</button>
        <span id="status" class="muted small">Paste token and click "Set token" to load files.</span>
      </div>
      <div id="list"></div>
    </div>
  </div>

<script>
const api = {
  listFiles: () => fetch('/files', { headers: authHeaders() }),
  createShare: (fileId) => fetch(`/share-links/create?file_id=${encodeURIComponent(fileId)}`, {
      method: 'POST', headers: authHeaders()
  }),
};

function authHeaders() {
  const t = localStorage.getItem('secureshare_token');
  return t ? { 'Authorization': 'Bearer ' + t } : {};
}

function saveToken() {
  const t = document.getElementById('token').value.trim();
  if (!t) return;
  localStorage.setItem('secureshare_token', t);
  document.getElementById('status').textContent = 'Token saved to this browser (localStorage).';
  loadFiles();
}
function clearToken() {
  localStorage.removeItem('secureshare_token');
  document.getElementById('status').textContent = 'Token cleared.';
  document.getElementById('list').innerHTML = '';
}

function fmtBytes(n) {
  if (!n && n !== 0) return '—';
  const units = ['B','KB','MB','GB','TB'];
  let p = n === 0 ? 0 : Math.min(Math.floor(Math.log(n)/Math.log(1024)), units.length-1);
  return (n/Math.pow(1024,p)).toFixed(2) + ' ' + units[p];
}

async function loadFiles() {
  const resp = await api.listFiles();
  if (!resp.ok) {
    document.getElementById('status').textContent = 'Failed to load files: ' + resp.status + ' ' + (await resp.text());
    return;
  }

  const files = await resp.json();
  document.getElementById('status').textContent = files.length + ' file(s)';
  const rows = files.map(f => `
    <tr>
      <td class="mono small">${f.id}</td>
      <td><div>${f.filename || '—'}</div>
          <div class="muted small">${f.content_type || ''}</div></td>
      <td>${fmtBytes(f.size)}</td>
      <td class="small">${f.expires_at || ''}</td>
      <td>
        <button onclick="share('${f.id}')">Get share link</button>
        <div id="share-${f.id}" class="small muted" style="margin-top:6px;"></div>
      </td>
    </tr>`).join('');

  document.getElementById('list').innerHTML = `
    <table>
      <thead><tr><th>ID</th><th>Name</th><th>Size</th><th>Expires</th><th>Actions</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>`;
}

async function share(fileId) {
  const box = document.getElementById('share-'+fileId);
  box.textContent = 'Creating…';
  const resp = await api.createShare(fileId);
  if (!resp.ok) {
    box.textContent = 'Error: ' + resp.status + ' ' + (await resp.text());
    return;
  }
  const data = await resp.json();
  const url = data.share_url;
  box.innerHTML = \`
    <div>URL: <a class="mono" href="\${url}" target="_blank" rel="noopener">\${url}</a></div>
    <div class="row" style="margin-top:6px;">
      <button class="secondary" onclick="copy('\${url}')">Copy</button>
      <a class="btn" href="\${url}">Open</a>
    </div>
  \`;
}

async function copy(text) {
  try { await navigator.clipboard.writeText(text); }
  catch (e) {
    const ta = document.createElement('textarea');
    ta.value = text;
    document.body.appendChild(ta);
    ta.select();
    document.execCommand('copy');
    document.body.removeChild(ta);
  }
}
</script>
</body>
</html>"""
    return HTMLResponse(html, headers={"Cache-Control": "no-store"})
