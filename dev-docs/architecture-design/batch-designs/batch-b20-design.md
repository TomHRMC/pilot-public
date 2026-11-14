# Batch Design: B20 — Invoice Builder Backend

**Batch**: B20  
**Type**: Backend only (Python Engineer)  
**Depends on**: B19 ✅  
**Frontend companion**: FE-B29 (depends on B20)  
**Engineer**: Pilot Python Engineer  
**Platform**: Backend (`backend/`)  
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-b20-design.md`  
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §Phase 1 — B20 row

---

## A. Input Read Summary

| Input | What Was Read | Key Finding |
|---|---|---|
| `pilot-launch-plan.md` §Phase 1 | B20 scope | 5 tasks: `payment_terms` on invoice; `square_integration_enabled` on tenant settings; `card_required` on customer + quote; `billing_mode`/`progress_pct` on invoice; `GET /api/v1/jobs/{id}/billable-items` |
| MCP: `tenant_settings` table | Live DB query | **`tenant_settings` does NOT exist** — table name is wrong. Tenant-level settings live in `platform_setting` (key/value JSONB, nullable `tenant_id` for tenant overrides). Already have `default_invoice_terms_days` (integer, `tenant_editable=true`, category "quotes") |
| MCP: `platform_setting` columns | Live DB | `id`, `key` (VARCHAR), `value` (JSONB), `tenant_id` (nullable UUID) |
| MCP: `platform_setting_catalog` columns | Live DB | `key`, `label`, `description`, `value_type`, `tenant_editable`, `allows_user_override`, `min_value`, `max_value`, `allowed_values`, `category`, `is_active`, `sort_order` |
| MCP: existing `platform_setting_catalog` keys | Live DB | `default_invoice_terms_days` (integer, tenant_editable, category "quotes") already exists |
| MCP: `invoice` columns | Live DB | Has: `quote_id`, `job_id`, `customer_id`, `site_id`, `status_id`, `invoice_number`, `issued_at`, `due_at`, `subtotal_cents`, `tax_cents`, `total_cents`, `balance_due_cents`, `currency`, `customer_notes`, `terms_and_conditions`, `last_reminder_sent_at`, `reminder_count`. Missing: `payment_terms`, `billing_mode`, `progress_pct`, `internal_memo` |
| MCP: `customer` columns | Live DB | Does NOT have `card_required` column |
| MCP: `quote` columns | Live DB | Does NOT have `card_required` column |
| MCP: `job` columns | Live DB | Has `job_number`; no `tenant_id` directly — but confirms FK structure |
| MCP: `job_expense` columns | Live DB | Has `is_billable`, `billable_cents`, `invoice_line_id` (nullable — null = not yet invoiced), `description`, `cost_cents` |
| MCP: `job_time_entry` columns | Live DB | Has `hours`, `hourly_rate_cents`, `total_cost_cents`, `notes`, `user_id` |
| MCP: `alembic_version` | Live DB | Current head: `44035334e651` |
| `mvp-arch.md` §16.5 | Pattern definition | Two-Tier Configuration uses `platform_setting` table; tenant overrides stored as rows with `tenant_id` set; system defaults have `tenant_id = NULL` |
| `invoices.py` route file (lines 1–80) | Structure | Router setup; imports established; uses `_generate_invoice_number()` |
| `schemas.py` (lines 1–80) | Schema pattern | `InvoiceCreate`, `InvoiceSummary`, etc. in `schemas.py` |

---

## B. Migration Plan

**Alembic current head**: `44035334e651` (B19)

### B.1 — Migration 1: `invoice` Table Additions

**New columns on `invoice`:**

| Column | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| `payment_terms` | `VARCHAR(30)` | Nullable | NULL | Values: `due_on_receipt`, `net_15`, `net_30`, `custom_date`. NULL = inherit from tenant's `default_payment_terms` platform setting |
| `billing_mode` | `VARCHAR(20)` | NOT NULL | `'line_item'` | Values: `line_item`, `progress`. Controls invoice builder mode |
| `progress_pct` | `NUMERIC(5,2)` | Nullable | NULL | 0.00–100.00. Only meaningful when `billing_mode = 'progress'` |
| `internal_memo` | `TEXT` | Nullable | NULL | Internal note not shown on PDF |

**3-Part Pattern** (NOT NULL columns with existing rows):
- `billing_mode`: Add nullable → backfill all existing rows to `'line_item'` → lock NOT NULL with server default
- `payment_terms`: Add nullable → no backfill (NULL = inherit) → leave nullable
- `progress_pct`: Add nullable → no backfill → leave nullable
- `internal_memo`: Add nullable → no backfill → leave nullable

**CHECK constraints** (added in same migration — DB-level enum enforcement without a lookup table):

```sql
ALTER TABLE invoice
  ADD CONSTRAINT chk_invoice_payment_terms
    CHECK (payment_terms IN ('due_on_receipt', 'net_15', 'net_30', 'custom_date')),
  ADD CONSTRAINT chk_invoice_billing_mode
    CHECK (billing_mode IN ('line_item', 'progress'));
