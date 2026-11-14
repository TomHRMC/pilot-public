"""
Background job to clean up expired idempotency keys.

This task removes idempotency keys that have passed their expiration time (expires_at).
Should be run daily via cron or Celery Beat scheduler.

Design Specification: Gap #28B - Idempotency Key Handling
TTL: 24 hours (configurable via IDEMPOTENCY_TTL_HOURS)

Usage:
    # Manual execution
    python -m tasks.cleanup_idempotency_keys

    # Via Celery (when configured)
    celery -A tasks.cleanup_idempotency_keys worker --beat
"""

from datetime import UTC, datetime

from sqlmodel import Session, select

from app.models.system import IdempotencyKey
from core.db import get_db


def cleanup_expired_idempotency_keys() -> int:
    """
    Delete idempotency keys that have expired.

    Returns:
        Number of keys deleted

    Example:
        >>> count = cleanup_expired_idempotency_keys()
        >>> print(f"Cleaned up {count} expired keys")
    """
    db: Session = next(get_db())

    try:
        # Find expired keys
        now = datetime.now(UTC)
        expired_keys = db.exec(
            select(IdempotencyKey).where(IdempotencyKey.expires_at < now)
        ).all()

        count = len(expired_keys)

        if count == 0:
            print(f"[{now.isoformat()}] No expired idempotency keys to clean up")
            return 0

        # Delete them
        for key in expired_keys:
            db.delete(key)

        db.commit()

        print(f"[{now.isoformat()}] Cleaned up {count} expired idempotency keys")
        return count

    except Exception as e:
        print(
            f"[{datetime.now(UTC).isoformat()}] Error cleaning up idempotency keys: {e}"
        )
        db.rollback()
        raise

    finally:
        db.close()


def cleanup_old_failed_keys(days_old: int = 7) -> int:
    """
    Delete old failed idempotency keys.

    Failed keys can accumulate if clients never retry. Clean up keys that
    have been in 'failed' status for more than the specified days.

    Args:
        days_old: Delete failed keys older than this many days (default: 7)

    Returns:
        Number of keys deleted
    """
    from datetime import timedelta

    db: Session = next(get_db())

    try:
        cutoff_date = datetime.now(UTC) - timedelta(days=days_old)

        old_failed_keys = db.exec(
            select(IdempotencyKey).where(
                IdempotencyKey.status == "failed",
                IdempotencyKey.first_seen_at < cutoff_date,
            )
        ).all()

        count = len(old_failed_keys)

        if count == 0:
            print(f"[{datetime.now(UTC).isoformat()}] No old failed keys to clean up")
            return 0

        for key in old_failed_keys:
            db.delete(key)

        db.commit()

        print(
            f"[{datetime.now(UTC).isoformat()}] Cleaned up {count} old failed idempotency keys (>{days_old} days)"
        )
        return count

    except Exception as e:
        print(
            f"[{datetime.now(UTC).isoformat()}] Error cleaning up old failed keys: {e}"
        )
        db.rollback()
        raise

    finally:
        db.close()


# Celery task definitions (Gap #21 - Celery Setup Complete)
# Activated as part of Task #12 - Celery Setup & Configuration

from core.celery_app import celery_app


@celery_app.task(name="cleanup_expired_idempotency_keys")
def cleanup_expired_idempotency_keys_task():
    """Celery task wrapper for cleanup_expired_idempotency_keys"""
    return cleanup_expired_idempotency_keys()


@celery_app.task(name="cleanup_old_failed_keys")
def cleanup_old_failed_keys_task(days_old: int = 7):
    """Celery task wrapper for cleanup_old_failed_keys"""
    return cleanup_old_failed_keys(days_old)


if __name__ == "__main__":
    """
    Run cleanup manually for testing or cron scheduling.
    
    Cron example (run daily at 2 AM):
    0 2 * * * cd /path/to/backend && python -m tasks.cleanup_idempotency_keys
    """
    print("=== Idempotency Key Cleanup ===")
    print(f"Started at: {datetime.now(UTC).isoformat()}")

    expired_count = cleanup_expired_idempotency_keys()
    failed_count = cleanup_old_failed_keys(days_old=7)

    print("\nSummary:")
    print(f"  - Expired keys removed: {expired_count}")
    print(f"  - Old failed keys removed: {failed_count}")
    print(f"  - Total removed: {expired_count + failed_count}")
    print(f"\nCompleted at: {datetime.now(UTC).isoformat()}")
