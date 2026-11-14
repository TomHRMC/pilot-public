# Implementation Prompt: C-B11 (Part B — React Engineer) — Operator Cohort Dashboard Page

**Mode**: Pilot React Engineer
**Batch**: C-B11 (Part B — runs AFTER Part A Python Engineer ✅ + UI design spec Tom-approved)
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §2.0 row 14p, §2.1a C-5
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-c-b11-design.md`
**UI design spec**: `dev-docs/architecture-design/batch-designs/batch-c-b11-ui-design-spec.md` ← **MUST be Tom-approved before starting**
**Estimated session**: 3–4 hours
**Platform**: Web only (`apps/web`)
**Backend companion**: C-B11 Part A ✅ COMPLETE 2026-08-06 (4 endpoints: GET /operator/cohort, POST extend, POST close, GET /auth/me)

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-react-engineer/react-engineer-rules.md`** — in full
- **`dev-docs/architecture-design/batch-designs/batch-c-b11-design.md`** — every section (A–M)
- **`dev-docs/architecture-design/batch-designs/batch-c-b11-ui-design-spec.md`** — the Tom-approved UI design spec

Critical rules for this batch:

- **Rule 1.1**: Before writing ANY hook or API call, verify the endpoint exists in `backend/openapi_schema_map.md`. If it is NOT there → **STOP and ask Tom**.
- **Rule 1.2**: Do NOT invent URL patterns or parameter names. Every shape comes from `openapi.json` or the design doc.
- **Rule 1.3**: Run `pnpm sync-api-types` before starting — all TypeScript types for backend payloads come from `@pilot/shared-types`.
- **Rule 2**: All API calls use `apiClient` from `@pilot/shared-api`. `fetch()` is permanently banned for `/api/v1/...` calls.
- **Rule 7**: Check `packages/ui/src/index.ts` before creating any new component — `<LoadingState>`, `<ErrorState>`, `<EmptyState>`, `<RoleGate>` are all available.
- **Rule 9**: Route files in `apps/web/src/app/` MUST be thin server components — no `"use client"`, no data fetching. All logic goes in feature components.
- **Rule 10**: If ANY test fails during your work — even one that appears to be pre-existing — **you must fix it before declaring the batch done**.
- **Rule 11 (React Compiler)**: Do NOT hand-write `useMemo`/`useCallback`/`React.memo` for render-perf — the compiler handles it.
- **Rule 12 (TanStack Query v5)**: Object-form API only (`useQuery({ queryKey, queryFn })`). `gcTime` not `cacheTime`; `isPending` not `isLoading`. Colocate query keys. Set `retry: false` in tests.
- **Rule 13 (Zod v4 + RHF)**: Form validation is Zod v4 via `@hookform/resolvers/zod`. Use top-level format helpers.
- **Rule 14 (server vs client)**: Authenticated data fetching stays **client-side**. Never fetch tenant data in a Server Component.
- **Rule 15 (WCAG 2.2 AA)**: Every new surface must satisfy Focus Not Obscured, Target Size (≥24×24px), Accessible Authentication (allow paste), modal focus management, and non-color-only errors.

---

## Design Decisions (Do Not Re-Litigate)

From Design Doc §G + Tom decisions — these are final:

| Decision | Outcome | Rationale |
|---|---|---|
| **Path A — standalone page** | No tenant shell, no nav sidebar, no impersonation | Tom decision 2026-08-06 — ship C-B11 faster; platform shell deferred to C-B15 |
| **Platform user login routing** | `GET /api/v1/auth/me` returns `user_type` + `redirect_to` | Frontend calls this after Cognito auth; platform users redirect to `/operator/cohort` |
| **`has_payment_method` always false** | Aggregation query doesn't check Stripe for PMs | N Stripe API calls per page load is too expensive; deferred to future optimization |
| **`last_contact` always null** | No operator contact log table exists yet | Deferred to a future batch; column is in the response for forward compatibility |
| **`days_since_last_job = null` → red** | No jobs ever created = highest concern | Null is worse than "created one 8 days ago" |

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

This regenerates `packages/shared-types/src/api-schema.d.ts` from the live backend. All backend payload types must come from `@pilot/shared-types` — never hand-written.

Consume types via the `components` root:

```typescript
import type { components } from "@pilot/shared-types";
type CohortOverviewResponse = components["schemas"]["CohortOverviewResponse"];
type CohortMemberResponse = components["schemas"]["CohortMemberResponse"];
```

---

## Pre-Work: Verify Endpoints

