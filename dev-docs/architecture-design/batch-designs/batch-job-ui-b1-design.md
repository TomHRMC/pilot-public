# Batch Design: JOB-UI-B1 — Jobs List + Edit Improvements

**Batch**: JOB-UI-B1 (mixed — Python first, then React)
**Author**: Pilot Architect
**Date**: 2026-07-27
**Status**: Ready for Tom review → Python Engineer (Part A) → React Engineer (Part B)
**Source plan**: `pilot-launch-plan.md §2.3 JOB-UI-B1`
**Prerequisite**: CLASS-B1 ✅ (priority + job_type schema/endpoint already shipped)

> **Scope**: The only net-new schema is `job.title`. Priority + job_type were delivered by CLASS-B1 (schemas + `GET /job-types` already exist). This batch (1) adds `job.title`, (2) makes `status` editable via `JobUpdate`, (3) surfaces title + priority + job_type in the jobs list and a full-page job edit form, and (4) adds priority/job_type dropdowns to job detail/edit + read-only to the dispatch panel (the panel read-only chips are DISPATCH-B3; here we cover the job pages).

---

## A. Input Read Summary

| Input | Why | Takeaway (verified 2026-07-27) |
|---|---|---|
| MCP `job` columns | Confirm title absence | `job` has **no** `title` column. Has `job_number`, `quote_version_id`, `status_id`, `version`, `priority` (CLASS-B1), `job_type_id` (CLASS-B1). |
| `schemas.py` Job*  | Current contract | `JobCreate/JobUpdate` already accept `priority`+`job_type_id` (CLASS-B1). `JobResponse/JobListItem` already return `priority`/`job_type_id`/`job_type_code`/`job_type_label`. **`JobUpdate` excludes `status_id`** (comment: transitions via dispatch). None have `title`/`quote_version_id`. |
| `JobEditModal.tsx` | Current edit UI | Modal edits customer/site/schedule/duration only via `useUpdateJob` partial PATCH. No title/priority/job_type/status. |
| `JobDetailPage.tsx` | Edit entry point | "Edit Job" button opens `JobEditModal`; also has TechAssignmentSection + profitability + 5 tabs. |
| `useUpdateJob.ts` | Update hook | `JobUpdatePayload` = customer/site/schedule/duration only. `JobUpdateResponse` lacks title/priority/job_type. |
| `JobsPage.tsx` | List grid | TanStack table; needs a Title column. |
| `GET /api/v1/job-types` | Dropdown source | Live (CLASS-B1): `[{id, code, label, sort_order, is_active, is_tenant_override}]`. |

---

## Part A — Backend (Python Engineer, runs first)

### B. Migration Plan

**One Alembic migration** (blank). Base = current head (`44fb6fed24c3` after CLASS-B1). `job.title` is nullable → **no 3-part pattern needed** (nullable add is single-step).

```sql
ALTER TABLE job ADD COLUMN title TEXT;   -- nullable; no backfill, no CHECK
```

- **Model**: `Job.title: str | None = Field(default=None)` in `fulfillment.py`.
- **No trigger changes** (existing `job` triggers cover the new column).
- `downgrade()`: `ALTER TABLE job DROP COLUMN title;`
- Triple-verify upgrade/downgrade/upgrade. Regenerate `db_models_map.md`, `schema_manager.py` (`job.title`), `openapi.json`.

> **Title default-from-quote**: when a job is created from a quote, default `title` from `quote.title`. This is **application logic in the job-create route**, not a DB default — the route already has `quote_id`; when `title` is omitted and `quote_id`/`quote_version_id` is set, look up the quote's title (tenant-scoped `select`) and use it. `quote.title` column existence must be MCP-verified by the engineer before wiring (the prompt requires it).

### C. Execution Order (Part A)
1. `Job.title` model field → migration → triple-verify → `generate_db_model_map.py`.
2. Schemas: add `title` to `JobCreate`/`JobUpdate`/`JobResponse`/`JobListItem`; add `quote_version_id` to `JobResponse`; make `status_id` editable in `JobUpdate` (see D).
3. Routes: job create defaults title from quote; job update accepts title + status (with transition validation); `list_jobs` projects `title`.
4. `schema_manager.py` + `export_openapi_json.py`.
5. Seed: add `title` to scenario jobs (Group D — see §F).

### D. API Changes (Part A)

No new routes. Field additions on existing endpoints:

| Endpoint | Change |
|---|---|
| `POST /api/v1/jobs` (+ `/test`) | Accept `title: str \| None`. When omitted **and** the job is created from a quote, default from `quote.title` (tenant-scoped lookup). |
| `PATCH /api/v1/jobs/{id}` (+ `/test`) | Accept `title`. **Also accept `status_id`** (or `status_code`) with **transition validation** — see below. This relaxes the current "status not editable here" rule. |
| `GET /api/v1/jobs/` (`_list_jobs_impl`) | Project `title`. |
| `GET /api/v1/jobs/{id}` | Return `title`, `quote_version_id`. |

**Status transition validation** (Tom decision — status becomes editable on the full-page edit form): `JobUpdate` gains `status_id: UUID | None` (or `status_code: str | None` — engineer picks whichever matches the existing status-set path; **MCP-verify `job_status` codes** first: `draft/scheduled/in_progress/completed/cancelled` + any others). Validate the transition is legal (e.g. cannot move `cancelled`→`in_progress`); reject illegal transitions with RFC 7807 422. If a transition matrix does not already exist, use a minimal forward-only guard: allow any → `cancelled`; `draft`→`scheduled`→`in_progress`→`completed`; block backward jumps except to `cancelled`. Confirm with Tom if the matrix is ambiguous.

