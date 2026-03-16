"""
Monitoring tools — daily metrics, run history, and carrier accuracy reports.
"""

from datetime import date
from typing import Optional
import structlog

from mcp_server.services.bigquery_client import BigQueryClient

log = structlog.get_logger(__name__)

bq = BigQueryClient()


def get_daily_metrics(target_date: Optional[date] = None) -> dict:
    """Get the daily accuracy scorecard."""
    return bq.get_daily_metrics(target_date)


def get_carrier_accuracy(carrier: str, days: int = 30) -> dict:
    """Get accuracy metrics for a specific carrier."""
    return bq.get_carrier_accuracy(carrier, days)


def get_run_history(days: int = 7) -> list[dict]:
    """Get recent run history from the run_log table."""
    query = f"""
        SELECT *
        FROM `{bq.client.project}.sw_carrier_accounting.run_log`
        WHERE started_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL @days DAY)
        ORDER BY started_at DESC
    """
    from google.cloud.bigquery import QueryJobConfig, ScalarQueryParameter
    job_config = QueryJobConfig(
        query_parameters=[
            ScalarQueryParameter("days", "INT64", days),
        ]
    )
    rows = list(bq.client.query(query, job_config=job_config).result())
    return [dict(r) for r in rows]
