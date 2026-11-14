# Design Spec: DISPATCH-B1.5 — Week-Lane Grid
# DispatchWeekLaneView · Lane|Tech Toggle (Week) · DispatchBoardPage Week Routing

**Batch**: DISPATCH-B1.5 (UI Design)
**Designer**: Pilot Web UI Designer
**Date authored**: 2026-07-26
**Scope**: Web only — `apps/web`. Mobile dispatch is out of scope.
**Architecture source**: `batch-dispatch-b1-design.md §Split` (geometry correction 2026-07-26)
**Pattern reference (mirror from)**: `dispatch-b1-ui-design-spec.md` — all tokens, `JobBlock` visual, `UnassignedTray`, `PillToggle`, `ConflictPreviewPane` docking, `JobContextMenu`
**Structural template**: `DispatchWeekView.tsx` — week-lane grid mirrors this layout exactly (lanes-as-columns instead of techs-as-columns)
**Lane logic source**: `DispatchBoardLanes.tsx` — `assignJobsToLanes` + `checkLaneAvailability` concepts reused per-day
**Prerequisite**: DISPATCH-B1 fully merged (pipeline, `UnassignedTray`, `layoutMode` store field, `JobBlock.tsx`, `timeHelpers.ts`, `JobContextMenu.tsx`)
**RBAC gate**: Entire dispatch board is wrapped in `<RoleGate role={["owner","operator"]}>` — unchanged from B1.
**Status**: Awaiting Tom's approval before implementation begins.

---

## Design Constraints (Applies to All Surfaces)

- All tokens from `pilotPreset` — **zero hex codes**.
- All icons: **Heroicons 2.0**, exact name specified per use, outline variant unless noted.
- Desktop-first, 1280px minimum design viewport.
- WCAG: every interactive element must have `focus-visible:ring-2 focus-visible:ring-brand-600`.
- `@dnd-kit` is the only DnD library — **no `react-dnd`**.
- `PointerSensor` with `activationConstraint: { distance: 8 }` on all draggable elements (prevents accidental drags on clicks — same constraint as `DispatchWeekView.tsx`).
- **No commitment chips in lane mode** — `WeekCommitmentChip` is a tech-mode-only concept (DISPATCH-B1.25). `DispatchWeekLaneView` renders primary job cards only; helper/crew assignments are not displayed in lane mode. This is explicitly confirmed and must be noted in implementation notes.

---

## Locked Geometry (Tom-approved 2026-07-26)

The dispatch board's Lane/Tech toggle swaps the **column** dimension only. Days are always rows.

| View | Rows | Columns | Status |
|---|---|---|---|
| Week-tech (`DispatchWeekView`) | Days (5 or 7) | Techs (N) | **EXISTS — untouched** |
| **Week-lane (`DispatchWeekLaneView`)** | Days (5 or 7) | Lanes (1–5, capped by `useScheduleLaneCount`) | **NEW — this spec** |

**Always render the full empty column set**: all lane columns render even when a day/lane cell is empty — every cell is a valid drop target and a source for pulling a job from `UnassignedTray`.

---

## Overall Board Layout (B1.5 Additions)

