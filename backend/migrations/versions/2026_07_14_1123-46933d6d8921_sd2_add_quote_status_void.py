"""sd2_add_quote_status_void

Revision ID: 46933d6d8921
Revises: 0c62db8483af
Create Date: 2026-07-14 11:23:00

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "46933d6d8921"
down_revision: str | None = "0c62db8483af"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("SET LOCAL session_replication_role = 'replica';")
    op.execute("""
        INSERT INTO public.quote_status
        (id, code, name, is_default, is_terminal, is_active, tenant_id, created_at, updated_at)
        VALUES (gen_random_uuid(), 'void', 'Void', false, true, true, NULL, NOW(), NOW())
        ON CONFLICT DO NOTHING
    """)


def downgrade() -> None:
    op.execute(
        "DELETE FROM public.quote_status WHERE code = 'void' AND tenant_id IS NULL"
    )
