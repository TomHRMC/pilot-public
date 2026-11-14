import uuid
from enum import Enum
from typing import Any

from pydantic import AwareDatetime
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import CITEXT, JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlmodel import Column, Field, SQLModel

from .mixins import AppendOnlyMixin, StandardAuditMixin


# --- Enums ---
class CustomerType(str, Enum):
    person = "person"
    company = "company"


# --- Dictionaries & Lookups ---
class CustomerLifecycleStatus(StandardAuditMixin, SQLModel, table=True):
    __tablename__ = "customer_lifecycle_status"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "code", name="uq_customer_lifecycle_status_tenant_code"
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID | None = Field(default=None, foreign_key="tenant.id")
    code: str = Field(nullable=False)
    name: str = Field(nullable=False)
    is_default: bool = Field(
        default=False,
        sa_column=Column(Boolean, server_default=text("false"), nullable=False),
    )
    is_active: bool = Field(
        default=True,
        sa_column=Column(Boolean, server_default=text("true"), nullable=False),
    )

    # Phase 6.0.1: Override audit fields with FK constraints
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )
    updated_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


class SiteLifecycleStatus(StandardAuditMixin, SQLModel, table=True):
    __tablename__ = "site_lifecycle_status"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "code", name="uq_site_lifecycle_status_tenant_code"
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID | None = Field(default=None, foreign_key="tenant.id")
    code: str = Field(nullable=False)
    name: str = Field(nullable=False)
    is_default: bool = Field(
        default=False,
        sa_column=Column(Boolean, server_default=text("false"), nullable=False),
    )
    is_active: bool = Field(
        default=True,
        sa_column=Column(Boolean, server_default=text("true"), nullable=False),
    )

    # Phase 6.0.1: Override audit fields with FK constraints
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )
    updated_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


class AddressType(StandardAuditMixin, SQLModel, table=True):
    __tablename__ = "address_type"

    code: str = Field(primary_key=True)
    tenant_id: uuid.UUID | None = Field(
        default=None, foreign_key="tenant.id", index=True
    )
    name: str = Field(nullable=False)
    is_default: bool = Field(
        default=False,
        sa_column=Column(Boolean, server_default=text("false"), nullable=False),
    )
    is_active: bool = Field(
        default=True,
        sa_column=Column(Boolean, server_default=text("true"), nullable=False),
    )

    # Phase 6.0.1: Override audit fields with FK constraints
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )
    updated_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


class ContactType(StandardAuditMixin, SQLModel, table=True):
    __tablename__ = "contact_type"

    code: str = Field(primary_key=True)
    tenant_id: uuid.UUID | None = Field(
        default=None, foreign_key="tenant.id", index=True
    )
    name: str = Field(nullable=False)
    is_default: bool = Field(
        default=False,
        sa_column=Column(Boolean, server_default=text("false"), nullable=False),
    )
    is_active: bool = Field(
        default=True,
        sa_column=Column(Boolean, server_default=text("true"), nullable=False),
    )

    # Phase 6.0.1: Override audit fields with FK constraints
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )
    updated_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


