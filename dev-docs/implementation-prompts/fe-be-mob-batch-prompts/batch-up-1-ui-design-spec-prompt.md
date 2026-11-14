# Design Commissioning Prompt: UP-1 — WIP Report Page UI Design Spec

**Mode**: Pilot Web UI Designer (`pilot-web-ui-designer`)
**Batch**: UP-1 — Part B design spec (precedes the React Engineer prompt, Rule 1.5)
**Source design doc**: `dev-docs/architecture-design/batch-designs/batch-up-1-design.md` — §D (endpoint contract), §H (surface scope), §I (component manifest)
**Backend companion**: `batch-up-1-python-engr-prompt.md` (Part A — builds `GET /api/v1/reports/wip`)
**Deliverable**: `dev-docs/architecture-design/batch-designs/batch-up-1-ui-design-spec.md`
**Handoff gate**: STOP after the spec. Tom approves before any React work begins.

---

## What You Are Designing

A new full-page **Work-In-Progress (WIP) report** for the web dashboard at **`/reports/wip`**, plus a **dashboard entry point** to reach it, plus a decision on the **dead `LiveJobsSection`** currently on `/reports`.

The WIP report answers one question for an owner/operator: *"For every job I'm actively working right now, am I on track to hit my quoted budget — accounting for the work still remaining (ETC)?"* This is the product's real-time job-costing differentiator; today the "active jobs" table on `/reports` is permanently empty.

**This is a read-only, table-first surface.** No mutations, no create/edit forms, no optimistic UI, no idempotency concerns. Your job is a clear, scannable, accessible data page.

---

## Mandatory Pre-Work (read before designing — §2 of your standards)

Use `read_file` on each:

1. `frontend/apps/web/src/features/profitability/components/ProfitabilityPage.tsx` — the existing `/reports` page that contains the dead `LiveJobsSection` you must reconcile. Understand its layout so the new WIP page is visually consistent.
2. `frontend/apps/web/src/features/profitability/hooks/useProfitability.ts` — see the hardcoded `live_jobs: []` (lines ~127, ~192) that makes the section permanently empty.
3. `frontend/apps/web/src/app/(authed)/dashboard/page.tsx` and the `AtRiskJobsWidget` it renders — the WIP entry point lives on/near this widget. Do **not** design a new dashboard widget; design an entry point (link/CTA) that composes into what exists.
4. `frontend/packages/ui/src/index.ts` — the authoritative barrel of shared components. **A component does not exist until it appears here.** Confirm before proposing anything new.
5. `frontend/apps/web/src/components/PilotTable.tsx` — the data table you will compose for the jobs list.
6. `.roo/rules-pilot-web-ui-designer/pilot-design-system-reference.md` — §3 status badges (the four-class severity styling you must reuse for the deviation badge; do NOT invent a new one).

---

## The Data You Are Designing Around (endpoint contract — Part A)

`GET /api/v1/reports/wip` returns (per design doc §D). Every field below is what the page renders — money fields are **integer cents** (divide by 100 for USD display, §12 of your standards):

**Top-level**: `report_type`, `generated_at` (timestamp — show as "as of {time}"), `margin_target_pct` (e.g. `20.0`), `row_count`.

**`summary`** (for the metric row at the top of the page):
- `active_job_count`
- `total_actual_cost_cents`
- `total_quoted_budget_cents`
- `total_projected_cost_cents`
- `jobs_over_budget_count`
- `jobs_below_margin_target_count`

**`rows[]`** (each active job, for the table):
- `job_number`, `title`, `customer_name` (nullable), `site_name` (nullable), `status_code` (`scheduled` | `in_progress`), `scheduled_start_at` (nullable)
- `quoted_budget_cents` (**nullable** — job may have no quote)
- `actual_cost_cents`
- `etc_hours_remaining` (nullable float), `etc_cost_cents`, `projected_cost_cents`
- `projected_margin_pct` (nullable), `budget_deviation_pct` (**nullable; negative = projected over budget = bad**)
- `has_etc` (bool), `below_margin_target` (bool)

**Query params the UI controls** (design the sort affordance around these):
- `sort` ∈ `deviation_pct` (default) | `projected_margin_pct` | `actual_cost_cents` | `scheduled_start_at`
- `order` ∈ `asc` | `desc` (default `desc` — worst deviation first)
- `status` — CSV; default `scheduled,in_progress`. **Optional**: you may spec a simple status filter (e.g. a segmented control for All / Scheduled / In-Progress), or defer it. If you defer, state that explicitly.

---

## Required Surfaces

### 1. `/reports/wip` — full page (RBAC: `owner | operator`)

- **Header**: page H1 + an "as of {generated_at}" caption. This is a live-ish snapshot; there is **no date range picker** (unlike the other reports — WIP is "now").
- **Summary metric row**: metric cards for at least `active_job_count`, `jobs_over_budget_count`, `jobs_below_margin_target_count`, and the budget-vs-projected totals. Decide the card grouping and spec it. The "over budget" and "below target" counts are the emotional hook — give them appropriate visual weight (compose the severity tokens; color is never the only signal — pair with label/icon).
- **Jobs table** (compose `<PilotTable>`): columns — Job (number + title), Customer / Site, Status, Quoted Budget, Actual Cost, ETC (hours + $), Projected Cost, **Deviation %**, **Margin %**. Sortable on the four `sort` values. Spec the sort interaction (clickable header → toggles `order`; indicate active sort column + direction with a Heroicon).
- **Deviation badge**: reuse the four-class severity styling from the design-system reference §3 (compose `<DeviationBadge>` per §I of the design doc only if no severity primitive already exists in the barrel — check first, Rule 6). Over-budget (negative deviation) must be conveyed by **icon + text + color**, never color alone (WCAG 1.4.1).
- **Nullable-field affordances**: jobs with **no quote** show `—` for budget/margin/deviation with a subtle "no quote" affordance; jobs with **no ETC** (`has_etc=false`) show that projected = actual (spec how you visually indicate "no estimate-to-complete captured yet" — e.g., a muted ETC cell).

