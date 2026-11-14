"""
SMS Quota Routes — B11/A65
===========================
Routes:
  GET /api/v1/sms/quota   — view current period quota status

RBAC: settings.view
"""

import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlmodel import Session

from core.auth import AuthenticatedUser
from core.db import get_db
from core.permissions import require_permission
from core.test_context import TestUserContext, get_test_context
from services.sms_quota import get_current_period

router = APIRouter()
logger = logging.getLogger(__name__)


class SmsQuotaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    period_start: str | None = None
    period_end: str | None = None
    included_segments: int
    used_segments: int
    overage_segments: int
    remaining_segments: int
    cap_policy: str
    projected_month_end_segments: int | None = None


def _get_quota_impl(
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> SmsQuotaResponse:
    period = get_current_period(db, user_context.tenant_id)

    if not period:
        return SmsQuotaResponse(
            period_start=None,
            period_end=None,
            included_segments=100,
            used_segments=0,
            overage_segments=0,
            remaining_segments=100,
            cap_policy="soft",
            projected_month_end_segments=0,
        )

    used = period.used_segments or 0
    included = period.included_segments or 100
    overage = max(0, used - included)
    remaining = max(0, included - used)

    # Simple linear projection: extrapolate to end of period
    from datetime import UTC, datetime

    now = datetime.now(UTC)
    period_start = period.period_start
    period_end = period.period_end

    elapsed_fraction = (now - period_start).total_seconds() / max(
        1, (period_end - period_start).total_seconds()
    )
    projected = int(used / max(0.001, elapsed_fraction)) if elapsed_fraction > 0 else 0

    return SmsQuotaResponse(
        period_start=period_start.isoformat() if period_start else None,
        period_end=period_end.isoformat() if period_end else None,
        included_segments=included,
        used_segments=used,
        overage_segments=overage,
        remaining_segments=remaining,
        cap_policy=period.cap_policy or "soft",
        projected_month_end_segments=projected,
    )


@router.get(
    "/test",
    response_model=SmsQuotaResponse,
    summary="[TEST] Get SMS quota — no auth",
)
def get_sms_quota_test(db: Session = Depends(get_db)) -> SmsQuotaResponse:
    """Test endpoint — blocked in staging/production."""
    test_context = get_test_context()
    return _get_quota_impl(db, test_context)


@router.get(
    "/",
    response_model=SmsQuotaResponse,
    summary="Get current SMS quota for tenant",
)
def get_sms_quota(
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("settings.view")),
) -> SmsQuotaResponse:
    """Return the current period's quota usage for the calling user's tenant."""
    return _get_quota_impl(db, current_user)
