"""SD-3: Annual billing schema — column renames + additions + founders_plan price fix.

Revision ID: 2f0c2875f4bd
Revises: 309a42729745
Create Date: 2026-07-14 14:59:00.000000

Changes:
  1. Renames subscription_tier.monthly_price_cents → annual_price_cents
     (holds annual-rate display price per month: $49/$149)
  2. Renames subscription_tier.stripe_price_id → stripe_price_id_monthly
  3. Adds subscription_tier.monthly_price_cents (new — month-to-month premium: $59/$179)
  4. Adds subscription_tier.stripe_price_id_annual (nullable — Tom populates after Stripe Dashboard)
  5. Fixes product_plan_version.price_cents for founders_plan from 4900 → 0
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "2f0c2875f4bd"
down_revision = "309a42729745"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("SET LOCAL session_replication_role = 'replica';")

    # ── Step 1: Rename existing columns ──────────────────────────────────────
    # monthly_price_cents → annual_price_cents
    # (holds annual-rate display price per month: $49/$149)
    op.alter_column(
        "subscription_tier",
        "monthly_price_cents",
        new_column_name="annual_price_cents",
        schema="public",
    )

    # stripe_price_id → stripe_price_id_monthly
    op.alter_column(
        "subscription_tier",
        "stripe_price_id",
        new_column_name="stripe_price_id_monthly",
        schema="public",
    )

    # ── Step 2: Add monthly_price_cents (3-part NOT NULL pattern) ────────────
    # Part 1: Add as nullable
    op.add_column(
        "subscription_tier",
        sa.Column("monthly_price_cents", sa.Integer(), nullable=True),
        schema="public",
    )

    # Part 2: Backfill with correct month-to-month premium prices
    op.execute("""
        UPDATE public.subscription_tier
        SET monthly_price_cents = CASE
            WHEN tier_name = 'starter' THEN 5900
            WHEN tier_name = 'teams'   THEN 17900
            ELSE 0
        END;
    """)

    # Part 3: Lock NOT NULL
    op.alter_column(
        "subscription_tier",
        "monthly_price_cents",
        nullable=False,
        schema="public",
    )

    # ── Step 3: Add stripe_price_id_annual (nullable — Tom populates later) ──
    op.add_column(
        "subscription_tier",
        sa.Column("stripe_price_id_annual", sa.Text(), nullable=True),
        schema="public",
    )

    # ── Step 4: Fix founders_plan product_plan_version price_cents ───────────
    # MKT-B11 incorrectly set price_cents=4900 for founders_plan.
    # Founders plan list price is $0 during the free cohort period.
    # The $49/mo billing activating at month 7 is a Stripe Subscription
    # Schedule event (STRIPE-B1 scope) — not a plan-price change.
    op.execute("""
        UPDATE public.product_plan_version
        SET price_cents = 0
        WHERE product_plan_code = 'founders_plan'
          AND price_cents != 0;
    """)


def downgrade() -> None:
    # Restore founders_plan price_cents
    op.execute("""
        UPDATE public.product_plan_version
        SET price_cents = 4900
        WHERE product_plan_code = 'founders_plan'
          AND price_cents = 0;
    """)

    # Drop new columns
    op.drop_column("subscription_tier", "stripe_price_id_annual", schema="public")
    op.drop_column("subscription_tier", "monthly_price_cents", schema="public")

    # Rename back
    op.alter_column(
        "subscription_tier",
        "stripe_price_id_monthly",
        new_column_name="stripe_price_id",
        schema="public",
    )
    op.alter_column(
        "subscription_tier",
        "annual_price_cents",
        new_column_name="monthly_price_cents",
        schema="public",
    )
