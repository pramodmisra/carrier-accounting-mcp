"""
Carrier Accounting MCP Server — main entrypoint.
All MCP tools are registered here.

Tools:
  INGESTION (3)    — ingest_carrier_statement, ingest_pdf, ingest_excel
  STANDALONE (4)   — normalize_transactions, validate_against_datalake,
                     score_confidence, browse_carrier_portal
  REVIEW (4)       — get_exception_queue_today, approve, reject, approve_run
  POSTING (5)      — post_to_epic, post_to_epic_via_ui, generate_epic_import,
                     rollback
  MONITORING (5)   — daily_metrics, carrier_accuracy, run_history,
                     list_supported_carriers
  REPORTING (2)    — reconciliation_report, trial_diff_report
  TOTAL: 23 tools
"""

import asyncio
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from fastmcp import FastMCP

from mcp_server.config import Config
from mcp_server.tools.ingestion import ingest_statement
from mcp_server.tools.normalization import normalize_raw_rows
from mcp_server.tools.validation import validate_transactions
from mcp_server.tools.staging import (
    stage_run, approve_transaction, reject_transaction,
    approve_batch, get_exception_queue
)
from mcp_server.tools.epic_writer import post_transactions_to_epic, rollback_run
from mcp_server.tools.epic_batch_import import (
    generate_epic_import_csv, generate_epic_import_string
)
from mcp_server.tools.reconciliation import (
    reconciliation_report as _reconciliation_report,
    trial_diff_report as _trial_diff_report,
)
from mcp_server.tools.monitoring import get_run_history as _get_run_history
from mcp_server.services.bigquery_client import BigQueryClient
from mcp_server.services.confidence_scorer import ConfidenceScorer

mcp = FastMCP("carrier-accounting-mcp")
bq = BigQueryClient()
scorer = ConfidenceScorer()


# ================================================================== #
# INGESTION TOOLS                                                      #
# ================================================================== #

@mcp.tool()
def ingest_carrier_statement(
    file_path: str,
    carrier: str,
    mode: str = "trial",
) -> dict:
    """
    Full pipeline: ingest a carrier PDF or Excel statement, normalize,
    validate against BigQuery, and stage for review or posting.

    Args:
        file_path: Absolute path to the PDF or Excel file
        carrier: Carrier slug (e.g. 'nationwide', 'travelers')
        mode: 'trial' (default, safe) or 'live' (writes to Epic)

    Returns:
        run_summary with counts by status and run_id for follow-up
    """
    run_id = str(uuid.uuid4())

    # 1. Ingest
    raw = ingest_statement(file_path, carrier, mode, run_id)

    # 2. Normalize
    transactions = normalize_raw_rows(raw)

    # 3. Validate
    validation = validate_transactions(transactions)

    # 4. Stage (write to BQ shadow or live table)
    run_summary = stage_run(
        run_id=run_id,
        carrier=carrier,
        source_file=file_path,
        mode=mode,
        auto_queue=validation["auto_queue"],
        review_queue=validation["review_queue"],
        rejected=validation["rejected"],
    )

    # 5. In live mode, auto-post high-confidence transactions
    posting_report = None
    if mode == "live":
        posting_report = post_transactions_to_epic(
            validation["auto_queue"], mode="live"
        )

    return {
        "run_id": run_id,
        "carrier": carrier,
        "source_file": file_path,
        "mode": mode,
        "total_parsed": validation["total"],
        "auto_approved": validation["auto_count"],
        "review_queue": validation["review_count"],
        "rejected": validation["rejected_count"],
        "posting_report": posting_report,
        "next_steps": (
            "Review the exception queue with get_exception_queue()"
            if validation["review_count"] > 0
            else "All transactions processed. Check get_daily_metrics() for summary."
        ),
    }


@mcp.tool()
def ingest_pdf(file_path: str, carrier: str, mode: str = "trial") -> dict:
    """
    Ingest a single carrier PDF statement. Runs the full pipeline.
    Alias for ingest_carrier_statement for explicit PDF files.
    """
    return ingest_carrier_statement(file_path, carrier, mode)


