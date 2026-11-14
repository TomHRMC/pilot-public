"""C-B11 — Operator Cohort Dashboard service.

Platform-level (not tenant-scoped) aggregation + write actions for the
Charter cohort management dashboard.

Three functions:
    - get_cohort_overview()  — read aggregation across all Charter members
    - extend_free_period()   — silent free-period extension (D16)
    - close_cohort()         — archive Charter price + deactivate tier
"""

import logging
import uuid
from datetime import datetime

from sqlalchemy import func
from sqlmodel import Session, select

from app.models.billing import Invoice, Subscription, SubscriptionStatus
from app.models.core import Tenant
from app.models.sms import TenantMessagingRegistration
from app.models.subscription import SubscriptionTier, TenantTierOverride
from core.datetime_utils import safe_now_utc

logger = logging.getLogger(__name__)


def get_cohort_overview(db: Session) -> dict:
    """Return all Charter members with tripwire alert data.

    Aggregates per-tenant: subscription status, messaging status, customer
    count, invoice count, days since last job, and computes an alert_level
    (red / amber / none).

    Returns:
        dict with keys: cohort_tier_name, cohort_is_active, signup_cap, members.
    """
    # 1. Charter tier metadata
    charter_tier = db.exec(
        select(SubscriptionTier).where(SubscriptionTier.tier_name == "charter")
    ).first()

    if not charter_tier:
        return {
            "cohort_tier_name": "charter",
            "cohort_is_active": False,
            "signup_cap": 0,
            "members": [],
        }

    # 2. All Charter-eligible tenants, ordered by member number
    tenants = db.exec(
        select(Tenant)
        .where(Tenant.charter_eligible == True)
        .order_by(Tenant.charter_member_number)
    ).all()

    members: list[dict] = []
    now = safe_now_utc()

    for tenant in tenants:
        # Subscription status
        sub_row = db.exec(
            select(Subscription)
            .where(Subscription.tenant_id == tenant.id)
            .where(Subscription.is_active == True)
        ).first()

        stripe_status = "unknown"
        if sub_row:
            status_row = db.exec(
                select(SubscriptionStatus).where(
                    SubscriptionStatus.id == sub_row.status_id
                )
            ).first()
            stripe_status = status_row.code if status_row else "unknown"

        # Messaging (10DLC) status
        msg_reg = db.exec(
            select(TenantMessagingRegistration).where(
                TenantMessagingRegistration.tenant_id == tenant.id
            )
        ).first()
        messaging_status = msg_reg.status if msg_reg else "not_started"

        # Customer count
        from app.models.crm import Customer

        customer_count = db.exec(
            select(func.count(Customer.id)).where(Customer.tenant_id == tenant.id)
        ).one()

        # Invoice count
        invoice_count = db.exec(
            select(func.count(Invoice.id)).where(Invoice.tenant_id == tenant.id)
        ).one()

        # Last job created_at (activation tripwire)
        from app.models.fulfillment import Job

        last_job = db.exec(
            select(func.max(Job.created_at)).where(Job.tenant_id == tenant.id)
        ).one()

        days_since_last_job: int | None = None
        if last_job:
            days_since_last_job = (now - last_job).days

        # Days remaining in free period
        days_remaining: int | None = None
        if tenant.free_period_ends_at:
            days_remaining = (tenant.free_period_ends_at - now).days

        # Alert level: red takes precedence over amber
        alert_level = "none"
        if days_since_last_job is None or days_since_last_job > 7:
            alert_level = "red"
        elif (
            tenant.free_period_ends_at
            and days_remaining is not None
            and days_remaining <= 14
        ):
            alert_level = "amber"

        members.append(
            {
                "tenant_id": str(tenant.id),
                "business_name": tenant.name,
                "charter_member_number": tenant.charter_member_number,
                "free_period_ends_at": tenant.free_period_ends_at.isoformat()
                if tenant.free_period_ends_at
                else None,
                "days_remaining": days_remaining,
                "stripe_status": stripe_status,
                "has_payment_method": False,  # deferred — requires N Stripe API calls
                "messaging_status": messaging_status,
                "customer_count": customer_count,
                "invoice_count": invoice_count,
                "days_since_last_job": days_since_last_job,
                "last_contact": None,  # deferred — no operator contact log table yet
                "alert_level": alert_level,
            }
        )

    return {
        "cohort_tier_name": charter_tier.tier_name,
        "cohort_is_active": charter_tier.is_active,
        "signup_cap": charter_tier.signup_cap or 0,
        "members": members,
    }


