# Task 4-8: Phase 2 - Function & Trigger Optimization (SQL → JSON)

**Reference:** `dev-docs/analysis/phase-4.6-db-schema-sync-2-plan.md` - Phase 2, Tasks 4-8
**Authority (Dual Master):**
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - Golden Master JSON (TO BE UPDATED)
- `dev-docs/db-design/aevofab-db-schema-dump-phase-4.6.sql` - Production SQL Dump (SOURCE OF TRUTH)
**Type:** Phase 2 - Function Optimization
**Priority:** CRITICAL (production reliability)
**Change Type:** JSON_UPDATE (Documentation Only - NO MIGRATIONS)

---

## Context

This is **Phase 4.6 - DB Sync v#2**, Phase 2 - a follow-up reconciliation after completing Phase 4.5. The SQL database contains **battle-tested function logic** that the JSON schema lacks. These optimizations prevent production bugs:

- `clock_timestamp()` prevents timestamp ordering issues in long transactions
- `is_active = true` filters prevent soft-deleted records from affecting totals
- Race condition guards prevent email sync corruption
- Dynamic column checking prevents function failures on tables without `created_by`

**Key Principle:** This is about **reconciliation and documentation**, not new features. **NO DATABASE MIGRATIONS NEEDED** - the database already has the correct implementations.

---

## What Was Completed in Phase 4.5 & Phase 1

**Phase 4.5 Status:** ✅ COMPLETE (March 30 - April 1, 2026)
- ✅ 572/572 tests passing (100%)
- ✅ 100% alignment between physical database and Golden Master JSON achieved
- ✅ All unique, check, and temporal exclusion constraints implemented
- ✅ All 293 triggers verified and functional

**Phase 1 Status:** ✅ COMPLETE (April 2, 2026)
- ✅ `discount_version` table added (Task 1)
- ✅ 4 missing check constraints enforced (Task 2)
- ✅ Email regex standardized to SQL standard (Task 3)
- ✅ 569/569 tests passing (555 baseline + 14 new = 100%)

**Current Baseline:** 569/569 tests passing (100%)

**See:** `dev-docs/analysis/phase-4.5-db-schema-sync-to-design-plan.md` for full Phase 4.5 history

---

## Current Task: Phase 2 - Backport All Function Optimizations from SQL to JSON

**Effort:** 2-3 days
**Gap Reference:** Phase 4.6 Analysis - Section 3 (Function Logic & Code Differences)
**Change Type:** JSON_UPDATE (Documentation Only)

This phase updates the JSON schema to document the battle-tested function implementations that already exist in the production database. **NO database migrations are required** - we're simply aligning the JSON documentation with SQL reality.

### What Needs to Be Fixed

| # | Component | Issue | Direction | Complexity |
|---|-----------|-------|-----------|------------|
| **4** | `set_updated_at()` | JSON uses `now()`, SQL uses `clock_timestamp()` | SQL→JSON | LOW |
| **5** | Total Calculation Functions (3) | JSON sums all lines, SQL filters `is_active = true` | SQL→JSON | MEDIUM |
| **6** | `recalc_invoice_totals_fn()` | JSON uses circular logic, SQL queries payment table | SQL→JSON | MEDIUM |
| **7** | Email Sync Functions (2) | JSON lacks race condition guards with session variables | SQL→JSON | MEDIUM |
| **8** | `guard_created_fields_immutable()` | JSON uses static checks, SQL uses dynamic schema queries | SQL→JSON | LOW |

### Tools Available

You have access to the postgres-local MCP server to query the DB directly, in read-only mode.

---

## ⚠️ BEFORE YOU START - Establish Regression Baseline

**CRITICAL:** Capture the current test baseline BEFORE making ANY changes.

### Step 1: Activate Virtual Environment

```bash
cd backend
source .venv/bin/activate
```

### Step 2: Run ALL Tests (Current Baseline)

```bash
# Run all tests EXCEPT integration tests
pytest --ignore=tests/integration/ tests/ -v

# Concise output to capture baseline count
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed|===)" | tail -5
```

