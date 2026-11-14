"""
B14/A76 — Stripe Subscriptions API integration.
Used by: tenant_subscription.py routes (A76), webhooks_stripe.py webhook handler (A76).

Requires in core.config.settings:
    STRIPE_SECRET_KEY      — Stripe secret API key (sk_live_... or sk_test_...)
    STRIPE_WEBHOOK_SECRET  — Stripe webhook signing secret (whsec_...)
    STRIPE_BASE_URL        — Override for stripe-mock in tests (default: https://api.stripe.com)
"""

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import or_
from sqlmodel import Session, select

logger = logging.getLogger(__name__)


def _get_stripe_client():
    """Return configured Stripe client. Lazy import to allow test mocking."""
    import stripe

    from core.config import settings

    stripe.api_key = settings.STRIPE_SECRET_KEY
    if (
        hasattr(settings, "STRIPE_BASE_URL")
        and settings.STRIPE_BASE_URL != "https://api.stripe.com"
    ):
        stripe.api_base = settings.STRIPE_BASE_URL
    return stripe


def create_stripe_customer(db: Session, tenant_id: UUID, billing_email: str) -> str:
    """
    Create a Stripe Customer record for a tenant on first paid conversion.
    Stores stripe_customer_id on tenant row.

    Returns:
        str: Stripe Customer ID (cus_...)
    """
    from app.models.core import Tenant

    stripe = _get_stripe_client()

    tenant = db.exec(select(Tenant).where(Tenant.id == tenant_id)).first()
    if not tenant:
        raise ValueError(f"Tenant {tenant_id} not found")

    # Create Stripe customer
    customer = stripe.Customer.create(
        email=billing_email,
        metadata={"tenant_id": str(tenant_id)},
    )

    # Store on tenant
    tenant.stripe_customer_id = customer.id
    db.add(tenant)
    db.commit()

    logger.info(f"Stripe Customer created for tenant {tenant_id}: {customer.id}")
    return customer.id


def create_stripe_subscription(
    db: Session,
    tenant_id: UUID,
    stripe_customer_id: str,
    stripe_price_id: str,
    stripe_payment_method_id: str,
) -> str:
    """
    Create a Stripe Subscription for a tenant.
    Does NOT update tenant tier — caller must wait for webhook confirmation.

    Returns:
        str: Stripe Subscription ID (sub_...)
    """
    stripe = _get_stripe_client()

    # Attach payment method to customer first
    stripe.PaymentMethod.attach(
        stripe_payment_method_id,
        customer=stripe_customer_id,
    )

    # Set as default payment method
    stripe.Customer.modify(
        stripe_customer_id,
        invoice_settings={"default_payment_method": stripe_payment_method_id},
    )

    # Create subscription
    subscription = stripe.Subscription.create(
        customer=stripe_customer_id,
        items=[{"price": stripe_price_id}],
        metadata={"tenant_id": str(tenant_id)},
    )

    logger.info(
        f"Stripe Subscription created for tenant {tenant_id}: {subscription.id} "
        f"(status: {subscription.status})"
    )
    return subscription.id


