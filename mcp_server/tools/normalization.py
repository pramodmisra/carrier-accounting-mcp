"""
Normalization tools — LLM-powered mapping from raw carrier data to CanonicalTransaction.
Claude reads raw extracted rows and maps them to the canonical schema.
"""

import uuid
import json
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Optional
import anthropic
import structlog

from mcp_server.config import Config
from mcp_server.schemas.canonical import (
    CanonicalTransaction, TransactionType, TransactionStatus, RunMode
)
from mcp_server.schemas.carrier_schemas import get_carrier_schema

log = structlog.get_logger(__name__)

_client = anthropic.Anthropic(api_key=Config.ANTHROPIC_API_KEY)

NORMALIZATION_SYSTEM_PROMPT = """
You are an insurance accounting data normalization expert.

Your job is to extract structured transaction data from raw carrier statement rows 
and map it to a canonical JSON schema.

For each input row, output a JSON object with these fields:
- policy_number: string (carrier's policy number, required)
- client_name: string (insured/client name)
- effective_date: string (YYYY-MM-DD format, or null)
- expiration_date: string (YYYY-MM-DD format, or null)
- statement_date: string (YYYY-MM-DD format, or null)
- amount: string (decimal number as string, positive for premium/commission, negative for returns)
- transaction_type: one of: premium, commission, return_premium, endorsement, cancellation, reinstatement, fee, adjustment
- commission_rate: string (decimal as percentage, e.g. "0.15" for 15%, or null)
- line_of_business: string (e.g. "Commercial Auto", "General Liability", or null)
- description: string (brief description of the transaction, or null)
- producer_code: string (producer/agent code, or null)
- skip: boolean (true if this row is a header, total, summary, or non-transaction row)
- skip_reason: string (reason for skipping, or null)

If you cannot confidently extract a required field, use null.
Respond ONLY with a JSON array of objects, one per input row. No explanation, no markdown.
""".strip()


def normalize_raw_rows(
    ingestion_result: dict,
    batch_size: int = 20,
) -> list[CanonicalTransaction]:
    """
    Takes the output of ingest_pdf_statement or ingest_excel_bordereaux
    and returns a list of CanonicalTransaction objects.

    Uses Claude to map raw carrier fields to the canonical schema.
    Processes rows in batches for efficiency.
    """
    run_id = ingestion_result["run_id"]
    carrier = ingestion_result["carrier"]
    source_file = ingestion_result["source_file"]
    mode = RunMode(ingestion_result.get("mode", "trial"))
    raw_rows = ingestion_result["raw_rows"]
    schema = get_carrier_schema(carrier)

    log.info("Starting normalization", run_id=run_id, carrier=carrier, rows=len(raw_rows))

    transactions = []

    # Process in batches
    for batch_start in range(0, len(raw_rows), batch_size):
        batch = raw_rows[batch_start:batch_start + batch_size]

        user_prompt = f"""
Carrier: {schema.carrier_display_name}
Statement format: {ingestion_result.get('format', 'unknown')}
Known field mappings for this carrier:
- Policy number field: {schema.policy_number_field}
- Client name field: {schema.client_name_field}
- Premium field: {schema.premium_field}
- Commission field: {schema.commission_field}
- Effective date field: {schema.effective_date_field}
- Date format: {schema.date_format}

Raw rows to normalize (batch {batch_start // batch_size + 1}):
{json.dumps(batch, indent=2, default=str)}
"""

        try:
            response = _client.messages.create(
                model="claude-opus-4-5",
                max_tokens=4000,
                system=NORMALIZATION_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}],
            )
            raw_json = response.content[0].text.strip()

            # Strip markdown code fences if present
            if raw_json.startswith("```"):
                raw_json = raw_json.split("```")[1]
                if raw_json.startswith("json"):
                    raw_json = raw_json[4:]

            normalized_batch = json.loads(raw_json)

        except Exception as e:
            log.error("Normalization LLM call failed", batch_start=batch_start, error=str(e))
            # Create error placeholders so we don't silently lose rows
            normalized_batch = [{"skip": True, "skip_reason": f"LLM error: {e}"}
                                 for _ in batch]

        for i, norm in enumerate(normalized_batch):
            original_row = batch[i] if i < len(batch) else {}

            # Skip header/summary rows
            if norm.get("skip"):
                log.debug("Skipping row", reason=norm.get("skip_reason"),
                          row_idx=batch_start + i)
                continue

            # Build CanonicalTransaction
            try:
                txn = CanonicalTransaction(
                    transaction_id=str(uuid.uuid4()),
                    run_id=run_id,
                    source_file=source_file,
                    source_row=original_row.get("_source_row"),
                    carrier=carrier,
                    policy_number=norm.get("policy_number", "").strip(),
                    client_name=norm.get("client_name", "").strip(),
                    effective_date=_parse_date(norm.get("effective_date")),
                    expiration_date=_parse_date(norm.get("expiration_date")),
                    statement_date=_parse_date(norm.get("statement_date")),
                    amount=_parse_decimal(norm.get("amount", "0")),
                    transaction_type=_parse_transaction_type(norm.get("transaction_type")),
                    commission_rate=_parse_decimal(norm.get("commission_rate")) if norm.get("commission_rate") else None,
                    line_of_business=norm.get("line_of_business"),
                    description=norm.get("description"),
                    producer_code=norm.get("producer_code"),
                    mode=mode,
                    status=TransactionStatus.PENDING,
                )
                transactions.append(txn)

            except Exception as e:
                log.warning("Failed to build CanonicalTransaction",
                            row_idx=batch_start + i, error=str(e), norm=norm)

    log.info("Normalization complete",
             run_id=run_id, input_rows=len(raw_rows), transactions=len(transactions))
    return transactions


# ------------------------------------------------------------------ #
# Parsing helpers                                                      #
# ------------------------------------------------------------------ #

def _parse_date(value: Optional[str]):
    if not value:
        return None
    from dateutil.parser import parse as dateparse
    try:
        return dateparse(value).date()
    except Exception:
        return None


def _parse_decimal(value: Optional[str]) -> Decimal:
    if not value:
        return Decimal("0")
    cleaned = str(value).replace(",", "").replace("$", "").replace("(", "-").replace(")", "").strip()
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return Decimal("0")


def _parse_transaction_type(value: Optional[str]) -> TransactionType:
    if not value:
        return TransactionType.PREMIUM
    mapping = {
        "premium": TransactionType.PREMIUM,
        "commission": TransactionType.COMMISSION,
        "return_premium": TransactionType.RETURN_PREMIUM,
        "endorsement": TransactionType.ENDORSEMENT,
        "cancellation": TransactionType.CANCELLATION,
        "reinstatement": TransactionType.REINSTATEMENT,
        "fee": TransactionType.FEE,
        "adjustment": TransactionType.ADJUSTMENT,
    }
    return mapping.get(value.lower(), TransactionType.PREMIUM)
