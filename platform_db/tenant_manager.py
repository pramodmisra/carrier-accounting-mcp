"""
Tenant lifecycle management — create, provision, configure, deactivate.
Handles BQ dataset creation and DDL execution during onboarding.
"""

import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional
import structlog

from sqlalchemy.orm import Session

from platform_db.models import Tenant, User, TenantStatus, UserRole
from platform_db.tenant_context import TenantContext

log = structlog.get_logger(__name__)

DDL_DIR = Path(__file__).parent.parent / "data_lake" / "schemas"


class TenantManager:
    def __init__(self, db: Session):
        self.db = db

    def create_tenant(
        self,
        slug: str,
        display_name: str,
        gcp_project: str,
        admin_email: str,
        epic_sdk_url: str = "",
        epic_api_key: str = "",
        epic_agency_id: str = "",
        plan: str = "trial",
    ) -> Tenant:
        """
        Create a new tenant and provision their BigQuery datasets.
        Returns the Tenant object.
        """
        tenant_id = str(uuid.uuid4())
        bq_dataset = f"{slug}_carrier_accounting"
        bq_staging_dataset = f"{slug}_staging"

        tenant = Tenant(
            id=tenant_id,
            slug=slug,
            display_name=display_name,
            gcp_project=gcp_project,
            bq_dataset=bq_dataset,
            bq_staging_dataset=bq_staging_dataset,
            epic_sdk_url=epic_sdk_url,
            epic_api_key_encrypted=epic_api_key,  # TODO: encrypt
            epic_agency_id=epic_agency_id,
            plan=plan,
            status=TenantStatus.PROVISIONING.value,
        )
        self.db.add(tenant)

        # Create admin user
        admin_user = User(
            id=str(uuid.uuid4()),
            email=admin_email,
            tenant_id=tenant_id,
            role=UserRole.ADMIN.value,
        )
        self.db.add(admin_user)
        self.db.commit()

        # Provision BigQuery datasets
        try:
            self._provision_bigquery(tenant)
            tenant.status = TenantStatus.ACTIVE.value
            self.db.commit()
        except Exception as e:
            log.error("BQ provisioning failed", tenant=slug, error=str(e))
            tenant.status = TenantStatus.PROVISIONING.value
            self.db.commit()
            raise

        log.info("Tenant created", tenant=slug, admin=admin_email, plan=plan)
        return tenant

    def get_tenant(self, slug: str) -> Optional[Tenant]:
        return self.db.query(Tenant).filter(Tenant.slug == slug).first()

    def get_tenant_by_id(self, tenant_id: str) -> Optional[Tenant]:
        return self.db.query(Tenant).filter(Tenant.id == tenant_id).first()

    def to_context(self, tenant: Tenant) -> TenantContext:
        """Convert a Tenant DB row to a TenantContext for request scoping."""
        return TenantContext(
            tenant_id=tenant.id,
            tenant_slug=tenant.slug,
            display_name=tenant.display_name,
            gcp_project=tenant.gcp_project,
            bq_dataset=tenant.bq_dataset,
            bq_staging_dataset=tenant.bq_staging_dataset,
            epic_sdk_url=tenant.epic_sdk_url,
            epic_api_key=tenant.epic_api_key_encrypted,  # TODO: decrypt
            epic_agency_id=tenant.epic_agency_id,
            epic_environment=tenant.epic_environment,
            anthropic_api_key=tenant.anthropic_api_key_encrypted,  # TODO: decrypt
            auto_post_threshold=tenant.auto_post_threshold,
            review_threshold=tenant.review_threshold,
            default_mode=tenant.default_mode,
        )

    def deactivate_tenant(self, slug: str):
        tenant = self.get_tenant(slug)
        if tenant:
            tenant.status = TenantStatus.DEACTIVATED.value
            self.db.commit()
            log.info("Tenant deactivated", tenant=slug)

    def list_tenants(self, active_only: bool = True) -> list[Tenant]:
        query = self.db.query(Tenant)
        if active_only:
            query = query.filter(Tenant.status == TenantStatus.ACTIVE.value)
        return query.all()

    def add_user(self, tenant_id: str, email: str, role: str = "viewer") -> User:
        user = User(
            id=str(uuid.uuid4()),
            email=email,
            tenant_id=tenant_id,
            role=role,
        )
        self.db.add(user)
        self.db.commit()
        return user

    def _provision_bigquery(self, tenant: Tenant):
        """Create BQ datasets and tables for a new tenant."""
        from google.cloud import bigquery

        bq_client = bigquery.Client(project=tenant.gcp_project)

        # Create datasets
        for dataset_id in [tenant.bq_dataset, tenant.bq_staging_dataset]:
            dataset = bigquery.Dataset(f"{tenant.gcp_project}.{dataset_id}")
            dataset.location = "US"
            bq_client.create_dataset(dataset, exists_ok=True)
            log.info("BQ dataset created", dataset=dataset_id)

        # Run DDL — replace dataset references with tenant-specific ones
        ddl_file = DDL_DIR / "staging_tables.sql"
        if ddl_file.exists():
            ddl = ddl_file.read_text()
            ddl = ddl.replace("sw_staging", tenant.bq_staging_dataset)
            ddl = ddl.replace("sw_carrier_accounting", tenant.bq_dataset)

            # Execute each statement separately
            for statement in ddl.split(";"):
                statement = statement.strip()
                if statement and not statement.startswith("--"):
                    try:
                        bq_client.query(statement).result()
                    except Exception as e:
                        log.warning("DDL statement failed", error=str(e), sql=statement[:100])

        audit_file = DDL_DIR / "audit_tables.sql"
        if audit_file.exists():
            ddl = audit_file.read_text()
            ddl = ddl.replace("sw_carrier_accounting", tenant.bq_dataset)
            for statement in ddl.split(";"):
                statement = statement.strip()
                if statement and not statement.startswith("--"):
                    try:
                        bq_client.query(statement).result()
                    except Exception as e:
                        log.warning("DDL statement failed", error=str(e), sql=statement[:100])

        log.info("BQ provisioning complete", tenant=tenant.slug)
