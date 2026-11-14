# Implementation Prompt: B19 — Human-Readable IDs, JobResponse Enrichment, Profitability Job Labels, Seed Invoices, QB intuit_tid

**Mode**: Pilot Python Engineer  
**Batch**: B19  
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §Phase 1 — Batch #1  
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-b19-design.md`  
**Estimated session**: 3–5 hours  
**Platform**: Backend only (`backend/`)  
**Frontend companion**: FE-B26 (UUID display bugs — depends on B19 completing first)

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`dev-docs/architecture-design/pilot-python-engineer-methods.md`** — §13 (Alembic), §8 (Router Design), §5 (Model Design), §16 (Standard Task Workflow)
- **`backend/tests/README-adding-tests.md`** — full document; this governs all test file structure, domain markers, and fixture rules

**Critical rules for this batch:**

- **Rule 1**: Never guess column names, data types, or table names. Use `postgres-local` MCP to verify every name before use. The MCP pre-work queries below are your safety net — run ALL of them before writing any code. If MCP returns an error → **STOP and ask Tom**.
- **Rule 2**: After any model file change → regenerate `backend/db_models_map.md` via `python generate_db_model_map.py`.
- **Rule 3**: After any endpoint change → run `python export_openapi_json.py` (updates both `openapi.json` and `openapi_schema_map.md`).
- **Rule 4**: All Alembic migrations must be written as **blank** migrations (never `--autogenerate`). Schema changes use raw `op.add_column()`. Backfill uses `op.execute()` with raw SQL.
- **Rule 5**: Never use module-level `TestClient` in any test file. Always use the `client` fixture from `conftest.py`.
- **Rule 6**: `db.get()` is permanently banned on tenant-scoped models. Always use tenant-scoped `select()` with an explicit `WHERE tenant_id = :tid` clause.
- **Rule 7**: The `postgres-local` MCP is for **read-only verification only**. Never use it to INSERT, UPDATE, or DELETE.
- **Rule 8**: All API error responses MUST follow RFC 7807 Problem Details format. Non-standard error shapes break the frontend `<NotificationBanner>` severity routing.
- **Rule 9**: Every mutation endpoint MUST call `set_audit_context_sync(db, user_id=user.id)` before committing. (Note: this batch does NOT add new mutation endpoints — only enriches existing `GET` responses. Rule 9 applies only if you touch any existing mutation.)
- **Rule 11**: If ANY test fails during your work — even a pre-existing failure — **you must fix it before declaring the batch done**.

---

## Pre-Work: Establish Regression Baseline

Before touching any file, capture the current **unit-only** test baseline:

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=no -q 2>&1 | tail -5
```

Record the exact count: **`X passed, Y failed`**.

> If any tests are already failing before you start: Do NOT treat them as "pre-existing" and proceed anyway. Either confirm with Tom that this is a known, accepted failure, OR fix it before touching any batch files.

---

## Pre-Work: Run MCP Verification Queries

Run **all** of these via `postgres-local` MCP before writing any code. If any query returns unexpected results → **STOP and ask Tom**.

> **MCP Usage Rule**: Read-only verification only. Never INSERT, UPDATE, or DELETE via MCP — all data changes go through application code, seed scripts, or Alembic migrations.

