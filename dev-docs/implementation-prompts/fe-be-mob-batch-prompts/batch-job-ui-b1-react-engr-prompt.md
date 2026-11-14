# Implementation Prompt: JOB-UI-B1 (Part B) — Jobs List Title + Full-Page Edit + Priority/Job-Type Dropdowns

**Mode**: Pilot React Engineer
**Batch**: JOB-UI-B1 (Part B — Frontend web)
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §2.3 JOB-UI-B1
**Design doc**: `batch-job-ui-b1-design.md` — Part B (§G–I)
**Backend companion**: JOB-UI-B1 Part A — **must complete first + `pnpm sync-api-types`**. Also depends on CLASS-B1 ✅ (priority + `GET /job-types`).
**Estimated session**: 3–4 hours
**Platform**: Web only (`apps/web`)

---

## ⚠️ MANDATORY STOP: Read These First

- **`.roo/rules-pilot-react-engineer/react-engineer-rules.md`** — in full
- **`batch-job-ui-b1-design.md`** — Part B (§G surfaces, §H manifest, §I reuse)

Critical rules for this batch:

- **Rule 1.3**: `pnpm sync-api-types` FIRST — Part A added `title`/`quote_version_id` + status-editable to the Job contract; CLASS-B1 added priority/job_type + `GET /job-types`.
- **Rule 2**: All API via `apiClient`. `fetch()` banned.
- **Rule 7**: Reuse — `CustomerCombobox`/`SiteCombobox` (already in `JobEditModal`), `RoleGate`, `PilotPaginator`, states. Do not recreate.
- **Rule 9**: New route file `app/(authed)/jobs/[id]/edit/page.tsx` MUST be a thin server component — one line rendering the feature component. All logic in `features/jobs/`.
- **Rule 10**: Any failing test fixed before done. Root cause unclear → STOP and ask Tom.

**Seed-Data Awareness (react-engr §18):** Part A seeded real `title` on scenario jobs + priority/job_type from CLASS-B1. MSW job fixtures must carry `title` (some null to test the `job_number` fallback), `priority`, and `job_type_code`/`job_type_label`.

---

## Design Decisions (Do Not Re-Litigate)

| Decision | Outcome |
|---|---|
| Title column fallback | Show `title`; when null → fall back to `job_number` |
| Edit location | **Full-page** `/jobs/{id}/edit` (new). `JobDetailPage` "Edit Job" routes there. |
| `JobEditModal` | **Unchanged** — stays the dispatch board's schedule-only quick edit. Do NOT add title/priority/job_type/status to it. |
| Priority values | `standard` · `urgent` · `emergency` (from CLASS-B1) |
| Job type dropdown | from `GET /api/v1/job-types`; display `label`, submit `job_type_id` (the row `id`) |
| Status editing | on the full-page form only; backend validates transitions (422 on illegal — surface the RFC 7807 message) |

---

## Pre-Work: Establish Regression Baseline

```bash
cd <repo>/frontend
pnpm --filter web test 2>&1 | tail -5
```
Record; fix any pre-existing failure (or confirm with Tom) first.

---

## Pre-Work: Sync API Types

```bash
cd <repo>/frontend
pnpm sync-api-types
grep -A 40 "JobResponse\|JobUpdate" frontend/packages/shared-types/src/api-schema.d.ts | grep -E "title|status_id|status_code|priority|job_type_id|quote_version_id"
```
`title` + status-editable + priority/job_type must appear. If not → Part A not synced. STOP and confirm with Tom.

---

## Pre-Work: Verify Endpoints

```bash
grep -A 6 "job-types" backend/openapi_schema_map.md
grep -A 30 "PATCH /api/v1/jobs" backend/openapi_schema_map.md | grep -E "title|status"
```

---

## Pre-Work: Read These Source Files

```
frontend/apps/web/src/features/jobs/components/JobsPage.tsx                    ← add Title column + row Edit action
frontend/apps/web/src/features/jobs/components/JobDetailPage.tsx               ← Edit Job → route to full page; title in header; priority/job_type chips
frontend/apps/web/src/features/jobs/components/JobDetailHeader.tsx             ← render title
frontend/apps/web/src/features/jobs/components/JobEditModal.tsx                ← REFERENCE ONLY (combobox pattern); do NOT modify (stays schedule-only)
frontend/apps/web/src/features/jobs/hooks/useUpdateJob.ts                      ← extend payload + response (title/priority/job_type_id/status)
frontend/apps/web/src/features/jobs/hooks/useJob.ts + useJobs.ts              ← carry title through
frontend/apps/web/src/components/CustomerCombobox.tsx + SiteCombobox.tsx       ← reuse on full-page form
frontend/apps/web/src/app/(authed)/jobs/[id]/  (route dir)                     ← where to add edit/page.tsx
frontend/apps/web/src/mocks/handlers/  (jobs handlers)                         ← add title/priority/job_type to fixtures; job-types handler
frontend/apps/web/src/mocks/handlers/index.ts                                 ← register job-types handler if new
```

