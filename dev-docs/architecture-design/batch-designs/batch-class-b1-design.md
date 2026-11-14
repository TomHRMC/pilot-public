# Batch Design: CLASS-B1 — Job/Site/Customer Classification Foundation

**Batch**: CLASS-B1
**Type**: Backend-only (`backend/`) — schema foundation + dispatch enrichment + seed rollout
**Engineer**: Pilot Python Engineer
**Author**: Pilot Architect
**Date**: 2026-07-27
**Status**: Ready for Tom review → Python Engineer
**Source plan**: `pilot-launch-plan.md §2.3`
**Decisions**: Tom-approved 2026-07-27 (chat) — see §G
**Frontend companions**: JOB-UI-B1, CUST-UI-B1, DISPATCH-B3 (all depend on this + `pnpm sync-api-types`)

> **Origin**: Dispatch-board testing found the Priority and Customer-Type filters non-functional. Root-cause investigation (MCP-verified 2026-07-27) revealed neither dimension had proper backing schema: `job` has **no** priority column at all, and the dispatch frontend's `commercial/residential` "customer type" does not exist — the real `customer.type` is `person`/`company`. Tom untangled a conflated concept: `rush/standard/warranty` mixed **priority** (urgency) with **job type** (kind of work). This batch establishes the correct schema for all four classification dimensions.

---

## A. Input Read Summary

| Input | Why | Key takeaway (MCP-verified 2026-07-27) |
|---|---|---|
| `postgres-local` MCP — `job` columns | Confirm priority absence | `job` has **no** priority/type column. Has `status_id` FK, `version` (int, optimistic lock), `job_number`, `customer_id`, `site_id`. |
| MCP — `customer` columns + constraints | Confirm real type field | `customer.type` = TEXT, `CHECK (type IN ('person','company'))` (`customer_type_chk`), default `'person'`, NOT NULL. Live data: 8 person / 3 company. |
| MCP — `site` columns | Confirm no type + FK for backfill | `site` has `customer_id` FK (NOT NULL), `name`, `jurisdiction_code`; **no** type column. |
| MCP — trigger functions | Trigger names for new table | Available: `set_updated_at`, `log_changes` (audit), `guard_created_fields_immutable`. Confirmed on `customer`: `audit_customer_changes`→`log_changes`, `trg_customer_set_updated_at`→`set_updated_at`, `trg_customer_guard_created_immutable`→`guard_created_fields_immutable`. |
| MCP — table existence | Confirm clean slate | `job_type`, `job_priority`, `site_type` tables do **not** exist. |
| MCP — alembic head | Migration base | `57475453234c`. |
| `crm.py` `Customer`/`Site` | Model patterns | `StandardAuditMixin`; TEXT+CHECK via `CheckConstraint` in `__table_args__`; `server_default=text("'...'")`. |
| `fulfillment.py` `Job` | Model pattern | `StandardAuditMixin`; nullable FK pattern (`quote_id`, `recurrence_rule_id` with `ondelete`). |
| `migrations/versions/…phase_4_7_enum_to_text_customer_type` | ENUM policy precedent | The codebase **deliberately migrated `customer.type` from PG ENUM → TEXT+CHECK**. New classification columns follow TEXT+CHECK — NOT PG ENUM. |
| `README-seed-data.md` | Seed rollout targets | Group A = `seed_core.py` (platform lookups); Group D = `seed_scenario_dispatch.py` / `_reporting.py` / `_quote_to_cash.py` (jobs + sites). New standing rule: schema changes roll into BOTH core defaults AND scenarios. |
| `python-engr-std-prompt-inclusions.md` | Prompt standard | Blank migrations, 3-part NOT NULL pattern, `/test` endpoints, schema_manager + openapi + model-map regen. |

---

## B. Migration Plan

**One Alembic migration** (blank, per Rule 4). Base revision `57475453234c`. Four logical groups. Full upgrade + downgrade + upgrade cycle required.

### B.1 — `job.priority` (TEXT + CHECK, 3-part NOT NULL)

`job` has existing rows → 3-part pattern:

1. **Add nullable**: `ALTER TABLE job ADD COLUMN priority TEXT;`
2. **Backfill**: `UPDATE job SET priority = 'standard' WHERE priority IS NULL;`
3. **Lock**: set `NOT NULL` + `server_default 'standard'` + add CHECK:
   ```sql
   ALTER TABLE job ALTER COLUMN priority SET DEFAULT 'standard';
   ALTER TABLE job ALTER COLUMN priority SET NOT NULL;
   ALTER TABLE job ADD CONSTRAINT job_priority_chk
     CHECK (priority IN ('standard','urgent','emergency'));
   ```

### B.2 — `job_type` lookup table (tenant-override-capable) + `job.job_type_id` FK

**New table `job_type`** — null `tenant_id` = platform default; non-null = tenant override.

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | uuid PK | NO | `default_factory=uuid.uuid4` |
| `tenant_id` | uuid FK→`tenant.id` ON DELETE RESTRICT | **YES** | NULL = platform default row |
| `code` | text | NO | stable machine key (e.g. `panel_upgrade`) |
| `label` | text | NO | display label (e.g. `Panel Upgrade`) |
| `sort_order` | int | NO | server_default `100`; UI ordering |
| `is_active` | boolean | NO | server_default `true` |
| + `StandardAuditMixin` | `created_at/updated_at/created_by/updated_by` | | |

**Uniqueness (partial indexes — NULLs are distinct in plain unique constraints, so two partials are required):**
```sql
CREATE UNIQUE INDEX uq_job_type_platform_code
  ON job_type (code) WHERE tenant_id IS NULL;
CREATE UNIQUE INDEX uq_job_type_tenant_code
  ON job_type (tenant_id, code) WHERE tenant_id IS NOT NULL;
CREATE INDEX ix_job_type_tenant_id ON job_type (tenant_id);
```

**Triggers on `job_type`** (mirror `customer`):
```sql
CREATE TRIGGER trg_job_type_set_updated_at BEFORE UPDATE ON job_type
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER audit_job_type_changes AFTER INSERT OR UPDATE OR DELETE ON job_type
  FOR EACH ROW EXECUTE FUNCTION log_changes();
CREATE TRIGGER trg_job_type_guard_created_immutable BEFORE UPDATE ON job_type
  FOR EACH ROW EXECUTE FUNCTION guard_created_fields_immutable();
```
> **Engineer**: before writing these, MCP-verify the exact trigger DDL on `customer` (`SELECT tgname, pg_get_triggerdef(oid) FROM pg_trigger WHERE tgrelid='public.customer'::regclass AND NOT tgisinternal`) and mirror argument style exactly.

**`job.job_type_id`** — nullable FK (job type is optional):
```sql
ALTER TABLE job ADD COLUMN job_type_id uuid
  REFERENCES job_type(id) ON DELETE SET NULL;
CREATE INDEX ix_job_job_type_id ON job (job_type_id);
```
Nullable — no backfill needed (existing jobs have no type; UI/optional).

**Platform-default seed rows** (inserted in the migration with `ON CONFLICT DO NOTHING`, `tenant_id = NULL`; also mirrored in `seed_core.py` — see §F). Electrical MVP taxonomy (Tom-approved list, refine labels as needed):

| code | label | sort |
|---|---|---|
| `service_call` | Service Call | 10 |
| `troubleshoot` | Troubleshoot / Diagnostic | 20 |
| `panel_upgrade` | Panel Upgrade | 30 |
| `rewire` | Rewire | 40 |
| `lighting` | Lighting | 50 |
| `generator_install` | Generator Install | 60 |
| `ev_charger_install` | EV Charger Install | 70 |
| `new_construction` | New Construction | 80 |
| `inspection` | Inspection | 90 |
| `warranty` | Warranty | 100 |
| `other` | Other | 999 |

> Migration INSERT must set `created_at, updated_at = NOW(), NOW()` explicitly (`StandardAuditMixin` has no server default — README §7).

### B.3 — `site.site_type` (TEXT + CHECK, 3-part NOT NULL, backfilled from customer)

`site` has existing rows → 3-part pattern with **customer-type-derived backfill**:

1. **Add nullable**: `ALTER TABLE site ADD COLUMN site_type TEXT;`
2. **Backfill from owning customer** (company→commercial, else residential):
   ```sql
   UPDATE site s SET site_type = CASE
     WHEN c.type = 'company' THEN 'commercial' ELSE 'residential' END
   FROM customer c WHERE s.customer_id = c.id AND s.site_type IS NULL;
   -- safety net for any orphan (FK is NOT NULL, so unlikely):
   UPDATE site SET site_type = 'residential' WHERE site_type IS NULL;
   ```
3. **Lock**: `server_default 'residential'` + `NOT NULL` + CHECK:
   ```sql
   ALTER TABLE site ALTER COLUMN site_type SET DEFAULT 'residential';
   ALTER TABLE site ALTER COLUMN site_type SET NOT NULL;
   ALTER TABLE site ADD CONSTRAINT site_type_chk
     CHECK (site_type IN ('commercial','residential','industrial'));
   ```
> The **create-form default logic** (company→commercial, person→residential) is applied at the **API/frontend layer** (CUST-UI-B1), not the DB. The DB server default is the neutral `'residential'`; the API `SiteCreate` handler computes the customer-type-aware default when `site_type` is omitted.

### B.4 — Downgrade

Exact reverse: drop `site_type_chk` + column; drop `job.job_type_id` FK+index+column; drop `job_type` triggers + partial indexes + table; drop `job_priority_chk` + column. (Platform seed rows vanish with the table.)

### B.5 — Post-migration required steps
- `alembic upgrade head → downgrade -1 → upgrade head` (triple-verify).
- `python generate_db_model_map.py` (new `JobType` model + `Job`/`Site` field changes).
- `python schema_manager.py` CRUD to record `job_type` table + `job.priority`/`job.job_type_id`/`site.site_type` columns in the master JSON.
- `python export_openapi_json.py` (schemas + new `job_type` list endpoint).

---

## C. Execution Order

| # | Step | Files |
|---|---|---|
| 1 | Models: `JobType` (new) in `fulfillment.py`; `Job.priority` + `Job.job_type_id` fields; `Site.site_type` field | `app/models/fulfillment.py`, `app/models/crm.py` |
| 2 | Alembic migration (§B, all 4 groups + platform seed rows) | `migrations/versions/…class_b1_classification.py` |
| 3 | Run migration triple-verify; `generate_db_model_map.py` | — |
| 4 | Pydantic schemas: add fields to `JobCreate/JobUpdate/JobResponse`, `SiteCreate/SiteUpdate/SiteResponse`; confirm `CustomerResponse.type` already surfaces; new `JobTypeResponse` | `api/schemas/schemas.py` |
| 5 | API: `GET /api/v1/job-types` (list active platform+tenant, tenant overrides win) + `/test`; wire `priority`/`job_type_id` into job create/update + `list_jobs` projection; wire `site_type` into site create/update (+ customer-type default) + site list/detail projection; enrich `DispatchBoardJobEntry` with `priority`, `customer_type`, `site_type`, `job_type_code`/`job_type_label` | `api/routes/jobs.py`, `api/routes/*sites*`, `api/routes/scheduling.py`, new `api/routes/job_types.py` |
| 6 | Seed — Group A: `seed_core.py` platform `job_type` defaults (idempotent, matches migration) | `migrations/scripts/seed_core.py` |
| 7 | Seed — Group D: assign `priority` + `job_type_id` to scenario jobs; `site_type` to scenario sites | `seed_scenario_dispatch.py`, `seed_scenario_reporting.py`, `seed_scenario_quote_to_cash.py` |
| 8 | `export_openapi_json.py`; `schema_manager.py`; tests | — |

---

## D. New API Endpoints

### `GET /api/v1/job-types`
- **Auth**: authenticated; **RBAC**: `jobs.view` (any tenant role that can see jobs). No `feature_code` gate.
- **Returns**: `list[JobTypeResponse]` = active platform defaults (`tenant_id IS NULL`) **unioned with** the tenant's own rows, with **tenant rows overriding platform rows on matching `code`** (tenant `code` shadows the platform `code`). Sorted by `sort_order, label`.
- **`/test` counterpart**: `GET /api/v1/job-types/test` via `TestUserContext`.

