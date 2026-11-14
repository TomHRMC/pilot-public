"""phase_fe_1_batch_b1_quote_discount_fields

Revision ID: c83719f1152e
Revises: 29384efbde55
Create Date: 2026-05-01 11:34:46

A3 — Time-Limited Discounts with Margin Cap
- Adds 4 nullable columns to quote: discount_pct, discount_amount_cents,
  discount_expires_at, discount_applied_by_user_id
- Adds max_discount_pct_owner to tenant_settings (3-part pattern)
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "c83719f1152e"
down_revision = "29384efbde55"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------ #
    # 1. Add 4 nullable discount columns to quote                         #
    # ------------------------------------------------------------------ #
    op.add_column("quote", sa.Column("discount_pct", sa.Numeric(5, 2), nullable=True))
    op.add_column(
        "quote", sa.Column("discount_amount_cents", sa.Integer(), nullable=True)
    )
    op.add_column(
        "quote",
        sa.Column("discount_expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "quote", sa.Column("discount_applied_by_user_id", sa.UUID(), nullable=True)
    )

    # FK for discount_applied_by_user_id
    op.create_foreign_key(
        "fk_quote_discount_applied_by_user_id",
        "quote",
        "user",
        ["discount_applied_by_user_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    # ------------------------------------------------------------------ #
    # 2. Add max_discount_pct_owner to tenant_settings                    #
    #    3-part pattern: nullable → backfill → NOT NULL + default         #
    # ------------------------------------------------------------------ #
    # Part 1: Add nullable
    op.add_column(
        "tenant_settings",
        sa.Column("max_discount_pct_owner", sa.Numeric(5, 2), nullable=True),
    )

    # Part 2: Backfill existing rows with the MVP default of 15%
    op.execute("""
        UPDATE tenant_settings
        SET max_discount_pct_owner = 15.00
        WHERE max_discount_pct_owner IS NULL
    """)

    # Part 3: Lock NOT NULL + server default
    op.alter_column(
        "tenant_settings",
        "max_discount_pct_owner",
        nullable=False,
        server_default=sa.text("15.00"),
    )


def downgrade() -> None:
    # Remove tenant_settings column
    op.drop_column("tenant_settings", "max_discount_pct_owner")

    # Remove quote FK and columns
    op.drop_constraint(
        "fk_quote_discount_applied_by_user_id", "quote", type_="foreignkey"
    )
    op.drop_column("quote", "discount_applied_by_user_id")
    op.drop_column("quote", "discount_expires_at")
    op.drop_column("quote", "discount_amount_cents")
    op.drop_column("quote", "discount_pct")
