"""
Telnyx Inbound SMS Webhook Handler — B11/A59
=============================================
Route: POST /api/v1/webhooks/sms/telnyx-inbound

Public endpoint (no JWT) — authenticated by Telnyx public-key signature.
Handles:
  1. Signature verification (401 on failure — Telnyx retries)
  2. TCPA keyword detection (STOP → opt-out, START/UNSTOP/YES → opt-in, HELP → auto-reply)
  3. Route to customer thread via route_inbound_message()
  4. Park unroutable messages in customer_communication_unrouted
  5. Delivery-status reconciliation for message.sent / message.finalized (DLC-B5)

TCPA stop keywords (exact-match, case-insensitive, stripped):
    STOP, STOPALL, UNSUBSCRIBE, QUIT, CANCEL, END, ARRET

TCPA re-opt-in keywords:
    START, UNSTOP, YES

TCPA help keywords:
    HELP, INFO
"""

import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from sqlmodel import Session, select
from starlette.requests import ClientDisconnect

from core.db import get_db

logger = logging.getLogger(__name__)

router = APIRouter()

# TCPA keyword sets (case-insensitive, exact-match on stripped body).
# These MUST match the keywords declared in the Telnyx customer-comms campaign.
# See dev-docs/integrations/telnyx/telnyx-10dlc-customer-comms-campaign.md §7.
#   Opt-out:  STOP, STOPALL, UNSUBSCRIBE, QUIT, CANCEL, END, ARRET (French STOP)
#   Opt-in:   START, UNSTOP, YES
#   Help:     HELP, INFO
_STOP_KEYWORDS = frozenset(
    ["stop", "stopall", "unsubscribe", "quit", "cancel", "end", "arret"]
)
_OPTIN_KEYWORDS = frozenset(["start", "unstop", "yes"])
_HELP_KEYWORDS = frozenset(["help", "info"])


def _is_stop_keyword(body: str) -> bool:
    return body.strip().lower() in _STOP_KEYWORDS


def _is_optin_keyword(body: str) -> bool:
    return body.strip().lower() in _OPTIN_KEYWORDS


def _is_help_keyword(body: str) -> bool:
    return body.strip().lower() in _HELP_KEYWORDS


# ---------------------------------------------------------------------------
# SIGNUP-C / Pathway C — user_endpoint (owner) target resolution + handlers.
# These resolve an inbound SMS to a ``user_endpoint`` (channel='sms') by the
# inbound ``from`` number, distinct from the customer-resolution path. The
# customer path (Pathway B) remains intact — owner resolution is an ADDITIONAL
# match, not a replacement.
# ---------------------------------------------------------------------------


def _resolve_owner_sms_endpoint(db: Session, from_number: str):
    """
    Resolve an active ``user_endpoint`` (channel='sms') by the inbound from_number.

    Returns the ``UserEndpoint`` or None. A user has at most one active sms
    endpoint; if multiple exist (legacy), the most recently created is returned.
    """
    from app.models.core import UserEndpoint

    return db.exec(
        select(UserEndpoint)
        .where(
            UserEndpoint.channel == "sms",
            UserEndpoint.value == from_number,
            UserEndpoint.is_active == True,
        )
        .order_by(UserEndpoint.created_at.desc())
    ).first()


