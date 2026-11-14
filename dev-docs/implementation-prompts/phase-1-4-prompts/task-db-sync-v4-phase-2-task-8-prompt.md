# Task 8: Add Payment Domain Composite Index

**Reference:** `dev-docs/analysis/phase-4.8-db-schema-sync-4-plan.md` - Phase 2, Task 8
**Authority (Dual Master):**
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - Golden Master JSON
- Current Live Database (Phase 4.7 Post-State)
**Type:** Phase 2 - Performance Optimization - Payment Domain Indexes
**Priority:** MEDIUM
**Change Type:** MIGRATION

---

## Context

This is **Phase 4.8 - DB Sync v#4**, a fourth forensic reconciliation after completing Phases 4.5, 4.6, and 4.7. A comprehensive comparison between the current database state and the Golden Master JSON revealed **2 remaining categories of discrepancies** requiring final alignment before production deployment.

**Key Focus Areas:**
1. **Legacy Check Constraints** (CRITICAL) - Stale constraints on user table hardcoding obsolete platform role values
2. **Missing Composite Indexes** (HIGH) - 18 performance indexes across 13 tables missing from physical database

**Key Principle:** The structure is fundamentally solid (all tables, functions, columns present). This phase focuses on **final constraint logic updates** and **query performance optimization** through strategic indexing.

---

## What Was Completed in Previous Phases

**Phase 4.5 Status:** ✅ COMPLETE (March 30 - April 1, 2026)
- ✅ 572/572 tests passing (100%)
- ✅ 100% alignment between physical database and Golden Master JSON achieved
- ✅ All unique, check, and temporal exclusion constraints implemented

**Phase 4.6 Status:** ✅ COMPLETE (April 1-2, 2026)
- ✅ 575/575 unit tests passing (100%)
- ✅ 602/602 total tests passing (100%)
- ✅ Dual-master reconciliation completed
- ✅ Function logic and constraint backporting from SQL to JSON

**Phase 4.7 Status:** ✅ COMPLETE (April 3-7, 2026)
- ✅ 609/609 unit tests passing (100%)
- ✅ 636/636 total tests passing (100%)
- ✅ ENUM standardization completed (all TEXT + CHECK)
- ✅ Integer capacity risks resolved (FK type alignments)
- ✅ Global email uniqueness enforced
- ✅ Missing defaults and constraints added
- ✅ Function/trigger logic aligned

**Current Baseline:** 609/609 unit tests, 636/636 total tests passing (100%)

**See:**
- `dev-docs/analysis/phase-4.5-db-schema-sync-to-design-plan.md` for Phase 4.5 history
- `dev-docs/analysis/phase-4.6-db-schema-sync-2-plan.md` for Phase 4.6 history
- `dev-docs/analysis/phase-4.7-db-schema-sync-3-plan.md` for Phase 4.7 history

---

## Current Task: Add Payment Domain Composite Index

**Effort:** 0.25 days
**Gap Reference:** Phase 4.8 Analysis - Section 2 - Missing Composite Indexes (psp_transaction_log)
**Change Type:** MIGRATION

The `psp_transaction_log` table tracks all payment service provider (Stripe) transaction events for auditing and reconciliation. The table currently has a single-column index on `tenant_id`, but lacks the composite index for tenant-scoped time-series queries that are common in payment history views and financial reporting.

### What Needs to Be Fixed

| # | Component | Issue | Impact | Complexity |
|---|-----------|-------|--------|------------|
| **1** | `psp_transaction_log` | Missing tenant + time composite index `(tenant_id, created_at DESC)` | Payment history queries require full table scan + sort instead of direct index scan | LOW |

### Tools Available

- You have access to the postgres-local MCP server to query the DB directly, in read-only mode.
- Remember that you do not need to insert any '\n' characters in the sql when creating it for the mcp server.

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
# Run full test suite but without the integration tests FIRST

