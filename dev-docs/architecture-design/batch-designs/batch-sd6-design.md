# Batch SD-6 Design — Deep Seed Data: Line Items, New Scenarios & README Updates

**Version**: 1.0  
**Date**: 2026-07-15  
**Author**: Pilot Architect  
**Status**: READY FOR IMPLEMENTATION  
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §2 P1 — Full UI Seed Data Expansion  
**Decisions tracker**: `dev-docs/seed-data/sd6-decisions-tracker.md`

---

## Table of Contents

- [Batch SD-6 Design — Deep Seed Data: Line Items, New Scenarios \& README Updates](#batch-sd-6-design--deep-seed-data-line-items-new-scenarios--readme-updates)
  - [Table of Contents](#table-of-contents)
  - [A. Input Read Summary](#a-input-read-summary)
  - [B. Migration Plan](#b-migration-plan)
    - [B.1 Pre-Implementation DB State Verification Queries](#b1-pre-implementation-db-state-verification-queries)
  - [C. Execution Order](#c-execution-order)
  - [D. Task 1 — `invoice_line` + `invoice_line_tax_component`: All 8 Invoices (D1)](#d-task-1--invoice_line--invoice_line_tax_component-all-8-invoices-d1)
    - [D.1 Schema Reference (MCP-verified)](#d1-schema-reference-mcp-verified)
    - [D.2 Pricebook Reference Data](#d2-pricebook-reference-data)
    - [D.3 Line Item Plan Per Invoice](#d3-line-item-plan-per-invoice)
    - [D.4 Tax Component Design](#d4-tax-component-design)
    - [D.5 Invoice Total UPDATE Pattern](#d5-invoice-total-update-pattern)
    - [D.6 `--reset` Behavior](#d6---reset-behavior)
  - [E. Task 2 — `mobile_sync_owner_escalation`: W-12 Coverage (D3)](#e-task-2--mobile_sync_owner_escalation-w-12-coverage-d3)
    - [E.1 Schema Reference (MCP-verified)](#e1-schema-reference-mcp-verified)
    - [E.2 Rows to Seed (in `seed_scenario_mobile_sync.py`)](#e2-rows-to-seed-in-seed_scenario_mobile_syncpy)
    - [E.3 ANCHOR\_DATE](#e3-anchor_date)
    - [E.4 `--reset` Behavior](#e4---reset-behavior)
  - [F. Task 3 — `loto_confirmation`: Safety Workflow Data (D4)](#f-task-3--loto_confirmation-safety-workflow-data-d4)
    - [F.1 Schema Discovery (MCP-verified)](#f1-schema-discovery-mcp-verified)
    - [F.2 Rows to Seed (in `seed_scenario_reporting.py`)](#f2-rows-to-seed-in-seed_scenario_reportingpy)
    - [F.3 `--reset` Behavior](#f3---reset-behavior)
  - [G. Task 4 — `change_order` + `change_order_line`: Job Change Orders (D5)](#g-task-4--change_order--change_order_line-job-change-orders-d5)
    - [G.1 Schema Reference (MCP-verified)](#g1-schema-reference-mcp-verified)
    - [G.2 Change Orders to Seed (in `seed_scenario_quote_to_cash.py`)](#g2-change-orders-to-seed-in-seed_scenario_quote_to_cashpy)
    - [G.3 `--reset` Behavior](#g3---reset-behavior)
  - [H. Task 5 — `seed_scenario_notifications.py`: New Notification Script (D6)](#h-task-5--seed_scenario_notificationspy-new-notification-script-d6)
    - [H.1 New File](#h1-new-file)
    - [H.2 Schema Reference (MCP-verified)](#h2-schema-reference-mcp-verified)
    - [H.3 Rows to Seed](#h3-rows-to-seed)
    - [H.4 Script Requirements](#h4-script-requirements)
    - [H.5 `--reset` Behavior](#h5---reset-behavior)
  - [I. Task 6 — `user_preference` + `user_setting_override` in `seed_test_tenant.py` (D7)](#i-task-6--user_preference--user_setting_override-in-seed_test_tenantpy-d7)
    - [I.1 Schema Reference (MCP-verified)](#i1-schema-reference-mcp-verified)
    - [I.2 Data to Seed](#i2-data-to-seed)
    - [I.3 Placement in `seed_test_tenant.py`](#i3-placement-in-seed_test_tenantpy)
    - [I.4 `--reset` Behavior](#i4---reset-behavior)
  - [J. Task 7 — `README-seed-data.md` Updates (D8, D9, D10)](#j-task-7--readme-seed-datamd-updates-d8-d9-d10)
    - [J.1 §4 Group A Count Corrections (D9)](#j1-4-group-a-count-corrections-d9)
    - [J.2 §4 Group D Update for SD-6](#j2-4-group-d-update-for-sd-6)
    - [J.3 §8 "What Is NOT Seeded" Additions (D10)](#j3-8-what-is-not-seeded-additions-d10)
    - [J.4 §9 Scenario Status Registry](#j4-9-scenario-status-registry)
    - [J.5 §10 Roadmap (D8)](#j5-10-roadmap-d8)
  - [K. Pattern Reuse Decisions](#k-pattern-reuse-decisions)
  - [L. Open Questions Resolved](#l-open-questions-resolved)
  - [M. Schema Discoveries (MCP-verified 2026-07-15)](#m-schema-discoveries-mcp-verified-2026-07-15)
    - [M.1 Critical Column Corrections](#m1-critical-column-corrections)
    - [M.2 Live Data IDs (Engineer Reference)](#m2-live-data-ids-engineer-reference)

---

## A. Input Read Summary

All inputs read and verified via MCP before this design was written (2026-07-15):

| Input | Key Finding |
|---|---|
| `invoice_line` schema | 24 columns. `source_type VARCHAR NOT NULL` — must be set in every INSERT (no default). `pricebook_item_id` is nullable. No `updated_at` — append-only pattern. |
| `invoice_line_tax_component` schema | 10 columns. Links via `invoice_line_id` + `tax_rate_version_id` (bigint). `component_code VARCHAR NOT NULL`. No `updated_at`. |
| `loto_confirmation` schema | No `status` column. `confirmed_at TIMESTAMPTZ NOT NULL`. A row = confirmed LOTO. Cannot seed "pending" state — that concept is application-level (job with `loto_confirmation_required=true` setting and no row yet). Seed 2 confirmed rows. |
| `change_order` schema | No `status` column. A change order is a neutral record attached to a job. `description VARCHAR NOT NULL`. Tom's "pending/approved" distinction exists at the application/UI layer — will seed 2 change orders with descriptive descriptions. |
| `change_order_line` schema | Has `pricebook_item_id` (nullable), `supplier_id` + `supplier_item_id` (nullable), full tax columns, `position INT NOT NULL`, `qco_line_type_id NOT NULL`. |
| `in_app_notification` schema | `category_id TEXT NOT NULL` — free-text matching `notification_category.code`. `deep_link_target TEXT NOT NULL`. `read_at TIMESTAMPTZ` (NULL = unread). `priority TEXT` (default 'standard'). No FK constraint — just a text match. |
| `mobile_sync_owner_escalation` schema | `conflict_id UUID NOT NULL` — links semantically to `mobile_sync_event.id`. No FK constraint declared in DB. `escalation_reason TEXT NOT NULL`, `escalation_reason_explainer TEXT NOT NULL`. `status TEXT` (default 'pending'). `resolved_by_user_id`, `resolved_at`, `resolution_action` — nullable. |
| `user_preference` schema | Single JSONB column `preferences` (default `{}`). Append-only style (`created_at` only, no `updated_at`). `tenant_id` is nullable. |
| `user_setting_override` schema | Composite PK: `(tenant_id, user_id, setting_key)`. `value JSONB NOT NULL`. Only 2 `allows_user_override=true` keys in catalog: `background_sync_enabled` (boolean), `voice_persona_tone` (string). |
| `pricebook_item_version` schema | Column is `default_unit_price_cents` (NOT `unit_price_cents`). `id` is bigint (not UUID). |
| `payment` schema | `payment_method_id UUID NOT NULL`. Existing payments all use `02e3ab2d-27be-41c0-b425-1e2da0b08f7f` (the seeded test payment method). |
| Live pricebook items | 6 items with version IDs. See §M for full table. |
| `qco_line_type` codes | labor=`65a92851`, material=`bb1588c7`, misc=`c067e242`, note=`1dd2f395`, discount=`78d28734` |
| `tax_rate_version` | US-DEFAULT: id=1, jurisdiction_code='US-DEFAULT', rate=6.00% |
| `notification_category.code` values | background_sync_alerts, billing, customer_activity, field_issues, job_activity, quote_approvals, sync_conflicts, system_announcements |
| Q-CONV-001 converted job | job_id=`60605a9f-e883-42f0-abd8-21a33254a27f`, job_number=JOB-900001 |
| Conflict mobile_sync_event | id=`624b8d17-6c49-402d-b6fc-874a0cd039e1`, operation_type=update_job_status, status=conflict |
| Completed dispatch job (LOTO target) | DISP-003: `bcfa701e-061f-49b4-b307-2dbe367a3496`, DISP-004: `2342c504-203c-4e2d-86b1-ecc4444a96c2` |
| `tenant_phone_number` cleanup | Tom ran `DELETE FROM tenant_phone_number WHERE phone_number = ''` → 580 rows removed ✅ |

---

## B. Migration Plan

**No Alembic migrations required.** All changes are to Python seed scripts and README documentation only. All columns used already exist in the live DB.

### B.1 Pre-Implementation DB State Verification Queries

The Python Engineer MUST run these via `postgres-local` MCP before writing any code:

```sql
-- 1. Confirm invoice_line is still empty (should be 0)
SELECT COUNT(*) FROM invoice_line WHERE tenant_id = '00000000-0000-0000-0000-000000000001';
-- Expected: 0

-- 2. Confirm invoice_line_tax_component is empty
SELECT COUNT(*) FROM invoice_line_tax_component WHERE tenant_id = '00000000-0000-0000-0000-000000000001';
-- Expected: 0

-- 3. Confirm all 8 invoices exist and get their IDs + current totals
SELECT invoice_number, id, total_cents, subtotal_cents, tax_cents, balance_due_cents
FROM invoice
WHERE tenant_id = '00000000-0000-0000-0000-000000000001'
ORDER BY invoice_number;

-- 4. Confirm pricebook_item_version IDs (bigint) with prices
SELECT pi.name, piv.id AS version_id, piv.default_unit_price_cents, pi.taxability_code
FROM pricebook_item pi
JOIN pricebook_item_version piv ON piv.pricebook_item_id = pi.id
WHERE pi.tenant_id = '00000000-0000-0000-0000-000000000001'
ORDER BY pi.name;

-- 5. Confirm qco_line_type IDs
SELECT id, code FROM qco_line_type ORDER BY code;

-- 6. Confirm tax_rate_version for US-DEFAULT
SELECT id, jurisdiction_code, rate_pct FROM tax_rate_version WHERE jurisdiction_code = 'US-DEFAULT';
-- Expected: id=1, rate_pct=6.0

-- 7. Confirm conflict mobile_sync_event ID
SELECT id, operation_type, status, conflict_severity
FROM mobile_sync_event
WHERE id = '624b8d17-6c49-402d-b6fc-874a0cd039e1';

-- 8. Confirm mobile_sync_owner_escalation is empty
SELECT COUNT(*) FROM mobile_sync_owner_escalation WHERE tenant_id = '00000000-0000-0000-0000-000000000001';
-- Expected: 0

-- 9. Confirm loto_confirmation is empty
SELECT COUNT(*) FROM loto_confirmation WHERE tenant_id = '00000000-0000-0000-0000-000000000001';
-- Expected: 0

-- 10. Confirm change_order is empty
SELECT COUNT(*) FROM change_order WHERE tenant_id = '00000000-0000-0000-0000-000000000001';
-- Expected: 0

-- 11. Confirm in_app_notification is empty
SELECT COUNT(*) FROM in_app_notification WHERE tenant_id = '00000000-0000-0000-0000-000000000001';
-- Expected: 0

-- 12. Confirm user_setting_override keys (allows_user_override=true)
SELECT key, label, value_type FROM platform_setting_catalog WHERE allows_user_override = true;
-- Expected: background_sync_enabled (boolean), voice_persona_tone (string)

-- 13. Confirm tenant_phone_number cleanup ran (should be 1 row)
SELECT COUNT(*) FROM tenant_phone_number WHERE tenant_id = '00000000-0000-0000-0000-000000000001';
-- Expected: 1
```

---

## C. Execution Order

| Step | Script | Task | Tables Written |
|---|---|---|---|
| 1 | `seed_scenario_quote_to_cash.py` | Add `invoice_line` + `invoice_line_tax_component` for INV-900001; add `change_order` + `change_order_line` for JOB-900001 | `invoice_line`, `invoice_line_tax_component`, `invoice` (UPDATE totals), `change_order`, `change_order_line` |
| 2 | `seed_scenario_reporting.py` | Add `invoice_line` + `invoice_line_tax_component` for INV-SEED-A through G; add `loto_confirmation` rows | `invoice_line`, `invoice_line_tax_component`, `invoice` (UPDATE totals), `loto_confirmation` |
| 3 | `seed_scenario_mobile_sync.py` | Add `mobile_sync_owner_escalation` (1 open + 1 resolved) | `mobile_sync_owner_escalation` |
| 4 | `seed_scenario_notifications.py` | **New script** — seed `in_app_notification` rows for owner user | `in_app_notification` |
| 5 | `seed_test_tenant.py` | Add `user_preference` + `user_setting_override` for owner user | `user_preference`, `user_setting_override` |
| 6 | `reset_dev_db.py` | Register new `notifications` scenario | `reset_dev_db.py` |
| 7 | `README-seed-data.md` | Documentation updates (§4, §8, §10) | `README-seed-data.md` |

---

## D. Task 1 — `invoice_line` + `invoice_line_tax_component`: All 8 Invoices (D1)

### D.1 Schema Reference (MCP-verified)

**`invoice_line`** key columns:
- `id UUID` (gen_random_uuid())
- `invoice_id UUID NOT NULL`
- `source_type VARCHAR NOT NULL` — use `'manual'` for all seeded lines
- `source_id UUID` (nullable) — leave NULL
- `position INT NOT NULL` — line ordering (1, 2, 3...)
- `qco_line_type_id UUID NOT NULL` — FK to `qco_line_type.id`
- `pricebook_item_id UUID` (nullable) — set to `pricebook_item.id` (NOT version ID)
- `description VARCHAR NOT NULL`
- `quantity NUMERIC NOT NULL` (default 1)
- `unit VARCHAR` (nullable) — e.g. 'hr', 'ea', 'ft'
- `unit_price_cents INT NOT NULL` (default 0)
- `taxability_code VARCHAR` — copy from pricebook_item (taxable/exempt)
- `subtotal_cents INT NOT NULL` — = `unit_price_cents × quantity` (rounded to integer)
- `total_cents INT NOT NULL` — = subtotal_cents + tax_amount_cents
- `tenant_id UUID NOT NULL`
- Tax columns (all nullable for exempt lines): `tax_rate_pct`, `tax_basis_cents`, `tax_amount_cents`, `tax_jurisdiction_code`, `tax_as_of`, `tax_source`

**`invoice_line_tax_component`** key columns:
- `id UUID` (gen_random_uuid())
- `invoice_line_id UUID NOT NULL`
- `tax_rate_version_id BIGINT NOT NULL` — use `1` (US-DEFAULT)
- `component_code VARCHAR NOT NULL` — use `'US-DEFAULT'`
- `rate_pct NUMERIC NOT NULL` — 6.00
- `amount_cents INT NOT NULL` — = round(subtotal_cents × 0.06)
- `tenant_id UUID NOT NULL`

### D.2 Pricebook Reference Data

| Item name | item_id | version_id (bigint) | default_unit_price_cents | taxability |
|---|---|---|---|---|
| Standard Outlet Installation | `e1881d63-e6ab-4514-b9e6-20e3b6d8236f` | 17216 | 15000 ($150) | taxable |
| 200A Panel Upgrade | `683de1cb-1909-465e-a12a-dc33b12a0311` | 17217 | 180000 ($1,800) | taxable |
| 15A Circuit Breaker | `3090ca84-374a-4315-8a63-42e61c22fde8` | 17218 | 1800 ($18) | taxable |
| EMT Conduit | `d2e55b5d-bdb7-403e-a2b6-3139768a654c` | 17219 | 350 ($3.50/ft) | taxable |
| Residential Permit Fee | `0cd9bfda-c801-4711-b22c-e6377450ed01` | 17220 | 25000 ($250) | exempt |
| Wire Nuts (bag of 50) | `d8254a6f-c0af-42a4-af76-7667958522ce` | 22350 | 500 ($5) | taxable |

**Note**: `invoice_line.pricebook_item_id` takes the `pricebook_item.id` (UUID), not the `pricebook_item_version.id` (bigint).

### D.3 Line Item Plan Per Invoice

The Python Engineer MUST:
1. Define line items as shown below
2. Compute `subtotal_cents`, `tax_cents`, `total_cents` from the line math
3. UPDATE the invoice row to set the computed totals (replacing hardcoded values from prior seeding)
4. For paid invoices: also UPDATE the payment row's `amount_cents` to match the new `total_cents`
5. For partial invoice (INV-SEED-E): set `balance_due_cents = total_cents - partial_payment_amount`

**INV-900001 (paid — Q-CONV-001 chain, JOB-900001)**

| # | Type | Item | Qty | Unit | unit_price_cents | subtotal_cents | taxable? |
|---|---|---|---|---|---|---|---|
| 1 | labor | Standard Outlet Installation | 3 | hr | 15000 | 45000 | ✅ |
| 2 | material | 15A Circuit Breaker | 12 | ea | 1800 | 21600 | ✅ |
| 3 | misc | Residential Permit Fee | 1 | ea | 25000 | 25000 | ❌ |

- subtotal = 91600, taxable_base = 66600, tax = round(66600 × 0.06) = 3996
- invoice total = 95596, balance_due = 0 (paid)
- UPDATE payment amount to 95596

**INV-SEED-A (paid — Panel Upgrade job, ~45 days ago)**

| # | Type | Item | Qty | Unit | unit_price_cents | subtotal_cents | taxable? |
|---|---|---|---|---|---|---|---|
| 1 | labor | 200A Panel Upgrade | 1 | ea | 180000 | 180000 | ✅ |
| 2 | material | EMT Conduit | 25 | ft | 350 | 8750 | ✅ |
| 3 | material | Wire Nuts (bag of 50) | 2 | ea | 500 | 1000 | ✅ |
| 4 | misc | Residential Permit Fee | 1 | ea | 25000 | 25000 | ❌ |

- subtotal = 214750, taxable_base = 189750, tax = round(189750 × 0.06) = 11385
- invoice total = 226135, balance_due = 0 (paid)
- UPDATE INV-SEED-A payment amount to 226135

**INV-SEED-B (paid — Service Call, ~45 days ago)**

| # | Type | Item | Qty | Unit | unit_price_cents | subtotal_cents | taxable? |
|---|---|---|---|---|---|---|---|
| 1 | labor | Standard Outlet Installation | 2 | ea | 15000 | 30000 | ✅ |
| 2 | material | 15A Circuit Breaker | 6 | ea | 1800 | 10800 | ✅ |
| 3 | material | Wire Nuts (bag of 50) | 1 | ea | 500 | 500 | ✅ |

- subtotal = 41300, taxable_base = 41300, tax = round(41300 × 0.06) = 2478
- invoice total = 43778, balance_due = 0 (paid)
- UPDATE INV-SEED-B payment amount to 43778
- **Refund row** (existing negative payment): keep at -3200 cents (partial refund on circuit breakers). UPDATE original payment `amount_cents` = 43778.

**INV-SEED-C (issued — Commercial Inspection, ~60 days ago)**

| # | Type | Item | Qty | Unit | unit_price_cents | subtotal_cents | taxable? |
|---|---|---|---|---|---|---|---|
| 1 | labor | Standard Outlet Installation | 5 | ea | 15000 | 75000 | ✅ |
| 2 | material | EMT Conduit | 30 | ft | 350 | 10500 | ✅ |
| 3 | misc | Residential Permit Fee | 1 | ea | 25000 | 25000 | ❌ |

- subtotal = 110500, taxable_base = 85500, tax = round(85500 × 0.06) = 5130
- invoice total = 115630, balance_due = 115630 (issued, unpaid)
- UPDATE INV-SEED-C totals

**INV-SEED-D (draft — Outlet Install, ~15 days ago)**

| # | Type | Item | Qty | Unit | unit_price_cents | subtotal_cents | taxable? |
|---|---|---|---|---|---|---|---|
| 1 | labor | Standard Outlet Installation | 1 | ea | 15000 | 15000 | ✅ |
| 2 | material | Wire Nuts (bag of 50) | 2 | ea | 500 | 1000 | ✅ |

- subtotal = 16000, taxable_base = 16000, tax = round(16000 × 0.06) = 960
- invoice total = 16960, balance_due = 16960 (draft)
- UPDATE INV-SEED-D totals

**INV-SEED-E (partial — HVAC Coordination, ~20 days ago)**

| # | Type | Item | Qty | Unit | unit_price_cents | subtotal_cents | taxable? |
|---|---|---|---|---|---|---|---|
| 1 | labor | 200A Panel Upgrade | 1 | ea | 180000 | 180000 | ✅ |
| 2 | misc | Residential Permit Fee | 1 | ea | 25000 | 25000 | ❌ |

- subtotal = 205000, taxable_base = 180000, tax = round(180000 × 0.06) = 10800
- invoice total = 215800
- Partial payment: 80000 cents ($800 paid, existing payment row)
- balance_due = 215800 - 80000 = 135800
- UPDATE INV-SEED-E totals; UPDATE partial payment amount to 80000

**INV-SEED-F (void — Generator Hookup, ~35 days ago)**

| # | Type | Item | Qty | Unit | unit_price_cents | subtotal_cents | taxable? |
|---|---|---|---|---|---|---|---|
| 1 | labor | 200A Panel Upgrade | 1 | ea | 180000 | 180000 | ✅ |
| 2 | material | EMT Conduit | 50 | ft | 350 | 17500 | ✅ |
| 3 | misc | Residential Permit Fee | 1 | ea | 25000 | 25000 | ❌ |

- subtotal = 222500, taxable_base = 197500, tax = round(197500 × 0.06) = 11850
- invoice total = 234350, balance_due = 234350 (void — no payment)
- UPDATE INV-SEED-F totals

**INV-SEED-G (writeoff — Commercial Rewire, ~75 days ago)**

| # | Type | Item | Qty | Unit | unit_price_cents | subtotal_cents | taxable? |
|---|---|---|---|---|---|---|---|
| 1 | labor | 200A Panel Upgrade | 2 | ea | 180000 | 360000 | ✅ |
| 2 | material | EMT Conduit | 100 | ft | 350 | 35000 | ✅ |
| 3 | material | 15A Circuit Breaker | 20 | ea | 1800 | 36000 | ✅ |
| 4 | misc | Residential Permit Fee | 2 | ea | 25000 | 50000 | ❌ |

- subtotal = 481000, taxable_base = 431000, tax = round(431000 × 0.06) = 25860
- invoice total = 506860, balance_due = 506860 (writeoff — no payment)
- UPDATE INV-SEED-G totals

### D.4 Tax Component Design

For every taxable `invoice_line` row, insert one `invoice_line_tax_component` row:
- `tax_rate_version_id = 1` (US-DEFAULT)
- `component_code = 'US-DEFAULT'`
- `rate_pct = 6.00`
- `amount_cents = round(line.subtotal_cents * 0.06)`

For exempt lines (`Residential Permit Fee`): do NOT insert a tax component.

### D.5 Invoice Total UPDATE Pattern

After inserting all `invoice_line` and `invoice_line_tax_component` rows, UPDATE each invoice:

```sql
UPDATE invoice SET
  subtotal_cents = <computed>,
  tax_cents = <computed>,
  total_cents = <computed>,
  balance_due_cents = <computed>
WHERE id = '<invoice_id>'
  AND tenant_id = '00000000-0000-0000-0000-000000000001';
```

For paid invoices (INV-900001, INV-SEED-A, INV-SEED-B): also UPDATE the linked payment:
```sql
UPDATE payment SET amount_cents = <new_total_cents>
WHERE invoice_id = '<invoice_id>'
  AND amount_cents > 0  -- positive only, preserve the refund row
  AND tenant_id = '00000000-0000-0000-0000-000000000001';
```

### D.6 `--reset` Behavior

Add `invoice_line` and `invoice_line_tax_component` to the DELETE block in both `seed_scenario_quote_to_cash.py` and `seed_scenario_reporting.py` reset logic. On reset, ALSO reset invoice totals back to zero (so re-seeding recalculates them cleanly).

---

## E. Task 2 — `mobile_sync_owner_escalation`: W-12 Coverage (D3)

### E.1 Schema Reference (MCP-verified)

| Column | Type | Notes |
|---|---|---|
| `id` | UUID | gen_random_uuid() |
| `tenant_id` | UUID NOT NULL | |
| `originating_user_id` | UUID NOT NULL | The tech who triggered the conflict |
| `conflict_id` | UUID NOT NULL | Links to `mobile_sync_event.id` (no FK constraint declared) |
| `escalated_at` | TIMESTAMPTZ NOT NULL | default now() |
| `escalation_reason` | TEXT NOT NULL | Short code-like reason |
| `escalation_reason_explainer` | TEXT NOT NULL | Human-readable detail |
| `status` | TEXT NOT NULL | default 'pending' |
| `resolved_by_user_id` | UUID | NULL for open escalations |
| `resolved_at` | TIMESTAMPTZ | NULL for open escalations |
| `resolution_action` | TEXT | NULL for open escalations |
| `resolution_payload` | JSONB | NULL |

### E.2 Rows to Seed (in `seed_scenario_mobile_sync.py`)

**Row 1 — Open escalation** (linked to the existing conflict event):

```
conflict_id: '624b8d17-6c49-402d-b6fc-874a0cd039e1'  (update_job_status conflict event, Session 2)
originating_user_id: '00000000-0000-0000-0000-000000000003'  (tech@pilot.local)
escalation_reason: 'job_status_conflict'
escalation_reason_explainer: 'Technician attempted to mark job in_progress while owner had already changed status to scheduled. Requires owner review before proceeding.'
status: 'pending'
resolved_by_user_id: NULL
resolved_at: NULL
resolution_action: NULL
escalated_at: ANCHOR_DATE (same as SD-5 anchor — use NOW() at seed time or hardcode to 2026-07-10)
```

**Row 2 — Resolved escalation** (fabricate a second mobile_sync_event for an older past conflict):

First insert a new `mobile_sync_event` row representing a resolved older conflict:
```
id: gen_random_uuid()
tenant_id: test tenant
user_id: '00000000-0000-0000-0000-000000000003'
device_id: '00000000-0000-0000-0002-000000000001'
operation_type: 'update_expense'
status: 'conflict'
conflict_severity: 'owner_escalation'
idempotency_uuid: '00000000-0002-0002-0002-000000000099'
client_capture_at: ANCHOR_DATE - 10 days
created_at: ANCHOR_DATE - 10 days
```

Then insert the resolved escalation:
```
conflict_id: <id of above event>
originating_user_id: '00000000-0000-0000-0000-000000000003'
escalation_reason: 'expense_amount_conflict'
escalation_reason_explainer: 'Technician submitted an expense update that conflicted with a recently approved purchase order. Owner reviewed and accepted the technician change.'
status: 'resolved'
resolved_by_user_id: '00000000-0000-0000-0000-000000000002'  (owner/dev@pilot.local)
resolved_at: ANCHOR_DATE - 9 days
resolution_action: 'owner_accepted_device_change'
resolution_payload: {"accepted_value": "materials", "note": "Technician expense confirmed correct"}
escalated_at: ANCHOR_DATE - 10 days
```

### E.3 ANCHOR_DATE

Use `ANCHOR_DATE = datetime(2026, 7, 1, tzinfo=timezone.utc)` — consistent with SD-5 reporting script anchor.

### E.4 `--reset` Behavior

Add `mobile_sync_owner_escalation` to the DELETE list in `seed_scenario_mobile_sync.py` reset block. The fabricated `mobile_sync_event` (row 2 anchor) should also be deleted on reset (delete by idempotency_uuid `...0099`).

---

## F. Task 3 — `loto_confirmation`: Safety Workflow Data (D4)

### F.1 Schema Discovery (MCP-verified)

```
id            UUID (gen_random_uuid())  
tenant_id     UUID NOT NULL  
job_id        UUID NOT NULL  
user_id       UUID NOT NULL  
confirmed_at  TIMESTAMPTZ NOT NULL  
client_capture_at   TIMESTAMPTZ (nullable)  
server_received_at  TIMESTAMPTZ (nullable)  
is_active     BOOLEAN NOT NULL (default true)  
created_at    TIMESTAMPTZ NOT NULL (default now())  
created_by    UUID (nullable)  
```

**Key design note**: There is NO `status` column. A `loto_confirmation` row = a completed lockout confirmation. A job with LOTO required but no confirmation row = "pending" state (application logic). The seed can only create "confirmed" records.

### F.2 Rows to Seed (in `seed_scenario_reporting.py`)

Attach to the two most suitable completed jobs from the reporting scenario:

**Row 1 — LOTO confirmation for INV-SEED-A job (Panel Upgrade — completed)**:
```
job_id: <job linked to INV-SEED-A>  (query during script: get job_id from invoice WHERE invoice_number = 'INV-SEED-A')
user_id: '00000000-0000-0000-0000-000000000003'  (tech@pilot.local)
confirmed_at: ANCHOR_DATE - 30 days + 9:15 AM (job was ~30d ago — confirm before work started)
client_capture_at: confirmed_at
server_received_at: confirmed_at + 2 seconds
is_active: true
```

**Row 2 — LOTO confirmation for INV-SEED-G job (Commercial Rewire — completed)**:
```
job_id: <job linked to INV-SEED-G>  (query: get job_id from invoice WHERE invoice_number = 'INV-SEED-G')
user_id: '00000000-0000-0000-0000-000000000003'  (tech@pilot.local)
confirmed_at: ANCHOR_DATE - 75 days + 8:00 AM
client_capture_at: confirmed_at
server_received_at: confirmed_at + 5 seconds
is_active: true
```

### F.3 `--reset` Behavior

Add `loto_confirmation` to the DELETE block in `seed_scenario_reporting.py` reset logic.

---

## G. Task 4 — `change_order` + `change_order_line`: Job Change Orders (D5)

### G.1 Schema Reference (MCP-verified)

**`change_order`** key columns:
```
id               UUID  
job_id           UUID NOT NULL → job.id  
description      VARCHAR NOT NULL  
subtotal_cents   INT NOT NULL (default 0)  
tax_cents        INT NOT NULL (default 0)  
total_cents      INT NOT NULL (default 0)  
is_active        BOOLEAN NOT NULL (default true)  
tenant_id        UUID NOT NULL  
client_capture_at / server_received_at  TIMESTAMPTZ (nullable)  
created_at, updated_at  TIMESTAMPTZ NOT NULL  
```

**Schema note**: NO `status` column exists. Change orders are neutral records. The description will communicate intent ("Pending owner approval" vs "Approved by owner").

**`change_order_line`** key columns:
```
id               UUID  
change_order_id  UUID NOT NULL → change_order.id  
position         INT NOT NULL  
qco_line_type_id UUID NOT NULL → qco_line_type.id  
pricebook_item_id UUID (nullable) → pricebook_item.id  
description      VARCHAR NOT NULL  
quantity         NUMERIC NOT NULL (default 1)  
unit             VARCHAR (nullable)  
unit_price_cents INT NOT NULL (default 0)  
subtotal_cents   INT NOT NULL (default 0)  
total_cents      INT NOT NULL (default 0)  
is_active        BOOLEAN NOT NULL (default true)  
tenant_id        UUID NOT NULL  
```

### G.2 Change Orders to Seed (in `seed_scenario_quote_to_cash.py`)

Both change orders attach to **JOB-900001** (`60605a9f-e883-42f0-abd8-21a33254a27f`) — the Q-CONV-001 converted job.

**CO-001 — "Additional panel breakers — pending owner approval"**

Description: `'Additional 20A breakers requested by customer after panel inspection — awaiting owner approval'`

Lines:
| # | type | item | qty | unit | unit_price_cents | subtotal_cents |
|---|---|---|---|---|---|---|
| 1 | material | 15A Circuit Breaker | 8 | ea | 1800 | 14400 |
| 2 | labor | Standard Outlet Installation | 1 | ea | 15000 | 15000 |

- subtotal = 29400, tax = round(29400 × 0.06) = 1764, total = 31164
- Both lines are taxable → SET change_order.tax_cents = 1764

**CO-002 — "Conduit extension — approved"**

Description: `'Extension of EMT conduit run to secondary panel location — approved by owner 2026-07-10'`

Lines:
| # | type | item | qty | unit | unit_price_cents | subtotal_cents |
|---|---|---|---|---|---|---|
| 1 | labor | Standard Outlet Installation | 2 | ea | 15000 | 30000 |
| 2 | material | EMT Conduit | 40 | ft | 350 | 14000 |
| 3 | note | — | 1 | — | 0 | 0 |

Line 3 (note):
- `pricebook_item_id = NULL`
- `description = 'Conduit run extended per field measurement — no additional materials required beyond listed items'`
- `unit_price_cents = 0`, `subtotal_cents = 0`, `total_cents = 0`
- taxability_code = NULL

- subtotal = 44000 (note line = 0), tax = round(44000 × 0.06) = 2640, total = 46640

### G.3 `--reset` Behavior

Add `change_order_line` (before) and `change_order` (after) to the DELETE list in `seed_scenario_quote_to_cash.py` reset block (delete lines first due to FK).

---

## H. Task 5 — `seed_scenario_notifications.py`: New Notification Script (D6)

### H.1 New File

Create `backend/migrations/scripts/seed_scenario_notifications.py`.

### H.2 Schema Reference (MCP-verified)

**`in_app_notification`** columns:
```
id               UUID (gen_random_uuid())  
tenant_id        UUID NOT NULL  
user_id          UUID NOT NULL  
category_id      TEXT NOT NULL  — must match notification_category.code
body             TEXT NOT NULL  
deep_link_target TEXT NOT NULL  — app route for tap navigation
priority         TEXT NOT NULL  (default 'standard') — 'standard' | 'urgent'
read_at          TIMESTAMPTZ (nullable) — NULL = unread
created_at       TIMESTAMPTZ NOT NULL (default now())  
created_by       UUID (nullable)  
```

**`notification_category.code` values**: `background_sync_alerts`, `billing`, `customer_activity`, `field_issues`, `job_activity`, `quote_approvals`, `sync_conflicts`, `system_announcements`

### H.3 Rows to Seed

All rows for owner user `00000000-0000-0000-0000-000000000002` (`dev@pilot.local`).

| # | category_id | body | deep_link_target | priority | read_at | created_at |
|---|---|---|---|---|---|---|
| 1 | `job_activity` | `'Tech assigned to Panel Upgrade job (JOB-SEED-A). Scheduled for tomorrow at 8:00 AM.'` | `'/jobs/JOB-SEED-A'` | `'standard'` | NULL (unread) | ANCHOR_DATE - 2 days |
| 2 | `sync_conflicts` | `'QuickBooks sync conflict on invoice INV-SEED-B: customer name mismatch. Review required before next sync.'` | `'/settings/quickbooks/conflicts'` | `'urgent'` | NULL (unread) | ANCHOR_DATE - 1 day |
| 3 | `billing` | `'Invoice INV-SEED-C is overdue by 14 days. Second dunning reminder sent to customer.'` | `'/invoices/INV-SEED-C'` | `'standard'` | ANCHOR_DATE - 3 days (read) | ANCHOR_DATE - 3 days |
| 4 | `customer_activity` | `'SMS sent to Carlos Rivera: "On my way to your location. ETA 15 minutes." Delivered successfully.'` | `'/communications'` | `'standard'` | ANCHOR_DATE - 5 days (read) | ANCHOR_DATE - 5 days |
| 5 | `field_issues` | `'GPS variance alert: tech location differs from job site by more than 0.5 miles on DISP-002. Review if unexpected.'` | `'/dispatch'` | `'standard'` | ANCHOR_DATE - 7 days (read) | ANCHOR_DATE - 7 days |

**ANCHOR_DATE** = `datetime(2026, 7, 1, tzinfo=timezone.utc)`

### H.4 Script Requirements

The new script must follow all Group D conventions:
- Standard argparse block: `--mode seed|inspect|show`, `--reset`
- `TENANT_ID = '00000000-0000-0000-0000-000000000001'`
- `OWNER_USER_ID = '00000000-0000-0000-0000-000000000002'`
- `ANCHOR_DATE = datetime(2026, 7, 1, tzinfo=timezone.utc)`
- `mode_seed()`, `mode_inspect()`, `mode_show()` functions
- `ON CONFLICT DO NOTHING` — idempotent (the notification rows use gen_random_uuid() so insert is the only natural path; `--reset` deletes by `tenant_id` + `user_id`)
- Register as `"notifications"` in `reset_dev_db.py`

### H.5 `--reset` Behavior

On reset: `DELETE FROM in_app_notification WHERE tenant_id = :tid AND user_id = :owner_id`

---

## I. Task 6 — `user_preference` + `user_setting_override` in `seed_test_tenant.py` (D7)

### I.1 Schema Reference (MCP-verified)

**`user_preference`**:
```
id           UUID NOT NULL  
user_id      UUID NOT NULL  
tenant_id    UUID (nullable)  
preferences  JSONB NOT NULL (default '{}')  
created_at, updated_at  TIMESTAMPTZ NOT NULL  
created_by, updated_by  UUID (nullable)  
```

**`user_setting_override`** (composite PK: tenant_id + user_id + setting_key):
```
tenant_id    UUID NOT NULL  
user_id      UUID NOT NULL  
setting_key  TEXT NOT NULL  — must match platform_setting_catalog.key where allows_user_override=true
value        JSONB NOT NULL  
created_at, updated_at  TIMESTAMPTZ NOT NULL  
created_by, updated_by  UUID (nullable)  
```

**Available `allows_user_override=true` keys** (only 2):
- `background_sync_enabled` (value_type: boolean)
- `voice_persona_tone` (value_type: string)

### I.2 Data to Seed

**`user_preference`** — 1 row for owner user:
```python
UserPreference(
    user_id='00000000-0000-0000-0000-000000000002',
    tenant_id='00000000-0000-0000-0000-000000000001',
    preferences={
        "theme": "light",
        "sidebar_collapsed": False,
        "notification_sounds": True,
        "default_invoice_terms": "net_30",
        "dashboard_layout": "default"
    }
)
```

**`user_setting_override`** — 2 rows for owner user (one per available key):
```python
# Row 1
UserSettingOverride(
    tenant_id='00000000-0000-0000-0000-000000000001',
    user_id='00000000-0000-0000-0000-000000000002',
    setting_key='background_sync_enabled',
    value=True  # JSONB: true
)

# Row 2  
UserSettingOverride(
    tenant_id='00000000-0000-0000-0000-000000000001',
    user_id='00000000-0000-0000-0000-000000000002',
    setting_key='voice_persona_tone',
    value='"professional"'  # JSONB: "professional" (quoted string)
)
```

### I.3 Placement in `seed_test_tenant.py`

Add to the `mode_seed()` function after the existing `user_endpoint` seeding block. Use `INSERT ... ON CONFLICT DO NOTHING` for `user_preference` (by user_id) and `INSERT ... ON CONFLICT (tenant_id, user_id, setting_key) DO NOTHING` for `user_setting_override`.

Add inspect output to `mode_inspect()`:
```
[user_preference] N row(s)  user=dev@pilot.local  keys=theme,sidebar_collapsed,...
[user_setting_override] N row(s)  user=dev@pilot.local  keys=background_sync_enabled,voice_persona_tone
```

### I.4 `--reset` Behavior

The existing `--reset` for `seed_test_tenant.py` wipes and re-seeds Group C. These rows will be naturally re-created on the seed pass. No special handling needed.

---

## J. Task 7 — `README-seed-data.md` Updates (D8, D9, D10)

### J.1 §4 Group A Count Corrections (D9)

Update the following rows in the Group A table:

| Table | Old count | New count | Note |
|---|---|---|---|
| `communication_template` | 15 | 17 | 2 rows added by post-SD-01 migrations |
| `platform_setting_catalog` | 42 | 48 | 6 keys added in later batches |
| `platform_setting` (defaults) | 42 | 49 | Matches catalog expansion |

### J.2 §4 Group D Update for SD-6

Add to the Group D section tables for each script:

- `seed_scenario_quote_to_cash.py`: Add `invoice_line` (N rows), `invoice_line_tax_component` (N rows), `change_order` (2 rows), `change_order_line` (5 rows)
- `seed_scenario_reporting.py`: Add `invoice_line` (N rows), `invoice_line_tax_component` (N rows), `loto_confirmation` (2 rows)
- `seed_scenario_mobile_sync.py`: Add `mobile_sync_owner_escalation` (2 rows)
- New row: `seed_scenario_notifications.py` — `in_app_notification` (5 rows)

### J.3 §8 "What Is NOT Seeded" Additions (D10)

Add these three entries to §8:

| Table | Reason |
|---|---|
| `psp_customer`, `psp_transaction_log` | Requires real Stripe transaction IDs from live webhook events; cannot be fabricated without risk of FK cascade issues |
| `voice_command_log`, `voice_command_entity_link`, `voice_feedback`, `conversation_session`, `conversation_message` | Requires live Voice AI session (Whisper + Ollama on GPU instance); blocked by GPU service dependency |
| `integration_credential`, `integration_sync_log`, `integration_sync_conflict`, `connector_run_log`, `connector_config` | Requires QuickBooks OAuth flow; blocked by external API dependency |

Also add new gotcha to §7 "Known Constraints & Gotchas":

```
### Seed scripts only manage their own inserted data

Each seed script is responsible only for data it has inserted. Do NOT add cleanup logic to 
`reset_dev_db.py` for rows that originated from manual testing or prior debugging sessions. 
If the DB contains spurious rows from testing, clean them with a standalone SQL DELETE statement 
run manually. If a completely clean DB is needed, instantiate from the schema-only SQL file and 
run seed scripts in order (A → B → C → D).
```

### J.4 §9 Scenario Status Registry

Add new row:
```
| `notifications` | `seed_scenario_notifications.py` | dev-only | ✅ Complete (SD-6) |
```

### J.5 §10 Roadmap (D8)

Add SD-5 completion entry and SD-6 active entry:

```markdown
### SD-5 — Group D Scenario Data Expansion ✅ Complete (2026-07-15)

Delivered 2026-07-15. Expanded all 7 Group D scenario scripts for full UI-testable data density:
- Full quote status coverage (10 quotes, all statuses)
- Full invoice status coverage (7 invoices, all statuses) + 5 payments
- Quote → Job → Invoice relational chain
- 3 suppliers with 14 items (Wesco, Graybar, Platt)
- Multi-tech dispatch + cancelled job + 3 availability blocks
- NEC conduit_fill 3rd calculation type
- Mobile sync partial-failure session + conflict + failed events
- Customer comms archived thread

**Test gate**: `pytest` full suite — 4080 passed, 39 skipped, 0 failed.

---

### SD-6 — Deep Seed: Line Items, New Scenarios & README Updates 🔄 Active (2026-07-15)

In progress. Targets:
- `invoice_line` + `invoice_line_tax_component` for all 8 invoices (real pricebook FKs, balanced math)
- `mobile_sync_owner_escalation` (W-12 coverage)
- `loto_confirmation` (2 rows)
- `change_order` + `change_order_line` (2 COs on JOB-900001)
- New `seed_scenario_notifications.py` (5 `in_app_notification` rows)
- `user_preference` + `user_setting_override` in `seed_test_tenant.py`
- README §4, §7, §8, §9, §10 documentation updates
```

---

## K. Pattern Reuse Decisions

| Pattern | Application |
|---|---|
| `ON CONFLICT DO NOTHING` | All INSERTs in all scripts — idempotent seeding |
| ANCHOR_DATE constant | All scripts use `datetime(2026, 7, 1, tzinfo=timezone.utc)` for deterministic timestamps |
| Dynamic FK lookup | Scripts that need invoice → job linkage (loto_confirmation) must query the invoice number to get the job_id at runtime, since those are non-deterministic UUIDs |
| Existing payment_method_id | All new payment rows use `02e3ab2d-27be-41c0-b425-1e2da0b08f7f` (confirmed live, same as SD-5) |
| group D `--reset` convention | Add new tables to `DELETE FROM ... WHERE tenant_id = :tid` block; FK children first |

---

## L. Open Questions Resolved

| Question | Resolution |
|---|---|
| `change_order.status` column — does it exist? | **No.** MCP-confirmed: there is no `status` column on `change_order`. Use `description` text to convey intent. |
| `loto_confirmation` — can "pending" state be seeded? | **No.** No `status` column. Rows = confirmed LOTO. "Pending" is an application-layer concept (job setting + no row). Seed 2 confirmed rows. |
| `invoice_line.source_type` — what value? | Use `'manual'` — the standard value for lines entered by users, not generated by Voice AI. |
| `in_app_notification.category_id` — FK or text? | **Text** — matches `notification_category.code` by string, no FK constraint. Use the code values directly (e.g., `'job_activity'`). |
| `mobile_sync_owner_escalation.conflict_id` — what does it link to? | Links to `mobile_sync_event.id`. No DB-level FK constraint declared. Use the existing conflict event ID: `624b8d17-6c49-402d-b6fc-874a0cd039e1`. |
| `user_setting_override` — what keys are eligible? | Only 2: `background_sync_enabled` (boolean) and `voice_persona_tone` (string). Seed both for owner user. |
| `pricebook_item_version.id` — UUID or bigint? | **bigint** — seed scripts must use Python integer, not UUID string. |
| `invoice_line.pricebook_item_id` — which ID? | The `pricebook_item.id` (UUID), NOT the version ID (bigint). |

---

## M. Schema Discoveries (MCP-verified 2026-07-15)

### M.1 Critical Column Corrections

| Table | Expected | Actual | Impact |
|---|---|---|---|
| `pricebook_item_version` | `unit_price_cents` | `default_unit_price_cents` | All references in invoice_line design use `default_unit_price_cents` |
| `pricebook_item_version` | `id` = UUID | `id` = bigint | Version IDs: 17216, 17217, 17218, 17219, 17220, 22350 |
| `pricebook_item` | `item_type` | No `item_type` column | Taxability comes from `pricebook_item.taxability_code` |
| `tax_rate_version` | `code` | `jurisdiction_code` | Column is `jurisdiction_code`, not `code` |
| `change_order` | `status` column | **Column does not exist** | No pending/approved distinction at DB level |
| `loto_confirmation` | `status` column | **Column does not exist** | Row = confirmed; no pending state possible |
| `notification_category` | `id` UUID | No `id` column — PK is `code` | `in_app_notification.category_id` = the code string |
| `user_preference` | `updated_at` pattern | Has `updated_at` | Must supply `created_at` AND `updated_at` (StandardAuditMixin) |

### M.2 Live Data IDs (Engineer Reference)

**`qco_line_type` IDs** (confirmed live):
- `labor`: `65a92851-3635-4d42-a99c-c40f1ab2e52e`
- `material`: `bb1588c7-e91f-4db8-8497-5d81679bc084`
- `misc`: `c067e242-84dc-4d73-bdce-84aec6d0bd3a`
- `note`: `1dd2f395-e703-4247-a57d-08e90e1ffd90`
- `discount`: `78d28734-eb44-4a16-9d52-1dfd6a34e061`

**`tax_rate_version`** (US-DEFAULT): `id = 1`, `rate_pct = 6.00`

**Conflict mobile_sync_event ID**: `624b8d17-6c49-402d-b6fc-874a0cd039e1`

**Q-CONV-001 job_id**: `60605a9f-e883-42f0-abd8-21a33254a27f`

**Existing payment_method_id**: `02e3ab2d-27be-41c0-b425-1e2da0b08f7f`