def handle_subscription_created(db: Session, stripe_event: dict) -> None:
    """
    Process customer.subscription.created webhook event.
    Updates tenant.current_subscription_tier_id based on Stripe price_id lookup.
    Creates/upserts subscription table row for FK targets (UsageLedger).
    Clears trial_ends_at if converting from trial.
    """
    import uuid
    from datetime import UTC, datetime

    from app.models.billing import Subscription
    from app.models.core import Tenant
    from app.models.subscription import SubscriptionTier

    subscription = stripe_event.get("data", {}).get("object", {})
    stripe_customer_id = subscription.get("customer")
    stripe_subscription_id = subscription.get("id")
    payload_status = subscription.get("status")

    if not stripe_customer_id or not stripe_subscription_id:
        logger.warning(
            "handle_subscription_created: missing customer or subscription id"
        )
        return

    # Find tenant by stripe_customer_id
    tenant = db.exec(
        select(Tenant).where(Tenant.stripe_customer_id == stripe_customer_id)
    ).first()

    if not tenant:
        logger.warning(f"No tenant found for Stripe customer {stripe_customer_id}")
        return

    # Get price_id from subscription items
    items = subscription.get("items", {}).get("data", [])
    if not items:
        return

    price_id = items[0].get("price", {}).get("id")
    if not price_id:
        return

    # Look up tier by either monthly or annual price ID (STRIPE-B1)
    tier = db.exec(
        select(SubscriptionTier).where(
            or_(
                SubscriptionTier.stripe_price_id_monthly == price_id,
                SubscriptionTier.stripe_price_id_annual == price_id,
            )
        )
    ).first()

    if not tier:
        # PLP-STRIPE-CHARTER-ROW-1: the Charter tier has NULL price columns in
        # prod (it bills via stripe_ids.*.json), so the price-ID lookup misses.
        # Fall back to the subscription metadata so the webhook path is
        # self-healing for Charter subscriptions created outside the signup
        # helper. Every non-Charter path is unchanged.
        tier_code = subscription.get("metadata", {}).get("tier_code")
        if tier_code == "charter":
            logger.info(
                "handle_subscription_created: price %s matched no tier; "
                "metadata.tier_code='charter' — using Charter fallback",
                price_id,
            )
            # Resolve free_period_ends_at from the tenant row (source of truth,
            # set by the signup wizard step4_tier) or fall back to the Stripe
            # trial_end timestamp in the payload.
            free_period_ends_at = tenant.free_period_ends_at
            if not free_period_ends_at:
                trial_end_ts = subscription.get("trial_end")
                if trial_end_ts:
                    free_period_ends_at = datetime.fromtimestamp(trial_end_ts, tz=UTC)
            if not free_period_ends_at:
                logger.warning(
                    "handle_subscription_created: Charter fallback — tenant %s "
                    "has no free_period_ends_at and the payload has no trial_end; "
                    "cannot write local subscription row",
                    tenant.id,
                )
                return
            # D5 — Out-of-order guard: Stripe does not guarantee webhook
            # ordering. If the local row is already 'active' and this payload
            # says 'trialing' (stale/late event), skip — never demote
            # active→trialing.
            from app.models.billing import SubscriptionStatus

            existing_sub = db.exec(
                select(Subscription).where(
                    Subscription.psp_subscription_id == stripe_subscription_id
                )
            ).first()
            if existing_sub:
                existing_status = db.exec(
                    select(SubscriptionStatus).where(
                        SubscriptionStatus.id == existing_sub.status_id
                    )
                ).first()
                if (
                    existing_status
                    and existing_status.code == "active"
                    and payload_status == "trialing"
                ):
                    logger.info(
                        "handle_subscription_created: stale event for sub %s "
                        "— local row is active, payload is trialing; "
                        "skipping (no demotion)",
                        stripe_subscription_id,
                    )
                    return

            _write_local_charter_subscription_row(
                db,
                tenant_id=tenant.id,
                stripe_customer_id=stripe_customer_id,
                stripe_subscription_id=stripe_subscription_id,
                free_period_ends_at=free_period_ends_at,
            )

            # D4 — On auto-conversion (payload status='active'), flip the
            # local row trialing→active and ensure metered overage items
            # are attached. customer.subscription.resumed only fires for
            # paused subs; the trial→active auto-conversion path was missed.
            if payload_status == "active":
                sub_row = db.exec(
                    select(Subscription).where(
                        Subscription.psp_subscription_id == stripe_subscription_id
                    )
                ).first()
                if sub_row:
                    active_status = db.exec(
                        select(SubscriptionStatus)
                        .where(SubscriptionStatus.code == "active")
                        .where(SubscriptionStatus.is_billing_active == True)
                    ).first()
                    if active_status:
                        sub_row.status_id = active_status.id
                        db.add(sub_row)
                        db.commit()

                # D6 — Metered-step failure is logged, never raised.
                try:
                    stripe = _get_stripe_client()
                    _add_metered_overage_items(stripe, stripe_subscription_id)
                except Exception:
                    logger.error(
                        "handle_subscription_created: failed to add metered "
                        "overage items for tenant %s (sub %s) — self-heals on "
                        "next subscription.updated / resume / upgrade",
                        tenant.id,
                        stripe_subscription_id,
                        exc_info=True,
                    )

            return
        logger.warning(f"No subscription tier found for Stripe price {price_id}")
        return

    # Verify tier has product_plan_code
    if not tier.product_plan_code:
        logger.warning(f"SubscriptionTier {tier.tier_id} has no product_plan_code set")
        return

    # Update tenant tier and clear trial_ends_at (conversion complete)
    tenant.current_subscription_tier_id = tier.tier_id
    tenant.trial_ends_at = None  # Trial ended on conversion
    db.add(tenant)
    db.commit()

    # Resolve subscription_status.id where code='active'
    from app.models.billing import SubscriptionStatus

    active_status = db.exec(
        select(SubscriptionStatus)
        .where(SubscriptionStatus.code == "active")
        .where(SubscriptionStatus.is_billing_active == True)
    ).first()

    if not active_status:
        logger.warning("No active subscription status found")
        return

    # Extract Stripe subscription fields
    billing_cycle_anchor = subscription.get("billing_cycle_anchor")
    current_period_end = subscription.get("current_period_end")

    # Derive billing interval from Stripe subscription item price metadata
    # Stripe returns "month" or "year" in price.recurring.interval
    billing_interval_str = "monthly"  # default
    items_data = subscription.get("items", {}).get("data", [])
    if items_data:
        stripe_interval = (
            items_data[0].get("price", {}).get("recurring", {}).get("interval")
        )
        if stripe_interval == "year":
            billing_interval_str = "annual"

    # Create or upsert subscription row
    sub_row = Subscription(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        product_plan_code=tier.product_plan_code,
        status_id=active_status.id,
        quantity_seats=1,
        billing_anchor=datetime.fromtimestamp(billing_cycle_anchor, tz=UTC).date()
        if billing_cycle_anchor
        else None,
        started_at=datetime.now(UTC),
        psp_provider="stripe",
        psp_subscription_id=stripe_subscription_id,
        psp_customer_id=stripe_customer_id,
        billing_interval=billing_interval_str,
        renews_at=datetime.fromtimestamp(current_period_end, tz=UTC)
        if current_period_end
        else None,
        is_active=True,
    )

    # Upsert: ON CONFLICT (psp_subscription_id) DO UPDATE
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    stmt = pg_insert(Subscription).values(
        id=sub_row.id,
        tenant_id=sub_row.tenant_id,
        product_plan_code=sub_row.product_plan_code,
        status_id=sub_row.status_id,
        quantity_seats=sub_row.quantity_seats,
        billing_anchor=sub_row.billing_anchor,
        started_at=sub_row.started_at,
        psp_provider=sub_row.psp_provider,
        psp_subscription_id=sub_row.psp_subscription_id,
        psp_customer_id=sub_row.psp_customer_id,
        billing_interval=sub_row.billing_interval,
        renews_at=sub_row.renews_at,
        is_active=sub_row.is_active,
    )

    stmt = stmt.on_conflict_do_update(
        index_elements=["psp_subscription_id"],
        set_={
            "status_id": active_status.id,
            "renews_at": sub_row.renews_at,
            "is_active": True,
        },
    )

    db.exec(stmt)
    db.commit()

    logger.info(
        f"Tenant {tenant.id} tier updated to {tier.tier_name} "
        f"and subscription row created/updated (sub_id: {stripe_subscription_id})"
    )

    # D3/D6 — Ensure metered overage items on active subscriptions. The GA
    # signup payment path doesn't exist yet, but subscription.updated fires
    # on every plan change/resume, and upgrade_charter_to_teams() assumes
    # metered items exist for Teams. Lazy client — only acquired when
    # status == "active".
    if payload_status == "active":
        try:
            stripe = _get_stripe_client()
            _add_metered_overage_items(stripe, stripe_subscription_id)
        except Exception:
            logger.error(
                "handle_subscription_created: failed to add metered overage "
                "items for tenant %s (sub %s) — self-heals on next "
                "subscription.updated / resume / upgrade",
                tenant.id,
                stripe_subscription_id,
                exc_info=True,
            )


