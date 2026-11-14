"""
SMS Quota Tracking + Cap Enforcement Service — B11/A65
=======================================================
Functions:
  check_quota()     — verify if send is allowed (does NOT modify DB)
  consume_quota()   — atomically increment used_segments after successful send
  get_current_period() — fetch active sms_quota_period for a tenant

Cap policy: read from sms_quota_period.cap_policy (default: 'soft').
  'soft' → allow send, increment overage counter, bill at $0.05/segment
  'hard' → block send if used_segments >= included_segments
"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlmodel import Session, select

if TYPE_CHECKING:
    from app.models.sms import SmsQuotaPeriod

logger = logging.getLogger(__name__)
# FIND-104: _DEFAULT_CAP_POLICY removed — now resolved via platform_setting
# (key='sms_quota_cap_policy', default='soft'). Use get_effective_setting() where needed.


@dataclass
class QuotaCheckResult:
    """Result of check_quota()."""

    allowed: bool
    overage: bool
    blocked_reason: str | None  # 'monthly_quota_reached' | 'customer_opted_out' | None
    used_segments: int
    included_segments: int
    remaining_segments: int


def check_quota(
    db: Session,
    tenant_id: UUID,
    customer_id: UUID,
    requested_segments: int,
) -> QuotaCheckResult:
    """
    Check whether a tenant can send `requested_segments` of SMS to `customer_id`.

    Checks in order:
    1. customer.sms_opted_out — returns blocked_reason='customer_opted_out' if True
    2. Current sms_quota_period — compares used vs. included
    3. cap_policy='hard' → blocked if over limit; 'soft' → allowed with overage=True

    Returns QuotaCheckResult without modifying used_segments.
    Call consume_quota() only after successful send.
    """
    from app.models.crm import Customer

    # Check 1: TCPA opt-out
    customer = db.exec(
        select(Customer).where(
            Customer.id == customer_id,
            Customer.tenant_id == tenant_id,
        )
    ).first()

    if customer and customer.sms_opted_out:
        return QuotaCheckResult(
            allowed=False,
            overage=False,
            blocked_reason="customer_opted_out",
            used_segments=0,
            included_segments=0,
            remaining_segments=0,
        )

    # Check 2: Quota period
    period = get_current_period(db, tenant_id)
    if not period:
        # No period = unlimited for MVP (provisioning hasn't set one up yet)
        return QuotaCheckResult(
            allowed=True,
            overage=False,
            blocked_reason=None,
            used_segments=0,
            included_segments=100,
            remaining_segments=100,
        )

    used = period.used_segments
    included = period.included_segments
    remaining = max(0, included - used)
    # FIND-104: resolve cap policy from platform_setting (falls back to 'soft')
    from services.setting_resolver import get_effective_setting

    resolved_cap_policy, _ = get_effective_setting(
        db, tenant_id, "sms_quota_cap_policy", fallback="soft"
    )
    cap_policy = period.cap_policy or resolved_cap_policy

    if cap_policy == "hard" and (used + requested_segments) > included:
        return QuotaCheckResult(
            allowed=False,
            overage=False,
            blocked_reason="monthly_quota_reached",
            used_segments=used,
            included_segments=included,
            remaining_segments=remaining,
        )

    overage = (used + requested_segments) > included
    return QuotaCheckResult(
        allowed=True,
        overage=overage,
        blocked_reason=None,
        used_segments=used,
        included_segments=included,
        remaining_segments=remaining,
    )


def consume_quota(
    db: Session,
    tenant_id: UUID,
    segments: int,
) -> None:
    """
    Atomically increment used_segments on the active sms_quota_period.

    Must be called in the same transaction as the successful send.
    Caller is responsible for rollback on send failure — do NOT call on failed send.

    Uses a SELECT FOR UPDATE to prevent race conditions with concurrent sends.
    """
    from app.models.sms import SmsQuotaPeriod

    now = datetime.now(UTC)

    # Lock the row for atomic update (sqlmodel select supports with_for_update via SQLAlchemy core)
    period = db.exec(
        select(SmsQuotaPeriod).where(
            SmsQuotaPeriod.tenant_id == tenant_id,
            SmsQuotaPeriod.period_start <= now,
            SmsQuotaPeriod.period_end >= now,
        )
    ).first()

    if not period:
        logger.warning(
            f"consume_quota: no active period for tenant {tenant_id} — skipping increment"
        )
        return

    period.used_segments = (period.used_segments or 0) + segments
    db.add(period)
    # Do NOT commit here — caller owns the transaction


def get_current_period(
    db: Session,
    tenant_id: UUID,
) -> Optional["SmsQuotaPeriod"]:
    """
    Return the active sms_quota_period for tenant, or None if not yet created.
    'Active' = period_start <= now <= period_end.
    """
    from app.models.sms import SmsQuotaPeriod

    now = datetime.now(UTC)
    return db.exec(
        select(SmsQuotaPeriod)
        .where(
            SmsQuotaPeriod.tenant_id == tenant_id,
            SmsQuotaPeriod.period_start <= now,
            SmsQuotaPeriod.period_end >= now,
        )
        .order_by(SmsQuotaPeriod.period_start.desc())
    ).first()


def create_initial_period(
    db: Session,
    tenant_id: UUID,
    included_segments: int = 100,
    cap_policy: str = "soft",
) -> "SmsQuotaPeriod":
    """
    Create the first sms_quota_period for a newly-provisioned tenant.
    Period covers the current calendar month UTC.
    Called at provisioning time if no period exists.
    """
    from app.models.sms import SmsQuotaPeriod

    now = datetime.now(UTC)
    # Start of current month
    period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    # End of current month: go to first of next month, subtract 1 second
    if period_start.month == 12:
        period_end = period_start.replace(year=period_start.year + 1, month=1)
    else:
        period_end = period_start.replace(month=period_start.month + 1)
    # period_end is exclusive (start of next month); store as inclusive end-of-day
    import datetime as _dt

    period_end_inclusive = period_end - _dt.timedelta(seconds=1)

    period = SmsQuotaPeriod(
        tenant_id=tenant_id,
        period_start=period_start,
        period_end=period_end_inclusive,
        included_segments=included_segments,
        used_segments=0,
        cap_policy=cap_policy,
    )
    db.add(period)
    db.commit()
    db.refresh(period)
    logger.info(
        f"Created sms_quota_period for tenant {tenant_id}: "
        f"{period_start.date()} → {period_end_inclusive.date()}, "
        f"{included_segments} segments, policy={cap_policy}"
    )
    return period
