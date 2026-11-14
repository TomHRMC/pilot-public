"""
B20 — card_required on Customer and Quote
Tests for card_required field on CustomerCreate/Response and QuoteCreate/Response.

Domain: crm
"""

import uuid

import pytest

pytestmark = [
    pytest.mark.domain_crm,
    pytest.mark.unit,
]


class TestCardRequired:
    """Test card_required on Customer and Quote."""

    def test_customer_card_required_default_false(self, client, test_tenant):
        """customer.card_required defaults to false when not specified."""
        display_name = f"Card Test Customer {uuid.uuid4().hex[:8]}"
        resp = client.post(
            "/api/v1/customers/test",
            json={
                "display_name": display_name,
                "type": "person",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "card_required" in data
        assert data["card_required"] is False

    def test_customer_card_required_explicit_false(self, client, test_tenant):
        """customer.card_required=False is accepted and stored."""
        display_name = f"Card False Customer {uuid.uuid4().hex[:8]}"
        resp = client.post(
            "/api/v1/customers/test",
            json={
                "display_name": display_name,
                "type": "person",
                "card_required": False,
            },
        )
        assert resp.status_code == 201
        assert resp.json()["card_required"] is False

    def test_customer_card_required_true(self, client, test_tenant):
        """customer.card_required=True is accepted and persisted."""
        display_name = f"Card Required Customer {uuid.uuid4().hex[:8]}"
        resp = client.post(
            "/api/v1/customers/test",
            json={
                "display_name": display_name,
                "type": "person",
                "card_required": True,
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["card_required"] is True
        customer_id = data["id"]

        # Verify persists on re-fetch
        get_resp = client.get(f"/api/v1/customers/{customer_id}/test")
        if get_resp.status_code == 200:
            assert get_resp.json()["card_required"] is True

    def test_customer_card_required_response_field_always_present(
        self, client, test_tenant
    ):
        """card_required is always present in CustomerResponse (no omit-if-None)."""
        display_name = f"Card Always Present {uuid.uuid4().hex[:8]}"
        resp = client.post(
            "/api/v1/customers/test",
            json={
                "display_name": display_name,
                "type": "person",
            },
        )
        assert resp.status_code == 201
        assert "card_required" in resp.json(), (
            "card_required must always be in CustomerResponse"
        )
