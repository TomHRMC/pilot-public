# Design Spec: DISPATCH-B1 — Day Board Surfaces
# DispatchGridDayView · UnassignedTray · Lane|Tech PillToggle · ConflictPreviewPane Docking · JobContextMenu

**Batch**: DISPATCH-B1 (UI Design)
**Designer**: Pilot Web UI Designer
**Date authored**: 2026-07-26
**Scope**: Web only — `apps/web`. Mobile dispatch is out of scope.
**Architecture source**: `batch-dispatch-b1-design.md §H–I`
**Pattern reference**: `batch-ui-ds-b1-design-spec.md §Surface 2` (JobBlock, DragOverlay, context-menu classes)
**RBAC gate**: Entire dispatch board is wrapped in `<RoleGate role={["owner","operator"]}>`; `tech` role does not see this surface.
**Status**: Awaiting Tom's approval before implementation begins.

---

## Design Constraints (Applies to All Surfaces)

- All tokens from `pilotPreset` — **zero hex codes**.
- All icons: **Heroicons 2.0**, exact name specified per use, outline variant unless noted.
- Desktop-first, 1280px minimum design viewport.
- WCAG: every interactive element must have `focus-visible:ring-2 focus-visible:ring-brand-600`.
- `@dnd-kit` is the only DnD library on the day board — **no `react-dnd`**.
- `PointerSensor` with `activationConstraint: { distance: 8 }` on all draggable elements (prevents accidental drags on clicks — carried over from `DispatchBoardLanes.tsx`).
- Exact geometry constants inherited from `DispatchBoardLanes.tsx`:
  - `HOUR_WIDTH_PX = 80`
  - `LANE_HEIGHT_PX = 72` (reused as tech-row height in day-tech mode)
  - Time axis header height: `h-7` (28px)
  - Default viewport: 6 AM–6 PM; expands dynamically per `computeViewportHours()` logic.

---

## Overall Board Layout (Updated for B1)

The following ASCII shows the full authenticated dispatch board page shell after B1 lands. `UnassignedTray` is inserted between the toolbar and the board body. The right rail is a shared 320px slot.

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ AppSidebar (256px, z-30)                                                     │
│ ┌──────────────────────────────────────────────────────────────────────────┐ │
│ │ DispatchToolbar (h-auto, border-b border-neutral-200, bg-white)          │ │
│ │  [Day|Week|Month]  < Prev  [Today]  Next >  Mon Jul 28, 2026  [Lane|Tech]│ │
│ ├──────────────────────────────────────────────────────────────────────────┤ │
│ │ UnassignedTray (h-auto min-h-[44px], border-b, bg-neutral-50)            │ │
│ │  Unassigned (3)  [chip] [chip] [chip]  …                                 │ │
│ ├────────────────────────────────────────────────┬─────────────────────────┤ │
│ │  BOARD GRID AREA (flex-1, overflow-x-scroll)   │ RIGHT RAIL (w-80=320px) │ │
│ │                                                │                         │ │
│ │  DispatchBoardLanes  OR  DispatchGridDayView   │  ConflictPreviewPane    │ │
│ │  (switches on layoutMode from store)           │   OR                    │ │
│ │                                                │  JobPropertiesPanel     │ │
│ │                                                │  (never both — see §4)  │ │
│ └────────────────────────────────────────────────┴─────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────────┘
```

**Right-rail arbitration rule (§4)**: Only one panel may occupy the right rail at any moment. `DispatchBoardPage` renders:
```
{conflictPreviewOpen
  ? <ConflictPreviewPane ... />
  : selectedJob
    ? <JobPropertiesPanel ... />
    : null}