For each new hook, verify the endpoint exists before writing any code:

```bash
grep -A 5 "operator/cohort" backend/openapi_schema_map.md
grep -A 5 "auth/me" backend/openapi_schema_map.md
```

Verified endpoints for this batch:
| Hook | Endpoint | Verified |
|---|---|---|
| `useCohortOverview` | `GET /api/v1/operator/cohort` | ✅ Confirmed (C-B11 Part A) |
| `useExtendFreePeriod` | `POST /api/v1/operator/cohort/{tenant_id}/extend` | ✅ Confirmed (C-B11 Part A) |
| `useCloseCohort` | `POST /api/v1/operator/cohort/close` | ✅ Confirmed (C-B11 Part A) |
| `useAuthMe` | `GET /api/v1/auth/me` | ✅ Confirmed (C-B11 Part A) |

**If an endpoint is NOT in `openapi_schema_map.md` → STOP. Do not invent a URL. Ask Tom.**

---

## Pre-Work: Read These Source Files

Read each of these with `read_file` before writing any code:

```
frontend/apps/web/src/app/(authed)/dashboard/page.tsx    ← why: existing route pattern (thin server component)
frontend/apps/web/src/features/messaging/hooks/useProvisioningStatus.ts ← why: TQ v5 hook pattern reference (polling)
frontend/apps/web/src/features/messaging/hooks/useInitiateProvisioning.ts ← why: TQ v5 mutation pattern reference
frontend/packages/ui/src/index.ts                        ← why: confirm shared components (LoadingState, ErrorState, EmptyState)
frontend/apps/web/src/mocks/handlers/index.ts             ← why: understand MSW handler registration
frontend/apps/web/src/mocks/handlers/messagingProvisioningHandlers.ts ← why: MSW handler pattern reference
frontend/apps/web/src/components/settings/messaging/MessagingSetupClient.tsx ← why: orchestrator component pattern reference
```

Also run these to locate related files:

```bash
find frontend/apps/web/src/features -name "use*.ts" | head -20
find frontend/apps/web/src/mocks/handlers -name "*.ts" | head -20
grep -n "EmptyState\|LoadingState\|ErrorState" frontend/packages/ui/src/index.ts
```

---

## Platform: Web (`apps/web`) — Mandatory Constraints

- **Route files are thin server components**: `app/operator/cohort/page.tsx` must NOT have `"use client"`, must NOT fetch data. One line: `return <CohortDashboardClient />;`
- **Feature components own logic**: All `"use client"`, hooks, state, and data fetching belong in `features/operator/` or `components/operator/`
- **RBAC gating**: This page is platform-level (not tenant-scoped). It does NOT use `<RoleGate>` (which is tenant-role-based). Instead, the page is protected by the routing layer — only platform users reach it via `GET /api/v1/auth/me` redirect.
- **State lifecycle patterns**: Use `<LoadingState>`, `<ErrorState>`, `<EmptyState>` from `@pilot/ui/states`
- **React Compiler (React 19.2)**: Do NOT hand-write `useMemo`/`useCallback`/`React.memo` for render-perf
- **TanStack Query v5**: Object-form only; `gcTime` not `cacheTime`; `isPending` not `isLoading`. Colocate query keys. `retry: false` in tests.
- **Zod v4 + React Hook Form 7**: Validate the extension form with `zodResolver`
- **Test framework: Vitest + `@testing-library/react`** — use `vi.mock()`, `toBeInTheDocument()` assertions

---

## Background / Context

C-B11 Part A built the backend: `PlatformUser` auth, `get_platform_user()`, `GET /api/v1/auth/me`, and 3 cohort endpoints. Part B builds the frontend: a standalone `/operator/cohort` page showing all Charter members in a table with tripwire alerts, plus the extension modal and cohort close button.

**Path A scope**: Standalone page — no tenant shell, no nav sidebar. Simple header + table + modals. The platform shell + tenant impersonation is deferred to C-B15.

**Login routing**: After Cognito auth, the frontend calls `GET /api/v1/auth/me`. If `user_type === "platform"`, redirect to `/operator/cohort`. If `user_type === "tenant"`, redirect to `/dashboard` (existing behavior). This routing change is part of this batch.

---

## Task 1 — Login Routing: `useAuthMe` Hook + Redirect Logic

Create `frontend/apps/web/src/features/auth/hooks/useAuthMe.ts`:

```typescript
// TQ v5 hook — GET /api/v1/auth/me
// Returns: { user_type, user_id, email, first_name, last_name, platform_role_code?, tenant_id?, role_code?, redirect_to }
// Used by the login flow to determine redirect target
```