> The dispatch-board move/reschedule path still owns **schedule** changes; JOB-UI-B1 only adds **status** editing on the job edit form. The `JobEditModal` (dispatch board's quick edit) stays schedule-only.

### E. Pattern Reuse
- Nullable column add (single-step, no 3-part) — `title` has no NOT NULL requirement.
- `db.get()` ban — quote-title lookup + status validation use tenant-scoped `select()`.
- RFC 7807 on invalid status transition.
- `set_audit_context_sync` on the mutation paths (already present; confirm).

### F. Seed (Part A — §20 dual rollout)
- **Group D scenario**: assign a human `title` to the scenario jobs that have one naturally — e.g. `seed_scenario_dispatch.py` + `seed_scenario_reporting.py` jobs get descriptive titles ("Panel Upgrade — Apex HQ", "Service Call — Smith Residence") so the list Title column shows real data. Idempotent `UPDATE` on owned rows. (No Group A/core rows — `title` is tenant data, not a platform lookup.)
- Jobs created from a quote in `seed_scenario_quote_to_cash.py` (JOB-900001) should get `title` from the linked quote's title to exercise the default path.

---

## Part B — Frontend (React Engineer, after Part A + `pnpm sync-api-types`)

### G. Surface Changes

| Surface | Change |
|---|---|
| **Jobs list** (`JobsPage.tsx`) | Add a **Title** column (fallback to `job_number` when title null). Add a direct row **Edit** action gated `jobs.edit` → navigates to the full-page edit route. |
| **Full-page edit** (new route `/jobs/{id}/edit`) | New thin route → `JobEditPage` feature component with all editable fields: title, customer, site, schedule, duration, **priority** (Standard/Urgent/Emergency), **job_type** (`GET /job-types` dropdown), **status** (dropdown with transition validation). Reuses `useUpdateJob` (extended). |
| **`JobEditModal`** (dispatch board quick edit) | **Kept schedule-only** — do NOT add title/priority/job_type/status here. The modal is the dispatch board's inline reschedule; full editing moves to the page. |
| **Job detail** (`JobDetailPage.tsx`) | Show title in the header; show priority + job_type as read-only chips near the header (reusing the chip styling); "Edit Job" button now routes to `/jobs/{id}/edit` (full page) instead of opening the modal. |

### H. Component Manifest (Part B)

| File | Action |
|---|---|
| `apps/web/src/app/(authed)/jobs/[id]/edit/page.tsx` | **New** — thin server component → `<JobEditPage jobId={...} />` |
| `apps/web/src/features/jobs/components/JobEditPage.tsx` | **New** — full-page edit form (title, customer, site, schedule, duration, priority, job_type, status) |
| `apps/web/src/features/jobs/hooks/useUpdateJob.ts` | **Update** — `JobUpdatePayload` + response gain `title`, `priority`, `job_type_id`, `status_id`/`status_code` |
| `apps/web/src/features/jobs/hooks/useJobTypes.ts` | **New** — `useQuery` for `GET /api/v1/job-types` (shared with dispatch if convenient; place in jobs feature) |
| `apps/web/src/features/jobs/components/JobsPage.tsx` | **Update** — Title column + row Edit action |
| `apps/web/src/features/jobs/components/JobDetailPage.tsx` | **Update** — title in header, priority/job_type chips, Edit routes to full page |
| `apps/web/src/features/jobs/components/JobDetailHeader.tsx` | **Update** — render title |
| `apps/web/src/features/jobs/hooks/useJobs.ts` / `useJob.ts` | **Update** — carry `title` through (mostly from `sync-api-types`) |

`JobEditModal.tsx` is **unchanged** (stays schedule-only for the dispatch board).

### I. Reuse
- Priority dropdown values `standard/urgent/emergency` — same as DISPATCH-B3 (from CLASS-B1). Job type dropdown from `useJobTypes` (label display, value = `id` sent as `job_type_id`).
- `CustomerCombobox`/`SiteCombobox` (already used by `JobEditModal`) reused on the full-page form.
- `RoleGate permission="jobs.edit"` on the edit route + row action.

---

## Open Questions Resolved

| Q | Resolution |
|---|---|
| Does CLASS-B1 already cover priority/job_type schema? | **Yes** — `JobCreate/Update/Response/ListItem` already have them + `GET /job-types` is live. JOB-UI-B1 only adds the **UI** for them (dropdowns) + the net-new `job.title`. |
| 3-part migration for `title`? | **No** — `title` is nullable, single-step add. |
| Status editing — where? | Full-page edit form only (with transition validation). `JobEditModal` stays schedule-only. Dispatch board move path unchanged. |
| Priority/job_type read-only chips on dispatch panel? | **DISPATCH-B3**, not here. JOB-UI-B1 covers the job detail/edit pages. |
| title default from quote | Application logic in job-create route (MCP-verify `quote.title` exists first). |

---

## Handoff

Two prompts:
- `batch-job-ui-b1-python-engr-prompt.md` — Part A (title + status-editable + seed). Ends with `export_openapi_json.py` + handoff to React.
- `batch-job-ui-b1-react-engr-prompt.md` — Part B (after `pnpm sync-api-types`).

*Authored 2026-07-27. `job.title` absence + Job schema state MCP/source-verified. Priority/job_type already delivered by CLASS-B1.*
