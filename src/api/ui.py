"""Internal admin UI served at GET /ui."""

from fastapi import APIRouter, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
import json
import urllib.parse
from typing import Optional
from src.config import settings

router = APIRouter()

_LOGIN_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Knowledge Base API — Login</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700&family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap" rel="stylesheet" />
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    :root {
      --bg:            #080b10;
      --surface:       #101520;
      --border:        #263345;
      --accent:        #6366f1;
      --accent-h:      #4f46e5;
      --text:          #f3f4f6;
      --muted:         #9ca3af;
      --radius:        14px;
      --radius-sm:     8px;
    }
    body {
      font-family: 'Plus Jakarta Sans', system-ui, sans-serif;
      background: var(--bg);
      color: var(--text);
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 1.5rem;
      background-image: 
        radial-gradient(at 0% 0%, rgba(99, 102, 241, 0.08) 0px, transparent 50%),
        radial-gradient(at 100% 100%, rgba(79, 70, 229, 0.05) 0px, transparent 50%);
      background-attachment: fixed;
    }
    .login-card {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 3rem 2.5rem;
      width: 100%;
      max-width: 420px;
      text-align: center;
      box-shadow: 0 20px 40px -15px rgba(0, 0, 0, 0.85);
    }
    .brand h1 {
      font-family: 'Outfit', sans-serif;
      font-size: 2rem;
      font-weight: 700;
      background: linear-gradient(135deg, #a5b4fc 0%, #6366f1 50%, #4338ca 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
      letter-spacing: -0.02em;
      margin-bottom: 0.5rem;
    }
    .brand p { 
      color: var(--muted); 
      font-size: 0.95rem;
      margin-bottom: 2rem;
    }
    .btn-ms {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 0.75rem;
      background: #2f2f2f;
      color: white;
      text-decoration: none;
      padding: 0.75rem 1rem;
      border: 1px solid #555;
      border-radius: var(--radius-sm);
      font-weight: 600;
      font-size: 0.95rem;
      transition: all 0.2s ease;
      width: 100%;
    }
    .btn-ms:hover {
      background: #3f3f3f;
      border-color: #666;
    }
    .btn-ms:focus-visible {
      outline: 2px solid var(--accent);
      outline-offset: 2px;
    }
    .btn-text {
      display: flex;
      flex-direction: column;
      align-items: flex-start;
    }
    .btn-text span:first-child {
      font-size: 0.95rem;
    }
    .btn-text span:last-child {
      font-size: 0.75rem;
      font-weight: 400;
      color: #aaa;
    }
    .message {
      margin-bottom: 1.5rem;
      padding: 0.75rem;
      border-radius: var(--radius-sm);
      font-size: 0.9rem;
      line-height: 1.4;
    }
    .message.error {
      background: rgba(239, 68, 68, 0.1);
      color: #fca5a5;
      border: 1px solid rgba(239, 68, 68, 0.2);
    }
    .message.success {
      background: rgba(16, 185, 129, 0.1);
      color: #6ee7b7;
      border: 1px solid rgba(16, 185, 129, 0.2);
    }
  </style>
</head>
<body>
  <div class="login-card">
    <div class="brand">
      <h1>Leadgen Assistant</h1>
      <p>Knowledge Base API Console</p>
    </div>
    {message_html}
    <a href="{auth_url}" class="btn-ms">
      <svg xmlns="http://www.w3.org/2000/svg" width="21" height="21" viewBox="0 0 21 21">
        <rect x="1" y="1" width="9" height="9" fill="#f25022"/>
        <rect x="11" y="1" width="9" height="9" fill="#7fba00"/>
        <rect x="1" y="11" width="9" height="9" fill="#00a4ef"/>
        <rect x="11" y="11" width="9" height="9" fill="#ffb900"/>
      </svg>
      <div class="btn-text">
        <span>Sign in with Microsoft</span>
        <span>Use your work or school account</span>
      </div>
    </a>
  </div>
</body>
</html>"""

_UI_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Knowledge Base API — Admin Console</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700&family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap" rel="stylesheet" />
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    :root {
      --bg:            #080b10;
      --surface:       #101520;
      --surface2:      #182030;
      --border:        #263345;
      --border-glow:   #3d516d;
      --accent:        #6366f1;
      --accent-glow:   rgba(99, 102, 241, 0.15);
      --accent-h:      #4f46e5;
      --success:       #10b981;
      --success-glow:  rgba(16, 185, 129, 0.15);
      --danger:        #ef4444;
      --danger-glow:   rgba(239, 68, 68, 0.15);
      --warn:          #f59e0b;
      --warn-glow:     rgba(245, 158, 11, 0.15);
      --text:          #f3f4f6;
      --muted:         #9ca3af;
      --radius:        14px;
      --radius-sm:     8px;
      --shadow:        0 10px 30px -10px rgba(0, 0, 0, 0.7);
      --shadow-lg:     0 20px 40px -15px rgba(0, 0, 0, 0.85);
    }

    body {
      font-family: 'Plus Jakarta Sans', system-ui, sans-serif;
      background: var(--bg);
      color: var(--text);
      min-height: 100vh;
      padding: 2.5rem 1.5rem 4rem;
      background-image: 
        radial-gradient(at 0% 0%, rgba(99, 102, 241, 0.08) 0px, transparent 50%),
        radial-gradient(at 100% 100%, rgba(79, 70, 229, 0.05) 0px, transparent 50%);
      background-attachment: fixed;
    }

    /* ── Header ── */
    header {
      max-width: 1200px;
      margin: 0 auto 3rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 1.5rem;
      border-bottom: 1px solid var(--border);
      padding-bottom: 1.5rem;
    }
    header .brand h1 {
      font-family: 'Outfit', sans-serif;
      font-size: 2.2rem;
      font-weight: 700;
      background: linear-gradient(135deg, #a5b4fc 0%, #6366f1 50%, #4338ca 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
      letter-spacing: -0.02em;
    }
    header .brand p { 
      color: var(--muted); 
      font-size: 0.95rem; 
      margin-top: 0.25rem; 
    }

    /* ── User Profile ── */
    .user-profile {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      background: var(--surface2);
      padding: 0.4rem 0.6rem;
      border-radius: var(--radius-sm);
      border: 1px solid var(--border);
    }
    .user-avatar {
      width: 32px;
      height: 32px;
      border-radius: 50%;
      background: linear-gradient(135deg, #6366f1, #4338ca);
      color: white;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 600;
      font-size: 0.85rem;
      flex-shrink: 0;
    }
    .user-info {
      display: flex;
      flex-direction: column;
      max-width: 130px;
    }
    .user-name {
      font-size: 0.82rem;
      font-weight: 600;
      color: var(--text);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .user-email {
      font-size: 0.7rem;
      color: var(--muted);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .btn-signout {
      background: transparent;
      border: none;
      color: #f87171;
      font-size: 0.75rem;
      font-weight: 600;
      cursor: pointer;
      padding: 0.4rem 0.6rem;
      border-left: 1px solid var(--border);
      transition: color 0.15s;
    }
    .btn-signout:hover {
      color: #ef4444;
      text-decoration: underline;
    }
    .btn-signout:focus-visible {
      outline: 2px solid var(--accent);
      outline-offset: 2px;
      border-radius: 4px;
    }

    /* ── Layout ── */
    .wrap { 
      max-width: 1200px; 
      margin: 0 auto; 
      display: grid;
      grid-template-columns: 1fr;
      gap: 2rem; 
    }

    @media (min-width: 1024px) {
      .wrap {
        grid-template-columns: 2fr 1fr;
      }
      .span-all {
        grid-column: span 2;
      }
    }

    .card {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 1.8rem 2rem;
      box-shadow: var(--shadow);
      position: relative;
      overflow: hidden;
    }

    .card::before {
      content: '';
      position: absolute;
      top: 0; left: 0; right: 0;
      height: 3px;
      background: linear-gradient(90deg, transparent, var(--border-glow), transparent);
    }

    .card-heading {
      font-family: 'Outfit', sans-serif;
      font-size: 1.25rem;
      font-weight: 600;
      margin-bottom: 1.5rem;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 0.5rem;
      letter-spacing: -0.01em;
    }

    /* ── Warning Banner ── */
    .warning-banner {
      background: rgba(245, 158, 11, 0.08);
      border: 1px solid rgba(245, 158, 11, 0.25);
      border-radius: var(--radius-sm);
      padding: 0.8rem 1rem;
      font-size: 0.83rem;
      color: #fbbf24;
      line-height: 1.5;
      margin-bottom: 1.2rem;
      display: flex;
      align-items: flex-start;
      gap: 0.65rem;
    }
    .warning-banner svg {
      width: 18px;
      height: 18px;
      flex-shrink: 0;
      margin-top: 2px;
    }

    /* ── Table Styles ── */
    .table-container {
      overflow-x: auto;
      margin-top: 0.5rem;
      border-radius: var(--radius-sm);
      border: 1px solid var(--border);
    }

    table {
      width: 100%;
      border-collapse: collapse;
      text-align: left;
      font-size: 0.88rem;
    }

    th, td {
      padding: 0.9rem 1.1rem;
      border-bottom: 1px solid var(--border);
    }

    th {
      background: var(--surface2);
      color: var(--muted);
      font-weight: 600;
      text-transform: uppercase;
      font-size: 0.73rem;
      letter-spacing: 0.05em;
    }

    tr:last-child td {
      border-bottom: none;
    }

    tr:hover td {
      background: rgba(24, 32, 48, 0.3);
    }

    /* ── Badges ── */
    .badge-status {
      display: inline-flex;
      align-items: center;
      gap: 0.35rem;
      font-size: 0.75rem;
      font-weight: 600;
      text-transform: uppercase;
      padding: 0.2rem 0.6rem;
      border-radius: 20px;
      letter-spacing: 0.02em;
    }
    .badge-status.processed {
      background: var(--success-glow);
      color: var(--success);
      border: 1px solid rgba(16, 185, 129, 0.2);
    }
    .badge-status.uploaded {
      background: var(--accent-glow);
      color: var(--text);
      border: 1px solid rgba(99, 102, 241, 0.2);
    }
    .badge-status.processing {
      background: var(--warn-glow);
      color: var(--warn);
      border: 1px solid rgba(245, 158, 11, 0.2);
      animation: pulse 1.8s infinite ease-in-out;
    }
    .badge-status.failed {
      background: var(--danger-glow);
      color: var(--danger);
      border: 1px solid rgba(239, 68, 68, 0.2);
    }
    .badge-status.archived {
      background: rgba(156, 163, 175, 0.1);
      color: var(--muted);
      border: 1px solid rgba(156, 163, 175, 0.2);
    }

    .badge-searchable {
      display: inline-flex;
      align-items: center;
      gap: 0.25rem;
      font-size: 0.7rem;
      font-weight: 700;
      padding: 0.1rem 0.4rem;
      border-radius: 4px;
      margin-left: 0.5rem;
    }
    .badge-searchable.yes {
      background: rgba(16, 185, 129, 0.15);
      color: var(--success);
    }
    .badge-searchable.no {
      background: rgba(156, 163, 175, 0.15);
      color: var(--muted);
    }

    @keyframes pulse {
      0% { opacity: 0.6; }
      50% { opacity: 1; }
      100% { opacity: 0.6; }
    }

    /* ── Form Fields ── */
    .g2 { display: grid; grid-template-columns: 1fr; gap: 1rem; }
    @media (min-width: 640px) {
      .g2 { grid-template-columns: 1fr 1fr; }
    }
    .full { grid-column: 1 / -1; }

    .field { display: flex; flex-direction: column; gap: 0.35rem; }

    label {
      font-size: 0.76rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--muted);
    }

    input[type="text"],
    input[type="number"],
    input[type="file"],
    textarea,
    select {
      background: var(--surface2);
      border: 1px solid var(--border);
      border-radius: var(--radius-sm);
      color: var(--text);
      font-family: inherit;
      font-size: 0.88rem;
      padding: 0.65rem 0.85rem;
      width: 100%;
      outline: none;
      transition: border-color 0.15s, box-shadow 0.15s;
    }
    input[type="text"]:focus,
    input[type="number"]:focus,
    input[type="file"]:focus,
    textarea:focus,
    select:focus { 
      border-color: var(--accent); 
      box-shadow: 0 0 0 3px var(--accent-glow);
    }

    textarea {
      resize: vertical;
      min-height: 80px;
    }

    /* ── Checkbox ── */
    .cbrow { display: flex; align-items: center; gap: 0.6rem; margin: 0.8rem 0; }
    .cbrow input[type="checkbox"] { 
      width: 16px; height: 16px; 
      accent-color: var(--accent); 
      cursor: pointer; 
      flex-shrink: 0; 
    }
    .cbrow label { 
      text-transform: none; 
      letter-spacing: 0; 
      font-size: 0.88rem; 
      color: var(--text); 
      cursor: pointer; 
    }

    /* ── Buttons ── */
    .btn {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 0.5rem;
      background: var(--accent);
      color: #fff;
      font-family: inherit;
      font-size: 0.88rem;
      font-weight: 600;
      padding: 0.65rem 1.4rem;
      border: 1px solid rgba(255,255,255,0.08);
      border-radius: var(--radius-sm);
      cursor: pointer;
      transition: background 0.15s, transform 0.08s, box-shadow 0.15s;
      user-select: none;
    }
    .btn:hover { background: var(--accent-h); }
    .btn:active { transform: scale(0.98); }
    .btn:disabled { opacity: 0.5; cursor: not-allowed; }

    .btn-secondary {
      background: transparent;
      border: 1px solid var(--border);
      color: var(--text);
    }
    .btn-secondary:hover {
      background: var(--surface2);
      border-color: var(--muted);
    }

    .btn-danger {
      background: rgba(239, 68, 68, 0.1);
      border: 1px solid rgba(239, 68, 68, 0.3);
      color: #fca5a5;
    }
    .btn-danger:hover {
      background: var(--danger);
      color: #fff;
    }

    .btn-warning {
      background: rgba(245, 158, 11, 0.1);
      border: 1px solid rgba(245, 158, 11, 0.3);
      color: #fde68a;
    }
    .btn-warning:hover {
      background: var(--warn);
      color: #000;
    }

    .btn-xs {
      padding: 0.3rem 0.6rem;
      font-size: 0.75rem;
      border-radius: 4px;
    }

    /* ── Spinner ── */
    .spin {
      display: none;
      width: 14px;
      height: 14px;
      border: 2px solid rgba(255,255,255,0.3);
      border-top-color: #fff;
      border-radius: 50%;
      animation: rot 0.65s linear infinite;
      flex-shrink: 0;
    }
    @keyframes rot { to { transform: rotate(360deg); } }

    /* ── Search Input ── */
    .search-input-group {
      display: flex;
      gap: 0.5rem;
      width: 100%;
    }

    /* ── Search Results ── */
    .chunks { margin-top: 1.5rem; display: flex; flex-direction: column; gap: 1rem; }

    .chunk {
      background: var(--surface2);
      border: 1px solid var(--border);
      border-radius: var(--radius-sm);
      padding: 1.2rem;
      transition: border-color 0.15s;
    }
    .chunk:hover {
      border-color: var(--border-glow);
    }
    .chunk-title { font-family: 'Outfit', sans-serif; font-weight: 600; font-size: 1rem; margin-bottom: 0.5rem; }
    .chunk-meta  { display: flex; flex-wrap: wrap; gap: 0.4rem 1rem; margin-bottom: 0.8rem; border-bottom: 1px solid rgba(255,255,255,0.05); padding-bottom: 0.5rem; }
    .chunk-meta span { font-size: 0.78rem; color: var(--muted); }
    .chunk-meta strong { color: var(--text); }
    
    .badge-score {
      background: var(--accent-glow);
      color: var(--accent-h);
      border: 1px solid rgba(99, 102, 241, 0.2);
      border-radius: 20px;
      padding: 0.1rem 0.5rem;
      font-size: 0.73rem;
      font-weight: 700;
    }
    .chunk-body {
      font-size: 0.88rem;
      color: #d1d5db;
      line-height: 1.6;
      max-height: 180px;
      overflow-y: auto;
      background: rgba(0,0,0,0.15);
      padding: 0.75rem;
      border-radius: 6px;
    }
    .empty { color: var(--muted); font-size: 0.88rem; text-align: center; padding: 2.5rem 0; }

    /* ── Modal Dialog ── */
    .modal-backdrop {
      position: fixed;
      top: 0; left: 0; right: 0; bottom: 0;
      background: rgba(4, 6, 10, 0.8);
      backdrop-filter: blur(8px);
      display: flex;
      align-items: center;
      justify-content: center;
      opacity: 0;
      pointer-events: none;
      transition: opacity 0.25s ease;
      z-index: 1000;
      padding: 1rem;
    }
    .modal-backdrop.show {
      opacity: 1;
      pointer-events: auto;
    }

    .modal-card {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      width: 100%;
      max-width: 760px;
      max-height: 90vh;
      overflow-y: auto;
      box-shadow: var(--shadow-lg);
      transform: translateY(20px);
      transition: transform 0.25s cubic-bezier(0.16, 1, 0.3, 1);
      display: flex;
      flex-direction: column;
    }
    .modal-backdrop.show .modal-card {
      transform: translateY(0);
    }

    .modal-header {
      padding: 1.5rem 1.8rem;
      border-bottom: 1px solid var(--border);
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .modal-header h2 {
      font-family: 'Outfit', sans-serif;
      font-size: 1.35rem;
      font-weight: 600;
    }
    .modal-close {
      background: transparent;
      border: none;
      color: var(--muted);
      cursor: pointer;
      font-size: 1.5rem;
      line-height: 1;
      padding: 0.25rem;
      transition: color 0.15s;
    }
    .modal-close:hover { color: var(--text); }

    .modal-body {
      padding: 1.8rem;
      overflow-y: auto;
      flex: 1;
    }

    .modal-footer {
      padding: 1.2rem 1.8rem;
      border-top: 1px solid var(--border);
      background: var(--surface2);
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      align-items: center;
      gap: 1rem;
      border-bottom-left-radius: var(--radius);
      border-bottom-right-radius: var(--radius);
    }

    .modal-actions-right {
      display: flex;
      gap: 0.5rem;
    }

    /* ── Read-only Block ── */
    .readonly-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
      gap: 0.75rem;
      background: var(--surface2);
      border: 1px solid var(--border);
      padding: 1rem;
      border-radius: var(--radius-sm);
      margin-bottom: 1.5rem;
    }
    .readonly-item {
      display: flex;
      flex-direction: column;
      gap: 0.2rem;
    }
    .readonly-label {
      font-size: 0.68rem;
      color: var(--muted);
      text-transform: uppercase;
      font-weight: 600;
    }
    .readonly-val {
      font-size: 0.82rem;
      font-weight: 500;
      color: var(--text);
      word-break: break-all;
    }

    /* ── Inline Subsections ── */
    .modal-section {
      margin-top: 2rem;
      padding-top: 1.5rem;
      border-top: 1px solid var(--border);
    }
    .modal-section-title {
      font-family: 'Outfit', sans-serif;
      font-size: 1rem;
      font-weight: 600;
      margin-bottom: 1rem;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }

    /* ── Jobs Table ── */
    .jobs-list {
      max-height: 200px;
      overflow-y: auto;
      border: 1px solid var(--border);
      border-radius: var(--radius-sm);
      font-size: 0.82rem;
    }
    .job-row {
      display: grid;
      grid-template-columns: 2fr 1fr 2fr 1fr;
      padding: 0.6rem 0.8rem;
      border-bottom: 1px solid var(--border);
      align-items: center;
    }
    .job-row:last-child { border-bottom: none; }
    .job-row.hdr {
      background: var(--surface2);
      font-weight: 600;
      color: var(--muted);
      text-transform: uppercase;
      font-size: 0.68rem;
    }
    .job-err {
      grid-column: span 4;
      padding: 0.4rem 0.8rem;
      background: rgba(239, 68, 68, 0.05);
      border-top: 1px dashed rgba(239, 68, 68, 0.2);
      color: var(--danger);
      font-size: 0.76rem;
      word-break: break-all;
    }

    .result-alert {
      margin-top: 1rem;
      padding: 0.75rem 1rem;
      border-radius: var(--radius-sm);
      font-size: 0.85rem;
      display: none;
    }
    .result-alert.show { display: block; }
    .result-alert.success {
      background: rgba(16, 185, 129, 0.1);
      border: 1px solid rgba(16, 185, 129, 0.25);
      color: #34d399;
    }
    .result-alert.error {
      background: rgba(239, 68, 68, 0.1);
      border: 1px solid rgba(239, 68, 68, 0.25);
      color: #f87171;
    }

    /* ── Confirmation Overlay ── */
    .confirm-overlay {
      position: fixed;
      top: 0; left: 0; right: 0; bottom: 0;
      background: rgba(4, 6, 10, 0.85);
      backdrop-filter: blur(4px);
      display: none;
      align-items: center;
      justify-content: center;
      z-index: 2000;
      padding: 1rem;
    }
    .confirm-dialog {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      width: 100%;
      max-width: 480px;
      padding: 1.8rem;
      box-shadow: var(--shadow-lg);
    }
    .confirm-dialog h3 {
      font-family: 'Outfit', sans-serif;
      font-size: 1.25rem;
      font-weight: 600;
      margin-top: 0;
      margin-bottom: 0.8rem;
      color: var(--text);
    }
    .confirm-dialog p {
      font-size: 0.9rem;
      color: var(--muted);
      line-height: 1.5;
      margin-bottom: 1.8rem;
    }
    .confirm-actions {
      display: flex;
      justify-content: flex-end;
      gap: 0.75rem;
    }

    /* ── Top Tabs Navigation ── */
    .tabs-container {
      max-width: 1200px;
      margin: 0 auto 1.5rem;
      display: flex;
      gap: 0.5rem;
      border-bottom: 1px solid var(--border);
      padding-bottom: 0.5rem;
    }
    .tab-btn {
      background: transparent;
      border: 1px solid transparent;
      font-family: inherit;
      color: var(--muted);
      cursor: pointer;
      font-size: 0.9rem;
      font-weight: 600;
      padding: 0.6rem 1.2rem;
      border-radius: var(--radius-sm);
      transition: all 0.15s ease;
      user-select: none;
    }
    .tab-btn:hover {
      color: var(--text);
      background: var(--surface2);
    }
    .tab-btn.active {
      color: #fff;
      background: var(--accent);
      border-color: rgba(255, 255, 255, 0.08);
    }
    .tab-btn:focus-visible {
      outline: 2px solid var(--accent);
      outline-offset: 2px;
    }

    .tab-content {
      display: none;
    }
    .tab-content.active {
      display: contents;
    }

  </style>
</head>
<body>

  <header>
    <div class="brand">
      <h1>⚡ Knowledge Base Console</h1>
      <p>Documents directory · semantic indexing · search admin</p>
    </div>
    <div style="display: flex; align-items: center; gap: 1rem; flex-wrap: wrap; justify-content: flex-end;">
      {user_profile_html}
      <button class="btn" onclick="openCreateModal()">
        <svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24"><path d="M12 5v14M5 12h14"></path></svg>
        Upload Document
      </button>
    </div>
  </header>

  <div class="tabs-container">
    <button type="button" id="tab-btn-kb" class="tab-btn active" aria-selected="true" aria-controls="kb-tab-content" onclick="switchTab('kb')">
      Knowledge Base
    </button>
    <button type="button" id="tab-btn-assistant" class="tab-btn" aria-selected="false" aria-controls="assistant-tab-content" onclick="switchTab('assistant')">
      Assistant
    </button>
  </div>

  <div class="wrap">

    <div id="kb-tab-content" class="tab-content active">

      <!-- ════ DOCUMENTS DIRECTORY ════ -->
      <div class="card span-all">
        <div class="card-heading">
          <span>📂 Documents Directory</span>
          <button class="btn btn-secondary btn-xs" onclick="loadDocuments()">↻ Refresh</button>
        </div>
        
        <!-- Inline error banner for document loading failures -->
        <div id="directory-error-banner" style="display: none; margin: 1rem 1.8rem 0; padding: 0.8rem 1.2rem; background: rgba(239, 68, 68, 0.08); border: 1px solid rgba(239, 68, 68, 0.2); border-radius: 6px; color: var(--danger); font-size: 0.88rem; align-items: center; justify-content: space-between;">
          <span style="font-weight: 500;">Failed to load documents directory.</span>
          <button class="btn btn-secondary btn-xs" onclick="loadDocuments()">Retry</button>
        </div>

        <div class="table-container">
          <table>
            <thead>
              <tr>
                <th>Title / File</th>
                <th>Status</th>
                <th>Chunks</th>
                <th>Tags / Authors</th>
                <th>Created At</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody id="documentsTableBody">
              <!-- Loaded dynamically -->
            </tbody>
          </table>
        </div>
      </div>

      <!-- ════ SEMANTIC SEARCH ════ -->
      <div class="card span-all">
        <div class="card-heading">🔍 Semantic Search</div>
        
        <!-- Search Exclusion Notice -->
        <div class="warning-banner">
          <svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path>
          </svg>
          <div>
            <strong>Index Availability Rule:</strong> Semantic search uses only <strong>processed</strong> documents. Uploaded, processing, failed and archived documents are excluded from search results.
          </div>
        </div>

        <form id="searchForm" novalidate>
          <div class="g2">
            <div class="field full">
              <label for="s-query">Query *</label>
              <div class="search-input-group">
                <input type="text" id="s-query" placeholder="Ask a question about the uploaded knowledge base documents..." required />
                <button type="submit" class="btn" id="s-btn" style="margin-top:0;">
                  <span class="spin" id="s-spin"></span>
                  <span id="s-btn-txt">Search</span>
                </button>
              </div>
            </div>
            <div class="field">
              <label for="s-limit">Max Chunk Results</label>
              <input type="number" id="s-limit" value="5" min="1" max="100" />
            </div>
          </div>
        </form>
        <div class="chunks" id="s-results"></div>
      </div>

    </div><!-- /kb-tab-content -->

    <!-- Assistant content -->
    <div id="assistant-tab-content" class="tab-content">
      <div class="card span-all" style="padding: 1.8rem 2rem; position: relative;">
        <!-- Configured state container -->
        <div id="assistant-configured" style="display: none;">
          <div class="card-heading" style="margin-bottom: 1.5rem; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 1rem;">
            <span>🤖 Assistant Console</span>
            <a id="hermesNewTabLink" href="" target="_blank" rel="noopener noreferrer" class="btn btn-secondary btn-xs">
              Open Assistant in a new tab ↗
            </a>
          </div>

          <div style="position: relative; width: 100%; height: calc(100vh - 250px); min-height: 700px; border-radius: var(--radius-sm); overflow: hidden; background: var(--surface2); border: 1px solid var(--border);">
            <!-- Loading placeholder overlay -->
            <div id="assistant-loading" style="position: absolute; top: 0; left: 0; right: 0; bottom: 0; background: var(--surface); display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 1rem; z-index: 10; transition: opacity 0.25s ease;">
              <div class="spin" style="display: block; width: 24px; height: 24px;"></div>
              <span style="color: var(--muted); font-size: 0.95rem;">Loading Assistant...</span>
            </div>

            <iframe
              id="hermesAssistantFrame"
              title="Leadgen Assistant"
              allow="clipboard-read; clipboard-write; microphone"
              style="width: 100%; height: 100%; border: 0;"
            ></iframe>
          </div>
        </div>

        <!-- Unconfigured state container -->
        <div id="assistant-unconfigured" style="display: none; padding: 3rem; text-align: center; color: var(--muted); font-size: 0.95rem;">
          Assistant is not configured.
        </div>
      </div>
    </div><!-- /assistant-tab-content -->

  </div><!-- /wrap -->


  <!-- ═════ REUSABLE DIALOG MODAL (CREATE & EDIT) ═════ -->
  <div class="modal-backdrop" id="docModal">
    <div class="modal-card">
      <div class="modal-header">
        <h2 id="modalTitle">Edit Document</h2>
        <button class="modal-close" onclick="closeModal()">&times;</button>
      </div>
      
      <div class="modal-body">
        
        <!-- Action Notification Alert -->
        <div class="result-alert" id="modalAlert"></div>

        <!-- Read-only details (Edit Mode Only) -->
        <div class="readonly-grid" id="modalReadonlyGrid">
          <div class="readonly-item">
            <span class="readonly-label">Document ID</span>
            <span class="readonly-val" id="r-id">-</span>
          </div>
          <div class="readonly-item">
            <span class="readonly-label">Storage Object Key</span>
            <span class="readonly-val" id="r-key">-</span>
          </div>
          <div class="readonly-item">
            <span class="readonly-label">Indexed Chunks</span>
            <span class="readonly-val" id="r-chunks">0</span>
          </div>
          <div class="readonly-item">
            <span class="readonly-label">Status</span>
            <div>
              <span class="badge-status" id="r-status">-</span>
              <span class="badge-searchable" id="r-searchable">-</span>
            </div>
          </div>
        </div>

        <form id="modalForm" novalidate>
          
          <div class="g2">
            
            <div class="field full" id="f-file-container">
              <label for="f-file">Source File *</label>
              <input type="file" id="f-file" accept=".pdf,.txt,.md,.markdown,.csv,.docx,.xlsx" />
              <small style="color: var(--muted); font-size: 0.72rem; margin-top: 0.15rem; display: block;">Supported formats: PDF, TXT, Markdown, CSV, DOCX, XLSX</small>
            </div>

            <div class="field full">
              <label for="f-title">Document Title *</label>
              <input type="text" id="f-title" placeholder="e.g. Sales Playbook Q2 2026" required />
            </div>

            <div class="field">
              <label for="f-type">Document Type</label>
              <select id="f-type">
                <option value="case">Case Study</option>
                <option value="proposal">Proposal</option>
                <option value="report">Report</option>
                <option value="other">Other</option>
              </select>
            </div>

            <div class="field">
              <label for="f-client">Client Name</label>
              <input type="text" id="f-client" placeholder="Acme Corporation" />
            </div>

            <div class="field">
              <label for="f-industry">Industry</label>
              <input type="text" id="f-industry" placeholder="Finance, Tech, Healthcare" />
            </div>

            <div class="field">
              <label for="f-geo">Geography</label>
              <input type="text" id="f-geo" placeholder="Global, North America" />
            </div>

            <div class="field">
              <label for="f-usecase">Use Case</label>
              <input type="text" id="f-usecase" placeholder="Customer Success" />
            </div>

            <div class="field">
              <label for="f-source-type">Source Type</label>
              <input type="text" id="f-source-type" placeholder="e.g. Google Drive, Confluence, Local" />
            </div>

            <div class="field full">
              <label for="f-source-url">Source URL</label>
              <input type="text" id="f-source-url" placeholder="https://..." />
            </div>

            <div class="field full">
              <label for="f-description">Description / Synopsis</label>
              <textarea id="f-description" placeholder="Provide a brief summary of the document contents..."></textarea>
            </div>

            <div class="field">
              <label for="f-tags">Tags <small>(comma-separated)</small></label>
              <input type="text" id="f-tags" placeholder="mlops, startup, case-study" />
            </div>

            <div class="field">
              <label for="f-authors">Authors <small>(comma-separated)</small></label>
              <input type="text" id="f-authors" placeholder="Jane Doe, John Smith" />
            </div>

            <div class="field full">
              <label for="f-metadata">Custom JSON Metadata</label>
              <textarea id="f-metadata" placeholder="{}"></textarea>
            </div>

          </div>

          <!-- Create Mode only option -->
          <div class="cbrow" id="f-process-container">
            <input type="checkbox" id="f-process" checked />
            <label for="f-process">Process immediately (parse → chunk → embed)</label>
          </div>

        </form>

        <!-- Replace File Section (Edit Mode Only) -->
        <div class="modal-section" id="modalReplaceSection">
          <div class="modal-section-title">♻ Replace Source File</div>
          <div class="warning-banner" style="margin-bottom:0.8rem;">
            <div>
              Replacing the source file will upload a versioned file (preventing overwrite of the previous version) and trigger a <strong>Rebuild Search Index</strong>.
            </div>
          </div>
          <div style="display:flex; gap:0.5rem; align-items:flex-end;">
            <div class="field" style="flex:1;">
              <label for="replace-file-input">Select New Source File</label>
              <input type="file" id="replace-file-input" accept=".pdf,.txt,.md,.markdown,.csv,.docx,.xlsx" />
              <small style="color: var(--muted); font-size: 0.72rem; margin-top: 0.15rem; display: block;">Supported formats: PDF, TXT, Markdown, CSV, DOCX, XLSX</small>
            </div>
            <button class="btn btn-warning" id="btnReplaceFile" onclick="triggerReplaceFile()">
              <span class="spin" id="replace-spin"></span>
              Replace &amp; Rebuild
            </button>
          </div>
        </div>

        <!-- Ingestion Job History Section (Edit Mode Only) -->
        <div class="modal-section" id="modalJobsSection">
          <div class="modal-section-title">
            <span>⚙ Ingestion &amp; Index Job History</span>
            <button class="btn btn-secondary btn-xs" onclick="loadJobsForCurrentDoc()">Reload Jobs</button>
          </div>
          <div class="jobs-list">
            <div class="job-row hdr">
              <div>Job ID / Started</div>
              <div>Status</div>
              <div>Source File Key</div>
              <div>Action</div>
            </div>
            <div id="jobsListBody">
              <!-- Dynamically populated -->
            </div>
          </div>
        </div>

      </div>

      <div class="modal-footer">
        <div style="display: flex; flex-direction: column; gap: 0.4rem;">
          <div style="display: flex; gap: 0.5rem;">
            <!-- Edit mode left actions -->
            <button class="btn btn-danger" id="btnArchive" onclick="toggleArchive()"></button>
            <button class="btn btn-warning" id="btnRebuild" onclick="triggerRebuild()"></button>
          </div>
          <div id="rebuild-helper" style="font-size: 0.72rem; color: var(--muted); max-width: 300px; line-height: 1.2;">
            Recreates chunks and embeddings from the current source file. Not needed for metadata edits.
          </div>
        </div>
        <div class="modal-actions-right">
          <button class="btn btn-secondary" onclick="closeModal()">Close</button>
          <button class="btn" id="btnSubmitForm" onclick="submitModalForm()">
            <span class="spin" id="submit-spin"></span>
            <span id="submit-btn-txt">Save</span>
          </button>
        </div>
      </div>

    </div>
  </div>


  <!-- ═════ REUSABLE CONFIRMATION MODAL ═════ -->
  <div id="confirmOverlay" class="confirm-overlay" style="display:none;">
    <div class="confirm-dialog">
      <h3 id="confirmTitle">Confirm Action</h3>
      <p id="confirmMessage"></p>
      <div class="confirm-actions">
        <button id="confirmCancelBtn" class="btn btn-secondary" onclick="handleConfirm(false)">Cancel</button>
        <button id="confirmOkBtn" class="btn" onclick="handleConfirm(true)">Confirm</button>
      </div>
    </div>
  </div>


  <script>
    // ── Global States ──
    let allDocuments = [];
    let currentDocId = null; // null represents Create Mode, defined string represents Edit Mode

    let confirmResolve = null;

    async function showConfirmDialog({
      title,
      message,
      confirmLabel = 'Confirm',
      cancelLabel = 'Cancel',
      tone = 'warning'
    }) {
      const overlay = document.getElementById('confirmOverlay');
      const titleEl = document.getElementById('confirmTitle');
      const messageEl = document.getElementById('confirmMessage');
      const cancelBtn = document.getElementById('confirmCancelBtn');
      const okBtn = document.getElementById('confirmOkBtn');

      titleEl.textContent = title;
      messageEl.textContent = message;
      cancelBtn.textContent = cancelLabel;
      okBtn.textContent = confirmLabel;

      // Reset styles
      okBtn.className = 'btn';
      if (tone === 'danger') {
        okBtn.classList.add('btn-danger');
      } else if (tone === 'warning') {
        okBtn.classList.add('btn-warning');
      } else {
        okBtn.classList.add('btn-primary');
      }

      overlay.style.display = 'flex';

      return new Promise((resolve) => {
        confirmResolve = resolve;
      });
    }

    function handleConfirm(confirmed) {
      const overlay = document.getElementById('confirmOverlay');
      overlay.style.display = 'none';
      if (confirmResolve) {
        confirmResolve(confirmed);
        confirmResolve = null;
      }
    }

    window.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        const overlay = document.getElementById('confirmOverlay');
        if (overlay && overlay.style.display === 'flex') {
          handleConfirm(false);
          e.stopImmediatePropagation();
        }
      }
    }, true);

    const esc = s => (s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');

    function formatBytes(bytes) {
      if (!bytes) return '0 Bytes';
      const k = 1024;
      const sizes = ['Bytes', 'KB', 'MB', 'GB'];
      const i = Math.floor(Math.log(bytes) / Math.log(k));
      return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    // ── Load Documents ──
    async function loadDocuments() {
      try {
        const resp = await fetch('/api/v1/documents');
        if (!resp.ok) throw new Error('Failed to fetch documents directory.');
        allDocuments = await resp.json();
        document.getElementById('directory-error-banner').style.display = 'none';
        renderDocuments();
      } catch (err) {
        document.getElementById('directory-error-banner').style.display = 'flex';
      }
    }

    function renderDocuments() {
      const tbody = document.getElementById('documentsTableBody');
      tbody.innerHTML = '';
      
      if (!allDocuments.length) {
        tbody.innerHTML = `<tr><td colspan="6" class="empty">No documents found. Upload one to get started!</td></tr>`;
        return;
      }

      allDocuments.forEach(doc => {
        const tr = document.createElement('tr');
        const isSearchable = doc.status === 'processed';
        
        tr.innerHTML = `
          <td>
            <div style="font-weight:600; color:var(--text); font-size:0.92rem;">${esc(doc.title)}</div>
            <div style="color:var(--muted); font-size:0.75rem; margin-top:0.15rem; word-break:break-all;">${esc(doc.file_name || doc.source_object_key)}</div>
          </td>
          <td>
            <span class="badge-status ${doc.status}">${doc.status}</span>
            <span class="badge-searchable ${isSearchable ? 'yes' : 'no'}">${isSearchable ? '🔍 Searchable' : '🚫 Not Searchable'}</span>
          </td>
          <td style="font-weight: 500;">${doc.chunks_count}</td>
          <td>
            <div style="max-width: 250px; display:flex; flex-wrap:wrap; gap:0.25rem;">
              ${(() => {
                const tags = doc.tags || [];
                const maxTags = 5;
                const visible = tags.slice(0, maxTags);
                let tagsHtml = visible.map(t => `<span style="font-size:0.7rem; background:var(--surface2); border:1px solid var(--border); padding:0.1rem 0.35rem; border-radius:4px; color:var(--muted);">${esc(t)}</span>`).join('');
                if (tags.length > maxTags) {
                  tagsHtml += `<span style="font-size:0.7rem; font-weight:600; color:var(--muted); align-self:center; margin-left:0.1rem;">+${tags.length - maxTags} more</span>`;
                }
                return tagsHtml;
              })()}
              ${(doc.authors || []).map(a => `<span style="font-size:0.7rem; background:rgba(99, 102, 241, 0.1); border:1px solid rgba(99, 102, 241, 0.2); padding:0.1rem 0.35rem; border-radius:4px; color:var(--text);">${esc(a)}</span>`).join('')}
            </div>
          </td>
          <td style="color:var(--muted); font-size:0.8rem;">${new Date(doc.created_at).toLocaleString()}</td>
          <td>
            <button class="btn btn-secondary btn-xs" onclick="openEditModal('${doc.id}')">Manage</button>
          </td>
        `;
        tbody.appendChild(tr);
      });
    }

    // ── Modal Handlers ──
    function openCreateModal() {
      currentDocId = null;
      document.getElementById('modalTitle').textContent = 'Upload Document';
      
      // Setup elements visibility
      document.getElementById('modalReadonlyGrid').style.display = 'none';
      document.getElementById('f-file-container').style.display = 'block';
      document.getElementById('f-process-container').style.display = 'flex';
      document.getElementById('modalReplaceSection').style.display = 'none';
      document.getElementById('modalJobsSection').style.display = 'none';
      document.getElementById('btnArchive').style.display = 'none';
      document.getElementById('btnRebuild').style.display = 'none';
      document.getElementById('rebuild-helper').style.display = 'none';
      
      document.getElementById('submit-btn-txt').textContent = 'Upload & Process';

      // Clear form
      document.getElementById('modalForm').reset();
      document.getElementById('f-metadata').value = '{}';
      clearAlert();

      // Show Modal
      document.getElementById('docModal').classList.add('show');
    }

    function openEditModal(docId) {
      currentDocId = docId;
      const doc = allDocuments.find(d => d.id === docId);
      if (!doc) return;

      document.getElementById('modalTitle').textContent = 'Edit Document Metadata';
      
      // Setup elements visibility
      document.getElementById('modalReadonlyGrid').style.display = 'grid';
      document.getElementById('f-file-container').style.display = 'none';
      document.getElementById('f-process-container').style.display = 'none';
      document.getElementById('modalReplaceSection').style.display = 'block';
      document.getElementById('modalJobsSection').style.display = 'block';
      document.getElementById('btnArchive').style.display = 'inline-flex';
      document.getElementById('btnRebuild').style.display = 'inline-flex';
      document.getElementById('rebuild-helper').style.display = 'block';
      
      document.getElementById('submit-btn-txt').textContent = 'Save Metadata';

      // Fill read-only specs
      document.getElementById('r-id').textContent = doc.id;
      document.getElementById('r-key').textContent = doc.source_object_key;
      document.getElementById('r-chunks').textContent = doc.chunks_count;
      
      const rStatus = document.getElementById('r-status');
      rStatus.className = `badge-status ${doc.status}`;
      rStatus.textContent = doc.status;

      const rSearchable = document.getElementById('r-searchable');
      const isSearchable = doc.status === 'processed';
      rSearchable.className = `badge-searchable ${isSearchable ? 'yes' : 'no'}`;
      rSearchable.textContent = isSearchable ? '🔍 Searchable' : '🚫 Not Searchable';

      // Archive button state
      const btnArchive = document.getElementById('btnArchive');
      if (doc.status === 'archived') {
        btnArchive.textContent = 'Restore Document';
        btnArchive.className = 'btn btn-secondary';
      } else {
        btnArchive.textContent = 'Archive Document';
        btnArchive.className = 'btn btn-danger';
      }

      // Rebuild button state
      const btnRebuild = document.getElementById('btnRebuild');
      btnRebuild.textContent = 'Rebuild Search Index';
      if (doc.status === 'archived') {
        btnRebuild.disabled = true;
        btnRebuild.title = 'Please restore the document first.';
      } else {
        btnRebuild.disabled = false;
        btnRebuild.title = '';
      }

      // Pre-fill form
      document.getElementById('f-title').value = doc.title || '';
      document.getElementById('f-type').value = doc.type || 'case';
      document.getElementById('f-client').value = doc.client_name || '';
      document.getElementById('f-industry').value = doc.industry || '';
      document.getElementById('f-geo').value = doc.geography || '';
      document.getElementById('f-usecase').value = doc.use_case || '';
      document.getElementById('f-source-type').value = doc.source_type || '';
      document.getElementById('f-source-url').value = doc.source_url || '';
      document.getElementById('f-description').value = doc.description || '';
      document.getElementById('f-tags').value = (doc.tags || []).join(', ');
      document.getElementById('f-authors').value = (doc.authors || []).join(', ');
      document.getElementById('f-metadata').value = JSON.stringify(doc.metadata || {}, null, 2);

      // Reset replace file input
      document.getElementById('replace-file-input').value = '';

      clearAlert();
      loadJobsForCurrentDoc();

      // Show Modal
      document.getElementById('docModal').classList.add('show');
    }

    function closeModal() {
      document.getElementById('docModal').classList.remove('show');
      loadDocuments(); // refresh underlying list
    }

    // Alert helpers
    function showAlert(ok, msg) {
      const alertEl = document.getElementById('modalAlert');
      alertEl.className = `result-alert show ${ok ? 'success' : 'error'}`;
      alertEl.textContent = msg;
    }
    function clearAlert() {
      const alertEl = document.getElementById('modalAlert');
      alertEl.className = 'result-alert';
      alertEl.textContent = '';
    }

    // Loading indicator helper inside modal
    function setModalLoading(loading, submitText) {
      document.getElementById('btnSubmitForm').disabled = loading;
      document.getElementById('submit-spin').style.display = loading ? 'block' : 'none';
      document.getElementById('submit-btn-txt').textContent = loading ? 'Saving...' : submitText;
    }

    // ── Submit Modal Form (Create / Edit Metadata) ──
    async function submitModalForm() {
      if (currentDocId === null) {
        // CREATE / UPLOAD MODE
        const fileEl = document.getElementById('f-file');
        const titleEl = document.getElementById('f-title');

        if (!fileEl.files.length) {
          showAlert(false, 'Please select a source file.');
          return;
        }
        if (!titleEl.value.trim()) {
          showAlert(false, 'Please enter a document title.');
          return;
        }

        setModalLoading(true, 'Upload & Process');
        try {
          const fd = new FormData();
          fd.append('file',              fileEl.files[0]);
          fd.append('title',             titleEl.value.trim());
          fd.append('type',              document.getElementById('f-type').value);
          fd.append('client_name',       document.getElementById('f-client').value.trim());
          fd.append('industry',          document.getElementById('f-industry').value.trim());
          fd.append('geography',         document.getElementById('f-geo').value.trim());
          fd.append('use_case',          document.getElementById('f-usecase').value.trim());
          fd.append('source_type',       document.getElementById('f-source-type').value.trim());
          fd.append('source_url',        document.getElementById('f-source-url').value.trim());
          fd.append('description',       document.getElementById('f-description').value.trim());
          fd.append('tags',              document.getElementById('f-tags').value.trim());
          fd.append('authors',           document.getElementById('f-authors').value.trim());
          fd.append('metadata',          document.getElementById('f-metadata').value.trim());
          fd.append('process_immediately', document.getElementById('f-process').checked ? 'true' : 'false');

          const resp = await fetch('/api/v1/documents/upload', { method: 'POST', body: fd });
          const data = await resp.json();
          if (resp.ok) {
            showAlert(true, `✓ Upload successful! Document ID: ${data.document_id}, Status: ${data.status}`);
            // Transition to Edit Mode for the newly created document
            setTimeout(() => {
              loadDocuments().then(() => openEditModal(data.document_id));
            }, 1000);
          } else {
            showAlert(false, data.detail || JSON.stringify(data));
          }
        } catch (err) {
          showAlert(false, 'Network error: ' + err.message);
        } finally {
          setModalLoading(false, 'Upload & Process');
        }

      } else {
        // EDIT METADATA MODE
        const title = document.getElementById('f-title').value.trim();
        if (!title) {
          showAlert(false, 'Title is required.');
          return;
        }

        // Validate JSON metadata field
        let metaObj = {};
        const metaStr = document.getElementById('f-metadata').value.trim();
        if (metaStr) {
          try {
            metaObj = JSON.parse(metaStr);
            if (typeof metaObj !== 'object' || Array.isArray(metaObj)) {
              throw new Error('Metadata must be a JSON object');
            }
          } catch (e) {
            showAlert(false, 'Invalid Custom JSON Metadata: ' + e.message);
            return;
          }
        }

        // Parse comma-separated lists
        const tags = document.getElementById('f-tags').value.split(',').map(t => t.strip ? t.strip() : t.trim()).filter(Boolean);
        const authors = document.getElementById('f-authors').value.split(',').map(a => a.strip ? a.strip() : a.trim()).filter(Boolean);

        const payload = {
          type: document.getElementById('f-type').value,
          client_name: document.getElementById('f-client').value.trim(),
          industry: document.getElementById('f-industry').value.trim(),
          geography: document.getElementById('f-geo').value.trim(),
          use_case: document.getElementById('f-usecase').value.trim(),
          tags: tags,
          authors: authors,
          description: document.getElementById('f-description').value.trim() || null,
          source_type: document.getElementById('f-source-type').value.trim() || null,
          source_url: document.getElementById('f-source-url').value.trim() || null,
          metadata: metaObj
        };

        setModalLoading(true, 'Save Metadata');
        try {
          const resp = await fetch(`/api/v1/documents/${currentDocId}?title=${encodeURIComponent(title)}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
          });
          const data = await resp.json();
          if (resp.ok) {
            showAlert(true, '✓ Metadata updated successfully!');
            loadDocuments().then(() => {
              // refresh edit modal details
              const doc = allDocuments.find(d => d.id === currentDocId);
              if (doc) {
                document.getElementById('r-chunks').textContent = doc.chunks_count;
              }
            });
          } else {
            showAlert(false, data.detail || JSON.stringify(data));
          }
        } catch (err) {
          showAlert(false, 'Network error: ' + err.message);
        } finally {
          setModalLoading(false, 'Save Metadata');
        }
      }
    }

    // ── Archive / Restore Document ──
    async function toggleArchive() {
      if (!currentDocId) return;
      const doc = allDocuments.find(d => d.id === currentDocId);
      if (!doc) return;

      const isArchived = doc.status === 'archived';
      const action = isArchived ? 'restore' : 'archive';
      
      if (!isArchived) {
        const confirmed = await showConfirmDialog({
          title: 'Archive document?',
          message: 'Archived documents are hidden from semantic search but remain stored.',
          confirmLabel: 'Archive Document',
          cancelLabel: 'Cancel',
          tone: 'danger'
        });
        if (!confirmed) return;
      }
      
      try {
        const resp = await fetch(`/api/v1/documents/${currentDocId}/${action}`, { method: 'POST' });
        const data = await resp.json();
        if (resp.ok) {
          showAlert(true, `✓ Document ${isArchived ? 'restored' : 'archived'} successfully.`);
          loadDocuments().then(() => openEditModal(currentDocId));
        } else {
          showAlert(false, data.detail || JSON.stringify(data));
        }
      } catch (err) {
        showAlert(false, 'Network error: ' + err.message);
      }
    }

    // ── Rebuild Search Index ──
    async function triggerRebuild() {
      if (!currentDocId) return;
      
      const confirmed = await showConfirmDialog({
        title: 'Rebuild search index?',
        message: 'This will delete current chunks, re-read the stored source file, recreate chunks, and regenerate embeddings. Metadata changes do not require this.',
        confirmLabel: 'Rebuild Search Index',
        cancelLabel: 'Cancel',
        tone: 'warning'
      });
      if (!confirmed) return;

      try {
        const resp = await fetch(`/api/v1/documents/${currentDocId}/reingest`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            process_immediately: true,
            reason: 'manual_rebuild'
          })
        });
        const data = await resp.json();
        if (resp.ok) {
          showAlert(true, `✓ Search Index rebuild triggered! New Job ID: ${data.job_id}. Status: ${data.status}`);
          loadDocuments().then(() => openEditModal(currentDocId));
        } else {
          showAlert(false, data.detail || JSON.stringify(data));
        }
      } catch (err) {
        showAlert(false, 'Network error: ' + err.message);
      }
    }

    // ── Replace Source File ──
    async function triggerReplaceFile() {
      if (!currentDocId) return;
      const fileEl = document.getElementById('replace-file-input');
      if (!fileEl.files.length) {
        showAlert(false, "Please select a source file first.");
        return;
      }

      const confirmed = await showConfirmDialog({
        title: 'Replace source file and rebuild search index?',
        message: 'This will upload a new versioned source file, update the document source, delete old chunks, and generate new embeddings. Existing metadata will be preserved.',
        confirmLabel: 'Replace & Rebuild',
        cancelLabel: 'Cancel',
        tone: 'warning'
      });
      if (!confirmed) return;

      const btn = document.getElementById('btnReplaceFile');
      const spin = document.getElementById('replace-spin');
      btn.disabled = true;
      spin.style.display = 'block';

      try {
        const fd = new FormData();
        fd.append('file', fileEl.files[0]);
        fd.append('process_immediately', 'true');

        const resp = await fetch(`/api/v1/documents/${currentDocId}/replace-file`, {
          method: 'POST',
          body: fd
        });
        const data = await resp.json();
        if (resp.ok) {
          showAlert(true, `✓ File replaced successfully! New version key: ${data.source_object_key}. Ingestion status: ${data.status}`);
          fileEl.value = '';
          loadDocuments().then(() => openEditModal(currentDocId));
        } else {
          showAlert(false, data.detail || JSON.stringify(data));
        }
      } catch (err) {
        showAlert(false, 'Network error: ' + err.message);
      } finally {
        btn.disabled = false;
        spin.style.display = 'none';
      }
    }

    // ── Load Jobs history for current doc ──
    async function loadJobsForCurrentDoc() {
      if (!currentDocId) return;
      const listBody = document.getElementById('jobsListBody');
      listBody.innerHTML = '<div style="padding:1rem; text-align:center; color:var(--muted)">Loading jobs...</div>';

      try {
        const resp = await fetch(`/api/v1/documents/${currentDocId}/jobs`);
        if (!resp.ok) throw new Error('Failed to fetch jobs.');
        const jobs = await resp.json();

        listBody.innerHTML = '';
        if (!jobs.length) {
          listBody.innerHTML = '<div style="padding:1rem; text-align:center; color:var(--muted)">No jobs found for this document.</div>';
          return;
        }

        jobs.forEach(job => {
          const row = document.createElement('div');
          row.style.display = 'contents'; // use CSS Grid layout of the container

          const isFailed = job.status === 'failed';
          const canRetry = isFailed;

          row.innerHTML = `
            <div class="job-row">
              <div>
                <strong style="color:var(--text); font-size:0.78rem;">${esc(job.job_id.substring(0,8))}...</strong>
                <div style="font-size:0.7rem; color:var(--muted); margin-top:0.1rem;">${new Date(job.created_at).toLocaleString()}</div>
              </div>
              <div>
                <span class="badge-status ${job.status}">${job.status}</span>
              </div>
              <div style="word-break:break-all; font-size:0.75rem; color:var(--muted);">${esc(job.source_object_key)}</div>
              <div>
                ${canRetry ? `<button class="btn btn-warning btn-xs" onclick="retryJob('${job.job_id}')">Retry</button>` : '<span style="color:var(--muted)">—</span>'}
              </div>
            </div>
            ${isFailed && job.error ? `<div class="job-err"><strong>Error:</strong> ${esc(job.error)}</div>` : ''}
          `;
          listBody.appendChild(row);
        });
      } catch (err) {
        listBody.innerHTML = `<div style="padding:1rem; text-align:center; color:var(--danger)">${esc(err.message)}</div>`;
      }
    }

    // ── Retry Job ──
    async function retryJob(jobId) {
      try {
        const resp = await fetch(`/api/v1/ingestion/jobs/${jobId}/retry?process_immediately=true`, {
          method: 'POST'
        });
        const data = await resp.json();
        if (resp.ok) {
          showAlert(true, `✓ Job retry triggered! Status: ${data.status}`);
          loadJobsForCurrentDoc();
          loadDocuments().then(() => {
            // refresh modal read only status block
            const doc = allDocuments.find(d => d.id === currentDocId);
            if (doc) {
              document.getElementById('r-chunks').textContent = doc.chunks_count;
              const rStatus = document.getElementById('r-status');
              rStatus.className = `badge-status ${doc.status}`;
              rStatus.textContent = doc.status;
            }
          });
        } else {
          showAlert(false, data.detail || JSON.stringify(data));
        }
      } catch (err) {
        showAlert(false, 'Network error: ' + err.message);
      }
    }

    // ── Semantic Search ──
    document.getElementById('searchForm').addEventListener('submit', async e => {
      e.preventDefault();
      const query = document.getElementById('s-query').value.trim();
      if (!query) return;

      const btn = document.getElementById('s-btn');
      const spin = document.getElementById('s-spin');
      const txt = document.getElementById('s-btn-txt');
      
      btn.disabled = true;
      spin.style.display = 'block';
      txt.textContent = 'Searching...';

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
              <span class="badge-score">Score: ${(r.score * 100).toFixed(1)}%</span>
              ${r.client_name ? `<span><strong>Client:</strong> ${esc(r.client_name)}</span>` : ''}
              ${r.type        ? `<span><strong>Type:</strong> ${esc(r.type)}</span>`        : ''}
              ${r.industry    ? `<span><strong>Industry:</strong> ${esc(r.industry)}</span>` : ''}
              ${r.source_type ? `<span><strong>Source:</strong> ${esc(r.source_type)}</span>` : ''}
            </div>
            <div class="chunk-body">${esc(r.content)}</div>
          `;
          container.appendChild(c);
        });
      } catch (err) {
        container.innerHTML = `<div class="empty" style="color:var(--danger)">Network error: ${esc(err.message)}</div>`;
      } finally {
        btn.disabled = false;
        spin.style.display = 'none';
        txt.textContent = 'Search';
      }
    });

    function switchTab(tab) {
      const kbTab = document.getElementById('kb-tab-content');
      const assistantTab = document.getElementById('assistant-tab-content');
      const btnKb = document.getElementById('tab-btn-kb');
      const btnAssistant = document.getElementById('tab-btn-assistant');

      if (tab === 'kb') {
        kbTab.classList.add('active');
        assistantTab.classList.remove('active');
        btnKb.classList.add('active');
        btnKb.setAttribute('aria-selected', 'true');
        btnAssistant.classList.remove('active');
        btnAssistant.setAttribute('aria-selected', 'false');
      } else if (tab === 'assistant') {
        kbTab.classList.remove('active');
        assistantTab.classList.add('active');
        btnKb.classList.remove('active');
        btnKb.setAttribute('aria-selected', 'false');
        btnAssistant.classList.add('active');
        btnAssistant.setAttribute('aria-selected', 'true');
      }
    }

    const hermesWebuiUrl = {hermes_webui_url_json};

    // ── Init ──
    document.addEventListener('DOMContentLoaded', () => {
      loadDocuments();

      const configuredContainer = document.getElementById('assistant-configured');
      const unconfiguredContainer = document.getElementById('assistant-unconfigured');
      const iframe = document.getElementById('hermesAssistantFrame');
      const newTabLink = document.getElementById('hermesNewTabLink');

      if (hermesWebuiUrl && hermesWebuiUrl.trim() !== "") {
        if (configuredContainer) configuredContainer.style.display = 'block';
        if (unconfiguredContainer) unconfiguredContainer.style.display = 'none';
        if (iframe) {
          iframe.src = hermesWebuiUrl;
          iframe.addEventListener('load', () => {
            const loadingOverlay = document.getElementById('assistant-loading');
            if (loadingOverlay) {
              loadingOverlay.style.opacity = '0';
              setTimeout(() => {
                loadingOverlay.style.display = 'none';
              }, 250);
            }
          });
        }
        if (newTabLink) newTabLink.href = hermesWebuiUrl;
      } else {
        if (configuredContainer) configuredContainer.style.display = 'none';
        if (unconfiguredContainer) unconfiguredContainer.style.display = 'block';
      }
    });
  </script>
</body>
</html>"""


from fastapi import Request
from fastapi.responses import HTMLResponse, RedirectResponse
import html

from src.dependencies.auth import get_optional_user

def get_initials(name: str) -> str:
    """Generate safe initials from a display name."""
    if not name:
        return "??"
    parts = name.strip().split()
    if len(parts) >= 2:
        return (parts[0][0] + parts[-1][0]).upper()
    return name[:2].upper()

@router.get("/ui", response_class=HTMLResponse, include_in_schema=False)
async def admin_ui(request: Request, response: Response):
    """Internal admin UI — document management dashboard."""
    user = await get_optional_user(request)
    if not user:
        return RedirectResponse(url="/login?return_to=/ui", status_code=303)
        
    name = user.get("name")
    preferred_username = user.get("preferred_username")
    
    display_name = name if name else preferred_username
    display_email = preferred_username if name and preferred_username else ""
    
    safe_name = html.escape(display_name or "")
    safe_email = html.escape(display_email or "")
    safe_initials = html.escape(get_initials(str(display_name or "")))
    
    user_html = f"""
    <div class="user-profile">
      <div class="user-avatar" title="{safe_name}">{safe_initials}</div>
      <div class="user-info">
        <div class="user-name" title="{safe_name}">{safe_name}</div>
    """
    if safe_email:
        user_html += f'        <div class="user-email" title="{safe_email}">{safe_email}</div>\n'
        
    user_html += """      </div>
      <form method="post" action="/auth/logout" style="margin: 0; padding: 0; display: flex;">
        <button type="submit" class="btn-signout" aria-label="Sign out">Sign out</button>
      </form>
    </div>
    """
        
    escaped_url_json = json.dumps(settings.HERMES_WEBUI_URL)
    html_content = _UI_HTML.replace("{hermes_webui_url_json}", escaped_url_json)
    html_content = html_content.replace("{user_profile_html}", user_html)
    
    response = HTMLResponse(content=html_content, status_code=200)
    response.headers["Cache-Control"] = "no-store"
    return response


@router.get("/login", response_class=HTMLResponse, include_in_schema=False)
async def login_page(
    request: Request,
    response: Response,
    return_to: Optional[str] = None,
    error: Optional[str] = None,
    logged_out: Optional[str] = None
):
    """Public login page."""
    # Check if already authenticated
    user = await get_optional_user(request)
    if user:
        return RedirectResponse(url="/ui", status_code=303)
        
    message_html = ""
    if logged_out == "1":
        message_html = '<div class="message success">You have been signed out successfully.</div>'
    elif error:
        error_msgs = {
            "access_denied": "Authentication was cancelled or administrator approval is required. Please try again or contact your administrator.",
            "session_expired": "Your login session expired. Please try again.",
            "auth_failed": "An error occurred during authentication. Please try again."
        }
        safe_msg = error_msgs.get(error, "An error occurred during authentication. Please try again.")
        message_html = f'<div class="message error">{safe_msg}</div>'

    # Build auth URL
    auth_url = "/auth/login"
    if return_to:
        auth_url += f"?return_to={urllib.parse.quote(return_to, safe='')}"
        
    html_content = _LOGIN_HTML.replace("{message_html}", message_html)
    html_content = html_content.replace("{auth_url}", html.escape(auth_url))
    
    response = HTMLResponse(content=html_content, status_code=200)
    response.headers["Cache-Control"] = "no-store"
    return response
