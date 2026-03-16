"""
Pydantic request/response models for the REST API.
Maps to the underlying MCP tool inputs and outputs.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field


# ------------------------------------------------------------------ #
# AUTH                                                                 #
# ------------------------------------------------------------------ #

class UserProfile(BaseModel):
    user_id: str
    email: str
    name: str
    tenant_id: str
    role: str


# ------------------------------------------------------------------ #
# INGESTION                                                            #
# ------------------------------------------------------------------ #

class IngestRequest(BaseModel):
    file_path: str = Field(..., description="Path to uploaded file (from /upload response)")
    carrier: str = Field(..., description="Carrier slug (e.g. 'nationwide')")
    mode: str = Field(default="trial", description="'trial' or 'live'")


class IngestResponse(BaseModel):
    run_id: str
    carrier: str
    source_file: str
    mode: str
    total_parsed: int
    auto_approved: int
    review_queue: int
    rejected: int
    posting_report: Optional[dict] = None
    next_steps: str


# ------------------------------------------------------------------ #
# REVIEW                                                               #
# ------------------------------------------------------------------ #

class ReviewAction(BaseModel):
    reviewer: str = Field(..., description="Reviewer name/email")
    notes: Optional[str] = None


class RejectAction(BaseModel):
    reviewer: str
    reason: str = Field(..., description="Rejection reason (required)")


class BatchApprovalResponse(BaseModel):
    run_id: str
    approved: int
    reviewer: str


# ------------------------------------------------------------------ #
# TRANSACTIONS                                                         #
# ------------------------------------------------------------------ #

class TransactionSummary(BaseModel):
    transaction_id: str
    carrier: str
    policy_number: str
    client_name: str
    amount: str
    transaction_type: str
    confidence_score: float
    status: str
    validation_warnings: list = []
    validation_errors: list = []


class ScoreCheckRequest(BaseModel):
    carrier: str
    policy_number: str
    client_name: str
    amount: str
    effective_date: Optional[str] = None


class ScoreCheckResponse(BaseModel):
    confidence_score: float
    classification: str
    confidence_factors: dict
    validation_warnings: list
    validation_errors: list
    policy_found: bool
    is_duplicate: bool
    epic_policy_id: Optional[str] = None


# ------------------------------------------------------------------ #
# POSTING                                                              #
# ------------------------------------------------------------------ #

class PostToEpicResponse(BaseModel):
    mode: str
    posted: int
    failed: int
    total: int
    results: list[dict]


class GenerateImportResponse(BaseModel):
    status: str
    run_id: str
    file_path: Optional[str] = None
    row_count: int
    total_amount: Optional[str] = None
    preview: list[dict] = []


class RollbackRequest(BaseModel):
    reason: str = Field(..., description="Reason for rollback")


# ------------------------------------------------------------------ #
# MONITORING                                                           #
# ------------------------------------------------------------------ #

class DailyMetrics(BaseModel):
    total_transactions: int = 0
    auto_approved: int = 0
    review_queue: int = 0
    failed: int = 0
    posted_to_epic: int = 0
    rejected: int = 0
    avg_confidence: Optional[float] = None
    total_amount: Optional[float] = None


class CarrierAccuracyResponse(BaseModel):
    carrier: Optional[str] = None
    total: int = 0
    avg_confidence: Optional[float] = None
    post_rate: Optional[float] = None
    rejection_rate: Optional[float] = None
    error_rate: Optional[float] = None


# ------------------------------------------------------------------ #
# CARRIERS                                                             #
# ------------------------------------------------------------------ #

class CarrierConfig(BaseModel):
    carrier_slug: str
    display_name: str
    policy_number_field: str = "Policy Number"
    client_name_field: str = "Insured Name"
    premium_field: str = "Premium"
    commission_field: str = "Commission"
    effective_date_field: str = "Effective Date"
    date_format: str = "MM/DD/YYYY"
    portal_url: Optional[str] = None
    mode: str = "trial"


class CarrierListResponse(BaseModel):
    carriers: list[CarrierConfig]
    total: int


# ------------------------------------------------------------------ #
# TENANTS (Admin)                                                      #
# ------------------------------------------------------------------ #

class TenantCreate(BaseModel):
    slug: str = Field(..., description="URL-safe identifier (e.g. 'acme-insurance')")
    display_name: str = Field(..., description="Agency display name")
    gcp_project: str
    admin_email: str
    epic_sdk_url: Optional[str] = ""
    epic_api_key: Optional[str] = ""
    epic_agency_id: Optional[str] = ""
    plan: str = "trial"


class TenantResponse(BaseModel):
    tenant_id: str
    slug: str
    display_name: str
    status: str
    plan: str
    created_at: Optional[str] = None
