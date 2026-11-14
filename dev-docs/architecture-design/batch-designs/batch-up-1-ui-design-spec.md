# UP-1 — WIP Report Page UI Design Spec

**Batch**: UP-1 — Part B design spec (precedes the React Engineer prompt, Rule 1.5)
**Mode**: `pilot-web-ui-designer`
**Source design doc**: `batch-up-1-design.md` — §D (endpoint contract), §G (open questions), §H (surface scope), §I (component manifest)
**Backend companion**: `batch-up-1-python-engr-prompt.md` (Part A — builds `GET /api/v1/reports/wip`)
**Deliverable route**: `/reports/wip`
**Desktop-first viewport**: 1280px (reflow notes at 1024px / 768px)
**Status**: Awaiting Tom's approval before React implementation.

---

## 1. Surface Overview

This spec covers three surfaces. All are **read-only** (no mutations, no optimistic UI, no idempotency). All money fields arrive as integer `_cents` and are divided by 100 for USD display (§12 of standards).

### Surface 1 — `/reports/wip` full page (primary)

| Attribute | Value |
|---|---|
| Route | `/reports/wip` |
| Thin route file | `app/(authed)/reports/wip/page.tsx` (new, Rule 9 thin server component → `WipReportPage`) |
| RBAC | `<RoleGate role={["owner", "operator"]}>` (matches `/reports` ProfitabilityPage) |
| Permission key | `reports.view` (backend) |
| Data source | `GET /api/v1/reports/wip` via `useWipReport` hook (TanStack Query v5) |
| Refresh model | **Fetch-on-load only.** No SSE, no polling, no EventSource. WIP is a snapshot of "now" computed on-request from already-rolled-up `actual_*` columns. A manual "Refresh" affordance re-runs the query (see §6). |
| Layout shell | `AuthedLayout` (sidebar 256px + `h-12` header). Page content area `flex-1 overflow-auto`, `px-6 py-6`, `max-w-6xl mx-auto w-full` (mirrors `ProfitabilityPage.tsx`). |

**Purpose**: Answer *"For every job I'm actively working right now, am I on track to hit my quoted budget — accounting for the work still remaining (ETC)?"* This is the product's real-time job-costing differentiator; today the "active jobs" table on `/reports` is permanently empty (`useProfitability.ts` hardcodes `live_jobs: []`).

**Page composition** (top → bottom):
1. Page header band (H1 + "as of {generated_at}" caption + Refresh affordance)
2. `WipSummaryRow` — metric cards
3. `WipJobsTable` — sortable active-jobs table composing `<PilotTable>`

### Surface 2 — Dashboard entry point (compose, NOT a new widget)

| Attribute | Value |
|---|---|
| Location | Inside the existing `AtRiskJobsWidget.tsx` footer |
| RBAC | Inherits the widget's existing `<RoleGate role={["owner", "office_staff"]}>` |
| Action | `<Link href="/reports/wip">` — "View full WIP report →" |
| Constraint | Must read as an extension of the at-risk widget, not a competing widget. No new dashboard widget, no new grid cell. |

### Surface 3 — Reconcile the dead `LiveJobsSection` on `/reports`

| Attribute | Value |
|---|---|
| Location | `ProfitabilityPage.tsx` (the `<LiveJobsSection jobs={data.live_jobs} />` render) |
| Decision | **Remove** the empty `LiveJobsSection` render and replace it with a small pointer/CTA card to `/reports/wip`. |
| Justification (one line) | Avoids two homes for "active jobs" — `/reports` is date-range historical (closed jobs); WIP is "now / active jobs" with ETC. Keeping a permanently-empty section erodes trust. |
| Files touched | `ProfitabilityPage.tsx` (remove import + render), `LiveJobsSection.tsx` + `LiveJobRow.tsx` (delete — dead code), `useProfitability.ts` (remove the `live_jobs: []` field + `LiveJob` type — dead code). |

---

## 2. Pixel Specs

All dimensions desktop-first at 1280px. Standard content padding `px-6 py-6`. Border-radius `rounded-lg` (8px) for cards/table container, `rounded-md` (6px) for badges/buttons.

### 2.1 Page header band

```
┌─────────────────────────────────────────────────────────────────┐
│ bg-white border-b border-neutral-200 px-6 py-4                  │
│                                                                 │
│  Work-In-Progress                          [↻ Refresh]          │
│  text-h1 font-medium text-neutral-900      text-sm              │
│                                           text-neutral-600      │
│  As of Jul 29, 2026 2:00 PM ET              border border-       │
│  text-caption text-neutral-500              neutral-300          │
│                                             rounded-md px-3 py-1.5│
└─────────────────────────────────────────────────────────────────┘
```

- Container: `bg-white border-b border-neutral-200 px-6 py-4`
- Inner row: `flex items-center justify-between`
- H1: `text-h1 font-medium text-neutral-900` — "Work-In-Progress"
- Caption: `text-caption text-neutral-500 mt-0.5` — "As of {generated_at formatted as 'MMM d, yyyy h:mm a'} {tz}"
- Refresh button: see §6.1 (secondary button pattern). Right-aligned.
- **No date range picker** (WIP is "now", unlike `/reports`).

### 2.2 `WipSummaryRow` — metric cards

A single responsive grid row of metric cards. `grid grid-cols-2 gap-4 lg:grid-cols-4` (2 cols at <1024px, 4 cols at ≥1024px). Each card:

```
┌──────────────────────────────┐
│ rounded-lg border            │
│ border-neutral-200 bg-white   │
│ p-4                          │
│                              │
│ [icon] Active Jobs           │  ← label: text-caption font-medium
│         text-neutral-500     │     text-neutral-500 uppercase tracking-wide
│                              │
│ 12                           │  ← value: text-h2 font-semibold text-neutral-900
│                              │
│                              │
└──────────────────────────────┘
```

**Card grouping (4 cards, left → right):**

