"""
Shared fixtures for PLATFORM-SMS-B1 tests.

The ``platform_sms_templates`` fixture inserts the 5 notification_type +
5 notification_template (channel='sms') system rows that the fail-loud loader
requires. The test DB is not guaranteed to carry seed_platform rows.
"""

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import text

# ── Campaign-locked verbatim SMS bodies (CXXXXXX §6/§8) ──────────────────────
# These are the canonical strings the verbatim-guardrail test asserts against.
# They MUST match the migration + seed_platform.py + the (now-deleted) code
# constants character-for-character.

PLATFORM_SMS_DOUBLE_OPTIN_BODY = (
    "Pilot for Trades: Reply YES to get important account, billing & security "
    "alerts by text. Msg freq varies. Msg & data rates may apply. "
    "Reply HELP for help, STOP to cancel."
)

PLATFORM_SMS_OPTIN_REPLY_BODY = (
    "Pilot for Trades: You're opted in to account, billing & security alerts. "
    "Msg freq varies. Msg & data rates may apply. "
    "Reply HELP for help, STOP to cancel."
)

PLATFORM_SMS_OPTOUT_REPLY_BODY = (
    "You have been unsubscribed from Pilot for Trades account alerts. "
    "No further messages will be sent. Reply START to re-subscribe."
)

PLATFORM_SMS_HELP_REPLY_BODY = (
    "Pilot for Trades account alerts. "
    "For help, visit pilotfortrades.com or email info@pilotfortrades.com. "
    "Msg & data rates may apply. Reply STOP to unsubscribe."
)

PLATFORM_PAYMENT_FAILED_BODY = (
    "Pilot for Trades: Your payment didn't go through. Please login to "
    "app.pilotfortrades.com and update your credit card to keep your account "
    "active. Reply STOP to opt out."
)

# PLATFORM-SMS-B2: Sample 3 — stored fully static (verbatim from playbook §6).
PLATFORM_SECURITY_NEW_DEVICE_BODY = (
    "Pilot for Trades: New sign-in to your account from a new device. "
    "If this wasn't you, secure your account now. Reply STOP to opt out."
)

# PLATFORM-SMS-B2: Sample 4 — stored with {{ maint_date }} / {{ maint_window }}
# Jinja2 placeholders. The registered render (with en-dash U+2013 in the
# window value) is asserted byte-for-byte in the B2 guardrail test.
PLATFORM_MAINTENANCE_BROADCAST_BODY = (
    "Pilot for Trades: Scheduled maintenance {{ maint_date }} from "
    "{{ maint_window }}. The app may be briefly unavailable. "
    "Reply STOP to opt out."
)

# All 7 type codes + bodies, keyed by type_code.
PLATFORM_SMS_TEMPLATES = {
    "platform_sms_double_optin": PLATFORM_SMS_DOUBLE_OPTIN_BODY,
    "platform_sms_optin_reply": PLATFORM_SMS_OPTIN_REPLY_BODY,
    "platform_sms_optout_reply": PLATFORM_SMS_OPTOUT_REPLY_BODY,
    "platform_sms_help_reply": PLATFORM_SMS_HELP_REPLY_BODY,
    "platform_payment_failed": PLATFORM_PAYMENT_FAILED_BODY,
    "platform_security_new_device": PLATFORM_SECURITY_NEW_DEVICE_BODY,
    "platform_maintenance_broadcast": PLATFORM_MAINTENANCE_BROADCAST_BODY,
}

# notification_type metadata (name + description per design §B.1).
PLATFORM_SMS_TYPES = [
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
        "description": "§8 auto-reply. Campaign-locked. Carrier-mandatory.",
    },
    {
        "code": "platform_sms_help_reply",
        "name": "Platform SMS — Help Reply (HELP/INFO)",
        "description": "§8 auto-reply. Campaign-locked. Carrier-mandatory.",
    },
    {
        "code": "platform_payment_failed",
        "name": "Platform SMS — Subscription Payment Failed",
        "description": (
            "§6 Sample 2 (Account Notifications). Campaign-locked. "
            "Fires from invoice.payment_failed."
        ),
    },
    # PLATFORM-SMS-B2: Samples 3 & 4 (campaign CXXXXXX).
    {
        "code": "platform_security_new_device",
        "name": "Platform: New-Device Sign-In Alert",
        "description": (
            "Pathway C security alert to tenant owners when a successful "
            "sign-in occurs from a device Cognito has not remembered "
            "(Post-Authentication trigger, newDeviceUsed). Campaign "
            "CXXXXXX Sample 3."
        ),
    },
    {
        "code": "platform_maintenance_broadcast",
        "name": "Platform: Scheduled Maintenance Broadcast",
        "description": (
            "Pathway C broadcast to all tenant owners announcing a "
            "scheduled platform maintenance window (operator-run CLI). "
            "Campaign CXXXXXX Sample 4."
        ),
    },
]


@pytest.fixture
def platform_sms_templates(db_session):
    """
    Insert the 7 notification_type + 7 notification_template (channel='sms')
    system rows required by the fail-loud loader.

    PLATFORM-SMS-B1: 5 pairs (double_optin, optin_reply, optout_reply,
    help_reply, payment_failed).
    PLATFORM-SMS-B2: 2 more pairs (security_new_device, maintenance_broadcast).

    Idempotent: uses ON CONFLICT DO NOTHING for types and WHERE NOT EXISTS for
    templates. Scoped to the exact 7 type codes — never touches other rows.
    """
    now = datetime.now(UTC).isoformat()

    # Insert notification_type rows.
    for nt in PLATFORM_SMS_TYPES:
        db_session.execute(
            text(
                """
                INSERT INTO public.notification_type
                    (code, tenant_id, audience, name, description, is_active,
                     created_at, updated_at)
                VALUES
                    (:code, NULL, 'tenant', :name, :description, true,
                     :now, :now)
                ON CONFLICT (code) DO NOTHING
                """
            ),
            {
                "code": nt["code"],
                "name": nt["name"],
                "description": nt["description"],
                "now": now,
            },
        )

    # Insert notification_template rows (sms channel, system-level).
    for type_code, body in PLATFORM_SMS_TEMPLATES.items():
        db_session.execute(
            text(
                """
                INSERT INTO public.notification_template
                    (id, tenant_id, notification_type_code, channel, locale,
                     subject, body, is_active, created_at, updated_at)
                SELECT :uuid, NULL, :type_code, 'sms', 'en',
                       NULL, :body, true, :now, :now
                WHERE NOT EXISTS (
                    SELECT 1 FROM public.notification_template
                    WHERE notification_type_code = :type_code
                      AND channel = 'sms'
                      AND tenant_id IS NULL
                )
                """
            ),
            {
                "uuid": str(uuid.uuid4()),
                "type_code": type_code,
                "body": body,
                "now": now,
            },
        )

    db_session.commit()
    return PLATFORM_SMS_TEMPLATES
