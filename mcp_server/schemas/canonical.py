"""Canonical transaction schema — all carrier data normalizes to this."""

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from enum import Enum


class TransactionType(str, Enum):
    PREMIUM = "premium"
    COMMISSION = "commission"
    RETURN_PREMIUM = "return_premium"
    ENDORSEMENT = "endorsement"
    CANCELLATION = "cancellation"
    REINSTATEMENT = "reinstatement"
    FEE = "fee"
    ADJUSTMENT = "adjustment"


class TransactionStatus(str, Enum):
    PENDING = "pending"         # Just parsed, not validated
    VALIDATED = "validated"     # Passed BQ validation
    REVIEW = "review"           # Needs human review (low confidence)
    APPROVED = "approved"       # Human approved
    REJECTED = "rejected"       # Human rejected
    POSTED = "posted"           # Written to Applied Epic
    FAILED = "failed"           # Epic write failed
    ROLLED_BACK = "rolled_back" # Rolled back after posting


class RunMode(str, Enum):
    TRIAL = "trial"   # Shadow writes to BQ staging only
    LIVE = "live"     # Real writes to Applied Epic


@dataclass
class CanonicalTransaction:
    """
    Single normalized insurance accounting transaction.
    Every carrier statement record maps to one of these.
    """

    # --- Identification ---
    transaction_id: str                       # UUID generated at parse time
    run_id: str                               # Groups all transactions from one file/run
    source_file: str                          # Original filename
    source_row: Optional[int] = None          # Row/page in source file

    # --- Carrier & Policy ---
    carrier: str = ""                         # Carrier slug: "nationwide", "travelers", etc.
    policy_number: str = ""                   # Carrier-side policy number (raw)
    epic_policy_id: Optional[str] = None      # Matched Applied Epic policy ID
    epic_client_id: Optional[str] = None      # Matched Applied Epic client ID
    client_name: str = ""                     # Client/insured name
    producer_code: Optional[str] = None       # Agency producer code

    # --- Transaction ---
    transaction_type: TransactionType = TransactionType.PREMIUM
    effective_date: Optional[date] = None
    expiration_date: Optional[date] = None
    statement_date: Optional[date] = None
    amount: Decimal = Decimal("0.00")
    commission_rate: Optional[Decimal] = None
    line_of_business: Optional[str] = None
    description: Optional[str] = None

    # --- Confidence & Validation ---
    confidence_score: float = 0.0             # 0.0–1.0
    confidence_factors: dict = field(default_factory=dict)  # Breakdown of score
    validation_warnings: list = field(default_factory=list)
    validation_errors: list = field(default_factory=list)

    # --- Workflow ---
    status: TransactionStatus = TransactionStatus.PENDING
    mode: RunMode = RunMode.TRIAL
    auto_approved: bool = False               # True if confidence >= threshold
    reviewed_by: Optional[str] = None
    review_notes: Optional[str] = None
    reviewed_at: Optional[datetime] = None

    # --- Epic Write ---
    epic_entry_id: Optional[str] = None       # Set after successful SDK write
    epic_posted_at: Optional[datetime] = None

    # --- Metadata ---
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "transaction_id": self.transaction_id,
            "run_id": self.run_id,
            "source_file": self.source_file,
            "source_row": self.source_row,
            "carrier": self.carrier,
            "policy_number": self.policy_number,
            "epic_policy_id": self.epic_policy_id,
            "epic_client_id": self.epic_client_id,
            "client_name": self.client_name,
            "producer_code": self.producer_code,
            "transaction_type": self.transaction_type.value,
            "effective_date": self.effective_date.isoformat() if self.effective_date else None,
            "expiration_date": self.expiration_date.isoformat() if self.expiration_date else None,
            "statement_date": self.statement_date.isoformat() if self.statement_date else None,
            "amount": str(self.amount),
            "commission_rate": str(self.commission_rate) if self.commission_rate else None,
            "line_of_business": self.line_of_business,
            "description": self.description,
            "confidence_score": self.confidence_score,
            "confidence_factors": self.confidence_factors,
            "validation_warnings": self.validation_warnings,
            "validation_errors": self.validation_errors,
            "status": self.status.value,
            "mode": self.mode.value,
            "auto_approved": self.auto_approved,
            "reviewed_by": self.reviewed_by,
            "review_notes": self.review_notes,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "epic_entry_id": self.epic_entry_id,
            "epic_posted_at": self.epic_posted_at.isoformat() if self.epic_posted_at else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class RunSummary:
    """Summary of a single ingestion run."""
    run_id: str
    source_file: str
    carrier: str
    mode: RunMode
    total_transactions: int = 0
    auto_approved: int = 0
    review_queue: int = 0
    failed: int = 0
    posted_to_epic: int = 0
    total_amount: Decimal = Decimal("0.00")
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    status: str = "running"   # running | completed | failed | rolled_back
