"""
Background jobs to manage voice AI conversation session lifecycle.

This module implements Celery tasks to:
1. Expire old sessions (>24 hours) and generate summaries
2. Archive expired sessions (>30 days) for cold storage
3. Cleanup orphaned conversation messages

Design Specification: Task #15 - Session Expiration & Cleanup
Gap Reference: Gap #19 in phase-1-4-implementation-gap-analysis.md
Database Design: Section 8 - Background Jobs Catalog (pilot-db-process-v2.6h.md)

Session Lifecycle:
    active → expired (24 hours) → archived (30 days)

Usage:
    # Manual execution
    python -m tasks.cleanup_sessions

    # Via Celery (when configured)
    celery -A core.celery_app worker --beat
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import func
from sqlmodel import Session, select

from app.models.ai import ConversationMessage, ConversationSession
from core.db import get_db


def generate_session_summary(session: ConversationSession, db: Session) -> str:
    """
    Extract key information from context_window_json and message count.

    Args:
        session: ConversationSession to summarize
        db: Database session

    Returns:
        Summary string with entities and message count

    Example:
        >>> summary = generate_session_summary(session, db)
        >>> print(summary)
        "Customer: 123, Quote: 456, 5 messages"
    """
    context = session.context_window_json or {}
    parts = []

    # Extract entities from context window
    if "active_customer_id" in context:
        parts.append(f"Customer: {context['active_customer_id']}")
    if "active_quote_id" in context:
        parts.append(f"Quote: {context['active_quote_id']}")
    if "active_job_id" in context:
        parts.append(f"Job: {context['active_job_id']}")

    # Count messages in this session
    msg_count = db.exec(
        select(func.count(ConversationMessage.id)).where(
            ConversationMessage.session_id == session.id
        )
    ).one()
    parts.append(f"{msg_count} messages")

    return ", ".join(parts) if parts else "Empty session"


def expire_old_sessions(db: Session = None) -> dict[str, int]:
    """
    Mark conversation sessions > 24 hours old as expired.
    Generate final summary from context_window_json.

    Args:
        db: Optional database session (for testing). If None, creates new session.

    Returns:
        Dict with counts of expired sessions and summaries generated

    Example:
        >>> result = expire_old_sessions()
        >>> print(f"Expired {result['expired_count']} sessions")
    """
    db_provided = db is not None
    if not db_provided:
        db = next(get_db())

    try:
        now = datetime.now(UTC)
        cutoff = now - timedelta(hours=24)

        # Find active sessions older than 24 hours
        old_sessions = db.exec(
            select(ConversationSession)
            .where(ConversationSession.status == "active")
            .where(ConversationSession.created_at < cutoff)
        ).all()

        expired_count = len(old_sessions)

        if expired_count == 0:
            print(
                f"[{now.isoformat()}] No active sessions to expire (cutoff: {cutoff.isoformat()})"
            )
            return {"expired_count": 0, "summary_generated_count": 0}

        summary_count = 0

        # Process each session
        for session in old_sessions:
            # Mark as expired
            session.status = "abandoned"
            session.is_active = False
            session.expires_at = now
            session.updated_at = now

            # Generate summary from context if not already present
            if not session.context_summary:
                session.context_summary = generate_session_summary(session, db)
                summary_count += 1

            db.add(session)

        # Commit all changes atomically
        db.commit()

        print(
            f"[{now.isoformat()}] Expired {expired_count} sessions, generated {summary_count} summaries"
        )
        return {
            "expired_count": expired_count,
            "summary_generated_count": summary_count,
        }

    except Exception as e:
        print(f"[{datetime.now(UTC).isoformat()}] Error expiring old sessions: {e}")
        db.rollback()
        raise

    finally:
        if not db_provided:
            db.close()


def archive_old_sessions(db: Session = None) -> dict[str, int]:
    """
    Mark sessions > 30 days old for archival to cold storage.
    MVP: Just mark status='archived', actual S3 upload deferred to post-MVP.

    Args:
        db: Optional database session (for testing). If None, creates new session.

    Returns:
        Dict with count of archived sessions

    Example:
        >>> result = archive_old_sessions()
        >>> print(f"Archived {result['archived_count']} sessions")
    """
    db_provided = db is not None
    if not db_provided:
        db = next(get_db())

    try:
        now = datetime.now(UTC)
        cutoff = now - timedelta(days=30)

        # Find expired sessions older than 30 days
        old_expired_sessions = db.exec(
            select(ConversationSession)
            .where(ConversationSession.status == "abandoned")
            .where(ConversationSession.expires_at < cutoff)
        ).all()

        archived_count = len(old_expired_sessions)

        if archived_count == 0:
            print(
                f"[{now.isoformat()}] No expired sessions to archive (cutoff: {cutoff.isoformat()})"
            )
            return {"archived_count": 0}

        # Mark each session as archived
        for session in old_expired_sessions:
            session.status = "ended"
            # Keep is_active=False (already set when expired)
            session.updated_at = now
            db.add(session)

        # Commit all changes atomically
        db.commit()

        print(
            f"[{now.isoformat()}] Archived {archived_count} sessions for cold storage"
        )
        print(f"[{now.isoformat()}] MVP: S3 upload deferred to post-MVP (Phase 4+)")
        return {"archived_count": archived_count}

    except Exception as e:
        print(f"[{datetime.now(UTC).isoformat()}] Error archiving old sessions: {e}")
        db.rollback()
        raise

    finally:
        if not db_provided:
            db.close()


def cleanup_orphaned_messages(db: Session = None) -> dict[str, int]:
    """
    Delete conversation_message records without valid session_id.
    Safety: Only delete messages > 7 days old to prevent race conditions.

    Args:
        db: Optional database session (for testing). If None, creates new session.

    Returns:
        Dict with count of deleted messages

    Example:
        >>> result = cleanup_orphaned_messages()
        >>> print(f"Cleaned up {result['deleted_count']} orphaned messages")
    """
    db_provided = db is not None
    if not db_provided:
        db = next(get_db())

    try:
        now = datetime.now(UTC)
        cutoff = now - timedelta(days=7)

        # Find orphaned messages (session_id doesn't exist) older than 7 days
        # Using subquery to find messages without valid session
        orphaned_messages = db.exec(
            select(ConversationMessage)
            .outerjoin(
                ConversationSession,
                ConversationMessage.session_id == ConversationSession.id,
            )
            .where(ConversationSession.id.is_(None))
            .where(ConversationMessage.created_at < cutoff)
        ).all()

        deleted_count = len(orphaned_messages)

        if deleted_count == 0:
            print(
                f"[{now.isoformat()}] No orphaned messages to clean up (cutoff: {cutoff.isoformat()})"
            )
            return {"deleted_count": 0}

        # Delete orphaned messages
        for message in orphaned_messages:
            db.delete(message)

        # Commit all deletions atomically
        db.commit()

        print(
            f"[{now.isoformat()}] Cleaned up {deleted_count} orphaned messages (>7 days old)"
        )
        return {"deleted_count": deleted_count}

    except Exception as e:
        print(
            f"[{datetime.now(UTC).isoformat()}] Error cleaning up orphaned messages: {e}"
        )
        db.rollback()
        raise

    finally:
        if not db_provided:
            db.close()


# Celery task definitions (Gap #21 - Celery Setup Complete)
# Activated as part of Task #15 - Session Expiration & Cleanup

from core.celery_app import celery_app


@celery_app.task(name="expire_old_sessions")
def expire_old_sessions_task():
    """Celery task wrapper for expire_old_sessions"""
    return expire_old_sessions()


@celery_app.task(name="archive_old_sessions")
def archive_old_sessions_task():
    """Celery task wrapper for archive_old_sessions"""
    return archive_old_sessions()


@celery_app.task(name="cleanup_orphaned_messages")
def cleanup_orphaned_messages_task():
    """Celery task wrapper for cleanup_orphaned_messages"""
    return cleanup_orphaned_messages()


if __name__ == "__main__":
    """
    Run cleanup manually for testing or cron scheduling.

    Cron example (run daily at 3 AM):
    0 3 * * * cd /path/to/backend && python -m tasks.cleanup_sessions
    """
    print("=== Conversation Session Cleanup ===")
    print(f"Started at: {datetime.now(UTC).isoformat()}")

    expire_result = expire_old_sessions()
    archive_result = archive_old_sessions()
    cleanup_result = cleanup_orphaned_messages()

    print("\nSummary:")
    print(f"  - Sessions expired: {expire_result['expired_count']}")
    print(f"  - Summaries generated: {expire_result['summary_generated_count']}")
    print(f"  - Sessions archived: {archive_result['archived_count']}")
    print(f"  - Orphaned messages deleted: {cleanup_result['deleted_count']}")
    print(f"\nCompleted at: {datetime.now(UTC).isoformat()}")
