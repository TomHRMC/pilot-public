# Task 4: Add Billing Domain Composite Indexes

**Reference:** `dev-docs/analysis/phase-4.8-db-schema-sync-4-plan.md` - Phase 2, Task 4
**Authority (Dual Master):**
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - Golden Master JSON
- Current Live Database (Phase 4.7 Post-State)
**Type:** Phase 2 - Performance Optimization
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

**Phase 4.8 - Task 1 Status:** ✅ COMPLETE (April 8, 2026)
- ✅ 613/613 unit tests passing (100%)
- ✅ 640/640 total tests passing (100%)
- ✅ Legacy user check constraints replaced with boolean logic
- ✅ Platform users can now be assigned modern roles

**Phase 4.8 - Task 2 Status:** ✅ COMPLETE (April 8, 2026)
- ✅ 617/617 unit tests passing (100%)
- ✅ 644/644 total tests passing (100%)
- ✅ 3 audit domain composite indexes added

**Phase 4.8 - Task 3 Status:** ✅ COMPLETE (April 8, 2026)
- ✅ 619/619 unit tests passing (100%)
- ✅ 646/646 total tests passing (100%)
- ✅ 1 quoting domain composite index added

**Current Baseline:** 619/619 unit tests, 646/646 total tests passing (100%)

**See:**
- `dev-docs/analysis/phase-4.5-db-schema-sync-to-design-plan.md` for Phase 4.5 history
- `dev-docs/analysis/phase-4.6-db-schema-sync-2-plan.md` for Phase 4.6 history
- `dev-docs/analysis/phase-4.7-db-schema-sync-3-plan.md` for Phase 4.7 history

---

## Current Task: Add Billing Domain Composite Indexes

**Effort:** 0.5 days
**Gap Reference:** Phase 4.8 Analysis - Section 2: Missing Composite Indexes (invoice, subscription_usage, usage_ledger)
**Change Type:** MIGRATION

The billing domain tables (`invoice`, `subscription_usage`, `usage_ledger`) lack composite indexes for common query patterns. This task adds 5 strategic indexes to optimize invoice status filtering, usage reporting, and billing cycle queries.

### What Needs to Be Fixed

| # | Component | Issue | Impact | Complexity |
|---|-----------|-------|--------|------------|
| **1** | `invoice` | Missing `idx_invoice_status_due_at` composite index | Overdue invoice queries require full table scan | LOW |
| **2** | `invoice` | Missing `idx_invoice_created_at` time-series index | Invoice list sorting requires full scan + sort | LOW |
| **3** | `subscription_usage` | Missing `idx_su_tenant_product_feature_period` composite index | Usage summary queries inefficient | LOW |
| **4** | `usage_ledger` | Missing `idx_ul_subscription_product_feature_time` composite index | Detailed usage history queries slow | LOW |
| **5** | `usage_ledger` | Missing `idx_usage_ledger_unreported` partial index | Billing cycle unreported usage queries scan full table | MEDIUM |

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

**Record the output of both results:** `619/619 & 646/646 tests passing` (Phase 4.8 baseline - starting from Task 3 completion)

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

**This is a MIGRATION-ONLY task** - No SQLModel changes needed. All indexes are created via Alembic migration only.

#### Index Patterns

**Type 1: Invoice Status + Due Date Filtering**
```sql
-- Pattern: WHERE status_id = '...' AND due_at < NOW() ORDER BY due_at
CREATE INDEX idx_invoice_status_due_at 
ON invoice (status_id, due_at);
```

**Type 2: Time-Series Ordering**
```sql
-- Pattern: ORDER BY created_at DESC (invoice list view)
CREATE INDEX idx_invoice_created_at 
ON invoice (created_at DESC);
```

**Type 3: Subscription Usage Composite**
```sql
-- Pattern: WHERE subscription_id = '...' AND product_feature_code = '...' ORDER BY period_end DESC
CREATE INDEX idx_su_tenant_product_feature_period 
ON subscription_usage (subscription_id, product_feature_code, period_end DESC);
```

**Type 4: Usage Ledger Time-Series**
```sql
-- Pattern: WHERE subscription_id = '...' AND product_feature_code = '...' ORDER BY occurred_at DESC
CREATE INDEX idx_ul_subscription_product_feature_time 
ON usage_ledger (subscription_id, product_feature_code, occurred_at DESC);
```

**Type 5: Partial Index for Unreported Usage**
```sql
-- Pattern: WHERE tenant_id = '...' AND product_feature_code = '...' AND is_reported = false
CREATE INDEX idx_usage_ledger_unreported 
ON usage_ledger (tenant_id, product_feature_code, is_reported)
WHERE is_reported = false;  -- Partial index only for unreported records
```

#### Migration Approach

1. **NO SQLModel changes needed** - Indexes are managed via Alembic only
2. Use `op.create_index()` with `sa.text()` for DESC/ASC ordering
3. For partial indexes (WHERE clause), use `op.execute()` with raw SQL
4. Order columns: filter columns → range columns → sort columns
5. Test index existence via pg_indexes query

#### Index Creation Example

```python
def upgrade():
    import sqlalchemy as sa
    
    # Standard composite index with DESC ordering
    op.create_index(
        'idx_invoice_status_due_at',
        'invoice',
        ['status_id', 'due_at']
    )
    
    # Time-series index with DESC ordering
    op.create_index(
        'idx_invoice_created_at',
        'invoice',
        [sa.text('created_at DESC')]
    )
    
    # Composite index with product feature and period
    op.create_index(
        'idx_su_tenant_product_feature_period',
        'subscription_usage',
        ['subscription_id', 'product_feature_code', sa.text('period_end DESC')]
    )
    
    # Usage ledger time-series
    op.create_index(
        'idx_ul_subscription_product_feature_time',
        'usage_ledger',
        ['subscription_id', 'product_feature_code', sa.text('occurred_at DESC')]
    )
    
    # Partial index with WHERE clause (use raw SQL)
    op.execute("""
        CREATE INDEX idx_usage_ledger_unreported 
        ON usage_ledger (tenant_id, product_feature_code, is_reported)
        WHERE is_reported = false
    """)

def downgrade():
    op.drop_index('idx_usage_ledger_unreported', table_name='usage_ledger')
    op.drop_index('idx_ul_subscription_product_feature_time', table_name='usage_ledger')
    op.drop_index('idx_su_tenant_product_feature_period', table_name='subscription_usage')
    op.drop_index('idx_invoice_created_at', table_name='invoice')
    op.drop_index('idx_invoice_status_due_at', table_name='invoice')
```

#### Database Verification Query

```sql
-- Verify all 5 billing indexes exist
SELECT 
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE indexname IN (
    'idx_invoice_status_due_at',
    'idx_invoice_created_at',
    'idx_su_tenant_product_feature_period',
    'idx_ul_subscription_product_feature_time',
    'idx_usage_ledger_unreported'
)
ORDER BY tablename, indexname;
```

---

### 2. Implementation Order

1. **✅ Establish Regression Baseline** (619/619 unit, 646/646 total tests)
2. **Review Query Patterns**
   - Invoice status + due date filtering
   - Invoice time-series sorting
   - Subscription usage by feature and period
   - Usage ledger detail queries
   - Unreported usage for billing cycles
3. **Create Alembic Migration** (No SQLModel changes needed)
   ```bash
   cd backend
   source .venv/bin/activate
   alembic revision -m "phase_4_8_add_billing_indexes_task4"
   ```
4. **Write Migration Logic**
   - Use `op.create_index()` for standard indexes
   - Use `sa.text('column DESC')` for ordering
   - Use `op.execute()` for partial index with WHERE clause
   - Ensure proper downgrade() to drop all indexes
5. **⚠️ CRITICAL: Review Migration File**
   - Search for `'event'` and `schema='audit'`
   - DELETE any `op.create_table('event', ... schema='audit')` blocks
   - DELETE any `op.drop_table('event', ... schema='audit')` blocks
   - Verify your 5 index creations are present
6. **Apply Migration**
   ```bash
   alembic upgrade head
   ```
7. **Create Test Suite** (Optional but Recommended)
   - Create `backend/tests/test_phase_4_8_billing_indexes.py`
   - Verify indexes exist via pg_indexes query
   - Keep tests simple (index existence checks)
8. **Run Tests**
   ```bash
   pytest tests/test_phase_4_8_billing_indexes.py -v
   ```
9. **Run Regression Tests** (see "After You Complete" section)
10. **Update Documentation**

---

### 3. Test Requirements

**⚠️ ZERO REGRESSION POLICY:**
- **ALL 619 existing unit tests MUST still pass**
- **ALL 646 total tests (including integration) MUST still pass**
- **New tests (if added) MUST pass**
- **Target: 100% pass rate on both test suites**

#### Test File: `backend/tests/test_phase_4_8_billing_indexes.py`

**Required Coverage (Minimum 2 Tests):**
```python
"""
Test Suite: Phase 4.8 Task 4 - Add Billing Domain Composite Indexes
Tests index creation for billing query performance optimization

Reference: phase-4.8-db-schema-sync-4-plan.md
"""
import pytest
from sqlmodel import Session
from sqlalchemy import text

class TestBillingIndexes:
    """Verify billing domain composite indexes were created"""
    
    def test_billing_indexes_exist(self, db_session: Session):
        """Verify all 5 billing indexes were created"""
        result = db_session.execute(text("""
            SELECT indexname FROM pg_indexes
            WHERE indexname IN (
                'idx_invoice_status_due_at',
                'idx_invoice_created_at',
                'idx_su_tenant_product_feature_period',
                'idx_ul_subscription_product_feature_time',
                'idx_usage_ledger_unreported'
            )
            ORDER BY indexname
        """))
        indexes = [row[0] for row in result]
        expected_count = 5
        assert len(indexes) == expected_count, \
            f"Expected {expected_count} indexes, found {len(indexes)}: {indexes}"
    
    def test_usage_ledger_unreported_partial_index(self, db_session: Session):
        """Verify unreported usage partial index has WHERE clause"""
        result = db_session.execute(text("""
            SELECT indexdef FROM pg_indexes
            WHERE indexname = 'idx_usage_ledger_unreported'
        """))
        indexdef = result.fetchone()[0]
        
        # Verify partial index includes WHERE clause
        assert 'WHERE' in indexdef
        assert 'is_reported = false' in indexdef or "is_reported = 'false'" in indexdef
        
        # Verify index includes expected columns
        assert 'tenant_id' in indexdef
        assert 'product_feature_code' in indexdef
```

**Test Patterns to Follow:**
- Review `backend/tests/test_phase_4_8_audit_indexes.py` - Task 2 patterns
- Review `backend/tests/test_phase_4_8_quote_indexes.py` - Task 3 patterns
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
- **Unit tests:** `[619 + 2] = 621 passed` (added 2 new index verification tests)
- **Total tests:** `[646 + 2] = 648 passed`

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

Find Phase 2, Task 4 and update with:

```markdown
### Task 4: Add Billing Domain Composite Indexes

**Status:** ✅ COMPLETE (2026-04-08)
**Effort:** 0.5 days (actual)
**Priority:** HIGH
**Change Type:** MIGRATION

**Implementation Summary:**

- Migration: `2026_04_08_HHMM-[hash]_phase_4_8_add_billing_indexes_task4.py`
- Test Suite: `test_phase_4_8_billing_indexes.py` - 2 tests ✅
- Final Results: 621/621 unit tests passing (100%), 648/648 total tests passing (100%)

**Key Changes:**
- ✅ Added idx_invoice_status_due_at for overdue invoice queries
- ✅ Added idx_invoice_created_at for time-series ordering
- ✅ Added idx_su_tenant_product_feature_period for subscription usage
- ✅ Added idx_ul_subscription_product_feature_time for usage ledger
- ✅ Added idx_usage_ledger_unreported partial index for billing cycles

**Verification:**
- All 5 indexes verified via pg_indexes query
- Partial index includes WHERE is_reported = false clause
- Migration rollback tested successfully
```

---

## Success Criteria

**MUST COMPLETE ALL BEFORE MARKING TASK AS DONE:**

- [ ] **Regression baseline captured** (619/619 unit, 646/646 total tests)
- [ ] **Query patterns reviewed** to determine optimal column order
- [ ] **Alembic migration created** (no SQLModel changes)
- [ ] **Used `sa.text()` wrapper** for DESC ordering in indexes
- [ ] **Used `op.execute()` for partial index** with WHERE clause
- [ ] **⚠️ CRITICAL: Checked migration for `audit.event` table** and removed if present
- [ ] **Migration applied successfully** (`alembic upgrade head`)
- [ ] **Index verification tests passing** (2 tests confirming existence)
- [ ] **ALL 619 existing unit tests still passing** (no regression)
- [ ] **ALL 646 total tests still passing** (no regression)
- [ ] **New total: 621/621 unit passing, 648/648 total passing (100%)**
- [ ] **Database verification query confirms** all 5 indexes created
- [ ] **Indexes include correct columns** in optimal order (filter → range → sort)
- [ ] **Partial index includes WHERE clause** (is_reported = false)
- [ ] **Migration rollback tested** (`alembic downgrade -1` then `upgrade head`)
- [ ] **Project plan document updated**

### For ALL Tasks:
- [ ] **100% test pass rate** - No failing tests
- [ ] **Zero regression** - Baseline maintained or exceeded

---

## Key Files to Review

### Architecture & Design
- `dev-docs/analysis/phase-4.8-db-schema-sync-4-plan.md` - **Task 4 Details** ⭐
- `dev-docs/analysis/phase-4.8-db-schema-sync-4-analysis.md` - Forensic Analysis
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - **Golden Master JSON**

### Backend Code
- `backend/app/models/billing.py` - Invoice, SubscriptionUsage, UsageLedger models

### Tests (Reference for Patterns)
- `backend/tests/test_phase_4_8_audit_indexes.py` - Task 2 index test patterns
- `backend/tests/test_phase_4_8_quote_indexes.py` - Task 3 index test patterns
- `backend/tests/conftest.py` - Test fixtures (`db_session`, `test_tenant`, etc.)

---

## Risk Assessment

**For Task 4 (Billing Domain Indexes):**
- **Performance Risk:** NONE (indexes only improve performance)
- **Regression Risk:** VERY LOW (indexes don't affect application logic)
- **Migration Time:** LOW-MEDIUM (invoice/usage_ledger tables may have data)
- **Storage Cost:** LOW (~5-10% table size per index × 5 indexes = ~25-50% overhead)
- **Mitigation:** Indexes build in background, verify existence after creation

---

## Notes

### Important Patterns to Follow
- **Virtual Environment Required:** All Python/pytest commands use `source .venv/bin/activate`
- **Use `db_session` Parameter:** NOT `session` (pytest fixture naming)
- **Use `select()/exec()` Pattern:** NOT `query()` (SQLModel standard, no deprecation warnings)
- **Check Alembic Migrations:** ALWAYS remove `audit.event` table creation if autogenerated
- **Use `sa.text()` for SQL:** Required for DESC/ASC ordering in index definitions
- **Use `op.execute()` for Partial Indexes:** Required for WHERE clauses
- **Index Column Order:** Filter columns → Range columns → Sort columns (matches query patterns)
- **Dual Master Strategy:** JSON is documentation authority, SQL database is runtime authority
- **Zero Regression Policy:** All 619 unit + 646 total tests MUST pass after changes

### Phase 4.8 Specific
- **Final performance optimization** - Missing composite indexes from ORM autogeneration
- **Domain-specific index tasks** - Billing domain (invoice, subscription_usage, usage_ledger)
- **Task 4 includes partial index** - First use of WHERE clause in index definition
- **Test coverage optional but recommended** - Indexes don't change behavior, existence tests sufficient
- **5 indexes in this task** - More than average (Tasks 2-3 had 3 and 1 respectively)

### Query Patterns for This Task

**Invoice Queries:**
```sql
-- Overdue invoices
SELECT * FROM invoice
WHERE status_id = '...' AND due_at < NOW()
ORDER BY due_at ASC;

-- Recent invoices
SELECT * FROM invoice
ORDER BY created_at DESC
LIMIT 50;
```

**Subscription Usage Queries:**
```sql
-- Usage by subscription and feature
SELECT * FROM subscription_usage
WHERE subscription_id = '...'
  AND product_feature_code = 'ai_voice_transcriptions'
ORDER BY period_end DESC;
```

**Usage Ledger Queries:**
```sql
-- Detailed usage history
SELECT * FROM usage_ledger
WHERE subscription_id = '...'
  AND product_feature_code = 'ai_voice_transcriptions'
ORDER BY occurred_at DESC;

-- Unreported usage for billing cycle
SELECT * FROM usage_ledger
WHERE tenant_id = '...'
  AND product_feature_code = 'ai_voice_transcriptions'
  AND is_reported = false;
```

### If You Get Stuck
- Use `postgres-local` MCP server to query database state in real-time
- Review Task 2 and Task 3 completed migrations for index patterns
- Search existing tests for `db_session` and `exec()` patterns
- Check pg_indexes for existing index patterns: `SELECT * FROM pg_indexes WHERE tablename = 'invoice';`
- Remember: Partial indexes with WHERE clauses must use `op.execute()` not `op.create_index()`
- Remember: Column order in composite indexes matters (filter → range → sort)

---

## Example Task Flow

```bash
# 1. Baseline - Capture starting point
cd backend
source .venv/bin/activate

# Run unit tests (no integration)
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Record: 619 passed

# Run all tests (including integration)
pytest tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Record: 646 passed

# 2. Review query patterns for billing domain
# Determine optimal column order:
# - Invoice: status_id + due_at (equality + range)
# - Invoice: created_at DESC (time-series)
# - Subscription usage: subscription_id + product_feature_code + period_end DESC
# - Usage ledger: subscription_id + product_feature_code + occurred_at DESC
# - Usage ledger unreported: tenant_id + product_feature_code + is_reported WHERE is_reported = false

# 3. Create migration (no SQLModel changes)
alembic revision -m "phase_4_8_add_billing_indexes_task4"

# 4. Edit migration file
# Add 5 index creations:
# - Use op.create_index() for standard indexes (4 indexes)
# - Use sa.text('column DESC') for ordering
# - Use op.execute() for partial index with WHERE clause (1 index)

# Example (see Requirements section for full code):
def upgrade():
    import sqlalchemy as sa
    
    # Invoice indexes
    op.create_index('idx_invoice_status_due_at', 'invoice', ['status_id', 'due_at'])
    op.create_index('idx_invoice_created_at', 'invoice', [sa.text('created_at DESC')])
    
    # Subscription usage index
    op.create_index(
        'idx_su_tenant_product_feature_period',
        'subscription_usage',
        ['subscription_id', 'product_feature_code', sa.text('period_end DESC')]
    )
    
    # Usage ledger indexes
    op.create_index(
        'idx_ul_subscription_product_feature_time',
        'usage_ledger',
        ['subscription_id', 'product_feature_code', sa.text('occurred_at DESC')]
    )
    
    # Partial index for unreported usage (WHERE clause)
    op.execute("""
        CREATE INDEX idx_usage_ledger_unreported 
        ON usage_ledger (tenant_id, product_feature_code, is_reported)
        WHERE is_reported = false
    """)

def downgrade():
    op.drop_index('idx_usage_ledger_unreported', table_name='usage_ledger')
    op.drop_index('idx_ul_subscription_product_feature_time', table_name='usage_ledger')
    op.drop_index('idx_su_tenant_product_feature_period', table_name='subscription_usage')
    op.drop_index('idx_invoice_created_at', table_name='invoice')
    op.drop_index('idx_invoice_status_due_at', table_name='invoice')

# 5. ⚠️ CRITICAL: Review migration file
# Search for 'audit' and 'event'
# DELETE any op.create_table('event', ... schema='audit') blocks
# DELETE any op.drop_table('event', ... schema='audit') blocks

# 6. Apply migration
alembic upgrade head

# 7. Verify indexes created using MCP server or psql
# SELECT indexname, indexdef FROM pg_indexes WHERE tablename IN ('invoice', 'subscription_usage', 'usage_ledger') AND indexname LIKE 'idx_%';

# 8. Create test suite
# Create backend/tests/test_phase_4_8_billing_indexes.py
# - Test verifying all 5 indexes exist via pg_indexes query
# - Test verifying partial index has WHERE clause

# 9. Run new tests
pytest tests/test_phase_4_8_billing_indexes.py -v
# All 2 new tests should pass

# 10. Regression check
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Expected: 621 passed (619 + 2 new)

pytest tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Expected: 648 passed (646 + 2 new)

# 11. Rollback test
alembic downgrade -1
alembic upgrade head
pytest tests/ -v  # Should still pass

# 12. Update docs
# Edit dev-docs/analysis/phase-4.8-db-schema-sync-4-plan.md
# Mark Task 4 as complete with test results
```

---

## Questions to Ask

**Before starting:**
1. Have I captured the 619/619 unit and 646/646 total baselines?
2. Do I understand the 5 different query patterns and optimal column order?
3. Do I know which index requires a partial WHERE clause (unreported usage)?
4. Do I have the correct index type (standard composite vs partial with WHERE)?

**During implementation:**
1. Am I using `db_session` parameter (NOT `session`) in tests?
2. Am I using `select()/exec()` pattern (NOT `query()`) in tests?
3. After running `alembic revision`, did I check for and remove `audit.event` table creation?
4. For standard indexes: Am I using `sa.text('column DESC')` for ordering?
5. For partial index: Am I using `op.execute()` with raw SQL and WHERE clause?
6. Are my index columns in the right order (filter → range → sort)?

**After implementation:**
1. Do I have 100% test pass rate on BOTH unit tests and total tests?
2. Do all 5 expected indexes exist in pg_indexes?
3. Does the partial index include the WHERE is_reported = false clause?
4. Have I updated the project plan document?
5. Have I tested migration rollback (`alembic downgrade -1`)?

---

**Ready to Begin!** 🚀

### Task 4 Checklist (Billing Domain Indexes - HIGH):
1. ✅ Capture baseline (619/619 unit, 646/646 total)
2. 📖 Review query patterns and determine column order
3. 📝 Create migration (indexes only, no SQLModel)
4. 🛠️ Use `sa.text()` for DESC ordering, `op.execute()` for partial index
5. ⚠️ **CRITICAL: Remove `audit.event` table from migration if present**
6. ✅ Apply migration (`alembic upgrade head`)
7. 🔍 Verify 5 indexes exist via pg_indexes query
8. 🧪 Create 2 index verification tests
9. 🔄 Run regression tests (621 unit, 648 total expected)
10. ↩️ Test rollback (`alembic downgrade -1`, then `upgrade head`)
11. 📚 Update project plan

Remember: This task adds **5 indexes** (2 on invoice, 1 on subscription_usage, 2 on usage_ledger) including the first **partial index with WHERE clause** in Phase 4.8. The unreported usage partial index is critical for billing cycle queries. Be thorough, verify all indexes exist, and always check for the `audit.event` table issue in migrations!
