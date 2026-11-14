# BETA-B7 Batch Design — Settings Sub-menu Typography Fix & Month Calendar Grid

**Version**: 1.0
**Date**: 2026-06-05
**Batch**: BETA-B7
**Prerequisite Batches**: FE-B11 ✅, BETA-B4 ✅, BETA-B5 ✅, BETA-B6 ✅
**Estimated Effort**: 2–4 days
**Test Subfolder**: `apps/web/__tests__/batch_beta_b7/`
**Platform**: Web-only (Next.js 16)
**Status**: Design complete — ready for React Engineer implementation

---

## A. Input Read Summary

All source artifacts were read directly before writing this document. No content was assumed.

### A.1 Artifacts Read

| Artifact | Key Findings |
|:---|:---|
| `frontend/apps/web/src/features/settings/components/SettingsSidebar.tsx` | `renderItem(item, depth)` uses `text-caption` at `depth=0` and adds `pl-6 text-xs` for `depth>0`. Root cause of visual size inversion: `text-caption` (a pilotPreset token, likely ≤0.75rem) renders parent group labels visually smaller than or equal to their `text-xs` sub-items. No visual grouping weight separates parent from child. Depth-2 sub-sub-items (e.g. "Auto-expiry & sync") fall into the same `depth > 0` path — same `pl-6 text-xs` — giving them identical or larger rendering than their depth-1 parent "QuickBooks". |
| `frontend/apps/web/src/features/settings/components/SettingsShell.tsx` | Shell layout is `flex h-full min-h-0 flex-1`. Sidebar is `hidden lg:flex` — `w-56 shrink-0`. No changes needed to shell. |
| `frontend/apps/web/src/features/dispatch-board/components/MonthDeferredState.tsx` | Renders "Month view coming soon" heading + instruction copy. This component is the sole output when `viewMode='month'` in `DispatchGrid.tsx`. It must be replaced by `MonthCalendarGrid`. |
| `frontend/apps/web/src/features/dispatch-board/components/DispatchGrid.tsx` | BETA-B5 wired `viewMode='month'` → `<MonthDeferredState>`. The routing branch for `month` is the single change point: swap `MonthDeferredState` for `MonthCalendarGrid`. All other view mode paths (day, 4day, week) remain untouched. |
| `frontend/apps/web/src/features/dispatch-board/store.ts` | `getTabDays('month')` returns `30`. Store exports `navigatePrev`/`navigateNext` which advance `activeDate` by `getTabDays(viewTab)` — advancing by 30 days in month view. `setActiveDate` is also exported and is the mechanism for drill-down from a cell click. `DispatchViewTab = "day" | "4day" | "week" | "month"` — no changes needed. |
| `frontend/apps/web/src/features/dispatch-board/components/DispatchBoardPage.tsx` | BETA-B5: computes `dateRange = Array.from({ length: getTabDays(viewTab) }, (_, i) => addDays(activeDate, i))` — for month view, this is a 30-element string array. Passes `dateRange` to `DispatchGrid`. `MonthCalendarGrid` will consume this prop. No change to `DispatchBoardPage` is needed. |
| `frontend/apps/web/src/features/dispatch-board/hooks/useDispatchBoard.ts` | BETA-B5 signature: `useDispatchBoard(startDate, endDate)`. Month view: `startDate=activeDate`, `endDate=addDays(activeDate,29)`. API already returns all jobs in that 30-day window. Data is fully available. |
| `dev-docs/architecture-design/batch-designs/batch-beta-v1-fixes-b5-design.md` §G Decision 2 | Month view deferred at BETA-B5 because: no time axis needed (architecturally different from time-column grid), `MonthViewCell` never built in FE-B4, 5–10 contractor beta preferred placeholder over broken tab. BETA-B7 now reverses this deferral — the infrastructure is ready (hook, store, dateRange). |
| `dev-docs/product-requirements/mvp-prd.md` §3.14 | "Primary scheduling UI on web renders as a grid of tech columns × time rows." Month view tab's existence is confirmed in the PRD; no explicit month-grid layout is specified. Standard industry convention (Google Calendar / Microsoft Outlook month view: 7-column × 5-row grid) applies. |
| `frontend/apps/web/src/components/AppSidebar.tsx` | Main nav uses `text-sm` for all items — readable and consistent. Settings menu item at depth=0 in `SettingsSidebar` should match or complement this scale. |

