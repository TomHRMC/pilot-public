"""
SD-08 Template Copy Sanity Tests
Domain: Notifications & Communications

Verifies that email_template and notification_template rows in the live DB
have been updated from stub copy to approved v1 copy after the Alembic
migration 4a2fbda323db ran.

Tests assert that the OLD stub text is absent — not that the exact new copy is
present (copy may be iterated without requiring a new migration).
"""

import pytest
from sqlalchemy import text

pytestmark = [
    pytest.mark.domain_notifications_comms,
    pytest.mark.unit,
]

# Old stub values that should no longer exist after SD-08 migration
_OLD_STUBS = {
    "invoice_sent": "<p>Your invoice is ready.</p>",
    "quote_sent": "<p>Please review your quote.</p>",
    "payment_received_customer": "<p>Thank you for your payment.</p>",
    "quote_expiring": "<p>Your quote expires in 3 days.</p>",
    "payment_failed": "<p>Your payment could not be processed.</p>",
}

_NOTIFICATION_STUB_PREFIX = "This is a placeholder"


class TestSD08EmailTemplateCopy:
    """Verify customer-facing email templates no longer have stub copy."""

    def test_invoice_sent_template_not_stub(self, db_session):
        """invoice_sent body_html_template must not contain the old stub."""
        result = db_session.execute(
            text("""
                SELECT body_html_template, subject_template, variables
                FROM public.email_template
                WHERE template_id = 'invoice_sent'
            """)
        ).first()
        assert result is not None, "invoice_sent email_template row not found"
        assert _OLD_STUBS["invoice_sent"] not in result.body_html_template, (
            "invoice_sent still has old stub body — SD-08 migration may not have run"
        )
        # Subject must have been updated with dynamic variables
        assert "{{invoice_total}}" in result.subject_template
        assert "{{due_date}}" in result.subject_template

    def test_quote_sent_template_not_stub(self, db_session):
        """quote_sent body_html_template must not contain the old stub."""
        result = db_session.execute(
            text("""
                SELECT body_html_template, subject_template
                FROM public.email_template
                WHERE template_id = 'quote_sent'
            """)
        ).first()
        assert result is not None, "quote_sent email_template row not found"
        assert _OLD_STUBS["quote_sent"] not in result.body_html_template, (
            "quote_sent still has old stub body — SD-08 migration may not have run"
        )
        assert "{{quote_total}}" in result.subject_template

    def test_payment_received_customer_template_not_stub(self, db_session):
        """payment_received_customer body_html_template must not contain the old stub."""
        result = db_session.execute(
            text("""
                SELECT body_html_template, subject_template
                FROM public.email_template
                WHERE template_id = 'payment_received_customer'
            """)
        ).first()
        assert result is not None, (
            "payment_received_customer email_template row not found"
        )
        assert _OLD_STUBS["payment_received_customer"] not in result.body_html_template
        assert "{{amount}}" in result.subject_template

    def test_quote_expiring_template_not_stub(self, db_session):
        """quote_expiring body_html_template must not contain the hardcoded '3 days' stub."""
        result = db_session.execute(
            text("""
                SELECT body_html_template, subject_template
                FROM public.email_template
                WHERE template_id = 'quote_expiring'
            """)
        ).first()
        assert result is not None, "quote_expiring email_template row not found"
        assert _OLD_STUBS["quote_expiring"] not in result.body_html_template
        # Subject must use the dynamic {{expires_at}} variable (not hardcoded "3 days")
        assert "{{expires_at}}" in result.subject_template

    def test_payment_failed_template_not_stub(self, db_session):
        """payment_failed body_html_template must not contain the old stub."""
        result = db_session.execute(
            text("""
                SELECT body_html_template, subject_template
                FROM public.email_template
                WHERE template_id = 'payment_failed'
            """)
        ).first()
        assert result is not None, "payment_failed email_template row not found"
        assert _OLD_STUBS["payment_failed"] not in result.body_html_template
        assert "{{company_name}}" in result.subject_template

    def test_customer_facing_templates_have_variables(self, db_session):
        """All 5 customer-facing email_template rows must have non-empty variables JSONB arrays."""
        customer_template_ids = [
            "invoice_sent",
            "quote_sent",
            "payment_received_customer",
            "quote_expiring",
            "payment_failed",
        ]
        results = db_session.execute(
            text("""
                SELECT template_id, variables
                FROM public.email_template
                WHERE template_id = ANY(:ids) AND category = 'customer_facing'
                ORDER BY template_id
            """),
            {"ids": customer_template_ids},
        ).fetchall()

        assert len(results) == 5, (
            f"Expected 5 customer-facing templates, found {len(results)}"
        )
        for row in results:
            assert row.variables is not None, f"{row.template_id} has NULL variables"
            # variables is a JSONB array — should have at least 1 element
            assert len(row.variables) > 0, (
                f"{row.template_id} has empty variables array"
            )

    def test_invoice_sent_variables_include_new_fields(self, db_session):
        """invoice_sent variables must include due_date and company_domain (added in SD-08)."""
        result = db_session.execute(
            text("""
                SELECT variables FROM public.email_template WHERE template_id = 'invoice_sent'
            """)
        ).first()
        assert result is not None
        var_list = result.variables  # JSONB returns as Python list
        assert "due_date" in var_list, "due_date not in invoice_sent variables"
        assert "company_domain" in var_list, (
            "company_domain not in invoice_sent variables"
        )

    def test_payment_failed_variables_include_company_fields(self, db_session):
        """payment_failed variables must include company_name and company_domain (added in SD-08)."""
        result = db_session.execute(
            text("""
                SELECT variables FROM public.email_template WHERE template_id = 'payment_failed'
            """)
        ).first()
        assert result is not None
        var_list = result.variables
        assert "company_name" in var_list, (
            "company_name not in payment_failed variables"
        )
        assert "company_domain" in var_list, (
            "company_domain not in payment_failed variables"
        )


