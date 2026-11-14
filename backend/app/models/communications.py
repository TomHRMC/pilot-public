# backend/app/models/communications.py
"""
Customer Communications models — B4, B15, B20/A94

CommunicationTemplate: lookup table for MVP templates (system + tenant-specific).
CustomerCommunication:  durable send log; one row per dispatched message.
EmailTemplate (B15/A82): system-wide email template registry (16 templates).
CustomerCommTemplateType (B20/A94): catalog of comm template types — replaces CHECK constraint.

Import path: from app.models.communications import CommunicationTemplate, CustomerCommunication, EmailTemplate, CustomerCommTemplateType
"""

import uuid
from typing import Any

from pydantic import AwareDatetime
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlmodel import Column, Field, SQLModel

from .mixins import AppendOnlyMixin, StandardAuditMixin


class CommunicationTemplate(StandardAuditMixin, SQLModel, table=True):
    __tablename__ = "communication_template"
    __table_args__ = (
        CheckConstraint(
            "channel IN ('sms', 'email')",
            name="communication_template_channel_chk",
        ),
        # B20/A94: communication_template_code_chk removed — replaced by FK to customer_comm_template_type
        CheckConstraint(
            "channel <> 'email' OR subject IS NOT NULL",
            name="communication_template_email_subject_chk",
        ),
        ForeignKeyConstraint(
            ["template_code"],
            ["customer_comm_template_type.code"],
            ondelete="RESTRICT",
            name="fk_communication_template_type",
        ),
        Index("idx_communication_template_tenant_id", "tenant_id"),
        Index("idx_communication_template_code_channel", "template_code", "channel"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    # NULL = system-level template; NOT NULL = tenant-specific customization
    tenant_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            PG_UUID,
            ForeignKey("tenant.id", ondelete="RESTRICT"),
            nullable=True,
        ),
    )

    template_code: str = Field(nullable=False)
    channel: str = Field(nullable=False)  # 'sms' | 'email'
    subject: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    body_template: str = Field(sa_column=Column(Text, nullable=False))

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


class CustomerCommunication(StandardAuditMixin, SQLModel, table=True):
    __tablename__ = "customer_communication"
    __table_args__ = (
        CheckConstraint(
            "channel IN ('sms', 'email')",
            name="customer_communication_channel_chk",
        ),
        CheckConstraint(
            "actual_channel IN ('sms', 'email')",
            name="customer_communication_actual_channel_chk",
        ),
        CheckConstraint(
            "status IN ('pending', 'sent', 'failed', 'canceled')",
            name="customer_communication_status_chk",
        ),
        # B20/A94: customer_communication_template_code_chk removed — replaced by FK to customer_comm_template_type
        ForeignKeyConstraint(
            ["template_code"],
            ["customer_comm_template_type.code"],
            ondelete="RESTRICT",
            name="fk_comm_template_type",
        ),
        Index("idx_customer_communication_tenant_id", "tenant_id"),
        Index("idx_customer_communication_customer_id", "customer_id"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    # Tenant + CRM FKs
    tenant_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("tenant.id", ondelete="RESTRICT"),
            nullable=False,
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
    job_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            PG_UUID,
            ForeignKey("job.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
    )
    sender_user_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("user.id", ondelete="RESTRICT"),
            nullable=False,
        )
    )

    # Template reference
    template_code: str = Field(nullable=False)
    template_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            PG_UUID,
            ForeignKey("communication_template.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    # Rendered content (server-side at send time)
    rendered_subject: str | None = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    rendered_message: str = Field(sa_column=Column(Text, nullable=False))

    # Channel fields (A4 base + A21 override audit)
    channel: str = Field(nullable=False)  # 'sms' | 'email'
    customer_preferred_channel: str | None = Field(
        default=None,
        sa_column=Column(String(10), nullable=True),
    )
    actual_channel: str = Field(nullable=False)  # 'sms' | 'email'
    channel_override_flag: bool = Field(
        default=False,
        sa_column=Column(Boolean, server_default=text("false"), nullable=False),
    )

    # Delivery tracking
    status: str = Field(
        default="pending",
        sa_column=Column(String, server_default=text("'pending'"), nullable=False),
    )
    sent_at: AwareDatetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    notification_outbox_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            PG_UUID,
            ForeignKey("notification_outbox.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
    )

    # Variables snapshot (for audit/preview reproducibility)
    variables_json: dict[str, Any] | None = Field(
        default=None, sa_column=Column(JSONB, nullable=True)
    )

    # B11/A60: back-link to thread for B4/B11 coexistence
    thread_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            PG_UUID,
            ForeignKey("customer_communication_thread.id", ondelete="SET NULL"),
            nullable=True,
        ),
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


# ─────────────────────────────────────────────────────────────────────────────
# B15/A82 — Email Template Registry
# ─────────────────────────────────────────────────────────────────────────────