# Concise output to capture baseline count (this is preferred option to minimize tokens)
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed|===)" | tail -5

# Full output to capture errors and warnings, or modify the concise output version as well
pytest --ignore=tests/integration/ tests/ -v

# Run all tests SECOND

# Concise output to capture baseline count (this is preferred option to minimize tokens)
pytest tests/ -v 2>&1 | grep -E "(passed|failed|===)" | tail -5

# Full output to capture errors and warnings, or modify the concise output version as well
pytest tests/ -v
```

**Record the output of both results:** `629/629 & 656/656 tests passing` (Phase 4.8 baseline - starting from Task 7 completion)

### Step 3: Document Your Baseline

**Write down both of these numbers before proceeding**

**This is your regression checkpoint. ALL these tests MUST still pass after your work.**

---

## ⚠️ CRITICAL: Coding Agent Best Practices

**BEFORE writing ANY code, review these common errors from previous phases:**

### 1. Use `db_session` NOT `session` in Tests
❌ **WRONG:**
```python
def test_example(session: Session, test_tenant):  # Wrong parameter name
    user = User(email="test@example.com")
    session.add(user)
```

✅ **CORRECT:**
```python
def test_example(db_session: Session, test_tenant):  # Correct parameter name
    user = User(email="test@example.com")
    db_session.add(user)
```

**Why:** The pytest fixture is named `db_session` in `backend/tests/conftest.py`. Using `session` will cause fixture not found errors.

**Action:** Search existing tests to confirm: `grep -r "def test_.*db_session" backend/tests/` shows 200+ tests use `db_session`.

---

### 2. Use SQLModel `select()` with `exec()` NOT `query()`

❌ **WRONG (Creates Deprecation Warnings):**
```python
user = db_session.query(User).filter(User.email == "test@example.com").first()
```

✅ **CORRECT (SQLModel Pattern):**
```python
from sqlmodel import select

user = db_session.exec(
    select(User).where(User.email == "test@example.com")
).first()
```

**Why:** SQLModel uses `select()` + `exec()` pattern, not SQLAlchemy's `query()` API. The `query()` method generates deprecation warnings.

**Action:** Review existing tests for patterns: `backend/tests/test_citext_email.py` shows correct usage.

---

### 3. ALWAYS Check Alembic Autogenerate for `audit.event` Table

❌ **COMMON MIGRATION ERROR:**
```python
# Alembic autogenerate sometimes incorrectly wants to create audit.event
def upgrade():
    op.create_table('event',  # This table already exists!
        sa.Column('id', sa.BigInteger(), nullable=False),
        ...
        schema='audit'
    )
```

✅ **CORRECT (Remove Before Running Migration):**
```python
def upgrade():
    # op.create_table('event', ...) <- REMOVED
    # Only include your actual schema changes
    op.create_index(...)  # Your actual changes
```

**Downgrade:** Also, don't forget to remove the audit.event from the downgrade method too.

**Why:** The `audit.event` table was created in Phase 4.5 and exists in the database. Alembic autogenerate sometimes detects it as missing due to schema search path issues.

**Action After `alembic revision --autogenerate`:**
1. Open the generated migration file
2. Search for `'event'` and `schema='audit'`
3. **DELETE any `op.create_table('event', ... schema='audit')` statements in upgrade**
4. **DELETE any `op.drop_table('event', ... schema='audit')` statements in downgrade**
5. **DELETE any indexes or constraints as well from the event table that aren't included in your task**
6. Verify your actual changes are still present
7. Only then run `alembic upgrade head`

---

### 4. Use `text()` Wrapper for Raw SQL and DESC Ordering in Indexes

❌ **WRONG (Will Fail with SQLAlchemy):**
```python
# Missing text() wrapper for raw SQL expressions
op.create_index(
    'idx_example',
    'my_table',
    ['tenant_id', 'created_at DESC']  # Wrong: DESC needs text() wrapper
)
```

✅ **CORRECT (Use text() for SQL Expressions):**
```python
import sqlalchemy as sa

