"""phase_fe_1_batch_b18_customer_taxability_code

FIND-107 (S2 High) — Add customer.taxability_code VARCHAR NULL FK → taxability_code(code).

NULL = customer is taxable (use line-level defaults).
Non-NULL = customer has a blanket taxability override (e.g., 'exempt').
New quote lines for this customer inherit the customer-level taxability_code.

Revision ID: 1e0785ece81a
Revises: 444da21effe2
Create Date: 2026-05-12 17:59:00.000000
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "1e0785ece81a"
down_revision = "444da21effe2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "customer",
        sa.Column("taxability_code", sa.String(), nullable=True),
    )
    op.create_foreign_key(
        "fk_customer_taxability_code",
        "customer",
        "taxability_code",
        ["taxability_code"],
        ["code"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint("fk_customer_taxability_code", "customer", type_="foreignkey")
    op.drop_column("customer", "taxability_code")
