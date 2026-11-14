"""
Rollover SMS Quota Periods — B11/A65, updated with FIND-105 overage billing
============================================================================
Celery periodic task: daily at 00:05 UTC.
Creates new sms_quota_period rows at subscription billing cycle boundaries
(start of calendar month UTC).

FIND-105: Before rolling to next period, if the closing period has overage_segments > 0
and cap_policy='soft':
- Resolve effective overage rate (2-tier: tenant override → plan-level → error)
- Resolve effective cap (same 2-tier logic)
- Create usage_ledger entry with quantity=overage_segments for metered billing audit trail
- saas_billing_aggregator task picks up unreported usage_ledger rows and aggregates them

Idempotent: uses sms_quota_period.period_start uniqueness per tenant.
If a period already exists for the new month, the creation is skipped.
"""

import logging
from datetime import UTC, datetime, timedelta

from sqlmodel import Session, select

from core.celery_app import celery_app
from core.db import get_db

logger = logging.getLogger(__name__)


def _rollover_impl(db: Session) -> dict[str, int]:
    """
    Inner implementation — identify tenants whose current quota period is ending
    within 24 hours, create the next period, and handle overage billing for closed periods.

    For each period closing with overage_segments > 0 and cap_policy='soft':
    - Resolve effective overage rate (2-tier: tenant override → plan-level → error)
    - Resolve effective cap (same 2-tier logic)
    - Calculate charge_cents = MIN(overage_segments * rate, cap ?? maxint)
    - Create usage_ledger entry for audit trail (metered billing pattern per FIND-101)
    """
    from app.models.billing import Subscription, UsageLedger
    from app.models.sms import SmsQuotaPeriod, TenantPhoneNumber
    from services.billing_rate_service import BillingConfigError, resolve_overage_rate
    from services.sms_quota import create_initial_period

    now = datetime.now(UTC)
    tomorrow = now + timedelta(hours=24)
    created = 0
    skipped = 0
    overages_billed = 0
    billing_errors = 0

    # Find all tenants with active phone numbers
    active_phones = db.exec(
        select(TenantPhoneNumber).where(TenantPhoneNumber.status == "active")
    ).all()

    tenant_ids = {p.tenant_id for p in active_phones}

    for tenant_id in tenant_ids:
        # Find the most recent period for this tenant
        latest_period = db.exec(
            select(SmsQuotaPeriod)
            .where(SmsQuotaPeriod.tenant_id == tenant_id)
            .order_by(SmsQuotaPeriod.period_start.desc())
        ).first()

        if not latest_period:
            # No period yet — create initial one
            create_initial_period(db, tenant_id)
            created += 1
            continue

        # If the latest period ends within 24 hours, create the next one
        if latest_period.period_end <= tomorrow:
            # FIND-105: Before creating next period, handle overage billing for the closing period
            if (
                latest_period.overage_segments
                and latest_period.overage_segments > 0
                and latest_period.cap_policy == "soft"
            ):
                try:
                    # Resolve effective rate using 2-tier lookup
                    # PLP-FIX-1: corrected stale pre-SD-07 code → outbound_sms_segments
                    effective_rate_cents, effective_cap = resolve_overage_rate(
                        db, tenant_id, "outbound_sms_segments"
                    )

                    # Calculate charge: MIN(overage_segments * rate, cap ?? maxint)
                    charge_cents = latest_period.overage_segments * effective_rate_cents
                    if effective_cap is not None:
                        charge_cents = min(charge_cents, effective_cap)

                    # Find active subscription for tenant to link usage ledger
                    subscription = db.exec(
                        select(Subscription).where(
                            Subscription.tenant_id == tenant_id,
                            Subscription.is_active == True,
                        )
                    ).first()

                    if subscription:
                        # Create usage_ledger entry for audit trail (metered billing pattern)
                        # This row will be picked up by saas_billing_aggregator task
                        usage_ledger = UsageLedger(
                            tenant_id=tenant_id,
                            subscription_id=subscription.id,
                            product_feature_code="outbound_sms_segments",
                            quantity=latest_period.overage_segments,
                            occurred_at=latest_period.period_end,
                            is_reported=False,
                            # PLP-FIX-1: idempotency_key is NOT NULL + unique —
                            # deterministic key per tenant+period prevents dup writes
                            idempotency_key=(
                                f"sms_overage:{tenant_id}:"
                                f"{latest_period.period_start.isoformat()}:"
                                f"{latest_period.period_end.isoformat()}"
                            ),
                        )
                        db.add(usage_ledger)

                        overages_billed += 1
                        logger.info(
                            f"Recorded SMS overage for tenant {tenant_id}: "
                            f"{latest_period.overage_segments} segments x {effective_rate_cents}c = {charge_cents}c"
                        )

                except BillingConfigError as e:
                    billing_errors += 1
                    logger.error(
                        f"Failed to resolve overage rate for tenant {tenant_id}: {e}"
                    )
                    # Continue — don't block period rollover due to billing config error
                except Exception as e:
                    billing_errors += 1
                    logger.error(
                        f"Error processing SMS overage for tenant {tenant_id}: {e}"
                    )
                    # Continue — don't block period rollover due to billing error

            next_start = _first_of_next_month(latest_period.period_end)
            next_end = _last_second_of_month(next_start)

            # Check if next period already exists (idempotency)
            existing = db.exec(
                select(SmsQuotaPeriod).where(
                    SmsQuotaPeriod.tenant_id == tenant_id,
                    SmsQuotaPeriod.period_start == next_start,
                )
            ).first()

            if existing:
                skipped += 1
                continue

            new_period = SmsQuotaPeriod(
                tenant_id=tenant_id,
                period_start=next_start,
                period_end=next_end,
                included_segments=latest_period.included_segments,
                used_segments=0,
                cap_policy=latest_period.cap_policy,
            )
            db.add(new_period)
            created += 1

    db.commit()
    return {
        "periods_created": created,
        "periods_skipped": skipped,
        "overages_billed": overages_billed,
        "billing_errors": billing_errors,
    }


def _first_of_next_month(dt: datetime) -> datetime:
    """Return the first second of the month following dt (UTC)."""
    if dt.month == 12:
        return dt.replace(
            year=dt.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0
        )
    return dt.replace(
        month=dt.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0
    )


def _last_second_of_month(first_of_month: datetime) -> datetime:
    """Return the last second of the month given its first second."""
    next_month = _first_of_next_month(first_of_month)
    return next_month - timedelta(seconds=1)


@celery_app.task(name="rollover_sms_quota_periods")
def rollover_sms_quota_periods() -> dict[str, int]:
    """
    Daily task. Create new sms_quota_period rows at subscription billing
    cycle boundaries (start of calendar month UTC).
    Handle SMS overage billing for closing periods.
    """
    db: Session = next(get_db())
    try:
        result = _rollover_impl(db)
        logger.info(f"rollover_sms_quota_periods: {result}")
        return result
    except Exception as exc:
        db.rollback()
        logger.error(f"rollover_sms_quota_periods failed: {exc}")
        raise
    finally:
        db.close()
