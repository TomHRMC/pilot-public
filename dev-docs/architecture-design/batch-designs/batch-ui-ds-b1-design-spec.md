# Design Spec: Batch UI-DS-B1
# Invoice Builder, Dispatch Week/Month Views, JobPropertiesPanel Save Button

**Batch**: UI-DS-B1  
**Designer**: Pilot Marketing UI Designer  
**Approval date**: 2026-07-11 (all 4 surfaces approved by Tom)  
**Implements**: FE-B27 (JobPropertiesPanel Save), FE-B29 (Invoice Builder), FE-B30 (Dispatch Week/Month Views)  
**Source decisions**: `dev-docs/testing-support/alpha-testing/ui-testing-status-2026-07-10-v2.md`

---

## Design Constraints (Applies to All Surfaces)

- All components use **existing Tailwind design tokens** from `tailwind.preset.ts`. No new color names.
- **Token reference** (confirmed from existing components):
  - Primary brand: `bg-brand-500`, `bg-brand-600`, `text-brand-600`, `hover:bg-brand-700`
  - Neutral: `bg-neutral-50`, `border-neutral-200`, `text-neutral-700`, `text-neutral-400`
  - Amber/warning: `bg-alert-50`, `border-alert-200`, `text-alert-600`, `text-alert-700`
  - Error: `bg-fault-50`, `border-fault-200`, `text-fault-600`, `text-fault-700`
  - Success/margin: `bg-margin-50`, `text-margin-600`
  - Typography scale: `text-caption` (11px), `text-body` (13px), `text-sm` (14px), `text-base` (16px)
- `<JobBlock>` in Week view = exact same component as Day view. No visual redesign.
- Invoice builder page shell mirrors `QuoteCreatePage.tsx` structure.
- No new navigation patterns — extend existing `DispatchToolbar` tab structure.
- WCAG compliant: all interactive elements have `focus-visible:ring-2 focus-visible:ring-brand-600` focus rings.

---

## Surface 1: Full-Page Invoice Builder `/invoices/new`

### Overview

Replaces the placeholder `InvoiceCreateModal`. A full-page builder at route `/invoices/new`, mirroring the shell and UX of `QuoteCreatePage.tsx`.

### Entry Points

| Entry Point | URL | Pre-fill Behavior |
|---|---|---|
| Invoices list "+ Create Invoice" | `/invoices/new` | Blank — no pre-fill |
| Job detail "Convert to Invoice" | `/invoices/new?job_id={id}` | Customer, site, and billable line items pre-populated from job |
| Accepted quote "Create Invoice" (future) | `/invoices/new?quote_id={id}` | From quote — Phase 2.0 |

On save → navigate to `/invoices/{new_id}`.  
On cancel → back navigation (previous page).

---

