"""platform_sms_b1_pathway_c_templates

Revision ID: ba16d3b7fb6f
Revises: 7f57c3f5f15c
Create Date: 2026-08-10 16:46:06.754706+00:00

PLATFORM-SMS-B1: Seeds 5 notification_type + 5 notification_template (channel='sms')
system rows for Pathway C (Pilot→tenant-owner platform SMS). Campaign CXXXXXX.

The five template bodies are campaign-locked verbatim strings registered with Telnyx.
Editing them requires a Telnyx portal resubmission — see
dev-docs/integrations/telnyx/telnyx-10dlc-p4t-tenant-comms-campaign.md §6/§8.

No DDL — inserts only. All statements idempotent (ON CONFLICT DO NOTHING / WHERE NOT EXISTS).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ba16d3b7fb6f"
down_revision: str | None = "7f57c3f5f15c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# ── Campaign-locked verbatim SMS bodies (CXXXXXX §6/§8) ──────────────────────
# DO NOT alter punctuation, spacing, or wording — MNO review (error 806) depends
# on an exact match to the submitted template. Code constants in
# tasks/sms_compliance_platform.py and api/routes/webhooks_sms.py were diffed
# character-for-character against these strings — they match exactly.

_PLATFORM_SMS_DOUBLE_OPTIN_BODY = (
    "Pilot for Trades: Reply YES to get important account, billing & security "
    "alerts by text. Msg freq varies. Msg & data rates may apply. "
    "Reply HELP for help, STOP to cancel."
)

_PLATFORM_SMS_OPTIN_REPLY_BODY = (
    "Pilot for Trades: You're opted in to account, billing & security alerts. "
    "Msg freq varies. Msg & data rates may apply. "
    "Reply HELP for help, STOP to cancel."
)

_PLATFORM_SMS_OPTOUT_REPLY_BODY = (
    "You have been unsubscribed from Pilot for Trades account alerts. "
    "No further messages will be sent. Reply START to re-subscribe."
)

_PLATFORM_SMS_HELP_REPLY_BODY = (
    "Pilot for Trades account alerts. "
    "For help, visit pilotfortrades.com or email info@pilotfortrades.com. "
    "Msg & data rates may apply. Reply STOP to unsubscribe."
)

_PLATFORM_PAYMENT_FAILED_BODY = (
    "Pilot for Trades: Your payment didn't go through. Please login to "
    "app.pilotfortrades.com and update your credit card to keep your account "
    "active. Reply STOP to opt out."
)

# ── notification_type rows (system, tenant_id NULL, audience='tenant') ───────
_NOTIFICATION_TYPES = [
    {
        "code": "platform_sms_double_optin",
        "name": "Platform SMS — Double Opt-In Request",
        "description": (
            "Pathway C first message (§6 Sample 1 / §8). Campaign-locked — "
            "do not edit without Telnyx resubmission."
        ),
    },
    {
        "code": "platform_sms_optin_reply",
        "name": "Platform SMS — Opt-In Reply (START/UNSTOP/YES)",
        "description": "§8 auto-reply. Campaign-locked.",
    },
    {
        "code": "platform_sms_optout_reply",
        "name": "Platform SMS — Opt-Out Reply (STOP)",
        "description": ("§8 auto-reply. Campaign-locked. Carrier-mandatory."),
    },
    {
        "code": "platform_sms_help_reply",
        "name": "Platform SMS — Help Reply (HELP/INFO)",
        "description": ("§8 auto-reply. Campaign-locked. Carrier-mandatory."),
    },
    {
        "code": "platform_payment_failed",
        "name": "Platform SMS — Subscription Payment Failed",
        "description": (
            "§6 Sample 2 (Account Notifications). Campaign-locked. "
            "Fires from invoice.payment_failed."
        ),
    },
]

# ── notification_template rows (tenant_id NULL, channel='sms', locale='en') ──
_NOTIFICATION_TEMPLATES = [
    ("platform_sms_double_optin", _PLATFORM_SMS_DOUBLE_OPTIN_BODY),
    ("platform_sms_optin_reply", _PLATFORM_SMS_OPTIN_REPLY_BODY),
    ("platform_sms_optout_reply", _PLATFORM_SMS_OPTOUT_REPLY_BODY),
    ("platform_sms_help_reply", _PLATFORM_SMS_HELP_REPLY_BODY),
    ("platform_payment_failed", _PLATFORM_PAYMENT_FAILED_BODY),
]


def upgrade() -> None:
    # Disable triggers/audit for bulk insert (standard replica-role pattern).
    op.execute("SET LOCAL session_replication_role = 'replica';")

    # ── 1. Insert 5 notification_type rows (idempotent via ON CONFLICT) ──────
    for nt in _NOTIFICATION_TYPES:
        op.execute(
            sa.text(
                """
                INSERT INTO public.notification_type
                    (code, tenant_id, audience, name, description, is_active,
                     created_at, updated_at)
                VALUES
                    (:code, NULL, 'tenant', :name, :description, true,
                     NOW(), NOW())
                ON CONFLICT (code) DO NOTHING
                """
            ).bindparams(
                code=nt["code"],
                name=nt["name"],
                description=nt["description"],
            )
        )

    # ── 2. Insert 5 notification_template rows (idempotent via WHERE NOT EXISTS)
    # No unique constraint on (notification_type_code, channel, tenant_id IS NULL)
    # — guard with WHERE NOT EXISTS to prevent duplicates on re-run.
    for type_code, body in _NOTIFICATION_TEMPLATES:
        op.execute(
            sa.text(
                """
                INSERT INTO public.notification_template
                    (id, tenant_id, notification_type_code, channel, locale,
                     subject, body, is_active, created_at, updated_at)
                SELECT gen_random_uuid(), NULL, :type_code, 'sms', 'en',
                       NULL, :body, true, NOW(), NOW()
                WHERE NOT EXISTS (
                    SELECT 1 FROM public.notification_template
                    WHERE notification_type_code = :type_code
                      AND channel = 'sms'
                      AND tenant_id IS NULL
                )
                """
            ).bindparams(type_code=type_code, body=body)
        )


def downgrade() -> None:
    op.execute("SET LOCAL session_replication_role = 'replica';")

    # Delete exactly the 5 template rows (value-scoped by exact codes).
    template_codes = tuple(t[0] for t in _NOTIFICATION_TEMPLATES)
    type_codes = tuple(nt["code"] for nt in _NOTIFICATION_TYPES)

    op.execute(
        sa.text(
            """
            DELETE FROM public.notification_template
            WHERE notification_type_code IN :codes
              AND channel = 'sms'
              AND tenant_id IS NULL
            """
        ).bindparams(sa.bindparam("codes", expanding=True, value=list(template_codes)))
    )

    # Delete exactly the 5 type rows (value-scoped by exact codes).
    op.execute(
        sa.text(
            """
            DELETE FROM public.notification_type
            WHERE code IN :codes
            """
        ).bindparams(sa.bindparam("codes", expanding=True, value=list(type_codes)))
    )
