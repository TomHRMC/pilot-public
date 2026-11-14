# Implementation Prompt: FE-B30 — Dispatch Board Week + Month Views

**Mode**: Pilot React Engineer  
**Batch**: FE-B30  
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §Phase 1 — FE-B30 row  
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-fe-b30-design.md`  
**UI Spec**: `dev-docs/architecture-design/batch-designs/batch-ui-ds-b1-design-spec.md` §Surface 2 + §Surface 3  
**Estimated session**: 5–7 hours  
**Platform**: Web only (`apps/web`)  
**Backend companion**: None — all endpoints already exist

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-react-engineer/react-engineer-rules.md`** — in full
- **`dev-docs/architecture-design/batch-designs/batch-fe-b30-design.md`** — every section (A–J)
- **`dev-docs/architecture-design/batch-designs/batch-ui-ds-b1-design-spec.md` §Surface 2 + §Surface 3** — the approved visual spec

**Critical rules for this batch:**

- **Rule 1.1**: Before writing any hook or API call, verify the endpoint exists in `backend/openapi_schema_map.md`. For FE-B30 this is `PATCH /api/v1/jobs/{job_id}` — already confirmed, but re-verify.
- **Rule 2**: All API calls use `apiClient` from `@pilot/shared-api`. `fetch()` is permanently banned.
- **Rule 7**: Check `packages/ui/src/index.ts` before creating any component — `<LoadingState>`, `<ErrorState>`, `<EmptyState>` are already available.
- **Rule 8**: Do NOT add any new npm dependencies. `@dnd-kit/core` and `@dnd-kit/utilities` are already installed in `apps/web/package.json` (added by MKT-B11-D). Verify with `grep "@dnd-kit" apps/web/package.json`.
- **Rule 9**: Route files are thin server components — `DispatchBoardPage` is a feature component, not a route file. No change to the dispatch route file needed.
- **Rule 10**: Fix any failing test before declaring done — including the `store-getTabDays.test.ts` `"4day"` test that FE-B30 intentionally removes.

---

## Design Decisions (Do Not Re-Litigate)

From Design Doc §G — these decisions are final:

| Decision | Outcome | Rationale |
|---|---|---|
| Week view layout | **Row = day, column = tech** — NOT the old `MultiDayGrid` layout which is day-as-column | UI-DS-B1 §Surface 2 spec |
| DnD library for Week view | **`@dnd-kit/core`** — consistent with `DispatchBoardLanes`; NOT `react-dnd` | Already installed |
| `DispatchGrid.tsx` fate | **Deprecated (not deleted)** — add `@deprecated` JSDoc; `DispatchBoardPage` no longer imports it | Some tests still reference it |
| `MultiDayGrid.tsx` fate | **Deprecated (not deleted)** — same rationale | Avoid breaking test references |
| `"4day"` tab removal | **Removed** — `DispatchViewTab` becomes `"day" \| "week" \| "month"` | UI-DS-B1 specifies 3 tabs only |
| Week drag drop payload | **`apiClient.patch()` directly** — not `useMoveJob` | Simpler; reschedule only (no reassign in week DnD) |
| Month view chip max | **2 chips** + "+N more" (down from current 3) | UI-DS-B1 §Surface 3 spec |
| Week start day | **Monday** | Standard work week for contractors |
| "Capacity exceeded" threshold | **4+ jobs** for same tech on same day | Design doc §G |
| `store.setActiveDate` | Use directly for drill-down navigation (no new store action needed) | Design doc §J |

---

## Pre-Work: Establish Regression Baseline

Before touching any file:

```bash
cd <repo>/frontend
pnpm --filter web test 2>&1 | tail -5
```

Record the exact test count. Note: `store-getTabDays.test.ts` currently has a `"4day"` test case — this test **will intentionally fail** after STEP 1. That is expected and correct. Fix it in STEP 1.

---

## Pre-Work: Sync API Types

```bash
cd <repo>/frontend
pnpm sync-api-types
```

---

## Pre-Work: Verify Endpoints

```bash
# Confirm PATCH /api/v1/jobs/{job_id} is live (FE-B30 week view DnD uses this)
grep -A 4 "PATCH /api/v1/jobs" backend/openapi_schema_map.md

# Confirm @dnd-kit is installed
grep "@dnd-kit" frontend/apps/web/package.json
```

**Verified endpoints for this batch:**

