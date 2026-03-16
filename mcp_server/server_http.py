"""
Production MCP Server with Streamable HTTP transport.
This is the deployment entrypoint for Railway / cloud hosting.

Adds to the base server.py:
- Streamable HTTP transport (required for Anthropic MCP Directory)
- /health endpoint
- CORS for claude.ai, claude.com
- Stateless mode for horizontal scaling

Usage:
  # HTTP mode (production / directory submission)
  uvicorn mcp_server.server_http:app --host 0.0.0.0 --port ${PORT:-8000}

  # stdio mode (local Claude Desktop / Claude Code)
  carrier-accounting-mcp
"""

import os
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

# Import the MCP server instance with all tools already registered
from mcp_server.server import mcp


# ── CORS middleware for Claude platforms ──
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "https://claude.ai,https://claude.com,http://localhost:6274").split(",")

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

# ── Health check endpoint ──
@mcp.custom_route("/health", methods=["GET"])
async def health_check(request):
    return JSONResponse({
        "status": "healthy",
        "service": "carrier-accounting-mcp",
        "version": "0.1.0",
        "tools": 21,
        "carriers": 48,
        "transport": "streamable-http",
    })


# ── ASGI app for uvicorn / Railway ──
app = mcp.http_app(
    path="/mcp",
    middleware=middleware,
    stateless_http=True,
)


# ── Direct run ──
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    print(f"Starting Carrier Accounting MCP Server (HTTP)")
    print(f"  URL: http://0.0.0.0:{port}")
    print(f"  MCP endpoint: http://0.0.0.0:{port}/mcp")
    print(f"  Health: http://0.0.0.0:{port}/health")
    print(f"  CORS origins: {ALLOWED_ORIGINS}")
    print(f"  Mode: stateless HTTP")
    print()
    uvicorn.run(app, host="0.0.0.0", port=port)
