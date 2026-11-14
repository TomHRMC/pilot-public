"""
QB-H1: QuickBooks connection-expiry notification helper.

Shared logic to enqueue a ``qb_connection_expired`` notification to the tenant
owner when a QuickBooks OAuth refresh fails permanently (invalid_grant / 400 /
401). Used by both the Celery beat task (``tasks/quickbooks_token_refresh.py``)
and the async route (``api/routes/integrations.py``).

Design: dev-docs/architecture-design/batch-designs/batch-qb-h1-design.md §F.1–F.3
"""

import logging
import uuid

from sqlmodel import Session, select

from app.models.auth import TenantUser
from app.models.core import User
from app.models.system import (
    IntegrationCredential,
    NotificationEvent,
    NotificationOutbox,
    NotificationType,
)

logger = logging.getLogger(__name__)


def _get_tenant_owner_email(db: Session, tenant_id: uuid.UUID) -> str | None:
    """Return the primary owner's email for this tenant, or None."""
    stmt = (
        select(User.email)
        .join(TenantUser, TenantUser.user_id == User.id)
        .where(
            TenantUser.tenant_id == tenant_id,
            TenantUser.role_code == "owner",
            TenantUser.is_active == True,
        )
        .limit(1)
    )
    return db.exec(stmt).first()


def enqueue_connection_expired_notification(
    db: Session,
    credential: IntegrationCredential,
    intuit_tid: str | None = None,
) -> None:
    """
    Mark the credential ``expired`` and enqueue a ``qb_connection_expired``
    email notification to the tenant owner.

    This mirrors the ``queue_conflict`` notification pattern in
    ``services/quickbooks_sync.py`` (NotificationEvent + NotificationOutbox
    in the same transaction).

    Args:
        db: Active DB session (caller commits).
        credential: The IntegrationCredential to mark expired.
        intuit_tid: Optional Intuit trace ID for log correlation.
    """
    tenant_id = credential.tenant_id

    # Mark the connection expired
    credential.connection_status = "expired"
    db.add(credential)

    # Look up the notification type (platform default, tenant_id IS NULL)
    notif_type = db.exec(
        select(NotificationType).where(
            NotificationType.code == "qb_connection_expired",
            NotificationType.tenant_id == None,
        )
    ).first()
    if not notif_type:
        logger.error(
            "notification_type 'qb_connection_expired' not seeded — "
            "run seed_core.py | tenant=%s intuit_tid=%s",
            tenant_id,
            intuit_tid or "unknown",
        )
        return

    # Resolve the tenant owner email
    owner_email = _get_tenant_owner_email(db, tenant_id)
    if not owner_email:
        logger.warning(
            "No active owner user found for tenant %s — "
            "qb_connection_expired notification not enqueued | intuit_tid=%s",
            tenant_id,
            intuit_tid or "unknown",
        )
        return

    # Create the notification event record
    event = NotificationEvent(
        tenant_id=tenant_id,
        notification_type_code="qb_connection_expired",
        entity_type_code="tenant",
        entity_id=str(tenant_id),
        payload={"credential_id": str(credential.id), "intuit_tid": intuit_tid},
    )
    db.add(event)
    db.flush()  # get event.id before outbox creation

    # Enqueue the email outbox record
    outbox = NotificationOutbox(
        tenant_id=tenant_id,
        notification_event_id=event.id,
        channel="email",
        to_address=owner_email,
        subject="[QuickBooks] Connection expired — reconnect to resume sync",
        body=(
            "Your QuickBooks Online connection has expired. "
            "The refresh token was rejected by Intuit, so customer, invoice, "
            "and payment sync is paused. No data was lost — queued changes will "
            "resume automatically after you reconnect. "
            "Go to Settings → Integrations → QuickBooks → Reconnect."
        ),
        status="pending",
        category_id="sync_conflicts",
    )
    db.add(outbox)

    logger.info(
        "QB connection expired — notification enqueued for owner | "
        "tenant=%s to=%s intuit_tid=%s",
        tenant_id,
        owner_email,
        intuit_tid or "unknown",
    )
