"""
B14/A76 — Stripe Webhook Handler.
POST /api/v1/webhooks/stripe

STRIPE-CONNECT-1 (A3) — Connect Webhook Handler.
POST /api/v1/webhooks/stripe-connect

Security: Stripe Signature verified on raw body BEFORE parsing (skipped if the webhook secret is unset — Known Limitations #28).
Idempotency: event_id checked against stripe_webhook_event_processed (dedup table).
Response: Returns 200 immediately; processing is async via BackgroundTasks.

NOTE: No /test endpoint per design doc §D — webhook signatures cannot be faked
in the test endpoint pattern; tests use MockStripeWebhook fixture instead.
"""

import json
import logging
from datetime import UTC, datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from sqlmodel import Session, select

from app.models.billing import StripeWebhookEventProcessed
from core.config import settings
from core.db import get_db

router = APIRouter()
logger = logging.getLogger(__name__)


def _verify_stripe_signature(request: Request, payload_bytes: bytes) -> None:
    """
    Raises stripe.error.SignatureVerificationError if invalid.
    Per §19.3 Stripe-specific pattern.
    """
    import stripe

    stripe.api_key = settings.STRIPE_SECRET_KEY
    sig_header = request.headers.get("Stripe-Signature", "")

    if not settings.STRIPE_WEBHOOK_SECRET:
        # In dev without webhook secret configured — allow but log warning
        logger.warning(
            "STRIPE_WEBHOOK_SECRET not configured — skipping signature verification"
        )
        return

    stripe.Webhook.construct_event(
        payload_bytes, sig_header, settings.STRIPE_WEBHOOK_SECRET
    )