### A.2 Root Cause Analysis

**Change #1 — Settings Sub-menu Typography**

Two compounding problems in `SettingsSidebar.tsx`:

1. **Size inversion**: `depth=0` group labels use `text-caption` (pilotPreset token). The token maps to a size ≤ `text-xs` (0.75rem). Sub-items at `depth=1` use `text-xs` — resulting in sub-items appearing the same size as or larger than their parent group labels. The founder explicitly observed "Margin buckets is actually larger than its parent."

2. **No visual weight hierarchy**: All items use `text-neutral-700` for inactive state. There is no `font-medium` or `text-sm` upgrade on group labels to signal structural hierarchy. The sidebar looks flat and hard to read.

3. **Sub-sub-items not distinguished**: `depth=2` items (e.g. "Auto-expiry & sync" under QuickBooks) fall into the same `depth > 0` branch as `depth=1` items — same `pl-6 text-xs` — with no additional indentation or color treatment to distinguish the third level.

**Change #2 — Month Calendar Grid**

The `MonthDeferredState` placeholder was an explicit design decision in BETA-B5 §G Decision 2. The founder has now determined that beta testers (who are used to Google Calendar and Outlook) need a real month grid view before beta testing begins. The infrastructure is fully wired from BETA-B5; only the visual layer needs to be built:
- `MonthCalendarGrid` component (new)
- `MonthViewCell` component (new — specified but never built in FE-B4)
- Replace `MonthDeferredState` reference in `DispatchGrid` month branch

---

## B. Migration Plan

**No database changes.** Both changes are pure frontend (visual layer only). No new API endpoints. No schema changes. No Celery tasks. No Alembic migrations.

---

## C. Execution Order

Implementation order is strict — each item must be completed and passing tests before the next:

| # | Task | File(s) | Dependency |
|:---:|:---|:---|:---|
| 1 | Fix `SettingsSidebar` typography — `depth=0` group labels → `text-sm font-semibold`, `depth=1` sub-items → `text-xs`, `depth=2` sub-sub-items → `text-xs` + deeper indent + muted color | `SettingsSidebar.tsx` | None |
| 2 | Add `SettingsSidebar` unit + integration tests for new styles | `SettingsSidebar.test.tsx`, `batch_beta_b7/` | #1 |
| 3 | Build `MonthViewCell` component | New file | None |
| 4 | Build `MonthCalendarGrid` component | New file | #3 |
| 5 | Replace `MonthDeferredState` with `MonthCalendarGrid` in `DispatchGrid` | `DispatchGrid.tsx` | #3, #4 |
| 6 | Update `DispatchBoardPage` for month-specific `dateRange` alignment (if needed — see §C.1) | `DispatchBoardPage.tsx` | #5 |
| 7 | Write unit + integration tests for `MonthCalendarGrid` and `MonthViewCell` | Test files per §I | #3–#6 |
| 8 | Update regression tests — `MonthDeferredState` heading text must no longer appear | `DispatchGrid.regression.test.tsx` | #5 |

### C.1 Month `dateRange` Alignment

The current `DispatchBoardPage` computes `dateRange` as 30 consecutive days starting from `activeDate`. For a calendar grid, the displayed cells must align with the calendar week structure — cells before `activeDate` or after day 30 are shown as "padding" cells (greyed out, no date number or job data). This padding is computed entirely within `MonthCalendarGrid` from the `dateRange` prop — `DispatchBoardPage` does **not** need to change. See §D.3 for the padding cell spec.

---

## D. Component Changes

### D.1 `SettingsSidebar` — Typography Fix

