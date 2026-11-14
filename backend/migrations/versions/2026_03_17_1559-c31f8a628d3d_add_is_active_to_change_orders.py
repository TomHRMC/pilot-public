"""add_is_active_to_change_orders

Revision ID: c31f8a628d3d
Revises: a4d2659a2921
Create Date: 2026-03-17 15:59:46.460208+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c31f8a628d3d"
down_revision: str | None = "a4d2659a2921"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add is_active column to change_order table
    op.add_column(
        "change_order",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
    )

    # Add is_active column to change_order_line table
    op.add_column(
        "change_order_line",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
    )


def downgrade() -> None:
    # Remove is_active column from change_order_line table
    op.drop_column("change_order_line", "is_active")

    # Remove is_active column from change_order table
    op.drop_column("change_order", "is_active")
