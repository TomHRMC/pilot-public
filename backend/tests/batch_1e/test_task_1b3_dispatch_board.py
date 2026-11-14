"""
Task 1-B-3: Dispatch Board Query — API route tests

Covers:
  GET /api/v1/scheduling/dispatch-board/test?start_date=...&end_date=...

Key assertions:
  - Returns a DispatchBoardResponse with 'techs', 'unassigned', 'start_date', 'end_date'
  - Jobs with an active primary assignment appear under their tech_id group
  - Jobs with no active primary assignment appear in 'unassigned'
  - Jobs outside the query window are excluded
  - end_date <= start_date returns 400
  - Missing start_date or end_date returns 422

Fix applied May 2026: Replaced module-level TestClient with conftest `client` fixture
to prevent permanent DB writes. See backend/tests/README-adding-tests.md section
"The Module-Level TestClient Anti-Pattern" for full explanation.
"""

import uuid
from datetime import UTC, datetime, timedelta

SCHED_BASE = "/api/v1/scheduling"
JOBS_BASE = "/api/v1/jobs"
CUST_BASE = "/api/v1/customers"
SITES_BASE = "/api/v1/sites"

_TEST_USER_ID = "00000000-0000-0000-0000-000000000002"
_TEST_TENANT_ID = "00000000-0000-0000-0000-000000000001"

_NOW = datetime.now(UTC)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _dt(offset_days: float = 0, offset_hours: float = 0) -> str:
    return (_NOW + timedelta(days=offset_days, hours=offset_hours)).isoformat()


def _create_scheduled_job(
    client, start_offset_days: float = 1, duration_hours: float = 4
) -> str:
    """Create a job with scheduled_start_at/end in the future and return its ID."""
    cust = client.post(
        f"{CUST_BASE}/test",
        json={"display_name": f"DB Customer {uuid.uuid4().hex[:6]}", "type": "person"},
    )
    assert cust.status_code == 201
    site = client.post(
        f"{SITES_BASE}/test",
        json={"customer_id": cust.json()["id"]},
    )
    assert site.status_code == 201

    start = _dt(offset_days=start_offset_days)
    end = _dt(offset_days=start_offset_days, offset_hours=duration_hours)

    job = client.post(
        f"{JOBS_BASE}/test",
        json={
            "customer_id": cust.json()["id"],
            "site_id": site.json()["id"],
            "scheduled_start_at": start,
            "scheduled_end_at": end,
        },
    )
    assert job.status_code == 201, job.text
    return job.json()["id"]


