# Task 6: Add Integration Domain Composite Indexes

**Reference:** `dev-docs/analysis/phase-4.8-db-schema-sync-4-plan.md` - Phase 2, Task 6
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

**Phase 4.8 Phase 1:** ✅ COMPLETE (April 8, 2026)
- ✅ Task 1: Replace Legacy User Check Constraints - 613/613 unit tests, 640/640 total tests passing (100%)

**Phase 4.8 Phase 2 Progress:**
- ✅ Task 2: Audit Domain Indexes - 617/617 unit tests, 644/644 total tests passing (100%)
- ✅ Task 3: Quoting Domain Indexes - 619/619 unit tests, 646/646 total tests passing (100%)
- ✅ Task 4: Billing Domain Indexes - 621/621 unit tests, 648/648 total tests passing (100%)
- ✅ Task 5: Job/Fulfillment Domain Indexes - 624/624 unit tests, 651/651 total tests passing (100%)

**Current Baseline:** 624/624 unit tests, 651/651 total tests passing (100%)

**See:**
- `dev-docs/analysis/phase-4.5-db-schema-sync-to-design-plan.md` for Phase 4.5 history
- `dev-docs/analysis/phase-4.6-db-schema-sync-2-plan.md` for Phase 4.6 history
- `dev-docs/analysis/phase-4.7-db-schema-sync-3-plan.md` for Phase 4.7 history

---

## Current Task: Add Integration Domain Composite Indexes

**Effort:** 0.5 days
**Gap Reference:** Phase 4.8 Analysis - Section 2: Missing Composite Indexes (integration_sync_*)
**Change Type:** MIGRATION

This task adds 4 critical composite indexes to the integration domain tables (`integration_sync_mapping`, `integration_sync_conflict`, `integration_sync_log`) to optimize QuickBooks bidirectional entity lookups and sync operation queries. These indexes are essential for fast entity mapping lookups during sync operations.

### What Needs to Be Fixed

| # | Component | Issue | Impact | Complexity |
|---|-----------|-------|--------|------------|
| **1** | `integration_sync_mapping` | Missing idx_ism_entity composite index for entity type + ID lookups | HIGH - Slow AevoFab entity → QuickBooks ID lookups | LOW |
| **2** | `integration_sync_mapping` | Missing idx_ism_external composite index for external system + ID lookups | HIGH - Slow QuickBooks ID → AevoFab entity lookups | LOW |
| **3** | `integration_sync_conflict` | Missing idx_isc_tenant_status composite index for tenant-scoped conflict filtering | MEDIUM - Slow conflict resolution queries | LOW |
| **4** | `integration_sync_log` | Missing idx_isl_tenant_service composite index for tenant-scoped sync history queries | MEDIUM - Slow sync audit trail queries | LOW |

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

**Record the output of both results:** `624/624 & 651/651 tests passing` (Phase 4.8 baseline - Task 5 completion)

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

This task adds **4 composite indexes** to the integration domain tables to optimize QuickBooks sync operations and entity mapping lookups. These indexes are critical for bidirectional entity lookups during sync operations.

**Problem:** Integration sync tables lack composite indexes for entity lookups and sync operations.

**Missing Indexes:**
```sql
-- 1. Sync mapping by entity type + ID (lookup AevoFab entity → QuickBooks ID)
CREATE INDEX idx_ism_entity 
ON integration_sync_mapping (entity_type_code, entity_id);

-- 2. Sync mapping by external system (lookup QuickBooks ID → AevoFab entity)
CREATE INDEX idx_ism_external 
ON integration_sync_mapping (app_service_id, external_id);

-- 3. Sync conflict tenant status filtering
CREATE INDEX idx_isc_tenant_status 
ON integration_sync_conflict (tenant_id, status);

-- 4. Sync log tenant + service + time ordering
CREATE INDEX idx_isl_tenant_service 
ON integration_sync_log (tenant_id, app_service_id, started_at DESC);
```

**Query Performance Impact:**
```sql
-- Common query: "Find QuickBooks customer ID for this AevoFab customer"
SELECT external_id FROM integration_sync_mapping
WHERE entity_type_code = 'customer'
  AND entity_id = '...';
-- WITHOUT index: Full table scan
-- WITH idx_ism_entity: Direct index lookup (optimal)

-- Common query: "Find AevoFab customer for this QuickBooks ID"
SELECT entity_id FROM integration_sync_mapping
WHERE app_service_id = '...'
  AND external_id = 'Customer|12345';
-- WITHOUT index: Full table scan
-- WITH idx_ism_external: Direct index lookup (optimal)

-- Common query: "Show me all unresolved sync conflicts for this tenant"
SELECT * FROM integration_sync_conflict
WHERE tenant_id = '...'
  AND status = 'unresolved';
-- WITHOUT index: Full table scan
-- WITH idx_isc_tenant_status: Index scan (optimal)

-- Common query: "Show me sync history for this tenant and QuickBooks"
SELECT * FROM integration_sync_log
WHERE tenant_id = '...'
  AND app_service_id = '...'
ORDER BY started_at DESC;
-- WITHOUT index: Full table scan + sort
-- WITH idx_isl_tenant_service: Index scan (pre-sorted)
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
WHERE indexname IN (
    'idx_ism_entity',
    'idx_ism_external',
    'idx_isc_tenant_status',
    'idx_isl_tenant_service'
)
ORDER BY tablename, indexname;
```

