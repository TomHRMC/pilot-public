"""
Help System API routes — B16 (A85, A84, A86, A87).

Routes:
    POST /api/v1/help/retrieve                              — Internal RAG retrieval (A85)
    GET  /api/v1/help/articles/{article_id}                 — Deliver full article markdown (A85)
    POST /api/v1/admin/help/articles/{article_id}/reprocess — Admin trigger re-embed (A85)
    POST /api/v1/help/chat                                  — Send help chat message (A84)
    GET  /api/v1/help/sessions                              — List user's sessions (A84)
    GET  /api/v1/help/sessions/{session_id}                 — Session message history (A84)
    POST /api/v1/help/sessions/{session_id}/feedback        — Inline session feedback (A84)
    POST /api/v1/help/sessions/delete-all                   — Phase 2 stub (A84)
    POST /api/v1/feedback                                   — Submit user feedback (A87)
"""

import logging
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, func, select

from api.schemas.help import (
    AdminReprocessResponse,
    FeedbackSubmitRequest,
    FeedbackSubmitResponse,
    HelpArticleResponse,
    HelpChatRequest,
    HelpChatResponse,
    HelpMessageDetail,
    HelpRetrieveRequest,
    HelpRetrieveResponse,
    HelpSessionDeleteResponse,
    HelpSessionDetailResponse,
    HelpSessionFeedbackRequest,
    HelpSessionFeedbackResponse,
    HelpSessionListResponse,
    HelpSessionSummary,
)
from core.auth import AuthenticatedUser
from core.db import get_db, set_audit_context_sync
from core.permissions import require_permission
from core.test_context import TestUserContext, get_test_context
from services.help_agent import generate_help_response
from services.help_retrieval import retrieve_chunks
from services.setting_resolver import get_effective_setting_for_user
from tasks.help_corpus import (
    generate_help_session_title,
    send_feedback_email,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ──────────────────────────────────────────────────────────────────────────────
# Shared business logic
# ──────────────────────────────────────────────────────────────────────────────


def _retrieve_chunks_impl(
    data: HelpRetrieveRequest,
    db: Session,
    user_role: str,
) -> HelpRetrieveResponse:
    """Internal RAG retrieval — called from chat handler."""

    # Use the pre-computed embedding from request if provided, otherwise embed query_text
    # For direct API calls the embedding vector is passed; internally we call retrieve_chunks
    # which handles embedding internally.
    # This endpoint exists for frontend to call with a query_text approach too.
    # For now: reconstruct via pgvector using pre-computed vector
    from sqlalchemy import text as sa_text

    embedding_str = "[" + ",".join(str(v) for v in data.query_embedding) + "]"

    if data.category_hint:
        sql = sa_text("""
            SELECT c.chunk_id::text, c.article_id, c.section_title, c.chunk_text,
                   1 - (c.embedding <=> :emb::vector) AS score
            FROM help_article_chunk c
            JOIN help_article a ON c.article_id = a.code
            WHERE a.audience @> ARRAY[:role]::text[]
              AND a.category = :category
            ORDER BY c.embedding <=> :emb::vector
            LIMIT :k
        """)
        rows = db.exec(
            sql,
            params={
                "emb": embedding_str,
                "role": user_role,
                "category": data.category_hint,
                "k": data.k,
            },
        ).all()
    else:
        sql = sa_text("""
            SELECT c.chunk_id::text, c.article_id, c.section_title, c.chunk_text,
                   1 - (c.embedding <=> :emb::vector) AS score
            FROM help_article_chunk c
            JOIN help_article a ON c.article_id = a.code
            WHERE a.audience @> ARRAY[:role]::text[]
            ORDER BY c.embedding <=> :emb::vector
            LIMIT :k
        """)
        rows = db.exec(
            sql, params={"emb": embedding_str, "role": user_role, "k": data.k}
        ).all()

    chunks = [
        {
            "chunk_id": r[0],
            "article_id": r[1],
            "section_title": r[2],
            "chunk_text": r[3],
            "score": float(r[4]),
        }
        for r in rows
    ]
    return HelpRetrieveResponse(chunks=chunks)


def _get_article_impl(
    article_id: str,
    db: Session,
    user_role: str,
) -> HelpArticleResponse:
    from app.models.help import HelpArticle

    # FIND-169: article_id → code on HelpArticle
    article = db.exec(select(HelpArticle).where(HelpArticle.code == article_id)).first()

    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Article not found"
        )

    # Audience check
    if user_role not in (article.audience or []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this article",
        )

    # Fetch content from S3
    content_markdown = _fetch_article_from_s3(article.s3_path)

    # FIND-169: article.article_id → article.code
    return HelpArticleResponse(
        article_id=article.code,
        title=article.title,
        category=article.category,
        content_markdown=content_markdown,
        audience=list(article.audience or []),
        last_updated=article.last_updated.isoformat() if article.last_updated else "",
    )


