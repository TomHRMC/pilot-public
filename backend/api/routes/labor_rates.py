"""
A91 — Labor Rate Version Management Endpoints

Provides tenant-scoped catalog endpoints for managing labor rates by skill level.
Mirrors the temporal versioning pattern of A90 (TenantMarkupVersion).
"""

import logging
from datetime import UTC
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, desc, func, select, text

from app.models.catalog import LaborRateVersion
from core.auth import AuthenticatedUser
from core.db import get_db
from core.permissions import require_permission
from core.test_context import TestUserContext, get_test_context

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================================================
# Pydantic Schemas
# ============================================================================


class LaborRateVersionCreate:
    """Request schema for POST /api/v1/settings/labor-rates"""

    skill_level_code: str
    hourly_rate_cents: int  # must be > 0
    burden_pct: Decimal  # 0.0 to 9.9999
    effective_from: str | None = None  # ISO datetime; defaults to now()


class LaborRateVersionRead:
    """Response schema for labor rate endpoints"""

    id: int
    skill_level_code: str
    hourly_rate_cents: int
    burden_pct: Decimal
    burdened_rate_cents: int  # computed: hourly_rate_cents * (1 + burden_pct)
    valid_period_lower: str  # ISO datetime
    valid_period_upper: str | None  # ISO datetime or null
    created_at: str  # ISO datetime
    created_by: UUID | None


# ============================================================================
# Helper Functions
# ============================================================================


def _parse_tstzrange(valid_period) -> tuple:
    """
    Extract lower and upper bounds from a psycopg2.extras.DateTimeTZRange object.
    Returns (lower_datetime, upper_datetime or None)
    """
    if valid_period is None:
        return None, None
    # valid_period has .lower and .upper attributes
    return valid_period.lower, valid_period.upper


def _row_to_response(row: LaborRateVersion) -> dict:
    """Convert a LaborRateVersion DB row to response dict."""
    lower, upper = _parse_tstzrange(row.valid_period)
    burdened = int(row.hourly_rate_cents * (1 + row.burden_pct))
    return {
        "id": row.id,
        "skill_level_code": row.skill_level_code,
        "hourly_rate_cents": row.hourly_rate_cents,
        "burden_pct": str(row.burden_pct),
        "burdened_rate_cents": burdened,
        "valid_period_lower": lower.isoformat() if lower else None,
        "valid_period_upper": upper.isoformat() if upper else None,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "created_by": row.created_by,
    }


# ============================================================================
# Shared _impl() Functions
# ============================================================================


def _get_active_labor_rates_impl(
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
    skill_level_code: str | None = None,
) -> list[dict]:
    """Shared logic for listing active labor rates."""
    query = (
        select(LaborRateVersion)
        .where(LaborRateVersion.tenant_id == user_context.tenant_id)
        .where(func.now().op("<@")(LaborRateVersion.valid_period))
    )
    if skill_level_code:
        query = query.where(LaborRateVersion.skill_level_code == skill_level_code)
    rows = db.exec(query).all()
    return [_row_to_response(row) for row in rows]


