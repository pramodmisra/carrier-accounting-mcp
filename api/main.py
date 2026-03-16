"""
Carrier Accounting API — FastAPI REST layer.
Wraps all 21 MCP tools into a standard REST API with auth and multi-tenancy.

Run with: uvicorn api.main:app --reload --port 8001
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import (
    health,
    ingestion,
    review,
    posting,
    monitoring,
    reconciliation,
    carriers,
    admin,
    sandbox,
    onboarding,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Carrier Accounting API starting...")
    print("  Docs: http://localhost:8001/docs")
    print("  Health: http://localhost:8001/api/health")
    yield
    # Shutdown
    print("Carrier Accounting API shutting down...")


app = FastAPI(
    title="Carrier Accounting API",
    description=(
        "Insurance carrier statement processing for Applied Epic agencies. "
        "Ingest PDFs/Excel, validate against BigQuery, post to Epic."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — allow the Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",     # Next.js dev
        "http://localhost:8000",     # Streamlit
        "https://agency.5gvector.com",
        "https://*.5gvector.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount all route groups
app.include_router(health.router)
app.include_router(sandbox.router)       # Sandbox — no auth needed
app.include_router(onboarding.router)    # Onboarding — connection setup
app.include_router(ingestion.router)
app.include_router(review.router)
app.include_router(posting.router)
app.include_router(monitoring.router)
app.include_router(reconciliation.router)
app.include_router(carriers.router)
app.include_router(admin.router)
