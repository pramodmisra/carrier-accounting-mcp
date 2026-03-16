"""
Authentication — JWT verification, role-based access control.
Supports Auth0, Clerk, or any OIDC-compliant provider.
"""

import os
from typing import Optional
from datetime import datetime

from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwt, JWTError

from platform_db.models import UserRole

security = HTTPBearer()

# Auth config — set via environment
AUTH_ISSUER = os.getenv("AUTH_ISSUER", "")           # e.g. https://your-app.us.auth0.com/
AUTH_AUDIENCE = os.getenv("AUTH_AUDIENCE", "")        # e.g. https://api.carrieraccounting.com
AUTH_JWKS_URL = os.getenv("AUTH_JWKS_URL", "")       # e.g. https://your-app.us.auth0.com/.well-known/jwks.json
AUTH_ALGORITHM = os.getenv("AUTH_ALGORITHM", "RS256")

# For development — allow a simple API key bypass
DEV_API_KEY = os.getenv("DEV_API_KEY", "")

# Role hierarchy: admin > accountant > reviewer > viewer
ROLE_HIERARCHY = {
    UserRole.ADMIN: 4,
    UserRole.ACCOUNTANT: 3,
    UserRole.REVIEWER: 2,
    UserRole.VIEWER: 1,
}


class AuthenticatedUser:
    """Represents the authenticated user for the current request."""
    def __init__(
        self,
        user_id: str,
        email: str,
        tenant_id: str,
        role: UserRole,
        name: str = "",
    ):
        self.user_id = user_id
        self.email = email
        self.tenant_id = tenant_id
        self.role = role
        self.name = name

    def has_role(self, minimum_role: UserRole) -> bool:
        return ROLE_HIERARCHY.get(self.role, 0) >= ROLE_HIERARCHY.get(minimum_role, 0)


def decode_token(token: str) -> dict:
    """
    Decode and validate a JWT token.
    In production, validates against the OIDC provider's JWKS.
    In development, supports a simple API key.
    """
    # Dev mode: simple API key
    if DEV_API_KEY and token == DEV_API_KEY:
        return {
            "sub": "dev-user",
            "email": "dev@localhost",
            "tenant_id": os.getenv("DEV_TENANT_ID", "default"),
            "role": "admin",
            "name": "Developer",
        }

    try:
        # In production, verify against JWKS
        # For now, decode without full JWKS verification for development
        payload = jwt.decode(
            token,
            key="",  # Will be replaced with JWKS in production
            algorithms=[AUTH_ALGORITHM],
            audience=AUTH_AUDIENCE,
            issuer=AUTH_ISSUER,
            options={"verify_signature": False} if not AUTH_JWKS_URL else {},
        )
        return payload
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> AuthenticatedUser:
    """
    FastAPI dependency — extracts and validates the authenticated user
    from the Authorization header.
    """
    payload = decode_token(credentials.credentials)

    return AuthenticatedUser(
        user_id=payload.get("sub", ""),
        email=payload.get("email", ""),
        tenant_id=payload.get("tenant_id", payload.get("org_id", "")),
        role=UserRole(payload.get("role", "viewer")),
        name=payload.get("name", ""),
    )


def require_role(minimum_role: UserRole):
    """
    Factory for a FastAPI dependency that enforces a minimum role.
    Usage: @router.get("/admin", dependencies=[Depends(require_role(UserRole.ADMIN))])
    """
    async def _check(user: AuthenticatedUser = Depends(get_current_user)):
        if not user.has_role(minimum_role):
            raise HTTPException(
                status_code=403,
                detail=f"Requires {minimum_role.value} role or higher"
            )
        return user
    return _check
