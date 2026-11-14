# Task 11: Partial Indexes (High-Value Performance Wins)

**Reference:** `dev-docs/analysis/phase-4.5-db-schema-sync-to-design-plan.md` - Task 11
**Authority:** `dev-docs/db-design/pilot-db-schema-v2.6h.json`
**Type:** Phase 4 - Advanced Indexing & Temporal Logic
**Priority:** MEDIUM

---

## Context

We're building AevoFab AI, an AI-powered SaaS platform for electrical contractors with voice-controlled quoting and QuickBooks integration. Following the 80/20 rule to reach MVP quickly.

This is a **Phase 4 performance optimization task** to achieve 100% alignment between our SQLModel implementations and the Golden Master Database Schema (v2.6h JSON). This is NOT a new feature - it's surgical additions of highly-tuned partial indexes that dramatically speed up common queries.

---

## Completed So Far

**Phase 1: Foundation (COMPLETE - March 30-31, 2026):**
- ✅ Task 1: Timezone enforcement (9 columns fixed)
- ✅ Task 2: Citext conversion for user email
- ✅ Task 3: QuickBooks identity rules on Customer table

**Phase 2: Functions & Triggers (COMPLETE - March 31, 2026):**
- ✅ Task 4: Missing PL/pgSQL functions (3 functions + 200 triggers)
- ✅ Task 5: Function naming standard compliance
- ✅ Task 6: Audit trigger coverage (85 audit triggers)
- ✅ Task 7: Operational trigger verification (293 total triggers)

**Phase 3: Data Integrity (COMPLETE - April 1, 2026):**
- ✅ Task 8: Missing unique constraints (4/4 complete)
- ✅ Task 9: Missing check constraints (9/9 complete)
- ✅ Task 10: Missing temporal exclusion constraints (6/6 complete)

**Current Test Baseline:** 535 tests passing (100%)
**See:** `dev-docs/analysis/phase-4.5-db-schema-sync-to-design-plan.md` for full context

---

## Current Task: Partial Indexes (High-Value Performance Wins)

**Effort:** 0.5 days
**Gap Reference:** Analysis Section 4 - Missing Indexes (Partial)

The Golden Master specifies highly-tuned partial indexes that dramatically speed up common queries. These indexes only include rows matching specific conditions, making them smaller and faster than full-table indexes. Currently missing 2 critical partial indexes for invoice aging reports and unbilled expense tracking.

### What Needs to Be Fixed

| # | Index Name | Purpose | Impact | Complexity |
|---|------------|---------|--------|------------|
| **1** | `idx_invoice_balance` | Speed up "unpaid invoices" query for collections aging reports | Query time: 500ms → 10ms (50x faster) | LOW |
| **2** | `idx_job_expense_unbilled` | Speed up "expenses not yet invoiced" query for billing workflow | Query time: 1s → 10ms (100x faster) | LOW |

---

## ⚠️ BEFORE YOU START - Establish Regression Baseline

**CRITICAL:** You MUST capture the current test baseline BEFORE making ANY changes. This ensures we can detect regressions.

### Step 1: Activate Virtual Environment

All Python and pytest commands MUST be run in the virtual environment:

```bash
cd backend
source .venv/bin/activate
```

### Step 2: Run Regression Tests (Non-Integration)

```bash
# Run all tests EXCEPT integration tests
pytest --ignore=tests/integration/ tests/ -v

# Concise output to capture baseline count
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed|===)" | tail -5
```

**Record the output:** `[BASELINE_NON_INTEGRATION_COUNT] tests passing`

Example output:
```
========================== 535 passed in 45.23s ==========================
```

### Step 3: Run ALL Tests (Including Integration)

```bash
# Run ALL tests
pytest tests/ -v

# Concise output
pytest tests/ -v 2>&1 | grep -E "(passed|failed|===)" | tail -5
```

**Record the output:** `[BASELINE_TOTAL_COUNT] tests passing`

Example output:
```
========================== 562 passed in 62.11s ==========================
```

### Step 4: Document Your Baseline

