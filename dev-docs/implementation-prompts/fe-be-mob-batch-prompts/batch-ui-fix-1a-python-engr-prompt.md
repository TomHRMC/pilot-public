# Implementation Prompt: UI-FIX-1A — Seed Data Repair + InvoiceResponse Payments

**Mode**: Pilot Python Engineer  
**Batch**: UI-FIX-1A  
**Source plan**: `dev-docs/architecture-design/batch-designs/ui-fix-1-decisions.md` §Implementation Batches  
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-ui-fix-1a-design.md`  
**Estimated session**: 4–5 hours  
**Platform**: Backend only (`backend/`)  
**Frontend companion**: UI-FIX-1B (React Engineer) — depends on this batch completing + OpenAPI regenerated; React Engineer must run `pnpm sync-api-types` before starting UI-FIX-1B

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`dev-docs/architecture-design/pilot-python-engineer-methods.md`** — §13 (Alembic), §8 (Router Design), §5 (Model Design), §16 (Standard Task Workflow)
- **`backend/tests/README-adding-tests.md`** — full document; governs all test file structure, domain markers, and fixture rules

**Critical rules for this batch:**

- **Rule 1**: Never guess column names, data types, or table names. Use `postgres-local` MCP to verify every name before use. **If MCP returns an error → STOP and ask Tom.** The MCP pre-work section below has specific queries — run every single one before touching any seed script.
- **Rule 2**: After modifying `invoices.py` → run `python export_openapi_json.py` to regenerate `openapi.json` and `openapi_schema_map.md`. The React Engineer for UI-FIX-1B depends on the updated OpenAPI spec.
- **Rule 3**: There is **no Alembic migration** in this batch. Do NOT run `alembic revision`. All changes are seed data scripts + one schema + one route handler.
- **Rule 6**: `db.get()` is permanently banned on tenant-scoped models. The `get_invoice()` update must use `db.exec(select(Invoice).where(...))` — see design doc §D for the exact pattern.
- **Rule 7**: `postgres-local` MCP is **read-only verification only**. Never use it to INSERT, UPDATE, or DELETE.
- **Rule 8**: All API error responses MUST follow RFC 7807 Problem Details format. The existing `get_invoice()` already uses this — do not degrade it.
- **Rule 11**: If ANY test fails during your work — even pre-existing — fix it before declaring the batch done.

---

## Pre-Work: Establish Regression Baseline

Before touching any file, capture the current unit-only test baseline:

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=no -q 2>&1 | tail -5
```

Record the exact count: **`X passed, Y failed`**.

> If any tests are already failing before you start: do NOT treat them as "pre-existing" and proceed. Either confirm with Tom (with a documented reason) OR fix the failure before touching any batch files. You may NOT start implementation work while tests are in an unexplained failed state.

---

## Pre-Work: Run MCP Verification Queries

Run **all** of these via `postgres-local` MCP before writing any code. If any query returns unexpected results → **STOP and ask Tom**.

> **MCP Usage Rule**: The `postgres-local` MCP is for **read-only verification only**. Use it to confirm table names, column types, and existing data. Never use it to INSERT, UPDATE, or DELETE.