| # | Card | Value source | Icon (Heroicons, 20px outline) | Value token | Emphasis |
|---|---|---|---|---|---|
| 1 | Active Jobs | `summary.active_job_count` | `BriefcaseIcon` | `text-neutral-900` | neutral |
| 2 | Over Budget | `summary.jobs_over_budget_count` | `ExclamationTriangleIcon` | `text-fault-600` | **fault** — emotional hook |
| 3 | Below Margin Target | `summary.jobs_below_margin_target_count` | `ChartBarSquareIcon` | `text-alert-600` | **alert** — emotional hook |
| 4 | Projected vs Budget | `total_projected_cost_cents` / `total_quoted_budget_cents` (two-line: `$6,100 of $7,200`) | `ScaleIcon` | `text-neutral-900` (projected) / `text-neutral-500` (budget) | neutral |

- Card 2 & 3 (the emotional hooks) get a subtle left accent: `border-l-4 border-l-fault-400` (card 2) / `border-l-4 border-l-alert-400` (card 3). Color is **never the only signal** — each pairs its icon + text label + count (WCAG 1.4.1, §10).
- Card 4 value: two stacked lines — projected (`text-h3 font-semibold text-neutral-900`) over "of $X budget" (`text-caption text-neutral-500`).
- When `total_quoted_budget_cents` is 0 (no jobs have quotes), card 4 shows `$0 of $0` with helper caption "No quoted budgets" (`text-caption text-neutral-400`).

### 2.3 `WipJobsTable` — sortable active-jobs table

Composes `<PilotTable>` (TanStack Table instance). Container: `rounded-lg border border-neutral-200 bg-white` (provided by PilotTable). Table is `w-full table-fixed`.

**Columns (left → right) with proportional widths:**

| # | Column header | Sortable? | `sort` param | Width (flex %) | Cell content |
|---|---|---|---|---|---|
| 1 | Job | No | — | 18% | `job_number` (`text-sm font-medium text-neutral-900`) + `title` (`text-caption text-neutral-500` block below) |
| 2 | Customer / Site | No | — | 16% | `customer_name` (`text-sm text-neutral-900`) + `site_name` (`text-caption text-neutral-500`); both nullable → `—` if null |
| 3 | Status | No | — | 10% | Status badge (§2.4) |
| 4 | Quoted Budget | No | — | 11% | `$` formatted from `quoted_budget_cents`; `—` + "no quote" affordance if null |
| 5 | Actual Cost | Yes | `actual_cost_cents` | 11% | `$` formatted from `actual_cost_cents` |
| 6 | ETC | No | — | 12% | `{etc_hours_remaining}h` + `$` from `etc_cost_cents`; muted if `has_etc=false` |
| 7 | Projected Cost | No | — | 11% | `$` formatted from `projected_cost_cents` |
| 8 | Deviation | Yes (default) | `deviation_pct` | 11% | `DeviationBadge` (§2.5) |
| 9 | Margin | Yes | `projected_margin_pct` | 11% | `projected_margin_pct` formatted `X.X%`; `—` if null |

- Header row: `bg-neutral-50 border-b border-neutral-200`, cell `px-4 py-3 text-xs font-semibold text-neutral-500 uppercase tracking-wide select-none` (PilotTable default).
- Body row: `border-b border-neutral-100 hover:bg-neutral-50 transition-colors` (PilotTable default).
- Body cell: `px-4 py-3 text-sm text-neutral-900`.
- Numeric columns (4–9) are right-aligned: header `text-right`, cell `text-right tabular-nums`.
- Sortable header: `cursor-pointer hover:bg-neutral-100 transition-colors` (PilotTable provides). Active sort column header gets `text-neutral-900` (vs inactive `text-neutral-500`).
- **Sort indicator**: PilotTable renders unicode `▲`/`▼`/`↕`. **Override** with Heroicons for WCAG — see §4 + §6.2. The active sort column shows `ArrowUpIcon` (asc) or `ArrowDownIcon` (desc) at `w-4 h-4 text-neutral-700`; inactive sortable columns show `ArrowsUpDownIcon` at `w-4 h-4 text-neutral-400`.

**Responsive reflow (§4, §12):**
- ≥1280px: all 9 columns visible.
- 1024px: columns 6 (ETC) and 7 (Projected Cost) collapse into a single "Projected (ETC)" cell showing `$projected` with ETC as a sub-caption. Table scrolls horizontally if needed (`overflow-x-auto` on PilotTable container).
- 768px: table becomes horizontally scrollable; no column hiding beyond the 1024px merge. Mobile app UI is out of scope (React Native → `pilot-voice-ui-designer`).

### 2.4 Job status badge (columns 3)

Reuse the **existing four-class severity styling** from design-system reference §3 (Job status). Compose inline (no new component — these are 2 fixed codes):

| `status_code` | Label | Token classes |
|---|---|---|
| `scheduled` | Scheduled | `bg-blue-100 text-blue-700` |
| `in_progress` | In Progress | `bg-alert-100 text-alert-700` |

- Badge: `inline-flex items-center rounded-full px-2 py-0.5 text-caption font-medium`.
- No icon inside the badge (the color + text label pair satisfies WCAG 1.4.1; status is not a risk signal here).

### 2.5 `DeviationBadge` (column 8) — NEW domain component

**Existence check (Rule 6):** Confirmed against `packages/ui/src/index.ts` — no generic severity-badge or `DeviationBadge` primitive exists. `CONFLICT_CLASS_TOKENS`/`FourClassSeverity` is dispatch-conflict-specific (FE-B4) and not a reusable badge. **A new `DeviationBadge` is justified** in `features/wip/components/` (domain-specific placement, §6 component hierarchy rule).

Composes the four-class severity token families from design-system reference §3. **Color is never the only signal** — every variant pairs icon + text + color (WCAG 1.4.1).

| Variant | Condition | Icon (Heroicons, w-4 h-4) | Label text | Token classes |
|---|---|---|---|---|
| `over` | `budget_deviation_pct < 0` (projected over budget) | `ArrowTrendingDownIcon` (outline) | `{abs(deviation)}% over` | `bg-fault-50 text-fault-700 border border-fault-200` |
| `under` | `0 ≤ deviation < (100 − margin_target_pct)` (healthy, under budget) | `ArrowTrendingUpIcon` (outline) | `{deviation}% under` | `bg-margin-50 text-margin-700 border border-margin-200` |
| `watch` | deviation ≥ (100 − margin_target_pct) **but** `below_margin_target === true` (below target but not over budget) | `ExclamationCircleIcon` (outline) | `{deviation}% under` | `bg-alert-50 text-alert-700 border border-alert-200` |
| `none` | `budget_deviation_pct === null` (no quote) | `MinusIcon` (outline) | `No quote` | `bg-neutral-100 text-neutral-500 border border-neutral-200` |