B1.5 changes only the `viewTab === "week"` routing inside `DispatchBoardPage`. The outer shell (header, `UnassignedTray`, right rail) is unchanged from B1. The ASCII below shows the full board with `viewTab === "week"`, `layoutMode === "lane"`.

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ AppSidebar (256px, z-30)                                                     │
│ ┌──────────────────────────────────────────────────────────────────────────┐ │
│ │ DispatchToolbar (h-auto, border-b border-neutral-200, bg-white)          │ │
│ │  [Day|Week|Month]  < Prev [Today] Next >  Week of Jul 28  [5d|7d] [Lane|Tech] │
│ │                                                        ↑          ↑ B1.5 │ │
│ │                                           (retained)  (now also week)    │ │
│ ├──────────────────────────────────────────────────────────────────────────┤ │
│ │ UnassignedTray (h-auto min-h-[44px], border-b, bg-neutral-50)            │ │
│ │  Unassigned (2)  [chip: JOB-042 · Monroe HVAC]  [chip: JOB-051 · Davis] │ │
│ ├────────────────────────────────────────────────┬─────────────────────────┤ │
│ │  BOARD GRID AREA (flex-1, overflow-auto)        │ RIGHT RAIL (w-80=320px) │ │
│ │                                                │                         │ │
│ │  DispatchWeekLaneView                          │  ConflictPreviewPane    │ │
│ │  (days-as-rows × lane-as-columns)              │   OR                    │ │
│ │                                                │  JobPropertiesPanel     │ │
│ │                                                │  (never both — B1 rule) │ │
│ └────────────────────────────────────────────────┴─────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────────┘
```

The **right-rail arbitration rule** from `dispatch-b1-ui-design-spec.md §Surface 4` applies unchanged — `ConflictPreviewPane` has strict priority over `JobPropertiesPanel`.

---

## Surface 1 — `DispatchWeekLaneView` (New Component)

### Overview

| Property | Value |
|---|---|
| File path | `apps/web/src/features/dispatch-board/components/DispatchWeekLaneView.tsx` |
| Status | **New** |
| Mounted by | `DispatchBoardPage` when `viewTab === "week" && layoutMode === "lane"` |
| DnD library | `@dnd-kit/core` — same `DndContext` owned by `DispatchBoardPage` (no internal `DndContext`) |
| Layout | `<table>` structure: sticky day row header (left column) × lane columns across the top |
| Row dimension | Days: 5 (Mon–Fri) or 7 (Mon–Sun) — controlled by `daysToShow` prop (existing 5d/7d toggle) |
| Column dimension | Lanes: `laneCount` columns (1–5, from `useScheduleLaneCount`, Founders cap = 5) |
| Always-render columns | **Yes** — all `laneCount` columns render even when a day/lane cell is empty |
| Cell minimum height | `min-h-[80px]` — matches `DispatchWeekView`'s `WeekCell` |
| Sticky row header width | `96px` (`ROW_HEADER_WIDTH_PX = 96`) — identical to `DispatchWeekView` |
| Lane column min-width | `160px` (`LANE_COL_WIDTH_PX = 160`) — identical to `COL_WIDTH_PX` in `DispatchWeekView` |
| Scroll | Horizontal + vertical scroll on grid body; day row header column is sticky left (`position: sticky; left: 0; z-index: 10`); lane column headers are sticky top (`position: sticky; top: 0; z-index: 20`) |
| Mobile | `md:hidden` fallback — matches `DispatchWeekView` (see §Mobile Fallback) |
| Commitment chips | **None** — lane mode shows primary job assignments only. No `WeekCommitmentChip`. |

### Component Interface

```ts
// DispatchWeekLaneView.tsx — props
export interface DispatchWeekLaneViewProps {
  /** Any date in the target week — Monday is computed internally */
  weekStartDate: string;
  /** 5 (Mon–Fri) or 7 (Mon–Sun) */
  daysToShow: 5 | 7;
  /** Number of lanes from useScheduleLaneCount — max 5 (Founders cap) */
  laneCount: number;
  /** All jobs in the week range (scheduled + unassigned with dates) */
  jobs: DispatchBoardJob[];
  /**
   * Called when a job card is dropped onto a cell.
   * laneIndex is 0-based. Fires → beginMove unified pipeline in DispatchBoardPage.
   */
  onJobDrop: (
    jobId: string,
    laneIndex: number,
    dateStr: string,
    newStartTime: Date,
  ) => Promise<void>;
  /** Left-click → JobPropertiesPanel */
  onJobClick: (job: DispatchBoardJob) => void;
  /** Right-click → JobContextMenu (shared component, rendered by DispatchBoardPage) */
  onJobContextMenu: (e: React.MouseEvent, job: DispatchBoardJob) => void;
  /** Called when user taps "View Today" on mobile fallback */
  onNavigateToDate: (dateStr: string) => void;
  /** Called when user switches away from week view on mobile fallback */
  onViewTabChange?: (tab: DispatchViewTab) => void;
}
```

### Layout Constants

```ts
// DispatchWeekLaneView.tsx — top-level constants
const LANE_COL_WIDTH_PX = 160;  // min-width per lane column — matches COL_WIDTH_PX in DispatchWeekView
const ROW_HEADER_WIDTH_PX = 96; // sticky day row header — matches DispatchWeekView
const CAPACITY_LIMIT = 4;       // max stacked job cards in one day×lane cell before drop blocked
```

### ASCII Layout Diagram (1280px viewport, 5 lanes, 5-day week)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ TABLE (min-width: ROW_HEADER_WIDTH_PX + laneCount × LANE_COL_WIDTH_PX)      │
│                                                                               │
│ ┌──────────┬──────────────┬──────────────┬──────────────┬──────────────┬──────────────┐
│ │ [corner] │    L1        │    L2        │    L3        │    L4        │    L5        │ ← thead, sticky top, z-20
│ │ 96px     │   160px      │   160px      │   160px      │   160px      │   160px      │
│ │ bg-white │ bg-white     │ bg-white     │ bg-white     │ bg-white     │ bg-white     │
│ │ border-b │ border-r/b   │ border-r/b   │ border-r/b   │ border-r/b   │ border-r/b   │
│ ├──────────┼──────────────┼──────────────┼──────────────┼──────────────┼──────────────┤
│ │ Mon      │ [WeekLane    │ [WeekLane    │ (empty cell) │ (empty cell) │ (empty cell) │ ← row: height auto, min-h-[80px]
│ │ Jul 28   │  JobCard]    │  JobCard]    │  dashed bg   │  dashed bg   │  dashed bg   │
│ │ sticky   │              │              │              │              │              │
│ │ left     │ [WeekLane    │              │              │              │              │
│ │ z-10     │  JobCard]    │              │              │              │              │
│ ├──────────┼──────────────┼──────────────┼──────────────┼──────────────┼──────────────┤
│ │ Tue ●    │ (empty)      │ [WeekLane    │ [WeekLane    │ (empty cell) │ (empty cell) │ ← ● = today highlight
│ │ Jul 29   │  dashed bg   │  JobCard]    │  JobCard]    │  dashed bg   │  dashed bg   │
│ ├──────────┼──────────────┼──────────────┼──────────────┼──────────────┼──────────────┤
│ │ Wed      │ …            │ …            │ …            │ …            │ …            │
│ ├──────────┼──────────────┼──────────────┼──────────────┼──────────────┼──────────────┤
│ │ Thu      │ …            │ …            │ …            │ …            │ …            │
│ ├──────────┼──────────────┼──────────────┼──────────────┼──────────────┼──────────────┤
│ │ Fri      │ …            │ …            │ …            │ …            │ …            │
│ └──────────┴──────────────┴──────────────┴──────────────┴──────────────┴──────────────┘
└──────────────────────────────────────────────────────────────────────────────┘
```

