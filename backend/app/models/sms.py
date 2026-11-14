"""
SMS Infrastructure Models — B11
=================================
Contains:
  - TenantPhoneNumber  (B11/A61) — provisioned Telnyx number per tenant
  - CustomerCommunicationThread (B11/A60) — per-(tenant,customer,tech,phone) thread
  - CustomerCommunicationMessage (B11/A60) — individual messages within a thread
  - CustomerCommunicationUnrouted (B11/A60) — unroutable inbound messages parked for owner
  - CustomerCommunicationMessageReadState (B11/A66) — per-user read receipt
  - SmsQuotaPeriod (B11/A65) — monthly SMS segment quota tracker

Mixin usage:
  - TenantPhoneNumber, CustomerCommunicationThread, SmsQuotaPeriod → StandardAuditMixin
    (migration DDL includes created_by / updated_by)
  - CustomerCommunicationMessage, CustomerCommunicationUnrouted → StandardAuditMixin
    (B13b remediation: created_by / updated_by columns added by migration)
"""

import uuid

from pydantic import AwareDatetime
from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Computed,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlmodel import Column, Field, SQLModel

from .mixins import AppendOnlyMixin, StandardAuditMixin

# ─── TenantPhoneNumber ────────────────────────────────────────────────────────


class TenantPhoneNumber(StandardAuditMixin, SQLModel, table=True):
    """
    Provisioned Telnyx phone number for a tenant.
    One active number per tenant (enforced via partial unique index).
    B11/A61.
    """

    __tablename__ = "tenant_phone_number"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'released', 'provisioning_failed')",
            name="tenant_phone_number_status_chk",
        ),
        CheckConstraint(
            "carrier IN ('telnyx')",
            name="tenant_phone_number_carrier_chk",
        ),
        # No table-level unique — enforced via partial index in migration
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("tenant.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        )
    )
    phone_number: str = Field(
        sa_column=Column(Text, nullable=False)
    )  # E.164 format e.g. +15125550001
    area_code: str = Field(sa_column=Column(Text, nullable=False))
    carrier: str = Field(
        default="telnyx",
        sa_column=Column(Text, server_default=text("'telnyx'"), nullable=False),
    )
    carrier_provisioning_id: str | None = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    monthly_fee_cents: int = Field(
        default=100,
        sa_column=Column(Integer, server_default=text("100"), nullable=False),
    )
    status: str = Field(
        default="active",
        sa_column=Column(Text, server_default=text("'active'"), nullable=False),
    )
    provisioned_at: AwareDatetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    released_at: AwareDatetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )

    # Audit FK overrides (Phase 6.0.1 pattern)
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )
    updated_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


# ─── CustomerCommunicationThread ──────────────────────────────────────────────


class CustomerCommunicationThread(StandardAuditMixin, SQLModel, table=True):
    """
    SMS conversation thread between a (tenant, customer, tech, phone_number) tuple.
    Uniqueness enforced by partial index on the 4-tuple WHERE status = 'active'.
    B11/A60.
    """

    __tablename__ = "customer_communication_thread"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'archived')",
            name="customer_communication_thread_status_chk",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
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
    tech_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("user.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        )
    )
    tenant_phone_number_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("tenant_phone_number.id", ondelete="RESTRICT"),
            nullable=False,
        )
    )
    status: str = Field(
        default="active",
        sa_column=Column(Text, server_default=text("'active'"), nullable=False),
    )
    first_message_at: AwareDatetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    last_message_at: AwareDatetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    message_count: int = Field(
        default=0,
        sa_column=Column(Integer, server_default=text("0"), nullable=False),
    )

    # Audit FK overrides
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )
    updated_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


# ─── CustomerCommunicationMessage ─────────────────────────────────────────────


