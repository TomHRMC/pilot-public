"""phase_fe_1_batch_b13_fix_user_mfa_method_audit_mixin

Revision ID: a84294e8eb9e
Revises: 69753944139f
Create Date: 2026-05-03 11:02:11

B13-fix: Add StandardAuditMixin columns to user_mfa_method.
Columns added: created_at, updated_at, created_by, updated_by.
"""

from alembic import op

revision = "a84294e8eb9e"
down_revision = "69753944139f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE user_mfa_method
            ADD COLUMN created_at  TIMESTAMPTZ,
            ADD COLUMN updated_at  TIMESTAMPTZ,
            ADD COLUMN created_by  UUID,
            ADD COLUMN updated_by  UUID
    """)
    op.execute(
        "UPDATE user_mfa_method SET created_at = now(), updated_at = now() WHERE created_at IS NULL"
    )
    op.execute("""
        ALTER TABLE user_mfa_method
            ALTER COLUMN created_at SET NOT NULL,
            ALTER COLUMN updated_at SET NOT NULL
    """)
    op.execute("""
        CREATE TRIGGER trg_user_mfa_method_guard_created_immutable
        BEFORE UPDATE ON public.user_mfa_method
        FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable()
    """)
    op.execute("""
        CREATE TRIGGER trg_user_mfa_method_set_updated_at
        BEFORE UPDATE ON public.user_mfa_method
        FOR EACH ROW EXECUTE FUNCTION public.set_updated_at()
    """)


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS trg_user_mfa_method_set_updated_at ON public.user_mfa_method"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_user_mfa_method_guard_created_immutable ON public.user_mfa_method"
    )
    op.execute("""
        ALTER TABLE user_mfa_method
            DROP COLUMN IF EXISTS updated_by,
            DROP COLUMN IF EXISTS created_by,
            DROP COLUMN IF EXISTS updated_at,
            DROP COLUMN IF EXISTS created_at
    """)
