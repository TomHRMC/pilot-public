# Batch Design: UI-FIX-2B — Multi-Tech Assignment on Dispatch Board + Job Detail

**Source decisions**: `dev-docs/architecture-design/batch-designs/ui-fix-2-decisions.md § FIX-015`  
**Batch type**: Mixed — Backend (Python Engineer first) + Frontend (React Engineer second)  
**Estimated effort**: ~2–3h BE + ~3–4h FE = ~5–7h total  
**Depends on**: UI-FIX-2A ✅ Complete — `job_assignment` legacy table dropped; seed targets correct table  
**Status**: ⏳ Pending

---

## A. Input Read Summary

| Input | Key finding |
|---|---|
| `ui-fix-2-decisions.md § FIX-015` | Full root cause, UX spec, code change list — fully resolved |
| MCP: `user` table (2026-07-21) | `first_name varchar(YES)`, `last_name varchar(YES)`, `display_color varchar(YES)` — all present, no migration needed |
| MCP: `job_tech_assignment` table (2026-07-21) | All columns present: `id`, `tenant_id`, `job_id`, `user_id`, `assigned_by_user_id`, `role text DEFAULT 'primary'`, `ordinal int DEFAULT 1`, `assigned_at timestamptz`, `is_active bool`, `version int` — no migration needed |
| `backend/api/schemas/roles.py` | `TenantUserWithRoleResponse` confirmed: `user_id`, `email`, `role_code`, `role_name`, `permissions`, `joined_at`, `is_active` — missing `first_name`, `last_name`, `display_color` |
| `backend/api/routes/roles.py` | `_list_tenant_users_impl()` already JOINs `User` model — `first_name`, `last_name`, `display_color` available in result set but not mapped to Pydantic schema |
| OpenAPI confirmed | `POST /api/v1/scheduling/jobs/{job_id}/assignments`, `GET /api/v1/scheduling/jobs/{job_id}/assignments`, `DELETE /api/v1/scheduling/jobs/{job_id}/assignments/{assignment_id}`, `GET /api/v1/users` all exist |

---

## B. Migration Plan

**No Alembic migration required.** All required columns are confirmed present in the live DB:

- `user.first_name`, `user.last_name`, `user.display_color` — exist, nullable
- `job_tech_assignment.role`, `ordinal`, `assigned_by_user_id`, `assigned_at`, `version` — exist with correct defaults

This batch is a **schema extension only** — adding 3 fields to an existing Pydantic response class and mapping them from an already-available JOIN.

**MCP pre-work verification queries for the Python Engineer:**

```sql
-- 1. Confirm user name + color columns exist
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'user'
  AND column_name IN ('first_name', 'last_name', 'display_color')
ORDER BY column_name;

-- 2. Confirm job_tech_assignment full column list
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'job_tech_assignment'
ORDER BY ordinal_position;

-- 3. Confirm roles.py endpoint handler table (verify JOIN exists)
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'tenant_user'
ORDER BY ordinal_position;

-- 4. Confirm current alembic head
SELECT version_num FROM public.alembic_version;
```

---

## C. Execution Order

| Step | What | File(s) | Engineer |
|---|---|---|---|
| 1 | Add `first_name`, `last_name`, `display_color` to `TenantUserWithRoleResponse` | `backend/api/schemas/roles.py` | Python |
| 2 | Map new fields from JOIN result in `_list_tenant_users_impl()` | `backend/api/routes/roles.py` | Python |
| 3 | Regenerate `openapi.json` + `openapi_schema_map.md` | `backend/export_openapi_json.py` | Python |
| 4 | Write BE unit test for new fields in `GET /api/v1/users` response | `backend/tests/domains/scheduling_dispatch/test_ui_fix_2b_tech_users.py` | Python |
| 5 | **Handoff**: Python Engineer runs `python export_openapi_json.py`, commits | — | Python |
| 6 | React Engineer runs `pnpm sync-api-types` | — | React |
| 7 | Create `useTenantUsers` hook | `apps/web/src/features/users/hooks/useTenantUsers.ts` | React |
| 8 | Create `useJobAssignments` hook | `apps/web/src/features/jobs/hooks/useJobAssignments.ts` | React |
| 9 | Create `useAddJobAssignment` mutation hook | `apps/web/src/features/jobs/hooks/useAddJobAssignment.ts` | React |
| 10 | Create `useRemoveJobAssignment` mutation hook | `apps/web/src/features/jobs/hooks/useRemoveJobAssignment.ts` | React |
| 11 | Create `TechAssignmentSection` component | `apps/web/src/features/jobs/components/TechAssignmentSection.tsx` | React |
| 12 | Wire into `JobPropertiesPanel.tsx` (Dispatch Board) | `apps/web/src/features/dispatch-board/components/JobPropertiesPanel.tsx` | React |
| 13 | Wire into `JobDetailPage.tsx` (Job Detail) | `apps/web/src/features/jobs/components/JobDetailPage.tsx` | React |
| 14 | Create MSW handlers + register in `index.ts` | `apps/web/src/mocks/handlers/assignmentHandlers.ts` | React |
| 15 | Write unit + integration tests | `__tests__/batch_ui_fix_2b/` | React |

