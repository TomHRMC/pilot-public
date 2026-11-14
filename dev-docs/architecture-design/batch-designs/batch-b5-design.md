# Batch B5 Design Document — Reports & Dashboard

**Batch**: B5  
**Item count**: 1 (A5 — Reports Domain + Pin-to-Dashboard)  
**Estimated effort**: 5–7 days  
**Prerequisites**: None (self-contained; parallel-safe)  
**Test subfolder**: `tests/batch_b5/`  
**Design date**: 2026-05-01  
**Status**: READY FOR IMPLEMENTATION

---

## Input Read Summary

All six reads completed before this document was written.

| Read | Source | Key Finding |
|---|---|---|
| READ 1 | `§6.B5` impl plan | Single item A5; 6 report endpoints + widget CRUD; `display_mode` from `report_chart_threshold` vs row count |
| READ 2 | `frontend-backend-mvp-additions-latest.md` A5, A15, A17 | `user_dashboard_widget` fields confirmed; `report_chart_threshold`, `margin_bucket_boundaries`, `margin_target_pct` already exist in `tenant_settings` per A15/A17 |
| READ 3 | `mvp-arch.md` §3.4, §16 | Profitability rollup writes to `job.actual_labor_cost_cents/material/profit`; cached fields are the read source for reports; no SSE needed (read-only) |
| READ 4 | `pilot-python-engineer-methods.md` §16, §20, §21 | §16 standard workflow applies; §21 `get_effective_setting()` used for chart threshold; §20 staleness check not applicable (all GETs) |
| READ 5 | postgres-local MCP | `user_dashboard_widget` does NOT exist (new table); `tenant_settings` already has `report_chart_threshold` (int, default 8), `margin_bucket_boundaries` (jsonb, default `[10,20,30]`), `margin_target_pct` (int, default 20); no dunning routines found (G7 flag) |
| READ 6 | Source files | `tasks/profitability_rollup.py::calculate_job_profitability()`, `services/etc_service.py::compute_projected_margin()`, no `reports.py` route exists; no `reports.view` or `dashboard.manage` permissions seeded |

---

## A. MIGRATION PLAN

### Pre-Batch Verification Result (READ 5)

The following columns from A5/A15/A17 scope are **already present** in `tenant_settings` — do **not** add them again:

| Column | Status | Confirmed via |
|---|---|---|
| `report_chart_threshold` | ✅ EXISTS (int, NOT NULL, default 8) | MCP query |
| `margin_bucket_boundaries` | ✅ EXISTS (jsonb, NOT NULL, default `[10,20,30]`) | MCP query |
| `margin_target_pct` | ✅ EXISTS (int, NOT NULL, default 20) | MCP query |

**G7 Pre-Batch Flag**: No dunning-related Celery task or stored procedure found in the live DB (`suppress_redundant_updates_trigger` is the only function — unrelated). This confirms G7 is a real gap, but it is **not a B5 blocker** — B5 reports only read `invoice.balance_due_cents` for AR aging, not trigger dunning. G7 remains an open item for the billing batch (B15). The AR aging report is safe to build.

---

### Migration 1 — `user_dashboard_widget` Table

**Migration name**: `phase_fe_1_batch_b5_user_dashboard_widget`

**New table**: `user_dashboard_widget`

| Column | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| `id` | `UUID` | NOT NULL | `gen_random_uuid()` | PK |
| `user_id` | `UUID` | NOT NULL | — | FK → `user.id` RESTRICT |
| `tenant_id` | `UUID` | NOT NULL | — | FK → `tenant.id` RESTRICT; denormalized for query efficiency |
| `widget_type` | `VARCHAR(64)` | NOT NULL | — | Enum string: see `WidgetType` below |
| `widget_config_json` | `JSONB` | NOT NULL | `'{}'::jsonb` | Report-specific filter/config overrides |
| `position_x` | `INTEGER` | NOT NULL | `0` | Dashboard grid column (0-based) |
| `position_y` | `INTEGER` | NOT NULL | `0` | Dashboard grid row (0-based) |
| `width` | `INTEGER` | NOT NULL | `2` | Grid width in columns |
| `height` | `INTEGER` | NOT NULL | `2` | Grid height in rows |
| `created_at` | `TIMESTAMPTZ` | NOT NULL | — | From `StandardAuditMixin` |
| `updated_at` | `TIMESTAMPTZ` | NOT NULL | — | From `StandardAuditMixin` |
| `created_by` | `UUID` | YES | NULL | FK → `user.id` RESTRICT |
| `updated_by` | `UUID` | YES | NULL | FK → `user.id` RESTRICT |

**Indexes**:
```sql
CREATE INDEX ix_user_dashboard_widget_user_id
    ON user_dashboard_widget (user_id);

CREATE INDEX ix_user_dashboard_widget_tenant_id
    ON user_dashboard_widget (tenant_id);
```

