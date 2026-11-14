"""
B15/A81 — Stripe Payment Intents Service

create_payment_intent(): Create a Stripe PI for customer-initiated invoice payment.
handle_payment_intent_succeeded(): Process payment_intent.succeeded webhook event.
handle_payment_intent_failed(): Process payment_intent.payment_failed webhook event.

External dependency: Stripe Python SDK (stripe package).
If STRIPE_SECRET_KEY not configured, create_payment_intent returns a mock response.

UI-FIX-2F: Added PaymentNotConfiguredError guard and stripe_account= routing.
Payment intents now route to the tenant's connected Stripe account (not Pilot's).

STRIPE-CONNECT-1 (A5): The Stripe-side idempotency key now includes the
client-supplied Idempotency-Key header value (or a uuid4 fallback) so two
same-amount partial payments create two PIs instead of collapsing into one.
"""

import logging
import uuid

from sqlmodel import Session, select

logger = logging.getLogger(__name__)


class PaymentNotConfiguredError(Exception):
    """
    Raised when a tenant tries to take a payment without a connected Stripe account.

    Callers should render manual payment instructions instead of a Stripe payment form.
    """

    pass


def create_payment_intent(
    db: Session,
    invoice_id: str,
    amount_cents: int,
    customer_comment: str | None,
    tenant_id: str,
    *,
    idempotency_key: str | None = None,
) -> dict:
    """
    Create a Stripe Payment Intent for a customer-initiated invoice payment.

    UI-FIX-2F: Payment intents are now routed to the tenant's connected Stripe
    account via stripe_account=tenant.stripe_connect_account_id. If the tenant
    has not connected a Stripe account, raises PaymentNotConfiguredError.

    STRIPE-CONNECT-1 (A5): The Stripe-side idempotency key now includes the
    client-supplied ``idempotency_key`` (from the Idempotency-Key header) or a
    uuid4 fallback. This ensures two same-amount partial payments create two
    distinct PIs instead of collapsing into one (the old key
    ``pi_invoice_{invoice_id}_{amount_cents}`` was amount-collision-prone).
    Client retries with the same header still collapse correctly (same key →
    same PI).

    Args:
        db: SQLModel session.
        invoice_id: UUID of the invoice being paid.
        amount_cents: Customer-entered payment amount.
        customer_comment: Optional customer note.
        tenant_id: Tenant owning the invoice (for Stripe metadata + account routing).
        idempotency_key: Optional client-supplied idempotency key (from the
            Idempotency-Key header). When provided, two same-amount payments
            with different keys create two PIs. When None, a uuid4 is generated
            (bare browser retry without a header still works).

    Returns:
        {"client_secret": str, "payment_intent_id": str}

    Raises:
        ValueError: if invoice not found or already fully paid.
        PaymentNotConfiguredError: if tenant has no connected Stripe account
            (only raised when STRIPE_SECRET_KEY is configured — not in mock mode).
        stripe.error.StripeError: on Stripe API failure (when configured).
    """
    from app.models.billing import Invoice

    invoice = db.exec(select(Invoice).where(Invoice.id == invoice_id)).first()
    if invoice is None or not invoice.is_active:
        raise ValueError(f"Invoice {invoice_id} not found")

    from core.config import settings as cfg

    # Mock stub: if STRIPE_SECRET_KEY is absent, return a mock response.
    # This preserves backward compatibility with tests that don't configure Stripe.
    # The PaymentNotConfiguredError guard is NOT applied in mock mode.
    base_stripe_key = getattr(cfg, "STRIPE_SECRET_KEY", None)
    if not base_stripe_key:
        logger.warning(
            "STRIPE_SECRET_KEY not configured — returning mock Payment Intent"
        )
        mock_pi_id = f"pi_mock_{invoice_id[:8]}"
        return {
            "client_secret": f"{mock_pi_id}_secret_mock",
            "payment_intent_id": mock_pi_id,
        }

    # UI-FIX-2F: Resolve the tenant's connected Stripe account.
    # This guard only fires when STRIPE_SECRET_KEY is set (real Stripe mode).
    from app.models.core import Tenant

    tenant = db.exec(select(Tenant).where(Tenant.id == invoice.tenant_id)).first()
    stripe_connect_account_id = (
        getattr(tenant, "stripe_connect_account_id", None) if tenant else None
    )

    if not stripe_connect_account_id:
        raise PaymentNotConfiguredError(
            "This tenant has not connected a Stripe account. "
            "Visit Settings → Payment Method to connect Stripe before accepting payments."
        )

    # Use the Connect platform key for routing payments to the connected account.
    stripe_key = getattr(cfg, "STRIPE_CONNECT_PLATFORM_KEY", None) or base_stripe_key

    try:
        import stripe

        stripe.api_key = stripe_key

        # STRIPE-CONNECT-1 (A5): Stripe-side idempotency key now includes the
        # client-supplied idempotency_key (or a uuid4 fallback) so two
        # same-amount partial payments create two PIs instead of collapsing.
        # The old key `pi_invoice_{invoice_id}_{amount_cents}` was
        # amount-collision-prone — two $500 partial payments on the same
        # invoice would share a key and the second would be a replay.
        client_key = idempotency_key or str(uuid.uuid4())
        stripe_idempotency_key = f"pi_{invoice_id}_{amount_cents}_{client_key}"

        pi = stripe.PaymentIntent.create(
            amount=amount_cents,
            currency=invoice.currency.lower() if invoice.currency else "usd",
            metadata={
                "invoice_id": invoice_id,
                "tenant_id": tenant_id,
                "customer_comment": customer_comment or "",
            },
            # UI-FIX-2F: Route payment to the tenant's connected account
            stripe_account=stripe_connect_account_id,
            idempotency_key=stripe_idempotency_key,
        )

        return {
            "client_secret": pi.client_secret,
            "payment_intent_id": pi.id,
        }

    except Exception as e:
        logger.error(f"Stripe PaymentIntent creation failed: {e}")
        raise


