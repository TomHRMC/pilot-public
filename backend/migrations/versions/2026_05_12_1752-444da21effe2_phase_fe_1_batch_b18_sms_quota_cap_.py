"""phase_fe_1_batch_b18_sms_quota_cap_policy_setting

FIND-104 (S2 High) — Seed sms_quota_cap_policy into platform_setting_catalog
and platform_setting (NULL tenant_id = platform default = 'soft').

Removes the hardcoded _DEFAULT_CAP_POLICY='soft' from services/sms_quota.py
(done in code change). Setting is now resolved via get_effective_setting().

Revision ID: 444da21effe2
Revises: 1fe208018f52
Create Date: 2026-05-12 17:52:00.000000
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "444da21effe2"
down_revision = "1fe208018f52"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Part 1: Seed the catalog entry
    # audit.log_changes() has the 'unknown_' entity_id fallback in place at this
    # point in the chain. BEFORE UPDATE triggers don't fire on INSERT. No bypass needed.
    op.execute("""
        INSERT INTO platform_setting_catalog
            (key, label, description, value_type, tenant_editable, allows_user_override,
             min_value, max_value, allowed_values, category, is_active, sort_order)
        VALUES
        ('sms_quota_cap_policy',
         'SMS quota cap policy',
         'Controls what happens when a tenant hits their monthly SMS quota. '
         '''soft'' allows overages billed at $0.05/segment; '
         '''hard'' blocks outbound SMS when quota is reached.',
         'string', true, false,
         NULL, NULL, '["soft","hard"]'::jsonb,
         'notifications', true, 100)
        ON CONFLICT (key) DO NOTHING
    """)

    # Part 2: Seed the platform default (NULL tenant_id = system-wide default)
    # Use WHERE NOT EXISTS because ON CONFLICT with partial index isn't available here
    op.execute("""
        INSERT INTO platform_setting (tenant_id, key, value)
        SELECT NULL, 'sms_quota_cap_policy', '"soft"'
        WHERE NOT EXISTS (
            SELECT 1 FROM platform_setting
            WHERE key = 'sms_quota_cap_policy' AND tenant_id IS NULL
        )
    """)


def downgrade() -> None:
    op.execute(
        "DELETE FROM platform_setting "
        "WHERE key = 'sms_quota_cap_policy' AND tenant_id IS NULL"
    )
    op.execute(
        "DELETE FROM platform_setting_catalog WHERE key = 'sms_quota_cap_policy'"
    )
