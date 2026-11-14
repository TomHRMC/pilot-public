# Implementation Prompt: B18 — Job PATCH Endpoint + Invoice List Customer Name

**Mode**: Pilot Python Engineer  
**Batch**: B18  
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §Integration & UI Hardening  
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-b18-design.md`  
**Estimated session**: 2–3 hours  
**Platform**: Backend only (`backend/`)  
**Frontend companion**: FE-B24 (invoice customer name display) + FE-B25 (Job Edit UI) — both depend on this batch

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`dev-docs/architecture-design/pilot-python-engineer-methods.md`** — §13 (Alembic), §8 (Router Design), §5 (Model Design), §16 (Standard Task Workflow)
- **`backend/tests/README-adding-tests.md`** — full document; governs all test file structure, domain markers, and fixture rules

**Critical rules for this batch:**

- **Rule 1**: Never guess column names, data types, or table names. Use `postgres-local` MCP to verify every name before use. If MCP returns an error → **STOP and ask Tom**.
- **Rule 2**: After any endpoint change → run `python export_openapi_json.py` (updates both `openapi.json` and `openapi_schema_map.md`).
- **Rule 3**: All Alembic migrations must be written as **blank** migrations. This batch has **no migrations** — do NOT create one.
- **Rule 4**: Never use module-level `TestClient` in any test file. Always use the `client` fixture from `conftest.py`.
- **Rule 5**: `db.get()` is permanently banned on tenant-scoped models. Always use tenant-scoped `select()` with explicit `WHERE tenant_id = :tid`.
- **Rule 6**: Every mutation endpoint MUST call `set_audit_context_sync(db, user_id=user.id)` before committing. Without this, `actor_id` is NULL in `audit_log`.
- **Rule 7**: All API error responses MUST follow RFC 7807 Problem Details format (`{"type": "...", "title": "...", "status": N, "detail": "..."}`).
- **Rule 8**: The `postgres-local` MCP is **read-only verification only**. Never use it to INSERT, UPDATE, or DELETE.

> **MCP Usage Rule**: The `postgres-local` MCP is for read-only verification only. Use it to confirm table names, column types, and existing data. If a query fails → STOP and ask Tom.

---

## Pre-Work: Establish Regression Baseline

Before touching any file, capture the current **unit-only** test baseline:

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=no -q 2>&1 | tail -5
```

Record the exact count: **`X passed, Y failed`**.

> **If any tests are already failing before you start**: Do NOT proceed. Fix the failure or confirm with Tom before touching any batch files.

---

## Pre-Work: Run MCP Verification Queries

Run **all** of these via `postgres-local` MCP before writing any code. If any query returns unexpected results → **STOP and ask Tom**.

```sql
-- 1. Confirm job table mutable columns exist exactly as designed
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'job'
ORDER BY ordinal_position;

-- 2. Confirm customer.display_name exists and is NOT NULL
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'customer'
AND column_name = 'display_name';

-- 3. Confirm invoice.customer_id exists and is NOT NULL
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'invoice'
AND column_name = 'customer_id';

-- 4. Confirm no PATCH /jobs/ endpoint exists yet (sanity check — look at DB for JobStatus.code)
SELECT code FROM job_status LIMIT 10;

-- 5. Confirm current alembic head (no pending migrations)
SELECT version_num FROM public.alembic_version;
```

**Expected results:**
- `job` table has: `id`, `tenant_id`, `customer_id`, `site_id`, `status_id`, `scheduled_start_at`, `scheduled_end_at`, `estimated_duration_minutes`, `is_active` (and others)
- `customer.display_name` exists, is `VARCHAR`, `NOT NULL`
- `invoice.customer_id` exists, is `UUID`, `NOT NULL`

---

## Pre-Work: Read These Source Files

Use `read_file` on each of these before writing any code:

```
backend/api/routes/jobs.py                    ← understand existing _impl() pattern, test endpoint placement, auth patterns
backend/api/routes/invoices.py (lines 395–468) ← understand _list_invoices_impl() join pattern to modify
backend/api/schemas/schemas.py (lines 150–205) ← understand existing JobCreate, JobResponse, JobListItem
backend/api/schemas/schemas.py (lines 443–475) ← understand InvoiceSummary and InvoiceListResponse
backend/app/models/crm.py                     ← understand Customer model for JOIN
backend/tests/conftest.py                     ← confirm test_job, test_customer, test_invoice_status fixtures
backend/db_models_map.md                      ← confirm model names and table mappings
```