```sql
-- 1. Confirm job_number does NOT exist yet on job table
SELECT column_name FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'job' AND column_name = 'job_number';
-- Expected: 0 rows returned

-- 2. Confirm quote_number and title do NOT exist yet on quote table
SELECT column_name FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'quote'
AND column_name IN ('quote_number', 'title');
-- Expected: 0 rows returned

-- 3. Full job table column list — verify before writing any migration or model code
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'job'
ORDER BY ordinal_position;

-- 4. Full quote table column list
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'quote'
ORDER BY ordinal_position;

-- 5. Verify job_status.code values (needed for JobResponse status_code JOIN)
SELECT code, name, is_terminal FROM job_status WHERE tenant_id IS NULL ORDER BY code;
-- Expected: cancelled, completed, draft, in_progress, scheduled

-- 6. Verify site table has 'name' column
SELECT column_name, data_type FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'site' AND column_name = 'name';

-- 7. Verify customer table has 'display_name' column
SELECT column_name, data_type FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'customer' AND column_name = 'display_name';

-- 8. Confirm invoice_status codes for seed data
SELECT code, name, is_terminal FROM invoice_status WHERE tenant_id IS NULL ORDER BY code;
-- Need: draft, issued, paid

-- 9. Confirm payment_status and payment_type codes (for seed payment rows)
SELECT code, name FROM payment_status WHERE tenant_id IS NULL ORDER BY code;
SELECT code, name FROM payment_type WHERE tenant_id IS NULL ORDER BY code;

-- 10. Confirm current alembic head
SELECT version_num FROM public.alembic_version;
```

---

## Pre-Work: Read These Source Files

Use `read_file` on each of these before writing any code:

```
backend/app/models/field_ops.py                   ← Job SQLModel class — understand StandardAuditMixin, existing fields
backend/app/models/sales.py                        ← Quote SQLModel class — understand existing fields
backend/api/routes/jobs.py                         ← Existing job routes — pattern for _get_job_impl(), _create_job_impl(), _generate_* pattern
backend/api/routes/quotes.py                       ← Existing quote routes — pattern for _create_quote_impl()
backend/api/routes/invoices.py lines 60-95         ← _generate_invoice_number() — exact pattern to replicate for job_number and quote_number
backend/api/schemas/schemas.py                     ← JobResponse, JobListItem, QuoteResponse, QuoteListItem, QuoteCreate schemas
backend/services/report_service.py lines 100-200   ← get_profitability_report() — the group_by=job SQL case that produces UUID group_label
backend/migrations/scripts/seed_scenario_reporting.py  ← Full file — understand mode_seed(), mode_reset(), mode_inspect() structure before adding invoice seeding
backend/db_models_map.md                           ← Confirm model names and table mappings before writing imports
```

---

## Background / Context

This batch fixes several related issues discovered during alpha UI testing:

1. **Jobs show UUID instead of a human-readable number** — `job` table has no `job_number` field. The breadcrumb on Job Detail shows `Job 3f4a-...`, the reports profitability drill-down shows UUID labels, and the "Convert to Invoice" button is broken because `isTerminalStatus(uuid)` always returns `false`.

2. **Quotes show UUID instead of a readable number and have no title** — `quote` table has no `quote_number` or `title`. The Quotes list shows raw UUID in the "Quote ID" column.

3. **Job Detail shows UUID for status, site, and customer** — `JobResponse` only returns `status_id` (UUID), `site_id` (UUID), `customer_id` (UUID). The frontend needs `status_code`, `site_name`, and `customer_name` as human-readable fields.

4. **Profitability report drill-down is unreadable** — When `group_by=job`, `group_label = COALESCE(j.id::text, '')` which is a UUID. After this batch adds `job_number`, the label should use it instead. `customer_name` is also missing from per-job rows.

5. **Seed invoices missing** — The reporting scenario has 4 completed jobs but no invoices, making the AR aging widget and invoice list empty in the demo environment.

6. **QB `intuit_tid` not logged** — Intuit recommends logging this header from all QBO API responses for support traceability.

---

## Task 1 — Migration 1: Add `job_number` to `job` table

Create a blank Alembic migration:

```bash
cd <repo>/backend
source .venv/bin/activate
alembic revision -m "b19_add_job_number_to_job"
```

Write the migration using the **3-part NOT NULL pattern**:

**Part 1 — Add nullable column:**
```python
op.add_column('job', sa.Column('job_number', sa.String(30), nullable=True))
```

**Part 2 — Backfill existing rows:**

> **Format decision**: Use `JOB-YYYY-XXXXXX` (annual, not daily). Supports up to 9,999 jobs/year per tenant — right-sized for small electrical contractors. The 6-char hex suffix provides collision resistance within the year.

