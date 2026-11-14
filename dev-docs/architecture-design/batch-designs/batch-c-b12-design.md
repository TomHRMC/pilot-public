# C-B12 — Charter → Teams Upgrade Flow + Forfeiture Warning Modal

**Batch**: C-B12
**Mode**: Pilot Python Engineer (Part A) → Pilot Web UI Designer → Pilot React Engineer (Part B)
**Prerequisite**: C-B4 ✅ (Stripe subscription lifecycle + webhook handlers)
**Source of truth**: `pilot-tech-impl-spec-v1.md` §6.7 (Charter → Teams Upgrade), §6.6 (Charter Member Badge), §4.5 (Price Lock)
**Status**: Design — Tom approved approach 2026-08-07 (billing interval = user choice, Charter rate forfeited permanently)
**Date**: August 7, 2026

> **Tom decision (2026-08-07)**: Charter members can stay on the Charter rate ($49/mo, Starter features, monthly billing, locked) forever, as long as they don't cancel. When they outgrow Starter and want Teams, they upgrade and become a "regular" customer — they choose their billing interval (monthly $179/mo or annual $149/mo effective). The Charter rate is gone for good (`charter_eligible = False` permanently), even if they later downgrade back to Starter. The forfeiture modal must show both Teams pricing options, not just "$149/mo" as the spec §6.7 copy currently states.

---

## Overview

C-B12 builds the Charter → Teams upgrade flow — the self-service path for a Charter member to voluntarily give up their locked $49/mo rate and move to the Teams plan at standard pricing.

The flow has two halves:

1. **Backend (Part A — Python Engineer)**: A dedicated `POST /api/v1/tenants/{tenant_id}/subscription/upgrade-from-charter` endpoint that performs the Stripe subscription modification (delete Charter item, add Teams item, end trial if active, prorate) and permanently flips `tenant.charter_eligible = False`. This is **separate from the existing generic `change-tier` endpoint** because the Charter flow has unique logic: item deletion + addition (not price replacement), `charter_eligible` forfeiture, trial-end, and billing interval selection.

2. **Frontend (Part B — React Engineer)**: A blocking forfeiture warning modal (§16.7 preview-before-send) triggered from the billing settings page. The modal shows both Teams pricing options (monthly $179/mo, annual $149/mo effective), a billing interval selector, and a safe default = "Keep my Charter rate" (Cancel button). On confirm, calls the new endpoint. Requires a UI design spec from the pilot-web-ui-designer (Rule 1.5 gate).

### Key Design Decision: Dedicated Endpoint vs. Extending `change-tier`

The existing `_change_tier_impl()` in `tenant_subscription.py` calls `stripe.Subscription.modify(sub_id, items=[{"price": selected_price_id}])` — this **adds** a new item without deleting the old one, resulting in the customer being billed for both Charter AND Teams simultaneously. It also does not flip `charter_eligible`, does not end the trial, and does not use `proration_behavior`.

C-B12 creates a **dedicated endpoint** (`upgrade-from-charter`) because:
1. The Stripe item operation is fundamentally different: delete the Charter item + add the Teams item (not replace-all)
2. The `charter_eligible = False` forfeiture is a permanent business rule that must not be applied to generic tier changes
3. The trial-end logic (`trial_end="now"`) is Charter-specific (a Charter member in trial who upgrades should exit the trial immediately)
4. The billing interval choice (monthly vs. annual) is presented in the forfeiture modal, not in the generic tier picker

---

## A. Input Read Summary

