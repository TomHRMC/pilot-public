"""
PLATFORM-SMS-B1 — Payment-Failed Sender Test
============================================
Tests for ``tasks.sms_platform_notifications._send_platform_account_notification_sms_impl``:
  - Sends to verified+opted-in endpoints only (mixed states: opted_out,
    unverified, verified — assert only verified receives).
  - Skips when PILOT_PLATFORM_SMS_NUMBER is unset.
  - ``handle_invoice_payment_failed`` enqueues the task (patches .delay).

Domain: notifications_comms (PRD §3.7)
"""

import hashlib
import uuid
from unittest.mock import MagicMock, patch

import pytest
from sqlmodel import select

from app.models.auth import TenantUser
from app.models.core import User
from services.notification_endpoints import upsert_owner_sms_endpoint

pytestmark = [
    pytest.mark.domain_notifications_comms,
    pytest.mark.unit,
]

# tenant_user_status.code='active' id (MCP-verified, seeded platform row).
_ACTIVE_STATUS_ID = "5b67cfd3-ef42-4311-9516-a4eec8642628"


def _make_owner_with_endpoint(
    db_session,
    test_tenant,
    phone,
    consent=True,
    verification_status="pending",
    consent_status=None,
):
    """Create a fresh owner user + TenantUser + sms user_endpoint in a specific state."""
    user = User(
        id=uuid.uuid4(),
        email=f"owner-{uuid.uuid4().hex[:8]}@test.local",
        first_name="Owner",
        last_name="Test",
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()

    db_session.add(
        TenantUser(
            tenant_id=test_tenant.id,
            user_id=user.id,
            role_code="owner",
            status_id=_ACTIVE_STATUS_ID,
            is_active=True,
        )
    )
    db_session.flush()

    # Create the endpoint via upsert, then override the verification/consent
    # state if needed for the test scenario.
    endpoint = upsert_owner_sms_endpoint(
        db_session,
        user_id=user.id,
        tenant_id=test_tenant.id,
        phone=phone,
        consent=consent,
        ip="127.0.0.1",
        disclosure_hash=hashlib.sha256(b"d").hexdigest(),
    )

    if verification_status != "pending" or consent_status is not None:
        endpoint.verification_status = verification_status
        if consent_status is not None:
            endpoint.consent_status = consent_status
        db_session.add(endpoint)

    db_session.commit()
    return user, endpoint


class TestPaymentFailedSender:
    """Tests for the _impl function (called without .delay())."""

    def test_sends_to_verified_opted_in_only(
        self, db_session, test_tenant, platform_sms_templates
    ):
        """Only verified+opted-in endpoints receive the SMS."""
        from tasks.sms_platform_notifications import (
            _send_platform_account_notification_sms_impl,
        )

        # Create 3 owners with different endpoint states:
        # 1. verified + opted_in → should receive
        user_verified, _ = _make_owner_with_endpoint(
            db_session,
            test_tenant,
            "+15125550601",
            consent=True,
            verification_status="verified",
            consent_status="opted_in",
        )
        # 2. opted_out → should NOT receive
        _user_opted_out, _ = _make_owner_with_endpoint(
            db_session,
            test_tenant,
            "+15125550602",
            consent=True,
            verification_status="verified",
            consent_status="opted_out",
        )
        # 3. unverified (pending) → should NOT receive
        _user_unverified, _ = _make_owner_with_endpoint(
            db_session,
            test_tenant,
            "+15125550603",
            consent=True,
            verification_status="pending",
            consent_status="opted_in",
        )

        mock_carrier = MagicMock()
        mock_carrier.send_message.return_value = MagicMock(
            status="sent", carrier_message_id="mock-id", error_message=None
        )

        with (
            patch(
                "tasks.sms_platform_notifications.get_sms_carrier",
                return_value=mock_carrier,
            ),
            patch("tasks.sms_platform_notifications.Session") as mock_session_cls,
            patch("core.config.settings.PILOT_PLATFORM_SMS_NUMBER", "+15125559999"),
        ):
            mock_session_cls.return_value.__enter__.return_value = db_session
            result = _send_platform_account_notification_sms_impl(
                str(test_tenant.id), "platform_payment_failed"
            )

        assert result["status"] == "sent"
        assert result["sent_count"] == 1
        assert len(result["results"]) == 1
        assert result["results"][0]["user_id"] == str(user_verified.id)

        # Carrier was called exactly once (only the verified endpoint).
        assert mock_carrier.send_message.call_count == 1
        call_kwargs = mock_carrier.send_message.call_args.kwargs
        assert call_kwargs["from_number"] == "+15125559999"
        assert call_kwargs["to_number"] == "+15125550601"
        assert "payment didn't go through" in call_kwargs["body"]

    def test_skips_when_no_verified_endpoints(
        self, db_session, test_tenant, platform_sms_templates
    ):
        """Returns skipped when no verified+opted-in endpoints exist."""
        from tasks.sms_platform_notifications import (
            _send_platform_account_notification_sms_impl,
        )

        # Create an owner with an unverified endpoint.
        _make_owner_with_endpoint(
            db_session,
            test_tenant,
            "+15125550610",
            consent=True,
            verification_status="pending",
        )

        mock_carrier = MagicMock()

        with (
            patch(
                "tasks.sms_platform_notifications.get_sms_carrier",
                return_value=mock_carrier,
            ),
            patch("tasks.sms_platform_notifications.Session") as mock_session_cls,
            patch("core.config.settings.PILOT_PLATFORM_SMS_NUMBER", "+15125559999"),
        ):
            mock_session_cls.return_value.__enter__.return_value = db_session
            result = _send_platform_account_notification_sms_impl(
                str(test_tenant.id), "platform_payment_failed"
            )

        assert result["status"] == "skipped"
        assert result["reason"] == "no_verified_endpoints"
        assert result["sent_count"] == 0
        mock_carrier.send_message.assert_not_called()

    def test_skips_when_platform_number_unset(
        self, db_session, test_tenant, platform_sms_templates
    ):
        """Returns skipped when PILOT_PLATFORM_SMS_NUMBER is not configured."""
        from tasks.sms_platform_notifications import (
            _send_platform_account_notification_sms_impl,
        )

        # Create a verified+opted-in owner.
        _make_owner_with_endpoint(
            db_session,
            test_tenant,
            "+15125550620",
            consent=True,
            verification_status="verified",
            consent_status="opted_in",
        )

        mock_carrier = MagicMock()

        with (
            patch(
                "tasks.sms_platform_notifications.get_sms_carrier",
                return_value=mock_carrier,
            ),
            patch("tasks.sms_platform_notifications.Session") as mock_session_cls,
            patch("core.config.settings.PILOT_PLATFORM_SMS_NUMBER", ""),
        ):
            mock_session_cls.return_value.__enter__.return_value = db_session
            result = _send_platform_account_notification_sms_impl(
                str(test_tenant.id), "platform_payment_failed"
            )

        assert result["status"] == "skipped"
        assert result["reason"] == "no_platform_from_number"
        assert result["sent_count"] == 0
        mock_carrier.send_message.assert_not_called()


class TestHandleInvoicePaymentFailedWiring:
    """Tests that handle_invoice_payment_failed enqueues the task."""

    def test_enqueues_platform_sms_task(self, db_session, test_tenant):
        """handle_invoice_payment_failed calls .delay with the right args."""
        # The tenant must have a stripe_customer_id for the handler to find it.
        from app.models.core import Tenant
        from services.stripe_subscriptions import handle_invoice_payment_failed

        tenant = db_session.exec(
            select(Tenant).where(Tenant.id == test_tenant.id)
        ).first()
        if tenant:
            tenant.stripe_customer_id = "cus_test_payment_failed"
            db_session.add(tenant)
            db_session.commit()

        stripe_event = {
            "data": {
                "object": {
                    "customer": "cus_test_payment_failed",
                    "attempt_count": 1,
                }
            }
        }

        with patch(
            "tasks.sms_platform_notifications.send_platform_account_notification_sms.delay"
        ) as mock_delay:
            handle_invoice_payment_failed(db_session, stripe_event)

        mock_delay.assert_called_once_with(
            tenant_id=str(test_tenant.id),
            type_code="platform_payment_failed",
        )
