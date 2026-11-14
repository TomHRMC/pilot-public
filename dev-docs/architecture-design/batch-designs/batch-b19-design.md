# Batch B19 Design — Human-Readable IDs, JobResponse Enrichment, Profitability Job Labels, Seed Invoices, QB intuit_tid

**Batch Code**: B19  
**Type**: Backend only  
**Date**: 2026-07-11  
**Author**: Pilot Architect  
**Status**: Ready for implementation  
**Priority**: P1 — unblocks FE-B26 (UUID display bugs) and FE-B27 (quote_number display)  
**Source Issue**: `dev-docs/testing-support/alpha-testing/ui-testing-status-2026-07-10-v2.md`  
**Launch plan section**: `dev-docs/analysis/pilot-launch-plan.md` §Phase 1 Batch #1

---

## A. Input Read Summary

| Input | What Was Verified |
|---|---|
| `ui-testing-status-2026-07-10-v2.md` | `job_number` missing from `job` table (UUID shown in breadcrumb, status badge, reports DrillDown). `quote_number` and `quote.title` missing from `quote` table. `JobResponse` missing `status_code`, `site_name`, `customer_name`. Profitability `group_label` for `group_by=job` is UUID string `COALESCE(j.id::text, '')`. Seed invoices missing from reporting scenario. QB `intuit_tid` not captured. |
| MCP live DB — `job` table | Confirmed: NO `job_number` column. Columns: `id`, `tenant_id`, `quote_id`, `quote_version_id`, `customer_id`, `site_id`, `status_id`, `scheduled_start_at`, `scheduled_end_at`, `actual_labor_cost_cents`, `actual_material_cost_cents`, `actual_profit_cents`, `is_active`, `estimated_duration_minutes`, `external_calendar_event_id`, `version`, `variance_owner_notified_at`, `variance_last_notified_pct` |
| MCP live DB — `quote` table | Confirmed: NO `quote_number`, NO `title` columns. Has: `id`, `tenant_id`, `customer_id`, `site_id`, `status_id`, `subtotal_cents`, `tax_cents`, `total_cents`, `currency`, `idempotency_key`, `is_active`, `submitted_by_user_id`, `submitted_at`, `approved_by_user_id`, `approved_at`, `discount_pct`, `discount_amount_cents`, `discount_expires_at`, `customer_acceptance_comment`, `customer_accepted_at`, `expires_at`, etc. |
| MCP live DB — `job_status` table | Confirmed: has `code` column (e.g. `draft`, `scheduled`, `in_progress`, `completed`, `cancelled`) and `is_terminal` boolean. `is_terminal` is already accurate per live data. |
| MCP live DB — `invoice` table | Confirmed: `invoice_number VARCHAR NOT NULL` already exists — pattern reference for `job_number` and `quote_number` generation. |
| `backend/api/routes/invoices.py` | `_generate_invoice_number()` function confirmed at line 68 — format `INV-{YYYYMMDD}-{6HEX}`. This is the pattern to replicate for `job_number` (`JOB-`) and `quote_number` (`Q-`). |
| `backend/services/report_service.py` | Profitability query confirmed: when `group_by == "job"`, `group_label = COALESCE(j.id::text, '')` — this is the UUID bug. Fix: use `COALESCE(j.job_number, j.id::text)` for `group_label`. `customer_name` not currently selected — add `c.display_name AS customer_name` via existing `customer c` JOIN (already present in profitability query for other group modes). |
| `backend/migrations/scripts/seed_scenario_reporting.py` | Confirmed: 4 completed jobs, no invoices. Jobs: Panel Upgrade (30 days ago), Service Call (45 days ago), Commercial Inspection (60 days ago), Outlet Installation (15 days ago). `mode_reset()` deletes jobs, time entries, expenses but NOT invoices. `mode_inspect()` shows job counts. |
| `backend/services/quickbooks_sync.py` (context) | QB API calls made via `requests` — response headers contain `intuit_tid`. Not currently captured or logged. One-line addition per API response. |

---

## B. Migration Plan

**Two Alembic migrations required.** Both add new columns to existing tables.

### Migration 1: Add `job_number` to `job` table