# --- Core CRM Entities ---
class Customer(StandardAuditMixin, SQLModel, table=True):
    __tablename__ = "customer"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "display_name", name="uq_customer_tenant_display_name"
        ),
        CheckConstraint("type IN ('person', 'company')", name="customer_type_chk"),
        CheckConstraint(
            "email IS NULL OR "
            "email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$'",
            name="customer_email_format_chk",
        ),
        CheckConstraint(
            "preferred_contact_channel IN ('sms', 'email')",
            name="customer_preferred_contact_channel_chk",
        ),
        # B11/A59: TCPA opt-in source validation
        CheckConstraint(
            "sms_opt_in_source IS NULL OR "
            "sms_opt_in_source IN ('explicit_checkbox', 'inbound_initiated', 'verbal_captured')",
            name="customer_sms_opt_in_source_chk",
        ),
        # DLC-1: Double opt-in verification status
        CheckConstraint(
            "sms_verification_status IN ('unverified','pending_verification','verified','opted_out')",
            name="customer_sms_verification_status_chk",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("tenant.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
    )
    type: str = Field(
        default="person",
        sa_column=Column(String, server_default=text("'person'"), nullable=False),
    )

    display_name: str = Field(nullable=False)
    first_name: str | None = Field(default=None)
    last_name: str | None = Field(default=None)
    company_name: str | None = Field(default=None)
    dba_name: str | None = Field(default=None)

    # Using CITEXT for case-insensitive email storage
    # Note: unique=True removed to allow multiple customers with same email (common in QuickBooks)
    email: str | None = Field(default=None, sa_column=Column(CITEXT))
    mobile_phone: str | None = Field(default=None)

    # B4/A21: customer's preferred outbound communication channel
    preferred_contact_channel: str = Field(
        default="sms",
        sa_column=Column(String(10), server_default=text("'sms'"), nullable=False),
    )

    locale: str | None = Field(default=None)
    timezone: str | None = Field(default=None)
    notes: str | None = Field(default=None)

    is_active: bool = Field(
        default=True,
        sa_column=Column(Boolean, server_default=text("true"), nullable=False),
    )
    lifecycle_status_id: uuid.UUID | None = Field(
        default=None, foreign_key="customer_lifecycle_status.id", index=True
    )

    # B11/A59: TCPA SMS consent fields
    sms_opted_out: bool = Field(
        default=False,
        sa_column=Column(Boolean, server_default=text("false"), nullable=False),
    )
    sms_opt_out_at: AwareDatetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    sms_opt_in_consent: bool = Field(
        default=False,
        sa_column=Column(Boolean, server_default=text("false"), nullable=False),
    )
    sms_opt_in_at: AwareDatetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    sms_opt_in_source: str | None = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )

    # DLC-1: Offline consent attestation audit fields
    sms_consent_attested_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            PG_UUID,
            ForeignKey("user.id", ondelete="RESTRICT"),
            nullable=True,
        ),
    )
    sms_consent_attested_at: AwareDatetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    sms_consent_ip_address: str | None = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    # DLC-1: Double opt-in state tracker
    # 'unverified' → 'pending_verification' (attestation) → 'verified' (YES reply) | 'opted_out' (STOP)
    sms_verification_status: str = Field(
        default="unverified",
        sa_column=Column(Text, server_default=text("'unverified'"), nullable=False),
    )

    # B11/F4: Routing fallback for inbound SMS thread assignment
    last_assigned_tech_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            PG_UUID,
            ForeignKey("user.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
    )

    # FIND-107 (B18): Customer-level taxability override — NULL = use line defaults
    taxability_code: str | None = Field(
        default=None,
        sa_column=Column(
            String,
            ForeignKey("taxability_code.code", ondelete="RESTRICT"),
            nullable=True,
        ),
    )

    # B20: card-on-file requirement
    card_required: bool = Field(
        default=False,
        sa_column=Column(Boolean, server_default=text("false"), nullable=False),
    )

    # Phase 6.0.1: Override audit fields with FK constraints
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )
    updated_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


class CustomerSmsConsentAudit(AppendOnlyMixin, SQLModel, table=True):
    """
    Append-only audit log for SMS consent lifecycle events per customer.
    Written on: attestation, double opt-in send, double opt-in confirmed, opt-out.
    Never mutated — no updated_at, no updated_by. DLC-1.
    """

    __tablename__ = "customer_sms_consent_audit"
    __table_args__ = (
        CheckConstraint(
            "action IN ('attested','double_opt_in_sent','double_opt_in_confirmed','opted_out')",
            name="customer_sms_consent_audit_action_chk",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    # created_at provided by AppendOnlyMixin; created_by also provided (nullable)
    tenant_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("tenant.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        )
    )
    customer_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("customer.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        )
    )
    attested_by: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("user.id", ondelete="RESTRICT"),
            nullable=False,
        )
    )
    ip_address: str = Field(sa_column=Column(Text, nullable=False))
    attested_at: AwareDatetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    consent_text_hash: str = Field(sa_column=Column(Text, nullable=False))
    action: str = Field(sa_column=Column(Text, nullable=False))


