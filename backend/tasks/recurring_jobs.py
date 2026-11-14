# backend/tasks/recurring_jobs.py
# B21: Celery Beat task for generating recurring job instances.
#
# Beat schedule: daily at 06:00 UTC → generate_due_recurring_jobs
# Notification: enqueue_recurring_job_notification (event-driven, no Beat entry)
#
# Architecture: two-layer pattern
#   _generate_due_recurring_jobs_impl(db) — pure business logic, testable directly
#   generate_due_recurring_jobs()          — Celery task wrapper

import logging
from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from sqlmodel import Session, select

from app.models.fulfillment import Job, JobRecurrenceRule, JobStatus
from core.celery_app import celery_app
from core.db import get_db

logger = logging.getLogger(__name__)


# ==================== PURE HELPERS ====================

try:
    from dateutil.relativedelta import relativedelta

    _HAS_DATEUTIL = True
except ImportError:  # pragma: no cover
    _HAS_DATEUTIL = False
    logger.warning(
        "python-dateutil not available; monthly/annually recurrence will fail"
    )


def _compute_next_job_at(pattern: str, interval_count: int, from_date: date) -> date:
    """
    Compute next occurrence date.

    Args:
        pattern: 'daily' | 'weekly' | 'monthly' | 'annually'
        interval_count: how many intervals between occurrences (≥1)
        from_date: the date to advance from

    Returns:
        Next occurrence as a date
    """
    if pattern == "daily":
        return from_date + timedelta(days=interval_count)
    elif pattern == "weekly":
        return from_date + timedelta(weeks=interval_count)
    elif pattern == "monthly":
        if not _HAS_DATEUTIL:  # pragma: no cover
            raise RuntimeError("python-dateutil is required for monthly recurrence")
        return from_date + relativedelta(months=interval_count)
    elif pattern == "annually":
        if not _HAS_DATEUTIL:  # pragma: no cover
            raise RuntimeError("python-dateutil is required for annual recurrence")
        return from_date + relativedelta(years=interval_count)
    else:
        raise ValueError(f"Unknown recurrence pattern: {pattern}")


def _date_to_noon_utc(d: date) -> datetime:
    """Convert a date to noon UTC datetime (avoids DST edge cases)."""
    return datetime(d.year, d.month, d.day, 12, 0, 0, tzinfo=UTC)


# ==================== NOTIFICATION TASK ====================


def _enqueue_recurring_job_notification_impl(
    rule_id: UUID,
    job_id: UUID,
    db: Session,
) -> dict:
    """
    Log a recurring-job-scheduled notification event.

    Full outbox dispatch (NotificationOutbox) requires a notification_event FK
    which is provisioned via the notification event system. For B21 MVP,
    we log the dispatch intent; the notification pipeline will pick it up when
    the event type is registered in a future batch.

    Mocked in tests via: unittest.mock.patch(
        "tasks.recurring_jobs.enqueue_recurring_job_notification"
    )
    """
    logger.info(
        f"recurring_job_scheduled: rule_id={rule_id}, job_id={job_id} "
        f"— notification intent logged (full dispatch requires notification_event FK)"
    )
    return {"rule_id": str(rule_id), "job_id": str(job_id), "status": "logged"}


@celery_app.task(name="tasks.recurring_jobs.enqueue_recurring_job_notification")
def enqueue_recurring_job_notification(rule_id: str, job_id: str) -> dict:
    """
    Celery task: log/dispatch notification for a newly created recurring job.
    Event-driven — no Beat entry.
    """
    db: Session = next(get_db())
    try:
        result = _enqueue_recurring_job_notification_impl(
            UUID(rule_id), UUID(job_id), db
        )
        return result
    except Exception as e:
        db.rollback()
        logger.error(f"enqueue_recurring_job_notification failed: {e}")
        raise
    finally:
        db.close()


# ==================== BEAT TASK IMPLEMENTATION ====================


