# Implementation Prompt: JOB-UI-B1 (Part A) — job.title + Status-Editable + Seed

**Mode**: Pilot Python Engineer
**Batch**: JOB-UI-B1 (Part A — Backend)
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §2.3 JOB-UI-B1
**Design doc**: `batch-job-ui-b1-design.md` — Part A (§B–F)
**Estimated session**: 2.5–3 hours
**Platform**: Backend only (`backend/`)
**Frontend companion**: JOB-UI-B1 Part B (React) — runs after this + `pnpm sync-api-types`

---

## ⚠️ MANDATORY STOP: Read These First

- **`dev-docs/architecture-design/pilot-python-engineer-methods.md`** — §13 (Alembic), §8 (Router), §5 (Model)
- **`backend/tests/README-adding-tests.md`** — full
- **`batch-job-ui-b1-design.md`** — Part A + Open Questions
- **`backend/README-seed-data.md`** — §3/§6/§7 (before editing seed scripts)

Critical rules for this batch:

- **Rule 1**: Never guess column/table names. MCP-verify. Error → STOP and ask Tom.
- **Rule 2**: Model change → `python generate_db_model_map.py`.
- **Rule 3**: Endpoint change → `python export_openapi_json.py`.
- **Rule 4**: Blank Alembic migration (never `--autogenerate`).
- **Rule 6**: `db.get()` banned on tenant-scoped models — quote-title lookup + status validation use tenant-scoped `select()`.
- **Rule 8**: RFC 7807 on invalid status transition (422).
- **Rule 9**: `set_audit_context_sync` on mutations before first write.
- **Rule 11**: Any failing test fixed before done. Root cause unclear → STOP and ask Tom.

**Context**: CLASS-B1 already added `job.priority` + `job.job_type_id` + `GET /job-types`, and `JobCreate/Update/Response/ListItem` already carry priority/job_type fields. **This batch adds only `job.title`** + makes `status` editable + seed titles. Do NOT re-add priority/job_type.

---

## Pre-Work: Establish Regression Baseline

```bash
cd <repo>/backend && source .venv/bin/activate
python -m pytest -m unit --tb=no -q 2>&1 | tail -5
```
Record `X passed, Y failed`. Fix any pre-existing failure (or confirm with Tom) before starting.

---

## Pre-Work: Run MCP Verification Queries

> **MCP is read-only.** Error → STOP and ask Tom.

```sql
-- 1. Confirm job has NO title column; confirm priority/job_type_id present (CLASS-B1) + quote_version_id
SELECT column_name, data_type, is_nullable FROM information_schema.columns
WHERE table_schema='public' AND table_name='job' ORDER BY ordinal_position;

-- 2. Confirm quote.title exists (for the default-from-quote logic)
SELECT column_name, data_type FROM information_schema.columns
WHERE table_schema='public' AND table_name='quote' AND column_name='title';

-- 3. job_status codes (for status transition validation)
SELECT code, is_default, is_terminal FROM public.job_status ORDER BY code;

-- 4. Alembic head (migration base)
SELECT version_num FROM public.alembic_version;
```

If query 2 returns nothing → `quote.title` does not exist; the default-from-quote logic must key off a different quote field (check `quote` columns) or be deferred — STOP and ask Tom before wiring the default.

---

## Pre-Work: Read These Source Files

```
backend/app/models/fulfillment.py               ← Job model — add title field
backend/api/schemas/schemas.py                   ← JobCreate/JobUpdate/JobResponse/JobListItem (:184–275) — add title + quote_version_id + status_id to JobUpdate
backend/api/routes/jobs.py                        ← create (default title from quote), update (title + status w/ transition validation), _list_jobs_impl (project title)
backend/migrations/versions/2026_07_27_1336-44fb6fed24c3_class_b1_classification.py  ← most recent migration — pattern reference
backend/migrations/scripts/seed_scenario_dispatch.py      ← add job titles
backend/migrations/scripts/seed_scenario_reporting.py     ← add job titles
backend/migrations/scripts/seed_scenario_quote_to_cash.py ← job-from-quote title default
backend/tests/conftest.py                        ← fixtures (test_job, test_tenant)
```

