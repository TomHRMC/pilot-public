# Batch Design: FE-B30 — Dispatch Board Week + Month Views

**Batch**: FE-B30  
**Type**: Frontend only (React Engineer — `apps/web`)  
**Depends on**: UI-DS-B1 ✅  
**Engineer**: Pilot React Engineer  
**Platform**: Web only (`frontend/apps/web/`)  
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-fe-b30-design.md`  
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §Phase 1 — FE-B30 row  
**UI Spec**: `dev-docs/architecture-design/batch-designs/batch-ui-ds-b1-design-spec.md` §Surface 2 (Week) + §Surface 3 (Month)

---

## A. Input Read Summary

| Input | What Was Read | Key Finding |
|---|---|---|
| `pilot-launch-plan.md` §Phase 1 | FE-B30 scope | Week view (tech-as-column drag+drop) + Month view (calendar grid); drop 4-Day view; deprecate `DispatchGrid` |
| `batch-ui-ds-b1-design-spec.md` §Surface 2 | Week view visual spec | Tech-as-column, day-as-row CSS grid; `@dnd-kit` DnD; right-click context menu; 5-day/7-day toggle; mobile fallback |
| `batch-ui-ds-b1-design-spec.md` §Surface 3 | Month view visual spec | Redesigned calendar with Customer/Tech chip toggle; context menu on chips; month nav controls; today highlight |
| `DispatchBoardPage.tsx` | Current routing | Day → `DispatchBoardLanes`; else → `DispatchGrid` (handles week/month/4day) |
| `DispatchToolbar.tsx` | Current toolbar | VIEW_TABS: `day`, `4day`, `week`, `month`; single nav row for all views |
| `DispatchGrid.tsx` | Current grid | Routes: `"4day"/"week"` → `MultiDayGrid`; `"month"` → `MonthCalendarGrid`; `"day"` → `DispatchGridDayView` |
| `MultiDayGrid.tsx` | Existing week impl | Day panels side-by-side using `DispatchGridColumn`; read-only; `react-dnd`; **this layout does NOT match spec** |
| `MonthCalendarGrid.tsx` | Existing month impl | 30-day rolling window; `MonthViewCell` with chip max 3; no tech initials; no context menu; no chip toggle |
| `MonthViewCell.tsx` | Existing cell | Job chip shows `job.title`; no right-click; click → drill down |
| `DispatchBoardLanes.tsx` | Day view DnD | Uses `@dnd-kit/core` — installed and working |
| `types-stub.ts` | Job/Tech types | `DispatchBoardJob.tech_id`, `title`, `customer_name`, `scheduled_start_at`, `scheduled_end_at`; `DispatchBoardTech.name`, `display_color` |
| `store.ts` | Zustand state | `DispatchViewTab = "day" \| "4day" \| "week" \| "month"`; `getTabDays("week") = 7` |
| MCP: `user.display_color` | Live DB | VARCHAR nullable — confirmed present in schema |
| `dispatchBoardHandlers.ts` | Existing MSW | Has `GET /api/v1/schedule/board` + subscription tiers handlers; already registered in `index.ts` |

---

## B. No Migrations — Frontend-Only Batch

This batch is purely frontend. No backend schema changes required. The `GET /api/v1/schedule/board` endpoint already returns `techs` with `name` and `display_color`. The `PATCH /api/v1/jobs/{job_id}` endpoint (B18) already handles schedule updates.

---

## C. Execution Order

| # | Task | File(s) | Notes |
|---|---|---|---|
| 1 | Remove `"4day"` from `DispatchViewTab` + update `getTabDays` | `store.ts` | Type change — cascades to Toolbar, DispatchBoardPage, DispatchGrid |
| 2 | Update `DispatchToolbar.tsx` | `DispatchToolbar.tsx` | Remove `"4Day"` tab; add week-specific + month-specific toolbar controls |
| 3 | Create `DispatchWeekView.tsx` | `features/dispatch-board/components/DispatchWeekView.tsx` | New component per UI-DS-B1 §Surface 2 |
| 4 | Update `MonthCalendarGrid.tsx` | `features/dispatch-board/components/MonthCalendarGrid.tsx` | Redesign per UI-DS-B1 §Surface 3 |
| 5 | Update `MonthViewCell.tsx` | `features/dispatch-board/components/MonthViewCell.tsx` | Add context menu; chip display mode prop; tech initials |
| 6 | Update `DispatchBoardPage.tsx` | `features/dispatch-board/components/DispatchBoardPage.tsx` | Route `week` → `DispatchWeekView`, `month` → updated `MonthCalendarGrid`; remove `DispatchGrid` from else-branch |
| 7 | Deprecate `DispatchGrid.tsx` | `features/dispatch-board/components/DispatchGrid.tsx` | Add `@deprecated` JSDoc; not deleted (still used by some tests) |
| 8 | Extend MSW handlers | `mocks/handlers/dispatchBoardHandlers.ts` | Ensure board handler returns rich `techs[]` with `name` + `display_color` for Week view rendering |
| 9 | Integration tests | `__tests__/batch_fe_b30/*.integration.test.tsx` | 5 test files, minimum 20 tests |

---

## D. New API Interactions (Frontend Only)

### D.1 — Week view drag drop reuses existing `PATCH /api/v1/jobs/{job_id}`

The Week view drag-and-drop fires the same endpoint as `JobPropertiesPanel` and `DispatchBoardLanes`:

```
PATCH /api/v1/jobs/{job_id}
Body: { scheduled_start_at: string, scheduled_end_at: string }
```

**No new endpoint required.** The React Engineer should use `apiClient.patch()` directly (as `DispatchBoardPage.handleJobDrop` already does) OR the existing `useMoveJob` hook. Prefer `useMoveJob` for staleness-check compatibility.

### D.2 — Context menu "Job Properties" opens existing `<JobPropertiesPanel>`

No new API interaction. `JobPropertiesPanel` already handles `PATCH /api/v1/jobs/{job_id}` internally via `useUpdateJob`. The Week/Month context menu just sets `selectedJob` state in `DispatchBoardPage` to open the panel.

---

## E. Pattern Reuse Decisions

| Pattern | Applied Where | `mvp-arch.md` Reference |
|---|---|---|
| §16.2 Optimistic UI | Week view drag: job card moves to target cell immediately; reverts on PATCH error | §16.2 |
| `@dnd-kit/core` | Week view drag-and-drop — consistent with `DispatchBoardLanes` | Already installed in `apps/web/package.json` |
| §16.6 `<LoadingState>` / `<ErrorState>` | Week/Month views while board data loads | `@pilot/ui/states` |
| Reuse `JobPropertiesPanel` | Context menu "Job Properties" option in Week/Month | Already in `DispatchBoardPage` — pass `setSelectedJob` callback |
| Reuse `JobBlock` from MKT-B11-D | Week view job cards — exact same `<JobBlock>` visual, `onContextMenu` added | `DispatchBoardLanes.tsx` pattern |

---

## F. Shared Module Interfaces

### F.1 — `DispatchViewTab` type update (BREAKING — cascades to 4 files)

```typescript
// store.ts — BEFORE:
export type DispatchViewTab = "day" | "4day" | "week" | "month";

// store.ts — AFTER:
export type DispatchViewTab = "day" | "week" | "month";
```

Update `getTabDays` to remove the `"4day"` case:

```typescript
export function getTabDays(tab: DispatchViewTab): number {
  switch (tab) {
    case "day":   return 1;
    case "week":  return 7;
    case "month": return 30;
  }
}
```

**Files that reference `"4day"` — must all be updated:**
- `store.ts` — type + getTabDays
- `DispatchToolbar.tsx` — VIEW_TABS array
- `DispatchGrid.tsx` — `if (viewMode === "4day" || viewMode === "week")` condition
- `store-getTabDays.test.ts` — remove the `"4day"` test case

### F.2 — `DispatchWeekView` component props

```typescript
interface DispatchWeekViewProps {
  /** YYYY-MM-DD string for the week start (Monday or Sunday — start of active week) */
  weekStartDate: string;
  /** 5 or 7 (from 5-day/7-day toggle in toolbar) */
  daysToShow: 5 | 7;
  techs: DispatchBoardTech[];
  jobs: ScheduledJob[];
  /** Fires when user drops a job onto a new tech×day cell */
  onJobDrop: (jobId: string, newTechId: string, newDate: string, newStartTime: Date) => void;
  /** Fires when user right-clicks a job → "Job Properties" */
  onJobClick: (job: ScheduledJob) => void;
  /** Navigate to day view for the given date */
  onNavigateToDate: (dateStr: string) => void;
}
```

### F.3 — Toolbar props additions (new optional props for week/month controls)

```typescript
interface DispatchToolbarProps {
  // EXISTING props unchanged...
  viewTab: DispatchViewTab;
  activeDate: string;
  // ...

