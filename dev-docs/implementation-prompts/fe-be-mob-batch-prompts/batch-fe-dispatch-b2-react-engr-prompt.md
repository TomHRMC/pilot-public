# Implementation Prompt: DISPATCH-B2 — Schedule Board Filter Bar Redesign

**Mode**: Pilot React Engineer
**Batch**: DISPATCH-B2 (Frontend web)
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §2.3 DISPATCH-B2
**Design doc**: `batch-dispatch-b2-design.md` — every section (A–I)
**Decisions record**: `dispatch-filter-redesign-decisions.md` — locked decisions D1–D9
**Estimated session**: 2.5–3.5 hours
**Platform**: Web only (`apps/web`)
**Pure frontend — no backend changes needed** (no `pnpm sync-api-types` gate; no new endpoints; no DB)
**Depends on**: DISPATCH-B1.5 ✅ (all merged)

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-react-engineer/react-engineer-rules.md`** — in full
- **`batch-dispatch-b2-design.md`** — every section, especially **§H Surface Spec** (all pixels/classes) and **§I Component Manifest**
- **`dispatch-filter-redesign-decisions.md`** — §7 discovered-issue resolutions (status pill values; soft-delete; feature-folder placement)

Critical rules for this batch:

- **Rule 7**: Check what already exists before creating anything. `PillToggle` is inline in `DispatchToolbar.tsx` (visual reference); the popover dismissal pattern (outside-click + Escape + scroll-close) already exists in `JobContextMenu.tsx` — reuse its logic. Do NOT add anything to `packages/ui` (§D-DISC-3 — build in the feature folder).
- **Rule 8**: No new npm dependencies. Heroicons 2.0 (`@heroicons/react/24/outline`) is already used across the dispatch board.
- **Rule 9**: Route files stay thin — all work in `features/dispatch-board/`.
- **Rule 10**: Any failing test — even one that looks pre-existing — must be fixed before done. Root cause unclear → STOP and ask Tom.
- **No hardcoded design values**: all tokens from `pilotPreset`. Zero hex codes. The board grid tech color dot (`tech.display_color`) is the ONLY inline style allowed (data-driven, same as the existing sidebar).

---

## Design Decisions (Do Not Re-Litigate)

From the design doc §G + decisions record — final:

| Decision | Outcome |
|---|---|
| Filter chrome | Replace the fixed 192px left `<FilterSidebar>` with a **horizontal collapsible `FilterBar`** docked above the board grid (below `UnassignedTray`). |
| `DispatchBoardFilters` shape | **UNCHANGED.** Same 5 dimensions, same 6 toggle/clear actions, same empty-array-means-all semantics. `applyFilters()` is NOT touched. |
| Status pills | `All · Unassigned · Scheduled · Confirmed · In Progress · Completed`. `All` = clears only the status dimension (NOT `clearAllFilters`). The five status values map to `DispatchBoardJob["status"]` union members: `unassigned·scheduled·confirmed·in_progress·completed`. |
| Priority | Segmented control `Rush · Warranty · Standard` (multi-select). |
| Tech | Compact `Techs ▾` popover button with count badge — NOT a permanently-expanded list. |
| Customer Type | `Commercial · Residential` 2-pill toggle. |
| Job Type | Conditional row — render only when `uniqueJobTypes.length > 0`. |
| Collapse state | In-memory only (local `useState` in `DispatchBoardPage` preferred; non-persisted store field is the fallback). NO `localStorage`. |
| `FilterSidebar` | **Soft-delete** — stop rendering it, but do NOT delete the file or its FE-B27 test. |
| New `packages/ui` component? | **No** — build all sub-components in `features/dispatch-board/components/`. |

These were resolved at the architecture level. Do NOT change them without asking Tom.

---

## Pre-Work: Establish Regression Baseline

Before touching any file:

```bash
cd <repo>/frontend
pnpm --filter web test 2>&1 | tail -5
```

Record the exact count. It must still pass at the end. If any test is already failing → fix it or confirm with Tom before starting (do not treat as "pre-existing").

---

## Pre-Work: Sync API Types

**Not required** — this batch adds no hooks and touches no backend contract. Skip `pnpm sync-api-types`. (Filter state is client-side Zustand; the board data hook `useDispatchBoard` is unchanged.)

---

## Pre-Work: Verify Endpoints

**None** — no new API calls. Filtering is client-side visibility filtering via the existing `applyFilters()`. No endpoint verification needed.

---

## Pre-Work: Read These Source Files

Read each with `read_file` before writing any code:

```
frontend/apps/web/src/features/dispatch-board/components/FilterSidebar.tsx        ← the chrome being replaced: filter groups, empty-array=all semantics, uniqueJobTypes derivation, per-option counts, hasActiveFilters derivation
frontend/apps/web/src/features/dispatch-board/store.ts                            ← DispatchBoardFilters shape + toggle/clear actions (reuse verbatim); layoutMode "not persisted" precedent
frontend/apps/web/src/features/dispatch-board/components/DispatchBoardPage.tsx     ← composition to rewire (remove sidebar, dock bar); applyFilters (untouched); where board.techs/board.jobs/filters come from
frontend/apps/web/src/features/dispatch-board/components/DispatchToolbar.tsx       ← PillToggle inline component (:90) — visual language reference for FilterPill
frontend/apps/web/src/features/dispatch-board/components/JobContextMenu.tsx        ← outside-click + Escape + scroll-close popover dismissal pattern — reuse for TechFilterPopover
frontend/apps/web/src/features/dispatch-board/types-stub.ts                        ← DispatchBoardJob["status"] union + DispatchBoardTech shape (display_color)
frontend/apps/web/src/__tests__/batch_fe_b27/filter_sidebar_label.test.tsx         ← confirm this stays green (FilterSidebar still importable under soft-delete)
```

Locate related pieces:

```bash
grep -n "PillToggle" frontend/apps/web/src/features/dispatch-board/components/DispatchToolbar.tsx
grep -rn "FilterSidebar" frontend/apps/web/src   # confirm only DispatchBoardPage + the FE-B27 test import it
grep -n "applyFilters\|clearAllFilters\|toggleStatusFilter" frontend/apps/web/src/features/dispatch-board/components/DispatchBoardPage.tsx
```

---

## Context: What This Batch Does

| Area | Change |
|---|---|
| `FilterPill.tsx` | **New** — presentational pill (label, active, onClick, optional count, optional colorDot) |
| `TechFilterPopover.tsx` | **New** — `Techs ▾` button + checkbox popover; reuses `JobContextMenu` dismissal |
| `FilterBar.tsx` | **New** — horizontal collapsible bar; composes status pills + priority segmented + Tech popover + customer-type + job-type + active count + Clear all + collapse toggle |
| `DispatchBoardPage.tsx` | **Modify** — remove `<FilterSidebar>` from the main flex row; dock `<FilterBar>` below `UnassignedTray`; add local `filterBarCollapsed` state |
| `FilterSidebar.tsx` | **Soft-delete** — no longer rendered; file + FE-B27 test untouched |

Follow **§H of the design doc** for every pixel/class. Code snippets below are starting points — read each file first and match the actual props/classes you find.

---

## STEP 1 — `FilterPill` presentational primitive

**File**: `features/dispatch-board/components/FilterPill.tsx` **(new)**

Small stateless pill mirroring the `PillToggle` visual from `DispatchToolbar.tsx`. Props per design doc §F: `{ label, active, onClick, count?, colorDot? }`.

- Active: `bg-white shadow-sm text-neutral-900`. Inactive: `text-neutral-500 hover:text-neutral-700`.
- Base: `px-2.5 py-1 text-caption font-medium rounded focus-visible:ring-2 focus-visible:ring-brand-600`.
- Optional `colorDot` → `<span className="w-2 h-2 rounded-full" style={{ backgroundColor: colorDot }} aria-hidden />` (the one allowed inline style — data-driven tech color).
- Optional `count` → trailing `text-caption text-neutral-400 tabular-nums`.

---

## STEP 2 — `TechFilterPopover`

**File**: `features/dispatch-board/components/TechFilterPopover.tsx` **(new)**

Per design doc §H "Techs popover". Props §F: `{ techs, selectedTechIds, onToggleTech }`.

- Trigger button: `Techs` + count badge `· {n}` when `selectedTechIds.length > 0`; `ChevronDownIcon` from `@heroicons/react/24/outline`. `aria-haspopup="true" aria-expanded={open}`.
- Panel: `absolute z-50 mt-1 w-56 rounded-md border border-neutral-200 bg-white shadow-lg p-1`, `role="menu"`.
- Each tech row: checkbox + `colorDot` (`tech.display_color`) + name. `checked = selectedTechIds.length === 0 || selectedTechIds.includes(tech.id)` (all-when-empty semantics — read `FilterSidebar.tsx` for the exact expression).
- **Dismissal**: reuse the outside-click (`mousedown` on `document`) + Escape + scroll-close logic from `JobContextMenu.tsx`. Read that file first and mirror its `useEffect` cleanup.

Intermediate check:
```bash
pnpm --filter web test -- apps/web/src/features/dispatch-board 2>&1 | tail -10
```

---

## STEP 3 — `FilterBar` container

**File**: `features/dispatch-board/components/FilterBar.tsx` **(new)**

Per design doc §H "FilterBar container" + all control sections. Props §F: `{ techs, jobs, filters, collapsed, onToggleCollapsed, onToggleTech, onToggleStatus, onToggleCustomerType, onToggleJobType, onTogglePriority, onClearAll }`.

Composition (left→right, `flex items-center gap-3 flex-wrap`, `border-b border-neutral-200 bg-white px-4 py-2`):

1. **Status pills** — `All · Unassigned · Scheduled · Confirmed · In Progress · Completed`.
   - `All` active when `filters.statuses.length === 0`.
   - **`All` click behavior**: clears ONLY the status dimension. There is no store action for this today — implement by iterating `filters.statuses` and calling `onToggleStatus` for each (nets to empty), OR add a tiny `resetStatusFilter` action to `store.ts` (additive — does not change the `DispatchBoardFilters` shape). **Do NOT call `onClearAll` for the `All` pill** — that wipes every dimension. Pick one approach; if adding `resetStatusFilter`, add a store unit test for it.
   - Value map: `Unassigned→"unassigned"`, `Scheduled→"scheduled"`, `Confirmed→"confirmed"`, `In Progress→"in_progress"`, `Completed→"completed"`. These MUST be members of `DispatchBoardJob["status"]` (verify against `types-stub.ts`).
2. Separator `<span className="h-5 w-px bg-neutral-200" aria-hidden />`.
3. **Priority segmented** — `Rush · Warranty · Standard` → `togglePriority`.
4. **`TechFilterPopover`** (STEP 2).
5. **Customer Type** — `Commercial · Residential` → `toggleCustomerType`.
6. **Job Type** — conditional: only when `uniqueJobTypes.length > 0` (derive exactly as `FilterSidebar` does). Pills → `toggleJobType`.
7. **Active count** — `"{n} filters active"` (`techIds + statuses + customerTypes + jobTypes + priorities` lengths); hidden when 0.
8. **Clear all** — `text-caption text-brand-600 hover:text-brand-800`; `onClearAll`; visible only when count > 0.
9. **Collapse toggle** — `ml-auto`; `ChevronUpIcon`/`ChevronDownIcon`; tooltip via `title`.

**Collapsed render**: only `Filters ▾` toggle + `· {count}` badge.

Intermediate check:
```bash
pnpm --filter web test -- apps/web/src/features/dispatch-board 2>&1 | tail -10
```

---

## STEP 4 — Rewire `DispatchBoardPage`

**File**: `DispatchBoardPage.tsx` **(modify)** — read it first.

- **Remove** the `<FilterSidebar ... />` block from the main content flex row (currently `:579`) and remove its import. (Do NOT delete `FilterSidebar.tsx`.)
- Add local state: `const [filterBarCollapsed, setFilterBarCollapsed] = useState(false);`
- **Dock** `<FilterBar>` between `<UnassignedTray>` and the main content flex row — a full-width horizontal strip. The board grid + right-rail row now has no left aside, so the grid gets full width.
- Wire `FilterBar` props from the existing store selectors already destructured in the component (`filters`, `toggleTechFilter`, `toggleStatusFilter`, `toggleCustomerTypeFilter`, `toggleJobTypeFilter`, `togglePriorityFilter`, `clearAllFilters`) and `board?.techs ?? []` / `board?.jobs ?? []`.
- **Do NOT touch `applyFilters`** — `filteredJobs`/`visibleJobs` derivation stays exactly as is.

Intermediate check:
```bash
pnpm --filter web test -- apps/web/src/features/dispatch-board 2>&1 | tail -10
```

---

## Test Requirements

Web = Vitest + `@testing-library/react`. Mock `next/navigation` if the component tree pulls it in. QueryClient `retry: false` where a QueryClient is needed. Assert by **specific content/ID**, never by total list count (seed/fixture data varies). No MSW needed for the bar itself (no API calls) — the integration test uses the existing dispatch MSW fixtures for board data.

Create in `features/dispatch-board/components/__tests__/` (unit) and `apps/web/src/__tests__/batch_dispatch_b2/` (integration):

**`FilterPill.test.tsx`** (unit):
- Active vs inactive classes applied correctly.
- `onClick` fires.
- Optional `count` renders; `colorDot` renders the aria-hidden dot.

**`TechFilterPopover.test.tsx`** (unit):
- Closed by default; opens on trigger click (`aria-expanded` flips).
- Closes on Escape and on outside `mousedown`.
- Count badge shows `· 2` when 2 selected; absent when 0.
- Toggling a tech row calls `onToggleTech(id)`.
- All-when-empty: with `selectedTechIds=[]`, every checkbox is checked.

**`FilterBar.test.tsx`** (unit):
- Renders status pills, priority segmented, Techs button, customer-type pills.
- `All` status pill active when `statuses=[]`; clicking a status pill calls `onToggleStatus` with the correct union value.
- Clicking `All` when statuses are selected results in the status dimension being cleared (assert the handler behavior you implemented — either N `onToggleStatus` calls or one `resetStatusFilter`).
- Job Type row absent when `jobs` have no `job_type`; present when they do.
- Active count text reflects selected filters; hidden at 0.
- `Clear all` visible only when a filter is active; calls `onClearAll`.
- Collapse toggle flips `onToggleCollapsed`; collapsed render shows only the toggle + count badge.

**`dispatch_b2.integration.test.tsx`** (integration):
- Board renders with `<FilterBar>` present and `<FilterSidebar>` NOT in the DOM (assert the "Filters" sidebar `aria-label="Dispatch board filters"` aside is gone; the bar is present).
- Selecting a status pill hides/shows a specific job by ID in the grid (drive `applyFilters` end-to-end — assert on a known fixture job).
- RBAC: board is gated to `owner`/`operator` (`<RoleGate>`); a `tech` role does not see the board (reuse the AuthContext.Provider pattern from the inclusions §9).

---

## Final Verification

> ❌ **BANNED**: `npx vitest run`. The ONLY correct runner is `pnpm --filter web test`.

### Phase 1 — Targeted
```bash
cd <repo>/frontend
pnpm --filter web test -- apps/web/src/features/dispatch-board 2>&1 | tail -10
pnpm --filter web test -- apps/web/src/__tests__/batch_dispatch_b2/ 2>&1 | tail -10
```

### Phase 2 — Full
```bash
cd <repo>/frontend && echo "=== UI - Type Check ===" && pnpm --filter @pilot/ui check-types && echo "=== Web - Type Check ===" && pnpm --filter web check-types && echo "=== Mobile - Type Check ===" && pnpm --filter mobile build && echo "=== UI - Lint ===" && pnpm --filter @pilot/ui lint && echo "=== Web - Lint ===" && pnpm --filter web lint && echo "=== Mobile - Lint ===" && pnpm --filter mobile lint && echo "=== TYPE+LINT PASS ===" && echo "=== UI - Tests ===" && pnpm --filter @pilot/ui test 2>&1 | tail -6 && echo "=== Web - Tests ===" && pnpm --filter web test 2>&1 | tail -6 && echo "=== Mobile - Tests ===" && pnpm --filter mobile test 2>&1 | tail -8 && echo "=== MVP FINAL VERIFICATION COMPLETE ==="
```

Any failure in either phase must be fixed before the batch is declared done.

---

## Definition of Done — DISPATCH-B2

- [ ] Pre-modification regression baseline captured (zero pre-existing failures, or confirmed with Tom)
- [ ] `pnpm sync-api-types` — **N/A** (no backend change; confirmed skipped)
- [ ] Design doc §H + §I fully read before writing code
- [ ] All mandatory source files read
- [ ] **STEP 1**: `FilterPill.tsx` created — mirrors `PillToggle` visual; optional count + colorDot
- [ ] **STEP 2**: `TechFilterPopover.tsx` created — button + count badge + checkbox popover; outside-click/Escape/scroll dismissal reused from `JobContextMenu`; all-when-empty semantics
- [ ] **STEP 3**: `FilterBar.tsx` created — status pills (incl. `All`-clears-status-only), priority segmented, Tech popover, customer-type, conditional job-type, active count, Clear all, collapse toggle
- [ ] **STEP 4**: `DispatchBoardPage.tsx` — `<FilterSidebar>` removed from composition (import removed); `<FilterBar>` docked below `UnassignedTray`; local `filterBarCollapsed` state; `applyFilters` untouched
- [ ] `FilterSidebar.tsx` NOT deleted; FE-B27 `filter_sidebar_label.test.tsx` still passes untouched
- [ ] `DispatchBoardFilters` shape unchanged (only optional additive `resetStatusFilter`/`filterBarCollapsed` if you chose the store approach — with a test)
- [ ] Zero hardcoded design values (only the data-driven tech `colorDot` inline style)
- [ ] Unit tests pass (targeted run) — FilterPill, TechFilterPopover, FilterBar
- [ ] Integration tests pass in `__tests__/batch_dispatch_b2/` — bar present, sidebar gone, status filter drives the grid by job ID, RBAC
- [ ] Zero TypeScript errors; zero ESLint warnings
- [ ] No regressions in pre-existing suite
- [ ] **Phase 2 FULL verification passes** (`=== MVP FINAL VERIFICATION COMPLETE ===`):
  ```bash
  cd <repo>/frontend && echo "=== UI - Type Check ===" && pnpm --filter @pilot/ui check-types && echo "=== Web - Type Check ===" && pnpm --filter web check-types && echo "=== Mobile - Type Check ===" && pnpm --filter mobile build && echo "=== UI - Lint ===" && pnpm --filter @pilot/ui lint && echo "=== Web - Lint ===" && pnpm --filter web lint && echo "=== Mobile - Lint ===" && pnpm --filter mobile lint && echo "=== TYPE+LINT PASS ===" && echo "=== UI - Tests ===" && pnpm --filter @pilot/ui test 2>&1 | tail -6 && echo "=== Web - Tests ===" && pnpm --filter web test 2>&1 | tail -6 && echo "=== Mobile - Tests ===" && pnpm --filter mobile test 2>&1 | tail -8 && echo "=== MVP FINAL VERIFICATION COMPLETE ==="
  ```
- [ ] Final test count (before → after) documented in the Completion Summary
- [ ] Completion Summary added to `pilot-launch-plan.md` Appendix B

---

## Completion Summary

After all Definition of Done items are complete, add a **Completion Summary** to `pilot-launch-plan.md` Appendix B using the React template:

```markdown
### DISPATCH-B2 — Schedule Board Filter Bar Redesign: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot React Engineer
**Source design doc**: `batch-dispatch-b2-design.md`
**Baseline**: <N passed> (web)
**Final**: <N+K passed> (+K new tests)

