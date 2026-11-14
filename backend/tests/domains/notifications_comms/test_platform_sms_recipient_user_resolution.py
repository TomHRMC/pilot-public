"""
PLP-FIX-8 — User-Scoped SMS Recipient Resolution Tests
=====================================================
Tests for ``tasks.sms_platform_notifications._send_platform_account_notification_sms_impl``
with the new ``recipient_user_id`` parameter (PLP-FIX-8 / INV-BUG-4):

  (a) ``recipient_user_id`` present → only that user's verified+opted-in SMS
      endpoint receives (build a matrix: target verified+opted-in, target
      opted-out, target unverified, OTHER tenant user verified+opted-in —
      assert ONLY the first is sent).
  (b) ``recipient_user_id`` absent → legacy owner fan-out unchanged
      (regression — all verified+opted-in owners receive).
  (c) target user with no verified+opted-in endpoint → quiet skip, no send,
      no exception.

Domain: notifications_comms (PRD §3.7)
"""

import hashlib
import uuid
from unittest.mock import MagicMock, patch

import pytest

from app.models.auth import TenantUser
from app.models.core import User
from services.notification_endpoints import upsert_owner_sms_endpoint

pytestmark = [
    pytest.mark.domain_notifications_comms,
    pytest.mark.unit,
]

# tenant_user_status.code='active' id (MCP-verified, seeded platform row).
_ACTIVE_STATUS_ID = "5b67cfd3-ef42-4311-9516-a4eec8642628"


def _make_user_with_endpoint(
    db_session,
    test_tenant,
    phone,
    role_code="technician",
    consent=True,
    verification_status="pending",
    consent_status=None,
):
    """Create a fresh user + TenantUser + sms user_endpoint in a specific state.

    Defaults to ``technician`` role — the PLP-FIX-8 use case is an employee
    (technician/office_staff) signing in from a new device.
    """
    user = User(
        id=uuid.uuid4(),
        email=f"fix8-{uuid.uuid4().hex[:8]}@test.local",
        first_name="Test",
        last_name="User",
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()

    db_session.add(
        TenantUser(
            tenant_id=test_tenant.id,
            user_id=user.id,
            role_code=role_code,
            status_id=_ACTIVE_STATUS_ID,
            is_active=True,
        )
    )
    db_session.flush()

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


def _run_impl(db_session, test_tenant, type_code, recipient_user_id=None):
    """Call _impl with the carrier-mock + Session-patch pattern."""
    from tasks.sms_platform_notifications import (
        _send_platform_account_notification_sms_impl,
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
            str(test_tenant.id),
            type_code,
            recipient_user_id=recipient_user_id,
        )
    return result, mock_carrier


class TestUserScopedRecipientResolution:
    """(a) recipient_user_id present → only that user's verified+opted-in endpoint."""

    def test_only_target_user_receives(
        self, db_session, test_tenant, platform_sms_templates
    ):
        """Matrix: target verified+opted-in, target opted-out, target unverified,
        OTHER user verified+opted-in — assert ONLY the first is sent."""
        # 1. Target user — verified + opted_in → SHOULD receive.
        target_user, _ = _make_user_with_endpoint(
            db_session,
            test_tenant,
            "+15125550801",
            role_code="technician",
            consent=True,
            verification_status="verified",
            consent_status="opted_in",
        )

        # 2. Another user in the SAME tenant — verified + opted_in → should NOT
        #    receive (user-scoped resolution, not owner fan-out).
        _other_user, _ = _make_user_with_endpoint(
            db_session,
            test_tenant,
            "+15125550802",
            role_code="owner",
            consent=True,
            verification_status="verified",
            consent_status="opted_in",
        )

        result, mock_carrier = _run_impl(
            db_session,
            test_tenant,
            "platform_security_new_device",
            recipient_user_id=str(target_user.id),
        )

        assert result["status"] == "sent"
        assert result["sent_count"] == 1
        assert len(result["results"]) == 1
        assert result["results"][0]["user_id"] == str(target_user.id)

        # Carrier called exactly once — only the target user's endpoint.
        assert mock_carrier.send_message.call_count == 1
        call_kwargs = mock_carrier.send_message.call_args.kwargs
        assert call_kwargs["to_number"] == "+15125550801"
        assert call_kwargs["from_number"] == "+15125559999"

    def test_target_opted_out_not_sent(
        self, db_session, test_tenant, platform_sms_templates
    ):
        """Target user with opted_out consent → no send (consent gate holds)."""
        target_user, _ = _make_user_with_endpoint(
            db_session,
            test_tenant,
            "+15125550810",
            role_code="technician",
            consent=True,
            verification_status="verified",
            consent_status="opted_out",
        )

        result, mock_carrier = _run_impl(
            db_session,
            test_tenant,
            "platform_security_new_device",
            recipient_user_id=str(target_user.id),
        )

        assert result["status"] == "skipped"
        assert result["reason"] == "no_verified_endpoints"
        assert result["sent_count"] == 0
        mock_carrier.send_message.assert_not_called()

    def test_target_unverified_not_sent(
        self, db_session, test_tenant, platform_sms_templates
    ):
        """Target user with pending verification → no send (verification gate holds)."""
        target_user, _ = _make_user_with_endpoint(
            db_session,
            test_tenant,
            "+15125550820",
            role_code="technician",
            consent=True,
            verification_status="pending",
            consent_status="opted_in",
        )

        result, mock_carrier = _run_impl(
            db_session,
            test_tenant,
            "platform_security_new_device",
            recipient_user_id=str(target_user.id),
        )

        assert result["status"] == "skipped"
        assert result["reason"] == "no_verified_endpoints"
        assert result["sent_count"] == 0
        mock_carrier.send_message.assert_not_called()


class TestLegacyOwnerFanOutRegression:
    """(b) recipient_user_id absent → legacy owner fan-out unchanged."""

    def test_absent_kwarg_fans_out_to_owners(
        self, db_session, test_tenant, platform_sms_templates
    ):
        """recipient_user_id=None → all verified+opted-in owners receive
        (regression — the two existing callers' behavior is unchanged)."""
        # Create a verified+opted-in owner.
        owner_user, _ = _make_user_with_endpoint(
            db_session,
            test_tenant,
            "+15125550830",
            role_code="owner",
            consent=True,
            verification_status="verified",
            consent_status="opted_in",
        )

        result, mock_carrier = _run_impl(
            db_session,
            test_tenant,
            "platform_payment_failed",
            recipient_user_id=None,
        )

        assert result["status"] == "sent"
        assert result["sent_count"] == 1
        assert result["results"][0]["user_id"] == str(owner_user.id)
        assert mock_carrier.send_message.call_count == 1


class TestNoEndpointsQuietSkip:
    """(c) target user with no verified+opted-in endpoint → quiet skip."""

    def test_target_no_verified_endpoint_quiet_skip(
        self, db_session, test_tenant, platform_sms_templates
    ):
        """Target user exists but has no verified+opted-in endpoint → skipped,
        no exception, no carrier call."""
        target_user, _ = _make_user_with_endpoint(
            db_session,
            test_tenant,
            "+15125550840",
            role_code="technician",
            consent=False,
            verification_status="pending",
            consent_status="unknown",
        )

        result, mock_carrier = _run_impl(
            db_session,
            test_tenant,
            "platform_security_new_device",
            recipient_user_id=str(target_user.id),
        )

        assert result["status"] == "skipped"
        assert result["reason"] == "no_verified_endpoints"
        assert result["sent_count"] == 0
        mock_carrier.send_message.assert_not_called()
