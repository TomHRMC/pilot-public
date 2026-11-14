# Implementation Prompt: UP-1 (Part B) — WIP Report Page (Web)

**Mode**: Pilot React Engineer
**Batch**: UP-1 — Part B (Frontend Web)
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §2.3 UP-1
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-up-1-design.md` (§D endpoint contract, §G decisions, §I manifest)
**UI design spec** (Tom-approved, Rule 1.5): `dev-docs/architecture-design/batch-designs/batch-up-1-ui-design-spec.md` — **read every section; it is pixel-authoritative**
**Estimated session**: 4–6 hours
**Platform**: Web only (`apps/web`) — desktop-first at 1280px
**Backend companion**: **UP-1 Part A is COMPLETE** — `GET /api/v1/reports/wip` (+ `/test`) is live in `openapi_schema_map.md`. No backend work in this batch; no MSW-for-missing-endpoint needed (the endpoint is real).

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-react-engineer/react-engineer-rules.md`** — in full
- **`batch-up-1-ui-design-spec.md`** — every section (§1–§9 + Accessibility Notes). This spec is pixel-, token-, and icon-authoritative. Do not improvise UI it already specifies.
- **`batch-up-1-design.md`** — §D (endpoint contract), §G (decisions), §I (manifest)

### Critical rules for this batch