def create_charter_subscription_schedule(
    db: Session,
    tenant_id: UUID,
    stripe_customer_id: str,
) -> str | None:
    """
    Create a Stripe Subscription Schedule for a Charter cohort tenant.
    Phase 1: $0/mo for 6 months (free cohort period).
    Phase 2: starter monthly price ($49/mo) starting at month 7, ongoing.

    Returns:
        str | None: Stripe schedule ID (sub_sched_...) or None if creation failed.

    IMPORTANT: This is NON-BLOCKING. If Stripe is unavailable or raises an error,
    logs the error and returns None. Caller must handle None gracefully.
    The Charter tenant is still created; schedule can be manually created by Tom later.
    """
    from app.models.billing import Subscription
    from app.models.subscription import SubscriptionTier

    stripe = _get_stripe_client()

    # Get the starter tier monthly price for Phase 2
    starter_tier = db.exec(
        select(SubscriptionTier).where(SubscriptionTier.tier_name == "starter")
    ).first()

    if not starter_tier or not starter_tier.stripe_price_id_monthly:
        logger.warning(
            "create_charter_subscription_schedule: starter tier or stripe_price_id_monthly "
            "not configured — skipping schedule creation. Run SD-3 seed + create Stripe monthly prices."
        )
        return None

    try:
        schedule = stripe.SubscriptionSchedule.create(
            customer=stripe_customer_id,
            start_date="now",
            end_behavior="release",
            phases=[
                {
                    "items": [],  # Phase 1: no charge
                    "iterations": 6,  # 6 monthly billing periods
                    "metadata": {"phase": "charter_free_period"},
                },
                {
                    "items": [
                        {"price": starter_tier.stripe_price_id_monthly, "quantity": 1}
                    ],
                    "metadata": {"phase": "charter_paid_period"},
                },
            ],
            metadata={"tenant_id": str(tenant_id), "schedule_type": "charter_cohort"},
        )

        # Store schedule ID on the subscription row
        sub_row = db.exec(
            select(Subscription)
            .where(Subscription.tenant_id == tenant_id)
            .where(Subscription.is_active == True)
        ).first()

        if sub_row:
            sub_row.stripe_schedule_id = schedule.id
            db.add(sub_row)
            db.commit()

        logger.info(
            f"Charter subscription schedule created for tenant {tenant_id}: "
            f"{schedule.id} — Phase 2 billing starts at month 7."
        )
        return schedule.id

    except Exception as e:
        logger.error(
            f"create_charter_subscription_schedule: Stripe error for tenant {tenant_id}: {e}. "
            "Charter tenant created successfully; schedule must be created manually."
        )
        return None


def handle_invoice_payment_failed(db: Session, stripe_event: dict) -> None:
    """
    Process invoice.payment_failed webhook event.
    After Stripe exhausts retries, transitions tenant to payment_failed paywall state
    and dispatches billing notification.
    """
    from app.models.core import Tenant

    invoice = stripe_event.get("data", {}).get("object", {})
    stripe_customer_id = invoice.get("customer")
    attempt_count = invoice.get("attempt_count", 0)

    if not stripe_customer_id:
        return

    tenant = db.exec(
        select(Tenant).where(Tenant.stripe_customer_id == stripe_customer_id)
    ).first()

    if not tenant:
        logger.warning(f"No tenant found for Stripe customer {stripe_customer_id}")
        return

    # Log payment failure — paywall enforcement handled at API layer
    logger.warning(
        f"Payment failed for tenant {tenant.id} "
        f"(attempt {attempt_count}, Stripe customer {stripe_customer_id})"
    )
    # PLATFORM-SMS-B1: Enqueue Pathway C payment-failed SMS (campaign Sample 2)
    # to verified, opted-in owners. Lazy import matches the existing task-dispatch
    # pattern in this codebase (e.g. free_period_notifications in this file).
    from tasks.sms_platform_notifications import send_platform_account_notification_sms

    send_platform_account_notification_sms.delay(
        tenant_id=str(tenant.id), type_code="platform_payment_failed"
    )


def handle_subscription_schedule_updated(db: Session, stripe_event: dict) -> None:
    """
    Process customer.subscription.schedule.updated webhook.
    Fires when a Subscription Schedule phase transitions.
    For Charter tenants: Phase 1 → Phase 2 at month 7 activates $49/mo billing.
    """
    from datetime import UTC, datetime

    from app.models.billing import Subscription
    from app.models.core import Tenant
    from app.models.subscription import SubscriptionTier

    schedule = stripe_event.get("data", {}).get("object", {})
    schedule_id = schedule.get("id")
    stripe_customer_id = schedule.get("customer")
    current_phase = schedule.get("current_phase", {})
    schedule_metadata = schedule.get("metadata", {})

    # Only process charter_cohort schedules
    if schedule_metadata.get("schedule_type") != "charter_cohort":
        logger.info(
            f"handle_subscription_schedule_updated: ignoring non-charter schedule {schedule_id}"
        )
        return

    # Find tenant by stripe_customer_id
    tenant = db.exec(
        select(Tenant).where(Tenant.stripe_customer_id == stripe_customer_id)
    ).first()
    if not tenant:
        logger.warning(
            f"handle_subscription_schedule_updated: no tenant for Stripe customer {stripe_customer_id}"
        )
        return

    # Determine which phase is now active
    phases = schedule.get("phases", [])
    current_phase_index = None
    for i, phase in enumerate(phases):
        if phase.get("start_date") == current_phase.get("start_date"):
            current_phase_index = i
            break

    # Only act on Phase 2 activation (index 1)
    if current_phase_index != 1:
        logger.info(
            f"Charter schedule {schedule_id}: phase {current_phase_index} event — "
            "no tier change needed"
        )
        return

    # Phase 2 activation: move tenant to starter tier
    starter_tier = db.exec(
        select(SubscriptionTier).where(SubscriptionTier.tier_name == "starter")
    ).first()
    if not starter_tier:
        logger.error(
            "handle_subscription_schedule_updated: starter tier not found — cannot transition"
        )
        return

    tenant.current_subscription_tier_id = starter_tier.tier_id
    tenant.trial_ends_at = None
    db.add(tenant)

    # Update subscription row
    sub_row = db.exec(
        select(Subscription)
        .where(Subscription.tenant_id == tenant.id)
        .where(Subscription.is_active == True)
    ).first()
    if sub_row:
        sub_row.billing_interval = "monthly"
        phase_end = current_phase.get("end_date")
        if phase_end:
            sub_row.renews_at = datetime.fromtimestamp(phase_end, tz=UTC)
        db.add(sub_row)

    db.commit()
    logger.info(
        f"Charter tenant {tenant.id} transitioned to starter tier at month 7. "
        f"Schedule: {schedule_id}"
    )


