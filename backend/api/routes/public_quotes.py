"""
B15/A80 — Public Quote Endpoints

Routes:
  GET  /api/v1/public/quotes/{signed_token}         — view quote (no auth)
  POST /api/v1/public/quotes/{signed_token}/accept  — accept quote (no auth)
  POST /api/v1/public/quotes/{signed_token}/decline — decline quote (no auth)

Auth: Public (signed token is the credential). No Cognito JWT required.
Rate limiting: not yet applied to these routes (Known Limitations #28).
"""

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

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


class QuoteBrandingResponse(BaseModel):
    logo_url: str | None = None
    brand_color_hex: str | None = None


class PublicQuoteResponse(BaseModel):
    quote_id: str
    tenant_name: str
    customer_name: str
    quote_total_cents: int
    currency: str
    line_items: list[dict[str, Any]]
    status: str
    expires_at: str | None
    branding: QuoteBrandingResponse
    customer_acceptance_comment: str | None = None
    customer_decline_comment: str | None = None


class AcceptQuoteRequest(BaseModel):
    comment: str | None = None


class DeclineQuoteRequest(BaseModel):
    reason: str  # pricing | scope | timing | other_contractor | other
    comment: str | None = None


class AcceptQuoteResponse(BaseModel):
    status: str
    accepted_at: str


class DeclineQuoteResponse(BaseModel):
    status: str
    declined_at: str


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _resolve_link_or_401(db: Session, signed_token: str):
    """
    Verify the signed token and resolve to (QuotePublicLink, payload).
    Raises 401 (invalid sig), 410 (expired or revoked).
    """
    from app.models.quoting import QuotePublicLink

    try:
        payload = verify_signed_token(signed_token)
    except TokenExpiredError:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Link has expired")
    except TokenInvalidError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid link token"
        )

    link_id = payload.get("link_id")
    if not link_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload"
        )

    link = db.exec(
        select(QuotePublicLink).where(QuotePublicLink.id == uuid.UUID(link_id))
    ).first()

    if link is None:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Link not found")

    if link.revoked_at is not None:
        raise HTTPException(
            status_code=status.HTTP_410_GONE, detail="Link has been revoked"
        )

    return link, payload


def _get_branding(db: Session, tenant_id: uuid.UUID) -> QuoteBrandingResponse:
    from app.models.core import TenantEmailBranding

    branding = db.exec(
        select(TenantEmailBranding).where(TenantEmailBranding.tenant_id == tenant_id)
    ).first()
    if branding is None:
        return QuoteBrandingResponse()
    logo_url = None
    if branding.logo_s3_path:
        from core.config import settings as cfg

        bucket = getattr(cfg, "S3_BUCKET_NAME", None)
        if bucket:
            logo_url = f"https://{bucket}.s3.amazonaws.com/{branding.logo_s3_path}"
        else:
            logo_url = branding.logo_s3_path
    return QuoteBrandingResponse(
        logo_url=logo_url,
        brand_color_hex=branding.brand_color_hex or "#5B3FF0",
    )


# ─────────────────────────────────────────────────────────────────────────────
# GET /public/quotes/{signed_token}
# ─────────────────────────────────────────────────────────────────────────────


