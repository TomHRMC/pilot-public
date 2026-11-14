# Implementation Prompt: B20 — Invoice Builder Backend

**Mode**: Pilot Python Engineer  
**Batch**: B20  
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §Phase 1 — B20 row  
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-b20-design.md`  
**Estimated session**: 3–4 hours  
**Platform**: Backend only (`backend/`)  
**Frontend companion**: FE-B29 (depends on this batch — do not start FE-B29 until `python export_openapi_json.py` is complete)

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`dev-docs/architecture-design/pilot-python-engineer-methods.md`** — §13 (Alembic), §8 (Router Design), §5 (Model Design), §16 (Standard Task Workflow)
- **`backend/tests/README-adding-tests.md`** — full document; governs all test file structure, domain markers, and fixture rules
- **`dev-docs/architecture-design/batch-designs/batch-b20-design.md`** — every section (A–G)

**Critical rules for this batch:**

- **Rule 1**: Never guess column names. Use `postgres-local` MCP to verify before any migration. The launch plan mentioned `tenant_settings` table — **this table does NOT exist**. Tenant settings live in `platform_setting` with nullable `tenant_id`. See Design Doc §G for the full resolution.
- **Rule 2**: After any model file change → regenerate `backend/db_models_map.md` via `python generate_db_model_map.py`.
- **Rule 3**: After all endpoints are added → run `python export_openapi_json.py` and hand off to FE-B29.
- **Rule 4**: All Alembic migrations must be **blank** (`alembic revision -m "name"`) — never `--autogenerate`.
- **Rule 5**: Never use module-level `TestClient`. Always use the `client` fixture.
- **Rule 6**: `db.get()` is banned on tenant-scoped models. Use `select()` + `WHERE tenant_id = current_user.tenant_id`.
- **Rule 8**: All API errors must follow RFC 7807 Problem Details format.
- **Rule 9**: Any mutation endpoints added must call `set_audit_context_sync()` before the first DB write. The new `GET /api/v1/jobs/{id}/billable-items` is read-only — no audit context needed.

---

## Pre-Work: Establish Regression Baseline

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=no -q 2>&1 | tail -5
```

Record the exact count. Zero failures required before starting.

---

## Pre-Work: Run MCP Verification Queries

Run **all** of these via `postgres-local` MCP before writing any migration code. If any returns unexpected results → **STOP and ask Tom**.

```sql
-- 1. Confirm current Alembic head (expect 44035334e651)
SELECT version_num FROM public.alembic_version;

-- 2. Confirm invoice fields do NOT exist yet
SELECT column_name FROM information_schema.columns 
WHERE table_schema = 'public' AND table_name = 'invoice'
AND column_name IN ('payment_terms', 'billing_mode', 'progress_pct', 'internal_memo');
-- Expected: 0 rows

-- 3. Confirm card_required does NOT exist on customer or quote
SELECT table_name, column_name FROM information_schema.columns 
WHERE table_schema = 'public' AND table_name IN ('customer', 'quote')
AND column_name = 'card_required';
-- Expected: 0 rows

-- 4. Confirm platform_setting_catalog does NOT have square key yet
SELECT key FROM platform_setting_catalog WHERE key = 'square_integration_enabled';
-- Expected: 0 rows

-- 5. Confirm existing invoice columns (use actual names in migration, not assumed names)
SELECT column_name, data_type, is_nullable FROM information_schema.columns 
WHERE table_schema = 'public' AND table_name = 'invoice'
ORDER BY ordinal_position;

-- 6. Confirm job_time_entry columns (for billable-items endpoint)
SELECT column_name, data_type FROM information_schema.columns 
WHERE table_schema = 'public' AND table_name = 'job_time_entry'
ORDER BY ordinal_position;

-- 7. Confirm job_expense columns (for billable-items endpoint)
SELECT column_name, data_type FROM information_schema.columns 
WHERE table_schema = 'public' AND table_name = 'job_expense'
ORDER BY ordinal_position;

-- 8. Confirm platform_setting catalog structure
SELECT key, value_type, tenant_editable, category FROM platform_setting_catalog 
WHERE category = 'billing' OR category = 'quotes'
ORDER BY category, key;
```

