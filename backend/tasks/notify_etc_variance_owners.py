"""
ETC Variance Notification Task — B3/A16.

Scans recent job_time_entry rows with ETC; notifies owners when variance
threshold is exceeded. Runs every 15 minutes via Celery Beat.

Logic:
  1. Find jobs that have ETC entries saved since last run (last 20 minutes
     to cover the 15-min interval + buffer).
  2. For each job, compute projected total hours using etc_service.
  3. Compare against quoted hours from linked QuoteVersion.
  4. If variance >= tenant.etc_variance_owner_notify_pct:
       - Check variance_owner_notified_at to prevent duplicate notifications
         (only re-notify if variance has worsened to a new band)
       - Insert notification_outbox record for owner (email + push channels)
       - Update job.variance_owner_notified_at + job.variance_last_notified_pct
  5. Return dict with notified count for monitoring.
"""

import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from core.celery_app import celery_app
from core.db import get_db

logger = logging.getLogger(__name__)

# Only look at ETC entries from the last 20 minutes (15-min interval + buffer)
LOOKBACK_MINUTES = 20


@celery_app.task(name="notify_etc_variance_owners")
def notify_etc_variance_owners() -> dict[str, int]:
    """Scan recent job_time_entry rows with ETC; notify owners when variance threshold exceeded.

    Returns:
        dict: {"notified": int, "skipped": int, "errors": int}
    """
    from sqlalchemy import text
    from sqlmodel import Session, select

    from app.models.fulfillment import Job
    from app.models.quoting import QuoteVersion
    from app.models.system import (
        NotificationEvent,
        NotificationOutbox,
        NotificationType,
    )
    from services.etc_service import check_etc_variance, get_latest_etc_entries

    db: Session = next(get_db())
    notified = 0
    skipped = 0
    errors = 0

    try:
        cutoff = datetime.now(UTC) - timedelta(minutes=LOOKBACK_MINUTES)

        # Find distinct job_ids with ETC entries created since cutoff
        recent_jobs_result = db.execute(
            text(
                """
                SELECT DISTINCT job_id, tenant_id
                FROM job_time_entry
                WHERE hours_remaining_estimate IS NOT NULL
                  AND created_at >= :cutoff
                """
            ),
            {"cutoff": cutoff.isoformat()},
        ).fetchall()

        for row in recent_jobs_result:
            job_id = row.job_id
            tenant_id = row.tenant_id

            try:
                # Load job + settings
                job = db.exec(
                    select(Job)
                    .where(Job.id == job_id)
                    .where(Job.tenant_id == tenant_id)
                    .where(Job.is_active == True)
                ).first()
                if not job:
                    continue

                from services.setting_resolver import get_effective_setting

                # FIND-056 (Phase 2): TODO — this task operates at tenant level across multiple jobs.
                # Should be updated to use LaborRateVersion catalog per technician.skill_level_code.
                # For now, using platform default rate. See FIND-056 design doc for Phase 2 wiring.
                labor_rate_cents_val, _ = get_effective_setting(
                    db, tenant_id, "default_labor_rate_cents", fallback=8500
                )
                labor_rate_cents = int(labor_rate_cents_val)
                notify_pct_val, _ = get_effective_setting(
                    db, tenant_id, "etc_variance_owner_notify_pct", fallback=50
                )
                notify_pct = int(notify_pct_val)

                # Get latest ETC entries
                etc_entries = get_latest_etc_entries(db, tenant_id, job_id)
                if not etc_entries:
                    continue

                # Compute projected hours
                hours_worked = (
                    Decimal(str(job.actual_labor_cost_cents))
                    / Decimal(str(labor_rate_cents))
                    if labor_rate_cents > 0
                    else Decimal("0")
                )
                total_remaining = sum(e["hours_remaining"] for e in etc_entries)
                projected_total_hours = hours_worked + Decimal(str(total_remaining))

                # Get quoted hours
                quoted_hours = Decimal("0")
                if job.quote_version_id:
                    qv = db.exec(
                        select(QuoteVersion).where(
                            QuoteVersion.id == job.quote_version_id
                        )
                    ).first()
                    if qv and labor_rate_cents > 0:
                        total_cents = getattr(qv, "total_price_cents", 0) or 0
                        quoted_hours = Decimal(str(total_cents)) / Decimal(
                            str(labor_rate_cents)
                        )

                should_notify, variance_pct = check_etc_variance(
                    projected_total_hours, quoted_hours, notify_pct
                )

                if not should_notify:
                    skipped += 1
                    continue

                # Prevent duplicate notifications unless variance worsened
                last_notified_pct = job.variance_last_notified_pct
                if last_notified_pct is not None:
                    if variance_pct <= last_notified_pct:
                        skipped += 1
                        continue

                # Find owner user_id for this tenant via TenantUser

                owner_user = db.execute(
                    text(
                        """
                        SELECT tu.user_id
                        FROM tenant_user tu
                        JOIN tenant_user_role tur ON tur.code = tu.role_code
                        WHERE tu.tenant_id = :tid
                          AND tu.is_active = true
                          AND tu.role_code IN ('owner', 'accountant')
                        LIMIT 1
                        """
                    ),
                    {"tid": str(tenant_id)},
                ).fetchone()

                if not owner_user:
                    skipped += 1
                    continue

                owner_user_id = owner_user.user_id

                # Get notification type
                notif_type = db.exec(
                    select(NotificationType).where(
                        NotificationType.code == "etc_variance_alert"
                    )
                ).first()
                if not notif_type:
                    # Gracefully skip if notification type not seeded
                    skipped += 1
                    continue

                # Get notification event
                notif_event = db.exec(
                    select(NotificationEvent).where(
                        NotificationEvent.code == "etc_variance_alert"
                    )
                ).first()
                if not notif_event:
                    skipped += 1
                    continue

                # Create outbox entry (email)
                outbox_email = NotificationOutbox(
                    recipient_user_id=owner_user_id,
                    tenant_id=tenant_id,
                    channel="email",
                    notification_event_id=notif_event.id,
                    body=f"Job {job_id}: ETC variance is {float(variance_pct):.1f}% over quoted hours.",
                    status="pending",
                    category_id="job_activity",  # B10/A56
                )
                db.add(outbox_email)

                # Update job variance tracking
                job.variance_owner_notified_at = datetime.now(UTC)
                job.variance_last_notified_pct = variance_pct
                db.add(job)

                notified += 1
                logger.info(
                    "notify_etc_variance_owners: job=%s tenant=%s variance=%.1f%%",
                    job_id,
                    tenant_id,
                    float(variance_pct),
                )

            except Exception as job_exc:
                logger.error(
                    "notify_etc_variance_owners: error on job=%s: %s",
                    job_id,
                    job_exc,
                )
                errors += 1
                continue

        db.commit()
        return {"notified": notified, "skipped": skipped, "errors": errors}

    except Exception as e:
        db.rollback()
        logger.error("notify_etc_variance_owners task error: %s", e)
        raise
    finally:
        db.close()
