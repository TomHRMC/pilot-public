"""
ORM models for the platform_setting redesign (FIND-086).

Two tables replace the flat tenant_settings table:
  - PlatformSettingCatalog: one row per setting key (metadata + validation rules)
  - PlatformSetting:        value rows — NULL tenant_id = platform default,
                            UUID tenant_id = tenant override

Resolution chain (enforced in services/setting_resolver.py):
  User override → Tenant override → Platform default → fallback constant (with WARNING log)
"""

import uuid
from typing import Any

from sqlalchemy import (
    Boolean,
    Column,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlmodel import Field, SQLModel

from .mixins import StandardAuditMixin


class PlatformSettingCatalog(StandardAuditMixin, SQLModel, table=True):
    """
    One row per configurable setting key.

    This table is the authoritative source for setting metadata, validation rules,
    and tenant/user editability flags. Previously represented as the static Python
    dict core/setting_catalog.py:SETTING_CATALOG (deleted by FIND-086 migration).
    """

    __tablename__ = "platform_setting_catalog"

    key: str = Field(primary_key=True)
    label: str = Field(nullable=False)
    description: str | None = Field(default=None)
    value_type: str = Field(
        sa_column=Column(
            String,
            nullable=False,
            # CHECK (value_type IN ('integer','boolean','string','decimal','jsonb'))
            # enforced by DB migration, not here
        )
    )
    tenant_editable: bool = Field(
        sa_column=Column(Boolean, server_default=text("false"), nullable=False)
    )
    allows_user_override: bool = Field(
        sa_column=Column(Boolean, server_default=text("false"), nullable=False)
    )
    min_value: int | None = Field(default=None)
    max_value: int | None = Field(default=None)
    # String enum validation — e.g. '["conservative","balanced","playful"]'
    allowed_values: Any | None = Field(
        default=None, sa_column=Column(JSONB, nullable=True)
    )
    # CHECK (category IN ('quotes','billing','notifications','voice','qb',
    #                     'sync','mobile','labor','reports','security','trial','safety'))
    category: str | None = Field(default=None)
    is_active: bool = Field(
        sa_column=Column(Boolean, server_default=text("true"), nullable=False)
    )
    sort_order: int = Field(
        sa_column=Column(Integer, server_default=text("0"), nullable=False)
    )

    # Override mixin audit FK columns with explicit FK constraints
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )
    updated_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


class PlatformSetting(StandardAuditMixin, SQLModel, table=True):
    """
    Value rows for platform settings.

    NULL tenant_id = platform-level default (one per catalog key).
    UUID tenant_id = tenant override (at most one per key+tenant).

    All value types are stored as JSONB:
      integer 5        → 5
      boolean true     → true
      string balanced  → "balanced"
      decimal 15.0     → 15.0
      jsonb [10,20,30] → [10,20,30]
    """

    __tablename__ = "platform_setting"
    __table_args__ = (
        UniqueConstraint("key", "tenant_id", name="uq_platform_setting_key_tenant"),
        Index("ix_platform_setting_key", "key"),
        Index("ix_platform_setting_tenant", "tenant_id"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    key: str = Field(
        sa_column=Column(
            String,
            ForeignKey("platform_setting_catalog.key", ondelete="RESTRICT"),
            nullable=False,
        )
    )
    # All types stored as JSONB — resolver casts to Python type on read
    value: Any = Field(sa_column=Column(JSONB, nullable=False))
    # NULL = platform default; UUID = tenant override
    tenant_id: uuid.UUID | None = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("tenant.id", ondelete="CASCADE"),
            nullable=True,
            index=True,
        )
    )

    # Override mixin audit FK columns with explicit FK constraints
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )
    updated_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )
