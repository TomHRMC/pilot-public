# Task [TASK_NUMBER]: [TASK_NAME]

**Reference:** `dev-docs/analysis/phase-4.8-db-schema-sync-4-plan.md` - Phase [PHASE_NUMBER], Task [TASK_NUMBER]
**Authority (Dual Master):**
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - Golden Master JSON
- Current Live Database (Phase 4.7 Post-State)
**Type:** Phase [PHASE_NUMBER] - [CATEGORY]
**Priority:** [CRITICAL/HIGH/MEDIUM]
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

## Current Task: [TASK_NAME]

**Effort:** [X] days
**Gap Reference:** Phase 4.8 Analysis - [SECTION_REFERENCE]
**Change Type:** MIGRATION

[TASK_DESCRIPTION - 2-3 sentences explaining what this task accomplishes and WHY it matters]

### What Needs to Be Fixed

| # | Component | Issue | Impact | Complexity |
|---|-----------|-------|--------|------------|
| **1** | `Component` | [Issue description] | [Business/Performance Impact] | LOW/MEDIUM/HIGH |
| **2** | ... | ... | ... | ... |

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

**Record the output of both results:** `609/609 & 636/636 tests passing` (Phase 4.8 baseline - starting from Phase 4.7 completion)

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

[IMPLEMENTATION INSTRUCTIONS - Phase 4.8 is ALL MIGRATION tasks]

#### For Task 1: Replace Legacy User Check Constraints (CRITICAL)

**Problem:** Two CHECK constraints on the `user` table hardcode obsolete platform role values ('staff', 'superadmin') that no longer exist in the current platform_role seed data. Current roles are: 'accountant', 'owner', 'support'.

**Current State (WRONG):**
```sql
-- user_platform_role_chk (STALE):
CHECK (platform_role_code IS NULL OR platform_role_code IN ('staff', 'superadmin'))

-- user_platform_mfa_required_chk (STALE):
CHECK (platform_role_code IS NULL OR 
       (platform_role_code IN ('staff', 'superadmin') AND mfa_enforced = true))
```

**JSON Schema (CORRECT):**
```json
{
  "check_constraints": [
    {
      "name": "user_platform_role_chk",
      "definition": "(is_platform_user = true AND platform_role_code IS NOT NULL) OR (is_platform_user = false AND platform_role_code IS NULL)"
    },
    {
      "name": "user_platform_mfa_required_chk",
      "definition": "(is_platform_user = false) OR (mfa_enforced = true)"
    }
  ]
}
```

**Migration Approach:**
1. Drop existing stale constraints
2. Add new constraints using boolean logic (not hardcoded roles)
3. Pre-validate: Check no users have legacy role codes
4. Post-validate: Test platform users can be assigned modern roles

**Database Verification Query:**
```sql
-- Verify constraints updated correctly
SELECT 
    conname AS constraint_name,
    pg_get_constraintdef(c.oid) AS constraint_definition
FROM pg_constraint c
JOIN pg_class t ON c.conrelid = t.oid
WHERE t.relname = 'user'
  AND contype = 'c'
  AND conname IN ('user_platform_role_chk', 'user_platform_mfa_required_chk');
```

---

#### For Tasks 2-8: Add Missing Composite Indexes (HIGH PRIORITY)

**Problem:** The JSON schema defines composite and partial indexes for optimizing common query patterns. The ORM auto-generated single-column foreign key indexes, but **missed all composite indexes**.

**Index Pattern Types:**

**Type 1: Tenant-Scoped Time-Ordered Queries**
```sql
-- Pattern: WHERE tenant_id = '...' ORDER BY created_at DESC
CREATE INDEX idx_[table]_tenant_time 
ON [table] (tenant_id, created_at DESC);
```

**Type 2: Tenant-Scoped Status Filtering with Time Ordering**
```sql
-- Pattern: WHERE tenant_id = '...' AND status_id = '...' ORDER BY created_at DESC
CREATE INDEX idx_[table]_tenant_status_created 
ON [table] (tenant_id, status_id, created_at DESC);
```

**Type 3: Entity Lookup Indexes**
```sql
-- Pattern: WHERE entity_type = '...' AND entity_id = '...'
CREATE INDEX idx_[table]_entity_search 
ON [table] (entity_type_code, entity_id, [optional_sort_column] DESC);
```

**Type 4: Partial Indexes (WHERE Clause)**
```sql
-- Pattern: WHERE status = 'pending' AND scheduled_at <= NOW()
CREATE INDEX idx_[table]_pending_scheduled 
ON [table] (status, scheduled_at)
WHERE status = 'pending';  -- Partial index only for pending records
```

**Migration Approach (Index Tasks):**
1. **NO SQLModel changes needed** - Indexes are managed via Alembic only
2. Use `op.create_index()` with `sa.text()` for DESC/ASC ordering
3. For partial indexes, use `op.execute()` with raw SQL
4. Order columns: filter columns → range columns → sort columns
5. Test index existence via pg_indexes query

**Index Creation Example:**
```python
def upgrade():
    # Standard composite index with DESC ordering
    op.create_index(
        'idx_quote_tenant_status_created_at',
        'quote',
        ['tenant_id', 'status_id', sa.text('created_at DESC')]
    )
    
    # Partial index with WHERE clause (use raw SQL)
    op.execute("""
        CREATE INDEX idx_usage_ledger_unreported 
        ON usage_ledger (tenant_id, product_feature_code, is_reported)
        WHERE is_reported = false
    """)

def downgrade():
    op.drop_index('idx_usage_ledger_unreported', table_name='usage_ledger')
    op.drop_index('idx_quote_tenant_status_created_at', table_name='quote')
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
    'idx_audit_event_tenant_time',
    'idx_quote_tenant_status_created_at',
    -- ... list all indexes for this task
)
ORDER BY tablename, indexname;
```

---

### 2. Implementation Order

**For Task 1 (Legacy Constraints - CRITICAL):**

1. **✅ Establish Regression Baseline** (609/609 unit, 636/636 total tests)
2. **Pre-Migration Data Validation**
   - Run validation queries to check for legacy role codes
   - Verify no users have 'staff' or 'superadmin' roles
3. **Create Alembic Migration** (No SQLModel changes needed - constraints only)
   ```bash
   cd backend
   source .venv/bin/activate
   alembic revision -m "phase_4_8_replace_user_check_constraints_task1"
   ```
4. **Write Migration Logic**
   - Drop old constraints
   - Add new constraints with boolean logic
   - Add pre-migration validation as comments
5. **Apply Migration**
   ```bash
   alembic upgrade head
   ```
6. **Create Test Suite**
   - Create `backend/tests/test_phase_4_8_user_check_constraints.py`
   - Test modern platform roles work
   - Test constraint violations properly rejected
7. **Run New Tests**
   ```bash
   pytest tests/test_phase_4_8_user_check_constraints.py -v
   ```
8. **Run Regression Tests** (see "After You Complete" section)
9. **Update Documentation**

---

**For Tasks 2-8 (Composite Indexes - HIGH):**

1. **✅ Establish Regression Baseline** (609/609 unit, 636/636 total tests)
2. **Review Query Patterns**
   - Read task description for common queries
   - Determine optimal column order (filters → range → sort)
3. **Create Alembic Migration** (No SQLModel changes needed)
   ```bash
   cd backend
   source .venv/bin/activate
   alembic revision -m "phase_4_8_add_[domain]_indexes_task[N]"
   ```
4. **Write Migration Logic**
   - Use `op.create_index()` for standard indexes
   - Use `sa.text('column DESC')` for ordering
   - Use `op.execute()` for partial indexes (WHERE clause)
   - Ensure proper downgrade() to drop all indexes
5. **Apply Migration**
   ```bash
   alembic upgrade head
   ```
6. **Create Test Suite** (Optional but Recommended)
   - Create `backend/tests/test_phase_4_8_[domain]_indexes.py`
   - Verify indexes exist via pg_indexes query
   - Keep tests simple (index existence checks)
7. **Run Tests**
   ```bash
   pytest tests/test_phase_4_8_[domain]_indexes.py -v
   ```
8. **Run Regression Tests** (see "After You Complete" section)
9. **Update Documentation**

---

### 3. Test Requirements

**⚠️ ZERO REGRESSION POLICY:**
- **ALL 609 existing unit tests MUST still pass**
- **ALL 636 total tests (including integration) MUST still pass**
- **New tests (if added) MUST pass**
- **Target: 100% pass rate on both test suites**

#### For Task 1 (Legacy Constraints)

**Test File:** `backend/tests/test_phase_4_8_user_check_constraints.py`

**Required Coverage (Minimum 4 Tests):**
```python
"""
Test Suite: Phase 4.8 Task 1 - Replace Legacy User Check Constraints
Tests modern platform role assignment - final constraint logic alignment

Reference: phase-4.8-db-schema-sync-4-plan.md
"""
import pytest
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from app.models.core import User, PlatformRole

class TestUserPlatformRoleConstraints:
    """Test updated user table CHECK constraints"""
    
    def test_platform_user_requires_role(self, db_session: Session):
        """Platform users MUST have a platform_role_code"""
        user = User(
            email="platform@aevofab.example.com",
            is_platform_user=True,
            platform_role_code=None,  # Invalid!
            mfa_enforced=True
        )
        db_session.add(user)
        
        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()
        assert 'user_platform_role_chk' in str(exc_info.value)
        db_session.rollback()
    
    def test_platform_user_can_use_modern_roles(self, db_session: Session):
        """Platform users can be assigned current role codes"""
        for role_code in ['accountant', 'owner', 'support']:
            user = User(
                email=f"{role_code}@aevofab.example.com",
                is_platform_user=True,
                platform_role_code=role_code,
                mfa_enforced=True
            )
            db_session.add(user)
            db_session.commit()
            
            # Verify created successfully
            result = db_session.exec(
                select(User).where(User.email == f"{role_code}@aevofab.example.com")
            ).first()
            assert result is not None
            assert result.platform_role_code == role_code
            
            # Clean up
            db_session.delete(result)
            db_session.commit()
    
    def test_tenant_user_cannot_have_platform_role(self, db_session: Session):
        """Regular users MUST NOT have platform_role_code"""
        user = User(
            email="regular@tenant.com",
            is_platform_user=False,
            platform_role_code='owner',  # Invalid!
            mfa_enforced=False
        )
        db_session.add(user)
        
        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()
        assert 'user_platform_role_chk' in str(exc_info.value)
        db_session.rollback()
    
    def test_platform_user_must_have_mfa(self, db_session: Session):
        """All platform users MUST have MFA enforced"""
        user = User(
            email="platform@aevofab.example.com",
            is_platform_user=True,
            platform_role_code='owner',
            mfa_enforced=False  # Invalid!
        )
        db_session.add(user)
        
        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()
        assert 'user_platform_mfa_required_chk' in str(exc_info.value)
        db_session.rollback()
```

---

#### For Tasks 2-8 (Composite Indexes)

**Test File:** `backend/tests/test_phase_4_8_[domain]_indexes.py`

**Required Coverage (1-2 Tests per Domain):**
```python
"""
Test Suite: Phase 4.8 Task [N] - Add [Domain] Composite Indexes
Tests index creation for query performance optimization

Reference: phase-4.8-db-schema-sync-4-plan.md
"""
import pytest
from sqlmodel import Session
from sqlalchemy import text

class Test[Domain]Indexes:
    """Verify [domain] composite indexes were created"""
    
    def test_[domain]_indexes_exist(self, db_session: Session):
        """Verify all [X] [domain] indexes were created"""
        result = db_session.execute(text("""
            SELECT indexname FROM pg_indexes
            WHERE indexname IN (
                'idx_[table1]_[pattern1]',
                'idx_[table2]_[pattern2]',
                -- List all indexes for this task
            )
            ORDER BY indexname
        """))
        indexes = [row[0] for row in result]
        expected_count = [X]  # Number of indexes in this task
        assert len(indexes) == expected_count, \
            f"Expected {expected_count} indexes, found {len(indexes)}: {indexes}"
    
    def test_[specific_index]_definition(self, db_session: Session):
        """Verify specific index has correct definition (optional)"""
        result = db_session.execute(text("""
            SELECT indexdef FROM pg_indexes
            WHERE indexname = 'idx_[specific_index]'
        """))
        indexdef = result.fetchone()[0]
        
        # Verify index includes expected columns
        assert 'tenant_id' in indexdef
        assert 'created_at DESC' in indexdef or 'created_at' in indexdef
```

**Test Patterns to Follow:**
- Review `backend/tests/test_phase_4_7_*.py` - Phase 4.7 test patterns
- Review `backend/tests/test_check_constraints_task9.py` - Constraint testing
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
- **For Task 1 (Constraints):** `[609 + 4] passed` (unit), `[636 + 4] passed` (total)
- **For Tasks 2-8 (Indexes):** `[609 + 0-2] passed` (unit), `[636 + 0-2] passed` (total) - minimal or no new tests

### Step 3: Verify 100% Pass Rate

**If ANY tests fail:**
1. Identify failing tests
2. Determine if new or existing tests
3. Fix ALL failures before proceeding
4. Re-run until 100% pass rate

**For Index Tasks:**
- If existing tests fail → Migration broke something (rollback and fix)
- If new tests fail → Index creation failed (check migration)

**For Constraint Task:**
- If existing tests fail → Constraint logic broke existing users (rollback and fix)
- If new tests fail → Fix implementation or test logic

---

## Documentation Update

### Update Project Plan Document

**File to Update:** `dev-docs/analysis/phase-4.8-db-schema-sync-4-plan.md`

Find Phase [PHASE_NUMBER], Task [TASK_NUMBER] and update with:

```markdown
### Task [TASK_NUMBER]: [TASK_NAME]

**Status:** ✅ COMPLETE (YYYY-MM-DD)
**Effort:** [X] days (actual)
**Priority:** [CRITICAL/HIGH/MEDIUM]
**Change Type:** MIGRATION

**Implementation Summary:**

- Migration: `YYYY_MM_DD_HHMM-[hash]_[name].py`
- Test Suite: `test_phase_4_8_[name].py` - [X] tests ✅
- Final Results: [609 + X]/[609 + X] unit tests passing (100%), [636 + X]/[636 + X] total tests passing (100%)

**Key Changes:**
- ✅ [Change 1]
- ✅ [Change 2]

**Verification:**
- [How correctness was verified]
```

---

## Success Criteria

**MUST COMPLETE ALL BEFORE MARKING TASK AS DONE:**

### For Task 1 (Legacy Constraints - CRITICAL):
- [ ] **Regression baseline captured** (609/609 unit, 636/636 total tests)
- [ ] **Pre-migration data validation completed** (no legacy role codes found)
- [ ] **Alembic migration created** without SQLModel changes
- [ ] **⚠️ CRITICAL: Checked migration for `audit.event` table** and removed if present
- [ ] **Migration applied successfully** (`alembic upgrade head`)
- [ ] **All 4 new tests written and passing**
- [ ] **Tests use `db_session` parameter** and `select()/exec()` pattern
- [ ] **ALL 609 existing unit tests still passing**
- [ ] **ALL 636 total tests still passing** (including integration)
- [ ] **New total: 613/613 unit passing, 640/640 total passing (100%)**
- [ ] **Database verification query confirms** constraints updated
- [ ] **Can create platform users with modern roles** (accountant, owner, support)
- [ ] **Migration rollback tested** (`alembic downgrade -1` then `upgrade head` again)
- [ ] **Project plan document updated**

### For Tasks 2-8 (Composite Indexes - HIGH):
- [ ] **Regression baseline captured** (609+/609+ unit, 636+/636+ total tests)
- [ ] **Query patterns reviewed** to determine optimal column order
- [ ] **Alembic migration created** (no SQLModel changes)
- [ ] **Used `sa.text()` wrapper** for DESC/ASC ordering in indexes
- [ ] **Used `op.execute()` for partial indexes** with WHERE clauses
- [ ] **⚠️ CRITICAL: Checked migration for `audit.event` table** and removed if present
- [ ] **Migration applied successfully** (`alembic upgrade head`)
- [ ] **Index verification tests passing** (1-2 tests confirming existence)
- [ ] **ALL existing unit tests still passing** (no regression)
- [ ] **ALL total tests still passing** (no regression)
- [ ] **Database verification query confirms** all indexes created
- [ ] **Indexes include correct columns** in optimal order (filter → range → sort)
- [ ] **Migration rollback tested** (`alembic downgrade -1` then `upgrade head`)
- [ ] **Project plan document updated**

### For ALL Tasks:
- [ ] **100% test pass rate** - No failing tests
- [ ] **Zero regression** - Baseline maintained or exceeded

---

## Key Files to Review

### Architecture & Design
- `dev-docs/analysis/phase-4.8-db-schema-sync-4-plan.md` - **Task [TASK_NUMBER] Details** ⭐
- `dev-docs/analysis/phase-4.8-db-schema-sync-4-analysis.md` - Forensic Analysis
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - **Golden Master JSON**

### Backend Code
- `backend/app/models/core.py` - User, PlatformRole models (Task 1)
- `backend/app/models/[domain].py` - Domain models (Tasks 2-8)

### Tests (Reference for Patterns)
- `backend/tests/test_phase_4_7_*.py` - Phase 4.7 test patterns
- `backend/tests/test_check_constraints_task9.py` - CHECK constraint patterns
- `backend/tests/test_citext_email.py` - Correct `select()/exec()` usage
- `backend/tests/conftest.py` - Test fixtures (`db_session`, `test_tenant`, etc.)

