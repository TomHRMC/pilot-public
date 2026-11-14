# Batch STRIPE-B1 Design — Annual Billing Service Layer + Founders Cohort Schedule

**Version**: 1.0  
**Date**: 2026-07-14  
**Author**: Pilot Architect  
**Status**: READY FOR IMPLEMENTATION  
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §2 P1 — STRIPE-B1  
**Prerequisite**: SD-3 complete ✅ — `subscription_tier` has `stripe_price_id_monthly`, `stripe_price_id_annual`, `annual_price_cents`, `monthly_price_cents` columns  

---

## Table of Contents

- [A. Input Read Summary](#a-input-read-summary)
- [B. What SD-3 Left Broken (Pre-Existing Issues STRIPE-B1 Must Fix)](#b-what-sd-3-left-broken)
- [C. Migration Plan](#c-migration-plan)
- [D. Execution Order](#d-execution-order)
- [E. Service Changes — `stripe_subscriptions.py`](#e-service-changes--stripe_subscriptionspy)
- [F. Route Changes — `tenant_subscription.py`](#f-route-changes--tenant_subscriptionpy)
- [G. Webhook Changes — `webhooks_stripe.py`](#g-webhook-changes--webhooks_stripepy)
- [H. Founders Subscription Schedule Design](#h-founders-subscription-schedule-design)
- [I. Pattern Reuse Decisions](#i-pattern-reuse-decisions)
- [J. Open Questions Resolved](#j-open-questions-resolved)

---

## A. Input Read Summary

| Input | Key Finding |
|---|---|
| `backend/services/stripe_subscriptions.py` | **2 pre-existing bugs** (lines 188, 191-193): `billing_interval` is read from `billing_cycle_anchor` (wrong field) and then checked via `hasattr(tier, "billing_interval")` (SubscriptionTier has no such field — always defaults to `"monthly"`). These were pre-existing before SD-3. |
| `backend/api/routes/tenant_subscription.py` | **5 stale references** to `target_tier.stripe_price_id` (lines 228, 280, 308, 370, 387) — old field name that no longer exists after SD-3 column rename. These will `AttributeError` at runtime. |
| `backend/app/models/billing.py` | `Subscription` model has `billing_interval` field with `CHECK IN ('monthly','annual')`. Does NOT have `stripe_schedule_id`. |
| Live DB — `subscription` table | No `stripe_schedule_id` column. All other expected fields present. |
| `dev-docs/analysis/pilot-launch-plan.md` §2 STRIPE-B1 | 5 scope items: (1) billing_interval routing, (2) `stripe_schedule_id` column, (3) `create_founders_subscription_schedule()`, (4) `customer.subscription.schedule.updated` webhook, (5) upgrade route `billing_interval` param |
| `dev-docs/integrations/stripe/stripe-pricing-config.md` §7 | Annual Stripe prices not yet created by Tom (NULL `stripe_price_id_annual` in DB). STRIPE-B1 must handle NULL gracefully — annual billing falls back to error until Tom creates the prices. |

---

## B. What SD-3 Left Broken

These are NOT new requirements — they are regressions introduced by SD-3's column rename that must be fixed in STRIPE-B1 before any paid subscription can be created.

### B.1 — `tenant_subscription.py` stale field references

After SD-3, `SubscriptionTier.stripe_price_id` no longer exists. These references will all `AttributeError` at runtime:

| File | Line | Stale Reference | Fix |
|---|---|---|---|
| `tenant_subscription.py` | 228 | `target_tier.stripe_price_id` | Replace with billing_interval routing logic |
| `tenant_subscription.py` | 280 | `target_tier.stripe_price_id` | Replace with `target_tier.stripe_price_id_monthly` (ConvertFromTrial always defaults monthly for now) |
| `tenant_subscription.py` | 308 | `target_tier.stripe_price_id` | Replace with billing_interval-aware price selection |
| `tenant_subscription.py` | 370 | `target_tier.stripe_price_id` | Replace with `target_tier.stripe_price_id_monthly` |
| `tenant_subscription.py` | 387 | `target_tier.stripe_price_id` | Replace with billing_interval-aware price selection |

### B.2 — `stripe_subscriptions.py` billing_interval detection bugs

Line 188: `billing_interval = subscription.get("billing_cycle_anchor")` — copies the integer Unix timestamp of the billing anchor, not the interval string. This variable is then never used correctly.

Lines 191-193: `if hasattr(tier, "billing_interval") and tier.billing_interval` — `SubscriptionTier` has no `billing_interval` field. This block always evaluates to False, so `billing_interval_str` is always `"monthly"` regardless of what the tenant selected. Annual subscriptions would be stored with `billing_interval = "monthly"` in the DB.

---

## C. Migration Plan

### C.1 Single migration: Add `stripe_schedule_id` to `subscription`

The only schema change in STRIPE-B1 is adding a nullable `stripe_schedule_id` column to `subscription`. This stores the Stripe Subscription Schedule ID for founders cohort tenants so the schedule can be cancelled or modified if needed.

```python
def upgrade() -> None:
    op.add_column(
        'subscription',
        sa.Column('stripe_schedule_id', sa.Text(), nullable=True),
        schema='public'
    )

def downgrade() -> None:
    op.drop_column('subscription', 'stripe_schedule_id', schema='public')
```

### C.2 MCP Pre-Work Verification Queries

```sql
-- 1. Confirm SD-3 columns exist on subscription_tier
SELECT column_name, data_type FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'subscription_tier'
  AND column_name IN ('stripe_price_id_monthly','stripe_price_id_annual','annual_price_cents','monthly_price_cents')
ORDER BY column_name;
-- Expected: 4 rows — all must exist before proceeding

-- 2. Confirm stripe_price_id column NO LONGER exists (SD-3 renamed it)
SELECT column_name FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'subscription_tier'
  AND column_name = 'stripe_price_id';
-- Expected: 0 rows (column was renamed by SD-3)

-- 3. Confirm stripe_schedule_id does NOT yet exist on subscription
SELECT column_name FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'subscription'
  AND column_name = 'stripe_schedule_id';
-- Expected: 0 rows (this migration adds it)

-- 4. Confirm subscription.billing_interval CHECK constraint exists
SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint
WHERE conrelid = 'public.subscription'::regclass AND conname LIKE '%billing_interval%';
-- Expected: subscription_billing_interval_chk with "billing_interval IN ('monthly','annual')"

-- 5. Confirm current test-mode stripe_price_id_monthly values
SELECT tier_name, stripe_price_id_monthly, stripe_price_id_annual
FROM public.subscription_tier ORDER BY display_order;
-- Expected: starter + teams have stripe_price_id_monthly set; all annual IDs are NULL

-- 6. Confirm Alembic head
SELECT version_num FROM public.alembic_version;

-- 7. Confirm SubscriptionTier model columns to verify all SD-3 field names
SELECT column_name, data_type FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'subscription_tier'
ORDER BY ordinal_position;
```

---

## D. Execution Order

| Step | Task | Files touched |
|---|---|---|
| 1 | MCP pre-work verification (all 7 queries) | — |
| 2 | Read source files: `stripe_subscriptions.py`, `tenant_subscription.py`, `webhooks_stripe.py`, `app/models/billing.py`, `app/models/subscription.py`, `api/schemas/schemas.py` (if billing_interval is defined there) | — |
| 3 | Write blank Alembic migration: add `stripe_schedule_id` to `subscription` | `migrations/versions/YYYY_*_stripe_b1_subscription_schedule_id.py` |
| 4 | Update `Subscription` SQLModel: add `stripe_schedule_id` field | `app/models/billing.py` |
| 5 | Run `python generate_db_model_map.py` | `db_models_map.md` |
| 6 | Fix billing_interval detection bugs in `handle_subscription_created()` | `services/stripe_subscriptions.py` |
| 7 | Add `create_founders_subscription_schedule()` function | `services/stripe_subscriptions.py` |
| 8 | Add `handle_subscription_schedule_updated()` webhook handler | `services/stripe_subscriptions.py` |
| 9 | Add `billing_interval` field to `ConvertFromTrialRequest` + `ChangeTierRequest` schemas | `api/routes/tenant_subscription.py` |
| 10 | Fix all 5 stale `target_tier.stripe_price_id` references in route file | `api/routes/tenant_subscription.py` |
| 11 | Add `_select_stripe_price_id()` helper function in route file | `api/routes/tenant_subscription.py` |
| 12 | Register `customer.subscription.schedule.updated` in webhook router | `api/routes/webhooks_stripe.py` |
| 13 | Run `pytest -m unit --tb=short -q` — fix any failures | — |
| 14 | Run `python export_openapi_json.py` (request schemas changed) | `openapi.json`, `openapi_schema_map.md` |
| 15 | Write tests (3 test files) | `tests/domains/subscriptions_usage/test_stripe_b1_*.py` |
| 16 | Run `pytest --tb=short -q` (full suite) | — |
| 17 | Update `stripe-pricing-config.md` §8 webhooks table + §7 founders schedule instructions | `dev-docs/integrations/stripe/stripe-pricing-config.md` |
| 18 | Update `pilot-launch-plan.md` — STRIPE-B1 items marked done, Appendix A + B | `dev-docs/analysis/pilot-launch-plan.md` |
| 19 | Update `pilot-operations.md` §4 — add billing_interval routing + founders schedule | `dev-docs/pilot-operations.md` |

---

## E. Service Changes — `stripe_subscriptions.py`

### E.1 Fix `create_stripe_subscription()` — no signature change needed

The function currently accepts `stripe_price_id: str` as a raw parameter — the caller is responsible for passing the correct price ID. This is the right design. **No change needed to this function's signature or body.**

The callers (`tenant_subscription.py`) must pass the correct price ID based on `billing_interval`. That fix lives in the route file (§F).

### E.2 Fix `handle_subscription_created()` — billing_interval detection

**Current buggy code (lines 186-193)**:
```python
billing_cycle_anchor = subscription.get("billing_cycle_anchor")   # integer timestamp
current_period_end = subscription.get("current_period_end")
billing_interval = subscription.get("billing_cycle_anchor")       # BUG: copies anchor, not interval

# Determine billing interval from tier (default monthly)
billing_interval_str = "monthly"
if hasattr(tier, "billing_interval") and tier.billing_interval:   # BUG: SubscriptionTier has no billing_interval
    billing_interval_str = tier.billing_interval
```

**Fixed code**:
```python
billing_cycle_anchor = subscription.get("billing_cycle_anchor")   # integer timestamp
current_period_end = subscription.get("current_period_end")

# Derive billing interval from Stripe subscription items
# Stripe returns "month" or "year" in price.recurring.interval
billing_interval_str = "monthly"  # default
items = subscription.get("items", {}).get("data", [])
if items:
    stripe_interval = items[0].get("price", {}).get("recurring", {}).get("interval")
    if stripe_interval == "year":
        billing_interval_str = "annual"
    # "month" → "monthly" (already defaulted above)
```

Also fix the tier lookup to search BOTH monthly AND annual price IDs:

**Current buggy tier lookup (line 151-155)**:
```python
tier = db.exec(
    select(SubscriptionTier)
    .where(SubscriptionTier.stripe_price_id_monthly == price_id)
    .where(SubscriptionTier.is_active == True)
).first()
```

**Fixed tier lookup** (search both columns):
```python
from sqlalchemy import or_

tier = db.exec(
    select(SubscriptionTier)
    .where(
        or_(
            SubscriptionTier.stripe_price_id_monthly == price_id,
            SubscriptionTier.stripe_price_id_annual == price_id,
        )
    )
).first()
# Note: no is_active filter — webhook must process subscriptions for any tier,
# including inactive ones (e.g., GA-only tiers that have is_active=False in founders mode)
```

### E.3 New function — `create_founders_subscription_schedule()`

Called at founders tenant signup after Cognito user + tenant rows are created. Creates a 2-phase Stripe Subscription Schedule: 6 months free → then $49/mo (starter monthly price) ongoing.

```python
def create_founders_subscription_schedule(
    db: Session,
    tenant_id: UUID,
    stripe_customer_id: str,
) -> str:
    """
    Create a Stripe Subscription Schedule for a founders cohort tenant.
    Phase 1: $0/mo for 6 months (free cohort period).
    Phase 2: Starter monthly price ($49/mo) starting at month 7, ongoing.

    Returns:
        str: Stripe Subscription Schedule ID (sub_sched_...)
    
    Stores schedule ID on subscription.stripe_schedule_id.
    The schedule fires customer.subscription.schedule.updated at month 7
    — the webhook handler activates billing at that point.
    
    IMPORTANT: Annual price IDs are NULL until Tom creates them in Stripe Dashboard.
    The founders plan always uses the MONTHLY price for Phase 2 (founders get
    $49/mo forever, not discounted annual rate — their deal is the locked price,
    not the billing interval).
    """
    from app.models.billing import Subscription
    from app.models.subscription import SubscriptionTier

    stripe = _get_stripe_client()

    # Get the starter tier monthly price for Phase 2
    starter_tier = db.exec(
        select(SubscriptionTier).where(SubscriptionTier.tier_name == "starter")
    ).first()

    if not starter_tier or not starter_tier.stripe_price_id_monthly:
        raise ValueError(
            "starter tier or stripe_price_id_monthly not configured — "
            "cannot create founders subscription schedule. "
            "Ensure SD-3 seed has run and Tom has created Stripe monthly prices."
        )

    # Create Stripe Subscription Schedule
    # Phase 1: 6 iterations of monthly period with $0 price (no items = $0)
    # Phase 2: open-ended, billing at starter monthly price
    schedule = stripe.SubscriptionSchedule.create(
        customer=stripe_customer_id,
        start_date="now",
        end_behavior="release",   # When schedule ends, releases to a regular subscription
        phases=[
            {
                # Phase 1: 6 months free — no items means no charge
                "items": [],
                "iterations": 6,
                "metadata": {"phase": "founders_free_period"},
            },
            {
                # Phase 2: $49/mo ongoing, released to regular subscription
                "items": [{"price": starter_tier.stripe_price_id_monthly, "quantity": 1}],
                "metadata": {"phase": "founders_paid_period"},
            },
        ],
        metadata={"tenant_id": str(tenant_id), "schedule_type": "founders_cohort"},
    )

    # Store schedule ID on the subscription row
    sub_row = db.exec(
        select(Subscription)
        .where(Subscription.tenant_id == tenant_id)
        .where(Subscription.is_active == True)
    ).first()

    if sub_row:
        sub_row.stripe_schedule_id = schedule.id
        db.add(sub_row)
        db.commit()

    logger.info(
        f"Founders subscription schedule created for tenant {tenant_id}: "
        f"{schedule.id} — Phase 2 starts at month 7."
    )
    return schedule.id
```

> **NOTE**: Phase 1 items are empty `[]` — Stripe accepts this for a $0 phase. An alternative is to use a $0 trial period (Stripe `trial_end`), but the Schedule approach is cleaner because it explicitly shows the 6-month free window vs. a paid window in the Stripe Dashboard, making it auditable.

> **Stripe Dashboard**: After `create_founders_subscription_schedule()` runs, Tom can see the schedule under the customer in Stripe Dashboard. If a founder churns early, Tom can cancel the schedule before Phase 2 activates.

### E.4 New function — `handle_subscription_schedule_updated()`

Fires when Stripe advances a Subscription Schedule from Phase 1 to Phase 2 (at month 7 for founders). Must update the tenant's tier and subscription row to reflect active billing.

```python
def handle_subscription_schedule_updated(db: Session, stripe_event: dict) -> None:
    """
    Process customer.subscription.schedule.updated webhook.
    Fires when a Subscription Schedule phase transitions — specifically when
    founders tenants advance from Phase 1 (free) to Phase 2 (paid at month 7).

    Actions on Phase 2 activation:
    - Update subscription.billing_interval = 'monthly'
    - Update subscription.renews_at to next billing date
    - Update tenant.current_subscription_tier_id to starter tier
    - Clear tenant.trial_ends_at (if still set)
    - Log the transition for audit trail
    """
    from datetime import UTC, datetime
    from app.models.billing import Subscription
    from app.models.core import Tenant
    from app.models.subscription import SubscriptionTier

    schedule = stripe_event.get("data", {}).get("object", {})
    schedule_id = schedule.get("id")
    stripe_customer_id = schedule.get("customer")
    current_phase = schedule.get("current_phase", {})
    metadata = schedule.get("metadata", {})

    # Only process founders_cohort schedules
    if metadata.get("schedule_type") != "founders_cohort":
        logger.info(f"Ignoring non-founders schedule update: {schedule_id}")
        return

    # Find tenant by stripe_customer_id
    tenant = db.exec(
        select(Tenant).where(Tenant.stripe_customer_id == stripe_customer_id)
    ).first()
    if not tenant:
        logger.warning(f"handle_subscription_schedule_updated: no tenant for {stripe_customer_id}")
        return

    # Check if we're entering Phase 2 (paid phase)
    # Phase 2 is identified by its metadata or by the absence of empty items
    phases = schedule.get("phases", [])
    current_phase_index = None
    for i, phase in enumerate(phases):
        if phase.get("start_date") == current_phase.get("start_date"):
            current_phase_index = i
            break

    if current_phase_index != 1:
        # Not Phase 2 transition — Phase 1 start or end-of-schedule event
        logger.info(
            f"Founders schedule {schedule_id}: phase {current_phase_index} event — "
            "no tier change needed"
        )
        return

    # Phase 2 activation: update tenant to starter tier
    starter_tier = db.exec(
        select(SubscriptionTier).where(SubscriptionTier.tier_name == "starter")
    ).first()
    if not starter_tier:
        logger.error("handle_subscription_schedule_updated: starter tier not found")
        return

    tenant.current_subscription_tier_id = starter_tier.tier_id
    tenant.trial_ends_at = None  # Clear any residual trial end date
    db.add(tenant)

    # Update subscription row
    sub_row = db.exec(
        select(Subscription)
        .where(Subscription.tenant_id == tenant.id)
        .where(Subscription.is_active == True)
    ).first()
    if sub_row:
        sub_row.billing_interval = "monthly"
        phase_end = current_phase.get("end_date")
        if phase_end:
            sub_row.renews_at = datetime.fromtimestamp(phase_end, tz=UTC)
        db.add(sub_row)

    db.commit()
    logger.info(
        f"Founders tenant {tenant.id} transitioned to paid tier at month 7. "
        f"Schedule: {schedule_id}"
    )
```

---

## F. Route Changes — `tenant_subscription.py`

### F.1 Add helper function `_select_stripe_price_id()`

Add this helper before the existing `_upgrade_tenant_subscription_impl()`. It centralizes the price ID selection logic across all three route functions.

```python
def _select_stripe_price_id(
    tier: SubscriptionTier,
    billing_interval: str,
) -> str | None:
    """
    Select the correct Stripe price ID based on billing interval.
    Returns None if the required price ID is not yet configured.
    
    billing_interval must be 'monthly' or 'annual'.
    Annual price IDs are NULL until Tom creates them in Stripe Dashboard.
    """
    if billing_interval == "annual":
        return tier.stripe_price_id_annual  # May be None — caller must check
    return tier.stripe_price_id_monthly     # monthly (default)
```

### F.2 Add `billing_interval` to request schemas

**`ConvertFromTrialRequest`** — add `billing_interval` field:
```python
class ConvertFromTrialRequest(BaseModel):
    target_tier_id: UUID
    payment_method_id: str
    billing_email: str
    billing_interval: Literal["monthly", "annual"] = "monthly"
```

**`ChangeTierRequest`** — add `billing_interval` field:
```python
class ChangeTierRequest(BaseModel):
    target_tier_id: UUID
    billing_interval: Literal["monthly", "annual"] = "monthly"
```

Note: `SubscriptionUpgradeRequest` does NOT need `billing_interval` — it handles free tiers (no Stripe). Keep it as-is.

### F.3 Fix `_upgrade_tenant_subscription_impl()` — line 228

This function handles free tier upgrades (trial tier, founders tier). The condition checking `target_tier.stripe_price_id` needs fixing:

```python
# BEFORE (line 228 — stale field name)
if (
    not isinstance(user_context, TestUserContext)
    and not target_tier.is_trial
    and target_tier.stripe_price_id
):

# AFTER
if (
    not isinstance(user_context, TestUserContext)
    and not target_tier.is_trial
    and target_tier.stripe_price_id_monthly  # Check monthly; annual not needed for upgrade redirect
):
```

### F.4 Fix `_convert_from_trial_impl()` — lines 280, 308

```python
# BEFORE (line 280)
if not target_tier.stripe_price_id:
    raise HTTPException(...)

# AFTER
selected_price_id = _select_stripe_price_id(target_tier, payload.billing_interval)
if not selected_price_id:
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail={
            "type": "https://errors.pilotfortrades.com/billing-not-configured",
            "title": "Billing not configured",
            "status": 400,
            "detail": (
                f"Target tier does not have a Stripe price configured for "
                f"'{payload.billing_interval}' billing. "
                "Contact support or choose monthly billing."
            ),
        },
    )

# BEFORE (line 304-310)
stripe_subscription_id = create_stripe_subscription(
    db,
    tenant_id,
    stripe_customer_id,
    target_tier.stripe_price_id,
    payload.payment_method_id,
)

# AFTER
stripe_subscription_id = create_stripe_subscription(
    db,
    tenant_id,
    stripe_customer_id,
    selected_price_id,
    payload.payment_method_id,
)
```

Also update `ConvertFromTrialResponse` to include `billing_interval` in response if needed for frontend:
```python
class ConvertFromTrialResponse(BaseModel):
    psp_subscription_id: str
    status: str
    billing_interval: str = "monthly"
```

### F.5 Fix `_change_tier_impl()` — lines 370, 387

```python
# BEFORE (line 370)
if not target_tier.stripe_price_id:
    raise HTTPException(...)

# AFTER
selected_price_id = _select_stripe_price_id(target_tier, payload.billing_interval)
if not selected_price_id:
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail={
            "type": "https://errors.pilotfortrades.com/billing-not-configured",
            "title": "Billing not configured",
            "status": 400,
            "detail": (
                f"Target tier does not have a Stripe price configured for "
                f"'{payload.billing_interval}' billing."
            ),
        },
    )

# BEFORE (line 386-388)
stripe.Subscription.modify(
    current_subscription.psp_subscription_id,
    items=[{"price": target_tier.stripe_price_id}],
)

# AFTER
stripe.Subscription.modify(
    current_subscription.psp_subscription_id,
    items=[{"price": selected_price_id}],
)
```

---

## G. Webhook Changes — `webhooks_stripe.py`

Two changes:

### G.1 Register `customer.subscription.schedule.updated` event

Add a new `elif` branch in the webhook event dispatch function:

```python
elif event_type == "customer.subscription.schedule.updated":
    handle_subscription_schedule_updated(db, event)
```

### G.2 Import the new handler

```python
from services.stripe_subscriptions import (
    handle_subscription_created,
    handle_invoice_payment_failed,
    handle_subscription_schedule_updated,   # NEW
    _handle_refund_event,
)
```

### G.3 Update `stripe-pricing-config.md` §8 webhooks table

Add to the registered events table:

| Event | Handler |
|---|---|
| `customer.subscription.schedule.updated` | `handle_subscription_schedule_updated()` |

> **Tom action**: Register this event in Stripe Dashboard under the production webhook endpoint `https://api.pilotfortrades.com/api/v1/webhooks/stripe`. Also register it on the test-mode ngrok endpoint.

---

## H. Founders Subscription Schedule Design

### H.1 When is the schedule created?

`create_founders_subscription_schedule()` is called during founders tenant sign-up flow, after:
1. Cognito user created
2. `tenant` row inserted
3. `user` row inserted  
4. `subscription` row created (with `product_plan_code = 'founders_plan'`, `billing_interval = 'monthly'`)
5. **`create_founders_subscription_schedule()`** is called here
6. `stripe_schedule_id` stored back on `subscription` row

The sign-up flow currently lives in the tenant onboarding service (or signup route). STRIPE-B1 must find this entry point and wire in the schedule creation.

> **Engineer**: Search for `"founders"` and signup flow entry points: `grep -rn "founders.*tier\|signup.*founders\|create_stripe_customer" backend/api/ --include="*.py"` to locate the sign-up handler.

### H.2 What happens at month 7

Stripe internally advances the schedule from Phase 1 → Phase 2 at the `end_date` of Phase 1. This fires `customer.subscription.schedule.updated` with the schedule object showing `current_phase.start_date` matching Phase 2's start time.

The webhook handler (`handle_subscription_schedule_updated()`) detects Phase 2 activation via `current_phase_index == 1` and:
1. Moves tenant to `starter` tier
2. Sets `billing_interval = 'monthly'` on subscription row
3. Clears `trial_ends_at` (insurance — should already be cleared)
4. No manual Tom action required

### H.3 If the founders tenant never adds a payment method

The schedule will advance to Phase 2 but the Stripe subscription will fail payment (no payment method). Stripe's standard dunning process kicks in: `invoice.payment_failed` → `past_due` → eventually `canceled`. The existing dunning webhook handler covers this.

**Recommendation**: Add payment method collection to the founders sign-up flow. When a founder enters card details "to save for after the free period", `create_founders_subscription_schedule()` is called at that point. If they don't add a card, the schedule is still created but Phase 2 fails. Tom is notified via the existing `past_due` webhook.

This is a UX decision — not a service layer decision. It does not block STRIPE-B1.

### H.4 Edge case: founder cancels during free period

Tom goes to Stripe Dashboard → finds the customer → cancels or releases the Subscription Schedule. This removes the Phase 2 billing activation. Tom also sets the tenant's `subscription.is_active = false` via direct SQL or future admin UI.

---

## I. Pattern Reuse Decisions

| `mvp-arch.md` §16 Pattern | Applied how |
|---|---|
| **Idempotency** | `ON CONFLICT DO NOTHING` on all DB writes; webhook dedup via `stripe_webhook_event_processed` table (already in place) |
| **Webhook upsert pattern** | `handle_subscription_schedule_updated()` follows the existing upsert pattern from `handle_subscription_created()` — find tenant by `stripe_customer_id`, update rows, commit |
| **`/test` endpoint bypass** | `TestUserContext` path in `_convert_from_trial_impl()` and `_change_tier_impl()` must continue to bypass Stripe calls — no changes needed there, just verify the mocks pass after route schema changes |
| **RFC 7807 error shape** | All new `HTTPException` raises in route file use the Problem Details dict format |

---

## J. Open Questions Resolved

| Question | Decision |
|---|---|
| Where is the founders sign-up entry point? | Engineer locates via grep — `create_founders_subscription_schedule()` wired in there. |
| What if `stripe_price_id_annual` is NULL for annual billing request? | Return `400 Bad Request` with clear message: "annual billing not yet configured — use monthly billing". This is the correct behavior while Tom is still creating annual Stripe prices. |
| Should `_upgrade_tenant_subscription_impl()` support annual billing? | No — `upgrade` is the free tier / founders path (no Stripe charge). Annual billing only applies to `convert-from-trial` and `change-tier` which involve real Stripe charges. |
| Does `billing_interval` need to be added to `SubscriptionUpgradeRequest`? | No. Upgrade handles free tiers only. |
| Should the founders Phase 1 use empty items `[]` or a $0 price object? | Empty items `[]` — Stripe accepts this for a schedule phase with no charge. Simpler than creating a $0 price object in the Dashboard. |
| What Stripe plan does founders Phase 2 use — monthly or annual? | Monthly (`stripe_price_id_monthly`). The founders deal is "locked at $49/mo forever" — not annual billing. The billing cadence is monthly. |

---

## Reference: Pre-Migration DB State (2026-07-14)

| Table | Column | State Before STRIPE-B1 |
|---|---|---|
| `subscription` | `stripe_schedule_id` | ❌ Does not exist |
| `subscription_tier` | `stripe_price_id_monthly` | ✅ Set for starter + teams (test mode IDs) |
| `subscription_tier` | `stripe_price_id_annual` | ⚠️ NULL — Tom creates annual prices in Stripe Dashboard |
| `subscription_tier` | `annual_price_cents` | ✅ 4900/14900 |
| `subscription_tier` | `monthly_price_cents` | ✅ 5900/17900 |
