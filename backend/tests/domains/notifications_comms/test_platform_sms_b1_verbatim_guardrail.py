"""
PLATFORM-SMS-B1 — Verbatim Guardrail Test
=========================================
Holds the five campaign-doc strings as test constants and asserts:
  (a) Each seeded template body (inserted via the platform_sms_templates
      fixture) equals the campaign-doc constant exactly.
  (b) Source scan: tasks/sms_compliance_platform.py and
      api/routes/webhooks_sms.py contain no remaining _PLATFORM_ constants
      and no ``Pilot for Trades:`` SMS body literals outside the loader.

This test exists specifically to prevent error 806 (MNO review failure from
a template/code mismatch). Any future copy change requires editing this test
+ a Telnyx portal resubmission — a deliberate, visible act.

Domain: notifications_comms (PRD §3.7)
"""

import pathlib

import pytest

from services.platform_sms_templates import get_platform_sms_body

pytestmark = [
    pytest.mark.domain_notifications_comms,
    pytest.mark.unit,
]

# ── Campaign-locked verbatim strings (CXXXXXX §6/§8) ─────────────────────────
# These are the single source of truth for the guardrail. They MUST match the
# migration, seed_platform.py, and the (now-deleted) code constants exactly.

_EXPECTED_DOUBLE_OPTIN = (
    "Pilot for Trades: Reply YES to get important account, billing & security "
    "alerts by text. Msg freq varies. Msg & data rates may apply. "
    "Reply HELP for help, STOP to cancel."
)

_EXPECTED_OPTIN_REPLY = (
    "Pilot for Trades: You're opted in to account, billing & security alerts. "
    "Msg freq varies. Msg & data rates may apply. "
    "Reply HELP for help, STOP to cancel."
)

_EXPECTED_OPTOUT_REPLY = (
    "You have been unsubscribed from Pilot for Trades account alerts. "
    "No further messages will be sent. Reply START to re-subscribe."
)

_EXPECTED_HELP_REPLY = (
    "Pilot for Trades account alerts. "
    "For help, visit pilotfortrades.com or email info@pilotfortrades.com. "
    "Msg & data rates may apply. Reply STOP to unsubscribe."
)

_EXPECTED_PAYMENT_FAILED = (
    "Pilot for Trades: Your payment didn't go through. Please login to "
    "app.pilotfortrades.com and update your credit card to keep your account "
    "active. Reply STOP to opt out."
)

_ALL_EXPECTED = {
    "platform_sms_double_optin": _EXPECTED_DOUBLE_OPTIN,
    "platform_sms_optin_reply": _EXPECTED_OPTIN_REPLY,
    "platform_sms_optout_reply": _EXPECTED_OPTOUT_REPLY,
    "platform_sms_help_reply": _EXPECTED_HELP_REPLY,
    "platform_payment_failed": _EXPECTED_PAYMENT_FAILED,
}

# Files that must NOT contain _PLATFORM_ constants or inline SMS body literals.
_SOURCE_FILES = [
    "tasks/sms_compliance_platform.py",
    "api/routes/webhooks_sms.py",
]

_DELETED_CONSTANT_NAMES = [
    "_PLATFORM_DOUBLE_OPTIN_TEMPLATE",
    "_PLATFORM_OPTOUT_REPLY",
    "_PLATFORM_OPTIN_REPLY",
    "_PLATFORM_HELP_REPLY",
]


class TestVerbatimGuardrail:
    """Asserts DB rows match campaign-doc strings + no stale code constants."""

    def test_seeded_templates_match_campaign_strings(
        self, db_session, platform_sms_templates
    ):
        """Each seeded template body must match the campaign-doc constant exactly."""
        for type_code, expected_body in _ALL_EXPECTED.items():
            actual_body = get_platform_sms_body(db_session, type_code)
            assert actual_body == expected_body, (
                f"Template body mismatch for {type_code}!\n"
                f"  Expected: {expected_body!r}\n"
                f"  Actual:   {actual_body!r}\n"
                f"This is a campaign-locked string (CXXXXXX). Editing it "
                f"requires a Telnyx portal resubmission."
            )

    def test_no_deleted_constants_remain_in_source(self):
        """The four deleted _PLATFORM_ constants must not appear as code in source files.

        We check for assignment or usage patterns (``= _PLATFORM_`` or
        ``body=_PLATFORM_``), not docstring mentions — the docstring
        intentionally references the deleted constant name to explain the
        PLATFORM-SMS-B1 refactor.
        """
        import re

        backend_root = pathlib.Path(__file__).parent.parent.parent.parent
        # Pattern: the constant name used as a value (assignment, function arg,
        # or expression) — NOT inside a string/docstring. We look for it
        # preceded by ``= `` or ``(`` or `` `` (as a bare reference).
        # A simple heuristic: the name NOT inside a triple-quoted string.
        _code_ref_pattern = re.compile(
            r'(?<!["\'])('
            + "|".join(re.escape(c) for c in _DELETED_CONSTANT_NAMES)
            + r')(?!["\'])'
        )
        for rel_path in _SOURCE_FILES:
            full_path = backend_root / rel_path
            content = full_path.read_text()
            # Strip triple-quoted strings (docstrings) before checking.
            stripped = re.sub(r'""".*?"""', '""', content, flags=re.DOTALL)
            stripped = re.sub(r"'''.*?'''", "''", stripped, flags=re.DOTALL)
            for const_name in _DELETED_CONSTANT_NAMES:
                assert const_name not in stripped, (
                    f"Banned constant '{const_name}' found in code (not docstring) "
                    f"in {rel_path}. All platform SMS bodies must come from the DB "
                    f"loader (services.platform_sms_templates.get_platform_sms_body)."
                )

    def test_no_inline_sms_body_literals_in_source(self):
        """No 'Pilot for Trades:' SMS body literals in the refactored source files.

        The only place these strings should appear is in the migration, the
        seed script, and the test fixtures — NOT in the task/route code that
        was refactored to use the DB loader.
        """
        backend_root = pathlib.Path(__file__).parent.parent.parent.parent
        # The SMS body prefix that appears in all 4 of the 5 templates
        # (optout_reply is the exception — it starts with "You have been").
        sms_body_markers = [
            "Pilot for Trades: Reply YES to get important",
            "Pilot for Trades: You're opted in to account",
            "Pilot for Trades account alerts. For help",
            "Pilot for Trades: Your payment didn't go through",
        ]
        for rel_path in _SOURCE_FILES:
            full_path = backend_root / rel_path
            content = full_path.read_text()
            for marker in sms_body_markers:
                assert marker not in content, (
                    f"Inline SMS body literal found in {rel_path}: "
                    f"'{marker}'. All platform SMS bodies must be loaded "
                    f"from the DB via get_platform_sms_body()."
                )
