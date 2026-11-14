# Batch Design: DISPATCH-B2 — Schedule Board Filter Bar Redesign

**Batch**: DISPATCH-B2
**Type**: Frontend-only (`apps/web`) — presentation refactor
**Engineer**: Pilot React Engineer
**Author**: Pilot Architect
**Date**: 2026-07-27
**Status**: Ready for Tom review → React Engineer
**Source plan**: `pilot-launch-plan.md §2.3 DISPATCH-B2`
**Decisions record**: `dispatch-filter-redesign-decisions.md` — all decisions D1–D9 locked there; this doc does not re-litigate them
**Prerequisite**: DISPATCH-B1.5 ✅

> **No backend. No DB. No API. No migration. No MCP verification required.** This batch replaces the fixed left filter sidebar with a collapsible horizontal filter bar. The `DispatchBoardFilters` Zustand shape, its toggle actions, and `applyFilters()` are all unchanged — this is a pure presentation-layer refactor. The §B "Migration Plan" section is intentionally N/A.

---

## A. Input Read Summary

| Input | Why read | Key takeaway |
|---|---|---|
| `pilot-launch-plan.md §2.3 DISPATCH-B2` | Batch scope + locked decisions | Status stays a filter dimension; primary pain = horizontal space; Tech = popover; filters persist across tabs, reset on load; status pills + priority segmented; active count + Clear all; soft-delete `FilterSidebar`. |
| `dispatch-filter-redesign-decisions.md` | Formalized decisions D1–D9 + discovered-issue resolutions | Status pill value set resolved (D-DISC-1); FE-B27 test safe under soft-delete (D-DISC-2); build sub-components in feature folder, not `packages/ui` (D-DISC-3). |
| `FilterSidebar.tsx` | Current filter chrome to replace | 5 checkbox groups; empty-array = all; per-option counts; `w-48` fixed aside. |
| `store.ts` | Filter state contract | `DispatchBoardFilters` (5 dims) + 6 toggle/clear actions — reused verbatim. `layoutMode` "not persisted" precedent for collapse state. |
| `DispatchBoardPage.tsx` | Composition + `applyFilters` | Sidebar mounted in main flex row (`:579`); `applyFilters` (`:84`) unchanged; right-rail arbitration + `UnassignedTray` untouched. |
| `DispatchToolbar.tsx` | `PillToggle` visual language | Private inline `PillToggle` (`:90`) is the pill visual reference; not shared in `packages/ui`. |
| `JobContextMenu.tsx` | Popover dismissal pattern | Outside-click + Escape + scroll-close reference for the Tech popover. |
| `types-stub.ts` | `DispatchBoardJob["status"]` union | Valid status values: `draft·scheduled·in_progress·completed·cancelled·unassigned·confirmed`. Status pills must map to these. |
| `react-engr-std-prompt-inclusions.md` | Prompt authoring standard | Web platform rules, test setup, verification gate. |
| `filter_sidebar_label.test.tsx` | Existing test impact | Renders `FilterSidebar` in isolation → safe under soft-delete (file stays). |

---

## B. Migration Plan

**N/A — no database changes.** DISPATCH-B2 is frontend presentation only. No Alembic migration, no new columns, no triggers, no MCP verification. The filter model is client-side Zustand state that already exists.

---

## C. Execution Order

| # | Step | File(s) | Notes |
|---|---|---|---|
| 1 | Add non-persisted `filterBarCollapsed` UI state | `store.ts` **or** local `useState` in `DispatchBoardPage` | Engineer's choice per §F. Not persisted (matches `layoutMode`). |
| 2 | Build `FilterPill` presentational primitive | `components/FilterPill.tsx` **(new)** | Shared by status / priority / customer-type / job-type rows. |
| 3 | Build `TechFilterPopover` | `components/TechFilterPopover.tsx` **(new)** | Button + count badge + checkbox popover; reuse `JobContextMenu` dismissal pattern. |
| 4 | Build `FilterBar` container | `components/FilterBar.tsx` **(new)** | Composes pills + popover + active count + Clear all + collapse toggle. Consumes the same Zustand actions the sidebar used. |
| 5 | Rewire `DispatchBoardPage` composition | `DispatchBoardPage.tsx` **(modify)** | Remove `<FilterSidebar>` from the main flex row; dock `<FilterBar>` above the board grid (below `UnassignedTray`). Leave `applyFilters` untouched. |
| 6 | Tests | `__tests__/` + `batch_dispatch_b2/` | Unit for each new component + integration for the bar wired into the page. |

