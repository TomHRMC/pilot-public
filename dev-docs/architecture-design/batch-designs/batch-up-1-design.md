# Batch UP-1 — Work-In-Progress (WIP) Report Page

**Version**: 1.0
**Date**: 2026-07-29
**Author**: Pilot Architect
**Batch type**: Mixed (Backend Python first → Frontend React)
**Priority / Phase**: P1 / Beta (§2.3 UI push)
**Plan link**: `pilot-launch-plan.md §2.3 UP-1`
**Frontend companion**: `batch-up-1-react-engr-prompt.md` (authored after Part A closes + `pnpm sync-api-types`)
**UI design spec** (Rule 1.5 gate): `batch-up-1-ui-design-spec.md` (pilot-web-ui-designer → Tom approval **before** the React prompt)

> **Scope note (recalibrated 2026-07-29)**: The original UP-1 card listed four items (WIP dashboard, appointment reminders UI, background-sync settings UI, communication templates UI). A design-time audit found **background-sync settings UI is already built** (`/settings/sync-storage/background-sync`), and **templates + reminders** are either preview-only or undiscovered — both moved to **Phase 1.5**. Tom confirmed UP-1 = **WIP report page only**. This doc covers that single deliverable.

---

## A. Input Read Summary

| Input | Section(s) read | What it told us |
|---|---|---|
| `mvp-prd.md` | §3.4 (Real-Time Job Costing, ETC Capture, Live Job Profitability View); line 1000 (WIP dashboard = P1 MVP item) | WIP's differentiator is **ETC-projected cost** (actuals + estimate-to-complete vs quoted budget), not just actuals. Margin target default 20%; buckets `[10,20,30]`. |
| Live DB via `postgres-local` MCP | `job`, `job_time_entry` columns | `job.actual_labor_cost_cents`, `actual_material_cost_cents`, `actual_profit_cents` (NOT NULL); budget = `quote.total_cents` (no budget column). ETC on `job_time_entry.hours_remaining_estimate` (numeric) + `hourly_rate_cents` + `etc_captured_at`. Job status via `job_status.code`. |
| `dashboard.py` `_get_at_risk_jobs_impl` | full impl | Existing at-risk endpoint = below-target subset, actuals-only, top-N. Reusable margin/quote pattern; **not** a superset and has **no ETC**. |
| `report_service.py` `get_profitability_report` | full SQL | Proven budget-vs-actual aggregation (`quote.total_cents` denominator, margin bucket classification, `get_margin_settings`). WIP reuses this shape but per-active-job + ETC. |
| `reports.py` | endpoint conventions | Report endpoints: dual `/test` twins, `reports.view` RBAC, `ReportEnvelope` response wrapper, `display_mode`/`report_chart_threshold`. |
| `ProfitabilityPage.tsx` + `useProfitability.ts` | full | `/reports` has a `LiveJobsSection`, but the adapter hardcodes **`live_jobs: []`** (`useProfitability.ts`) — the "active jobs" table is **permanently empty**. No ETC anywhere in the FE. **This is the real gap UP-1 closes.** |
| `ADR-0005`, `ADR-0007` | tenant-scoped select; OpenAPI contract | Read-only report is tenant-scoped by `tenant_id` in the query; FE types via `pnpm sync-api-types`. |

**Key finding**: UP-1 is **not** "the dashboard has no BI" (AR aging, at-risk, pending-approvals widgets already exist). It is the **one concrete gap**: a full, populated **active-jobs WIP report with ETC-projected margin** — replacing the permanently-empty `LiveJobsSection`.

---

## B. Migration Plan

**No migration.** MCP-verified: every field the WIP report needs already exists.

| Data needed | Source (MCP-verified) |
|---|---|
| Actual labor/material cost | `job.actual_labor_cost_cents`, `job.actual_material_cost_cents` (NOT NULL int) |
| Quoted budget | `quote.total_cents` via `job.quote_id` (LEFT JOIN; may be null) |
| ETC hours remaining | `job_time_entry.hours_remaining_estimate` (numeric, nullable) — **latest per job** by `etc_captured_at` |
| ETC labor rate | `job_time_entry.hourly_rate_cents` (int) |
| Active status filter | `job_status.code IN ('scheduled','in_progress')` |
| Margin target / buckets | `get_margin_settings()` / `get_effective_setting('margin_target_pct', 20)` |

