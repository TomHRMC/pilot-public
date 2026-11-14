"""
C-B9 — 10DLC Stripe Checkout Service.

Creates a Stripe Checkout Session for the one-time 10DLC setup charge.
Uses mode="payment", setup_future_usage="off_session", inline price_data
with the millicents-based quote total converted to Stripe's cents format.

On checkout.session.completed (handled by stripe_subscriptions.py):
  1. Attach PM as customer.invoice_settings.default_payment_method
  2. Transition registration to 'brand_submitted'
  3. Enqueue Celery task: provision_brand(registration_id)
"""

import logging
import uuid

from sqlmodel import Session, select

from app.models.core import Tenant
from app.models.sms import TenantMessagingRegistration
from services.messaging_provisioning import transition_status

logger = logging.getLogger(__name__)


def create_10dlc_checkout_session(
    db: Session,
    tenant_id: uuid.UUID,
    registration: TenantMessagingRegistration,
) -> str:
    """Creates a Stripe Checkout Session for the one-time 10DLC setup charge.

    Uses mode="payment", setup_future_usage="off_session", inline price_data.
    Stores stripe_checkout_id on the registration row.
    Transitions status to 'awaiting_payment'.
    Returns the checkout URL.

    Raises:
        ValueError: If quoted_setup_cents is None (quote not fetched).
        Exception: On Stripe API error.
    """
    if registration.quoted_setup_cents is None:
        raise ValueError(
            "Cannot create checkout session — quoted_setup_cents is null. "
            "Run provisioning first to fetch a quote."
        )

    # Get the tenant's Stripe customer ID
    tenant = db.exec(select(Tenant).where(Tenant.id == tenant_id)).first()
    if not tenant:
        raise ValueError(f"Tenant {tenant_id} not found.")

    stripe_customer_id = getattr(tenant, "stripe_customer_id", None)
    if not stripe_customer_id:
        raise ValueError(
            f"Tenant {tenant_id} has no stripe_customer_id. "
            "Create a Stripe customer first."
        )

    # Transition to awaiting_payment
    transition_status(db, registration, "awaiting_payment")

    # Create Stripe Checkout Session
    from services.stripe_subscriptions import _get_stripe_client

    stripe = _get_stripe_client()

    # Stripe uses cents (integer). Our quote is in millicents.
    # Convert: cents = millicents // 1000
    # But quoted_setup_cents is already in cents (stored on registration row).
    amount_cents = registration.quoted_setup_cents

    session = stripe.checkout.Session.create(
        mode="payment",
        customer=stripe_customer_id,
        setup_future_usage="off_session",
        line_items=[
            {
                "price_data": {
                    "currency": "usd",
                    "product_data": {
                        "name": "10DLC SMS Setup — Carrier Registration",
                        "description": (
                            "One-time carrier registration fee for A2P 10DLC "
                            "brand + campaign + phone number. Passed through at "
                            "cost — Pilot adds no markup."
                        ),
                    },
                    "unit_amount": amount_cents,
                },
                "quantity": 1,
            }
        ],
        metadata={
            "purpose": "a2p_10dlc_setup",
            "tenant_id": str(tenant_id),
            "registration_id": str(registration.id),
        },
        success_url="/settings/messaging?status=paid",
        cancel_url="/settings/messaging?status=cancelled",
    )

    # Store checkout session ID on registration
    registration.stripe_checkout_id = session.id
    if session.payment_intent:
        registration.stripe_payment_intent = session.payment_intent
    db.add(registration)
    db.commit()
    db.refresh(registration)

    checkout_url = session.url or ""
    logger.info(
        "Created 10DLC checkout session %s for tenant %s (amount=%d cents)",
        session.id,
        tenant_id,
        amount_cents,
    )

    return checkout_url
