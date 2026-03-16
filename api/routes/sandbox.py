"""
Sandbox routes — fully functional demo environment.
No credentials needed. Returns realistic synthetic data so agencies
can evaluate all features before connecting their own systems.
"""

import uuid
import shutil
from pathlib import Path
from typing import Optional
from datetime import date

from fastapi import APIRouter, UploadFile, File, Query

from mcp_server.services.sandbox.demo_data import (
    generate_demo_daily_metrics,
    generate_demo_run_history,
    generate_demo_carrier_accuracy,
    generate_demo_exception_queue,
    generate_demo_transactions,
    generate_demo_reconciliation,
    generate_demo_trial_diff,
    DEMO_CARRIERS,
)

router = APIRouter(prefix="/api/sandbox", tags=["Sandbox"])

SANDBOX_UPLOAD_DIR = Path("uploads/sandbox")

# ------------------------------------------------------------------ #
# DASHBOARD / MONITORING                                               #
# ------------------------------------------------------------------ #

@router.get("/metrics/daily")
async def sandbox_daily_metrics(target_date: Optional[str] = None) -> dict:
    """Sandbox daily scorecard — realistic demo data, no BQ needed."""
    return generate_demo_daily_metrics()


@router.get("/metrics/carrier/{carrier}")
async def sandbox_carrier_accuracy(carrier: str, days: int = 30) -> dict:
    return generate_demo_carrier_accuracy(carrier, days)


@router.get("/runs")
async def sandbox_run_history(days: int = 7) -> list[dict]:
    return generate_demo_run_history(days)


@router.get("/runs/{run_id}")
async def sandbox_run_detail(run_id: str) -> dict:
    txns = generate_demo_transactions(count=20)
    return {
        "run": {
            "run_id": run_id,
            "carrier": "hartford",
            "source_file": "Hartford May 2025.pdf",
            "mode": "trial",
            "total_transactions": len(txns),
            "auto_approved": sum(1 for t in txns if t["auto_approved"]),
            "review_queue": sum(1 for t in txns if t["status"] == "review"),
            "status": "completed",
        },
        "transactions": txns,
        "transaction_count": len(txns),
    }


# ------------------------------------------------------------------ #
# INGESTION                                                            #
# ------------------------------------------------------------------ #

@router.post("/upload")
async def sandbox_upload(file: UploadFile = File(...)) -> dict:
    """Upload a file in sandbox mode — saved locally, processed with demo pipeline."""
    file_id = str(uuid.uuid4())
    dest_dir = SANDBOX_UPLOAD_DIR / file_id
    dest_dir.mkdir(parents=True, exist_ok=True)

    dest = dest_dir / file.filename
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)

    return {
        "file_id": file_id,
        "filename": file.filename,
        "file_path": str(dest),
        "size_bytes": dest.stat().st_size,
        "mode": "sandbox",
    }


@router.post("/ingest")
async def sandbox_ingest(
    file_path: str,
    carrier: str = "hartford",
    mode: str = "trial",
) -> dict:
    """
    Sandbox ingestion — runs REAL parsing on the uploaded file,
    but uses demo data for validation/scoring (no BQ needed).
    """
    from mcp_server.tools.ingestion import ingest_statement

    run_id = str(uuid.uuid4())

    # Real parsing
    try:
        raw = ingest_statement(file_path, carrier, mode, run_id)
        row_count = len(raw.get("raw_rows", []))
    except Exception as e:
        row_count = 0
        raw = {"raw_rows": [], "error": str(e)}

    # Simulate validation results (no BQ needed)
    auto = max(1, int(row_count * 0.85))
    review = max(0, row_count - auto)

    return {
        "run_id": run_id,
        "carrier": carrier,
        "source_file": file_path,
        "mode": "sandbox",
        "total_parsed": row_count,
        "auto_approved": auto,
        "review_queue": review,
        "rejected": 0,
        "posting_report": None,
        "columns_detected": raw.get("columns", []),
        "sample_rows": raw.get("raw_rows", [])[:3],
        "next_steps": (
            f"Parsed {row_count} rows from your file. "
            "In production mode, these would be validated against BigQuery and scored."
        ),
    }