**Constraints**:
- No `UNIQUE` constraint on `(user_id, widget_type)` — a user may pin the same report type multiple times with different `widget_config_json` filters.
- `CHECK (width BETWEEN 1 AND 12)` — grid max 12 columns.
- `CHECK (height BETWEEN 1 AND 8)` — grid max 8 rows.
- `CHECK (position_x >= 0)`, `CHECK (position_y >= 0)`.

**No `is_active` soft-delete**: widgets are hard-deleted when removed. Dashboard state is configuration data, not business records.

**`WidgetType` enum values** (stored as `VARCHAR`, not PG ENUM):
```
profitability_summary
revenue_chart
ar_aging
tech_productivity
tax_liability
voice_analytics
```

---

### No Other Migrations

The following were verified as **already present** and require no migration:
- `tenant_settings.report_chart_threshold` — EXISTS
- `tenant_settings.margin_bucket_boundaries` — EXISTS
- `tenant_settings.margin_target_pct` — EXISTS

No column additions to `job`, `invoice`, `job_time_entry`, `job_expense`, `payment`, or `voice_command_log` are required for B5 reports. All report data is aggregated from existing columns using SQL at query time.

---

## B. EXECUTION ORDER

B5 contains one A-item (A5), which decomposes into the following implementation sub-steps in dependency order:

| # | Sub-step | Rationale |
|---|---|---|
| 1 | Alembic migration: `user_dashboard_widget` table | Schema must exist before model, service, or route can be tested |
| 2 | SQLModel model: `backend/app/models/reports.py` — `UserDashboardWidget` | Model required before any DB interaction in service or route layer |
| 3 | Register model in `backend/app/main.py` and update `backend/db_models_map.md` | Alembic autogenerate and import paths need the model registered |
| 4 | Pydantic schemas: `backend/api/schemas/reports.py` — all request/response shapes | Routes cannot be written without input/output schemas |
| 5 | New service: `backend/services/report_service.py` — 6 aggregation functions | Business logic isolated from routes; enables unit testing of SQL aggregations independent of HTTP layer |
| 6 | New route: `backend/api/routes/reports.py` — 6 GET report endpoints | Consumes `report_service.py`; registers with router |
| 7 | New route: `backend/api/routes/dashboard.py` — widget CRUD endpoints | Depends on `UserDashboardWidget` model and `reports.py` schemas |
| 8 | Register both new routers in `backend/app/main.py` | Routes not discoverable until registered |
| 9 | Seed new RBAC permissions (`reports.view`, `dashboard.manage`) | Permissions must exist in DB before route guards can be tested; add to existing role-seed migration or new seed script |
| 10 | Tests: `tests/batch_b5/` | All report shapes, widget CRUD isolation, tenant isolation, `display_mode` threshold logic |

---

## C. NEW API ENDPOINTS

### Common Report Query Parameters

All 6 report endpoints share these query parameters:

| Parameter | Type | Required | Description |
|---|---|---|---|
| `date_from` | `date` (ISO 8601) | YES | Start of reporting period (inclusive) |
| `date_to` | `date` (ISO 8601) | YES | End of reporting period (inclusive) |
| `group_by` | `str` | NO | Grouping dimension (report-specific values; see each endpoint) |

`tenant_scope` is **not** a query parameter — it is enforced automatically from `current_user.tenant_id`. Reports never return cross-tenant data.

**Common response envelope** (all 6 reports):

```json
{
  "report_type": "profitability",
  "date_from": "2026-01-01",
  "date_to": "2026-03-31",
  "display_mode": "chart",
  "row_count": 12,
  "report_chart_threshold": 8,
  "data": [ ... ]
}
```

`display_mode` is computed at API layer: if `len(data) < tenant_settings.report_chart_threshold` → `"chart"`, else → `"table"`.

---

### Endpoint 1 — Profitability Report

**`GET /api/v1/reports/profitability`**

**Auth**: JWT required  
**Permission**: `reports.view`

**Query params** (in addition to common params):
- `group_by`: `"job"` (default) | `"customer"` | `"site"`
- `filter_status`: optional — comma-separated `job_status.code` values to include

**Response `data` item shape**:
```json
{
  "group_key": "uuid-or-name",
  "group_label": "Customer Name or Job Title",
  "job_count": 4,
  "quoted_total_cents": 450000,
  "actual_labor_cost_cents": 180000,
  "actual_material_cost_cents": 60000,
  "actual_profit_cents": 210000,
  "margin_pct": 46.7,
  "margin_bucket": "30+",
  "below_margin_target": false
}
```

**Computed fields**:
- `margin_pct` = `(quoted_total_cents - actual_labor_cost_cents - actual_material_cost_cents) / quoted_total_cents * 100` — handle `quoted_total_cents = 0` → `null`
- `margin_bucket` derived from `tenant_settings.margin_bucket_boundaries` (e.g., `[10, 20, 30]` → buckets `<10`, `10–20`, `20–30`, `30+`)
- `below_margin_target` = `margin_pct < tenant_settings.margin_target_pct`

