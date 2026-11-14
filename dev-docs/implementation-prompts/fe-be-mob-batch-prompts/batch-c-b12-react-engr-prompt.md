# Implementation Prompt: C-B12 (Part B — React Engineer) — Charter Upgrade Forfeiture Modal

**Mode**: Pilot React Engineer
**Batch**: C-B12 (Part B — React Engineer runs AFTER Part A Python Engineer ✅ + UI design spec Tom-approved)
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §2.0 row 14q, §2.1a C-5
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-c-b12-design.md` §H (Surface Mockup Reference), §I (Component Manifest)
**UI design spec**: `dev-docs/architecture-design/batch-designs/batch-c-b12-ui-design-spec.md` ← **Tom must approve this before you start**
**Estimated session**: 2–3 hours
**Platform**: Web only (`apps/web`)
**Backend companion**: C-B12 Part A ✅ COMPLETE 2026-08-07 — `POST /api/v1/tenants/{tenant_id}/subscription/upgrade-from-charter` + `/test` twin are live in `openapi_schema_map.md`

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-react-engineer/react-engineer-rules.md`** — in full
- **`dev-docs/architecture-design/batch-designs/batch-c-b12-design.md`** — every section (A–I)
- **`dev-docs/architecture-design/batch-designs/batch-c-b12-ui-design-spec.md`** — the Tom-approved UI design spec (if not approved → STOP and ask Tom)

**Before rendering any subscription, billing, or entitlement UI:**
Read `dev-docs/pilot-operations.md` — covers: subscription status display rules, annual vs. monthly price display formula, and entitlement 402 handling. The operational behavior is NOT inferrable from the schema alone.

Critical rules for this batch:

- **Rule 1.1**: Before writing ANY hook or API call, verify the endpoint exists in `backend/openapi_schema_map.md`. If it is NOT there → **STOP and ask Tom**.
- **Rule 1.3**: Run `pnpm sync-api-types` before starting — all TypeScript types for backend payloads come from `@pilot/shared-types`, never hand-written interfaces.
- **Rule 2**: All API calls use `apiClient` from `@pilot/shared-api`. `fetch()` is permanently banned for `/api/v1/...` calls.
- **Rule 7**: Check `packages/ui/src/index.ts` before creating any new component — `<NotificationBanner>`, `<RoleGate>`, `<LoadingState>`, `<ErrorState>` are all available.
- **Rule 10**: If ANY test fails during your work — even one that appears to be pre-existing — **you must fix it before declaring the batch done**.
- **Rule 11 (React Compiler)**: Do NOT hand-write `useMemo`/`useCallback`/`React.memo` for render-perf — the compiler handles it.
- **Rule 12 (TanStack Query v5)**: Object-form API only (`useQuery({ queryKey, queryFn })`). `gcTime` not `cacheTime`; `isPending` not `isLoading`. Colocated query keys. Invalidate after mutations.
- **Rule 13 (Zod v4 + RHF)**: Form validation via `zodResolver`. Use top-level `z.email()`/`z.uuid()`. Infer API types from `@pilot/shared-types`.
- **Rule 14 (server vs client)**: Authenticated data fetching stays client-side. Never fetch tenant data in a Server Component.
- **Rule 15 (WCAG 2.2 AA)**: Focus trap in modal, ≥24×24px targets, `focus-visible` rings, `prefers-reduced-motion` fallbacks, non-color-only errors.

---

## Design Decisions (Do Not Re-Litigate)

From Design Doc §G — these decisions are final:

| Decision | Outcome | Rationale |
|---|---|---|
| Dedicated endpoint vs. extend `change-tier` | New `POST /upgrade-from-charter` | Existing `change-tier` double-bills (adds without deleting); Charter flow needs item deletion + `charter_eligible` flip + trial-end |
| Billing interval | User choice (monthly $179 or annual $149 effective) | Tom decision 2026-08-07 — Charter members become "regular" customers at standard rates |
| Safe default | "Keep my Charter rate" (Cancel = primary button) | Spec §6.7 — forfeiture is irreversible; the safe action must be the easiest to click |
| Stale tier picker | Remove hardcoded "Pro"/"Growth" from BillingSettingsPage | Legacy code from pre-GTM-v3; replaced by Charter-specific upgrade flow |
| Dashboard badge | No upgrade CTA on dashboard badge | Badge stays informational; upgrade CTA lives on billing settings page |