| Input | Source | Key findings |
|---|---|---|
| Spec §6.7 — Charter → Teams Upgrade | `pilot-tech-impl-spec-v1.md` §6.7 | `stripe.Subscription.modify(sub_id, items=[{"id": charter_item_id, "deleted": True}, {"price": teams_price_id, "quantity": 1}], proration_behavior="create_prorations")` then `tenant.charter_eligible = False`. Blocking forfeiture modal, safe default = keep Charter rate. **Spec copy says "$149/mo" — Tom clarified this should show both monthly ($179) and annual ($149 effective) options.** |
| Spec §6.6 — Charter Member Badge | Same, §6.6 | Dashboard renders badge + "Your rate: $49/mo — locked". `price_locked` flag triggers the forfeiture warning modal in the Upgrade UI. |
| Spec §4.5 — Price Lock | Same, §4.5 | Charter subscriptions excluded from price migrations via `WHERE price_locked = false`. Archived prices continue billing existing subscriptions. The lock is operational discipline + one WHERE clause. |
| Spec §4.2 — Tier Pricing | Same, §4.2 | Charter: $49/mo (locked, monthly only). Starter: $59/mo monthly / $588/yr annual ($49/mo effective). Teams: $179/mo monthly / $1,788/yr annual ($149/mo effective). |
| Live DB — `subscription` table | MCP (this session) | 21 columns. Key: `psp_subscription_id` (VARCHAR, nullable), `status_id` (UUID FK), `is_active` (BOOLEAN), `product_plan_code` (VARCHAR, NOT NULL), `billing_interval` (VARCHAR, NOT NULL, default 'monthly'), `trial_ends_at` (TIMESTAMPTZ, nullable), `tenant_id` (UUID FK). |
| Live DB — `tenant` table | MCP (this session) | Has `charter_eligible` (BOOLEAN, NOT NULL, default true), `charter_member_number` (INTEGER, nullable), `free_period_ends_at` (TIMESTAMPTZ, nullable), `current_subscription_tier_id` (UUID FK), `stripe_customer_id` (TEXT, nullable). |
| Live DB — `subscription_tier` table | MCP (this session) | 4 tiers: `charter` ($49/mo, `price_locked=true`, `is_active=true`, `stripe_price_id_monthly=price_REDACTED...`), `trial` (inactive), `starter` ($59/mo monthly, $588/yr annual, inactive), `teams` ($179/mo monthly, $1788/yr annual, inactive, `stripe_price_id_monthly=price_REDACTED...`, `stripe_price_id_annual=price_REDACTED...`). |
| Live DB — `subscription_status` table | MCP (this session) | 6 codes: `active` (is_billing_active=true), `canceled` (false), `past_due` (true), `paused` (false), `trialing` (true), `unpaid` (false). |
| Existing code — `create_charter_subscription()` | `backend/services/stripe_subscriptions.py` | Creates Charter subscription with **3 items**: `price_charter_monthly` (quantity=1) + `price_voice_overage` (metered) + `price_sms_overage` (metered). Uses `trial_end` + `trial_settings.end_behavior.missing_payment_method: pause`. The upgrade must delete only the charter_monthly item and keep the metered items. |
| Existing code — `_change_tier_impl()` | `backend/api/routes/tenant_subscription.py` | Generic tier change. Calls `stripe.Subscription.modify(sub_id, items=[{"price": selected_price_id}])` — **adds** a new item without deleting the old one. Does NOT flip `charter_eligible`, does NOT end trial, does NOT use `proration_behavior`. **Not suitable for Charter → Teams.** |
| Existing code — `handle_subscription_deleted()` | `backend/services/stripe_subscriptions.py` | Already sets `tenant.charter_eligible = False` on subscription deletion (D22). C-B12 applies the same flip on upgrade (D23) — but in the service function, not a webhook handler. |
| Existing code — `stripe_config.py` | `backend/core/stripe_config.py` | `get_stripe_ids()` returns dict with `prices.price_teams_monthly` + `prices.price_teams_annual`. |
| Existing code — `stripe_ids.test.json` | `backend/scripts/stripe_ids.test.json` | All 9 price IDs present: `price_charter_monthly`, `price_starter_monthly`, `price_starter_annual`, `price_teams_monthly`, `price_teams_annual`, `price_voice_overage`, `price_sms_overage`, `price_lane_addon_1`, `price_lane_addon_5`. |
| Existing code — `BillingSettingsPage.tsx` | `frontend/apps/web/src/features/settings/components/BillingSettingsPage.tsx` | Shows "Upgrade plan" button for `isTrial || tierName === "starter"`. Charter tier is NOT included — no upgrade CTA for Charter members today. Tier picker modal has **stale hardcoded "Pro" and "Growth" tiers** (lines 137-140) — these are legacy and need replacement. |
| Existing code — `useTenantSubscription.ts` | `frontend/apps/web/src/features/settings/hooks/useTenantSubscription.ts` | TQ v5 hook. `changeTier` mutation calls `POST /change-tier`. C-B12 adds `upgradeFromCharter` mutation calling the new endpoint. |
| Existing code — `CharterMemberBadge.tsx` | `frontend/apps/web/src/features/dashboard/components/CharterMemberBadge.tsx` | Dashboard badge showing "Charter Member #N" + "Free until {date}". Owner-only (RoleGate). C-B12 does NOT modify this — the badge stays as informational. The upgrade CTA lives on the billing settings page. |
| mvp-arch §16 | `mvp-arch.md` §16 | Platform patterns: always-preview-before-send (§16.7) — the forfeiture modal shows the new rate + billing interval before the user confirms. Four-class severity — the modal is a destructive confirmation (forfeiture is irreversible). |

