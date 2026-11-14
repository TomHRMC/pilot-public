# Implementation Prompt: UI-FIX-2B — Multi-Tech Assignment: Frontend (React Engineer)

**Mode**: Pilot React Engineer  
**Batch**: UI-FIX-2B (Frontend half)  
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` — UI-FIX-2B row  
**Source decisions**: `dev-docs/architecture-design/batch-designs/ui-fix-2-decisions.md § FIX-015`  
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-ui-fix-2b-design.md`  
**Estimated session**: 3–4 hours  
**Platform**: Web only (`apps/web`)  
**Backend companion**: UI-FIX-2B Python Engineer — **must be complete and committed before starting this prompt**

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-react-engineer/react-engineer-rules.md`** — in full
- **`dev-docs/architecture-design/batch-designs/batch-ui-fix-2b-design.md`** — every section (A–I)
- **`dev-docs/architecture-design/batch-designs/ui-fix-2-decisions.md § FIX-015`** — the full FIX-015 section including Multi-Tech UX Design

**Critical rules for this batch:**

- **Rule 1.1**: Before writing ANY hook, verify its endpoint exists in `backend/openapi_schema_map.md`. If NOT there → **STOP and ask Tom**. Specifically verify `GET /api/v1/users` now returns `first_name`, `last_name`, `display_color`.
- **Rule 1.3**: Run `pnpm sync-api-types` FIRST — the Python Engineer batch added 3 new fields to `TenantUserWithRoleResponse`. TypeScript types won't have them until you sync.
- **Rule 2**: All API calls use `apiClient` from `@pilot/shared-api`. `fetch()` is permanently banned for `/api/v1/...` calls.
- **Rule 7**: Check `packages/ui/src/index.ts` before creating any new component — `<LoadingState>`, `<ErrorState>`, `<EmptyState>`, `<RoleGate>` are available.
- **Rule 8**: No new npm dependencies without first checking `package.json`.
- **Rule 9**: Route files in `app/(authed)/` MUST be thin server components — no `"use client"`, no data fetching.
- **Rule 10**: If ANY test fails — even pre-existing — fix it before declaring done.

---

## Design Decisions (Do Not Re-Litigate)

From Design Doc §G — these decisions are final:

| Decision | Outcome | Rationale |
|---|---|---|
| `JobEditModal.tsx` included? | **No** — tech assignment is real-time POST/DELETE, no save-button flow | Immediate API call = no form submit needed |
| Primary/helper UI labels? | **"Lead" badge for primary only** — no "primary"/"helper" terminology exposed to user | MVP simplicity |
| Role auto-computation | First addition → `role='primary'`; additional → `role='helper'` — computed from assignments list length | No UI radio |
| Re-fetch vs optimistic update | **Re-fetch on success** — dispatch board real-time accuracy over perceived speed | Board grid must reflect truth |
| Remove primary with helpers remaining | **No auto-promotion** — leave helpers as helpers | Backend does not auto-promote; MVP scope |
| Component location | `apps/web` only (not `packages/ui`) | No mobile requirement in this batch |

---

## Pre-Work: Establish Regression Baseline

```bash
cd <repo>/frontend
pnpm --filter web test 2>&1 | tail -5
```

Record exact count. Fix any unexplained failures before proceeding.

---

## Pre-Work: Sync API Types

```bash
cd <repo>/frontend
pnpm sync-api-types
```

This picks up the new `first_name`, `last_name`, `display_color` fields on `TenantUserWithRoleResponse` added by the Python Engineer batch. If this fails, check that the backend `openapi.json` was committed.

---

## Pre-Work: Verify Endpoints

```bash
grep -A 8 "GET /api/v1/users" backend/openapi_schema_map.md
grep -A 5 "first_name\|last_name\|display_color" backend/openapi_schema_map.md | head -15
grep -A 3 "assignments" backend/openapi_schema_map.md | grep "scheduling" | head -10
```

Verified endpoints for this batch:

| Hook | Endpoint | Must Verify |
|---|---|---|
| `useTenantUsers` | `GET /api/v1/users` | Confirm `first_name`, `last_name`, `display_color` in response schema |
| `useJobAssignments` | `GET /api/v1/scheduling/jobs/{job_id}/assignments` | Confirm exists |
| `useAddJobAssignment` | `POST /api/v1/scheduling/jobs/{job_id}/assignments` | Confirm exists |
| `useRemoveJobAssignment` | `DELETE /api/v1/scheduling/jobs/{job_id}/assignments/{assignment_id}` | Confirm exists |

If any endpoint is NOT confirmed → **STOP and ask Tom**.

---

## Pre-Work: Read These Source Files

Read each of these with `read_file` before writing any code:

```
frontend/apps/web/src/features/dispatch-board/components/JobPropertiesPanel.tsx
  ← find the existing tech display block + dead "+ Add technician" button (~lines 395–439)
  ← understand the onJobUpdated callback prop

