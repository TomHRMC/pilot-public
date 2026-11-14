# Implementation Prompt: FE-B25 — Job Edit UI (useUpdateJob + JobEditModal)

**Mode**: Pilot React Engineer  
**Batch**: FE-B25  
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §Integration & UI Hardening  
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-fe-b25-design.md`  
**Estimated session**: 2–3 hours  
**Platform**: Web only (`apps/web`)  
**Backend companion**: B18 must complete first (`PATCH /api/v1/jobs/{job_id}` endpoint)  
**Prerequisite batch**: FE-B24 must complete first (creates `jobHandlers.ts` that FE-B25 extends)

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-react-engineer/react-engineer-rules.md`** — in full
- **`dev-docs/architecture-design/batch-designs/batch-fe-b25-design.md`** — every section (A–I)

**Critical rules for this batch:**

- **Rule 1.1**: Before writing ANY hook or API call, verify `PATCH /api/v1/jobs/{job_id}` exists in `backend/openapi_schema_map.md`. If NOT there → **STOP and wait for B18**.
- **Rule 1.2**: Do NOT invent URL patterns or parameter names. Every shape comes from `openapi.json` or the design doc.
- **Rule 1.3**: Run `pnpm sync-api-types` before starting.
- **Rule 2**: All API calls use `apiClient` from `@pilot/shared-api`. `fetch()` is permanently banned for `/api/v1/...` calls.
- **Rule 7**: Check `packages/ui/src/index.ts` before creating any new component.
- **Rule 8**: No new npm dependencies without checking `package.json` first.
- **Rule 10**: If ANY test fails during your work — fix it before declaring the batch done.

---

## Design Decisions (Do Not Re-Litigate)

| Decision | Outcome | Rationale |
|---|---|---|
| `JobEditModal` vs reuse `JobFormModal` | **Separate component** — pre-populated, calls PATCH | Create and Edit have different prop shapes and API calls |
| `status_id` in edit form | **Excluded** — not in `JobUpdate` | Status transitions go through dispatch board |
| `quote_id` in edit form | **Excluded** — not in `JobUpdate` | Quote linkage set at job creation |
| `jobHandlers.ts` | **Extend from FE-B24** — add PATCH handler | FE-B24 created the file; FE-B25 adds PATCH to it |

---

## Pre-Work: Establish Regression Baseline

Before touching any file:

```bash
cd <repo>/frontend
pnpm --filter web test 2>&1 | tail -5
```

Record exact count. Fix any pre-existing failures before starting.

---

## Pre-Work: Sync API Types

```bash
cd <repo>/frontend
pnpm sync-api-types
```

Verify the PATCH endpoint type is now available:
```bash
grep -i "JobUpdate\|job.*patch" frontend/packages/shared-types/src/api-schema.d.ts | head -10
```

> **If `pnpm sync-api-types` fails** because B18 is not deployed → STOP and wait for B18.

---

## Pre-Work: Verify Endpoints

```bash
grep -A 5 "PATCH.*jobs.*{job_id}" backend/openapi_schema_map.md
```

**Verified endpoint for this batch:**

| Hook | Endpoint | Verified |
|---|---|---|
| `useUpdateJob` | `PATCH /api/v1/jobs/{job_id}` | Must confirm in openapi_schema_map.md |

**If this endpoint is NOT found → STOP. Do not invent a URL. Wait for B18 to complete.**

Also confirm FE-B24 completed successfully:
```bash
find frontend/apps/web/src/mocks/handlers -name "jobHandlers*" | head -3
find frontend/apps/web/src/features/jobs/components -name "JobFormModal*" | head -3
```

Both must exist. If not → complete FE-B24 first.

---

## Pre-Work: Read These Source Files

Read each with `read_file` before writing any code:

```
frontend/apps/web/src/features/jobs/components/JobDetailPage.tsx     ← find where to add "Edit Job" button
frontend/apps/web/src/features/jobs/components/JobFormModal.tsx       ← read the Create modal for pattern reference
frontend/apps/web/src/features/jobs/hooks/useCreateJob.ts             ← pattern reference for useUpdateJob
frontend/apps/web/src/features/jobs/hooks/                            ← find all existing job hooks (use find)
frontend/packages/ui/src/index.ts                                     ← confirm shared component paths
frontend/apps/web/src/mocks/handlers/jobHandlers.ts                   ← read before extending (FE-B24 created this)
frontend/apps/web/src/mocks/handlers/index.ts                         ← confirm jobHandlers already registered
```

Also run:
```bash
find frontend/apps/web/src/features/jobs -name "*.tsx" | head -15
find frontend/apps/web/src/features/jobs/hooks -name "*.ts" | head -10
```

---

## Context: What This Batch Does

| Step | Description | File |
|---|---|---|
| 1 | `useUpdateJob` hook | `features/jobs/hooks/useUpdateJob.ts` (new) |
| 2 | `JobEditModal` — pre-populated form, calls PATCH | `features/jobs/components/JobEditModal.tsx` (new) |
| 3 | Wire "Edit Job" button in `JobDetailPage` | modify `features/jobs/components/JobDetailPage.tsx` |
| 4 | Extend `jobHandlers.ts` with PATCH handler | modify `mocks/handlers/jobHandlers.ts` |
| 5 | Tests | `__tests__/batch_fe_b25/` |

---

## STEP 1 — Create `useUpdateJob` hook

**File**: `frontend/apps/web/src/features/jobs/hooks/useUpdateJob.ts`

Read `useCreateJob.ts` (from FE-B24) for the established pattern before writing.

```typescript
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";

interface JobUpdatePayload {
  customer_id?: string;
  site_id?: string;
  scheduled_start_at?: string; // ISO 8601
  scheduled_end_at?: string;   // ISO 8601
  estimated_duration_minutes?: number;
}

export function useUpdateJob(jobId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: JobUpdatePayload) =>
      apiClient.patch(`/api/v1/jobs/${jobId}`, payload).then((r) => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["job", jobId] });
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
    },
  });
}
```

> **Adjust the `apiClient` import path** by checking `packages/shared-api/src/index.ts` for the exact export name.

Run targeted test after this step:
```bash
pnpm --filter web test -- features/jobs 2>&1 | tail -8
```

---

## STEP 2 — Create `JobEditModal` component

**File**: `frontend/apps/web/src/features/jobs/components/JobEditModal.tsx`

Read `JobFormModal.tsx` (from FE-B24) for the established modal + customer/site cascade pattern before writing.

**`JobEditModal` differs from `JobFormModal` in these ways:**
- Props include `currentJob` (the existing job data for pre-population)
- Form inputs are pre-populated with current values
- Submit calls `useUpdateJob(jobId)` with only changed fields (partial PATCH semantics)
- Modal title: "Edit Job" instead of "Add Job"
- Submit button: "Save Changes" instead of "Create Job"

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
  onSuccess?: () => void;
}
```

**Key behaviors:**
- Customer dropdown: `GET /api/v1/customers/` — pre-selected to `currentJob.customer_id`
- Site dropdown: `GET /api/v1/sites/?customer_id={id}` — pre-selected to `currentJob.site_id`, filtered by selected customer
- When customer changes → reset site selection (user must re-select)
- `scheduled_start_at`: datetime-local input, pre-populated from `currentJob.scheduled_start_at`
- `scheduled_end_at`: datetime-local input, pre-populated from `currentJob.scheduled_end_at`
- `estimated_duration_minutes`: number input, pre-populated
- Submit: sends only the fields the user changed. Build a partial payload — compare current form values to `currentJob` props, only include changed values
- On success: call `onSuccess()`, close modal
- On error: display API error message in form
- `<LoadingState>` while customers/sites load

> **Code examples are starting points, not gospel.** Read `JobFormModal.tsx` first and adjust prop names, import paths, and state patterns to match what you actually find.

---

## STEP 3 — Wire "Edit Job" button in `JobDetailPage`

Read `JobDetailPage.tsx` (and any `JobDetailHeader.tsx` it may use) before modifying. Find the job detail header area.

Add:
```typescript
const [editOpen, setEditOpen] = useState(false);

