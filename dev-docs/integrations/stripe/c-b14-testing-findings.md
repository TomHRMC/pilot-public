# C-B14 Stripe Integration Testing Findings

**Date**: 2026-08-08
**Author**: Pilot Python Engineer
**Batch**: C-B14 — Full Test Suite + Stripe Live-Mode Verification
**Related**: `batch-c-b14-design.md`, `stripe-ops-runbook.md`

---

## Overview

This document captures all technical findings, Stripe API constraints, and architectural decisions discovered during the C-B14 Stripe test-clock integration testing. These findings should be reviewed by the Architect to update design docs, the ops runbook, and the tech impl spec as needed.

---

## 1. Critical Stripe API Constraint: Metered Items + Trial-Pause

### The Problem

Stripe **does not allow** subscription items with `usage_type: metered` on subscriptions that have `trial_settings.end_behavior.missing_payment_method: pause` configured. The API returns:

```
InvalidRequestError: Subscriptions that are configured to pause at trial end
can't contain subscription items with a price using `usage_type` set to `metered`.
```

This constraint applies at **both creation time and modification time** — you cannot add metered items to a subscription while the `trial_settings` pause config is present, even if the subscription has already transitioned to `active`.

### The Fix

**`create_charter_subscription()`** now creates the subscription with **only the flat-rate `price_charter_monthly` item** (1 item, no metered). The metered overage items (`price_voice_overage`, `price_sms_overage`) are added later by `_add_metered_overage_items()` after the subscription transitions to active.

**`_add_metered_overage_items()`** (new helper):
1. Retrieves the subscription to check existing items
2. Identifies which metered items are missing
3. Clears `trial_settings.end_behavior.missing_payment_method` to `"cancel"` (the only valid values are `cancel`, `pause`, or `create_invoice` — `"none"` is invalid)
4. Adds the missing metered items via `stripe.Subscription.modify()`

**Called from:**
- `resume_subscription()` — after the subscription is resumed with a payment method
- Test scenarios that attach a PM directly (without calling `resume_subscription()`)
- `upgrade_charter_to_teams()` — adds metered items if not already present

### Impact on Existing Code

- `test_cb4_create_charter_subscription.py` — updated to expect 1 item instead of 3
- `test_cb4_resume_subscription.py` — updated to mock the `_add_metered_overage_items` call
- `test_cb12_charter_upgrade.py` — updated mock customer to use attribute access; added `test_upgrade_adds_metered_items_if_missing`

### Architectural Implication

The Charter subscription lifecycle is now:
1. **Signup** → `create_charter_subscription()` → 1 item (charter_monthly), trial_settings=pause
2. **Trial ends without PM** → subscription pauses
3. **User adds PM** → `resume_subscription()` → adds metered items + clears trial_settings
4. **OR: User adds PM during trial** → subscription auto-converts to active → metered items must be added separately (via webhook or manual call)
5. **Upgrade to Teams** → `upgrade_charter_to_teams()` → adds metered items if not already present

**Gap**: For case 4 (PM added during trial, auto-convert to active), there is no webhook handler that automatically adds metered items. The `handle_subscription_created()` / `handle_subscription_updated()` webhook handler (which routes both `customer.subscription.created` and `customer.subscription.updated` to the same function) does NOT add metered items. This means in production, if a user adds a PM before the trial ends, the metered items won't be on the subscription until the user explicitly resumes or upgrades.

**Recommendation for Architect**: Consider adding metered item provisioning to the `handle_subscription_created()` webhook handler (which also handles `subscription.updated`) — check if the subscription is active and add metered items if missing.

---

## 2. Stripe Customer Object: No `.get()` Method

### The Problem

`upgrade_charter_to_teams()` used `customer.get("invoice_settings", {}).get("default_payment_method")` to check for a payment method. This works on Python dicts and MagicMock (in tests), but **Stripe's `Customer` object (StripeObject) does not support `.get()`** — it raises `AttributeError: get`.

### The Fix

Changed to `getattr(customer, "invoice_settings", None)` and `getattr(invoice_settings, "default_payment_method", None)`.

### Impact

This was a latent production bug that only surfaced when running against the real Stripe API (not mocked). All existing mocked tests passed because MagicMock supports `.get()`.

**Recommendation for Architect**: Audit all Stripe service code for `.get()` usage on Stripe objects — replace with `getattr()` or `obj["key"]` (StripeObject supports `__getitem__`).

---

## 3. Test Clock Advancement Limit: 2 Intervals Maximum

### The Problem