@mcp.tool()
def ingest_excel(file_path: str, carrier: str, mode: str = "trial",
                 sheet_name: Optional[str] = None) -> dict:
    """
    Ingest a single carrier Excel bordereaux. Runs the full pipeline.
    """
    return ingest_carrier_statement(file_path, carrier, mode)


# ================================================================== #
# STANDALONE PIPELINE TOOLS (Gap #2)                                   #
# ================================================================== #

@mcp.tool()
def normalize_transactions(
    file_path: str,
    carrier: str,
    mode: str = "trial",
) -> list[dict]:
    """
    Parse and normalize a carrier document WITHOUT validation or staging.
    Returns the raw normalized transactions for inspection.
    Useful for debugging normalization quality before running full pipeline.

    Args:
        file_path: Path to PDF or Excel file
        carrier: Carrier slug
        mode: 'trial' or 'live'
    """
    run_id = str(uuid.uuid4())
    raw = ingest_statement(file_path, carrier, mode, run_id)
    transactions = normalize_raw_rows(raw)
    return [t.to_dict() for t in transactions]


@mcp.tool()
def validate_against_datalake(
    file_path: str,
    carrier: str,
    mode: str = "trial",
) -> dict:
    """
    Parse, normalize, AND validate a carrier document against BigQuery —
    but do NOT stage or post. Returns the full validation report including
    confidence scores, policy matches, and queue classifications.

    Args:
        file_path: Path to PDF or Excel file
        carrier: Carrier slug
        mode: 'trial' or 'live'
    """
    run_id = str(uuid.uuid4())
    raw = ingest_statement(file_path, carrier, mode, run_id)
    transactions = normalize_raw_rows(raw)
    validation = validate_transactions(transactions)

    # Serialize transactions for output
    auto_dicts = [t.to_dict() for t in validation["auto_queue"]]
    review_dicts = [t.to_dict() for t in validation["review_queue"]]
    rejected_dicts = [t.to_dict() for t in validation["rejected"]]

    return {
        "run_id": run_id,
        "carrier": carrier,
        "total": validation["total"],
        "auto_count": validation["auto_count"],
        "review_count": validation["review_count"],
        "rejected_count": validation["rejected_count"],
        "auto_queue": auto_dicts,
        "review_queue": review_dicts,
        "rejected": rejected_dicts,
    }


@mcp.tool()
def score_confidence(
    carrier: str,
    policy_number: str,
    client_name: str,
    amount: str,
    effective_date: Optional[str] = None,
) -> dict:
    """
    Score a single transaction's confidence without running the full pipeline.
    Looks up the policy in BigQuery, checks for duplicates, and returns the
    confidence score breakdown. Useful for testing and debugging.

    Args:
        carrier: Carrier slug
        policy_number: Carrier policy number
        client_name: Insured/client name
        amount: Transaction amount as string (e.g. '1500.00')
        effective_date: Effective date YYYY-MM-DD (optional)
    """
    from mcp_server.schemas.canonical import CanonicalTransaction

    eff_date = None
    if effective_date:
        from dateutil.parser import parse as dp
        eff_date = dp(effective_date).date()

    txn = CanonicalTransaction(
        transaction_id=str(uuid.uuid4()),
        run_id="score-check",
        source_file="manual",
        carrier=carrier,
        policy_number=policy_number,
        client_name=client_name,
        amount=Decimal(amount),
        effective_date=eff_date,
    )

    # Policy lookup
    bq_match = bq.find_policy_by_carrier_number(carrier, policy_number)

    # Duplicate check
    is_duplicate = False
    if eff_date:
        is_duplicate = bq.check_duplicate(carrier, policy_number, txn.amount, eff_date)

    # Score
    txn = scorer.score(txn, bq_match, is_duplicate)
    classification = scorer.classify(txn)

    return {
        "confidence_score": txn.confidence_score,
        "classification": classification,
        "confidence_factors": txn.confidence_factors,
        "validation_warnings": txn.validation_warnings,
        "validation_errors": txn.validation_errors,
        "policy_found": bq_match is not None,
        "is_duplicate": is_duplicate,
        "epic_policy_id": txn.epic_policy_id,
        "epic_client_id": txn.epic_client_id,
    }


