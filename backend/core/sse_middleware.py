"""
SSE Middleware — B3/A19 Canonical Pattern.

Provides JWT validation for SSE connections (which must pass auth token
as query parameter since browser EventSource cannot set headers).

Established here in B3; reused by B6, B8, B11.

Usage in route:
    from core.sse_middleware import validate_sse_token

    @router.get("/board/stream")
    async def board_stream(
        token: str = Query(..., description="JWT token for SSE auth"),
        db: Session = Depends(get_db),
        ...
    ):
        user = validate_sse_token(token, db)
        ...
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from fastapi import HTTPException, status
from sqlmodel import Session, select

if TYPE_CHECKING:
    from core.auth import AuthenticatedUser

logger = logging.getLogger(__name__)


def validate_sse_token(token: str, db: Session) -> AuthenticatedUser:
    """Validate a JWT token passed as a query parameter for SSE connections.

    SSE browser clients cannot set Authorization headers on the initial
    EventSource handshake. The JWT is passed as ?token= and validated
    synchronously before the async generator starts.

    Replicates the core logic of core.auth.get_current_user() without
    requiring a FastAPI Request object.

    Args:
        token: Raw JWT string from query parameter.
        db:    Open SQLModel session for user/tenant lookup.
    Returns:
        AuthenticatedUser — authenticated user context with tenant_id and permissions.
    Raises:
        HTTPException 401: if token is invalid or expired.
        HTTPException 403: if user is not in any active tenant or role not found.
        HTTPException 404: if user not found.
    """
    from app.models.auth import TenantUser, TenantUserRole
    from app.models.core import User
    from core.auth import AuthenticatedUser, verify_cognito_jwt

    # Validate JWT
    try:
        payload = verify_cognito_jwt(token)
    except Exception as exc:
        logger.warning("sse_middleware.validate_sse_token: JWT invalid: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "type": "https://pilotfortrades.com/errors/unauthorized",
                "title": "Unauthorized",
                "status": 401,
                "detail": "Invalid or expired SSE authentication token.",
            },
        )

    email = payload.get("email")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="SSE token does not contain email claim.",
        )

    # Lookup user
    user = db.exec(
        select(User).where(User.email == email).where(User.is_active == True)
    ).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found."
        )

    # Lookup tenant membership
    tenant_user = db.exec(
        select(TenantUser)
        .where(TenantUser.user_id == user.id)
        .where(TenantUser.is_active == True)
    ).first()
    if not tenant_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not belong to any active tenant.",
        )

    # Lookup role + permissions
    role = db.exec(
        select(TenantUserRole)
        .where(TenantUserRole.code == tenant_user.role_code)
        .where(TenantUserRole.is_active == True)
    ).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User role '{tenant_user.role_code}' not found or inactive.",
        )

    permissions = role.permissions if isinstance(role.permissions, list) else []

    return AuthenticatedUser(
        user=user,
        tenant_id=tenant_user.tenant_id,
        role_code=role.code,
        permissions=permissions,
    )
