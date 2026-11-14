"""
Tests for: Post-Authentication Lambda handler (PLATFORM-SMS-B2 / Sample 3 + PLP-FIX-10/INV-BUG-17).
Domain: identity_access (PRD §3.5)

Covers the new-device sign-in alert trigger AND the login-recording enqueue
(PLP-FIX-10/INV-BUG-17 — fires on EVERY successful auth):

  - newDeviceUsed=True with two active tenant_user rows → two send_task calls
    for device alerts + two send_task calls for login recording (4 total).
  - newDeviceUsed=False → zero device-alert calls + one login-recording call
    per tenant.
  - newDeviceUsed absent → zero device-alert calls + one login-recording call
    per tenant.
  - Email not present in user table → zero calls (no raise).
  - Producer send_task raises → handler still returns event (never-raise).
  - userAttributes missing email → zero calls.

Mirrors ``test_post_confirmation_router.py``'s importlib pattern and its
approach to pointing the module engine at the test DB.
"""

import uuid
from unittest.mock import MagicMock, patch

import pytest
from sqlmodel import Session

from app.models.auth import TenantUser
from app.models.core import User

pytestmark = [
    pytest.mark.domain_identity_access,
    pytest.mark.unit,
]

# tenant_user_status.code='active' id (MCP-verified, seeded platform row).
_ACTIVE_STATUS_ID = "5b67cfd3-ef42-4311-9516-a4eec8642628"

_DEVICE_TASK = "send_platform_account_notification_sms"
_LOGIN_TASK = "record_user_login"


def _make_cognito_event(email: str, new_device_used=True) -> dict:
    """Build a synthetic Cognito Post-Authentication event dict."""
    return {
        "request": {
            "newDeviceUsed": new_device_used,
            "userAttributes": {
                "email": email,
                "sub": str(uuid.uuid4()),
            },
        },
        "response": {},
    }


