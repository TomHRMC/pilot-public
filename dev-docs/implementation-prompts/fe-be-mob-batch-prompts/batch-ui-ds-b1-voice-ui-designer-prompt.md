# Implementation Prompt: UI-DS-B1 — Invoice Builder, Dispatch Week/Month Views, JobPropertiesPanel Save Button

**Mode**: Pilot Voice UI Designer  
**Batch**: UI-DS-B1  
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §Phase 1 — Batch #2  
**Design decisions source**: `dev-docs/testing-support/alpha-testing/ui-testing-status-2026-07-10-v2.md`  
**Estimated session**: 3–4 hours  
**Platform**: Web app (`frontend/apps/web/`) — Tailwind CSS + design token system  
**React Engineer companion**: FE-B29 (invoice builder), FE-B30 (dispatch views), FE-B27 (JobPropertiesPanel save button) — all depend on this spec

---

## ⚠️ MANDATORY STOP: Read These First

Before designing anything, read these files in full:

1. **`dev-docs/testing-support/alpha-testing/ui-testing-status-2026-07-10-v2.md`** — Read the `✅ Decision Made` sections for: "Create Invoice Flow", "Dispatch Board Views", and "Auto-Save Pattern". These are the approved decisions you are designing for.

2. **`frontend/apps/web/src/features/dispatch-board/components/DispatchBoardLanes.tsx`** — This is the existing Day view. Week view must visually match this component's job card design, color coding, and interaction model.

3. **`frontend/apps/web/src/features/dispatch-board/components/JobPropertiesPanel.tsx`** — The right-side panel you are redesigning to add an explicit Save button.

4. **`frontend/packages/ui/src/index.ts`** (or the `packages/ui/src/` directory) — Available shared components. You MUST use existing tokens and components rather than inventing new ones.

---

## Your Role in This Batch

You are the **design authority** for these 4 surfaces. The React Engineers who implement FE-B27, FE-B29, and FE-B30 will implement **exactly what you specify here** — they do not make visual or UX decisions.

### ⚠️ REQUIRED: Tom Approval Gate Before Each Spec Section

**You must present your design proposal for each surface to Tom for approval before writing the spec section for that surface.** Do not design all 4 surfaces and write the full spec in one pass — work through them one at a time:

1. Design Surface 1 (Invoice Builder) → **present to Tom using `ask_followup_question`** → get approval → write the Surface 1 spec section
2. Design Surface 2 (Dispatch Week view) → **present to Tom** → get approval → write the Surface 2 spec section
3. Design Surface 3 (Dispatch Month view) → **present to Tom** → get approval → write the Surface 3 spec section
4. Design Surface 4 (JobPropertiesPanel Save) → **present to Tom** → get approval → write the Surface 4 spec section

**How to present to Tom**: Use `ask_followup_question` to describe your design proposal for the surface in plain language (not markdown spec). Summarize the key layout decisions and interaction patterns. Tom will approve or request changes. Only after Tom approves do you write that section of the design spec.

**Why this process**: Each surface has adjacent design decisions that benefit from validation before locking in. Tom has final authority on UX patterns — not the designer.

Your output for this batch is a **single design spec document** saved at:

> `dev-docs/architecture-design/batch-designs/batch-ui-ds-b1-design-spec.md`

The spec is built section by section as each surface is approved. The design spec must be in Markdown. For each surface, provide:
- **Layout description**: How the page/panel is structured. Label sections. Use ASCII layout diagrams where helpful.
- **Component inventory**: Every UI element on the surface with its purpose and Tailwind/token class guidance
- **State descriptions**: How the surface looks in empty, loading, filled, error, and success states
- **Interaction notes**: What happens on each user action (click, blur, submit, etc.)
- **Design token usage**: Use `text-neutral-900`, `bg-brand-500`, etc. — reference existing tokens from the `tailwind.preset.ts` or existing components. Do NOT invent new color names.

---

## Surface 1: Full-Page Invoice Builder (`/invoices/new`)

### Context

The current `InvoiceCreateModal` is a minimal placeholder popup. We are replacing it with a full-page invoice builder at the route `/invoices/new`, mirroring the structure and UX of the existing quote builder at `/quotes/new`.