### Lane Column Header (`<thead>`)

The column headers row is sticky at the top (`position: sticky; top: 0; z-index: 20`) so lane labels remain visible when scrolling vertically on long weeks.

| Element | Classes | Notes |
|---|---|---|
| `<thead>` row | `sticky top-0 z-20` | Keeps headers visible on vertical scroll |
| Corner `<th>` (top-left) | `sticky left-0 z-30 bg-white border-r border-b border-neutral-200` + `min-w-24 w-24 px-2 py-2` | z-30 so corner stays above both sticky axes |
| Lane `<th>` | `border-r border-b border-neutral-200 min-w-40 px-3 py-3 bg-white text-center` | `min-w-40 = 160px` |
| Lane label text | `text-caption font-semibold text-neutral-500 uppercase tracking-wide` | Text: `"L1"` … `"L5"` — no avatar, no tech name |

**Rationale for text-only headers**: Lane columns have no avatar or individual identity — they are anonymous schedule slots. `L1`…`L5` labels are sufficient and match the label pattern from `DispatchBoardLanes.tsx`.

### Day Row Header (`<th scope="row">`)

Mirrors the sticky day header from `DispatchWeekView.tsx` exactly — same classes, same today-highlight logic.

| Element | Classes | Today variant |
|---|---|---|
| Row `<th>` root | `sticky left-0 z-10 border-r border-b border-neutral-200 min-w-24 w-24 px-2 py-2 text-left` | `bg-brand-50` (today) / `bg-white` (other days) |
| Weekday label | `text-caption font-semibold uppercase tracking-wide` | `text-brand-600` (today) / `text-neutral-500` (other) |
| Date label | `text-body font-bold` | `text-brand-700` (today) / `text-neutral-800` (other) |

### `WeekLaneCell` — Droppable Cell (Lane × Day)

Each cell is a `useDroppable` with `id: "cell-lane{laneIndex}-{dateStr}"` and `data: { laneIndex: number; dateStr: string }`.

| Property | Value |
|---|---|
| Drop ID | `cell-lane{laneIndex}-{dateStr}` — e.g. `"cell-lane0-2026-07-28"` |
| Drop data | `{ laneIndex: number; dateStr: string }` |
| Min height | `min-h-[80px]` |
| Cell padding | `p-1.5` |
| Internal layout | `flex flex-col gap-1` |

#### Cell State Classes

| State | Classes |
|---|---|
| Default (has jobs) | `border-r border-b border-neutral-200 transition-colors` |
| Empty cell | `border border-dashed border-neutral-200 rounded bg-neutral-50/50` (matches `WeekCell` empty state in `DispatchWeekView.tsx`) |
| Drag over — cell free | `bg-brand-50/40` |
| Drag over — over capacity | `bg-fault-50/40 border-fault-200` |

#### Per-Day Lane Assignment Logic

The `DispatchWeekLaneView` runs `assignJobsToLanes` **once per day row** to determine which jobs belong in which lane column for that day. This is the same earliest-free-slot algorithm from `DispatchBoardLanes.tsx`, now imported from `features/dispatch-board/utils/laneHelpers.ts` (or re-exported from the same place B1 extracts it).

```ts
// Per-day lane assignment (runs in useMemo keyed to [jobs, laneCount, weekDates])
// For each dateStr in weekDates:
const dayJobs = jobs.filter(j => j.scheduled_start_at?.startsWith(dateStr));
const laneAssignment = assignJobsToLanes(dayJobs, laneCount);
// → Map<jobId, laneIndex>
// Produces: jobsByDayAndLane[dateStr][laneIndex] = DispatchBoardJob[]
```

This means each `WeekLaneCell` at `(day, lane)` receives the array of jobs assigned to that lane on that day. Multiple jobs can appear in the same lane cell if they are non-overlapping (the algorithm places sequential non-overlapping jobs in the same lane).

**Jobs stacked within a cell are sorted by `scheduled_start_at` ascending** — matching `WeekCell`'s sort in `DispatchWeekView.tsx`.

