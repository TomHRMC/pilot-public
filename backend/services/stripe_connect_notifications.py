"""
STRIPE-CONNECT-1: Stripe Connect disconnect + dispute owner-notification helpers.

Shared logic to enqueue ``stripe_connect_disconnected`` and
``stripe_dispute_opened`` notifications to the tenant owner. Mirrors the
``qb_connection_notification.py`` precedent (QB-H1): owner lookup via
``TenantUser.role_code == "owner"``, NotificationEvent + NotificationOutbox
in the same transaction.

Design: dev-docs/architecture-design/batch-designs/batch-stripe-connect-1-design.md §F.1, §F.4
"""

import logging
import uuid

from sqlmodel import Session, select

from app.models.auth import TenantUser
from app.models.core import User
from app.models.system import (
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


def _get_tenant_owner_user_id(db: Session, tenant_id: uuid.UUID) -> uuid.UUID | None:
    """Return the primary owner's user_id for this tenant, or None."""
    stmt = (
        select(TenantUser.user_id)
        .where(
            TenantUser.tenant_id == tenant_id,
            TenantUser.role_code == "owner",
            TenantUser.is_active == True,
        )
        .limit(1)
    )
    return db.exec(stmt).first()


def enqueue_connect_disconnected_notification(
    db: Session,
    tenant_id: uuid.UUID,
) -> None:
    """
    Enqueue a ``stripe_connect_disconnected`` notification to the tenant owner.

    Creates a NotificationEvent + an email NotificationOutbox entry in the
    current transaction (caller commits). Skips silently if the notification
    type is not seeded or no active owner exists.
    """
    notif_type = db.exec(
        select(NotificationType).where(
            NotificationType.code == "stripe_connect_disconnected",
            NotificationType.tenant_id == None,
        )
    ).first()
    if not notif_type:
        logger.error(
            "notification_type 'stripe_connect_disconnected' not seeded — "
            "run seed_core.py | tenant=%s",
            tenant_id,
        )
        return

    owner_email = _get_tenant_owner_email(db, tenant_id)
    if not owner_email:
        logger.warning(
            "No active owner user found for tenant %s — "
            "stripe_connect_disconnected notification not enqueued",
            tenant_id,
        )
        return

    event = NotificationEvent(
        tenant_id=tenant_id,
        notification_type_code="stripe_connect_disconnected",
        entity_type_code="tenant",
        entity_id=str(tenant_id),
        payload={"reason": "account.application.deauthorized"},
    )
    db.add(event)
    db.flush()

    outbox = NotificationOutbox(
        tenant_id=tenant_id,
        notification_event_id=event.id,
        channel="email",
        to_address=owner_email,
        subject="[Payments] Stripe account disconnected",
        body=(
            "Your Stripe Connect account has been disconnected. "
            "Card payments on invoice links are paused, and customers now see "
            "manual-payment instructions. Reconnect in Settings → Payment Method."
        ),
        status="pending",
        category_id="customer_activity",
    )
    db.add(outbox)

    logger.info(
        "stripe_connect_disconnected notification enqueued for owner | tenant=%s to=%s",
        tenant_id,
        owner_email,
    )


def enqueue_dispute_notification(
    db: Session,
    tenant_id: uuid.UUID,
    *,
    amount_display: str,
    respond_by: str,
    closed: bool,
) -> None:
    """
    Enqueue a ``stripe_dispute_opened`` notification to the tenant owner.

    For ``closed=True`` (charge.dispute.closed), the body notes the dispute
    was closed (design §F.4 — brief note in the same thread).

    Creates a NotificationEvent + an email NotificationOutbox entry in the
    current transaction (caller commits). Skips silently if the notification
    type is not seeded or no active owner exists.
    """
    notif_type = db.exec(
        select(NotificationType).where(
            NotificationType.code == "stripe_dispute_opened",
            NotificationType.tenant_id == None,
        )
    ).first()
    if not notif_type:
        logger.error(
            "notification_type 'stripe_dispute_opened' not seeded — "
            "run seed_core.py | tenant=%s",
            tenant_id,
        )
        return

    owner_email = _get_tenant_owner_email(db, tenant_id)
    if not owner_email:
        logger.warning(
            "No active owner user found for tenant %s — "
            "stripe_dispute_opened notification not enqueued",
            tenant_id,
        )
        return

    if closed:
        subject = "[Payments] A customer dispute was closed"
        body = (
            f"A customer dispute for {amount_display} has been closed. "
            "Review the outcome in your Stripe dashboard."
        )
    else:
        subject = "[Payments] A customer disputed a payment"
        body = (
            f"A customer has disputed a payment of {amount_display}. "
            f"The dispute respond-by date is {respond_by}. "
            "Respond in your Stripe dashboard — Pilot does not handle dispute "
            "resolution in-app."
        )

    event = NotificationEvent(
        tenant_id=tenant_id,
        notification_type_code="stripe_dispute_opened",
        entity_type_code="tenant",
        entity_id=str(tenant_id),
        payload={
            "amount": amount_display,
            "respond_by": respond_by,
            "closed": closed,
        },
    )
    db.add(event)
    db.flush()

    outbox = NotificationOutbox(
        tenant_id=tenant_id,
        notification_event_id=event.id,
        channel="email",
        to_address=owner_email,
        subject=subject,
        body=body,
        status="pending",
        category_id="customer_activity",
    )
    db.add(outbox)

    logger.info(
        "stripe_dispute_opened notification enqueued for owner | "
        "tenant=%s to=%s closed=%s",
        tenant_id,
        owner_email,
        closed,
    )