Also run:
```bash
grep -rn "InvoiceSummary\|_list_invoices_impl\|from app.models.crm" backend/api/routes/invoices.py | head -20
grep -rn "JobUpdate\|JobCreate\|JobResponse" backend/api/schemas/schemas.py | head -10
```

---

## Background / Context

This batch closes two of the five gaps discovered in alpha testing on 2026-07-10:

1. **Gap #4 (Issue #4)**: `PATCH /api/v1/jobs/{job_id}` does not exist. The frontend cannot implement a "Edit Job" form without this endpoint. This is an owner workflow gap (🟡 Important).

2. **Gap #3 (Issue #3)**: `GET /api/v1/invoices/` returns `InvoiceSummary` which has `customer_id` (a UUID) but no `customer_name`. The frontend renders a truncated UUID (`customer_id.slice(0,8)…`) instead of the customer's display name. This is a 🔴 critical demo bug.

**No Alembic migration is required.** All DB tables (`job`, `invoice`, `customer`) have the correct columns. This batch only adds one new endpoint and modifies one query + one schema.

---

## Task 1 — Add `JobUpdate` Schema to `api/schemas/schemas.py`

**File**: `backend/api/schemas/schemas.py`

Add a new `JobUpdate` class immediately after the `JobListItem` class (around line 202):

```python
class JobUpdate(BaseModel):
    """Request to update mutable fields on an existing job.
    
    All fields are optional — only send the fields you want to change.
    status_id is intentionally excluded — status transitions go through 
    the dispatch board workflow, not this endpoint.
    quote_id is intentionally excluded — quote linkage set at job creation.
    """
    customer_id: UUID | None = None
    site_id: UUID | None = None
    scheduled_start_at: datetime | None = None
    scheduled_end_at: datetime | None = None
    estimated_duration_minutes: int | None = None
```

Also add `JobUpdate` to the import in `api/routes/jobs.py` (Step 2 below will handle this).

Run intermediate unit test after this step:
```bash
python -m pytest -m unit --tb=short -q 2>&1 | tail -5
```

---

## Task 2 — Add `_update_job_impl()` + PATCH endpoints to `jobs.py`

**File**: `backend/api/routes/jobs.py`

### 2A. Import `JobUpdate` and `set_audit_context_sync`

Add to the existing imports at the top of `jobs.py`:

```python
from api.schemas.schemas import (
    # ... existing imports ...
    JobUpdate,  # ADD THIS
)
from core.db import get_db, set_audit_context_sync  # ADD set_audit_context_sync
```

### 2B. Add `_update_job_impl()` shared function

Add this function in the `# ==================== SHARED BUSINESS LOGIC ====================` section, after `_get_job_impl()`:

```python
def _update_job_impl(
    job_id: UUID,
    job_update: JobUpdate,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> Job:
    """
    Update mutable fields on a job (customer, site, schedule).
    
    Business logic:
    - Validates job belongs to tenant (IDOR protection)
    - If customer_id provided: validates customer belongs to tenant
    - If site_id provided: validates site belongs to tenant
    - If both customer_id and site_id provided: validates site belongs to customer
    - If only site_id provided: validates site belongs to existing job.customer_id
    - Applies only the fields that were sent (exclude_unset)
    
    status_id is intentionally excluded from JobUpdate.
    """
    # 1. Tenant-scoped job fetch — db.get() BANNED per §7.1
    job = db.exec(
        select(Job)
        .where(Job.id == job_id)
        .where(Job.tenant_id == user_context.tenant_id)
    ).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "type": "https://errors.pilotfortrades.com/not-found",
                "title": "Job not found",
                "status": 404,
                "detail": f"Job {job_id} does not exist in this tenant.",
            },
        )

    update_data = job_update.model_dump(exclude_unset=True)

    # Determine effective customer_id for site validation
    effective_customer_id = update_data.get("customer_id", job.customer_id)

    # 2. If customer_id is being changed, validate it belongs to tenant
    if "customer_id" in update_data:
        customer = db.exec(
            select(Customer)
            .where(Customer.id == update_data["customer_id"])
            .where(Customer.tenant_id == user_context.tenant_id)
        ).first()
        if not customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "type": "https://errors.pilotfortrades.com/not-found",
                    "title": "Customer not found",
                    "status": 404,
                    "detail": f"Customer {update_data['customer_id']} does not exist in this tenant.",
                },
            )

    # 3. If site_id is being changed, validate it belongs to tenant + effective customer
    if "site_id" in update_data:
        site = db.exec(
            select(Site)
            .where(Site.id == update_data["site_id"])
            .where(Site.tenant_id == user_context.tenant_id)
        ).first()
        if not site:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "type": "https://errors.pilotfortrades.com/not-found",
                    "title": "Site not found",
                    "status": 404,
                    "detail": f"Site {update_data['site_id']} does not exist in this tenant.",
                },
            )
        if site.customer_id != effective_customer_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "type": "https://errors.pilotfortrades.com/validation",
                    "title": "Site does not belong to customer",
                    "status": 400,
                    "detail": "The specified site does not belong to the specified (or existing) customer.",
                },
            )

    # 4. Apply updates
    for key, val in update_data.items():
        setattr(job, key, val)

    db.add(job)
    db.commit()
    db.refresh(job)
    return job
```

