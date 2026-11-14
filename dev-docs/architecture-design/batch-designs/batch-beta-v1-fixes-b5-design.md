# BETA-B5 Batch Design — Dispatch Board Multi-Day Views

**Version**: 1.0  
**Date**: 2026-06-04  
**Batch**: BETA-B5  
**Prerequisite Batches**: FE-B4 ✅, BETA-B1 ✅, BETA-B2 ✅, BETA-B3 ✅, BETA-B4 ✅  
**Estimated Effort**: 3–5 days  
**Test Subfolder**: `apps/web/__tests__/batch_beta_b5/`  
**Platform**: Web-only (Next.js 16)  
**Status**: Design complete — ready for React Engineer implementation  

---

## A. Input Read Summary

All source artifacts were read directly. No content was assumed.

### A.1 Artifacts Read

| Artifact | Key Findings |
|:---|:---|
| `frontend/apps/web/src/features/dispatch-board/components/DispatchGrid.tsx` | Props: `{ techs, jobs, activeDate, onJobSelect, onMoveJob, isMoveJobPending }`. No `viewMode` prop. Wraps `DndProvider`. Renders tech columns side-by-side. `activeDate` drives all drop pixel → ISO conversion. No multi-day awareness. |
| `frontend/apps/web/src/features/dispatch-board/store.ts` | `DispatchViewTab = "day" \| "4day" \| "week" \| "month"`. `getTabDays()` returns 1/4/7/30. `navigatePrev/navigateNext` correctly advances `activeDate` by `getTabDays(viewTab)`. Store is correct — the visual rendering layer does not consume `viewTab`. |
| `frontend/apps/web/src/features/dispatch-board/hooks/useDispatchBoard.ts` | **Critical gap**: `fetchDispatchBoard(date)` always generates `end_date = T23:59:59Z` for the same date — a 24-hour window regardless of `viewTab`. For 4-Day/Week, it must receive `endDate` derived from `getTabDays()`. Hook signature must change to `useDispatchBoard(startDate, endDate)`. |
| `frontend/apps/web/src/features/dispatch-board/components/DispatchBoardPage.tsx` | Calls `useDispatchBoard(activeDate)` — single date only. Passes `viewTab` to `DispatchToolbar` but **not** to `DispatchGrid`. `DispatchGrid` is called with fixed `techs`, `jobs`, `activeDate` — no view mode awareness. |
| `frontend/apps/web/src/features/dispatch-board/components/DispatchToolbar.tsx` | Tab switcher is fully functional. `VIEW_TABS` renders Day/4-Day/Week/Month buttons. `formatDisplayDate()` correctly formats date string for month/week/4day/day. `onViewTabChange` callback wires correctly to Zustand store. **No changes needed to DispatchToolbar.** |
| `frontend/apps/web/src/features/dispatch-board/components/DispatchGridColumn.tsx` | Single tech column, height `780px` (13h × 60px). `isoToTopPx()` uses `getHours()` on ISO string — time-only, no date dimension. `COLUMN_MIN_WIDTH_PX = 140`. Exports `GRID_START_HOUR`, `GRID_END_HOUR`, `GRID_HOURS`, `HOUR_HEIGHT_PX`, `GRID_HEIGHT_PX`. |
| `frontend/apps/web/src/features/dispatch-board/components/JobBlock.tsx` | `useDrag` makes block draggable. Props: `{ job, tech, heightPx, topPx, onSelect, hasDriveTimeWarning }`. Absolutely positioned within its parent column. No date dimension — position is purely computed from `topPx`/`heightPx` by parent. |
| `frontend/apps/web/src/features/dispatch-board/types-stub.ts` | `DispatchBoardResponse = { date, techs: DispatchBoardTech[], jobs: DispatchBoardJob[] }`. **Mismatch from real API** — the actual `DispatchBoardResponse` schema (openapi.json) uses `{ start_date, end_date, techs: DispatchBoardTechGroup[], unassigned: DispatchBoardJobEntry[] }`. The stub's flat `jobs` array is a fabrication. See §H. |
| `backend/openapi.json` (dispatch-board endpoint) | `GET /api/v1/scheduling/dispatch-board` accepts `start_date` and `end_date` (ISO-8601 datetime). Returns `DispatchBoardResponse` with `start_date`, `end_date`, `techs: DispatchBoardTechGroup[]`, `unassigned: DispatchBoardJobEntry[]`. `DispatchBoardTechGroup` contains `tech_id`, `jobs[]`, `eta_minutes_to_first_job`. **Single endpoint handles all date ranges.** No pagination. |
| `backend/openapi.json` (`DispatchBoardJobEntry` schema) | Fields: `id`, `tenant_id`, `customer_id`, `site_id`, `status_id`, `scheduled_start_at` (nullable datetime), `scheduled_end_at` (nullable datetime), `estimated_duration_minutes` (nullable int), `external_calendar_event_id` (nullable), `is_active`, `eta_minutes` (nullable int). Note: no `title`, `customer_name`, `priority`, `job_type`, `customer_type` — those are stub-only fields. |
| `dev-docs/architecture-design/batch-designs/batch-fe-b4-design.md` | FE-B4 specified `MonthViewCell` component ("Single day cell in Month view; shows job count + capacity bar") but it was never built. FE-B4 described `DispatchGrid` as "tech columns × time rows" — tech-column layout is the canonical design intent. URL state for view mode was noted. No explicit layout spec for multi-day beyond the grid concept. |
| `dev-docs/product-requirements/mvp-prd.md` §3.14 | PRD says: "primary scheduling UI on web renders as a grid of tech columns × time rows." Drag-to-reschedule and drag-to-reassign are required PRD features, not scoped to day-only. Month view has no explicit layout spec beyond the toolbar tab existence. Four-class conflict detection applies to placement actions. |
| `dev-docs/architecture-design/mvp-arch.md` §13.11 | SSE endpoint: `GET /api/v1/scheduling/board/stream?token=`. Events: `job_scheduled`, `job_rescheduled`, `job_reassigned`, `job_unassigned`, `conflict_detected`, `conflict_cleared`. SSE is a global board stream — **not date-scoped**. Multi-day views do not change the SSE architecture. |