---

## B. Migration Plan

### B.1 — DB Changes

**No migration needed.** All required columns already exist:
- `tenant.charter_eligible` — from C-B2 (BOOLEAN, NOT NULL, default true)
- `tenant.charter_member_number` — from C-B2 (INTEGER, nullable)
- `tenant.free_period_ends_at` — from C-B2 (TIMESTAMPTZ, nullable)
- `tenant.current_subscription_tier_id` — pre-existing (UUID FK)
- `tenant.stripe_customer_id` — pre-existing (TEXT, nullable)
- `subscription.product_plan_code` — pre-existing (VARCHAR, NOT NULL)
- `subscription.billing_interval` — pre-existing (VARCHAR, NOT NULL, default 'monthly')
- `subscription.trial_ends_at` — pre-existing (TIMESTAMPTZ, nullable)
- `subscription.status_id` — pre-existing (UUID FK)
- `subscription_tier.stripe_price_id_monthly` — pre-existing
- `subscription_tier.stripe_price_id_annual` — pre-existing

**No new table.** The upgrade is a write action on existing tables + a Stripe API call.

### B.2 — MCP Verification Queries (pre-implementation)

```sql
-- 1. Verify tenant has Charter-related columns
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'tenant'
  AND column_name IN ('charter_eligible', 'charter_member_number', 'free_period_ends_at',
                      'current_subscription_tier_id', 'stripe_customer_id')
ORDER BY ordinal_position;

-- 2. Verify subscription has product_plan_code + billing_interval + trial_ends_at + status_id
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'subscription'
  AND column_name IN ('psp_subscription_id', 'status_id', 'is_active', 'product_plan_code',
                      'billing_interval', 'trial_ends_at', 'tenant_id', 'psp_customer_id')
ORDER BY ordinal_position;

-- 3. Verify subscription_tier has Teams price IDs
SELECT tier_name, monthly_price_cents, annual_price_cents,
       stripe_price_id_monthly, stripe_price_id_annual, is_active, price_locked
FROM subscription_tier WHERE tier_name IN ('charter', 'teams') ORDER BY tier_name;

-- 4. Verify subscription_status codes
SELECT code, name, is_billing_active FROM subscription_status ORDER BY code;

-- 5. Verify subscription row for a Charter tenant (if seed data exists)
SELECT s.psp_subscription_id, s.status_id, s.product_plan_code, s.billing_interval,
       s.is_active, s.trial_ends_at, st.code as status_code, t.charter_eligible
FROM subscription s
JOIN subscription_status st ON s.status_id = st.id
JOIN tenant t ON s.tenant_id = t.id
WHERE t.charter_eligible = true
LIMIT 5;
```

### B.3 — Pre-Implementation State

- `tenant`: has all Charter columns from C-B2
- `subscription`: has `product_plan_code`, `billing_interval`, `trial_ends_at`, `status_id`
- `subscription_tier`: Charter tier active with `price_locked=true`; Teams tier inactive with both monthly + annual Stripe price IDs
- `subscription_status`: 6 codes (active, trialing, paused, canceled, past_due, unpaid)
- `stripe_ids.test.json`: all 9 price IDs present
- No existing Charter → Teams upgrade endpoint

### B.4 — 3-Part NOT NULL Pattern

Not applicable — no new columns.

### B.5 — Audit Columns

Not applicable — no new table.

### B.6 — Seed Data Rollout

Not applicable — no new seed data. The tier rows and Stripe price IDs already exist from C-B2/C-B3.

---

## C. Execution Order