3-part NOT NULL pattern (existing rows must be backfilled before constraint applied):

- **Part 1**: Add `job_number VARCHAR(30) NULLABLE` to `job`
- **Part 2**: Backfill existing rows with `JOB-{created_at date}-{id[:6].upper()}` via `op.execute()`
- **Part 3**: Set `NOT NULL` + add `UNIQUE` constraint on `(tenant_id, job_number)` — **not a global unique**, tenant-scoped

**Number format decision (2026-07-11 final)**: All entity numbers use a **sequential numeric format with 3-letter prefix** — no dates, no hex. Clean, professional, and easy to reference verbally.

| Entity | Format | Example | Counter |
|---|---|---|---|
| Job | `JOB-000001` | `JOB-000042` | Tenant-scoped, sequential, zero-padded 6 digits |
| Quote | `QUO-000001` | `QUO-000017` | Tenant-scoped, sequential, zero-padded 6 digits |
| Invoice | `INV-000001` | `INV-000089` | Tenant-scoped, sequential — **existing `_generate_invoice_number()` must also be updated** |

The invoice format change (`INV-YYYYMMDD-XXXXXX` → `INV-000001`) is included in this batch to achieve consistency. Existing seed invoice rows from `seed_scenario_reporting.py` will use the new format.

**Implementation pattern** (replaces random hex generation): Use `SELECT MAX(numeric portion) + 1 WHERE tenant_id = :tid` with a unique constraint on `(tenant_id, job_number)` to catch race conditions. Retry on unique violation. At small contractor scale (< 100 concurrent sessions) this is safe and simple.

```sql
-- Part 2 backfill for job_number (sequential per tenant, ordered by created_at)
UPDATE job j
SET job_number = 'JOB-' || LPAD(rn.row_num::text, 6, '0')
FROM (
    SELECT id, ROW_NUMBER() OVER (PARTITION BY tenant_id ORDER BY created_at) AS row_num
    FROM job
) rn
WHERE j.id = rn.id
AND j.job_number IS NULL;
```

### Migration 2: Add `quote_number` + `title` to `quote` table

- **`quote_number`**: 3-part NOT NULL pattern — sequential format `QUO-000001`. Note `QUO-` prefix (3-letter, consistent with `INV-` and `JOB-`).
- **`title`**: Add as `VARCHAR(255) NULLABLE` — no backfill needed, no NOT NULL constraint

```sql
-- quote_number backfill (sequential per tenant, ordered by created_at)
UPDATE quote q
SET quote_number = 'QUO-' || LPAD(rn.row_num::text, 6, '0')
FROM (
    SELECT id, ROW_NUMBER() OVER (PARTITION BY tenant_id ORDER BY created_at) AS row_num
    FROM quote
) rn
WHERE q.id = rn.id
AND q.quote_number IS NULL;
```

**Pre-Migration MCP Verification Queries (engineer must run before writing any code):**

```sql
-- 1. Confirm job_number does NOT exist on job table
SELECT column_name FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'job' AND column_name = 'job_number';

-- 2. Confirm quote_number and title do NOT exist on quote table
SELECT column_name FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'quote'
AND column_name IN ('quote_number', 'title');

-- 3. Verify job_status.code exists and get values
SELECT code, is_terminal FROM job_status WHERE tenant_id IS NULL ORDER BY code;

-- 4. Verify site.name column exists (for JobResponse JOIN)
SELECT column_name, data_type FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'site' AND column_name = 'name';

-- 5. Verify customer.display_name exists (for JobResponse JOIN)
SELECT column_name, data_type FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'customer' AND column_name = 'display_name';

-- 6. Confirm invoice_status codes for seed data (draft, issued, paid)
SELECT code, name, is_terminal FROM invoice_status WHERE tenant_id IS NULL ORDER BY code;

-- 7. Confirm current alembic head
SELECT version_num FROM public.alembic_version;
```

---

## C. Execution Order