@router.get("/quotes/{signed_token}", response_model=PublicQuoteResponse)
def get_public_quote(
    signed_token: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Public quote view. No JWT required.
    Auth = valid HMAC-signed token.
    """
    from app.models.crm import Customer
    from app.models.quoting import Quote, QuoteLine

    link, payload = _resolve_link_or_401(db, signed_token)

    quote = db.exec(select(Quote).where(Quote.id == link.quote_id)).first()
    if quote is None or not quote.is_active:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Quote not found")

    customer = db.exec(select(Customer).where(Customer.id == quote.customer_id)).first()
    customer_name = customer.name if customer else "Customer"

    # Tenant name
    from app.models.core import Tenant

    tenant = db.exec(select(Tenant).where(Tenant.id == quote.tenant_id)).first()
    tenant_name = tenant.name if tenant else "Contractor"

    # Line items
    lines = db.exec(
        select(QuoteLine)
        .where(QuoteLine.quote_id == quote.id)
        .where(QuoteLine.is_active == True)
        .where(QuoteLine.customer_visible == True)
    ).all()
    line_items = [
        {
            "description": l.description,
            "quantity": str(l.quantity),
            "unit_price_cents": l.unit_price_cents,
            "total_cents": l.total_cents,
        }
        for l in lines
    ]

    # Derive status string from QuotePublicLink / quote status
    status_str = "sent"
    if getattr(quote, "customer_accepted_at", None):
        status_str = "accepted"
    elif getattr(quote, "customer_declined_at", None):
        status_str = "declined"
    elif link.expires_at and datetime.now(UTC) > link.expires_at:
        status_str = "expired"

    branding = _get_branding(db, quote.tenant_id)

    return PublicQuoteResponse(
        quote_id=str(quote.id),
        tenant_name=tenant_name,
        customer_name=customer_name,
        quote_total_cents=quote.total_cents,
        currency=quote.currency,
        line_items=line_items,
        status=status_str,
        expires_at=link.expires_at.isoformat() if link.expires_at else None,
        branding=branding,
        customer_acceptance_comment=getattr(quote, "customer_acceptance_comment", None),
        customer_decline_comment=getattr(quote, "customer_decline_comment", None),
    )


# ─────────────────────────────────────────────────────────────────────────────
# POST /public/quotes/{signed_token}/accept
# ─────────────────────────────────────────────────────────────────────────────


@router.post("/quotes/{signed_token}/accept", response_model=AcceptQuoteResponse)
def accept_public_quote(
    signed_token: str,
    body: AcceptQuoteRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Accept a quote via public link. No JWT required."""
    from app.models.quoting import Quote

    link, payload = _resolve_link_or_401(db, signed_token)

    quote = db.exec(select(Quote).where(Quote.id == link.quote_id)).first()
    if quote is None or not quote.is_active:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Quote not found")

    # Check idempotency — already accepted or declined
    accepted_at = getattr(quote, "customer_accepted_at", None)
    declined_at = getattr(quote, "customer_declined_at", None)
    if accepted_at:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Quote already accepted",
        )
    if declined_at:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Quote already declined",
        )

    now = datetime.now(UTC)

    # Store acceptance (A83 wires the comment fields — these are set if columns exist)
    if hasattr(quote, "customer_accepted_at"):
        quote.customer_accepted_at = now
    if hasattr(quote, "customer_acceptance_comment"):
        quote.customer_acceptance_comment = body.comment
    if hasattr(quote, "customer_email_at_action"):
        quote.customer_email_at_action = payload.get("customer_id")  # best available

    # Increment used_count
    link.used_count = (link.used_count or 0) + 1
    link.last_used_at = now

    db.add(quote)
    db.add(link)
    db.commit()

    return AcceptQuoteResponse(status="accepted", accepted_at=now.isoformat())


# ─────────────────────────────────────────────────────────────────────────────
# POST /public/quotes/{signed_token}/decline
# ─────────────────────────────────────────────────────────────────────────────

VALID_DECLINE_REASONS = {"pricing", "scope", "timing", "other_contractor", "other"}


@router.post("/quotes/{signed_token}/decline", response_model=DeclineQuoteResponse)
def decline_public_quote(
    signed_token: str,
    body: DeclineQuoteRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Decline a quote via public link. No JWT required."""
    from app.models.quoting import Quote

    if body.reason not in VALID_DECLINE_REASONS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Invalid reason. Allowed: {sorted(VALID_DECLINE_REASONS)}",
        )

    link, payload = _resolve_link_or_401(db, signed_token)

    quote = db.exec(select(Quote).where(Quote.id == link.quote_id)).first()
    if quote is None or not quote.is_active:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Quote not found")

    accepted_at = getattr(quote, "customer_accepted_at", None)
    declined_at = getattr(quote, "customer_declined_at", None)
    if accepted_at:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Quote already accepted"
        )
    if declined_at:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Quote already declined"
        )

    now = datetime.now(UTC)

    if hasattr(quote, "customer_declined_at"):
        quote.customer_declined_at = now
    if hasattr(quote, "customer_decline_reason"):
        quote.customer_decline_reason = body.reason
    if hasattr(quote, "customer_decline_comment"):
        quote.customer_decline_comment = body.comment
    if hasattr(quote, "customer_email_at_action"):
        quote.customer_email_at_action = payload.get("customer_id")

    link.used_count = (link.used_count or 0) + 1
    link.last_used_at = now

    db.add(quote)
    db.add(link)
    db.commit()

    return DeclineQuoteResponse(status="declined", declined_at=now.isoformat())
