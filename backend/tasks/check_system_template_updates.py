"""
FIND-099 (B19): System Template Update Notification Task

Celery Beat task (nightly 2:00 AM UTC) — detects when system templates have been updated
and notifies tenants whose forked templates are now behind the current version.

Business Logic:
1. Find all system templates (is_system_template=true)
2. For each system template, find all tenant-forked templates
3. For each fork that is behind (forked_from_version < system_template.current_version):
   - Check if the tenant has created any recent quotes (within last 30 days)
   - If yes, enqueue a notification_outbox row for that tenant
4. Returns {"notified": int} count of tenant notifications enqueued

Pattern: §17.1 Periodic Poll Task (no bind, no retry)
Registered in: core/celery_app.py (task name 'check_system_template_updates')
Beat schedule: nightly at 2:00 AM UTC
"""

import logging
from datetime import UTC, datetime, timedelta

from sqlmodel import Session, select

from core.celery_app import celery_app
from core.db import get_db

logger = logging.getLogger(__name__)


def _check_system_template_updates_impl(db: Session) -> dict[str, int]:
    """
    Inner implementation — separated for testability without Celery.

    Finds tenant-forked templates lagging behind system template versions,
    checks for recent quote activity, and enqueues notification_outbox rows.

    Returns:
        {"notified": int} — count of tenant notifications enqueued
    """
    from app.models.quoting import Quote, QuoteTemplate
    from app.models.system import (
        NotificationChannel,
        NotificationEvent,
        NotificationOutbox,
    )

    notified_count = 0
    thirty_days_ago = datetime.now(UTC) - timedelta(days=30)

    # Find all system templates
    system_templates = db.exec(
        select(QuoteTemplate).where(
            QuoteTemplate.is_system_template == True,
            QuoteTemplate.is_active == True,
        )
    ).all()

    for system_tpl in system_templates:
        # Find all tenant-forked templates for this system template
        forked_templates = db.exec(
            select(QuoteTemplate).where(
                QuoteTemplate.system_template_id == system_tpl.id,
                QuoteTemplate.is_active == True,
            )
        ).all()

        for forked_tpl in forked_templates:
            if forked_tpl.tenant_id is None:
                continue

            # Check if this fork is behind
            if (forked_tpl.forked_from_version or 0) >= system_tpl.current_version:
                continue

            # Check if tenant has created any recent quotes
            # (This would use quote_version snapshot to infer template usage)
            # For now, we'll check if the tenant has ANY recent quotes
            recent_quote_count = db.exec(
                select(Quote).where(
                    Quote.tenant_id == forked_tpl.tenant_id,
                    Quote.created_at >= thirty_days_ago,
                    Quote.is_active == True,
                )
            ).first()

            if recent_quote_count is None:
                # No recent quotes, skip notification
                continue

            # Enqueue notification_outbox row for this tenant
            try:
                # Get the notification_event for "system_template_updated"
                notification_event = db.exec(
                    select(NotificationEvent).where(
                        NotificationEvent.code == "system_template_updated"
                    )
                ).first()

                if not notification_event:
                    logger.warning(
                        "notification_event 'system_template_updated' not found; "
                        "skipping notification for tenant %s",
                        forked_tpl.tenant_id,
                    )
                    continue

                # Get the default notification channel
                notification_channel = db.exec(
                    select(NotificationChannel).where(
                        NotificationChannel.code == "in_app"
                    )
                ).first()

                if not notification_channel:
                    logger.warning(
                        "notification_channel 'in_app' not found; "
                        "skipping notification for tenant %s",
                        forked_tpl.tenant_id,
                    )
                    continue

                # Create notification_outbox row
                outbox_row = NotificationOutbox(
                    tenant_id=forked_tpl.tenant_id,
                    notification_event_id=notification_event.id,
                    channel=notification_channel.code,
                    to_address=None,
                    subject=None,
                    body=f"System template '{system_tpl.name}' has been updated. "
                    f"Your forked template '{forked_tpl.name}' is now behind version "
                    f"{system_tpl.current_version}. Consider updating your copy.",
                    status="pending",
                    contextdata={
                        "system_template_id": str(system_tpl.id),
                        "forked_template_id": str(forked_tpl.id),
                        "system_template_version": system_tpl.current_version,
                        "forked_from_version": forked_tpl.forked_from_version,
                    },
                    category_id="system_template_update",
                )
                db.add(outbox_row)
                db.flush()  # Ensure row is created before commit
                notified_count += 1

                logger.info(
                    "check_system_template_updates: enqueued notification for tenant %s "
                    "(system template '%s' v%s, forked template '%s' behind at v%s)",
                    forked_tpl.tenant_id,
                    system_tpl.name,
                    system_tpl.current_version,
                    forked_tpl.name,
                    forked_tpl.forked_from_version,
                )

            except Exception as e:
                logger.error(
                    "Error enqueueing notification for tenant %s: %s",
                    forked_tpl.tenant_id,
                    e,
                )
                continue

    if notified_count > 0:
        logger.info(
            "check_system_template_updates: enqueued %d notification(s)",
            notified_count,
        )

    return {"notified": notified_count}


@celery_app.task(name="check_system_template_updates")
def check_system_template_updates() -> dict[str, int]:
    """
    FIND-099: Nightly Celery Beat task — check system templates for updates
    and notify tenants whose forked templates are behind.

    For each system template, finds tenant-forked templates that are behind the
    current version. If the tenant has created recent quotes, enqueues a
    notification_outbox row for that tenant.

    Beat schedule: daily at 2:00 AM UTC (registered in core/celery_app.py)

    Returns:
        {"notified": int} — count of tenant notifications enqueued
    """
    db: Session = next(get_db())
    try:
        result = _check_system_template_updates_impl(db)
        db.commit()
        return result
    except Exception as e:
        db.rollback()
        logger.error("Error in check_system_template_updates: %s", e)
        raise
    finally:
        db.close()
