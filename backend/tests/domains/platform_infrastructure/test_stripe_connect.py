"""
Tests for: Stripe Connect Account Links endpoints (UI-FIX-2F)
Domain: Platform Infrastructure (PRD §3.8)

Tests the three Stripe Connect endpoints:
  GET    /api/v1/settings/billing/stripe-connect/status/test
  POST   /api/v1/settings/billing/stripe-connect/onboard/test
  DELETE /api/v1/settings/billing/stripe-connect/test

PLP-FIX-6: fixtures migrated from plain-dict mocks to real ``construct_from``
``StripeObject`` instances. Any regression to dict-style ``.get()`` on a
``StripeObject`` in the impl fails here, not in prod.
"""

from unittest.mock import MagicMock, patch

import pytest
import stripe
from sqlmodel import Session, select

from app.models.core import Tenant

pytestmark = [
    pytest.mark.domain_platform_infrastructure,
    pytest.mark.unit,
]

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

BASE = "/api/v1/settings/billing"

_FACTORY = "api.routes.stripe_connect._get_stripe_connect_client"


def _get_test_tenant(db: Session, test_tenant) -> Tenant:
    """Re-fetch the test tenant row within the current test transaction."""
    return db.exec(select(Tenant).where(Tenant.id == test_tenant.id)).first()


def _make_connect_account(**overrides) -> "stripe.Account":
    """v15-faithful fixture: a REAL StripeObject (attribute access, NO .get()).

    Any regression to dict-style access in the impl fails here, not in prod.
    """
    values = {
        "id": "acct_test_123",
        "charges_enabled": True,
        "payouts_enabled": True,
        "business_profile": {"name": "Test Electric"},
        "settings": {"dashboard": {"display_name": "Test Electric"}},
    }
    values.update(overrides)
    return stripe.Account.construct_from(values, key="sk_test_fake")


def _make_account_link(**overrides) -> "stripe.AccountLink":
    """v15-faithful fixture for the AccountLink object."""
    values = {
        "url": "https://connect.stripe.com/setup/s/test",
        "expires_at": 1893456000,
    }
    values.update(overrides)
    return stripe.AccountLink.construct_from(values, key="sk_test_fake")


def _build_client(*, account=None, link=None, retrieve_side_effect=None):
    """Build a MagicMock client for the v1 StripeClient namespace.

    Use inside ``with patch(_FACTORY, return_value=client):``.
    """
    client = MagicMock()
    if retrieve_side_effect is not None:
        client.v1.accounts.retrieve.side_effect = retrieve_side_effect
    else:
        client.v1.accounts.retrieve.return_value = account
    if account is not None:
        client.v1.accounts.create.return_value = account
    if link is not None:
        client.v1.account_links.create.return_value = link
    return client


# ---------------------------------------------------------------------------
# Status endpoint tests
# ---------------------------------------------------------------------------


class TestStripeConnectStatus:
    """Tests for GET /api/v1/settings/billing/stripe-connect/status/test"""

    def test_status_not_connected(self, client, db_session, test_tenant):
        """Returns connected=false when tenant has no stripe_connect_account_id."""
        # Ensure no account is set
        tenant = _get_test_tenant(db_session, test_tenant)
        tenant.stripe_connect_account_id = None
        db_session.add(tenant)
        db_session.commit()

        resp = client.get(f"{BASE}/stripe-connect/status/test")
        assert resp.status_code == 200
        data = resp.json()
        assert data["connected"] is False
        assert data["account_id"] is None
        assert data["charges_enabled"] is False

    def test_status_connected(self, client, db_session, test_tenant):
        """Returns connected=true with fields when tenant has a stripe_connect_account_id."""
        # Set a fake account ID on the tenant
        fake_account_id = "acct_test_1234567890"
        tenant = _get_test_tenant(db_session, test_tenant)
        tenant.stripe_connect_account_id = fake_account_id
        db_session.add(tenant)
        db_session.commit()

        # Mock the Stripe API call with a REAL StripeObject
        mock_account = _make_connect_account(
            id=fake_account_id,
            business_profile={"name": "Mike's Electric LLC"},
        )
        client_mock = _build_client(account=mock_account)

        with patch(_FACTORY, return_value=client_mock):
            resp = client.get(f"{BASE}/stripe-connect/status/test")

        assert resp.status_code == 200
        data = resp.json()
        assert data["connected"] is True
        assert data["account_id"] == fake_account_id
        assert data["charges_enabled"] is True
        assert data["payouts_enabled"] is True


# ---------------------------------------------------------------------------
# Onboard endpoint tests
# ---------------------------------------------------------------------------