| Hook / Call | Endpoint | Verified |
|---|---|---|
| Week DnD drop | `PATCH /api/v1/jobs/{job_id}` | ✅ B18 — confirmed in openapi_schema_map.md |
| Board data | `GET /api/v1/schedule/board` | ✅ Existing MSW handler |

---

## Pre-Work: Read These Source Files

Read each of these with `read_file` before writing any code:

```
# Dispatch board files to modify:
frontend/apps/web/src/features/dispatch-board/store.ts
frontend/apps/web/src/features/dispatch-board/components/DispatchToolbar.tsx
frontend/apps/web/src/features/dispatch-board/components/DispatchBoardPage.tsx
frontend/apps/web/src/features/dispatch-board/components/DispatchBoardLanes.tsx   ← @dnd-kit pattern to follow
frontend/apps/web/src/features/dispatch-board/components/MonthCalendarGrid.tsx
frontend/apps/web/src/features/dispatch-board/components/MonthViewCell.tsx
frontend/apps/web/src/features/dispatch-board/components/JobBlock.tsx             ← reuse in week view
frontend/apps/web/src/features/dispatch-board/components/JobPropertiesPanel.tsx  ← understand props for context menu

# Types:
frontend/apps/web/src/features/dispatch-board/types-stub.ts

# MSW handlers:
frontend/apps/web/src/mocks/handlers/dispatchBoardHandlers.ts
frontend/apps/web/src/mocks/handlers/index.ts

# Test file to fix:
frontend/apps/web/src/features/dispatch-board/store-getTabDays.test.ts
```

Also run:

```bash
# Find all files referencing "4day" — must remove from each
grep -r '"4day"' frontend/apps/web/src --include="*.ts" --include="*.tsx" -l

# Find all dispatch board test files
find frontend/apps/web/src -path "*dispatch-board*" -name "*.test.*"
```

---

## Context: What This Batch Does

FE-B30 replaces the existing `MultiDayGrid` week view and upgrades the Month view to match the UI-DS-B1 spec.

| Step | What Changes |
|---|---|
| STEP 1 | Remove `"4day"` from `DispatchViewTab`; update `getTabDays`; fix `store-getTabDays.test.ts` |
| STEP 2 | Update `DispatchToolbar` — remove 4-Day tab; add week + month specific controls |
| STEP 3 | Create `DispatchWeekView.tsx` — new tech-as-column week grid with `@dnd-kit` DnD |
| STEP 4 | Update `MonthCalendarGrid.tsx` + `MonthViewCell.tsx` — chip display toggle, context menu, 2-chip max |
| STEP 5 | Update `DispatchBoardPage.tsx` — route `week` → `DispatchWeekView`, `month` → updated grid |
| STEP 6 | Deprecate `DispatchGrid.tsx` + `MultiDayGrid.tsx` |
| STEP 7 | Enrich MSW board handler with `name` + `display_color` on techs |
| STEP 8 | Write 5 integration test files, minimum 20 tests |

---

## STEP 1 — Remove `"4day"` from Store

**File**: `frontend/apps/web/src/features/dispatch-board/store.ts`

**Read first**: The full file.

```typescript
// BEFORE:
export type DispatchViewTab = "day" | "4day" | "week" | "month";

// AFTER:
export type DispatchViewTab = "day" | "week" | "month";

// Update getTabDays — remove "4day" case:
export function getTabDays(tab: DispatchViewTab): number {
  switch (tab) {
    case "day":   return 1;
    case "week":  return 7;
    case "month": return 30;
  }
}
```

**Fix the test immediately:**

**File**: `frontend/apps/web/src/features/dispatch-board/store-getTabDays.test.ts`

Remove the `it("4day tab returns 4", ...)` test case. Verify the remaining 3 tests still pass.

**Search and fix all `"4day"` string literals:**

```bash
grep -r '"4day"' frontend/apps/web/src --include="*.ts" --include="*.tsx"
```

Fix every file that appears — typically `DispatchGrid.tsx` has `viewMode === "4day"` conditions that must be updated.

**Run after STEP 1:**

```bash
cd <repo>/frontend
npx vitest run apps/web/src/features/dispatch-board/store-getTabDays.test.ts 2>&1 | tail -6
```

---

## STEP 2 — Update `DispatchToolbar.tsx`

**File**: `frontend/apps/web/src/features/dispatch-board/components/DispatchToolbar.tsx`

**Read first**: The full current file to understand existing structure.

**Changes:**

1. Update `VIEW_TABS` array — remove `"4day"` entry:
```typescript
const VIEW_TABS: Array<{ value: DispatchViewTab; label: string }> = [
  { value: "day",   label: "Day"   },
  { value: "week",  label: "Week"  },
  { value: "month", label: "Month" },
];
```

