"""
STRIPE-CONNECT-1 (A2) Tests: Tenant capability columns + notification types/templates.

Tests:
1. test_capability_columns_exist_and_nullable — both columns present, nullable
2. test_backfill_sets_true_for_connected_tenant — a tenant with
   stripe_connect_account_id gets true/true; a tenant without does not
3. test_notification_types_seeded — stripe_connect_disconnected +
   stripe_dispute_opened present (platform default, tenant_id NULL)
4. test_notification_templates_seeded — 6 templates (2 types x 3 channels)
   present with tenant_id NULL
5. test_public_get_not_connected — PublicInvoiceResponse returns
   card_payments_enabled=False, payment_unavailable_reason='not_connected'
   when tenant has no stripe_connect_account_id
6. test_public_get_charges_disabled — returns
   payment_unavailable_reason='charges_disabled' when account exists but
   charges_enabled is False
7. test_public_get_enabled — returns card_payments_enabled=True,
   payment_unavailable_reason=None when both flags true
8. test_status_write_through — GET /stripe-connect/status persists fresh
   flags onto the tenant (Stripe retrieve mocked)
"""

import uuid
from unittest.mock import MagicMock, patch

import pytest
import stripe
from sqlalchemy import text
from sqlmodel import Session, select

from app.models.core import Tenant
from app.models.system import NotificationTemplate, NotificationType

pytestmark = [
    pytest.mark.domain_invoicing_billing,
    pytest.mark.unit,
]

BASE = "/api/v1/settings/billing"
PUBLIC = "/api/v1/public"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_tenant(
    db: Session, *, has_connect: bool, charges=None, payouts=None
) -> Tenant:
    """Insert a fresh tenant with the given connect state. Returns it."""
    tenant = Tenant(
        id=uuid.uuid4(),
        name=f"[SC1] Tenant {uuid.uuid4()}",
        is_active=True,
        stripe_connect_account_id=(
            f"acct_test_{uuid.uuid4().hex[:12]}" if has_connect else None
        ),
        stripe_connect_charges_enabled=charges,
        stripe_connect_payouts_enabled=payouts,
    )
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    return tenant


# ---------------------------------------------------------------------------
# Column + backfill tests
# ---------------------------------------------------------------------------


class TestCapabilityColumns:
    """A2: column existence, nullability, and backfill behavior."""

    def test_capability_columns_exist_and_nullable(self, db_session):
        """Both columns exist on the tenant table and are nullable."""
        result = db_session.execute(
            text(
                """
                SELECT column_name, is_nullable
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'tenant'
                  AND column_name IN
                      ('stripe_connect_charges_enabled',
                       'stripe_connect_payouts_enabled')
                ORDER BY column_name
                """
            )
        ).fetchall()
        assert len(result) == 2
        names = {r[0] for r in result}
        assert names == {
            "stripe_connect_charges_enabled",
            "stripe_connect_payouts_enabled",
        }
        for r in result:
            assert r[1] == "YES"  # nullable

    def test_backfill_sets_true_for_connected_tenant(self, db_session):
        """A tenant with stripe_connect_account_id gets true/true via backfill.

        We simulate the backfill UPDATE (the migration ran it at upgrade time;
        here we re-apply the same value-scoped UPDATE to prove the logic).
        """
        connected = _make_tenant(
            db_session, has_connect=True, charges=None, payouts=None
        )
        unconnected = _make_tenant(
            db_session, has_connect=False, charges=None, payouts=None
        )

        # Re-apply the migration's backfill (value-scoped, idempotent)
        db_session.execute(
            text(
                """
                UPDATE tenant
                SET stripe_connect_charges_enabled = true,
                    stripe_connect_payouts_enabled = true,
                    updated_at = now()
                WHERE stripe_connect_account_id IS NOT NULL
                  AND stripe_connect_charges_enabled IS NULL
                """
            )
        )
        db_session.commit()

        db_session.refresh(connected)
        db_session.refresh(unconnected)
        assert connected.stripe_connect_charges_enabled is True
        assert connected.stripe_connect_payouts_enabled is True
        # Unconnected tenant stays NULL (not backfilled)
        assert unconnected.stripe_connect_charges_enabled is None
        assert unconnected.stripe_connect_payouts_enabled is None