def _handle_owner_opt_in(db: Session, endpoint, inbound) -> None:
    """
    Process TCPA START/UNSTOP/YES for an owner ``user_endpoint`` (Pathway C).

    Sets ``consent_status='opted_in'``, ``verification_status='verified'``,
    ``verified_at``/``consent_updated_at``=now, writes
    ``user_sms_consent_audit(action='double_opt_in_confirmed')``, and replies
    with the §8 opt-in string.
    """
    from datetime import UTC, datetime

    from app.models.auth import TenantUser
    from services.notification_endpoints import hash_consent_text, write_consent_audit
    from services.platform_sms_templates import get_platform_sms_body
    from services.sms_carrier import get_sms_carrier

    # PLATFORM-SMS-B1: Load the campaign-locked opt-in reply body from the
    # single DB content path (notification_template system row, channel='sms').
    # Fail-loud: a missing row raises PlatformSmsTemplateMissingError.
    optin_body = get_platform_sms_body(db, "platform_sms_optin_reply")

    now = datetime.now(UTC)
    endpoint.consent_status = "opted_in"
    endpoint.verification_status = "verified"
    endpoint.verified_at = now
    endpoint.consent_updated_at = now
    db.add(endpoint)
    db.commit()

    # Resolve tenant_id via tenant_user for the audit row.
    tenant_user = db.exec(
        select(TenantUser).where(TenantUser.user_id == endpoint.user_id)
    ).first()
    if tenant_user is not None:
        try:
            write_consent_audit(
                db,
                tenant_id=tenant_user.tenant_id,
                user_id=endpoint.user_id,
                user_endpoint_id=endpoint.id,
                action="double_opt_in_confirmed",
                consent_text_hash=hash_consent_text(optin_body),
                created_by=endpoint.user_id,
            )
        except Exception as exc:
            logger.warning(
                "_handle_owner_opt_in: failed to write audit row for user %s: %s",
                endpoint.user_id,
                exc,
            )

    logger.info(
        "Owner user_endpoint %s (user %s) opted in via YES/START — verified",
        endpoint.id,
        endpoint.user_id,
    )

    carrier = get_sms_carrier()
    try:
        carrier.send_message(
            from_number=inbound.to_number,
            to_number=inbound.from_number,
            body=optin_body,
        )
    except Exception as exc:
        logger.error(
            "Failed to send platform opt-in confirmation to %s: %s",
            inbound.from_number,
            exc,
        )


def _handle_owner_opt_out(db: Session, endpoint, inbound) -> None:
    """
    Process TCPA STOP for an owner ``user_endpoint`` (Pathway C).

    Sets ``consent_status='opted_out'``, ``consent_updated_at``=now, writes
    ``user_sms_consent_audit(action='opted_out')``, and replies with the §8
    opt-out string.
    """
    from datetime import UTC, datetime

    from app.models.auth import TenantUser
    from services.notification_endpoints import hash_consent_text, write_consent_audit
    from services.platform_sms_templates import get_platform_sms_body
    from services.sms_carrier import get_sms_carrier

    # PLATFORM-SMS-B1: Load the campaign-locked opt-out reply body from the
    # single DB content path (notification_template system row, channel='sms').
    # Fail-loud: a missing row raises PlatformSmsTemplateMissingError.
    optout_body = get_platform_sms_body(db, "platform_sms_optout_reply")

    now = datetime.now(UTC)
    endpoint.consent_status = "opted_out"
    endpoint.consent_updated_at = now
    db.add(endpoint)
    db.commit()

    tenant_user = db.exec(
        select(TenantUser).where(TenantUser.user_id == endpoint.user_id)
    ).first()
    if tenant_user is not None:
        try:
            write_consent_audit(
                db,
                tenant_id=tenant_user.tenant_id,
                user_id=endpoint.user_id,
                user_endpoint_id=endpoint.id,
                action="opted_out",
                consent_text_hash=hash_consent_text(optout_body),
                created_by=endpoint.user_id,
            )
        except Exception as exc:
            logger.warning(
                "_handle_owner_opt_out: failed to write audit row for user %s: %s",
                endpoint.user_id,
                exc,
            )

    logger.info(
        "Owner user_endpoint %s (user %s) opted out via STOP",
        endpoint.id,
        endpoint.user_id,
    )

    carrier = get_sms_carrier()
    try:
        carrier.send_message(
            from_number=inbound.to_number,
            to_number=inbound.from_number,
            body=optout_body,
        )
    except Exception as exc:
        logger.error(
            "Failed to send platform opt-out confirmation to %s: %s",
            inbound.from_number,
            exc,
        )


def _handle_owner_help(db: Session, inbound) -> None:
    """
    Process TCPA HELP for an owner number (Pathway C) — pure auto-reply.

    No DB state change. Replies with the §8 help string loaded from the
    single DB content path (PLATFORM-SMS-B1).
    """
    from services.platform_sms_templates import get_platform_sms_body
    from services.sms_carrier import get_sms_carrier

    # PLATFORM-SMS-B1: Load the campaign-locked help reply body from the
    # single DB content path. Fail-loud on missing row.
    help_body = get_platform_sms_body(db, "platform_sms_help_reply")

    carrier = get_sms_carrier()
    try:
        carrier.send_message(
            from_number=inbound.to_number,
            to_number=inbound.from_number,
            body=help_body,
        )
        logger.info("Sent platform HELP auto-reply to %s", inbound.from_number)
    except Exception as exc:
        logger.error(
            "Failed to send platform HELP auto-reply to %s: %s",
            inbound.from_number,
            exc,
        )


