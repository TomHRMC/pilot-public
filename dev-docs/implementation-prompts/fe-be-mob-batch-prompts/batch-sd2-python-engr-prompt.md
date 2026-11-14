# Batch SD-2 — Seed Data & Lookup Table Cleanup
**Mode**: `pilot-python-engineer`  
**Batch**: SD-2  
**Plan link**: `dev-docs/analysis/pilot-launch-plan.md`  
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-sd2-design.md`  
**Estimate**: 3–4 hours  
**Platform**: Backend only  
**Frontend companion**: None (lookup table data changes only)

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`dev-docs/architecture-design/pilot-python-engineer-methods.md`** — §13 (Alembic), §5 (Model Design), §16 (Standard Task Workflow)
- **`backend/tests/README-adding-tests.md`** — full document; this governs all test file structure, domain markers, and fixture rules

**Critical rules for this batch:**

- **Rule 1**: All Alembic migrations must be written as **blank** migrations — never `--autogenerate`. Data changes use raw `op.execute()` with `SET LOCAL session_replication_role = 'replica';` at the start of `upgrade()`.
- **Rule 2**: Always use `ON CONFLICT DO NOTHING` for all seed data INSERTs — migrations must be idempotent.
- **Rule 3**: Every new `notification_type`, `payment_status`, `invoice_status`, `quote_status`, `qco_line_type` row must use `tenant_id IS NULL` (global platform row) and include explicit `created_at = NOW(), updated_at = NOW()`.
- **Rule 4**: After removing fields from the `Payment` SQLModel — run `python generate_db_model_map.py` immediately before continuing.
- **Rule 5**: If ANY test fails during your work — even one that appears pre-existing — **stop and ask Tom**. No "not my fault" exception.
- **Rule 6**: The `postgres-local` MCP is **read-only verification only**. Never use it to INSERT, UPDATE, or DELETE.

---

## Pre-Work: Establish Regression Baseline

Before touching any file, capture the current **unit-only** test baseline:

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=no -q 2>&1 | tail -5
```

Record the exact count: **`X passed, Y failed`**.

> If any tests are already failing: confirm with Tom before proceeding. Do NOT start implementation while tests are in an unexplained failed state.

---

## Pre-Work: Run MCP Verification Queries

Run **all** of these via `postgres-local` MCP before writing any migration. If any query returns unexpected results → **STOP and ask Tom**.

```sql
-- 1. Confirm refund columns exist in payment (will be dropped in Step 5)
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'payment'
  AND column_name IN ('refunded_amount_cents', 'refunded_at')
ORDER BY ordinal_position;
-- Expected: 2 rows

-- 2. Confirm no live refund data before dropping columns
SELECT COUNT(*) FROM public.payment WHERE refunded_amount_cents > 0;
-- Expected: 0 (no production refund data yet)

-- 3. Confirm data_exports is in product_feature but NOT in product_plan_product_feature_version
SELECT code FROM public.product_feature WHERE code = 'data_exports';
-- Expected: 1 row
SELECT COUNT(*) FROM public.product_plan_product_feature_version WHERE product_feature_code = 'data_exports';
-- Expected: 0 rows

-- 4. Confirm notification_type current state (expect 3 rows)
SELECT code, audience, is_active FROM public.notification_type WHERE tenant_id IS NULL ORDER BY code;

-- 5. Confirm schema of tables being modified
SELECT column_name, data_type, is_nullable FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'qco_line_type' ORDER BY ordinal_position;

SELECT column_name, data_type, is_nullable FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'notification_type' ORDER BY ordinal_position;

SELECT column_name, data_type, is_nullable FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'payment' ORDER BY ordinal_position;
```

---

## Pre-Work: Read These Source Files

Use `read_file` on each before writing any code:

