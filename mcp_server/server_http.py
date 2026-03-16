"""
Production MCP Server with Streamable HTTP transport + OAuth 2.0.
This is the deployment entrypoint for Railway / cloud hosting.

Features:
- Streamable HTTP transport (required for Anthropic MCP Directory)
- OAuth 2.0 authorization code flow via Auth0
- /health endpoint
- /.well-known/oauth-authorization-server metadata
- CORS for claude.ai, claude.com
- Stateless mode for horizontal scaling

Usage:
  uvicorn mcp_server.server_http:app --host 0.0.0.0 --port ${PORT:-8000}
"""

import os
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

# Import the MCP server instance with all tools registered
from mcp_server.server import mcp
from mcp_server.auth.oauth import oauth_routes


# ── CORS ──
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "https://claude.ai,https://claude.com,http://localhost:6274"
).split(",")

middleware = [
    Middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*", "mcp-protocol-version", "mcp-session-id", "Authorization"],
        expose_headers=["mcp-session-id"],
    )
]


# ── Health check ──
async def health_check(request):
    return JSONResponse({
        "status": "healthy",
        "service": "carrier-accounting-mcp",
        "version": "0.1.0",
        "tools": 21,
        "carriers": 48,
        "transport": "streamable-http",
        "auth": "oauth2",
    })


# ── Landing page ──
async def landing_page(request):
    from starlette.responses import HTMLResponse
    return HTMLResponse("""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>5G Vector — Carrier Accounting MCP Server</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f8fafc; color: #0f172a; }
  .container { max-width: 720px; margin: 0 auto; padding: 60px 24px; }
  .logo { display: flex; align-items: center; gap: 10px; margin-bottom: 32px; }
  .logo-icon { width: 40px; height: 40px; background: #2563eb; border-radius: 10px; display: flex; align-items: center; justify-content: center; }
  .logo-icon svg { width: 22px; height: 22px; }
  .logo-text { font-size: 22px; font-weight: 700; color: #2563eb; }
  h1 { font-size: 32px; font-weight: 700; line-height: 1.2; margin-bottom: 12px; }
  .subtitle { font-size: 17px; color: #64748b; margin-bottom: 36px; line-height: 1.5; }
  .card { background: white; border: 1px solid #e2e8f0; border-radius: 12px; padding: 24px; margin-bottom: 16px; }
  .card h3 { font-size: 15px; font-weight: 600; margin-bottom: 8px; }
  .card p { font-size: 14px; color: #64748b; line-height: 1.5; }
  .stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 32px; }
  .stat { background: white; border: 1px solid #e2e8f0; border-radius: 10px; padding: 16px; text-align: center; }
  .stat .num { font-size: 28px; font-weight: 700; color: #2563eb; font-family: 'JetBrains Mono', monospace; }
  .stat .label { font-size: 12px; color: #64748b; margin-top: 2px; }
  .endpoints { background: #0f172a; border-radius: 10px; padding: 20px; margin: 24px 0; font-family: monospace; font-size: 13px; color: #94a3b8; line-height: 1.8; }
  .endpoints .url { color: #38bdf8; }
  .endpoints .method { color: #a78bfa; font-weight: 600; }
  .footer { margin-top: 40px; padding-top: 24px; border-top: 1px solid #e2e8f0; font-size: 13px; color: #94a3b8; }
  .footer a { color: #2563eb; text-decoration: none; }
  a { color: #2563eb; }
</style>
</head>
<body>
<div class="container">
  <div class="logo">
    <div class="logo-icon"><svg viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/></svg></div>
    <span class="logo-text">5G Vector</span>
  </div>

  <h1>Carrier Accounting MCP Server</h1>
  <p class="subtitle">AI-powered carrier commission statement processing for US insurance agencies using Applied Epic. Parse PDFs, Excel, and CSV statements from 48+ carriers with 99.5% reconciliation accuracy.</p>

  <div class="stats">
    <div class="stat"><div class="num">21</div><div class="label">MCP Tools</div></div>
    <div class="stat"><div class="num">48+</div><div class="label">Carriers</div></div>
    <div class="stat"><div class="num">99.5%</div><div class="label">Match Rate</div></div>
  </div>

  <div class="card">
    <h3>Ingestion</h3>
    <p>Upload carrier PDFs, Excel, or CSV statements. AI extracts policy numbers, insured names, premiums, commissions, and dates — handling 3 negative formats, 4 rate encodings, and carrier-specific quirks automatically.</p>
  </div>
  <div class="card">
    <h3>5-Layer Reconciliation</h3>
    <p>Multi-strategy policy matching, self-learning mappings, client name scanning, amount+date triangulation, and AI-powered resolution. Every human approval teaches the system for next time.</p>
  </div>
  <div class="card">
    <h3>Applied Epic Integration</h3>
    <p>Post accounting entries via REST API, Playwright UI automation, or CSV batch import. Trial mode lets you test with zero Epic writes. Full rollback support.</p>
  </div>
  <div class="card">
    <h3>Monitoring &amp; Reports</h3>
    <p>Daily accuracy scorecard, per-carrier metrics, reconciliation reports, and trial diff analysis. Track auto-reconciliation rate, exception queue, and team performance.</p>
  </div>

  <div class="endpoints">
    <div><span class="method">GET </span> <span class="url">/health</span> — Server status</div>
    <div><span class="method">GET </span> <span class="url">/.well-known/oauth-authorization-server</span> — OAuth metadata</div>
    <div><span class="method">GET </span> <span class="url">/authorize</span> — Start OAuth flow</div>
    <div><span class="method">POST</span> <span class="url">/mcp</span> — MCP protocol endpoint</div>
  </div>

  <div class="card">
    <h3>Connect from Claude</h3>
    <p>Add this MCP server in Claude Desktop, Claude Code, or Claude.ai to start processing carrier statements with AI assistance.</p>
  </div>

  <div class="footer">
    <p><strong>5G Vector Technologies</strong> — Atlanta, GA</p>
    <p style="margin-top: 6px;">
      <a href="https://5gvector.com/carrier-accounting">Full Platform</a> &middot;
      <a href="https://github.com/pramodmisra/carrier-accounting-mcp">GitHub</a> &middot;
      <a href="https://pypi.org/project/carrier-accounting-mcp/">PyPI</a> &middot;
      <a href="mailto:support@5gvector.com">support@5gvector.com</a>
    </p>
  </div>
</div>
</body>
</html>""")


# ── Build the ASGI app ──
# MCP app handles /mcp endpoint
mcp_app = mcp.http_app(path="/mcp", stateless_http=True)

# Combine: landing + OAuth + health + MCP
app = Starlette(
    routes=[
        Route("/", landing_page, methods=["GET"]),
        Route("/health", health_check, methods=["GET"]),
        *oauth_routes,
        Mount("/", app=mcp_app),
    ],
    middleware=middleware,
    lifespan=mcp_app.lifespan,
)


# ── Direct run ──
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    print(f"Starting Carrier Accounting MCP Server (HTTP + OAuth)")
    print(f"  URL: http://0.0.0.0:{port}")
    print(f"  MCP: http://0.0.0.0:{port}/mcp")
    print(f"  Health: http://0.0.0.0:{port}/health")
    print(f"  OAuth metadata: http://0.0.0.0:{port}/.well-known/oauth-authorization-server")
    print(f"  Auth0 domain: {os.getenv('AUTH0_DOMAIN', 'dev-84h8qxuqxtxik8x7.us.auth0.com')}")
    print()
    uvicorn.run(app, host="0.0.0.0", port=port)
