"""sd07_revise_product_features_and_plan_rename

Revision ID: fb896203a21a
Revises: eb757cc7d9eb
Create Date: 2026-07-06 21:59:17.000000

SD-07: Revise product feature set and rename professional_plan → teams.

Changes:
  1. Rename product_plan code + name: professional_plan → teams
  2. Update product_plan_product_feature_version rows referencing professional_plan → teams
  3. Delete product_plan_product_feature_version rows for qb_sync_operations
  4. Delete qb_sync_operations from product_feature
  5. Insert dispatch_slots and outbound_sms_segments into product_feature
  6. Update data_exports limit_quantity for starter (5→0) and teams (25→-1)
  7. Insert new product_plan_product_feature_version rows for dispatch_slots + outbound_sms_segments

Schema verified (MCP 2026-07-06):
  product_plan: code (PK), name, description, is_active, created_at, updated_at
  product_feature: code (PK), name, unit (NOT NULL), description, is_active, created_at, updated_at
  product_plan_product_feature_version (AppendOnly): id (serial PK), product_plan_code, product_feature_code,
    limit_quantity, included_quantity, overage_price_cents, valid_period (tstzrange), recorded_at,
    created_at, limit_enforcement (NOT NULL), overage_cap_per_period, alert_threshold_pct
  No FK constraints between ppfv and product_plan/product_feature.
"""

from alembic import op

# revision identifiers
revision: str = "fb896203a21a"
down_revision: str = "eb757cc7d9eb"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("SET LOCAL session_replication_role = 'replica';")

    # 1. Rename professional_plan → teams in product_plan
    op.execute("""
        UPDATE public.product_plan
        SET code = 'teams',
            name = 'Teams Plan',
            updated_at = NOW()
        WHERE code = 'professional_plan';
    """)

    # 2. Update ppfv rows referencing professional_plan → teams
    op.execute("""
        UPDATE public.product_plan_product_feature_version
        SET product_plan_code = 'teams'
        WHERE product_plan_code = 'professional_plan';
    """)

    # 3. Delete ppfv rows for qb_sync_operations (feature being removed)
    op.execute("""
        DELETE FROM public.product_plan_product_feature_version
        WHERE product_feature_code = 'qb_sync_operations';
    """)

    # 4. Delete qb_sync_operations from product_feature
    op.execute("""
        DELETE FROM public.product_feature
        WHERE code = 'qb_sync_operations';
    """)

    # 5. Insert dispatch_slots and outbound_sms_segments into product_feature
    #    unit column is NOT NULL — 'count' is appropriate for both
    op.execute("""
        INSERT INTO public.product_feature
            (code, name, unit, description, is_active, created_at, updated_at)
        VALUES
            ('dispatch_slots', 'Dispatch Slots', 'slots',
             'Maximum concurrent field technician dispatch slots', true, NOW(), NOW()),
            ('outbound_sms_segments', 'Outbound SMS Segments', 'segments',
             'Outbound SMS segments per billing cycle', true, NOW(), NOW())
        ON CONFLICT (code) DO NOTHING;
    """)

    # 6. Update data_exports limits to match GTM matrix:
    #    starter: 5 → 0 (blocked), teams: 25 → -1 (unlimited), enterprise: -1 (unchanged)
    op.execute("""
        UPDATE public.product_plan_product_feature_version
        SET limit_quantity = 0, included_quantity = 0
        WHERE product_plan_code = 'starter_plan'
          AND product_feature_code = 'data_exports';
    """)

    op.execute("""
        UPDATE public.product_plan_product_feature_version
        SET limit_quantity = -1, included_quantity = -1
        WHERE product_plan_code = 'teams'
          AND product_feature_code = 'data_exports';
    """)

    # voice_ai_minutes: teams was 300 → update to 240 per GTM matrix
    op.execute("""
        UPDATE public.product_plan_product_feature_version
        SET limit_quantity = 240, included_quantity = 240
        WHERE product_plan_code = 'teams'
          AND product_feature_code = 'voice_ai_minutes';
    """)

    # voice_ai_minutes: enterprise was -1 (unlimited) → 1000 per GTM matrix
    op.execute("""
        UPDATE public.product_plan_product_feature_version
        SET limit_quantity = 1000, included_quantity = 1000
        WHERE product_plan_code = 'enterprise_plan'
          AND product_feature_code = 'voice_ai_minutes';
    """)

    # 7. Insert ppfv rows for dispatch_slots (starter=5, teams=25, enterprise=75)
    op.execute("""
        INSERT INTO public.product_plan_product_feature_version
            (product_plan_code, product_feature_code, limit_quantity, included_quantity,
             overage_price_cents, limit_enforcement, valid_period, recorded_at, created_at)
        VALUES
            ('starter_plan',    'dispatch_slots', 5,  5,  0, 'soft', tstzrange(NOW(), NULL), NOW(), NOW()),
            ('teams',           'dispatch_slots', 25, 25, 0, 'soft', tstzrange(NOW(), NULL), NOW(), NOW()),
            ('enterprise_plan', 'dispatch_slots', 75, 75, 0, 'soft', tstzrange(NOW(), NULL), NOW(), NOW())
        ON CONFLICT DO NOTHING;
    """)

    # 8. Insert ppfv rows for outbound_sms_segments (starter=100, teams=500, enterprise=2500)
    op.execute("""
        INSERT INTO public.product_plan_product_feature_version
            (product_plan_code, product_feature_code, limit_quantity, included_quantity,
             overage_price_cents, limit_enforcement, valid_period, recorded_at, created_at)
        VALUES
            ('starter_plan',    'outbound_sms_segments', 100,  100,  0, 'soft', tstzrange(NOW(), NULL), NOW(), NOW()),
            ('teams',           'outbound_sms_segments', 500,  500,  0, 'soft', tstzrange(NOW(), NULL), NOW(), NOW()),
            ('enterprise_plan', 'outbound_sms_segments', 2500, 2500, 0, 'soft', tstzrange(NOW(), NULL), NOW(), NOW())
        ON CONFLICT DO NOTHING;
    """)