```
backend/app/models/billing.py                        ← Payment model — fields to remove
backend/services/stripe_subscriptions.py             ← _handle_refund_event() — full rewrite
backend/services/stripe_payment_intents.py           ← invoice status transition logic — add partial
backend/services/gps_variance_service.py             ← get-or-create fallback to remove
backend/tasks/auto_expire_qb_conflicts.py            ← get-or-create fallback to remove
backend/services/quickbooks_sync.py                  ← get-or-create fallback to remove
backend/tasks/check_system_template_updates.py       ← get-or-create fallback to remove
backend/migrations/scripts/seed_core.py              ← all 6 seed_core changes needed at end
backend/tests/batch_b7b/test_a41_photo_upload_pipeline.py  ← expense category code fix
backend/db_models_map.md                             ← confirm current Payment model shape
```

---

## Implementation Tasks

Work through these steps in order. Run `pytest -m unit --tb=no -q | tail -5` after each step that changes code.

---

### Step 1 — Migration: Deactivate non-USD currencies

```bash
alembic revision -m "sd2_deactivate_non_usd_currencies"
```

`upgrade()`:
```python
def upgrade() -> None:
    op.execute("SET LOCAL session_replication_role = 'replica';")
    op.execute("""
        UPDATE public.currency
        SET is_active = false, updated_at = NOW()
        WHERE code IN ('CAD', 'EUR', 'GBP')
    """)

def downgrade() -> None:
    op.execute("""
        UPDATE public.currency
        SET is_active = true, updated_at = NOW()
        WHERE code IN ('CAD', 'EUR', 'GBP')
    """)
```

Test: `alembic upgrade head && alembic downgrade -1 && alembic upgrade head`

---

### Step 2 — Migration: Add `quote_status` `void`

```bash
alembic revision -m "sd2_add_quote_status_void"
```

`upgrade()`:
```python
def upgrade() -> None:
    op.execute("SET LOCAL session_replication_role = 'replica';")
    op.execute("""
        INSERT INTO public.quote_status
        (code, name, is_default, is_terminal, is_active, tenant_id, created_at, updated_at)
        VALUES ('void', 'Void', false, true, true, NULL, NOW(), NOW())
        ON CONFLICT DO NOTHING
    """)

def downgrade() -> None:
    op.execute("DELETE FROM public.quote_status WHERE code = 'void' AND tenant_id IS NULL")
```

---

### Step 3 — Migration: Add `invoice_status` `partial`

```bash
alembic revision -m "sd2_add_invoice_status_partial"
```

`upgrade()`:
```python
def upgrade() -> None:
    op.execute("SET LOCAL session_replication_role = 'replica';")
    op.execute("""
        INSERT INTO public.invoice_status
        (code, name, is_default, is_terminal, is_active, tenant_id, created_at, updated_at)
        VALUES ('partial', 'Partially Paid', false, false, true, NULL, NOW(), NOW())
        ON CONFLICT DO NOTHING
    """)

def downgrade() -> None:
    op.execute("DELETE FROM public.invoice_status WHERE code = 'partial' AND tenant_id IS NULL")
```

---

### Step 4 — Migration: Add `payment_status` `refunded`

```bash
alembic revision -m "sd2_add_payment_status_refunded"
```

`upgrade()`:
```python
def upgrade() -> None:
    op.execute("SET LOCAL session_replication_role = 'replica';")
    op.execute("""
        INSERT INTO public.payment_status
        (code, name, is_default, is_terminal, is_active, tenant_id, created_at, updated_at)
        VALUES ('refunded', 'Refunded', false, true, true, NULL, NOW(), NOW())
        ON CONFLICT DO NOTHING
    """)

def downgrade() -> None:
    op.execute("DELETE FROM public.payment_status WHERE code = 'refunded' AND tenant_id IS NULL")
```

---

### Step 5 — Migration: Drop refund columns from `payment`

**Pre-check**: Re-run MCP query #2 above. If COUNT > 0, STOP and ask Tom before proceeding.

```bash
alembic revision -m "sd2_drop_payment_refund_columns"
```

