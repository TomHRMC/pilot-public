# C-B7 — Entitlements: Paused-State Service Block + Charter Entitlement Resolution

**Batch**: C-B7
**Mode**: Pilot Python Engineer
**Prerequisite**: C-B4 ✅ (Stripe subscription lifecycle + `handle_subscription_paused`)
**Source of truth**: `pilot-tech-impl-spec-v1.md` §9.1-9.3 — **§9.3 SMS exception OVERRIDDEN by Tom (2026-08-05)**
**Status**: Design complete — ready for prompt authoring
**Date**: August 5, 2026

---

## Overview

C-B7 implements the Charter entitlement enforcement rules. Three scope items:

1. **D11 (data export to all plans)**: **Already done** — `data_exports` product_feature was deleted in SD-07/MKT-B11. Data exports are unlimited and untracked on all plans. No code change needed.

2. **Paused-state service block (§9.3 — OVERRIDDEN)**: The spec §9.3 originally proposed an SMS exception when `tenant_messaging_registration.status = 'active'`. **Tom overrode this decision on 2026-08-05**: when a subscription is paused, the tenant is not paying, and ALL services including SMS must be blocked. Allowing SMS creates costs Pilot is liable for, and once the tenant exceeds plan overage, they're charged in addition to the monthly fee. **No SMS exception — when paused, everything is blocked.**

3. **Q#6 (data retention)**: Resolved as "Standard for now" — no special retention logic needed. No code change.

**Net scope**: Item #2 requires adding a billing-active check to the SMS send path to BLOCK SMS when the subscription is paused. The existing `enforce_paywall()` only checks trial expiration — there is no billing-active check for non-trial tenants. C-B7 adds this check.

---

## A. Input Read Summary

| Input | Sections read | Key takeaways |
|---|---|---|
| `pilot-tech-impl-spec-v1.md` | §9.1 (D11), §9.2 (Charter = Starter entitlements), §9.3 (paused-state service block — **SMS exception OVERRIDDEN by Tom 2026-08-05**) | D11 already done. Charter resolves to exactly Starter entitlement set — no parallel Charter path. **§9.3 SMS exception overridden**: when paused → ALL services including SMS blocked, no exceptions. Blocked while paused: job/quote/invoice creation, voice AI, new customer creation, SMS. Allowed: all reads, data export, payment method addition. |
| `data_export_pipeline.py` | Line 111 | "MKT-B11: data_exports feature code deleted — data exports are now unlimited and untracked. Usage ledger write removed entirely. No entitlement check needed." D11 is done. |
| `sms_quota.py` | `check_quota()` function | Checks customer opt-out + quota limits. Does NOT check subscription billing status. SMS sending is gated by quota, not by billing status. |
| `trial_management.py` | `enforce_paywall()` | Only checks trial expiration (`check_trial_expired`). Does NOT check subscription `is_billing_active`. The paywall for paused subscriptions is not yet implemented as a middleware/dependency. |
| `stripe_subscriptions.py` | `handle_subscription_paused()` (C-B4) | Sets subscription status to `paused` (`is_billing_active=false`). Comment says "Entitlement enforcement handled by existing is_billing_active paywall" — but no such paywall check exists for non-trial tenants. |
| Live DB — `tenant_messaging_registration` | MCP (C-B4 session) | `status` column exists (TEXT). Values: `quoting`, `brand_submitted`, `active`, etc. (C-B9 will define the full state machine). |
| Live DB — `subscription_status` | MCP (C-B4 session) | `paused` code exists with `is_billing_active=false`. |

---

## B. Migration Plan

**No migration needed.** All columns exist:
- `tenant_messaging_registration.status` (C-B2 ✅)
- `subscription_status` `paused` code (seeded ✅)
- `subscription.status_id` FK (B14 ✅)

---

## C. Execution Order

| # | Task | File(s) |
|---|---|---|
| 1 | Create `is_subscription_billing_active()` check function in `entitlement_service.py` — checks subscription status `is_billing_active` | `backend/services/entitlement_service.py` |
| 2 | Integrate the check into the SMS send path — BLOCK SMS when subscription is paused/unpaid/canceled | `backend/services/sms_quota.py` or `backend/services/customer_comms_service.py` (verify which file gates the send) |
| 3 | Write unit tests for the billing-active check | `backend/tests/domains/notifications_comms/` |
| 4 | Run ruff + full test suite (Phase 2) | — |

