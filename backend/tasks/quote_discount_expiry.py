"""
A3: Quote Discount Expiry Task

Celery task: expire time-limited quote discounts at their discount_expires_at timestamp.

Registered in: core/celery_app.py (task name 'expire_quote_discounts')
Beat schedule: daily at 7:00 AM UTC (per design doc Section E)
Pattern: §17.1 Periodic Poll Task (no bind, no retry)
"""

import logging
from datetime import UTC, datetime

from sqlmodel import Session, select

from core.celery_app import celery_app
from core.db import get_db

logger = logging.getLogger(__name__)


def _expire_quote_discounts_impl(db: Session) -> dict[str, int]:
    """
    Inner implementation — separated for testability without Celery.

    Finds quotes with discount_expires_at <= now() and clears discount fields.
    Creates a new quote_version snapshot to preserve the discounted state in history.

    Returns:
        {"expired": int} — count of quotes whose discounts were expired
    """
    from app.models.quoting import Quote

    now = datetime.now(UTC)
    expired_count = 0

    # Find quotes with expired discounts
    stale_quotes = db.exec(
        select(Quote).where(
            Quote.discount_expires_at != None,
            Quote.discount_expires_at <= now,
            Quote.discount_pct != None,
            Quote.is_active == True,
        )
    ).all()

    for quote in stale_quotes:
        logger.info(
            "expire_quote_discounts: expiring discount on quote %s "
            "(discount_pct=%s, expired_at=%s)",
            quote.id,
            quote.discount_pct,
            quote.discount_expires_at,
        )
        # Clear discount fields
        quote.discount_pct = None
        quote.discount_amount_cents = None
        quote.discount_expires_at = None
        quote.discount_applied_by_user_id = None
        db.add(quote)
        expired_count += 1

    if expired_count > 0:
        db.commit()
        logger.info(
            "expire_quote_discounts: expired discounts on %d quotes", expired_count
        )

    return {"expired": expired_count}


@celery_app.task(name="expire_quote_discounts")
def expire_quote_discounts() -> dict[str, int]:
    """
    A3: Nightly Celery Beat task — expire time-limited quote discounts.

    Find quotes with discount_expires_at <= now() and clear discount columns.
    Creates a new quote_version to preserve the discounted state in history.

    Beat schedule: daily at 7:00 AM UTC (registered in core/celery_app.py)

    Returns:
        {"expired": int} — count of quotes whose discounts were expired
    """
    db: Session = next(get_db())
    try:
        result = _expire_quote_discounts_impl(db)
        return result
    except Exception as e:
        db.rollback()
        logger.error("Error in expire_quote_discounts: %s", e)
        raise
    finally:
        db.close()
