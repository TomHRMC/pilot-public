# Implementation Prompt: BETA-B5 — Dispatch Board Multi-Day Views

**Mode**: Pilot React Engineer  
**Batch**: BETA-B5  
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-beta-v1-fixes-b5-design.md`  
**Source plan**: `dev-docs/analysis/pilot-app-beta-fixes-v1-impl-plan.md` §8 BETA-B5  
**Estimated session**: 3–5 hours  
**Pure frontend — no backend changes needed**

---

## ⚠️ MANDATORY STOP: Read These Rules First

Before writing a single line of code, read:
- **`.roo/rules-pilot-react-engineer/react-engineer-rules.md`** — in full

Critical rules for this batch:
- **Rule 1.1**: The design doc's component interfaces came from reading the actual source files. Follow them exactly.
- **Rule 2**: All API calls use `apiClient`. Never raw `fetch()`.
- **Rule 8**: The bulk change pattern (`useDispatchBoard` signature change) must be verified with Prettier after modification.

---

## Root Cause: Two Bugs, Not One

The design doc identified **two separate bugs** causing the visual freeze on tab switch:

1. **Data layer bug** (`useDispatchBoard.ts`): Always computes `end_date` as `{activeDate}T23:59:59Z` regardless of which tab is active. 4-Day, Week, and Month tabs all request a 24-hour window — same as Day view.

2. **Rendering layer bug** (`DispatchGrid.tsx`): Never receives the `viewTab` from `DispatchBoardPage`. Renders the same Day-view layout regardless of which tab is active.

Both bugs must be fixed. Fixing only one is not sufficient.

---

## Design Decisions (Do Not Re-Litigate)

From Design Doc §G — these are final:

| Decision | Outcome |
|---|---|
| 4-Day/Week layout | **Option C: side-by-side day panels** — each panel is one day's tech-column × time-row grid |
| Month view | **Deferred** — `<MonthDeferredState>` placeholder "Month view coming soon" |
| Drag-drop in multi-day | **Day view only** — multi-day panels are read-only for beta |
| `DispatchGridColumn.onDrop` | Make **optional** — enables reuse without a drop target |

---

## Pre-Work: Establish Regression Baseline

```bash
cd <repo>/frontend
pnpm --filter web test 2>&1 | tail -5
```

Record this count. All existing tests must still pass at the end — especially Day view tests.

---

## Pre-Work: Read ALL Source Files Before Writing Any Code

**This is mandatory.** The design doc was created from reading these files. You must also read them to understand the exact code you are modifying. Do not infer what they contain.

```
frontend/apps/web/src/features/dispatch-board/hooks/useDispatchBoard.ts
frontend/apps/web/src/features/dispatch-board/components/DispatchGrid.tsx
frontend/apps/web/src/features/dispatch-board/components/DispatchBoardPage.tsx
frontend/apps/web/src/features/dispatch-board/components/DispatchGridColumn.tsx
frontend/apps/web/src/features/dispatch-board/components/JobBlock.tsx
frontend/apps/web/src/features/dispatch-board/store.ts
frontend/apps/web/src/features/dispatch-board/types-stub.ts
```

Read every file with `read_file` before making any changes.

---

## Implementation: Step-by-Step Execution

Follow Design Doc §B execution order exactly.

---

### STEP 1: Fix `useDispatchBoard.ts` — Add `endDate` Parameter

**File**: `frontend/apps/web/src/features/dispatch-board/hooks/useDispatchBoard.ts`

Read the file first. Then make these changes:

1. Change function signature from `useDispatchBoard(date: string)` to `useDispatchBoard(startDate: string, endDate: string)`
2. Update `fetchDispatchBoard` internal function to use `startDate` and `endDate`
3. Update the API call params:
   - `start_date` = `{startDate}T00:00:00Z`
   - `end_date` = `{endDate}T23:59:59Z`  
4. Update `DISPATCH_BOARD_QUERY_KEY` to include both dates:
   ```typescript
   export const DISPATCH_BOARD_QUERY_KEY = (startDate: string, endDate: string) =>
     ["dispatch-board", startDate, endDate] as const;
   ```

**Backward compatibility**: When called with `startDate === endDate` (Day view), the behavior is identical to the original — a 24-hour window for that single date.

After this change, run:
```bash
pnpm --filter web test 2>&1 | tail -5
```

Expect compilation errors in `DispatchBoardPage.tsx` (caller must be updated). Fix them in STEP 5.

---

### STEP 2: Make `DispatchGridColumn.onDrop` Optional

**File**: `frontend/apps/web/src/features/dispatch-board/components/DispatchGridColumn.tsx`

Read the file first. Find the `DispatchGridColumnProps` interface. Change `onDrop` from required to optional:

```typescript
// Before
onDrop: (item: JobBlockDragItem, targetTechId: string | null, dropTopPx: number) => void;

