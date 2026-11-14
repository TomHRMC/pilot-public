"""PLP-FIX-2 — QCO Line-Type Lookup Endpoint + FK Hardening Regression Tests
============================================================================
Domain: sales_quoting (PRD §3.10)

Verifies:
  1. GET /api/v1/qco-line-types returns platform defaults (assert by code, not UUID)
  2. Exactly one row has is_default=True and its code is 'labor'
  3. Tenant override shadows platform row (is_tenant_override=True)
  4. Inactive rows are excluded
  5. Authenticated path smoke (setup_test_user + headers)
  6. FK hardening — bad qco_line_type_id returns RFC 7807 404 (Issue 5 regression)
  7. Happy path — real 'misc' type id (queried by code, never hardcoded) returns 201

Test isolation (Rule 16): all assertions scope by inserted ID/code; no total-count
assertions; no hardcoded seed UUIDs.
"""

import uuid
from datetime import UTC, datetime

import pytest
from sqlmodel import select

from app.models.quoting import QcoLineType
from tests.test_phase2 import setup_test_user

pytestmark = [
    pytest.mark.domain_sales_quoting,
    pytest.mark.unit,
]

BASE = "/api/v1/qco-line-types"
QUOTES_BASE = "/api/v1/quotes"

# The 5 seeded platform codes — the cross-environment contract (Issue 5 lesson)
EXPECTED_PLATFORM_CODES = {"labor", "material", "misc", "discount", "note"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_customer(client, display_name: str = "ZTEST-PLP-FIX-2 Customer"):
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


def _get_line_type_id_by_code(db_session, code: str) -> uuid.UUID:
    """Query the real platform row id by code — never hardcode a seed UUID."""
    row = db_session.exec(
        select(QcoLineType).where(
            QcoLineType.tenant_id == None,
            QcoLineType.code == code,
        )
    ).first()
    assert row is not None, f"Platform qco_line_type row for code='{code}' must exist"
    return row.id


# ---------------------------------------------------------------------------
# GET /api/v1/qco-line-types/test — platform defaults + merge logic
# ---------------------------------------------------------------------------


class TestQcoLineTypeList:
    """PLP-FIX-2 — GET /api/v1/qco-line-types lookup endpoint."""

    def test_returns_platform_defaults(self, client, test_tenant):
        """Platform defaults are visible without any tenant overrides.

        Asserts by code (stable cross-environment key), never by count or UUID
        (Rule 16 — seed UUIDs vary per environment, that is the Issue 5 lesson).
        """
        resp = client.get(f"{BASE}/test")
        assert resp.status_code == 200
        data = resp.json()
        codes = {row["code"] for row in data}
        assert EXPECTED_PLATFORM_CODES.issubset(codes), (
            f"Expected platform codes {EXPECTED_PLATFORM_CODES} ⊆ {codes}"
        )

    def test_exactly_one_default_and_it_is_labor(self, client, test_tenant):
        """Documents current seed truth: exactly one is_default=True row, code='labor'."""
        resp = client.get(f"{BASE}/test")
        assert resp.status_code == 200
        data = resp.json()
        defaults = [row for row in data if row["is_default"] is True]
        assert len(defaults) == 1, (
            f"Expected exactly 1 is_default=True row, got {len(defaults)}"
        )
        assert defaults[0]["code"] == "labor"

    def test_tenant_override_shadows_platform(self, client, test_tenant, db_session):
        """A tenant row with the same code as a platform default wins; is_tenant_override=True."""
        override = QcoLineType(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            code="misc",
            name="Tenant Misc Override",
            is_default=False,
            is_active=True,
        )
        override.created_at = datetime.now(UTC)
        override.updated_at = datetime.now(UTC)
        db_session.add(override)
        db_session.commit()

        resp = client.get(f"{BASE}/test")
        assert resp.status_code == 200
        data = resp.json()

        misc_rows = [r for r in data if r["code"] == "misc"]
        assert len(misc_rows) == 1, (
            f"Expected exactly 1 'misc' row after override, got {len(misc_rows)}"
        )
        assert misc_rows[0]["name"] == "Tenant Misc Override"
        assert misc_rows[0]["is_tenant_override"] is True

    def test_inactive_rows_excluded(self, client, test_tenant, db_session):
        """Inactive qco_line_type rows are not returned."""
        unique_code = f"test_inactive_{uuid.uuid4().hex[:6]}"
        inactive = QcoLineType(
            id=uuid.uuid4(),
            tenant_id=None,
            code=unique_code,
            name="Inactive Test Type",
            is_default=False,
            is_active=False,
        )
        inactive.created_at = datetime.now(UTC)
        inactive.updated_at = datetime.now(UTC)
        db_session.add(inactive)
        db_session.commit()

        resp = client.get(f"{BASE}/test")
        assert resp.status_code == 200
        codes = {r["code"] for r in resp.json()}
        assert unique_code not in codes

    @pytest.mark.skip_mock_entitlement_allowed
    def test_authenticated_path_smoke(
        self, client, db_session, mock_cognito_jwt_verify
    ):
        """Authenticated GET /api/v1/qco-line-types returns 200 with same shape."""
        headers, _user_id, _tenant_id = setup_test_user(client, db_session)

        resp = client.get(BASE, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        codes = {row["code"] for row in data}
        assert EXPECTED_PLATFORM_CODES.issubset(codes)
        # Shape check — every row has the response schema fields
        for row in data:
            assert "id" in row
            assert "code" in row
            assert "name" in row
            assert "is_default" in row
            assert "is_active" in row
            assert "is_tenant_override" in row


# ---------------------------------------------------------------------------
# FK Hardening — Issue 5 regression (POST /quotes/{id}/lines/test)
# ---------------------------------------------------------------------------


class TestQuoteLineFkHardening:
    """PLP-FIX-2 — validate-before-insert guard in _create_quote_line_impl."""

    def test_bad_line_type_id_returns_rfc7807_404(self, client, test_tenant):
        """Issue 5 regression: a nonexistent qco_line_type_id must return 404 RFC 7807,
        not a raw 500 ForeignKeyViolation at db.flush().
        """
        cust = _create_customer(client, "ZTEST-PLP-FIX-2 FK Bad")
        site = _create_site(client, cust["id"])
        quote = _create_quote(client, cust["id"], site["id"])

        payload = {
            "description": "ZTEST Bad Line Type",
            "quantity": "1.0",
            "unit_price_cents": 10000,
            "qco_line_type_id": str(uuid.uuid4()),  # random — guaranteed nonexistent
            "position": 1,
        }
        resp = client.post(f"{QUOTES_BASE}/{quote['id']}/lines/test", json=payload)
        assert resp.status_code == 404, (
            f"Expected 404 for bad line type, got {resp.status_code}: {resp.text[:300]}"
        )
        body = resp.json()["detail"]
        assert body["status"] == 404
        assert body["title"] == "Line type not found"
        assert body["type"].startswith("https://errors.pilotfortrades.com/")

    def test_happy_path_with_real_misc_type_id(self, client, test_tenant, db_session):
        """Happy path: POST a line with the real 'misc' type id (queried by code,
        never hardcoded) returns 201.
        """
        misc_id = _get_line_type_id_by_code(db_session, "misc")

        cust = _create_customer(client, "ZTEST-PLP-FIX-2 FK Happy")
        site = _create_site(client, cust["id"])
        quote = _create_quote(client, cust["id"], site["id"])

        payload = {
            "description": "ZTEST Happy Path Line",
            "quantity": "1.0",
            "unit_price_cents": 10000,
            "qco_line_type_id": str(misc_id),
            "position": 1,
        }
        resp = client.post(f"{QUOTES_BASE}/{quote['id']}/lines/test", json=payload)
        assert resp.status_code == 201, (
            f"Expected 201 for valid line type, got {resp.status_code}: {resp.text[:300]}"
        )
        assert resp.json()["qco_line_type_id"] == str(misc_id)
