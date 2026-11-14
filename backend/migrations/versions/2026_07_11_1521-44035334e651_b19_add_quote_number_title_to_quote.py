"""b19_add_quote_number_title_to_quote

Revision ID: 44035334e651
Revises: b3f3643b4e20
Create Date: 2026-07-11 15:21:00.000000

Format: QUO-000001 (sequential, tenant-scoped, zero-padded 6 digits)
title: VARCHAR(255) nullable
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "44035334e651"
down_revision: str | None = "b3f3643b4e20"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- quote_number: 3-part NOT NULL pattern ---

    # Part 1 — Add nullable column
    op.add_column("quote", sa.Column("quote_number", sa.String(20), nullable=True))

    # Part 2 — Backfill existing rows: sequential per tenant, ordered by created_at
    op.execute("""
        UPDATE quote q
        SET quote_number = 'QUO-' || LPAD(rn.row_num::text, 6, '0')
        FROM (
            SELECT id, ROW_NUMBER() OVER (PARTITION BY tenant_id ORDER BY created_at) AS row_num
            FROM quote
        ) rn
        WHERE q.id = rn.id
        AND q.quote_number IS NULL
    """)

    # Part 3 — Apply NOT NULL constraint and unique index
    op.alter_column("quote", "quote_number", nullable=False)
    op.create_index(
        "ix_quote_tenant_quote_number",
        "quote",
        ["tenant_id", "quote_number"],
        unique=True,
    )

    # --- title: simple nullable add (no backfill needed) ---
    op.add_column("quote", sa.Column("title", sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_index("ix_quote_tenant_quote_number", table_name="quote")
    op.drop_column("quote", "quote_number")
    op.drop_column("quote", "title")