---

## Pre-Work: Establish Regression Baseline

Before touching any file:

```bash
cd <repo>/frontend
pnpm --filter web test 2>&1 | tail -5
```

Record the exact count. These must still pass at the end of the batch.

> **If any tests are already failing before you start**: Do NOT treat them as "pre-existing" and proceed. Either confirm with Tom or fix before starting.

---

## Pre-Work: Sync API Types

```bash
cd <repo>/frontend
pnpm sync-api-types
```

This regenerates `packages/shared-types/src/api-schema.d.ts` from the live backend OpenAPI spec. The `upgrade-from-charter` endpoint types must be available before writing hooks.

Consume types via:
```typescript
import type { components } from "@pilot/shared-types";
type UpgradeFromCharterResponse = components["schemas"]["UpgradeFromCharterResponse"];
```

---

## Pre-Work: Verify Endpoints

```bash
grep -A 5 "upgrade-from-charter" backend/openapi_schema_map.md
```

Verified endpoints for this batch:
| Hook | Endpoint | Verified |
|---|---|---|
| `useUpgradeFromCharter` | `POST /api/v1/tenants/{tenant_id}/subscription/upgrade-from-charter` | ✅ (Part A complete) |

---

## Pre-Work: Read These Source Files

Read each of these with `read_file` before writing any code:

```
frontend/apps/web/src/features/settings/components/BillingSettingsPage.tsx  ← why: the page to modify — add Charter upgrade CTA, remove stale tier picker
frontend/apps/web/src/features/settings/hooks/useTenantSubscription.ts      ← why: the hook to extend with upgradeFromCharter mutation
frontend/apps/web/src/features/dashboard/components/CharterMemberBadge.tsx   ← why: understand Charter visual language
frontend/packages/ui/src/index.ts                                            ← why: confirm shared components (NotificationBanner, RoleGate, states)
frontend/apps/web/src/mocks/handlers/index.ts                                ← why: understand MSW handler registration pattern
frontend/apps/web/src/components/operator/cohort/ExtendFreePeriodModal.tsx   ← why: C-B11 preview-before-send modal pattern reference
frontend/apps/web/src/components/operator/cohort/CloseCohortButton.tsx       ← why: C-B11 destructive confirm pattern reference
```

Also run:
```bash
find frontend/apps/web/src/mocks/handlers -name "*.ts" | head -20
grep -rn "upgrade\|changeTier\|change-tier" frontend/apps/web/src/features/settings/ --include="*.ts" --include="*.tsx"
```

---

## Context: What This Batch Does

| # | Change | File |
|---|---|---|
| 1 | Add `useUpgradeFromCharter` mutation hook | `features/settings/hooks/useTenantSubscription.ts` (updated) |
| 2 | Create `CharterUpgradeModal` component | `features/settings/components/CharterUpgradeModal.tsx` (NEW) |
| 3 | Update `BillingSettingsPage` — add Charter upgrade CTA, remove stale tier picker | `features/settings/components/BillingSettingsPage.tsx` (updated) |
| 4 | Create MSW handler for `POST /upgrade-from-charter` | `mocks/handlers/charterUpgradeHandlers.ts` (NEW) |
| 5 | Register MSW handler in barrel | `mocks/handlers/index.ts` (updated) |
| 6 | Unit tests for modal + hook | `features/settings/components/__tests__/CharterUpgradeModal.test.tsx` (NEW) |
| 7 | Integration test for billing page | `__tests__/batch_c_b12/billing-upgrade.integration.test.tsx` (NEW) |

---