> **MCP Usage Rule**: The `postgres-local` MCP is for **read-only verification only**. Never use it to INSERT, UPDATE, or DELETE.

---

## Pre-Work: Read These Source Files

Use `read_file` on each of these before writing any code:

```
backend/app/models/billing.py
← understand Invoice model, field patterns, StandardAuditMixin usage

backend/app/models/crm.py
← understand Customer model before adding card_required

backend/app/models/quoting.py
← understand Quote model before adding card_required

backend/api/schemas/schemas.py
← understand InvoiceCreate, InvoiceResponse, CustomerCreate, CustomerResponse shapes

backend/api/schemas/quotes.py
← understand QuoteCreate, QuoteResponse before adding card_required

backend/api/routes/invoices.py (lines 1-150)
← understand _create_invoice_impl() pattern

backend/api/routes/jobs.py (lines 1-100)
← understand existing job endpoint patterns before adding billable-items

backend/migrations/versions/44035334e651*.py
← most recent migration — use as pattern reference

backend/tests/conftest.py
← understand available fixtures

backend/db_models_map.md
← confirm model names and table mappings
```

Also run:
```bash
# Find the most recent migration file
ls -t backend/migrations/versions/ | head -3

# Find existing billable-related schemas
grep -n "Billable\|billable" backend/api/schemas/schemas.py | head -10

# Find platform_setting model
grep -rn "PlatformSetting\|platform_setting" backend/app/models/ --include="*.py" | head -10
```

---

## TASK 1 — Migration 1: Add Invoice Builder Fields to `invoice` Table

**Create blank migration:**
```bash
cd <repo>/backend
source .venv/bin/activate
alembic revision -m "b20_add_invoice_builder_fields"
```

**Implement the migration:**

```python
def upgrade() -> None:
    # Part 1: Add columns as nullable
    op.add_column('invoice', sa.Column('payment_terms', sa.String(30), nullable=True))
    op.add_column('invoice', sa.Column('billing_mode', sa.String(20), nullable=True))
    op.add_column('invoice', sa.Column('progress_pct', sa.Numeric(5, 2), nullable=True))
    op.add_column('invoice', sa.Column('internal_memo', sa.Text(), nullable=True))

    # Part 2: Backfill billing_mode (will become NOT NULL)
    op.execute("UPDATE invoice SET billing_mode = 'line_item' WHERE billing_mode IS NULL")

    # Part 3: Lock billing_mode as NOT NULL with server default
    op.alter_column('invoice', 'billing_mode',
        nullable=False,
        server_default='line_item')

    # payment_terms, progress_pct, internal_memo remain nullable — no backfill needed


def downgrade() -> None:
    op.drop_column('invoice', 'internal_memo')
    op.drop_column('invoice', 'progress_pct')
    op.drop_column('invoice', 'billing_mode')
    op.drop_column('invoice', 'payment_terms')
```

**Test the migration cycle:**
```bash
alembic upgrade head
alembic downgrade -1
alembic upgrade head
alembic current  # must show the new revision
```

---

## TASK 2 — Migration 2: Add `card_required` to `customer` + `quote`

**Create blank migration:**
```bash
alembic revision -m "b20_add_card_required_to_customer_quote"
```

**Implement:**

```python
def upgrade() -> None:
    # customer.card_required — NOT NULL with default false (3-part pattern)
    # Part 1: Add nullable
    op.add_column('customer', sa.Column('card_required', sa.Boolean(), nullable=True))
    # Part 2: Backfill
    op.execute("UPDATE customer SET card_required = false WHERE card_required IS NULL")
    # Part 3: Lock NOT NULL
    op.alter_column('customer', 'card_required',
        nullable=False,
        server_default='false')

    # quote.card_required — nullable (None = inherit from customer)
    op.add_column('quote', sa.Column('card_required', sa.Boolean(), nullable=True))


def downgrade() -> None:
    op.drop_column('quote', 'card_required')
    op.drop_column('customer', 'card_required')
```

