"""phase_fe_1_batch_b18_platform_setting_tables

FIND-086: Create platform_setting_catalog + platform_setting tables.
Drop tenant_settings table (and all its columns).
Add mfa_grace_period_started_at to tenant table.

Resolution: Two-tier EAV replaces flat wide tenant_settings table.
Seed: All 41 catalog entries + 41 NULL platform default rows.

Revision ID: a7c3e5f91b02
Revises: bf1e91a9e960
Create Date: 2026-05-11 21:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "a7c3e5f91b02"
down_revision = "bf1e91a9e960"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ============================================================
    # Step 1: Create platform_setting_catalog table
    # ============================================================
    op.create_table(
        "platform_setting_catalog",
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("user.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column(
            "updated_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("user.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("key", sa.String(), nullable=False),
        sa.Column("label", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "value_type",
            sa.String(),
            sa.CheckConstraint(
                "value_type IN ('integer', 'boolean', 'string', 'decimal', 'jsonb')",
                name="ck_platform_setting_catalog_value_type",
            ),
            nullable=False,
        ),
        sa.Column(
            "tenant_editable",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "allows_user_override",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("min_value", sa.Integer(), nullable=True),
        sa.Column("max_value", sa.Integer(), nullable=True),
        sa.Column("allowed_values", postgresql.JSONB(), nullable=True),
        sa.Column(
            "category",
            sa.String(),
            sa.CheckConstraint(
                "category IN ('quotes','billing','notifications','voice','qb',"
                "'sync','mobile','labor','reports','security','trial','safety')",
                name="ck_platform_setting_catalog_category",
            ),
            nullable=True,
        ),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column(
            "sort_order", sa.Integer(), nullable=False, server_default=sa.text("0")
        ),
        sa.PrimaryKeyConstraint("key"),
    )

    op.execute(
        "CREATE TRIGGER audit_platform_setting_catalog_changes "
        "AFTER INSERT OR UPDATE OR DELETE ON platform_setting_catalog "
        "FOR EACH ROW EXECUTE FUNCTION audit.log_changes();"
    )

    # ============================================================
    # Step 2: Create platform_setting table
    # ============================================================
    op.create_table(
        "platform_setting",
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("user.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column(
            "updated_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("user.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "key",
            sa.String(),
            sa.ForeignKey("platform_setting_catalog.key", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("value", postgresql.JSONB(), nullable=False),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenant.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key", "tenant_id", name="uq_platform_setting_key_tenant"),
    )
    op.create_index("ix_platform_setting_key", "platform_setting", ["key"])
    op.create_index("ix_platform_setting_tenant", "platform_setting", ["tenant_id"])

    op.execute(
        "CREATE TRIGGER audit_platform_setting_changes "
        "AFTER INSERT OR UPDATE OR DELETE ON platform_setting "
        "FOR EACH ROW EXECUTE FUNCTION audit.log_changes();"
    )

    # ============================================================
    # Step 3: Seed platform_setting_catalog (41 rows)
    # audit.log_changes() has the 'unknown_' entity_id fallback at this point in
    # the chain (added in 6350c51bc555). platform_setting has UUID id PK.
    # No session_replication_role bypass needed on RDS.
    # ============================================================
    op.execute("""
    INSERT INTO platform_setting_catalog
        (key, label, description, value_type, tenant_editable, allows_user_override,
         min_value, max_value, allowed_values, category, is_active, sort_order)
    VALUES
    -- QUOTES & APPROVAL
    ('require_approval_for_tech_quotes', 'Require approval for tech quotes',
     'When ON, quotes created by technicians require owner/accountant approval before sending.',
     'boolean', true, false, NULL, NULL, NULL, 'quotes', true, 10),

    ('max_discount_pct_owner', 'Maximum discount percentage',
     'Maximum discount an owner/accountant can apply to a quote before requiring explicit override.',
     'decimal', true, false, 0, 100, NULL, 'quotes', true, 20),

    ('default_quote_validity_days', 'Default quote validity (days)',
     'How many days a new quote is valid before expiring.',
     'integer', true, false, 1, 365, NULL, 'quotes', true, 30),

    ('default_invoice_terms_days', 'Default invoice terms (days)',
     'Default net-payment terms on new invoices (0 = due on receipt).',
     'integer', true, false, 0, 120, NULL, 'quotes', true, 40),

    -- LABOR & COST
    ('default_labor_rate_cents', 'Default labor rate (cents/hour)',
     'Default internal cost rate for labor hours. Operator-only: affects all tenants without a LaborRateVersion row.',
     'integer', false, false, 100, NULL, NULL, 'labor', true, 10),

    ('default_billable_labor_rate_cents', 'Default billable labor rate (cents/hour)',
     'Default customer-facing billable rate for labor. Operator-only.',
     'integer', false, false, 100, NULL, NULL, 'labor', true, 20),

    -- ETC VARIANCE
    ('etc_variance_owner_notify_pct', 'ETC variance owner notify threshold (%)',
     'Notify owner when projected cost exceeds quoted by this percentage.',
     'integer', true, false, 1, 500, NULL, 'reports', true, 10),

    ('etc_variance_note_required_pct', 'ETC variance note required threshold (%)',
     'Require tech to provide a note when ETC increases projected hours by this percentage.',
     'integer', true, false, 1, 200, NULL, 'reports', true, 20),

    -- PROFITABILITY
    ('margin_target_pct', 'Margin target (%)',
     'Jobs below this margin % receive a visual indicator on the profitability dashboard.',
     'integer', true, false, 0, 100, NULL, 'reports', true, 30),

    ('margin_bucket_boundaries', 'Margin bucket boundaries',
     'Three ascending integers defining four margin buckets for the profitability report chart.',
     'jsonb', true, false, NULL, NULL, NULL, 'reports', true, 40),

    ('report_chart_threshold', 'Report chart threshold (rows)',
     'Row count below which report endpoints return display_mode: chart. Operator-only.',
     'integer', false, false, 1, 100, NULL, 'reports', true, 50),

    -- CALENDAR CONFLICT AUTO-EXPIRY
    ('calendar_conflict_auto_expire_enabled', 'Calendar conflict auto-expiry enabled',
     'When ON, unresolved calendar sync conflicts are auto-resolved after the expiry period.',
     'boolean', true, false, NULL, NULL, NULL, 'sync', true, 10),

    ('calendar_conflict_auto_expire_days', 'Calendar conflict auto-expiry period (days)',
     'Days before an unresolved calendar conflict is auto-accepted (using Pilot version).',
     'integer', true, false, 1, 365, NULL, 'sync', true, 20),

    ('calendar_conflict_pre_warning_days', 'Calendar conflict pre-warning (days)',
     'Days before auto-expiry to send a pre-warning notification. Must be < auto_expire_days.',
     'integer', true, false, 1, 30, NULL, 'sync', true, 30),

    -- QUICKBOOKS CONFLICT AUTO-EXPIRY
    ('qb_auto_expire_days', 'QB conflict auto-expiry period (days)',
     'Days before a QB sync conflict is auto-resolved (when per-entity expiry is ON).',
     'integer', true, false, 1, 365, NULL, 'qb', true, 10),

    ('qb_pre_warning_days', 'QB conflict pre-warning (days)',
     'Days before QB conflict auto-expiry to send a pre-warning.',
     'integer', true, false, 1, 60, NULL, 'qb', true, 20),

    ('qb_auto_expire_customer_enabled', 'QB customer conflict auto-expiry enabled',
     'When ON, QB customer conflicts auto-resolve after the expiry period.',
     'boolean', true, false, NULL, NULL, NULL, 'qb', true, 30),

    ('qb_auto_expire_customer_direction', 'QB customer conflict auto-expiry direction',
     'Which version wins when a QB customer conflict auto-resolves.',
     'string', true, false, NULL, NULL, '["pilot","quickbooks"]', 'qb', true, 40),

    ('qb_auto_expire_quote_enabled', 'QB quote conflict auto-expiry enabled',
     'When ON, QB quote conflicts auto-resolve after the expiry period.',
     'boolean', true, false, NULL, NULL, NULL, 'qb', true, 50),

    ('qb_auto_expire_quote_direction', 'QB quote conflict auto-expiry direction',
     'Which version wins when a QB quote conflict auto-resolves.',
     'string', true, false, NULL, NULL, '["pilot","quickbooks"]', 'qb', true, 60),

    ('qb_auto_expire_invoice_enabled', 'QB invoice conflict auto-expiry enabled',
     'When ON, QB invoice conflicts auto-resolve after the expiry period.',
     'boolean', true, false, NULL, NULL, NULL, 'qb', true, 70),

    ('qb_auto_expire_invoice_direction', 'QB invoice conflict auto-expiry direction',
     'Which version wins when a QB invoice conflict auto-resolves.',
     'string', true, false, NULL, NULL, '["pilot","quickbooks"]', 'qb', true, 80),

    ('qb_auto_expire_expense_enabled', 'QB expense conflict auto-expiry enabled',
     'When ON, QB expense conflicts auto-resolve after the expiry period.',
     'boolean', true, false, NULL, NULL, NULL, 'qb', true, 90),

    ('qb_auto_expire_expense_direction', 'QB expense conflict auto-expiry direction',
     'Which version wins when a QB expense conflict auto-resolves.',
     'string', true, false, NULL, NULL, '["pilot","quickbooks"]', 'qb', true, 100),

    -- PHOTO UPLOAD & RETENTION
    ('photo_upload_wifi_only', 'Upload photos on WiFi only',
     'When ON, photo uploads are deferred until a WiFi connection is available.',
     'boolean', true, false, NULL, NULL, NULL, 'mobile', true, 10),

    ('photo_local_retention_days', 'Photo local retention (days)',
     'Days a synced photo remains on the device before auto-purge.',
     'integer', true, false, 1, 30, NULL, 'mobile', true, 20),

    -- OFFLINE OPERATIONS
    ('offline_hard_limit_hours', 'Offline hard limit (hours)',
     'Hours before the app blocks new offline captures. Operator-only: min 1, no unlimited.',
     'integer', false, false, 1, NULL, NULL, 'mobile', true, 30),

    ('voice_offline_audio_storage_limit_mb', 'Voice audio offline storage limit (MB)',
     'Maximum on-device storage for offline-captured voice audio. Operator-only.',
     'integer', false, false, 50, 2000, NULL, 'mobile', true, 40),

    -- BACKGROUND SYNC
    ('background_sync_enabled', 'Background sync enabled',
     'When ON, the server sends silent pushes to trigger background sync on mobile devices.',
     'boolean', true, true, NULL, NULL, NULL, 'sync', true, 40),

    ('background_sync_wifi_only', 'Background sync on WiFi only',
     'When ON, background sync only runs over WiFi (saves mobile data).',
     'boolean', true, false, NULL, NULL, NULL, 'sync', true, 50),

    ('background_sync_battery_floor_pct', 'Background sync battery floor (%)',
     'Background sync will not run if battery is below this percentage.',
     'integer', true, false, 5, 50, NULL, 'sync', true, 60),

    ('background_sync_push_interval_minutes', 'Background sync push interval (minutes)',
     'How often the server sends a silent push to trigger background sync.',
     'integer', true, false, 1, 60, NULL, 'sync', true, 70),

    -- SYNC INDICATOR
    ('tenant_sync_indicator_pending_amber_threshold', 'Sync indicator amber threshold (pending items)',
     'Number of pending sync items above which the sync indicator turns amber. Operator-only.',
     'integer', false, false, 1, 100, NULL, 'sync', true, 80),

    -- VOICE PERSONA
    ('voice_persona_tone', 'Voice AI persona tone',
     'The personality tone of the AI voice assistant. Conservative = formal/brief; Balanced = friendly/professional; Playful = casual/upbeat.',
     'string', true, true, NULL, NULL, '["conservative","balanced","playful"]', 'voice', true, 10),

    ('voice_persona_tone_user_override_allowed', 'Allow per-user voice persona override',
     'When ON, each team member can set their own voice AI tone. When OFF, all users use the team default.',
     'boolean', true, false, NULL, NULL, NULL, 'voice', true, 20),

    -- MFA POLICY
    ('tenant_mfa_required', 'Require MFA for all users',
     'When ON, all tenant users must enroll in MFA before they can access the platform.',
     'boolean', true, false, NULL, NULL, NULL, 'security', true, 10),

    ('tenant_mfa_grace_period_days', 'MFA grace period (days)',
     'Number of days users have to enroll in MFA after the requirement is enabled.',
     'integer', true, false, 1, 90, NULL, 'security', true, 20),

    -- SMS
    ('sms_quota_cap_policy', 'SMS quota cap policy',
     'soft = allow overages billed at $0.05/segment; hard = block sends when quota is reached.',
     'string', true, false, NULL, NULL, '["soft","hard"]', 'billing', true, 10),

    -- TECH COLOR PALETTE
    ('tech_color_palette', 'Tech color palette',
     'Custom color palette for dispatch board avatar assignment. NULL = use system default 12-hue palette.',
     'jsonb', true, false, NULL, NULL, NULL, 'reports', true, 60),

    -- TRIAL
    ('default_trial_length_days', 'Default trial length (days)',
     'Platform default trial length in days. Operator-only. Per-tenant overrides: tenant.trial_length_days_override > tenant_tier_override.override_trial_length_days.',
     'integer', false, false, 1, 365, NULL, 'trial', true, 10),

    -- SAFETY / GPS
    ('gps_variance_alert_threshold_meters', 'GPS variance alert threshold (meters)',
     'When a tech clocks in farther than this distance from the job site, an owner notification is enqueued. 0 = disabled.',
     'integer', true, false, 0, 50000, NULL, 'safety', true, 10);
    """)

    # ============================================================
    # Step 4: Seed platform_setting NULL rows (platform defaults)
    # ============================================================
    op.execute("""
    INSERT INTO platform_setting (key, value, tenant_id)
    VALUES
    -- QUOTES & APPROVAL
    ('require_approval_for_tech_quotes', 'true'::jsonb,          NULL),
    ('max_discount_pct_owner',           '15.0'::jsonb,          NULL),
    ('default_quote_validity_days',      '30'::jsonb,            NULL),
    ('default_invoice_terms_days',       '0'::jsonb,             NULL),

    -- LABOR & COST
    ('default_labor_rate_cents',         '8500'::jsonb,          NULL),
    ('default_billable_labor_rate_cents','15000'::jsonb,         NULL),

    -- ETC VARIANCE
    ('etc_variance_owner_notify_pct',    '50'::jsonb,            NULL),
    ('etc_variance_note_required_pct',   '10'::jsonb,            NULL),

    -- PROFITABILITY
    ('margin_target_pct',                '20'::jsonb,            NULL),
    ('margin_bucket_boundaries',         '[10, 20, 30]'::jsonb,  NULL),
    ('report_chart_threshold',           '8'::jsonb,             NULL),

    -- CALENDAR
    ('calendar_conflict_auto_expire_enabled', 'true'::jsonb,     NULL),
    ('calendar_conflict_auto_expire_days',    '60'::jsonb,       NULL),
    ('calendar_conflict_pre_warning_days',    '14'::jsonb,       NULL),

    -- QUICKBOOKS
    ('qb_auto_expire_days',                    '60'::jsonb,      NULL),
    ('qb_pre_warning_days',                    '14'::jsonb,      NULL),
    ('qb_auto_expire_customer_enabled',        'false'::jsonb,   NULL),
    ('qb_auto_expire_customer_direction',      'null'::jsonb,    NULL),
    ('qb_auto_expire_quote_enabled',           'false'::jsonb,   NULL),
    ('qb_auto_expire_quote_direction',         'null'::jsonb,    NULL),
    ('qb_auto_expire_invoice_enabled',         'false'::jsonb,   NULL),
    ('qb_auto_expire_invoice_direction',       'null'::jsonb,    NULL),
    ('qb_auto_expire_expense_enabled',         'false'::jsonb,   NULL),
    ('qb_auto_expire_expense_direction',       'null'::jsonb,    NULL),

    -- PHOTO
    ('photo_upload_wifi_only',           'true'::jsonb,          NULL),
    ('photo_local_retention_days',       '7'::jsonb,             NULL),

    -- OFFLINE
    ('offline_hard_limit_hours',         '72'::jsonb,            NULL),
    ('voice_offline_audio_storage_limit_mb', '500'::jsonb,       NULL),

    -- BACKGROUND SYNC
    ('background_sync_enabled',          'true'::jsonb,          NULL),
    ('background_sync_wifi_only',        'false'::jsonb,         NULL),
    ('background_sync_battery_floor_pct','20'::jsonb,            NULL),
    ('background_sync_push_interval_minutes', '5'::jsonb,        NULL),

    -- SYNC INDICATOR
    ('tenant_sync_indicator_pending_amber_threshold', '5'::jsonb, NULL),

    -- VOICE
    ('voice_persona_tone',               '"balanced"'::jsonb,    NULL),
    ('voice_persona_tone_user_override_allowed', 'true'::jsonb,  NULL),

    -- MFA
    ('tenant_mfa_required',              'false'::jsonb,         NULL),
    ('tenant_mfa_grace_period_days',     '7'::jsonb,             NULL),

    -- SMS
    ('sms_quota_cap_policy',             '"soft"'::jsonb,        NULL),

    -- TECH COLOR PALETTE (null = use system default palette)
    ('tech_color_palette',               'null'::jsonb,          NULL),

    -- TRIAL
    ('default_trial_length_days',        '14'::jsonb,            NULL),

    -- SAFETY / GPS
    ('gps_variance_alert_threshold_meters', '500'::jsonb,        NULL);
    """)

    # ============================================================
    # Step 5: Add mfa_grace_period_started_at to tenant table
    # (must happen BEFORE dropping tenant_settings)
    # ============================================================
    op.add_column(
        "tenant",
        sa.Column(
            "mfa_grace_period_started_at", sa.DateTime(timezone=True), nullable=True
        ),
    )

    # Migrate existing timestamp from tenant_settings → tenant
    op.execute("""
    UPDATE tenant t
    SET mfa_grace_period_started_at = ts.tenant_mfa_required_grace_period_starts_at
    FROM tenant_settings ts
    WHERE t.id = ts.tenant_id
      AND ts.tenant_mfa_required_grace_period_starts_at IS NOT NULL;
    """)

    # ============================================================
    # Step 6: Migrate existing tenant overrides from tenant_settings
    # ============================================================
    # Boolean NOT NULL columns: only migrate if value differs from platform default
    # Nullable columns: only migrate if NOT NULL (explicit override)

    # require_approval_for_tech_quotes (default: true)
    op.execute("""
    INSERT INTO platform_setting (key, value, tenant_id)
    SELECT 'require_approval_for_tech_quotes',
           to_jsonb(require_approval_for_tech_quotes),
           tenant_id
    FROM tenant_settings
    WHERE require_approval_for_tech_quotes IS DISTINCT FROM true
    ON CONFLICT (key, tenant_id) DO NOTHING;
    """)

    # max_discount_pct_owner (default: 15.00)
    op.execute("""
    INSERT INTO platform_setting (key, value, tenant_id)
    SELECT 'max_discount_pct_owner',
           to_jsonb(max_discount_pct_owner::float),
           tenant_id
    FROM tenant_settings
    WHERE max_discount_pct_owner IS DISTINCT FROM 15.00
    ON CONFLICT (key, tenant_id) DO NOTHING;
    """)

    # default_quote_validity_days (default: 30)
    op.execute("""
    INSERT INTO platform_setting (key, value, tenant_id)
    SELECT 'default_quote_validity_days',
           to_jsonb(default_quote_validity_days),
           tenant_id
    FROM tenant_settings
    WHERE default_quote_validity_days IS DISTINCT FROM 30
    ON CONFLICT (key, tenant_id) DO NOTHING;
    """)

    # default_invoice_terms_days (default: 0)
    op.execute("""
    INSERT INTO platform_setting (key, value, tenant_id)
    SELECT 'default_invoice_terms_days',
           to_jsonb(default_invoice_terms_days),
           tenant_id
    FROM tenant_settings
    WHERE default_invoice_terms_days IS DISTINCT FROM 0
    ON CONFLICT (key, tenant_id) DO NOTHING;
    """)

    # default_labor_rate_cents (default: 8500)
    op.execute("""
    INSERT INTO platform_setting (key, value, tenant_id)
    SELECT 'default_labor_rate_cents',
           to_jsonb(default_labor_rate_cents),
           tenant_id
    FROM tenant_settings
    WHERE default_labor_rate_cents IS DISTINCT FROM 8500
    ON CONFLICT (key, tenant_id) DO NOTHING;
    """)

    # default_billable_labor_rate_cents (default: 15000)
    op.execute("""
    INSERT INTO platform_setting (key, value, tenant_id)
    SELECT 'default_billable_labor_rate_cents',
           to_jsonb(default_billable_labor_rate_cents),
           tenant_id
    FROM tenant_settings
    WHERE default_billable_labor_rate_cents IS DISTINCT FROM 15000
    ON CONFLICT (key, tenant_id) DO NOTHING;
    """)

    # etc_variance_owner_notify_pct (default: 50)
    op.execute("""
    INSERT INTO platform_setting (key, value, tenant_id)
    SELECT 'etc_variance_owner_notify_pct',
           to_jsonb(etc_variance_owner_notify_pct),
           tenant_id
    FROM tenant_settings
    WHERE etc_variance_owner_notify_pct IS DISTINCT FROM 50
    ON CONFLICT (key, tenant_id) DO NOTHING;
    """)

    # etc_variance_note_required_pct (default: 10)
    op.execute("""
    INSERT INTO platform_setting (key, value, tenant_id)
    SELECT 'etc_variance_note_required_pct',
           to_jsonb(etc_variance_note_required_pct),
           tenant_id
    FROM tenant_settings
    WHERE etc_variance_note_required_pct IS DISTINCT FROM 10
    ON CONFLICT (key, tenant_id) DO NOTHING;
    """)

    # margin_target_pct (default: 20)
    op.execute("""
    INSERT INTO platform_setting (key, value, tenant_id)
    SELECT 'margin_target_pct',
           to_jsonb(margin_target_pct),
           tenant_id
    FROM tenant_settings
    WHERE margin_target_pct IS DISTINCT FROM 20
    ON CONFLICT (key, tenant_id) DO NOTHING;
    """)

    # margin_bucket_boundaries (default: [10,20,30]) — nullable JSONB
    op.execute("""
    INSERT INTO platform_setting (key, value, tenant_id)
    SELECT 'margin_bucket_boundaries',
           margin_bucket_boundaries,
           tenant_id
    FROM tenant_settings
    WHERE margin_bucket_boundaries IS NOT NULL
      AND margin_bucket_boundaries IS DISTINCT FROM '[10, 20, 30]'::jsonb
    ON CONFLICT (key, tenant_id) DO NOTHING;
    """)

    # report_chart_threshold (default: 8)
    op.execute("""
    INSERT INTO platform_setting (key, value, tenant_id)
    SELECT 'report_chart_threshold',
           to_jsonb(report_chart_threshold),
           tenant_id
    FROM tenant_settings
    WHERE report_chart_threshold IS DISTINCT FROM 8
    ON CONFLICT (key, tenant_id) DO NOTHING;
    """)

    # calendar_conflict_auto_expire_enabled (default: true)
    op.execute("""
    INSERT INTO platform_setting (key, value, tenant_id)
    SELECT 'calendar_conflict_auto_expire_enabled',
           to_jsonb(calendar_conflict_auto_expire_enabled),
           tenant_id
    FROM tenant_settings
    WHERE calendar_conflict_auto_expire_enabled IS DISTINCT FROM true
    ON CONFLICT (key, tenant_id) DO NOTHING;
    """)

    # calendar_conflict_auto_expire_days (nullable — migrate if NOT NULL)
    op.execute("""
    INSERT INTO platform_setting (key, value, tenant_id)
    SELECT 'calendar_conflict_auto_expire_days',
           to_jsonb(calendar_conflict_auto_expire_days),
           tenant_id
    FROM tenant_settings
    WHERE calendar_conflict_auto_expire_days IS NOT NULL
    ON CONFLICT (key, tenant_id) DO NOTHING;
    """)

    # calendar_conflict_pre_warning_days (nullable — migrate if NOT NULL)
    op.execute("""
    INSERT INTO platform_setting (key, value, tenant_id)
    SELECT 'calendar_conflict_pre_warning_days',
           to_jsonb(calendar_conflict_pre_warning_days),
           tenant_id
    FROM tenant_settings
    WHERE calendar_conflict_pre_warning_days IS NOT NULL
    ON CONFLICT (key, tenant_id) DO NOTHING;
    """)

    # qb_auto_expire_days (nullable)
    op.execute("""
    INSERT INTO platform_setting (key, value, tenant_id)
    SELECT 'qb_auto_expire_days',
           to_jsonb(qb_auto_expire_days),
           tenant_id
    FROM tenant_settings
    WHERE qb_auto_expire_days IS NOT NULL
    ON CONFLICT (key, tenant_id) DO NOTHING;
    """)

    # qb_pre_warning_days (nullable)
    op.execute("""
    INSERT INTO platform_setting (key, value, tenant_id)
    SELECT 'qb_pre_warning_days',
           to_jsonb(qb_pre_warning_days),
           tenant_id
    FROM tenant_settings
    WHERE qb_pre_warning_days IS NOT NULL
    ON CONFLICT (key, tenant_id) DO NOTHING;
    """)

    # qb_auto_expire_customer_enabled (default: false)
    op.execute("""
    INSERT INTO platform_setting (key, value, tenant_id)
    SELECT 'qb_auto_expire_customer_enabled',
           to_jsonb(qb_auto_expire_customer_enabled),
           tenant_id
    FROM tenant_settings
    WHERE qb_auto_expire_customer_enabled IS DISTINCT FROM false
    ON CONFLICT (key, tenant_id) DO NOTHING;
    """)

    # qb_auto_expire_customer_direction (nullable string)
    op.execute("""
    INSERT INTO platform_setting (key, value, tenant_id)
    SELECT 'qb_auto_expire_customer_direction',
           to_jsonb(qb_auto_expire_customer_direction),
           tenant_id
    FROM tenant_settings
    WHERE qb_auto_expire_customer_direction IS NOT NULL
    ON CONFLICT (key, tenant_id) DO NOTHING;
    """)

    # qb_auto_expire_quote_enabled (default: false)
    op.execute("""
    INSERT INTO platform_setting (key, value, tenant_id)
    SELECT 'qb_auto_expire_quote_enabled',
           to_jsonb(qb_auto_expire_quote_enabled),
           tenant_id
    FROM tenant_settings
    WHERE qb_auto_expire_quote_enabled IS DISTINCT FROM false
    ON CONFLICT (key, tenant_id) DO NOTHING;
    """)

    # qb_auto_expire_quote_direction (nullable)
    op.execute("""
    INSERT INTO platform_setting (key, value, tenant_id)
    SELECT 'qb_auto_expire_quote_direction',
           to_jsonb(qb_auto_expire_quote_direction),
           tenant_id
    FROM tenant_settings
    WHERE qb_auto_expire_quote_direction IS NOT NULL
    ON CONFLICT (key, tenant_id) DO NOTHING;
    """)

    # qb_auto_expire_invoice_enabled (default: false)
    op.execute("""
    INSERT INTO platform_setting (key, value, tenant_id)
    SELECT 'qb_auto_expire_invoice_enabled',
           to_jsonb(qb_auto_expire_invoice_enabled),
           tenant_id
    FROM tenant_settings
    WHERE qb_auto_expire_invoice_enabled IS DISTINCT FROM false
    ON CONFLICT (key, tenant_id) DO NOTHING;
    """)

    # qb_auto_expire_invoice_direction (nullable)
    op.execute("""
    INSERT INTO platform_setting (key, value, tenant_id)
    SELECT 'qb_auto_expire_invoice_direction',
           to_jsonb(qb_auto_expire_invoice_direction),
           tenant_id
    FROM tenant_settings
    WHERE qb_auto_expire_invoice_direction IS NOT NULL
    ON CONFLICT (key, tenant_id) DO NOTHING;
    """)

    # qb_auto_expire_expense_enabled (default: false)
    op.execute("""
    INSERT INTO platform_setting (key, value, tenant_id)
    SELECT 'qb_auto_expire_expense_enabled',
           to_jsonb(qb_auto_expire_expense_enabled),
           tenant_id
    FROM tenant_settings
    WHERE qb_auto_expire_expense_enabled IS DISTINCT FROM false
    ON CONFLICT (key, tenant_id) DO NOTHING;
    """)

    # qb_auto_expire_expense_direction (nullable)
    op.execute("""
    INSERT INTO platform_setting (key, value, tenant_id)
    SELECT 'qb_auto_expire_expense_direction',
           to_jsonb(qb_auto_expire_expense_direction),
           tenant_id
    FROM tenant_settings
    WHERE qb_auto_expire_expense_direction IS NOT NULL
    ON CONFLICT (key, tenant_id) DO NOTHING;
    """)

    # photo_upload_wifi_only (default: true)
    op.execute("""
    INSERT INTO platform_setting (key, value, tenant_id)
    SELECT 'photo_upload_wifi_only',
           to_jsonb(photo_upload_wifi_only),
           tenant_id
    FROM tenant_settings
    WHERE photo_upload_wifi_only IS DISTINCT FROM true
    ON CONFLICT (key, tenant_id) DO NOTHING;
    """)

    # photo_local_retention_days (default: 7)
    op.execute("""
    INSERT INTO platform_setting (key, value, tenant_id)
    SELECT 'photo_local_retention_days',
           to_jsonb(photo_local_retention_days),
           tenant_id
    FROM tenant_settings
    WHERE photo_local_retention_days IS DISTINCT FROM 7
    ON CONFLICT (key, tenant_id) DO NOTHING;
    """)

    # offline_hard_limit_hours (nullable)
    op.execute("""
    INSERT INTO platform_setting (key, value, tenant_id)
    SELECT 'offline_hard_limit_hours',
           to_jsonb(offline_hard_limit_hours),
           tenant_id
    FROM tenant_settings
    WHERE offline_hard_limit_hours IS NOT NULL
      AND offline_hard_limit_hours IS DISTINCT FROM 72
    ON CONFLICT (key, tenant_id) DO NOTHING;
    """)

    # voice_offline_audio_storage_limit_mb (default: 500)
    op.execute("""
    INSERT INTO platform_setting (key, value, tenant_id)
    SELECT 'voice_offline_audio_storage_limit_mb',
           to_jsonb(voice_offline_audio_storage_limit_mb),
           tenant_id
    FROM tenant_settings
    WHERE voice_offline_audio_storage_limit_mb IS DISTINCT FROM 500
    ON CONFLICT (key, tenant_id) DO NOTHING;
    """)

    # background_sync_enabled (default: true)
    op.execute("""
    INSERT INTO platform_setting (key, value, tenant_id)
    SELECT 'background_sync_enabled',
           to_jsonb(background_sync_enabled),
           tenant_id
    FROM tenant_settings
    WHERE background_sync_enabled IS DISTINCT FROM true
    ON CONFLICT (key, tenant_id) DO NOTHING;
    """)

    # background_sync_wifi_only (default: false)
    op.execute("""
    INSERT INTO platform_setting (key, value, tenant_id)
    SELECT 'background_sync_wifi_only',
           to_jsonb(background_sync_wifi_only),
           tenant_id
    FROM tenant_settings
    WHERE background_sync_wifi_only IS DISTINCT FROM false
    ON CONFLICT (key, tenant_id) DO NOTHING;
    """)

    # background_sync_battery_floor_pct (default: 20)
    op.execute("""
    INSERT INTO platform_setting (key, value, tenant_id)
    SELECT 'background_sync_battery_floor_pct',
           to_jsonb(background_sync_battery_floor_pct),
           tenant_id
    FROM tenant_settings
    WHERE background_sync_battery_floor_pct IS DISTINCT FROM 20
    ON CONFLICT (key, tenant_id) DO NOTHING;
    """)

    # background_sync_push_interval_minutes (nullable)
    op.execute("""
    INSERT INTO platform_setting (key, value, tenant_id)
    SELECT 'background_sync_push_interval_minutes',
           to_jsonb(background_sync_push_interval_minutes),
           tenant_id
    FROM tenant_settings
    WHERE background_sync_push_interval_minutes IS NOT NULL
    ON CONFLICT (key, tenant_id) DO NOTHING;
    """)

    # tenant_sync_indicator_pending_amber_threshold (default: 5)
    op.execute("""
    INSERT INTO platform_setting (key, value, tenant_id)
    SELECT 'tenant_sync_indicator_pending_amber_threshold',
           to_jsonb(tenant_sync_indicator_pending_amber_threshold),
           tenant_id
    FROM tenant_settings
    WHERE tenant_sync_indicator_pending_amber_threshold IS DISTINCT FROM 5
    ON CONFLICT (key, tenant_id) DO NOTHING;
    """)

    # voice_persona_tone (nullable string)
    op.execute("""
    INSERT INTO platform_setting (key, value, tenant_id)
    SELECT 'voice_persona_tone',
           to_jsonb(voice_persona_tone),
           tenant_id
    FROM tenant_settings
    WHERE voice_persona_tone IS NOT NULL
    ON CONFLICT (key, tenant_id) DO NOTHING;
    """)

    # voice_persona_tone_user_override_allowed (default: true)
    op.execute("""
    INSERT INTO platform_setting (key, value, tenant_id)
    SELECT 'voice_persona_tone_user_override_allowed',
           to_jsonb(voice_persona_tone_user_override_allowed),
           tenant_id
    FROM tenant_settings
    WHERE voice_persona_tone_user_override_allowed IS DISTINCT FROM true
    ON CONFLICT (key, tenant_id) DO NOTHING;
    """)

    # tenant_mfa_required (default: false)
    op.execute("""
    INSERT INTO platform_setting (key, value, tenant_id)
    SELECT 'tenant_mfa_required',
           to_jsonb(tenant_mfa_required),
           tenant_id
    FROM tenant_settings
    WHERE tenant_mfa_required IS DISTINCT FROM false
    ON CONFLICT (key, tenant_id) DO NOTHING;
    """)

    # tenant_mfa_grace_period_days (default: 7)
    op.execute("""
    INSERT INTO platform_setting (key, value, tenant_id)
    SELECT 'tenant_mfa_grace_period_days',
           to_jsonb(tenant_mfa_grace_period_days),
           tenant_id
    FROM tenant_settings
    WHERE tenant_mfa_grace_period_days IS DISTINCT FROM 7
    ON CONFLICT (key, tenant_id) DO NOTHING;
    """)

    # tech_color_palette (nullable JSONB)
    op.execute("""
    INSERT INTO platform_setting (key, value, tenant_id)
    SELECT 'tech_color_palette',
           tech_color_palette,
           tenant_id
    FROM tenant_settings
    WHERE tech_color_palette IS NOT NULL
    ON CONFLICT (key, tenant_id) DO NOTHING;
    """)

    # ============================================================
    # Step 7: Drop tenant_settings CASCADE
    # ============================================================
    op.execute("DROP TABLE tenant_settings CASCADE;")


def downgrade() -> None:
    # Re-create tenant_settings (schema only — data is not restored)
    op.create_table(
        "tenant_settings",
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenant.id"),
            nullable=False,
        ),
        sa.Column(
            "default_labor_rate_cents",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("8500"),
        ),
        sa.Column(
            "default_billable_labor_rate_cents",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("15000"),
        ),
        sa.Column(
            "default_quote_validity_days",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("30"),
        ),
        sa.Column(
            "default_invoice_terms_days",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "require_approval_for_tech_quotes",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "max_discount_pct_owner",
            sa.Numeric(5, 2),
            nullable=False,
            server_default=sa.text("15.00"),
        ),
        sa.Column("tech_color_palette", postgresql.JSONB(), nullable=True),
        sa.Column(
            "report_chart_threshold",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("8"),
        ),
        sa.Column(
            "etc_variance_owner_notify_pct",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("50"),
        ),
        sa.Column(
            "etc_variance_note_required_pct",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("10"),
        ),
        sa.Column(
            "margin_bucket_boundaries",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[10, 20, 30]'::jsonb"),
        ),
        sa.Column(
            "margin_target_pct",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("20"),
        ),
        sa.Column(
            "calendar_conflict_auto_expire_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column("calendar_conflict_auto_expire_days", sa.Integer(), nullable=True),
        sa.Column("calendar_conflict_pre_warning_days", sa.Integer(), nullable=True),
        sa.Column(
            "photo_upload_wifi_only",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "photo_local_retention_days",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("7"),
        ),
        sa.Column("offline_hard_limit_hours", sa.Integer(), nullable=True),
        sa.Column(
            "voice_offline_audio_storage_limit_mb",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("500"),
        ),
        sa.Column(
            "qb_auto_expire_customer_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("qb_auto_expire_customer_direction", sa.String(), nullable=True),
        sa.Column(
            "qb_auto_expire_quote_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("qb_auto_expire_quote_direction", sa.String(), nullable=True),
        sa.Column(
            "qb_auto_expire_invoice_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("qb_auto_expire_invoice_direction", sa.String(), nullable=True),
        sa.Column(
            "qb_auto_expire_expense_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("qb_auto_expire_expense_direction", sa.String(), nullable=True),
        sa.Column("qb_auto_expire_days", sa.Integer(), nullable=True),
        sa.Column("qb_pre_warning_days", sa.Integer(), nullable=True),
        sa.Column(
            "background_sync_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "background_sync_wifi_only",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "background_sync_battery_floor_pct",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("20"),
        ),
        sa.Column("background_sync_push_interval_minutes", sa.Integer(), nullable=True),
        sa.Column("voice_persona_tone", sa.String(), nullable=True),
        sa.Column(
            "voice_persona_tone_user_override_allowed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "tenant_mfa_required",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "tenant_mfa_required_grace_period_starts_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "tenant_mfa_grace_period_days",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("7"),
        ),
        sa.Column(
            "tenant_sync_indicator_pending_amber_threshold",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("5"),
        ),
        sa.PrimaryKeyConstraint("tenant_id"),
    )

    # Remove mfa_grace_period_started_at from tenant table
    op.drop_column("tenant", "mfa_grace_period_started_at")

    # Drop new tables
    op.execute("DROP TABLE IF EXISTS platform_setting CASCADE;")
    op.execute("DROP TABLE IF EXISTS platform_setting_catalog CASCADE;")