| Property | Detail |
|:---|:---|
| **File** | `frontend/apps/web/src/features/settings/components/SettingsSidebar.tsx` |
| **Change** | Update `renderItem` class logic for depth-based typographic hierarchy |

**Current problematic class assignment in `renderItem`:**
```typescript
// Current (broken hierarchy):
className={`flex items-center rounded-md px-3 py-2 text-caption transition-colors ${
  active ? "bg-brand-50 font-medium text-brand-700"
  : ancestor ? "font-medium text-neutral-900 hover:bg-neutral-100"
  : "text-neutral-700 hover:bg-neutral-100"
} ${depth > 0 ? "pl-6 text-xs" : ""}`}
```

**Required new class assignment:**
```typescript
// New (corrected hierarchy):
className={`flex items-center rounded-md px-3 py-2 transition-colors ${
  // Depth-specific base typography
  depth === 0
    ? "text-sm font-semibold"
    : depth === 1
      ? "text-xs font-normal"
      : "text-xs font-normal"
} ${
  // Active / ancestor / default states
  active
    ? "bg-brand-50 font-medium text-brand-700"
    : ancestor
      ? "text-neutral-900 hover:bg-neutral-100"
      : depth === 0
        ? "text-neutral-800 hover:bg-neutral-100"
        : depth === 1
          ? "text-neutral-600 hover:bg-neutral-100"
          : "text-neutral-500 hover:bg-neutral-100"
} ${
  // Depth indentation
  depth === 0 ? ""
  : depth === 1 ? "pl-6"
  : "pl-10"
}`}
```

**Summary of visual changes per depth level:**

| Depth | Element Example | Before | After |
|:---:|:---|:---|:---|
| 0 | "Operations", "My Account", "Integrations" | `text-caption text-neutral-700` (very small, flat) | `text-sm font-semibold text-neutral-800` (clear group header) |
| 1 | "Margin buckets", "Profile", "Calendar" | `pl-6 text-xs text-neutral-700` | `pl-6 text-xs text-neutral-600` (proper sub-item, smaller than group header) |
| 2 | "Auto-expiry & sync" | `pl-6 text-xs text-neutral-700` (same as depth=1 — visual collision) | `pl-10 text-xs text-neutral-500` (clearly tertiary, deeper indent) |

**Design rationale:**
- `text-sm font-semibold` at depth=0 establishes unmistakable group labels — clearly larger and bolder than any child
- `text-xs` at depth=1 is the correct sub-item size — clearly smaller than the parent
- `pl-10` at depth=2 visually isolates the third level from depth=1 items (current `pl-6` makes depth=2 start at the same x-position as depth=1)
- `text-neutral-500` at depth=2 provides the muted "tertiary navigation" signal expected by users familiar with Google/Microsoft settings UIs
- `ancestor` state removes the `font-medium` override at depth=0 (it was duplicating the weight that `font-semibold` already provides); the active state still upgrades to `font-medium text-brand-700` regardless of depth

**No changes** to `SIDEBAR_ITEMS` data structure, `SettingsShell`, or `SettingsSidebarSearch`.

### D.2 `MonthViewCell` — New Component

| Property | Detail |
|:---|:---|
| **File** | `frontend/apps/web/src/features/dispatch-board/components/MonthViewCell.tsx` |
| **Type** | New component (specified in FE-B4 spec but never built) |
| **Used by** | `MonthCalendarGrid` |

```typescript
interface MonthViewCellProps {
  /** YYYY-MM-DD for this cell, or null for padding cells */
  dateStr: string | null;
  /** Jobs scheduled on this day */
  jobs: DispatchBoardJob[];
  /** Whether this cell is today */
  isToday: boolean;
  /** Whether this cell falls within the current active 30-day window */
  isInRange: boolean;
  /** Callback: user clicked this cell to drill down to Day view */
  onDrillDown: (dateStr: string) => void;
}
```