### 2. Dashboard entry point (compose — do NOT add a new widget)

A link/CTA on or adjacent to the existing `AtRiskJobsWidget` — e.g. "View full WIP report →" routing to `/reports/wip`. Spec placement, label, icon, and all five interaction states. It must read as an extension of the existing at-risk widget, not a competing widget.

### 3. Reconcile the dead `LiveJobsSection` on `/reports`

Per design doc §G, make a recommendation and spec it: **either** remove the empty `LiveJobsSection` from `ProfitabilityPage` and replace it with a small pointer/CTA to the new `/reports/wip` page (**recommended** — avoids two homes for "active jobs"), **or** wire it to the WIP data as a compact preview. Pick one, justify it in one line, and spec the resulting `/reports` change.

---

## Required Data States (§8.5 + §12 — all four, every surface)

- **`isPending`**: skeleton matching the summary-row + table layout (skeletons over spinners for content-shaped loading, §11).
- **`isError`**: `<ErrorState>` with retry (severity-routed from RFC 7807 — the endpoint returns 422 on bad params, 402 on paywall).
- **Empty** (`row_count === 0`): `<EmptyState>` / `<FirstTimeUserState>` — "No active jobs right now." Spec the copy and any CTA (e.g. link to create/schedule a job). This is the common state for a brand-new founder tenant.
- **Populated**: the full table + summary.

> **"Overdue" is not a status** (§12) — do not spec an overdue badge. Job status here is only `scheduled` / `in_progress`. Budget risk is derived (deviation %), not a status.

---

## Spec Output Requirements (your §8 output format — all 9 sections + Accessibility Notes)

Produce `dev-docs/architecture-design/batch-designs/batch-up-1-ui-design-spec.md` containing:

1. **Surface overview** — the three surfaces above, routes, RBAC (`owner | operator`).
2. **Pixel specs** — dimensions, padding (`px-6 py-6` standard), gaps, border-radius for the summary cards, table, badges, and entry-point CTA. Desktop-first at **1280px**; note 1024px/768px table reflow (§4, §12).
3. **Token-only colors** — zero hex. Use `pilotPreset` tokens (over-budget → `fault` family; healthy margin → `margin` family; below-target-but-positive → `alert` family; neutrals per §3 of your standards). If you invent any new token pairing, state its contrast ratio.
4. **Icon inventory** — exact Heroicons names (e.g. sort indicator, deviation up/down arrows, "no quote" affordance). 16px (`w-4 h-4`) inline/table; 20px (`w-5 h-5`) nav-level.
5. **State coverage** — the four data states above, plus per-row nullable states (no quote / no ETC).
6. **Interaction spec** — all five states (default / hover / focus-visible / active / disabled) for sortable headers, the entry-point CTA, and any status filter control. `focus-visible:ring-2 focus-visible:ring-brand-500`.
7. **Animation spec** — any sort transition / skeleton shimmer with a `prefers-reduced-motion` fallback (§11).
8. **Component manifest** — reconcile **exactly** against design doc §I. Every file the React Engineer will create/modify with its path (`features/wip/components/...`, `app/(authed)/reports/wip/page.tsx`, dashboard entry-point edit, `ProfitabilityPage.tsx` reconciliation). Confirm each new component does not already exist in the `packages/ui` barrel; where a shared primitive exists, spec "compose `<X>`" not "build new."
9. **Implementation notes** — hook name (`useWipReport`), query key composition (`status`/`sort`/`order`), `retry: false`, query-param → API mapping, currency-from-cents formatting rule, and the SSE note: **WIP is fetch-on-load, not SSE** (it is not a live-push surface like the dispatch board) — state this so the engineer doesn't wire an EventSource.

**Accessibility Notes subsection (§10 — mandatory):**
- Color-independent status: deviation/over-budget conveyed via icon + text + color.
- Target sizes: every sortable header hit area and the CTA ≥ 24×24px (prefer 44×44px for the primary CTA).
- Focus order + `focus-visible` ring treatment across sortable headers and the CTA; focus never obscured by the `h-12` sticky header (spec `scroll-margin-top` if anchored).
- Table semantics: proper `<th scope="col">`, `aria-sort` on the active sort column.
- Contrast: confirm token pairings meet ≥4.5:1 (body) / ≥3:1 (large text, borders).

---

## Component Reuse Guardrails (§6 — do not duplicate locked patterns)

- Compose `<PilotTable>`, `<LoadingState>`, `<ErrorState>`, `<EmptyState>`/`<FirstTimeUserState>`, `<RoleGate permission="reports.view">`, `<NotificationBanner>` (severity-routed) — do not recreate any of these.
- The deviation badge composes the **existing four-class severity styling** (design-system reference §3). If a badge primitive already exists in the barrel, extend/compose it; only propose a new `DeviationBadge` if the barrel confirms none exists, and note it as "new domain component in `features/wip/components/`."
- Do **not** invent a new top-level UX pattern — this page is a straightforward report table composing existing primitives.

---

## Handoff Gate (§9)

After producing the spec, **STOP. Do not write any code.** End the spec with an explicit line: *"Design spec complete — awaiting Tom's approval before React implementation (Rule 1.5)."* Once Tom approves, the Architect authors `batch-up-1-react-engr-prompt.md` referencing this spec by path.