**Write down these numbers before proceeding:**
- Non-Integration Baseline: `___/___` passing
- Total Tests Baseline: `___/___` passing

**These are your regression checkpoints. All these tests MUST still pass after your work.**

---

## Requirements

### 1. Implementation Details

#### Gap 1: `idx_invoice_balance` - Aging Report Optimization

**Problem:** The "unpaid invoices" query (critical for collections) currently performs a sequential scan of ALL invoices (~10,000 rows). This causes slow aging reports (p95: ~500ms).

**Current Query Performance:**
```sql
-- Without index: Sequential scan of ALL invoices
SELECT * FROM invoice WHERE balance_due_cents > 0;
-- Query time: ~500ms (p95)
```

**Partial Index Solution:**
```sql
CREATE INDEX CONCURRENTLY idx_invoice_balance 
ON invoice (balance_due_cents) 
WHERE balance_due_cents > 0;
```

**Why This Works:**
- Only indexes invoices with outstanding balances (typically 20-30% of all invoices)
- Smaller index = faster lookups and less storage
- `CONCURRENTLY` prevents table lock during creation (online operation)

**Expected Performance:**
- Query time: ~10ms (p95) - **50x faster**
- Index size: <10% of table size

**Migration SQL:**
```sql
-- Create partial index on invoice.balance_due_cents
-- Only indexes rows where balance_due_cents > 0 (unpaid invoices)
CREATE INDEX CONCURRENTLY idx_invoice_balance 
ON invoice (balance_due_cents) 
WHERE balance_due_cents > 0;
```

**Downgrade SQL:**
```sql
-- Drop the partial index
DROP INDEX CONCURRENTLY IF EXISTS idx_invoice_balance;
```

---

#### Gap 2: `idx_job_expense_unbilled` - Unbilled Expense Tracking

**Problem:** The "expenses not yet invoiced" query (critical for billing workflow) currently scans all job expenses. This causes timeout issues when processing billing runs (p95: ~1s).

**Current Query Performance:**
```sql
-- Without index: Full table scan
SELECT * FROM job_expense 
WHERE is_billable = true 
  AND invoice_line_id IS NULL;
-- Query time: ~1s (p95)
```

**Partial Index Solution:**
```sql
CREATE INDEX CONCURRENTLY idx_job_expense_unbilled 
ON job_expense (job_id) 
WHERE is_billable = true AND invoice_line_id IS NULL;
```

**Why This Works:**
- Only indexes billable expenses that haven't been invoiced yet
- Dramatically reduces index size (typically 5-10% of total expenses)
- Enables fast lookup by job_id for billing workflow

**Expected Performance:**
- Query time: ~10ms (p95) - **100x faster**
- Index size: <5% of table size

**Migration SQL:**
```sql
-- Create partial index on job_expense for unbilled expenses
-- Only indexes rows where is_billable = true AND invoice_line_id IS NULL
CREATE INDEX CONCURRENTLY idx_job_expense_unbilled 
ON job_expense (job_id) 
WHERE is_billable = true AND invoice_line_id IS NULL;
```

**Downgrade SQL:**
```sql
-- Drop the partial index
DROP INDEX CONCURRENTLY IF EXISTS idx_job_expense_unbilled;
```

---

### 2. Database Query Tools

**You have access to the postgres-local MCP server for direct database queries:**

```python
# Example: Check current query performance (EXPLAIN ANALYZE)
await mcp__postgres_local__query({
    "sql": """
        EXPLAIN ANALYZE 
        SELECT * FROM invoice WHERE balance_due_cents > 0;
    """
})
```

Use this tool to:
- Benchmark query performance BEFORE index creation
- Verify indexes are created AFTER migration
- Confirm queries use the new indexes (look for "Index Scan using idx_invoice_balance")
- Monitor index size

**Helpful Verification Queries:**

