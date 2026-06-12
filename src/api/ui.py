"""Internal admin UI served at GET /ui."""

# pyrefly: ignore [missing-import]
from fastapi import APIRouter
# pyrefly: ignore [missing-import]
from fastapi.responses import HTMLResponse

router = APIRouter()

_UI_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Leadgen API — Admin</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet" />
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    :root {
      --bg:        #0d1117;
      --surface:   #161b22;
      --surface2:  #1f2937;
      --border:    #30363d;
      --accent:    #7c6fff;
      --accent-h:  #9d8fff;
      --success:   #2ea043;
      --danger:    #f85149;
      --warn:      #d29922;
      --text:      #e6edf3;
      --muted:     #8b949e;
      --radius:    10px;
    }

    body {
      font-family: 'Inter', system-ui, sans-serif;
      background: var(--bg);
      color: var(--text);
      min-height: 100vh;
      padding: 2rem 1rem 4rem;
    }

    /* ── header ── */
    header {
      text-align: center;
      margin-bottom: 2.5rem;
    }
    header h1 {
      font-size: 1.8rem;
      font-weight: 700;
      background: linear-gradient(135deg, #7c6fff 0%, #c084fc 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
    }
    header p { color: var(--muted); font-size: 0.88rem; margin-top: 0.35rem; }

    /* ── layout ── */
    .wrap { max-width: 820px; margin: 0 auto; display: flex; flex-direction: column; gap: 1.75rem; }

    .card {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 1.6rem 1.8rem;
    }

    .card-heading {
      font-size: 1rem;
      font-weight: 600;
      margin-bottom: 1.2rem;
      display: flex;
      align-items: center;
      gap: 0.45rem;
    }

    /* ── grid ── */
    .g2 { display: grid; grid-template-columns: 1fr 1fr; gap: 0.8rem; }
    .full { grid-column: 1 / -1; }

    /* ── field ── */
    .field { display: flex; flex-direction: column; gap: 0.3rem; }

    label {
      font-size: 0.74rem;
      font-weight: 500;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--muted);
    }

    input[type="text"],
    input[type="number"],
    input[type="file"],
    select {
      background: var(--surface2);
      border: 1px solid var(--border);
      border-radius: 7px;
      color: var(--text);
      font-family: inherit;
      font-size: 0.88rem;
      padding: 0.55rem 0.8rem;
      width: 100%;
      outline: none;
      transition: border-color 0.15s;
    }
    input[type="text"]:focus,
    input[type="number"]:focus,
    input[type="file"]:focus,
    select:focus { border-color: var(--accent); }

    input[type="file"] { cursor: pointer; padding: 0.45rem 0.8rem; }

    /* ── checkbox ── */
    .cbrow { display: flex; align-items: center; gap: 0.55rem; margin-top: 0.6rem; }
    .cbrow input[type="checkbox"] { width: 15px; height: 15px; accent-color: var(--accent); cursor: pointer; flex-shrink: 0; }
    .cbrow label { text-transform: none; letter-spacing: 0; font-size: 0.88rem; color: var(--text); cursor: pointer; }

    /* ── button ── */
    .btn {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 0.4rem;
      background: var(--accent);
      color: #fff;
      font-family: inherit;
      font-size: 0.88rem;
      font-weight: 600;
      padding: 0.6rem 1.4rem;
      border: none;
      border-radius: 7px;
      cursor: pointer;
      margin-top: 1rem;
      transition: background 0.15s, transform 0.08s;
      min-width: 130px;
    }
    .btn:hover { background: var(--accent-h); }
    .btn:active { transform: scale(0.97); }
    .btn:disabled { opacity: 0.5; cursor: not-allowed; }

    /* ── spinner ── */
    .spin {
      display: none;
      width: 14px;
      height: 14px;
      border: 2px solid rgba(255,255,255,0.35);
      border-top-color: #fff;
      border-radius: 50%;
      animation: rot 0.65s linear infinite;
      flex-shrink: 0;
    }
    @keyframes rot { to { transform: rotate(360deg); } }

    /* ── result boxes ── */
    .result { margin-top: 1.2rem; border-radius: 7px; overflow: hidden; display: none; }
    .result.show { display: block; }

    .result-hdr {
      padding: 0.5rem 0.9rem;
      font-size: 0.76rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.06em;
    }
    .result-hdr.ok  { background: rgba(46,160,67,0.18);  color: #3fb950; }
    .result-hdr.err { background: rgba(248,81,73,0.18);  color: #f85149; }

    pre.result-pre {
      background: var(--surface2);
      color: var(--text);
      font-size: 0.8rem;
      line-height: 1.65;
      padding: 0.9rem 1rem;
      overflow-x: auto;
      white-space: pre-wrap;
      word-break: break-word;
    }

    /* ── search results ── */
    .chunks { margin-top: 1.2rem; }

    .chunk {
      background: var(--surface2);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 0.9rem 1rem;
      margin-bottom: 0.7rem;
    }
    .chunk-title { font-weight: 600; font-size: 0.92rem; margin-bottom: 0.4rem; }
    .chunk-meta  { display: flex; flex-wrap: wrap; gap: 0.4rem 1rem; margin-bottom: 0.5rem; }
    .chunk-meta span { font-size: 0.76rem; color: var(--muted); }
    .chunk-meta strong { color: var(--text); }
    .badge {
      display: inline-block;
      background: rgba(124,111,255,0.2);
      color: var(--accent-h);
      border-radius: 20px;
      padding: 0.1rem 0.55rem;
      font-size: 0.73rem;
      font-weight: 600;
    }
    .chunk-body {
      font-size: 0.83rem;
      color: #adbac7;
      line-height: 1.6;
      max-height: 130px;
      overflow-y: auto;
    }
    .empty { color: var(--muted); font-size: 0.88rem; text-align: center; padding: 1.5rem 0; }

    @media (max-width: 580px) {
      .g2 { grid-template-columns: 1fr; }
      .card { padding: 1.1rem; }
    }
  </style>
</head>
<body>
  <header>
    <h1>⚡ Leadgen API Admin</h1>
    <p>Internal document management · upload &amp; search</p>
  </header>

  <div class="wrap">

    <!-- ════ UPLOAD ════ -->
    <div class="card">
      <div class="card-heading">📄 Upload Document</div>
      <form id="uploadForm" novalidate>
        <div class="g2">
          <div class="field full">
            <label for="u-file">PDF File *</label>
            <input type="file" id="u-file" accept=".pdf" required />
          </div>
          <div class="field full">
            <label for="u-title">Title *</label>
            <input type="text" id="u-title" placeholder="e.g. Q4 Case Study — Acme Corp" required />
          </div>
          <div class="field">
            <label for="u-type">Type</label>
            <select id="u-type">
              <option value="case">Case Study</option>
              <option value="proposal">Proposal</option>
              <option value="report">Report</option>
              <option value="other">Other</option>
            </select>
          </div>
          <div class="field">
            <label for="u-client">Client Name</label>
            <input type="text" id="u-client" placeholder="Acme Corp" />
          </div>
          <div class="field">
            <label for="u-industry">Industry</label>
            <input type="text" id="u-industry" placeholder="Technology" />
          </div>
          <div class="field">
            <label for="u-geo">Geography</label>
            <input type="text" id="u-geo" placeholder="Global" />
          </div>
          <div class="field">
            <label for="u-usecase">Use Case</label>
            <input type="text" id="u-usecase" placeholder="Lead Generation" />
          </div>
          <div class="field">
            <label for="u-tags">Tags <small style="text-transform:none">(comma-separated)</small></label>
            <input type="text" id="u-tags" placeholder="AI, Data Engineering, MLOps, RAG, CRM Integration" />
          </div>
          <div class="field full">
            <label for="u-authors">Authors <small style="text-transform:none">(comma-separated)</small></label>
            <input type="text" id="u-authors" placeholder="Alice, Bob" />
          </div>
        </div>
        <div class="cbrow">
          <input type="checkbox" id="u-process" checked />
          <label for="u-process">Process immediately (parse → chunk → embed)</label>
        </div>
        <button type="submit" class="btn" id="u-btn">
          <span class="spin" id="u-spin"></span>
          <span id="u-btn-txt">Upload &amp; Process</span>
        </button>
      </form>
      <div class="result" id="u-result">
        <div class="result-hdr" id="u-result-hdr"></div>
        <pre class="result-pre" id="u-result-body"></pre>
      </div>
    </div>

    <!-- ════ SEARCH ════ -->
    <div class="card">
      <div class="card-heading">🔍 Semantic Search</div>
      <form id="searchForm" novalidate>
        <div class="g2">
          <div class="field full">
            <label for="s-query">Query *</label>
            <input type="text" id="s-query" placeholder="What is the role of OpenClaw in the leadgen architecture?" required />
          </div>
          <div class="field">
            <label for="s-limit">Results</label>
            <input type="number" id="s-limit" value="5" min="1" max="50" />
          </div>
        </div>
        <button type="submit" class="btn" id="s-btn">
          <span class="spin" id="s-spin"></span>
          <span id="s-btn-txt">Search</span>
        </button>
      </form>
      <div class="chunks" id="s-results"></div>
    </div>

  </div><!-- /wrap -->

  <script>
    // ── helpers ──────────────────────────────────────────────────────────────
    const esc = s => (s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');

    function setLoading(btnId, spinId, txtId, on, label) {
      document.getElementById(btnId).disabled = on;
      document.getElementById(spinId).style.display = on ? 'block' : 'none';
      document.getElementById(txtId).textContent  = on ? 'Working…' : label;
    }

    function showResult(boxId, hdrId, bodyId, ok, data) {
      const box  = document.getElementById(boxId);
      const hdr  = document.getElementById(hdrId);
      const body = document.getElementById(bodyId);
      box.classList.add('show');
      hdr.className   = 'result-hdr ' + (ok ? 'ok' : 'err');
      hdr.textContent = ok ? '✓ Success' : '✗ Error';
      body.textContent = typeof data === 'string' ? data : JSON.stringify(data, null, 2);
    }

    // ── upload ────────────────────────────────────────────────────────────────
    document.getElementById('uploadForm').addEventListener('submit', async e => {
      e.preventDefault();
      const fileEl  = document.getElementById('u-file');
      const titleEl = document.getElementById('u-title');

      if (!fileEl.files.length) {
        showResult('u-result','u-result-hdr','u-result-body', false, 'Please select a PDF file.');
        return;
      }
      if (!titleEl.value.trim()) {
        showResult('u-result','u-result-hdr','u-result-body', false, 'Please enter a document title.');
        return;
      }

      setLoading('u-btn','u-spin','u-btn-txt', true, 'Upload & Process');
      try {
        const fd = new FormData();
        fd.append('file',              fileEl.files[0]);
        fd.append('title',             titleEl.value.trim());
        fd.append('type',              document.getElementById('u-type').value);
        fd.append('client_name',       document.getElementById('u-client').value.trim());
        fd.append('industry',          document.getElementById('u-industry').value.trim());
        fd.append('geography',         document.getElementById('u-geo').value.trim());
        fd.append('use_case',          document.getElementById('u-usecase').value.trim());
        fd.append('tags',              document.getElementById('u-tags').value.trim());
        fd.append('authors',           document.getElementById('u-authors').value.trim());
        fd.append('process_immediately', document.getElementById('u-process').checked ? 'true' : 'false');

        const resp = await fetch('/api/v1/documents/upload', { method: 'POST', body: fd });
        const data = await resp.json();
        showResult('u-result','u-result-hdr','u-result-body', resp.ok, data);
      } catch(err) {
        showResult('u-result','u-result-hdr','u-result-body', false, 'Network error: ' + err.message);
      } finally {
        setLoading('u-btn','u-spin','u-btn-txt', false, 'Upload & Process');
      }
    });

    // ── search ────────────────────────────────────────────────────────────────
    document.getElementById('searchForm').addEventListener('submit', async e => {
      e.preventDefault();
      const query = document.getElementById('s-query').value.trim();
      if (!query) return;

      setLoading('s-btn','s-spin','s-btn-txt', true, 'Search');
      const container = document.getElementById('s-results');
      container.innerHTML = '';

      try {
        const resp = await fetch('/api/v1/documents/search', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            query,
            limit: parseInt(document.getElementById('s-limit').value, 10) || 5,
          }),
        });
        const data = await resp.json();

        if (!resp.ok) {
          container.innerHTML = `<div class="empty" style="color:var(--danger)">${esc(data.detail || JSON.stringify(data))}</div>`;
          return;
        }

        const results = data.results || [];
        if (!results.length) {
          container.innerHTML = '<div class="empty">No matching chunks found.</div>';
          return;
        }

        results.forEach(r => {
          const c = document.createElement('div');
          c.className = 'chunk';
          c.innerHTML = `
            <div class="chunk-title">${esc(r.title)}</div>
            <div class="chunk-meta">
              <span><strong>File:</strong> ${esc(r.source_object_key)}</span>
              <span><strong>Chunk:</strong> #${r.chunk_index}</span>
              <span class="badge">Score: ${(r.score * 100).toFixed(1)}%</span>
              ${r.client_name ? `<span><strong>Client:</strong> ${esc(r.client_name)}</span>` : ''}
              ${r.type        ? `<span><strong>Type:</strong> ${esc(r.type)}</span>`        : ''}
              ${r.industry    ? `<span><strong>Industry:</strong> ${esc(r.industry)}</span>` : ''}
            </div>
            <div class="chunk-body">${esc(r.content)}</div>
          `;
          container.appendChild(c);
        });
      } catch(err) {
        container.innerHTML = `<div class="empty" style="color:var(--danger)">Network error: ${esc(err.message)}</div>`;
      } finally {
        setLoading('s-btn','s-spin','s-btn-txt', false, 'Search');
      }
    });
  </script>
</body>
</html>"""


@router.get("/ui", response_class=HTMLResponse, include_in_schema=False)
async def admin_ui():
    """Internal admin UI — document upload and semantic search."""
    return HTMLResponse(content=_UI_HTML, status_code=200)