**Test the migration cycle:**
```bash
alembic upgrade head
alembic downgrade -1
alembic upgrade head
alembic current
```

---

## TASK 3 — Migration 3: `square_integration_enabled` Platform Setting

**Create blank data migration:**
```bash
alembic revision -m "b20_add_square_integration_platform_setting"
```

**Implement:**

```python
def upgrade() -> None:
    import json
    op.execute("SET LOCAL session_replication_role = 'replica';")

    # Insert catalog entry
    op.execute("""
        INSERT INTO platform_setting_catalog (
            key, label, description, value_type, tenant_editable, 
            allows_user_override, category, is_active, sort_order,
            created_at, updated_at
        )
        VALUES (
            'square_integration_enabled',
            'Square payment integration enabled',
            'When enabled, tenants can require card-on-file via Square before work begins.',
            'boolean',
            true,
            false,
            'billing',
            true,
            100,
            now(),
            now()
        )
        ON CONFLICT (key) DO NOTHING;
    """)

    # Insert system default (tenant_id = NULL)
    op.execute("""
        INSERT INTO platform_setting (key, value, tenant_id, created_at, updated_at)
        VALUES (
            'square_integration_enabled',
            'false'::jsonb,
            NULL,
            now(),
            now()
        )
        ON CONFLICT DO NOTHING;
    """)


def downgrade() -> None:
    op.execute("DELETE FROM platform_setting WHERE key = 'square_integration_enabled';")
    op.execute("DELETE FROM platform_setting_catalog WHERE key = 'square_integration_enabled';")
```

> **Read `platform_setting_catalog`** via `read_file backend/app/models/core.py` (or wherever `PlatformSettingCatalog` is defined) to confirm the PRIMARY KEY constraint name before writing `ON CONFLICT (key)`. If the PK is not `key`, adjust accordingly.

**Test the migration cycle:**
```bash
alembic upgrade head
alembic downgrade -1
alembic upgrade head
alembic current
```

**Intermediate unit test run:**
```bash
python -m pytest -m unit --tb=short -q 2>&1 | tail -5
```

---

## TASK 4 — Update SQLModel Classes

**Read the model files before modifying:**
```
read_file backend/app/models/billing.py
read_file backend/app/models/crm.py
read_file backend/app/models/quoting.py
```

### `Invoice` model (`app/models/billing.py`)

Add after the existing `reminder_count` field (read file to confirm exact position):

```python
# B20: Invoice builder fields
payment_terms: str | None = Field(default=None, max_length=30)
billing_mode: str = Field(default="line_item", max_length=20)
progress_pct: Decimal | None = Field(default=None)
internal_memo: str | None = Field(default=None)
```

Add `from decimal import Decimal` to imports if not already present.

### `Customer` model (`app/models/crm.py`)

Add after existing SMS consent fields:

```python
# B20: Square card-on-file requirement
card_required: bool = Field(default=False)
```

### `Quote` model (`app/models/quoting.py`)

Add after existing fields:

```python
# B20: Square card-on-file override (None = inherit from customer.card_required)
card_required: bool | None = Field(default=None)
```

**After all model changes, regenerate:**
```bash
python generate_db_model_map.py
grep "card_required\|billing_mode\|payment_terms\|progress_pct\|internal_memo" backend/db_models_map.md
```

---

## TASK 5 — Update Pydantic Schemas

**Read the schema files before modifying:**
```
read_file backend/api/schemas/schemas.py --offset 1 --limit 100
read_file backend/api/schemas/quotes.py
```

### Add to `schemas.py`:

**`InvoiceCreate`** — add these optional fields:
```python
payment_terms: str | None = None  # 'due_on_receipt'|'net_15'|'net_30'|'custom_date'
billing_mode: str = "line_item"   # 'line_item'|'progress'
progress_pct: Decimal | None = None
internal_memo: str | None = None

@model_validator(mode='after')
def validate_billing_mode(self) -> 'InvoiceCreate':
    if self.billing_mode == 'progress':
        if self.progress_pct is None:
            raise ValueError("progress_pct is required when billing_mode is 'progress'")
        if not (0 <= self.progress_pct <= 100):
            raise ValueError("progress_pct must be between 0 and 100")
    return self
```

Add `from pydantic import model_validator` if not already imported. Add `from decimal import Decimal` if needed.

**`InvoiceResponse`** / **`InvoiceSummary`** — add the same fields as read-only responses:
```python
payment_terms: str | None = None
billing_mode: str = "line_item"
progress_pct: Decimal | None = None
internal_memo: str | None = None
```

**`CustomerCreate`** — add:
```python
card_required: bool = False
```

**`CustomerResponse`** — add:
```python
card_required: bool = False
```

**`BillableTimeEntry`** (new schema — add near other Invoice schemas):
```python
class BillableTimeEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    tech_name: str | None = None
    started_at: AwareDatetime
    ended_at: AwareDatetime | None = None
    hours: Decimal | None = None
    hourly_rate_cents: int
    total_cost_cents: int
    notes: str | None = None
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
    job_number: str | None = None
    customer_name: str | None = None
    time_entries: list[BillableTimeEntry]
    expenses: list[BillableExpense]
```

### Add to `quotes.py`:

**`QuoteCreate`** — add:
```python
card_required: bool | None = None  # None = inherit from customer.card_required
```

**`QuoteResponse`** — add:
```python
card_required: bool | None = None
```

---

## TASK 6 — Update `_create_invoice_impl()` + `_create_customer_impl()` + `_create_quote_impl()`

**Read route files before modifying:**
```
read_file backend/api/routes/invoices.py --offset 80 --limit 120
read_file backend/api/routes/customers.py --offset 1 --limit 80
read_file backend/api/routes/quotes.py --offset 1 --limit 80
```

For each `_create_*_impl()` function, ensure the new fields from `*Create` schemas are mapped into the SQLModel constructor call. Example pattern (adjust to actual code found):

```python
# In _create_invoice_impl():
invoice = Invoice(
    # ... existing fields ...
    payment_terms=invoice_in.payment_terms,
    billing_mode=invoice_in.billing_mode,
    progress_pct=invoice_in.progress_pct,
    internal_memo=invoice_in.internal_memo,
)

# In _create_customer_impl() or equivalent:
customer = Customer(
    # ... existing fields ...
    card_required=customer_in.card_required,
)

# In _create_quote_impl():
quote = Quote(
    # ... existing fields ...
    card_required=quote_in.card_required,
)
```

> **Important**: Read each impl function before modifying. The actual parameter mapping may differ from the example above.

---

## TASK 7 — Add `GET /api/v1/jobs/{job_id}/billable-items` Endpoint

**Read the file first:**
```
read_file backend/api/routes/jobs.py --offset 1 --limit 100
```

Add the following to `backend/api/routes/jobs.py` after existing job endpoints:

```python
from api.schemas.schemas import BillableItemsResponse, BillableTimeEntry, BillableExpense

@router.get("/{job_id}/billable-items", response_model=BillableItemsResponse)
def get_job_billable_items(
    job_id: UUID,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(
        require_permission("invoices.create")
    ),
) -> BillableItemsResponse:
    """
    Return all time entries + expenses for a job, used by the invoice builder
    to pre-populate the line-item checklist.
    B20: MVP — is_already_invoiced always False for time entries.
    """
    return _get_job_billable_items_impl(job_id=job_id, db=db, user=current_user)


@router.get("/{job_id}/billable-items/test", response_model=BillableItemsResponse)
def get_job_billable_items_test(
    job_id: UUID,
    db: Session = Depends(get_db),
    ctx: TestUserContext = Depends(get_test_context),
) -> BillableItemsResponse:
    """Test-only — bypasses JWT auth."""
    return _get_job_billable_items_impl(job_id=job_id, db=db, user=ctx)
```

