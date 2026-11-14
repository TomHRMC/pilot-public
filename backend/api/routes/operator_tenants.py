"""C-B15 — Operator tenant list + impersonation start/end routes.

Platform-level endpoints (not tenant-scoped).  All use get_platform_user()
for auth.  Permission gates:
    - GET /tenants          → read_all
    - POST /impersonation/* → impersonate_tenant

Endpoints:
    GET  /api/v1/operator/tenants                — tenant selector source
    POST /api/v1/operator/impersonation/start    — begin impersonation session
    POST /api/v1/operator/impersonation/end      — end impersonation session
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from api.schemas.operator import (
    ImpersonationEndRequest,
    ImpersonationEndResponse,
    ImpersonationSessionResponse,
    ImpersonationStartRequest,
    OperatorTenantListResponse,
    OperatorTenantSummary,
)
from core.auth import PlatformUser, get_platform_user
from core.db import get_db, set_audit_context_sync
from services.impersonation_service import (
    end_impersonation,
    list_operator_tenants,
    start_impersonation,
)

router = APIRouter(prefix="/api/v1/operator", tags=["operator"])


def _forbidden(detail: str) -> HTTPException:
    """Build a RFC 7807 403 error."""
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={
            "type": "https://errors.pilotfortrades.com/forbidden",
            "title": "Insufficient permissions",
            "status": 403,
            "detail": detail,
        },
    )


@router.get("/tenants", response_model=OperatorTenantListResponse)
def list_tenants(
    platform_user: PlatformUser = Depends(get_platform_user),
    db: Session = Depends(get_db),
) -> OperatorTenantListResponse:
    """List all tenants for the operator selector — active first, then name ASC.

    Requires: platform_role.permissions.read_all == true
    """
    if not platform_user.can_read_all():
        raise _forbidden("Platform role does not have read_all permission.")

    tenants = list_operator_tenants(db)
    return OperatorTenantListResponse(
        tenants=[OperatorTenantSummary(**t) for t in tenants]
    )


@router.post(
    "/impersonation/start",
    response_model=ImpersonationSessionResponse,
    status_code=status.HTTP_200_OK,
)
def start_impersonation_endpoint(
    request: ImpersonationStartRequest,
    platform_user: PlatformUser = Depends(get_platform_user),
    db: Session = Depends(get_db),
) -> ImpersonationSessionResponse:
    """Begin an impersonation session as the target tenant's owner.

    Requires: platform_role.permissions.impersonate_tenant == true
    Validates: target tenant exists (404) and is_active=true (409).
    Audit-logs the 'start' event (actor_type='platform').
    """
    if platform_user.permissions.get("impersonate_tenant") is not True:
        raise _forbidden("Platform role does not have impersonate_tenant permission.")

    set_audit_context_sync(db, user_id=platform_user.id)

    try:
        result = start_impersonation(
            db,
            tenant_id=request.tenant_id,
            impersonator_user_id=platform_user.id,
            user_role=platform_user.platform_role_code,
        )
    except ValueError as exc:
        msg = str(exc)
        if "not found" in msg.lower():
            code = status.HTTP_404_NOT_FOUND
        elif "not active" in msg.lower():
            code = status.HTTP_409_CONFLICT
        else:
            code = status.HTTP_400_BAD_REQUEST
        raise HTTPException(
            status_code=code,
            detail={
                "type": "https://errors.pilotfortrades.com/impersonation-error",
                "title": "Impersonation start failed",
                "status": code,
                "detail": msg,
            },
        )

    return ImpersonationSessionResponse(**result)


@router.post(
    "/impersonation/end",
    response_model=ImpersonationEndResponse,
    status_code=status.HTTP_200_OK,
)
def end_impersonation_endpoint(
    request: ImpersonationEndRequest,
    platform_user: PlatformUser = Depends(get_platform_user),
    db: Session = Depends(get_db),
) -> ImpersonationEndResponse:
    """End an impersonation session. Always 200 even if no matching start row.

    Requires: platform_role.permissions.impersonate_tenant == true
    Audit-logs the 'end' event (actor_type='platform').
    """
    if platform_user.permissions.get("impersonate_tenant") is not True:
        raise _forbidden("Platform role does not have impersonate_tenant permission.")

    set_audit_context_sync(db, user_id=platform_user.id)

    end_impersonation(
        db,
        tenant_id=request.tenant_id,
        impersonator_user_id=platform_user.id,
        user_role=platform_user.platform_role_code,
    )
    return ImpersonationEndResponse(ended=True)
