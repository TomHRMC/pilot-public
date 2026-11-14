"""
Help corpus Celery tasks — B16/A85, A84, A87, A88.

Tasks:
    process_help_article        — Event-driven (§17.2): embed a help article. Retryable.
    generate_help_session_title — Event-driven (§17.2): auto-title a help chat session.
    anonymize_help_sessions     — Periodic poll (§17.1): daily anonymization pipeline.
    send_feedback_email         — Event-driven (§17.2): send feedback to support. Retryable.
"""

import hashlib
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlmodel import Session, select

from core.celery_app import celery_app
from core.config import settings
from core.db import get_db
from services.ai_service import generate_text_sync
from services.email_service import send_email
from services.help_corpus import process_article

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# A85 — Corpus embedding task
# ──────────────────────────────────────────────────────────────────────────────


@celery_app.task(
    name="process_help_article",
    bind=True,
    max_retries=3,
)
def process_help_article(self, article_id: str, s3_path: str) -> dict[str, Any]:
    """
    Embed a help article into pgvector.
    Triggered by S3 event or manual admin trigger via POST /api/v1/admin/help/articles/{id}/reprocess.
    Retries on OpenAI API or S3 transient failures with 60-second countdown.
    Pattern: §17.2 Event-Driven Retryable Task.
    """
    db: Session = next(get_db())
    try:
        result = _process_help_article_impl(article_id, s3_path, db)
        return result
    except ValueError:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error processing article {article_id}: {e}")
        raise self.retry(exc=e, countdown=60)
    finally:
        db.close()


def _process_help_article_impl(
    article_id: str, s3_path: str, db: Session
) -> dict[str, Any]:
    """Inner implementation — separated for testability without Celery."""

    return process_article(article_id=article_id, s3_path=s3_path, db=db)


# ──────────────────────────────────────────────────────────────────────────────
# A84 — Help session title generation task
# ──────────────────────────────────────────────────────────────────────────────


@celery_app.task(
    name="generate_help_session_title",
    bind=True,
    max_retries=3,
)
def generate_help_session_title(
    self, session_id: str, first_user_message: str
) -> dict[str, Any]:
    """
    Generate an AI title for a help chat session after the first turn.
    Enqueued by POST /api/v1/help/chat after first assistant message.
    Only fires if title is NULL — never overwrites an existing title.
    Pattern: §17.2 Event-Driven Retryable Task.
    """
    db: Session = next(get_db())
    try:
        result = _generate_help_session_title_impl(session_id, first_user_message, db)
        return result
    except Exception as e:
        db.rollback()
        logger.error(f"Error generating help session title for {session_id}: {e}")
        raise self.retry(exc=e, countdown=60)
    finally:
        db.close()


def _generate_help_session_title_impl(
    session_id: str, first_user_message: str, db: Session
) -> dict[str, Any]:
    """Inner implementation — testable without Celery."""
    import uuid

    from app.models.help import HelpChatSession

    try:
        session_uuid = uuid.UUID(session_id)
    except ValueError:
        return {
            "session_id": session_id,
            "title": None,
            "skipped": True,
            "reason": "invalid_uuid",
        }

    # FIND-169: session_id → id on HelpChatSession
    session = db.exec(
        select(HelpChatSession).where(HelpChatSession.id == session_uuid)
    ).first()

    if not session:
        return {
            "session_id": session_id,
            "title": None,
            "skipped": True,
            "reason": "session_not_found",
        }

    if session.title is not None:
        return {
            "session_id": session_id,
            "title": session.title,
            "skipped": True,
            "reason": "title_already_set",
        }

    try:
        prompt = (
            f"Generate a 3-5 word title for a help conversation that started with: "
            f"'{first_user_message[:200]}'. Return ONLY the title, no quotes or punctuation."
        )
        title = generate_text_sync(prompt=prompt, max_tokens=20).strip()[:80]
    except Exception as e:
        logger.warning(
            f"Ollama title generation failed for help session {session_id}: {e}"
        )
        return {
            "session_id": session_id,
            "title": None,
            "skipped": True,
            "reason": f"ollama_error: {e}",
        }

    if not title:
        return {
            "session_id": session_id,
            "title": None,
            "skipped": True,
            "reason": "empty_response",
        }

    session.title = title
    db.add(session)
    db.commit()

    return {"session_id": session_id, "title": title, "skipped": False}


# ──────────────────────────────────────────────────────────────────────────────
# A87 — Feedback email dispatch task
# ──────────────────────────────────────────────────────────────────────────────


@celery_app.task(
    name="send_feedback_email",
    bind=True,
    max_retries=3,
)
def send_feedback_email(self, submission_id: str) -> dict[str, Any]:
    """
    Send feedback submission to support email via SendGrid.
    Enqueued by POST /api/v1/feedback after creating the submission record.
    Pattern: §17.2 Event-Driven Retryable Task.
    """
    db: Session = next(get_db())
    try:
        result = _send_feedback_email_impl(submission_id, db)
        return result
    except ValueError:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error sending feedback email for {submission_id}: {e}")
        raise self.retry(exc=e, countdown=60)
    finally:
        db.close()