@router.post("/stripe")
async def stripe_webhook_handler(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Stripe webhook receiver.

    Security: Stripe Signature verified on raw body.
    Idempotency: dedup check against stripe_webhook_event_processed.
    Response: Returns 200 immediately.
    """
    # Step 1: Get raw body before any parsing
    payload_bytes = await request.body()

    # Step 2: Verify Stripe signature
    try:
        _verify_stripe_signature(request, payload_bytes)
    except Exception as e:
        logger.warning(f"Invalid Stripe signature: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Stripe signature",
        )

    # Step 3: Parse payload
    try:
        payload = json.loads(payload_bytes.decode("utf-8"))
    except Exception as e:
        logger.error(f"Failed to parse Stripe webhook JSON: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload",
        )

    event_id = payload.get("id")
    event_type = payload.get("type", "unknown")

    if not event_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing event ID",
        )

    # Step 4: Idempotency — dedup check
    existing = db.exec(
        select(StripeWebhookEventProcessed).where(
            StripeWebhookEventProcessed.event_id == event_id
        )
    ).first()

    if existing:
        logger.info(f"Stripe webhook duplicate {event_id} — already processed")
        return {"status": "duplicate", "event_id": event_id}

    # Step 5: Mark as processed (atomic with processing)
    dedup_record = StripeWebhookEventProcessed(
        event_id=event_id,
        processed_at=datetime.now(UTC),
        event_type=event_type,
    )
    db.add(dedup_record)
    db.commit()

    # Step 6: Dispatch heavy processing to BackgroundTasks
    background_tasks.add_task(_process_stripe_event, event_id=event_id, payload=payload)

    # Step 7: Return 200 quickly
    logger.info(f"Stripe webhook received: {event_id} ({event_type})")
    return {"status": "received", "event_id": event_id}


def _process_stripe_event(event_id: str, payload: dict) -> None:
    """
    Process Stripe event in the background.
    Called by BackgroundTasks — imports db here to get a fresh session.
    """
    from core.db import get_db
    from services.stripe_subscriptions import (
        handle_checkout_session_completed,
        handle_invoice_paid,
        handle_invoice_payment_failed,
        handle_payment_method_attached,
        handle_subscription_created,
        handle_subscription_deleted,
        handle_subscription_paused,
        handle_subscription_resumed,
        handle_subscription_schedule_updated,
        handle_subscription_trial_will_end,
    )

    db = next(get_db())

    try:
        event_type = payload.get("type", "")

        if event_type == "customer.subscription.created":
            handle_subscription_created(db, payload)
        elif event_type == "customer.subscription.updated":
            # Handle plan changes — same logic as created for MVP
            handle_subscription_created(db, payload)
        elif event_type == "invoice.payment_failed":
            handle_invoice_payment_failed(db, payload)
        elif event_type == "payment_intent.succeeded":
            # B15/A81: Customer-initiated invoice payment via public link
            from services.stripe_payment_intents import handle_payment_intent_succeeded

            handle_payment_intent_succeeded(db, payload)
        elif event_type == "payment_intent.payment_failed":
            # B15/A81: Customer payment failed — notify tenant
            from services.stripe_payment_intents import handle_payment_intent_failed

            handle_payment_intent_failed(db, payload)
        elif event_type == "subscription_schedule.updated":
            handle_subscription_schedule_updated(db, payload)
        elif event_type in ("charge.refunded", "refund.created"):
            # SD-05: Track refund on the payment row
            _handle_refund_event(db, payload)
        # C-B4 — Charter subscription lifecycle events
        elif event_type == "customer.subscription.trial_will_end":
            handle_subscription_trial_will_end(db, payload)
        elif event_type == "customer.subscription.paused":
            handle_subscription_paused(db, payload)
        elif event_type == "customer.subscription.resumed":
            handle_subscription_resumed(db, payload)
        elif event_type == "customer.subscription.deleted":
            handle_subscription_deleted(db, payload)
        elif event_type == "invoice.paid":
            handle_invoice_paid(db, payload)
        elif event_type == "checkout.session.completed":
            handle_checkout_session_completed(db, payload)
        elif event_type == "payment_method.attached":
            handle_payment_method_attached(db, payload)
        else:
            logger.debug(f"Stripe event {event_type} — no handler registered")

    except Exception as e:
        logger.error(f"Error processing Stripe event {event_id}: {e}")
        # Don't re-raise — BackgroundTask failures are logged, not surfaced to Stripe
    finally:
        db.close()


def _handle_refund_event(db, payload: dict) -> None:
    """
    SD-2: Handle charge.refunded / refund.created Stripe events.
    Creates a negative-amount payment row (replaces SD-05 column-based approach).

    Delegates to services.stripe_subscriptions._handle_refund_event which expects
    event_data = {"object": <charge_dict>}.
    """
    from services.stripe_subscriptions import _handle_refund_event as _svc_handle_refund

    event_data = payload.get("data", {})
    _svc_handle_refund(db, event_data)


# ─────────────────────────────────────────────────────────────────────────────
# STRIPE-CONNECT-1 (A3) — Connect Webhook Endpoint + Handlers
# ─────────────────────────────────────────────────────────────────────────────


def _verify_connect_signature(request: Request, payload_bytes: bytes) -> None:
    """Verify the Stripe Connect webhook signature.

    Uses STRIPE_CONNECT_WEBHOOK_SECRET (falls back to skipping verification in
    dev when the secret is unset — same posture as the platform endpoint).
    """
    import stripe

    stripe.api_key = (
        getattr(settings, "STRIPE_CONNECT_PLATFORM_KEY", None)
        or settings.STRIPE_SECRET_KEY
    )
    sig_header = request.headers.get("Stripe-Signature", "")

    connect_secret = getattr(settings, "STRIPE_CONNECT_WEBHOOK_SECRET", None)
    if not connect_secret:
        logger.warning(
            "STRIPE_CONNECT_WEBHOOK_SECRET not configured — "
            "skipping Connect signature verification"
        )
        return

    stripe.Webhook.construct_event(payload_bytes, sig_header, connect_secret)


@router.post("/stripe-connect")
async def stripe_connect_webhook_handler(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    STRIPE-CONNECT-1: Connect-account webhook receiver.

    Receives connected-account events (direct charges, account lifecycle,
    disputes). Verifies with STRIPE_CONNECT_WEBHOOK_SECRET; resolves the tenant
    via event['account'] → tenant.stripe_connect_account_id; dedups via
    stripe_webhook_event_processed (shared with the platform endpoint — event
    IDs are globally unique).
    """
    payload_bytes = await request.body()

    try:
        _verify_connect_signature(request, payload_bytes)
    except Exception as e:
        logger.warning(f"Invalid Stripe Connect signature: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "type": "https://errors.pilotfortrades.com/invalid-signature",
                "title": "Invalid Stripe signature",
                "status": 401,
                "detail": "Invalid Stripe Connect webhook signature.",
            },
        )

    try:
        payload = json.loads(payload_bytes.decode("utf-8"))
    except Exception as e:
        logger.error(f"Failed to parse Stripe Connect webhook JSON: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "type": "https://errors.pilotfortrades.com/invalid-payload",
                "title": "Invalid JSON payload",
                "status": 400,
                "detail": "Invalid JSON payload.",
            },
        )

    event_id = payload.get("id")
    event_type = payload.get("type", "unknown")

    if not event_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "type": "https://errors.pilotfortrades.com/invalid-payload",
                "title": "Missing event ID",
                "status": 400,
                "detail": "Missing event ID.",
            },
        )

    # Dedup — shared table with the platform endpoint
    existing = db.exec(
        select(StripeWebhookEventProcessed).where(
            StripeWebhookEventProcessed.event_id == event_id
        )
    ).first()

    if existing:
        logger.info(f"Stripe Connect webhook duplicate {event_id} — already processed")
        return {"status": "duplicate", "event_id": event_id}

    dedup_record = StripeWebhookEventProcessed(
        event_id=event_id,
        processed_at=datetime.now(UTC),
        event_type=event_type,
    )
    db.add(dedup_record)
    db.commit()

    # Dispatch heavy processing to BackgroundTasks (sync handler in a thread)
    background_tasks.add_task(
        _process_connect_event, event_id=event_id, payload=payload
    )

    logger.info(f"Stripe Connect webhook received: {event_id} ({event_type})")
    return {"status": "received", "event_id": event_id}