| # | Task | Files | Description |
|---|---|---|---|
| 1 | Upgrade service function | `backend/services/stripe_subscriptions.py` | Add `upgrade_charter_to_teams()` — retrieves subscription, finds Charter item ID, calls `stripe.Subscription.modify()` (delete Charter item + add Teams item + `trial_end="now"` + `proration_behavior`), flips `charter_eligible=False`, updates `tenant.current_subscription_tier_id`, nulls `free_period_ends_at`, updates `subscription` row. |
| 2 | Request/response schemas | `backend/api/schemas/subscription.py` (or inline in route) | `UpgradeFromCharterRequest` (billing_interval), `UpgradeFromCharterResponse` (psp_subscription_id, new_tier_name, billing_interval, charter_eligible_forfeited). |
| 3 | API route | `backend/api/routes/tenant_subscription.py` | Add `POST /{tenant_id}/subscription/upgrade-from-charter` + `/test` twin. RBAC: `subscription.tier.change`. |
| 4 | OpenAPI regen | — | `python export_openapi_json.py` — 1 new endpoint (+ test twin). |
| 5 | Tests | `backend/tests/domains/subscriptions_usage/test_cb12_charter_upgrade.py` (NEW) | Unit tests for service function + endpoint tests. |
| 6 | Schema JSON | — | No schema changes. |
| 7 | UI design spec | `dev-docs/architecture-design/batch-designs/batch-c-b12-ui-design-spec.md` | Pilot Web UI Designer authors the forfeiture modal spec. Tom approves before React prompt. |
| 8 | React hook | `frontend/apps/web/src/features/settings/hooks/useTenantSubscription.ts` | Add `upgradeFromCharter` mutation calling `POST /upgrade-from-charter`. |
| 9 | Forfeiture modal | `frontend/apps/web/src/features/settings/components/CharterUpgradeModal.tsx` (NEW) | Blocking modal with billing interval selector + safe default. |
| 10 | Billing settings page | `frontend/apps/web/src/features/settings/components/BillingSettingsPage.tsx` | Add "Upgrade to Teams" CTA for Charter members. Replace stale tier picker. |
| 11 | MSW handlers | `frontend/apps/web/src/mocks/handlers/` | Add handler for `POST /upgrade-from-charter`. |
| 12 | React tests | `frontend/apps/web/src/__tests__/batch_c_b12/` (NEW) | Integration tests for the modal + billing page. |

---

## D. New API Endpoints

### D.1 — `POST /api/v1/tenants/{tenant_id}/subscription/upgrade-from-charter`

**Auth**: `get_current_user()` (tenant-scoped)
**RBAC**: `subscription.tier.change`
**Request**: `UpgradeFromCharterRequest`

```json
{
  "billing_interval": "monthly"
}
```

`billing_interval` is `"monthly"` or `"annual"`. Determines which Teams Stripe price ID is used.

**Response**: `UpgradeFromCharterResponse` (200 OK)

```json
{
  "psp_subscription_id": "sub_...",
  "new_tier_name": "teams",
  "billing_interval": "monthly",
  "charter_eligible_forfeited": true
}
```

**Errors** (all RFC 7807):
- `400` — Tenant is not on the Charter tier (`charter_eligible == false` or `current_subscription_tier_id` is not Charter)
- `400` — No active Stripe subscription found (`subscription.psp_subscription_id` is null or `is_active == false`)
- `400` — No payment method on file (Stripe customer has no `invoice_settings.default_payment_method`). A Charter member in trial with no card cannot upgrade — they must add a card first.
- `404` — Tenant not found (tenant isolation: `tenant_id != current_user.tenant_id`)
- `502` — Stripe API error (subscription modification failed)

### D.2 — `POST /api/v1/tenants/{tenant_id}/subscription/upgrade-from-charter/test`

Test twin — no auth, Stripe bypassed. Returns mock response.

---

## E. Pattern Reuse Decisions

| Pattern | Source | How it applies |
|---|---|---|
| **`_get_stripe_client()`** | C-B4 `stripe_subscriptions.py` | Reuse for `Subscription.modify()` + `Subscription.retrieve()` (to find the Charter item ID). |
| **`get_stripe_ids()`** | C-B4 `core/stripe_config.py` | Load `price_teams_monthly` / `price_teams_annual` IDs. |
| **`set_audit_context_sync()`** | Standard pattern | Called on the endpoint (the tenant user is the actor). |
| **RFC 7807 errors** | Standard pattern | All error responses use Problem Details format. |
| **Always-preview-before-send** (§16.7) | mvp-arch §16.7 | The forfeiture modal shows the new rate + billing interval before the user confirms. The React UI renders a confirmation modal with the exact price change. |
| **Four-class severity** | mvp-arch §16 | The forfeiture modal is a destructive confirmation (forfeiture is irreversible). The modal uses the destructive-confirmation variant: Cancel = safe default (primary button), Confirm = secondary/danger button. |
| **TestUserContext bypass** | Standard pattern | Test endpoint bypasses Stripe API calls, returns mock response. |
| **`handle_subscription_created()` webhook** | C-B4 `stripe_subscriptions.py` | The `customer.subscription.updated` webhook (fired by `Subscription.modify()`) will update the `subscription` row's `product_plan_code` + `billing_interval` via the existing `handle_subscription_created()` upsert logic. C-B12's service function also updates the row directly for immediate consistency. |