#### Over-Capacity Detection (Client-Side)

Over-capacity for a week-lane cell: `jobs.length >= CAPACITY_LIMIT` (where `CAPACITY_LIMIT = 4`). This is the same threshold as week-tech. When a drag is over a cell at capacity, show the over-capacity chip and block the drop.

| Element | Classes |
|---|---|
| Over-capacity chip | `absolute top-1 right-1 bg-fault-100 text-fault-700 text-caption rounded-full px-2 py-0.5 font-medium z-10 pointer-events-none` |
| Chip text | `"Capacity exceeded"` |

### `WeekLaneJobCard` — Job Card Inside a Cell

The job card in `DispatchWeekLaneView` uses the **same visual as `WeekJobCard`** in `DispatchWeekView.tsx`, with one key difference: **no tech `display_color` border** (lane mode has no tech dimension). The left border uses the neutral fallback color token instead of `tech.display_color`.

**No `WeekCommitmentChip` in lane mode** — this is confirmed design intent. Lane mode shows primary job assignments only. Helper/crew commitment rendering is a tech-mode feature (B1.25) and must not appear here.

#### Pixel Spec

| Property | Value |
|---|---|
| Card root | `flex flex-col rounded border bg-white shadow-sm cursor-grab select-none overflow-hidden text-caption hover:shadow transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-600` |
| Left accent border | `border-l-[3px] border-l-neutral-300` (no tech color — lane mode is tech-agnostic) |
| Dragging state | `opacity-30` (via `isDragging` from `useDraggable`) |
| Card padding | `px-2 py-1` |

#### Label Content (inside card, per B1 label spec)

| Line | Content | Classes |
|---|---|---|
| **Time range** (if `scheduled_start_at` present) | `"8:00 AM – 10:30 AM"` format | `text-caption text-neutral-500 font-medium mb-0.5 leading-tight` |
| **Primary label** | `title ?? job_number` (forward-compat: `title` null until JOB-UI-B1; fall back to `job_number`) | `text-caption font-semibold text-neutral-900 leading-tight truncate` |
| **Customer name** | `customer_name` if present | `text-caption text-neutral-500 truncate` |

**End-time rendering**: The time range line shows both start and end times when `scheduled_end_at` is present. This matches the existing `WeekJobCard` pattern at `DispatchWeekView.tsx` — no change needed.

#### Draggable Behavior

Each `WeekLaneJobCard` is a `useDraggable` with:
```ts
useDraggable({
  id: `job-${job.id}`,
  data: { jobId: job.id, job } satisfies DragData,
})
```

**Only the primary job card is draggable** — this is consistent with the architecture requirement: "Only the primary job block is draggable; a move reschedules the whole crew." Lane mode has no commitment chips, so this distinction is implicit.

### `DragOverlay` (Week-Lane Mode)

Identical ghost card to `DispatchWeekView`'s `DragOverlay` — reuse same classes:

```
border border-brand-400 rounded px-3 py-2 bg-white shadow-lg
text-caption font-medium text-brand-700 opacity-90 pointer-events-none
```

Show `title ?? job_number` as overlay label (same `activeDragJob` state pattern as `DispatchWeekView`).

### Drop Handler Logic

`DispatchWeekLaneView` fires `onJobDrop(jobId, laneIndex, dateStr, newStartTime)` from `handleDragEnd`. The `beginMove` unified pipeline in `DispatchBoardPage` handles the rest.

**Time-of-day preservation on date change** — mirror the logic from `DispatchWeekView.tsx`:

```ts
// Preserve time-of-day from source job when moving to a new date
if (job.scheduled_start_at) {
  const origStart = new Date(job.scheduled_start_at);
  const pad = (n: number) => String(n).padStart(2, "0");
  const timeOfDay = `T${pad(origStart.getUTCHours())}:${pad(origStart.getUTCMinutes())}:${pad(origStart.getUTCSeconds())}.000Z`;
  newStartTime = new Date(`${dateStr}${timeOfDay}`);
} else {
  newStartTime = new Date(`${dateStr}T08:00:00.000Z`); // fallback
}
```

### State Table

| State | Trigger | Visual |
|---|---|---|
| **Idle** | Board loaded, no drag | Normal grid; job cards in computed lane cells; empty cells show dashed border |
| **Loading** | Board data fetching | `<LoadingState>` from `@pilot/ui` centered in the grid body (inside `md:flex`) |
| **Empty week** | No jobs this week | All cells render with dashed border pattern; `UnassignedTray` shows `Unassigned (0)` |
| **No lanes configured** | `laneCount === 0` | `<EmptyState>` centered: `"No schedule lanes configured"` + link to settings |
| **Drag active — source card** | `isDragging === true` | Source card: `opacity-30` |
| **Drag over free cell** | `isOver && jobs.length < CAPACITY_LIMIT` | Cell: `bg-brand-50/40` |
| **Drag over full cell** | `isOver && jobs.length >= CAPACITY_LIMIT` | Cell: `bg-fault-50/40 border-fault-200`; `"Capacity exceeded"` chip top-right |
| **Drop — free cell** | `onDragEnd` — cell under capacity | `onJobDrop(jobId, laneIndex, dateStr, newStartTime)` → `beginMove` pipeline |
| **Drop — full cell** | `onDragEnd` — at capacity | Drop blocked; no API call; job returns to origin; chip flashes for 1.5s then fades |
| **Drop — outside grid** | `onDragEnd`, `over === null` | Job returns to origin; no API call |
| **Mobile** | Viewport < `md` (768px) | `md:hidden` fallback (see §Mobile Fallback) |

