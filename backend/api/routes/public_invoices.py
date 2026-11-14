"""
B15/A80 — Public Invoice Endpoints
B15/A81 — Stripe Payment Intent + Confirm routes (wired here)
STRIPE-CONNECT-1 (A5/A6) — Idempotency-Key header + payment-state fields

Routes:
  GET  /api/v1/public/invoices/{signed_token}                   — view invoice
  POST /api/v1/public/invoices/{signed_token}/payment-intent    — create Stripe PI (A81)
  POST /api/v1/public/invoices/{signed_token}/confirm-payment   — confirm payment (advisory)

Auth: Public (signed token is the credential). No Cognito JWT required.

STRIPE-CONNECT-1 A6: the GET response includes ``card_payments_enabled`` and
``payment_unavailable_reason`` computed from LOCAL tenant columns
(``stripe_connect_account_id``, ``stripe_connect_charges_enabled``) — never a
live Stripe call on the public hot path. The 402 guard on the POST remains the
hard backstop.
"""

import logging
import uuid
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlmodel import Session, select

from core.db import get_db
from services.public_link_signer import (
    TokenExpiredError,
    TokenInvalidError,
    verify_signed_token,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ─────────────────────────────────────────────────────────────────────────────
# Pydantic schemas
# ─────────────────────────────────────────────────────────────────────────────


class InvoiceBrandingResponse(BaseModel):
    logo_url: str | None = None
    brand_color_hex: str | None = None


class PublicInvoiceResponse(BaseModel):
    invoice_id: str
    tenant_name: str
    customer_name: str
    invoice_total_cents: int
    amount_paid_cents: int
    amount_due_cents: int
    currency: str
    line_items: list[dict[str, Any]]
    status: str  # unpaid | partial | paid
    due_date: str | None
    branding: InvoiceBrandingResponse
    # STRIPE-CONNECT-1 A6: payment-state fields computed from LOCAL tenant
    # columns — never a live Stripe call on the public hot path.
    card_payments_enabled: bool = False
    payment_unavailable_reason: Literal["not_connected", "charges_disabled"] | None = (
        None
    )
    # STRIPE-CONNECT-1-B2: contractor-entered billing contact for the
    # manual-payment panel (null = not entered — frontend renders fallback line).
    tenant_phone: str | None = None
    tenant_email: str | None = None


class PaymentIntentRequest(BaseModel):
    amount_cents: int
    comment: str | None = None


class PaymentIntentResponse(BaseModel):
    client_secret: str
    payment_intent_id: str


class ConfirmPaymentRequest(BaseModel):
    payment_intent_id: str


class ConfirmPaymentResponse(BaseModel):
    status: str  # "pending_confirmation"


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _resolve_invoice_link_or_401(db: Session, signed_token: str):
    """Verify token and return (InvoicePublicLink, payload)."""
    from app.models.billing import InvoicePublicLink

    try:
        payload = verify_signed_token(signed_token)
    except TokenExpiredError:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail={
                "type": "https://errors.pilotfortrades.com/link-expired",
                "title": "Link expired",
                "status": 410,
                "detail": "This invoice link has expired. Please ask the contractor to send a new link.",
            },
        )
    except TokenInvalidError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "type": "https://errors.pilotfortrades.com/invalid-link",
                "title": "Invalid link",
                "status": 401,
                "detail": "This invoice link is invalid. Please check the link in your email.",
            },
        )

    link_id = payload.get("link_id")
    if not link_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "type": "https://errors.pilotfortrades.com/invalid-link",
                "title": "Invalid link",
                "status": 401,
                "detail": "This invoice link is invalid. Please check the link in your email.",
            },
        )

    link = db.exec(
        select(InvoicePublicLink).where(InvoicePublicLink.id == uuid.UUID(link_id))
    ).first()
    if link is None:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail={
                "type": "https://errors.pilotfortrades.com/link-not-found",
                "title": "Link not found",
                "status": 410,
                "detail": "This invoice link could not be found. It may have been removed.",
            },
        )

    if link.revoked_at is not None or link.status == "revoked":
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail={
                "type": "https://errors.pilotfortrades.com/link-revoked",
                "title": "Link revoked",
                "status": 410,
                "detail": "This invoice link has been revoked by the contractor.",
            },
        )

    return link, payload


