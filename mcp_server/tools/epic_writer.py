"""
Epic write tools — post approved transactions to Applied Epic via the SDK.
Wraps the EpicSDKClient with batch processing, audit logging, and rollback.
"""

from datetime import datetime
from typing import Optional
import structlog

from mcp_server.schemas.canonical import (
    CanonicalTransaction, TransactionStatus, RunMode
)
from mcp_server.services.epic_sdk_client import EpicSDKClient
from mcp_server.services.bigquery_client import BigQueryClient

log = structlog.get_logger(__name__)

epic = EpicSDKClient()
bq = BigQueryClient()


def post_transactions_to_epic(
    transactions: list[CanonicalTransaction],
    mode: str = "live",
) -> dict:
    """
    Post a list of approved transactions to Applied Epic.
    In trial mode, returns a simulation report without making SDK calls.
    In live mode, calls Epic SDK and records entry IDs back to BigQuery.
    """
    if mode == "trial":
        return {
            "mode": "trial",
            "message": "Trial mode — no Epic writes performed",
            "would_post": len(transactions),
            "total_amount": str(sum(t.amount for t in transactions)),
        }

    posted = 0
    failed = 0
    results = []

    for txn in transactions:
        try:
            epic_entry_id = epic.post_accounting_entry(txn)

            if epic_entry_id:
                # Record the entry ID back to BigQuery immediately
                bq.update_transaction_status(
                    transaction_id=txn.transaction_id,
                    status=TransactionStatus.POSTED.value,
                    epic_entry_id=epic_entry_id,
                )
                txn.epic_entry_id = epic_entry_id
                txn.status = TransactionStatus.POSTED
                posted += 1
                results.append({
                    "transaction_id": txn.transaction_id,
                    "epic_entry_id": epic_entry_id,
                    "status": "posted",
                })
            else:
                results.append({
                    "transaction_id": txn.transaction_id,
                    "status": "skipped",
                    "reason": "No entry ID returned (trial mode or blocked)",
                })

        except Exception as e:
            log.error("Epic write failed",
                      transaction_id=txn.transaction_id, error=str(e))
            bq.update_transaction_status(
                transaction_id=txn.transaction_id,
                status=TransactionStatus.FAILED.value,
            )
            txn.status = TransactionStatus.FAILED
            failed += 1
            results.append({
                "transaction_id": txn.transaction_id,
                "status": "failed",
                "error": str(e),
            })

    log.info("Epic posting complete", posted=posted, failed=failed)
    return {
        "mode": mode,
        "posted": posted,
        "failed": failed,
        "total": len(transactions),
        "results": results,
    }


def rollback_run(run_id: str, reason: str) -> dict:
    """
    Rollback all Epic entries from a specific run.
    Calls Epic void for each posted entry and updates BQ status.
    """
    # Fetch posted transactions for this run
    query = f"""
        SELECT transaction_id, epic_entry_id
        FROM `{bq.client.project}.sw_carrier_accounting.carrier_entries_live`
        WHERE run_id = @run_id AND status = 'posted' AND epic_entry_id IS NOT NULL
    """
    from google.cloud.bigquery import QueryJobConfig, ScalarQueryParameter
    job_config = QueryJobConfig(
        query_parameters=[
            ScalarQueryParameter("run_id", "STRING", run_id),
        ]
    )
    rows = list(bq.client.query(query, job_config=job_config).result())

    if not rows:
        return {"run_id": run_id, "message": "No posted entries found to rollback"}

    rolled_back = 0
    failed = 0

    for row in rows:
        success = epic.rollback_entry(row["epic_entry_id"], reason)
        if success:
            bq.update_transaction_status(
                transaction_id=row["transaction_id"],
                status="rolled_back",
            )
            rolled_back += 1
        else:
            failed += 1

    log.info("Rollback complete",
             run_id=run_id, rolled_back=rolled_back, failed=failed)
    return {
        "run_id": run_id,
        "reason": reason,
        "rolled_back": rolled_back,
        "failed": failed,
        "total": len(rows),
    }