frontend/apps/web/src/features/jobs/components/JobDetailPage.tsx
  ← find JobDetailHeader and JobProfitabilityWidget to know insertion point
  ← understand jobId prop passing pattern

frontend/packages/ui/src/index.ts
  ← confirm LoadingState, ErrorState, EmptyState, RoleGate import paths

frontend/apps/web/src/mocks/handlers/index.ts
  ← understand barrel structure before adding new handlers

frontend/packages/ui/src/role-gate/permissions.ts
  ← confirm "schedule.manage" permission key exists (needed for RoleGate)
```

Also run:
```bash
find frontend/apps/web/src/features -name "use*.ts" | grep -i "job\|user" | head -15
find frontend/apps/web/src/mocks/handlers -name "*.ts" | head -20
```

---

## Step 1 — Create `useTenantUsers` Hook

**File**: `apps/web/src/features/users/hooks/useTenantUsers.ts` (create directory if needed)

```typescript
"use client";
// Read the actual TenantUserWithRoleResponse type from @pilot/shared-types after pnpm sync-api-types
// Adjust type name to match what was generated
import { apiClient } from "@pilot/shared-api";
import { useQuery } from "@tanstack/react-query";

export interface TenantUserItem {
  user_id: string;
  email: string;
  first_name: string | null;
  last_name: string | null;
  display_color: string | null;
  role_code: string;
  is_active: boolean;
  display_name: string; // computed
}

export function useTenantUsers() {
  return useQuery({
    queryKey: ["tenant-users"],
    queryFn: async (): Promise<TenantUserItem[]> => {
      const resp = await apiClient.get("/api/v1/users");
      // Map to TenantUserItem, computing display_name
      return (resp.data.items ?? resp.data).map((u: any) => ({
        ...u,
        display_name:
          [u.first_name, u.last_name].filter(Boolean).join(" ").trim() ||
          u.email,
      }));
    },
    staleTime: 60_000,
  });
}
```

> Read the actual API response shape from `openapi.json` or `pnpm sync-api-types` output. Adjust field names and response shape accordingly. The `items ?? data` pattern handles both paginated and non-paginated responses.

---

## Step 2 — Create `useJobAssignments` Hook

**File**: `apps/web/src/features/jobs/hooks/useJobAssignments.ts`

```typescript
// GET /api/v1/scheduling/jobs/{jobId}/assignments
// Returns list of active assignments
// staleTime: 0 — real-time accuracy required for dispatch board

import { apiClient } from "@pilot/shared-api";
import { useQuery } from "@tanstack/react-query";

export function useJobAssignments(jobId: string | undefined) {
  return useQuery({
    queryKey: ["job-assignments", jobId],
    queryFn: async () => {
      const resp = await apiClient.get(
        `/api/v1/scheduling/jobs/${jobId}/assignments`
      );
      return resp.data as any[]; // adjust type after pnpm sync-api-types
    },
    enabled: !!jobId,
    staleTime: 0,
  });
}
```

---

## Step 3 — Create `useAddJobAssignment` Mutation

**File**: `apps/web/src/features/jobs/hooks/useAddJobAssignment.ts`

```typescript
// POST /api/v1/scheduling/jobs/{jobId}/assignments
// Body: { user_id, role, ordinal? }
// On success: invalidate ['job-assignments', jobId]

import { apiClient } from "@pilot/shared-api";
import { useMutation, useQueryClient } from "@tanstack/react-query";

export function useAddJobAssignment(jobId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      user_id: string;
      role: "primary" | "helper";
      ordinal?: number;
    }) => {
      const resp = await apiClient.post(
        `/api/v1/scheduling/jobs/${jobId}/assignments`,
        payload
      );
      return resp.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["job-assignments", jobId] });
    },
  });
}
```

---

## Step 4 — Create `useRemoveJobAssignment` Mutation

**File**: `apps/web/src/features/jobs/hooks/useRemoveJobAssignment.ts`

```typescript
// DELETE /api/v1/scheduling/jobs/{jobId}/assignments/{assignmentId}
// On success: invalidate ['job-assignments', jobId]