### A.2 Root Cause Analysis

There are **two bugs** causing the visual freeze, not one:

1. **Hook bug (data layer)**: `useDispatchBoard(date)` always computes `end_date` as `{date}T23:59:59Z` — identical to a Day view range — regardless of `viewTab`. When the user switches to 4-Day, the API is still called with a 24-hour window and returns only one day of jobs.

2. **Rendering bug (visual layer)**: `DispatchGrid` receives no `viewMode` prop and always renders the same tech-column × time-row layout. Even if the hook returned 4 days of data, the grid would still render all jobs as if they were on the active date.

Both must be fixed for multi-day views to work.

---

## B. Execution Order

Implementation order is strict — each item depends on the previous:

1. **Update `useDispatchBoard` hook signature** — add `endDate` parameter; update `DispatchBoardPage` to compute `endDate` from `getTabDays(viewTab)` before passing.
2. **Add `MultiDayGrid` sub-component** — new file, new component, renders N day panels side-by-side.
3. **Extend `DispatchGrid` with `viewMode` prop** — routing branch: `day` → existing code path; `4day`/`week` → `<MultiDayGrid>`; `month` → `<MonthDeferredState>`.
4. **Add `MonthDeferredState` sub-component** — simple placeholder rendering "Month view coming soon" with correct empty-state styling.
5. **Update `DispatchBoardPage`** — pass `viewTab` and computed `endDate` to hook; pass `viewMode` and `dateRange` to `DispatchGrid`.
6. **Tests** — per §I.

---

## C. Component Changes

### C.1 `useDispatchBoard` — Hook Signature Change

| Property | Detail |
|:---|:---|
| **File** | `frontend/apps/web/src/features/dispatch-board/hooks/useDispatchBoard.ts` |
| **Change** | Add `endDate: string` parameter (YYYY-MM-DD). Compute `end_date` as `{endDate}T23:59:59Z` instead of the same date as `start_date`. Update `DISPATCH_BOARD_QUERY_KEY` to include both dates. |