# ================================================================== #
# BROWSER TOOLS (Gap #1)                                               #
# ================================================================== #

@mcp.tool()
def browse_carrier_portal(
    carrier: str,
    username: str,
    password: str,
    mode: str = "trial",
    download_dir: Optional[str] = None,
) -> dict:
    """
    Log into a carrier portal via Playwright and download latest statements.
    Returns paths to downloaded files which can then be passed to
    ingest_carrier_statement.

    Args:
        carrier: Carrier slug (must have portal_url in its config)
        username: Portal login username
        password: Portal login password
        mode: 'trial' or 'live'
        download_dir: Optional override for download directory
    """
    from mcp_server.tools.browser import browse_carrier_portal as _browse
    return asyncio.run(_browse(carrier, username, password, mode, download_dir))


# ================================================================== #
# REVIEW TOOLS                                                         #
# ================================================================== #

@mcp.tool()
def get_exception_queue_today() -> list[dict]:
    """
    Return all transactions in the human review queue for today.
    These are transactions with confidence score 0.80-0.94 that need
    accounting team review before posting to Epic.
    """
    return get_exception_queue(date.today())


@mcp.tool()
def approve(transaction_id: str, reviewer: str, notes: Optional[str] = None) -> dict:
    """
    Approve a single transaction from the review queue.
    In live mode, this will trigger an Epic posting.

    Args:
        transaction_id: UUID of the transaction
        reviewer: Name/email of the reviewer
        notes: Optional review notes
    """
    return approve_transaction(transaction_id, reviewer, notes)


@mcp.tool()
def reject(transaction_id: str, reviewer: str, reason: str) -> dict:
    """
    Reject a transaction from the review queue.

    Args:
        transaction_id: UUID of the transaction
        reviewer: Name/email of the reviewer
        reason: Reason for rejection (required)
    """
    return reject_transaction(transaction_id, reviewer, reason)


@mcp.tool()
def approve_run(run_id: str, reviewer: str) -> dict:
    """
    Bulk approve all review-queue transactions from a specific run.
    Use after verifying the trial run report is accurate.

    Args:
        run_id: The run ID from ingest_carrier_statement output
        reviewer: Name/email of the approving accountant
    """
    return approve_batch(run_id, reviewer)


# ================================================================== #
# POSTING TOOLS                                                        #
# ================================================================== #

@mcp.tool()
def post_to_epic(run_id: str) -> dict:
    """
    Post all approved transactions from a run to Applied Epic via REST API.
    Only works in live mode. In trial mode, returns a simulation report.

    Args:
        run_id: The run ID to post
    """
    from mcp_server.schemas.canonical import CanonicalTransaction, TransactionStatus, RunMode

    query = f"""
        SELECT * FROM `{bq.client.project}.sw_carrier_accounting.carrier_entries_live`
        WHERE run_id = '{run_id}' AND status = 'approved'
    """
    rows = list(bq.client.query(query).result())

    if not rows:
        return {"message": f"No approved transactions found for run {run_id}", "run_id": run_id}

    transactions = []
    for r in rows:
        txn = CanonicalTransaction(
            transaction_id=r["transaction_id"],
            run_id=r["run_id"],
            source_file=r["source_file"],
            carrier=r["carrier"],
            policy_number=r["policy_number"],
            epic_policy_id=r.get("epic_policy_id"),
            epic_client_id=r.get("epic_client_id"),
            amount=Decimal(str(r["amount"])),
            status=TransactionStatus.APPROVED,
            mode=RunMode.LIVE,
        )
        transactions.append(txn)

    return post_transactions_to_epic(transactions, mode="live")


