"""
Settings models for Pilot for Trades.

Established in B9/A53.
"""

import uuid
from typing import Any

from sqlalchemy import ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlmodel import Column, Field, SQLModel

from .mixins import StandardAuditMixin


class UserSettingOverride(StandardAuditMixin, SQLModel, table=True):
    """
    User-level setting override — Tier 1 of the three-tier resolver.
    One row per (tenant_id, user_id, setting_key).

    Established in B9/A53. Used by services/setting_resolver.py.
    """

    __tablename__ = "user_setting_override"

    # Composite PK: primary_key=True goes inside Column, not Field, when using sa_column
    tenant_id: uuid.UUID = Field(
        default=None,
        sa_column=Column(
            PG_UUID,
            ForeignKey(
                "tenant.id", ondelete="RESTRICT", name="fk_user_setting_override_tenant"
            ),
            primary_key=True,
            nullable=False,
        ),
    )
    user_id: uuid.UUID = Field(
        default=None,
        sa_column=Column(
            PG_UUID,
            ForeignKey(
                "user.id", ondelete="CASCADE", name="fk_user_setting_override_user"
            ),
            primary_key=True,
            nullable=False,
        ),
    )
    setting_key: str = Field(
        default=None,
        sa_column=Column(Text, primary_key=True, nullable=False),
    )
    value: dict[str, Any] = Field(sa_column=Column(JSONB, nullable=False))

    # Phase 6.0.1: Override audit FK constraints
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            PG_UUID,
            ForeignKey(
                "user.id",
                ondelete="RESTRICT",
                name="fk_user_setting_override_created_by",
            ),
        ),
    )
    updated_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            PG_UUID,
            ForeignKey(
                "user.id",
                ondelete="RESTRICT",
                name="fk_user_setting_override_updated_by",
            ),
        ),
    )
