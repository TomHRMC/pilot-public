"""SD-3: Rename product_plan code 'teams' → 'teams_plan' with FK cascade.

Revision ID: 309a42729745
Revises: 888fb75f8048
Create Date: 2026-07-14 14:58:00.000000

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "309a42729745"
down_revision = "888fb75f8048"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("SET LOCAL session_replication_role = 'replica';")

    # Rename the plan code
    op.execute("""
        UPDATE public.product_plan
        SET code = 'teams_plan', updated_at = NOW()
        WHERE code = 'teams';
    """)

    # Cascade to product_plan_version
    op.execute("""
        UPDATE public.product_plan_version
        SET product_plan_code = 'teams_plan'
        WHERE product_plan_code = 'teams';
    """)

    # Cascade to product_plan_product_feature_version
    op.execute("""
        UPDATE public.product_plan_product_feature_version
        SET product_plan_code = 'teams_plan'
        WHERE product_plan_code = 'teams';
    """)

    # Cascade to subscription_tier
    op.execute("""
        UPDATE public.subscription_tier
        SET product_plan_code = 'teams_plan', updated_at = NOW()
        WHERE product_plan_code = 'teams';
    """)

    # Cascade to subscription (may have rows for test tenant)
    op.execute("""
        UPDATE public.subscription
        SET product_plan_code = 'teams_plan', updated_at = NOW()
        WHERE product_plan_code = 'teams';
    """)


def downgrade() -> None:
    op.execute("SET LOCAL session_replication_role = 'replica';")
    op.execute(
        "UPDATE public.subscription SET product_plan_code = 'teams', updated_at = NOW() WHERE product_plan_code = 'teams_plan';"
    )
    op.execute(
        "UPDATE public.subscription_tier SET product_plan_code = 'teams', updated_at = NOW() WHERE product_plan_code = 'teams_plan';"
    )
    op.execute(
        "UPDATE public.product_plan_product_feature_version SET product_plan_code = 'teams' WHERE product_plan_code = 'teams_plan';"
    )
    op.execute(
        "UPDATE public.product_plan_version SET product_plan_code = 'teams' WHERE product_plan_code = 'teams_plan';"
    )
    op.execute(
        "UPDATE public.product_plan SET code = 'teams', updated_at = NOW() WHERE code = 'teams_plan';"
    )
