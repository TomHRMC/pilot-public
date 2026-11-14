"""
PLATFORM-SMS-B2 — Verbatim Guardrail Test
========================================
Holds the two new campaign-doc strings (Samples 3 & 4) as test constants and
asserts:
  (a) Sample 3: the seeded template body equals the registered constant
      byte-for-byte.
  (b) Sample 4: rendering the seeded template body with the registered values
      (maint_date="Sun 08-02-2026", maint_window="2:00–3:00 AM ET" — en-dash
      U+2013 preserved) equals the registered Sample 4 constant byte-for-byte.
      This is the 806-safety assertion: it proves the parameterized body
      renders to the exact string registered with Telnyx under campaign
      CXXXXXX.
  (c) Grep assertions: no ``Pilot for Trades:`` literal in
      ``scripts/broadcast_maintenance_sms.py``,
      ``lambda/post_authentication/handler.py``, or
      ``tasks/sms_platform_notifications.py`` (the campaign-locked bodies must
      come from the DB loader, never hardcoded in the task/CLI/Lambda code).

This test exists specifically to prevent error 806 (MNO review failure from a
template/code mismatch). Any future copy change requires editing this test +
a Telnyx portal resubmission — a deliberate, visible act.

Domain: notifications_comms (PRD §3.7)
"""

import pathlib

import pytest

from services.platform_sms_templates import get_platform_sms_body
from services.template_renderer import render_template

pytestmark = [
    pytest.mark.domain_notifications_comms,
    pytest.mark.unit,
]

# ── Campaign-locked verbatim strings (CXXXXXX §6) ─────────────────────────────
# These are the single source of truth for the guardrail. They MUST match the
# migration, seed_platform.py, and the conftest fixture constants exactly.

# Sample 3 — Security alert (Account Notifications) — stored fully static.
_EXPECTED_SECURITY_NEW_DEVICE = (
    "Pilot for Trades: New sign-in to your account from a new device. "
    "If this wasn't you, secure your account now. Reply STOP to opt out."
)

# Sample 4 — Scheduled maintenance (Account Notifications) — the REGISTERED
# render (with en-dash U+2013 in the window value). The stored body has
# {{ maint_date }} / {{ maint_window }} placeholders; rendering with the
# registered values must produce this exact string.
# ⚠️ en-dash U+2013 in "2:00–3:00" — do NOT substitute a hyphen.
_EXPECTED_MAINTENANCE_BROADCAST_RENDERED = (
    "Pilot for Trades: Scheduled maintenance Sun 08-02-2026 from "
    "2:00–3:00 AM ET. The app may be briefly unavailable. "
    "Reply STOP to opt out."
)

# The registered render values (en-dash U+2013 in the window).
_REGISTERED_MAINT_DATE = "Sun 08-02-2026"
_REGISTERED_MAINT_WINDOW = "2:00–3:00 AM ET"

# Files that must NOT contain a ``Pilot for Trades:`` literal (the
# campaign-locked bodies must come from the DB loader, never hardcoded).
_GUARDRAIL_SOURCE_FILES = [
    "scripts/broadcast_maintenance_sms.py",
    "lambda/post_authentication/handler.py",
    "tasks/sms_platform_notifications.py",
]


class TestVerbatimGuardrailB2:
    """Asserts DB rows match campaign-doc strings + no hardcoded body literals."""

    def test_sample3_seeded_body_matches_campaign_string(
        self, db_session, platform_sms_templates
    ):
        """Sample 3: the seeded template body must match the campaign-doc constant exactly."""
        actual_body = get_platform_sms_body(db_session, "platform_security_new_device")
        assert actual_body == _EXPECTED_SECURITY_NEW_DEVICE, (
            f"Sample 3 body mismatch!\n"
            f"  Expected: {_EXPECTED_SECURITY_NEW_DEVICE!r}\n"
            f"  Actual:   {actual_body!r}\n"
            f"This is a campaign-locked string (CXXXXXX). Editing it "
            f"requires a Telnyx portal resubmission."
        )

    def test_sample4_render_matches_campaign_string(
        self, db_session, platform_sms_templates
    ):
        """Sample 4: rendering the stored body with the registered values must
        produce the registered Sample 4 constant byte-for-byte (806-safety)."""
        stored_body = get_platform_sms_body(
            db_session, "platform_maintenance_broadcast"
        )
        rendered = render_template(
            stored_body,
            {
                "maint_date": _REGISTERED_MAINT_DATE,
                "maint_window": _REGISTERED_MAINT_WINDOW,
            },
        )
        assert rendered == _EXPECTED_MAINTENANCE_BROADCAST_RENDERED, (
            f"Sample 4 render mismatch!\n"
            f"  Expected: {_EXPECTED_MAINTENANCE_BROADCAST_RENDERED!r}\n"
            f"  Actual:   {rendered!r}\n"
            f"The parameterized body must render to the exact string "
            f"registered with Telnyx (campaign CXXXXXX). Check the en-dash "
            f"(U+2013) in the window value and the placeholder names."
        )

    def test_no_pilot_for_trades_literal_in_guardrail_files(self):
        """No 'Pilot for Trades:' literal in the task/CLI/Lambda source files.

        The campaign-locked bodies must be loaded from the DB via
        get_platform_sms_body(). The only places these strings may appear as
        literals are the migration, seed_platform.py, and the test constants.
        """
        backend_root = pathlib.Path(__file__).parent.parent.parent.parent
        marker = "Pilot for Trades:"
        for rel_path in _GUARDRAIL_SOURCE_FILES:
            full_path = backend_root / rel_path
            content = full_path.read_text()
            assert marker not in content, (
                f"Inline 'Pilot for Trades:' literal found in {rel_path}. "
                f"All platform SMS bodies must be loaded from the DB via "
                f"get_platform_sms_body()."
            )