## STEP 1 — Add `useUpgradeFromCharter` Mutation Hook

In `frontend/apps/web/src/features/settings/hooks/useTenantSubscription.ts`, add the `upgradeFromCharter` mutation.

Read the file first. The existing `changeTier` mutation (around line 112) is the pattern reference. Add a new mutation after it:

```typescript
// Upgrade from Charter to Teams — permanent forfeiture of Charter rate
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
```

Add to the return interface:
```typescript
upgradeFromCharter: (billingInterval: "monthly" | "annual") => Promise<void>;
isUpgradingFromCharter: boolean;
```

**Intermediate verification**: `pnpm --filter web test -- apps/web/src/features/settings/hooks/ 2>&1 | tail -10`

---

## STEP 2 — Create `CharterUpgradeModal` Component

Create `frontend/apps/web/src/features/settings/components/CharterUpgradeModal.tsx`.

Read the UI design spec first — it has the exact pixel specs, tokens, and interaction states. The component is a `"use client"` component with:

**Props** (adjust to match the actual interface you find in the design spec):
```typescript
interface CharterUpgradeModalProps {
  isOpen: boolean;
  onClose: () => void;
  onUpgrade: (billingInterval: "monthly" | "annual") => Promise<void>;
  isUpgrading: boolean;
  upgradeError: string | null;
}
```

**Key implementation details** (from design doc §H + UI spec):
- `role="dialog"` + `aria-modal="true"` + `aria-labelledby` pointing to the header
- Focus trap: first focusable element on open, return focus to trigger on close, Escape key = close (safe default)
- Billing interval selector: `role="radiogroup"` with two `role="radio"` options
- Safe default button ("Keep my Charter rate") on the LEFT, `bg-brand-600 text-white`
- Destructive button ("I understand — upgrade to Teams") on the RIGHT, `bg-fault-600 text-white hover:bg-fault-700`
- Loading state: destructive button shows "Upgrading…" + `disabled` + spinner when `isUpgrading`
- Error state: `NotificationBanner` with `severity="error"` inside modal when `upgradeError` is set
- `prefers-reduced-motion`: no transition on modal open

**Pattern reference**: Read `ExtendFreePeriodModal.tsx` (C-B11) for the established modal pattern — focus trap, Zod form, preview-before-send, error handling. The CharterUpgradeModal is simpler (no form, just a radio group + two buttons).

**Intermediate verification**: `pnpm --filter web test -- apps/web/src/features/settings/components/__tests__/CharterUpgradeModal.test.tsx 2>&1 | tail -10`

---

## STEP 3 — Update `BillingSettingsPage`

In `frontend/apps/web/src/features/settings/components/BillingSettingsPage.tsx`:

1. **Remove the stale tier picker** (lines ~130-168 — the hardcoded "Pro" and "Growth" modal with `showTierPicker` state)
2. **Add Charter upgrade CTA**: In the "Current Plan" card (around line 117), add a condition for Charter members:
   ```tsx
   {(isTrial || currentTier.tierName === "starter" || currentTier.tierName === "charter") && (
     <button
       onClick={() => {
         if (currentTier.tierName === "charter") {
           setShowCharterUpgradeModal(true);
         } else {
           // Legacy: trial/starter upgrade — keep existing behavior or remove
           // For now, just route to /signup/plan or show a "coming soon" message
         }
       }}
       className="rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 ..."
     >
       {currentTier.tierName === "charter" ? "Upgrade to Teams" : "Upgrade plan"}
     </button>
   )}
   ```
3. **Add the CharterUpgradeModal** at the bottom of the component:
   ```tsx
   {showCharterUpgradeModal && (
     <CharterUpgradeModal
       isOpen={showCharterUpgradeModal}
       onClose={() => setShowCharterUpgradeModal(false)}
       onUpgrade={async (interval) => {
         await upgradeFromCharter(interval);
         setShowCharterUpgradeModal(false);
       }}
       isUpgrading={isUpgradingFromCharter}
       upgradeError={upgradeError}
     />
   )}
   ```