- **Rule 1.1 / 1.2 (verify endpoint, don't invent)**: `GET /api/v1/reports/wip` is confirmed in `openapi_schema_map.md`. All params/field names come from `openapi.json` (via `pnpm sync-api-types`) — never hand-typed.
- **Rule 1.3 (types)**: `WipReportResponse`, `WipReportRow`, `WipSummary` come from `@pilot/shared-types` after `pnpm sync-api-types`. Do NOT hand-write these interfaces.
- **Rule 2 (`apiClient`)**: All `/api/v1/...` calls use `apiClient` from `@pilot/shared-api`. `fetch()` is banned. `@/lib/api-client` does not exist.
- **Rule 7 (reuse)**: Compose `<PilotTable>`, `<LoadingState>`, `<ErrorState>`, `<EmptyState>`, `<RoleGate>`, `<NotificationBanner>` — all confirmed available. The **only** new component is `DeviationBadge` (spec §2.5 confirmed it's not in the `packages/ui` barrel).
- **Rule 9 (thin routes)**: `app/(authed)/reports/wip/page.tsx` is a thin server component — no `"use client"`, no data fetching. One line: `return <WipReportPage />;`.
- **Rule 10 (fix every failure)**: Any test failure — even seemingly pre-existing — must be fixed before done. If root cause is unclear → STOP and ask Tom.
- **Rule 11 (React Compiler)**: React 19.2 + compiler auto-memoizes. Do NOT hand-write `useMemo`/`useCallback`/`React.memo` for render-perf. Keep components pure.
- **Rule 12 (TanStack Query v5)**: Object-form only; `isPending` not `isLoading`; colocated query key including every `queryFn` variable (`status`/`sort`/`order`); `retry: false` (spec §5.2 — user controls retry via `<ErrorState>`).
- **Rule 14 (client-side fetch)**: WIP data is fetched client-side (`apiClient` + TanStack Query in `"use client"` feature components). Never fetch tenant data in a Server Component.
- **Rule 15 (WCAG 2.2 AA)**: axe-core zero violations. The spec's **Accessibility Notes** section is mandatory: color-independent `DeviationBadge` (icon+text+color), `aria-sort` on the active sort header, `scope="col"` headers, target sizes ≥24px, `focus-visible` rings, `prefers-reduced-motion` fallbacks for `animate-pulse`/`animate-spin`.

> **This is a READ-ONLY surface.** No mutations, no optimistic UI, no idempotency keys, no `<MessagePreviewModal>`, no SSE. See §9.4 of the spec: **WIP is fetch-on-load, NOT SSE** — do not wire an `EventSource`/`useSseChannel`. The only refresh is the manual Refresh button calling `query.refetch()`.

---

## Design Decisions (Do Not Re-Litigate)

From design doc §G + UI spec — these are final:

| Decision | Outcome | Rationale |
|---|---|---|
| WIP location | New full page at `/reports/wip` (not a dashboard widget) | Separate from date-range historical `/reports`; WIP is "now" + ETC |
| Dead `LiveJobsSection` | **Remove** it from `ProfitabilityPage`; replace with a pointer card to `/reports/wip`; delete `LiveJobsSection.tsx` + `LiveJobRow.tsx` + the `live_jobs` field/type in `useProfitability.ts` | Avoids two homes for "active jobs"; a permanently-empty section erodes trust (spec §1 Surface 3) |
| `DeviationBadge` | **New** domain component in `features/wip/components/` (4 variants: over/under/watch/none) | Confirmed not in `packages/ui` barrel (spec §2.5); composes four-class severity tokens |
| Refresh model | Manual Refresh button → `query.refetch()`. No SSE, no polling. | WIP is a snapshot computed on-request (design doc §F) |
| Status filter control | **Deferred** — default `status=scheduled,in_progress` covers full WIP scope (spec §6.6) | Low-value filter on a small row count |
| `watch` badge logic | Uses server `below_margin_target` boolean — badge does NOT re-derive margin client-side (spec §2.5, §9.6) | Server owns margin-target logic |
| Pagination | None for MVP (spec §9.2) | Active-job count is tens, not thousands |

---

## Pre-Work: Establish Regression Baseline

```bash
cd <repo>/frontend
pnpm --filter web test 2>&1 | tail -5
```

Record the exact counts — these must still pass at the end.

> **If any tests are already failing before you start**: do NOT treat them as "pre-existing" and proceed. Either (a) confirm with Tom it's a known accepted failure, OR (b) fix it before touching any batch files.

---

## Pre-Work: Sync API Types

```bash
cd <repo>/frontend
pnpm sync-api-types
```

This re-exports the live backend spec then regenerates `packages/shared-types/src/api-schema.d.ts`. Consume via the `components` root:

```typescript
import type { components } from "@pilot/shared-types";
type WipReportResponse = components["schemas"]["WipReportResponse"];
type WipReportRow = components["schemas"]["WipReportRow"];
type WipSummary = components["schemas"]["WipSummary"];
```

> Part A is live, so `sync-api-types` will deliver these types. If any of the three is missing after sync → STOP and ask Tom (do not hand-type them).

---

## Pre-Work: Verify Endpoints

Confirm before writing the hook:

```bash
grep -A 8 "reports/wip" backend/openapi_schema_map.md | head -30
```

Verified endpoints for this batch:

| Hook | Endpoint | Params | Verified |
|---|---|---|---|
| `useWipReport` | `GET /api/v1/reports/wip` | `status` (CSV, opt), `sort` (opt, default `deviation_pct`), `order` (opt, default `desc`) | ✅ Confirmed in `openapi_schema_map.md` (line ~16626) |

**Response** `WipReportResponse`: `{ report_type, generated_at, margin_target_pct, row_count, summary{active_job_count, total_actual_cost_cents, total_quoted_budget_cents, total_projected_cost_cents, jobs_over_budget_count, jobs_below_margin_target_count}, rows[] }`. Each row: `job_id, job_number, title, customer_name, site_name, status_code, scheduled_start_at, quoted_budget_cents, actual_cost_cents, etc_hours_remaining, etc_cost_cents, projected_cost_cents, projected_margin_pct, budget_deviation_pct, has_etc, below_margin_target`.

> The `openapi_schema_map.md` sample truncates the row fields at 8 for brevity — the **full** `WipReportRow` type from `pnpm sync-api-types` is authoritative. Nullable per contract: `title`, `customer_name`, `site_name`, `scheduled_start_at`, `quoted_budget_cents`, `etc_hours_remaining`, `projected_margin_pct`, `budget_deviation_pct`.

---

## Pre-Work: Read These Source Files

Read each with `read_file` before writing any code:

```
frontend/apps/web/src/features/profitability/components/ProfitabilityPage.tsx   ← Surface 3 reconciliation: remove LiveJobsSection, insert pointer card; also the layout shell to mirror (max-w, padding)
frontend/apps/web/src/features/profitability/components/LiveJobsSection.tsx      ← to be DELETED — confirm nothing else imports it
frontend/apps/web/src/features/profitability/components/LiveJobRow.tsx           ← to be DELETED — confirm only LiveJobsSection consumes it
frontend/apps/web/src/features/profitability/hooks/useProfitability.ts           ← remove live_jobs field (~line 192) + LiveJob type (~lines 58-69); confirm ProfitabilityResponse consumers don't read live_jobs
frontend/apps/web/src/features/dashboard/components/AtRiskJobsWidget.tsx          ← Surface 2: add WIP entry-point CTA in footer; mirror its formatCents + existing "View Jobs →" link pattern
frontend/apps/web/src/components/PilotTable.tsx                                   ← compose for the jobs table; understand sort handler, header render, whether it sets scope/aria-sort (spec §4 note + Accessibility Notes)
frontend/packages/ui/src/index.ts                                                ← confirm exact import paths for RoleGate, states (LoadingState/ErrorState/EmptyState), NotificationBanner; confirm DeviationBadge does NOT exist
frontend/apps/web/src/features/profitability/components/ProfitabilityPage.tsx     ← RoleGate usage pattern for reports (role vs permission prop shape)
frontend/apps/web/src/mocks/handlers/index.ts                                    ← how to register the new wipHandlers barrel entry (mandatory step)
frontend/apps/web/src/lib/                                                        ← check for an existing timestamp/currency util before writing new ones (spec §9.3, §9.5)
```

Also run:

```bash
# Confirm no other consumer of LiveJobsSection / live_jobs before deleting
grep -rn "LiveJobsSection\|LiveJobRow\|live_jobs\|LiveJob\b" frontend/apps/web/src

# Confirm shared component import paths
grep -n "RoleGate\|LoadingState\|ErrorState\|EmptyState\|NotificationBanner" frontend/packages/ui/src/index.ts

# Confirm DeviationBadge is NOT already present
grep -n "DeviationBadge" frontend/packages/ui/src/index.ts

# Existing MSW handler files + registration
find frontend/apps/web/src/mocks/handlers -name "*.ts" | head -20
cat frontend/apps/web/src/mocks/handlers/index.ts

# RoleGate prop shape for reports (role array vs permission key)
grep -rn "RoleGate" frontend/apps/web/src/features/profitability
```

> **RoleGate prop shape**: the UI spec uses `<RoleGate role={["owner","operator"]}>`. Verify the actual prop the codebase uses (`role` array vs `permission="reports.view"`) by reading `ProfitabilityPage.tsx` and `packages/ui/src/role-gate/`. **Match the existing `/reports` pattern exactly** — if `/reports` gates by `permission="reports.view"`, use that; do not introduce a different gating style. If the spec's `role`-array form conflicts with the codebase's `permission` form, follow the codebase and note it.

---

## Context: What This Batch Does

| # | Change | File(s) |
|---|---|---|
| 1 | `useWipReport` hook (TanStack Query v5, URL-synced sort) | `features/wip/hooks/useWipReport.ts` (new) |
| 2 | `DeviationBadge` (4 variants, icon+text+color) | `features/wip/components/DeviationBadge.tsx` (new) |
| 3 | `WipSummaryRow` (4 metric cards) | `features/wip/components/WipSummaryRow.tsx` (new) |
| 4 | `WipJobsTable` (compose PilotTable, sortable, URL-synced) | `features/wip/components/WipJobsTable.tsx` (new) |
| 5 | `WipSkeleton` (isPending state) | `features/wip/components/WipSkeleton.tsx` (new) |
| 6 | `WipReportPage` (RoleGate + state switching + header/Refresh) | `features/wip/components/WipReportPage.tsx` (new) |
| 7 | Thin route | `app/(authed)/reports/wip/page.tsx` (new) |
| 8 | Dashboard entry-point CTA | `features/dashboard/components/AtRiskJobsWidget.tsx` (edit) |
| 9 | Reconcile `/reports`: remove dead section + pointer card | `ProfitabilityPage.tsx` (edit), delete `LiveJobsSection.tsx`/`LiveJobRow.tsx`, `useProfitability.ts` (edit) |
| 10 | MSW handler + barrel registration | `mocks/handlers/wipHandlers.ts` (new) + `mocks/handlers/index.ts` (edit) |
| 11 | Nav reachability check | `AppSidebar.tsx` (verify; edit only if a Reports sub-menu exists — spec §8.2) |

---

## STEP 1 — `useWipReport` hook

Create `features/wip/hooks/useWipReport.ts`. Read the design spec §9.1–§9.2 first. Types from `@pilot/shared-types`; **adjust the shape below to the actual generated type** (starting point, not gospel):

```ts
"use client";
import { useQuery, keepPreviousData } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";
import type { components } from "@pilot/shared-types";

type WipReportResponse = components["schemas"]["WipReportResponse"];
export type WipSort = "deviation_pct" | "projected_margin_pct" | "actual_cost_cents" | "scheduled_start_at";

export interface UseWipReportOptions {
  status?: string;          // CSV; default "scheduled,in_progress"
  sort?: WipSort;           // default "deviation_pct"
  order?: "asc" | "desc";   // default "desc"
}

export const WIP_QUERY_KEY = (o: UseWipReportOptions) =>
  ["wip-report", o.status ?? "scheduled,in_progress", o.sort ?? "deviation_pct", o.order ?? "desc"] as const;

async function fetchWipReport(o: UseWipReportOptions): Promise<WipReportResponse> {
  const res = await apiClient.get("/api/v1/reports/wip", {
    params: { status: o.status, sort: o.sort, order: o.order },
  });
  return res.data;
}

export function useWipReport(options: UseWipReportOptions) {
  return useQuery({
    queryKey: WIP_QUERY_KEY(options),
    queryFn: () => fetchWipReport(options),
    retry: false,                  // spec §5.2 — user controls retry via <ErrorState>
    staleTime: 60_000,             // snapshot; don't refetch aggressively
    refetchOnWindowFocus: false,   // not a live surface
    placeholderData: keepPreviousData,  // keep table visible while re-sorting
  });
}
```

> Confirm `apiClient` params handling (axios `.data`) against a neighboring hook (e.g. `useProfitability.ts`). Do not hand-write `WipReportResponse`.

---

## STEP 2 — `DeviationBadge`

Create `features/wip/components/DeviationBadge.tsx`. Implement the 4 variants **exactly** per spec §2.5 (tokens, Heroicons, labels) and Accessibility Notes (icon `aria-hidden`, text carries meaning). Variant selection uses the row's `budget_deviation_pct` + `below_margin_target` (server-computed) + `margin_target_pct` — see spec §2.5 conditions. Do NOT re-derive margin logic beyond what the spec's condition table states.

Token-only colors (zero hex, spec §3). Icons from Heroicons per spec §4.

---

## STEP 3 — `WipSummaryRow`

Create `features/wip/components/WipSummaryRow.tsx`. 4 metric cards per spec §2.2 (Active Jobs / Over Budget / Below Margin Target / Projected vs Budget). Pure presentational — takes `summary: WipSummary` + `marginTargetPct`. Currency via the `formatCents` helper (spec §9.3 — reuse the app's existing util if present). Card 2 & 3 emotional-hook accents + icons + labels (color never the only signal).

---

## STEP 4 — `WipJobsTable`

Create `features/wip/components/WipJobsTable.tsx`. Compose `<PilotTable>` with TanStack column defs per spec §2.3 (9 columns, widths, right-aligned numerics, `tabular-nums`). Read `PilotTable.tsx` first to match its column-def + sort-handler API.

**Sort → URL sync** (spec §6.2, §9.2): use `next/navigation` `useSearchParams` + `useRouter` to read/write `?sort=&order=`. Clicking a sortable header updates the URL; the parent's `useWipReport` re-fires via query-key change. Only 3 columns are sortable in the UI (Deviation default, Margin, Actual Cost); `scheduled_start_at` is API-only (spec §6.2 note).

**Accessibility (spec Accessibility Notes)**: `aria-sort` on the active sort `<th>`; `scope="col"` on headers; Heroicons sort indicators (spec §4 — if PilotTable's built-in unicode glyph can't be suppressed without a fork, the unicode interim is acceptable; file a follow-up, do NOT fork PilotTable). Render `DeviationBadge` in the deviation column; nullable affordances per spec §2.6/§5.5.

---

## STEP 5 — `WipSkeleton`

Create `features/wip/components/WipSkeleton.tsx` matching spec §5.1 (4 skeleton cards + 8 skeleton table rows). `animate-pulse` with `motion-reduce:animate-none` (spec §7, §9.8).

---

## STEP 6 — `WipReportPage`

Create `features/wip/components/WipReportPage.tsx` (`"use client"`). Wrap in `<RoleGate>` (match `/reports` gating — see Pre-Work note). Owns:
- Header band + "as of {generated_at}" caption (spec §2.1, §9.5) + Refresh button (spec §6.1 → `query.refetch()`, disabled+spin while `isFetching && !isPending`).
- State switching: `isPending` → `<WipSkeleton>`; `isError` → `<ErrorState>` (severity/paywall routing per spec §5.2); `row_count === 0` → `<EmptyState>` (spec §5.3, summary row hidden); else → `<WipSummaryRow>` + `<WipJobsTable>`.
- Reads sort/order from URL (or lifts to pass into `useWipReport`).

Layout shell mirrors `ProfitabilityPage` (`max-w-6xl mx-auto`, `px-6 py-6`) per spec §1.

---

## STEP 7 — Thin route

Create `app/(authed)/reports/wip/page.tsx` (Rule 9 — thin server component):

```tsx
import { WipReportPage } from "@/features/wip/components/WipReportPage";
export default function Page() {
  return <WipReportPage />;
}
```

No `"use client"`, no data fetching, no logic. Verify import alias (`@/features/...`) matches the codebase.

---

## STEP 8 — Dashboard entry-point CTA

Edit `features/dashboard/components/AtRiskJobsWidget.tsx` — add the WIP CTA in the widget footer per spec §2.7 (`<Link href="/reports/wip">` "View full WIP report →" + sub-caption). No change to the widget's existing logic or RoleGate. Mirror the existing "View Jobs →" link pattern.

> Intermediate check after this edit (touches a dashboard component many tests may render):
> ```bash
> pnpm --filter web test -- apps/web/src/features/dashboard 2>&1 | tail -10
> ```

---

## STEP 9 — Reconcile `/reports` (Surface 3)

Per spec §1 Surface 3 + §5.7 + §8.2/§8.3:
1. `ProfitabilityPage.tsx`: remove the `LiveJobsSection` import + render; insert the WIP pointer card (spec §5.7) between `MetricsCardRow` and `ClosedJobsSection`.
2. Delete `LiveJobsSection.tsx` and `LiveJobRow.tsx` (confirm via the Step-0 grep that nothing else imports them).
3. `useProfitability.ts`: remove the `live_jobs: []` field + `LiveJob` type; update `ProfitabilityResponse` so no consumer reads `live_jobs` (the grep confirms consumers).

> Intermediate check (touches profitability tests):
> ```bash
> pnpm --filter web test -- apps/web/src/features/profitability 2>&1 | tail -10
> ```

---

## STEP 10 — MSW handler + registration

Create `mocks/handlers/wipHandlers.ts` covering the fixtures in spec §9.7 (happy 12-row mixed; empty `row_count:0`; 422; 402 paywall; one-each over/watch/under/none deviation rows). Then **register in the barrel** (mandatory):

```typescript
// mocks/handlers/index.ts
import { wipHandlers } from "./wipHandlers";
export const handlers = [ ...existing, ...wipHandlers ]; // ← without this line the handler never loads
```

Check `index.ts` first — never duplicate an existing `http.get` for the path.

---

## STEP 11 — Nav reachability (verify)

Read `AppSidebar.tsx`. If it only links to `/reports` (no Reports sub-menu), no change is needed — `/reports/wip` is reachable via the dashboard CTA + the `/reports` pointer card (spec §8.2). If a Reports sub-menu exists, add a "WIP" entry matching the existing item pattern.

---

## Test Requirements

Use Vitest + `@testing-library/react`. Fresh `QueryClient` per test with `retry: false` (both queries + mutations). MSW at the HTTP level — never mock `apiClient`. Mock `next/navigation` (`useSearchParams`, `useRouter`, `usePathname`) and `next/link` in component tests (inclusion §8.1). Reset MSW handlers in `afterEach`.

**Unit tests (co-located `features/wip/components/__tests__/` and `features/wip/hooks/__tests__/`):**
- `useWipReport`: returns shape with mock response; error state on 500; **query key includes `status`/`sort`/`order`** (assert key composition).
- `DeviationBadge`: each of the 4 variants renders the correct icon + text label (assert by text/`data-testid`, not color) — the color-independence proof.
- `WipSummaryRow`: renders the 4 metric values from a mock `summary`.
- `WipJobsTable`: renders rows; nullable affordances (`—` for no-quote, "No ETC" for `has_etc:false`); clicking a sortable header updates the URL sort param (assert `router.push`/`replace` called with the expected query).
- `WipReportPage`: renders `<WipSkeleton>` while pending; `<ErrorState>` on failure; `<EmptyState>` when `row_count:0`; RBAC — unauthorized role does NOT see content (use `AuthContext.Provider` pattern, inclusion §9).

**Integration test (`apps/web/src/__tests__/batch_up_1/wip-report.integration.test.tsx`):**
1. `/reports/wip` route renders (not 404) with MSW happy-path data.
2. RBAC: authorized role (owner/operator) sees the table; unauthorized role does not.
3. Populated table shows a specific job by `job_number`/content (assert by content, NOT row count — MSW fixture is the source).
4. Sort interaction fires the correct URL param change; the refetched query uses the new `sort`/`order`.
5. Empty state renders with the `row_count:0` fixture.
6. Error/paywall state renders `<ErrorState>` with the 402 fixture.

> Assert by specific IDs/content from the MSW fixture — never `toHaveLength(N)` on the row list (inclusion §9 resilience rule).

---

## Final Verification

> ❌ **BANNED**: `npx vitest run` — bypasses the workspace and breaks module resolution. Only `pnpm --filter web test`.

### Phase 1 — Targeted (during development)
```bash
cd <repo>/frontend
pnpm --filter web test -- apps/web/src/features/wip 2>&1 | tail -10
pnpm --filter web test -- apps/web/src/__tests__/batch_up_1/ 2>&1 | tail -10
```

### Phase 2 — Full verification (once, before DoD sign-off)
```bash
cd <repo>/frontend && echo "=== UI - Type Check ===" && pnpm --filter @pilot/ui check-types && echo "=== Web - Type Check ===" && pnpm --filter web check-types && echo "=== Mobile - Type Check ===" && pnpm --filter mobile build && echo "=== UI - Lint ===" && pnpm --filter @pilot/ui lint && echo "=== Web - Lint ===" && pnpm --filter web lint && echo "=== Mobile - Lint ===" && pnpm --filter mobile lint && echo "=== TYPE+LINT PASS ===" && echo "=== UI - Tests ===" && pnpm --filter @pilot/ui test 2>&1 | tail -6 && echo "=== Web - Tests ===" && pnpm --filter web test 2>&1 | tail -6 && echo "=== Mobile - Tests ===" && pnpm --filter mobile test 2>&1 | tail -8 && echo "=== MVP FINAL VERIFICATION COMPLETE ==="
```

> Any failure in either phase must be fixed before done — no "pre-existing" exception without Tom's written confirmation.

---

## Definition of Done — UP-1 Part B

- [ ] Regression baseline captured (zero pre-existing web failures, or confirmed with Tom)
- [ ] `pnpm sync-api-types` run — `WipReportResponse`/`WipReportRow`/`WipSummary` resolve from `@pilot/shared-types`; no new type errors
- [ ] UI design spec + design doc fully read before coding
- [ ] `GET /api/v1/reports/wip` verified in `openapi_schema_map.md`
- [ ] All mandatory source files read; `LiveJobsSection`/`live_jobs` consumers grep'd before deletion
- [ ] **STEP 1** `useWipReport` — v5 object-form, `retry:false`, query key incl. `status`/`sort`/`order`
- [ ] **STEP 2** `DeviationBadge` — 4 variants, icon+text+color (color-independent)
- [ ] **STEP 3** `WipSummaryRow` — 4 cards per spec §2.2
- [ ] **STEP 4** `WipJobsTable` — composes `<PilotTable>`, URL-synced sort, `aria-sort` + `scope="col"`, nullable affordances
- [ ] **STEP 5** `WipSkeleton` — `motion-reduce` fallback
- [ ] **STEP 6** `WipReportPage` — RoleGate + 4 data states + Refresh
- [ ] **STEP 7** thin route `app/(authed)/reports/wip/page.tsx` (no `"use client"`)
- [ ] **STEP 8** dashboard CTA added to `AtRiskJobsWidget` (no widget-logic change)
- [ ] **STEP 9** `/reports` reconciled: `LiveJobsSection`/`LiveJobRow` deleted, pointer card added, `live_jobs`/`LiveJob` removed from `useProfitability.ts`
- [ ] **STEP 10** `wipHandlers.ts` created AND registered in `mocks/handlers/index.ts`
- [ ] **STEP 11** nav reachability verified (`AppSidebar` edited only if a Reports sub-menu exists)
- [ ] No SSE/`EventSource` wired (spec §9.4); no hand-written memoization (Rule 11)
- [ ] axe-core zero violations + WCAG spot-checks (target ≥24px, focus-visible, `aria-sort`, `prefers-reduced-motion`, color-independent badges)
- [ ] Unit tests pass (targeted run)
- [ ] Integration tests pass in `__tests__/batch_up_1/`
- [ ] **Phase 2 FULL verification passes** (`=== MVP FINAL VERIFICATION COMPLETE ===`):
  ```bash
  cd <repo>/frontend && echo "=== UI - Type Check ===" && pnpm --filter @pilot/ui check-types && echo "=== Web - Type Check ===" && pnpm --filter web check-types && echo "=== Mobile - Type Check ===" && pnpm --filter mobile build && echo "=== UI - Lint ===" && pnpm --filter @pilot/ui lint && echo "=== Web - Lint ===" && pnpm --filter web lint && echo "=== Mobile - Lint ===" && pnpm --filter mobile lint && echo "=== TYPE+LINT PASS ===" && echo "=== UI - Tests ===" && pnpm --filter @pilot/ui test 2>&1 | tail -6 && echo "=== Web - Tests ===" && pnpm --filter web test 2>&1 | tail -6 && echo "=== Mobile - Tests ===" && pnpm --filter mobile test 2>&1 | tail -8 && echo "=== MVP FINAL VERIFICATION COMPLETE ==="
  ```
- [ ] Final test count (before → after) documented
- [ ] Completion Summary added to the launch plan §2.3 UP-1 card

---

## Completion Summary

After all DoD items are complete, add a Completion Summary to `pilot-launch-plan.md` §2.3 UP-1:

```markdown
### UP-1 (Part B) — WIP Report Page (Web): Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot React Engineer
**Baseline**: X passed (web)
**Final**: X+N passed (+N new tests)

#### What Was Accomplished
- New `/reports/wip` page: summary metric row + sortable active-jobs table with ETC-projected cost, deviation %, and margin %, consuming `GET /api/v1/reports/wip`.
- New `DeviationBadge` (4 variants, color-independent); dashboard entry-point CTA in `AtRiskJobsWidget`.
- Reconciled the dead `LiveJobsSection` on `/reports` (removed + pointer card; deleted `LiveJobsSection`/`LiveJobRow`; removed `live_jobs` from `useProfitability`).

#### Files Changed / Created
| File | Action |
|---|---|
| `features/wip/hooks/useWipReport.ts` | Created |
| `features/wip/components/{WipReportPage,WipSummaryRow,WipJobsTable,DeviationBadge,WipSkeleton}.tsx` | Created |
| `app/(authed)/reports/wip/page.tsx` | Created — thin route |
| `features/dashboard/components/AtRiskJobsWidget.tsx` | Updated — WIP CTA |
| `features/profitability/components/ProfitabilityPage.tsx` | Updated — pointer card, removed LiveJobsSection |
| `features/profitability/components/{LiveJobsSection,LiveJobRow}.tsx` | Deleted — dead code |
| `features/profitability/hooks/useProfitability.ts` | Updated — removed live_jobs/LiveJob |
| `mocks/handlers/wipHandlers.ts` (+ index.ts) | Created + registered |

#### Tests Added
| Test File | Type | Tests | All Pass |
|---|---|---|---|
| `__tests__/batch_up_1/wip-report.integration.test.tsx` | Integration | N | ✅ |
| `features/wip/**/__tests__/*.test.tsx` | Unit | N | ✅ |
```

This closes UP-1 (both halves). No mobile work in this batch.