**Data source**: `job` JOIN `quote` (for `quote.total_cents`), filtered by `job.scheduled_start_at` within date range and `job.tenant_id`

---

### Endpoint 2 — Revenue Report

**`GET /api/v1/reports/revenue`**

**Auth**: JWT required  
**Permission**: `reports.view`

**Query params** (in addition to common params):
- `group_by`: `"month"` (default) | `"week"` | `"quarter"`

**Response `data` item shape**:
```json
{
  "period_label": "2026-01",
  "period_start": "2026-01-01",
  "period_end": "2026-01-31",
  "invoiced_cents": 320000,
  "collected_cents": 280000,
  "outstanding_cents": 40000,
  "invoice_count": 8,
  "payment_count": 7
}
```

**Data sources**:
- `invoiced_cents`: `SUM(invoice.total_cents)` grouped by period using `invoice.issued_at`, filtered by `invoice.tenant_id`
- `collected_cents`: `SUM(payment.amount_cents)` grouped by period using `payment.paid_at`, filtered by `payment.tenant_id`
- `outstanding_cents`: `invoiced_cents - collected_cents` (computed at API layer)

---

### Endpoint 3 — AR Aging Report

**`GET /api/v1/reports/ar-aging`**

**Auth**: JWT required  
**Permission**: `reports.view`

**Query params**: none beyond `date_from`/`date_to` (aging computed as-of `date_to`); no `group_by` (always by customer)

**Response shape** (flat customer-level):
```json
{
  "report_type": "ar_aging",
  "as_of_date": "2026-03-31",
  "display_mode": "table",
  "row_count": 14,
  "report_chart_threshold": 8,
  "summary": {
    "current_cents": 120000,
    "bucket_31_60_cents": 45000,
    "bucket_61_90_cents": 22000,
    "bucket_91_plus_cents": 8000,
    "total_outstanding_cents": 195000
  },
  "data": [
    {
      "customer_id": "uuid",
      "customer_name": "Acme Corp",
      "current_cents": 15000,
      "bucket_31_60_cents": 0,
      "bucket_61_90_cents": 22000,
      "bucket_91_plus_cents": 8000,
      "total_outstanding_cents": 45000,
      "oldest_invoice_due_at": "2025-12-31"
    }
  ]
}
```

**Aging bucket logic**: computed from `CURRENT_DATE - invoice.due_at` (days overdue), filtered to `invoice.balance_due_cents > 0` and `invoice.tenant_id`. Invoices where `due_at IS NULL` land in `current` bucket.

---

### Endpoint 4 — Tech Productivity Report

**`GET /api/v1/reports/tech-productivity`**

**Auth**: JWT required  
**Permission**: `reports.view`

**Query params** (in addition to common params):
- `group_by`: `"user"` (default) | `"job_status"`
- `user_id`: optional UUID filter — restrict to single tech (owner may view any; tech may view self only)

**Response `data` item shape**:
```json
{
  "user_id": "uuid",
  "user_full_name": "Jane Smith",
  "jobs_worked": 12,
  "jobs_completed": 9,
  "total_hours_logged": 87.5,
  "avg_hours_per_job": 7.3,
  "total_labor_cost_cents": 743750
}
```

**Data sources**: `job_time_entry` (hours, `total_cost_cents`, `user_id`) grouped by `user_id`, date-filtered on `job_time_entry.started_at`. `jobs_completed` = distinct `job_id`s where `job.status_id` maps to a terminal `job_status`.

**RBAC note**: If `current_user` has role `technician` and does not have `reports.view_all`, restrict to `user_id = current_user.id`. Owners have `reports.view` which grants cross-user visibility.

---

### Endpoint 5 — Tax Liability Report

**`GET /api/v1/reports/tax-liability`**

**Auth**: JWT required  
**Permission**: `reports.view`

**Query params** (in addition to common params):
- `group_by`: `"month"` (default) | `"quarter"`

**Response `data` item shape**:
```json
{
  "period_label": "2026-Q1",
  "period_start": "2026-01-01",
  "period_end": "2026-03-31",
  "invoice_count": 22,
  "total_invoiced_cents": 890000,
  "total_tax_cents": 71200,
  "effective_tax_rate_pct": 8.0
}
```

**Data source**: `invoice` table using `invoice.tax_cents` (already stored per invoice) and `invoice.total_cents`, grouped by period on `invoice.issued_at`, filtered by `invoice.tenant_id`. MVP uses the aggregate `tax_cents` column; line-item tax breakdowns (by tax jurisdiction/component) are Phase 2 via `invoice_line_tax_component`.

---

### Endpoint 6 — Voice Analytics Report

