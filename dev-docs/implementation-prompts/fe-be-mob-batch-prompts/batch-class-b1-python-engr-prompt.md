# Implementation Prompt: CLASS-B1 — Job/Site/Customer Classification Foundation

**Mode**: Pilot Python Engineer
**Batch**: CLASS-B1
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §2.3
**Design doc**: `batch-class-b1-design.md` — every section (A–G)
**Estimated session**: 4–5 hours
**Platform**: Backend only (`backend/`)
**Frontend companions**: JOB-UI-B1, CUST-UI-B1, DISPATCH-B3 (all depend on this batch + `pnpm sync-api-types`)

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`dev-docs/architecture-design/pilot-python-engineer-methods.md`** — §13 (Alembic), §8 (Router Design), §5 (Model Design), §16 (Standard Task Workflow)
- **`backend/tests/README-adding-tests.md`** — full document
- **`batch-class-b1-design.md`** — every section, especially §B (Migration Plan), §D (Endpoints), §F (Enrichment + Seed Rollout)
- **`backend/README-seed-data.md`** — §3 (Group A–D), §6 (run order), §7 (DELETE safety + shared-DB rule) — mandatory before editing any seed script

Critical rules for this batch:

- **Rule 1**: Never guess column names, data types, or table names. Use `postgres-local` MCP to verify every name before use. If MCP returns an error → **STOP and ask Tom**.
- **Rule 2**: After any model file change → regenerate `backend/db_models_map.md` via `python generate_db_model_map.py`.
- **Rule 3**: After any endpoint change → run `python export_openapi_json.py`.
- **Rule 4**: Alembic migration must be **blank** (`alembic revision -m "..."`, never `--autogenerate`). Data inserts use raw `op.execute()`.
- **Rule 6**: `db.get()` is permanently banned on tenant-scoped models. Use tenant-scoped `select()` with explicit `WHERE tenant_id`.
- **Rule 8**: All error responses use RFC 7807 Problem Details (invalid `priority`/`site_type` → 422 with the dict shape).
- **Rule 9**: Every mutation endpoint calls `set_audit_context_sync(db, user_id=...)` before the first write.
- **Rule 11**: Any failing test — even seemingly pre-existing — must be fixed before done. Root cause unclear → STOP and ask Tom.

**TEXT + CHECK, NOT PostgreSQL ENUM.** `job.priority` and `site.site_type` are `TEXT` columns with a `CHECK` constraint — matching the deliberate `customer.type` ENUM→TEXT migration (`phase_4_7`). Do NOT create PG `ENUM` types.

---

## Pre-Work: Establish Regression Baseline

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=no -q 2>&1 | tail -5
```
Record `X passed, Y failed`. Fix any pre-existing failure (or confirm with Tom) before starting.

---

## Pre-Work: Run MCP Verification Queries

> **MCP Usage Rule**: `postgres-local` is read-only verification. Never INSERT/UPDATE/DELETE via MCP. If a query errors → STOP and ask Tom.

Run **all** of these before writing any code. The Architect verified these on 2026-07-27 (alembic head `57475453234c`); re-confirm nothing drifted.

```sql
-- 1. Confirm job has NO priority/type column and HAS status_id + version (base for 3-part + enrichment)
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns WHERE table_schema='public' AND table_name='job'
ORDER BY ordinal_position;

-- 2. Confirm customer.type CHECK values (relabel source of truth)
SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint
WHERE conrelid='public.customer'::regclass AND contype='c' AND conname='customer_type_chk';

-- 3. Confirm site has customer_id FK (backfill source) and NO site_type
SELECT column_name, data_type, is_nullable FROM information_schema.columns
WHERE table_schema='public' AND table_name='site' ORDER BY ordinal_position;

-- 4. Confirm none of the new tables exist
SELECT table_name FROM information_schema.tables
WHERE table_schema='public' AND table_name IN ('job_type','job_priority','site_type');