```
JobTypeResponse: { id: UUID, code: str, label: str, sort_order: int, is_active: bool, is_tenant_override: bool }
```

> **Resolution rule** (implement in a shared `_list_job_types_impl`): fetch platform rows (tenant NULL) + tenant rows; build a dict keyed by `code`, tenant row wins; return active only. `is_tenant_override=true` when the winning row has non-null `tenant_id`.

**No new create/edit endpoints for job_type in this batch** — tenant override management UI is future scope (Tom: "read-only for now" on job type). Platform defaults + the schema for tenant overrides land now; the override-editing surface is deferred.

### Modified endpoints (fields added — no new routes)
- `POST/PATCH /api/v1/jobs` + `/test`: accept `priority`, `job_type_id`. `priority` validated by CHECK (invalid → RFC 7807 422). Job create defaults `priority='standard'` when omitted.
- `GET /api/v1/jobs` (`list_jobs`) + `GET /api/v1/jobs/{id}`: project `priority`, `job_type_id`, `job_type_code`, `job_type_label`.
- `POST/PATCH /api/v1/sites` + `/test`: accept `site_type`. On create, when `site_type` omitted → default from owning customer (`company`→`commercial`, else `residential`).
- `GET` sites (customer sites list + detail): project `site_type`.
- `GET /api/v1/scheduling/dispatch-board`: `DispatchBoardJobEntry` gains `priority`, `customer_type`, `site_type`, `job_type_code`, `job_type_label` (batch-load pattern — see §F).

---

## E. Pattern Reuse Decisions

| Pattern | Applies | How |
|---|---|---|
| TEXT + CHECK (not PG ENUM) | ✅ | `job.priority`, `site.site_type` — matches the `customer.type` phase_4_7 precedent. |
| 3-part NOT NULL migration (methods §13 / inclusions §5) | ✅ | `job.priority` + `site.site_type` (both on tables with existing rows). |
| Nullable-tenant lookup with partial unique indexes | ✅ | `job_type` — platform default (NULL tenant) + tenant override, two partial unique indexes. |
| Mandatory triggers on new table (audit/updated_at/immutable) | ✅ | `job_type` mirrors `customer` trigger set. |
| Batch-load enrichment (anti-N+1) — DISPATCH-B1 pattern | ✅ | Dispatch-board enrichment loads customer.type + site.site_type + job_type label via set-based queries keyed by id, exactly like B1's `customer_name`/`site_address`. |
| `/test` endpoint for new entity (inclusions §11) | ✅ | `GET /api/v1/job-types/test`. |
| Seed core + scenario dual rollout (NEW standing rule) | ✅ | §F — platform defaults in `seed_core.py`; scenario assignment in Group D scripts. |
| `db.get()` ban | ✅ | All new lookups tenant-scoped `select()`. |

---

## F. Shared Interfaces, Enrichment & Seed Rollout

### F.1 Dispatch-board enrichment (in `_dispatch_board_impl`)
Extend the existing batch-load block (B1 added `customer_name`/`site_address`; B1.5 added `site_name`). Add:
- `job.priority` — already on the job row being iterated (no extra query).
- `customer_type` — from the customer batch-load already running for `customer_name` (add `Customer.type` to the selected columns; key by `customer_id`).
- `site_type` — from the site batch-load already running for `site_name`/`site_address` (add `Site.site_type`).
- `job_type_code` + `job_type_label` — one batched query: `SELECT id, code, label FROM job_type WHERE id IN (:job_type_ids)`; key by `job_type_id`; null-safe when `job.job_type_id IS NULL`.

`DispatchBoardJobEntry` new fields (all with safe defaults for forward-compat): `priority: str = "standard"`, `customer_type: str | None = None`, `site_type: str | None = None`, `job_type_code: str | None = None`, `job_type_label: str | None = None`.

### F.2 Seed rollout — **BOTH core defaults AND scenarios** (Tom's standing requirement)

