# Batch FE-B25 Design — Job Edit UI (useUpdateJob + JobDetailHeader Edit Form)

**Batch Code**: FE-B25  
**Type**: Frontend web only (`apps/web`)  
**Date**: 2026-07-10  
**Author**: Pilot Architect  
**Status**: Ready for implementation (after B18 and FE-B24 complete)  
**Priority**: P1 — owner workflow gap (🟡 important)  
**Backend companion**: B18 must complete first (`PATCH /api/v1/jobs/{job_id}` endpoint)  
**Source Issue**: `dev-docs/testing-support/alpha-testing/ui-testing-status-2026-07-10.md` — Issue #4

---

## A. Input Read Summary

| Input | What Was Verified |
|---|---|
| `ui-testing-status-2026-07-10.md` | Issue #4: No edit button/form in `JobDetailHeader.tsx`. Backend `PATCH /api/v1/jobs/{job_id}` does not exist (before B18). |
| B18 design doc | `PATCH /api/v1/jobs/{job_id}` — accepts `customer_id?`, `site_id?`, `scheduled_start_at?`, `scheduled_end_at?`, `estimated_duration_minutes?`. Returns `JobResponse`. |
| `backend/api/schemas/schemas.py` — `JobResponse` | Fields: `id`, `tenant_id`, `customer_id`, `site_id`, `status_id`, `scheduled_start_at?`, `scheduled_end_at?`, `estimated_duration_minutes?`, `actual_labor_cost_cents`, `actual_material_cost_cents`, `actual_profit_cents`, `is_active` |
| `frontend/react-engr-std-prompt-inclusions.md` | Read in full — all required prompt sections identified |
| FE-B24 design doc | `JobFormModal` is built in FE-B24 for Create. FE-B25 builds `JobEditModal` for edit, which is similar but pre-populated and calls PATCH instead of POST. |

---

## B. Migration Plan

**No Alembic migration.** Pure frontend batch.

---

## C. Execution Order

| Step | Task | Primary File(s) |
|---|---|---|
| 1 | `pnpm sync-api-types` — confirms `PATCH /api/v1/jobs/{job_id}` exists in openapi schema | — |
| 2 | Verify endpoint in `openapi_schema_map.md` | `backend/openapi_schema_map.md` |
| 3 | Create `useUpdateJob` hook | `features/jobs/hooks/useUpdateJob.ts` |
| 4 | Create `JobEditModal` component (pre-populated form, calls PATCH) | `features/jobs/components/JobEditModal.tsx` |
| 5 | Wire "Edit Job" button in `JobDetailPage` or `JobDetailHeader` → `JobEditModal` | `features/jobs/components/JobDetailPage.tsx` or `JobDetailHeader.tsx` |
| 6 | Extend job MSW handlers to include `PATCH /api/v1/jobs/:id` | `mocks/handlers/jobHandlers.ts` |
| 7 | Write unit + integration tests | `__tests__/batch_fe_b25/` |
| 8 | Phase 2 full verification | — |

---

## D. New API Endpoints

**`PATCH /api/v1/jobs/{job_id}`** — provided by B18. No new endpoints needed in this batch.

| Hook | Endpoint | Verified |
|---|---|---|
| `useUpdateJob` | `PATCH /api/v1/jobs/{job_id}` | ✅ After B18 + `pnpm sync-api-types` |

**Request payload** (all fields optional — send only what changed):

```typescript
interface JobUpdatePayload {
  customer_id?: string;
  site_id?: string;
  scheduled_start_at?: string; // ISO 8601
  scheduled_end_at?: string;   // ISO 8601
  estimated_duration_minutes?: number;
}
```

**Response**: `JobResponse` — same shape as GET /api/v1/jobs/{job_id}

---

## E. Pattern Reuse Decisions