def _fetch_article_from_s3(s3_path: str) -> str:
    """Fetch article markdown from S3, returning placeholder if unavailable."""
    from core.config import settings

    if not settings.HELP_CONTENT_BUCKET:
        return "*Article content not yet available. S3 bucket not configured.*"

    try:
        import boto3  # type: ignore

        without_prefix = s3_path.removeprefix("s3://")
        bucket, _, key = without_prefix.partition("/")
        s3 = boto3.client("s3")
        response = s3.get_object(Bucket=bucket, Key=key)
        return response["Body"].read().decode("utf-8")
    except Exception as e:
        logger.warning(f"Failed to fetch article from S3 {s3_path}: {e}")
        return "*Article content temporarily unavailable.*"


def _chat_impl(
    data: HelpChatRequest,
    db: Session,
    user_id: UUID,
    tenant_id: UUID,
    user_role: str,
) -> HelpChatResponse:
    from app.models.help import HelpChatMessage, HelpChatSession

    now_utc = datetime.now(UTC)

    # Get or create session
    session = None
    if data.session_id:
        # FIND-169: session_id → id on HelpChatSession
        session = db.exec(
            select(HelpChatSession)
            .where(HelpChatSession.id == data.session_id)
            .where(HelpChatSession.tenant_id == tenant_id)
            .where(HelpChatSession.user_id == user_id)
            .where(HelpChatSession.anonymized_at == None)
        ).first()
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Help chat session not found",
            )

    if session is None:
        session = HelpChatSession(
            tenant_id=tenant_id,
            user_id=user_id,
            started_at=now_utc,
            last_activity_at=now_utc,
            message_count=0,
            created_at=now_utc,
            updated_at=now_utc,
        )
        db.add(session)
        db.flush()

    # Load conversation history (last 10 messages)
    # FIND-169: session.session_id → session.id (HelpChatSession PK renamed)
    history_messages = db.exec(
        select(HelpChatMessage)
        .where(HelpChatMessage.session_id == session.id)
        .order_by(HelpChatMessage.created_at.asc())
        .limit(10)
    ).all()

    conversation_history = [
        {"role": m.role, "content": m.content} for m in history_messages
    ]

    # Retrieve relevant chunks
    context_payload_dict = None
    if data.context_payload:
        context_payload_dict = data.context_payload.model_dump(exclude_none=True)

    chunks = retrieve_chunks(
        db=db,
        query_text=data.message,
        user_role=user_role,
        category_hint=context_payload_dict.get("route", "").split("/")[2]
        if context_payload_dict and context_payload_dict.get("route")
        else None,
        k=5,
    )

    # Resolve tone via setting resolver (§21)
    tone, _ = get_effective_setting_for_user(
        db=db,
        tenant_id=tenant_id,
        user_id=user_id,
        setting_key="voice_persona_tone",
        fallback="balanced",
    )
    if tone not in ("conservative", "balanced", "playful"):
        tone = "balanced"

    # Generate AI response
    assistant_content = generate_help_response(
        user_message=data.message,
        retrieved_chunks=chunks,
        conversation_history=conversation_history,
        context_payload=context_payload_dict,
        tone=tone,
    )

    # Persist user message
    user_msg = HelpChatMessage(
        # FIND-169: session.session_id → session.id
        session_id=session.id,
        tenant_id=tenant_id,
        role="user",
        content=data.message,
        context_payload=context_payload_dict,
        voice_used=False,
        created_at=now_utc,
    )
    db.add(user_msg)

    # Persist assistant message
    retrieved_chunks_payload = {
        "chunks": [
            {
                "chunk_id": c["chunk_id"],
                "article_id": c["article_id"],
                "score": c["score"],
            }
            for c in chunks
        ]
    }
    asst_msg = HelpChatMessage(
        # FIND-169: session.session_id → session.id
        session_id=session.id,
        tenant_id=tenant_id,
        role="assistant",
        content=assistant_content,
        retrieved_chunks=retrieved_chunks_payload,
        voice_used=False,
        created_at=now_utc,
    )
    db.add(asst_msg)

    # Update session
    session.last_activity_at = now_utc
    session.message_count = (session.message_count or 0) + 2  # user + assistant
    session.updated_at = now_utc
    db.add(session)
    db.commit()
    db.refresh(asst_msg)

    # Enqueue title generation after first turn
    if session.message_count == 2 and session.title is None:
        # FIND-169: session.session_id → session.id
        generate_help_session_title.delay(str(session.id), data.message[:200])

    retrieved_article_ids = list({c["article_id"] for c in chunks})

    # FIND-169: session.session_id → session.id
    return HelpChatResponse(
        session_id=session.id,
        message_id=asst_msg.message_id,
        role="assistant",
        content=assistant_content,
        retrieved_article_ids=retrieved_article_ids,
        session_title=session.title,
    )


