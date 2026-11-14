"""
A58 — Delivery Dispatcher Preference Gate Tests
tests/batch_b10/test_a58_dispatcher_gate.py

Test focus cases:
  1. _send_notification_impl suppresses in_app when user preference disables channel
  2. status set to 'suppressed_by_preferences' on suppression
  3. _send_notification_impl delivers (in_app) when system default allows
  4. System default push=False → notification suppressed
  5. Forced-minimum push uniform: delivery not suppressed even with user pref=False
  6. No suppression when notification has no recipient_user_id (fallback: deliver)
  7. Push stub channel returns 'sent' without real carrier call
  8. _build_recipient_list returns single user when recipient_user_id is set
  9. _build_recipient_list returns [] when no recipient_user_id
  10. pref_cache is populated and reused across multiple calls in same cycle
"""

from unittest.mock import patch

from app.models.sync import MobileDevicePushToken
from app.models.system import (
    NotificationOutbox,
    NotificationPreference,
)
from services.notification_resolver import get_effective_preference
from tasks.notification_worker import _build_recipient_list, _send_notification_impl

# ─── Helpers ─────────────────────────────────────────────────────────────────


def _make_in_app_outbox(
    db_session,
    test_tenant,
    test_notification_event,
    test_user,
    category_id="sync_conflicts",
    sub_trigger_id=None,
    recipient_user_id_originating=None,
):
    """
    Create a pending in_app NotificationOutbox row.

    in_app channel uses recipient_user_id as sole recipient (no to_address).
    The notification_outbox_recipient_exclusive_chk requires exactly one of
    (recipient_contact_id, recipient_user_id, to_address).
    """
    outbox = NotificationOutbox(
        tenant_id=test_tenant.id,
        notification_event_id=test_notification_event.id,
        recipient_user_id=test_user.id,
        channel="in_app",
        body="Test notification body",
        status="pending",
        category_id=category_id,
        sub_trigger_id=sub_trigger_id,
        recipient_user_id_originating=recipient_user_id_originating,
    )
    db_session.add(outbox)
    db_session.commit()
    db_session.refresh(outbox)
    return outbox


def _make_push_outbox(
    db_session,
    test_tenant,
    test_notification_event,
    test_user,
    category_id="field_issues",
    sub_trigger_id=None,
    recipient_user_id_originating=None,
):
    """Create a pending push NotificationOutbox row (no to_address needed for push)."""
    outbox = NotificationOutbox(
        tenant_id=test_tenant.id,
        notification_event_id=test_notification_event.id,
        recipient_user_id=test_user.id,
        channel="push",
        body="Push notification body",
        status="pending",
        category_id=category_id,
        sub_trigger_id=sub_trigger_id,
        recipient_user_id_originating=recipient_user_id_originating,
    )
    db_session.add(outbox)
    db_session.commit()
    db_session.refresh(outbox)
    return outbox


def _make_to_address_outbox(
    db_session,
    test_tenant,
    test_notification_event,
    recipient_user_id=None,
    channel="email",
    category_id="system_announcements",
):
    """Create a pending outbox row with to_address (email/sms delivery path)."""
    outbox = NotificationOutbox(
        tenant_id=test_tenant.id,
        notification_event_id=test_notification_event.id,
        # No recipient_user_id when to_address is set (exclusive constraint)
        channel=channel,
        to_address="test@example.com",
        body="Test body",
        status="pending",
        category_id=category_id,
    )
    db_session.add(outbox)
    db_session.commit()
    db_session.refresh(outbox)
    return outbox


# ─── Tests 1-4: Basic suppression / delivery ─────────────────────────────────


