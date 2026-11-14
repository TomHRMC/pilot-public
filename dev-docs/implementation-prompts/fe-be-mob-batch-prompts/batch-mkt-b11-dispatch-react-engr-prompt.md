# Implementation Prompt: MKT-B11-D — Dispatch Board Schedule Lane Redesign

**Mode**: Pilot React Engineer  
**Batch**: MKT-B11-D  
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §MKT-B11  
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-mkt-b11-db-design.md` §F.2 (lane enforcement), §B.4 (target tier data)  
**Estimated session**: 5–7 hours  
**Platform**: Web app only (`frontend/apps/web/`)  
**Backend companion**: MKT-B11-BE — **must be complete first**. Run `pnpm sync-api-types` after backend closes before starting this batch.

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-react-engineer/react-engineer-rules.md`** — in full
- **`dev-docs/architecture-design/batch-designs/batch-mkt-b11-db-design.md`** — §F.2 (lane enforcement query), §B.4 (target subscription_tier data with schedule_lanes column), §G.8 (Founders upgrade path)
- **`dev-docs/marketing-analysis/gtm-pricing-strategy-v1.md` §D1–D3** — schedule lane definition and dispatch board redesign decision

**Critical rules for this batch:**

- **Rule 1.1**: Before writing ANY hook or API call, verify the endpoint exists in `backend/openapi_schema_map.md`. If it is NOT there → **STOP and ask Tom**.
- **Rule 1.2**: Run `pnpm sync-api-types` first — `schedule_lanes` is a new field on `SubscriptionTierResponse`. All TypeScript types for backend payloads come from `@pilot/shared-types`.
- **Rule 2**: All API calls use `apiClient` from `@pilot/shared-api`. `fetch()` is permanently banned for `/api/v1/...` calls.
- **Rule 7**: Check `packages/ui/src/index.ts` before creating any new shared component — reuse existing `<LoadingState>`, `<ErrorState>`, `<EmptyState>` rather than creating new ones.
- **Rule 8.a**: No new npm dependencies without first checking `package.json` for what is already installed. Check for `@dnd-kit/core` before specifying it.
- **Rule 9**: Route files in `apps/web/src/app/(authed)/` MUST be thin server components — no `"use client"`, no data fetching. All logic goes in feature components.
- **Rule 10**: If ANY test fails during your work — fix it before declaring the batch done.

---

## Pre-Work: Establish Regression Baseline

Before touching any file:

```bash
cd <repo>/frontend
pnpm --filter web test 2>&1 | tail -5
```

Record the exact count: **`X passed, Y failed`**. These counts must still pass at the end of the batch.

---

## Pre-Work: Sync API Types

```bash
cd <repo>/frontend
pnpm sync-api-types
```

After running, verify `schedule_lanes` appears in the subscription tier type:
```bash
grep -n "schedule_lanes" frontend/packages/shared-types/src/api-schema.d.ts
```

If `schedule_lanes` is not present → MKT-B11-BE has not been run yet. **STOP** — do not proceed until the backend batch is complete.

---

## Pre-Work: Verify Endpoints

```bash
grep -A 8 "subscription-tiers" backend/openapi_schema_map.md
grep -A 5 "schedule" backend/openapi_schema_map.md
```

| Hook | Endpoint | Purpose |
|---|---|---|
| `useSubscriptionEntitlement` | `GET /api/v1/subscription-tiers` | Get active tier + `schedule_lanes` count |
| `useDispatchJobs` | `GET /api/v1/schedule/board` | Current board jobs (existing endpoint) |
| `useScheduleJob` | `PATCH /api/v1/jobs/{id}` | Update job schedule (existing endpoint) |

**If `GET /api/v1/subscription-tiers` does not expose `schedule_lanes`** → MCP-verify the field exists in DB, then check `SubscriptionTierResponse` in `backend/api/routes/subscription_tiers.py`. If the field is missing from the response schema → STOP and ask Tom.

---

## Pre-Work: Check Available Dependencies

```bash
# Check if @dnd-kit is already installed
grep "@dnd-kit" frontend/apps/web/package.json
grep "@dnd-kit" frontend/package.json
find frontend -name "package.json" -not -path "*/node_modules/*" | xargs grep "@dnd-kit" 2>/dev/null
```

If `@dnd-kit/core` is not installed, you will need to add it. Only add it if not present — do not add a duplicate or different version of an already-installed drag library.

