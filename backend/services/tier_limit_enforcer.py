"""
B14/A75 — Tier limit enforcement service.
Used by: user invitation routes, SMS send service.

MKT-B11: Updated for Pricing Model v3.0
- Removed max_users enforcement (unlimited users is now a permanent invariant)
- Removed max_sms_segments_per_month enforcement (SMS limits live in ppfv)
- Added get_effective_schedule_lanes() helper for dispatch board lane enforcement
- check_user_add_allowed now always returns (True, {}) — unlimited users invariant
- increment_user_count / decrement_user_count retained for usage tracking

Resolution chain:
1. tenant_tier_override.override_tier_id (operator override tier)
2. tenant.current_subscription_tier_id (tenant's active tier)
"""

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlmodel import Session, select

from app.models.billing import (
    ProductPlanProductFeatureVersion,
    Subscription,
    TenantProductFeatureOverride,
)
from app.models.core import Tenant
from app.models.subscription import (
    SubscriptionTier,
    TenantSubscriptionUsage,
    TenantTierOverride,
)

logger = logging.getLogger(__name__)


def _get_effective_tier(db: Session, tenant_id: UUID) -> SubscriptionTier:
    """
    Resolve the effective subscription tier for a tenant.
    Operator override takes precedence over tenant's current_subscription_tier_id.
    """
    # Check for operator override
    override = db.exec(
        select(TenantTierOverride).where(TenantTierOverride.tenant_id == tenant_id)
    ).first()

    if override and override.override_tier_id:
        tier = db.exec(
            select(SubscriptionTier).where(
                SubscriptionTier.tier_id == override.override_tier_id
            )
        ).first()
        if tier:
            return tier

    # Fall back to tenant's current_subscription_tier_id
    tenant = db.exec(select(Tenant).where(Tenant.id == tenant_id)).first()
    if tenant and tenant.current_subscription_tier_id:
        tier = db.exec(
            select(SubscriptionTier).where(
                SubscriptionTier.tier_id == tenant.current_subscription_tier_id
            )
        ).first()
        if tier:
            return tier

    # Should never reach here if data integrity is maintained
    raise RuntimeError(f"No effective subscription tier found for tenant {tenant_id}")


def get_effective_schedule_lanes(tenant_id: UUID, db: Session) -> int:
    """
    Returns effective lane count for tenant:
      1. Check tenant_product_feature_override for 'schedule_lanes' (add-ons)
      2. Fall back to active plan's ppfv limit_quantity

    Raises ValueError if no lane config found (misconfigured plan).

    MKT-B11: Replaces old dispatch_slots enforcement.
    """
    from sqlalchemy import text

    # Priority 1: tenant-specific override (purchased add-on lanes)
    override = db.exec(
        select(TenantProductFeatureOverride).where(
            TenantProductFeatureOverride.tenant_id == tenant_id,
            TenantProductFeatureOverride.product_feature_code == "schedule_lanes",
            TenantProductFeatureOverride.enabled == True,
        )
    ).first()
    if override and override.limit_quantity is not None:
        return override.limit_quantity

    # Priority 2: plan ppfv limit (join active subscription → ppfv)
    result = db.exec(
        select(ProductPlanProductFeatureVersion.limit_quantity)
        .join(
            Subscription,
            Subscription.product_plan_code
            == ProductPlanProductFeatureVersion.product_plan_code,
        )
        .where(
            Subscription.tenant_id == tenant_id,
            Subscription.is_active == True,
            ProductPlanProductFeatureVersion.product_feature_code == "schedule_lanes",
            text(
                "product_plan_product_feature_version.valid_period @> now()::timestamptz"
            ),
        )
    ).first()

    if result is None:
        raise ValueError(
            f"No schedule_lanes configuration found for tenant {tenant_id}"
        )
    return result


def check_user_add_allowed(db: Session, tenant_id: UUID) -> tuple[bool, dict]:
    """
    MKT-B11: Unlimited users is a permanent invariant.
    Always returns (True, {}) — max_users column was dropped in v3.0.

    Retained for backward compatibility with invitation routes and existing tests
    that call this function. Callers can rely on this always allowing user adds.
    """
    return True, {}


def _get_current_usage(db: Session, tenant_id: UUID) -> TenantSubscriptionUsage | None:
    """Return the current billing period usage row (period_end >= now())."""
    now = datetime.now(UTC)
    return db.exec(
        select(TenantSubscriptionUsage)
        .where(TenantSubscriptionUsage.tenant_id == tenant_id)
        .where(TenantSubscriptionUsage.period_end >= now)
        .order_by(TenantSubscriptionUsage.period_end)
        .limit(1)
    ).first()


def increment_user_count(db: Session, tenant_id: UUID) -> None:
    """
    Increment current_user_count in tenant_subscription_usage for current period.
    Called after a successful user invitation acceptance.
    Creates a usage row if one doesn't exist for the current period.

    MKT-B11: User count tracking is retained for analytics even though enforcement
    is removed (unlimited users invariant).
    """
    usage = _get_current_usage(db, tenant_id)

    if usage:
        usage.current_user_count = max(0, usage.current_user_count + 1)
        db.add(usage)
        db.commit()
    else:
        # Create initial usage row for current period (monthly aligned)
        now = datetime.now(UTC)
        period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        # End of month
        if period_start.month == 12:
            period_end = period_start.replace(year=period_start.year + 1, month=1)
        else:
            period_end = period_start.replace(month=period_start.month + 1)

        new_usage = TenantSubscriptionUsage(
            tenant_id=tenant_id,
            period_start=period_start,
            period_end=period_end,
            current_user_count=1,
            current_sms_segment_count=0,
        )
        db.add(new_usage)
        db.commit()


def decrement_user_count(db: Session, tenant_id: UUID) -> None:
    """
    Decrement current_user_count in tenant_subscription_usage for current period.
    Floor: 0. Called after a user is deactivated/removed.

    MKT-B11: User count tracking is retained for analytics even though enforcement
    is removed (unlimited users invariant).
    """
    usage = _get_current_usage(db, tenant_id)

    if usage and usage.current_user_count > 0:
        usage.current_user_count = usage.current_user_count - 1
        db.add(usage)
        db.commit()
