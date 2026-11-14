"""
B19: Tests for job_number field on Job — sequential format JOB-000001.

Covers:
- job_number auto-assigned on create
- job_number format (JOB-XXXXXX)
- JobResponse includes status_code, site_name, customer_name
- job_number unique per tenant
"""

import re

import pytest

pytestmark = [
    pytest.mark.domain_field_operations,
    pytest.mark.unit,
]


def _create_customer(client, display_name: str = "B19 Job Customer"):
    resp = client.post(
        "/api/v1/customers/test",
        json={"display_name": display_name, "type": "person"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _create_site(client, customer_id: str):
    resp = client.post("/api/v1/sites/test", json={"customer_id": customer_id})
    assert resp.status_code == 201, resp.text
    return resp.json()


def _create_job(client, customer_id: str, site_id: str):
    resp = client.post(
        "/api/v1/jobs/test",
        json={"customer_id": customer_id, "site_id": site_id},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


class TestJobNumberAssignment:
    def test_create_job_assigns_job_number(self, client):
        """POST /api/v1/jobs/test → response includes job_number starting with JOB-"""
        cust = _create_customer(client)
        site = _create_site(client, cust["id"])
        data = _create_job(client, cust["id"], site["id"])
        assert "job_number" in data
        assert data["job_number"].startswith("JOB-"), (
            f"Expected JOB- prefix, got: {data['job_number']}"
        )

    def test_job_number_format(self, client):
        """job_number matches pattern JOB-XXXXXX"""
        cust = _create_customer(client)
        site = _create_site(client, cust["id"])
        data = _create_job(client, cust["id"], site["id"])
        job_number = data["job_number"]
        assert re.match(r"^JOB-[A-Za-z0-9]+$", job_number), (
            f"job_number '{job_number}' does not match expected pattern JOB-XXXXXX"
        )

    def test_job_number_unique_per_tenant(self, client):
        """Create 2 jobs for same tenant → different job_number values"""
        cust = _create_customer(client)
        site = _create_site(client, cust["id"])
        job1 = _create_job(client, cust["id"], site["id"])
        job2 = _create_job(client, cust["id"], site["id"])
        assert job1["job_number"] != job2["job_number"], (
            "Two jobs created for same tenant must have different job_number values"
        )


class TestJobDetailEnrichedFields:
    def test_job_detail_includes_status_code(self, client):
        """GET /api/v1/jobs/{id}/test → status_code is a non-None string"""
        cust = _create_customer(client)
        site = _create_site(client, cust["id"])
        created = _create_job(client, cust["id"], site["id"])
        job_id = created["id"]

        resp = client.get(f"/api/v1/jobs/{job_id}/test")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "status_code" in data
        assert data["status_code"] is not None, (
            "status_code should be populated from job_status JOIN"
        )
        assert isinstance(data["status_code"], str)
        known_codes = {"draft", "scheduled", "in_progress", "completed", "cancelled"}
        assert data["status_code"] in known_codes, (
            f"Unexpected status_code: {data['status_code']}"
        )

    def test_job_detail_includes_site_name(self, client):
        """GET /api/v1/jobs/{id}/test → site_name field is present in response (from site JOIN).
        The value may be None if the test site has no name; the important thing is the key exists.
        """
        cust = _create_customer(client)
        site = _create_site(client, cust["id"])
        created = _create_job(client, cust["id"], site["id"])
        job_id = created["id"]

        resp = client.get(f"/api/v1/jobs/{job_id}/test")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        # The site_name key MUST exist in the response (confirms JOIN is in place)
        assert "site_name" in data, (
            "site_name field missing from JobResponse — JOIN not implemented"
        )
        # Value is str or None depending on whether site.name is set
        assert data["site_name"] is None or isinstance(data["site_name"], str)

    def test_job_detail_includes_customer_name(self, client):
        """GET /api/v1/jobs/{id}/test → customer_name is populated"""
        cust = _create_customer(client, display_name="Acme Electric LLC")
        site = _create_site(client, cust["id"])
        created = _create_job(client, cust["id"], site["id"])
        job_id = created["id"]

        resp = client.get(f"/api/v1/jobs/{job_id}/test")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "customer_name" in data
        assert data["customer_name"] is not None, (
            "customer_name should be populated from customer JOIN"
        )
        assert isinstance(data["customer_name"], str)

    def test_job_detail_includes_job_number(self, client):
        """GET /api/v1/jobs/{id}/test → job_number matches the created value"""
        cust = _create_customer(client)
        site = _create_site(client, cust["id"])
        created = _create_job(client, cust["id"], site["id"])
        job_id = created["id"]
        expected_job_number = created["job_number"]

        resp = client.get(f"/api/v1/jobs/{job_id}/test")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["job_number"] == expected_job_number
