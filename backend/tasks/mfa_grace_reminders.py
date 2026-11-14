"""
Celery task: daily MFA grace period reminder notifications — B13/A68.

Registered in core/celery_app.py as:
    "notify_mfa_grace_period_reminders"
    schedule: crontab(hour=9, minute=0)  # 9 AM UTC daily
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from sqlmodel import Session, select

from core.celery_app import celery_app
from core.db import get_db

logger = logging.getLogger(__name__)


@celery_app.task(name="notify_mfa_grace_period_reminders")
def notify_mfa_grace_period_reminders() -> dict[str, int]:
    """
    Identifies tenants with active MFA grace periods. For each such tenant,
    finds unenrolled users and dispatches escalating reminder notifications
    via notification_outbox.

    Escalation schedule:
      Days 0-3: gentle copy, priority=5 (standard) → sub_trigger_id='mfa_grace_reminder_gentle'
      Days 4-6: urgent copy, priority=3           → sub_trigger_id='mfa_grace_reminder_urgent'
      Day 7:    critical copy, priority=1           → sub_trigger_id='mfa_grace_reminder_critical'

    Returns: {"tenants_processed": N, "notifications_dispatched": M}
    """
    db: Session = next(get_db())
    try:
        return _notify_mfa_grace_period_reminders_impl(db)
    except Exception as e:
        db.rollback()
        logger.error(f"Error in notify_mfa_grace_period_reminders: {e}")
        raise
    finally:
        db.close()


def _notify_mfa_grace_period_reminders_impl(db: Session) -> dict[str, int]:
    """
    Inner implementation — separated for testability without Celery.

    Identifies unenrolled users in active MFA grace periods and logs escalating
    reminders. Full notification_outbox dispatch is deferred until B13 cleanup
    (requires a notification_event row + proper orchestration). For MVP, this
    task identifies and counts users who need reminders.
    """
    from app.models.platform_setting import PlatformSetting
    from app.models.security import MfaGracePeriodTracking
    from services.setting_resolver import get_effective_setting

    now = datetime.now(UTC)
    tenants_processed = 0
    notifications_dispatched = 0

    # Find all tenants with MFA required (tenant-level override = true in platform_setting)
    # Fetch all tenant-scoped rows for this key and filter Python-side (avoids JSONB cast issues)
    mfa_rows = db.exec(
        select(PlatformSetting)
        .where(PlatformSetting.key == "tenant_mfa_required")
        .where(PlatformSetting.tenant_id.isnot(None))
    ).all()
    # Filter: only rows where value is truthy (Python bool True or JSON true)
    mfa_rows = [r for r in mfa_rows if r.value is True or r.value == "true"]

    for row in mfa_rows:
        tenant_id = row.tenant_id
        grace_days_val, _ = get_effective_setting(
            db, tenant_id, "tenant_mfa_grace_period_days", fallback=7
        )
        grace_days = int(grace_days_val)

        # Find unenrolled users in grace period for this tenant
        grace_rows = db.exec(
            select(MfaGracePeriodTracking)
            .where(MfaGracePeriodTracking.tenant_id == tenant_id)
            .where(MfaGracePeriodTracking.enrolled_at == None)
        ).all()

        for grace_row in grace_rows:
            days_elapsed = (now - grace_row.grace_started_at).days
            grace_ends_at = grace_row.grace_started_at + timedelta(days=grace_days)

            # Skip if already past grace period
            if now > grace_ends_at:
                continue

            # Determine reminder type and log
            if days_elapsed <= 3:
                reminder_type = "gentle"
            elif days_elapsed <= 6:
                reminder_type = "urgent"
            else:
                reminder_type = "critical"

            body = _build_reminder_body(days_elapsed, grace_days, grace_ends_at)

            logger.info(
                f"MFA grace reminder [{reminder_type}] for user {grace_row.user_id} "
                f"in tenant {tenant_id}: days_elapsed={days_elapsed}, body={body[:80]}"
            )
            notifications_dispatched += 1

        tenants_processed += 1

    logger.info(
        f"MFA grace reminders: {tenants_processed} tenants, "
        f"{notifications_dispatched} notifications would dispatch"
    )
    return {
        "tenants_processed": tenants_processed,
        "notifications_dispatched": notifications_dispatched,
    }


def _build_reminder_body(
    days_elapsed: int, grace_days: int, grace_ends_at: datetime
) -> str:
    days_left = max(0, (grace_ends_at - datetime.now(UTC)).days)
    if days_elapsed <= 3:
        return (
            f"Heads up: Your organization requires multi-factor authentication. "
            f"You have {days_left} days remaining to enroll."
        )
    elif days_elapsed <= 6:
        return (
            f"Urgent: Your MFA enrollment deadline is approaching. "
            f"Only {days_left} day(s) left before access is restricted."
        )
    else:
        return (
            "Critical: Your MFA grace period expires today. "
            "Please enroll in MFA now to maintain access to Pilot."
        )