**Read the quote builder first** to understand the layout pattern to mirror:
- `frontend/apps/web/src/features/quotes/` — especially `QuoteBuilderPage.tsx` or equivalent

### Approved Feature Spec (from ui-testing-status-2026-07-10-v2.md)

**Entry points**:
- Invoices list "+ Create Invoice" → `/invoices/new` (blank)
- Job detail "Convert to Invoice" → `/invoices/new?job_id={id}` (pre-populated from job)

**Page sections** (in order, top to bottom):
1. **Page header** — breadcrumb ("Invoices → New Invoice") + page title + Cancel/Save action buttons
2. **Header panel** — Customer picker (Combobox / typeahead), Site picker (cascades from customer), Linked Job (read-only badge if `?job_id=` param present)
3. **Billing Mode toggle** — "Select line items" (default tab) vs "Progress billing (%)" (second tab)
4. **Line Items panel** — When job is linked: checklist of time entries + expenses pre-populated from job. Contractor checks/unchecks items. Always: "+ Add custom line item" row at bottom.
5. **Payment Terms panel** — Terms dropdown (Due on Receipt / Net 15 / Net 30 / Custom date), due date field, % split fields if Progress billing mode is active
6. **Notes panel** — Two text areas: "Customer-facing note" (shown on invoice PDF) + "Internal memo" (not on PDF)
7. **Action footer** — "Preview Invoice" button + "Save as Draft" + "Send Invoice" (primary CTA)

### Design Requirements

**Progress Billing mode** (tab 2):
- Shows a % input field: "Bill % of total job value"
- Default: 50%
- Below the % input: shows calculated dollar amount ("= $X,XXX")
- Replaces the line-item checklist with a summary of the full job value

**Line item row** (in checklist mode):
- Checkbox on left
- Item description (e.g., "Labor: Jake — 4h @ $85/hr = $340")
- Amount on right (right-aligned)
- Checked items are included; unchecked = deferred to future invoice
- "+ Add custom line item" opens an inline add row (description field + amount field + add button)

**Payment terms**:
- Dropdown: "Due on Receipt", "Net 15", "Net 30", "Custom date"
- "Custom date" reveals a date picker inline
- Show calculated due date as a label next to the dropdown

**Page-level states**:
- Loading (while fetching job billable items if `?job_id=`): skeleton loader on the Line Items panel
- Empty (no job linked): Line Items panel shows prompt "Link a job above to pre-fill billable items, or add custom line items manually"
- Error (API fetch failed): `<ErrorState>` in the Line Items panel

**Mobile consideration**: The page should stack vertically on narrow viewports. Each panel collapses to a card. Not full mobile design — just ensure panels stack gracefully.

---

## Surface 2: Dispatch Board — Week View

### Context

The existing Day view uses a **lane-as-row** layout (horizontal time axis, vertical lane rows). The Week view currently uses `DispatchGrid.tsx` (old tech-as-column layout). We are replacing the Week view with a **tech-as-column, day-as-row** layout.

**Read the existing Day view for visual reference**:
- `frontend/apps/web/src/features/dispatch-board/components/DispatchBoardLanes.tsx`
- `frontend/apps/web/src/features/dispatch-board/components/JobBlock.tsx`
- `frontend/apps/web/src/features/dispatch-board/components/DispatchToolbar.tsx` — existing toolbar with view tabs

### Approved Spec (2026-07-11 — Option A, Tech × Day Grid)

**v1 Layout decision**: Tech × Day grid. Each column = one technician. Each row = one day. This is the ServiceTitan model — the industry standard for dispatch because dispatchers think "who is doing what when" and need to see per-tech workload at a glance.

**Phase 1.5 addition** (NOT in this batch — log for future): Add a layout toggle in the Week view toolbar to switch between:
- **"By Tech"** (current Option A): tech columns × day rows
- **"By Day"** (Option B): day columns × all jobs stacked, tech shown on each card

This toggle stores its setting in user preferences (localStorage is fine for Phase 1.5). For now, design only the "By Tech" (Option A) layout.

