# DISPATCH-B2 — Filter Bar Redesign: Decisions & Findings Record

**Batch**: DISPATCH-B2
**Status**: ✅ Decisions locked — ready to drive the design doc + UI spec + React Engineer prompt
**Author**: Pilot Architect
**Date authored**: 2026-07-27
**Layer**: Frontend only — `apps/web`. No backend, no DB, no API changes.
**Source card**: `pilot-launch-plan.md §2.3 DISPATCH-B2`
**Prerequisite**: DISPATCH-B1.5 ✅ (Day + Week parity in Lane/Tech modes; toolbar `PillToggle` pattern established)

> **Purpose**: This record freezes every design decision for the dispatch filter redesign so the design doc, UI spec, and engineer prompt do not re-litigate them. Tom locked the core decisions on 2026-07-24 (recorded in the launch plan card); this doc formalizes them, resolves the discovered status-value discrepancy, and inventories the exact current code that changes.

---

## 1. Problem Statement

The dispatch board currently renders a fixed **192px left sidebar** (`FilterSidebar.tsx`, `w-48`) with five vertically-stacked checkbox filter groups (Tech, Status, Customer Type, Job Type, Priority). On a 1280px design viewport the board grid (day-tech, week-lane, week-tech) is horizontally cramped — the sidebar permanently consumes 15% of the width even when the dispatcher is not filtering.

**Primary pain (Tom, 2026-07-24)**: horizontal space. The board is the product's highest-value surface; the filter controls should not permanently occupy a full column.

---

## 2. Current State (Confirmed via Source)

| Aspect | Current implementation | File |
|---|---|---|
| Filter chrome | Fixed 192px left `<aside>` (`w-48 flex-shrink-0 border-r`) | `FilterSidebar.tsx` |
| Filter dimensions | Tech, Status, Customer Type, Job Type, Priority (5 groups of checkboxes) | `FilterSidebar.tsx` |
| Filter state | `DispatchBoardFilters` in Zustand (`techIds[]`, `statuses[]`, `customerTypes[]`, `jobTypes[]`, `priorities[]`) | `store.ts` |
| Filter actions | `toggleTechFilter`, `toggleStatusFilter`, `toggleCustomerTypeFilter`, `toggleJobTypeFilter`, `togglePriorityFilter`, `clearAllFilters` | `store.ts` |
| Filter application | `applyFilters(board.jobs, filters)` — pure client-side visibility filter | `DispatchBoardPage.tsx` |
| Composition | `<FilterSidebar>` sits left of the board grid inside the main content flex row | `DispatchBoardPage.tsx` |
| Empty-state semantics | Empty array in any dimension = "all visible" (not "none visible") | `FilterSidebar.tsx`, `applyFilters` |
| Status values in sidebar | `unassigned`, `scheduled`, `in_progress`, `confirmed` | `FilterSidebar.tsx` |
| Priority values | `rush`, `standard`, `warranty` | `FilterSidebar.tsx` |
| Existing test | `filter_sidebar_label.test.tsx` renders `FilterSidebar` in isolation, asserts "Customer Type" group label | FE-B27 |

**Shared-component reality**: There is **no** shared `PillToggle`, segmented control, or popover primitive in `packages/ui`. `PillToggle` is a private inline component in `DispatchToolbar.tsx`. The click-outside + Escape + scroll-close popover pattern already exists in `JobContextMenu.tsx` and is the reuse reference for the Tech multi-select popover.

---

## 3. Locked Decisions (Tom, 2026-07-24)

