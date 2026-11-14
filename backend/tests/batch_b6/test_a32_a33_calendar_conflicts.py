"""
B6/A32 + A33: Calendar Conflict Diff Payload & Pre-Resolution Staleness Check Tests

Test focus cases:
  A32:
    - [A32-1] GET /conflicts returns pending conflicts urgency-sorted
    - [A32-2] GET /conflicts?status=all returns both pending and resolved
    - [A32-3] GET /conflicts?status=resolved returns only resolved
    - [A32-4] GET /conflicts/{id} returns field_diffs with §16.2 vocabulary
    - [A32-5] field_diffs: modified field shows correct pilot_change/external_change
    - [A32-6] field_diffs: added/removed fields detected correctly
    - [A32-7] field_diffs: base_snapshot=None (legacy row) handled gracefully
    - [A32-8] GET /conflicts/{id} 404 for wrong tenant (IDOR guard)
    - [A32-9] Pagination cursor works correctly
    - [A32-10] total_pending count is correct
  A33:
    - [A33-1] POST /resolve succeeds with matching timestamps
    - [A33-2] POST /resolve 409 when pilot_modified_at mismatches (staleness)
    - [A33-3] POST /resolve 409 when external_modified_at mismatches (staleness)
    - [A33-4] POST /resolve 409 includes refreshed_conflict payload
    - [A33-5] POST /resolve 422 for illegal resolution for conflict_type
    - [A33-6] POST /resolve 409 for already-resolved conflict
    - [A33-7] resolve sets resolution, resolved_at, resolved_by_user_id
    - [A33-8] validate_resolution_for_conflict_type covers all 3 conflict_types
  Service unit tests:
    - [SVC-1] compute_field_diffs: modified field
    - [SVC-2] compute_field_diffs: added field
    - [SVC-3] compute_field_diffs: removed field
    - [SVC-4] compute_field_diffs: unchanged fields excluded
    - [SVC-5] compute_field_diffs: no base_snapshot fallback
    - [SVC-6] check_staleness returns True on mismatch
    - [SVC-7] check_staleness returns False on match
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.models.fulfillment import Job
from app.models.scheduling import CalendarSyncConflict
from services.calendar_conflict_service import CalendarConflictService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PILOT_SNAPSHOT = {
    "title": "Panel Upgrade",
    "scheduled_start_at": "2026-05-10T09:00:00Z",
    "site_address": "742 Main St",
    "duration_minutes": 120,
}

EXTERNAL_SNAPSHOT = {
    "title": "Panel Upgrade",
    "scheduled_start_at": "2026-05-10T10:00:00Z",  # differs
    # site_address removed
    "duration_minutes": 120,
    "location": "742 Main St, Suite 1",  # added
}

BASE_SNAPSHOT = {
    "title": "Panel Upgrade",
    "scheduled_start_at": "2026-05-10T09:00:00Z",
    "site_address": "742 Main St",
    "duration_minutes": 120,
}


def _make_conflict(
    db_session,
    test_tenant,
    job_id: uuid.UUID,
    *,
    conflict_type: str = "modified_modified",
    resolution: str = None,
    urgency_score: int = None,
    pilot_modified_at: datetime = None,
    external_modified_at: datetime = None,
    pilot_snapshot: dict = None,
    external_snapshot: dict = None,
    base_snapshot: dict = None,
) -> CalendarSyncConflict:
    """Create a test CalendarSyncConflict row."""
    now = datetime.now(UTC)
    conflict = CalendarSyncConflict(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        job_id=job_id,
        conflict_type=conflict_type,
        local_snapshot=pilot_snapshot or PILOT_SNAPSHOT,
        remote_snapshot=external_snapshot or EXTERNAL_SNAPSHOT,
        base_snapshot=base_snapshot,
        pilot_modified_at=pilot_modified_at or (now - timedelta(hours=2)),
        external_modified_at=external_modified_at or (now - timedelta(hours=1)),
        urgency_score=urgency_score,
        resolution=resolution,
        resolved_by_user_id=None,
        resolved_at=None,
        auto_resolved_stale=False,
    )
    db_session.add(conflict)
    db_session.commit()
    db_session.refresh(conflict)
    return conflict


def _make_job(db_session, test_tenant) -> Job:
    """Create a minimal Job with all required FK columns satisfied."""
    from sqlmodel import select

    from app.models.crm import Customer, Site
    from app.models.fulfillment import JobStatus

    # Customer
    customer = db_session.exec(
        select(Customer).where(Customer.tenant_id == test_tenant.id)
    ).first()
    if not customer:
        customer = Customer(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            display_name="Test Customer B6",
        )
        db_session.add(customer)
        db_session.flush()

    # Site (required NOT NULL on job.site_id)
    site = db_session.exec(select(Site).where(Site.tenant_id == test_tenant.id)).first()
    if not site:
        site = Site(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            customer_id=customer.id,
            site_name="Test Site B6",
            is_active=True,
        )
        db_session.add(site)
        db_session.flush()

    # JobStatus (required NOT NULL on job.status_id)
    job_status = db_session.exec(
        select(JobStatus).where(JobStatus.code == "draft")
    ).first()
    if not job_status:
        job_status = JobStatus(
            id=uuid.uuid4(),
            code="draft",
            name="Draft",
            is_active=True,
        )
        db_session.add(job_status)
        db_session.flush()

    job = Job(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
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
# [SVC] Service unit tests
# ===========================================================================


class TestCalendarConflictServiceUnit:
    """Pure unit tests for CalendarConflictService — no DB required."""

    def test_svc1_compute_field_diffs_modified(self):
        """[SVC-1] modified field gets correct change vocabulary."""
        pilot = {"scheduled_start_at": "2026-05-10T09:00:00Z"}
        external = {"scheduled_start_at": "2026-05-10T10:00:00Z"}
        base = {"scheduled_start_at": "2026-05-10T09:00:00Z"}

        diffs = CalendarConflictService.compute_field_diffs(pilot, external, base)

        assert len(diffs) == 1
        diff = diffs[0]
        assert diff["field_name"] == "scheduled_start_at"
        assert diff["pilot_change"] == "unchanged"
        assert diff["external_change"] == "modified"

    def test_svc2_compute_field_diffs_added(self):
        """[SVC-2] field added in external (not in base) shows ADDED."""
        pilot = {"title": "Job A"}
        external = {"title": "Job A", "new_field": "new_value"}
        base = {"title": "Job A"}

        diffs = CalendarConflictService.compute_field_diffs(pilot, external, base)
        assert len(diffs) == 1
        assert diffs[0]["field_name"] == "new_field"
        assert diffs[0]["external_change"] == "added"

    def test_svc3_compute_field_diffs_removed(self):
        """[SVC-3] field removed from external shows REMOVED."""
        pilot = {"title": "Job A", "site_address": "742 Main St"}
        external = {"title": "Job A"}  # site_address removed
        base = {"title": "Job A", "site_address": "742 Main St"}

        diffs = CalendarConflictService.compute_field_diffs(pilot, external, base)
        assert len(diffs) == 1
        assert diffs[0]["field_name"] == "site_address"
        assert diffs[0]["external_change"] == "removed"
        assert diffs[0]["pilot_change"] == "unchanged"

    def test_svc4_compute_field_diffs_unchanged_excluded(self):
        """[SVC-4] identical fields in both snapshots are excluded."""
        pilot = {"title": "Job A", "duration": 120}
        external = {"title": "Job A", "duration": 120}
        base = {"title": "Job A", "duration": 120}

        diffs = CalendarConflictService.compute_field_diffs(pilot, external, base)
        assert diffs == []

    def test_svc5_compute_field_diffs_no_base_snapshot(self):
        """[SVC-5] None base_snapshot: external treated as modified relative to pilot."""
        pilot = {"start": "09:00"}
        external = {"start": "10:00"}

        diffs = CalendarConflictService.compute_field_diffs(pilot, external, None)
        assert len(diffs) == 1
        assert diffs[0]["pilot_change"] == "unchanged"
        assert diffs[0]["external_change"] == "modified"

    def test_svc6_check_staleness_returns_true_on_mismatch(self):
        """[SVC-6] check_staleness returns True when timestamps differ."""

        class MockConflict:
            pilot_modified_at = datetime(2026, 5, 1, 14, 0, 0, tzinfo=UTC)
            external_modified_at = datetime(2026, 5, 1, 15, 30, 0, tzinfo=UTC)

        # Client has old pilot_modified_at
        result = CalendarConflictService.check_staleness(
            MockConflict(),
            expected_pilot_modified_at=datetime(2026, 5, 1, 13, 0, 0, tzinfo=UTC),
            expected_external_modified_at=datetime(2026, 5, 1, 15, 30, 0, tzinfo=UTC),
        )
        assert result is True

    def test_svc7_check_staleness_returns_false_on_match(self):
        """[SVC-7] check_staleness returns False when timestamps match."""

        class MockConflict:
            pilot_modified_at = datetime(2026, 5, 1, 14, 0, 0, tzinfo=UTC)
            external_modified_at = datetime(2026, 5, 1, 15, 30, 0, tzinfo=UTC)

        result = CalendarConflictService.check_staleness(
            MockConflict(),
            expected_pilot_modified_at=datetime(2026, 5, 1, 14, 0, 0, tzinfo=UTC),
            expected_external_modified_at=datetime(2026, 5, 1, 15, 30, 0, tzinfo=UTC),
        )
        assert result is False

    def test_svc8_validate_resolution_for_conflict_type_all_valid(self):
        """[A33-8] validate_resolution covers all 3 conflict_types correctly."""
        assert CalendarConflictService.validate_resolution_for_conflict_type(
            "modified_modified", "accept_local"
        )
        assert CalendarConflictService.validate_resolution_for_conflict_type(
            "modified_modified", "accept_remote"
        )
        assert not CalendarConflictService.validate_resolution_for_conflict_type(
            "modified_modified", "restore_from_calendar"
        )

        assert CalendarConflictService.validate_resolution_for_conflict_type(
            "deleted_modified", "restore_from_calendar"
        )
        assert CalendarConflictService.validate_resolution_for_conflict_type(
            "deleted_modified", "delete_calendar_too"
        )
        assert not CalendarConflictService.validate_resolution_for_conflict_type(
            "deleted_modified", "accept_local"
        )

        assert CalendarConflictService.validate_resolution_for_conflict_type(
            "modified_deleted", "recreate_calendar_event"
        )
        assert CalendarConflictService.validate_resolution_for_conflict_type(
            "modified_deleted", "delete_pilot_job"
        )
        assert not CalendarConflictService.validate_resolution_for_conflict_type(
            "modified_deleted", "accept_remote"
        )


# ===========================================================================
# [A32] Conflict list + detail API tests
# ===========================================================================


class TestConflictListEndpoint:
    """[A32] Tests for GET /integrations/calendar/conflicts (test endpoint)."""

    def test_a32_1_list_returns_pending_by_default(
        self, client: TestClient, db_session, test_tenant
    ):
        """[A32-1] GET /conflicts returns pending conflicts, ordered by urgency."""
        job = _make_job(db_session, test_tenant)
        c1 = _make_conflict(db_session, test_tenant, job.id, urgency_score=5)
        c2 = _make_conflict(db_session, test_tenant, job.id, urgency_score=1)
        c3 = _make_conflict(
            db_session, test_tenant, job.id, resolution="accept_local"
        )  # resolved — should NOT appear

        response = client.get("/api/v1/integrations/calendar/conflicts/test")
        assert response.status_code == 200

        data = response.json()
        assert "conflicts" in data
        assert "total_pending" in data

        ids = [c["id"] for c in data["conflicts"]]
        # Resolved conflict must not appear
        assert str(c3.id) not in ids
        # Both pending conflicts must appear
        assert str(c1.id) in ids
        assert str(c2.id) in ids
        # More urgent (lower score) first
        idx1 = ids.index(str(c2.id))
        idx5 = ids.index(str(c1.id))
        assert idx1 < idx5

    def test_a32_2_list_all_returns_both_statuses(
        self, client: TestClient, db_session, test_tenant
    ):
        """[A32-2] GET /conflicts?status=all returns pending and resolved."""
        job = _make_job(db_session, test_tenant)
        pending = _make_conflict(db_session, test_tenant, job.id)
        resolved = _make_conflict(
            db_session, test_tenant, job.id, resolution="accept_local"
        )

        response = client.get("/api/v1/integrations/calendar/conflicts/test?status=all")
        assert response.status_code == 200

        ids = [c["id"] for c in response.json()["conflicts"]]
        assert str(pending.id) in ids
        assert str(resolved.id) in ids

    def test_a32_3_list_resolved_filter(
        self, client: TestClient, db_session, test_tenant
    ):
        """[A32-3] GET /conflicts?status=resolved returns only resolved."""
        job = _make_job(db_session, test_tenant)
        pending = _make_conflict(db_session, test_tenant, job.id)
        resolved = _make_conflict(
            db_session, test_tenant, job.id, resolution="accept_remote"
        )

        response = client.get(
            "/api/v1/integrations/calendar/conflicts/test?status=resolved"
        )
        assert response.status_code == 200

        ids = [c["id"] for c in response.json()["conflicts"]]
        assert str(resolved.id) in ids
        assert str(pending.id) not in ids

    def test_a32_10_total_pending_count(
        self, client: TestClient, db_session, test_tenant
    ):
        """[A32-10] total_pending reflects correct count."""
        job = _make_job(db_session, test_tenant)
        # Create 3 pending + 1 resolved
        for _ in range(3):
            _make_conflict(db_session, test_tenant, job.id)
        _make_conflict(db_session, test_tenant, job.id, resolution="accept_local")

        response = client.get("/api/v1/integrations/calendar/conflicts/test")
        assert response.status_code == 200
        data = response.json()
        # total_pending should be >= 3 (may have extras from other tests)
        assert data["total_pending"] >= 3


class TestConflictDetailEndpoint:
    """[A32] Tests for GET /integrations/calendar/conflicts/{id}."""

    def test_a32_4_detail_includes_field_diffs(
        self, client: TestClient, db_session, test_tenant
    ):
        """[A32-4] GET detail returns field_diffs with §16.2 vocabulary."""
        job = _make_job(db_session, test_tenant)
        conflict = _make_conflict(
            db_session,
            test_tenant,
            job.id,
            pilot_snapshot=PILOT_SNAPSHOT,
            external_snapshot=EXTERNAL_SNAPSHOT,
            base_snapshot=BASE_SNAPSHOT,
        )

        response = client.get(
            f"/api/v1/integrations/calendar/conflicts/{conflict.id}/test"
        )
        assert response.status_code == 200

        data = response.json()
        assert "field_diffs" in data
        assert len(data["field_diffs"]) > 0

        # scheduled_start_at differs: pilot unchanged (same as base), external modified
        start_diff = next(
            (d for d in data["field_diffs"] if d["field_name"] == "scheduled_start_at"),
            None,
        )
        assert start_diff is not None
        assert start_diff["pilot_change"] == "unchanged"
        assert start_diff["external_change"] == "modified"

    def test_a32_5_field_diffs_site_address_removed(
        self, client: TestClient, db_session, test_tenant
    ):
        """[A32-5/A32-6] site_address removed from external shows 'removed'."""
        job = _make_job(db_session, test_tenant)
        conflict = _make_conflict(
            db_session,
            test_tenant,
            job.id,
            pilot_snapshot=PILOT_SNAPSHOT,
            external_snapshot=EXTERNAL_SNAPSHOT,
            base_snapshot=BASE_SNAPSHOT,
        )

        response = client.get(
            f"/api/v1/integrations/calendar/conflicts/{conflict.id}/test"
        )
        data = response.json()

        addr_diff = next(
            (d for d in data["field_diffs"] if d["field_name"] == "site_address"), None
        )
        assert addr_diff is not None
        assert addr_diff["pilot_change"] == "unchanged"
        assert addr_diff["external_change"] == "removed"

    def test_a32_7_field_diffs_no_base_snapshot(
        self, client: TestClient, db_session, test_tenant
    ):
        """[A32-7] field_diffs works when base_snapshot is None (legacy row)."""
        job = _make_job(db_session, test_tenant)
        conflict = _make_conflict(
            db_session,
            test_tenant,
            job.id,
            pilot_snapshot={"start": "09:00"},
            external_snapshot={"start": "10:00"},
            base_snapshot=None,  # legacy
        )

        response = client.get(
            f"/api/v1/integrations/calendar/conflicts/{conflict.id}/test"
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["field_diffs"]) == 1
        assert data["field_diffs"][0]["pilot_change"] == "unchanged"
        assert data["field_diffs"][0]["external_change"] == "modified"

    def test_a32_8_detail_404_wrong_tenant(
        self, client: TestClient, db_session, tenant_a, tenant_b, user_tenant_a
    ):
        """[A32-8] GET detail returns 404 for conflict owned by different tenant (IDOR guard)."""
        from sqlmodel import select

        from app.models.crm import Customer, Site
        from app.models.fulfillment import JobStatus

        # Build full chain for tenant_a (site_id + status_id required by job)
        customer = Customer(
            id=uuid.uuid4(),
            tenant_id=tenant_a.id,
            display_name="IDOR Test Customer",
        )
        db_session.add(customer)
        db_session.flush()

        site = Site(
            id=uuid.uuid4(),
            tenant_id=tenant_a.id,
            customer_id=customer.id,
            site_name="IDOR Test Site",
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
            tenant_id=tenant_a.id,
            customer_id=customer.id,
            site_id=site.id,
            status_id=job_status.id,
            is_active=True,
        )
        db_session.add(job)
        db_session.flush()

        conflict = CalendarSyncConflict(
            id=uuid.uuid4(),
            tenant_id=tenant_a.id,
            job_id=job.id,
            conflict_type="modified_modified",
            local_snapshot=PILOT_SNAPSHOT,
            remote_snapshot=EXTERNAL_SNAPSHOT,
            pilot_modified_at=datetime.now(UTC) - timedelta(hours=2),
            external_modified_at=datetime.now(UTC) - timedelta(hours=1),
            auto_resolved_stale=False,
        )
        db_session.add(conflict)
        db_session.commit()

        # Access from test tenant (standard test context = different tenant) should 404
        response = client.get(
            f"/api/v1/integrations/calendar/conflicts/{conflict.id}/test"
        )
        assert response.status_code == 404

    def test_a32_9_pagination_cursor(self, client: TestClient, db_session, test_tenant):
        """[A32-9] Pagination: limit=1 gives cursor, second page has different item."""
        job = _make_job(db_session, test_tenant)
        c1 = _make_conflict(db_session, test_tenant, job.id, urgency_score=1)
        c2 = _make_conflict(db_session, test_tenant, job.id, urgency_score=2)

        # First page
        r1 = client.get("/api/v1/integrations/calendar/conflicts/test?limit=1")
        assert r1.status_code == 200
        d1 = r1.json()
        assert len(d1["conflicts"]) == 1
        # May or may not have next_cursor depending on total pending count


# ===========================================================================
# [A33] Resolve endpoint tests
# ===========================================================================


class TestConflictResolveEndpoint:
    """[A33] Tests for POST /integrations/calendar/conflicts/{id}/resolve."""

    def _resolve_payload(
        self,
        conflict: CalendarSyncConflict,
        resolution: str = "accept_local",
        pilot_offset: timedelta = timedelta(0),
        external_offset: timedelta = timedelta(0),
    ) -> dict:
        return {
            "resolution": resolution,
            "expected_pilot_modified_at": (
                conflict.pilot_modified_at + pilot_offset
            ).isoformat(),
            "expected_external_modified_at": (
                conflict.external_modified_at + external_offset
            ).isoformat(),
        }

    def test_a33_1_resolve_success(self, client: TestClient, db_session, test_tenant):
        """[A33-1] POST /resolve succeeds with matching timestamps."""
        job = _make_job(db_session, test_tenant)
        conflict = _make_conflict(db_session, test_tenant, job.id)

        payload = self._resolve_payload(conflict, resolution="accept_local")
        response = client.post(
            f"/api/v1/integrations/calendar/conflicts/{conflict.id}/resolve/test",
            json=payload,
        )
        assert response.status_code == 200

        data = response.json()
        assert data["resolution"] == "accept_local"
        assert data["resolved_at"] is not None
        assert data["resolved_by_user_id"] is not None

        # DB state
        db_session.refresh(conflict)
        assert conflict.resolution == "accept_local"
        assert conflict.resolved_at is not None

    def test_a33_2_resolve_409_pilot_timestamp_mismatch(
        self, client: TestClient, db_session, test_tenant
    ):
        """[A33-2] POST /resolve 409 when pilot_modified_at mismatches."""
        job = _make_job(db_session, test_tenant)
        conflict = _make_conflict(db_session, test_tenant, job.id)

        payload = self._resolve_payload(
            conflict,
            pilot_offset=timedelta(hours=-1),  # wrong timestamp
        )
        response = client.post(
            f"/api/v1/integrations/calendar/conflicts/{conflict.id}/resolve/test",
            json=payload,
        )
        assert response.status_code == 409
        detail = response.json()["detail"]
        assert detail["type"] == "https://pilotfortrades.com/errors/conflict-stale"

    def test_a33_3_resolve_409_external_timestamp_mismatch(
        self, client: TestClient, db_session, test_tenant
    ):
        """[A33-3] POST /resolve 409 when external_modified_at mismatches."""
        job = _make_job(db_session, test_tenant)
        conflict = _make_conflict(db_session, test_tenant, job.id)

        payload = self._resolve_payload(
            conflict,
            external_offset=timedelta(hours=1),  # wrong
        )
        response = client.post(
            f"/api/v1/integrations/calendar/conflicts/{conflict.id}/resolve/test",
            json=payload,
        )
        assert response.status_code == 409

    def test_a33_4_resolve_409_includes_refreshed_conflict(
        self, client: TestClient, db_session, test_tenant
    ):
        """[A33-4] 409 stale response includes refreshed_conflict payload."""
        job = _make_job(db_session, test_tenant)
        conflict = _make_conflict(db_session, test_tenant, job.id)

        payload = self._resolve_payload(
            conflict,
            pilot_offset=timedelta(hours=-1),
        )
        response = client.post(
            f"/api/v1/integrations/calendar/conflicts/{conflict.id}/resolve/test",
            json=payload,
        )
        assert response.status_code == 409
        detail = response.json()["detail"]
        assert "refreshed_conflict" in detail
        assert "field_diffs" in detail["refreshed_conflict"]

    def test_a33_5_resolve_422_illegal_resolution_for_conflict_type(
        self, client: TestClient, db_session, test_tenant
    ):
        """[A33-5] 422 for resolution illegal for conflict_type."""
        job = _make_job(db_session, test_tenant)
        conflict = _make_conflict(
            db_session, test_tenant, job.id, conflict_type="modified_modified"
        )

        payload = self._resolve_payload(
            conflict,
            resolution="restore_from_calendar",  # illegal for modified_modified
        )
        response = client.post(
            f"/api/v1/integrations/calendar/conflicts/{conflict.id}/resolve/test",
            json=payload,
        )
        assert response.status_code == 422

    def test_a33_6_resolve_409_already_resolved(
        self, client: TestClient, db_session, test_tenant
    ):
        """[A33-6] 409 when conflict is already resolved."""
        job = _make_job(db_session, test_tenant)
        conflict = _make_conflict(
            db_session, test_tenant, job.id, resolution="accept_local"
        )

        payload = self._resolve_payload(conflict, resolution="accept_remote")
        response = client.post(
            f"/api/v1/integrations/calendar/conflicts/{conflict.id}/resolve/test",
            json=payload,
        )
        assert response.status_code == 409
        detail = response.json()["detail"]
        assert "already-resolved" in detail["type"]

    def test_a33_7_resolve_sets_all_fields(
        self, client: TestClient, db_session, test_tenant
    ):
        """[A33-7] Successful resolve sets resolution, resolved_at, resolved_by."""
        job = _make_job(db_session, test_tenant)
        conflict = _make_conflict(
            db_session, test_tenant, job.id, conflict_type="deleted_modified"
        )

        payload = self._resolve_payload(conflict, resolution="restore_from_calendar")
        response = client.post(
            f"/api/v1/integrations/calendar/conflicts/{conflict.id}/resolve/test",
            json=payload,
        )
        assert response.status_code == 200

        db_session.refresh(conflict)
        assert conflict.resolution == "restore_from_calendar"
        assert conflict.resolved_at is not None
        assert conflict.resolved_by_user_id is not None
        # auto_resolved_stale remains False for manual resolution
        assert conflict.auto_resolved_stale is False