// After
onDrop?: (item: JobBlockDragItem, targetTechId: string | null, dropTopPx: number) => void;
```

Inside the component, wherever `onDrop` is called, add a null check:
```typescript
// Before
onDrop(item, targetTechId, dropTopPx);

// After
onDrop?.(item, targetTechId, dropTopPx);
```

**Day view regression check**: The Day view still passes `onDrop` — changing it to optional does not remove its functionality when provided.

---

### STEP 3: Export `getTabDays` from `store.ts`

**File**: `frontend/apps/web/src/features/dispatch-board/store.ts`

Read the file. Find the `getTabDays` function (it is currently internal). Add `export` to it:

```typescript
// Before (likely)
function getTabDays(tab: DispatchViewTab): number { ... }

// After
export function getTabDays(tab: DispatchViewTab): number { ... }
```

The full function must return exactly:
```typescript
export function getTabDays(tab: DispatchViewTab): number {
  switch (tab) {
    case "day":   return 1;
    case "4day":  return 4;
    case "week":  return 7;
    case "month": return 30;
  }
}
```

Verify the actual implementation matches — do not change the logic, only add `export`.

---

### STEP 4: Create `MultiDayGrid.tsx` — New Component

**File**: `frontend/apps/web/src/features/dispatch-board/components/MultiDayGrid.tsx`

This is the core new component. Layout: **N side-by-side day panels**, each showing one date's tech-column × time-row grid. Read-only (no drag-drop).

Key implementation details per Design Doc §C.3:
- Each panel filters `jobs` to those with `scheduled_start_at?.startsWith(dateStr)`
- Each panel renders one `DispatchGridColumn` per tech (read-only — `onDrop` is undefined)
- Wrap the entire `MultiDayGrid` in its own `DndProvider` (from `react-dnd`) so `JobBlock`'s `useDrag` hook is satisfied — but without any `useDrop` targets. Blocks are technically draggable but no drop occurs. This avoids React DnD console warnings.
- Date header per panel: format as `"Mon Jun 9"` (weekday abbreviated + month + day)
- Highlight today's date header
- Horizontal scroll via `overflow-x-auto` on the outer container
- Vertical scroll matches Day view: same `GRID_HEIGHT_PX` per panel
- Use `COLUMN_MIN_WIDTH_PX`, `GRID_HEIGHT_PX`, `GRID_START_HOUR`, `GRID_END_HOUR`, `HOUR_HEIGHT_PX`, `GRID_HOURS` — all exported from `DispatchGridColumn.tsx` — do not redefine these constants

```tsx
"use client";
import { DndProvider } from "react-dnd";
import { HTML5Backend } from "react-dnd-html5-backend";
import { DispatchGridColumn, COLUMN_MIN_WIDTH_PX, GRID_HEIGHT_PX, HOUR_HEIGHT_PX, GRID_HOURS, GRID_START_HOUR } from "./DispatchGridColumn";
// Adjust imports to match actual exports — read DispatchGridColumn.tsx first

export interface MultiDayGridProps {
  /** YYYY-MM-DD strings for each panel, length 4 (4day) or 7 (week) */
  dateRange: string[];
  techs: DispatchBoardTech[];
  jobs: DispatchBoardJob[];
  onJobSelect: (jobId: string) => void;
}