@mcp.tool()
def post_to_epic_via_browser(
    run_id: str,
    epic_username: str,
    epic_password: str,
) -> dict:
    """
    Fallback: post approved transactions to Applied Epic by automating the
    Epic web UI via Playwright. Use when the REST API / SDK is unavailable.

    Args:
        run_id: The run ID to post
        epic_username: Epic web UI login username
        epic_password: Epic web UI login password
    """
    from mcp_server.schemas.canonical import CanonicalTransaction, TransactionStatus, RunMode
    from mcp_server.tools.epic_ui_automation import post_to_epic_via_ui

    query = f"""
        SELECT * FROM `{bq.client.project}.sw_carrier_accounting.carrier_entries_live`
        WHERE run_id = '{run_id}' AND status = 'approved'
    """
    rows = list(bq.client.query(query).result())

    if not rows:
        return {"message": f"No approved transactions found for run {run_id}", "run_id": run_id}

    transactions = []
    for r in rows:
        txn = CanonicalTransaction(
            transaction_id=r["transaction_id"],
            run_id=r["run_id"],
            source_file=r["source_file"],
            carrier=r["carrier"],
            policy_number=r["policy_number"],
            epic_policy_id=r.get("epic_policy_id"),
            epic_client_id=r.get("epic_client_id"),
            amount=Decimal(str(r["amount"])),
            status=TransactionStatus.APPROVED,
            mode=RunMode.LIVE,
        )
        transactions.append(txn)

    return asyncio.run(post_to_epic_via_ui(
        transactions, epic_username, epic_password
    ))


@mcp.tool()
def generate_epic_import(run_id: str, output_path: Optional[str] = None) -> dict:
    """
    Generate an Applied Epic-compatible CSV import file for a run's
    approved transactions. Use for batch imports when neither the SDK
    nor UI automation is available.

    Args:
        run_id: The run ID to export
        output_path: Optional output file path (auto-generated if omitted)
    """
    from mcp_server.schemas.canonical import CanonicalTransaction, TransactionStatus, RunMode

    # Fetch from both shadow (trial) and live tables
    for table in [Config.live_table(), Config.shadow_table()]:
        query = f"""
            SELECT * FROM `{table}`
            WHERE run_id = '{run_id}'
            AND status IN ('approved', 'validated', 'review')
        """
        rows = list(bq.client.query(query).result())
        if rows:
            break

    if not rows:
        return {"message": f"No transactions found for run {run_id}", "run_id": run_id}

    transactions = []
    for r in rows:
        txn = CanonicalTransaction(
            transaction_id=r["transaction_id"],
            run_id=r["run_id"],
            source_file=r.get("source_file", ""),
            carrier=r.get("carrier", ""),
            policy_number=r.get("policy_number", ""),
            epic_policy_id=r.get("epic_policy_id"),
            epic_client_id=r.get("epic_client_id"),
            client_name=r.get("client_name", ""),
            amount=Decimal(str(r.get("amount", 0))),
            effective_date=r.get("effective_date"),
            expiration_date=r.get("expiration_date"),
            statement_date=r.get("statement_date"),
            line_of_business=r.get("line_of_business"),
            description=r.get("description"),
            producer_code=r.get("producer_code"),
            commission_rate=Decimal(str(r["commission_rate"])) if r.get("commission_rate") else None,
            status=TransactionStatus.APPROVED,
            mode=RunMode(r.get("mode", "trial")),
        )
        transactions.append(txn)

    result = generate_epic_import_csv(transactions, output_path)
    result["run_id"] = run_id
    return result


@mcp.tool()
def rollback(run_id: str, reason: str) -> dict:
    """
    Rollback all Epic entries from a run.
    Use if a bad batch was posted. Calls Epic void for each entry.

    Args:
        run_id: The run ID to roll back
        reason: Reason for rollback (required, logged to audit trail)
    """
    return rollback_run(run_id, reason)


# ================================================================== #
# MONITORING TOOLS (Gap #6)                                            #
# ================================================================== #

@mcp.tool()
def daily_metrics(target_date: Optional[str] = None) -> dict:
    """
    Get the daily accuracy scorecard for the accounting team.
    Shows total processed, auto-approved, review queue, exceptions, accuracy %.

    Args:
        target_date: Date string YYYY-MM-DD (defaults to today)
    """
    parsed_date = None
    if target_date:
        from dateutil.parser import parse as dp
        parsed_date = dp(target_date).date()
    return bq.get_daily_metrics(parsed_date)