Update the login redirect logic (wherever the post-Cognito-auth redirect happens — find it by grepping for the existing `/dashboard` redirect):

```typescript
// After Cognito auth, call useAuthMe, then redirect based on user_type:
// - platform → router.push("/operator/cohort")
// - tenant → router.push("/dashboard") (existing behavior)
```

**Read the existing login flow first** — grep for `router.push("/dashboard")` or `router.replace("/dashboard")` to find where the post-auth redirect happens. The `useAuthMe` call should be inserted there.

**Intermediate test run**: `pnpm --filter web test 2>&1 | tail -6`

---

## Task 2 — `useCohortOverview` Hook

Create `frontend/apps/web/src/features/operator/hooks/useCohortOverview.ts`:

```typescript
// TQ v5 hook — GET /api/v1/operator/cohort
// Query key: ["operator", "cohort"]
// Returns: CohortOverviewResponse (cohort_tier_name, cohort_is_active, signup_cap, members[])
// staleTime: 30s (operator checks periodically, not real-time)
```

---

## Task 3 — `useExtendFreePeriod` Hook

Create `frontend/apps/web/src/features/operator/hooks/useExtendFreePeriod.ts`:

```typescript
// TQ v5 mutation — POST /api/v1/operator/cohort/{tenant_id}/extend
// Request: { new_free_period_ends_at: string, override_reason: string }
// On success: invalidate ["operator", "cohort"] (refresh the table)
// retry: false (operator sees error immediately)
```

---

## Task 4 — `useCloseCohort` Hook

Create `frontend/apps/web/src/features/operator/hooks/useCloseCohort.ts`:

```typescript
// TQ v5 mutation — POST /api/v1/operator/cohort/close
// No request body
// On success: invalidate ["operator", "cohort"] (refresh — cohort_is_active becomes false)
// retry: false
```

---

## Task 5 — `CohortDashboardPage` (Thin Route)

Create `frontend/apps/web/src/app/operator/cohort/page.tsx`:

```typescript
// Thin server component — no "use client", no data fetching
// One line: return <CohortDashboardClient />;
```

**Note**: This route is NOT under `(authed)/` — it's a platform-level route at `/operator/cohort`. Create the `operator/cohort/` directory directly under `app/`.

---

## Task 6 — `CohortDashboardClient` (Orchestrator)

Create `frontend/apps/web/src/components/operator/cohort/CohortDashboardClient.tsx`:

```typescript
"use client";

// Orchestrator component:
// 1. useCohortOverview() — fetch data
// 2. Loading state → <LoadingState />
// 3. Error state → <ErrorState />
// 4. Empty state (no members) → <EmptyState message="No Charter members yet..." />
// 5. Success → render header (title + CloseCohortButton) + table (CohortMemberRow per member)
// 6. Extension modal state (which tenant is being extended, open/close)
```

Follow the UI design spec for layout, spacing, and token usage.

---

## Task 7 — `CohortMemberRow` Component

Create `frontend/apps/web/src/components/operator/cohort/CohortMemberRow.tsx`:

```typescript
// Single table row for one Charter member
// Props: member: CohortMemberResponse, onExtend: (tenant_id: string) => void
// Alert-level styling (color-independent — icon + text, not color alone):
//   - red: AlertIcon + "Tripwire" text (days_since_last_job > 7 or null)
//   - amber: ClockIcon + "Expiring" text (free_period_ends_at within 14 days)
//   - none: no alert indicator
// "Extend" button per row → opens extension modal
```

Follow the UI design spec for column layout, alert styling, and token usage.

---

## Task 8 — `ExtendFreePeriodModal` Component

Create `frontend/apps/web/src/components/operator/cohort/ExtendFreePeriodModal.tsx`:

```typescript
"use client";

// Preview-before-send modal (§16.7):
// 1. Shows current free_period_ends_at
// 2. Date picker for new_free_period_ends_at (must be after current)
// 3. Required reason text field (Zod v4 validation: min 10 chars)
// 4. Preview: "Extend from {current} to {new} — No notification will be sent to the customer"
// 5. Confirm button (disabled until valid) → useExtendFreePeriod mutation
// 6. Cancel button (default, safe action)
// 7. Error display (409 = not trialing, 422 = invalid date)
// 8. On success: close modal, invalidate cohort query (handled by hook)
```

Use React Hook Form 7 + Zod v4 for form validation. Modal focus management (focus trap, Escape to close, restore focus on close).

