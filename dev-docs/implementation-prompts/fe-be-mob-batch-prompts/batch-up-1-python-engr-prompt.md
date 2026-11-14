# Implementation Prompt: UP-1 (Part A) — Work-In-Progress (WIP) Report Endpoint

**Mode**: Pilot Python Engineer
**Batch**: UP-1 — Part A (Backend)
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §2.3 UP-1
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-up-1-design.md`
**Estimated session**: 3–4 hours
**Platform**: Backend only (`backend/`)
**Frontend companion**: `batch-up-1-react-engr-prompt.md` — **gated on this batch closing** (`pnpm sync-api-types`) **and** a Tom-approved UI design spec (Rule 1.5). Do not start FE work here.

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-python-engineer/python-engineer-rules.md`** — full document; the 25 hard rules are non-negotiable STOPs
- **`dev-docs/architecture-design/pilot-python-engineer-methods.md`** — §8 (Router Design), §16 (Standard Task Workflow); §13 (Alembic) — **N/A this batch: no migration**
- **`backend/tests/README-adding-tests.md`** — full document; governs all test file structure, domain markers, and fixture rules

### Critical rules for this batch

- **Rule 1 (verify, don't guess)**: Never guess column names, data types, or table names. Use `postgres-local` MCP to verify every name before use. If MCP returns an error → **STOP and ask Tom**. This is a **read-only report** touching `job`, `job_time_entry`, `job_status`, `quote`, `customer`, `site` — verify every column you SELECT.
- **Rule 6 (tenant scoping)**: `db.get()` is permanently banned on tenant-scoped models. Every query in this batch is raw SQL via `text(...).bindparams()` with an explicit `WHERE j.tenant_id = :tenant_id` clause — mirror the existing `report_service.py` pattern exactly.
- **Rule 7 (MCP read-only)**: The `postgres-local` MCP is for **read-only verification only**. Never INSERT/UPDATE/DELETE through it.
- **Rule 8 (RFC 7807)**: All error responses MUST follow RFC 7807 Problem Details format. Invalid `sort`/`order`/`status` values → `422` with the Problem Details dict.
- **Rule 12 (sync-by-design)**: Every route and `_impl()` here is a plain `def` — this endpoint touches the blocking sync `Session`. **Never** make it `async def`. Verify against the neighboring handlers in `api/routes/reports.py` — all are `def`.
- **Rule 13 (Pydantic v2 + money)**: v2 idioms only (`model_config = ConfigDict`, no `class Config`/`@validator`/`.dict()`). Every route has `response_model`. **Money is always integer cents** — and all ETC/projection arithmetic uses `Decimal` with `ROUND_HALF_UP`, never `float`.
- **Rule 14 (Ruff)**: Run `ruff check . --fix && ruff format .` before declaring done. Modern typing (`str | None`, `list[X]`); no hand-ordered imports; no unjustified `# noqa`.
- **Rule 16 (verify, don't assume)**: 186 tables exist. Query `information_schema.columns` for every table you touch this session before writing SQL.

> **No new mutation endpoint, no new table, no migration.** This batch adds one read-only GET (+ its `/test` twin), a new service module, and new Pydantic response schemas. `set_audit_context_sync()` is **not** needed (no writes). `schema_manager.py` is **not** needed (no schema change). `generate_db_model_map.py` is **not** needed (no model change).

> **Paywall / entitlement note**: This endpoint inherits `require_permission("reports.view")`. The `/reports` domain is not currently `feature_code`-gated in the other six report endpoints — **match the existing pattern exactly** (do not add a `feature_code` the sibling report endpoints don't have). If you believe a `feature_code` is required, STOP and ask Tom rather than diverging from the sibling endpoints.

---

## Pre-Work: Establish Regression Baseline

Before touching any file, capture the current **unit-only** test baseline:

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=no -q 2>&1 | tail -5
```

Record the exact count: **`X passed, Y failed`**.

> **If any tests are already failing before you start**: Do NOT treat them as "pre-existing" and proceed anyway. Either (a) confirm with Tom this is a known, accepted failure with a documented reason, OR (b) fix the failure before touching any batch files. You may NOT start implementation while tests are in an unexplained failed state.

---

## Pre-Work: Run MCP Verification Queries

> **MCP Usage Rule**: The `postgres-local` MCP is for **read-only verification only**. Use it to confirm table names, column types, and existing data. Never use it to INSERT, UPDATE, or DELETE. If a query fails or returns an error → STOP and ask Tom.

> **Independent column verification (MANDATORY)**: The column names below were MCP-verified by the Architect on 2026-07-29, but the live DB is the only authoritative source. Re-run each query. If any column name here does not match what MCP returns → use the MCP-returned name, note the discrepancy in your Completion Summary, and proceed. Do not ask the Architect to redo the prompt.

Run **all** of these before writing any SQL:

```sql
-- 1. job — confirm actuals + status_id + scheduling columns (NOTE: status is via status_id FK, NOT a code column on job)
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'job'
ORDER BY ordinal_position;

-- 2. job_time_entry — confirm the ETC columns (hours_remaining_estimate, hourly_rate_cents, etc_captured_at)
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'job_time_entry'
ORDER BY ordinal_position;

-- 3. job_status — confirm the code column and the active codes exist
SELECT code, name, is_terminal, is_active FROM public.job_status ORDER BY code;
-- Expected active (non-terminal) codes for WIP: 'scheduled', 'in_progress'

-- 4. quote — confirm total_cents is the budget source (int, NOT NULL) reachable via job.quote_id
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'quote' AND column_name IN ('id','tenant_id','total_cents');

-- 5. customer / site — confirm the name columns used for row labels
SELECT table_name, column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name IN ('customer','site')
  AND column_name IN ('id','tenant_id','display_name','company_name','first_name','last_name','name');
```

**What these confirm (Architect's MCP findings 2026-07-29 — verify they still hold):**

| Data needed | Source (MCP-verified) |
|---|---|
| Actual labor / material cost | `job.actual_labor_cost_cents`, `job.actual_material_cost_cents` — `integer`, `NOT NULL` |
| Quoted budget | `quote.total_cents` (`integer`, `NOT NULL`) via `job.quote_id` — **LEFT JOIN** (`job.quote_id` is nullable) |
| Active status filter | **`job.status_id` → `job_status.code`** — `job` has **no** `code`/`status_code` column; you MUST JOIN `job_status js ON js.id = j.status_id` and filter `js.code IN ('scheduled','in_progress')` |
| ETC hours remaining | `job_time_entry.hours_remaining_estimate` (`numeric`, nullable) — latest per job by `etc_captured_at` |
| ETC labor rate | `job_time_entry.hourly_rate_cents` (`integer`, `NOT NULL`) |
| ETC recency key | `job_time_entry.etc_captured_at` (`timestamptz`, nullable) |
| Customer label | `customer.display_name` (preferred; used by existing profitability report) — fall back to `company_name`, else `first_name || ' ' || last_name` |
| Site label | `site.name` |

---

## Pre-Work: Read These Source Files

Use `read_file` on each of these before writing any code:

```
backend/api/routes/reports.py                 ← dual /test twin pattern, require_permission("reports.view"), _impl() structure, 422 validation helper
backend/services/report_service.py            ← text(sql).bindparams() pattern, get_margin_settings(), classify_margin_bucket(), compute_display_mode(); the profitability SQL is the closest template
backend/api/schemas/reports.py                ← ReportEnvelope + existing *Row / *ReportResponse Pydantic shapes to mirror
backend/services/setting_resolver.py          ← get_effective_setting() signature (used by get_margin_settings)
backend/tests/conftest.py                     ← available fixtures (test_tenant, test_job, second_tenant, mock_cognito_jwt, etc.)
backend/tests/domains/platform_infrastructure/ ← existing report endpoint tests to mirror structure (list the dir; read the profitability/report test file)
backend/tests/README-adding-tests.md          ← domain marker + fixture + resilience rules
```

Also run these greps to find related code and existing tests:

```bash
grep -rn "get_profitability_report\|get_margin_settings\|classify_margin_bucket" backend/ --include="*.py" -l
grep -rn "reports.view\|/reports" backend/api/routes/reports.py
grep -rln "domain_platform_infrastructure" backend/tests/ | head
grep -rn "hours_remaining_estimate\|etc_captured_at" backend/ --include="*.py"
```

---

## Background / Context

`/reports` has a `LiveJobsSection` on the frontend whose adapter hardcodes `live_jobs: []` — the "active jobs" table is **permanently empty**, and **no ETC-projected cost exists anywhere** in the product. UP-1 closes that gap.

This batch (Part A) builds the backend: a read-only **WIP report** that, for each **active** job (`job_status.code IN ('scheduled','in_progress')`), computes:

- `actual_cost` = `actual_labor_cost_cents + actual_material_cost_cents`
- `etc_cost` = the **latest** ETC (`hours_remaining_estimate × hourly_rate_cents` from the `job_time_entry` row with `MAX(etc_captured_at)` and a non-null `hours_remaining_estimate`), computed via **Decimal, ROUND_HALF_UP**
- `projected_cost` = `actual_cost + etc_cost`
- `budget` = `quote.total_cents` via `job.quote_id` (nullable — jobs with no quote list with `null` budget/margin/deviation)
- `projected_margin_pct` = `(budget − projected_cost) / budget × 100` (None if budget is None/0)
- `budget_deviation_pct` = `(budget − projected_cost) / budget × 100` — **negative = projected over budget (bad)**

The report is **"now"** (no date range) and returns all active jobs (not paginated for MVP — active-job counts are tens, not thousands).

---

## Task 1 — `wip_service.compute_wip_report()`

Create **`backend/services/wip_service.py`**. Mirror `report_service.py` conventions: raw SQL via `text(sql).bindparams(...)`, tenant-scoped, batched (no N+1), Decimal money math.

**Signature:**

```python
from decimal import ROUND_HALF_UP, Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlmodel import Session

ACTIVE_STATUS_CODES = ["scheduled", "in_progress"]
VALID_SORT = {"deviation_pct", "projected_margin_pct", "actual_cost_cents", "scheduled_start_at"}


def compute_wip_report(
    db: Session,
    tenant_id: UUID,
    status_codes: list[str] | None = None,   # default ACTIVE_STATUS_CODES
    sort: str = "deviation_pct",
    order: str = "desc",
) -> dict[str, Any]:
    """
    Returns {"margin_target_pct": int, "summary": {...}, "rows": [ {...}, ... ]}.
    See design doc §D/§F. Money via Decimal + ROUND_HALF_UP; never float on cents.
    """
```

**ETC "latest per job" (anti-N+1)** — one grouped subquery, joined to the active-job set. Use `DISTINCT ON` to pick the most recent ETC row per job:

```sql
WITH latest_etc AS (
    SELECT DISTINCT ON (jte.job_id)
        jte.job_id,
        jte.hours_remaining_estimate,
        jte.hourly_rate_cents
    FROM job_time_entry jte
    WHERE jte.tenant_id = :tenant_id
      AND jte.hours_remaining_estimate IS NOT NULL
      AND jte.etc_captured_at IS NOT NULL
    ORDER BY jte.job_id, jte.etc_captured_at DESC
)
SELECT
    j.id::text                                   AS job_id,
    j.job_number                                 AS job_number,
    j.title                                      AS title,
    js.code                                      AS status_code,
    j.scheduled_start_at                         AS scheduled_start_at,
    COALESCE(
        NULLIF(c.display_name, ''),
        NULLIF(c.company_name, ''),
        NULLIF(TRIM(CONCAT(COALESCE(c.first_name,''), ' ', COALESCE(c.last_name,''))), '')
    )                                            AS customer_name,
    s.name                                       AS site_name,
    q.total_cents                                AS quoted_budget_cents,   -- NULL if no quote
    j.actual_labor_cost_cents                    AS actual_labor_cost_cents,
    j.actual_material_cost_cents                 AS actual_material_cost_cents,
    le.hours_remaining_estimate                  AS etc_hours_remaining,   -- NULL if no ETC
    le.hourly_rate_cents                         AS etc_hourly_rate_cents  -- NULL if no ETC
FROM job j
JOIN job_status js ON js.id = j.status_id
LEFT JOIN customer c ON c.id = j.customer_id
LEFT JOIN site s ON s.id = j.site_id
LEFT JOIN quote q ON q.id = j.quote_id
LEFT JOIN latest_etc le ON le.job_id = j.id
WHERE j.tenant_id = :tenant_id
  AND j.is_active = true
  AND js.code = ANY(:status_codes)
```

> **Verify `job_status.tenant_id` handling**: `job_status.tenant_id` is nullable (platform-default rows are `NULL`). Do **not** add a `js.tenant_id = :tenant_id` filter — the join to `j.status_id` already scopes correctly and would drop rows using platform-default statuses. Confirm with MCP query #3 that `scheduled`/`in_progress` exist as platform rows.

**Python-side computation per row (Decimal money):**

```python
actual_cost = actual_labor_cost_cents + actual_material_cost_cents  # ints

if etc_hours_remaining is not None and etc_hourly_rate_cents is not None:
    etc_cost = int(
        (Decimal(str(etc_hours_remaining)) * Decimal(etc_hourly_rate_cents))
        .quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    )
    has_etc = True
else:
    etc_cost = 0
    has_etc = False

projected_cost = actual_cost + etc_cost

if quoted_budget_cents and quoted_budget_cents > 0:
    projected_margin_pct = round(
        float(Decimal(quoted_budget_cents - projected_cost) / Decimal(quoted_budget_cents) * 100), 2
    )
    budget_deviation_pct = projected_margin_pct  # same numerator/denominator; negative = over budget
    below_margin_target = projected_margin_pct < target_pct
else:
    projected_margin_pct = None
    budget_deviation_pct = None
    below_margin_target = False  # no budget → cannot be "below target"
```

**Margin target**: reuse `get_margin_settings(db, tenant_id)` from `report_service.py` — returns `(boundaries, target_pct)`. Use `target_pct` only (WIP does not bucket).

**Sorting**: validate `sort ∈ VALID_SORT` and `order ∈ {"asc","desc"}` **in the service or the `_impl`** (raise 422 — see Task 3). Sort **in Python** after computing rows (rows with `None` deviation/margin sort last regardless of order). Default `deviation_pct desc` = worst (most negative) first — so for `deviation_pct` treat `None` as `+inf` when `desc` (pushed to the end) and be consistent for `asc`.

**Summary block:**

```python
summary = {
    "active_job_count": len(rows),
    "total_actual_cost_cents": sum(r["actual_cost_cents"] for r in rows),
    "total_quoted_budget_cents": sum(r["quoted_budget_cents"] or 0 for r in rows),
    "total_projected_cost_cents": sum(r["projected_cost_cents"] for r in rows),
    "jobs_over_budget_count": sum(1 for r in rows if r["budget_deviation_pct"] is not None and r["budget_deviation_pct"] < 0),
    "jobs_below_margin_target_count": sum(1 for r in rows if r["below_margin_target"]),
}
```

Run the intermediate unit loop after this task:
```bash
python -m pytest -m unit --tb=short -q 2>&1 | tail -5
```

---

## Task 2 — Pydantic response schemas

Add to **`backend/api/schemas/reports.py`** (mirror the existing `*Row` / `*ReportResponse` style; note WIP has **no** `date_from`/`date_to`, so it does **not** extend `ReportEnvelope` — model it like `ARAgingReportResponse` which also breaks the envelope):

```python
class WipSummary(BaseModel):
    active_job_count: int
    total_actual_cost_cents: int
    total_quoted_budget_cents: int
    total_projected_cost_cents: int
    jobs_over_budget_count: int
    jobs_below_margin_target_count: int


class WipReportRow(BaseModel):
    job_id: str
    job_number: str
    title: str | None = None
    customer_name: str | None = None
    site_name: str | None = None
    status_code: str
    scheduled_start_at: datetime | None = None
    quoted_budget_cents: int | None = None
    actual_cost_cents: int
    etc_hours_remaining: float | None = None
    etc_cost_cents: int
    projected_cost_cents: int
    projected_margin_pct: float | None = None
    budget_deviation_pct: float | None = None
    has_etc: bool
    below_margin_target: bool


class WipReportResponse(BaseModel):
    report_type: str = "wip"
    generated_at: datetime
    margin_target_pct: float
    row_count: int
    summary: WipSummary
    rows: list[WipReportRow]
```

> `etc_hours_remaining` is `numeric` in the DB → expose as `float | None` for the FE (display only; never used for money math on the FE). `generated_at` = `datetime.now(UTC)` at response build time (import `from datetime import UTC, datetime` — Rule 7 UTC-aware).

---

## Task 3 — `GET /api/v1/reports/wip` (+ `/test` twin)

Add to **`backend/api/routes/reports.py`**. Follow the file's established structure exactly:

1. A shared `_get_wip_impl(status, sort, order, db, user_context) -> WipReportResponse`.
2. Register the **`/wip/test` twin FIRST** (in the TEST ENDPOINTS block, before the authenticated endpoints), then the authenticated `/wip`.
3. Auth: `current_user: AuthenticatedUser = Depends(require_permission("reports.view"))` — identical to the sibling report endpoints. **No `feature_code`** (siblings don't use one).

**Validation (RFC 7807, Rule 8)** — in `_get_wip_impl`:

```python
if sort not in VALID_SORT:
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail={
            "type": "https://errors.pilotfortrades.com/validation-error",
            "title": "Invalid sort parameter",
            "status": 422,
            "detail": f"sort must be one of: {', '.join(sorted(VALID_SORT))}",
        },
    )
# same shape for order ∈ {'asc','desc'} and each status code ∈ known job_status codes
```

> Check how the existing report endpoints shape their 422 `detail`. The sibling endpoints currently use a **plain string** `detail` (e.g. `_validate_date_range`). **Rule 8 requires the RFC 7807 dict** — use the dict form for the new WIP endpoint. If a linter/test enforces string-shape parity with siblings, STOP and ask Tom rather than downgrading to a plain string.

**Query params** (mirror `filter_status` CSV handling from profitability):
- `status: str | None = Query(default=None)` → CSV → `list[str]`; default `["scheduled","in_progress"]` when None.
- `sort: str = Query(default="deviation_pct")`
- `order: str = Query(default="desc")`

**Response build:**

```python
data = compute_wip_report(db, user_context.tenant_id, status_codes, sort, order)
return WipReportResponse(
    report_type="wip",
    generated_at=datetime.now(UTC),
    margin_target_pct=float(data["margin_target_pct"]),
    row_count=len(data["rows"]),
    summary=WipSummary(**data["summary"]),
    rows=[WipReportRow(**r) for r in data["rows"]],
)
```

Both the authenticated and `/test` handlers are plain `def` (Rule 12). The `/test` handler uses `get_test_context()` exactly like the six existing `*_test` report handlers.

Run the intermediate unit loop:
```bash
python -m pytest -m unit --tb=short -q 2>&1 | tail -5
```

---

## Test Requirements

Per `backend/tests/README-adding-tests.md`:

- **Domain folder**: `backend/tests/domains/platform_infrastructure/` (reports live here). New file e.g. `test_wip_report.py`.
- **`pytestmark`**:
  ```python
  pytestmark = [pytest.mark.domain_platform_infrastructure, pytest.mark.unit]
  ```
- Use the `client` fixture (never module-level `TestClient`). Use `test_tenant`/`test_job`/`second_tenant` fixtures — **no hardcoded UUIDs**.
- **Scope assertions by inserted IDs** — never assert on total row counts (seed data is always present). To assert a specific job appears in the WIP rows, filter the response `rows` by the `job_id` you created.
- Use the **`/reports/wip/test`** endpoint (no JWT) to exercise the logic, consistent with how the other report tests hit `/reports/*/test`.
- **Entitlement**: the autouse `mock_entitlement_allowed` bypasses paywall — fine here (this batch does not test tier gating). Do **not** add `skip_mock_entitlement_allowed`.

**Required test cases (map to §G of the design):**

| Case | What it asserts |
|---|---|
| ETC present | A job with a recent `job_time_entry` (non-null `hours_remaining_estimate`, `etc_captured_at`, `hourly_rate_cents`) → `has_etc=true`, `etc_cost_cents = round(hours × rate)`, `projected_cost = actual + etc` |
| ETC absent | Active job with no ETC time entry → `has_etc=false`, `etc_cost_cents=0`, `projected_cost_cents == actual_cost_cents` |
| Latest ETC wins | Two time entries with different `etc_captured_at` → the row uses the one with the **max** `etc_captured_at` |
| No quote | Job with `quote_id = NULL` → `quoted_budget_cents=null`, `projected_margin_pct=null`, `budget_deviation_pct=null`, `below_margin_target=false`; row still present |
| Over budget | `projected_cost > budget` → `budget_deviation_pct < 0`, counted in `summary.jobs_over_budget_count` |
| Below margin target | `0 < projected_margin_pct < target_pct` → `below_margin_target=true`, counted in `summary.jobs_below_margin_target_count` |
| Status filter | Only `scheduled`/`in_progress` jobs appear by default; a `completed`/`cancelled` job you insert does NOT appear |
| Decimal rounding | Fractional `hours_remaining_estimate` (e.g. `6.5`) with a rate producing a `.5` cent → ROUND_HALF_UP verified (assert exact `etc_cost_cents`) |
| Invalid sort | `?sort=bogus` → `422` RFC 7807 Problem Details |
| Tenant isolation | Insert an active job in `second_tenant`; call `/wip/test` (which uses the canonical test tenant) → the `second_tenant` job is **absent** from `rows` |

> Money-math tests: assert exact integer `_cents` values — the ROUND_HALF_UP behavior is the whole point of using Decimal, so pick fixtures that would round differently under banker's rounding vs half-up.

---

## Regeneration Steps

### Regenerate OpenAPI (endpoints changed)

After all unit tests pass (and after `ruff check . --fix && ruff format .`):

```bash
cd <repo>/backend
source .venv/bin/activate
python export_openapi_json.py
```

This regenerates both `backend/openapi.json` (consumed by FE `pnpm sync-api-types`) and `backend/openapi_schema_map.md` (the React Engineer's endpoint reference). Verify:

```bash
grep -A 5 "reports/wip" backend/openapi_schema_map.md
```

> **Not needed this batch**: `schema_manager.py` (no schema change), `generate_db_model_map.py` (no model change), Alembic (no migration), seed rollout (no new column/lookup value). If you find yourself editing a model or migration, STOP — the design says none is required; confirm with Tom before diverging.

---

## Final Verification

### Phase 1 — Unit Tests Only (during development)

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=short -q 2>&1 | tail -10
```

All unit tests must pass before moving on. Fix any unit failure — including failures that appear to originate outside your batch — before proceeding.

### Phase 2 — Lint + Full Suite (once, at the end, before DoD sign-off)

```bash
cd <repo>/backend
source .venv/bin/activate

ruff check . --fix
ruff format .

python -m pytest --tb=short -q 2>&1 | tail -10
python -m pytest tests/domains/platform_infrastructure/ -v 2>&1 | tail -20
grep -A 5 "reports/wip" backend/openapi_schema_map.md

echo "=== UP-1 PART A FINAL VERIFICATION COMPLETE ==="
```

> **Warning-clean is part of done.** Ruff must report no remaining issues (no unjustified `# noqa`), and the pytest run must be free of Pydantic-v1 / deprecation warnings. Any failure in either phase must be fixed before the batch is declared done — no "pre-existing failure" exception without written confirmation from Tom.

---

## Definition of Done

Update the `pilot-launch-plan.md` §2.3 UP-1 tracker when each item is done:

- [ ] Pre-modification regression baseline captured (`X passed, Y failed`) using `pytest -m unit`
- [ ] Zero pre-existing unit failures confirmed before starting (or confirmed with Tom)
- [ ] All 5 MCP pre-work queries run — `job.status_id → job_status.code` JOIN confirmed (job has no direct code column); ETC columns + `quote.total_cents` + customer/site name columns verified
- [ ] All mandatory source files read before writing any code (including `api/schemas/reports.py`)
- [ ] `backend/services/wip_service.py` created — `compute_wip_report()` with `DISTINCT ON` latest-ETC subquery (no N+1), Decimal ROUND_HALF_UP money math, tenant-scoped
- [ ] `WipSummary` / `WipReportRow` / `WipReportResponse` added to `api/schemas/reports.py` (Pydantic v2)
- [ ] `_get_wip_impl` + `GET /reports/wip` + `GET /reports/wip/test` twin (test registered first) added to `api/routes/reports.py`
- [ ] All DB-touching routes/`_impl()`/service functions are sync `def` — no `async def` (Rule 12)
- [ ] Only Pydantic v2 idioms; `response_model` on both new routes; money integer cents; all projection math via Decimal (Rule 13)
- [ ] Invalid `sort`/`order`/`status` → `422` RFC 7807 Problem Details (Rule 8)
- [ ] New test file uses `pytestmark` with `domain_platform_infrastructure` + `unit`; `client`/`test_tenant`/`second_tenant` fixtures; assertions scoped by inserted IDs
- [ ] All 10 required test cases implemented and passing (incl. ROUND_HALF_UP and tenant isolation)
- [ ] `ruff check . --fix && ruff format .` — zero remaining issues
- [ ] `python export_openapi_json.py` run — `reports/wip` appears in `openapi_schema_map.md`
- [ ] **Phase 1**: all unit tests pass (`pytest -m unit`) — zero failures
- [ ] **Phase 2**: full suite passes (`pytest`) — zero failures, warning-clean
- [ ] Final test count (before → after) documented
- [ ] Completion Summary added to the launch plan §2.3 UP-1 card
- [ ] Handoff instructions executed (below)

---

## Handoff Instructions (BE → FE)

This is a mixed batch; the React Engineer (Part B) depends on this endpoint. Before declaring Part A done:

1. Confirm `python export_openapi_json.py` has run and `reports/wip` is present in **both** `openapi.json` and `openapi_schema_map.md`.
2. Commit with a message like `feat(reports): add WIP report endpoint (UP-1 Part A)`.
3. **Notify the Architect/Tom** that Part A is closed so that: (a) the React Engineer's first Pre-Work step `pnpm sync-api-types` will pick up `WipReportResponse`, and (b) the Part B React prompt (already gated on the Tom-approved UI design spec, Rule 1.5) can be authored/started.

> Do **not** start any frontend work in this batch. Part B is a separate prompt with its own design-spec gate.

---

## Completion Summary

After all Definition of Done items are complete, add a **Completion Summary** to `pilot-launch-plan.md` §2.3 UP-1 using this format:

```markdown
### UP-1 (Part A) — WIP Report Endpoint: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot Python Engineer
**Baseline**: X passed, Y failed
**Final**: X+N passed, Y failed (+N new tests)

#### What Was Accomplished
- New `GET /api/v1/reports/wip` (+ `/test`) computing per-active-job actuals + ETC-projected cost vs quoted budget, with deviation % and projected margin %.
- Latest-ETC-per-job via `DISTINCT ON` (no N+1); Decimal ROUND_HALF_UP money math; tenant-scoped.
- [Any MCP discrepancy vs the prompt, noted here.]

#### Files Changed / Created
| File | Action |
|---|---|
| `backend/services/wip_service.py` | Created — compute_wip_report() |
| `backend/api/schemas/reports.py` | Updated — WipSummary/WipReportRow/WipReportResponse |
| `backend/api/routes/reports.py` | Updated — /reports/wip + /test twin + _get_wip_impl |
| `backend/openapi.json` / `openapi_schema_map.md` | Regenerated |

#### Tests Added
| Test File | Domain | Tests | All Pass |
|---|---|---|---|
| `tests/domains/platform_infrastructure/test_wip_report.py` | `domain_platform_infrastructure` | N | ✅ |
```

---

## After This Task — Next Step

Part B (React) — `batch-up-1-react-engr-prompt.md`, gated on (1) this endpoint being live + `pnpm sync-api-types`, and (2) a Tom-approved `batch-up-1-ui-design-spec.md` from the `pilot-web-ui-designer` (Rule 1.5). The Architect authors that prompt after both gates clear.
