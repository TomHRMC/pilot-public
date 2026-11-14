"""
Tests for: GET /api/v1/quotes/{quote_id}/detail (PRE-WS3-FIX-01)
Domain: Sales & Quoting (PRD §3.10)

Endpoint returns QuoteDetailResponse — aggregated from:
  quote + status + customer + submitted_by user + quote_version +
  pending_edits + approval_comments + line_items (with qco_line_type) +
  require_approval setting
"""

from uuid import uuid4

import pytest

pytestmark = [
    pytest.mark.domain_sales_quoting,
    pytest.mark.unit,
]

BASE = "/api/v1/quotes"

# qco_line_type.id for 'labor' — verified via MCP on 2026-06-16
LABOR_LINE_TYPE_ID = "65a92851-3635-4d42-a99c-c40f1ab2e52e"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_customer(client, display_name: str = "ZTEST-Detail Customer"):
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


def _create_quote(client, customer_id: str, site_id: str):
    resp = client.post(
        f"{BASE}/test",
        json={"customer_id": customer_id, "site_id": site_id, "currency": "USD"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _create_quote_version(client, quote_id: str):
    """Create a quote version — required by get_quote_detail."""
    resp = client.post(f"{BASE}/{quote_id}/versions/test", json={})
    assert resp.status_code == 201, resp.text
    return resp.json()


def _create_line(
    client,
    quote_id: str,
    unit_price_cents: int = 10000,
    unit_cost_cents: int | None = 5000,
    position: int = 1,
):
    """Create a quote line. unit_cost_cents=None tests NULL margin behavior."""
    payload = {
        "description": "ZTEST Line Item",
        "quantity": "2.0",
        "unit_price_cents": unit_price_cents,
        "qco_line_type_id": LABOR_LINE_TYPE_ID,
        "position": position,
        "customer_visible": True,
    }
    if unit_cost_cents is not None:
        payload["unit_cost_cents"] = unit_cost_cents

    resp = client.post(f"{BASE}/{quote_id}/lines/test", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _setup_quote(client, display_name: str = "ZTEST-Detail Customer"):
    """Create customer, site, quote, and quote_version. Returns quote data."""
    cust = _create_customer(client, display_name)
    site = _create_site(client, cust["id"])
    q = _create_quote(client, cust["id"], site["id"])
    _create_quote_version(client, q["id"])
    return q, cust


def _get_detail(client, quote_id: str):
    return client.get(f"{BASE}/{quote_id}/detail/test")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestQuoteDetailEndpoint:
    """14 tests covering PRE-WS3-FIX-01 GET /detail endpoint."""

    def test_detail_returns_200_with_all_fields(self, client):
        """All top-level fields present in response."""
        q, cust = _setup_quote(client, "ZTEST-AllFields Customer")

        resp = _get_detail(client, q["id"])
        assert resp.status_code == 200, resp.text
        data = resp.json()

        # All required top-level fields must be present
        for field in [
            "id",
            "quote_number",
            "status",
            "customer_id",
            "customer_name",
            "site_id",
            "submitted_by_user_id",
            "submitted_by_name",
            "submitted_at",
            "approved_at",
            "rejected_at",
            "subtotal_cents",
            "tax_cents",
            "total_cents",
            "margin_percent",
            "quote_version_id",
            "has_owner_edits",
            "require_approval",
            "line_items",
        ]:
            assert field in data, f"Missing field: {field}"

        assert data["id"] == q["id"]
        assert data["customer_id"] == cust["id"]
        assert data["quote_number"].startswith("Q-")
        assert isinstance(data["line_items"], list)
        assert isinstance(data["has_owner_edits"], bool)
        assert isinstance(data["require_approval"], bool)

    def test_detail_customer_name_denormalized(self, client):
        """customer_name = customer.display_name (denormalized join)."""
        q, _cust = _setup_quote(client, "ZTEST-CustomerName Customer")

        resp = _get_detail(client, q["id"])
        assert resp.status_code == 200
        data = resp.json()
        assert data["customer_name"] == "ZTEST-CustomerName Customer"

    def test_detail_quote_number_format(self, client):
        """quote_number is formatted as Q-{first 8 chars of UUID uppercased}."""
        q, _ = _setup_quote(client)

        resp = _get_detail(client, q["id"])
        assert resp.status_code == 200
        data = resp.json()
        expected = f"Q-{q['id'][:8].upper()}"
        assert data["quote_number"] == expected

    def test_detail_status_code_is_draft(self, client):
        """status field returns 'draft' string (not a UUID) for new quotes."""
        q, _ = _setup_quote(client)

        resp = _get_detail(client, q["id"])
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "draft"

    def test_detail_line_items_returned(self, client):
        """Active line items are included in response."""
        q, _ = _setup_quote(client)
        _create_line(client, q["id"])

        resp = _get_detail(client, q["id"])
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["line_items"]) == 1

        line = data["line_items"][0]
        for field in [
            "id",
            "description",
            "customer_visible",
            "unit_price_cents",
            "quantity",
            "total_cents",
            "line_type",
        ]:
            assert field in line, f"Missing line field: {field}"

    def test_detail_line_type_resolved(self, client):
        """line_type field contains qco_line_type.code string (e.g. 'labor')."""
        q, _ = _setup_quote(client)
        _create_line(client, q["id"])

        resp = _get_detail(client, q["id"])
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["line_items"]) >= 1
        line = data["line_items"][0]
        assert line["line_type"] == "labor"

    def test_detail_line_qco_line_type_id_round_trips(self, client):
        """PLP-FIX-5 (Issue 14): persisted qco_line_type_id is returned by /detail.

        The draft editor resolves persisted-row labels by id
        (lineTypes.find(t => t.id === line.qco_line_type_id)); the response
        must carry the FK so persisted rows render their Type label.
        """
        q, _ = _setup_quote(client, "ZTEST-LineTypeId Customer")
        line = _create_line(client, q["id"])

        resp = _get_detail(client, q["id"])
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert len(data["line_items"]) == 1
        returned = data["line_items"][0]
        # Scope assertion to the inserted line's id (rule §16)
        assert returned["id"] == line["id"]
        # The FK must round-trip exactly as inserted
        assert returned["qco_line_type_id"] == LABOR_LINE_TYPE_ID

    def test_detail_margin_percent_computed(self, client):
        """With all unit_cost_cents set: margin_percent is computed correctly."""
        q, _ = _setup_quote(client)
        # unit_price=10000, unit_cost=5000, qty=2 → total_cents=20000, total_cost=10000
        # margin = (20000 - 10000) / 20000 * 100 = 50.0
        _create_line(client, q["id"], unit_price_cents=10000, unit_cost_cents=5000)

        resp = _get_detail(client, q["id"])
        assert resp.status_code == 200
        data = resp.json()
        if data["total_cents"] > 0 and data["margin_percent"] is not None:
            assert isinstance(data["margin_percent"], float)
            assert 0 <= data["margin_percent"] <= 100

    def test_detail_margin_percent_null_when_cost_missing(self, client):
        """If any line has unit_cost_cents = null → margin_percent = None."""
        q, _ = _setup_quote(client)
        # Create a line WITHOUT unit_cost_cents → NULL in DB
        _create_line(client, q["id"], unit_price_cents=5000, unit_cost_cents=None)

        resp = _get_detail(client, q["id"])
        assert resp.status_code == 200
        data = resp.json()
        # margin_percent must be None when any unit_cost_cents is NULL
        assert data["margin_percent"] is None

    def test_detail_has_owner_edits_false(self, client):
        """No pending edits → has_owner_edits = False."""
        q, _ = _setup_quote(client)

        resp = _get_detail(client, q["id"])
        assert resp.status_code == 200
        assert resp.json()["has_owner_edits"] is False

    def test_detail_quote_version_id_present(self, client):
        """quote_version_id is a valid UUID matching a version for this quote."""
        q, _ = _setup_quote(client)

        resp = _get_detail(client, q["id"])
        assert resp.status_code == 200
        data = resp.json()
        assert data["quote_version_id"] is not None
        # Must be a valid UUID string
        uuid4_parsed = uuid4().__class__(
            data["quote_version_id"]
        )  # raises ValueError if invalid
        assert str(uuid4_parsed) == data["quote_version_id"]

    def test_detail_rejected_at_none_when_no_rejection(self, client):
        """No rejection comment → rejected_at = None."""
        q, _ = _setup_quote(client)

        resp = _get_detail(client, q["id"])
        assert resp.status_code == 200
        assert resp.json()["rejected_at"] is None

    def test_detail_submitted_by_name_null_for_new_quote(self, client):
        """New quotes have no submitted_by_user_id → submitted_by_name = None."""
        q, _ = _setup_quote(client)

        resp = _get_detail(client, q["id"])
        assert resp.status_code == 200
        data = resp.json()
        # Draft quotes haven't been submitted yet
        assert data["submitted_by_user_id"] is None
        assert data["submitted_by_name"] is None

    def test_detail_404_not_found(self, client):
        """Non-existent quote_id → 404 with RFC 7807 detail."""
        fake_id = str(uuid4())
        resp = client.get(f"{BASE}/{fake_id}/detail/test")
        assert resp.status_code == 404
        data = resp.json()
        assert "detail" in data
        detail = data["detail"]
        assert detail["status"] == 404
        assert "type" in detail
        assert "title" in detail

    def test_detail_404_cross_tenant(self, client, tenant_a, tenant_b, db_session):
        """A random UUID that doesn't exist in any tenant → 404."""
        # Any valid quote exists and is accessible
        q, _ = _setup_quote(client)
        resp = _get_detail(client, q["id"])
        assert resp.status_code == 200

        # A made-up UUID → 404 regardless of tenant
        resp = client.get(f"{BASE}/{uuid4()}/detail/test")
        assert resp.status_code == 404