---

## Risk Assessment

**For Task 1 (Legacy Constraints):**
- **Data Validation Risk:** LOW (new constraints are more permissive)
- **Regression Risk:** LOW (changes only affect future inserts/updates)
- **Deployment Impact:** CRITICAL (blocks platform user creation until fixed)
- **Mitigation:** Pre-validate no legacy role codes exist, test modern roles work

**For Tasks 2-8 (Composite Indexes):**
- **Performance Risk:** NONE (indexes only improve performance)
- **Regression Risk:** VERY LOW (indexes don't affect application logic)
- **Migration Time:** LOW-MEDIUM (index builds may take seconds on large tables)
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
- **Zero Regression Policy:** All 609 unit + 636 total tests MUST pass after changes

### Phase 4.8 Specific
- **Final performance optimization** - Missing composite indexes from ORM autogeneration
- **Legacy constraint cleanup** - Hardcoded role values blocking modern platform users
- **All tasks are migrations** - No JSON-only tasks (unlike phases 4.6 and 4.7)
- **Domain-specific index tasks** - Broken into 7 focused tasks for manageability
- **Critical deployment blocker** - Task 1 MUST be completed before platform users can be created
- **Test coverage optional for indexes** - Indexes don't change behavior, existence tests sufficient

### If You Get Stuck
- Use `postgres-local` MCP server to query database state in real-time
- Review Phase 4.7 completed tasks for migration patterns
- Search existing tests for `db_session` and `exec()` patterns
- Review the "Best Practices" section at the top of this template
- Check pg_indexes for existing index patterns: `SELECT * FROM pg_indexes WHERE tablename = 'your_table';`
- Remember: Column order in composite indexes matters (filter → range → sort)

---

## Example Task Flow

### For Task 1 (Legacy Constraints):

```bash
# 1. Baseline - Capture starting point
cd backend
source .venv/bin/activate

# Run unit tests (no integration)
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Record: 609 passed

# Run all tests (including integration)
pytest tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Record: 636 passed

# 2. Pre-migration data validation using MCP server
# Query for legacy platform roles
SELECT id, email, platform_role_code
FROM "user"
WHERE platform_role_code IN ('staff', 'superadmin');
# Should return 0 rows

# 3. Create migration (no SQLModel changes needed)
alembic revision -m "phase_4_8_replace_user_check_constraints_task1"

# 4. Edit migration file
# Add logic to:
# - Drop old constraints
# - Add new constraints with boolean logic
# - Include pre-migration validation as comments

# 5. ⚠️ CRITICAL: Review migration file
# Search for 'audit' and 'event'
# DELETE any op.create_table('event', ... schema='audit') blocks
# Verify your constraint changes are present

# 6. Apply migration
alembic upgrade head

# 7. Verify constraints updated
# Use MCP server to query pg_constraint
SELECT conname, pg_get_constraintdef(c.oid)
FROM pg_constraint c
JOIN pg_class t ON c.conrelid = t.oid
WHERE t.relname = 'user' AND contype = 'c'
AND conname LIKE 'user_platform%';

# 8. Create test suite
# Create backend/tests/test_phase_4_8_user_check_constraints.py
# - Use db_session: Session parameter
# - Use select() with exec()
# - Test modern roles work, legacy rules enforced

# 9. Run new tests
pytest tests/test_phase_4_8_user_check_constraints.py -v
# All 4 new tests should pass

# 10. Regression check
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Expected: 613 passed (609 + 4 new)

pytest tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Expected: 640 passed (636 + 4 new)

# 11. Rollback test
alembic downgrade -1
alembic upgrade head
pytest tests/ -v  # Should still pass

# 12. Update docs
# Edit dev-docs/analysis/phase-4.8-db-schema-sync-4-plan.md
# Mark Task 1 as complete with test results
```

---

### For Tasks 2-8 (Composite Indexes):

```bash
# 1. Baseline - Capture starting point
cd backend
source .venv/bin/activate

pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Record baseline (should be 613+ from Task 1 if completed)

pytest tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Record baseline (should be 640+ from Task 1 if completed)

# 2. Review query patterns in task description
# Determine optimal column order:
# - Equality filters first (tenant_id, status_id)
# - Range/order columns last (created_at DESC)

# 3. Create migration (no SQLModel changes)
alembic revision -m "phase_4_8_add_[domain]_indexes_task[N]"

# 4. Edit migration file
# Add index creation:
# - Use op.create_index() for standard indexes
# - Use sa.text('column DESC') for ordering
# - Use op.execute() for partial indexes (WHERE clause)

# Example:
def upgrade():
    import sqlalchemy as sa
    
    # Standard composite index
    op.create_index(
        'idx_quote_tenant_status_created_at',
        'quote',
        ['tenant_id', 'status_id', sa.text('created_at DESC')]
    )
    
    # Partial index with WHERE clause
    op.execute("""
        CREATE INDEX idx_usage_ledger_unreported 
        ON usage_ledger (tenant_id, product_feature_code, is_reported)
        WHERE is_reported = false
    """)

def downgrade():
    op.drop_index('idx_usage_ledger_unreported', table_name='usage_ledger')
    op.drop_index('idx_quote_tenant_status_created_at', table_name='quote')

# 5. ⚠️ CRITICAL: Review migration file
# Search for 'audit' and 'event'
# DELETE any op.create_table('event', ... schema='audit') blocks

# 6. Apply migration
alembic upgrade head

# 7. Verify indexes created using MCP server
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = '[your_table]'
AND indexname IN ('idx_[index1]', 'idx_[index2]');

# 8. Create test suite (optional but recommended)
# Create backend/tests/test_phase_4_8_[domain]_indexes.py
# - Simple test verifying indexes exist via pg_indexes query

# 9. Run tests
pytest tests/test_phase_4_8_[domain]_indexes.py -v

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
# Mark task as complete
```

---

## Questions to Ask

**Before starting:**
1. Have I captured the 609/609 unit and 636/636 total baselines?
2. For Task 1: Have I verified no users have legacy platform role codes?
3. For Tasks 2-8: Do I understand the query patterns and optimal column order?
4. Do I have the correct index type (standard composite vs partial with WHERE)?

**During implementation:**
1. Am I using `db_session` parameter (NOT `session`) in tests?
2. Am I using `select()/exec()` pattern (NOT `query()`) in tests?
3. After running `alembic revision`, did I check for and remove `audit.event` table creation?
4. For indexes: Am I using `sa.text('column DESC')` for ordering?
5. For partial indexes: Am I using `op.execute()` with raw SQL?
6. Are my index columns in the right order (filter → range → sort)?

**After implementation:**
1. Do I have 100% test pass rate on BOTH unit tests and total tests?
2. For Task 1: Can I create platform users with modern roles (accountant, owner, support)?
3. For Tasks 2-8: Do all expected indexes exist in pg_indexes?
4. Have I updated the project plan document?
5. Have I tested migration rollback (`alembic downgrade -1`)?

---

**Ready to Begin!** 🚀

### Task 1 Checklist (Legacy Constraints - CRITICAL):
1. ✅ Capture baseline (609/609 unit, 636/636 total)
2. 🔍 Validate no legacy role codes (staff, superadmin)
3. 📝 Create migration (no SQLModel changes)
4. ⚠️ **CRITICAL: Remove `audit.event` table from migration if present**
5. ✅ Apply migration (`alembic upgrade head`)
6. 🧪 Create 4 constraint tests (modern roles, violations)
7. 🔄 Run regression tests (613 unit, 640 total expected)
8. ↩️ Test rollback (`alembic downgrade -1`, then `upgrade head`)
9. 📚 Update project plan

### Tasks 2-8 Checklist (Composite Indexes - HIGH):
1. ✅ Capture baseline (starting from Task 1 completion)
2. 📖 Review query patterns and determine column order
3. 📝 Create migration (indexes only, no SQLModel)
4. 🛠️ Use `sa.text()` for DESC/ASC, `op.execute()` for partial indexes
5. ⚠️ **CRITICAL: Remove `audit.event` table from migration if present**
6. ✅ Apply migration (`alembic upgrade head`)
7. 🔍 Verify indexes exist via pg_indexes query
8. 🧪 Create simple existence tests (optional)
9. 🔄 Run regression tests (minimal change expected)
10. ↩️ Test rollback (`alembic downgrade -1`, then `upgrade head`)
11. 📚 Update project plan

Remember: Phase 4.8 is about **final performance optimization** and **legacy constraint cleanup** before production deployment. Task 1 is CRITICAL (deployment blocker), Tasks 2-8 are HIGH priority (query performance). Be thorough, verify indexes exist, and always check for the `audit.event` table issue in migrations!