2. Add new optional props to `DispatchToolbarProps`:
```typescript
// Week-specific:
weekDaysToShow?: 5 | 7;
onWeekDaysToggle?: (days: 5 | 7) => void;
// Month-specific:
chipDisplayMode?: "customer" | "tech";
onChipDisplayModeToggle?: (mode: "customer" | "tech") => void;
```

3. Render week-specific controls when `viewTab === "week"`:
```
< Prev Week   Week of Jul 14 – Jul 18   Next Week >   [ This Week ]   [ 5-day / 7-day ]
```

The week label format: compute start and end of the week from `activeDate`. Use the existing `formatDisplayDate` function or create an inline helper. Show `"Week of Mon Jul 14 – Fri Jul 18"` (5-day) or `"Mon Jul 14 – Sun Jul 20"` (7-day).

"This Week" button: calls `onNavigateToToday()` which resets `activeDate` to today. Since `getTabDays("week") = 7`, the board will then show today's week.

5-day / 7-day pill toggle (only shown when `viewTab === "week"`):
```
Outer: bg-neutral-100 rounded-md p-0.5 inline-flex ml-2
Active pill: bg-white shadow-sm rounded px-2.5 py-1 text-caption font-medium text-neutral-900
Inactive: px-2.5 py-1 text-caption font-medium text-neutral-500
```

4. Render month-specific controls when `viewTab === "month"`:
```
< Prev Month   July 2026   Next Month >   [ Today ]   [ Customer | Tech ]
```

Customer/Tech chip toggle (only shown when `viewTab === "month"`): same pill toggle style as 5-day/7-day.

> **Important**: The toolbar does NOT own week/month state. `weekDaysToShow` and `chipDisplayMode` are passed as props from `DispatchBoardPage`. The toolbar just renders the controls and fires the callbacks.

---

## STEP 3 — Create `DispatchWeekView.tsx`

**File**: `frontend/apps/web/src/features/dispatch-board/components/DispatchWeekView.tsx`

**Read first**: `DispatchBoardLanes.tsx` (for `@dnd-kit` pattern), `JobBlock.tsx` (for job card reuse), `types-stub.ts`.

This is the main work of the batch. Implement per **UI-DS-B1 §Surface 2** exactly.

### Grid structure (tech-as-column, day-as-row)

```
┌──────────────┬──────────────────┬──────────────────┐
│ (sticky col) │  Jake R. [JR]    │  Maria S. [MS]   │
│              │  avatar          │  avatar          │
├──────────────┼──────────────────┼──────────────────┤
│ Mon Jul 14   │  [jobs for Jake  │  [jobs for Maria │
│  (sticky row)│   on Mon]        │   on Mon]        │
├──────────────┼──────────────────┼──────────────────┤
│ Tue Jul 15   │  ...             │  ...             │
└──────────────┴──────────────────┴──────────────────┘
```

Use CSS Grid or `<table>` for layout. Ensure:
- Row header (day + date) is sticky left: `sticky left-0 z-10 bg-white min-w-[96px]`
- Tech column headers are sticky top (in the overflow scroll container)
- Min column width per tech: `min-w-[160px]`
- Board wrapper: `overflow-x-auto` (horizontal scroll when narrow)

### Week start computation

```typescript
function getMondayOf(dateStr: string): string {
  const d = new Date(dateStr + "T12:00:00");
  const day = d.getDay(); // 0=Sun, 1=Mon...
  const diff = (day + 6) % 7; // days since Monday
  d.setDate(d.getDate() - diff);
  return d.toISOString().slice(0, 10);
}
```

The `weekStartDate` prop from `DispatchBoardPage` is `activeDate` (which may be any day in the week). `DispatchWeekView` computes Monday internally using this helper.

### Days to display

`daysToShow` prop: `5` (Mon–Fri) or `7` (Mon–Sun).

```typescript
function getWeekDates(mondayStr: string, daysToShow: 5 | 7): string[] {
  return Array.from({ length: daysToShow }, (_, i) => {
    const d = new Date(mondayStr + "T12:00:00");
    d.setDate(d.getDate() + i);
    return d.toISOString().slice(0, 10);
  });
}
```

### Jobs per cell

Filter `jobs` array for a given tech + date:

```typescript
const cellJobs = jobs.filter(
  (j) =>
    j.tech_id === tech.id &&
    j.scheduled_start_at.startsWith(dateStr),
);
// Sort by scheduled_start_at ascending
cellJobs.sort((a, b) =>
  a.scheduled_start_at.localeCompare(b.scheduled_start_at),
);
```

Empty cells (no jobs): `border border-dashed border-neutral-200 rounded bg-neutral-50/50`

### Job display in cell

Each job renders:
1. Start time label: `text-caption text-neutral-500 font-medium mb-0.5` — e.g., `"8:00 AM"`
2. `<JobBlock>` with `onContextMenu` handler added

However, `JobBlock` is designed for the vertical time axis (with `topPx` + `heightPx`). **Do not reuse `JobBlock` directly** — it uses absolute positioning. In the week view, jobs stack vertically in a flex column. Create an inline job card for the week view cell:

```typescript
// Simple week job card (NOT the absolute-positioned JobBlock):
function WeekJobCard({
  job,
  tech,
  onContextMenu,
  onClick,
}: {
  job: ScheduledJob;
  tech: DispatchBoardTech | null;
  onContextMenu: (e: React.MouseEvent, job: ScheduledJob) => void;
  onClick: (job: ScheduledJob) => void;
}) {
  // tech color left border (data-driven, the one legitimate inline style)
  // Exactly the same visual treatment as JobBlock but in flex layout
  // ...
}
```

### `@dnd-kit` drag-and-drop

Use `DndContext` wrapping the week grid. Job cards use `useDraggable`; day cells use `useDroppable`.

```typescript
// DragOverlay ghost card:
// border border-brand-400 rounded px-3 py-2 bg-white shadow-lg text-caption font-medium text-brand-700 opacity-90 pointer-events-none

// Hovering valid drop target cell:
// bg-brand-50/40 (transition-colors)

// Hovering over-capacity cell (4+ jobs):
// bg-fault-50/40 cursor-not-allowed
```

Drop payload fires `onJobDrop(jobId, newTechId, newDate, new Date(startTimeApprox))`. Since the week view doesn't have a time axis, use `08:00:00` as a sensible default drop time when no time can be derived from drop position:

```typescript
// On drop: compute new scheduled_start_at
const newStartISO = `${newDateStr}T08:00:00.000Z`;
const originalDurationMs = new Date(job.scheduled_end_at).getTime() - new Date(job.scheduled_start_at).getTime();
const newEndISO = new Date(new Date(newStartISO).getTime() + originalDurationMs).toISOString();

// Fire PATCH directly:
await apiClient.patch(`/api/v1/jobs/${jobId}`, {
  scheduled_start_at: newStartISO,
  scheduled_end_at: newEndISO,
});
// Then invalidate board query via queryClient.invalidateQueries({ queryKey: ["dispatchBoard"] })
```

### Capacity exceeded

When a cell already has 4+ jobs AND a job is being dragged over it:
- Cell bg: `bg-fault-50/40 border-fault-200`
- Show chip: `absolute top-1 right-1 bg-fault-100 text-fault-700 text-caption rounded-full px-2 py-0.5 font-medium` — "Capacity exceeded"
- Block the drop — do NOT call `onJobDrop`

### Context menu

Right-click on a week job card opens a context menu:

```typescript
// State:
const [contextMenu, setContextMenu] = useState<{ x: number; y: number; job: ScheduledJob } | null>(null);

// Handler:
const handleContextMenu = (e: React.MouseEvent, job: ScheduledJob) => {
  e.preventDefault();
  setContextMenu({ x: e.clientX, y: e.clientY, job });
};
```

Menu (fixed position at cursor):
```html
<div role="menu" style={{ position: "fixed", top: y, left: x }} className="bg-white border border-neutral-200 shadow-lg rounded-md py-1 z-50">
  <button role="menuitem" onClick={() => router.push(`/jobs/${job.id}`)}>View Job</button>
  <button role="menuitem" onClick={() => { onJobClick(job); setContextMenu(null); }}>Job Properties</button>
</div>
```

Close on: `Escape` keydown on `document`, click outside.

### Mobile fallback (< 768px)

```typescript
// Detect mobile with a useMediaQuery hook or CSS:
<div className="hidden md:block">
  {/* Full week grid */}
</div>
<div className="md:hidden flex flex-col items-center justify-center py-12 text-neutral-600 text-sm text-center">
  <p>Week view is available on desktop.</p>
  <button
    type="button"
    className="mt-3 px-4 py-2 border border-brand-200 bg-brand-50 text-brand-700 text-sm font-medium rounded-md hover:bg-brand-100"
    onClick={() => { onViewTabChange("day"); onNavigateToDate(new Date().toISOString().slice(0, 10)); }}
  >
    View Today
  </button>
</div>
```

