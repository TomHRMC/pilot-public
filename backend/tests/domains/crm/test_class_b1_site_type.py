"""
Tests for: CLASS-B1 — site.site_type (create, validate, customer-type default)
Domain: crm (PRD §3.3)
"""

import uuid

import pytest

pytestmark = [
    pytest.mark.domain_crm,
    pytest.mark.unit,
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_customer(client, customer_type="person"):
    payload = {
        "display_name": f"Cust-{uuid.uuid4().hex[:6]}",
        "type": customer_type,
    }
    r = client.post("/api/v1/customers/test", json=payload)
    assert r.status_code == 201, r.text
    return r.json()


def _create_site(client, customer_id, **kwargs):
    r = client.post(
        "/api/v1/sites/test", json={"customer_id": str(customer_id), **kwargs}
    )
    assert r.status_code == 201, r.text
    return r.json()


# ---------------------------------------------------------------------------
# site.site_type — explicit value
# ---------------------------------------------------------------------------


class TestSiteTypeCreate:
    """CLASS-B1 — site.site_type create and validate."""

    def test_create_industrial_persists(self, client, test_tenant):
        """Creating a site with site_type='industrial' persists."""
        cust = _create_customer(client, customer_type="company")
        site = _create_site(client, cust["id"], site_type="industrial")
        assert site["site_type"] == "industrial"

        get_resp = client.get(f"/api/v1/sites/{site['id']}/test")
        assert get_resp.status_code == 200
        assert get_resp.json()["site_type"] == "industrial"

    def test_invalid_site_type_returns_422_rfc7807(self, client, test_tenant):
        """Invalid site_type returns 422 with RFC 7807 format."""
        cust = _create_customer(client)
        resp = client.post(
            "/api/v1/sites/test",
            json={"customer_id": str(cust["id"]), "site_type": "warehouse"},
        )
        assert resp.status_code == 422
        # FastAPI wraps HTTPException detail in {"detail": {...}}
        body = resp.json()["detail"]
        assert "type" in body
        assert "title" in body
        assert "status" in body
        assert body["status"] == 422


# ---------------------------------------------------------------------------
# site.site_type — customer-type default on create
# ---------------------------------------------------------------------------


class TestSiteTypeCustomerDefault:
    """CLASS-B1 — when site_type omitted, customer.type drives the default."""

    def test_company_customer_defaults_to_commercial(self, client, test_tenant):
        """Company customer → site_type defaults to 'commercial'."""
        cust = _create_customer(client, customer_type="company")
        site = _create_site(client, cust["id"])  # no site_type
        assert site["site_type"] == "commercial", (
            f"Expected 'commercial' for company customer, got '{site['site_type']}'"
        )

    def test_person_customer_defaults_to_residential(self, client, test_tenant):
        """Person customer → site_type defaults to 'residential'."""
        cust = _create_customer(client, customer_type="person")
        site = _create_site(client, cust["id"])  # no site_type
        assert site["site_type"] == "residential", (
            f"Expected 'residential' for person customer, got '{site['site_type']}'"
        )

    def test_explicit_overrides_customer_default(self, client, test_tenant):
        """Explicitly passing site_type overrides the customer-type default."""
        # Company customer but explicitly setting residential
        cust = _create_customer(client, customer_type="company")
        site = _create_site(client, cust["id"], site_type="residential")
        assert site["site_type"] == "residential"
