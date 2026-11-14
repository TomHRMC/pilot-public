# Batch SD-5 Design — Group D Scenario Data Expansion

**Version**: 1.0  
**Date**: 2026-07-15  
**Author**: Pilot Architect  
**Status**: READY FOR IMPLEMENTATION  
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §2 P1 — Full UI Seed Data Expansion  
**Decisions tracker**: `dev-docs/seed-data/sd5-decisions-tracker.md`

---

## Table of Contents

- [A. Input Read Summary](#a-input-read-summary)
- [B. Migration Plan](#b-migration-plan)
- [C. Execution Order](#c-execution-order)
- [D. seed\_scenario\_quote\_to\_cash.py Changes (D1–D3)](#d-seed_scenario_quote_to_cashpy-changes-d1d3)
- [E. seed\_scenario\_reporting.py Changes (D4–D5)](#e-seed_scenario_reportingpy-changes-d4d5)
- [F. seed\_scenario\_dispatch.py Changes (D6)](#f-seed_scenario_dispatchpy-changes-d6)
- [G. seed\_scenario\_supplier\_catalog.py Changes (D7)](#g-seed_scenario_supplier_catalogpy-changes-d7)
- [H. seed\_scenario\_mobile\_sync.py Changes (D8, D11)](#h-seed_scenario_mobile_syncpy-changes-d8-d11)
- [I. seed\_scenario\_nec.py Changes (D9, D11)](#i-seed_scenario_necpy-changes-d9-d11)
- [J. seed\_scenario\_customer\_comms.py Changes (D10)](#j-seed_scenario_customer_commspy-changes-d10)
- [K. Pattern Reuse Decisions](#k-pattern-reuse-decisions)
- [L. Open Questions Resolved](#l-open-questions-resolved)
- [M. Deferred Items](#m-deferred-items)

---

## A. Input Read Summary

All inputs read and verified via MCP before this design was written (2026-07-15):

| Input | Key Finding |
|---|---|
| All 7 Group D seed scripts | Full source read. See decisions tracker for per-script gap analysis. |
| Live DB — `customer` | 9 rows (8 expected — 1 dispatch fallback). Leave as-is. |
| Live DB — `job` | 13 rows (9 expected — 4 extra from prior testing). Leave as-is. |
| Live DB — `invoice` | **0 rows** — reporting script ran before B19 added invoice code. Fix: re-run script. |
| Live DB — `payment` | **0 rows** — same root cause as invoices. |
| Live DB — `quote` | 1 row (draft). ✅ |
| Live DB — `supplier` | 1 row (Wesco). ✅ |
| `quote` schema | Full column list confirmed. Key columns: `expires_at`, `submitted_at`, `approved_at`, `customer_accepted_at`, `customer_declined_at`, `discount_amount_cents`, `title`. No `valid_until` column — use `expires_at`. |
| `invoice` schema | Full column list confirmed. Key NOT NULL columns: `billing_mode`, `reminder_count`. Must include in all INSERTs. |
| `payment` schema | `refunded_amount_cents` does **NOT** exist in live DB — SD-BE-1 migration may not have run locally. Python Engineer must verify before implementing D5. |
| `tech_availability` schema | `availability_type` is free-form `text`. Valid values: `pto` (confirmed seeded). `sick` is safe to add. |
| `quote_status` codes | 10 codes: draft, pending_approval, pending, approved, sent, accepted, converted, rejected, expired, void |
| `invoice_status` codes | 6 codes: draft, issued, partial, paid, void, writeoff |
| FK relationships | `job.quote_id UUID NULL` → `quote`; `invoice.job_id UUID NULL` → `job`; `invoice.quote_id UUID NULL` → `quote` |

---

## B. Migration Plan

**No Alembic migrations required.** All changes are to Python seed scripts only. All columns being used already exist in the live DB (except `payment.refunded_amount_cents` — see §L).

### B.1 Pre-Implementation DB State (MCP-verified 2026-07-15)

```sql
-- Quote status coverage (current — only 1 draft)
SELECT qs.code, COUNT(*) FROM quote q JOIN quote_status qs ON qs.id = q.status_id
WHERE q.tenant_id = '00000000-0000-0000-0000-000000000001'
GROUP BY qs.code;
-- Expected: draft=1, all others=0

-- Invoice current state (expect 0)
SELECT COUNT(*) FROM invoice WHERE tenant_id = '00000000-0000-0000-0000-000000000001';
-- Expected: 0

-- Payment current state (expect 0)
SELECT COUNT(*) FROM payment WHERE tenant_id = '00000000-0000-0000-0000-000000000001';
-- Expected: 0

-- Supplier count (expect 1)
SELECT COUNT(*) FROM supplier WHERE tenant_id = '00000000-0000-0000-0000-000000000001';
-- Expected: 1

-- payment.refunded_amount_cents column exists?
SELECT column_name FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'payment'
AND column_name = 'refunded_amount_cents';
-- If 0 rows: SD-BE-1 migration not applied → cannot implement D5 until migration runs
```

---

## C. Execution Order

Scripts are independent of each other (no cross-script FK dependencies), but within each script, ordering matters:

| Step | Script | Change | Decision |
|---|---|---|---|
| 1 | `seed_scenario_quote_to_cash.py` | Add 3 customers + 3 sites | D2 |
| 2 | `seed_scenario_quote_to_cash.py` | Add 9 new quotes (all non-draft statuses) | D1 |
| 3 | `seed_scenario_quote_to_cash.py` | Enrich existing draft quote with 8 lines | D1 |
| 4 | `seed_scenario_quote_to_cash.py` | Add converted quote → job → invoice → payment chain | D3 |
| 5 | `seed_scenario_reporting.py` | Re-run to restore invoices A–D + payments (idempotent) | D4 |
| 6 | `seed_scenario_reporting.py` | Add 3 new jobs E/F/G + invoices (partial, void, writeoff) | D4 |
| 7 | `seed_scenario_reporting.py` | Add refunded payment (if `refunded_amount_cents` column exists) | D5 |
| 8 | `seed_scenario_dispatch.py` | Add 2nd tech (owner) to 2 jobs + 1 cancelled job + sick availability | D6 |
| 9 | `seed_scenario_supplier_catalog.py` | Add 2 more suppliers (Graybar, Platt) + 8 items + 1 inactive | D7 |
| 10 | `seed_scenario_mobile_sync.py` | Add partial-failure session + conflict/failed events | D8 |
| 11 | `seed_scenario_mobile_sync.py` | Add `parse_args()` + `--mode` support | D11 |
| 12 | `seed_scenario_nec.py` | Add box_fill calc log row | D9 |
| 13 | `seed_scenario_nec.py` | Add `parse_args()` + `--mode` support | D11 |
| 14 | `seed_scenario_customer_comms.py` | Update Sunrise Electric thread to `status=closed` | D10 |
| 15 | `backend/README-seed-data.md` | Update §4 Group D tables to reflect all new rows | Documentation |

---

## D. seed_scenario_quote_to_cash.py Changes (D1–D3)

### D.1 Add 3 Customers + 3 Sites (D2)

Add to the `CUSTOMERS` list at the end:
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

Add to `CUSTOMER_SITES` (new customers are indices 5, 6, 7):
```python
{
    "customer_idx": 5,
    "site_name": "Kim Residence",
    "line1": "321 Pine St",
    "city": "Seattle",
    "state": "WA",
    "postal_code": "98101",
    "country": "US",
},
{
    "customer_idx": 6,
    "site_name": "Metro Office Park",
    "line1": "555 Business Ave",
    "city": "Dallas",
    "state": "TX",
    "postal_code": "75201",
    "country": "US",
},
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

### D.2 Enrich Existing Draft Quote Lines (D1)

The existing draft quote (Q-DRAFT-001 for John Smith) has only 2 lines (labor + material). Expand to 8 lines covering all `qco_line_type` codes:

After the existing 2 lines, add:
- Line 3: `material` — 200A Panel Upgrade pricebook item × 1 = $1,800.00
- Line 4: `material` — EMT Conduit × 50 ft @ $3.50/ft = $175.00
- Line 5: `misc` — Residential Permit Fee × 1 = $250.00
- Line 6: `note` — text: `"All electrical work performed per NEC 2023 standards."` (no price, `qb_item_name_hint=NULL`)
- Line 7: `discount` — `unit_price_cents = -10000` (−$100 off), `description = "New customer discount"`
- Line 8: `material` — (add a new pricebook item: "Wire Nuts (bag)" SKU=WNUT-BAG-01 $5.00)

**New pricebook item to add**:
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

This brings `pricebook_item` to 6 rows total and the draft quote to 8 lines.

Idempotency check for existing lines: use `position` number — if line at position N already exists, skip.

### D.3 Add 9 New Quotes (D1)

Add a `QUOTES` constant list. Each quote references the customer by `customer_idx` (into the now 8-element `CUSTOMERS` list):

```python
QUOTES = [
    {
        "quote_number": "Q-PEND-APPR-001",
        "title": "Panel Upgrade — Pending Internal Approval",
        "status_code": "pending_approval",
        "customer_idx": 1,   # Mary Johnson
        "site_idx": 1,       # Johnson Home
        "subtotal_cents": 190000,  # 200A panel + breakers
        "submitted_by": "owner",
        "submitted_at_offset_days": -2,
    },
    {
        "quote_number": "Q-PEND-001",
        "title": "Commercial Panel Assessment — Pending Customer Review",
        "status_code": "pending",
        "customer_idx": 2,   # Apex Commercial LLC
        "site_idx": 2,       # Apex HQ
        "subtotal_cents": 320000,
        "submitted_at_offset_days": -1,
    },
    {
        "quote_number": "Q-APPR-001",
        "title": "Outlet Installation — Internally Approved",
        "status_code": "approved",
        "customer_idx": 5,   # Rachel Kim
        "site_idx": 5,       # Kim Residence
        "subtotal_cents": 45000,
        "approved_at_offset_days": -1,
    },
    {
        "quote_number": "Q-SENT-001",
        "title": "Service Panel Inspection — Sent to Customer",
        "status_code": "sent",
        "customer_idx": 6,   # Metro Properties LLC
        "site_idx": 6,       # Metro Office Park
        "subtotal_cents": 85000,
        "expires_at_offset_days": 14,  # expires 14 days from ANCHOR
    },
    {
        "quote_number": "Q-ACPT-001",
        "title": "Wiring Upgrade — Customer Accepted",
        "status_code": "accepted",
        "customer_idx": 7,   # James Torres
        "site_idx": 7,       # Torres Home
        "subtotal_cents": 230000,
        "customer_accepted_at_offset_days": -3,
        "customer_email_at_action": "james.torres@example.com",
        "customer_acceptance_comment": "Looks good, please proceed.",
    },
    {
        "quote_number": "Q-CONV-001",
        "title": "Electrical Inspection — Converted to Job",
        "status_code": "converted",
        "customer_idx": 0,   # John Smith
        "site_idx": 0,       # Smith Residence
        "subtotal_cents": 95000,
        # This quote anchors the full quote→job→invoice→payment chain
        "create_job_and_invoice": True,
    },
    {
        "quote_number": "Q-REJT-001",
        "title": "Solar Panel Wiring Estimate — Rejected",
        "status_code": "rejected",
        "customer_idx": 3,   # Bob Davis (prospect)
        "site_idx": None,    # no site — prospect
        "subtotal_cents": 450000,
        "customer_declined_at_offset_days": -5,
        "customer_decline_comment": "Too expensive for now.",
        "customer_decline_reason": "price",
    },
    {
        "quote_number": "Q-EXPR-001",
        "title": "Generator Install Estimate — Expired",
        "status_code": "expired",
        "customer_idx": 1,   # Mary Johnson
        "site_idx": 1,       # Johnson Home
        "subtotal_cents": 180000,
        "expires_at_offset_days": -30,  # expired 30 days before ANCHOR
    },
    {
        "quote_number": "Q-VOID-001",
        "title": "EV Charger Install — Voided",
        "status_code": "void",
        "customer_idx": 5,   # Rachel Kim
        "site_idx": 5,       # Kim Residence
        "subtotal_cents": 65000,
    },
]
```

**Idempotency**: check `WHERE tenant_id = :tid AND quote_number = :quote_number LIMIT 1`.

Each quote gets:
- 2–3 quote lines using existing pricebook items
- 1 `quote_version` row (required by quote detail endpoint)

### D.4 Q-CONV-001 → Job → Invoice → Payment Chain (D3)

When `create_job_and_invoice=True` on Q-CONV-001, after creating the quote:

**Step 1 — Job** (linked to quote):
```sql
INSERT INTO public.job
(id, tenant_id, customer_id, site_id, status_id, job_number, quote_id,
 scheduled_start_at, scheduled_end_at,
 actual_labor_cost_cents, actual_material_cost_cents, actual_profit_cents,
 is_active, version, created_at, updated_at)
VALUES (gen_random_uuid(), :tid, :cid, :sid, :completed_status_id, 'QTC-CONV-001', :quote_id,
        :anchor_minus_7days_9am, :anchor_minus_7days_5pm,
        48000, 22000, 25000,
        true, 1, NOW(), NOW())
```

**Step 2 — Invoice** (linked to job AND quote):
```sql
INSERT INTO public.invoice
(id, tenant_id, invoice_number, quote_id, job_id, customer_id, site_id, status_id,
 subtotal_cents, tax_cents, total_cents, balance_due_cents,
 currency, billing_mode, is_active, issued_at, due_at, reminder_count,
 created_at, updated_at)
VALUES (gen_random_uuid(), :tid, 'INV-QTC-001', :quote_id, :job_id, :cid, :sid, :paid_status_id,
        95000, 7600, 102600, 0,
        'USD', 'invoice', true, :anchor_minus_5days, :anchor_plus_25days, 0,
        NOW(), NOW())
```

**Step 3 — Payment** (linked to invoice):
```sql
INSERT INTO public.payment
(id, tenant_id, invoice_id, payment_method_id, status_id,
 amount_cents, paid_via, paid_at, is_active,
 created_at, updated_at)
VALUES (gen_random_uuid(), :tid, :inv_id, :seed_pm_id, :succeeded_status_id,
        102600, 'check', :anchor_minus_2days, true,
        NOW(), NOW())
```

**Idempotency**: check by `job.job_number = 'QTC-CONV-001'` and `invoice.invoice_number = 'INV-QTC-001'`.

---

## E. seed_scenario_reporting.py Changes (D4–D5)

### E.1 Invoice Fix — Re-run Idempotently (D4)

The invoice/payment code was added in B19. The script has been idempotent since then. **Simply re-running** `seed_scenario_reporting.py` will create the 4 invoices (A–D) and 2 payments that are currently missing. No code change is needed for this step — just re-run.

Expected result after re-run:
- INV-SEED-A: `paid`, John Smith, $1,325.16, due -14d from ANCHOR ✅ has payment
- INV-SEED-B: `paid`, Mary Johnson, $270.00, due -29d from ANCHOR ✅ has payment
- INV-SEED-C: `issued`, Apex Commercial LLC, $883.63, due -25d from ANCHOR (overdue) ✅ no payment
- INV-SEED-D: `draft`, John Smith, $235.63, due +20d from ANCHOR ✅ no payment

### E.2 Add Jobs E/F/G + New Invoice Statuses (D4)

Add 3 new job definitions to `REPORTING_JOBS`:

```python
# Job E — Partial payment received
{
    "title": "HVAC Coordination — Completed Job E",
    "days_ago": 20,
    "start_hour": 10,
    "end_hour": 15,
    "customer_idx": 0,  # John Smith (3rd job for repeat customer)
    "time_entries": [
        {"skill": "journeyman", "start_offset_h": 0, "duration_h": 3.0, "notes": "Coordination with HVAC contractor"},
    ],
    "expenses": [
        {"category": "materials", "description": "Electrical supplies", "cost_cents": 8500, "markup_pct": 20.0},
    ],
},
# Job F — Voided invoice
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
# Job G — Written off
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

**Invoice specs for Jobs E/F/G** (added to `invoice_specs` in the existing invoice loop):

```python
# Job E — partial (idx=4)
{
    "letter": "e",
    "subtotal_cents": 41700,
    "tax_cents": 3336,
    "total_cents": 45036,
    "balance_due_cents": 25036,  # partial payment received
    "issued_at_offset": -18,
    "due_at_offset": -4,         # overdue by 4 days
    "status_id": partial_inv_status_id,
    "create_payment": True,
    "partial_payment_cents": 20000,  # customer paid $200 of $450.36
},
# Job F — void (idx=5)
{
    "letter": "f",
    "subtotal_cents": 68400,
    "tax_cents": 5472,
    "total_cents": 73872,
    "balance_due_cents": 73872,
    "issued_at_offset": -33,
    "due_at_offset": -19,
    "status_id": void_inv_status_id,
    "create_payment": False,
},
# Job G — writeoff (idx=6)
{
    "letter": "g",
    "subtotal_cents": 202000,
    "tax_cents": 16160,
    "total_cents": 218160,
    "balance_due_cents": 218160,
    "issued_at_offset": -72,
    "due_at_offset": -42,        # severely overdue when written off
    "status_id": writeoff_inv_status_id,
    "create_payment": False,
},
```

**For partial payment (Job E)**: create a payment with `amount_cents = 20000` and then update invoice's `balance_due_cents` accordingly. The invoice is seeded with the post-partial `balance_due_cents = 25036`.

Need to add `partial_inv_status_id`, `void_inv_status_id`, `writeoff_inv_status_id` to the invoice status lookup:
```python
partial_inv_status_id = inv_status_map.get("partial")
void_inv_status_id = inv_status_map.get("void")
writeoff_inv_status_id = inv_status_map.get("writeoff")
```

### E.3 Refunded Payment — CONDITIONAL on Column Existence (D5)

⚠️ **GATE**: Before implementing D5, run this MCP query:
```sql
SELECT column_name FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'payment'
AND column_name = 'refunded_amount_cents';
```

**If column exists**: Add a refund row for Invoice B's payment:
```sql
INSERT INTO public.payment
(id, tenant_id, invoice_id, payment_method_id, status_id,
 amount_cents, paid_via, paid_at, is_active, created_at, updated_at)
VALUES (gen_random_uuid(), :tid, :inv_b_id, :seed_pm_id, :refunded_status_id,
        -3200, 'check', :refund_paid_at, true, NOW(), NOW())
-- Negative amount = refund per SD-2 design
```

**If column does NOT exist**: Skip D5. Log in Completion Summary that `payment.refunded_amount_cents` column was absent — SD-BE-1 migration needs to be applied first. Raise with Tom before proceeding.

---

## F. seed_scenario_dispatch.py Changes (D6)

### F.1 Add Owner as 2nd Tech on 2 Jobs

After the existing tech assignment loop, add owner as secondary tech to Jobs 1 and 2:

```python
# After seeding TECH_USER_ID as primary (ordinal=1), add OWNER_USER_ID as secondary (ordinal=2)
OWNER_USER_ID = UUID("00000000-0000-0000-0000-000000000002")

SECONDARY_ASSIGNMENTS = [0, 1]  # indices into job_ids (job 1 and job 2)

for job_idx in SECONDARY_ASSIGNMENTS:
    job_id, job_def = job_ids[job_idx]
    if not job_id:
        continue
    existing = db.execute(
        text("SELECT id FROM public.job_tech_assignment WHERE tenant_id=:tid AND job_id=:jid AND user_id=:uid"),
        {"tid": tid, "jid": job_id, "uid": str(OWNER_USER_ID)},
    ).first()
    if not existing:
        db.execute(text("""
            INSERT INTO public.job_tech_assignment
            (id, tenant_id, job_id, user_id, assigned_by_user_id, role, ordinal,
             assigned_at, is_active, version, created_at, updated_at)
            VALUES (gen_random_uuid(), :tid, :jid, :uid, :assigned_by, 'secondary', 2,
                    NOW(), true, 1, NOW(), NOW())
        """), {"tid": tid, "jid": job_id, "uid": str(OWNER_USER_ID), "assigned_by": str(OWNER_USER_ID)})
        print(f"  ✅ [job_tech_assignment] Assigned owner as secondary to {job_id}")
```

### F.2 Add Cancelled Job

Add to `JOBS` list:
```python
{
    "title": "Cancelled - Customer Backed Out",
    "status_code": "cancelled",
    "offset_days": None,  # no schedule
    "start_hour": None,
    "end_hour": None,
    "assign_tech": False,
    "job_number_override": "DISP-006",
},
```

Update job_number logic to use `job_number_override` if present.

### F.3 Add Sick Day Tech Availability

After the existing PTO block:
```python
# Owner has a sick day 2 weeks from next Friday
sick_date_utc = next_friday + timedelta(weeks=2)
sick_date_eod = sick_date_utc.replace(hour=17)

existing_sick = db.execute(text("""
    SELECT id FROM public.tech_availability
    WHERE tenant_id=:tid AND user_id=:uid AND availability_type='sick' AND starts_at=:starts
"""), {"tid": tid, "uid": str(OWNER_USER_ID), "starts": sick_date_utc}).first()

if not existing_sick:
    db.execute(text("""
        INSERT INTO public.tech_availability
        (id, tenant_id, user_id, availability_type, starts_at, ends_at, is_active, notes, created_at, updated_at)
        VALUES (gen_random_uuid(), :tid, :uid, 'sick', :starts, :ends, true, 'Owner sick day', NOW(), NOW())
    """), {"tid": tid, "uid": str(OWNER_USER_ID), "starts": sick_date_utc, "ends": sick_date_eod})
    print(f"  ✅ [tech_availability] Sick day for owner: {sick_date_utc.date()}")
```

---

## G. seed_scenario_supplier_catalog.py Changes (D7)

### G.1 Add SUPPLIER_2 and SUPPLIER_3

Add two new supplier constants:

```python
SUPPLIER_2_NAME = "Graybar Electric"
SUPPLIER_2_ITEMS = [
    ("WIRE-14AWG-THHN", "14 AWG THHN Wire", "wire_cable", "foot", 0.65),
    ("CONDUIT-EMT-0.75IN", '3/4" EMT Conduit', "conduit_raceway", "foot", 2.25),
    ("BREAKER-CH115", "Eaton CH115 15A Breaker", "dist_equip", "each", 10.50),
    ("OUTLET-GFCI-TR", "GFCI Outlet Tamper-Resistant", "wiring_devices", "each", 8.75),
    ("COUPLING-EMT-0.75IN", '3/4" EMT Coupling', "fittings", "each", 1.25),
]

SUPPLIER_3_NAME = "Platt Electric Supply"
SUPPLIER_3_ITEMS = [
    ("LIGHT-LED-2X4-PANEL", "LED Panel Light 2x4", "lighting", "each", 45.00),
    ("FAST-WIRE-STAPLES", "Wire Staples (box of 100)", "fasteners", "box", 12.50),
    ("TAPE-ELEC-ROLL", "Electrical Tape (roll)", "wiring_devices", "roll", 3.25),
    # Inactive item — for "discontinued items" filter testing
    ("INCAND-60W-BULB", "60W Incandescent Bulb (discontinued)", "lighting", "each", 1.50, False),
]
```

Note: The 4th element in each SUPPLIER_3_ITEMS tuple is `is_active` (default `True`). The incandescent bulb is `False` for inactive testing.

Update `mode_seed()` to loop over all 3 suppliers using the same idempotent pattern as Supplier 1.

---

## H. seed_scenario_mobile_sync.py Changes (D8, D11)

### H.1 Add Partial Failure Session + Events (D8)

Add a second device constant:
```python
SEED_DEVICE_ID_2 = UUID("00000000-0000-0000-0002-000000000001")
```

Add after the existing success session:
```python
# Session 2 — partial failure
existing_session_2 = db.execute(text("""
    SELECT id FROM public.mobile_sync_session
    WHERE tenant_id=:tid AND device_id=:device_id AND triggered_by='user_initiated' AND outcome='partial'
    LIMIT 1
"""), {"tid": tid, "device_id": str(SEED_DEVICE_ID_2)}).first()

if not existing_session_2:
    session2_result = db.execute(text("""
        INSERT INTO public.mobile_sync_session
        (id, tenant_id, user_id, device_id, triggered_by,
         outcome, items_attempted, items_committed, items_deferred, items_failed,
         started_at, completed_at, created_at)
        VALUES (gen_random_uuid(), :tid, :uid, :device_id, 'user_initiated',
                'partial', 3, 1, 1, 1,
                :started_at, :completed_at, NOW())
        RETURNING id
    """), {"tid": tid, "uid": uid, "device_id": str(SEED_DEVICE_ID_2),
           "started_at": SESSION_STARTED_AT - timedelta(days=1),
           "completed_at": SESSION_COMPLETED_AT - timedelta(days=1)})
    session2_id = str(session2_result.first().id)
    print(f"  ✅ [mobile_sync_session] Created partial failure session ({session2_id})")
```

Add 2 new events for device 2:
```python
events_2 = [
    {
        "operation_type": "update_job_status",
        "status": "conflict",
        "conflict_severity": "critical",
        "error_detail": "Server job status (completed) conflicts with client status (in_progress)",
        "idempotency_uuid": str(UUID("00000000-0001-0001-0001-000000000003")),
    },
    {
        "operation_type": "upload_photo",
        "status": "failed",
        "conflict_severity": None,
        "error_detail": "S3 upload timeout after 3 retries",
        "idempotency_uuid": str(UUID("00000000-0001-0001-0001-000000000004")),
    },
]
```

### H.2 Add `parse_args()` + `--mode` Support (D11)

Add standard argparse block matching the pattern from `seed_scenario_dispatch.py`:

```python
import argparse

def parse_args():
    parser = argparse.ArgumentParser(description="seed_scenario_mobile_sync.py — Group D mobile sync seeder")
    parser.add_argument("--mode", choices=["seed", "inspect", "show"], default="seed")
    parser.add_argument("--reset", action="store_true")
    return parser.parse_args()
```

Update `if __name__ == "__main__":` block to call the right function based on `args.mode` and `args.reset`.

---

## I. seed_scenario_nec.py Changes (D9, D11)

### I.1 Add box_fill Calc Row (D9)

Add a 3rd entry to the `rows` list in `_seed_impl()`:

```python
{
    "calc_type": "box_fill",
    "nec_guide_version": "2023",
    "inputs_json": '{"box_size_cubic_inches": 18, "conductors": [{"awg": "12", "count": 4}, {"awg": "14", "count": 2}], "devices": 1, "clamps": 1}',
    "result_json": '{"calc_type": "box_fill", "result_value": 16.25, "is_compliant": true, "nec_article": "NEC 314.16(B)", "nec_citation": "NEC 314.16(B) — Box fill calculation. Available: 18 cu.in, Required: 16.25 cu.in", "available_cubic_inches": 18, "required_cubic_inches": 16.25, "is_compliant": true}',
    "is_offline_calc": False,
    "client_capture_at": None,
},
```

Update idempotency check to also handle box_fill:
```python
# For box_fill rows, use a different amperage prefix pattern:
"inputs_prefix": f'%"box_size_cubic_inches"%',
```

Or more robustly: check by `calc_type` only (not amperage), since box_fill inputs don't have amperage.

### I.2 Add `parse_args()` + `--mode` Support (D11)

Same as H.2 — add standard argparse block. The existing `seed()`, `mode_reset()`, `mode_inspect()` functions already exist; just add the `__main__` routing.

---

## J. seed_scenario_customer_comms.py Changes (D10)

### J.1 Update Sunrise Electric Thread to `status=closed`

After seeding all threads, add a targeted UPDATE for the Sunrise Electric LLC thread:

```python
# After thread seeding loop — close the Sunrise Electric thread
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
print("  ✅ [customer_communication_thread] Updated Sunrise Electric LLC thread → status=closed")
```

This is idempotent (the `AND status != 'closed'` guard prevents repeated updates from failing).

---

## K. Pattern Reuse Decisions

| Pattern | Applied |
|---|---|
| Idempotent `INSERT ... ON CONFLICT DO NOTHING` | All new quote, job, invoice INSERTs |
| Check-by-quote_number for quotes | `WHERE tenant_id = :tid AND quote_number = :num LIMIT 1` |
| Check-by-invoice_number for invoices | `WHERE tenant_id = :tid AND invoice_number = :num LIMIT 1` |
| Check-by-job_number for the chain job | `WHERE tenant_id = :tid AND job_number = 'QTC-CONV-001' LIMIT 1` |
| Targeted UPDATE for existing rows | Comms thread status, labor_rate burden_pct (from SD-4) |
| ANCHOR_DATE pattern for fixed dates | Used by reporting script; quote dates use same pattern |
| `parse_args()` standard pattern | Added to nec + mobile_sync scripts |
| `mode_show()` update | All scripts that gain new data |
| `mode_inspect()` update | All scripts that gain new data |

---

## L. Open Questions Resolved

| Question | Resolution |
|---|---|
| Does `quote.valid_until` exist? | No — the column is `expires_at`. Use `expires_at` for Q-SENT-001 (expires 14d from ANCHOR) and Q-EXPR-001 (expired 30d before ANCHOR). |
| What `availability_type` values are valid? | `availability_type` is free-form `text` — `pto` and `sick` are both valid. |
| Does `payment.refunded_amount_cents` exist? | NOT confirmed in live DB (column query returned 0 rows). Python Engineer must run MCP check before implementing D5. If absent, skip D5 and flag for Tom. |
| Should mobile_sync events reference a session_id? | The schema header in the script shows `mobile_sync_event` does NOT have a `session_id` FK — events reference `tenant_id + user_id + device_id`. Sessions and events are separate tables. |
| `invoice.billing_mode` NOT NULL — what value? | `"invoice"` (standard mode). The reporting script already uses this. |
| Customer required for rejected quote (Bob Davis has no site) | Quote INSERT uses `site_id NOT NULL`. For Q-REJT-001 (Bob Davis, no site), use the first available site for the tenant as a placeholder OR add a site for Bob Davis. Decision: add a minimal site for Bob Davis in the qtc script. |

### L.1 Bob Davis Site Addition

Bob Davis (prospect) currently has no site. The `quote.site_id` is `NOT NULL`, so rejected/prospect quotes still need a site. Add:

```python
{
    "customer_idx": 3,  # Bob Davis
    "site_name": "Davis Property",
    "line1": "42 Prospect Lane",
    "city": "Denver",
    "state": "CO",
    "postal_code": "80201",
    "country": "US",
},
```

This brings `site` count to 4 in qtc. Total tenant sites after SD-5: 7 (3 qtc active + 1 Bob Davis + 3 new from D2).

---

## M. Deferred Items

| Item | Reason |
|---|---|
| `payment.refunded_amount_cents` seeding (D5) | Conditional on SD-BE-1 migration being applied to local DB. If absent, this row cannot be seeded. Python Engineer gates on MCP check. |
| Additional NEC calc types beyond box_fill | Only box_fill added in SD-5. Other types (wire_sizing, demand_load) deferred to SD-6 or later. |
| Multiple price rows per supplier item (price history) | Deferred — requires date-ranged tstzrange INSERT pattern. SD-5 adds only 1 price per item. |
| `recurrence_rrule` on tech_availability | The column exists but no recurring availability blocks are seeded. Deferred. |
| Email thread coverage in customer_comms | All threads are SMS-only. Email thread type deferred — may not be MVP scope. |

---

## N. README-seed-data.md Updates Required

After SD-5 implementation, update `backend/README-seed-data.md` §4 Group D tables:

| Scenario | Before SD-5 | After SD-5 |
|---|---|---|
| `customer` (qtc) | 5 | 8 (3 new: Kim, Metro, Torres) |
| `site` (qtc) | 3 | 7 (1 Bob Davis + 3 new customer sites) |
| `pricebook_item` | 5 | 6 (1 new: Wire Nuts bag) |
| `quote` | 1 (draft) | 10 (all statuses covered) |
| `quote_line` | 2 | 30+ (8 lines on draft + 2–3 per new quote) |
| `quote_version` | 1 | 10 (1 per quote) |
| `job` (qtc chain) | 0 | 1 (QTC-CONV-001, linked to Q-CONV-001) |
| `invoice` | 0 | 8 (4 existing restored + 1 qtc chain + 3 new) |
| `payment` | 0 | 4 (2 existing restored + 1 qtc chain + 1 partial) |
| `job` (dispatch) | 5 | 6 (1 new: cancelled DISP-006) |
| `job_tech_assignment` (dispatch) | 3 | 5 (2 secondary owner assignments) |
| `tech_availability` | 1 (PTO) | 2 (PTO + sick) |
| `job` (reporting) | 4 | 7 (3 new: E/F/G) |
| `job_time_entry` | 7 | 11 (4 new) |
| `job_expense` | 5 | 9 (4 new) |
| `supplier` | 1 | 3 (Wesco + Graybar + Platt) |
| `supplier_item` | 5 | 13 (5 Wesco + 5 Graybar + 3 Platt) |
| `supplier_item_price` | 5 | 13 |
| `mobile_sync_session` | 1 | 2 (1 new: partial failure) |
| `mobile_sync_event` | 2 | 4 (2 new: conflict + failed) |
| `nec_calculation_log` | 2 | 3 (1 new: box_fill) |
| `customer_communication_thread` | 3 (all active) | 3 (1 now closed) |
