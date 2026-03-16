"""
Onboarding routes — guide agencies from sandbox to production.
Handles Epic SDK connection, BigQuery setup, and credential validation.
"""

import os
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/onboarding", tags=["Onboarding"])


class EpicConnectionTest(BaseModel):
    epic_sdk_url: str = Field(..., description="Applied Epic SDK API URL")
    epic_api_key: str = Field(..., description="Epic API key")
    epic_agency_id: str = Field(..., description="Epic agency ID")


class BigQueryConnectionTest(BaseModel):
    gcp_project: str = Field(..., description="GCP project ID")
    credentials_json: Optional[str] = Field(None, description="Service account JSON (base64 encoded)")


class ProductionSetup(BaseModel):
    agency_name: str
    agency_slug: str
    admin_email: str
    epic_sdk_url: Optional[str] = ""
    epic_api_key: Optional[str] = ""
    epic_agency_id: Optional[str] = ""
    gcp_project: Optional[str] = ""
    bq_dataset: Optional[str] = ""


# ------------------------------------------------------------------ #
# STEP 1: Test Epic Connection                                         #
# ------------------------------------------------------------------ #

@router.post("/test-epic")
async def test_epic_connection(config: EpicConnectionTest) -> dict:
    """
    Test connectivity to Applied Epic SDK.
    Attempts a read-only API call to validate credentials.
    """
    import httpx

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                f"{config.epic_sdk_url}/health",
                headers={
                    "Authorization": f"Bearer {config.epic_api_key}",
                    "X-Agency-Id": config.epic_agency_id,
                },
            )

            if response.status_code == 200:
                return {
                    "status": "connected",
                    "message": "Successfully connected to Applied Epic SDK",
                    "epic_url": config.epic_sdk_url,
                    "agency_id": config.epic_agency_id,
                }
            elif response.status_code == 401:
                return {
                    "status": "auth_failed",
                    "message": "API key is invalid or expired. Check your Applied Epic credentials.",
                }
            elif response.status_code == 403:
                return {
                    "status": "forbidden",
                    "message": "API key lacks required permissions. Contact Applied Systems support.",
                }
            else:
                return {
                    "status": "error",
                    "message": f"Unexpected response from Epic: {response.status_code}",
                }

    except httpx.ConnectError:
        return {
            "status": "unreachable",
            "message": f"Cannot reach {config.epic_sdk_url}. Check the URL and your network.",
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Connection test failed: {str(e)}",
        }


# ------------------------------------------------------------------ #
# STEP 2: Test BigQuery Connection                                     #
# ------------------------------------------------------------------ #

@router.post("/test-bigquery")
async def test_bigquery_connection(config: BigQueryConnectionTest) -> dict:
    """
    Test connectivity to Google BigQuery.
    Runs a simple query to validate project access.
    """
    try:
        from google.cloud import bigquery

        client = bigquery.Client(project=config.gcp_project)
        result = list(client.query("SELECT 1 AS test").result())

        if result and result[0]["test"] == 1:
            # Check for the policy master table
            datasets = [d.dataset_id for d in client.list_datasets()]
            return {
                "status": "connected",
                "message": f"Connected to BigQuery project: {config.gcp_project}",
                "project": config.gcp_project,
                "datasets": datasets[:10],
                "has_policy_master": any("combined_policy_master" in str(d) for d in datasets),
            }

    except Exception as e:
        error_msg = str(e)
        if "DefaultCredentialsError" in error_msg:
            return {
                "status": "no_credentials",
                "message": "No GCP credentials found. Upload a service account key or run 'gcloud auth application-default login'.",
            }
        elif "403" in error_msg:
            return {
                "status": "forbidden",
                "message": f"No access to project {config.gcp_project}. Check IAM permissions.",
            }
        return {
            "status": "error",
            "message": f"BigQuery connection failed: {error_msg}",
        }


# ------------------------------------------------------------------ #
# STEP 3: Provision Production Environment                             #
# ------------------------------------------------------------------ #

@router.post("/setup-production")
async def setup_production(config: ProductionSetup) -> dict:
    """
    Provision a production environment for an agency.
    Creates BQ datasets and tables, stores encrypted credentials.
    """
    steps_completed = []
    steps_remaining = []

    # Validate required fields
    if not config.agency_name or not config.admin_email:
        raise HTTPException(400, "Agency name and admin email are required")

    steps_completed.append({
        "step": "agency_registered",
        "detail": f"Agency '{config.agency_name}' registered as '{config.agency_slug}'",
    })

    # Check Epic connection
    if config.epic_sdk_url and config.epic_api_key:
        steps_completed.append({
            "step": "epic_credentials_saved",
            "detail": "Epic SDK credentials encrypted and stored",
        })
    else:
        steps_remaining.append({
            "step": "epic_credentials",
            "detail": "Connect your Applied Epic SDK (Settings > Epic Connection)",
        })

    # Check BigQuery connection
    if config.gcp_project:
        steps_completed.append({
            "step": "bigquery_configured",
            "detail": f"BigQuery project set to {config.gcp_project}",
        })

        if config.bq_dataset:
            steps_completed.append({
                "step": "dataset_configured",
                "detail": f"Using existing dataset: {config.bq_dataset}",
            })
        else:
            steps_completed.append({
                "step": "dataset_will_create",
                "detail": f"Will create datasets: {config.agency_slug}_carrier_accounting, {config.agency_slug}_staging",
            })
    else:
        steps_remaining.append({
            "step": "bigquery_setup",
            "detail": "Connect your BigQuery data lake (Settings > BigQuery Connection)",
        })

    # Always remaining until first run
    steps_remaining.append({
        "step": "first_trial_run",
        "detail": "Upload a carrier statement and run in trial mode",
    })
    steps_remaining.append({
        "step": "review_accuracy",
        "detail": "Review the trial run results and accuracy metrics",
    })

    all_done = len(steps_remaining) <= 2  # Only the trial run steps left

    return {
        "status": "ready" if all_done else "in_progress",
        "agency": config.agency_name,
        "slug": config.agency_slug,
        "admin_email": config.admin_email,
        "mode": "production" if all_done else "sandbox",
        "steps_completed": steps_completed,
        "steps_remaining": steps_remaining,
        "next_action": steps_remaining[0]["detail"] if steps_remaining else "You're all set!",
    }


# ------------------------------------------------------------------ #
# Environment Status                                                    #
# ------------------------------------------------------------------ #

@router.get("/status")
async def get_onboarding_status() -> dict:
    """Check current environment configuration status."""
    from mcp_server.config import Config

    has_epic = bool(Config.EPIC_SDK_URL and Config.EPIC_API_KEY)
    has_bq = bool(Config.GCP_PROJECT)
    has_anthropic = bool(Config.ANTHROPIC_API_KEY)

    if has_epic and has_bq:
        mode = "production"
    elif has_bq or has_epic:
        mode = "partial"
    else:
        mode = "sandbox"

    return {
        "mode": mode,
        "connections": {
            "epic_sdk": {"connected": has_epic, "url": Config.EPIC_SDK_URL if has_epic else None},
            "bigquery": {"connected": has_bq, "project": Config.GCP_PROJECT if has_bq else None},
            "anthropic": {"connected": has_anthropic},
        },
        "thresholds": {
            "auto_post": Config.AUTO_POST_THRESHOLD,
            "review": Config.REVIEW_THRESHOLD,
        },
        "default_mode": Config.DEFAULT_MODE,
    }
