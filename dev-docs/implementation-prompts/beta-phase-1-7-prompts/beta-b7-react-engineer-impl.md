# BETA-B7 Implementation Prompt — React Engineer

**Batch**: BETA-B7  
**Design Doc**: `dev-docs/architecture-design/batch-designs/batch-beta-v1-fixes-b7-design.md`  
**Methods Doc**: `dev-docs/architecture-design/pilot-react-engineer-methods.md`  
**Prerequisite Batches Completed**: BETA-B1 ✅, BETA-B2 ✅, BETA-B3 ✅, BETA-B4 ✅, BETA-B5 ✅, BETA-B6 ✅  
**Platform**: Web-only (`apps/web`)  
**Estimated Effort**: 2–4 days  

---

## Mandatory Pre-Work (Do Before Writing Any Code)

1. **Read the design doc in full**: `batch-beta-v1-fixes-b7-design.md`. Every section (A–J) has been written by the Architect against actual source code. Do not skip any section.

2. **Capture regression baseline** before touching any files:
   ```bash
   cd frontend
   pnpm --filter @pilot/ui test 2>&1 | tail -5
   pnpm --filter web test 2>&1 | tail -5
   pnpm check-types 2>&1 | tail -10
   ```
   Record the test counts. The current passing baseline is approximately:
   - `@pilot/ui`: ~630 tests
   - `web`: ~811 tests

3. **Read each source file before editing it** (use `read_file` — do not assume contents):
   - `frontend/apps/web/src/features/settings/components/SettingsSidebar.tsx`
   - `frontend/apps/web/src/features/dispatch-board/components/DispatchGrid.tsx`
   - `frontend/apps/web/src/features/dispatch-board/components/MonthDeferredState.tsx`
   - `frontend/apps/web/src/features/dispatch-board/store.ts`
   - `frontend/apps/web/src/features/dispatch-board/components/DispatchBoardPage.tsx`
   - `frontend/apps/web/src/features/dispatch-board/types-stub.ts` (to understand `DispatchBoardJob` type)

4. **No new npm dependencies**. Both changes are achievable with existing packages (Tailwind CSS, React, Zustand, existing stub types).

5. **No changes to `backend/`**, no API endpoint changes, no schema changes.

---

## Change #1 — Settings Sidebar Typography Fix

### What Is Broken

In `SettingsSidebar.tsx`, the `renderItem(item, depth)` function applies `text-caption` to depth=0 group labels. This pilotPreset token renders at ≤ `text-xs` size, meaning sub-items (`text-xs` at depth=1) appear the same size as or **larger** than their parent group label — a clear visual hierarchy inversion.

Additionally:
- depth=2 items ("Auto-expiry & sync" under QuickBooks) use the same `pl-6 text-xs` as depth=1 items, making them indistinguishable from their parent level.

### What to Change

**Only file**: `frontend/apps/web/src/features/settings/components/SettingsSidebar.tsx`

Update the `className` template inside `renderItem` to implement the following visual hierarchy per the design doc §D.1:

| Depth | Before | After |
|:---:|:---|:---|
| 0 (group labels) | `text-caption text-neutral-700` | `text-sm font-semibold text-neutral-800` |
| 1 (sub-items) | `pl-6 text-xs text-neutral-700` | `pl-6 text-xs text-neutral-600` |
| 2 (sub-sub-items) | `pl-6 text-xs text-neutral-700` (SAME as depth=1) | `pl-10 text-xs text-neutral-500` |

For **active** items at any depth: retain `bg-brand-50 font-medium text-brand-700`.
For **ancestor** items (expanded group containing the active page): `text-neutral-900 hover:bg-neutral-100` (no `font-medium` override — `font-semibold` at depth=0 is sufficient weight).

**Important**: The depth=0 ancestor path previously had `font-medium text-neutral-900` — with `font-semibold` now applied as the base, the ancestor state should just set `text-neutral-900` (no `font-medium` addition needed; `font-semibold` already provides adequate weight). Active state still applies `font-medium` as the override.

### Tests for Change #1

Create or update `frontend/apps/web/src/features/settings/components/__tests__/SettingsSidebar.test.tsx` with unit tests per design doc §J.1.

Add an integration test file `frontend/apps/web/__tests__/batch_beta_b7/settings-sidebar.integration.test.tsx` with tests per design doc §J.2.

---

## Change #2 — Month Calendar Grid

### What Was Deferred