  // NEW optional props for week-specific controls:
  weekDaysToShow?: 5 | 7;              // 5-day/7-day toggle (week view only)
  onWeekDaysToggle?: (days: 5 | 7) => void;

  // NEW optional props for month-specific controls:
  chipDisplayMode?: "customer" | "tech"; // Customer/Tech toggle (month view only)
  onChipDisplayModeToggle?: (mode: "customer" | "tech") => void;
}
```

State for `weekDaysToShow` and `chipDisplayMode` lives in `DispatchBoardPage` (passed down). These are UI-only preferences, not persisted in Zustand.

### F.4 — `MonthCalendarGrid` updated props

```typescript
interface MonthCalendarGridProps {
  /** 30 YYYY-MM-DD strings (unchanged) */
  dateRange: string[];
  jobs: DispatchBoardJob[];
  techs: DispatchBoardTech[];       // NEW — for tech initials in tech chip mode
  onDrillDown: (dateStr: string) => void;
  /** NEW — controls chip label display */
  chipDisplayMode: "customer" | "tech";
  /** NEW — fires when user right-clicks a job chip → "Job Properties" */
  onJobClick?: (job: DispatchBoardJob) => void;
}
```

### F.5 — Context Menu component (inline in `DispatchWeekView` + `MonthViewCell`)

Context menu is implemented inline in each component (not a shared component) due to the different parent contexts. Both follow the same spec:

```typescript
// Triggered by onContextMenu on a job card/chip
interface ContextMenuState {
  x: number;
  y: number;
  job: DispatchBoardJob | ScheduledJob;
}
```

Menu items: "View Job" → `router.push('/jobs/{job.id}')` | "Job Properties" → `onJobClick(job)`

Menu closes on: `Escape`, click outside, any item click.

---

## G. Open Questions Resolved

| Question | Resolution |
|---|---|
| Does removing `"4day"` break any existing tests? | Yes — `store-getTabDays.test.ts` has a `"4day"` test case that must be removed. `DispatchGrid.test.tsx` and `MultiDayGrid.test.tsx` still compile but may have `"4day"` references — engineer must search for all `"4day"` string literals and remove them. |
| What happens to `DispatchGrid.tsx` and `MultiDayGrid.tsx`? | Both get a `@deprecated` JSDoc comment but are NOT deleted — existing tests reference them. After FE-B30, `DispatchBoardPage` no longer imports `DispatchGrid`. The files remain but are dead code. |
| Does the Week view use `@dnd-kit` or `react-dnd`? | **`@dnd-kit/core`** — already installed in `apps/web`. The existing `DispatchGrid` day view uses `react-dnd` (HTML5Backend) but `DispatchBoardLanes` already migrated to `@dnd-kit`. Week view follows `DispatchBoardLanes` pattern. |
| Week view drop payload — does it use `useMoveJob` or raw `apiClient.patch()`? | **Use `apiClient.patch()`** directly (same as `DispatchBoardPage.handleJobDrop`), then invalidate board query. Simpler than `useMoveJob` which requires `expected_updated_at` for the 409-staleness pattern. Week view DnD is a reschedule, not a reassign — staleness check is lower stakes. |
| What is the week start day? | **Monday** — standard work week. `weekStartDate` is always the Monday of the active week. Computing Sunday-based week would confuse contractors. `activeDate` from the store is used to derive Monday: `startOfWeek(activeDate, { weekStartsOn: 1 })`. |
| How does "This Week" button work in toolbar? | Sets `activeDate` to today's Monday via `navigateToToday()`. The engineer can compute Monday from today using: `const d = new Date(today); d.setDate(d.getDate() - ((d.getDay() + 6) % 7));`. |
| How does `DispatchBoardPage.navigatePrev/Next` work for week view? | `getTabDays("week") = 7`. The existing `navigatePrev` subtracts `getTabDays(viewTab)` days from `activeDate`. For week view: -7 days = previous week, +7 days = next week. No change needed to the store nav logic. |
| Month view toolbar controls (prev/next month): | The existing `navigatePrev` subtracts 30 days from `activeDate` (since `getTabDays("month") = 30`). This is close enough for MVP — "previous month" navigates ~30 days back. Not calendar-precise but acceptable. No store changes required. |
| Context menu in tests — how to test? | `fireEvent.contextMenu(element)` in Vitest + testing-library triggers `onContextMenu`. Check that menu items appear in the DOM. |
| Week view — what constitutes "capacity exceeded" for a tech/day cell? | No formal capacity limit in the data model. Per UI-DS-B1 §Surface 2: show the "capacity exceeded" chip when a cell has 4+ jobs for the same tech on the same day. This is a client-side threshold: `jobs.filter(j => j.tech_id === tech.id && j.scheduled_start_at.startsWith(dateStr)).length >= 4`. |
| Should the Week view use the existing `ScheduledJob` type from `DispatchBoardLanes`? | Yes — import `ScheduledJob` from `DispatchBoardLanes.tsx`. The week view receives the same `ScheduledJob[]` array from `DispatchBoardPage`. |

---

## H. Surface Mockup Reference

| Surface | Spec Location | Platform | Scope in FE-B30 |
|---|---|---|---|
| Invoice Builder `/invoices/new` | UI-DS-B1 §Surface 1 | Web only | ❌ FE-B29 complete |
| Dispatch Board Week View | UI-DS-B1 §Surface 2 | Web only | ✅ Full implementation |
| Dispatch Board Month View | UI-DS-B1 §Surface 3 | Web only | ✅ Full implementation |
| `JobPropertiesPanel` Save Button | UI-DS-B1 §Surface 4 | Web only | ❌ FE-B27 complete |

**Critical spec details for Week View (UI-DS-B1 §Surface 2):**
- Grid layout: **row = day, column = tech** (NOT the existing `MultiDayGrid` layout which is day-as-column)
- Sticky row header (day + date): `min-w-[96px]`; sticky tech column headers
- Min column width: `min-w-[160px]` per tech
- `overflow-x: auto` on board wrapper — horizontal scroll when too narrow
- Jobs within a cell ordered by `scheduled_start_at` ascending
- Each job shows start time label above `<JobBlock>` (reused from Day view)
- Mobile fallback `< 768px`: "Week view is available on desktop" + "View Today" button

**Critical spec details for Month View (UI-DS-B1 §Surface 3):**
- Chip display toggle: "Customer" (default) shows `job.customer_name`; "Tech" shows tech initials + `job.title`
- Tech initials mini-avatar: `w-4 h-4 rounded-full bg-brand-100 text-brand-700 text-[10px] font-bold`
- Max 2 chips per cell + "+N more" (change from current 3-chip limit → 2-chip per spec)
- "+N more" click → navigate to Day view for that date
- Context menu on chips: right-click → "View Job" | "Job Properties"

---

## I. Component Manifest

| Component / File | Path | New or Modified | Purpose |
|---|---|---|---|
| `store.ts` | `features/dispatch-board/store.ts` | **Modified** | Remove `"4day"` from `DispatchViewTab`; update `getTabDays` |
| `DispatchToolbar.tsx` | `features/dispatch-board/components/DispatchToolbar.tsx` | **Modified** | Remove "4 Day" tab; add week/month view-specific controls |
| `DispatchWeekView.tsx` | `features/dispatch-board/components/DispatchWeekView.tsx` | **New** | Full Week view per UI-DS-B1 §Surface 2 |
| `MonthCalendarGrid.tsx` | `features/dispatch-board/components/MonthCalendarGrid.tsx` | **Modified** | Add `chipDisplayMode` prop + context menu wiring |
| `MonthViewCell.tsx` | `features/dispatch-board/components/MonthViewCell.tsx` | **Modified** | Add context menu; tech mode chip; reduce max chips to 2 |
| `DispatchBoardPage.tsx` | `features/dispatch-board/components/DispatchBoardPage.tsx` | **Modified** | Route `week` → `DispatchWeekView`; remove `DispatchGrid` from non-day path |
| `DispatchGrid.tsx` | `features/dispatch-board/components/DispatchGrid.tsx` | **Modified (deprecated)** | Add `@deprecated` JSDoc; not imported by DispatchBoardPage anymore |
| `store-getTabDays.test.ts` | `features/dispatch-board/store-getTabDays.test.ts` | **Modified** | Remove `"4day"` test case |
| `dispatchBoardHandlers.ts` | `mocks/handlers/dispatchBoardHandlers.ts` | **Modified** | Enrich `techs[]` fixture with `name` + `display_color` |
| Integration tests | `__tests__/batch_fe_b30/` | **New** | 5 test files, minimum 20 tests |

**Integration test files:**

| Test File | Surface Covered | Min Tests |
|---|---|---|
| `dispatch_week_view_render.integration.test.tsx` | Week view renders; day/tech headers visible; mobile fallback | 4 |
| `dispatch_week_view_dnd.integration.test.tsx` | Job drop fires PATCH with correct date+time+tech; optimistic reorder | 4 |
| `dispatch_week_month_context_menu.integration.test.tsx` | Right-click on job → context menu → "View Job" navigates; "Job Properties" fires onJobClick | 4 |
| `dispatch_month_view_chips.integration.test.tsx` | Customer mode shows customer_name; Tech mode shows initials; overflow "+N more" | 4 |
| `dispatch_toolbar_4day_removed.integration.test.tsx` | "4 Day" tab absent; "Week" tab present; week toolbar controls visible when week active | 4 |

---

## J. `DispatchBoardPage` Routing After FE-B30

```typescript
// DispatchBoardPage.tsx — updated routing (replacing the current if/else block)
{viewTab === "day" && (
  <DispatchBoardLanes
    date={new Date(activeDate + "T12:00:00")}
    laneCount={laneCount}
    jobs={visibleJobs}
    onJobClick={handleJobClick}
    onJobDrop={handleJobDrop}
    onUpgradeClick={handleUpgradeClick}
  />
)}
{viewTab === "week" && (
  <DispatchWeekView
    weekStartDate={activeDate}
    daysToShow={weekDaysToShow}
    techs={board?.techs ?? []}
    jobs={visibleJobs}
    onJobDrop={handleWeekJobDrop}
    onJobClick={handleJobClick}
    onNavigateToDate={(dateStr) => {
      setViewTab("day");
      navigateToDate(dateStr); // new store action or setActiveDate
    }}
  />
)}
{viewTab === "month" && (
  <MonthCalendarGrid
    dateRange={dateRange}
    jobs={board?.jobs ?? []}
    techs={board?.techs ?? []}
    onDrillDown={(dateStr) => {
      setViewTab("day");
      // setActiveDate is available from useDispatchBoardStore
    }}
    chipDisplayMode={chipDisplayMode}
    onJobClick={handleJobClick}
  />
)}
```

**Note**: `navigateToDate` is not currently in the store. The React Engineer should use the existing `setActiveDate` action directly from the store in the drill-down callbacks.

---

*Design doc authored: 2026-07-12 | FE-B30 depends on UI-DS-B1 ✅ | Background-Sync-B1 follows*