def _process_connect_event(event_id: str, payload: dict) -> None:
    """
    Process a Stripe Connect event in the background.

    Tenant resolution: event['account'] → tenant.stripe_connect_account_id
    (tenant-scoped select, never db.get — Rule 4). Unknown account → logged +
    200 (Stripe must never see a 5xx for an unmapped account).
    """
    from core.db import get_db

    db = next(get_db())

    try:
        event_type = payload.get("type", "")
        account_id = payload.get("account")

        # payment_intent.* events on connected accounts: delegate to the
        # existing handlers (they resolve via PI metadata and are idempotent).
        if event_type == "payment_intent.succeeded":
            from services.stripe_payment_intents import handle_payment_intent_succeeded

            handle_payment_intent_succeeded(db, payload)
            return
        if event_type == "payment_intent.payment_failed":
            from services.stripe_payment_intents import handle_payment_intent_failed

            handle_payment_intent_failed(db, payload)
            return

        # Account-scoped events: resolve the tenant
        tenant = None
        if account_id:
            from app.models.core import Tenant

            tenant = db.exec(
                select(Tenant).where(Tenant.stripe_connect_account_id == account_id)
            ).first()

        if tenant is None and account_id:
            logger.warning(
                f"Stripe Connect event {event_id} ({event_type}) — "
                f"no tenant found for account {account_id}; ignoring"
            )
            return

        if event_type == "account.updated":
            handle_connect_account_updated(db, payload, tenant)
        elif event_type == "account.application.deauthorized":
            handle_connect_deauthorized(db, payload, tenant)
        elif event_type == "charge.dispute.created":
            handle_connect_dispute(db, payload, tenant, closed=False)
        elif event_type == "charge.dispute.closed":
            handle_connect_dispute(db, payload, tenant, closed=True)
        else:
            logger.debug(f"Stripe Connect event {event_type} — no handler registered")

    except Exception as e:
        logger.error(f"Error processing Stripe Connect event {event_id}: {e}")
    finally:
        db.close()


def handle_connect_account_updated(db: Session, payload: dict, tenant) -> None:
    """Persist charges_enabled / payouts_enabled onto the tenant (idempotent)."""
    from datetime import UTC, datetime

    account_obj = payload.get("data", {}).get("object", {})
    charges_enabled = account_obj.get("charges_enabled", False)
    payouts_enabled = account_obj.get("payouts_enabled", False)

    if (
        tenant.stripe_connect_charges_enabled != charges_enabled
        or tenant.stripe_connect_payouts_enabled != payouts_enabled
    ):
        tenant.stripe_connect_charges_enabled = charges_enabled
        tenant.stripe_connect_payouts_enabled = payouts_enabled
        tenant.updated_at = datetime.now(UTC)
        db.add(tenant)
        db.commit()
        db.refresh(tenant)

    logger.info(
        f"account.updated — tenant {tenant.id} charges={charges_enabled} "
        f"payouts={payouts_enabled}"
    )


def handle_connect_deauthorized(db: Session, payload: dict, tenant) -> None:
    """Null stripe_connect_account_id + flags; enqueue disconnect notification to owner."""
    from datetime import UTC, datetime

    from services.stripe_connect_notifications import (
        enqueue_connect_disconnected_notification,
    )

    tenant.stripe_connect_account_id = None
    tenant.stripe_connect_charges_enabled = None
    tenant.stripe_connect_payouts_enabled = None
    tenant.updated_at = datetime.now(UTC)
    db.add(tenant)
    db.commit()
    db.refresh(tenant)

    # Enqueue owner notification (best-effort — never block on notification failure)
    try:
        enqueue_connect_disconnected_notification(db, tenant.id)
        db.commit()
    except Exception as e:
        logger.warning(
            f"Failed to enqueue stripe_connect_disconnected notification "
            f"for tenant {tenant.id}: {e}"
        )

    logger.info(f"account.application.deauthorized — tenant {tenant.id} disconnected")


def handle_connect_dispute(db: Session, payload: dict, tenant, *, closed: bool) -> None:
    """Enqueue stripe_dispute_opened (or closed-note) to the owner."""
    from services.stripe_connect_notifications import (
        enqueue_dispute_notification,
    )

    dispute_obj = payload.get("data", {}).get("object", {})
    amount_cents = dispute_obj.get("amount_disputed", 0)
    # Stripe amounts are in cents; format as dollars for the notification body
    amount_display = f"${amount_cents / 100:.2f}"
    respond_by = (
        dispute_obj.get("evidence_details", {}).get("due_by")
        or "the deadline in your Stripe dashboard"
    )

    try:
        enqueue_dispute_notification(
            db,
            tenant.id,
            amount_display=amount_display,
            respond_by=str(respond_by),
            closed=closed,
        )
        db.commit()
    except Exception as e:
        logger.warning(
            f"Failed to enqueue stripe_dispute_opened notification "
            f"for tenant {tenant.id}: {e}"
        )

    logger.info(
        f"charge.dispute.{'closed' if closed else 'created'} — "
        f"tenant {tenant.id} amount={amount_display}"
    )