// In the header section:
<RoleGate permission="jobs.update">
  <button onClick={() => setEditOpen(true)}>Edit Job</button>
</RoleGate>

<JobEditModal
  open={editOpen}
  onClose={() => setEditOpen(false)}
  jobId={job.id}
  currentJob={{
    customer_id: job.customer_id,
    site_id: job.site_id,
    scheduled_start_at: job.scheduled_start_at,
    scheduled_end_at: job.scheduled_end_at,
    estimated_duration_minutes: job.estimated_duration_minutes,
  }}
  onSuccess={() => setEditOpen(false)}
/>
```

Use the actual button/styling patterns from the existing `JobDetailPage` — match whatever pattern other action buttons use (e.g., the "Add Time Entry" or other header buttons).

---

## STEP 4 — Extend `jobHandlers.ts` with PATCH handler

Read `mocks/handlers/jobHandlers.ts` (created in FE-B24) before modifying. Add the PATCH handler:

```typescript
// Add to existing jobHandlers array in jobHandlers.ts:
http.patch("/api/v1/jobs/:jobId", async ({ request, params }) => {
  const body = (await request.json()) as any;
  return HttpResponse.json({
    id: params.jobId,
    tenant_id: "mock-tenant-id",
    customer_id: body.customer_id ?? "mock-customer-id",
    site_id: body.site_id ?? "mock-site-id",
    status_id: "mock-status-id",
    scheduled_start_at: body.scheduled_start_at ?? "2026-09-01T09:00:00Z",
    scheduled_end_at: body.scheduled_end_at ?? "2026-09-01T17:00:00Z",
    estimated_duration_minutes: body.estimated_duration_minutes ?? 480,
    actual_labor_cost_cents: 0,
    actual_material_cost_cents: 0,
    actual_profit_cents: 0,
    is_active: true,
  });
}),
```

> **Check `index.ts`** — `jobHandlers` should already be registered from FE-B24. You do NOT need to re-register; only verify it's there.

---

## Test Implementation

### Integration tests in `apps/web/src/__tests__/batch_fe_b25/`

**File**: `job_edit.integration.test.tsx`

```typescript
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import { describe, it, expect, beforeAll, afterEach, afterAll, vi } from "vitest";
import React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