@router.post("/ingest-demo")
async def sandbox_ingest_demo(carrier: str = "hartford") -> dict:
    """Run ingestion with built-in demo data (no file upload needed)."""
    run_id = str(uuid.uuid4())
    txns = generate_demo_transactions(carrier=carrier, count=25)
    auto = sum(1 for t in txns if t["auto_approved"])
    review = len(txns) - auto
    return {
        "run_id": run_id,
        "carrier": carrier,
        "source_file": f"[Demo] {DEMO_CARRIERS.get(carrier, {}).get('display', carrier)} statement",
        "mode": "sandbox",
        "total_parsed": len(txns),
        "auto_approved": auto,
        "review_queue": review,
        "rejected": 0,
        "transactions": txns[:5],
        "next_steps": "Demo run complete. Try the Review Queue to approve/reject transactions.",
    }


# ------------------------------------------------------------------ #
# REVIEW QUEUE                                                         #
# ------------------------------------------------------------------ #

@router.get("/queue")
async def sandbox_queue(
    target_date: Optional[str] = None,
    carrier: Optional[str] = None,
) -> list[dict]:
    queue = generate_demo_exception_queue(count=8)
    if carrier:
        queue = [t for t in queue if t["carrier"] == carrier]
    return queue


@router.post("/transactions/{transaction_id}/approve")
async def sandbox_approve(transaction_id: str, reviewer: str = "Demo User") -> dict:
    return {"transaction_id": transaction_id, "status": "approved", "reviewer": reviewer,
            "message": "Transaction approved (sandbox mode — no BQ write)"}


@router.post("/transactions/{transaction_id}/reject")
async def sandbox_reject(transaction_id: str, reviewer: str = "Demo User", reason: str = "Demo rejection") -> dict:
    return {"transaction_id": transaction_id, "status": "rejected", "reviewer": reviewer,
            "reason": reason, "message": "Transaction rejected (sandbox mode — no BQ write)"}


# ------------------------------------------------------------------ #
# RECONCILIATION / REPORTS                                             #
# ------------------------------------------------------------------ #

@router.get("/reconciliation")
async def sandbox_reconciliation(run_id: Optional[str] = None) -> dict:
    return generate_demo_reconciliation(run_id)


@router.get("/trial-diff")
async def sandbox_trial_diff(run_id: Optional[str] = None) -> dict:
    return generate_demo_trial_diff(run_id)


# ------------------------------------------------------------------ #
# SCORING                                                              #
# ------------------------------------------------------------------ #

@router.post("/score-check")
async def sandbox_score_check(
    carrier: str = "hartford",
    policy_number: str = "HTF-123456",
    client_name: str = "Apex Manufacturing LLC",
    amount: str = "1500.00",
) -> dict:
    """Demo confidence scoring — returns realistic scores without BQ."""
    import random
    score = round(random.uniform(0.82, 0.99), 4)
    return {
        "confidence_score": score,
        "classification": "auto" if score >= 0.95 else "review" if score >= 0.80 else "reject",
        "confidence_factors": {
            "policy_match": round(random.uniform(0.8, 1.0), 2),
            "client_name_match": round(random.uniform(0.7, 1.0), 2),
            "amount_reasonable": round(random.uniform(0.6, 1.0), 2),
            "date_valid": 1.0,
            "not_duplicate": 1.0,
        },
        "validation_warnings": ["Demo mode — no real validation performed"],
        "validation_errors": [],
        "policy_found": True,
        "is_duplicate": False,
        "epic_policy_id": "EP-DEMO-001",
    }


# ------------------------------------------------------------------ #
# CARRIERS                                                             #
# ------------------------------------------------------------------ #

@router.get("/carriers")
async def sandbox_carriers() -> dict:
    carriers = []
    for slug, info in DEMO_CARRIERS.items():
        carriers.append({
            "carrier_slug": slug,
            "display_name": info["display"],
            "policy_number_field": "Policy Number",
            "premium_field": "Premium",
            "mode": "trial",
        })
    return {"carriers": carriers, "total": len(carriers)}


# ------------------------------------------------------------------ #
# EPIC IMPORT                                                          #
# ------------------------------------------------------------------ #

@router.post("/runs/{run_id}/generate-import")
async def sandbox_generate_import(run_id: str) -> dict:
    return {
        "status": "generated",
        "run_id": run_id,
        "file_path": f"/exports/demo_epic_import_{run_id[:8]}.csv",
        "row_count": 25,
        "total_amount": "34,521.87",
        "mode": "sandbox",
        "message": "Demo CSV generated. In production, this creates a real Epic-compatible import file.",
        "preview": [
            {"PolicyNumber": "HTF-123456", "ClientName": "Apex Manufacturing", "Amount": "1500.00", "TransactionType": "premium"},
            {"PolicyNumber": "HTF-789012", "ClientName": "Brightside Properties", "Amount": "3200.00", "TransactionType": "commission"},
        ],
    }