Find the status-set path + job create-from-quote:
```bash
grep -n "status_id\|status_code\|quote_id\|quote_version_id\|_list_jobs_impl\|def create_job\|def update_job" backend/api/routes/jobs.py
```

---

## Task 1 — Model + Migration

- `app/models/fulfillment.py`: add `title: str | None = Field(default=None)` to `Job`.
- Blank migration `alembic revision -m "job_ui_b1_job_title"` (base = query 4 head):
  ```python
  def upgrade():
      op.execute("ALTER TABLE job ADD COLUMN title TEXT;")  # nullable — single-step
  def downgrade():
      op.execute("ALTER TABLE job DROP COLUMN title;")
  ```
- No CHECK, no backfill, no trigger changes (nullable add; existing `job` triggers cover it).
- Triple-verify: `alembic upgrade head && alembic downgrade -1 && alembic upgrade head && alembic current`.
- `python generate_db_model_map.py`.

---

## Task 2 — Schemas

In `schemas.py`:
- `JobCreate`: add `title: str | None = None`.
- `JobUpdate`: add `title: str | None = None` **and** `status_id: UUID | None = None` (or `status_code: str | None = None` — match the code path the route uses to set status; MCP query 3 gives the valid codes). Update the docstring — status is now editable here with transition validation.
- `JobResponse`: add `title: str | None = None` and `quote_version_id: UUID | None = None`.
- `JobListItem`: add `title: str | None = None`.

---

## Task 3 — Routes (`jobs.py`)

- **Create** (`create_job` + `/test`): accept `title`. When `title` is omitted **and** the job is created from a quote (`quote_id`/`quote_version_id` set), default from the quote's title via a tenant-scoped `select` on `quote` (Rule 6 — never `db.get`). `set_audit_context_sync` before write.
- **Update** (`update_job` + `/test`): accept `title` (partial). Accept `status_id`/`status_code` with **transition validation**:
  - MCP query 3 gives codes (expected: `draft`, `scheduled`, `in_progress`, `completed`, `cancelled`).
  - Allow forward: `draft→scheduled→in_progress→completed`; allow any→`cancelled`; block backward (except →cancelled). Illegal → RFC 7807 422.
  - If a transition matrix/service already exists in the codebase (grep `transition` in scheduling/jobs), reuse it; otherwise implement the minimal guard above. If ambiguous → STOP and ask Tom.
- **List** (`_list_jobs_impl`): project `title` into `JobListItem`.
- **Detail** (`get_job`): return `title` + `quote_version_id`.

Regenerate:
```bash
python export_openapi_json.py
grep -A 30 "JobUpdate\|JobResponse" backend/openapi_schema_map.md | grep -i title
```

---

## Task 4 — Seed Data Rollout (Group D only — §20 Layer 2)

`title` is tenant data (no core/platform rows). Per `README-seed-data.md` §7 (idempotent, value-scoped UPDATE on owned rows):
- `seed_scenario_dispatch.py`: give each of the 6 dispatch jobs a descriptive `title` (e.g. "Panel Upgrade — Apex HQ", "Service Call — Smith Residence").
- `seed_scenario_reporting.py`: give the 7 completed jobs titles matching their nature (Panel Upgrade, Service Call, Commercial Inspection, …).
- `seed_scenario_quote_to_cash.py`: the job created from a quote (JOB-900001) — set `title` from the linked quote's title (exercises the default path).

Verify tests still pass after seeding:
```bash
python migrations/scripts/seed_scenario_dispatch.py
python migrations/scripts/seed_scenario_reporting.py
python migrations/scripts/seed_scenario_quote_to_cash.py
python -m pytest -m unit --tb=no -q 2>&1 | tail -5
```