**Clicking a job card in Week view** opens the same `<JobPropertiesPanel>` right-side panel that Day view uses — same component, same behavior, no redesign needed.

**Layout (Option A)**: Tech-as-column dispatch board
- Each **column** = one technician (header = tech name + initials avatar)
- Each **row** = one day (Mon–Fri default; Sun–Sat on 7-day toggle)
- Each **cell** = list of job cards assigned to that tech on that day, stacked vertically in chronological order by `scheduled_start_at`
- **Row height is variable** — each day row grows to the height of its tallest cell (the tech with the most jobs that day). No truncation. Every job must be visible without scrolling or clicking. Functional over aesthetic.
- Each job card shows the start time as a label (e.g., "8:00 AM") — no time axis. Jobs stack top-to-bottom in time order.
- No "+N more" chips — this view is meant to show full daily workload at a glance.

**Navigation bar** (replace 4-Day tab with Week in `DispatchToolbar`):
- View tab buttons: `Day | Week | Month` (remove "4-Day")
- Week-specific controls (visible when Week tab active):
  - `< Prev Week` button
  - `Week of [Mon date] – [Fri date]` label
  - `Next Week >` button
  - `This Week` jump button
  - `5-day / 7-day` toggle

**Column headers**: Technician name + avatar/initials (same as Day view tech headers)

**Row headers**: Day name + date (e.g., "Mon Jul 14")

**Job cells**: Each day × tech cell shows:
- A list of `<JobBlock>` cards (stacked vertically, same card visual as Day view)
- Empty cell: light dashed border, no text
- If over capacity (> schedule_lanes): red tint + "Capacity exceeded" warning chip

**Drag-and-drop**: Drag a `<JobBlock>` from one cell to another — updates `scheduled_date` and `tech_id`. Same `@dnd-kit` interaction model as Day view.

**Scrolling**: `min-width` per column (same constraint as Day view — do not compress below minimum). Horizontal scroll if window too narrow.

**Mobile**: Week view is desktop-only (≥ 768px). On mobile, the Week tab should show a message: "Week view is available on desktop" with a "View Today" button that switches to Day view.

**Empty week state**: "No jobs scheduled this week" centered in the grid with a "+ Create Job" button.

---

## Surface 3: Dispatch Board — Month View

### Context

The existing `MonthCalendarGrid.tsx` exists but needs to be redesigned to be consistent with the new Day/Week views in terms of visual style and navigation.

**Read the existing month component**:
- `frontend/apps/web/src/features/dispatch-board/components/MonthCalendarGrid.tsx`
- `frontend/apps/web/src/features/dispatch-board/components/MonthViewCell.tsx`

### Approved Spec

**Layout**: Standard 6-row × 7-column calendar grid
- Column headers: Sun, Mon, Tue, Wed, Thu, Fri, Sat
- Days from previous/next month shown in muted color in the grid

**Navigation bar** (Month-specific, shown when Month tab active):
- `< Prev Month` button
- `[Month Year]` label (e.g., "July 2026")
- `Next Month >` button
- `Today` jump button