4. **Add Charter-specific display**: In the "Current Plan" card, when `currentTier.tierName === "charter"`, show "Your rate: $49/mo — locked" (per spec §6.6) instead of the generic price display.

**Intermediate verification**: `pnpm --filter web test -- apps/web/src/features/settings/ 2>&1 | tail -10`

---

## STEP 4 — Create MSW Handler

Create `frontend/apps/web/src/mocks/handlers/charterUpgradeHandlers.ts`:

```typescript
import { http, HttpResponse } from "msw";

export const charterUpgradeHandlers = [
  http.post("/api/v1/tenants/:tenantId/subscription/upgrade-from-charter", async ({ request }) => {
    const body = (await request.json()) as { billing_interval: string };
    return HttpResponse.json({
      psp_subscription_id: "sub_test_mock",
      new_tier_name: "teams",
      billing_interval: body.billing_interval,
      charter_eligible_forfeited: true,
    });
  }),
  http.post("/api/v1/tenants/:tenantId/subscription/upgrade-from-charter/test", async ({ request }) => {
    const body = (await request.json()) as { billing_interval: string };
    return HttpResponse.json({
      psp_subscription_id: "test_sub_mock_id",
      new_tier_name: "teams",
      billing_interval: body.billing_interval,
      charter_eligible_forfeited: true,
    });
  }),
];
```

**Register in barrel** `mocks/handlers/index.ts`:
```typescript
import { charterUpgradeHandlers } from "./charterUpgradeHandlers";
export const handlers = [
  ...existingHandlers,
  ...charterUpgradeHandlers,
];
```

---

## STEP 5 — Write Tests

### Unit Tests: `CharterUpgradeModal.test.tsx`

Create `frontend/apps/web/src/features/settings/components/__tests__/CharterUpgradeModal.test.tsx`:

```typescript
import { describe, it, expect, vi } from "vitest";
// ... imports
```

**Minimum tests**:
1. Renders warning header "You'll lose your Charter rate."
2. Shows both pricing options ($179/mo monthly, $149/mo annual)
3. Billing interval selector defaults to "Monthly"
4. Clicking "Keep my Charter rate" calls `onClose` (safe default)
5. Clicking "I understand — upgrade to Teams" calls `onUpgrade` with selected interval
6. Loading state: "Upgrading…" + disabled when `isUpgrading=true`
7. Error state: shows error message when `upgradeError` is set
8. Escape key closes modal (safe default)
9. Focus trap: first focusable element receives focus on open

### Integration Test: `billing-upgrade.integration.test.tsx`

Create `frontend/apps/web/src/__tests__/batch_c_b12/billing-upgrade.integration.test.tsx`:

**Minimum tests**:
1. Charter member sees "Upgrade to Teams" button on billing page
2. Non-Charter member does NOT see "Upgrade to Teams" button
3. Clicking "Upgrade to Teams" opens the forfeiture modal
4. Clicking "I understand — upgrade to Teams" fires `POST /upgrade-from-charter` with correct payload
5. After successful upgrade, modal closes + success notification appears
6. Stale "Pro"/"Growth" tier picker is NOT present

**TanStack Query setup** (required for all tests):
```typescript
function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}
```

**MSW setup**:
```typescript
import { setupServer } from "msw/node";
const server = setupServer(...charterUpgradeHandlers);
beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
```

**RBAC testing**: Use `AuthContext.Provider` pattern from the inclusions file. The billing page is gated by `billing.view` permission.

---

## Final Verification

### Phase 1 — Targeted tests (run after each step)

```bash
cd <repo>/frontend
pnpm --filter web test -- apps/web/src/features/settings/ 2>&1 | tail -10
pnpm --filter web test -- apps/web/src/__tests__/batch_c_b12/ 2>&1 | tail -10
```

### Phase 2 — Full verification (run once at the very end)