### 2C. Add test endpoint (BEFORE authenticated endpoint — register first)

In the `# ==================== TEST ENDPOINTS (UNAUTHENTICATED) ====================` section, add AFTER `get_job_test()`:

```python
@router.patch("/{job_id}/test", response_model=JobResponse)
def update_job_test(
    job_id: UUID,
    job_update: JobUpdate,
    db: Session = Depends(get_db),
):
    """
    Update a job (TEST ENDPOINT — no authentication required).
    
    Security:
        - Only available when TEST_ENDPOINT_ENABLED=true
        - Blocked in staging/production
    """
    test_context = get_test_context()
    return _update_job_impl(job_id, job_update, db, test_context)
```

### 2D. Add authenticated PATCH endpoint

In the `# ==================== AUTHENTICATED ENDPOINTS ====================` section, add AFTER `get_job()`:

```python
@router.patch("/{job_id}", response_model=JobResponse)
def update_job(
    job_id: UUID,
    job_update: JobUpdate,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("jobs.update")),
):
    """
    Update a job's mutable fields (requires JWT and jobs.update permission).
    
    Updatable fields: customer_id, site_id, scheduled_start_at, scheduled_end_at,
    estimated_duration_minutes. All fields are optional — send only what changes.
    
    status_id is NOT updatable via this endpoint — status transitions use the
    dispatch board workflow.
    
    Security:
        - Requires valid JWT token
        - Requires jobs.update permission
        - Job must belong to authenticated user's tenant
    """
    set_audit_context_sync(db, user_id=current_user.id)
    return _update_job_impl(job_id, job_update, db, current_user)
```

Run intermediate unit test:
```bash
python -m pytest -m unit --tb=short -q 2>&1 | tail -5
```

---

## Task 3 — Add `customer_name` to `InvoiceSummary` schema

**File**: `backend/api/schemas/schemas.py`

Update `InvoiceSummary` class to add `customer_name` field:

```python
class InvoiceSummary(BaseModel):
    """Summary of invoice for list response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    invoice_number: str
    customer_id: UUID
    customer_name: str | None = None  # ADD THIS — from customer JOIN in _list_invoices_impl
    site_id: UUID
    status_id: UUID
    status_code: str
    issued_at: datetime | None
    due_at: datetime | None
    subtotal_cents: int
    tax_cents: int
    total_cents: int
    balance_due_cents: int
    currency: str
    quote_id: UUID | None
    job_id: UUID | None
    created_at: datetime
    updated_at: datetime
```

The `customer_name` field is `str | None = None` (optional) so existing tests that construct `InvoiceSummary` without this field will not break.

---

## Task 4 — Update `_list_invoices_impl()` to JOIN Customer

**File**: `backend/api/routes/invoices.py`

### 4A. Add Customer import

At the top of `invoices.py`, update the CRM import:

```python
from app.models.crm import Customer  # ADD THIS (may need to add, check existing imports)
```

If `Customer` is not already imported in `invoices.py`, add it. Check first:
```bash
grep -n "from app.models.crm" backend/api/routes/invoices.py
```

### 4B. Update `_list_invoices_impl()` query

Read the full `_list_invoices_impl()` function (lines ~395–468) before modifying.

