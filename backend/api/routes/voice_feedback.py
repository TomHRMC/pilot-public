"""
Voice AI Feedback Loop API — A6 (B2).

Endpoints:
  POST /api/v1/voice/feedback          — submit a feedback record
  GET  /api/v1/voice/transcripts       — list voice command log entries (for review)
  GET  /api/v1/voice/feedback          — list submitted feedback items

All endpoints follow the dual-endpoint architecture (§8.2): authenticated + test variants.
RBAC: voice.provide_feedback permission required (owner/accountant roles).
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlmodel import Session, select

from app.models.ai import VoiceCommandLog, VoiceFeedback
from core.auth import AuthenticatedUser
from core.db import get_db
from core.permissions import require_permission
from core.test_context import TestUserContext, get_test_context

router = APIRouter()


# ==================== REQUEST / RESPONSE SCHEMAS ====================


class VoiceFeedbackCreate(BaseModel):
    """Request body for POST /api/v1/voice/feedback"""

    voice_command_log_id: int | None = None
    original_transcription: str
    corrected_text: str | None = None
    intent_misparsed: bool = False
    corrected_intent: str | None = None
    feedback_notes: str | None = None


class VoiceFeedbackCreatedResponse(BaseModel):
    """Response for POST /api/v1/voice/feedback"""

    feedback_id: str
    tenant_id: str
    created_at: str


class TranscriptItem(BaseModel):
    """A single voice command log entry for transcript review."""

    voice_command_log_id: int
    tenant_id: str
    user_id: str
    original_transcription: str | None = None
    intent_detected: str | None = None
    is_successful: bool
    whisper_latency_ms: int | None = None
    created_at: str
    has_feedback: bool


class TranscriptListResponse(BaseModel):
    transcripts: list[TranscriptItem]
    next_cursor: str | None = None
    has_more: bool


class FeedbackItem(BaseModel):
    """A single voice feedback record."""

    feedback_id: str
    voice_command_log_id: int | None = None
    original_transcription: str
    corrected_text: str | None = None
    intent_misparsed: bool
    corrected_intent: str | None = None
    feedback_notes: str | None = None
    exported_at: str | None = None
    created_at: str


class FeedbackListResponse(BaseModel):
    feedback_items: list[FeedbackItem]
    next_cursor: str | None = None
    has_more: bool


# ==================== SHARED BUSINESS LOGIC ====================


def _submit_feedback_impl(
    payload: VoiceFeedbackCreate,
    user_context: AuthenticatedUser | TestUserContext,
    db: Session,
) -> VoiceFeedbackCreatedResponse:
    """Shared logic for POST /feedback."""
    # Validate voice_command_log_id belongs to same tenant if provided
    if payload.voice_command_log_id is not None:
        log_entry = db.exec(
            select(VoiceCommandLog)
            .where(VoiceCommandLog.id == payload.voice_command_log_id)
            .where(VoiceCommandLog.tenant_id == user_context.tenant_id)
        ).first()
        if not log_entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "type": "https://pilot.app/errors/not-found",
                    "title": "Voice command log not found",
                    "status": 404,
                    "detail": f"voice_command_log_id {payload.voice_command_log_id} not found for this tenant.",
                },
            )

    feedback = VoiceFeedback(
        tenant_id=user_context.tenant_id,
        user_id=user_context.id,
        voice_command_log_id=payload.voice_command_log_id,
        original_transcription=payload.original_transcription,
        corrected_text=payload.corrected_text,
        intent_misparsed=payload.intent_misparsed,
        corrected_intent=payload.corrected_intent,
        feedback_notes=payload.feedback_notes,
        created_by=user_context.id,
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)

    return VoiceFeedbackCreatedResponse(
        feedback_id=str(feedback.id),
        tenant_id=str(feedback.tenant_id),
        created_at=feedback.created_at.isoformat(),
    )


def _list_transcripts_impl(
    user_context: AuthenticatedUser | TestUserContext,
    db: Session,
    limit: int = 20,
    cursor: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    intent: str | None = None,
) -> TranscriptListResponse:
    """Shared logic for GET /transcripts."""
    limit = min(limit, 50)

    stmt = (
        select(VoiceCommandLog)
        .where(VoiceCommandLog.tenant_id == user_context.tenant_id)
        .order_by(VoiceCommandLog.created_at.desc())
        .limit(limit + 1)
    )

    if intent:
        stmt = stmt.where(VoiceCommandLog.intent_detected == intent)

    logs = db.exec(stmt).all()

    has_more = len(logs) > limit
    logs = logs[:limit]

    # Check which logs already have feedback
    log_ids = [log.id for log in logs]
    feedback_log_ids = set()
    if log_ids:
        existing_feedback = db.exec(
            select(VoiceFeedback.voice_command_log_id)
            .where(VoiceFeedback.voice_command_log_id.in_(log_ids))
            .where(VoiceFeedback.tenant_id == user_context.tenant_id)
        ).all()
        feedback_log_ids = {fid for fid in existing_feedback if fid is not None}

    transcripts = [
        TranscriptItem(
            voice_command_log_id=log.id,
            tenant_id=str(log.tenant_id),
            user_id=str(log.user_id),
            original_transcription=None,  # transcription is in conversation_message
            intent_detected=log.intent_detected,
            is_successful=log.is_successful,
            whisper_latency_ms=log.whisper_latency_ms,
            created_at=log.created_at.isoformat(),
            has_feedback=log.id in feedback_log_ids,
        )
        for log in logs
    ]

    return TranscriptListResponse(
        transcripts=transcripts,
        next_cursor=None,  # MVP: simplified pagination
        has_more=has_more,
    )


def _list_feedback_impl(
    user_context: AuthenticatedUser | TestUserContext,
    db: Session,
    limit: int = 20,
    cursor: str | None = None,
    exported: bool | None = None,
) -> FeedbackListResponse:
    """Shared logic for GET /feedback."""
    limit = min(limit, 50)

    stmt = (
        select(VoiceFeedback)
        .where(VoiceFeedback.tenant_id == user_context.tenant_id)
        .order_by(VoiceFeedback.created_at.desc())
        .limit(limit + 1)
    )

    if exported is True:
        stmt = stmt.where(VoiceFeedback.exported_at.isnot(None))
    elif exported is False:
        stmt = stmt.where(VoiceFeedback.exported_at.is_(None))

    items = db.exec(stmt).all()

    has_more = len(items) > limit
    items = items[:limit]

    feedback_items = [
        FeedbackItem(
            feedback_id=str(item.id),
            voice_command_log_id=item.voice_command_log_id,
            original_transcription=item.original_transcription,
            corrected_text=item.corrected_text,
            intent_misparsed=item.intent_misparsed,
            corrected_intent=item.corrected_intent,
            feedback_notes=item.feedback_notes,
            exported_at=item.exported_at.isoformat() if item.exported_at else None,
            created_at=item.created_at.isoformat(),
        )
        for item in items
    ]

    return FeedbackListResponse(
        feedback_items=feedback_items,
        next_cursor=None,  # MVP: simplified pagination
        has_more=has_more,
    )


# ==================== TEST ENDPOINTS (register FIRST) ====================


@router.post(
    "/feedback/test",
    response_model=VoiceFeedbackCreatedResponse,
    status_code=status.HTTP_201_CREATED,
)
def submit_feedback_test(
    payload: VoiceFeedbackCreate,
    db: Session = Depends(get_db),
):
    """Test endpoint — submit voice AI feedback."""
    test_context = get_test_context()
    return _submit_feedback_impl(payload, test_context, db)


@router.get("/transcripts/test", response_model=TranscriptListResponse)
def list_transcripts_test(
    limit: int = Query(20, ge=1, le=50),
    cursor: str | None = Query(None),
    intent: str | None = Query(None),
    db: Session = Depends(get_db),
):
    """Test endpoint — list voice command transcripts for review."""
    test_context = get_test_context()
    return _list_transcripts_impl(
        test_context, db, limit=limit, cursor=cursor, intent=intent
    )


@router.get("/feedback/test", response_model=FeedbackListResponse)
def list_feedback_test(
    limit: int = Query(20, ge=1, le=50),
    cursor: str | None = Query(None),
    exported: bool | None = Query(None),
    db: Session = Depends(get_db),
):
    """Test endpoint — list submitted voice feedback."""
    test_context = get_test_context()
    return _list_feedback_impl(
        test_context, db, limit=limit, cursor=cursor, exported=exported
    )


# ==================== AUTHENTICATED ENDPOINTS ====================


@router.post(
    "/feedback",
    response_model=VoiceFeedbackCreatedResponse,
    status_code=status.HTTP_201_CREATED,
)
def submit_feedback(
    payload: VoiceFeedbackCreate,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(
        require_permission("voice.provide_feedback")
    ),
):
    """
    Submit voice AI feedback for a transcription error or intent misparse.

    Auth: JWT required — `voice.provide_feedback` permission
    RBAC: owner / accountant roles only

    The feedback is stored for nightly export to S3 training bucket.
    """
    return _submit_feedback_impl(payload, current_user, db)


@router.get("/transcripts", response_model=TranscriptListResponse)
def list_transcripts(
    limit: int = Query(20, ge=1, le=50),
    cursor: str | None = Query(None),
    intent: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(
        require_permission("voice.provide_feedback")
    ),
):
    """
    List recent voice command log entries for feedback review.

    Auth: JWT required — `voice.provide_feedback` permission
    """
    return _list_transcripts_impl(
        current_user, db, limit=limit, cursor=cursor, intent=intent
    )


@router.get("/feedback", response_model=FeedbackListResponse)
def list_feedback(
    limit: int = Query(20, ge=1, le=50),
    cursor: str | None = Query(None),
    exported: bool | None = Query(None),
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(
        require_permission("voice.provide_feedback")
    ),
):
    """
    List submitted voice feedback entries.

    Auth: JWT required — `voice.provide_feedback` permission
    Query params:
      - exported: true = exported only, false = unexported only, omit = all
    """
    return _list_feedback_impl(
        current_user, db, limit=limit, cursor=cursor, exported=exported
    )
