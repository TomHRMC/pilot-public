"""
B14/A73 — Tenant Signup State Machine model.
Table: tenant_signup
"""

import uuid

from pydantic import AwareDatetime
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlmodel import Column, Field, SQLModel

from .mixins import StandardAuditMixin


class TenantSignup(StandardAuditMixin, SQLModel, table=True):
    """
    Wizard state machine for tenant onboarding.
    State transitions: step1_account → step2_legal → step3_phone → step4_tier → step5_confirm → complete
    """

    __tablename__ = "tenant_signup"
    __table_args__ = (
        CheckConstraint(
            "signup_state IN ('step1_account', 'step2_legal', 'step3_phone', 'step4_tier', 'step5_confirm', 'complete')",
            name="tenant_signup_state_chk",
        ),
        Index("ix_tenant_signup_state", "signup_state"),
    )

    tenant_id: uuid.UUID = Field(
        primary_key=True,
        foreign_key="tenant.id",
    )
    signup_state: str = Field(
        default="step1_account",
        sa_column=Column(
            String,
            server_default=text("'step1_account'"),
            nullable=False,
        ),
    )
    signup_started_at: AwareDatetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    signup_completed_at: AwareDatetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    business_name: str = Field(
        sa_column=Column(String, nullable=False),
    )
    trade: str = Field(
        sa_column=Column(String, nullable=False),
    )
    business_size: str = Field(
        sa_column=Column(String, nullable=False),
    )
    zip: str = Field(
        sa_column=Column(String, nullable=False),
    )
    time_zone: str = Field(
        sa_column=Column(String, nullable=False),
    )

    # SIGNUP-GA-1: Owner identity persisted on the signup record so step-1
    # resolve-or-attach can key off owner_email (previously dropped by
    # initiate_signup). All nullable — no backfill.
    owner_email: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    owner_first_name: str | None = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    owner_last_name: str | None = Field(
        default=None, sa_column=Column(Text, nullable=True)
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
