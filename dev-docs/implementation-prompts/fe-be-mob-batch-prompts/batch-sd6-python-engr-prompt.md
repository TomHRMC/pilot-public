# Implementation Prompt: SD-6 — Deep Seed Data: Line Items, New Scenarios & README Updates

**Mode**: Pilot Python Engineer  
**Batch**: SD-6  
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §2 P1 — Full UI Seed Data Expansion  
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-sd6-design.md`  
**Estimated session**: 3–4 hours  
**Platform**: Backend only (`backend/migrations/scripts/`, `backend/README-seed-data.md`)  
**Frontend companion**: None — seed data only, no endpoint changes

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`dev-docs/architecture-design/pilot-python-engineer-methods.md`** — §16 (Standard Task Workflow), §5 (Model Design)
- **`backend/tests/README-adding-tests.md`** — Seed Data Coexistence Rules (§v1.3 section)

**Critical rules for this batch:**

- **Rule 1**: Never guess column names, data types, or table names. The design doc's §M contains MCP-verified column lists for every table in this batch. If you encounter a discrepancy between the prompt and the live DB → use the live DB column name and note it in your Completion Summary.
- **Rule 2**: This batch touches NO API endpoints, NO SQLModel models, NO Alembic migrations. Do NOT run `export_openapi_json.py` or `schema_manager.py`. Do NOT create any Alembic migration files.
- **Rule 3**: Seed scripts only manage data they inserted. Do NOT add cleanup logic for rows that originated from manual testing or other scripts. If `--reset` should remove a table's rows, that table must have been seeded by the same script.
- **Rule 4**: The `postgres-local` MCP is for **read-only verification only**. Never use it to INSERT, UPDATE, or DELETE — all data changes go through the Python seed scripts.
- **Rule 5**: All seed INSERTs must use `ON CONFLICT DO NOTHING` (or equivalent idempotency guard) so scripts can be re-run safely.
- **Rule 6**: `pricebook_item_version.id` is a **bigint** (not UUID). The column is `default_unit_price_cents` (not `unit_price_cents`). Use the exact values from §M.2 of the design doc.
- **Rule 7**: `change_order` and `loto_confirmation` have **no `status` column** — confirmed via MCP. The design doc describes intent via `description` text and `confirmed_at` timestamp respectively. Do not add a `status` field.
- **Rule 8**: `invoice_line.source_type` is `NOT NULL` with no default — every INSERT must include `source_type = 'manual'`.
- **Rule 9**: After inserting all invoice_line rows for an invoice, you MUST UPDATE the invoice's `subtotal_cents`, `tax_cents`, `total_cents`, and `balance_due_cents` to match the computed line totals. Do NOT leave the old hardcoded values in place.
- **Rule 10**: After all tasks pass unit tests — run the full suite (`pytest`) and fix any failures before declaring done.

---

## Pre-Work: Establish Regression Baseline

Before touching any file, capture the current unit-only test baseline:

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=no -q 2>&1 | tail -5
```

Record the exact count: **`X passed, Y failed`**.

> **If any tests are already failing before you start**: Do NOT treat them as "pre-existing" and proceed anyway. Either confirm with Tom that this is a known, accepted failure with a documented reason, or fix the failure before touching any batch files.

---

## Pre-Work: Run MCP Verification Queries

Run **all** of these via `postgres-local` MCP before writing any code. If any returns unexpected results → **STOP and ask Tom**.

```sql
-- 1. Confirm invoice_line is still empty (should be 0)
SELECT COUNT(*) FROM invoice_line WHERE tenant_id = '00000000-0000-0000-0000-000000000001';
-- Expected: 0

-- 2. Confirm invoice_line_tax_component is empty
SELECT COUNT(*) FROM invoice_line_tax_component WHERE tenant_id = '00000000-0000-0000-0000-000000000001';
-- Expected: 0

-- 3. All 8 invoices — IDs and current totals (you'll UPDATE these)
SELECT invoice_number, id, total_cents, subtotal_cents, tax_cents, balance_due_cents
FROM invoice
WHERE tenant_id = '00000000-0000-0000-0000-000000000001'
ORDER BY invoice_number;

-- 4. Pricebook items + version IDs with prices (bigint version IDs)
SELECT pi.name, pi.id AS item_id, piv.id AS version_id, piv.default_unit_price_cents, pi.taxability_code
FROM pricebook_item pi
JOIN pricebook_item_version piv ON piv.pricebook_item_id = pi.id
WHERE pi.tenant_id = '00000000-0000-0000-0000-000000000001'
ORDER BY pi.name;

-- 5. qco_line_type IDs (needed for invoice_line and change_order_line)
SELECT id, code FROM qco_line_type ORDER BY code;

-- 6. US-DEFAULT tax rate
SELECT id, jurisdiction_code, rate_pct FROM tax_rate_version WHERE jurisdiction_code = 'US-DEFAULT';
-- Expected: id=1, rate_pct=6.0

-- 7. Confirm existing conflict mobile_sync_event
SELECT id, operation_type, status, conflict_severity
FROM mobile_sync_event
WHERE id = '624b8d17-6c49-402d-b6fc-874a0cd039e1';

-- 8. mobile_sync_owner_escalation is empty
SELECT COUNT(*) FROM mobile_sync_owner_escalation WHERE tenant_id = '00000000-0000-0000-0000-000000000001';
-- Expected: 0

-- 9. loto_confirmation is empty
SELECT COUNT(*) FROM loto_confirmation WHERE tenant_id = '00000000-0000-0000-0000-000000000001';
-- Expected: 0

-- 10. change_order is empty
SELECT COUNT(*) FROM change_order WHERE tenant_id = '00000000-0000-0000-0000-000000000001';
-- Expected: 0

-- 11. in_app_notification is empty
SELECT COUNT(*) FROM in_app_notification WHERE tenant_id = '00000000-0000-0000-0000-000000000001';
-- Expected: 0

-- 12. user_setting_override keys with user override allowed
SELECT key, label, value_type FROM platform_setting_catalog WHERE allows_user_override = true;
-- Expected: background_sync_enabled (boolean), voice_persona_tone (string)

-- 13. tenant_phone_number cleanup confirmed
SELECT COUNT(*) FROM tenant_phone_number WHERE tenant_id = '00000000-0000-0000-0000-000000000001';
-- Expected: 1 (Tom already ran the cleanup SQL)

-- 14. Q-CONV-001 job ID for change_order FKs
SELECT q.id AS quote_id, j.id AS job_id, j.job_number
FROM quote q
JOIN quote_status qs ON qs.id = q.status_id
JOIN job j ON j.quote_id = q.id
WHERE q.tenant_id = '00000000-0000-0000-0000-000000000001'
  AND qs.code = 'converted';
-- Expected: job_number=JOB-900001, job_id=60605a9f-e883-42f0-abd8-21a33254a27f

-- 15. Existing payment_method_id used by all seed payments
SELECT DISTINCT payment_method_id FROM payment
WHERE tenant_id = '00000000-0000-0000-0000-000000000001';
-- Expected: 02e3ab2d-27be-41c0-b425-1e2da0b08f7f
```