class TestStripeConnectOnboard:
    """Tests for POST /api/v1/settings/billing/stripe-connect/onboard/test"""

    def test_onboard_creates_account(self, client, db_session, test_tenant):
        """POST creates a new Stripe account and returns account_link_url."""
        # Ensure no account is set
        tenant = _get_test_tenant(db_session, test_tenant)
        tenant.stripe_connect_account_id = None
        db_session.add(tenant)
        db_session.commit()

        fake_account_id = "acct_new_testaccount"
        mock_account = _make_connect_account(id=fake_account_id)
        mock_link = _make_account_link(
            url="https://connect.stripe.com/setup/e/acct_test/abc123",
            expires_at=1721563200,
        )
        client_mock = _build_client(account=mock_account, link=mock_link)

        with patch(_FACTORY, return_value=client_mock):
            resp = client.post(f"{BASE}/stripe-connect/onboard/test")

        assert resp.status_code == 200
        data = resp.json()
        assert "account_link_url" in data
        assert (
            data["account_link_url"]
            == "https://connect.stripe.com/setup/e/acct_test/abc123"
        )
        assert data["expires_at"] == 1721563200

        # Verify tenant now has the account ID saved
        db_session.refresh(tenant)
        assert tenant.stripe_connect_account_id == fake_account_id

    def test_onboard_reuses_existing_account(self, client, db_session, test_tenant):
        """POST reuses existing account_id without calling Account.create."""
        existing_account_id = "acct_existing_test"
        tenant = _get_test_tenant(db_session, test_tenant)
        tenant.stripe_connect_account_id = existing_account_id
        db_session.add(tenant)
        db_session.commit()

        mock_link = _make_account_link(
            url="https://connect.stripe.com/setup/e/acct_existing/xyz789",
            expires_at=1721566800,
        )
        client_mock = _build_client(link=mock_link)

        with patch(_FACTORY, return_value=client_mock):
            resp = client.post(f"{BASE}/stripe-connect/onboard/test")

        assert resp.status_code == 200
        data = resp.json()
        assert (
            data["account_link_url"]
            == "https://connect.stripe.com/setup/e/acct_existing/xyz789"
        )


# ---------------------------------------------------------------------------
# Disconnect endpoint tests
# ---------------------------------------------------------------------------


class TestStripeConnectDisconnect:
    """Tests for DELETE /api/v1/settings/billing/stripe-connect/test"""

    def test_disconnect_clears_account_id(self, client, db_session, test_tenant):
        """DELETE clears stripe_connect_account_id on the tenant."""
        tenant = _get_test_tenant(db_session, test_tenant)
        tenant.stripe_connect_account_id = "acct_to_disconnect"
        db_session.add(tenant)
        db_session.commit()

        resp = client.delete(f"{BASE}/stripe-connect/test")
        assert resp.status_code == 200
        data = resp.json()
        assert data["disconnected"] is True
        assert "manual payment" in data["message"].lower()

        # Verify account ID is cleared
        db_session.refresh(tenant)
        assert tenant.stripe_connect_account_id is None

    def test_disconnect_already_null_is_idempotent(
        self, client, db_session, test_tenant
    ):
        """DELETE when stripe_connect_account_id is already NULL returns 200 (idempotent)."""
        tenant = _get_test_tenant(db_session, test_tenant)
        tenant.stripe_connect_account_id = None
        db_session.add(tenant)
        db_session.commit()

        resp = client.delete(f"{BASE}/stripe-connect/test")
        assert resp.status_code == 200
        data = resp.json()
        assert data["disconnected"] is True


# ---------------------------------------------------------------------------
# PLP-FIX-6: v15-faithful regression tests (anti-blindness)
# ---------------------------------------------------------------------------


class TestStatusV15Fidelity:
    """Anti-blindness tests pinning the v15 StripeObject access pattern.

    These tests use real ``construct_from`` StripeObjects (not plain dicts)
    so any regression to ``.get()`` on a StripeObject fails here, not in prod.
    """

    def test_happy_path_via_real_stripe_object(self, client, db_session, test_tenant):
        """Status happy path via a real StripeObject fixture."""
        fake_account_id = "acct_v15_happy"
        tenant = _get_test_tenant(db_session, test_tenant)
        tenant.stripe_connect_account_id = fake_account_id
        db_session.add(tenant)
        db_session.commit()

        mock_account = _make_connect_account(id=fake_account_id)
        client_mock = _build_client(account=mock_account)

        with patch(_FACTORY, return_value=client_mock):
            resp = client.get(f"{BASE}/stripe-connect/status/test")

        assert resp.status_code == 200
        data = resp.json()
        assert data["connected"] is True
        assert data["charges_enabled"] is True
        assert data["payouts_enabled"] is True
        assert data["account_name"] == "Test Electric"

    def test_absent_optional_nested_keys_degrade_gracefully(
        self, client, db_session, test_tenant
    ):
        """Missing business_profile + settings → 200, account_name None, no 502."""
        fake_account_id = "acct_v15_sparse"
        tenant = _get_test_tenant(db_session, test_tenant)
        tenant.stripe_connect_account_id = fake_account_id
        db_session.add(tenant)
        db_session.commit()

        # Build a StripeObject WITHOUT business_profile or settings keys
        mock_account = stripe.Account.construct_from(
            {
                "id": fake_account_id,
                "charges_enabled": False,
                "payouts_enabled": False,
            },
            key="sk_test_fake",
        )
        client_mock = _build_client(account=mock_account)

        with patch(_FACTORY, return_value=client_mock):
            resp = client.get(f"{BASE}/stripe-connect/status/test")

        assert resp.status_code == 200
        data = resp.json()
        assert data["connected"] is True
        assert data["account_name"] is None
        assert data["charges_enabled"] is False

    def test_unexpected_error_names_its_class(self, client, db_session, test_tenant):
        """A non-PermissionError exception → 502 with class name in detail."""
        fake_account_id = "acct_v15_err"
        tenant = _get_test_tenant(db_session, test_tenant)
        tenant.stripe_connect_account_id = fake_account_id
        db_session.add(tenant)
        db_session.commit()

        client_mock = _build_client(retrieve_side_effect=ValueError("boom"))

        with patch(_FACTORY, return_value=client_mock):
            resp = client.get(f"{BASE}/stripe-connect/status/test")

        assert resp.status_code == 502
        body = resp.json()
        # FastAPI wraps HTTPException detail as {"detail": <rfc7807 dict>}.
        # The inner "detail" key of the RFC 7807 dict holds the human-readable
        # string containing the exception class name.
        problem = body["detail"]
        assert "ValueError" in problem["detail"]
