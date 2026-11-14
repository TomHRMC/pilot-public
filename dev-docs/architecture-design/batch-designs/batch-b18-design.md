# Batch B18 Design — CRUD Completeness: Job PATCH Endpoint + Invoice List Customer Name

**Batch Code**: B18  
**Type**: Backend only  
**Date**: 2026-07-10  
**Author**: Pilot Architect  
**Status**: Ready for implementation  
**Priority**: P1 — blocks FE-B24 (customer_name display) and FE-B25 (Job Edit UI)  
**Source Issue**: `dev-docs/testing-support/alpha-testing/ui-testing-status-2026-07-10.md`

---

## A. Input Read Summary

| Input | What Was Verified |
|---|---|
| `dev-docs/testing-support/alpha-testing/ui-testing-status-2026-07-10.md` | Issue #4 (Job Edit — no backend PATCH endpoint) and Issue #3 (Invoice list shows truncated UUID instead of customer name) are confirmed missing backend work |
| MCP live DB — `job` table columns | Verified: `customer_id`, `site_id`, `status_id`, `scheduled_start_at`, `scheduled_end_at`, `estimated_duration_minutes` are the mutable fields; `id`, `tenant_id`, `created_at`, `created_by`, `actual_labor_cost_cents`, `actual_material_cost_cents`, `actual_profit_cents`, `version` must not be writable via PATCH |
| MCP live DB — `invoice` table | Confirmed: `customer_id UUID NOT NULL` is on `invoice`. No `customer_name` column — must be JOIN-derived from `customer.display_name` |
| MCP live DB — `customer` table | Confirmed: `display_name VARCHAR NOT NULL` — this is the name to surface |
| `backend/api/routes/jobs.py` | Full read: `POST /` and `GET /` exist; `PATCH /{job_id}` does NOT exist. Pattern for `_impl()` / authenticated / test endpoint pairs is well-established. No `set_audit_context_sync()` calls in existing job route — must add to PATCH. |
| `backend/api/schemas/schemas.py` | `JobCreate`, `JobResponse`, `JobListItem` confirmed. No `JobUpdate` schema exists. `InvoiceSummary` has `customer_id` but no `customer_name`. `_list_invoices_impl` JOINs only `InvoiceStatus`, not `Customer`. |
| `backend/python-engr-std-prompt-inclusions.md` | Read in full — all required prompt sections identified |

---

## B. Migration Plan

**No Alembic migration is required for B18.** This batch makes no schema changes — it only adds a new endpoint and modifies the invoice list query and response schema. All DB tables (`job`, `invoice`, `customer`) already exist with the correct columns.

**Pre-Migration Verification (run via MCP before writing any code):**

```sql
-- 1. Confirm job table editable columns
SELECT column_name, data_type, is_nullable FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'job'
ORDER BY ordinal_position;

-- 2. Confirm customer.display_name exists and is NOT NULL
SELECT column_name, data_type, is_nullable FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'customer'
AND column_name = 'display_name';

-- 3. Confirm invoice.customer_id is NOT NULL
SELECT column_name, data_type, is_nullable FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'invoice'
AND column_name = 'customer_id';

-- 4. Confirm alembic head (no pending migrations)
SELECT version_num FROM public.alembic_version;
```

---

## C. Execution Order

| Step | Task | File(s) |
|---|---|---|
| 1 | Add `JobUpdate` schema to `api/schemas/schemas.py` | `backend/api/schemas/schemas.py` |
| 2 | Add `_update_job_impl()` + `PATCH /{job_id}` authenticated endpoint + `PATCH /{job_id}/test` test endpoint to `jobs.py` | `backend/api/routes/jobs.py` |
| 3 | Add `customer_name: str \| None = None` to `InvoiceSummary` in `api/schemas/schemas.py` | `backend/api/schemas/schemas.py` |
| 4 | Update `_list_invoices_impl()` in `invoices.py` to JOIN `Customer` and populate `customer_name` | `backend/api/routes/invoices.py` |
| 5 | Run Phase 1 unit tests — fix any regressions | — |
| 6 | Regenerate `openapi.json` + `openapi_schema_map.md` | `python export_openapi_json.py` |
| 7 | Regenerate `db_models_map.md` (no model changes, but verify) | — |
| 8 | Write unit tests for new PATCH endpoint and customer_name field | `backend/tests/domains/field_operations/` and `backend/tests/domains/invoicing_billing/` |
| 9 | Run Phase 2 full suite | — |

