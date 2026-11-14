# Task 5: Add Job/Fulfillment Domain Composite Indexes

**Reference:** `dev-docs/analysis/phase-4.8-db-schema-sync-4-plan.md` - Phase 2, Task 5
**Authority (Dual Master):**
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - Golden Master JSON
- Current Live Database (Phase 4.7 Post-State)
**Type:** Phase 2 - Performance Indexes
**Priority:** HIGH
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

**Phase 4.8 Task 1 Status:** ✅ COMPLETE (April 8, 2026)
- ✅ 613/613 unit tests passing (100%)
- ✅ 640/640 total tests passing (100%)
- ✅ Legacy user check constraints replaced with boolean logic
- ✅ Platform users can now be assigned modern roles

**Phase 4.8 Task 2 Status:** ✅ COMPLETE (April 8, 2026)
- ✅ 617/617 unit tests passing (100%)
- ✅ 644/644 total tests passing (100%)
- ✅ Audit domain indexes added (3 composite indexes)

**Phase 4.8 Task 3 Status:** ✅ COMPLETE (April 8, 2026)
- ✅ 619/619 unit tests passing (100%)
- ✅ 646/646 total tests passing (100%)
- ✅ Quoting domain indexes added (1 composite index)

**Phase 4.8 Task 4 Status:** ✅ COMPLETE (April 8, 2026)
- ✅ 621/621 unit tests passing (100%)
- ✅ 648/648 total tests passing (100%)
- ✅ Billing domain indexes added (5 composite indexes)

**Current Baseline:** 621/621 unit tests, 648/648 total tests passing (100%)

**See:**
- `dev-docs/analysis/phase-4.5-db-schema-sync-to-design-plan.md` for Phase 4.5 history
- `dev-docs/analysis/phase-4.6-db-schema-sync-2-plan.md` for Phase 4.6 history
- `dev-docs/analysis/phase-4.7-db-schema-sync-3-plan.md` for Phase 4.7 history

---

## Current Task: Add Job/Fulfillment Domain Composite Indexes

**Effort:** 0.5 days
**Gap Reference:** Phase 4.8 Analysis - Missing Composite Indexes (job, job_expense)
**Change Type:** MIGRATION

The job domain tables (`job`, `job_expense`) lack composite indexes for tenant-scoped status filtering with time ordering. This task adds 2 strategic indexes to optimize common query patterns for technician job lists and expense tracking.

### What Needs to Be Fixed

| # | Component | Issue | Impact | Complexity |
|---|-----------|-------|--------|------------|
| **1** | `job` | Missing composite index for tenant + status + time queries | HIGH - Slow job list queries for technicians | LOW |
| **2** | `job_expense` | Missing composite index for tenant + time queries | MEDIUM - Inefficient expense tracking queries | LOW |

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

**Record the output of both results:** `621/621 & 648/648 tests passing` (Phase 4.8 baseline - starting from Task 4 completion)

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
    op.add_constraint(...)  # Your actual changes
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

This is a **MIGRATION-ONLY task** - no SQLModel changes needed. You will create an Alembic migration to add 2 composite indexes for job domain query optimization.

#### Missing Indexes for Job/Fulfillment Domain

**Problem:** The `job` and `job_expense` tables have single-column indexes on foreign keys but lack composite indexes for common query patterns.

**Current State (Suboptimal):**
- `job` table: Single-column indexes on `tenant_id`, `status_id`, `customer_id`, `site_id`
- `job_expense` table: Single-column indexes on `tenant_id`, `job_id`

**Missing Indexes:**

**Index 1: Job tenant-scoped status list with time ordering**
```sql
-- Query pattern: "Show me all 'in_progress' jobs for this tenant, newest first"
CREATE INDEX idx_job_tenant_status_created_at 
ON job (tenant_id, status_id, created_at DESC);
```

**Index 2: Job expense tenant-scoped time ordering**
```sql
-- Query pattern: "Show me all expenses for this tenant this month"
CREATE INDEX idx_job_expense_tenant 
ON job_expense (tenant_id, incurred_at DESC);
```

**Query Performance Impact:**

```sql
-- Common query 1: Technician job list by status
SELECT * FROM job
WHERE tenant_id = '...'
  AND status_id = '...'
ORDER BY created_at DESC
LIMIT 50;
-- WITHOUT index: Scan ix_job_tenant_id → filter by status → sort (expensive)
-- WITH idx_job_tenant_status_created_at: Direct index scan (optimal)

-- Common query 2: Monthly expense report
SELECT * FROM job_expense
WHERE tenant_id = '...'
  AND incurred_at >= DATE_TRUNC('month', NOW())
ORDER BY incurred_at DESC;
-- WITHOUT index: Full table scan
-- WITH idx_job_expense_tenant: Index scan
```

**Why This Matters:**
- Technician mobile app lists jobs by status frequently (active jobs, completed jobs)
- Expense tracking queries need time-range filtering for monthly/weekly reports
- Single-column indexes on `tenant_id` alone require additional filtering + sorting overhead

---

### 2. Implementation Order

**For Task 5 (Job/Fulfillment Indexes - HIGH):**

1. **✅ Establish Regression Baseline** (621/621 unit, 648/648 total tests)
2. **Review Query Patterns**
   - Read task description for common queries
   - Determine optimal column order (filters → range → sort)
3. **Create Alembic Migration** (No SQLModel changes needed)
   ```bash
   cd backend
   source .venv/bin/activate
   alembic revision -m "phase_4_8_add_job_indexes_task5"
   ```
4. **Write Migration Logic**
   - Use `op.create_index()` for both indexes
   - Use `sa.text('created_at DESC')` and `sa.text('incurred_at DESC')` for ordering
   - Ensure proper downgrade() to drop both indexes
5. **⚠️ CRITICAL: Review migration file**
   - Search for `'event'` and `schema='audit'`
   - DELETE any `op.create_table('event', ... schema='audit')` blocks
   - DELETE any event table index/constraint operations not part of this task
   - Verify your 2 job domain index creations are present
6. **Apply Migration**
   ```bash
   alembic upgrade head
   ```
7. **Verify Indexes Created**
   - Use MCP server to query pg_indexes
   - Confirm both indexes exist with correct column order
8. **Create Test Suite** (Optional but Recommended)
   - Create `backend/tests/test_phase_4_8_job_indexes.py`
   - Verify indexes exist via pg_indexes query
   - Keep tests simple (index existence checks)
9. **Run Tests**
   ```bash
   pytest tests/test_phase_4_8_job_indexes.py -v
   ```
10. **Run Regression Tests** (see "After You Complete" section)
11. **Update Documentation**

---

### 3. Test Requirements

**⚠️ ZERO REGRESSION POLICY:**
- **ALL 621 existing unit tests MUST still pass**
- **ALL 648 total tests (including integration) MUST still pass**
- **New tests (if added) MUST pass**
- **Target: 100% pass rate on both test suites**

#### For Task 5 (Job/Fulfillment Indexes)

**Test File:** `backend/tests/test_phase_4_8_job_indexes.py`

**Required Coverage (Minimum 2 Tests):**
```python
"""
Test Suite: Phase 4.8 Task 5 - Add Job/Fulfillment Domain Composite Indexes
Tests index creation for job domain query performance optimization

Reference: phase-4.8-db-schema-sync-4-plan.md - Task 5
"""
import pytest
from sqlmodel import Session
from sqlalchemy import text

class TestJobIndexes:
    """Verify job domain composite indexes were created"""
    
    def test_job_indexes_exist(self, db_session: Session):
        """Verify both job domain indexes were created"""
        result = db_session.execute(text("""
            SELECT indexname FROM pg_indexes
            WHERE indexname IN (
                'idx_job_tenant_status_created_at',
                'idx_job_expense_tenant'
            )
            ORDER BY indexname
        """))
        indexes = [row[0] for row in result]
        expected_count = 2
        assert len(indexes) == expected_count, \
            f"Expected {expected_count} indexes, found {len(indexes)}: {indexes}"
    
    def test_job_tenant_status_index_definition(self, db_session: Session):
        """Verify job index has correct column order and DESC sorting"""
        result = db_session.execute(text("""
            SELECT indexdef FROM pg_indexes
            WHERE indexname = 'idx_job_tenant_status_created_at'
        """))
        row = result.fetchone()
        assert row is not None, "idx_job_tenant_status_created_at index not found"
        
        indexdef = row[0]
        # Verify index includes expected columns in correct order
        assert 'tenant_id' in indexdef
        assert 'status_id' in indexdef
        assert 'created_at' in indexdef
        # Verify DESC ordering on created_at
        assert 'DESC' in indexdef or 'created_at' in indexdef
```

**Test Patterns to Follow:**
- Review `backend/tests/test_phase_4_8_audit_indexes.py` - Task 2 patterns
- Review `backend/tests/test_phase_4_8_quote_indexes.py` - Task 3 patterns
- Review `backend/tests/test_phase_4_8_billing_indexes.py` - Task 4 patterns
- Review `backend/tests/conftest.py` - Available fixtures

**Common Test Fixtures Available:**
- `db_session` - Database session (use this, NOT `session`)
- `test_tenant` - Pre-created tenant for testing
- `test_user` - Pre-created user linked to test_tenant
- `test_customer` - Pre-created customer
- `test_site` - Pre-created site

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
- **For Task 5 (Job Indexes):** `[621 + 0-2] passed` (unit), `[648 + 0-2] passed` (total) - minimal new tests

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

Find Phase 2, Task 5 and update with:

```markdown
### Task 5: Add Job/Fulfillment Domain Composite Indexes

**Status:** ✅ COMPLETE (YYYY-MM-DD)
**Effort:** 0.5 days (actual)
**Priority:** HIGH
**Change Type:** MIGRATION

**Implementation Summary:**

- Migration: `YYYY_MM_DD_HHMM-[hash]_phase_4_8_add_job_indexes_task5.py`
- Test Suite: `test_phase_4_8_job_indexes.py` - [X] tests ✅
- Final Results: [621 + X]/[621 + X] unit tests passing (100%), [648 + X]/[648 + X] total tests passing (100%)

**Key Changes:**
- ✅ Added idx_job_tenant_status_created_at for tenant-scoped job status queries
- ✅ Added idx_job_expense_tenant for tenant-scoped expense tracking queries

**Verification:**
- All 2 indexes verified via pg_indexes query
- Indexes include correct column order (tenant_id, status_id/incurred_at, created_at DESC)
- Migration rollback tested successfully
```

---

## Success Criteria

**MUST COMPLETE ALL BEFORE MARKING TASK AS DONE:**

### For Task 5 (Job/Fulfillment Indexes - HIGH):
- [ ] **Regression baseline captured** (621/621 unit, 648/648 total tests)
- [ ] **Query patterns reviewed** to determine optimal column order
- [ ] **Alembic migration created** (no SQLModel changes)
- [ ] **Used `sa.text()` wrapper** for DESC ordering in both indexes
- [ ] **⚠️ CRITICAL: Checked migration for `audit.event` table** and removed if present
- [ ] **Migration applied successfully** (`alembic upgrade head`)
- [ ] **Index verification tests passing** (2 tests confirming existence)
- [ ] **ALL existing unit tests still passing** (no regression)
- [ ] **ALL total tests still passing** (no regression)
- [ ] **Database verification query confirms** both indexes created
- [ ] **Indexes include correct columns** in optimal order (filter → sort)
- [ ] **Migration rollback tested** (`alembic downgrade -1` then `upgrade head`)
- [ ] **Project plan document updated**

### For ALL Tasks:
- [ ] **100% test pass rate** - No failing tests
- [ ] **Zero regression** - Baseline maintained or exceeded

---

## Key Files to Review

### Architecture & Design
- `dev-docs/analysis/phase-4.8-db-schema-sync-4-plan.md` - **Task 5 Details** ⭐
- `dev-docs/analysis/phase-4.8-db-schema-sync-4-analysis.md` - Forensic Analysis
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - **Golden Master JSON**

### Backend Code
- `backend/app/models/fulfillment.py` - Job, JobExpense models

### Tests (Reference for Patterns)
- `backend/tests/test_phase_4_8_audit_indexes.py` - Task 2 index test patterns
- `backend/tests/test_phase_4_8_quote_indexes.py` - Task 3 index test patterns
- `backend/tests/test_phase_4_8_billing_indexes.py` - Task 4 index test patterns
- `backend/tests/conftest.py` - Test fixtures (`db_session`, `test_tenant`, etc.)

---

## Risk Assessment

