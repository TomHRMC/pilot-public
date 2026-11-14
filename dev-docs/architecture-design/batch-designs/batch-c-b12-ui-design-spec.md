# C-B12 — Charter Upgrade Forfeiture Modal UI Design Spec

**Batch**: C-B12 (Part B prerequisite — UI design spec must be Tom-approved before React Engineer prompt)
**Mode**: Pilot Web UI Designer
**Date**: August 7, 2026
**Source design doc**: `batch-c-b12-design.md` §H (Surface Mockup Reference), §I (Component Manifest), §G (Open Questions Resolved)
**Platform**: Web only (`apps/web`) — internal authenticated surface (billing settings page)

---

## 1. Surface Overview

This spec covers two surfaces on the existing Billing Settings page (`/settings/billing`):

### Surface 1 — Charter Upgrade CTA (modified `BillingSettingsPage`)

| Attribute | Value |
|---|---|
| Route | `/settings/billing` (existing page) |
| RBAC | `billing.view` (existing page-level `<RoleGate>`) — owner + operator roles |
| Visibility condition | `currentTier.tierName === "charter"` AND `charterEligible === true` |
| What changes | The "Current Plan" card gains a Charter-specific "Upgrade to Teams" button. The stale hardcoded tier picker modal (lines 137–140 of `BillingSettingsPage.tsx`) is **removed entirely**. For trial/starter members, the existing "Upgrade plan" button is retained as-is (generic tier picker fix is out of scope for C-B12 — only the stale hardcoded picker is removed). |

### Surface 2 — `CharterUpgradeModal` (new component)

| Attribute | Value |
|---|---|
| Component | `CharterUpgradeModal` (NEW — domain-specific, lives in `apps/web/src/features/settings/components/`) |
| Trigger | Click of the "Upgrade to Teams" CTA on the Billing Settings page |
| Type | Blocking modal — `role="dialog"`, `aria-modal="true"`, focus trap, Escape to close = safe default (closes modal, no action taken) |
| §16 pattern | **Always-preview-before-send** (§16.7) — shows the exact price change + billing interval before confirm. **Four-class severity** — destructive confirmation (forfeiture is irreversible). |
| Safe default | "Keep my Charter rate" button (primary visual weight, `bg-brand-600`) — closes the modal with no action. |
| Destructive action | "I understand — upgrade to Teams" button (`bg-fault-600`) — calls `POST /api/v1/tenants/{tenant_id}/subscription/upgrade-from-charter`. |

### RBAC note

The entire `BillingSettingsPage` is already wrapped in `<RoleGate permission="billing.view">` (see `BillingSettingsPage.tsx`:219). The Charter CTA and modal inherit this gate — no additional `<RoleGate>` wrapper is needed inside the modal. The `upgradeFromCharter` mutation is backend-gated by `subscription.tier.change` (owner + operator). Per the hide-not-disable RBAC rule, tech role never sees the billing page at all.

---

## 2. Pixel Specs

### 2.1 — Charter Upgrade CTA Button (on Current Plan card)

| Property | Value |
|---|---|
| Placement | Right side of the "Current Plan" card header row (same position as the existing "Upgrade plan" button for trial/starter) |
| Label | "Upgrade to Teams" |
| Height | `py-2` → ~36px rendered (meets ≥24px target; button text + padding yields ≥36px) |
| Width | Auto (content-driven, `px-4`) |
| Border radius | `rounded-md` (6px) |
| Background | `bg-brand-600` |
| Text | `text-white text-sm font-medium` |
| Icon | `ArrowRightIcon` (Heroicons outline, `w-4 h-4`) — right-aligned, `ml-2` gap from label |
| Min hit area | 36×auto (≥24×24px satisfied) |

**Conditional rendering logic** (replaces the existing `isTrial || currentTier.tierName === "starter"` block at line 117):

```
if (currentTier.tierName === "charter" && charterEligible) → render "Upgrade to Teams" CTA
else if (isTrial || currentTier.tierName === "starter") → render existing "Upgrade plan" button (unchanged)
else → no upgrade button (Teams members, etc.)
```