**`GET /api/v1/reports/voice-analytics`**

**Auth**: JWT required  
**Permission**: `reports.view`

**Query params** (in addition to common params):
- `group_by`: `"intent"` (default) | `"user"` | `"day"`

**Response shape**:
```json
{
  "report_type": "voice_analytics",
  "date_from": "2026-01-01",
  "date_to": "2026-03-31",
  "display_mode": "chart",
  "row_count": 8,
  "report_chart_threshold": 8,
  "summary": {
    "total_commands": 412,
    "successful_commands": 389,
    "success_rate_pct": 94.4,
    "avg_whisper_latency_ms": 340,
    "avg_ollama_latency_ms": 210,
    "avg_total_latency_ms": 580,
    "p95_total_latency_ms": 1420
  },
  "data": [
    {
      "group_key": "create_quote",
      "group_label": "Create Quote",
      "command_count": 98,
      "success_count": 95,
      "success_rate_pct": 96.9,
      "avg_total_latency_ms": 540
    }
  ]
}
```

**Data source**: `voice_command_log` using `intent_detected`, `is_successful`, `whisper_latency_ms`, `ollama_latency_ms`, `total_latency_ms`, date-filtered on `voice_command_log.created_at`, tenant-filtered by `voice_command_log.tenant_id`. P95 latency computed via `PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY total_latency_ms)`.

---

### Widget CRUD Endpoints

#### `GET /api/v1/dashboard/widgets`

**Auth**: JWT required  
**Permission**: `dashboard.manage` (implicitly: only own widgets)  
**Response**: Array of `UserDashboardWidgetResponse`

```json
[
  {
    "id": "uuid",
    "user_id": "uuid",
    "tenant_id": "uuid",
    "widget_type": "profitability_summary",
    "widget_config_json": {"group_by": "customer"},
    "position_x": 0,
    "position_y": 0,
    "width": 4,
    "height": 2,
    "created_at": "2026-03-01T12:00:00Z",
    "updated_at": "2026-03-01T12:00:00Z"
  }
]
```

Filtered by `user_dashboard_widget.user_id = current_user.id` — users never see other users' widgets.

---

#### `POST /api/v1/dashboard/widgets`

**Auth**: JWT required  
**Permission**: `dashboard.manage`

**Request body**:
```json
{
  "widget_type": "profitability_summary",
  "widget_config_json": {"group_by": "customer"},
  "position_x": 0,
  "position_y": 0,
  "width": 4,
  "height": 2
}
```

**Response**: `201 Created` with `UserDashboardWidgetResponse`

**Validation**:
- `widget_type` must be one of the `WidgetType` enum values
- `width` 1–12, `height` 1–8, `position_x ≥ 0`, `position_y ≥ 0`
- `tenant_id` stamped from `current_user.tenant_id`; `user_id` from `current_user.id`

---

#### `PATCH /api/v1/dashboard/widgets/{widget_id}`

**Auth**: JWT required  
**Permission**: `dashboard.manage`

**Request body** (all fields optional):
```json
{
  "widget_config_json": {"group_by": "job"},
  "position_x": 4,
  "position_y": 0,
  "width": 6,
  "height": 3
}
```

**Response**: `200 OK` with updated `UserDashboardWidgetResponse`

**Ownership guard**: verify `widget.user_id == current_user.id` before writing. Return `404` (not `403`) if widget not found or owned by different user — prevents user enumeration.

---

#### `DELETE /api/v1/dashboard/widgets/{widget_id}`

**Auth**: JWT required  
**Permission**: `dashboard.manage`  
**Response**: `204 No Content`

**Ownership guard**: same as PATCH — verify `widget.user_id == current_user.id`. Hard delete (no soft-delete for widget records).

---

## D. PATTERN REUSE DECISIONS

### §3.4 Profitability Rollup (mvp-arch.md) — Consumed by Profitability & Revenue Reports

The profitability rollup worker (`tasks/profitability_rollup.py::calculate_job_profitability`) writes cached financials to `job.actual_labor_cost_cents`, `job.actual_material_cost_cents`, `job.actual_profit_cents` after every time entry or expense mutation. B5 reports **read these cached columns directly** — they do not re-aggregate time entries or expenses at query time.

This means:
- Profitability report latency is bounded by a single `SELECT` on `job` (fast)
- No `JOIN` to `job_time_entry` or `job_expense` needed for profitability aggregation
- A `JOIN` to `quote` is still needed to retrieve `quote.total_cents` for margin percentage computation (the cached `actual_profit_cents` uses `invoiced_total - costs`, which may differ from `quoted_total - costs` when quote ≠ invoice amount)

**Resolved decision**: For margin % in the profitability report, use `job.quote_id → quote.total_cents` as the denominator (quoted amount), not invoiced amount. This is consistent with how `etc_service.py::compute_projected_margin()` computes margin.