Current signature: `useDispatchBoard(date: string)`  
New signature: `useDispatchBoard(startDate: string, endDate: string)`

The `fetchDispatchBoard` internal function becomes `fetchDispatchBoard(startDate, endDate)`, sending:
- `start_date = {startDate}T00:00:00Z`
- `end_date = {endDate}T23:59:59Z`

The query key changes from `["dispatch-board", date]` to `["dispatch-board", startDate, endDate]`.

**Backward compatibility**: Day view passes `startDate = activeDate, endDate = activeDate` — identical behavior to the current call.

### C.2 `DispatchGrid` — Add `viewMode` and `dateRange` Props

| Property | Detail |
|:---|:---|
| **File** | `frontend/apps/web/src/features/dispatch-board/components/DispatchGrid.tsx` |
| **Change** | Add two optional props: `viewMode?: DispatchViewTab` (default `'day'`) and `dateRange?: string[]` (array of YYYY-MM-DD strings for the window). Add rendering branch: `viewMode === 'day'` or not provided → existing code path unchanged. `viewMode === '4day' \| 'week'` → render `<MultiDayGrid>`. `viewMode === 'month'` → render `<MonthDeferredState>`. |

Extended interface:
```
interface DispatchGridProps {
  techs: DispatchBoardTech[];
  jobs: DispatchBoardJob[];
  activeDate: string;
  onJobSelect: (jobId: string) => void;
  onMoveJob: (variables: MoveJobVariables) => void;
  isMoveJobPending?: boolean;
  // New props for BETA-B5:
  viewMode?: DispatchViewTab;   // default 'day'
  dateRange?: string[];          // YYYY-MM-DD strings; length matches viewMode window
}
```

The `DndProvider` wrapper and `ConflictPreviewPane` remain unchanged. Multi-day views skip the DnD rendering path — `MultiDayGrid` does not use `onMoveJob` or `handleDrop`. The conflict pane only shows when `showConflictPane` is true, which can only be set by `handleDrop` — so the pane is never triggered in multi-day mode.

**Day view code path is completely unchanged** — the added props are optional with `day` as default.

### C.3 `MultiDayGrid` — New Component

| Property | Detail |
|:---|:---|
| **File** | `frontend/apps/web/src/features/dispatch-board/components/MultiDayGrid.tsx` |
| **Type** | New component |
| **Used by** | `DispatchGrid` (when `viewMode === '4day'` or `'week'`) |

Layout pattern: **Option C — side-by-side day panels**. Each panel is a date-scoped read-only rendering of all tech columns for that single date. N panels are displayed horizontally, where N = 4 (4-Day) or 7 (Week).

Rationale for Option C:
- **PRD alignment**: "grid of tech columns × time rows" — time axis is fundamental to the design. Option C preserves this for each day.
- **Component reuse**: Each panel reuses `DispatchGridColumn` directly. No new column architecture needed.
- **Data shape**: Jobs are already in a flat array with `scheduled_start_at` ISO timestamps — client-side filter by date string is trivial.
- **Minimum viable complexity for beta**: Options A and B require new time-axis and layout logic; Option C wraps existing components.
- **Read-only**: Drag-drop is explicitly out of scope for multi-day in beta — removing `DndProvider` from each day panel is trivial.

**Props:**
```
interface MultiDayGridProps {
  dateRange: string[];          // YYYY-MM-DD array, length 4 or 7
  techs: DispatchBoardTech[];
  jobs: DispatchBoardJob[];
  onJobSelect: (jobId: string) => void;
}
```

**Internal behavior:**
- For each `dateStr` in `dateRange`, render a `<DayPanel>` (inline sub-component within the file).
- `<DayPanel>` accepts `date: string, techs, jobs, onJobSelect`.
- Inside `<DayPanel>`: filter `jobs` to those whose `scheduled_start_at` matches the panel date (YYYY-MM-DD prefix comparison). Render a read-only column set: a date header row followed by one `DispatchGridColumn` per tech (without `onDrop`, which is optional in `DispatchGridColumn`) plus an Unassigned column.
- **No `DndProvider` wrapper** — multi-day panels are read-only at beta.
- Panels scroll vertically together (shared scroll container). The date header row is sticky at the top of each panel.
- Column width: `COLUMN_MIN_WIDTH_PX` (140px) per column, identical to Day view. With 4 days × N techs, horizontal scroll is expected and handled by the parent overflow container.