def _list_sessions_impl(
    db: Session,
    user_id: UUID,
    tenant_id: UUID,
    limit: int,
    offset: int,
) -> HelpSessionListResponse:
    from app.models.help import HelpChatSession

    base_query = (
        select(HelpChatSession)
        .where(HelpChatSession.user_id == user_id)
        .where(HelpChatSession.tenant_id == tenant_id)
        .where(HelpChatSession.anonymized_at == None)
    )

    total = db.exec(select(func.count()).select_from(base_query.subquery())).one()

    sessions = db.exec(
        base_query.order_by(HelpChatSession.last_activity_at.desc())
        .offset(offset)
        .limit(limit)
    ).all()

    return HelpSessionListResponse(
        sessions=[HelpSessionSummary.model_validate(s) for s in sessions],
        total=total,
    )


def _get_session_impl(
    session_id: UUID,
    db: Session,
    user_id: UUID,
    tenant_id: UUID,
) -> HelpSessionDetailResponse:
    from app.models.help import HelpChatMessage, HelpChatSession

    # FIND-169: session_id → id on HelpChatSession
    session = db.exec(
        select(HelpChatSession)
        .where(HelpChatSession.id == session_id)
        .where(HelpChatSession.user_id == user_id)
        .where(HelpChatSession.tenant_id == tenant_id)
    ).first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Help chat session not found"
        )

    messages = db.exec(
        select(HelpChatMessage)
        .where(HelpChatMessage.session_id == session_id)
        .order_by(HelpChatMessage.created_at.asc())
    ).all()

    # FIND-169: session.session_id → session.id
    return HelpSessionDetailResponse(
        session_id=session.id,
        title=session.title,
        outcome=session.outcome,
        messages=[HelpMessageDetail.model_validate(m) for m in messages],
    )


def _submit_feedback_impl(
    data: FeedbackSubmitRequest,
    db: Session,
    user_id: UUID,
    tenant_id: UUID,
) -> FeedbackSubmitResponse:
    from app.models.help import FeedbackSubmission
    from core.config import settings

    valid_categories = {"bug", "feature_request", "question", "general"}
    if data.category not in valid_categories:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid category. Must be one of: {sorted(valid_categories)}",
        )

    # Validate session FK if provided
    if data.from_help_chat_session_id:
        from app.models.help import HelpChatSession

        # FIND-169: session_id → id on HelpChatSession
        session = db.exec(
            select(HelpChatSession)
            .where(HelpChatSession.id == data.from_help_chat_session_id)
            .where(HelpChatSession.tenant_id == tenant_id)
        ).first()
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Referenced help chat session not found",
            )

    now_utc = datetime.now(UTC)
    submission = FeedbackSubmission(
        tenant_id=tenant_id,
        user_id=user_id,
        category=data.category,
        body=data.body,
        from_help_chat_session_id=data.from_help_chat_session_id,
        email_sent_to=settings.SUPPORT_EMAIL_ADDRESS,
        created_at=now_utc,
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)

    # Dispatch email task

    send_feedback_email.delay(str(submission.submission_id))

    return FeedbackSubmitResponse(
        submission_id=submission.submission_id,
        category=submission.category,
        submitted_at=submission.created_at,
        confirmation_message="Thanks for your feedback! We'll follow up at your email address.",
    )


def _delete_session_impl(
    session_id: UUID,
    db: Session,
    user_id: UUID,
    tenant_id: UUID,
) -> HelpSessionDeleteResponse:
    """Soft-delete a help chat session (anonymized_at = now())."""
    from app.models.help import HelpChatSession

    # FIND-169: session_id → id on HelpChatSession
    session = db.exec(
        select(HelpChatSession)
        .where(HelpChatSession.id == session_id)
        .where(HelpChatSession.user_id == user_id)
        .where(HelpChatSession.tenant_id == tenant_id)
        .where(HelpChatSession.anonymized_at == None)
    ).first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Help chat session not found",
        )

    now_utc = datetime.now(UTC)
    session.anonymized_at = now_utc
    session.updated_at = now_utc
    db.add(session)
    db.commit()

    return HelpSessionDeleteResponse(
        message="Session deleted",
        session_id=session.id,
    )


