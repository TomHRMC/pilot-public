"""phase_fe_1_batch_b4_communication_tables

Revision ID: 16668cf3041e
Revises: 20cf5fb214f9
Create Date: 2026-05-01 16:29:00

Batch B4 — Customer Comms Base
Creates:
  - communication_template  (system + tenant-level SMS/email templates)
  - customer_communication  (durable send-log; one row per dispatched message)

Also seeds:
  - notification_type row: "customer_communication_sent"
  - 7 system-level communication_template rows (MVP SMS defaults + on_my_way email)

Triggers: audit_log, immutable_guard, updated_at_sync for both tables.
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "16668cf3041e"
down_revision = "20cf5fb214f9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. Create communication_template
    # ------------------------------------------------------------------
    op.execute("""
        CREATE TABLE communication_template (
            created_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            created_by             UUID REFERENCES "user"(id) ON DELETE RESTRICT,
            updated_by             UUID REFERENCES "user"(id) ON DELETE RESTRICT,
            id                     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id              UUID REFERENCES tenant(id) ON DELETE RESTRICT,
            template_code          VARCHAR NOT NULL,
            channel                VARCHAR NOT NULL,
            subject                TEXT,
            body_template          TEXT NOT NULL,
            is_active              BOOLEAN NOT NULL DEFAULT TRUE,
            CONSTRAINT communication_template_channel_chk
                CHECK (channel IN ('sms', 'email')),
            CONSTRAINT communication_template_code_chk
                CHECK (template_code IN ('on_my_way','running_late','arrived','job_complete','parts_delay','confirm_appointment')),
            CONSTRAINT communication_template_email_subject_chk
                CHECK (channel <> 'email' OR subject IS NOT NULL)
        )
    """)

    # Composite unique index (partial: only active templates)
    op.execute("""
        CREATE UNIQUE INDEX uq_communication_template_scope
            ON communication_template (COALESCE(tenant_id, '00000000-0000-0000-0000-000000000000'::uuid), template_code, channel)
            WHERE is_active = TRUE
    """)

    op.execute("""
        CREATE INDEX idx_communication_template_tenant_id
            ON communication_template (tenant_id)
    """)

    op.execute("""
        CREATE INDEX idx_communication_template_code_channel
            ON communication_template (template_code, channel)
    """)

    # Triggers for communication_template
    op.execute("""
        CREATE TRIGGER audit_communication_template_changes
            AFTER INSERT OR DELETE OR UPDATE ON public.communication_template
            FOR EACH ROW EXECUTE FUNCTION audit.log_changes()
    """)
    op.execute("""
        CREATE TRIGGER trg_communication_template_guard_created_immutable
            BEFORE UPDATE ON public.communication_template
            FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable()
    """)
    op.execute("""
        CREATE TRIGGER trg_communication_template_set_updated_at
            BEFORE UPDATE ON public.communication_template
            FOR EACH ROW EXECUTE FUNCTION public.set_updated_at()
    """)

    # ------------------------------------------------------------------
    # 2. Create customer_communication
    # ------------------------------------------------------------------
    op.execute("""
        CREATE TABLE customer_communication (
            created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            created_by                  UUID REFERENCES "user"(id) ON DELETE RESTRICT,
            updated_by                  UUID REFERENCES "user"(id) ON DELETE RESTRICT,
            id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id                   UUID NOT NULL REFERENCES tenant(id) ON DELETE RESTRICT,
            customer_id                 UUID NOT NULL REFERENCES customer(id) ON DELETE RESTRICT,
            job_id                      UUID REFERENCES job(id) ON DELETE SET NULL,
            sender_user_id              UUID NOT NULL REFERENCES "user"(id) ON DELETE RESTRICT,
            template_code               VARCHAR NOT NULL,
            template_id                 UUID REFERENCES communication_template(id) ON DELETE SET NULL,
            rendered_subject            TEXT,
            rendered_message            TEXT NOT NULL,
            channel                     VARCHAR NOT NULL,
            customer_preferred_channel  VARCHAR(10),
            actual_channel              VARCHAR NOT NULL,
            channel_override_flag       BOOLEAN NOT NULL DEFAULT FALSE,
            status                      VARCHAR NOT NULL DEFAULT 'pending',
            sent_at                     TIMESTAMPTZ,
            notification_outbox_id      UUID REFERENCES notification_outbox(id) ON DELETE SET NULL,
            variables_json              JSONB,
            CONSTRAINT customer_communication_channel_chk
                CHECK (channel IN ('sms', 'email')),
            CONSTRAINT customer_communication_actual_channel_chk
                CHECK (actual_channel IN ('sms', 'email')),
            CONSTRAINT customer_communication_status_chk
                CHECK (status IN ('pending', 'sent', 'failed', 'canceled')),
            CONSTRAINT customer_communication_template_code_chk
                CHECK (template_code IN ('on_my_way','running_late','arrived','job_complete','parts_delay','confirm_appointment'))
        )
    """)

    op.execute("""
        CREATE INDEX idx_customer_communication_tenant_id
            ON customer_communication (tenant_id)
    """)
    op.execute("""
        CREATE INDEX idx_customer_communication_customer_id
            ON customer_communication (customer_id)
    """)
    op.execute("""
        CREATE INDEX idx_customer_communication_customer_sent
            ON customer_communication (customer_id, sent_at DESC NULLS LAST)
    """)
    op.execute("""
        CREATE INDEX idx_customer_communication_tenant_sent
            ON customer_communication (tenant_id, sent_at DESC NULLS LAST)
    """)
    op.execute("""
        CREATE INDEX idx_customer_communication_job_id
            ON customer_communication (job_id)
            WHERE job_id IS NOT NULL
    """)
    op.execute("""
        CREATE INDEX idx_customer_communication_notification_outbox_id
            ON customer_communication (notification_outbox_id)
            WHERE notification_outbox_id IS NOT NULL
    """)

    # Triggers for customer_communication
    op.execute("""
        CREATE TRIGGER audit_customer_communication_changes
            AFTER INSERT OR DELETE OR UPDATE ON public.customer_communication
            FOR EACH ROW EXECUTE FUNCTION audit.log_changes()
    """)
    op.execute("""
        CREATE TRIGGER trg_customer_communication_guard_created_immutable
            BEFORE UPDATE ON public.customer_communication
            FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable()
    """)
    op.execute("""
        CREATE TRIGGER trg_customer_communication_set_updated_at
            BEFORE UPDATE ON public.customer_communication
            FOR EACH ROW EXECUTE FUNCTION public.set_updated_at()
    """)

    # ------------------------------------------------------------------
    # 3a. Seed: entity_type row for customer_communication
    #     Required by NotificationEvent.entity_type_code FK
    # ------------------------------------------------------------------
    op.execute("""
        INSERT INTO entity_type (code, name, is_active, is_default, created_at, updated_at)
        VALUES (
            'customer_communication',
            'Customer Communication',
            TRUE,
            FALSE,
            NOW(),
            NOW()
        )
        ON CONFLICT (code) DO NOTHING
    """)

    # ------------------------------------------------------------------
    # 3b. Seed: notification_type row for customer_communication_sent
    #    note: code is PK; audience is required (see existing rows e.g. 'quote_accepted')
    # ------------------------------------------------------------------
    op.execute("""
        INSERT INTO notification_type (code, audience, name, description, is_active, created_at, updated_at)
        VALUES (
            'customer_communication_sent',
            'tenant',
            'Customer Communication Sent',
            'Fired when a templated customer communication is dispatched via the send endpoint.',
            TRUE,
            NOW(),
            NOW()
        )
        ON CONFLICT (code) DO NOTHING
    """)

    # ------------------------------------------------------------------
    # 4. Seed: system-level communication_template rows (tenant_id IS NULL)
    # ------------------------------------------------------------------
    op.execute("""
        INSERT INTO communication_template
            (id, tenant_id, template_code, channel, subject, body_template, is_active, created_at, updated_at)
        VALUES
            -- SMS templates
            (gen_random_uuid(), NULL, 'on_my_way',           'sms', NULL,
             'Hi {{ customer_first_name }}, this is {{ sender_name }} — I''m on my way, ETA {{ eta }}. Reply STOP to opt out.',
             TRUE, NOW(), NOW()),
            (gen_random_uuid(), NULL, 'running_late',        'sms', NULL,
             'Hi {{ customer_first_name }}, {{ sender_name }} here — running about {{ minutes_late }} minutes behind. Apologies for the delay. Reply STOP to opt out.',
             TRUE, NOW(), NOW()),
            (gen_random_uuid(), NULL, 'arrived',             'sms', NULL,
             'Hi {{ customer_first_name }}, {{ sender_name }} here — I''ve arrived and am starting work. Reply STOP to opt out.',
             TRUE, NOW(), NOW()),
            (gen_random_uuid(), NULL, 'job_complete',        'sms', NULL,
             'Hi {{ customer_first_name }}, {{ sender_name }} here — work is complete. Invoice to follow. Reply STOP to opt out.',
             TRUE, NOW(), NOW()),
            (gen_random_uuid(), NULL, 'parts_delay',         'sms', NULL,
             'Hi {{ customer_first_name }}, {{ sender_name }} here — there''s a parts delay. I''ll update you as soon as I have more info. Reply STOP to opt out.',
             TRUE, NOW(), NOW()),
            (gen_random_uuid(), NULL, 'confirm_appointment', 'sms', NULL,
             'Hi {{ customer_first_name }}, please confirm your appointment for {{ date_time }} at {{ site_address }}. Reply YES to confirm or call us. Reply STOP to opt out.',
             TRUE, NOW(), NOW()),
            -- Email variant for on_my_way (only email seeded in B4)
            (gen_random_uuid(), NULL, 'on_my_way',           'email', 'On my way — ETA {{ eta }}',
             'Hi {{ customer_first_name }},

I''m on my way to {{ site_address }}. ETA {{ eta }}.

{{ sender_name }}',
             TRUE, NOW(), NOW())
    """)

    # ------------------------------------------------------------------
    # 5. Seed: RBAC — add communications.send to technician and office_staff roles
    # ------------------------------------------------------------------
    op.execute("""
        UPDATE platform_role
        SET permissions = permissions || '["communications.send"]'::jsonb,
            updated_at  = NOW()
        WHERE code IN ('technician', 'office_staff')
          AND NOT (permissions @> '["communications.send"]'::jsonb)
    """)


def downgrade() -> None:
    # Reverse RBAC seed
    op.execute("""
        UPDATE platform_role
        SET permissions = (
            SELECT jsonb_agg(elem)
            FROM jsonb_array_elements(permissions) AS elem
            WHERE elem::text <> '"communications.send"'
        ),
        updated_at = NOW()
        WHERE code IN ('technician', 'office_staff')
    """)

    # Remove entity_type and notification_type seeds
    op.execute("""
        DELETE FROM notification_type WHERE code = 'customer_communication_sent'
    """)
    op.execute("""
        DELETE FROM entity_type WHERE code = 'customer_communication'
    """)

    # Drop customer_communication (references communication_template)
    op.execute(
        "DROP TRIGGER IF EXISTS audit_customer_communication_changes ON public.customer_communication"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_customer_communication_guard_created_immutable ON public.customer_communication"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_customer_communication_set_updated_at ON public.customer_communication"
    )
    op.execute("DROP TABLE IF EXISTS customer_communication")

    # Drop communication_template
    op.execute(
        "DROP TRIGGER IF EXISTS audit_communication_template_changes ON public.communication_template"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_communication_template_guard_created_immutable ON public.communication_template"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_communication_template_set_updated_at ON public.communication_template"
    )
    op.execute("DROP TABLE IF EXISTS communication_template")