```sql
-- Verify indexes exist
SELECT 
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE indexname IN ('idx_invoice_balance', 'idx_job_expense_unbilled')
ORDER BY indexname;

-- Check index size
SELECT 
    indexname,
    pg_size_pretty(pg_relation_size(indexrelid)) AS index_size,
    idx_scan AS times_used
FROM pg_stat_user_indexes
WHERE indexname IN ('idx_invoice_balance', 'idx_job_expense_unbilled')
ORDER BY indexname;
```

---

### 3. Implementation Order

Execute in this exact sequence:

1. **✅ Establish Regression Baseline** (see "Before You Start" section above)

2. **Pre-Migration Performance Benchmark**
   - Run EXPLAIN ANALYZE on both queries (aging report, unbilled expenses)
   - Record current query plans and execution times
   - Document baseline performance (p95 latency)

3. **Create Manual Alembic Migration**
   ```bash
   cd backend
   source .venv/bin/activate
   alembic revision -m "add_partial_indexes_for_invoice_and_expense_queries_task11"
   ```
   
   **Note:** Cannot use `--autogenerate` because SQLModel doesn't support index definitions in models. This must be a manual migration.

4. **Edit Migration File**
   - Add both `CREATE INDEX CONCURRENTLY` statements to `upgrade()`
   - Add both `DROP INDEX CONCURRENTLY` statements to `downgrade()`
   - **Important:** Use `CONCURRENTLY` to avoid table locks (critical for production deployments)

5. **Apply Migration**
   ```bash
   alembic upgrade head
   ```
   
   **Expected:** Migration completes without locking tables (online operation)

6. **Post-Migration Performance Verification**
   - Run EXPLAIN ANALYZE on both queries again
   - Verify query plans now use index scans (not sequential scans)
   - Measure new p95 latency
   - Confirm 50-100x speedup achieved

7. **Create Test Suite**
   - Create `backend/tests/test_partial_indexes_task11.py`
   - Write performance and functional tests (see Test Requirements below)
   - **CRITICAL:** Use `session.query()` NOT `session.exec()` to avoid deprecation warnings

8. **Run New Tests**
   ```bash
   pytest tests/test_partial_indexes_task11.py -v
   ```

9. **Run Regression Tests** (see "After You Complete" section below)

10. **Update Documentation** (see Documentation Update section below)

---

### 4. Test Requirements

**⚠️ ZERO FAILING TESTS POLICY:**
- **ALL 535 existing tests MUST still pass** (baseline cannot regress)
- **ALL new tests MUST pass** (schema sync verification)
- **Target: 543/543 passing (100%)** (535 baseline + 8 new tests)

**Test File:** `backend/tests/test_partial_indexes_task11.py`

**Test Standards:**