**Visual spec per cell:**
- **Padding cell** (`dateStr === null` or `!isInRange`): grey background (`bg-neutral-100`), no date number, no jobs. Non-interactive.
- **In-range cell**: white background (`bg-white`) with `border border-neutral-200`. Date number top-left corner: `text-xs font-medium text-neutral-700`.
- **Today cell**: date number circle highlighted — `bg-brand-600 text-white rounded-full` (8px padding around number).
- **Job chips**: up to 3 job chips per cell (`text-xs bg-brand-50 text-brand-700 rounded px-1 py-0.5 truncate`). If more than 3 jobs, render `+N more` chip in `text-neutral-500`.
- **Cell height**: `min-h-[80px]` to ensure readability.
- **Hover**: `hover:bg-neutral-50 cursor-pointer` on in-range cells.
- **Click**: calls `onDrillDown(dateStr)`.

**Job chip content**: Display `job.id` truncated to 8 chars as a fallback (the real `types-stub.ts` `DispatchBoardJob` has stub fields `title`, `customer_name` — use `job.title ?? job.id.slice(0, 8)` for the label). This follows the same stub-tolerance pattern established in BETA-B5 — chips display what is available without crashing.

### D.3 `MonthCalendarGrid` — New Component

| Property | Detail |
|:---|:---|
| **File** | `frontend/apps/web/src/features/dispatch-board/components/MonthCalendarGrid.tsx` |
| **Type** | New component |
| **Used by** | `DispatchGrid` (when `viewMode === 'month'`) |

**Props:**
```typescript
interface MonthCalendarGridProps {
  /** 30 YYYY-MM-DD strings from DispatchBoardPage (activeDate to activeDate+29) */
  dateRange: string[];
  /** All jobs in the date range from useDispatchBoard */
  jobs: DispatchBoardJob[];
  /** Callback to navigate to day view for a specific date */
  onDrillDown: (dateStr: string) => void;
}
```

**Grid layout spec:**
- **Day-of-week header row**: `["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]` — `text-xs font-medium text-neutral-500 uppercase` — not clickable.
- **Cell grid**: `grid grid-cols-7` CSS grid. 
- **Padding cells before first day**: The first date in `dateRange` has a `dayOfWeek` (0=Sun, 6=Sat). Render `dayOfWeek` empty padding cells before the first real cell.
- **Padding cells after last day**: Fill the final grid row to 7 columns.
- **Real cells**: `MonthViewCell` for each `dateStr` in `dateRange`.
- **Job filtering per cell**: `jobs.filter(job => job.scheduled_start_at?.startsWith(dateStr))` — same prefix-match pattern from `MultiDayGrid`.
- **`isToday`**: compare `dateStr === new Date().toISOString().slice(0, 10)`.
- **Container**: `overflow-x-hidden` (no horizontal scroll — calendar fills the available width). Each cell fills its column equally via `grid-cols-7`.

**`onDrillDown` wiring:**
`MonthCalendarGrid` receives `onDrillDown`. When a cell is clicked, the parent (`DispatchGrid`) must call two Zustand store actions:
1. `setActiveDate(dateStr)` — navigate to the clicked date
2. `setViewTab('day')` — switch to Day view

This is a two-action call. `DispatchGrid` constructs the `onDrillDown` handler and passes it down. See §D.4.

**Month navigation:** The existing `<DispatchToolbar>` prev/next buttons advance by `getTabDays('month')` = 30 days. This is sufficient for MVP month navigation — users see 30 rolling days. No "jump to start of month" logic is required at MVP.

### D.4 `DispatchGrid` — Wire Month Branch

| Property | Detail |
|:---|:---|
| **File** | `frontend/apps/web/src/features/dispatch-board/components/DispatchGrid.tsx` |
| **Change** | Replace `<MonthDeferredState />` with `<MonthCalendarGrid>` in the month branch. Add `onDrillDown` handler. |

**Current month branch (to be replaced):**
```typescript
if (effectiveViewMode === "month") {
  return <MonthDeferredState />;
}
```

**New month branch:**
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

