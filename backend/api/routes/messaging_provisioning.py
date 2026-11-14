"""
Messaging Provisioning Routes — C-B9
=====================================
POST   /api/v1/tenants/{tenant_id}/messaging/provision          — initiate provisioning (settings.manage)
POST   /api/v1/tenants/{tenant_id}/messaging/provision/test     — test endpoint (no auth)
POST   /api/v1/tenants/{tenant_id}/messaging/checkout           — create Stripe Checkout (settings.manage)
POST   /api/v1/tenants/{tenant_id}/messaging/checkout/test      — test endpoint (no auth)
POST   /api/v1/tenants/{tenant_id}/messaging/otp                — submit sole-prop OTP (settings.manage)
POST   /api/v1/tenants/{tenant_id}/messaging/otp/test           — test endpoint (no auth)
GET    /api/v1/tenants/{tenant_id}/messaging/status             — get provisioning status (settings.view)
GET    /api/v1/tenants/{tenant_id}/messaging/status/test        — test endpoint (no auth)
POST   /api/v1/tenants/{tenant_id}/messaging/retry              — retry from payment_failed (settings.manage)
POST   /api/v1/tenants/{tenant_id}/messaging/retry/test         — test endpoint (no auth)
GET    /api/v1/tenants/{tenant_id}/messaging/verticals          — proxy carrier verticals (settings.view)
GET    /api/v1/tenants/{tenant_id}/messaging/verticals/test     — test endpoint (no auth)
GET    /api/v1/tenants/{tenant_id}/messaging/available-numbers  — proxy carrier numbers (settings.view)
GET    /api/v1/tenants/{tenant_id}/messaging/available-numbers/test — test endpoint (no auth)
POST   /api/v1/tenants/{tenant_id}/messaging/assign-number      — assign selected number (settings.manage)
POST   /api/v1/tenants/{tenant_id}/messaging/assign-number/test — test endpoint (no auth)

All endpoints are tenant-scoped. Mutations use settings.manage, reads use settings.view.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, select

from api.schemas.dlc import (
    AssignNumberRequest,
    AssignNumberResponse,
    AvailableNumbersResponse,
    CheckoutResponse,
    OtpRequest,
    OtpResponse,
    ProvisioningStatusResponse,
    ProvisionRequest,
    ProvisionResponse,
    RetryResponse,
    VerticalsResponse,
)
from app.models.sms import TenantMessagingRegistration
from core.auth import AuthenticatedUser
from core.db import get_db, set_audit_context_sync
from core.permissions import require_permission
from core.test_context import TestUserContext, get_test_context
from services.messaging_checkout import create_10dlc_checkout_session
from services.messaging_provisioning import (
    assign_phone_number,
    get_provisioning_status,
    initiate_provisioning,
    submit_otp,
    transition_status,
)
from services.sms_carrier import get_sms_carrier
from services.telnyx_quoting import get_carrier_quote

router = APIRouter()


# ── Helpers ─────────────────────────────────────────────────────────────────


def _get_registration(
    db: Session, tenant_id: uuid.UUID
) -> TenantMessagingRegistration | None:
    """Load the tenant's messaging registration row."""
    return db.exec(
        select(TenantMessagingRegistration).where(
            TenantMessagingRegistration.tenant_id == tenant_id
        )
    ).first()


def _rfc7807(
    status_code: int, title: str, detail: str, type_suffix: str = ""
) -> HTTPException:
    """Build an RFC 7807 Problem Details HTTPException."""
    type_url = (
        f"https://errors.pilotfortrades.com/{type_suffix}"
        if type_suffix
        else "about:blank"
    )
    return HTTPException(
        status_code=status_code,
        detail={
            "type": type_url,
            "title": title,
            "status": status_code,
            "detail": detail,
        },
    )


# ── POST /messaging/provision ───────────────────────────────────────────────


