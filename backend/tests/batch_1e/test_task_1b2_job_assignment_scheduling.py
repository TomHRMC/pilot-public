"""
Task 1-B-2: Job Assignment & Scheduling — API route tests

Covers:
  PATCH  /api/v1/scheduling/jobs/{job_id}/schedule/test   — update scheduled times
  POST   /api/v1/scheduling/jobs/{job_id}/assignments/test — assign tech (upsert)
  GET    /api/v1/scheduling/jobs/{job_id}/assignments/test — list assignments
  DELETE /api/v1/scheduling/jobs/{job_id}/assignments/{id}/test — soft-delete

Key business rule tested:
  - Assigning a new primary soft-deletes the current active primary first
    (upsert semantics — only one active primary per job at any time)

Note on user_id constraint:
  job_tech_assignment.user_id has a FK to user.id (RESTRICT).
  In tests we can only use _TEST_USER_ID (00000000-0000-0000-0000-000000000002)
  which is guaranteed to exist in the seeded database.  Random UUIDs will
  violate the FK and must NOT be used as user_id values.

Fix applied May 2026: Replaced module-level TestClient with conftest `client` fixture
to prevent permanent DB writes. See backend/tests/README-adding-tests.md §"The Module-Level
TestClient Anti-Pattern" for full explanation.
"""

import uuid
from datetime import UTC, datetime, timedelta

SCHED_BASE = "/api/v1/scheduling"
JOBS_BASE = "/api/v1/jobs"

_TEST_USER_ID = "00000000-0000-0000-0000-000000000002"
_TEST_TENANT_ID = "00000000-0000-0000-0000-000000000001"

_NOW = datetime.now(UTC)
_START = (_NOW + timedelta(days=1)).isoformat()
_END = (_NOW + timedelta(days=1, hours=4)).isoformat()
_START2 = (_NOW + timedelta(days=2)).isoformat()
_END2 = (_NOW + timedelta(days=2, hours=4)).isoformat()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_test_job(client) -> str:
    """Create a job via the existing jobs test endpoint and return its ID."""
    cust_resp = client.post(
        "/api/v1/customers/test",
        json={
            "display_name": f"Sched Test Customer {uuid.uuid4().hex[:6]}",
            "type": "person",
        },
    )
    assert cust_resp.status_code == 201, cust_resp.text
    customer_id = cust_resp.json()["id"]

    site_resp = client.post(
        "/api/v1/sites/test",
        json={"customer_id": customer_id},
    )
    assert site_resp.status_code == 201, site_resp.text
    site_id = site_resp.json()["id"]

    job_resp = client.post(
        f"{JOBS_BASE}/test",
        json={"customer_id": customer_id, "site_id": site_id},
    )
    assert job_resp.status_code == 201, job_resp.text
    return job_resp.json()["id"]


def _assign_payload(role: str = "primary", ordinal: int = 1) -> dict:
    """Use the seeded test user — the only user guaranteed to exist in the DB."""
    return {
        "user_id": _TEST_USER_ID,
        "role": role,
        "ordinal": ordinal,
    }


# ---------------------------------------------------------------------------
# Job Schedule Update (PATCH)
# ---------------------------------------------------------------------------