**Day cell content**:
1. Day number (top-left corner, bold for today's date)
2. If jobs exist: job count chip (e.g., "4 jobs" — brand blue pill)
3. Up to 2 abbreviated job chips: `[Tech initials] [Job title truncated]`
4. If more than 2 jobs: `+N more` link

**Interactions**:
- Click any day cell → navigate to **Day view** for that date (not Month drill-in)
- Click a job chip → navigate to job detail page (`/jobs/{id}`)
- Hover day cell → subtle highlight (light brand tint)
- No drag-and-drop in Month view

**Today highlight**: Today's date cell has a distinct background (light brand-50 or similar) with the day number in brand-600.

**Empty month**: No special state needed — cells simply show no job chips.

---

## Surface 4: JobPropertiesPanel — Explicit Save Button

### Context

The existing `JobPropertiesPanel.tsx` (right-side slide-in panel on the dispatch board) currently **saves on blur** — when the user clicks away from a field, it fires a `PATCH /api/v1/jobs/{id}` immediately. 

**Decision (from ui-testing-status-2026-07-10-v2.md TD-1)**: Replace auto-save-on-blur with an **explicit Save button** so the owner can make multiple field changes and confirm them all at once.

**Read the current panel**:
- `frontend/apps/web/src/features/dispatch-board/components/JobPropertiesPanel.tsx` lines 1–60 (header and structure)

### Design Requirements

**Dirty state indicator**: When any field is edited and not yet saved, show a visible "Unsaved changes" indicator — either:
- A small amber dot or pill near the panel header ("● Unsaved changes")
- Or a subtle yellow/amber tint on the panel header bar
The user must always know when they have unsaved edits before leaving.

**Action buttons**: Add a Save/Cancel button pair to the panel footer (above the existing "View Full Job | Create Invoice" action links):
- `[ Cancel ]` (secondary/ghost) — discards changes, reverts all fields to last-saved values
- `[ Save Changes ]` (primary brand button) — fires the PATCH, shows loading state while in-flight
- Both buttons only visible when there are unsaved changes (dirty state)
- When no unsaved changes exist: hide the buttons (panel looks clean)

**Save success**: After PATCH succeeds:
- "Unsaved changes" indicator disappears
- Fields show saved values
- Brief `Saved ✓` inline confirmation (1.5s, then disappears)
- Buttons hide again

**Save error**: If PATCH fails:
- Show an inline error message below the buttons: "Save failed — please try again"
- Keep the buttons visible so the user can retry
- Do NOT auto-dismiss the error

**Cancel behavior**: Clicking Cancel reverts all edited fields to their pre-edit values. If the user had changed the scheduled date + tech assignment, both revert. Show a brief "Changes discarded" message (optional, 1s).

**No auto-save on blur**: Fields must NOT fire any API call when the user clicks out of them. The PATCH only fires when the user explicitly clicks "Save Changes".

---

## Output Instructions

Save your complete design spec to:

> **`dev-docs/architecture-design/batch-designs/batch-ui-ds-b1-design-spec.md`**

The file must contain:

1. **Surface 1: Invoice Builder `/invoices/new`**
   - Full layout description with ASCII wireframe
   - Component inventory table (component name, purpose, token/class guidance)
   - All state descriptions (empty/loading/filled/error/success)
   - Interaction annotations
   - Responsive behavior notes

2. **Surface 2: Dispatch Board Week View**
   - Full layout description with ASCII wireframe
   - Column/row/cell structure spec
   - Navigation bar elements and behaviors
   - Drag-and-drop visual feedback states (dragging, drag-over valid cell, drag-over invalid cell)
   - Empty state and capacity-exceeded state
   - Mobile fallback spec

3. **Surface 3: Dispatch Board Month View**
   - Day cell layout spec (day number, job count chip, job chips, +N more)
   - Navigation bar elements
   - Today highlight and interaction states
   - How it connects to Day view on click

4. **Surface 4: JobPropertiesPanel Save Button**
   - Dirty state indicator (exact placement and visual treatment)
   - Save/Cancel button placement and behavior
   - Save success confirmation visual
   - Save error display
   - Cancel/revert behavior

---

## Design Constraints

- **All components must use existing Tailwind design tokens** from `tailwind.preset.ts`. Do not invent new color names.
- **Job cards in Week view must visually match** the `<JobBlock>` component used in Day view. Do not redesign the card — reuse it.
- **The invoice builder page layout should mirror** the quote builder (`/quotes/new`) structure. Look at the quote builder before designing — don't reinvent the page shell.
- **The `JobPropertiesPanel` Save button** should use the same `bg-brand-500 text-white hover:bg-brand-600` primary button style used elsewhere in the app.
- **Do not design new navigation patterns** — use the existing `DispatchToolbar` tab structure and extend it.

---

## Completion

When your design spec is complete at `dev-docs/architecture-design/batch-designs/batch-ui-ds-b1-design-spec.md`, update the launch plan:

1. Mark **UI-DS-B1** status as ✅ in `dev-docs/analysis/pilot-launch-plan.md` §Phase 1 Batch #2.
2. Add a one-line completion note to the batch row.

The React Engineers for FE-B27, FE-B29, and FE-B30 cannot start until this spec is approved by Tom. The spec is the engineering brief — everything they build comes from it.
