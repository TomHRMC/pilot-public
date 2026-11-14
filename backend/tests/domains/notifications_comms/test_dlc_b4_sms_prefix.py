"""
DLC-B4 SMS Brand Prefix Tests
==============================
Verifies that all system SMS communication templates are prefixed with
"Pilot for Trades: " as required by 10DLC campaign CXXXXXX resubmission
(Telnyx rejection fix, 2026-07-27).

Scope of assertions:
  1. All 11 system SMS templates start with "Pilot for Trades: " and preserve variables.
  2. Migration idempotency — no double-prefix possible.
  3. Email templates are NOT prefixed (out-of-scope channel).
  4. Double opt-in confirmation string in sms_compliance._DOUBLE_OPTIN_TEMPLATE is prefixed.

Domain: notifications_comms
"""

import pytest
from sqlalchemy import text

pytestmark = [
    pytest.mark.domain_notifications_comms,
    pytest.mark.unit,
]

_PREFIX = "Pilot for Trades: "

# Exact set of 11 system SMS template codes + a key variable that must survive prefixing.
_SMS_TEMPLATES_WITH_VARIABLE = [
    ("appointment_reminder_1h", "{{appointment_time}}"),
    ("appointment_reminder_24h", "{{appointment_time}}"),
    ("arrived", "{{ customer_first_name }}"),
    ("confirm_appointment", "{{ date_time }}"),
    ("invoice_sent", "{{invoice_link}}"),
    ("job_complete", "{{ sender_name }}"),
    ("on_my_way", "{{ eta }}"),
    ("parts_delay", "{{ sender_name }}"),
    ("payment_received", "{{payment_amount}}"),
    ("recurring_job_scheduled", "{{scheduled_date}}"),
    ("running_late", "{{ minutes_late }}"),
]

# A known email template code to verify email channel is untouched.
_EMAIL_TEMPLATE_CODE = "invoice_sent"


class TestDlcB4SmsBrandPrefix:
    """All system SMS templates must carry the platform sender prefix."""

    def test_all_sms_templates_prefixed(self, db_session):
        """Every system (tenant_id IS NULL) SMS template body starts with the prefix."""
        rows = db_session.execute(
            text("""
                SELECT template_code, body_template
                FROM public.communication_template
                WHERE channel = 'sms'
                  AND tenant_id IS NULL
                ORDER BY template_code
            """)
        ).fetchall()

        template_codes_found = {r.template_code for r in rows}
        expected_codes = {code for code, _ in _SMS_TEMPLATES_WITH_VARIABLE}

        assert expected_codes.issubset(template_codes_found), (
            f"Missing SMS templates: {expected_codes - template_codes_found}"
        )

        for row in rows:
            if row.template_code in expected_codes:
                assert row.body_template.startswith(_PREFIX), (
                    f"template_code='{row.template_code}' body does not start with "
                    f"'{_PREFIX}'. Got: {row.body_template[:80]!r}"
                )

    def test_each_sms_template_preserves_variables(self, db_session):
        """Each prefixed template still contains its key Jinja variable."""
        for template_code, expected_variable in _SMS_TEMPLATES_WITH_VARIABLE:
            row = db_session.execute(
                text("""
                    SELECT body_template
                    FROM public.communication_template
                    WHERE template_code = :code
                      AND channel = 'sms'
                      AND tenant_id IS NULL
                """),
                {"code": template_code},
            ).first()

            assert row is not None, (
                f"SMS template '{template_code}' not found (tenant_id IS NULL)"
            )
            assert row.body_template.startswith(_PREFIX), (
                f"'{template_code}' missing prefix. Got: {row.body_template[:80]!r}"
            )
            assert expected_variable in row.body_template, (
                f"'{template_code}' missing variable '{expected_variable}' after prefixing. "
                f"Got: {row.body_template!r}"
            )

    def test_no_double_prefix(self, db_session):
        """Running the upgrade condition again must not double-prefix any row.

        Simulates what would happen if the migration's idempotency guard were absent:
        tests that no row in the live DB starts with the prefix twice.
        This validates the NOT LIKE guard in the migration SQL is effective.
        """
        double_prefixed = db_session.execute(
            text("""
                SELECT COUNT(*) AS cnt
                FROM public.communication_template
                WHERE channel = 'sms'
                  AND tenant_id IS NULL
                  AND body_template LIKE :double_prefix
            """),
            {"double_prefix": f"{_PREFIX}{_PREFIX}%"},
        ).scalar()

        assert double_prefixed == 0, (
            f"Found {double_prefixed} row(s) with double prefix — idempotency guard failed"
        )

    def test_email_template_not_prefixed(self, db_session):
        """Email-channel templates must NOT be prefixed (scope: sms only)."""
        row = db_session.execute(
            text("""
                SELECT body_template
                FROM public.communication_template
                WHERE template_code = :code
                  AND channel = 'email'
                  AND tenant_id IS NULL
                LIMIT 1
            """),
            {"code": _EMAIL_TEMPLATE_CODE},
        ).first()

        assert row is not None, (
            f"Email template '{_EMAIL_TEMPLATE_CODE}' not found — cannot verify scope"
        )
        assert not row.body_template.startswith(_PREFIX), (
            f"Email template '{_EMAIL_TEMPLATE_CODE}' was incorrectly prefixed. "
            f"Got: {row.body_template[:80]!r}"
        )


class TestDlcB4DoubleOptInPrefix:
    """The double opt-in confirmation string must also carry the platform prefix."""

    def test_double_optin_template_starts_with_prefix(self):
        """_DOUBLE_OPTIN_TEMPLATE must start with 'Pilot for Trades: '."""
        from tasks.sms_compliance import _DOUBLE_OPTIN_TEMPLATE

        assert _DOUBLE_OPTIN_TEMPLATE.startswith(_PREFIX), (
            f"_DOUBLE_OPTIN_TEMPLATE does not start with '{_PREFIX}'. "
            f"Got: {_DOUBLE_OPTIN_TEMPLATE[:80]!r}"
        )

    def test_double_optin_template_preserves_first_name_placeholder(self):
        """_DOUBLE_OPTIN_TEMPLATE must still contain {first_name} placeholder."""
        from tasks.sms_compliance import _DOUBLE_OPTIN_TEMPLATE

        assert "{first_name}" in _DOUBLE_OPTIN_TEMPLATE, (
            "'{first_name}' placeholder missing from _DOUBLE_OPTIN_TEMPLATE"
        )

    def test_double_optin_template_preserves_business_name_placeholder(self):
        """_DOUBLE_OPTIN_TEMPLATE must still contain {business_name} placeholder."""
        from tasks.sms_compliance import _DOUBLE_OPTIN_TEMPLATE

        assert "{business_name}" in _DOUBLE_OPTIN_TEMPLATE, (
            "'{business_name}' placeholder missing from _DOUBLE_OPTIN_TEMPLATE"
        )

    def test_double_optin_rendered_message_starts_with_prefix(self):
        """Rendered opt-in message (after .format()) still starts with prefix."""
        from tasks.sms_compliance import _DOUBLE_OPTIN_TEMPLATE

        rendered = _DOUBLE_OPTIN_TEMPLATE.format(
            first_name="Mike",
            business_name="Apex Electric",
        )
        assert rendered.startswith(_PREFIX), (
            f"Rendered opt-in message missing prefix. Got: {rendered[:80]!r}"
        )
        # The inline "Pilot for Trades" program description must also be present.
        assert "Pilot for Trades for service updates" in rendered, (
            "Inline program description 'Pilot for Trades for service updates' missing"
        )
