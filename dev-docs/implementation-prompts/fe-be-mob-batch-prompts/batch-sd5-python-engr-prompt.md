# Implementation Prompt: SD-5 — Group D Scenario Data Expansion

**Mode**: Pilot Python Engineer  
**Batch**: SD-5  
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §2 P1 — Full UI Seed Data Expansion  
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-sd5-design.md`  
**Estimated session**: 4–6 hours  
**Platform**: Backend only (`backend/migrations/scripts/`) — seed scripts only, no application code, no Alembic migrations  
**Frontend companion**: None — but these seed changes are required before the Full UI Regression testing pass

> ⚠️ **Session scope advisory**: This batch touches 7 seed scripts with significant changes. If context feels crowded during implementation, complete Task Groups 1–3 first (quote/job/invoice chain — the highest priority), commit, then continue with Groups 4–5 in a fresh session. Never leave a script half-updated.

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`dev-docs/architecture-design/pilot-python-engineer-methods.md`** — §16 (Standard Task Workflow), §5 (Model Design)
- **`backend/tests/README-adding-tests.md`** — full document; governs all test structure and seed data coexistence rules

Critical rules for this batch:

- **Rule 1**: Never guess column names, data types, or table names. Use `postgres-local` MCP to verify every column before writing SQL. If MCP returns unexpected results → **STOP and ask Tom**.
- **Rule 2**: This batch is **seed scripts only** — no Alembic migrations, no application code, no route files, no model files. All changes stay in `backend/migrations/scripts/`.
- **Rule 3**: The SD-2 refund model uses a **new negative-amount payment row** — NOT a `refunded_amount_cents` column (that column was added by an early migration and then intentionally dropped by migration `44b8d8f15789` on 2026-07-14). The correct implementation of D5 is: INSERT a new `payment` row with `amount_cents = -3200` and `status_id` pointing to `payment_status.code = 'refunded'`. No column check needed — `payment_status.refunded` was confirmed in the live DB during SD-2.
- **Rule 4**: `invoice.billing_mode` is `NOT NULL` — all invoice INSERTs must include `billing_mode = 'invoice'`.
- **Rule 5**: `invoice.reminder_count` is `NOT NULL` — all invoice INSERTs must include `reminder_count = 0`.
- **Rule 6**: `quote.expires_at` is the expiry column (NOT `valid_until`). Use `expires_at` for expired/sent quotes.
- **Rule 7**: `quote.site_id` is `NOT NULL` — all quotes require a valid site, even rejected/draft ones. Bob Davis gets a new site (see Task Group 1).
- **Rule 8**: `labor_rate_version` has a GiST exclusion constraint — never INSERT a new row overlapping an existing `(tenant_id, skill_level_code, valid_period)`. Only UPDATE existing rows.
- **Rule 9**: The `postgres-local` MCP is **read-only verification only**. Never INSERT, UPDATE, or DELETE via MCP.
- **Rule 10**: If ANY test fails during your work → fix it before declaring the batch done.

---

## Pre-Work: Establish Regression Baseline

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=no -q 2>&1 | tail -5
```

Record the exact count: **`X passed, Y failed`**.

---

## Pre-Work: Run MCP Verification Queries

Run **all** of these before writing any code:

> **MCP Usage Rule**: Read-only only. Never INSERT/UPDATE/DELETE via MCP.

```sql
-- 1. Current quote count by status
SELECT qs.code, COUNT(*) AS cnt
FROM quote q JOIN quote_status qs ON qs.id = q.status_id
WHERE q.tenant_id = '00000000-0000-0000-0000-000000000001'
GROUP BY qs.code ORDER BY qs.code;
-- Expected: draft=1, all others=0

-- 2. Current invoice count (expect 0 before re-run)
SELECT COUNT(*) FROM invoice WHERE tenant_id = '00000000-0000-0000-0000-000000000001';

-- 3. Current payment count (expect 0 before re-run)
SELECT COUNT(*) FROM payment WHERE tenant_id = '00000000-0000-0000-0000-000000000001';

-- 4. Verify quote columns (key ones: expires_at, submitted_at, approved_at, customer_accepted_at, customer_declined_at, quote_number, title, site_id)
SELECT column_name, data_type, is_nullable FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'quote'
AND column_name IN ('expires_at', 'submitted_at', 'approved_at', 'customer_accepted_at',
                    'customer_declined_at', 'quote_number', 'title', 'site_id', 'customer_id',
                    'discount_amount_cents', 'card_required')
ORDER BY column_name;

-- 5. Verify invoice NOT NULL columns
SELECT column_name, data_type, is_nullable FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'invoice'
AND column_name IN ('billing_mode', 'reminder_count', 'quote_id', 'job_id', 'balance_due_cents')
ORDER BY column_name;

-- 6. Verify payment_status.refunded exists (needed for D5)
SELECT code, name FROM payment_status WHERE code = 'refunded' AND tenant_id IS NULL;
-- Expected: 1 row (confirmed added by SD-2) — D5 uses this status_id for the refund row

-- 7. Current customer count
SELECT COUNT(*) FROM customer WHERE tenant_id = '00000000-0000-0000-0000-000000000001';
-- Expected: 9 (8 correct + 1 dispatch fallback)

-- 8. Current site count
SELECT COUNT(*) FROM site WHERE tenant_id = '00000000-0000-0000-0000-000000000001';
-- Expected: 3

-- 9. Current supplier count
SELECT COUNT(*) FROM supplier WHERE tenant_id = '00000000-0000-0000-0000-000000000001';
-- Expected: 1 (Wesco)

-- 10. mobile_sync_event schema — confirm conflict_severity column exists
SELECT column_name FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'mobile_sync_event'
AND column_name = 'conflict_severity';

-- 11. Confirm quote_status codes available
SELECT code FROM quote_status WHERE tenant_id IS NULL ORDER BY code;
-- Expected: accepted, approved, converted, draft, expired, pending, pending_approval, rejected, sent, void

-- 12. Confirm invoice_status codes available
SELECT code FROM invoice_status WHERE tenant_id IS NULL ORDER BY code;
-- Expected: draft, issued, partial, paid, void, writeoff
```

