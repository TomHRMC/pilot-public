"""
TEAM-INVITE-1 — Team Invite API Routes.

Endpoints:
  POST /api/v1/users/invites              — Create + send invite (users.manage)
  GET  /api/v1/users/invites              — List tenant invites (users.view)
  POST /api/v1/users/invites/{id}/resend  — Resend invite (users.manage)
  POST /api/v1/users/invites/{id}/revoke  — Revoke invite (users.manage)
  GET  /api/v1/invites/{token}            — Public token validation (no auth)

All authenticated POSTs require an Idempotency-Key header (24h replay cache
via core/idempotency.py middleware). /test twins tolerate missing header.

Design: dev-docs/architecture-design/batch-designs/batch-team-invite-1-design.md §D
"""

import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlmodel import Session, select

from api.schemas.team_invites import (
    TeamInviteCreateRequest,
    TeamInviteListItem,
    TeamInvitePublicResponse,
    TeamInviteResendResponse,
    TeamInviteResponse,
    TeamInviteRevokeResponse,
)
from app.models.core import Tenant
from core.auth import AuthenticatedUser
from core.db import get_db, set_audit_context_sync
from core.permissions import require_permission
from core.rate_limit import limiter
from core.test_context import TestUserContext, get_test_context
from services.team_invite_service import (
    InvitePendingExistsError,
    TeamInviteError,
    compute_invite_status,
    get_public_invite_data,
)
from services.team_invite_service import (
    create_invite as _create_invite_svc,
)
from services.team_invite_service import (
    list_invites as _list_invites_svc,
)
from services.team_invite_service import (
    resend_invite as _resend_invite_svc,
)
from services.team_invite_service import (
    revoke_invite as _revoke_invite_svc,
)

router = APIRouter(prefix="/api/v1", tags=["team-invites"])


# ==================== SHARED _impl() FUNCTIONS ====================


def _create_invite_impl(
    invite_req: TeamInviteCreateRequest,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> TeamInviteResponse:
    """Shared logic for creating an invite."""
    try:
        invite, _raw_token = _create_invite_svc(
            db,
            tenant_id=user_context.tenant_id,
            email=invite_req.email,
            role_code=invite_req.role_code,
            invited_by=user_context.id,
        )
    except TeamInviteError as e:
        raise _to_http_exception(e)

    return TeamInviteResponse(
        id=invite.id,
        email=invite.email,
        role_code=invite.role_code,
        expires_at=invite.expires_at,
        created_at=invite.created_at,
    )


def _list_invites_impl(
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> list[TeamInviteListItem]:
    """Shared logic for listing invites."""
    invites = _list_invites_svc(db, tenant_id=user_context.tenant_id)
    return [
        TeamInviteListItem(
            id=inv.id,
            email=inv.email,
            role_code=inv.role_code,
            invited_by=inv.invited_by,
            created_at=inv.created_at,
            expires_at=inv.expires_at,
            accepted_at=inv.accepted_at,
            is_active=inv.is_active,
            status=compute_invite_status(inv),
        )
        for inv in invites
    ]


def _resend_invite_impl(
    invite_id: uuid.UUID,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> TeamInviteResendResponse:
    """Shared logic for resending an invite."""
    try:
        invite, _raw_token = _resend_invite_svc(
            db, tenant_id=user_context.tenant_id, invite_id=invite_id
        )
    except TeamInviteError as e:
        raise _to_http_exception(e)

    return TeamInviteResendResponse(
        id=invite.id,
        email=invite.email,
        expires_at=invite.expires_at,
    )


def _revoke_invite_impl(
    invite_id: uuid.UUID,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> TeamInviteRevokeResponse:
    """Shared logic for revoking an invite."""
    try:
        invite = _revoke_invite_svc(
            db, tenant_id=user_context.tenant_id, invite_id=invite_id
        )
    except TeamInviteError as e:
        raise _to_http_exception(e)

    return TeamInviteRevokeResponse(id=invite.id, is_active=invite.is_active)


def _get_public_invite_impl(
    raw_token: str,
    db: Session,
) -> TeamInvitePublicResponse:
    """Shared logic for the public invite lookup."""
    invite = get_public_invite_data(db, raw_token=raw_token)
    if not invite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "type": "https://errors.pilotfortrades.com/invite_invalid",
                "title": "Invite not valid",
                "status": 404,
                "detail": "This invite link is no longer valid.",
            },
        )

    tenant = db.exec(select(Tenant).where(Tenant.id == invite.tenant_id)).first()
    tenant_name = tenant.name if tenant else "Pilot for Trades"

    return TeamInvitePublicResponse(
        tenant_name=tenant_name,
        email=invite.email,
        role_code=invite.role_code,
        expires_at=invite.expires_at,
    )


def _to_http_exception(e: TeamInviteError) -> HTTPException:
    """Map a TeamInviteError to an RFC 7807 HTTPException."""
    error_type_map = {
        "invalid_role": "https://errors.pilotfortrades.com/invalid-role",
        "invite_user_exists": "https://errors.pilotfortrades.com/invite_user_exists",
        "invite_pending_exists": "https://errors.pilotfortrades.com/invite_pending_exists",
        "invite_not_found": "https://errors.pilotfortrades.com/not-found",
        "invite_already_accepted": "https://errors.pilotfortrades.com/conflict",
        "invite_revoked": "https://errors.pilotfortrades.com/conflict",
    }
    detail = {
        "type": error_type_map.get(
            e.error_code, "https://errors.pilotfortrades.com/error"
        ),
        "title": e.message,
        "status": e.status_code,
        "detail": e.message,
    }
    # Carry the existing invite id for invite_pending_exists
    if isinstance(e, InvitePendingExistsError):
        detail["invite_id"] = str(e.invite_id)

    return HTTPException(status_code=e.status_code, detail=detail)


# ==================== TEST ENDPOINTS (register BEFORE authenticated) ====================


@router.post(
    "/users/invites/test",
    response_model=TeamInviteResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_invite_test(
    invite_req: TeamInviteCreateRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
) -> TeamInviteResponse:
    """Create a team invite (TEST ENDPOINT — no auth required)."""
    test_context = get_test_context()
    set_audit_context_sync(db, user_id=test_context.id)
    return _create_invite_impl(invite_req, db, test_context)


@router.get("/users/invites/test", response_model=list[TeamInviteListItem])
def list_invites_test(
    db: Session = Depends(get_db),
) -> list[TeamInviteListItem]:
    """List team invites (TEST ENDPOINT — no auth required)."""
    test_context = get_test_context()
    return _list_invites_impl(db, test_context)


@router.post(
    "/users/invites/{invite_id}/resend/test",
    response_model=TeamInviteResendResponse,
)
def resend_invite_test(
    invite_id: uuid.UUID,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
) -> TeamInviteResendResponse:
    """Resend a team invite (TEST ENDPOINT — no auth required)."""
    test_context = get_test_context()
    set_audit_context_sync(db, user_id=test_context.id)
    return _resend_invite_impl(invite_id, db, test_context)


@router.post(
    "/users/invites/{invite_id}/revoke/test",
    response_model=TeamInviteRevokeResponse,
)
def revoke_invite_test(
    invite_id: uuid.UUID,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
) -> TeamInviteRevokeResponse:
    """Revoke a team invite (TEST ENDPOINT — no auth required)."""
    test_context = get_test_context()
    set_audit_context_sync(db, user_id=test_context.id)
    return _revoke_invite_impl(invite_id, db, test_context)


# ==================== AUTHENTICATED ENDPOINTS ====================


@router.post(
    "/users/invites",
    response_model=TeamInviteResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_invite(
    invite_req: TeamInviteCreateRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("users.manage")),
) -> TeamInviteResponse:
    """Create + send a team invite. RBAC: users.manage.

    Requires Idempotency-Key header (24h replay cache via middleware).
    """
    if not idempotency_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "type": "https://errors.pilotfortrades.com/missing-header",
                "title": "Missing Idempotency-Key",
                "status": 400,
                "detail": "Idempotency-Key header is required for invite creation.",
            },
        )
    set_audit_context_sync(db, user_id=current_user.id)
    return _create_invite_impl(invite_req, db, current_user)


@router.get("/users/invites", response_model=list[TeamInviteListItem])
def list_invites(
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("users.view")),
) -> list[TeamInviteListItem]:
    """List all invites for the current tenant. RBAC: users.view."""
    return _list_invites_impl(db, current_user)


