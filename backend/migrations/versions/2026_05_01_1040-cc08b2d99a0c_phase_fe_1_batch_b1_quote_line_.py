"""phase_fe_1_batch_b1_quote_line_visibility_hierarchy

Revision ID: cc08b2d99a0c
Revises: 5089dc9fc2e5
Create Date: 2026-05-01 10:40:21

A24 — Quote Line Item Schema Extension
Adds: customer_visible, parent_line_id, display_order, is_section_header
Pattern: 3-part migration (nullable → backfill → NOT NULL) for customer_visible,
         display_order, is_section_header. parent_line_id stays nullable by design.
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "cc08b2d99a0c"
down_revision = "5089dc9fc2e5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------ #
    # A24 — Part 1: Add new columns as NULLABLE first                     #
    # ------------------------------------------------------------------ #

    # customer_visible — BOOLEAN, will be NOT NULL TRUE after backfill
    op.add_column(
        "quote_line", sa.Column("customer_visible", sa.Boolean(), nullable=True)
    )
    # parent_line_id — self-referential FK, stays nullable by design
    op.add_column("quote_line", sa.Column("parent_line_id", sa.UUID(), nullable=True))
    # display_order — INT, will be NOT NULL 0 after backfill
    op.add_column("quote_line", sa.Column("display_order", sa.Integer(), nullable=True))
    # is_section_header — BOOLEAN, will be NOT NULL FALSE after backfill
    op.add_column(
        "quote_line", sa.Column("is_section_header", sa.Boolean(), nullable=True)
    )

    # ------------------------------------------------------------------ #
    # Part 2: Backfill existing rows with safe defaults                   #
    # ------------------------------------------------------------------ #
    op.execute("""
        UPDATE quote_line
        SET
            customer_visible   = TRUE,
            display_order      = position,
            is_section_header  = FALSE
        WHERE customer_visible IS NULL
    """)

    # ------------------------------------------------------------------ #
    # Part 3: Lock NOT NULL constraints + set server defaults             #
    # ------------------------------------------------------------------ #
    op.alter_column(
        "quote_line", "customer_visible", nullable=False, server_default=sa.text("true")
    )
    op.alter_column(
        "quote_line", "display_order", nullable=False, server_default=sa.text("0")
    )
    op.alter_column(
        "quote_line",
        "is_section_header",
        nullable=False,
        server_default=sa.text("false"),
    )

    # ------------------------------------------------------------------ #
    # FK constraint for parent_line_id (self-referential)                 #
    # ------------------------------------------------------------------ #
    op.create_foreign_key(
        "fk_quote_line_parent_line_id",
        "quote_line",
        "quote_line",
        ["parent_line_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    # ------------------------------------------------------------------ #
    # Index for self-referential parent lookup                            #
    # ------------------------------------------------------------------ #
    op.create_index(
        "ix_quote_line_parent_line_id",
        "quote_line",
        ["parent_line_id"],
    )

    # ------------------------------------------------------------------ #
    # CHECK constraint: section headers cannot be children                #
    # ------------------------------------------------------------------ #
    op.execute("""
        ALTER TABLE quote_line
        ADD CONSTRAINT chk_section_header_no_parent
        CHECK (NOT (is_section_header = TRUE AND parent_line_id IS NOT NULL))
    """)


def downgrade() -> None:
    # Drop CHECK constraint first
    op.execute("""
        ALTER TABLE quote_line
        DROP CONSTRAINT IF EXISTS chk_section_header_no_parent
    """)

    # Drop index
    op.drop_index("ix_quote_line_parent_line_id", table_name="quote_line")

    # Drop FK
    op.drop_constraint("fk_quote_line_parent_line_id", "quote_line", type_="foreignkey")

    # Drop all 4 A24 columns
    op.drop_column("quote_line", "is_section_header")
    op.drop_column("quote_line", "display_order")
    op.drop_column("quote_line", "parent_line_id")
    op.drop_column("quote_line", "customer_visible")
