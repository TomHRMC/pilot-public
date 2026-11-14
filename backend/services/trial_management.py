"""
B14/A73 — Trial state machine and expiration enforcement service.
Used by: tenant signup wizard (A73), enforce_trial_expirations Celery task (A73),
         tier limit enforcer (A75), Stripe webhook handler (A76).
"""

import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlmodel import Session, select

from app.models.core import Tenant
from app.models.subscription import (
    SubscriptionTier,
    TenantSubscriptionUsage,
    TenantTierOverride,
)
from app.models.system import NotificationOutbox

logger = logging.getLogger(__name__)

# Hardcoded fallback trial length when no tier/override specifies one
DEFAULT_TRIAL_DAYS = 14


def compute_trial_end_date(
    db: Session,
    tenant_id: UUID,
    trial_start: datetime,
) -> datetime:
    """
    Resolve trial length using two-tier chain:
    1. tenant_tier_override.override_trial_length_days (operator override)
    2. subscription_tier.trial_duration_days (system default for trial tier)
    3. Hardcoded fallback: 14 days

    Returns:
        datetime (UTC): computed trial_ends_at timestamp
    """
    # Check operator override
    override = db.exec(
        select(TenantTierOverride).where(TenantTierOverride.tenant_id == tenant_id)
    ).first()

    if override and override.override_trial_length_days is not None:
        days = override.override_trial_length_days
        logger.debug(
            f"Trial length for {tenant_id}: {days} days (from operator override)"
        )
        return trial_start + timedelta(days=days)

    # Check trial tier default
    tenant = db.exec(select(Tenant).where(Tenant.id == tenant_id)).first()
    if tenant and tenant.current_subscription_tier_id:
        tier = db.exec(
            select(SubscriptionTier)
            .where(SubscriptionTier.tier_id == tenant.current_subscription_tier_id)
            .where(SubscriptionTier.is_trial == True)
        ).first()
        if tier and tier.trial_duration_days is not None:
            days = tier.trial_duration_days
            logger.debug(f"Trial length for {tenant_id}: {days} days (from trial tier)")
            return trial_start + timedelta(days=days)

    logger.debug(
        f"Trial length for {tenant_id}: {DEFAULT_TRIAL_DAYS} days (hardcoded fallback)"
    )
    return trial_start + timedelta(days=DEFAULT_TRIAL_DAYS)


def activate_trial(
    db: Session,
    tenant_id: UUID,
    initiating_user_id: UUID,
) -> None:
    """
    Set tenant.trial_started_at = now(), tenant.trial_ends_at = compute_trial_end_date().
    Creates tenant_subscription_usage row for the trial period.
    Called from wizard step 5 (trial confirmation path) and from signup completion.

    Args:
        db:                   Active DB session
        tenant_id:            Target tenant
        initiating_user_id:   Owner user completing the wizard
    """
    now = datetime.now(UTC)

    tenant = db.exec(select(Tenant).where(Tenant.id == tenant_id)).first()
    if not tenant:
        raise ValueError(f"Tenant {tenant_id} not found")

    tenant.trial_started_at = now
    tenant.trial_ends_at = compute_trial_end_date(db, tenant_id, now)
    db.add(tenant)

    # Create trial period usage row
    period_start = now
    period_end = tenant.trial_ends_at

    # Check if usage row already exists for this period
    existing_usage = db.exec(
        select(TenantSubscriptionUsage)
        .where(TenantSubscriptionUsage.tenant_id == tenant_id)
        .where(TenantSubscriptionUsage.period_start == period_start)
    ).first()

    if not existing_usage:
        usage = TenantSubscriptionUsage(
            tenant_id=tenant_id,
            period_start=period_start,
            period_end=period_end,
            current_user_count=1,  # Count the owner who just signed up
            current_sms_segment_count=0,
        )
        db.add(usage)

    db.commit()
    logger.info(f"Trial activated for tenant {tenant_id}: ends {tenant.trial_ends_at}")


def check_trial_expired(db: Session, tenant_id: UUID) -> bool:
    """
    Returns True if tenant is on trial tier AND trial_ends_at <= now().
    Used by API middleware paywall gate and enforce_trial_expirations task.
    """
    tenant = db.exec(select(Tenant).where(Tenant.id == tenant_id)).first()
    if not tenant:
        return False

    if not tenant.trial_ends_at:
        return False

    # Check if tenant is on trial tier
    if not tenant.current_subscription_tier_id:
        return False

    tier = db.exec(
        select(SubscriptionTier).where(
            SubscriptionTier.tier_id == tenant.current_subscription_tier_id
        )
    ).first()

    if not tier or not tier.is_trial:
        return False

    return tenant.trial_ends_at <= datetime.now(UTC)


def enforce_paywall(db: Session, tenant_id: UUID) -> dict:
    """
    Returns structured 402 payload for write-blocked trial-expired tenants.

    Returns:
        dict with keys: paywall=True, paywall_message=str, upgrade_url=str
        Returns empty dict {} if paywall does NOT apply.
    """
    if not check_trial_expired(db, tenant_id):
        return {}

    return {
        "paywall": True,
        "paywall_message": "Your trial has expired. Upgrade to continue using Pilot.",
        "upgrade_url": "/settings/subscription/upgrade",
    }


def dispatch_trial_warning(db: Session, tenant_id: UUID, days_remaining: int) -> None:
    """
    Write a notification_outbox row for a trial expiration warning.
    Category: 'billing'; sub_trigger: 'billing.trial_expiring'
    Day-0 uses system_announcements.critical (forced-minimum push).

    Args:
        db:              Active DB session
        tenant_id:       Target tenant
        days_remaining:  0 | 1 | 3 | 7 — determines copy and priority
    """
    # Look up owner user for this tenant
    from app.models.auth import TenantUser

    owner = db.exec(
        select(TenantUser)
        .where(TenantUser.tenant_id == tenant_id)
        .where(TenantUser.role_code == "owner")
        .where(TenantUser.is_active == True)
    ).first()

    if not owner:
        logger.warning(
            f"No active owner found for tenant {tenant_id} — skipping trial warning"
        )
        return

    # Look up notification category
    from app.models.system import NotificationCategory

    if days_remaining == 0:
        category_code = "system_announcements"
        sub_trigger_code = "system_announcements.critical"
        priority = "critical"
    else:
        category_code = "billing"
        sub_trigger_code = "billing.trial_expiring"
        priority = "standard"

    category = db.exec(
        select(NotificationCategory).where(NotificationCategory.code == category_code)
    ).first()

    if days_remaining == 0:
        body = "Your trial has expired. Pick a plan now to keep using Pilot."
    elif days_remaining == 1:
        body = "Your trial expires tomorrow. Pick a plan to keep using Pilot."
    elif days_remaining == 3:
        body = "Your trial expires in 3 days. Pick a plan to keep using Pilot."
    else:
        body = f"Your trial expires in {days_remaining} days. Pick a plan to keep using Pilot."

    outbox = NotificationOutbox(
        tenant_id=tenant_id,
        recipient_user_id=owner.user_id,
        category_id=category.id if category else None,
        sub_trigger_id=sub_trigger_code,
        channel="push",
        body=body,
        deep_link_target="/settings/subscription/upgrade",
        priority=priority,
    )
    db.add(outbox)
    db.commit()
    logger.info(
        f"Trial warning dispatched for tenant {tenant_id}: {days_remaining} days remaining"
    )
