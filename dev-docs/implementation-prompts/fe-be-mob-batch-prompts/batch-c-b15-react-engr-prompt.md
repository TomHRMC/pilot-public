# Implementation Prompt: C-B15 (Part B) — Platform Shell + Tenant Impersonation Frontend

**Mode**: Pilot React Engineer
**Batch**: C-B15 (Part B — Frontend)
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` row 14v
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-c-b15-design.md` — read §C Part B, §E, §F.3, §G, §I
**UI design spec**: `dev-docs/architecture-design/batch-designs/batch-c-b15-ui-design-spec.md` — **Tom-approved**; binding for every class name, icon, state, and a11y requirement. Sections §1–§15.
**Estimated session**: 4–5 hours
**Platform**: Web (`apps/web`) + shared packages (`packages/shared-api`, `packages/ui` — small modifications only). No mobile, no marketing.
**Backend companion**: C-B15 Part A (Python Engineer) — ✅ **COMPLETE**. All 3 endpoints are live in `backend/openapi_schema_map.md` and `pnpm sync-api-types` will deliver the types.

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-react-engineer/react-engineer-rules.md`** — in full
- **`dev-docs/architecture-design/batch-designs/batch-c-b15-design.md`** — every section (A–I)
- **`dev-docs/architecture-design/batch-designs/batch-c-b15-ui-design-spec.md`** — every section; this is the pixel/token/a11y contract

Critical rules for this batch:

- **Rule 1.1**: Before writing ANY hook or API call, verify the endpoint exists in `backend/openapi_schema_map.md`. If it is NOT there → **STOP and ask Tom**. (Pre-verified below — you confirm.)
- **Rule 1.3**: Run `pnpm sync-api-types` before starting — all TypeScript types for backend payloads come from `@pilot/shared-types`, never hand-written interfaces.
- **Rule 2**: All API calls use `apiClient` from `@pilot/shared-api`. `fetch()` is permanently banned for `/api/v1/...` calls. **Single sanctioned exception**: the pre-existing raw `fetch()` in `AuthProvider.tsx` `fetchUserFromBackend()` (predates the mandate) — you are adding a header to it, not replacing it. Do not refactor it to apiClient in this batch.
- **Rule 7**: Check `packages/ui/src/index.ts` before creating any new component. `<LoadingState>`, `<ErrorState>`, `<EmptyState>`, `<NotificationBanner>`, `RequireAuth` all exist and MUST be used (spec §13.1). Note: **no generic `Modal` primitive exists** (spec §5.2 existence check) — build `ImpersonationConfirmModal` on the standard modal pattern like C-B11's `CloseCohortButton` did.
- **Rule 8**: No new npm dependencies without checking `package.json` first.
- **Rule 10**: If ANY test fails during your work — even one that appears pre-existing — you must fix it before declaring the batch done. No "not my fault" exception.
- **Rule 11 (React Compiler — rules §32)**: Do NOT hand-write `useMemo`/`useCallback`/`React.memo` for render-perf. Keep components pure.
- **Rule 12 (TanStack Query v5 — rules §33)**: Object-form only; `gcTime` not `cacheTime`; `isPending` not `isLoading`; colocated query keys.
- **Rule 15 (WCAG 2.2 AA — rules §36)**: Every surface in this batch has explicit a11y requirements in the spec §10 — modal focus trap, ≥24×24px targets, color-independent status, `role="status"`/`aria-live` on the banner.

## Design Decisions (Do Not Re-Litigate)

From design doc §G + UI spec — these decisions are final:

| Decision | Outcome | Rationale |
|---|---|---|
| Impersonation start/exit navigation | **Deliberate full page reload** (`window.location.assign('/dashboard')` on start, `'/operator/cohort'` on exit) | Rebuilds `AuthProvider` + all TanStack caches under the new tenant context; prevents cross-tenant cache leakage (design §G Q2/Q3, spec §14.5). NOT optimistic, NOT an in-place state swap. |
| Session persistence | `sessionStorage` key `pilot.impersonation` (tab-scoped) | Tab close ends the session — a safety feature (spec §5.7). |
| Impersonated role context | Tenant `owner` (server-side, already built in Part A) | Support use case requires writes; every mutation is audit-logged. |
| Banner layout | **Normal-flow `shrink-0` bar, first child of the outer flex column** — NOT `position: fixed` | Fixed would z-fight the sticky header and require scroll-margin hacks (spec §6.5). |
| Sidebar collapse state | Shared `useSidebarState()` key `pilot.sidebar.collapsed` with tenant `AppSidebar` | "One product" feel (spec §3.3/§14.8). If Tom wants independent state, that's a follow-up — do not invent a second key in this batch. |
| `accountant` role | Selector browsable (read-only); selecting a tenant shows `NotificationBanner` warning, NOT the confirm modal | Hide-not-disable at the action level (spec §1.3/§4.7). |
| `MessagePreviewModal` | **Not used** — locked to comms previews | Spec §5.1/§13.2. |
| `RoleGate` | **Not used** on operator surfaces | Platform-level; visibility via `useAuthMe()` → `user_type`/`platform_role_code` (spec §1.3/§13.2). |

These were resolved in the design doc and approved spec. Do NOT change them without asking Tom.

---

## Pre-Work: Establish Regression Baseline

Before touching any file:

```bash
cd <repo>/frontend
pnpm --filter web test 2>&1 | tail -5
pnpm --filter @pilot/ui test 2>&1 | tail -5
```

Record the exact counts. These must still pass at the end of the batch.

> **If any tests are already failing before you start**: Do NOT treat them as "pre-existing" and proceed. Either (a) confirm with Tom that this is a known, accepted failure, or (b) fix the failure before touching any batch files.

## Pre-Work: Sync API Types (FIRST work step)

```bash
cd <repo>/frontend
pnpm sync-api-types
```

C-B15 Part A added 3 endpoints + 4 schemas. After sync, confirm these types exist in `packages/shared-types/src/api-schema.d.ts`: `OperatorTenantSummary`, `OperatorTenantListResponse`, `ImpersonationStartRequest`, `ImpersonationSessionResponse`. Consume via:

```typescript
import type { components } from "@pilot/shared-types";
type OperatorTenantSummary = components["schemas"]["OperatorTenantSummary"];
type ImpersonationSessionResponse = components["schemas"]["ImpersonationSessionResponse"];
```

## Pre-Work: Verify Endpoints

```bash
grep -A 5 "operator/tenants" backend/openapi_schema_map.md
grep -A 5 "impersonation/start" backend/openapi_schema_map.md
grep -A 5 "impersonation/end" backend/openapi_schema_map.md
```

Verified endpoints for this batch (confirmed present at prompt-authoring time — you re-confirm):

| Hook | Endpoint | Verified |
|---|---|---|
| `useOperatorTenants` | `GET /api/v1/operator/tenants` | ✅ in openapi_schema_map.md |
| `useImpersonationStart` | `POST /api/v1/operator/impersonation/start` | ✅ in openapi_schema_map.md |
| `useImpersonationEnd` | `POST /api/v1/operator/impersonation/end` | ✅ in openapi_schema_map.md |
| `useAuthMe` (existing) | `GET /api/v1/operator/auth/me` | ✅ (C-B11) |

**If an endpoint is NOT in `openapi_schema_map.md` → STOP. Do not invent a URL. Ask Tom.**

## Pre-Work: Read These Source Files

Read each of these with `read_file` before writing any code:

```
frontend/packages/shared-api/src/client.ts                  ← you are modifying the request interceptor
frontend/packages/ui/src/auth/AuthProvider.tsx              ← fetchUserFromBackend() raw fetch — you add one header (lines ~82–114)
frontend/apps/web/src/app/(authed)/layout.tsx               ← you mount the banner here; note the outer flex column structure (spec §6.5)
frontend/apps/web/src/components/AppSidebar.tsx             ← collapse conventions to mirror (pill toggle, useSidebarState, active treatment)
frontend/apps/web/src/hooks/useSidebarState.ts              ← shared collapse state hook you will reuse
frontend/apps/web/src/features/auth/hooks/useAuthMe.ts      ← platform guard source (user_type, platform_role_code)
frontend/apps/web/src/components/operator/cohort/CohortDashboardClient.tsx  ← you modify this (spec §7): remove RequireAuth wrapper, simplify page header
frontend/apps/web/src/app/operator/cohort/page.tsx          ← thin route — inherits your new layout automatically; no change needed
frontend/apps/web/src/features/operator/hooks/useCohortOverview.ts  ← hook conventions for the operator domain (query key style, retry: false)
frontend/apps/web/src/mocks/handlers/cohortDashboardHandlers.ts     ← operator-domain MSW handler conventions
frontend/apps/web/src/mocks/handlers/index.ts               ← barrel — you must register your new handler file here
frontend/packages/ui/src/index.ts                           ← confirm shared component imports (LoadingState, ErrorState, EmptyState, NotificationBanner, RequireAuth)
```

Also run:

```bash
find frontend/apps/web/src/features/operator -type f | head -20
grep -n "RequireAuth" frontend/packages/ui/src/index.ts
grep -rn "signOut" frontend/packages/ui/src/auth/AuthProvider.tsx | head -5   ← find the sign-out handler for the header logout button (spec §14.9)
```

---

## Context: What This Batch Does

C-B15 Part A (backend) is complete: platform users with `impersonate_tenant` can act as any tenant's owner via the `X-Impersonate-Tenant` header. Part B builds the frontend:

| # | Change | Files |
|---|---|---|
| 1 | Impersonation store + header injection | `packages/shared-api/src/impersonation.ts` (NEW), `client.ts` (MODIFIED) |
| 2 | Operator layout shell | `apps/web/src/app/operator/layout.tsx` (NEW) |
| 3 | Operator sidebar | `apps/web/src/components/operator/OperatorSidebar.tsx` (NEW) |
| 4 | Tenant selector | `apps/web/src/components/operator/TenantSelector.tsx` (NEW) |
| 5 | Confirm modal | `apps/web/src/components/operator/ImpersonationConfirmModal.tsx` (NEW) |
| 6 | Impersonation banner | `apps/web/src/components/operator/ImpersonationBanner.tsx` (NEW) + mount in both layouts |
| 7 | AuthProvider header | `packages/ui/src/auth/AuthProvider.tsx` (MODIFIED — one header line) |
| 8 | Hooks ×3 | `apps/web/src/features/operator/hooks/` (NEW) |
| 9 | MSW handlers | `apps/web/src/mocks/handlers/operatorTenantsHandlers.ts` (NEW) + barrel registration |
| 10 | Cohort page adjustment | `CohortDashboardClient.tsx` (MODIFIED — spec §7) |
| 11 | Tests | unit + `apps/web/src/__tests__/batch_c_b15/` integration |

---

## STEP 1 — Impersonation store: `packages/shared-api/src/impersonation.ts` (NEW)

Per design §F.3 + spec §14.3:

```typescript
export interface ImpersonationSession { tenantId: string; tenantName: string; }
export function getImpersonation(): ImpersonationSession | null
export function setImpersonation(s: ImpersonationSession): void
export function clearImpersonation(): void
export function useImpersonation(): ImpersonationSession | null
```

- `sessionStorage` key `pilot.impersonation` = `JSON.stringify({ tenantId, tenantName })`.
- `getImpersonation()`: read + parse; return `null` if absent/invalid/SSR (`typeof window === "undefined"` guard — this package is imported by server-rendered layouts).
- `setImpersonation`/`clearImpersonation`: write/remove + dispatch `new CustomEvent("pilot:impersonation-change")` on `window`.
- `useImpersonation()`: React hook — read on mount (`useState` initializer with lazy read), subscribe to the custom event + `storage` event in a `useEffect`, return current value. This is a legitimate identity-sensitive Context-adjacent case — a small hand-rolled subscription is fine; do not over-engineer.
- Add the export to `packages/shared-api/src/index.ts` (read it first).

Then modify `client.ts`: in the **request interceptor**, after the JWT attach block, add:

```typescript
const imp = getImpersonation();
if (imp) config.headers["X-Impersonate-Tenant"] = imp.tenantId;
```

Read synchronously from `sessionStorage` on every request — no React state (spec §14.4). Keep the existing dev-mode logging style.

**Intermediate verification**: `pnpm --filter web test 2>&1 | tail -5` (existing apiClient tests in `packages/shared-api/src/client.test.ts` may need a sessionStorage stub — check and update that test file if the interceptor change breaks it).

## STEP 2 — Hooks: `apps/web/src/features/operator/hooks/` (3 NEW files)

Per spec §14.6. TanStack Query v5 object-form, `retry: false`, colocated key constants, types from `@pilot/shared-types`:

- `useOperatorTenants.ts` — `export const OPERATOR_TENANTS_QUERY_KEY = ["operator-tenants"] as const;` `useQuery({ queryKey, queryFn: async () => (await apiClient.get<OperatorTenantListResponse>("/api/v1/operator/tenants")).data, staleTime: 5 * 60 * 1000, retry: false })`
- `useImpersonationStart.ts` — `useMutation({ mutationFn: ({ tenantId }: { tenantId: string }) => apiClient.post<ImpersonationSessionResponse>("/api/v1/operator/impersonation/start", { tenant_id: tenantId }), retry: false })`. Match the C-B11 hook style (`useExtendFreePeriod.ts`) — read it.
- `useImpersonationEnd.ts` — same shape, POST `/api/v1/operator/impersonation/end`, body `{ tenant_id: tenantId }`.

**Intermediate verification**: co-located hook unit tests (see Test Implementation) — `pnpm --filter web test -- apps/web/src/features/operator/hooks/__tests__/ 2>&1 | tail -10`.

## STEP 3 — MSW handlers: `apps/web/src/mocks/handlers/operatorTenantsHandlers.ts` (NEW)

Per spec §14.7: 8–12 fixture tenants with varied tiers and statuses (`trialing`, `active`, `past_due`, `canceled`, one `null` subscription). POST start → `ImpersonationSessionResponse` success; POST end → `{ "ended": true }`.

**Mandatory barrel step**: register in `mocks/handlers/index.ts` — import + spread `...operatorTenantsHandlers`. Without this the handlers are never loaded. Check for duplicate paths first (cohort handlers don't cover these).

## STEP 4 — `OperatorSidebar`: `apps/web/src/components/operator/OperatorSidebar.tsx` (NEW)

Spec §3 is binding: nav aria-label "Operator navigation"; item 1 "Cohort Dashboard" (`Squares2X2Icon`, `/operator/cohort`, active treatment identical to `AppSidebar`); item 2 disabled placeholder "More operator tools / Coming soon" (`EllipsisHorizontalCircleIcon`, `aria-disabled="true"`); pill toggle identical to `AppSidebar`; reuse `useSidebarState()` (shared key — Design Decisions table). `usePathname()` for active state. Mirror `AppSidebar` structure — read it first and adapt; do not fork the patterns.

## STEP 5 — `TenantSelector`: `apps/web/src/components/operator/TenantSelector.tsx` (NEW)

Spec §4 is binding: trigger button (44px min height, `aria-haspopup="listbox"`, `aria-expanded`); dropdown panel (`w-96`, search input with `MagnifyingGlassIcon`, clear button, list `max-h-80`, footer "{N} tenants"); subscription-status pill per §4.4 (icon + label, color-independent — build a small internal `StatusPill` subcomponent, reused by the modal preview per spec §5.6); keyboard nav (ArrowUp/Down, Enter, Escape); client-side filtering (§16.6 — no refetch); loading skeleton / `<EmptyState>` / `<ErrorState>` / no-results states per §4.5.

Props: `platformRoleCode: string` (from `useAuthMe`). On select: `owner`/`support` → open `ImpersonationConfirmModal`; `accountant` → show `NotificationBanner` warning "Your role does not permit impersonation." (spec §4.7).

## STEP 6 — `ImpersonationConfirmModal`: `apps/web/src/components/operator/ImpersonationConfirmModal.tsx` (NEW)

Spec §5 is binding. Standard modal pattern (overlay `fixed inset-0 bg-neutral-900/50 z-50`, panel `max-w-md`, focus trap, `role="dialog"` + `aria-modal="true"` + `aria-labelledby`, focus to Cancel on open, return focus to the selector trigger on close, Escape/overlay = Cancel). Preview block (tenant/tier/status-pill/role), warning sentence ("All changes you make are real and audit-logged."), persistence note, Cancel (default safe) / "View as {name}" primary.

On confirm → `useImpersonationStart` → on success: `setImpersonation({ tenantId, tenantName })` → `window.location.assign("/dashboard")`. **Full reload — hard rule** (Design Decisions). Error mapping per §5.9 (403/404/409 → specific messages, modal stays open). In-flight state per §5.10.

## STEP 7 — `ImpersonationBanner`: `apps/web/src/components/operator/ImpersonationBanner.tsx` (NEW)

Spec §6 is binding: `h-10 bg-alert-50 border-b border-alert-200` normal-flow bar (`shrink-0`, NOT fixed); `EyeIcon` + "Viewing as: **{tenantName}**"; Exit button (`ArrowRightOnRectangleIcon` + "Exit", `aria-label="Exit impersonation and return to operator cohort"`); `role="status"` + `aria-live="polite"` on the text container.

On exit → `useImpersonationEnd` → on **settle** (success or failure — spec §8.4): `clearImpersonation()` → `window.location.assign("/operator/cohort")`. In-flight: "Exiting…" + disabled.

## STEP 8 — `OperatorLayout`: `apps/web/src/app/operator/layout.tsx` (NEW)

Spec §2 is binding. This is a **client layout** (`"use client"` — layouts may be client components; the thin-server-component rule applies to `page.tsx` route files, and this layout needs hooks for the guard):

1. Wrap in `<RequireAuth redirectTo="/login">` (from `@pilot/ui/auth` — verify the export name in `packages/ui/src/index.ts`).
2. Platform-user guard via `useAuthMe()` per spec §2.2: `isPending` → centered `<LoadingState>` "Verifying access…"; `isError` → `<ErrorState>` with retry (`queryClient.invalidateQueries({ queryKey: ["auth", "me"] })` — confirm the actual query key in `useAuthMe.ts`); `user_type === "tenant"` → `router.replace("/dashboard")` + render `null`; `"platform"` → render shell.
3. Shell structure per §2.1 ASCII: banner slot (`{useImpersonation() && <ImpersonationBanner />}`) → header (logo switch via `useSidebarState`, "Operator" badge, `<TenantSelector platformRoleCode={...}>`, logout icon button per §2.3 — wire to the existing Cognito sign-out from `AuthProvider`; spec §14.9) → sidebar + content area (`flex-1 min-w-0 overflow-auto bg-neutral-50`).

The existing `/operator/cohort` page inherits this layout automatically — do not touch `page.tsx`.

## STEP 9 — Mount banner in `(authed)/layout.tsx` (MODIFIED)

Per spec §6.5: insert `{useImpersonation() && <ImpersonationBanner />}` as the **first child** of the outer flex column, before the header. The outer div is `flex flex-col h-full min-h-screen` — the banner is a `shrink-0` sibling; no other layout changes. The layout is already a client component — add the hook import from `@pilot/shared-api`.

## STEP 10 — `AuthProvider.tsx` header (MODIFIED)

In `fetchUserFromBackend()`, add the impersonation header to the existing raw `fetch()` (sanctioned exception — do not refactor to apiClient):

```typescript
const imp = getImpersonation();
const res = await fetch(`${apiBase}/api/v1/users/me/permissions`, {
  headers: {
    Authorization: `Bearer ${token}`,
    ...(imp ? { "X-Impersonate-Tenant": imp.tenantId } : {}),
  },
});
```

Import `getImpersonation` from `@pilot/shared-api` (verify the package dependency exists in `packages/ui/package.json` — if it does not, STOP and ask Tom rather than adding a dependency silently).

## STEP 11 — Cohort page adjustment (MODIFIED)

Per spec §7: in `CohortDashboardClient.tsx`, remove the `RequireAuth` wrapper (the operator layout now provides auth + platform guard). Keep the `useAuthMe()` call (permission flags still needed). Page header: remove logo, title → "Charter Cohort", keep Close Cohort button, container `h-16 bg-white border-b border-neutral-200 px-6 flex items-center justify-between sticky top-0 z-20`. **No other C-B11 changes** (§7.2).

Existing C-B11 tests may assert on the removed header/wrapper — update them as part of this step (Rule 10: all tests green).

---

## Test Implementation

### Setup rules (all mandatory)

- Fresh `QueryClient` per test with `queries.retry: false` and `mutations.retry: false`. Never share instances.
- MSW `setupServer` from `msw/node`; `server.listen({ onUnhandledRequest: "warn" })`; `server.resetHandlers()` in `afterEach`; `server.close()` in `afterAll`. **Never mock `apiClient` directly.**
- Mock `next/navigation` in any test touching components that use `useRouter`/`usePathname` (`vi.mock("next/navigation", ...)`).
- `sessionStorage`: stub/clear in `beforeEach` for store + banner tests (`window.sessionStorage.clear()`); assert header injection by inspecting the intercepted MSW request (`request.headers.get("X-Impersonate-Tenant")`).
- `window.location.assign`: jsdom does not implement navigation — stub it (`vi.stubGlobal` or delete + assign a `vi.fn()` on `window.location`) in modal/banner tests; assert it was called with `/dashboard` or `/operator/cohort`.
- Web assertions: `toBeInTheDocument()` (not `.toBeTruthy()`).

### Unit tests (co-located `__tests__/`)

| File | Coverage |
|---|---|
| `packages/shared-api/src/impersonation.test.ts` (NEW) | get/set/clear round-trip; invalid JSON → null; custom event dispatched; `useImpersonation` reflects changes |
| `client.test.ts` (UPDATE if needed) | interceptor attaches `X-Impersonate-Tenant` when session present; absent when not |
| `features/operator/hooks/__tests__/useOperatorTenants.test.tsx` | data shape, query key, error state |
| `features/operator/hooks/__tests__/useImpersonationStart.test.tsx` + `useImpersonationEnd.test.tsx` | correct method/URL/payload; error surfaces |
| `components/operator/__tests__/TenantSelector.test.tsx` | renders trigger; opens panel; filters list; accountant → warning banner (no modal); owner → modal opens |
| `components/operator/__tests__/ImpersonationConfirmModal.test.tsx` | preview block renders tenant/tier/status; Cancel closes without mutation; confirm fires POST + `setImpersonation` + `location.assign('/dashboard')`; 403/409 error messages per spec §5.9 |
| `components/operator/__tests__/ImpersonationBanner.test.tsx` | renders "Viewing as:" + tenant name; Exit fires POST end + `clearImpersonation` + `location.assign('/operator/cohort')` |
| `components/operator/__tests__/OperatorSidebar.test.tsx` | nav items render; placeholder is `aria-disabled`; collapse toggle works |

### Integration tests: `apps/web/src/__tests__/batch_c_b15/operator-shell.integration.test.tsx` (NEW)

1. Operator layout renders for platform user (MSW: `GET /operator/auth/me` → `user_type: "platform"`) — sidebar + header + cohort content visible.
2. Tenant user (`user_type: "tenant"`) → redirect to `/dashboard` (assert `router.replace` called).
3. Full impersonation flow: open selector → pick tenant → confirm modal → POST start fires with correct payload → session written → reload triggered.
4. Banner renders in the tenant shell when `sessionStorage` has a session; Exit clears + reloads.
5. Cohort page renders inside the shell without its own `RequireAuth` (no double auth gate).

---

## Final Verification

> ❌ **BANNED COMMAND**: `npx vitest run` — **NEVER use this**. The ONLY correct runner is `pnpm --filter web test` (optionally with `-- <path>`).

### Phase 1 — Targeted tests (run after each task group during development)

```bash
cd <repo>/frontend
pnpm --filter web test -- apps/web/src/__tests__/batch_c_b15/ 2>&1 | tail -10
pnpm --filter web test -- apps/web/src/components/operator/ 2>&1 | tail -10
pnpm --filter @pilot/ui test 2>&1 | tail -6
```

Fix any failure before moving to the next task — including failures that appear pre-existing.

### Phase 2 — Full verification (run once at the very end, before DoD sign-off)

```bash
cd <repo>/frontend && echo "=== UI - Type Check ===" && pnpm --filter @pilot/ui check-types && echo "=== Web - Type Check ===" && pnpm --filter web check-types && echo "=== Mobile - Type Check ===" && pnpm --filter mobile build && echo "=== UI - Lint ===" && pnpm --filter @pilot/ui lint && echo "=== Web - Lint ===" && pnpm --filter web lint && echo "=== Mobile - Lint ===" && pnpm --filter mobile lint && echo "=== TYPE+LINT PASS ===" && echo "=== UI - Tests ===" && pnpm --filter @pilot/ui test 2>&1 | tail -6 && echo "=== Web - Tests ===" && pnpm --filter web test 2>&1 | tail -6 && echo "=== Mobile - Tests ===" && pnpm --filter mobile test 2>&1 | tail -8 && echo "=== MVP FINAL VERIFICATION COMPLETE ==="
```

> **`pnpm --filter mobile build` = mobile type check.** Any failure in either phase must be fixed before the batch is declared done. If you cannot identify the root cause → STOP and ask Tom.

---

## Definition of Done — C-B15 Part B

- [ ] Pre-modification regression baseline captured (web + @pilot/ui; zero pre-existing failures, or confirmed with Tom)
- [ ] `pnpm sync-api-types` run — all 4 new schema types present in `api-schema.d.ts`; no new type errors
- [ ] Design doc + Tom-approved UI design spec fully read before writing any code
- [ ] All mandatory source files read before modifying (including `mocks/handlers/index.ts` and `packages/ui/src/index.ts`)
- [ ] All 4 endpoint URLs verified in `openapi_schema_map.md`
- [ ] **STEP 1**: `impersonation.ts` store created + exported from `packages/shared-api/src/index.ts`; `client.ts` interceptor injects `X-Impersonate-Tenant`
- [ ] **STEP 2**: 3 hooks created (object-form TQ v5, `retry: false`, colocated keys, `@pilot/shared-types` types)
- [ ] **STEP 3**: `operatorTenantsHandlers.ts` created AND registered in the `index.ts` barrel
- [ ] **STEP 4–7**: `OperatorSidebar`, `TenantSelector` (+ internal StatusPill), `ImpersonationConfirmModal`, `ImpersonationBanner` built to the spec (tokens only — zero hex codes)
- [ ] **STEP 8**: `operator/layout.tsx` created — RequireAuth + platform guard (pending/error/redirect states) + shell
- [ ] **STEP 9**: banner mounted as first child of `(authed)/layout.tsx` outer flex column (normal flow, not fixed)
- [ ] **STEP 10**: `AuthProvider.fetchUserFromBackend()` attaches the header (no apiClient refactor)
- [ ] **STEP 11**: `CohortDashboardClient` — RequireAuth removed, header simplified; affected C-B11 tests updated
- [ ] Full reload (`window.location.assign`) on both start and exit — NO in-place context switch (hard rule)
- [ ] No hand-written `useMemo`/`useCallback`/`React.memo` for render-perf (React Compiler, rules §32)
- [ ] No tenant-data fetching in Server Components (rules §35); `page.tsx` files untouched/thin
- [ ] axe-core zero violations + WCAG 2.2 AA spot-checks: modal focus trap + return focus, `role="status"`/`aria-live` on banner, ≥24×24px targets, color-independent status pills + banner (rules §36)
- [ ] No new npm dependencies added without Tom's explicit approval
- [ ] Unit tests pass (targeted run) — one file per new component/hook + store
- [ ] Integration tests pass in `__tests__/batch_c_b15/`
- [ ] Zero TypeScript errors; zero ESLint `no-hardcoded-design-values` warnings
- [ ] **Phase 2 FULL verification command passes** (`=== MVP FINAL VERIFICATION COMPLETE ===`) — exact command above
- [ ] Final test count (before → after) documented
- [ ] Completion Summary added to launch plan (see below)

## Completion Summary

After all Definition of Done items are complete, add a **Completion Summary** subsection to `dev-docs/analysis/pilot-launch-plan.md`, directly beneath the C-B15 Part A summary:

```markdown
### C-B15 (Part B — React Engineer) — Platform Shell + Tenant Impersonation Frontend: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot React Engineer
**Baseline**: X passed, Y failed (web) | X passed (@pilot/ui)
**Final**: X+N passed, Y failed (+N new tests)

#### What Was Accomplished
- ...

#### Files Changed / Created
| File | Action |
|---|---|
| ... | ... |

#### Tests Added
| Test File | Type | Tests | All Pass |
|---|---|---|---|
| ... | ... | ... | ✅ |
```

Also update launch plan row 14v status to `✅ COMPLETE (Part A + Part B)` with the final counts, and mark the design doc header status `Complete`.

## After This Task — Next Step

- **C-B14-FIX (row 14v2)** — Stripe hardening follow-ups (Python), may run next in parallel
- **TELNYX-SPIKE-1 (row 14w)** — deferred until C-B15 completes (your completion unblocks it)