`upgrade()`:
```python
def upgrade() -> None:
    op.drop_column("payment", "refunded_amount_cents")
    op.drop_column("payment", "refunded_at")

def downgrade() -> None:
    import sqlalchemy as sa
    op.add_column("payment", sa.Column("refunded_amount_cents", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("payment", sa.Column("refunded_at", sa.DateTime(timezone=True), nullable=True))
```

---

### Step 6 — Update `Payment` SQLModel

**File**: `backend/app/models/billing.py`

Remove these two fields from the `Payment` class:
```python
# REMOVE:
refunded_amount_cents: int = ...
refunded_at: AwareDatetime | None = ...
```

After editing: `python generate_db_model_map.py`

Run pytest baseline check.

---

### Step 7 — Rewrite `_handle_refund_event()` in `stripe_subscriptions.py`

Replace the current implementation that updates refund columns with a version that creates a new **negative-amount payment row** with `status_code = 'refunded'`. See the design doc §D-5 for the full implementation pattern.

Key logic:
1. Find the original `payment` row by `stripe_payment_intent_id`
2. Look up `PaymentStatus` where `code='refunded'` and `tenant_id IS NULL`
3. If not found → `logger.error(...)` and return (do NOT crash)
4. Create a new `Payment` row with `amount_cents = -(charge.amount_refunded)` and `status_id = refunded_status.id`
5. `db.add(refund_row); db.commit()`

Run pytest baseline check.

---

### Step 8 — Add `partial` invoice status transition to `stripe_payment_intents.py`

After a successful payment is applied to an invoice, the existing code sets `invoice.status_code = 'paid'` when the full balance is received. Extend this logic to also set `status_code = 'partial'` when `0 < remaining_balance < invoice.total_cents`.

Read `stripe_payment_intents.py` fully before editing. Find the post-payment status transition block and add the partial check.

Run pytest baseline check.

---

### Step 9 — Remove 4 service get-or-create fallbacks

For each file, find the `if not notification_event: notification_event = NotificationEvent(...)` pattern and replace it with a hard lookup that logs an error and returns gracefully.

**Files to update:**
1. `backend/services/gps_variance_service.py` — `_enqueue_gps_variance_notification()` or equivalent
2. `backend/tasks/check_system_template_updates.py`
3. `backend/services/quickbooks_sync.py` — QB conflict notification path
4. `backend/tasks/auto_expire_qb_conflicts.py` — pre-warning path

**Pattern to use:**
```python
notification_type = db.exec(
    select(NotificationType).where(
        NotificationType.code == "the_code",
        NotificationType.tenant_id == None
    )
).first()
if not notification_type:
    logger.error("notification_type 'the_code' not seeded — run seed_core.py")
    return  # graceful skip for background tasks
```

Run pytest baseline check after all 4 files.

---

### Step 10 — Migration: Add `qco_line_type` `note`

```bash
alembic revision -m "sd2_add_qco_line_type_note"
```

`upgrade()`:
```python
def upgrade() -> None:
    op.execute("SET LOCAL session_replication_role = 'replica';")
    op.execute("""
        INSERT INTO public.qco_line_type
        (code, name, is_default, is_active, qb_item_name_hint, tenant_id, created_at, updated_at)
        VALUES ('note', 'Note', false, true, NULL, NULL, NOW(), NOW())
        ON CONFLICT DO NOTHING
    """)

def downgrade() -> None:
    op.execute("DELETE FROM public.qco_line_type WHERE code = 'note' AND tenant_id IS NULL")
```

---

### Step 11 — Migration: Add 6 `notification_type` rows

```bash
alembic revision -m "sd2_add_missing_notification_types"
```

