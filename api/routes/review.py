"""
Review queue routes — approve, reject, and manage exception queue.
Maps to MCP tools: get_exception_queue_today, approve, reject, approve_run
"""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query

from api.auth import AuthenticatedUser, get_current_user, require_role
from api.dependencies import get_tenant_config
from api.models.schemas import ReviewAction, RejectAction, BatchApprovalResponse
from platform_db.models import UserRole

router = APIRouter(prefix="/api", tags=["Review Queue"])


@router.get("/queue")
async def get_exception_queue(
    target_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    carrier: Optional[str] = Query(None),
    user: AuthenticatedUser = Depends(require_role(UserRole.REVIEWER)),
) -> list[dict]:
    """Get transactions needing human review."""
    from mcp_server.tools.staging import get_exception_queue as _get_queue

    parsed_date = None
    if target_date:
        from dateutil.parser import parse as dp
        parsed_date = dp(target_date).date()
    else:
        parsed_date = date.today()

    queue = _get_queue(parsed_date)

    # Optional carrier filter
    if carrier:
        queue = [t for t in queue if t.get("carrier") == carrier]

    return queue


@router.post("/transactions/{transaction_id}/approve")
async def approve_transaction(
    transaction_id: str,
    action: ReviewAction,
    user: AuthenticatedUser = Depends(require_role(UserRole.REVIEWER)),
) -> dict:
    """Approve a single transaction from the review queue."""
    from mcp_server.tools.staging import approve_transaction as _approve
    return _approve(transaction_id, action.reviewer or user.email, action.notes)


@router.post("/transactions/{transaction_id}/reject")
async def reject_transaction(
    transaction_id: str,
    action: RejectAction,
    user: AuthenticatedUser = Depends(require_role(UserRole.REVIEWER)),
) -> dict:
    """Reject a transaction with a reason."""
    from mcp_server.tools.staging import reject_transaction as _reject
    return _reject(transaction_id, action.reviewer or user.email, action.reason)


@router.post("/runs/{run_id}/approve-batch", response_model=BatchApprovalResponse)
async def approve_batch(
    run_id: str,
    action: ReviewAction,
    user: AuthenticatedUser = Depends(require_role(UserRole.ACCOUNTANT)),
) -> dict:
    """Bulk approve all review-queue transactions from a run."""
    from mcp_server.tools.staging import approve_batch as _batch
    return _batch(run_id, action.reviewer or user.email)
