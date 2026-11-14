"""phase_fe_1_batch_b19_subscription_tier_product_plan_code

Revision ID: 2369fb1773a6
Revises: 00b2f1d3e1ce
Create Date: 2026-05-12 21:00:33.204408+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2369fb1773a6"
down_revision: str | None = "00b2f1d3e1ce"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "subscription_tier", sa.Column("product_plan_code", sa.String(), nullable=True)
    )
    op.create_index(
        "ix_subscription_tier_product_plan_code",
        "subscription_tier",
        ["product_plan_code"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_subscription_tier_product_plan_code", table_name="subscription_tier"
    )
    op.drop_column("subscription_tier", "product_plan_code")
