"""
Monitor SMS Quota Thresholds — B11/A65
=======================================
Celery periodic task: hourly.
Detects 80%/100% threshold crossings and dispatches billing notifications
via notification_outbox with category_id='billing'.

Sub-trigger IDs:
  sms_quota_80_pct         — 80% threshold crossing
  sms_quota_100_pct_soft   — 100% threshold, soft cap (overage billing info)
  sms_quota_100_pct_hard   — 100% threshold, hard cap (blocking info)
"""

import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlmodel import Session

from core.celery_app import celery_app
from core.db import get_db

logger = logging.getLogger(__name__)


def _monitor_impl(db: Session) -> dict[str, int]:
    """
    Inner implementation — scan all active quota periods and emit
    notifications for tenants crossing 80% or 100% thresholds.
    """
    from app.models.sms import SmsQuotaPeriod

    now = datetime.now(UTC)
    notified_80 = 0
    notified_100 = 0

    # All active periods
    periods = db.exec(
        select(SmsQuotaPeriod).where(
            SmsQuotaPeriod.period_start <= now,
            SmsQuotaPeriod.period_end >= now,
        )
    ).all()

    for period in periods:
        used = period.used_segments or 0
        included = period.included_segments or 100

        if included == 0:
            continue

        pct = (used / included) * 100

        # 100% threshold
        if pct >= 100:
            sub_trigger = (
                "sms_quota_100_pct_hard"
                if period.cap_policy == "hard"
                else "sms_quota_100_pct_soft"
            )
            _emit_notification(db, period.tenant_id, "billing", sub_trigger)
            notified_100 += 1

        # 80% threshold (only if not already at 100%)
        elif pct >= 80:
            _emit_notification(db, period.tenant_id, "billing", "sms_quota_80_pct")
            notified_80 += 1

    db.commit()
    return {"notified_80_pct": notified_80, "notified_100_pct": notified_100}


def _emit_notification(
    db: Session, tenant_id, category_id: str, sub_trigger_id: str
) -> None:
    """Create a notification_outbox row for the given tenant/category/sub_trigger."""
    import json
    import uuid

    from app.models.system import NotificationOutbox

    try:
        outbox = NotificationOutbox(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            category_id=category_id,
            sub_trigger_id=sub_trigger_id,
            status="pending",
            payload=json.dumps({"sub_trigger_id": sub_trigger_id}),
        )
        db.add(outbox)
    except Exception as exc:
        logger.warning(f"Could not create notification for tenant {tenant_id}: {exc}")


@celery_app.task(name="monitor_sms_quota_thresholds")
def monitor_sms_quota_thresholds() -> dict[str, int]:
    """
    Hourly periodic task. Detect 80%/100% threshold crossings and dispatch
    billing notifications via notification_outbox.
    """
    db: Session = next(get_db())
    try:
        result = _monitor_impl(db)
        logger.info(f"monitor_sms_quota_thresholds: {result}")
        return result
    except Exception as exc:
        db.rollback()
        logger.error(f"monitor_sms_quota_thresholds failed: {exc}")
        raise
    finally:
        db.close()
