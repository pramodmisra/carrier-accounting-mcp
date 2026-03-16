"""
Ingestion routes — file upload and pipeline execution.
Maps to MCP tools: ingest_carrier_statement, normalize_transactions, validate_against_datalake
"""

import uuid
import shutil
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException

from api.auth import AuthenticatedUser, get_current_user, require_role
from api.dependencies import get_tenant_config
from api.models.schemas import IngestRequest, IngestResponse
from platform_db.models import UserRole
from platform_db.tenant_context import TenantContext

router = APIRouter(prefix="/api", tags=["Ingestion"])

UPLOAD_DIR = Path("uploads")


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    user: AuthenticatedUser = Depends(require_role(UserRole.ACCOUNTANT)),
    tenant: TenantContext = Depends(get_tenant_config),
) -> dict:
    """Upload a carrier statement file (PDF or Excel) for processing."""
    # Validate file type
    allowed_extensions = {".pdf", ".xlsx", ".xls", ".xlsm", ".csv"}
    suffix = Path(file.filename).suffix.lower()
    if suffix not in allowed_extensions:
        raise HTTPException(400, f"Unsupported file type: {suffix}")

    # Save to tenant-specific directory
    file_id = str(uuid.uuid4())
    tenant_dir = UPLOAD_DIR / tenant.tenant_slug / file_id
    tenant_dir.mkdir(parents=True, exist_ok=True)

    dest = tenant_dir / file.filename
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)

    return {
        "file_id": file_id,
        "filename": file.filename,
        "file_path": str(dest),
        "size_bytes": dest.stat().st_size,
        "tenant": tenant.tenant_slug,
    }


@router.post("/ingest", response_model=IngestResponse)
async def ingest_statement(
    request: IngestRequest,
    user: AuthenticatedUser = Depends(require_role(UserRole.ACCOUNTANT)),
    tenant: TenantContext = Depends(get_tenant_config),
) -> dict:
    """Run the full ingestion pipeline: parse -> normalize -> validate -> stage."""
    from mcp_server.tools.ingestion import ingest_statement as _ingest
    from mcp_server.tools.normalization import normalize_raw_rows
    from mcp_server.tools.validation import validate_transactions
    from mcp_server.tools.staging import stage_run
    from mcp_server.tools.epic_writer import post_transactions_to_epic

    run_id = str(uuid.uuid4())

    raw = _ingest(request.file_path, request.carrier, request.mode, run_id)
    transactions = normalize_raw_rows(raw)
    validation = validate_transactions(transactions)

    stage_run(
        run_id=run_id,
        carrier=request.carrier,
        source_file=request.file_path,
        mode=request.mode,
        auto_queue=validation["auto_queue"],
        review_queue=validation["review_queue"],
        rejected=validation["rejected"],
    )

    posting_report = None
    if request.mode == "live":
        posting_report = post_transactions_to_epic(validation["auto_queue"], mode="live")

    return {
        "run_id": run_id,
        "carrier": request.carrier,
        "source_file": request.file_path,
        "mode": request.mode,
        "total_parsed": validation["total"],
        "auto_approved": validation["auto_count"],
        "review_queue": validation["review_count"],
        "rejected": validation["rejected_count"],
        "posting_report": posting_report,
        "next_steps": (
            "Review the exception queue"
            if validation["review_count"] > 0
            else "All transactions processed."
        ),
    }


@router.post("/normalize")
async def normalize_only(
    request: IngestRequest,
    user: AuthenticatedUser = Depends(require_role(UserRole.ACCOUNTANT)),
) -> list[dict]:
    """Parse and normalize a file WITHOUT validation or staging. For debugging."""
    from mcp_server.tools.ingestion import ingest_statement as _ingest
    from mcp_server.tools.normalization import normalize_raw_rows

    run_id = str(uuid.uuid4())
    raw = _ingest(request.file_path, request.carrier, request.mode, run_id)
    transactions = normalize_raw_rows(raw)
    return [t.to_dict() for t in transactions]


@router.post("/validate")
async def validate_only(
    request: IngestRequest,
    user: AuthenticatedUser = Depends(require_role(UserRole.ACCOUNTANT)),
) -> dict:
    """Parse, normalize, and validate WITHOUT staging. Returns full validation report."""
    from mcp_server.tools.ingestion import ingest_statement as _ingest
    from mcp_server.tools.normalization import normalize_raw_rows
    from mcp_server.tools.validation import validate_transactions

    run_id = str(uuid.uuid4())
    raw = _ingest(request.file_path, request.carrier, request.mode, run_id)
    transactions = normalize_raw_rows(raw)
    validation = validate_transactions(transactions)

    return {
        "run_id": run_id,
        "total": validation["total"],
        "auto_count": validation["auto_count"],
        "review_count": validation["review_count"],
        "rejected_count": validation["rejected_count"],
        "auto_queue": [t.to_dict() for t in validation["auto_queue"]],
        "review_queue": [t.to_dict() for t in validation["review_queue"]],
        "rejected": [t.to_dict() for t in validation["rejected"]],
    }
