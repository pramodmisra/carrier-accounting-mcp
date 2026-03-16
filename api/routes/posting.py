"""
Posting routes — post to Epic, generate CSV imports, rollback.
Maps to MCP tools: post_to_epic, post_to_epic_via_browser, generate_epic_import, rollback
"""

from typing import Optional

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse

from api.auth import AuthenticatedUser, require_role
from api.dependencies import get_tenant_config
from api.models.schemas import RollbackRequest, PostToEpicResponse, GenerateImportResponse
from platform_db.models import UserRole
from platform_db.tenant_context import TenantContext

router = APIRouter(prefix="/api", tags=["Epic Posting"])


@router.post("/runs/{run_id}/post-to-epic")
async def post_to_epic(
    run_id: str,
    user: AuthenticatedUser = Depends(require_role(UserRole.ACCOUNTANT)),
    tenant: TenantContext = Depends(get_tenant_config),
) -> dict:
    """Post all approved transactions from a run to Applied Epic via REST API."""
    from mcp_server.services.bigquery_client import BigQueryClient
    from mcp_server.schemas.canonical import CanonicalTransaction, TransactionStatus, RunMode
    from mcp_server.tools.epic_writer import post_transactions_to_epic
    from decimal import Decimal

    bq = BigQueryClient()
    query = f"""
        SELECT * FROM `{tenant.live_table()}`
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


@router.post("/runs/{run_id}/generate-import")
async def generate_epic_import(
    run_id: str,
    user: AuthenticatedUser = Depends(require_role(UserRole.ACCOUNTANT)),
) -> dict:
    """Generate an Applied Epic-compatible CSV import file for a run."""
    # Delegate to the MCP server's generate_epic_import tool logic
    from mcp_server.tools.epic_batch_import import generate_epic_import_csv
    from mcp_server.services.bigquery_client import BigQueryClient
    from mcp_server.schemas.canonical import CanonicalTransaction, TransactionStatus, RunMode
    from mcp_server.config import Config
    from decimal import Decimal

    bq = BigQueryClient()
    rows = []
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
        return {"status": "empty", "message": f"No transactions for run {run_id}", "run_id": run_id}

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
            status=TransactionStatus.APPROVED,
            mode=RunMode(r.get("mode", "trial")),
        )
        transactions.append(txn)

    result = generate_epic_import_csv(transactions)
    result["run_id"] = run_id
    return result


@router.get("/runs/{run_id}/download-import")
async def download_import_file(
    run_id: str,
    user: AuthenticatedUser = Depends(require_role(UserRole.ACCOUNTANT)),
):
    """Download a previously generated Epic import CSV file."""
    from pathlib import Path
    import glob

    matches = glob.glob(f"exports/epic_import_*_{run_id[:8]}_*.csv")
    if not matches:
        from fastapi import HTTPException
        raise HTTPException(404, f"No import file found for run {run_id}")

    return FileResponse(
        matches[0],
        media_type="text/csv",
        filename=Path(matches[0]).name,
    )


@router.post("/runs/{run_id}/rollback")
async def rollback_run(
    run_id: str,
    request: RollbackRequest,
    user: AuthenticatedUser = Depends(require_role(UserRole.ADMIN)),
) -> dict:
    """Rollback all Epic entries from a run. Admin only."""
    from mcp_server.tools.epic_writer import rollback_run as _rollback
    return _rollback(run_id, request.reason)
