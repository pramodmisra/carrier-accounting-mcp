"""
Platform database models — tenant registry, users, billing.
Uses SQLAlchemy for the platform PostgreSQL database.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import (
    Column, String, DateTime, Float, Boolean, ForeignKey, Text, JSON
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class UserRole(str, Enum):
    ADMIN = "admin"             # Full access, tenant settings, user management
    ACCOUNTANT = "accountant"   # Ingest, review, post, reconcile
    REVIEWER = "reviewer"       # View + approve/reject only
    VIEWER = "viewer"           # Read-only access to dashboards


class TenantStatus(str, Enum):
    PROVISIONING = "provisioning"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DEACTIVATED = "deactivated"


class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(String, primary_key=True)
    slug = Column(String, unique=True, nullable=False, index=True)
    display_name = Column(String, nullable=False)

    # GCP
    gcp_project = Column(String, nullable=False)
    bq_dataset = Column(String, nullable=False)
    bq_staging_dataset = Column(String, nullable=False)

    # Applied Epic (encrypted at rest)
    epic_sdk_url = Column(String, default="")
    epic_api_key_encrypted = Column(Text, default="")
    epic_agency_id = Column(String, default="")
    epic_environment = Column(String, default="sandbox")

    # Anthropic
    anthropic_api_key_encrypted = Column(Text, default="")

    # Thresholds
    auto_post_threshold = Column(Float, default=0.95)
    review_threshold = Column(Float, default=0.80)
    default_mode = Column(String, default="trial")

    # Metadata
    status = Column(String, default=TenantStatus.PROVISIONING.value)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Billing
    plan = Column(String, default="trial")  # trial | starter | professional | enterprise
    stripe_customer_id = Column(String, nullable=True)

    # Relationships
    users = relationship("User", back_populates="tenant")
    carrier_configs = relationship("TenantCarrierConfig", back_populates="tenant")


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True)
    email = Column(String, nullable=False, index=True)
    name = Column(String, default="")
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    role = Column(String, default=UserRole.VIEWER.value)
    auth_provider_sub = Column(String, nullable=True, index=True)  # Auth0/Clerk subject ID
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login_at = Column(DateTime, nullable=True)

    tenant = relationship("Tenant", back_populates="users")


class TenantCarrierConfig(Base):
    __tablename__ = "tenant_carrier_configs"

    id = Column(String, primary_key=True)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    carrier_slug = Column(String, nullable=False)
    display_name = Column(String, default="")
    field_mappings = Column(JSON, default=dict)  # CarrierSchema fields as JSON
    portal_config = Column(JSON, default=dict)   # Portal URL, selectors
    is_active = Column(Boolean, default=True)
    mode = Column(String, default="trial")       # trial | live per carrier
    created_at = Column(DateTime, default=datetime.utcnow)

    tenant = relationship("Tenant", back_populates="carrier_configs")