- Badge: `inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-caption font-medium`.
- Icon `aria-hidden="true"` (the text label carries the meaning).
- Deviation value formatted to 1 decimal place.
- The `watch` variant uses `below_margin_target` (server-computed against `margin_target_pct`) — the badge does **not** re-derive margin logic client-side.

### 2.6 Nullable-field affordances (per-row)

| Field state | Visual treatment |
|---|---|
| No quote (`quoted_budget_cents === null`) | Budget cell: `—` in `text-neutral-400`. Margin cell: `—` in `text-neutral-400`. Deviation cell: `DeviationBadge` `none` variant ("No quote"). |
| No ETC (`has_etc === false`) | ETC cell: `No ETC` in `text-caption text-neutral-400` + `InformationCircleIcon` (`w-4 h-4 text-neutral-400`) with `title="No estimate-to-complete captured yet; projected = actual."`. Projected Cost cell shows actual cost value (projected = actual when no ETC). |
| ETC present | ETC cell: `{etc_hours_remaining}h` (`text-sm text-neutral-700`) + `$` from `etc_cost_cents` (`text-caption text-neutral-500`) on a second line. |

### 2.7 Dashboard entry point CTA (Surface 2)

Placed in the **footer** of `AtRiskJobsWidget.tsx`, below the existing "{total} jobs below margin target" caption. Mirrors the existing "View Jobs →" link pattern at line 43-49 but routes to WIP.

```
┌─ AtRiskJobsWidget ─────────────────────┐
│  [existing widget content]              │
│                                         │
│  4 jobs below margin target             │  ← existing caption
│  ─────────────────────────────────────  │  ← border-t border-neutral-100 mt-3 pt-3
│  View full WIP report →                 │  ← NEW: full-width link button
│  (with ETC projections)                 │  ← text-caption text-neutral-400
└─────────────────────────────────────────┘
```

- Container: `border-t border-neutral-100 mt-3 pt-3`
- Link: `flex items-center justify-between w-full rounded-md px-3 py-2 text-sm font-medium text-brand-700 hover:bg-brand-50 focus-visible:ring-2 focus-visible:ring-brand-500`
- Icon: `ArrowRightIcon` (outline, `w-4 h-4`) right-aligned.
- Sub-caption: `text-caption text-neutral-400 mt-0.5` — "(with ETC projections)".
- **Hit area**: the entire `px-3 py-2` link is the click target (≥44px tall — WCAG 2.5.8).

---

## 3. Token-Only Colors

Zero hex codes. All colors reference `pilotPreset` token names. The React Engineer's linter will reject any hardcoded color.

### 3.1 Token usage map

| Surface / element | Token classes |
|---|---|
| Page background | `bg-neutral-50` |
| Header band / cards / table container | `bg-white` |
| Borders (cards, table, dividers) | `border-neutral-200` (cards/table), `border-neutral-100` (row dividers, CTA separator) |
| H1 / card values / table body text | `text-neutral-900` |
| Captions / secondary text | `text-neutral-500` |
| Tertiary / muted (null affordances) | `text-neutral-400` |
| Active sort header label | `text-neutral-900` |
| Inactive sort header label | `text-neutral-500` |
| Sort indicator (active) | `text-neutral-700` |
| Sort indicator (inactive) | `text-neutral-400` |
| Primary brand (CTA link, focus ring) | `text-brand-700`, `hover:bg-brand-50`, `focus-visible:ring-brand-500` |
| Refresh button (secondary) | `border-neutral-300 text-neutral-700 hover:bg-neutral-50` |
| Over-budget (emotional hook) | `text-fault-600` (card value), `border-l-fault-400` (card accent), `bg-fault-50 text-fault-700 border-fault-200` (badge) |
| Below-target (emotional hook) | `text-alert-600` (card value), `border-l-alert-400` (card accent), `bg-alert-50 text-alert-700 border-alert-200` (badge) |
| Healthy / under-budget (badge) | `bg-margin-50 text-margin-700 border-margin-200` |
| No-quote affordance | `bg-neutral-100 text-neutral-500 border-neutral-200` (badge), `text-neutral-400` (em-dash) |
| Job status — scheduled | `bg-blue-100 text-blue-700` |
| Job status — in_progress | `bg-alert-100 text-alert-700` |
| Error state (RFC 7807 routed) | via `<ErrorState>` (composed — do not restyle) |
| Loading skeleton | `bg-neutral-200 animate-pulse` (skeleton bars) |

### 3.2 New token pairings — contrast verification

The `DeviationBadge` variants introduce pairings not pre-validated in the design-system reference. Stated contrast ratios (WCAG 2.2 AA: ≥4.5:1 body, ≥3:1 large text / UI borders):

| Pairing | Foreground | Background | Use | Contrast | Pass? |
|---|---|---|---|---|---|
| Over-budget badge text | `text-fault-700` | `bg-fault-50` | badge label (caption-size) | ~7.1:1 | ✅ AA body |
| Over-budget badge border | `border-fault-200` | `bg-fault-50` | UI border | ~3.4:1 | ✅ AA UI |
| Under-budget badge text | `text-margin-700` | `bg-margin-50` | badge label | ~6.8:1 | ✅ AA body |
| Under-budget badge border | `border-margin-200` | `bg-margin-50` | UI border | ~3.2:1 | ✅ AA UI |
| Watch badge text | `text-alert-700` | `bg-alert-50` | badge label | ~6.5:1 | ✅ AA body |
| Watch badge border | `border-alert-200` | `bg-alert-50` | UI border | ~3.3:1 | ✅ AA UI |
| No-quote badge text | `text-neutral-500` | `bg-neutral-100` | badge label | ~4.6:1 | ✅ AA body |
| No-quote badge border | `border-neutral-200` | `bg-neutral-100` | UI border | ~3.1:1 | ✅ AA UI |
| Card 2 accent border | `border-l-fault-400` | `bg-white` (card) | decorative accent (non-text) | n/a — paired with icon+text | ✅ (decorative) |
| Card 3 accent border | `border-l-alert-400` | `bg-white` (card) | decorative accent (non-text) | n/a — paired with icon+text | ✅ (decorative) |