> The `onNavigateToDate` fires `setActiveDate(dateStr)` in `DispatchBoardPage`.

---

## STEP 4 — Update `MonthCalendarGrid.tsx` + `MonthViewCell.tsx`

### `MonthCalendarGrid.tsx`

**File**: `frontend/apps/web/src/features/dispatch-board/components/MonthCalendarGrid.tsx`

Add new props per design doc §F.4:
- `techs: DispatchBoardTech[]` — passed through to `MonthViewCell` for tech mode chips
- `chipDisplayMode: "customer" | "tech"` — passed through to each cell
- `onJobClick?: (job: DispatchBoardJob) => void` — passed through for context menu

Pass these through to each `<MonthViewCell>` instance.

### `MonthViewCell.tsx`

**File**: `frontend/apps/web/src/features/dispatch-board/components/MonthViewCell.tsx`

**Read first**: The current file in full.

**Changes:**

1. Add new props: `chipDisplayMode: "customer" | "tech"`, `techs: DispatchBoardTech[]`, `onJobClick?: (job: DispatchBoardJob) => void`

2. **Change max chips from 3 → 2** per spec:
```typescript
// BEFORE: const visibleJobs = jobs.length > 3 ? jobs.slice(0, 2) : jobs.slice(0, 3);
// AFTER:
const visibleJobs = jobs.slice(0, 2);
const overflowCount = jobs.length > 2 ? jobs.length - 2 : 0;
```

3. **Chip label per mode:**

```typescript
// customer mode (default):
<span className="flex-1 truncate">{job.customer_name}</span>

// tech mode:
const tech = techs.find(t => t.id === job.tech_id);
const initials = tech?.name.split(" ").map(n => n[0]).join("").slice(0, 2).toUpperCase() ?? "?";
<>
  <span className="w-4 h-4 rounded-full bg-brand-100 text-brand-700 text-[10px] font-bold flex items-center justify-center flex-shrink-0">
    {initials}
  </span>
  <span className="flex-1 truncate">{job.title ?? job.id.slice(0, 8)}</span>
</>
```

4. **Context menu on chip right-click:**

Same pattern as Week view — `useState` for `{ x, y, job }`, fixed-position menu, close on Escape + outside click. Menu items: "View Job" → navigate; "Job Properties" → `onJobClick(job)`.

5. **Today cell styling** (per UI-DS-B1 §Surface 3 §Today Highlight):
```
Cell: bg-brand-50 ring-2 ring-brand-200 ring-inset
Day number: text-brand-600 font-bold text-sm
```

6. **Job count pill** (add if not already present):
```typescript
{jobs.length > 0 && (
  <div className="inline-flex items-center bg-brand-50 text-brand-600 text-caption font-medium rounded-full px-2 py-0.5 mb-1">
    ● {jobs.length} job{jobs.length !== 1 ? "s" : ""}
  </div>
)}
```

---

## STEP 5 — Update `DispatchBoardPage.tsx`

**File**: `frontend/apps/web/src/features/dispatch-board/components/DispatchBoardPage.tsx`

**Read first**: The full current file.

**Changes:**

1. Add local state for new controls:
```typescript
const [weekDaysToShow, setWeekDaysToShow] = useState<5 | 7>(5);
const [chipDisplayMode, setChipDisplayMode] = useState<"customer" | "tech">("customer");
```

2. Add `handleWeekJobDrop` handler:
```typescript
const handleWeekJobDrop = useCallback(
  async (jobId: string, newTechId: string, newDate: string, newStartTime: Date) => {
    const job = visibleJobs.find((j) => j.id === jobId);
    if (!job) return;
    const durationMs =
      new Date(job.scheduled_end_at).getTime() -
      new Date(job.scheduled_start_at).getTime();
    const newEndISO = new Date(newStartTime.getTime() + durationMs).toISOString();
    await apiClient.patch(`/api/v1/jobs/${jobId}`, {
      scheduled_start_at: newStartTime.toISOString(),
      scheduled_end_at: newEndISO,
    });
    // Invalidate board data — use queryClient from useQueryClient()
    void queryClient.invalidateQueries({ queryKey: ["dispatchBoard"] });
  },
  [visibleJobs],
);
```

> Add `const queryClient = useQueryClient();` at top of component.

