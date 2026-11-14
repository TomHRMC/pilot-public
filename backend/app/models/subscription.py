"""
B14/A75 — Subscription Tier Infrastructure models.
Tables: subscription_tier, tenant_tier_override, tenant_subscription_usage
"""

import uuid

from pydantic import AwareDatetime
from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    PrimaryKeyConstraint,
    String,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlmodel import Column, Field, SQLModel

from .mixins import StandardAuditMixin


class SubscriptionTier(StandardAuditMixin, SQLModel, table=True):
    """
    Operator-managed tier catalogue.
    trial | starter | professional | enterprise
    """

    __tablename__ = "subscription_tier"

    tier_id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
    )
    tier_name: str = Field(
        sa_column=Column(String, nullable=False),
    )
    display_label: str = Field(
        sa_column=Column(String, nullable=False),
    )
    annual_price_cents: int = Field(
        sa_column=Column(Integer, nullable=False),
    )  # Total annual billing amount in cents: 58800 ($588/yr) for Starter, 178800 ($1,788/yr) for Teams
    monthly_price_cents: int = Field(
        default=0,
        sa_column=Column(Integer, nullable=False),
    )  # Month-to-month premium rate in cents: 5900 ($59/mo) for Starter, 17900 ($179/mo) for Teams
    is_trial: bool = Field(
        default=False,
        sa_column=Column(Boolean, server_default=text("false"), nullable=False),
    )
    trial_duration_days: int | None = Field(
        default=None,
        sa_column=Column(Integer, nullable=True),
    )
    schedule_lanes: int = Field(
        default=0,
        sa_column=Column(Integer, nullable=False),
    )
    is_active: bool = Field(
        default=True,
        sa_column=Column(Boolean, server_default=text("true"), nullable=False),
    )
    display_order: int = Field(
        sa_column=Column(Integer, nullable=False),
    )
    stripe_price_id_monthly: str | None = Field(
        default=None,
        sa_column=Column(String, nullable=True),
    )  # Renamed from stripe_price_id
    stripe_price_id_annual: str | None = Field(
        default=None,
        sa_column=Column(String, nullable=True),
    )  # NEW — populated by the operator after Stripe Dashboard setup
    product_plan_code: str | None = Field(
        default=None,
        sa_column=Column(String, nullable=True, index=True),
    )

    # C-B2: Charter program lifecycle fields
    free_period_days: int | None = Field(
        default=None,
        sa_column=Column(Integer, nullable=True),
    )  # Days at $0 from activation. NULL = no free period.
    requires_payment_method: bool = Field(
        default=True,
        sa_column=Column(Boolean, server_default=text("true"), nullable=False),
    )  # Whether the signup wizard collects a card.
    signup_cap: int | None = Field(
        default=None,
        sa_column=Column(Integer, nullable=True),
    )  # Max tenants that may activate on this tier. NULL = uncapped.
    price_locked: bool = Field(
        default=False,
        sa_column=Column(Boolean, server_default=text("false"), nullable=False),
    )  # Excludes this tier from future price-migration jobs.

    # Phase 6.0.1 pattern: Override audit fields with FK constraints
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )
    updated_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


class TenantTierOverride(StandardAuditMixin, SQLModel, table=True):
    """
    Operator-set per-tenant tier override. Single row per tenant (PK = tenant_id).
    """

    __tablename__ = "tenant_tier_override"

    tenant_id: uuid.UUID = Field(
        primary_key=True,
        foreign_key="tenant.id",
    )
    override_tier_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            PG_UUID,
            ForeignKey("subscription_tier.tier_id", ondelete="RESTRICT"),
            nullable=True,
        ),
    )
    override_trial_length_days: int | None = Field(
        default=None,
        sa_column=Column(Integer, nullable=True),
    )
    # FIND-103 (B18): override_reason is NOT NULL — audit trail is mandatory
    override_reason: str = Field(
        sa_column=Column(String, nullable=False),
    )
    set_by_operator_user_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("user.id", ondelete="RESTRICT"),
            nullable=False,
        ),
    )
    set_at: AwareDatetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

    # C-B2: Operator-set free period extension (case by case; not an advertised offer)
    override_free_period_ends_at: AwareDatetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
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


class TenantSubscriptionUsage(StandardAuditMixin, SQLModel, table=True):
    """
    Per-tenant per-billing-period usage counters.
    Composite PK (tenant_id, period_start) allows historical period tracking.
    Current period: WHERE tenant_id = :tid AND period_end >= now()
    """

    __tablename__ = "tenant_subscription_usage"
    __table_args__ = (
        PrimaryKeyConstraint(
            "tenant_id", "period_start", name="pk_tenant_subscription_usage"
        ),
    )

    tenant_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("tenant.id", ondelete="RESTRICT"),
            nullable=False,
        ),
    )
    period_start: AwareDatetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    period_end: AwareDatetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    current_user_count: int = Field(
        default=0,
        sa_column=Column(Integer, server_default=text("0"), nullable=False),
    )
    current_sms_segment_count: int = Field(
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