def _handle_refund_event(db: Session, event_data: dict) -> None:
    """
    Create a negative-amount payment row for a Stripe refund.
    Fires on charge.refunded and refund.created events.
    The original succeeded payment row is NOT modified.

    SD-2: Refund model — negative payment row (not columns on original row).
    """
    from datetime import UTC, datetime

    from app.models.billing import Payment, PaymentStatus

    charge = event_data.get("object", {})
    amount_refunded = charge.get("amount_refunded", 0)
    stripe_pi_id = charge.get("payment_intent")

    if not stripe_pi_id or not amount_refunded:
        return

    # Find the original payment row
    original = db.exec(
        select(Payment).where(Payment.stripe_payment_intent_id == stripe_pi_id)
    ).first()
    if not original:
        logger.warning(f"_handle_refund_event: no payment found for pi={stripe_pi_id}")
        return

    # Look up 'refunded' status (global platform row — tenant_id IS NULL)
    refunded_status = db.exec(
        select(PaymentStatus).where(
            PaymentStatus.code == "refunded",
            PaymentStatus.tenant_id == None,
        )
    ).first()
    if not refunded_status:
        logger.error(
            "_handle_refund_event: 'refunded' payment_status not seeded — run seed_core.py"
        )
        return

    # Create the negative-amount refund row
    refund_row = Payment(
        tenant_id=original.tenant_id,
        invoice_id=original.invoice_id,
        amount_cents=-amount_refunded,
        payment_method_id=original.payment_method_id,
        status_id=refunded_status.id,
        paid_at=datetime.now(UTC),
        psp_provider=original.psp_provider,
        psp_payment_id=charge.get("id"),  # Stripe charge ID
        paid_via="stripe",
        is_active=True,
    )
    db.add(refund_row)
    db.commit()
    logger.info(
        f"_handle_refund_event: created refund row for pi={stripe_pi_id} "
        f"amount={-amount_refunded} cents"
    )


# =====================================================================
# C-B4 — Charter subscription lifecycle, usage reporting, webhooks
# =====================================================================


class ResumeFailedError(Exception):
    """Subscription remained paused after resume — payment method may have failed."""

    pass


def _add_metered_overage_items(stripe, subscription_id: str) -> None:
    """Add voice_overage + sms_overage metered items to a subscription.

    Called by resume_subscription() after a Charter subscription is resumed
    with a payment method on file. Stripe does not allow metered usage items
    on subscriptions configured to pause at trial end, so they are added
    here after the subscription transitions to active.

    Also clears trial_settings.end_behavior.missing_payment_method since
    the subscription is no longer in trial — Stripe requires this before
    metered items can be added.

    Idempotent: checks existing items and only adds those that are missing.
    """
    from core.stripe_config import get_stripe_ids

    ids = get_stripe_ids()
    voice_price_id = ids["prices"]["price_voice_overage"]
    sms_price_id = ids["prices"]["price_sms_overage"]

    # Retrieve current subscription items to check what's already present
    sub = stripe.Subscription.retrieve(subscription_id)
    existing_price_ids = {item["price"]["id"] for item in sub["items"]["data"]}

    new_items = []
    if voice_price_id not in existing_price_ids:
        new_items.append({"price": voice_price_id})
    if sms_price_id not in existing_price_ids:
        new_items.append({"price": sms_price_id})

    if new_items:
        # Clear trial_settings — Stripe won't allow metered items while
        # the pause-at-trial-end config is present, even if the subscription
        # is already active.
        modify_kwargs: dict = {"items": new_items}
        trial_settings = getattr(sub, "trial_settings", None)
        if trial_settings:
            modify_kwargs["trial_settings"] = {
                "end_behavior": {"missing_payment_method": "cancel"}
            }
        stripe.Subscription.modify(
            subscription_id,
            **modify_kwargs,
        )
        logger.info(
            "Added %d metered overage item(s) to subscription %s",
            len(new_items),
            subscription_id,
        )


def _write_local_charter_subscription_row(
    db: Session,
    *,
    tenant_id: UUID,
    stripe_customer_id: str,
    stripe_subscription_id: str,
    free_period_ends_at: datetime,
) -> None:
    """Upsert the local ``subscription`` row for a Charter tenant.

    Resolves ``product_plan_code`` from the Charter ``subscription_tier`` and
    ``status_id`` via ``subscription_status WHERE code='trialing'`` (never
    hardcodes the UUID — it differs per environment). Writes a row with
    ``psp_provider='stripe'``, ``billing_interval='monthly'``,
    ``trial_ends_at=renews_at=free_period_ends_at``, ``is_active=True``,
    ``stripe_schedule_id=None``.

    Idempotent: ``ON CONFLICT (psp_subscription_id) DO UPDATE``. Commits
    internally (consistent with ``create_charter_subscription()``).

    Never raises — if the Charter tier or trialing status can't be resolved,
    logs the error and returns so the caller (the signup wizard) is never
    crashed by a local-write failure.
    """
    import uuid as _uuid

    from sqlalchemy.dialects.postgresql import insert as pg_insert

    from app.models.billing import Subscription, SubscriptionStatus
    from app.models.subscription import SubscriptionTier

    # 1. Load the Charter tier → product_plan_code
    charter_tier = db.exec(
        select(SubscriptionTier).where(SubscriptionTier.tier_name == "charter")
    ).first()
    if not charter_tier or not charter_tier.product_plan_code:
        logger.error(
            "_write_local_charter_subscription_row: Charter tier not found or "
            "has no product_plan_code — cannot write local subscription row for "
            "tenant %s (sub %s)",
            tenant_id,
            stripe_subscription_id,
        )
        return

    # 2. Resolve status_id via code='trialing' (is_billing_active=True)
    trialing_status = db.exec(
        select(SubscriptionStatus)
        .where(SubscriptionStatus.code == "trialing")
        .where(SubscriptionStatus.is_billing_active == True)
    ).first()
    if not trialing_status:
        logger.error(
            "_write_local_charter_subscription_row: 'trialing' subscription_status "
            "not found — cannot write local subscription row for tenant %s (sub %s)",
            tenant_id,
            stripe_subscription_id,
        )
        return

    # 3. Build the row per design §B.3
    started_at = datetime.now(UTC)
    sub_row = Subscription(
        id=_uuid.uuid4(),
        tenant_id=tenant_id,
        product_plan_code=charter_tier.product_plan_code,
        status_id=trialing_status.id,
        quantity_seats=1,
        started_at=started_at,
        psp_provider="stripe",
        psp_subscription_id=stripe_subscription_id,
        psp_customer_id=stripe_customer_id,
        billing_interval="monthly",
        trial_ends_at=free_period_ends_at,
        renews_at=free_period_ends_at,
        is_active=True,
        stripe_schedule_id=None,
    )

    # 4. Upsert: ON CONFLICT (psp_subscription_id) DO UPDATE
    stmt = pg_insert(Subscription).values(
        id=sub_row.id,
        tenant_id=sub_row.tenant_id,
        product_plan_code=sub_row.product_plan_code,
        status_id=sub_row.status_id,
        quantity_seats=sub_row.quantity_seats,
        started_at=sub_row.started_at,
        psp_provider=sub_row.psp_provider,
        psp_subscription_id=sub_row.psp_subscription_id,
        psp_customer_id=sub_row.psp_customer_id,
        billing_interval=sub_row.billing_interval,
        trial_ends_at=sub_row.trial_ends_at,
        renews_at=sub_row.renews_at,
        is_active=sub_row.is_active,
        stripe_schedule_id=sub_row.stripe_schedule_id,
    )

    stmt = stmt.on_conflict_do_update(
        index_elements=["psp_subscription_id"],
        set_={
            "status_id": trialing_status.id,
            "product_plan_code": charter_tier.product_plan_code,
            "trial_ends_at": free_period_ends_at,
            "renews_at": free_period_ends_at,
            "is_active": True,
            "psp_customer_id": stripe_customer_id,
        },
    )

    db.exec(stmt)
    db.commit()

    logger.info(
        "_write_local_charter_subscription_row: upserted local subscription row "
        "for tenant %s (sub %s, status=trialing, is_active=True)",
        tenant_id,
        stripe_subscription_id,
    )