---

## Pre-Work: Read These Source Files

```
backend/migrations/scripts/seed_scenario_quote_to_cash.py   ← full source
backend/migrations/scripts/seed_scenario_reporting.py       ← full source
backend/migrations/scripts/seed_scenario_dispatch.py        ← full source
backend/migrations/scripts/seed_scenario_supplier_catalog.py ← full source
backend/migrations/scripts/seed_scenario_mobile_sync.py     ← full source
backend/migrations/scripts/seed_scenario_nec.py             ← full source
backend/migrations/scripts/seed_scenario_customer_comms.py  ← full source
```

---

## Background

SD-5 expands all 7 Group D scenario scripts from "thin E2E coverage" to "full UI-testable data density." The primary goals:
1. Every status tab in the Quotes list shows at least 1 quote
2. Every status tab in the Invoices list shows at least 1 invoice
3. The full quote→job→invoice→payment relational chain exists in seeded data
4. Dispatch board shows 2 technicians (not just 1)
5. Supplier catalog shows 3 suppliers
6. Mobile sync UI shows both success and partial-failure scenarios
7. NEC history shows 2 calc types

**No Alembic migrations. No application code changes. Seed scripts only.**

---

## Task Group 1 — seed_scenario_quote_to_cash.py: Full Status Coverage

**File**: `backend/migrations/scripts/seed_scenario_quote_to_cash.py`

This is the highest-priority and most complex task. The script currently seeds 5 customers, 3 sites, 5 pricebook items, and 1 draft quote. SD-5 expands this to 8 customers, 7 sites, 6 pricebook items, and 10 quotes covering all statuses.

### 1a — Add 3 New Customers (indices 5, 6, 7)

Add to the `CUSTOMERS` list:
```python
{
    "display_name": "Rachel Kim",
    "first_name": "Rachel",
    "last_name": "Kim",
    "company_name": None,
    "type": "person",
    "lifecycle": "active",
    "mobile_phone": "+14255551005",
    "email": "rachel.kim@example.com",
},
{
    "display_name": "Metro Properties LLC",
    "first_name": None,
    "last_name": None,
    "company_name": "Metro Properties LLC",
    "type": "company",
    "lifecycle": "active",
    "mobile_phone": "+12025551006",
    "email": "info@metro-properties.example.com",
},
{
    "display_name": "James Torres",
    "first_name": "James",
    "last_name": "Torres",
    "company_name": None,
    "type": "person",
    "lifecycle": "active",
    "mobile_phone": "+13055551007",
    "email": "james.torres@example.com",
},
```

### 1b — Add 4 New Sites (Bob Davis + 3 new customers)

Add to `CUSTOMER_SITES`:
```python
# Bob Davis (idx 3) — needed for Q-REJT-001 (quote.site_id NOT NULL)
{
    "customer_idx": 3,
    "site_name": "Davis Property",
    "line1": "42 Prospect Lane",
    "city": "Denver",
    "state": "CO",
    "postal_code": "80201",
    "country": "US",
},
# Rachel Kim (idx 5)
{
    "customer_idx": 5,
    "site_name": "Kim Residence",
    "line1": "321 Pine St",
    "city": "Seattle",
    "state": "WA",
    "postal_code": "98101",
    "country": "US",
},
# Metro Properties LLC (idx 6)
{
    "customer_idx": 6,
    "site_name": "Metro Office Park",
    "line1": "555 Business Ave",
    "city": "Dallas",
    "state": "TX",
    "postal_code": "75201",
    "country": "US",
},
# James Torres (idx 7)
{
    "customer_idx": 7,
    "site_name": "Torres Home",
    "line1": "888 Palm Dr",
    "city": "Miami",
    "state": "FL",
    "postal_code": "33101",
    "country": "US",
},
```

### 1c — Add 1 New Pricebook Item

Add to `PRICEBOOK_ITEMS`:
```python
{
    "sku": "WNUT-BAG-01",
    "name": "Wire Nuts (bag of 50)",
    "description": "Assorted wire nuts for electrical connections",
    "category": "material",
    "uom_code": "bag",
    "unit_price_cents": 500,
    "taxability_code": "taxable",
},
```

### 1d — Enrich Draft Quote to 8 Lines

After the existing 2 lines (positions 1 and 2), add lines 3–8 to the draft quote (Q-DRAFT-001 / QTC-001):