```

These ensure that even direct SQL writes cannot insert invalid values. The Pydantic `model_validator` guards the API boundary; the CHECK constraint guards the DB boundary.

**Migration command:**
```bash
alembic revision -m "b20_add_invoice_builder_fields"
```

**Pre-migration verification** (MCP — run before writing migration):
```sql
SELECT column_name FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'invoice'
AND column_name IN ('payment_terms', 'billing_mode', 'progress_pct', 'internal_memo');
-- Expected: 0 rows (none exist yet)

-- Also verify no existing constraints by these names
SELECT conname FROM pg_constraint
WHERE conrelid = 'public.invoice'::regclass
AND conname IN ('chk_invoice_payment_terms', 'chk_invoice_billing_mode');
-- Expected: 0 rows
```

**Downgrade**: Drop constraints first, then columns:
```sql
ALTER TABLE invoice
  DROP CONSTRAINT IF EXISTS chk_invoice_payment_terms,
  DROP CONSTRAINT IF EXISTS chk_invoice_billing_mode,
  DROP COLUMN IF EXISTS payment_terms,
  DROP COLUMN IF EXISTS billing_mode,
  DROP COLUMN IF EXISTS progress_pct,
  DROP COLUMN IF EXISTS internal_memo;
```

### B.2 — Migration 2: `customer` + `quote` Table Additions

**New column on `customer`:**

| Column | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| `card_required` | `BOOLEAN` | NOT NULL | `false` | When true: Square card-on-file required before work begins for this customer |

**New column on `quote`:**

| Column | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| `card_required` | `BOOLEAN` | Nullable | NULL | NULL = inherit from customer.card_required. Explicit true/false = per-quote override |

**3-Part Pattern** for `customer.card_required` (existing rows):
- Add nullable → backfill `UPDATE customer SET card_required = false WHERE card_required IS NULL` → lock NOT NULL with `DEFAULT false`

**Migration command:**
```bash
alembic revision -m "b20_add_card_required_and_square"
```

**Pre-migration verification** (MCP — run before writing migration):
```sql
SELECT column_name FROM information_schema.columns 
WHERE table_schema = 'public' AND table_name IN ('customer', 'quote')
AND column_name = 'card_required';
-- Expected: 0 rows
```

**Downgrade**: `ALTER TABLE customer DROP COLUMN IF EXISTS card_required; ALTER TABLE quote DROP COLUMN IF EXISTS card_required;`

### B.3 — Data Migration 3: `platform_setting_catalog` + `platform_setting` Additions

**New `platform_setting_catalog` rows** — 3 keys total, all in category `billing`:

| Key | Label | Value Type | Tenant Editable | `allowed_values` | Default | Notes |
|---|---|---|---|---|---|---|
| `square_integration_enabled` | Square payment integration enabled | `boolean` | `true` | — | `false` | Tenant opt-in for card-on-file via Square |
| `default_payment_terms` | Default invoice payment terms | `string` | `true` | `["due_on_receipt","net_15","net_30","custom_date"]` | `"due_on_receipt"` | When `invoice.payment_terms` is NULL, FE-B29 pre-selects this value. Validated against `allowed_values` by the platform settings API |
| `default_billing_mode` | Default invoice billing mode | `string` | `true` | `["line_item","progress"]` | `"line_item"` | When FE-B29 opens a blank invoice, this is the default tab selection. Same allowed_values as the CHECK constraint on `invoice.billing_mode` |

**Important design note**: The `allowed_values` JSONB array on `platform_setting_catalog` serves as the catalog-level validation list for the settings API. This ensures the valid values for tenant defaults match exactly the valid values enforced by the DB CHECK constraints on `invoice.payment_terms` and `invoice.billing_mode` — single source of truth per enum.

**New `platform_setting` rows** (system defaults, `tenant_id = NULL`):

| Key | Value (JSONB) | Tenant ID |
|---|---|---|
| `square_integration_enabled` | `false` | NULL |
| `default_payment_terms` | `"due_on_receipt"` | NULL |
| `default_billing_mode` | `"line_item"` | NULL |

**Migration command:**
```bash
alembic revision -m "b20_add_invoice_platform_settings"
```

This is a **data migration** — use `op.execute()` with `SET LOCAL session_replication_role = 'replica';`.

**Pre-migration verification** (MCP):
```sql
SELECT key FROM platform_setting_catalog
WHERE key IN ('square_integration_enabled', 'default_payment_terms', 'default_billing_mode');
-- Expected: 0 rows