def _provision_impl(
    payload: ProvisionRequest,
    db: Session,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
) -> ProvisionResponse:
    """Shared provisioning logic — called by both authenticated and test endpoints."""
    set_audit_context_sync(db, user_id=user_id)

    try:
        registration, quote = initiate_provisioning(
            db=db,
            tenant_id=tenant_id,
            entity_type=payload.entity_type,
            profile_data=payload.model_dump(),
            user_id=user_id,
        )
    except ValueError as exc:
        if (
            "non-retryable" in str(exc).lower()
            or "already in progress" in str(exc).lower()
        ):
            raise _rfc7807(
                status.HTTP_409_CONFLICT,
                "Provisioning conflict",
                str(exc),
                "conflict",
            ) from exc
        raise _rfc7807(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Validation error",
            str(exc),
            "validation-error",
        ) from exc

    from api.schemas.dlc import CarrierQuoteResponse

    return ProvisionResponse(
        registration_id=registration.id,
        status=registration.status,
        entity_type=registration.entity_type,
        quote=CarrierQuoteResponse(**quote),
    )


@router.post(
    "/messaging/provision/test",
    response_model=ProvisionResponse,
    status_code=status.HTTP_200_OK,
    summary="[TEST] Initiate 10DLC provisioning — no auth",
    tags=["sms"],
)
def provision_test(
    payload: ProvisionRequest,
    db: Session = Depends(get_db),
    ctx: TestUserContext = Depends(get_test_context),
):
    return _provision_impl(payload, db, ctx.tenant_id, ctx.id)


@router.post(
    "/messaging/provision",
    response_model=ProvisionResponse,
    status_code=status.HTTP_200_OK,
    summary="Initiate 10DLC provisioning",
    tags=["sms"],
)
def provision(
    payload: ProvisionRequest,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("settings.manage")),
):
    if current_user.tenant_id != current_user.tenant_id:
        raise _rfc7807(404, "Resource not found", "Tenant not found.", "not-found")
    return _provision_impl(payload, db, current_user.tenant_id, current_user.id)


# ── POST /messaging/checkout ────────────────────────────────────────────────


def _checkout_impl(
    db: Session,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
) -> CheckoutResponse:
    """Shared checkout logic — called by both authenticated and test endpoints."""
    set_audit_context_sync(db, user_id=user_id)

    registration = _get_registration(db, tenant_id)
    if not registration:
        raise _rfc7807(
            404,
            "Registration not found",
            "No messaging registration found. Run provisioning first.",
            "not-found",
        )

    if registration.status != "quoting":
        raise _rfc7807(
            status.HTTP_409_CONFLICT,
            "Invalid state",
            f"Checkout not valid in status={registration.status}. Must be in 'quoting'.",
            "conflict",
        )

    if registration.quoted_setup_cents is None:
        raise _rfc7807(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Quote not fetched",
            "quoted_setup_cents is null. Run provisioning first to fetch a quote.",
            "validation-error",
        )

    try:
        checkout_url = create_10dlc_checkout_session(db, tenant_id, registration)
    except ValueError as exc:
        raise _rfc7807(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Checkout error",
            str(exc),
            "validation-error",
        ) from exc
    except Exception as exc:
        raise _rfc7807(
            500,
            "Stripe API error",
            f"Failed to create checkout session: {exc}",
            "stripe-error",
        ) from exc

    return CheckoutResponse(
        checkout_url=checkout_url,
        checkout_session_id=registration.stripe_checkout_id or "",
    )


@router.post(
    "/messaging/checkout/test",
    response_model=CheckoutResponse,
    summary="[TEST] Create Stripe Checkout — no auth",
    tags=["sms"],
)
def checkout_test(
    db: Session = Depends(get_db),
    ctx: TestUserContext = Depends(get_test_context),
):
    return _checkout_impl(db, ctx.tenant_id, ctx.id)


@router.post(
    "/messaging/checkout",
    response_model=CheckoutResponse,
    summary="Create Stripe Checkout session for 10DLC setup",
    tags=["sms"],
)
def checkout(
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("settings.manage")),
):
    return _checkout_impl(db, current_user.tenant_id, current_user.id)


# ── POST /messaging/otp ─────────────────────────────────────────────────────