### §16 Standard Implementation Task Workflow (pilot-python-engineer-methods.md)

All sub-steps follow the §16.2 standard 4-step execution loop:
1. Write migration + verify with MCP
2. Write model + schemas
3. Write service functions + unit tests
4. Write routes + integration tests

Per §16.1: run full regression baseline (`pytest`) before starting B5. B5 is additive (no mutations to existing models) — regression risk is low.

### §21 Three-Tier Settings Resolver (pilot-python-engineer-methods.md) — `display_mode` Computation

`report_chart_threshold` lives in `tenant_settings` (a direct column, not the key-value settings system). Because it is a direct column — not routed through the `TenantSetting` key-value table — the three-tier resolver (`services/setting_resolver.py::get_effective_setting()`) is **not used** here. Instead, read directly:

```python
# In report_service.py
from sqlmodel import select, Session
from app.models.core import TenantSettings

def get_report_chart_threshold(db: Session, tenant_id: UUID) -> int:
    settings = db.exec(
        select(TenantSettings).where(TenantSettings.tenant_id == tenant_id)
    ).first()
    return settings.report_chart_threshold if settings else 8  # hardcoded fallback

def compute_display_mode(row_count: int, threshold: int) -> str:
    return "chart" if row_count < threshold else "table"
```

This same pattern is already used in `backend/api/routes/jobs.py` for `margin_target_pct` (confirmed from source read).

### `margin_bucket_boundaries` Application (from `tenant_settings`)

Read directly from `tenant_settings.margin_bucket_boundaries` (JSONB). Apply in `report_service.py`:

```python
def classify_margin_bucket(margin_pct: float, boundaries: list[int]) -> str:
    """Classify a margin percentage into the tenant's configured buckets.

    Args:
        margin_pct: Computed margin percentage (e.g., 24.5).
        boundaries: Sorted list of integers from tenant_settings.margin_bucket_boundaries
                    (e.g., [10, 20, 30]).
    Returns:
        str: Bucket label (e.g., "<10", "10–20", "20–30", "30+").
    """
    sorted_b = sorted(boundaries)
    for i, bound in enumerate(sorted_b):
        if margin_pct < bound:
            if i == 0:
                return f"<{bound}"
            return f"{sorted_b[i-1]}–{bound}"
    return f"{sorted_b[-1]}+"
```

### Existing SSE Pattern (`dispatch_board_stream.py`) — Not Reused in B5

Reports are read-only polling endpoints (GET), not push/streaming surfaces. The `dispatch_board_stream.broadcast_board_event()` SSE pattern is not consumed by B5. Dashboard widgets auto-refresh via client-side polling (React Native interval) — no server-sent events.

---

## E. SHARED MODULE INTERFACES

### New File: `backend/services/report_service.py`

This module contains all 6 report aggregation functions. Each function receives a database session, tenant_id, date range, and grouping parameters, and returns a typed dict suitable for serialization by the route layer.