### Interaction Spec

| Element | Interaction | Behavior |
|---|---|---|
| Job card | Left-click | `onJobClick(job)` → `JobPropertiesPanel` opens in right rail |
| Job card | Right-click | `onJobContextMenu(e, job)` → `JobContextMenu` at cursor (rendered at page level) |
| Job card | Drag ≥ 8px | `DragOverlay` ghost card follows cursor; source card `opacity-30` |
| Empty cell | Drop (any job) | If under capacity: `onJobDrop(...)` → `beginMove` |
| Full cell | Drop attempt | Blocked client-side; over-capacity chip shown; no API call |
| Today's row header | — | Row `<th>` uses `bg-brand-50`; weekday label `text-brand-600`; date label `text-brand-700` |
| Column header `L1`…`L5` | — | Non-interactive; `text-neutral-500` |

### Animation Spec

| Transition | Property | Duration | Easing |
|---|---|---|---|
| Job card drag opacity | `opacity` | `150ms` | `ease` (via Tailwind `transition-opacity`) |
| Cell drag-over tint | `background-color` | `150ms` | `ease` (via Tailwind `transition-colors`) |
| Over-capacity chip fade-out | `opacity` | `500ms` | `ease-out` (JS `setTimeout(1500)` + `transition-opacity duration-500`) |

### Mobile Fallback

Below `md` (768px), `DispatchWeekLaneView` renders a fallback identical in structure to `DispatchWeekView`'s mobile fallback (`DispatchWeekView.tsx`).

```
┌──────────────────────────────────────────────────────┐
│                                                      │
│   Week view is available on desktop.                 │
│                                                      │
│          [ View Today ]                              │
│                                                      │
└──────────────────────────────────────────────────────┘
```

| Element | Classes |
|---|---|
| Fallback root | `md:hidden flex flex-col items-center justify-center py-12 text-neutral-600 text-sm text-center px-4` |
| Text | `"Week view is available on desktop."` |
| Button | `mt-3 px-4 py-2 border border-brand-200 bg-brand-50 text-brand-700 text-sm font-medium rounded-md hover:bg-brand-100` |
| Button label | `"View Today"` |
| Button action | `onViewTabChange?.("day"); onNavigateToDate(todayStr)` |

The desktop grid renders inside `<div className="hidden md:flex flex-col h-full overflow-hidden">` — same pattern as `DispatchWeekView`.

---

## Surface 2 — Lane | Tech Toggle in `DispatchToolbar` (Week Mode)

### Overview

| Property | Value |
|---|---|
| File modified | `apps/web/src/features/dispatch-board/components/DispatchToolbar.tsx` |
| Status | **Modify** (B1 already added it for `viewTab === "day"`; B1.5 extends it to `viewTab === "week"`) |
| Condition | Rendered when `viewTab === "day"` **OR** `viewTab === "week"` |
| 5-day / 7-day toggle | Retained and visible in week mode regardless of `layoutMode` |

### B1 vs B1.5 Condition Change

**B1 (existing)**:
```ts
{viewTab === "day" && onLayoutModeToggle && (
  <PillToggle ... />
)}
```

**B1.5 (new)**:
```ts
{(viewTab === "day" || viewTab === "week") && onLayoutModeToggle && (
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

No visual change to the toggle itself — same `PillToggle` component, same classes from `dispatch-b1-ui-design-spec.md §Surface 3`.

### Full Toolbar Row Diagram (Week view, both toggles visible)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ [Day|Week|Month]  <  [Today]  >  Week of Jul 28, 2026  [5d|7d]  [Lane|Tech]  │
│                                                        ↑         ↑           │
│                                                  (existing)   (B1.5: now    │
│                                                               also in week)  │
└──────────────────────────────────────────────────────────────────────────────┘
```

### State Table

| State | Visual |
|---|---|
| `viewTab === "month"` | Neither `Lane\|Tech` toggle nor `5d\|7d` toggle rendered |
| `viewTab === "day"`, `layoutMode === "lane"` | `Lane` pill active; `Tech` inactive — unchanged from B1 |
| `viewTab === "day"`, `layoutMode === "tech"` | `Tech` pill active; `Lane` inactive — unchanged from B1 |
| `viewTab === "week"`, `layoutMode === "lane"` | `5d\|7d` toggle visible + `Lane` pill active in `Lane\|Tech` toggle |
| `viewTab === "week"`, `layoutMode === "tech"` | `5d\|7d` toggle visible + `Tech` pill active in `Lane\|Tech` toggle |