```python
# Line 3: labor — 200A Panel Upgrade
# Line 4: material — EMT Conduit × 50 ft @ 350¢/ft = 17500¢
# Line 5: misc — Residential Permit Fee × 1 = 25000¢
# Line 6: note — display text only, no price (qco_line_type code='note')
#   description="All electrical work performed per NEC 2023 standards."
#   unit_price_cents=0, subtotal_cents=0, total_cents=0
# Line 7: discount — unit_price_cents=-10000 (−$100 off)
#   description="New customer discount"
# Line 8: material — Wire Nuts (WNUT-BAG-01) × 50 = 500¢ × 50 = 25000¢
```

Idempotency: check by `quote_id + position`. Skip if position already exists.

### 1e — Add 9 New Quotes (All Non-Draft Statuses)

Add a `QUOTES` constant list and a new section in `mode_seed()` that:
1. Looks up `quote_status` IDs by code
2. For each quote definition, checks idempotency by `tenant_id + quote_number`
3. Inserts quote + 2–3 quote_lines + 1 quote_version

**Quote definitions**:

```python
ANCHOR_DATE = datetime(2026, 7, 1, tzinfo=UTC)  # same anchor as reporting script

QUOTES = [
    {
        "quote_number": "Q-PEND-APPR-001",
        "title": "Panel Upgrade — Pending Internal Approval",
        "status_code": "pending_approval",
        "customer_idx": 1,   # Mary Johnson
        "site_customer_idx": 1,  # Johnson Home
        "subtotal_cents": 190000,
        "tax_cents": 15200,
        "total_cents": 205200,
        "submitted_at_offset_days": -2,  # submitted 2 days before ANCHOR
        "expires_at_offset_days": 30,
        "line_items": [
            ("PANEL-200A-01", "labor", 1, 180000),
            ("BRKR-15A-01", "material", 10, 18000),
            ("PERMIT-RES-01", "misc", 1, 25000),
        ],
    },
    {
        "quote_number": "Q-PEND-001",
        "title": "Commercial Panel Assessment — Pending Customer Review",
        "status_code": "pending",
        "customer_idx": 2,   # Apex Commercial LLC
        "site_customer_idx": 2,  # Apex HQ
        "subtotal_cents": 320000,
        "tax_cents": 25600,
        "total_cents": 345600,
        "submitted_at_offset_days": -1,
        "expires_at_offset_days": 14,
        "line_items": [
            ("PANEL-200A-01", "labor", 1, 180000),
            ("COND-EMT-01", "material", 100, 35000),
            ("PERMIT-RES-01", "misc", 1, 25000),
        ],
    },
    {
        "quote_number": "Q-APPR-001",
        "title": "Outlet Installation — Internally Approved",
        "status_code": "approved",
        "customer_idx": 5,   # Rachel Kim
        "site_customer_idx": 5,  # Kim Residence
        "subtotal_cents": 45000,
        "tax_cents": 3600,
        "total_cents": 48600,
        "approved_at_offset_days": -1,
        "expires_at_offset_days": 21,
        "line_items": [
            ("OUTLET-STD-01", "labor", 3, 45000),
        ],
    },
    {
        "quote_number": "Q-SENT-001",
        "title": "Service Panel Inspection — Sent to Customer",
        "status_code": "sent",
        "customer_idx": 6,   # Metro Properties LLC
        "site_customer_idx": 6,  # Metro Office Park
        "subtotal_cents": 85000,
        "tax_cents": 6800,
        "total_cents": 91800,
        "expires_at_offset_days": 14,  # expires 14d from ANCHOR (still valid)
        "line_items": [
            ("PANEL-200A-01", "labor", 1, 60000),
            ("BRKR-15A-01", "material", 5, 9000),
        ],
    },
    {
        "quote_number": "Q-ACPT-001",
        "title": "Wiring Upgrade — Customer Accepted",
        "status_code": "accepted",
        "customer_idx": 7,   # James Torres
        "site_customer_idx": 7,  # Torres Home
        "subtotal_cents": 230000,
        "tax_cents": 18400,
        "total_cents": 248400,
        "expires_at_offset_days": 30,
        "customer_accepted_at_offset_days": -3,
        "customer_acceptance_comment": "Looks good, please proceed.",
        "customer_email_at_action": "james.torres@example.com",
        "line_items": [
            ("PANEL-200A-01", "labor", 1, 180000),
            ("COND-EMT-01", "material", 50, 17500),
            ("PERMIT-RES-01", "misc", 1, 25000),
        ],
    },
    {
        "quote_number": "Q-CONV-001",
        "title": "Electrical Inspection — Converted to Job",
        "status_code": "converted",
        "customer_idx": 0,   # John Smith
        "site_customer_idx": 0,  # Smith Residence
        "subtotal_cents": 95000,
        "tax_cents": 7600,
        "total_cents": 102600,
        "expires_at_offset_days": 30,
        "create_job_and_invoice": True,  # triggers chain creation
        "line_items": [
            ("OUTLET-STD-01", "labor", 3, 45000),
            ("BRKR-15A-01", "material", 5, 9000),
            ("PERMIT-RES-01", "misc", 1, 25000),
        ],
    },
    {
        "quote_number": "Q-REJT-001",
        "title": "Solar Panel Wiring Estimate — Rejected",
        "status_code": "rejected",
        "customer_idx": 3,   # Bob Davis (prospect)
        "site_customer_idx": 3,  # Davis Property
        "subtotal_cents": 450000,
        "tax_cents": 36000,
        "total_cents": 486000,
        "expires_at_offset_days": 14,
        "customer_declined_at_offset_days": -5,
        "customer_decline_comment": "Too expensive for now.",
        "customer_decline_reason": "price",
        "line_items": [
            ("PANEL-200A-01", "labor", 2, 360000),
            ("COND-EMT-01", "material", 100, 35000),
        ],
    },
    {
        "quote_number": "Q-EXPR-001",
        "title": "Generator Install Estimate — Expired",
        "status_code": "expired",
        "customer_idx": 1,   # Mary Johnson
        "site_customer_idx": 1,  # Johnson Home
        "subtotal_cents": 180000,
        "tax_cents": 14400,
        "total_cents": 194400,
        "expires_at_offset_days": -30,  # expired 30d before ANCHOR (past date)
        "line_items": [
            ("PANEL-200A-01", "labor", 1, 180000),
        ],
    },
    {
        "quote_number": "Q-VOID-001",
        "title": "EV Charger Install — Voided",
        "status_code": "void",
        "customer_idx": 5,   # Rachel Kim
        "site_customer_idx": 5,  # Kim Residence
        "subtotal_cents": 65000,
        "tax_cents": 5200,
        "total_cents": 70200,
        "expires_at_offset_days": 14,
        "line_items": [
            ("OUTLET-STD-01", "labor", 2, 30000),
            ("COND-EMT-01", "material", 50, 17500),
        ],
    },
]
```