@router.post(
    "/users/invites/{invite_id}/resend",
    response_model=TeamInviteResendResponse,
)
def resend_invite(
    invite_id: uuid.UUID,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("users.manage")),
) -> TeamInviteResendResponse:
    """Resend a team invite (rotate token + reset expiry). RBAC: users.manage."""
    if not idempotency_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "type": "https://errors.pilotfortrades.com/missing-header",
                "title": "Missing Idempotency-Key",
                "status": 400,
                "detail": "Idempotency-Key header is required for invite resend.",
            },
        )
    set_audit_context_sync(db, user_id=current_user.id)
    return _resend_invite_impl(invite_id, db, current_user)


@router.post(
    "/users/invites/{invite_id}/revoke",
    response_model=TeamInviteRevokeResponse,
)
def revoke_invite(
    invite_id: uuid.UUID,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("users.manage")),
) -> TeamInviteRevokeResponse:
    """Revoke a team invite. RBAC: users.manage."""
    if not idempotency_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "type": "https://errors.pilotfortrades.com/missing-header",
                "title": "Missing Idempotency-Key",
                "status": 400,
                "detail": "Idempotency-Key header is required for invite revocation.",
            },
        )
    set_audit_context_sync(db, user_id=current_user.id)
    return _revoke_invite_impl(invite_id, db, current_user)


# ==================== PUBLIC ENDPOINT (no auth) ====================


@router.get(
    "/invites/{token}",
    response_model=TeamInvitePublicResponse,
    tags=["public"],
)
@limiter.limit("10/minute")
def get_public_invite(
    request: Request,
    token: str,
    db: Session = Depends(get_db),
) -> TeamInvitePublicResponse:
    """Public endpoint — validate an invite token for the landing page.

    Uniform 404 for every failure mode (unknown/expired/accepted/revoked) —
    no enumeration oracle (design §G.9).
    """
    return _get_public_invite_impl(token, db)


__all__ = ["router"]
