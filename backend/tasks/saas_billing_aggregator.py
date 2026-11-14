"""
SaaS Billing Aggregator — Celery Beat task for metered feature usage aggregation.

Runs every 4 hours (00:00, 04:00, 08:00, 12:00, 16:00, 20:00 UTC).

Workflow:
1. Query unreported usage_ledger rows (WHERE is_reported=false)
2. Group by (subscription_id, product_feature_code, billing_period)
3. Upsert into subscription_usage
4. Mark batch is_reported=true ONLY after confirmed upsert
5. If upsert fails, log and skip (retry next run — idempotent)

Tom's decision (2026-05-09):
- 4-hour cadence so subscription UI reflects usage within ≤4 hours
- Idempotent upsert makes frequent runs safe
- No hardcoded rate constants — rates always from DB (via billing_rate_service)
"""

import logging

from sqlalchemy import text
from sqlmodel import Session, select

from core.celery_app import celery_app
from core.db import get_db

logger = logging.getLogger(__name__)


@celery_app.task(name="saas_billing_aggregator")
def saas_billing_aggregator() -> dict[str, int]:
    """
    Aggregate unreported usage_ledger rows into subscription_usage.

    Returns:
        Dict with counts: {
            "rows_processed": int,
            "subscriptions_updated": int,
            "errors": int
        }
    """
    db: Session = next(get_db())
    rows_processed = 0
    subscriptions_updated = 0
    errors = 0

    try:
        from app.models.billing import UsageLedger

        # Query unreported rows (uses idx_usage_ledger_unreported partial index)
        unreported = db.exec(
            select(UsageLedger)
            .where(UsageLedger.is_reported == False)
            .limit(1000)  # Process in batches to avoid memory pressure
        ).all()

        if not unreported:
            logger.info("No unreported usage_ledger rows to aggregate")
            return {
                "rows_processed": 0,
                "subscriptions_updated": 0,
                "errors": 0,
            }

        logger.info(f"Processing {len(unreported)} unreported usage_ledger rows")

        # Group by (subscription_id, product_feature_code, period)
        # Period = month containing occurred_at (for monthly billing cycles)
        grouped: dict = {}
        for row in unreported:
            if row.subscription_id is None:
                logger.warning(f"Skipping usage_ledger {row.id} — no subscription_id")
                continue

            # Determine billing period (month containing occurred_at)
            occurred = row.occurred_at
            period_start = occurred.replace(
                day=1, hour=0, minute=0, second=0, microsecond=0
            )
            # Period end = first day of next month
            if period_start.month == 12:
                period_end = period_start.replace(year=period_start.year + 1, month=1)
            else:
                period_end = period_start.replace(month=period_start.month + 1)

            key = (
                str(row.subscription_id),
                row.product_feature_code,
                period_start.isoformat(),
                period_end.isoformat(),
            )

            if key not in grouped:
                grouped[key] = {
                    "subscription_id": row.subscription_id,
                    "product_feature_code": row.product_feature_code,
                    "period_start": period_start,
                    "period_end": period_end,
                    "total_quantity": 0.0,
                    "row_ids": [],
                }

            grouped[key]["total_quantity"] += float(row.quantity)
            grouped[key]["row_ids"].append(row.id)
            rows_processed += 1

        # Upsert each group into subscription_usage
        for key, data in grouped.items():
            try:
                # Upsert using raw SQL for PostgreSQL-specific ON CONFLICT syntax
                upsert_sql = """
                    INSERT INTO subscription_usage
                        (subscription_id, product_feature_code, period_start, period_end, used_quantity)
                    VALUES
                        (:subscription_id, :product_feature_code, :period_start, :period_end, :used_quantity)
                    ON CONFLICT (subscription_id, product_feature_code, period_start, period_end)
                    DO UPDATE SET
                        used_quantity = subscription_usage.used_quantity + EXCLUDED.used_quantity,
                        updated_at = now()
                """

                db.exec(
                    text(upsert_sql),
                    {
                        "subscription_id": str(data["subscription_id"]),
                        "product_feature_code": data["product_feature_code"],
                        "period_start": data["period_start"],
                        "period_end": data["period_end"],
                        "used_quantity": data["total_quantity"],
                    },
                )

                # Only after successful upsert, mark rows as reported
                for row_id in data["row_ids"]:
                    db.exec(
                        text(
                            """
                        UPDATE usage_ledger
                        SET is_reported = true, reported_at = now()
                        WHERE id = :row_id
                        """
                        ),
                        {"row_id": row_id},
                    )

                db.commit()
                subscriptions_updated += 1
                logger.info(
                    f"Aggregated {len(data['row_ids'])} rows for "
                    f"subscription={data['subscription_id']}, feature={data['product_feature_code']}, "
                    f"period={data['period_start'].date()}"
                )

            except Exception as e:
                db.rollback()
                errors += 1
                logger.error(
                    f"Failed to upsert subscription_usage for key {key}: {e}. "
                    f"Skipping; will retry next run."
                )

        logger.info(
            f"saas_billing_aggregator completed: "
            f"rows_processed={rows_processed}, subscriptions_updated={subscriptions_updated}, "
            f"errors={errors}"
        )

        return {
            "rows_processed": rows_processed,
            "subscriptions_updated": subscriptions_updated,
            "errors": errors,
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Fatal error in saas_billing_aggregator: {e}")
        raise

    finally:
        db.close()