**Toggle persistence**: `layoutMode` is **not persisted** — in-memory only. Survives Day↔Week tab switches (switching from Day to Week remembers `layoutMode`), resets to `"lane"` on full page reload. This is unchanged from B1's `store.ts` behavior.

---

## Surface 3 — `DispatchBoardPage` Week Routing (Modify)

### B1 Week Render (existing — to be replaced)

```ts
// B1 existing — week always shows DispatchWeekView (tech mode)
{viewTab === "week" && <DispatchWeekView ... />}
```

### B1.5 Week Render (new)

```ts
// B1.5 — week renders based on layoutMode
{viewTab === "week" && layoutMode === "lane" && (
  <DispatchWeekLaneView
    weekStartDate={activeDate}
    daysToShow={daysToShow}
    laneCount={laneCount}
    jobs={jobs}
    onJobDrop={handleWeekLaneDrop}    // → unified beginMove pipeline
    onJobClick={handleJobClick}
    onJobContextMenu={handleJobContextMenu}
    onNavigateToDate={handleNavigateToDate}
    onViewTabChange={handleViewTabChange}
  />
)}
{viewTab === "week" && layoutMode === "tech" && (
  <DispatchWeekView
    weekStartDate={activeDate}
    daysToShow={daysToShow}
    techs={techs}
    jobs={jobs}
    onJobDrop={handleWeekTechDrop}    // existing — wires to beginMove pipeline
    onJobClick={handleJobClick}
    onNavigateToDate={handleNavigateToDate}
    onViewTabChange={handleViewTabChange}
  />
)}
```

### `handleWeekLaneDrop` — Week-Lane Drop Handler

```ts
// In DispatchBoardPage — new handler for week-lane drops
async function handleWeekLaneDrop(
  jobId: string,
  laneIndex: number,
  dateStr: string,
  newStartTime: Date,
): Promise<void> {
  // Lane-mode drops: tech_user_id is null (unassigned to a specific tech).
  // The move pipeline assigns the job to the lane slot server-side
  // using the same scheduling.py /move endpoint — tech_user_id = null is valid
  // for lane-only moves (job remains assigned to its existing tech or unassigned).
  await beginMove(jobId, null, newStartTime, computedEndTime);
}
```

> **Implementation note for React Engineer**: When `tech_user_id` is `null` in the `/move` request, the backend rescheduling service reschedules the job's time without changing its tech assignment. The lane index itself is client-side computed — it is NOT stored server-side. The move updates `scheduled_start_at` and `scheduled_end_at` only. This is consistent with the architecture doc: "There is no `lane_number` column (confirmed absent) — lanes remain client-computed via the existing `assignJobsToLanes` earliest-free-slot algorithm."

---

## Reuse Inventory (No Redesign — All From B1)

The following components are fully built in DISPATCH-B1 and are consumed unchanged by B1.5. This section confirms their reuse contract.

### `UnassignedTray` — Drag-Out to Week-Lane Cells

The shared `UnassignedTray` renders above the board in all view modes (Day and Week). In week-lane mode, chips from the tray can be dragged onto any `WeekLaneCell` drop target.

**Drop flow from tray onto week-lane cell**:
1. User drags chip from `UnassignedTray`
2. Drops onto `WeekLaneCell` with `id: "cell-lane{laneIndex}-{dateStr}"`
3. `DispatchBoardPage.handleDragEnd` reads `over.data.current: { laneIndex, dateStr }`
4. Calls `handleWeekLaneDrop(jobId, laneIndex, dateStr, defaultStartTime)`
5. `beginMove` pipeline fires (check-conflicts → `ConflictPreviewPane` → confirm → move)

The `UnassignedTray` UI, props, and `data-testid="unassigned-tray"` are unchanged from B1.

### Move Pipeline — Unified `beginMove`

The `check-conflicts → ConflictPreviewPane → confirm → move` pipeline built in B1 is reused unchanged for week-lane drops. `DispatchWeekLaneView` fires `onJobDrop` → `DispatchBoardPage.handleWeekLaneDrop` → `beginMove`. No changes to `useMoveJob`, `useCheckConflicts`, or `ConflictPreviewPane`.

### `JobContextMenu` — Right-Click on Week-Lane Cards

`DispatchWeekLaneView` passes `onJobContextMenu` down to each `WeekLaneJobCard`. The shared `JobContextMenu` component (built in B1) is rendered once at `DispatchBoardPage` level. B1.5 extends its consumer list from `[DispatchBoardLanes, DispatchGridDayView]` to `[DispatchBoardLanes, DispatchGridDayView, DispatchWeekLaneView]`. No changes to `JobContextMenu` itself.

Note: `DispatchWeekView` (week-tech) retains its own inline `ContextMenu` sub-component (as-is, not refactored) per the "untouched" constraint on that file.

### `JobPropertiesPanel` — Left-Click on Week-Lane Cards

