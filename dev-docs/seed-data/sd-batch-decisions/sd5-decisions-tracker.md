# SD-5 Decisions Tracker (Working Doc)

**Session**: 2026-07-15
**Purpose**: Track all Group D audit decisions before writing batch-sd5-design.md

---

## Scope Decision

**Tom approved (2026-07-15)**: Include ALL must-have AND nice-to-have items in SD-5 — one batch. All quote/job/invoice data must be fully linked (quote → job → invoice → payment relational chain).

---

## Pre-Audit DB State (MCP-verified 2026-07-15)

| Table | Expected | Live | Status |
|---|---|---|---|
| `customer` | 8 | 9 | ⚠️ 1 extra (dispatch fallback) |
| `site` | 3 | 3 | ✅ |
| `job` | 9 | 13 | ⚠️ 4 extra (prior testing) |
| `job_time_entry` | 7 | 7 | ✅ |
| `invoice` | 4 | **0** | ❌ Must fix (re-run) |
| `payment` | 2 | **0** | ❌ Must fix (re-run) |
| `quote` | 1 | 1 | ✅ |
| `pricebook_item` | 5 | 5 | ✅ |
| `customer_communication_thread` | 3 | 3 | ✅ |
| `supplier` | 1 | 1 | ✅ |

---

## FK Schema (MCP-verified 2026-07-15)

- `job.quote_id UUID NULL` → `quote(id)` — links job to originating quote
- `invoice.job_id UUID NULL` → `job(id)` — links invoice to job
- `invoice.quote_id UUID NULL` → `quote(id)` — links invoice to originating quote
- `quote.title VARCHAR NULL` — display title for the quote

**Full relational chain**: quote → (converted to) job (job.quote_id) → (generates) invoice (invoice.job_id + invoice.quote_id) → payment

---

## Quote Status Coverage (10 codes in live DB)

| Code | Name | Terminal | Seed Target |
|---|---|---|---|
| `draft` | Draft | No | ✅ Already exists (QTC-001) — KEEP, enrich |
| `pending_approval` | Pending Approval | No | ➕ Add (internal review before sending) |
| `pending` | Pending Review | No | ➕ Add (sent, customer viewing) |
| `approved` | Approved | No | ➕ Add (internal approval granted) |
| `sent` | Sent to Customer | No | ➕ Add (sent to customer, no response yet) |
| `accepted` | Accepted | Yes | ➕ Add (customer accepted, not yet converted) |
| `converted` | Converted to Job | Yes | ➕ Add (becomes the anchor for job+invoice chain) |
| `rejected` | Rejected | Yes | ➕ Add (customer rejected) |
| `expired` | Expired | Yes | ➕ Add (past valid_until date) |
| `void` | Void | Yes | ➕ Add (cancelled before sending) |

**Total**: 10 quotes — 1 existing (draft) + 9 new

---

## Invoice Status Coverage (6 codes in live DB)

