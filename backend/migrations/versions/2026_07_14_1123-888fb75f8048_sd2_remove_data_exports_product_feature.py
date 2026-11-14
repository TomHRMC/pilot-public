"""sd2_remove_data_exports_product_feature

Revision ID: 888fb75f8048
Revises: cc42e269f531
Create Date: 2026-07-14 11:23:06

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "888fb75f8048"
down_revision: str | None = "cc42e269f531"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("SET LOCAL session_replication_role = 'replica';")
    op.execute("DELETE FROM public.product_feature WHERE code = 'data_exports'")


def downgrade() -> None:
    op.execute("""
        INSERT INTO public.product_feature (code, name, unit, description, created_at, updated_at)
        VALUES ('data_exports', 'Data exports', 'count',
                'Number of data export requests completed', NOW(), NOW())
        ON CONFLICT DO NOTHING
    """)
