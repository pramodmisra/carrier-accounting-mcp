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


# ── Build the ASGI app ──
# MCP app handles /mcp endpoint
mcp_app = mcp.http_app(path="/mcp", stateless_http=True)

# Combine: OAuth routes at root + MCP at /mcp + health
app = Starlette(
    routes=[
        Route("/health", health_check, methods=["GET"]),
        *oauth_routes,  # /authorize, /oauth/callback, /oauth/token, /.well-known/...
        Mount("/", app=mcp_app),  # MCP protocol at /mcp
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
