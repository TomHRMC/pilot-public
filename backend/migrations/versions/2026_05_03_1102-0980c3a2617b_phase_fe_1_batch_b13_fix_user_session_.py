"""phase_fe_1_batch_b13_fix_user_session_history_audit_mixin

Revision ID: 0980c3a2617b
Revises: d16eb70cda5c
Create Date: 2026-05-03 11:02:11

B13-fix: Add StandardAuditMixin columns to user_session_history.
Columns added: created_at, updated_at, created_by, updated_by.
Note: audit_user_session_history_changes trigger already exists — only
guard_created_immutable and set_updated_at triggers are added here.
"""

from alembic import op

revision = "0980c3a2617b"
down_revision = "d16eb70cda5c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Part 1: Add columns as nullable
    op.execute("""
        ALTER TABLE user_session_history
            ADD COLUMN created_at  TIMESTAMPTZ,
            ADD COLUMN updated_at  TIMESTAMPTZ,
            ADD COLUMN created_by  UUID,
            ADD COLUMN updated_by  UUID
    """)

    # Part 2: Backfill existing rows
    op.execute(
        "UPDATE user_session_history SET created_at = now(), updated_at = now() WHERE created_at IS NULL"
    )

    # Part 3: Lock created_at and updated_at NOT NULL
    op.execute("""
        ALTER TABLE user_session_history
            ALTER COLUMN created_at SET NOT NULL,
            ALTER COLUMN updated_at SET NOT NULL
    """)

    # Part 4: Install triggers (audit trigger already exists from B13 original migration)
    op.execute("""
        CREATE TRIGGER trg_user_session_history_guard_created_immutable
        BEFORE UPDATE ON public.user_session_history
        FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable()
    """)
    op.execute("""
        CREATE TRIGGER trg_user_session_history_set_updated_at
        BEFORE UPDATE ON public.user_session_history
        FOR EACH ROW EXECUTE FUNCTION public.set_updated_at()
    """)


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS trg_user_session_history_set_updated_at ON public.user_session_history"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_user_session_history_guard_created_immutable ON public.user_session_history"
    )
    op.execute("""
        ALTER TABLE user_session_history
            DROP COLUMN IF EXISTS updated_by,
            DROP COLUMN IF EXISTS created_by,
            DROP COLUMN IF EXISTS updated_at,
            DROP COLUMN IF EXISTS created_at
    """)
