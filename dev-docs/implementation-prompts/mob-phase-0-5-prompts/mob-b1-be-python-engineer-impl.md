# Implementation Prompt: MOB-B1-BE — Jobs List API Enhancements

**Mode**: Pilot Python Engineer
**Batch**: MOB-B1-BE (Backend companion to MOB-B1)
**Source design doc**: `dev-docs/architecture-design/batch-designs/batch-mob-b1-design.md` §B.1
**Source plan**: `dev-docs/analysis/pilot-app-beta-fixes-v2-impl-plan.md`
**Estimated session**: 1–2 hours
**Unblocks**: MOB-B1 frontend (React Engineer) — the frontend was built against the planned API contract using MSW stubs and becomes wire-complete once this task ships

---

## ⚠️ MANDATORY STOP: Read These Rules First

Before writing a single line of code, read:
- **`.roo/rules-pilot-python-engineer/`** — in full

Critical rules for this batch:
- **Rule A**: Never guess table or column names. Run the MCP queries in §0 first and stop if any return unexpected results.
- **Rule B**: Never use `db.get(Model, pk)` on tenant-scoped models. Always use the tenant-scoped `select()` pattern.
- **Rule C**: Read the actual source files before editing them.
- **Rule D**: Follow the 3-part migration pattern for NOT NULL columns on existing tables (not needed here — no schema migration required).

---

## §0 Pre-Work: Verify Table Names via MCP

**Run all three queries before writing any code. If any return 0 rows, STOP and ask Tom.**

```sql
-- Verify the job table columns
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'job'
ORDER BY ordinal_position;
```

```sql
-- Verify the job_status table (to understand the status code lookup)
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'job_status'
ORDER BY ordinal_position;
```

```sql
-- Verify the tech assignment table name (may be scheduling_job_tech_assignment or similar)
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name LIKE '%job%tech%'
  OR table_name LIKE '%assignment%'
ORDER BY table_name;
```

```sql
-- Once you have the correct assignment table name, verify its columns:
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = '<actual_assignment_table_name>'
ORDER BY ordinal_position;
```

Record the **exact table names and column names** before proceeding. The design doc uses `scheduling_job_tech_assignment` and `user_id` as assumed names — verify these match the actual schema.

---

## Pre-Work: Establish Regression Baseline

```bash
cd <repo>/backend
pytest -m unit 2>&1 | tail -5
```

Record the exact passing test count before any changes.

---

## Pre-Work: Read These Files First

Read every file with `read_file` before writing any code.

```bash
# The jobs route that needs to be modified
cat backend/api/routes/jobs.py

# The jobs schemas file
cat backend/api/schemas/jobs.py

# Reference: how BETA-B3 companion did the same pattern for quotes
# (added ?status= filter + status_code + customer_name to quotes list)
cat backend/api/schemas/quotes.py   # look for QuoteListItem
grep -n "customer_name\|status_code\|_list_quotes_impl" backend/api/routes/quotes.py | head -30
```

---

## What This Task Does

The `GET /api/v1/jobs/` endpoint currently only accepts `skip` and `limit` params and returns a minimal response with only UUID fields. The mobile Jobs tab (`useTechJobsList`) needs:

1. **`?tech_id=` filter** — return only jobs assigned to the specified user (JOIN on the tech assignment table)
2. **`?scheduled_date=` filter** — return only jobs scheduled on the specified YYYY-MM-DD date
3. **`status_code: str | None`** in the response — the human-readable status string (e.g., `"scheduled"`, `"in_progress"`) from the `job_status` table
4. **`customer_name: str | None`** in the response — the customer's `display_name` from the `customer` table

**No schema migration required** — all changes are JOIN-based additions to an existing endpoint.

---

## Step 1: Add `JobListItem` Schema

Read `backend/api/schemas/jobs.py` first. Then add a new schema class `JobListItem` following the same pattern as `QuoteListItem` in `backend/api/schemas/quotes.py`:

```python
class JobListItem(SQLModel):
    """Lightweight job representation for list views (mobile Jobs tab).

    Extended vs JobResponse: adds status_code (from job_status JOIN) and
    customer_name (from customer JOIN). Added by MOB-B1-BE.
    """
    id: str
    tenant_id: str
    customer_id: str
    site_id: str
    status_id: str
    status_code: str | None = None       # from job_status.code JOIN
    customer_name: str | None = None     # from customer.display_name JOIN
    scheduled_start_at: datetime | None = None
    scheduled_end_at: datetime | None = None
    estimated_duration_minutes: int | None = None
```

> **Read the existing `JobResponse` class first** to ensure `JobListItem` field names are consistent with the existing schema pattern in the file.

---

## Step 2: Update `_list_jobs_impl()` in `backend/api/routes/jobs.py`

Read the entire `jobs.py` file before modifying. Find the `_list_jobs_impl()` function (or equivalent list implementation).

Add two new optional query params:

| Param | Type | Behavior |
|---|---|---|
| `tech_id` | `str \| None = Query(default=None)` | If provided, filter to jobs where the assignment table has `user_id = tech_id` (verify exact column name from MCP). |
| `scheduled_date` | `str \| None = Query(default=None)` | If provided (YYYY-MM-DD), filter where `DATE(job.scheduled_start_at) = scheduled_date` using PostgreSQL `::date` cast. |