```
`ConflictPreviewPane` has **strict priority** over `JobPropertiesPanel` — a pending move must be committed or cancelled before properties editing can occur.

---

## Surface 1 — `DispatchGridDayView` (New Component)

### Overview

| Property | Value |
|---|---|
| File path | `apps/web/src/features/dispatch-board/components/DispatchGridDayView.tsx` |
| Status | **New** |
| Mounted by | `DispatchBoardPage` when `viewTab === "day" && layoutMode === "tech"` |
| DnD library | `@dnd-kit/core` (same `DndContext` as `DispatchBoardLanes`) |
| Layout | Time-across-horizontal × one row per tenant tech |
| Row height | `LANE_HEIGHT_PX = 72px` (matches day-lane row height) |
| Tech header col width | `128px` (wider than lane's `64px` to accommodate tech name + avatar) |
| Time axis height | `h-7` (28px) — matches `DispatchBoardLanes` |
| Hour width | `HOUR_WIDTH_PX = 80` — matches `DispatchBoardLanes` |
| Scroll | Horizontal scroll on board only; tech header column is sticky left |

### Component Interface

```ts
// DispatchGridDayView.tsx — props
interface DispatchGridDayViewProps {
  date: Date;
  techs: DispatchBoardTech[];              // ALL tenant techs — always render a row, even if empty
  jobs: ScheduledJob[];
  onJobClick: (job: ScheduledJob) => void;         // left-click → JobPropertiesPanel
  onJobDrop: (jobId: string, techId: string, startTime: Date) => void;  // → unified beginMove pipeline
  onJobContextMenu: (e: React.MouseEvent, job: ScheduledJob) => void;   // right-click → JobContextMenu
}
```

### ASCII Layout Diagram (1280px viewport, 3 techs)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ TECH HDR COL (128px, sticky left, bg-neutral-50, border-r border-neutral-200)│
│                  TIME AXIS HEADER (h-7 = 28px, bg-neutral-50, border-b)      │
│ [spacer h-7]  │  6 AM      7 AM      8 AM      9 AM     10 AM    11 AM  ...  │
├───────────────┼──────────────────────────────────────────────────────────────┤
│  [JR] Jake R. │                   [──── JobBlock ────]        [JobBlock]     │  h=72px
├───────────────┼──────────────────────────────────────────────────────────────┤
│  [MS] Maria S.│        [──── JobBlock ────]                                  │  h=72px
├───────────────┼──────────────────────────────────────────────────────────────┤
│  [DT] Dev T.  │  (empty row — always rendered, accepts drops)                │  h=72px
└───────────────┴──────────────────────────────────────────────────────────────┘
```

### Tech Row Header (Left Sticky Column)

| Element | Classes |
|---|---|
| Column root | `width: 128px; flex-shrink: 0; position: sticky; left: 0; z-index: 1` + `bg-neutral-50 border-r border-neutral-200` |
| Time-axis spacer cell | `h-7 border-b border-neutral-200` (aligns with time axis header) |
| Each tech row cell | `height: 72px; display: flex; align-items: center; gap: 8px; padding: 0 8px;` + `border-b border-neutral-100` |
| Tech avatar (initials) | `w-7 h-7 rounded-full bg-brand-100 flex items-center justify-center flex-shrink-0` |
| Avatar initials text | `text-caption font-bold text-brand-700` — initials derived from tech full name (first + last initial) |
| Tech name | `text-caption font-medium text-neutral-700 truncate` — max 1 line |

### Tech Row (Droppable Drop Zone)

Each tech row is a `useDroppable` region with `id: "tech-row-{techId}"` and `data: { techId }`.

| Property | Value |
|---|---|
| Height | `72px` (constant — `LANE_HEIGHT_PX`) |
| Width | `boardWidthPx` (computed same as `DispatchBoardLanes` — `totalViewHours × HOUR_WIDTH_PX`) |
| Position | `position: relative` — job blocks are absolutely positioned inside |
| Border | `border-b border-neutral-100` |
| Hour grid lines | Vertical `w-px bg-neutral-100` lines at each hour — matches `DispatchBoardLanes` pattern |

### JobBlock Positioning Inside Tech Row

Reuse **identical** `DraggableJobBlock` visual and absolute-positioning logic from `DispatchBoardLanes.tsx`. No visual redesign.

```
left = dateToPx(scheduled_start_at, viewStartHour)
width = max(20, dateToPx(scheduled_end_at, viewStartHour) - left)
top: 4px; bottom: 4px  (4px inset top and bottom within the 72px row)
```

The `DraggableJobBlock` component is extracted from `DispatchBoardLanes` into a shared file at `features/dispatch-board/components/JobBlock.tsx` so both `DispatchBoardLanes` and `DispatchGridDayView` import the same component. **No visual changes to the block itself.**

### Label Content on JobBlock

After Part A lands, the block renders:
1. **Primary line**: `title` (if non-null from B1.5 onward) else `job_number` — `text-caption font-semibold leading-tight truncate`
2. **Secondary line**: `customer_name` — `text-caption opacity-75 truncate`

### Over-Capacity State (Tech Row — Occupied Time Slot)

"Over-capacity" in day-tech mode means: a job is being dragged over a time window that **already contains another job for that tech** (overlap detected client-side before firing `beginMove`).

| State | Visual |
|---|---|
| Drop hover — slot free | `bg-brand-50/40 transition-colors` (same as day-lane free hover) |
| Drop hover — slot occupied | `bg-fault-50/40 transition-colors` + `cursor-not-allowed` on the drag overlay |
| Over-capacity chip | `absolute top-1 right-1` inside the row: `bg-fault-100 text-fault-700 text-caption font-medium rounded-full px-2 py-0.5` text: `"Conflict"` |