@mcp.tool()
def carrier_accuracy(carrier: str, days: int = 30) -> dict:
    """
    Get accuracy metrics for a specific carrier over the past N days.
    Useful for deciding when to promote a carrier from trial to live mode.

    Args:
        carrier: Carrier slug (e.g. 'nationwide')
        days: Number of days to look back (default 30)
    """
    return bq.get_carrier_accuracy(carrier, days)


@mcp.tool()
def run_history(days: int = 7) -> list[dict]:
    """
    Get recent ingestion run history. Shows run_id, carrier, mode, counts,
    and status for each run over the past N days.

    Args:
        days: Number of days to look back (default 7)
    """
    return _get_run_history(days)


@mcp.tool()
def list_supported_carriers() -> list[str]:
    """List all carriers currently configured in the system."""
    from mcp_server.schemas.carrier_schemas import CARRIER_REGISTRY
    return list(CARRIER_REGISTRY.keys())


# ================================================================== #
# REPORTING TOOLS (Gaps #4 and #5)                                     #
# ================================================================== #

@mcp.tool()
def reconciliation_report(
    run_id: Optional[str] = None,
    carrier: Optional[str] = None,
    target_date: Optional[str] = None,
) -> dict:
    """
    Compare posted transactions in our data lake against Applied Epic entries.
    For each posted transaction, reads the Epic entry and checks for
    discrepancies in amount, policy ID, and status.

    Returns match rate, mismatched records, and entries missing from Epic.

    Args:
        run_id: Specific run to reconcile (optional)
        carrier: Filter by carrier slug (optional)
        target_date: Date string YYYY-MM-DD (optional, defaults to today)
    """
    parsed_date = None
    if target_date:
        from dateutil.parser import parse as dp
        parsed_date = dp(target_date).date()
    return _reconciliation_report(run_id, carrier, parsed_date)


@mcp.tool()
def trial_diff_report(
    run_id: Optional[str] = None,
    carrier: Optional[str] = None,
    target_date: Optional[str] = None,
) -> dict:
    """
    Side-by-side comparison: what the system WOULD have posted to Epic
    (from the shadow table) vs what currently exists in Epic for those
    policies.

    This is the key report for the accounting team during trial/shadow mode.
    Shows every parsed transaction alongside existing Epic data, highlighting
    amount deltas, name mismatches, and an overall accuracy recommendation.

    Args:
        run_id: Specific trial run to diff (optional)
        carrier: Filter by carrier slug (optional)
        target_date: Date string YYYY-MM-DD (optional, defaults to today)
    """
    parsed_date = None
    if target_date:
        from dateutil.parser import parse as dp
        parsed_date = dp(target_date).date()
    return _trial_diff_report(run_id, carrier, parsed_date)


# ================================================================== #
# MAIN                                                                 #
# ================================================================== #

def main():
    """Entry point for the carrier-accounting-mcp CLI command."""
    import os
    import argparse
    parser = argparse.ArgumentParser(description="Carrier Accounting MCP Server")
    parser.add_argument("--mode", default=Config.DEFAULT_MODE,
                        choices=["trial", "live"], help="Default operating mode")
    parser.add_argument("--port", type=int, default=int(os.getenv("PORT", "8000")))
    parser.add_argument("--transport", default=os.getenv("TRANSPORT", "stdio"),
                        choices=["stdio", "http"], help="Transport: stdio (local) or http (cloud)")
    args = parser.parse_args()

    print(f"Starting Carrier Accounting MCP Server")
    print(f"  Transport: {args.transport}")
    print(f"  Port: {args.port}")
    print(f"  Tools: 21 | Carriers: 48+")
    print(f"  Docs: https://5gvector.com/carrier-accounting")
    print()

    if args.transport == "http":
        mcp.run(transport="http", host="0.0.0.0", port=args.port)
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