Add two new JOINs to the existing query:

```python
# JOIN job_status for status_code
# (verify exact table/column names from MCP before coding)
query = (
    select(
        Job,
        JobStatus.code.label("status_code"),
        Customer.display_name.label("customer_name"),
    )
    .join(JobStatus, Job.status_id == JobStatus.id, isouter=True)
    .join(Customer, Job.customer_id == Customer.id, isouter=True)
    .where(Job.tenant_id == current_tenant_id)
    .where(Customer.tenant_id == current_tenant_id)  # ← MANDATORY IDOR protection
)
```

> **Multi-tenancy rule**: The `Customer` JOIN MUST include `.where(Customer.tenant_id == current_tenant_id)` to prevent cross-tenant customer name leakage. This is the same rule applied in `QuoteListItem` (BETA-B3 companion). Failure to include this is an IDOR vulnerability.

Apply filters conditionally:

```python
if tech_id:
    query = query.join(
        <AssignmentTable>,
        Job.id == <AssignmentTable>.job_id,
    ).where(<AssignmentTable>.user_id == tech_id)
    # Use exact table/column names confirmed from MCP

if scheduled_date:
    from sqlalchemy import cast, Date as SADate
    query = query.where(
        cast(Job.scheduled_start_at, SADate) == scheduled_date
    )
```

Change the response model from `list[JobResponse]` → `list[JobListItem]` for both the authenticated endpoint and the `/test` no-auth endpoint.

Map the query result rows to `JobListItem` objects — the JOIN adds `status_code` and `customer_name` as additional columns. Follow the same mapping pattern used in the quotes endpoint after BETA-B3.

---

## Step 3: Update Both Endpoint Signatures

Both `GET /api/v1/jobs/` (authenticated) and `GET /api/v1/jobs/test` (no auth) must accept the new params and return `list[JobListItem]`.

Read the current endpoint function signatures before modifying. Add `tech_id` and `scheduled_date` as optional `Query` params to both.

---

## Step 4: Regenerate OpenAPI

```bash
cd <repo>/backend
python export_openapi_json.py
```

Verify the output:
```bash
grep -A 10 "tech_id\|scheduled_date\|status_code\|customer_name" backend/openapi_schema_map.md | head -30
```

All four additions should appear in the schema map.

---

## Tests

Create `backend/tests/domains/field_operations/test_job_list_enhancements.py`:

| Test | Assertion |
|---|---|
| `?tech_id=` filter returns only assigned jobs | Returns jobs assigned to `tech_id`; excludes jobs assigned to other techs |
| `?tech_id=` filter with no assignments | Returns empty list |
| `?scheduled_date=` filter returns only today's jobs | Returns jobs with `scheduled_start_at` matching the date; excludes jobs on other dates |
| Combined `?tech_id=&scheduled_date=` | Both filters applied; only matching jobs returned |
| `status_code` in response | Response includes the status code string, not null |
| `customer_name` in response | Response includes the customer's display name, not null |
| Multi-tenancy: customer from different tenant excluded | Customer JOIN does not expose cross-tenant names |
| `skip` and `limit` still work | Pagination still functional alongside new params |

**Every test must**:
- Declare `pytestmark` with domain marker + `pytest.mark.unit`
- Use `client` fixture (never module-level `TestClient`)
- Use `test_tenant` and `test_user` fixtures (never hardcoded UUIDs)
- Use ID-scoped assertions (never `assert len(all_rows) == N`)

---

## Definition of Done — MOB-B1-BE

- [ ] Pre-modification regression baseline captured (exact test count)
- [ ] All three MCP queries run and results reviewed; exact table/column names confirmed
- [ ] `backend/api/routes/jobs.py` read before modification
- [ ] `backend/api/schemas/jobs.py` read before modification
- [ ] `JobListItem` schema added to `jobs.py` schemas
- [ ] `_list_jobs_impl()` updated with `?tech_id=` and `?scheduled_date=` params
- [ ] `status_code` JOIN on `job_status` table added (verify exact table name from MCP)
- [ ] `customer_name` JOIN on `customer` table added WITH `tenant_id` filter (IDOR protection)
- [ ] Both authenticated and `/test` endpoints return `list[JobListItem]`
- [ ] `python export_openapi_json.py` run — `openapi.json` and `openapi_schema_map.md` updated
- [ ] `grep "tech_id" backend/openapi_schema_map.md` returns results
- [ ] `grep "status_code" backend/openapi_schema_map.md` returns results in jobs section
- [ ] All new tests pass with zero regressions
- [ ] No existing job endpoint tests broken by the response shape change
- [ ] Final test count documented (before → after)

---

## After Completion: Notify React Engineer

When MOB-B1-BE is done:
1. The React Engineer must run `pnpm sync-api-types` in `frontend/`
2. Delete `frontend/apps/mobile/features/jobs/types-stub.ts` (stub is no longer needed)
3. Update `JobCardRow.tsx`, `useTechJobsList.ts`, and `jobsHandlers.ts` imports to use the generated type from `@pilot/shared-types`
4. The MSW handler in `jobsHandlers.ts` can be simplified once the real API supports the params