**Modify the query** to JOIN Customer:

```python
from app.models.crm import Customer  # ensure imported

def _list_invoices_impl(...) -> InvoiceListResponse:
    """Shared list-invoices logic for both authenticated and test endpoints."""
    now = datetime.now(UTC)

    query = (
        select(Invoice, InvoiceStatus, Customer)           # ADD Customer
        .join(InvoiceStatus, Invoice.status_id == InvoiceStatus.id)
        .join(Customer, Invoice.customer_id == Customer.id, isouter=True)  # ADD — outer join
        .where(Invoice.tenant_id == user_context.tenant_id)
        .where(Customer.tenant_id == user_context.tenant_id)  # IDOR protection
    )
    # ... rest of filters unchanged ...
```

**Modify the row loop** to unpack 3 values and populate `customer_name`:

```python
    # OLD:
    for invoice, invoice_status_obj in rows:
        summary = InvoiceSummary(
            **invoice.model_dump(),
            status_code=invoice_status_obj.code,
        )

    # NEW:
    for invoice, invoice_status_obj, customer in rows:
        summary = InvoiceSummary(
            **invoice.model_dump(),
            status_code=invoice_status_obj.code,
            customer_name=customer.display_name if customer else None,
        )
```

> **Important**: The count query (`count_query`) does NOT need to change — it counts `Invoice` rows, not customer joins. Leave the count query unchanged.

Run intermediate unit test:
```bash
python -m pytest -m unit --tb=short -q 2>&1 | tail -5
```

---

## Task 5 — Write Tests

### Test File 1: `backend/tests/domains/field_operations/test_b18_job_patch.py`

```python
import pytest
from uuid import UUID

pytestmark = [
    pytest.mark.domain_field_operations,
    pytest.mark.unit,
]


def test_patch_job_schedule_returns_200(client, test_tenant, mock_cognito_jwt):
    """Happy path: PATCH with new scheduled_start_at returns 200 with updated field."""
    # Create a job first
    resp = client.post("/api/v1/jobs/test", json={
        "customer_id": str(test_tenant.customer_id),  # use fixture IDs
        "site_id": str(test_tenant.site_id),
    })
    assert resp.status_code == 201
    job_id = resp.json()["id"]

    # PATCH it
    patch_resp = client.patch(f"/api/v1/jobs/{job_id}/test", json={
        "scheduled_start_at": "2026-09-01T09:00:00Z",
        "scheduled_end_at": "2026-09-01T17:00:00Z",
    })
    assert patch_resp.status_code == 200
    data = patch_resp.json()
    assert data["id"] == job_id
    assert "2026-09-01" in data["scheduled_start_at"]


def test_patch_job_empty_body_returns_200_unchanged(client, test_tenant):
    """PATCH with empty body {} returns 200 with unchanged job."""
    resp = client.post("/api/v1/jobs/test", json={
        "customer_id": str(test_tenant.customer_id),
        "site_id": str(test_tenant.site_id),
    })
    assert resp.status_code == 201
    job_id = resp.json()["id"]

    patch_resp = client.patch(f"/api/v1/jobs/{job_id}/test", json={})
    assert patch_resp.status_code == 200
    assert patch_resp.json()["id"] == job_id


def test_patch_job_nonexistent_returns_404(client, test_tenant):
    """PATCH job with job_id not in tenant returns 404."""
    fake_id = "00000000-0000-0000-0000-000000000099"
    resp = client.patch(f"/api/v1/jobs/{fake_id}/test", json={
        "estimated_duration_minutes": 120
    })
    assert resp.status_code == 404


def test_patch_job_invalid_customer_returns_404(client, test_tenant):
    """PATCH job with customer_id not in tenant returns 404."""
    resp = client.post("/api/v1/jobs/test", json={
        "customer_id": str(test_tenant.customer_id),
        "site_id": str(test_tenant.site_id),
    })
    assert resp.status_code == 201
    job_id = resp.json()["id"]

    fake_customer_id = "00000000-0000-0000-0000-000000000099"
    patch_resp = client.patch(f"/api/v1/jobs/{job_id}/test", json={
        "customer_id": fake_customer_id,
    })
    assert patch_resp.status_code == 404


def test_patch_job_site_wrong_customer_returns_400(client, test_tenant, second_tenant):
    """PATCH job with site belonging to a different customer returns 400."""
    # Create job in test_tenant
    resp = client.post("/api/v1/jobs/test", json={
        "customer_id": str(test_tenant.customer_id),
        "site_id": str(test_tenant.site_id),
    })
    assert resp.status_code == 201
    job_id = resp.json()["id"]

    # Create second customer in same tenant — get a different site
    # Use second_tenant's site which won't belong to test_tenant's customer
    # Note: If second_tenant fixtures aren't available for cross-validation,
    # create a second customer via /api/v1/customers/test and a site for it,
    # then pass that site_id with the original customer_id
    # Adjust fixture usage based on what conftest.py provides
```

