"""
Task 1-B-4: Conflict Detection Service -- API route tests

Covers:
  POST /api/v1/scheduling/conflict-check/test

Validates:
  - Feasible slot (no conflicts) -> is_feasible=True, conflicts=[]
  - PTO block overlap -> is_feasible=False, conflict_type='availability_block'
  - Unavailable block overlap -> is_feasible=False, conflict_type='availability_block'
  - Double-booking on another job -> is_feasible=False, conflict_type='double_booking'
  - exclude_job_id skips that job in double-booking check
  - proposed_end <= proposed_start returns 400
  - working_hours availability type is NOT treated as a blocking conflict

Double-booking tests use UUID-seeded large day offsets (1000+, 2000+, 3000+) to
guarantee each test run lands on a unique date window and avoids leftover DB
rows from prior runs polluting the overlap check.

Fix applied May 2026: Replaced module-level TestClient with conftest `client` fixture
to prevent permanent DB writes. See backend/tests/README-adding-tests.md §"The Module-Level
TestClient Anti-Pattern" for full explanation.
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


def _purge_stale_availability_records():
    """Delete any orphan availability records for _TEST_USER_ID left by prior test sessions.

    This prevents 'test_adjacent_pto_no_overlap_is_feasible' from failing due to
    stale working_hours or pto records accumulated before cleanup was fixed.
    Called once at module import time.
    """
    from sqlalchemy import text

    from core.db import engine

    with engine.connect() as conn:
        conn.execute(
            text(
                "DELETE FROM tech_availability "
                "WHERE user_id = :uid "
                "  AND availability_type IN ('working_hours', 'pto', 'unavailable')"
            ).bindparams(uid=_TEST_USER_ID)
        )
        conn.commit()


def _purge_stale_job_records():
    """Delete any orphan job records for _TEST_USER_ID left by prior test sessions.

    This prevents double-booking conflict tests from failing due to stale job
    assignments accumulated before cleanup was fixed.
    Called once at module import time.

    Deletes all RESTRICT-FK child rows before deleting jobs to avoid constraint
    violations from tables that reference job.id with ON DELETE RESTRICT.
    """
    from sqlalchemy import text

    from core.db import engine

    _cutoff = datetime(2000, 1, 1, tzinfo=UTC)

    with engine.connect() as conn:
        # Collect stale job IDs first so we can delete child rows by job_id
        rows = conn.execute(
            text(
                "SELECT id FROM job "
                "WHERE tenant_id = :tid AND scheduled_start_at > :cutoff"
            ).bindparams(tid=_TEST_TENANT_ID, cutoff=_cutoff)
        ).fetchall()
        stale_ids = [str(r[0]) for r in rows]

        if stale_ids:
            id_list = ", ".join(f"'{jid}'" for jid in stale_ids)
            # Delete all child tables with RESTRICT FK on job.id
            for child_table, col in [
                ("job_tech_assignment", "job_id"),
                ("job_notes", "job_id"),
                ("job_attachment", "job_id"),
                ("job_time_entry", "job_id"),
                ("job_expense", "job_id"),
                ("loto_confirmation", "job_id"),
                ("calendar_sync_conflict", "job_id"),
                ("quote", "job_id"),
            ]:
                conn.execute(
                    text(f"DELETE FROM {child_table} WHERE {col}::text IN ({id_list})")
                )
            conn.commit()

        # Also delete any remaining job_tech_assignment for _TEST_USER_ID (belt+suspenders)
        conn.execute(
            text("DELETE FROM job_tech_assignment WHERE user_id = :uid").bindparams(
                uid=_TEST_USER_ID
            )
        )
        conn.commit()

        # Now safe to delete the stale jobs
        conn.execute(
            text(
                "DELETE FROM job "
                "WHERE tenant_id = :tid "
                "  AND scheduled_start_at > :cutoff"
            ).bindparams(tid=_TEST_TENANT_ID, cutoff=_cutoff)
        )
        conn.commit()


# Purge stale records at module load — idempotent, safe to run on every import
try:
    _purge_stale_availability_records()
    _purge_stale_job_records()
except Exception:
    pass  # If DB not available during import (e.g., collection-only), skip silently


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


import pytest


@pytest.fixture(scope="class", autouse=True)
def cleanup_stale_jobs():
    """Clean up stale job records before and after each test class.

    This prevents job assignments from accumulating across test classes within
    a single pytest session, which would cause double-booking conflict tests to fail.
    """
    try:
        _purge_stale_job_records()
    except Exception:
        pass  # If DB not available during fixture setup, skip silently
    yield
    try:
        _purge_stale_job_records()
    except Exception:
        pass  # If DB not available during fixture cleanup, skip silently


def _dt(offset_days: float = 0, offset_hours: float = 0) -> str:
    """Return an ISO-8601 datetime string offset from _NOW."""
    return (_NOW + timedelta(days=offset_days, hours=offset_hours)).isoformat()


def _conflict_check(
    client,
    tech_user_id: str,
    proposed_start: str,
    proposed_end: str,
    exclude_job_id: str | None = None,
):
    payload = {
        "tech_user_id": tech_user_id,
        "proposed_start": proposed_start,
        "proposed_end": proposed_end,
    }
    if exclude_job_id:
        payload["exclude_job_id"] = exclude_job_id
    return client.post(f"{SCHED_BASE}/conflict-check/test", json=payload)


def _create_pto(client, starts_at: str, ends_at: str) -> str:
    resp = client.post(
        f"{SCHED_BASE}/tech-availability/test",
        json={
            "user_id": _TEST_USER_ID,
            "availability_type": "pto",
            "starts_at": starts_at,
            "ends_at": ends_at,
            "notes": "Test PTO",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _create_unavailable(client, starts_at: str, ends_at: str) -> str:
    resp = client.post(
        f"{SCHED_BASE}/tech-availability/test",
        json={
            "user_id": _TEST_USER_ID,
            "availability_type": "unavailable",
            "starts_at": starts_at,
            "ends_at": ends_at,
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _create_scheduled_assigned_job(
    client,
    start_days: float,
    start_hours: float = 0,
    duration_hours: float = 4,
) -> str:
    """Create a job with scheduled times and assign test user as primary.

    Returns the job ID.
    """
    cust = client.post(
        f"{CUST_BASE}/test",
        json={"display_name": f"CC Customer {uuid.uuid4().hex[:6]}", "type": "person"},
    )
    assert cust.status_code == 201
    site = client.post(f"{SITES_BASE}/test", json={"customer_id": cust.json()["id"]})
    assert site.status_code == 201

    job_start = _dt(offset_days=start_days, offset_hours=start_hours)
    job_end = _dt(offset_days=start_days, offset_hours=start_hours + duration_hours)

    job = client.post(
        f"{JOBS_BASE}/test",
        json={
            "customer_id": cust.json()["id"],
            "site_id": site.json()["id"],
            "scheduled_start_at": job_start,
            "scheduled_end_at": job_end,
        },
    )
    assert job.status_code == 201, job.text
    job_id = job.json()["id"]

    assign = client.post(
        f"{SCHED_BASE}/jobs/{job_id}/assignments/test",
        json={"user_id": _TEST_USER_ID, "role": "primary", "ordinal": 1},
    )
    assert assign.status_code == 201, assign.text
    return job_id


# ---------------------------------------------------------------------------
# Feasible slots (no conflicts)
# ---------------------------------------------------------------------------


class TestFeasibleSlot:
    def test_clean_slot_is_feasible(self, client):
        """A far-future slot with no PTO and no other jobs -> feasible."""
        resp = _conflict_check(
            client,
            tech_user_id=_TEST_USER_ID,
            proposed_start=_dt(offset_days=500),
            proposed_end=_dt(offset_days=500, offset_hours=4),
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["is_feasible"] is True
        assert body["conflicts"] == []

    def test_response_echoes_proposed_times(self, client):
        start = _dt(offset_days=501)
        end = _dt(offset_days=501, offset_hours=3)
        resp = _conflict_check(
            client,
            tech_user_id=_TEST_USER_ID,
            proposed_start=start,
            proposed_end=end,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["tech_user_id"] == _TEST_USER_ID
        assert "proposed_start" in body
        assert "proposed_end" in body


# ---------------------------------------------------------------------------
# Availability block conflicts
# ---------------------------------------------------------------------------


class TestAvailabilityBlockConflicts:
    def test_pto_overlap_makes_infeasible(self, client):
        """A PTO block overlapping the proposed slot -> availability_block conflict."""
        pto_id = _create_pto(
            client,
            starts_at=_dt(offset_days=200),
            ends_at=_dt(offset_days=202),
        )
        try:
            resp = _conflict_check(
                client,
                tech_user_id=_TEST_USER_ID,
                proposed_start=_dt(offset_days=200, offset_hours=6),
                proposed_end=_dt(offset_days=200, offset_hours=10),
            )
            assert resp.status_code == 200
            body = resp.json()
            assert body["is_feasible"] is False
            assert any(
                c["conflict_type"] == "availability_block" for c in body["conflicts"]
            )
        finally:
            client.delete(f"{SCHED_BASE}/tech-availability/test/{pto_id}")

    def test_unavailable_block_overlap_makes_infeasible(self, client):
        unavail_id = _create_unavailable(
            client,
            starts_at=_dt(offset_days=210),
            ends_at=_dt(offset_days=211),
        )
        try:
            resp = _conflict_check(
                client,
                tech_user_id=_TEST_USER_ID,
                proposed_start=_dt(offset_days=210),
                proposed_end=_dt(offset_days=210, offset_hours=4),
            )
            body = resp.json()
            assert body["is_feasible"] is False
            assert any(
                c["conflict_type"] == "availability_block" for c in body["conflicts"]
            )
        finally:
            client.delete(f"{SCHED_BASE}/tech-availability/test/{unavail_id}")

    def test_pto_block_entirely_contains_proposed_slot_is_conflict(self, client):
        pto_id = _create_pto(
            client,
            starts_at=_dt(offset_days=220),
            ends_at=_dt(offset_days=223),
        )
        try:
            resp = _conflict_check(
                client,
                tech_user_id=_TEST_USER_ID,
                proposed_start=_dt(offset_days=221),
                proposed_end=_dt(offset_days=222),
            )
            assert resp.json()["is_feasible"] is False
        finally:
            client.delete(f"{SCHED_BASE}/tech-availability/test/{pto_id}")

    def test_adjacent_pto_no_overlap_is_feasible(self, client):
        """PTO ends exactly when proposed starts -- touching, not overlapping -> feasible.

        Fix: always delete the PTO record created by this test to prevent accumulation
        across test runs (1,100+ rows were building up in the DB, polluting future runs).
        Also: purge ALL stale availability records before test to clear prior test debris.
        """
        # Pre-cleanup: remove all stale availability records for this user from prior runs
        # This ensures we don't have old PTO/unavailable blocks interfering with the test
        from sqlalchemy import text

        from core.db import engine

        with engine.connect() as conn:
            conn.execute(
                text(
                    "DELETE FROM tech_availability "
                    "WHERE user_id = :uid "
                    "  AND availability_type IN ('pto', 'unavailable')"
                ).bindparams(uid=_TEST_USER_ID)
            )
            conn.commit()

        # UUID-seeded offset in a large range to minimize collision with other tests
        base = 4000 + (uuid.uuid4().int % 500)
        pto_id = _create_pto(
            client,
            starts_at=_dt(offset_days=base),
            ends_at=_dt(offset_days=base + 1),
        )
        try:
            resp = _conflict_check(
                client,
                tech_user_id=_TEST_USER_ID,
                proposed_start=_dt(offset_days=base + 1),
                proposed_end=_dt(offset_days=base + 2),
            )
            assert resp.json()["is_feasible"] is True
        finally:
            # Always delete the PTO to prevent DB row accumulation across test runs
            client.delete(f"{SCHED_BASE}/tech-availability/test/{pto_id}")

    def test_working_hours_type_does_not_block_slot(self, client):
        """working_hours availability records are NOT treated as blocking conflicts."""
        create_resp = client.post(
            f"{SCHED_BASE}/tech-availability/test",
            json={
                "user_id": _TEST_USER_ID,
                "availability_type": "working_hours",
                "recurrence_rrule": "FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR;BYHOUR=8;BYMINUTE=0",
            },
        )
        assert create_resp.status_code == 201, create_resp.text
        record_id = create_resp.json()["id"]
        try:
            resp = _conflict_check(
                client,
                tech_user_id=_TEST_USER_ID,
                proposed_start=_dt(offset_days=502),
                proposed_end=_dt(offset_days=502, offset_hours=4),
            )
            body = resp.json()
            availability_conflicts = [
                c
                for c in body["conflicts"]
                if c["conflict_type"] == "availability_block"
            ]
            assert len(availability_conflicts) == 0
        finally:
            # Always delete the availability record to prevent DB row accumulation
            # across test runs — missing cleanup was causing test_adjacent_pto_no_overlap_is_feasible
            # to fail non-deterministically (orphan records polluted conflict queries)
            client.delete(f"{SCHED_BASE}/tech-availability/test/{record_id}")


# ---------------------------------------------------------------------------
# Double-booking conflicts
#
# UUID-seeded offsets ensure each test run lands on a unique date window,
# preventing leftover rows from prior test runs from polluting results.
# ---------------------------------------------------------------------------


class TestDoubleBookingConflicts:
    def setup_method(self):
        """Clean up stale job records before each test method in this class."""
        try:
            _purge_stale_job_records()
        except Exception:
            pass  # If DB not available, skip silently

    def test_overlapping_job_makes_infeasible(self, client):
        """Tech is assigned to a job; proposed slot overlaps -> double_booking conflict."""
        base = 1000 + (uuid.uuid4().int % 500)
        _create_scheduled_assigned_job(
            client, start_days=base, start_hours=0, duration_hours=4
        )

        resp = _conflict_check(
            client,
            tech_user_id=_TEST_USER_ID,
            proposed_start=_dt(offset_days=base, offset_hours=2),
            proposed_end=_dt(offset_days=base, offset_hours=3),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["is_feasible"] is False
        assert any(c["conflict_type"] == "double_booking" for c in body["conflicts"])

    def test_non_overlapping_job_is_feasible(self, client):
        """Job ends at base+4h; proposed slot starts at base+6h -> no conflict."""
        base = 2000 + (uuid.uuid4().int % 500)
        _create_scheduled_assigned_job(
            client, start_days=base, start_hours=0, duration_hours=4
        )

        resp = _conflict_check(
            client,
            tech_user_id=_TEST_USER_ID,
            proposed_start=_dt(offset_days=base, offset_hours=6),
            proposed_end=_dt(offset_days=base, offset_hours=9),
        )
        body = resp.json()
        double_bookings = [
            c for c in body["conflicts"] if c["conflict_type"] == "double_booking"
        ]
        assert len(double_bookings) == 0

    def test_exclude_job_id_skips_that_job(self, client):
        """exclude_job_id must suppress the double-booking check for that specific job.

        Creates a job at a unique far-future offset, then verifies:
          - without exclusion: conflict detected
          - with exclusion: no double-booking for that job
        """
        base = 3000 + (uuid.uuid4().int % 500)
        job_id = _create_scheduled_assigned_job(
            client, start_days=base, start_hours=0, duration_hours=4
        )

        overlap_start = _dt(offset_days=base, offset_hours=2)
        overlap_end = _dt(offset_days=base, offset_hours=3)

        # Without exclusion: should see a conflict
        resp_conflict = _conflict_check(
            client,
            tech_user_id=_TEST_USER_ID,
            proposed_start=overlap_start,
            proposed_end=overlap_end,
        )
        assert resp_conflict.json()["is_feasible"] is False

        # With exclusion: the only job in this date window is excluded -> no conflict
        resp_excluded = _conflict_check(
            client,
            tech_user_id=_TEST_USER_ID,
            proposed_start=overlap_start,
            proposed_end=overlap_end,
            exclude_job_id=job_id,
        )
        body = resp_excluded.json()
        double_bookings = [
            c for c in body["conflicts"] if c["conflict_type"] == "double_booking"
        ]
        assert len(double_bookings) == 0


# ---------------------------------------------------------------------------
# Validation / edge cases
# ---------------------------------------------------------------------------


class TestConflictCheckValidation:
    def test_end_before_start_returns_400(self, client):
        resp = _conflict_check(
            client,
            tech_user_id=_TEST_USER_ID,
            proposed_start=_dt(offset_days=5),
            proposed_end=_dt(offset_days=1),
        )
        assert resp.status_code == 400
        assert "proposed_end" in resp.json()["detail"].lower()

    def test_equal_start_end_returns_400(self, client):
        ts = _dt(offset_days=5)
        resp = _conflict_check(
            client,
            tech_user_id=_TEST_USER_ID,
            proposed_start=ts,
            proposed_end=ts,
        )
        assert resp.status_code == 400

    def test_conflict_detail_includes_entity_id(self, client):
        """Each conflict entry must include a non-null conflicting_entity_id."""
        _create_pto(
            client,
            starts_at=_dt(offset_days=270),
            ends_at=_dt(offset_days=272),
        )
        resp = _conflict_check(
            client,
            tech_user_id=_TEST_USER_ID,
            proposed_start=_dt(offset_days=270, offset_hours=6),
            proposed_end=_dt(offset_days=270, offset_hours=10),
        )
        body = resp.json()
        assert body["is_feasible"] is False
        for conflict in body["conflicts"]:
            assert conflict.get("conflicting_entity_id") is not None
