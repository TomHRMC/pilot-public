"""
PLP-STRIPE-CHARTER-ROW-1 — One-time backfill: local `subscription` row for an
existing Charter tenant.

Context
-------
The author's own end-to-end Charter signup test (Lang Electric Co., his test
tenant, on the pre-release AWS environment, Stripe test mode) completed signup and landed on
the dashboard, but no local `public.subscription` row was written:

- `create_charter_subscription()` created the Stripe subscription but never
  inserted the local row (fixed in this batch — write-at-source).
- The `customer.subscription.created` webhook's tier-by-price lookup missed
  because the Charter tier has NULL stripe_price_id_* columns in the pre-release
  environment (fixed in
  this batch — metadata.tier_code fallback).

Without the row, `is_subscription_billing_active()` returns False and the API
paywall 402s every paywalled mutation for the tenant.

What this script does
---------------------
1. Loads the tenant row (must exist; reads `free_period_ends_at` from it).
2. Lists the customer's subscriptions from Stripe and picks the trialing/active
   one. The `sub_…` id is READ FROM STRIPE — never fabricated.
3. Calls the shared `_write_local_charter_subscription_row()` helper, which
   upserts ON CONFLICT (psp_subscription_id) DO UPDATE — so re-running this
   script is a no-op.
4. Prints the resulting row for verification.

Usage (from backend/, venv active)
----------------------------------
    # Dry-run against local dev DB (no writes):
    python -m migrations.scripts.backfill_charter_subscription_row --dry-run

    # Backfill the Lang Electric test tenant (defaults below). Requires
    # DATABASE_URL pointed at the pre-release AWS environment (via the operator's SSH tunnel) and STRIPE_SECRET_KEY
    # for the same mode (test) the tenant was created with:
    python -m migrations.scripts.backfill_charter_subscription_row

    # Different tenant/customer:
    python -m migrations.scripts.backfill_charter_subscription_row \
        --tenant-id <uuid> --stripe-customer-id cus_...

Idempotency
-----------
Safe to run twice. The helper upserts on the unique `psp_subscription_id`
index; a second run performs an UPDATE of the same row (no duplicate insert).
"""

import argparse
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

# Ensure the backend directory is on sys.path so `migrations.*`, `app.*`, and
# `services.*` imports resolve when the script is run directly (not via -m).
_backend_dir = Path(__file__).parent.parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

from migrations.scripts._db_utils import get_db_session  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ── Backfill target: Lang Electric Co. (author's test tenant) ───────────────
DEFAULT_TENANT_ID = "00000000-0000-0000-0000-000000000000"  # placeholder; pass the real tenant ID
DEFAULT_STRIPE_CUSTOMER_ID = "cus_REDACTEDX02"

# Stripe subscription statuses considered "live" for the backfill.
_LIVE_STATUSES = ("trialing", "active", "past_due")


def _pick_live_subscription(stripe, stripe_customer_id: str):
    """Return the first trialing/active Subscription for the customer, or None."""
    subs = stripe.Subscription.list(customer=stripe_customer_id, limit=10)
    for sub in subs.auto_paging_iter():
        # StripeObject does not support .get() — use getattr (C-B14-FIX #2)
        if getattr(sub, "status", None) in _LIVE_STATUSES:
            return sub
    return None


def run_backfill(
    *,
    tenant_id: UUID,
    stripe_customer_id: str,
    dry_run: bool = False,
) -> bool:
    """Execute the backfill. Returns True if a row exists after the run."""
    from sqlmodel import select

    from app.models.billing import Subscription
    from app.models.core import Tenant

    with get_db_session() as db:
        tenant = db.exec(select(Tenant).where(Tenant.id == tenant_id)).first()
        if not tenant:
            logger.error("Tenant %s not found — aborting.", tenant_id)
            return False

        existing = db.exec(
            select(Subscription).where(
                Subscription.tenant_id == tenant_id,
                Subscription.is_active == True,
            )
        ).first()
        if existing:
            logger.info(
                "Active subscription row already present for tenant %s "
                "(psp_subscription_id=%s) — nothing to do.",
                tenant_id,
                existing.psp_subscription_id,
            )
            return True

        # Read the sub_… id from Stripe — never fabricate it.
        from services.stripe_subscriptions import (
            _get_stripe_client,
            _write_local_charter_subscription_row,
        )

        stripe = _get_stripe_client()
        sub = _pick_live_subscription(stripe, stripe_customer_id)
        if not sub:
            logger.error(
                "No trialing/active Stripe subscription found for customer %s — "
                "aborting. Check the Stripe dashboard for the correct mode.",
                stripe_customer_id,
            )
            return False

        logger.info(
            "Found Stripe subscription %s (status=%s) for customer %s",
            sub["id"],
            getattr(sub, "status", None),
            stripe_customer_id,
        )

        # free_period_ends_at: tenant row is the source of truth (set by the
        # signup wizard); fall back to the Stripe trial_end timestamp.
        free_period_ends_at = tenant.free_period_ends_at
        if not free_period_ends_at:
            # StripeObject does not support .get() — use getattr (C-B14-FIX #2)
            trial_end_ts = getattr(sub, "trial_end", None)
            if trial_end_ts:
                free_period_ends_at = datetime.fromtimestamp(trial_end_ts, tz=UTC)
        if not free_period_ends_at:
            logger.error(
                "Tenant %s has no free_period_ends_at and subscription %s has no "
                "trial_end — cannot build the row. Aborting.",
                tenant_id,
                sub["id"],
            )
            return False

        if dry_run:
            logger.info(
                "DRY RUN — would upsert subscription row: tenant_id=%s "
                "psp_subscription_id=%s psp_customer_id=%s "
                "trial_ends_at=%s status=trialing",
                tenant_id,
                sub["id"],
                stripe_customer_id,
                free_period_ends_at,
            )
            return True

        _write_local_charter_subscription_row(
            db,
            tenant_id=tenant_id,
            stripe_customer_id=stripe_customer_id,
            stripe_subscription_id=sub["id"],
            free_period_ends_at=free_period_ends_at,
        )

        # Verify
        row = db.exec(
            select(Subscription).where(Subscription.psp_subscription_id == sub["id"])
        ).first()
        if row:
            logger.info(
                "✅ Backfill complete: subscription id=%s status_id=%s "
                "is_active=%s trial_ends_at=%s",
                row.id,
                row.status_id,
                row.is_active,
                row.trial_ends_at,
            )
            return True

        logger.error(
            "Backfill ran but no row found for psp_subscription_id=%s — "
            "check helper logs above.",
            sub["id"],
        )
        return False


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Backfill the local subscription row for a Charter tenant.",
    )
    parser.add_argument(
        "--tenant-id",
        default=DEFAULT_TENANT_ID,
        help=f"Tenant UUID (default: {DEFAULT_TENANT_ID} — Lang Electric Co.)",
    )
    parser.add_argument(
        "--stripe-customer-id",
        default=DEFAULT_STRIPE_CUSTOMER_ID,
        help=f"Stripe customer id (default: {DEFAULT_STRIPE_CUSTOMER_ID})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Resolve everything and print the planned upsert, but do not write.",
    )
    args = parser.parse_args()

    ok = run_backfill(
        tenant_id=UUID(args.tenant_id),
        stripe_customer_id=args.stripe_customer_id,
        dry_run=args.dry_run,
    )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
