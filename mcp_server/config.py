"""All configuration for the Carrier Accounting MCP Server."""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # --- GCP / BigQuery ---
    GCP_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT", "snellings-walters-prod")
    BQ_DATASET = os.getenv("BIGQUERY_DATASET", "sw_carrier_accounting")
    BQ_STAGING_DATASET = os.getenv("BIGQUERY_STAGING_DATASET", "sw_staging")

    # --- Applied Epic ---
    EPIC_SDK_URL = os.getenv("APPLIED_EPIC_SDK_URL", "")
    EPIC_API_KEY = os.getenv("APPLIED_EPIC_API_KEY", "")
    EPIC_AGENCY_ID = os.getenv("APPLIED_EPIC_AGENCY_ID", "")
    EPIC_ENVIRONMENT = os.getenv("APPLIED_EPIC_ENVIRONMENT", "sandbox")

    # --- Anthropic ---
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

    # --- Thresholds ---
    AUTO_POST_THRESHOLD = float(os.getenv("AUTO_POST_THRESHOLD", "0.95"))
    REVIEW_THRESHOLD = float(os.getenv("REVIEW_THRESHOLD", "0.80"))

    # --- Defaults ---
    DEFAULT_MODE = os.getenv("DEFAULT_MODE", "trial")

    # --- Table helpers ---
    @classmethod
    def policy_master_table(cls) -> str:
        return f"{cls.GCP_PROJECT}.{cls.BQ_DATASET}.combined_policy_master"

    @classmethod
    def shadow_table(cls) -> str:
        return f"{cls.GCP_PROJECT}.{cls.BQ_STAGING_DATASET}.carrier_entries_shadow"

    @classmethod
    def live_table(cls) -> str:
        return f"{cls.GCP_PROJECT}.{cls.BQ_DATASET}.carrier_entries_live"

    @classmethod
    def run_log_table(cls) -> str:
        return f"{cls.GCP_PROJECT}.{cls.BQ_DATASET}.run_log"

    @classmethod
    def audit_trail_table(cls) -> str:
        return f"{cls.GCP_PROJECT}.{cls.BQ_DATASET}.audit_trail"