```python
"""
report_service.py — B5/A5

Aggregation functions for all six MVP report types.
All functions are read-only SQL aggregations; no writes occur here.
Consumes: job.actual_labor_cost_cents/material/profit (cached by profitability_rollup task)
"""

from datetime import date, UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlmodel import Session, select

from app.models.core import TenantSettings


def get_report_chart_threshold(db: Session, tenant_id: UUID) -> int:
    """Read report_chart_threshold from tenant_settings.

    Args:
        db:        Open SQLModel session.
        tenant_id: Tenant UUID.
    Returns:
        int: threshold value (defaults to 8 if TenantSettings row not found).
    """
    ...


def compute_display_mode(row_count: int, threshold: int) -> str:
    """Return 'chart' if row_count < threshold, else 'table'.

    Args:
        row_count: Number of data rows in the report response.
        threshold: Value from get_report_chart_threshold().
    Returns:
        str: 'chart' | 'table'
    """
    ...


def classify_margin_bucket(margin_pct: float | None, boundaries: list[int]) -> str | None:
    """Classify a margin percentage into tenant-configured buckets.

    Args:
        margin_pct: Computed margin percentage; None if quoted_total_cents = 0.
        boundaries: Sorted list from tenant_settings.margin_bucket_boundaries.
    Returns:
        str: Bucket label (e.g., '<10', '10–20', '30+') or None if margin_pct is None.
    """
    ...


def get_profitability_report(
    db: Session,
    tenant_id: UUID,
    date_from: date,
    date_to: date,
    group_by: str = "job",
    filter_status: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Aggregate job profitability data from cached job financial columns.

    Args:
        db:            Open SQLModel session.
        tenant_id:     Tenant UUID (enforces isolation).
        date_from:     Report period start (inclusive), filters on job.scheduled_start_at.
        date_to:       Report period end (inclusive).
        group_by:      'job' | 'customer' | 'site'
        filter_status: Optional list of job_status.code values to include.
    Returns:
        list of dicts with keys: group_key, group_label, job_count, quoted_total_cents,
        actual_labor_cost_cents, actual_material_cost_cents, actual_profit_cents,
        margin_pct, margin_bucket, below_margin_target.
    """
    ...


def get_revenue_report(
    db: Session,
    tenant_id: UUID,
    date_from: date,
    date_to: date,
    group_by: str = "month",
) -> list[dict[str, Any]]:
    """Aggregate invoiced vs collected revenue by period.

    Args:
        db:        Open SQLModel session.
        tenant_id: Tenant UUID.
        date_from: Period start (inclusive), filters on invoice.issued_at / payment.paid_at.
        date_to:   Period end (inclusive).
        group_by:  'month' | 'week' | 'quarter'
    Returns:
        list of dicts with keys: period_label, period_start, period_end,
        invoiced_cents, collected_cents, outstanding_cents, invoice_count, payment_count.
    """
    ...


def get_ar_aging_report(
    db: Session,
    tenant_id: UUID,
    as_of_date: date,
) -> dict[str, Any]:
    """Compute accounts-receivable aging buckets as of a given date.

    Args:
        db:          Open SQLModel session.
        tenant_id:   Tenant UUID.
        as_of_date:  Aging computed as of this date (typically date_to from request).
    Returns:
        dict with keys: as_of_date, summary (aggregate bucket totals),
        data (list of per-customer dicts with current/31-60/61-90/91+ buckets).
        Only includes invoices with balance_due_cents > 0.
    """
    ...


def get_tech_productivity_report(
    db: Session,
    tenant_id: UUID,
    date_from: date,
    date_to: date,
    group_by: str = "user",
    user_id: UUID | None = None,
) -> list[dict[str, Any]]:
    """Aggregate technician productivity from job_time_entry.

    Args:
        db:        Open SQLModel session.
        tenant_id: Tenant UUID.
        date_from: Period start (inclusive), filters on job_time_entry.started_at.
        date_to:   Period end (inclusive).
        group_by:  'user' | 'job_status'
        user_id:   Optional filter to single technician.
    Returns:
        list of dicts with keys: user_id, user_full_name, jobs_worked,
        jobs_completed, total_hours_logged, avg_hours_per_job, total_labor_cost_cents.
    """
    ...


def get_tax_liability_report(
    db: Session,
    tenant_id: UUID,
    date_from: date,
    date_to: date,
    group_by: str = "month",
) -> list[dict[str, Any]]:
    """Aggregate tax liability from invoice.tax_cents by period.

    Args:
        db:        Open SQLModel session.
        tenant_id: Tenant UUID.
        date_from: Period start (inclusive), filters on invoice.issued_at.
        date_to:   Period end (inclusive).
        group_by:  'month' | 'quarter'
    Returns:
        list of dicts with keys: period_label, period_start, period_end,
        invoice_count, total_invoiced_cents, total_tax_cents, effective_tax_rate_pct.
        Note: effective_tax_rate_pct = total_tax_cents / total_invoiced_cents * 100;
        None if total_invoiced_cents = 0.
    """
    ...


def get_voice_analytics_report(
    db: Session,
    tenant_id: UUID,
    date_from: date,
    date_to: date,
    group_by: str = "intent",
) -> dict[str, Any]:
    """Aggregate voice command analytics from voice_command_log.

    Args:
        db:        Open SQLModel session.
        tenant_id: Tenant UUID.
        date_from: Period start (inclusive), filters on voice_command_log.created_at.
        date_to:   Period end (inclusive).
        group_by:  'intent' | 'user' | 'day'
    Returns:
        dict with keys: summary (total_commands, successful_commands, success_rate_pct,
        avg_whisper_latency_ms, avg_ollama_latency_ms, avg_total_latency_ms,
        p95_total_latency_ms) and data (list grouped by group_by dimension).
        P95 uses PostgreSQL PERCENTILE_CONT(0.95).
    """
    ...
```

### New File: `backend/app/models/reports.py`

