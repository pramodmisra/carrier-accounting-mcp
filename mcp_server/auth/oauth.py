"""
OAuth 2.0 Authorization Code Flow for MCP Directory submission.
Uses Auth0 as the identity provider.

Endpoints:
  GET  /authorize                              → Redirect to Auth0 login
  GET  /oauth/callback                         → Exchange code for tokens
  POST /oauth/token                            → Token refresh
  GET  /.well-known/oauth-authorization-server → OAuth metadata discovery
"""

import os
import secrets
import httpx
from urllib.parse import urlencode

from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse
from starlette.routing import Route

# Auth0 config
AUTH0_DOMAIN = os.getenv("AUTH0_DOMAIN", "dev-84h8qxuqxtxik8x7.us.auth0.com")
AUTH0_CLIENT_ID = os.getenv("AUTH0_CLIENT_ID", "jCROt4KKVPS2s06c8HmVGACMqPyd2Bsc")
AUTH0_CLIENT_SECRET = os.getenv("AUTH0_CLIENT_SECRET", "")
AUTH0_AUDIENCE = os.getenv("AUTH0_AUDIENCE", "https://mcp.5gvector.com/carrier-accounting")

# The public URL of this MCP server (set in Railway env)
SERVER_URL = os.getenv("SERVER_URL", "https://carrier-accounting-mcp-production.up.railway.app")

SCOPES = "openid profile email read:statements read:analytics write:epic write:review"

# In-memory state store for CSRF (use Redis in production for multi-instance)
_state_store: dict[str, str] = {}


async def authorize(request: Request) -> RedirectResponse:
    """Redirect to Auth0 login page."""
    # Get the redirect_uri from the client (Claude sends this)
    redirect_uri = request.query_params.get("redirect_uri", f"{SERVER_URL}/oauth/callback")
    state = secrets.token_urlsafe(32)
    _state_store[state] = redirect_uri

    auth_url = f"https://{AUTH0_DOMAIN}/authorize?" + urlencode({
        "response_type": "code",
        "client_id": AUTH0_CLIENT_ID,
        "redirect_uri": f"{SERVER_URL}/oauth/callback",
        "scope": SCOPES,
        "audience": AUTH0_AUDIENCE,
        "state": state,
    })
    return RedirectResponse(auth_url)


async def oauth_callback(request: Request) -> RedirectResponse:
    """Exchange authorization code for tokens."""
    code = request.query_params.get("code")
    state = request.query_params.get("state")
    error = request.query_params.get("error")

    if error:
        return JSONResponse({"error": error, "description": request.query_params.get("error_description", "")}, status_code=400)

    if not code:
        return JSONResponse({"error": "missing_code"}, status_code=400)

    # Exchange code for tokens
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            f"https://{AUTH0_DOMAIN}/oauth/token",
            json={
                "grant_type": "authorization_code",
                "client_id": AUTH0_CLIENT_ID,
                "client_secret": AUTH0_CLIENT_SECRET,
                "code": code,
                "redirect_uri": f"{SERVER_URL}/oauth/callback",
            },
        )

    if token_response.status_code != 200:
        return JSONResponse({"error": "token_exchange_failed", "detail": token_response.text}, status_code=400)

    tokens = token_response.json()

    # Get the original redirect_uri from state
    original_redirect = _state_store.pop(state, None)
    if original_redirect and original_redirect != f"{SERVER_URL}/oauth/callback":
        # Redirect back to the MCP client (Claude) with the tokens
        separator = "&" if "?" in original_redirect else "?"
        return RedirectResponse(
            f"{original_redirect}{separator}access_token={tokens.get('access_token', '')}"
            f"&token_type=bearer"
            f"&expires_in={tokens.get('expires_in', 3600)}"
        )

    # If no redirect, return tokens directly (for testing)
    return JSONResponse({
        "access_token": tokens.get("access_token"),
        "token_type": "bearer",
        "expires_in": tokens.get("expires_in", 3600),
        "refresh_token": tokens.get("refresh_token"),
        "scope": tokens.get("scope", SCOPES),
    })


async def token_refresh(request: Request) -> JSONResponse:
    """Refresh an access token."""
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "invalid_request"}, status_code=400)

    grant_type = body.get("grant_type")
    refresh_token = body.get("refresh_token")

    if grant_type != "refresh_token" or not refresh_token:
        return JSONResponse({"error": "invalid_grant"}, status_code=400)

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"https://{AUTH0_DOMAIN}/oauth/token",
            json={
                "grant_type": "refresh_token",
                "client_id": AUTH0_CLIENT_ID,
                "client_secret": AUTH0_CLIENT_SECRET,
                "refresh_token": refresh_token,
            },
        )

    if response.status_code != 200:
        return JSONResponse({"error": "refresh_failed"}, status_code=400)

    tokens = response.json()
    return JSONResponse({
        "access_token": tokens.get("access_token"),
        "token_type": "bearer",
        "expires_in": tokens.get("expires_in", 3600),
        "refresh_token": tokens.get("refresh_token", refresh_token),
    })


async def oauth_metadata(request: Request) -> JSONResponse:
    """OAuth 2.0 Authorization Server Metadata (RFC 8414)."""
    return JSONResponse({
        "issuer": f"{SERVER_URL}",
        "authorization_endpoint": f"{SERVER_URL}/authorize",
        "token_endpoint": f"{SERVER_URL}/oauth/token",
        "registration_endpoint": None,
        "scopes_supported": SCOPES.split(),
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code", "refresh_token"],
        "token_endpoint_auth_methods_supported": ["client_secret_post"],
        "service_documentation": "https://5gvector.com/carrier-accounting",
        "code_challenge_methods_supported": ["S256"],
    })


# Starlette routes to mount
oauth_routes = [
    Route("/authorize", authorize, methods=["GET"]),
    Route("/oauth/callback", oauth_callback, methods=["GET"]),
    Route("/oauth/token", token_refresh, methods=["POST"]),
    Route("/.well-known/oauth-authorization-server", oauth_metadata, methods=["GET"]),
]