**Date header row** (per panel):
- Date formatted as `"Mon Jun 9"` (weekday abbreviated, no year).
- Highlighted if `dateStr === today`.
- Separator between panels via a thin right border.

**`DispatchGridColumn` read-only mode**: `DispatchGridColumn` already works without a drop target — `onDrop` is required in its current interface, but the prop can be given a no-op function for read-only mode. See §E for the minor prop adjustment needed.

### C.4 `MonthDeferredState` — New Component

| Property | Detail |
|:---|:---|
| **File** | `frontend/apps/web/src/features/dispatch-board/components/MonthDeferredState.tsx` |
| **Type** | New component |
| **Used by** | `DispatchGrid` (when `viewMode === 'month'`) |

Renders an empty-state panel with:
- Calendar icon (reuse existing Pilot UI icon set).
- Heading: "Month view coming soon"
- Body text: "Switch to Day, 4-Day, or Week view to manage your schedule."
- No call-to-action. No action buttons.

This is an **explicit design decision** (see §G) — Month view is deferred for beta. The FE-B4 spec listed `MonthViewCell` but it was never built, and a full calendar-grid layout is outside beta scope.

### C.5 `DispatchBoardPage` — Wire `viewTab` to Hook and Grid

| Property | Detail |
|:---|:---|
| **File** | `frontend/apps/web/src/features/dispatch-board/components/DispatchBoardPage.tsx` |
| **Change** | Compute `endDate` from `activeDate` + `viewTab`; pass both to `useDispatchBoard`. Pass `viewMode={viewTab}` and `dateRange={computedDateRange}` to `DispatchGrid`. |

