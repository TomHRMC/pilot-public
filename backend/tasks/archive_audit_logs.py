"""
Background job to archive old audit events for compliance and cost optimization.

This module implements Celery tasks to:
1. Move audit events older than 90 days from hot storage to S3 archive
2. Delete from hot audit.event table to reduce RDS costs
3. Maintain compliance with 7-year retention requirements

Design Specification: Task #20 - Audit Event Logging + FIND-165
Gap Reference: Gap #29 in phase-1-4-implementation-gap-analysis.md
Database Design: Section 8 - Audit Event Logging (pilot-db-process-v2.6h.md)

Retention Policy:
    hot (audit.event) → 90 days (fast queries, indexed)
    cold (S3 archive) → 7 years (compliance, rarely accessed, Glacier after 90 days)

Cost Impact:
    - 100 tenants × 1,000 events/month = 100,000 events/month
    - 90 days hot: ~270,000 events × 1KB = 270MB RDS ($27/month at $0.10/GB)
    - 7 years archive: ~8.4M events → S3 Glacier = $0.004/GB/month = $0.03/month

S3 Archive Structure:
    s3://pilot-audit-archive/YYYY/MM/DD/{tenant_id}/audit-events-{timestamp}.jsonl.gz

Usage:
    # Manual execution
    python -m tasks.archive_audit_logs

    # Via Celery (when configured)
    celery -A core.celery_app worker --beat
"""

import gzip
import io
import json
import logging
from datetime import UTC, datetime, timedelta

import boto3
from sqlmodel import Session, select

from app.models.system import AuditEvent
from core.config import settings
from core.db import get_db

logger = logging.getLogger(__name__)

# Batch size for processing events (prevents memory pressure)
BATCH_SIZE = 1000


def _serialize_audit_event_to_dict(event: AuditEvent) -> dict:
    """
    Convert an AuditEvent ORM instance to a JSON-serializable dictionary.

    Args:
        event: AuditEvent ORM instance

    Returns:
        Dictionary with all audit event fields
    """
    return {
        "id": event.id,
        "occurred_at": event.occurred_at.isoformat() if event.occurred_at else None,
        "tenant_id": str(event.tenant_id) if event.tenant_id else None,
        "user_id": str(event.user_id) if event.user_id else None,
        "actor_type": event.actor_type,
        "user_role": event.user_role,
        "ip": event.ip,
        "user_agent": event.user_agent,
        "request_id": event.request_id,
        "correlation_id": event.correlation_id,
        "idempotency_key": event.idempotency_key,
        "entity_name": event.entity_name,
        "entity_id": event.entity_id,
        "action": event.action,
        "old_values": event.old_values,
        "new_values": event.new_values,
        "reason": event.reason,
        "contextdata": event.contextdata,
        "prev_hash": event.prev_hash,
        "self_hash": event.self_hash,
        "hashed_at": event.hashed_at.isoformat() if event.hashed_at else None,
    }


def _batch_export_to_s3(events: list[AuditEvent], timestamp: str) -> bool:
    """
    Export a batch of audit events to S3 as JSONL/gzip.

    Args:
        events: List of AuditEvent instances
        timestamp: ISO timestamp for file naming

    Returns:
        True if upload succeeded, False otherwise

    Side effects:
        - Creates S3 object at pilot-audit-archive/YYYY/MM/DD/{tenant_id}/audit-events-{timestamp}.jsonl.gz
        - Logs errors if upload fails
    """
    if not events:
        return True

    try:
        # Group events by tenant_id for S3 path organization
        events_by_tenant = {}
        for event in events:
            tenant_id = str(event.tenant_id) if event.tenant_id else "system"
            if tenant_id not in events_by_tenant:
                events_by_tenant[tenant_id] = []
            events_by_tenant[tenant_id].append(event)

        s3_client = boto3.client("s3", region_name=settings.AWS_S3_REGION)

        # Upload each tenant's batch separately
        for tenant_id, tenant_events in events_by_tenant.items():
            # Serialize all events in this batch to JSONL
            jsonl_lines = []
            for event in tenant_events:
                event_dict = _serialize_audit_event_to_dict(event)
                jsonl_lines.append(json.dumps(event_dict))

            # Compress
            jsonl_data = "\n".join(jsonl_lines).encode("utf-8")
            gzip_buffer = io.BytesIO()
            with gzip.GzipFile(fileobj=gzip_buffer, mode="wb") as gz_file:
                gz_file.write(jsonl_data)
            gzip_buffer.seek(0)

            # Compute S3 key path: YYYY/MM/DD/{tenant_id}/audit-events-{timestamp}.jsonl.gz
            dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            year = dt.strftime("%Y")
            month = dt.strftime("%m")
            day = dt.strftime("%d")
            s3_key = (
                f"{year}/{month}/{day}/{tenant_id}/audit-events-{timestamp}.jsonl.gz"
            )

            # Upload to S3
            s3_client.put_object(
                Bucket=settings.AUDIT_ARCHIVE_S3_BUCKET,
                Key=s3_key,
                Body=gzip_buffer.getvalue(),
                ContentType="application/gzip",
                ServerSideEncryption="AES256",
                Metadata={
                    "archive-timestamp": timestamp,
                    "tenant-id": tenant_id,
                    "event-count": str(len(tenant_events)),
                },
            )

            logger.info(
                f"Exported {len(tenant_events)} audit events to S3 "
                f"s3://{settings.AUDIT_ARCHIVE_S3_BUCKET}/{s3_key}"
            )

        return True

    except Exception as e:
        logger.error(f"Error exporting batch to S3: {e}", exc_info=True)
        return False