import { apiClient } from "@pilot/shared-api";
import { useMutation, useQueryClient } from "@tanstack/react-query";

export function useRemoveJobAssignment(jobId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (assignmentId: string) => {
      await apiClient.delete(
        `/api/v1/scheduling/jobs/${jobId}/assignments/${assignmentId}`
      );
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["job-assignments", jobId] });
    },
  });
}
```

**Intermediate verification:**
```bash
cd <repo>/frontend
pnpm --filter web test -- --testPathPattern="useJobAssignments|useTenantUsers" 2>&1 | tail -8
```

---

## Step 5 — Create `TechAssignmentSection` Component

**File**: `apps/web/src/features/jobs/components/TechAssignmentSection.tsx`

This is the shared component used in both surfaces. Read `packages/ui/src/index.ts` first to confirm exact import paths.

```typescript
"use client";
// Read the file first — adjust imports to match what you find in packages/ui/src/index.ts
import { LoadingState, ErrorState, RoleGate } from "@pilot/ui";
import { useJobAssignments } from "../hooks/useJobAssignments";
import { useAddJobAssignment } from "../hooks/useAddJobAssignment";
import { useRemoveJobAssignment } from "../hooks/useRemoveJobAssignment";
import { useTenantUsers } from "../../users/hooks/useTenantUsers";

interface TechAssignmentSectionProps {
  jobId: string;
  onAssignmentChanged?: () => void;
}

export function TechAssignmentSection({
  jobId,
  onAssignmentChanged,
}: TechAssignmentSectionProps) {
  // 1. Fetch current assignments
  const { data: assignments = [], isLoading, isError, refetch } = useJobAssignments(jobId);
  // 2. Fetch all tenant users (for picker dropdown)
  const { data: allUsers = [] } = useTenantUsers();
  // 3. Mutations
  const addMutation = useAddJobAssignment(jobId);
  const removeMutation = useRemoveJobAssignment(jobId);

  // Already-assigned user IDs (for filtering picker)
  const assignedUserIds = new Set(assignments.map((a: any) => a.user_id));

  // Available users = active users not already assigned
  const availableUsers = allUsers.filter(
    (u) => u.is_active && !assignedUserIds.has(u.user_id)
  );

  // Role auto-computation: first tech = primary, subsequent = helper
  const nextRole = assignments.length === 0 ? "primary" : "helper";

  const handleAdd = async (userId: string) => {
    await addMutation.mutateAsync({ user_id: userId, role: nextRole });
    await refetch();
    onAssignmentChanged?.();
  };

  const handleRemove = async (assignmentId: string) => {
    await removeMutation.mutateAsync(assignmentId);
    await refetch();
    onAssignmentChanged?.();
  };

  if (isLoading) return <LoadingState />;
  if (isError) return <ErrorState message="Failed to load technicians" />;

  return (
    <div className="space-y-2">
      <h4 className="text-sm font-semibold text-neutral-700">Technicians</h4>
      
      {assignments.length === 0 && (
        <p className="text-sm text-neutral-400">No technician assigned.</p>
      )}

      {assignments.map((assignment: any) => {
        const user = allUsers.find((u) => u.user_id === assignment.user_id);
        const isPrimary = assignment.role === "primary";
        const color = user?.display_color ?? "#6B7280"; // gray fallback
        const name = user?.display_name ?? assignment.user_id;

        return (
          <div key={assignment.id} className="flex items-center gap-2">
            {/* Colored avatar */}
            <span
              className="w-6 h-6 rounded-full flex items-center justify-center text-white text-xs font-bold"
              style={{ backgroundColor: color }}
            >
              {name.charAt(0).toUpperCase()}
            </span>
            <span className="text-sm text-neutral-800 flex-1">{name}</span>
            {isPrimary && (
              <span className="text-xs text-brand-600 font-medium">Lead</span>
            )}
            <RoleGate permission="schedule.manage">
              <button
                onClick={() => handleRemove(assignment.id)}
                className="text-neutral-400 hover:text-fault-600 text-xs px-1"
                aria-label={`Remove ${name}`}
                disabled={removeMutation.isPending}
              >
                ✕
              </button>
            </RoleGate>
          </div>
        );
      })}

      <RoleGate permission="schedule.manage">
        {availableUsers.length > 0 && (
          <div className="mt-2">
            <select
              className="text-sm border border-neutral-200 rounded px-2 py-1 text-neutral-600 w-full"
              value=""
              onChange={(e) => {
                if (e.target.value) handleAdd(e.target.value);
              }}
              disabled={addMutation.isPending}
            >
              <option value="">+ Add technician</option>
              {availableUsers.map((u) => (
                <option key={u.user_id} value={u.user_id}>
                  {u.display_name}
                </option>
              ))}
            </select>
          </div>
        )}
      </RoleGate>
    </div>
  );
}
```

> **Read the file first** for both surfaces before wiring. Adjust styling tokens to match what's used in the surrounding files (use `grep -n "className=" JobPropertiesPanel.tsx | head -20` to see the token vocabulary in use).

**Intermediate verification:**
```bash
pnpm --filter web test -- --testPathPattern="TechAssignmentSection" 2>&1 | tail -8
```

---

## Step 6 — Wire into `JobPropertiesPanel.tsx`

**File**: `apps/web/src/features/dispatch-board/components/JobPropertiesPanel.tsx`

Read the file first. Find the existing tech display block (~lines 395–439) — it shows a single tech's avatar and a dead `+ Add technician` button with no `onClick`.

Replace that entire block with:

```tsx
<TechAssignmentSection
  jobId={job.id}
  onAssignmentChanged={onJobUpdated}
