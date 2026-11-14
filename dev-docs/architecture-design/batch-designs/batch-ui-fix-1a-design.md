# Batch UI-FIX-1A — Seed Data Repair + InvoiceResponse Payments

**Type**: Backend (Python Engineer)  
**Status**: 🟡 Ready for implementation  
**Designed**: 2026-07-17  
**Source findings**: `dev-docs/architecture-design/batch-designs/ui-fix-1-decisions.md`  
**Fixes addressed**: FIX-003, FIX-005, FIX-006, FIX-007, FIX-008, FIX-011, FIX-012, FIX-013-BE  
**Estimated effort**: 4–5 hours  
**Frontend companion**: UI-FIX-1B — must wait for UI-FIX-1A to close + `pnpm sync-api-types` to run  

---

## Table of Contents

- [Batch UI-FIX-1A — Seed Data Repair + InvoiceResponse Payments](#batch-ui-fix-1a--seed-data-repair--invoiceresponse-payments)
  - [Table of Contents](#table-of-contents)
  - [A. Input Read Summary](#a-input-read-summary)
  - [B. Migration Plan](#b-migration-plan)
  - [C. Execution Order](#c-execution-order)
  - [D. New API Changes](#d-new-api-changes)
    - [FIX-013-BE — Add payments to InvoiceResponse](#fix-013-be--add-payments-to-invoiceresponse)
  - [E. Pattern Reuse Decisions](#e-pattern-reuse-decisions)
  - [F. Shared Module Interfaces](#f-shared-module-interfaces)
  - [G. Open Questions Resolved](#g-open-questions-resolved)

---

## A. Input Read Summary

| Input | Key finding |
|---|---|
| `ui-fix-1-decisions.md` — FIX-003 | SMS body uses fictional `pay.pilotfortrades.com` URL — must use `https://app.pilotfortrades.com/i/EXAMPLE_TOKEN_abc123` |
| `ui-fix-1-decisions.md` — FIX-005 | 3 scheduled jobs have zero `job_assignment` rows; scheduled dates are past fixed dates |
| `ui-fix-1-decisions.md` — FIX-006 | All `in_progress`/`scheduled` jobs have zero `job_time_entry`, `job_expense`, `job_note` rows |
| `ui-fix-1-decisions.md` — FIX-007 | Only 3 invoices (40-day, 57-day, 19-day); no current, 30+, or 90+ buckets |
| `ui-fix-1-decisions.md` — FIX-008 | Quote titles embed status in the title string (e.g. "Panel Upgrade — Pending Internal Approval") |
| `ui-fix-1-decisions.md` — FIX-011 | `INV-SEED-A` through `INV-SEED-G` must be renamed to `INV-900002`–`INV-900008`; cross-refs in notifications script |
| `ui-fix-1-decisions.md` — FIX-012 | All customer `email` → `info@pilotfortrades.com`, `mobile_phone` → `+14105550123` (E.164) |
| `ui-fix-1-decisions.md` — FIX-013-BE | `InvoiceResponse` has no `payments` field; `InvoiceDetailPage` always renders empty payment history |
| MCP — `invoice` table | Columns confirmed: `id`, `tenant_id`, `invoice_number`, `status_id`, `due_at`, `balance_due_cents`, `issued_at`, etc. |
| MCP — `payment` table | Columns confirmed: `id`, `tenant_id`, `invoice_id`, `amount_cents`, `paid_at`, `psp_provider`, `paid_via`, `customer_payment_comment`, `status_id` |
| MCP — `payment_status` | Codes: `canceled`, `failed`, `pending`, `refunded`, `succeeded` |
| MCP — `job_time_entry` table | Columns confirmed: `id`, `tenant_id`, `job_id`, `user_id`, `started_at`, `ended_at`, `hours`, `hourly_rate_cents`, `total_cost_cents`, `notes`, `hours_remaining_estimate` |
| MCP — `job_assignment` table | Columns confirmed: `id`, `tenant_id`, `job_id`, `user_id`, `is_lead`, `is_active` |
| MCP — `due_before` already live | `GET /api/v1/invoices/` already accepts `?due_before=` — no backend change needed for FIX-010 |
| `openapi_schema_map.md` — `InvoiceResponse` | Currently has `lines: list[InvoiceLineResponse]` but **no `payments` field** |
| `backend/api/schemas/schemas.py` | Confirmed `InvoiceResponse` schema — no payments field; `PaymentResponse` exists at line 653 but is for the record-payment endpoint, not the detail response |

---

## B. Migration Plan

**No Alembic migrations required.** All changes are:
1. Seed script modifications (data-only — existing tables, existing schema)
2. Pydantic schema additions (`schemas.py` — API layer only, no DB changes)
3. Route handler updates (`invoices.py` — JOIN addition only)

There are **no new tables, no new columns, no Alembic migrations** in this batch.

---

## C. Execution Order

| # | Task | File(s) | Fix |
|---|---|---|---|
| 1 | Rename `INV-SEED-*` invoice numbers | `seed_scenario_reporting.py`, `seed_scenario_notifications.py` | FIX-011 |
| 2 | Fix customer email + phone | `seed_scenario_quote_to_cash.py`, `seed_test_tenant.py` | FIX-012 |
| 3 | Fix quote titles | `seed_scenario_quote_to_cash.py` | FIX-008 |
| 4 | Fix SMS body URL | `seed_scenario_customer_comms.py` | FIX-003 |
| 5 | Add `job_assignment` rows + fix scheduled dates | `seed_scenario_reporting.py` (or the seed script that owns jobs) | FIX-005 |
| 6 | Add `job_time_entry`, `job_expense`, `job_note` rows | Same seed script(s) that own jobs | FIX-006 |
| 7 | Add 6 new AR aging invoices | `seed_scenario_reporting.py` | FIX-007 |
| 8 | Add `PaymentSummaryResponse` schema + `payments` to `InvoiceResponse` | `backend/api/schemas/schemas.py` | FIX-013-BE |
| 9 | Update `get_invoice()` handler to JOIN + return payments | `backend/api/routes/invoices.py` | FIX-013-BE |
| 10 | Regenerate OpenAPI + verify | `python export_openapi_json.py` | All |

---

## D. New API Changes

### FIX-013-BE — Add payments to InvoiceResponse

**No new endpoint.** Change is purely additive to the existing `GET /api/v1/invoices/{invoice_id}` response.

#### New Pydantic Schema: `PaymentSummaryResponse`

Add to `backend/api/schemas/schemas.py` **before** `InvoiceResponse` class:

```python
class PaymentSummaryResponse(BaseModel):
    """Payment summary embedded in InvoiceResponse."""

    model_config = ConfigDict(from_attributes=True, extra="ignore")

    id: UUID
    amount_cents: int
    paid_at: datetime | None
    paid_via: str | None
    psp_provider: str | None
    customer_payment_comment: str | None
    status_id: UUID
```

> **MCP-verified fields** (all exist in `payment` table): `id`, `amount_cents`, `paid_at`, `paid_via`, `psp_provider`, `customer_payment_comment`, `status_id`

#### Add `payments` field to `InvoiceResponse`

Append to `InvoiceResponse` after `lines`:

```python
payments: list[PaymentSummaryResponse] = []
```

#### Update `get_invoice()` handler

File: `backend/api/routes/invoices.py` — `get_invoice()` function at approximately line 1081.

Read the full function before modifying. The change: after fetching the invoice, query the `payment` table for all payments for that invoice and populate the response:

```python
from app.models.payment import Payment  # verify exact import path by reading invoices.py

# After fetching invoice (tenant-scoped select — db.get() is BANNED):
invoice = db.exec(
    select(Invoice)
    .where(Invoice.id == invoice_id)
    .where(Invoice.tenant_id == current_user.tenant_id)
).first()
if not invoice:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={
            "type": "https://errors.pilotfortrades.com/not-found",
            "title": "Invoice not found",
            "status": 404,
            "detail": f"Invoice {invoice_id} does not exist in this tenant.",
        },
    )

# ADD: fetch payments for this invoice
payments = db.exec(
    select(Payment)
    .where(Payment.invoice_id == invoice_id)
    .where(Payment.tenant_id == current_user.tenant_id)
    .where(Payment.is_active == True)
    .order_by(Payment.paid_at.desc().nulls_last())
).all()

# Build response — pass payments to the response model
response = InvoiceResponse.model_validate(invoice)
response.payments = payments
return response
```

> **Important**: Read the actual `get_invoice()` function body before implementing. The `InvoiceResponse` model has `model_config = ConfigDict(from_attributes=True)` so `model_validate(invoice)` works. Payments must be separately fetched and assigned.

**No changes to `list_invoices()` or `list_invoices_test()`.** The `InvoiceListResponse` uses `InvoiceSummary` (not `InvoiceResponse`), so payments are not embedded in list views.

**The `/test` variant** (`GET /api/v1/invoices/{invoice_id}/test`) must also be updated if it calls a different handler. Verify by reading the route file.

---

## E. Pattern Reuse Decisions

| Pattern | Decision |
|---|---|
| Tenant-scoped `select()` | All seed scripts already use `WHERE tenant_id = :tid`. New code in `get_invoice()` must follow the same pattern — `db.get()` is permanently banned. |
| `ON CONFLICT DO NOTHING` | All new seed data INSERTs must use this for idempotency (scripts can be re-run after a DB reset). |
| Relative dates in seed data | FIX-005: `scheduled_start_at` values must use `NOW() + interval 'X days'` so the dispatch board shows current data on any run date. |
| RFC 7807 errors | `get_invoice()` already has correct error format — do not introduce plain string `detail` in any new code path. |

---

## F. Shared Module Interfaces

No new Celery tasks. No new shared service functions. All changes are:
- Seed data only (Python dict/INSERT changes in existing scripts)
- Pydantic schema additions (`schemas.py`)
- Route handler JOIN addition (`invoices.py`)

---

## G. Open Questions Resolved

| Question | Resolution |
|---|---|
| Which seed script owns the `job_assignment` rows? | Read `seed_scenario_reporting.py` before starting — jobs may be seeded there or in a separate jobs script. The Python Engineer must run `grep -rn "job_assignment" backend/migrations/scripts/` to locate the owning script. |
| Do we need a `job_expense` schema to understand its columns? | MCP showed `job_expense` table exists. Python Engineer must run `SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'job_expense' ORDER BY ordinal_position;` as part of pre-work MCP queries before writing any INSERT. |
| Do we need a `job_note` schema? | Same — Python Engineer must MCP-verify `job_note` table columns before writing any INSERT. |
| Does `reset_dev_db.py` need updating for new invoice numbers? | No — `reset_dev_db.py` deletes by `tenant_id`, not by invoice number. No changes needed there. |
| Is `due_before` backend work needed for FIX-010? | **No — already live.** `GET /api/v1/invoices/` already accepts `?due_before=` (confirmed in `openapi_schema_map.md`). FIX-010 is a frontend-only change (UI-FIX-1B). |
| Does `InvoiceResponse.payments` affect the `/test` endpoint? | The `/test` variant is a separate handler — Python Engineer must verify it and update if it calls the same underlying logic as the authenticated handler. |
| Which `seed_scenario_*` scripts own customer rows? | FIX-012 specifies `seed_scenario_quote_to_cash.py` + `seed_test_tenant.py`. Python Engineer must `grep -rn "mobile_phone\|email.*customer" backend/migrations/scripts/` to find all customer INSERT locations. |
| FIX-006 — does `job_note` exist or is it `job_notes`? | Python Engineer must run `SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_name LIKE '%note%';` to confirm the exact table name before writing any INSERT. |