> **MCP Usage Rule**: Read-only verification only. Never INSERT/UPDATE/DELETE via MCP — all data changes go through the seed scripts.

---

## Pre-Work: Read These Source Files

Use `read_file` on each before writing any code:

```
backend/migrations/scripts/seed_scenario_quote_to_cash.py   ← existing script you'll expand
backend/migrations/scripts/seed_scenario_reporting.py       ← existing script you'll expand  
backend/migrations/scripts/seed_scenario_mobile_sync.py     ← existing script you'll expand
backend/migrations/scripts/seed_test_tenant.py              ← existing script for user_preference/setting
backend/migrations/scripts/reset_dev_db.py                  ← register new notifications scenario here
backend/migrations/scripts/_db_utils.py                     ← shared session context manager pattern
backend/README-seed-data.md                                 ← sections §4, §7, §8, §9, §10 to update
```

---

## Background & Context

**What this batch does**: Fills the remaining seed data gaps identified in the SD-6 audit session (2026-07-15). The highest-impact item is `invoice_line` — all 8 invoices currently have calculated totals but zero line items, so the Invoice Detail UI shows a blank table. This batch also seeds 4 new entity types (change orders, LOTO confirmations, owner escalations, in-app notifications), adds user preference data, and updates the README documentation.

**No new API endpoints, models, or migrations.** This is a seed-data-only batch. The scope is entirely within `backend/migrations/scripts/` and `backend/README-seed-data.md`.

**Key reference data** (MCP-verified — use exactly):
- `qco_line_type` IDs: labor=`65a92851-3635-4d42-a99c-c40f1ab2e52e`, material=`bb1588c7-e91f-4db8-8497-5d81679bc084`, misc=`c067e242-84dc-4d73-bdce-84aec6d0bd3a`, note=`1dd2f395-e703-4247-a57d-08e90e1ffd90`
- `tax_rate_version`: id=`1` (bigint), `jurisdiction_code='US-DEFAULT'`, `rate_pct=6.00`
- `pricebook_item_version` column is `default_unit_price_cents` (NOT `unit_price_cents`)
- `payment_method_id` for all new payments: `02e3ab2d-27be-41c0-b425-1e2da0b08f7f`

---

## Task 1 — `invoice_line` + `invoice_line_tax_component` for All 8 Invoices

**Files**: `seed_scenario_quote_to_cash.py` (INV-900001) and `seed_scenario_reporting.py` (INV-SEED-A through G)

**Reference**: Design doc §D for full line-by-line specification.

### 1.1 For each invoice, implement this pattern:

```python
ANCHOR_DATE = datetime(2026, 7, 1, tzinfo=timezone.utc)
TENANT_ID = '00000000-0000-0000-0000-000000000001'
TAX_RATE_VERSION_ID = 1  # bigint — US-DEFAULT, 6%
TAX_RATE_PCT = Decimal('6.00')

# qco_line_type IDs
QCO_LABOR   = '65a92851-3635-4d42-a99c-c40f1ab2e52e'
QCO_MATERIAL= 'bb1588c7-e91f-4db8-8497-5d81679bc084'
QCO_MISC    = 'c067e242-84dc-4d73-bdce-84aec6d0bd3a'
QCO_NOTE    = '1dd2f395-e703-4247-a57d-08e90e1ffd90'

# pricebook_item IDs (UUID — NOT the bigint version ID)
ITEM_OUTLET  = 'e1881d63-e6ab-4514-b9e6-20e3b6d8236f'
ITEM_PANEL   = '683de1cb-1909-465e-a12a-dc33b12a0311'
ITEM_BREAKER = '3090ca84-374a-4315-8a63-42e61c22fde8'
ITEM_CONDUIT = 'd2e55b5d-bdb7-403e-a2b6-3139768a654c'
ITEM_PERMIT  = '0cd9bfda-c801-4711-b22c-e6377450ed01'
ITEM_WIRE    = 'd8254a6f-c0af-42a4-af76-7667958522ce'
```