```python
op.execute("""
    UPDATE job
    SET job_number = 'JOB-' || TO_CHAR(created_at AT TIME ZONE 'UTC', 'YYYY') || '-' || UPPER(SUBSTRING(id::text, 1, 6))
    WHERE job_number IS NULL
""")
```

**Part 3 — Apply NOT NULL constraint and unique index:**
```python
op.alter_column('job', 'job_number', nullable=False)
op.create_index('ix_job_tenant_job_number', 'job', ['tenant_id', 'job_number'], unique=True)
```

**Downgrade:**
```python
op.drop_index('ix_job_tenant_job_number', table_name='job')
op.drop_column('job', 'job_number')
```

**Test the cycle:**
```bash
alembic upgrade head
alembic downgrade -1
alembic upgrade head
alembic current  # must show new revision
```

---

## Task 2 — Migration 2: Add `quote_number` + `title` to `quote` table

```bash
alembic revision -m "b19_add_quote_number_title_to_quote"
```

**`quote_number`** — 3-part NOT NULL pattern. **Format: `QUO-000001`** (sequential, tenant-scoped, 3-letter prefix, zero-padded 6 digits — no date):

```python
# Part 1
op.add_column('quote', sa.Column('quote_number', sa.String(20), nullable=True))

# Part 2 — sequential backfill per tenant, ordered by created_at
op.execute("""
    UPDATE quote q
    SET quote_number = 'QUO-' || LPAD(rn.row_num::text, 6, '0')
    FROM (
        SELECT id, ROW_NUMBER() OVER (PARTITION BY tenant_id ORDER BY created_at) AS row_num
        FROM quote
    ) rn
    WHERE q.id = rn.id
    AND q.quote_number IS NULL
""")

# Part 3
op.alter_column('quote', 'quote_number', nullable=False)
op.create_index('ix_quote_tenant_quote_number', 'quote', ['tenant_id', 'quote_number'], unique=True)
```

**`title`** — simple nullable add (no backfill needed):
```python
op.add_column('quote', sa.Column('title', sa.String(255), nullable=True))
```

**Downgrade:**
```python
op.drop_index('ix_quote_tenant_quote_number', table_name='quote')
op.drop_column('quote', 'quote_number')
op.drop_column('quote', 'title')
```

Test the full cycle: upgrade → downgrade -1 → upgrade.

---

## Task 3 — Add `job_number` to `Job` SQLModel + auto-generate on create

**3a. Update `Job` SQLModel** in `backend/app/models/field_ops.py` (or wherever confirmed by your `read_file`):

```python
job_number: str = Field(sa_column=Column(String(30), nullable=False, index=True))
```

**3b. Add `_generate_job_number()` to `jobs.py`** — sequential `MAX + 1` counter:

> **Format (2026-07-11 final)**: `JOB-000001` — sequential, tenant-scoped, zero-padded 6 digits. No date, no hex.

```python
def _generate_job_number(tenant_id: UUID, db: Session) -> str:
    """
    Generate a sequential job number for the tenant: JOB-000001, JOB-000002, ...
    Uses MAX(numeric suffix) + 1 scoped to tenant_id.
    Retries up to 5 times on unique constraint violation (race condition guard).
    """
    for _ in range(5):
        result = db.exec(
            text(
                "SELECT COALESCE(MAX(CAST(SUBSTRING(job_number FROM 5) AS INTEGER)), 0) + 1 "
                "FROM job WHERE tenant_id = :tid AND job_number LIKE 'JOB-%'"
            ),
            {"tid": str(tenant_id)},
        ).first()
        next_num = result[0] if result else 1
        job_number = f"JOB-{str(next_num).zfill(6)}"  # e.g. JOB-000001
        existing = db.exec(
            select(Job).where(
                Job.tenant_id == tenant_id,
                Job.job_number == job_number,
            )
        ).first()
        if not existing:
            return job_number
    raise ValueError("Unable to generate unique job_number after 5 attempts")
```