---

## D. New API Endpoints

### D1. `PATCH /api/v1/jobs/{job_id}`

| Field | Value |
|---|---|
| **Path** | `/api/v1/jobs/{job_id}` |
| **Method** | `PATCH` |
| **Auth** | Required — Cognito JWT |
| **RBAC** | `require_permission("jobs.update")` |
| **Request Schema** | `JobUpdate` (all fields optional) |
| **Response Schema** | `JobResponse` (existing schema, 200) |
| **Error Codes** | 404 (job not found), 422 (validation), 400 (site not belonging to customer) |

**`JobUpdate` schema** (all fields optional — send only what you want to change):

```python
class JobUpdate(BaseModel):
    customer_id: UUID | None = None
    site_id: UUID | None = None
    scheduled_start_at: datetime | None = None
    scheduled_end_at: datetime | None = None
    estimated_duration_minutes: int | None = None
```

**Business logic in `_update_job_impl()`:**
1. Fetch job tenant-scoped: `WHERE id = job_id AND tenant_id = tenant_id` → 404 if not found
2. Call `set_audit_context_sync(db, user_id=current_user.id)` — mandatory before any write
3. If `customer_id` provided: verify customer belongs to tenant → 404 if not
4. If `site_id` provided: verify site belongs to tenant → 404 if not  
5. If both `customer_id` and `site_id` provided: verify site belongs to customer → 400 if not
6. If only `site_id` provided (without new `customer_id`): verify site belongs to the existing `job.customer_id` → 400 if not
7. Apply `model_dump(exclude_unset=True)` updates via `setattr`
8. `db.add(job)`, `db.commit()`, `db.refresh(job)`, `return job`

**Test endpoint**: `PATCH /api/v1/jobs/{job_id}/test` — no auth, uses `get_test_context()`

**Note**: `status_id` is intentionally excluded from `JobUpdate`. Status transitions are managed by the dispatch board / workflow state machine, not directly via the edit form. Including it here would bypass status transition guards.

### D2. `InvoiceSummary` — add `customer_name` field (no new route)

The existing `GET /api/v1/invoices/` route already returns `InvoiceListResponse`. The change is:

1. Add `customer_name: str | None = None` to `InvoiceSummary` schema
2. Update `_list_invoices_impl()` to JOIN `Customer` and populate `customer_name` from `Customer.display_name`

**Updated query pattern in `_list_invoices_impl()`:**

```python
from app.models.crm import Customer

query = (
    select(Invoice, InvoiceStatus, Customer)
    .join(InvoiceStatus, Invoice.status_id == InvoiceStatus.id)
    .join(Customer, Invoice.customer_id == Customer.id, isouter=True)  # outer join — in case of orphan
    .where(Invoice.tenant_id == user_context.tenant_id)
    .where(Customer.tenant_id == user_context.tenant_id)  # IDOR protection
)

# In the row loop:
for invoice, invoice_status_obj, customer in rows:
    summary = InvoiceSummary(
        **invoice.model_dump(),
        status_code=invoice_status_obj.code,
        customer_name=customer.display_name if customer else None,
    )
```

**IDOR note**: `.where(Customer.tenant_id == user_context.tenant_id)` is required even though `invoice.customer_id` FK ensures the customer exists — it prevents cross-tenant data access per §7.1 of `pilot-architect-methods.md`.

---

## E. Pattern Reuse Decisions

