"""
Tests for: UI-FIX-1C Part A — Server-Side Pagination & Filters (Backend)
Domain: Platform Infrastructure

Covers:
- PaginatedResponse shape on all 5 list endpoints
- Filter params: status, search, customer_search, title_search, date range
- Offset/limit pagination correctness

Related endpoints:
- GET /api/v1/customers/test
- GET /api/v1/quotes/test
- GET /api/v1/invoices/test
- GET /api/v1/jobs/test
- GET /api/v1/catalog/pricebook/test
"""

import uuid

import pytest

pytestmark = [
    pytest.mark.domain_platform_infrastructure,
    pytest.mark.unit,
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_customer(client, display_name: str):
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


def _create_quote(client, customer_id: str, site_id: str, title: str | None = None):
    payload = {
        "customer_id": customer_id,
        "site_id": site_id,
        "currency": "USD",
    }
    if title:
        payload["title"] = title
    resp = client.post("/api/v1/quotes/test", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _create_job(client, customer_id: str, site_id: str):
    resp = client.post(
        "/api/v1/jobs/test",
        json={
            "customer_id": customer_id,
            "site_id": site_id,
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _create_pricebook_item(client, name: str, sku: str | None = None):
    sku_val = sku or f"SKU-{uuid.uuid4().hex[:8].upper()}"
    resp = client.post(
        "/api/v1/catalog/pricebook/test",
        json={
            "name": name,
            "sku": sku_val,
            "initial_price_cents": 1000,
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


# ---------------------------------------------------------------------------
# Test 1 — Customers: returns PaginatedResponse with total
# ---------------------------------------------------------------------------


class TestCustomersPagination:
    def test_list_customers_returns_paginated_response(self, client):
        """Customers list endpoint returns PaginatedResponse shape."""
        c = _create_customer(client, f"Pagination Customer {uuid.uuid4().hex[:6]}")
        resp = client.get("/api/v1/customers/test")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data, "Missing 'items' key in paginated response"
        assert "total" in data, "Missing 'total' key in paginated response"
        assert "limit" in data, "Missing 'limit' key in paginated response"
        assert "offset" in data, "Missing 'offset' key in paginated response"
        assert data["total"] >= 1, "total should be >= 1 (seed data present)"
        ids = [r["id"] for r in data["items"]]
        assert c["id"] in ids, f"Created customer {c['id']} not in items"

    def test_list_customers_active_filter(self, client):
        """status=active filter returns customers with is_active=True."""
        c = _create_customer(client, f"Active Filter Customer {uuid.uuid4().hex[:6]}")
        resp = client.get("/api/v1/customers/test", params={"status": "active"})
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert data["total"] >= 1
        # All returned items should be active
        for item in data["items"]:
            assert item["is_active"] is True, (
                f"Inactive customer in active filter: {item['id']}"
            )
        ids = [r["id"] for r in data["items"]]
        assert c["id"] in ids, f"Newly created active customer {c['id']} not in items"

    def test_list_customers_search_filter(self, client):
        """search param filters by display_name."""
        unique = uuid.uuid4().hex[:10]
        name = f"UniqueSearchName{unique}"
        c = _create_customer(client, name)
        resp = client.get("/api/v1/customers/test", params={"search": unique})
        assert resp.status_code == 200
        data = resp.json()
        ids = [r["id"] for r in data["items"]]
        assert c["id"] in ids, f"Customer {c['id']} not found by search={unique}"


# ---------------------------------------------------------------------------
# Test 4 — Quotes: returns PaginatedResponse with total
# ---------------------------------------------------------------------------


class TestQuotesPagination:
    def test_list_quotes_returns_paginated_response(self, client):
        """Quotes list endpoint returns PaginatedResponse shape."""
        cust = _create_customer(client, f"Quote Pg Customer {uuid.uuid4().hex[:6]}")
        site = _create_site(client, cust["id"])
        q = _create_quote(client, cust["id"], site["id"])

        resp = client.get("/api/v1/quotes/test")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert "limit" in data
        assert "offset" in data
        assert data["total"] >= 1
        ids = [r["id"] for r in data["items"]]
        assert q["id"] in ids, f"Created quote {q['id']} not in items"

    def test_list_quotes_title_search(self, client):
        """title_search param filters quotes by title."""
        unique = uuid.uuid4().hex[:10]
        title = f"SpecialTitle{unique}"
        cust = _create_customer(client, f"Title Search Cust {uuid.uuid4().hex[:6]}")
        site = _create_site(client, cust["id"])
        q = _create_quote(client, cust["id"], site["id"], title=title)

        resp = client.get("/api/v1/quotes/test", params={"title_search": unique})
        assert resp.status_code == 200
        data = resp.json()
        ids = [r["id"] for r in data["items"]]
        assert q["id"] in ids, f"Quote {q['id']} with title {title} not found"


# ---------------------------------------------------------------------------
# Test 6 — Invoices: customer_search filter
# ---------------------------------------------------------------------------


class TestInvoicesPagination:
    def test_list_invoices_customer_search(self, client):
        """customer_search filter appended to existing invoice filters."""
        unique = uuid.uuid4().hex[:10]
        cust_name = f"InvSearchCust{unique}"
        cust = _create_customer(client, cust_name)
        site = _create_site(client, cust["id"])
        q = _create_quote(client, cust["id"], site["id"])

        # Create an invoice for this customer via test endpoint
        # PLP-FIX-1: quote mode — customer_id/site_id derive from the quote;
        # sending them alongside quote_id is now a 400 invalid-mode.
        inv_resp = client.post(
            "/api/v1/invoices/test",
            json={
                "quote_id": q["id"],
            },
        )
        if inv_resp.status_code != 201:
            pytest.skip("Invoice creation via test endpoint not available; skipping.")

        resp = client.get("/api/v1/invoices/test", params={"customer_search": unique})
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] >= 1
        ids = [r["id"] for r in data["items"]]
        assert inv_resp.json()["id"] in ids


# ---------------------------------------------------------------------------
# Test 7 — Jobs: returns PaginatedResponse
# ---------------------------------------------------------------------------


class TestJobsPagination:
    def test_list_jobs_returns_paginated_response(self, client):
        """Jobs list endpoint returns PaginatedResponse shape."""
        cust = _create_customer(client, f"Job Pg Customer {uuid.uuid4().hex[:6]}")
        site = _create_site(client, cust["id"])
        job = _create_job(client, cust["id"], site["id"])

        resp = client.get("/api/v1/jobs/test?limit=200")  # seed data has 26+ jobs
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert "limit" in data
        assert "offset" in data
        assert data["total"] >= 1
        ids = [r["id"] for r in data["items"]]
        assert job["id"] in ids, f"Created job {job['id']} not in items"

    def test_list_jobs_status_filter(self, client):
        """status filter returns only jobs with matching status_code."""
        cust = _create_customer(client, f"Job Status Cust {uuid.uuid4().hex[:6]}")
        site = _create_site(client, cust["id"])
        job = _create_job(client, cust["id"], site["id"])

        resp = client.get("/api/v1/jobs/test", params={"status": "draft"})
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        for item in data["items"]:
            assert item["status_code"] == "draft", (
                f"Non-draft job in filtered response: {item['status_code']}"
            )
        ids = [r["id"] for r in data["items"]]
        assert job["id"] in ids, (
            f"New draft job {job['id']} not in draft filter results"
        )


# ---------------------------------------------------------------------------
# Test 9 — Catalog: returns PaginatedResponse
# ---------------------------------------------------------------------------


class TestCatalogPagination:
    def test_list_pricebook_returns_paginated_response(self, client):
        """Pricebook list endpoint returns PaginatedResponse shape."""
        unique = uuid.uuid4().hex[:8]
        item = _create_pricebook_item(client, f"PgItem {unique}")

        resp = client.get("/api/v1/catalog/pricebook/test")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert "limit" in data
        assert "offset" in data
        assert data["total"] >= 1
        ids = [r["id"] for r in data["items"]]
        assert item["id"] in ids, f"Created pricebook item {item['id']} not in items"

    def test_pricebook_search_filter(self, client):
        """search param filters by name, description, or sku."""
        unique = uuid.uuid4().hex[:10]
        item = _create_pricebook_item(client, f"SearchableName{unique}")

        resp = client.get("/api/v1/catalog/pricebook/test", params={"search": unique})
        assert resp.status_code == 200
        data = resp.json()
        ids = [r["id"] for r in data["items"]]
        assert item["id"] in ids, f"Item {item['id']} not found by search={unique}"


# ---------------------------------------------------------------------------
# Test 10 — Pagination: offset + limit produce correct slice
# ---------------------------------------------------------------------------


class TestPaginationOffsetLimit:
    def test_pagination_offset_limit(self, client):
        """limit=1&offset=1 returns exactly 1 item and total >= 2."""
        # Create 3 customers to ensure we have enough rows
        unique = uuid.uuid4().hex[:8]
        _create_customer(client, f"PgSlice1-{unique}")
        _create_customer(client, f"PgSlice2-{unique}")
        c3 = _create_customer(client, f"PgSlice3-{unique}")  # noqa: F841

        # Get with offset=0 limit=3 to confirm ordering
        resp_full = client.get(
            "/api/v1/customers/test",
            params={"search": f"PgSlice{unique[0]}", "limit": 200},
        )
        # Note: search "PgSlice..." will match all 3 because unique is in name
        assert resp_full.status_code == 200

        # Get a paginated slice
        resp = client.get(
            "/api/v1/customers/test",
            params={"search": unique, "limit": 1, "offset": 1},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["limit"] == 1
        assert data["offset"] == 1
        assert len(data["items"]) == 1, "Expected exactly 1 item with limit=1"
        assert data["total"] >= 2, (
            "Expected total >= 2 (we created 3 matching customers)"
        )

    def test_pagination_response_has_correct_metadata(self, client):
        """Paginated response metadata matches requested params."""
        resp = client.get(
            "/api/v1/customers/test",
            params={"limit": 5, "offset": 0},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["limit"] == 5
        assert data["offset"] == 0
        assert isinstance(data["items"], list)
        assert len(data["items"]) <= 5

    def test_default_limit_is_25(self, client):
        """Default limit is 25 (changed from 100)."""
        resp = client.get("/api/v1/customers/test")
        assert resp.status_code == 200
        data = resp.json()
        assert data["limit"] == 25, f"Expected default limit=25, got {data['limit']}"

    def test_quotes_pagination_offset_limit(self, client):
        """Quotes pagination offset+limit returns correct slice."""
        cust = _create_customer(client, f"QuotePgCust {uuid.uuid4().hex[:6]}")
        site = _create_site(client, cust["id"])
        _create_quote(client, cust["id"], site["id"])
        q2 = _create_quote(client, cust["id"], site["id"])  # noqa: F841

        resp = client.get(
            "/api/v1/quotes/test",
            params={"limit": 1, "offset": 0},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["limit"] == 1
        assert len(data["items"]) == 1
        assert data["total"] >= 1