# ---------------------------------------------------------------------------
# DLC-B5: Delivery-status mapping helper
# ---------------------------------------------------------------------------

# Telnyx per-recipient status → our customer_communication_message.status
# Rule: delivered → delivered (set delivered_at)
#       sent / sending / queued / delivery_unconfirmed → sent (no-op usually)
#       delivery_failed / sending_failed (or non-empty errors[]) → failed
_TELNYX_STATUS_MAP: dict[str, str] = {
    "delivered": "delivered",
    "sent": "sent",
    "sending": "sent",
    "queued": "sent",
    "delivery_unconfirmed": "sent",
    "delivery_failed": "failed",
    "sending_failed": "failed",
    # older Telnyx alias seen in some payloads
    "failed": "failed",
}


def _map_delivery_status(telnyx_status: str, has_errors: bool) -> str:
    """
    Pure helper: map a Telnyx per-recipient status string to our DB status.

    Args:
        telnyx_status: Value from data.payload.to[0].status in the Telnyx webhook.
        has_errors:    True if data.payload.errors[] is non-empty.

    Returns:
        One of: 'delivered' | 'sent' | 'failed'
        (All are valid per customer_communication_message.status CHECK constraint.)

    This function has no side-effects and no DB dependency — unit-testable without
    a database session.
    """
    # Non-empty errors[] always maps to failed, regardless of the to[0].status field.
    if has_errors:
        return "failed"
    return _TELNYX_STATUS_MAP.get(telnyx_status, "sent")


# ---------------------------------------------------------------------------
# DLC-B5: Delivery-status background task
# ---------------------------------------------------------------------------


def _process_delivery_status(
    raw_payload: bytes,
    db_session_factory,
) -> None:
    """
    Background task: reconcile delivery status for an outbound SMS after the
    Telnyx message.sent or message.finalized webhook has been verified.

    Opens its own DB session (separate from the request-scoped session) —
    mirrors _process_inbound_sms exactly.

    Lookup key: carrier_message_id (data.payload.id). This is the one legitimate
    exception to tenant-scoping (Rule 6) — the carrier webhook does not carry
    tenant context; carrier_message_id is globally unique per Telnyx. The webhook
    endpoint is public; tenant resolution is unnecessary for delivery reconciliation.

    Idempotency invariant: a row with status='delivered' is never regressed.
    Once delivered, stay delivered. 'failed' may overwrite 'sent'; nothing
    overwrites 'delivered'.
    """
    import json as _json
    from datetime import UTC, datetime

    from app.models.sms import CustomerCommunicationMessage

    db: Session = next(db_session_factory())

    try:
        # 1. Parse payload — extract carrier_message_id, to[0].status, errors[]
        try:
            body = _json.loads(raw_payload)
        except Exception as exc:
            logger.error("DLC-B5: failed to parse delivery-status payload: %s", exc)
            return

        event_payload = body.get("data", {}).get("payload", {})
        carrier_message_id: str = event_payload.get("id", "")
        recipients: list = event_payload.get("to", [])
        telnyx_status: str = recipients[0].get("status", "") if recipients else ""
        errors: list = event_payload.get("errors", []) or []
        has_errors = len(errors) > 0

        if not carrier_message_id:
            logger.debug("DLC-B5: delivery-status webhook has no payload.id — skipping")
            return

        # 2. Look up the outbound row by carrier_message_id (tenant-agnostic — Rule 6).
        #    carrier_message_id is globally unique per Telnyx; no tenant filter needed.
        msg = db.exec(
            select(CustomerCommunicationMessage).where(
                CustomerCommunicationMessage.carrier_message_id == carrier_message_id
            )
        ).first()

        if msg is None:
            # No match: Telnyx sends status for messages we didn't originate (e.g. test
            # sends in the portal), or the carrier_message_id hasn't been stored yet.
            # Clean no-op — do not crash.
            logger.debug(
                "DLC-B5: no outbound row found for carrier_message_id=%r — no-op",
                carrier_message_id,
            )
            return

        # 3. Map Telnyx status → our status
        new_status = _map_delivery_status(telnyx_status, has_errors)

        # 4. Idempotency invariant: never regress a delivered row.
        if msg.status == "delivered":
            logger.debug(
                "DLC-B5: carrier_message_id=%r already delivered — idempotent no-op",
                carrier_message_id,
            )
            return

        # 5. Apply update
        msg.status = new_status

        if new_status == "delivered":
            # Use event timestamp if parseable, else fall back to now(UTC).
            # Telnyx does not send a dedicated delivered_at field in the webhook;
            # the event is fired immediately on delivery so now(UTC) is accurate enough.
            msg.delivered_at = datetime.now(UTC)

        if has_errors and new_status == "failed":
            # Log each error code for visibility. No schema column exists for this yet.
            for err in errors:
                code = err.get("code", "unknown")
                detail = err.get("detail") or err.get("title", "")
                logger.warning(
                    "DLC-B5: SMS delivery failure — carrier_message_id=%r code=%r detail=%r",
                    carrier_message_id,
                    code,
                    detail,
                )
            # TODO(P2/DLC): persist delivery_error_code
            # A future delivery_error_code column on customer_communication_message
            # would allow the UI to surface the specific carrier error (e.g. 40010
            # = not 10DLC registered) so the owner can act on it. No migration today.

        db.add(msg)
        db.commit()
        logger.info(
            "DLC-B5: reconciled carrier_message_id=%r → status=%r",
            carrier_message_id,
            new_status,
        )

    except Exception as exc:
        db.rollback()
        logger.error(
            "DLC-B5: error processing delivery-status webhook: %s", exc, exc_info=True
        )
    finally:
        db.close()