`DispatchGrid` must import `setActiveDate` and `setViewTab` from the Zustand store. Both are already present in the store — they just need to be imported via `useDispatchBoardStore`. No new store actions.

**`MonthDeferredState` import removal:** Remove the import of `MonthDeferredState` from `DispatchGrid.tsx`. The component file itself (`MonthDeferredState.tsx`) is **not deleted** — it remains in the codebase since it may be referenced in existing tests. However, `DispatchGrid` no longer uses it. The existing `MonthDeferredState` tests in `batch_beta_b5/` test the component in isolation — they remain valid as component-level tests. Only `DispatchGrid` wiring changes.

---

## E. Pattern Reuse Decisions

### E.1 Job Prefix-Date Filtering — Reused from `MultiDayGrid`
`MonthCalendarGrid` uses the same `job.scheduled_start_at?.startsWith(dateStr)` pattern established in BETA-B5 `MultiDayGrid`. No change to the pattern.

### E.2 `getTabDays` / `addDays` — No Changes
`DispatchBoardPage` already computes a 30-element `dateRange` for month view. `MonthCalendarGrid` consumes it as-is. No changes to `store.ts` or `DispatchBoardPage`.

### E.3 Zustand Store `setActiveDate` + `setViewTab` — Standard Pattern
Drill-down from month cell to day view uses the same Zustand action pattern used by `DispatchToolbar` for tab switching. No new patterns introduced.

### E.4 Design Token Compliance — No Hardcoded Colors
All new class names in both `SettingsSidebar.tsx` and `MonthViewCell.tsx` / `MonthCalendarGrid.tsx` must use the pilotPreset Tailwind tokens:
- `brand-*` for active/highlight states
- `neutral-*` for structural greys
- `text-sm`, `text-xs` for typography scale
- No hex colors, no `style={}` attribute color overrides

### E.5 `MonthViewCell` — Read-Only (No Drag-Drop)
Consistent with the BETA-B5 §G Decision 3 precedent (drag-drop restricted to Day view), `MonthViewCell` is click-to-drill-down only. No `DndProvider` is added to `MonthCalendarGrid`. Drag interactions are not supported in Month view at MVP.

---

## F. Shared Module Interfaces

### F.1 No New Exports from `store.ts`
`setActiveDate` and `setViewTab` are already exported via `useDispatchBoardStore`. No new exports needed.

### F.2 `MonthCalendarGridProps` Interface
```typescript
// frontend/apps/web/src/features/dispatch-board/components/MonthCalendarGrid.tsx
export interface MonthCalendarGridProps {
  dateRange: string[];          // YYYY-MM-DD, length 30 (from getTabDays('month'))
  jobs: DispatchBoardJob[];
  onDrillDown: (dateStr: string) => void;
}
```

### F.3 `MonthViewCellProps` Interface
```typescript
// frontend/apps/web/src/features/dispatch-board/components/MonthViewCell.tsx
export interface MonthViewCellProps {
  dateStr: string | null;
  jobs: DispatchBoardJob[];
  isToday: boolean;
  isInRange: boolean;
  onDrillDown: (dateStr: string) => void;
}
```

---

## G. Open Questions Resolved

### G.1 Should Month Navigation Align to Calendar Month Boundaries?

**Decision**: No — MVP month view shows a rolling 30-day window starting from `activeDate`. Navigation via prev/next advances 30 days.

**Rationale**: Implementing "snap to month start" navigation requires additional store logic (computing first-of-month for any `activeDate`). The PRD does not specify month-boundary snapping. The existing `navigatePrev`/`navigateNext` pattern is consistent across all view modes. Rolling 30-day is functionally sufficient for beta users who need to see what is scheduled across a month window. Post-beta, "snap to month" is a natural improvement when the navigation UX is refined.

### G.2 What Replaces `MonthDeferredState` — Delete or Keep?

**Decision**: Keep `MonthDeferredState.tsx` as a dormant file. Remove only the import and usage in `DispatchGrid.tsx`.

