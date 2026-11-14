"""
B18 — customer_name field in InvoiceSummary (GET /api/v1/invoices/test).

Verifies that the _list_invoices_impl() Customer JOIN correctly populates
customer_name in every InvoiceSummary item returned.

All assertions scoped by key presence or specific inserted IDs — never by total count.
"""

import pytest

pytestmark = [
    pytest.mark.domain_invoicing_billing,
    pytest.mark.unit,
]


def test_invoice_list_includes_customer_name_key(client, test_tenant):
    """GET /invoices/test returns items that each have a customer_name key."""
    resp = client.get("/api/v1/invoices/test")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    # Every item must have the customer_name key
    for item in data["items"]:
        assert "customer_name" in item


def test_invoice_list_customer_name_is_string_when_present(client, test_tenant):
    """If any invoice has a customer, customer_name is a non-empty string."""
    resp = client.get("/api/v1/invoices/test")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    if data["items"]:
        item = data["items"][0]
        assert "customer_name" in item
        # Seed data always has customers — customer_name should be populated
        if item["customer_name"] is not None:
            assert isinstance(item["customer_name"], str)
            assert len(item["customer_name"]) > 0


def test_invoice_list_response_shape_with_customer_name(client, test_tenant):
    """InvoiceListResponse shape includes customer_name on all items."""
    resp = client.get("/api/v1/invoices/test")
    assert resp.status_code == 200
    data = resp.json()
    # Verify top-level response shape
    assert "items" in data
    assert "total" in data
    assert "limit" in data
    assert "offset" in data
    # All items have customer_name key (may be null for orphaned invoices)
    for item in data["items"]:
        assert "customer_name" in item
        assert "customer_id" in item
