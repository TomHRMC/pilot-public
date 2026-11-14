"""sd05_add_refund_columns_to_payment

Revision ID: 1923b2d3aa14
Revises: 94095600df2a
Create Date: 2026-07-06 21:08:00.000000

SD-05: Add refunded_amount_cents and refunded_at columns to the payment table.
- refunded_amount_cents: NOT NULL with server_default='0' — safe for existing rows
- refunded_at: nullable — NULL means no refund has been processed
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "1923b2d3aa14"
down_revision = "94095600df2a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # refunded_amount_cents: NOT NULL with server_default='0' — safe for existing rows
    op.add_column(
        "payment",
        sa.Column(
            "refunded_amount_cents",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    # refunded_at: nullable — NULL means no refund processed
    op.add_column(
        "payment",
        sa.Column("refunded_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("payment", "refunded_at")
    op.drop_column("payment", "refunded_amount_cents")
