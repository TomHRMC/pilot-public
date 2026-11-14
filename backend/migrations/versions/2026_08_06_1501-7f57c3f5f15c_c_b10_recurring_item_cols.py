"""c_b10_recurring_item_cols

Revision ID: 7f57c3f5f15c
Revises: b7bb6c0bb38a
Create Date: 2026-08-06 15:01:04.627893+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7f57c3f5f15c"
down_revision: str | None = "b7bb6c0bb38a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("SET LOCAL session_replication_role = 'replica';")
    op.add_column(
        "tenant_messaging_registration",
        sa.Column("stripe_recurring_item_id", sa.Text(), nullable=True),
    )
    op.add_column(
        "tenant_messaging_registration",
        sa.Column(
            "recurring_item_created_at", sa.DateTime(timezone=True), nullable=True
        ),
    )


def downgrade() -> None:
    op.execute("SET LOCAL session_replication_role = 'replica';")
    op.drop_column("tenant_messaging_registration", "recurring_item_created_at")
    op.drop_column("tenant_messaging_registration", "stripe_recurring_item_id")