---

## F. Shared Module Interfaces

### F.1 — `services/stripe_subscriptions.py` addition

```python
def upgrade_charter_to_teams(
    db: Session,
    tenant_id: uuid.UUID,
    billing_interval: str,
) -> dict:
    """Upgrade a Charter member to the Teams plan.
    
    This is a PERMANENT, IRREVERSIBLE action:
    1. Deletes the Charter monthly item from the Stripe subscription
    2. Adds the Teams item (monthly or annual price based on billing_interval)
    3. Ends the trial immediately (trial_end="now") if the subscription is trialing
    4. Sets proration_behavior="create_prorations" (immediate invoice for the difference)
    5. Flips tenant.charter_eligible = False (permanent — D23)
    6. Updates tenant.current_subscription_tier_id to Teams
    7. Nulls tenant.free_period_ends_at (no longer in free period)
    8. Updates subscription row: product_plan_code, billing_interval, status_id→active
    
    The metered items (voice_overage, sms_overage) are preserved — they are 
    shared across all tiers and should NOT be deleted.
    
    Args:
        db: Database session
        tenant_id: Tenant to upgrade
        billing_interval: "monthly" or "annual"
    
    Returns:
        {"psp_subscription_id", "new_tier_name", "billing_interval", 
         "charter_eligible_forfeited"}
    
    Raises:
        ValueError: tenant is not Charter, no active subscription, 
                    no payment method, or Stripe API error
    """
```

### F.2 — Implementation Detail: Finding the Charter Item ID

The Charter subscription has 3 items: `price_charter_monthly` (quantity=1), `price_voice_overage` (metered), `price_sms_overage` (metered). The upgrade must:

1. `stripe.Subscription.retrieve(sub_id)` to get all items
2. Find the item whose `price.id == ids["prices"]["price_charter_monthly"]`
3. Build the `items` array for `Subscription.modify()`:
   - `{"id": charter_item_id, "deleted": True}` — delete the Charter item
   - `{"price": teams_price_id, "quantity": 1}` — add the Teams item
   - The metered items are NOT included in the `items` array → they are preserved automatically

```python
stripe_sub = stripe.Subscription.retrieve(sub_row.psp_subscription_id)
charter_price_id = ids["prices"]["price_charter_monthly"]
teams_price_id = (
    ids["prices"]["price_teams_annual"]
    if billing_interval == "annual"
    else ids["prices"]["price_teams_monthly"]
)

# Find the Charter item to delete
charter_item = None
for item in stripe_sub["items"]["data"]:
    if item["price"]["id"] == charter_price_id:
        charter_item = item
        break

if not charter_item:
    raise ValueError("Charter price item not found on subscription")

# Build modify call
modify_kwargs = {
    "items": [
        {"id": charter_item["id"], "deleted": True},
        {"price": teams_price_id, "quantity": 1},
    ],
    "proration_behavior": "create_prorations",
}

# End trial if active
if stripe_sub.status == "trialing":
    modify_kwargs["trial_end"] = "now"

updated_sub = stripe.Subscription.modify(
    sub_row.psp_subscription_id,
    **modify_kwargs,
)
```

### F.3 — Payment Method Check

Before calling `Subscription.modify()`, the service must verify the customer has a payment method on file. A Charter member in trial with no card cannot upgrade — the proration invoice would fail.

```python
customer = stripe.Customer.retrieve(
    tenant.stripe_customer_id,
    expand=["invoice_settings.default_payment_method"],
)
if not customer["invoice_settings"]["default_payment_method"]:
    raise ValueError(
        "No payment method on file. Add a card before upgrading."
    )
```

---

## G. Open Questions Resolved

