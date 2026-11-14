"""
Messaging Quote Routes — C-B8
=============================
GET  /api/v1/tenants/{tenant_id}/messaging/quote       — get carrier quote (settings.view)
GET  /api/v1/tenants/{tenant_id}/messaging/quote/test  — test endpoint (no auth)

Returns the itemized 10DLC carrier cost quote for the tenant's entity type.
Reads the tenant's entity_type from tenant_messaging_registration (C-B2).
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from api.schemas.dlc import CarrierQuoteResponse
from app.models.sms import TenantMessagingRegistration
from core.auth import AuthenticatedUser
from core.db import get_db
from core.permissions import require_permission
from core.test_context import TestUserContext, get_test_context
from services.telnyx_quoting import get_carrier_quote

router = APIRouter()


def _resolve_entity_type(db: Session, tenant_id: uuid.UUID) -> str | None:
    """
    Load the tenant's entity_type from tenant_messaging_registration.
    Returns None if no registration row exists yet.
    """
    reg = db.exec(
        select(TenantMessagingRegistration).where(
            TenantMessagingRegistration.tenant_id == tenant_id
        )
    ).first()
    if reg:
        return reg.entity_type
    return None


def _get_quote_impl(db: Session, tenant_id: uuid.UUID) -> CarrierQuoteResponse:
    entity_type = _resolve_entity_type(db, tenant_id)
    if not entity_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "type": "https://errors.pilotfortrades.com/not-found",
                "title": "Entity type not configured",
                "status": 404,
                "detail": "No messaging registration found for this tenant. "
                "Set the entity type before requesting a quote.",
            },
        )
    quote = get_carrier_quote(db, entity_type)
    return CarrierQuoteResponse(**quote)


# ── TEST ENDPOINT FIRST (per §8.2 dual-endpoint pattern) ───────────────────


@router.get(
    "/messaging/quote/test",
    response_model=CarrierQuoteResponse,
    summary="[TEST] Get carrier quote — no auth",
    tags=["sms"],
)
def get_messaging_quote_test(
    tenant_id: uuid.UUID,
    db: Session = Depends(get_db),
    ctx: TestUserContext = Depends(get_test_context),
):
    return _get_quote_impl(db, ctx.tenant_id)


# ── AUTHENTICATED ENDPOINT ──────────────────────────────────────────────────


@router.get(
    "/messaging/quote",
    response_model=CarrierQuoteResponse,
    summary="Get 10DLC carrier cost quote",
    tags=["sms"],
)
def get_messaging_quote(
    tenant_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("settings.view")),
):
    # Tenant-scoped: ensure the path tenant_id matches the authenticated user's tenant
    if tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "type": "https://errors.pilotfortrades.com/not-found",
                "title": "Resource not found",
                "status": 404,
                "detail": "No messaging quote found for this tenant.",
            },
        )
    return _get_quote_impl(db, current_user.tenant_id)
