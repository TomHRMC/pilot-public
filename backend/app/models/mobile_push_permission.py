"""
B14/A78 — Mobile Push Permission State model.
Table: mobile_push_permission_state
Mixin: StandardAuditMixin — permission state changes over time.
Composite PK: (tenant_id, user_id, device_id)
"""

import uuid

from pydantic import AwareDatetime
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    PrimaryKeyConstraint,
    String,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlmodel import Column, Field, SQLModel

from .mixins import StandardAuditMixin


class MobilePushPermissionState(StandardAuditMixin, SQLModel, table=True):
    """
    Per-device mobile push notification permission state.
    Composite PK (tenant_id, user_id, device_id).
    device_id references mobile_device_push_token.device_id (stable across token rotations).
    """

    __tablename__ = "mobile_push_permission_state"
    __table_args__ = (
        PrimaryKeyConstraint(
            "tenant_id",
            "user_id",
            "device_id",
            name="pk_mobile_push_permission_state",
        ),
        CheckConstraint(
            "permission_state IN ('not_asked', 'granted', 'denied_by_user_choice', 'denied_by_os', 'revoked_in_settings')",
            name="mobile_push_permission_state_state_chk",
        ),
        Index("ix_mobile_push_perm_tenant_user", "tenant_id", "user_id"),
    )

    tenant_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("tenant.id", ondelete="RESTRICT"),
            nullable=False,
        ),
    )
    user_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("user.id", ondelete="RESTRICT"),
            nullable=False,
        ),
    )
    device_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("mobile_device_push_token.device_id", ondelete="RESTRICT"),
            nullable=False,
        ),
    )
    permission_state: str = Field(
        default="not_asked",
        sa_column=Column(
            String,
            server_default=text("'not_asked'"),
            nullable=False,
        ),
    )
    last_state_change_at: AwareDatetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    dismissable_banner_dismissed_at: AwareDatetime | None = Field(
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
