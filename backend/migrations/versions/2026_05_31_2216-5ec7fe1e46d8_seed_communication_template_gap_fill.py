"""seed_communication_template_gap_fill

Adds placeholder communication templates for 4 critical event types that had
no template rows in communication_template. The existing 7 rows (seeded by
batch_b4) cover field-status messages; this migration fills the transactional
communication gap needed for beta testing.

Templates added (SMS + email channels each):
  - invoice_sent            (2 rows)
  - appointment_reminder_24h(2 rows)
  - appointment_reminder_1h (2 rows)
  - payment_received        (2 rows)

Total: 8 new rows (all tenant_id=NULL = system-level default templates)

Note: `quote_sent` is intentionally excluded — no matching code exists in
customer_comm_template_type (FK would be violated). It should be added in a
future migration once the template type is registered.

Must run AFTER seed_system_user_sentinel so the sentinel user
(00000000-0000-0000-0000-000000000000) exists for created_by FK references.

Constraint awareness:
  - communication_template_email_subject_chk: email channel requires subject != NULL
  - fk_communication_template_type: template_code must exist in customer_comm_template_type
  - ON CONFLICT DO NOTHING is used for idempotency (keyed on id PK via new gen_random_uuid)
    NOTE: since the PK is a generated UUID, true idempotency is via the WHERE NOT EXISTS
    guard on (template_code, channel, tenant_id IS NULL).

Revision ID: 5ec7fe1e46d8
Revises: 4d035847177f
Create Date: 2026-05-31 22:16:00.000000
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "5ec7fe1e46d8"
down_revision = "4d035847177f"
branch_labels = None
depends_on = None

# Sentinel user for created_by FK
_SYSTEM_USER_ID = "00000000-0000-0000-0000-000000000000"


def upgrade() -> None:
    # ---------------------------------------------------------------------------
    # communication_template has UUID `id` PK — audit.log_changes() works fine.
    # BEFORE UPDATE triggers don't fire on INSERT. No session_replication_role
    # bypass needed on RDS.
    # ---------------------------------------------------------------------------

    # ---------------------------------------------------------------------------
    # invoice_sent — SMS channel
    # ---------------------------------------------------------------------------
    op.execute(f"""
        INSERT INTO communication_template (id, tenant_id, template_code, channel,
                                            subject, body_template, is_active,
                                            created_at, updated_at,
                                            created_by, updated_by)
        SELECT
            gen_random_uuid(),
            NULL,
            'invoice_sent',
            'sms',
            NULL,
            'Your invoice is ready. View and pay at {{{{invoice_link}}}}. Reply STOP to opt out.',
            true,
            now(), now(),
            '{_SYSTEM_USER_ID}'::uuid,
            '{_SYSTEM_USER_ID}'::uuid
        WHERE NOT EXISTS (
            SELECT 1 FROM communication_template
            WHERE template_code = 'invoice_sent'
              AND channel = 'sms'
              AND tenant_id IS NULL
        );
    """)

    # ---------------------------------------------------------------------------
    # invoice_sent — email channel (subject required)
    # ---------------------------------------------------------------------------
    op.execute(f"""
        INSERT INTO communication_template (id, tenant_id, template_code, channel,
                                            subject, body_template, is_active,
                                            created_at, updated_at,
                                            created_by, updated_by)
        SELECT
            gen_random_uuid(),
            NULL,
            'invoice_sent',
            'email',
            'Your Invoice from {{{{tenant_name}}}}',
            'Hi {{{{customer_first_name}}}},\n\nYour invoice for {{{{job_title}}}} is ready. '
            'View and pay here: {{{{invoice_link}}}}\n\nThank you,\n{{{{tenant_name}}}}',
            true,
            now(), now(),
            '{_SYSTEM_USER_ID}'::uuid,
            '{_SYSTEM_USER_ID}'::uuid
        WHERE NOT EXISTS (
            SELECT 1 FROM communication_template
            WHERE template_code = 'invoice_sent'
              AND channel = 'email'
              AND tenant_id IS NULL
        );
    """)

    # ---------------------------------------------------------------------------
    # appointment_reminder_24h — SMS channel
    # ---------------------------------------------------------------------------
    op.execute(f"""
        INSERT INTO communication_template (id, tenant_id, template_code, channel,
                                            subject, body_template, is_active,
                                            created_at, updated_at,
                                            created_by, updated_by)
        SELECT
            gen_random_uuid(),
            NULL,
            'appointment_reminder_24h',
            'sms',
            NULL,
            'Reminder: {{{{tenant_name}}}} appointment tomorrow at {{{{appointment_time}}}}. '
            'Reply STOP to opt out.',
            true,
            now(), now(),
            '{_SYSTEM_USER_ID}'::uuid,
            '{_SYSTEM_USER_ID}'::uuid
        WHERE NOT EXISTS (
            SELECT 1 FROM communication_template
            WHERE template_code = 'appointment_reminder_24h'
              AND channel = 'sms'
              AND tenant_id IS NULL
        );
    """)

    # ---------------------------------------------------------------------------
    # appointment_reminder_24h — email channel (subject required)
    # ---------------------------------------------------------------------------
    op.execute(f"""
        INSERT INTO communication_template (id, tenant_id, template_code, channel,
                                            subject, body_template, is_active,
                                            created_at, updated_at,
                                            created_by, updated_by)
        SELECT
            gen_random_uuid(),
            NULL,
            'appointment_reminder_24h',
            'email',
            'Appointment Reminder — {{{{appointment_time}}}}',
            'Hi {{{{customer_first_name}}}},\n\nThis is a reminder that '
            '{{{{tenant_name}}}} has an appointment scheduled for {{{{appointment_time}}}}.\n\n'
            'Address: {{{{site_address}}}}\n\nThank you,\n{{{{tenant_name}}}}',
            true,
            now(), now(),
            '{_SYSTEM_USER_ID}'::uuid,
            '{_SYSTEM_USER_ID}'::uuid
        WHERE NOT EXISTS (
            SELECT 1 FROM communication_template
            WHERE template_code = 'appointment_reminder_24h'
              AND channel = 'email'
              AND tenant_id IS NULL
        );
    """)

    # ---------------------------------------------------------------------------
    # appointment_reminder_1h — SMS channel
    # ---------------------------------------------------------------------------
    op.execute(f"""
        INSERT INTO communication_template (id, tenant_id, template_code, channel,
                                            subject, body_template, is_active,
                                            created_at, updated_at,
                                            created_by, updated_by)
        SELECT
            gen_random_uuid(),
            NULL,
            'appointment_reminder_1h',
            'sms',
            NULL,
            '{{{{tenant_name}}}} is on the way — arriving around {{{{appointment_time}}}}. '
            'Reply STOP to opt out.',
            true,
            now(), now(),
            '{_SYSTEM_USER_ID}'::uuid,
            '{_SYSTEM_USER_ID}'::uuid
        WHERE NOT EXISTS (
            SELECT 1 FROM communication_template
            WHERE template_code = 'appointment_reminder_1h'
              AND channel = 'sms'
              AND tenant_id IS NULL
        );
    """)

    # ---------------------------------------------------------------------------
    # appointment_reminder_1h — email channel (subject required)
    # ---------------------------------------------------------------------------
    op.execute(f"""
        INSERT INTO communication_template (id, tenant_id, template_code, channel,
                                            subject, body_template, is_active,
                                            created_at, updated_at,
                                            created_by, updated_by)
        SELECT
            gen_random_uuid(),
            NULL,
            'appointment_reminder_1h',
            'email',
            'Your Appointment Is In About 1 Hour',
            'Hi {{{{customer_first_name}}}},\n\n'
            '{{{{tenant_name}}}} will be arriving at {{{{site_address}}}} around {{{{appointment_time}}}}.\n\n'
            'Thank you,\n{{{{tenant_name}}}}',
            true,
            now(), now(),
            '{_SYSTEM_USER_ID}'::uuid,
            '{_SYSTEM_USER_ID}'::uuid
        WHERE NOT EXISTS (
            SELECT 1 FROM communication_template
            WHERE template_code = 'appointment_reminder_1h'
              AND channel = 'email'
              AND tenant_id IS NULL
        );
    """)

    # ---------------------------------------------------------------------------
    # payment_received — SMS channel
    # ---------------------------------------------------------------------------
    op.execute(f"""
        INSERT INTO communication_template (id, tenant_id, template_code, channel,
                                            subject, body_template, is_active,
                                            created_at, updated_at,
                                            created_by, updated_by)
        SELECT
            gen_random_uuid(),
            NULL,
            'payment_received',
            'sms',
            NULL,
            'Payment received — thank you! {{{{tenant_name}}}} has processed your payment of '
            '{{{{payment_amount}}}}. Reply STOP to opt out.',
            true,
            now(), now(),
            '{_SYSTEM_USER_ID}'::uuid,
            '{_SYSTEM_USER_ID}'::uuid
        WHERE NOT EXISTS (
            SELECT 1 FROM communication_template
            WHERE template_code = 'payment_received'
              AND channel = 'sms'
              AND tenant_id IS NULL
        );
    """)

    # ---------------------------------------------------------------------------
    # payment_received — email channel (subject required)
    # ---------------------------------------------------------------------------
    op.execute(f"""
        INSERT INTO communication_template (id, tenant_id, template_code, channel,
                                            subject, body_template, is_active,
                                            created_at, updated_at,
                                            created_by, updated_by)
        SELECT
            gen_random_uuid(),
            NULL,
            'payment_received',
            'email',
            'Payment Received — Thank You!',
            'Hi {{{{customer_first_name}}}},\n\n'
            'We have received your payment of {{{{payment_amount}}}} for {{{{job_title}}}}. '
            'Thank you for your business!\n\n{{{{tenant_name}}}}',
            true,
            now(), now(),
            '{_SYSTEM_USER_ID}'::uuid,
            '{_SYSTEM_USER_ID}'::uuid
        WHERE NOT EXISTS (
            SELECT 1 FROM communication_template
            WHERE template_code = 'payment_received'
              AND channel = 'email'
              AND tenant_id IS NULL
        );
    """)


def downgrade() -> None:
    # Remove only the system-level placeholder templates added by this migration.
    # Tenant-specific customizations (tenant_id IS NOT NULL) are untouched.
    op.execute("""
        DELETE FROM communication_template
        WHERE tenant_id IS NULL
          AND template_code IN (
              'invoice_sent',
              'appointment_reminder_24h',
              'appointment_reminder_1h',
              'payment_received'
          );
    """)