Left-clicking a `WeekLaneJobCard` calls `onJobClick(job)` → `DispatchBoardPage.handleJobClick` → `setSelectedJob(job)`. This triggers `JobPropertiesPanel` in the right rail via the existing B1 arbitration logic. No changes.

### Right-Rail Arbitration

The `ConflictPreviewPane` / `JobPropertiesPanel` mutual exclusion rule from `dispatch-b1-ui-design-spec.md §Surface 4` applies unchanged in week-lane mode. The B1.5 implementation does not touch this logic.

---

## Icon Inventory (B1.5 Additions)

No new icons introduced by B1.5. The `DispatchWeekLaneView` uses:

| Use | Heroicons Name | Variant | Size | Notes |
|---|---|---|---|---|
| Mobile fallback — no new icon | — | — | — | Text-only fallback, same as `DispatchWeekView` |
| Over-capacity chip | — | — | — | Text-only chip, no icon (matches `DispatchWeekView` pattern) |
| `EmptyState` (no lanes) | Managed by `<EmptyState>` from `@pilot/ui` | — | — | Shared component handles its own icon |

All icons on shared components (`JobContextMenu`, `ConflictPreviewPane`, `UnassignedTray`) are unchanged from B1.

---

## Implementation Notes

1. **No internal `DndContext`**: `DispatchWeekLaneView` must NOT wrap its own `DndContext`. B1 lifted `DndContext` to `DispatchBoardPage`. `DispatchWeekLaneView` registers `useDroppable` + `useDraggable` nodes inside the page-level context, exactly like `DispatchBoardLanes` after B1.

2. **No commitment chips**: `WeekCommitmentChip` is a `DispatchWeekView`-only sub-component and must NOT be imported or used in `DispatchWeekLaneView`. Lane mode shows primary job cards only. Add a code comment confirming this explicitly: `// DISPATCH-B1.5: Lane mode — no WeekCommitmentChip. Commitment chips are tech-mode only (DISPATCH-B1.25).`

3. **`assignJobsToLanes` import**: Extract (or confirm already extracted by B1) `assignJobsToLanes` into a shared utility at `features/dispatch-board/utils/laneHelpers.ts` (or `timeHelpers.ts` if B1 placed it there). `DispatchWeekLaneView` must import it from the shared file — do NOT copy the function inline.