> **Note to Engineer**: Check `conftest.py` for available fixtures before writing test 5. Use `second_tenant` for IDOR tests. If cross-customer site validation requires creating additional customers/sites via `/test` endpoints, do so. Scope assertions by inserted IDs — never count all rows.

### Test File 2: `backend/tests/domains/invoicing_billing/test_b18_invoice_customer_name.py`

```python
import pytest

pytestmark = [
    pytest.mark.domain_invoicing_billing,
    pytest.mark.unit,
]


def test_invoice_list_includes_customer_name(client, test_tenant, mock_cognito_jwt):
    """GET /invoices/test returns items with non-null customer_name."""
    resp = client.get("/api/v1/invoices/test")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    # At least one invoice should exist from seed data
    if data["items"]:
        item = data["items"][0]
        assert "customer_name" in item
        # customer_name should be a string, not None (seed data has customers)
        assert item["customer_name"] is not None
        assert isinstance(item["customer_name"], str)


def test_invoice_customer_name_matches_customer(client, test_tenant):
    """customer_name in list matches the actual customer display_name."""
    # Create an invoice via test endpoint
    resp = client.get("/api/v1/invoices/test")
    assert resp.status_code == 200
    data = resp.json()
    if data["items"]:
        invoice = data["items"][0]
        customer_id = invoice["customer_id"]
        customer_name = invoice["customer_name"]

        # Fetch the customer to verify name matches
        cust_resp = client.get(f"/api/v1/customers/{customer_id}/test")
        if cust_resp.status_code == 200:
            assert cust_resp.json()["display_name"] == customer_name


def test_invoice_list_customer_name_field_present_even_if_null(client, test_tenant):
    """InvoiceSummary shape includes customer_name key (may be null for orphans)."""
    resp = client.get("/api/v1/invoices/test")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    # Every item must have the customer_name key
    for item in data["items"]:
        assert "customer_name" in item
```

---

## Final Verification

### Phase 1 — Unit Tests Only (run after each task group during development)

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=short -q 2>&1 | tail -10
```

All unit tests must pass before moving to Phase 2.

### Phase 2 — Full Suite (run once, at the very end, before DoD sign-off)

```bash
cd <repo>/backend
source .venv/bin/activate

# Full suite
python -m pytest --tb=short -q 2>&1 | tail -10

# Batch-specific spot checks
python -m pytest tests/domains/field_operations/test_b18_job_patch.py -v 2>&1 | tail -20
python -m pytest tests/domains/invoicing_billing/test_b18_invoice_customer_name.py -v 2>&1 | tail -20

# Verify new endpoint appears in openapi map
grep -A 3 "PATCH.*jobs.*{job_id}" backend/openapi_schema_map.md
grep -A 3 "customer_name" backend/openapi_schema_map.md

