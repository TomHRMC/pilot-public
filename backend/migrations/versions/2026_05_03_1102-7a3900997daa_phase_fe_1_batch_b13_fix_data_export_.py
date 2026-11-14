"""phase_fe_1_batch_b13_fix_data_export_request_audit_mixin

Revision ID: 7a3900997daa
Revises: dfb9ddaea5f9
Create Date: 2026-05-03 11:02:11

B13-fix: Add StandardAuditMixin columns to data_export_request.
Columns added: created_at, updated_at, created_by, updated_by.
"""

from alembic import op

revision = "7a3900997daa"
down_revision = "dfb9ddaea5f9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE data_export_request
            ADD COLUMN created_at  TIMESTAMPTZ,
            ADD COLUMN updated_at  TIMESTAMPTZ,
            ADD COLUMN created_by  UUID,
            ADD COLUMN updated_by  UUID
    """)
    op.execute(
        "UPDATE data_export_request SET created_at = now(), updated_at = now() WHERE created_at IS NULL"
    )
    op.execute("""
        ALTER TABLE data_export_request
            ALTER COLUMN created_at SET NOT NULL,
            ALTER COLUMN updated_at SET NOT NULL
    """)
    op.execute("""
        CREATE TRIGGER trg_data_export_request_guard_created_immutable
        BEFORE UPDATE ON public.data_export_request
        FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable()
    """)
    op.execute("""
        CREATE TRIGGER trg_data_export_request_set_updated_at
        BEFORE UPDATE ON public.data_export_request
        FOR EACH ROW EXECUTE FUNCTION public.set_updated_at()
    """)


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS trg_data_export_request_set_updated_at ON public.data_export_request"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_data_export_request_guard_created_immutable ON public.data_export_request"
    )
    op.execute("""
        ALTER TABLE data_export_request
            DROP COLUMN IF EXISTS updated_by,
            DROP COLUMN IF EXISTS created_by,
            DROP COLUMN IF EXISTS updated_at,
            DROP COLUMN IF EXISTS created_at
    """)
