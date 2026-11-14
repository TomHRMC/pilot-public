"""b20_add_invoice_builder_fields

Revision ID: f06d384b7525
Revises: 44035334e651
Create Date: 2026-07-11 20:18:28

B20: Add payment_terms, billing_mode, progress_pct, internal_memo to invoice table.
Includes CHECK constraints for payment_terms and billing_mode per design doc §B.1.
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "f06d384b7525"
down_revision = "44035334e651"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Part 1: Add columns as nullable
    op.add_column("invoice", sa.Column("payment_terms", sa.String(30), nullable=True))
    op.add_column("invoice", sa.Column("billing_mode", sa.String(20), nullable=True))
    op.add_column("invoice", sa.Column("progress_pct", sa.Numeric(5, 2), nullable=True))
    op.add_column("invoice", sa.Column("internal_memo", sa.Text(), nullable=True))

    # Part 2: Backfill billing_mode (will become NOT NULL)
    op.execute(
        "UPDATE invoice SET billing_mode = 'line_item' WHERE billing_mode IS NULL"
    )

    # Part 3: Lock billing_mode as NOT NULL with server default
    op.alter_column(
        "invoice", "billing_mode", nullable=False, server_default="line_item"
    )

    # Part 4: Add CHECK constraints — DB-level enum enforcement
    # Single source of truth: matches Pydantic model_validator values exactly
    op.execute("""
        ALTER TABLE invoice
          ADD CONSTRAINT chk_invoice_payment_terms
            CHECK (payment_terms IN ('due_on_receipt', 'net_15', 'net_30', 'custom_date')),
          ADD CONSTRAINT chk_invoice_billing_mode
            CHECK (billing_mode IN ('line_item', 'progress'))
    """)

    # payment_terms, progress_pct, internal_memo remain nullable — no backfill needed


def downgrade() -> None:
    # Drop constraints FIRST (before dropping columns they depend on)
    op.execute("""
        ALTER TABLE invoice
          DROP CONSTRAINT IF EXISTS chk_invoice_payment_terms,
          DROP CONSTRAINT IF EXISTS chk_invoice_billing_mode
    """)
    op.drop_column("invoice", "internal_memo")
    op.drop_column("invoice", "progress_pct")
    op.drop_column("invoice", "billing_mode")
    op.drop_column("invoice", "payment_terms")
