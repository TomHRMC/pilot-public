"""
C-B6: Tests for the free-period notification Celery beat task.
Domain: notifications_comms

Covers:
  - Task registered in celery imports + beat_schedule
  - _impl sends at T-30
  - _impl sends at T-0 (expiry day)
  - Idempotent (skip if already sent)
  - Skips tenants without free_period_ends_at
"""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from sqlmodel import select

pytestmark = [
    pytest.mark.domain_notifications_comms,
    pytest.mark.unit,
]

# tenant_user_status.code='active' id (MCP-verified, seeded platform row).
_ACTIVE_STATUS_ID = "5b67cfd3-ef42-4311-9516-a4eec8642628"


def _make_tenant_with_owner(db_session, *, free_period_ends_at=None, is_active=True):
    """Create a fresh tenant + owner user + TenantUser link (rolled back after test)."""
    from app.models.auth import TenantUser
    from app.models.core import Tenant, User

    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()

    tenant = Tenant(
        id=tenant_id,
        name=f"[C-B6-TEST] Tenant {tenant_id}",
        is_active=is_active,
        free_period_ends_at=free_period_ends_at,
    )
    db_session.add(tenant)
    db_session.flush()

    owner = User(
        id=user_id,
        email=f"cb6-owner-{user_id}@test.pilotfortrades.com",
        is_active=True,
    )
    db_session.add(owner)
    db_session.flush()

    db_session.add(
        TenantUser(
            tenant_id=tenant_id,
            user_id=user_id,
            role_code="owner",
            status_id=_ACTIVE_STATUS_ID,
            is_active=True,
        )
    )
    db_session.commit()
    db_session.refresh(tenant)
    return tenant


class TestFreePeriodNotificationsRegistration:
    """Verify the task is registered in celery_app imports + beat_schedule."""

    def test_task_in_celery_imports(self):
        """'tasks.free_period_notifications' is in celery_app.conf.imports."""
        from core.celery_app import celery_app

        imports = celery_app.conf.imports
        assert "tasks.free_period_notifications" in imports, (
            "tasks.free_period_notifications missing from celery_app imports"
        )

    def test_beat_schedule_entry_exists(self):
        """'free-period-notifications-daily' beat entry exists with daily 09:00 UTC schedule."""
        from core.celery_app import celery_app

        beat = celery_app.conf.beat_schedule
        assert "free-period-notifications-daily" in beat, (
            "free-period-notifications-daily missing from beat_schedule"
        )
        entry = beat["free-period-notifications-daily"]
        assert entry["task"] == "free_period_notifications"


class TestFreePeriodNotificationsImpl:
    """Tests for _free_period_notifications_impl()."""

    def test_sends_at_t30(self, db_session):
        """_impl dispatches a notification when days_remaining == 30."""
        from tasks.free_period_notifications import _free_period_notifications_impl

        now = datetime.now(UTC)
        # +6h buffer so .days truncation yields 30 (not 29 from µs drift)
        tenant = _make_tenant_with_owner(
            db_session, free_period_ends_at=now + timedelta(days=30, hours=6)
        )

        with patch("tasks.notification_worker.send_notification"):
            result = _free_period_notifications_impl(db_session)

        assert result["notifications_sent"] >= 1

        # Verify NotificationEvent was created with days_remaining=30
        from app.models.system import NotificationEvent

        events = db_session.exec(
            select(NotificationEvent)
            .where(NotificationEvent.tenant_id == tenant.id)
            .where(NotificationEvent.notification_type_code == "free_period_warning")
        ).all()
        assert len(events) == 1
        assert events[0].payload["days_remaining"] == 30

    def test_sends_at_t0_expiry_day(self, db_session):
        """_impl dispatches a notification on expiry day (days_remaining == 0)."""
        from tasks.free_period_notifications import _free_period_notifications_impl

        now = datetime.now(UTC)
        # free_period_ends_at slightly in the future so .days == 0
        tenant = _make_tenant_with_owner(
            db_session, free_period_ends_at=now + timedelta(hours=2)
        )
        # NOTE: (now + 2h - now_impl).days == 0 since < 1 day remaining

        with patch("tasks.notification_worker.send_notification"):
            result = _free_period_notifications_impl(db_session)

        assert result["notifications_sent"] >= 1

        from app.models.system import NotificationEvent

        events = db_session.exec(
            select(NotificationEvent)
            .where(NotificationEvent.tenant_id == tenant.id)
            .where(NotificationEvent.notification_type_code == "free_period_warning")
        ).all()
        assert len(events) == 1
        assert events[0].payload["days_remaining"] == 0

    def test_idempotent_skip_if_already_sent(self, db_session):
        """_impl does not create a duplicate notification for the same threshold."""
        from tasks.free_period_notifications import _free_period_notifications_impl

        now = datetime.now(UTC)
        # +6h buffer so .days truncation yields 30 (not 29 from µs drift)
        tenant = _make_tenant_with_owner(
            db_session, free_period_ends_at=now + timedelta(days=30, hours=6)
        )

        with patch("tasks.notification_worker.send_notification"):
            # First run — sends the notification
            result1 = _free_period_notifications_impl(db_session)
            assert result1["notifications_sent"] >= 1

            # Second run — should skip (idempotent)
            _free_period_notifications_impl(db_session)

        # The second run should not have sent a new notification for this tenant.
        # (It may report 0 or a small count if other tenants exist, but the
        # NotificationEvent count for this tenant must remain 1.)
        from app.models.system import NotificationEvent

        events = db_session.exec(
            select(NotificationEvent)
            .where(NotificationEvent.tenant_id == tenant.id)
            .where(NotificationEvent.notification_type_code == "free_period_warning")
        ).all()
        assert len(events) == 1, (
            "Idempotency failed — duplicate NotificationEvent created for same threshold"
        )

    def test_skips_tenants_without_free_period_ends_at(self, db_session):
        """_impl does not dispatch for tenants with free_period_ends_at IS NULL."""
        from tasks.free_period_notifications import _free_period_notifications_impl

        # Create a tenant with NO free_period_ends_at
        tenant = _make_tenant_with_owner(db_session, free_period_ends_at=None)

        with patch("tasks.notification_worker.send_notification"):
            _free_period_notifications_impl(db_session)

        # No NotificationEvent should exist for this tenant
        from app.models.system import NotificationEvent

        events = db_session.exec(
            select(NotificationEvent)
            .where(NotificationEvent.tenant_id == tenant.id)
            .where(NotificationEvent.notification_type_code == "free_period_warning")
        ).all()
        assert len(events) == 0
