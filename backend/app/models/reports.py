"""
reports.py — B5/A5

SQLModel models for reports domain.
Currently contains only UserDashboardWidget.
"""

import uuid
from enum import Enum
from typing import Any

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlmodel import Column, Field, SQLModel

from .mixins import StandardAuditMixin


class WidgetType(str, Enum):
    profitability_summary = "profitability_summary"
    revenue_chart = "revenue_chart"
    ar_aging = "ar_aging"
    tech_productivity = "tech_productivity"
    tax_liability = "tax_liability"
    voice_analytics = "voice_analytics"


class UserDashboardWidget(StandardAuditMixin, SQLModel, table=True):
    """
    Stores per-user pinned dashboard widgets.

    Widgets are user-scoped configuration — hard-deleted when removed
    (no soft-delete). Users may pin the same widget_type multiple times
    with different widget_config_json filter overrides.
    """

    __tablename__ = "user_dashboard_widget"
    __table_args__ = (
        CheckConstraint("width BETWEEN 1 AND 12", name="ck_widget_width"),
        CheckConstraint("height BETWEEN 1 AND 8", name="ck_widget_height"),
        CheckConstraint("position_x >= 0", name="ck_widget_position_x"),
        CheckConstraint("position_y >= 0", name="ck_widget_position_y"),
    )

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
    )
    user_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID(as_uuid=True),
            ForeignKey("user.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        )
    )
    tenant_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID(as_uuid=True),
            ForeignKey("tenant.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        )
    )
    widget_type: str = Field(sa_column=Column(String(64), nullable=False))
    widget_config_json: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(
            JSONB,
            nullable=False,
            server_default=text("'{}'::jsonb"),
        ),
    )
    position_x: int = Field(
        default=0,
        sa_column=Column(Integer, server_default=text("0"), nullable=False),
    )
    position_y: int = Field(
        default=0,
        sa_column=Column(Integer, server_default=text("0"), nullable=False),
    )
    width: int = Field(
        default=2,
        sa_column=Column(Integer, server_default=text("2"), nullable=False),
    )
    height: int = Field(
        default=2,
        sa_column=Column(Integer, server_default=text("2"), nullable=False),
    )

    # Phase 6.0.1 pattern: audit FK overrides
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            PG_UUID(as_uuid=True),
            ForeignKey("user.id", ondelete="RESTRICT"),
        ),
    )
    updated_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            PG_UUID(as_uuid=True),
            ForeignKey("user.id", ondelete="RESTRICT"),
        ),
    )
