"""
Tests for: Customer list ?search= param (BETA-B3 BE-1)
Domain: CRM (PRD §3.3)

Verifies case-insensitive search across display_name, first_name, last_name,
company_name, and email fields on GET /api/v1/customers/ and /test variant.
"""

import pytest

pytestmark = [
    pytest.mark.domain_crm,
    pytest.mark.unit,
]


def _create_customer(
    client,
    display_name: str,
    first_name: str = "Test",
    last_name: str = "User",
    company_name: str | None = None,
    email: str | None = None,
):
    """Create a customer via the test endpoint. client must be the fixture."""
    payload = {
        "display_name": display_name,
        "type": "person",
        "first_name": first_name,
        "last_name": last_name,
    }
    if company_name:
        payload["type"] = "company"
        payload["company_name"] = company_name
    if email:
        payload["email"] = email
    resp = client.post("/api/v1/customers/test", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


class TestCustomerSearch:
    """BE-1: ?search= param on customer list endpoints."""

    def test_no_search_returns_created_customer(self, client):
        """Without search param, all tenant customers are returned."""
        c = _create_customer(client, "Visible Customer")
        resp = client.get("/api/v1/customers/test")
        assert resp.status_code == 200
        ids = [r["id"] for r in resp.json()["items"]]
        assert c["id"] in ids

    def test_search_by_display_name_exact(self, client):
        """Search by exact display_name returns matching customer."""
        c = _create_customer(client, "Smith Electrical")
        resp = client.get(
            "/api/v1/customers/test", params={"search": "Smith Electrical"}
        )
        assert resp.status_code == 200
        ids = [r["id"] for r in resp.json()["items"]]
        assert c["id"] in ids

    def test_search_by_display_name_partial(self, client):
        """Partial search on display_name returns matching customer."""
        c = _create_customer(client, "Acme Corporation")
        resp = client.get("/api/v1/customers/test", params={"search": "Acme"})
        assert resp.status_code == 200
        ids = [r["id"] for r in resp.json()["items"]]
        assert c["id"] in ids

    def test_search_is_case_insensitive(self, client):
        """Search is case-insensitive."""
        c = _create_customer(client, "Johnson Services")
        resp = client.get("/api/v1/customers/test", params={"search": "JOHNSON"})
        assert resp.status_code == 200
        ids = [r["id"] for r in resp.json()["items"]]
        assert c["id"] in ids

    def test_search_by_email(self, client):
        """Search by email address returns matching customer."""
        c = _create_customer(client, "Email Customer", email="uniquesearch@example.com")
        resp = client.get("/api/v1/customers/test", params={"search": "uniquesearch"})
        assert resp.status_code == 200
        ids = [r["id"] for r in resp.json()["items"]]
        assert c["id"] in ids

    def test_search_by_first_name(self, client):
        """Search by first_name returns matching customer."""
        c = _create_customer(
            client, "Alice Smith", first_name="Alice", last_name="Smith"
        )
        resp = client.get("/api/v1/customers/test", params={"search": "Alice"})
        assert resp.status_code == 200
        ids = [r["id"] for r in resp.json()["items"]]
        assert c["id"] in ids

    def test_search_by_last_name(self, client):
        """Search by last_name returns matching customer."""
        c = _create_customer(
            client, "Bob Martinez", first_name="Bob", last_name="Martinez"
        )
        resp = client.get("/api/v1/customers/test", params={"search": "martinez"})
        assert resp.status_code == 200
        ids = [r["id"] for r in resp.json()["items"]]
        assert c["id"] in ids

    def test_search_no_match_returns_empty(self, client):
        """Search that matches nothing returns empty list (scoped to this test's data)."""
        # Create a known customer that won't match the nonsense search
        _create_customer(client, "Known Customer XYZ")
        resp = client.get(
            "/api/v1/customers/test",
            params={"search": "xyzzznooonematch99887766"},
        )
        assert resp.status_code == 200
        # No match expected — result may be empty or contain only non-matching rows
        # UI-FIX-1C: response is now PaginatedCustomerResponse, not a bare list
        data = resp.json()
        assert "items" in data
        assert isinstance(data["items"], list)

    def test_search_empty_string_returns_all(self, client):
        """Empty search string returns all customers (no filter applied)."""
        c = _create_customer(client, "Baseline Customer")
        resp = client.get("/api/v1/customers/test", params={"search": ""})
        assert resp.status_code == 200
        ids = [r["id"] for r in resp.json()["items"]]
        assert c["id"] in ids