**Implement `_get_job_billable_items_impl()`:**

```python
def _get_job_billable_items_impl(
    job_id: UUID,
    db: Session,
    user: AuthenticatedUser | TestUserContext,
) -> BillableItemsResponse:
    # IDOR-safe job lookup
    job = db.exec(
        select(Job)
        .where(Job.id == job_id)
        .where(Job.tenant_id == user.tenant_id)
        .where(Job.is_active == True)
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

    # Fetch customer name for the response
    customer = db.exec(
        select(Customer)
        .where(Customer.id == job.customer_id)
        .where(Customer.tenant_id == user.tenant_id)
    ).first()

    # Fetch time entries
    time_entries_raw = db.exec(
        select(JobTimeEntry, User)
        .join(User, JobTimeEntry.user_id == User.id)
        .where(JobTimeEntry.job_id == job_id)
        .where(JobTimeEntry.tenant_id == user.tenant_id)
    ).all()

    time_entries = [
        BillableTimeEntry(
            id=te.id,
            user_id=te.user_id,
            tech_name=u.display_name,
            started_at=te.started_at,
            ended_at=te.ended_at,
            hours=te.hours,
            hourly_rate_cents=te.hourly_rate_cents,
            total_cost_cents=te.total_cost_cents,
            notes=te.notes,
            is_already_invoiced=False,  # MVP: always False
        )
        for te, u in time_entries_raw
    ]

    # Fetch expenses
    expenses_raw = db.exec(
        select(JobExpense)
        .where(JobExpense.job_id == job_id)
        .where(JobExpense.tenant_id == user.tenant_id)
        .where(JobExpense.is_active == True)
    ).all()

    expenses = [
        BillableExpense(
            id=exp.id,
            description=exp.description,
            cost_cents=exp.cost_cents,
            billable_cents=exp.billable_cents,
            is_billable=exp.is_billable,
            is_already_invoiced=exp.invoice_line_id is not None,
            incurred_at=exp.incurred_at,
        )
        for exp in expenses_raw
    ]

    return BillableItemsResponse(
        job_id=job.id,
        job_number=job.job_number,
        customer_name=customer.display_name if customer else None,
        time_entries=time_entries,
        expenses=expenses,
    )
```

**Important adjustments**:
- Read `jobs.py` to confirm the exact `User` model import path — it may be `from app.models.auth import User` or similar
- Verify `job_time_entry.tenant_id` exists (MCP confirmed it does)
- Verify `job_expense.tenant_id` exists (MCP confirmed it does)
- The JOIN on `User` may need adjustment based on how `User` is imported in `jobs.py`

**Check imports needed:**
```bash
grep -n "^from\|^import" backend/api/routes/jobs.py | head -20
grep -n "class User\|from.*User" backend/app/models/ -r --include="*.py" | head -5
```

**Intermediate unit test run:**
```bash
python -m pytest -m unit --tb=short -q 2>&1 | tail -5
```

---

## Test Requirements

### Test Files to Create

**Test 1: `backend/tests/domains/invoicing_billing/test_b20_invoice_builder_fields.py`**