```python
"""
Test Suite: Phase 4 Task 11 - Partial Indexes (Performance)
Tests partial index creation and query performance from Golden Master v2.6h
"""
import pytest
from sqlmodel import Session, select
from sqlalchemy import text

from app.models.billing import Invoice
from app.models.fulfillment import JobExpense


class TestInvoicePartialIndex:
    """Test idx_invoice_balance partial index for aging reports"""
    
    def test_idx_invoice_balance_exists(self, session: Session):
        """Verify idx_invoice_balance index exists in database"""
        result = session.execute(text("""
            SELECT indexname 
            FROM pg_indexes 
            WHERE indexname = 'idx_invoice_balance'
        """))
        index = result.fetchone()
        assert index is not None, "idx_invoice_balance index should exist"
    
    def test_invoice_balance_query_uses_index(self, session: Session, test_tenant, test_customer):
        """Verify unpaid invoice query uses the partial index"""
        # Create test invoice with balance due
        invoice = Invoice(
            tenant_id=test_tenant.id,
            customer_id=test_customer.id,
            invoice_number="INV-TEST-001",
            balance_due_cents=10000,
            # ... other required fields ...
        )
        session.add(invoice)
        session.commit()
        
        # Query for unpaid invoices
        result = session.execute(text("""
            EXPLAIN SELECT * FROM invoice WHERE balance_due_cents > 0
        """))
        plan = " ".join([row[0] for row in result.fetchall()])
        
        # Verify index is used (look for "Index Scan using idx_invoice_balance")
        assert "idx_invoice_balance" in plan or "Index Scan" in plan, \
            "Query should use idx_invoice_balance index"
    
    def test_aging_report_query_performance(self, session: Session, test_tenant, test_customer):
        """Verify aging report query returns unpaid invoices correctly"""
        # Create mix of paid and unpaid invoices
        paid_invoice = Invoice(
            tenant_id=test_tenant.id,
            customer_id=test_customer.id,
            invoice_number="INV-PAID-001",
            balance_due_cents=0,  # Fully paid
            # ... other required fields ...
        )
        unpaid_invoice = Invoice(
            tenant_id=test_tenant.id,
            customer_id=test_customer.id,
            invoice_number="INV-UNPAID-001",
            balance_due_cents=5000,  # Outstanding balance
            # ... other required fields ...
        )
        session.add_all([paid_invoice, unpaid_invoice])
        session.commit()
        
        # Query using index
        unpaid = session.query(Invoice).filter(Invoice.balance_due_cents > 0).all()
        
        assert len(unpaid) == 1
        assert unpaid[0].invoice_number == "INV-UNPAID-001"


class TestJobExpensePartialIndex:
    """Test idx_job_expense_unbilled partial index for billing workflow"""
    
    def test_idx_job_expense_unbilled_exists(self, session: Session):
        """Verify idx_job_expense_unbilled index exists in database"""
        result = session.execute(text("""
            SELECT indexname 
            FROM pg_indexes 
            WHERE indexname = 'idx_job_expense_unbilled'
        """))
        index = result.fetchone()
        assert index is not None, "idx_job_expense_unbilled index should exist"
    
    def test_unbilled_expense_query_uses_index(self, session: Session, test_tenant, test_job):
        """Verify unbilled expense query uses the partial index"""
        # Create unbilled expense
        expense = JobExpense(
            tenant_id=test_tenant.id,
            job_id=test_job.id,
            is_billable=True,
            invoice_line_id=None,  # Not yet invoiced
            # ... other required fields ...
        )
        session.add(expense)
        session.commit()
        
        # Query for unbilled expenses
        result = session.execute(text("""
            EXPLAIN SELECT * FROM job_expense 
            WHERE is_billable = true AND invoice_line_id IS NULL
        """))
        plan = " ".join([row[0] for row in result.fetchall()])
        
        # Verify index is considered (may use bitmap scan or index scan)
        assert "idx_job_expense_unbilled" in plan or "Index" in plan, \
            "Query should consider idx_job_expense_unbilled index"
    
    def test_unbilled_expense_query_correctness(self, session: Session, test_tenant, test_job):
        """Verify unbilled expense query returns correct results"""
        # Create mix of expenses
        billed_expense = JobExpense(
            tenant_id=test_tenant.id,
            job_id=test_job.id,
            is_billable=True,
            invoice_line_id=123,  # Already invoiced
            # ... other required fields ...
        )
        unbilled_expense = JobExpense(
            tenant_id=test_tenant.id,
            job_id=test_job.id,
            is_billable=True,
            invoice_line_id=None,  # Not yet invoiced
            # ... other required fields ...
        )
        non_billable = JobExpense(
            tenant_id=test_tenant.id,
            job_id=test_job.id,
            is_billable=False,
            invoice_line_id=None,
            # ... other required fields ...
        )
        session.add_all([billed_expense, unbilled_expense, non_billable])
        session.commit()
        
        # Query for unbilled expenses
        unbilled = session.query(JobExpense).filter(
            JobExpense.is_billable == True,
            JobExpense.invoice_line_id == None
        ).all()
        
        assert len(unbilled) == 1
        assert unbilled[0].id == unbilled_expense.id


class TestIndexSizeAndPerformance:
    """Test index size and performance characteristics"""
    
    def test_index_sizes_are_reasonable(self, session: Session):
        """Verify partial indexes are smaller than full-table indexes"""
        result = session.execute(text("""
            SELECT 
                i.indexname,
                pg_size_pretty(pg_relation_size(i.indexrelid)) AS index_size,
                pg_size_pretty(pg_relation_size(t.tablename::regclass)) AS table_size
            FROM pg_stat_user_indexes i
            JOIN pg_tables t ON t.tablename = i.relname
            WHERE i.indexname IN ('idx_invoice_balance', 'idx_job_expense_unbilled')
        """))
        
        for row in result.fetchall():
            index_name, index_size, table_size = row
            # Partial indexes should be significantly smaller than tables
            # This is a smoke test - actual sizes will vary
            assert index_size is not None, f"{index_name} should have a size"
            assert table_size is not None, f"Table for {index_name} should have a size"
```