`upgrade()`:
```python
def upgrade() -> None:
    op.execute("SET LOCAL session_replication_role = 'replica';")
    op.execute("""
        INSERT INTO public.notification_type
        (code, tenant_id, audience, name, description, is_active, created_at, updated_at)
        VALUES
          ('job_assigned', NULL, 'tenant', 'Job Assigned',
           'Fired when a technician is assigned to a job', true, NOW(), NOW()),
          ('schedule_changed', NULL, 'tenant', 'Schedule Changed',
           'Fired when a job schedule is updated', true, NOW(), NOW()),
          ('qb_sync_conflict', NULL, 'tenant', 'QB Sync Conflict',
           'Fired when a QuickBooks sync conflict is detected', true, NOW(), NOW()),
          ('qb_conflict_pre_warning', NULL, 'tenant', 'QB Conflict Pre-Warning',
           'Fired before a QB conflict is auto-expired', true, NOW(), NOW()),
          ('gps_variance_alert', NULL, 'tenant', 'GPS Variance Alert',
           'Fired when a tech clock-in GPS is far from the job site', true, NOW(), NOW()),
          ('system_template_updated', NULL, 'tenant', 'System Template Updated',
           'Fired when a system communication template is updated', true, NOW(), NOW())
        ON CONFLICT DO NOTHING
    """)

def downgrade() -> None:
    op.execute("""
        DELETE FROM public.notification_type
        WHERE code IN (
          'job_assigned', 'schedule_changed', 'qb_sync_conflict',
          'qb_conflict_pre_warning', 'gps_variance_alert', 'system_template_updated'
        ) AND tenant_id IS NULL
    """)
```

---

### Step 12 — Migration: Delete `data_exports` from `product_feature`

**Pre-check**: Re-run MCP query #3 above. Confirm 0 ppfv rows reference `data_exports` before deleting.

```bash
alembic revision -m "sd2_remove_data_exports_product_feature"
```

`upgrade()`:
```python
def upgrade() -> None:
    op.execute("SET LOCAL session_replication_role = 'replica';")
    op.execute("DELETE FROM public.product_feature WHERE code = 'data_exports'")

def downgrade() -> None:
    op.execute("""
        INSERT INTO public.product_feature (code, name, unit, description, created_at, updated_at)
        VALUES ('data_exports', 'Data exports', 'count',
                'Number of data export requests completed', NOW(), NOW())
        ON CONFLICT DO NOTHING
    """)
```

---

### Step 13 — Update `seed_core.py`

**File**: `backend/migrations/scripts/seed_core.py`

Make all 7 changes:

1. **`currency`** — set `is_active: False` for CAD, EUR, GBP rows in `SIMPLE_CODE_TABLES["currency"]["rows"]`
2. **`quote_status`** — add `{"code": "void", "name": "Void", "is_default": False, "is_terminal": True, "is_active": True}` to `TENANT_NULLABLE_CODE_TABLES["quote_status"]["rows"]`
3. **`invoice_status`** — add `{"code": "partial", "name": "Partially Paid", "is_default": False, "is_terminal": False, "is_active": True}` to `TENANT_NULLABLE_CODE_TABLES["invoice_status"]["rows"]`
4. **`payment_status`** — add `{"code": "refunded", "name": "Refunded", "is_default": False, "is_terminal": True, "is_active": True}` to `TENANT_NULLABLE_CODE_TABLES["payment_status"]["rows"]`
5. **`qco_line_type`** — add `{"code": "note", "name": "Note", "is_default": False, "is_active": True, "qb_item_name_hint": None}` to `TENANT_NULLABLE_CODE_TABLES["qco_line_type"]["rows"]`
6. **`notification_type`** — add 6 new rows to `TENANT_NULLABLE_CODE_TABLES["notification_type"]["rows"]` with correct `code`, `name`, `audience="tenant"`, `is_active=True`
7. **`PRODUCT_FEATURE_ROWS`** — remove the `data_exports` dict entirely

Run `python migrations/scripts/seed_core.py --mode show` and verify the changes appear correctly.

---

### Step 14 — Fix test inconsistency

**File**: `backend/tests/batch_b7b/test_a41_photo_upload_pipeline.py`

Line ~718: Change `job_expense_category_code="other"` to `job_expense_category_code="materials"`.

`other` is not a seeded expense category code. `materials` is the correct substitution.

---