---

## Pre-Work: Read These Source Files

Read each of these with `read_file` before writing any code:

```
frontend/apps/web/src/features/dispatch-board/           ← entire directory — read all files
frontend/apps/web/src/app/(authed)/schedule/page.tsx     ← route file for dispatch board
frontend/apps/web/src/hooks/useSubscriptionEntitlement.ts ← if it exists; check with find
frontend/packages/ui/src/index.ts                        ← confirm available shared components
frontend/apps/web/src/mocks/handlers/index.ts            ← register any new MSW handlers here
```

Also run:
```bash
find frontend/apps/web/src/features/dispatch-board -name "*.tsx" -o -name "*.ts" | sort
find frontend/apps/web/src/features -name "useSubscription*" 2>/dev/null
find frontend/apps/web/src/hooks -name "*.ts" 2>/dev/null
```

---

## Background / Context — Schedule Lane Model

**What is a Schedule Lane?** A visual row on the dispatch board — one parallel job slot. Any number of non-overlapping jobs can share a lane throughout the day (e.g., Job A from 8am–noon and Job B from 1pm–4pm can both be in Lane 1). Any user (owner, tech, apprentice) can be assigned to any job in any lane — unlimited users, no per-seat charge.

**The licensing constraint**: The total number of lanes = base tier `schedule_lanes` + any add-on lane packs in `tenant_product_feature_override`. The `useScheduleLaneCount()` hook encapsulates this resolution.

**Current dispatch board state**: The existing dispatch board shows technicians as columns. This batch replaces that with lane-as-row layout. The current tech-as-column board is **being replaced** — this is a full redesign of the board layout, not an extension.