`FilterSidebar.tsx` is **not** deleted (soft-delete, D9) and its FE-B27 test is not touched.

---

## D. New API Endpoints

**None.** No new endpoints, no changed contracts, no new query params. Filtering remains client-side visibility filtering via the existing `applyFilters()`.

---

## E. Pattern Reuse Decisions

| Pattern | Applies? | How |
|---|---|---|
| `PillToggle` visual language (`DispatchToolbar`) | ✅ | `FilterPill` mirrors the pill styling (`bg-neutral-100` container, active = `bg-white shadow-sm text-neutral-900`, inactive = `text-neutral-500`). |
| Popover dismissal (`JobContextMenu`: outside-click + Escape + scroll) | ✅ | `TechFilterPopover` reuses this exact dismissal logic. |
| Empty-array-means-all filter semantics | ✅ | Preserved verbatim; the `All` status pill and the "no tech selected = all techs" badge both encode this. |
| `<RoleGate role={["owner","operator"]}>` board wrapper | ✅ | Unchanged — the bar renders inside the existing gate; no new permission key. |
| §16 platform patterns (track-changes, confirm-as-turn, 409-refresh, etc.) | ❌ | None apply — this is a filter chrome refactor, not a data-mutation surface. |
| Optimistic UI / mutation | ❌ | No mutations; filtering is local. |

No new top-level UX pattern is introduced (Rule 8 §8 compliance) — the bar composes the existing pill/popover visual language.

---

## F. Shared Module Interfaces & State

**No Celery tasks, no backend services.** Client component interfaces only:

```ts
// FilterBar.tsx — props (approximate; engineer adjusts to actual store selectors)
interface FilterBarProps {
  techs: DispatchBoardTech[];        // from board.techs — for the Tech popover list
  jobs: DispatchBoardJob[];          // from board.jobs — for uniqueJobTypes derivation (+ optional per-option counts)
  filters: DispatchBoardFilters;     // current Zustand filter state
  collapsed: boolean;                // UI state (§C step 1)
  onToggleCollapsed: () => void;
  onToggleTech: (id: string) => void;
  onToggleStatus: (s: DispatchBoardJob["status"]) => void;
  onToggleCustomerType: (t: "commercial" | "residential") => void;
  onToggleJobType: (t: string) => void;
  onTogglePriority: (p: "rush" | "standard" | "warranty") => void;
  onClearAll: () => void;
}
```

```ts
// FilterPill.tsx — presentational
interface FilterPillProps {
  label: string;
  active: boolean;
  onClick: () => void;
  count?: number;      // optional per-option count (deferred nice-to-have)
  colorDot?: string;   // for tech rows inside the popover
}
```

```ts
// TechFilterPopover.tsx
interface TechFilterPopoverProps {
  techs: DispatchBoardTech[];
  selectedTechIds: string[];   // filters.techIds
  onToggleTech: (id: string) => void;
}
```

**Collapse state decision (§C step 1)**: Prefer a **local `useState` in `DispatchBoardPage`** over a store field — it is view chrome, not cross-component filter data, and keeping it local avoids growing the store. If the engineer finds the bar needs the state at a level `DispatchBoardPage` cannot reach, a non-persisted `filterBarCollapsed` store field (mirroring `layoutMode`) is the fallback. Either is acceptable; local `useState` is the default.

All existing actions (`toggleTechFilter`, `toggleStatusFilter`, `toggleCustomerTypeFilter`, `toggleJobTypeFilter`, `togglePriorityFilter`, `clearAllFilters`) are consumed unchanged from `useDispatchBoardStore`.

---

## G. Open Questions Resolved

| Q | Resolution |
|---|---|
| Status pill values — card says `Completed`, sidebar uses `confirmed` | **Resolved (D-DISC-1)**: ship `All · Unassigned · Scheduled · Confirmed · In Progress · Completed`. `All` clears the dimension; the other five map to real `DispatchBoardJob["status"]` union members (`unassigned`, `scheduled`, `confirmed`, `in_progress`, `completed`). Superset of the current sidebar — no regression; adds `Completed`. |
| Delete `FilterSidebar.tsx` now? | **No (D9)** — soft-delete: stop rendering it, keep the file + FE-B27 test until Tom validates. Deletion is a follow-up. |
| New shared `packages/ui` component? | **No (D-DISC-3)** — build in `features/dispatch-board/components/`. Promote to `packages/ui` only when a 2nd consumer appears (Rule 7). |
| Per-option match counts in the bar? | **Optional/deferred** — active-filter total (D7) is required; per-pill counts are a nice-to-have that may be dropped if the bar crowds. |
| Collapse state persistence? | **In-memory only** — no `localStorage`. Resets on reload, survives tab switches (matches `layoutMode`). |
| Standalone UI design spec doc? | **Not required for this batch** — §H below inlines the pixel spec; the controls mirror the established `PillToggle` language. Tom may request a standalone spec at review if desired. |

