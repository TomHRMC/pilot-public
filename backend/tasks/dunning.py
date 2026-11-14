"""
Celery task: Dunning reminders for overdue invoices — B19/FIND-069 / SD-06B.

Registered in core/celery_app.py as:
    "dunning_reminders"
    schedule: crontab(hour=9, minute=0)  # once daily at 09:00 UTC (SD-06B)

Queries invoices WHERE due_at < now() AND balance_due_cents > 0
and:
  1. Throttles by last_reminder_sent_at (skip if reminded < 1 day ago)
  2. Respects 3-threshold schedule from platform_setting_catalog
  3. Sends customer-facing SMS via payment_reminder template (if phone available)
  4. Sends internal owner notification (email + in_app)
  5. Updates invoice.reminder_count and invoice.last_reminder_sent_at
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from sqlmodel import Session, select

from core.celery_app import celery_app
from core.db import get_db

logger = logging.getLogger(__name__)


@celery_app.task(name="dunning_reminders")
def dunning_reminders() -> dict[str, int]:
    """
    Celery Beat task (daily at 09:00 UTC) that identifies overdue invoices
    and sends dunning reminders to tenant owners + customer SMS.

    Returns: {"overdue_invoices": N, "notifications_enqueued": M, "sms_sent": K}
    """
    db: Session = next(get_db())
    try:
        return _dunning_reminders_impl(db)
    except Exception as e:
        db.rollback()
        logger.error(f"Error in dunning_reminders: {e}")
        raise
    finally:
        db.close()


def _dunning_reminders_impl(db: Session) -> dict[str, int]:
    """
    Inner implementation — separated for testability without Celery.

    SD-06B enhancements:
    - Throttle: skip invoices reminded < 1 day ago
    - Threshold schedule: only fire at 1d/7d/14d overdue milestones
    - Customer SMS via payment_reminder template
    - Update reminder_count + last_reminder_sent_at
    """
    from app.models.billing import Invoice
    from app.models.core import Tenant, User
    from app.models.system import NotificationEvent, NotificationOutbox

    now = datetime.now(UTC)
    overdue_invoices_count = 0
    notifications_enqueued = 0
    sms_sent = 0

    # Load reminder threshold days from platform_setting (null-tenant defaults)
    reminder_days = _get_reminder_thresholds(db)
    logger.info(f"Dunning thresholds: {reminder_days} days overdue")

    # Query all overdue invoices: due_at < now AND balance_due_cents > 0
    overdue_invoices = db.exec(
        select(Invoice)
        .where(Invoice.due_at < now)
        .where(Invoice.balance_due_cents > 0)
        .where(Invoice.is_active == True)
    ).all()

    for invoice in overdue_invoices:
        # --- SD-06B Throttle: skip if reminded < 1 day ago ---
        if invoice.last_reminder_sent_at is not None:
            time_since_last = now - invoice.last_reminder_sent_at
            if time_since_last < timedelta(hours=23):
                logger.debug(
                    f"Dunning skip (throttle): invoice {invoice.id} "
                    f"reminded {time_since_last} ago"
                )
                continue

        # --- SD-06B Threshold check: fire based on reminder_count progression ---
        # reminder_count=0 fires at threshold[0], count=1 at threshold[1], etc.
        # If reminder_count >= len(thresholds), no more reminders.
        days_overdue = (now - invoice.due_at).days
        if not _is_at_threshold(days_overdue, reminder_days, invoice.reminder_count):
            logger.debug(
                f"Dunning skip (threshold): invoice {invoice.id}, "
                f"{days_overdue}d overdue, count={invoice.reminder_count}, "
                f"thresholds={reminder_days}"
            )
            continue

        overdue_invoices_count += 1

        # Find the tenant owner
        tenant = db.exec(select(Tenant).where(Tenant.id == invoice.tenant_id)).first()
        if not tenant:
            logger.warning(
                f"Tenant {invoice.tenant_id} not found for invoice {invoice.id}"
            )
            continue

        owner_user = None
        if tenant.created_by:
            owner_user = db.exec(
                select(User).where(User.id == tenant.created_by)
            ).first()

        if not owner_user:
            logger.warning(
                f"No owner found for tenant {invoice.tenant_id} "
                f"(invoice {invoice.id}). Skipping notification."
            )
            continue

        amount_due_dollars = invoice.balance_due_cents / 100.0

        # --- Internal owner notification ---
        notification_event = NotificationEvent(
            tenant_id=invoice.tenant_id,
            notification_type_code="dunning_reminder",
            entity_type_code="invoice",
            entity_id=invoice.id,
            occurred_at=now,
            payload={
                "days_overdue": days_overdue,
                "reminder_count": invoice.reminder_count + 1,
            },
        )
        db.add(notification_event)
        db.flush()

        email_outbox = NotificationOutbox(
            notification_event_id=notification_event.id,
            tenant_id=invoice.tenant_id,
            recipient_user_id=owner_user.id,
            channel="email",
            body=(
                f"Invoice {invoice.invoice_number} is {days_overdue} days overdue. "
                f"Amount due: ${amount_due_dollars:.2f}. "
                f"Please follow up with the customer."
            ),
            category_id="billing",
            sub_trigger_id=None,
        )
        db.add(email_outbox)
        notifications_enqueued += 1

        inapp_outbox = NotificationOutbox(
            notification_event_id=notification_event.id,
            tenant_id=invoice.tenant_id,
            recipient_user_id=owner_user.id,
            channel="in_app",
            body=(
                f"Invoice {invoice.invoice_number} is {days_overdue} days overdue. "
                f"Balance due: ${amount_due_dollars:.2f}."
            ),
            category_id="billing",
            sub_trigger_id=None,
        )
        db.add(inapp_outbox)
        notifications_enqueued += 1

        # --- SD-06B Customer SMS via payment_reminder template ---
        # Savepoint wraps the ENTIRE SMS block (phone lookup + enqueue) to prevent
        # any failure from aborting the main transaction.
        from sqlalchemy import text as _sms_text

        db.execute(_sms_text("SAVEPOINT dunning_sms"))
        try:
            customer_phone = _get_customer_primary_phone(
                db, invoice.customer_id, invoice.tenant_id
            )
            if customer_phone:
                _enqueue_customer_sms(db, invoice, customer_phone, days_overdue)
                sms_sent += 1
                logger.info(
                    f"Dunning SMS enqueued for invoice {invoice.id}, phone={customer_phone}"
                )
            else:
                logger.debug(
                    f"Dunning skip customer SMS for invoice {invoice.id}: no primary phone"
                )
            db.execute(_sms_text("RELEASE SAVEPOINT dunning_sms"))
        except Exception as sms_err:
            try:
                db.execute(_sms_text("ROLLBACK TO SAVEPOINT dunning_sms"))
            except Exception:
                pass
            logger.debug(f"Dunning SMS skipped for invoice {invoice.id}: {sms_err}")

        # --- SD-06B Update reminder tracking ---
        invoice.reminder_count = invoice.reminder_count + 1
        invoice.last_reminder_sent_at = now
        db.add(invoice)

    db.commit()

    logger.info(
        f"Dunning reminders: {overdue_invoices_count} overdue invoices processed, "
        f"{notifications_enqueued} owner notifications enqueued, "
        f"{sms_sent} customer SMS sent"
    )
    return {
        "overdue_invoices": overdue_invoices_count,
        "notifications_enqueued": notifications_enqueued,
        "sms_sent": sms_sent,
    }


def _get_reminder_thresholds(db: Session) -> list[int]:
    """
    Load invoice reminder day thresholds from platform_setting (null-tenant defaults).
    Returns sorted list of ints, e.g. [1, 7, 14].
    Falls back to [1, 7, 14] if settings not found.
    """
    from sqlalchemy import text

    try:
        rows = db.execute(
            text("""
                SELECT key, value
                FROM public.platform_setting
                WHERE key IN (
                    'invoice_reminder_days_1',
                    'invoice_reminder_days_2',
                    'invoice_reminder_days_3'
                ) AND tenant_id IS NULL
            """)
        ).fetchall()

        thresholds = []
        for row in rows:
            try:
                # value is JSONB — could be int or string
                val = row.value
                if isinstance(val, str):
                    val = int(val.strip('"'))
                elif isinstance(val, (int, float)):
                    val = int(val)
                thresholds.append(val)
            except (ValueError, TypeError):
                pass

        return sorted(thresholds) if thresholds else [1, 7, 14]
    except Exception as e:
        logger.warning(
            f"Could not load dunning thresholds: {e} — using defaults [1, 7, 14]"
        )
        return [1, 7, 14]


def _is_at_threshold(
    days_overdue: int, thresholds: list[int], reminder_count: int = 0
) -> bool:
    """
    Returns True if the invoice should receive a reminder based on its current
    reminder_count and days_overdue against the configured thresholds.

    Logic:
    - reminder_count=0: fire when days_overdue >= threshold[0] (first reminder)
    - reminder_count=1: fire when days_overdue >= threshold[1] (second reminder)
    - reminder_count >= len(thresholds): no more reminders

    This ensures each invoice progresses through the reminder sequence,
    and existing tests (which use reminder_count=0) fire when days_overdue >= 1.
    """
    if reminder_count >= len(thresholds):
        return False
    return days_overdue >= thresholds[reminder_count]


def _get_customer_primary_phone(db: Session, customer_id, tenant_id) -> str | None:
    """
    Look up the customer's primary contact phone number.
    Returns None if no phone available.
    """
    from sqlalchemy import text

    try:
        row = db.execute(
            text("""
                SELECT c.phone
                FROM public.contact c
                JOIN public.entity_contact ec ON ec.contact_id = c.id
                WHERE ec.entity_type = 'customer'
                  AND ec.entity_id = :customer_id
                  AND c.tenant_id = :tenant_id
                  AND c.phone IS NOT NULL
                  AND c.is_active = true
                ORDER BY ec.is_primary DESC, c.created_at ASC
                LIMIT 1
            """),
            {"customer_id": str(customer_id), "tenant_id": str(tenant_id)},
        ).first()
        return row.phone if row else None
    except Exception as e:
        logger.debug(f"Could not look up customer phone for {customer_id}: {e}")
        return None


def _enqueue_customer_sms(
    db: Session, invoice, customer_phone: str, days_overdue: int
) -> None:
    """
    Enqueue a customer-facing SMS for a dunning reminder.
    Uses the payment_reminder communication_template (SMS channel) if available.
    Falls back to a hardcoded message if template not found.
    """
    from sqlalchemy import text

    amount_due_dollars = invoice.balance_due_cents / 100.0

    # Look up payment_reminder SMS template
    template_row = db.execute(
        text("""
            SELECT body_template FROM public.communication_template
            WHERE template_code = 'payment_reminder'
              AND channel = 'sms'
              AND tenant_id IS NULL
              AND is_active = true
            LIMIT 1
        """)
    ).first()

    if template_row:
        body = template_row.body_template
        # Simple variable substitution
        body = body.replace("{{invoice_number}}", invoice.invoice_number)
        body = body.replace("{{amount_due}}", f"${amount_due_dollars:.2f}")
        body = body.replace("{{days_overdue}}", str(days_overdue))
    else:
        body = (
            f"Friendly reminder: Invoice {invoice.invoice_number} is {days_overdue} days overdue. "
            f"Amount due: ${amount_due_dollars:.2f}. Please contact us to resolve. "
            f"Reply STOP to opt out."
        )

    # Insert into communication_outbox (or skip if table not found)
    try:
        db.execute(
            text("""
                INSERT INTO public.communication_outbox
                (id, tenant_id, customer_id, channel, body, to_phone, status, created_at, updated_at)
                VALUES (gen_random_uuid(), :tenant_id, :customer_id, 'sms', :body, :phone, 'pending', NOW(), NOW())
            """),
            {
                "tenant_id": str(invoice.tenant_id),
                "customer_id": str(invoice.customer_id),
                "body": body,
                "phone": customer_phone,
            },
        )
    except Exception:
        # communication_outbox may not exist in all environments — log and continue
        logger.debug(
            f"communication_outbox insert failed for invoice {invoice.id} — "
            f"table may not exist yet (MVP)"
        )