**MCP verification queries (Python Engineer must re-run before writing SQL, Rule 3):**
```sql
SELECT column_name, data_type, is_nullable FROM information_schema.columns
WHERE table_schema='public' AND table_name='job' ORDER BY ordinal_position;
SELECT column_name, data_type, is_nullable FROM information_schema.columns
WHERE table_schema='public' AND table_name='job_time_entry' ORDER BY ordinal_position;
SELECT code FROM job_status WHERE tenant_id IS NULL OR tenant_id = :tid;  -- confirm active codes
```

**Pre-migration state**: N/A (no schema change).

---

## C. Execution Order

| # | Step | Owner | Notes |
|---|---|---|---|
| 1 | MCP re-verify `job` + `job_time_entry` + `job_status.code` | Python | Rule 3 gate before any SQL |
| 2 | Add `wip_service.compute_wip_report()` | Python | ETC projection logic (§F) |
| 3 | Add `WipReportRow` + `WipReportResponse` schemas | Python | §D |
| 4 | Add `GET /api/v1/reports/wip` + `/test` twin | Python | `reports.view` RBAC |
| 5 | Unit tests (service + endpoint, ETC math, tenant isolation) | Python | §G coverage map |
| 6 | Regenerate OpenAPI + `openapi_schema_map.md`; commit; notify FE | Python | Handoff |
| 7 | `pnpm sync-api-types` | React | First FE Pre-Work step |
| 8 | `useWipReport` hook | React | §D contract |
| 9 | WIP components (§I manifest) + `/reports/wip` route | React | Per UI design spec |
| 10 | Dashboard entry point (link/CTA to WIP) | React | Compose, not new widget |
| 11 | MSW handler + tests | React | §G |

---

## D. New API Endpoint

### `GET /api/v1/reports/wip`

- **Auth**: JWT + `require_permission("reports.view")` (matches all report endpoints). Dual `/test` twin registered FIRST (§8.2).
- **RBAC surface (FE)**: RoleGate `owner | operator` (same as `/reports`).
- **Query params**:
  - `status` *(optional)* — CSV of `job_status.code`; default `scheduled,in_progress`.
  - `sort` *(optional)* — `deviation_pct` (default) | `projected_margin_pct` | `actual_cost_cents` | `scheduled_start_at`.
  - `order` *(optional)* — `asc` | `desc` (default `desc` for deviation — worst first).
- **Response** (`WipReportResponse`, extends `ReportEnvelope` conventions but no date range — WIP is "now"):

```jsonc
{
  "report_type": "wip",
  "generated_at": "2026-07-29T14:00:00Z",
  "margin_target_pct": 20.0,
  "row_count": 12,
  "summary": {
    "active_job_count": 12,
    "total_actual_cost_cents": 480000,
    "total_quoted_budget_cents": 720000,
    "total_projected_cost_cents": 610000,
    "jobs_over_budget_count": 3,
    "jobs_below_margin_target_count": 4
  },
  "rows": [
    {
      "job_id": "…",
      "job_number": "JOB-000123",
      "title": "Panel upgrade",
      "customer_name": "Apex Commercial LLC",
      "site_name": "North Warehouse",
      "status_code": "in_progress",
      "scheduled_start_at": "2026-07-20T13:00:00Z",
      "quoted_budget_cents": 60000,
      "actual_cost_cents": 42000,
      "etc_hours_remaining": 6.5,
      "etc_cost_cents": 13000,
      "projected_cost_cents": 55000,
      "projected_margin_pct": 8.33,
      "budget_deviation_pct": -8.33,
      "has_etc": true,
      "below_margin_target": true
    }
  ]
}
```

