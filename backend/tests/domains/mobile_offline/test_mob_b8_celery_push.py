"""
Tests for: MOB-B8 Background Sync Push Celery Tasks
Domain: mobile_offline (PRD §3.15)

Tests the _impl() functions directly — never calls .delay() or the real Expo API.
All Expo push calls are mocked. DB interactions use the db_session rollback fixture.
"""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from sqlmodel import select

from app.models.sync import MobileDevicePushToken, MobilePushRateLimit
from tasks.background_sync_push import (
    _scan_and_dispatch_impl,
    _send_background_sync_push_impl,
)

pytestmark = [
    pytest.mark.domain_mobile_offline,
    pytest.mark.unit,
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_push_token(
    db_session,
    tenant_id,
    user_id,
    device_id=None,
    push_token=None,
    platform="ios",
    revoked_at=None,
    notification_permission_granted=True,
):
    """Insert a MobileDevicePushToken row directly into the test session."""
    did = device_id or uuid.uuid4()
    now = datetime.now(UTC)
    row = MobileDevicePushToken(
        tenant_id=tenant_id,
        user_id=user_id,
        device_id=did,
        platform=platform,
        push_token=push_token or f"ExponentPushToken[{uuid.uuid4().hex[:16]}]",
        registered_at=now,
        last_seen_at=now,
        notification_permission_granted=notification_permission_granted,
        revoked_at=revoked_at,
    )
    db_session.add(row)
    db_session.commit()
    db_session.refresh(row)
    return row


def _create_rate_limit(db_session, tenant_id, device_id, last_push_minutes_ago=0):
    """Insert a MobilePushRateLimit row with last_push_sent_at = now - minutes_ago."""
    now = datetime.now(UTC)
    last_sent = now - timedelta(minutes=last_push_minutes_ago)
    row = MobilePushRateLimit(
        tenant_id=tenant_id,
        device_id=device_id,
        last_push_sent_at=last_sent,
        push_count_current_window=1,
        window_start_at=last_sent,
    )
    db_session.add(row)
    db_session.commit()
    db_session.refresh(row)
    return row


# ---------------------------------------------------------------------------
# Tests — _send_background_sync_push_impl
# ---------------------------------------------------------------------------


class TestSendBackgroundSyncPushImpl:
    """Unit tests for _send_background_sync_push_impl() — business logic only."""

    def test_send_push_disabled_by_setting(self, db_session, test_tenant, test_user):
        """When background_sync_enabled=False, impl returns sent=False, reason='background_sync_disabled'."""
        device_id = uuid.uuid4()
        _create_push_token(
            db_session, test_tenant.id, test_user.id, device_id=device_id
        )

        with (
            patch(
                "tasks.background_sync_push.get_effective_setting"  # patched at import location in task module
            ) as mock_get
        ):
            # First call → background_sync_enabled = False
            mock_get.return_value = (False, "tenant")

            result = _send_background_sync_push_impl(
                str(test_tenant.id), str(device_id), db_session
            )

        assert result["sent"] is False
        assert result["reason"] == "background_sync_disabled"

    def test_send_push_no_active_token(self, db_session, test_tenant, test_user):
        """Device with no token row returns sent=False, reason='no_active_token'."""
        unknown_device = uuid.uuid4()

        with patch("tasks.background_sync_push.get_effective_setting") as mock_get:
            # Simulate enabled=True, interval=5
            mock_get.side_effect = [(True, "system"), (5, "system")]

            result = _send_background_sync_push_impl(
                str(test_tenant.id), str(unknown_device), db_session
            )

        assert result["sent"] is False
        assert result["reason"] == "no_active_token"

    def test_send_push_rate_limited(self, db_session, test_tenant, test_user):
        """Device pushed <1 min ago (with 5-min interval) returns rate_limited reason."""
        device_id = uuid.uuid4()
        _create_push_token(
            db_session, test_tenant.id, test_user.id, device_id=device_id
        )
        # Rate limit row: last push was 0.5 minutes ago (30 seconds)
        _create_rate_limit(
            db_session, test_tenant.id, device_id, last_push_minutes_ago=0.5
        )

        with patch("tasks.background_sync_push.get_effective_setting") as mock_get:
            # enabled=True, interval=5 minutes
            mock_get.side_effect = [(True, "system"), (5, "system")]

            result = _send_background_sync_push_impl(
                str(test_tenant.id), str(device_id), db_session
            )

        assert result["sent"] is False
        assert result["reason"].startswith("rate_limited_"), (
            f"Expected reason starting with 'rate_limited_', got: {result['reason']}"
        )

    def test_send_push_revoked_token_skipped(self, db_session, test_tenant, test_user):
        """Device with revoked_at set returns no_active_token."""
        device_id = uuid.uuid4()
        _create_push_token(
            db_session,
            test_tenant.id,
            test_user.id,
            device_id=device_id,
            revoked_at=datetime.now(UTC),  # revoked
        )

        with patch("tasks.background_sync_push.get_effective_setting") as mock_get:
            mock_get.side_effect = [(True, "system"), (5, "system")]

            result = _send_background_sync_push_impl(
                str(test_tenant.id), str(device_id), db_session
            )

        assert result["sent"] is False
        assert result["reason"] == "no_active_token"

    def test_send_push_success(self, db_session, test_tenant, test_user):
        """Eligible device with no prior rate limit gets push dispatched — returns sent=True."""
        device_id = uuid.uuid4()
        _create_push_token(
            db_session, test_tenant.id, test_user.id, device_id=device_id
        )

        with patch("tasks.background_sync_push.get_effective_setting") as mock_get:
            mock_get.side_effect = [(True, "system"), (5, "system")]

            with patch(
                "tasks.background_sync_push._dispatch_expo_silent_push",
                return_value=True,
            ):
                result = _send_background_sync_push_impl(
                    str(test_tenant.id), str(device_id), db_session
                )

        assert result["sent"] is True
        assert result["reason"] == "ok"

        # Verify rate limit row was created
        rate_row = db_session.exec(
            select(MobilePushRateLimit).where(
                MobilePushRateLimit.device_id == device_id
            )
        ).first()
        assert rate_row is not None
        assert rate_row.push_count_current_window == 1


# ---------------------------------------------------------------------------
# Tests — _scan_and_dispatch_impl
# ---------------------------------------------------------------------------


class TestScanAndDispatchImpl:
    """Unit tests for _scan_and_dispatch_impl() — never calls .delay()."""

    def test_scan_dispatches_active_tokens(self, db_session, test_tenant, test_user):
        """_scan_and_dispatch_impl with 2 active tokens returns dispatched=2; delay called twice."""
        device_a = uuid.uuid4()
        device_b = uuid.uuid4()

        _create_push_token(db_session, test_tenant.id, test_user.id, device_id=device_a)
        _create_push_token(db_session, test_tenant.id, test_user.id, device_id=device_b)

        captured_calls = []

        def fake_delay(tenant_id, device_id):
            captured_calls.append((tenant_id, device_id))

        with patch("tasks.background_sync_push.send_background_sync_push") as mock_task:
            mock_task.delay = MagicMock(side_effect=fake_delay)

            result = _scan_and_dispatch_impl(db_session)

        # Should have dispatched at least the 2 tokens we created
        assert result["dispatched"] >= 2, (
            f"Expected dispatched >= 2, got {result['dispatched']}"
        )
        assert "scanned_at" in result

        # Verify delay was called with our two devices
        dispatched_devices = {call[1] for call in captured_calls}
        assert str(device_a) in dispatched_devices, "device_a was not dispatched"
        assert str(device_b) in dispatched_devices, "device_b was not dispatched"

    def test_scan_skips_revoked_tokens(self, db_session, test_tenant, test_user):
        """_scan_and_dispatch_impl does NOT dispatch for revoked tokens."""
        device_active = uuid.uuid4()
        device_revoked = uuid.uuid4()

        _create_push_token(
            db_session, test_tenant.id, test_user.id, device_id=device_active
        )
        _create_push_token(
            db_session,
            test_tenant.id,
            test_user.id,
            device_id=device_revoked,
            revoked_at=datetime.now(UTC),
        )

        captured_calls = []

        def fake_delay(tenant_id, device_id):
            captured_calls.append((tenant_id, device_id))

        with patch("tasks.background_sync_push.send_background_sync_push") as mock_task:
            mock_task.delay = MagicMock(side_effect=fake_delay)
            _scan_and_dispatch_impl(db_session)

        dispatched_devices = {call[1] for call in captured_calls}
        assert str(device_revoked) not in dispatched_devices, (
            "Revoked token should not be dispatched"
        )
        assert str(device_active) in dispatched_devices, (
            "Active token should be dispatched"
        )