def create_charter_subscription(
    db: Session,
    tenant_id: UUID,
    stripe_customer_id: str,
    free_period_ends_at: datetime,
    charter_member_number: int | None = None,
) -> str:
    """
    Create a Charter subscription with trial (no payment method required).

    Uses trial_end + trial_settings.end_behavior.missing_payment_method: pause.
    Only the flat-rate charter_monthly item is included at creation time.
    Metered overage items (voice_overage, sms_overage) are added by
    resume_subscription() after a payment method is attached — Stripe
    does not allow metered usage items on subscriptions configured to
    pause at trial end (InvalidRequestError).

    Returns:
        str: Stripe Subscription ID (sub_...).
    """
    from core.stripe_config import get_stripe_ids

    stripe = _get_stripe_client()
    ids = get_stripe_ids()

    sub = stripe.Subscription.create(
        customer=stripe_customer_id,
        items=[
            {"price": ids["prices"]["price_charter_monthly"], "quantity": 1},
        ],
        trial_end=int(free_period_ends_at.timestamp()),
        trial_settings={"end_behavior": {"missing_payment_method": "pause"}},
        payment_behavior="allow_incomplete",
        collection_method="charge_automatically",
        metadata={
            "tenant_id": str(tenant_id),
            "tier_code": "charter",
            "charter_member_number": str(charter_member_number)
            if charter_member_number
            else "",
        },
    )

    logger.info(
        "Charter subscription created for tenant %s: %s (status: %s, trial_end: %s)",
        tenant_id,
        sub.id,
        sub.status,
        free_period_ends_at,
    )

    # PLP-STRIPE-CHARTER-ROW-1: write the local subscription row synchronously
    # so is_subscription_billing_active() flips to True and the paywall opens.
    # Non-blocking: a local-write error is logged and swallowed so the wizard
    # still advances and sub.id is still returned (the webhook fallback or the
    # backfill will write the row).
    try:
        _write_local_charter_subscription_row(
            db,
            tenant_id=tenant_id,
            stripe_customer_id=stripe_customer_id,
            stripe_subscription_id=sub.id,
            free_period_ends_at=free_period_ends_at,
        )
    except Exception as e:
        logger.error(
            "create_charter_subscription: failed to write local subscription "
            "row for tenant %s (sub %s): %s. Wizard advancing; row will be "
            "written by the webhook fallback or the backfill.",
            tenant_id,
            sub.id,
            e,
        )

    return sub.id


def resume_subscription(
    db: Session,
    tenant_id: UUID,
    stripe_payment_method_id: str,
) -> dict:
    """
    Resume a paused Charter subscription after PM addition.

    C-SPIKE-1 flow: attach PM → set default → Subscription.resume() → check status.

    Returns:
        {"psp_subscription_id": str, "status": str, "billing_cycle_anchor": int|None}

    Raises:
        ResumeFailedError: if subscription stays paused after resume.
        ValueError: if tenant/subscription not found or subscription is not paused.
    """
    from app.models.billing import Subscription
    from app.models.core import Tenant

    stripe = _get_stripe_client()

    # 1. Load tenant
    tenant = db.exec(select(Tenant).where(Tenant.id == tenant_id)).first()
    if not tenant or not tenant.stripe_customer_id:
        raise ValueError(f"Tenant {tenant_id} not found or has no Stripe customer ID")

    # 2. Load active subscription
    sub_row = db.exec(
        select(Subscription).where(
            Subscription.tenant_id == tenant_id,
            Subscription.is_active == True,
        )
    ).first()
    if not sub_row or not sub_row.psp_subscription_id:
        raise ValueError(f"No active subscription found for tenant {tenant_id}")

    # 3. Verify Stripe subscription is paused
    stripe_sub = stripe.Subscription.retrieve(sub_row.psp_subscription_id)
    if stripe_sub.status != "paused":
        raise ValueError(
            f"Subscription {sub_row.psp_subscription_id} is not paused "
            f"(status: {stripe_sub.status})"
        )

    # 4. Attach payment method to customer
    stripe.PaymentMethod.attach(
        stripe_payment_method_id,
        customer=tenant.stripe_customer_id,
    )

    # 5. Set as default payment method (REQUIRED before resume)
    stripe.Customer.modify(
        tenant.stripe_customer_id,
        invoice_settings={"default_payment_method": stripe_payment_method_id},
    )

    # 6. Resume the subscription
    resumed_sub = stripe.Subscription.resume(
        sub_row.psp_subscription_id,
        billing_cycle_anchor="now",
    )

    # 7. CRITICAL — check returned status (resume can silently fail!)
    if resumed_sub.status == "paused":
        logger.error(
            "Resume failed for tenant %s: subscription %s remains paused after resume "
            "— payment method may have failed",
            tenant_id,
            sub_row.psp_subscription_id,
        )
        raise ResumeFailedError(
            "Subscription remains paused after resume — payment method may have failed"
        )

    # 7b. Add metered overage items (voice_overage + sms_overage).
    # These cannot be included at creation time because Stripe does not
    # allow metered usage items on subscriptions configured to pause at
    # trial end. They are added here after the subscription is resumed
    # with a payment method on file.
    _add_metered_overage_items(stripe, resumed_sub.id)

    # 8. Update subscription status to active
    from app.models.billing import SubscriptionStatus

    active_status = db.exec(
        select(SubscriptionStatus)
        .where(SubscriptionStatus.code == "active")
        .where(SubscriptionStatus.is_billing_active == True)
    ).first()
    if active_status:
        sub_row.status_id = active_status.id
        db.add(sub_row)
        db.commit()

    logger.info(
        "Subscription resumed for tenant %s: %s (status: %s)",
        tenant_id,
        resumed_sub.id,
        resumed_sub.status,
    )

    return {
        "psp_subscription_id": resumed_sub.id,
        "status": resumed_sub.status,
        "billing_cycle_anchor": resumed_sub.billing_cycle_anchor,
    }