op.create_index(
    'idx_example',
    'my_table',
    ['tenant_id', sa.text('created_at DESC')]  # Correct: DESC in text() wrapper
)
```

**Why:** SQLAlchemy requires explicit `text()` wrapper for raw SQL expressions like `DESC`, `ASC`, or function calls in index definitions.

**Action:** Always wrap raw SQL fragments in `sa.text()` when creating indexes with ordering or expressions.

---

### 5. For Composite Indexes: Order Columns by Query Pattern

❌ **WRONG (Poor Index Performance):**
```python
# Incorrect column order - doesn't match query pattern
CREATE INDEX idx_job_created_status ON job (created_at DESC, tenant_id, status_id);

# Query pattern:
SELECT * FROM job WHERE tenant_id = '...' AND status_id = '...' ORDER BY created_at DESC;
# Index won't be used efficiently because first column is created_at
```

✅ **CORRECT (Matches Query Pattern):**
```python
# Correct column order - matches WHERE filters then ORDER BY
CREATE INDEX idx_job_tenant_status_created ON job (tenant_id, status_id, created_at DESC);

# Query pattern:
SELECT * FROM job WHERE tenant_id = '...' AND status_id = '...' ORDER BY created_at DESC;
# Index used optimally: filter by tenant_id, filter by status_id, sorted by created_at
```

**Why:** Composite indexes are most efficient when column order matches the query pattern: equality filters first, then range/order columns.

**Rule:** **Filter columns → Range columns → Sort columns**

**Action:** Review the query patterns in the task description to determine correct column order.

---

### 6. Test Index Creation and Usage

❌ **INCOMPLETE (Doesn't Verify Index Exists):**
```python
def test_query_performance(db_session, test_tenant):
    """Test query runs fast"""
    result = db_session.exec(select(Job).where(Job.tenant_id == test_tenant.id)).all()
    assert len(result) >= 0
    # Missing: Verify index actually exists in database
```

✅ **CORRECT (Verify Index Exists):**
```python
from sqlalchemy import text

def test_job_indexes_exist(db_session):
    """Verify composite job indexes were created"""
    result = db_session.execute(text("""
        SELECT indexname FROM pg_indexes
        WHERE tablename = 'job'
        AND indexname IN (
            'idx_job_tenant_status_created_at',
            'idx_job_expense_tenant'
        )
    """))
    indexes = [row[0] for row in result]
    assert len(indexes) == 2, f"Expected 2 indexes, found {len(indexes)}"
```

**Why:** You must verify indexes were actually created in the database, not just that queries run without errors.

**Action:** Include index existence verification tests for all index creation tasks.

---

## Requirements

### 1. Implementation Details

This is a **MIGRATION-ONLY** task. No SQLModel changes are needed.

**Problem:** The `psp_transaction_log` table only has a single-column index on `tenant_id`. Queries that filter by tenant AND sort by time require a full table scan followed by sorting.

**Current State:**
```sql
-- Existing indexes (single-column only):
CREATE INDEX ix_psp_transaction_log_tenant_id ON psp_transaction_log (tenant_id);
```

**JSON Schema (CORRECT):**
```json
{
  "indexes": [
    {
      "name": "idx_psp_tx_log_tenant_time",
      "columns": [
        {"name": "tenant_id", "order": "ASC"},
        {"name": "created_at", "order": "DESC"}
      ],
      "unique": false
    }
  ]
}
```

**Missing Index:**
```sql
-- Tenant-scoped payment transaction history (time-ordered)
CREATE INDEX idx_psp_tx_log_tenant_time 
ON psp_transaction_log (tenant_id, created_at DESC);
```

**Query Performance Impact:**
```sql
-- Common query: "Show me all Stripe transactions for this tenant this month"
SELECT * FROM psp_transaction_log
WHERE tenant_id = '...'
  AND created_at >= DATE_TRUNC('month', NOW())
