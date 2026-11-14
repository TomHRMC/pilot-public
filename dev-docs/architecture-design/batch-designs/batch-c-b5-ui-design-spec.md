# C-B5 UI Design Spec — Wizard Step 4/5 Conditional + Checklist Item + Charter Badge

**Batch**: C-B5
**Mode**: Pilot Web UI Designer
**Design doc**: `batch-c-b5-design.md` — §H (Surface Mockup Reference) + §I (Component Manifest)
**Source spec**: `pilot-tech-impl-spec-v1.md` §4.1–4.3, §7.1–7.2
**Output**: `dev-docs/architecture-design/batch-designs/batch-c-b5-ui-design-spec.md`
**Date**: August 4, 2026

---

## 1. Surface Overview

This spec covers four web-dashboard surfaces for the Charter program signup flow. All are internal authenticated or signup-wizard surfaces in `apps/web` — no mobile, no marketing.

| # | Surface | Route | RBAC | New/Modified |
|---|---|---|---|---|
| 1 | Wizard Step 4 — Charter Tier Card | `/signup/plan` | Public (signup wizard, pre-auth) | Modified page + new component |
| 2 | Wizard Step 5 — Payment / Confirmation (two branches) | `/signup/ready` | Public (signup wizard, pre-auth) | Modified page + new component |
| 3 | Onboarding Checklist — "Set up text messaging" item | `/dashboard` (widget) | All authenticated (Charter-only conditional render) | Modified types + new component |
| 4 | Charter Member Badge | `/dashboard` (header) | Owner-only (`<RoleGate role="owner">`) | New component + dashboard wiring |

**§16 pattern consumption**:
- **Optimistic UI (§16.8)** — Step 4 shows "Free for 90 days. No card needed." immediately on tier selection; no loading state for the free-period copy (tier data already fetched).
- **System-default / tenant-override (§16.5)** — `requires_payment_method` is a tier-level default read by the wizard to decide step 5 behavior. Not a tenant override.
- **409-and-refresh (§16.4)** — Existing wizard staleness guard unchanged. The tier-closed 409 (cohort cap reached) surfaces via the existing error path.

---

## 2. Surface 1 — Wizard Step 4: Charter Tier Card

### 2.1 Context

The existing `/signup/plan` page renders a grid of `TierPickerCard` components, one per active tier. During Charter, `useSubscriptionTiers()` returns exactly one active tier (the Charter tier), so the grid renders a single card.

The existing page already has mode-aware subtitle logic (lines 137–140):
- Trial mode: `"Start with a 14-day free trial — no credit card required."`
- Charter mode: `"Join the Charter program — 90 days free, no credit card required."`

**What changes**: The `tierToCardProps()` mapper (lines 38–62) must pass Charter-specific display data so the single card communicates the free period in plain language. The `SubscriptionTierAPI` type (in `signup/types.ts`) must be extended with the new tier fields from the C-B5 backend (`free_period_days`, `requires_payment_method`).

### 2.2 New Component — `CharterTierCard`

**Location**: `frontend/apps/web/src/features/signup/components/CharterTierCard.tsx`

A purpose-built card for the Charter tier. It composes the visual language of `TierPickerCard` (rounded-xl, border-2, p-6, feature list with checkmark icons) but is a distinct component because:
- The price display is a fixed "$49/month" with a "Free for 90 days" callout — not the generic `formatCents()` path.
- The free-period copy is plain-language and derived from `free_period_days`, not `trial_duration_days`.
- The `charter_member_number` is explicitly NOT shown here (assigned server-side, shown later on the dashboard badge).

**Decision**: Do NOT extend `TierPickerCard` with more additive props. Its interface is FROZEN after FE-B13. A feature-specific component in the signup feature folder is the correct placement (per §6 component placement rule: domain-specific → `features/[domain]/components/`).

### 2.3 Pixel Specs — `CharterTierCard`