```sql
-- 1. Confirm job_note table name (could be job_note or job_notes — the design doc is uncertain)
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public' AND table_name LIKE '%note%'
ORDER BY table_name;

-- 2. Get all columns on job_note (or whatever name the above returns)
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'job_note'  -- adjust name per query 1 result
ORDER BY ordinal_position;

-- 3. Get all columns on job_expense
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'job_expense'
ORDER BY ordinal_position;

-- 4. Confirm payment table columns (used in FIX-013-BE)
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'payment'
ORDER BY ordinal_position;

-- 5. Confirm invoice_status codes (needed to seed new invoices with correct status_id)
SELECT id, code, name FROM invoice_status ORDER BY code;

-- 6. Confirm payment_status codes (needed for existing payment rows)
SELECT id, code, name FROM payment_status ORDER BY code;

-- 7. Check current seeded invoices (baseline — what's already there)
SELECT invoice_number, status_id, issued_at, due_at, balance_due_cents
FROM invoice
WHERE tenant_id = '00000000-0000-0000-0000-000000000001'
ORDER BY invoice_number;

-- 8. Confirm which jobs exist and their status (for FIX-005 + FIX-006)
SELECT j.id, j.job_number, js.code AS status_code, j.scheduled_start_at
FROM job j
JOIN job_status js ON j.status_id = js.id
WHERE j.tenant_id = '00000000-0000-0000-0000-000000000001'
ORDER BY j.job_number;

-- 9. Check existing job_assignment rows (should be zero for scheduled jobs — confirms FIX-005 gap)
SELECT job_id, user_id, is_lead
FROM job_assignment
WHERE tenant_id = '00000000-0000-0000-0000-000000000001';

-- 10. Confirm Dev Technician user ID (needed for job_assignment + job_time_entry inserts)
SELECT id, email FROM "user"
WHERE tenant_id = '00000000-0000-0000-0000-000000000001'
ORDER BY email;

-- 11. Confirm current alembic head (verify no unexpected migration state)
SELECT version_num FROM public.alembic_version;

-- 12. Check existing payments for any invoices (to understand current state before FIX-013)
SELECT p.id, p.invoice_id, p.amount_cents, p.paid_at, p.paid_via
FROM payment p
WHERE p.tenant_id = '00000000-0000-0000-0000-000000000001'
ORDER BY p.paid_at;
```

---

## Pre-Work: Read These Source Files

Use `read_file` on each of these before writing any code:

```
backend/migrations/scripts/seed_scenario_reporting.py        ← understand invoice + job seeding patterns
backend/migrations/scripts/seed_scenario_quote_to_cash.py    ← quote title + customer email fields
backend/migrations/scripts/seed_test_tenant.py               ← customer email/phone fields
backend/migrations/scripts/seed_scenario_customer_comms.py   ← SMS body (FIX-003)
backend/migrations/scripts/seed_scenario_notifications.py    ← INV-SEED-B and INV-SEED-C references
backend/api/schemas/schemas.py                               ← InvoiceResponse + PaymentResponse classes
backend/api/routes/invoices.py                               ← get_invoice() handler
backend/app/models/                                          ← locate Payment model file
```

Also run these to find related files:

```bash
# Find which seed script owns job_assignment inserts
grep -rn "job_assignment" backend/migrations/scripts/ --include="*.py"

# Find Payment model location
grep -rn "class Payment" backend/app/models/ --include="*.py"

# Find all customer mobile_phone/email INSERT locations
grep -rn "mobile_phone\|email.*customer\|customer.*email" backend/migrations/scripts/ --include="*.py" -l

# Find job_note INSERT locations (confirm table name)
grep -rn "job_note" backend/migrations/scripts/ --include="*.py"
```

---

## Background / Context

During hands-on UI testing (2026-07-16 to 2026-07-17), Tom identified 8 issues across seed data quality and one backend API gap. This batch fixes all of them:

- **Seed data issues (FIX-003, 005, 006, 007, 008, 011, 012)**: No DB schema changes — these are pure data corrections in existing seed scripts. The seed scripts must be re-run after these fixes to update the dev DB.
- **API gap (FIX-013-BE)**: `InvoiceDetailPage` always renders an empty payment history section because `InvoiceResponse` does not include a `payments` field. Adding this requires a new `PaymentSummaryResponse` Pydantic schema, a field addition to `InvoiceResponse`, and a JOIN in `get_invoice()`.

> **No Alembic migration in this batch.** All DB changes go through seed script re-runs. Do NOT run `alembic revision`.

---

## Task 1 — FIX-011: Rename INV-SEED-* Invoice Numbers

**File**: `backend/migrations/scripts/seed_scenario_reporting.py`  
**Also**: `backend/migrations/scripts/seed_scenario_notifications.py`

After reading both files, rename all `INV-SEED-<letter>` references:

| Old | New |
|---|---|
| `INV-SEED-A` | `INV-900002` |
| `INV-SEED-B` | `INV-900003` |
| `INV-SEED-C` | `INV-900004` |
| `INV-SEED-D` | `INV-900005` |
| `INV-SEED-E` | `INV-900006` |
| `INV-SEED-F` | `INV-900007` |
| `INV-SEED-G` | `INV-900008` |

In `seed_scenario_notifications.py`, update the hardcoded invoice number strings in the notification body text and any deep-link URLs. Use `grep -n "INV-SEED" backend/migrations/scripts/seed_scenario_notifications.py` to find all instances.

> **After this task**: Run `python -m pytest -m unit --tb=short -q 2>&1 | tail -5` — zero regressions expected.

---

## Task 2 — FIX-012: Update Customer Email + Phone

**Files**: `backend/migrations/scripts/seed_scenario_quote_to_cash.py`, `backend/migrations/scripts/seed_test_tenant.py`

Update **every** customer's `email` and `mobile_phone`:

```
email:        info@pilotfortrades.com
mobile_phone: +14105550123    ← E.164 format — required for Telnyx SMS delivery
```

This applies to ALL seeded customers in both files — including those with `NULL` email/phone currently. Also correct the non-E.164 `555-1234` format on Jane Doe (and any other non-E.164 phone numbers you find) to `+14105550123`.

Run `grep -rn "mobile_phone\|customer.*email\|email.*customer" backend/migrations/scripts/ --include="*.py"` to find all INSERT/upsert locations across all seed scripts.

---

## Task 3 — FIX-008: Fix Quote Titles

**File**: `backend/migrations/scripts/seed_scenario_quote_to_cash.py`

Update all seeded quote `title` values. The status keyword must be removed from the title. Use these replacements:

| Quote # | New Title |
|---|---|
| `QUO-900001` | `200A Panel Upgrade — Johnson Residence` |
| `QUO-900002` | `Commercial Panel Assessment — Metro Properties LLC` |
| `QUO-900003` | `GFCI Outlet Installation — Master Bath` |
| `QUO-900004` | `Electrical Service Inspection — Fairview Ave Property` |
| `QUO-900005` | `Full Home Rewire — Smith Renovation` |
| `QUO-900006` | `LED Lighting Upgrade — Office Suite 200` |
| `QUO-900007` | `Solar Panel Tie-In Wiring — Rooftop Array` |
| `QUO-900008` | `Standby Generator Installation — Backup System` |
| `QUO-900009` | `EV Charger Rough-In — Garage 240V Circuit` |
| `QUO-000001` | `Service Call — Outlet Troubleshooting` |
| `QTC-001` | `Electrical Service Call — Initial Estimate` |

Also check for a `QUOTE_SCENARIOS` dict or similar at the top of the file — update the title strings there if that's the source of truth.

---

## Task 4 — FIX-003: Fix SMS Body URL

**File**: `backend/migrations/scripts/seed_scenario_customer_comms.py`

Find the SMS body that reads:
```
"...View and pay at: https://pay.pilotfortrades.com/inv/abc123..."
```

Replace with:
```
"...View and pay at: https://app.pilotfortrades.com/i/EXAMPLE_TOKEN_abc123..."
```

The correct URL structure for invoice payment links is `https://app.pilotfortrades.com/i/{signed_token}`. The seed placeholder `EXAMPLE_TOKEN_abc123` clearly communicates it's a demo token.

---

## Task 5 — FIX-005: Add Job Assignments + Fix Scheduled Dates

**File**: Identified by `grep -rn "job_assignment" backend/migrations/scripts/` — read the owning script before editing.

**Step A — Fix scheduled_start_at dates**: Replace all hardcoded past dates with relative expressions so the dispatch board shows relevant data on any run date. Examples:
- `NOW() + interval '1 day'` (tomorrow morning 09:00 local)
- `NOW() + interval '3 days'`
- `NOW() + interval '5 days'`

For SQL-based seeds, use `NOW() + INTERVAL '1 day'`. For Python-based seeds, use `datetime.now(timezone.utc) + timedelta(days=1)`.