**Detection logic**: Client-side only (before hitting the pipeline). Check whether any job in `techJobs` for that tech has a time window overlapping `[proposedStart, proposedEnd]`. If overlap detected, fire `setOverCapacity(techId)` local state; do **not** call `onJobDrop` — instead show the over-capacity chip and discard the drop. The backend `/check-conflicts` pipeline runs only when the drop is clean client-side.

### DragOverlay (Day-Tech Mode)

Reuse identical `DragOverlay` ghost card from `DispatchBoardLanes`:
```
border border-brand-400 rounded px-3 py-2 bg-white shadow-lg
text-caption font-medium text-brand-700 opacity-90 pointer-events-none
```
Show `job_number` (or `title` when available) as the overlay label.

### Empty Tech Row

An empty tech row (no jobs for this tech today) **always renders** — it is a valid drop target. Visually it is just the blank row with hour grid lines, `bg-white` background, no placeholder text. The `useDroppable` hook is always applied — dropping a chip from `UnassignedTray` onto an empty row schedules the job.

### State Table

| State | Trigger | Visual |
|---|---|---|
| **Idle** | Board loaded, no drag | Normal row appearance; job blocks at computed positions |
| **Loading** | Board data fetching | `<LoadingState>` from `@pilot/ui` centered in the grid body |
| **Empty board** | No jobs and no techs | `<EmptyState>` centered: "No technicians configured" + `<button>` to go to settings |
| **No jobs, techs present** | All rows empty | All rows render with blank content; tray shows `Unassigned (0)` |
| **Drag active — source block** | `useDraggable isDragging` | Source job block: `opacity-30` |
| **Drag over free slot** | `useDroppable isOver` + no conflict | Row tint: `bg-brand-50/40` |
| **Drag over occupied slot** | `useDroppable isOver` + client-overlap | Row tint: `bg-fault-50/40`; overlay cursor: `cursor-not-allowed`; over-capacity chip shown |
| **Drop committed** | `onDragEnd` fires clean | `onJobDrop(jobId, techId, snappedStart)` → `beginMove` pipeline |
| **Drop rejected** | Occupied slot | Job returns to origin; no API call; over-capacity chip disappears after 1.5s |

### Interaction Spec

| Element | Interaction | Behavior |
|---|---|---|
| Job block | Left-click | `onJobClick(job)` → `JobPropertiesPanel` opens in right rail |
| Job block | Right-click | `onJobContextMenu(e, job)` → `JobContextMenu` at cursor |
| Job block | Drag (≥8px movement) | `DragOverlay` ghost follows cursor |
| Empty row | Drop | If free: `onJobDrop(jobId, techId, snappedStart)` |
| Over-capacity row | Drop attempt | Blocked client-side; over-capacity chip flash; no API call |
| Tech row | Keyboard drop | Not in B1 scope — noted for accessibility backlog |

### Animation Spec

| Transition | Property | Duration | Easing |
|---|---|---|---|
| Job block drag opacity | `opacity` | `150ms` | `ease` (via Tailwind `transition-opacity`) |
| Row hover tint | `background-color` | `150ms` | `ease` (via Tailwind `transition-colors`) |
| Over-capacity chip fade-out | `opacity` | `500ms` | `ease-out` (JS `setTimeout(1500)` + `transition-opacity duration-500`) |

---

## Surface 2 — `UnassignedTray` (New Component)

### Overview

| Property | Value |
|---|---|
| File path | `apps/web/src/features/dispatch-board/components/UnassignedTray.tsx` |
| Status | **New** |
| Mounted by | `DispatchBoardPage` — always, between `DispatchToolbar` and the board body |
| Purpose | Replaces the bottom `UnscheduledJobQueue` in `DispatchBoardLanes` |
| Test ID | `data-testid="unassigned-tray"` (required by architecture spec §I) |
| Visibility | Always rendered — even when empty. Shows `Unassigned (0)` label. |
| DnD | Chips are `useDraggable`; dragging out-of-tray schedules a job via the unified `beginMove` pipeline |

### Component Interface

```ts
// UnassignedTray.tsx — props
interface UnassignedTrayProps {
  jobs: DispatchBoardJob[];     // board.jobs where primary_assignment_id === null (unassigned)
  onJobClick: (job: DispatchBoardJob) => void;
  // drag-out handled by shared DndContext in DispatchBoardPage; chips are @dnd-kit useDraggable
}
```

### ASCII Layout Diagram

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ border-b border-neutral-200 · bg-neutral-50 · px-4 py-2                      │
│ Unassigned (3)  [chip: JOB-001 · Smith Home]  [chip: JOB-007 · Jones Apt]   │
│                 [chip: JOB-012 · Anon Client]  (overflow chips hidden +2 →) │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Pixel Spec