**Required Test Coverage (Minimum 8 Tests):**
- [ ] Index existence verification (2 tests - one per index)
- [ ] Query plan verification (2 tests - confirm indexes are used)
- [ ] Query correctness tests (2 tests - verify results are accurate)
- [ ] Performance smoke tests (1 test - verify indexes are reasonable size)
- [ ] Integration test (1 test - end-to-end aging report or billing workflow)

**Test Fixtures:**
Review `backend/tests/conftest.py` for available fixtures:
- `session` - Database session with auto-rollback
- `test_tenant` - Test tenant record
- `test_user` - Test user record
- `test_customer` - Test customer record
- `test_job` - Test job record (may need to add this fixture)
- Add new fixtures if needed following existing patterns

---

### 5. Database Verification

**After Migration Applied:**

Use the MCP server or psql to verify indexes:

```sql
-- Verify indexes exist
SELECT 
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE indexname IN ('idx_invoice_balance', 'idx_job_expense_unbilled')
ORDER BY indexname;

-- Expected output:
-- idx_invoice_balance | invoice | CREATE INDEX idx_invoice_balance ON invoice USING btree (balance_due_cents) WHERE (balance_due_cents > 0)
-- idx_job_expense_unbilled | job_expense | CREATE INDEX idx_job_expense_unbilled ON job_expense USING btree (job_id) WHERE (is_billable = true AND invoice_line_id IS NULL)
```

**Performance Benchmark:**

```sql
-- Before index: Sequential scan
EXPLAIN ANALYZE SELECT * FROM invoice WHERE balance_due_cents > 0;
-- Look for: Seq Scan on invoice (cost=X..Y rows=Z)

-- After index: Index scan
EXPLAIN ANALYZE SELECT * FROM invoice WHERE balance_due_cents > 0;
-- Look for: Index Scan using idx_invoice_balance on invoice (cost=X..Y rows=Z)
```

**Index Statistics:**

```sql
-- Monitor index usage over time
SELECT 
    indexname,
    idx_scan AS times_used,
    idx_tup_read AS tuples_read,
    idx_tup_fetch AS tuples_fetched,
    pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
FROM pg_stat_user_indexes
WHERE indexname IN ('idx_invoice_balance', 'idx_job_expense_unbilled')
ORDER BY indexname;
```

---

## 🎯 AFTER YOU COMPLETE - Verify No Regressions

**CRITICAL:** After all implementation and new tests pass, you MUST verify the regression baseline.

### Step 1: Activate Virtual Environment

```bash
cd backend
source .venv/bin/activate
```

### Step 2: Run Non-Integration Tests

```bash
# Run all tests EXCEPT integration tests
pytest --ignore=tests/integration/ tests/ -v

# Concise output
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed|===)" | tail -5
```

**Expected:** `543 passed` (535 baseline + 8 new tests)

### Step 3: Run ALL Tests (Including Integration)

```bash
# Run ALL tests
pytest tests/ -v

# Concise output
pytest tests/ -v 2>&1 | grep -E "(passed|failed|===)" | tail -5
```

**Expected:** `570 passed` (562 baseline + 8 new tests)

### Step 4: Verify 100% Pass Rate

**If ANY tests fail:**
1. Identify which tests are failing
2. Determine if they are:
   - New tests you wrote (fix them)
   - Existing tests that regressed (CRITICAL - fix immediately)