| Pattern | Applied |
|---|---|
| TanStack Query `useMutation` + `invalidateQueries` | `useUpdateJob` — invalidates `['job', jobId]` and `['jobs']` on success |
| `retry: false` on QueryClient in tests | Required per react-engr inclusions §9 |
| MSW `PATCH` handler with `HttpResponse.json` | `jobHandlers.ts` |
| `<RoleGate permission="jobs.update">` | Edit button — owner and office staff only, not tech |
| Cascade-select (customer → site) | `JobEditModal` — same pattern as `JobFormModal` in FE-B24 |
| Pre-populate form from current job data | `JobEditModal` receives `currentJob: JobResponse` as prop |
| `apiClient` from `@pilot/shared-api` | All API calls |

---

## F. Shared Module Interfaces

### F1. `useUpdateJob` hook

```typescript
// features/jobs/hooks/useUpdateJob.ts
interface JobUpdatePayload {
  customer_id?: string;
  site_id?: string;
  scheduled_start_at?: string;
  scheduled_end_at?: string;
  estimated_duration_minutes?: number;
}

const useUpdateJob = (jobId: string) => useMutation({
  mutationFn: (payload: JobUpdatePayload) =>
    apiClient.patch(`/api/v1/jobs/${jobId}`, payload),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['job', jobId] });
    queryClient.invalidateQueries({ queryKey: ['jobs'] });
  },
});
```

### F2. `JobEditModal` component contract

```typescript
interface JobEditModalProps {
  open: boolean;
  onClose: () => void;
  jobId: string;
  currentJob: {
    customer_id: string;
    site_id: string;
    scheduled_start_at: string | null;
    scheduled_end_at: string | null;
    estimated_duration_minutes: number | null;
  };
  onSuccess?: (updatedJob: JobResponse) => void;
}
```

**Form behavior:**
- Customer dropdown: pre-selected to `currentJob.customer_id`
- Site dropdown: pre-selected to `currentJob.site_id`, filtered by customer
- `scheduled_start_at`: datetime picker, pre-populated
- `scheduled_end_at`: datetime picker, pre-populated
- `estimated_duration_minutes`: number input, pre-populated
- Submit: calls `useUpdateJob(jobId)` with only changed fields
- On success: closes modal, shows success toast, invalidates job detail

**Placement**: "Edit Job" button in `JobDetailPage` header area, gated by `<RoleGate permission="jobs.update">`.

---

## G. Open Questions Resolved

| Question | Resolution |
|---|---|
| Should `JobEditModal` allow changing `status_id`? | **No.** Per B18 design §G: status transitions go through the dispatch board. `status_id` is not in `JobUpdate`. |
| Should FE-B25 reuse `JobFormModal` from FE-B24? | **No — separate component.** `JobFormModal` (Create) is empty form. `JobEditModal` (Edit) is pre-populated and calls PATCH. They share structure but have different props and behavior. Could share a base form component internally but keep the modals separate for clarity. |
| Where does the "Edit Job" button go? | In `JobDetailPage.tsx` header section. Read the actual file before deciding exact placement — `JobDetailHeader.tsx` may be a sub-component. |
| What happens when the customer is changed? Does it affect related invoices? | The PATCH only updates the job record. Invoices linked to the job still reference the old customer. This is an acceptable MVP limitation — noted in the UI with an info tooltip if needed. |

---

## H. Surface Mockup Reference

No dedicated UI designer pass — this is CRUD completion work using existing design patterns.

| Surface | Platform | Description |
|---|---|---|
| `JobEditModal` | Web only | Pre-populated modal matching `JobFormModal` structure; "Edit Job" label; PATCH on submit |
| "Edit Job" button in `JobDetailPage` | Web only | Gated by `jobs.update` permission; opens `JobEditModal` |

---

## I. Component Manifest

| Component | Destination Path | Type |
|---|---|---|
| `useUpdateJob` | `apps/web/src/features/jobs/hooks/useUpdateJob.ts` | New |
| `JobEditModal` | `apps/web/src/features/jobs/components/JobEditModal.tsx` | New |
| `jobHandlers.ts` (PATCH extension) | `apps/web/src/mocks/handlers/jobHandlers.ts` | Extend existing (from FE-B24) |

> **Sequencing note**: FE-B25 runs after FE-B24 because FE-B24 creates `jobHandlers.ts`. FE-B25 extends that file with the PATCH handler.
