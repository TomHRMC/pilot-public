"""
DISPATCH-B1.5 (Part A) — site_name on DispatchBoardJobEntry

Covers the new field added by DISPATCH-B1.5:
  - site_name (batch-loaded from site.name, no new DB query)

Test 1: site_name is populated when the site has a name
Test 2: site_name is None when the site has no name (null-safe)
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
    return 700.0 + float(uuid.uuid4().int % 500) * 0.1


def _create_customer(client) -> dict:
    name = f"B1.5 Customer {uuid.uuid4().hex[:8]}"
    resp = client.post(
        CUST_BASE + "/test", json={"display_name": name, "type": "person"}
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _create_site(client, customer_id: str, name: str | None = None) -> dict:
    payload: dict = {"customer_id": customer_id}
    if name is not None:
        payload["name"] = name
    resp = client.post(SITES_BASE + "/test", json=payload)
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
# Test 1: site_name is populated when site has a known name
# ---------------------------------------------------------------------------


class TestSiteNamePopulated:
    def test_site_name_matches_site_name_field(self, client):
        """Board entry must expose site_name equal to the site's name when set."""
        offset = _unique_offset()
        known_site_name = f"North Warehouse {uuid.uuid4().hex[:6]}"

        customer = _create_customer(client)
        site = _create_site(client, customer["id"], name=known_site_name)
        job = _create_job(client, customer["id"], site["id"], offset)

        board = _get_board(client, offset)
        entry = _find_entry_in_board(board, job["id"])

        assert entry is not None, f"Job {job['id']} not found in board"
        assert entry["site_name"] == known_site_name, (
            f"Expected site_name={known_site_name!r}, got {entry['site_name']!r}"
        )


# ---------------------------------------------------------------------------
# Test 2: site_name is None when site has no name (null-safe)
# ---------------------------------------------------------------------------


class TestSiteNameNullSafe:
    def test_site_name_is_none_when_site_has_no_name(self, client):
        """Board entry must have site_name=None when site.name is NULL (no error)."""
        offset = _unique_offset()

        customer = _create_customer(client)
        # /sites/test with no name → site.name stays NULL
        site = _create_site(client, customer["id"])
        job = _create_job(client, customer["id"], site["id"], offset)

        board = _get_board(client, offset)
        entry = _find_entry_in_board(board, job["id"])

        assert entry is not None, f"Job {job['id']} not found in board"
        assert entry["site_name"] is None, (
            f"Expected site_name=None for a site with no name, got {entry['site_name']!r}"
        )