| # | Question | Resolution |
|---|---|---|
| 1 | **Should the upgrade use the existing `change-tier` endpoint or a new one?** | **New dedicated endpoint.** The existing `_change_tier_impl()` adds a new price item without deleting the old one (double-billing), doesn't flip `charter_eligible`, doesn't end the trial, and doesn't use `proration_behavior`. The Charter → Teams flow is fundamentally different. |
| 2 | **What billing interval should the Charter member get on Teams?** | **User choice.** Tom decision 2026-08-07: the Charter member becomes a "regular" customer and chooses monthly ($179/mo) or annual ($149/mo effective). The forfeiture modal shows both options. The spec §6.7 copy ("$149/mo") is updated to show both prices. |
| 3 | **Should the trial end immediately on upgrade?** | **Yes.** A Charter member in their 90-day free period who upgrades to Teams should exit the trial immediately and start paying. `trial_end="now"` in the `Subscription.modify()` call. The proration invoice charges them for Teams from the moment of upgrade. |
| 4 | **What happens to the metered items (voice_overage, sms_overage)?** | **Preserved.** They are shared across all tiers. The `Subscription.modify()` call only includes the Charter item (deleted) + Teams item (added). Items not in the `items` array are left unchanged. |
| 5 | **Should `charter_eligible` flip happen before or after the Stripe call?** | **After.** The Stripe call is the source of truth for the billing change. If it fails, we don't flip `charter_eligible`. The service function calls Stripe first, then updates the DB on success. |
| 6 | **What if the Charter member has no payment method?** | **Reject with 400.** The forfeiture modal should check for a payment method before showing the confirm button. If no PM, show "Add a payment method first" with a link to `/settings/billing/payment-method`. The backend also validates this as a safety net. |
| 7 | **Should the `customer.subscription.updated` webhook handle the tier change?** | **Partially.** The existing `handle_subscription_created()` upserts the `subscription` row based on the price ID → tier lookup. C-B12's service function also updates the row directly for immediate consistency (the webhook is async). The `tenant.current_subscription_tier_id` update happens in the service function, not the webhook. |
| 8 | **Should the `BillingSettingsPage` tier picker be fully replaced?** | **Yes.** The current tier picker has stale hardcoded "Pro" and "Growth" tiers (lines 137-140). C-B12 replaces it with: (a) a Charter-specific "Upgrade to Teams" CTA + forfeiture modal for Charter members, (b) the existing generic tier picker for trial/starter members (but with real tier data from the API, not hardcoded). The generic picker fix is in scope for C-B12 since we're already touching the file. |
| 9 | **Should the dashboard Charter badge show an upgrade CTA?** | **No.** The badge stays informational ("Charter Member #N, Free until {date}"). The upgrade CTA lives on the billing settings page. Adding it to the dashboard badge would clutter the primary surface. |

---

## H. Surface Mockup Reference

**Frontend batch**: Part B (React Engineer) — requires a UI design spec from the pilot-web-ui-designer before the React prompt is authored.

**Surface**: Billing settings page (`/settings/billing`) — the existing page gets a Charter-specific upgrade CTA + the forfeiture modal.

**Surfaces touched**:
1. **BillingSettingsPage** (`/settings/billing`) — add "Upgrade to Teams" CTA for Charter members (replaces the stale tier picker). The CTA opens the forfeiture modal.
2. **CharterUpgradeModal** (new component) — blocking forfeiture warning modal with billing interval selector.

**§16 pattern consumption**:
- **Always-preview-before-send** (§16.7) — the forfeiture modal shows the exact price change ($49/mo → $179/mo or $149/mo effective) + billing interval before the user confirms.
- **Four-class severity** — the modal is a destructive confirmation (forfeiture is irreversible). Cancel = safe default (primary button), "I understand — upgrade to Teams" = danger button.

**Platform**: Web only (`apps/web`). No mobile surface — subscription management is a settings action, not a field action.

**UI design spec output**: `dev-docs/architecture-design/batch-designs/batch-c-b12-ui-design-spec.md` (pilot-web-ui-designer authors, Tom approves before React prompt).

**Forfeiture modal copy** (per spec §6.7, updated per Tom decision):

> **You'll lose your Charter rate.**
>
> You're on $49/month, locked. Moving to Teams means:
> - **$179/month** if you pay monthly
> - **$149/month** if you pay annually ($1,788/year)
>
> The Charter rate is gone for good — you can't get it back later, even if you move back to Starter.
>
> Billing interval: [ Monthly ] [ Annual ]
>
> [ Keep my Charter rate ]  [ I understand — upgrade to Teams ]

---

## I. Component Manifest

