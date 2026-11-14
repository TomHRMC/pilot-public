"""
STRIPE-CONNECT-1-B2 — Billing Payment-Contact settings endpoints.

Lets the contractor enter a phone + email shown to customers on the public
invoice manual-payment panel (when card payments are not connected/enabled).
Both fields are nullable — null is a valid state meaning "not entered"; the
frontend renders a fallback line in that case (design §G Q9 — no owner-user
personal phone/email fallback by design).

Router prefix: ``/api/v1/settings/billing`` (registered in ``app/main.py``).
Full paths:
  GET   /api/v1/settings/billing/payment-contact   — hydrate the settings form
  PATCH /api/v1/settings/billing/payment-contact   — partial update

Auth: JWT required; RBAC: ``settings.tenant.write`` (owner + operator roles —
consistent with the sibling Stripe Connect endpoints; NOT owner-only).

Idempotency: the optional ``Idempotency-Key`` header is handled by the existing
``idempotency_middleware`` (core/idempotency.py) — a replay with the same header
returns the cached response with ``X-Idempotency-Replay: true``. PATCH is
naturally idempotent for identical payloads; the header protects the
mobile/offline retry path (Part A A5 precedent).

All routes are sync ``def`` (§21 — never ``async def`` with the blocking Session).
Every mutation calls ``set_audit_context_sync()`` before the first ``db.add()``.
All fetches are tenant-scoped ``select()`` (Rule 4 — ``db.get()`` banned).
RFC 7807 errors on every raise.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlmodel import Session, select

from app.models.core import Tenant
from core.auth import AuthenticatedUser
from core.db import get_db, set_audit_context_sync
from core.permissions import require_permission
from core.test_context import TestUserContext, get_test_context

logger = logging.getLogger(__name__)

router = APIRouter()


# ─────────────────────────────────────────────────────────────────────────────
# Pydantic schemas (v2)
# ─────────────────────────────────────────────────────────────────────────────


class PaymentContactResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    billing_contact_phone: str | None = None
    billing_contact_email: str | None = None


class PaymentContactUpdateRequest(BaseModel):
    billing_contact_phone: str | None = Field(default=None, max_length=32)
    billing_contact_email: EmailStr | None = None


# ─────────────────────────────────────────────────────────────────────────────
# Shared business logic (_impl — called by both auth and /test twins)
# ─────────────────────────────────────────────────────────────────────────────


def _fetch_tenant_or_404(db: Session, tenant_id) -> Tenant:
    """Tenant-scoped fetch (Rule 4 — never ``db.get()``). 404 RFC 7807 if absent."""
    tenant = db.exec(select(Tenant).where(Tenant.id == tenant_id)).first()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "type": "https://errors.pilotfortrades.com/not-found",
                "title": "Tenant not found",
                "status": 404,
                "detail": "Tenant record not found.",
            },
        )
    return tenant


def _get_payment_contact_impl(db: Session, tenant_id) -> PaymentContactResponse:
    """Shared logic for GET /payment-contact."""
    tenant = _fetch_tenant_or_404(db, tenant_id)
    return PaymentContactResponse(
        billing_contact_phone=tenant.billing_contact_phone,
        billing_contact_email=tenant.billing_contact_email,
    )


def _update_payment_contact_impl(
    db: Session,
    tenant_id,
    user_id,
    body: PaymentContactUpdateRequest,
) -> PaymentContactResponse:
    """Shared logic for PATCH /payment-contact.

    Partial-update semantics via ``model_fields_set``:
      - omitted field  → unchanged
      - explicit ``null`` → cleared (stored as None)
      - phone: stored as-entered after ``strip()``; empty-string-after-strip → None
      - email: ``EmailStr``-validated (422 RFC 7807 on invalid)
    """
    set_audit_context_sync(db, user_id=user_id)
    tenant = _fetch_tenant_or_404(db, tenant_id)

    if "billing_contact_phone" in body.model_fields_set:
        phone = body.billing_contact_phone
        if phone is not None:
            phone = phone.strip()
            if phone == "":
                phone = None
        tenant.billing_contact_phone = phone

    if "billing_contact_email" in body.model_fields_set:
        email = body.billing_contact_email
        if email is not None:
            email = email.strip()
            if email == "":
                email = None
        tenant.billing_contact_email = email

    db.add(tenant)
    db.commit()
    db.refresh(tenant)

    return PaymentContactResponse(
        billing_contact_phone=tenant.billing_contact_phone,
        billing_contact_email=tenant.billing_contact_email,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Authenticated endpoints
# ─────────────────────────────────────────────────────────────────────────────


@router.get(
    "/payment-contact",
    response_model=PaymentContactResponse,
    summary="Get billing payment-contact (phone + email)",
    tags=["settings"],
)
def get_payment_contact(
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(
        require_permission("settings.tenant.write")
    ),
) -> PaymentContactResponse:
    """Return the contractor-entered billing contact shown on the public invoice manual-payment panel."""
    return _get_payment_contact_impl(db, current_user.tenant_id)


@router.patch(
    "/payment-contact",
    response_model=PaymentContactResponse,
    summary="Update billing payment-contact (phone + email)",
    tags=["settings"],
)
def update_payment_contact(
    body: PaymentContactUpdateRequest,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(
        require_permission("settings.tenant.write")
    ),
) -> PaymentContactResponse:
    """
    Partial update of the billing contact. Omitted fields are unchanged;
    explicit ``null`` clears a field. Phone is stored as-entered (no E.164
    coercion); email is validated. The optional ``Idempotency-Key`` header is
    handled by the idempotency middleware (24h cache; replay returns the
    cached response).
    """
    return _update_payment_contact_impl(
        db, current_user.tenant_id, current_user.id, body
    )


# ─────────────────────────────────────────────────────────────────────────────
# /test variants (unauthenticated — DEV/QA only)
# ─────────────────────────────────────────────────────────────────────────────


@router.get(
    "/payment-contact/test",
    response_model=PaymentContactResponse,
    summary="[TEST] Get billing payment-contact",
    tags=["settings"],
)
def get_payment_contact_test(
    db: Session = Depends(get_db),
    ctx: TestUserContext = Depends(get_test_context),
) -> PaymentContactResponse:
    """Test-only endpoint — bypasses JWT, uses canonical test tenant."""
    return _get_payment_contact_impl(db, ctx.tenant_id)


@router.patch(
    "/payment-contact/test",
    response_model=PaymentContactResponse,
    summary="[TEST] Update billing payment-contact",
    tags=["settings"],
)
def update_payment_contact_test(
    body: PaymentContactUpdateRequest,
    db: Session = Depends(get_db),
    ctx: TestUserContext = Depends(get_test_context),
) -> PaymentContactResponse:
    """Test-only endpoint — bypasses JWT, uses canonical test tenant."""
    return _update_payment_contact_impl(db, ctx.tenant_id, ctx.id, body)
