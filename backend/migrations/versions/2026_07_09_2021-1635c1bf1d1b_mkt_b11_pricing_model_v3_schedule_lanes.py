"""mkt_b11_pricing_model_v3_schedule_lanes

Revision ID: 1635c1bf1d1b
Revises: 4a2fbda323db
Create Date: 2026-07-09 20:21:50

MKT-B11-BE: Pricing Model v3.0 DB Migration
- Deletes stale ppfv rows (12) and ppv rows (3)
- Deletes dispatch_slots and data_exports product_features
- Inserts schedule_lanes product_feature
- Adds founders_plan; marks starter_plan/teams is_active=false; deletes enterprise_plan
- Drops max_users and max_sms_segments_per_month from subscription_tier
- Adds schedule_lanes column to subscription_tier
- Inserts 4 correct tier rows: founders (active), trial/starter/teams (inactive)
- Inserts 9 correct ppfv rows (founders_plan×3, starter_plan×3, teams×3)
- Inserts 3 correct ppv rows
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "1635c1bf1d1b"
down_revision = "4a2fbda323db"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("SET LOCAL session_replication_role = 'replica';")

    # STEP 1: Delete all ppfv and ppv stale rows (clear FK dependencies first)
    op.execute("DELETE FROM public.product_plan_product_feature_version;")
    op.execute("DELETE FROM public.product_plan_version;")

    # STEP 2: Delete stale feature rows; insert schedule_lanes
    op.execute(
        "DELETE FROM public.product_feature WHERE code IN ('dispatch_slots', 'data_exports');"
    )
    op.execute("""
        INSERT INTO public.product_feature
        (code, name, unit, description, is_active, created_at, updated_at)
        VALUES
        ('schedule_lanes', 'Schedule Lanes', 'lanes',
         'Concurrent job slots on the dispatch board. One lane = one parallel scheduling row. Any user can be assigned to jobs in any lane.',
         true, NOW(), NOW())
        ON CONFLICT (code) DO NOTHING;
    """)

    # STEP 3: Rebuild product_plan (add founders_plan; set inactive; delete enterprise_plan)
    op.execute("""
        INSERT INTO public.product_plan
        (code, name, description, is_active, created_at, updated_at)
        VALUES
        ('founders_plan', 'Founders Plan',
         'Time-limited founding member cohort plan. 6 months free, then $49/mo locked at Starter limits for life.',
         true, NOW(), NOW())
        ON CONFLICT (code) DO NOTHING;
    """)
    op.execute(
        "UPDATE public.product_plan SET is_active = false, updated_at = NOW() WHERE code IN ('starter_plan', 'teams');"
    )
    # Reassign any subscriptions pointing to enterprise_plan or professional_plan → founders_plan
    # (session_replication_role = replica disables FK triggers, but we do this explicitly for correctness)
    op.execute("""
        UPDATE public.subscription
        SET product_plan_code = 'founders_plan', updated_at = NOW()
        WHERE product_plan_code IN ('enterprise_plan', 'professional_plan');
    """)
    op.execute("DELETE FROM public.product_plan WHERE code = 'enterprise_plan';")

    # STEP 4: Rebuild subscription_tier (delete all; drop old columns; add schedule_lanes; insert 4 correct rows)
    op.execute("DELETE FROM public.subscription_tier;")
    op.execute("ALTER TABLE public.subscription_tier DROP COLUMN IF EXISTS max_users;")
    op.execute(
        "ALTER TABLE public.subscription_tier DROP COLUMN IF EXISTS max_sms_segments_per_month;"
    )
    op.execute(
        "ALTER TABLE public.subscription_tier ADD COLUMN IF NOT EXISTS schedule_lanes INTEGER NOT NULL DEFAULT 0;"
    )
    op.execute("""
        INSERT INTO public.subscription_tier
        (tier_id, tier_name, display_label, monthly_price_cents, is_trial,
         trial_duration_days, is_active, display_order, schedule_lanes,
         product_plan_code, created_at, updated_at)
        VALUES
        (gen_random_uuid(), 'founders', 'Founders', 0, false,
         NULL, true, 0, 5, 'founders_plan', NOW(), NOW()),
        (gen_random_uuid(), 'trial', 'Trial', 0, true,
         14, false, 1, 5, 'starter_plan', NOW(), NOW()),
        (gen_random_uuid(), 'starter', 'Starter', 4900, false,
         NULL, false, 2, 5, 'starter_plan', NOW(), NOW()),
        (gen_random_uuid(), 'teams', 'Teams', 14900, false,
         NULL, false, 3, 20, 'teams', NOW(), NOW());
    """)

    # STEP 5: Insert 9 correct ppfv rows (founders_plan × 3, starter_plan × 3, teams × 3)
    op.execute("""
        INSERT INTO public.product_plan_product_feature_version
        (product_plan_code, product_feature_code, limit_quantity, included_quantity,
         overage_price_cents, limit_enforcement, valid_period, recorded_at, created_at)
        VALUES
        ('founders_plan', 'schedule_lanes', 5, 5, NULL, 'block', tstzrange(NOW(), NULL), NOW(), NOW()),
        ('founders_plan', 'voice_ai_minutes', 90, 90, 5, 'soft', tstzrange(NOW(), NULL), NOW(), NOW()),
        ('founders_plan', 'outbound_sms_segments', 100, 100, 5, 'soft', tstzrange(NOW(), NULL), NOW(), NOW()),
        ('starter_plan', 'schedule_lanes', 5, 5, NULL, 'block', tstzrange(NOW(), NULL), NOW(), NOW()),
        ('starter_plan', 'voice_ai_minutes', 90, 90, 5, 'soft', tstzrange(NOW(), NULL), NOW(), NOW()),
        ('starter_plan', 'outbound_sms_segments', 100, 100, 5, 'soft', tstzrange(NOW(), NULL), NOW(), NOW()),
        ('teams', 'schedule_lanes', 20, 20, NULL, 'block', tstzrange(NOW(), NULL), NOW(), NOW()),
        ('teams', 'voice_ai_minutes', 300, 300, 5, 'soft', tstzrange(NOW(), NULL), NOW(), NOW()),
        ('teams', 'outbound_sms_segments', 500, 500, 5, 'soft', tstzrange(NOW(), NULL), NOW(), NOW());
    """)

    # STEP 6: Insert 3 correct ppv rows
    op.execute("""
        INSERT INTO public.product_plan_version
        (product_plan_code, name, price_cents, valid_period, recorded_at, created_at)
        VALUES
        ('founders_plan', 'Founders Plan', 4900, tstzrange(NOW(), NULL), NOW(), NOW()),
        ('starter_plan', 'Starter Plan', 4900, tstzrange(NOW(), NULL), NOW(), NOW()),
        ('teams', 'Teams Plan', 14900, tstzrange(NOW(), NULL), NOW(), NOW());
    """)

    # STEP 7: Reassign all tenants whose current_subscription_tier_id points to a
    # now-deleted tier UUID → redirect to the founders tier.
    # This fixes dev/test tenant FK integrity after the tier table wipe+rebuild.
    op.execute("""
        UPDATE public.tenant
        SET current_subscription_tier_id = (
            SELECT tier_id FROM public.subscription_tier WHERE tier_name = 'founders' LIMIT 1
        ),
        updated_at = NOW()
        WHERE current_subscription_tier_id IS NOT NULL
          AND NOT EXISTS (
            SELECT 1 FROM public.subscription_tier
            WHERE tier_id = tenant.current_subscription_tier_id
          );
    """)


def downgrade() -> None:
    # DEV DB ONLY — not production-safe. Restores pre-v3.0 schema skeleton.
    # Full downgrade of real production data requires a DB restore from backup.
    # This downgrade re-adds the old columns and drops schedule_lanes, but does NOT
    # re-insert the old tier rows (trial/starter/professional/enterprise) with their
    # original max_users values because that data is lost. Similarly, dispatch_slots
    # and data_exports features are not re-inserted, and enterprise_plan is not restored.
    op.execute("SET LOCAL session_replication_role = 'replica';")
    op.execute("DELETE FROM public.product_plan_product_feature_version;")
    op.execute("DELETE FROM public.product_plan_version;")
    op.execute("DELETE FROM public.subscription_tier;")
    op.execute(
        "ALTER TABLE public.subscription_tier DROP COLUMN IF EXISTS schedule_lanes;"
    )
    op.execute(
        "ALTER TABLE public.subscription_tier ADD COLUMN IF NOT EXISTS max_users INTEGER;"
    )
    op.execute(
        "ALTER TABLE public.subscription_tier ADD COLUMN IF NOT EXISTS max_sms_segments_per_month INTEGER;"
    )
    op.execute("DELETE FROM public.product_feature WHERE code = 'schedule_lanes';")
    # Note: dispatch_slots and data_exports NOT re-inserted; enterprise_plan NOT re-inserted.
    # Note: founders_plan is left as-is (was not present before upgrade).
    # Note: subscription_tier rows NOT re-inserted — original max_users values are lost.
    # A production downgrade requires restoring from a backup taken before this migration.