| Property | Value |
|---|---|
| Container height | Auto; `min-h-[44px]` to always occupy space even when empty |
| Container padding | `px-4 py-2` |
| Container background | `bg-neutral-50` |
| Container border | `border-b border-neutral-200` |
| Internal layout | `flex items-center gap-2 flex-wrap` |

### Component Inventory

| Element | Classes | Notes |
|---|---|---|
| Tray root | `flex items-center gap-2 px-4 py-2 min-h-[44px] border-b border-neutral-200 bg-neutral-50 flex-wrap` | `data-testid="unassigned-tray"` |
| Label | `text-caption font-semibold text-neutral-500 flex-shrink-0 mr-1` | Text: `"Unassigned ({count})"` — always visible including when `count === 0` |
| Empty message (count=0) | `text-caption text-neutral-400 italic` | Text: `"No unassigned jobs"` — renders after the label when `jobs.length === 0` |
| Chip (draggable) | `border border-neutral-300 rounded px-3 py-1.5 bg-white cursor-grab text-caption shadow-sm hover:border-brand-400 hover:shadow transition-all select-none max-w-[180px] flex-shrink-0` | `useDraggable({ id: job.id, data: { job } })` |
| Chip primary text | `text-caption font-medium text-neutral-800 truncate block` | Shows `job_number` (until `title` lands) |
| Chip secondary text | `text-caption text-neutral-500 truncate block` | Shows `customer_name` if present |
| Chip — dragging state | `opacity-30` | `isDragging` from `useDraggable` |

### State Table

| State | Trigger | Visual |
|---|---|---|
| **Empty** | `jobs.length === 0` | Label `Unassigned (0)` + italic `"No unassigned jobs"` text. Tray still occupies `min-h-[44px]`. |
| **Populated** | `jobs.length > 0` | Label + one chip per job, `flex-wrap` |
| **Chip dragging** | `isDragging === true` | Chip `opacity-30` in tray; `DragOverlay` ghost card follows cursor |
| **Chip dropped on tech row** (day-tech) | `onDragEnd` — `over.id` matches `"tech-row-{techId}"` | `onJobDrop(jobId, techId, snappedStart)` → `beginMove` pipeline |
| **Chip dropped on lane row** (day-lane) | `onDragEnd` — `over.id` matches `"lane-{laneIndex}"` | `onJobDrop(jobId, laneIndex, snappedStart)` → `beginMove` pipeline |
| **Chip dropped outside board** | `onDragEnd` — `over === null` | Job returns to tray; no API call |

### Interaction Spec

| Element | Interaction | Behavior |
|---|---|---|
| Chip | Left-click (no drag movement) | `onJobClick(job)` → opens `JobPropertiesPanel` in right rail |
| Chip | Keyboard Enter / Space | Same as left-click |
| Chip | Drag ≥8px | Activate `DragOverlay` ghost; chip becomes `opacity-30` |
| Tray (empty) | — | Read-only; the label and empty message are non-interactive |

### Animation Spec

| Transition | Property | Duration | Easing |
|---|---|---|---|
| Chip drag opacity | `opacity` | `150ms` | `ease` |
| Chip hover border/shadow | `border-color`, `box-shadow` | `150ms` | `ease` (via `transition-all`) |

### DispatchBoardLanes Modification

Remove the `<UnscheduledJobQueue>` from the bottom of `DispatchBoardLanes`. The `UnscheduledJobQueue` sub-component (and its `UnscheduledJobCard`) may be deleted from `DispatchBoardLanes.tsx` after `UnassignedTray` is mounted in `DispatchBoardPage`. The `unscheduledJobs` `useMemo` inside `DispatchBoardLanes` can also be removed.

---

## Surface 3 — Lane | Tech PillToggle in `DispatchToolbar`

### Overview

| Property | Value |
|---|---|
| File modified | `apps/web/src/features/dispatch-board/components/DispatchToolbar.tsx` |
| Status | **Modify** |
| Condition | Rendered only when `viewTab === "day"` |
| Default value | `"lane"` — matches `store.ts` default for `layoutMode` |
| Persistence | **Not persisted** — in-memory only (resets to `"lane"` on page reload) |
| Component reused | The existing `PillToggle<T>` generic component already in `DispatchToolbar.tsx` (line 87) — zero new component code needed |

### Props Added to `DispatchToolbarProps`

```ts
// Additions to DispatchToolbarProps interface
layoutMode?: 'lane' | 'tech';                   // only relevant when viewTab === "day"
onLayoutModeToggle?: (mode: 'lane' | 'tech') => void;
```

