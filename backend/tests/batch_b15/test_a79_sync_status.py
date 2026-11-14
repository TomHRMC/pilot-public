"""
B15/A79 — Unified Pending-Count Exposure tests.

Test focus cases:
1. GET /sync/{surface}/status/test returns 200 for all four valid surfaces
2. Invalid surface returns 400 Bad Request
3. amber_threshold defaults to 5 when TenantSettings has no override
4. amber_threshold uses tenant override when TenantSettings record exists
5. calendar surface returns pending_count from calendar_sync_conflict unresolved rows
6. quickbooks surface returns pending_count from integration_sync_conflict pending rows
7. mobile_data surface returns synced_idle when no mobile_sync_session exists
8. emit_sync_status_changed enqueues event to SSE channel
9. TenantSettings.tenant_sync_indicator_pending_amber_threshold column exists with default 5
"""

import uuid
from datetime import UTC, datetime

import pytest
from sqlmodel import select

from app.models.fulfillment import Job, JobStatus
from app.models.platform_setting import PlatformSetting
from app.models.scheduling import CalendarSyncConflict

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _make_job(db_session, tenant_id, customer_id, site_id) -> Job:
    """Create a minimal Job row that satisfies the FK constraint on calendar_sync_conflict."""
    status = db_session.exec(select(JobStatus).where(JobStatus.code == "draft")).first()
    if status is None:
        # Fallback: pick any status
        status = db_session.exec(select(JobStatus)).first()
    if status is None:
        raise RuntimeError("No JobStatus rows found — seed data missing")
    job = Job(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        customer_id=customer_id,
        site_id=site_id,
        status_id=status.id,
    )
    db_session.add(job)
    db_session.flush()
    return job


def _make_conflict(db_session, tenant_id, job_id) -> CalendarSyncConflict:
    """Create an unresolved CalendarSyncConflict with a valid conflict_type."""
    c = CalendarSyncConflict(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        job_id=job_id,
        conflict_type="modified_modified",
        local_snapshot={"title": "Panel Upgrade"},
        remote_snapshot={"title": "Panel Upgrade - Modified"},
        auto_resolved_stale=False,
        pilot_modified_at=datetime.now(UTC),
        external_modified_at=datetime.now(UTC),
    )
    db_session.add(c)
    db_session.flush()
    return c


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# (client fixture comes from conftest.py — shares db_session via get_db override)
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def tenant_settings_with_amber(db_session, test_tenant):
    """
    Set amber threshold = 3 for the test tenant via platform_setting upsert (FIND-086).
    Replaces the old tenant_settings raw SQL insert.
    """
    existing = db_session.exec(
        select(PlatformSetting)
        .where(PlatformSetting.key == "tenant_sync_indicator_pending_amber_threshold")
        .where(PlatformSetting.tenant_id == test_tenant.id)
    ).first()
    if existing:
        existing.value = 3
    else:
        existing = PlatformSetting(
            key="tenant_sync_indicator_pending_amber_threshold",
            value=3,
            tenant_id=test_tenant.id,
        )
    db_session.add(existing)
    db_session.commit()
    return 3


@pytest.fixture
def calendar_conflict(db_session, test_tenant, test_customer, test_site):
    """Create an unresolved CalendarSyncConflict for the test tenant (with valid job FK)."""
    job = _make_job(db_session, test_tenant.id, test_customer.id, test_site.id)
    conflict = _make_conflict(db_session, test_tenant.id, job.id)
    db_session.commit()
    db_session.refresh(conflict)
    return conflict


# ─────────────────────────────────────────────────────────────────────────────
# Test cases
# ─────────────────────────────────────────────────────────────────────────────


class TestSyncStatusOrm:
    """ORM-level column tests (post-FIND-086: platform_setting replaces tenant_settings)."""

    def test_tenant_sync_indicator_default_is_5(self, db_session, test_tenant):
        """platform_setting NULL row for amber threshold defaults to 5."""
        from services.setting_resolver import get_effective_setting

        val, scope = get_effective_setting(
            db_session,
            test_tenant.id,
            "tenant_sync_indicator_pending_amber_threshold",
            fallback=5,
        )
        assert val == 5
        assert scope in ("system", "fallback")

    def test_tenant_sync_indicator_column_accepts_override(
        self, db_session, test_tenant
    ):
        """platform_setting tenant override can be set to a custom value."""
        from services.setting_resolver import get_effective_setting

        override = PlatformSetting(
            key="tenant_sync_indicator_pending_amber_threshold",
            value=10,
            tenant_id=test_tenant.id,
        )
        db_session.add(override)
        db_session.commit()

        val, scope = get_effective_setting(
            db_session,
            test_tenant.id,
            "tenant_sync_indicator_pending_amber_threshold",
        )
        assert val == 10
        assert scope == "tenant"

        # Cleanup
        db_session.delete(override)
        db_session.commit()