| Step | Task | File(s) |
|---|---|---|
| 1 | Run MCP verification queries | — |
| 2 | Read all mandatory source files | See §Pre-Work in prompt |
| 3 | Migration 1 — `job_number` to `job` table | `backend/migrations/versions/YYYY_MM_DD_-b19_add_job_number_to_job.py` |
| 4 | Migration 2 — `quote_number` + `title` to `quote` table | `backend/migrations/versions/YYYY_MM_DD_-b19_add_quote_number_title_to_quote.py` |
| 5 | Add `_generate_job_number()` to `jobs.py`; update `Job` SQLModel; auto-generate in `_create_job_impl()` | `backend/app/models/field_ops.py` (or wherever `Job` lives), `backend/api/routes/jobs.py` |
| 6 | Add `job_number: str` to `JobResponse` + `JobListItem` in schemas | `backend/api/schemas/schemas.py` |
| 7 | Add `_generate_quote_number()` to `quotes.py`; update `Quote` SQLModel; auto-generate in `_create_quote_impl()` | `backend/app/models/sales.py` (or wherever `Quote` lives), `backend/api/routes/quotes.py` |
| 8 | Add `quote_number: str` + `title: str \| None` to `QuoteCreate`, `QuoteResponse`, `QuoteListItem` schemas | `backend/api/schemas/schemas.py` |
| 9 | Add `status_code`, `site_name`, `customer_name` to `JobResponse` — update `_get_job_impl()` to JOIN `job_status`, `site`, `customer` | `backend/api/routes/jobs.py`, `backend/api/schemas/schemas.py` |
| 10 | **Phase 1 unit test checkpoint** | `pytest -m unit --tb=short -q \| tail -10` |
| 11 | Update `get_profitability_report()` job `group_by` case — `group_label` uses `job_number`; add `customer_name` to result row; update `ProfitabilityReportRow` schema | `backend/services/report_service.py`, `backend/api/schemas/schemas.py` |
| 12 | Update `seed_scenario_reporting.py` — add invoices + payments; update `mode_reset()` + `mode_inspect()` | `backend/migrations/scripts/seed_scenario_reporting.py` |
| 13 | Add `intuit_tid` logging to QuickBooks sync service | `backend/services/quickbooks_sync.py` |
| 14 | Write all tests for new functionality | `backend/tests/domains/field_operations/`, `backend/tests/domains/sales_quoting/`, `backend/tests/domains/platform_infrastructure/` |
| 15 | **Phase 1 unit test checkpoint** (final pre-full-suite check) | `pytest -m unit --tb=short -q \| tail -10` |
| 16 | `python export_openapi_json.py` | — |
| 17 | `python generate_db_model_map.py` | — |
| 18 | `python schema_manager.py --help` then appropriate CRUD command | — | CRUD script — run `--help` first to see available commands |
| 19 | **Phase 2 full suite** | `pytest --tb=short -q \| tail -10` |

---

## D. New API Endpoints / Schema Changes

No new API endpoints are added in B19. All changes are to existing endpoint response shapes and internal service logic.

### D1. `JobResponse` — added fields

| Field | Type | Source |
|---|---|---|
| `job_number` | `str` | `job.job_number` (new column) |
| `status_code` | `str \| None` | `job_status.code` via JOIN on `job.status_id = job_status.id` |
| `site_name` | `str \| None` | `site.name` via JOIN on `job.site_id = site.id` |
| `customer_name` | `str \| None` | `customer.display_name` via JOIN on `job.customer_id = customer.id` |

**Implementation note**: The `_get_job_impl()` function in `jobs.py` currently fetches the `Job` row directly. It must be updated to JOIN these three related tables and return enriched data. Use `LEFT JOIN` for all three new fields (site/customer/status could in theory be NULL in edge cases) — `str | None` is the correct type.

### D2. `JobListItem` — added field

| Field | Type | Source |
|---|---|---|
| `job_number` | `str \| None` | `job.job_number` (already JOINed in list query — just add to SELECT) |

### D3. `QuoteResponse` and `QuoteListItem` — added fields

| Field | Type | Source |
|---|---|---|
| `quote_number` | `str` | `quote.quote_number` (new column) |
| `title` | `str \| None` | `quote.title` (new nullable column) |

### D4. `QuoteCreate` — added field

| Field | Type | Notes |
|---|---|---|
| `title` | `str \| None = None` | Optional — not every quote needs a title at creation |

### D5. `ProfitabilityReportRow` (or equivalent schema) — added field