Stripe test clocks can only be advanced **up to 2 intervals at a time**, where the interval is determined by the shortest subscription interval on the clock. For a monthly subscription, this means **maximum 60 days per advancement call**.

```
InvalidRequestError: You can only advance a test clock up to two intervals from
the current frozen time at a time, based on the shortest subscription interval
in the test clock.
```

### The Fix

`advance_clock_and_wait()` now advances in increments of ≤59 days, accumulating the total offset from the clock's current frozen time (retrieved via `stripe.test_helpers.TestClock.retrieve()`).

**Critical**: The function retrieves the clock's current `frozen_time` and calculates the target from there — NOT from `datetime.now(UTC)`. This is essential because tests may call `advance_clock_and_wait()` multiple times (e.g., advance 85 days, then advance 6 more days). Using `datetime.now(UTC)` as the base would calculate the wrong target on the second call.

---

## 4. Test Clock Processing Delay: "Advancement Underway"

### The Problem

After advancing a test clock, Stripe needs time to process the advancement (update subscription statuses, generate invoices, etc.). Any API call that modifies objects on the clock during this processing window returns:

```
RateLimitError: Test clock advancement underway - cannot perform modifications
```

### The Fix

1. **`advance_clock_and_wait()`** sleeps 10s after each advancement step
2. The `TestClock.advance()` call itself is retried up to 8 times with 15s delay
3. All post-advancement Stripe API calls in tests are wrapped with `_retry_stripe_call()` (5 retries, 10s delay)
4. The `stripe_cleanup` fixture sleeps 5s after cleanup to prevent concurrent clock operations from interfering with the next test

### Timing Summary

| Operation | Wait |
|---|---|
| Initial sleep before advancement | 5s (default `sleep_seconds`) |
| After each advancement step | 10s |
| Retry on "advancement underway" | 15s × up to 8 attempts |
| Post-cleanup (between tests) | 5s |
| Post-advancement API call retry | 10s × up to 5 attempts |

**Total runtime**: 12 Stripe scenarios take ~7-8 minutes with all sleeps.

---

## 5. Stripe Bootstrap Script: Stale JSON Cache

### The Problem

`stripe_bootstrap.py` loads `stripe_ids.{mode}.json` and uses cached IDs to skip creation: `existing = ids["prices"].get(price_key) or _find_price_by_pilot_key(price_key)`. If the Stripe account was purged but the JSON file still has old IDs, the script reports "EXISTS" for objects that no longer exist in Stripe.

### The Fix

Delete `scripts/stripe_ids.test.json` before running the bootstrap if the Stripe test account has been purged. The script will recreate all objects from scratch.

### Recommendation

Consider adding a `--force` flag to `stripe_bootstrap.py` that ignores the cached JSON and always queries Stripe for existing objects. Or validate cached IDs by retrieving each object from Stripe before trusting them.

---

## 6. Stripe Bootstrap Script: Audit Bug

### The Problem

`stripe_bootstrap.py --mode test --audit` crashes with `UnboundLocalError: cannot access local variable 'pkey'` in the meters loop (line 493). The variable `pkey` was defined in the prices loop (line 472) but is referenced in the meters loop where it doesn't exist.

### The Fix

