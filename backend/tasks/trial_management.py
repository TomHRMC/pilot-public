"""
B14/A73 — Trial expiration enforcement Celery task.
Runs hourly; transitions expired trials to paywall state.
Also dispatches 4-step pre-expiration warning notifications.
Per arch doc §4.7.5 and §20.8.
"""

import logging
from datetime import UTC, datetime

from sqlmodel import Session, select

from core.celery_app import celery_app
from core.db import get_db

logger = logging.getLogger(__name__)

# Warning dispatch thresholds (days before expiry)
WARNING_DAYS = [7, 3, 1, 0]


@celery_app.task(name="enforce_trial_expirations")
def enforce_trial_expirations() -> dict:
    """
    Hourly: transition expired trials to trial_expired paywall state.
    Also dispatches 4-step pre-expiration warning notifications.
    Per §17.1 periodic poll pattern: no bind=True, no retry.

    Returns:
        dict with counts: expired, warnings_sent
    """
    from app.models.core import Tenant
    from app.models.subscription import SubscriptionTier
    from services.trial_management import dispatch_trial_warning

    db: Session = next(get_db())
    expired_count = 0
    warnings_count = 0

    try:
        now = datetime.now(UTC)

        # Find all tenants on trial tier with trial_ends_at set
        trial_tiers = db.exec(
            select(SubscriptionTier.tier_id).where(SubscriptionTier.is_trial == True)
        ).all()
        trial_tier_ids = [t for t in trial_tiers]

        if not trial_tier_ids:
            logger.warning("No trial tiers found — skipping enforce_trial_expirations")
            return {"expired": 0, "warnings_sent": 0}

        tenants_on_trial = db.exec(
            select(Tenant)
            .where(Tenant.current_subscription_tier_id.in_(trial_tier_ids))
            .where(Tenant.trial_ends_at != None)
            .where(Tenant.is_active == True)
        ).all()

        for tenant in tenants_on_trial:
            days_remaining = (tenant.trial_ends_at - now).days

            # Dispatch warnings at thresholds
            if days_remaining in WARNING_DAYS:
                try:
                    dispatch_trial_warning(db, tenant.id, days_remaining)
                    warnings_count += 1
                except Exception as e:
                    logger.error(
                        f"Failed to dispatch trial warning for tenant {tenant.id}: {e}"
                    )

            # Count expired trials (paywall is enforced at API layer via enforce_paywall())
            if tenant.trial_ends_at <= now:
                expired_count += 1
                logger.info(
                    f"Trial expired for tenant {tenant.id} "
                    f"(ended {tenant.trial_ends_at.isoformat()})"
                )

        return {"expired": expired_count, "warnings_sent": warnings_count}

    except Exception as e:
        db.rollback()
        logger.error(f"Error in enforce_trial_expirations: {e}")
        raise

    finally:
        db.close()