| Pattern | Applied |
|---|---|
| `_impl()` / authenticated / `/test` three-layer endpoint pattern | Yes — `_update_job_impl()` shared between `PATCH /{job_id}` and `PATCH /{job_id}/test` |
| `db.get()` permanently banned on tenant-scoped models (§7.1) | Yes — all fetches use `select().where(tenant_id == ...)` |
| `set_audit_context_sync()` on every mutation | Yes — mandatory in `_update_job_impl()` |
| RFC 7807 Problem Details for errors | Yes — all HTTPException calls use dict detail |
| Return 404 (never 403) for tenant-scoped not-found | Yes — prevents UUID enumeration |
| JOIN for denormalized fields (no computed columns) | Yes — `customer_name` derived via SQL JOIN, not stored |

---

## F. Shared Module Interfaces

No new Celery tasks. No new services. No changes to existing services.

**Function signature for new `_update_job_impl`:**

```python
def _update_job_impl(
    job_id: UUID,
    job_update: JobUpdate,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> Job:
    """
    Update mutable fields on a job. Validates customer/site ownership.
    Raises HTTPException 404 if job not found in tenant.
    Raises HTTPException 400 if site does not belong to the specified/existing customer.
    """
```

---

## G. Open Questions Resolved

| Question | Resolution |
|---|---|
| Should `status_id` be patchable via this endpoint? | **No.** Status transitions must go through the dispatch board workflow. Including it here bypasses guards. |
| Should `quote_id` be patchable? | **No.** Quote linkage is set at job creation from an accepted quote. Changing it post-creation has billing implications. Excluded from `JobUpdate`. |
| Should the PATCH also handle re-scheduling (calendar sync)? | **No — out of scope for B18.** Calendar sync re-triggering is a separate concern. The PATCH updates the `scheduled_start_at`/`scheduled_end_at` fields; any downstream calendar re-sync is a follow-up task. |
| How to handle `customer_name` when invoice has no customer (orphan invoice)? | The outer join + `None` fallback is correct — `customer_name: str \| None = None` on `InvoiceSummary`. |
| Does adding `customer_name` to `InvoiceSummary` break any existing tests? | It may if tests assert on the exact shape of `InvoiceSummary`. The field is optional (`None` default), so existing tests should pass without modification. However, test mock data should be checked. |
| Should `_list_invoices_impl` count query also join Customer? | No — the count query counts `Invoice` rows, not customer joins. Adding Customer to the count query is unnecessary and would risk double-counting on outer joins. Count query stays as-is. |

---

## Test Requirements

**New test files:**

| Test File | Domain | Min Tests |
|---|---|---|
| `backend/tests/domains/field_operations/test_b18_job_patch.py` | `field_operations` | 5 |
| `backend/tests/domains/invoicing_billing/test_b18_invoice_customer_name.py` | `invoicing_billing` | 3 |

**`test_b18_job_patch.py` — minimum scenarios:**
1. Happy path: PATCH job with new `scheduled_start_at` returns 200 with updated field
2. PATCH job with `customer_id` not in tenant returns 404
3. PATCH job with `site_id` that belongs to a different customer returns 400
4. PATCH job with `job_id` not in tenant returns 404
5. PATCH with no fields set (empty body `{}`) returns 200 with unchanged job

**`test_b18_invoice_customer_name.py` — minimum scenarios:**
1. `GET /api/v1/invoices/test` returns `items[n].customer_name` as non-null string
2. `customer_name` matches the `display_name` of the customer linked to the invoice
3. Second tenant's invoices do NOT appear in first tenant's list (IDOR test)

---

## Handoff to Frontend

After B18 completes:
1. Run `python export_openapi_json.py` — verify `PATCH /api/v1/jobs/{job_id}` and `customer_name` in `InvoiceSummary` appear in `openapi_schema_map.md`
2. Commit openapi changes
3. Notify React Engineer to run `pnpm sync-api-types` before starting FE-B24 and FE-B25

**FE-B24** (frontend fixes batch) depends on B18 for the `customer_name` display feature.  
**FE-B25** (Job Edit UI) depends on B18 for `PATCH /api/v1/jobs/{job_id}`.