### Layout Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│ BREADCRUMB + PAGE TITLE ROW                                      │
│ Invoices / New Invoice      [Cancel] [Save as Draft] [Send →]   │
├──────────────────────────────────────────────────────────────────┤
│ SECTION 1: HEADER PANEL (white card)                             │
│ ┌──────────────────────┬──────────────────────┐                  │
│ │ Customer *           │ Site *               │                  │
│ │ [Combobox typeahead] │ [Combobox typeahead] │                  │
│ └──────────────────────┴──────────────────────┘                  │
│ [Linked Job: JOB-20260710-XYZ ×]  ← shows only if ?job_id=      │
├──────────────────────────────────────────────────────────────────┤
│ SECTION 2: BILLING MODE TOGGLE                                   │
│ ┌────────────────────────────────────┐                           │
│ │ [ Select line items ] [ Progress billing (%) ]                 │
│ └────────────────────────────────────┘                           │
├──────────────────────────────────────────────────────────────────┤
│ SECTION 3: LINE ITEMS PANEL (white card)                         │
│  ☑  Labor: Jake — 4h @ $85/hr                           $340.00 │
│  ☑  Materials: Wire 12AWG x 50ft                          $48.00 │
│  ☐  Expense: Permit fee                                   $75.00 │  ← deferred
│  ─────────────────────────────────────────────────────────────   │
│  [+ Add custom line item]                                        │
├──────────────────────────────────────────────────────────────────┤
│ SECTION 4: PAYMENT TERMS PANEL (white card)                      │
│ Terms: [Due on Receipt ▼]     Due: Aug 11, 2026                 │
├──────────────────────────────────────────────────────────────────┤
│ SECTION 5: NOTES PANEL (white card)                              │
│ Customer-facing note (shown on invoice PDF)                      │
│ [                                                    ]           │
│ ─────────────────────────────────────────────────────────────── │
│ Internal memo (not shown on PDF)                                 │
│ [                                                    ]           │
├──────────────────────────────────────────────────────────────────┤
│ ACTION FOOTER                                                    │
│ [Preview Invoice]    [Save as Draft]    [Send Invoice →]         │
└──────────────────────────────────────────────────────────────────┘
```

---

### Component Inventory

| Component | Purpose | Token / Class Guidance |
|---|---|---|
| Page wrapper | Max-width container | `max-w-4xl mx-auto p-6 pb-24` |
| Breadcrumb nav | Wayfinding + page title | `text-sm text-neutral-500 mb-4` — link: `hover:text-brand-600`, current: `text-neutral-900 font-medium` |
| Page H1 | "New Invoice" | `text-2xl font-semibold text-neutral-900 mb-6` |
| Top action row | Cancel / Save Draft / Send Invoice buttons — right-aligned in breadcrumb row | `flex items-center justify-between` — buttons share row with breadcrumb |
| Section cards | Each panel (Header, Billing Mode, Line Items, Payment Terms, Notes) | `bg-white border border-neutral-200 rounded-lg shadow-sm p-6 space-y-4` |
| Section H2 | Panel title label (e.g., "Line Items") | `text-base font-semibold text-neutral-800 mb-3` |
| Customer Combobox | Typeahead search — same pattern as QuoteCreatePage customer search | `w-full border border-neutral-200 rounded-md px-3 py-2 text-sm focus:outline-none focus:border-brand-400` |
| Site Combobox | Cascades from customer selection | Same input classes as Customer Combobox; `disabled:bg-neutral-50 disabled:text-neutral-400` when no customer selected |
| Linked Job badge | Read-only amber pill (only when `?job_id=` present) | `inline-flex items-center gap-1.5 bg-alert-50 border border-alert-200 text-alert-700 text-caption font-medium rounded-full px-2.5 py-1 mt-3` |
| Billing Mode toggle | 2-option pill switcher | Outer: `bg-neutral-100 rounded-md p-1 inline-flex`; Active pill: `bg-white shadow-sm rounded px-3 py-1 text-sm font-medium text-neutral-900`; Inactive: `px-3 py-1 text-sm font-medium text-neutral-500 hover:text-neutral-700` |
| Line item row | Checkbox + description + amount | `flex items-center gap-3 py-2 border-b border-neutral-100` |
| Line item checkbox | Check/uncheck to include on invoice | `w-4 h-4 rounded border-neutral-300 text-brand-600 focus:ring-brand-500` |
| Line item description | Labor/expense label | Checked: `text-sm text-neutral-800 flex-1`; Unchecked: `text-sm text-neutral-400 line-through flex-1` |
| Line item amount | Right-aligned dollar value | Checked: `text-sm font-medium text-neutral-900 ml-auto`; Unchecked: `text-sm text-neutral-400 ml-auto` |
| Add custom line item row | Inline expand row at bottom of list | `flex items-center gap-2 pt-3` — description `input` + amount `input` + `Add` button (`bg-brand-600 text-white text-sm px-3 py-1.5 rounded-md`) |
| Progress billing % input | Large centered % input (replaces checklist in progress mode) | `text-3xl font-semibold text-neutral-900 w-24 text-center border-b-2 border-brand-500 focus:outline-none bg-transparent` |
| Progress billing calculated amount | Dollar equivalent below % input | `text-neutral-500 text-sm mt-1` — e.g., "= $5,000.00" |
| Payment Terms dropdown | Due on Receipt / Net 15 / Net 30 / Custom date | `border border-neutral-200 rounded-md px-3 py-2 text-sm focus:outline-none focus:border-brand-400` |
| Due date label | Calculated display next to dropdown | `text-sm text-neutral-500 ml-3` — e.g., "Due: Aug 11, 2026" |
| Custom date picker | Revealed inline when "Custom date" selected | `mt-2 border border-neutral-200 rounded-md px-3 py-2 text-sm focus:outline-none focus:border-brand-400 w-44` |
| Progress billing split fields | Deposit % + On completion % inputs | `flex items-center gap-2 text-sm text-neutral-700 mt-3` |
| Customer-facing note textarea | Shown on invoice PDF | `w-full rounded border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-900 resize-y min-h-[80px] focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 placeholder:text-neutral-400` |
| Internal memo textarea | NOT on PDF | Same as above with `placeholder="Add internal memo (not visible to customer)…"` |
| Textarea sub-labels | "(shown on invoice PDF)" / "(not shown on PDF)" | `text-xs text-neutral-400 mt-0.5 mb-1` |
| Section divider (Notes) | Separates two note areas | `border-t border-neutral-100 my-4` |
| Preview Invoice button | Opens invoice preview | `px-4 py-2 text-sm font-medium text-neutral-700 border border-neutral-200 rounded-md hover:bg-neutral-50 transition-colors` |
| Save as Draft button | Saves without sending | `px-4 py-2 text-sm font-medium text-brand-700 border border-brand-200 bg-brand-50 rounded-md hover:bg-brand-100 transition-colors disabled:opacity-50` |
| Send Invoice button (primary CTA) | Saves and initiates send | `px-4 py-2 text-sm font-medium text-white bg-brand-600 rounded-md hover:bg-brand-700 transition-colors disabled:opacity-50` |

---

### State Descriptions

#### Page-Level States

| State | Trigger | Visual Treatment |
|---|---|---|
| **Default (no job)** | Navigating to `/invoices/new` | Header panel visible; Line Items panel shows empty state prompt |
| **Job loading** | `?job_id=` present, API fetch in-flight | Line Items panel shows 3-row skeleton loader (`animate-pulse bg-neutral-100 rounded h-8`) |
| **Job loaded** | API fetch complete | Line Items panel shows pre-populated checklist from job billable items |
| **Job fetch error** | API fetch failed | `<ErrorState>` in Line Items panel: `text-fault-700 bg-fault-50 border border-fault-200 rounded px-4 py-3 text-sm` with retry button |
| **Saving** | Save Draft / Send clicked | All action buttons disabled (`disabled:opacity-50`); button text → "Saving…" |
| **Save error** | POST/PATCH fails | `text-sm text-alert-700 bg-alert-50 border border-alert-200 rounded px-3 py-2` error message above action footer |
| **Billing mode: Progress** | Billing toggle → "Progress billing" | Line items checklist replaced by % input + calculated amount; Payment Terms panel gains split fields |

#### Line Items Panel States

| State | Visual |
|---|---|
| **Empty (no job)** | Centered icon + `"Link a job above to pre-fill billable items, or add custom line items manually"` in `text-neutral-500 text-sm text-center py-8` |
| **Loading (job fetching)** | 3 pulse skeleton rows + "+ Add custom line item" row hidden |
| **Populated (job loaded)** | Checklist rows (checked = included, unchecked = deferred/muted) + "+ Add custom line item" at bottom |
| **Custom only (no job)** | Empty state prompt + "+ Add custom line item" inline row immediately below |
| **Error** | `<ErrorState>` replaces list with fault-colored block + "Retry" button |

---

### Interaction Annotations

| Action | Behavior |
|---|---|
| Customer Combobox — type | Filters customer list in real time; dropdown appears below input |
| Customer Combobox — select | Customer selected; Site Combobox enables and fetches sites for that customer |
| Customer Combobox — clear | Site Combobox resets to disabled + empty |
| Site Combobox — select | Site selected; "✓ [site name] selected" confirmation below |
| Linked Job badge [×] | Removes `job_id` param from URL; clears line items panel back to empty state |
| Billing toggle — "Progress billing" | Animates checklist out, animates % input in (`transition-opacity`); Payment Terms gains split row |
| Billing toggle — "Select line items" | Reverses the above |
| Line item checkbox — check | Row opacity 100%, amount dark, included in invoice total |
| Line item checkbox — uncheck | Row muted (`text-neutral-400`), amount muted, NOT included in total |
| "+ Add custom line item" — click | Inline row expands with description input + amount input + "Add" button; after Add → new row appended to list, inline row collapses |
| Payment Terms → "Custom date" | Date picker field appears inline below dropdown (`mt-2`) |
| Preview Invoice | Renders a read-only preview modal or slide-over — Phase 1.5 detail (engineering to decide implementation) |
| Save as Draft | POST `/api/v1/invoices/` → creates invoice → navigates to `/invoices/{id}` |
| Send Invoice | Same save flow → triggers send confirmation step (email delivery) |
| Cancel | Back navigation — `router.back()` |

---

### Responsive Behavior

| Breakpoint | Layout Change |
|---|---|
| `md` and above (≥ 768px) | Customer + Site pickers in 2-col grid (`grid grid-cols-1 md:grid-cols-2 gap-4`) |
| Below `md` (< 768px) | Customer + Site stack vertically (single column) |
| All breakpoints | Each section card stacks vertically; action buttons always right-aligned in the footer row; no horizontal scrolling |

---

## Surface 2: Dispatch Board — Week View

### Overview

A new `DispatchWeekView` component replacing the old `DispatchGrid.tsx` week implementation. Uses a **tech-as-column, day-as-row** CSS grid. The "4-Day" tab is removed from `DispatchToolbar`.

Referenced existing components:
- `DispatchToolbar.tsx` — modified to remove 4-Day, add week navigation controls
- `DispatchBoardLanes.tsx` — `<JobBlock>` and DragOverlay patterns reused
- `JobPropertiesPanel.tsx` — opened on right-click "Job Properties" option

---

### Toolbar Modifications

**Remove**: `{ value: "4day", label: "4 Day" }` from `VIEW_TABS` array in `DispatchToolbar.tsx`.

**New VIEW_TABS**:
```typescript
const VIEW_TABS = [
  { value: "day",   label: "Day"   },
  { value: "week",  label: "Week"  },
  { value: "month", label: "Month" },
];
```

**Week-specific toolbar controls** (rendered when `viewTab === "week"`):

```
[ Day | Week | Month ]   < Prev Week   Week of Jul 14 – Jul 18   Next Week >   [ This Week ]   [ 5-day / 7-day ]
```

| Control | Class Guidance |
|---|---|
| `< Prev Week` chevron button | `p-1.5 rounded-md text-neutral-600 hover:bg-neutral-100 focus-visible:ring-2 focus-visible:ring-brand-600` |
| `Week of [Mon] – [Fri]` label | `text-body font-medium text-neutral-900 min-w-48 text-center` |
| `Next Week >` chevron button | Same as Prev Week |
| `[ This Week ]` button | `px-3 py-1 rounded-md text-body font-medium text-neutral-600 border border-neutral-200 hover:bg-neutral-50 focus-visible:ring-2 focus-visible:ring-brand-600` |
| `5-day / 7-day` pill toggle | Outer: `bg-neutral-100 rounded-md p-0.5 inline-flex ml-2`; Active: `bg-white shadow-sm rounded px-2.5 py-1 text-caption font-medium text-neutral-900`; Inactive: `px-2.5 py-1 text-caption font-medium text-neutral-500` |

---

### Grid Layout

```
┌──────────────┬──────────────────┬──────────────────┬──────────────────┐
│              │  Jake R.         │  Maria S.        │  Dev Tech        │
│ Row header   │  [JR initials]   │  [MS initials]   │  [DT initials]   │
│  (sticky)    │  avatar          │  avatar          │  avatar          │
├──────────────┼──────────────────┼──────────────────┼──────────────────┤
│ Mon Jul 14   │  8:00 AM         │                  │  9:30 AM         │
│              │  [JobBlock]      │  (empty cell)    │  [JobBlock]      │
│              │  10:00 AM        │                  │                  │
│              │  [JobBlock]      │                  │                  │
├──────────────┼──────────────────┼──────────────────┼──────────────────┤
│ Tue Jul 15   │                  │  8:00 AM         │  8:00 AM         │
│              │  (empty cell)    │  [JobBlock]      │  [JobBlock]      │
│              │                  │  10:00 AM        │  11:00 AM        │
│              │                  │  [JobBlock]      │  [JobBlock]      │ ← capacity exceeded
├──────────────┼──────────────────┼──────────────────┼──────────────────┤
│ Wed Jul 16   │  8:00 AM         │                  │                  │
│              │  [JobBlock]      │  (empty cell)    │  (empty cell)    │
├──────────────┼──────────────────┼──────────────────┼──────────────────┤
│ Thu Jul 17   │                  │  9:00 AM         │                  │
│              │  (empty cell)    │  [JobBlock]      │  (empty cell)    │
├──────────────┼──────────────────┼──────────────────┼──────────────────┤
│ Fri Jul 18   │  8:00 AM         │  8:00 AM         │                  │
│              │  [JobBlock]      │  [JobBlock]      │  (empty cell)    │
└──────────────┴──────────────────┴──────────────────┴──────────────────┘
```

---

### Component Inventory

| Component | Purpose | Token / Class Guidance |
|---|---|---|
| Week grid wrapper | Outer scroll container | `overflow-x-auto` — board scrolls horizontally when too narrow |
| Grid table | CSS grid or `<table>` with fixed columns | `border-collapse border-neutral-200` |
| Tech column header | Technician name + initials avatar | Reuse existing `<TechColumnHeader>` component from Day view; `min-w-[160px]` |
| Tech avatar (initials) | Initials circle in column header | `w-8 h-8 rounded-full bg-brand-100 flex items-center justify-center text-brand-700 font-semibold text-sm` |
| Row header | Day name + date, sticky left | `sticky left-0 z-10 bg-white min-w-[96px] px-3 py-2 border-r border-neutral-200 text-body font-semibold text-neutral-700 whitespace-nowrap` |
| Day cell | Each tech × day intersection | `min-h-[72px] p-2 border border-neutral-100 align-top relative`; grows to fit content (no `max-height`) |
| Empty cell | No jobs assigned | `border border-dashed border-neutral-200 rounded bg-neutral-50/50` |
| Start time label | Time displayed above JobBlock | `text-caption text-neutral-500 font-medium mb-0.5` — e.g., "8:00 AM" |
| JobBlock | Reused Day view job card | **No visual changes** — exact same `<JobBlock>` component. Context menu added via `onContextMenu` handler. |
| Capacity exceeded cell | Tech × day cell over lane limit | Cell bg: `bg-fault-50/40 border-fault-200`; Chip: `absolute top-1 right-1 bg-fault-100 text-fault-700 text-caption rounded-full px-2 py-0.5 font-medium` — e.g., "Capacity exceeded" |
| Context menu | Right-click popup on job card | `bg-white border border-neutral-200 shadow-lg rounded-md py-1 z-50` — fixed position at cursor; items: `text-sm text-neutral-700 px-3 py-1.5 hover:bg-brand-50 cursor-pointer` |
| DragOverlay ghost | Dragged job card phantom | `border border-brand-400 rounded px-3 py-2 bg-white shadow-lg text-caption font-medium text-brand-700 opacity-90 pointer-events-none` |
| Empty week state | No jobs in entire week | Centered: `text-neutral-500 text-sm` + "No jobs scheduled this week" + `<button className="mt-3 px-4 py-2 bg-brand-600 text-white text-sm font-medium rounded-md hover:bg-brand-700">+ Create Job</button>` |
| Mobile fallback | < 768px week view | `text-sm text-neutral-600 text-center py-12` + "Week view is available on desktop" + `<button className="mt-3 px-4 py-2 border border-brand-200 bg-brand-50 text-brand-700 text-sm font-medium rounded-md hover:bg-brand-100">View Today</button>` (fires `onViewTabChange("day")` + reset date to today) |

---

### Column / Row / Cell Specification

**Column constraints**:
- Minimum column width: `min-w-[160px]` per tech column — does NOT compress below this
- Row header column: `min-w-[96px]` sticky
- When browser window is narrower than the combined grid: `overflow-x: auto` on the board wrapper — horizontal scroll

**Row height**:
- Variable height — each day row grows to the height of its tallest cell (the tech with the most jobs that day)
- Achieved via CSS: cells use `height: auto` — the row wraps content
- **No truncation** — every job must be visible without scrolling. Functional over aesthetic.

**Cell job ordering**:
- Jobs within a cell stack vertically, ordered by `scheduled_start_at` ascending (earliest first, top to bottom)

---

### Drag-and-Drop Visual States

| State | Visual |
|---|---|
| **Idle** | Normal cell appearance |
| **Job being dragged (source cell)** | Source `<JobBlock>`: `opacity-30` (same as Day view DraggableJobBlock isDragging treatment) |
| **DragOverlay active** | Ghost card follows cursor: `border border-brand-400 rounded px-3 py-2 bg-white shadow-lg text-caption font-medium text-brand-700 opacity-90 pointer-events-none` |
| **Hovering valid drop target** | Cell bg: `bg-brand-50/40` (`transition-colors`) |
| **Hovering over-capacity cell** | Cell bg: `bg-fault-50/40`; cursor: `cursor-not-allowed` |
| **Drop success** | Cell updates with new job card; `onJobDrop(jobId, newTechId, newDate)` fires |
| **Drop on invalid target** | Job returns to origin; no API call |

**Drop payload**: `{ jobId: string, techId: string, scheduledDate: Date }` — fires PATCH to update `scheduled_date` and `tech_id` on the job.

---

### Job Right-Click Context Menu

Applies to **both Week view** and **Month view** `<JobBlock>` / job chip components.

**Trigger**: `onContextMenu` event on the job card element.

**Menu items**:
1. `View Job` → navigates to `/jobs/{id}`
2. `Job Properties` → opens `<JobPropertiesPanel>` for that job (same panel as Day view; panel opens as right-side slide-in)

**Menu behavior**:
- Menu appears at cursor position (`position: fixed; top: {y}px; left: {x}px`)
- Closes on: click outside, `Escape` key, any menu item click
- `z-index: 50` (above all board content)

**Accessibility**: Menu items are `role="menuitem"` inside `role="menu"`. Focus moves to first item on open. `Escape` closes and returns focus to the job card.

---

### Empty State

When no jobs exist in the selected week:

```
(grid renders with all empty cells)
          "No jobs scheduled this week"
                 [+ Create Job]