### Placement in Toolbar Row

The `Lane | Tech` toggle renders **after the date navigation group** and **before the `flex-1` spacer**, exactly where the `5-day | 7-day` toggle sits in week mode and the `Customer | Tech` toggle sits in month mode. The toolbar JSX condition:

```
{viewTab === "day" && onLayoutModeToggle && (
  <PillToggle<'lane' | 'tech'>
    options={[
      { value: "lane", label: "Lane" },
      { value: "tech", label: "Tech" },
    ]}
    value={layoutMode ?? "lane"}
    onChange={onLayoutModeToggle}
  />
)}
```

### Visual Spec (from existing `PillToggle` in `DispatchToolbar.tsx`)

| Element | Classes |
|---|---|
| Toggle outer | `bg-neutral-100 rounded-md p-0.5 inline-flex ml-2` |
| Active option pill | `bg-white shadow-sm rounded px-2.5 py-1 text-caption font-medium text-neutral-900` |
| Inactive option | `px-2.5 py-1 text-caption font-medium text-neutral-500` |
| Focus ring | `focus-visible:ring-2 focus-visible:ring-brand-600` (applied per-button inside `PillToggle`) |

**Option labels**: `"Lane"` / `"Tech"` — sentence case, no all-caps.

### Full Toolbar Row Diagram (Day view, both toggles active)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ [Day|Week|Month]  <  [Today]  >  Monday, July 28, 2026  [Lane|Tech]  ·····  │
│                                                          ↑ NEW (day only)    │
│                                                          ↑ After date label  │
└──────────────────────────────────────────────────────────────────────────────┘
```

### State Table

| State | Visual |
|---|---|
| `viewTab !== "day"` | Toggle not rendered at all |
| `viewTab === "day"`, `layoutMode === "lane"` | "Lane" pill is active (white + shadow); "Tech" is inactive (muted) |
| `viewTab === "day"`, `layoutMode === "tech"` | "Tech" pill is active; "Lane" is inactive |
| Toggle click | Immediate visual switch; `onLayoutModeToggle(newMode)` fires synchronously; board swaps render instantly |

### Animation Spec

No animation on toggle switch — the board content swap is a synchronous conditional render with no transition. The `PillToggle` pills themselves do not animate between states (matches existing 5-day/7-day and Customer/Tech toggle behavior).

---

## Surface 4 — `ConflictPreviewPane` Docking + Right-Rail Arbitration

### Overview

`ConflictPreviewPane.tsx` is **already fully styled** — its internal layout (header, scrollable body, footer buttons) requires no visual changes. This surface spec covers **only**:
1. Its mount position in `DispatchBoardPage`
2. The mutual exclusion rule with `JobPropertiesPanel`

### Current Problem

Both `ConflictPreviewPane` and `JobPropertiesPanel` are right-side inline panels:
- `JobPropertiesPanel`: `w-80 flex-shrink-0 flex flex-col h-full border-l border-neutral-200 bg-white` — 320px
- `ConflictPreviewPane`: `flex flex-col h-full` — no explicit width (currently unmounted anywhere)

If both mounted simultaneously, they would both render in the right rail and collapse the board grid.

### Resolution: Single Right-Rail Slot

**The right rail is a single `w-80` (320px) `flex-shrink-0` slot.** `DispatchBoardPage` renders exactly one child in it at a time, or nothing.

### Mount Spec for `ConflictPreviewPane`

Add `className="w-80 flex-shrink-0 flex flex-col h-full border-l border-neutral-200 bg-white shadow-lg"` to `ConflictPreviewPane`'s root `<div>` — matching `JobPropertiesPanel`'s root element exactly so both panels have identical box geometry.

> **Note for React Engineer**: This is a one-line `className` addition to the `<div>` at line 54 of `ConflictPreviewPane.tsx`. The internal layout (`flex flex-col h-full`) is unchanged.

### Right-Rail Arbitration in `DispatchBoardPage`

```
// Conceptual render logic — DispatchBoardPage
<div className="flex flex-row flex-1 min-h-0 overflow-hidden">
  {/* Board grid — takes remaining space */}
  <div className="flex-1 min-w-0 overflow-hidden">
    {viewTab === "day" && layoutMode === "lane"  && <DispatchBoardLanes ... />}
    {viewTab === "day" && layoutMode === "tech"  && <DispatchGridDayView ... />}
    {viewTab === "week"  && <DispatchWeekView ... />}
    {viewTab === "month" && <MonthCalendarGrid ... />}
  </div>

  {/* Right rail — exclusive slot, w-80, never both */}
  {conflictPreviewOpen
    ? <ConflictPreviewPane ... />
    : selectedJob
      ? <JobPropertiesPanel ... />
      : null}