def _make_user_with_tenants(db_session, email, tenant_ids):
    """Create a user + active TenantUser rows for each tenant_id."""
    user = User(
        id=uuid.uuid4(),
        email=email,
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()
    for tid in tenant_ids:
        db_session.add(
            TenantUser(
                tenant_id=tid,
                user_id=user.id,
                role_code="owner",
                status_id=_ACTIVE_STATUS_ID,
                is_active=True,
            )
        )
    db_session.flush()
    db_session.commit()
    return user


def _run_handler(db_session, email, new_device_used=True):
    """Import the handler module fresh, patch engine+producer, run handler."""
    import importlib

    handler_mod = importlib.import_module("lambda.post_authentication.handler")

    fake_producer = MagicMock()
    with (
        patch.object(handler_mod, "_get_engine", return_value=db_session.get_bind()),
        patch.object(handler_mod, "_get_producer", return_value=fake_producer),
    ):
        event = _make_cognito_event(email, new_device_used=new_device_used)
        result = handler_mod.handler(event, None)

    return result, fake_producer


def _run_handler_no_new_device_key(db_session, email):
    """Run handler with an event that has no newDeviceUsed key at all."""
    import importlib

    handler_mod = importlib.import_module("lambda.post_authentication.handler")

    fake_producer = MagicMock()
    with (
        patch.object(handler_mod, "_get_engine", return_value=db_session.get_bind()),
        patch.object(handler_mod, "_get_producer", return_value=fake_producer),
    ):
        event = {
            "request": {
                "userAttributes": {"email": email},
            },
            "response": {},
        }
        result = handler_mod.handler(event, None)

    return result, fake_producer


def _run_handler_missing_email(db_session):
    """Run handler with an event that has no email in userAttributes."""
    import importlib

    handler_mod = importlib.import_module("lambda.post_authentication.handler")

    fake_producer = MagicMock()
    with (
        patch.object(handler_mod, "_get_engine", return_value=db_session.get_bind()),
        patch.object(handler_mod, "_get_producer", return_value=fake_producer),
    ):
        event = {
            "request": {
                "newDeviceUsed": True,
                "userAttributes": {},
            },
            "response": {},
        }
        result = handler_mod.handler(event, None)

    return result, fake_producer


class TestNewDeviceAlertFanOut:
    """newDeviceUsed=True → one device-alert + one login-recording per tenant."""

    def test_two_active_tenants_both_tasks_enqueued(
        self, db_session: Session, test_tenant, second_tenant
    ):
        email = f"b2-auth-{uuid.uuid4()}@example.com"
        user = _make_user_with_tenants(
            db_session, email, [test_tenant.id, second_tenant.id]
        )

        result, fake_producer = _run_handler(db_session, email, new_device_used=True)

        assert result is event_or_none(result)
        # 2 tenants x 2 task types (device alert + login recording) = 4 calls.
        assert fake_producer.send_task.call_count == 4

        device_calls = []
        login_calls = []
        for call in fake_producer.send_task.call_args_list:
            args, kwargs = call
            task_name = args[0]
            if task_name == _DEVICE_TASK:
                device_calls.append(kwargs)
            elif task_name == _LOGIN_TASK:
                login_calls.append(kwargs)

        # Device alerts: 2 calls (one per tenant).
        assert len(device_calls) == 2
        called_device_tenant_ids = set()
        called_device_recipient_user_ids = set()
        for kwargs in device_calls:
            assert kwargs["kwargs"]["type_code"] == "platform_security_new_device"
            called_device_tenant_ids.add(kwargs["kwargs"]["tenant_id"])
            called_device_recipient_user_ids.add(kwargs["kwargs"]["recipient_user_id"])
        assert str(test_tenant.id) in called_device_tenant_ids
        assert str(second_tenant.id) in called_device_tenant_ids
        assert len(called_device_recipient_user_ids) == 1
        assert str(user.id) in called_device_recipient_user_ids

        # Login recording: 2 calls (one per tenant).
        assert len(login_calls) == 2
        called_login_tenant_ids = set()
        called_login_user_ids = set()
        for kwargs in login_calls:
            called_login_tenant_ids.add(kwargs["kwargs"]["tenant_id"])
            called_login_user_ids.add(kwargs["kwargs"]["user_id"])
        assert str(test_tenant.id) in called_login_tenant_ids
        assert str(second_tenant.id) in called_login_tenant_ids
        assert len(called_login_user_ids) == 1
        assert str(user.id) in called_login_user_ids


def event_or_none(result):
    """Helper — the handler always returns the event dict."""
    return result


class TestLoginRecordingOnEveryAuth:
    """newDeviceUsed=False/absent → only login recording enqueued (no device alert)."""

    def test_new_device_false_only_login_recording(
        self, db_session: Session, test_tenant
    ):
        email = f"b2-false-{uuid.uuid4()}@example.com"
        user = _make_user_with_tenants(db_session, email, [test_tenant.id])

        result, fake_producer = _run_handler(db_session, email, new_device_used=False)

        assert result is event_or_none(result)
        # Only login recording — no device alert.
        assert fake_producer.send_task.call_count == 1

        call = fake_producer.send_task.call_args_list[0]
        args, kwargs = call
        assert args[0] == _LOGIN_TASK
        assert kwargs["kwargs"]["tenant_id"] == str(test_tenant.id)
        assert kwargs["kwargs"]["user_id"] == str(user.id)

    def test_new_device_absent_only_login_recording(
        self, db_session: Session, test_tenant
    ):
        email = f"b2-absent-{uuid.uuid4()}@example.com"
        user = _make_user_with_tenants(db_session, email, [test_tenant.id])

        result, fake_producer = _run_handler_no_new_device_key(db_session, email)

        assert result is event_or_none(result)
        # Only login recording — no device alert.
        assert fake_producer.send_task.call_count == 1

        call = fake_producer.send_task.call_args_list[0]
        args, kwargs = call
        assert args[0] == _LOGIN_TASK
        assert kwargs["kwargs"]["tenant_id"] == str(test_tenant.id)
        assert kwargs["kwargs"]["user_id"] == str(user.id)


class TestNoUserFound:
    """Email not present in user table → zero calls, returns event (no raise)."""

    def test_unknown_email_no_calls(self, db_session: Session):
        email = f"b2-unknown-{uuid.uuid4()}@example.com"
        # Do NOT create a user for this email.

        result, fake_producer = _run_handler(db_session, email, new_device_used=True)

        assert result is event_or_none(result)
        fake_producer.send_task.assert_not_called()


class TestNeverRaise:
    """Producer send_task raises → handler still returns event."""

    def test_producer_raises_returns_event(self, db_session: Session, test_tenant):
        import importlib

        handler_mod = importlib.import_module("lambda.post_authentication.handler")

        email = f"b2-raise-{uuid.uuid4()}@example.com"
        _make_user_with_tenants(db_session, email, [test_tenant.id])

        fake_producer = MagicMock()
        fake_producer.send_task.side_effect = RuntimeError("broker down")
        with (
            patch.object(
                handler_mod, "_get_engine", return_value=db_session.get_bind()
            ),
            patch.object(handler_mod, "_get_producer", return_value=fake_producer),
        ):
            event = _make_cognito_event(email, new_device_used=True)
            result = handler_mod.handler(event, None)

        # Never-raise: handler returns event despite the producer exception.
        assert result is event


class TestMissingEmail:
    """userAttributes missing email → zero calls, returns event."""

    def test_user_attributes_missing_email(self, db_session: Session):
        result, fake_producer = _run_handler_missing_email(db_session)

        assert result is event_or_none(result)
        fake_producer.send_task.assert_not_called()