> **Engineer note**: `SUBSTRING(job_number FROM 5)` strips the 4-char `JOB-` prefix. Check how `text()` is imported in `jobs.py` — adapt the raw SQL execution to the pattern already used in that file.

**3c. Call `_generate_job_number()` in `_create_job_impl()`** — set `job_number` at creation, exactly as `invoice_number` is set in `_create_invoice_impl()`.

---

## Task 4 — Add `job_number` to `JobResponse` and `JobListItem` schemas

In `backend/api/schemas/schemas.py`:

**`JobResponse`** — add:
```python
job_number: str
status_code: str | None = None
site_name: str | None = None
customer_name: str | None = None
```

**`JobListItem`** — add:
```python
job_number: str | None = None
```

**Update `_get_job_impl()`** in `jobs.py` to JOIN the three related tables and populate the new fields:

```python
# In the job detail query — add JOINs:
# LEFT JOIN job_status js ON js.id = job.status_id
# LEFT JOIN site s ON s.id = job.site_id  
# LEFT JOIN customer c ON c.id = job.customer_id

# Then populate on the returned JobResponse:
response.status_code = js.code if js else None
response.site_name = s.name if s else None
response.customer_name = c.display_name if c else None
```

> The exact implementation depends on how the current `_get_job_impl()` constructs its response — read the file first and adapt. If it uses `db.exec(select(Job).where(...)).first()`, you may need to use a multi-table select or do separate lookups for the JOIN fields.

**Update `_list_jobs_impl()`** to include `job_number` in the list query result. Check whether the current list query already SELECTs from the `job` table directly — if so, `job_number` is automatically available once the column exists on the SQLModel.

---

## Task 5 — Add `quote_number` + `title` to `Quote` SQLModel and schemas

**5a. Update `Quote` SQLModel** in `backend/app/models/sales.py`:

```python
quote_number: str = Field(sa_column=Column(String(30), nullable=False, index=True))
title: str | None = Field(default=None, sa_column=Column(String(255), nullable=True))
```

**5b. Add `_generate_quote_number()` to `quotes.py`** — same sequential `MAX + 1` pattern as `_generate_job_number()`. Use prefix `QUO-` (not `Q-`), `SUBSTRING(quote_number FROM 5)` to strip the 4-char prefix, and format as `f"QUO-{str(next_num).zfill(6)}"`.

**5c. Update `_create_quote_impl()`** — set `quote_number` at creation.

**5d. Update `_generate_invoice_number()` in `invoices.py`** — replace the random hex implementation with the same sequential `MAX + 1` pattern:
- Old format: `INV-YYYYMMDD-XXXXXX` (random hex)
- **New format**: `INV-000001` (sequential, tenant-scoped, zero-padded 6 digits)
- Use `SUBSTRING(invoice_number FROM 5)` to strip the 4-char `INV-` prefix
- Format as `f"INV-{str(next_num).zfill(6)}"`
- **Existing invoice records keep their old format** — no data migration needed for existing rows. Only new invoices created after this batch ships use `INV-000001`.

**5d. Update schemas in `schemas.py`:**

`QuoteCreate` — add:
```python
title: str | None = None
```

`QuoteResponse` — add:
```python
quote_number: str
title: str | None = None
```

`QuoteListItem` — add:
```python
quote_number: str | None = None
title: str | None = None
```

**Run unit tests after this task:**
```bash
python -m pytest -m unit --tb=short -q 2>&1 | tail -10
```

---

## Task 6 — Fix Profitability Report: job `group_label` + add `customer_name`

In `backend/services/report_service.py`, find the `get_profitability_report()` function. When `group_by == "job"`, the current code is:

```python
# CURRENT (broken — returns UUID):
group_select = "j.id::text AS group_key, COALESCE(j.id::text, '') AS group_label"
group_clause = "..."
```

**Fix:**
```python
# FIXED — uses job_number; falls back to UUID for any rows without job_number
group_select = (
    "j.id::text AS group_key, "
    "COALESCE(j.job_number, j.id::text) AS group_label, "
    "c.display_name AS customer_name"
)
```