**Record the output:** `569/569 tests passing` (Phase 2 baseline)

### Step 3: Document Your Baseline

**Write down this number before proceeding:**
- Baseline: `569/569` passing

**This is your regression checkpoint. ALL these tests MUST still pass after your work.**

---

## Requirements

### 1. Implementation Details

This phase consists of 5 JSON_UPDATE tasks. Each task updates the JSON schema to match the production SQL logic.

---

#### Task 4: Backport Clock Timestamp Optimization

**Problem:** The JSON schema defines `set_updated_at()` using `now()`, but the SQL database uses `clock_timestamp()`.

**Why This Matters:**
```sql
-- JSON Version (WRONG):
CREATE FUNCTION set_updated_at() RETURNS trigger AS $$
BEGIN
  NEW.updated_at := now();  -- Returns transaction start time
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Problem: If transaction runs for 10 seconds, ALL updates get same timestamp
-- Example: Update 3 invoices in same transaction:
--   Invoice A: updated_at = 2024-01-01 10:00:00
--   Invoice B: updated_at = 2024-01-01 10:00:00  ← SAME (wrong)
--   Invoice C: updated_at = 2024-01-01 10:00:00  ← SAME (wrong)

-- SQL Version (CORRECT):
CREATE FUNCTION set_updated_at() RETURNS trigger AS $$
BEGIN
  NEW.updated_at := clock_timestamp();  -- Returns actual wall clock time
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Result: Each update gets unique timestamp
--   Invoice A: updated_at = 2024-01-01 10:00:00.123
--   Invoice B: updated_at = 2024-01-01 10:00:05.456  ← CORRECT
--   Invoice C: updated_at = 2024-01-01 10:00:08.789  ← CORRECT
```