Locate route dir + jobs MSW handler + any existing job-types handler:
```bash
find frontend/apps/web/src/app/\(authed\)/jobs -type f
grep -rln "jobs/\|job-types" frontend/apps/web/src/mocks/handlers/
```

---

## Context: What This Batch Does

| Area | Change |
|---|---|
| `useJobTypes.ts` | **New** — `useQuery` `GET /api/v1/job-types` |
| `useUpdateJob.ts` | Extend `JobUpdatePayload` + response: `title`, `priority`, `job_type_id`, `status_id`/`status_code` |
| `JobEditPage.tsx` | **New** — full-page edit: title, customer, site, schedule, duration, priority, job_type, status |
| `app/(authed)/jobs/[id]/edit/page.tsx` | **New** — thin route |
| `JobsPage.tsx` | Title column (fallback job_number) + row Edit action (gated `jobs.edit`) |
| `JobDetailPage.tsx` | Title in header; priority/job_type read-only chips; Edit routes to `/jobs/{id}/edit` |
| MSW | Job fixtures carry title/priority/job_type; job-types handler |

---

## STEP 1 — `useJobTypes` hook

`features/jobs/hooks/useJobTypes.ts` (new): `useQuery(["job-types"], () => apiClient.get("/api/v1/job-types"))` → `JobTypeItem[]` (`{id, code, label, sort_order, is_active, is_tenant_override}` from `@pilot/shared-types`). `retry: false` handling per standard.

---

## STEP 2 — `useUpdateJob` extend

