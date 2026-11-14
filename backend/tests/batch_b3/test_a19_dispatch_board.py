"""
Batch B3 — A19 Test Coverage
==============================

A19: Dispatch Board API Endpoints (Optimistic Locking + SSE)

Test Coverage:
- Job ORM model has version field (integer, NOT NULL, default 1)
- JobTechAssignment ORM model has version field
- Job ORM model has variance_owner_notified_at and variance_last_notified_pct
- POST /api/v1/scheduling/jobs/{id}/move/test succeeds with correct version
- POST /api/v1/scheduling/jobs/{id}/move/test returns 409 on stale version
- POST /api/v1/scheduling/jobs/{id}/move/test returns 404 for unknown job
- POST /api/v1/scheduling/jobs/{id}/check-conflicts/test returns feasibility result
- dispatch_board_stream._channel_name formats correctly
- dispatch_board_stream._history_key formats correctly
- dispatch_board_stream._format_sse formats SSE string correctly
- sse_middleware module imports correctly
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlmodel import select

# ─────────────────────────────────────────────────────────────────────────────
# A19 — ORM model checks
# ─────────────────────────────────────────────────────────────────────────────


class TestA19ORMModels:
    """Verify new version and variance columns exist on Job and JobTechAssignment."""

    def test_job_has_version_field(self):
        from app.models.fulfillment import Job

        assert hasattr(Job, "version")

    def test_job_tech_assignment_has_version_field(self):
        from app.models.scheduling import JobTechAssignment

        assert hasattr(JobTechAssignment, "version")

    def test_job_has_variance_owner_notified_at(self):
        from app.models.fulfillment import Job

        assert hasattr(Job, "variance_owner_notified_at")

    def test_job_has_variance_last_notified_pct(self):
        from app.models.fulfillment import Job

        assert hasattr(Job, "variance_last_notified_pct")

    def test_job_version_default_is_1_in_db(self, db_session, test_tenant):
        """Verify newly created jobs get version=1 from server default."""
        from app.models.crm import Customer, Site
        from app.models.fulfillment import Job, JobStatus

        # Ensure job_status exists
        status = db_session.exec(
            select(JobStatus).where(JobStatus.tenant_id == test_tenant.id)
        ).first()
        if not status:
            status = JobStatus(
                id=uuid.uuid4(),
                tenant_id=test_tenant.id,
                code="open",
                name="Open",
                is_default=True,
                is_active=True,
            )
            db_session.add(status)
            db_session.flush()

        # Minimal customer/site
        customer = Customer(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            display_name=f"A19Test-{uuid.uuid4().hex[:8]}",
            is_active=True,
        )
        db_session.add(customer)
        db_session.flush()

        site = Site(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            customer_id=customer.id,
            name="Test Site",
            is_active=True,
        )
        db_session.add(site)
        db_session.flush()

        job = Job(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            customer_id=customer.id,
            site_id=site.id,
            status_id=status.id,
            is_active=True,
        )
        db_session.add(job)
        db_session.flush()
        db_session.refresh(job)

        assert job.version == 1


# ─────────────────────────────────────────────────────────────────────────────
# A19 — SSE service unit tests
# ─────────────────────────────────────────────────────────────────────────────


class TestA19DispatchBoardStream:
    """Unit tests for dispatch_board_stream helper functions."""

    def test_channel_name_format(self):
        from services.dispatch_board_stream import _channel_name

        tid = "abc123"
        assert _channel_name(tid) == "dispatch:abc123"

    def test_history_key_format(self):
        from services.dispatch_board_stream import _history_key

        tid = "abc123"
        assert _history_key(tid) == "dispatch_stream:abc123:events"

    def test_format_sse_output(self):
        from services.dispatch_board_stream import _format_sse

        result = _format_sse("job_rescheduled", {"job_id": "j1"}, "42")
        assert result.startswith("id: 42\n")
        assert "event: job_rescheduled\n" in result
        assert '"job_id": "j1"' in result
        assert result.endswith("\n\n")

    def test_make_event_id_is_unique(self):
        from services.dispatch_board_stream import _make_event_id

        ids = {_make_event_id() for _ in range(10)}
        assert len(ids) == 10

    def test_module_constants(self):
        from services import dispatch_board_stream as dbs

        assert dbs.CHANNEL_PREFIX == "dispatch"
        assert dbs.MAX_HISTORY_LEN == 100
        assert dbs.HEARTBEAT_INTERVAL_SECONDS == 15
        assert dbs.IDLE_TIMEOUT_SECONDS == 300

    def test_sse_middleware_imports(self):
        """sse_middleware module imports correctly."""
        from core.sse_middleware import validate_sse_token

        assert callable(validate_sse_token)


# ─────────────────────────────────────────────────────────────────────────────
# A19 — HTTP endpoint tests
# ─────────────────────────────────────────────────────────────────────────────


class TestA19JobMoveEndpoint:
    """HTTP tests for POST /api/v1/scheduling/jobs/{job_id}/move/test"""

    def _create_test_job(self, db_session, test_tenant, test_user):
        """Create minimal job for move endpoint tests."""
        from app.models.crm import Customer, Site
        from app.models.fulfillment import Job, JobStatus

        status = db_session.exec(
            select(JobStatus).where(JobStatus.tenant_id == test_tenant.id)
        ).first()
        if not status:
            status = JobStatus(
                id=uuid.uuid4(),
                tenant_id=test_tenant.id,
                code="open",
                name="Open",
                is_default=True,
                is_active=True,
            )
            db_session.add(status)
            db_session.flush()

        customer = Customer(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            display_name=f"MoveTest {uuid.uuid4()}",
            is_active=True,
        )
        db_session.add(customer)
        db_session.flush()

        site = Site(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            customer_id=customer.id,
            name="Test Site",
            is_active=True,
        )
        db_session.add(site)
        db_session.flush()

        job = Job(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            customer_id=customer.id,
            site_id=site.id,
            status_id=status.id,
            scheduled_start_at=datetime.now(UTC),
            scheduled_end_at=datetime.now(UTC) + timedelta(hours=2),
            is_active=True,
            version=1,
        )
        db_session.add(job)
        db_session.flush()
        db_session.refresh(job)
        return job

    def test_job_move_returns_200_with_correct_version(
        self, client, db_session, test_tenant, test_user
    ):
        """POST move with matching expected_job_version=1 returns 200."""
        job = self._create_test_job(db_session, test_tenant, test_user)
        new_start = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
        new_end = (datetime.now(UTC) + timedelta(hours=3)).isoformat()

        with pytest.MonkeyPatch.context() as mp:
            mp.setenv("TEST_ENDPOINT_ENABLED", "true")
            mp.setenv("ENVIRONMENT", "dev")
            resp = client.post(
                f"/api/v1/scheduling/jobs/{job.id}/move/test",
                json={
                    "tech_user_id": str(test_user.id),
                    "scheduled_start_at": new_start,
                    "scheduled_end_at": new_end,
                    "expected_job_version": 1,
                },
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["job_id"] == str(job.id)
        assert data["job_version"] == 2  # bumped from 1 to 2

    def test_job_move_returns_409_on_stale_version(
        self, client, db_session, test_tenant, test_user
    ):
        """POST move with stale expected_job_version returns 409."""
        job = self._create_test_job(db_session, test_tenant, test_user)
        new_start = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
        new_end = (datetime.now(UTC) + timedelta(hours=3)).isoformat()

        with pytest.MonkeyPatch.context() as mp:
            mp.setenv("TEST_ENDPOINT_ENABLED", "true")
            mp.setenv("ENVIRONMENT", "dev")
            resp = client.post(
                f"/api/v1/scheduling/jobs/{job.id}/move/test",
                json={
                    "tech_user_id": str(test_user.id),
                    "scheduled_start_at": new_start,
                    "scheduled_end_at": new_end,
                    "expected_job_version": 99,  # stale
                },
            )

        assert resp.status_code == 409
        data = resp.json()
        assert "current_job_version" in data.get("detail", {})

    def test_job_move_returns_404_for_unknown_job(self, client, test_tenant, test_user):
        """POST move for a UUID not in this tenant returns 404."""
        with pytest.MonkeyPatch.context() as mp:
            mp.setenv("TEST_ENDPOINT_ENABLED", "true")
            mp.setenv("ENVIRONMENT", "dev")
            resp = client.post(
                f"/api/v1/scheduling/jobs/{uuid.uuid4()}/move/test",
                json={
                    "tech_user_id": str(test_user.id),
                    "scheduled_start_at": datetime.now(UTC).isoformat(),
                    "scheduled_end_at": (
                        datetime.now(UTC) + timedelta(hours=2)
                    ).isoformat(),
                    "expected_job_version": 1,
                },
            )

        assert resp.status_code == 404


class TestA19CheckConflictsEndpoint:
    """HTTP tests for POST /api/v1/scheduling/jobs/{job_id}/check-conflicts/test"""

    def test_check_conflicts_returns_feasibility_result(
        self, client, test_tenant, test_user
    ):
        """POST check-conflicts returns a feasibility dict."""
        with pytest.MonkeyPatch.context() as mp:
            mp.setenv("TEST_ENDPOINT_ENABLED", "true")
            mp.setenv("ENVIRONMENT", "dev")
            resp = client.post(
                f"/api/v1/scheduling/jobs/{uuid.uuid4()}/check-conflicts/test",
                json={
                    "tech_user_id": str(test_user.id),
                    "scheduled_start_at": datetime.now(UTC).isoformat(),
                    "scheduled_end_at": (
                        datetime.now(UTC) + timedelta(hours=2)
                    ).isoformat(),
                },
            )

        assert resp.status_code == 200
        data = resp.json()
        assert "is_feasible" in data
        assert "conflicts" in data