**For Task 5 (Job/Fulfillment Indexes):**
- **Performance Risk:** NONE (indexes only improve performance)
- **Regression Risk:** VERY LOW (indexes don't affect application logic)
- **Migration Time:** LOW (job tables typically < 10,000 rows in development)
- **Storage Cost:** LOW (~5-10% table size per index)
- **Mitigation:** Indexes build in background, verify existence after creation

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
- **Zero Regression Policy:** All 621 unit + 648 total tests MUST pass after changes

### Phase 4.8 Specific
- **Final performance optimization** - Missing composite indexes from ORM autogeneration
- **All tasks are migrations** - No JSON-only tasks
- **Domain-specific index tasks** - Broken into 7 focused tasks for manageability
- **Test coverage optional for indexes** - Indexes don't change behavior, existence tests sufficient

### If You Get Stuck
- Use `postgres-local` MCP server to query database state in real-time
- Review Phase 4.8 Tasks 2-4 completed migrations for index creation patterns
- Search existing tests for `db_session` and `exec()` patterns
- Review the "Best Practices" section at the top of this template
- Check pg_indexes for existing index patterns: `SELECT * FROM pg_indexes WHERE tablename = 'job';`
- Remember: Column order in composite indexes matters (filter → range → sort)

---

## Example Task Flow

### For Task 5 (Job/Fulfillment Indexes):

```bash
# 1. Baseline - Capture starting point
cd backend
source .venv/bin/activate

pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Record: 621 passed

pytest tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Record: 648 passed

# 2. Review query patterns
# Job queries: WHERE tenant_id + status_id, ORDER BY created_at DESC
# Expense queries: WHERE tenant_id, ORDER BY incurred_at DESC
# Column order: (tenant_id, status_id, created_at DESC) for job
# Column order: (tenant_id, incurred_at DESC) for expense

# 3. Create migration (no SQLModel changes)
alembic revision -m "phase_4_8_add_job_indexes_task5"

# 4. Edit migration file
# Add index creation:

def upgrade():
    import sqlalchemy as sa
    
    # Job tenant-scoped status list with time ordering
    op.create_index(
        'idx_job_tenant_status_created_at',
        'job',
        ['tenant_id', 'status_id', sa.text('created_at DESC')]
    )
    
    # Job expense tenant-scoped time ordering
    op.create_index(
        'idx_job_expense_tenant',
        'job_expense',
        ['tenant_id', sa.text('incurred_at DESC')]
    )

def downgrade():
    op.drop_index('idx_job_expense_tenant', table_name='job_expense')
    op.drop_index('idx_job_tenant_status_created_at', table_name='job')

# 5. ⚠️ CRITICAL: Review migration file
# Search for 'audit' and 'event'
# DELETE any op.create_table('event', ... schema='audit') blocks
# DELETE any event table operations not part of this task

# 6. Apply migration
alembic upgrade head

# 7. Verify indexes created using MCP server
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename IN ('job', 'job_expense')
AND indexname IN ('idx_job_tenant_status_created_at', 'idx_job_expense_tenant');

# 8. Create test suite (optional but recommended)
# Create backend/tests/test_phase_4_8_job_indexes.py
# - Simple test verifying indexes exist via pg_indexes query

# 9. Run tests
pytest tests/test_phase_4_8_job_indexes.py -v

# 10. Regression check
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
pytest tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Should match or slightly exceed baseline (minimal new tests)

# 11. Rollback test
alembic downgrade -1
alembic upgrade head
pytest tests/ -v

# 12. Update docs
# Edit dev-docs/analysis/phase-4.8-db-schema-sync-4-plan.md
# Mark Task 5 as complete
```

---

## Questions to Ask

**Before starting:**
1. Have I captured the 621/621 unit and 648/648 total baselines?
2. Do I understand the query patterns and optimal column order for both indexes?
3. Do I have the correct index column order (tenant_id first, then status/time)?

**During implementation:**
1. Am I using `db_session` parameter (NOT `session`) in tests?
2. Am I using `select()/exec()` pattern (NOT `query()`) in tests?
3. After running `alembic revision`, did I check for and remove `audit.event` table creation?
4. Am I using `sa.text('created_at DESC')` and `sa.text('incurred_at DESC')` for ordering?
5. Are my index columns in the right order (filter → sort)?

**After implementation:**
1. Do I have 100% test pass rate on BOTH unit tests and total tests?
2. Do both indexes exist in pg_indexes?
3. Have I updated the project plan document?
4. Have I tested migration rollback (`alembic downgrade -1`)?

---

**Ready to Begin!** 🚀

### Task 5 Checklist (Job/Fulfillment Indexes - HIGH):
1. ✅ Capture baseline (621/621 unit, 648/648 total)
2. 📖 Review query patterns and determine column order
3. 📝 Create migration (indexes only, no SQLModel)
4. 🛠️ Use `sa.text()` for DESC ordering
5. ⚠️ **CRITICAL: Remove `audit.event` table from migration if present**
6. ✅ Apply migration (`alembic upgrade head`)
7. 🔍 Verify indexes exist via pg_indexes query
8. 🧪 Create simple existence tests (optional)
9. 🔄 Run regression tests (minimal change expected)
10. ↩️ Test rollback (`alembic downgrade -1`, then `upgrade head`)
11. 📚 Update project plan

Remember: Task 5 adds **2 strategic indexes** for job domain query performance. Be thorough, verify indexes exist with correct column order, and always check for the `audit.event` table issue in migrations!