---

## H. Surface Spec (inlined — no separate UI spec doc)

**Scope**: Web only, desktop-first (1280px min). All tokens from `pilotPreset` — **zero hex codes**. All icons Heroicons 2.0 outline. Every interactive element gets `focus-visible:ring-2 focus-visible:ring-brand-600`.

### Docked position

```
┌────────────────────────────────────────────────────────────────────────────┐
│ DispatchToolbar  [Day|Week|Month] < Today >  … [5d|7d] [Lane|Tech]         │
├────────────────────────────────────────────────────────────────────────────┤
│ UnassignedTray   Unassigned (2)  [chip] [chip]                             │
├────────────────────────────────────────────────────────────────────────────┤
│ FilterBar  ← NEW (below tray, above board; full width; border-b)           │
│  [Status: All·Unassigned·Scheduled·Confirmed·In Progress·Completed]         │
│  [Priority: Rush·Warranty·Standard]  [Techs ▾ ·3]  [Commercial·Residential] │
│  [Job Type: …]      3 filters active   Clear all              [▾ collapse]  │
├──────────────────────────────────────────────────┬─────────────────────────┤
│ BOARD GRID AREA (now full width — no left aside)  │ RIGHT RAIL (w-80)       │
│                                                    │ Conflict OR Properties  │
└──────────────────────────────────────────────────┴─────────────────────────┘
```

### FilterBar container

| Property | Value |
|---|---|
| Root | `w-full border-b border-neutral-200 bg-white px-4 py-2 flex items-center gap-3 flex-wrap` |
| Collapsed root | Same, but renders only `Filters ▾` toggle + active-count badge |
| Section separators | Between control groups: `<span className="h-5 w-px bg-neutral-200" aria-hidden />` |

### Status pill row

| Element | Classes / behavior |
|---|---|
| Container | `inline-flex bg-neutral-100 rounded-md p-0.5 gap-0.5` |
| Each pill (`FilterPill`) | active: `bg-white shadow-sm text-neutral-900`; inactive: `text-neutral-500 hover:text-neutral-700`; `px-2.5 py-1 text-caption font-medium rounded` |
| `All` pill | active when `filters.statuses.length === 0`; click → `clearAllFilters` is **wrong** — instead reset only status: engineer sets `statuses` to `[]` (add a tiny `resetStatuses` inline via `toggleStatusFilter` loop, or clear by toggling — see prompt STEP note). Simplest: `All` click removes every currently-selected status. |
| Status pills | `Unassigned·Scheduled·Confirmed·In Progress·Completed` → union values `unassigned·scheduled·confirmed·in_progress·completed`; each toggles `toggleStatusFilter(value)` |

> **`All` implementation note**: there is no store action that clears only the status dimension without touching other dimensions. The engineer implements `All` by iterating the currently-selected statuses and calling `toggleStatusFilter` for each (net effect: empties `statuses[]`), OR adds a small `resetStatusFilter` action to the store. Adding `resetStatusFilter` is acceptable (additive, does not change the shape) — engineer's choice. Do NOT use `clearAllFilters` for the `All` status pill — that would wipe every dimension.

### Priority segmented control

`Rush · Warranty · Standard` — same `FilterPill` container/pill classes as status; each toggles `togglePriorityFilter`. Multi-select (independent). Order: `Rush · Warranty · Standard` (per card).

### Techs popover (`TechFilterPopover`)

| Element | Classes / behavior |
|---|---|
| Trigger button | `inline-flex items-center gap-1 px-2.5 py-1 text-caption font-medium rounded-md border border-neutral-200 text-neutral-700 hover:bg-neutral-50`; label `Techs`; when `techIds.length > 0` append a count badge `· {n}` |
| Chevron | `ChevronDownIcon` (Heroicons, `w-3.5 h-3.5`) |
| Popover panel | `absolute z-50 mt-1 w-56 rounded-md border border-neutral-200 bg-white shadow-lg p-1`; dismiss on outside-click / Escape / scroll (reuse `JobContextMenu` logic) |
| Tech row | checkbox + color dot (`tech.display_color`) + name; toggles `toggleTechFilter(tech.id)`; `checked = techIds.length === 0 || techIds.includes(tech.id)` (all-when-empty semantics) |
| a11y | trigger `aria-haspopup="true" aria-expanded={open}`; panel `role="menu"` |