</div>
```

### Priority Rules

| Scenario | Right-Rail Renders | Explanation |
|---|---|---|
| No job selected, no pending move | Nothing | Right rail is empty; board grid fills full width |
| Job clicked (left-click) | `JobPropertiesPanel` | Normal properties inspect flow |
| Job dragged + dropped → `beginMove` fires | `ConflictPreviewPane` opens | `store.openConflictPreview(jobId)` sets `conflictPreviewOpen = true`; `JobPropertiesPanel` is hidden (even if it was open) |
| Conflict pane: "Confirm move" clicked | `ConflictPreviewPane` closes | `store.closeConflictPreview()` sets `conflictPreviewOpen = false`; if `selectedJob` is still set, `JobPropertiesPanel` re-appears |
| Conflict pane: "Cancel" clicked | `ConflictPreviewPane` closes | Same as above — `JobPropertiesPanel` re-appears if a job was previously selected |

### Pixel Spec — `ConflictPreviewPane` Shell

| Property | Value |
|---|---|
| Width | `w-80` (320px) — added to root element |
| `flex-shrink-0` | Yes — prevents panel from collapsing when board grid is wide |
| Height | `h-full` — fills the board body height |
| Left border | `border-l border-neutral-200` — matches `JobPropertiesPanel` |
| Background | `bg-white` |
| Shadow | `shadow-lg` |
| z-index | No z-index needed — in normal document flow (not fixed/absolute) |

### State Table (Mount Conditions)

| `conflictPreviewOpen` | `selectedJob` | Right rail content |
|---|---|---|
| `true` | any | `ConflictPreviewPane` |
| `false` | non-null | `JobPropertiesPanel` |
| `false` | `null` | Empty (right rail not rendered) |

### ConflictPreviewPane Internal States (Existing — No Change)

| State | Visual |
|---|---|
| **Loading** (conflict check in-flight) | `"Checking conflicts…"` centered in body |
| **No conflicts** | Green check circle + `"No conflicts"` + `"This move looks good"` sub-text |
| **Warn conflicts** | `ConflictItem` list; proceed button = `bg-fault-600 "Move anyway (not recommended)"` |
| **Blocking conflicts** | Proceed button disabled (`disabled:opacity-50 disabled:cursor-not-allowed`) |
| **Move in-flight** | Both buttons disabled; proceed button text → `"Moving…"` |

---

## Surface 5 — `JobContextMenu` (New Shared Component)

### Overview

| Property | Value |
|---|---|
| File path | `apps/web/src/features/dispatch-board/components/JobContextMenu.tsx` |
| Status | **New** (extracted from `DispatchWeekView`'s inline right-click menu pattern) |
| Trigger | `onContextMenu` event (right-click) on any `DraggableJobBlock` in day-lane or day-tech modes |
| Menu items | `View Job` → `/jobs/{id}` · `Job Properties` → `JobPropertiesPanel` opens |
| Scope | B1: day-lane + day-tech. B1.5: week modes reuse same component unchanged. |

### Component Interface

```ts
// JobContextMenu.tsx — props
interface JobContextMenuProps {
  state: { x: number; y: number; job: ScheduledJob } | null;
  onClose: () => void;
  onViewJob: (job: ScheduledJob) => void;      // navigate to /jobs/{id}
  onJobProperties: (job: ScheduledJob) => void; // open JobPropertiesPanel
}
```

`state === null` → component renders nothing.
`state !== null` → menu renders at `position: fixed; top: {state.y}px; left: {state.x}px`.

### Pixel Spec

| Property | Value |
|---|---|
| Position | `fixed` at cursor coordinates (`state.x`, `state.y`) |
| z-index | `z-50` — above all board content |
| Width | `w-44` (176px, fixed) |
| Background | `bg-white` |
| Border | `border border-neutral-200` |
| Shadow | `shadow-lg` |
| Border radius | `rounded-md` |
| Padding | `py-1` (top and bottom only) |

### Menu Item Spec

| Element | Classes |
|---|---|
| Menu item button | `w-full text-left px-3 py-1.5 text-sm text-neutral-700 hover:bg-brand-50 hover:text-brand-700 cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-brand-600` |
| Icon (left of label) | `w-4 h-4 mr-2 inline-block align-text-bottom flex-shrink-0` |
| Divider (between items) | `border-t border-neutral-100 my-1` — used between menu sections if needed |

### Icon Inventory

| Menu Item | Icon | Heroicons Name |
|---|---|---|
| View Job | Arrow pointing to page | `ArrowTopRightOnSquareIcon` (outline, `w-4 h-4`) |
| Job Properties | Adjustments sliders | `AdjustmentsHorizontalIcon` (outline, `w-4 h-4`) |

### Menu Layout Diagram

```
┌────────────────────────────┐  ← w-44 (176px)
│  ↗ View Job                │  ← px-3 py-1.5 text-sm hover:bg-brand-50
│  ⚙ Job Properties          │  ← px-3 py-1.5 text-sm hover:bg-brand-50
└────────────────────────────┘
```

### Accessibility

| Property | Value |
|---|---|
| Menu root role | `role="menu"` |
| Menu item role | `role="menuitem"` |
| Focus on open | Focus moves to first menu item |
| Close on Escape | `document.addEventListener("keydown", …)` — `e.key === "Escape"` → `onClose()` |
| Close on click outside | `document.addEventListener("mousedown", …)` — outside `menuRef` → `onClose()` |
| Close on item click | Each item's `onClick` calls `onClose()` before the action |
| `aria-label` | Root element: `aria-label="Job options"` |

### Close Triggers

| Trigger | Behavior |
|---|---|
| Click menu item | Item action fires → `onClose()` |
| Click outside menu | `onClose()` |
| Press `Escape` | `onClose()` |
| Scroll board | `onClose()` (add `scroll` listener on board container, remove on close) |

### State Table

| `state` | Visual |
|---|---|
| `null` | Nothing rendered (component returns `null`) |
| `{ x, y, job }` | Menu renders at fixed `(x, y)` coordinates with 2 items |

### Integrating Into `DispatchBoardLanes`

Add `onContextMenu` handler to each `DraggableJobBlock` in `DispatchBoardLanes`:

```ts
// Inside DraggableJobBlock props — new prop
onContextMenu: (e: React.MouseEvent, job: ScheduledJob) => void;