def extend_free_period(
    db: Session,
    tenant_id: uuid.UUID,
    new_end_date: datetime,
    reason: str,
    operator_user_id: uuid.UUID,
) -> dict:
    """Silently extend a Charter member's free period (D16).

    1. Validate: tenant is Charter (charter_eligible=True), subscription is
       'trialing'.
    2. Upsert tenant_tier_override (override_free_period_ends_at +
       override_reason + set_by_operator_user_id).
    3. Update tenant.free_period_ends_at = new_end_date.
    4. stripe.Subscription.modify(sub_id, trial_end=int(new_end_date.timestamp())).
    5. Audit log entry (via set_audit_context_sync — caller's responsibility).
    6. NO customer notification.

    Raises:
        ValueError: Tenant not found, not Charter, subscription not trialing,
            or new date is not after the current date.
    """
    # 1. Load tenant
    tenant = db.exec(select(Tenant).where(Tenant.id == tenant_id)).first()
    if not tenant:
        raise ValueError(f"Tenant {tenant_id} not found")

    if not tenant.charter_eligible:
        raise ValueError(f"Tenant {tenant_id} is not a Charter member")

    # 2. Validate new date is after current
    if tenant.free_period_ends_at and new_end_date <= tenant.free_period_ends_at:
        raise ValueError(
            f"New free period end date {new_end_date} must be after "
            f"current {tenant.free_period_ends_at}"
        )

    # 3. Find active Stripe subscription + check status is 'trialing'
    sub_row = db.exec(
        select(Subscription)
        .where(Subscription.tenant_id == tenant_id)
        .where(Subscription.is_active == True)
        .where(Subscription.psp_provider == "stripe")
    ).first()

    if not sub_row or not sub_row.psp_subscription_id:
        raise ValueError(f"No active Stripe subscription found for tenant {tenant_id}")

    status_row = db.exec(
        select(SubscriptionStatus).where(SubscriptionStatus.id == sub_row.status_id)
    ).first()

    if not status_row or status_row.code != "trialing":
        raise ValueError(
            f"Subscription status is "
            f"'{status_row.code if status_row else 'unknown'}', must be "
            f"'trialing' to extend. Use the resume flow instead."
        )

    # 4. Validate operator_user_id exists in the user table (FK guard).
    #    The route passes the authenticated platform_user.id, but a stale
    #    or invalid UUID would cause a raw ForeignKeyViolation 500. Raise
    #    ValueError("... not found ...") so the route maps it to 404 RFC 7807.
    from app.models.core import User

    operator = db.exec(select(User).where(User.id == operator_user_id)).first()
    if not operator:
        raise ValueError(
            f"Operator user {operator_user_id} not found — cannot record override"
        )

    # 5. Upsert tenant_tier_override
    previous_end = tenant.free_period_ends_at

    existing_override = db.exec(
        select(TenantTierOverride).where(TenantTierOverride.tenant_id == tenant_id)
    ).first()

    if existing_override:
        existing_override.override_free_period_ends_at = new_end_date
        existing_override.override_reason = reason
        existing_override.set_by_operator_user_id = operator_user_id
        existing_override.set_at = safe_now_utc()
        db.add(existing_override)
    else:
        override = TenantTierOverride(
            tenant_id=tenant_id,
            override_free_period_ends_at=new_end_date,
            override_reason=reason,
            set_by_operator_user_id=operator_user_id,
            set_at=safe_now_utc(),
        )
        db.add(override)

    # 5. Update tenant.free_period_ends_at
    tenant.free_period_ends_at = new_end_date
    db.add(tenant)
    db.commit()
    db.refresh(tenant)

    # 6. Call Stripe to update trial_end
    from services.stripe_subscriptions import _get_stripe_client

    stripe = _get_stripe_client()
    stripe.Subscription.modify(
        sub_row.psp_subscription_id,
        trial_end=int(new_end_date.timestamp()),
    )

    logger.info(
        "Extended free period for tenant %s: %s → %s (reason: %s, operator: %s)",
        tenant_id,
        previous_end,
        new_end_date,
        reason,
        operator_user_id,
    )

    return {
        "previous_free_period_ends_at": previous_end.isoformat()
        if previous_end
        else None,
        "new_free_period_ends_at": new_end_date.isoformat(),
        "stripe_subscription_id": sub_row.psp_subscription_id,
        "stripe_trial_end_updated": True,
    }


def close_cohort(db: Session, operator_user_id: uuid.UUID) -> dict:
    """Close the Charter cohort — archive price, deactivate tier, activate others.

    1. stripe.Price.modify(price_charter_monthly_id, active=false) — archive,
       never delete.
    2. UPDATE subscription_tier SET is_active=false WHERE tier_name='charter'.
    3. UPDATE subscription_tier SET is_active=true WHERE tier_name IN
       ('trial', 'starter', 'teams').
    4. Audit log entry (via set_audit_context_sync — caller's responsibility).

    Raises:
        ValueError: Cohort already closed (charter tier is_active=false).
    """
    # 1. Check Charter tier is still active
    charter_tier = db.exec(
        select(SubscriptionTier).where(SubscriptionTier.tier_name == "charter")
    ).first()

    if not charter_tier:
        raise ValueError("Charter tier not found")

    if not charter_tier.is_active:
        raise ValueError("Cohort already closed — Charter tier is already inactive")

    # 2. Archive the Charter price in Stripe
    from core.stripe_config import get_stripe_ids
    from services.stripe_subscriptions import _get_stripe_client

    stripe_ids = get_stripe_ids()
    charter_price_id = stripe_ids.get("prices", {}).get("price_charter_monthly")

    if charter_price_id:
        stripe = _get_stripe_client()
        stripe.Price.modify(charter_price_id, active=False)
        logger.info("Archived Charter price %s in Stripe", charter_price_id)

    # 3. Deactivate Charter tier
    charter_tier.is_active = False
    db.add(charter_tier)

    # 4. Activate other tiers
    activated_tiers: list[str] = []
    other_tiers = db.exec(
        select(SubscriptionTier).where(
            SubscriptionTier.tier_name.in_(["trial", "starter", "teams"])
        )
    ).all()

    for tier in other_tiers:
        if not tier.is_active:
            tier.is_active = True
            db.add(tier)
            activated_tiers.append(tier.tier_name)

    db.commit()

    logger.info(
        "Cohort closed by operator %s: Charter price archived, tier "
        "deactivated, %d tiers activated",
        operator_user_id,
        len(activated_tiers),
    )

    return {
        "charter_price_archived": bool(charter_price_id),
        "charter_tier_deactivated": True,
        "activated_tiers": activated_tiers,
    }
