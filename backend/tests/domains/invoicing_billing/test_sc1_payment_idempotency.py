"""
STRIPE-CONNECT-1 (A5) Tests: Payment intent idempotency hardening.

Tests the Stripe-side idempotency key change in create_payment_intent:
1. Same idempotency_key twice → same Stripe idempotency key (one PI)
2. Two different keys, same amount → two distinct Stripe keys (two PIs)
3. No idempotency_key → uuid4 fallback (no collision between bare calls)

The API-level 24h response cache is handled by the existing
``idempotency_middleware`` (core/idempotency.py) and is already covered by
the existing idempotency test suite — these tests focus on the Stripe-side
key uniqueness fix (the A5 delta).
"""

import uuid
from unittest.mock import MagicMock, patch

import pytest

pytestmark = [
    pytest.mark.domain_invoicing_billing,
    pytest.mark.unit,
]


class TestStripeIdempotencyKey:
    """A5: Stripe-side idempotency key includes the client key or uuid4."""

    def test_same_key_produces_same_stripe_key(self, db_session, test_tenant):
        """Same idempotency_key → same Stripe idempotency key (replay-safe)."""
        from services.stripe_payment_intents import create_payment_intent

        # We test the key construction by mocking stripe.PaymentIntent.create
        # and capturing the idempotency_key argument.
        mock_pi = MagicMock()
        mock_pi.id = "pi_test_same_key"
        mock_pi.client_secret = "pi_test_same_key_secret"

        captured_keys = []

        def capture_create(**kwargs):
            captured_keys.append(kwargs.get("idempotency_key"))
            return mock_pi

        # Set up a connected tenant + invoice
        from sqlmodel import select

        from app.models.billing import Invoice, InvoiceStatus
        from app.models.core import Tenant
        from app.models.crm import Customer, Site

        tenant = db_session.exec(
            select(Tenant).where(Tenant.id == test_tenant.id)
        ).first()
        tenant.stripe_connect_account_id = "acct_test_idem"
        db_session.add(tenant)
        db_session.commit()

        inv_status = db_session.exec(
            select(InvoiceStatus)
            .where(InvoiceStatus.tenant_id == None)
            .where(InvoiceStatus.code == "issued")
        ).first()
        if not inv_status:
            pytest.skip("No 'issued' invoice status seeded")

        customer = Customer(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            display_name="SC1 Idem Cust",
            is_active=True,
        )
        db_session.add(customer)
        db_session.flush()
        site = Site(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            customer_id=customer.id,
            site_name="SC1 Idem Site",
            is_active=True,
        )
        db_session.add(site)
        db_session.commit()

        invoice = Invoice(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            invoice_number=f"INV-SC1ID-{uuid.uuid4().hex[:6].upper()}",
            customer_id=customer.id,
            site_id=site.id,
            status_id=inv_status.id,
            total_cents=10000,
            currency="USD",
            is_active=True,
        )
        db_session.add(invoice)
        db_session.commit()
        db_session.refresh(invoice)

        # Patch STRIPE_SECRET_KEY so the real-Stripe path runs
        with (
            patch("core.config.settings.STRIPE_SECRET_KEY", "sk_test_fake"),
            patch("stripe.PaymentIntent.create", side_effect=capture_create),
        ):
            create_payment_intent(
                db=db_session,
                invoice_id=str(invoice.id),
                amount_cents=5000,
                customer_comment=None,
                tenant_id=str(test_tenant.id),
                idempotency_key="client-key-abc",
            )
            create_payment_intent(
                db=db_session,
                invoice_id=str(invoice.id),
                amount_cents=5000,
                customer_comment=None,
                tenant_id=str(test_tenant.id),
                idempotency_key="client-key-abc",
            )

        assert len(captured_keys) == 2
        assert captured_keys[0] == captured_keys[1]
        assert "client-key-abc" in captured_keys[0]

    def test_different_keys_produce_different_stripe_keys(
        self, db_session, test_tenant
    ):
        """Two different idempotency_keys, same amount → two distinct keys."""
        from services.stripe_payment_intents import create_payment_intent

        mock_pi = MagicMock()
        mock_pi.id = "pi_test_diff"
        mock_pi.client_secret = "pi_test_diff_secret"

        captured_keys = []

        def capture_create(**kwargs):
            captured_keys.append(kwargs.get("idempotency_key"))
            return mock_pi

        from sqlmodel import select

        from app.models.billing import Invoice, InvoiceStatus
        from app.models.core import Tenant
        from app.models.crm import Customer, Site

        tenant = db_session.exec(
            select(Tenant).where(Tenant.id == test_tenant.id)
        ).first()
        tenant.stripe_connect_account_id = "acct_test_idem2"
        db_session.add(tenant)
        db_session.commit()

        inv_status = db_session.exec(
            select(InvoiceStatus)
            .where(InvoiceStatus.tenant_id == None)
            .where(InvoiceStatus.code == "issued")
        ).first()
        if not inv_status:
            pytest.skip("No 'issued' invoice status seeded")

        customer = Customer(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            display_name="SC1 Idem Cust 2",
            is_active=True,
        )
        db_session.add(customer)
        db_session.flush()
        site = Site(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            customer_id=customer.id,
            site_name="SC1 Idem Site 2",
            is_active=True,
        )
        db_session.add(site)
        db_session.commit()

        invoice = Invoice(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            invoice_number=f"INV-SC1ID2-{uuid.uuid4().hex[:6].upper()}",
            customer_id=customer.id,
            site_id=site.id,
            status_id=inv_status.id,
            total_cents=10000,
            currency="USD",
            is_active=True,
        )
        db_session.add(invoice)
        db_session.commit()
        db_session.refresh(invoice)

        with (
            patch("core.config.settings.STRIPE_SECRET_KEY", "sk_test_fake"),
            patch("stripe.PaymentIntent.create", side_effect=capture_create),
        ):
            create_payment_intent(
                db=db_session,
                invoice_id=str(invoice.id),
                amount_cents=5000,
                customer_comment=None,
                tenant_id=str(test_tenant.id),
                idempotency_key="client-key-aaa",
            )
            create_payment_intent(
                db=db_session,
                invoice_id=str(invoice.id),
                amount_cents=5000,
                customer_comment=None,
                tenant_id=str(test_tenant.id),
                idempotency_key="client-key-bbb",
            )

        assert len(captured_keys) == 2
        assert captured_keys[0] != captured_keys[1]
        assert "client-key-aaa" in captured_keys[0]
        assert "client-key-bbb" in captured_keys[1]

    def test_no_key_uses_uuid_fallback(self, db_session, test_tenant):
        """No idempotency_key → uuid4 fallback (no collision between calls)."""
        from services.stripe_payment_intents import create_payment_intent

        mock_pi = MagicMock()
        mock_pi.id = "pi_test_nokey"
        mock_pi.client_secret = "pi_test_nokey_secret"

        captured_keys = []

        def capture_create(**kwargs):
            captured_keys.append(kwargs.get("idempotency_key"))
            return mock_pi

        from sqlmodel import select

        from app.models.billing import Invoice, InvoiceStatus
        from app.models.core import Tenant
        from app.models.crm import Customer, Site

        tenant = db_session.exec(
            select(Tenant).where(Tenant.id == test_tenant.id)
        ).first()
        tenant.stripe_connect_account_id = "acct_test_idem3"
        db_session.add(tenant)
        db_session.commit()

        inv_status = db_session.exec(
            select(InvoiceStatus)
            .where(InvoiceStatus.tenant_id == None)
            .where(InvoiceStatus.code == "issued")
        ).first()
        if not inv_status:
            pytest.skip("No 'issued' invoice status seeded")

        customer = Customer(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            display_name="SC1 Idem Cust 3",
            is_active=True,
        )
        db_session.add(customer)
        db_session.flush()
        site = Site(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            customer_id=customer.id,
            site_name="SC1 Idem Site 3",
            is_active=True,
        )
        db_session.add(site)
        db_session.commit()

        invoice = Invoice(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            invoice_number=f"INV-SC1ID3-{uuid.uuid4().hex[:6].upper()}",
            customer_id=customer.id,
            site_id=site.id,
            status_id=inv_status.id,
            total_cents=10000,
            currency="USD",
            is_active=True,
        )
        db_session.add(invoice)
        db_session.commit()
        db_session.refresh(invoice)

        with (
            patch("core.config.settings.STRIPE_SECRET_KEY", "sk_test_fake"),
            patch("stripe.PaymentIntent.create", side_effect=capture_create),
        ):
            create_payment_intent(
                db=db_session,
                invoice_id=str(invoice.id),
                amount_cents=5000,
                customer_comment=None,
                tenant_id=str(test_tenant.id),
                idempotency_key=None,
            )
            create_payment_intent(
                db=db_session,
                invoice_id=str(invoice.id),
                amount_cents=5000,
                customer_comment=None,
                tenant_id=str(test_tenant.id),
                idempotency_key=None,
            )

        assert len(captured_keys) == 2
        # Two different uuid4 fallbacks → two different keys
        assert captured_keys[0] != captured_keys[1]
        # Both should contain the invoice_id + amount prefix
        assert str(invoice.id) in captured_keys[0]
        assert "5000" in captured_keys[0]