### Customer Type toggle

`Commercial · Residential` 2-pill toggle (same `FilterPill`); toggles `toggleCustomerTypeFilter`. Empty = all.

### Job Type row (conditional)

Rendered **only when** `uniqueJobTypes.length > 0` (derive exactly as the sidebar does: `Array.from(new Set(jobs.map(j => j.job_type).filter(Boolean)))`). Pills toggle `toggleJobTypeFilter`. Label each with `jobType[0].toUpperCase() + slice(1)`.

### Active-filter count + Clear all

| Element | Behavior |
|---|---|
| Count text | `text-caption text-neutral-500`; e.g. `"3 filters active"` (sum of `techIds.length + statuses.length + customerTypes.length + jobTypes.length + priorities.length`); hidden when 0 |
| Clear all | `text-caption text-brand-600 hover:text-brand-800`; calls `clearAllFilters()`; visible only when count > 0 (same `hasActiveFilters` derivation as the sidebar) |

### Collapse toggle

`ChevronUpIcon`/`ChevronDownIcon` button at the far right (`ml-auto`); toggles `collapsed`. Tooltip `"Collapse filters"` / `"Expand filters"`. When collapsed, the bar shows only `Filters ▾` + active-count badge.

### State table

| State | Visual |
|---|---|
| Expanded, no filters | Full control set; no count text; no Clear all; `All` status pill active |
| Expanded, N filters | Active pills highlighted; `"N filters active"` + `Clear all` shown |
| Collapsed | Slim row: `Filters ▾` + `· N` count badge (if any); chevron expands |
| Tech popover open | Panel visible; trigger `aria-expanded=true`; dismiss on outside/Escape/scroll |
| No job-type data | Job Type row absent (conditional guard) |

---

## I. Component Manifest

| File | Action | Destination | Description |
|---|---|---|---|
| `FilterBar.tsx` | **New** | `apps/web/.../dispatch-board/components/` | Horizontal collapsible filter bar; composes pills + Tech popover + count + Clear all + collapse toggle; consumes existing Zustand actions |
| `FilterPill.tsx` | **New** | same | Presentational pill (label, active, onClick, optional count/colorDot) — shared by status/priority/customer/job-type |
| `TechFilterPopover.tsx` | **New** | same | Tech multi-select popover button + checkbox list; reuses `JobContextMenu` dismissal pattern |
| `DispatchBoardPage.tsx` | **Modify** | same | Remove `<FilterSidebar>` from main flex row; dock `<FilterBar>` above the board grid; add local `filterBarCollapsed` state; `applyFilters` untouched |
| `FilterSidebar.tsx` | **Soft-delete (keep)** | same | No longer rendered; file + FE-B27 test remain until Tom approves deletion |

**Tests (new)**:
- `components/__tests__/FilterBar.test.tsx` — renders controls; toggles fire correct store actions; active count; Clear all; collapse; Job Type conditional.
- `components/__tests__/TechFilterPopover.test.tsx` — opens/closes (outside-click, Escape); toggles tech; count badge; all-when-empty checkbox state.
- `components/__tests__/FilterPill.test.tsx` — active/inactive classes; onClick; optional count.
- `__tests__/batch_dispatch_b2/dispatch_b2.integration.test.tsx` — bar wired into page; status pill filters the grid (assert a job hidden/shown by ID, not by count); `FilterSidebar` no longer in the DOM; RBAC (board gated to owner/operator).

**Unchanged (do not modify)**: `store.ts` (unless adding optional `resetStatusFilter`/`filterBarCollapsed`), `applyFilters`, `DispatchToolbar`, `UnassignedTray`, `ConflictPreviewPane`, `JobPropertiesPanel`, all hooks, `DispatchWeekView`/`DispatchWeekLaneView`/`DispatchGridDayView`/`DispatchBoardLanes`.

---

## Handoff

This design drives `batch-fe-dispatch-b2-react-engr-prompt.md`. No Python Engineer half — frontend-only, no `pnpm sync-api-types` gate (no backend contract change). React Engineer proceeds directly after Tom approves this design.

*Authored by Pilot Architect, 2026-07-27. Source reads: launch plan §2.3, decisions record, `FilterSidebar.tsx`, `store.ts`, `DispatchBoardPage.tsx`, `DispatchToolbar.tsx`, `JobContextMenu.tsx`, `types-stub.ts`, FE-B27 filter test, react-engr inclusions.*