/>
```

Import `TechAssignmentSection` at the top of the file.

> Identify the exact prop name for the job update callback (it may be `onJobUpdated`, `onRefresh`, or similar — read the component's props interface). Pass it as `onAssignmentChanged`.

---

## Step 7 — Wire into `JobDetailPage.tsx`

**File**: `apps/web/src/features/jobs/components/JobDetailPage.tsx`

Read the file first. Find `<JobDetailHeader>` and `<JobProfitabilityWidget>` (or equivalent). Insert `<TechAssignmentSection>` between them — below the header, above the profitability widget:

```tsx
<JobDetailHeader jobId={jobId} ... />

{/* Tech assignment — always visible, not in a tab */}
<div className="px-4 py-3 border-b border-neutral-100">
  <TechAssignmentSection jobId={jobId} />
</div>

<JobProfitabilityWidget ... />
```

> Read the file to find the correct `jobId` variable name. It may come from a route param, a prop, or a hook. Adjust accordingly.

---

## Step 8 — Create MSW Handlers

**File**: `apps/web/src/mocks/handlers/assignmentHandlers.ts`

```typescript
import { http, HttpResponse } from "msw";

const MOCK_ASSIGNMENTS = [
  {
    id: "assign-001",
    job_id: "job-001",
    user_id: "user-003",
    role: "primary",
    ordinal: 1,
    assigned_at: "2026-07-21T10:00:00Z",
    is_active: true,
  },
];

