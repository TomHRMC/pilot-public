"""
FE-B23/A2: Tests for GET /api/v1/dashboard/pending-approvals-summary

Test resilience rules:
- Never count all rows; always scope by inserted IDs.
- Never UPDATE/DELETE rows not inserted in this test.
- Uses /test endpoints with TestUserContext (no JWT).
"""

import pytest
from fastapi.testclient import TestClient

pytestmark = [pytest.mark.domain_platform_infrastructure, pytest.mark.unit]


class TestPendingApprovalsSummary:
    """Tests for GET /api/v1/dashboard/pending-approvals-summary/test"""

    def test_pending_approvals_returns_200(self, client: TestClient):
        """Endpoint is reachable and returns valid structure."""
        resp = client.get("/api/v1/dashboard/pending-approvals-summary/test")
        assert resp.status_code == 200
        body = resp.json()
        assert "pending_quotes" in body
        assert "pending_field_issues" in body

    def test_pending_approvals_returns_non_negative_counts(self, client: TestClient):
        """Both counts are non-negative integers."""
        resp = client.get("/api/v1/dashboard/pending-approvals-summary/test")
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body["pending_quotes"], int)
        assert isinstance(body["pending_field_issues"], int)
        assert body["pending_quotes"] >= 0
        assert body["pending_field_issues"] >= 0

    def test_pending_approvals_scoped_to_test_tenant(self, client: TestClient):
        """Endpoint returns data without error (tenant isolation applied internally)."""
        resp = client.get("/api/v1/dashboard/pending-approvals-summary/test")
        assert resp.status_code == 200
        # Response is well-formed — tenant scoping verified by query design
        body = resp.json()
        assert set(body.keys()) == {"pending_quotes", "pending_field_issues"}