---

## Task 9 — `CloseCohortButton` Component

Create `frontend/apps/web/src/components/operator/cohort/CloseCohortButton.tsx`:

```typescript
"use client";

// Cohort close action with confirmation modal:
// 1. Button in the header area (only visible when cohort_is_active === true)
// 2. Click → confirmation modal: "This will archive the Charter price and close the cohort to new signups. Existing members keep their locked rate. This cannot be undone."
// 3. Two buttons: "Cancel" (default, safe action) + "Close Cohort" (destructive styling)
// 4. Confirm → useCloseCohort mutation
// 5. On success: modal closes, table refreshes (cohort_is_active becomes false, button hides)
// 6. Error display (409 = already closed)
```

---

## Task 10 — MSW Handlers

Create `frontend/apps/web/src/mocks/handlers/cohortDashboardHandlers.ts`:

```typescript
// MSW handlers for 4 endpoints:
// GET /api/v1/operator/cohort → CohortOverviewResponse with 3 varied members (red, amber, none alerts)
// POST /api/v1/operator/cohort/:tenantId/extend → ExtendFreePeriodResponse
// POST /api/v1/operator/cohort/close → CloseCohortResponse
// GET /api/v1/auth/me → AuthMeResponse (platform user variant)
```

Register in `frontend/apps/web/src/mocks/handlers/index.ts`:

```typescript
import { cohortDashboardHandlers } from "./cohortDashboardHandlers";
export const handlers = [
  ...existingHandlers,
  ...cohortDashboardHandlers, // ← ADD THIS
];
```

---

## Task 11 — Tests

### Test Requirements

Per [`backend/tests/README-adding-tests.md`] and the React Engineer rules:

**TanStack Query — Required Setup for All Tests:**

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

**Never share a QueryClient instance across tests** — always create a fresh one per test.

**MSW in Tests:**

```typescript
import { setupServer } from "msw/node";
const server = setupServer(...cohortDashboardHandlers);
beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
```

**Never mock `apiClient` directly** — MSW intercepts at the HTTP level.

### Required Tests

| Test File | Type | Tests | Description |
|---|---|---|---|
| `features/operator/hooks/__tests__/useCohortOverview.test.tsx` | Unit (hook) | 3 | Returns data shape, error state, query key |
| `features/operator/hooks/__tests__/useExtendFreePeriod.test.tsx` | Unit (hook) | 3 | Mutation fires correct POST, invalidates cohort query, error handling |
| `features/operator/hooks/__tests__/useCloseCohort.test.tsx` | Unit (hook) | 2 | Mutation fires correct POST, invalidates cohort query |
| `features/operator/hooks/__tests__/useAuthMe.test.tsx` | Unit (hook) | 2 | Returns platform user, returns tenant user |
| `components/operator/cohort/__tests__/CohortMemberRow.test.tsx` | Unit | 4 | Renders all columns, red alert, amber alert, none alert |
| `components/operator/cohort/__tests__/ExtendFreePeriodModal.test.tsx` | Unit | 3 | Renders form, validation blocks empty reason, submit fires mutation |
| `components/operator/cohort/__tests__/CloseCohortButton.test.tsx` | Unit | 2 | Renders button when active, confirmation modal opens |
| `__tests__/batch_c_b11/cohort-dashboard.integration.test.tsx` | Integration | 5 | Page renders, table shows members, extend modal flow, close cohort flow, empty state |

**Integration tests** go in `apps/web/src/__tests__/batch_c_b11/`.

---

## Final Verification

> ❌ **BANNED COMMAND**: `npx vitest run` — **NEVER use this**. The ONLY correct test runner for `apps/web` is `pnpm --filter web test`.

### Phase 1 — Targeted tests (run after each task group during development)

```bash
cd <repo>/frontend
pnpm --filter web test 2>&1 | tail -6
```

Fix any failure before moving to the next task.

### Phase 2 — Full verification (run once at the very end, before DoD sign-off)

```bash
cd <repo>/frontend && echo "=== UI - Type Check ===" && pnpm --filter @pilot/ui check-types && echo "=== Web - Type Check ===" && pnpm --filter web check-types && echo "=== Mobile - Type Check ===" && pnpm --filter mobile build && echo "=== UI - Lint ===" && pnpm --filter @pilot/ui lint && echo "=== Web - Lint ===" && pnpm --filter web lint && echo "=== Mobile - Lint ===" && pnpm --filter mobile lint && echo "=== TYPE+LINT PASS ===" && echo "=== UI - Tests ===" && pnpm --filter @pilot/ui test 2>&1 | tail -6 && echo "=== Web - Tests ===" && pnpm --filter web test 2>&1 | tail -6 && echo "=== Mobile - Tests ===" && pnpm --filter mobile test 2>&1 | tail -8 && echo "=== MVP FINAL VERIFICATION COMPLETE ==="
```

