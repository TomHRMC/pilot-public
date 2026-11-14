# Implementation Prompt: C-B5 (Part B — React Engineer) — Wizard Step 4/5 Conditional + Checklist + Badge

**Mode**: Pilot React Engineer  
**Batch**: C-B5 Part B  
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §2.0 row 14j  
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-c-b5-design.md`  
**UI design spec**: `dev-docs/architecture-design/batch-designs/batch-c-b5-ui-design-spec.md` — **Tom-approved** ✅  
**Backend companion**: C-B5 Part A ✅ COMPLETE 2026-08-04 — `pnpm sync-api-types` must run first  
**Estimated session**: 3–4 hours  
**Platform**: Web only (`frontend/apps/web`)

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-react-engineer/react-engineer-rules.md`** — in full
- **`dev-docs/architecture-design/batch-designs/batch-c-b5-ui-design-spec.md`** — every section (1–11). This is the Tom-approved UI spec. Follow it exactly — pixel specs, token names, component paths, and interaction states are binding.

Critical rules for this batch:

- **Rule 1.1**: Before writing ANY hook or API call, verify the endpoint exists in `backend/openapi_schema_map.md`. The C-B5 Part A backend added `free_period_ends_at`, `requires_payment_method`, `charter_member_number` to `GET /signup/{id}/state` and `messaging_setup` to `GET /onboarding/checklist`.
- **Rule 1.3**: Run `pnpm sync-api-types` before starting — all TypeScript types for backend payloads come from `@pilot/shared-types`, never hand-written interfaces.
- **Rule 2**: All API calls use `apiClient` from `@pilot/shared-api`. `fetch()` is permanently banned for `/api/v1/...` calls.
- **Rule 7**: Check `packages/ui/src/index.ts` before creating any new component — `<RoleGate>`, `<TierPickerCard>`, `<EmptyState>`, `<LoadingState>`, `<ErrorState>` are all available.
- **Rule 9**: Route files in `apps/web/src/app/` MUST be thin server components — no `"use client"`, no data fetching. All logic goes in feature components.
- **Rule 10**: If ANY test fails during your work — even one that appears to be pre-existing — **you must fix it before declaring the batch done**.
- **Rule 11 (React Compiler)**: Do NOT hand-write `useMemo`/`useCallback`/`React.memo` — the compiler handles it. Keep components pure.
- **Rule 12 (TanStack Query v5)**: Object-form API only. `gcTime` not `cacheTime`; `isPending` not `isLoading`. Set `retry: false` for mutation hooks.
- **Rule 15 (WCAG 2.2 AA)**: Every new surface must satisfy Focus Not Obscured, Target Size (≥24×24px), non-color-only errors. The UI spec §7 has the accessibility notes — follow them.

---

## Pre-Work: Sync API Types

**This is the first step — before anything else.** The C-B5 Part A backend added new fields to the OpenAPI spec. You need the updated TypeScript types.

```bash
cd <repo>/frontend
pnpm sync-api-types
```

This regenerates `packages/shared-types/src/api-schema.d.ts` from `backend/openapi.json`. After running, verify the new fields are present:

- `SubscriptionTierResponse` should include `free_period_days`, `requires_payment_method`, `signup_cap`
- `SignupStateResponse.collected_data` should include `free_period_ends_at`, `requires_payment_method`, `charter_member_number`
- `OnboardingChecklistResponse` should include `messaging_setup`

If any field is missing → STOP and ask Tom (the backend may not have been committed).

---

## Pre-Work: Regression Baseline

```bash
cd <repo>/frontend
pnpm --filter pilot-web test -- --run 2>&1 | tail -5
```

Record the exact count: **`X passed, Y failed`**.

> **If any tests are already failing**: Do NOT treat them as "pre-existing" and proceed. Either confirm with Tom or fix before starting.

---

## Pre-Work: Endpoint Verification

Verify these endpoints exist in `backend/openapi_schema_map.md`:

| Endpoint | Method | New fields from C-B5 Part A |
|---|---|---|
| `/api/v1/signup/{tenant_id}/state` | GET | `collected_data.free_period_ends_at`, `collected_data.requires_payment_method`, `collected_data.charter_member_number` |
| `/api/v1/subscription-tiers` | GET | `free_period_days`, `requires_payment_method`, `signup_cap` on each tier |
| `/api/v1/tenants/{tenant_id}/onboarding/checklist` | GET | `messaging_setup: boolean` |

---

## Pre-Work: Read These Source Files

