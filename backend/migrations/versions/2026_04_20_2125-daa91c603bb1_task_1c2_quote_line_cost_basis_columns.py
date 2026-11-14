"""task_1c2_quote_line_cost_basis_columns

Revision ID: daa91c603bb1
Revises: 79d53b7fcffa
Create Date: 2026-04-20 21:25:00.000000

Task 1-C-2: Add unit_cost_cents (BIGINT, nullable) and cost_source (VARCHAR, nullable)
to the quote_line table.

These columns store the raw material or labor cost at the time the line is added,
enabling the API to compute a pre-sale gross margin (unit_price_cents - unit_cost_cents).
This is a core differentiator that prevents underbidding — a primary AevoFab value proposition.
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "daa91c603bb1"
down_revision = "79d53b7fcffa"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add unit_cost_cents: raw material/labor cost at line-creation time (nullable — not all
    # lines require a cost basis, e.g. discount or note lines)
    op.add_column(
        "quote_line",
        sa.Column("unit_cost_cents", sa.BigInteger(), nullable=True),
    )

    # Add cost_source: origin of the cost value (e.g. 'supplier_catalog', 'manual', 'labor_rate')
    op.add_column(
        "quote_line",
        sa.Column("cost_source", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("quote_line", "cost_source")
    op.drop_column("quote_line", "unit_cost_cents")
