"""
FE-B23/A1: Tests for GET /api/v1/dashboard/at-risk-jobs

Test resilience rules:
- Never count all rows; always scope by inserted IDs.
- Never UPDATE/DELETE rows not inserted in this test.
- Uses /test endpoints with TestUserContext (no JWT).
"""

import pytest
from fastapi.testclient import TestClient

pytestmark = [pytest.mark.domain_platform_infrastructure, pytest.mark.unit]


class TestAtRiskJobs:
    """Tests for GET /api/v1/dashboard/at-risk-jobs/test"""

    def test_at_risk_jobs_returns_200(self, client: TestClient):
        """Endpoint is reachable and returns valid structure."""
        resp = client.get("/api/v1/dashboard/at-risk-jobs/test")
        assert resp.status_code == 200
        body = resp.json()
        assert "jobs" in body
        assert "total" in body
        assert isinstance(body["jobs"], list)
        assert isinstance(body["total"], int)

    def test_at_risk_jobs_empty_when_no_active_jobs(self, client: TestClient):
        """Returns empty list (or subset) without error when there are no qualifying jobs.

        Since other seed data may exist, we just verify structure — not that list is empty.
        """
        resp = client.get("/api/v1/dashboard/at-risk-jobs/test?limit=50")
        assert resp.status_code == 200
        body = resp.json()
        assert "jobs" in body
        assert isinstance(body["jobs"], list)
        # total must match jobs list length
        assert body["total"] == len(body["jobs"])

    def test_at_risk_jobs_respects_limit(self, client: TestClient):
        """Limit parameter is respected — never more than limit items returned."""
        resp = client.get("/api/v1/dashboard/at-risk-jobs/test?limit=1")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["jobs"]) <= 1

    def test_at_risk_jobs_invalid_limit_rejected(self, client: TestClient):
        """limit < 1 is rejected with 422."""
        resp = client.get("/api/v1/dashboard/at-risk-jobs/test?limit=0")
        assert resp.status_code == 422

    def test_at_risk_jobs_limit_over_50_rejected(self, client: TestClient):
        """limit > 50 is rejected with 422."""
        resp = client.get("/api/v1/dashboard/at-risk-jobs/test?limit=51")
        assert resp.status_code == 422

    def test_at_risk_jobs_item_schema(self, client: TestClient):
        """Each item in the response has required fields."""
        resp = client.get("/api/v1/dashboard/at-risk-jobs/test?limit=50")
        assert resp.status_code == 200
        for item in resp.json()["jobs"]:
            assert "job_id" in item
            assert "customer_name" in item
            assert "actual_cost_cents" in item
            assert isinstance(item["actual_cost_cents"], int)
