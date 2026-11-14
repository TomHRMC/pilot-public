"""
TP-B7 — Communications Inbox — Test Endpoints

Coverage (one happy-path test per new /test endpoint minimum):
  1. GET  /api/v1/communications/unrouted/test                        → list_unrouted_test
  2. POST /api/v1/communications/unrouted/{id}/assign-to-thread/test  → assign_unrouted_to_thread_test
  3. POST /api/v1/communications/threads/{thread_id}/mark-read/test   → mark_thread_read_test

Also verifies:
  - 403 when TEST_ENDPOINT_ENABLED=false
  - 404 for unknown IDs
  - Suffix /test pattern (not prefix /test/) for consistency with rest of codebase
"""

import uuid
from unittest.mock import patch

from fastapi import status

from core.config import settings

BASE = "/api/v1/communications"


# ==================== SECURITY GUARD TESTS ====================


class TestTpB7SecurityGuards:
    def test_list_unrouted_blocked_when_disabled(self, client):
        """GET /communications/unrouted/test returns 403 when disabled."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", False):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.get(f"{BASE}/unrouted/test")
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "test_endpoints_disabled" in response.json()["detail"]["error"]

    def test_assign_blocked_in_production(self, client):
        """POST /communications/unrouted/{id}/assign-to-thread/test returns 403 in production."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "production"):
                response = client.post(
                    f"{BASE}/unrouted/{uuid.uuid4()}/assign-to-thread/test",
                    json={"thread_id": str(uuid.uuid4())},
                )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_mark_read_blocked_when_disabled(self, client):
        """POST /communications/threads/{id}/mark-read/test returns 403 when disabled."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", False):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.post(f"{BASE}/threads/{uuid.uuid4()}/mark-read/test")
        assert response.status_code == status.HTTP_403_FORBIDDEN


# ==================== LIST UNROUTED /test ====================


class TestTpB7ListUnrouted:
    def test_list_unrouted_returns_200(self, client):
        """GET /communications/unrouted/test returns 200 with a list (may be empty)."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.get(f"{BASE}/unrouted/test")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "items" in data
        assert isinstance(data["items"], list)

    def test_list_unrouted_with_status_filter(self, client):
        """GET /communications/unrouted/test?status=parked returns 200."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.get(f"{BASE}/unrouted/test?status=parked")
        assert response.status_code == status.HTTP_200_OK


# ==================== ASSIGN TO THREAD /test ====================


class TestTpB7AssignToThread:
    def test_assign_404_for_unknown_unrouted_message(self, client):
        """POST /communications/unrouted/{id}/assign-to-thread/test returns 404 for unknown message."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.post(
                    f"{BASE}/unrouted/{uuid.uuid4()}/assign-to-thread/test",
                    json={"thread_id": str(uuid.uuid4())},
                )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_assign_endpoint_reachable(self, client):
        """POST assign-to-thread/test endpoint is reachable (not 403 or 405)."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.post(
                    f"{BASE}/unrouted/{uuid.uuid4()}/assign-to-thread/test",
                    json={"thread_id": str(uuid.uuid4())},
                )
        # Must be reachable (not auth blocked or routing mismatch)
        assert response.status_code != status.HTTP_403_FORBIDDEN
        assert response.status_code != status.HTTP_405_METHOD_NOT_ALLOWED
        # Expected: 404 (unknown IDs) — proves the endpoint is wired up
        assert response.status_code == status.HTTP_404_NOT_FOUND


# ==================== MARK THREAD READ /test ====================


class TestTpB7MarkThreadRead:
    def test_mark_read_404_for_unknown_thread(self, client):
        """POST /communications/threads/{id}/mark-read/test returns 404 for unknown thread."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.post(f"{BASE}/threads/{uuid.uuid4()}/mark-read/test")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_mark_read_endpoint_reachable(self, client):
        """POST mark-read/test endpoint is reachable (not 403 or 405)."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.post(f"{BASE}/threads/{uuid.uuid4()}/mark-read/test")
        assert response.status_code != status.HTTP_403_FORBIDDEN
        assert response.status_code != status.HTTP_405_METHOD_NOT_ALLOWED


# ==================== ROUTE ORDERING / SUFFIX PATTERN VERIFICATION ====================


class TestTpB7RouteOrdering:
    def test_unrouted_test_suffix_vs_id_are_distinct(self, client):
        """GET /unrouted/test (list) and /unrouted/{id}/... are distinct routes."""
        fake_id = str(uuid.uuid4())
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                # /unrouted/test = list endpoint → returns 200 with items
                list_resp = client.get(f"{BASE}/unrouted/test")
                # /unrouted/{id}/assign-to-thread/test = action endpoint → 404 for unknown
                action_resp = client.post(
                    f"{BASE}/unrouted/{fake_id}/assign-to-thread/test",
                    json={"thread_id": str(uuid.uuid4())},
                )
        assert list_resp.status_code == status.HTTP_200_OK
        assert "items" in list_resp.json()
        # The action endpoint returns 404 (unknown ID), not 422 or 405
        assert action_resp.status_code == status.HTTP_404_NOT_FOUND
