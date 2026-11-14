"""phase_fe_1_batch_b3_tenant_settings_b3

Revision ID: 20cf5fb214f9
Revises: bbb80146cb8c
Create Date: 2026-05-01 15:57:17.000000

B3/A15, A16, A17: Add settings columns to tenant_settings.
Batched into one migration to avoid multiple ALTERs on same table.

A15: report_chart_threshold INT NOT NULL DEFAULT 8
A16: etc_variance_owner_notify_pct INT NOT NULL DEFAULT 50
     etc_variance_note_required_pct INT NOT NULL DEFAULT 10
A17: margin_bucket_boundaries JSONB NOT NULL DEFAULT '[10, 20, 30]'::jsonb
     margin_target_pct INT NOT NULL DEFAULT 20

All have server_default — no backfill required.

Check constraints:
  ck_ts_report_chart_threshold_positive: report_chart_threshold > 0
  ck_ts_etc_notify_pct_range:            etc_variance_owner_notify_pct BETWEEN 1 AND 500
  ck_ts_etc_note_pct_range:              etc_variance_note_required_pct BETWEEN 1 AND 100
  ck_ts_margin_target_range:             margin_target_pct BETWEEN 0 AND 100
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20cf5fb214f9"
down_revision: str | None = "bbb80146cb8c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # A15
    op.add_column(
        "tenant_settings",
        sa.Column(
            "report_chart_threshold",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("8"),
        ),
    )
    # A16
    op.add_column(
        "tenant_settings",
        sa.Column(
            "etc_variance_owner_notify_pct",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("50"),
        ),
    )
    op.add_column(
        "tenant_settings",
        sa.Column(
            "etc_variance_note_required_pct",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("10"),
        ),
    )
    # A17
    op.add_column(
        "tenant_settings",
        sa.Column(
            "margin_bucket_boundaries",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[10, 20, 30]'::jsonb"),
        ),
    )
    op.add_column(
        "tenant_settings",
        sa.Column(
            "margin_target_pct",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("20"),
        ),
    )
    # Check constraints
    op.create_check_constraint(
        "ck_ts_report_chart_threshold_positive",
        "tenant_settings",
        "report_chart_threshold > 0",
    )
    op.create_check_constraint(
        "ck_ts_etc_notify_pct_range",
        "tenant_settings",
        "etc_variance_owner_notify_pct BETWEEN 1 AND 500",
    )
    op.create_check_constraint(
        "ck_ts_etc_note_pct_range",
        "tenant_settings",
        "etc_variance_note_required_pct BETWEEN 1 AND 100",
    )
    op.create_check_constraint(
        "ck_ts_margin_target_range",
        "tenant_settings",
        "margin_target_pct BETWEEN 0 AND 100",
    )


def downgrade() -> None:
    op.drop_constraint("ck_ts_margin_target_range", "tenant_settings", type_="check")
    op.drop_constraint("ck_ts_etc_note_pct_range", "tenant_settings", type_="check")
    op.drop_constraint("ck_ts_etc_notify_pct_range", "tenant_settings", type_="check")
    op.drop_constraint(
        "ck_ts_report_chart_threshold_positive", "tenant_settings", type_="check"
    )
    op.drop_column("tenant_settings", "margin_target_pct")
    op.drop_column("tenant_settings", "margin_bucket_boundaries")
    op.drop_column("tenant_settings", "etc_variance_note_required_pct")
    op.drop_column("tenant_settings", "etc_variance_owner_notify_pct")
    op.drop_column("tenant_settings", "report_chart_threshold")