class TestUpdateJobSchedule:
    def test_patch_scheduled_times_returns_200(self, client):
        job_id = _create_test_job(client)
        resp = client.patch(
            f"{SCHED_BASE}/jobs/{job_id}/schedule/test",
            json={"scheduled_start_at": _START, "scheduled_end_at": _END},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["id"] == job_id
        assert body["scheduled_start_at"] is not None
        assert body["scheduled_end_at"] is not None

    def test_patch_estimated_duration(self, client):
        job_id = _create_test_job(client)
        resp = client.patch(
            f"{SCHED_BASE}/jobs/{job_id}/schedule/test",
            json={
                "scheduled_start_at": _START,
                "scheduled_end_at": _END,
                "estimated_duration_minutes": 240,
            },
        )
        assert resp.status_code == 200
        assert resp.json()["estimated_duration_minutes"] == 240

    def test_patch_external_calendar_event_id(self, client):
        job_id = _create_test_job(client)
        ext_id = f"google_evt_{uuid.uuid4().hex}"
        resp = client.patch(
            f"{SCHED_BASE}/jobs/{job_id}/schedule/test",
            json={
                "scheduled_start_at": _START,
                "scheduled_end_at": _END,
                "external_calendar_event_id": ext_id,
            },
        )
        assert resp.status_code == 200
        assert resp.json()["external_calendar_event_id"] == ext_id

    def test_patch_end_before_start_returns_400(self, client):
        job_id = _create_test_job(client)
        resp = client.patch(
            f"{SCHED_BASE}/jobs/{job_id}/schedule/test",
            json={
                "scheduled_start_at": _END,
                "scheduled_end_at": _START,
            },  # intentionally swapped
        )
        assert resp.status_code == 400
        assert "scheduled_end_at" in resp.json()["detail"].lower()

    def test_patch_only_start_without_end_returns_400(self, client):
        job_id = _create_test_job(client)
        resp = client.patch(
            f"{SCHED_BASE}/jobs/{job_id}/schedule/test",
            json={"scheduled_start_at": _START},  # missing end
        )
        assert resp.status_code == 400

    def test_patch_negative_duration_returns_400(self, client):
        job_id = _create_test_job(client)
        resp = client.patch(
            f"{SCHED_BASE}/jobs/{job_id}/schedule/test",
            json={
                "scheduled_start_at": _START,
                "scheduled_end_at": _END,
                "estimated_duration_minutes": -10,
            },
        )
        assert resp.status_code == 400

    def test_patch_unknown_job_returns_404(self, client):
        fake_id = str(uuid.uuid4())
        resp = client.patch(
            f"{SCHED_BASE}/jobs/{fake_id}/schedule/test",
            json={"scheduled_start_at": _START, "scheduled_end_at": _END},
        )
        assert resp.status_code == 404

    def test_patch_clears_scheduled_times_to_null(self, client):
        """Sending both start and end as null should clear schedule fields."""
        job_id = _create_test_job(client)
        # First set times
        client.patch(
            f"{SCHED_BASE}/jobs/{job_id}/schedule/test",
            json={"scheduled_start_at": _START, "scheduled_end_at": _END},
        )
        # Clear both to null
        resp = client.patch(
            f"{SCHED_BASE}/jobs/{job_id}/schedule/test",
            json={"scheduled_start_at": None, "scheduled_end_at": None},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["scheduled_start_at"] is None
        assert body["scheduled_end_at"] is None

    def test_patch_returns_tenant_id(self, client):
        job_id = _create_test_job(client)
        resp = client.patch(
            f"{SCHED_BASE}/jobs/{job_id}/schedule/test",
            json={"scheduled_start_at": _START, "scheduled_end_at": _END},
        )
        assert resp.json()["tenant_id"] == _TEST_TENANT_ID


# ---------------------------------------------------------------------------
# Assign Tech (POST) — upsert primary
# ---------------------------------------------------------------------------


class TestAssignTech:
    def test_assign_primary_returns_201(self, client):
        job_id = _create_test_job(client)
        resp = client.post(
            f"{SCHED_BASE}/jobs/{job_id}/assignments/test",
            json=_assign_payload(),
        )
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["job_id"] == job_id
        assert body["role"] == "primary"
        assert body["is_active"] is True
        assert body["tenant_id"] == _TEST_TENANT_ID

    def test_assign_helper_on_separate_job_returns_201(self, client):
        """Assign the test user as a helper on a separate job (different job_id = no uniqueness conflict)."""
        job_id = _create_test_job(client)
        resp = client.post(
            f"{SCHED_BASE}/jobs/{job_id}/assignments/test",
            json=_assign_payload(role="helper"),
        )
        assert resp.status_code == 201
        assert resp.json()["role"] == "helper"

    def test_reassign_primary_soft_deletes_old(self, client, db_session):
        """Assigning a new primary must soft-delete the current active primary.

        Uses the same test user both times: the upsert soft-deletes the first
        active primary record before creating the second, so the partial unique
        index (is_active=true AND role='primary') never has two live rows.
        """
        from sqlmodel import select

        from app.models.scheduling import JobTechAssignment

        job_id = _create_test_job(client)

        # First primary assignment
        first_resp = client.post(
            f"{SCHED_BASE}/jobs/{job_id}/assignments/test",
            json=_assign_payload(role="primary"),
        )
        assert first_resp.status_code == 201, first_resp.text
        first_id = first_resp.json()["id"]

        # Second primary assignment — same user, triggers upsert (soft-delete + new insert)
        second_resp = client.post(
            f"{SCHED_BASE}/jobs/{job_id}/assignments/test",
            json=_assign_payload(role="primary"),
        )
        assert second_resp.status_code == 201, second_resp.text
        second_id = second_resp.json()["id"]

        # Verify the first primary is now inactive in DB
        db_session.expire_all()
        first_record = db_session.exec(
            select(JobTechAssignment).where(JobTechAssignment.id == uuid.UUID(first_id))
        ).first()
        assert first_record is not None
        assert first_record.is_active is False

        # Verify the second primary is active
        second_record = db_session.exec(
            select(JobTechAssignment).where(
                JobTechAssignment.id == uuid.UUID(second_id)
            )
        ).first()
        assert second_record is not None
        assert second_record.is_active is True

    def test_only_one_active_primary_after_repeated_reassignment(self, client):
        """After 3 consecutive primary assignments, only 1 active primary must exist."""
        job_id = _create_test_job(client)

        for _ in range(3):
            client.post(
                f"{SCHED_BASE}/jobs/{job_id}/assignments/test",
                json=_assign_payload(role="primary"),
            )

        assignments = client.get(f"{SCHED_BASE}/jobs/{job_id}/assignments/test").json()
        primaries = [a for a in assignments if a["role"] == "primary"]
        assert len(primaries) == 1

    def test_assign_invalid_role_returns_400(self, client):
        job_id = _create_test_job(client)
        resp = client.post(
            f"{SCHED_BASE}/jobs/{job_id}/assignments/test",
            json={"user_id": _TEST_USER_ID, "role": "supervisor", "ordinal": 1},
        )
        assert resp.status_code == 400
        assert "role" in resp.json()["detail"].lower()

    def test_assign_zero_ordinal_returns_400(self, client):
        job_id = _create_test_job(client)
        resp = client.post(
            f"{SCHED_BASE}/jobs/{job_id}/assignments/test",
            json={"user_id": _TEST_USER_ID, "role": "primary", "ordinal": 0},
        )
        assert resp.status_code == 400

    def test_assign_unknown_job_returns_404(self, client):
        fake_id = str(uuid.uuid4())
        resp = client.post(
            f"{SCHED_BASE}/jobs/{fake_id}/assignments/test",
            json=_assign_payload(),
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# List Assignments (GET)
# ---------------------------------------------------------------------------


class TestListAssignments:
    def test_list_returns_200_and_is_list(self, client):
        job_id = _create_test_job(client)
        resp = client.get(f"{SCHED_BASE}/jobs/{job_id}/assignments/test")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_list_shows_newly_created_assignment(self, client):
        job_id = _create_test_job(client)
        client.post(
            f"{SCHED_BASE}/jobs/{job_id}/assignments/test",
            json=_assign_payload(),
        )
        resp = client.get(f"{SCHED_BASE}/jobs/{job_id}/assignments/test")
        assert len(resp.json()) >= 1
        assert all(a["is_active"] for a in resp.json())

    def test_list_excludes_soft_deleted_assignments(self, client):
        job_id = _create_test_job(client)
        assign_resp = client.post(
            f"{SCHED_BASE}/jobs/{job_id}/assignments/test",
            json=_assign_payload(),
        )
        assignment_id = assign_resp.json()["id"]

        # Soft-delete
        client.delete(f"{SCHED_BASE}/jobs/{job_id}/assignments/{assignment_id}/test")

        resp = client.get(f"{SCHED_BASE}/jobs/{job_id}/assignments/test")
        ids = [a["id"] for a in resp.json()]
        assert assignment_id not in ids

    def test_list_unknown_job_returns_404(self, client):
        fake_id = str(uuid.uuid4())
        resp = client.get(f"{SCHED_BASE}/jobs/{fake_id}/assignments/test")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Delete Assignment (soft-delete)
# ---------------------------------------------------------------------------


class TestDeleteAssignment:
    def test_delete_returns_200_with_message(self, client):
        job_id = _create_test_job(client)
        assign_resp = client.post(
            f"{SCHED_BASE}/jobs/{job_id}/assignments/test",
            json=_assign_payload(),
        )
        assignment_id = assign_resp.json()["id"]

        del_resp = client.delete(
            f"{SCHED_BASE}/jobs/{job_id}/assignments/{assignment_id}/test"
        )
        assert del_resp.status_code == 200
        body = del_resp.json()
        assert body["id"] == assignment_id
        assert "deactivated" in body["message"].lower()

    def test_delete_unknown_assignment_returns_404(self, client):
        job_id = _create_test_job(client)
        fake_assignment_id = str(uuid.uuid4())
        resp = client.delete(
            f"{SCHED_BASE}/jobs/{job_id}/assignments/{fake_assignment_id}/test"
        )
        assert resp.status_code == 404

    def test_delete_sets_is_active_false_in_db(self, client, db_session):
        from sqlmodel import select

        from app.models.scheduling import JobTechAssignment

        job_id = _create_test_job(client)
        assign_resp = client.post(
            f"{SCHED_BASE}/jobs/{job_id}/assignments/test",
            json=_assign_payload(),
        )
        assignment_id = assign_resp.json()["id"]

        client.delete(f"{SCHED_BASE}/jobs/{job_id}/assignments/{assignment_id}/test")

        db_session.expire_all()
        record = db_session.exec(
            select(JobTechAssignment).where(
                JobTechAssignment.id == uuid.UUID(assignment_id)
            )
        ).first()
        assert record is not None
        assert record.is_active is False


# ---------------------------------------------------------------------------
# Tenant Isolation
# ---------------------------------------------------------------------------


class TestAssignmentTenantIsolation:
    def test_assignment_scoped_to_test_tenant(self, client):
        job_id = _create_test_job(client)
        resp = client.post(
            f"{SCHED_BASE}/jobs/{job_id}/assignments/test",
            json=_assign_payload(),
        )
        assert resp.json()["tenant_id"] == _TEST_TENANT_ID

    def test_schedule_update_scoped_to_test_tenant(self, client):
        job_id = _create_test_job(client)
        resp = client.patch(
            f"{SCHED_BASE}/jobs/{job_id}/schedule/test",
            json={"scheduled_start_at": _START, "scheduled_end_at": _END},
        )
        assert resp.json()["tenant_id"] == _TEST_TENANT_ID
