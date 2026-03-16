"""
Reconciliation routes — posted vs Epic comparison, trial diff reports.
Maps to MCP tools: reconciliation_report, trial_diff_report, score_confidence
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query

from api.auth import AuthenticatedUser, require_role
from api.models.schemas import ScoreCheckRequest, ScoreCheckResponse
from platform_db.models import UserRole

router = APIRouter(prefix="/api", tags=["Reconciliation & Reports"])


@router.get("/reconciliation")
async def reconciliation_report(
    run_id: Optional[str] = Query(None),
    carrier: Optional[str] = Query(None),
    target_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    user: AuthenticatedUser = Depends(require_role(UserRole.ACCOUNTANT)),
) -> dict:
    """
    Compare posted transactions against Applied Epic entries.
    Returns match rate, mismatched records, and entries missing from Epic.
    """
    from mcp_server.tools.reconciliation import reconciliation_report as _recon

    parsed_date = None
    if target_date:
        from dateutil.parser import parse as dp
        parsed_date = dp(target_date).date()

    return _recon(run_id, carrier, parsed_date)


@router.get("/trial-diff")
async def trial_diff_report(
    run_id: Optional[str] = Query(None),
    carrier: Optional[str] = Query(None),
    target_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    user: AuthenticatedUser = Depends(require_role(UserRole.ACCOUNTANT)),
) -> dict:
    """
    Side-by-side comparison: what the system WOULD have posted vs
    what's currently in Epic. Key report for trial/shadow mode.
    """
    from mcp_server.tools.reconciliation import trial_diff_report as _diff

    parsed_date = None
    if target_date:
        from dateutil.parser import parse as dp
        parsed_date = dp(target_date).date()

    return _diff(run_id, carrier, parsed_date)


@router.post("/score-check", response_model=ScoreCheckResponse)
async def score_confidence(
    request: ScoreCheckRequest,
    user: AuthenticatedUser = Depends(require_role(UserRole.REVIEWER)),
) -> dict:
    """
    Score a single transaction's confidence without running the full pipeline.
    Useful for testing and debugging.
    """
    import uuid
    from decimal import Decimal
    from mcp_server.schemas.canonical import CanonicalTransaction
    from mcp_server.services.bigquery_client import BigQueryClient
    from mcp_server.services.confidence_scorer import ConfidenceScorer

    bq = BigQueryClient()
    scorer = ConfidenceScorer()

    eff_date = None
    if request.effective_date:
        from dateutil.parser import parse as dp
        eff_date = dp(request.effective_date).date()

    txn = CanonicalTransaction(
        transaction_id=str(uuid.uuid4()),
        run_id="score-check",
        source_file="api",
        carrier=request.carrier,
        policy_number=request.policy_number,
        client_name=request.client_name,
        amount=Decimal(request.amount),
        effective_date=eff_date,
    )

    bq_match = bq.find_policy_by_carrier_number(request.carrier, request.policy_number)
    is_duplicate = False
    if eff_date:
        is_duplicate = bq.check_duplicate(request.carrier, request.policy_number, txn.amount, eff_date)

    txn = scorer.score(txn, bq_match, is_duplicate)

    return {
        "confidence_score": txn.confidence_score,
        "classification": scorer.classify(txn),
        "confidence_factors": txn.confidence_factors,
        "validation_warnings": txn.validation_warnings,
        "validation_errors": txn.validation_errors,
        "policy_found": bq_match is not None,
        "is_duplicate": is_duplicate,
        "epic_policy_id": txn.epic_policy_id,
    }