# ---------------------------------------------------------------------------
# Notification type + template tests
# ---------------------------------------------------------------------------


class TestConnectNotifications:
    """A2: stripe_connect_disconnected + stripe_dispute_opened seeded."""

    def test_notification_types_seeded(self, db_session):
        """Both notification_type rows exist as platform defaults (tenant_id NULL)."""
        for code in ("stripe_connect_disconnected", "stripe_dispute_opened"):
            nt = db_session.exec(
                select(NotificationType).where(
                    NotificationType.code == code,
                    NotificationType.tenant_id == None,
                )
            ).first()
            assert nt is not None, f"notification_type '{code}' not seeded"
            assert nt.is_active is True
            assert nt.audience == "tenant"

    def test_notification_templates_seeded(self, db_session):
        """6 templates (2 types x email/in_app/push) present, tenant_id NULL."""
        for code in ("stripe_connect_disconnected", "stripe_dispute_opened"):
            for channel in ("email", "in_app", "push"):
                tpl = db_session.exec(
                    select(NotificationTemplate).where(
                        NotificationTemplate.notification_type_code == code,
                        NotificationTemplate.channel == channel,
                        NotificationTemplate.tenant_id == None,
                    )
                ).first()
                assert tpl is not None, (
                    f"notification_template {code}/{channel} not seeded"
                )
                assert tpl.is_active is True
                assert tpl.locale == "en"
                assert tpl.subject is not None
                assert tpl.body is not None


# ---------------------------------------------------------------------------
# Public GET payment-state tests (A6 — tested here per prompt grouping)
# ---------------------------------------------------------------------------


def _create_public_invoice_for_tenant(db: Session, tenant_id, customer_id, site_id):
    """Create a minimal invoice + public link for the public GET tests."""
    from app.models.billing import (
        Invoice,
        InvoicePublicLink,
        InvoiceStatus,
    )
    from services.public_link_signer import generate_signed_token

    inv_status = db.exec(
        select(InvoiceStatus)
        .where(InvoiceStatus.tenant_id == None)
        .where(InvoiceStatus.code == "issued")
    ).first()
    if not inv_status:
        pytest.skip("No 'issued' invoice status seeded")

    invoice = Invoice(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        invoice_number=f"INV-SC1-{uuid.uuid4().hex[:6].upper()}",
        customer_id=customer_id,
        site_id=site_id,
        status_id=inv_status.id,
        total_cents=10000,
        currency="USD",
        is_active=True,
    )
    db.add(invoice)
    db.flush()

    # No InvoiceLine — the GET handler returns an empty line_items list when
    # none exist; the payment-state fields are computed from the tenant, not
    # the lines. (invoice_line.source_type is NOT NULL and not relevant here.)

    link_id = uuid.uuid4()
    token, _expires = generate_signed_token(
        link_id=link_id,
        link_type="invoice",
        customer_id=customer_id,
    )
    link = InvoicePublicLink(
        id=link_id,
        tenant_id=tenant_id,
        invoice_id=invoice.id,
        token_hash="sc1-test-hash",
        status="active",
        is_active=True,
    )
    db.add(link)
    db.commit()
    return invoice, token


