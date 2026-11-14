"""phase_fe_1_batch_b13_fix_mfa_grace_period_tracking_audit_mixin

Revision ID: 69753944139f
Revises: 0980c3a2617b
Create Date: 2026-05-03 11:02:11

B13-fix: Add StandardAuditMixin columns to mfa_grace_period_tracking.
Columns added: created_at, updated_at, created_by, updated_by.
"""

from alembic import op

revision = "69753944139f"
down_revision = "0980c3a2617b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE mfa_grace_period_tracking
            ADD COLUMN created_at  TIMESTAMPTZ,
            ADD COLUMN updated_at  TIMESTAMPTZ,
            ADD COLUMN created_by  UUID,
            ADD COLUMN updated_by  UUID
    """)
    op.execute(
        "UPDATE mfa_grace_period_tracking SET created_at = now(), updated_at = now() WHERE created_at IS NULL"
    )
    op.execute("""
        ALTER TABLE mfa_grace_period_tracking
            ALTER COLUMN created_at SET NOT NULL,
            ALTER COLUMN updated_at SET NOT NULL
    """)
    op.execute("""
        CREATE TRIGGER trg_mfa_grace_period_tracking_guard_created_immutable
        BEFORE UPDATE ON public.mfa_grace_period_tracking
        FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable()
    """)
    op.execute("""
        CREATE TRIGGER trg_mfa_grace_period_tracking_set_updated_at
        BEFORE UPDATE ON public.mfa_grace_period_tracking
        FOR EACH ROW EXECUTE FUNCTION public.set_updated_at()
    """)


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS trg_mfa_grace_period_tracking_set_updated_at ON public.mfa_grace_period_tracking"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_mfa_grace_period_tracking_guard_created_immutable ON public.mfa_grace_period_tracking"
    )
    op.execute("""
        ALTER TABLE mfa_grace_period_tracking
            DROP COLUMN IF EXISTS updated_by,
            DROP COLUMN IF EXISTS created_by,
            DROP COLUMN IF EXISTS updated_at,
            DROP COLUMN IF EXISTS created_at
    """)