# ──────────────────────────────────────────────────────────────────────────────
# TEST ENDPOINTS (registered FIRST per §8.2)
# ──────────────────────────────────────────────────────────────────────────────


@router.post(
    "/chat/test", response_model=HelpChatResponse, status_code=status.HTTP_200_OK
)
def help_chat_test(data: HelpChatRequest, db: Session = Depends(get_db)):
    """Test endpoint — no auth. Blocked in staging/production."""
    ctx = get_test_context()
    return _chat_impl(data, db, ctx.id, ctx.tenant_id, "owner")


@router.get("/sessions/test", response_model=HelpSessionListResponse)
def list_sessions_test(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    """Test endpoint — no auth. Blocked in staging/production."""
    ctx = get_test_context()
    return _list_sessions_impl(db, ctx.id, ctx.tenant_id, limit, offset)


@router.post(
    "/feedback/test",
    response_model=FeedbackSubmitResponse,
    status_code=status.HTTP_201_CREATED,
)
def submit_feedback_test(data: FeedbackSubmitRequest, db: Session = Depends(get_db)):
    """Test endpoint — no auth. Blocked in staging/production."""
    ctx = get_test_context()
    set_audit_context_sync(db, ctx.id)
    return _submit_feedback_impl(data, db, ctx.id, ctx.tenant_id)


@router.delete("/sessions/{session_id}/test", response_model=HelpSessionDeleteResponse)
def delete_help_session_test(
    session_id: UUID,
    db: Session = Depends(get_db),
):
    """Test endpoint — no auth. Blocked in staging/production."""
    ctx = get_test_context()
    set_audit_context_sync(db, ctx.id)
    return _delete_session_impl(session_id, db, ctx.id, ctx.tenant_id)


# ──────────────────────────────────────────────────────────────────────────────
# AUTHENTICATED ENDPOINTS
# ──────────────────────────────────────────────────────────────────────────────


@router.post("/retrieve", response_model=HelpRetrieveResponse)
def retrieve_help_chunks(
    data: HelpRetrieveRequest,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(
        require_permission("help_chat.send_message")
    ),
):
    """Internal RAG retrieval endpoint — used by A84 chat handler."""
    return _retrieve_chunks_impl(data, db, current_user.role_code or "owner")


@router.get("/articles/{article_id}", response_model=HelpArticleResponse)
def get_help_article(
    article_id: str,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(
        require_permission("help_chat.send_message")
    ),
):
    """Deliver full article markdown for 'Read full article' action."""
    return _get_article_impl(article_id, db, current_user.role_code or "owner")


@router.post("/chat", response_model=HelpChatResponse)
def help_chat(
    data: HelpChatRequest,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(
        require_permission("help_chat.send_message")
    ),
):
    """Send a message in a help conversation."""
    set_audit_context_sync(db, current_user.id)
    return _chat_impl(
        data,
        db,
        current_user.id,
        current_user.tenant_id,
        current_user.role_code or "owner",
    )


@router.get("/sessions", response_model=HelpSessionListResponse)
def list_help_sessions(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(
        require_permission("help_chat.view_history")
    ),
):
    """List user's recent help sessions."""
    return _list_sessions_impl(
        db, current_user.id, current_user.tenant_id, limit, offset
    )


def _submit_session_feedback_impl(
    session_id: UUID,
    data: HelpSessionFeedbackRequest,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> HelpSessionFeedbackResponse:
    """Shared logic for submitting session feedback."""
    from app.models.help import HelpChatSession

    valid_signals = {"resolved", "escalated", "abandoned"}
    if data.signal not in valid_signals:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid signal. Must be one of: {sorted(valid_signals)}",
        )

    session = db.exec(
        select(HelpChatSession)
        .where(HelpChatSession.id == session_id)
        .where(HelpChatSession.user_id == user_context.id)
        .where(HelpChatSession.tenant_id == user_context.tenant_id)
    ).first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Help chat session not found"
        )

    if isinstance(user_context, AuthenticatedUser):
        set_audit_context_sync(db, user_context.id)

    session.outcome = data.signal
    session.updated_at = datetime.now(UTC)
    db.add(session)
    db.commit()

    return HelpSessionFeedbackResponse(session_id=session.id, outcome=session.outcome)


# TEST ENDPOINTS for get_help_session and submit_session_feedback (register BEFORE authenticated)


