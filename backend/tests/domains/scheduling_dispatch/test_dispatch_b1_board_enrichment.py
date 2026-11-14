"""
DISPATCH-B1 (Part A) — Dispatch Board Response Enrichment Tests

Covers the new fields added to DispatchBoardJobEntry:
  - version (optimistic lock)
  - primary_assignment_id + assignment_version (active primary assignment)
  - job_number (label field)
  - customer_name (batch-loaded from Customer.display_name)
  - site_address (batch-loaded via entity_address polymorphic join)
  - title (forward-compat null — populated by JOB-UI-B1 later)

Test 1: Assigned job entry carries all new fields with correct non-null values
Test 2: Unassigned entry carries labels but null assignment fields
Test 3: title is null (forward-compat)
Test 4: site_address is None when site has no EntityAddress row (bare test site fixture)
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest

pytestmark = [
    pytest.mark.domain_scheduling_dispatch,
    pytest.mark.unit,
]

SCHED_BASE = "/api/v1/scheduling"
JOBS_BASE = "/api/v1/jobs"
CUST_BASE = "/api/v1/customers"
SITES_BASE = "/api/v1/sites"

_TEST_USER_ID = "00000000-0000-0000-0000-000000000002"

_NOW = datetime.now(UTC)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _dt(offset_days: float = 0, offset_hours: float = 0) -> str:
    return (_NOW + timedelta(days=offset_days, hours=offset_hours)).isoformat()


def _unique_offset() -> float:
    """Return a far-future day offset unique to this call to avoid window collisions."""
    return 500.0 + float(uuid.uuid4().int % 500) * 0.1


def _create_customer(client, display_name: str | None = None) -> dict:
    name = display_name or f"DISP-B1 Customer {uuid.uuid4().hex[:8]}"
    resp = client.post(
        CUST_BASE + "/test", json={"display_name": name, "type": "person"}
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _create_site(client, customer_id: str) -> dict:
    resp = client.post(SITES_BASE + "/test", json={"customer_id": customer_id})
    assert resp.status_code == 201, resp.text
    return resp.json()


def _create_job(client, customer_id: str, site_id: str, offset_days: float) -> dict:
    start = _dt(offset_days=offset_days)
    end = _dt(offset_days=offset_days, offset_hours=4)
    resp = client.post(
        JOBS_BASE + "/test",
        json={
            "customer_id": customer_id,
            "site_id": site_id,
            "scheduled_start_at": start,
            "scheduled_end_at": end,
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _assign_primary(client, job_id: str) -> dict:
    resp = client.post(
        f"{SCHED_BASE}/jobs/{job_id}/assignments/test",
        json={"user_id": _TEST_USER_ID, "role": "primary", "ordinal": 1},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _get_board(client, offset_days: float) -> dict:
    resp = client.get(
        f"{SCHED_BASE}/dispatch-board/test",
        params={
            "start_date": _dt(offset_days=offset_days - 0.5),
            "end_date": _dt(offset_days=offset_days + 1),
        },
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def _find_entry_in_board(board: dict, job_id: str) -> dict | None:
    """Locate a job entry anywhere in the board (techs or unassigned) by job id."""
    for entry in board["unassigned"]:
        if entry["id"] == job_id:
            return entry
    for group in board["techs"]:
        for entry in group["jobs"]:
            if entry["id"] == job_id:
                return entry
    return None


# ---------------------------------------------------------------------------
# Test 1: Assigned job entry carries all DISPATCH-B1 fields
# ---------------------------------------------------------------------------


class TestAssignedJobEntryFields:
    def test_assigned_job_carries_version_assignment_and_labels(self, client):
        """An assigned job must expose version, primary_assignment_id, assignment_version,
        job_number, and customer_name — all non-null."""
        offset = _unique_offset()
        customer_name = f"Enrich Co {uuid.uuid4().hex[:6]}"
        customer = _create_customer(client, customer_name)
        site = _create_site(client, customer["id"])
        job = _create_job(client, customer["id"], site["id"], offset)
        assignment = _assign_primary(client, job["id"])

        board = _get_board(client, offset)
        entry = _find_entry_in_board(board, job["id"])

        assert entry is not None, f"Job {job['id']} not found in board"

        # version must be a non-negative integer
        assert isinstance(entry["version"], int)
        assert entry["version"] >= 0

        # primary assignment fields must be present and non-null
        assert entry["primary_assignment_id"] is not None
        assert entry["primary_assignment_id"] == assignment["id"]
        assert isinstance(entry["assignment_version"], int)
        assert entry["assignment_version"] >= 0

        # label fields
        assert isinstance(entry["job_number"], str)
        assert entry["job_number"] != ""

        # customer_name must match the seeded customer's display_name
        assert entry["customer_name"] == customer_name


# ---------------------------------------------------------------------------
# Test 2: Unassigned job carries labels but null assignment fields
# ---------------------------------------------------------------------------


class TestUnassignedJobEntryFields:
    def test_unassigned_entry_has_labels_but_null_assignment_fields(self, client):
        """An unassigned job must carry version, job_number, customer_name but have
        primary_assignment_id=None and assignment_version=None."""
        offset = _unique_offset()
        customer_name = f"Unassigned Co {uuid.uuid4().hex[:6]}"
        customer = _create_customer(client, customer_name)
        site = _create_site(client, customer["id"])
        job = _create_job(client, customer["id"], site["id"], offset)
        # Deliberately no assignment call

        board = _get_board(client, offset)

        # Verify it's in unassigned, not in any tech group
        unassigned_ids = [j["id"] for j in board["unassigned"]]
        assert job["id"] in unassigned_ids, "Job should be in unassigned bucket"

        tech_job_ids = [j["id"] for g in board["techs"] for j in g["jobs"]]
        assert job["id"] not in tech_job_ids, "Job should NOT appear in any tech group"

        entry = next(j for j in board["unassigned"] if j["id"] == job["id"])

        # Labels must be present
        assert isinstance(entry["version"], int)
        assert entry["version"] >= 0
        assert isinstance(entry["job_number"], str)
        assert entry["job_number"] != ""
        assert entry["customer_name"] == customer_name

        # Assignment fields must be null
        assert entry["primary_assignment_id"] is None
        assert entry["assignment_version"] is None


# ---------------------------------------------------------------------------
# Test 3: title is null (FORWARD-COMPAT — JOB-UI-B1 populates later)
# ---------------------------------------------------------------------------


class TestTitleForwardCompat:
    def test_title_is_null_before_job_ui_b1(self, client):
        """title must be None — JOB-UI-B1 will populate it later."""
        offset = _unique_offset()
        customer = _create_customer(client)
        site = _create_site(client, customer["id"])
        job = _create_job(client, customer["id"], site["id"], offset)

        board = _get_board(client, offset)
        entry = _find_entry_in_board(board, job["id"])

        assert entry is not None, f"Job {job['id']} not found in board"
        assert entry["title"] is None, "title should be None (JOB-UI-B1 deferred)"


# ---------------------------------------------------------------------------
# Test 4: site_address is None when site has no EntityAddress row
# ---------------------------------------------------------------------------


class TestSiteAddressEnrichment:
    def test_site_address_is_none_for_bare_test_site(self, client):
        """A site created via /sites/test (no address row) must have site_address=None."""
        offset = _unique_offset()
        customer = _create_customer(client)
        site = _create_site(client, customer["id"])
        job = _create_job(client, customer["id"], site["id"], offset)

        board = _get_board(client, offset)
        entry = _find_entry_in_board(board, job["id"])

        assert entry is not None, f"Job {job['id']} not found in board"
        # The bare /sites/test endpoint creates no entity_address row — expect None
        assert entry["site_address"] is None, (
            "site_address should be None for a site with no entity_address row"
        )