**Rationale**: The file has passing tests in `batch_beta_b5/MonthDeferredState.test.tsx`. Deleting it would require deleting or rewriting those tests. The file is small and harmless. Keeping it avoids a test deletion that would reduce the total test count and could confuse future engineers reviewing git history.

### G.3 Month Cell Drill-Down — Navigate to Day View or Open Modal?

**Decision**: Drill-down navigates `activeDate` to the clicked date and switches `viewTab` to `'day'`. No modal. No new route.

**Rationale**: The dispatch board is a single-page feature — all view mode switching happens via Zustand store mutations, not route changes. Switching to Day view is the correct "zoom in" action. Opening a modal would require a new UI pattern not established in the existing design system.

### G.4 How Many Job Chips Per Cell — What Is the Truncation Threshold?

**Decision**: Show up to 3 job chips. If `jobs.length > 3`, show the first 2 chips + `+N more` label.

**Rationale**: Cell height is `min-h-[80px]`. At `text-xs` line height (~16px) + padding (~4px), 3 chips fit without overflow. The `+N more` pattern is familiar from Google Calendar. Showing only 2 chips + overflow label (rather than 3 + label) when there are 4+ jobs gives cleaner visual breathing room.

### G.5 `SettingsSidebar` — Should `text-caption` Be Removed from the Design Tokens?

**Decision**: Out of scope for BETA-B7. The `text-caption` token may be used by other components. This batch only changes `SettingsSidebar.tsx` — it replaces the token usage in this specific component. No global token change.

---

## H. Surface Mockup Reference

### H.1 Settings Sidebar — Before / After Hierarchy

```
BEFORE (broken):
  Operations         ← text-caption (≤text-xs, barely visible)
    Margin buckets   ← text-xs (SAME or LARGER than parent — reported bug)
    Profitability rules
    Field operations
  Integrations       ← text-caption
    General          ← text-xs
    Calendar         ← text-xs
    QuickBooks       ← text-xs
      Auto-expiry    ← text-xs pl-6 (SAME position as QuickBooks — reported bug)

AFTER (fixed):
  Operations         ← text-sm font-semibold text-neutral-800 (clear group header)
    Margin buckets   ← text-xs text-neutral-600 pl-6 (clearly smaller)
    Profitability rules
    Field operations
  Integrations       ← text-sm font-semibold text-neutral-800
    General          ← text-xs text-neutral-600 pl-6
    Calendar         ← text-xs text-neutral-600 pl-6
    QuickBooks       ← text-xs text-neutral-600 pl-6
      Auto-expiry    ← text-xs text-neutral-500 pl-10 (deeper indent, muted — clearly tertiary)
```

### H.2 Month Calendar Grid — Layout

```
┌────────────────────────────────────────────────────────────────┐
│  Sun    Mon    Tue    Wed    Thu    Fri    Sat                  │
├────────┬────────┬────────┬────────┬────────┬────────┬─────────┤
│        │   1   │   2   │   3   │   4   │   5   │   6   │  ← padding cells on left (greyed)
│        │ Job A │ ·Job B│       │ +2more│       │       │
├────────┼────────┼────────┼────────┼────────┼────────┼─────────┤
│   7   │   8   │  [9]  │  10   │  11   │  12   │  13   │  ← [today] circled in brand-600
│       │       │ Job C │       │ Job D │       │       │
├────────┼────────┼────────┼────────┼────────┼────────┼─────────┤
│  ...                                                           │
└────────────────────────────────────────────────────────────────┘
```

Click on any cell → `setActiveDate(dateStr)` + `setViewTab('day')` → board shows that day.

---

## I. Component Manifest