def upgrade_charter_to_teams(
    db: Session,
    tenant_id: UUID,
    billing_interval: str,
) -> dict:
    """Upgrade a Charter member to the Teams plan.

    This is a PERMANENT, IRREVERSIBLE action:
    1. Deletes the Charter monthly item from the Stripe subscription
    2. Adds the Teams item (monthly or annual price based on billing_interval)
    3. Ends the trial immediately (trial_end="now") if the subscription is trialing
    4. Sets proration_behavior="create_prorations" (immediate invoice for the difference)
    5. Flips tenant.charter_eligible = False (permanent — D23)
    6. Updates tenant.current_subscription_tier_id to Teams
    7. Nulls tenant.free_period_ends_at (no longer in free period)
    8. Updates subscription row: product_plan_code, billing_interval, status_id→active

    The metered items (voice_overage, sms_overage) are preserved if present.
    If the subscription was created without metered items (Charter trial
    without prior resume), they are added during the upgrade.

    Args:
        db: Database session
        tenant_id: Tenant to upgrade
        billing_interval: "monthly" or "annual"

    Returns:
        {"psp_subscription_id", "new_tier_name", "billing_interval",
         "charter_eligible_forfeited"}

    Raises:
        ValueError: tenant is not Charter, no active subscription,
                    no payment method, or Stripe API error
    """
    from app.models.billing import Subscription, SubscriptionStatus
    from app.models.core import Tenant
    from app.models.subscription import SubscriptionTier
    from core.stripe_config import get_stripe_ids

    if billing_interval not in ("monthly", "annual"):
        raise ValueError("billing_interval must be 'monthly' or 'annual'")

    stripe = _get_stripe_client()
    ids = get_stripe_ids()

    # 1. Load tenant (tenant-scoped select — Rule 7.1)
    tenant = db.exec(select(Tenant).where(Tenant.id == tenant_id)).first()
    if not tenant:
        raise ValueError(f"Tenant {tenant_id} not found")

    # 2. Verify tenant is Charter
    if not tenant.charter_eligible:
        raise ValueError("Tenant is not a Charter member")

    charter_tier = db.exec(
        select(SubscriptionTier).where(SubscriptionTier.tier_name == "charter")
    ).first()
    if not charter_tier:
        raise ValueError("Charter tier not found")

    if tenant.current_subscription_tier_id != charter_tier.tier_id:
        raise ValueError("Tenant is not on the Charter tier")

    # 3. Load active subscription
    sub_row = db.exec(
        select(Subscription).where(
            Subscription.tenant_id == tenant_id,
            Subscription.is_active == True,
        )
    ).first()
    if not sub_row or not sub_row.psp_subscription_id:
        raise ValueError("No active subscription found")

    # 4. Verify payment method on file
    customer = stripe.Customer.retrieve(
        tenant.stripe_customer_id,
        expand=["invoice_settings.default_payment_method"],
    )
    invoice_settings = getattr(customer, "invoice_settings", None)
    default_pm = (
        getattr(invoice_settings, "default_payment_method", None)
        if invoice_settings
        else None
    )
    if not default_pm:
        raise ValueError("No payment method on file. Add a card before upgrading.")

    # 5. Retrieve Stripe subscription to find the Charter item
    stripe_sub = stripe.Subscription.retrieve(sub_row.psp_subscription_id)
    charter_price_id = ids["prices"]["price_charter_monthly"]
    teams_price_id = (
        ids["prices"]["price_teams_annual"]
        if billing_interval == "annual"
        else ids["prices"]["price_teams_monthly"]
    )

    charter_item = None
    for item in stripe_sub["items"]["data"]:
        if item["price"]["id"] == charter_price_id:
            charter_item = item
            break

    if not charter_item:
        raise ValueError("Charter price item not found on subscription")

    # 6. Build modify call — swap charter item for teams item
    items_list = [
        {"id": charter_item["id"], "deleted": True},
        {"price": teams_price_id, "quantity": 1},
    ]

    # Add metered overage items if not already present (Charter subscriptions
    # created without metered items due to Stripe trial-pause constraint).
    voice_price_id = ids["prices"]["price_voice_overage"]
    sms_price_id = ids["prices"]["price_sms_overage"]
    existing_price_ids = {item["price"]["id"] for item in stripe_sub["items"]["data"]}
    if voice_price_id not in existing_price_ids:
        items_list.append({"price": voice_price_id})
    if sms_price_id not in existing_price_ids:
        items_list.append({"price": sms_price_id})

    modify_kwargs = {
        "items": items_list,
        "proration_behavior": "create_prorations",
    }

    # End trial if active
    if stripe_sub.status == "trialing":
        modify_kwargs["trial_end"] = "now"

    # Clear trial_settings if adding metered items — Stripe won't allow
    # metered items while the pause-at-trial-end config is present.
    adding_metered = len(items_list) > 2  # more than delete + add
    if adding_metered:
        trial_settings = getattr(stripe_sub, "trial_settings", None)
        if trial_settings:
            modify_kwargs["trial_settings"] = {
                "end_behavior": {"missing_payment_method": "cancel"}
            }

    # 7. Call Stripe
    updated_sub = stripe.Subscription.modify(
        sub_row.psp_subscription_id,
        **modify_kwargs,
    )

    # 8. Update tenant (AFTER Stripe success)
    teams_tier = db.exec(
        select(SubscriptionTier).where(SubscriptionTier.tier_name == "teams")
    ).first()

    tenant.charter_eligible = False  # D23 — permanent forfeiture
    tenant.current_subscription_tier_id = teams_tier.tier_id
    tenant.free_period_ends_at = None  # No longer in free period
    db.add(tenant)

    # 9. Update subscription row
    active_status = db.exec(
        select(SubscriptionStatus).where(
            SubscriptionStatus.code == "active",
            SubscriptionStatus.is_billing_active == True,
        )
    ).first()

    sub_row.product_plan_code = teams_tier.product_plan_code
    sub_row.billing_interval = billing_interval
    sub_row.trial_ends_at = None
    if active_status:
        sub_row.status_id = active_status.id
    db.add(sub_row)

    db.commit()

    logger.info(
        "Charter tenant %s upgraded to Teams (billing_interval=%s, "
        "charter_eligible=false, sub_id=%s)",
        tenant_id,
        billing_interval,
        updated_sub.id,
    )

    return {
        "psp_subscription_id": updated_sub.id,
        "new_tier_name": "teams",
        "billing_interval": billing_interval,
        "charter_eligible_forfeited": True,
    }