### 2.2 — CharterUpgradeModal Panel

| Property | Value |
|---|---|
| Overlay | `fixed inset-0 bg-neutral-900/50 z-50` (click on overlay = close = safe default) |
| Panel | `bg-white rounded-lg shadow-xl max-w-lg w-full mx-auto mt-16 p-6` |
| Max width | `max-w-lg` (512px) — wider than the standard `max-w-md` (448px) to accommodate the two-option billing interval selector side-by-side |
| Padding | `p-6` (24px all sides) |
| Internal gap | `space-y-4` between major sections (header, body, selector, button bar) |
| Border radius | `rounded-lg` (8px) |
| z-index | `z-50` (modal layer per design-system-reference §7) |

### 2.3 — Modal Header Row

| Property | Value |
|---|---|
| Layout | `flex items-start justify-between` |
| Left side | Warning icon + heading, `flex items-center gap-3` |
| Warning icon | `ExclamationTriangleIcon` (Heroicons outline, `w-6 h-6`, `text-alert-600`) |
| Heading | "You'll lose your Charter rate." — `text-h2 font-semibold text-neutral-900` |
| Right side | Close button (`XMarkIcon`) — `text-neutral-400 hover:text-neutral-600 hover:bg-neutral-100 rounded-md p-2.5 focus-visible:ring-2 focus-visible:ring-brand-500`, `aria-label="Close modal"`. Hit area: `p-2.5` + `w-5 h-5` icon = 40×40px (≥24px). |

### 2.4 — Current Rate Display

| Property | Value |
|---|---|
| Text | "You're on $49/month, locked." |
| Typography | `text-body text-neutral-700` |
| Spacing | `mt-1` below header row (within the `space-y-4` flow) |

### 2.5 — Teams Pricing Display

| Property | Value |
|---|---|
| Layout | Unordered list, `space-y-1.5` |
| Intro line | "Moving to Teams means:" — `text-body text-neutral-700`, `mb-1` |
| Bullet 1 | "$179/month if you pay monthly" — `text-body text-neutral-900`, with `text-neutral-400` bullet marker |
| Bullet 2 | "$149/month if you pay annually ($1,788/year)" — `text-body text-neutral-900` |
| Bullet marker | Standard `list-disc list-inside` or custom `•` in `text-neutral-400` |

> **Money display rule** (§12): All amounts are display-formatted from integer cents. The Charter rate is `4900` cents → `$49`. Teams monthly is `17900` cents → `$179`. Teams annual is `178800` cents/year → `$1,788/year`, with per-month equivalent `178800 / 12 / 100 = $149/mo`. The spec hardcodes these display strings because they are fixed pricing copy (not dynamic data) — but the engineer should source them from the tier data where available.

### 2.6 — Forfeiture Warning

| Property | Value |
|---|---|
| Layout | `flex items-start gap-1.5` (icon + text) |
| Icon | `ExclamationCircleIcon` (Heroicons outline, `w-4 h-4`, `text-fault-600`, `mt-0.5 shrink-0`) |
| Text | "The Charter rate is gone for good — you can't get it back later, even if you move back to Starter." |
| Typography | `text-body text-fault-600` |
| Background | `bg-fault-50 border border-fault-200 rounded-md p-3` (callout container to emphasize irreversibility) |
| Spacing | `mt-2` |

### 2.7 — Billing Interval Selector (segmented radio group)

| Property | Value |
|---|---|
| Container | `role="radiogroup"` with `aria-label="Billing interval"` |
| Layout | `grid grid-cols-2 gap-3` (two equal-width options side-by-side) |
| Label above | "Billing interval" — `block text-sm font-medium text-neutral-700 mb-2` (visible label per §10 form pattern) |
| Option — Monthly | Button with `role="radio"`, `aria-checked` toggled |
| Option — Annual | Button with `role="radio"`, `aria-checked` toggled |
| Option dimensions | Full width of grid cell, `px-4 py-3` → ~52px height (≥24px target satisfied) |
| Border radius | `rounded-md` (6px) |
| Border width | `border` (1px) |