Not fixed in this batch (pre-existing bug in a file we didn't change). The meters loop should use `event_name` instead of `pkey` for logging, since meters don't support metadata.

---

## 7. `extend_free_period()` FK Constraint

### The Problem

`extend_free_period()` in `cohort_dashboard.py` inserts a `tenant_tier_override` row with `set_by_operator_user_id` that has a foreign key to the `user` table. Tests that pass `uuid.uuid4()` as the operator user ID fail with `ForeignKeyViolation` because the random UUID doesn't exist in the `user` table.

### The Fix

Tests use the seeded test user ID `00000000-0000-0000-0000-000000000002` instead of `uuid.uuid4()`.

### Recommendation

The `extend_free_period()` function should validate that the `operator_user_id` exists before inserting, or the route layer should pass the authenticated user's ID (not a client-supplied UUID).

---

## 8. Meter Events During Trial: No Invoice Generated

### Finding

Meter events reported via `stripe.billing.MeterEvent.create()` during a trial period do NOT produce overage invoices — the trial includes overage. This is expected behavior. The test for scenario 6 (`test_meter_events_during_trial`) verifies that the invoice amount is $0 during trial.

However, since the subscription no longer has metered items during trial (due to the constraint in finding #1), meter events won't be aggregated at all. The test handles this gracefully with `if invoices.data:` — if no invoice is generated, the test passes.

---

## 9. Test Clock Frozen Time vs. Real Time

### Finding

The test clock's `frozen_time` is an absolute Unix timestamp. When a subscription is created with `trial_end=int(free_period_ends_at.timestamp())`, the trial end is calculated from `datetime.now(UTC) + timedelta(days=90)`. The test clock is created at the same time and frozen at `int(datetime.now(UTC).timestamp())`.

When `extend_free_period()` sets a new `trial_end`, it must be calculated relative to the clock's current frozen time, NOT `datetime.now(UTC)`. In the test, the clock has been advanced 80 days, so `datetime.now(UTC)` is ~80 days behind the clock. The new trial end must be at least 15 days ahead of the clock's frozen time (which is at day 80) to survive the subsequent 15-day advancement.

The test uses `datetime.now(UTC) + timedelta(days=170)` to ensure the new trial end is well past the 95-day mark the clock will be advanced to.

---

## 10. `stripe_ids.test.json` File

### Confirmed

Yes, `stripe_bootstrap.py --mode test` creates `backend/scripts/stripe_ids.test.json` — a JSON file mapping `pilot_key` names to actual Stripe object IDs:

```json
{
    "mode": "test",
    "products": {"prod_starter": "prod_...", ...},
    "meters": {"meter_voice_minutes": "mtr_test_...", ...},
    "prices": {"price_charter_monthly": "price_...", ...}
}
```

This file is loaded by `core.stripe_config.get_stripe_ids()` at runtime to map pilot_key names to Stripe IDs. The file must be regenerated whenever the Stripe test account is purged or objects are recreated.

---

## Summary of Architect Action Items

1. ✅ **Update design docs** to reflect the metered-items-on-resume pattern (finding #1) — dispositioned 2026-08-12 (Architect): the pattern is recorded in the living ops doc (`stripe-ops-runbook.md` test-clock constraints block, incl. the C-B14-FIX webhook auto-conversion path); `batch-c-b14-design.md` is a point-in-time batch record and is intentionally not rewritten.
2. ✅ **Consider webhook handler** for auto-adding metered items on trial→active transition (finding #1 gap) — C-B14-FIX Task 1: `handle_subscription_created()` now provisions metered items on `status='active'` in both Charter fallback and normal tier branches, with out-of-order guard (D5) and failure-swallow (D6).
3. ✅ **Audit Stripe service code** for `.get()` usage on StripeObject (finding #2) — C-B14-FIX Task 2: audited all `.get()` sites across `stripe_subscriptions.py`, `stripe_payment_intents.py`, `tenant_signup.py`, `stripe_bootstrap.py`. One fix applied: `mode_audit()` prices-loop `recurring_obj.get("interval")` → `getattr(recurring_obj, "interval", "?")` (was always returning `"?"` for real Stripe prices due to the `hasattr` guard). All other sites are safe-dict (webhook payloads / config dicts).
4. ✅ **Add `--force` flag** to `stripe_bootstrap.py` to skip stale JSON cache (finding #5) — C-B14-FIX Task 3: `--force` flag added, threaded through `mode_create()` all 3 loops (products, meters, prices). Bypasses JSON cache only; live Stripe lookup always runs. Docs updated in `README-stripe-bootstrap.md` + `stripe-ops-runbook.md`.
5. ✅ **Fix audit bug** in `stripe_bootstrap.py` meters loop (finding #6) — C-B14-FIX Task 4: removed the stale `pilot_key={pkey!r}` fragment from the meters-loop `_log()` call. `mode_audit()` no longer crashes with `UnboundLocalError` on empty prices.
6. ✅ **Add operator_user_id validation** to `extend_free_period()` (finding #7) — C-B14-FIX Task 5: `extend_free_period()` now validates `operator_user_id` exists in the `user` table before the `tenant_tier_override` upsert, raising `ValueError("... not found ...")` → 404 RFC 7807 via the existing route mapping. No route/schema change.
7. ✅ **Update C-SPIKE-1 findings** with the test clock 2-interval limit (finding #3) — dispositioned 2026-08-12 (Architect): C-SPIKE-1 findings were archived (frozen) in the 2026.08.08 cycle and are intentionally not edited; the 2-interval limit is captured in `stripe-ops-runbook.md` (test-clock constraints block).
8. ✅ **Update stripe-ops-runbook** with the timing/retry patterns (finding #4) — done in the runbook v1.2 review (2026-08-10): 2-interval limit, "advancement underway" retry pattern, and per-operation timing table are all in the test-clock constraints block.