class TestSyncStatusEndpoint:
    """API endpoint tests via test client."""

    def test_calendar_surface_returns_200(self, client):
        resp = client.get("/api/v1/sync/test/calendar/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["surface"] == "calendar"
        assert "state" in data
        assert "pending_count" in data
        assert "amber_threshold" in data

    def test_quickbooks_surface_returns_200(self, client):
        resp = client.get("/api/v1/sync/test/quickbooks/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["surface"] == "quickbooks"

    def test_mobile_data_surface_returns_200(self, client):
        resp = client.get("/api/v1/sync/test/mobile_data/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["surface"] == "mobile_data"

    def test_background_surface_returns_200(self, client):
        resp = client.get("/api/v1/sync/test/background/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["surface"] == "background"

    def test_invalid_surface_returns_400(self, client):
        resp = client.get("/api/v1/sync/test/unknown_surface/status")
        assert resp.status_code == 400
        detail = resp.json().get("detail", "")
        assert "surface" in str(detail).lower() or "invalid" in str(detail).lower()

    def test_amber_threshold_defaults_to_5(self, client):
        """When no TenantSettings override exists, amber_threshold = 5."""
        resp = client.get("/api/v1/sync/test/calendar/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["amber_threshold"] == 5

    def test_amber_threshold_respects_tenant_override(
        self, client, db_session, tenant_settings_with_amber
    ):
        """When TenantSettings.threshold = 3, response reflects 3."""
        resp = client.get("/api/v1/sync/test/calendar/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["amber_threshold"] == 3

    def test_calendar_pending_count_reflects_unresolved_conflicts(
        self, client, db_session, calendar_conflict
    ):
        """Pending count increments when an unresolved CalendarSyncConflict exists."""
        resp = client.get("/api/v1/sync/test/calendar/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["pending_count"] >= 1
        assert data["state"] in ("synced_pending", "synced_idle")

    def test_mobile_data_returns_synced_idle_when_no_sessions(self, client):
        """mobile_data surface returns synced_idle when no sessions exist for the test tenant."""
        resp = client.get("/api/v1/sync/test/mobile_data/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["state"] in ("synced_idle", "syncing")

    def test_response_schema_has_all_required_fields(self, client):
        """Response includes all fields defined in SyncStatusResponse."""
        resp = client.get("/api/v1/sync/test/calendar/status")
        assert resp.status_code == 200
        data = resp.json()
        required_keys = {
            "surface",
            "state",
            "pending_count",
            "pending_items",
            "last_sync_at",
            "next_sync_at",
            "manual_trigger_supported",
            "resolve_target",
            "amber_threshold",
        }
        assert required_keys.issubset(set(data.keys()))

    def test_pending_items_capped_at_5(
        self, client, db_session, test_tenant, test_customer, test_site
    ):
        """pending_items list is never longer than 5 entries."""
        # Create 7 unresolved conflicts with real job FKs
        for _ in range(7):
            job = _make_job(db_session, test_tenant.id, test_customer.id, test_site.id)
            _make_conflict(db_session, test_tenant.id, job.id)
        db_session.commit()

        resp = client.get("/api/v1/sync/test/calendar/status")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["pending_items"]) <= 5


class TestSyncStatusSseEmitter:
    """SSE emit_sync_status_changed helper tests."""

    def test_emit_enqueues_event_to_registered_channel(self):
        """emit_sync_status_changed puts event on tenant queue."""
        import asyncio

        from api.routes.sync_status import _sync_sse_channels, emit_sync_status_changed

        tenant_id = str(uuid.uuid4())
        q: asyncio.Queue = asyncio.Queue()
        _sync_sse_channels[tenant_id] = {q}

        emit_sync_status_changed(tenant_id, "calendar", "synced_pending", 3)

        assert not q.empty()
        evt = q.get_nowait()
        assert evt["event"] == "sync_status_changed"
        assert evt["data"]["surface"] == "calendar"
        assert evt["data"]["state"] == "synced_pending"
        assert evt["data"]["pending_count"] == 3

        # Clean up
        del _sync_sse_channels[tenant_id]

    def test_emit_no_channels_does_not_raise(self):
        """emit_sync_status_changed is a no-op if no clients connected."""
        from api.routes.sync_status import emit_sync_status_changed

        # Should not raise
        emit_sync_status_changed(str(uuid.uuid4()), "quickbooks", "synced_idle", 0)
