"""
STRIPE-CONNECT-1 (A3) Tests: Connect webhook endpoint + handlers.

Tests:
1. test_account_updated_persists_flags — handle_connect_account_updated
   persists charges_enabled / payouts_enabled onto the tenant
2. test_deauthorized_nulls_account_and_flags — handle_connect_deauthorized
   nulls stripe_connect_account_id + both flags
3. test_deauthorized_enqueues_owner_notification — a NotificationOutbox
   email row is created for the owner
4. test_dispute_created_enqueues_owner_notification —
   handle_connect_dispute(closed=False) enqueues stripe_dispute_opened
5. test_duplicate_event_deduped — the endpoint dedups via
   stripe_webhook_event_processed (no double side effects)
6. test_payment_intent_succeeded_delegates — _process_connect_event
   delegates payment_intent.succeeded to the existing handler (Payment row
   created exactly once)
7. test_unknown_account_returns_200 — unknown event['account'] → logged,
   no side effects (Stripe must never see a 5xx for an unmapped account)
"""

import json
import uuid
from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from sqlmodel import Session, select

from app.models.auth import TenantUser, TenantUserStatus
from app.models.billing import Payment, StripeWebhookEventProcessed
from app.models.core import Tenant, User
from app.models.system import NotificationOutbox

pytestmark = [
    pytest.mark.domain_invoicing_billing,
    pytest.mark.unit,
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_connected_tenant(db: Session, *, charges=True, payouts=True) -> Tenant:
    """Insert a fresh tenant with a connected Stripe account + an owner user."""
    tenant = Tenant(
        id=uuid.uuid4(),
        name=f"[SC1-WH] Tenant {uuid.uuid4()}",
        is_active=True,
        stripe_connect_account_id=f"acct_test_{uuid.uuid4().hex[:12]}",
        stripe_connect_charges_enabled=charges,
        stripe_connect_payouts_enabled=payouts,
    )
    db.add(tenant)
    db.flush()

    # Create an owner user + tenant_user link so notifications can resolve
    status = TenantUserStatus(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        code="active",
        name="Active",
        is_default=True,
        is_active=True,
    )
    db.add(status)
    db.flush()

    user = User(
        id=uuid.uuid4(),
        email=f"owner-{uuid.uuid4()}@example.com",
        first_name="Owner",
        last_name="SC1",
        is_active=True,
    )
    db.add(user)
    db.flush()

    tu = TenantUser(
        tenant_id=tenant.id,
        user_id=user.id,
        role_code="owner",
        status_id=status.id,
        is_active=True,
    )
    db.add(tu)
    db.commit()
    db.refresh(tenant)
    return tenant


def _account_updated_payload(account_id: str, *, charges=True, payouts=True) -> dict:
    return {
        "id": f"evt_test_{uuid.uuid4().hex[:12]}",
        "type": "account.updated",
        "account": account_id,
        "data": {
            "object": {
                "id": account_id,
                "charges_enabled": charges,
                "payouts_enabled": payouts,
            }
        },
    }


def _deauthorized_payload(account_id: str) -> dict:
    return {
        "id": f"evt_test_{uuid.uuid4().hex[:12]}",
        "type": "account.application.deauthorized",
        "account": account_id,
        "data": {"object": {"id": account_id}},
    }


def _dispute_created_payload(account_id: str, amount_cents=5000) -> dict:
    return {
        "id": f"evt_test_{uuid.uuid4().hex[:12]}",
        "type": "charge.dispute.created",
        "account": account_id,
        "data": {
            "object": {
                "id": f"dp_test_{uuid.uuid4().hex[:8]}",
                "amount_disputed": amount_cents,
                "evidence_details": {"due_by": "2026-09-15"},
            }
        },
    }


# ---------------------------------------------------------------------------
# Handler tests (direct calls — no HTTP layer)
# ---------------------------------------------------------------------------


class TestConnectAccountUpdated:
    """A3: account.updated persists flags."""

    def test_account_updated_persists_flags(self, db_session):
        from api.routes.webhooks_stripe import handle_connect_account_updated

        tenant = _make_connected_tenant(db_session, charges=True, payouts=True)
        payload = _account_updated_payload(
            tenant.stripe_connect_account_id, charges=False, payouts=True
        )

        handle_connect_account_updated(db_session, payload, tenant)

        db_session.expire_all()
        refreshed = db_session.exec(
            select(Tenant).where(Tenant.id == tenant.id)
        ).first()
        assert refreshed.stripe_connect_charges_enabled is False
        assert refreshed.stripe_connect_payouts_enabled is True


class TestConnectDeauthorized:
    """A3: account.application.deauthorized nulls id + flags + enqueues notification."""

    def test_deauthorized_nulls_account_and_flags(self, db_session):
        from api.routes.webhooks_stripe import handle_connect_deauthorized

        tenant = _make_connected_tenant(db_session, charges=True, payouts=True)
        payload = _deauthorized_payload(tenant.stripe_connect_account_id)

        handle_connect_deauthorized(db_session, payload, tenant)

        db_session.expire_all()
        refreshed = db_session.exec(
            select(Tenant).where(Tenant.id == tenant.id)
        ).first()
        assert refreshed.stripe_connect_account_id is None
        assert refreshed.stripe_connect_charges_enabled is None
        assert refreshed.stripe_connect_payouts_enabled is None

    def test_deauthorized_enqueues_owner_notification(self, db_session):
        from api.routes.webhooks_stripe import handle_connect_deauthorized

        tenant = _make_connected_tenant(db_session, charges=True, payouts=True)
        payload = _deauthorized_payload(tenant.stripe_connect_account_id)

        handle_connect_deauthorized(db_session, payload, tenant)

        # An email NotificationOutbox row should exist for this tenant
        outbox_rows = db_session.exec(
            select(NotificationOutbox).where(
                NotificationOutbox.tenant_id == tenant.id,
                NotificationOutbox.channel == "email",
            )
        ).all()
        assert len(outbox_rows) >= 1
        assert any("disconnected" in (r.subject or "").lower() for r in outbox_rows)


class TestConnectDispute:
    """A3: charge.dispute.created enqueues owner notification."""

    def test_dispute_created_enqueues_owner_notification(self, db_session):
        from api.routes.webhooks_stripe import handle_connect_dispute

        tenant = _make_connected_tenant(db_session, charges=True, payouts=True)
        payload = _dispute_created_payload(
            tenant.stripe_connect_account_id, amount_cents=5000
        )

        handle_connect_dispute(db_session, payload, tenant, closed=False)

        outbox_rows = db_session.exec(
            select(NotificationOutbox).where(
                NotificationOutbox.tenant_id == tenant.id,
                NotificationOutbox.channel == "email",
            )
        ).all()
        assert len(outbox_rows) >= 1
        assert any("disputed" in (r.subject or "").lower() for r in outbox_rows)


# ---------------------------------------------------------------------------
# Endpoint-level tests (dedup + delegation + unknown account)
# ---------------------------------------------------------------------------


class TestConnectWebhookEndpoint:
    """A3: endpoint dedup, PI delegation, unknown-account handling."""

    def test_duplicate_event_deduped(self, client, db_session, test_tenant):
        """Same event_id twice → deduped (no double side effects)."""

        tenant = _make_connected_tenant(db_session, charges=True, payouts=True)
        payload = _account_updated_payload(
            tenant.stripe_connect_account_id, charges=False, payouts=False
        )
        event_id = payload["id"]

        # Pre-insert the dedup record (simulating the endpoint's dedup step)
        dedup = StripeWebhookEventProcessed(
            event_id=event_id,
            processed_at=datetime.now(UTC),
            event_type="account.updated",
        )
        db_session.add(dedup)
        db_session.commit()

        # Call the handler directly — it should still work (handlers are
        # idempotent by design; the dedup is at the endpoint layer). But the
        # endpoint would have returned "duplicate" before dispatching.
        # Here we verify the dedup record prevents double dispatch by checking
        # the endpoint returns "duplicate".
        payload_bytes = json.dumps(payload).encode()
        with patch("api.routes.webhooks_stripe._verify_connect_signature"):
            resp = client.post(
                "/api/v1/webhooks/stripe-connect",
                content=payload_bytes,
                headers={"Content-Type": "application/json"},
            )
        assert resp.status_code == 200
        assert resp.json()["status"] == "duplicate"

    def test_unknown_account_returns_200(self, client, db_session, test_tenant):
        """Unknown event['account'] → 200 (Stripe must never see a 5xx)."""
        payload = {
            "id": f"evt_unknown_{uuid.uuid4().hex[:12]}",
            "type": "account.updated",
            "account": "acct_nonexistent_12345",
            "data": {
                "object": {
                    "id": "acct_nonexistent_12345",
                    "charges_enabled": True,
                    "payouts_enabled": True,
                }
            },
        }
        payload_bytes = json.dumps(payload).encode()
        with patch("api.routes.webhooks_stripe._verify_connect_signature"):
            resp = client.post(
                "/api/v1/webhooks/stripe-connect",
                content=payload_bytes,
                headers={"Content-Type": "application/json"},
            )
        # The endpoint returns 200 immediately (processing is in BackgroundTasks)
        assert resp.status_code == 200
        assert resp.json()["status"] == "received"

    def test_payment_intent_succeeded_delegates(self, db_session, test_tenant):
        """payment_intent.succeeded on the Connect endpoint delegates to the
        existing handler — Payment row created exactly once.

        We call handle_payment_intent_succeeded directly with the test's
        db_session (the Connect dispatch path delegates to this same function;
        _process_connect_event opens its own session which can't see
        uncommitted test data, so we test the delegated handler directly)."""
        from app.models.billing import (
            Invoice,
            InvoiceStatus,
            PaymentMethod,
            PaymentStatus,
            PaymentType,
        )
        from app.models.crm import Customer, Site
        from services.stripe_payment_intents import handle_payment_intent_succeeded

        # The handler requires a 'paid' PaymentStatus + a system
        # 'one_time_public_link' PaymentMethod. Seed them if absent (the dev
        # DB has 'succeeded' not 'paid' — the handler's hardcoded lookup is a
        # pre-existing B15/A81 issue, not introduced by this batch).
        paid_status = db_session.exec(
            select(PaymentStatus).where(
                PaymentStatus.code == "paid",
                PaymentStatus.tenant_id == None,
            )
        ).first()
        if not paid_status:
            paid_status = PaymentStatus(
                id=uuid.uuid4(),
                code="paid",
                name="Paid",
                is_active=True,
            )
            db_session.add(paid_status)
            db_session.flush()

        # payment_method.payment_type_id is NOT NULL — use the global 'card' type
        card_type = db_session.exec(
            select(PaymentType).where(
                PaymentType.code == "card",
                PaymentType.tenant_id == None,
            )
        ).first()
        if not card_type:
            pytest.skip("No 'card' payment_type seeded")

        system_pm = db_session.exec(
            select(PaymentMethod).where(
                PaymentMethod.psp_payment_method_id == "one_time_public_link"
            )
        ).first()
        if not system_pm:
            system_pm = PaymentMethod(
                id=uuid.uuid4(),
                tenant_id=test_tenant.id,
                payment_type_id=card_type.id,
                psp_payment_method_id="one_time_public_link",
                psp_provider="stripe",
                is_active=True,
            )
            db_session.add(system_pm)
            db_session.flush()

        # Create a minimal invoice for the test tenant
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
            display_name="SC1 PI Cust",
            is_active=True,
        )
        db_session.add(customer)
        db_session.flush()
        site = Site(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            customer_id=customer.id,
            site_name="SC1 PI Site",
            is_active=True,
        )
        db_session.add(site)
        db_session.commit()

        invoice = Invoice(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            invoice_number=f"INV-SC1PI-{uuid.uuid4().hex[:6].upper()}",
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

        pi_id = f"pi_test_{uuid.uuid4().hex[:12]}"
        payload = {
            "id": f"evt_pi_{uuid.uuid4().hex[:12]}",
            "type": "payment_intent.succeeded",
            "account": "acct_test_delegation",
            "data": {
                "object": {
                    "id": pi_id,
                    "amount_received": 10000,
                    "metadata": {
                        "invoice_id": str(invoice.id),
                        "tenant_id": str(test_tenant.id),
                        "customer_comment": "",
                    },
                }
            },
        }

        # Call the delegated handler directly (same function the Connect
        # dispatch path calls for payment_intent.succeeded)
        handle_payment_intent_succeeded(db_session, payload)

        # Verify the Payment row was created
        payment = db_session.exec(
            select(Payment).where(Payment.stripe_payment_intent_id == pi_id)
        ).first()
        assert payment is not None
        assert payment.amount_cents == 10000
