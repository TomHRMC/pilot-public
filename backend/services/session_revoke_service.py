"""
Session revocation service for Pilot for Trades — B13/A70.

Provides shared revocation logic consumed by:
- DELETE /api/v1/users/me/sessions/{session_id}   (A70 route)
- POST  /api/v1/users/me/sessions/revoke-others   (A70 route)
- Password-change endpoint hook (G3 / arch doc §4.8.1)
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlmodel import Session, select

from app.models.auth import AuthRefreshToken
from app.models.security import UserSessionMetadata

logger = logging.getLogger(__name__)


def revoke_session(
    db: Session,
    tenant_id: UUID,
    user_id: UUID,
    session_id: UUID,
    reason: str = "user_revoked",
) -> bool:
    """
    Revoke a single session by session_id.

    Sets user_session_metadata.revoked_at and invalidates the associated
    auth_refresh_token rows via revoked_at + revoked_reason.

    Args:
        db:         Active SQLModel session.
        tenant_id:  Tenant scope (prevents cross-tenant access).
        user_id:    Owner of the session (prevents cross-user access).
        session_id: The session to revoke.
        reason:     Revocation reason stored on the token record.

    Returns:
        True if session was found and revoked; False if not found.
    """
    now = datetime.now(UTC)

    session_row = db.exec(
        select(UserSessionMetadata)
        .where(UserSessionMetadata.session_id == session_id)
        .where(UserSessionMetadata.tenant_id == tenant_id)
        .where(UserSessionMetadata.user_id == user_id)
        .where(UserSessionMetadata.revoked_at == None)
    ).first()

    if not session_row:
        return False

    session_row.revoked_at = now
    db.add(session_row)

    # Invalidate associated refresh tokens
    tokens = db.exec(
        select(AuthRefreshToken)
        .where(AuthRefreshToken.session_id == session_id)
        .where(AuthRefreshToken.revoked_at == None)
    ).all()

    for token in tokens:
        token.revoked_at = now
        token.revoked_reason = reason
        db.add(token)

    db.commit()
    logger.info(f"Revoked session {session_id} for user {user_id} (reason={reason})")
    return True


def revoke_others(
    db: Session,
    tenant_id: UUID,
    user_id: UUID,
    current_session_id: UUID,
    reason: str = "revoke_others",
) -> int:
    """
    Revoke all sessions for user_id except current_session_id.

    Used by:
    - POST /api/v1/users/me/sessions/revoke-others
    - Password change hook (G3) — called with reason="password_changed"

    Args:
        db:                 Active SQLModel session.
        tenant_id:          Tenant scope.
        user_id:            User whose other sessions are revoked.
        current_session_id: Session to preserve.
        reason:             Revocation reason for audit trail.

    Returns:
        Count of sessions revoked.
    """
    now = datetime.now(UTC)

    other_sessions = db.exec(
        select(UserSessionMetadata)
        .where(UserSessionMetadata.tenant_id == tenant_id)
        .where(UserSessionMetadata.user_id == user_id)
        .where(UserSessionMetadata.session_id != current_session_id)
        .where(UserSessionMetadata.revoked_at == None)
    ).all()

    revoked_count = 0
    for session_row in other_sessions:
        session_row.revoked_at = now
        db.add(session_row)

        # Invalidate associated refresh tokens
        tokens = db.exec(
            select(AuthRefreshToken)
            .where(AuthRefreshToken.session_id == session_row.session_id)
            .where(AuthRefreshToken.revoked_at == None)
        ).all()
        for token in tokens:
            token.revoked_at = now
            token.revoked_reason = reason
            db.add(token)

        revoked_count += 1

    if revoked_count:
        db.commit()
        logger.info(
            f"Revoked {revoked_count} other sessions for user {user_id} (reason={reason})"
        )

    return revoked_count