class Site(StandardAuditMixin, SQLModel, table=True):
    __tablename__ = "site"

    __table_args__ = (
        # NEW: Task 3 - Customer sites lookup composite index
        Index("idx_site_tenant_customer", "tenant_id", "customer_id"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID, ForeignKey("tenant.id", ondelete="RESTRICT"), nullable=False
        ),
    )
    customer_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("customer.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
    )

    name: str | None = Field(default=None)
    notes: str | None = Field(default=None)

    # Task 1-C-3: Structured access fields for field technician Voice AI read-out
    gate_code: str | None = Field(
        default=None,
        sa_column=Column(String(50), nullable=True),
    )
    access_instructions: str | None = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
    )
    hazard_notes: str | None = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
    )

    jurisdiction_code: str | None = Field(
        default=None
    )  # Tax jurisdiction (e.g., "US-TX-HARRIS")

    is_active: bool = Field(
        default=True,
        sa_column=Column(Boolean, server_default=text("true"), nullable=False),
    )
    lifecycle_status_id: uuid.UUID | None = Field(
        default=None, foreign_key="site_lifecycle_status.id", index=True
    )

    # CLASS-B1: Site type (commercial/residential/industrial) — TEXT+CHECK, 3-part NOT NULL migration
    site_type: str = Field(
        default="residential",
        sa_column=Column(Text, server_default=text("'residential'"), nullable=False),
    )

    # Phase 6.0.1: Override audit fields with FK constraints
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )
    updated_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


class Contact(StandardAuditMixin, SQLModel, table=True):
    __tablename__ = "contact"
    __table_args__ = (
        CheckConstraint(
            "(email IS NULL) OR (email ~* '^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$')",
            name="contact_email_format_chk",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("tenant.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
    )
    customer_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            PG_UUID,
            ForeignKey("customer.id", ondelete="RESTRICT"),
            nullable=True,
            index=True,
        ),
    )

    first_name: str | None = Field(default=None)
    last_name: str | None = Field(default=None)
    email: str | None = Field(default=None, sa_column=Column(CITEXT))
    mobile_phone: str | None = Field(default=None)

    locale: str | None = Field(default=None)
    timezone: str | None = Field(default=None)
    notes: str | None = Field(default=None)
    is_active: bool = Field(
        default=True,
        sa_column=Column(Boolean, server_default=text("true"), nullable=False),
    )

    # Phase 6.0.1: Override audit fields with FK constraints
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )
    updated_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


