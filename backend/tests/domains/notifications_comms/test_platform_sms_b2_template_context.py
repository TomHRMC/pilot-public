"""
PLATFORM-SMS-B2 — template_context Render Test
=============================================
Tests for ``tasks.sms_platform_notifications._send_platform_account_notification_sms_impl``
with the new ``template_context`` parameter (PLATFORM-SMS-B2):

  1. ``template_context=None`` on ``platform_security_new_device`` → carrier
     receives the raw stored body (B1 regression — static body used verbatim).
  2. ``template_context={"maint_date": ..., "maint_window": ...}`` on
     ``platform_maintenance_broadcast`` → carrier receives the rendered body;
     the provided values appear and no ``{{`` remains.
  3. Registered-values integration: context = the registered values → carrier
     body == registered Sample 4 constant byte-for-byte (en-dash U+2013).

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

# Registered Sample 4 render values (en-dash U+2013 in the window).
_REGISTERED_MAINT_DATE = "Sun 08-02-2026"
_REGISTERED_MAINT_WINDOW = "2:00–3:00 AM ET"
_REGISTERED_SAMPLE4_RENDERED = (
    "Pilot for Trades: Scheduled maintenance Sun 08-02-2026 from "
    "2:00–3:00 AM ET. The app may be briefly unavailable. "
    "Reply STOP to opt out."
)


def _make_verified_owner(db_session, test_tenant, phone):
    """Create a fresh owner user + TenantUser + verified+opted-in sms endpoint."""
    user = User(
        id=uuid.uuid4(),
        email=f"b2-ctx-{uuid.uuid4().hex[:8]}@test.local",
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

    endpoint = upsert_owner_sms_endpoint(
        db_session,
        user_id=user.id,
        tenant_id=test_tenant.id,
        phone=phone,
        consent=True,
        ip="127.0.0.1",
        disclosure_hash=hashlib.sha256(b"d").hexdigest(),
    )
    endpoint.verification_status = "verified"
    endpoint.consent_status = "opted_in"
    db_session.add(endpoint)
    db_session.commit()
    return user, endpoint


def _run_impl(db_session, test_tenant, type_code, template_context=None):
    """Call _impl with the B1 carrier-mock + Session-patch pattern."""
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
            template_context=template_context,
        )
    return result, mock_carrier


class TestTemplateContext:
    """Tests for the template_context parameter on _impl."""

    def test_none_context_uses_static_body_verbatim(
        self, db_session, test_tenant, platform_sms_templates
    ):
        """template_context=None on platform_security_new_device → carrier
        receives the raw stored body (B1 regression — no rendering)."""
        _make_verified_owner(db_session, test_tenant, "+15125550701")

        result, mock_carrier = _run_impl(
            db_session,
            test_tenant,
            "platform_security_new_device",
            template_context=None,
        )

        assert result["status"] == "sent"
        assert result["sent_count"] == 1
        assert mock_carrier.send_message.call_count == 1
        body = mock_carrier.send_message.call_args.kwargs["body"]
        # The static body must contain the new-device text and NO {{ }}.
        assert "New sign-in to your account from a new device" in body
        assert "{{" not in body
        assert "}}" not in body

    def test_context_renders_placeholders(
        self, db_session, test_tenant, platform_sms_templates
    ):
        """template_context on platform_maintenance_broadcast → carrier receives
        the rendered body; provided values appear and no {{ remains."""
        _make_verified_owner(db_session, test_tenant, "+15125550702")

        ctx = {
            "maint_date": "Mon 09-15-2026",
            "maint_window": "1:00–2:00 AM ET",
        }
        result, mock_carrier = _run_impl(
            db_session,
            test_tenant,
            "platform_maintenance_broadcast",
            template_context=ctx,
        )

        assert result["status"] == "sent"
        assert result["sent_count"] == 1
        body = mock_carrier.send_message.call_args.kwargs["body"]
        assert "Mon 09-15-2026" in body
        assert "1:00–2:00 AM ET" in body
        assert "{{" not in body
        assert "}}" not in body

    def test_registered_values_render_byte_identical(
        self, db_session, test_tenant, platform_sms_templates
    ):
        """Context = the registered values → carrier body == registered Sample 4
        constant byte-for-byte (the 806-safety integration assertion)."""
        _make_verified_owner(db_session, test_tenant, "+15125550703")

        ctx = {
            "maint_date": _REGISTERED_MAINT_DATE,
            "maint_window": _REGISTERED_MAINT_WINDOW,
        }
        result, mock_carrier = _run_impl(
            db_session,
            test_tenant,
            "platform_maintenance_broadcast",
            template_context=ctx,
        )

        assert result["status"] == "sent"
        body = mock_carrier.send_message.call_args.kwargs["body"]
        assert body == _REGISTERED_SAMPLE4_RENDERED, (
            f"Rendered body does not match the registered Sample 4 constant!\n"
            f"  Expected: {_REGISTERED_SAMPLE4_RENDERED!r}\n"
            f"  Actual:   {body!r}"
        )
