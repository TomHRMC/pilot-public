"""
C-B4: Tests for report_usage_event() — Billing Meter event reporting.
Domain: subscriptions_usage (PRD §3.11)
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
from sqlmodel import select

pytestmark = [
    pytest.mark.domain_subscriptions_usage,
    pytest.mark.unit,
]


class TestReportUsageEvent:
    """Tests for report_usage_event() with mocked Stripe."""

    def test_meter_event_created_with_identifier(self, db_session, test_tenant):
        """MeterEvent.create is called with event_name, identifier, payload, timestamp."""
        from app.models.core import Tenant
        from services.stripe_subscriptions import report_usage_event

        # Set stripe_customer_id on the test tenant
        tenant = db_session.exec(
            select(Tenant).where(Tenant.id == test_tenant.id)
        ).first()
        tenant.stripe_customer_id = "cus_test_usage"
        db_session.add(tenant)
        db_session.commit()

        ts = datetime(2026, 8, 4, 12, 0, 0, tzinfo=UTC)

        with patch("services.stripe_subscriptions._get_stripe_client") as mock_client:
            mock_stripe = MagicMock()
            mock_client.return_value = mock_stripe

            report_usage_event(
                db=db_session,
                tenant_id=test_tenant.id,
                event_name="voice_minutes",
                identifier="voice_session_123",
                value=5,
                timestamp=ts,
            )

        mock_stripe.billing.MeterEvent.create.assert_called_once_with(
            event_name="voice_minutes",
            identifier="voice_session_123",
            payload={
                "stripe_customer_id": "cus_test_usage",
                "value": "5",
            },
            timestamp=int(ts.timestamp()),
        )

    def test_missing_stripe_customer_id_skips_silently(self, db_session, test_tenant):
        """Tenant with no stripe_customer_id → logs warning, returns None, no Stripe call."""
        from app.models.core import Tenant
        from services.stripe_subscriptions import report_usage_event

        # Ensure tenant has no stripe_customer_id
        tenant = db_session.exec(
            select(Tenant).where(Tenant.id == test_tenant.id)
        ).first()
        tenant.stripe_customer_id = None
        db_session.add(tenant)
        db_session.commit()

        with patch("services.stripe_subscriptions._get_stripe_client") as mock_client:
            mock_stripe = MagicMock()
            mock_client.return_value = mock_stripe

            report_usage_event(
                db=db_session,
                tenant_id=test_tenant.id,
                event_name="sms_segments",
                identifier="sms_msg_456",
                value=3,
                timestamp=datetime.now(UTC),
            )

        # No Stripe API call made
        mock_stripe.billing.MeterEvent.create.assert_not_called()

    def test_stripe_error_is_non_blocking(self, db_session, test_tenant):
        """Stripe API error is caught, logged, and does not raise."""
        from app.models.core import Tenant
        from services.stripe_subscriptions import report_usage_event

        tenant = db_session.exec(
            select(Tenant).where(Tenant.id == test_tenant.id)
        ).first()
        tenant.stripe_customer_id = "cus_test_usage_err"
        db_session.add(tenant)
        db_session.commit()

        with patch("services.stripe_subscriptions._get_stripe_client") as mock_client:
            mock_stripe = MagicMock()
            mock_stripe.billing.MeterEvent.create.side_effect = Exception(
                "Stripe unavailable"
            )
            mock_client.return_value = mock_stripe

            # Should NOT raise — non-blocking
            report_usage_event(
                db=db_session,
                tenant_id=test_tenant.id,
                event_name="voice_minutes",
                identifier="voice_session_789",
                value=10,
                timestamp=datetime.now(UTC),
            )
