"""C-B11 — Operator Cohort Dashboard routes.

Platform-level endpoints (not tenant-scoped).  Uses get_platform_user() for
auth on the cohort endpoints, and a dual-auth fallback for /auth/me.

Endpoints:
    GET  /api/v1/operator/cohort                  — cohort overview
    POST /api/v1/operator/cohort/{tenant_id}/extend — silent free-period extension
    POST /api/v1/operator/cohort/close            — cohort close
    GET  /api/v1/auth/me                          — login routing discriminator
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session

from api.schemas.cohort import (
    AuthMeResponse,
    CloseCohortResponse,
    CohortOverviewResponse,
    ExtendFreePeriodRequest,
    ExtendFreePeriodResponse,
)
from core.auth import PlatformUser, get_current_user, get_platform_user
from core.db import get_db, set_audit_context_sync
from services.cohort_dashboard import (
    close_cohort,
    extend_free_period,
    get_cohort_overview,
)

security = HTTPBearer()
router = APIRouter(prefix="/api/v1/operator", tags=["operator"])


# ─────────────────────────────────────────────────────────────────────────────
# Cohort dashboard endpoints (platform auth)
# ─────────────────────────────────────────────────────────────────────────────


@router.get("/cohort", response_model=CohortOverviewResponse)
def get_cohort(
    platform_user: PlatformUser = Depends(get_platform_user),
    db: Session = Depends(get_db),
):
    """Get the Charter cohort overview — all members with tripwire alerts.

    Requires: platform_role.permissions.read_all == true
    """
    if not platform_user.can_read_all():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "type": "https://errors.pilotfortrades.com/forbidden",
                "title": "Insufficient permissions",
                "status": 403,
                "detail": "Platform role does not have read_all permission.",
            },
        )

    return get_cohort_overview(db)


@router.post("/cohort/{tenant_id}/extend", response_model=ExtendFreePeriodResponse)
def extend_member_free_period(
    tenant_id: uuid.UUID,
    request: ExtendFreePeriodRequest,
    platform_user: PlatformUser = Depends(get_platform_user),
    db: Session = Depends(get_db),
):
    """Silently extend a Charter member's free period (D16).

    Requires: platform_role.permissions.write contains 'tenants' or 'billing'.
    Rejects if Stripe subscription is not 'trialing'.
    """
    if not (platform_user.can_write("tenants") or platform_user.can_write("billing")):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "type": "https://errors.pilotfortrades.com/forbidden",
                "title": "Insufficient permissions",
                "status": 403,
                "detail": "Platform role does not have write permission for "
                "'tenants' or 'billing'.",
            },
        )

    set_audit_context_sync(db, user_id=platform_user.id)

    try:
        result = extend_free_period(
            db=db,
            tenant_id=tenant_id,
            new_end_date=request.new_free_period_ends_at,
            reason=request.override_reason,
            operator_user_id=platform_user.id,
        )
    except ValueError as exc:
        msg = str(exc)
        if "not found" in msg.lower() or "not a charter" in msg.lower():
            code = status.HTTP_404_NOT_FOUND
        elif "must be after" in msg.lower():
            code = status.HTTP_422_UNPROCESSABLE_CONTENT
        elif "must be 'trialing'" in msg.lower() or "resume flow" in msg.lower():
            code = status.HTTP_409_CONFLICT
        else:
            code = status.HTTP_400_BAD_REQUEST

        raise HTTPException(
            status_code=code,
            detail={
                "type": "https://errors.pilotfortrades.com/cohort-extension-error",
                "title": "Free period extension failed",
                "status": code,
                "detail": msg,
            },
        )

    result["tenant_id"] = tenant_id
    return result


@router.post("/cohort/close", response_model=CloseCohortResponse)
def close_charter_cohort(
    platform_user: PlatformUser = Depends(get_platform_user),
    db: Session = Depends(get_db),
):
    """Close the Charter cohort — archive price, deactivate tier, activate others.

    Requires: platform_role.permissions.write contains 'billing'.
    """
    if not platform_user.can_write("billing"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "type": "https://errors.pilotfortrades.com/forbidden",
                "title": "Insufficient permissions",
                "status": 403,
                "detail": "Platform role does not have write permission for 'billing'.",
            },
        )

    set_audit_context_sync(db, user_id=platform_user.id)

    try:
        return close_cohort(db=db, operator_user_id=platform_user.id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "type": "https://errors.pilotfortrades.com/cohort-close-error",
                "title": "Cohort close failed",
                "status": 409,
                "detail": str(exc),
            },
        )


# ─────────────────────────────────────────────────────────────────────────────
# Auth Me endpoint (dual-auth: tenant first, platform fallback)
# ─────────────────────────────────────────────────────────────────────────────


@router.get("/auth/me", response_model=AuthMeResponse, tags=["auth"])
def get_auth_me(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    """Return user type + redirect target after login.

    Tries tenant auth first; on 403 (no tenant_user row) falls back to
    platform auth.  Returns a discriminated union response so the frontend
    can route without a second API call.
    """
    try:
        tenant_user = get_current_user(request, credentials, db)
        return AuthMeResponse(
            user_type="tenant",
            user_id=tenant_user.id,
            email=tenant_user.user.email,
            first_name=tenant_user.user.first_name,
            last_name=tenant_user.user.last_name,
            tenant_id=tenant_user.tenant_id,
            role_code=tenant_user.role_code,
            redirect_to="/dashboard",
        )
    except HTTPException as exc:
        if exc.status_code != status.HTTP_403_FORBIDDEN:
            raise

        platform_user = get_platform_user(request, credentials, db)
        return AuthMeResponse(
            user_type="platform",
            user_id=platform_user.id,
            email=platform_user.user.email,
            first_name=platform_user.user.first_name,
            last_name=platform_user.user.last_name,
            platform_role_code=platform_user.platform_role_code,
            redirect_to="/operator/cohort",
        )
