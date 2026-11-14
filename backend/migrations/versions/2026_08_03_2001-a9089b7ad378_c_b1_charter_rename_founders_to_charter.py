"""c_b1_charter_rename_founders_to_charter

Revision ID: a9089b7ad378
Revises: 388bab9c7b7d
Create Date: 2026-08-03 20:01:28.444517+00:00

C-B1 (Part A): Rename "founders"/"founders_plan" → "charter"/"charter_plan" per GTM v3 D14.

This is a pure data-level UPDATE migration (no DDL). It renames:
  - product_plan.code: 'founders_plan' → 'charter_plan'
  - product_plan.name: 'Founders Plan' → 'Charter'
  - product_plan.description: updated to Charter program description
  - subscription_tier.tier_name: 'founders' → 'charter'
  - subscription_tier.display_label: 'Founders' → 'Charter'
  - subscription_tier.product_plan_code: 'founders_plan' → 'charter_plan'
  - All 4 FK tables referencing product_plan.code updated atomically

Uses SET LOCAL session_replication_role = replica to disable FK triggers during
the atomic PK rename (product_plan.code is a PK referenced by 4 tables).

Verified via postgres-local MCP (2026-08-03):
  - subscription_tier columns: tier_name, display_label, product_plan_code
  - product_plan columns: code (PK), name, description, is_active
  - 4 FK tables: product_plan_version, product_plan_product_feature_version,
    subscription, subscription_tier
  - Blast radius: subscription=1, product_plan_version=1,
    product_plan_product_feature_version=3, subscription_tier=1
"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a9089b7ad378"
down_revision: Union[str, None] = "388bab9c7b7d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Step 1: Disable FK triggers for atomic PK rename
    # product_plan.code is a PK referenced by 4 tables; updating it in-place
    # would violate FK constraints unless triggers are disabled.
    op.execute("SET LOCAL session_replication_role = 'replica';")

    # Step 2: Rename product_plan PK + display name + description
    op.execute(
        sa.text(
            """
            UPDATE public.product_plan
            SET code = 'charter_plan',
                name = 'Charter',
                description = 'Charter program plan. 90 days free, then $49/mo locked at Starter limits for as long as subscribed.',
                updated_at = NOW()
            WHERE code = 'founders_plan'
            """
        )
    )

    # Step 3: Rename subscription_tier (tier_name, display_label, product_plan_code)
    op.execute(
        sa.text(
            """
            UPDATE public.subscription_tier
            SET tier_name = 'charter',
                display_label = 'Charter',
                product_plan_code = 'charter_plan',
                updated_at = NOW()
            WHERE tier_name = 'founders'
            """
        )
    )

    # Step 4: Update all FK references to product_plan.code
    op.execute(
        sa.text(
            """
            UPDATE public.product_plan_version
            SET product_plan_code = 'charter_plan'
            WHERE product_plan_code = 'founders_plan'
            """
        )
    )

    op.execute(
        sa.text(
            """
            UPDATE public.product_plan_product_feature_version
            SET product_plan_code = 'charter_plan'
            WHERE product_plan_code = 'founders_plan'
            """
        )
    )

    op.execute(
        sa.text(
            """
            UPDATE public.subscription
            SET product_plan_code = 'charter_plan',
                updated_at = NOW()
            WHERE product_plan_code = 'founders_plan'
            """
        )
    )

    # Step 5: Re-enable FK triggers
    op.execute("SET LOCAL session_replication_role = 'origin';")


def downgrade() -> None:
    # Reverse all UPDATEs — exact mirror of upgrade()
    op.execute("SET LOCAL session_replication_role = 'replica';")

    # Reverse FK references first
    op.execute(
        sa.text(
            """
            UPDATE public.subscription
            SET product_plan_code = 'founders_plan',
                updated_at = NOW()
            WHERE product_plan_code = 'charter_plan'
            """
        )
    )

    op.execute(
        sa.text(
            """
            UPDATE public.product_plan_product_feature_version
            SET product_plan_code = 'founders_plan'
            WHERE product_plan_code = 'charter_plan'
            """
        )
    )

    op.execute(
        sa.text(
            """
            UPDATE public.product_plan_version
            SET product_plan_code = 'founders_plan'
            WHERE product_plan_code = 'charter_plan'
            """
        )
    )

    # Reverse subscription_tier
    op.execute(
        sa.text(
            """
            UPDATE public.subscription_tier
            SET tier_name = 'founders',
                display_label = 'Founders',
                product_plan_code = 'founders_plan',
                updated_at = NOW()
            WHERE tier_name = 'charter'
            """
        )
    )

    # Reverse product_plan PK + name + description
    op.execute(
        sa.text(
            """
            UPDATE public.product_plan
            SET code = 'founders_plan',
                name = 'Founders Plan',
                description = 'Time-limited founding member cohort plan. 6 months free, then $49/mo locked at Starter limits for life.',
                updated_at = NOW()
            WHERE code = 'charter_plan'
            """
        )
    )

    op.execute("SET LOCAL session_replication_role = 'origin';")