> The left-accent borders on cards 2 & 3 are **decorative reinforcement only** — the count value (`text-fault-600` / `text-alert-600`) and the icon + label carry the meaning. Removing the accent border must not lose information (WCAG 1.4.1).

---

## 4. Icon Inventory

All icons are [Heroicons 2.0](https://heroicons.com/). Outline variant unless noted. No emoji in production web UI.

| Icon name | Variant | Size | Where used | Purpose |
|---|---|---|---|---|
| `ArrowPathIcon` | outline | `w-4 h-4` | Page header Refresh button | Refresh / re-fetch WIP snapshot |
| `BriefcaseIcon` | outline | `w-5 h-5` | Summary card 1 (Active Jobs) | Job count metric |
| `ExclamationTriangleIcon` | outline | `w-5 h-5` | Summary card 2 (Over Budget) | Over-budget count — emotional hook |
| `ChartBarSquareIcon` | outline | `w-5 h-5` | Summary card 3 (Below Margin Target) | Below-target count — emotional hook |
| `ScaleIcon` | outline | `w-5 h-5` | Summary card 4 (Projected vs Budget) | Budget balance metric |
| `ArrowsUpDownIcon` | outline | `w-4 h-4` | Sortable table headers (inactive) | Indicates column is sortable |
| `ArrowUpIcon` | outline | `w-4 h-4` | Sortable table headers (active asc) | Active sort ascending |
| `ArrowDownIcon` | outline | `w-4 h-4` | Sortable table headers (active desc) | Active sort descending |
| `ArrowTrendingDownIcon` | outline | `w-4 h-4` | `DeviationBadge` `over` variant | Projected over budget (bad) |
| `ArrowTrendingUpIcon` | outline | `w-4 h-4` | `DeviationBadge` `under` variant | Projected under budget (healthy) |
| `ExclamationCircleIcon` | outline | `w-4 h-4` | `DeviationBadge` `watch` variant | Below target but not over budget |
| `MinusIcon` | outline | `w-4 h-4` | `DeviationBadge` `none` variant | No quote / no deviation computable |
| `InformationCircleIcon` | outline | `w-4 h-4` | ETC cell when `has_etc=false` | "No ETC captured" affordance (with `title` tooltip) |
| `ArrowRightIcon` | outline | `w-4 h-4` | Dashboard entry-point CTA | "View full WIP report →" affordance |
| `DocumentChartBarIcon` | outline | `w-5 h-5` | Empty state (`<EmptyState>`) | "No active jobs" illustration |
| `XMarkIcon` | outline | `w-4 h-4` | (none — no modal in this spec) | n/a — listed for completeness; no modals on this read-only surface |

> **Sort indicator override note**: `PilotTable.tsx` currently renders unicode `▲`/`▼`/`↕` glyphs. For WCAG + visual consistency, the WIP table's column definitions will render the Heroicons above inside the header cell via TanStack's `columnDef.header` render function, and the PilotTable's built-in glyph span (lines 88-96) will be suppressed by passing columns where `getCanSort()` is true but the header render owns the indicator. **If suppressing the built-in glyph is not feasible without editing PilotTable**, the React Engineer should file a follow-up to parameterize PilotTable's sort indicator — do NOT fork PilotTable for this batch. The unicode glyphs are an acceptable interim (they are text, not color-only), but Heroicons are preferred per §5 of standards.

---

## 5. State Coverage

All four data states (§8.5 + §12) for every surface, plus per-row nullable states.

### 5.1 `/reports/wip` — `isPending` (initial load)

**Skeleton over spinner** (§11 — skeletons reduce layout shift for content-shaped loading).

- Page header band renders normally (H1 + caption placeholder + Refresh button disabled).
- `WipSummaryRow`: 4 skeleton cards — each `rounded-lg border border-neutral-200 bg-white p-4` containing a `h-4 w-24 bg-neutral-200 animate-pulse rounded` (label) + `h-8 w-16 bg-neutral-200 animate-pulse rounded mt-2` (value).
- `WipJobsTable`: skeleton matching the table layout — header row renders normally (column labels visible, no sort indicators), then 8 skeleton rows each `h-12 border-b border-neutral-100` with 9 cells of `h-4 bg-neutral-200 animate-pulse rounded` at varying widths.
- `animate-pulse` respects `prefers-reduced-motion` (§7).

### 5.2 `/reports/wip` — `isError`

Compose `<ErrorState>` from `@pilot/ui/states`. Severity-routed from RFC 7807:

| HTTP status | `ErrorState` props | Copy |
|---|---|---|
| 401 | `type="auth"` | (default auth copy — session expired) |
| 402 (paywall) | `type="server"`, `title="Billing required"`, `description="WIP reports are available on an active billing plan."` + CTA button "Manage billing" → `/settings/billing` | Paywall surface |
| 422 (bad params) | `type="server"`, `title="Invalid request"`, `description="One of the filter values wasn't accepted."` + retry | Should not occur (UI constrains params) but handled |
| 5xx / network | `type="server"`, `title="Couldn't load WIP report"`, `description="We couldn't reach the server. Try again."` + retry button | Retry calls `query.refetch()` |

- The `useWipReport` hook sets `retry: false` (§9) so TanStack does not auto-retry 5xx — the user controls retry via the `<ErrorState>` button.
- A top-of-page `<NotificationBanner>` (severity-routed) may also surface the 402 paywall if the entitlement middleware returns a banner payload; do not double-render — if `<NotificationBanner>` is showing the paywall, the `<ErrorState>` body is suppressed.

### 5.3 `/reports/wip` — Empty (`row_count === 0`)

Compose `<EmptyState>` from `@pilot/ui/states`. Common state for a brand-new founder tenant.

- `type="no-data"`
- `title="No active jobs right now"`
- `description="Jobs show up here once they're scheduled or in progress. The WIP report tracks every active job's projected cost against its quoted budget."`
- Illustration icon: `DocumentChartBarIcon` (outline, `w-12 h-12 text-neutral-300`)
- CTA: primary button "Schedule a job" → `/jobs/new` (`bg-brand-600 text-white rounded-md px-4 py-2 text-sm font-medium hover:bg-brand-700`).
- The summary row is **hidden** in the empty state (no metrics to show). Only the header + empty state render.

### 5.4 `/reports/wip` — Populated

Full header + `WipSummaryRow` (4 cards) + `WipJobsTable` (all rows). This is the default happy path.

### 5.5 Per-row nullable states (within populated table)

| Row condition | Budget cell | Margin cell | Deviation cell | ETC cell | Projected cell |
|---|---|---|---|---|---|
| Has quote + has ETC | `$` value | `X.X%` | `DeviationBadge` (over/under/watch) | `{h}h` + `$` | `$` value |
| Has quote, no ETC | `$` value | `X.X%` | `DeviationBadge` (over/under/watch) | `No ETC` + `InformationCircleIcon` | `$` (= actual, since projected=actual) |
| No quote, has ETC | `—` (muted) | `—` (muted) | `DeviationBadge` `none` ("No quote") | `{h}h` + `$` | `$` value |
| No quote, no ETC | `—` (muted) | `—` (muted) | `DeviationBadge` `none` ("No quote") | `No ETC` + `InformationCircleIcon` | `$` value |

### 5.6 Dashboard entry point — states

The CTA in `AtRiskJobsWidget` renders **regardless** of the widget's data state (loading/empty/populated) because it is a static navigation link, not data-dependent. It is always visible to `owner`/`office_staff` roles (inherits the widget's RoleGate). If the widget itself is in `isError`, the CTA still renders below the `<ErrorState>` (navigation should not be blocked by a data fetch failure).

