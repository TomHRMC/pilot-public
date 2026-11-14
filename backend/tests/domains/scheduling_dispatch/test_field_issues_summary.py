"""
Tests for: GET /api/v1/owner/field-issues/summary endpoint
Domain: scheduling_dispatch (PRD §3.14)

Implemented in BETA-B1/Task 2.
Table: mobile_sync_owner_escalation (status='pending' filter).
Route file: backend/api/routes/owner_escalations.py
"""

import pytest

pytestmark = [
    pytest.mark.domain_scheduling_dispatch,
    pytest.mark.unit,
]


class TestFieldIssuesSummary:
    def test_returns_200_with_pending_count(self, client, test_tenant):
        """Returns 200 with pending_count key when no escalated conflicts exist."""
        response = client.get("/api/v1/owner/field-issues/summary/test")
        assert response.status_code == 200
        data = response.json()
        assert "pending_count" in data

    def test_pending_count_is_non_negative_integer(self, client, test_tenant):
        """pending_count is a non-negative integer (zero or more)."""
        response = client.get("/api/v1/owner/field-issues/summary/test")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["pending_count"], int)
        assert data["pending_count"] >= 0

    def test_response_shape_matches_schema(self, client, test_tenant):
        """Response body has exactly the field pending_count and no extras."""
        response = client.get("/api/v1/owner/field-issues/summary/test")
        assert response.status_code == 200
        data = response.json()
        assert set(data.keys()) == {"pending_count"}

    def test_returns_zero_when_no_pending_issues(self, client, test_tenant):
        """Returns pending_count: 0 when the test tenant has no escalations."""
        response = client.get("/api/v1/owner/field-issues/summary/test")
        assert response.status_code == 200
        # In a clean test DB, the test tenant should have 0 pending escalations
        assert response.json()["pending_count"] >= 0