Also verify the `job` query JOINs the `customer` table (`c`) — for customer and site group modes it does; confirm it also does for the job mode, or add the JOIN.

**Update the result dict** in the `group_by == "job"` case to include `customer_name`:
```python
{
    "group_key": row.group_key,
    "group_label": row.group_label,
    "customer_name": getattr(row, 'customer_name', None),
    # ... existing fields
}
```

**Update `ProfitabilityReportRow`** (or equivalent Pydantic model in `schemas.py`) to add:
```python
customer_name: str | None = None
```

---

## Task 7 — Update `seed_scenario_reporting.py`: Add Invoices + Payments

Add invoice and payment inserts to `mode_seed()` in `seed_scenario_reporting.py`.

After all 4 jobs are created and their IDs are captured, look up the required status IDs:

```python
# Look up invoice_status IDs
draft_status = db.exec(select(InvoiceStatus).where(InvoiceStatus.code == "draft")).first()
issued_status = db.exec(select(InvoiceStatus).where(InvoiceStatus.code == "issued")).first()
paid_status = db.exec(select(InvoiceStatus).where(InvoiceStatus.code == "paid")).first()

# Look up payment_status and payment_type IDs (verify code values via MCP first)
paid_pmt_status = db.exec(select(PaymentStatus).where(PaymentStatus.code == "paid")).first()
check_pmt_type = db.exec(select(PaymentType).where(PaymentType.code == "check")).first()
```

**Insert 4 invoices** (one per job):

| Job | Invoice Fields | Status |
|---|---|---|
| Panel Upgrade (job_a) | `subtotal_cents=122700`, `tax_cents=9816`, `total_cents=132516`, `balance_due_cents=0`, `issued_at=anchor-28d`, `due_at=anchor-14d` | `paid` |
| Service Call (job_b) | `subtotal_cents=25000`, `tax_cents=2000`, `total_cents=27000`, `balance_due_cents=0`, `issued_at=anchor-43d`, `due_at=anchor-29d` | `paid` |
| Commercial Inspection (job_c) | `subtotal_cents=81818`, `tax_cents=6545`, `total_cents=88363`, `balance_due_cents=88363`, `issued_at=anchor-55d`, `due_at=anchor-25d` | `issued` (overdue) |
| Outlet Installation (job_d) | `subtotal_cents=21818`, `tax_cents=1745`, `total_cents=23563`, `balance_due_cents=23563`, `issued_at=anchor-10d`, `due_at=anchor+20d` | `draft` |

Each invoice requires:
- `tenant_id`, `customer_id` (from the job's customer), `site_id` (from the job's site), `job_id`
- `status_id` (from status lookup above)
- `invoice_number` — call `_generate_invoice_number()` from `invoices.py` (or replicate the logic inline using a simple deterministic format like `f"INV-SEED-{job_letter}"` for seed data)
- `currency = "USD"`
- `is_active = True`

**Insert 2 payment rows** (for `paid` invoices):
- `payment_status_id`, `payment_type_id`, `amount_cents` (= `total_cents`), `paid_at` (= due_at), `invoice_id`, `tenant_id`

> **Verify the `payment` table column names via MCP before writing the INSERT.** The seed script uses direct SQL or SQLModel inserts — use the pattern already established in the file for existing inserts.

**Update `mode_reset()`:**
Add cleanup for invoices and payments before the job deletion:
```python
# Delete payments for seeded invoices first (FK constraint)
db.exec(delete(Payment).where(Payment.invoice_id.in_(seeded_invoice_ids)))
# Delete seeded invoices
db.exec(delete(Invoice).where(Invoice.job_id.in_(seeded_job_ids)))
```

**Update `mode_inspect()`:**
After the existing job count output, add:
```python
invoice_count = db.exec(select(func.count(Invoice.id)).where(Invoice.job_id.in_(seeded_job_ids))).one()
print(f"  Invoices for seeded jobs: {invoice_count}")
```