> **Any failure in either phase must be fixed before the batch is declared done.**

---

## Definition of Done — C-B11 Part B

- [ ] Pre-modification regression baseline captured (zero pre-existing failures, or confirmed with Tom)
- [ ] `pnpm sync-api-types` run — no new type errors
- [ ] UI design spec fully read before writing any code
- [ ] All mandatory source files read before modifying
- [ ] All endpoint URLs verified in `openapi_schema_map.md`
- [ ] `useAuthMe` hook created + login redirect logic updated (platform → `/operator/cohort`)
- [ ] `useCohortOverview` hook created (GET /operator/cohort)
- [ ] `useExtendFreePeriod` hook created (POST extend)
- [ ] `useCloseCohort` hook created (POST close)
- [ ] `CohortDashboardPage` thin route created at `/operator/cohort`
- [ ] `CohortDashboardClient` orchestrator created (loading/error/empty/success states)
- [ ] `CohortMemberRow` created with color-independent alert styling (red/amber/none)
- [ ] `ExtendFreePeriodModal` created (preview-before-send, Zod v4 + RHF, focus management)
- [ ] `CloseCohortButton` created with confirmation modal (destructive action, default = safe)
- [ ] MSW handlers created for 4 endpoints + registered in `index.ts`
- [ ] No hand-written `useMemo`/`useCallback`/`React.memo` for render-perf; components are pure
- [ ] All new hooks use TanStack Query v5 object-form + colocated query keys; `retry: false` in tests
- [ ] Form validation uses Zod v4 via `zodResolver`; API types inferred from `@pilot/shared-types`
- [ ] No tenant-data fetching in Server Components — data fetching is client-side
- [ ] axe-core zero violations + WCAG 2.2 AA spot-checks (target size ≥24px, focus not obscured, paste allowed, modal focus trap, non-color-only errors)
- [ ] All new MSW handler files registered in `mocks/handlers/index.ts`
- [ ] Unit tests pass (targeted run) — one file per new component/hook
- [ ] Integration tests pass in `__tests__/batch_c_b11/`
- [ ] Zero TypeScript errors (`check-types` passes)
- [ ] Zero ESLint `no-hardcoded-design-values` warnings
- [ ] No regressions in pre-existing test suite
- [ ] **Phase 2 FULL verification command passes** (`=== MVP FINAL VERIFICATION COMPLETE ===`)
- [ ] Final test count (before → after) documented
- [ ] Completion Summary added to launch plan Appendix B

---

## Completion Summary

After all Definition of Done items are complete:

1. Add a **Completion Summary** subsection to `dev-docs/analysis/pilot-launch-plan.md` Appendix B.

```markdown
### C-B11 (Part B — React Engineer) — Operator Cohort Dashboard Page: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot React Engineer
**Baseline**: X passed, Y failed (web)
**Final**: X+N passed, Y failed (+N new tests)

#### What Was Accomplished

- [Brief description of key change 1]
- [Brief description of key change 2]

#### Files Changed / Created

| File | Action |
|---|---|
| `frontend/apps/web/src/app/operator/cohort/page.tsx` | Created — thin route |
| `frontend/apps/web/src/components/operator/cohort/CohortDashboardClient.tsx` | Created — orchestrator |
| ... | ... |

#### Tests Added

| Test File | Type | Tests | All Pass |
|---|---|---|---|
| `__tests__/batch_c_b11/cohort-dashboard.integration.test.tsx` | Integration | N | ✅ |
| `features/operator/hooks/__tests__/useCohortOverview.test.tsx` | Unit (hook) | N | ✅ |
| ... | ... | ... | ✅ |
```

---

## After This Task — Next Step

C-B11 is now fully complete (Part A + Part B). The remaining Charter batches are:
- **C-B12** — Charter → Teams upgrade flow (Python + React)
- **C-B13** — Marketing site rebuild (Marketing React)
- **C-B14** — Full test suite + live-mode rehearsal (launch gate)
- **C-B15** — Platform Shell + Tenant Impersonation (the full operator experience)

Return to Pilot Architect mode for the next batch design.
