"""sd2_deactivate_non_usd_currencies

Revision ID: 0c62db8483af
Revises: b1bd90914b77
Create Date: 2026-07-14 11:16:00

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0c62db8483af"
down_revision: str | None = "b1bd90914b77"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("SET LOCAL session_replication_role = 'replica';")
    op.execute("""
        UPDATE public.currency
        SET is_active = false, updated_at = NOW()
        WHERE code IN ('CAD', 'EUR', 'GBP')
    """)


def downgrade() -> None:
    op.execute("""
        UPDATE public.currency
        SET is_active = true, updated_at = NOW()
        WHERE code IN ('CAD', 'EUR', 'GBP')
    """)