def report_usage_event(
    db: Session,
    tenant_id: UUID,
    event_name: str,
    identifier: str,
    value: int,
    timestamp: datetime,
) -> None:
    """
    Report a Billing Meter event to Stripe.

    Uses stripe.billing.MeterEvent.create() with identifier as idempotency key.
    Non-blocking: logs error and returns None on failure (usage data is best-effort).
    """
    from app.models.core import Tenant

    stripe = _get_stripe_client()

    # Get stripe_customer_id
    tenant = db.exec(select(Tenant).where(Tenant.id == tenant_id)).first()
    if not tenant or not tenant.stripe_customer_id:
        logger.warning(
            "report_usage_event: tenant %s has no stripe_customer_id — skipping",
            tenant_id,
        )
        return

    try:
        stripe.billing.MeterEvent.create(
            event_name=event_name,
            identifier=identifier,
            payload={
                "stripe_customer_id": tenant.stripe_customer_id,
                "value": str(value),
            },
            timestamp=int(timestamp.timestamp()),
        )
        logger.debug(
            "Meter event reported: %s=%s for tenant %s (id: %s)",
            event_name,
            value,
            tenant_id,
            identifier,
        )
    except Exception as e:
        # Non-blocking — usage data is best-effort
        logger.error(
            "Failed to report meter event %s for tenant %s: %s",
            event_name,
            tenant_id,
            e,
        )


# ---------------------------------------------------------------------
# C-B4 webhook handlers
# ---------------------------------------------------------------------


def handle_subscription_trial_will_end(db: Session, stripe_event: dict) -> None:
    """customer.subscription.trial_will_end — fires 3 days before trial ends.

    C-B6: Dispatches the T-3 free-period notification via the free-period
    notification pipeline. The Celery beat task (daily 09:00 UTC) also fires
    at T-3 — idempotency via ``NotificationEvent.payload->>'days_remaining'``
    prevents duplicate notifications.
    """
    sub = stripe_event.get("data", {}).get("object", {})
    stripe_customer_id = sub.get("customer")
    if not stripe_customer_id:
        logger.info(
            "Trial will end for subscription %s — no customer ID, skipping",
            sub.get("id"),
        )
        return

    from app.models.core import Tenant

    tenant = db.exec(
        select(Tenant).where(Tenant.stripe_customer_id == stripe_customer_id)
    ).first()

    if not tenant:
        logger.warning(
            "handle_subscription_trial_will_end: no tenant for stripe_customer_id=%s",
            stripe_customer_id,
        )
        return

    if not tenant.free_period_ends_at:
        logger.info(
            "Trial will end for subscription %s — tenant %s has no "
            "free_period_ends_at, skipping free-period notification",
            sub.get("id"),
            tenant.id,
        )
        return

    logger.info(
        "Trial will end for subscription %s — dispatching T-3 free-period "
        "notification for tenant %s",
        sub.get("id"),
        tenant.id,
    )

    from tasks.free_period_notifications import _dispatch_free_period_notification

    _dispatch_free_period_notification(db, tenant, days_remaining=3)
    db.commit()


def handle_subscription_paused(db: Session, stripe_event: dict) -> None:
    """customer.subscription.paused — update subscription.status_id to 'paused'.

    Do NOT disable SMS if tenant_messaging_registration.status='active' (spec §6.8).
    """
    from app.models.billing import Subscription, SubscriptionStatus

    sub = stripe_event.get("data", {}).get("object", {})
    stripe_sub_id = sub.get("id")
    if not stripe_sub_id:
        return

    # Find subscription row by psp_subscription_id
    sub_row = db.exec(
        select(Subscription).where(Subscription.psp_subscription_id == stripe_sub_id)
    ).first()
    if not sub_row:
        logger.warning(
            "handle_subscription_paused: no subscription row for %s", stripe_sub_id
        )
        return

    # Update status to 'paused'
    paused_status = db.exec(
        select(SubscriptionStatus).where(SubscriptionStatus.code == "paused")
    ).first()
    if paused_status:
        sub_row.status_id = paused_status.id
        db.add(sub_row)
        db.commit()

    logger.info(
        "Subscription %s paused — tenant %s enters read-only paywall",
        stripe_sub_id,
        sub_row.tenant_id,
    )
    # Entitlement enforcement (job/quote/invoice creation blocked) is handled by
    # the existing is_billing_active paywall — paused status has is_billing_active=false


def handle_subscription_resumed(db: Session, stripe_event: dict) -> None:
    """customer.subscription.resumed — update subscription.status_id to 'active'."""
    from app.models.billing import Subscription, SubscriptionStatus

    sub = stripe_event.get("data", {}).get("object", {})
    stripe_sub_id = sub.get("id")
    if not stripe_sub_id:
        return

    sub_row = db.exec(
        select(Subscription).where(Subscription.psp_subscription_id == stripe_sub_id)
    ).first()
    if not sub_row:
        logger.warning(
            "handle_subscription_resumed: no subscription row for %s", stripe_sub_id
        )
        return

    active_status = db.exec(
        select(SubscriptionStatus)
        .where(SubscriptionStatus.code == "active")
        .where(SubscriptionStatus.is_billing_active == True)
    ).first()
    if active_status:
        sub_row.status_id = active_status.id
        db.add(sub_row)
        db.commit()

    logger.info(
        "Subscription %s resumed — tenant %s full access restored",
        stripe_sub_id,
        sub_row.tenant_id,
    )