Use `read_file` on each of these before writing any code:

```
frontend/apps/web/src/app/signup/plan/page.tsx          ← why: step 4 tier picker — add CharterTierCard conditional
frontend/apps/web/src/app/signup/ready/page.tsx         ← why: step 5 — add Step5Confirmation branch
frontend/apps/web/src/features/signup/types.ts          ← why: SubscriptionTierAPI + SignupStateResponse + WizardFormData types
frontend/apps/web/src/features/signup/hooks/useSignupWizard.ts  ← why: RESUME action — carry new fields
frontend/apps/web/src/features/signup/hooks/useSubscriptionTiers.ts ← why: already filters is_active
frontend/apps/web/src/features/onboarding/types.ts      ← why: OnboardingChecklistState + CHECKLIST_ITEMS + mapChecklistResponse
frontend/apps/web/src/features/onboarding/components/OnboardingChecklistWidget.tsx ← why: add tierName prop + conditional render
frontend/apps/web/src/features/onboarding/components/ChecklistItem.tsx ← why: visual pattern reference for MessagingSetupChecklistItem
frontend/apps/web/src/app/(authed)/dashboard/page.tsx   ← why: add CharterMemberBadge to header + pass tierName to checklist
frontend/packages/ui/src/index.ts                       ← why: check RoleGate, TierPickerCard, EmptyState, LoadingState exports
frontend/packages/ui/src/role-gate/RoleGate.tsx         ← why: owner-only RBAC gate for badge
frontend/packages/ui/src/tier-picker-card/TierPickerCard.tsx ← why: visual pattern reference for CharterTierCard
frontend/apps/web/src/mocks/handlers/index.ts            ← why: barrel registration for MSW handlers
```

---

## Design Decisions

1. **CharterTierCard is a new feature-specific component**, not an extension of `TierPickerCard`. The `TierPickerCard` interface is FROZEN after FE-B13. The Charter card has a fixed "$49/month" price display, a free-period callout, and a feature list — all Charter-specific. Per §6 component placement: domain-specific → `features/signup/components/`.

2. **Step5Confirmation replaces the trial callout** for Charter tenants. The existing `StripePaymentForm` is **retained and made conditional**, not removed. Flipping `requires_payment_method` to `true` re-enables it with no code change.

3. **MessagingSetupChecklistItem is a new component** because the cost disclosure (multi-line secondary description) doesn't fit the existing `ChecklistItem` interface. Adding a `secondaryDescription` prop would change all 8 existing items.