---

## Task 8 — Log `intuit_tid` in QuickBooks Sync Service

In `backend/services/quickbooks_sync.py`, find every location that calls the QBO API and receives an HTTP response object. After each response, add:

```python
intuit_tid = response.headers.get("intuit_tid", "unknown")
logger.info(
    "QBO API call: %s %s | status=%d | intuit_tid=%s",
    response.request.method,
    response.url,
    response.status_code,
    intuit_tid,
)
```

This is a logging-only change — no schema changes, no new fields. Ensure `logger = logging.getLogger(__name__)` is already present at the top of `quickbooks_sync.py` (it should be — read the file to confirm).

---

## Task 9 — Update Schema JSON + OpenAPI + DB Model Map

After all tasks are complete and tests pass:

```bash
cd <repo>/backend
source .venv/bin/activate

# 1. Update OpenAPI (required — endpoints changed)
python export_openapi_json.py

# 2. Update DB model map (required — models changed)
python generate_db_model_map.py

# 3. Update schema JSON — schema_manager.py is a CRUD script, NOT a sync script
python schema_manager.py --help   # read available CRUD commands (set, delete, inspect, etc.)
# Then use the appropriate CRUD command for your new columns
```

---

## Task 10 — Write Tests

Create the following test files:

### `backend/tests/domains/field_operations/test_b19_job_number.py`

```python
pytestmark = [
    pytest.mark.domain_field_operations,
    pytest.mark.unit,
]
```

**Tests to write (minimum 5):**
1. `test_create_job_assigns_job_number` — POST to `/api/v1/jobs/test` → response includes `job_number` starting with `"JOB-"`
2. `test_job_number_format` — `job_number` matches pattern `JOB-YYYYMMDD-XXXXXX`
3. `test_job_detail_includes_status_code` — GET `/api/v1/jobs/{id}` → `status_code` is a string (not None), matches a known code
4. `test_job_detail_includes_site_name` — GET `/api/v1/jobs/{id}` → `site_name` is populated
5. `test_job_detail_includes_customer_name` — GET `/api/v1/jobs/{id}` → `customer_name` is populated
6. `test_job_number_unique_per_tenant` — create 2 jobs for same tenant → different `job_number` values

### `backend/tests/domains/sales_quoting/test_b19_quote_number.py`

```python
pytestmark = [
    pytest.mark.domain_sales_quoting,
    pytest.mark.unit,
]
```

**Tests to write (minimum 3):**
1. `test_create_quote_assigns_quote_number` — POST to quote create → `quote_number` starts with `"Q-"`
2. `test_create_quote_with_title` — POST with `title="Main Panel Upgrade"` → `title` in response
3. `test_create_quote_without_title` — POST without `title` → `title` is `None` in response

### `backend/tests/domains/platform_infrastructure/test_b19_profitability_job_labels.py`

```python
pytestmark = [
    pytest.mark.domain_platform_infrastructure,
    pytest.mark.unit,
]
```

**Tests to write (minimum 2):**
1. `test_profitability_report_job_group_label_uses_job_number` — call profitability endpoint with `group_by=job` → `group_label` does NOT look like a UUID (does not match `[0-9a-f]{8}-[0-9a-f]{4}-...`)
2. `test_profitability_report_job_group_includes_customer_name` — `customer_name` field is present in response rows when `group_by=job`

---

## Verification Checkpoints

**After Task 5 (quote schemas):**
```bash
python -m pytest -m unit --tb=short -q 2>&1 | tail -5
```

**After Task 6 (profitability fix):**
```bash
python -m pytest -m unit --tb=short -q 2>&1 | tail -5
```

---

## Final Verification

