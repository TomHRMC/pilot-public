# Architect Design Session Prompt: BETA-B5 — Dispatch Board Multi-Day Views

**Paste this entire prompt into a fresh Pilot Architect chat session.**

---

## Your Task

Produce the batch design document `dev-docs/architecture-design/batch-designs/batch-beta-v1-fixes-b5-design.md` for BETA-B5.

This is a Phase 1 Surface Design Session. No implementation happens here — the output is the design doc that the React Engineer will execute against.

**Design Principle**: This document is PRD-driven. The PRD defines what the dispatch board must do. The current backend API is the constraint for what data is available — document any gaps as companion tasks, not silent limitations.

---

## Background: What BETA-B5 Fixes

The Dispatch Board (`/schedule`) was built in FE-B4 with a **Day view only**. The 4-Day, Week, and Month tabs exist in the toolbar and correctly calculate date ranges (the `getTabDays()` function in the Zustand store is already correct) and send the correct date params to the API — but the **grid visual does not change**. All four tab modes render the identical single-day-per-tech column layout.

The fix is **pure frontend visual rendering**. No backend work is needed for 4-Day and Week views. Month view may require a different grid structure.

Source issue: `dev-docs/testing-support/fe-ui-testing-open-issues-v1.md` §2.1  
Source plan: `dev-docs/analysis/pilot-app-beta-fixes-v1-impl-plan.md` §8 BETA-B5

---

## Phase 1: Required Reads (Complete ALL Before Writing the Design Doc)

### Step 1: Read the PRD for dispatch board requirements

Read `dev-docs/product-requirements/mvp-prd.md` — find the section covering the Dispatch Board (look for §3.14 Scheduling & Dispatch or similar). Document:
- What does the PRD say about multi-day views specifically?
- What visual layout does the PRD specify for 4-Day, Week, and Month views?
- Are drag-drop and conflict detection required in multi-day mode?

### Step 2: Read the existing Dispatch Board implementation

Read the actual source files — do not assume what they contain:

```
frontend/apps/web/src/features/dispatch-board/components/DispatchGrid.tsx
frontend/apps/web/src/features/dispatch-board/components/DispatchBoardPage.tsx
frontend/apps/web/src/features/dispatch-board/components/DispatchToolbar.tsx
frontend/apps/web/src/features/dispatch-board/components/DispatchGridColumn.tsx
frontend/apps/web/src/features/dispatch-board/components/JobBlock.tsx
frontend/apps/web/src/features/dispatch-board/store.ts
frontend/apps/web/src/features/dispatch-board/hooks/useDispatchBoard.ts
```

This is the most critical read. The design must be grounded in what actually exists, not assumed. Specifically identify:
- How does `DispatchGrid.tsx` currently render? What props does it accept?
- How does `store.ts` define `viewTab` and `getTabDays()`? What date range does each tab produce?
- What does `useDispatchBoard.ts` send to the API? What response shape does it expect?
- How does `DispatchGridColumn.tsx` render a single tech column with job blocks?
- What existing TypeScript interfaces describe the board data?

### Step 3: Verify the API response shape for multi-day ranges

Check `backend/openapi_schema_map.md` for the dispatch board endpoint:

```bash
python3 -c "
import json
spec = json.load(open('backend/openapi.json'))
path = '/api/v1/scheduling/dispatch-board'
if path in spec['paths']:
    print(json.dumps(spec['paths'][path], indent=2))
else:
    print('PATH NOT FOUND')
" 2>/dev/null | head -100
```

Determine:
- Does the same endpoint handle multi-day ranges (4-day, week)?
- Does the response shape change for multi-day ranges vs. single-day?
- Are jobs that span multiple days returned differently?
- Is there any pagination or separate endpoint for wider date ranges?

### Step 4: Read the FE-B4 design doc for original dispatch board intent

```
dev-docs/architecture-design/batch-designs/batch-fe-b4-design.md
```

Understand what FE-B4 specified for 4-Day/Week/Month views originally. Did the design doc define how multi-day rendering should work? Was it left as "Day view only for MVP" or was multi-day always intended?

### Step 5: Read `mvp-arch.md` for SSE and real-time patterns on the board

```
dev-docs/architecture-design/mvp-arch.md
```

Specifically the dispatch board SSE pattern (§13 or wherever the board streaming is documented). Does the SSE architecture change for multi-day views?

---

## Phase 2: Design Decisions to Make and Document

After completing all reads, make and document these decisions:

### Decision 1: Grid Layout for 4-Day and Week Views

The issue description says the fix is "only the visual rendering is missing." Based on reading `DispatchGrid.tsx`, decide:

**Option A**: Pivot to date-columns (N dates × M techs grid)  
For 4-Day/Week: each column represents ONE DATE (not one tech). Techs are shown as nested rows within each date column. This means the column header is a date, and each tech's jobs for that date are stacked vertically within.

**Option B**: Keep tech-columns, add date grouping within each column  
For 4-Day/Week: each column is still one tech, but the column renders time blocks for ALL days in the range, with date separators. The time axis stretches to cover the full range.

**Option C**: Side-by-side day panels  
The 4-Day/Week view renders N identical Day-view panels side-by-side, one per date. Each panel is a scaled-down version of the Day view.