**Monthly option content:**
- Line 1: "Monthly" — `text-sm font-medium`
- Line 2: "$179/mo" — `text-caption`

**Annual option content:**
- Line 1: "Annual" — `text-sm font-medium`
- Line 2: "$149/mo (billed $1,788/yr)" — `text-caption`

**Selected state classes:** `bg-brand-50 border-brand-500 text-brand-700`
**Unselected state classes:** `bg-white border-neutral-200 text-neutral-700`
**Default selection:** Monthly (`aria-checked="true"`)

### 2.8 — Button Bar

| Property | Value |
|---|---|
| Layout | `flex justify-end gap-3 mt-6` |
| Safe default (left) | "Keep my Charter rate" |
| Destructive (right) | "I understand — upgrade to Teams" |
| Button height | `py-2.5` → ~40px rendered. To meet ≥44px WCAG target for primary actions, use `min-h-[44px]` on both buttons. |
| Button width | Auto, `px-4` |
| Border radius | `rounded-md` (6px) |

**Safe default button ("Keep my Charter rate"):**
- `bg-brand-600 text-white rounded-md px-4 py-2.5 min-h-[44px] text-sm font-medium hover:bg-brand-700 focus-visible:ring-2 focus-visible:ring-brand-500`
- On click: closes modal, no action

**Destructive button ("I understand — upgrade to Teams"):**
- `bg-fault-600 text-white rounded-md px-4 py-2.5 min-h-[44px] text-sm font-medium hover:bg-fault-700 focus-visible:ring-2 focus-visible:ring-fault-500 disabled:bg-neutral-300 disabled:cursor-not-allowed`
- On click: calls `upgradeFromCharter(billingInterval)`

> **Design decision**: Both buttons are filled (not outline). The safe default uses `bg-brand-600` (primary brand color) to draw the eye toward the safe choice. The destructive uses `bg-fault-600`. This is a deliberate departure from the CloseCohortButton pattern (where Cancel was an outline button) — here the stakes are higher (permanent rate forfeiture) and both actions need equal visual weight so the user reads both before choosing. Per Tom's decision (§6.7, prompt §26).

### 2.9 — Error Banner (inside modal, above button bar)

| Property | Value |
|---|---|
| Component | `<NotificationBanner>` from `@pilot/ui` (or `useNotificationQueue` inline render) — severity `"error"` |
| Placement | `mt-4` above the button bar, below the billing interval selector |
| Content | Error message from RFC 7807 response. For no-payment-method 400: "No payment method on file. Add a card before upgrading." with an inline link to `/settings/billing/payment-method`. |
| Dismissal | User-dismissable (does not auto-dismiss for errors — `dismissAfterMs: null`) |

### 2.10 — Success Banner (on billing page, after modal close)

| Property | Value |
|---|---|
| Component | `useNotificationQueue` → `addNotification({ severity: "success", ... })` |
| Title | "You're now on the Teams plan." |
| Dismissal | `dismissAfterMs: 6000` (standard success auto-dismiss) |
| Placement | Top-of-page via `<NotificationPortal>` (existing pattern from CloseCohortButton) |

---

## 3. Token-Only Colors

Zero hex codes. All colors reference `pilotPreset` token names:

| Element | Token classes |
|---|---|
| Modal overlay | `bg-neutral-900/50` |
| Modal panel | `bg-white` |
| Modal shadow | `shadow-xl` |
| Header heading | `text-neutral-900` |
| Warning icon (header) | `text-alert-600` |
| Current rate text | `text-neutral-700` |
| Pricing bullet text | `text-neutral-900` |
| Bullet markers | `text-neutral-400` |
| Forfeiture warning text | `text-fault-600` |
| Forfeiture warning bg | `bg-fault-50` |
| Forfeiture warning border | `border-fault-200` |
| Forfeiture warning icon | `text-fault-600` |
| Selector label | `text-neutral-700` |
| Selector — selected | `bg-brand-50 border-brand-500 text-brand-700` |
| Selector — unselected | `bg-white border-neutral-200 text-neutral-700` |
| Selector — hover | `hover:border-brand-400` |
| Selector — focus-visible | `focus-visible:ring-2 focus-visible:ring-brand-500` |
| Safe default button | `bg-brand-600 text-white hover:bg-brand-700` |
| Safe default focus | `focus-visible:ring-2 focus-visible:ring-brand-500` |
| Destructive button | `bg-fault-600 text-white hover:bg-fault-700` |
| Destructive focus | `focus-visible:ring-2 focus-visible:ring-fault-500` |
| Disabled button | `disabled:bg-neutral-300 disabled:cursor-not-allowed` |
| Close (X) button | `text-neutral-400 hover:text-neutral-600 hover:bg-neutral-100` |
| Close focus | `focus-visible:ring-2 focus-visible:ring-brand-500` |
| CTA button (billing page) | `bg-brand-600 text-white hover:bg-brand-700` |
| CTA focus | `focus-visible:ring-2 focus-visible:ring-brand-500` |
| Spinner (loading) | `border-brand-600 border-t-transparent` |

> **Contrast validation**: All token pairings used here (`text-neutral-900 on bg-white`, `text-brand-700 on bg-brand-50`, `text-fault-600 on bg-fault-50`, `text-white on bg-brand-600`, `text-white on bg-fault-600`) are pre-validated per §10 of the design standards. No novel pairings introduced.

---

## 4. Icon Inventory