ORDER BY created_at DESC;
-- WITHOUT index: Scan ix_psp_transaction_log_tenant_id → filter → sort (expensive)
-- WITH idx_psp_tx_log_tenant_time: Direct index scan (optimal)

-- Common query: "Show me last 100 payment events for this tenant"
SELECT * FROM psp_transaction_log
WHERE tenant_id = '...'
ORDER BY created_at DESC
LIMIT 100;
-- WITHOUT index: Scan ix_psp_transaction_log_tenant_id → sort → limit
-- WITH idx_psp_tx_log_tenant_time: Direct index scan (pre-sorted)
```

**Migration Approach:**
1. **NO SQLModel changes needed** - Indexes are managed via Alembic only
2. Use `op.create_index()` with `sa.text('created_at DESC')` for DESC ordering
3. Verify index exists via `pg_indexes` query
4. Keep migration simple (1 index only)

**Index Creation Example:**
```python
def upgrade():
    # Payment transaction log tenant-scoped time ordering
    op.create_index(
        'idx_psp_tx_log_tenant_time',
        'psp_transaction_log',
        ['tenant_id', sa.text('created_at DESC')]
    )

def downgrade():
    op.drop_index('idx_psp_tx_log_tenant_time', table_name='psp_transaction_log')
```

**Database Verification Query:**
```sql
-- Verify index exists
SELECT 
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE indexname = 'idx_psp_tx_log_tenant_time';
-- Should return 1 row with correct definition
```

---

### 2. Implementation Order

**For Task 8 (Payment Domain Index - MEDIUM):**

1. **✅ Establish Regression Baseline** (629/629 unit, 656/656 total tests - from Task 7)
2. **Review Query Patterns**
   - Read task description for common queries
   - Confirm column order: tenant_id (filter) → created_at DESC (sort)
3. **Create Alembic Migration** (No SQLModel changes needed)
   ```bash
   cd backend
   source .venv/bin/activate
   alembic revision -m "phase_4_8_add_payment_indexes_task8"
   ```
4. **Write Migration Logic**
   - Use `op.create_index()` for standard composite index
   - Use `sa.text('created_at DESC')` for DESC ordering
   - Ensure proper downgrade() to drop index
5. **⚠️ CRITICAL: Review Migration File**
   - Search for `'event'` and `schema='audit'`
   - DELETE any `op.create_table('event', ... schema='audit')` blocks
   - DELETE any `op.drop_table('event', ... schema='audit')` blocks in downgrade
   - Verify your index creation is still present
6. **Apply Migration**
   ```bash
   alembic upgrade head
   ```
7. **Verify Index Created**
   - Use MCP server to query `pg_indexes`
   - Confirm index includes correct columns in correct order
8. **Create Test Suite** (Optional but Recommended)
   - Create `backend/tests/test_phase_4_8_payment_indexes.py`
   - Verify index exists via pg_indexes query
   - Keep test simple (index existence check)
9. **Run Tests**
   ```bash
   pytest tests/test_phase_4_8_payment_indexes.py -v
   ```
10. **Run Regression Tests** (see "After You Complete" section)
11. **Update Documentation**

---

### 3. Test Requirements

**⚠️ ZERO REGRESSION POLICY:**
- **ALL 629 existing unit tests MUST still pass**
- **ALL 656 total tests (including integration) MUST still pass**
- **New tests (if added) MUST pass**
- **Target: 100% pass rate on both test suites**

#### For Task 8 (Payment Domain Index)

**Test File:** `backend/tests/test_phase_4_8_payment_indexes.py`

**Required Coverage (Minimum 1-2 Tests):**
```python
"""
Test Suite: Phase 4.8 Task 8 - Add Payment Domain Composite Index
Tests index creation for payment transaction log query performance optimization

Reference: phase-4.8-db-schema-sync-4-plan.md
"""
import pytest
from sqlmodel import Session
from sqlalchemy import text