```

Centered in the grid body: `flex flex-col items-center justify-center py-16 text-neutral-500 text-sm`.

---

### Mobile Fallback (< 768px)

```
┌─────────────────────────────────────────┐
│        Week view is available           │
│             on desktop.                 │
│                                         │
│          [ View Today ]                 │
└─────────────────────────────────────────┘
```

`"View Today"` fires `onViewTabChange("day")` + resets active date to today's date.

---

## Surface 3: Dispatch Board — Month View

### Overview

A redesigned `MonthCalendarGrid.tsx` — consistent with Day/Week views in visual style, navigation pattern, and design token usage. Read-only — no drag-and-drop.

Referenced existing: `MonthCalendarGrid.tsx` and `MonthViewCell.tsx`.

---

### Toolbar Modifications (Month View Controls)

When `viewTab === "month"`, replace the date navigation row with:

```
[ Day | Week | Month ]   < Prev Month   July 2026   Next Month >   [ Today ]   [ Customer | Tech ]
```

| Control | Purpose | Class Guidance |
|---|---|---|
| `< Prev Month` / `Next Month >` chevron | Navigate months | Same chevron button style as day/week nav |
| `[Month Year]` label | e.g., "July 2026" | `text-body font-medium text-neutral-900 min-w-32 text-center` |
| `[ Today ]` button | Jump to current month | Same "Today" button style as Day view |
| `[ Customer \| Tech ]` chip display toggle | Toggles job chip label in cells | `bg-neutral-100 rounded-md p-0.5 inline-flex ml-4`; Active pill: `bg-white shadow-sm rounded px-2.5 py-1 text-caption font-medium text-neutral-900`; Inactive: `px-2.5 py-1 text-caption font-medium text-neutral-500` |

**Chip display toggle** state: stored in component state (`useState<"customer" | "tech">("customer")`). Default: "Customer".

---

### Grid Layout

```
┌──────┬──────┬──────┬──────┬──────┬──────┬──────┐
│ Sun  │ Mon  │ Tue  │ Wed  │ Thu  │ Fri  │ Sat  │  ← Column headers
├──────┼──────┼──────┼──────┼──────┼──────┼──────┤
│  28  │  29  │  30  │   1  │   2  │   3  │   4  │  ← Prev/next month days (muted)
│      │      │      │● 4j  │      │ 1j   │      │
│      │      │      │[chip]│      │[chip]│      │
│      │      │      │[chip]│      │      │      │
│      │      │      │+2 → │      │      │      │
├──────┼──────┼──────┼──────┼──────┼──────┼──────┤
│  5   │  6   │  7   │  8   │  9   │  10  │  11  │
│      │      │      │[TODAY]      │      │      │
│      │      │      │● 2j  │      │      │      │
│      │      │      │[chip]│      │      │      │
│      │      │      │[chip]│      │      │      │
└──────┴──────┴──────┴──────┴──────┴──────┴──────┘
(6 rows × 7 columns total)
```

---

### Component Inventory

| Component | Purpose | Token / Class Guidance |
|---|---|---|
| Calendar grid wrapper | Outer grid container | `w-full border-collapse` table or CSS grid |
| Column headers (day names) | Sun, Mon, Tue, Wed, Thu, Fri, Sat | `text-caption font-semibold text-neutral-500 uppercase tracking-wide py-2 text-center border-b border-neutral-200` |
| Day cell | Each calendar day | `min-h-[100px] p-2 align-top border border-neutral-100 cursor-pointer hover:bg-brand-50/30 transition-colors` |
| Adjacent month cell | Days from prev/next month | Same as day cell + `bg-neutral-50/50`; day number: `text-neutral-300` |
| Today cell | Current calendar date | `bg-brand-50 ring-2 ring-brand-200 ring-inset` applied to cell `className` |
| Day number | Top-left of each cell | Normal: `text-sm font-semibold text-neutral-700`; Today: `text-sm font-bold text-brand-600` |
| Job count pill | "N jobs" badge | `inline-flex items-center bg-brand-50 text-brand-600 text-caption font-medium rounded-full px-2 py-0.5 mb-1` — shows only when jobs > 0 |
| Job chip (customer mode) | Truncated customer name | `flex items-center gap-1 text-caption text-neutral-700 truncate cursor-pointer hover:text-brand-600` — e.g., "Smith Home" |
| Job chip (tech mode) | Tech initials + truncated job title | `flex items-center gap-1 text-caption text-neutral-700 truncate cursor-pointer hover:text-brand-600` — `[JR]` initials avatar + job title |
| Tech initials mini-avatar | Initials in chip (tech mode) | `w-4 h-4 rounded-full bg-brand-100 text-brand-700 text-[10px] font-bold flex items-center justify-center flex-shrink-0` |
| "+N more" link | Overflow indicator | `text-caption text-brand-600 hover:underline cursor-pointer mt-0.5` — click navigates to Day view for that date |
| Context menu | Right-click on job chip | Same spec as Week view context menu (see Surface 2) |

---

### Day Cell Anatomy

```
┌─────────────────────────┐
│ 14                      │  ← Day number (top-left)
│                         │
│ ● 4 jobs                │  ← Job count pill (brand-50 bg)
│                         │
│ [JR] Panel Upgrade      │  ← Chip 1 (tech mode: initials + title)
│      Smith Home         │  ← Chip 1 (customer mode: customer name)
│                         │
│ [MS] Service Call       │  ← Chip 2 (max 2 chips shown)
│                         │
│ +2 more →               │  ← Overflow link (if > 2 jobs)
└─────────────────────────┘
```

**Chip display rule**: Show maximum **2** job chips per cell. If a cell has 3+ jobs, show 2 chips + "+N more" link. N = remaining job count.

---

### Interaction States

| Action | Behavior |
|---|---|
| **Hover day cell** | `hover:bg-brand-50/30 transition-colors` — subtle brand tint |
| **Left-click day cell** (not a chip) | Navigate to **Day view** for that date: `onViewTabChange("day")` + `onNavigateToDate(date)` |
| **Left-click job chip** | Navigate to `/jobs/{id}` (job detail page) |
| **Right-click job chip** | Show context menu: `View Job` → `/jobs/{id}` OR `Job Properties` → opens `<JobPropertiesPanel>` |
| **Click "+N more" link** | Navigate to Day view for that date |
| **No drag-and-drop** | Month view is fully read-only — no `useDraggable` / `useDroppable` in this component |

---

### Today Highlight

| Property | Value |
|---|---|
| Cell background | `bg-brand-50` |
| Cell ring | `ring-2 ring-brand-200 ring-inset` |
| Day number | `text-brand-600 font-bold text-sm` |
| Job count pill | Same brand pill style as other cells |

---

### Empty Month State

No special state needed — cells simply render with no job chips and no count pill. An empty month looks like a clean calendar grid.

---

## Surface 4: JobPropertiesPanel — Explicit Save Button

### Overview

Modifies `JobPropertiesPanel.tsx` to replace auto-save-on-blur with an explicit Save button pattern. All PATCH calls are eliminated from `ScheduleSection`, `NotesSection`, and any field `onBlur` handler. The single PATCH fires only when the user clicks "Save Changes".

**Approved decision reference**: `ui-testing-status-2026-07-10-v2.md` §"Auto-Save Pattern — TD-1"

---

### Dirty State Management

**`isDirty` flag** — A `boolean` state tracked at the `JobPropertiesPanel` level.

```typescript
// Conceptual — exact implementation for React Engineer
const [isDirty, setIsDirty] = useState(false);
const [editedFields, setEditedFields] = useState<Partial<ScheduledJob>>({});
```

**Set to `true`** when: any field value in the panel differs from the original `job` prop value.  
**Set to `false`** when: Save succeeds OR Cancel is clicked.

**Original values reference**: The initial `job` prop values are stored in a `useRef` or `useState` snapshot on panel open — this is what Cancel reverts to and what `isDirty` compares against.

---

### Dirty State Indicator

When `isDirty === true`:

**Panel header visual change** — The header bar shifts from `bg-neutral-50` to `bg-alert-50`:

```
┌─────────────────────────────────────────────────────┐
│  [bg-alert-50 header bar]                           │
│  Main Panel Upgrade         ● Unsaved changes   [×] │
│  [Scheduled badge]                                  │
└─────────────────────────────────────────────────────┘
```

**"● Unsaved changes" indicator**:
- Placement: Below the job title and status pill, inline in the header section
- Classes: `flex items-center gap-1 text-caption font-medium text-alert-600 mt-1`
- Dot: `inline-block w-2 h-2 rounded-full bg-alert-500`
- Text: `"Unsaved changes"`
- Visible only when `isDirty === true`

---

### Panel Structure (Updated Section Map)

```
┌────────────────────────────────────────────┐
│ HEADER (Section 1)                         │
│ Job title + Status pill                    │  ← bg-alert-50 when dirty
│ ● Unsaved changes                          │  ← visible only when isDirty
│                                    [Close] │
├────────────────────────────────────────────┤
│ SCROLLABLE BODY (Sections 2–6)             │
│ § Customer & Site (read-only)              │
│ § Schedule (datetime inputs — no onBlur)   │
│ § Assigned Technicians                     │
│ § Status                                   │
│ § Internal Notes (textarea — no onBlur)    │
├────────────────────────────────────────────┤
│ SAVE/CANCEL ROW (new — shows only if dirty)│
│ [  Cancel  ]  [  Save Changes  ]           │
│ "Save failed — please try again" ← error  │
├────────────────────────────────────────────┤
│ ACTIONS FOOTER (Section 7 — always visible)│
│ [ View Full Job ]                          │
│ [ Create Invoice ]                         │
└────────────────────────────────────────────┘
```

---

### Component Inventory

| Component | Purpose | Token / Class Guidance |
|---|---|---|
| Panel header (dirty) | Amber-tinted header bar | `bg-alert-50` replaces `bg-neutral-50`; `transition-colors duration-150` |
| Panel header (clean) | Normal header bar | `bg-neutral-50 border-b border-neutral-200` |
| Unsaved changes indicator | Amber dot + text | `flex items-center gap-1 text-caption font-medium text-alert-600 mt-1`; dot: `inline-block w-2 h-2 rounded-full bg-alert-500` |
| Save/Cancel row | Button pair — only visible when `isDirty` | `border-t border-neutral-200 px-4 py-3 flex items-center justify-end gap-2 bg-white` — `display: none` when `!isDirty` |
| Cancel button | Discard changes | `px-3 py-1.5 text-caption font-medium text-neutral-700 border border-neutral-300 rounded-md hover:bg-neutral-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 transition-colors` |
| Save Changes button | Fires PATCH | `px-3 py-1.5 text-caption font-semibold text-white bg-brand-500 rounded-md hover:bg-brand-600 disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 transition-colors` |
| Save loading state | PATCH in-flight | Save button: `disabled` + text → spinner + "Saving…" — `animate-spin` spinner SVG inline |
| Save error message | PATCH failed | `text-caption text-fault-600 mt-1 text-right` below button pair — "Save failed — please try again" — does NOT auto-dismiss |
| Save success flash | Post-PATCH confirmation | `text-caption text-margin-600 font-medium` appears for 1.5s at position where Save button was, then fades with `transition-opacity duration-500` — "Saved ✓" |
| "Changes discarded" flash | Post-cancel confirmation | Optional — `text-caption text-neutral-500` flash 1s at position where Cancel button was |

---

### Field Behavior Changes

All fields in the panel must have their `onBlur` API call handlers **removed**:

| Section | Current Behavior | New Behavior |
|---|---|---|
| `ScheduleSection` — Start datetime input | `onBlur` fires `mutation.mutate(...)` | `onBlur` removed; field updates `editedFields.scheduled_start_at` in local state only; `setIsDirty(true)` |
| `ScheduleSection` — End datetime input | `onBlur` fires `mutation.mutate(...)` | Same — updates local state only |
| `NotesSection` — Internal notes textarea | `onBlur` fires `mutation.mutate(...)` | Same — updates local state only |
| `StatusSection` — Status pill buttons | `onClick` fires `mutation.mutate(...)` immediately | `onClick` updates `editedFields.status` in local state only; `setIsDirty(true)` — visual active ring still updates immediately |

**Important**: Status pill visual selection (which pill has `ring-2 ring-brand-400`) should update immediately on click (optimistic UI for the selection indicator), but the actual API call is deferred until Save.

---

### State Descriptions

#### Save Success State

1. PATCH resolves successfully
2. `isDirty` → `false`
3. Header returns to `bg-neutral-50`
4. "● Unsaved changes" indicator hides
5. Save/Cancel button row hides
6. "Saved ✓" flash appears for 1.5 seconds in the button area, then fades out
7. `onJobUpdated(updatedJob)` fires to update parent state

#### Save Error State

1. PATCH rejects
2. Buttons remain visible
3. Error message appears below button pair: `"Save failed — please try again"` in `text-caption text-fault-600`
4. Save button returns to enabled state (not disabled)
5. Error does NOT auto-dismiss — user must retry (Save) or discard (Cancel)
6. Header remains `bg-alert-50` (still dirty)

#### Cancel State

1. All `editedFields` cleared
2. All form field values reverted to original `job` prop values
3. `isDirty` → `false`
4. Header returns to `bg-neutral-50`
5. Save/Cancel row hides
6. Optional: `"Changes discarded"` flash (1s, then fade) in `text-caption text-neutral-500`

#### Panel Opened (Initial State)

1. `isDirty` = `false`
2. No dirty indicator shown
3. No Save/Cancel buttons shown
4. Header: `bg-neutral-50` (clean)
5. Fields populated from `job` prop values

---

### PATCH Payload

When "Save Changes" is clicked, fire a single PATCH with **only the changed fields** (delta patch):

```
PATCH /api/v1/jobs/{job.id}
Body: {
  scheduled_start_at?: string | null,
  scheduled_end_at?: string | null,
  status?: string,
  internal_notes?: string
}
```

Only fields that differ from the original `job` prop are included in the payload. Unchanged fields are omitted.

---

## Completion Notes

- **FE-B27** implements Surface 4 (JobPropertiesPanel Save button)
- **FE-B29** implements Surface 1 (Invoice Builder `/invoices/new`)
- **FE-B30** implements Surface 2 + 3 (Dispatch Week + Month views)
- The context menu (right-click on job chips) applies to both Week view (Surface 2) and Month view (Surface 3) — spec'd in Surface 2 and cross-referenced in Surface 3
- React Engineers must NOT make visual or UX decisions outside this spec — all deviations require a spec update

---

*Design spec authored: 2026-07-11 | All 4 surfaces approved by Tom | Batch UI-DS-B1*
