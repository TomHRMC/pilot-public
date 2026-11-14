# Task 2: Add Audit Domain Composite Indexes

**Reference:** `dev-docs/analysis/phase-4.8-db-schema-sync-4-plan.md` - Phase 2, Task 2
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
1. **Legacy Check Constraints** (CRITICAL) - Stale constraints on user table hardcoding obsolete platform role values ✅ COMPLETE
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
- ✅ Platform users can now use modern roles (accountant, owner, support)

**Current Baseline:** 613/613 unit tests, 640/640 total tests passing (100%)

**See:**
- `dev-docs/analysis/phase-4.5-db-schema-sync-to-design-plan.md` for Phase 4.5 history
- `dev-docs/analysis/phase-4.6-db-schema-sync-2-plan.md` for Phase 4.6 history
- `dev-docs/analysis/phase-4.7-db-schema-sync-3-plan.md` for Phase 4.7 history
- `dev-docs/analysis/phase-4.8-db-schema-sync-4-plan.md` for Phase 4.8 Task 1 (user constraints)

---

## Current Task: Add Audit Domain Composite Indexes

**Effort:** 0.5 days
**Gap Reference:** Phase 4.8 Analysis - Section 2: Missing Composite Indexes (audit.event)
**Change Type:** MIGRATION

The `audit.event` table currently has only single-column indexes on `idempotency_key` and `request_id`. This task adds three critical composite indexes to optimize the most common audit log query patterns: tenant-scoped time-ordered queries, entity-specific audit trails, and user action history.

### What Needs to Be Fixed

| # | Component | Issue | Impact | Complexity |
|---|-----------|-------|--------|------------|
| **1** | `audit.event` | Missing `idx_audit_event_tenant_time` for tenant-scoped time-ordered queries | HIGH - Full table scan for "show all tenant events" queries | LOW |
| **2** | `audit.event` | Missing `idx_audit_event_entity_search` for entity-specific audit trails | HIGH - Full table scan for "show all changes to this entity" queries | LOW |
| **3** | `audit.event` | Missing `idx_audit_event_user_action_time` for user action history | MEDIUM - Full table scan for "show user's actions" queries | LOW |

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

**Record the output of both results:** `613/613 & 640/640 tests passing` (Phase 4.8 baseline - starting from Task 1 completion)

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

This is a **MIGRATION-ONLY** task. No SQLModel changes needed - indexes are managed purely through Alembic.

**Problem:** The `audit.event` table only has single-column indexes on `idempotency_key` and `request_id`. Missing tenant-scoped, time-ordered, and entity-search indexes.

**Missing Indexes:**
```sql
-- 1. Tenant-scoped audit log (most common query)
CREATE INDEX idx_audit_event_tenant_time 
ON audit.event (tenant_id, occurred_at DESC);

-- 2. Entity-specific audit trail
CREATE INDEX idx_audit_event_entity_search 
ON audit.event (entity_name, entity_id, occurred_at DESC);

-- 3. User action history
CREATE INDEX idx_audit_event_user_action_time 
ON audit.event (user_id, action, occurred_at DESC);
```

**Query Performance Impact:**
```sql
-- Common query: "Show me all audit events for this tenant in the last 30 days"
SELECT * FROM audit.event
WHERE tenant_id = '...'
  AND occurred_at > NOW() - INTERVAL '30 days'
ORDER BY occurred_at DESC
LIMIT 100;
-- WITHOUT index: Full table scan (100,000+ rows)
-- WITH idx_audit_event_tenant_time: Index scan (100 rows)

-- Common query: "Show me all changes to this specific customer"
SELECT * FROM audit.event
WHERE entity_name = 'customer'
  AND entity_id = '...'
ORDER BY occurred_at DESC;
-- WITHOUT index: Full table scan
-- WITH idx_audit_event_entity_search: Index scan
```

**Migration Approach:**
1. **NO SQLModel changes needed** - Indexes are managed via Alembic only
2. Use `op.create_index()` with `sa.text()` for DESC ordering
3. Specify `schema='audit'` since audit.event is in the audit schema
4. Order columns: filter columns → sort columns
5. Test index existence via pg_indexes query

**Index Creation Pattern:**
```python
def upgrade():
    import sqlalchemy as sa
    
    # Tenant-scoped audit log (most common query)
    op.create_index(
        'idx_audit_event_tenant_time',
        'event',
        ['tenant_id', sa.text('occurred_at DESC')],
        schema='audit'
    )
    
    # Entity-specific audit trail
    op.create_index(
        'idx_audit_event_entity_search',
        'event',
        ['entity_name', 'entity_id', sa.text('occurred_at DESC')],
        schema='audit'
    )
    
    # User action history
    op.create_index(
        'idx_audit_event_user_action_time',
        'event',
        ['user_id', 'action', sa.text('occurred_at DESC')],
        schema='audit'
    )

def downgrade():
    op.drop_index('idx_audit_event_user_action_time', table_name='event', schema='audit')
    op.drop_index('idx_audit_event_entity_search', table_name='event', schema='audit')
    op.drop_index('idx_audit_event_tenant_time', table_name='event', schema='audit')
```

**Database Verification Query:**
```sql
-- Verify indexes exist
SELECT 
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'audit' 
  AND tablename = 'event'
  AND indexname IN (
    'idx_audit_event_tenant_time',
    'idx_audit_event_entity_search',
    'idx_audit_event_user_action_time'
)
ORDER BY indexname;
```

---

### 2. Implementation Order

**For Task 2 (Audit Domain Indexes - HIGH):**

1. **✅ Establish Regression Baseline** (613/613 unit, 640/640 total tests)
2. **Review Query Patterns**
   - Tenant-scoped queries: filter by `tenant_id`, sort by `occurred_at DESC`
   - Entity audit trails: filter by `entity_name` + `entity_id`, sort by `occurred_at DESC`
   - User actions: filter by `user_id` + `action`, sort by `occurred_at DESC`
3. **Create Alembic Migration** (No SQLModel changes needed)
   ```bash
   cd backend
   source .venv/bin/activate
   alembic revision --autogenerate -m "phase_4_8_add_audit_indexes_task2"
   ```
4. **⚠️ CRITICAL: Review Migration File**
   - **DELETE any `op.create_table('event', ... schema='audit')` blocks**
   - **DELETE any `op.drop_table('event', ... schema='audit')` blocks**
   - Verify your 3 index creations are present
   - Verify `schema='audit'` is specified for all index operations
5. **Write Migration Logic**
   - Use `op.create_index()` for all 3 indexes
   - Use `sa.text('occurred_at DESC')` for time ordering
   - Specify `schema='audit'` for all operations
   - Ensure proper downgrade() to drop all 3 indexes
6. **Apply Migration**
   ```bash
   alembic upgrade head
   ```
7. **Create Test Suite** (Optional but Recommended)
   - Create `backend/tests/test_phase_4_8_audit_indexes.py`
   - Verify all 3 indexes exist via pg_indexes query
   - Keep tests simple (index existence checks)
8. **Run Tests**
   ```bash
   pytest tests/test_phase_4_8_audit_indexes.py -v
   ```
9. **Run Regression Tests** (see "After You Complete" section)
10. **Update Documentation**

---

### 3. Test Requirements

**⚠️ ZERO REGRESSION POLICY:**
- **ALL 613 existing unit tests MUST still pass**
- **ALL 640 total tests (including integration) MUST still pass**
- **New tests (if added) MUST pass**
- **Target: 100% pass rate on both test suites**

#### For Task 2 (Audit Domain Indexes)

**Test File:** `backend/tests/test_phase_4_8_audit_indexes.py`

**Required Coverage (1-2 Tests):**
```python
"""
Test Suite: Phase 4.8 Task 2 - Add Audit Domain Composite Indexes
Tests index creation for audit log query performance optimization

Reference: phase-4.8-db-schema-sync-4-plan.md - Task 2
"""
import pytest
from sqlmodel import Session
from sqlalchemy import text

class TestAuditIndexes:
    """Verify audit.event composite indexes were created"""
    
    def test_audit_indexes_exist(self, db_session: Session):
        """Verify all 3 audit indexes were created"""
        result = db_session.execute(text("""
            SELECT indexname FROM pg_indexes
            WHERE schemaname = 'audit' 
              AND tablename = 'event'
              AND indexname IN (
                'idx_audit_event_tenant_time',
                'idx_audit_event_entity_search',
                'idx_audit_event_user_action_time'
            )
            ORDER BY indexname
        """))
        indexes = [row[0] for row in result]
        expected_count = 3
        assert len(indexes) == expected_count, \
            f"Expected {expected_count} indexes, found {len(indexes)}: {indexes}"
    
    def test_audit_tenant_time_index_definition(self, db_session: Session):
        """Verify tenant time index has correct definition (optional)"""
        result = db_session.execute(text("""
            SELECT indexdef FROM pg_indexes
            WHERE schemaname = 'audit'
              AND tablename = 'event'
              AND indexname = 'idx_audit_event_tenant_time'
        """))
        row = result.fetchone()
        assert row is not None, "Index idx_audit_event_tenant_time not found"
        
        indexdef = row[0]
        # Verify index includes expected columns
        assert 'tenant_id' in indexdef
        assert 'occurred_at' in indexdef
```

**Test Patterns to Follow:**
- Review `backend/tests/test_phase_4_7_*.py` - Phase 4.7 test patterns
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
- **For Task 2 (Audit Indexes):** `[613 + 0-2] passed` (unit), `[640 + 0-2] passed` (total) - minimal or no new tests

### Step 3: Verify 100% Pass Rate

**If ANY tests fail:**
1. Identify failing tests
2. Determine if new or existing tests
3. Fix ALL failures before proceeding
4. Re-run until 100% pass rate

**For Index Tasks:**
- If existing tests fail → Migration broke something (rollback and fix)
- If new tests fail → Index creation failed (check migration)

---

## Documentation Update

### Update Project Plan Document

**File to Update:** `dev-docs/analysis/phase-4.8-db-schema-sync-4-plan.md`

Find Phase 2, Task 2 and update with:

```markdown
### Task 2: Add Audit Domain Composite Indexes

**Status:** ✅ COMPLETE (YYYY-MM-DD)
**Effort:** 0.5 days (actual)
**Priority:** HIGH
**Change Type:** MIGRATION

**Implementation Summary:**

- Migration: `YYYY_MM_DD_HHMM-[hash]_phase_4_8_add_audit_indexes_task2.py`
- Test Suite: `test_phase_4_8_audit_indexes.py` - [X] tests ✅
- Final Results: [613 + X]/[613 + X] unit tests passing (100%), [640 + X]/[640 + X] total tests passing (100%)

**Key Changes:**
- ✅ Added idx_audit_event_tenant_time for tenant-scoped audit queries
- ✅ Added idx_audit_event_entity_search for entity-specific audit trails
- ✅ Added idx_audit_event_user_action_time for user action history

**Verification:**
- All 3 indexes verified via pg_indexes query
- Indexes in audit schema correctly specified
- Indexes include DESC ordering on occurred_at column
```

---

## Success Criteria

**MUST COMPLETE ALL BEFORE MARKING TASK AS DONE:**

### For Task 2 (Audit Domain Indexes - HIGH):
- [ ] **Regression baseline captured** (613/613 unit, 640/640 total tests)
- [ ] **Query patterns reviewed** to determine optimal column order
- [ ] **Alembic migration created** (no SQLModel changes)
- [ ] **Used `sa.text()` wrapper** for DESC ordering in indexes
- [ ] **Specified `schema='audit'`** for all index operations
- [ ] **⚠️ CRITICAL: Checked migration for `audit.event` table** and removed if present
- [ ] **Migration applied successfully** (`alembic upgrade head`)
- [ ] **Index verification tests passing** (1-2 tests confirming existence)
- [ ] **ALL 613 existing unit tests still passing** (no regression)
- [ ] **ALL 640 total tests still passing** (no regression)
- [ ] **Database verification query confirms** all 3 indexes created in audit schema
- [ ] **Indexes include correct columns** in optimal order (filter → sort)
- [ ] **Migration rollback tested** (`alembic downgrade -1` then `upgrade head`)
- [ ] **Project plan document updated**

### For ALL Tasks:
- [ ] **100% test pass rate** - No failing tests
- [ ] **Zero regression** - Baseline maintained or exceeded

---

## Key Files to Review

### Architecture & Design
- `dev-docs/analysis/phase-4.8-db-schema-sync-4-plan.md` - **Task 2 Details** ⭐
- `dev-docs/analysis/phase-4.8-db-schema-sync-4-analysis.md` - Forensic Analysis
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - **Golden Master JSON**

### Backend Code
- `backend/app/models/core.py` - AuditEvent model (in audit schema)

### Tests (Reference for Patterns)
- `backend/tests/test_phase_4_7_*.py` - Phase 4.7 test patterns
- `backend/tests/conftest.py` - Test fixtures (`db_session`, `test_tenant`, etc.)

---

## Risk Assessment

**For Task 2 (Audit Domain Indexes):**
- **Performance Risk:** NONE (indexes only improve performance)
- **Regression Risk:** VERY LOW (indexes don't affect application logic)
- **Migration Time:** LOW (index builds may take seconds on audit.event table)
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
- **Schema Specification:** MUST specify `schema='audit'` for audit.event table operations
- **Dual Master Strategy:** JSON is documentation authority, SQL database is runtime authority
- **Zero Regression Policy:** All 613 unit + 640 total tests MUST pass after changes

### Phase 4.8 Specific
- **Final performance optimization** - Missing composite indexes from ORM autogeneration
- **All Phase 2 tasks are migrations** - No SQLModel changes needed
- **Domain-specific index tasks** - Broken into 7 focused tasks for manageability
- **Test coverage optional for indexes** - Indexes don't change behavior, existence tests sufficient
- **Audit schema special handling** - Must specify `schema='audit'` in all operations

### If You Get Stuck
- Use `postgres-local` MCP server to query database state in real-time
- Review Phase 4.7 completed tasks for migration patterns
- Search existing tests for `db_session` and `exec()` patterns
- Review the "Best Practices" section at the top of this template
- Check pg_indexes for existing index patterns: `SELECT * FROM pg_indexes WHERE schemaname = 'audit' AND tablename = 'event';`
- Remember: Column order in composite indexes matters (filter → sort)
- Remember: `schema='audit'` must be specified for audit.event operations

---

## Example Task Flow

### For Task 2 (Audit Domain Indexes):

```bash
# 1. Baseline - Capture starting point
cd backend
source .venv/bin/activate

# Run unit tests (no integration)
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Record: 613 passed

# Run all tests (including integration)
pytest tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Record: 640 passed

# 2. Review query patterns
# - Tenant-scoped: WHERE tenant_id = X ORDER BY occurred_at DESC
# - Entity audit: WHERE entity_name = X AND entity_id = Y ORDER BY occurred_at DESC
# - User actions: WHERE user_id = X AND action = Y ORDER BY occurred_at DESC

# 3. Create migration
alembic revision --autogenerate -m "phase_4_8_add_audit_indexes_task2"

# 4. ⚠️ CRITICAL: Review migration file
# Search for 'audit' and 'event'
# DELETE any op.create_table('event', ... schema='audit') blocks in upgrade
# DELETE any op.drop_table('event', ... schema='audit') blocks in downgrade
# DELETE any other index/constraint operations on event table not in your task
# Verify your 3 index creations are present

# 5. Edit migration file to add indexes
# Use pattern from Requirements section above
# - op.create_index('idx_audit_event_tenant_time', 'event', [...], schema='audit')
# - op.create_index('idx_audit_event_entity_search', 'event', [...], schema='audit')
# - op.create_index('idx_audit_event_user_action_time', 'event', [...], schema='audit')
# - Use sa.text('occurred_at DESC') for time ordering
# - Ensure downgrade() drops all 3 indexes

# 6. Apply migration
alembic upgrade head

# 7. Verify indexes created using MCP server
# Query: SELECT indexname FROM pg_indexes 
#        WHERE schemaname = 'audit' AND tablename = 'event'
#        AND indexname IN (...)

# 8. Create test suite (optional)
# Create backend/tests/test_phase_4_8_audit_indexes.py
# - Test verifying all 3 indexes exist via pg_indexes query
# - Optionally test index definitions contain expected columns

# 9. Run tests
pytest tests/test_phase_4_8_audit_indexes.py -v

# 10. Regression check
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
pytest tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Should be 613-615 unit, 640-642 total (613+0-2 new tests)

# 11. Rollback test
alembic downgrade -1
alembic upgrade head
pytest tests/ -v

# 12. Update docs
# Edit dev-docs/analysis/phase-4.8-db-schema-sync-4-plan.md
# Mark Task 2 as complete with test results
```

---

## Questions to Ask

**Before starting:**
1. Have I captured the 613/613 unit and 640/640 total baselines?
2. Do I understand the query patterns and optimal column order (filter → sort)?
3. Do I know to specify `schema='audit'` for all index operations?

**During implementation:**
1. Am I using `db_session` parameter (NOT `session`) in tests?
2. Am I using `select()/exec()` pattern (NOT `query()`) in tests?
3. After running `alembic revision --autogenerate`, did I check for and remove `audit.event` table creation?
4. Am I using `sa.text('occurred_at DESC')` for time ordering?
5. Am I specifying `schema='audit'` for all index operations?
6. Are my index columns in the right order (filter → sort)?

**After implementation:**
1. Do I have 100% test pass rate on BOTH unit tests and total tests?
2. Do all 3 expected indexes exist in pg_indexes with schemaname='audit'?
3. Have I updated the project plan document?
4. Have I tested migration rollback (`alembic downgrade -1`)?

---

**Ready to Begin!** 🚀

### Task 2 Checklist (Audit Domain Indexes - HIGH):
1. ✅ Capture baseline (613/613 unit, 640/640 total)
2. 📖 Review query patterns and determine column order
3. 📝 Create migration (indexes only, no SQLModel)
4. 🛠️ Use `sa.text('occurred_at DESC')` for time ordering
5. 🔧 Specify `schema='audit'` for all operations
6. ⚠️ **CRITICAL: Remove `audit.event` table from migration if present**
7. ✅ Apply migration (`alembic upgrade head`)
8. 🔍 Verify 3 indexes exist via pg_indexes query (schemaname='audit')
9. 🧪 Create simple existence tests (optional)
10. 🔄 Run regression tests (minimal change expected)
11. ↩️ Test rollback (`alembic downgrade -1`, then `upgrade head`)
12. 📚 Update project plan

Remember: This task adds 3 composite indexes to the audit.event table to optimize tenant-scoped queries, entity audit trails, and user action history. The indexes are in the **audit schema**, so all operations must specify `schema='audit'`. Always check for the `audit.event` table creation issue in autogenerated migrations!
