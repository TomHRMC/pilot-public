"""
B14/A77 — Onboarding Checklist routes.
GET  /api/v1/tenants/{tenant_id}/onboarding/checklist
PUT  /api/v1/tenants/{tenant_id}/onboarding/checklist/skip/{item}
PUT  /api/v1/tenants/{tenant_id}/onboarding/checklist/hidden
PUT  /api/v1/tenants/{tenant_id}/onboarding/checklist/dismissed
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlmodel import Session, select

from app.models.onboarding import TenantOnboardingChecklist
from core.auth import AuthenticatedUser
from core.db import get_db, set_audit_context_sync
from core.permissions import require_permission
from core.test_context import get_test_context
from services.onboarding_service import (
    dismiss_checklist_permanently,
    ensure_checklist_exists,
    hide_checklist,
    skip_item,
    unhide_checklist,
)

router = APIRouter()


# ==================== SCHEMAS ====================


class OnboardingChecklistResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    tenant_id: UUID
    account_created: bool
    legal_accepted: bool
    tier_selected: bool
    first_customer_added: bool
    first_customer_added_at: str | None = None
    catalog_setup: bool
    catalog_setup_at: str | None = None
    quickbooks_connected: bool
    quickbooks_skipped: bool
    calendar_connected: bool
    calendar_skipped: bool
    team_invited: bool
    team_skipped: bool
    messaging_setup: bool
    checklist_hidden: bool
    checklist_dismissed_permanently: bool


class HideChecklistRequest(BaseModel):
    hidden: bool


# ==================== SHARED LOGIC ====================


def _get_checklist_impl(tenant_id: UUID, db: Session) -> OnboardingChecklistResponse:
    """Get checklist, ensuring row exists."""
    ensure_checklist_exists(db, tenant_id)

    checklist = db.exec(
        select(TenantOnboardingChecklist).where(
            TenantOnboardingChecklist.tenant_id == tenant_id
        )
    ).first()

    if not checklist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Onboarding checklist not found",
        )

    return OnboardingChecklistResponse(
        tenant_id=checklist.tenant_id,
        account_created=checklist.account_created,
        legal_accepted=checklist.legal_accepted,
        tier_selected=checklist.tier_selected,
        first_customer_added=checklist.first_customer_added,
        first_customer_added_at=(
            checklist.first_customer_added_at.isoformat()
            if checklist.first_customer_added_at
            else None
        ),
        catalog_setup=checklist.catalog_setup,
        catalog_setup_at=(
            checklist.catalog_setup_at.isoformat()
            if checklist.catalog_setup_at
            else None
        ),
        quickbooks_connected=checklist.quickbooks_connected,
        quickbooks_skipped=checklist.quickbooks_skipped,
        calendar_connected=checklist.calendar_connected,
        calendar_skipped=checklist.calendar_skipped,
        team_invited=checklist.team_invited,
        team_skipped=checklist.team_skipped,
        messaging_setup=checklist.messaging_setup,
        checklist_hidden=checklist.checklist_hidden,
        checklist_dismissed_permanently=checklist.checklist_dismissed_permanently,
    )


# ==================== TEST ENDPOINTS ====================


@router.get(
    "/{tenant_id}/onboarding/checklist/test",
    response_model=OnboardingChecklistResponse,
    status_code=status.HTTP_200_OK,
)
def get_onboarding_checklist_test(tenant_id: UUID, db: Session = Depends(get_db)):
    get_test_context()
    return _get_checklist_impl(tenant_id, db)


@router.put(
    "/{tenant_id}/onboarding/checklist/skip/{item}/test",
    response_model=OnboardingChecklistResponse,
    status_code=status.HTTP_200_OK,
)
def skip_checklist_item_test(tenant_id: UUID, item: str, db: Session = Depends(get_db)):
    get_test_context()
    skip_item(db, tenant_id, item)
    return _get_checklist_impl(tenant_id, db)


@router.put(
    "/{tenant_id}/onboarding/checklist/hidden/test",
    status_code=status.HTTP_200_OK,
)
def hide_checklist_test(
    tenant_id: UUID,
    payload: HideChecklistRequest,
    db: Session = Depends(get_db),
):
    get_test_context()
    if payload.hidden:
        hide_checklist(db, tenant_id)
    else:
        unhide_checklist(db, tenant_id)
    return {"checklist_hidden": payload.hidden}


@router.put(
    "/{tenant_id}/onboarding/checklist/dismissed/test",
    status_code=status.HTTP_200_OK,
)
def dismiss_checklist_test(tenant_id: UUID, db: Session = Depends(get_db)):
    get_test_context()
    dismiss_checklist_permanently(db, tenant_id)
    return {"checklist_dismissed_permanently": True}


# ==================== AUTHENTICATED ENDPOINTS ====================


@router.get(
    "/{tenant_id}/onboarding/checklist",
    response_model=OnboardingChecklistResponse,
    status_code=status.HTTP_200_OK,
)
def get_onboarding_checklist(
    tenant_id: UUID,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("subscription.view")),
):
    """Return full onboarding checklist state for the tenant."""
    if tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found"
        )
    return _get_checklist_impl(tenant_id, db)


@router.put(
    "/{tenant_id}/onboarding/checklist/skip/{item}",
    response_model=OnboardingChecklistResponse,
    status_code=status.HTTP_200_OK,
)
def skip_checklist_item(
    tenant_id: UUID,
    item: str,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(
        require_permission("onboarding_checklist.skip_item")
    ),
):
    """Skip a skippable checklist item: quickbooks | calendar | team"""
    if tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found"
        )
    set_audit_context_sync(db, current_user.id)
    try:
        skip_item(db, tenant_id, item)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e),
        )
    return _get_checklist_impl(tenant_id, db)


@router.put(
    "/{tenant_id}/onboarding/checklist/hidden",
    status_code=status.HTTP_200_OK,
)
def hide_checklist_route(
    tenant_id: UUID,
    payload: HideChecklistRequest,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(
        require_permission("onboarding_checklist.dismiss")
    ),
):
    """Set checklist_hidden = true/false."""
    if tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found"
        )
    set_audit_context_sync(db, current_user.id)
    if payload.hidden:
        hide_checklist(db, tenant_id)
    else:
        unhide_checklist(db, tenant_id)
    return {"checklist_hidden": payload.hidden}


@router.put(
    "/{tenant_id}/onboarding/checklist/dismissed",
    status_code=status.HTTP_200_OK,
)
def dismiss_checklist_route(
    tenant_id: UUID,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(
        require_permission("onboarding_checklist.dismiss")
    ),
):
    """Permanently dismiss the checklist widget."""
    if tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found"
        )
    set_audit_context_sync(db, current_user.id)
    dismiss_checklist_permanently(db, tenant_id)
    return {"checklist_dismissed_permanently": True}