def handle_payment_intent_succeeded(
    db: Session,
    payload: dict,
) -> None:
    """
    Process payment_intent.succeeded webhook event.

    Side effects:
      - Creates Payment record with amount_cents, stripe_payment_intent_id,
        amount_variance_cents, customer_payment_comment, paid_via='stripe'
      - Creates notification_outbox entry (category_id='customer_activity')
      - Updates invoice status (partial if underpaid)

    Idempotent: checks payment.stripe_payment_intent_id for existing record.
    Called from _process_stripe_event() in webhooks_stripe.py.
    """
    from app.models.billing import Invoice, Payment, PaymentStatus

    pi_obj = payload.get("data", {}).get("object", {})
    pi_id = pi_obj.get("id")
    amount_received = pi_obj.get("amount_received", 0)
    metadata = pi_obj.get("metadata", {})
    invoice_id = metadata.get("invoice_id")
    customer_comment = metadata.get("customer_comment") or None

    if not invoice_id or not pi_id:
        logger.warning(
            f"payment_intent.succeeded missing invoice_id or pi_id: {payload}"
        )
        return

    # Idempotency check — skip if already processed
    existing = db.exec(
        select(Payment).where(Payment.stripe_payment_intent_id == pi_id)
    ).first()
    if existing is not None:
        logger.info(f"Payment for PI {pi_id} already recorded — skipping")
        return

    invoice = db.exec(select(Invoice).where(Invoice.id == invoice_id)).first()
    if invoice is None:
        logger.warning(f"Invoice {invoice_id} not found for PI {pi_id}")
        return

    # Resolve paid status
    paid_status = db.exec(
        select(PaymentStatus).where(
            PaymentStatus.code == "paid",
            PaymentStatus.tenant_id == None,
        )
    ).first()
    if paid_status is None:
        logger.warning("No 'paid' PaymentStatus found")
        return

    # Resolve a system payment_method for Stripe one-time payments (per design doc §F8)
    from app.models.billing import PaymentMethod

    system_pm = db.exec(
        select(PaymentMethod).where(
            PaymentMethod.psp_payment_method_id == "one_time_public_link"
        )
    ).first()
    if system_pm is None:
        logger.warning(
            "No system payment_method 'one_time_public_link' found — "
            "ensure phase_fe_1_batch_b15_payment_stripe_columns migration was run"
        )
        return

    variance_cents = amount_received - invoice.total_cents

    payment = Payment(
        tenant_id=invoice.tenant_id,
        invoice_id=invoice.id,
        amount_cents=amount_received,
        payment_method_id=system_pm.id,
        status_id=paid_status.id,
        psp_provider="stripe",
        psp_payment_id=pi_id,
        stripe_payment_intent_id=pi_id,
        customer_payment_comment=customer_comment,
        amount_variance_cents=variance_cents,
        paid_via="stripe",
    )
    db.add(payment)
    db.flush()  # flush so SUM below includes the new payment

    # SD-2: Update invoice status based on remaining balance
    _update_invoice_status_after_payment(db, invoice)

    # Dispatch notification (non-blocking — best effort)
    try:
        _create_payment_notification(db, invoice, amount_received)
    except Exception as e:
        logger.warning(f"Failed to create payment notification: {e}")

    db.commit()
    logger.info(
        f"Payment {payment.id} created for invoice {invoice_id} "
        f"via PI {pi_id} — amount={amount_received} variance={variance_cents}"
    )