class TestPaymentIndexes:
    """Verify payment domain composite index was created"""
    
    def test_payment_index_exists(self, db_session: Session):
        """Verify psp_transaction_log tenant+time index was created"""
        result = db_session.execute(text("""
            SELECT indexname FROM pg_indexes
            WHERE tablename = 'psp_transaction_log'
            AND indexname = 'idx_psp_tx_log_tenant_time'
        """))
        index = result.fetchone()
        assert index is not None, "Missing index: idx_psp_tx_log_tenant_time"
    
    def test_payment_index_definition(self, db_session: Session):
        """Verify index has correct column order (tenant_id, created_at DESC)"""
        result = db_session.execute(text("""
            SELECT indexdef FROM pg_indexes
            WHERE indexname = 'idx_psp_tx_log_tenant_time'
        """))
        indexdef = result.fetchone()[0]
        
        # Verify index includes expected columns in correct order
        assert 'tenant_id' in indexdef, "Index should include tenant_id"
        assert 'created_at' in indexdef, "Index should include created_at"
        # DESC ordering may appear as 'DESC' or be implicit
```

**Test Patterns to Follow:**
- Review `backend/tests/test_phase_4_8_*.py` - Previous Phase 4.8 test patterns
- Review `backend/tests/conftest.py` - Available fixtures

**Common Test Fixtures Available:**
- `db_session` - Database session (use this, NOT `session`)
- `test_tenant` - Pre-created tenant for testing
- `test_user` - Pre-created user linked to test_tenant

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
pytest tests/ -v

# Concise output
pytest tests/ -v 2>&1 | grep -E "(passed|failed|===)" | tail -5
```

**Expected:**
- **For Task 8 (Payment Index):** `[629 + 1-2] passed` (unit), `[656 + 1-2] passed` (total) - minimal new tests

### Step 3: Verify 100% Pass Rate

**If ANY tests fail:**
1. Identify failing tests
2. Determine if new or existing tests
3. Fix ALL failures before proceeding
4. Re-run until 100% pass rate

**For Index Task:**
- If existing tests fail → Migration broke something (rollback and fix)
- If new tests fail → Index creation failed (check migration)

---

## Documentation Update

### Update Project Plan Document

**File to Update:** `dev-docs/analysis/phase-4.8-db-schema-sync-4-plan.md`

Find Phase 2, Task 8 and update with:

```markdown
### Task 8: Add Payment Domain Composite Index

**Status:** ✅ COMPLETE (YYYY-MM-DD)
**Effort:** 0.25 days (actual)
**Priority:** MEDIUM
**Change Type:** MIGRATION

**Implementation Summary:**

- Migration: `YYYY_MM_DD_HHMM-[hash]_phase_4_8_add_payment_indexes_task8.py`
- Test Suite: `test_phase_4_8_payment_indexes.py` - 2 tests ✅
- Final Results: [629 + 2]/[629 + 2] unit tests passing (100%), [656 + 2]/[656 + 2] total tests passing (100%)

**Key Changes:**
- ✅ Added idx_psp_tx_log_tenant_time composite index on psp_transaction_log
- ✅ Optimized tenant-scoped payment transaction history queries

**Verification:**
- Index verified via pg_indexes query
- Composite index includes (tenant_id, created_at DESC) in correct order
- Migration rollback tested successfully
```

---

## Success Criteria

**MUST COMPLETE ALL BEFORE MARKING TASK AS DONE:**