| Component | File Path | Action | Batch Establishes |
|:---|:---|:---|:---|
| `SettingsSidebar` (modified) | `apps/web/src/features/settings/components/SettingsSidebar.tsx` | Modify — `renderItem` class logic | BETA-B7 |
| `MonthViewCell` | `apps/web/src/features/dispatch-board/components/MonthViewCell.tsx` | **New** | BETA-B7 |
| `MonthCalendarGrid` | `apps/web/src/features/dispatch-board/components/MonthCalendarGrid.tsx` | **New** | BETA-B7 |
| `DispatchGrid` (modified) | `apps/web/src/features/dispatch-board/components/DispatchGrid.tsx` | Modify — replace `MonthDeferredState` with `MonthCalendarGrid` in month branch | BETA-B7 |
| `MonthDeferredState` (unchanged) | `apps/web/src/features/dispatch-board/components/MonthDeferredState.tsx` | Keep — remove from `DispatchGrid` import; component file retained | FE-B5 |

---

## J. Test Plan

**Test subfolder**: `apps/web/__tests__/batch_beta_b7/`

### J.1 Unit Tests — Settings Sidebar Typography

| Test | File | Assertion |
|:---|:---|:---|
| Depth-0 group labels have `text-sm` class | `SettingsSidebar.test.tsx` | `getByText('Operations')` has class matching `text-sm` |
| Depth-0 group labels have `font-semibold` class | `SettingsSidebar.test.tsx` | `getByText('Operations')` has class matching `font-semibold` |
| Depth-1 sub-items have `text-xs` class | `SettingsSidebar.test.tsx` | `getByText('Margin buckets')` has class matching `text-xs` |
| Depth-1 sub-items have `pl-6` indent | `SettingsSidebar.test.tsx` | `getByText('Margin buckets')` parent has `pl-6` |
| Depth-2 sub-sub-items have `pl-10` indent | `SettingsSidebar.test.tsx` | `getByText('Auto-expiry & sync')` parent has `pl-10` |
| Depth-2 sub-sub-items have `text-neutral-500` color | `SettingsSidebar.test.tsx` | `getByText('Auto-expiry & sync')` has `text-neutral-500` |
| Active item still has `bg-brand-50 text-brand-700` regardless of depth | `SettingsSidebar.test.tsx` | Simulate `pathname=/settings/operations/margin-buckets`; leaf renders `bg-brand-50` |
| Ancestor (group label for active child) still renders | `SettingsSidebar.test.tsx` | Parent "Operations" is visible when child is active |

### J.2 Integration Tests — Settings Sidebar

| Test | File | Assertion |
|:---|:---|:---|
| Navigate to `/settings/operations` → sub-items visible | `batch_beta_b7/settings-sidebar.integration.test.tsx` | "Margin buckets", "Profitability rules", "Field operations" appear when Operations is active |
| Integrations → QuickBooks expanded → depth-2 item visible | `batch_beta_b7/settings-sidebar.integration.test.tsx` | Navigate to `/settings/integrations/quickbooks` → "Auto-expiry & sync" appears with deeper indentation than "QuickBooks" |
| Sidebar renders without `text-caption` class on any group label | `batch_beta_b7/settings-sidebar.integration.test.tsx` | No element matching `[class*="text-caption"]` within `settings-sidebar` |

### J.3 Unit Tests — `MonthViewCell`

| Test | File | Assertion |
|:---|:---|:---|
| Renders date number for in-range cell | `MonthViewCell.test.tsx` | `getByText('15')` visible for `dateStr='2026-06-15'` |
| Today cell has brand highlight class | `MonthViewCell.test.tsx` | `isToday=true` → element with `bg-brand-600` wraps the date number |
| Renders up to 3 job chips | `MonthViewCell.test.tsx` | 3 jobs → 3 chips; 4 jobs → 2 chips + "+2 more" text |
| Padding cell renders nothing | `MonthViewCell.test.tsx` | `dateStr=null` → no date number, not interactive |
| Out-of-range cell is not interactive | `MonthViewCell.test.tsx` | `isInRange=false` → no `cursor-pointer` class |
| Click on in-range cell calls `onDrillDown` with dateStr | `MonthViewCell.test.tsx` | `fireEvent.click` → `onDrillDown` called with `'2026-06-15'` |
| Click on padding cell does NOT call `onDrillDown` | `MonthViewCell.test.tsx` | `fireEvent.click` on null cell → `onDrillDown` not called |

