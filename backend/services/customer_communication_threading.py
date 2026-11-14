"""
Customer Communication Threading Service — B11/A60
===================================================
Routes inbound SMS messages to the correct thread or parks in unrouted queue.
Also handles TCPA opt-out/opt-in state transitions.

Interface:
  route_inbound_message() — main entry point from webhook handler
  handle_sms_opt_out()    — STOP keyword processing
  handle_sms_opt_in()     — START/UNSTOP/YES processing
  handle_sms_help()       — HELP keyword processing (auto-reply with support info)
"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlmodel import Session, select

if TYPE_CHECKING:
    from app.models.crm import Customer
    from app.models.sms import CustomerCommunicationThread

logger = logging.getLogger(__name__)


@dataclass
class InboundMessage:
    """Normalized inbound SMS (mirrors sms_carrier.InboundMessage)."""

    from_number: str
    to_number: str
    body: str
    carrier_message_id: str
    received_at: str  # ISO timestamp string from carrier


@dataclass
class ThreadingResult:
    """Result of route_inbound_message()."""

    success: bool
    thread_id: UUID | None  # Set when routed to an existing or new thread
    unrouted_id: UUID | None  # Set when parked in unrouted queue
    error: str | None


def route_inbound_message(
    db: Session,
    inbound: InboundMessage,
    tenant_id: UUID,
) -> ThreadingResult:
    """
    Route an inbound SMS to the correct customer communication thread.

    Routing algorithm (§17.4):
    1. Resolve customer from inbound.from_number → customer.mobile_phone
    2. Confirm inbound.to_number is an active tenant_phone_number for this tenant
    3. Find most recent active thread within 7-day window for (customer, tech → any tech)
    4. If no recent thread: fall back to customer.last_assigned_tech_id
    5. If still no match: park in customer_communication_unrouted with owner notification

    Returns ThreadingResult with thread_id on success or unrouted_id on park.
    """
    from datetime import timedelta

    from app.models.crm import Customer
    from app.models.sms import (
        CustomerCommunicationThread,
        TenantPhoneNumber,
    )

    # Step 1: Resolve tenant_phone_number from to_number
    tenant_phone = db.exec(
        select(TenantPhoneNumber).where(
            TenantPhoneNumber.phone_number == inbound.to_number,
            TenantPhoneNumber.tenant_id == tenant_id,
            TenantPhoneNumber.status == "active",
        )
    ).first()

    if not tenant_phone:
        logger.warning(
            f"Inbound SMS to unknown number {inbound.to_number} for tenant {tenant_id} — parking"
        )
        return _park_unrouted(db, tenant_id, inbound, tenant_phone_id=None)

    # Step 2: Resolve customer from from_number
    customer = db.exec(
        select(Customer).where(
            Customer.mobile_phone == inbound.from_number,
            Customer.tenant_id == tenant_id,
            Customer.is_active.is_(True),
        )
    ).first()

    if not customer:
        logger.warning(
            f"Inbound SMS from unknown number {inbound.from_number} — parking"
        )
        return _park_unrouted(db, tenant_id, inbound, tenant_phone_id=tenant_phone.id)

    # Step 3: Find most recent active thread within 7-day window
    seven_days_ago = datetime.now(UTC) - timedelta(days=7)
    recent_thread = db.exec(
        select(CustomerCommunicationThread)
        .where(
            CustomerCommunicationThread.tenant_id == tenant_id,
            CustomerCommunicationThread.customer_id == customer.id,
            CustomerCommunicationThread.tenant_phone_number_id == tenant_phone.id,
            CustomerCommunicationThread.status == "active",
            CustomerCommunicationThread.last_message_at >= seven_days_ago,
        )
        .order_by(CustomerCommunicationThread.last_message_at.desc())
    ).first()

    if recent_thread:
        return _append_to_thread(db, recent_thread, inbound, customer)

    # Step 4: Fall back to last_assigned_tech_id
    tech_id = customer.last_assigned_tech_id
    if not tech_id:
        logger.warning(f"No last_assigned_tech_id for customer {customer.id} — parking")
        return _park_unrouted(db, tenant_id, inbound, tenant_phone_id=tenant_phone.id)

    # Create a new thread
    now = datetime.now(UTC)
    new_thread = CustomerCommunicationThread(
        tenant_id=tenant_id,
        customer_id=customer.id,
        tech_id=tech_id,
        tenant_phone_number_id=tenant_phone.id,
        status="active",
        first_message_at=now,
        last_message_at=now,
        message_count=0,
    )
    db.add(new_thread)
    db.flush()  # Get the ID before creating the message

    return _append_to_thread(db, new_thread, inbound, customer)


def _append_to_thread(
    db: Session,
    thread: "CustomerCommunicationThread",
    inbound: InboundMessage,
    customer: "Customer",
) -> ThreadingResult:
    """Create a message row and update thread metadata."""
    from app.models.sms import CustomerCommunicationMessage

    now = datetime.now(UTC)

    try:
        received_dt = datetime.fromisoformat(inbound.received_at.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        received_dt = now

    msg = CustomerCommunicationMessage(
        thread_id=thread.id,
        direction="inbound",
        channel="sms",
        body=inbound.body,
        segment_count=max(1, (len(inbound.body) + 159) // 160),
        status="received",
        carrier_message_id=inbound.carrier_message_id,
        received_at=received_dt,
        audit_user_id=thread.tech_id,
    )
    db.add(msg)

    # Update thread counters
    thread.last_message_at = received_dt
    thread.message_count = (thread.message_count or 0) + 1
    db.add(thread)
    db.commit()

    logger.info(f"Routed inbound SMS to thread {thread.id} for customer {customer.id}")
    return ThreadingResult(
        success=True, thread_id=thread.id, unrouted_id=None, error=None
    )


def _park_unrouted(
    db: Session,
    tenant_id: UUID,
    inbound: InboundMessage,
    tenant_phone_id: UUID | None,
) -> ThreadingResult:
    """Park an unroutable inbound message in the unrouted queue."""
    from app.models.sms import CustomerCommunicationUnrouted

    try:
        received_dt = datetime.fromisoformat(inbound.received_at.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        received_dt = datetime.now(UTC)

    now = datetime.now(UTC)
    unrouted = CustomerCommunicationUnrouted(
        tenant_id=tenant_id,
        from_number=inbound.from_number,
        to_number=inbound.to_number,
        body=inbound.body,
        carrier_message_id=inbound.carrier_message_id,
        received_at=received_dt,
        parked_at=now,
        status="parked",
    )
    db.add(unrouted)
    db.commit()
    db.refresh(unrouted)

    logger.info(f"Parked unroutable inbound SMS in unrouted queue: {unrouted.id}")
    return ThreadingResult(
        success=True, thread_id=None, unrouted_id=unrouted.id, error=None
    )


def handle_sms_opt_out(
    db: Session,
    customer_id: UUID,
    opt_out_message: InboundMessage,
) -> None:
    """
    Process TCPA STOP command.

    1. Sets customer.sms_opted_out = True, sms_opt_out_at = now()
    2. Sets customer.sms_verification_status = 'opted_out' (DLC-1)
    3. Sends DLC spec §2.4-compliant confirmation reply
    """
    import hashlib
    import uuid as _uuid

    from app.models.crm import Customer, CustomerSmsConsentAudit
    from services.sms_carrier import get_sms_carrier

    customer = db.exec(select(Customer).where(Customer.id == customer_id)).first()

    if not customer:
        logger.warning(f"handle_sms_opt_out: customer {customer_id} not found")
        return

    now = datetime.now(UTC)
    customer.sms_opted_out = True
    customer.sms_opt_out_at = now
    # DLC-1: update verification status
    customer.sms_verification_status = "opted_out"
    db.add(customer)
    db.commit()

    # DLC-1: Write audit row for opt-out event (only if we have a valid user FK)
    _attested_by = customer.last_assigned_tech_id or customer.created_by
    if _attested_by is not None:
        try:
            consent_text = "Customer replied STOP — opted out of SMS communications."
            audit_row = CustomerSmsConsentAudit(
                id=_uuid.uuid4(),
                created_at=now,
                tenant_id=customer.tenant_id,
                customer_id=customer.id,
                attested_by=_attested_by,
                ip_address="inbound_sms",
                attested_at=now,
                consent_text_hash=hashlib.sha256(consent_text.encode()).hexdigest(),
                action="opted_out",
            )
            db.add(audit_row)
            db.commit()
        except Exception as exc:
            logger.warning(f"handle_sms_opt_out: failed to write audit row: {exc}")

    logger.info(f"Customer {customer_id} opted out of SMS (STOP keyword)")

    # Send DLC spec §2.4-compliant confirmation (playbook §8 — STOP reply)
    carrier = get_sms_carrier()
    try:
        carrier.send_message(
            from_number=opt_out_message.to_number,
            to_number=opt_out_message.from_number,
            body=(
                "You have been unsubscribed from Pilot for Trades messages. "
                "No further messages will be sent. Reply START to re-subscribe."
            ),
        )
    except Exception as exc:
        logger.error(
            f"Failed to send opt-out confirmation to {opt_out_message.from_number}: {exc}"
        )


def handle_sms_opt_in(
    db: Session,
    customer_id: UUID,
    opt_in_message: InboundMessage,
) -> None:
    """
    Process TCPA START/UNSTOP/YES from a previously opted-out customer.

    1. Sets customer.sms_opted_out = False, sms_opt_in_consent = True
    2. Sets sms_opt_in_at = now(), sms_opt_in_source = 'inbound_initiated'
    3. Sets customer.sms_verification_status = 'verified' (DLC-1)
    4. Writes CustomerSmsConsentAudit row with action='double_opt_in_confirmed' (DLC-1)
    5. Sends confirmation reply with tenant business name
    """
    import hashlib
    import uuid as _uuid

    from app.models.crm import Customer, CustomerSmsConsentAudit
    from services.sms_carrier import get_sms_carrier

    customer = db.exec(select(Customer).where(Customer.id == customer_id)).first()

    if not customer:
        logger.warning(f"handle_sms_opt_in: customer {customer_id} not found")
        return

    now = datetime.now(UTC)
    customer.sms_opted_out = False
    customer.sms_opt_in_consent = True
    customer.sms_opt_in_at = now
    customer.sms_opt_in_source = "inbound_initiated"
    # DLC-1: mark as verified on YES reply
    customer.sms_verification_status = "verified"
    db.add(customer)
    db.commit()

    # DLC-1: Write audit row for double opt-in confirmed (only if we have a valid user FK)
    _attested_by = customer.last_assigned_tech_id or customer.created_by
    if _attested_by is not None:
        try:
            consent_text = "Customer replied YES — double opt-in confirmed."
            audit_row = CustomerSmsConsentAudit(
                id=_uuid.uuid4(),
                created_at=now,
                tenant_id=customer.tenant_id,
                customer_id=customer.id,
                attested_by=_attested_by,
                ip_address="inbound_sms",
                attested_at=now,
                consent_text_hash=hashlib.sha256(consent_text.encode()).hexdigest(),
                action="double_opt_in_confirmed",
            )
            db.add(audit_row)
            db.commit()
        except Exception as exc:
            logger.warning(f"handle_sms_opt_in: failed to write audit row: {exc}")

    logger.info(f"Customer {customer_id} opted back in to SMS (START/UNSTOP/YES)")

    # Send confirmation (playbook §8 — START/YES reply; no MFA/login framing)
    carrier = get_sms_carrier()
    try:
        carrier.send_message(
            from_number=opt_in_message.to_number,
            to_number=opt_in_message.from_number,
            body=(
                "Pilot for Trades: You're opted in to receive service updates. "
                "Msg freq varies. Msg & data rates may apply. "
                "Reply HELP for help, STOP to cancel."
            ),
        )
    except Exception as exc:
        logger.error(
            f"Failed to send opt-in confirmation to {opt_in_message.from_number}: {exc}"
        )


def handle_sms_help(
    inbound_message: InboundMessage,
    db: Session | None = None,
) -> None:
    """
    Process TCPA HELP keyword — send DLC spec §2.4-compliant auto-reply.

    Does NOT require a matched customer — HELP is answered for any inbound number.
    No DB state change is made; this is a pure outbound auto-reply.
    Fixed brand string per playbook §8 — no dynamic lookup needed.
    """
    from services.sms_carrier import get_sms_carrier

    # Compliant HELP reply (playbook §8 — includes website, email, rates, STOP)
    body = (
        "Pilot for Trades service messages. "
        "For help, visit pilotfortrades.com or email info@pilotfortrades.com. "
        "Msg & data rates may apply. Reply STOP to unsubscribe."
    )

    carrier = get_sms_carrier()
    try:
        carrier.send_message(
            from_number=inbound_message.to_number,
            to_number=inbound_message.from_number,
            body=body,
        )
        logger.info(f"Sent HELP auto-reply to {inbound_message.from_number}")
    except Exception as exc:
        logger.error(
            f"Failed to send HELP auto-reply to {inbound_message.from_number}: {exc}"
        )
