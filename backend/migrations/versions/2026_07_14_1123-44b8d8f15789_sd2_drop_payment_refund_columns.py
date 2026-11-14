"""sd2_drop_payment_refund_columns

Revision ID: 44b8d8f15789
Revises: c8830d4e194d
Create Date: 2026-07-14 11:23:03

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "44b8d8f15789"
down_revision: str | None = "c8830d4e194d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_column("payment", "refunded_amount_cents")
    op.drop_column("payment", "refunded_at")


def downgrade() -> None:
    op.add_column(
        "payment",
        sa.Column(
            "refunded_amount_cents", sa.Integer(), nullable=False, server_default="0"
        ),
    )
    op.add_column(
        "payment",
        sa.Column("refunded_at", sa.DateTime(timezone=True), nullable=True),
    )