class EmailTemplate(StandardAuditMixin, SQLModel, table=True):
    """
    System-wide email template registry.

    Each row is a named template with Jinja2-style {{variable}} syntax.
    System-seeded at migration time; operators can edit via admin UI.
    No tenant_id — one set of templates applies to all tenants.
    Per-tenant customisation is handled at the branding layer (TenantEmailBranding).

    Mixin: StandardAuditMixin — full audit trail tracks who last modified template copy.
    """

    __tablename__ = "email_template"
    __table_args__ = (
        CheckConstraint(
            "category IN ('customer_facing', 'internal')",
            name="email_template_category_chk",
        ),
    )

    # PK is the slug-style template identifier (not a UUID)
    template_id: str = Field(primary_key=True)

    display_name: str = Field(nullable=False)
    category: str = Field(nullable=False)  # 'customer_facing' | 'internal'

    subject_template: str = Field(sa_column=Column(Text, nullable=False))
    body_html_template: str = Field(sa_column=Column(Text, nullable=False))
    body_plain_template: str = Field(sa_column=Column(Text, nullable=False))

    variables: Any = Field(
        default_factory=list,
        sa_column=Column(JSONB, nullable=False, server_default=text("'[]'::jsonb")),
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


# ─────────────────────────────────────────────────────────────────────────────
# B20/A94 — Customer Communication Template Type Catalog
# ─────────────────────────────────────────────────────────────────────────────


class CustomerCommTemplateType(StandardAuditMixin, SQLModel, table=True):
    """
    Catalog of customer communication template types — A94, B20 Task 13.

    Each row defines a type of customer-facing communication (e.g. 'on_my_way',
    'invoice_sent'). Replaces the raw CHECK constraint on
    customer_communication.template_code and communication_template.template_code.

    PK is the code string (e.g. 'on_my_way') — matches existing FK values in both tables.
    slug decouples UI identity from PK for future renames.
    is_active=false rows are pre-registered Phase 2 templates — no schema migration needed to activate.
    is_system=false reserved for tenant-custom types (Phase 2+).
    """

    __tablename__ = "customer_comm_template_type"
    __table_args__ = (
        CheckConstraint(
            "category IN ('pre_appointment','quoting','during_job','post_job','relationship','exception')",
            name="customer_comm_template_type_category_chk",
        ),
        CheckConstraint(
            "preferred_channel IS NULL OR preferred_channel IN ('sms','email','both')",
            name="customer_comm_template_type_preferred_channel_chk",
        ),
        CheckConstraint(
            "initiator IN ('tech','owner','system')",
            name="customer_comm_template_type_initiator_chk",
        ),
        CheckConstraint(
            "send_mode IN ('manual','automated','both')",
            name="customer_comm_template_type_send_mode_chk",
        ),
        Index("idx_customer_comm_template_type_is_active", "is_active"),
        Index("idx_customer_comm_template_type_category", "category"),
    )

    code: str = Field(primary_key=True)
    slug: str = Field(sa_column=Column(String, nullable=False, unique=True))
    name: str = Field(nullable=False)
    description: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    category: str = Field(nullable=False)
    preferred_channel: str | None = Field(
        default=None, sa_column=Column(String, nullable=True)
    )
    initiator: str = Field(
        default="tech",
        sa_column=Column(String, server_default=text("'tech'"), nullable=False),
    )
    requires_approval: bool = Field(
        default=False,
        sa_column=Column(Boolean, server_default=text("false"), nullable=False),
    )
    send_mode: str = Field(
        default="manual",
        sa_column=Column(String, server_default=text("'manual'"), nullable=False),
    )
    trigger_event: str | None = Field(
        default=None, sa_column=Column(String, nullable=True)
    )
    is_system: bool = Field(
        default=True,
        sa_column=Column(Boolean, server_default=text("true"), nullable=False),
    )
    is_active: bool = Field(
        default=True,
        sa_column=Column(Boolean, server_default=text("true"), nullable=False),
    )
    sort_order: int = Field(
        default=0,
        sa_column=Column(Integer, server_default=text("0"), nullable=False),
    )

    # Phase 6.0.1 pattern: Override audit fields with FK constraints
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )
    updated_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


# ─── UserSmsConsentAudit ──────────────────────────────────────────────────────


class UserSmsConsentAudit(AppendOnlyMixin, SQLModel, table=True):
    """
    Append-only audit log for SMS consent lifecycle events per tenant owner.

    SIGNUP-C / Pathway C — Pilot→owner platform notifications (account, billing
    & security alerts). Mirrors ``customer_sms_consent_audit`` (DLC-1) for the
    owner surface. Written on: attestation (signup checkbox), double opt-in send,
    double opt-in confirmed (YES reply), opt-out (STOP reply).

    Never mutated — no ``updated_at``, no ``updated_by``. Append-only immutability
    is enforced at the ORM layer via ``AppendOnlyMixin`` (no DB trigger), matching
    the established consent-audit pattern (MCP-verified: the mirror source carries
    no triggers).

    FKs all ``ON DELETE RESTRICT`` (mirrors ``customer_sms_consent_audit``).
    """

    __tablename__ = "user_sms_consent_audit"
    __table_args__ = (
        CheckConstraint(
            "action IN ('attested','double_opt_in_sent','double_opt_in_confirmed','opted_out')",
            name="user_sms_consent_audit_action_chk",
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
    user_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("user.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        )
    )
    user_endpoint_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            PG_UUID,
            ForeignKey("user_endpoint.id", ondelete="RESTRICT"),
            nullable=True,
        ),
    )
    action: str = Field(sa_column=Column(Text, nullable=False))
    consent_text_hash: str = Field(sa_column=Column(Text, nullable=False))
    ip_address: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    attested_at: AwareDatetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    # created_by (nullable) provided by AppendOnlyMixin; FK enforced at DB layer.
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )
