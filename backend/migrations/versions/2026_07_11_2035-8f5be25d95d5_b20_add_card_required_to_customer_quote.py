"""b20_add_card_required_to_customer_quote

Revision ID: 8f5be25d95d5
Revises: f06d384b7525
Create Date: 2026-07-11 20:35:52

B20: Add card_required to customer (NOT NULL, default false) and quote (nullable).
customer.card_required: true = Square card-on-file required before work begins.
quote.card_required: NULL = inherit from customer.card_required; explicit value = per-quote override.
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "8f5be25d95d5"
down_revision = "f06d384b7525"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # customer.card_required — NOT NULL with default false (3-part pattern)
    # Part 1: Add nullable
    op.add_column("customer", sa.Column("card_required", sa.Boolean(), nullable=True))
    # Part 2: Backfill existing rows
    op.execute("UPDATE customer SET card_required = false WHERE card_required IS NULL")
    # Part 3: Lock NOT NULL with server default
    op.alter_column("customer", "card_required", nullable=False, server_default="false")

    # quote.card_required — nullable (NULL = inherit from customer.card_required)
    op.add_column("quote", sa.Column("card_required", sa.Boolean(), nullable=True))


def downgrade() -> None:
    op.drop_column("quote", "card_required")
    op.drop_column("customer", "card_required")