For each line item:
1. Compute `subtotal_cents = round(unit_price_cents * quantity)`
2. If `taxability_code = 'taxable'`: `tax_amount_cents = round(subtotal_cents * 0.06)`, else `0`
3. `total_cents = subtotal_cents + tax_amount_cents`
4. INSERT into `invoice_line`
5. If taxable, INSERT into `invoice_line_tax_component`

After all lines for the invoice:
6. Compute invoice totals from lines: `subtotal = sum(line.subtotal_cents)`, `tax = sum(tax_components.amount_cents)`, `total = subtotal + tax`
7. Set `balance_due` based on invoice status (0 for paid, `total` for others, `total - partial_payment` for partial)
8. UPDATE invoice row with computed totals
9. For paid invoices: UPDATE the positive payment row's `amount_cents` to match the new `total_cents`

### 1.2 Required `invoice_line` fields:

```sql
INSERT INTO invoice_line (
  id, invoice_id, source_type, source_id, position,
  qco_line_type_id, pricebook_item_id, description,
  quantity, unit, unit_price_cents, taxability_code,
  subtotal_cents, total_cents,
  tax_rate_pct, tax_basis_cents, tax_amount_cents,
  tax_jurisdiction_code, tax_as_of, tax_source,
  is_active, tenant_id, created_at, created_by
) VALUES (
  gen_random_uuid(), :invoice_id, 'manual', NULL, :position,
  :qco_line_type_id, :pricebook_item_id, :description,
  :quantity, :unit, :unit_price_cents, :taxability_code,
  :subtotal_cents, :total_cents,
  -- For taxable lines:
  6.00, :subtotal_cents, :tax_amount_cents, 'US-DEFAULT', NOW(), 'manual_rate',
  -- For exempt lines: NULL for all tax fields
  true, :tenant_id, NOW(), NULL
)
ON CONFLICT DO NOTHING  -- (no unique constraint — idempotency via --reset logic)
```

