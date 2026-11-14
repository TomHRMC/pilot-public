import json
import time
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlmodel import Session, select

from app.models.ai import ConversationMessage, ConversationSession, VoiceCommandLog
from app.models.billing import Subscription, UsageLedger
from core.auth import AuthenticatedUser
from core.db import get_db
from core.permissions import require_permission
from core.test_context import TestUserContext, get_test_context
from services.ai_service import get_embedding, parse_intent, transcribe_audio

router = APIRouter()


class VoiceCommandResponse(BaseModel):
    transcribed_text: str
    parsed_intent: dict
    session_id: uuid.UUID
    action_result: dict | None = None  # NEW: Result from action execution


# ==================== SHARED BUSINESS LOGIC ====================


async def _process_voice_command_impl(
    audio: UploadFile,
    session_id: uuid.UUID | None,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> VoiceCommandResponse:
    """
    Shared voice command processing logic used by both authenticated and test endpoints.

    Args:
        audio: Uploaded audio file
        session_id: Optional existing conversation session ID
        db: Database session
        user_context: Either authenticated User or TestUserContext

    Returns:
        VoiceCommandResponse with transcription, intent, and session ID

    Raises:
        HTTPException: If audio read, transcription, or intent parsing fails

    Note:
        This function works for both authenticated and test endpoints because
        TestUserContext provides tenant_id and user_id attributes (User model lacks tenant_id - Gap #40).
    """
    # a. Start a high-resolution timer.
    start_time = time.perf_counter()

    # Read audio bytes
    try:
        audio_bytes = await audio.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read audio file: {e}")

    # b. Await transcribe_audio. Record whisper_latency_ms.
    whisper_start = time.perf_counter()
    try:
        transcribed_text = await transcribe_audio(
            audio_bytes, audio.filename or "audio.m4a"
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Transcription failed: {e!s}")
    whisper_latency_ms = int((time.perf_counter() - whisper_start) * 1000)

    # c. Fetch the existing conversation_session or create a new one.
    conversation_session = None
    if session_id:
        conversation_session = db.exec(
            select(ConversationSession)
            .where(ConversationSession.id == session_id)
            .where(ConversationSession.tenant_id == user_context.tenant_id)
        ).first()

    if not conversation_session:
        conversation_session = ConversationSession(
            tenant_id=user_context.tenant_id,
            user_id=user_context.id,
            status="active",
        )
        db.add(conversation_session)
        db.flush()

    # Build context for Ollama (optional, using previous messages if any)
    context_messages = []
    if session_id and conversation_session:
        previous_messages = db.exec(
            select(ConversationMessage)
            .where(ConversationMessage.session_id == conversation_session.id)
            .order_by(ConversationMessage.created_at)
        ).all()
        for msg in previous_messages:
            context_messages.append({"role": msg.role, "content": msg.content_text})

    # d. Insert a conversation_message (role='user', content=transcribed_text).
    user_message = ConversationMessage(
        session_id=conversation_session.id,
        tenant_id=conversation_session.tenant_id,
        role="user",
        content_text=transcribed_text,
        created_by=user_context.id,
    )
    db.add(user_message)
    db.flush()

    # e. Await get_embedding on the text. Update the message and session context_embedding.
    try:
        embedding = await get_embedding(transcribed_text)
        user_message.embedding = embedding
        # Naive approach: overwrite session embedding with the latest user utterance
        # (In a real system, you might average them or use a sliding window)
        conversation_session.context_embedding = embedding
        db.add(user_message)
        db.add(conversation_session)
    except Exception:
        # Embedding failure is non-fatal: continue without it.
        pass

    # f. Await parse_intent. Record ollama_latency_ms.
    ollama_start = time.perf_counter()
    try:
        parsed_json_string = await parse_intent(transcribed_text, context_messages)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Intent parsing failed: {e!s}")
    ollama_latency_ms = int((time.perf_counter() - ollama_start) * 1000)

    # Try to parse the json string to store in DB
    try:
        parsed_intent_dict = json.loads(parsed_json_string)
    except json.JSONDecodeError:
        # Fallback if Ollama didn't return valid JSON
        parsed_intent_dict = {"raw_output": parsed_json_string}

    # g. Insert a conversation_message (role='assistant', content=parsed_json_string).
    assistant_message = ConversationMessage(
        session_id=conversation_session.id,
        tenant_id=conversation_session.tenant_id,
        role="assistant",
        content_text=parsed_json_string,
    )
    db.add(assistant_message)
    db.flush()

    # NEW: h. Execute the voice action (Gap #17 - Intent-Based Action Execution)
    action_result: dict = {}
    action_latency_ms = 0

    intent_type = parsed_intent_dict.get("intent")
    if intent_type:
        from services.voice_action_router import execute_action

        action_start = time.perf_counter()
        try:
            action_result = await execute_action(
                intent_type=intent_type,
                entities=parsed_intent_dict.get("entities", {}),
                current_user=user_context,
                db=db,
                session=conversation_session,
            )
            action_latency_ms = int((time.perf_counter() - action_start) * 1000)
        except Exception as e:
            # Log error but don't fail the whole request
            action_result = {
                "action": intent_type,
                "success": False,
                "error": str(e),
                "message": f"Action failed: {e!s}",
            }
            action_latency_ms = int((time.perf_counter() - action_start) * 1000)

    # i. Calculate total_latency_ms. Insert a voice_command_log record with the latencies and the parsed intent.
    total_latency_ms = int((time.perf_counter() - start_time) * 1000)

    voice_log = VoiceCommandLog(
        tenant_id=user_context.tenant_id,
        user_id=user_context.id,
        message_id=user_message.id,
        intent_detected=intent_type,
        entities_extracted=parsed_intent_dict.get("entities", parsed_intent_dict),
        action_executed=intent_type
        if action_result.get("success")
        else None,  # NEW: Track executed action
        whisper_latency_ms=whisper_latency_ms,
        ollama_latency_ms=ollama_latency_ms,
        total_latency_ms=total_latency_ms,
        is_successful=action_result.get("success", True),  # Track action success
    )
    db.add(voice_log)
    db.commit()

    # FIND-101: Record voice AI minutes usage for metered billing (write path)
    try:
        # Get tenant subscription for FK reference
        tenant_subscription = db.exec(
            select(Subscription)
            .where(Subscription.tenant_id == user_context.tenant_id)
            .where(Subscription.is_active == True)
            .order_by(Subscription.created_at.desc())
        ).first()

        # Only write usage ledger if subscription exists (FIND-102 prerequisite)
        if tenant_subscription:
            voice_minutes = round(whisper_latency_ms / 60_000, 4)
            usage_ledger = UsageLedger(
                tenant_id=user_context.tenant_id,
                subscription_id=tenant_subscription.id,
                product_feature_code="voice_ai_minutes",
                quantity=voice_minutes,
                occurred_at=datetime.now(UTC),
                idempotency_key=f"voice-{voice_log.id}",
                created_by=user_context.id,
            )
            db.add(usage_ledger)
            db.commit()
    except Exception as e:
        # Log error but don't fail the voice command response if usage tracking fails
        import logging

        logging.warning(
            f"Failed to record voice AI usage for tenant {user_context.tenant_id}: {e}"
        )

    # k. A11: Enqueue session title generation after the first assistant turn.
    # Only fires if title is NULL or auto-generated (user-set titles are frozen).
    # Check if this was the first assistant message in the session.
    if not conversation_session.title or conversation_session.title_auto_generated:
        # Count assistant messages — if this is the first, enqueue the title task
        from sqlalchemy import func as sa_func

        assistant_count = db.exec(
            select(sa_func.count()).where(
                ConversationMessage.session_id == conversation_session.id,
                ConversationMessage.role == "assistant",
            )
        ).one()
        if assistant_count <= 1:
            try:
                from tasks.voice_session_title import generate_session_title

                generate_session_title.delay(str(conversation_session.id))
            except Exception as e:
                # Non-blocking: log but don't fail the request if Celery is unavailable
                import logging

                logging.getLogger(__name__).warning(
                    f"Failed to enqueue generate_session_title for session "
                    f"{conversation_session.id}: {e}"
                )

    # j. Return the parsed intent, action result, and transcribed text to the client.
    return VoiceCommandResponse(
        transcribed_text=transcribed_text,
        parsed_intent=parsed_intent_dict,
        session_id=conversation_session.id,
        action_result=action_result
        if action_result
        else None,  # NEW: Include action result
    )


# ==================== AUTHENTICATED ENDPOINTS ====================


@router.post("/command", response_model=VoiceCommandResponse)
async def process_voice_command(
    audio: UploadFile = File(...),
    session_id: uuid.UUID | None = Form(None),
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("voice.use")),
):
    """
    Process voice command with Whisper transcription and Llama intent parsing (requires JWT authentication and voice.use permission).

    Security:
        - Requires valid JWT token
        - Requires voice.use permission (technician, owner roles)
        - Conversation created in authenticated user's tenant

    Processing Steps:
        1. Transcribe audio using Whisper Large-v3
        2. Parse intent using the local Llama model
        3. Store conversation and log latencies

    Returns:
        VoiceCommandResponse with transcription, parsed intent, and session ID
    """
    return await _process_voice_command_impl(audio, session_id, db, current_user)


# ==================== TEST ENDPOINTS (UNAUTHENTICATED) ====================


@router.post("/command/test", response_model=VoiceCommandResponse)
async def process_voice_command_test(
    audio: UploadFile = File(...),
    session_id: uuid.UUID | None = Form(None),
    db: Session = Depends(get_db),
):
    """
    Process voice command with Whisper transcription and Llama intent parsing (TEST ENDPOINT - no authentication required).
    
    Security:
        - Only available when TEST_ENDPOINT_ENABLED=true
        - Only available in DEV/QA environments (blocked in staging/production)
        - Returns HTTP 403 if disabled
        
    Test Context:
        - Uses hardcoded test tenant: 00000000-0000-0000-0000-000000000001
        - Uses hardcoded test user: 00000000-0000-0000-0000-000000000002
        
    Processing Steps:
        1. Transcribe audio using Whisper Large-v3
        2. Parse intent using the local Llama model
        3. Store conversation and log latencies
        
    Usage:
        curl -X POST http://localhost:8000/api/v1/voice/command/test \\
          -F "audio=@test-audio.m4a" \\
          -F "session_id=optional-uuid-here"
          
    Returns:
        VoiceCommandResponse with transcription, parsed intent, and session ID
    """
    test_context = get_test_context()  # Raises 403 if disabled
    return await _process_voice_command_impl(audio, session_id, db, test_context)


# ============================================================
# B7b/A42 — Offline Voice Capture Endpoints
# ============================================================


from pydantic import ConfigDict


class VoiceUploadResponse(BaseModel):
    voice_command_log_id: int
    idempotency_uuid: uuid.UUID
    processing_status: str


class VoiceCommandStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    voice_command_log_id: int
    processing_status: str | None
    intent_detected: str | None
    action_executed: str | None
    pending_confirmation: bool
    captured_at: datetime | None
    transcribed_at: datetime | None
    parsed_at: datetime | None


# ---- Shared logic ----


def _upload_audio_impl(
    audio: UploadFile,
    captured_at: str,
    idempotency_uuid: uuid.UUID,
    conversation_session_id: uuid.UUID | None,
    originating_screen: str | None,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> VoiceUploadResponse:
    """Upload offline audio, create VoiceCommandLog row, enqueue processing task."""
    import boto3

    from core.config import settings

    # Idempotency check: if idempotency_uuid already exists, return existing row
    existing = db.exec(
        select(VoiceCommandLog)
        .where(VoiceCommandLog.idempotency_uuid == idempotency_uuid)
        .where(VoiceCommandLog.tenant_id == user_context.tenant_id)
    ).first()

    if existing:
        return VoiceUploadResponse(
            voice_command_log_id=existing.id,
            idempotency_uuid=idempotency_uuid,
            processing_status=existing.processing_status or "pending_upload",
        )

    # Parse captured_at timestamp
    try:
        from datetime import datetime as dt

        captured_dt = dt.fromisoformat(captured_at.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        captured_dt = datetime.now(UTC)

    # S3 object key for audio
    audio_key = f"tenants/{user_context.tenant_id}/voice/{idempotency_uuid}.m4a"

    # Upload to S3
    if settings.AWS_S3_PHOTOS_BUCKET_NAME:
        s3 = boto3.client("s3", region_name=settings.AWS_S3_REGION)
        audio_bytes = audio.file.read()
        s3.put_object(
            Bucket=settings.AWS_S3_PHOTOS_BUCKET_NAME,
            Key=audio_key,
            Body=audio_bytes,
            ContentType=audio.content_type or "audio/m4a",
        )

    # Create VoiceCommandLog row
    log_row = VoiceCommandLog(
        tenant_id=user_context.tenant_id,
        user_id=user_context.id,
        processing_status="pending_upload",
        audio_object_key=audio_key,
        captured_at=captured_dt,
        idempotency_uuid=idempotency_uuid,
        is_successful=True,
    )
    db.add(log_row)
    db.commit()
    db.refresh(log_row)

    # Enqueue async processing
    from tasks.voice_offline_tasks import process_voice_audio_async

    process_voice_audio_async.delay(log_row.id)

    return VoiceUploadResponse(
        voice_command_log_id=log_row.id,
        idempotency_uuid=idempotency_uuid,
        processing_status="pending_upload",
    )


def _get_voice_command_status_impl(
    idempotency_uuid: uuid.UUID,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> VoiceCommandStatusResponse:
    """Poll processing status by idempotency_uuid."""
    log_row = db.exec(
        select(VoiceCommandLog)
        .where(VoiceCommandLog.idempotency_uuid == idempotency_uuid)
        .where(VoiceCommandLog.tenant_id == user_context.tenant_id)
        .where(VoiceCommandLog.user_id == user_context.id)
    ).first()

    if not log_row:
        raise HTTPException(status_code=404, detail="Voice command not found")

    return VoiceCommandStatusResponse(
        voice_command_log_id=log_row.id,
        processing_status=log_row.processing_status,
        intent_detected=log_row.intent_detected,
        action_executed=log_row.action_executed,
        pending_confirmation=False,  # Full §16.3 wiring activates in next batch
        captured_at=log_row.captured_at,
        transcribed_at=log_row.transcribed_at,
        parsed_at=log_row.parsed_at,
    )


# ---- TEST endpoints (registered FIRST per §8.2) ----


@router.post(
    "/upload-audio/test",
    response_model=VoiceUploadResponse,
    status_code=202,
    summary="[TEST] Upload offline audio (no JWT)",
)
async def upload_audio_test(
    audio: UploadFile = File(...),
    captured_at: str = Form(...),
    idempotency_uuid: uuid.UUID = Form(...),
    conversation_session_id: uuid.UUID | None = Form(default=None),
    originating_screen: str | None = Form(default=None),
    db: Session = Depends(get_db),
):
    """Test endpoint — no auth required. Blocked in staging/production."""
    test_context = get_test_context()
    return _upload_audio_impl(
        audio,
        captured_at,
        idempotency_uuid,
        conversation_session_id,
        originating_screen,
        db,
        test_context,
    )


@router.get(
    "/command/{idempotency_uuid}/test",
    response_model=VoiceCommandStatusResponse,
    summary="[TEST] Poll voice command status (no JWT)",
)
def get_voice_command_status_test(
    idempotency_uuid: uuid.UUID,
    db: Session = Depends(get_db),
):
    """Test endpoint — no auth required. Blocked in staging/production."""
    test_context = get_test_context()
    return _get_voice_command_status_impl(idempotency_uuid, db, test_context)


# ---- AUTHENTICATED endpoints ----


@router.post(
    "/upload-audio",
    response_model=VoiceUploadResponse,
    status_code=202,
    summary="Upload offline-captured audio for async processing",
)
async def upload_audio(
    audio: UploadFile = File(...),
    captured_at: str = Form(...),
    idempotency_uuid: uuid.UUID = Form(...),
    conversation_session_id: uuid.UUID | None = Form(default=None),
    originating_screen: str | None = Form(default=None),
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("voice.create")),
):
    """
    Upload offline-captured audio for deferred transcription + intent parsing.
    Creates a VoiceCommandLog row and enqueues process_voice_audio_async.
    Idempotent: if idempotency_uuid already exists, returns existing status.
    """
    return _upload_audio_impl(
        audio,
        captured_at,
        idempotency_uuid,
        conversation_session_id,
        originating_screen,
        db,
        current_user,
    )


@router.get(
    "/command/{idempotency_uuid}",
    response_model=VoiceCommandStatusResponse,
    summary="Poll offline voice command processing status",
)
def get_voice_command_status(
    idempotency_uuid: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("voice.view")),
):
    """
    Poll the processing status of an offline voice command by its idempotency_uuid.
    The client uses this UUID before the upload completes (available before server PK).
    Returns 404 if not found for this tenant+user.
    """
    return _get_voice_command_status_impl(idempotency_uuid, db, current_user)
