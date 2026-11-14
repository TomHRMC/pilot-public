"""phase_fe_1_batch_b10_notification_category_registry

Revision ID: 3c02a7d21470
Revises: c9cf97fd02cf
Create Date: 2026-05-02 14:55:28

Scope (A56):
  - CREATE TABLE notification_category (8-row seed)
  - CREATE TABLE notification_category_sub_trigger (4 forced-minimum rows seeded)
  - CREATE TABLE notification_default_policy (24 system-default rows seeded)
  - ADD COLUMNS notification_outbox.category_id, sub_trigger_id, recipient_user_id_originating
    using 3-part nullable-backfill-lock pattern for category_id (→ NOT NULL)
  - All standard 3-trigger sets (audit + immutable + updated_at)

Note: Seed INSERTs are performed BEFORE adding the audit trigger on lookup tables
because audit.log_changes() extracts entity_id from NEW.id which is NULL for
tables using non-uuid PKs (category_id, sub_trigger_id). The trigger is attached
after seeding so that future DML is audited correctly.
"""

from alembic import op

# revision identifiers
revision = "3c02a7d21470"
down_revision = "c9cf97fd02cf"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Set audit context so triggers have a user_id
    op.execute("SET LOCAL app.user_id = '00000000-0000-0000-0000-000000000000'")

    # ──────────────────────────────────────────────────────────────
    # 1. CREATE TABLE notification_category
    # ──────────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE notification_category (
            created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
            created_by        UUID REFERENCES "user"(id) ON DELETE RESTRICT,
            updated_by        UUID REFERENCES "user"(id) ON DELETE RESTRICT,
            category_id       TEXT NOT NULL,
            display_label     TEXT NOT NULL,
            description       TEXT NOT NULL,
            category_group_id TEXT,
            display_order     INTEGER NOT NULL,
            CONSTRAINT pk_notification_category PRIMARY KEY (category_id)
        )
    """)

    # Seed BEFORE adding audit trigger (audit.log_changes needs an 'id' column
    # for entity_id; these lookup tables use category_id as PK instead)
    op.execute("""
        INSERT INTO notification_category (category_id, display_label, description, display_order)
        VALUES
            ('quote_approvals',        'Quote Approvals',        'Notifications when quotes are submitted, approved, or rejected.',                 1),
            ('field_issues',           'Field Issues',           'Notifications for field escalations and mobile sync conflicts.',                   2),
            ('sync_conflicts',         'Sync Conflicts',         'Notifications for QuickBooks and calendar sync conflicts requiring attention.',    3),
            ('job_activity',           'Job Activity',           'Notifications for job assignments, updates, and status changes.',                 4),
            ('customer_activity',      'Customer Activity',      'Notifications for customer communications and inbound messages.',                 5),
            ('billing',                'Billing',                'Notifications for invoice activity, payments, and subscription changes.',         6),
            ('background_sync_alerts', 'Background Sync Alerts', 'Notifications for background synchronization status and errors.',                 7),
            ('system_announcements',   'System Announcements',   'Platform announcements and critical system notifications.',                       8)
    """)

    # Add triggers AFTER seeding
    op.execute("""
        CREATE TRIGGER audit_notification_category_changes
        AFTER INSERT OR DELETE OR UPDATE ON public.notification_category
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes()
    """)
    op.execute("""
        CREATE TRIGGER trg_notification_category_guard_created_immutable
        BEFORE UPDATE ON public.notification_category
        FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable()
    """)
    op.execute("""
        CREATE TRIGGER trg_notification_category_set_updated_at
        BEFORE UPDATE ON public.notification_category
        FOR EACH ROW EXECUTE FUNCTION public.set_updated_at()
    """)

    # ──────────────────────────────────────────────────────────────
    # 2. CREATE TABLE notification_category_sub_trigger
    # ──────────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE notification_category_sub_trigger (
            created_at                         TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at                         TIMESTAMPTZ NOT NULL DEFAULT now(),
            created_by                         UUID REFERENCES "user"(id) ON DELETE RESTRICT,
            updated_by                         UUID REFERENCES "user"(id) ON DELETE RESTRICT,
            sub_trigger_id                     TEXT NOT NULL,
            category_id                        TEXT NOT NULL,
            display_label                      TEXT,
            forced_minimum_push_uniform        BOOLEAN NOT NULL DEFAULT FALSE,
            forced_minimum_push_recipient_only BOOLEAN DEFAULT FALSE,
            CONSTRAINT pk_notif_sub_trigger PRIMARY KEY (sub_trigger_id),
            CONSTRAINT fk_notif_sub_trigger_category
                FOREIGN KEY (category_id)
                REFERENCES notification_category(category_id)
                ON DELETE RESTRICT
        )
    """)

    op.execute("""
        CREATE INDEX ix_notif_sub_trigger_category_id
        ON notification_category_sub_trigger (category_id)
    """)

    # Seed BEFORE audit trigger
    op.execute("""
        INSERT INTO notification_category_sub_trigger
            (sub_trigger_id, category_id, display_label, forced_minimum_push_uniform, forced_minimum_push_recipient_only)
        VALUES
            ('field_issues.all',                    'field_issues',        'All Field Issues',       TRUE,  FALSE),
            ('job_activity.assignment',              'job_activity',        'Job Assignment',         FALSE, TRUE),
            ('system_announcements.critical',        'system_announcements','Critical Announcements', TRUE,  FALSE),
            ('customer_activity.inbound_sms_reply',  'customer_activity',   'Inbound SMS Reply',      FALSE, TRUE)
    """)

    # Add triggers AFTER seeding
    op.execute("""
        CREATE TRIGGER audit_notification_category_sub_trigger_changes
        AFTER INSERT OR DELETE OR UPDATE ON public.notification_category_sub_trigger
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes()
    """)
    op.execute("""
        CREATE TRIGGER trg_notification_category_sub_trigger_guard_created_immutable
        BEFORE UPDATE ON public.notification_category_sub_trigger
        FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable()
    """)
    op.execute("""
        CREATE TRIGGER trg_notification_category_sub_trigger_set_updated_at
        BEFORE UPDATE ON public.notification_category_sub_trigger
        FOR EACH ROW EXECUTE FUNCTION public.set_updated_at()
    """)

    # ──────────────────────────────────────────────────────────────
    # 3. CREATE TABLE notification_default_policy
    # ──────────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE notification_default_policy (
            created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
            created_by  UUID REFERENCES "user"(id) ON DELETE RESTRICT,
            updated_by  UUID REFERENCES "user"(id) ON DELETE RESTRICT,
            id          UUID NOT NULL DEFAULT gen_random_uuid(),
            tenant_id   UUID REFERENCES tenant(id) ON DELETE RESTRICT,
            category_id TEXT NOT NULL,
            channel     TEXT NOT NULL,
            enabled     BOOLEAN NOT NULL,
            CONSTRAINT pk_notification_default_policy PRIMARY KEY (id),
            CONSTRAINT fk_notif_default_policy_category
                FOREIGN KEY (category_id)
                REFERENCES notification_category(category_id)
                ON DELETE RESTRICT,
            CONSTRAINT chk_notif_default_policy_channel
                CHECK (channel IN ('push', 'email', 'in_app'))
        )
    """)

    op.execute("""
        CREATE INDEX ix_notif_default_policy_tenant_id
        ON notification_default_policy (tenant_id)
    """)

    # Partial unique indexes (NULL != NULL in standard UNIQUE)
    op.execute("""
        CREATE UNIQUE INDEX uq_notif_default_policy_system
        ON notification_default_policy (category_id, channel)
        WHERE tenant_id IS NULL
    """)
    op.execute("""
        CREATE UNIQUE INDEX uq_notif_default_policy_tenant
        ON notification_default_policy (tenant_id, category_id, channel)
        WHERE tenant_id IS NOT NULL
    """)

    # Seed 24 system-default rows (tenant_id = NULL) BEFORE audit trigger
    # Matrix: quote_approvals=ON/ON/ON, field_issues=ON/ON/ON, sync_conflicts=OFF/ON/ON,
    #         job_activity=ON/OFF/ON, customer_activity=ON/OFF/ON, billing=OFF/ON/ON,
    #         background_sync_alerts=ON/OFF/ON, system_announcements=OFF/ON/ON
    op.execute("""
        INSERT INTO notification_default_policy (category_id, channel, enabled)
        VALUES
            ('quote_approvals',        'push',   TRUE),
            ('quote_approvals',        'email',  TRUE),
            ('quote_approvals',        'in_app', TRUE),
            ('field_issues',           'push',   TRUE),
            ('field_issues',           'email',  TRUE),
            ('field_issues',           'in_app', TRUE),
            ('sync_conflicts',         'push',   FALSE),
            ('sync_conflicts',         'email',  TRUE),
            ('sync_conflicts',         'in_app', TRUE),
            ('job_activity',           'push',   TRUE),
            ('job_activity',           'email',  FALSE),
            ('job_activity',           'in_app', TRUE),
            ('customer_activity',      'push',   TRUE),
            ('customer_activity',      'email',  FALSE),
            ('customer_activity',      'in_app', TRUE),
            ('billing',                'push',   FALSE),
            ('billing',                'email',  TRUE),
            ('billing',                'in_app', TRUE),
            ('background_sync_alerts', 'push',   TRUE),
            ('background_sync_alerts', 'email',  FALSE),
            ('background_sync_alerts', 'in_app', TRUE),
            ('system_announcements',   'push',   FALSE),
            ('system_announcements',   'email',  TRUE),
            ('system_announcements',   'in_app', TRUE)
    """)

    # Add triggers AFTER seeding
    op.execute("""
        CREATE TRIGGER audit_notification_default_policy_changes
        AFTER INSERT OR DELETE OR UPDATE ON public.notification_default_policy
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes()
    """)
    op.execute("""
        CREATE TRIGGER trg_notification_default_policy_guard_created_immutable
        BEFORE UPDATE ON public.notification_default_policy
        FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable()
    """)
    op.execute("""
        CREATE TRIGGER trg_notification_default_policy_set_updated_at
        BEFORE UPDATE ON public.notification_default_policy
        FOR EACH ROW EXECUTE FUNCTION public.set_updated_at()
    """)

    # ──────────────────────────────────────────────────────────────
    # 4. Extend notification_outbox (3-part nullable-backfill-lock)
    # ──────────────────────────────────────────────────────────────

    # Part 1: Add as NULLABLE
    op.execute("""
        ALTER TABLE notification_outbox
        ADD COLUMN category_id TEXT NULL,
        ADD COLUMN sub_trigger_id TEXT NULL,
        ADD COLUMN recipient_user_id_originating UUID NULL
    """)

    # Part 2: Backfill existing rows with sentinel 'system_announcements'
    op.execute("""
        UPDATE notification_outbox
        SET category_id = 'system_announcements'
        WHERE category_id IS NULL
    """)

    # Verify zero NULLs before locking
    op.execute("""
        DO $$
        DECLARE null_count INTEGER;
        BEGIN
            SELECT COUNT(*) INTO null_count
            FROM notification_outbox
            WHERE category_id IS NULL;
            IF null_count > 0 THEN
                RAISE EXCEPTION 'Backfill failed: % rows still have NULL category_id', null_count;
            END IF;
        END $$
    """)

    # Part 3: Lock to NOT NULL
    op.execute("""
        ALTER TABLE notification_outbox
        ALTER COLUMN category_id SET NOT NULL
    """)

    # Add FK constraints and indexes AFTER NOT NULL lock
    op.execute("""
        ALTER TABLE notification_outbox
        ADD CONSTRAINT fk_notif_outbox_category
            FOREIGN KEY (category_id)
            REFERENCES notification_category(category_id)
    """)
    op.execute("""
        ALTER TABLE notification_outbox
        ADD CONSTRAINT fk_notif_outbox_sub_trigger
            FOREIGN KEY (sub_trigger_id)
            REFERENCES notification_category_sub_trigger(sub_trigger_id)
    """)
    op.execute("""
        CREATE INDEX ix_notif_outbox_category_id
        ON notification_outbox (category_id)
    """)
    op.execute("""
        CREATE INDEX ix_notif_outbox_sub_trigger_id
        ON notification_outbox (sub_trigger_id)
        WHERE sub_trigger_id IS NOT NULL
    """)

    # Seed RBAC permissions for notification preferences (B10)
    op.execute("""
        UPDATE platform_role
        SET permissions = permissions || '["notification_preference.tenant_default.edit", "notification_preference.user_override.edit"]'::jsonb
        WHERE code = 'owner'
          AND NOT (permissions @> '["notification_preference.user_override.edit"]'::jsonb)
    """)
    op.execute("""
        UPDATE platform_role
        SET permissions = permissions || '["notification_preference.user_override.edit"]'::jsonb
        WHERE code IN ('technician', 'accountant', 'office_staff')
          AND NOT (permissions @> '["notification_preference.user_override.edit"]'::jsonb)
    """)


def downgrade() -> None:
    op.execute("SET LOCAL app.user_id = '00000000-0000-0000-0000-000000000000'")

    # Remove notification_outbox column extensions
    op.execute("DROP INDEX IF EXISTS ix_notif_outbox_sub_trigger_id")
    op.execute("DROP INDEX IF EXISTS ix_notif_outbox_category_id")
    op.execute("""
        ALTER TABLE notification_outbox
        DROP CONSTRAINT IF EXISTS fk_notif_outbox_sub_trigger,
        DROP CONSTRAINT IF EXISTS fk_notif_outbox_category,
        DROP COLUMN IF EXISTS recipient_user_id_originating,
        DROP COLUMN IF EXISTS sub_trigger_id,
        DROP COLUMN IF EXISTS category_id
    """)

    # Remove RBAC permissions
    op.execute("""
        UPDATE platform_role
        SET permissions = (
            SELECT jsonb_agg(elem)
            FROM jsonb_array_elements(permissions) AS elem
            WHERE elem::text NOT IN (
                '"notification_preference.tenant_default.edit"',
                '"notification_preference.user_override.edit"'
            )
        )
        WHERE code IN ('owner', 'technician', 'accountant', 'office_staff')
    """)

    # Drop notification_default_policy
    op.execute(
        "DROP TRIGGER IF EXISTS trg_notification_default_policy_set_updated_at ON notification_default_policy"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_notification_default_policy_guard_created_immutable ON notification_default_policy"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS audit_notification_default_policy_changes ON notification_default_policy"
    )
    op.execute("DROP TABLE IF EXISTS notification_default_policy")

    # Drop notification_category_sub_trigger
    op.execute(
        "DROP TRIGGER IF EXISTS trg_notification_category_sub_trigger_set_updated_at ON notification_category_sub_trigger"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_notification_category_sub_trigger_guard_created_immutable ON notification_category_sub_trigger"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS audit_notification_category_sub_trigger_changes ON notification_category_sub_trigger"
    )
    op.execute("DROP TABLE IF EXISTS notification_category_sub_trigger")

    # Drop notification_category
    op.execute(
        "DROP TRIGGER IF EXISTS trg_notification_category_set_updated_at ON notification_category"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_notification_category_guard_created_immutable ON notification_category"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS audit_notification_category_changes ON notification_category"
    )
    op.execute("DROP TABLE IF EXISTS notification_category")