> **Note**: `invoice_line` has no `updated_at` (it's append-only). Do NOT include `updated_at` in the INSERT.

### 1.3 Required `invoice_line_tax_component` fields:

```sql
INSERT INTO invoice_line_tax_component (
  id, invoice_line_id, tax_rate_version_id, component_code,
  rate_pct, amount_cents, is_active, tenant_id, created_at, created_by
) VALUES (
  gen_random_uuid(), :invoice_line_id, 1, 'US-DEFAULT',
  6.00, :amount_cents, true, :tenant_id, NOW(), NULL
)
```

### 1.4 Exact line plans

See **design doc §D.3** for the complete line-by-line specification for all 8 invoices with exact quantities, prices, tax calculations, and computed totals. Use those numbers precisely — do not recalculate from scratch.

**Summary of new totals** (implement from design doc):
| Invoice | New total_cents | New balance_due_cents | Payment update needed? |
|---|---|---|---|
| INV-900001 | 95,596 | 0 | Yes → payment = 95,596 |
| INV-SEED-A | 226,135 | 0 | Yes → payment = 226,135 |
| INV-SEED-B | 43,778 | 0 | Yes → payment = 43,778 (keep refund row at -3,200) |
| INV-SEED-C | 115,630 | 115,630 | No payment |
| INV-SEED-D | 16,960 | 16,960 | No payment |
| INV-SEED-E | 215,800 | 135,800 | Yes → partial payment = 80,000 |
| INV-SEED-F | 234,350 | 234,350 | No payment |
| INV-SEED-G | 506,860 | 506,860 | No payment |

### 1.5 `--reset` addition

In both seed scripts' reset block, add BEFORE existing deletes:
```python
db.exec(text("DELETE FROM invoice_line_tax_component WHERE tenant_id = :tid"), {"tid": TENANT_ID})
db.exec(text("DELETE FROM invoice_line WHERE tenant_id = :tid"), {"tid": TENANT_ID})
# Reset invoice totals back to 0
db.exec(text("""
  UPDATE invoice SET subtotal_cents=0, tax_cents=0, total_cents=0, balance_due_cents=0
  WHERE tenant_id = :tid AND invoice_number IN ('INV-900001','INV-SEED-A','INV-SEED-B',
    'INV-SEED-C','INV-SEED-D','INV-SEED-E','INV-SEED-F','INV-SEED-G')
"""), {"tid": TENANT_ID})
```

### Checkpoint after Task 1

```bash
python -m pytest -m unit --tb=short -q 2>&1 | tail -5
```

All unit tests must pass before continuing.

---

## Task 2 — `mobile_sync_owner_escalation`: W-12 Coverage

**File**: `seed_scenario_mobile_sync.py`

**Reference**: Design doc §E.

### 2.1 Rows to seed

**Row 1 — Open escalation** (linked to existing conflict event):
```python
CONFLICT_EVENT_ID = '624b8d17-6c49-402d-b6fc-874a0cd039e1'

# Insert into mobile_sync_owner_escalation:
{
    "id": uuid.uuid4(),
    "tenant_id": TENANT_ID,
    "originating_user_id": "00000000-0000-0000-0000-000000000003",  # tech
    "conflict_id": CONFLICT_EVENT_ID,
    "escalated_at": ANCHOR_DATE,  # 2026-07-01
    "escalation_reason": "job_status_conflict",
    "escalation_reason_explainer": "Technician attempted to mark job in_progress while owner had already changed status to scheduled. Requires owner review before proceeding.",
    "status": "pending",
    "resolved_by_user_id": None,
    "resolved_at": None,
    "resolution_action": None,
    "resolution_payload": None,
    "created_at": ANCHOR_DATE,
    "updated_at": ANCHOR_DATE,
}
```

**Row 2 — Resolved escalation**: First insert a new `mobile_sync_event` row, then the resolved escalation.

New `mobile_sync_event`:
```python
{
    "id": uuid.uuid4(),  # capture this ID
    "tenant_id": TENANT_ID,
    "user_id": "00000000-0000-0000-0000-000000000003",
    "device_id": "00000000-0000-0000-0002-000000000001",
    "operation_type": "update_expense",
    "status": "conflict",
    "conflict_severity": "owner_escalation",
    "idempotency_uuid": "00000000-0002-0002-0002-000000000099",
    "client_capture_at": ANCHOR_DATE - timedelta(days=10),
    "created_at": ANCHOR_DATE - timedelta(days=10),
}
```

Resolved escalation (using captured event ID above):
```python
{
    "id": uuid.uuid4(),
    "tenant_id": TENANT_ID,
    "originating_user_id": "00000000-0000-0000-0000-000000000003",
    "conflict_id": <id from new event above>,
    "escalated_at": ANCHOR_DATE - timedelta(days=10),
    "escalation_reason": "expense_amount_conflict",
    "escalation_reason_explainer": "Technician submitted an expense update that conflicted with a recently approved purchase order. Owner reviewed and accepted the technician change.",
    "status": "resolved",
    "resolved_by_user_id": "00000000-0000-0000-0000-000000000002",  # owner
    "resolved_at": ANCHOR_DATE - timedelta(days=9),
    "resolution_action": "owner_accepted_device_change",
    "resolution_payload": {"accepted_value": "materials", "note": "Technician expense confirmed correct"},
    "created_at": ANCHOR_DATE - timedelta(days=10),
    "updated_at": ANCHOR_DATE - timedelta(days=9),
}
```

### 2.2 `--reset` addition

Add to reset block:
```python
db.exec(text("DELETE FROM mobile_sync_owner_escalation WHERE tenant_id = :tid"), {"tid": TENANT_ID})
# Also delete the fabricated mobile_sync_event (idempotency_uuid = ...0099)
db.exec(text("""
  DELETE FROM mobile_sync_event
  WHERE tenant_id = :tid
    AND idempotency_uuid = '00000000-0002-0002-0002-000000000099'
"""), {"tid": TENANT_ID})
```

---

## Task 3 — `loto_confirmation`: Safety Workflow Data

**File**: `seed_scenario_reporting.py`

**Reference**: Design doc §F.

### 3.1 Key schema note

There is **no `status` column**. A `loto_confirmation` row = a completed lockout. Use `confirmed_at` timestamp to represent when the lockout was confirmed.

### 3.2 Job ID lookup pattern

The reporting script seeds jobs with non-deterministic UUIDs. At seed time, look up job IDs via invoice number:

```python
def get_job_id_by_invoice(db, invoice_number: str) -> str:
    result = db.exec(text("""
        SELECT j.id FROM job j
        JOIN invoice i ON i.job_id = j.id
        WHERE i.tenant_id = :tid AND i.invoice_number = :inv_num
    """), {"tid": TENANT_ID, "inv_num": invoice_number}).first()
    return str(result[0]) if result else None
```

### 3.3 Rows to seed

**Row 1** — LOTO for Panel Upgrade job (INV-SEED-A, ~30 days before anchor):
```python
job_id = get_job_id_by_invoice(db, "INV-SEED-A")
confirmed_at = ANCHOR_DATE - timedelta(days=30) + timedelta(hours=9, minutes=15)
{
    "id": uuid.uuid4(),
    "tenant_id": TENANT_ID,
    "job_id": job_id,
    "user_id": "00000000-0000-0000-0000-000000000003",  # tech
    "confirmed_at": confirmed_at,
    "client_capture_at": confirmed_at,
    "server_received_at": confirmed_at + timedelta(seconds=2),
    "is_active": True,
    "created_at": confirmed_at,
}
```

**Row 2** — LOTO for Commercial Rewire job (INV-SEED-G, ~75 days before anchor):
```python
job_id = get_job_id_by_invoice(db, "INV-SEED-G")
confirmed_at = ANCHOR_DATE - timedelta(days=75) + timedelta(hours=8)
{
    "id": uuid.uuid4(),
    "tenant_id": TENANT_ID,
    "job_id": job_id,
    "user_id": "00000000-0000-0000-0000-000000000003",
    "confirmed_at": confirmed_at,
    "client_capture_at": confirmed_at,
    "server_received_at": confirmed_at + timedelta(seconds=5),
    "is_active": True,
    "created_at": confirmed_at,
}
```

> **`created_by` is nullable** (no `StandardAuditMixin` — seed scripts set `created_by=None`).

### 3.4 `--reset` addition

```python
db.exec(text("DELETE FROM loto_confirmation WHERE tenant_id = :tid"), {"tid": TENANT_ID})
```

---

## Task 4 — `change_order` + `change_order_line`: Job Change Orders

**File**: `seed_scenario_quote_to_cash.py`

**Reference**: Design doc §G.

### 4.1 Target job

Both change orders attach to **JOB-900001** (id=`60605a9f-e883-42f0-abd8-21a33254a27f`).

At seed time, verify via query:
```python
job_id = "60605a9f-e883-42f0-abd8-21a33254a27f"  # hard-coded from MCP verification
# Or dynamically: get via job_number='JOB-900001'
```

### 4.2 Change order data

**CO-001** — "Additional panel breakers — pending owner approval":
```python
co1_id = uuid.uuid4()
{
    "id": co1_id,
    "job_id": job_id,
    "tenant_id": TENANT_ID,
    "description": "Additional 20A breakers requested by customer after panel inspection — awaiting owner approval",
    "subtotal_cents": 29400,
    "tax_cents": 1764,      # round(29400 * 0.06)
    "total_cents": 31164,
    "is_active": True,
    "created_at": ANCHOR_DATE - timedelta(days=2),
    "updated_at": ANCHOR_DATE - timedelta(days=2),
}
```

Lines for CO-001:
```python
# Line 1: material — 15A Circuit Breaker × 8
{
    "id": uuid.uuid4(),
    "change_order_id": co1_id,
    "position": 1,
    "qco_line_type_id": QCO_MATERIAL,
    "pricebook_item_id": ITEM_BREAKER,
    "description": "15A Circuit Breaker",
    "quantity": 8,
    "unit": "ea",
    "unit_price_cents": 1800,
    "subtotal_cents": 14400,
    "total_cents": 15264,   # 14400 + round(14400*0.06)=864
    "taxability_code": "taxable",
    "tenant_id": TENANT_ID,
    ...timestamps
}
# Line 2: labor — Standard Outlet Installation × 1
{
    "id": uuid.uuid4(),
    "change_order_id": co1_id,
    "position": 2,
    "qco_line_type_id": QCO_LABOR,
    "pricebook_item_id": ITEM_OUTLET,
    "description": "Standard Outlet Installation",
    "quantity": 1,
    "unit": "ea",
    "unit_price_cents": 15000,
    "subtotal_cents": 15000,
    "total_cents": 15900,   # 15000 + round(15000*0.06)=900
    "taxability_code": "taxable",
    "tenant_id": TENANT_ID,
    ...timestamps
}
```

**CO-002** — "Conduit extension — approved":
```python
co2_id = uuid.uuid4()
{
    "id": co2_id,
    "job_id": job_id,
    "tenant_id": TENANT_ID,
    "description": "Extension of EMT conduit run to secondary panel location — approved by owner 2026-07-10",
    "subtotal_cents": 44000,
    "tax_cents": 2640,      # round(44000 * 0.06)
    "total_cents": 46640,
    "is_active": True,
    "created_at": ANCHOR_DATE + timedelta(days=9),
    "updated_at": ANCHOR_DATE + timedelta(days=9),
}
```

Lines for CO-002:
```python
# Line 1: labor — Standard Outlet Installation × 2
# Line 2: material — EMT Conduit × 40 ft
# Line 3: note — display text, no price
```
See design doc §G.2 for exact values.

### 4.3 `--reset` addition

```python
# Delete lines first (FK dependency)
db.exec(text("DELETE FROM change_order_line WHERE tenant_id = :tid"), {"tid": TENANT_ID})
db.exec(text("DELETE FROM change_order WHERE tenant_id = :tid"), {"tid": TENANT_ID})
```

---

## Task 5 — `seed_scenario_notifications.py`: New File

**File**: Create `backend/migrations/scripts/seed_scenario_notifications.py`

**Reference**: Design doc §H.

### 5.1 Script structure

Follow the exact pattern from `seed_scenario_nec.py` (which was the most recently written clean script). Use:
- `argparse` with `--mode` (seed/inspect/show) and `--reset`
- `TENANT_ID`, `OWNER_USER_ID`, `ANCHOR_DATE` constants
- `mode_seed()`, `mode_inspect()`, `mode_show()` functions
- Call `mode_seed()` as default in `if __name__ == '__main__'`

### 5.2 Rows to seed

All 5 rows for owner user `00000000-0000-0000-0000-000000000002`.

```python
ANCHOR_DATE = datetime(2026, 7, 1, tzinfo=timezone.utc)
OWNER_USER_ID = '00000000-0000-0000-0000-000000000002'

notifications = [
    {
        "category_id": "job_activity",
        "body": "Tech assigned to Panel Upgrade job (JOB-SEED-A). Scheduled for tomorrow at 8:00 AM.",
        "deep_link_target": "/jobs/JOB-SEED-A",
        "priority": "standard",
        "read_at": None,  # unread
        "created_at": ANCHOR_DATE - timedelta(days=2),
    },
    {
        "category_id": "sync_conflicts",
        "body": "QuickBooks sync conflict on invoice INV-SEED-B: customer name mismatch. Review required before next sync.",
        "deep_link_target": "/settings/quickbooks/conflicts",
        "priority": "urgent",
        "read_at": None,  # unread
        "created_at": ANCHOR_DATE - timedelta(days=1),
    },
    {
        "category_id": "billing",
        "body": "Invoice INV-SEED-C is overdue by 14 days. Second dunning reminder sent to customer.",
        "deep_link_target": "/invoices/INV-SEED-C",
        "priority": "standard",
        "read_at": ANCHOR_DATE - timedelta(days=3),  # read
        "created_at": ANCHOR_DATE - timedelta(days=3),
    },
    {
        "category_id": "customer_activity",
        "body": "SMS sent to Carlos Rivera: \"On my way to your location. ETA 15 minutes.\" Delivered successfully.",
        "deep_link_target": "/communications",
        "priority": "standard",
        "read_at": ANCHOR_DATE - timedelta(days=5),  # read
        "created_at": ANCHOR_DATE - timedelta(days=5),
    },
    {
        "category_id": "field_issues",
        "body": "GPS variance alert: tech location differs from job site by more than 0.5 miles on DISP-002. Review if unexpected.",
        "deep_link_target": "/dispatch",
        "priority": "standard",
        "read_at": ANCHOR_DATE - timedelta(days=7),  # read
        "created_at": ANCHOR_DATE - timedelta(days=7),
    },
]
```

### 5.3 INSERT pattern

```python
for n in notifications:
    db.exec(text("""
        INSERT INTO in_app_notification
          (id, tenant_id, user_id, category_id, body, deep_link_target, priority, read_at, created_at)
        VALUES
          (gen_random_uuid(), :tid, :uid, :category_id, :body, :deep_link_target, :priority, :read_at, :created_at)
    """), {
        "tid": TENANT_ID,
        "uid": OWNER_USER_ID,
        "category_id": n["category_id"],
        "body": n["body"],
        "deep_link_target": n["deep_link_target"],
        "priority": n["priority"],
        "read_at": n["read_at"],
        "created_at": n["created_at"],
    })
```

> **Idempotency note**: `in_app_notification` uses `gen_random_uuid()` — there's no natural unique key to conflict on. Idempotency is handled by the `--reset` path (delete by tenant_id + user_id before re-seeding).

### 5.4 Register in `reset_dev_db.py`

Add `"notifications"` to the scenario registry in `reset_dev_db.py`, following the same pattern as other Group D scenarios.

---

## Task 6 — `user_preference` + `user_setting_override` in `seed_test_tenant.py`

**File**: `seed_test_tenant.py`

**Reference**: Design doc §I.

### 6.1 `user_preference` — 1 row for owner

Add after the `user_endpoint` seeding block in `mode_seed()`:

```python
db.exec(text("""
    INSERT INTO user_preference (id, user_id, tenant_id, preferences, created_at, updated_at)
    VALUES (gen_random_uuid(), :uid, :tid, :prefs::jsonb, NOW(), NOW())
    ON CONFLICT (user_id) DO NOTHING
"""), {
    "uid": OWNER_USER_ID,
    "tid": TENANT_ID,
    "prefs": json.dumps({
        "theme": "light",
        "sidebar_collapsed": False,
        "notification_sounds": True,
        "default_invoice_terms": "net_30",
        "dashboard_layout": "default"
    })
})
```

> **Check `user_preference` unique constraint first**: Run `SELECT conname, contype FROM pg_constraint WHERE conrelid = 'public.user_preference'::regclass;` via MCP to confirm the unique column. Adjust the `ON CONFLICT` clause to match.

### 6.2 `user_setting_override` — 2 rows for owner

```python
for key, value in [
    ("background_sync_enabled", True),
    ("voice_persona_tone", "professional"),
]:
    db.exec(text("""
        INSERT INTO user_setting_override
          (tenant_id, user_id, setting_key, value, created_at, updated_at)
        VALUES
          (:tid, :uid, :key, :val::jsonb, NOW(), NOW())
        ON CONFLICT (tenant_id, user_id, setting_key) DO NOTHING
    """), {
        "tid": TENANT_ID,
        "uid": OWNER_USER_ID,
        "key": key,
        "val": json.dumps(value),
    })
```

### 6.3 Add to `mode_inspect()`

```python
pref_rows = db.exec(text(
    "SELECT id FROM user_preference WHERE user_id = :uid"
), {"uid": OWNER_USER_ID}).all()
print(f"[user_preference] {len(pref_rows)} row(s)  user=dev@pilot.local")

override_rows = db.exec(text(
    "SELECT setting_key FROM user_setting_override WHERE tenant_id = :tid AND user_id = :uid"
), {"tid": TENANT_ID, "uid": OWNER_USER_ID}).all()
keys = [r[0] for r in override_rows]
print(f"[user_setting_override] {len(override_rows)} row(s)  keys={','.join(keys)}")
```

---

## Task 7 — `README-seed-data.md` Documentation Updates

**File**: `backend/README-seed-data.md`

**Reference**: Design doc §J.

### 7.1 Updates required:

1. **§4 Group A table** — correct 3 row counts:
   - `communication_template`: 15 → **17** rows
   - `platform_setting_catalog`: 42 → **48** rows
   - `platform_setting` (defaults): 42 → **49** rows

2. **§4 Group D tables** — add new tables seeded by SD-6 for each script:
   - `seed_scenario_quote_to_cash.py`: add `change_order` (2 rows), `change_order_line` (5 rows), `invoice_line` (N rows), `invoice_line_tax_component` (N rows)
   - `seed_scenario_reporting.py`: add `invoice_line` (N rows), `invoice_line_tax_component` (N rows), `loto_confirmation` (2 rows)
   - `seed_scenario_mobile_sync.py`: add `mobile_sync_owner_escalation` (2 rows)
   - Add new script row: `seed_scenario_notifications.py` → `in_app_notification` (5 rows)

3. **§7 Known Constraints & Gotchas** — add new gotcha:
   > **Seed scripts only manage their own inserted data**: Each seed script only deletes/reseeds rows it has inserted. Do NOT add cleanup logic for rows from manual testing or other debugging sessions. For one-time cleanup of spurious rows, use a standalone SQL statement. If a completely clean DB is needed, instantiate from the schema-only SQL file and run seed scripts in order (A → B → C → D).

4. **§8 What Is NOT Seeded** — add 3 new entries:
   - `psp_customer`, `psp_transaction_log` — requires real Stripe transaction IDs; cannot be fabricated
   - `voice_command_log`, `voice_command_entity_link`, `voice_feedback`, `conversation_session`, `conversation_message` — requires live Voice AI session (Whisper + Ollama)
   - `integration_credential`, `integration_sync_log`, `integration_sync_conflict`, `connector_run_log`, `connector_config` — requires QuickBooks OAuth flow

5. **§9 Scenario Status Registry** — add new row:
   - `notifications` | `seed_scenario_notifications.py` | dev-only | ✅ Complete (SD-6)

6. **§10 Roadmap** — add SD-5 ✅ Complete entry and SD-6 🔄 Active entry (see design doc §J.5 for exact text).

---

## Final Verification

### Phase 1 — Unit Tests Only (run after each task group during implementation)

```bash
cd <repo>/backend
source .venv/bin/activate

python -m pytest -m unit --tb=short -q 2>&1 | tail -10
```

All unit tests must pass before moving to the next task.

### Phase 2 — Full Suite + Seed Script Smoke Test (run once at the end)

```bash
cd <repo>/backend
source .venv/bin/activate

# Full test suite
python -m pytest --tb=short -q 2>&1 | tail -10

# Run the daily reset to confirm all scripts work end-to-end
python migrations/scripts/reset_dev_db.py --wipe-only
python migrations/scripts/seed_scenario_quote_to_cash.py
python migrations/scripts/seed_scenario_reporting.py
python migrations/scripts/seed_scenario_dispatch.py
python migrations/scripts/seed_scenario_customer_comms.py
python migrations/scripts/seed_scenario_supplier_catalog.py
python migrations/scripts/seed_scenario_nec.py
python migrations/scripts/seed_scenario_mobile_sync.py
python migrations/scripts/seed_scenario_notifications.py

# Inspect to verify all counts
python migrations/scripts/reset_dev_db.py --mode inspect
python migrations/scripts/seed_test_tenant.py --mode inspect

# Spot-check invoice_line and invoice_line_tax_component
python -c "
from sqlalchemy import create_engine, text
import os
engine = create_engine(os.environ['DATABASE_URL'])
with engine.connect() as conn:
    il = conn.execute(text('SELECT COUNT(*) FROM invoice_line')).scalar()
    iltc = conn.execute(text('SELECT COUNT(*) FROM invoice_line_tax_component')).scalar()
    notif = conn.execute(text('SELECT COUNT(*) FROM in_app_notification')).scalar()
    loto = conn.execute(text('SELECT COUNT(*) FROM loto_confirmation')).scalar()
    co = conn.execute(text('SELECT COUNT(*) FROM change_order')).scalar()
    esc = conn.execute(text('SELECT COUNT(*) FROM mobile_sync_owner_escalation')).scalar()
    pref = conn.execute(text(\"SELECT COUNT(*) FROM user_preference WHERE user_id = '00000000-0000-0000-0000-000000000002'\")).scalar()
    print(f'invoice_line: {il}')
    print(f'invoice_line_tax_component: {iltc}')
    print(f'in_app_notification: {notif}')
    print(f'loto_confirmation: {loto}')
    print(f'change_order: {co}')
    print(f'mobile_sync_owner_escalation: {esc}')
    print(f'user_preference (owner): {pref}')
"

echo "=== SD-6 FINAL VERIFICATION COMPLETE ==="
```

**Expected counts after full seed run**:
- `invoice_line`: ≥ 27 rows (3+4+3+3+2+2+3+4 across all 8 invoices)
- `invoice_line_tax_component`: ≥ 20 rows (taxable lines only)
- `in_app_notification`: 5 rows (owner user)
- `loto_confirmation`: 2 rows
- `change_order`: 2 rows
- `mobile_sync_owner_escalation`: 2 rows
- `user_preference (owner)`: 1 row

> **Any failure in either phase must be fixed before the batch is declared done.**

---

## Test Requirements

This batch adds **no new API endpoints or business logic** — it is seed-script-only. No new test files are required for this batch.

**However**: If any existing test fails because of the invoice total changes (invoice `total_cents` values are being updated), investigate the root cause. Existing tests that assert on specific hardcoded invoice totals must be updated to use the new computed totals. These are not "pre-existing failures" — they are caused by this batch and must be fixed before declaring done.

---

## Definition of Done

- [ ] Pre-modification regression baseline captured (`X passed, Y failed`) using `pytest -m unit`
- [ ] Zero pre-existing unit failures confirmed before starting work
- [ ] All 15 MCP pre-work queries run and results match expected values
- [ ] All mandatory source files read before writing any code
- [ ] `invoice_line` rows inserted for all 8 invoices (correct pricebook FKs, balanced math)
- [ ] `invoice_line_tax_component` rows inserted for all taxable lines (6% US-DEFAULT)
- [ ] All 8 invoices' `subtotal_cents`, `tax_cents`, `total_cents`, `balance_due_cents` UPDATED to match line totals
- [ ] Payment `amount_cents` UPDATED for INV-900001, INV-SEED-A, INV-SEED-B paid invoices
- [ ] `mobile_sync_owner_escalation`: 1 open + 1 resolved rows inserted in `seed_scenario_mobile_sync.py`
- [ ] `loto_confirmation`: 2 confirmed rows inserted in `seed_scenario_reporting.py`
- [ ] `change_order`: 2 rows + 5 `change_order_line` rows inserted in `seed_scenario_quote_to_cash.py`
- [ ] New `seed_scenario_notifications.py` created — 5 `in_app_notification` rows, standard argparse pattern, registered in `reset_dev_db.py`
- [ ] `user_preference`: 1 row for owner user in `seed_test_tenant.py`
- [ ] `user_setting_override`: 2 rows for owner user in `seed_test_tenant.py`
- [ ] `mode_inspect()` updated in all modified scripts to show new tables
- [ ] `README-seed-data.md` §4 Group A counts corrected (communication_template, platform_setting_catalog, platform_setting)
- [ ] `README-seed-data.md` §4 Group D updated with new SD-6 tables per script
- [ ] `README-seed-data.md` §7 new "seed scripts only manage their own data" gotcha added
- [ ] `README-seed-data.md` §8 3 new "not seeded" entries added
- [ ] `README-seed-data.md` §9 notifications scenario added
- [ ] `README-seed-data.md` §10 SD-5 ✅ Complete entry added (closed 2026-07-15)
- [ ] `README-seed-data.md` §10 SD-6 🔄 Active entry added
- [ ] `--reset` logic in all modified scripts deletes newly added tables (children before parents)
- [ ] Full seed run (`reset_dev_db.py --wipe-only` + all scripts) completes without errors
- [ ] `reset_dev_db.py --mode inspect` shows correct counts for all tables
- [ ] **Phase 1**: All unit tests pass (`pytest -m unit`) — zero failures
- [ ] **Phase 2**: Full test suite passes (`pytest`) — zero failures
- [ ] Final test count (before → after) documented
- [ ] Completion Summary added to `README-seed-data.md` §10 SD-6 entry

---

## Completion Summary

After all Definition of Done items are complete, update `backend/README-seed-data.md` §10 SD-6 entry from "🔄 Active" to "✅ Complete" and add the Completion Summary subsection using this format:

```markdown
### SD-6 — Deep Seed Data: Line Items, New Scenarios & README Updates ✅ Complete (YYYY-MM-DD)

**Completed**: YYYY-MM-DD
**Mode**: Pilot Python Engineer
**Baseline**: X passed, Y failed
**Final**: X+N passed, Y failed (+N new tests if any)

#### What Was Accomplished

- Seeded `invoice_line` + `invoice_line_tax_component` for all 8 invoices; updated invoice totals to match line math
- Added `mobile_sync_owner_escalation` (1 open + 1 resolved) — closes W-12 coverage gap
- Added `loto_confirmation` (2 confirmed rows) on Panel Upgrade + Commercial Rewire jobs
- Added `change_order` + `change_order_line` (2 COs, 5 lines) on JOB-900001
- Created new `seed_scenario_notifications.py` — 5 `in_app_notification` rows for owner user
- Added `user_preference` + `user_setting_override` to `seed_test_tenant.py`
- Updated `README-seed-data.md` §4, §7, §8, §9, §10

#### Files Changed / Created

| File | Action |
|---|---|
| `backend/migrations/scripts/seed_scenario_quote_to_cash.py` | Updated — invoice_line + invoice_line_tax_component + change_order + change_order_line |
| `backend/migrations/scripts/seed_scenario_reporting.py` | Updated — invoice_line + invoice_line_tax_component + loto_confirmation |
| `backend/migrations/scripts/seed_scenario_mobile_sync.py` | Updated — mobile_sync_owner_escalation |
| `backend/migrations/scripts/seed_scenario_notifications.py` | Created — new Group D script |
| `backend/migrations/scripts/seed_test_tenant.py` | Updated — user_preference + user_setting_override |
| `backend/migrations/scripts/reset_dev_db.py` | Updated — registered notifications scenario |
| `backend/README-seed-data.md` | Updated — §4, §7, §8, §9, §10 |
```