Document which option best matches:
- The PRD intent (if specified)
- The existing component architecture in `DispatchGrid.tsx`
- The API response shape (does it group by date or by tech?)
- The minimum viable implementation complexity for beta

### Decision 2: Month View Layout

Month view is fundamentally different from Day/4-Day/Week:
- Day/4-Day/Week: a time-axis grid (hours as Y-axis)
- Month: a calendar grid (days as cells, no time axis)

Determine the month view design:
- **Option A**: Full calendar grid (7-column × ~5-row) with job count per day cell; click a day to drill into Day view
- **Option B**: Month as a list of weeks, each week showing job blocks
- **Option C**: Month view deferred for beta (document as explicit out-of-scope decision); "Month" tab active but shows "Month view coming soon" state

For beta testing, Option C (deferred with a clear state) is acceptable if the full Month calendar is too complex. **Document the explicit decision either way.**

### Decision 3: Drag-Drop in Multi-Day Views

In Day view, job blocks are draggable (`react-dnd`). For multi-day views:
- Does drag-drop across days make sense for beta?
- If yes: what are the constraints (e.g., can drag to different day, same tech only)?
- If no: document "multi-day views are read-only; drag-drop only in Day view" as an explicit MVP constraint

### Decision 4: Component Architecture

Based on reading `DispatchGrid.tsx`, determine how to add the multi-day rendering mode:

**Recommended approach** (verify against actual code):
- Add a `viewMode: 'day' | '4day' | 'week' | 'month'` prop to `<DispatchGrid>` 
- `viewMode='day'` renders the existing day grid (no changes to current code path)
- `viewMode='4day'` and `viewMode='week'` render the new multi-day grid layout
- `viewMode='month'` renders the month calendar (or deferred state)

Document the exact prop name, the switch point, and whether any new sub-components are introduced.

### Decision 5: Data Normalization

The current hook (`useDispatchBoard`) likely fetches data optimized for day view. For 4-Day/Week, the same endpoint is called with a wider date range. Determine:
- Does the response data need to be normalized differently for multi-day rendering?
- Are there new TypeScript interfaces needed for the multi-day data shape?
- Does the existing `DispatchBoardResponse` type (if it exists) cover the multi-day case?

---

## Phase 3: Write the Design Document

**Output file**: `dev-docs/architecture-design/batch-designs/batch-beta-v1-fixes-b5-design.md`

The design doc MUST contain sections A through I:

### A. Input Read Summary

Table of all artifacts read, key findings. Include what the `DispatchGrid.tsx` and `store.ts` currently look like (paraphrase the key code structure — do NOT copy-paste raw code, but describe the component API and how the viewTab state is managed).

### B. Execution Order

List components in implementation order:
1. Any new TypeScript interfaces/types
2. `DispatchGrid` multi-day rendering extension
3. Any new sub-components (e.g., `<MultiDayGrid>`, `<MonthCalendarGrid>`)
4. `DispatchToolbar` updates (if any — verify toolbar already switches viewTab correctly)
5. Tests

### C. Component Changes

For each component being modified or created:
- Exact file path
- What changes (add prop, add rendering branch, add sub-component)
- The exact prop interface change (if any) — must be backward compatible; Day view must not regress

### D. API Endpoint Consumption

Document whether multi-day views call the same endpoint with different date params, or a different endpoint. The hook should NOT need to change significantly — it already sends `start_date`/`end_date` correctly. Document what data normalization (if any) is needed for multi-day rendering.

### E. Pattern Reuse Decisions

Does the multi-day grid reuse `<DispatchGridColumn>` or build a new column component? Does the Month view reuse anything from existing calendar conflict pages?

### F. Shared Module Interfaces

If any new TypeScript interfaces are added to describe multi-day board data, specify them fully.

### G. Open Questions Resolved

All design decisions documented with rationale. Specifically:
- Which layout option was chosen for 4-Day/Week and why
- Whether Month view is implemented or deferred
- Whether drag-drop is supported in multi-day mode

### H. External Dependency Status

BETA-B5 is pure frontend. No new backend dependencies. Document any assumptions about the API response shape that the implementation depends on.

### I. Test Plan

Per rendering mode:
- Unit tests for multi-day grid rendering
- Integration test: switching tabs changes the rendered grid structure
- Regression tests: Day view still works exactly as before

---

## Design Doc Quality Gates

Before finalizing:

- [ ] Every code file referenced was actually read (not assumed)
- [ ] `DispatchGrid.tsx` current props interface documented
- [ ] `store.ts` `viewTab` type and `getTabDays()` behavior documented
- [ ] API response shape for multi-day range documented (from `openapi.json`)
- [ ] Layout option for 4-Day/Week chosen with explicit rationale
- [ ] Month view decision explicitly documented (implement or defer)
- [ ] Drag-drop decision explicitly documented
- [ ] Backward compatibility confirmed: Day view unchanged
- [ ] Component changes are additive (new `viewMode` prop, not refactoring existing code)

---

## Output

The completed design doc at:  
**`dev-docs/architecture-design/batch-designs/batch-beta-v1-fixes-b5-design.md`**

Once complete and reviewed by Tom, it becomes the input for the BETA-B5 React Engineer implementation prompt.
