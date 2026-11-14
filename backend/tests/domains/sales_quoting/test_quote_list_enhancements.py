"""
Tests for: Quote list enhancements (BETA-B3 BE-2, BE-3, BE-4)
Domain: Sales & Quoting (PRD §3.10)

BE-2: ?status= filter on GET /api/v1/quotes
BE-3: status_code in list response
BE-4: customer_name in list response
"""

import pytest

pytestmark = [
    pytest.mark.domain_sales_quoting,
    pytest.mark.unit,
]


def _create_customer(client, display_name: str = "Test Customer"):
    resp = client.post(
        "/api/v1/customers/test",
        json={
            "display_name": display_name,
            "type": "person",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _create_site(client, customer_id: str):
    resp = client.post("/api/v1/sites/test", json={"customer_id": customer_id})
    assert resp.status_code == 201, resp.text
    return resp.json()


def _create_quote(client, customer_id: str, site_id: str):
    resp = client.post(
        "/api/v1/quotes/test",
        json={
            "customer_id": customer_id,
            "site_id": site_id,
            "currency": "USD",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


class TestQuoteListEnhancements:
    """BE-2 / BE-3 / BE-4: quote list status filter + status_code + customer_name."""

    def test_quote_list_includes_status_code(self, client):
        """BE-3: list response includes status_code field."""
        cust = _create_customer(client, "StatusCode Customer")
        site = _create_site(client, cust["id"])
        q = _create_quote(client, cust["id"], site["id"])

        resp = client.get("/api/v1/quotes/test")
        assert resp.status_code == 200
        items = resp.json()["items"]  # UI-FIX-1C: paginated response
        # Find our quote in the list
        our_quotes = [i for i in items if i["id"] == q["id"]]
        assert len(our_quotes) == 1, f"Quote {q['id']} not in list response"
        item = our_quotes[0]
        assert "status_code" in item, "status_code field missing from response"
        assert item["status_code"] is not None
        # Default status code should be "draft"
        assert item["status_code"] == "draft"

    def test_quote_list_includes_customer_name(self, client):
        """BE-4: list response includes customer_name field."""
        cust = _create_customer(client, "Named Customer Co")
        site = _create_site(client, cust["id"])
        q = _create_quote(client, cust["id"], site["id"])

        resp = client.get("/api/v1/quotes/test")
        assert resp.status_code == 200
        items = resp.json()["items"]  # UI-FIX-1C: paginated response
        our_quotes = [i for i in items if i["id"] == q["id"]]
        assert len(our_quotes) == 1
        item = our_quotes[0]
        assert "customer_name" in item, "customer_name field missing from response"
        assert item["customer_name"] == "Named Customer Co"

    def test_quote_list_no_status_filter_returns_all(self, client):
        """Without ?status= filter, list returns all quotes for tenant."""
        cust = _create_customer(client, "All Quotes Customer")
        site = _create_site(client, cust["id"])
        q = _create_quote(client, cust["id"], site["id"])

        resp = client.get("/api/v1/quotes/test")
        assert resp.status_code == 200
        ids = [i["id"] for i in resp.json()["items"]]  # UI-FIX-1C: paginated
        assert q["id"] in ids

    def test_quote_list_status_filter_matches_draft(self, client):
        """BE-2: ?status=draft returns only draft quotes."""
        cust = _create_customer(client, "Draft Filter Customer")
        site = _create_site(client, cust["id"])
        q = _create_quote(client, cust["id"], site["id"])

        resp = client.get("/api/v1/quotes/test", params={"status": "draft"})
        assert resp.status_code == 200
        items = resp.json()["items"]  # UI-FIX-1C: paginated
        # All returned items must have status_code = draft
        for item in items:
            assert item["status_code"] == "draft", (
                f"Non-draft quote in filtered response: {item['status_code']}"
            )
        # Our newly created quote (default=draft) must be in results
        ids = [i["id"] for i in items]
        assert q["id"] in ids

    def test_quote_list_status_filter_case_insensitive(self, client):
        """BE-2: ?status= filter is case-insensitive."""
        cust = _create_customer(client, "Case Filter Customer")
        site = _create_site(client, cust["id"])
        q = _create_quote(client, cust["id"], site["id"])

        resp = client.get("/api/v1/quotes/test", params={"status": "DRAFT"})
        assert resp.status_code == 200
        ids = [i["id"] for i in resp.json()["items"]]  # UI-FIX-1C: paginated
        assert q["id"] in ids

    def test_quote_list_status_filter_nonexistent_returns_empty_for_own_quote(
        self, client
    ):
        """BE-2: Filtering by non-existent status returns empty results for our quote."""
        cust = _create_customer(client, "Filter Miss Customer")
        site = _create_site(client, cust["id"])
        q = _create_quote(client, cust["id"], site["id"])

        resp = client.get(
            "/api/v1/quotes/test", params={"status": "nonexistent_status_xyz"}
        )
        assert resp.status_code == 200
        ids = [i["id"] for i in resp.json()["items"]]  # UI-FIX-1C: paginated
        # Our draft quote should NOT appear when filtering by nonexistent status
        assert q["id"] not in ids

    def test_quote_list_response_shape(self, client):
        """List response contains required BETA-B3 fields."""
        cust = _create_customer(client, "Shape Check Customer")
        site = _create_site(client, cust["id"])
        q = _create_quote(client, cust["id"], site["id"])

        resp = client.get("/api/v1/quotes/test")
        assert resp.status_code == 200
        items = resp.json()["items"]  # UI-FIX-1C: paginated
        our_quotes = [i for i in items if i["id"] == q["id"]]
        assert len(our_quotes) == 1
        item = our_quotes[0]

        # Verify full required shape
        required_fields = {
            "id",
            "tenant_id",
            "customer_id",
            "customer_name",
            "site_id",
            "status_id",
            "status_code",
            "subtotal_cents",
            "tax_cents",
            "total_cents",
        }
        for field in required_fields:
            assert field in item, (
                f"Required field '{field}' missing from quote list item"
            )