-- 5. Get the EXACT trigger DDL on customer — mirror these three onto job_type
SELECT tgname, pg_get_triggerdef(oid) FROM pg_trigger
WHERE tgrelid='public.customer'::regclass AND NOT tgisinternal ORDER BY tgname;

-- 6. Confirm the trigger FUNCTIONS exist
SELECT proname FROM pg_proc WHERE proname IN ('set_updated_at','log_changes','guard_created_fields_immutable');

-- 7. Alembic head
SELECT version_num FROM public.alembic_version;

-- 8. Row counts to size the 3-part backfill
SELECT (SELECT COUNT(*) FROM job) AS jobs, (SELECT COUNT(*) FROM site) AS sites;
```

If query 5 shows trigger arg styles different from the design doc's pseudocode → use the MCP-returned DDL, note it in your Completion Summary.

---

## Pre-Work: Read These Source Files

```
backend/app/models/fulfillment.py          ← Job model (add priority + job_type_id); pattern for new JobType table
backend/app/models/crm.py                   ← Customer (type CHECK precedent) + Site (add site_type)
backend/api/schemas/schemas.py               ← JobCreate/Update/Response, SiteCreate/Update/Response, CustomerResponse, DispatchBoardJobEntry, DispatchBoardTechGroup
backend/api/routes/jobs.py                    ← job create/update/list — wire priority + job_type_id + list projection
backend/api/routes/scheduling.py              ← _dispatch_board_impl — extend batch-load enrichment (B1/B1.5 pattern)
backend/migrations/versions/2026_04_03_1624-6b15b78db845_phase_4_7_enum_to_text_customer_type_.py  ← TEXT+CHECK precedent
backend/migrations/scripts/seed_core.py       ← Group A: add job_type platform defaults
backend/migrations/scripts/seed_scenario_dispatch.py    ← Group D: assign priority + job_type_id to 6 jobs
backend/migrations/scripts/seed_scenario_reporting.py   ← Group D: assign job_type_id to 7 completed jobs
backend/migrations/scripts/seed_scenario_quote_to_cash.py ← Group D: assign site_type to 7 sites
backend/db_models_map.md                      ← confirm model names
backend/tests/conftest.py                     ← fixtures (test_tenant, test_job, test_site, test_customer, second_tenant)
```

Find the sites route (name varies — could be in `crm.py` routes or a dedicated file):
```bash
grep -rln "SiteCreate\|def create_site\|/sites" backend/api/routes/
grep -rln "def list_jobs\|_list_jobs_impl" backend/api/routes/
```

---

## Context: What This Batch Does

Establishes proper schema for four classification dimensions that the dispatch filters + detail pages need (design §origin). Splits the conflated `rush/standard/warranty` into **priority** (urgency: `standard`/`urgent`/`emergency`) and **job_type** (kind of work); adds **site_type** (commercial/residential/industrial); surfaces the real **customer.type** (person/company) through the dispatch board. Rolls all of it into seed (core defaults + scenarios). Frontend batches consume it after.

| Area | Change |
|---|---|
| `job.priority` | New TEXT+CHECK `standard`/`urgent`/`emergency`, default `standard` (3-part NOT NULL) |
| `job_type` table + `job.job_type_id` | New nullable-tenant lookup (platform defaults + tenant overrides) + nullable FK |
| `site.site_type` | New TEXT+CHECK `commercial`/`residential`/`industrial` (3-part, backfilled from customer.type) |
| `GET /api/v1/job-types` | New endpoint: platform defaults ∪ tenant overrides (tenant wins on `code`) |
| Job/Site schemas + routes | Accept/return new fields; list projections |
| `DispatchBoardJobEntry` | + `priority`, `customer_type`, `site_type`, `job_type_code`, `job_type_label` (batch-load) |
| Seed | Core `job_type` defaults + scenario assignment of all new fields |

Follow the design doc §B for exact migration SQL. Code below is a starting point — read each file first.

---

## Task 1 — Models

**`app/models/fulfillment.py`**:
- New `JobType(StandardAuditMixin, SQLModel, table=True)` — `__tablename__="job_type"`; fields per design §B.2 (`id`, nullable `tenant_id` FK→tenant ON DELETE RESTRICT, `code`, `label`, `sort_order` default 100, `is_active` default true). Do NOT declare the partial unique indexes as SQLModel `UniqueConstraint` (they're partial — created in the migration).
- `Job.priority: str` (default `"standard"`, `server_default=text("'standard'")`, NOT NULL) — but the column is created by the migration's 3-part pattern; the model just declares it.
- `Job.job_type_id: uuid.UUID | None` (nullable FK→`job_type.id` ON DELETE SET NULL, indexed).

**`app/models/crm.py`**:
- `Site.site_type: str` (default `"residential"`, `server_default=text("'residential'")`, NOT NULL).

Then:
```bash
python -m pytest -m unit --tb=short -q 2>&1 | tail -5
```

---

## Task 2 — Alembic Migration

`alembic revision -m "class_b1_classification"`. Implement all 4 groups from design §B (job.priority 3-part; job_type table + triggers + partial indexes + platform seed rows; job.job_type_id FK; site.site_type 3-part backfilled from customer.type). `downgrade()` exactly reverses.

Key points:
- Use the **exact trigger DDL from MCP query 5** for the 3 `job_type` triggers.
- Platform `job_type` seed rows (§B.2 table, 11 rows) inserted here with `ON CONFLICT DO NOTHING` on the platform partial-unique; set `created_at, updated_at = NOW(), NOW()`, `tenant_id = NULL`.
- site_type backfill uses the `CASE WHEN c.type='company' THEN 'commercial' ELSE 'residential' END` join (design §B.3).

Triple-verify:
```bash
alembic upgrade head && alembic downgrade -1 && alembic upgrade head && alembic current
```
Then:
```bash
python generate_db_model_map.py && grep -E "JobType|job_type" backend/db_models_map.md | head
```

---

## Task 3 — Pydantic Schemas

In `api/schemas/schemas.py`:
- `JobCreate`/`JobUpdate`: add `priority: str | None` (validate against `{standard,urgent,emergency}` — reject others with RFC 7807 422) and `job_type_id: uuid.UUID | None`.
- `JobResponse`: add `priority`, `job_type_id`, `job_type_code`, `job_type_label`.
- `SiteCreate`/`SiteUpdate`: add `site_type: str | None` (validate `{commercial,residential,industrial}`).
- `SiteResponse` (+ customer-sites list item shape): add `site_type`.
- Confirm `CustomerResponse` already exposes `type`; if not, add it.
- New `JobTypeResponse` (design §D): `{id, code, label, sort_order, is_active, is_tenant_override}`.
- `DispatchBoardJobEntry`: add `priority: str = "standard"`, `customer_type: str | None = None`, `site_type: str | None = None`, `job_type_code: str | None = None`, `job_type_label: str | None = None`.

---

## Task 4 — Endpoints

**New `api/routes/job_types.py`** (register router in `app/main.py`):
- `_list_job_types_impl(db, tenant_id)`: platform rows (`tenant_id IS NULL`) + tenant rows; dict keyed by `code`, tenant row wins; active only; sort by `sort_order, label`; set `is_tenant_override`. Tenant-scoped `select()` (Rule 6).
- `GET /api/v1/job-types` (auth, `require_permission("jobs.view")`) + `GET /api/v1/job-types/test` (`TestUserContext`, inclusions §11).

**`api/routes/jobs.py`**:
- Job create/update (auth + `/test`): accept `priority` (default `standard` when omitted) + `job_type_id`; `set_audit_context_sync` before writes.
- `_list_jobs_impl` + job detail: project `priority`, `job_type_id`, and LEFT JOIN `job_type` for `job_type_code`/`job_type_label`.

**Sites route** (file found via grep):
- Site create/update: accept `site_type`; **on create, when omitted → customer-type default**: look up the owning customer's `type` (tenant-scoped `select`), `company`→`commercial` else `residential`.
- Site list (customer sites) + detail: project `site_type`.

**`api/routes/scheduling.py` `_dispatch_board_impl`** (design §F.1): extend the existing customer/site batch-loads to also select `Customer.type` and `Site.site_type`; add one batched `job_type` lookup keyed by `job_type_id`; set the 5 new `DispatchBoardJobEntry` fields in the `_build_entry` helper (null-safe). No N+1.

Then:
```bash
python -m pytest -m unit --tb=short -q 2>&1 | tail -5
python export_openapi_json.py
grep -A 4 "job-types" backend/openapi_schema_map.md
```

---

## Task 5 — Seed Data Rollout (Core + Scenario)

Per `README-seed-data.md` §3/§6/§7 — read the DELETE-safety rule (§7) before editing.

### Layer 1 — Core (`seed_core.py`, Group A)
Add the 11 `job_type` platform-default rows (identical to the migration's rows, `tenant_id=NULL`), `INSERT … ON CONFLICT DO NOTHING`. Update `seed`, `show`, and `inspect` modes to include `job_type`. Migration rows and `seed_core.py` rows MUST be identical (seed_core is the schema-restore recovery path).

### Layer 2 — Scenarios (Group D)
- **`seed_scenario_dispatch.py`** (6 jobs): assign varied `priority` (≥1 `emergency`, ≥1 `urgent`, rest `standard`) + `job_type_id` (look up id by `code` at runtime — never hardcode UUID). Idempotent `UPDATE` on the script's owned jobs.
- **`seed_scenario_reporting.py`** (7 completed jobs): assign representative `job_type_id` (Panel Upgrade→`panel_upgrade`, Service Call→`service_call`, Commercial Inspection→`inspection`, Outlet Install→`service_call`, Generator Hookup→`generator_install`, Commercial Rewire→`rewire`, HVAC Coord→`other`) + `priority='standard'`.
- **`seed_scenario_quote_to_cash.py`** (7 sites): set `site_type` — Apex HQ + Metro Office Park → `commercial`; the residences → `residential`. (Dispatch/reporting jobs reference these sites, so `site_type` flows to the board.)

Run + verify:
```bash
python migrations/scripts/seed_core.py --mode inspect | grep -i job_type
python migrations/scripts/seed_scenario_dispatch.py
python migrations/scripts/seed_scenario_reporting.py
python migrations/scripts/seed_scenario_quote_to_cash.py
python -m pytest -m unit --tb=no -q 2>&1 | tail -5   # seed rows must not break tests
```

### schema_manager + README
```bash
python schema_manager.py --help   # then set job_type table + job.priority/job.job_type_id/site.site_type
```
Update `README-seed-data.md` §4 (Group A: `job_type` 11 rows; Group D: priority/job_type/site_type on scenario rows).

---

## Test Requirements

Per `README-adding-tests.md`. New test files: `pytestmark = [pytest.mark.domain_field_operations, pytest.mark.unit]` (jobs/job_type) and `pytest.mark.domain_crm` (site_type). Use `client` fixture, `test_tenant`/`test_job`/`test_site`/`test_customer` fixtures, assert by inserted ID.

Cover:
- **`job_type`**: `GET /job-types` returns platform defaults; a tenant override with the same `code` shadows the platform row (`is_tenant_override=true`); inactive rows excluded. (Create the override row directly in the test via `db_session`.)
- **`job.priority`**: create with `urgent` persists; invalid value → 422 RFC 7807; default `standard` when omitted; CHECK rejects invalid at DB level.
- **`job.job_type_id`**: create with a valid job_type id persists + response carries `job_type_code`/`job_type_label`; null job_type → null labels.
- **`site.site_type`**: create with `industrial` persists; invalid → 422; **omitted → customer-type default** (company customer → `commercial`; person customer → `residential`); CHECK rejects invalid.
- **Dispatch enrichment**: board response entries carry `priority`, `customer_type`, `site_type`, `job_type_code`; a job with a `company` customer + commercial site shows `customer_type='company'`, `site_type='commercial'`.
- **Migration backfill** (integration): existing sites got `site_type` derived from their customer.type; existing jobs got `priority='standard'`.

Domain folders: `tests/domains/field_operations/` (job + job_type) and `tests/domains/crm/` (site).

---

## Final Verification

### Phase 1 — Unit
```bash
cd <repo>/backend && source .venv/bin/activate
python -m pytest -m unit --tb=short -q 2>&1 | tail -10
```

### Phase 2 — Full suite
```bash
cd <repo>/backend && source .venv/bin/activate
python -m pytest --tb=short -q 2>&1 | tail -10
python -m pytest tests/domains/field_operations/ tests/domains/crm/ -q 2>&1 | tail -20
grep -A 4 "job-types" backend/openapi_schema_map.md
echo "=== CLASS-B1 FINAL VERIFICATION COMPLETE ==="
```
Any failure in either phase must be fixed before done. Root cause unclear → STOP and ask Tom.

---

## Definition of Done

- [ ] Regression baseline captured (`pytest -m unit`); zero pre-existing failures (or confirmed with Tom)
- [ ] All 8 MCP pre-work queries run; trigger DDL from query 5 used verbatim for `job_type`
- [ ] All mandatory source files read (including `api/schemas/schemas.py` + the 3 seed scripts + `README-seed-data.md`)
- [ ] **Task 1**: `JobType` model + `Job.priority`/`Job.job_type_id` + `Site.site_type` fields
- [ ] **Task 2**: blank migration — job.priority (3-part), job_type table+triggers+partial indexes+11 platform rows, job.job_type_id FK, site.site_type (3-part, customer-derived backfill); triple-verify upgrade/downgrade/upgrade passes
- [ ] `generate_db_model_map.py` run — `JobType` appears under DB Tables
- [ ] **Task 3**: schemas updated (Job/Site create/update/response, JobTypeResponse, DispatchBoardJobEntry + customer type confirmed)
- [ ] **Task 4**: `GET /job-types` (+ `/test`) with tenant-override resolution; job priority/job_type wired; site_type wired with customer-type default; dispatch enrichment (no N+1); `set_audit_context_sync` on all mutations; RFC 7807 on invalid values
- [ ] `export_openapi_json.py` run — `job-types` + new fields in `openapi_schema_map.md`
- [ ] **Task 5 (Layer 1)**: `seed_core.py` job_type defaults (identical to migration) in seed/show/inspect
- [ ] **Task 5 (Layer 2)**: dispatch (varied priority + job_type), reporting (job_type), quote_to_cash (site_type) scenarios assigned; idempotent; FK looked up by code at runtime
- [ ] `schema_manager.py` updated (job_type + 3 columns); `README-seed-data.md` §4 updated
- [ ] New tests use domain marker + `pytest.mark.unit`, `client` fixture, no hardcoded UUIDs, assert-by-ID
- [ ] **Phase 1** unit pass; **Phase 2** full suite pass (both zero failures)
- [ ] Final test count (before → after) documented
- [ ] Completion Summary added to launch plan Appendix B; README-seed-data §4/§10 headers updated

---

## Completion Summary

Add to `pilot-launch-plan.md` Appendix B (Python template). Handoff note MUST state:

> CLASS-B1 complete. Run `pnpm sync-api-types` before any FE companion. New contract: `job.priority` (standard/urgent/emergency), `job.job_type_id` + `GET /api/v1/job-types`, `site.site_type` (commercial/residential/industrial, customer-type default on create), `customer.type` surfaced (person/company). `DispatchBoardJobEntry` now returns real `priority`/`customer_type`/`site_type`/`job_type_code`/`job_type_label` — DISPATCH-B3 must delete the hardcoded `normalizeJob` fallbacks. Seed data (core + scenarios) carries varied values.

Then update README-seed-data.md §4 (Group A `job_type`; Group D new fields) and §10 if it tracks this batch.