### schema_manager + README
```bash
python schema_manager.py --help   # then set job.title
```
Update `README-seed-data.md` §4 Group D (job `title` on scenario jobs).

---

## Test Requirements

Per `README-adding-tests.md`. New file `tests/domains/field_operations/test_job_ui_b1.py` — `pytestmark = [pytest.mark.domain_field_operations, pytest.mark.unit]`; `client` + `test_tenant`/`test_job` fixtures; assert by inserted ID.

Cover:
- Create job with `title` → persists + returned.
- Create job from a quote **without** title → title defaults from `quote.title`.
- Update job `title` (partial) → persists; other fields untouched.
- Update `status` legal transition (`scheduled`→`in_progress`) → succeeds.
- Update `status` illegal transition (`completed`→`draft`) → 422 RFC 7807.
- Update → `cancelled` from any status → succeeds.
- `GET /jobs/` list projects `title`; `GET /jobs/{id}` returns `title` + `quote_version_id`.
- Migration backfill: existing jobs have `title = NULL` (nullable, no backfill).

---

## Final Verification

### Phase 1 — Unit
```bash
cd <repo>/backend && source .venv/bin/activate
python -m pytest -m unit --tb=short -q 2>&1 | tail -10
```
### Phase 2 — Full
```bash
cd <repo>/backend && source .venv/bin/activate
python -m pytest --tb=short -q 2>&1 | tail -10
python -m pytest tests/domains/field_operations/ -q 2>&1 | tail -10
grep -i "title" backend/openapi_schema_map.md | grep -i job | head
echo "=== JOB-UI-B1 (Part A) FINAL VERIFICATION COMPLETE ==="
```
Any failure in either phase fixed before done. Root cause unclear → STOP and ask Tom.

---

## Definition of Done — JOB-UI-B1 (Part A)

- [ ] Regression baseline captured; zero pre-existing failures (or confirmed with Tom)
- [ ] MCP queries run — `job.title` absent confirmed; `quote.title` confirmed (or Tom consulted); `job_status` codes captured; head captured
- [ ] Mandatory source files read (incl. `schemas.py` + 3 seed scripts + README-seed-data)
- [ ] **Task 1**: `Job.title` model field + nullable-add migration; triple-verify passes; model map regenerated
- [ ] **Task 2**: `title` on JobCreate/Update/Response/ListItem; `quote_version_id` on JobResponse; `status_id`/`status_code` on JobUpdate
- [ ] **Task 3**: create defaults title from quote; update accepts title + status with transition validation (RFC 7807 on illegal); list/detail project title; `set_audit_context_sync` present
- [ ] `export_openapi_json.py` run — `title` visible on Job schemas in map
- [ ] **Task 4**: scenario titles seeded (dispatch/reporting/quote_to_cash); idempotent; tests still pass
- [ ] `schema_manager.py` (`job.title`) + `README-seed-data.md` §4 updated
- [ ] New tests use domain marker + `pytest.mark.unit`, `client` fixture, no hardcoded UUIDs, assert-by-ID
- [ ] **Phase 1** unit pass; **Phase 2** full suite pass (both zero failures)
- [ ] Final test count documented
- [ ] Completion Summary added to launch plan Appendix B

---

## Completion Summary

Add to `pilot-launch-plan.md` Appendix B (Python template). Handoff note MUST state:

> JOB-UI-B1 Part A complete. Run `pnpm sync-api-types` before Part B. New contract: `job.title` (nullable, defaults from quote on create), `status_id`/`status_code` now editable via `PATCH /jobs/{id}` with transition validation (RFC 7807 on illegal), `title`/`quote_version_id` on `JobResponse`, `title` on `JobListItem`. Priority/job_type were already delivered by CLASS-B1. Part B (React) adds the Title column, full-page edit route, and priority/job_type/status dropdowns.
