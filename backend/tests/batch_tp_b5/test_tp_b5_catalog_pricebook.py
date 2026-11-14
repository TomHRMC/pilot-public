"""
TP-B5 — Catalog Pricebook (FIND-171) — Test Endpoints

Coverage (one happy-path test per new /test endpoint minimum):
  1. GET   /api/v1/catalog/pricebook/test                          → list_pricebook_items_test
  2. POST  /api/v1/catalog/pricebook/test                          → create_pricebook_item_test
  3. GET   /api/v1/catalog/pricebook/{item_id}/test                → get_pricebook_item_test
  4. PATCH /api/v1/catalog/pricebook/{item_id}/test                → patch_pricebook_item_test
  5. POST  /api/v1/catalog/pricebook/{item_id}/price/test          → create_pricebook_item_price_test
  6. GET   /api/v1/catalog/pricebook/{item_id}/price-history/test  → get_pricebook_item_price_history_test

Also verifies:
  - 403 when TEST_ENDPOINT_ENABLED=false
  - 404 for unknown item IDs
  - Route ordering: /pricebook/test is distinct from /pricebook/{item_id}
"""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from fastapi import status

from app.models.quoting import PricebookItem
from core.config import settings

TEST_TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
TEST_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")

BASE = "/api/v1/catalog/pricebook"


# ==================== FIXTURES ====================


@pytest.fixture
def b5_pricebook_item(db_session, test_tenant):
    """Create a pre-existing PricebookItem (no version — just the item row) for test reads."""
    item = PricebookItem(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        sku=f"SKU-B5-{uuid.uuid4().hex[:6].upper()}",
        name="TP-B5 Test Item",
        description="A test pricebook item",
        is_active=True,
        created_by=TEST_USER_ID,
        updated_by=TEST_USER_ID,
    )
    db_session.add(item)
    db_session.commit()
    db_session.refresh(item)
    return item


# ==================== SECURITY GUARD TESTS ====================


class TestTpB5SecurityGuards:
    def test_list_blocked_when_disabled(self, client):
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", False):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.get(f"{BASE}/test")
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "test_endpoints_disabled" in response.json()["detail"]["error"]

    def test_create_blocked_in_production(self, client):
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "production"):
                response = client.post(
                    f"{BASE}/test",
                    json={"sku": "X", "name": "X", "initial_price_cents": 100},
                )
        assert response.status_code == status.HTTP_403_FORBIDDEN


# ==================== LIST PRICEBOOK /test ====================


class TestTpB5ListPricebook:
    def test_list_returns_200(self, client):
        """GET /pricebook/test returns 200 with a list."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.get(f"{BASE}/test")
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.json()["items"], list)  # UI-FIX-1C: paginated

    def test_list_includes_created_item(self, client, b5_pricebook_item):
        """List includes the pre-existing fixture item."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.get(f"{BASE}/test")
        ids = [item["id"] for item in response.json()["items"]]  # UI-FIX-1C: paginated
        assert str(b5_pricebook_item.id) in ids


# ==================== CREATE PRICEBOOK ITEM /test ====================


class TestTpB5CreatePricebookItem:
    def test_create_item_returns_201(self, client):
        """POST /pricebook/test creates a new pricebook item."""
        sku = f"SKU-B5-NEW-{uuid.uuid4().hex[:6].upper()}"
        payload = {
            "sku": sku,
            "name": "TP-B5 New Item",
            "initial_price_cents": 1500,
        }
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.post(f"{BASE}/test", json=payload)
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["sku"] == sku
        assert data["name"] == "TP-B5 New Item"
        assert data["is_active"] is True
        assert "id" in data

    def test_create_duplicate_sku_returns_409(self, client, b5_pricebook_item):
        """Returns 409 when SKU already exists for the tenant."""
        payload = {
            "sku": b5_pricebook_item.sku,
            "name": "Duplicate SKU",
            "initial_price_cents": 100,
        }
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.post(f"{BASE}/test", json=payload)
        assert response.status_code == status.HTTP_409_CONFLICT


# ==================== GET PRICEBOOK ITEM /test ====================