| Field | Type | Notes |
|---|---|---|
| `customer_name` | `str \| None = None` | Only populated when `group_by=job`; NULL for customer/site group modes |

The existing `group_label` field behavior changes when `group_by=job`: from `COALESCE(j.id::text, '')` (UUID) to `COALESCE(j.job_number, j.id::text)` (job number, fallback to UUID for any rows without a job_number after migration).

---

## E. Pattern Reuse Decisions

| Pattern | Applied Where |
|---|---|
| Sequential `MAX(suffix) + 1` counter | `_generate_job_number()`, `_generate_quote_number()`, updated `_generate_invoice_number()` — all use same tenant-scoped MAX+1 pattern |
| Customer LEFT JOIN in `_list_invoices_impl()` (B18) | Replicate for `_get_job_impl()` — same pattern for `customer.display_name` |
| 3-part NOT NULL migration pattern (B18 design §B context) | Used for both `job_number` and `quote_number` backfill |
| `set_audit_context_sync()` already present in create job/quote routes | No change needed — audit context already set |

---

## F. Shared Module Interfaces

**Final number format (2026-07-11)**: All entity numbers are **sequential, tenant-scoped, zero-padded 6 digits, 3-letter prefix, no date component**.

| Entity | Format | Example | Prefix chars to strip for MAX() |
|---|---|---|---|
| Job | `JOB-000001` | `JOB-000042` | 4 (`JOB-`) |
| Quote | `QUO-000001` | `QUO-000017` | 4 (`QUO-`) |
| Invoice | `INV-000001` | `INV-000089` | 4 (`INV-`) |

### F1. `_generate_job_number(tenant_id: UUID, db: Session) -> str`

Location: `backend/api/routes/jobs.py`

**Format**: `JOB-000001` (sequential, tenant-scoped, zero-padded 6 digits).

```python
def _generate_job_number(tenant_id: UUID, db: Session) -> str:
    """
    Generate a sequential job number for the tenant: JOB-000001, JOB-000002, ...
    Uses MAX(numeric suffix) + 1 scoped to tenant_id.
    Retries up to 5 times on unique constraint violation (race condition guard).
    """
    for _ in range(5):
        # Get the highest existing numeric suffix for this tenant
        result = db.exec(
            text(
                "SELECT COALESCE(MAX(CAST(SUBSTRING(job_number FROM 5) AS INTEGER)), 0) + 1 "
                "FROM job WHERE tenant_id = :tid"
            ),
            {"tid": str(tenant_id)},
        ).first()
        next_num = result[0] if result else 1
        job_number = f"JOB-{str(next_num).zfill(6)}"
        existing = db.exec(
            select(Job).where(
                Job.tenant_id == tenant_id, Job.job_number == job_number
            )
        ).first()
        if not existing:
            return job_number
    raise ValueError("Unable to generate unique job_number after 5 attempts")
```

> **Engineer note**: The exact SQLAlchemy pattern for the raw SQL subquery may differ from the skeleton above. Use whatever raw SQL execution pattern is already established in the file (check existing usages of `text()` or `db.execute()`). The key logic is: `SUBSTRING(job_number FROM 5)` strips the `JOB-` prefix, `CAST ... AS INTEGER` converts the zero-padded number, `COALESCE(MAX(...), 0) + 1` safely handles empty tenant (first job returns 1).

### F2. `_generate_quote_number(tenant_id: UUID, db: Session) -> str`

Location: `backend/api/routes/quotes.py`

**Format**: `QUO-000001` (sequential, tenant-scoped, zero-padded 6 digits). `QUO-` prefix — 3-letter, consistent with `INV-` and `JOB-`. Same pattern as F1 using `SUBSTRING(quote_number FROM 5)` and `Quote` model.

### F3. Update `_generate_invoice_number(tenant_id: UUID, db: Session) -> str`

Location: `backend/api/routes/invoices.py`

**Current format** (replace): `INV-YYYYMMDD-XXXXXX` (random hex, daily date)
**New format**: `INV-000001` (sequential, tenant-scoped, zero-padded 6 digits)

Same pattern as F1/F2 using `SUBSTRING(invoice_number FROM 5)` and `Invoice` model.