- **Error codes**: 401 (no JWT), 402 (paywall via entitlement middleware), 422 (invalid `sort`/`status` value → RFC 7807).
- **Not paginated for MVP**: active-job count per tenant is small (tens, not thousands); return all rows sorted. If a tenant ever exceeds ~200 active jobs, add `limit`/`offset` (flag, don't pre-build — Rule: no premature scaling).

---

## E. Pattern Reuse Decisions (`mvp-arch.md §16`)

| Pattern | Applies? | How |
|---|---|---|
| Tenant-scoped `select()` (ADR-0005) | ✅ | All queries `WHERE job.tenant_id = :tid`; read-only; no `db.get()`. |
| OpenAPI contract (ADR-0007) | ✅ | Regenerate after Part A; FE runs `pnpm sync-api-types`. |
| Optimistic UI / confirm-as-turn / 409-refresh | ❌ | WIP is **read-only** — no mutations, no optimistic UI, no idempotency key. |
| `display_mode`/`report_chart_threshold` | ➖ Partial | WIP is a table-first surface; no chart threshold needed for MVP. Reuse `ReportEnvelope` fields only where meaningful (`row_count`, `generated_at`). |
| Money = integer cents | ✅ | All `_cents` fields int; FE ÷100 for display. Never float for money. |
| `get_margin_settings` / `get_effective_setting` | ✅ | Reuse existing margin-target/bucket resolution — do **not** re-implement. |

---

## F. Shared Module Interfaces

### `backend/services/wip_service.py` (new)

```python
def compute_wip_report(
    db: Session,
    tenant_id: UUID,
    status_codes: list[str] | None = None,   # default ['scheduled','in_progress']
    sort: str = "deviation_pct",
    order: str = "desc",
) -> WipReportData:
    """
    For each active job:
      actual_cost      = actual_labor_cost_cents + actual_material_cost_cents
      etc_cost         = round(latest_etc_hours_remaining * etc_hourly_rate_cents)   # Decimal, ROUND_HALF_UP
      projected_cost   = actual_cost + etc_cost
      budget           = quote.total_cents (via job.quote_id; None if no quote)
      projected_margin = (budget - projected_cost) / budget * 100    # None if budget is None/0
      deviation_pct    = (budget - projected_cost) / budget * 100    # negative = over-budget risk
      has_etc          = latest_etc row exists with non-null hours_remaining_estimate
    Rules:
      - "latest ETC" = job_time_entry for the job with MAX(etc_captured_at) and non-null
        hours_remaining_estimate; if none, etc_cost = 0 and has_etc = False (projected = actual).
      - Money via Decimal + ROUND_HALF_UP; never float arithmetic on cents.
      - Jobs with no quote: budget/margin/deviation = None; still listed (actual_cost shown).
      - Tenant-scoped throughout; batch-load ETC (one grouped query, no N+1).
    """
```

**ETC "latest per job" query approach** (anti-N+1): one grouped subquery selecting the `hours_remaining_estimate` + `hourly_rate_cents` from the `job_time_entry` row with `MAX(etc_captured_at)` per `job_id`, joined to the active-job set. Mirror the batched-lookup pattern from `_dispatch_board_impl` (DISPATCH-B1) rather than per-job queries.

**No Celery / no scheduled task** — WIP is computed on-request from already-rolled-up columns (`actual_*` are maintained by the existing `profitability_rollup` task; UP-1 does not touch that task).

---

## G. Open Questions Resolved

| Q | Resolution |
|---|---|
| Is WIP a new page or a dashboard widget? | **New full page** at `/reports/wip` + a dashboard **entry point** (link/CTA), per Tom. Not a 5-row card (that's the existing at-risk widget). |
| Reuse `/reports` ProfitabilityPage? | **No** — that page is date-range historical (profitability by closed jobs). WIP is "now / active jobs" and needs ETC. Separate route. But **fix the dead `LiveJobsSection`**: either wire it to `/wip` data or remove it (decide in UI spec — recommend removing the empty section from ProfitabilityPage and pointing to the new WIP page to avoid two homes for "active jobs"). |
| ETC when a job has multiple time entries? | Use the **latest** ETC by `etc_captured_at` (most recent tech estimate). Documented in §F. |
| ETC when no time entries / no ETC captured? | `has_etc=false`, `etc_cost=0`, `projected_cost=actual_cost`. Row still shown. |
| Job with no linked quote? | Listed with `budget/margin/deviation = null`; UI shows "—" and a "no quote" affordance. Matches at-risk endpoint behavior. |
| Deviation sign convention | `budget_deviation_pct` negative = projected over budget (bad). UI colors + icon (non-color-only, WCAG 1.4.1). |
| Does this touch the `profitability_rollup` Celery task? | **No.** Reads existing `actual_*` columns. |
| Paywall? | Yes — inherits `reports.view` + entitlement middleware (402 if `is_billing_active=false`). |

---

## H. Surface Mockup Reference *(frontend)*

- **Design spec** (Rule 1.5): `batch-up-1-ui-design-spec.md` — authored by **`pilot-web-ui-designer`**, Tom-approved **before** the React prompt. Must be token-only, WCAG 2.2 AA (color-independent over/under-budget status via icon+text, ≥24px targets, `focus-visible`, `prefers-reduced-motion`).
- **Platform scope**: web dashboard only (`apps/web`). No mobile.
- **§16 pattern consumption**: none new — table + sort composes existing `PilotTable`; status/deviation badges compose the four-class severity styling already in `packages/ui`. Designer must confirm no new top-level pattern.
- **Surfaces**:
  1. `/reports/wip` — full page: header + summary metric row + sortable active-jobs table (job, customer/site, status, budget, actual, ETC, projected, deviation%, margin%).
  2. Dashboard entry point — a link/CTA (e.g. on/near the existing `AtRiskJobsWidget`) to "View full WIP report". Compose, do not duplicate.
  3. Reconcile the dead `LiveJobsSection` on `/reports` (remove or redirect — per spec decision in §G).

---

## I. Component Manifest *(frontend)*

| Component | Path (destination) | New? | Notes |
|---|---|---|---|
| `useWipReport` hook | `features/wip/hooks/useWipReport.ts` | New | TanStack Query v5; `retry:false`; query key includes `status`/`sort`/`order`; types from `@pilot/shared-types`. |
| `WipReportPage` | `features/wip/components/WipReportPage.tsx` | New | RoleGate `owner\|operator`; loading/error/empty states; composes summary + table. |
| `WipSummaryRow` | `features/wip/components/WipSummaryRow.tsx` | New | Metric cards (active count, over-budget count, below-target count). |
| `WipJobsTable` | `features/wip/components/WipJobsTable.tsx` | New | `PilotTable`-based, sortable columns; deviation badge (icon+text+color). |
| `DeviationBadge` | `features/wip/components/DeviationBadge.tsx` | New | Over/under/on-budget — WCAG 1.4.1 (icon + text, not color-only). Check `packages/ui/src/index.ts` first — reuse severity styling if a badge primitive exists. |
| thin route | `app/(authed)/reports/wip/page.tsx` | New | Rule 9 thin server component → `WipReportPage`. |
| MSW handler | `mocks/handlers/wipHandlers.ts` (+ barrel `index.ts`) | New | `/reports/wip` happy path + empty + 422; varied ETC/no-ETC/no-quote fixtures. |
| Dashboard entry point | edit `AtRiskJobsWidget.tsx` or `dashboard/page.tsx` | Edit | Add "View full WIP report" link. No new widget. |

**Component-existence check**: Python Engineer/React Engineer must confirm against `packages/ui/src/index.ts` that `DeviationBadge`/severity badge isn't already provided before creating a new one (Rule 1.5.4).

---

## Definition of Done (design-level)

- Part A: `GET /reports/wip` + `/test` returns MCP-accurate data; ETC math via Decimal; tenant-scoped; +unit tests (ETC present/absent, no-quote, over-budget, sort, tenant isolation); OpenAPI regenerated.
- Part B: `/reports/wip` page populated from real endpoint; dead `LiveJobsSection` reconciled; dashboard entry point added; MSW + tests; `pnpm sync-api-types` run first.
- Rule 1.5: UI design spec exists + Tom-approved before the React prompt is authored.

---

*Authored by Pilot Architect. Part A (Python) prompt to follow using `python-engr-std-prompt-inclusions.md`; Part B (React) prompt gated on the Tom-approved UI design spec (Rule 1.5).*