**Key user flows to support**:
1. Dispatcher sees N lane rows on the board (N = their plan's lane count)
2. Dispatcher drags an unscheduled job from a queue into a lane at a time slot
3. Dispatcher clicks a placed job to open right-panel properties and assign techs
4. System blocks adding a job if it would overlap all occupied lanes at that time window (shows upgrade CTA)

---

## Task 1 — Create `useScheduleLaneCount()` Hook

**File to create**: `frontend/apps/web/src/features/dispatch-board/hooks/useScheduleLaneCount.ts`

This hook returns the effective lane count for the current tenant:
1. First checks `tenant_product_feature_override` for add-on lanes
2. Falls back to the subscription tier's `schedule_lanes` value

```typescript
// Adjust implementation based on actual API response shape from pnpm sync-api-types
// Read the current useSubscriptionEntitlement pattern before implementing

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";

export function useScheduleLaneCount(): {
  laneCount: number;
  isLoading: boolean;
  isError: boolean;
} {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["subscription-lane-count"],
    queryFn: async () => {
      // Fetch active tiers — after MKT-B11-BE, only 'founders' tier is active
      const res = await apiClient.get("/api/v1/subscription-tiers");
      return res.data;
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: false,
  });

  // Extract schedule_lanes from active tier
  // Adjust field access based on actual API schema from pnpm sync-api-types
  const activeTier = Array.isArray(data)
    ? data.find((t: any) => t.is_active)
    : null;
  const laneCount = activeTier?.schedule_lanes ?? 5; // default to 5 (founders/starter base)

  return { laneCount, isLoading, isError };
}
```

> **If `tenant_product_feature_override` (add-on lanes) needs to be factored in**: check whether the subscription API already applies the override before responding, or whether a separate call is needed. Confirm with `grep "effective_lanes\|schedule_lanes\|product_feature_override" backend/openapi_schema_map.md`. If the override is not exposed via API yet, implement with the base tier count for now and document as a follow-up task.

**Intermediate test run:**
```bash
cd frontend && pnpm --filter web test 2>&1 | tail -5
```

---

## Task 2 — Create Lane-Based Board Layout Component

**File to create**: `frontend/apps/web/src/features/dispatch-board/components/DispatchBoardLanes.tsx`

This is the core replacement for the tech-as-column layout.

**Layout structure**:
```
┌─ Board ──────────────────────────────────────────────────────┐
│  Time axis: 6am ─── 7am ─── 8am ─── ... ─── 6pm           │
│  ┌─ Lane 1 ─────────────────────────────────────────────┐   │
│  │  [Job A, 8am–noon]          [Job B, 1pm–4pm]        │   │
│  └───────────────────────────────────────────────────────┘   │
│  ┌─ Lane 2 ─────────────────────────────────────────────┐   │
│  │  [Job C, 9am–5pm]                                    │   │
│  └───────────────────────────────────────────────────────┘   │
│  ... N lanes total (from useScheduleLaneCount)               │
│  ┌─ Upgrade CTA (shown when lanes are full) ────────────┐   │
│  │  "All lanes occupied. Add more lanes — $10/lane/mo"  │   │
│  └───────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

**Props interface**:
```typescript
interface DispatchBoardLanesProps {
  date: Date;              // Currently viewed date
  laneCount: number;       // From useScheduleLaneCount()
  jobs: ScheduledJob[];    // Jobs scheduled for this date
  onJobClick: (job: ScheduledJob) => void;   // Opens right panel
  onJobDrop: (jobId: string, laneIndex: number, startTime: Date) => void;  // After drag
  onUpgradeClick: () => void;  // Lane full → upgrade prompt
}
```

**Time grid**: The horizontal time axis should span the business day (6am–6pm by default, scrollable). Each hour is a fixed-width column. Jobs are positioned using CSS `left` (start time offset) and `width` (duration).

**Lane overflow indicator**: When all N lanes are occupied at a given time slot:
- Show a visual indicator on the time slot cells that are blocked
- Show a persistent "All lanes occupied" banner or CTA below the last lane with an "Add more lanes" link

---

## Task 3 — Implement Drag-and-Drop

**Prerequisite**: Verify `@dnd-kit/core` is installed (Pre-Work step). If not, install it:
```bash
cd frontend && pnpm --filter web add @dnd-kit/core @dnd-kit/utilities
```

**Draggable area**: An "Unscheduled Jobs" sidebar/queue panel containing jobs with no `scheduled_start_at`. Each job card is a `<Draggable>` element.

**Drop zones**: Each time slot cell in each lane row is a `<Droppable>`. On drop, call `onJobDrop(jobId, laneIndex, droppedStartTime)` which triggers a `PATCH /api/v1/jobs/{id}` to update `scheduled_start_at`, `scheduled_end_at`, and `lane_number`.

> **Note on `lane_number`**: Check whether the `job` model currently has a `lane_number` field. Run `grep -n "lane_number" backend/openapi_schema_map.md`. If it's missing, it may not have been added in MKT-B11-BE (check the design doc). If absent → the dispatch board can render based on time overlap detection (auto-assign jobs to lanes by collision detection client-side) rather than a stored lane_number. Document which approach is used in the Completion Summary.

**Drag-and-drop pattern** (read `@dnd-kit` docs if needed):
```typescript
import { DndContext, useDraggable, useDroppable } from "@dnd-kit/core";

// Wrap the board in <DndContext onDragEnd={handleDragEnd}>
// Each job card: const { attributes, listeners, setNodeRef } = useDraggable({ id: job.id })
// Each time slot: const { setNodeRef, isOver } = useDroppable({ id: `lane-${laneIdx}-${timeSlot}` })
```

---

## Task 4 — Create Right-Panel Job Properties View

**File to create**: `frontend/apps/web/src/features/dispatch-board/components/JobPropertiesPanel.tsx`

This is a slide-in right column panel that appears when any job on the board is clicked. Pattern: Inspector/Properties panel (Figma sidebar, VS Code file properties style).

**Panel sections**:

1. **Header**: Job title + status badge + close button (×)

2. **Customer & Site**: 
   - Customer display name (link to `/customers/{id}`)
   - Site address

3. **Schedule** (editable inline):
   - Start date + time (date/time picker or text input)
   - End date + time
   - On change: call `PATCH /api/v1/jobs/{id}` with new schedule

4. **Assigned Technicians** (editable):
   - List of currently assigned users (name + role)
   - "Add technician" → dropdown of all active tenant users
   - Remove button per user
   - On change: call existing job tech assignment API

5. **Job Status**: Status pill/badge with change action (draft → scheduled → in_progress → completed)

6. **Notes**: Internal notes text area (editable inline)

7. **Actions footer**:
   - "View Full Job" → link to `/jobs/{id}`
   - "Create Invoice" → link to invoice creation

**Panel behavior**:
- Slide in from the right when a job is clicked on the board
- Board content does NOT re-render when panel opens — panel overlays on the right
- Close via × button, Escape key, or clicking outside the panel

**Width**: ~320px fixed on desktop; full-width bottom sheet on mobile (if applicable)

```typescript
interface JobPropertiesPanelProps {
  job: ScheduledJob | null;   // null = panel closed
  onClose: () => void;
  onJobUpdated: (job: ScheduledJob) => void;  // refetch after patch
}
```

---

## Task 5 — Update Route/Feature Entry Point

**File**: `frontend/apps/web/src/features/dispatch-board/` — update the main `DispatchBoard` component (or `DispatchBoardPage` — read the existing files to find the entry point)

The main board component needs to:
1. Call `useScheduleLaneCount()` to get the lane count
2. Pass `laneCount` to `<DispatchBoardLanes />`
3. Manage selected job state for `<JobPropertiesPanel />`
4. Show `<LoadingState>` while lane count is loading
5. Show `<ErrorState>` if lane count fails to load

**Route file** (`frontend/apps/web/src/app/(authed)/schedule/page.tsx`) must remain a thin server component — no changes to the route file beyond what's already there.

---

## Task 6 — Lane Overflow Enforcement

When the user drops a job that would occupy all lanes at a given time slot, the drop must be rejected and an upgrade CTA shown.

**Lane availability check** (client-side):
```typescript
function checkLaneAvailability(
  jobs: ScheduledJob[],
  laneCount: number,
  startTime: Date,
  endTime: Date,
): { available: boolean; blockedLanes: number[] } {
  // Find how many lanes are occupied during [startTime, endTime]
  // A lane is occupied if it already has a job whose time range overlaps
  // Return available=true if there is at least one free lane
}
```

If `!available`:
- Cancel the drop (DndContext `onDragEnd` — do not call the API)
- Show the lane-full banner/indicator on the board
- The upgrade CTA links to `Settings > Subscription` or opens an upgrade modal

---

## Task 7 — MSW Handlers for Tests

**File**: `frontend/apps/web/src/mocks/handlers/dispatchBoardHandlers.ts` (update if exists; create if needed)

Add handlers for any new endpoints used in this batch:
- `GET /api/v1/subscription-tiers` — return mock with `schedule_lanes: 5` for founders tier
- Any job scheduling endpoints modified in this batch

Register in `frontend/apps/web/src/mocks/handlers/index.ts`.

---

## Task 8 — Write Tests

**Test file**: `frontend/apps/web/src/__tests__/batch_mkt_b11_dispatch/dispatch_board_lanes.integration.test.tsx`

Required test coverage:

```typescript
describe("DispatchBoardLanes — Schedule Lane Model", () => {
  it("renders N lane rows equal to useScheduleLaneCount result", () => {
    // Mock useScheduleLaneCount to return 5
    // Render DispatchBoardLanes
    // Assert 5 lane rows are present
  });

  it("shows upgrade CTA when all lanes are occupied at a time slot", () => {
    // Mock 5 jobs filling all 5 lanes at 10am
    // Drop a 6th job at 10am
    // Assert upgrade CTA appears
    // Assert job was NOT added to board (PATCH not called)
  });

  it("allows job placement in a free lane", () => {
    // Mock 2 jobs in lanes 1 and 2
    // Drop job into lane 3
    // Assert job appears in lane 3
  });

  it("opens job properties panel on job click", () => {
    // Render board with 1 job
    // Click the job
    // Assert <JobPropertiesPanel> is visible with job data
  });

  it("closes panel on Escape key", () => {
    // Open panel
    // Press Escape
    // Assert panel is no longer visible
  });

  it("lane properties panel shows editable schedule fields", () => {
    // Open panel
    // Assert start time and end time inputs are present and editable
  });
});
```

---

## Final Verification

### Phase 1 — Targeted tests (run after each task group)

```bash
cd <repo>/frontend
pnpm --filter web test 2>&1 | tail -6
```

### Phase 2 — Full verification (run once at the end)

```bash
cd <repo>/frontend && pnpm --filter @pilot/ui check-types && pnpm --filter web check-types && pnpm --filter @pilot/ui lint && pnpm --filter web lint && echo "=== TYPE+LINT PASS ===" && pnpm --filter @pilot/ui test 2>&1 | tail -6 && pnpm --filter web test 2>&1 | tail -6 && echo "=== MKT-B11-D FINAL VERIFICATION COMPLETE ==="
```

**Manual smoke test** (required before declaring done):
1. Log in as `dev@pilot.local` (owner) → navigate to Schedule
2. Verify the board renders N lane rows (N = subscription tier `schedule_lanes`)
3. Drag an unscheduled job onto a lane — verify it appears on the board
4. Click a placed job — verify right-panel opens with correct job data
5. Edit the schedule time — verify `PATCH` fires and board updates
6. Assign a tech — verify assignment appears in panel
7. Fill all lanes at a time slot — verify upgrade CTA appears on drop attempt

> **Any failure must be fixed before the batch is declared done.**

---

## Definition of Done — MKT-B11-D

- [ ] Pre-modification regression baseline captured (zero pre-existing failures, or confirmed with Tom)
- [ ] `pnpm sync-api-types` run — `schedule_lanes` field present in shared types
- [ ] All mandatory source files read before modifying (existing dispatch board fully read)
- [ ] Endpoints verified in `backend/openapi_schema_map.md`
- [ ] `@dnd-kit/core` verified as installed (or installed if missing)
- [ ] **Task 1**: `useScheduleLaneCount()` hook created — returns effective lane count
- [ ] **Task 2**: `<DispatchBoardLanes>` component created — lane-as-row layout renders N lanes
- [ ] **Task 3**: Drag-and-drop functional — jobs drag from queue onto lane at time slot
- [ ] **Task 4**: `<JobPropertiesPanel>` created — opens on job click with all 7 sections
- [ ] **Task 5**: Main `DispatchBoard` component updated — uses `useScheduleLaneCount()`, manages panel state
- [ ] **Task 6**: Lane overflow enforcement — blocks drop when all lanes occupied + shows upgrade CTA
- [ ] **Task 7**: MSW handler for `GET /api/v1/subscription-tiers` updated with `schedule_lanes` field; registered in `index.ts`
- [ ] **Task 8**: Test file created — all 6 tests pass
- [ ] Manual smoke test passed (all 7 steps)
- [ ] Zero TypeScript errors (`pnpm --filter web check-types` clean)
- [ ] Zero ESLint warnings
- [ ] **Phase 2 FULL verification passes** (`=== MKT-B11-D FINAL VERIFICATION COMPLETE ===`)
- [ ] Completion Summary added to `pilot-launch-plan.md` §MKT-B11

---

## Completion Summary

After all Definition of Done items are complete, add a Completion Summary to `dev-docs/analysis/pilot-launch-plan.md` §MKT-B11:

```markdown
### MKT-B11-D — Dispatch Board Schedule Lane Redesign: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot React Engineer
**Baseline**: X passed (web)
**Final**: X+N passed (+N new tests)

#### What Was Accomplished

- Created useScheduleLaneCount() hook — reads schedule_lanes from active subscription tier
- Created DispatchBoardLanes component — lane-as-row layout replaces tech-as-column
- Implemented drag-and-drop with @dnd-kit/core — jobs drag from queue to lane/time slot
- Created JobPropertiesPanel — 7-section right-panel properties view (schedule/assign/notes/actions)
- Implemented lane overflow enforcement — blocks drop when all lanes full, shows upgrade CTA
- [Note on lane_number: stored in DB / computed client-side — document which approach]

#### Files Changed / Created

| File | Action |
|---|---|
| `frontend/apps/web/src/features/dispatch-board/hooks/useScheduleLaneCount.ts` | Created |
| `frontend/apps/web/src/features/dispatch-board/components/DispatchBoardLanes.tsx` | Created |
| `frontend/apps/web/src/features/dispatch-board/components/JobPropertiesPanel.tsx` | Created |
| `frontend/apps/web/src/features/dispatch-board/[main board file]` | Updated — integrates lane count + panel |
| `frontend/apps/web/src/mocks/handlers/dispatchBoardHandlers.ts` | Updated |
| `frontend/apps/web/src/mocks/handlers/index.ts` | Updated — handler registered |
| `frontend/apps/web/src/__tests__/batch_mkt_b11_dispatch/dispatch_board_lanes.integration.test.tsx` | Created — N tests |

#### Tests Added

| Test File | Type | Tests | All Pass |
|---|---|---|---|
| `__tests__/batch_mkt_b11_dispatch/dispatch_board_lanes.integration.test.tsx` | Integration | N | ✅ |
```