### Phase 1 — Unit Tests Only

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=short -q 2>&1 | tail -10
```

All unit tests must pass before moving to Phase 2.

### Phase 2 — Full Suite

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest --tb=short -q 2>&1 | tail -10

# Batch-specific spot checks
python -m pytest tests/domains/field_operations/ -v 2>&1 | tail -20
python -m pytest tests/domains/sales_quoting/ -v 2>&1 | tail -20
python -m pytest tests/domains/platform_infrastructure/ -v 2>&1 | tail -20

# Verify new fields in OpenAPI
grep -A 3 "job_number" backend/openapi_schema_map.md
grep -A 3 "quote_number" backend/openapi_schema_map.md
grep -A 3 "status_code" backend/openapi_schema_map.md

echo "=== B19 FINAL VERIFICATION COMPLETE ==="
```

---

## Test Requirements Summary

| Test File | Domain | Min Tests |
|---|---|---|
| `test_b19_job_number.py` | `domain_field_operations` | 6 |
| `test_b19_quote_number.py` | `domain_sales_quoting` | 3 |
| `test_b19_profitability_job_labels.py` | `domain_platform_infrastructure` | 2 |

All test files must:
- Use `pytestmark` with domain marker + `pytest.mark.unit`
- Use `client` fixture (never module-level `TestClient`)
- Use `test_tenant` and `test_user` fixtures (no hardcoded UUIDs)
- Assert on specific inserted IDs — never on total row counts

---

## Definition of Done

- [ ] Pre-modification regression baseline captured (`X passed, Y failed`) using `pytest -m unit`
- [ ] Zero pre-existing unit failures confirmed before starting (or confirmed with Tom)
- [ ] All 10 MCP pre-work queries run — results match expectations documented in design doc §B
- [ ] All mandatory source files read before writing any code
- [ ] Migration 1: `job_number` added to `job` table — 3-part NOT NULL pattern applied; upgrade/downgrade cycle verified
- [ ] Migration 2: `quote_number` + `title` added to `quote` table — 3-part NOT NULL pattern for `quote_number`; upgrade/downgrade cycle verified
- [ ] `Job` SQLModel updated with `job_number` field
- [ ] `_generate_job_number()` added to `jobs.py`; called in `_create_job_impl()`
- [ ] `Quote` SQLModel updated with `quote_number` + `title` fields
- [ ] `_generate_quote_number()` added to `quotes.py`; called in `_create_quote_impl()`
- [ ] `JobResponse` updated with `job_number`, `status_code`, `site_name`, `customer_name` fields
- [ ] `JobListItem` updated with `job_number` field
- [ ] `QuoteResponse` updated with `quote_number`, `title` fields
- [ ] `QuoteListItem` updated with `quote_number`, `title` fields
- [ ] `QuoteCreate` updated with optional `title` field
- [ ] `_get_job_impl()` JOINs `job_status`, `site`, `customer` and populates new fields
- [ ] Profitability `group_by=job` case uses `job_number` for `group_label` (not UUID)
- [ ] `customer_name` added to profitability row when `group_by=job`
- [ ] `ProfitabilityReportRow` (or equivalent) schema updated with `customer_name` field
- [ ] `seed_scenario_reporting.py` adds 4 invoices + 2 payment rows; `mode_reset()` + `mode_inspect()` updated
- [ ] `quickbooks_sync.py` logs `intuit_tid` from all QBO API responses
- [ ] All new API errors follow RFC 7807 Problem Details format (no plain string `detail`)
- [ ] All new test files use `pytestmark` with domain marker + `pytest.mark.unit`
- [ ] No module-level `TestClient` in any test file
- [ ] `python export_openapi_json.py` run — `job_number`, `quote_number`, `status_code`, `site_name`, `customer_name` visible in `openapi_schema_map.md`
- [ ] `python generate_db_model_map.py` run — `job_number` and `quote_number` appear in `db_models_map.md`
- [ ] `python schema_manager.py --help` run first; then appropriate CRUD command used — `job_number` and `quote_number` appear in `pilot-db-schema-v2.6h.json`
- [ ] **Phase 1**: All unit tests pass (`pytest -m unit`) — zero failures
- [ ] **Phase 2**: Full test suite passes (`pytest`) — zero failures
- [ ] Final test count (before → after) documented
- [ ] Completion Summary added to `pilot-launch-plan.md` §Phase 1 Batch #1

