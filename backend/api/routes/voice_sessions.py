"""
Voice Sessions API — session listing with per-day numbering.
Established in B2 (A9, A12).
FE-B23/A3: Added POST /sessions create endpoint.
"""

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from sqlmodel import Session, select

from app.models.ai import ConversationMessage, ConversationSession
from core.auth import AuthenticatedUser
from core.db import get_db, set_audit_context_sync
from core.permissions import require_permission
from core.test_context import TestUserContext, get_test_context
from services.voice_session_service import get_sessions_with_numbers

router = APIRouter()


# ==================== RESPONSE SCHEMAS ====================


class SessionMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    message_id: str
    session_id: str
    role: str
    content_text: str
    structured_content_json: dict | None = None
    created_at: str


class SessionResponse(BaseModel):
    """Response for a single session with session number."""

    session_id: str
    session_number: int
    title: str | None
    title_auto_generated: bool
    status: str
    created_at: str
    updated_at: str
    archived_at: str | None = None
    message_count: int = 0


class SessionListResponse(BaseModel):
    """Paginated list of sessions."""

    sessions: list[SessionResponse]
    next_cursor: str | None = None
    has_more: bool


class SessionMessagesResponse(BaseModel):
    """Paginated list of messages within a session."""

    messages: list[SessionMessageResponse]
    next_cursor: str | None = None
    has_more: bool


# ==================== SHARED BUSINESS LOGIC ====================


def _get_sessions_with_counts_impl(
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
    limit: int = 20,
    cursor: str | None = None,
) -> SessionListResponse:
    """
    Shared logic for retrieving sessions with message counts.
    """
    sessions, next_cursor, has_more = get_sessions_with_numbers(
        db=db,
        tenant_id=user_context.tenant_id,
        user_id=user_context.id,
        limit=limit,
    )

    # Fetch message counts for each session
    response_sessions = []
    for session_dict in sessions:
        session_id_uuid = uuid.UUID(session_dict["session_id"])
        message_count = db.exec(
            select(ConversationMessage)
            .where(ConversationMessage.session_id == session_id_uuid)
            .where(ConversationMessage.tenant_id == user_context.tenant_id)
        ).all()

        response_sessions.append(
            SessionResponse(
                session_id=session_dict["session_id"],
                session_number=session_dict["session_number"],
                title=session_dict["title"],
                title_auto_generated=session_dict["title_auto_generated"],
                status=session_dict["status"],
                created_at=session_dict["created_at"],
                updated_at=session_dict["updated_at"],
                archived_at=session_dict["archived_at"],
                message_count=len(message_count),
            )
        )

    return SessionListResponse(
        sessions=response_sessions,
        next_cursor=next_cursor,
        has_more=has_more,
    )


def _get_session_messages_impl(
    db: Session,
    session_id: uuid.UUID,
    user_context: AuthenticatedUser | TestUserContext,
    limit: int = 50,
    cursor: str | None = None,
) -> SessionMessagesResponse:
    """
    Shared logic for retrieving messages in a session.
    """
    # Verify session ownership (tenant + user scope)
    session = db.exec(
        select(ConversationSession)
        .where(ConversationSession.id == session_id)
        .where(ConversationSession.tenant_id == user_context.tenant_id)
        .where(ConversationSession.user_id == user_context.id)
    ).first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    # Cap limit at 50
    limit = min(limit, 50)

    # Fetch messages
    messages = db.exec(
        select(ConversationMessage)
        .where(ConversationMessage.session_id == session_id)
        .where(ConversationMessage.tenant_id == user_context.tenant_id)
        .order_by(ConversationMessage.created_at.asc())
        .limit(limit + 1)
    ).all()

    has_more = len(messages) > limit
    messages = messages[:limit]

    response_messages = [
        SessionMessageResponse(
            message_id=str(msg.id),
            session_id=str(msg.session_id),
            role=msg.role,
            content_text=msg.content_text,
            structured_content_json=msg.structured_content_json,
            created_at=msg.created_at.isoformat(),
        )
        for msg in messages
    ]

    return SessionMessagesResponse(
        messages=response_messages,
        next_cursor=None,  # Simplified pagination for MVP
        has_more=has_more,
    )


# ==================== CREATE SESSION SHARED LOGIC ====================


def _create_session_impl(
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> SessionResponse:
    """Create a new active voice conversation session."""
    now = datetime.now(UTC)
    session = ConversationSession(
        tenant_id=user_context.tenant_id,
        user_id=user_context.id,
        status="active",
        created_at=now,
        updated_at=now,
        created_by=user_context.id,
        updated_by=user_context.id,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    return SessionResponse(
        session_id=str(session.id),
        session_number=1,  # New sessions start at 1; real numbering via list endpoint
        title=session.title,
        title_auto_generated=session.title_auto_generated,
        status=session.status,
        created_at=session.created_at.isoformat(),
        updated_at=session.updated_at.isoformat(),
        archived_at=session.archived_at.isoformat() if session.archived_at else None,
        message_count=0,
    )


# ==================== TEST ENDPOINTS (register FIRST) ====================


@router.post(
    "/test",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Voice Session (TEST — no auth)",
)
def create_session_test(
    db: Session = Depends(get_db),
) -> SessionResponse:
    """TEST ENDPOINT — no authentication required."""
    test_context = get_test_context()
    return _create_session_impl(db, test_context)


@router.get("/test", response_model=SessionListResponse)
def list_sessions_test(
    limit: int = Query(20, ge=1, le=50),
    cursor: str | None = Query(None),
    db: Session = Depends(get_db),
):
    """Test endpoint — list conversation sessions with session numbers."""
    test_context = get_test_context()  # Raises 403 if disabled
    return _get_sessions_with_counts_impl(db, test_context, limit, cursor)


@router.get("/test/{session_id}/messages", response_model=SessionMessagesResponse)
def get_session_messages_test(
    session_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=50),
    cursor: str | None = Query(None),
    db: Session = Depends(get_db),
):
    """Test endpoint — get messages in a session."""
    test_context = get_test_context()
    return _get_session_messages_impl(db, session_id, test_context, limit, cursor)


# ==================== AUTHENTICATED ENDPOINTS ====================


@router.post(
    "/",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Voice Session — FE-B23/A3",
    description="Create a new active voice conversation session for the authenticated user.",
)
def create_session(
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("voice.use")),
) -> SessionResponse:
    """
    Create a new voice conversation session.

    Auth: JWT required — `voice.use` permission
    RBAC: `require_permission("voice.use")`
    """
    set_audit_context_sync(db, user_id=current_user.id)
    return _create_session_impl(db, current_user)


@router.get("/", response_model=SessionListResponse)
def list_sessions(
    limit: int = Query(20, ge=1, le=50),
    cursor: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("voice.use")),
):
    """
    List conversation sessions with derived per-day session numbers.

    Auth: JWT required — `voice.use` permission
    RBAC: `require_permission("voice.use")`

    Query params:
    - limit: Max sessions per page (1-50, default 20)
    - cursor: Opaque pagination cursor
    """
    return _get_sessions_with_counts_impl(db, current_user, limit, cursor)


@router.get("/{session_id}/messages", response_model=SessionMessagesResponse)
def get_session_messages(
    session_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=50),
    cursor: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("voice.use")),
):
    """
    Get messages in a conversation session.

    Auth: JWT required — `voice.use` permission
    RBAC: `require_permission("voice.use")` + tenant-scoped session ownership check

    Query params:
    - limit: Max messages per page (1-50, default 50)
    - cursor: Opaque pagination cursor
    """
    return _get_session_messages_impl(db, session_id, current_user, limit, cursor)