class TestPublicGetPaymentState:
    """A6: PublicInvoiceResponse card_payments_enabled + payment_unavailable_reason."""

    def test_public_get_not_connected(self, client, db_session, test_tenant):
        """No stripe_connect_account_id → not_connected."""
        from app.models.crm import Customer, Site

        tenant = db_session.exec(
            select(Tenant).where(Tenant.id == test_tenant.id)
        ).first()
        tenant.stripe_connect_account_id = None
        tenant.stripe_connect_charges_enabled = None
        tenant.stripe_connect_payouts_enabled = None
        db_session.add(tenant)
        db_session.commit()

        customer = Customer(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            display_name="SC1 Cust",
            is_active=True,
        )
        db_session.add(customer)
        db_session.flush()
        site = Site(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            customer_id=customer.id,
            site_name="SC1 Site",
            is_active=True,
        )
        db_session.add(site)
        db_session.commit()

        _, token = _create_public_invoice_for_tenant(
            db_session, test_tenant.id, customer.id, site.id
        )

        resp = client.get(f"{PUBLIC}/invoices/{token}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["card_payments_enabled"] is False
        assert data["payment_unavailable_reason"] == "not_connected"

    def test_public_get_charges_disabled(self, client, db_session, test_tenant):
        """Account exists but charges_enabled=False → charges_disabled."""
        from app.models.crm import Customer, Site

        tenant = db_session.exec(
            select(Tenant).where(Tenant.id == test_tenant.id)
        ).first()
        tenant.stripe_connect_account_id = "acct_test_disabled"
        tenant.stripe_connect_charges_enabled = False
        tenant.stripe_connect_payouts_enabled = True
        db_session.add(tenant)
        db_session.commit()

        customer = Customer(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            display_name="SC1 Cust 2",
            is_active=True,
        )
        db_session.add(customer)
        db_session.flush()
        site = Site(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            customer_id=customer.id,
            site_name="SC1 Site 2",
            is_active=True,
        )
        db_session.add(site)
        db_session.commit()

        _, token = _create_public_invoice_for_tenant(
            db_session, test_tenant.id, customer.id, site.id
        )

        resp = client.get(f"{PUBLIC}/invoices/{token}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["card_payments_enabled"] is False
        assert data["payment_unavailable_reason"] == "charges_disabled"

    def test_public_get_enabled(self, client, db_session, test_tenant):
        """Both flags true → card_payments_enabled=True, reason=None."""
        from app.models.crm import Customer, Site

        tenant = db_session.exec(
            select(Tenant).where(Tenant.id == test_tenant.id)
        ).first()
        tenant.stripe_connect_account_id = "acct_test_enabled"
        tenant.stripe_connect_charges_enabled = True
        tenant.stripe_connect_payouts_enabled = True
        db_session.add(tenant)
        db_session.commit()

        customer = Customer(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            display_name="SC1 Cust 3",
            is_active=True,
        )
        db_session.add(customer)
        db_session.flush()
        site = Site(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            customer_id=customer.id,
            site_name="SC1 Site 3",
            is_active=True,
        )
        db_session.add(site)
        db_session.commit()

        _, token = _create_public_invoice_for_tenant(
            db_session, test_tenant.id, customer.id, site.id
        )

        resp = client.get(f"{PUBLIC}/invoices/{token}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["card_payments_enabled"] is True
        assert data["payment_unavailable_reason"] is None


# ---------------------------------------------------------------------------
# /status write-through test (A6)
# ---------------------------------------------------------------------------


class TestStatusWriteThrough:
    """A6: GET /stripe-connect/status persists fresh flags onto the tenant."""

    def test_status_write_through_updates_flags(self, client, db_session, test_tenant):
        """After a successful Account.retrieve, the local flags are persisted."""
        tenant = db_session.exec(
            select(Tenant).where(Tenant.id == test_tenant.id)
        ).first()
        tenant.stripe_connect_account_id = "acct_test_wt"
        tenant.stripe_connect_charges_enabled = False
        tenant.stripe_connect_payouts_enabled = False
        db_session.add(tenant)
        db_session.commit()

        # PLP-FIX-6: real StripeObject (not a plain dict) — pins the v15
        # access pattern so a regression to .get() on a StripeObject fails
        # here, not in prod.
        mock_account = stripe.Account.construct_from(
            {
                "id": "acct_test_wt",
                "charges_enabled": True,
                "payouts_enabled": True,
                "business_profile": {"name": "Write-Through Co"},
                "settings": {},
            },
            key="sk_test_fake",
        )

        with patch("api.routes.stripe_connect._get_stripe_connect_client") as factory:
            client_mock = MagicMock()
            client_mock.v1.accounts.retrieve.return_value = mock_account
            factory.return_value = client_mock
            resp = client.get(f"{BASE}/stripe-connect/status/test")

        assert resp.status_code == 200
        data = resp.json()
        assert data["connected"] is True
        assert data["charges_enabled"] is True
        assert data["payouts_enabled"] is True

        # Verify the flags were persisted onto the tenant row
        db_session.expire_all()
        refreshed = db_session.exec(
            select(Tenant).where(Tenant.id == test_tenant.id)
        ).first()
        assert refreshed.stripe_connect_charges_enabled is True
        assert refreshed.stripe_connect_payouts_enabled is True
