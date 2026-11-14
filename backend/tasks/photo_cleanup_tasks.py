"""
tasks/photo_cleanup_tasks.py

Celery tasks for photo upload lifecycle management (B7b/A41).

Tasks:
    cleanup_incomplete_photo_uploads — periodic Beat task, weekly

Pattern: §17.1 Periodic Poll Task (no bind, no retry)
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from sqlmodel import Session, select

from app.models.fulfillment import JobAttachment
from core.celery_app import celery_app
from core.db import get_db

logger = logging.getLogger(__name__)


@celery_app.task(name="cleanup_incomplete_photo_uploads")
def cleanup_incomplete_photo_uploads() -> dict:
    """
    Weekly cleanup of orphaned job_attachment rows whose S3 multipart sessions
    never completed (§17.1 periodic poll pattern).

    Logic:
        1. Query job_attachment WHERE upload_status IN ('pending_upload', 'uploading')
           AND created_at < now() - 24 hours
        2. For each orphaned row: mark upload_status = 'failed'
        3. Log s3_upload_session_id for audit trail
        4. Return count for CloudWatch metric emission

    S3 lifecycle rule (configured via Terraform — not Alembic):
        Rule: ExpireMultipartUploads after 24 hours on photos bucket.
        This task handles the DB-side orphan records; S3 handles the byte cleanup.

    Returns:
        {"cleaned_up": N}
    """
    db: Session = next(get_db())
    cleaned_up = 0
    cutoff = datetime.now(UTC) - timedelta(hours=24)

    try:
        orphaned_rows = db.exec(
            select(JobAttachment)
            .where(JobAttachment.upload_status.in_(["pending_upload", "uploading"]))
            .where(JobAttachment.created_at < cutoff)
            .limit(500)  # Process in batches to avoid long-running transactions
        ).all()

        for row in orphaned_rows:
            logger.info(
                "Marking orphaned photo upload as failed: attachment_id=%s "
                "s3_session_id=%s tenant_id=%s",
                row.id,
                row.s3_upload_session_id,
                row.tenant_id,
            )
            row.upload_status = "failed"
            db.add(row)
            cleaned_up += 1

        if cleaned_up > 0:
            db.commit()

        logger.info("cleanup_incomplete_photo_uploads: cleaned up %d rows", cleaned_up)
        return {"cleaned_up": cleaned_up}

    except Exception as e:
        db.rollback()
        logger.error("Error in cleanup_incomplete_photo_uploads: %s", e)
        raise

    finally:
        db.close()


def _cleanup_incomplete_photo_uploads_impl(db: Session, cutoff_hours: int = 24) -> dict:
    """
    Inner implementation — separated for testability without Celery.
    Used by unit tests (§17.4 pattern).

    Args:
        db: SQLModel Session
        cutoff_hours: Hours before now to consider an upload orphaned.

    Returns:
        {"cleaned_up": N}
    """
    cleaned_up = 0
    cutoff = datetime.now(UTC) - timedelta(hours=cutoff_hours)

    orphaned_rows = db.exec(
        select(JobAttachment)
        .where(JobAttachment.upload_status.in_(["pending_upload", "uploading"]))
        .where(JobAttachment.created_at < cutoff)
        .limit(500)
    ).all()

    for row in orphaned_rows:
        row.upload_status = "failed"
        db.add(row)
        cleaned_up += 1

    if cleaned_up > 0:
        db.commit()

    return {"cleaned_up": cleaned_up}