```python
import pytest
from decimal import Decimal

pytestmark = [
    pytest.mark.domain_invoicing_billing,
    pytest.mark.unit,
]

class TestInvoiceBuilderFields:
    """Test new B20 fields: payment_terms, billing_mode, progress_pct, internal_memo"""

    def test_create_invoice_with_payment_terms(self, client, test_tenant):
        resp = client.post("/api/v1/invoices/test", json={
            # minimal valid payload — read InvoiceCreate to see required fields
            "payment_terms": "net_30",
            "billing_mode": "line_item",
        })
        assert resp.status_code in (200, 201)
        data = resp.json()
        assert data["payment_terms"] == "net_30"
        assert data["billing_mode"] == "line_item"

    def test_create_invoice_progress_mode(self, client, test_tenant):
        resp = client.post("/api/v1/invoices/test", json={
            "billing_mode": "progress",
            "progress_pct": "50.00",
        })
        assert resp.status_code in (200, 201)
        data = resp.json()
        assert data["billing_mode"] == "progress"
        assert Decimal(data["progress_pct"]) == Decimal("50.00")

    def test_progress_mode_requires_pct(self, client, test_tenant):
        """billing_mode=progress without progress_pct must be rejected."""
        resp = client.post("/api/v1/invoices/test", json={
            "billing_mode": "progress",
            "progress_pct": None,
        })
        assert resp.status_code == 422

    def test_invoice_internal_memo(self, client, test_tenant):
        resp = client.post("/api/v1/invoices/test", json={
            "billing_mode": "line_item",
            "internal_memo": "This is an internal note.",
        })
        assert resp.status_code in (200, 201)
        assert resp.json()["internal_memo"] == "This is an internal note."

    def test_invoice_defaults(self, client, test_tenant):
        """billing_mode defaults to 'line_item' if not specified."""
        resp = client.post("/api/v1/invoices/test", json={})
        # May 422 if required fields missing — check InvoiceCreate schema first
        # Just verify billing_mode default if creation succeeds
        if resp.status_code in (200, 201):
            assert resp.json()["billing_mode"] == "line_item"
```

> **Adjust payloads**: Read `InvoiceCreate` and the `/test` endpoint handler to confirm the minimal required fields. Some fields like `customer_id`, `site_id` may be required. Use `test_tenant` and `test_customer` fixtures where needed.

**Test 2: `backend/tests/domains/crm/test_b20_card_required.py`**

```python
import pytest

pytestmark = [
    pytest.mark.domain_crm,
    pytest.mark.unit,
]

class TestCardRequired:
    """Test card_required on Customer and Quote"""

    def test_customer_card_required_default_false(self, client, test_tenant):
        resp = client.post("/api/v1/customers/test", json={
            "display_name": "Card Test Customer",
            "type": "person",
        })
        assert resp.status_code == 201
        assert resp.json()["card_required"] == False

    def test_customer_card_required_true(self, client, test_tenant):
        resp = client.post("/api/v1/customers/test", json={
            "display_name": "Card Required Customer",
            "type": "person",
            "card_required": True,
        })
        assert resp.status_code == 201
        assert resp.json()["card_required"] == True
```

**Test 3: `backend/tests/domains/field_operations/test_b20_billable_items.py`**

```python
import pytest

pytestmark = [
    pytest.mark.domain_field_operations,
    pytest.mark.unit,
]

class TestBillableItems:
    """Test GET /api/v1/jobs/{job_id}/billable-items"""

    def test_billable_items_returns_200(self, client, test_tenant, test_job):
        """Basic smoke test — returns 200 for a job in the tenant."""
        resp = client.get(f"/api/v1/jobs/{test_job.id}/billable-items/test")
        assert resp.status_code == 200
        data = resp.json()
        assert "time_entries" in data
        assert "expenses" in data
        assert data["job_id"] == str(test_job.id)

    def test_billable_items_404_wrong_tenant(self, client, second_tenant):
        """Job from another tenant returns 404 (IDOR protection)."""
        # Create a job via test endpoint, then fetch from second_tenant perspective
        # This test validates tenant scoping — adjust based on available fixtures
        resp = client.get(f"/api/v1/jobs/00000000-0000-0000-0000-000000000001/billable-items/test")
        assert resp.status_code == 404

    def test_billable_items_expense_is_already_invoiced(self, client, test_tenant, test_job, db_session):
        """Expense with invoice_line_id set shows is_already_invoiced=True."""
        # This test may require inserting an expense with invoice_line_id set
        # Use db_session fixture to insert directly, then call endpoint
        # Defer to engineer if fixture setup is complex
        pass  # Mark as skip if setup is too complex for this batch
```

