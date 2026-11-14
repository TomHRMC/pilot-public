"""
tasks/mobile_sync_cleanup.py

Celery Beat task for archiving old mobile sync events (FIND-088).

FIND-088 remediation: Archive mobile_sync_event rows older than 30 days
to prevent unbounded table growth while maintaining recent sync history
for troubleshooting.

Run schedule: Daily 3:00 AM UTC via Celery Beat
Cleanup window: Rows with created_at < now() - 30 days
Index: ix_mobile_sync_event_created_at
"""

import logging
from datetime import UTC, datetime, timedelta

from sqlmodel import Session, select

from app.models.sync import MobileSyncEvent
from app.models.system import MobileSyncOwnerEscalation
from core.celery_app import celery_app
from core.db import get_db

logger = logging.getLogger(__name__)


@celery_app.task(name="archive_old_mobile_sync_events")
def archive_old_mobile_sync_events() -> dict[str, int]:
    """
    Archive (delete) mobile_sync_event rows older than 30 days.

    This task runs on Celery Beat daily at 3:00 AM UTC.
    It removes rows where created_at < now() - 30 days, using the
    ix_mobile_sync_event_created_at index for efficient scanning.

    Skips events that are still referenced by mobile_sync_owner_escalation
    rows (FK ondelete=RESTRICT prevents deletion of referenced events).

    Returns:
        Dict with keys:
            - rows_deleted: count of rows removed
            - error: any error message if cleanup failed
    """
    db: Session = next(get_db())
    cutoff_date = datetime.now(UTC) - timedelta(days=30)
    rows_deleted = 0

    try:
        # Collect all event IDs referenced by escalation records.
        # select(Model.column) returns raw values, not model objects.
        escalation_conflict_ids = set(
            db.exec(select(MobileSyncOwnerEscalation.conflict_id)).all()
        )

        # Query old rows using the index, excluding FK-referenced events
        old_events = db.exec(
            select(MobileSyncEvent)
            .where(MobileSyncEvent.created_at < cutoff_date)
            .limit(10000)  # Batch delete to avoid locking for too long
        ).all()

        for event in old_events:
            # Skip events still referenced by escalation records (FK RESTRICT)
            if event.id in escalation_conflict_ids:
                logger.debug(
                    f"Skipping event {event.id} — referenced by an escalation record"
                )
                continue
            db.delete(event)
            rows_deleted += 1

        db.commit()
        logger.info(
            f"archive_old_mobile_sync_events: deleted {rows_deleted} "
            f"rows older than {cutoff_date.isoformat()}"
        )
        return {"rows_deleted": rows_deleted}

    except Exception as e:
        db.rollback()
        logger.error(f"Error in archive_old_mobile_sync_events: {e}")
        raise

    finally:
        db.close()
