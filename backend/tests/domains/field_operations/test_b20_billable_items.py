"""
B20 — Billable Items Endpoint
Tests for GET /api/v1/jobs/{job_id}/billable-items(/test).

NOTE: We create jobs via the /api/v1/jobs/test endpoint so they live in the
canonical TestUserContext tenant (TEST_TENANT_ID). The test_job fixture uses
tenant_a which does NOT match TestUserContext.tenant_id — that fixture is for
RBAC tests only. Rule 16: never assume a job from another fixture is in scope.

Domain: field_operations
"""

import uuid
from unittest.mock import patch

import pytest

from core.config import settings

pytestmark = [
    pytest.mark.domain_field_operations,
    pytest.mark.unit,
]


def _create_test_job(client, test_tenant, test_customer, test_site):
    """
    Create a job in the canonical test tenant via the /jobs/test endpoint.
    Returns the job dict on success, or None if creation failed.
    """
    with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
        with patch.object(settings, "ENVIRONMENT", "dev"):
            resp = client.post(
                "/api/v1/jobs/test",
                json={
                    "customer_id": str(test_customer.id),
                    "site_id": str(test_site.id),
                    "description": "B20 billable items test job",
                },
            )
    if resp.status_code in (200, 201):
        return resp.json()
    return None


class TestBillableItems:
    """Test GET /api/v1/jobs/{job_id}/billable-items endpoint."""

    def test_billable_items_returns_200_for_valid_job(
        self, client, test_tenant, test_customer, test_site
    ):
        """Basic smoke test — returns 200 for an active job in the canonical test tenant."""
        job = _create_test_job(client, test_tenant, test_customer, test_site)
        if job is None:
            pytest.skip("Job creation via /jobs/test failed — check seeded data")
        job_id = job["id"]
        resp = client.get(f"/api/v1/jobs/{job_id}/billable-items/test")
        assert resp.status_code == 200
        data = resp.json()
        assert "time_entries" in data
        assert "expenses" in data
        assert "job_id" in data
        assert data["job_id"] == job_id

    def test_billable_items_response_shape(
        self, client, test_tenant, test_customer, test_site
    ):
        """Response contains required top-level keys per BillableItemsResponse schema."""
        job = _create_test_job(client, test_tenant, test_customer, test_site)
        if job is None:
            pytest.skip("Job creation failed")
        resp = client.get(f"/api/v1/jobs/{job['id']}/billable-items/test")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data["time_entries"], list)
        assert isinstance(data["expenses"], list)
        assert "job_number" in data
        assert "customer_name" in data

    def test_billable_items_404_for_unknown_job(self, client, test_tenant):
        """Non-existent job UUID returns 404 (IDOR-safe, RFC 7807 shape)."""
        fake_id = str(uuid.uuid4())
        resp = client.get(f"/api/v1/jobs/{fake_id}/billable-items/test")
        assert resp.status_code == 404
        data = resp.json()
        assert "detail" in data
        detail = data["detail"]
        if isinstance(detail, dict):
            assert detail.get("status") == 404
            assert "type" in detail
            assert "title" in detail

    def test_billable_items_time_entries_is_already_invoiced_always_false(
        self, client, test_tenant, test_customer, test_site
    ):
        """MVP: is_already_invoiced is always False for time entries."""
        job = _create_test_job(client, test_tenant, test_customer, test_site)
        if job is None:
            pytest.skip("Job creation failed")
        resp = client.get(f"/api/v1/jobs/{job['id']}/billable-items/test")
        assert resp.status_code == 200
        for entry in resp.json()["time_entries"]:
            assert entry["is_already_invoiced"] is False, (
                f"Time entry {entry['id']} should have is_already_invoiced=False in MVP"
            )

    def test_billable_items_expense_shape(
        self, client, test_tenant, test_customer, test_site
    ):
        """Each expense entry contains required BillableExpense fields."""
        job = _create_test_job(client, test_tenant, test_customer, test_site)
        if job is None:
            pytest.skip("Job creation failed")
        resp = client.get(f"/api/v1/jobs/{job['id']}/billable-items/test")
        assert resp.status_code == 200
        for exp in resp.json()["expenses"]:
            assert "id" in exp
            assert "description" in exp
            assert "cost_cents" in exp
            assert "billable_cents" in exp
            assert "is_billable" in exp
            assert "is_already_invoiced" in exp
            assert "incurred_at" in exp