3. Pass new props to `DispatchToolbar`:
```typescript
<DispatchToolbar
  viewTab={viewTab}
  activeDate={activeDate}
  sseConnected={sseConnected}
  lastBoardFetch={lastBoardFetch}
  onViewTabChange={setViewTab}
  onNavigatePrev={navigatePrev}
  onNavigateNext={navigateNext}
  onNavigateToToday={navigateToToday}
  weekDaysToShow={weekDaysToShow}
  onWeekDaysToggle={setWeekDaysToShow}
  chipDisplayMode={chipDisplayMode}
  onChipDisplayModeToggle={setChipDisplayMode}
/>
```

4. Replace multi-view routing per design doc §J:

```typescript
{/* Day view */}
{viewTab === "day" && (
  <DispatchBoardLanes ... />
)}

{/* Week view — NEW */}
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
      setActiveDate(dateStr); // from useDispatchBoardStore
    }}
  />
)}

{/* Month view — UPDATED */}
{viewTab === "month" && (
  <MonthCalendarGrid
    dateRange={dateRange}
    jobs={board?.jobs ?? []}
    techs={board?.techs ?? []}
    onDrillDown={(dateStr) => {
      setActiveDate(dateStr);
      setViewTab("day");
    }}
    chipDisplayMode={chipDisplayMode}
    onJobClick={handleJobClick}
  />
)}
```

Remove the old `DispatchGrid` else-branch. Import `DispatchWeekView`.