```
┌─────────────────────────────────────────────┐
│  rounded-xl  border-2  p-6  w-full           │
│  border-brand-200  bg-white  shadow-sm       │
│                                             │
│  ┌─ Badge (absolute, -top-3, centered) ─┐   │
│  │ Charter Program                       │   │
│  │ bg-brand-600 text-white px-3 py-0.5  │   │
│  │ rounded-full text-xs font-semibold   │   │
│  └───────────────────────────────────────┘   │
│                                             │
│  Charter                          ✓ (selected checkmark) │
│  text-h3 font-semibold text-neutral-900     │
│                                             │
│  $49 /mo          ← text-2xl font-bold      │
│  text-neutral-900   text-sm text-neutral-500│
│                                             │
│  ┌─ Free-period callout ───────────────┐    │
│  │ bg-margin-50 border border-margin-200│   │
│  │ rounded-md px-3 py-2                 │   │
│  │ GiftIcon (w-4 h-4 text-margin-600)   │   │
│  │ "Free for 90 days. No card needed."  │   │
│  │ text-sm text-margin-700 font-medium  │   │
│  └──────────────────────────────────────┘   │
│                                             │
│  ── Feature list ──                         │
│  ✓ Voice quoting                            │
│  ✓ Job management                           │
│  ✓ QuickBooks sync                          │
│  ✓ SMS notifications                        │
│  ✓ Team members          Up to 12           │
│  (CheckmarkIcon w-4 h-4 text-margin-600)    │
│                                             │
│  ┌─ CTA button ────────────────────────┐    │
│  │ Select Charter                      │    │
│  │ bg-brand-600 text-white rounded-lg  │    │
│  │ py-2 px-4 text-sm font-semibold     │    │
│  └──────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
```

| Element | Spec |
|---|---|
| Card container | `relative flex flex-col gap-4 rounded-xl border-2 p-6 transition-all` |
| Default border | `border-brand-200 bg-white shadow-sm` |
| Selected border | `border-brand-600 bg-brand-50 shadow-md` |
| Featured badge | `absolute -top-3 left-1/2 -translate-x-1/2`, `bg-brand-600 text-white px-3 py-0.5 rounded-full text-xs font-semibold` |
| Tier name | `text-h3 font-semibold text-neutral-900` |
| Price | `text-2xl font-bold text-neutral-900` + `text-sm text-neutral-500` for `/mo` |
| Free-period callout | `bg-margin-50 border border-margin-200 rounded-md px-3 py-2 flex items-center gap-2` |
| Free-period text | `text-sm text-margin-700 font-medium` |
| Feature row | `flex items-center gap-2 text-sm text-neutral-700` |
| Feature checkmark | `CheckCircleIcon` (Heroicons outline, `w-4 h-4 text-margin-600`) |
| CTA button | `mt-auto w-full py-2 px-4 rounded-lg text-sm font-semibold bg-brand-600 text-white hover:bg-brand-800` |
| Selected CTA | `bg-brand-600 text-white` with label "Selected" |

### 2.4 Icon Inventory — Step 4

| Element | Heroicons 2.0 name | Variant | Size |
|---|---|---|---|
| Free-period callout | `GiftIcon` | outline | `w-4 h-4` |
| Feature checkmark | `CheckCircleIcon` | outline | `w-4 h-4` |
| Selected checkmark (corner) | custom SVG (existing pattern from `TierPickerCard`) | — | `w-5 h-5` container, `w-3 h-3` check |

### 2.5 Interaction States — `CharterTierCard`

| State | Visual |
|---|---|
| Default | `border-brand-200 bg-white shadow-sm` |
| Hover | `border-brand-300 shadow-md` (subtle lift) |
| Focus-visible | `focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-2` |
| Active (mouse down) | `border-brand-600` |
| Selected | `border-brand-600 bg-brand-50 shadow-md` + corner checkmark |
| Disabled (tier closed) | Not rendered — the tier is filtered out by `is_active=false` before it reaches the grid. A 409 error from the backend surfaces via the existing `submitError` path. |

### 2.6 Data Flow — Step 4

The `SubscriptionTierAPI` type gains three optional fields (mirroring the backend C-B5 changes):

```typescript
export interface SubscriptionTierAPI {
  // ... existing fields ...
  free_period_days?: number | null;
  requires_payment_method?: boolean;
  signup_cap?: number | null;
}
```

The `tierToCardProps()` mapper in `plan/page.tsx` is replaced by a conditional:
- If `tier.tier_name === "charter"` → render `<CharterTierCard>`.
- Else → render existing `<TierPickerCard>`.

The `handleContinue` flow (lines 179–202) is unchanged for Charter: it calls `PUT /step4` with `selected_tier_id`, then since `selectedTierIsTrial` is false but `requires_payment_method` is also false, the step5 PUT is skipped (the backend handles Charter confirmation in step4). The page navigates to `/signup/ready`.

**Optimistic UI**: The free-period callout ("Free for 90 days. No card needed.") renders immediately from the already-fetched tier data — no loading state, no spinner. This matches §16.8's principle: the UI reflects the selection instantly.

### 2.7 State Coverage — Step 4

