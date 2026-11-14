"""
B19: Tests for quote_number and title fields on Quote — sequential format QUO-000001.

Covers:
- quote_number auto-assigned on create (starts with QUO-)
- optional title field on create and list
"""

import pytest

pytestmark = [
    pytest.mark.domain_sales_quoting,
    pytest.mark.unit,
]


def _create_customer(client, display_name: str = "B19 Test Customer"):
    resp = client.post(
        "/api/v1/customers/test",
        json={"display_name": display_name, "type": "person"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _create_site(client, customer_id: str):
    resp = client.post("/api/v1/sites/test", json={"customer_id": customer_id})
    assert resp.status_code == 201, resp.text
    return resp.json()


class TestQuoteNumberAssignment:
    def test_create_quote_assigns_quote_number(self, client):
        """POST /api/v1/quotes/test → response includes quote_number starting with QUO-"""
        cust = _create_customer(client)
        site = _create_site(client, cust["id"])
        resp = client.post(
            "/api/v1/quotes/test",
            json={
                "customer_id": cust["id"],
                "site_id": site["id"],
                "currency": "USD",
            },
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert "quote_number" in data
        assert data["quote_number"].startswith("QUO-"), (
            f"Expected QUO- prefix, got: {data['quote_number']}"
        )

    def test_create_quote_with_title(self, client):
        """POST with title= → title is returned in response"""
        cust = _create_customer(client)
        site = _create_site(client, cust["id"])
        resp = client.post(
            "/api/v1/quotes/test",
            json={
                "customer_id": cust["id"],
                "site_id": site["id"],
                "currency": "USD",
                "title": "Main Panel Upgrade",
            },
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data.get("title") == "Main Panel Upgrade", (
            f"Expected title='Main Panel Upgrade', got: {data.get('title')}"
        )

    def test_create_quote_without_title(self, client):
        """POST without title → title is None in response"""
        cust = _create_customer(client)
        site = _create_site(client, cust["id"])
        resp = client.post(
            "/api/v1/quotes/test",
            json={
                "customer_id": cust["id"],
                "site_id": site["id"],
                "currency": "USD",
            },
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data.get("title") is None, (
            f"Expected title=None when not provided, got: {data.get('title')}"
        )