### For Task 8 (Payment Domain Index - MEDIUM):
- [ ] **Regression baseline captured** (629/629 unit, 656/656 total tests)
- [ ] **Query patterns reviewed** - Confirmed tenant_id (filter) → created_at DESC (sort) order
- [ ] **Alembic migration created** (no SQLModel changes)
- [ ] **Used `sa.text()` wrapper** for `created_at DESC` ordering
- [ ] **⚠️ CRITICAL: Checked migration for `audit.event` table** and removed if present
- [ ] **Migration applied successfully** (`alembic upgrade head`)
- [ ] **Index verification tests passing** (1-2 tests confirming existence)
- [ ] **ALL existing unit tests still passing** (no regression)
- [ ] **ALL total tests still passing** (no regression)
- [ ] **Database verification query confirms** index created
- [ ] **Index includes correct columns** in optimal order (tenant_id, created_at DESC)
- [ ] **Migration rollback tested** (`alembic downgrade -1` then `upgrade head`)
- [ ] **Project plan document updated**

### For ALL Tasks:
- [ ] **100% test pass rate** - No failing tests
- [ ] **Zero regression** - Baseline maintained or exceeded

---

## Key Files to Review

### Architecture & Design
- `dev-docs/analysis/phase-4.8-db-schema-sync-4-plan.md` - **Task 8 Details** ⭐
- `dev-docs/analysis/phase-4.8-db-schema-sync-4-analysis.md` - Forensic Analysis
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - **Golden Master JSON**

### Backend Code
- `backend/app/models/billing.py` - PSPTransactionLog model

### Tests (Reference for Patterns)
- `backend/tests/test_phase_4_8_*.py` - Phase 4.8 test patterns
- `backend/tests/conftest.py` - Test fixtures (`db_session`, `test_tenant`, etc.)

---

## Risk Assessment