class TestTpB5GetPricebookItem:
    def test_get_item_returns_200(self, client, b5_pricebook_item):
        """GET /pricebook/{item_id}/test returns item detail."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.get(f"{BASE}/{b5_pricebook_item.id}/test")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == str(b5_pricebook_item.id)
        assert data["sku"] == b5_pricebook_item.sku

    def test_get_item_404_for_unknown(self, client):
        """Returns 404 for unknown item."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.get(f"{BASE}/{uuid.uuid4()}/test")
        assert response.status_code == status.HTTP_404_NOT_FOUND


# ==================== PATCH PRICEBOOK ITEM /test ====================


class TestTpB5PatchPricebookItem:
    def test_patch_updates_name(self, client, b5_pricebook_item):
        """PATCH /pricebook/{item_id}/test updates item name."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.patch(
                    f"{BASE}/{b5_pricebook_item.id}/test",
                    json={"name": "Updated Name via Test"},
                )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["name"] == "Updated Name via Test"

    def test_patch_404_for_unknown(self, client):
        """Returns 404 for unknown item."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.patch(
                    f"{BASE}/{uuid.uuid4()}/test",
                    json={"name": "nope"},
                )
        assert response.status_code == status.HTTP_404_NOT_FOUND


# ==================== CREATE PRICE /test ====================


class TestTpB5CreatePricebookItemPrice:
    def test_create_price_via_test_endpoint(self, client):
        """POST /pricebook/test creates item, then /price/test sets a price."""
        sku = f"SKU-PRICE-{uuid.uuid4().hex[:6].upper()}"
        # First create an item
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                create_resp = client.post(
                    f"{BASE}/test",
                    json={
                        "sku": sku,
                        "name": "Price Test Item",
                        "initial_price_cents": 1000,
                        "effective_from": datetime.now(UTC).isoformat(),
                    },
                )
        assert create_resp.status_code == status.HTTP_201_CREATED
        item_id = create_resp.json()["id"]

        # Set a new price (future date to avoid overlap)
        future_dt = (datetime.now(UTC) + timedelta(days=30)).isoformat()
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                price_resp = client.post(
                    f"{BASE}/{item_id}/price/test",
                    json={"unit_price_cents": 2000, "effective_from": future_dt},
                )
        assert price_resp.status_code == status.HTTP_201_CREATED
        assert price_resp.json()["default_unit_price_cents"] == 2000

    def test_create_price_404_for_unknown_item(self, client):
        """Returns 404 for unknown item."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.post(
                    f"{BASE}/{uuid.uuid4()}/price/test",
                    json={
                        "unit_price_cents": 500,
                        "effective_from": datetime.now(UTC).isoformat(),
                    },
                )
        assert response.status_code == status.HTTP_404_NOT_FOUND


# ==================== GET PRICE HISTORY /test ====================


class TestTpB5GetPriceHistory:
    def test_get_price_history_returns_list(self, client):
        """GET /pricebook/{item_id}/price-history/test returns price history."""
        sku = f"SKU-HIST-{uuid.uuid4().hex[:6].upper()}"
        # Create item with initial price
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                create_resp = client.post(
                    f"{BASE}/test",
                    json={
                        "sku": sku,
                        "name": "Price History Item",
                        "initial_price_cents": 3000,
                    },
                )
        item_id = create_resp.json()["id"]

        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                hist_resp = client.get(f"{BASE}/{item_id}/price-history/test")
        assert hist_resp.status_code == status.HTTP_200_OK
        history = hist_resp.json()
        assert isinstance(history, list)
        assert len(history) >= 1
        assert history[0]["default_unit_price_cents"] == 3000

    def test_price_history_404_for_unknown_item(self, client):
        """Returns 404 for unknown item."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.get(f"{BASE}/{uuid.uuid4()}/price-history/test")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_route_ordering_list_vs_get_item(self, client):
        """Verify GET /pricebook/test is distinct from GET /pricebook/{item_id}/test."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                # /pricebook/test = list endpoint → returns array
                list_resp = client.get(f"{BASE}/test")
                # /pricebook/{fake_id}/test = get-item endpoint → returns 404 for unknown
                get_resp = client.get(f"{BASE}/{uuid.uuid4()}/test")

        assert list_resp.status_code == status.HTTP_200_OK
        assert isinstance(list_resp.json()["items"], list)  # UI-FIX-1C: paginated
        assert get_resp.status_code == status.HTTP_404_NOT_FOUND
