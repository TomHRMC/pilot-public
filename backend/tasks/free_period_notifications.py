"""
C-B6 — Free-period notification schedule.

Celery Beat task (daily at 09:00 UTC) that sends email + push + in-app banner
notifications at T-30, T-14, T-7, T-3, T-1, and on expiry day (T-0) for tenants
with ``free_period_ends_at`` set (Charter free period).

The Stripe ``customer.subscription.trial_will_end`` webhook (fires at T-3) calls
the same ``_dispatch_free_period_notification()`` helper — idempotency via
``NotificationEvent.payload->>'days_remaining'`` prevents duplicates.

Pattern: §17.1 Periodic Poll Task (no bind=True, no retry, log + move on).
Two-layer: ``_free_period_notifications_impl()`` (testable) + ``free_period_notifications()``
wrapper (opens session, handles exceptions).
"""

import logging
from datetime import UTC, datetime

from sqlalchemy import text
from sqlmodel import Session, select

from core.celery_app import celery_app
from core.db import get_db

logger = logging.getLogger(__name__)

# Charter free-period notification thresholds (days before expiry; 0 = expiry day)
FREE_PERIOD_WARNING_DAYS = [30, 14, 7, 3, 1, 0]

# Notification category for free-period warnings (FK to notification_category.code)
_FREE_PERIOD_CATEGORY_ID = "billing"


@celery_app.task(name="free_period_notifications")
def free_period_notifications() -> dict[str, int]:
    """Celery Beat task (daily 09:00 UTC)."""
    db: Session = next(get_db())
    try:
        return _free_period_notifications_impl(db)
    except Exception as e:
        db.rollback()
        logger.error(f"Error in free_period_notifications: {e}")
        raise
    finally:
        db.close()


def _free_period_notifications_impl(db: Session) -> dict[str, int]:
    """
    Inner implementation — separated for testability.

    Queries tenants with ``free_period_ends_at`` set, computes days remaining,
    dispatches notifications at T-30/14/7/3/1/0 thresholds.

    Idempotent: checks ``NotificationEvent`` for existing dispatch at the same
    ``days_remaining`` threshold before creating a new one.
    """
    from app.models.core import Tenant
    from app.models.system import NotificationEvent

    now = datetime.now(UTC)
    notifications_sent = 0

    # Find all active tenants with a free period end date
    tenants = db.exec(
        select(Tenant)
        .where(Tenant.free_period_ends_at != None)
        .where(Tenant.is_active == True)
    ).all()

    for tenant in tenants:
        days_remaining = (tenant.free_period_ends_at - now).days

        if days_remaining not in FREE_PERIOD_WARNING_DAYS:
            continue

        # Idempotency: check if already notified for this threshold
        existing = db.exec(
            select(NotificationEvent)
            .where(NotificationEvent.tenant_id == tenant.id)
            .where(NotificationEvent.notification_type_code == "free_period_warning")
            .where(
                text("notification_event.payload->>'days_remaining' = :dr").bindparams(
                    dr=str(days_remaining)
                )
            )
        ).first()

        if existing:
            continue  # Already sent for this threshold

        try:
            _dispatch_free_period_notification(db, tenant, days_remaining)
            notifications_sent += 1
        except Exception as e:
            logger.error(
                f"Failed to dispatch free-period notification for "
                f"tenant {tenant.id} (days_remaining={days_remaining}): {e}"
            )

    db.commit()
    logger.info(f"Free-period notifications: {notifications_sent} sent")
    return {"notifications_sent": notifications_sent}


def _dispatch_free_period_notification(
    db: Session, tenant, days_remaining: int
) -> None:
    """
    Create ``NotificationEvent`` + 3 ``NotificationOutbox`` rows (email/push/in_app)
    for a single tenant + threshold, then enqueue ``send_notification.delay()``
    for each outbox row.

    Called by both the Celery beat task and the Stripe ``trial_will_end`` webhook
    handler. Idempotency is enforced by the caller (``_free_period_notifications_impl``)
    — this function always creates rows.

    Args:
        db:             Active DB session (caller commits).
        tenant:         Tenant ORM instance with ``free_period_ends_at`` set.
        days_remaining: 0 | 1 | 3 | 7 | 14 | 30 — determines copy.
    """
    from app.models.auth import TenantUser
    from app.models.system import NotificationEvent, NotificationOutbox

    now = datetime.now(UTC)

    # Look up the tenant owner (same pattern as trial_management.dispatch_trial_warning)
    owner = db.exec(
        select(TenantUser)
        .where(TenantUser.tenant_id == tenant.id)
        .where(TenantUser.role_code == "owner")
        .where(TenantUser.is_active == True)
    ).first()

    if not owner:
        logger.warning(
            f"No active owner found for tenant {tenant.id} — "
            f"skipping free-period notification"
        )
        return

    # Format the expiry date for the body copy
    expiry_date_str = tenant.free_period_ends_at.strftime("%B %d, %Y")

    # Build the body copy based on threshold
    if days_remaining == 0:
        body = (
            "Your free period ends today. "
            "Add a payment method now to avoid interruption."
        )
    elif days_remaining == 1:
        body = (
            "Your free period ends tomorrow. "
            "Add a payment method to avoid interruption."
        )
    else:
        body = (
            f"Your Pilot for Trades free period ends on {expiry_date_str}. "
            f"Add a payment method in Settings → Subscription & Billing "
            f"to keep your account running past that date."
        )

    # Create the NotificationEvent (append-only)
    notification_event = NotificationEvent(
        tenant_id=tenant.id,
        notification_type_code="free_period_warning",
        entity_type_code="tenant",
        entity_id=str(tenant.id),
        occurred_at=now,
        payload={"days_remaining": days_remaining},
    )
    db.add(notification_event)
    db.flush()  # Get the event ID for the outbox rows

    # Create 3 NotificationOutbox rows (email, push, in_app)
    channels = ["email", "push", "in_app"]
    outbox_ids = []
    for channel in channels:
        outbox = NotificationOutbox(
            notification_event_id=notification_event.id,
            tenant_id=tenant.id,
            recipient_user_id=owner.user_id,
            channel=channel,
            body=body,
            category_id=_FREE_PERIOD_CATEGORY_ID,
            sub_trigger_id=None,
            contextdata={"days_remaining": days_remaining},
        )
        db.add(outbox)
        outbox_ids.append(outbox)

    db.flush()  # Ensure outbox rows have IDs before enqueuing

    # Enqueue send_notification for each outbox row
    # Import here to avoid circular import at module load time
    from tasks.notification_worker import send_notification

    for outbox in outbox_ids:
        try:
            send_notification.delay(str(outbox.id))
        except Exception as e:
            # Enqueue failure is non-fatal — poll_pending_notifications will
            # pick up the pending outbox row within 30 seconds.
            logger.debug(
                f"send_notification.delay() failed for outbox {outbox.id}: {e}"
            )

    logger.info(
        f"Free-period notification dispatched for tenant {tenant.id}: "
        f"{days_remaining} days remaining"
    )