4. **`checkLaneAvailability` — NOT needed in week-lane view**: The week-lane grid uses the simpler `jobs.length >= CAPACITY_LIMIT` check per cell (same as `DispatchWeekView`'s `isOverCapacity` logic at `DispatchWeekView.tsx`). `checkLaneAvailability` (the full time-overlap variant) is not needed here because the drop target is a full-day cell, not a time-axis slot.

5. **`isActiveDragOver` state**: `DispatchWeekLaneView` tracks `activeDragJob: DispatchBoardJob | null` in local state (same as `DispatchWeekView`) and passes it down to each `WeekLaneCell` as `isActiveDragOver`. Cells only show drop-target styling when `isActiveDragOver !== null`.

6. **`tech_user_id: null` in `/move` request for lane drops**: When a job is moved via a lane-mode drop, the `tech_user_id` sent to the `/move` endpoint should be the job's **existing** `primary_assignment_id`'s tech (from `job.primary_assignment_id`), NOT `null`. The lane move reschedules the job's time but preserves the existing tech assignment. If the job is unassigned (`primary_assignment_id === null`), `tech_user_id` is omitted from the request body (the server treats it as a time-only reschedule). The React Engineer must confirm this behavior matches the `/move` endpoint contract in `scheduling.py`.

7. **`daysToShow` prop source**: `DispatchWeekLaneView.daysToShow` receives the same `daysToShow: 5 | 7` value from `DispatchBoardPage` as `DispatchWeekView` does. The 5-day/7-day toggle in `DispatchToolbar` controls this value; it is already in `DispatchBoardPage` state and requires no new wiring.

8. **`laneCount` source**: From `useScheduleLaneCount()` hook already present in `DispatchBoardPage`. Founders tier cap is 5. Pass as `laneCount` prop.

9. **`CAPACITY_LIMIT = 4` rationale**: Matches the week-tech view's capacity limit for visual consistency. In lane mode this is a UI guard — the actual scheduling constraint is the time-overlap check done by the backend `/check-conflicts` endpoint via the `beginMove` pipeline.

10. **`WeekLaneJobCard` is NOT the same component as `DraggableJobBlock`**: `DraggableJobBlock` is the day-board time-axis block (absolutely positioned, width proportional to duration). `WeekLaneJobCard` is a vertically-stacked card in a `flex-col` cell, identical in visual style to `WeekJobCard` in `DispatchWeekView`. These are different layout modes and different sub-components — do not conflate them.

11. **`DispatchWeekView` is untouched**: The week-tech view file (`DispatchWeekView.tsx`) must NOT be modified by B1.5. It retains its own inline `ContextMenu`, its own `DndContext`, and its `WeekCommitmentChip`. The only `DispatchWeekView`-related change in B1.5 is how `DispatchBoardPage` conditionally renders it (`layoutMode === "tech"` gate added).

12. **Accessibility**: Each `WeekLaneCell` root `<div>` should have `role="gridcell"` and `aria-label="Lane {laneIndex + 1}, {dayLabel}"` (e.g. `"Lane 1, Monday Jul 28"`). The table `<thead>` lane headers should have `scope="col"` and `aria-label="Lane {n}"`. Day row `<th>` already has `scope="row"` (matches `DispatchWeekView`).

---

## Component Manifest

| File | Action | Description |
|---|---|---|
| `apps/web/src/features/dispatch-board/components/DispatchWeekLaneView.tsx` | **New** | Week-lane grid — days-as-rows × lane-columns; `useDroppable` cells; `WeekLaneJobCard` sub-component; per-day `assignJobsToLanes` for cell population; mobile fallback |
| `apps/web/src/features/dispatch-board/components/DispatchToolbar.tsx` | **Modify** | Extend `Lane\|Tech` `PillToggle` condition from `viewTab === "day"` to `viewTab === "day" \|\| viewTab === "week"` — one-line condition change |
| `apps/web/src/features/dispatch-board/components/DispatchBoardPage.tsx` | **Modify** | Add `layoutMode === "lane"` / `layoutMode === "tech"` conditional branches to week routing; import `DispatchWeekLaneView`; add `handleWeekLaneDrop` handler |
| `apps/web/src/features/dispatch-board/utils/laneHelpers.ts` | **New (or confirm B1 created)** | Shared `assignJobsToLanes` export for both `DispatchBoardLanes` and `DispatchWeekLaneView`; `checkLaneAvailability` (for `DispatchBoardLanes` use only — not consumed by week-lane view) |

**Unchanged by B1.5** (confirmed — do not modify):
- `apps/web/src/features/dispatch-board/components/DispatchWeekView.tsx` — week-tech view untouched
- `apps/web/src/features/dispatch-board/components/UnassignedTray.tsx` — reused as-is
- `apps/web/src/features/dispatch-board/components/JobContextMenu.tsx` — reused as-is
- `apps/web/src/features/dispatch-board/components/JobBlock.tsx` — reused as-is (day boards only; week-lane uses `WeekLaneJobCard` inline sub-component)
- `apps/web/src/features/dispatch-board/components/ConflictPreviewPane.tsx` — reused as-is
- `apps/web/src/features/dispatch-board/store.ts` — `layoutMode` field already added by B1; no new store fields for B1.5
- `apps/web/src/features/dispatch-board/hooks/useMoveJob.ts` — reused as-is
- `apps/web/src/features/dispatch-board/hooks/useCheckConflicts.ts` — reused as-is

---

## Tests (Targeted — for React Engineer)

- **`DispatchWeekLaneView` renders `laneCount` columns**: with `laneCount=5`, 5 `<th>` lane headers (`L1`…`L5`) render.
- **Per-day `assignJobsToLanes` populates cells correctly**: 2 non-overlapping jobs on Monday → both appear in the same lane column (L1); 2 overlapping jobs → split across L1 and L2.
- **Empty cell renders**: with no jobs, cell shows dashed border + `bg-neutral-50/50`.
- **Over-capacity blocks drop**: 4 jobs in a cell → dragging a 5th → "Capacity exceeded" chip appears; `onJobDrop` NOT called.
- **Under-capacity allows drop**: 3 jobs in cell → drop → `onJobDrop(jobId, laneIndex, dateStr, newStartTime)` called once.
- **No `WeekCommitmentChip` in lane mode**: `DispatchWeekLaneView` renders 0 elements with `role="button"` having a class `border-dashed` (commitment chip indicator) — lane mode has no commitment chips.
- **`Lane|Tech` toggle in week view**: with `viewTab === "week"`, `layoutMode === "lane"` → `DispatchWeekLaneView` renders; clicking "Tech" → `DispatchWeekView` renders.
- **5d/7d toggle retained in week-lane mode**: switching to 7d → `daysToShow=7` → 7 day rows render in `DispatchWeekLaneView`.
- **Mobile fallback**: at viewport < `md` → `"Week view is available on desktop."` text visible; grid table hidden.
- **MSW**: no new handlers required (B1's `/scheduling/jobs/:id/move` + `/check-conflicts` handlers cover week-lane drops).

---

## Handoff Gate

This spec is ready for Tom's review. Implementation starts only after approval.

---

*Spec authored by Pilot Web UI Designer, 2026-07-26. Source reads: `batch-dispatch-b1-design.md §Split + §Geometry correction 2026-07-26`, `dispatch-b1-ui-design-spec.md §All surfaces`, `DispatchWeekView.tsx (full)`, `DispatchBoardLanes.tsx (full)`. Week-tech view (`DispatchWeekView`) is explicitly out of scope — untouched. Backend is out of scope — B1 + B1.25 `DispatchBoardJobEntry` already delivers all required fields.*