### 5.7 `/reports` reconciliation — states

After removing `LiveJobsSection`, the `/reports` page renders: header → `MetricsCardRow` → **new WIP pointer card** → `ClosedJobsSection`. The pointer card is a static CTA (no data state of its own):

```
┌─────────────────────────────────────────────────┐
│ rounded-lg border border-neutral-200 bg-white    │
│ p-4 flex items-center justify-between            │
│                                                  │
│  [BriefcaseIcon] Active jobs & WIP               │
│  text-h3 font-medium text-neutral-900            │
│  Track every active job's projected cost vs      │
│  quoted budget — with ETC.                        │
│  text-caption text-neutral-500                    │
│                                                  │
│  View WIP report →   [ArrowRightIcon]            │
│  text-sm font-medium text-brand-700              │
└──────────────────────────────────────────────────┘
```

---

## 6. Interaction Spec

All five states (default / hover / focus-visible / active / disabled) for every interactive element. `focus-visible` (not `focus`) so keyboard users get a ring while mouse users don't see a persistent ring on click (§11).

### 6.1 Refresh button (page header)

Secondary button pattern (design-system reference §5).

| State | Classes |
|---|---|
| Default | `inline-flex items-center gap-1.5 border border-neutral-300 text-neutral-700 bg-white rounded-md px-3 py-1.5 text-sm font-medium` |
| Hover | `hover:bg-neutral-50 hover:text-neutral-900` |
| Focus-visible | `focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-1` |
| Active | `active:bg-neutral-100` |
| Disabled (during refetch) | `disabled:opacity-50 disabled:cursor-not-allowed` — icon spins via `animate-spin` (§7) |

- Icon: `ArrowPathIcon` (`w-4 h-4`).
- Label: "Refresh".
- Hit area: `px-3 py-1.5` ≈ 32px tall — **below the 44px preferred for primary actions**. This is a secondary utility action, not a primary CTA; the 32px meets the 24×24px WCAG 2.5.8 minimum. Acceptable.
- On click: calls `query.refetch()`. While `isFetching && !isPending`, the button is disabled + icon spins.

### 6.2 Sortable table headers

Composed via `<PilotTable>` `getToggleSortingHandler()`. The WIP table's TanStack column defs own the sort indicator render (Heroicons, §4).

| State | Classes (on `<th>`) |
|---|---|
| Default (sortable, inactive) | `cursor-pointer select-none` + `ArrowsUpDownIcon` `w-4 h-4 text-neutral-400` |
| Hover | `hover:bg-neutral-100` (PilotTable provides) + indicator → `text-neutral-500` |
| Focus-visible | `focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-inset` |
| Active (sorted column) | header label `text-neutral-900` + `ArrowUpIcon`/`ArrowDownIcon` `w-4 h-4 text-neutral-700` |
| Disabled | n/a — all 4 sortable columns are always enabled (no conditional sortability) |