All icons are [Heroicons 2.0](https://heroicons.com/), outline variant unless noted.

| Icon | Variant | Size | Location |
|---|---|---|---|
| `ExclamationTriangleIcon` | outline | `w-6 h-6` | Modal header — warning indicator next to heading |
| `ExclamationCircleIcon` | outline | `w-4 h-4` | Forfeiture warning callout — inline with warning text |
| `XMarkIcon` | outline | `w-5 h-5` | Modal close button (top-right) |
| `ArrowRightIcon` | outline | `w-4 h-4` | "Upgrade to Teams" CTA button on billing page |
| `ArrowPathIcon` | outline | `w-4 h-4` | Spinner inside destructive button during loading state (with `animate-spin`) |

No custom SVGs required. No emoji in production UI.

---

## 5. State Coverage (Four Data States Minimum)

### 5.1 — Default (modal open, monthly selected, both buttons enabled)

- Modal is visible, focus is on the safe-default button ("Keep my Charter rate") on open
- Monthly billing interval is selected by default (`aria-checked="true"`)
- Both buttons are enabled
- No error banner visible

### 5.2 — Loading (upgrade mutation in flight)

- The "I understand — upgrade to Teams" button is `disabled` (`disabled:bg-neutral-300 disabled:cursor-not-allowed`)
- Button label changes to "Upgrading…" with an inline `ArrowPathIcon` spinner (`animate-spin w-4 h-4 mr-2`)
- The "Keep my Charter rate" button remains enabled (user can still cancel mid-flight — the mutation will be aborted on unmount)
- Overlay click is disabled during loading (prevent accidental close mid-request) — `onClick` handler checks `isUpgrading` and no-ops
- Escape key still works (safe default — aborts mutation)

### 5.3 — Error (upgrade failed)

- A `<NotificationBanner>` with `severity="error"` renders inside the modal, above the button bar, below the billing interval selector
- The destructive button reverts to enabled state (loading complete)
- The error message is extracted from the RFC 7807 response `detail` field
- **No payment method (400)**: Message = "No payment method on file. Add a card before upgrading." + inline `<Link href="/settings/billing/payment-method">` "Add a payment method →"
- **Not Charter (400)**: Message = "This account is no longer eligible for the Charter upgrade."
- **Stripe error (502)**: Message = "Upgrade failed due to a payment provider error. Please try again or contact support."
- Modal stays open — user can retry or cancel

### 5.4 — Success (upgrade completed)

- Brief state: the destructive button shows "Upgrading…" then the mutation resolves
- Modal closes immediately on `onSuccess`
- A success `<NotificationBanner>` (`severity="success"`, title "You're now on the Teams plan.", `dismissAfterMs: 6000`) renders at the top of the billing page via `<NotificationPortal>`
- The TanStack Query cache for `["tenant-subscription", tenantId]` is invalidated → the "Current Plan" card re-renders showing "Teams" tier with the new billing interval
- The Charter CTA button disappears (condition `charterEligible === true` is now false)

### 5.5 — Billing page data states (existing, unchanged)

- `isLoading` → centered spinner (existing, `BillingSettingsPage.tsx`:61)
- `isError || !subscription` → error card (existing, `BillingSettingsPage.tsx`:69)
- Empty → N/A (subscription always exists for authenticated tenants)
- Populated → renders Current Plan card + Usage + Payment Method

---

## 6. Interaction Spec (All Five States Per Element)

### 6.1 — "Upgrade to Teams" CTA button (billing page)

| State | Spec |
|---|---|
| Default | `bg-brand-600 text-white` |
| Hover | `hover:bg-brand-700` |
| Focus-visible | `focus-visible:ring-2 focus-visible:ring-brand-500` |
| Active | `active:bg-brand-700` (browser default active) |
| Disabled | N/A — button is only rendered when `charterEligible === true`; if the upgrade mutation is in flight from another tab, the button is not disabled (the modal handles its own loading state) |

### 6.2 — Billing interval selector options (Monthly / Annual)

| State | Spec |
|---|---|
| Default (unselected) | `bg-white border-neutral-200 text-neutral-700` |
| Hover | `hover:border-brand-400` |
| Focus-visible | `focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-1` |
| Active (selected) | `bg-brand-50 border-brand-500 text-brand-700`, `aria-checked="true"` |
| Disabled | N/A — both options are always enabled (no condition disables them) |

### 6.3 — Safe default button ("Keep my Charter rate")

| State | Spec |
|---|---|
| Default | `bg-brand-600 text-white` |
| Hover | `hover:bg-brand-700` |
| Focus-visible | `focus-visible:ring-2 focus-visible:ring-brand-500` |
| Active | `active:bg-brand-700` |
| Disabled | N/A — always enabled (safe default must always be available) |

### 6.4 — Destructive button ("I understand — upgrade to Teams")

| State | Spec |
|---|---|
| Default | `bg-fault-600 text-white` |
| Hover | `hover:bg-fault-700` |
| Focus-visible | `focus-visible:ring-2 focus-visible:ring-fault-500` |
| Active | `active:bg-fault-700` |
| Disabled (loading) | `disabled:bg-neutral-300 disabled:cursor-not-allowed`, label = "Upgrading…" + spinner |

### 6.5 — Close (X) button

| State | Spec |
|---|---|
| Default | `text-neutral-400` |
| Hover | `hover:text-neutral-600 hover:bg-neutral-100` |
| Focus-visible | `focus-visible:ring-2 focus-visible:ring-brand-500` |
| Active | `active:bg-neutral-100` |
| Disabled | N/A — always enabled (except during loading, where overlay click is suppressed but X remains enabled as escape hatch) |

### 6.6 — Modal overlay (backdrop)

| State | Spec |
|---|---|
| Default click | Closes modal (safe default) — `onClick={onClose}` on overlay div |
| Loading click | Suppressed — `onClick` checks `isUpgrading` and no-ops |
| Escape key | Closes modal (safe default) — always works, even during loading (aborts mutation) |

---

## 7. Animation Spec

| Element | Transition | Reduced-motion fallback |
|---|---|---|
| Modal open (backdrop + panel) | `transition: opacity 200ms ease-in-out` — backdrop fades from 0→1, panel fades + slight scale (0.98→1.0) | `@media (prefers-reduced-motion: reduce)` → no transition, instant appear |
| Billing interval selection | `transition: background-color 150ms ease-in-out, border-color 150ms ease-in-out` on the option buttons | `@media (prefers-reduced-motion: reduce)` → no transition, instant color swap |
| Button hover | `transition: background-color 150ms ease-in-out` (standard, inherited from Tailwind defaults) | `@media (prefers-reduced-motion: reduce)` → no transition |
| Spinner | `animate-spin` (standard Tailwind) — continuous rotation | `@media (prefers-reduced-motion: reduce)` → spinner hidden, "Upgrading…" text remains (the disabled state + text label communicates loading without motion) |

> **Implementation note**: The modal open animation should use a mounted state toggle (`isMounted`) with a short `requestAnimationFrame` delay to trigger the opacity transition, OR use a CSS class toggle. The engineer should follow the same approach as `ExtendFreePeriodModal.tsx` (which currently appears instantly — C-B12 may add the fade-in as an enhancement, but instant appear is acceptable if the reduced-motion path is the default).

---

## 8. Component Manifest

| Component | Path | Status | Description |
|---|---|---|---|
| `CharterUpgradeModal` | `apps/web/src/features/settings/components/CharterUpgradeModal.tsx` | NEW | Blocking forfeiture warning modal with billing interval selector + safe default. Composes `useNotificationQueue` for error/success banners. Calls `upgradeFromCharter` mutation from `useTenantSubscription`. |
| `BillingSettingsPage` | `apps/web/src/features/settings/components/BillingSettingsPage.tsx` | MODIFIED | Add "Upgrade to Teams" CTA for Charter members (conditional on `tierName === "charter" && charterEligible`). Remove stale hardcoded tier picker modal (lines 129–168). Add `showCharterUpgrade` state + render `<CharterUpgradeModal>`. |
| `useTenantSubscription` | `apps/web/src/features/settings/hooks/useTenantSubscription.ts` | MODIFIED | Add `charterEligible` field to `TenantSubscription` interface + normalizer. Add `upgradeFromCharter(billingInterval)` mutation calling `POST /api/v1/tenants/{tenant_id}/subscription/upgrade-from-charter`. Add `isUpgradingFromCharter` flag. Invalidate `["tenant-subscription", tenantId]` on success. |
| `charterUpgradeHandlers` | `apps/web/src/mocks/handlers/charterUpgradeHandlers.ts` | NEW | MSW handler for `POST /upgrade-from-charter` + `/test` twin. Returns mock `UpgradeFromCharterResponse`. Registered in handler barrel. |

> **No new shared components** in `packages/ui`. The modal is domain-specific (Charter upgrade is a one-time flow, not reusable across surfaces) and lives in the settings feature folder per the component placement rule (§6 of design standards). The modal composes existing shared primitives: `useNotificationQueue` from `@pilot/ui/notification-banner`, `RoleGate` (inherited from page), Heroicons.

---

## 9. Implementation Notes

### 9.1 — Hook changes (`useTenantSubscription.ts`)

The existing `TenantSubscription` interface does not expose `charterEligible`. The backend `GET /subscription` response must include `charter_eligible` (boolean) and `charter_member_number` (integer | null) in its response body. The normalizer (`normalizeSubscription()`:80) must map these:

```typescript
// Add to SubscriptionRaw interface:
charter_eligible: boolean;
charter_member_number: number | null;

// Add to TenantSubscription interface:
charterEligible: boolean;
charterMemberNumber: number | null;

// Add to normalizeSubscription():
charterEligible: raw.charter_eligible,
charterMemberNumber: raw.charter_member_number,
```

The new mutation:

```typescript
const upgradeMutation = useMutation({
  mutationFn: async (billingInterval: "monthly" | "annual") => {
    await apiClient.post(
      `/api/v1/tenants/${tenantId}/subscription/upgrade-from-charter`,
      { billing_interval: billingInterval },
    );
  },
  onSuccess: () => {
    void qc.invalidateQueries({ queryKey });
  },
});

// Return additions:
upgradeFromCharter: async (billingInterval) => {
  await upgradeMutation.mutateAsync(billingInterval);
},
isUpgradingFromCharter: upgradeMutation.isPending,
upgradeError: upgradeMutation.error,
```

### 9.2 — Endpoint

- `POST /api/v1/tenants/{tenant_id}/subscription/upgrade-from-charter`
- Request body: `{ "billing_interval": "monthly" | "annual" }`
- Response 200: `{ "psp_subscription_id": "sub_...", "new_tier_name": "teams", "billing_interval": "monthly", "charter_eligible_forfeited": true }`
- Errors: RFC 7807 Problem Details (400 not-Charter, 400 no-subscription, 400 no-payment-method, 404 tenant-isolation, 502 Stripe error)
- Test twin: `POST /api/v1/tenants/{tenant_id}/subscription/upgrade-from-charter/test`

### 9.3 — Query keys

- Subscription query key: `["tenant-subscription", tenantId]` (existing — invalidated on upgrade success)
- No new query key needed (the upgrade is a mutation, not a query)

### 9.4 — Focus management (follow ExtendFreePeriodModal / CloseCohortButton pattern)

- On modal open: focus the safe-default button ("Keep my Charter rate") — use a `ref` + `useEffect` (same as `CloseCohortButton.tsx`:42 `cancelButtonRef`)
- Escape key: closes modal (safe default) — always works, even during loading (aborts the mutation via TanStack Query's `mutation.cancel()`)
- Tab focus trap: cycle within modal — same implementation as `ExtendFreePeriodModal.tsx`:115 (query `focusable` elements, wrap first/last)
- On modal close: restore focus to the "Upgrade to Teams" CTA button (the trigger element) — store the trigger ref or use `document.activeElement` snapshot before open

### 9.5 — Stale tier picker removal

The existing tier picker modal (`BillingSettingsPage.tsx`:129–168) has hardcoded "Pro" ($9900) and "Growth" ($19900) tiers that do not exist in the database. **Remove the entire `showTierPicker` modal block** (lines 129–168) and the `showTierPicker` state. The trial/starter "Upgrade plan" button should remain but its `onClick` should be a no-op or show a "Coming soon" toast until the generic tier picker is built in a future batch. The Charter "Upgrade to Teams" button uses a separate `showCharterUpgrade` state.

### 9.6 — Notification queue

Use `useNotificationQueue` from `@pilot/ui/notification-banner` (same as `CloseCohortButton.tsx`:37). The success notification is added on `onSuccess` of the mutation, then the modal closes. The error notification is rendered inline inside the modal (not via the queue portal) so it appears in context — use a local `errorMessage` state + inline `<NotificationBanner>` render, OR add to the queue with a modal-scoped ID. Recommended: local state for in-modal errors (keeps them in context), queue for the post-close success banner.

### 9.7 — Money formatting

The pricing copy in the modal is fixed (Charter $49/mo, Teams $179/mo monthly, Teams $149/mo effective annual). These can be hardcoded as display strings in the component since they are product-defined pricing, not dynamic data. However, if the engineer prefers to source from tier data, the `subscription_tier` table has `monthly_price_cents` and `annual_price_cents` — format via the existing `formatCents()`:22 helper (divide by 100). For annual, show per-month equivalent: `annual_price_cents / 12 / 100`.

### 9.8 — MSW handler

The mock handler should return a successful `UpgradeFromCharterResponse` by default, with a configurable delay (300ms) to test the loading state. Add a query-param or header toggle for error scenarios (no payment method, not Charter) for test coverage.

---

## 10. Accessibility Notes

### 10.1 — Color-independent status

- The forfeiture warning is **not red-only**. It pairs `text-fault-600` (color) with the `ExclamationCircleIcon` icon (shape) and the text "The Charter rate is gone for good" (text label). Satisfies WCAG 1.4.1 (Use of Color).
- The billing interval selected state pairs `bg-brand-50 border-brand-500` (color) with `aria-checked="true"` (programmatic) and a visible border-weight difference (selected = `border-brand-500`, unselected = `border-neutral-200`). Satisfies WCAG 1.4.1.
- The header warning icon (`ExclamationTriangleIcon` in `text-alert-600`) pairs color with the triangle shape + the heading text "You'll lose your Charter rate."

### 10.2 — Target sizes (WCAG 2.2 SC 2.5.8)

| Element | Rendered size | Meets ≥24×24px? |
|---|---|---|
| "Upgrade to Teams" CTA | ~36×auto | ✅ |
| Close (X) button | 40×40px (`p-2.5` + `w-5 h-5`) | ✅ |
| Billing interval options | ~52px height × grid cell width | ✅ |
| Safe default button | `min-h-[44px]` | ✅ (≥44px primary action) |
| Destructive button | `min-h-[44px]` | ✅ (≥44px primary action) |

### 10.3 — Focus order + focus-visible treatment

1. Modal opens → focus moves to the safe-default button ("Keep my Charter rate")
2. Tab order: safe-default button → billing interval Monthly option → billing interval Annual option → destructive button → close (X) button → wraps to safe-default
3. Shift+Tab reverses the order
4. All interactive elements use `focus-visible:ring-2 focus-visible:ring-brand-500` (or `ring-fault-500` for the destructive button) — keyboard users get a visible ring, mouse users do not see a persistent ring after click
5. On modal close → focus returns to the "Upgrade to Teams" CTA button (the trigger)

### 10.4 — Modal focus-trap / return behavior

- Focus trap implementation follows the `ExtendFreePeriodModal.tsx`:115 pattern: `document.addEventListener("keydown", handleKeyDown)` with Tab wrapping logic
- `role="dialog"` + `aria-modal="true"` on the overlay div
- `aria-label="Upgrade to Teams — Charter rate forfeiture warning"` on the dialog
- Escape key closes the modal (safe default) — always available, even during loading
- Focus is restored to the trigger button on close (store `document.activeElement` before open, restore on unmount)

### 10.5 — Form field labels

- The billing interval selector has a visible `<label>` ("Billing interval") above it per §10 of design standards (placeholder-as-label is banned)
- Each radio option has an accessible name via its visible text content ("Monthly — $179/mo", "Annual — $149/mo (billed $1,788/yr)")
- The `role="radiogroup"` has `aria-label="Billing interval"` as a redundant accessible name

### 10.6 — Reduced motion

- All transitions have `@media (prefers-reduced-motion: reduce)` fallbacks (instant or opacity-only) — see §7
- The loading spinner is hidden under reduced-motion; the "Upgrading…" text label remains to communicate the loading state without motion

### 10.7 — Focus not obscured (WCAG 2.2 SC 2.4.11)

- The modal is `position: fixed` with `z-50`, above the `h-12` sticky header (`z-30`). When the modal is open, focus is trapped inside the modal — no content beneath the sticky header can be scrolled to. No `scroll-margin-top` needed for modal content.
- The success `<NotificationBanner>` portal renders at the top of the billing page after modal close. If it appears beneath the sticky header, the engineer should ensure `scroll-margin-top: 60px` on the page content container so anchored focus is not obscured. (The `<NotificationPortal>` typically renders in a top-of-body slot above the header — verify during implementation.)

---

## 11. Responsive Notes (1024px / 768px reflow)

- **1280px+ (primary spec)**: Modal is `max-w-lg` (512px), centered with `mt-16`. Billing interval selector is `grid-cols-2` (side-by-side).
- **1024px**: No change — modal is narrower than the content area. Selector remains side-by-side.
- **768px**: Modal `max-w-lg` still fits (512px < 768px). If the viewport is narrower than 512px (not expected at 768px minimum), the modal `w-full` with `mx-4` margin would apply. The billing interval selector could reflow to `grid-cols-1` (stacked) at <480px, but this is below the 768px desktop minimum and out of scope for this mode (mobile is React Native → `pilot-voice-ui-designer`).

---

## Handoff Gate

This spec is ready for Tom's review. Implementation starts only after approval.

The React Engineer prompt (C-B12 Part B) will be authored only after Tom confirms this spec is approved.