| # | Decision | Outcome |
|---|---|---|
| D1 | **Status stays a filter dimension** | Status is NOT promoted to top-level tabs. It remains one filter among several, rendered as a horizontal pill row. |
| D2 | **Primary goal = recover horizontal space** | Replace the fixed 192px `<aside>` with a horizontal, collapsible filter **bar** docked **above** the board grid (below `UnassignedTray`). |
| D3 | **Tech filter = compact multi-select popover** | Tech becomes a single button (`Techs ▾` with an active-count badge) that opens a checkbox popover — not a permanently-expanded list. |
| D4 | **Filters persist across view tabs, reset on load** | Filter state survives Day↔Week↔Month tab switches (already true — Zustand persists in-memory). It resets to empty on full page reload (already true — no `localStorage`). No change needed to persistence behavior. |
| D5 | **Status pills** | `All · Unassigned · Scheduled · In Progress · Completed` (see §7 D-DISC-1 for value resolution). |
| D6 | **Priority = segmented control** | `Rush · Warranty · Standard` as a multi-select segmented control. |
| D7 | **Active-filter count + "Clear all"** | The bar shows a total active-filter count and a "Clear all" affordance that calls `clearAllFilters()`. |
| D8 | **`DispatchBoardFilters` Zustand shape unchanged** | No store field renames, no new dimensions, no changed empty-array semantics. Presentation-only refactor. |
| D9 | **Soft-delete `FilterSidebar`** | Do NOT delete `FilterSidebar.tsx` or its FE-B27 test. Stop rendering it (remove from `DispatchBoardPage`), leave the file + test intact until Tom validates the new bar in live use. Deletion is a follow-up cleanup. |

---

## 4. Layout Decision — Collapsible Horizontal Bar

**Docked position**: A full-width `FilterBar` sits **between `UnassignedTray` and the board grid** (i.e., the main content flex row becomes a single column: grid + right rail; the bar is a horizontal strip above that row).