def _board(client, start_offset: float = 0, end_offset: float = 3) -> dict:
    """Call the dispatch board test endpoint and return the JSON body."""
    resp = client.get(
        f"{SCHED_BASE}/dispatch-board/test",
        params={
            "start_date": _dt(offset_days=start_offset),
            "end_date": _dt(offset_days=end_offset),
        },
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


# ---------------------------------------------------------------------------
# Schema / basic structure
# ---------------------------------------------------------------------------


class TestDispatchBoardStructure:
    def test_returns_200_with_correct_shape(self, client):
        resp = client.get(
            f"{SCHED_BASE}/dispatch-board/test",
            params={
                "start_date": _dt(offset_days=10),
                "end_date": _dt(offset_days=12),
            },
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert "techs" in body
        assert "unassigned" in body
        assert "start_date" in body
        assert "end_date" in body
        assert isinstance(body["techs"], list)
        assert isinstance(body["unassigned"], list)

    def test_end_before_start_returns_400(self, client):
        resp = client.get(
            f"{SCHED_BASE}/dispatch-board/test",
            params={
                "start_date": _dt(offset_days=5),
                "end_date": _dt(offset_days=1),  # before start
            },
        )
        assert resp.status_code == 400
        assert "end_date" in resp.json()["detail"].lower()

    def test_equal_start_end_returns_400(self, client):
        ts = _dt(offset_days=5)
        resp = client.get(
            f"{SCHED_BASE}/dispatch-board/test",
            params={"start_date": ts, "end_date": ts},
        )
        assert resp.status_code == 400

    def test_missing_start_date_returns_422(self, client):
        resp = client.get(
            f"{SCHED_BASE}/dispatch-board/test",
            params={"end_date": _dt(offset_days=5)},
        )
        assert resp.status_code == 422

    def test_missing_end_date_returns_422(self, client):
        resp = client.get(
            f"{SCHED_BASE}/dispatch-board/test",
            params={"start_date": _dt(offset_days=1)},
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Unassigned bucket
# ---------------------------------------------------------------------------


class TestUnassignedJobs:
    def test_job_without_assignment_appears_in_unassigned(self, client):
        # Use a far-future window unique to this test to avoid interference
        offset = 50.0 + float(uuid.uuid4().int % 100) * 0.1
        job_id = _create_scheduled_job(client, start_offset_days=offset)

        board = client.get(
            f"{SCHED_BASE}/dispatch-board/test",
            params={
                "start_date": _dt(offset_days=offset - 0.5),
                "end_date": _dt(offset_days=offset + 1),
            },
        )
        assert board.status_code == 200
        unassigned_ids = [j["id"] for j in board.json()["unassigned"]]
        assert job_id in unassigned_ids

    def test_unassigned_job_not_in_any_tech_group(self, client):
        offset = 60.0 + float(uuid.uuid4().int % 100) * 0.1
        job_id = _create_scheduled_job(client, start_offset_days=offset)

        board = client.get(
            f"{SCHED_BASE}/dispatch-board/test",
            params={
                "start_date": _dt(offset_days=offset - 0.5),
                "end_date": _dt(offset_days=offset + 1),
            },
        ).json()

        all_tech_job_ids = [
            j["id"] for tech_group in board["techs"] for j in tech_group["jobs"]
        ]
        assert job_id not in all_tech_job_ids


# ---------------------------------------------------------------------------
# Assigned jobs — tech groups
# ---------------------------------------------------------------------------


class TestAssignedJobs:
    def test_assigned_job_appears_in_tech_group(self, client):
        offset = 70.0 + float(uuid.uuid4().int % 100) * 0.1
        job_id = _create_scheduled_job(client, start_offset_days=offset)

        # Assign the test user as primary
        assign_resp = client.post(
            f"{SCHED_BASE}/jobs/{job_id}/assignments/test",
            json={"user_id": _TEST_USER_ID, "role": "primary", "ordinal": 1},
        )
        assert assign_resp.status_code == 201

        board = client.get(
            f"{SCHED_BASE}/dispatch-board/test",
            params={
                "start_date": _dt(offset_days=offset - 0.5),
                "end_date": _dt(offset_days=offset + 1),
            },
        ).json()

        # The job must appear in the correct tech group
        found_in_tech = any(
            any(j["id"] == job_id for j in group["jobs"])
            for group in board["techs"]
            if group["tech_id"] == _TEST_USER_ID
        )
        assert found_in_tech, "Job not found in expected tech group"

        # The job must NOT appear in unassigned
        unassigned_ids = [j["id"] for j in board["unassigned"]]
        assert job_id not in unassigned_ids

    def test_tech_group_has_correct_tech_id(self, client):
        offset = 80.0 + float(uuid.uuid4().int % 100) * 0.1
        job_id = _create_scheduled_job(client, start_offset_days=offset)

        client.post(
            f"{SCHED_BASE}/jobs/{job_id}/assignments/test",
            json={"user_id": _TEST_USER_ID, "role": "primary", "ordinal": 1},
        )

        board = client.get(
            f"{SCHED_BASE}/dispatch-board/test",
            params={
                "start_date": _dt(offset_days=offset - 0.5),
                "end_date": _dt(offset_days=offset + 1),
            },
        ).json()

        matching_group = next(
            (g for g in board["techs"] if g["tech_id"] == _TEST_USER_ID), None
        )
        assert matching_group is not None
        job_ids_in_group = [j["id"] for j in matching_group["jobs"]]
        assert job_id in job_ids_in_group


# ---------------------------------------------------------------------------
# Window filtering
# ---------------------------------------------------------------------------


class TestWindowFiltering:
    def test_job_outside_window_not_returned(self, client):
        """A job scheduled at day+200 must not appear in a day+100 query."""
        far_job_id = _create_scheduled_job(client, start_offset_days=200)

        board = client.get(
            f"{SCHED_BASE}/dispatch-board/test",
            params={
                "start_date": _dt(offset_days=100),
                "end_date": _dt(offset_days=101),
            },
        ).json()

        all_ids = [j["id"] for j in board["unassigned"]] + [
            j["id"] for g in board["techs"] for j in g["jobs"]
        ]
        assert far_job_id not in all_ids

    def test_empty_window_returns_empty_board(self, client):
        """A window with no scheduled jobs should return empty techs and unassigned."""
        board = client.get(
            f"{SCHED_BASE}/dispatch-board/test",
            params={
                "start_date": _dt(offset_days=300),
                "end_date": _dt(offset_days=301),
            },
        ).json()

        assert board["techs"] == []
        assert board["unassigned"] == []


# ---------------------------------------------------------------------------
# Tenant isolation
# ---------------------------------------------------------------------------


class TestDispatchBoardTenantIsolation:
    def test_board_scoped_to_test_tenant(self, client):
        """All job entries in the board must belong to the test tenant."""
        offset = 90.0 + float(uuid.uuid4().int % 100) * 0.1
        job_id = _create_scheduled_job(client, start_offset_days=offset)

        board = client.get(
            f"{SCHED_BASE}/dispatch-board/test",
            params={
                "start_date": _dt(offset_days=offset - 0.5),
                "end_date": _dt(offset_days=offset + 1),
            },
        ).json()

        all_jobs = [j for j in board["unassigned"]] + [
            j for g in board["techs"] for j in g["jobs"]
        ]
        for job in all_jobs:
            assert job["tenant_id"] == _TEST_TENANT_ID