| State | Treatment |
|---|---|
| Loading (tiers fetching) | Existing skeleton grid (lines 234–242): 4× `animate-pulse rounded-xl border-2 border-neutral-200 bg-neutral-100 h-64` |
| Error (tiers fetch failed) | Existing error banner (lines 220–233): `border-fault-200 bg-fault-50 text-fault-700` with Retry button |
| Empty (no active tiers) | `<EmptyState>` from `@pilot/ui/states` — "No plans available right now. Please check back later." |
| Populated (Charter tier active) | Single `<CharterTierCard>` centered in the grid |
| Tier closed (409 on submit) | `submitError` banner: `text-fault-600 text-sm` — "This tier has reached its signup cap and is no longer accepting new members." |

---

## 3. Surface 2 — Wizard Step 5: Payment / Confirmation (Two Branches)

### 3.1 Context

The existing `/signup/ready` page shows a celebration header, a summary checklist, a trial callout, and a "Get started →" button. It calls `PUT /step5` with `{ confirmed: true }`.

**What changes**: The page must branch on `requires_payment_method` (returned by `GET /signup/{id}/state` in `collected_data`):

- **`requires_payment_method = true`** (non-Charter): The existing Stripe Elements payment form is shown. This is the **retained** path — the `StripePaymentForm` component is made conditional, not removed. Flipping the flag re-enables it with no code change.
- **`requires_payment_method = false`** (Charter): Skip payment entirely. Show confirmation copy: *"You're set. No charge until {free_period_ends_at}."* with a "Complete Signup" button.

### 3.2 New Component — `Step5Confirmation`

**Location**: `frontend/apps/web/src/features/signup/components/Step5Confirmation.tsx`

This component renders the Charter (no-card) branch of step 5. It replaces the trial callout with a Charter-specific confirmation message.

### 3.3 Pixel Specs — `Step5Confirmation`

```
┌─────────────────────────────────────────────┐
│  (Celebration header — unchanged from       │
│   existing ready/page.tsx)                  │
│                                             │
│  🎉  (existing — w-16 h-16 rounded-full     │
│       bg-margin-50 border-2 border-margin-200)│
│                                             │
│  You're all set, {ownerName}!               │
│  text-2xl font-bold text-neutral-900        │
│                                             │
│  (Summary checklist — unchanged)            │
│  ✓ Account                                  │
│  ✓ Legal agreements                         │
│  ✓ Phone                                     │
│  ✓ Plan: Charter                            │
│                                             │
│  ┌─ Charter confirmation callout ───────┐   │
│  │ bg-brand-50 border border-brand-100   │   │
│  │ rounded-lg px-4 py-3                  │   │
│  │ CheckBadgeIcon (w-5 h-5 text-brand-600)│  │
│  │ "You're set. No charge until          │   │
│  │  Aug 14, 2026."                       │   │
│  │ text-sm text-brand-700                │   │
│  └────────────────────────────────────────┘   │
│                                             │
│  ┌─ Complete Signup button ─────────────┐   │
│  │ bg-brand-600 text-white rounded-lg   │   │
│  │ py-3 px-6 text-sm font-semibold      │   │
│  │ w-full                                │   │
│  └────────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
```

| Element | Spec |
|---|---|
| Confirmation callout | `rounded-lg bg-brand-50 border border-brand-100 px-4 py-3 flex items-start gap-3` |
| Callout icon | `CheckBadgeIcon` (Heroicons outline, `w-5 h-5 text-brand-600 flex-shrink-0`) |
| Callout text | `text-sm text-brand-700` — "You're set. No charge until {formatted date}." |
| Complete Signup button | `w-full py-3 px-6 rounded-lg text-sm font-semibold bg-brand-600 text-white hover:bg-brand-800 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-2` |
| Submitting state | `opacity-40 cursor-not-allowed bg-brand-600 text-white` with label "Setting up…" |

### 3.4 Date Formatting

`free_period_ends_at` arrives as an ISO 8601 string (e.g., `"2026-11-02T18:37:42Z"`). Format as a human-readable date:

```typescript
const formattedDate = new Date(freePeriodEndsAt).toLocaleDateString("en-US", {
  month: "short",
  day: "numeric",
  year: "numeric",
});
// → "Nov 2, 2026"
```

Copy template: `"You're set. No charge until {formattedDate}."`

### 3.5 Icon Inventory — Step 5

| Element | Heroicons 2.0 name | Variant | Size |
|---|---|---|---|
| Confirmation callout | `CheckBadgeIcon` | outline | `w-5 h-5` |

### 3.6 Interaction States — `Step5Confirmation`