```python
"""
reports.py — B5/A5

SQLModel models for reports domain.
Currently contains only UserDashboardWidget.
"""

import uuid
from enum import Enum
from typing import Any, Dict, Optional

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Integer, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlmodel import Column, Field, SQLModel

from .mixins import StandardAuditMixin


class WidgetType(str, Enum):
    profitability_summary = "profitability_summary"
    revenue_chart = "revenue_chart"
    ar_aging = "ar_aging"
    tech_productivity = "tech_productivity"
    tax_liability = "tax_liability"
    voice_analytics = "voice_analytics"


class UserDashboardWidget(StandardAuditMixin, SQLModel, table=True):
    __tablename__ = "user_dashboard_widget"
    __table_args__ = (
        CheckConstraint("width BETWEEN 1 AND 12", name="ck_widget_width"),
        CheckConstraint("height BETWEEN 1 AND 8", name="ck_widget_height"),
        CheckConstraint("position_x >= 0", name="ck_widget_position_x"),
        CheckConstraint("position_y >= 0", name="ck_widget_position_y"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID, ForeignKey("user.id", ondelete="RESTRICT"),
            nullable=False, index=True
        )
    )
    tenant_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID, ForeignKey("tenant.id", ondelete="RESTRICT"),
            nullable=False, index=True
        )
    )
    widget_type: str = Field(
        sa_column=Column(String(64), nullable=False)
    )
    widget_config_json: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False, server_default=text("'{}'::jsonb")),
    )
    position_x: int = Field(
        default=0,
        sa_column=Column(Integer, server_default=text("0"), nullable=False)
    )
    position_y: int = Field(
        default=0,
        sa_column=Column(Integer, server_default=text("0"), nullable=False)
    )
    width: int = Field(
        default=2,
        sa_column=Column(Integer, server_default=text("2"), nullable=False)
    )
    height: int = Field(
        default=2,
        sa_column=Column(Integer, server_default=text("2"), nullable=False)
    )

    # Phase 6.0.1 pattern: audit FK overrides
    created_by: Optional[uuid.UUID] = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )
    updated_by: Optional[uuid.UUID] = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )
```

**Note**: `UserDashboardWidget` uses `StandardAuditMixin` (provides `created_at`, `updated_at`, `created_by`, `updated_by`). No `is_active` field — widgets are hard-deleted.

---

## F. OPEN QUESTIONS RESOLVED

### F1 — `widget_type` as VARCHAR vs PostgreSQL ENUM

**Question**: Should `widget_type` be a PG ENUM (type-safe, DB-enforced) or VARCHAR with application-level enum?

**Resolution**: Use `VARCHAR(64)` with a Python `WidgetType(str, Enum)` — consistent with the existing project convention (see `QuoteStatus`, `JobStatus`, `WidgetType` pattern). PG ENUMs require DDL `ALTER TYPE` for new values, which is cumbersome as the widget catalog grows. VARCHAR with application-layer validation is the correct choice here. Validation enforced in the Pydantic `UserDashboardWidgetCreate` schema via `widget_type: WidgetType`.

### F2 — Profitability Report: `quoted_total_cents` Source

**Question**: The profitability rollup task (`calculate_job_profitability`) computes `actual_profit_cents = invoiced_total_cents - actual_costs` (with `invoiced_total_cents = 0` currently, per the TODO comment in `tasks/profitability_rollup.py` line 91). The report needs a revenue denominator for margin %. Which value to use?

**Resolution**: Use `job.quote_id → quote.total_cents` as the denominator for margin %. This is: (a) available in all jobs with a quote, (b) consistent with `etc_service.py::compute_projected_margin()` which uses `quoted_total_cents`, (c) the value the owner approved. Jobs without a `quote_id` (direct jobs) show `margin_pct = null`. The existing `actual_profit_cents` on `job` is left as-is for the profitability rollup (it will be fixed in the billing batch when `invoiced_total_cents` is wired correctly). The reports service computes its own margin from the join — it does not rely on `job.actual_profit_cents` for margin %.

### F3 — Margin % When `quoted_total_cents = 0`

**Resolution**: Return `margin_pct = null` for any job/group where the denominator is zero. Return `below_margin_target = false` when `margin_pct = null` (conservative). Document this in the API response shape as nullable.

### F4 — AR Aging: Which Invoice Statuses Are "Open"?

**Question**: The AR aging report needs to know which invoices are outstanding. `invoice.balance_due_cents > 0` is the filter, but should `is_active = false` invoices be excluded?

**Resolution**: Filter on both `invoice.balance_due_cents > 0 AND invoice.is_active = true`. Soft-deleted (voided) invoices should not appear in AR aging. Do not filter by `status_id` values (the status lookup table values are tenant-configurable) — `balance_due_cents > 0` is the correct business signal for outstanding debt.

### F5 — Voice Analytics: `null` Latency Rows

**Question**: Some `voice_command_log` rows may have `NULL` latency columns (e.g., commands that failed before Whisper/Ollama completed).

**Resolution**: Use `AVG(whisper_latency_ms) FILTER (WHERE whisper_latency_ms IS NOT NULL)` and the same for other latency fields. The P95 computation via `PERCENTILE_CONT` naturally excludes NULLs. Document this in the summary shape (`avg_whisper_latency_ms` may be `null` if all rows have null latency).

### F6 — Tech Productivity: `jobs_completed` Definition

**Question**: "Completed" is tenant-configurable via `job_status.is_terminal`. How to identify terminal statuses?

**Resolution**: Join `job_time_entry → job → job_status` and count distinct `job_id` where `job_status.is_terminal = true`. This is correct and does not hardcode status codes.