def _create_labor_rate_impl(
    payload: dict,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> dict:
    """Shared logic for creating/superseding a labor rate."""
    from datetime import datetime

    skill_code = payload.get("skill_level_code")
    hourly_rate = payload.get("hourly_rate_cents")
    burden = payload.get("burden_pct")
    effective_from_str = payload.get("effective_from")

    if not skill_code:
        raise HTTPException(status_code=400, detail="skill_level_code required")
    if not hourly_rate or hourly_rate <= 0:
        raise HTTPException(status_code=422, detail="hourly_rate_cents must be > 0")
    if burden is None or burden < 0 or burden > 9.9999:
        raise HTTPException(status_code=422, detail="burden_pct must be 0 to 9.9999")

    if effective_from_str:
        try:
            effective_from = datetime.fromisoformat(
                effective_from_str.replace("Z", "+00:00")
            )
        except (ValueError, AttributeError):
            raise HTTPException(
                status_code=422, detail="effective_from must be ISO 8601"
            )
    else:
        effective_from = datetime.now(UTC)

    try:
        current = db.exec(
            select(LaborRateVersion)
            .where(LaborRateVersion.tenant_id == user_context.tenant_id)
            .where(LaborRateVersion.skill_level_code == skill_code)
            .where(func.now().op("<@")(LaborRateVersion.valid_period))
        ).first()

        if current:
            lower, _ = _parse_tstzrange(current.valid_period)
            if lower and lower.replace(microsecond=0) == effective_from.replace(
                microsecond=0
            ):
                raise HTTPException(
                    status_code=409,
                    detail="effective_from cannot equal the current version's start date",
                )
            db.execute(
                text(
                    "UPDATE labor_rate_version "
                    "SET valid_period = tstzrange(lower(valid_period), :upper, '[)') "
                    "WHERE id = :id"
                ).bindparams(upper=effective_from, id=current.id)
            )

        new_row = LaborRateVersion(
            tenant_id=user_context.tenant_id,
            skill_level_code=skill_code,
            hourly_rate_cents=hourly_rate,
            burden_pct=burden,
            valid_period=f"[{effective_from.isoformat()},)",
            created_by=user_context.id,
        )
        db.add(new_row)
        db.commit()
        db.refresh(new_row)
        return _row_to_response(new_row)

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating labor rate: {e}")
        if "23P01" in str(e) or "exclusion violation" in str(e).lower():
            raise HTTPException(
                status_code=409,
                detail="Overlapping period for this skill level. Cannot supersede.",
            )
        raise HTTPException(status_code=500, detail=str(e))


def _get_labor_rate_history_impl(
    skill_level_code: str,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> list[dict]:
    """Shared logic for getting labor rate history for a skill level."""
    rows = db.exec(
        select(LaborRateVersion)
        .where(LaborRateVersion.tenant_id == user_context.tenant_id)
        .where(LaborRateVersion.skill_level_code == skill_level_code)
        .order_by(desc(LaborRateVersion.recorded_at))
    ).all()
    return [_row_to_response(row) for row in rows]


# ============================================================================
# TEST ENDPOINTS (register BEFORE authenticated)
# ============================================================================


@router.get(
    "/test",
    summary="Get active labor rates (TEST — no auth)",
    tags=["Labor Rates"],
)
def get_active_labor_rates_test(
    skill_level_code: str | None = None,
    db: Session = Depends(get_db),
) -> list[dict]:
    """TEST ENDPOINT — no authentication required."""
    test_context = get_test_context()
    return _get_active_labor_rates_impl(
        db, test_context, skill_level_code=skill_level_code
    )


@router.post(
    "/test",
    status_code=status.HTTP_201_CREATED,
    summary="Create or supersede a labor rate (TEST — no auth)",
    tags=["Labor Rates"],
)
def create_labor_rate_test(
    payload: dict,
    db: Session = Depends(get_db),
) -> dict:
    """TEST ENDPOINT — no authentication required."""
    test_context = get_test_context()
    return _create_labor_rate_impl(payload, db, test_context)


@router.get(
    "/{skill_level_code}/history/test",
    summary="Get historical labor rates for a skill level (TEST — no auth)",
    tags=["Labor Rates"],
)
def get_labor_rate_history_test(
    skill_level_code: str,
    db: Session = Depends(get_db),
) -> list[dict]:
    """TEST ENDPOINT — no authentication required."""
    test_context = get_test_context()
    return _get_labor_rate_history_impl(skill_level_code, db, test_context)


# ============================================================================
# Authenticated Endpoints (RBAC: catalog.manage)
# ============================================================================


@router.get(
    "",
    summary="Get active labor rates",
    tags=["Labor Rates"],
)
def get_active_labor_rates(
    skill_level_code: str | None = None,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("catalog.manage")),
) -> list[dict]:
    """Get active labor rates. RBAC: catalog.manage."""
    return _get_active_labor_rates_impl(
        db, current_user, skill_level_code=skill_level_code
    )


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Create or supersede a labor rate",
    tags=["Labor Rates"],
)
def create_labor_rate(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("catalog.manage")),
) -> dict:
    """Create or supersede a labor rate. RBAC: catalog.manage."""
    return _create_labor_rate_impl(payload, db, current_user)


@router.get(
    "/{skill_level_code}/history",
    summary="Get historical labor rates for a skill level",
    tags=["Labor Rates"],
)
def get_labor_rate_history(
    skill_level_code: str,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("catalog.manage")),
) -> list[dict]:
    """Get full labor rate history for a skill level. RBAC: catalog.manage."""
    return _get_labor_rate_history_impl(skill_level_code, db, current_user)