---

### 2. Implementation Order

**For Task 6 (Integration Indexes - HIGH):**

1. **✅ Establish Regression Baseline** (624/624 unit, 651/651 total tests)
2. **Review Query Patterns**
   - Read task description for common queries
   - Determine optimal column order (filters → range → sort)
3. **Create Alembic Migration** (No SQLModel changes needed)
   ```bash
   cd backend
   source .venv/bin/activate
   alembic revision -m "phase_4_8_add_integration_indexes_task6"
   ```
4. **Write Migration Logic**
   - Use `op.create_index()` for all 4 indexes
   - Use `sa.text('started_at DESC')` for the sync log time ordering
   - Ensure proper downgrade() to drop all indexes
5. **Apply Migration**
   ```bash
   alembic upgrade head
   ```
6. **Create Test Suite** (Optional but Recommended)
   - Create `backend/tests/test_phase_4_8_integration_indexes.py`
   - Verify indexes exist via pg_indexes query
   - Keep tests simple (index existence checks)
7. **Run Tests**
   ```bash
   pytest tests/test_phase_4_8_integration_indexes.py -v
   ```
8. **Run Regression Tests** (see "After You Complete" section)
9. **Update Documentation**

---

### 3. Test Requirements

**⚠️ ZERO REGRESSION POLICY:**
- **ALL 624 existing unit tests MUST still pass**
- **ALL 651 total tests (including integration) MUST still pass**
- **New tests (if added) MUST pass**
- **Target: 100% pass rate on both test suites**

#### For Task 6 (Integration Indexes)

**Test File:** `backend/tests/test_phase_4_8_integration_indexes.py`

**Required Coverage (2 Tests Minimum):**
```python
"""
Test Suite: Phase 4.8 Task 6 - Add Integration Domain Composite Indexes
Tests index creation for QuickBooks sync query performance optimization

Reference: phase-4.8-db-schema-sync-4-plan.md
"""
import pytest
from sqlmodel import Session
from sqlalchemy import text

class TestIntegrationIndexes:
    """Verify integration domain composite indexes were created"""
    
    def test_integration_indexes_exist(self, db_session: Session):
        """Verify all 4 integration indexes were created"""
        result = db_session.execute(text("""
            SELECT indexname FROM pg_indexes
            WHERE indexname IN (
                'idx_ism_entity',
                'idx_ism_external',
                'idx_isc_tenant_status',
                'idx_isl_tenant_service'
            )
            ORDER BY indexname
        """))
        indexes = [row[0] for row in result]
        expected_count = 4
        assert len(indexes) == expected_count, \
            f"Expected {expected_count} indexes, found {len(indexes)}: {indexes}"
    
    def test_sync_mapping_entity_index_definition(self, db_session: Session):
        """Verify entity lookup index has correct definition"""
        result = db_session.execute(text("""
            SELECT indexdef FROM pg_indexes
            WHERE indexname = 'idx_ism_entity'
        """))
        indexdef = result.fetchone()[0]
        
        # Verify index includes expected columns in correct order
        assert 'entity_type_code' in indexdef
        assert 'entity_id' in indexdef
        assert 'integration_sync_mapping' in indexdef
```

**Test Patterns to Follow:**
- Review `backend/tests/test_phase_4_8_audit_indexes.py` - Task 2 index patterns
- Review `backend/tests/test_phase_4_8_job_indexes.py` - Task 5 index patterns
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
- **For Task 6 (Indexes):** `[624 + 2] = 626 passed` (unit), `[651 + 2] = 653 passed` (total) - 2 new index verification tests

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

Find Phase 2, Task 6 and update with:

```markdown
### Task 6: Add Integration Domain Composite Indexes

**Status:** ✅ COMPLETE (YYYY-MM-DD)
**Effort:** 0.5 days (actual)
**Priority:** HIGH
**Change Type:** MIGRATION

**Implementation Summary:**

- Migration: `YYYY_MM_DD_HHMM-[hash]_phase_4_8_add_integration_indexes_task6.py`
- Test Suite: `test_phase_4_8_integration_indexes.py` - 2 tests ✅
- Final Results: 626/626 unit tests passing (100%), 653/653 total tests passing (100%)

**Key Changes:**
- ✅ Added idx_ism_entity for entity type + ID lookups
- ✅ Added idx_ism_external for external system + ID lookups
- ✅ Added idx_isc_tenant_status for conflict filtering
- ✅ Added idx_isl_tenant_service for sync history queries

**Verification:**
- All 4 indexes verified via pg_indexes query
- Bidirectional entity mapping lookups optimized
- Migration rollback tested successfully
```

