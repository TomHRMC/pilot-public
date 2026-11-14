"""
B14/A75 — GET /api/v1/subscription-tiers
Returns all active subscription tiers for the tier picker UI.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict
from sqlmodel import Session, select

from app.models.subscription import SubscriptionTier
from core.auth import AuthenticatedUser
from core.db import get_db
from core.permissions import require_permission
from core.test_context import get_test_context

router = APIRouter()


# ==================== SCHEMAS ====================


class SubscriptionTierResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    tier_id: UUID
    tier_name: str
    display_label: str
    monthly_price_cents: int
    annual_price_cents: int  # PLP-FIX-5 (Issue 8): yearly total (58800 = $588/yr)
    is_trial: bool
    trial_duration_days: int | None
    schedule_lanes: int
    display_order: int
    is_active: bool
    # C-B2: Charter program lifecycle fields
    free_period_days: int | None
    requires_payment_method: bool
    signup_cap: int | None
    price_locked: bool


class SubscriptionTiersListResponse(BaseModel):
    tiers: list[SubscriptionTierResponse]


# ==================== SHARED LOGIC ====================


def _list_tiers_impl(db: Session) -> SubscriptionTiersListResponse:
    """Return all active tiers ordered by display_order."""
    tiers = db.exec(
        select(SubscriptionTier)
        .where(SubscriptionTier.is_active == True)
        .order_by(SubscriptionTier.display_order)
    ).all()
    return SubscriptionTiersListResponse(
        tiers=[SubscriptionTierResponse.model_validate(t) for t in tiers]
    )


# ==================== TEST ENDPOINTS ====================


@router.get(
    "/test",
    response_model=SubscriptionTiersListResponse,
    status_code=status.HTTP_200_OK,
)
def list_subscription_tiers_test(db: Session = Depends(get_db)):
    """Test endpoint — no auth required. Blocked in staging/production."""
    get_test_context()  # Raises 403 if disabled
    return _list_tiers_impl(db)


# ==================== AUTHENTICATED ENDPOINTS ====================


@router.get(
    "/", response_model=SubscriptionTiersListResponse, status_code=status.HTTP_200_OK
)
def list_subscription_tiers(
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("subscription.view")),
):
    """Return all active subscription tiers. Requires subscription.view permission."""
    return _list_tiers_impl(db)