BETA-B5 design doc §G Decision 2 explicitly deferred the Month calendar grid in favor of a "Month view coming soon" placeholder (`MonthDeferredState`). The founder has now determined that beta testers require a functional month view before beta testing begins. All infrastructure from BETA-B5 is already wired and ready:
- `useDispatchBoard(startDate, endDate)` already fetches 30 days of data for month view
- `DispatchBoardPage` already computes a 30-element `dateRange` string array for month view
- `DispatchGrid` already routes `viewMode='month'` to a component — it just needs to route to `MonthCalendarGrid` instead of `MonthDeferredState`

### Step 1 — Create `MonthViewCell` Component

**File**: `frontend/apps/web/src/features/dispatch-board/components/MonthViewCell.tsx`

This is a new component. Implement the interface and visual spec from design doc §D.2:

```typescript
interface MonthViewCellProps {
  dateStr: string | null;         // YYYY-MM-DD, or null for padding cells
  jobs: DispatchBoardJob[];       // jobs on this day
  isToday: boolean;
  isInRange: boolean;
  onDrillDown: (dateStr: string) => void;
}
```

**Visual rules:**
- **Padding cell** (`dateStr === null` or `!isInRange`): `bg-neutral-100` background, no date number, no job chips, not clickable.
- **In-range cell**: `bg-white border border-neutral-200 hover:bg-neutral-50 cursor-pointer`. Date number in top-left corner: `text-xs font-medium text-neutral-700`.
- **Today cell**: wrap the date number in `<span className="flex items-center justify-center w-6 h-6 rounded-full bg-brand-600 text-white text-xs font-medium">`.
- **Job chips**: filter to `jobs` for this cell (caller handles filtering — component receives pre-filtered `jobs`). Show up to 2 chips + `+N more` when `jobs.length > 2`. Chip: `text-xs bg-brand-50 text-brand-700 rounded px-1 py-0.5 truncate max-w-full`. "+N more": `text-xs text-neutral-500`.
- **Cell height**: `min-h-[80px]` with `p-1 flex flex-col gap-0.5`.
- **Click on in-range cell**: calls `onDrillDown(dateStr)`. Click on padding/out-of-range: no-op.

**Job chip label**: use `(job as any).title ?? job.id.slice(0, 8)` — the stub type has `title` but the real `DispatchBoardJobEntry` does not. The cast is acceptable in stub-tolerance mode per BETA-B5 precedent.

### Step 2 — Create `MonthCalendarGrid` Component

**File**: `frontend/apps/web/src/features/dispatch-board/components/MonthCalendarGrid.tsx`

New component. Implement the interface and layout spec from design doc §D.3:

```typescript
interface MonthCalendarGridProps {
  dateRange: string[];                            // 30 YYYY-MM-DD strings
  jobs: DispatchBoardJob[];
  onDrillDown: (dateStr: string) => void;
}
```

**Layout logic:**
1. Compute `firstDayOfWeek` from `dateRange[0]`:
   ```typescript
   const [year, month, day] = dateRange[0].split('-').map(Number);
   const firstDayOfWeek = new Date(year, month - 1, day).getDay(); // 0=Sun, 6=Sat
   ```
2. Render day-of-week header row: `["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]` — `text-xs font-medium text-neutral-500 uppercase text-center py-1`.
3. Build cell array: `firstDayOfWeek` padding cells (null dateStr) + 30 real cells + trailing padding to fill the last row to 7 columns.
4. Render cells in `<div className="grid grid-cols-7 border-l border-t border-neutral-200">` — each cell has `border-r border-b border-neutral-200`.
5. For each real cell, filter jobs: `jobs.filter(j => j.scheduled_start_at?.startsWith(dateStr))`.
6. `isToday`: `dateStr === new Date().toISOString().slice(0, 10)`.
7. Pass `onDrillDown` to each `MonthViewCell`.

**Container**: wrap in `<div className="flex flex-col h-full overflow-hidden p-2">`.

### Step 3 — Update `DispatchGrid` to Use `MonthCalendarGrid`

**File**: `frontend/apps/web/src/features/dispatch-board/components/DispatchGrid.tsx`

Read the file first. Find the month branch (currently `if (effectiveViewMode === "month") { return <MonthDeferredState />; }`).

Replace it with (per design doc §D.4):
```typescript
if (effectiveViewMode === "month") {
  const handleDrillDown = (dateStr: string) => {
    setActiveDate(dateStr);
    setViewTab("day");
  };
  return (
    <MonthCalendarGrid
      dateRange={dateRange ?? []}
      jobs={jobs}
      onDrillDown={handleDrillDown}
    />
  );
}
```

You need to:
1. Import `MonthCalendarGrid` (add import).
2. Import `setActiveDate` and `setViewTab` from `useDispatchBoardStore` (check the store to confirm exact action names — `setViewTab` may be called `setViewTab` or `setActiveTab` — **read the store file to verify**).
3. Remove the `MonthDeferredState` import from `DispatchGrid` (the component file is NOT deleted — just the import from DispatchGrid).

