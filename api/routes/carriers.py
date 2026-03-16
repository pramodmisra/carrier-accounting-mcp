"""
Carrier management routes — list, add, update carrier configurations.
Maps to MCP tool: list_supported_carriers + CRUD operations
"""

from fastapi import APIRouter, Depends, HTTPException

from api.auth import AuthenticatedUser, require_role
from api.models.schemas import CarrierConfig, CarrierListResponse
from platform_db.models import UserRole

router = APIRouter(prefix="/api", tags=["Carrier Management"])


@router.get("/carriers", response_model=CarrierListResponse)
async def list_carriers(
    user: AuthenticatedUser = Depends(require_role(UserRole.VIEWER)),
) -> dict:
    """List all configured carriers with their field mappings."""
    from mcp_server.schemas.carrier_schemas import CARRIER_REGISTRY

    carriers = []
    for slug, schema in CARRIER_REGISTRY.items():
        carriers.append({
            "carrier_slug": schema.carrier_slug,
            "display_name": schema.carrier_display_name,
            "policy_number_field": schema.policy_number_field,
            "client_name_field": schema.client_name_field,
            "premium_field": schema.premium_field,
            "commission_field": schema.commission_field,
            "effective_date_field": schema.effective_date_field,
            "date_format": schema.date_format,
            "portal_url": schema.portal_url,
            "mode": "trial",
        })

    return {"carriers": carriers, "total": len(carriers)}


@router.get("/carriers/{slug}")
async def get_carrier(
    slug: str,
    user: AuthenticatedUser = Depends(require_role(UserRole.VIEWER)),
) -> dict:
    """Get details for a specific carrier."""
    from mcp_server.schemas.carrier_schemas import get_carrier_schema, CARRIER_REGISTRY

    if slug not in CARRIER_REGISTRY:
        raise HTTPException(404, f"Carrier '{slug}' not found")

    schema = get_carrier_schema(slug)
    return {
        "carrier_slug": schema.carrier_slug,
        "display_name": schema.carrier_display_name,
        "policy_number_field": schema.policy_number_field,
        "client_name_field": schema.client_name_field,
        "premium_field": schema.premium_field,
        "commission_field": schema.commission_field,
        "effective_date_field": schema.effective_date_field,
        "date_format": schema.date_format,
        "portal_url": schema.portal_url,
        "portal_login_selector": schema.portal_login_selector,
        "portal_download_selector": schema.portal_download_selector,
        "has_header_row": schema.has_header_row,
        "skip_rows_top": schema.skip_rows_top,
        "skip_rows_bottom": schema.skip_rows_bottom,
    }


@router.post("/carriers")
async def add_carrier(
    config: CarrierConfig,
    user: AuthenticatedUser = Depends(require_role(UserRole.ADMIN)),
) -> dict:
    """Add a new carrier configuration. Admin only."""
    from mcp_server.schemas.carrier_schemas import CARRIER_REGISTRY, CarrierSchema

    if config.carrier_slug in CARRIER_REGISTRY:
        raise HTTPException(409, f"Carrier '{config.carrier_slug}' already exists")

    schema = CarrierSchema(
        carrier_slug=config.carrier_slug,
        carrier_display_name=config.display_name,
        policy_number_field=config.policy_number_field,
        client_name_field=config.client_name_field,
        premium_field=config.premium_field,
        commission_field=config.commission_field,
        effective_date_field=config.effective_date_field,
        date_format=config.date_format,
        portal_url=config.portal_url,
    )
    CARRIER_REGISTRY[config.carrier_slug] = schema

    return {
        "status": "created",
        "carrier_slug": config.carrier_slug,
        "message": f"Carrier '{config.display_name}' added. Run trial mode before enabling live.",
    }


@router.put("/carriers/{slug}")
async def update_carrier(
    slug: str,
    config: CarrierConfig,
    user: AuthenticatedUser = Depends(require_role(UserRole.ADMIN)),
) -> dict:
    """Update a carrier's field mappings. Admin only."""
    from mcp_server.schemas.carrier_schemas import CARRIER_REGISTRY, CarrierSchema

    if slug not in CARRIER_REGISTRY:
        raise HTTPException(404, f"Carrier '{slug}' not found")

    schema = CarrierSchema(
        carrier_slug=slug,
        carrier_display_name=config.display_name,
        policy_number_field=config.policy_number_field,
        client_name_field=config.client_name_field,
        premium_field=config.premium_field,
        commission_field=config.commission_field,
        effective_date_field=config.effective_date_field,
        date_format=config.date_format,
        portal_url=config.portal_url,
    )
    CARRIER_REGISTRY[slug] = schema

    return {"status": "updated", "carrier_slug": slug}
