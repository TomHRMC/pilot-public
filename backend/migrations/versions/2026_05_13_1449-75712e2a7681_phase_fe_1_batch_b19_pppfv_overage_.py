"""phase_fe_1_batch_b19_pppfv_overage_price_required

Revision ID: 75712e2a7681
Revises: b19find101seed
Create Date: 2026-05-13 14:49:59.554059+00:00

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "75712e2a7681"
down_revision: str | None = "b19find101seed"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add CHECK constraint to product_plan_product_feature_version
    # Enforces: if limit_enforcement != 'block', then overage_price_cents must be NOT NULL
    op.create_check_constraint(
        "chk_pppfv_overage_price_required_when_soft",
        "product_plan_product_feature_version",
        "limit_enforcement = 'block' OR overage_price_cents IS NOT NULL",
    )


def downgrade() -> None:
    # Drop the CHECK constraint
    op.drop_constraint(
        "chk_pppfv_overage_price_required_when_soft",
        "product_plan_product_feature_version",
        type_="check",
    )