```bash
cd <repo>/frontend && echo "=== UI - Type Check ===" && pnpm --filter @pilot/ui check-types && echo "=== Web - Type Check ===" && pnpm --filter web check-types && echo "=== Mobile - Type Check ===" && pnpm --filter mobile build && echo "=== UI - Lint ===" && pnpm --filter @pilot/ui lint && echo "=== Web - Lint ===" && pnpm --filter web lint && echo "=== Mobile - Lint ===" && pnpm --filter mobile lint && echo "=== TYPE+LINT PASS ===" && echo "=== UI - Tests ===" && pnpm --filter @pilot/ui test 2>&1 | tail -6 && echo "=== Web - Tests ===" && pnpm --filter web test 2>&1 | tail -6 && echo "=== Mobile - Tests ===" && pnpm --filter mobile test 2>&1 | tail -8 && echo "=== MVP FINAL VERIFICATION COMPLETE ==="
```

---

## Definition of Done — C-B12 Part B

- [ ] Pre-modification regression baseline captured (zero pre-existing failures, or confirmed with Tom)
- [ ] `pnpm sync-api-types` run — no new type errors
- [ ] UI design spec read and followed (Tom-approved)
- [ ] All mandatory source files read before modifying
- [ ] `upgrade-from-charter` endpoint verified in `openapi_schema_map.md`
- [ ] **STEP 1**: `useUpgradeFromCharter` mutation added to `useTenantSubscription.ts`
- [ ] **STEP 2**: `CharterUpgradeModal` component created with focus trap, billing interval selector, safe default
- [ ] **STEP 3**: `BillingSettingsPage` updated — Charter upgrade CTA added, stale tier picker removed
- [ ] **STEP 4**: MSW handler created + registered in `index.ts`
- [ ] **STEP 5**: Unit tests + integration tests written
- [ ] No hand-written `useMemo`/`useCallback`/`React.memo` for render-perf (React Compiler)
- [ ] All new hooks use TanStack Query v5 object-form + colocated query keys
- [ ] No `fetch()` calls — all API via `apiClient` from `@pilot/shared-api`
- [ ] axe-core zero violations + WCAG 2.2 AA (focus trap, ≥24px targets, `focus-visible`, `prefers-reduced-motion`)
- [ ] All new MSW handler files registered in `mocks/handlers/index.ts`
- [ ] Unit tests pass (targeted run)
- [ ] Integration tests pass in `__tests__/batch_c_b12/`
- [ ] Zero TypeScript errors (`check-types` passes)
- [ ] Zero ESLint warnings
- [ ] No regressions in pre-existing test suite
- [ ] **Phase 2 FULL verification command passes** (`=== MVP FINAL VERIFICATION COMPLETE ===`)
- [ ] Final test count (before → after) documented
- [ ] Completion Summary added to launch plan Appendix B

---

## Completion Summary

After all Definition of Done items are complete:

1. Add a **Completion Summary** subsection to `dev-docs/analysis/pilot-launch-plan.md` Appendix B using the format below.

```markdown
### C-B12 (Part B — React Engineer) — Charter Upgrade Forfeiture Modal: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot React Engineer
**Source design doc**: `batch-c-b12-design.md`
**UI design spec**: `batch-c-b12-ui-design-spec.md`
**Baseline**: X passed, Y failed (web)
**Final**: X+N passed, Y failed (+N new tests)

#### What Was Accomplished

- [Brief description of key change 1]
- [Brief description of key change 2]

#### Files Changed / Created

| File | Action |
|---|---|
| `frontend/apps/web/src/features/settings/components/CharterUpgradeModal.tsx` | Created — [what it does] |
| `frontend/apps/web/src/features/settings/components/BillingSettingsPage.tsx` | Updated — [what changed] |
| ... | ... |

#### Tests Added

| Test File | Type | Tests | All Pass |
|---|---|---|---|
| `features/settings/components/__tests__/CharterUpgradeModal.test.tsx` | Unit | N | ✅ |
| `__tests__/batch_c_b12/billing-upgrade.integration.test.tsx` | Integration | N | ✅ |
```
