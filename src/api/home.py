"""Public homepage endpoint and template."""

from typing import Optional
import html
from fastapi import APIRouter, Request, Query
from fastapi.responses import HTMLResponse

router = APIRouter()

_HOME_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Knowledge Base API — Home</title>
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
      flex-direction: column;
      background-image:
        radial-gradient(at 0% 0%, rgba(99, 102, 241, 0.08) 0px, transparent 50%),
        radial-gradient(at 100% 100%, rgba(79, 70, 229, 0.05) 0px, transparent 50%);
      background-attachment: fixed;
    }

    /* Header */
    header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 1.5rem 2rem;
      max-width: 1200px;
      margin: 0 auto;
      width: 100%;
    }
    .brand h1 {
      font-family: 'Outfit', sans-serif;
      font-size: 1.5rem;
      font-weight: 700;
      background: linear-gradient(135deg, #a5b4fc 0%, #6366f1 50%, #4338ca 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
      letter-spacing: -0.02em;
    }
    .btn-header {
      background: rgba(255,255,255,0.05);
      border: 1px solid var(--border);
      color: var(--text);
      padding: 0.5rem 1rem;
      border-radius: var(--radius-sm);
      text-decoration: none;
      font-weight: 600;
      font-size: 0.9rem;
      transition: all 0.2s ease;
    }
    .btn-header:hover {
      background: rgba(255,255,255,0.1);
      border-color: #444;
    }

    /* Main Container */
    main {
      flex: 1;
      display: flex;
      flex-direction: column;
      align-items: center;
      width: 100%;
      max-width: 1200px;
      margin: 0 auto;
      padding: 4rem 2rem;
    }

    /* Hero Section */
    .hero {
      display: grid;
      grid-template-columns: 1fr;
      gap: 4rem;
      width: 100%;
      align-items: center;
      margin-bottom: 6rem;
    }
    @media (min-width: 900px) {
      .hero {
        grid-template-columns: 1fr 1fr;
      }
    }

    .hero-text h2 {
      font-family: 'Outfit', sans-serif;
      font-size: 3rem;
      line-height: 1.1;
      margin-bottom: 1.5rem;
      font-weight: 700;
    }
    .hero-text p {
      color: var(--muted);
      font-size: 1.1rem;
      line-height: 1.6;
      margin-bottom: 2.5rem;
      max-width: 500px;
    }
    .hero-cta {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      background: var(--accent);
      color: white;
      text-decoration: none;
      padding: 0.8rem 1.5rem;
      border-radius: var(--radius-sm);
      font-weight: 600;
      font-size: 1rem;
      transition: all 0.2s ease;
      box-shadow: 0 4px 14px rgba(99, 102, 241, 0.4);
    }
    .hero-cta:hover {
      background: var(--accent-h);
      box-shadow: 0 6px 20px rgba(99, 102, 241, 0.6);
      transform: translateY(-1px);
    }

    /* How it works */
    .how-it-works {
      width: 100%;
      max-width: 1000px;
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 3rem;
      box-shadow: 0 20px 40px -15px rgba(0, 0, 0, 0.85);
    }
    .how-it-works h3 {
      font-family: 'Outfit', sans-serif;
      font-size: 1.8rem;
      margin-bottom: 2rem;
      text-align: center;
    }
    .steps {
      display: grid;
      grid-template-columns: 1fr;
      gap: 1.5rem;
    }
    @media (min-width: 600px) {
      .steps { grid-template-columns: 1fr 1fr; }
    }
    .step {
      display: flex;
      gap: 1rem;
      align-items: flex-start;
    }
    .step-num {
      flex-shrink: 0;
      width: 32px;
      height: 32px;
      border-radius: 50%;
      background: rgba(99, 102, 241, 0.15);
      color: var(--accent);
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 700;
      font-size: 1rem;
    }
    .step-text {
      color: var(--text);
      font-size: 0.95rem;
      line-height: 1.5;
      padding-top: 4px;
    }

    /* Animation Styles */
    .animation-wrapper {
      position: relative;
      width: 100%;
      max-width: 500px;
      aspect-ratio: 1 / 1;
      margin: 0 auto;
      display: flex;
      align-items: center;
      justify-content: center;
    }
    .flow-grid {
      display: flex;
      align-items: center;
      justify-content: space-between;
      width: 100%;
      height: 100%;
      position: relative;
    }

    .col-docs {
      display: flex;
      flex-direction: column;
      gap: 1rem;
      z-index: 2;
    }
    .anim-card {
      background: rgba(16, 21, 32, 0.8);
      border: 1px solid var(--border);
      padding: 0.75rem 1rem;
      border-radius: var(--radius-sm);
      font-size: 0.85rem;
      color: var(--muted);
      text-align: center;
      box-shadow: 0 4px 10px rgba(0,0,0,0.5);
      backdrop-filter: blur(4px);
    }

    .col-process {
      position: absolute;
      left: 50%;
      top: 50%;
      transform: translate(-50%, -50%);
      z-index: 2;
      display: flex;
      align-items: center;
      justify-content: center;
    }
    .ai-node {
      width: 120px;
      height: 120px;
      border-radius: 50%;
      background: linear-gradient(135deg, rgba(99, 102, 241, 0.2), rgba(67, 56, 202, 0.4));
      border: 2px solid var(--accent);
      display: flex;
      align-items: center;
      justify-content: center;
      text-align: center;
      font-size: 0.85rem;
      font-weight: 600;
      color: #fff;
      box-shadow: 0 0 30px rgba(99, 102, 241, 0.3);
    }

    .col-answer {
      z-index: 2;
    }
    .answer-card {
      background: rgba(16, 21, 32, 0.9);
      border: 1px solid var(--accent);
      padding: 1rem 1.25rem;
      border-radius: var(--radius-sm);
      font-size: 0.9rem;
      color: #fff;
      font-weight: 600;
      box-shadow: 0 10px 25px rgba(99, 102, 241, 0.2);
    }

    /* Lines and Particles */
    .connection-lines {
      position: absolute;
      top: 0; left: 0; right: 0; bottom: 0;
      z-index: 1;
    }
    .line {
      position: absolute;
      height: 2px;
      background: linear-gradient(90deg, rgba(38, 51, 69, 0), rgba(38, 51, 69, 1), rgba(38, 51, 69, 0));
      top: 50%;
      transform: translateY(-50%);
    }
    .line-left { left: 10%; right: 50%; }
    .line-right { left: 50%; right: 10%; }

    .particle {
      position: absolute;
      width: 6px;
      height: 6px;
      background: #22d3ee;
      border-radius: 50%;
      box-shadow: 0 0 10px #22d3ee;
      top: 50%;
      transform: translateY(-50%);
      opacity: 0;
    }

    /* Banner */
    .banner {
      width: 100%;
      background: rgba(34, 197, 94, 0.1);
      border: 1px solid rgba(34, 197, 94, 0.4);
      color: #4ade80;
      padding: 1rem 1.5rem;
      border-radius: var(--radius-sm);
      margin-bottom: 2rem;
      font-weight: 500;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .banner-close {
      background: none;
      border: none;
      color: inherit;
      font-size: 1.5rem;
      line-height: 1;
      cursor: pointer;
      opacity: 0.8;
      padding: 0 0.5rem;
    }
    .banner-close:hover { opacity: 1; }

    /* Animations */
    @keyframes float {
      0%, 100% { transform: translateY(0); }
      50% { transform: translateY(-5px); }
    }
    @keyframes pulse {
      0%, 100% { box-shadow: 0 0 30px rgba(99, 102, 241, 0.3); transform: scale(1); }
      50% { box-shadow: 0 0 50px rgba(99, 102, 241, 0.6); transform: scale(1.05); }
    }
    @keyframes moveRight {
      0% { left: 15%; opacity: 0; }
      20% { opacity: 1; }
      80% { opacity: 1; }
      100% { left: 50%; opacity: 0; }
    }
    @keyframes moveRightAnswer {
      0% { left: 50%; opacity: 0; }
      20% { opacity: 1; }
      80% { opacity: 1; }
      100% { left: 85%; opacity: 0; }
    }
    @keyframes reveal {
      0%, 50% { opacity: 0.3; transform: scale(0.95); }
      70%, 100% { opacity: 1; transform: scale(1); }
    }

    .float-1 { animation: float 4s ease-in-out infinite; }
    .float-2 { animation: float 4s ease-in-out infinite 1s; }
    .float-3 { animation: float 4s ease-in-out infinite 2s; }
    .ai-node { animation: pulse 3s ease-in-out infinite; }
    .answer-card { animation: reveal 4s ease-in-out infinite; }

    .p1 { animation: moveRight 3s linear infinite; }
    .p2 { animation: moveRight 3s linear infinite 1s; }
    .p3 { animation: moveRight 3s linear infinite 2s; }
    .p4 { animation: moveRightAnswer 3s linear infinite 1.5s; }

    /* Reduced motion fallback */
    @media (prefers-reduced-motion: reduce) {
      .float-1, .float-2, .float-3, .ai-node, .answer-card {
        animation: none !important;
        transform: none !important;
        opacity: 1 !important;
        box-shadow: 0 0 20px rgba(99, 102, 241, 0.3) !important;
      }
      .particle {
        display: none !important;
        animation: none !important;
      }
    }
  </style>
</head>
<body>
  <header>
    <div class="brand">
      <h1>Leadgen Assistant</h1>
    </div>
    <a href="{btn_url}" class="btn-header">{btn_text}</a>
  </header>

  <main>
{banner}
    <section class="hero">
      <div class="hero-text">
        <h2>Turn company knowledge into an AI-powered workspace</h2>
        <p>Leadgen Assistant helps authorized teams securely access company knowledge, find relevant information, and work with an AI assistant grounded in approved business content.</p>
        <a href="{btn_url}" class="hero-cta">{btn_text}</a>
      </div>

      <div class="animation-wrapper" aria-hidden="true">
        <div class="connection-lines">
          <div class="line line-left">
            <div class="particle p1"></div>
            <div class="particle p2"></div>
            <div class="particle p3"></div>
          </div>
          <div class="line line-right">
            <div class="particle p4"></div>
          </div>
        </div>
        <div class="flow-grid">
          <div class="col-docs">
            <div class="anim-card float-1">Policy</div>
            <div class="anim-card float-2">Product Guide</div>
            <div class="anim-card float-3">Research</div>
          </div>
          <div class="col-process">
            <div class="ai-node">
              <span>Company Knowledge</span>
            </div>
          </div>
          <div class="col-answer">
            <div class="answer-card">Grounded Answer</div>
          </div>
        </div>
      </div>
    </section>

    <section class="how-it-works">
      <h3>How it works</h3>
      <div class="steps">
        <div class="step">
          <div class="step-num">1</div>
          <div class="step-text">Sign in with your organization’s Microsoft account.</div>
        </div>
        <div class="step">
          <div class="step-num">2</div>
          <div class="step-text">Access the company knowledge available to you.</div>
        </div>
        <div class="step">
          <div class="step-num">3</div>
          <div class="step-text">Search or ask questions in natural language.</div>
        </div>
        <div class="step">
          <div class="step-num">4</div>
          <div class="step-text">Receive answers grounded in approved company content.</div>
        </div>
      </div>
    </section>
  </main>
</body>
</html>"""


@router.get("/")
async def home_page(request: Request, logged_out: Optional[str] = Query(None)):
    """
    Public homepage with knowledge-flow animation.
    Does not render internal data. Caching is disabled to prevent
    authenticated/unauthenticated state mixups.
    """
    user = request.session.get("user")

    if user:
        btn_text = "Open Console"
        btn_url = "/ui"
    else:
        btn_text = "Sign in with Microsoft"
        btn_url = "/login?return_to=/ui"

    banner_html = ""
    if not user and logged_out == "1":
        banner_html = """
    <div class="banner" role="status" id="logout-banner">
      <span>You have been signed out successfully.</span>
      <button class="banner-close" aria-label="Close" onclick="document.getElementById('logout-banner').remove()">×</button>
    </div>"""

    html_content = _HOME_HTML.replace("{btn_text}", html.escape(btn_text))
    html_content = html_content.replace("{btn_url}", html.escape(btn_url))
    html_content = html_content.replace("{banner}", banner_html)

    return HTMLResponse(
        content=html_content, headers={"Cache-Control": "private, no-store"}
    )
