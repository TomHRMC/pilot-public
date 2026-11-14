"""C-B13 — Public Charter availability endpoint.

GET /api/v1/public/charter-availability → {open: bool, remaining: int}
No auth required. Read-only query.

The marketing site (/charter page) calls this endpoint to determine whether
the Charter cohort is still open and how many spots remain. The API always
returns the true count; suppression of the numeric counter until
``remaining <= 8`` is a frontend concern (GTM §6.8).
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func
from sqlmodel import Session, select

from app.models.core import Tenant
from app.models.subscription import SubscriptionTier
from core.db import get_db

router = APIRouter()


class CharterAvailabilityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    open: bool
    remaining: int


@router.get(
    "/charter-availability",
    response_model=CharterAvailabilityResponse,
)
def get_charter_availability(db: Session = Depends(get_db)):
    """Public endpoint — returns Charter cohort availability.

    Returns ``{open: false, remaining: 0}`` when:
    - Charter tier not found
    - Charter tier ``is_active = false`` (cohort closed)
    - ``remaining <= 0`` (cap reached)
    """
    charter_tier = db.exec(
        select(SubscriptionTier).where(SubscriptionTier.tier_name == "charter")
    ).first()

    if not charter_tier or not charter_tier.is_active:
        return CharterAvailabilityResponse(open=False, remaining=0)

    charter_count = db.exec(
        select(func.count(Tenant.id)).where(Tenant.charter_eligible == True)
    ).one()

    remaining = charter_tier.signup_cap - charter_count

    if remaining <= 0:
        return CharterAvailabilityResponse(open=False, remaining=0)

    return CharterAvailabilityResponse(open=True, remaining=remaining)