**Step B — Add job_assignment rows**: For every `scheduled` and `in_progress` job, insert one `job_assignment` row:

```python
# job_assignment columns (MCP-verified): id, tenant_id, job_id, user_id, is_lead, is_active, created_at, updated_at
# Assign to Dev Technician — confirm their user_id via MCP query 10 above
{
    "id": <new uuid>,
    "tenant_id": <tenant_uuid>,
    "job_id": <job_uuid>,
    "user_id": <dev_tech_user_id>,   # verified from MCP query 10
    "is_lead": True,
    "is_active": True,
}
```

Use `ON CONFLICT DO NOTHING` on the INSERT.

Seed at least 2–3 jobs with `scheduled_start_at` in the next 7 days so the dispatch board shows a populated schedule immediately.

---

## Task 6 — FIX-006: Add Operational Data to Jobs

**File**: Same seed script(s) as Task 5 (or a new `seed_scenario_operational.py` if the existing file is getting unwieldy — your judgment).

For every `in_progress` and `scheduled` job in seed data, add the following. **Run all MCP verification queries first** to confirm exact column names on `job_time_entry`, `job_expense`, and the note table (name confirmed in MCP query 1).

### A. Time Entries (minimum 2 per job)

`job_time_entry` columns (MCP-verified): `id`, `tenant_id`, `job_id`, `user_id`, `started_at`, `ended_at`, `hours`, `hourly_rate_cents`, `total_cost_cents`, `notes`, `hours_remaining_estimate`

```python
# Example: 4-hour clock-in/out on a scheduled job
{
    "id": <uuid>,
    "tenant_id": <tenant_uuid>,
    "job_id": <job_uuid>,
    "user_id": <dev_tech_user_id>,
    "started_at": <job.scheduled_start_at>,
    "ended_at": <started_at + 4 hours>,
    "hours": 4.0,
    "hourly_rate_cents": 9500,   # $95/hr
    "total_cost_cents": 38000,   # hours * rate
    "notes": "Panel rough-in complete",
    "hours_remaining_estimate": 4.0,
}
```

### B. Expenses (minimum 1–2 per job)

**Important**: Run MCP query 3 to confirm `job_expense` column names before writing any INSERT. Then insert expenses with realistic material costs ($100–$2,000 range).

### C. Job Notes (minimum 1 per job)

**Important**: Run MCP query 1 to confirm the exact table name (`job_note` or `job_notes`), then run query 2 to confirm all column names. Then insert one note per job:

```
"Customer requested outlet moved to east wall — adjusted scope accordingly"
```

### D. At-Risk Scenario (at least 1 job)

Create one job where the sum of `total_cost_cents` across all its `job_time_entry` rows exceeds 80% of the linked quote's `total_cents`. This will trigger the at-risk threshold detection. Also set `hours_remaining_estimate` high enough on one entry to push projected cost over budget.

---

## Task 7 — FIX-007: Add AR Aging Invoices

**File**: `backend/migrations/scripts/seed_scenario_reporting.py`

Add 6 new invoices to cover all AR aging buckets. Use the live `invoice_status` IDs from MCP query 5. Use relative dates so the aging buckets stay accurate on any run date.

| New Invoice # | Status code | issued_at | due_at | balance_due_cents | Notes |
|---|---|---|---|---|---|
| `INV-900009` | `issued` | `NOW() - interval '5 days'` | `NOW() + interval '10 days'` | 85000 | Current (not yet overdue) |
| `INV-900010` | `issued` | `NOW() - interval '20 days'` | `NOW() + interval '5 days'` | 145000 | Current (due soon) |
| `INV-900011` | `issued` | `NOW() - interval '35 days'` | `NOW() - interval '5 days'` | 62500 | 30+ days bucket |
| `INV-900012` | `issued` | `NOW() - interval '55 days'` | `NOW() - interval '25 days'` | 189000 | 60+ days bucket |
| `INV-900013` | `issued` | `NOW() - interval '95 days'` | `NOW() - interval '65 days'` | 340000 | 90+ days bucket |
| `INV-900014` | `partial` | `NOW() - interval '45 days'` | `NOW() - interval '15 days'` | 52000 | Partial — has a payment recorded |

