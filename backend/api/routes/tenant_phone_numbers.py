"""
Tenant Phone Number Provisioning Routes — B11/A61
=================================================
Routes:
  POST /api/v1/tenants/{tenant_id}/phone-numbers/provision
  GET  /api/v1/tenants/{tenant_id}/phone-numbers

RBAC:
  provision — requires settings.manage
  list      — requires settings.view
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlmodel import Session, select

from app.models.sms import TenantPhoneNumber
from core.auth import AuthenticatedUser
from core.db import get_db
from core.permissions import require_permission
from core.test_context import TestUserContext, get_test_context
from services.sms_provisioning import provision_for_tenant

router = APIRouter()
logger = logging.getLogger(__name__)


# ─── Schemas ──────────────────────────────────────────────────────────────────


class ProvisionNumberRequest(BaseModel):
    area_code: str | None = None  # E.g. "512"; defaults to tenant's office area code


class TenantPhoneNumberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    phone_number_id: UUID
    phone_number: str
    area_code: str
    carrier: str
    status: str
    monthly_fee_cents: int
    provisioned_at: str | None = None


class TenantPhoneNumberListResponse(BaseModel):
    numbers: list[TenantPhoneNumberResponse]


# ─── Shared Implementation ────────────────────────────────────────────────────


def _provision_impl(
    tenant_id: UUID,
    payload: ProvisionNumberRequest,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> TenantPhoneNumberResponse:
    """Shared provisioning logic — auth-agnostic."""
    result = provision_for_tenant(
        db=db,
        tenant_id=tenant_id,
        area_code=payload.area_code,
        requested_by_user_id=user_context.id,
    )

    if not result.success:
        if result.tenant_phone_number_id is not None:
            # Already has active number
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "type": "https://pilotfortrades.com/errors/phone-number-already-provisioned",
                    "title": "Phone Number Already Provisioned",
                    "status": 409,
                    "detail": "This tenant already has an active provisioned phone number.",
                    "phone_number": result.phone_number,
                    "phone_number_id": str(result.tenant_phone_number_id),
                },
            )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "type": "https://pilotfortrades.com/errors/provisioning-failed",
                "title": "Provisioning Failed",
                "status": 503,
                "detail": result.error,
                "suggested_area_codes": result.suggested_area_codes,
            },
        )

    # Fetch the newly created record
    record = db.exec(
        select(TenantPhoneNumber).where(
            TenantPhoneNumber.id == result.tenant_phone_number_id
        )
    ).first()

    return TenantPhoneNumberResponse(
        phone_number_id=record.id,
        phone_number=record.phone_number,
        area_code=record.area_code,
        carrier=record.carrier,
        status=record.status,
        monthly_fee_cents=record.monthly_fee_cents,
        provisioned_at=record.provisioned_at.isoformat()
        if record.provisioned_at
        else None,
    )


def _list_impl(
    tenant_id: UUID,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> TenantPhoneNumberListResponse:
    """Shared listing logic — auth-agnostic."""
    numbers = db.exec(
        select(TenantPhoneNumber)
        .where(TenantPhoneNumber.tenant_id == tenant_id)
        .order_by(TenantPhoneNumber.created_at.desc())
    ).all()

    return TenantPhoneNumberListResponse(
        numbers=[
            TenantPhoneNumberResponse(
                phone_number_id=n.id,
                phone_number=n.phone_number,
                area_code=n.area_code,
                carrier=n.carrier,
                status=n.status,
                monthly_fee_cents=n.monthly_fee_cents,
                provisioned_at=n.provisioned_at.isoformat()
                if n.provisioned_at
                else None,
            )
            for n in numbers
        ]
    )


# ─── Test Endpoints (registered FIRST) ───────────────────────────────────────


@router.post(
    "/test/provision",
    response_model=TenantPhoneNumberResponse,
    status_code=status.HTTP_200_OK,
    summary="[TEST] Provision phone number — no auth",
)
def provision_number_test(
    tenant_id: UUID,
    payload: ProvisionNumberRequest,
    db: Session = Depends(get_db),
):
    """Test endpoint — no auth required. Blocked in staging/production."""
    test_context = get_test_context()
    # Override tenant_id with test tenant for safety
    return _provision_impl(test_context.tenant_id, payload, db, test_context)


@router.get(
    "/test",
    response_model=TenantPhoneNumberListResponse,
    summary="[TEST] List phone numbers — no auth",
)
def list_phone_numbers_test(
    tenant_id: UUID,
    db: Session = Depends(get_db),
):
    """Test endpoint — no auth required. Blocked in staging/production."""
    test_context = get_test_context()
    return _list_impl(test_context.tenant_id, db, test_context)


# ─── Authenticated Endpoints ──────────────────────────────────────────────────


@router.post(
    "/provision",
    response_model=TenantPhoneNumberResponse,
    status_code=status.HTTP_200_OK,
    summary="Provision a Telnyx phone number for this tenant",
)
def provision_number(
    tenant_id: UUID,
    payload: ProvisionNumberRequest,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("settings.manage")),
):
    """
    Provision a Telnyx phone number for the tenant.

    - Only one active number per tenant is allowed (returns 409 if already provisioned).
    - area_code is optional; defaults to the tenant's primary office area code.
    - On provisioning failure, returns suggested alternative area codes.
    """
    # Tenant-scoped: only the user's own tenant can be provisioned
    if current_user.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot provision a phone number for another tenant",
        )
    return _provision_impl(tenant_id, payload, db, current_user)


@router.get(
    "/",
    response_model=TenantPhoneNumberListResponse,
    summary="List all phone numbers for this tenant",
)
def list_phone_numbers(
    tenant_id: UUID,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("settings.view")),
):
    """List all phone numbers (active, released, failed) for the tenant."""
    if current_user.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot view phone numbers for another tenant",
        )
    return _list_impl(tenant_id, db, current_user)
