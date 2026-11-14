"""
Billing rate resolution service for all metered features.

Implements the three-tier rate and cap lookup pattern (Tom's decision 2026-05-09):
1. Tenant product feature override (highest priority)
2. Product plan product feature version (plan-level rate)
3. Error if neither returns a value for billable features

No hardcoded rate constants anywhere in application code — all rates read from DB.
"""

import logging
from uuid import UUID

from sqlmodel import Session, select

logger = logging.getLogger(__name__)


class BillingConfigError(Exception):
    """Raised when rate configuration is missing or invalid."""

    pass


def resolve_overage_rate(
    db: Session,
    tenant_id: UUID,
    feature_code: str,
    plan_code: str | None = None,
) -> tuple[int, int | None]:
    """
    Resolve effective overage rate and cap for a feature at a tenant.

    Three-tier resolution (no fallback constants):
    1. tenant_product_feature_override (per-tenant custom deal)
    2. product_plan_product_feature_version (plan-standard rate)
    3. If both NULL → raise BillingConfigError

    Args:
        db: Database session
        tenant_id: Tenant making the query
        feature_code: Feature identifier (e.g., 'outbound_sms_segments', 'voice_ai_minutes')
        plan_code: Optional plan code (if not provided, must be passed or error raised)

    Returns:
        Tuple of (effective_rate_cents, effective_cap_or_None)
        - effective_rate_cents: int, cents per unit
        - effective_cap_or_None: Optional[int], total cap in cents per period, or None if uncapped

    Raises:
        BillingConfigError: If both override and plan rate are NULL (misconfigured)
    """
    from app.models.billing import (
        ProductPlanProductFeatureVersion,
        TenantProductFeatureOverride,
    )

    # Tier 1: Check tenant-specific override
    override = db.exec(
        select(TenantProductFeatureOverride).where(
            TenantProductFeatureOverride.tenant_id == tenant_id,
            TenantProductFeatureOverride.product_feature_code == feature_code,
        )
    ).first()

    if override and override.overage_price_cents is not None:
        # Override takes precedence; cap may also be set (or None = uncapped)
        return override.overage_price_cents, override.overage_cap_per_period

    # Tier 2: Look up plan-level rate (plan_code must be provided)
    if plan_code is None:
        raise BillingConfigError(
            f"plan_code required for feature {feature_code} (no tenant override found)"
        )

    plan_feature = db.exec(
        select(ProductPlanProductFeatureVersion).where(
            ProductPlanProductFeatureVersion.product_plan_code == plan_code,
            ProductPlanProductFeatureVersion.product_feature_code == feature_code,
        )
    ).first()

    if plan_feature and plan_feature.overage_price_cents is not None:
        return (
            plan_feature.overage_price_cents,
            plan_feature.overage_cap_per_period,
        )

    # Tier 3: Not found anywhere — this is a configuration error
    raise BillingConfigError(
        f"overage_price_cents not configured for feature {feature_code} on plan {plan_code}"
    )


def resolve_cap_only(
    db: Session,
    tenant_id: UUID,
    feature_code: str,
    plan_code: str | None = None,
) -> int | None:
    """
    Resolve cap without rate (used for scenarios where rate is determined separately).

    Returns:
        Cap in cents per period, or None if uncapped.
    """
    from app.models.billing import (
        ProductPlanProductFeatureVersion,
        TenantProductFeatureOverride,
    )

    # Tier 1: tenant override
    override = db.exec(
        select(TenantProductFeatureOverride).where(
            TenantProductFeatureOverride.tenant_id == tenant_id,
            TenantProductFeatureOverride.product_feature_code == feature_code,
        )
    ).first()

    if override:
        return override.overage_cap_per_period

    # Tier 2: plan-level
    if plan_code:
        plan_feature = db.exec(
            select(ProductPlanProductFeatureVersion).where(
                ProductPlanProductFeatureVersion.product_plan_code == plan_code,
                ProductPlanProductFeatureVersion.product_feature_code == feature_code,
            )
        ).first()

        if plan_feature:
            return plan_feature.overage_cap_per_period

    return None