All new invoices must have valid `customer_id`, `site_id`, and `tenant_id` pointing to existing seed data. Use `ON CONFLICT DO NOTHING`.

For `INV-900014` (partial), also insert one `payment` row with `amount_cents = 50000` (partial payment), `paid_via = 'check'`, `paid_at = NOW() - interval '30 days'`, and the correct `status_id` for `succeeded`.

---

## Task 8 — FIX-013-BE Part A: Add PaymentSummaryResponse Schema

**File**: `backend/api/schemas/schemas.py`

After reading the file, add `PaymentSummaryResponse` immediately before the `InvoiceResponse` class (around line 540). Use the exact column names verified by MCP query 4:

```python
class PaymentSummaryResponse(BaseModel):
    """Payment summary embedded in InvoiceResponse — not standalone."""

    model_config = ConfigDict(from_attributes=True, extra="ignore")

    id: UUID
    amount_cents: int
    paid_at: datetime | None
    paid_via: str | None
    psp_provider: str | None
    customer_payment_comment: str | None
    status_id: UUID
```

Then add `payments` to `InvoiceResponse` **after** `lines`:

```python
lines: list[InvoiceLineResponse]
payments: list[PaymentSummaryResponse] = []   # ← ADD THIS LINE
```

---

## Task 9 — FIX-013-BE Part B: Update get_invoice() Handler

**File**: `backend/api/routes/invoices.py`

Read the full `get_invoice()` function (approximately line 1081) before modifying. Also read the `/test` variant if it exists.

The change adds a `payment` JOIN after the invoice is fetched. Read the existing import block at the top of the file — add the `Payment` model import if it's not already there.

After fetching and verifying the invoice (keep the existing 404 guard logic intact — do not restructure it), add:

```python
# Fetch payments for this invoice (tenant-scoped)
payments = db.exec(
    select(Payment)
    .where(Payment.invoice_id == invoice.id)
    .where(Payment.tenant_id == current_user.tenant_id)
    .where(Payment.is_active == True)
    .order_by(Payment.paid_at.desc().nulls_last())
).all()
```

Then build the response with payments populated. The exact approach depends on how the existing handler builds its response — read it first. The `InvoiceResponse` schema uses `model_config = ConfigDict(from_attributes=True)`, so you may need to construct the response, then assign the payments list to the `payments` attribute before returning.

Also update the `/test` variant handler if it has its own implementation.

---

## Task 10 — Regenerate OpenAPI

After Tasks 8 and 9 are complete and all unit tests pass:

```bash
cd <repo>/backend
source .venv/bin/activate
python export_openapi_json.py
```

Verify the new `PaymentSummaryResponse` schema and `payments` field appear in the response:

```bash
grep -A 20 "payments" backend/openapi_schema_map.md | head -30
grep -A 5 "PaymentSummaryResponse" backend/openapi_schema_map.md
```

Also verify the existing invoice endpoints still appear correctly:
```bash
grep -A 5 "GET /api/v1/invoices/{invoice_id}" backend/openapi_schema_map.md
```

---

## Test Requirements

Per `backend/tests/README-adding-tests.md`:

**Required new test file**: `backend/tests/domains/invoicing_billing/test_invoice_payments_embedded.py`

**Every new test file MUST**:
- Declare `pytestmark` with both domain marker and `pytest.mark.unit`:
  ```python
  pytestmark = [
      pytest.mark.domain_invoicing_billing,
      pytest.mark.unit,
  ]
  ```
- Use `client` fixture (never module-level `TestClient`)
- Use `test_tenant`, `test_user`, `mock_cognito_jwt` fixtures (no hardcoded UUIDs)
- Assert by inserted IDs only — never `assert len(all_rows) == N`

**Minimum test coverage for FIX-013-BE**:

```python
# Test 1: GET /api/v1/invoices/{id} returns payments array (even if empty)
def test_get_invoice_includes_payments_field(client, test_tenant, mock_cognito_jwt):
    # Create invoice via /test endpoint, fetch it, assert response has 'payments' key
    # and it's a list (empty is fine here)
    ...

# Test 2: Payments are populated when they exist
def test_get_invoice_includes_existing_payments(client, test_tenant, mock_cognito_jwt):
    # Create invoice, record a payment, fetch the invoice detail
    # Assert invoice.payments has exactly 1 entry with correct amount_cents
    # (scope by the inserted payment ID — never assert total list count)
    ...

# Test 3: Payments from OTHER invoices are NOT included (tenant scoping)
def test_get_invoice_payments_tenant_scoped(client, tenant_a, tenant_b, user_tenant_a, user_tenant_b):
    # Create invoice + payment in tenant_a; fetch from tenant_b's perspective
    # Assert 404 (can't see the other tenant's invoice at all)
    ...
```

**No new tests required for seed data changes** (Tasks 1–7 are data-only; they're validated by running the seed scripts and visually verifying in the UI).

---

## Final Verification

### Phase 1 — Unit Tests Only (run after each task group during development)

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=short -q 2>&1 | tail -10
```

Run this after completing Tasks 8–9 and after adding the new test file. All unit tests must pass before moving forward.

### Phase 2 — Full Suite (run once, at the very end, before DoD sign-off)

```bash
cd <repo>/backend
source .venv/bin/activate

# Full suite including integration tests
python -m pytest --tb=short -q 2>&1 | tail -10

# Invoice domain spot check
python -m pytest tests/domains/invoicing_billing/ -v 2>&1 | tail -20

# Verify OpenAPI regenerated correctly
grep -A 5 "PaymentSummaryResponse" backend/openapi_schema_map.md
grep -A 15 '"payments"' backend/openapi_schema_map.md | head -20

echo "=== UI-FIX-1A FINAL VERIFICATION COMPLETE ==="
```

> **Any failure in either phase must be fixed before the batch is declared done.** There is no "pre-existing failure" exception without explicit written confirmation from Tom.

---

## Definition of Done

Update `dev-docs/architecture-design/batch-designs/ui-fix-1-decisions.md` §Implementation Batches when each item is done:

- [ ] Pre-modification regression baseline captured (`X passed, Y failed`) using `pytest -m unit`
- [ ] Zero pre-existing unit failures confirmed before starting work (or confirmed with Tom)
- [ ] All 12 MCP pre-work queries run — results reviewed (stop if unexpected)
- [ ] All mandatory source files read before writing any code
- [ ] `grep` commands run to locate owning scripts for `job_assignment`, `Payment` model, `mobile_phone`, `job_note`
- [ ] **Task 1**: All `INV-SEED-*` numbers renamed to `INV-9*` in `seed_scenario_reporting.py` + `seed_scenario_notifications.py`
- [ ] **Task 2**: All customer `email` → `info@pilotfortrades.com` and `mobile_phone` → `+14105550123` across all seed scripts
- [ ] **Task 3**: All quote titles updated — no status keywords in title strings
- [ ] **Task 4**: SMS body URL corrected to `https://app.pilotfortrades.com/i/EXAMPLE_TOKEN_abc123`
- [ ] **Task 5A**: All `scheduled_start_at` dates use relative expressions (`NOW() + interval`)
- [ ] **Task 5B**: `job_assignment` rows added for all `scheduled`/`in_progress` jobs
- [ ] **Task 6A**: `job_time_entry` rows added (≥2 per job) for all `in_progress`/`scheduled` jobs
- [ ] **Task 6B**: `job_expense` rows added (≥1 per job) — column names MCP-verified
- [ ] **Task 6C**: job note rows added (≥1 per job) — exact table name MCP-verified
- [ ] **Task 6D**: At-risk scenario job seeded (labor cost > 80% of quote total)
- [ ] **Task 7**: 6 new invoices added covering Current, 30+, 60+, 90+, Partial buckets
- [ ] **Task 8**: `PaymentSummaryResponse` added to `schemas.py`; `payments: list[PaymentSummaryResponse] = []` added to `InvoiceResponse`
- [ ] **Task 9**: `get_invoice()` updated to JOIN `payment` table and return payments; `/test` variant also updated if it has its own implementation
- [ ] All new API errors (if any) follow RFC 7807 Problem Details format
- [ ] New test file `test_invoice_payments_embedded.py` created with 3 test cases
- [ ] All new tests use `pytestmark` with `domain_invoicing_billing` + `pytest.mark.unit`
- [ ] No module-level `TestClient` in any test file
- [ ] **Task 10**: `python export_openapi_json.py` run — `PaymentSummaryResponse` + `payments` field visible in `openapi_schema_map.md`
- [ ] **Phase 1**: All unit tests pass (`pytest -m unit`) — zero failures
- [ ] **Phase 2**: Full test suite passes (`pytest`) — zero failures including integration
- [ ] Final test count (before → after) documented
- [ ] Seed scripts re-run against dev DB and visually verified in UI (dispatch board shows assignments, invoice detail shows payment history, AR aging has data in all buckets)
- [ ] Completion Summary added to `ui-fix-1-decisions.md` §Implementation Batches
- [ ] `ui-fix-1-decisions.md` — UI-FIX-1A row updated to ✅ Complete

---

## Handoff Instructions (After UI-FIX-1A is Done)

Before handing off to the React Engineer (UI-FIX-1B):

1. Run `python export_openapi_json.py` — confirm it succeeds
2. Commit `backend/openapi.json` and `backend/openapi_schema_map.md` in the same commit as the code changes
3. Notify the React Engineer: **"UI-FIX-1A is complete. Run `pnpm sync-api-types` before starting UI-FIX-1B."**

The React Engineer's `useInvoice` hook will need to be updated to include `payments: PaymentEntry[]` — the type will be available via `@pilot/shared-types` after `pnpm sync-api-types`.

---

## Completion Summary

After all Definition of Done items are complete:

1. Add a **Completion Summary** to `ui-fix-1-decisions.md` §Implementation Batches using the format below.
2. Update the `UI-FIX-1A` row in the Batch Overview table to ✅ Complete.

```markdown
### UI-FIX-1A — Seed Data Repair + InvoiceResponse Payments: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot Python Engineer
**Baseline**: X passed, Y failed
**Final**: X+N passed, Y failed (+N new tests)

#### What Was Accomplished

- [Brief description of each fix implemented]
- FIX-013-BE: PaymentSummaryResponse schema added; InvoiceResponse.payments field added; get_invoice() now JOINs payment table

#### Files Changed / Created

| File | Action |
|---|---|
| `backend/migrations/scripts/seed_scenario_reporting.py` | Updated — INV-SEED-* renamed, AR aging invoices added, job assignments + time entries + expenses + notes added |
| `backend/migrations/scripts/seed_scenario_quote_to_cash.py` | Updated — customer email/phone + quote titles |
| `backend/migrations/scripts/seed_test_tenant.py` | Updated — customer email/phone |
| `backend/migrations/scripts/seed_scenario_customer_comms.py` | Updated — SMS URL corrected |
| `backend/migrations/scripts/seed_scenario_notifications.py` | Updated — INV-SEED-* cross-references renamed |
| `backend/api/schemas/schemas.py` | Updated — PaymentSummaryResponse added; InvoiceResponse.payments added |
| `backend/api/routes/invoices.py` | Updated — get_invoice() JOIN + payments populated |
| `backend/openapi.json` | Regenerated |
| `backend/openapi_schema_map.md` | Regenerated |
| `backend/tests/domains/invoicing_billing/test_invoice_payments_embedded.py` | Created — 3 unit tests |

#### Tests Added

| Test File | Domain | Tests | All Pass |
|---|---|---|---|
| `tests/domains/invoicing_billing/test_invoice_payments_embedded.py` | `domain_invoicing_billing` | 3 | ✅ |
```