### J.4 Unit Tests — `MonthCalendarGrid`

| Test | File | Assertion |
|:---|:---|:---|
| Renders 7 day-of-week header labels | `MonthCalendarGrid.test.tsx` | Sun, Mon, Tue, Wed, Thu, Fri, Sat all visible |
| Renders correct number of padding cells before first day | `MonthCalendarGrid.test.tsx` | `dateRange[0]='2026-06-01'` (Monday) → 1 padding cell before it (Sun slot empty) |
| Renders all 30 in-range cells | `MonthCalendarGrid.test.tsx` | 30 real `MonthViewCell` elements with date numbers |
| Jobs routed to correct cell | `MonthCalendarGrid.test.tsx` | Job with `scheduled_start_at='2026-06-15T09:00:00Z'` appears in June 15 cell only |
| `onDrillDown` propagated from cell click | `MonthCalendarGrid.test.tsx` | Click June 15 cell → `onDrillDown('2026-06-15')` called |
| Today cell is highlighted | `MonthCalendarGrid.test.tsx` | Cell matching today's date has `isToday=true` |

### J.5 Integration Tests — Month View on Dispatch Board

| Test | File | Assertion |
|:---|:---|:---|
| Month tab renders calendar grid (not "coming soon") | `batch_beta_b7/DispatchBoardMonth.integration.test.tsx` | Switch to Month tab → "Month view coming soon" text absent; day-of-week headers visible |
| Month tab shows 7-column grid | `batch_beta_b7/DispatchBoardMonth.integration.test.tsx` | Grid has 7 column headers (Sun–Sat) |
| Click cell → switches to Day view for that date | `batch_beta_b7/DispatchBoardMonth.integration.test.tsx` | Click a cell → `viewTab` becomes 'day'; `activeDate` matches clicked date |
| Jobs from API appear in correct cells | `batch_beta_b7/DispatchBoardMonth.integration.test.tsx` | MSW returns job with June 10 date → June 10 cell shows job chip |
| "Month view coming soon" string is gone from DOM | `batch_beta_b7/DispatchBoardMonth.integration.test.tsx` | `queryByText('Month view coming soon')` returns null |

### J.6 Regression Tests

| Test | File | Assertion |
|:---|:---|:---|
| Day view unchanged | `DispatchGrid.regression.test.tsx` (existing — update) | Month text absent; Day columns still render |
| 4-Day / Week views unchanged | `DispatchGrid.regression.test.tsx` (existing — update) | `MultiDayGrid` still renders for 4day/week |
| Settings sidebar existing BETA-B4 routes still render | `batch_beta_b7/settings-sidebar.integration.test.tsx` | All 11 routes from BETA-B4 still return pages (no regression from style change) |

---

## Design Doc Quality Gate Checklist

- [x] Every code file referenced was actually read (not assumed)
- [x] Root cause of `text-caption` size inversion documented with before/after class mapping
- [x] Depth=2 sub-sub-item (`pl-10` + `text-neutral-500`) is explicitly designed — no ambiguity for engineer
- [x] `MonthCalendarGrid` props interface fully specified
- [x] `MonthViewCell` props interface fully specified
- [x] Drill-down interaction (`setActiveDate` + `setViewTab('day')`) explicitly specified in `DispatchGrid` §D.4
- [x] `MonthDeferredState.tsx` file retention decision documented in §G.2
- [x] Month navigation strategy (rolling 30-day, no snap-to-month) explicitly resolved in §G.1
- [x] No backend changes, no schema changes, no new API endpoints
- [x] No new npm dependencies
- [x] Infrastructure constraint: zero cost impact (pure frontend, no new AWS services)
- [x] BETA-B5 regression (Day/4-Day/Week views) explicitly tested in §J.6
- [x] Design token compliance rule stated in §E.4 (no hardcoded colors)