The `getTabDays` helper is internal to `store.ts` — it is not exported. `DispatchBoardPage` needs a local helper `addDays(date, n)` (identical logic to the store's helper) to compute `endDate`. Alternatively, export `getTabDays` from `store.ts`. **Preferred**: export `getTabDays` from `store.ts` — it is pure and reusable.

Changes:
1. Export `getTabDays` from `store.ts`.
2. In `DispatchBoardPage`: compute `endDate = addDays(activeDate, getTabDays(viewTab) - 1)`.
3. Compute `dateRange: string[]` = array of `getTabDays(viewTab)` date strings starting from `activeDate`.
4. Call `useDispatchBoard(activeDate, endDate)`.
5. Pass `viewMode={viewTab}` and `dateRange={dateRange}` to `<DispatchGrid>`.

The `addDays` utility can be extracted to a shared `dateUtils.ts` within the dispatch-board feature folder, or inlined in the page. For BETA-B5, inlining is acceptable.

---

## D. API Endpoint Consumption

**The same endpoint handles all date ranges.** No new endpoint needed.

`GET /api/v1/scheduling/dispatch-board?start_date=...&end_date=...`

For multi-day views, the hook sends:
- 4-Day: `start_date = {activeDate}T00:00:00Z`, `end_date = {activeDate+3}T23:59:59Z`
- Week: `start_date = {activeDate}T00:00:00Z`, `end_date = {activeDate+6}T23:59:59Z`

**The API response does NOT change shape for wider ranges.** The `DispatchBoardResponse` schema (`start_date`, `end_date`, `techs: DispatchBoardTechGroup[]`, `unassigned`) is range-agnostic. Jobs within the range are returned under their tech group.

**Data normalization for multi-day rendering:**

The current `types-stub.ts` `DispatchBoardResponse` is a stub with a flat `jobs` array. The real API returns jobs nested under `DispatchBoardTechGroup`. The `MultiDayGrid` requires jobs filterable by date. The filtering logic is:

```typescript
// Filter jobs for a given panel date
const panelJobs = jobs.filter(job =>
  job.scheduled_start_at?.startsWith(dateStr)
);
```

This works if `jobs` is a flat array (current stub behavior). No additional normalization is required for the multi-day rendering — the flat array from the stub (or future API normalization) supports date prefix filtering.

**Companion API contract task**: The stub `DispatchBoardResponse` shape diverges from the real API schema (stub has flat `jobs` array; API has `techs[].jobs`). This mismatch should be resolved in a separate companion task (not BETA-B5) when `types-stub.ts` is deleted and replaced with generated types. BETA-B5 continues against the stub types.

---

## E. Pattern Reuse Decisions

### E.1 `DispatchGridColumn` Reuse in `MultiDayGrid`

`MultiDayGrid` reuses `DispatchGridColumn` directly. The column renders correctly with a no-op `onDrop` prop. The current `DispatchGridColumnProps.onDrop` is required — it should be made **optional** in BETA-B5:

```typescript
// Before
onDrop: (item: JobBlockDragItem, targetTechId: string | null, dropTopPx: number) => void;
// After
onDrop?: (item: JobBlockDragItem, targetTechId: string | null, dropTopPx: number) => void;
```

When `onDrop` is absent, the `useDrop` hook within `DispatchGridColumn` should be conditioned to a no-op. This makes `DispatchGridColumn` safely reusable in non-DnD contexts (multi-day panels, future mobile views).

### E.2 `JobBlock` Reuse

`JobBlock` is reused unchanged within each `DispatchGridColumn` rendered by `MultiDayGrid`. The `onSelect` callback propagates correctly. The `useDrag` inside `JobBlock` is harmless in the absence of `DndProvider` — drag events simply have no effect without the provider context. However, to avoid React DnD console warnings, `MultiDayGrid` panels should **not** include a `DndProvider` — which is correct since `DndProvider` lives in `DispatchGrid` and multi-day bypasses that wrapper.

**Resolution**: The `JobBlock` `useDrag` hook must be wrapped in a null check for the DnD context, or the `DayPanel` within `MultiDayGrid` must wrap each panel's grid area in its own `DndProvider` — but with drag disabled. **Simplest approach**: wrap `MultiDayGrid` in a `DndProvider` to satisfy the hook but omit any `useDrop` targets — blocks will be technically draggable but no drop target accepts them. This produces clean UX (drag starts but snaps back) and zero console errors.

### E.3 `MonthViewCell` — Not Reused

The FE-B4 spec listed `MonthViewCell` but it was never built. Month view is deferred (§G Decision 2). `MonthViewCell` remains unbuilt.

### E.4 No Calendar Conflict Page Reuse

The calendar conflict page (`/settings/integrations/calendar/conflicts`) uses a different visual vocabulary (field-level diff). No reuse applies to the dispatch board multi-day grid.

---

## F. Shared Module Interfaces

### F.1 `DispatchViewTab` — Already Exported

`DispatchViewTab` is already exported from `store.ts` as `"day" | "4day" | "week" | "month"`. No change needed.

### F.2 `getTabDays` — Export Addition

```typescript
// frontend/apps/web/src/features/dispatch-board/store.ts
// Add: export the helper so DispatchBoardPage can compute endDate
export function getTabDays(tab: DispatchViewTab): number {
  switch (tab) {
    case "day":   return 1;
    case "4day":  return 4;
    case "week":  return 7;
    case "month": return 30;
  }
}
```

### F.3 `MultiDayGridProps` — New Interface

```typescript
// frontend/apps/web/src/features/dispatch-board/components/MultiDayGrid.tsx
export interface MultiDayGridProps {
  /** YYYY-MM-DD strings for each panel, length 4 (4day) or 7 (week) */
  dateRange: string[];
  techs: DispatchBoardTech[];
  jobs: DispatchBoardJob[];
  onJobSelect: (jobId: string) => void;
}
```

### F.4 `DispatchGridProps` — Extended Interface

```typescript
// frontend/apps/web/src/features/dispatch-board/components/DispatchGrid.tsx
interface DispatchGridProps {
  techs: DispatchBoardTech[];
  jobs: DispatchBoardJob[];
  activeDate: string;
  onJobSelect: (jobId: string) => void;
  onMoveJob: (variables: MoveJobVariables) => void;
  isMoveJobPending?: boolean;
  // BETA-B5 additions:
  viewMode?: DispatchViewTab;  // default 'day' — backward compatible
  dateRange?: string[];         // required when viewMode is '4day' or 'week'
}
```

### F.5 `useDispatchBoard` — Updated Signature

```typescript
// frontend/apps/web/src/features/dispatch-board/hooks/useDispatchBoard.ts
export const DISPATCH_BOARD_QUERY_KEY = (startDate: string, endDate: string) =>
  ["dispatch-board", startDate, endDate] as const;

export function useDispatchBoard(startDate: string, endDate: string) {
  return useQuery({
    queryKey: DISPATCH_BOARD_QUERY_KEY(startDate, endDate),
    queryFn: () => fetchDispatchBoard(startDate, endDate),
    staleTime: 30_000,
    refetchOnWindowFocus: true,
  });
}
```

---

## G. Open Questions Resolved

### G.1 Layout Option for 4-Day and Week Views — **Option C: Side-by-Side Day Panels**

**Decision**: Each of 4 or 7 panels renders one day's worth of tech columns × time rows side-by-side.

**Rationale**:
- The PRD's canonical layout is "tech columns × time rows" — Option C preserves this per day.
- `DispatchGridColumn` uses `isoToTopPx(isoStr)` which extracts hours/minutes from the ISO timestamp — it is time-aware, not date-aware. Extending a single column to span multiple days (Option B) would require replacing the entire time-axis model.
- Option A (date-column headers with tech rows inside) is a fundamentally different layout that inverts the PRD's stated grid structure and requires all-new components.
- Option C reuses the maximum amount of existing code — only `MultiDayGrid.tsx` and `MonthDeferredState.tsx` are new files.
- Option C is the most readable: the dispatcher sees each day as a familiar Day-view slice. This matches how dispatchers think about multi-day scheduling (day-by-day, not tech-by-tech across days).

### G.2 Month View — **Deferred for Beta**

**Decision**: Month view renders `<MonthDeferredState>` — a "Month view coming soon" placeholder.

**Rationale**:
- Month view requires a 7-column × 5-row calendar grid with no time axis — architecturally distinct from the time-grid used for Day/4-Day/Week.
- FE-B4 specified `MonthViewCell` but it was never built. The component does not exist.
- The PRD's `§3.14` does not explicitly specify the Month view visual layout beyond the tab's existence.
- For beta testing with 5–10 contractors, Month view is low-priority relative to functional 4-Day and Week views.
- Explicit deferred state is preferable to a broken tab. "Coming soon" sets expectations and prevents confusion.
- Month view implementation is a well-scoped follow-on: a `MonthCalendarGrid` component with `MonthViewCell` cells, keyed to the existing `getTabDays('month')` = 30 day window.

### G.3 Drag-Drop in Multi-Day Views — **Day View Only for Beta**

**Decision**: Drag-drop (react-dnd) is restricted to Day view. Multi-day views are visually read-only.

**Rationale**:
- `handleDrop` in `DispatchGrid` uses `activeDate` (a single date string) to convert drop pixel coordinates to an ISO timestamp via `dropPxToIso(topPx, activeDate)`. This function is date-unaware — it always produces a time on `activeDate`.
- Supporting drag-drop in multi-day views would require: (a) identifying which day panel received the drop, (b) passing the panel's date to `dropPxToIso`, (c) handling cross-day drag (move job to different date), and (d) extended conflict check semantics.
- This is a significant complexity addition for beta. The PRD requires drag-drop but does not specify that it must work in all view modes simultaneously.
- Read-only multi-day views are useful for overview (is each day covered?) with editing done by switching to Day view.
- This decision is explicitly documented as an MVP constraint. Post-beta, drag-drop in 4-Day/Week is a logical extension that does not require re-architecture — the `handleDrop` function simply needs a date parameter from the panel context.

### G.4 SSE Architecture — **No Change for Multi-Day**

The SSE stream (`/api/v1/scheduling/board/stream`) is a global board event stream. Events carry `job_id` and timestamps — the handler in `useDispatchSse` invalidates the `dispatch-board` TanStack Query cache. With the new two-param query key `["dispatch-board", startDate, endDate]`, cache invalidation still works correctly — the board refetches the entire date window on any SSE event. No SSE changes are required.

---

## H. External Dependency Status

BETA-B5 is **pure frontend**. No backend changes, no new API endpoints, no schema changes.

**Assumptions the implementation depends on:**

| Assumption | Source | Risk |
|:---|:---|:---|
| `GET /api/v1/scheduling/dispatch-board` handles arbitrary date ranges | Confirmed in `openapi.json` — `start_date` and `end_date` are the only query params; no max-range constraint documented | Low |
| Response shape is consistent across date ranges | API description: "Return the dispatch board grouped payload" — no mention of range-limited behavior | Low |
| Jobs in multi-day response have `scheduled_start_at` with date prefix matching panel date | `DispatchBoardJobEntry.scheduled_start_at` is ISO datetime — date prefix extraction is reliable | Low |
| `types-stub.ts` flat `jobs` array is populated by MSW handlers for multi-day ranges | MSW handlers must be updated to return jobs spanning the full requested range, not just one day | Medium — MSW stub update is a companion task |
| `DispatchGridColumn` renders correctly with no-op `onDrop` | Confirmed — `useDrop` in the column only fires on actual HTML5 drop events, which cannot occur without a `DndProvider` | Low |

**Companion task (not BETA-B5)**: Update MSW stub handlers for the dispatch board endpoint to return multi-day data when `end_date` spans multiple days. Update `types-stub.ts` once `pnpm sync-api-types` delivers real types from `DispatchBoardJobEntry`. The stub's `DispatchBoardJob` type has UI-display fields (`title`, `customer_name`, `priority`, etc.) that don't exist in the real `DispatchBoardJobEntry` schema — this gap is a BETA-B2 scope item, not BETA-B5.

---

## I. Test Plan

**Test subfolder**: `apps/web/__tests__/batch_beta_b5/`

### I.1 Unit Tests

| Test | File | Assertion |
|:---|:---|:---|
| `useDispatchBoard` single-day range | `useDispatchBoard.test.ts` | `startDate='2026-06-04'`, `endDate='2026-06-04'` → query URL has `start_date=2026-06-04T00:00:00Z&end_date=2026-06-04T23:59:59Z` |
| `useDispatchBoard` 4-day range | `useDispatchBoard.test.ts` | `startDate='2026-06-04'`, `endDate='2026-06-07'` → query URL has `end_date=2026-06-07T23:59:59Z` |
| `useDispatchBoard` query key uniqueness | `useDispatchBoard.test.ts` | Different `endDate` values produce different TanStack query keys (no stale-cache collision) |
| `getTabDays` export | `store.test.ts` | `getTabDays('day')=1`, `getTabDays('4day')=4`, `getTabDays('week')=7`, `getTabDays('month')=30` |
| `MultiDayGrid` renders N panels | `MultiDayGrid.test.tsx` | `dateRange` of length 4 → 4 `DayPanel` headers rendered; length 7 → 7 headers |
| `MultiDayGrid` date filtering | `MultiDayGrid.test.tsx` | Job with `scheduled_start_at='2026-06-05T09:00:00Z'` appears only in the June 5 panel, not June 4 or 6 |
| `MultiDayGrid` job absent from wrong panel | `MultiDayGrid.test.tsx` | A June 4 job does not appear in the June 5 panel |
| `MonthDeferredState` renders placeholder | `MonthDeferredState.test.tsx` | Renders heading "Month view coming soon" |
| `DispatchGrid` day mode unchanged | `DispatchGrid.test.tsx` | Without `viewMode` prop (default), renders `DispatchGridColumn` components, not `MultiDayGrid` |
| `DispatchGrid` 4day mode renders MultiDayGrid | `DispatchGrid.test.tsx` | With `viewMode='4day'` and `dateRange` of length 4, renders `MultiDayGrid`, not day columns |
| `DispatchGrid` month mode renders deferred state | `DispatchGrid.test.tsx` | With `viewMode='month'`, renders `MonthDeferredState` |
| `DispatchGridColumn` with no-op `onDrop` | `DispatchGridColumn.test.tsx` | Renders without error when `onDrop` is undefined |

### I.2 Integration Tests

| Test | File | Assertion |
|:---|:---|:---|
| Tab switch 4-Day: API called with 4-day range | `DispatchBoardPage.integration.test.tsx` | Switching to "4 Day" tab triggers API call with `end_date = activeDate+3` |
| Tab switch Week: API called with 7-day range | `DispatchBoardPage.integration.test.tsx` | Switching to "Week" tab triggers API call with `end_date = activeDate+6` |
| Tab switch Month: no multi-day grid rendered | `DispatchBoardPage.integration.test.tsx` | Switching to "Month" tab renders deferred state, not a grid |
| Tab switch back to Day: grid returns to normal | `DispatchBoardPage.integration.test.tsx` | Switching from "Week" to "Day" renders `DispatchGrid` day columns, not `MultiDayGrid` |
| 4-Day grid: 4 date panels visible | `DispatchBoardPage.integration.test.tsx` | Switching to "4 Day" → 4 column headers with consecutive dates appear |
| 4-Day grid: jobs per-panel filtered correctly | `DispatchBoardPage.integration.test.tsx` | MSW returns jobs spanning 4 days → each panel shows only its own day's jobs |
| Navigate prev/next in 4-Day mode | `DispatchBoardPage.integration.test.tsx` | Clicking prev/next in 4-Day view advances `activeDate` by 4 days; grid re-renders with new 4 panels |
| SSE event triggers board refetch | `DispatchBoardPage.integration.test.tsx` | Mock SSE `job_rescheduled` event → board query invalidated and re-called (query key with start+end dates matches) |

### I.3 Regression Tests (Day View Must Not Regress)

| Test | File | Assertion |
|:---|:---|:---|
| Day view renders tech columns unchanged | `DispatchGrid.regression.test.tsx` | With `viewMode='day'` (or no prop), `DispatchGridColumn` renders for each tech + Unassigned |
| Day view drag-drop works | `DispatchGrid.regression.test.tsx` | `DndProvider` present; `handleDrop` can be triggered; `onMoveJob` called |
| Day view `ConflictPreviewPane` appears on drop | `DispatchGrid.regression.test.tsx` | Drop event → conflict pane visible |
| Day view `activeDate` used for pixel conversion | `DispatchGrid.regression.test.tsx` | `dropPxToIso` produces ISO time for `activeDate`, not a different date |

---

## Design Doc Quality Gate Checklist

- [x] Every code file referenced was actually read (not assumed)
- [x] `DispatchGrid.tsx` current props interface documented (`techs, jobs, activeDate, onJobSelect, onMoveJob, isMoveJobPending`)
- [x] `store.ts` `viewTab` type (`DispatchViewTab = "day" | "4day" | "week" | "month"`) and `getTabDays()` behavior documented
- [x] API response shape for multi-day range documented — same endpoint, `DispatchBoardResponse` with `start_date`, `end_date`, `techs: DispatchBoardTechGroup[]`, `unassigned: DispatchBoardJobEntry[]`
- [x] Layout option for 4-Day/Week chosen with explicit rationale — **Option C: side-by-side day panels**
- [x] Month view decision explicitly documented — **deferred for beta**, `<MonthDeferredState>` placeholder
- [x] Drag-drop decision explicitly documented — **Day view only for beta**; multi-day is read-only
- [x] Backward compatibility confirmed — Day view unchanged; `viewMode` defaults to `'day'`; `useDispatchBoard` Day call is identical (`endDate = startDate`)
- [x] Component changes are additive — new `viewMode`/`dateRange` props optional; new `MultiDayGrid` and `MonthDeferredState` are new files; `getTabDays` export addition only; `onDrop` made optional in `DispatchGridColumn`