// On the root div of DraggableJobBlock — new handler
onContextMenu={(e) => {
  e.preventDefault();
  onContextMenu(e, job);
}}
```

`DispatchBoardPage` holds `contextMenuState: { x, y, job } | null` and passes `setContextMenuState` down through `onJobContextMenu` prop of both `DispatchBoardLanes` and `DispatchGridDayView`. `JobContextMenu` is rendered **once** in `DispatchBoardPage` — not inside each row component.

---

## Icon Inventory (All Surfaces)

| Component | Icon Use | Heroicons Name | Variant | Size |
|---|---|---|---|---|
| `ConflictPreviewPane` close button | Close/dismiss | `XMarkIcon` | Outline | `w-4 h-4` |
| `JobContextMenu` — View Job | External navigation | `ArrowTopRightOnSquareIcon` | Outline | `w-4 h-4` |
| `JobContextMenu` — Job Properties | Settings/adjust | `AdjustmentsHorizontalIcon` | Outline | `w-4 h-4` |
| `UnassignedTray` | No icon needed | — | — | — |
| `DispatchGridDayView` tech header | No icon — initials only | — | — | — |

> **Note**: The existing close button SVG in `ConflictPreviewPane.tsx` (lines 68–81) is a hand-drawn `<path d="M4 4l8 8M12 4l-8 8">` — replace with `XMarkIcon` from `@heroicons/react/24/outline` for consistency.

---

## Implementation Notes

1. **`DndContext` ownership**: `DispatchBoardPage` owns the single `DndContext` wrapping `UnassignedTray` + the active grid (both `DispatchBoardLanes` and `DispatchGridDayView` must be inside this context, not wrap their own). The `onDragEnd` in `DispatchBoardPage` dispatches to `beginMove`. This replaces the per-component `DndContext` currently in `DispatchBoardLanes.tsx` — the React Engineer must extract `DndContext` up to the page level.

2. **Snapping**: Both `DispatchBoardLanes` and `DispatchGridDayView` snap dropped times to 15-minute increments using the existing `snapTo15Min()` utility from `DispatchBoardLanes.tsx`. Extract this to `features/dispatch-board/utils/timeHelpers.ts` so both components share it.

3. **`DraggableJobBlock` extraction**: Extract the `DraggableJobBlock` sub-component from `DispatchBoardLanes.tsx` into `features/dispatch-board/components/JobBlock.tsx`. Both lane and tech day views import from there. **No visual changes.**

4. **`layoutMode` store field**: `store.ts` additions `layoutMode: 'lane' | 'tech'` (default `'lane'`) + `setLayoutMode` per §E.5 of the architecture doc. Not persisted — no `persist` middleware. `DispatchToolbar` reads and sets this value.

5. **`TECH_HEADER_WIDTH_PX = 128`**: Add this constant to `DispatchGridDayView.tsx` (analogous to `LANE_LABEL_WIDTH_PX = 64` in `DispatchBoardLanes.tsx`). It is wider because tech names need more space than `L1`/`L2` labels.

6. **Job label**: Until `title` exists on `ScheduledJob` (lands with JOB-UI-B1), render `job_number` in all job blocks and chips. The `DispatchBoardJobEntry` in Part A exposes `title: null` as a forward-compat field — check `title ?? job_number`.

7. **Conflict check flow** (for React Engineer — not a visual spec): The unified `beginMove(jobId, techId, start, end)` function in `DispatchBoardPage`:
   - Step 1: `setPendingMove({ jobId, techId, start, end })`
   - Step 2: `checkConflicts.mutate(...)` → fires `POST /scheduling/jobs/{id}/check-conflicts`
   - Step 3: On response: `store.openConflictPreview(jobId)` → `conflictPreviewOpen = true` → `ConflictPreviewPane` mounts in right rail (pushes `JobPropertiesPanel` out)
   - Step 4 (Proceed): `moveJob.mutate(...)` → `POST /scheduling/jobs/{id}/move`
   - Step 5 (Cancel): `store.closeConflictPreview()` → pane unmounts

8. **Accessibility for `DispatchGridDayView` rows**: Each `DroppableTechRow` should have `role="region"` + `aria-label="Schedule row for {techName}"`, matching the `aria-label` pattern in `DispatchBoardLanes`'s `DroppableLaneRow`.

9. **Mobile fallback**: `DispatchGridDayView` renders a mobile fallback below `md` (768px) identical to the Week view fallback: centered text `"Tech view is available on desktop"` + `<button>` to switch to Lane mode.

---

## Component Manifest

| File | Action | Description |
|---|---|---|
| `apps/web/src/features/dispatch-board/components/DispatchGridDayView.tsx` | **New** | Day-tech mode grid — time axis × one row per tech, `@dnd-kit` |
| `apps/web/src/features/dispatch-board/components/UnassignedTray.tsx` | **New** | Horizontal unassigned chips strip above board; `data-testid="unassigned-tray"` |
| `apps/web/src/features/dispatch-board/components/JobContextMenu.tsx` | **New** | Shared right-click context menu for day-lane + day-tech job cards |
| `apps/web/src/features/dispatch-board/components/JobBlock.tsx` | **New** | `DraggableJobBlock` extracted from `DispatchBoardLanes` — shared between both day views |
| `apps/web/src/features/dispatch-board/components/DispatchToolbar.tsx` | **Modify** | Add `layoutMode` + `onLayoutModeToggle` props; render `Lane\|Tech` `PillToggle` when `viewTab === "day"` |
| `apps/web/src/features/dispatch-board/components/DispatchBoardLanes.tsx` | **Modify** | Remove `<UnscheduledJobQueue>` and its sub-component; add `onContextMenu` prop + handler to `DraggableJobBlock`; import `JobBlock` from shared file; remove own `DndContext` (lifted to page) |
| `apps/web/src/features/dispatch-board/components/ConflictPreviewPane.tsx` | **Modify** | Add `w-80 flex-shrink-0 border-l border-neutral-200 shadow-lg` to root `<div>` className; replace hand-drawn close SVG with `XMarkIcon` from `@heroicons/react/24/outline` |
| `apps/web/src/features/dispatch-board/components/DispatchBoardPage.tsx` | **Modify** | Mount `UnassignedTray` between toolbar and board; render `DispatchGridDayView` vs `DispatchBoardLanes` on `layoutMode`; implement right-rail arbitration; mount `JobContextMenu` at page level; lift `DndContext` to page; implement `beginMove` unified pipeline |
| `apps/web/src/features/dispatch-board/utils/timeHelpers.ts` | **New** | Extract `snapTo15Min`, `dateToPx`, `pxToDate`, `computeViewportHours` from `DispatchBoardLanes` — shared utilities |
| `apps/web/src/features/dispatch-board/store.ts` | **Modify** | Add `layoutMode: 'lane' \| 'tech'` (default `'lane'`, not persisted) + `setLayoutMode`; activate `conflictPreviewOpen`/`conflictPreviewJobId` fields (currently orphaned) |

---

## Handoff Gate

This spec is ready for Tom's review. Implementation starts only after approval.

---

*Spec authored by Pilot Web UI Designer, 2026-07-26. Source reads: `batch-dispatch-b1-design.md §H–I`, `batch-ui-ds-b1-design-spec.md §Surface 2`, `DispatchBoardLanes.tsx`, `DispatchToolbar.tsx`, `ConflictPreviewPane.tsx`, `JobPropertiesPanel.tsx`. Week surfaces (`DispatchWeekLaneView`, week-tech transpose) are explicitly out of scope — deferred to DISPATCH-B1.5.*