class CustomerCommunicationMessage(StandardAuditMixin, SQLModel, table=True):
    """
    Individual SMS message within a CustomerCommunicationThread.
    B11/A60.

    B13b: StandardAuditMixin added — created_by / updated_by columns added via migration.
    Outbound messages: created_by populated with sender user. Inbound: NULL (system-received).

    voice_audio_id FK type: BIGINT (voice_command_log.id is a BIGINT sequence — confirmed via MCP).
    """

    __tablename__ = "customer_communication_message"
    __table_args__ = (
        CheckConstraint(
            "direction IN ('outbound', 'inbound')",
            name="customer_communication_message_direction_chk",
        ),
        CheckConstraint(
            "channel IN ('sms')",
            name="customer_communication_message_channel_chk",
        ),
        CheckConstraint(
            "status IN ('pending_send', 'sent', 'delivered', 'failed', 'received')",
            name="customer_communication_message_status_chk",
        ),
        CheckConstraint(
            "composition_method IS NULL OR composition_method IN ('template', 'free_form_text', 'free_form_voice')",
            name="customer_communication_message_composition_method_chk",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    # created_at, updated_at, created_by, updated_by provided by StandardAuditMixin
    thread_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("customer_communication_thread.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        )
    )
    direction: str = Field(
        sa_column=Column(Text, nullable=False)
    )  # 'outbound' | 'inbound'
    channel: str = Field(
        default="sms",
        sa_column=Column(Text, server_default=text("'sms'"), nullable=False),
    )
    body: str = Field(sa_column=Column(Text, nullable=False))
    segment_count: int = Field(
        default=1,
        sa_column=Column(Integer, server_default=text("1"), nullable=False),
    )
    status: str = Field(
        default="pending_send",
        sa_column=Column(Text, server_default=text("'pending_send'"), nullable=False),
    )
    carrier_message_id: str | None = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    sent_at: AwareDatetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    delivered_at: AwareDatetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    received_at: AwareDatetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    composition_method: str | None = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    template_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            PG_UUID,
            ForeignKey("communication_template.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    # F1 decision: voice_command_log.id is BIGINT (confirmed via MCP), NOT UUID
    voice_audio_id: int | None = Field(
        default=None,
        sa_column=Column(
            BigInteger,
            ForeignKey("voice_command_log.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    audit_user_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("user.id", ondelete="RESTRICT"),
            nullable=False,
        )
    )


# ─── CustomerCommunicationUnrouted ────────────────────────────────────────────


class CustomerCommunicationUnrouted(StandardAuditMixin, SQLModel, table=True):
    """
    Inbound SMS messages that could not be matched to an existing thread/customer.
    Parked for owner review.
    B11/A60.

    B13b: StandardAuditMixin added — created_by / updated_by columns added via migration.
    System-created on inbound receipt — created_by/updated_by always NULL at runtime.
    """

    __tablename__ = "customer_communication_unrouted"
    __table_args__ = (
        CheckConstraint(
            "status IN ('parked', 'assigned', 'dismissed')",
            name="customer_communication_unrouted_status_chk",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    # created_at, updated_at, created_by, updated_by provided by StandardAuditMixin
    tenant_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("tenant.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        )
    )
    from_number: str = Field(sa_column=Column(Text, nullable=False))  # E.164
    to_number: str = Field(sa_column=Column(Text, nullable=False))  # E.164
    body: str = Field(sa_column=Column(Text, nullable=False))
    carrier_message_id: str | None = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    received_at: AwareDatetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    parked_at: AwareDatetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    resolved_at: AwareDatetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    resolved_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            PG_UUID,
            ForeignKey("user.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    resolved_thread_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            PG_UUID,
            ForeignKey("customer_communication_thread.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    status: str = Field(
        default="parked",
        sa_column=Column(Text, server_default=text("'parked'"), nullable=False),
    )


# ─── CustomerCommunicationMessageReadState ────────────────────────────────────


class CustomerCommunicationMessageReadState(AppendOnlyMixin, SQLModel, table=True):
    """
    Per-user read receipt for a CustomerCommunicationMessage.
    Composite PK (message_id, user_id). AppendOnly pattern (no updated_at).
    B11/A66.

    B13b: AppendOnlyMixin added — created_at (backfilled from read_at) + created_by added via migration.
    """

    __tablename__ = "customer_communication_message_read_state"

    message_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("customer_communication_message.id", ondelete="CASCADE"),
            nullable=False,
            primary_key=True,
        )
    )
    user_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("user.id", ondelete="CASCADE"),
            nullable=False,
            primary_key=True,
        )
    )
    read_at: AwareDatetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )


# ─── SmsQuotaPeriod ───────────────────────────────────────────────────────────


class SmsQuotaPeriod(StandardAuditMixin, SQLModel, table=True):
    """
    Monthly SMS segment quota tracker per tenant.
    overage_segments is a computed/stored column in the DB (GENERATED ALWAYS AS STORED).
    Python tracks it as a regular int populated on read.
    B11/A65.

    B13b: StandardAuditMixin added — created_by / updated_by columns added via migration.
    Created by Celery rollover task — created_by always NULL at runtime.
    """

    __tablename__ = "sms_quota_period"
    __table_args__ = (
        CheckConstraint(
            "cap_policy IN ('soft', 'hard')",
            name="sms_quota_period_cap_policy_chk",
        ),
        # EXCLUDE constraint (gist) for no-overlap is DB-only — no ORM repr
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    # created_at, updated_at, created_by, updated_by provided by StandardAuditMixin
    tenant_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("tenant.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        )
    )
    period_start: AwareDatetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    period_end: AwareDatetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    included_segments: int = Field(
        default=100,
        sa_column=Column(Integer, server_default=text("100"), nullable=False),
    )
    used_segments: int = Field(
        default=0,
        sa_column=Column(Integer, server_default=text("0"), nullable=False),
    )
    # DB-computed column (GENERATED ALWAYS AS STORED); read-only from Python.
    # Use sqlalchemy.Computed to tell SQLAlchemy this column is DB-generated
    # and must NEVER be included in INSERT/UPDATE statements.
    overage_segments: int | None = Field(
        default=None,
        sa_column=Column(
            Integer,
            Computed("GREATEST(0, used_segments - included_segments)", persisted=True),
            nullable=True,
        ),
    )
    cap_policy: str = Field(
        default="soft",
        sa_column=Column(Text, server_default=text("'soft'"), nullable=False),
    )


# ─── TenantMessagingRegistration ──────────────────────────────────────────────


class TenantMessagingRegistration(StandardAuditMixin, SQLModel, table=True):
    """
    10DLC provisioning state machine for a tenant.

    Tracks the A2P 10DLC brand/campaign registration lifecycle with Telnyx:
    entity type selection → quote → Stripe checkout → OTP verification →
    brand/campaign provisioning → phone number assignment.

    One row per tenant (UNIQUE constraint on tenant_id).
    C-B2.
    """

    __tablename__ = "tenant_messaging_registration"
    __table_args__ = (
        UniqueConstraint("tenant_id", name="uq_tenant_messaging_registration_tenant"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    # created_at, updated_at, created_by, updated_by provided by StandardAuditMixin
    tenant_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("tenant.id", ondelete="RESTRICT"),
            nullable=False,
        )
    )
    entity_type: str = Field(
        sa_column=Column(String, nullable=False),
    )  # 'sole_proprietor' | 'standard'
    status: str = Field(
        sa_column=Column(String, nullable=False),
    )  # see state machine, spec §5.2
    telnyx_brand_id: str | None = Field(
        default=None,
        sa_column=Column(String, nullable=True),
    )
    telnyx_campaign_id: str | None = Field(
        default=None,
        sa_column=Column(String, nullable=True),
    )
    telnyx_phone_number: str | None = Field(
        default=None,
        sa_column=Column(String, nullable=True),
    )
    quoted_setup_cents: int | None = Field(
        default=None,
        sa_column=Column(Integer, nullable=True),
    )
    quoted_monthly_cents: int | None = Field(
        default=None,
        sa_column=Column(Integer, nullable=True),
    )
    stripe_checkout_id: str | None = Field(
        default=None,
        sa_column=Column(String, nullable=True),
    )
    stripe_payment_intent: str | None = Field(
        default=None,
        sa_column=Column(String, nullable=True),
    )
    otp_requested_at: AwareDatetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    otp_verified_at: AwareDatetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    failure_reason: str | None = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
    )
    # C-B10: Recurring carrier fee pass-through (Stripe SubscriptionItem)
    stripe_recurring_item_id: str | None = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
    )
    recurring_item_created_at: AwareDatetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