---

## D. New API Endpoints

**No new endpoints.** All 4 endpoints already exist and are confirmed in `openapi.json`:

| Endpoint | Auth | RBAC | Purpose |
|---|---|---|---|
| `GET /api/v1/users` | JWT | `users.view` | List active tenant users — **being extended** to return `first_name`, `last_name`, `display_color` |
| `GET /api/v1/scheduling/jobs/{job_id}/assignments` | JWT | Any authenticated | Get all active assignments for a job |
| `POST /api/v1/scheduling/jobs/{job_id}/assignments` | JWT | `schedule.manage` | Add a tech to a job |
| `DELETE /api/v1/scheduling/jobs/{job_id}/assignments/{assignment_id}` | JWT | `schedule.manage` | Remove a tech assignment |

**Schema change to `GET /api/v1/users` response** (Python Engineer step 1–2):

`TenantUserWithRoleResponse` gains 3 new optional fields:

```python
# backend/api/schemas/roles.py — ADD to TenantUserWithRoleResponse:
first_name: str | None = Field(None, description="User's first name")
last_name: str | None = Field(None, description="User's last name")
display_color: str | None = Field(None, description="User's avatar color hex")
```

`_list_tenant_users_impl()` mapping in `backend/api/routes/roles.py` — ADD to `TenantUserWithRoleResponse(...)` constructor:

```python
first_name=user.first_name,
last_name=user.last_name,
display_color=user.display_color,
```

---

## E. Pattern Reuse Decisions

| Pattern | Applied How |
|---|---|
| `mvp-arch.md §16` — Optimistic UI | **Not used here** — real-time dispatch board accuracy requires immediate re-fetch after assignment change (no optimistic update) |
| `mvp-arch.md §16` — `<RoleGate>` | `+ Add technician` and `✕ remove` buttons wrapped in `<RoleGate permission="schedule.manage">` — owner/operator only; techs can see the list but cannot modify |
| `mvp-arch.md §16` — `<LoadingState>`, `<ErrorState>` | Used in `TechAssignmentSection` during assignment list fetch |
| `<RoleGate>` from `@pilot/ui` | Standard pattern — no custom role check inline |

---

## F. Shared Module Interfaces

### `TechAssignmentSection` component interface

```typescript
// apps/web/src/features/jobs/components/TechAssignmentSection.tsx
interface TechAssignmentSectionProps {
  jobId: string;
  onAssignmentChanged?: () => void; // called after any add/remove — used by dispatch board to refresh grid
}
```

### `useTenantUsers` hook

```typescript
// apps/web/src/features/users/hooks/useTenantUsers.ts
// GET /api/v1/users
interface TenantUserItem {
  user_id: string;
  email: string;
  first_name: string | null;
  last_name: string | null;
  display_color: string | null;
  role_code: string;
  is_active: boolean;
  display_name: string; // computed: `${first_name} ${last_name}`.trim() || email
}
```

### `useJobAssignments` hook

```typescript
// apps/web/src/features/jobs/hooks/useJobAssignments.ts
// GET /api/v1/scheduling/jobs/{jobId}/assignments
// Returns JobTechAssignmentResponse[] — already typed in shared-types after sync
// TanStack Query key: ['job-assignments', jobId]
// staleTime: 0 (real-time accuracy required)
```

### `useAddJobAssignment` mutation