---

## Success Criteria

**MUST COMPLETE ALL BEFORE MARKING TASK AS DONE:**

### For Task 6 (Integration Indexes - HIGH):
- [ ] **Regression baseline captured** (624/624 unit, 651/651 total tests)
- [ ] **Query patterns reviewed** to determine optimal column order
- [ ] **Alembic migration created** (no SQLModel changes)
- [ ] **Used `op.create_index()` for all 4 indexes**
- [ ] **Used `sa.text('started_at DESC')` for time ordering in idx_isl_tenant_service**
- [ ] **⚠️ CRITICAL: Checked migration for `audit.event` table** and removed if present
- [ ] **Migration applied successfully** (`alembic upgrade head`)
- [ ] **Index verification tests passing** (2 tests confirming existence)
- [ ] **ALL 624 existing unit tests still passing** (no regression)
- [ ] **ALL 651 total tests still passing** (no regression)
- [ ] **Database verification query confirms** all 4 indexes created
- [ ] **Indexes include correct columns** in optimal order:
  - idx_ism_entity: (entity_type_code, entity_id)
  - idx_ism_external: (app_service_id, external_id)
  - idx_isc_tenant_status: (tenant_id, status)
  - idx_isl_tenant_service: (tenant_id, app_service_id, started_at DESC)
- [ ] **Migration rollback tested** (`alembic downgrade -1` then `upgrade head`)
- [ ] **Project plan document updated**

### For ALL Tasks:
- [ ] **100% test pass rate** - No failing tests
- [ ] **Zero regression** - Baseline maintained or exceeded

---

## Key Files to Review

### Architecture & Design
- `dev-docs/analysis/phase-4.8-db-schema-sync-4-plan.md` - **Task 6 Details** ⭐
- `dev-docs/analysis/phase-4.8-db-schema-sync-4-analysis.md` - Forensic Analysis
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - **Golden Master JSON**

### Backend Code
- `backend/app/models/integration.py` - IntegrationSyncMapping, IntegrationSyncConflict, IntegrationSyncLog models

### Tests (Reference for Patterns)
- `backend/tests/test_phase_4_8_audit_indexes.py` - Task 2 index patterns
- `backend/tests/test_phase_4_8_job_indexes.py` - Task 5 index patterns
- `backend/tests/conftest.py` - Test fixtures (`db_session`, `test_tenant`, etc.)

---

## Risk Assessment