class TestSD08NotificationTemplateCopy:
    """Verify notification_template rows no longer have placeholder body strings."""

    def test_dunning_reminder_notification_not_stub(self, db_session):
        """dunning_reminder notification_template bodies must not contain placeholder prefix."""
        results = db_session.execute(
            text("""
                SELECT channel, body FROM public.notification_template
                WHERE notification_type_code = 'dunning_reminder'
                  AND tenant_id IS NULL
                ORDER BY channel
            """)
        ).fetchall()
        assert len(results) > 0, "No dunning_reminder notification_template rows found"
        for row in results:
            assert _NOTIFICATION_STUB_PREFIX not in row.body, (
                f"dunning_reminder/{row.channel} still has placeholder body — "
                "SD-08 migration may not have run"
            )

    def test_quote_accepted_notification_not_stub(self, db_session):
        """quote_accepted notification_template bodies must not contain placeholder prefix."""
        results = db_session.execute(
            text("""
                SELECT channel, body FROM public.notification_template
                WHERE notification_type_code = 'quote_accepted'
                  AND tenant_id IS NULL
                ORDER BY channel
            """)
        ).fetchall()
        assert len(results) > 0, "No quote_accepted notification_template rows found"
        for row in results:
            assert _NOTIFICATION_STUB_PREFIX not in row.body, (
                f"quote_accepted/{row.channel} still has placeholder body"
            )

    def test_customer_communication_sent_notification_not_stub(self, db_session):
        """customer_communication_sent notification_template bodies must not be placeholders."""
        results = db_session.execute(
            text("""
                SELECT channel, body FROM public.notification_template
                WHERE notification_type_code = 'customer_communication_sent'
                  AND tenant_id IS NULL
                ORDER BY channel
            """)
        ).fetchall()
        assert len(results) > 0, (
            "No customer_communication_sent notification_template rows found"
        )
        for row in results:
            assert _NOTIFICATION_STUB_PREFIX not in row.body, (
                f"customer_communication_sent/{row.channel} still has placeholder body"
            )

    def test_dunning_reminder_email_body_has_variables(self, db_session):
        """dunning_reminder email body must reference invoice and amount variables."""
        result = db_session.execute(
            text("""
                SELECT body FROM public.notification_template
                WHERE notification_type_code = 'dunning_reminder'
                  AND channel = 'email' AND tenant_id IS NULL
            """)
        ).first()
        assert result is not None, (
            "dunning_reminder/email notification_template not found"
        )
        assert "{{invoice_number}}" in result.body
        assert "{{amount_due}}" in result.body

    def test_quote_accepted_in_app_body_has_customer_name(self, db_session):
        """quote_accepted in_app body must reference {{customer_name}}."""
        result = db_session.execute(
            text("""
                SELECT body FROM public.notification_template
                WHERE notification_type_code = 'quote_accepted'
                  AND channel = 'in_app' AND tenant_id IS NULL
            """)
        ).first()
        assert result is not None, (
            "quote_accepted/in_app notification_template not found"
        )
        assert "{{customer_name}}" in result.body
