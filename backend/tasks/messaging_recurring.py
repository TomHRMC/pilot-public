"""
C-B10 — Recurring carrier fee Celery task.
==========================================

Daily beat task that finds eligible tenant_messaging_registration rows and
creates the recurring Stripe SubscriptionItem for carrier fee pass-through.

Eligibility:
  - status = 'active'
  - created_at + 90 days <= now()  (prepaid window expired)
  - stripe_recurring_item_id IS NULL  (not yet created)

Pattern: Two-layer approach (_impl + @celery_app.task wrapper).
"""

import logging
from datetime import timedelta

from sqlmodel import Session, select

from app.models.sms import TenantMessagingRegistration
from core.celery_app import celery_app
from core.datetime_utils import safe_now_utc
from core.db import get_db
from services.messaging_recurring import create_recurring_carrier_item

logger = logging.getLogger(__name__)


def _create_recurring_carrier_items_impl(db: Session) -> dict[str, int]:
    """Inner implementation — find eligible registrations and create recurring items.

    Returns: {"processed": N, "created": M, "skipped": K, "errors": E}
    """
    cutoff = safe_now_utc() - timedelta(days=90)

    eligible = db.exec(
        select(TenantMessagingRegistration).where(
            TenantMessagingRegistration.status == "active",
            TenantMessagingRegistration.created_at <= cutoff,
            TenantMessagingRegistration.stripe_recurring_item_id.is_(None),
        )
    ).all()

    processed = len(eligible)
    created = 0
    skipped = 0
    errors = 0

    for reg in eligible:
        try:
            create_recurring_carrier_item(db, reg.id)
            created += 1
        except ValueError as exc:
            # Expected skip (already exists, invalid amount, no subscription, etc.)
            logger.info("Skipping registration %s: %s", reg.id, exc)
            skipped += 1
        except Exception as exc:
            logger.error(
                "Failed to create recurring item for registration %s: %s", reg.id, exc
            )
            errors += 1
            db.rollback()

    return {
        "processed": processed,
        "created": created,
        "skipped": skipped,
        "errors": errors,
    }


@celery_app.task(name="create_recurring_carrier_items")
def create_recurring_carrier_items() -> dict[str, int]:
    """Daily: create recurring carrier fee subscription items for eligible tenants."""
    db: Session = next(get_db())
    try:
        result = _create_recurring_carrier_items_impl(db)
        logger.info("create_recurring_carrier_items task complete: %s", result)
        return result
    except Exception as exc:
        db.rollback()
        logger.error("create_recurring_carrier_items failed: %s", exc)
        raise