#### What Was Accomplished
- Replaced the fixed 192px left `FilterSidebar` with a collapsible horizontal `FilterBar` above the board grid — recovers full viewport width for the grid in Day/Week/Month.
- <status pills / priority segmented / Tech popover / customer-type / job-type details>
- `DispatchBoardFilters` Zustand shape + `applyFilters` unchanged; `FilterSidebar` soft-deleted (file retained).

#### Files Changed / Created
| File | Action |
|---|---|
| `apps/web/src/features/dispatch-board/components/FilterBar.tsx` | Created |
| `apps/web/src/features/dispatch-board/components/FilterPill.tsx` | Created |
| `apps/web/src/features/dispatch-board/components/TechFilterPopover.tsx` | Created |
| `apps/web/src/features/dispatch-board/components/DispatchBoardPage.tsx` | Updated — sidebar removed, bar docked |
| `apps/web/src/features/dispatch-board/store.ts` | (if applicable) Updated — additive `resetStatusFilter` |

#### Tests Added
| Test File | Type | Tests | All Pass |
|---|---|---|---|
| `components/__tests__/FilterBar.test.tsx` | Unit | N | ✅ |
| `components/__tests__/TechFilterPopover.test.tsx` | Unit | N | ✅ |
| `components/__tests__/FilterPill.test.tsx` | Unit | N | ✅ |
| `__tests__/batch_dispatch_b2/dispatch_b2.integration.test.tsx` | Integration | N | ✅ |
```

Then mark DISPATCH-B2 ✅ in launch plan §2.0, add a one-row entry to Appendix A, and update the Section 5 gate item "Dispatch board — filter bar redesign (DISPATCH-B2)". Note the next dispatch work is complete for the Order-2 wave — JOB-UI-B1 / COMMS-UI-B1 / INVOICE-UI-B1 remain in Order 1.