4. **CharterMemberBadge is owner-only** (Q#5 resolved). Wrapped in `<RoleGate role="owner">`. Non-interactive (display-only). No `Badge`/`Pill` primitive exists in `packages/ui` — this is a feature-specific component in `features/dashboard/components/`.

5. **Charter-only checklist item**: The `MessagingSetupChecklistItem` is only rendered when `tierName === "charter"`. The widget receives `tierName` as a new prop from the dashboard page.

6. **10DLC route placeholder**: The "Set up text messaging" item links to `/settings/communications/sms-compliance` — this route already exists. The actual 10DLC flow is C-B9.

---

## Task 1 — Update Types (`signup/types.ts` + `onboarding/types.ts`)

### `signup/types.ts`

Add to `SubscriptionTierAPI`:
```typescript
free_period_days?: number | null;
requires_payment_method?: boolean;
signup_cap?: number | null;
```

Add to `SignupStateResponse.collected_data` (or the equivalent type):
```typescript
free_period_ends_at?: string | null;
requires_payment_method?: boolean;
charter_member_number?: number | null;
```

Add to `WizardFormData` (the form state type used by `useSignupWizard`):
```typescript
freePeriodEndsAt?: string | null;
requiresPaymentMethod?: boolean;
charterMemberNumber?: number | null;
```

### `onboarding/types.ts`

Add to `OnboardingChecklistState`:
```typescript
messagingSetup: boolean;
```

Add to `OnboardingChecklistResponse`:
```typescript
messaging_setup: boolean;
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

**Intermediate test run:** `pnpm --filter pilot-web test -- --run 2>&1 | tail -5`

---

## Task 2 — Create `CharterTierCard` Component

**Path**: `frontend/apps/web/src/features/signup/components/CharterTierCard.tsx`

Follow the UI spec §2.3 pixel specs exactly. Key elements:
- `relative flex flex-col gap-4 rounded-xl border-2 p-6 transition-all`
- Featured badge: `absolute -top-3 left-1/2 -translate-x-1/2 bg-brand-600 text-white px-3 py-0.5 rounded-full text-xs font-semibold` — "Charter Program"
- Price: `text-2xl font-bold text-neutral-900` — "$49" + `text-sm text-neutral-500` — "/mo"
- Free-period callout: `bg-margin-50 border border-margin-200 rounded-md px-3 py-2 flex items-center gap-2` with `GiftIcon` (Heroicons outline, `w-4 h-4 text-margin-600`) + "Free for 90 days. No card needed." (`text-sm text-margin-700 font-medium`)
- Feature list with `CheckCircleIcon` (Heroicons outline, `w-4 h-4 text-margin-600`)
- CTA button: `mt-auto w-full py-2 px-4 rounded-lg text-sm font-semibold bg-brand-600 text-white hover:bg-brand-800`
- `role="radio"` with `aria-checked={isSelected}` (following `TierPickerCard` pattern)
- `focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-2`

Props:
```typescript
interface CharterTierCardProps {
  tier: SubscriptionTierAPI;
  isSelected: boolean;
  onSelect: () => void;
}
```

The free-period text is derived from `tier.free_period_days`: `"Free for {free_period_days} days. No card needed."`

**Intermediate test run:** `pnpm --filter pilot-web test -- --run 2>&1 | tail -5`

---

## Task 3 — Update `plan/page.tsx` (Step 4)

In `frontend/apps/web/src/app/signup/plan/page.tsx`:

Replace the `tierToCardProps()` mapper with a conditional render:
- If `tier.tier_name === "charter"` → render `<CharterTierCard>`
- Else → render existing `<TierPickerCard>`

The `handleContinue` flow is unchanged — it calls `PUT /step4` with `selected_tier_id`, then navigates to `/signup/ready`.

**Tier-closed 409**: If the backend returns 409 (tier-closed), surface via the existing `submitError` banner: `text-fault-600 text-sm` — "This tier has reached its signup cap and is no longer accepting new members."

**Intermediate test run:** `pnpm --filter pilot-web test -- --run 2>&1 | tail -5`

---

## Task 4 — Create `Step5Confirmation` Component

**Path**: `frontend/apps/web/src/features/signup/components/Step5Confirmation.tsx`

Follow the UI spec §3.3 pixel specs. Key elements:
- Confirmation callout: `rounded-lg bg-brand-50 border border-brand-100 px-4 py-3 flex items-start gap-3`
- `CheckBadgeIcon` (Heroicons outline, `w-5 h-5 text-brand-600 flex-shrink-0`)
- Callout text: `text-sm text-brand-700` — "You're set. No charge until {formattedDate}."
- Complete Signup button: `w-full py-3 px-6 rounded-lg text-sm font-semibold bg-brand-600 text-white hover:bg-brand-800 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-2`
- Submitting state: `opacity-40 cursor-not-allowed` + label "Setting up…"
- Error: `text-fault-600 text-sm text-center` alert below button

Date formatting (UI spec §3.4):
```typescript
const formattedDate = new Date(freePeriodEndsAt).toLocaleDateString("en-US", {
  month: "short",
  day: "numeric",
  year: "numeric",
});
```

Props:
```typescript
interface Step5ConfirmationProps {
  freePeriodEndsAt: string;
  ownerName: string;
  onConfirm: () => void;
  isSubmitting: boolean;
  submitError: string | null;
}
```

**Intermediate test run:** `pnpm --filter pilot-web test -- --run 2>&1 | tail -5`

---

## Task 5 — Update `ready/page.tsx` (Step 5)

In `frontend/apps/web/src/app/signup/ready/page.tsx`:

1. Add state for the new fields:
```typescript
const [requiresPaymentMethod, setRequiresPaymentMethod] = useState(true);
const [freePeriodEndsAt, setFreePeriodEndsAt] = useState<string | null>(null);
```

2. In the `useEffect` that fetches `GET /signup/{id}/state`, extract from `collected_data`:
```typescript
setRequiresPaymentMethod(res.data.collected_data?.requires_payment_method ?? true);
setFreePeriodEndsAt(res.data.collected_data?.free_period_ends_at ?? null);
```

3. Render logic:
- If `requiresPaymentMethod === false` → render `<Step5Confirmation>` (Charter path)
- If `requiresPaymentMethod === true` → render existing Stripe Elements form (retained, made conditional)

The existing trial callout is replaced by the Charter confirmation callout for the `false` branch.

**Intermediate test run:** `pnpm --filter pilot-web test -- --run 2>&1 | tail -5`

---

## Task 6 — Create `MessagingSetupChecklistItem` Component

**Path**: `frontend/apps/web/src/features/onboarding/components/MessagingSetupChecklistItem.tsx`

Follow the UI spec §4.3 pixel specs. Key elements:
- Row container: `flex items-start gap-3 py-2` (note: `items-start` not `items-center`)
- Status icon: same as `ChecklistItem` — complete = `text-margin-600` checkmark, incomplete = `w-4 h-4 rounded-full border-2 border-neutral-300`
- Label: `text-sm font-medium text-neutral-900` (incomplete) / `line-through text-neutral-400` (complete)
- Cost disclosure: `flex items-start gap-1.5 mt-1` with `InformationCircleIcon` (Heroicons outline, `w-3.5 h-3.5 text-neutral-400 flex-shrink-0 mt-0.5`) + `text-xs text-neutral-500`
- Cost disclosure text: "Carrier registration costs, which vary between $21–$29 upfront and $3–$13 monthly (est.), depending on your business setup. This amount will go directly to the phone carrier - we don't take any of it."
- Action link: `text-xs font-medium text-brand-600 hover:text-brand-800 focus:outline-none focus-visible:underline` — "Set up →"
- Action route: `/settings/communications/sms-compliance`

Props:
```typescript
interface MessagingSetupChecklistItemProps {
  isComplete: boolean;
  onNavigate: (route: string) => void;
}
```

**Intermediate test run:** `pnpm --filter pilot-web test -- --run 2>&1 | tail -5`

---

## Task 7 — Update `OnboardingChecklistWidget` + `onboarding/types.ts`

In `OnboardingChecklistWidget`:
1. Add `tierName?: string` prop
2. In the `CHECKLIST_ITEMS.map()`:
   - If `item.key === "messagingSetup"` and `tierName !== "charter"` → skip (return `null`)
   - If `item.key === "messagingSetup"` and `tierName === "charter"` → render `<MessagingSetupChecklistItem>` instead of `<ChecklistItem>`

**Intermediate test run:** `pnpm --filter pilot-web test -- --run 2>&1 | tail -5`

---

## Task 8 — Create `CharterMemberBadge` Component

**Path**: `frontend/apps/web/src/features/dashboard/components/CharterMemberBadge.tsx`

Follow the UI spec §5.4 pixel specs (Option A — single pill). Key elements:
- Container: `inline-flex items-center gap-2 rounded-full px-3 py-1 bg-brand-50 border border-brand-200`
- `StarIcon` (Heroicons solid, `w-4 h-4 text-brand-600`)
- Member number: `text-sm font-semibold text-brand-700` — "Charter Member #{charterMemberNumber}"
- Separator: `text-brand-300` middot "·"
- Free-until: `text-xs text-brand-600` — "Free until {formattedDate}"
- `aria-label="Charter Member number {N}, free until {date}"`
- Non-interactive (display-only)
- Returns `null` if `charterMemberNumber` is null/undefined
- Omits "Free until" portion if `freePeriodEndsAt` is null

Props:
```typescript
interface CharterMemberBadgeProps {
  charterMemberNumber: number;
  freePeriodEndsAt: string | null;
}
```

**Intermediate test run:** `pnpm --filter pilot-web test -- --run 2>&1 | tail -5`

---

## Task 9 — Update `dashboard/page.tsx`

In `frontend/apps/web/src/app/(authed)/dashboard/page.tsx`:

1. Add `CharterMemberBadge` to the header, wrapped in `<RoleGate role="owner">`:
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

2. Pass `tierName` to the `OnboardingChecklistWidget`:
```tsx
<OnboardingChecklistWidget
  tenantId={tenantId}
  checklistState={checklistState}
  tierName={tierName}
/>
```

3. The `charterMemberNumber`, `freePeriodEndsAt`, and `tierName` values come from the authenticated user object. Verify the exact field path after `pnpm sync-api-types` — the C-B5 backend includes these in the auth response or they can be fetched via `GET /signup/{id}/state`. If the auth response doesn't include them, fetch from the signup state endpoint and cache in component state.

**Intermediate test run:** `pnpm --filter pilot-web test -- --run 2>&1 | tail -5`

---

## Task 10 — Update `useSignupWizard` Hook

In `frontend/apps/web/src/features/signup/hooks/useSignupWizard.ts`:

The `RESUME` action (lines ~123–144) must be extended to carry `freePeriodEndsAt`, `requiresPaymentMethod`, and `charterMemberNumber` from `collected_data` into `WizardFormData`.

**Intermediate test run:** `pnpm --filter pilot-web test -- --run 2>&1 | tail -5`

---

## Task 11 — MSW Handlers

Update MSW handlers to include the new fields in mock responses:

1. In the signup state handler: add `free_period_ends_at`, `requires_payment_method`, `charter_member_number` to `collected_data`
2. In the subscription tiers handler: add `free_period_days`, `requires_payment_method`, `signup_cap` to the Charter tier mock
3. In the onboarding checklist handler: add `messaging_setup: false` to the response

Register any new handlers in the barrel `index.ts`.

**Intermediate test run:** `pnpm --filter pilot-web test -- --run 2>&1 | tail -5`

---

## Task 12 — Write Tests

### Test Requirements

Per the UI spec and React Engineer rules:

**Test files to create:**

| Test File | Tests | Description |
|---|---|---|
| `CharterTierCard.test.tsx` | 3 | Renders free-period callout from `free_period_days`; selected state shows checkmark; CTA button calls `onSelect` |
| `Step5Confirmation.test.tsx` | 3 | Renders "You're set. No charge until {date}." with formatted date; Complete Signup button calls `onConfirm`; submitting state shows "Setting up…" |
| `MessagingSetupChecklistItem.test.tsx` | 2 | Incomplete state shows "Set up →" link; complete state shows strikethrough + no link |
| `CharterMemberBadge.test.tsx` | 3 | Renders "Charter Member #N" + "Free until {date}"; returns null when `charterMemberNumber` is null; omits "Free until" when `freePeriodEndsAt` is null |
| `plan/page.test.tsx` (update) | 1 | Charter tier renders `CharterTierCard` instead of `TierPickerCard` |
| `ready/page.test.tsx` (update) | 2 | Charter path (`requires_payment_method=false`) renders `Step5Confirmation`; non-Charter path renders Stripe Elements |
| `dashboard/page.test.tsx` (update) | 2 | Owner sees `CharterMemberBadge` when `charterMemberNumber` is set; non-owner does not see badge |

Use `@testing-library/react` + `@testing-library/user-event`. Mock `apiClient` with MSW. Use `renderWithProviders` if available, otherwise wrap in necessary providers.

**TanStack Query `retry: false`**: Set `retry: false` on all test query hooks to avoid flaky timeouts.

**Intermediate test run after each file:** `pnpm --filter pilot-web test -- --run 2>&1 | tail -5`

---

## Final Verification Gate

### Phase 1 — Targeted Tests

```bash
cd <repo>/frontend
pnpm --filter pilot-web test -- --run 2>&1 | tail -10
```

**Gate**: All targeted tests pass. If any fail → fix before Phase 2.

### Phase 2 — Full Suite

```bash
pnpm --filter pilot-web test -- --run 2>&1 | tail -10
```

**Gate**: Full suite passes (0 failures). No new warnings.

---

## Definition of Done

- [ ] `pnpm sync-api-types` run — new fields in `api-schema.d.ts`
- [ ] `CharterTierCard` created — follows UI spec §2.3 pixel specs
- [ ] `Step5Confirmation` created — follows UI spec §3.3 pixel specs
- [ ] `MessagingSetupChecklistItem` created — follows UI spec §4.3 pixel specs
- [ ] `CharterMemberBadge` created — follows UI spec §5.4 pixel specs (Option A)
- [ ] `plan/page.tsx` updated — conditional `CharterTierCard` for charter tier
- [ ] `ready/page.tsx` updated — branches on `requires_payment_method`
- [ ] `OnboardingChecklistWidget` updated — `tierName` prop + conditional `MessagingSetupChecklistItem`
- [ ] `dashboard/page.tsx` updated — `CharterMemberBadge` in header (owner-only) + `tierName` to checklist
- [ ] `signup/types.ts` + `onboarding/types.ts` updated with new fields
- [ ] `useSignupWizard` RESUME action carries new fields
- [ ] MSW handlers updated with new fields
- [ ] All tests pass (Phase 1 + Phase 2)
- [ ] WCAG 2.2 AA: focus-visible rings, ≥24×24px targets, non-color-only status, `prefers-reduced-motion` fallbacks

---

## Completion Summary

When done, append a completion summary to `dev-docs/analysis/pilot-launch-plan.md` Appendix B. Also:
1. Add a one-row entry to Appendix A
2. Mark C-B5 Part B as ✅ in the §2.0 Master Status Table (the full C-B5 batch is now complete)
