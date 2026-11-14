"""
Task 1-E-1: Admin Tenant Feature Override API

Provides platform-admin endpoints for reading and writing per-tenant product-feature
overrides (tenant_product_feature_override table). When an override is written, the
corresponding Redis entitlement cache key is deleted so new limits take effect immediately.

Routes
------
GET  /api/v1/admin/tenants/{tenant_id}/overrides/test   — unauthenticated (test env only)
GET  /api/v1/admin/tenants/{tenant_id}/overrides        — requires "tenants.manage"
POST /api/v1/admin/tenants/{tenant_id}/overrides/test   — unauthenticated (test env only)
POST /api/v1/admin/tenants/{tenant_id}/overrides        — requires "tenants.manage"

Permission: "tenants.manage"
  - Platform `owner` and `support` roles must hold this permission.
  - Tenant-level users (technician, office_staff, accountant) do NOT hold it.

Cache invalidation
  On every upsert: DELETE entitlement:{tenant_id}:{product_feature_code}

Reference: dev-docs/analysis/db-schema-domain-mvp-features-impl-plan.md Task 1-E-1
"""

import logging
import re
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlmodel import Session, select

from api.schemas.schemas import TenantOverrideCreate, TenantOverrideResponse
from app.models.billing import TenantProductFeatureOverride
from core.auth import AuthenticatedUser
from core.db import get_db
from core.permissions import require_permission
from core.test_context import TestUserContext, get_test_context

logger = logging.getLogger(__name__)

router = APIRouter()

# ── Cache constants (must match entitlement_service.py) ──────────────────────
_ENTITLEMENT_REDIS_DB: int = 3
_CACHE_KEY_PREFIX: str = "entitlement"


# ── Redis helper ─────────────────────────────────────────────────────────────


def _get_redis_client():
    """Return a redis-py client pointed at the entitlement cache database (db=3)."""
    import redis  # type: ignore[import]

    from core.config import settings

    base_url = settings.CELERY_BROKER_URL
    redis_url = re.sub(r"/\d+$", f"/{_ENTITLEMENT_REDIS_DB}", base_url)
    return redis.from_url(redis_url, encoding="utf-8", decode_responses=True)


# ── Core implementation functions ─────────────────────────────────────────────


def _get_overrides_impl(
    tenant_id: UUID, db: Session
) -> list[TenantProductFeatureOverride]:
    """
    Return all TenantProductFeatureOverride rows for the given tenant.

    Args:
        tenant_id: The tenant whose overrides to retrieve.
        db:        Active SQLModel session.

    Returns:
        List of TenantProductFeatureOverride ORM instances (may be empty).
    """
    return db.exec(
        select(TenantProductFeatureOverride).where(
            TenantProductFeatureOverride.tenant_id == tenant_id
        )
    ).all()