3. Fix ALL failing tests before proceeding
4. Re-run regression tests until 100% pass rate

**Regression Analysis:**
- New tests failing → Fix your test code
- Existing tests failing → Your changes broke something - ROLLBACK and fix
- Cannot achieve 100% → Create fix document (see Zero Tolerance Policy below)

---

## Documentation Update

### Update Project Plan Document

**File to Update:** `dev-docs/analysis/phase-4.5-db-schema-sync-to-design-plan.md`

Find Task 11 section and update with:

```markdown
### Task 11: Partial Indexes (High-Value Performance Wins)

**Status:** ✅ COMPLETE (2026-04-XX)
**Effort:** 0.5 days (actual)
**Priority:** MEDIUM
**Gap Reference:** Analysis Section 4 - Missing Indexes (Partial)

**Completed 2 partial indexes:**
- ✅ `idx_invoice_balance` - Aging report query optimization (500ms → 10ms)
- ✅ `idx_job_expense_unbilled` - Unbilled expense query optimization (1s → 10ms)

**Implementation Summary:**

#### 1. Invoice Aging Report Index
- **Index:** `idx_invoice_balance ON invoice (balance_due_cents) WHERE balance_due_cents > 0`
- **Purpose:** Speed up unpaid invoice queries for collections workflow
- **Performance Gain:** 50x faster (500ms → 10ms p95)
- **Index Type:** Partial B-tree index (only unpaid invoices)
- **Test:** `test_idx_invoice_balance_exists`, `test_invoice_balance_query_uses_index` ✅ PASSING

#### 2. Unbilled Expense Tracking Index
- **Index:** `idx_job_expense_unbilled ON job_expense (job_id) WHERE is_billable = true AND invoice_line_id IS NULL`
- **Purpose:** Speed up unbilled expense queries for billing workflow
- **Performance Gain:** 100x faster (1s → 10ms p95)
- **Index Type:** Partial B-tree index (only billable, uninvoiced expenses)
- **Test:** `test_idx_job_expense_unbilled_exists`, `test_unbilled_expense_query_uses_index` ✅ PASSING

**Migration:** `2026_04_XX_XXXX-[hash]_add_partial_indexes_for_invoice_and_expense_queries_task11.py`
**Test Suite:** `test_partial_indexes_task11.py` - 8 tests
**Final Test Results:** 543/543 tests passing (100%)

**Database Verification:**
- Both partial indexes confirmed active ✅
- Query plans verified using indexes (EXPLAIN ANALYZE) ✅
- Performance benchmarks met (50-100x speedup) ✅
- Index sizes <10% of table size ✅
- Migration upgrade/downgrade tested successfully ✅

**Test Coverage Breakdown:**
- New tests added: 8
- Baseline maintained: 535
- Total passing: 543/543 (100%)
- Test categories: Index existence (2), Query plans (2), Correctness (2), Performance (2)

**Key Implementation Notes:**
- Used `CREATE INDEX CONCURRENTLY` to avoid table locks during creation
- Partial indexes significantly smaller than full-table indexes (storage optimization)
- Query optimizer automatically selects indexes for matching WHERE clauses
- Indexes critical for production collections and billing workflows
```

---

## Success Criteria

**MUST COMPLETE ALL BEFORE MARKING TASK AS DONE:**

- [ ] **Regression baseline captured** (non-integration and total test counts recorded)
- [ ] **Pre-migration benchmarks captured** (EXPLAIN ANALYZE for both queries)
- [ ] **Manual Alembic migration created** (cannot use autogenerate for indexes)
- [ ] **Migration uses CONCURRENTLY** (both upgrade and downgrade)
- [ ] **Both partial indexes created successfully** (`idx_invoice_balance`, `idx_job_expense_unbilled`)
- [ ] **Migration applied successfully** (`alembic upgrade head` completes without errors)
- [ ] **Post-migration benchmarks captured** (verify 50-100x speedup)
- [ ] **All 8 new tests written and passing**
- [ ] **Use session.query() in all tests** (not session.exec() - avoids deprecation warnings)
- [ ] **ALL existing tests still passing** - Zero regression
- [ ] **Non-integration tests:** 543 passing (535 baseline + 8 new)
- [ ] **Total tests:** 570 passing (562 baseline + 8 new)
- [ ] **100% test pass rate** - No failing tests
- [ ] **Database verification queries** confirm both indexes active and used by queries
- [ ] **Migration rollback tested** (`alembic downgrade -1` then `upgrade head` works)
- [ ] **Project plan document updated** with implementation summary