def _otp_impl(
    payload: OtpRequest,
    db: Session,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
) -> OtpResponse:
    """Shared OTP submission logic."""
    set_audit_context_sync(db, user_id=user_id)

    try:
        new_status = submit_otp(db, tenant_id, payload.otp_code)
    except ValueError as exc:
        if "not valid in status" in str(exc).lower():
            raise _rfc7807(
                status.HTTP_409_CONFLICT,
                "Invalid state",
                str(exc),
                "conflict",
            ) from exc
        raise _rfc7807(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "OTP error",
            str(exc),
            "validation-error",
        ) from exc

    return OtpResponse(status=new_status)


@router.post(
    "/messaging/otp/test",
    response_model=OtpResponse,
    summary="[TEST] Submit sole-prop OTP — no auth",
    tags=["sms"],
)
def otp_test(
    payload: OtpRequest,
    db: Session = Depends(get_db),
    ctx: TestUserContext = Depends(get_test_context),
):
    return _otp_impl(payload, db, ctx.tenant_id, ctx.id)


@router.post(
    "/messaging/otp",
    response_model=OtpResponse,
    summary="Submit sole-proprietor OTP code",
    tags=["sms"],
)
def otp(
    payload: OtpRequest,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("settings.manage")),
):
    return _otp_impl(payload, db, current_user.tenant_id, current_user.id)


# ── GET /messaging/status ───────────────────────────────────────────────────


def _status_impl(db: Session, tenant_id: uuid.UUID) -> ProvisioningStatusResponse:
    """Shared status logic."""
    try:
        status_dict = get_provisioning_status(db, tenant_id)
    except ValueError as exc:
        raise _rfc7807(
            404,
            "Registration not found",
            str(exc),
            "not-found",
        ) from exc

    return ProvisioningStatusResponse(**status_dict)


@router.get(
    "/messaging/status/test",
    response_model=ProvisioningStatusResponse,
    summary="[TEST] Get provisioning status — no auth",
    tags=["sms"],
)
def status_test(
    db: Session = Depends(get_db),
    ctx: TestUserContext = Depends(get_test_context),
):
    return _status_impl(db, ctx.tenant_id)


@router.get(
    "/messaging/status",
    response_model=ProvisioningStatusResponse,
    summary="Get 10DLC provisioning status",
    tags=["sms"],
)
def get_status(
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("settings.view")),
):
    return _status_impl(db, current_user.tenant_id)


# ── POST /messaging/retry ───────────────────────────────────────────────────


def _retry_impl(
    db: Session,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
) -> RetryResponse:
    """Shared retry logic — retry from payment_failed back to quoting."""
    set_audit_context_sync(db, user_id=user_id)

    registration = _get_registration(db, tenant_id)
    if not registration:
        raise _rfc7807(
            404,
            "Registration not found",
            "No messaging registration found.",
            "not-found",
        )

    if registration.status != "payment_failed":
        raise _rfc7807(
            status.HTTP_409_CONFLICT,
            "Invalid state",
            f"Retry not valid in status={registration.status}. Must be in 'payment_failed'.",
            "conflict",
        )

    # Transition back to quoting and re-fetch quote
    transition_status(db, registration, "quoting", user_id=user_id)
    quote = get_carrier_quote(db, registration.entity_type)
    registration.quoted_setup_cents = quote["setup_total_millicents"] // 1000
    registration.quoted_monthly_cents = quote["recurring_monthly_millicents"] // 1000
    db.add(registration)
    db.commit()
    db.refresh(registration)

    from api.schemas.dlc import CarrierQuoteResponse

    return RetryResponse(
        status=registration.status,
        quote=CarrierQuoteResponse(**quote),
    )


@router.post(
    "/messaging/retry/test",
    response_model=RetryResponse,
    summary="[TEST] Retry from payment_failed — no auth",
    tags=["sms"],
)
def retry_test(
    db: Session = Depends(get_db),
    ctx: TestUserContext = Depends(get_test_context),
):
    return _retry_impl(db, ctx.tenant_id, ctx.id)


@router.post(
    "/messaging/retry",
    response_model=RetryResponse,
    summary="Retry provisioning from payment_failed",
    tags=["sms"],
)
def retry(
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("settings.manage")),
):
    return _retry_impl(db, current_user.tenant_id, current_user.id)


# ── GET /messaging/verticals ────────────────────────────────────────────────