export function MultiDayGrid({ dateRange, techs, jobs, onJobSelect }: MultiDayGridProps) {
  const today = new Date().toISOString().slice(0, 10);

  return (
    <DndProvider backend={HTML5Backend}>
      <div className="flex overflow-x-auto h-full">
        {dateRange.map((dateStr) => {
          const panelJobs = jobs.filter(
            (j) => j.scheduled_start_at?.startsWith(dateStr)
          );
          const isToday = dateStr === today;
          const displayDate = formatPanelDate(dateStr);

          return (
            <div
              key={dateStr}
              className="flex-shrink-0 border-r border-neutral-200 last:border-r-0"
            >
              {/* Date header */}
              <div
                className={`px-3 py-2 text-xs font-medium border-b border-neutral-200 text-center ${
                  isToday
                    ? "bg-brand-50 text-brand-700"
                    : "bg-neutral-50 text-neutral-600"
                }`}
              >
                {displayDate}
              </div>

              {/* Tech columns for this day */}
              <div className="flex" style={{ height: GRID_HEIGHT_PX }}>
                {/* Time axis */}
                <TimeAxis />
                {/* Tech columns (read-only — no onDrop) */}
                {techs.map((tech) => {
                  const techJobs = panelJobs.filter(
                    (j) => j.tech_id === tech.tech_id
                  );
                  return (
                    <DispatchGridColumn
                      key={tech.tech_id}
                      tech={tech}
                      jobs={techJobs}
                      activeDate={dateStr}
                      onJobSelect={onJobSelect}
                      // onDrop intentionally omitted — read-only mode
                    />
                  );
                })}
                {/* Unassigned column */}
                <DispatchGridColumn
                  tech={null}
                  jobs={panelJobs.filter((j) => !j.tech_id)}
                  activeDate={dateStr}
                  onJobSelect={onJobSelect}
                />
              </div>
            </div>
          );
        })}
      </div>
    </DndProvider>
  );
}

function formatPanelDate(dateStr: string): string {
  const d = new Date(dateStr + "T12:00:00");
  return d.toLocaleDateString("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
  });
}
```

> **Important**: Read `DispatchGridColumn.tsx` carefully before implementing. The props interface for `DispatchGridColumn` (specifically `tech`, `jobs`, the Unassigned column handling, and the exported constants) must match exactly what exists — not what is assumed. Adjust the code above based on actual prop names.

> **Important**: Read `JobBlock.tsx` to understand what `j.tech_id` field is called on the job object. Adjust the filter accordingly.

---

### STEP 5: Create `MonthDeferredState.tsx` — New Component

**File**: `frontend/apps/web/src/features/dispatch-board/components/MonthDeferredState.tsx`

Simple placeholder — no data fetching:

```tsx
export function MonthDeferredState() {
  return (
    <div className="flex flex-col items-center justify-center h-64 text-center">
      <div className="text-4xl mb-4" aria-hidden="true">📅</div>
      <h3 className="text-lg font-medium text-neutral-700 mb-2">
        Month view coming soon
      </h3>
      <p className="text-sm text-neutral-500 max-w-xs">
        Switch to Day, 4-Day, or Week view to manage your schedule.
      </p>
    </div>
  );
}
```

---

### STEP 6: Extend `DispatchGrid.tsx` — Add `viewMode` and `dateRange` Props

**File**: `frontend/apps/web/src/features/dispatch-board/components/DispatchGrid.tsx`

Read the file first. Then:

1. Add two optional props to `DispatchGridProps`:
   ```typescript
   viewMode?: DispatchViewTab;  // default 'day' — backward compatible
   dateRange?: string[];         // YYYY-MM-DD array; required when viewMode is '4day' or 'week'
   ```

2. Add a rendering branch at the top of the component body (before the existing Day-view JSX):

```typescript
import { MultiDayGrid } from "./MultiDayGrid";
import { MonthDeferredState } from "./MonthDeferredState";

