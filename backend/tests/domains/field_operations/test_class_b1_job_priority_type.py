"""
Tests for: CLASS-B1 — job.priority, job.job_type_id, GET /job-types
Domain: field_operations (PRD §3.4)
"""

import uuid
from datetime import UTC, datetime

import pytest
from sqlmodel import select

from app.models.fulfillment import JobType

pytestmark = [
    pytest.mark.domain_field_operations,
    pytest.mark.unit,
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_customer(client, customer_type="person"):
    payload = {"display_name": f"Cust-{uuid.uuid4().hex[:6]}", "type": customer_type}
    r = client.post("/api/v1/customers/test", json=payload)
    assert r.status_code == 201, r.text
    return r.json()


def _create_site(client, customer_id, **kwargs):
    r = client.post(
        "/api/v1/sites/test", json={"customer_id": str(customer_id), **kwargs}
    )
    assert r.status_code == 201, r.text
    return r.json()


def _create_job(client, customer_id, site_id, **kwargs):
    resp = client.post(
        "/api/v1/jobs/test",
        json={"customer_id": str(customer_id), "site_id": str(site_id), **kwargs},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


# ---------------------------------------------------------------------------
# GET /api/v1/job-types/test
# ---------------------------------------------------------------------------


class TestJobTypeList:
    """CLASS-B1 — GET /api/v1/job-types returns platform defaults."""

    def test_returns_platform_defaults(self, client, test_tenant):
        """Platform defaults are visible without any tenant overrides."""
        resp = client.get("/api/v1/job-types/test")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 11, "Expected at least 11 platform-default rows"
        codes = {row["code"] for row in data}
        assert "service_call" in codes
        assert "panel_upgrade" in codes
        assert "other" in codes

    def test_tenant_override_shadows_platform(self, client, test_tenant, db_session):
        """A tenant row with the same code as a platform default wins, is_tenant_override=True."""
        platform_row = db_session.exec(
            select(JobType)
            .where(JobType.tenant_id == None)
            .where(JobType.code == "service_call")
        ).first()
        assert platform_row is not None, "service_call platform default must exist"

        override = JobType(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            code="service_call",
            label="Tenant Service Call Override",
            sort_order=10,
            is_active=True,
        )
        override.created_at = datetime.now(UTC)
        override.updated_at = datetime.now(UTC)
        db_session.add(override)
        db_session.commit()

        resp = client.get("/api/v1/job-types/test")
        assert resp.status_code == 200
        data = resp.json()

        sc_rows = [r for r in data if r["code"] == "service_call"]
        assert len(sc_rows) == 1
        assert sc_rows[0]["label"] == "Tenant Service Call Override"
        assert sc_rows[0]["is_tenant_override"] is True

    def test_inactive_rows_excluded(self, client, test_tenant, db_session):
        """Inactive job_type rows are not returned."""
        inactive = JobType(
            id=uuid.uuid4(),
            tenant_id=None,
            code=f"test_inactive_{uuid.uuid4().hex[:6]}",
            label="Inactive Test Type",
            sort_order=999,
            is_active=False,
        )
        inactive.created_at = datetime.now(UTC)
        inactive.updated_at = datetime.now(UTC)
        db_session.add(inactive)
        db_session.commit()

        resp = client.get("/api/v1/job-types/test")
        assert resp.status_code == 200
        codes = {r["code"] for r in resp.json()}
        assert inactive.code not in codes


# ---------------------------------------------------------------------------
# job.priority
# ---------------------------------------------------------------------------


class TestJobPriority:
    """CLASS-B1 — job.priority create/validate/default."""

    def test_create_with_urgent_persists(self, client, test_tenant):
        """Creating a job with priority='urgent' persists correctly."""
        cust = _create_customer(client)
        site = _create_site(client, cust["id"])
        job = _create_job(client, cust["id"], site["id"], priority="urgent")
        # Create returns the model; GET returns enriched response
        get_resp = client.get(f"/api/v1/jobs/{job['id']}/test")
        assert get_resp.status_code == 200
        assert get_resp.json()["priority"] == "urgent"

    def test_invalid_priority_returns_422_rfc7807(self, client, test_tenant):
        """Invalid priority value returns 422 with RFC 7807 format."""
        cust = _create_customer(client)
        site = _create_site(client, cust["id"])
        resp = client.post(
            "/api/v1/jobs/test",
            json={
                "customer_id": str(cust["id"]),
                "site_id": str(site["id"]),
                "priority": "rush",
            },
        )
        assert resp.status_code == 422
        # FastAPI wraps HTTPException detail in {"detail": {...}}
        body = resp.json()["detail"]
        assert "type" in body
        assert "title" in body
        assert "status" in body
        assert body["status"] == 422

    def test_default_standard_when_omitted(self, client, test_tenant):
        """Omitting priority defaults to 'standard'."""
        cust = _create_customer(client)
        site = _create_site(client, cust["id"])
        job = _create_job(client, cust["id"], site["id"])
        assert job["priority"] == "standard"

    def test_emergency_priority_valid(self, client, test_tenant):
        """Creating a job with priority='emergency' works."""
        cust = _create_customer(client)
        site = _create_site(client, cust["id"])
        job = _create_job(client, cust["id"], site["id"], priority="emergency")
        assert job["priority"] == "emergency"


# ---------------------------------------------------------------------------
# job.job_type_id
# ---------------------------------------------------------------------------


class TestJobTypeId:
    """CLASS-B1 — job.job_type_id link and enrichment."""

    def test_create_with_valid_job_type_id(self, client, test_tenant, db_session):
        """Creating a job with a valid job_type_id — GET enriches code/label."""
        panel_type = db_session.exec(
            select(JobType)
            .where(JobType.code == "panel_upgrade")
            .where(JobType.tenant_id == None)
        ).first()
        assert panel_type is not None

        cust = _create_customer(client)
        site = _create_site(client, cust["id"])
        job = _create_job(
            client, cust["id"], site["id"], job_type_id=str(panel_type.id)
        )
        assert job["job_type_id"] == str(panel_type.id)

        # GET returns enriched response with code/label
        get_resp = client.get(f"/api/v1/jobs/{job['id']}/test")
        assert get_resp.status_code == 200
        data = get_resp.json()
        assert data["job_type_id"] == str(panel_type.id)
        assert data["job_type_code"] == "panel_upgrade"
        assert data["job_type_label"] == "Panel Upgrade"

    def test_null_job_type_returns_null_labels(self, client, test_tenant):
        """Job created without job_type_id has null code/label in GET response."""
        cust = _create_customer(client)
        site = _create_site(client, cust["id"])
        job = _create_job(client, cust["id"], site["id"])

        get_resp = client.get(f"/api/v1/jobs/{job['id']}/test")
        assert get_resp.status_code == 200
        data = get_resp.json()
        assert data["job_type_id"] is None
        assert data["job_type_code"] is None
        assert data["job_type_label"] is None
