"""Health check routes — no auth required."""

from fastapi import APIRouter

router = APIRouter(tags=["Health"])


@router.get("/api/health")
async def health():
    return {"status": "healthy", "service": "carrier-accounting-mcp"}


@router.get("/api/ready")
async def readiness():
    """Check if the service is ready (BQ connection, etc.)."""
    checks = {"api": True, "bigquery": False, "epic": False}

    try:
        from mcp_server.services.bigquery_client import BigQueryClient
        bq = BigQueryClient()
        bq.client.query("SELECT 1").result()
        checks["bigquery"] = True
    except Exception:
        pass

    try:
        from mcp_server.services.epic_sdk_client import EpicSDKClient
        epic = EpicSDKClient()
        checks["epic"] = bool(epic.base_url)
    except Exception:
        pass

    overall = all(checks.values())
    return {"ready": overall, "checks": checks}