### F7 — G7 Dunning Pre-Batch Check Result

**Question** (from cross-check): Does a dunning Celery task exist?

**Resolution**: MCP query confirmed no dunning routines exist in the live DB. The AR aging report does NOT require dunning logic — it only reads `invoice.balance_due_cents`. G7 (automated dunning) is a separate feature gap that belongs in the billing batch (B15), not B5. **B5 is not blocked by G7.** Flag this for B15 scope confirmation.

### F8 — Redis Caching for Heavy Reports

**Question**: The impl plan notes Redis caching for profitability and revenue reports as a non-blocking optimization.

**Resolution**: Do not implement Redis caching in B5. At MVP data volumes (< 500 jobs per tenant), direct SQL aggregation from the `job` table's cached financial columns will be sub-200ms. Add a `# TODO: Redis cache if p95 > 2s at production volume` comment in `report_service.py`. The existing `idx_job_tenant_status_created_at` index is well-suited for profitability aggregation queries.

---

## G. EXTERNAL DEPENDENCY STATUS

### All 6 Report Endpoints

| Report | External Dependency | Mock Strategy | Tom Action Required |
|---|---|---|---|
| Profitability | None — reads from `job` table (cached by Celery rollup worker) | N/A | None |
| Revenue | None — reads from `invoice` and `payment` | N/A | None |
| AR Aging | None — reads from `invoice` | N/A | None |
| Tech Productivity | None — reads from `job_time_entry` and `job` | N/A | None |
| Tax Liability | None — reads from `invoice.tax_cents` | N/A | None |
| Voice Analytics | None — reads from `voice_command_log` | N/A | None |

### Dashboard Widget CRUD

| Feature | External Dependency | Mock Strategy | Tom Action Required |
|---|---|---|---|
| Widget CRUD | None — pure PostgreSQL reads/writes | N/A | None |

**B5 has zero external dependencies.** No Stripe, Telnyx, SendGrid, QuickBooks, or 10DLC involvement. This is why B5 is parallel-safe and can start immediately.

### Dependency on Prior Batch Infrastructure

| Infrastructure | Status | Required for B5 |
|---|---|---|
| `tasks/profitability_rollup.py::calculate_job_profitability` | ✅ EXISTS — already implemented | YES (profitability report reads `job.actual_labor_cost_cents` which the task populates) |
| `services/etc_service.py::compute_projected_margin` | ✅ EXISTS — already implemented | NO (not consumed by B5 reports; only by B3 ETC endpoints) |
| `tenant_settings.report_chart_threshold` | ✅ EXISTS | YES |
| `tenant_settings.margin_bucket_boundaries` | ✅ EXISTS | YES |
| `tenant_settings.margin_target_pct` | ✅ EXISTS | YES |

**Implementation note on `actual_profit_cents`**: The existing `calculate_job_profitability` task uses `invoiced_total_cents = 0` as a placeholder (see TODO at line 91 of `tasks/profitability_rollup.py`). This means `job.actual_profit_cents` is currently always negative (0 - costs). B5's profitability report computes its own margin from `quote.total_cents - costs` (per F2 resolution above), bypassing this known limitation. The B5 report is therefore accurate regardless of the rollup task's current `actual_profit_cents` value.

---

## H. TEST FOCUS (for `tests/batch_b5/`)

Per impl plan B5 test requirements:

1. **Report shape tests** — all 6 endpoints return correct JSON shape with:
   - Empty data (no jobs/invoices/entries in date range → `data: []`, `row_count: 0`)
   - Small data (row_count < threshold → `display_mode: "chart"`)
   - Large data (row_count ≥ threshold → `display_mode: "table"`)

2. **`display_mode` threshold test** — verify `display_mode` switches at exactly `report_chart_threshold` rows, and that the threshold is read from `tenant_settings`, not hardcoded.

3. **Widget CRUD isolation** — verify:
   - User A creates widget → User B in same tenant cannot `GET`, `PATCH`, or `DELETE` it
   - `GET /dashboard/widgets` returns only `user_id = current_user.id` rows
   - `PATCH`/`DELETE` on another user's widget returns `404` (not `403`)

4. **Tenant isolation** — report endpoints never return `job`, `invoice`, `job_time_entry`, or `voice_command_log` rows from a different tenant_id.

5. **`margin_pct = null` edge case** — profitability report for a job with no `quote_id` (or `quoted_total_cents = 0`) returns `margin_pct: null` and `below_margin_target: false`.

6. **AR aging bucket boundaries** — invoice 31 days past `due_at` lands in `bucket_31_60`, not `current`. Invoice with `due_at = null` lands in `current`.

7. **Voice analytics null latency** — `voice_command_log` rows with null `whisper_latency_ms` don't crash the aggregation; `avg_whisper_latency_ms` in summary is `null` when all rows lack latency data.