**Zero Tolerance Policy:**
- **Any failing test = INCOMPLETE**
- **Test pass rate MUST be 100%**
- **Regression baseline MUST be maintained or exceeded**
- If tests fail after 10+ attempts, create detailed fix document but mark task incomplete

---

## Key Files to Review

### Architecture & Design
- `dev-docs/analysis/phase-4.5-db-schema-sync-to-design-plan.md` - **Task 11 Details** ⭐
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - **GOLDEN MASTER**
- `dev-docs/db-design/aevofab-db-process-v2.6h.md` - Database operations

### Backend Code (Tables Affected)
- `backend/app/models/billing.py` - Invoice model (affects `idx_invoice_balance`)
- `backend/app/models/fulfillment.py` - JobExpense model (affects `idx_job_expense_unbilled`)

### Migration (To Create)
- `backend/migrations/versions/YYYY_MM_DD_HHMM-*_add_partial_indexes_for_invoice_and_expense_queries_task11.py`

### Tests (To Create)
- `backend/tests/test_partial_indexes_task11.py` - 8 tests minimum

---

## Risk Assessment

**Data Validation Risk:** LOW
- Indexes don't modify data, only query performance
- **Mitigation:** No data migration required

**Performance Impact:** HIGH (Positive)
- Dramatic speedup for critical queries (50-100x)
- **Measurement:** EXPLAIN ANALYZE before/after benchmarks

**Rollback Complexity:** LOW
- DROP INDEX CONCURRENTLY is safe and fast
- **Testing:** Test downgrade in development environment

**Production Deployment Risk:** LOW
- CONCURRENTLY flag prevents table locks
- Indexes can be created during business hours
- **Mitigation:** Monitor index creation progress, can be cancelled if needed

---

## Notes

- **Virtual Environment Required:** All Python/pytest commands use `source .venv/bin/activate`
- **MCP Server Available:** Use `postgres-local` MCP server for direct database queries
- **Manual Migration Required:** SQLModel doesn't support index definitions, use manual migration
- **CONCURRENTLY Is Critical:** Always use CONCURRENTLY to avoid locking tables in production
- **Query Optimizer:** PostgreSQL automatically selects indexes when WHERE clauses match
- **Deprecation Warnings:** Use `session.query()` not `session.exec()` in all tests
- **Regression Testing:** Capture baseline BEFORE, verify AFTER - both non-integration and total
- **Golden Master Authority:** The JSON schema is the single source of truth
- **Zero Regression Policy:** All existing tests MUST still pass after changes
- **Cost Impact:** Minimal (indexes use ~5-10% additional storage)
- **Production Safe:** CONCURRENTLY flag makes this a zero-downtime operation

**Important Patterns:**
- Always use `CREATE INDEX CONCURRENTLY` for production-safe deployments
- Always benchmark with EXPLAIN ANALYZE before and after
- Partial indexes are smaller and faster than full-table indexes
- Monitor `pg_stat_user_indexes` to track index usage over time

**If you get stuck:**
- Check the Golden Master JSON for exact index specifications
- Review PostgreSQL partial index documentation
- Use EXPLAIN ANALYZE to verify query plans
- Use MCP server to query pg_indexes and pg_stat_user_indexes
- Verify virtual environment is activated for all commands

---

## Example Task Flow