// Mock Next.js navigation
vi.mock("next/navigation", () => ({
  usePathname: () => "/jobs/mock-job-id",
  useRouter: () => ({ push: vi.fn(), back: vi.fn() }),
}));

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}
```

**Minimum test scenarios:**

1. `"Edit Job" button renders for owner role` — `<RoleGate>` allows `owner`
2. `"Edit Job" button is NOT visible for tech role` — `<RoleGate>` blocks `tech`
3. `JobEditModal opens when button clicked` — modal renders with pre-populated fields
4. `Submit fires PATCH /api/v1/jobs/{id}` — mutation called with correct payload
5. `Modal closes on success` — `onSuccess` callback fires after PATCH 200

---

## Final Verification

### Phase 1 — Targeted tests (run after each step)

```bash
cd <repo>/frontend
pnpm --filter web test 2>&1 | tail -6
```

### Phase 2 — Full verification (run once at the end)

```bash
cd <repo>/frontend && pnpm --filter @pilot/ui check-types && pnpm --filter web check-types && pnpm --filter mobile build && pnpm --filter @pilot/ui lint && pnpm --filter web lint && pnpm --filter mobile lint && echo "=== TYPE+LINT PASS ===" && pnpm --filter @pilot/ui test 2>&1 | tail -6 && pnpm --filter web test 2>&1 | tail -6 && pnpm --filter mobile test 2>&1 | tail -8 && echo "=== MVP FINAL VERIFICATION COMPLETE ==="
```

---

## Definition of Done — FE-B25

Update `dev-docs/analysis/pilot-launch-plan.md` when each item is done:

- [ ] Pre-modification regression baseline captured (zero pre-existing failures, or confirmed with Tom)
- [ ] B18 confirmed complete — `PATCH /api/v1/jobs/{job_id}` visible in `openapi_schema_map.md`
- [ ] FE-B24 confirmed complete — `jobHandlers.ts` exists and is registered in `index.ts`
- [ ] `pnpm sync-api-types` run — `JobUpdate` / PATCH type visible in shared types
- [ ] Design doc read before writing any code
- [ ] All mandatory source files read before modifying (`JobDetailPage.tsx`, `JobFormModal.tsx`, `jobHandlers.ts`)
- [ ] `PATCH /api/v1/jobs/{job_id}` verified in `openapi_schema_map.md`
- [ ] **STEP 1**: `useUpdateJob.ts` created — calls PATCH, invalidates `['job', jobId]` + `['jobs']`
- [ ] **STEP 2**: `JobEditModal.tsx` created — pre-populated, customer/site cascade, calls `useUpdateJob`
- [ ] **STEP 3**: "Edit Job" button wired in `JobDetailPage` with `<RoleGate permission="jobs.update">`
- [ ] **STEP 4**: `jobHandlers.ts` extended with PATCH handler (no re-registration needed in `index.ts`)
- [ ] Integration tests in `__tests__/batch_fe_b25/job_edit.integration.test.tsx` pass (min 5 tests)
- [ ] Zero TypeScript errors (`pnpm --filter web check-types`)
- [ ] Zero ESLint warnings
- [ ] No regressions in pre-existing web test suite
- [ ] **Phase 2 FULL verification command passes** (`=== MVP FINAL VERIFICATION COMPLETE ===`):
  ```bash
  cd <repo>/frontend && pnpm --filter @pilot/ui check-types && pnpm --filter web check-types && pnpm --filter mobile build && pnpm --filter @pilot/ui lint && pnpm --filter web lint && pnpm --filter mobile lint && echo "=== TYPE+LINT PASS ===" && pnpm --filter @pilot/ui test 2>&1 | tail -6 && pnpm --filter web test 2>&1 | tail -6 && pnpm --filter mobile test 2>&1 | tail -8 && echo "=== MVP FINAL VERIFICATION COMPLETE ==="
  ```
- [ ] Final test count (before → after) documented
- [ ] Completion Summary added to pilot-launch-plan.md

---

## Completion Summary

After all Definition of Done items are complete, add to `dev-docs/analysis/pilot-launch-plan.md`:

```markdown
### FE-B25 — Job Edit UI (useUpdateJob + JobEditModal): Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot React Engineer
**Baseline**: X passed (web)
**Final**: X+N passed (+N new tests)
**Build**: ✅ Pass — TypeScript errors: 0, ESLint warnings: 0

#### What Was Accomplished

- `useUpdateJob(jobId)` hook — PATCH `/api/v1/jobs/{jobId}`, invalidates job + jobs queries
- `JobEditModal` — pre-populated customer/site cascade form; calls PATCH with changed fields only
- "Edit Job" button wired in `JobDetailPage` with `<RoleGate permission="jobs.update">`
- `jobHandlers.ts` extended with PATCH mock handler for tests

#### Files Changed / Created

| File | Action |
|---|---|
| `features/jobs/hooks/useUpdateJob.ts` | Created |
| `features/jobs/components/JobEditModal.tsx` | Created |
| `features/jobs/components/JobDetailPage.tsx` | Updated — "Edit Job" button + JobEditModal |
| `mocks/handlers/jobHandlers.ts` | Updated — PATCH handler added |
| `__tests__/batch_fe_b25/job_edit.integration.test.tsx` | Created — 5 tests |

#### Tests Added

| Test File | Type | Tests | All Pass |
|---|---|---|---|
| `batch_fe_b25/job_edit.integration.test.tsx` | Integration | 5 | ✅ |
```