def _process_inbound_sms(
    raw_payload: bytes,
    db_session_factory,
) -> None:
    """
    Background task: route an inbound SMS after signature has been verified.
    Opens its own DB session (separate from the request-scoped session).
    """
    from app.models.crm import Customer
    from services.customer_communication_threading import (
        handle_sms_help,
        handle_sms_opt_in,
        handle_sms_opt_out,
        route_inbound_message,
    )
    from services.sms_carrier import get_sms_carrier

    db: Session = next(db_session_factory())

    try:
        carrier = get_sms_carrier()
        inbound = carrier.parse_inbound_webhook(raw_payload)

        # Find customer by from_number (mobile_phone) within the tenant
        # We match on to_number → tenant_phone_number → tenant_id
        # then find a customer.mobile_phone matching from_number
        customer = db.exec(
            select(Customer).where(Customer.mobile_phone == inbound.from_number)
        ).first()

        customer_id = customer.id if customer else None

        # SIGNUP-C / Pathway C: also resolve an owner user_endpoint (channel=sms)
        # by the inbound from_number. Owner resolution is an ADDITIONAL match —
        # the customer path (Pathway B) below stays intact. An owner number will
        # not normally match a customer row, so the two paths are disjoint in
        # practice; if both match, the customer path takes precedence (existing
        # behavior preserved).
        owner_endpoint = (
            _resolve_owner_sms_endpoint(db, inbound.from_number)
            if not customer_id
            else None
        )

        # TCPA: check for STOP keywords first
        if _is_stop_keyword(inbound.body):
            if customer_id:
                handle_sms_opt_out(db, customer_id, inbound)
            elif owner_endpoint is not None:
                _handle_owner_opt_out(db, owner_endpoint, inbound)
            else:
                logger.warning(
                    f"STOP from unknown number {inbound.from_number} — no customer or owner matched"
                )
            return

        # TCPA: check for HELP keywords — send DLC-spec auto-reply
        if _is_help_keyword(inbound.body):
            if owner_endpoint is not None:
                # Pathway C owner HELP reply (platform-sender strings).
                _handle_owner_help(db, inbound)
            else:
                # Pathway B customer HELP reply (existing behavior).
                handle_sms_help(inbound, db=db)
            return

        # TCPA: check for opt-in keywords
        if _is_optin_keyword(inbound.body):
            if customer_id:
                handle_sms_opt_in(db, customer_id, inbound)
            elif owner_endpoint is not None:
                _handle_owner_opt_in(db, owner_endpoint, inbound)
            else:
                logger.warning(
                    f"START from unknown number {inbound.from_number} — no customer or owner matched"
                )
            return

        # Regular inbound message — route to thread
        # Resolve tenant_id from tenant_phone_number.phone_number matching inbound.to_number
        from app.models.sms import TenantPhoneNumber

        tenant_phone = db.exec(
            select(TenantPhoneNumber).where(
                TenantPhoneNumber.phone_number == inbound.to_number,
                TenantPhoneNumber.status == "active",
            )
        ).first()

        if not tenant_phone:
            logger.warning(
                f"Inbound SMS to unknown number {inbound.to_number} — discarding"
            )
            return

        route_inbound_message(db, inbound, tenant_phone.tenant_id)

    except Exception as exc:
        db.rollback()
        logger.error(f"Error processing inbound SMS: {exc}", exc_info=True)
    finally:
        db.close()


