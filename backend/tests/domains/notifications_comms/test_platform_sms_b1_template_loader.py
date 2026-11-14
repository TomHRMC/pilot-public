"""
PLATFORM-SMS-B1 — Template Loader Test
======================================
Tests for ``services.platform_sms_templates.get_platform_sms_body()``:
  - Returns the body for an active row.
  - Raises ``PlatformSmsTemplateMissingError`` for a missing type code.
  - Raises for an ``is_active=false`` row.
  - Ignores tenant-scoped rows (only system rows with tenant_id IS NULL).

Domain: notifications_comms (PRD §3.7)
"""

import uuid

import pytest
from sqlalchemy import text

from services.platform_sms_templates import (
    PlatformSmsTemplateMissingError,
    get_platform_sms_body,
)

pytestmark = [
    pytest.mark.domain_notifications_comms,
    pytest.mark.unit,
]


class TestPlatformSmsTemplateLoader:
    """Tests for the fail-loud DB template loader."""

    def test_returns_body_for_active_row(self, db_session, platform_sms_templates):
        """Loader returns the correct body for an active system sms template."""
        body = get_platform_sms_body(db_session, "platform_sms_double_optin")
        assert "Reply YES to get important account" in body
        assert body == platform_sms_templates["platform_sms_double_optin"]

    def test_returns_body_for_payment_failed(self, db_session, platform_sms_templates):
        """Loader returns the payment-failed body."""
        body = get_platform_sms_body(db_session, "platform_payment_failed")
        assert "payment didn't go through" in body
        assert body == platform_sms_templates["platform_payment_failed"]

    def test_raises_for_missing_type_code(self, db_session, platform_sms_templates):
        """Loader raises PlatformSmsTemplateMissingError for a non-existent type code."""
        with pytest.raises(PlatformSmsTemplateMissingError):
            get_platform_sms_body(db_session, "platform_sms_nonexistent")

    def test_raises_for_inactive_row(self, db_session, platform_sms_templates):
        """Loader raises when the template row exists but is_active=false."""
        # Deactivate the double_optin template.
        db_session.execute(
            text(
                """
                UPDATE public.notification_template
                SET is_active = false
                WHERE notification_type_code = 'platform_sms_double_optin'
                  AND channel = 'sms'
                  AND tenant_id IS NULL
                """
            )
        )
        db_session.commit()

        with pytest.raises(PlatformSmsTemplateMissingError):
            get_platform_sms_body(db_session, "platform_sms_double_optin")

    def test_ignores_tenant_scoped_rows(
        self, db_session, test_tenant, platform_sms_templates
    ):
        """Loader only reads system rows (tenant_id IS NULL), not tenant-scoped rows."""
        # Insert a tenant-scoped row with a different body for the same type code.
        # Use the test_tenant fixture so the FK constraint is satisfied.
        db_session.execute(
            text(
                """
                INSERT INTO public.notification_template
                    (id, tenant_id, notification_type_code, channel, locale,
                     subject, body, is_active, created_at, updated_at)
                VALUES
                    (:id, :tenant_id, 'platform_sms_double_optin', 'sms', 'en',
                     NULL, 'TENANT-SPECIFIC BODY — should be ignored', true,
                     NOW(), NOW())
                """
            ),
            {"id": str(uuid.uuid4()), "tenant_id": str(test_tenant.id)},
        )
        db_session.commit()

        # Loader must return the SYSTEM row body, not the tenant-scoped one.
        body = get_platform_sms_body(db_session, "platform_sms_double_optin")
        assert body == platform_sms_templates["platform_sms_double_optin"]
        assert "TENANT-SPECIFIC BODY" not in body
