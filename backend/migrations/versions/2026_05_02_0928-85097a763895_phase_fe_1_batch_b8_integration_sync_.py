"""phase_fe_1_batch_b8_integration_sync_conflict_diff_columns

Revision ID: 85097a763895
Revises: 7137111db267
Create Date: 2026-05-02 09:28:00.000000

B8/A49: Add diff/staleness columns to integration_sync_conflict for QB conflict display.
New columns: base_snapshot, field_diffs, pilot_modified_at, pilot_modified_by_user_id,
             qb_modified_at, qb_modified_by_external_user_label, auto_expire_at, pre_warning_at.
"""

from alembic import op

revision: str = "85097a763895"
down_revision: str | None = "7137111db267"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new diff/staleness columns — use defaults so existing rows are not broken
    op.execute("""
        ALTER TABLE integration_sync_conflict
            ADD COLUMN base_snapshot              JSONB NOT NULL DEFAULT '{}'::jsonb,
            ADD COLUMN field_diffs                JSONB NOT NULL DEFAULT '[]'::jsonb,
            ADD COLUMN pilot_modified_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
            ADD COLUMN pilot_modified_by_user_id  UUID NULL REFERENCES "user"(id) ON DELETE SET NULL,
            ADD COLUMN qb_modified_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
            ADD COLUMN qb_modified_by_external_user_label  TEXT NULL,
            ADD COLUMN auto_expire_at             TIMESTAMPTZ NULL,
            ADD COLUMN pre_warning_at             TIMESTAMPTZ NULL
    """)

    # Partial indexes for expiry background task performance
    op.execute("""
        CREATE INDEX idx_integration_sync_conflict_auto_expire
            ON integration_sync_conflict (tenant_id, auto_expire_at)
            WHERE status = 'pending' AND auto_expire_at IS NOT NULL
    """)

    op.execute("""
        CREATE INDEX idx_integration_sync_conflict_pre_warning
            ON integration_sync_conflict (tenant_id, pre_warning_at)
            WHERE status = 'pending' AND pre_warning_at IS NOT NULL
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_integration_sync_conflict_pre_warning")
    op.execute("DROP INDEX IF EXISTS idx_integration_sync_conflict_auto_expire")
    op.execute("""
        ALTER TABLE integration_sync_conflict
            DROP COLUMN IF EXISTS pre_warning_at,
            DROP COLUMN IF EXISTS auto_expire_at,
            DROP COLUMN IF EXISTS qb_modified_by_external_user_label,
            DROP COLUMN IF EXISTS qb_modified_at,
            DROP COLUMN IF EXISTS pilot_modified_by_user_id,
            DROP COLUMN IF EXISTS pilot_modified_at,
            DROP COLUMN IF EXISTS field_diffs,
            DROP COLUMN IF EXISTS base_snapshot
    """)