def _generate_due_recurring_jobs_impl(db: Session) -> dict:
    """
    Core Beat task logic — testable directly without Celery.

    For each active rule where next_job_at <= now:
      1. Check expiry conditions (ends_on, max_occurrences)
      2. Create the job for this occurrence
      3. Advance next_job_at
      4. Enqueue notification

    Returns a summary dict: {"processed": N, "deactivated": N, "skipped": N}
    """
    from api.routes.jobs import _generate_job_number

    now = datetime.now(UTC)

    # Fetch all active rules due for generation
    due_rules = db.exec(
        select(JobRecurrenceRule)
        .where(JobRecurrenceRule.is_active == True)
        .where(JobRecurrenceRule.next_job_at <= now)
    ).all()

    processed = 0
    deactivated = 0
    skipped = 0

    for rule in due_rules:
        try:
            today = now.date()

            # Check expiry: ends_on in past
            if rule.ends_on and rule.ends_on < today:
                rule.is_active = False
                db.add(rule)
                db.commit()
                deactivated += 1
                logger.info(
                    f"Rule {rule.id} deactivated: ends_on {rule.ends_on} is past"
                )
                continue

            # Check expiry: max_occurrences reached
            if (
                rule.max_occurrences
                and rule.occurrences_created >= rule.max_occurrences
            ):
                rule.is_active = False
                db.add(rule)
                db.commit()
                deactivated += 1
                logger.info(
                    f"Rule {rule.id} deactivated: max_occurrences {rule.max_occurrences} reached"
                )
                continue

            # Determine job date from next_job_at
            job_date = rule.next_job_at.date() if rule.next_job_at else today

            # Get default job status (tenant-specific preferred over global)
            job_status = db.exec(
                select(JobStatus)
                .where(
                    (JobStatus.tenant_id == rule.tenant_id)
                    | (JobStatus.tenant_id == None)
                )
                .where(JobStatus.is_default == True)
                .order_by(JobStatus.tenant_id)
            ).first()

            if not job_status:
                job_status = db.exec(select(JobStatus)).first()

            if not job_status:
                logger.error(f"No job status available — skipping rule {rule.id}")
                skipped += 1
                continue

            # Create the job
            # ck_job_schedule_range: both start/end NULL OR both NOT NULL with end > start.
            scheduled_start = _date_to_noon_utc(job_date)
            duration_minutes = rule.estimated_duration_minutes or 60
            scheduled_end = scheduled_start + timedelta(minutes=duration_minutes)
            job = Job(
                tenant_id=rule.tenant_id,
                customer_id=rule.customer_id,
                site_id=rule.site_id,
                status_id=job_status.id,
                recurrence_rule_id=rule.id,
                scheduled_start_at=scheduled_start,
                scheduled_end_at=scheduled_end,
                estimated_duration_minutes=rule.estimated_duration_minutes,
                job_number=_generate_job_number(rule.tenant_id, db),
            )
            db.add(job)
            db.flush()  # Populate job.id

            # Auto-assign default tech if configured
            if rule.default_tech_user_id:
                from app.models.scheduling import JobTechAssignment

                # assigned_by_user_id is NOT NULL — use the rule creator or
                # system sentinel (00000000-0000-0000-0000-000000000000) for
                # system-generated records (see migration 4d035847177f).
                _system_sentinel = UUID("00000000-0000-0000-0000-000000000000")
                assigner = rule.created_by or _system_sentinel

                assignment = JobTechAssignment(
                    tenant_id=rule.tenant_id,
                    job_id=job.id,
                    user_id=rule.default_tech_user_id,
                    assigned_by_user_id=assigner,
                    assigned_at=datetime.now(UTC),
                    is_lead=True,
                )
                db.add(assignment)

            # Advance next_job_at to NEXT occurrence
            next_date = _compute_next_job_at(
                rule.pattern, rule.interval_count, job_date
            )
            rule.next_job_at = _date_to_noon_utc(next_date)
            rule.occurrences_created += 1
            rule.last_job_created_at = now

            db.add(rule)
            db.commit()
            db.refresh(job)

            # Enqueue notification (fire-and-forget)
            try:
                enqueue_recurring_job_notification.delay(str(rule.id), str(job.id))
            except Exception as notify_exc:
                logger.warning(
                    f"Notification enqueue failed for rule {rule.id}: {notify_exc}"
                )

            processed += 1
            logger.info(
                f"Rule {rule.id}: created job {job.id} for {job_date}, "
                f"next_job_at={rule.next_job_at}"
            )

        except Exception as e:
            db.rollback()
            logger.error(f"Error processing rule {rule.id}: {e}", exc_info=True)
            skipped += 1
            continue

    result = {"processed": processed, "deactivated": deactivated, "skipped": skipped}
    logger.info(f"generate_due_recurring_jobs completed: {result}")
    return result


@celery_app.task(name="tasks.recurring_jobs.generate_due_recurring_jobs")
def generate_due_recurring_jobs() -> dict:
    """
    Celery Beat task: run daily at 06:00 UTC.
    Generates all job instances that are due based on active recurrence rules.
    """
    db: Session = next(get_db())
    try:
        return _generate_due_recurring_jobs_impl(db)
    except Exception as e:
        db.rollback()
        logger.error(f"generate_due_recurring_jobs failed: {e}", exc_info=True)
        raise
    finally:
        db.close()