@router.get("/sessions/{session_id}/test", response_model=HelpSessionDetailResponse)
def get_help_session_test(
    session_id: UUID,
    db: Session = Depends(get_db),
):
    """Full message history for a session (TEST ENDPOINT — no auth required)."""
    test_context = get_test_context()
    return _get_session_impl(session_id, db, test_context.id, test_context.tenant_id)


@router.post(
    "/sessions/{session_id}/feedback/test", response_model=HelpSessionFeedbackResponse
)
def submit_session_feedback_test(
    session_id: UUID,
    data: HelpSessionFeedbackRequest,
    db: Session = Depends(get_db),
):
    """Capture inline session feedback (TEST ENDPOINT — no auth required)."""
    test_context = get_test_context()
    return _submit_session_feedback_impl(session_id, data, db, test_context)


# AUTHENTICATED ENDPOINTS


@router.get("/sessions/{session_id}", response_model=HelpSessionDetailResponse)
def get_help_session(
    session_id: UUID,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(
        require_permission("help_chat.view_history")
    ),
):
    """Full message history for a session."""
    return _get_session_impl(session_id, db, current_user.id, current_user.tenant_id)


@router.post(
    "/sessions/{session_id}/feedback", response_model=HelpSessionFeedbackResponse
)
def submit_session_feedback(
    session_id: UUID,
    data: HelpSessionFeedbackRequest,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(
        require_permission("help_chat.send_message")
    ),
):
    """Capture inline session feedback signal (resolved/escalated/abandoned)."""
    return _submit_session_feedback_impl(session_id, data, db, current_user)


@router.delete("/sessions/{session_id}", response_model=HelpSessionDeleteResponse)
def delete_help_session(
    session_id: UUID,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(
        require_permission("help_chat.delete_own_history")
    ),
):
    """Delete a user's help chat session (soft-delete via anonymized_at)."""
    set_audit_context_sync(db, current_user.id)
    return _delete_session_impl(session_id, db, current_user.id, current_user.tenant_id)


@router.post("/sessions/delete-all", status_code=status.HTTP_501_NOT_IMPLEMENTED)
def delete_all_help_sessions(
    current_user: AuthenticatedUser = Depends(
        require_permission("help_chat.delete_own_history")
    ),
):
    """Phase 2 stub — self-service deletion not yet implemented."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={
            "status": "not_implemented",
            "detail": "Self-service deletion is a Phase 2 feature.",
        },
    )


# ──────────────────────────────────────────────────────────────────────────────
# A87 — Feedback submission (prefix /api/v1/feedback — registered separately in main.py)
# ──────────────────────────────────────────────────────────────────────────────

feedback_router = APIRouter()


@feedback_router.post(
    "/test", response_model=FeedbackSubmitResponse, status_code=status.HTTP_201_CREATED
)
def submit_feedback_test_alt(
    data: FeedbackSubmitRequest, db: Session = Depends(get_db)
):
    """Test endpoint — no auth. Blocked in staging/production."""
    ctx = get_test_context()
    set_audit_context_sync(db, ctx.id)
    return _submit_feedback_impl(data, db, ctx.id, ctx.tenant_id)


@feedback_router.post(
    "/", response_model=FeedbackSubmitResponse, status_code=status.HTTP_201_CREATED
)
def submit_feedback(
    data: FeedbackSubmitRequest,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("feedback.submit")),
):
    """Submit user feedback — dispatches to support email via SendGrid."""
    set_audit_context_sync(db, current_user.id)
    return _submit_feedback_impl(data, db, current_user.id, current_user.tenant_id)


# ──────────────────────────────────────────────────────────────────────────────
# A85 — Admin reprocess endpoint (prefix /api/v1/admin — registered separately)
# ──────────────────────────────────────────────────────────────────────────────

admin_help_router = APIRouter()


@admin_help_router.post(
    "/help/articles/{article_id}/reprocess",
    response_model=AdminReprocessResponse,
)
def admin_reprocess_article(
    article_id: str,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("admin.manage")),
):
    """Admin trigger to re-embed a single help article."""
    from app.models.help import HelpArticle

    # FIND-169: article_id → code on HelpArticle
    article = db.exec(select(HelpArticle).where(HelpArticle.code == article_id)).first()

    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Article not found"
        )

    from tasks.help_corpus import process_help_article

    # FIND-169: article.article_id → article.code
    process_help_article.delay(article_id=article.code, s3_path=article.s3_path)

    return AdminReprocessResponse(status="queued", article_id=article_id)
