"""b21_seed_recurring_job_scheduled_templates

Revision ID: b1bd90914b77
Revises: aa84a3d6afe8
Create Date: 2026-07-12 16:45:26

B21: Seed the recurring_job_scheduled sms + email communication templates.

communication_template columns (confirmed via MCP):
  created_at, updated_at, created_by, updated_by, id, tenant_id,
  template_code, channel, subject, body_template, is_active

No unique constraint on (template_code, channel) — use WHERE NOT EXISTS to
guard against duplicate inserts on re-run (mirrors the platform_setting pattern
from migration f7f30492c3e4).
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "b1bd90914b77"
down_revision = "aa84a3d6afe8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("SET LOCAL session_replication_role = 'replica';")

    # SMS template
    op.execute("""
        INSERT INTO communication_template (
            id, tenant_id, template_code, channel,
            subject, body_template, is_active,
            created_at, updated_at
        )
        SELECT
            gen_random_uuid(),
            NULL,
            'recurring_job_scheduled',
            'sms',
            NULL,
            'Hi {{customer_name}}, your scheduled {{service_description}} with {{company_name}} is confirmed for {{scheduled_date}} at {{scheduled_time}}. Reply STOP to opt out.',
            true,
            now(),
            now()
        WHERE NOT EXISTS (
            SELECT 1 FROM communication_template
            WHERE template_code = 'recurring_job_scheduled'
              AND channel = 'sms'
              AND tenant_id IS NULL
        )
    """)

    # Email template
    op.execute("""
        INSERT INTO communication_template (
            id, tenant_id, template_code, channel,
            subject, body_template, is_active,
            created_at, updated_at
        )
        SELECT
            gen_random_uuid(),
            NULL,
            'recurring_job_scheduled',
            'email',
            'Your {{service_description}} is scheduled',
            'Hi {{customer_name}},

Your scheduled {{service_description}} with {{company_name}} is confirmed.

Date: {{scheduled_date}}
Time: {{scheduled_time}}
Address: {{site_address}}

If you need to reschedule, please contact us at {{company_phone}}.

Thank you,
{{company_name}}',
            true,
            now(),
            now()
        WHERE NOT EXISTS (
            SELECT 1 FROM communication_template
            WHERE template_code = 'recurring_job_scheduled'
              AND channel = 'email'
              AND tenant_id IS NULL
        )
    """)


def downgrade() -> None:
    op.execute("""
        DELETE FROM communication_template
        WHERE template_code = 'recurring_job_scheduled'
          AND tenant_id IS NULL
    """)