**Important date logic**: Use `ANCHOR_DATE + timedelta(days=offset)` for all quote timestamps. `expires_at_offset_days` is relative to ANCHOR_DATE. Negative offsets = past dates (expired). Positive = future dates.

### 1f — Q-CONV-001 → Job → Invoice → Payment Chain

When `create_job_and_invoice=True`, after creating the quote, create the full chain. All 3 steps use idempotency checks by unique number:

**Step 1 — Job** (idempotency: `job_number = 'QTC-CONV-001'`):
```sql
INSERT INTO public.job
(id, tenant_id, customer_id, site_id, status_id, job_number, quote_id,
 scheduled_start_at, scheduled_end_at,
 actual_labor_cost_cents, actual_material_cost_cents, actual_profit_cents,
 is_active, version, created_at, updated_at)
VALUES (gen_random_uuid(), :tid, :cid, :sid, :completed_status_id, 'QTC-CONV-001', :quote_id,
        :anchor_minus_7d_9am, :anchor_minus_7d_5pm,
        48000, 22000, 25000,
        true, 1, NOW(), NOW())
```
Where `anchor_minus_7d_9am = ANCHOR_DATE - timedelta(days=7) + timedelta(hours=9)`.

**Step 2 — Invoice** (idempotency: `invoice_number = 'INV-QTC-001'`):
```sql
INSERT INTO public.invoice
(id, tenant_id, invoice_number, quote_id, job_id, customer_id, site_id, status_id,
 subtotal_cents, tax_cents, total_cents, balance_due_cents,
 currency, billing_mode, is_active, issued_at, due_at, reminder_count,
 created_at, updated_at)
VALUES (gen_random_uuid(), :tid, 'INV-QTC-001', :quote_id, :job_id, :cid, :sid, :paid_status_id,
        95000, 7600, 102600, 0,
        'USD', 'invoice', true, :anchor_minus_5d, :anchor_plus_25d, 0,
        NOW(), NOW())
```

**Step 3 — Payment** (idempotency: check `invoice_id = :inv_id AND amount_cents = 102600`):
- Requires `seed_payment_method` row (same `psp_provider='seed'` pattern as reporting script — look it up or create)
- `status_id` = `succeeded` from `payment_status`
- `amount_cents = 102600`, `paid_via = 'check'`, `paid_at = ANCHOR_DATE - timedelta(days=2)`

**Verify after Task Group 1**:
```bash
python migrations/scripts/seed_scenario_quote_to_cash.py --mode inspect
# Should show: 8 customers, 7 sites, 6 pricebook items
# Should show: 10 quotes (1 per status code)
# Should show: job QTC-CONV-001 + invoice INV-QTC-001 + 1 payment
```

Run unit tests after this group:
```bash
python -m pytest -m unit --tb=short -q 2>&1 | tail -5
```

---

## Task Group 2 — seed_scenario_reporting.py: Invoice Fix + New Statuses

**File**: `backend/migrations/scripts/seed_scenario_reporting.py`

### 2a — Re-run to Restore Invoices A–D (No Code Change Needed)

The existing invoice/payment code (added B19) is already in the script. **Simply re-running** the script will create the 4 missing invoices and 2 payments idempotently. Jobs A–D already exist — the script will skip them and only create the invoices.

```bash
python migrations/scripts/seed_scenario_reporting.py
python migrations/scripts/seed_scenario_reporting.py --mode inspect
# Should now show: 4 invoices (A:paid, B:paid, C:issued, D:draft) + 2 payments
```

### 2b — Add 3 New Jobs E/F/G with Partial/Void/Writeoff Invoices

Add to `REPORTING_JOBS`:

```python
# Job E — partial payment invoice
{
    "title": "HVAC Coordination — Completed Job E",
    "days_ago": 20,
    "start_hour": 10,
    "end_hour": 15,
    "customer_idx": 0,  # John Smith
    "time_entries": [
        {"skill": "journeyman", "start_offset_h": 0, "duration_h": 3.0, "notes": "Coordination with HVAC contractor"},
    ],
    "expenses": [
        {"category": "materials", "description": "Electrical supplies", "cost_cents": 8500, "markup_pct": 20.0},
    ],
},
# Job F — voided invoice
{
    "title": "Generator Hookup — Completed Job F",
    "days_ago": 35,
    "start_hour": 8,
    "end_hour": 14,
    "customer_idx": 1,  # Mary Johnson
    "time_entries": [
        {"skill": "master", "start_offset_h": 0, "duration_h": 4.0, "notes": "Generator transfer switch installation"},
    ],
    "expenses": [
        {"category": "materials", "description": "Transfer switch hardware", "cost_cents": 32000, "markup_pct": 20.0},
    ],
},
# Job G — written off invoice
{
    "title": "Commercial Rewire — Completed Job G",
    "days_ago": 75,
    "start_hour": 7,
    "end_hour": 16,
    "customer_idx": 2,  # Apex Commercial LLC
    "time_entries": [
        {"skill": "master", "start_offset_h": 0, "duration_h": 5.0, "notes": "Full commercial rewire"},
        {"skill": "journeyman", "start_offset_h": 3, "duration_h": 6.0, "notes": "Panel sub-feed installation"},
    ],
    "expenses": [
        {"category": "materials", "description": "Commercial wiring materials", "cost_cents": 65000, "markup_pct": 20.0},
        {"category": "permits", "description": "Commercial electrical permit", "cost_cents": 45000, "markup_pct": 0.0},
    ],
},
```

Add invoice specs for E/F/G to the `invoice_specs` list (after index 3):

```python
# Job E — partial (index 4)
{
    "letter": "e",
    "subtotal_cents": 41700,
    "tax_cents": 3336,
    "total_cents": 45036,
    "balance_due_cents": 25036,
    "issued_at_offset": -18,
    "due_at_offset": -4,        # overdue
    "status_id": inv_status_map.get("partial"),
    "create_payment": True,
    "payment_amount_override": 20000,  # partial payment only
},
# Job F — void (index 5)
{
    "letter": "f",
    "subtotal_cents": 68400,
    "tax_cents": 5472,
    "total_cents": 73872,
    "balance_due_cents": 73872,
    "issued_at_offset": -33,
    "due_at_offset": -19,
    "status_id": inv_status_map.get("void"),
    "create_payment": False,
},
# Job G — writeoff (index 6)
{
    "letter": "g",
    "subtotal_cents": 202000,
    "tax_cents": 16160,
    "total_cents": 218160,
    "balance_due_cents": 218160,
    "issued_at_offset": -72,
    "due_at_offset": -42,
    "status_id": inv_status_map.get("writeoff"),
    "create_payment": False,
},
```

For the partial invoice (E), when `payment_amount_override` is set, use that value instead of `spec["total_cents"]` for the payment amount.

Also look up `partial`, `void`, `writeoff` status IDs in the existing `inv_status_map` lookup.

### 2c — Refunded Payment (D5) — ALWAYS IMPLEMENT

**Architecture note**: The SD-2 design established that refunds use a **new negative-amount payment row** — NOT a `refunded_amount_cents` column. Migration `44b8d8f15789` (2026-07-14) intentionally dropped that column. The `payment_status` table already has a `refunded` code (confirmed in live DB).

1. Find Invoice B's ID: `SELECT id FROM invoice WHERE tenant_id=:tid AND invoice_number='INV-SEED-B'`
2. Find the seed payment_method: `SELECT id FROM payment_method WHERE tenant_id=:tid AND psp_provider='seed' LIMIT 1`
3. Look up the `refunded` status ID: `SELECT id FROM payment_status WHERE code='refunded' AND tenant_id IS NULL LIMIT 1`
4. Insert the refund row (negative amount = refund):
```sql
INSERT INTO public.payment
(id, tenant_id, invoice_id, payment_method_id, status_id,
 amount_cents, paid_via, paid_at, is_active, created_at, updated_at)
VALUES (gen_random_uuid(), :tid, :inv_b_id, :pm_id, :refunded_status_id,
        -3200, 'check', :anchor_minus_27d, true, NOW(), NOW())
-- amount_cents = -3200 (negative = refund per SD-2 design)
-- The original succeeded payment row is unchanged
```

Idempotency: check `WHERE invoice_id = :inv_b_id AND amount_cents = -3200 LIMIT 1`.

---

## Task Group 3 — seed_scenario_dispatch.py: Multi-Tech + Cancelled Job

**File**: `backend/migrations/scripts/seed_scenario_dispatch.py`

### 3a — Add OWNER_USER_ID constant

```python
OWNER_USER_ID = UUID("00000000-0000-0000-0000-000000000002")
```

### 3b — Add 6th Job (Cancelled)

Add to `JOBS` list:
```python
{
    "title": "Cancelled - Customer Backed Out",
    "status_code": "cancelled",
    "offset_days": None,
    "start_hour": None,
    "end_hour": None,
    "assign_tech": False,
    "job_number_suffix": "006",  # → DISP-006
},
```

Update the job INSERT to use `job_number_suffix` if present (otherwise use the sequential index).

### 3c — Secondary Tech Assignments for Jobs 1 and 2

