"""
Staging tools — write validated transactions to BigQuery shadow or live tables.
Handles trial/live routing, review queue management, and batch operations.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional
import structlog

from mcp_server.schemas.canonical import (
    CanonicalTransaction, RunSummary, TransactionStatus, RunMode
)
from mcp_server.services.bigquery_client import BigQueryClient

log = structlog.get_logger(__name__)

bq = BigQueryClient()


def stage_run(
    run_id: str,
    carrier: str,
    source_file: str,
    mode: str,
    auto_queue: list[CanonicalTransaction],
    review_queue: list[CanonicalTransaction],
    rejected: list[CanonicalTransaction],
) -> dict:
    """
    Write all validated transactions to the appropriate BigQuery table.
    Trial mode -> shadow table, Live mode -> live table.
    Also writes a run_log entry.
    """
    all_txns = auto_queue + review_queue + rejected
    run_mode = RunMode(mode)

    if run_mode == RunMode.TRIAL:
        rows_written = bq.write_to_shadow(all_txns)
    else:
        rows_written = bq.write_to_live(all_txns)

    # Compute total amount
    total_amount = sum(t.amount for t in all_txns)

    # Write run log
    run_summary = RunSummary(
        run_id=run_id,
        source_file=source_file,
        carrier=carrier,
        mode=run_mode,
        total_transactions=len(all_txns),
        auto_approved=len(auto_queue),
        review_queue=len(review_queue),
        failed=len(rejected),
        total_amount=total_amount,
        completed_at=datetime.utcnow(),
        status="completed",
    )
    bq.write_run_log(run_summary)

    log.info("Run staged",
             run_id=run_id, mode=mode,
             total=len(all_txns), rows_written=rows_written)

    return {
        "run_id": run_id,
        "mode": mode,
        "rows_written": rows_written,
        "auto_approved": len(auto_queue),
        "review_queue": len(review_queue),
        "rejected": len(rejected),
        "total_amount": str(total_amount),
    }


def approve_transaction(
    transaction_id: str,
    reviewer: str,
    notes: Optional[str] = None,
) -> dict:
    """Approve a single transaction from the review queue."""
    bq.update_transaction_status(
        transaction_id=transaction_id,
        status=TransactionStatus.APPROVED.value,
        reviewed_by=reviewer,
        review_notes=notes,
    )
    log.info("Transaction approved",
             transaction_id=transaction_id, reviewer=reviewer)
    return {
        "transaction_id": transaction_id,
        "status": "approved",
        "reviewer": reviewer,
    }


def reject_transaction(
    transaction_id: str,
    reviewer: str,
    reason: str,
) -> dict:
    """Reject a single transaction from the review queue."""
    bq.update_transaction_status(
        transaction_id=transaction_id,
        status=TransactionStatus.REJECTED.value,
        reviewed_by=reviewer,
        review_notes=reason,
    )
    log.info("Transaction rejected",
             transaction_id=transaction_id, reviewer=reviewer, reason=reason)
    return {
        "transaction_id": transaction_id,
        "status": "rejected",
        "reviewer": reviewer,
        "reason": reason,
    }


def approve_batch(run_id: str, reviewer: str) -> dict:
    """Bulk approve all review-queue transactions from a specific run."""
    queue = bq.get_exception_queue()
    approved = 0
    for txn in queue:
        if txn.get("run_id") == run_id and txn.get("status") == "review":
            approve_transaction(txn["transaction_id"], reviewer)
            approved += 1

    log.info("Batch approved", run_id=run_id, reviewer=reviewer, count=approved)
    return {
        "run_id": run_id,
        "approved": approved,
        "reviewer": reviewer,
    }


def get_exception_queue(target_date: Optional[date] = None) -> list[dict]:
    """Return all transactions needing human review."""
    return bq.get_exception_queue(target_date)
