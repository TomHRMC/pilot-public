"""phase_fe_1_batch_b13_fix_user_mfa_recovery_code_audit_mixin

Revision ID: 16a276d83a38
Revises: a84294e8eb9e
Create Date: 2026-05-03 11:02:11

B13-fix: Add AppendOnlyMixin columns to user_mfa_recovery_code.
Columns added: created_at, created_by (no updated_at — AppendOnly).
Triggers: audit_* already exists; only guard_created_immutable added (no set_updated_at).
"""

from alembic import op

revision = "16a276d83a38"
down_revision = "a84294e8eb9e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # AppendOnlyMixin: created_at + created_by only; no updated_at
    op.execute("""
        ALTER TABLE user_mfa_recovery_code
            ADD COLUMN created_at  TIMESTAMPTZ,
            ADD COLUMN created_by  UUID
    """)
    op.execute(
        "UPDATE user_mfa_recovery_code SET created_at = now() WHERE created_at IS NULL"
    )
    op.execute(
        "ALTER TABLE user_mfa_recovery_code ALTER COLUMN created_at SET NOT NULL"
    )

    # AppendOnly: audit trigger already exists; guard_created_immutable only (no set_updated_at)
    op.execute("""
        CREATE TRIGGER trg_user_mfa_recovery_code_guard_created_immutable
        BEFORE UPDATE ON public.user_mfa_recovery_code
        FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable()
    """)


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS trg_user_mfa_recovery_code_guard_created_immutable ON public.user_mfa_recovery_code"
    )
    op.execute("""
        ALTER TABLE user_mfa_recovery_code
            DROP COLUMN IF EXISTS created_by,
            DROP COLUMN IF EXISTS created_at
    """)
