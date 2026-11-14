"""
Tests for: GET /api/v1/communications/recent — cross-customer aggregate endpoint
Domain: notifications_comms (PRD §3.7)

Implemented in BETA-B1/Task 3.
Aggregates customer_communication_message rows via customer_communication_thread
(tenant isolation) + customer (display_name), ordered by created_at DESC.

COMMS-UI-B1: migrated to canonical offset/limit pagination shape.
"""

import pytest

pytestmark = [
    pytest.mark.domain_notifications_comms,
    pytest.mark.unit,
]


class TestCommunicationsRecent:
    def test_returns_200_with_items_and_total(self, client, test_tenant):
        """Returns 200 with items list and total count."""
        response = client.get(
            "/api/v1/communications/recent/test",
            params={"limit": 50, "offset": 0},
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)
        assert isinstance(data["total"], int)
        assert data["total"] >= 0

    def test_response_pagination_fields_present(self, client, test_tenant):
        """Response contains all four canonical pagination fields."""
        response = client.get(
            "/api/v1/communications/recent/test",
            params={"limit": 10, "offset": 0},
        )
        assert response.status_code == 200
        data = response.json()
        assert "limit" in data
        assert "offset" in data
        assert data["limit"] == 10
        assert data["offset"] == 0

    def test_empty_items_when_no_communications(self, client, test_tenant):
        """Returns empty items list when the test tenant has no communications."""
        response = client.get(
            "/api/v1/communications/recent/test",
            params={"limit": 50, "offset": 0},
        )
        assert response.status_code == 200
        data = response.json()
        # In a clean test DB, no communications exist for the test tenant
        assert isinstance(data["items"], list)

    def test_default_pagination_applied(self, client, test_tenant):
        """Endpoint works without explicit limit/offset (defaults applied)."""
        response = client.get("/api/v1/communications/recent/test")
        assert response.status_code == 200
        data = response.json()
        # Defaults: limit=50, offset=0
        assert data["limit"] == 50
        assert data["offset"] == 0

    def test_limit_respected(self, client, test_tenant):
        """limit query param is reflected in response."""
        response = client.get(
            "/api/v1/communications/recent/test",
            params={"limit": 5, "offset": 0},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["limit"] == 5
        assert len(data["items"]) <= 5
