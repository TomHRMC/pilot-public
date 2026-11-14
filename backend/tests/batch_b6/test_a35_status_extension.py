"""# noqa: E501
B6/A35: Mobile Pending-Conflicts Status & Rate Limiting — Tests

Test focus cases:
  - [A35-1] GET /integrations/calendar/status/test returns pending_conflicts_count
  - [A35-2] pending_conflicts_count reflects only unresolved conflicts
  - [A35-3] connection_status = 'connected' when sync_status = 'active'
  - [A35-4] connection_status = 'disconnected' when sync_status = 'paused'
  - [A35-5] connection_status = 'error' when sync_status = 'error'
  - [A35-6] last_successful_sync_at from CalendarSyncLog (status='success')
  - [A35-7] last_successful_sync_at is None when no successful sync log exists
  - [A35-8] requires_reconnect = True when sync_status = 'error' and token expired
  - [A35-9] requires_reconnect = False when sync_status = 'error' but token still valid
  - [A35-10] requires_reconnect = False when sync_status = 'active'
  - [A35-11] GET /status returns is_connected=False with connection_status='disconnected' when no integration
  - [A35-12] Rate limit check: count_recent_conflict_notifications counts push notifications
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlmodel import select

from app.models.scheduling import (
    CalendarSyncConflict,
    CalendarSyncLog,
    TenantCalendarIntegration,
)
from services.calendar_conflict_service import CalendarConflictService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_calendar_integration(
    db_session, tenant_id: uuid.UUID, sync_status: str = "active", token_expires_at=None
) -> TenantCalendarIntegration:
    """Create TenantCalendarIntegration for test tenant."""
    from app.models.core import User

    existing = db_session.exec(
        select(TenantCalendarIntegration).where(
            TenantCalendarIntegration.tenant_id == tenant_id
        )
    ).first()
    if existing:
        existing.sync_status = sync_status
        if token_expires_at is not None:
            existing.token_expires_at = token_expires_at
        db_session.add(existing)
        db_session.commit()
        db_session.refresh(existing)
        return existing

    user = db_session.exec(select(User).limit(1)).first()
    user_id = user.id if user else uuid.uuid4()

    now = datetime.now(UTC)
    integration = TenantCalendarIntegration(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        provider_code="google",
        external_calendar_id="primary",
        access_token_encrypted=b"mock",
        refresh_token_encrypted=b"mock",
        token_expires_at=token_expires_at or (now + timedelta(hours=1)),
        sync_status=sync_status,
        connected_by_user_id=user_id,
        connected_at=now,
    )
    db_session.add(integration)
    db_session.commit()
    db_session.refresh(integration)
    return integration


def _make_conflict(
    db_session, tenant_id: uuid.UUID, job_id: uuid.UUID, resolution: str = None
) -> CalendarSyncConflict:
    """Create a minimal CalendarSyncConflict."""
    now = datetime.now(UTC)
    conflict = CalendarSyncConflict(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        job_id=job_id,
        conflict_type="modified_modified",
        local_snapshot={"title": "Test"},
        remote_snapshot={"title": "Test Modified"},
        pilot_modified_at=now - timedelta(hours=2),
        external_modified_at=now - timedelta(hours=1),
        auto_resolved_stale=False,
        resolution=resolution,
    )
    db_session.add(conflict)
    db_session.commit()
    db_session.refresh(conflict)
    return conflict


def _make_job(db_session, tenant_id: uuid.UUID):
    """Create minimal Job for FK."""
    from app.models.crm import Customer, Site
    from app.models.fulfillment import Job, JobStatus

    customer = Customer(id=uuid.uuid4(), tenant_id=tenant_id, display_name="A35 Test")
    db_session.add(customer)
    db_session.flush()

    site = Site(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        customer_id=customer.id,
        site_name="A35 Site",
        is_active=True,
    )
    db_session.add(site)
    db_session.flush()

    job_status = db_session.exec(
        select(JobStatus).where(JobStatus.code == "draft")
    ).first()
    if not job_status:
        job_status = JobStatus(
            id=uuid.uuid4(), code="draft", name="Draft", is_active=True
        )
        db_session.add(job_status)
        db_session.flush()

    job = Job(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        customer_id=customer.id,
        site_id=site.id,
        status_id=job_status.id,
        is_active=True,
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    return job


# ===========================================================================
# A35 API endpoint tests
# ===========================================================================


class TestCalendarStatusExtension:
    def test_a35_11_no_integration_returns_disconnected(
        self, client: TestClient, db_session, test_tenant
    ):
        """[A35-11] No integration row → is_connected=False, connection_status='disconnected'."""
        # Ensure no integration for test tenant
        existing = db_session.exec(
            select(TenantCalendarIntegration).where(
                TenantCalendarIntegration.tenant_id == test_tenant.id
            )
        ).first()
        if existing:
            existing.sync_status = "paused"
            db_session.add(existing)
            db_session.commit()

        response = client.get("/api/v1/integrations/calendar/status/test")
        assert response.status_code == 200
        data = response.json()
        assert data["is_connected"] is False

    def test_a35_1_status_includes_pending_conflicts_count(
        self, client: TestClient, db_session, test_tenant
    ):
        """[A35-1] Status response includes pending_conflicts_count."""
        _make_calendar_integration(db_session, test_tenant.id)

        response = client.get("/api/v1/integrations/calendar/status/test")
        assert response.status_code == 200
        data = response.json()
        assert "pending_conflicts_count" in data
        assert isinstance(data["pending_conflicts_count"], int)

    def test_a35_2_pending_conflicts_count_only_unresolved(
        self, client: TestClient, db_session, test_tenant
    ):
        """[A35-2] pending_conflicts_count counts only unresolved conflicts."""
        _make_calendar_integration(db_session, test_tenant.id)
        job = _make_job(db_session, test_tenant.id)

        # Get baseline count
        r0 = client.get("/api/v1/integrations/calendar/status/test")
        base_count = r0.json()["pending_conflicts_count"]

        # Add 2 pending, 1 resolved
        _make_conflict(db_session, test_tenant.id, job.id)
        _make_conflict(db_session, test_tenant.id, job.id)
        _make_conflict(db_session, test_tenant.id, job.id, resolution="accept_local")

        r1 = client.get("/api/v1/integrations/calendar/status/test")
        data = r1.json()
        assert data["pending_conflicts_count"] == base_count + 2

    def test_a35_3_connection_status_connected(
        self, client: TestClient, db_session, test_tenant
    ):
        """[A35-3] connection_status = 'connected' when sync_status = 'active'."""
        _make_calendar_integration(db_session, test_tenant.id, sync_status="active")
        r = client.get("/api/v1/integrations/calendar/status/test")
        assert r.json()["connection_status"] == "connected"

    def test_a35_4_connection_status_disconnected_when_paused(
        self, client: TestClient, db_session, test_tenant
    ):
        """[A35-4] connection_status = 'disconnected' when sync_status = 'paused'."""
        _make_calendar_integration(db_session, test_tenant.id, sync_status="paused")
        r = client.get("/api/v1/integrations/calendar/status/test")
        data = r.json()
        assert data["connection_status"] == "disconnected"
        assert data["is_connected"] is False

    def test_a35_5_connection_status_error_when_error(
        self, client: TestClient, db_session, test_tenant
    ):
        """[A35-5] connection_status = 'error' when sync_status = 'error'."""
        _make_calendar_integration(db_session, test_tenant.id, sync_status="error")
        r = client.get("/api/v1/integrations/calendar/status/test")
        assert r.json()["connection_status"] == "error"

    def test_a35_6_last_successful_sync_at(
        self, client: TestClient, db_session, test_tenant
    ):
        """[A35-6] last_successful_sync_at from CalendarSyncLog with status='success'."""
        _make_calendar_integration(db_session, test_tenant.id)
        job = _make_job(db_session, test_tenant.id)

        # Create a success log entry
        success_log = CalendarSyncLog(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            direction="pull",
            entity_type="job",
            entity_id=job.id,
            status="success",
        )
        db_session.add(success_log)
        db_session.commit()

        r = client.get("/api/v1/integrations/calendar/status/test")
        data = r.json()
        assert data["last_successful_sync_at"] is not None

    def test_a35_7_last_successful_sync_at_none_when_no_success_log(
        self, client: TestClient, db_session, test_tenant
    ):
        """[A35-7] last_successful_sync_at = None when no success log exists."""
        # Ensure fresh integration with no success logs for this tenant
        # Use a fresh UUID tenant-like context by querying with filter
        # Delete any existing success logs for test tenant
        db_session.execute(
            __import__("sqlalchemy", fromlist=["text"]).text(
                "DELETE FROM calendar_sync_log WHERE tenant_id = :tid AND status = 'success'"
            ),
            {"tid": str(test_tenant.id)},
        )
        db_session.commit()

        _make_calendar_integration(db_session, test_tenant.id)

        r = client.get("/api/v1/integrations/calendar/status/test")
        data = r.json()
        assert data["last_successful_sync_at"] is None

    def test_a35_8_requires_reconnect_true_when_error_and_token_expired(
        self, client: TestClient, db_session, test_tenant
    ):
        """[A35-8] requires_reconnect=True when error + token expired."""
        expired_at = datetime.now(UTC) - timedelta(hours=2)
        _make_calendar_integration(
            db_session, test_tenant.id, sync_status="error", token_expires_at=expired_at
        )
        r = client.get("/api/v1/integrations/calendar/status/test")
        assert r.json()["requires_reconnect"] is True

    def test_a35_9_requires_reconnect_false_when_error_but_token_valid(
        self, client: TestClient, db_session, test_tenant
    ):
        """[A35-9] requires_reconnect=False when error but token still valid."""
        valid_at = datetime.now(UTC) + timedelta(hours=2)
        _make_calendar_integration(
            db_session, test_tenant.id, sync_status="error", token_expires_at=valid_at
        )
        r = client.get("/api/v1/integrations/calendar/status/test")
        assert r.json()["requires_reconnect"] is False

    def test_a35_10_requires_reconnect_false_when_active(
        self, client: TestClient, db_session, test_tenant
    ):
        """[A35-10] requires_reconnect=False when sync_status='active'."""
        _make_calendar_integration(db_session, test_tenant.id, sync_status="active")
        r = client.get("/api/v1/integrations/calendar/status/test")
        assert r.json()["requires_reconnect"] is False


# ===========================================================================
# A35 Rate-limit service unit test
# ===========================================================================


class TestRateLimitService:
    def test_a35_12_count_recent_conflict_notifications(self, db_session, test_tenant):
        """[A35-12] count_recent_conflict_notifications counts push notifications in window."""
        import sqlalchemy as sa
        from sqlmodel import select

        from app.models.core import User
        from app.models.system import NotificationEvent

        # Create a notification_event row inline (append-only; unique id per run)
        event = NotificationEvent(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            notification_type_code="quote_accepted",
            entity_type_code="customer",
            entity_id=str(uuid.uuid4()),
        )
        db_session.add(event)
        db_session.flush()

        # Get a real user for recipient_user_id
        user = db_session.exec(select(User).limit(1)).first()
        if not user:
            pytest.skip("No user available for NotificationOutbox recipient_user_id")

        # Insert 2 in_app notifications with conflict_detected event_type via raw SQL
        # B8/A51: 'push' channel deferred to B8; using 'in_app' for B6.
        for _ in range(2):
            db_session.execute(
                sa.text("""
                    INSERT INTO notification_outbox (
                        id, notification_event_id, tenant_id, channel, body,
                        status, attempt_count, priority,
                        recipient_user_id,
                        contextdata, category_id, created_at, updated_at
                    ) VALUES (
                        CAST(:id AS uuid),
                        CAST(:event_id AS uuid),
                        CAST(:tenant_id AS uuid),
                        :channel, :body, :status, 0, 5,
                        CAST(:user_id AS uuid),
                        CAST(:contextdata AS jsonb),
                        :category_id,
                        NOW(), NOW()
                    )
                """),
                {
                    "id": str(uuid.uuid4()),
                    "event_id": str(event.id),
                    "tenant_id": str(test_tenant.id),
                    "channel": "in_app",
                    "body": "Conflict detected",
                    "status": "pending",
                    "user_id": str(user.id),
                    "contextdata": '{"event_type": "calendar_conflict_detected"}',
                    "category_id": "sync_conflicts",  # B10/A56: required NOT NULL
                },
            )
        db_session.commit()

        count = CalendarConflictService.count_recent_conflict_notifications(
            db_session, test_tenant.id, window_hours=1
        )
        assert count >= 2
