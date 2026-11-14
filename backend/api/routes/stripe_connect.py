"""
STRIPE-CONNECT-1 — Stripe Connect (Express) Account Links endpoints.

Allows tenants to connect their own Stripe accounts so customers can pay
invoices directly to the contractor (not Pilot's platform account).

Architecture: **Express accounts via Account Links** (ADR-0019, 2026-08-28).
  - The platform creates an Express connected account for the contractor via
    ``stripe.Account.create(type="express", ...)`` with explicit capability
    requests (``card_payments``, ``transfers`` — Express requires them).
  - Stripe hosts the onboarding UI (KYC, payouts, 1099s) via Account Links —
    NOT OAuth 2.0 / ``ca_`` client ID, NOT Custom (Pilot never hosts KYC UI).
  - Charges are **direct charges** on the connected account
    (``stripe_account=``); the contractor pays Stripe fees; no platform-fee
    model in MVP (Phase 1.5 decision).
  - STRIPE_CONNECT_PLATFORM_KEY used for Connect API calls.
  - STRIPE_SECRET_KEY used for Pilot's own subscription billing (unchanged).

Endpoints:
  GET    /api/v1/settings/billing/stripe-connect/status   — connection status
  POST   /api/v1/settings/billing/stripe-connect/onboard  — generate Account Link URL
  DELETE /api/v1/settings/billing/stripe-connect          — disconnect account

GET /status requires settings.tenant.write permission (owner + operator roles).
POST /onboard + DELETE require settings.tenant.write **+ owner-role guard**
(STRIPE-CONNECT-1 A4 — connect management is owner-only).
/test variants bypass JWT for dev/test environments.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from api.schemas.schemas import (
    StripeConnectDisconnectResponse,
    StripeConnectOnboardResponse,
    StripeConnectStatusResponse,
)
from app.models.core import Tenant
from core.auth import AuthenticatedUser
from core.db import get_db, set_audit_context_sync
from core.permissions import require_permission
from core.test_context import TestUserContext, get_test_context

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _require_owner_role(user_context) -> None:
    """STRIPE-CONNECT-1 A4: inline owner-role guard.

    Connect management (onboard + disconnect) is owner-only. The house
    pattern is an inline ``role_code == "owner"`` check (roles.py /
    reports.py precedent — design §G Q5). Non-owners get 403 RFC 7807.

    This is the deliberate 403 exception (design §D note): the resource is
    known-visible to the caller's role class; UUID enumeration is N/A.
    """
    role_code = getattr(user_context, "role_code", None)
    if role_code != "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "type": "https://errors.pilotfortrades.com/forbidden",
                "title": "Owner role required",
                "status": 403,
                "detail": (
                    "Stripe Connect management is restricted to the tenant owner role."
                ),
            },
        )


def _get_stripe_connect_client():
    """Return a StripeClient configured with the Connect platform key.

    PLP-FIX-6: establishes the house StripeClient pattern (v1 namespace).
    Key precedence UNCHANGED: STRIPE_CONNECT_PLATFORM_KEY → STRIPE_SECRET_KEY.
    No missing-key guard existed before; none is added — the SDK raises on
    use, exactly as the module-level mutation did.
    """
    import stripe

    from core.config import settings as cfg

    stripe_key = getattr(cfg, "STRIPE_CONNECT_PLATFORM_KEY", None) or getattr(
        cfg, "STRIPE_SECRET_KEY", None
    )
    return stripe.StripeClient(api_key=stripe_key)


def _get_status_impl(
    db: Session,
    tenant_id,
) -> StripeConnectStatusResponse:
    """Shared logic for GET /stripe-connect/status."""
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

    if not tenant.stripe_connect_account_id:
        return StripeConnectStatusResponse(connected=False)

    try:
        client = _get_stripe_connect_client()
        account = client.v1.accounts.retrieve(tenant.stripe_connect_account_id)
        # PLP-FIX-6: StripeObject is not a dict in stripe-python v12+.
        # Convert ONCE via .to_dict() (stripe_bootstrap.py house pattern),
        # then all dict-style reads are safe.
        account_dict = account.to_dict()
        account_name = (account_dict.get("business_profile") or {}).get("name") or (
            account_dict.get("settings") or {}
        ).get("dashboard", {}).get("display_name")
        charges_enabled = account_dict.get("charges_enabled", False)
        payouts_enabled = account_dict.get("payouts_enabled", False)

        # STRIPE-CONNECT-1 A6: write-through — persist the fresh flags onto
        # the tenant so the public hot path (GET /public/invoices/{token})
        # can render card_payments_enabled without a live Stripe call.
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

        return StripeConnectStatusResponse(
            connected=True,
            account_id=account.id,
            account_name=account_name,
            charges_enabled=charges_enabled,
            payouts_enabled=payouts_enabled,
        )
    except Exception as e:
        import stripe as stripe_lib

        if isinstance(e, stripe_lib.error.PermissionError):
            # Account exists in DB but API can't access it
            return StripeConnectStatusResponse(
                connected=True,
                account_id=tenant.stripe_connect_account_id,
                charges_enabled=False,
                payouts_enabled=False,
            )
        logger.exception(
            "Stripe Connect status retrieval failed for tenant %s", tenant_id
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "type": "https://errors.pilotfortrades.com/stripe-error",
                "title": "Stripe API error",
                "status": 502,
                "detail": (
                    f"Could not retrieve Stripe account status: "
                    f"{type(e).__name__}: {e!s}"
                ),
            },
        )


def _onboard_impl(
    db: Session,
    tenant_id,
    user_id,
    user_context=None,
) -> StripeConnectOnboardResponse:
    """Shared logic for POST /stripe-connect/onboard.

    STRIPE-CONNECT-1 A4: owner-only — ``user_context`` is checked by
    ``_require_owner_role`` before any Stripe API call.
    """
    if user_context is not None:
        _require_owner_role(user_context)
    set_audit_context_sync(db, user_id=user_id)

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

    try:
        client = _get_stripe_connect_client()

        # Step 1: Create account if not yet present
        # STRIPE-CONNECT-1 / ADR-0019: Express accounts with explicit capability
        # requests (card_payments + transfers — Express requires them).
        # PLP-FIX-6: migrated to StripeClient v1 namespace (params= dict form).
        if not tenant.stripe_connect_account_id:
            account = client.v1.accounts.create(
                params={
                    "type": "express",
                    "country": "US",
                    "capabilities": {
                        "card_payments": {"requested": True},
                        "transfers": {"requested": True},
                    },
                }
            )
            tenant.stripe_connect_account_id = account.id
            tenant.updated_at = datetime.now(UTC)
            db.add(tenant)
            db.commit()
            db.refresh(tenant)

        # Step 2: Generate Account Link (expires in ~10 min — user clicks immediately)
        link = client.v1.account_links.create(
            params={
                "account": tenant.stripe_connect_account_id,
                "refresh_url": "https://app.pilotfortrades.com/settings/billing/payment-method?retry=true",
                "return_url": "https://app.pilotfortrades.com/settings/billing/payment-method?connected=true",
                "type": "account_onboarding",
            }
        )
        return StripeConnectOnboardResponse(
            account_link_url=link.url,
            expires_at=link.expires_at,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "type": "https://errors.pilotfortrades.com/stripe-error",
                "title": "Stripe API error",
                "status": 502,
                "detail": f"Could not initiate Stripe Connect onboarding: {e!s}",
            },
        )


def _disconnect_impl(
    db: Session,
    tenant_id,
    user_id,
    user_context=None,
) -> StripeConnectDisconnectResponse:
    """Shared logic for DELETE /stripe-connect.

    STRIPE-CONNECT-1 A4: owner-only — ``user_context`` is checked by
    ``_require_owner_role`` before any DB write.
    """
    if user_context is not None:
        _require_owner_role(user_context)
    set_audit_context_sync(db, user_id=user_id)

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

    tenant.stripe_connect_account_id = None
    tenant.updated_at = datetime.now(UTC)
    db.add(tenant)
    db.commit()

    return StripeConnectDisconnectResponse()


# ---------------------------------------------------------------------------
# Authenticated endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/stripe-connect/status",
    response_model=StripeConnectStatusResponse,
    summary="Get Stripe Connect account status",
    tags=["settings"],
)
def get_stripe_connect_status(
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(
        require_permission("settings.tenant.write")
    ),
) -> StripeConnectStatusResponse:
    """Return Stripe Connect account connection status for the current tenant."""
    return _get_status_impl(db, current_user.tenant_id)


@router.post(
    "/stripe-connect/onboard",
    response_model=StripeConnectOnboardResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate Stripe Account Link for onboarding",
    tags=["settings"],
)
def stripe_connect_onboard(
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(
        require_permission("settings.tenant.write")
    ),
) -> StripeConnectOnboardResponse:
    """
    Creates (or retrieves) a Stripe connected account and generates an Account Link.
    Frontend redirects browser to the returned URL — Stripe hosts the onboarding UI.

    If the tenant already has a stripe_connect_account_id (e.g., incomplete onboarding),
    skip creation and generate a new Account Link for the existing account.
    """
    return _onboard_impl(
        db, current_user.tenant_id, current_user.id, user_context=current_user
    )


@router.delete(
    "/stripe-connect",
    response_model=StripeConnectDisconnectResponse,
    summary="Disconnect Stripe connected account",
    tags=["settings"],
)
def stripe_connect_disconnect(
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(
        require_permission("settings.tenant.write")
    ),
) -> StripeConnectDisconnectResponse:
    """
    Nulls stripe_connect_account_id on the tenant record.
    Customers will see manual payment instructions on invoice pages until reconnected.
    Does NOT deauthorize the Stripe account — tenant can reconnect later.
    """
    return _disconnect_impl(
        db, current_user.tenant_id, current_user.id, user_context=current_user
    )


# ---------------------------------------------------------------------------
# /test variants (unauthenticated — DEV/QA only)
# ---------------------------------------------------------------------------


@router.get(
    "/stripe-connect/status/test",
    response_model=StripeConnectStatusResponse,
    summary="[TEST] Get Stripe Connect account status",
    tags=["settings"],
)
def get_stripe_connect_status_test(
    db: Session = Depends(get_db),
    ctx: TestUserContext = Depends(get_test_context),
) -> StripeConnectStatusResponse:
    """Test-only endpoint — bypasses JWT, uses canonical test tenant."""
    return _get_status_impl(db, ctx.tenant_id)


@router.post(
    "/stripe-connect/onboard/test",
    response_model=StripeConnectOnboardResponse,
    status_code=status.HTTP_200_OK,
    summary="[TEST] Generate Stripe Account Link for onboarding",
    tags=["settings"],
)
def stripe_connect_onboard_test(
    db: Session = Depends(get_db),
    ctx: TestUserContext = Depends(get_test_context),
) -> StripeConnectOnboardResponse:
    """Test-only endpoint — bypasses JWT, uses canonical test tenant."""
    return _onboard_impl(db, ctx.tenant_id, ctx.id, user_context=ctx)


@router.delete(
    "/stripe-connect/test",
    response_model=StripeConnectDisconnectResponse,
    summary="[TEST] Disconnect Stripe connected account",
    tags=["settings"],
)
def stripe_connect_disconnect_test(
    db: Session = Depends(get_db),
    ctx: TestUserContext = Depends(get_test_context),
) -> StripeConnectDisconnectResponse:
    """Test-only endpoint — bypasses JWT, uses canonical test tenant."""
    return _disconnect_impl(db, ctx.tenant_id, ctx.id, user_context=ctx)