export const assignmentHandlers = [
  http.get("/api/v1/scheduling/jobs/:jobId/assignments", ({ params }) => {
    return HttpResponse.json(
      MOCK_ASSIGNMENTS.filter((a) => a.job_id === params.jobId || true)
    );
  }),
  http.post("/api/v1/scheduling/jobs/:jobId/assignments", async ({ request }) => {
    const body = (await request.json()) as any;
    return HttpResponse.json(
      { id: "assign-new", job_id: "job-001", ...body, is_active: true },
      { status: 201 }
    );
  }),
  http.delete(
    "/api/v1/scheduling/jobs/:jobId/assignments/:assignmentId",
    () => HttpResponse.json({}, { status: 200 })
  ),
];
```

**File**: `apps/web/src/mocks/handlers/userHandlers.ts` — create or update to include name fields:

```typescript
// Ensure GET /api/v1/users handler returns first_name, last_name, display_color
// Check if this handler already exists; if so, add the new fields to the fixture
```

**Register both in `index.ts`**:
```typescript
// apps/web/src/mocks/handlers/index.ts
// Read the file first, then add:
import { assignmentHandlers } from "./assignmentHandlers";
// Add ...assignmentHandlers to the handlers array
```

---

## Step 9 — Write Tests

### Unit tests (co-located)

**`features/jobs/hooks/__tests__/useJobAssignments.test.ts`** — min 3 tests:
- calls correct endpoint with jobId
- returns data from API
- disabled when jobId is undefined

**`features/jobs/hooks/__tests__/useAddJobAssignment.test.ts`** — min 2 tests:
- fires POST with correct body
- invalidates job-assignments query on success

**`features/jobs/hooks/__tests__/useTenantUsers.test.ts`** — min 3 tests:
- calls GET /api/v1/users
- computes display_name from first+last name
- falls back to email when names are null

**`features/jobs/components/__tests__/TechAssignmentSection.test.tsx`** — min 5 tests:
- renders "No technician assigned" when assignments empty
- renders tech name + Lead badge for primary assignment
- "✕ remove" button visible with schedule.manage role
- "✕ remove" button hidden for tech role (RoleGate)
- "+ Add technician" dropdown hidden when no available users remain

### Integration tests

**`apps/web/src/__tests__/batch_ui_fix_2b/tech_assignment.integration.test.tsx`** — min 4 tests:
- dispatch board Properties panel renders TechAssignmentSection (no more dead button)
- Job Detail page renders TechAssignmentSection above profitability widget
- Add tech: POST fires with correct payload; list re-fetches
- Remove tech: DELETE fires with correct assignmentId; list re-fetches

Use TanStack Query `retry: false` in all test QueryClients. Use MSW at HTTP level — never mock `apiClient`. Use `vi.mock("next/navigation", ...)` for any component using router.

---

## Final Verification

### Phase 1 — Targeted tests

```bash
cd <repo>/frontend
pnpm --filter web test -- --testPathPattern="TechAssignment|useJobAssignment|useTenantUser|batch_ui_fix_2b" 2>&1 | tail -10
```

Fix any failures before Phase 2.

### Phase 2 — Full verification

```bash
cd <repo>/frontend && echo "=== UI - Type Check ===" && pnpm --filter @pilot/ui check-types && echo "=== Web - Type Check ===" && pnpm --filter web check-types && echo "=== Mobile - Type Check ===" && pnpm --filter mobile build && echo "=== UI - Lint ===" && pnpm --filter @pilot/ui lint && echo "=== Web - Lint ===" && pnpm --filter web lint && echo "=== Mobile - Lint ===" && pnpm --filter mobile lint && echo "=== TYPE+LINT PASS ===" && echo "=== UI - Tests ===" && pnpm --filter @pilot/ui test 2>&1 | tail -6 && echo "=== Web - Tests ===" && pnpm --filter web test 2>&1 | tail -6 && echo "=== Mobile - Tests ===" && pnpm --filter mobile test 2>&1 | tail -8 && echo "=== MVP FINAL VERIFICATION COMPLETE ==="
```

---

## Definition of Done — UI-FIX-2B React Engineer

- [ ] Pre-modification regression baseline captured (zero pre-existing failures, or confirmed with Tom)
- [ ] `pnpm sync-api-types` run — `first_name`, `last_name`, `display_color` visible on `TenantUserWithRoleResponse` in shared-types
- [ ] Design doc fully read before writing any code
- [ ] All mandatory source files read before modifying (`JobPropertiesPanel.tsx`, `JobDetailPage.tsx`, `permissions.ts`, `mocks/handlers/index.ts`)
- [ ] All 4 endpoints verified in `openapi_schema_map.md` (including new fields on users endpoint)
- [ ] **STEP 1**: `useTenantUsers.ts` created — calls `GET /api/v1/users`, computes `display_name`
- [ ] **STEP 2**: `useJobAssignments.ts` created — calls `GET .../assignments`, `staleTime: 0`
- [ ] **STEP 3**: `useAddJobAssignment.ts` created — POST mutation, invalidates on success
- [ ] **STEP 4**: `useRemoveJobAssignment.ts` created — DELETE mutation, invalidates on success
- [ ] **STEP 5**: `TechAssignmentSection.tsx` created — renders list, inline picker, colored avatar, Lead badge, RoleGate on add/remove
- [ ] **STEP 6**: `JobPropertiesPanel.tsx` updated — dead single-tech block replaced with `<TechAssignmentSection>`
- [ ] **STEP 7**: `JobDetailPage.tsx` updated — `<TechAssignmentSection>` added below header, above profitability widget
- [ ] **STEP 8**: `assignmentHandlers.ts` created; user handler updated with name fields; both registered in `mocks/handlers/index.ts`
- [ ] `<RoleGate permission="schedule.manage">` wraps add and remove controls
- [ ] Role auto-computation: first addition = `primary`, subsequent = `helper`
- [ ] Re-fetch (not optimistic update) used after every add/remove
- [ ] `onAssignmentChanged?.()` called after every add/remove in Properties panel
- [ ] All new MSW handler files registered in `mocks/handlers/index.ts`
- [ ] Unit tests pass (targeted run)
- [ ] Integration tests pass in `__tests__/batch_ui_fix_2b/`
- [ ] Zero TypeScript errors (`check-types` passes)
- [ ] Zero ESLint `no-hardcoded-design-values` warnings
- [ ] **Phase 2 FULL verification command passes** (`=== MVP FINAL VERIFICATION COMPLETE ===`):
  ```bash
  cd <repo>/frontend && echo "=== UI - Type Check ===" && pnpm --filter @pilot/ui check-types && echo "=== Web - Type Check ===" && pnpm --filter web check-types && echo "=== Mobile - Type Check ===" && pnpm --filter mobile build && echo "=== UI - Lint ===" && pnpm --filter @pilot/ui lint && echo "=== Web - Lint ===" && pnpm --filter web lint && echo "=== Mobile - Lint ===" && pnpm --filter mobile lint && echo "=== TYPE+LINT PASS ===" && echo "=== UI - Tests ===" && pnpm --filter @pilot/ui test 2>&1 | tail -6 && echo "=== Web - Tests ===" && pnpm --filter web test 2>&1 | tail -6 && echo "=== Mobile - Tests ===" && pnpm --filter mobile test 2>&1 | tail -8 && echo "=== MVP FINAL VERIFICATION COMPLETE ==="
  ```
- [ ] Final test count (before → after) documented
- [ ] Completion Summary added to `ui-fix-2-decisions.md` under UI-FIX-2B React Engineer row

---

## Completion Summary

After all Definition of Done items are complete:

1. Add a **Completion Summary** to `dev-docs/architecture-design/batch-designs/ui-fix-2-decisions.md` under the UI-FIX-2B batch section (React Engineer row):

```markdown
### UI-FIX-2B (React Engineer) — TechAssignmentSection on Dispatch Board + Job Detail: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot React Engineer
**Baseline**: X passed (web)
**Final**: X+N passed (+N new tests)