**SQL Database Reality (What's Actually Working):**
```sql
-- Production SQL (from phase-4.6 dump)
CREATE FUNCTION public.set_updated_at() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
  NEW.updated_at := clock_timestamp();
  RETURN NEW;
END;
$$;
```

**JSON Schema Gap (What's Missing in JSON):**
The `set_updated_at` function in JSON uses `now()` instead of `clock_timestamp()`.

**JSON Schema Fix Required:**
Update the `set_updated_at` function definition in the JSON `functions` array to use `clock_timestamp()`.

**⚠️ IMPORTANT: NO DATABASE MIGRATION NEEDED**
- The database already has the correct implementation
- This is a JSON documentation update only
- No `alembic revision` required
- Verification is comparing JSON to SQL dump

---

#### Task 5: Backport Active Record Filters to Total Calculations

**Problem:** The JSON schema defines total calculation functions that **sum ALL lines**, but the SQL database correctly **filters soft-deleted lines** using `is_active = true`.

**Financial Impact:**
```sql
-- JSON Version (WRONG):
CREATE FUNCTION recalc_quote_totals_fn(quote_id uuid)
RETURNS void AS $$
BEGIN
  UPDATE quote SET
    subtotal_cents = (SELECT COALESCE(SUM(total_cents), 0) FROM quote_line WHERE quote_id = $1),
    -- Problem: Includes soft-deleted lines (is_active = false)
    -- Example: 3 lines ($100, $200, $300 deleted) → subtotal = $600 (wrong, should be $300)
END;
$$ LANGUAGE plpgsql;

-- SQL Version (CORRECT):
CREATE FUNCTION recalc_quote_totals_fn(quote_id uuid)
RETURNS void AS $$
BEGIN
  UPDATE quote SET
    subtotal_cents = (
      SELECT COALESCE(SUM(total_cents), 0)
      FROM quote_line
      WHERE quote_id = $1 AND is_active = true  -- Correct: exclude deleted lines
    ),
END;
$$ LANGUAGE plpgsql;
```

**Affected Functions (3):**
1. `recalc_quote_totals_fn()` - Quote totals
2. `recalc_change_order_totals_fn()` - Change order totals
3. `recalc_invoice_totals_fn()` - Invoice totals

**SQL Database Reality (What's Actually Working):**
All 3 functions in the SQL dump include `AND is_active = true` or `AND l.is_active = true` filters in their SUM queries.

**JSON Schema Gap (What's Missing in JSON):**
The JSON schema versions of these functions lack the `is_active = true` filters.

**JSON Schema Fix Required:**
Update all 3 function bodies in the JSON `functions` array to add `AND is_active = true` to all SUM queries.

**⚠️ IMPORTANT: NO DATABASE MIGRATION NEEDED**
- The database already has the correct implementation
- This is a JSON documentation update only

---

#### Task 6: Backport Invoice Balance Due Calculation

**Problem:** The JSON schema uses a **rudimentary formula** to calculate `balance_due_cents`, but the SQL database **explicitly queries the payment table**.

**Comparison:**

```sql
-- JSON Version (FRAGILE):
UPDATE invoice SET
  balance_due_cents = total_cents - (total_cents - balance_due_cents);
  -- Problem: Relies on existing balance_due_cents (circular logic)

-- SQL Version (CORRECT):
UPDATE invoice SET
  balance_due_cents = total_cents - COALESCE((
    SELECT SUM(amount_cents)
    FROM payment
    WHERE invoice_id = _iid AND status = 'completed'
  ), 0);
  -- Correct: Recalculates from payment table (source of truth)
```

**Why SQL Version is Better:**
- Idempotent (can be called multiple times safely)
- Self-healing (corrects incorrect balance_due_cents)
- Explicit (clear calculation logic)

**SQL Database Reality (What's Actually Working):**
The `recalc_invoice_totals_fn` in the SQL dump calculates balance due by querying the payment table.

**JSON Schema Gap (What's Missing in JSON):**
The JSON schema version uses a circular formula instead of querying payments.

**JSON Schema Fix Required:**
Update the `recalc_invoice_totals_fn` body in JSON to include the payment table query for balance due calculation.

**⚠️ IMPORTANT: NO DATABASE MIGRATION NEEDED**
- The database already has the correct implementation
- This is a JSON documentation update only

---

#### Task 7: Backport Race Condition Guards (Email Sync)

**Problem:** The JSON schema defines `guard_user_endpoint_primary_email_fn()` and `sync_user_email_from_endpoint_fn()` with **standard trigger logic**, but the SQL database uses **PostgreSQL session variables** to prevent race conditions.

**SQL Optimization (Not in JSON):**
```sql
-- SQL Database (production-tested):
CREATE FUNCTION guard_user_endpoint_primary_email_fn()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  -- Skip Highlander check if we're in the middle of auto-demotion
  IF current_setting('aevofab.skip_highlander_check', true) = 'true' THEN
    RETURN NEW;
  END IF;
  
  -- Set flag to prevent recursive trigger firing
  PERFORM set_config('aevofab.skip_sync', 'true', true);
  
  -- Demote existing primary emails
  UPDATE user_endpoint SET is_primary = false
  WHERE user_id = NEW.user_id AND id != NEW.id AND is_primary = true;
  
  -- Clear flag
  PERFORM set_config('aevofab.skip_sync', 'false', true);
  
  RETURN NEW;
END;
$$;
```

**Why This Matters:**
- Prevents infinite trigger loops (trigger calls itself recursively)
- Prevents constraint violations during multi-step updates
- Production-tested (no email sync corruption since deployment)

**SQL Database Reality (What's Actually Working):**
Both `guard_user_endpoint_primary_email_fn` and `sync_user_email_from_endpoint_fn` in the SQL dump use session configuration variables (`set_config()` and `current_setting()`) to prevent race conditions.

**JSON Schema Gap (What's Missing in JSON):**
The JSON schema versions lack the session variable guards.

**JSON Schema Fix Required:**
Update both function bodies in JSON to include the session variable checks and guards.

**⚠️ IMPORTANT: NO DATABASE MIGRATION NEEDED**
- The database already has the correct implementation
- This is a JSON documentation update only

---

#### Task 8: Backport Dynamic Column Checking (Immutability Guard)

**Problem:** The JSON schema defines `guard_created_fields_immutable()` with **static checks** for `created_by`, but the SQL database **dynamically queries the schema** to handle tables without `created_by`.

**Comparison:**

```sql
-- JSON Version (BRITTLE):
IF NEW.created_by IS DISTINCT FROM OLD.created_by THEN
  RAISE EXCEPTION 'created_by is immutable';
END IF;
-- Problem: Fails on tables without created_by column

-- SQL Version (ROBUST):
IF EXISTS (
  SELECT 1 FROM information_schema.columns
  WHERE table_schema = TG_TABLE_SCHEMA
    AND table_name = TG_TABLE_NAME
    AND column_name = 'created_by'
) THEN
  EXECUTE format('
    IF ($1.created_by IS DISTINCT FROM $2.created_by) THEN
      RAISE EXCEPTION ''created_by is immutable'';
    END IF;
  ') USING NEW, OLD;
END IF;
-- Correct: Checks if column exists before validating
```

**SQL Database Reality (What's Actually Working):**
The `guard_created_fields_immutable` function in the SQL dump uses dynamic schema queries to check for column existence before validation.

**JSON Schema Gap (What's Missing in JSON):**
The JSON schema version uses static column references.

**JSON Schema Fix Required:**
Update the `guard_created_fields_immutable` function body in JSON to include dynamic schema checking via `information_schema.columns` query and `EXECUTE format()`.

**⚠️ IMPORTANT: NO DATABASE MIGRATION NEEDED**
- The database already has the correct implementation
- This is a JSON documentation update only

---

### 2. Implementation Order

**For JSON_UPDATE Tasks (Phase 2):**

1. **✅ Establish Regression Baseline** (569/569 tests)
2. **Review SQL Dump for All 5 Tasks**
   - Read `dev-docs/db-design/aevofab-db-schema-dump-phase-4.6.sql`
   - Locate all production function definitions:
     - `set_updated_at`
     - `recalc_quote_totals_fn`
     - `recalc_change_order_totals_fn`
     - `recalc_invoice_totals_fn`
     - `guard_user_endpoint_primary_email_fn`
     - `sync_user_email_from_endpoint_fn`
     - `guard_created_fields_immutable`
3. **Update JSON Schema (All Functions)**
   - Modify `dev-docs/db-design/pilot-db-schema-v2.6h.json`
   - Copy correct logic from SQL dump to JSON for each function
   - Update 7 function definitions total
4. **Document JSON Changes** (see "JSON Change Tracking" section below)
5. **Verify Database (No Changes Expected)**
   ```sql
   -- Confirm database already has correct implementations
   SELECT proname, prosrc FROM pg_proc 
   WHERE proname IN (
     'set_updated_at',
     'recalc_quote_totals_fn',
     'recalc_change_order_totals_fn',
     'recalc_invoice_totals_fn',
     'guard_user_endpoint_primary_email_fn',
     'sync_user_email_from_endpoint_fn',
     'guard_created_fields_immutable'
   );
   ```
6. **Run Existing Tests (Verify No Regression)**
   ```bash
   pytest --ignore=tests/integration/ tests/ -v
   # Expected: 569/569 passing (no change)
   ```
7. **Optional: Add Verification Tests**
   - Only if testing newly documented behavior
   - Keep consistent with existing test patterns
   - Examples:
     - Test that `clock_timestamp()` produces monotonic timestamps
     - Test that soft-deleted lines don't affect totals
     - Test that race condition guards prevent email sync errors
8. **Update Documentation**

---

### 3. Test Requirements

**⚠️ ZERO REGRESSION POLICY:**
- **ALL 569 existing tests MUST still pass**
- **New tests (if added) MUST pass**
- **Target: 100% pass rate**

#### For JSON_UPDATE Tasks

**No New Tests Required (Usually)**
- The database logic already works (proven by 569/569 passing tests)
- This is documentation alignment only

**Optional Verification Tests:**
- Add ONLY if documenting previously untested behavior
- Keep minimal and consistent with existing patterns
- Example test scenarios:
  - Test that `clock_timestamp()` produces monotonic timestamps in long transactions
  - Test that soft-deleted quote lines don't affect quote totals
  - Test that invoice balance due recalculates correctly from payments

**If You Add Tests:**

Create: `backend/tests/test_function_optimizations_phase2.py`

```python
"""
Test Suite: Phase 4.6 Phase 2 - Function Optimization Verification
Tests battle-tested function logic - reconciliation after Phase 4.5
"""
import pytest
import time
from sqlmodel import Session
from sqlalchemy import text

from app.models.quoting import Quote, QuoteLine
from app.models.billing import Invoice, Payment

# ⚠️ Use session.query() NOT session.exec()

class TestClockTimestampOptimization:
    """Verify set_updated_at uses clock_timestamp() not now()"""
    
    def test_updated_at_monotonic_in_long_transaction(self, session: Session, test_tenant, test_user):
        """Updates in same transaction should have distinct timestamps"""
        # This test verifies Task 4
        pass

class TestActiveRecordFilters:
    """Verify total calculations filter is_active = true"""
    
    def test_quote_total_excludes_soft_deleted_lines(self, session: Session, test_tenant, test_user):
        """Soft-deleted quote lines should not affect totals"""
        # This test verifies Task 5
        pass

class TestInvoiceBalanceCalculation:
    """Verify invoice balance queries payment table"""
    
    def test_balance_due_recalculates_from_payments(self, session: Session, test_tenant, test_user):
        """Balance due should recalculate from payment table"""
        # This test verifies Task 6
        pass
```

---

### 4. JSON Change Tracking

**For JSON_UPDATE Tasks:** Provide a summary of all JSON changes for manual review.

**Format:**
```markdown
## JSON Schema Changes for Phase 2 (Tasks 4-8)

**File:** `dev-docs/db-design/pilot-db-schema-v2.6h.json`

### Changes Made:

#### Task 4: Clock Timestamp Optimization

1. **Function: `set_updated_at`**
   - **Location:** Line [X] (approx), `functions` array
   - **Before:** `NEW.updated_at := now();`
   - **After:** `NEW.updated_at := clock_timestamp();`
   - **Reason:** Backport clock_timestamp() optimization from production SQL to ensure monotonic timestamps in long transactions

#### Task 5: Active Record Filters

2. **Function: `recalc_quote_totals_fn`**
   - **Location:** Line [Y], `functions` array
   - **Before:** `WHERE ql.quote_id = _qid`
   - **After:** `WHERE ql.quote_id = _qid AND ql.is_active = true`
   - **Reason:** Add active record filter to exclude soft-deleted lines from totals (production-tested logic)

3. **Function: `recalc_change_order_totals_fn`**
   - **Location:** Line [Z], `functions` array
   - **Before:** `WHERE col.change_order_id = _coid`
   - **After:** `WHERE col.change_order_id = _coid AND col.is_active = true`
   - **Reason:** Add active record filter (production-tested logic)

4. **Function: `recalc_invoice_totals_fn`**
   - **Location:** Line [A], `functions` array
   - **Before:** `WHERE il.invoice_id = _iid`
   - **After:** `WHERE il.invoice_id = _iid AND il.is_active = true`
   - **Reason:** Add active record filter (production-tested logic)

#### Task 6: Invoice Balance Calculation

5. **Function: `recalc_invoice_totals_fn` (balance_due_cents calculation)**
   - **Location:** Line [B], `functions` array, within balance calculation section
   - **Before:** `balance_due_cents = total_cents - (total_cents - balance_due_cents)`
   - **After:** `balance_due_cents = total_cents - COALESCE((SELECT SUM(p.amount_cents) FROM payment p WHERE p.invoice_id = _iid AND p.status = 'completed'), 0)`
   - **Reason:** Replace circular logic with explicit payment table query (idempotent, self-healing)

#### Task 7: Race Condition Guards

6. **Function: `guard_user_endpoint_primary_email_fn`**
   - **Location:** Line [C], `functions` array
   - **Before:** Standard trigger logic without session variables
   - **After:** Added `current_setting('aevofab.skip_highlander_check', true)` check and `set_config('aevofab.skip_sync', ...)` guards
   - **Reason:** Prevent infinite trigger loops and race conditions (production-tested)

7. **Function: `sync_user_email_from_endpoint_fn`**
   - **Location:** Line [D], `functions` array
   - **Before:** Standard trigger logic without session variables
   - **After:** Added session variable checks to prevent recursive firing
   - **Reason:** Coordinate with guard function to prevent email sync corruption (production-tested)

#### Task 8: Dynamic Column Checking

8. **Function: `guard_created_fields_immutable`**
   - **Location:** Line [E], `functions` array
   - **Before:** Static `IF NEW.created_by IS DISTINCT FROM OLD.created_by` check
   - **After:** Added `information_schema.columns` query and `EXECUTE format()` for dynamic column checking
   - **Reason:** Make function robust across all tables (works with or without created_by column)

### Verification:

- [ ] All 8 function changes align with `aevofab-db-schema-dump-phase-4.6.sql`
- [ ] No functional database changes made (JSON doc only)
- [ ] All 569 tests still passing (no regression)
- [ ] Functions verified via postgres-local MCP queries
```

**⚠️ USER REVIEW REQUIRED:**
The founder will manually review these JSON changes against the SQL dump to confirm accuracy.

---

## 🎯 AFTER YOU COMPLETE - Verify No Regressions

**CRITICAL:** After all work is complete, verify the baseline.

### Step 1: Activate Virtual Environment

```bash
cd backend
source .venv/bin/activate
```

### Step 2: Run Full Test Suite

```bash
# Run ALL tests
pytest --ignore=tests/integration/ tests/ -v

# Concise output
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed|===)" | tail -5
```

**Expected:**
- **For JSON_UPDATE tasks (Phase 2):** `569 passed` (no change)
- **If optional verification tests added:** `569 + NEW_TEST_COUNT passed`

### Step 3: Verify 100% Pass Rate

**If ANY tests fail:**
1. Identify failing tests
2. Determine if new or existing tests
3. Fix ALL failures before proceeding
4. Re-run until 100% pass rate

**For JSON_UPDATE tasks:**
- If existing tests fail → Your JSON changes revealed a mismatch (investigate)
- If tests still pass → JSON documentation is correct

---

## Documentation Update

### Update Project Plan Document

**File to Update:** `dev-docs/analysis/phase-4.6-db-schema-sync-2-plan.md`

Find Phase 2, Tasks 4-8 and update with:

```markdown
## 🔧 Phase 2: Function & Trigger Optimization (SQL → JSON)

**Status:** ✅ COMPLETE (YYYY-MM-DD)
**Timeline:** 2-3 days (actual: X days)
**Priority:** CRITICAL (production reliability)

**Implementation Summary:**
- Updated: `pilot-db-schema-v2.6h.json`
- Functions Updated: 7 functions backported from SQL
- Database: No changes (already correct)
- Test Results: 569/569 tests passing (100% - no regression)
- Optional Verification Tests: [X tests added if applicable]

**Key Changes:**
- ✅ Task 4: `set_updated_at` now uses `clock_timestamp()` (prevents timestamp ordering issues)
- ✅ Task 5: Total calculation functions filter `is_active = true` (excludes soft-deleted lines)
- ✅ Task 6: Invoice balance calculation queries payment table (idempotent, self-healing)
- ✅ Task 7: Email sync functions use session variables (prevents race conditions)
- ✅ Task 8: Immutability guard uses dynamic column checking (robust across all tables)

**Verification:**
- All function logic verified against SQL dump
- Zero functional database changes (JSON documentation only)
- All 569 existing tests passing (100% - no regression)
```

---

## Success Criteria

**MUST COMPLETE ALL BEFORE MARKING PHASE 2 AS DONE:**

### For JSON_UPDATE Tasks (Phase 2):
- [ ] **Regression baseline captured** (569/569 tests)
- [ ] **SQL dump reviewed** for all 7 function definitions
- [ ] **JSON schema updated** with all 7 function optimizations
- [ ] **JSON changes documented** for manual review (8 changes total)
- [ ] **Database verification confirms** no changes needed (already correct)
- [ ] **ALL 569 tests still passing** (no regression)
- [ ] **Optional verification tests added** (if applicable)
- [ ] **Functions verified via MCP queries**
- [ ] **Project plan document updated** with Phase 2 completion

### Specific Function Updates:
- [ ] `set_updated_at` uses `clock_timestamp()` (Task 4)
- [ ] `recalc_quote_totals_fn` filters `is_active = true` (Task 5)
- [ ] `recalc_change_order_totals_fn` filters `is_active = true` (Task 5)
- [ ] `recalc_invoice_totals_fn` filters `is_active = true` (Task 5)
- [ ] `recalc_invoice_totals_fn` queries payment table for balance (Task 6)
- [ ] `guard_user_endpoint_primary_email_fn` uses session variables (Task 7)
- [ ] `sync_user_email_from_endpoint_fn` uses session variables (Task 7)
- [ ] `guard_created_fields_immutable` uses dynamic column checking (Task 8)

### For ALL Tasks:
- [ ] **100% test pass rate** - No failing tests
- [ ] **Zero regression** - Baseline maintained (569/569)

---

## Key Files to Review

### Architecture & Design
- `dev-docs/analysis/phase-4.6-db-schema-sync-2-plan.md` - **Phase 2, Tasks 4-8** ⭐
- `dev-docs/analysis/phase-4.6-db-schema-sync-2-analysis.md` - Forensic Analysis (Section 3)
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - **Golden Master JSON (TO UPDATE)**
- `dev-docs/db-design/aevofab-db-schema-dump-phase-4.6.sql` - **Production SQL Dump (SOURCE OF TRUTH)**

### Backend Code (Reference - No Changes Needed)
- `backend/migrations/versions/2026_03_31_1850-6b525454c89c_add_missing_plpgsql_functions.py` - set_updated_at, guard_created_fields_immutable
- `backend/migrations/versions/2026_03_30_1810-6907731fd637_sync_with_golden_master_v2_6h.py` - Total calculation functions
- `backend/migrations/versions/2026_03_31_1954-0a26d3a349c2_rename_user_endpoint_guard_function.py` - guard_user_endpoint_primary_email_fn
- `backend/migrations/versions/2026_03_30_1929-cbf672175f02_fix_user_endpoint_sync_race_condition.py` - sync_user_email_from_endpoint_fn

---

## Risk Assessment

**Data Validation Risk:** NONE
- No database changes being made
- JSON is documentation only

**Regression Risk:** LOW
- No code or database changes
- All existing tests must continue passing
- **Mitigation:** Maintain 569/569 baseline, test after all changes

**JSON Documentation Risk:** LOW
- JSON changes might not perfectly match SQL reality
- **Mitigation:** 
  - Line-by-line comparison with SQL dump
  - Founder manually reviews all JSON changes
  - MCP queries verify database has expected implementations
  - Provide detailed change tracking for review

**Production Impact:** NONE
- Database already has correct logic (production-tested)
- This is documentation catch-up only

---

## Notes

### Important Patterns to Follow
- **Virtual Environment Required:** All Python/pytest commands use `source .venv/bin/activate`
- **Deprecation Warnings:** Use `session.query()` not `session.exec()` in tests
- **Dual Master Strategy:** JSON is documentation authority, SQL dump is runtime authority
- **Phase 2 = JSON Only:** This phase requires NO database migrations
- **Zero Regression Policy:** All 569 existing tests MUST pass after changes

### Phase 2 Specific
- **This is documentation work** - aligning JSON with battle-tested SQL
- **Database is already correct** - all fixes are JSON documentation updates
- **Simpler than Phase 1** - no migrations, no model changes, no tests (unless optional)
- **Function consistency critical** - copy exact logic from SQL dump line-by-line
- **Review is key** - founder must verify all function logic matches SQL

### Function Extraction Tips
- Use `grep -A 50` to extract functions from SQL dump
- Example: `grep -A 50 "CREATE FUNCTION public.set_updated_at" dev-docs/db-design/aevofab-db-schema-dump-phase-4.6.sql`
- Copy function bodies carefully (watch for escaped quotes in JSON)
- Verify function names match exactly (check for `_fn` suffix)

### If You Get Stuck
- Check the SQL dump for exact production definitions (use grep)
- Use `postgres-local` MCP server to query database functions
- Verify JSON changes line-by-line against SQL dump
- Remember: Phase 2 should NOT create migrations
- If tests fail: JSON changes revealed a mismatch (investigate carefully)

---

## Example Task Flow

### For JSON_UPDATE Tasks (Phase 2):

```bash
# 1. Baseline
cd backend
source .venv/bin/activate
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep passed | tail -1
# Record: 569 passed

# 2. Review SQL dump (repeat for each function)
grep -A 50 "CREATE FUNCTION public.set_updated_at" \
  dev-docs/db-design/aevofab-db-schema-dump-phase-4.6.sql

grep -A 100 "CREATE FUNCTION public.recalc_quote_totals_fn" \
  dev-docs/db-design/aevofab-db-schema-dump-phase-4.6.sql

# Repeat for all 7 functions...

# 3. Update JSON schema
# [Edit dev-docs/db-design/pilot-db-schema-v2.6h.json]
# Copy correct logic from SQL dump for all 7 functions

# 4. Document changes
# [Create JSON change summary with 8 detailed changes]

# 5. Verify database (use MCP or psql)
# Confirm functions exist with expected logic
SELECT proname, prosrc FROM pg_proc 
WHERE proname IN (
  'set_updated_at',
  'recalc_quote_totals_fn',
  'recalc_change_order_totals_fn',
  'recalc_invoice_totals_fn',
  'guard_user_endpoint_primary_email_fn',
  'sync_user_email_from_endpoint_fn',
  'guard_created_fields_immutable'
);

# 6. Regression check
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep passed | tail -1
# Expected: 569 passed (no change)

# 7. Optional verification tests
# [Add tests if validating newly documented behavior]
# Example: test_clock_timestamp_monotonic.py

# 8. Update docs
# [Edit phase-4.6-db-schema-sync-2-plan.md - mark Phase 2 complete]
```

---

## Questions to Ask

**Before starting:**
1. Have I captured the 569/569 baseline?
2. Do I understand this is JSON_UPDATE only (no migrations)?
3. Have I located all 7 function definitions in the SQL dump?
4. Do I have the SQL dump open for reference?

**During implementation:**
1. Am I copying the EXACT function body from the SQL dump (not paraphrasing)?
2. Am I watching for escaped quotes when converting to JSON?
3. Am I documenting each change with before/after/reason?
4. Am I verifying function names match exactly (watch for `_fn` suffix)?

**After implementation:**
1. Do I still have 569/569 pass rate (no regression)?
2. Have I provided a clear change list for founder review?
3. Did I verify the database functions match what I documented?
4. Have I updated the project plan document?
5. Are all 8 function changes documented with line numbers?

---

**Ready to Begin!** 🚀

### JSON_UPDATE Phase 2 Checklist:
1. ✅ Capture baseline (569/569)
2. 📖 Review SQL dump for all 7 functions
3. ✏️ Update JSON schema with all optimizations
4. 📋 Document all 8 changes for review
5. ✅ Verify database (no changes needed)
6. 🔄 Run regression tests (expect 569/569)
7. 🧪 Optional: Add verification tests
8. 📚 Update project plan (mark Phase 2 complete)

Remember: Phase 2 is about **documentation alignment**, not database changes. The database already has the correct, battle-tested logic. Keep it simple, maintain test success, and document thoroughly!
