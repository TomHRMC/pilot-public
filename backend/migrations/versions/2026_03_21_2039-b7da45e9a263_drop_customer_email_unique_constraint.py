"""drop_customer_email_unique_constraint

Revision ID: b7da45e9a263
Revises: 808181099844
Create Date: 2026-03-21 20:39:45.984622+00:00

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7da45e9a263"
down_revision: str | None = "808181099844"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Drop unique constraint on customer.email to allow duplicate emails
    # QuickBooks allows multiple customers with the same email (common for companies)
    op.drop_constraint("customer_email_key", "customer", type_="unique")


def downgrade() -> None:
    # Re-add unique constraint on customer.email
    # WARNING: This will fail if there are duplicate emails in the table
    op.create_unique_constraint("customer_email_key", "customer", ["email"])
