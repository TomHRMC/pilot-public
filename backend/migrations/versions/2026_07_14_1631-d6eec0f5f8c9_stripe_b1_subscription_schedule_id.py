"""STRIPE-B1: Add stripe_schedule_id to subscription for Founders cohort schedule tracking.

Revision ID: d6eec0f5f8c9
Revises: 2f0c2875f4bd
Create Date: 2026-07-14 16:31:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d6eec0f5f8c9"
down_revision: str | None = "2f0c2875f4bd"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "subscription",
        sa.Column("stripe_schedule_id", sa.Text(), nullable=True),
        schema="public",
    )


def downgrade() -> None:
    op.drop_column("subscription", "stripe_schedule_id", schema="public")