| Code | Name | Terminal | Seed Target | Linked to |
|---|---|---|---|---|
| `draft` | Draft | No | ➕ (for the draft quote's job — pre-issue) | job D |
| `issued` | Issued | No | ✅ Exists in reporting script (C) — re-run to restore | job C |
| `partial` | Partially Paid | No | ➕ Add — needs a partial payment | job E (new) |
| `paid` | Paid | Yes | ✅ Exists in reporting script (A,B) — re-run | jobs A, B |
| `void` | Void | Yes | ➕ Add — terminal, no payment | job F (new) |
| `writeoff` | Write-Off | Yes | ➕ Add — terminal, aged debt | job G (new) |

**Total**: 7 invoices (4 existing in reporting script that will be restored by re-run + 3 new)

---

## Decisions Log

### D1 — `seed_scenario_quote_to_cash.py`: Full quote status coverage + richer lines

**Problem**: Only 1 draft quote. All other Quotes list status tabs show empty state.

**Action**: Expand `seed_scenario_quote_to_cash.py` to seed 10 quotes covering all status codes:

1. **Q-DRAFT-001** (existing — enrich lines): draft, John Smith, Smith Residence — 8 lines (labor × 2, material × 3, misc × 1, note × 1, discount × 1)
2. **Q-PEND-APPR-001**: pending_approval, Mary Johnson, Johnson Home — 3 lines (panel + breakers + permit)
3. **Q-PEND-001**: pending, Apex Commercial LLC, Apex HQ — 4 lines (commercial work)
4. **Q-APPR-001**: approved, John Smith, Smith Residence — 3 lines
5. **Q-SENT-001**: sent, Mary Johnson, Johnson Home — 3 lines, `valid_until` = 14 days from ANCHOR_DATE
6. **Q-ACPT-001**: accepted, Apex Commercial LLC, Apex HQ — 4 lines, `valid_until` = future
7. **Q-CONV-001**: converted, John Smith, Smith Residence — 3 lines — this quote links to a job (job.quote_id)
8. **Q-REJT-001**: rejected, Bob Davis (prospect), no site — 2 lines
9. **Q-EXPR-001**: expired, Mary Johnson, Johnson Home — 3 lines, `valid_until` = past date
10. **Q-VOID-001**: void, John Smith, Smith Residence — 1 line (cancelled before sending)

Each quote gets a `quote_version` row (required by the detail endpoint).

**Rich line types for Q-DRAFT-001** (the primary testable quote):
- Line 1: Labor — Standard Outlet Installation × 1 = $150.00
- Line 2: Labor — 200A Panel Upgrade × 1 = $1,800.00
- Line 3: Material — 15A Circuit Breaker × 10 = $180.00
- Line 4: Material — EMT Conduit × 50 ft = $175.00
- Line 5: Misc — Residential Permit Fee × 1 = $250.00
- Line 6: Note — *(display text: "All electrical work performed per NEC 2023 standards.")*
- Line 7: Discount — -$100 off total
- Line 8: Material — Wire nuts (small) × 50 = $25.00

**Status**: 🔄 Pending

### D2 — `seed_scenario_quote_to_cash.py`: Add 3 more customers + sites for coverage

**Problem**: Only 5 customers total (3 active with sites, 1 prospect, 1 dormant). Not enough for relational coverage across 10 quotes + 7+ invoices without reusing the same customer for too many docs.

**Action**: Add 3 more customers with sites to the qtc script:
- **Rachel Kim** — active, person — `+14255551005` — site: "Kim Residence", 321 Pine St, Seattle WA 98101
- **Metro Properties LLC** — active, company — `+12025551006` — site: "Metro Office Park", 555 Business Ave, Dallas TX 75201
- **James Torres** — active, person — `+13055551007` — site: "Torres Home", 888 Palm Dr, Miami FL 33101

This gives us 8 active customers with sites, which supports 10 quotes across distinct customers without awkward overloading.

**Status**: 🔄 Pending

### D3 — `seed_scenario_quote_to_cash.py` + `seed_scenario_reporting.py`: Quote→Job→Invoice chain

**Problem**: No end-to-end relational chain from quote to job to invoice to payment exists.

**Action**: Add a linked chain to the qtc scenario. For `Q-CONV-001` (converted quote):
- Create a `job` row with `job.quote_id = Q-CONV-001.id`, `status=completed`
- Create an `invoice` row with `invoice.job_id = job.id` AND `invoice.quote_id = Q-CONV-001.id`, `status=paid`
- Create a `payment` row linked to the invoice

For the reporting scenario's 4 existing jobs (once re-run):
- They should also link back to quotes. The reporting jobs were originally seeded standalone (no `quote_id`). Update the reporting script to set `job.quote_id` where a corresponding quote exists for that customer.

**Status**: 🔄 Pending

### D4 — `seed_scenario_reporting.py`: Fix missing invoices + add partial/void/writeoff

**Problem**: 0 invoices in DB (script ran before B19 added invoice code). Also missing `partial`, `void`, `writeoff` status coverage.

**Action**:
1. Re-run `seed_scenario_reporting.py` — existing invoice code (added B19) will create 4 invoices (paid/paid/issued/draft) + 2 payments + 1 seed payment_method.
2. Add 3 new jobs + invoices to the reporting script for the missing statuses:
   - **Job E**: completed (20d ago) → invoice `partial` — `$8,500` invoice, `$4,000` partial payment received → `balance_due_cents = $4,500`
   - **Job F**: completed (35d ago) → invoice `void` — issued then voided before payment
   - **Job G**: completed (75d ago) → invoice `writeoff` — aged overdue, written off

These 3 new jobs follow the same pattern as A–D (with time entries + expenses).

**Status**: 🔄 Pending

### D5 — `seed_scenario_reporting.py`: Add refunded payment

**Problem**: No `refunded` payment status coverage. The Payments history surface can't test the refund flow.

**Action**: For Job B's invoice (paid), add a second payment row:
- `amount_cents = -3200` (negative — per the SD-2 refund model)
- `status = refunded` (from the `payment_status` lookup)
- `refunded_amount_cents` on the original payment updated to 3200

**Note**: Per SD-2 design: refunds create a new negative-amount payment row; the original `succeeded` row is unchanged. The `payment.refunded_amount_cents` column on the original payment tracks total refunded.

**Status**: 🔄 Pending

### D6 — `seed_scenario_dispatch.py`: Add 2nd tech + cancelled job

**Problem**: All tech assignments use only `tech@pilot.local` (`...0003`). Dispatch board multi-tech view not testable. No `cancelled` jobs exist.

**Action**:
1. Assign `owner` (`...0002`) as a secondary tech to 2 jobs:
   - Job 1 (scheduled tomorrow): owner as `secondary` tech, ordinal=2
   - Job 2 (in_progress today): owner as `secondary` tech, ordinal=2
2. Add a 6th job: `status=cancelled`, `job_number=DISP-006`, no schedule, no tech assignment
3. Add a 2nd tech_availability block: owner has a sick day (2 weeks from now), `availability_type=sick`

**Status**: 🔄 Pending

### D7 — `seed_scenario_supplier_catalog.py`: Add 2 more suppliers

**Problem**: Only 1 supplier (Wesco Distribution). Supplier list view shows 1 item. Multi-supplier filtering untestable.

**Action**: Add 2 more suppliers:

**Supplier 2 — Graybar Electric**:
- Items (5): 14AWG THHN Wire, 3/4" EMT Conduit, CH115 15A Breaker (Eaton), GFCI Outlet Tamper-Resistant, 3/4" EMT Coupling
- Categories: wire_cable, conduit_raceway, dist_equip, wiring_devices, fittings
- Prices: $0.65/ft, $2.25/ft, $10.50/ea, $8.75/ea, $1.25/ea

**Supplier 3 — Platt Electric (local)**:
- Items (3): LED Panel Light 2x4, Wire Staples (box), Electrical Tape (roll)
- Categories: lighting, fasteners, wiring_devices
- Prices: $45.00/ea, $12.50/box, $3.25/roll
- Also seed 1 inactive item (`is_active=false`) for the "inactive items" filter test

**Status**: 🔄 Pending

### D8 — `seed_scenario_mobile_sync.py`: Add failure/conflict scenario

**Problem**: Only happy-path sync data (success session + 2 succeeded events). Conflict resolution UI untestable.

**Action**: Add a 2nd session + 2 events representing a partial failure:
- Session 2: `outcome=partial`, `triggered_by=user_initiated`, `items_attempted=3`, `items_committed=1`, `items_deferred=1`, `items_failed=1`
- Event 3: `operation_type=update_job_status`, `status=conflict`, `idempotency_uuid=...000003`
- Event 4: `operation_type=upload_photo`, `status=failed`, `error_detail="S3 upload timeout"`, `idempotency_uuid=...000004`

Use SEED_DEVICE_ID_2 = `00000000-0000-0000-0002-000000000001` for the 2nd device.

**Status**: 🔄 Pending

### D9 — `seed_scenario_nec.py`: Add box_fill calc type

**Problem**: Only `voltage_drop` calc_type. NEC Calculation History list can't test filtering by calc_type.

**Action**: Add 1 more `nec_calculation_log` row:
- `calc_type = "box_fill"` (online calc, `is_offline_calc=False`)
- `inputs_json`: `{"box_size_cubic_inches": 18, "conductors": [{"awg": "12", "count": 4}, {"awg": "14", "count": 2}], "devices": 1, "clamps": 1}`
- `result_json`: compliant box fill calculation result

**Status**: 🔄 Pending

### D10 — `seed_scenario_customer_comms.py`: Add closed thread

**Problem**: All 3 threads are `status=active`. Thread archive/close state not testable.

**Action**: After seeding the 3 active threads, update the Sunrise Electric LLC thread to `status=closed`:
```sql
UPDATE customer_communication_thread SET status = 'closed' WHERE tenant_id = :tid AND customer_id = (SELECT id FROM customer WHERE tenant_id = :tid AND display_name = 'Sunrise Electric LLC')
```

This is an UPDATE, not a new INSERT — keeps idempotency since the thread already exists as active.

**Status**: 🔄 Pending

### D11 — `seed_scenario_nec.py` + `seed_scenario_mobile_sync.py`: Add `--mode` arg support

**Problem**: Both scripts lack the standard `parse_args()` + `--mode seed|inspect|show` + `--reset` CLI pattern used by all other Group D scripts. They call `seed()` directly as `__main__`. Inconsistency makes them harder to use.

**Action**: Add standard argparse block to both scripts matching the pattern in the other Group D scripts. No functional changes to the seed data itself.

**Status**: 🔄 Pending

---

## What Does NOT Change in SD-5

| Item | Reason |
|---|---|
| `seed_scenario_customer_comms.py` customer/contact data | 3 customers + contacts + entity_contacts are correct. Only the Sunrise thread status changes (D10). |
| `seed_scenario_nec.py` existing 2 rows | Kept as-is; only 1 new box_fill row added. |
| `seed_scenario_mobile_sync.py` existing session/events | Kept as-is; new partial-failure session added as 2nd device. |
| Extra jobs in dispatch (13 vs 9) | Leave as-is — extra jobs from prior testing won't break anything. Don't delete. |
| Extra customer (9 vs 8) | Dispatch fallback customer — leave as-is. |

---

## Open Questions — All Resolved

| Question | Resolution |
|---|---|
| Where does the quote→job→invoice chain live? | qtc script owns the quote; a new linked job is created in qtc; the reporting script is updated to link its jobs to quotes where possible |
| Does `quote.valid_until` exist? | Need to verify — not returned by column query. Will check in design doc MCP queries. |
| What `availability_type` codes exist in tech_availability? | `pto` confirmed. Need to check if `sick` is a valid code. |
| Mobile sync — does `mobile_sync_event.conflict_severity` need a value for conflict events? | Yes — column exists per schema header in the script. Use `"critical"` for the conflict event. |

*This tracker will be superseded by `batch-sd5-design.md` at end of session.*