> **Existing invoice records**: Records already in the DB (`INV-20260710-XXXXXX` format from seed data) are NOT backfilled by this batch — their old format is preserved as-is. A separate cleanup migration can be done later if needed. Only **new** invoices created after this batch ships will use `INV-000001` format.

---

## G. Open Questions Resolved

| Question | Resolution |
|---|---|
| Should `job_number` be globally unique or tenant-scoped unique? | **Tenant-scoped** — `UNIQUE(tenant_id, job_number)`. Two tenants can both have `JOB-000001`. |
| Should `quote_number` be globally unique or tenant-scoped? | **Tenant-scoped** — same reasoning. `QUO-000001` is per-tenant. |
| What prefix for quote numbers? | **`QUO-`** — 3-letter prefix consistent with `INV-` and `JOB-`. Not `Q-`. |
| What format for all three entity numbers? | **`PREFIX-000001`** (sequential, no date, zero-padded 6 digits). Clean, verbal-reference-friendly, professional on customer-facing invoices. |
| Does `_generate_invoice_number()` need to change? | **Yes** — updated from `INV-YYYYMMDD-XXXXXX` (random hex) to `INV-000001` (sequential). Existing seed records keep their old format; only new records use the new format. |
| Should `title` on `quote` be required at creation? | **No** — `NULLABLE`. Existing quotes have no title, backward compatible. FE-B26 will add the field to the create quote form. |
| Can `job_number` be NULL after migration? | **No** — 3-part NOT NULL pattern ensures backfill before constraint is applied. The constraint is added in Part 3. |
| Does `group_label` change for customer/site profitability groups? | **No** — only changes for `group_by=job`. Customer groups use `c.name`, site groups use `s.name` — these are already human-readable. |
| Should `intuit_tid` be stored in DB or just logged? | **Logged only** — CloudWatch via Python `logging.info()`. No schema change. If Intuit support needs it, it appears in CloudWatch logs for the relevant time range. |
| Which QuickBooks sync calls need `intuit_tid` logging? | All outbound QBO API calls in `quickbooks_sync.py` that receive an HTTP response. Extract from `response.headers.get("intuit_tid")` and log at INFO level alongside the operation name. |
| What invoice statuses to use for seed data? | `draft` (Outlet Installation, 15 days ago), `issued` (Commercial Inspection, 60 days ago — overdue), `paid` (Panel Upgrade 30 days ago, Service Call 45 days ago). MCP confirmed these codes exist in `invoice_status`. |

---

## Seed Invoice Data (Task 12 Reference)

For `seed_scenario_reporting.py` — add after each job's time entries and expenses are inserted:

| Job | Invoice Amount | Status Code | Issue Date | Due Date | Payment? |
|---|---|---|---|---|---|
| Panel Upgrade (30 days ago) | $1,350 total (labor ~$900 + materials $450 w/ markup) — `subtotal_cents=122700`, `tax_cents=9816`, `total_cents=132516` | `paid` | 28 days ago | 14 days ago | ✅ Yes — `paid_amount_cents=132516` |
| Service Call (45 days ago) | $280 total — `subtotal_cents=25000`, `tax_cents=2000`, `total_cents=27000` | `paid` | 43 days ago | 29 days ago | ✅ Yes |
| Commercial Inspection (60 days ago) | $900 total — `subtotal_cents=81818`, `tax_cents=6545`, `total_cents=88363` | `issued` (overdue) | 55 days ago | 25 days ago | ❌ No |
| Outlet Installation (15 days ago) | $240 total — `subtotal_cents=21818`, `tax_cents=1745`, `total_cents=23563` | `draft` | 10 days ago | 20 days from now | ❌ No |

`balance_due_cents` = `total_cents` for `issued` and `draft`; 0 for `paid`.

Payment rows for paid invoices: use `payment_status` code `paid`, `payment_type` code `check` (verify via MCP before inserting).

`mode_reset()` must also `DELETE FROM invoice WHERE job_id IN (seeded_job_ids)` and `DELETE FROM payment WHERE invoice_id IN (seeded_invoice_ids)`.

`mode_inspect()` must show invoice count and status breakdown for each seeded job.