**Group A — `seed_core.py`** (platform/core values, idempotent recovery tool):
- Add `job_type` platform-default rows (the 11-row taxonomy from §B.2), `tenant_id = NULL`, `INSERT … ON CONFLICT DO NOTHING` keyed on the platform partial-unique (`code` where tenant NULL). Add to the script's `seed`, `show`, and `inspect` modes.
- **The migration seeds these too** (so a fresh `alembic upgrade` has them); `seed_core.py` is the post-schema-restore recovery path. Both must produce identical rows.

**Group D — scenario scripts** (assign the new fields to existing scenario data):
- `seed_scenario_dispatch.py` (6 jobs): assign a mix of `priority` (e.g. 1 `emergency`, 1 `urgent`, rest `standard`) and `job_type_id` (look up by code at runtime — never hardcode the UUID, per README pricebook rule) so the dispatch filters have varied data to exercise. Value-scoped `mode_seed` updates only.
- `seed_scenario_reporting.py` (7 completed jobs): assign representative `job_type_id` per job (Panel Upgrade→`panel_upgrade`, Service Call→`service_call`, Commercial Inspection→`inspection`, etc.) + `priority='standard'`.
- `seed_scenario_quote_to_cash.py`: set `site_type` on the 7 seeded sites (commercial for Apex HQ / Metro Office Park; residential for the homes). The dispatch/reporting jobs reference these sites, so `site_type` flows to the board.
- Assignment must be **idempotent** and follow the DELETE-safety rule (README §7) — these are `UPDATE`s on rows the script already owns, keyed by the scenario's business keys.

> **Verification**: after seeding, `seed_core.py --mode inspect` shows 11 `job_type` platform rows; dispatch board response for the scenario tenant returns non-uniform `priority`/`customer_type`/`site_type`/`job_type_*`.

### F.3 No Celery tasks. No new background jobs.

---

## G. Open Questions Resolved

| Q | Resolution (Tom 2026-07-27) |
|---|---|
| ENUM vs TEXT+CHECK | **TEXT + CHECK** — matches the deliberate `customer.type` phase_4_7 ENUM→TEXT migration. Adding a value later = trivial constraint swap. |
| Customer type labels | Keep **`person`/`company`** (already in DB). The dispatch "Commercial/Residential customer type" was a frontend fiction — DISPATCH-B3 relabels the filter to person/company. |
| Priority vs job type conflation | **Split into two fields.** `job.priority` (urgency) = `standard`/`urgent`/`emergency`. `job_type` (kind of work) = lookup table. `warranty` moves from "priority" to a job_type. |
| Priority values | `standard` (default) · `urgent` · `emergency`. **(Tom 2026-07-27: `urgent` chosen over `rush` — cleaner severity ladder, pairs with `emergency`, industry-standard.)** |
| site_type values | `commercial` · `residential` · `industrial`. |
| site_type default | DB server default `'residential'`; **API create default is customer-type-aware** (company→commercial, person→residential) when omitted. |
| job_type storage | Lookup table with tenant overrides (null-tenant = platform default). Override-editing UI deferred; platform defaults seeded now. |
| Where do the classification concepts live | `priority` + `job_type` on **job**; `type` on **customer** (exists); `site_type` on **site**. `residential/commercial/industrial` is a property of the **site**, not the customer — a `person` can own commercial premises. |
| Seed strategy | **Both** core platform defaults (`seed_core.py` + migration) **and** scenario assignment (Group D). New standing rule added to `python-engr-std-prompt-inclusions.md`. |

---

## Handoff

CLASS-B1 (this doc) → Python Engineer first. On completion + `pnpm sync-api-types`, the three FE batches proceed independently:
- **JOB-UI-B1** consumes `job.priority`, `job.job_type_id`, `GET /job-types`, `job.title` (title is JOB-UI-B1's own scope).
- **CUST-UI-B1** consumes `customer.type` (display) + `site.site_type` (dropdown + customer-type default).
- **DISPATCH-B3** consumes the enriched `DispatchBoardJobEntry` (kills hardcoded `normalizeJob` fallbacks; repairs the 3 filters; adds read-only panel chips).

*Authored by Pilot Architect, 2026-07-27. All schema facts MCP-verified against live `pilot_dev` (alembic head `57475453234c`). No PG ENUMs — TEXT+CHECK per the customer.type precedent.*
