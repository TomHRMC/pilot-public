"""
TP-B10 — Dashboard Widgets — Test Endpoints

Coverage:
  1. GET    /api/v1/dashboard/widgets/test                           → list_widgets_test
  2. POST   /api/v1/dashboard/widgets/test                           → create_widget_test
  3. PATCH  /api/v1/dashboard/widgets/{widget_id}/test               → update_widget_test
  4. DELETE /api/v1/dashboard/widgets/{widget_id}/test               → delete_widget_test
  5. GET    /api/v1/dashboard/widgets/recent-customer-messages/test  → get_recent_customer_messages_test

Route ordering:
  - /widgets/test (list + create) BEFORE /widgets/{widget_id}
  - /widgets/recent-customer-messages/test BEFORE /widgets/{widget_id}

Also verifies:
  - 403 when TEST_ENDPOINT_ENABLED=false
  - 404 for unknown widget IDs
"""

import uuid
from unittest.mock import patch

from fastapi import status

from core.config import settings

BASE = "/api/v1/dashboard"
WIDGET_BASE = f"{BASE}/widgets"

VALID_WIDGET_PAYLOAD = {
    "widget_type": "profitability_summary",
    "widget_config_json": {},
    "position_x": 0,
    "position_y": 0,
    "width": 4,
    "height": 2,
}


# ==================== SECURITY GUARD TESTS ====================


class TestTpB10SecurityGuards:
    def test_list_widgets_blocked_when_disabled(self, client):
        """GET /widgets/test returns 403 when TEST_ENDPOINT_ENABLED=false."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", False):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.get(f"{WIDGET_BASE}/test")
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "test_endpoints_disabled" in response.json()["detail"]["error"]

    def test_create_widget_blocked_in_production(self, client):
        """POST /widgets/test returns 403 in production."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "production"):
                response = client.post(f"{WIDGET_BASE}/test", json=VALID_WIDGET_PAYLOAD)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_recent_messages_blocked_when_disabled(self, client):
        """GET /widgets/recent-customer-messages/test returns 403 when disabled."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", False):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.get(f"{WIDGET_BASE}/recent-customer-messages/test")
        assert response.status_code == status.HTTP_403_FORBIDDEN


# ==================== LIST WIDGETS /test ====================


class TestTpB10ListWidgets:
    def test_list_widgets_returns_200(self, client):
        """GET /widgets/test returns list (may be empty for test user)."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.get(f"{WIDGET_BASE}/test")
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.json(), list)

    def test_list_widgets_includes_created_widget(self, client):
        """After creating, widget appears in list."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                create_resp = client.post(
                    f"{WIDGET_BASE}/test", json=VALID_WIDGET_PAYLOAD
                )
                assert create_resp.status_code == status.HTTP_201_CREATED
                list_resp = client.get(f"{WIDGET_BASE}/test")
        assert list_resp.status_code == status.HTTP_200_OK
        ids = [w["id"] for w in list_resp.json()]
        assert create_resp.json()["id"] in ids


# ==================== CREATE WIDGET /test ====================


class TestTpB10CreateWidget:
    def test_create_widget_returns_201(self, client):
        """POST /widgets/test creates a new widget."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.post(f"{WIDGET_BASE}/test", json=VALID_WIDGET_PAYLOAD)
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["widget_type"] == "profitability_summary"
        assert "id" in data


# ==================== UPDATE WIDGET /test ====================


class TestTpB10UpdateWidget:
    def test_update_widget_returns_200(self, client):
        """PATCH /widgets/{id}/test updates widget position."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                create_resp = client.post(
                    f"{WIDGET_BASE}/test", json=VALID_WIDGET_PAYLOAD
                )
                widget_id = create_resp.json()["id"]
                update_resp = client.patch(
                    f"{WIDGET_BASE}/{widget_id}/test",
                    json={"position_x": 2, "position_y": 1},
                )
        assert update_resp.status_code == status.HTTP_200_OK
        assert update_resp.json()["position_x"] == 2

    def test_update_widget_404_for_unknown(self, client):
        """Returns 404 for unknown widget."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.patch(
                    f"{WIDGET_BASE}/{uuid.uuid4()}/test",
                    json={"position_x": 0},
                )
        assert response.status_code == status.HTTP_404_NOT_FOUND


# ==================== DELETE WIDGET /test ====================


class TestTpB10DeleteWidget:
    def test_delete_widget_returns_204(self, client):
        """DELETE /widgets/{id}/test hard-deletes the widget."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                create_resp = client.post(
                    f"{WIDGET_BASE}/test", json=VALID_WIDGET_PAYLOAD
                )
                widget_id = create_resp.json()["id"]
                delete_resp = client.delete(f"{WIDGET_BASE}/{widget_id}/test")
        assert delete_resp.status_code == status.HTTP_204_NO_CONTENT

    def test_delete_widget_no_longer_in_list(self, client):
        """After deletion, widget no longer appears in list."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                create_resp = client.post(
                    f"{WIDGET_BASE}/test", json=VALID_WIDGET_PAYLOAD
                )
                widget_id = create_resp.json()["id"]
                client.delete(f"{WIDGET_BASE}/{widget_id}/test")
                list_resp = client.get(f"{WIDGET_BASE}/test")
        ids = [w["id"] for w in list_resp.json()]
        assert widget_id not in ids

    def test_delete_widget_404_for_unknown(self, client):
        """Returns 404 for unknown widget."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.delete(f"{WIDGET_BASE}/{uuid.uuid4()}/test")
        assert response.status_code == status.HTTP_404_NOT_FOUND


# ==================== RECENT CUSTOMER MESSAGES /test ====================


class TestTpB10RecentCustomerMessages:
    def test_recent_messages_returns_200(self, client):
        """GET /widgets/recent-customer-messages/test returns messages (may be empty)."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.get(f"{WIDGET_BASE}/recent-customer-messages/test")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "messages" in data
        assert isinstance(data["messages"], list)

    def test_route_ordering_test_vs_widget_id(self, client):
        """Verify /widgets/test (list) and /widgets/recent-customer-messages/test are distinct from /widgets/{id}/test."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                list_resp = client.get(f"{WIDGET_BASE}/test")
                messages_resp = client.get(
                    f"{WIDGET_BASE}/recent-customer-messages/test"
                )
                patch_resp = client.patch(
                    f"{WIDGET_BASE}/{uuid.uuid4()}/test", json={"position_x": 0}
                )

        # list endpoint returns array
        assert list_resp.status_code == status.HTTP_200_OK
        assert isinstance(list_resp.json(), list)
        # messages endpoint returns messages dict
        assert messages_resp.status_code == status.HTTP_200_OK
        assert "messages" in messages_resp.json()
        # patch endpoint for unknown ID returns 404 (proves routing works correctly)
        assert patch_resp.status_code == status.HTTP_404_NOT_FOUND
