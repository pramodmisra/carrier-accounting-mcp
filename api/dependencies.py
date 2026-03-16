"""
FastAPI dependency injection — resolved per-request.
Provides tenant-scoped config, BigQuery client, and services.
"""

from fastapi import Depends

from api.auth import AuthenticatedUser, get_current_user
from platform_db.tenant_context import TenantContext, set_tenant
from mcp_server.config import Config


async def get_tenant_config(
    user: AuthenticatedUser = Depends(get_current_user),
) -> TenantContext:
    """
    Resolve the tenant configuration for the current request.
    In single-tenant mode (no platform DB), falls back to env-var Config.
    In multi-tenant mode, looks up the tenant from the platform database.
    """
    # Multi-tenant path: look up tenant from platform DB
    # For now, construct from environment (single-tenant compatible)
    ctx = TenantContext(
        tenant_id=user.tenant_id or "default",
        tenant_slug=user.tenant_id or "default",
        display_name="Default Agency",
        gcp_project=Config.GCP_PROJECT,
        bq_dataset=Config.BQ_DATASET,
        bq_staging_dataset=Config.BQ_STAGING_DATASET,
        epic_sdk_url=Config.EPIC_SDK_URL,
        epic_api_key=Config.EPIC_API_KEY,
        epic_agency_id=Config.EPIC_AGENCY_ID,
        epic_environment=Config.EPIC_ENVIRONMENT,
        anthropic_api_key=Config.ANTHROPIC_API_KEY,
        auto_post_threshold=Config.AUTO_POST_THRESHOLD,
        review_threshold=Config.REVIEW_THRESHOLD,
        default_mode=Config.DEFAULT_MODE,
    )
    set_tenant(ctx)
    return ctx


async def get_bq_client(
    tenant: TenantContext = Depends(get_tenant_config),
):
    """Return a BigQuery client scoped to the current tenant."""
    from mcp_server.services.bigquery_client import BigQueryClient
    return BigQueryClient()
