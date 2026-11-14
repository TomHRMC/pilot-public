"""
A26: System Template Update Notification Flow

Celery task: notify tenants whose forked templates are behind the current system version.

Registered in: core/celery_app.py (task name 'notify_system_template_updates')
Beat schedule: daily at 6:00 AM UTC (per arch doc §3.2)
Pattern: §17.1 Periodic Poll Task (no bind, no retry)

Business Logic:
- Find all tenant-forked templates where forked_from_version < system template's current_version
- Log the stale forks for each tenant
- Returns {"notified": int} count of tenants with stale forks identified

MVP Deviation (B1):
- Full notification_outbox row creation requires notification_event_id FK which needs
  the notification_event seed infrastructure (out of scope for B1). This task identifies
  stale forks and logs them for observability. Full notification dispatch will be wired
  in the B9/A53 notification preferences batch when the three-tier resolver is established.
"""

import logging

from sqlmodel import Session, select

from core.celery_app import celery_app
from core.db import get_db

logger = logging.getLogger(__name__)


def _notify_system_template_updates_impl(db: Session) -> dict[str, int]:
    """
    Inner implementation — separated for testability without Celery.

    Finds tenant-forked templates lagging behind system template versions,
    logs stale forks per tenant, and returns a count.

    Returns:
        {"notified": int} — count of tenants with stale template forks identified
    """
    from app.models.quoting import QuoteTemplate

    notified_tenants: set = set()

    # Find all tenant forks that reference a system template
    forked_templates = db.exec(
        select(QuoteTemplate).where(
            QuoteTemplate.system_template_id != None,
            QuoteTemplate.is_active == True,
        )
    ).all()

    for forked in forked_templates:
        if forked.system_template_id is None or forked.tenant_id is None:
            continue

        # Fetch the current system template
        system_tpl = db.exec(
            select(QuoteTemplate).where(
                QuoteTemplate.id == forked.system_template_id,
                QuoteTemplate.is_system_template == True,
            )
        ).first()

        if not system_tpl:
            continue

        # Check if this fork is behind
        if (forked.forked_from_version or 0) >= system_tpl.current_version:
            continue

        # Log the stale fork for observability
        logger.info(
            "system_template_notifier: tenant %s has stale fork '%s' "
            "(forked_from_version=%s, current_version=%s) of system template '%s'",
            forked.tenant_id,
            forked.name,
            forked.forked_from_version,
            system_tpl.current_version,
            system_tpl.name,
        )
        notified_tenants.add(str(forked.tenant_id))

    notified = len(notified_tenants)
    if notified > 0:
        logger.info(
            "system_template_notifier: identified %d tenant(s) with stale template forks",
            notified,
        )

    return {"notified": notified}


@celery_app.task(name="notify_system_template_updates")
def notify_system_template_updates() -> dict[str, int]:
    """
    A26: Nightly Celery Beat task — check forked templates against system template versions.

    For each tenant template with system_template_id set,
    compares forked_from_version to the system template's current_version.
    If behind: logs the stale fork. Returns count of tenants with stale forks.

    Beat schedule: daily at 6:00 AM UTC (registered in core/celery_app.py)

    Returns:
        {"notified": int} — count of tenants with stale template forks identified
    """
    db: Session = next(get_db())
    try:
        result = _notify_system_template_updates_impl(db)
        return result
    except Exception as e:
        db.rollback()
        logger.error("Error in notify_system_template_updates: %s", e)
        raise
    finally:
        db.close()
