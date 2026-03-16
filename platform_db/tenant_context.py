"""
Multi-tenant context — per-request tenant isolation.
Uses contextvars so each API request gets its own tenant config.
"""

import contextvars
from dataclasses import dataclass
from typing import Optional


@dataclass
class TenantContext:
    """Per-tenant configuration resolved from the platform database."""
    tenant_id: str
    tenant_slug: str
    display_name: str

    # GCP / BigQuery — each tenant gets isolated datasets
    gcp_project: str
    bq_dataset: str                     # e.g. "acme_carrier_accounting"
    bq_staging_dataset: str             # e.g. "acme_staging"

    # Applied Epic — each agency has their own Epic credentials
    epic_sdk_url: str
    epic_api_key: str
    epic_agency_id: str
    epic_environment: str = "sandbox"

    # Anthropic — can share or per-tenant
    anthropic_api_key: str = ""

    # Thresholds — customizable per agency
    auto_post_threshold: float = 0.95
    review_threshold: float = 0.80
    default_mode: str = "trial"

    # Table helpers
    def policy_master_table(self) -> str:
        return f"{self.gcp_project}.{self.bq_dataset}.combined_policy_master"

    def shadow_table(self) -> str:
        return f"{self.gcp_project}.{self.bq_staging_dataset}.carrier_entries_shadow"

    def live_table(self) -> str:
        return f"{self.gcp_project}.{self.bq_dataset}.carrier_entries_live"

    def run_log_table(self) -> str:
        return f"{self.gcp_project}.{self.bq_dataset}.run_log"

    def audit_trail_table(self) -> str:
        return f"{self.gcp_project}.{self.bq_dataset}.audit_trail"


# Thread-safe per-request context variable
_tenant_var: contextvars.ContextVar[Optional[TenantContext]] = contextvars.ContextVar(
    "tenant_context", default=None
)


def set_tenant(ctx: TenantContext):
    """Set the tenant context for the current request."""
    _tenant_var.set(ctx)


def get_tenant() -> Optional[TenantContext]:
    """Get the current request's tenant context."""
    return _tenant_var.get()


def require_tenant() -> TenantContext:
    """Get the tenant context, raising if not set."""
    ctx = _tenant_var.get()
    if ctx is None:
        raise RuntimeError("No tenant context set — authentication required")
    return ctx
