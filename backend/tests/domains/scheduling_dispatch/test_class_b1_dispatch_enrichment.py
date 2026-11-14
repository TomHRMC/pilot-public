"""
Tests for: CLASS-B1 — Dispatch board DispatchBoardJobEntry enrichment
  (priority, customer_type, site_type, job_type_code, job_type_label)
Domain: scheduling_dispatch (PRD §3.14)
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlmodel import select

from app.models.fulfillment import Job, JobStatus, JobType

pytestmark = [
    pytest.mark.domain_scheduling_dispatch,
    pytest.mark.unit,
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_customer(client, customer_type="person", display_name=None):
    payload = {
        "display_name": display_name or f"Cust-{uuid.uuid4().hex[:6]}",
        "type": customer_type,
    }
    r = client.post("/api/v1/customers/test", json=payload)
    assert r.status_code == 201, r.text
    return r.json()


def _create_site(client, customer_id, **kwargs):
    r = client.post(
        "/api/v1/sites/test", json={"customer_id": str(customer_id), **kwargs}
    )
    assert r.status_code == 201, r.text
    return r.json()


def _create_job_direct(
    db_session,
    tenant_id,
    customer_id,
    site_id,
    status_code="scheduled",
    priority="standard",
    job_type_id=None,
    start_at=None,
):
    """Create a Job row directly in db_session with a scheduled time."""
    job_status = db_session.exec(
        select(JobStatus)
        .where(JobStatus.code == status_code)
        .where(JobStatus.tenant_id == None)
    ).first()
    if job_status is None:
        # Fall back to any status
        job_status = db_session.exec(select(JobStatus)).first()

    if start_at is None:
        start_at = datetime.now(UTC) + timedelta(hours=1)

    job = Job(
        tenant_id=tenant_id,
        customer_id=customer_id,
        site_id=site_id,
        status_id=job_status.id,
        job_number=f"JOB-{uuid.uuid4().hex[:6].upper()}",
        priority=priority,
        job_type_id=job_type_id,
        scheduled_start_at=start_at,
        scheduled_end_at=start_at + timedelta(hours=2),
    )
    from datetime import UTC, datetime

    job.created_at = datetime.now(UTC)
    job.updated_at = datetime.now(UTC)
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    return job


# ---------------------------------------------------------------------------
# Dispatch enrichment tests
# ---------------------------------------------------------------------------


class TestDispatchBoardEnrichment:
    """CLASS-B1 — dispatch board entries carry the 5 new enrichment fields."""

    def test_dispatch_entry_carries_priority(self, client, test_tenant, db_session):
        """Dispatch board job entry returns the job's priority field."""
        cust = _create_customer(client, customer_type="person")
        site = _create_site(client, cust["id"])

        now = datetime.now(UTC)
        job = _create_job_direct(
            db_session,
            test_tenant.id,
            uuid.UUID(cust["id"]),
            uuid.UUID(site["id"]),
            priority="urgent",
            start_at=now + timedelta(hours=1),
        )

        resp = client.get(
            "/api/v1/scheduling/dispatch-board/test",
            params={
                "start_date": now.isoformat(),
                "end_date": (now + timedelta(days=1)).isoformat(),
            },
        )
        assert resp.status_code == 200
        board = resp.json()

        # Find our job in unassigned (no tech assigned)
        all_entries = board.get("unassigned", [])
        our_entry = next((e for e in all_entries if e["id"] == str(job.id)), None)
        assert our_entry is not None, f"Job {job.id} not found in unassigned"
        assert our_entry["priority"] == "urgent"

    def test_dispatch_entry_carries_customer_type(
        self, client, test_tenant, db_session
    ):
        """Dispatch board entry returns customer_type (person/company)."""
        cust = _create_customer(client, customer_type="company")
        site = _create_site(client, cust["id"], site_type="commercial")

        now = datetime.now(UTC)
        job = _create_job_direct(
            db_session,
            test_tenant.id,
            uuid.UUID(cust["id"]),
            uuid.UUID(site["id"]),
            start_at=now + timedelta(hours=1),
        )

        resp = client.get(
            "/api/v1/scheduling/dispatch-board/test",
            params={
                "start_date": now.isoformat(),
                "end_date": (now + timedelta(days=1)).isoformat(),
            },
        )
        assert resp.status_code == 200
        board = resp.json()
        all_entries = board.get("unassigned", [])
        our_entry = next((e for e in all_entries if e["id"] == str(job.id)), None)
        assert our_entry is not None
        assert our_entry["customer_type"] == "company"
        assert our_entry["site_type"] == "commercial"

    def test_dispatch_entry_carries_job_type(self, client, test_tenant, db_session):
        """Dispatch board entry returns job_type_code and job_type_label."""
        cust = _create_customer(client)
        site = _create_site(client, cust["id"])

        panel_type = db_session.exec(
            select(JobType)
            .where(JobType.code == "panel_upgrade")
            .where(JobType.tenant_id == None)
        ).first()
        assert panel_type is not None

        now = datetime.now(UTC)
        job = _create_job_direct(
            db_session,
            test_tenant.id,
            uuid.UUID(cust["id"]),
            uuid.UUID(site["id"]),
            job_type_id=panel_type.id,
            start_at=now + timedelta(hours=1),
        )

        resp = client.get(
            "/api/v1/scheduling/dispatch-board/test",
            params={
                "start_date": now.isoformat(),
                "end_date": (now + timedelta(days=1)).isoformat(),
            },
        )
        assert resp.status_code == 200
        board = resp.json()
        all_entries = board.get("unassigned", [])
        our_entry = next((e for e in all_entries if e["id"] == str(job.id)), None)
        assert our_entry is not None
        assert our_entry["job_type_code"] == "panel_upgrade"
        assert our_entry["job_type_label"] == "Panel Upgrade"

    def test_dispatch_entry_null_job_type_is_safe(
        self, client, test_tenant, db_session
    ):
        """Dispatch board entry with no job_type_id has null code/label."""
        cust = _create_customer(client)
        site = _create_site(client, cust["id"])

        now = datetime.now(UTC)
        job = _create_job_direct(
            db_session,
            test_tenant.id,
            uuid.UUID(cust["id"]),
            uuid.UUID(site["id"]),
            job_type_id=None,
            start_at=now + timedelta(hours=1),
        )

        resp = client.get(
            "/api/v1/scheduling/dispatch-board/test",
            params={
                "start_date": now.isoformat(),
                "end_date": (now + timedelta(days=1)).isoformat(),
            },
        )
        assert resp.status_code == 200
        board = resp.json()
        all_entries = board.get("unassigned", [])
        our_entry = next((e for e in all_entries if e["id"] == str(job.id)), None)
        assert our_entry is not None
        assert our_entry["job_type_code"] is None
        assert our_entry["job_type_label"] is None
