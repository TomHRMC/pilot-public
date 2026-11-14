"""PLP-FIX-3 — Quote v1-at-Create + Versionless-Quote Backfill (Issue 6)
============================================================================
Domain: sales_quoting (PRD §3.10)

Verifies the invariant "every quote has an active v1 from creation":
  1. POST /api/v1/quotes/test → 201; exactly one active quote_version (v1)
     with snapshot containing 'quote' + 'lines' (== []) keys.
  2. Issue 6 regression — a created quote is immediately viewable via
     GET /api/v1/quotes/{id}/detail/test (NO hand-built version) → 200;
     quote_version_id == the auto-created v1 id.
  3. An explicit version POST after create yields v2 (auto v1 occupies v1);
     detail now returns the v2 id (latest-active rule).
  4. Create quote → add a real line (qco_line_type_id queried by code, never
     hardcoded) → detail shows the line in line_items.

Test isolation (Rule 16): all assertions scope by inserted ID; no total-count
assertions; no hardcoded seed UUIDs; client fixture only (no module-level
TestClient); test_tenant-family fixtures; do NOT modify conftest
test_quote_version fixture.
"""

import pytest
from sqlmodel import select

from app.models.quoting import QuoteVersion

pytestmark = [
    pytest.mark.domain_sales_quoting,
    pytest.mark.unit,
]

QUOTES_BASE = "/api/v1/quotes"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_customer(client, display_name: str = "ZTEST-PLP-FIX-3 Customer"):
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
        f"{QUOTES_BASE}/test",
        json={"customer_id": customer_id, "site_id": site_id, "currency": "USD"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _get_line_type_id_by_code(db_session, code: str):
    """Query the real platform row id by code — never hardcode a seed UUID."""
    from app.models.quoting import QcoLineType

    row = db_session.exec(
        select(QcoLineType).where(
            QcoLineType.tenant_id == None,
            QcoLineType.code == code,
        )
    ).first()
    assert row is not None, f"Platform qco_line_type row for code='{code}' must exist"
    return row.id


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestQuoteVersionAtCreate:
    """PLP-FIX-3 — every quote gets an active v1 at creation time."""

    def test_create_quote_creates_active_v1(self, client, test_tenant, db_session):
        """POST /quotes/test → exactly one active quote_version (v1).

        Asserts the snapshot shape: has 'quote' + 'lines' keys, lines == []
        (no lines exist at create time).
        """
        cust = _create_customer(client)
        site = _create_site(client, cust["id"])
        quote = _create_quote(client, cust["id"], site["id"])
        quote_id = quote["id"]

        versions = db_session.exec(
            select(QuoteVersion).where(QuoteVersion.quote_id == quote_id)
        ).all()
        assert len(versions) == 1, (
            f"Expected exactly 1 version for new quote, got {len(versions)}"
        )
        v1 = versions[0]
        assert v1.version_no == 1
        assert v1.is_active is True
        snap = v1.snapshot
        assert "quote" in snap, "snapshot must contain 'quote' key"
        assert "lines" in snap, "snapshot must contain 'lines' key"
        assert snap["lines"] == [], "v1 snapshot lines must be empty at create"

    def test_created_quote_viewable_via_detail(self, client, test_tenant, db_session):
        """Issue 6 regression — created quote is immediately viewable via /detail.

        No hand-built version; the auto-created v1 satisfies the active-version
        requirement of get_quote_detail(). quote_version_id == the auto v1 id.
        """
        cust = _create_customer(client, display_name="ZTEST-PLP-FIX-3 Detail Cust")
        site = _create_site(client, cust["id"])
        quote = _create_quote(client, cust["id"], site["id"])
        quote_id = quote["id"]

        # The auto-created v1 id (scoped to this quote)
        v1 = db_session.exec(
            select(QuoteVersion).where(QuoteVersion.quote_id == quote_id)
        ).first()
        assert v1 is not None, "auto v1 must exist"
        auto_v1_id = str(v1.id)

        resp = client.get(f"{QUOTES_BASE}/{quote_id}/detail/test")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["id"] == quote_id
        assert data["quote_version_id"] == auto_v1_id, (
            "detail quote_version_id must equal the auto-created v1 id"
        )

    def test_explicit_version_after_create_is_v2(self, client, test_tenant, db_session):
        """Explicit version POST after create yields v2 (auto v1 occupies v1).

        Detail now returns the v2 id (latest-active-by-version_no rule).
        """
        cust = _create_customer(client, display_name="ZTEST-PLP-FIX-3 V2 Cust")
        site = _create_site(client, cust["id"])
        quote = _create_quote(client, cust["id"], site["id"])
        quote_id = quote["id"]

        # Explicit version POST (test twin)
        resp = client.post(f"{QUOTES_BASE}/{quote_id}/versions/test")
        assert resp.status_code == 201, resp.text
        v2 = resp.json()
        assert v2["version_no"] == 2, (
            f"explicit version after create must be v2, got {v2['version_no']}"
        )

        # Detail now returns the v2 id (latest active by version_no desc)
        detail = client.get(f"{QUOTES_BASE}/{quote_id}/detail/test")
        assert detail.status_code == 200, detail.text
        assert detail.json()["quote_version_id"] == v2["id"], (
            "detail must return the latest active version id (v2)"
        )

    def test_create_quote_line_then_detail_shows_line(
        self, client, test_tenant, db_session
    ):
        """Create quote → add a real line → detail shows the line in line_items.

        qco_line_type_id is queried by code via db_session (never hardcoded).
        """
        cust = _create_customer(client, display_name="ZTEST-PLP-FIX-3 Line Cust")
        site = _create_site(client, cust["id"])
        quote = _create_quote(client, cust["id"], site["id"])
        quote_id = quote["id"]

        line_type_id = str(_get_line_type_id_by_code(db_session, "misc"))

        line_payload = {
            "position": 1,
            "qco_line_type_id": line_type_id,
            "description": "PLP-FIX-3 proof line",
            "quantity": 1.0,
            "unit_price_cents": 7500,
        }
        line_resp = client.post(
            f"{QUOTES_BASE}/{quote_id}/lines/test", json=line_payload
        )
        assert line_resp.status_code == 201, line_resp.text
        line_id = line_resp.json()["id"]

        detail = client.get(f"{QUOTES_BASE}/{quote_id}/detail/test")
        assert detail.status_code == 200, detail.text
        items = detail.json()["line_items"]
        matching = [li for li in items if li["id"] == line_id]
        assert len(matching) == 1, (
            f"detail line_items must contain the created line, got {len(matching)}"
        )
        assert matching[0]["description"] == "PLP-FIX-3 proof line"