SELECT key FROM platform_setting
WHERE key IN ('square_integration_enabled', 'default_payment_terms', 'default_billing_mode')
AND tenant_id IS NULL;
-- Expected: 0 rows
```

**Downgrade**:
```sql
DELETE FROM platform_setting WHERE key IN ('square_integration_enabled', 'default_payment_terms', 'default_billing_mode');
DELETE FROM platform_setting_catalog WHERE key IN ('square_integration_enabled', 'default_payment_terms', 'default_billing_mode');
```

---

## C. Execution Order

| # | Task | File(s) | Notes |
|---|---|---|---|
| 1 | Migration 1: `invoice` builder fields | Alembic | `billing_mode` uses 3-part pattern (NOT NULL) |
| 2 | Migration 2: `card_required` on `customer` + `quote` | Alembic | `customer.card_required` uses 3-part; `quote.card_required` nullable |
| 3 | Migration 3: `square_integration_enabled` catalog + default | Alembic data migration | Uses `op.execute()` with replica role |
| 4 | Update `Invoice` SQLModel | `app/models/billing.py` | Add 4 new fields |
| 5 | Update `Customer` SQLModel | `app/models/crm.py` | Add `card_required` field |
| 6 | Update `Quote` SQLModel | `app/models/quoting.py` | Add `card_required` field |
| 7 | Update `InvoiceCreate` schema | `api/schemas/schemas.py` | Add `payment_terms`, `billing_mode`, `progress_pct`, `internal_memo` |
| 8 | Update `InvoiceResponse` schema | `api/schemas/schemas.py` | Expose new fields |
| 9 | Update `_create_invoice_impl()` | `api/routes/invoices.py` | Map new fields from `InvoiceCreate` |
| 10 | Add `CustomerUpdate` `card_required` | `api/schemas/schemas.py` | Add optional field to existing update schema |
| 11 | Add `QuoteUpdate` `card_required` | `api/schemas/quotes.py` | Add optional field |
| 12 | Add `GET /api/v1/jobs/{id}/billable-items` endpoint | `api/routes/jobs.py` | Returns time entries + expenses; new `/test` counterpart |
| 13 | Add `BillableItemsResponse` schema | `api/schemas/schemas.py` | Response shape for billable items endpoint |
| 14 | Tests | `tests/domains/` | `field_operations/` for billable-items; `invoicing_billing/` for invoice fields |
| 15 | Regenerate `openapi.json` + `openapi_schema_map.md` | `export_openapi_json.py` | After all endpoints added |
| 16 | Regenerate `db_models_map.md` | `generate_db_model_map.py` | After all model changes |
| 17 | Update `pilot-db-schema-v2.6h.json` | `schema_manager.py --help` then appropriate CRUD command | CRUD script — run `--help` first; no `--sync` flag exists |

---

## D. New API Endpoints

### D.1 — `GET /api/v1/jobs/{job_id}/billable-items`

**Purpose**: Returns all time entries and expenses for a job that are eligible for invoicing. Used by the invoice builder (`FE-B29`) to pre-populate the line-item checklist when `/invoices/new?job_id={id}` is visited.

**Auth**: Required (Cognito JWT)  
**RBAC**: `require_permission("invoices.create")`  
**Tenant scope**: `job.tenant_id == current_user.tenant_id` (IDOR-safe)

**Path parameter**: `job_id: UUID`

**Response 200**: `BillableItemsResponse`
```json
{
  "job_id": "uuid",
  "job_number": "JOB-000001",
  "customer_name": "Acme Electric",
  "time_entries": [
    {
      "id": "uuid",
      "user_id": "uuid",
      "tech_name": "Jake Rodriguez",
      "started_at": "2026-07-01T08:00:00Z",
      "ended_at": "2026-07-01T12:00:00Z",
      "hours": "4.00",
      "hourly_rate_cents": 8500,
      "total_cost_cents": 34000,
      "notes": "Panel upgrade labor",
      "is_already_invoiced": false
    }
  ],
  "expenses": [
    {
      "id": "uuid",
      "description": "Wire 12AWG 50ft",
      "cost_cents": 4800,
      "billable_cents": 5280,
      "is_billable": true,
      "is_already_invoiced": false,
      "incurred_at": "2026-07-01T09:30:00Z"
    }
  ]
}
```

**`is_already_invoiced` logic**:
- For time entries: determined by whether `job_time_entry.id` appears in any `invoice_line` linked to a non-void, non-draft invoice for the same job. Since `job_time_entry` does not have a direct `invoice_line_id` FK, compute via: check if `invoice_line_id` in `job_expense` is set (expenses). For **time entries**, there is no direct FK to `invoice_line` — implement as `false` for MVP (always show all; the invoice builder frontend will show them as unchecked if a prior invoice exists for this job).
- For expenses: `job_expense.invoice_line_id IS NOT NULL` = already invoiced.

> **Simplification**: For MVP, `is_already_invoiced` for time entries is always `false`. The endpoint returns all time entries regardless. The frontend will warn the user if the job already has a non-draft invoice. This avoids a complex JOIN and is a known MVP deferral.

**Response 404**: Job not found in tenant (RFC 7807)  
**Response 403**: Insufficient permission

**Test endpoint**: `GET /api/v1/jobs/{job_id}/billable-items/test` (unauthenticated, uses `TestUserContext`)

---

### D.2 — No new CRUD endpoints for `card_required` or `payment_terms`

These fields are added to existing schemas:
- `CustomerCreate` / `CustomerResponse` — `card_required` field added
- `QuoteCreate` / `QuoteResponse` — `card_required` field added  
- `InvoiceCreate` / `InvoiceResponse` — `payment_terms`, `billing_mode`, `progress_pct`, `internal_memo` added

No new routes needed for these. The existing `POST /api/v1/customers/`, `POST /api/v1/quotes/`, and `POST /api/v1/invoices/` routes already accept these parent resources — the new fields flow through the existing `_create_*_impl()` functions.

---

### D.3 — `square_integration_enabled` Setting Access

**No new API endpoint for reading/writing settings.** The `platform_setting` system already has CRUD endpoints (verified in the codebase). Tenant owners can enable/disable Square integration via the existing settings system. The invoice builder endpoint will read `square_integration_enabled` from `platform_setting` if needed — but for B20, the flag is only persisted, not consumed by any endpoint (consumption is FE-B29's concern for flag-only display).

---

## E. Pattern Reuse Decisions

| Pattern | Applied Where | `mvp-arch.md` Reference |
|---|---|---|
| §16.5 Two-Tier Config | `square_integration_enabled` stored in `platform_setting` (not a new table column) | §16.5 — platform_setting + tenant override rows |
| 3-Part NOT NULL Migration | `invoice.billing_mode` (existing rows) + `customer.card_required` | §B.2 of batch design standards |
| IDOR-safe tenant-scoped select | `GET /api/v1/jobs/{id}/billable-items` — verify `job.tenant_id == current_user.tenant_id` before fetching | §7.1 of methods doc |
| `/test` endpoint pattern | `GET /api/v1/jobs/{id}/billable-items/test` uses `TestUserContext` | §11 inclusions file |
| RFC 7807 error format | All new endpoint errors | §13 inclusions file |
| `set_audit_context_sync()` | Not needed for GET-only endpoint; N/A for schema additions to existing endpoints | §9 inclusions file |
| Billing domain (`invoicing_billing/`) | Tests for invoice field additions | `README-adding-tests.md` domain mapping |
| Field operations domain (`field_operations/`) | Tests for `billable-items` endpoint | `README-adding-tests.md` domain mapping |

---

## F. Shared Module Interfaces

### F.1 — `BillableItemsResponse` Schema (new in `api/schemas/schemas.py`)

```python
class BillableTimeEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    tech_name: str | None  # user display name — joined from User table
    started_at: AwareDatetime
    ended_at: AwareDatetime | None
    hours: Decimal | None
    hourly_rate_cents: int
    total_cost_cents: int
    notes: str | None
    is_already_invoiced: bool = False  # MVP: always False for time entries