After the existing primary tech assignment loop, add:

```python
# Owner as secondary tech on Jobs 1 and 2 (indices 0 and 1)
for job_idx in [0, 1]:
    job_id, job_def = job_ids[job_idx]
    if not job_id:
        continue
    existing_secondary = db.execute(text("""
        SELECT id FROM public.job_tech_assignment
        WHERE tenant_id=:tid AND job_id=:jid AND user_id=:uid
    """), {"tid": tid, "jid": job_id, "uid": str(OWNER_USER_ID)}).first()
    
    if not existing_secondary:
        db.execute(text("""
            INSERT INTO public.job_tech_assignment
            (id, tenant_id, job_id, user_id, assigned_by_user_id, role, ordinal,
             assigned_at, is_active, version, created_at, updated_at)
            VALUES (gen_random_uuid(), :tid, :jid, :uid, :assigned_by, 'secondary', 2,
                    NOW(), true, 1, NOW(), NOW())
            ON CONFLICT DO NOTHING
        """), {"tid": tid, "jid": job_id, "uid": str(OWNER_USER_ID), "assigned_by": str(OWNER_USER_ID)})
        print(f"  ✅ [job_tech_assignment] Owner assigned as secondary to job {job_id}")
```

### 3d — Owner Sick Day Tech Availability

After the PTO block:
```python
# Owner sick day (2 weeks after next Friday)
sick_start_utc = next_friday + timedelta(weeks=2)
sick_end_utc = sick_start_utc.replace(hour=17)

existing_sick = db.execute(text("""
    SELECT id FROM public.tech_availability
    WHERE tenant_id=:tid AND user_id=:uid AND availability_type='sick' AND starts_at=:starts
"""), {"tid": tid, "uid": str(OWNER_USER_ID), "starts": sick_start_utc}).first()

if not existing_sick:
    db.execute(text("""
        INSERT INTO public.tech_availability
        (id, tenant_id, user_id, availability_type, starts_at, ends_at, is_active, notes, created_at, updated_at)
        VALUES (gen_random_uuid(), :tid, :uid, 'sick', :starts, :ends, true, 'Owner sick day', NOW(), NOW())
        ON CONFLICT DO NOTHING
    """), {"tid": tid, "uid": str(OWNER_USER_ID), "starts": sick_start_utc, "ends": sick_end_utc})
    print(f"  ✅ [tech_availability] Owner sick day: {sick_start_utc.date()}")
```

---

## Task Group 4 — seed_scenario_supplier_catalog.py + Others

### 4a — Supplier Catalog: Add 2 Suppliers (D7)

**File**: `backend/migrations/scripts/seed_scenario_supplier_catalog.py`

Add:
```python
SUPPLIER_2_NAME = "Graybar Electric"
SUPPLIER_2_ITEMS = [
    ("WIRE-14AWG-THHN", "14 AWG THHN Wire", "wire_cable", "foot", 0.65, True),
    ("CONDUIT-EMT-0.75IN", '3/4" EMT Conduit', "conduit_raceway", "foot", 2.25, True),
    ("BREAKER-CH115", "Eaton CH115 15A Breaker", "dist_equip", "each", 10.50, True),
    ("OUTLET-GFCI-TR", "GFCI Outlet Tamper-Resistant", "wiring_devices", "each", 8.75, True),
    ("COUPLING-EMT-0.75IN", '3/4" EMT Coupling', "fittings", "each", 1.25, True),
]

SUPPLIER_3_NAME = "Platt Electric Supply"
SUPPLIER_3_ITEMS = [
    ("LIGHT-LED-2X4-PANEL", "LED Panel Light 2x4", "lighting", "each", 45.00, True),
    ("FAST-WIRE-STAPLES", "Wire Staples (box of 100)", "fasteners", "box", 12.50, True),
    ("TAPE-ELEC-ROLL", "Electrical Tape (roll)", "wiring_devices", "roll", 3.25, True),
    ("INCAND-60W-BULB", "60W Incandescent Bulb (discontinued)", "lighting", "each", 1.50, False),  # inactive
]
```

Each item tuple is: `(sku, name, category_code, uom_code, unit_price, is_active)`.

Update `mode_seed()` to loop over a list of `(supplier_name, items)` pairs:
```python
ALL_SUPPLIERS = [
    (SUPPLIER_NAME, SUPPLIER_ITEMS),       # Wesco (existing)
    (SUPPLIER_2_NAME, SUPPLIER_2_ITEMS),   # Graybar (new)
    (SUPPLIER_3_NAME, SUPPLIER_3_ITEMS),   # Platt (new)
]
```

For each supplier, use the same idempotent pattern as the existing Wesco logic. For items, pass `is_active` to the INSERT (add `is_active` to the existing INSERT).

### 4b — Mobile Sync: Partial Failure Session (D8)

**File**: `backend/migrations/scripts/seed_scenario_mobile_sync.py`

Add at the top:
```python
SEED_DEVICE_ID_2 = UUID("00000000-0000-0000-0002-000000000001")
```

In `seed()`, after the success session block, add a 2nd session (partial failure) and 2 events (conflict + failed). See design doc §H.1 for the exact INSERT SQL.