```bash
# ============================================
# PHASE 1: ESTABLISH BASELINE
# ============================================

# 1. Activate virtual environment
cd backend
source .venv/bin/activate

# 2. Capture non-integration baseline
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Record: 535 passed

# 3. Capture total baseline
pytest tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Record: 562 passed

# ============================================
# PHASE 2: BENCHMARK CURRENT PERFORMANCE
# ============================================

# 4. Benchmark invoice aging query
# [Use MCP server for EXPLAIN ANALYZE]

# 5. Benchmark unbilled expense query
# [Use MCP server for EXPLAIN ANALYZE]

# ============================================
# PHASE 3: CREATE MIGRATION
# ============================================

# 6. Create manual migration (cannot use autogenerate)
alembic revision -m "add_partial_indexes_for_invoice_and_expense_queries_task11"

# 7. Edit migration file
# Add CREATE INDEX CONCURRENTLY statements to upgrade()
# Add DROP INDEX CONCURRENTLY statements to downgrade()

# 8. Apply migration
alembic upgrade head

# ============================================
# PHASE 4: VERIFY DATABASE
# ============================================

# 9. Verify indexes exist (using MCP server)
# Query pg_indexes to confirm both indexes created

# 10. Benchmark queries with indexes
# [Use MCP server for EXPLAIN ANALYZE]
# Verify 50-100x speedup achieved

# ============================================
# PHASE 5: TEST
# ============================================

# 11. Create test file
# [Create backend/tests/test_partial_indexes_task11.py]
# REMEMBER: Use session.query() not session.exec()

# 12. Run new tests only
pytest tests/test_partial_indexes_task11.py -v
# Expected: 8 passed

# ============================================
# PHASE 6: REGRESSION VERIFICATION
# ============================================

# 13. Run non-integration regression tests
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Expected: 543 passed (535 baseline + 8 new)

# 14. Run ALL tests (full regression)
pytest tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Expected: 570 passed (562 baseline + 8 new)

# 15. Verify 100% pass rate
# If any failures → FIX IMMEDIATELY

# ============================================
# PHASE 7: ROLLBACK TEST
# ============================================

# 16. Test migration reversibility
alembic downgrade -1
alembic upgrade head
pytest tests/test_partial_indexes_task11.py -v
# Expected: Still 8 passed

# ============================================
# PHASE 8: DOCUMENTATION
# ============================================

# 17. Update project plan document
# [Edit phase-4.5-db-schema-sync-to-design-plan.md]
# Add completion details, benchmark results, test counts
```

---

## Questions to Ask

**Before starting:**
1. Have I reviewed the Golden Master JSON for index specifications?
2. Have I captured the regression baseline (non-integration AND total test counts)?
3. Have I activated the virtual environment?
4. Do I understand why CONCURRENTLY is critical for production?

**During implementation:**
1. Am I using `session.query()` instead of `session.exec()` in tests?
2. Have I benchmarked query performance BEFORE creating indexes?
3. Did I use `CREATE INDEX CONCURRENTLY` in the migration?
4. Are all new tests passing?
5. Am I documenting performance improvements?

**After implementation:**
1. Did I run BOTH non-integration and total regression tests?
2. Do I have 100% test pass rate (no failures)?
3. Did baseline tests increase by exactly 8 (the number of new tests)?
4. Have I verified indexes are actually being used (EXPLAIN ANALYZE)?
5. Have I updated the project plan document with benchmark results?
6. Can the migration be rolled back cleanly?
7. Did I achieve the expected 50-100x performance improvement?

---

**Ready to Begin!** 🚀

1. ✅ Capture regression baseline (non-integration and total)
2. 📊 Benchmark current query performance (EXPLAIN ANALYZE)
3. 🛠️ Create manual migration with CONCURRENTLY indexes
4. ✅ Apply migration and verify indexes created
5. 📊 Benchmark new query performance (verify 50-100x speedup)
6. ✅ Create comprehensive tests (use session.query())
7. 🔄 Run regression tests
8. 📚 Update project plan document with benchmark results

Remember: Virtual environment required, use postgres-local MCP server, CONCURRENTLY is critical, maintain 100% pass rate!
