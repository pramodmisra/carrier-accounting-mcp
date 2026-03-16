"""
Validation tools — validate normalized transactions against BigQuery.
Checks policy existence, duplicates, and scores confidence.
"""

from typing import Optional
import structlog

from mcp_server.schemas.canonical import (
    CanonicalTransaction, TransactionStatus, RunMode
)
from mcp_server.services.bigquery_client import BigQueryClient
from mcp_server.services.confidence_scorer import ConfidenceScorer

log = structlog.get_logger(__name__)

bq = BigQueryClient()
scorer = ConfidenceScorer()


def validate_transactions(
    transactions: list[CanonicalTransaction],
) -> dict:
    """
    Validate a list of CanonicalTransactions against BigQuery:
    1. Look up each policy in combined_policy_master
    2. Check for duplicates in live/shadow tables
    3. Score confidence
    4. Classify into auto-queue, review-queue, or rejected

    Returns a dict with:
        auto_queue: list[CanonicalTransaction]   — confidence >= 0.95
        review_queue: list[CanonicalTransaction]  — confidence 0.80–0.94
        rejected: list[CanonicalTransaction]      — confidence < 0.80
        total, auto_count, review_count, rejected_count
    """
    auto_queue = []
    review_queue = []
    rejected = []

    for txn in transactions:
        try:
            # 1. Policy lookup
            bq_match = None
            if txn.policy_number:
                bq_match = bq.find_policy_by_carrier_number(
                    txn.carrier, txn.policy_number
                )

            # 2. Duplicate check
            is_duplicate = False
            if txn.policy_number and txn.effective_date:
                is_duplicate = bq.check_duplicate(
                    txn.carrier, txn.policy_number,
                    txn.amount, txn.effective_date
                )

            # 3. Score confidence
            txn = scorer.score(txn, bq_match, is_duplicate)

            # 4. Classify
            classification = scorer.classify(txn)
            if classification == "auto":
                txn.status = TransactionStatus.APPROVED
                txn.auto_approved = True
                auto_queue.append(txn)
            elif classification == "review":
                txn.status = TransactionStatus.REVIEW
                review_queue.append(txn)
            else:
                txn.status = TransactionStatus.REJECTED
                rejected.append(txn)

        except Exception as e:
            log.error("Validation error", transaction_id=txn.transaction_id, error=str(e))
            txn.status = TransactionStatus.FAILED
            txn.validation_errors.append(f"Validation exception: {e}")
            rejected.append(txn)

    log.info("Validation complete",
             total=len(transactions),
             auto=len(auto_queue),
             review=len(review_queue),
             rejected=len(rejected))

    return {
        "auto_queue": auto_queue,
        "review_queue": review_queue,
        "rejected": rejected,
        "total": len(transactions),
        "auto_count": len(auto_queue),
        "review_count": len(review_queue),
        "rejected_count": len(rejected),
    }