#### What Was Accomplished

- Created TechAssignmentSection component: colored avatar list, Lead badge, ✕ remove, + Add picker, RoleGate
- Created 4 hooks: useTenantUsers, useJobAssignments, useAddJobAssignment, useRemoveJobAssignment
- Wired TechAssignmentSection into JobPropertiesPanel (replaced dead single-tech block)
- Wired TechAssignmentSection into JobDetailPage (below header, above profitability widget)
- MSW handlers created for assignments GET/POST/DELETE; user handler updated with name fields

#### Files Changed / Created

| File | Action |
|---|---|
| `apps/web/src/features/users/hooks/useTenantUsers.ts` | Created |
| `apps/web/src/features/jobs/hooks/useJobAssignments.ts` | Created |
| `apps/web/src/features/jobs/hooks/useAddJobAssignment.ts` | Created |
| `apps/web/src/features/jobs/hooks/useRemoveJobAssignment.ts` | Created |
| `apps/web/src/features/jobs/components/TechAssignmentSection.tsx` | Created |
| `apps/web/src/features/dispatch-board/components/JobPropertiesPanel.tsx` | Updated |
| `apps/web/src/features/jobs/components/JobDetailPage.tsx` | Updated |
| `apps/web/src/mocks/handlers/assignmentHandlers.ts` | Created |
| `apps/web/src/mocks/handlers/userHandlers.ts` | Created/Updated |
| `apps/web/src/mocks/handlers/index.ts` | Updated |

#### Tests Added

| Test File | Type | Tests | All Pass |
|---|---|---|---|
| `features/jobs/hooks/__tests__/useJobAssignments.test.ts` | Unit | N | ✅ |
| `features/jobs/hooks/__tests__/useTenantUsers.test.ts` | Unit | N | ✅ |
| `features/jobs/components/__tests__/TechAssignmentSection.test.tsx` | Unit | N | ✅ |
| `__tests__/batch_ui_fix_2b/tech_assignment.integration.test.tsx` | Integration | N | ✅ |
```

2. Update `dev-docs/analysis/pilot-launch-plan.md` — UI-FIX-2B row: change Status to `✅ Complete — YYYY-MM-DD`.