| State | Visual |
|---|---|
| Default (button) | `bg-brand-600 text-white` |
| Hover (button) | `bg-brand-800` |
| Focus-visible (button) | `ring-2 ring-brand-600 ring-offset-2` |
| Active (button, mouse down) | `bg-brand-700` |
| Disabled / submitting | `opacity-40 cursor-not-allowed` + label "Setting up…" |
| Error (submit failed) | `text-fault-600 text-sm text-center` alert below button |

### 3.7 Branching Logic — `ready/page.tsx`

The `ready/page.tsx` `useEffect` (lines 54–93) fetches `GET /signup/{id}/state`. The C-B5 backend adds `requires_payment_method` and `free_period_ends_at` to `collected_data`. The page stores these in state:

```typescript
const [requiresPaymentMethod, setRequiresPaymentMethod] = useState(true);
const [freePeriodEndsAt, setFreePeriodEndsAt] = useState<string | null>(null);
```

In the `useEffect` `.then()`:
```typescript
setRequiresPaymentMethod(res.data.collected_data?.requires_payment_method ?? true);
setFreePeriodEndsAt(res.data.collected_data?.free_period_ends_at ?? null);
```

Render logic:
- If `requiresPaymentMethod === false` → render `<Step5Confirmation>` (Charter path).
- If `requiresPaymentMethod === true` → render the existing Stripe Elements payment form (retained, made conditional). The existing trial callout is replaced by a payment-method callout.

**The `StripePaymentForm` component is retained and made conditional, not removed.** Flipping `requires_payment_method` to `true` re-enables it with no code change.

### 3.8 State Coverage — Step 5

| State | Treatment |
|---|---|
| Loading (state fetching) | Existing skeleton: `animate-pulse` placeholder blocks matching the summary layout |
| Error (state fetch failed) | Redirect to `/signup/account` (existing behavior, lines 89–92) |
| Charter (`requires_payment_method=false`) | `<Step5Confirmation>` with "You're set. No charge until {date}." |
| Non-Charter (`requires_payment_method=true`) | Existing Stripe Elements form + payment callout |
| Submit error | `text-fault-600 text-sm text-center` alert |

---

## 4. Surface 3 — Onboarding Checklist: "Set up text messaging" Item

### 4.1 Context

The existing `OnboardingChecklistWidget` renders a list of `ChecklistItem` rows from the `CHECKLIST_ITEMS` array in `onboarding/types.ts`. Each item has a `key`, `label`, `description`, `actionLabel`, `actionRoute`, `isSkippable`, and `isAutoComplete`.

**What changes**:
1. The `OnboardingChecklistState` and `OnboardingChecklistResponse` types gain a `messagingSetup` / `messaging_setup` field (mirroring the C-B5 backend migration).
2. The `CHECKLIST_ITEMS` array gains a new entry for "Set up text messaging".
3. The new item is **Charter-only**: it is only displayed when the tenant is on the Charter tier. This is a conditional render in the widget, not a backend filter.
4. The new item has an inline cost disclosure that doesn't fit the existing `ChecklistItem` layout — it needs a secondary description line.

### 4.2 New Component — `MessagingSetupChecklistItem`

**Location**: `frontend/apps/web/src/features/onboarding/components/MessagingSetupChecklistItem.tsx`

A specialized checklist row that extends the `ChecklistItem` visual pattern with a secondary cost-disclosure line. It is rendered conditionally by the widget when the tenant is on the Charter tier.

**Why a new component instead of extending `ChecklistItem`**: The cost disclosure ("Carrier registration runs about $13–$37…") is a multi-line secondary description that the existing `ChecklistItem` `description` field (currently unused in the render) doesn't support. Adding a `secondaryDescription` prop to `ChecklistItem` would change its interface for all 8 existing items. A feature-specific component is cleaner.

### 4.3 Pixel Specs — `MessagingSetupChecklistItem`

```
┌──────────────────────────────────────────────────┐
│  (Same row structure as ChecklistItem, plus      │
│   a secondary cost-disclosure line below)        │
│                                                  │
│  ○  Set up text messaging        Set up →        │
│     text-sm font-medium text-neutral-900         │
│     ┌─ Cost disclosure ──────────────────────┐   │
│     │ InformationCircleIcon (w-3.5 h-3.5     │   │
│     │   text-neutral-400)                    │   │
│     │ "Carrier registration costs, which     │   │
│     │  vary between $21–$29 upfront and      │   │
│     │  $3–$13 monthly (est.), depending      │   │
│     │  on your business setup. This amount.  │   │
│     │  will go directly to the phone         │   │
│     │  carrier - we don't take any of it."   │   │
│     │ text-xs text-neutral-500               │   │
│     └────────────────────────────────────────┘   │
└──────────────────────────────────────────────────┘
```

