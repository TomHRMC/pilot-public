"""
DISPATCH-B1.25 (Part A) — Multi-Tech Commitment Visibility Tests

Covers the new fields added to the dispatch board response:
  - DispatchBoardJobEntry.assignment_role
  - DispatchBoardTechGroup.additional_job_commitments

Test 1: Helper commitment appears in correct tech group's additional_job_commitments
Test 2: No duplication in jobs[] — job appears exactly once across all tech groups
Test 3: Commitment-only tech appears as a tech group (empty jobs[], populated commitments)
Test 4: Primary fields intact; commitment entry has no primary_assignment_id
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

# Seeded user IDs (from seed_test_tenant.py — permanently reserved)
_ALICE_USER_ID = "00000000-0000-0000-0000-000000000002"  # owner / dev@pilot.local
_BOB_USER_ID = "00000000-0000-0000-0000-000000000003"  # technician / tech@pilot.local

_NOW = datetime.now(UTC)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _dt(offset_days: float = 0, offset_hours: float = 0) -> str:
    return (_NOW + timedelta(days=offset_days, hours=offset_hours)).isoformat()


def _unique_offset() -> float:
    """Far-future day offset unique per call to avoid window collisions."""
    return 600.0 + float(uuid.uuid4().int % 500) * 0.1


def _create_customer(client, display_name: str | None = None) -> dict:
    name = display_name or f"B1.25 Customer {uuid.uuid4().hex[:8]}"
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


def _assign(client, job_id: str, user_id: str, role: str) -> dict:
    resp = client.post(
        f"{SCHED_BASE}/jobs/{job_id}/assignments/test",
        json={"user_id": user_id, "role": role, "ordinal": 1},
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


def _find_tech_group(board: dict, user_id: str) -> dict | None:
    """Return the tech group for a given user_id, or None."""
    for group in board["techs"]:
        if group["tech_id"] == user_id:
            return group
    return None


# ---------------------------------------------------------------------------
# Test 1: Helper commitment appears in correct tech group
# ---------------------------------------------------------------------------


class TestHelperCommitmentAppears:
    def test_helper_commitment_in_additional_job_commitments(self, client):
        """Job with primary=Alice + helper=Bob:
        - job is in Alice's jobs[] with assignment_role='primary'
        - job is in Bob's additional_job_commitments[] with assignment_role='helper'
        """
        offset = _unique_offset()
        customer = _create_customer(client)
        site = _create_site(client, customer["id"])
        job = _create_job(client, customer["id"], site["id"], offset)

        # Assign Alice as primary, Bob as helper
        _assign(client, job["id"], _ALICE_USER_ID, "primary")
        _assign(client, job["id"], _BOB_USER_ID, "helper")

        board = _get_board(client, offset)

        # Alice's tech group: job in jobs[] with role='primary'
        alice_group = _find_tech_group(board, _ALICE_USER_ID)
        assert alice_group is not None, "Alice should have a tech group"
        alice_job_ids = [j["id"] for j in alice_group["jobs"]]
        assert job["id"] in alice_job_ids, "Job should be in Alice's jobs[]"

        alice_entry = next(j for j in alice_group["jobs"] if j["id"] == job["id"])
        assert alice_entry["assignment_role"] == "primary"

        # Bob's tech group: job in additional_job_commitments[] with role='helper'
        bob_group = _find_tech_group(board, _BOB_USER_ID)
        assert bob_group is not None, (
            "Bob should have a tech group (commitment-only OK)"
        )

        commitment_ids = [j["id"] for j in bob_group["additional_job_commitments"]]
        assert job["id"] in commitment_ids, (
            "Job should be in Bob's additional_job_commitments[]"
        )

        bob_commitment = next(
            j for j in bob_group["additional_job_commitments"] if j["id"] == job["id"]
        )
        assert bob_commitment["assignment_role"] == "helper"


# ---------------------------------------------------------------------------
# Test 2: No duplication in jobs[]
# ---------------------------------------------------------------------------


class TestNoDuplicationInJobsList:
    def test_job_appears_exactly_once_in_all_tech_jobs_lists(self, client):
        """The same job (with primary=Alice, helper=Bob) must appear exactly ONCE
        across all techs[].jobs — only in Alice's jobs[], never in Bob's jobs[].
        """
        offset = _unique_offset()
        customer = _create_customer(client)
        site = _create_site(client, customer["id"])
        job = _create_job(client, customer["id"], site["id"], offset)

        _assign(client, job["id"], _ALICE_USER_ID, "primary")
        _assign(client, job["id"], _BOB_USER_ID, "helper")

        board = _get_board(client, offset)

        # Flatten all jobs[] across all tech groups — count occurrences of this job_id
        all_primary_job_ids = [j["id"] for g in board["techs"] for j in g["jobs"]]
        occurrences = all_primary_job_ids.count(job["id"])
        assert occurrences == 1, (
            f"Job {job['id']} appears {occurrences} times in techs[].jobs — must be exactly 1"
        )

        # Verify Bob's jobs[] does NOT contain the job
        bob_group = _find_tech_group(board, _BOB_USER_ID)
        if bob_group is not None:
            bob_jobs_ids = [j["id"] for j in bob_group["jobs"]]
            assert job["id"] not in bob_jobs_ids, "Job must NOT appear in Bob's jobs[]"


# ---------------------------------------------------------------------------
# Test 3: Commitment-only tech appears as a tech group
# ---------------------------------------------------------------------------


class TestCommitmentOnlyTechAppears:
    def test_commitment_only_tech_has_empty_jobs_and_populated_commitments(
        self, client
    ):
        """A tech with only a helper assignment (no primary jobs in the window)
        must appear as a tech group with jobs=[] and a populated
        additional_job_commitments[].
        """
        offset = _unique_offset()
        customer = _create_customer(client)
        site = _create_site(client, customer["id"])
        job = _create_job(client, customer["id"], site["id"], offset)

        # Alice is primary (so there IS a primary owner for the job)
        _assign(client, job["id"], _ALICE_USER_ID, "primary")
        # Bob is ONLY a helper — he has no primary jobs in this window
        _assign(client, job["id"], _BOB_USER_ID, "helper")

        board = _get_board(client, offset)

        bob_group = _find_tech_group(board, _BOB_USER_ID)
        assert bob_group is not None, (
            "Bob (helper-only) must appear as a tech group so his commitment is visible"
        )
        assert bob_group["jobs"] == [], (
            "Bob has no primary jobs — his jobs[] must be empty"
        )
        assert len(bob_group["additional_job_commitments"]) >= 1, (
            "Bob must have at least one entry in additional_job_commitments[]"
        )
        commitment_ids = [j["id"] for j in bob_group["additional_job_commitments"]]
        assert job["id"] in commitment_ids


# ---------------------------------------------------------------------------
# Test 4: Primary fields intact; commitment entry has no primary_assignment_id
# ---------------------------------------------------------------------------


class TestPrimaryFieldsIntact:
    def test_primary_entry_carries_assignment_fields_commitment_entry_does_not(
        self, client
    ):
        """Primary entry (Alice) carries primary_assignment_id + assignment_version.
        Commitment entry (Bob) has assignment_role='helper' and primary_assignment_id is None.
        """
        offset = _unique_offset()
        customer = _create_customer(client)
        site = _create_site(client, customer["id"])
        job = _create_job(client, customer["id"], site["id"], offset)

        alice_assignment = _assign(client, job["id"], _ALICE_USER_ID, "primary")
        _assign(client, job["id"], _BOB_USER_ID, "helper")

        board = _get_board(client, offset)

        # Alice's primary entry: must carry primary_assignment_id + assignment_version
        alice_group = _find_tech_group(board, _ALICE_USER_ID)
        assert alice_group is not None
        alice_entry = next(j for j in alice_group["jobs"] if j["id"] == job["id"])
        assert alice_entry["assignment_role"] == "primary"
        assert alice_entry["primary_assignment_id"] == alice_assignment["id"], (
            "primary_assignment_id must match the actual primary assignment id"
        )
        assert isinstance(alice_entry["assignment_version"], int)

        # Bob's commitment entry: role='helper', primary_assignment_id is None
        bob_group = _find_tech_group(board, _BOB_USER_ID)
        assert bob_group is not None
        bob_commitment = next(
            j for j in bob_group["additional_job_commitments"] if j["id"] == job["id"]
        )
        assert bob_commitment["assignment_role"] == "helper"
        assert bob_commitment["primary_assignment_id"] is None, (
            "Commitment entry must not carry primary_assignment_id"
        )