class BillableExpense(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    description: str
    cost_cents: int
    billable_cents: int
    is_billable: bool
    is_already_invoiced: bool  # True when job_expense.invoice_line_id IS NOT NULL
    incurred_at: AwareDatetime


class BillableItemsResponse(BaseModel):
    job_id: UUID
    job_number: str | None
    customer_name: str | None
    time_entries: list[BillableTimeEntry]
    expenses: list[BillableExpense]
```

### F.2 — Updated `InvoiceCreate` Schema (additions only)

```python
class InvoiceCreate(BaseModel):
    # ... existing fields unchanged ...
    payment_terms: str | None = None  # 'due_on_receipt'|'net_15'|'net_30'|'custom_date'
    billing_mode: str = "line_item"   # 'line_item'|'progress'
    progress_pct: Decimal | None = None  # 0.00–100.00 when billing_mode='progress'
    internal_memo: str | None = None   # internal note, not on PDF
```

### F.3 — Updated `InvoiceResponse` Schema (additions only)

```python
class InvoiceResponse(BaseModel):
    # ... existing fields unchanged ...
    payment_terms: str | None = None
    billing_mode: str = "line_item"
    progress_pct: Decimal | None = None
    internal_memo: str | None = None
```

### F.4 — Updated `CustomerCreate` + `CustomerResponse`

```python
# CustomerCreate addition:
card_required: bool = False

# CustomerResponse addition:
card_required: bool = False
```

### F.5 — Updated `QuoteCreate` + `QuoteResponse` (in `api/schemas/quotes.py`)

```python
# QuoteCreate addition:
card_required: bool | None = None  # None = inherit from customer.card_required

# QuoteResponse addition:
card_required: bool | None = None
```

### F.6 — `Invoice` SQLModel additions (in `app/models/billing.py`)

```python
payment_terms: str | None = Field(default=None, max_length=30)
billing_mode: str = Field(default="line_item", max_length=20)
progress_pct: Decimal | None = Field(default=None)
internal_memo: str | None = Field(default=None)
```

### F.7 — `Customer` SQLModel addition (in `app/models/crm.py`)

```python
card_required: bool = Field(default=False)
```

### F.8 — `Quote` SQLModel addition (in `app/models/quoting.py`)

```python
card_required: bool | None = Field(default=None)
```

---

## G. Open Questions Resolved

| Question | Resolution |
|---|---|
| `tenant_settings` table referenced in the launch plan doesn't exist — where does tenant-level config go? | `platform_setting` table with nullable `tenant_id` — the §16.5 Two-Tier pattern. Three new catalog keys: `square_integration_enabled`, `default_payment_terms`, `default_billing_mode`. |
| Should `payment_terms` be its own lookup table or an enum string? | VARCHAR(30) enum string: `due_on_receipt`, `net_15`, `net_30`, `custom_date`. DB-level CHECK constraint enforces validity. `platform_setting_catalog.allowed_values` mirrors the same enum for the settings API. |
| Must `default_payment_terms` and `default_invoice_terms_days` stay in sync? | **Yes — they are the same business rule expressed in two formats.** When a tenant changes payment terms in Settings, the settings API must write BOTH `default_payment_terms` (code) AND `default_invoice_terms_days` (integer days) atomically. The canonical mapping is: `due_on_receipt=0`, `net_15=15`, `net_30=30`. For `custom_date` the days count is irrelevant — invoices always carry an explicit `due_at`. If they drift out of sync, customers get dunning emails on the wrong schedule (dangerously wrong UX). |
| How does `_create_invoice_impl` compute `due_at`? | **Payment terms code → `due_at` mapping** (computed at creation, not at dunning time): `PAYMENT_TERMS_DAYS = {"due_on_receipt": 0, "net_15": 15, "net_30": 30}`. If `payment_terms in PAYMENT_TERMS_DAYS` and `issued_at` is set: `due_at = issued_at + timedelta(days=PAYMENT_TERMS_DAYS[payment_terms])`. If `payment_terms == "custom_date"`: `due_at` must be explicitly provided by the caller — 422 if absent. `due_at` is written to the invoice row. The dunning engine (`dunning.py`) reads `invoice.due_at` directly and never re-derives it — `today >= due_at` triggers overdue status regardless of how `due_at` was set. |
| How does the dunning worker handle `custom_date` invoices? | Identically to all other invoices: `dunning.py` compares `today >= invoice.due_at`. The `due_at` column is the single authoritative trigger. No special `custom_date` case in the worker. The FE-B29 builder simply sends the user-chosen calendar date as `due_at` when `payment_terms = 'custom_date'`. |
| Does `is_already_invoiced` on time entries require a complex join? | For MVP: always `false`. Time entries lack a direct `invoice_line_id` FK. Tracking per-entry invoicing is a Phase 1.5 enhancement. The frontend (FE-B29) shows a job-level warning if a prior non-draft invoice exists, rather than per-time-entry tracking. |
| `tech_name` in `BillableTimeEntry` — join or separate endpoint? | Single JOIN in the `billable-items` endpoint: `JOIN "user" ON job_time_entry.user_id = user.id` to get `user.display_name`. No separate endpoint. |
| Should `billing_mode` and `progress_pct` be validated at the API level? | Yes — add a Pydantic `model_validator`: if `billing_mode == 'progress'` then `progress_pct` must be between 0 and 100. If `billing_mode == 'line_item'` then `progress_pct` must be None or ignored. |
| `card_required` on `quote` — does it inherit from customer if NULL? | Yes. `quote.card_required IS NULL` means "inherit from `customer.card_required`". Frontend resolves the cascade; backend stores NULL as "not overridden". |
| Should the `billable-items` endpoint be scoped by `is_billable = true` for expenses? | Return ALL expenses (both billable and non-billable) but include the `is_billable` flag. The FE-B29 invoice builder pre-checks billable items and shows non-billable ones greyed-out/unchecked. This gives the owner the option to manually include non-billable items if needed. |
| What migration order matters? | Migration 1 (invoice fields + CHECK constraints) → Migration 2 (customer/quote card_required) → Migration 3 (data: platform_setting). Migrations 1 and 2 are independent and could run in either order. Migration 3 is data-only and can run last. |

### G.1 — `_create_invoice_impl()` Payment Terms → `due_at` Logic (REQUIRED in B20)

This logic must be implemented as part of Task 6 (updating `_create_invoice_impl`). It is architecturally critical — the dunning engine depends on `invoice.due_at` being set correctly at creation.

```python
from datetime import timedelta

PAYMENT_TERMS_DAYS: dict[str, int] = {
    "due_on_receipt": 0,
    "net_15": 15,
    "net_30": 30,
}

# In _create_invoice_impl(), after setting payment_terms on the invoice object:
if invoice_in.payment_terms in PAYMENT_TERMS_DAYS:
    if invoice_in.issued_at:
        invoice.due_at = invoice_in.issued_at + timedelta(
            days=PAYMENT_TERMS_DAYS[invoice_in.payment_terms]
        )
    # If issued_at not provided, due_at stays None — caller can set it later
elif invoice_in.payment_terms == "custom_date":
    if invoice_in.due_at is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "type": "https://errors.pilotfortrades.com/validation-error",
                "title": "Missing due_at",
                "status": 422,
                "detail": "due_at is required when payment_terms is 'custom_date'.",
            },
        )
    invoice.due_at = invoice_in.due_at
```

**`InvoiceCreate` schema addition** — expose `due_at` as an optional input field:
```python
due_at: AwareDatetime | None = None  # Required when payment_terms='custom_date'
```

**Dunning engine** (`tasks/dunning.py`) — no changes needed. It already compares `today >= invoice.due_at`. The `due_at` column is the single authoritative overdue trigger regardless of which payment terms mode created it.

---

*Design doc authored: 2026-07-11 | B20 depends on B19 ✅ | FE-B29 depends on B20*