**For Task 8 (Payment Domain Index):**
- **Performance Risk:** NONE (indexes only improve performance)
- **Regression Risk:** VERY LOW (indexes don't affect application logic)
- **Migration Time:** LOW (psp_transaction_log typically small in dev environment)
- **Storage Cost:** LOW (~5-10% table size)
- **Mitigation:** Index builds in background, verify existence after creation

---

## Notes

### Important Patterns to Follow
- **Virtual Environment Required:** All Python/pytest commands use `source .venv/bin/activate`
- **Use `db_session` Parameter:** NOT `session` (pytest fixture naming)
- **Use `select()/exec()` Pattern:** NOT `query()` (SQLModel standard, no deprecation warnings)
- **Check Alembic Migrations:** ALWAYS remove `audit.event` table creation if autogenerated
- **Use `sa.text()` for SQL:** Required for DESC/ASC ordering in index definitions
- **Index Column Order:** Filter columns → Range columns → Sort columns (matches query patterns)
- **Dual Master Strategy:** JSON is documentation authority, SQL database is runtime authority
- **Zero Regression Policy:** All 629 unit + 656 total tests MUST pass after changes

### Phase 4.8 Specific
- **Final performance optimization** - Missing composite indexes from ORM autogeneration
- **Task 8 is MEDIUM priority** - Lower than other index tasks (payment log is lower traffic)
- **Simple migration** - Only 1 index to add
- **Test coverage optional** - Index existence test sufficient

### If You Get Stuck
- Use `postgres-local` MCP server to query database state in real-time
- Review Phase 4.8 completed tasks (Tasks 2-7) for migration patterns
- Search existing tests for `db_session` and `exec()` patterns
- Review the "Best Practices" section at the top of this prompt
- Check pg_indexes for existing index patterns: `SELECT * FROM pg_indexes WHERE tablename = 'psp_transaction_log';`
- Remember: Column order in composite indexes matters (filter → range → sort)

---

## Example Task Flow

### For Task 8 (Payment Domain Index):

```bash
# 1. Baseline - Capture starting point
cd backend
source .venv/bin/activate

# Run unit tests (no integration)
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Record: 629 passed (from Task 7 completion)

# Run all tests (including integration)
pytest tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Record: 656 passed (from Task 7 completion)

# 2. Review query patterns
# Pattern: WHERE tenant_id = '...' ORDER BY created_at DESC
# Column order: tenant_id (equality filter) → created_at DESC (sort)

# 3. Create migration (no SQLModel changes)
alembic revision -m "phase_4_8_add_payment_indexes_task8"

# 4. Edit migration file
# Add logic to:
# - Create idx_psp_tx_log_tenant_time index
# - Use sa.text('created_at DESC') for ordering
# - Include proper downgrade()

# Example:
def upgrade():
    import sqlalchemy as sa
    
    op.create_index(
        'idx_psp_tx_log_tenant_time',
        'psp_transaction_log',
        ['tenant_id', sa.text('created_at DESC')]
    )

def downgrade():
    op.drop_index('idx_psp_tx_log_tenant_time', table_name='psp_transaction_log')

# 5. ⚠️ CRITICAL: Review migration file
# Search for 'audit' and 'event'
# DELETE any op.create_table('event', ... schema='audit') blocks
# DELETE any op.drop_table('event', ... schema='audit') blocks in downgrade
# Verify your index creation is present

# 6. Apply migration
alembic upgrade head

# 7. Verify index created using MCP server
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'psp_transaction_log'
AND indexname = 'idx_psp_tx_log_tenant_time';
# Should return 1 row

# 8. Create test suite (optional)
# Create backend/tests/test_phase_4_8_payment_indexes.py
# - Simple test verifying index exists via pg_indexes query

# 9. Run tests
pytest tests/test_phase_4_8_payment_indexes.py -v

# 10. Regression check
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Expected: 630-631 passed (629 + 1-2 new)

pytest tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Expected: 657-658 passed (656 + 1-2 new)

# 11. Rollback test
alembic downgrade -1
alembic upgrade head
pytest tests/ -v  # Should still pass

# 12. Update docs
# Edit dev-docs/analysis/phase-4.8-db-schema-sync-4-plan.md
# Mark Task 8 as complete with test results
```

---

## Questions to Ask

**Before starting:**
1. Have I captured the 629/629 unit and 656/656 total baselines (from Task 7)?
2. Do I understand the query patterns (tenant filter → time sort)?
3. Do I have the correct column order (tenant_id, created_at DESC)?

**During implementation:**
1. Am I using `db_session` parameter (NOT `session`) in tests?
2. Am I using `select()/exec()` pattern (NOT `query()`) in tests?
3. After running `alembic revision`, did I check for and remove `audit.event` table creation?
4. For index: Am I using `sa.text('created_at DESC')` for DESC ordering?
5. Is my index column order correct (filter → sort)?

**After implementation:**
1. Do I have 100% test pass rate on BOTH unit tests and total tests?
2. Does the index exist in pg_indexes?
3. Have I updated the project plan document?
4. Have I tested migration rollback (`alembic downgrade -1`)?

---

**Ready to Begin!** 🚀

### Task 8 Checklist (Payment Domain Index - MEDIUM):
1. ✅ Capture baseline (629/629 unit, 656/656 total from Task 7)
2. 📖 Review query patterns (tenant filter → time sort)
3. 📝 Create migration (index only, no SQLModel)
4. 🛠️ Use `sa.text()` for `created_at DESC`
5. ⚠️ **CRITICAL: Remove `audit.event` table from migration if present**
6. ✅ Apply migration (`alembic upgrade head`)
7. 🔍 Verify index exists via pg_indexes query
8. 🧪 Create simple existence test (optional)
9. 🔄 Run regression tests (minimal change expected)
10. ↩️ Test rollback (`alembic downgrade -1`, then `upgrade head`)
11. 📚 Update project plan

Remember: This is the **final index task** in Phase 4.8! Payment transactions are lower traffic than other tables, so this index is MEDIUM priority (not HIGH like Tasks 2-7). Keep it simple: 1 index, verify it exists, ensure all tests pass. After this task, Phase 2 is complete!