## Test Requirements

Tests for this batch belong in these domains:

| New behavior | Domain folder |
|:---|:---|
| Refund creates negative payment row | `tests/domains/invoicing_billing/` |
| Invoice transitions to `partial` on under-payment | `tests/domains/invoicing_billing/` |
| `notification_type` seeded rows exist | `tests/domains/notifications_comms/` or verified via MCP-only check |

**Minimum tests required**:

1. `test_sd2_payment_refund_creates_negative_row.py` (domain: `invoicing_billing`):
   - Mock Stripe `charge.refunded` event → assert new `Payment` row created with negative `amount_cents` and `status_code = 'refunded'`
   - Assert original payment row is unchanged

2. `test_sd2_invoice_partial_status.py` (domain: `invoicing_billing`):
   - Create invoice with total 10000 cents → apply payment of 5000 cents → assert `invoice.status_code == 'partial'`
   - Apply another payment of 5000 cents → assert `invoice.status_code == 'paid'`

3. `test_sd2_notification_types_seeded.py` (domain: `notifications_comms`):
   - Via `db_session`, confirm all 6 new `notification_type` codes exist with `audience='tenant'` and `is_active=True`

**Test file structure** (declare `pytestmark` in every new file):
```python
pytestmark = [
    pytest.mark.domain_invoicing_billing,
    pytest.mark.unit,
]
```

---

## Schema JSON Sync

After all migrations run and tests pass, update the schema JSON for the `payment` table (two columns removed):

```bash
cd <repo>/backend
python schema_manager.py --help
```

Use the `delete` command to remove `refunded_amount_cents` and `refunded_at` from the `payment` table entry.

---

## Two-Phase Final Verification Gate

### Phase 1 — Unit tests only

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=short -q 2>&1 | tail -10
```

**Must match or exceed baseline count. Zero new failures.**

### Phase 2 — Full suite

```bash
python -m pytest --tb=short -q 2>&1 | tail -10
```

**Zero new failures.**

---

## Definition of Done Checklist

- [ ] 8 Alembic migrations applied (`alembic current` shows new head)
- [ ] `alembic downgrade -1 && alembic upgrade head` cycle tested for each migration
- [ ] `Payment` model has `refunded_amount_cents` and `refunded_at` removed
- [ ] `python generate_db_model_map.py` run after model change
- [ ] `stripe_subscriptions.py` `_handle_refund_event()` creates negative-amount payment row
- [ ] `stripe_payment_intents.py` transitions invoice to `partial` on underpayment
- [ ] 4 service/task get-or-create fallbacks replaced with hard lookup + graceful return
- [ ] `seed_core.py` updated with all 7 data changes
- [ ] `test_a41_photo_upload_pipeline.py` expense category code fixed
- [ ] Schema JSON updated via `schema_manager.py`
- [ ] Phase 1 gate: 0 new failures ← **separate line item**
- [ ] Phase 2 gate: 0 new failures ← **separate line item**

---

## Completion Summary

After finishing, post a summary in this format:

```
## SD-2 Completion Summary

**Completed**: [date]
**Baseline**: [N] passed, [N] failed
**Final Phase 1**: [N] passed, [N] failed
**Final Phase 2**: [N] passed, [N] failed

**Migrations applied (8)**:
1. sd2_deactivate_non_usd_currencies
2. sd2_add_quote_status_void
3. sd2_add_invoice_status_partial
4. sd2_add_payment_status_refunded
5. sd2_drop_payment_refund_columns
6. sd2_add_qco_line_type_note
7. sd2_add_missing_notification_types
8. sd2_remove_data_exports_product_feature

**Model changes**: Payment — removed refunded_amount_cents, refunded_at
**Service changes**: [list 4 service files + stripe_subscriptions + stripe_payment_intents]
**seed_core.py changes**: [list 7 changes]
**Test files created**: [list]
**Test files fixed**: test_a41_photo_upload_pipeline.py
**Any deviations from design doc**: [none or describe]
```