| Component | Destination | Purpose |
|---|---|---|
| `CharterUpgradeModal` | `apps/web/src/features/settings/components/CharterUpgradeModal.tsx` (NEW) | Blocking forfeiture warning modal with billing interval selector + safe default |
| `useTenantSubscription` (updated) | `apps/web/src/features/settings/hooks/useTenantSubscription.ts` | Add `upgradeFromCharter` mutation + `isUpgradingFromCharter` flag |
| `BillingSettingsPage` (updated) | `apps/web/src/features/settings/components/BillingSettingsPage.tsx` | Add "Upgrade to Teams" CTA for Charter members; replace stale tier picker |
| `charterUpgradeHandlers` | `apps/web/src/mocks/handlers/charterUpgradeHandlers.ts` (NEW) | MSW handler for `POST /upgrade-from-charter` |

---

## J. Detailed Design — Service Function

### J.1 — `upgrade_charter_to_teams()` Full Flow

```python
def upgrade_charter_to_teams(
    db: Session,
    tenant_id: uuid.UUID,
    billing_interval: str,
) -> dict:
    from app.models.billing import Subscription, SubscriptionStatus
    from app.models.core import Tenant
    from app.models.subscription import SubscriptionTier
    from core.stripe_config import get_stripe_ids

    if billing_interval not in ("monthly", "annual"):
        raise ValueError("billing_interval must be 'monthly' or 'annual'")

    stripe = _get_stripe_client()
    ids = get_stripe_ids()

    # 1. Load tenant (tenant-scoped select — Rule 7.1)
    tenant = db.exec(
        select(Tenant).where(Tenant.id == tenant_id)
    ).first()
    if not tenant:
        raise ValueError(f"Tenant {tenant_id} not found")

    # 2. Verify tenant is Charter
    if not tenant.charter_eligible:
        raise ValueError("Tenant is not a Charter member")

    charter_tier = db.exec(
        select(SubscriptionTier).where(SubscriptionTier.tier_name == "charter")
    ).first()
    if not charter_tier:
        raise ValueError("Charter tier not found")

    if tenant.current_subscription_tier_id != charter_tier.tier_id:
        raise ValueError("Tenant is not on the Charter tier")

    # 3. Load active subscription
    sub_row = db.exec(
        select(Subscription).where(
            Subscription.tenant_id == tenant_id,
            Subscription.is_active == True,
        )
    ).first()
    if not sub_row or not sub_row.psp_subscription_id:
        raise ValueError("No active subscription found")

    # 4. Verify payment method on file
    customer = stripe.Customer.retrieve(
        tenant.stripe_customer_id,
        expand=["invoice_settings.default_payment_method"],
    )
    if not customer.get("invoice_settings", {}).get("default_payment_method"):
        raise ValueError(
            "No payment method on file. Add a card before upgrading."
        )

    # 5. Retrieve Stripe subscription to find the Charter item
    stripe_sub = stripe.Subscription.retrieve(sub_row.psp_subscription_id)
    charter_price_id = ids["prices"]["price_charter_monthly"]
    teams_price_id = (
        ids["prices"]["price_teams_annual"]
        if billing_interval == "annual"
        else ids["prices"]["price_teams_monthly"]
    )

    charter_item = None
    for item in stripe_sub["items"]["data"]:
        if item["price"]["id"] == charter_price_id:
            charter_item = item
            break

    if not charter_item:
        raise ValueError("Charter price item not found on subscription")

    # 6. Build modify call
    modify_kwargs = {
        "items": [
            {"id": charter_item["id"], "deleted": True},
            {"price": teams_price_id, "quantity": 1},
        ],
        "proration_behavior": "create_prorations",
    }

    # End trial if active
    if stripe_sub.status == "trialing":
        modify_kwargs["trial_end"] = "now"

    # 7. Call Stripe
    updated_sub = stripe.Subscription.modify(
        sub_row.psp_subscription_id,
        **modify_kwargs,
    )

    # 8. Update tenant (AFTER Stripe success)
    teams_tier = db.exec(
        select(SubscriptionTier).where(SubscriptionTier.tier_name == "teams")
    ).first()

    tenant.charter_eligible = False  # D23 — permanent forfeiture
    tenant.current_subscription_tier_id = teams_tier.tier_id
    tenant.free_period_ends_at = None  # No longer in free period
    db.add(tenant)

    # 9. Update subscription row
    active_status = db.exec(
        select(SubscriptionStatus).where(
            SubscriptionStatus.code == "active",
            SubscriptionStatus.is_billing_active == True,
        )
    ).first()

    sub_row.product_plan_code = teams_tier.product_plan_code
    sub_row.billing_interval = billing_interval
    sub_row.trial_ends_at = None
    if active_status:
        sub_row.status_id = active_status.id
    db.add(sub_row)

    db.commit()

    logger.info(
        "Charter tenant %s upgraded to Teams (billing_interval=%s, "
        "charter_eligible=false, sub_id=%s)",
        tenant_id,
        billing_interval,
        updated_sub.id,
    )

    return {
        "psp_subscription_id": updated_sub.id,
        "new_tier_name": "teams",
        "billing_interval": billing_interval,
        "charter_eligible_forfeited": True,
    }
```

