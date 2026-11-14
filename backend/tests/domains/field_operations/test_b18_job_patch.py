"""
B18 — PATCH /api/v1/jobs/{job_id} endpoint tests.

Tests the _update_job_impl() shared logic via the /test (unauthenticated) endpoint.
All assertions scoped by inserted ID — never count all rows.
"""

import pytest

pytestmark = [
    pytest.mark.domain_field_operations,
    pytest.mark.unit,
]


def test_patch_job_schedule_returns_200(client, test_tenant, test_customer, test_site):
    """Happy path: PATCH with new scheduled_start_at returns 200 with updated field."""
    # Create a job first
    resp = client.post(
        "/api/v1/jobs/test",
        json={
            "customer_id": str(test_customer.id),
            "site_id": str(test_site.id),
        },
    )
    assert resp.status_code == 201
    job_id = resp.json()["id"]

    # PATCH it
    patch_resp = client.patch(
        f"/api/v1/jobs/{job_id}/test",
        json={
            "scheduled_start_at": "2026-09-01T09:00:00Z",
            "scheduled_end_at": "2026-09-01T17:00:00Z",
        },
    )
    assert patch_resp.status_code == 200
    data = patch_resp.json()
    assert data["id"] == job_id
    assert "2026-09-01" in data["scheduled_start_at"]


def test_patch_job_estimated_duration_returns_200(
    client, test_tenant, test_customer, test_site
):
    """Happy path: PATCH with estimated_duration_minutes returns 200 with updated field."""
    resp = client.post(
        "/api/v1/jobs/test",
        json={
            "customer_id": str(test_customer.id),
            "site_id": str(test_site.id),
        },
    )
    assert resp.status_code == 201
    job_id = resp.json()["id"]

    patch_resp = client.patch(
        f"/api/v1/jobs/{job_id}/test",
        json={"estimated_duration_minutes": 120},
    )
    assert patch_resp.status_code == 200
    data = patch_resp.json()
    assert data["id"] == job_id
    assert data["estimated_duration_minutes"] == 120


def test_patch_job_empty_body_returns_200_unchanged(
    client, test_tenant, test_customer, test_site
):
    """PATCH with empty body {} returns 200 with unchanged job."""
    resp = client.post(
        "/api/v1/jobs/test",
        json={
            "customer_id": str(test_customer.id),
            "site_id": str(test_site.id),
        },
    )
    assert resp.status_code == 201
    job_id = resp.json()["id"]

    patch_resp = client.patch(f"/api/v1/jobs/{job_id}/test", json={})
    assert patch_resp.status_code == 200
    assert patch_resp.json()["id"] == job_id


def test_patch_job_nonexistent_returns_404(client, test_tenant):
    """PATCH job with job_id not in tenant returns 404."""
    fake_id = "00000000-0000-0000-0000-000000000099"
    resp = client.patch(
        f"/api/v1/jobs/{fake_id}/test",
        json={"estimated_duration_minutes": 120},
    )
    assert resp.status_code == 404
    detail = resp.json()["detail"]
    assert detail["status"] == 404
    assert "Job" in detail["title"]


def test_patch_job_invalid_customer_returns_404(
    client, test_tenant, test_customer, test_site
):
    """PATCH job with customer_id not in tenant returns 404."""
    resp = client.post(
        "/api/v1/jobs/test",
        json={
            "customer_id": str(test_customer.id),
            "site_id": str(test_site.id),
        },
    )
    assert resp.status_code == 201
    job_id = resp.json()["id"]

    fake_customer_id = "00000000-0000-0000-0000-000000000099"
    patch_resp = client.patch(
        f"/api/v1/jobs/{job_id}/test",
        json={"customer_id": fake_customer_id},
    )
    assert patch_resp.status_code == 404
    detail = patch_resp.json()["detail"]
    assert detail["status"] == 404
    assert "Customer" in detail["title"]


def test_patch_job_site_wrong_customer_returns_400(
    client, test_tenant, test_customer, test_site
):
    """PATCH job with site belonging to a different customer returns 400.

    Creates a second customer with their own site and tries to assign that site
    to a job belonging to the original customer — expect 400.
    """
    # Create second customer via test endpoint
    second_customer_resp = client.post(
        "/api/v1/customers/test",
        json={"display_name": "B18 Second Customer"},
    )
    assert second_customer_resp.status_code == 201
    second_customer_id = second_customer_resp.json()["id"]

    # Create site for second customer
    second_site_resp = client.post(
        "/api/v1/sites/test",
        json={
            "customer_id": second_customer_id,
            "name": "B18 Second Site",
        },
    )
    assert second_site_resp.status_code == 201
    second_site_id = second_site_resp.json()["id"]

    # Create job for original customer/site
    job_resp = client.post(
        "/api/v1/jobs/test",
        json={
            "customer_id": str(test_customer.id),
            "site_id": str(test_site.id),
        },
    )
    assert job_resp.status_code == 201
    job_id = job_resp.json()["id"]

    # Try to assign second customer's site to original customer's job — should fail
    patch_resp = client.patch(
        f"/api/v1/jobs/{job_id}/test",
        json={"site_id": second_site_id},
    )
    assert patch_resp.status_code == 400
    detail = patch_resp.json()["detail"]
    assert detail["status"] == 400
    assert "customer" in detail["detail"].lower()