**Also add `parse_args()` and update `__main__`** (D11):
```python
import argparse

def parse_args():
    parser = argparse.ArgumentParser(description="seed_scenario_mobile_sync.py — Group D mobile sync seeder")
    parser.add_argument("--mode", choices=["seed", "inspect", "show"], default="seed")
    parser.add_argument("--reset", action="store_true")
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    if args.reset:
        mode_reset()
    elif args.mode == "seed":
        seed()
    elif args.mode == "inspect":
        mode_inspect()
    elif args.mode == "show":
        print("=== seed_scenario_mobile_sync: show mode ===")
        print(f"  Session 1: device={SEED_DEVICE_ID}  triggered_by=silent_push  outcome=success")
        print(f"  Session 2: device={SEED_DEVICE_ID_2}  triggered_by=user_initiated  outcome=partial")
        print(f"  Events: create_time_entry, create_expense (succeeded) + update_job_status (conflict) + upload_photo (failed)")
```

### 4c — NEC: Add box_fill Row + `parse_args()` (D9, D11)

**File**: `backend/migrations/scripts/seed_scenario_nec.py`

Add a 3rd entry to `rows` in `_seed_impl()`:
```python
{
    "calc_type": "box_fill",
    "nec_guide_version": "2023",
    "inputs_json": '{"box_size_cubic_inches": 18, "conductors": [{"awg": "12", "count": 4}, {"awg": "14", "count": 2}], "devices": 1, "clamps": 1}',
    "result_json": '{"calc_type": "box_fill", "result_value": 16.25, "is_compliant": true, "nec_article": "NEC 314.16(B)", "nec_citation": "NEC 314.16(B) — Box fill calc. Available: 18 cu.in, Required: 16.25 cu.in", "available_cubic_inches": 18, "required_cubic_inches": 16.25}',
    "is_offline_calc": False,
    "client_capture_at": None,
},
```

Update the idempotency check for box_fill (different pattern than voltage_drop — no amperage):
```python
# For box_fill: check by calc_type + is_offline_calc + inputs_prefix matching box_size
"inputs_prefix": f'%"box_size_cubic_inches"%',
```

Add `parse_args()` (same pattern as mobile_sync above).

### 4d — Customer Comms: Close Sunrise Thread (D10)

**File**: `backend/migrations/scripts/seed_scenario_customer_comms.py`

At the end of `mode_seed()`, after the thread+message loop:
```python
# Update Sunrise Electric LLC thread to closed
db.execute(text("""
    UPDATE public.customer_communication_thread
    SET status = 'closed', updated_at = NOW()
    WHERE tenant_id = :tid
    AND customer_id = (
        SELECT id FROM public.customer
        WHERE tenant_id = :tid AND display_name = 'Sunrise Electric LLC'
        LIMIT 1
    )
    AND status != 'closed'
"""), {"tid": tid})
print("  ✅ [customer_communication_thread] Sunrise Electric LLC thread → status=closed")
```

---

## Task Group 5 — README-seed-data.md Update

Update `backend/README-seed-data.md` §4 Group D to reflect:

- **quote-to-cash scenario**: 8 customers, 7 sites, 6 pricebook items, 10 quotes (all statuses), 1 job (QTC-CONV-001), 1 invoice (INV-QTC-001), 1 payment
- **reporting scenario**: 7 jobs (A–G), 11 time entries, 9 expenses, 7 invoices (all statuses), 4 payments (including partial payment)
- **dispatch scenario**: 6 jobs (including cancelled), 5 tech assignments (3 primary + 2 secondary owner), 2 tech_availability blocks
- **supplier_catalog scenario**: 3 suppliers (Wesco + Graybar + Platt), 13 items, 13 prices
- **mobile_sync scenario**: 2 sessions (success + partial), 4 events (2 succeeded + 1 conflict + 1 failed)
- **nec scenario**: 3 calc log rows (2 voltage_drop + 1 box_fill)
- **customer_comms scenario**: unchanged (3 customers, 3 threads — Sunrise now closed)

---

## Final Verification