> **Note**: `test_job` fixture exists (confirmed in `conftest.py`). Read `conftest.py` to understand what `test_job` contains before using it.

### Test Domain Assignments

| Test File | Domain Marker | Domain Folder |
|---|---|---|
| `test_b20_invoice_builder_fields.py` | `domain_invoicing_billing` | `invoicing_billing/` |
| `test_b20_card_required.py` | `domain_crm` | `crm/` |
| `test_b20_billable_items.py` | `domain_field_operations` | `field_operations/` |

---

## Final Verification

### Phase 1 — Unit Tests Only

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=short -q 2>&1 | tail -10
```

All unit tests must pass before proceeding to Phase 2.

### Phase 2 — Full Suite + OpenAPI Regeneration

```bash
cd <repo>/backend
source .venv/bin/activate

# Full test suite
python -m pytest --tb=short -q 2>&1 | tail -10

# Spot checks
python -m pytest tests/domains/field_operations/ -v 2>&1 | tail -15
python -m pytest tests/domains/invoicing_billing/ -v 2>&1 | tail -15

# Regenerate OpenAPI
python export_openapi_json.py

# Verify new endpoint appears
grep -A 5 "billable-items" backend/openapi_schema_map.md

# Verify new invoice fields appear
grep -A 2 "billing_mode\|payment_terms\|progress_pct\|internal_memo" backend/openapi_schema_map.md | head -20

# Regenerate DB model map
python generate_db_model_map.py
grep "card_required\|billing_mode" backend/db_models_map.md

# Update JSON schema — schema_manager.py is a CRUD script, NOT a sync script
python schema_manager.py --help   # read available CRUD commands (set, delete, inspect, etc.)
# Then use the appropriate command for your changes

echo "=== B20 FINAL VERIFICATION COMPLETE ==="
```

---

## Definition of Done — B20

Update `dev-docs/analysis/pilot-launch-plan.md` §Phase 1 B20 row when each item is done:

- [ ] Regression baseline captured — zero pre-existing failures confirmed
- [ ] All 8 MCP pre-work queries run and verified
- [ ] All mandatory source files read before writing any code
- [ ] **Migration 1**: `invoice` fields — `payment_terms`, `billing_mode` (NOT NULL, default 'line_item'), `progress_pct`, `internal_memo` — migration cycle passes (upgrade → downgrade → upgrade)
- [ ] **Migration 2**: `customer.card_required` (NOT NULL, default false) + `quote.card_required` (nullable) — migration cycle passes
- [ ] **Migration 3**: `square_integration_enabled` catalog + system default — migration cycle passes
- [ ] `Invoice` SQLModel updated with 4 new fields
- [ ] `Customer` SQLModel updated with `card_required`
- [ ] `Quote` SQLModel updated with `card_required`
- [ ] `InvoiceCreate` schema updated with 4 new fields + `model_validator` for progress mode
- [ ] `InvoiceResponse` / `InvoiceSummary` updated with 4 new fields
- [ ] `CustomerCreate` + `CustomerResponse` updated with `card_required`
- [ ] `QuoteCreate` + `QuoteResponse` updated with `card_required`
- [ ] `BillableTimeEntry`, `BillableExpense`, `BillableItemsResponse` schemas created
- [ ] `_create_invoice_impl()` maps all 4 new fields
- [ ] `_create_customer_impl()` maps `card_required`
- [ ] `_create_quote_impl()` maps `card_required`
- [ ] `GET /api/v1/jobs/{job_id}/billable-items` endpoint added with IDOR-safe tenant scope
- [ ] `GET /api/v1/jobs/{job_id}/billable-items/test` counterpart added
- [ ] 3 test files created in correct domain folders
- [ ] All new test files use `pytestmark` with domain marker + `pytest.mark.unit`
- [ ] No module-level `TestClient` in any test file
- [ ] All RFC 7807 error shapes in new endpoint
- [ ] `python generate_db_model_map.py` run — new fields visible in `db_models_map.md`
- [ ] `python export_openapi_json.py` run — `openapi.json` + `openapi_schema_map.md` updated
- [ ] `python schema_manager.py --help` run first; then appropriate CRUD command used to update `pilot-db-schema-v2.6h.json`
- [ ] **Phase 1**: All unit tests pass (`pytest -m unit`) — zero failures
- [ ] **Phase 2**: Full test suite passes — zero failures
- [ ] Final test count (before → after) documented

---

## Completion Summary

After all Definition of Done items are complete:

1. Add a **Completion Summary** subsection to `dev-docs/analysis/pilot-launch-plan.md` §Phase 1 B20 section.
2. Notify the Pilot Architect that B20 is complete — **FE-B29 is now unblocked**.

```markdown
### B20 — Invoice Builder Backend: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot Python Engineer
**Baseline**: X passed, Y failed
**Final**: X+N passed, Y failed (+N new tests)