**For Task 6 (Integration Indexes):**
- **Performance Risk:** NONE (indexes only improve performance)
- **Regression Risk:** VERY LOW (indexes don't affect application logic)
- **Migration Time:** LOW (integration tables typically small in MVP)
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
- **Zero Regression Policy:** All 624 unit + 651 total tests MUST pass after changes

### Phase 4.8 Specific
- **Final performance optimization** - Missing composite indexes from ORM autogeneration
- **All tasks are migrations** - No JSON-only tasks (unlike phases 4.6 and 4.7)
- **Domain-specific index tasks** - Broken into 7 focused tasks for manageability
- **Test coverage optional for indexes** - Indexes don't change behavior, existence tests sufficient
- **QuickBooks sync critical** - These indexes directly impact sync performance

### If You Get Stuck
- Use `postgres-local` MCP server to query database state in real-time
- Review Task 2 (audit indexes) and Task 5 (job indexes) for migration patterns
- Search existing tests for `db_session` and `exec()` patterns
- Review the "Best Practices" section at the top of this template
- Check pg_indexes for existing index patterns: `SELECT * FROM pg_indexes WHERE tablename = 'integration_sync_mapping';`
- Remember: Column order in composite indexes matters (filter → range → sort)

---

## Example Task Flow

### For Task 6 (Integration Indexes):

```bash
# 1. Baseline - Capture starting point
cd backend
source .venv/bin/activate

pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Record: 624 passed

pytest tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Record: 651 passed

# 2. Review query patterns in task description
# Determine optimal column order:
# - idx_ism_entity: (entity_type_code, entity_id) - equality filters
# - idx_ism_external: (app_service_id, external_id) - equality filters
# - idx_isc_tenant_status: (tenant_id, status) - equality filters
# - idx_isl_tenant_service: (tenant_id, app_service_id, started_at DESC) - filter + sort

# 3. Create migration (no SQLModel changes)
alembic revision -m "phase_4_8_add_integration_indexes_task6"

# 4. Edit migration file
# Add 4 index creations:
# - Use op.create_index() for all indexes
# - Use sa.text('started_at DESC') for time ordering in idx_isl_tenant_service
# - Ensure proper downgrade() with all 4 index drops

# Example:
def upgrade():
    import sqlalchemy as sa
    
    # Sync mapping indexes
    op.create_index(
        'idx_ism_entity',
        'integration_sync_mapping',
        ['entity_type_code', 'entity_id']
    )
    
    op.create_index(
        'idx_ism_external',
        'integration_sync_mapping',
        ['app_service_id', 'external_id']
    )
    
    # Sync conflict index
    op.create_index(
        'idx_isc_tenant_status',
        'integration_sync_conflict',
        ['tenant_id', 'status']
    )
    
    # Sync log index with time ordering
    op.create_index(
        'idx_isl_tenant_service',
        'integration_sync_log',
        ['tenant_id', 'app_service_id', sa.text('started_at DESC')]
    )

def downgrade():
    op.drop_index('idx_isl_tenant_service', table_name='integration_sync_log')
    op.drop_index('idx_isc_tenant_status', table_name='integration_sync_conflict')
    op.drop_index('idx_ism_external', table_name='integration_sync_mapping')
    op.drop_index('idx_ism_entity', table_name='integration_sync_mapping')

# 5. ⚠️ CRITICAL: Review migration file
# Search for 'audit' and 'event'
# DELETE any op.create_table('event', ... schema='audit') blocks

# 6. Apply migration
alembic upgrade head

# 7. Verify indexes created using MCP server
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename IN ('integration_sync_mapping', 'integration_sync_conflict', 'integration_sync_log')
AND indexname IN ('idx_ism_entity', 'idx_ism_external', 'idx_isc_tenant_status', 'idx_isl_tenant_service');

# 8. Create test suite
# Create backend/tests/test_phase_4_8_integration_indexes.py
# - Simple test verifying all 4 indexes exist via pg_indexes query
# - Optional test verifying one index has correct column definition

# 9. Run tests
pytest tests/test_phase_4_8_integration_indexes.py -v

# 10. Regression check
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Expected: 626 passed (624 + 2 new)

pytest tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Expected: 653 passed (651 + 2 new)

# 11. Rollback test
alembic downgrade -1
alembic upgrade head
pytest tests/ -v  # Should still pass

# 12. Update docs
# Edit dev-docs/analysis/phase-4.8-db-schema-sync-4-plan.md
# Mark Task 6 as complete with test results
```

---

## Questions to Ask

**Before starting:**
1. Have I captured the 624/624 unit and 651/651 total baselines?
2. Do I understand the query patterns and optimal column order for each index?
3. Do I know which tables need indexes (integration_sync_mapping, integration_sync_conflict, integration_sync_log)?

**During implementation:**
1. Am I using `db_session` parameter (NOT `session`) in tests?
2. Am I using `select()/exec()` pattern (NOT `query()`) in tests?
3. After running `alembic revision`, did I check for and remove `audit.event` table creation?
4. Am I using `sa.text('started_at DESC')` for time ordering in idx_isl_tenant_service?
5. Are my index columns in the right order (filter → sort)?
6. Did I create all 4 indexes (2 on mapping, 1 on conflict, 1 on log)?

**After implementation:**
1. Do I have 100% test pass rate on BOTH unit tests and total tests?
2. Do all 4 expected indexes exist in pg_indexes?
3. Have I updated the project plan document?
4. Have I tested migration rollback (`alembic downgrade -1`)?

---

**Ready to Begin!** 🚀

### Task 6 Checklist (Integration Indexes - HIGH):
1. ✅ Capture baseline (624/624 unit, 651/651 total)
2. 📖 Review query patterns and determine column order
3. 📝 Create migration (indexes only, no SQLModel)
4. 🛠️ Create all 4 indexes using `op.create_index()`
5. 🛠️ Use `sa.text('started_at DESC')` for time ordering
6. ⚠️ **CRITICAL: Remove `audit.event` table from migration if present**
7. ✅ Apply migration (`alembic upgrade head`)
8. 🔍 Verify indexes exist via pg_indexes query
9. 🧪 Create 2 simple existence tests
10. 🔄 Run regression tests (626 unit, 653 total expected)
11. ↩️ Test rollback (`alembic downgrade -1`, then `upgrade head`)
12. 📚 Update project plan

Remember: Task 6 focuses on **QuickBooks sync performance optimization** through strategic indexing of entity mapping and sync tracking tables. These indexes are critical for fast bidirectional entity lookups during sync operations. Be thorough, verify all 4 indexes exist, and always check for the `audit.event` table issue in migrations!
