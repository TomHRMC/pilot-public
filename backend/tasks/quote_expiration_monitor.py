"""
Quote expiration monitoring task — daily Celery Beat task.

Executes daily at 1:00 AM UTC. Queries all quotes with status='sent' and expires_at < NOW(),
then transitions each to 'expired' status via quote_service.transition_quote_status().

Established: B19 (FIND-096)
Consumed by: Celery Beat schedule (backend/core/celery_app.py)
"""

import logging
from datetime import UTC, datetime

from sqlmodel import Session, select

from app.models.quoting import Quote, QuoteStatus
from core.celery_app import celery_app
from core.db import get_db
from services.quote_service import transition_quote_status

logger = logging.getLogger(__name__)


@celery_app.task(name="quote_expiration_monitor")
def quote_expiration_monitor() -> dict[str, int]:
    """
    Monitor and auto-expire quotes. Run by Celery Beat daily at 1:00 AM UTC.
    Transitions all quotes with status='sent' and expires_at < NOW() to 'expired' status.

    Returns:
        Dict with counts: {"expired_count": int, "processed": int, "errors": int}
    """
    db: Session = next(get_db())
    expired_count = 0
    errors = 0

    try:
        # Query all quotes with status='sent' and expires_at < NOW()
        # Performance note: index on expires_at helps filter quickly
        now = datetime.now(UTC)

        # First, get all 'sent' status rows
        sent_status_rows = db.exec(
            select(QuoteStatus).where(QuoteStatus.code == "sent")
        ).all()

        if not sent_status_rows:
            logger.warning("quote_expiration_monitor: no 'sent' status found in DB")
            return {"expired_count": 0, "processed": 0, "errors": 0}

        sent_status_ids = [s.id for s in sent_status_rows]

        # Query all quotes with status in sent_status_ids and expires_at < now
        expirable_quotes = db.exec(
            select(Quote)
            .where(Quote.status_id.in_(sent_status_ids))
            .where(Quote.expires_at < now)
            .where(Quote.expires_at.is_not(None))
        ).all()

        logger.info(
            "quote_expiration_monitor: found %d quotes ready to expire",
            len(expirable_quotes),
        )

        for quote in expirable_quotes:
            try:
                # Transition to 'expired' status
                transition_quote_status(
                    quote=quote,
                    new_status_code="expired",
                    db=db,
                    tenant_id=quote.tenant_id,
                )
                expired_count += 1
            except Exception as e:
                errors += 1
                logger.error(
                    "quote_expiration_monitor: error expiring quote %s: %s",
                    quote.id,
                    e,
                )

        return {
            "expired_count": expired_count,
            "processed": len(expirable_quotes),
            "errors": errors,
        }

    except Exception as e:
        logger.error("quote_expiration_monitor: task failed: %s", e)
        raise

    finally:
        db.close()