def _get_branding(db: Session, tenant_id: uuid.UUID) -> InvoiceBrandingResponse:
    from app.models.core import TenantEmailBranding

    branding = db.exec(
        select(TenantEmailBranding).where(TenantEmailBranding.tenant_id == tenant_id)
    ).first()
    if branding is None:
        return InvoiceBrandingResponse()
    logo_url = None
    if branding.logo_s3_path:
        from core.config import settings as cfg

        bucket = getattr(cfg, "S3_BUCKET_NAME", None)
        logo_url = (
            f"https://{bucket}.s3.amazonaws.com/{branding.logo_s3_path}"
            if bucket
            else branding.logo_s3_path
        )
    return InvoiceBrandingResponse(
        logo_url=logo_url,
        brand_color_hex=branding.brand_color_hex or "#5B3FF0",
    )


# ─────────────────────────────────────────────────────────────────────────────
# GET /public/invoices/{signed_token}
# ─────────────────────────────────────────────────────────────────────────────


@router.get("/invoices/{signed_token}", response_model=PublicInvoiceResponse)
def get_public_invoice(
    signed_token: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """Public invoice view. No JWT required."""
    from app.models.billing import Invoice, InvoiceLine, Payment
    from app.models.core import Tenant
    from app.models.crm import Customer

    link, _payload = _resolve_invoice_link_or_401(db, signed_token)

    invoice = db.exec(select(Invoice).where(Invoice.id == link.invoice_id)).first()
    if invoice is None or not invoice.is_active:
        raise HTTPException(
            status_code=status.HTTP_410_GONE, detail="Invoice not found"
        )

    customer = db.exec(
        select(Customer).where(Customer.id == invoice.customer_id)
    ).first()
    customer_name = customer.display_name if customer else "Customer"

    tenant = db.exec(select(Tenant).where(Tenant.id == invoice.tenant_id)).first()
    tenant_name = tenant.name if tenant else "Contractor"

    lines = db.exec(
        select(InvoiceLine)
        .where(InvoiceLine.invoice_id == invoice.id)
        .where(InvoiceLine.is_active == True)
    ).all()
    line_items = [
        {
            "description": line.description,
            "quantity": str(line.quantity),
            "unit_price_cents": line.unit_price_cents,
            "total_cents": line.total_cents,
        }
        for line in lines
    ]

    # Sum paid payments
    payments = db.exec(
        select(Payment)
        .where(Payment.invoice_id == invoice.id)
        .where(Payment.is_active == True)
    ).all()
    amount_paid_cents = sum(
        p.amount_cents
        for p in payments
        if p.status_id is not None  # simplified check
    )
    amount_due_cents = max(invoice.total_cents - amount_paid_cents, 0)

    if amount_paid_cents == 0:
        payment_status = "unpaid"
    elif amount_due_cents == 0:
        payment_status = "paid"
    else:
        payment_status = "partial"

    branding = _get_branding(db, invoice.tenant_id)

    # STRIPE-CONNECT-1 A6: compute payment-state from LOCAL tenant columns —
    # never a live Stripe call on the public hot path. The 402 guard on the
    # POST remains the hard backstop.
    card_payments_enabled = False
    payment_unavailable_reason: str | None = "not_connected"
    if tenant and tenant.stripe_connect_account_id:
        charges = getattr(tenant, "stripe_connect_charges_enabled", None)
        if charges is True:
            card_payments_enabled = True
            payment_unavailable_reason = None
        else:
            # charges False or NULL (unknown) — treat as disabled
            payment_unavailable_reason = "charges_disabled"

    # STRIPE-CONNECT-1-B2: populate the manual-payment panel contact fields
    # from the already-loaded tenant's local columns (None-safe; no extra
    # query, no live Stripe call, no owner-user fallback — by design §G Q9).
    tenant_phone = getattr(tenant, "billing_contact_phone", None) if tenant else None
    tenant_email = getattr(tenant, "billing_contact_email", None) if tenant else None

    return PublicInvoiceResponse(
        invoice_id=str(invoice.id),
        tenant_name=tenant_name,
        customer_name=customer_name,
        invoice_total_cents=invoice.total_cents,
        amount_paid_cents=amount_paid_cents,
        amount_due_cents=amount_due_cents,
        currency=invoice.currency,
        line_items=line_items,
        status=payment_status,
        due_date=None,  # invoice.due_date if exists
        branding=branding,
        card_payments_enabled=card_payments_enabled,
        payment_unavailable_reason=payment_unavailable_reason,
        tenant_phone=tenant_phone,
        tenant_email=tenant_email,
    )


# ─────────────────────────────────────────────────────────────────────────────
# POST /public/invoices/{signed_token}/payment-intent  (A81)
# ─────────────────────────────────────────────────────────────────────────────


@router.post(
    "/invoices/{signed_token}/payment-intent",
    response_model=PaymentIntentResponse,
)
def create_payment_intent(
    signed_token: str,
    body: PaymentIntentRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Create a Stripe Payment Intent for customer-initiated invoice payment.
    Validates: if amount differs from invoice total, comment is required.

    STRIPE-CONNECT-1 (A5): The optional ``Idempotency-Key`` header is passed
    through to the Stripe-side PI creation key so two same-amount partial
    payments create two PIs. The 24h response cache is handled by the existing
    ``idempotency_middleware`` (core/idempotency.py) — a replay with the same
    header returns the cached response with ``X-Idempotency-Replay: true``.
    A bare browser retry without the header still works (uuid4 fallback).
    """
    from app.models.billing import Invoice
    from services.stripe_payment_intents import create_payment_intent as _create_pi

    link, _payload = _resolve_invoice_link_or_401(db, signed_token)

    invoice = db.exec(select(Invoice).where(Invoice.id == link.invoice_id)).first()
    if invoice is None or not invoice.is_active:
        raise HTTPException(
            status_code=status.HTTP_410_GONE, detail="Invoice not found"
        )

    # Validate: comment required when amount differs from invoice total
    if body.amount_cents != invoice.total_cents and not body.comment:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="comment is required when payment amount differs from invoice total",
        )

    # STRIPE-CONNECT-1 (A5): pass the Idempotency-Key header through to the
    # Stripe-side key for PI uniqueness. The middleware handles the 24h
    # response cache; this just ensures the Stripe key is per-attempt.
    idempotency_key = request.headers.get("Idempotency-Key")

    try:
        result = _create_pi(
            db=db,
            invoice_id=str(invoice.id),
            amount_cents=body.amount_cents,
            customer_comment=body.comment,
            tenant_id=str(invoice.tenant_id),
            idempotency_key=idempotency_key,
        )
    except Exception as e:
        # Check for PaymentNotConfiguredError by class name to avoid circular import
        if type(e).__name__ == "PaymentNotConfiguredError":
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail={
                    "type": "https://errors.pilotfortrades.com/payment-not-configured",
                    "title": "Payment not configured",
                    "status": 402,
                    "detail": (
                        "This contractor has not connected a payment account. "
                        "Please contact them directly to arrange payment."
                    ),
                    "manual_payment": True,
                },
            )
        raise

    return PaymentIntentResponse(
        client_secret=result["client_secret"],
        payment_intent_id=result["payment_intent_id"],
    )


# ─────────────────────────────────────────────────────────────────────────────
# POST /public/invoices/{signed_token}/confirm-payment  (A81)
# ─────────────────────────────────────────────────────────────────────────────


@router.post(
    "/invoices/{signed_token}/confirm-payment",
    response_model=ConfirmPaymentResponse,
)
def confirm_payment(
    signed_token: str,
    body: ConfirmPaymentRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Advisory endpoint: customer indicates payment was submitted.
    Backend does NOT mark invoice paid until webhook fires.
    Returns 'pending_confirmation' so frontend shows "Payment processing" state.
    """
    link, _payload = _resolve_invoice_link_or_401(db, signed_token)
    # No state change here — just ack the advisory signal
    logger.info(
        f"Payment confirmation advisory received for invoice_link {link.id}, "
        f"payment_intent_id={body.payment_intent_id}"
    )
    return ConfirmPaymentResponse(status="pending_confirmation")
