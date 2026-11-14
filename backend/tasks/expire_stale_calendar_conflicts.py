"""
Celery Beat task: expire_stale_calendar_conflicts — B6/A34

Daily task that:
  1. Iterates all tenants with active calendar integrations
  2. Resolves effective expire_days and pre_warning_days per tenant (two-tier §16.5)
  3. Sends pre-warning notification at (expire_days - pre_warning_days) days old
  4. Auto-resolves conflicts >= expire_days old to 'accept_local'
  5. Flags auto_resolved_stale = TRUE on resolved rows
  6. Logs auto-resolution to calendar_sync_log

Registration: added to core/celery_app.py beat schedule at 02:00 UTC daily.
"""

import logging
from datetime import UTC, datetime

from core.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="tasks.expire_stale_calendar_conflicts")
def expire_stale_calendar_conflicts() -> dict[str, int]:
    """
    Daily Celery Beat task for calendar conflict auto-expiry (A34).

    Returns:
        dict: {"expired": int, "pre_warned": int, "tenants_processed": int}
    """
    from sqlmodel import Session

    from core.db import get_db

    db: Session = next(get_db())
    try:
        return _expire_stale_calendar_conflicts_impl(db)
    finally:
        db.close()


def _expire_stale_calendar_conflicts_impl(db=None) -> dict[str, int]:
    """
    Inner implementation — separated for testability without Celery (§17.4).

    Args:
        db: SQLModel Session. If None, creates its own session.
            In tests, pass the test db_session to share transaction visibility.

    Logic per tenant:
      1. If calendar_conflict_auto_expire_enabled is FALSE → skip
      2. Resolve effective expire_days (tenant override or system default 30)
      3. Resolve effective pre_warning_days (tenant override or system default 7)
      4. Send pre-warning push at (expire_days - pre_warning_days) old (dedup via outbox)
      5. Auto-resolve conflicts >= expire_days old → 'accept_local', set auto_resolved_stale=TRUE
      6. Write calendar_sync_log entry for each auto-resolution
    """
    from sqlmodel import select

    from app.models.scheduling import (
        CalendarSyncConflict,
        CalendarSyncLog,
        TenantCalendarIntegration,
    )
    from app.models.system import NotificationOutbox
    from services.calendar_conflict_service import CalendarConflictService

    _owns_session = False
    if db is None:
        from core.db import get_db

        db = next(get_db())
        _owns_session = True

    expired = 0
    pre_warned = 0
    tenants_processed = 0

    try:
        # Fetch all tenants with active calendar integrations
        active_integrations = db.exec(
            select(TenantCalendarIntegration).where(
                TenantCalendarIntegration.sync_status == "active"
            )
        ).all()

        now = datetime.now(UTC)

        for integration in active_integrations:
            tenant_id = integration.tenant_id
            tenants_processed += 1

            # Resolve effective settings via DB resolver (post-FIND-086)
            expire_days = CalendarConflictService.get_effective_expire_days(
                db, tenant_id
            )

            # If auto-expiry is disabled for this tenant, skip
            if expire_days is None:
                continue

            pre_warning_days = CalendarConflictService.get_effective_pre_warning_days(
                db, tenant_id
            )

            # Fetch pending conflicts for this tenant
            pending_conflicts = db.exec(
                select(CalendarSyncConflict).where(
                    CalendarSyncConflict.tenant_id == tenant_id,
                    CalendarSyncConflict.resolution.is_(None),  # type: ignore[union-attr]
                    CalendarSyncConflict.auto_resolved_stale == False,
                )
            ).all()

            for conflict in pending_conflicts:
                age_days = (now - conflict.created_at).days

                # Pre-warning check
                if pre_warning_days is not None:
                    pre_warning_threshold = expire_days - pre_warning_days
                    if pre_warning_threshold <= age_days < expire_days:
                        # Check dedup: already sent pre-warning?
                        existing_warning = db.exec(
                            select(NotificationOutbox).where(
                                NotificationOutbox.tenant_id == tenant_id,
                                NotificationOutbox.contextdata[  # type: ignore[index]
                                    "conflict_id"
                                ].as_string()
                                == str(conflict.id),
                                NotificationOutbox.contextdata[  # type: ignore[index]
                                    "notification_subtype"
                                ].as_string()
                                == "pre_warning",
                            )
                        ).first()

                        if not existing_warning:
                            # Enqueue pre-warning in_app notification
                            # B8/A51: 'push' channel (APNs/FCM) deferred to B8.
                            # Using 'in_app' for B6 MVP scope.
                            notification = NotificationOutbox(
                                tenant_id=tenant_id,
                                channel="in_app",
                                body=(
                                    f"Calendar conflict will auto-resolve in "
                                    f"{expire_days - age_days} days. Review in Pilot."
                                ),
                                status="pending",
                                attempt_count=0,
                                priority=5,
                                contextdata={
                                    "event_type": "calendar_conflict_pre_warning",
                                    "notification_subtype": "pre_warning",
                                    "conflict_id": str(conflict.id),
                                    "tenant_id": str(tenant_id),
                                    "expires_in_days": expire_days - age_days,
                                },
                                category_id="sync_conflicts",  # B10/A56
                            )
                            db.add(notification)
                            pre_warned += 1

                # Auto-expiry check
                if age_days >= expire_days:
                    conflict.resolution = "accept_local"
                    conflict.auto_resolved_stale = True
                    conflict.resolved_at = now
                    db.add(conflict)

                    # Log to calendar_sync_log
                    sync_log = CalendarSyncLog(
                        tenant_id=tenant_id,
                        direction="pull",
                        entity_type="job",
                        entity_id=conflict.job_id,
                        status="success",
                        error_detail=None,
                        payload_snapshot={
                            "event": "auto_resolved_stale",
                            "conflict_id": str(conflict.id),
                            "resolution": "accept_local",
                            "age_days": age_days,
                        },
                    )
                    db.add(sync_log)
                    expired += 1

        db.commit()
        logger.info(
            "expire_stale_calendar_conflicts completed: "
            f"tenants={tenants_processed} expired={expired} pre_warned={pre_warned}"
        )
        return {
            "expired": expired,
            "pre_warned": pre_warned,
            "tenants_processed": tenants_processed,
        }

    except Exception as e:
        db.rollback()
        logger.error(f"expire_stale_calendar_conflicts failed: {e}")
        raise

    finally:
        if _owns_session:
            db.close()