| Element | Spec |
|---|---|
| Row container | `flex items-start gap-3 py-2` (note: `items-start` not `items-center` — the secondary line needs top alignment) |
| Status icon | Same as `ChecklistItem`: `w-5 h-5` — complete = `text-margin-600` checkmark, incomplete = `w-4 h-4 rounded-full border-2 border-neutral-300` |
| Label | `text-sm font-medium text-neutral-900` (incomplete) / `line-through text-neutral-400` (complete) |
| Cost disclosure container | `flex items-start gap-1.5 mt-1 ml-0` |
| Cost disclosure icon | `InformationCircleIcon` (Heroicons outline, `w-3.5 h-3.5 text-neutral-400 flex-shrink-0 mt-0.5`) |
| Cost disclosure text | `text-xs text-neutral-500` |
| Action link | `text-xs font-medium text-brand-600 hover:text-brand-800 focus:outline-none focus-visible:underline` — "Set up →" |
| Action route | `/settings/communications/sms-compliance` (placeholder — the 10DLC flow is C-B9, not yet built) |

### 4.4 Icon Inventory — Checklist Item

| Element | Heroicons 2.0 name | Variant | Size |
|---|---|---|---|
| Cost disclosure | `InformationCircleIcon` | outline | `w-3.5 h-3.5` |
| Complete checkmark | custom SVG (existing pattern) | — | `w-5 h-5` |

### 4.5 Interaction States — `MessagingSetupChecklistItem`

| State | Visual |
|---|---|
| Incomplete | `border-neutral-300` circle icon, `text-neutral-900` label, "Set up →" link visible |
| Complete | `text-margin-600` checkmark, `line-through text-neutral-400` label, no action link |
| Hover (action link) | `text-brand-800` |
| Focus-visible (action link) | `underline` |

### 4.6 Type Changes — `onboarding/types.ts`

Add `messagingSetup` to `OnboardingChecklistState`:

```typescript
export interface OnboardingChecklistState {
  // ... existing fields ...
  messagingSetup: boolean;
}
```

Add `messaging_setup` to `OnboardingChecklistResponse`:

```typescript
export interface OnboardingChecklistResponse {
  // ... existing fields ...
  messaging_setup: boolean;
}
```

Update `mapChecklistResponse()` to include `messagingSetup: res.messaging_setup`.

Update `isChecklistComplete()` to include `state.messagingSetup` in the AND chain.

Add to `CHECKLIST_ITEMS` — inserted after `catalogSetup` (position 5), before `quickbooksConnected`:

```typescript
{
  key: "messagingSetup",
  label: "Set up text messaging",
  description: "Register your business for 10DLC SMS messaging",
  actionLabel: "Set up",
  actionRoute: "/settings/communications/sms-compliance",
  isSkippable: false,
  isAutoComplete: false,
},
```

### 4.7 Charter-Only Conditional Render

The widget receives the tenant's tier info. The simplest approach: the dashboard page already has access to `user` from `useAuth()`. Add a `tierName` prop to `OnboardingChecklistWidget`:

```typescript
interface OnboardingChecklistWidgetProps {
  tenantId: string;
  checklistState: OnboardingChecklistState;
  tierName?: string; // "charter" | "starter" | "professional" | "enterprise" | ...
}
```

In the widget's `CHECKLIST_ITEMS.map()`:
- If `item.key === "messagingSetup"` and `tierName !== "charter"` → skip (return `null`).
- If `item.key === "messagingSetup"` and `tierName === "charter"` → render `<MessagingSetupChecklistItem>` instead of `<ChecklistItem>`.

The dashboard page passes `tierName` from the user object (the C-B5 backend includes tier info in the auth response, or it can be fetched separately).

### 4.8 State Coverage — Checklist Item

| State | Treatment |
|---|---|
| Incomplete (Charter tenant) | Circle icon + label + cost disclosure + "Set up →" link |
| Complete | Checkmark + strikethrough label, no action link |
| Non-Charter tenant | Not rendered (conditional) |

---

## 5. Surface 4 — Charter Member Badge

### 5.1 Context

A small badge/pill shown on the dashboard. It communicates two things:
1. The tenant is a Charter Member, with their number: "Charter Member #N"
2. The current `free_period_ends_at` as a date: "Free until Aug 14, 2026"