### Phase 1 — Unit Tests (run after each task group)

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=short -q 2>&1 | tail -10
```

### Full Seed Verification (run after all task groups)

```bash
python migrations/scripts/seed_scenario_quote_to_cash.py --mode inspect
python migrations/scripts/seed_scenario_reporting.py --mode inspect
python migrations/scripts/seed_scenario_dispatch.py --mode inspect
python migrations/scripts/seed_scenario_supplier_catalog.py --mode inspect
python migrations/scripts/seed_scenario_mobile_sync.py --mode inspect
python migrations/scripts/seed_scenario_nec.py --mode inspect
python migrations/scripts/seed_scenario_customer_comms.py --mode inspect
```

**Expected key outputs**:
- `[quote]` 10 rows (1 per status code)
- `[invoice]` 8 rows (4 restored + 1 qtc + 3 new)
- `[payment]` 4+ rows
- `[supplier]` 3 rows
- `[mobile_sync_session]` 2 rows
- `[nec_calculation_log]` 3 rows

### Phase 2 — Full Test Suite

```bash
python -m pytest --tb=short -q 2>&1 | tail -10
echo "=== SD-5 FINAL VERIFICATION COMPLETE ==="
```

---

## Test Requirements

This batch modifies **only seed scripts** — no new application code is added. No new test files required. All verification is via `--mode inspect` output.

**Watch for tests that may break due to seed data changes**:
- Tests in `tests/domains/sales_quoting/` that count quotes by status
- Tests in `tests/domains/invoicing_billing/` that assert invoice states
- Any test using `second_tenant` or `tenant_a` will be unaffected (only `test_tenant` changes)

---

## Definition of Done

- [ ] Pre-modification regression baseline captured using `pytest -m unit`
- [ ] Zero pre-existing unit failures confirmed (or confirmed with Tom)
- [ ] All 12 MCP pre-work queries run — results match expected state
- [ ] All mandatory source files read before writing any code
- [ ] **Task Group 1**: qtc script — 3 customers, 4 sites, 1 pricebook item, 9 quotes, Q-CONV-001 chain (job+invoice+payment)
- [ ] **Task Group 1**: Draft quote enriched to 8 lines (all qco_line_type codes represented)
- [ ] **Task Group 2a**: Re-run reporting script — 4 invoices + 2 payments restored
- [ ] **Task Group 2b**: Jobs E/F/G + invoices (partial, void, writeoff) added
- [ ] **Task Group 2c**: Refunded payment row added for Invoice B — negative `amount_cents = -3200`, `status = refunded` (new row per SD-2 negative-amount refund model)
- [ ] **Task Group 3a**: Cancelled DISP-006 job added
- [ ] **Task Group 3b**: Owner assigned as secondary tech to DISP-001 and DISP-002
- [ ] **Task Group 3c**: Owner sick day tech_availability block added
- [ ] **Task Group 4a**: Graybar + Platt suppliers added (13 items total, 1 inactive item)
- [ ] **Task Group 4b**: Mobile sync partial-failure session + conflict/failed events added
- [ ] **Task Group 4b**: `seed_scenario_mobile_sync.py` has standard `parse_args()` + `--mode`
- [ ] **Task Group 4c**: NEC box_fill calc row added
- [ ] **Task Group 4c**: `seed_scenario_nec.py` has standard `parse_args()` + `--mode`
- [ ] **Task Group 4d**: Sunrise Electric LLC thread status updated to `closed`
- [ ] **Task Group 5**: `backend/README-seed-data.md` §4 Group D updated
- [ ] All `--mode inspect` outputs match expected counts above
- [ ] **Phase 1**: All unit tests pass (`pytest -m unit`) — zero failures including pre-existing
- [ ] **Phase 2**: Full test suite passes (`pytest`) — zero failures
- [ ] Final test count documented
- [ ] Completion Summary added to `pilot-launch-plan.md` Appendix B
- [ ] D5 refunded payment row confirmed in DB (`SELECT amount_cents FROM payment WHERE amount_cents = -3200 AND tenant_id = :tid`)

---

## Completion Summary

After all Definition of Done items are complete:

1. Add a **Completion Summary** to `dev-docs/analysis/pilot-launch-plan.md` Appendix B.
2. Note in the summary whether D5 (refunded payment) was implemented or skipped.

```markdown
### SD-5 — Group D Scenario Data Expansion: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot Python Engineer
**Baseline**: X passed, Y failed
**Final**: X+N passed, Y failed (+N new tests)

#### What Was Accomplished

- Expanded quote_to_cash: 8 customers, 7 sites, 10 quotes (all statuses), Q-CONV-001 chain
- Restored invoices A–D (re-run reporting script); added jobs E/F/G + invoices (partial/void/writeoff)
- D5: Added refunded payment row for Invoice B — `amount_cents = -3200`, `status = refunded` (SD-2 negative-amount refund model; `payment.refunded_amount_cents` column was intentionally dropped by migration 44b8d8f15789)
- Dispatch: cancelled DISP-006, owner as secondary tech, sick day availability
- Supplier catalog: Graybar + Platt (13 total items, 1 inactive)
- Mobile sync: partial-failure session + conflict/failed events; parse_args() added
- NEC: box_fill calc row added; parse_args() added
- Customer comms: Sunrise Electric thread → closed
- README-seed-data.md updated

#### Files Changed

| File | Action |
|---|---|
| `backend/migrations/scripts/seed_scenario_quote_to_cash.py` | Updated |
| `backend/migrations/scripts/seed_scenario_reporting.py` | Updated |
| `backend/migrations/scripts/seed_scenario_dispatch.py` | Updated |
| `backend/migrations/scripts/seed_scenario_supplier_catalog.py` | Updated |
| `backend/migrations/scripts/seed_scenario_mobile_sync.py` | Updated |
| `backend/migrations/scripts/seed_scenario_nec.py` | Updated |
| `backend/migrations/scripts/seed_scenario_customer_comms.py` | Updated |
| `backend/README-seed-data.md` | Updated |
```

---

## After This Batch — Next Step

After SD-5 is complete, run the full reseed sequence:

```bash
cd <repo>/backend && source .venv/bin/activate

python migrations/scripts/seed_platform.py
python migrations/scripts/seed_test_tenant.py
python migrations/scripts/seed_scenario_quote_to_cash.py
python migrations/scripts/seed_scenario_dispatch.py
python migrations/scripts/seed_scenario_customer_comms.py
python migrations/scripts/seed_scenario_reporting.py
python migrations/scripts/seed_scenario_supplier_catalog.py
python migrations/scripts/seed_scenario_nec.py
python migrations/scripts/seed_scenario_mobile_sync.py
```

Then Tom proceeds with the **Web UI Full Regression** pass — all status tabs, list views, and detail views will have realistic data.