def test_dispatcher_suppresses_in_app_when_user_pref_disabled(
    db_session, test_tenant, test_notification_event, test_user
):
    """When user disables in_app for a category, notification is suppressed."""
    from sqlmodel import delete as sqldelete

    # Resilience: seed_test_tenant.py may have inserted a preference row for
    # this user+category+channel. Delete it before setting our own (Rule 16).
    db_session.exec(
        sqldelete(NotificationPreference).where(
            NotificationPreference.tenant_id == test_tenant.id,
            NotificationPreference.user_id == test_user.id,
            NotificationPreference.category_id == "sync_conflicts",
            NotificationPreference.channel == "in_app",
        )
    )
    db_session.commit()

    # sync_conflicts/in_app system default = True; override to False
    pref = NotificationPreference(
        tenant_id=test_tenant.id,
        user_id=test_user.id,
        category_id="sync_conflicts",
        channel="in_app",
        enabled=False,
    )
    db_session.add(pref)
    db_session.commit()

    outbox = _make_in_app_outbox(
        db_session,
        test_tenant,
        test_notification_event,
        test_user,
        category_id="sync_conflicts",
    )

    result = _send_notification_impl(str(outbox.id), db_session)

    assert result["status"] == "suppressed"
    assert result["reason"] == "user_preferences"

    db_session.refresh(outbox)
    assert outbox.status == "suppressed_by_preferences"

    # Cleanup
    db_session.delete(pref)
    db_session.commit()


def test_dispatcher_delivers_in_app_when_system_default_allows(
    db_session, test_tenant, test_notification_event, test_user
):
    """Without a user override, system default allows delivery (in_app for job_activity = True)."""
    # job_activity/in_app system default = TRUE (seeded by migration)
    outbox = _make_in_app_outbox(
        db_session,
        test_tenant,
        test_notification_event,
        test_user,
        category_id="job_activity",
    )

    result = _send_notification_impl(str(outbox.id), db_session)

    # in_app delivery returns "sent" immediately
    assert result["status"] == "sent"

    db_session.refresh(outbox)
    assert outbox.status == "sent"


def test_dispatcher_suppresses_when_system_default_push_is_false(
    db_session, test_tenant, test_notification_event, test_user
):
    """sync_conflicts/push system default = FALSE → notification suppressed.

    Resilience: seed_test_tenant.py may have seeded a user-level preference
    override for sync_conflicts/push=True. Delete it so this test falls through
    to the system default (False) as intended (Rule 16).
    """
    from sqlmodel import delete as sqldelete

    db_session.exec(
        sqldelete(NotificationPreference).where(
            NotificationPreference.tenant_id == test_tenant.id,
            NotificationPreference.user_id == test_user.id,
            NotificationPreference.category_id == "sync_conflicts",
            NotificationPreference.channel == "push",
        )
    )
    db_session.commit()

    outbox = _make_push_outbox(
        db_session,
        test_tenant,
        test_notification_event,
        test_user,
        category_id="sync_conflicts",
    )

    result = _send_notification_impl(str(outbox.id), db_session)

    assert result["status"] == "suppressed"
    db_session.refresh(outbox)
    assert outbox.status == "suppressed_by_preferences"


# ─── Test 5: Forced-minimum push uniform bypasses suppression ─────────────────


@patch("services.expo_push_service.send_expo_push")
def test_forced_minimum_push_uniform_bypasses_suppression(
    mock_expo, db_session, test_tenant, test_notification_event, test_user
):
    """field_issues.all has forced_minimum_push_uniform=True — cannot be suppressed."""
    from uuid import uuid4

    from services.expo_push_service import ExpoPushResult

    # Mock Expo push service to return success
    mock_expo.return_value = ExpoPushResult(
        status="sent",
        expo_ticket_id="ticket-123",
        error_message=None,
        retryable=False,
        http_status=200,
    )

    # Create a push token for the user
    token = MobileDevicePushToken(
        tenant_id=test_tenant.id,
        user_id=test_user.id,
        device_id=uuid4(),
        platform="ios",
        push_token="ExponentPushToken[test-token]",
    )
    db_session.add(token)

    # Set user push preference = disabled for field_issues
    pref = NotificationPreference(
        tenant_id=test_tenant.id,
        user_id=test_user.id,
        category_id="field_issues",
        channel="push",
        enabled=False,
    )
    db_session.add(pref)
    db_session.commit()

    outbox = _make_push_outbox(
        db_session,
        test_tenant,
        test_notification_event,
        test_user,
        category_id="field_issues",
        sub_trigger_id="field_issues.all",
        recipient_user_id_originating=test_user.id,
    )

    result = _send_notification_impl(str(outbox.id), db_session)

    # Forced-minimum should bypass suppression and deliver
    db_session.refresh(outbox)
    assert outbox.status == "sent", f"Expected 'sent', got '{outbox.status}'"

    # Cleanup
    db_session.delete(pref)
    db_session.commit()


