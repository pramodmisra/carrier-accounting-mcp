"""
Admin routes — tenant management, user management, system settings.
All routes require admin role.
"""

from fastapi import APIRouter, Depends, HTTPException

from api.auth import AuthenticatedUser, require_role
from api.models.schemas import TenantCreate, TenantResponse
from platform_db.models import UserRole

router = APIRouter(prefix="/api/admin", tags=["Admin"])


@router.post("/tenants", response_model=TenantResponse)
async def create_tenant(
    request: TenantCreate,
    user: AuthenticatedUser = Depends(require_role(UserRole.ADMIN)),
) -> dict:
    """
    Onboard a new insurance agency.
    Creates BQ datasets, provisions tables, and creates the admin user.
    """
    # In production, this would use the platform DB session
    # For now, return a structured response showing what would be created
    return {
        "tenant_id": f"tenant_{request.slug}",
        "slug": request.slug,
        "display_name": request.display_name,
        "status": "provisioning",
        "plan": request.plan,
        "created_at": None,
        "message": f"Tenant '{request.display_name}' creation initiated. "
                   f"BQ datasets: {request.slug}_carrier_accounting, {request.slug}_staging",
    }


@router.get("/tenants")
async def list_tenants(
    user: AuthenticatedUser = Depends(require_role(UserRole.ADMIN)),
) -> list[dict]:
    """List all tenants (platform admin only)."""
    return []


@router.get("/tenants/{slug}")
async def get_tenant(
    slug: str,
    user: AuthenticatedUser = Depends(require_role(UserRole.ADMIN)),
) -> dict:
    """Get tenant details including provisioning status."""
    return {"slug": slug, "status": "active"}


@router.post("/tenants/{slug}/users")
async def add_user(
    slug: str,
    email: str,
    role: str = "viewer",
    user: AuthenticatedUser = Depends(require_role(UserRole.ADMIN)),
) -> dict:
    """Add a user to a tenant."""
    return {
        "tenant": slug,
        "email": email,
        "role": role,
        "status": "invited",
    }


@router.get("/settings")
async def get_settings(
    user: AuthenticatedUser = Depends(require_role(UserRole.ADMIN)),
) -> dict:
    """Get current system settings."""
    from mcp_server.config import Config
    return {
        "gcp_project": Config.GCP_PROJECT,
        "bq_dataset": Config.BQ_DATASET,
        "epic_environment": Config.EPIC_ENVIRONMENT,
        "auto_post_threshold": Config.AUTO_POST_THRESHOLD,
        "review_threshold": Config.REVIEW_THRESHOLD,
        "default_mode": Config.DEFAULT_MODE,
    }
