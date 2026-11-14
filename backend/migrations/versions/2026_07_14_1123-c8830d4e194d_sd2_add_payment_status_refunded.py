"""sd2_add_payment_status_refunded

Revision ID: c8830d4e194d
Revises: 81723faa49d9
Create Date: 2026-07-14 11:23:02

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c8830d4e194d"
down_revision: str | None = "81723faa49d9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("SET LOCAL session_replication_role = 'replica';")
    op.execute("""
        INSERT INTO public.payment_status
        (id, code, name, is_default, is_terminal, is_active, tenant_id, created_at, updated_at)
        VALUES (gen_random_uuid(), 'refunded', 'Refunded', false, true, true, NULL, NOW(), NOW())
        ON CONFLICT DO NOTHING
    """)


def downgrade() -> None:
    op.execute(
        "DELETE FROM public.payment_status WHERE code = 'refunded' AND tenant_id IS NULL"
    )
