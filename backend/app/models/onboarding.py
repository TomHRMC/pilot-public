"""
B14/A77 — Onboarding Checklist model.
Table: tenant_onboarding_checklist
Mixin: StandardAuditMixin — checklist items toggle between states; updated_at tracks completion.
"""

import uuid

from pydantic import AwareDatetime
from sqlalchemy import Boolean, DateTime, ForeignKey, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlmodel import Column, Field, SQLModel

from .mixins import StandardAuditMixin


class TenantOnboardingChecklist(StandardAuditMixin, SQLModel, table=True):
    """
    Per-tenant onboarding checklist widget state.
    PK = tenant_id (one row per tenant).
    """

    __tablename__ = "tenant_onboarding_checklist"

    tenant_id: uuid.UUID = Field(
        primary_key=True,
        foreign_key="tenant.id",
    )

    # Wizard completion steps (auto-set)
    account_created: bool = Field(
        default=False,
        sa_column=Column(Boolean, server_default=text("false"), nullable=False),
    )
    legal_accepted: bool = Field(
        default=False,
        sa_column=Column(Boolean, server_default=text("false"), nullable=False),
    )
    tier_selected: bool = Field(
        default=False,
        sa_column=Column(Boolean, server_default=text("false"), nullable=False),
    )

    # Domain event completions
    first_customer_added: bool = Field(
        default=False,
        sa_column=Column(Boolean, server_default=text("false"), nullable=False),
    )
    first_customer_added_at: AwareDatetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    catalog_setup: bool = Field(
        default=False,
        sa_column=Column(Boolean, server_default=text("false"), nullable=False),
    )
    catalog_setup_at: AwareDatetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )

    # Integration connections (with skip options)
    quickbooks_connected: bool = Field(
        default=False,
        sa_column=Column(Boolean, server_default=text("false"), nullable=False),
    )
    quickbooks_skipped: bool = Field(
        default=False,
        sa_column=Column(Boolean, server_default=text("false"), nullable=False),
    )
    calendar_connected: bool = Field(
        default=False,
        sa_column=Column(Boolean, server_default=text("false"), nullable=False),
    )
    calendar_skipped: bool = Field(
        default=False,
        sa_column=Column(Boolean, server_default=text("false"), nullable=False),
    )
    team_invited: bool = Field(
        default=False,
        sa_column=Column(Boolean, server_default=text("false"), nullable=False),
    )
    team_skipped: bool = Field(
        default=False,
        sa_column=Column(Boolean, server_default=text("false"), nullable=False),
    )

    # C-B5: 10DLC messaging setup (Charter-only, with cost disclosure)
    messaging_setup: bool = Field(
        default=False,
        sa_column=Column(Boolean, server_default=text("false"), nullable=False),
    )

    # Widget visibility
    checklist_hidden: bool = Field(
        default=False,
        sa_column=Column(Boolean, server_default=text("false"), nullable=False),
    )
    checklist_dismissed_permanently: bool = Field(
        default=False,
        sa_column=Column(Boolean, server_default=text("false"), nullable=False),
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
