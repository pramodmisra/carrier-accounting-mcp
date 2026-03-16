"""
Gap #3: Epic batch CSV import generator.
Produces Applied Epic-compatible CSV files for bulk accounting entry imports.
Use when the REST API is unavailable or for large batch operations.
"""

import csv
import io
from datetime import datetime
from pathlib import Path
from typing import Optional
import structlog

from mcp_server.schemas.canonical import CanonicalTransaction
from mcp_server.config import Config

log = structlog.get_logger(__name__)

# Applied Epic batch import column spec
# Adjust column names to match your agency's Epic import template
EPIC_IMPORT_COLUMNS = [
    "AgencyId",
    "PolicyId",
    "ClientId",
    "PolicyNumber",
    "ClientName",
    "CarrierName",
    "TransactionType",
    "Amount",
    "EffectiveDate",
    "ExpirationDate",
    "StatementDate",
    "LineOfBusiness",
    "Description",
    "ProducerCode",
    "CommissionRate",
    "ReferenceNumber",
    "Source",
]


def _transaction_to_import_row(txn: CanonicalTransaction) -> dict:
    """Convert a CanonicalTransaction to an Epic import CSV row."""
    return {
        "AgencyId": Config.EPIC_AGENCY_ID,
        "PolicyId": txn.epic_policy_id or "",
        "ClientId": txn.epic_client_id or "",
        "PolicyNumber": txn.policy_number,
        "ClientName": txn.client_name,
        "CarrierName": txn.carrier,
        "TransactionType": txn.transaction_type.value,
        "Amount": str(txn.amount),
        "EffectiveDate": txn.effective_date.strftime("%m/%d/%Y") if txn.effective_date else "",
        "ExpirationDate": txn.expiration_date.strftime("%m/%d/%Y") if txn.expiration_date else "",
        "StatementDate": txn.statement_date.strftime("%m/%d/%Y") if txn.statement_date else "",
        "LineOfBusiness": txn.line_of_business or "",
        "Description": txn.description or f"Carrier statement import - {txn.carrier}",
        "ProducerCode": txn.producer_code or "",
        "CommissionRate": str(txn.commission_rate) if txn.commission_rate else "",
        "ReferenceNumber": txn.transaction_id,
        "Source": "carrier_accounting_mcp",
    }


def generate_epic_import_csv(
    transactions: list[CanonicalTransaction],
    output_path: Optional[str] = None,
) -> dict:
    """
    Generate an Applied Epic-compatible CSV import file from transactions.

    Args:
        transactions: List of approved CanonicalTransactions to export
        output_path: Optional file path; if None, generates in exports/ dir

    Returns:
        Dict with file_path, row_count, total_amount, and preview of first rows
    """
    if not transactions:
        return {"status": "empty", "message": "No transactions to export", "row_count": 0}

    # Default output path
    if not output_path:
        export_dir = Path("exports")
        export_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        carrier = transactions[0].carrier
        run_id = transactions[0].run_id[:8]
        output_path = str(export_dir / f"epic_import_{carrier}_{run_id}_{timestamp}.csv")

    rows = [_transaction_to_import_row(txn) for txn in transactions]

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=EPIC_IMPORT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    total_amount = sum(txn.amount for txn in transactions)

    # Preview first 5 rows
    preview = []
    for row in rows[:5]:
        preview.append({
            "PolicyNumber": row["PolicyNumber"],
            "ClientName": row["ClientName"],
            "Amount": row["Amount"],
            "TransactionType": row["TransactionType"],
        })

    log.info("Epic import CSV generated",
             path=output_path, rows=len(rows), total_amount=str(total_amount))

    return {
        "status": "generated",
        "file_path": output_path,
        "row_count": len(rows),
        "total_amount": str(total_amount),
        "columns": EPIC_IMPORT_COLUMNS,
        "preview": preview,
    }


def generate_epic_import_string(transactions: list[CanonicalTransaction]) -> str:
    """
    Generate Epic import CSV as a string (for returning via MCP tool
    without writing to disk).
    """
    if not transactions:
        return ""

    output = io.StringIO()
    rows = [_transaction_to_import_row(txn) for txn in transactions]

    writer = csv.DictWriter(output, fieldnames=EPIC_IMPORT_COLUMNS)
    writer.writeheader()
    writer.writerows(rows)

    return output.getvalue()