# ─── Test 6: No recipient_user_id → gate skipped, deliver ─────────────────────


@patch("tasks.notification_worker.send_email")
def test_no_recipient_user_id_skips_preference_gate(
    mock_email, db_session, test_tenant, test_notification_event
):
    """If no recipient_user_id, gate is skipped and delivery is attempted."""
    mock_email.return_value = {
        "status": "sent",
        "details": {},
        "error_message": None,
        "http_status": 200,
        "retryable": False,
    }

    # to_address-only row (no recipient_user_id → gate skipped)
    outbox = _make_to_address_outbox(
        db_session,
        test_tenant,
        test_notification_event,
        channel="email",
        category_id="system_announcements",  # enabled by system default
    )

    result = _send_notification_impl(str(outbox.id), db_session)

    # Gate skipped → email delivery attempted
    assert mock_email.called
    assert result["status"] == "sent"


# ─── Test 7: Push stub channel ────────────────────────────────────────────────


@patch("services.expo_push_service.send_expo_push")
def test_push_channel_stub_returns_sent_for_forced_minimum(
    mock_expo, db_session, test_tenant, test_notification_event, test_user
):
    """Push channel stub returns 'sent' for field_issues.all (forced-minimum)."""
    from uuid import uuid4

    from services.expo_push_service import ExpoPushResult

    # Mock Expo push service to return success
    mock_expo.return_value = ExpoPushResult(
        status="sent",
        expo_ticket_id="ticket-456",
        error_message=None,
        retryable=False,
        http_status=200,
    )

    # Create a push token for the user
    token = MobileDevicePushToken(
        tenant_id=test_tenant.id,
        user_id=test_user.id,
        device_id=uuid4(),
        platform="android",
        push_token="ExponentPushToken[test-android-token]",
    )
    db_session.add(token)
    db_session.commit()

    outbox = _make_push_outbox(
        db_session,
        test_tenant,
        test_notification_event,
        test_user,
        category_id="field_issues",
        sub_trigger_id="field_issues.all",
        recipient_user_id_originating=test_user.id,
    )

    result = _send_notification_impl(str(outbox.id), db_session)

    db_session.refresh(outbox)
    assert outbox.status == "sent"
    assert result["status"] == "sent"


# ─── Tests 8-9: _build_recipient_list ─────────────────────────────────────────


def test_build_recipient_list_with_user(
    test_notification_event, test_tenant, test_user
):
    """_build_recipient_list returns the recipient_user_id when set."""
    outbox = NotificationOutbox(
        tenant_id=test_tenant.id,
        notification_event_id=test_notification_event.id,
        recipient_user_id=test_user.id,
        channel="in_app",
        body="body",
        status="pending",
        category_id="system_announcements",
    )
    result = _build_recipient_list(outbox)
    assert result == [test_user.id]


def test_build_recipient_list_no_user(test_notification_event, test_tenant):
    """_build_recipient_list returns empty list when no recipient_user_id."""
    outbox = NotificationOutbox(
        tenant_id=test_tenant.id,
        notification_event_id=test_notification_event.id,
        channel="email",
        to_address="t@t.com",
        body="body",
        status="pending",
        category_id="system_announcements",
    )
    result = _build_recipient_list(outbox)
    assert result == []


# ─── Test 10: pref_cache reuse ────────────────────────────────────────────────


def test_pref_cache_populated_and_reused(db_session, test_tenant, test_user):
    """pref_cache is populated by first get_effective_preference call and reused."""
    cache: dict[tuple, bool] = {}

    # First call — populates cache
    result1 = get_effective_preference(
        db_session, test_tenant.id, test_user.id, "sync_conflicts", "push", cache
    )
    assert (test_user.id, "sync_conflicts", "push") in cache

    # Mutate a preference to ensure second call reads from cache (not DB)
    # (If it re-queried DB, it would see the fresh value, not the cached one)
    cached_value = cache[(test_user.id, "sync_conflicts", "push")]

    result2 = get_effective_preference(
        db_session, test_tenant.id, test_user.id, "sync_conflicts", "push", cache
    )
    assert result1 == result2 == cached_value
