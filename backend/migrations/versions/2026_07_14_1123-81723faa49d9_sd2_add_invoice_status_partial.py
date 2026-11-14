"""sd2_add_invoice_status_partial

Revision ID: 81723faa49d9
Revises: 46933d6d8921
Create Date: 2026-07-14 11:23:01

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "81723faa49d9"
down_revision: str | None = "46933d6d8921"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("SET LOCAL session_replication_role = 'replica';")
    op.execute("""
        INSERT INTO public.invoice_status
        (id, code, name, is_default, is_terminal, is_active, tenant_id, created_at, updated_at)
        VALUES (gen_random_uuid(), 'partial', 'Partially Paid', false, false, true, NULL, NOW(), NOW())
        ON CONFLICT DO NOTHING
    """)


def downgrade() -> None:
    op.execute(
        "DELETE FROM public.invoice_status WHERE code = 'partial' AND tenant_id IS NULL"
    )
