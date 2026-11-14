"""sd2_add_qco_line_type_note

Revision ID: f3b52caec35b
Revises: 44b8d8f15789
Create Date: 2026-07-14 11:23:04

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f3b52caec35b"
down_revision: str | None = "44b8d8f15789"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("SET LOCAL session_replication_role = 'replica';")
    op.execute("""
        INSERT INTO public.qco_line_type
        (id, code, name, is_default, is_active, qb_item_name_hint, tenant_id, created_at, updated_at)
        VALUES (gen_random_uuid(), 'note', 'Note', false, true, NULL, NULL, NOW(), NOW())
        ON CONFLICT DO NOTHING
    """)


def downgrade() -> None:
    op.execute(
        "DELETE FROM public.qco_line_type WHERE code = 'note' AND tenant_id IS NULL"
    )
