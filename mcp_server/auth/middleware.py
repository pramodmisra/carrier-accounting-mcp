"""
JWT verification middleware for MCP requests.
Validates Auth0 access tokens on every MCP tool call.
"""

import os
import logging
from typing import Optional

import httpx
from jose import jwt, JWTError, jwk
from jose.utils import base64url_decode

logger = logging.getLogger("5gvector.mcp.auth")

AUTH0_DOMAIN = os.getenv("AUTH0_DOMAIN", "dev-84h8qxuqxtxik8x7.us.auth0.com")
AUTH0_AUDIENCE = os.getenv("AUTH0_AUDIENCE", "https://mcp.5gvector.com/carrier-accounting")
JWKS_URL = f"https://{AUTH0_DOMAIN}/.well-known/jwks.json"

# Cache JWKS
_jwks_cache: Optional[dict] = None


async def get_jwks() -> dict:
    """Fetch and cache the Auth0 JWKS (JSON Web Key Set)."""
    global _jwks_cache
    if _jwks_cache is not None:
        return _jwks_cache

    async with httpx.AsyncClient() as client:
        response = await client.get(JWKS_URL)
        _jwks_cache = response.json()
    return _jwks_cache


def verify_token_sync(token: str) -> Optional[dict]:
    """
    Synchronously verify a JWT access token.
    Returns the decoded payload if valid, None if invalid.
    For use in non-async contexts.
    """
    try:
        # Decode without verification first to get the kid
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")
        if not kid:
            return None

        # Fetch JWKS synchronously
        import httpx as sync_httpx
        response = sync_httpx.get(JWKS_URL)
        jwks_data = response.json()

        # Find the matching key
        rsa_key = None
        for key in jwks_data.get("keys", []):
            if key.get("kid") == kid:
                rsa_key = key
                break

        if not rsa_key:
            return None

        # Verify the token
        payload = jwt.decode(
            token,
            rsa_key,
            algorithms=["RS256"],
            audience=AUTH0_AUDIENCE,
            issuer=f"https://{AUTH0_DOMAIN}/",
        )
        return payload

    except JWTError as e:
        logger.warning("JWT verification failed: %s", e)
        return None
    except Exception as e:
        logger.warning("Token verification error: %s", e)
        return None


def extract_bearer_token(authorization: str) -> Optional[str]:
    """Extract token from 'Bearer xxx' header value."""
    if not authorization:
        return None
    parts = authorization.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    return None
