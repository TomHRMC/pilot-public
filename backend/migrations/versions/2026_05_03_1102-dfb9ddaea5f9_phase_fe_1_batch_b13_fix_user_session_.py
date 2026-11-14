"""phase_fe_1_batch_b13_fix_user_session_metadata_audit_mixin

Revision ID: dfb9ddaea5f9
Revises: 16a276d83a38
Create Date: 2026-05-03 11:02:11

B13-fix: Add StandardAuditMixin columns to user_session_metadata.
EXCEPTION: created_at already exists (was added in original B13 migration with DEFAULT now()).
Columns added: updated_at, created_by, updated_by ONLY (skip created_at).
"""

from alembic import op

revision = "dfb9ddaea5f9"
down_revision = "16a276d83a38"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # created_at already exists — skip it. Add only updated_at, created_by, updated_by.
    op.execute("""
        ALTER TABLE user_session_metadata
            ADD COLUMN updated_at  TIMESTAMPTZ,
            ADD COLUMN created_by  UUID,
            ADD COLUMN updated_by  UUID
    """)
    op.execute(
        "UPDATE user_session_metadata SET updated_at = now() WHERE updated_at IS NULL"
    )
    op.execute("ALTER TABLE user_session_metadata ALTER COLUMN updated_at SET NOT NULL")

    op.execute("""
        CREATE TRIGGER trg_user_session_metadata_guard_created_immutable
        BEFORE UPDATE ON public.user_session_metadata
        FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable()
    """)
    op.execute("""
        CREATE TRIGGER trg_user_session_metadata_set_updated_at
        BEFORE UPDATE ON public.user_session_metadata
        FOR EACH ROW EXECUTE FUNCTION public.set_updated_at()
    """)


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS trg_user_session_metadata_set_updated_at ON public.user_session_metadata"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_user_session_metadata_guard_created_immutable ON public.user_session_metadata"
    )
    op.execute("""
        ALTER TABLE user_session_metadata
            DROP COLUMN IF EXISTS updated_by,
            DROP COLUMN IF EXISTS created_by,
            DROP COLUMN IF EXISTS updated_at
    """)
