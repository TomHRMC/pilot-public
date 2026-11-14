# Implementation Prompt: COMMS-UI-B1 (Part B — Web) — Communications Page: TanStack Table + Search + Filter + Paginator

**Mode**: Pilot React Engineer
**Batch**: COMMS-UI-B1 (Part B — web FE half of a mixed batch)
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §2.3 → COMMS-UI-B1
**Design doc**: none (self-contained; consumes the Part A contract)
**Estimated session**: 3–4 hours
**Platform**: Web only (`apps/web`)
**Backend companion**: COMMS-UI-B1 (Part A — Python Engineer) — `batch-comms-ui-b1-python-engr-prompt.md`. **Part A must be merged + `python export_openapi_json.py` run before you start.**

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-react-engineer/react-engineer-rules.md`** — in full.

Critical rules for this batch:

- **Rule 1.1**: Before writing the hook, verify `GET /api/v1/communications/recent` and its new params exist in `backend/openapi_schema_map.md`. If the new params (`customer_search`, `channel`, `sent_from`, `sent_to`, `offset`, `limit`) are NOT there → Part A hasn't landed → **STOP and ask Tom**.
- **Rule 1.3**: Run `pnpm sync-api-types` before starting — the response shape changed (Part A migrated `page`/`page_size` → `limit`/`offset`). Stale types will silently break.
- **Rule 2**: All API calls use `apiClient` from `@pilot/shared-api`. `fetch()` is permanently banned. (The current `comms/page.tsx` already uses `apiClient` — keep it.)
- **Rule 7**: Check what already exists before building: `PilotPaginator` (`apps/web/src/components/PilotPaginator.tsx`), `<LoadingState>`/`<ErrorState>`/`<EmptyState>` from `@pilot/ui/states`, and the TanStack Table setup from FE-B28 (all 8 existing tables). Do NOT hand-roll a paginator or a table framework.
- **Rule 9**: Route files in `apps/web/src/app/(authed)/` MUST be thin. Today `comms/page.tsx` is a `"use client"` page component doing its own fetch — **refactor**: move all logic into a `features/comms/` feature component and make the route file thin.
- **Rule 10**: If ANY test fails during your work — even apparently pre-existing — fix it before declaring done. If you cannot find the root cause → STOP and ask Tom.
- **Rule 11 (React Compiler — rules §32)**: `apps/web` runs React 19.2 with the React Compiler. Do NOT hand-write `useMemo`/`useCallback`/`React.memo` for render-perf on the table rows, column defs, or filtered data — the compiler memoizes automatically. Keep `CommsPage` pure (no mutating props/state/hook returns during render). Narrow identity-only exceptions still apply (a value in a `useEffect` dep array).
- **Rule 12 (TanStack Query v5 — rules §33)**: Object-form only (`useQuery({ queryKey, queryFn })`); `isPending` not `isLoading`; `gcTime` not `cacheTime`. The query key MUST include every param the `queryFn` reads (`limit`, `offset`, `customer_search`, `channel`, `sent_from`, `sent_to`) so a filter change refetches. Use `placeholderData: keepPreviousData` so the table doesn't flash empty on page/filter change.
- **Rule 14 (server vs client — rules §35)**: Authenticated data fetching stays **client-side** — `useRecentComms` runs in the `"use client"` `CommsPage` feature component. Never move the `/recent` fetch into the route Server Component or a Route Handler (the Amplify session is browser-held and 401s server-side).
- **Rule 15 (WCAG 2.2 AA — rules §36)**: The new filter bar + table surface must satisfy: Target Size ≥24×24px on the channel pills / paginator buttons / date inputs, non-color-only channel + direction badges (pair the color with a text label / icon), `focus-visible` rings, and modal focus management if any filter opens a popover. Backs the axe-core DoD gate.

**Invoice/comms note — no "email" data today:** The backend `channel` filter is SMS-only in the current data (Part A Design Decision D-1). The Email pill is wired for forward-compat; selecting it legitimately returns 0 rows. Do NOT fake email fixtures to make it "look populated" — one MSW fixture may carry `channel: "email"` to prove the pill filters, but the honest default is SMS-dominant.

---

## Design Decisions (Do Not Re-Litigate)

From Part A + the launch-plan card — these are final:

| Decision | Outcome | Rationale |
|---|---|---|
| Table framework | **TanStack Table** (mirror the FE-B28 pattern used by the other 8 tables) — replace the raw `<table>` | Consistency + sorting for free |
| Pagination | **`PilotPaginator`** driven by `offset`/`limit` from the API response | Canonical; already built |
| Sortable columns | Client-side sort on Customer, Channel, Direction, Time (the current page has zero sorting) | Table is small per page (≤200) |
| Filter bar | Customer search (debounced text) + Channel pill (`SMS`/`Email`) + Date range (`sent_from`/`sent_to`) | From the card |
| Filter → query | Filters go into the **query key + params** so the API re-fetches server-side (do NOT filter client-side — the endpoint filters) | `total` must reflect filters for the paginator |
| Channel default | No channel filter selected = all channels (today = all SMS) | D-1 |
| RBAC gate | Wrap page content in `<RoleGate permission="comms.send">` — the only comms permission key in `permissions.ts` (`communications.view` is a backend-only key). All roles currently have `comms.send`. Do NOT add a new permission key in this batch. | Verified in `packages/ui/src/role-gate/permissions.ts` |

> **Preserve these existing testids** (an E2E Playwright spec + others depend on them): `data-testid="comms-page"`, `data-testid="recent-comms-table"`, `data-testid="comm-row-{id}"`, the "No messages sent yet…" empty text, the `SMS`/`Email` channel span, and the customer `Link` to `/customers/{customer_id}/comms`. See `apps/web/src/__tests__/e2e/cp4_customer_sms.playwright.ts`.

---

## Pre-Work: Establish Regression Baseline

```bash
cd <repo>/frontend
pnpm --filter web test 2>&1 | tail -5
```

Record the exact count. It must still pass at the end.

> If any test is already failing: do NOT proceed. Fix it or confirm with Tom first.

---

## Pre-Work: Sync API Types

```bash
cd <repo>/frontend
pnpm sync-api-types
```

This regenerates `packages/shared-types/src/api-schema.d.ts` from Part A's OpenAPI. The `RecentCommunicationsResponse` type now has `{ items, total, limit, offset }` (no more `page`/`page_size`). Import the backend types from `@pilot/shared-types` — do not hand-write the response interface (the current `comms/page.tsx` hand-writes it; replace with the generated type or a thin local alias marked for removal).

---

## Pre-Work: Verify Endpoints

```bash
grep -A 15 "communications/recent\"" backend/openapi_schema_map.md
```

| Hook | Endpoint | Verified |
|---|---|---|
| `useRecentComms` | `GET /api/v1/communications/recent?limit&offset&customer_search&channel&sent_from&sent_to` | ☐ confirm the params appear before coding |

If the params are missing → Part A not merged → STOP.

---

## Pre-Work: Read These Source Files

```
frontend/apps/web/src/app/(authed)/comms/page.tsx                 ← current page — being refactored to thin route + feature component
frontend/apps/web/src/components/PilotPaginator.tsx               ← offset/limit paginator props (total, limit, offset, onPageChange)
frontend/apps/web/src/mocks/handlers/communications.ts            ← existing /recent MSW handler (~line 218) — update to new params + shape
frontend/apps/web/src/mocks/handlers/index.ts                     ← confirm communicationHandlers is already registered (do not double-register)
frontend/apps/web/src/__tests__/e2e/cp4_customer_sms.playwright.ts ← the testids you must preserve
```

Find the FE-B28 TanStack Table reference to mirror (columns, `useReactTable`, sorting state):

```bash
grep -rln "useReactTable\|getSortedRowModel" frontend/apps/web/src/features | head
grep -rln "PilotPaginator" frontend/apps/web/src/features | head
```

Read one of those files as your table + paginator wiring reference.

---

## Context: What This Batch Does

| Before | After |
|---|---|
| `/comms` is a raw `<table>` in a `"use client"` route file; no sort, no search, no filter; hardcoded `page:1,page_size:50`; hand-written response interface | Thin route → `features/comms/CommsPage` feature component; TanStack Table w/ sortable columns; filter bar (customer search + channel pill + date range) driving server-side params; `PilotPaginator`; generated types; `<RoleGate>` |

---

## STEP 1 — `useRecentComms` hook

Create `frontend/apps/web/src/features/comms/hooks/useRecentComms.ts`:

- `useQuery` against `GET /api/v1/communications/recent` via `apiClient`.
- Params object: `{ limit, offset, customer_search?, channel?, sent_from?, sent_to? }`.
- Query key: `["recent-comms", { limit, offset, customer_search, channel, sent_from, sent_to }]` — so any filter change refetches.
- `retry: false` awareness for tests; `staleTime: 30_000` (preserve current behavior).
- Return type from `@pilot/shared-types` (`RecentCommunicationsResponse`).

> Read the file first; adjust import paths (`apiClient` from `@pilot/shared-api`) to what you find.

Intermediate check: `pnpm --filter web test -- apps/web/src/features/comms 2>&1 | tail -10` (after you add the hook test).

---

## STEP 2 — Feature component `CommsPage`

Create `frontend/apps/web/src/features/comms/components/CommsPage.tsx` (`"use client"`):

- Local state: `offset` (default 0), `limit` (50), `customerSearch` (debounced ~300ms), `channel` (`"" | "sms" | "email"`), `sentFrom`, `sentTo`.
- Call `useRecentComms(...)` with those.
- **Filter bar** above the table:
  - Customer search text input (debounced) — `data-testid="comms-customer-search"`.
  - Channel pill toggle `All · SMS · Email` — `data-testid="comms-channel-filter"`. Selecting resets `offset` to 0.
  - Date range: two `<input type="date">` (or the existing shared date control if one exists in `@pilot/ui`) → `sent_from`/`sent_to` as ISO datetimes. `data-testid="comms-date-from"` / `comms-date-to`.
  - Any filter change → reset `offset` to 0.
- **Table**: TanStack Table, columns Customer (link, sortable), Channel (SMS/Email badge, sortable), Direction (sortable), Message (truncated, `title` full body), Time (sortable). Keep `data-testid="recent-comms-table"` on the table and `comm-row-{id}` on rows.
- **States**: `<LoadingState>` while fetching, `<ErrorState onRetry>` on error, empty text "No messages sent yet. Visit a customer to send their first message." when `items.length === 0` (preserve exact string).
- **`PilotPaginator`** below the table: `total={data.total} limit={limit} offset={offset} onPageChange={setOffset}`.
- Root `<main data-testid="comms-page">`, `<h1>Communications</h1>`.

Preserve every testid listed in the Design Decisions note.

---

## STEP 3 — Thin route file

Rewrite `frontend/apps/web/src/app/(authed)/comms/page.tsx` to be thin (no `"use client"`, no fetch):

```tsx
import { CommsPage } from "@/features/comms/components/CommsPage";
export default function Page() {
  return <CommsPage />;
}
```

Wrap the content in `<RoleGate permission="comms.send">` — either inside `CommsPage` (preferred, so tests can render the component directly) or the route. Verify the import path for `RoleGate` via `grep -n "RoleGate" frontend/packages/ui/src/index.ts`.

---

## STEP 4 — Update MSW handler

In `apps/web/src/mocks/handlers/communications.ts` (~line 218), update the `/recent` handler to:
- Read `limit`, `offset`, `customer_search`, `channel`, `sent_from`, `sent_to` (not `page`/`page_size`).
- Apply the filters to `RECENT_COMMS_FIXTURE` (customer_name ilike, channel eq, created_at range), then slice by `offset`/`limit`.
- Return `{ items, total, limit, offset }`.
- Ensure the fixture has **varied** data: multiple customers, both directions, and at least one `channel: "email"` row so the Email pill filter is provably exercised (D-1 — email is otherwise empty in real data; this is a test fixture only).

`communicationHandlers` is already registered in `index.ts` — do not re-register.

---

## Test Requirements

Use the standard TanStack Query `createWrapper()` (`retry: false`) + MSW `setupServer` patterns. Mock `next/navigation` and `next/link` for any component test.

**Unit** — `features/comms/hooks/__tests__/useRecentComms.test.ts`:
- Returns data shape with mock response; error state on 500; query key includes the filter params.

**Integration** — `apps/web/src/__tests__/batch_comms_ui_b1/comms_ui_b1.integration.test.tsx`:
1. Route renders (not 404); `comms-page` + `recent-comms-table` present with MSW data.
2. `<RoleGate>` — a role without `comms.send` sees nothing (use the `AuthContext.Provider` pattern; note all seeded roles currently HAVE `comms.send`, so construct a role value without it to prove the gate).
3. Customer search input fires a request with `customer_search=` (assert via `server.use` spy or by asserting the filtered rows shown).
4. Channel pill `Email` → fires `channel=email`; with the one email fixture, shows exactly that row; `SMS` → shows SMS rows only.
5. Sorting a column reorders rows.
6. `PilotPaginator` next-page click calls the API with an increased `offset`.
7. Empty state string renders when the handler returns `{items:[], total:0, limit, offset}`.

> Assert by specific content/IDs from the MSW fixture — never by hardcoded total counts.

---

## Final Verification

> ❌ **BANNED**: `npx vitest run`. Only `pnpm --filter web test`.

### Phase 1 — Targeted

```bash
cd <repo>/frontend
pnpm --filter web test -- apps/web/src/features/comms 2>&1 | tail -10
pnpm --filter web test -- apps/web/src/__tests__/batch_comms_ui_b1/ 2>&1 | tail -10
```

### Phase 2 — Full canonical

```bash
cd <repo>/frontend && echo "=== UI - Type Check ===" && pnpm --filter @pilot/ui check-types && echo "=== Web - Type Check ===" && pnpm --filter web check-types && echo "=== Mobile - Type Check ===" && pnpm --filter mobile build && echo "=== UI - Lint ===" && pnpm --filter @pilot/ui lint && echo "=== Web - Lint ===" && pnpm --filter web lint && echo "=== Mobile - Lint ===" && pnpm --filter mobile lint && echo "=== TYPE+LINT PASS ===" && echo "=== UI - Tests ===" && pnpm --filter @pilot/ui test 2>&1 | tail -6 && echo "=== Web - Tests ===" && pnpm --filter web test 2>&1 | tail -6 && echo "=== Mobile - Tests ===" && pnpm --filter mobile test 2>&1 | tail -8 && echo "=== MVP FINAL VERIFICATION COMPLETE ==="
```

> Any failure in either phase must be fixed before done. No "pre-existing" exception without Tom's written OK.

---

## Definition of Done — COMMS-UI-B1 (Part B)

- [ ] Regression baseline captured (zero pre-existing failures, or confirmed with Tom)
- [ ] `pnpm sync-api-types` run — no new type errors; response type is `{items,total,limit,offset}`
- [ ] `/recent` params verified in `openapi_schema_map.md` before coding
- [ ] All mandatory source files read (incl. `PilotPaginator`, the E2E testid spec, `mocks/handlers/index.ts`)
- [ ] **STEP 1**: `useRecentComms` hook created (query key includes all filter params)
- [ ] **STEP 2**: `features/comms/components/CommsPage.tsx` — TanStack Table + filter bar + PilotPaginator + states
- [ ] **STEP 3**: `comms/page.tsx` refactored to thin route; content wrapped in `<RoleGate permission="comms.send">`
- [ ] **STEP 4**: `/recent` MSW handler updated to new params + `{items,total,limit,offset}` + one email fixture row
- [ ] All preserved testids intact (`comms-page`, `recent-comms-table`, `comm-row-{id}`, empty-state string, channel span, customer link)
- [ ] Filters drive **server-side** params (not client-side filtering); `offset` resets to 0 on any filter change
- [ ] No hand-written `useMemo`/`useCallback`/`React.memo` for render-perf; `CommsPage` is pure (React Compiler, rules §32)
- [ ] `useRecentComms` uses TanStack Query v5 object-form; query key includes all 6 filter params; `placeholderData: keepPreviousData` set (rules §33)
- [ ] Data fetching is client-side only — no `/recent` fetch in a Server Component / Route Handler (rules §35)
- [ ] axe-core zero violations + WCAG 2.2 AA spot-checks (pills/paginator/date targets ≥24px, non-color-only channel + direction badges, focus-visible) (rules §36)
- [ ] No new npm dependency; no `fetch()`; no new permission key added
- [ ] Unit + integration tests pass (targeted run)
- [ ] Zero TypeScript errors; zero ESLint `no-hardcoded-design-values` warnings
- [ ] **Phase 2 FULL verification command passes** (`=== MVP FINAL VERIFICATION COMPLETE ===`):
  ```bash
  cd <repo>/frontend && echo "=== UI - Type Check ===" && pnpm --filter @pilot/ui check-types && echo "=== Web - Type Check ===" && pnpm --filter web check-types && echo "=== Mobile - Type Check ===" && pnpm --filter mobile build && echo "=== UI - Lint ===" && pnpm --filter @pilot/ui lint && echo "=== Web - Lint ===" && pnpm --filter web lint && echo "=== Mobile - Lint ===" && pnpm --filter mobile lint && echo "=== TYPE+LINT PASS ===" && echo "=== UI - Tests ===" && pnpm --filter @pilot/ui test 2>&1 | tail -6 && echo "=== Web - Tests ===" && pnpm --filter web test 2>&1 | tail -6 && echo "=== Mobile - Tests ===" && pnpm --filter mobile test 2>&1 | tail -8 && echo "=== MVP FINAL VERIFICATION COMPLETE ==="
  ```
- [ ] Final test count (before → after) documented
- [ ] Completion Summary added to launch plan Appendix B + one-row Appendix A entry

---

## Completion Summary

After all DoD items are complete, add a **Completion Summary** to `pilot-launch-plan.md` Appendix B (React Engineer template) and a one-row entry to Appendix A, using the format below. Mark the COMMS-UI-B1 gate item in Section 5 ✅ once both halves are merged.

```markdown
### COMMS-UI-B1 (Part B — Web) — Communications Page Search/Filter/Paginator: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot React Engineer
**Baseline**: X passed, Y failed (web)
**Final**: X+N passed, Y failed (+N new tests)

#### What Was Accomplished

- [Brief description of key change 1 — e.g. refactored `/comms` to thin route + `features/comms/CommsPage`]
- [Brief description of key change 2 — e.g. TanStack Table + filter bar driving server-side params]
- [Root cause analysis if a bug was fixed]

#### Files Changed / Created

| File | Action |
|---|---|
| `frontend/apps/web/src/features/comms/hooks/useRecentComms.ts` | Created — TanStack Query v5 hook |
| `frontend/apps/web/src/features/comms/components/CommsPage.tsx` | Created — table + filter bar + PilotPaginator |
| `frontend/apps/web/src/app/(authed)/comms/page.tsx` | Updated — refactored to thin route |
| `frontend/apps/web/src/mocks/handlers/communications.ts` | Updated — `/recent` new params + `{items,total,limit,offset}` |
| ... | ... |

#### Tests Added

| Test File | Type | Tests | All Pass |
|---|---|---|---|
| `apps/web/src/features/comms/hooks/__tests__/useRecentComms.test.ts` | Unit | N | ✅ |
| `apps/web/src/__tests__/batch_comms_ui_b1/comms_ui_b1.integration.test.tsx` | Integration | N | ✅ |
```
