"""
C-B10 — Recurring 10DLC carrier fee pass-through service.

Creates a recurring Stripe SubscriptionItem on the tenant's existing Charter
subscription for monthly carrier fee pass-through (campaign fee + phone number).
Uses inline price_data against prod_passthrough ("Carrier fees (pass-through)").
Amount = registration.quoted_monthly_cents (stored at provisioning time by C-B9).
proration_behavior="none" to avoid prorating the first charge.

Called by the Celery task after the 90-day prepaid window expires.
"""

import logging
import uuid

from sqlmodel import Session, select

from app.models.billing import Subscription
from app.models.sms import TenantMessagingRegistration
from core.datetime_utils import safe_now_utc

logger = logging.getLogger(__name__)


def create_recurring_carrier_item(
    db: Session,
    registration_id: uuid.UUID,
) -> str:
    """Creates a recurring Stripe SubscriptionItem for 10DLC carrier fees.

    Idempotency: if registration.stripe_recurring_item_id is non-null, skip.
    Returns the Stripe SubscriptionItem ID (si_...).

    Raises:
        ValueError: If registration not found, not in 'active' status,
            quoted_monthly_cents is None/zero, or no active subscription found.
        Exception: On Stripe API error.
    """
    # 1. Load registration
    registration = db.exec(
        select(TenantMessagingRegistration).where(
            TenantMessagingRegistration.id == registration_id
        )
    ).first()
    if not registration:
        raise ValueError(f"Registration {registration_id} not found")

    # 2. Idempotency guard
    if registration.stripe_recurring_item_id:
        logger.info(
            "Recurring item already exists for registration %s (si_id=%s), skipping",
            registration_id,
            registration.stripe_recurring_item_id,
        )
        return registration.stripe_recurring_item_id

    # 3. Validate status
    if registration.status != "active":
        raise ValueError(
            f"Registration {registration_id} not in 'active' status "
            f"(current: {registration.status})"
        )

    # 4. Validate quoted_monthly_cents
    if not registration.quoted_monthly_cents or registration.quoted_monthly_cents <= 0:
        logger.warning(
            "Registration %s has invalid quoted_monthly_cents=%s, skipping",
            registration_id,
            registration.quoted_monthly_cents,
        )
        raise ValueError("quoted_monthly_cents is null or zero")

    # 5. Find the tenant's active Stripe subscription
    sub_row = db.exec(
        select(Subscription).where(
            Subscription.tenant_id == registration.tenant_id,
            Subscription.is_active == True,
            Subscription.psp_provider == "stripe",
        )
    ).first()
    if not sub_row or not sub_row.psp_subscription_id:
        raise ValueError(
            f"No active Stripe subscription found for tenant {registration.tenant_id}"
        )

    # 6. Get prod_passthrough ID from stripe_ids config
    from core.stripe_config import get_stripe_ids

    stripe_ids = get_stripe_ids()
    prod_passthrough_id = stripe_ids["products"]["prod_passthrough"]

    # 7. Create the recurring SubscriptionItem
    from services.stripe_subscriptions import _get_stripe_client

    stripe = _get_stripe_client()

    sub_item = stripe.SubscriptionItem.create(
        subscription=sub_row.psp_subscription_id,
        price_data={
            "currency": "usd",
            "product": prod_passthrough_id,
            "recurring": {"interval": "month"},
            "unit_amount": registration.quoted_monthly_cents,  # already in cents
        },
        quantity=1,
        proration_behavior="none",
    )

    # 8. Store the SubscriptionItem ID + timestamp on the registration
    registration.stripe_recurring_item_id = sub_item.id
    registration.recurring_item_created_at = safe_now_utc()
    db.add(registration)
    db.commit()
    db.refresh(registration)

    logger.info(
        "Created recurring carrier item %s for registration %s (amount=%d cents/month)",
        sub_item.id,
        registration_id,
        registration.quoted_monthly_cents,
    )
    return sub_item.id