echo "=== B18 FINAL VERIFICATION COMPLETE ==="
```

---

### Regenerate OpenAPI

After all tests pass:

```bash
cd <repo>/backend
source .venv/bin/activate
python export_openapi_json.py
```

Verify:
```bash
grep -A 5 "jobs/{job_id}" backend/openapi_schema_map.md | grep -i patch
grep "customer_name" backend/openapi_schema_map.md
```

---

## Definition of Done

Update `dev-docs/analysis/pilot-launch-plan.md` when each item is done:

- [ ] Pre-modification regression baseline captured (`X passed, Y failed`) using `pytest -m unit`
- [ ] Zero pre-existing unit failures confirmed before starting work (or confirmed with Tom)
- [ ] All MCP pre-work queries run — job columns, customer.display_name, invoice.customer_id confirmed
- [ ] All mandatory source files read before writing any code
- [ ] `JobUpdate` schema added to `api/schemas/schemas.py`
- [ ] `_update_job_impl()` added to `jobs.py` — IDOR-safe, validates customer/site cross-ownership
- [ ] `PATCH /{job_id}/test` test endpoint added (registered BEFORE authenticated endpoints)
- [ ] `PATCH /{job_id}` authenticated endpoint added with `set_audit_context_sync()` call
- [ ] `customer_name: str | None = None` added to `InvoiceSummary` in `schemas.py`
- [ ] `_list_invoices_impl()` JOIN updated to include `Customer` with IDOR protection
- [ ] Row loop updated to populate `customer_name` from `customer.display_name`
- [ ] `set_audit_context_sync()` called at start of `update_job()` authenticated endpoint
- [ ] All new API errors follow RFC 7807 Problem Details format (dict, not string)
- [ ] Test file `test_b18_job_patch.py` created in `domains/field_operations/` with `pytestmark`
- [ ] Test file `test_b18_invoice_customer_name.py` created in `domains/invoicing_billing/` with `pytestmark`
- [ ] No module-level `TestClient` in any test file
- [ ] All tests use fixtures, not hardcoded UUIDs
- [ ] `python export_openapi_json.py` run — `PATCH /api/v1/jobs/{job_id}` and `customer_name` appear in `openapi_schema_map.md`
- [ ] **Phase 1**: All unit tests pass (`pytest -m unit`) — zero failures
- [ ] **Phase 2**: Full test suite passes (`pytest`) — zero failures including integration tests
- [ ] Final test count (before → after) documented
- [ ] Completion Summary added to `pilot-launch-plan.md`

---

## Completion Summary

After all Definition of Done items are complete:

1. Add a **Completion Summary** subsection to `dev-docs/analysis/pilot-launch-plan.md` using this format:

```markdown
### B18 — Job PATCH Endpoint + Invoice Customer Name: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot Python Engineer
**Baseline**: X passed, Y failed
**Final**: X+N passed, Y failed (+N new tests)

#### What Was Accomplished

- Added `JobUpdate` schema (`customer_id?`, `site_id?`, `scheduled_start_at?`, `scheduled_end_at?`, `estimated_duration_minutes?`)
- Added `_update_job_impl()` with IDOR-safe tenant/customer/site validation
- Added `PATCH /api/v1/jobs/{job_id}` authenticated endpoint with audit context
- Added `PATCH /api/v1/jobs/{job_id}/test` test endpoint
- Added `customer_name: str | None = None` to `InvoiceSummary`
- Updated `_list_invoices_impl()` to JOIN `Customer` and populate `customer_name`
- [N] new tests across field_operations and invoicing_billing domains

#### Files Changed / Created

| File | Action |
|---|---|
| `backend/api/schemas/schemas.py` | Updated — `JobUpdate` added; `InvoiceSummary.customer_name` added |
| `backend/api/routes/jobs.py` | Updated — `_update_job_impl`, `PATCH /{job_id}/test`, `PATCH /{job_id}` |
| `backend/api/routes/invoices.py` | Updated — `_list_invoices_impl` Customer JOIN + row loop |
| `backend/openapi.json` | Regenerated |
| `backend/openapi_schema_map.md` | Regenerated |
| `backend/tests/domains/field_operations/test_b18_job_patch.py` | Created |
| `backend/tests/domains/invoicing_billing/test_b18_invoice_customer_name.py` | Created |

#### Tests Added

| Test File | Domain | Tests | All Pass |
|---|---|---|---|
| `test_b18_job_patch.py` | `domain_field_operations` | N | ✅ |
| `test_b18_invoice_customer_name.py` | `domain_invoicing_billing` | N | ✅ |
```

2. Notify React Engineer that B18 is complete — they must run `pnpm sync-api-types` before starting FE-B24 and FE-B25.

---

## After This Task — Next Step

FE-B24 (Job Create Modal, Invoice Create Rework, Customer Name Display, Quote Edit Modal, Customer Delete) can start once:
- `python export_openapi_json.py` has run
- `PATCH /api/v1/jobs/{job_id}` and `customer_name` in `InvoiceSummary` are confirmed in `openapi_schema_map.md`
- React Engineer has run `pnpm sync-api-types`

FE-B25 (Job Edit UI) depends on the PATCH endpoint from this batch.