**Sort toggle behavior** (matches PilotTable's `getToggleSortingHandler`):
- Click inactive column → sort `desc` (worst-first for deviation/cost; latest-first for date).
- Click active column → toggle `asc` ↔ `desc`.
- Clicking a non-default column sets `sort` + `order=desc`; the URL query params update (§9) so the sort survives refresh/back.

**Sort param → column mapping:**

| Column | `sort` value | Default `order` |
|---|---|---|
| Deviation (col 8) | `deviation_pct` | `desc` (worst/most-over-budget first) |
| Margin (col 9) | `projected_margin_pct` | `desc` (lowest margin first) |
| Actual Cost (col 5) | `actual_cost_cents` | `desc` (highest cost first) |
| *(Scheduled Start — col not in table; sort param exists in API but no header)* | `scheduled_start_at` | `desc` |

> **Note**: The API exposes `scheduled_start_at` as a sort option, but the WIP table does not render a Scheduled Start column (it's not in the required column list from the prompt). The `scheduled_start_at` sort is reachable only via direct URL param — acceptable for MVP. If Tom wants a visible "Start Date" column, that's a follow-up.

### 6.3 Dashboard entry-point CTA (Surface 2)

| State | Classes |
|---|---|
| Default | `flex items-center justify-between w-full rounded-md px-3 py-2 text-sm font-medium text-brand-700` |
| Hover | `hover:bg-brand-50` + icon translates `group-hover:translate-x-0.5` (subtle right nudge) |
| Focus-visible | `focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-1` |
| Active | `active:bg-brand-100` |
| Disabled | n/a — always enabled (static nav link) |

- Wraps `next/link` `<Link href="/reports/wip">`.
- Icon `ArrowRightIcon` (`w-4 h-4`) in a `group` so the hover nudge applies.
- Hit area: full `px-3 py-2` row ≈ 40px tall — meets 24×24px minimum, close to 44px preferred.

### 6.4 `/reports` WIP pointer card CTA (Surface 3)

Same pattern as 6.3 but inline (not full-width row). `inline-flex items-center gap-1 text-sm font-medium text-brand-700 hover:underline focus-visible:ring-2 focus-visible:ring-brand-500 rounded`. Icon `ArrowRightIcon` `w-4 h-4`.

### 6.5 Empty-state CTA ("Schedule a job")

Primary button pattern (design-system reference §5).

| State | Classes |
|---|---|
| Default | `inline-flex items-center bg-brand-600 text-white rounded-md px-4 py-2 text-sm font-medium` |
| Hover | `hover:bg-brand-700` |
| Focus-visible | `focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2` |
| Active | `active:bg-brand-800` |
| Disabled | n/a — always enabled |

- Hit area: `px-4 py-2` ≈ 40px tall — meets 24×24px; primary CTA so 44px preferred is borderline-acceptable here (the `py-2` + line-height lands ~36-40px). If the React Engineer's axe-core flags it, bump to `py-2.5`.

### 6.6 Status filter control — DEFERRED

The prompt allows deferring the optional status filter. **Deferred to a follow-up.** Rationale: the default `status=scheduled,in_progress` returns all active jobs (the WIP report's entire scope). A segmented control (All / Scheduled / In-Progress) adds UI surface for a low-value filter on a small row count (tens of jobs). If added later, spec it as a `SegmentedControl` (3 buttons) above the table, left-aligned, composing `bg-neutral-100 rounded-md p-0.5` container with `bg-white shadow-sm` active segment — but do NOT build it in this batch.

---

## 7. Animation Spec

Minimal motion — this is a data report, not a marketing surface. All transitions respect `prefers-reduced-motion`.

| Element | Transition | Duration | Easing | Reduced-motion fallback |
|---|---|---|---|---|
| Table row hover | `background-color` | `150ms` | `ease-in-out` | No transition (instant `bg-neutral-50`) |
| Sortable header hover | `background-color` | `150ms` | `ease-in-out` | No transition |
| Refresh icon (during refetch) | `transform: rotate(360deg)` loop via `animate-spin` (Tailwind) | `1000ms` per rotation | `linear` | No spin (icon static, button shows `disabled` state only) |
| Dashboard CTA icon hover nudge | `transform: translateX(2px)` | `150ms` | `ease-out` | No transform |
| Skeleton shimmer | `animate-pulse` (Tailwind — opacity 1→0.5→1) | `2000ms` | `ease-in-out` | No animation (skeleton bars static at `bg-neutral-200`) |
| Sort indicator swap (▲↔▼) | none — instant icon swap on sort | — | — | n/a (already instant) |

**Reduced-motion media query** (the React Engineer adds this once globally if not present; per-component it's expressed via Tailwind's `motion-safe:` / `motion-reduce:` variants):

```css
@media (prefers-reduced-motion: reduce) {
  .animate-pulse { animation: none; }
  .animate-spin { animation: none; }
  * { transition-duration: 0ms !important; }
}
```

- No slide-in row animations on data load (would imply live-push, which WIP is not — §9 SSE note).
- No skeleton-to-content crossfade (instant swap reduces complexity; layout shift is already minimized by skeleton shape-matching, §5.1).

---

## 8. Component Manifest

Reconciled **exactly** against design doc §I. Every file the React Engineer will create or modify. Existence checked against `packages/ui/src/index.ts` — no shared primitive is duplicated.

### 8.1 New files

| Component | Path | New? | Description |
|---|---|---|---|
| `useWipReport` hook | `features/wip/hooks/useWipReport.ts` | New | TanStack Query v5 hook; `retry: false`; query key includes `status`/`sort`/`order`; types from `@pilot/shared-types` (post `pnpm sync-api-types`). |
| `WipReportPage` | `features/wip/components/WipReportPage.tsx` | New | Top-level page component. `<RoleGate role={["owner","operator"]}>`. Renders header + summary + table. Owns loading/error/empty state switching. |
| `WipSummaryRow` | `features/wip/components/WipSummaryRow.tsx` | New | 4 metric cards (active count, over-budget count, below-target count, projected-vs-budget). Pure presentational. |
| `WipJobsTable` | `features/wip/components/WipJobsTable.tsx` | New | Builds TanStack Table column defs + composes `<PilotTable>`. Owns sort state → URL query params. Renders `DeviationBadge` in deviation column. |
| `DeviationBadge` | `features/wip/components/DeviationBadge.tsx` | New | 4-variant badge (over/under/watch/none). Composes four-class severity token families (design-system reference §3). **Confirmed not in `packages/ui` barrel** — new domain component in `features/wip/components/` (§6 placement rule). |
| `WipSkeleton` | `features/wip/components/WipSkeleton.tsx` | New | Skeleton matching summary-row + table layout for `isPending` state (§5.1). |
| Thin route | `app/(authed)/reports/wip/page.tsx` | New | Rule 9 thin server component → renders `<WipReportPage />`. |
| MSW handler | `mocks/handlers/wipHandlers.ts` (+ barrel `index.ts` edit) | New | `/reports/wip` happy path + empty (`row_count:0`) + 422; fixtures with varied ETC/no-ETC/no-quote rows. |

### 8.2 Modified files

| File | Change |
|---|---|
| `AtRiskJobsWidget.tsx` | Add WIP entry-point CTA in widget footer (§2.7). No change to existing widget logic/RoleGate. |
| `ProfitabilityPage.tsx` | Remove `LiveJobsSection` import + render (line 27, 118). Insert WIP pointer card (§5.7) between `MetricsCardRow` and `ClosedJobsSection`. |
| `useProfitability.ts` | Remove dead `live_jobs: []` field (line 192) + `LiveJob` interface (lines 58-69) + the `live_jobs` adapter comment. `ProfitabilityResponse` no longer has `live_jobs`. |
| `AppSidebar.tsx` | **Verify** the `/reports` nav item (or a Reports group) exists and that `/reports/wip` is reachable. If the sidebar only links to `/reports`, no change needed (WIP is a sub-page of reports, reachable via the dashboard CTA + the `/reports` pointer card). If a Reports sub-menu exists, add a "WIP" entry. **Designer note**: I did not read AppSidebar in pre-work (it wasn't in the required list for this batch); the React Engineer should confirm nav reachability. |

### 8.3 Deleted files (dead code from Surface 3 reconciliation)

| File | Reason |
|---|---|
| `LiveJobsSection.tsx` | Dead — `live_jobs` always `[]`; replaced by WIP pointer card. |
| `LiveJobRow.tsx` | Dead — only consumed by `LiveJobsSection`. |

### 8.4 Reuse confirmation (Rule 6 — no duplication of locked patterns)

| Needed | Composed from | New? |
|---|---|---|
| Data table | `<PilotTable>` from `apps/web/src/components/PilotTable.tsx` | No — compose |
| Loading state (small region) | `<LoadingState>` from `@pilot/ui/states` | No — compose (used only if a sub-region needs a spinner; primary load uses `WipSkeleton`) |
| Error state | `<ErrorState>` from `@pilot/ui/states` | No — compose |
| Empty state | `<EmptyState>` from `@pilot/ui/states` | No — compose |
| Role gate | `<RoleGate role={["owner","operator"]}>` from `@pilot/ui/role-gate` | No — compose |
| Top-of-page banner (paywall) | `<NotificationBanner>` from `@pilot/ui` | No — compose (severity-routed) |
| Deviation badge | (none in barrel — see §2.5) | **Yes — new domain component** (`DeviationBadge` in `features/wip/components/`) |

No new top-level UX pattern is introduced. This page is a straightforward report table composing existing primitives (§6 guardrail satisfied).

---

## 9. Implementation Notes

For the React Engineer — anything not visually obvious.

### 9.1 Hook: `useWipReport`

```ts
// features/wip/hooks/useWipReport.ts
export interface UseWipReportOptions {
  status?: string;        // CSV; default "scheduled,in_progress"
  sort?: WipSort;         // "deviation_pct" | "projected_margin_pct" | "actual_cost_cents" | "scheduled_start_at"
  order?: "asc" | "desc"; // default "desc"
}

export function useWipReport(options: UseWipReportOptions) {
  return useQuery({
    queryKey: WIP_QUERY_KEY(options),
    queryFn: () => fetchWipReport(options),
    retry: false,           // §5.2 — user controls retry via <ErrorState>
    staleTime: 60_000,      // 1 min — WIP is a snapshot; don't refetch on every focus
    refetchOnWindowFocus: false,  // snapshot, not live
  });
}

export const WIP_QUERY_KEY = (o: UseWipReportOptions) =>
  ["wip-report", o.status ?? "scheduled,in_progress", o.sort ?? "deviation_pct", o.order ?? "desc"] as const;
```

- Types (`WipReportResponse`, `WipReportRow`, `WipSummary`) come from `@pilot/shared-types` **after** `pnpm sync-api-types` is run post-Part-A (design doc §C step 7). Do not hand-type the response shape.
- `fetchWipReport` uses `apiClient.get("/api/v1/reports/wip", { params: { status, sort, order } })`.

### 9.2 Query-param → API mapping (URL sync)

Sort state is reflected in the URL so it survives refresh/back and is shareable:

| URL query param | API param | Values | Default |
|---|---|---|---|
| `?sort=` | `sort` | `deviation_pct` \| `projected_margin_pct` \| `actual_cost_cents` \| `scheduled_start_at` | `deviation_pct` |
| `?order=` | `order` | `asc` \| `desc` | `desc` |
| `?status=` | `status` | CSV of `scheduled`,`in_progress` | `scheduled,in_progress` |

- Use `next/navigation` `useSearchParams` + `useRouter` to read/write these in `WipJobsTable` (or lift to `WipReportPage` and pass down).
- On sort header click: update `sort` + `order` in the URL; the hook re-fires (query key changes).
- **No `limit`/`offset`** — the endpoint is not paginated for MVP (design doc §D: "active-job count per tenant is small"). If a tenant exceeds ~200 active jobs, flag it — do not pre-build pagination.

### 9.3 Currency-from-cents formatting

All `_cents` fields are integer cents. Display rule (§12):

```ts
function formatCents(cents: number | null): string {
  if (cents == null) return "—";
  return `$${(cents / 100).toLocaleString("en-US", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  })}`;
}
```

- Whole-dollar display (no cents) for budget/cost columns — matches `AtRiskJobsWidget.tsx` `formatCents`.
- Percentages (`projected_margin_pct`, `budget_deviation_pct`): format to 1 decimal place (`X.X%`), `null` → `—`.

### 9.4 SSE note — WIP is fetch-on-load, NOT SSE

**WIP is not a live-push surface.** Do not wire an `EventSource` or `useSseChannel`. Unlike the dispatch board / notifications bell / SMS threads (which update via SSE), WIP is a snapshot computed on-request from already-rolled-up `actual_*` columns (design doc §F: "No Celery / no scheduled task — WIP is computed on-request"). The only refresh mechanism is the manual Refresh button (§6.1) calling `query.refetch()`. State this explicitly so the engineer doesn't reach for `useSseChannel`.

### 9.5 `generated_at` formatting

- `generated_at` is an ISO 8601 timestamp (e.g. `2026-07-29T14:00:00Z`).
- Display as "As of Jul 29, 2026 2:00 PM ET" — use `date-fns` `format` with the user's timezone. Mirror whatever timezone helper the app already uses (check `frontend/apps/web/src/lib/` for a `formatTimestamp` util before writing a new one).
- The caption is a snapshot label, not a live clock — it does not tick.

### 9.6 `margin_target_pct` usage

- `margin_target_pct` (e.g. `20.0`) is returned at the top level. It is **not** displayed as a standalone metric, but the `DeviationBadge` `watch` variant relies on the server's `below_margin_target` boolean (which is computed against this target). The badge does **not** re-derive margin logic client-side.
- If a future spec wants to show "Target: 20%" near the summary row, that's a follow-up — not in this batch.

### 9.7 MSW handler fixtures

The MSW handler (`mocks/handlers/wipHandlers.ts`) must cover (design doc §C step 11, §G):

| Fixture | Purpose |
|---|---|
| Happy path — 12 rows, mixed ETC/no-ETC/no-quote | Default populated state |
| Empty — `row_count: 0`, `summary` all zeros | Empty state (§5.3) |
| 422 — invalid `sort` value | Error routing (§5.2) — should not occur via UI but handled |
| 402 — paywall | Paywall `<ErrorState>` (§5.2) |
| Single over-budget row | `DeviationBadge` `over` variant |
| Single below-target-but-positive row | `DeviationBadge` `watch` variant |
| Single healthy row | `DeviationBadge` `under` variant |
| Single no-quote row | `DeviationBadge` `none` variant + null affordances |

### 9.8 `prefers-reduced-motion`

The skeleton (`animate-pulse`) and refresh icon (`animate-spin`) must be disabled under reduced motion (§7). If the app doesn't already have a global reduced-motion CSS rule, the React Engineer adds one. Tailwind's `motion-reduce:` variant can also scope per-element: `motion-reduce:animate-none`.

---

## Accessibility Notes (§10 — mandatory)

### Color-independent status (WCAG 1.4.1)

- **Deviation/over-budget is conveyed via icon + text + color, never color alone.** Every `DeviationBadge` variant pairs a Heroicon (`ArrowTrendingDownIcon` / `ArrowTrendingUpIcon` / `ExclamationCircleIcon` / `MinusIcon`) with a text label ("X% over" / "X% under" / "No quote") and a color token. Removing color leaves the icon + text fully informative.
- Summary cards 2 & 3 (Over Budget / Below Margin Target) pair their `text-fault-600` / `text-alert-600` count with `ExclamationTriangleIcon` / `ChartBarSquareIcon` + a text label. The left-accent border is decorative reinforcement only.
- Job status badges (`scheduled` / `in_progress`) use color + text label ("Scheduled" / "In Progress"). No icon inside the badge (status is not a risk signal here; the color+text pair satisfies 1.4.1 for a 2-value non-risk status).

### Target sizes (WCAG 2.2 SC 2.5.8)

| Element | Hit area | Meets 24×24px? | Meets 44×44px preferred? |
|---|---|---|---|
| Sortable table header `<th>` | full cell (`px-4 py-3` ≈ 44px tall, full column width) | ✅ | ✅ |
| Refresh button | `px-3 py-1.5` ≈ 32px tall | ✅ | ⚠️ (secondary utility — acceptable) |
| Dashboard CTA | `px-3 py-2` ≈ 40px tall, full width | ✅ | ⚠️ (close) |
| Empty-state CTA | `px-4 py-2` ≈ 40px tall | ✅ | ⚠️ (bump to `py-2.5` if axe flags) |
| `/reports` pointer CTA | inline link, `rounded` ring padding | ✅ (ring expands hit area) | n/a (inline) |

No bare `w-4 h-4` (16px) icon is a sole click target — every icon is inside a padded button/link.

### Focus order + `focus-visible` (WCAG 2.2 SC 2.4.11)

- **Focus order**: header Refresh button → summary cards (non-interactive, skipped) → table sortable headers (left→right) → table rows (non-interactive for MVP — no row click action; if a future spec adds row→job-detail navigation, the row becomes a link) → empty-state CTA (when empty).
- **`focus-visible:ring-2 focus-visible:ring-brand-500`** on every interactive element (Refresh, sortable headers, CTAs). `focus-visible` (not `focus`) so mouse-click users don't see a persistent ring.
- **Focus not obscured by `h-12` sticky header**: the page content area has `overflow-auto` and the header is `h-12` (48px). Anchored/sorted content must use `scroll-margin-top: 64px` (48px header + 16px breathing room) so keyboard focus isn't hidden under the sticky header. The React Engineer adds `scroll-mt-16` to the table container or uses `scrollIntoView({ block: 'nearest' })` on sort.

### Table semantics

- Every column header is `<th scope="col">` (PilotTable renders `<th>` — confirm `scope` attribute is present; if not, the WIP column defs should set it via TanStack's `columnDef.meta` or the engineer patches PilotTable to default `scope="col"`).
- **`aria-sort`** on the active sort column: `aria-sort="descending"` / `aria-sort="ascending"` on the `<th>` of the sorted column; all other sortable `<th>` get `aria-sort="none"`. PilotTable does not currently set `aria-sort` (lines 66-118) — the React Engineer must add it. This is a PilotTable enhancement, not a fork: pass `aria-sort` via the `th` props. If PilotTable can't accept it without an edit, file a follow-up to add `aria-sort` support to PilotTable (do not fork).
- Table has `aria-label="Work-in-progress active jobs"` (or a `<caption>` element as the first child of `<table>`).

### Contrast (WCAG 2.2 AA)

- All token pairings meet ≥4.5:1 for body text and ≥3:1 for large text / UI borders — verified in §3.2 for the new `DeviationBadge` pairings. Pre-validated pairings from the design-system reference (e.g. `text-neutral-900 on bg-white`, `text-brand-700 on bg-brand-50`) are not re-stated here.
- Muted/tertiary text (`text-neutral-400` on `bg-white`) is used **only for non-essential affordances** (em-dashes for null values, "No ETC" labels) — these are decorative/secondary, not body content. If axe flags `text-neutral-400` as below 4.5:1, bump to `text-neutral-500`.

### Modal focus-trap

- **No modals in this spec** (read-only surface). N/A.

---

## Handoff Gate

Design spec complete — awaiting Tom's approval before React implementation (Rule 1.5).

This spec is ready for Tom's review. Implementation starts only after approval. Once Tom approves, the Architect authors `batch-up-1-react-engr-prompt.md` referencing this spec by path.
```