@router.post(
    "/sms/telnyx-inbound",
    summary="Telnyx inbound SMS webhook receiver",
    # Public endpoint — no JWT; authenticated by Telnyx public-key signature verification.
    # Visible in /docs for dev/QA parity with QB and Stripe webhook endpoints.
    # /docs is disabled entirely in production (ENVIRONMENT=production → docs_url=None).
)
async def telnyx_inbound_sms(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Receive inbound SMS events from Telnyx.

    Auth: Public (no JWT). Authenticated via Telnyx public-key webhook signature.
    Returns: {"status": "received"} — always 200 after signature passes (Telnyx retries on non-2xx).
    Returns: 401 on signature failure.

    Processing is dispatched to BackgroundTasks to return < 5s to Telnyx.
    """
    # Step 1: Capture raw body BEFORE any parsing (required for signature verification)
    # ALPHA-FIX-1: Telnyx edge may drop the connection mid-body (seen on the pre-release AWS environment as
    # ASGI ExceptionGroup noise). Catch ClientDisconnect and return 400 so Telnyx
    # retries on a fresh connection — never surface as an unhandled 500. This is
    # pre-signature-verification; a body we could not read cannot be processed.
    try:
        payload_bytes = await request.body()
    except ClientDisconnect:
        logger.info("Telnyx inbound webhook: client disconnected before body read")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "type": "https://errors.pilotfortrades.com/validation-error",
                "title": "Validation Error",
                "status": 400,
                "detail": "Request body could not be read (client disconnected).",
            },
        ) from None

    # Step 2: Verify Telnyx webhook signature.
    # Pass the full headers dict — the Telnyx v4 SDK (standardwebhooks) requires
    # telnyx-signature-ed25519, telnyx-timestamp, AND telnyx-nonce in one call.
    # Extracting only two headers caused "Missing required headers" (FIND-DLC-B4-FIX).
    from services.sms_carrier import get_sms_carrier

    all_headers = dict(request.headers)
    carrier = get_sms_carrier()
    if not carrier.verify_webhook_signature(payload_bytes, all_headers):
        logger.warning(
            "Invalid Telnyx webhook signature from %s",
            request.client.host if request.client else "unknown",
        )
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    # Step 3: Route by event_type.
    #   message.received   → _process_inbound_sms (inbound SMS routing)
    #   message.sent       → _process_delivery_status (DLC-B5: delivery reconciliation)
    #   message.finalized  → _process_delivery_status (DLC-B5: delivery reconciliation)
    #   10dlc.* / unknown  → debug log, 200 ack (no processing needed)
    #
    # All verified events return 200. Telnyx retries on non-2xx so we must never
    # return 4xx/5xx for events we choose not to process.
    import json as _json

    try:
        _event_body = _json.loads(payload_bytes)
        event_type = _event_body.get("data", {}).get("event_type", "")
    except Exception:
        event_type = ""

    from core.db import get_db as _get_db

    if event_type == "message.received":
        background_tasks.add_task(_process_inbound_sms, payload_bytes, _get_db)
    elif event_type in ("message.sent", "message.finalized"):
        # DLC-B5: reconcile delivery status for outbound rows.
        background_tasks.add_task(_process_delivery_status, payload_bytes, _get_db)
    else:
        logger.debug(
            "Telnyx webhook event_type=%r — acknowledged, no processing needed",
            event_type,
        )

    return {"status": "received"}
