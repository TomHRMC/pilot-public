"""
Entitlement Service for Pilot for Trades  (Task 1-D-4)

Evaluates whether a tenant is allowed to use a given product feature by executing
the following priority chain:

  1. tenant_product_feature_override  — per-tenant admin toggle / custom limit
  2. Subscription.product_plan_code   — resolves the active billing plan
  3. product_plan_product_feature_version — plan-level limit (TSTZRANGE-scoped)
  4. subscription_usage               — current-period consumed quantity

A Redis cache wrapper (get_cached_entitlement) sits in front of every DB lookup.

Cache key   : entitlement:{tenant_id}:{feature_code}
TTL         : 300 s  (5 min)
Redis DB    : index 3  (isolated from rate-limit db=0, Celery db=1/2)

Related models:
  - TenantProductFeatureOverride  : backend/app/models/billing.py:730
  - Subscription                  : backend/app/models/billing.py:451
  - ProductPlanProductFeatureVersion : backend/app/models/billing.py:693
  - SubscriptionUsage             : backend/app/models/billing.py:759
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from datetime import date

from pydantic import BaseModel
from sqlalchemy import text
from sqlmodel import Session, select

from app.models.billing import (
    ProductPlanProductFeatureVersion,
    Subscription,
    SubscriptionUsage,
    TenantProductFeatureOverride,
)

logger = logging.getLogger(__name__)

# ── Cache constants ──────────────────────────────────────────────────────────
_ENTITLEMENT_REDIS_DB: int = 3  # isolated index
_CACHE_TTL: int = 300  # seconds
_CACHE_KEY_PREFIX: str = "entitlement"


# ── Output schema ────────────────────────────────────────────────────────────


class EntitlementResult(BaseModel):
    """Structured result returned by every entitlement check."""

    is_allowed: bool
    limit: int | None = None  # None = unlimited
    used: int = 0
    reason: str = ""


# ── Task 1: Core business-logic function ────────────────────────────────────


def check_entitlement(
    tenant_id: uuid.UUID,
    feature_code: str,
    db: Session,
) -> EntitlementResult:
    """
    Execute the full entitlement decision tree against PostgreSQL.

    Logic:
      1. Override table — if enabled=False → blocked immediately.
         If a custom limit_quantity is set, use it (skip plan lookup).
      2. No override → find the tenant's active Subscription.
      3. Query ProductPlanProductFeatureVersion for plan/feature where
         valid_period @> now().  Absent → blocked.
      4. If limit_quantity is set, query SubscriptionUsage for the billing
         period that contains today.
      5. used_quantity >= limit_quantity → blocked.

    Args:
        tenant_id    : Tenant UUID
        feature_code : Product feature code (e.g. "schedule_lanes")
        db           : Active SQLModel session

    Returns:
        EntitlementResult(is_allowed, limit, used, reason)
    """
    today = date.today()

    # ── 1. Tenant-level override (highest priority) ─────────────────────────
    override = db.exec(
        select(TenantProductFeatureOverride).where(
            TenantProductFeatureOverride.tenant_id == tenant_id,
            TenantProductFeatureOverride.product_feature_code == feature_code,
        )
    ).first()

    if override is not None:
        if not override.enabled:
            return EntitlementResult(
                is_allowed=False,
                reason="feature_disabled_by_override",
            )

        if override.limit_quantity is not None:
            used = _get_current_usage(tenant_id, feature_code, today, db)
            if used >= override.limit_quantity:
                return EntitlementResult(
                    is_allowed=False,
                    limit=override.limit_quantity,
                    used=used,
                    reason="usage_limit_exceeded",
                )
            return EntitlementResult(
                is_allowed=True,
                limit=override.limit_quantity,
                used=used,
                reason="override_limit_ok",
            )

        # Override present & enabled, no quantity cap → unlimited access
        return EntitlementResult(
            is_allowed=True,
            limit=None,
            used=0,
            reason="override_unlimited",
        )

    # ── 2. Resolve active subscription ──────────────────────────────────────
    subscription = db.exec(
        select(Subscription).where(
            Subscription.tenant_id == tenant_id,
            Subscription.is_active == True,
        )
    ).first()

    if not subscription:
        return EntitlementResult(
            is_allowed=False,
            reason="no_active_subscription",
        )

    # ── 3. Resolve plan-feature version (must be valid today) ───────────────
    feature_version = db.exec(
        select(ProductPlanProductFeatureVersion).where(
            ProductPlanProductFeatureVersion.product_plan_code
            == subscription.product_plan_code,
            ProductPlanProductFeatureVersion.product_feature_code == feature_code,
            text(
                "product_plan_product_feature_version.valid_period @> now()::timestamptz"
            ),
        )
    ).first()

    if not feature_version:
        return EntitlementResult(
            is_allowed=False,
            reason="feature_not_in_plan",
        )

    plan_limit = feature_version.limit_quantity

    # ── 4 & 5. Compare usage to limit ───────────────────────────────────────
    if plan_limit is None:
        return EntitlementResult(
            is_allowed=True,
            limit=None,
            used=0,
            reason="plan_unlimited",
        )

    used = _get_current_usage(tenant_id, feature_code, today, db)

    if used >= plan_limit:
        return EntitlementResult(
            is_allowed=False,
            limit=plan_limit,
            used=used,
            reason="usage_limit_exceeded",
        )

    return EntitlementResult(
        is_allowed=True,
        limit=plan_limit,
        used=used,
        reason="within_plan_limit",
    )


def _get_current_usage(
    tenant_id: uuid.UUID,
    feature_code: str,
    today: date,
    db: Session,
) -> int:
    """
    Return used_quantity from subscription_usage for the billing period that
    contains today.  Returns 0 when no row exists (never-used feature).
    """
    usage_row = db.exec(
        select(SubscriptionUsage).where(
            SubscriptionUsage.tenant_id == tenant_id,
            SubscriptionUsage.product_feature_code == feature_code,
            SubscriptionUsage.period_start <= today,
            SubscriptionUsage.period_end >= today,
        )
    ).first()

    return usage_row.used_quantity if usage_row else 0


# ── C-B7: Subscription billing-active gate ───────────────────────────────────


def is_subscription_billing_active(db: Session, tenant_id: uuid.UUID) -> bool:
    """
    Check whether the tenant's subscription is billing-active.

    Returns False when the subscription status is 'paused', 'unpaid', or
    'canceled' (is_billing_active=false). Returns True for 'active',
    'trialing', 'past_due'.

    When False, ALL services are blocked — including SMS. The tenant is not
    paying for their subscription, and allowing SMS creates costs Pilot is
    liable for. Spec §9.3 SMS exception was overridden by Tom (2026-08-05):
    when paused → everything blocked, including SMS. No exceptions.

    Args:
        db        : Active SQLModel session.
        tenant_id : Tenant UUID.

    Returns:
        True if subscription is billing-active, False otherwise.
    """
    from app.models.billing import Subscription, SubscriptionStatus

    sub = db.exec(
        select(Subscription).where(
            Subscription.tenant_id == tenant_id,
            Subscription.is_active == True,
        )
    ).first()

    if not sub:
        return False

    status = db.exec(
        select(SubscriptionStatus).where(SubscriptionStatus.id == sub.status_id)
    ).first()

    if not status:
        return False

    return bool(status.is_billing_active)


# ── Task 2: Redis cache wrapper ──────────────────────────────────────────────


def _get_redis_client():
    """
    Return a redis-py client pointed at the entitlement cache database (db=3).

    Derives the Redis URL from CELERY_BROKER_URL so we share the same
    ElastiCache instance without a new config variable.
    """
    import redis  # type: ignore[import]

    from core.config import settings

    base_url = settings.CELERY_BROKER_URL
    # Replace the trailing db-index path segment (e.g. /1 → /3)
    redis_url = re.sub(r"/\d+$", f"/{_ENTITLEMENT_REDIS_DB}", base_url)
    return redis.from_url(redis_url, encoding="utf-8", decode_responses=True)


def get_cached_entitlement(
    tenant_id: uuid.UUID,
    feature_code: str,
    db: Session,
) -> EntitlementResult:
    """
    Cache-aware entitlement check.

    Flow:
      1. Build cache_key = "entitlement:{tenant_id}:{feature_code}"
      2. Try GET from Redis → deserialise and return on HIT.
      3. On MISS (or Redis unavailable): call check_entitlement(), store
         the JSON result in Redis with TTL=300s, and return it.

    Redis failures are swallowed with a warning so that entitlement checks
    degrade gracefully to direct DB reads (fail-open for availability).

    Args:
        tenant_id    : Tenant UUID
        feature_code : Product feature code
        db           : SQLModel session (only used on cache miss)

    Returns:
        EntitlementResult
    """
    cache_key = f"{_CACHE_KEY_PREFIX}:{tenant_id}:{feature_code}"

    # ── Cache read ───────────────────────────────────────────────────────────
    try:
        client = _get_redis_client()
        raw = client.get(cache_key)
        if raw is not None:
            logger.debug("Entitlement cache HIT  key=%s", cache_key)
            return EntitlementResult(**json.loads(raw))
    except Exception as exc:
        logger.warning("Entitlement cache GET error key=%s err=%s", cache_key, exc)

    # ── Cache miss → DB ──────────────────────────────────────────────────────
    logger.debug("Entitlement cache MISS key=%s", cache_key)
    result = check_entitlement(tenant_id, feature_code, db)

    # ── Cache write ──────────────────────────────────────────────────────────
    try:
        client = _get_redis_client()
        client.setex(cache_key, _CACHE_TTL, result.model_dump_json())
    except Exception as exc:
        logger.warning("Entitlement cache SET error key=%s err=%s", cache_key, exc)

    return result


def invalidate_entitlement_cache(
    tenant_id: uuid.UUID,
    feature_code: str | None = None,
) -> None:
    """
    Delete cached entitlement result(s) for a tenant.

    Args:
        tenant_id    : Tenant UUID
        feature_code : Specific feature to clear; omit to clear ALL features
                       for this tenant.
    """
    try:
        client = _get_redis_client()
        if feature_code:
            client.delete(f"{_CACHE_KEY_PREFIX}:{tenant_id}:{feature_code}")
        else:
            pattern = f"{_CACHE_KEY_PREFIX}:{tenant_id}:*"
            keys = client.keys(pattern)
            if keys:
                client.delete(*keys)
    except Exception as exc:
        logger.warning("Entitlement cache invalidation error: %s", exc)


# ── Public API ───────────────────────────────────────────────────────────────
__all__ = [
    "EntitlementResult",
    "check_entitlement",
    "get_cached_entitlement",
    "invalidate_entitlement_cache",
    "is_subscription_billing_active",
]