def _verticals_impl() -> VerticalsResponse:
    """Shared verticals logic — proxies carrier verticals enum."""
    carrier = get_sms_carrier()
    verticals = carrier.get_verticals()
    return VerticalsResponse(verticals=verticals)


@router.get(
    "/messaging/verticals/test",
    response_model=VerticalsResponse,
    summary="[TEST] Get carrier verticals — no auth",
    tags=["sms"],
)
def verticals_test(
    db: Session = Depends(get_db),
    ctx: TestUserContext = Depends(get_test_context),
):
    return _verticals_impl()


@router.get(
    "/messaging/verticals",
    response_model=VerticalsResponse,
    summary="Get carrier business verticals",
    tags=["sms"],
)
def verticals(
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("settings.view")),
):
    return _verticals_impl()


# ── GET /messaging/available-numbers ────────────────────────────────────────


def _available_numbers_impl(
    area_code: str, limit: int = 10
) -> AvailableNumbersResponse:
    """Shared available numbers logic — proxies carrier available numbers."""
    # Validate area code format (3 digits)
    if not area_code or len(area_code) != 3 or not area_code.isdigit():
        raise _rfc7807(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Invalid area code",
            "area_code must be a 3-digit US area code.",
            "validation-error",
        )

    carrier = get_sms_carrier()
    try:
        numbers = carrier.list_available_numbers(area_code, limit=limit)
    except Exception as exc:
        raise _rfc7807(
            502,
            "Carrier API error",
            f"Failed to fetch available numbers: {exc}",
            "carrier-error",
        ) from exc

    from api.schemas.dlc import AvailablePhoneNumber

    return AvailableNumbersResponse(
        numbers=[AvailablePhoneNumber(**n) for n in numbers]
    )


@router.get(
    "/messaging/available-numbers/test",
    response_model=AvailableNumbersResponse,
    summary="[TEST] Get available phone numbers — no auth",
    tags=["sms"],
)
def available_numbers_test(
    area_code: str = Query(..., description="3-digit US area code"),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    ctx: TestUserContext = Depends(get_test_context),
):
    return _available_numbers_impl(area_code, limit)


@router.get(
    "/messaging/available-numbers",
    response_model=AvailableNumbersResponse,
    summary="Get available phone numbers for an area code",
    tags=["sms"],
)
def available_numbers(
    area_code: str = Query(..., description="3-digit US area code"),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("settings.view")),
):
    return _available_numbers_impl(area_code, limit)


# ── POST /messaging/assign-number ───────────────────────────────────────────


def _assign_number_impl(
    payload: AssignNumberRequest,
    db: Session,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
) -> AssignNumberResponse:
    """Shared assign number logic."""
    set_audit_context_sync(db, user_id=user_id)

    try:
        assigned = assign_phone_number(db, tenant_id, payload.phone_number, user_id)
    except ValueError as exc:
        if "not valid in status" in str(exc).lower():
            raise _rfc7807(
                status.HTTP_409_CONFLICT,
                "Invalid state",
                str(exc),
                "conflict",
            ) from exc
        raise _rfc7807(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Assignment error",
            str(exc),
            "validation-error",
        ) from exc
    except Exception as exc:
        raise _rfc7807(
            502,
            "Carrier API error",
            f"Failed to assign phone number: {exc}",
            "carrier-error",
        ) from exc

    return AssignNumberResponse(status="active", telnyx_phone_number=assigned)


@router.post(
    "/messaging/assign-number/test",
    response_model=AssignNumberResponse,
    summary="[TEST] Assign phone number — no auth",
    tags=["sms"],
)
def assign_number_test(
    payload: AssignNumberRequest,
    db: Session = Depends(get_db),
    ctx: TestUserContext = Depends(get_test_context),
):
    return _assign_number_impl(payload, db, ctx.tenant_id, ctx.id)


@router.post(
    "/messaging/assign-number",
    response_model=AssignNumberResponse,
    summary="Assign selected phone number to campaign",
    tags=["sms"],
)
def assign_number(
    payload: AssignNumberRequest,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("settings.manage")),
):
    return _assign_number_impl(payload, db, current_user.tenant_id, current_user.id)