def archive_old_events(db: Session = None) -> dict[str, int]:
    """
    Move audit events older than 90 days to S3 archive, then delete from RDS.

    FIND-165 Implementation (2026-05-13):
    - Batch process events in chunks of 1,000 to avoid memory pressure
    - Serialize batch to JSONL (one JSON record per line)
    - gzip compress and upload to S3 before deleting from DB
    - Only delete from DB after confirmed S3 upload
    - If S3 upload fails, skip delete for safety and log error
    - Retry next run will re-process same batch

    Args:
        db: Optional database session (for testing). If None, creates new session.

    Returns:
        Dict with counts of archived and deleted events

    Example:
        >>> result = archive_old_events()
        >>> print(f"Archived {result['exported_count']} events")
        Archived 5420 events

    Safety:
        - Only deletes records >90 days old (configurable)
        - Exports to S3 BEFORE deleting from DB
        - If S3 upload fails, events remain in DB (retry next run)
        - Logs all operations for audit trail
        - Transaction-safe per batch
    """
    db_provided = db is not None
    if not db_provided:
        db = next(get_db())

    try:
        now = datetime.now(UTC)
        timestamp = now.isoformat()
        cutoff = now - timedelta(days=90)

        logger.info(f"Starting audit event archive (cutoff: {cutoff.isoformat()})")

        # Count total events to archive
        from sqlalchemy import func

        total_count_query = select(func.count(AuditEvent.id)).where(
            AuditEvent.occurred_at < cutoff
        )
        total_archival_count = db.exec(total_count_query).one()

        if total_archival_count == 0:
            logger.info(f"No audit events to archive (cutoff: {cutoff.isoformat()})")
            return {"exported_count": 0, "deleted_count": 0}

        # Process in batches of BATCH_SIZE
        exported_count = 0
        deleted_count = 0
        batch_num = 0

        while True:
            batch_num += 1

            # Fetch next batch of events to archive
            batch_query = (
                select(AuditEvent)
                .where(AuditEvent.occurred_at < cutoff)
                .order_by(AuditEvent.occurred_at)
                .limit(BATCH_SIZE)
            )
            batch_events = db.exec(batch_query).all()

            if not batch_events:
                break

            # Export batch to S3 before deleting
            upload_success = _batch_export_to_s3(batch_events, timestamp)

            if not upload_success:
                # S3 upload failed — stop processing, don't delete
                logger.error(
                    f"S3 upload failed for batch {batch_num}. "
                    f"Stopping archive process. Batch will be retried next run."
                )
                break

            # Only delete after confirmed S3 upload
            batch_ids = [e.id for e in batch_events]
            for event_id in batch_ids:
                event = db.exec(
                    select(AuditEvent).where(AuditEvent.id == event_id)
                ).first()
                if event:
                    db.delete(event)
            db.commit()

            exported_count += len(batch_events)
            deleted_count += len(batch_events)

            logger.info(
                f"Batch {batch_num}: Exported {len(batch_events)} events to S3 "
                f"and deleted from RDS (total: {deleted_count}/{total_archival_count})"
            )

        logger.info(
            f"Archive complete: {exported_count} events exported to S3, "
            f"{deleted_count} deleted from RDS"
        )

        return {
            "exported_count": exported_count,
            "deleted_count": deleted_count,
        }

    except Exception as e:
        logger.error(f"Error archiving audit events: {e}", exc_info=True)
        db.rollback()
        raise

    finally:
        if not db_provided:
            db.close()