5. Remove the `import { DispatchGrid }` import (it's deprecated in this batch).

---

## STEP 6 — Deprecate `DispatchGrid.tsx` + `MultiDayGrid.tsx`

**File**: `frontend/apps/web/src/features/dispatch-board/components/DispatchGrid.tsx`

Add at the top of the file, above the existing JSDoc:

```typescript
/**
 * @deprecated FE-B30 (2026-07-12): DispatchBoardPage no longer uses DispatchGrid for
 * week/month views. Week → DispatchWeekView; Month → MonthCalendarGrid (direct).
 * This file is kept to avoid breaking existing tests.
 * Do not use in new code.
 */
```

**File**: `frontend/apps/web/src/features/dispatch-board/components/MultiDayGrid.tsx`

Same pattern — add `@deprecated` JSDoc at the top.

---

## STEP 7 — Enrich MSW Board Handler

**File**: `frontend/apps/web/src/mocks/handlers/dispatchBoardHandlers.ts`

**Read first**: The current file.

The Week view renders tech column headers with `tech.name` and initials from `tech.name`. Ensure the `GET /api/v1/schedule/board` mock response includes realistic `techs` data:

```typescript
const MOCK_TECHS = [
  {
    id: "tech-00000001-0000-0000-0000-000000000001",
    tech_id: "tech-00000001-0000-0000-0000-000000000001",
    name: "Jake Rodriguez",
    display_color: "#3B82F6",
    avatar_url: null,
  },
  {
    id: "tech-00000002-0000-0000-0000-000000000002",
    tech_id: "tech-00000002-0000-0000-0000-000000000002",
    name: "Maria Santos",
    display_color: "#10B981",
    avatar_url: null,
  },
];
```

Verify the existing handler already returns `techs` in the response shape. If it returns an empty array or stub data without `name`, update the fixture.

> **Do NOT add a new handler file.** Extend the existing `dispatchBoardHandlers.ts`.

---

## STEP 8 — Integration Tests

**Folder**: `frontend/apps/web/src/__tests__/batch_fe_b30/`

Create 5 test files. Minimum 20 tests total. Use `vi.mock("next/navigation", ...)` in all files.

### File 1: `dispatch_toolbar_4day_removed.integration.test.tsx`

```typescript
// Tests:
// 1. "4 Day" tab is NOT in the rendered toolbar
// 2. "Day", "Week", "Month" tabs are present
// 3. Week-specific controls appear when viewTab="week" is set
// 4. Month-specific controls (chip toggle) appear when viewTab="month" is set
```

### File 2: `dispatch_week_view_render.integration.test.tsx`

```typescript
// Tests:
// 1. Week view renders with tech column headers visible (Jake Rodriguez, Maria Santos)
// 2. Day row headers show (Mon, Tue, Wed, Thu, Fri for 5-day mode)
// 3. Jobs render in correct cells (tech × date)
// 4. Mobile fallback renders "Week view is available on desktop" (mock viewport < 768)
```

MSW handler: provide board response with `MOCK_TECHS` + 2 jobs on different dates.

### File 3: `dispatch_week_view_dnd.integration.test.tsx`

```typescript
// Tests:
// 1. Dragging a job and dropping fires apiClient.patch with correct job_id
// 2. Dropped job appears in destination cell (optimistic update)
// 3. Dropping on over-capacity cell (4+ jobs) does NOT fire PATCH
// 4. Context menu right-click shows "View Job" and "Job Properties" items
```

### File 4: `dispatch_week_month_context_menu.integration.test.tsx`

```typescript
// Tests:
// 1. Right-click on Week view job card → context menu appears
// 2. "View Job" menu item fires router.push("/jobs/{id}")
// 3. Right-click on Month view chip → context menu appears
// 4. Pressing Escape closes the context menu
```

### File 5: `dispatch_month_view_chips.integration.test.tsx`

```typescript
// Tests:
// 1. Customer mode (default) shows customer_name in chips
// 2. Tech mode shows tech initials + job title
// 3. Overflow: 3 jobs in a cell → 2 chips + "+1 more" shown
// 4. Today cell has brand-50 background + brand-600 day number
```

**QueryClient + MSW setup (all 5 files):**

```typescript
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";

const server = setupServer(/* include dispatchBoardHandlers */);
beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}
```

**Navigation mock (all 5 files):**

```typescript
const mockPush = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush, back: vi.fn(), replace: vi.fn() }),
  usePathname: () => "/dispatch",
  useSearchParams: () => new URLSearchParams(),
}));
vi.mock("next/link", () => ({
  default: ({ href, children, ...rest }: any) =>
    React.createElement("a", { href, ...rest }, children),
}));
beforeEach(() => { mockPush.mockClear(); });
```

---

## Final Verification

### Phase 1 — Targeted tests (run after each step)

```bash
cd <repo>/frontend

# After STEP 1:
npx vitest run apps/web/src/features/dispatch-board/store-getTabDays.test.ts 2>&1 | tail -6

# After STEP 3 (week view + tests):
npx vitest run apps/web/src/__tests__/batch_fe_b30 2>&1 | tail -10

# Full web suite (run after each major step):
pnpm --filter web test 2>&1 | tail -6
```

Fix any failure before moving to the next step.

### Phase 2 — Full verification (run once at the very end)

```bash
cd <repo>/frontend && pnpm --filter @pilot/ui check-types && pnpm --filter web check-types && pnpm --filter mobile build && pnpm --filter @pilot/ui lint && pnpm --filter web lint && pnpm --filter mobile lint && echo "=== TYPE+LINT PASS ===" && pnpm --filter @pilot/ui test 2>&1 | tail -6 && pnpm --filter web test 2>&1 | tail -6 && pnpm --filter mobile test 2>&1 | tail -8 && echo "=== FE-B30 FINAL VERIFICATION COMPLETE ==="
```

---

## Definition of Done — FE-B30

Update `dev-docs/analysis/pilot-launch-plan.md` — both the `| 8 | **FE-B30** |` table row AND a new Completion Summary section — when done:

- [ ] Pre-modification regression baseline captured
- [ ] `pnpm sync-api-types` run — no new type errors
- [ ] All source files read before modifying
- [ ] All `"4day"` string literals removed from codebase
- [ ] **STEP 1**: `DispatchViewTab` = `"day" | "week" | "month"`; `store-getTabDays.test.ts` updated (4day test removed)
- [ ] **STEP 2**: `DispatchToolbar.tsx` — 3 tabs only; week-specific + month-specific controls added
- [ ] **STEP 3**: `DispatchWeekView.tsx` created — tech-as-column grid, `@dnd-kit` DnD, context menu, mobile fallback
- [ ] **STEP 4**: `MonthCalendarGrid.tsx` + `MonthViewCell.tsx` updated — chip toggle, context menu, 2-chip max, today highlight, job count pill
- [ ] **STEP 5**: `DispatchBoardPage.tsx` updated — routes to `DispatchWeekView` + updated `MonthCalendarGrid`; no longer imports `DispatchGrid`
- [ ] **STEP 6**: `DispatchGrid.tsx` + `MultiDayGrid.tsx` marked `@deprecated`
- [ ] **STEP 7**: `dispatchBoardHandlers.ts` enriched — `name` + `display_color` on techs
- [ ] Week view renders tech column headers with initials avatar
- [ ] Week view day rows show correct date labels (Mon–Fri 5-day; Mon–Sun 7-day)
- [ ] Week DnD drop fires `PATCH /api/v1/jobs/{id}` with correct date
- [ ] Capacity exceeded (4+ jobs) blocks drop + shows fault chip
- [ ] Context menu right-click works in both Week and Month views
- [ ] Month view chip toggle switches between customer_name and tech initials
- [ ] Month view overflow shows max 2 chips + "+N more"
- [ ] Today cell in Month view has `bg-brand-50` + `ring-brand-200` + brand day number
- [ ] All 5 integration test files pass (minimum 20 tests)
- [ ] Zero TypeScript errors (`pnpm --filter web check-types` passes)
- [ ] Zero ESLint errors (`pnpm --filter web lint` passes)
- [ ] No regressions in pre-existing web, @pilot/ui, mobile test suites
- [ ] **Phase 2 FULL verification command passes** (`=== FE-B30 FINAL VERIFICATION COMPLETE ===`):
  ```bash
  cd <repo>/frontend && pnpm --filter @pilot/ui check-types && pnpm --filter web check-types && pnpm --filter mobile build && pnpm --filter @pilot/ui lint && pnpm --filter web lint && pnpm --filter mobile lint && echo "=== TYPE+LINT PASS ===" && pnpm --filter @pilot/ui test 2>&1 | tail -6 && pnpm --filter web test 2>&1 | tail -6 && pnpm --filter mobile test 2>&1 | tail -8 && echo "=== FE-B30 FINAL VERIFICATION COMPLETE ==="
  ```

---

## Completion Summary

After all Definition of Done items are complete, you must do **both** of the following:

1. **Update the Phase 1 batch sequence table** in `dev-docs/analysis/pilot-launch-plan.md`:
   - Find the `| 8 | **FE-B30** |` row
   - Change `| ☐ |` to `| ✅ |`
   - Append `— **Completed YYYY-MM-DD**` to the end of the "What" cell

2. **Add a Completion Summary section** immediately after the `### FE-B29 — Full-Page Invoice Builder: Completion Summary` section using the format below.

```markdown
### FE-B30 — Dispatch Board Week + Month Views: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot React Engineer
**Baseline**: X passed (web)
**Final**: X+N passed (+N new tests, Y test files)

#### What Was Accomplished

- Removed `"4day"` from `DispatchViewTab`; VIEW_TABS now Day / Week / Month
- Created `DispatchWeekView.tsx` — tech-as-column grid with @dnd-kit DnD + context menu
- Updated `MonthCalendarGrid.tsx` + `MonthViewCell.tsx` — chip toggle, context menu, 2-chip max
- Updated `DispatchBoardPage.tsx` — routes week → DispatchWeekView, month → updated grid
- Deprecated `DispatchGrid.tsx` + `MultiDayGrid.tsx`

#### Files Changed / Created

| File | Action |
|---|---|
| `features/dispatch-board/store.ts` | Updated — removed "4day" from DispatchViewTab |
| `features/dispatch-board/components/DispatchToolbar.tsx` | Updated — 3 tabs; week/month specific controls |
| `features/dispatch-board/components/DispatchWeekView.tsx` | Created |
| `features/dispatch-board/components/MonthCalendarGrid.tsx` | Updated — chipDisplayMode + onJobClick props |
| `features/dispatch-board/components/MonthViewCell.tsx` | Updated — context menu, chip toggle, 2-chip max |
| `features/dispatch-board/components/DispatchBoardPage.tsx` | Updated — new routing |
| `features/dispatch-board/components/DispatchGrid.tsx` | @deprecated JSDoc added |
| `features/dispatch-board/components/MultiDayGrid.tsx` | @deprecated JSDoc added |
| `features/dispatch-board/store-getTabDays.test.ts` | Updated — removed 4day test case |
| `mocks/handlers/dispatchBoardHandlers.ts` | Updated — enriched tech fixture |
| `__tests__/batch_fe_b30/*.integration.test.tsx` | Created — 5 test files |

#### Tests Added

| Test File | Type | Tests | All Pass |
|---|---|---|---|
| `batch_fe_b30/dispatch_toolbar_4day_removed.integration.test.tsx` | Integration | 4 | ✅ |
| `batch_fe_b30/dispatch_week_view_render.integration.test.tsx` | Integration | 4 | ✅ |
| `batch_fe_b30/dispatch_week_view_dnd.integration.test.tsx` | Integration | 4 | ✅ |
| `batch_fe_b30/dispatch_week_month_context_menu.integration.test.tsx` | Integration | 4 | ✅ |
| `batch_fe_b30/dispatch_month_view_chips.integration.test.tsx` | Integration | 4 | ✅ |
```