---

## D. New API Endpoints

**No new endpoints.** C-B7 is a service-layer change only.

---

## E. Pattern Reuse Decisions

| Pattern | How it applies |
|---|---|
| **Entitlement check** (existing) | The existing `entitlement_service.py` has `check_entitlement()` and `get_cached_entitlement()`. C-B7 adds a new `is_sms_allowed_while_paused()` function that checks the subscription status + messaging registration. |
| **Sync routes** (Rule §21) | All new code is `def` — no `async def`. |

---

## F. Shared Module Interfaces

### services/entitlement_service.py — New Function

```python
def is_subscription_billing_active(db: Session, tenant_id: UUID) -> bool:
    """
    Check whether the tenant's subscription is billing-active.

    Returns False when the subscription status is 'paused', 'unpaid', or 'canceled'
    (is_billing_active=false on the subscription_status row). Returns True for
    'active', 'trialing', 'past_due' (is_billing_active=true).

    When False, ALL services are blocked — including SMS. The tenant is not paying
    for their subscription, and allowing SMS creates costs Pilot is liable for.

    Returns:
        True if subscription is billing-active, False otherwise.
    """
    from app.models.billing import Subscription, SubscriptionStatus

    # Find the tenant's active subscription
    sub = db.exec(
        select(Subscription)
        .where(Subscription.tenant_id == tenant_id)
        .where(Subscription.is_active == True)
    ).first()

    if not sub:
        return False  # No active subscription

    # Look up the subscription status
    status = db.exec(
        select(SubscriptionStatus).where(SubscriptionStatus.id == sub.status_id)
    ).first()

    if not status:
        return False

    return status.is_billing_active
```

### Integration Point

The SMS send path must call `is_subscription_billing_active()` and BLOCK SMS when it returns False. The exact integration point depends on where the SMS send is gated. Based on the code analysis:

- `sms_quota.check_quota()` checks customer opt-out + quota limits — does NOT check billing status
- The SMS send route (in `customer_comms_service.py` or the communications API route) calls `check_quota()` but does not check billing status

**The engineer must** `read_file` on the SMS send route and `customer_comms_service.py` to find where to add the billing-active check. The check should be added early in the send path — before `check_quota()` or alongside it. If billing-active is False, return a blocked result with reason `"subscription_paused"`.

**Tom's decision (2026-08-05)**: When a subscription is paused, NO services are allowed — including SMS. The spec §9.3 SMS exception (allowing SMS when `tenant_messaging_registration.status = 'active'`) is **overridden**. Allowing SMS creates costs Pilot is liable for, and once the tenant exceeds plan overage, they're charged in addition to the monthly fee. The Telnyx brand/campaign being theirs does not override this — they can resume the subscription to re-enable SMS.

---

## G. Open Questions Resolved

| Question | Resolution | Source |
|---|---|---|
| **D11 (data export to all plans)** | **Already done.** `data_exports` product_feature deleted in SD-07/MKT-B11. Data exports are unlimited and untracked. No code change. | `data_export_pipeline.py` |
| **Q#6 (data retention window)** | **Standard for now.** No special retention logic. Revisit if Charter members request longer retention. | Spec Q#6 resolution |
| **Charter = Starter entitlements (§9.2)** | Charter resolves to exactly the Starter entitlement set. No parallel Charter entitlement path. The only Charter-specific behaviors are: `free_period_ends_at`, `charter_member_number`, `price_locked`, and the paused-state service block (§9.3 — SMS exception overridden, ALL services blocked when paused). | Spec §9.2 |
| **Where does the paywall block SMS?** | The existing `enforce_paywall()` only checks trial expiration. There is no billing-active middleware for non-trial tenants. SMS sends are gated by `sms_quota.check_quota()` (customer opt-out + quota), not by billing status. **C-B7 adds the billing-active check to the SMS send path to BLOCK SMS when paused.** | Code analysis |
| **Spec §9.3 SMS exception OVERRIDDEN** | Tom decided (2026-08-05) that when a subscription is paused, ALL services including SMS are blocked. The spec §9.3 proposed allowing SMS when `tenant_messaging_registration.status = 'active'`, but this creates costs Pilot is liable for. No exception — when paused, everything is blocked. The tenant can resume their subscription to re-enable SMS. | Tom decision 2026-08-05 |
