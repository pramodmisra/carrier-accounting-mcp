"""
Monitoring routes — daily metrics, carrier accuracy, run history.
Maps to MCP tools: daily_metrics, carrier_accuracy, run_history
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query

from api.auth import AuthenticatedUser, get_current_user
from api.dependencies import get_bq_client

router = APIRouter(prefix="/api", tags=["Monitoring"])


@router.get("/metrics/daily")
async def get_daily_metrics(
    target_date: Optional[str] = Query(None, description="YYYY-MM-DD, defaults to today"),
    user: AuthenticatedUser = Depends(get_current_user),
    bq=Depends(get_bq_client),
) -> dict:
    """Get the daily accuracy scorecard."""
    parsed_date = None
    if target_date:
        from dateutil.parser import parse as dp
        parsed_date = dp(target_date).date()
    return bq.get_daily_metrics(parsed_date)


@router.get("/metrics/carrier/{carrier}")
async def get_carrier_accuracy(
    carrier: str,
    days: int = Query(30, ge=1, le=365),
    user: AuthenticatedUser = Depends(get_current_user),
    bq=Depends(get_bq_client),
) -> dict:
    """Get accuracy metrics for a specific carrier over N days."""
    return bq.get_carrier_accuracy(carrier, days)


@router.get("/runs")
async def get_run_history(
    days: int = Query(7, ge=1, le=90),
    user: AuthenticatedUser = Depends(get_current_user),
) -> list[dict]:
    """Get recent ingestion run history."""
    from mcp_server.tools.monitoring import get_run_history as _history
    return _history(days)


@router.get("/runs/{run_id}")
async def get_run_detail(
    run_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
    bq=Depends(get_bq_client),
) -> dict:
    """Get detailed information about a specific run."""
    from mcp_server.config import Config
    from google.cloud.bigquery import QueryJobConfig, ScalarQueryParameter

    # Get run log
    run_query = f"""
        SELECT * FROM `{Config.run_log_table()}`
        WHERE run_id = @run_id
    """
    job_config = QueryJobConfig(
        query_parameters=[ScalarQueryParameter("run_id", "STRING", run_id)]
    )
    run_rows = list(bq.client.query(run_query, job_config=job_config).result())
    run_info = dict(run_rows[0]) if run_rows else {}

    # Get transactions for this run
    txn_query = f"""
        SELECT
            transaction_id, carrier, policy_number, client_name,
            amount, transaction_type, confidence_score, status,
            epic_entry_id, validation_warnings, validation_errors
        FROM `{Config.shadow_table()}`
        WHERE run_id = @run_id
        UNION ALL
        SELECT
            transaction_id, carrier, policy_number, client_name,
            amount, transaction_type, confidence_score, status,
            epic_entry_id, validation_warnings, validation_errors
        FROM `{Config.live_table()}`
        WHERE run_id = @run_id
        ORDER BY confidence_score DESC
    """
    txn_rows = list(bq.client.query(txn_query, job_config=job_config).result())

    return {
        "run": run_info,
        "transactions": [dict(r) for r in txn_rows],
        "transaction_count": len(txn_rows),
    }