def get_archive_statistics(db: Session = None) -> dict[str, any]:
    """
    Get statistics about audit event storage and archival candidates.

    Returns information useful for monitoring storage costs and archival health.

    Args:
        db: Optional database session

    Returns:
        Dict with statistics:
        - total_events: Total audit events in database
        - hot_events: Events < 90 days old (should stay)
        - archival_candidates: Events > 90 days old (should be archived)
        - oldest_event_date: Timestamp of oldest event
        - newest_event_date: Timestamp of newest event
        - estimated_storage_mb: Rough storage estimate

    Example:
        >>> stats = get_archive_statistics()
        >>> print(f"Ready to archive: {stats['archival_candidates']} events")
        Ready to archive: 5420 events
    """
    db_provided = db is not None
    if not db_provided:
        db = next(get_db())

    try:
        now = datetime.now(UTC)
        cutoff = now - timedelta(days=90)

        # Total events
        from sqlalchemy import func

        total_query = select(func.count(AuditEvent.id))
        total_events = db.exec(total_query).one()

        # Hot events (< 90 days)
        hot_query = select(func.count(AuditEvent.id)).where(
            AuditEvent.occurred_at >= cutoff
        )
        hot_events = db.exec(hot_query).one()

        # Archival candidates (> 90 days)
        archival_candidates = total_events - hot_events

        # Oldest and newest events
        oldest_query = select(func.min(AuditEvent.occurred_at))
        oldest_event_date = db.exec(oldest_query).one()

        newest_query = select(func.max(AuditEvent.occurred_at))
        newest_event_date = db.exec(newest_query).one()

        # Rough storage estimate (assume 1KB per event)
        estimated_storage_mb = round(total_events / 1024, 2)

        return {
            "total_events": total_events,
            "hot_events": hot_events,
            "archival_candidates": archival_candidates,
            "oldest_event_date": oldest_event_date.isoformat()
            if oldest_event_date
            else None,
            "newest_event_date": newest_event_date.isoformat()
            if newest_event_date
            else None,
            "estimated_storage_mb": estimated_storage_mb,
            "cutoff_date": cutoff.isoformat(),
        }

    finally:
        if not db_provided:
            db.close()


# ============================================================================
# Celery Task Definitions
# ============================================================================

from core.celery_app import celery_app


@celery_app.task(name="archive_audit_logs")
def archive_old_events_task():
    """
    Celery task wrapper for archive_old_events.

    Scheduled to run daily at 1 AM via Celery Beat.
    See core/celery_app.py for schedule configuration.
    """
    return archive_old_events()


@celery_app.task(name="audit_archive_stats")
def get_archive_statistics_task():
    """
    Celery task wrapper for get_archive_statistics.

    Useful for monitoring and alerting on archive health.
    Can be called manually or scheduled for daily reports.
    """
    return get_archive_statistics()


# ============================================================================
# CLI Execution (for manual testing or cron)
# ============================================================================

if __name__ == "__main__":
    """
    Run archive manually for testing or cron scheduling.
    
    Cron example (run daily at 1 AM):
    0 1 * * * cd /path/to/backend && python -m tasks.archive_audit_logs
    """
    print("=== Audit Event Archive (FIND-165) ===")
    print(f"Started at: {datetime.now(UTC).isoformat()}\n")

    # Get statistics before archival
    print("Statistics before archival:")
    stats_before = get_archive_statistics()
    print(f"  Total events: {stats_before['total_events']}")
    print(f"  Hot events (<90 days): {stats_before['hot_events']}")
    print(f"  Archival candidates (>90 days): {stats_before['archival_candidates']}")
    print(f"  Estimated storage: {stats_before['estimated_storage_mb']} MB")
    print(f"  Oldest event: {stats_before['oldest_event_date']}")
    print(f"  Newest event: {stats_before['newest_event_date']}\n")

    # Run archive
    result = archive_old_events()

    # Get statistics after archival
    print("\nStatistics after archival:")
    stats_after = get_archive_statistics()
    print(f"  Total events: {stats_after['total_events']}")
    print(f"  Hot events (<90 days): {stats_after['hot_events']}")
    print(f"  Archival candidates (>90 days): {stats_after['archival_candidates']}")
    print(f"  Estimated storage: {stats_after['estimated_storage_mb']} MB\n")

    # Summary
    print("Summary:")
    print(f"  - Events exported to S3: {result['exported_count']}")
    print(f"  - Events deleted from RDS: {result['deleted_count']}")
    print(f"  - Storage freed: ~{round(result['deleted_count'] / 1024, 2)} MB")
    print(
        f"  - S3 archive: s3://{settings.AUDIT_ARCHIVE_S3_BUCKET}/YYYY/MM/DD/{{tenant_id}}/..."
    )
    print(f"\nCompleted at: {datetime.now(UTC).isoformat()}")