def _set_override_impl(
    tenant_id: UUID,
    data: TenantOverrideCreate,
    db: Session,
    user_context: "AuthenticatedUser | TestUserContext",
) -> TenantProductFeatureOverride:
    """
    Upsert a TenantProductFeatureOverride row and invalidate the entitlement cache.

    Logic:
      1. Query for an existing override on (tenant_id, product_feature_code).
      2. If found, update mutable fields in-place.
      3. If not found, create a new TenantProductFeatureOverride instance.
      4. db.add(), db.commit(), db.refresh().
      5. Delete the Redis cache key so the change takes effect immediately.

    Args:
        tenant_id:    Target tenant UUID.
        data:         Validated input payload.
        db:           Active SQLModel session.
        user_context: Authenticated user or test context (provides user ID for audit).

    Returns:
        The persisted (created or updated) TenantProductFeatureOverride row.
    """
    existing = db.exec(
        select(TenantProductFeatureOverride).where(
            TenantProductFeatureOverride.tenant_id == tenant_id,
            TenantProductFeatureOverride.product_feature_code
            == data.product_feature_code,
        )
    ).first()

    if existing:
        # Update mutable fields
        existing.limit_quantity = data.limit_quantity
        existing.included_quantity = data.included_quantity
        existing.overage_price_cents = data.overage_price_cents
        existing.overage_cap_per_period = data.overage_cap_per_period
        existing.alert_threshold_pct = data.alert_threshold_pct
        existing.enabled = data.enabled
        existing.updated_by = user_context.id
        override = existing
    else:
        override = TenantProductFeatureOverride(
            tenant_id=tenant_id,
            product_feature_code=data.product_feature_code,
            limit_quantity=data.limit_quantity,
            included_quantity=data.included_quantity,
            overage_price_cents=data.overage_price_cents,
            overage_cap_per_period=data.overage_cap_per_period,
            alert_threshold_pct=data.alert_threshold_pct,
            enabled=data.enabled,
            created_by=user_context.id,
            updated_by=user_context.id,
        )

    db.add(override)
    db.commit()
    db.refresh(override)

    # CRITICAL: invalidate entitlement cache so new limits take effect immediately
    cache_key = f"{_CACHE_KEY_PREFIX}:{tenant_id}:{data.product_feature_code}"
    try:
        client = _get_redis_client()
        client.delete(cache_key)
        logger.info("Entitlement cache invalidated: %s", cache_key)
    except Exception as exc:
        logger.warning(
            "Entitlement cache invalidation failed key=%s err=%s", cache_key, exc
        )

    return override


# ── Routes — /test endpoints MUST be registered BEFORE authenticated endpoints ─


@router.get(
    "/{tenant_id}/overrides/test",
    response_model=list[TenantOverrideResponse],
    summary="[TEST] List tenant feature overrides (no auth)",
    tags=["admin-tenants"],
)
def get_overrides_test(
    tenant_id: UUID,
    db: Session = Depends(get_db),
):
    """
    Test-only variant of GET /{tenant_id}/overrides.
    Requires TEST_ENDPOINT_ENABLED=true and ENVIRONMENT=dev|qa.
    """
    get_test_context()  # raises 403 if test endpoints are disabled
    overrides = _get_overrides_impl(tenant_id, db)
    return overrides


@router.get(
    "/{tenant_id}/overrides",
    response_model=list[TenantOverrideResponse],
    summary="List tenant feature overrides",
    tags=["admin-tenants"],
)
def get_overrides(
    tenant_id: UUID,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("tenants.manage")),
):
    """
    Return all product-feature overrides configured for a given tenant.
    Requires the `tenants.manage` permission (platform owner / support roles).
    """
    overrides = _get_overrides_impl(tenant_id, db)
    return overrides


@router.post(
    "/{tenant_id}/overrides/test",
    response_model=TenantOverrideResponse,
    status_code=status.HTTP_201_CREATED,
    summary="[TEST] Create/update tenant feature override (no auth)",
    tags=["admin-tenants"],
)
def set_override_test(
    tenant_id: UUID,
    data: TenantOverrideCreate,
    db: Session = Depends(get_db),
):
    """
    Test-only variant of POST /{tenant_id}/overrides.
    Requires TEST_ENDPOINT_ENABLED=true and ENVIRONMENT=dev|qa.
    """
    test_context = get_test_context()  # raises 403 if test endpoints are disabled
    override = _set_override_impl(tenant_id, data, db, test_context)
    return override


@router.post(
    "/{tenant_id}/overrides",
    response_model=TenantOverrideResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create or update a tenant feature override",
    tags=["admin-tenants"],
)
def set_override(
    tenant_id: UUID,
    data: TenantOverrideCreate,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("tenants.manage")),
):
    """
    Upsert a per-tenant product-feature limit override.

    - If an override for (tenant_id, product_feature_code) already exists it is
      updated in-place (upsert — no IntegrityError).
    - The entitlement cache key is deleted so the change takes effect within the
      next request cycle (no 5-minute TTL lag).

    Requires the `tenants.manage` permission (platform owner / support roles only).
    Tenant-level users receive 403 Forbidden.
    """
    override = _set_override_impl(tenant_id, data, db, current_user)
    return override