def handle_subscription_deleted(db: Session, stripe_event: dict) -> None:
    """customer.subscription.deleted — set tenant.charter_eligible=false permanently;
    update subscription.status_id to 'canceled'; audit."""
    from app.models.billing import Subscription, SubscriptionStatus
    from app.models.core import Tenant

    sub = stripe_event.get("data", {}).get("object", {})
    stripe_sub_id = sub.get("id")
    stripe_customer_id = sub.get("customer")
    if not stripe_sub_id or not stripe_customer_id:
        return

    # Find tenant by stripe_customer_id
    tenant = db.exec(
        select(Tenant).where(Tenant.stripe_customer_id == stripe_customer_id)
    ).first()
    if not tenant:
        logger.warning(
            "handle_subscription_deleted: no tenant for customer %s",
            stripe_customer_id,
        )
        return

    # Set charter_eligible = false permanently
    tenant.charter_eligible = False
    db.add(tenant)

    # Update subscription status to 'canceled'
    sub_row = db.exec(
        select(Subscription).where(Subscription.psp_subscription_id == stripe_sub_id)
    ).first()
    if sub_row:
        canceled_status = db.exec(
            select(SubscriptionStatus).where(SubscriptionStatus.code == "canceled")
        ).first()
        if canceled_status:
            sub_row.status_id = canceled_status.id
            sub_row.is_active = False
            sub_row.canceled_at = datetime.now(UTC)
            db.add(sub_row)

    db.commit()
    logger.info(
        "Subscription %s deleted — tenant %s charter_eligible=false, subscription canceled",
        stripe_sub_id,
        tenant.id,
    )


def handle_invoice_paid(db: Session, stripe_event: dict) -> None:
    """invoice.paid — clear dunning state (if any). Log payment success."""
    invoice = stripe_event.get("data", {}).get("object", {})
    stripe_sub_id = invoice.get("subscription")
    amount_paid = invoice.get("amount_paid", 0)

    logger.info(
        "Invoice paid for subscription %s: $%.2f",
        stripe_sub_id,
        amount_paid / 100,
    )
    # Dunning state clearing: if the subscription was in 'past_due' or 'unpaid' status,
    # update to 'active'. The customer.subscription.updated webhook may also fire.
    # For MVP, just log — dunning recovery is handled by the subscription.updated handler.


def handle_checkout_session_completed(db: Session, stripe_event: dict) -> None:
    """checkout.session.completed — 10DLC setup charge handler (C-B9).

    If metadata.purpose == 'a2p_10dlc_setup':
      1. Attach PM as customer.invoice_settings.default_payment_method
      2. Transition registration to 'brand_submitted'
      3. Enqueue Celery task: provision_brand(registration_id)
    """
    from app.models.sms import TenantMessagingRegistration
    from services.messaging_provisioning import transition_status

    session = stripe_event.get("data", {}).get("object", {})
    purpose = session.get("metadata", {}).get("purpose")

    if purpose == "a2p_10dlc_setup":
        checkout_id = session.get("id")
        registration_id_str = session.get("metadata", {}).get("registration_id")
        customer_id = session.get("customer")
        payment_intent_id = session.get("payment_intent")

        logger.info(
            "Checkout session completed for 10DLC setup: %s (registration=%s)",
            checkout_id,
            registration_id_str,
        )

        # 1. Attach PM as customer.invoice_settings.default_payment_method
        if customer_id and payment_intent_id:
            try:
                stripe = _get_stripe_client()
                # Retrieve the payment intent to get the payment method
                pi = stripe.PaymentIntent.retrieve(payment_intent_id)
                pm_id = pi.payment_method
                if pm_id:
                    stripe.Customer.modify(
                        customer_id,
                        invoice_settings={"default_payment_method": pm_id},
                    )
                    logger.info(
                        "Attached PM %s as default for customer %s",
                        pm_id,
                        customer_id,
                    )
            except Exception as exc:
                logger.error(
                    "Failed to attach PM for 10DLC checkout %s: %s",
                    checkout_id,
                    exc,
                )

        # 2. Transition registration to 'brand_submitted'
        if registration_id_str:
            try:
                import uuid as _uuid

                reg_id = _uuid.UUID(registration_id_str)
                registration = db.exec(
                    select(TenantMessagingRegistration).where(
                        TenantMessagingRegistration.id == reg_id
                    )
                ).first()

                if registration:
                    # Store payment intent on registration
                    if payment_intent_id:
                        registration.stripe_payment_intent = payment_intent_id
                        db.add(registration)

                    # Transition to brand_submitted
                    if registration.status == "awaiting_payment":
                        transition_status(db, registration, "brand_submitted")

                        # 3. Enqueue Celery task: provision_brand
                        try:
                            from core.celery_app import celery_app

                            celery_app.send_task(
                                "provision_brand",
                                args=[str(reg_id)],
                            )
                            logger.info(
                                "Enqueued provision_brand task for registration %s",
                                reg_id,
                            )
                        except Exception as exc:
                            logger.error(
                                "Failed to enqueue provision_brand task: %s", exc
                            )
                    else:
                        logger.warning(
                            "Registration %s in status %s, not transitioning "
                            "to brand_submitted",
                            reg_id,
                            registration.status,
                        )
                else:
                    logger.warning(
                        "Registration %s not found for 10DLC checkout %s",
                        registration_id_str,
                        checkout_id,
                    )
            except Exception as exc:
                logger.error("Failed to process 10DLC checkout completion: %s", exc)
    else:
        logger.debug(
            "Checkout session completed: %s (purpose: %s)",
            session.get("id"),
            purpose,
        )


def handle_payment_method_attached(db: Session, stripe_event: dict) -> None:
    """payment_method.attached — if tenant's subscription is paused, log.

    Frontend will surface resume affordance via subscription status polling.
    """
    from app.models.billing import Subscription

    pm = stripe_event.get("data", {}).get("object", {})
    customer_id = pm.get("customer")
    if not customer_id:
        return

    # Check if tenant has a paused subscription
    sub_row = db.exec(
        select(Subscription).where(
            Subscription.psp_customer_id == customer_id,
            Subscription.is_active == True,
        )
    ).first()

    if sub_row:
        # Check Stripe status
        stripe = _get_stripe_client()
        try:
            stripe_sub = stripe.Subscription.retrieve(sub_row.psp_subscription_id)
            if stripe_sub.status == "paused":
                logger.info(
                    "Payment method attached for paused subscription %s — tenant can resume",
                    sub_row.psp_subscription_id,
                )
        except Exception as e:
            logger.error(
                "handle_payment_method_attached: failed to check subscription status: %s",
                e,
            )