**Owner-only RBAC** (Q#5 resolved): visible only to the tenant owner, not to employees/techs. Gate with `<RoleGate role="owner">`.

**No countdown**: Always renders the *current* `free_period_ends_at` as a date, never a countdown from the original grant. This is what makes silent extension (§4.4) invisible to the user.

### 5.2 Component-Existence Check

There is no generic `Badge` or `Pill` primitive in `packages/ui/src/index.ts`. The existing badge-like components (`ExpiryCountdownBadge`, `SmsOptOutBadge`, `PendingBadge`) are all domain-specific. The `CharterMemberBadge` is also domain-specific (Charter program) and lives in the dashboard feature folder.

**Decision**: New feature-specific component. Not a shared primitive.

### 5.3 New Component — `CharterMemberBadge`

**Location**: `frontend/apps/web/src/features/dashboard/components/CharterMemberBadge.tsx`

### 5.4 Pixel Specs — `CharterMemberBadge`

```
┌──────────────────────────────────────────────────┐
│  inline-flex items-center gap-2                  │
│  rounded-full px-3 py-1                          │
│  bg-brand-50 border border-brand-200             │
│                                                  │
│  StarIcon (w-4 h-4 text-brand-600)               │
│  "Charter Member #7"                             │
│  text-sm font-semibold text-brand-700            │
│  ── divider ──                                   │
│  "Free until Nov 2, 2026"                        │
│  text-xs text-brand-600                          │
└──────────────────────────────────────────────────┘
```

Two layout options depending on available space:

**Option A — Single pill (compact, header placement)**:
```
[★ Charter Member #7 · Free until Nov 2, 2026]
```
Single `rounded-full` pill with a middot separator between the member number and the free-until date.

**Option B — Stacked (dashboard content area)**:
```
[★ Charter Member #7]
[Free until Nov 2, 2026]
```
Two-line stack if placed in a wider content area.

**Recommended**: Option A (single pill) placed in the dashboard page header, next to the "Dashboard" H1.

| Element | Spec |
|---|---|
| Container | `inline-flex items-center gap-2 rounded-full px-3 py-1 bg-brand-50 border border-brand-200` |
| Star icon | `StarIcon` (Heroicons solid, `w-4 h-4 text-brand-600`) |
| Member number text | `text-sm font-semibold text-brand-700` — "Charter Member #{charterMemberNumber}" |
| Separator | `text-brand-300` middot "·" |
| Free-until text | `text-xs text-brand-600` — "Free until {formattedDate}" |

### 5.5 Date Formatting

Same as Step 5 (§3.4): `toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })`.

Copy template: `"Free until {formattedDate}"`

### 5.6 Icon Inventory — Badge

| Element | Heroicons 2.0 name | Variant | Size |
|---|---|---|---|
| Charter star | `StarIcon` | solid | `w-4 h-4` |

### 5.7 Interaction States — `CharterMemberBadge`

The badge is **non-interactive** (display-only). No hover, focus, or active states. It is an informational element, not a button or link.

| State | Visual |
|---|---|
| Default | `bg-brand-50 border border-brand-200` |
| No `charter_member_number` | Not rendered (returns `null`) |
| No `free_period_ends_at` | Renders member number only, omits the "Free until" portion |

### 5.8 RBAC Gate

Wrap the badge in `<RoleGate role="owner">`:

```tsx
<RoleGate role="owner">
  <CharterMemberBadge
    charterMemberNumber={charterMemberNumber}
    freePeriodEndsAt={freePeriodEndsAt}
  />
</RoleGate>
```

Employees (`office_staff`), techs (`tech`), and operators do not see the badge. This is **hide-not-disable** per the RBAC rule — `RoleGate` returns `null` for unauthorized roles.

### 5.9 Dashboard Wiring

In `dashboard/page.tsx`, the header currently is:

```tsx
<header className="flex items-center justify-between px-6 py-4 bg-white border-b border-neutral-200">
  <h1 className="text-h1 text-neutral-900">Dashboard</h1>
</header>
```

Updated to include the badge next to the H1:

```tsx
<header className="flex items-center justify-between px-6 py-4 bg-white border-b border-neutral-200">
  <div className="flex items-center gap-3">
    <h1 className="text-h1 text-neutral-900">Dashboard</h1>
    <RoleGate role="owner">
      {charterMemberNumber && (
        <CharterMemberBadge
          charterMemberNumber={charterMemberNumber}
          freePeriodEndsAt={freePeriodEndsAt}
        />
      )}
    </RoleGate>
  </div>
</header>
```

The `charterMemberNumber` and `freePeriodEndsAt` values come from the user object (the C-B5 backend includes them in the auth response `collected_data`, or they can be fetched via a separate query). The dashboard page reads them from `useAuth()`.

### 5.10 State Coverage — Badge

| State | Treatment |
|---|---|
| Owner + Charter member | Badge rendered with member number + free-until date |
| Owner + non-Charter | Not rendered (`charterMemberNumber` is null) |
| Non-owner (any role) | Not rendered (`RoleGate` hides) |
| Owner + Charter + no `free_period_ends_at` | Badge renders member number only, omits "Free until" portion |
| Loading (auth resolving) | Not rendered until `user` is populated |

---

## 6. Animation Spec

| Surface | Animation | CSS | Reduced-motion fallback |
|---|---|---|---|
| `CharterTierCard` hover | Subtle shadow lift | `transition-all 150ms ease-in-out` on card container | `@media (prefers-reduced-motion: reduce) → no transition` |
| `CharterTierCard` selection | Border + bg color change | `transition-all 150ms ease-in-out` | Instant color change |
| `Step5Confirmation` button | Background color on hover | `transition-colors 150ms ease-in-out` | Instant |
| `CharterMemberBadge` | None (display-only) | — | — |
| Checklist progress bar | Width transition on completion | `transition-all 200ms ease-in-out` (existing) | Instant width change |

All transitions must have a `@media (prefers-reduced-motion: reduce)` fallback that disables the transition (instant or opacity-only).

---

## 7. Accessibility Notes

### 7.1 Color-Independent Status

- **Charter tier card**: The "Free for 90 days" callout uses `text-margin-700` on `bg-margin-50` — the text label "Free for 90 days. No card needed." is the primary signal, not the green color alone.
- **Charter Member badge**: The `StarIcon` (solid) provides a non-color signal alongside the `bg-brand-50` background. The text "Charter Member #N" is the primary identifier.
- **Checklist item status**: The existing `ChecklistItem` pattern uses distinct icons (checkmark circle vs. empty circle) — not color alone. The new `MessagingSetupChecklistItem` follows the same pattern.

### 7.2 Target Sizes

| Element | Target size | Meets WCAG 2.5.8 (≥24×24px)? |
|---|---|---|
| `CharterTierCard` (entire card is clickable) | Full card (~300×400px) | ✅ |
| `CharterTierCard` CTA button | `w-full py-2 px-4` (~44px tall) | ✅ |
| `Step5Confirmation` button | `w-full py-3 px-6` (~48px tall) | ✅ |
| Checklist "Set up →" link | Text link — spec `min-h-[24px] min-w-[24px]` padding | ✅ (add `py-1` to ensure 24px height) |
| `CharterMemberBadge` | Non-interactive — no target needed | N/A |

### 7.3 Focus Order & Focus-Visible

- **Step 4**: The `CharterTierCard` is a `role="radio"` element (following `TierPickerCard` pattern). `tabIndex={0}`, `focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-2`. The CTA button inside is also focusable with its own ring.
- **Step 5**: The "Complete Signup" button is the primary focus target. `focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-2`.
- **Checklist**: The "Set up →" link uses `focus-visible:underline`. Tab order follows visual order.
- **Badge**: Non-interactive, not in tab order.

### 7.4 Modal Focus Trap

No modals in this batch. The wizard steps are full-page routes, not modals.

### 7.5 Screen Reader Announcements

- The `CharterTierCard` uses `role="radio"` with `aria-checked={isSelected}` (following `TierPickerCard`).
- The `CharterMemberBadge` uses `aria-label="Charter Member number {N}, free until {date}"` to ensure screen readers announce the full context.
- The cost disclosure in `MessagingSetupChecklistItem` is plain text — naturally announced by screen readers.

### 7.6 Contrast Ratios

All token pairings are pre-validated per the design-system reference:
- `text-brand-700 on bg-brand-50` — ✅ (≥4.5:1)
- `text-margin-700 on bg-margin-50` — ✅
- `text-neutral-900 on bg-white` — ✅
- `text-neutral-500 on bg-white` — ✅ (≥4.5:1 for body text)
- `text-brand-600 on bg-brand-50` — ✅

---

## 8. Responsive Notes

Primary spec is for 1280px+ desktop. Reflow behavior:

| Surface | 1280px+ | 1024px | 768px |
|---|---|---|---|
| Step 4 tier grid | Single card, centered, `max-w-md mx-auto` | Same | Same |
| Step 5 confirmation | `max-w-lg mx-auto` | Same | Same |
| Checklist widget | Full width in dashboard content area | Same | Same |
| Charter badge | Inline next to H1 | Inline next to H1 | Stacks below H1 (`flex-col` on header) |

The signup wizard pages are already single-column and mobile-reflow-friendly. No table layouts to worry about.

---

## 9. Implementation Notes

### 9.1 Type Sync

After the C-B5 backend ships, run `pnpm sync-api-types` to get the updated OpenAPI types. The `SubscriptionTierAPI` and `SignupStateResponse` types must be updated to include:
- `free_period_days`, `requires_payment_method`, `signup_cap` on `SubscriptionTierAPI`
- `free_period_ends_at`, `requires_payment_method`, `charter_member_number` in `SignupStateResponse.collected_data`
- `messaging_setup` on `OnboardingChecklistResponse`

### 9.2 Hook Changes

- `useSubscriptionTiers`: No change — already filters `is_active`. The Charter tier will be the only active tier during Charter.
- `useSignupWizard`: The `RESUME` action (lines 123–144) must be extended to carry `freePeriodEndsAt`, `requiresPaymentMethod`, and `charterMemberNumber` from `collected_data` into `WizardFormData`.
- `useOnboardingChecklist`: No change — `mapChecklistResponse()` handles the new field.

### 9.3 localStorage / sessionStorage Keys

No new keys. The existing `WIZARD_TENANT_ID_KEY` (`"pilot_signup_tenant_id"`) is unchanged.

### 9.4 10DLC Route Placeholder

The "Set up text messaging" checklist item links to `/settings/communications/sms-compliance`. This route already exists (see the file listing: `(authed)/settings/communications/sms-compliance/page.tsx`). The actual 10DLC flow is built in C-B9 — for now, the link navigates to the existing SMS compliance settings page.

### 9.5 Charter Badge Data Source

The `charterMemberNumber` and `freePeriodEndsAt` for the dashboard badge come from the authenticated user object. The C-B5 backend includes these in the `GET /signup/{id}/state` response, but after wizard completion they should be available on the tenant/user profile endpoint. The React Engineer should verify the exact field path in the auth response after `pnpm sync-api-types`.

---

## 10. Component Manifest

| Component | Path | New/Modified | Description |
|---|---|---|---|
| `CharterTierCard` | `frontend/apps/web/src/features/signup/components/CharterTierCard.tsx` | New | Step 4 Charter tier card with free-period callout |
| `Step5Confirmation` | `frontend/apps/web/src/features/signup/components/Step5Confirmation.tsx` | New | Step 5 Charter confirmation branch (no-card path) |
| `MessagingSetupChecklistItem` | `frontend/apps/web/src/features/onboarding/components/MessagingSetupChecklistItem.tsx` | New | Checklist item with cost disclosure |
| `CharterMemberBadge` | `frontend/apps/web/src/features/dashboard/components/CharterMemberBadge.tsx` | New | Owner-only badge showing charter_member_number + free-until date |
| `plan/page.tsx` | `frontend/apps/web/src/app/signup/plan/page.tsx` | Modified | Conditional render: `CharterTierCard` for charter tier, `TierPickerCard` for others |
| `ready/page.tsx` | `frontend/apps/web/src/app/signup/ready/page.tsx` | Modified | Branch on `requires_payment_method`: `Step5Confirmation` (Charter) vs Stripe Elements (non-Charter) |
| `signup/types.ts` | `frontend/apps/web/src/features/signup/types.ts` | Modified | Add `free_period_days`, `requires_payment_method`, `signup_cap` to `SubscriptionTierAPI`; add Charter fields to `SignupStateResponse.collected_data` and `WizardFormData` |
| `onboarding/types.ts` | `frontend/apps/web/src/features/onboarding/types.ts` | Modified | Add `messagingSetup` / `messaging_setup`; add `messagingSetup` to `CHECKLIST_ITEMS`; update `mapChecklistResponse()` and `isChecklistComplete()` |
| `OnboardingChecklistWidget` | `frontend/apps/web/src/features/onboarding/components/OnboardingChecklistWidget.tsx` | Modified | Add `tierName` prop; conditional render of `MessagingSetupChecklistItem` for Charter tenants |
| `dashboard/page.tsx` | `frontend/apps/web/src/app/(authed)/dashboard/page.tsx` | Modified | Add `CharterMemberBadge` (owner-only) to header; pass `tierName` to checklist widget |

---

## 11. Handoff Gate

This spec is ready for Tom's review. Implementation starts only after approval.