def _send_feedback_email_impl(submission_id: str, db: Session) -> dict[str, Any]:
    """Inner implementation — testable without Celery."""
    import uuid

    from app.models.core import User
    from app.models.help import FeedbackSubmission

    try:
        sub_uuid = uuid.UUID(submission_id)
    except ValueError:
        raise ValueError(f"Invalid submission_id: {submission_id}")

    submission = db.exec(
        select(FeedbackSubmission).where(FeedbackSubmission.submission_id == sub_uuid)
    ).first()

    if not submission:
        raise ValueError(f"FeedbackSubmission {submission_id} not found")

    user = db.get(User, submission.user_id)
    user_email = user.email if user else "unknown@unknown.com"
    user_name = getattr(user, "full_name", None) or user_email

    category_display = submission.category.replace("_", " ").title()
    subject = f"[Pilot Feedback - {category_display}] {submission.body[:60]}"

    body = _render_feedback_email_body(submission, user_name, user_email)

    result = send_email(
        to=settings.SUPPORT_EMAIL_ADDRESS,
        subject=subject,
        body=body,
    )

    # Store the SendGrid message ID for delivery tracking
    msg_id = result.get("details", {}).get("headers", {}).get("X-Message-Id")
    if msg_id:
        submission.email_message_id = msg_id
        db.add(submission)
        db.commit()

    return {"status": result.get("status", "sent"), "message_id": msg_id}


def _render_feedback_email_body(
    submission: Any, user_name: str, user_email: str
) -> str:
    """Render the plain-text feedback email body."""
    lines = [
        f"Feedback from: {user_name} <{user_email}>",
        f"Category: {submission.category.replace('_', ' ').title()}",
        f"Submission ID: {submission.submission_id}",
        "",
        "--- Feedback ---",
        submission.body,
        "",
    ]
    if submission.from_help_chat_session_id:
        lines.append(f"Help Chat Session: {submission.from_help_chat_session_id}")
    return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────────────────
# A88 — Anonymization pipeline task
# ──────────────────────────────────────────────────────────────────────────────


@celery_app.task(name="anonymize_help_sessions")
def anonymize_help_sessions() -> dict[str, int]:
    """
    Daily task: anonymize help sessions >= 90 days old.
    Applies PII detection, writes to help_training_corpus, deletes original messages.
    Pattern: §17.1 Periodic Poll Task (no bind, no retry).
    """
    db: Session = next(get_db())
    anonymized = 0
    try:
        cutoff = datetime.now(UTC) - timedelta(days=90)

        from app.models.help import HelpChatSession

        sessions = db.exec(
            select(HelpChatSession)
            .where(HelpChatSession.last_activity_at <= cutoff)
            .where(HelpChatSession.anonymized_at == None)
            .limit(200)
        ).all()

        for session in sessions:
            _anonymize_session_impl(session, db)
            anonymized += 1

        db.commit()
        logger.info(f"anonymize_help_sessions: anonymized {anonymized} sessions")
        return {"anonymized": anonymized}
    except Exception as e:
        db.rollback()
        logger.error(f"Error in anonymize_help_sessions: {e}")
        raise
    finally:
        db.close()


def _anonymize_session_impl(session: Any, db: Session) -> None:
    """
    Anonymize a single help chat session:
    1. Load all messages
    2. Anonymize PII in message content and context payloads
    3. Write to help_training_corpus (skip if already exists — hash dedup)
    4. Mark session as anonymized (keeps session row, messages deleted via CASCADE)
    """
    from app.models.help import HelpChatMessage, HelpTrainingCorpus
    from services.pii_anonymizer import anonymize_context_payload, anonymize_text

    # Load messages ordered by time
    # FIND-169: session.session_id → session.id
    messages = db.exec(
        select(HelpChatMessage)
        .where(HelpChatMessage.session_id == session.id)
        .order_by(HelpChatMessage.created_at.asc())
    ).all()

    # Compute dedup hash
    session_id_hash = hashlib.sha256(str(session.id).encode()).hexdigest()

    # Check if already processed
    existing_corpus = db.exec(
        select(HelpTrainingCorpus).where(
            HelpTrainingCorpus.original_session_id_hash == session_id_hash
        )
    ).first()

    if not existing_corpus:
        # Build anonymized message history
        anon_history = []
        for msg in messages:
            anon_entry: dict = {
                "role": msg.role,
                "content": anonymize_text(msg.content),
            }
            if msg.retrieved_chunks:
                # Only keep chunk IDs (not content) for training lineage
                chunk_ids = []
                if isinstance(msg.retrieved_chunks, list):
                    chunk_ids = [
                        c.get("chunk_id")
                        for c in msg.retrieved_chunks
                        if c.get("chunk_id")
                    ]
                elif isinstance(msg.retrieved_chunks, dict):
                    chunk_ids = msg.retrieved_chunks.get("chunk_ids", [])
                anon_entry["retrieved_chunks_summary"] = chunk_ids
            anon_history.append(anon_entry)

        # Anonymize context payload from first user message
        anon_context = None
        for msg in messages:
            if msg.role == "user" and msg.context_payload:
                anon_context = anonymize_context_payload(msg.context_payload)
                break

        now_utc = datetime.now(UTC)
        corpus_entry = HelpTrainingCorpus(
            original_session_id_hash=session_id_hash,
            anonymized_message_history=anon_history,
            anonymized_context_payload=anon_context,
            category_inferred=None,  # Phase 2: AI classification
            outcome=session.outcome or "abandoned",
            anonymized_at=now_utc,
            created_at=now_utc,
        )
        db.add(corpus_entry)

    # Mark session as anonymized and delete messages (CASCADE)
    # Delete messages explicitly (ON DELETE CASCADE on session delete, but session stays)
    for msg in messages:
        db.delete(msg)

    session.anonymized_at = datetime.now(UTC)
    db.add(session)