**Collapsed vs expanded**:
- **Default (expanded)**: bar shows the full control set (status pills, priority segmented, Techs popover button, Customer Type toggle, Job Type toggle when data exists, active-count, Clear all).
- **Collapsed**: bar collapses to a single slim row showing only a `Filters ▾` toggle + the active-filter count badge. Chevron toggles expanded/collapsed.
- **Persistence**: collapsed/expanded is **in-memory only** (a new `useState` in `DispatchBoardPage` OR a non-persisted store field — engineer's choice; see design doc §F). It does NOT use `localStorage`. Matches the `layoutMode` "not persisted" convention from B1.

**Space win**: removing the 192px `<aside>` returns the full viewport width to the board grid in all three views.

---

## 5. Control Inventory (Expanded Bar, Left→Right)

| Control | Type | State dimension | Behavior |
|---|---|---|---|
| **Status** | Pill row (multi-select) | `filters.statuses[]` | `All` pill = clears the status dimension (empty array). Other pills toggle individual statuses. `All` is visually active when `statuses.length === 0`. |
| **Priority** | Segmented control (multi-select) | `filters.priorities[]` | `Rush · Warranty · Standard`; each toggles independently via `togglePriorityFilter`. |
| **Techs ▾** | Popover button + checkbox list | `filters.techIds[]` | Button shows `Techs` + count badge (`Techs · 3` when 3 selected; no badge when 0 = all). Popover lists techs with color dot + name; each row toggles `toggleTechFilter`. Popover closes on outside-click / Escape / scroll (reuse `JobContextMenu` pattern). |
| **Customer Type** | 2-pill toggle | `filters.customerTypes[]` | `Commercial · Residential`; toggles via `toggleCustomerTypeFilter`. |
| **Job Type** | Pill row (conditional) | `filters.jobTypes[]` | Rendered **only when** `uniqueJobTypes.length > 0` (same guard as current sidebar). Toggles via `toggleJobTypeFilter`. |
| **Active count** | Text | derived | Total count of active filter selections across all dimensions. |
| **Clear all** | Text button | — | Calls `clearAllFilters()`; visible only when any filter is active. |

**Counts on individual options**: the current sidebar shows a per-option match count (e.g. `Scheduled 4`). Retaining per-pill counts in a horizontal bar is **optional and deferred** — the design doc marks per-option counts as a nice-to-have that may be dropped if it crowds the bar. The active-filter total (D7) is required; per-option counts are not.

---

## 6. State & Filtering Logic — Unchanged

- `applyFilters()` in `DispatchBoardPage.tsx` is **not touched**. The new bar drives the exact same Zustand actions the sidebar drove.
- Empty-array-means-all semantics preserved for every dimension.
- No new query params, no server round-trip — filtering stays 100% client-side visibility filtering.
- SSE, move pipeline, right-rail arbitration, `UnassignedTray` — all untouched.

---

## 7. Discovered Issues & Resolutions

### D-DISC-1 — Status pill values vs. current sidebar values (RESOLVED)

**Finding**: The locked card (D5) lists status pills `All · Unassigned · Scheduled · In Progress · Completed`. The current `FilterSidebar.tsx` uses `unassigned · scheduled · in_progress · confirmed` (note: `confirmed`, not `completed`). The `DispatchBoardJob["status"]` union in `types-stub.ts` is: `draft · scheduled · in_progress · completed · cancelled · unassigned · confirmed`.

**Resolution**: The status pill set is a **presentation choice over the same `statuses[]` array** — each pill's `value` must be a member of the `DispatchBoardJob["status"]` union so `applyFilters` matches. Ship the pills that map to real dispatch-relevant statuses:

`All · Unassigned · Scheduled · Confirmed · In Progress · Completed`

- `All` = clears the dimension (not a status value).
- `Unassigned`→`unassigned`, `Scheduled`→`scheduled`, `Confirmed`→`confirmed`, `In Progress`→`in_progress`, `Completed`→`completed`.
- This is a **superset** of the current sidebar (adds `Completed`, keeps `Confirmed`) — no status the sidebar filtered on is lost, and `completed` is a valid union member. The UI Designer/engineer must use these exact union string values; do NOT invent a `completed` alias that isn't in the union.

> **Rationale for keeping both `Confirmed` and `Completed`**: the launch-plan card omitted `Confirmed`, but it is an active dispatch status in the union and the current sidebar filters on it. Dropping it would be a regression. Adding `Completed` matches the card's intent (dispatchers want to hide finished work). Six pills is still comfortable in a horizontal row at 1280px.

### D-DISC-2 — FE-B27 FilterSidebar test (RESOLVED)

**Finding**: `filter_sidebar_label.test.tsx` renders `FilterSidebar` in isolation and asserts the "Customer Type" group label.

**Resolution**: Per D9 (soft-delete), `FilterSidebar.tsx` stays in the tree and remains importable, so this test continues to pass untouched. No change to the FE-B27 test in this batch. When Tom later approves deleting `FilterSidebar`, that cleanup batch also deletes this test.

### D-DISC-3 — No shared popover/segmented primitive (RESOLVED)

**Finding**: `packages/ui` has no `PillToggle`, segmented control, or popover primitive to reuse.

**Resolution**: Build the new bar sub-components **inside the dispatch-board feature folder** (`features/dispatch-board/components/`), not in `packages/ui`. These are dispatch-specific and not yet needed elsewhere (Rule 7 — only promote to `packages/ui` when a second consumer appears). The Tech popover reuses the outside-click/Escape/scroll-close logic already proven in `JobContextMenu.tsx`. The status/priority/customer pills can share one small internal `FilterPill` presentational component.

---

## 8. Scope Boundary

**In scope** (this batch):
- New `FilterBar` + its pill/segmented/popover sub-components in `features/dispatch-board/components/`.
- Remove `<FilterSidebar>` from `DispatchBoardPage` composition; dock `<FilterBar>` above the board grid.
- Collapse/expand toggle (in-memory).
- Active-filter count + Clear all.
- Unit + integration tests for the new bar.

**Out of scope** (explicitly deferred):
- Deleting `FilterSidebar.tsx` and its FE-B27 test (follow-up cleanup after Tom validates).
- Any change to `DispatchBoardFilters` shape, `applyFilters`, or Zustand actions.
- Promoting any bar sub-component to `packages/ui`.
- Server-side filtering / new query params.
- Mobile dispatch (dispatch board is desktop/web-only).
- Per-option match counts (optional nice-to-have, may be dropped).

---

## 9. Handoff

This record drives:
1. `batch-dispatch-b2-design.md` — the formal batch design (§A–I), which in turn references this record for all locked decisions.
2. A UI design spec (`dispatch-b2-ui-design-spec.md`) — **optional**; the card names UI Designer as the next step, but because DISPATCH-B2 is a presentation refactor of existing, well-understood controls (mirroring the established `PillToggle` visual language), the design doc §H may inline the pixel spec instead of a separate spec doc. Tom decides at review whether a standalone UI spec is warranted.
3. `batch-fe-dispatch-b2-react-engr-prompt.md` — the React Engineer implementation prompt.
