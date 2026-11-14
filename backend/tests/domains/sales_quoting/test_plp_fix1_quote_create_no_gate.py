"""
PLP-FIX-1 — Quote Route De-Gate Regression Tests
=================================================
Domain: sales_quoting (PRD §3.10)

Verifies that quote creation no longer carries a feature entitlement gate.
Before PLP-FIX-1, ``require_permission("quotes.create", feature_code="quotes_per_month")``
caused HTTP 402 for every tenant because ``quotes_per_month`` was never seeded
(phantom gate). The fix (Option B) removed the ``feature_code`` — quotes are
unlimited on every plan per PRD §3.11.

Tests:
  1. Quote create succeeds with no entitlement backing (skip_mock_entitlement_allowed)
  2. Entitlement service is never consulted on the quotes route
"""

import uuid
from unittest.mock import patch

import pytest
from sqlmodel import Session, select

from app.models.billing import Currency
from app.models.crm import Customer, CustomerType, Site
from app.models.quoting import QuoteStatus
from tests.test_phase2 import setup_test_user

pytestmark = [
    pytest.mark.domain_sales_quoting,
    pytest.mark.unit,
]


def _ensure_currency(db_session: Session) -> None:
    currency = db_session.exec(select(Currency).where(Currency.code == "USD")).first()
    if not currency:
        currency = Currency(code="USD", name="US Dollar", symbol="$")
        db_session.add(currency)
        db_session.flush()


def _seed_quote_prereqs(db_session: Session, tenant_id: uuid.UUID):
    """Seed the minimum rows needed for quote creation (customer, site, status, currency)."""
    _ensure_currency(db_session)

    customer = Customer(
        tenant_id=tenant_id,
        type=CustomerType.person,
        display_name=f"PLP-FIX-1 Quote Test {uuid.uuid4().hex[:6]}",
    )
    db_session.add(customer)
    db_session.flush()

    site = Site(
        tenant_id=tenant_id,
        customer_id=customer.id,
        name="PLP-FIX-1 Test Site",
    )
    db_session.add(site)
    db_session.flush()

    quote_status = QuoteStatus(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        code="draft",
        name="Draft",
        is_default=True,
    )
    db_session.add(quote_status)
    db_session.commit()

    return customer, site


class TestQuoteCreateNoGate:
    """PLP-FIX-1: quote creation must not be entitlement-gated."""

    @pytest.mark.skip_mock_entitlement_allowed
    def test_quote_create_succeeds_without_entitlement_backing(
        self, client, db_session, mock_cognito_jwt_verify
    ):
        """Quote creation returns 201 even with no subscription / no ppfv rows.

        Before PLP-FIX-1 this returned 402 ``feature_not_in_plan`` because the
        route consulted the entitlement service for ``quotes_per_month`` (never
        seeded). The route is now de-gated — only RBAC (``quotes.create``) applies.
        """
        headers, _user_id, tenant_id = setup_test_user(client, db_session)
        customer, site = _seed_quote_prereqs(db_session, tenant_id)

        payload = {
            "customer_id": str(customer.id),
            "site_id": str(site.id),
            "currency": "USD",
        }

        response = client.post("/api/v1/quotes", json=payload, headers=headers)
        assert response.status_code == 201, (
            f"Expected 201 (de-gated), got {response.status_code}: {response.text[:300]}"
        )
        data = response.json()
        assert data["customer_id"] == str(customer.id)

    def test_entitlement_service_never_consulted_on_quotes_route(
        self, client, db_session, mock_cognito_jwt_verify
    ):
        """The quotes route must not call ``get_cached_entitlement`` at all.

        Patches the entitlement lookup with a Mock that raises AssertionError
        if called — proving the de-gate is complete (no ``feature_code`` wiring).
        """
        headers, _user_id, tenant_id = setup_test_user(client, db_session)
        customer, site = _seed_quote_prereqs(db_session, tenant_id)

        payload = {
            "customer_id": str(customer.id),
            "site_id": str(site.id),
            "currency": "USD",
        }

        with patch(
            "services.entitlement_service.get_cached_entitlement",
            side_effect=AssertionError(
                "entitlement service should not be consulted on the de-gated quotes route"
            ),
        ):
            response = client.post("/api/v1/quotes", json=payload, headers=headers)

        assert response.status_code == 201, (
            f"Expected 201, got {response.status_code}: {response.text[:300]}"
        )