def downgrade() -> None:
    op.execute("SET LOCAL session_replication_role = 'replica';")

    # Remove dispatch_slots and outbound_sms_segments ppfv rows
    op.execute("""
        DELETE FROM public.product_plan_product_feature_version
        WHERE product_feature_code IN ('dispatch_slots', 'outbound_sms_segments');
    """)

    # Remove dispatch_slots and outbound_sms_segments from product_feature
    op.execute("""
        DELETE FROM public.product_feature
        WHERE code IN ('dispatch_slots', 'outbound_sms_segments');
    """)

    # Restore qb_sync_operations in product_feature
    op.execute("""
        INSERT INTO public.product_feature
            (code, name, unit, description, is_active, created_at, updated_at)
        VALUES
            ('qb_sync_operations', 'QB sync operations', 'operations',
             'Number of QuickBooks Online sync operations (journal entries, items, etc)',
             true, NOW(), NOW())
        ON CONFLICT (code) DO NOTHING;
    """)

    # Re-insert qb_sync_operations ppfv rows (original values: starter=100, teams→professional=500, enterprise=-1)
    op.execute("""
        INSERT INTO public.product_plan_product_feature_version
            (product_plan_code, product_feature_code, limit_quantity, included_quantity,
             overage_price_cents, limit_enforcement, valid_period, recorded_at, created_at)
        VALUES
            ('starter_plan',    'qb_sync_operations', 100, 100, 0, 'soft', tstzrange(NOW(), NULL), NOW(), NOW()),
            ('professional_plan', 'qb_sync_operations', 500, 500, 0, 'soft', tstzrange(NOW(), NULL), NOW(), NOW()),
            ('enterprise_plan', 'qb_sync_operations', -1, -1, 0, 'soft', tstzrange(NOW(), NULL), NOW(), NOW())
        ON CONFLICT DO NOTHING;
    """)

    # Restore data_exports limits to original values
    op.execute("""
        UPDATE public.product_plan_product_feature_version
        SET limit_quantity = 5, included_quantity = 5
        WHERE product_plan_code = 'starter_plan'
          AND product_feature_code = 'data_exports';
    """)

    op.execute("""
        UPDATE public.product_plan_product_feature_version
        SET limit_quantity = 25, included_quantity = 25
        WHERE product_plan_code = 'professional_plan'
          AND product_feature_code = 'data_exports';
    """)

    # Restore voice_ai_minutes original values
    op.execute("""
        UPDATE public.product_plan_product_feature_version
        SET limit_quantity = 300, included_quantity = 300
        WHERE product_plan_code = 'professional_plan'
          AND product_feature_code = 'voice_ai_minutes';
    """)

    op.execute("""
        UPDATE public.product_plan_product_feature_version
        SET limit_quantity = -1, included_quantity = -1
        WHERE product_plan_code = 'enterprise_plan'
          AND product_feature_code = 'voice_ai_minutes';
    """)

    # Rename ppfv rows back: teams → professional_plan
    op.execute("""
        UPDATE public.product_plan_product_feature_version
        SET product_plan_code = 'professional_plan'
        WHERE product_plan_code = 'teams';
    """)

    # Rename product_plan back: teams → professional_plan
    op.execute("""
        UPDATE public.product_plan
        SET code = 'professional_plan',
            name = 'Professional Plan',
            updated_at = NOW()
        WHERE code = 'teams';
    """)