### Step 4 — Add MSW Handler for Month View (If Needed)

Check whether the existing dispatch board MSW handler in `frontend/apps/web/src/mocks/handlers/` already supports multi-day ranges. If `start_date` and `end_date` spanning 30 days return valid data, no new handler is needed. If the handler always returns one day's data, add a handler that returns jobs spread across the date range for month view integration tests.

---

## Test Requirements

### Tests to Create

Per design doc §J:

**Unit tests:**
- `frontend/apps/web/src/features/settings/components/__tests__/SettingsSidebar.test.tsx` — §J.1 (8 tests)
- `frontend/apps/web/src/features/dispatch-board/components/__tests__/MonthViewCell.test.tsx` — §J.3 (7 tests)
- `frontend/apps/web/src/features/dispatch-board/components/__tests__/MonthCalendarGrid.test.tsx` — §J.4 (6 tests)

**Integration tests** (under `apps/web/__tests__/batch_beta_b7/`):
- `settings-sidebar.integration.test.tsx` — §J.2 (3 tests)
- `DispatchBoardMonth.integration.test.tsx` — §J.5 (5 tests)

**Regression test updates:**
- Update `apps/web/__tests__/batch_beta_b5/DispatchGrid.regression.test.tsx` — remove assertions on "Month view coming soon" text (per §J.6). The `MonthDeferredState` component-level tests in `batch_beta_b5/` remain valid — do NOT delete them.

---

## Definition of Done (BETA-B7)

All items must be checked before declaring this batch complete:

- [ ] Pre-modification regression baseline captured (record exact test counts)
- [ ] All mandatory source files read before writing any code
- [ ] **Change #1**: Depth-0 group labels in `SettingsSidebar` render `text-sm font-semibold text-neutral-800`
- [ ] **Change #1**: Depth-1 sub-items render `text-xs text-neutral-600 pl-6`
- [ ] **Change #1**: Depth-2 sub-sub-items render `text-xs text-neutral-500 pl-10`
- [ ] **Change #1**: Active items at all depths still render `bg-brand-50 font-medium text-brand-700`
- [ ] **Change #1**: No `text-caption` class appears on any group label in the settings sidebar
- [ ] **Change #2**: `MonthViewCell.tsx` created and renders date number, today highlight, job chips, and `+N more` chip
- [ ] **Change #2**: `MonthCalendarGrid.tsx` created and renders 7-column grid with day-of-week headers and padding cells
- [ ] **Change #2**: `DispatchGrid.tsx` month branch routes to `MonthCalendarGrid` (not `MonthDeferredState`)
- [ ] **Change #2**: Clicking a month cell calls `setActiveDate(dateStr)` + `setViewTab('day')` — board transitions to Day view
- [ ] **Change #2**: "Month view coming soon" string no longer appears in the DOM when Month tab is active
- [ ] All unit tests pass per §J.1–§J.4
- [ ] All integration tests pass per §J.2, §J.5
- [ ] Regression tests updated per §J.6 (no "coming soon" assertion)
- [ ] `DispatchGrid.regression.test.tsx` still passes (Day/4-Day/Week views unchanged)
- [ ] Zero TypeScript errors (`pnpm check-types` passes on both `@pilot/ui` and `web`)
- [ ] Zero ESLint `no-hardcoded-design-values` warnings (no hardcoded hex colors in new files)
- [ ] No regressions in pre-existing test suite
- [ ] Final test count documented (before → after)
- [ ] No new npm dependencies added

---

## Common Pitfalls to Avoid

| ❌ Wrong | ✅ Correct |
|:---|:---|
| Deleting `MonthDeferredState.tsx` | Keep the file; only remove the import from `DispatchGrid.tsx` |
| Assuming `setViewTab` is the store action name | Read `store.ts` to verify the exact action name before importing |
| Hardcoding hex colors in `MonthViewCell` | Use only `brand-*` and `neutral-*` Tailwind tokens |
| Adding `DndProvider` to `MonthCalendarGrid` | Month view is read-only — no drag-drop; no DndProvider |
| Trying to snap navigation to start of calendar month | Rolling 30-day from `activeDate` is correct for MVP — no month-boundary alignment needed |
| Changing `DispatchBoardPage.tsx` logic | The 30-element `dateRange` computation there is already correct — no changes needed |
| Changing `store.ts` `getTabDays('month')` | Already returns `30` — correct; no changes |
| Using `text-caption` anywhere in the updated `SettingsSidebar` | Remove it entirely from `renderItem`; replace with `text-sm` at depth=0 |