class Address(StandardAuditMixin, SQLModel, table=True):
    __tablename__ = "address"
    __table_args__ = (
        CheckConstraint(
            "(line1 IS NOT NULL AND city IS NOT NULL) OR (latitude IS NOT NULL AND longitude IS NOT NULL)",
            name="address_has_physical_or_gps_chk",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(foreign_key="tenant.id", nullable=False, index=True)

    line1: str | None = Field(default=None)
    line2: str | None = Field(default=None)
    line3: str | None = Field(default=None)
    city: str | None = Field(default=None)
    state: str | None = Field(default=None)
    postal_code: str | None = Field(default=None)
    country: str = Field(
        default="US",
        sa_column=Column(String, server_default=text("'US'"), nullable=False),
    )

    latitude: float | None = Field(default=None, sa_column=Column(Numeric(10, 7)))
    longitude: float | None = Field(default=None, sa_column=Column(Numeric(10, 7)))

    is_active: bool = Field(
        default=True,
        sa_column=Column(Boolean, server_default=text("true"), nullable=False),
    )

    # Phase 6.0.1: Override audit fields with FK constraints
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )
    updated_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


# --- Polymorphic Mappers ---
class EntityContact(StandardAuditMixin, SQLModel, table=True):
    __tablename__ = "entity_contact"
    __table_args__ = (
        UniqueConstraint(
            "entity_type_code",
            "entity_id",
            "contact_id",
            name="uq_entity_contact_entity_contact",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(foreign_key="tenant.id", nullable=False, index=True)
    entity_type_code: str = Field(foreign_key="entity_type.code", nullable=False)
    # Polymorphic ID: No strict foreign key constraint because it can point to multiple tables
    entity_id: uuid.UUID = Field(nullable=False)

    contact_id: uuid.UUID = Field(foreign_key="contact.id", nullable=False, index=True)
    contact_type_code: str = Field(
        foreign_key="contact_type.code", nullable=False, index=True
    )
    is_primary: bool = Field(
        default=False,
        sa_column=Column(Boolean, server_default=text("false"), nullable=False),
    )

    # Phase 6.0.1: Override audit fields with FK constraints
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )
    updated_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


class EntityAddress(StandardAuditMixin, SQLModel, table=True):
    __tablename__ = "entity_address"
    __table_args__ = (
        UniqueConstraint(
            "entity_type_code",
            "entity_id",
            "address_id",
            name="uq_entity_address_entity_address",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(foreign_key="tenant.id", nullable=False, index=True)
    entity_type_code: str = Field(foreign_key="entity_type.code", nullable=False)
    entity_id: uuid.UUID = Field(nullable=False)

    address_id: uuid.UUID = Field(foreign_key="address.id", nullable=False, index=True)
    address_type_code: str = Field(
        foreign_key="address_type.code", nullable=False, index=True
    )
    is_primary: bool = Field(
        default=False,
        sa_column=Column(Boolean, server_default=text("false"), nullable=False),
    )
    is_active: bool = Field(
        default=True,
        sa_column=Column(Boolean, server_default=text("true"), nullable=False),
    )

    # Phase 6.0.1: Override audit fields with FK constraints
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )
    updated_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


class ContactEndpoint(StandardAuditMixin, SQLModel, table=True):
    __tablename__ = "contact_endpoint"
    __table_args__ = (
        CheckConstraint(
            "(channel <> 'email') OR (value ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$')",
            name="contact_endpoint_email_format_chk",
        ),
        CheckConstraint(
            "channel IN ('email', 'sms')",
            name="contact_endpoint_channel_chk",
        ),
        CheckConstraint(
            "verification_status IN ('pending', 'verified', 'failed')",
            name="contact_endpoint_verification_status_chk",
        ),
        CheckConstraint(
            "consent_status IN ('unknown', 'opted_in', 'opted_out')",
            name="contact_endpoint_consent_status_chk",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(foreign_key="tenant.id", nullable=False, index=True)
    contact_id: uuid.UUID = Field(foreign_key="contact.id", nullable=False, index=True)
    channel: str = Field(nullable=False)  # 'email' | 'sms'
    value: str = Field(nullable=False)

    is_primary: bool = Field(
        default=False,
        sa_column=Column(Boolean, server_default=text("false"), nullable=False),
    )
    verification_status: str = Field(
        default="pending",
        sa_column=Column(String, server_default=text("'pending'"), nullable=False),
    )
    verified_at: AwareDatetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True))
    )

    consent_status: str = Field(
        default="unknown",
        sa_column=Column(String, server_default=text("'unknown'"), nullable=False),
    )
    consent_updated_at: AwareDatetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True))
    )

    # Safely renamed from metadata
    contextdata: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))
    is_active: bool = Field(
        default=True,
        sa_column=Column(Boolean, server_default=text("true"), nullable=False),
    )

    # Phase 6.0.1: Override audit fields with FK constraints
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )
    updated_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )
