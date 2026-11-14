"""
Voice Session Title Generation Task.

Event-driven task: enqueued after the first substantive assistant turn in a session.
Established in B2 (A11). Extended in B12 (A67) to use voice persona tone.

Pattern: §17.2 Event-Driven Retryable Task (bind=True, max_retries=3)
"""

import logging
from typing import Any

from sqlmodel import Session

from core.celery_app import celery_app
from core.db import get_db

logger = logging.getLogger(__name__)


@celery_app.task(
    name="generate_session_title",
    bind=True,
    max_retries=3,
)
def generate_session_title(self, session_id: str) -> dict[str, Any]:
    """
    Generate an AI title for a conversation session after the first assistant turn.

    Only fires if title is NULL or title_auto_generated = TRUE — user-set titles
    (title_auto_generated = FALSE) are never overwritten.

    Enqueued by: POST /api/v1/voice/command after first assistant message in a session.
    Retries: 3 attempts with 60-second countdown on Ollama timeout.

    B12 extension point: When B12 is implemented, this task will call
    voice_persona_renderer.get_title_prompt(user_id) to inject the user's tone
    into the Ollama prompt. For MVP (B2), hardcoded neutral/descriptive tone.
    """
    db: Session = next(get_db())
    try:
        result = _generate_session_title_impl(session_id, db)
        return result
    except Exception as e:
        db.rollback()
        logger.error(f"Error generating session title for {session_id}: {e}")
        raise self.retry(exc=e, countdown=60)
    finally:
        db.close()


def _generate_session_title_impl(session_id: str, db: Session) -> dict[str, Any]:
    """
    Inner implementation — testable without Celery.

    Returns: {"session_id": str, "title": str | None, "skipped": bool}
    """
    import uuid

    from sqlmodel import select

    from app.models.ai import ConversationMessage, ConversationSession

    try:
        session_uuid = uuid.UUID(session_id)
    except ValueError:
        return {
            "session_id": session_id,
            "title": None,
            "skipped": True,
            "reason": "invalid_uuid",
        }

    session = db.exec(
        select(ConversationSession)
        .where(ConversationSession.id == session_uuid)
        .where(ConversationSession.is_active == True)
    ).first()

    if not session:
        return {
            "session_id": session_id,
            "title": None,
            "skipped": True,
            "reason": "session_not_found",
        }

    # Guard: user-set title is frozen (title_auto_generated = FALSE)
    if session.title is not None and not session.title_auto_generated:
        return {
            "session_id": session_id,
            "title": session.title,
            "skipped": True,
            "reason": "user_set_title_frozen",
        }

    # Fetch first 6 messages (3 turns) for session context
    messages = db.exec(
        select(ConversationMessage)
        .where(ConversationMessage.session_id == session_uuid)
        .order_by(ConversationMessage.created_at.asc())
        .limit(6)
    ).all()

    if not messages:
        return {
            "session_id": session_id,
            "title": None,
            "skipped": True,
            "reason": "no_messages",
        }

    conversation_excerpt = "\n".join(
        f"{msg.role.upper()}: {msg.content_text[:200]}"
        for msg in messages
        if msg.role in ("user", "assistant")
    )

    # B12/A67 extension: use voice_persona_renderer.generate_session_title()
    # to produce a tone-aware title using the session creator's effective tone.
    # Falls back to the inline Ollama prompt if the renderer is unavailable.
    try:
        from services.voice_persona_renderer import (
            generate_session_title as _render_title,
        )

        generated_title = _render_title(
            session_context=conversation_excerpt,
            creator_user_id=session.user_id,
            db=db,
            tenant_id=session.tenant_id,
        )
        generated_title = generated_title.strip()[:80]  # cap length
    except Exception as e:
        logger.warning(
            f"voice_persona_renderer.generate_session_title failed for session "
            f"{session_id}: {e}. Falling back to inline prompt."
        )
        # Fallback: inline neutral prompt (matches pre-B12 behaviour)
        try:
            from services.ai_service import generate_text_sync

            fallback_prompt = (
                f"Summarize this conversation in 3-5 words, suitable as a scannable title "
                f"in a chat history list. Be specific to the work discussed. "
                f"Respond with ONLY the title, no punctuation at end.\n\n"
                f"Conversation:\n{conversation_excerpt}"
            )
            generated_title = generate_text_sync(fallback_prompt, max_tokens=20)
            generated_title = generated_title.strip()[:80]
        except Exception as fallback_exc:
            logger.warning(
                f"Fallback Ollama title generation also failed for session {session_id}: {fallback_exc}"
            )
            return {
                "session_id": session_id,
                "title": None,
                "skipped": True,
                "reason": f"ollama_error: {fallback_exc!s}",
            }

    if not generated_title:
        return {
            "session_id": session_id,
            "title": None,
            "skipped": True,
            "reason": "empty_response",
        }

    session.title = generated_title
    session.title_auto_generated = True
    db.add(session)
    db.commit()

    return {"session_id": session_id, "title": generated_title, "skipped": False}