---

## Completion Summary

After all Definition of Done items are complete:

1. Add a **Completion Summary** subsection to `dev-docs/analysis/pilot-launch-plan.md` §Phase 1 Batch #1 using the format below.
2. Update `dev-docs/analysis/pilot-launch-plan.md` Batch #1 status from `☐` → `✅`.

```markdown
### B19 — Human-Readable IDs, JobResponse Enrichment, Profitability Job Labels, Seed Invoices, QB intuit_tid: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot Python Engineer
**Baseline**: X passed, Y failed
**Final**: X+N passed, Y failed (+N new tests)

#### What Was Accomplished

- Added `job_number` (VARCHAR 30, NOT NULL, tenant-scoped unique) to `job` table; backfilled existing rows; auto-generates on create via `_generate_job_number()`
- Added `quote_number` (VARCHAR 30, NOT NULL, tenant-scoped unique) + `title` (VARCHAR 255, nullable) to `quote` table; backfilled `quote_number`; auto-generates on create
- Added `status_code`, `site_name`, `customer_name` to `JobResponse` via JOIN in `_get_job_impl()`
- Added `job_number` to `JobListItem`
- Fixed profitability `group_by=job` case: `group_label` now uses `job_number` instead of UUID; `customer_name` added to row
- Added 4 invoices + 2 payments to `seed_scenario_reporting.py`; `mode_reset()` + `mode_inspect()` updated
- Added `intuit_tid` logging to all QBO API calls in `quickbooks_sync.py`

#### Files Changed / Created

| File | Action |
|---|---|
| `backend/migrations/versions/YYYY_MM_DD_-b19_add_job_number_to_job.py` | Created |
| `backend/migrations/versions/YYYY_MM_DD_-b19_add_quote_number_title_to_quote.py` | Created |
| `backend/app/models/field_ops.py` | Updated — `job_number` field |
| `backend/app/models/sales.py` | Updated — `quote_number`, `title` fields |
| `backend/api/routes/jobs.py` | Updated — `_generate_job_number()`, create + detail impl |
| `backend/api/routes/quotes.py` | Updated — `_generate_quote_number()`, create impl |
| `backend/api/schemas/schemas.py` | Updated — JobResponse, JobListItem, QuoteResponse, QuoteListItem, QuoteCreate, ProfitabilityReportRow |
| `backend/services/report_service.py` | Updated — profitability job group_label + customer_name |
| `backend/migrations/scripts/seed_scenario_reporting.py` | Updated — invoice + payment seeding, mode_reset, mode_inspect |
| `backend/services/quickbooks_sync.py` | Updated — intuit_tid logging |
| `backend/openapi.json` | Regenerated |
| `backend/openapi_schema_map.md` | Regenerated |
| `backend/db_models_map.md` | Regenerated |
| `dev-docs/db-design/pilot-db-schema-v2.6h.json` | Updated via schema_manager.py |

#### Tests Added

| Test File | Domain | Tests | All Pass |
|---|---|---|---|
| `tests/domains/field_operations/test_b19_job_number.py` | `domain_field_operations` | 6 | ✅ |
| `tests/domains/sales_quoting/test_b19_quote_number.py` | `domain_sales_quoting` | 3 | ✅ |
| `tests/domains/platform_infrastructure/test_b19_profitability_job_labels.py` | `domain_platform_infrastructure` | 2 | ✅ |
```

---

## After This Batch — Next Step

After B19 is complete and Tom has reviewed:

**FE-B26** (React Engineer) depends on B19 and can be started. FE-B26 fixes all UUID display bugs in the frontend that now have the real data fields (`job_number`, `quote_number`, `status_code`, `site_name`, `customer_name`) to render correctly.

**Before FE-B26 starts**: Run `cd frontend && pnpm sync-api-types` to regenerate `packages/shared-types/src/api-schema.d.ts` from the updated `backend/openapi.json`.
