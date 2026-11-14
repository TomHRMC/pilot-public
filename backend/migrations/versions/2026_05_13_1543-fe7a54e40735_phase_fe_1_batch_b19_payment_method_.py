"""phase_fe_1_batch_b19_payment_method_customer_fk

Revision ID: fe7a54e40735
Revises: 75712e2a7681
Create Date: 2026-05-13 15:43:50.394605+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "fe7a54e40735"
down_revision: str | None = "75712e2a7681"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Part 1: Add columns
    op.add_column("payment_method", sa.Column("customer_id", sa.Uuid(), nullable=True))
    op.add_column(
        "payment_method",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
    )

    # Part 2: Create FK constraint
    op.create_foreign_key(
        "fk_payment_method_customer_id",
        "payment_method",
        "customer",
        ["customer_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    # Part 3: Create index for fast lookup by customer
    op.create_index("ix_payment_method_customer_id", "payment_method", ["customer_id"])


def downgrade() -> None:
    # Drop index
    op.drop_index("ix_payment_method_customer_id", table_name="payment_method")

    # Drop FK constraint
    op.drop_constraint(
        "fk_payment_method_customer_id", "payment_method", type_="foreignkey"
    )

    # Drop columns
    op.drop_column("payment_method", "customer_id")
    op.drop_column("payment_method", "is_active")