```typescript
// apps/web/src/features/jobs/hooks/useAddJobAssignment.ts
// POST /api/v1/scheduling/jobs/{jobId}/assignments
// Body: { user_id: string, role: 'primary' | 'helper', ordinal?: number }
// On success: invalidate ['job-assignments', jobId]
```

### `useRemoveJobAssignment` mutation

```typescript
// apps/web/src/features/jobs/hooks/useRemoveJobAssignment.ts
// DELETE /api/v1/scheduling/jobs/{jobId}/assignments/{assignmentId}
// On success: invalidate ['job-assignments', jobId]
```

### Role assignment logic (computed inside `TechAssignmentSection`, not exposed in UI)

```typescript
// When user picks a tech from the dropdown:
const role = currentAssignments.length === 0 ? 'primary' : 'helper';
// No UI radio/toggle — role is auto-computed from current state
```

---

## G. Open Questions Resolved

| Question | Resolution |
|---|---|
| Should `JobEditModal.tsx` get tech assignment fields? | **No** — tech assignment is real-time (immediate POST/DELETE), no save-button flow needed. `JobEditModal` handles scheduled times, customer, site only. |
| Should primary/helper terminology be shown to the user? | **No** — MVP shows "Lead" badge only for the primary tech. The `role` field drives this display only. Users never see "primary"/"helper" labels. |
| What happens if the primary tech is removed but helpers remain? | **No automatic promotion in MVP** — leave helpers as helpers. Backend does not auto-promote. |
| Should `TechAssignmentSection` be in `packages/ui` (shared) or `apps/web` (web-only)? | **`apps/web` only** — no mobile requirement for this component in this batch. Mobile `CustomerDetailScreen` is already built (MOB-B3); tech assignment on mobile is not in scope. |
| What if `display_color` is null? | Fall back to a deterministic color derived from `user_id` (hash the UUID, pick from the 8 Pilot palette colors). The `TechAssignmentSection` handles this fallback internally. |
| Optimistic update or re-fetch? | **Re-fetch on success** — dispatch board real-time accuracy matters more than perceived speed. After any add/remove, call `refetch()` on the assignments query AND call `onAssignmentChanged?.()` to refresh the dispatch board grid. |

---

## H. Surface Mockup Reference

**Not a frontend-only batch** — UI Designer design spec not required. The UX is fully specified in `ui-fix-2-decisions.md § FIX-015 — Multi-Tech UX Design`.

```
Technicians
──────────────────────────────────────────
  🟢  John Smith      Lead      [✕]
  🔵  Maria Garcia              [✕]
  
  <RoleGate permission="schedule.manage">
    [+ Add technician ▾]
  </RoleGate>
──────────────────────────────────────────
```

**Placement:**
- **Dispatch Board Properties panel** (`JobPropertiesPanel.tsx`): replace the single-tech block + dead `+ Add technician` button (lines ~395–439)
- **Job Detail page** (`JobDetailPage.tsx`): add below `<JobDetailHeader>`, above `<JobProfitabilityWidget>` — always visible, not in a tab

---

## I. Component Manifest

| Component / Hook | Destination Path | Action |
|---|---|---|
| `TechAssignmentSection` | `apps/web/src/features/jobs/components/TechAssignmentSection.tsx` | **New** |
| `useTenantUsers` | `apps/web/src/features/users/hooks/useTenantUsers.ts` | **New** |
| `useJobAssignments` | `apps/web/src/features/jobs/hooks/useJobAssignments.ts` | **New** |
| `useAddJobAssignment` | `apps/web/src/features/jobs/hooks/useAddJobAssignment.ts` | **New** |
| `useRemoveJobAssignment` | `apps/web/src/features/jobs/hooks/useRemoveJobAssignment.ts` | **New** |
| `JobPropertiesPanel.tsx` | `apps/web/src/features/dispatch-board/components/JobPropertiesPanel.tsx` | **Update** — replace dead tech block |
| `JobDetailPage.tsx` | `apps/web/src/features/jobs/components/JobDetailPage.tsx` | **Update** — add `TechAssignmentSection` |
| `assignmentHandlers.ts` | `apps/web/src/mocks/handlers/assignmentHandlers.ts` | **New** — MSW |
| `userHandlers.ts` | `apps/web/src/mocks/handlers/userHandlers.ts` | **New or update** — add name/color fields |
| `mocks/handlers/index.ts` | `apps/web/src/mocks/handlers/index.ts` | **Update** — register new handlers |