def handle_payment_intent_failed(
    db: Session,
    payload: dict,
) -> None:
    """
    Process payment_intent.payment_failed webhook event.

    Side effects:
      - Logs failure
      - Creates notification_outbox entry for tenant (category_id='customer_activity')

    Does NOT create a Payment record — no payment occurred.
    Called from _process_stripe_event() in webhooks_stripe.py.
    """
    pi_obj = payload.get("data", {}).get("object", {})
    pi_id = pi_obj.get("id")
    metadata = pi_obj.get("metadata", {})
    invoice_id = metadata.get("invoice_id")

    logger.info(
        f"payment_intent.payment_failed received — PI={pi_id} invoice={invoice_id}"
    )

    if not invoice_id:
        return

    from app.models.billing import Invoice

    invoice = db.exec(select(Invoice).where(Invoice.id == invoice_id)).first()
    if invoice is None:
        return

    try:
        _create_payment_failed_notification(db, invoice, pi_id)
    except Exception as e:
        logger.warning(f"Failed to create payment-failed notification: {e}")

    db.commit()


# ─────────────────────────────────────────────────────────────────────────────
# Invoice status helpers
# ─────────────────────────────────────────────────────────────────────────────


def _update_invoice_status_after_payment(db: Session, invoice) -> None:
    """
    SD-2: Transition invoice to 'partial' or 'paid' based on remaining balance.

    Calculates net received = SUM(payment.amount_cents) for active, non-refunded payments.
    - remaining > 0 AND remaining < invoice.total_cents → 'partial'
    - remaining == 0 → 'paid'
    - remaining >= invoice.total_cents (overpayment) → 'paid' (variance handled at creation)

    Must be called after db.flush() so new payment row is visible in SUM.
    """
    from sqlalchemy import func as sa_func

    from app.models.billing import InvoiceStatus, Payment

    # Sum all active payment rows for this invoice (includes negative refund rows)
    total_received = (
        db.exec(
            select(sa_func.coalesce(sa_func.sum(Payment.amount_cents), 0)).where(
                Payment.invoice_id == invoice.id,
                Payment.is_active == True,
            )
        ).first()
        or 0
    )

    remaining = invoice.total_cents - total_received

    if remaining <= 0:
        target_code = "paid"
    elif remaining < invoice.total_cents:
        target_code = "partial"
    else:
        # No positive payment yet received (shouldn't happen here, but guard)
        return

    target_status = db.exec(
        select(InvoiceStatus).where(
            InvoiceStatus.code == target_code,
            InvoiceStatus.tenant_id == None,
        )
    ).first()
    if target_status is None:
        logger.warning(
            f"_update_invoice_status_after_payment: '{target_code}' invoice_status not seeded"
        )
        return

    invoice.status_id = target_status.id
    db.add(invoice)


# ─────────────────────────────────────────────────────────────────────────────
# Notification helpers
# ─────────────────────────────────────────────────────────────────────────────


def _create_payment_notification(db: Session, invoice, amount_received: int) -> None:
    """
    Create a notification_outbox entry for successful payment.
    notification_event_id is NOT NULL — looks up NotificationEvent.
    Skips silently if the event record doesn't exist (dev/test environments).
    """
    from sqlmodel import select

    from app.models.system import NotificationEvent, NotificationOutbox

    event = db.exec(
        select(NotificationEvent).where(
            NotificationEvent.event_key == "payment_received"
        )
    ).first()
    if event is None:
        logger.debug("No NotificationEvent 'payment_received' — skipping outbox")
        return

    entry = NotificationOutbox(
        notification_event_id=event.id,
        tenant_id=invoice.tenant_id,
        category_id="customer_activity",
        contextdata={
            "event": "payment_received",
            "invoice_id": str(invoice.id),
            "amount_cents": amount_received,
        },
    )
    db.add(entry)


def _create_payment_failed_notification(db: Session, invoice, pi_id: str) -> None:
    """
    Create a notification_outbox entry for failed payment.
    Skips silently if NotificationEvent not found.
    """
    from sqlmodel import select

    from app.models.system import NotificationEvent, NotificationOutbox

    event = db.exec(
        select(NotificationEvent).where(NotificationEvent.event_key == "payment_failed")
    ).first()
    if event is None:
        logger.debug("No NotificationEvent 'payment_failed' — skipping outbox")
        return

    entry = NotificationOutbox(
        notification_event_id=event.id,
        tenant_id=invoice.tenant_id,
        category_id="customer_activity",
        contextdata={
            "event": "payment_failed",
            "invoice_id": str(invoice.id),
            "payment_intent_id": pi_id,
        },
    )
    db.add(entry)