Add to `JobUpdatePayload`: `title?: string | null`, `priority?: "standard" | "urgent" | "emergency"`, `job_type_id?: string | null`, and `status_id?: string` (or `status_code?: string` — match Part A's contract; check the synced type). Add the same to `JobUpdateResponse`. Preserve the partial-PATCH semantics (only send changed fields). Surface the backend RFC 7807 `detail` on 422 (illegal status transition) — the `apiClient` error shape is already handled; ensure the form shows it.

---

## STEP 3 — `JobEditPage` (new full-page form)

`features/jobs/components/JobEditPage.tsx` — wrap in `<RoleGate permission="jobs.edit">`. Fields: **Title** (text), **Customer** (`CustomerCombobox`), **Site** (`SiteCombobox`), **Scheduled Start/End** (datetime-local — reuse the `toDatetimeLocalValue`/`fromDatetimeLocalValue` helpers from `JobEditModal`; extract to a shared util if cleaner), **Estimated Duration**, **Priority** (`<select>` Standard/Urgent/Emergency), **Job Type** (`<select>` from `useJobTypes`, option value = `id`, display `label`), **Status** (`<select>` of valid statuses). Partial PATCH via `useUpdateJob`. On success → navigate back to `/jobs/{id}` (`useRouter().push`). On 422 → show the RFC 7807 message inline. Loading/error states via `@pilot/ui` states + `useJob`.

Thin route `app/(authed)/jobs/[id]/edit/page.tsx`:
```tsx
import { JobEditPage } from "@/features/jobs/components/JobEditPage";
export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <JobEditPage jobId={id} />;
}
```
(Match the actual Next param convention used by the sibling `jobs/[id]/page.tsx` — read it first.)

Intermediate:
```bash
pnpm --filter web test -- apps/web/src/features/jobs 2>&1 | tail -10
```

---

## STEP 4 — `JobsPage` Title column + row Edit

- Add a **Title** column to the TanStack table: render `job.title ?? job.job_number`.
- Add a row **Edit** action (gated `jobs.edit`) → `router.push('/jobs/${id}/edit')`. Match the existing row-action pattern in the table (read the file).

---

## STEP 5 — `JobDetailPage` + header

- `JobDetailHeader`: render `title` (fallback `job_number`).
- `JobDetailPage`: add read-only **priority** + **job_type** chips near the header (reuse the chip styling from `CustomerOverviewTab`/DISPATCH-B3 pattern — neutral chip; priority colored per DISPATCH-B3 convention: emergency=fault, urgent=warn, standard=neutral). Change the "Edit Job" button from opening `JobEditModal` to `router.push('/jobs/${jobId}/edit')`.
- **Leave `JobEditModal` mounted for the dispatch board** — but on the detail page, the Edit button now routes to the full page. (If `JobEditModal` is no longer used by `JobDetailPage` after this, confirm it's still imported by the dispatch board before removing the import here; do NOT delete the modal.)

Intermediate:
```bash
pnpm --filter web test -- apps/web/src/features/jobs 2>&1 | tail -10
```

---

## Test Requirements

Web = Vitest + `@testing-library/react`. Mock `next/navigation` (`useRouter` push). QueryClient `retry: false`. MSW at HTTP level; `afterEach(server.resetHandlers())`.

**MSW**: job fixtures carry `title` (≥1 null to test fallback), `priority` (varied), `job_type_code`/`job_type_label`; add a `GET /api/v1/job-types` handler returning ≥3 types; register in `index.ts`.

Create in `apps/web/src/__tests__/batch_job_ui_b1/` + co-located:
- **JobsPage Title column**: renders `title` when present; falls back to `job_number` when null; row Edit action navigates to `/jobs/{id}/edit` (assert `push` called).
- **useJobTypes**: returns list shape from MSW.
- **JobEditPage**: renders all fields pre-filled from `useJob`; priority `<select>` has Standard/Urgent/Emergency; job_type `<select>` populated from `useJobTypes`; submit fires PATCH with only changed fields (assert body); RBAC — `jobs.edit` gates the page (tech role blocked).
- **Illegal status transition**: MSW returns 422 RFC 7807 → form shows the detail message.
- **JobDetailPage**: title in header; priority/job_type chips render; Edit button routes to full page (not modal open).
- Update any existing JobDetailPage/JobsPage tests that assumed the modal-based edit.

---

## Final Verification

> ❌ BANNED: `npx vitest run`. Only `pnpm --filter web test`.

### Phase 1 — Targeted
```bash
cd <repo>/frontend
pnpm --filter web test -- apps/web/src/features/jobs 2>&1 | tail -10
pnpm --filter web test -- apps/web/src/__tests__/batch_job_ui_b1/ 2>&1 | tail -10
```
### Phase 2 — Full
```bash
cd <repo>/frontend && echo "=== UI - Type Check ===" && pnpm --filter @pilot/ui check-types && echo "=== Web - Type Check ===" && pnpm --filter web check-types && echo "=== Mobile - Type Check ===" && pnpm --filter mobile build && echo "=== UI - Lint ===" && pnpm --filter @pilot/ui lint && echo "=== Web - Lint ===" && pnpm --filter web lint && echo "=== Mobile - Lint ===" && pnpm --filter mobile lint && echo "=== TYPE+LINT PASS ===" && echo "=== UI - Tests ===" && pnpm --filter @pilot/ui test 2>&1 | tail -6 && echo "=== Web - Tests ===" && pnpm --filter web test 2>&1 | tail -6 && echo "=== Mobile - Tests ===" && pnpm --filter mobile test 2>&1 | tail -8 && echo "=== MVP FINAL VERIFICATION COMPLETE ==="
```
Any failure in either phase fixed before done.

---

## Definition of Done — JOB-UI-B1 (Part B)

- [ ] Regression baseline captured (zero pre-existing failures or confirmed with Tom)
- [ ] `pnpm sync-api-types` run — title/status-editable/priority/job_type present
- [ ] **STEP 1**: `useJobTypes` hook
- [ ] **STEP 2**: `useUpdateJob` extended (title/priority/job_type_id/status; partial semantics; 422 surfaced)
- [ ] **STEP 3**: `JobEditPage` full-page form + thin `/jobs/[id]/edit` route (RoleGate jobs.edit)
- [ ] **STEP 4**: `JobsPage` Title column (fallback job_number) + row Edit action
- [ ] **STEP 5**: `JobDetailPage` title header + priority/job_type chips + Edit routes to full page; `JobEditModal` unchanged (still dispatch-board quick edit)
- [ ] MSW job fixtures + job-types handler; registered in `index.ts`
- [ ] Zero hardcoded design values (chip colors from tokens)
- [ ] Unit + integration tests pass
- [ ] **Phase 2 FULL verification passes** (`=== MVP FINAL VERIFICATION COMPLETE ===`)
- [ ] Final test count documented
- [ ] Completion Summary added to launch plan Appendix B

---

## Completion Summary

Add to `pilot-launch-plan.md` Appendix B (React template). This closes JOB-UI-B1 (and, with DISPATCH-B3 + CUST-UI-B1, the full CLASS-B1 → FE-consumer wave). Mark JOB-UI-B1 ✅ in §2.0.