export function DispatchGrid({
  techs,
  jobs,
  activeDate,
  onJobSelect,
  onMoveJob,
  isMoveJobPending,
  viewMode = "day",
  dateRange,
}: DispatchGridProps) {

  // Multi-day routing — day view falls through to existing code path
  if (viewMode === "4day" || viewMode === "week") {
    return (
      <MultiDayGrid
        dateRange={dateRange ?? [activeDate]}
        techs={techs}
        jobs={jobs}
        onJobSelect={onJobSelect}
      />
    );
  }

  if (viewMode === "month") {
    return <MonthDeferredState />;
  }

  // viewMode === 'day' (or default) — EXISTING CODE UNCHANGED BELOW THIS LINE
  // ... rest of existing component exactly as-is
}
```

**The existing Day-view code below the routing branch must not be modified at all.** The only change to `DispatchGrid.tsx` is: (a) the new imports, (b) the two new optional props, and (c) the routing branch at the top.

---

### STEP 7: Update `DispatchBoardPage.tsx` — Wire `viewTab` to Hook and Grid

**File**: `frontend/apps/web/src/features/dispatch-board/components/DispatchBoardPage.tsx`

Read the file first. Then make these changes:

1. Import `getTabDays` from `store.ts`:
   ```typescript
   import { useDispatchBoardStore, getTabDays } from "../store";
   ```

2. In the component body, compute `endDate` and `dateRange`:
   ```typescript
   const activeDate = useDispatchBoardStore((s) => s.activeDate);
   const viewTab = useDispatchBoardStore((s) => s.viewTab);

   // Compute end date based on view tab
   const endDate = addDays(activeDate, getTabDays(viewTab) - 1);

   // Compute date range for multi-day grid
   const dateRange = Array.from(
     { length: getTabDays(viewTab) },
     (_, i) => addDays(activeDate, i)
   );
   ```

3. Add the `addDays` helper (inline in the file):
   ```typescript
   function addDays(dateStr: string, days: number): string {
     const d = new Date(dateStr + "T12:00:00");
     d.setDate(d.getDate() + days);
     return d.toISOString().slice(0, 10);
   }
   ```

4. Update the `useDispatchBoard` call:
   ```typescript
   // Before
   const { data, isLoading } = useDispatchBoard(activeDate);

   // After
   const { data, isLoading } = useDispatchBoard(activeDate, endDate);
   ```

5. Update `<DispatchGrid>` props:
   ```typescript
   // Add viewMode and dateRange to the existing DispatchGrid call
   <DispatchGrid
     {...existingProps}
     viewMode={viewTab}
     dateRange={dateRange}
   />
   ```

> **Read the file carefully** before making changes. The component may have additional prop passing, loading states, or error handling that must be preserved. The above shows the logical changes — insert them into the actual code structure you find.

---

## Test Implementation

### Unit Tests

Create per Design Doc §I.1. All test files are **new** — no existing dispatch board test files should be modified.

**Key test files:**

1. `useDispatchBoard.test.ts` — verify the three query param scenarios (single-day, 4-day range, different `endDate` produces different query key)

2. `store.test.ts` (or `store-getTabDays.test.ts`) — verify `getTabDays` returns correct values for all 4 tabs

3. `MultiDayGrid.test.tsx` — verify: N panels for N dates; job filtering by date (job appears only in correct panel); read-only (no DnD drop targets)

4. `MonthDeferredState.test.tsx` — verify "Month view coming soon" heading renders

5. `DispatchGrid.test.tsx` — verify: no `viewMode` prop → day path; `viewMode='4day'` → `MultiDayGrid`; `viewMode='month'` → `MonthDeferredState`

6. `DispatchGridColumn.test.tsx` (update existing) — verify `onDrop` optional: column renders without `onDrop` prop

### Integration Tests

**Location**: `apps/web/__tests__/batch_beta_b5/`

Per Design Doc §I.2 — create `DispatchBoardPage.integration.test.tsx` covering:
- Tab switch to 4-Day → API called with correct `end_date = activeDate+3`
- Tab switch to Week → API called with `end_date = activeDate+6`
- Tab switch to Month → `MonthDeferredState` renders (no grid)
- Tab switch back to Day → day columns render (not `MultiDayGrid`)
- 4-Day grid: 4 date panel headers with consecutive dates
- Navigate prev/next in 4-Day: `activeDate` advances by 4 days

### Regression Tests (Day View Must Not Break)

Per Design Doc §I.3 — create `DispatchGrid.regression.test.tsx`:
- Day view with no `viewMode` prop → renders `DispatchGridColumn` components
- Day view drag-drop: `DndProvider` present, `handleDrop` triggers `onMoveJob`
- Day view `ConflictPreviewPane` still appears on drop

---

## Final Verification

```bash
cd <repo>/frontend && pnpm --filter @pilot/ui check-types && pnpm --filter web check-types && pnpm --filter mobile build && pnpm --filter @pilot/ui lint && pnpm --filter web lint && pnpm --filter mobile lint && echo "=== TYPE+LINT PASS ===" && pnpm --filter @pilot/ui test 2>&1 | tail -6 && pnpm --filter web test 2>&1 | tail -6 && pnpm --filter mobile test 2>&1 | tail -8 && echo "=== MVP FINAL VERIFICATION COMPLETE ==="
```

---

## Definition of Done — BETA-B5

Update the `pilot-app-beta-fixes-v1-impl-plan.md` §9 Batch Completion Tracker:

- [ ] Pre-modification regression baseline captured
- [ ] All 7 dispatch board source files read before writing any code
- [ ] **STEP 1**: `useDispatchBoard` signature updated to `(startDate, endDate)` — verified via grep
- [ ] **STEP 1**: Query key updated to include both dates
- [ ] **STEP 1**: `start_date = {startDate}T00:00:00Z`, `end_date = {endDate}T23:59:59Z`
- [ ] **STEP 2**: `DispatchGridColumn.onDrop` changed to optional — no-op callers use `?.`
- [ ] **STEP 3**: `getTabDays` exported from `store.ts`
- [ ] **STEP 4**: `MultiDayGrid.tsx` created — N side-by-side day panels; date filtering works
- [ ] **STEP 4**: Each panel renders `DispatchGridColumn` without `onDrop` (read-only)
- [ ] **STEP 4**: `DndProvider` wraps `MultiDayGrid` to satisfy `useDrag` hooks
- [ ] **STEP 5**: `MonthDeferredState.tsx` created — "Month view coming soon" heading
- [ ] **STEP 6**: `DispatchGrid` extended with optional `viewMode` + `dateRange` props
- [ ] **STEP 6**: `viewMode='day'` (default) → existing code path unchanged
- [ ] **STEP 6**: `viewMode='4day'|'week'` → `<MultiDayGrid>` rendered
- [ ] **STEP 6**: `viewMode='month'` → `<MonthDeferredState>` rendered
- [ ] **STEP 7**: `DispatchBoardPage` imports and uses `getTabDays`
- [ ] **STEP 7**: `endDate` computed as `activeDate + (getTabDays(viewTab) - 1)` days
- [ ] **STEP 7**: `dateRange` computed as array of consecutive YYYY-MM-DD strings
- [ ] **STEP 7**: `useDispatchBoard` called with `(activeDate, endDate)`
- [ ] **STEP 7**: `DispatchGrid` called with `viewMode={viewTab}` and `dateRange={dateRange}`
- [ ] Switching to "4 Day" tab: grid shows 4 date panel headers with consecutive dates
- [ ] Switching to "Week" tab: grid shows 7 date panel headers
- [ ] Switching to "Month" tab: "Month view coming soon" placeholder renders
- [ ] Switching back to "Day" tab: normal Day view grid renders unchanged
- [ ] Navigate prev/next in 4-Day mode: date advances by 4 days
- [ ] Day view drag-drop still works — no regression
- [ ] Day view `ConflictPreviewPane` still works — no regression
- [ ] Unit tests pass per §I.1 (6 test files)
- [ ] Integration tests pass per §I.2 (7 scenarios in `batch_beta_b5/`)
- [ ] Regression tests pass per §I.3 (4 Day-view scenarios)
- [ ] Zero TypeScript errors
- [ ] Zero ESLint `no-hardcoded-design-values` warnings
- [ ] No regressions in pre-existing test suite
- [ ] Full verification command passes (`=== MVP FINAL VERIFICATION COMPLETE ===`)
- [ ] Update this Definition of Done list with completion checks next to each item if completed
- [ ] Final test count (before/after) documented in impl plan tracker in the source plan
- [ ] Summary of work accomplished added to new sub-section in impl plan tracker in Section 9 in the source plan after the last batch entry