---

## K. Test Plan

| Test | Type | Description |
|---|---|---|
| `test_upgrade_charter_to_teams_monthly` | Unit | Valid Charter tenant, monthly interval → Charter item deleted, Teams item added, `charter_eligible=False`, tier updated, `free_period_ends_at=None`. |
| `test_upgrade_charter_to_teams_annual` | Unit | Valid Charter tenant, annual interval → uses `price_teams_annual`, `billing_interval="annual"`. |
| `test_upgrade_ends_trial_immediately` | Unit | Charter tenant in `trialing` status → `trial_end="now"` passed to `Subscription.modify()`. |
| `test_upgrade_preserves_metered_items` | Unit | After upgrade, the voice_overage + sms_overage items are still on the subscription (not deleted). |
| `test_upgrade_not_charter_tenant` | Unit | Tenant with `charter_eligible=False` → ValueError. |
| `test_upgrade_not_charter_tier` | Unit | Tenant on Starter tier → ValueError. |
| `test_upgrade_no_subscription` | Unit | No active subscription row → ValueError. |
| `test_upgrade_no_payment_method` | Unit | Stripe customer has no `default_payment_method` → ValueError. |
| `test_upgrade_invalid_billing_interval` | Unit | `billing_interval="weekly"` → ValueError. |
| `test_upgrade_stripe_error` | Unit | Stripe API raises → error propagates, `charter_eligible` NOT flipped (DB unchanged). |
| `test_endpoint_happy_path` | Unit | Authenticated Charter tenant → 200, response has `charter_eligible_forfeited=True`. |
| `test_endpoint_not_charter` | Unit | Non-Charter tenant → 400. |
| `test_endpoint_tenant_isolation` | Unit | `tenant_id != current_user.tenant_id` → 404. |
| `test_endpoint_test_twin` | Unit | Test endpoint bypasses Stripe, returns mock. |

**Domain folder**: `tests/domains/subscriptions_usage/` (subscription tier changes are in the subscriptions domain).

---

## L. Cost Impact

**$0.** No new AWS services, no new infrastructure. The upgrade is a single Stripe API call + a DB update. The Stripe API call is free. The DB update is a single-row UPDATE. No additional compute, storage, or bandwidth.

---

## M. Definition of Done

### Part A (Python Engineer)
- [ ] `upgrade_charter_to_teams()` service function added to `services/stripe_subscriptions.py`
- [ ] `POST /{tenant_id}/subscription/upgrade-from-charter` + `/test` twin added to `api/routes/tenant_subscription.py`
- [ ] Request/response schemas added (`UpgradeFromCharterRequest`, `UpgradeFromCharterResponse`)
- [ ] OpenAPI regenerated (1 new endpoint + test twin)
- [ ] Unit tests written (14 tests minimum) — all passing
- [ ] `pytest -m unit` — 0 new failures
- [ ] Full suite — 0 new failures
- [ ] Ruff — 0 errors on changed/new files
- [ ] MCP-verified: all pre-implementation queries confirmed
- [ ] `pnpm sync-api-types` run (handoff to React Engineer)

### Part B (React Engineer — gated on UI design spec)
- [ ] UI design spec authored by pilot-web-ui-designer
- [ ] Tom approves UI design spec
- [ ] `useTenantSubscription` hook updated with `upgradeFromCharter` mutation
- [ ] `CharterUpgradeModal` component created
- [ ] `BillingSettingsPage` updated with Charter upgrade CTA + stale tier picker replaced
- [ ] MSW handlers added + registered in barrel `index.ts`
- [ ] Integration tests written
- [ ] `pnpm --filter web test` — 0 new failures
- [ ] Type check: UI ✅, Web ✅, Mobile ✅
- [ ] Lint: 0 warnings
- [ ] WCAG 2.2 AA: focus trap in modal, ≥24×24px targets, `focus-visible` rings, `prefers-reduced-motion` fallbacks
