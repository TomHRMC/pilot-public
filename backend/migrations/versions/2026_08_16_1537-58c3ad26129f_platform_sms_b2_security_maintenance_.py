"""platform_sms_b2_security_maintenance_templates

PLATFORM-SMS-B2 — Pathway C platform SMS: Security-Alert (New-Device) +
Maintenance Broadcast senders. Data-only migration: inserts 2
notification_type rows + 2 notification_template (channel='sms') rows for
campaign CXXXXXX Samples 3 & 4.

Design: dev-docs/architecture-design/batch-designs/batch-platform-sms-b2-design.md §B
ADR-0013 (three-pathway SMS model / Pathway C).

Sample 3 (platform_security_new_device) — stored fully static, verbatim.
Sample 4 (platform_maintenance_broadcast) — stored with {{ maint_date }} /
{{ maint_window }} Jinja placeholders; renders to the registered string.

Idempotent via WHERE NOT EXISTS guards (notification_template has no unique
constraint on its natural key; tenant_id IS NULL never conflict-matches).

Revision ID: 58c3ad26129f
Revises: c9043c486324
Create Date: 2026-08-16 15:37:58.468390+00:00

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "58c3ad26129f"
down_revision: str | None = "c9043c486324"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Disable FK checks for the data insert (no FKs touched, but matches the
    # repo convention for data migrations).
    op.execute("SET LOCAL session_replication_role = 'replica';")

    # ── B.1 — notification_type rows (system, tenant_id NULL, audience='tenant') ──
    op.execute(
        """
        INSERT INTO public.notification_type
            (code, tenant_id, audience, name, description, is_active,
             created_at, updated_at, created_by, updated_by)
        SELECT v.code, NULL, 'tenant', v.name, v.description, true,
               now(), now(), NULL, NULL
        FROM (VALUES
            ('platform_security_new_device',
             'Platform: New-Device Sign-In Alert',
             'Pathway C security alert to tenant owners when a successful sign-in occurs from a device Cognito has not remembered (Post-Authentication trigger, newDeviceUsed). Campaign CXXXXXX Sample 3.'),
            ('platform_maintenance_broadcast',
             'Platform: Scheduled Maintenance Broadcast',
             'Pathway C broadcast to all tenant owners announcing a scheduled platform maintenance window (operator-run CLI). Campaign CXXXXXX Sample 4.')
        ) AS v(code, name, description)
        WHERE NOT EXISTS (
            SELECT 1 FROM public.notification_type t WHERE t.code = v.code
        );
        """
    )

    # ── B.2 — notification_template rows (channel='sms', locale='en', subject=NULL) ──
    # Sample 3 — stored fully static (verbatim from playbook §6).
    op.execute(
        """
        INSERT INTO public.notification_template
            (id, tenant_id, notification_type_code, channel, locale, subject, body, is_active,
             created_at, updated_at, created_by, updated_by)
        SELECT gen_random_uuid(), NULL, 'platform_security_new_device', 'sms', 'en', NULL,
               'Pilot for Trades: New sign-in to your account from a new device. If this wasn''t you, secure your account now. Reply STOP to opt out.',
               true, now(), now(), NULL, NULL
        WHERE NOT EXISTS (
            SELECT 1 FROM public.notification_template
            WHERE notification_type_code = 'platform_security_new_device'
              AND channel = 'sms' AND locale = 'en' AND tenant_id IS NULL
        );
        """
    )

    # Sample 4 — stored with {{ maint_date }} / {{ maint_window }} placeholders.
    op.execute(
        """
        INSERT INTO public.notification_template
            (id, tenant_id, notification_type_code, channel, locale, subject, body, is_active,
             created_at, updated_at, created_by, updated_by)
        SELECT gen_random_uuid(), NULL, 'platform_maintenance_broadcast', 'sms', 'en', NULL,
               'Pilot for Trades: Scheduled maintenance {{ maint_date }} from {{ maint_window }}. The app may be briefly unavailable. Reply STOP to opt out.',
               true, now(), now(), NULL, NULL
        WHERE NOT EXISTS (
            SELECT 1 FROM public.notification_template
            WHERE notification_type_code = 'platform_maintenance_broadcast'
              AND channel = 'sms' AND locale = 'en' AND tenant_id IS NULL
        );
        """
    )


def downgrade() -> None:
    op.execute("SET LOCAL session_replication_role = 'replica';")

    # Reverse order: templates first, then types.
    op.execute(
        """
        DELETE FROM public.notification_template
        WHERE notification_type_code IN ('platform_security_new_device', 'platform_maintenance_broadcast')
          AND channel = 'sms' AND tenant_id IS NULL;
        """
    )
    op.execute(
        """
        DELETE FROM public.notification_type
        WHERE code IN ('platform_security_new_device', 'platform_maintenance_broadcast')
          AND tenant_id IS NULL;
        """
    )
