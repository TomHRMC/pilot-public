"""# noqa: E501
tasks/auto_expire_qb_conflicts.py

B8/A50: Auto-expiry background task for stale QB sync conflicts.

Mirrors expire_stale_calendar_conflicts from B6/A34 but for QuickBooks conflicts.
Default expiry: 60 days (vs calendar 30) per accounting cadence.
System default: 14 days pre-warning (vs calendar 7).

Beat schedule: daily at 3:30 AM UTC.
"""

import json
import logging
from datetime import UTC, datetime

from sqlmodel import Session, select

from app.models.system import IntegrationSyncConflict, NotificationOutbox
from core.celery_app import celery_app
from core.db import get_db

logger = logging.getLogger(__name__)

# System-level defaults removed (FIND-086): use get_effective_setting(db, tenant_id, "qb_auto_expire_days")
# SYSTEM_QB_AUTO_EXPIRE_DAYS and SYSTEM_QB_PRE_WARNING_DAYS deleted — values now live in platform_setting


@celery_app.task(name="auto_expire_qb_conflicts_per_tenant")
def auto_expire_qb_conflicts_per_tenant() -> dict[str, int]:
    """
    Auto-expire stale QB sync conflicts per tenant settings.

    For each pending conflict:
    1. Calculates effective expiry days (tenant override or system default 60)
    2. If now >= auto_expire_at and auto_expire_at is set → expire the conflict
    3. If now >= pre_warning_at and pre_warning_at is set → insert notification_outbox row

    Returns count dict for logging/monitoring.
    """
    db: Session = next(get_db())
    expired = 0
    pre_warned = 0

    try:
        from app.models.system import (
            IntegrationSyncConflict,
            NotificationOutbox,
        )

        now = datetime.now(UTC)

        # Process conflicts with auto_expire_at set and past due
        expire_stmt = select(IntegrationSyncConflict).where(
            IntegrationSyncConflict.status == "pending",
            IntegrationSyncConflict.auto_expire_at != None,
            IntegrationSyncConflict.auto_expire_at <= now,
        )
        to_expire = db.exec(expire_stmt).all()

        for conflict in to_expire:
            conflict.status = "resolved_keep_internal"  # owner-side wins on expiry
            conflict.resolved_at = now
            db.add(conflict)
            expired += 1

        # Process conflicts with pre_warning_at set and past due
        # Insert notification_outbox if not already notified (simple check: pre_warning_at past)
        pre_warn_stmt = select(IntegrationSyncConflict).where(
            IntegrationSyncConflict.status == "pending",
            IntegrationSyncConflict.pre_warning_at != None,
            IntegrationSyncConflict.pre_warning_at <= now,
            IntegrationSyncConflict.auto_expire_at
            != None,  # only warn if expiry is also set
            IntegrationSyncConflict.auto_expire_at > now,  # conflict not yet expired
        )
        to_pre_warn = db.exec(pre_warn_stmt).all()

        for conflict in to_pre_warn:
            # Insert notification_outbox row for pre-warning (email to owner)
            outbox = NotificationOutbox(
                tenant_id=conflict.tenant_id,
                notification_type_code="qb_conflict_pre_warning",
                channel="email",
                body=json.dumps(
                    {
                        "conflict_id": str(conflict.id),
                        "entity_type": conflict.entity_type_code,
                        "entity_id": str(conflict.entity_id),
                        "external_id": conflict.external_id,
                        "expires_at": conflict.auto_expire_at.isoformat()
                        if conflict.auto_expire_at
                        else None,
                        "message": (
                            f"QB conflict for {conflict.entity_type_code} #{conflict.external_id} "
                            f"will auto-expire soon. Please review."
                        ),
                    }
                ),
                category_id="sync_conflicts",  # B10/A56
            )
            db.add(outbox)
            # Advance pre_warning_at to prevent repeated warnings (set to None)
            conflict.pre_warning_at = None
            db.add(conflict)
            pre_warned += 1

        db.commit()
        logger.info(
            "auto_expire_qb_conflicts: expired=%d, pre_warned=%d",
            expired,
            pre_warned,
        )
        return {"expired": expired, "pre_warned": pre_warned}

    except Exception as e:
        db.rollback()
        logger.error("Error in auto_expire_qb_conflicts_per_tenant: %s", e)
        raise

    finally:
        db.close()


def _auto_expire_qb_conflicts_impl(db: Session) -> dict[str, int]:
    """
    Inner implementation — separated for testability without Celery.

    Processes all pending QB conflicts across all tenants.
    Returns dict of expired and pre_warned counts.
    """

    now = datetime.now(UTC)
    expired = 0
    pre_warned = 0

    # Expire past-due conflicts
    to_expire = db.exec(
        select(IntegrationSyncConflict).where(
            IntegrationSyncConflict.status == "pending",
            IntegrationSyncConflict.auto_expire_at != None,
            IntegrationSyncConflict.auto_expire_at <= now,
        )
    ).all()

    for conflict in to_expire:
        conflict.status = "resolved_keep_internal"
        conflict.resolved_at = now
        db.add(conflict)
        expired += 1

    # Pre-warn past-due pre_warning_at
    to_pre_warn = db.exec(
        select(IntegrationSyncConflict).where(
            IntegrationSyncConflict.status == "pending",
            IntegrationSyncConflict.pre_warning_at != None,
            IntegrationSyncConflict.pre_warning_at <= now,
            IntegrationSyncConflict.auto_expire_at != None,
            IntegrationSyncConflict.auto_expire_at > now,
        )
    ).all()

    for conflict in to_pre_warn:
        outbox = NotificationOutbox(
            tenant_id=conflict.tenant_id,
            notification_type_code="qb_conflict_pre_warning",
            channel="email",
            body=json.dumps(
                {
                    "conflict_id": str(conflict.id),
                    "entity_type": conflict.entity_type_code,
                }
            ),
            category_id="sync_conflicts",  # B10/A56
        )
        db.add(outbox)
        conflict.pre_warning_at = None
        db.add(conflict)
        pre_warned += 1

    db.commit()
    return {"expired": expired, "pre_warned": pre_warned}
