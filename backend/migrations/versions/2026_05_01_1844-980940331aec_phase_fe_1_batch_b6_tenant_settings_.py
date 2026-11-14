"""phase_fe_1_batch_b6_tenant_settings_auto_expiry

Revision ID: 980940331aec
Revises: 41c1340bfa7e
Create Date: 2026-05-01 18:44:58.000000

B6/A34: Add auto-expiry configuration columns to tenant_settings.

New columns:
  - calendar_conflict_auto_expire_enabled BOOLEAN NOT NULL DEFAULT true
  - calendar_conflict_auto_expire_days INTEGER NULL (NULL = inherit system default 30)
  - calendar_conflict_pre_warning_days INTEGER NULL (NULL = inherit system default 7)

Check constraint:
  - ck_ts_calendar_conflict_days: pre_warning < auto_expire (when both not NULL)
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "980940331aec"
down_revision: str | None = "41c1340bfa7e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ----------------------------------------------------------------
    # 1. calendar_conflict_auto_expire_enabled: NOT NULL BOOLEAN DEFAULT true
    # ----------------------------------------------------------------
    op.add_column(
        "tenant_settings",
        sa.Column(
            "calendar_conflict_auto_expire_enabled",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
    )

    # ----------------------------------------------------------------
    # 2. calendar_conflict_auto_expire_days: nullable INTEGER
    # ----------------------------------------------------------------
    op.add_column(
        "tenant_settings",
        sa.Column("calendar_conflict_auto_expire_days", sa.Integer(), nullable=True),
    )

    # ----------------------------------------------------------------
    # 3. calendar_conflict_pre_warning_days: nullable INTEGER
    # ----------------------------------------------------------------
    op.add_column(
        "tenant_settings",
        sa.Column("calendar_conflict_pre_warning_days", sa.Integer(), nullable=True),
    )

    # ----------------------------------------------------------------
    # 4. Validation constraint: pre_warning < auto_expire (when both set)
    # ----------------------------------------------------------------
    op.execute(
        """
        ALTER TABLE tenant_settings ADD CONSTRAINT ck_ts_calendar_conflict_days
        CHECK (
            calendar_conflict_auto_expire_days IS NULL OR
            calendar_conflict_pre_warning_days IS NULL OR
            calendar_conflict_pre_warning_days < calendar_conflict_auto_expire_days
        )
        """
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE tenant_settings DROP CONSTRAINT IF EXISTS ck_ts_calendar_conflict_days"
    )
    op.drop_column("tenant_settings", "calendar_conflict_pre_warning_days")
    op.drop_column("tenant_settings", "calendar_conflict_auto_expire_days")
    op.drop_column("tenant_settings", "calendar_conflict_auto_expire_enabled")