#### What Was Accomplished

- Added `payment_terms`, `billing_mode` (NOT NULL default 'line_item'), `progress_pct`, `internal_memo` to `invoice` table + schemas
- Added `card_required` to `customer` (NOT NULL, default false) and `quote` (nullable) + schemas
- Added `square_integration_enabled` to `platform_setting_catalog` (tenant_editable=true, category='billing') + system default row
- Added `GET /api/v1/jobs/{id}/billable-items` endpoint (authenticated + test variants) for invoice builder pre-fill
- Added `BillableTimeEntry`, `BillableExpense`, `BillableItemsResponse` schemas

#### Files Changed / Created

| File | Action |
|---|---|
| `backend/migrations/versions/..._b20_add_invoice_builder_fields.py` | Created |
| `backend/migrations/versions/..._b20_add_card_required_to_customer_quote.py` | Created |
| `backend/migrations/versions/..._b20_add_square_integration_platform_setting.py` | Created |
| `backend/app/models/billing.py` | Updated — 4 new invoice fields |
| `backend/app/models/crm.py` | Updated — card_required |
| `backend/app/models/quoting.py` | Updated — card_required |
| `backend/api/schemas/schemas.py` | Updated — InvoiceCreate/Response, Customer*, Billable* schemas |
| `backend/api/schemas/quotes.py` | Updated — QuoteCreate/Response card_required |
| `backend/api/routes/invoices.py` | Updated — _create_invoice_impl maps new fields |
| `backend/api/routes/customers.py` | Updated — card_required in create |
| `backend/api/routes/quotes.py` | Updated — card_required in create |
| `backend/api/routes/jobs.py` | Updated — billable-items endpoints |
| `backend/tests/domains/invoicing_billing/test_b20_invoice_builder_fields.py` | Created |
| `backend/tests/domains/crm/test_b20_card_required.py` | Created |
| `backend/tests/domains/field_operations/test_b20_billable_items.py` | Created |
| `backend/openapi.json` | Regenerated |
| `backend/openapi_schema_map.md` | Regenerated |
| `backend/db_models_map.md` | Regenerated |
| `dev-docs/db-design/pilot-db-schema-v2.6h.json` | Updated via schema_manager.py |

#### Tests Added

| Test File | Domain | Tests | All Pass |
|---|---|---|---|
| `test_b20_invoice_builder_fields.py` | `domain_invoicing_billing` | N | ✅ |
| `test_b20_card_required.py` | `domain_crm` | N | ✅ |
| `test_b20_billable_items.py` | `domain_field_operations` | N | ✅ |
```

---

## After This Batch — Next Step

Run `python export_openapi_json.py` and commit the updated `openapi.json` before notifying Tom that FE-B29 can start. The React Engineer must run `pnpm sync-api-types` as their first Pre-Work step.
