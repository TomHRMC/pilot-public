# Task 7: Add Communication Domain Composite Indexes

**Reference:** `dev-docs/analysis/phase-4.8-db-schema-sync-4-plan.md` - Phase 2, Task 7
**Authority (Dual Master):**
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - Golden Master JSON
- Current Live Database (Phase 4.7 Post-State)
**Type:** Phase 2 - Performance Index Optimization
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

**Phase 4.8 Tasks Completed:**
- ✅ Task 1: Replace Legacy User Check Constraints (613/613 unit, 640/640 total)
- ✅ Task 2: Add Audit Domain Composite Indexes (617/617 unit, 644/644 total)
- ✅ Task 3: Add Quoting Domain Composite Indexes (619/619 unit, 646/646 total)
- ✅ Task 4: Add Billing Domain Composite Indexes (621/621 unit, 648/648 total)
- ✅ Task 5: Add Job/Fulfillment Domain Composite Indexes (624/624 unit, 651/651 total)
- ✅ Task 6: Add Integration Domain Composite Indexes (626/626 unit, 653/653 total)

**Current Baseline:** 626/626 unit tests, 653/653 total tests passing (100%)

**See:**
- `dev-docs/analysis/phase-4.5-db-schema-sync-to-design-plan.md` for Phase 4.5 history
- `dev-docs/analysis/phase-4.6-db-schema-sync-2-plan.md` for Phase 4.6 history
- `dev-docs/analysis/phase-4.7-db-schema-sync-3-plan.md` for Phase 4.7 history

---

## Current Task: Add Communication Domain Composite Indexes

**Effort:** 0.5 days
**Gap Reference:** Phase 4.8 Analysis - Section 2: Missing Composite Indexes (conversation_message, notification_outbox)
**Change Type:** MIGRATION

Communication tables lack composite indexes for conversation threading and notification scheduling. This task adds 5 critical performance indexes to optimize background worker queries for notification processing and conversation history retrieval.

### What Needs to Be Fixed

| # | Component | Issue | Impact | Complexity |
|---|-----------|-------|--------|------------|
| **1** | `conversation_message` | Missing session-scoped time-ordered index | Slow conversation threading queries | LOW |
| **2** | `notification_outbox` | Missing status + scheduling composite index | Inefficient background worker queries | LOW |
| **3** | `notification_outbox` | Missing channel + status filtering index | Slow notification filtering | LOW |
| **4** | `notification_outbox` | Missing provider message ID lookup index | Slow delivery callback lookups | LOW |
| **5** | `notification_outbox` | Missing time-series ordering index | Inefficient notification history queries | LOW |

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

**Record the output of both results:** `626/626 & 653/653 tests passing` (Phase 4.8 baseline - starting from Task 6 completion)

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

**This is Task 7: Add Communication Domain Composite Indexes (HIGH PRIORITY)**

**Problem:** Communication tables lack composite indexes for conversation threading and notification scheduling.

**Current State:** Only single-column foreign key indexes exist. Missing all composite indexes for time-ordered queries, status filtering, and provider callbacks.

**Missing Indexes:**

```sql
-- 1. Conversation message session threading (chronological order)
CREATE INDEX idx_conv_msg_session_time 
ON conversation_message (session_id, created_at ASC);

-- 2. Notification outbox status + scheduling (background worker query)
CREATE INDEX idx_notif_outbox_status_sched 
ON notification_outbox (status, scheduled_at, next_attempt_at);

-- 3. Notification outbox channel + status filtering
CREATE INDEX idx_notif_outbox_channel_status 
ON notification_outbox (channel, status);

-- 4. Notification outbox provider message ID lookup (delivery callbacks)
CREATE INDEX idx_notif_outbox_provider_msg 
ON notification_outbox (provider_message_id);

-- 5. Notification outbox time-series ordering
CREATE INDEX idx_notif_outbox_created_at 
ON notification_outbox (created_at DESC);
```

**Query Performance Impact:**

```sql
-- Common query: "Get next batch of pending notifications to send"
SELECT * FROM notification_outbox
WHERE status = 'pending'
  AND scheduled_at <= NOW()
ORDER BY scheduled_at ASC
LIMIT 100;
-- WITHOUT index: Full table scan
-- WITH idx_notif_outbox_status_sched: Index scan

-- Common query: "Get conversation messages in chronological order"
SELECT * FROM conversation_message
WHERE session_id = '...'
ORDER BY created_at ASC;
-- WITHOUT index: Full table scan + sort
-- WITH idx_conv_msg_session_time: Direct index scan (pre-sorted)

-- Common query: "Find notification by Twilio message SID (delivery callback)"
SELECT * FROM notification_outbox
WHERE provider_message_id = 'SM1234567890abcdef';
-- WITHOUT index: Full table scan
-- WITH idx_notif_outbox_provider_msg: Direct lookup
```

**Migration Approach:**
1. **NO SQLModel changes needed** - Indexes are managed via Alembic only
2. Use `op.create_index()` with `sa.text()` for DESC/ASC ordering
3. Order columns: filter columns → range columns → sort columns
4. Test index existence via pg_indexes query

**Index Creation Pattern:**

```python
def upgrade():
    import sqlalchemy as sa
    
    # Conversation message session threading
    op.create_index(
        'idx_conv_msg_session_time',
        'conversation_message',
        ['session_id', sa.text('created_at ASC')]
    )
    
    # Notification outbox scheduling (most critical for background workers)
    op.create_index(
        'idx_notif_outbox_status_sched',
        'notification_outbox',
        ['status', 'scheduled_at', 'next_attempt_at']
    )
    
    # Notification outbox channel filtering
    op.create_index(
        'idx_notif_outbox_channel_status',
        'notification_outbox',
        ['channel', 'status']
    )
    
    # Provider message ID lookup (Twilio/SendGrid callbacks)
    op.create_index(
        'idx_notif_outbox_provider_msg',
        'notification_outbox',
        ['provider_message_id']
    )
    
    # Time-series ordering
    op.create_index(
        'idx_notif_outbox_created_at',
        'notification_outbox',
        [sa.text('created_at DESC')]
    )

def downgrade():
    op.drop_index('idx_notif_outbox_created_at', table_name='notification_outbox')
    op.drop_index('idx_notif_outbox_provider_msg', table_name='notification_outbox')
    op.drop_index('idx_notif_outbox_channel_status', table_name='notification_outbox')
    op.drop_index('idx_notif_outbox_status_sched', table_name='notification_outbox')
    op.drop_index('idx_conv_msg_session_time', table_name='conversation_message')
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
    'idx_conv_msg_session_time',
    'idx_notif_outbox_status_sched',
    'idx_notif_outbox_channel_status',
    'idx_notif_outbox_provider_msg',
    'idx_notif_outbox_created_at'
)
ORDER BY tablename, indexname;
```

---

### 2. Implementation Order

**For Task 7 (Communication Indexes - HIGH):**

1. **✅ Establish Regression Baseline** (626/626 unit, 653/653 total tests)
2. **Review Query Patterns**
   - Read task description for common queries
   - Determine optimal column order (filters → range → sort)
3. **Create Alembic Migration** (No SQLModel changes needed)
   ```bash
   cd backend
   source .venv/bin/activate
   alembic revision -m "phase_4_8_add_communication_indexes_task7"
   ```
4. **Write Migration Logic**
   - Use `op.create_index()` for all 5 indexes
   - Use `sa.text('column DESC')` or `sa.text('column ASC')` for ordering
   - Ensure proper downgrade() to drop all indexes
5. **⚠️ CRITICAL: Review Migration File**
   - Search for 'audit' and 'event'
   - **DELETE any `op.create_table('event', ... schema='audit')` blocks**
   - **DELETE any `op.drop_table('event', ... schema='audit')` blocks**
   - Verify your 5 index creations are present
6. **Apply Migration**
   ```bash
   alembic upgrade head
   ```
7. **Create Test Suite** (Recommended)
   - Create `backend/tests/test_phase_4_8_communication_indexes.py`
   - Verify indexes exist via pg_indexes query
   - Keep tests simple (index existence checks)
8. **Run Tests**
   ```bash
   pytest tests/test_phase_4_8_communication_indexes.py -v
   ```
9. **Run Regression Tests** (see "After You Complete" section)
10. **Update Documentation**

---

### 3. Test Requirements

**⚠️ ZERO REGRESSION POLICY:**
- **ALL 626 existing unit tests MUST still pass**
- **ALL 653 total tests (including integration) MUST still pass**
- **New tests (if added) MUST pass**
- **Target: 100% pass rate on both test suites**

#### For Task 7 (Communication Indexes)

**Test File:** `backend/tests/test_phase_4_8_communication_indexes.py`

**Required Coverage (Minimum 2 Tests):**

```python
"""
Test Suite: Phase 4.8 Task 7 - Add Communication Domain Composite Indexes
Tests index creation for conversation threading and notification scheduling

Reference: phase-4.8-db-schema-sync-4-plan.md
"""
import pytest
from sqlmodel import Session
from sqlalchemy import text

class TestCommunicationIndexes:
    """Verify communication domain composite indexes were created"""
    
    def test_communication_indexes_exist(self, db_session: Session):
        """Verify all 5 communication indexes were created"""
        result = db_session.execute(text("""
            SELECT indexname FROM pg_indexes
            WHERE indexname IN (
                'idx_conv_msg_session_time',
                'idx_notif_outbox_status_sched',
                'idx_notif_outbox_channel_status',
                'idx_notif_outbox_provider_msg',
                'idx_notif_outbox_created_at'
            )
            ORDER BY indexname
        """))
        indexes = [row[0] for row in result]
        expected_count = 5
        assert len(indexes) == expected_count, \
            f"Expected {expected_count} indexes, found {len(indexes)}: {indexes}"
    
    def test_notification_outbox_indexes_definition(self, db_session: Session):
        """Verify notification_outbox indexes have correct definitions"""
        result = db_session.execute(text("""
            SELECT indexname, indexdef FROM pg_indexes
            WHERE tablename = 'notification_outbox'
            AND indexname IN (
                'idx_notif_outbox_status_sched',
                'idx_notif_outbox_channel_status',
                'idx_notif_outbox_provider_msg',
                'idx_notif_outbox_created_at'
            )
        """))
        indexes = {row[0]: row[1] for row in result}
        
        # Verify critical background worker index
        assert 'idx_notif_outbox_status_sched' in indexes
        assert 'status' in indexes['idx_notif_outbox_status_sched']
        assert 'scheduled_at' in indexes['idx_notif_outbox_status_sched']
        
        # Verify provider callback index
        assert 'idx_notif_outbox_provider_msg' in indexes
        assert 'provider_message_id' in indexes['idx_notif_outbox_provider_msg']
```

**Test Patterns to Follow:**
- Review `backend/tests/test_phase_4_8_audit_indexes.py` - Task 2 index test patterns
- Review `backend/tests/test_phase_4_8_integration_indexes.py` - Task 6 index test patterns
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
- **For Task 7 (Communication Indexes):** `[626 + 0-2] passed` (unit), `[653 + 0-2] passed` (total) - minimal or no new tests

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

Find Phase 2, Task 7 and update with:

```markdown
### Task 7: Add Communication Domain Composite Indexes

**Status:** ✅ COMPLETE (2026-04-08)
**Effort:** 0.5 days (actual)
**Priority:** HIGH
**Change Type:** MIGRATION

**Implementation Summary:**

- Migration: `YYYY_MM_DD_HHMM-[hash]_phase_4_8_add_communication_indexes_task7.py`
- Test Suite: `test_phase_4_8_communication_indexes.py` - [X] tests ✅
- Final Results: [626 + X]/[626 + X] unit tests passing (100%), [653 + X]/[653 + X] total tests passing (100%)

**Key Changes:**
- ✅ Added idx_conv_msg_session_time for conversation threading
- ✅ Added idx_notif_outbox_status_sched for background worker queries
- ✅ Added idx_notif_outbox_channel_status for channel filtering
- ✅ Added idx_notif_outbox_provider_msg for delivery callbacks
- ✅ Added idx_notif_outbox_created_at for time-series ordering

**Verification:**
- All 5 indexes verified via pg_indexes query
- Background worker notification queries optimized
- Conversation threading queries optimized
- Migration rollback tested successfully
```

---

## Success Criteria

**MUST COMPLETE ALL BEFORE MARKING TASK AS DONE:**

### For Task 7 (Communication Indexes - HIGH):
- [ ] **Regression baseline captured** (626/626 unit, 653/653 total tests)
- [ ] **Query patterns reviewed** to determine optimal column order
- [ ] **Alembic migration created** (no SQLModel changes)
- [ ] **Used `sa.text()` wrapper** for DESC/ASC ordering in indexes
- [ ] **⚠️ CRITICAL: Checked migration for `audit.event` table** and removed if present
- [ ] **Migration applied successfully** (`alembic upgrade head`)
- [ ] **Index verification tests passing** (2 tests confirming existence)
- [ ] **ALL 626 existing unit tests still passing** (no regression)
- [ ] **ALL 653 total tests still passing** (no regression)
- [ ] **Database verification query confirms** all 5 indexes created
- [ ] **Indexes include correct columns** in optimal order (filter → range → sort)
- [ ] **Migration rollback tested** (`alembic downgrade -1` then `upgrade head`)
- [ ] **Project plan document updated**

### For ALL Tasks:
- [ ] **100% test pass rate** - No failing tests
- [ ] **Zero regression** - Baseline maintained or exceeded

---

## Key Files to Review

### Architecture & Design
- `dev-docs/analysis/phase-4.8-db-schema-sync-4-plan.md` - **Task 7 Details** ⭐
- `dev-docs/analysis/phase-4.8-db-schema-sync-4-analysis.md` - Forensic Analysis
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - **Golden Master JSON**

### Backend Code
- `backend/app/models/voice.py` - ConversationMessage model
- `backend/app/models/notifications.py` - NotificationOutbox model

### Tests (Reference for Patterns)
- `backend/tests/test_phase_4_8_audit_indexes.py` - Task 2 index test patterns
- `backend/tests/test_phase_4_8_integration_indexes.py` - Task 6 index test patterns
- `backend/tests/conftest.py` - Test fixtures (`db_session`, `test_tenant`, etc.)

---

## Risk Assessment

**For Task 7 (Communication Indexes):**
- **Performance Risk:** NONE (indexes only improve performance)
- **Regression Risk:** VERY LOW (indexes don't affect application logic)
- **Migration Time:** LOW (conversation_message and notification_outbox are typically small tables)
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
- **Zero Regression Policy:** All 626 unit + 653 total tests MUST pass after changes

### Phase 4.8 Task 7 Specific
- **5 indexes total** - 1 on conversation_message, 4 on notification_outbox
- **Critical for background workers** - `idx_notif_outbox_status_sched` optimizes notification processing
- **Provider callback optimization** - `idx_notif_outbox_provider_msg` enables fast Twilio/SendGrid lookups
- **Conversation threading** - `idx_conv_msg_session_time` ensures chronological message ordering
- **Test coverage minimal** - Index existence tests sufficient (indexes don't change behavior)

### If You Get Stuck
- Use `postgres-local` MCP server to query database state in real-time
- Review Tasks 2-6 completed migrations for index creation patterns
- Search existing tests for `db_session` and `exec()` patterns
- Review the "Best Practices" section at the top of this template
- Check pg_indexes for existing index patterns: `SELECT * FROM pg_indexes WHERE tablename = 'notification_outbox';`
- Remember: Column order in composite indexes matters (filter → range → sort)

---

## Example Task Flow

### For Task 7 (Communication Indexes):

```bash
# 1. Baseline - Capture starting point
cd backend
source .venv/bin/activate

# Run unit tests (no integration)
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Record: 626 passed

# Run all tests (including integration)
pytest tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Record: 653 passed

# 2. Review query patterns in task description
# - Conversation threading: session_id → created_at ASC
# - Notification scheduling: status → scheduled_at → next_attempt_at
# - Channel filtering: channel → status
# - Provider lookup: provider_message_id (single column)
# - Time-series: created_at DESC (single column)

# 3. Create migration (no SQLModel changes)
alembic revision -m "phase_4_8_add_communication_indexes_task7"

# 4. Edit migration file
# Add 5 index creations:
# - idx_conv_msg_session_time
# - idx_notif_outbox_status_sched
# - idx_notif_outbox_channel_status
# - idx_notif_outbox_provider_msg
# - idx_notif_outbox_created_at

# Example:
def upgrade():
    import sqlalchemy as sa
    
    # Conversation message session threading
    op.create_index(
        'idx_conv_msg_session_time',
        'conversation_message',
        ['session_id', sa.text('created_at ASC')]
    )
    
    # Notification outbox scheduling
    op.create_index(
        'idx_notif_outbox_status_sched',
        'notification_outbox',
        ['status', 'scheduled_at', 'next_attempt_at']
    )
    
    # Channel filtering
    op.create_index(
        'idx_notif_outbox_channel_status',
        'notification_outbox',
        ['channel', 'status']
    )
    
    # Provider message ID lookup
    op.create_index(
        'idx_notif_outbox_provider_msg',
        'notification_outbox',
        ['provider_message_id']
    )
    
    # Time-series ordering
    op.create_index(
        'idx_notif_outbox_created_at',
        'notification_outbox',
        [sa.text('created_at DESC')]
    )

def downgrade():
    op.drop_index('idx_notif_outbox_created_at', table_name='notification_outbox')
    op.drop_index('idx_notif_outbox_provider_msg', table_name='notification_outbox')
    op.drop_index('idx_notif_outbox_channel_status', table_name='notification_outbox')
    op.drop_index('idx_notif_outbox_status_sched', table_name='notification_outbox')
    op.drop_index('idx_conv_msg_session_time', table_name='conversation_message')

# 5. ⚠️ CRITICAL: Review migration file
# Search for 'audit' and 'event'
# DELETE any op.create_table('event', ... schema='audit') blocks
# DELETE any op.drop_table('event', ... schema='audit') blocks

# 6. Apply migration
alembic upgrade head

# 7. Verify indexes created using MCP server
SELECT indexname, indexdef
FROM pg_indexes
WHERE indexname IN (
    'idx_conv_msg_session_time',
    'idx_notif_outbox_status_sched',
    'idx_notif_outbox_channel_status',
    'idx_notif_outbox_provider_msg',
    'idx_notif_outbox_created_at'
);

# 8. Create test suite (recommended)
# Create backend/tests/test_phase_4_8_communication_indexes.py
# - Simple test verifying all 5 indexes exist
# - Optional test verifying index definitions

# 9. Run tests
pytest tests/test_phase_4_8_communication_indexes.py -v

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
# Mark Task 7 as complete
```

---

## Questions to Ask

**Before starting:**
1. Have I captured the 626/626 unit and 653/653 total baselines?
2. Do I understand the query patterns and optimal column order for each index?
3. Do I have the correct index type (standard composite vs single-column)?
4. Have I reviewed previous task migration files for index creation patterns?

**During implementation:**
1. Am I using `db_session` parameter (NOT `session`) in tests?
2. Am I using `select()/exec()` pattern (NOT `query()`) in tests?
3. After running `alembic revision`, did I check for and remove `audit.event` table creation?
4. For indexes: Am I using `sa.text('column DESC')` or `sa.text('column ASC')` for ordering?
5. Are my index columns in the right order (filter → range → sort)?
6. Did I create proper downgrade() methods to drop all 5 indexes?

**After implementation:**
1. Do I have 100% test pass rate on BOTH unit tests and total tests?
2. Do all 5 expected indexes exist in pg_indexes?
3. Have I updated the project plan document?
4. Have I tested migration rollback (`alembic downgrade -1`)?

---

**Ready to Begin!** 🚀

### Task 7 Checklist (Communication Indexes - HIGH):
1. ✅ Capture baseline (626/626 unit, 653/653 total)
2. 📖 Review query patterns and determine column order
3. 📝 Create migration (indexes only, no SQLModel)
4. 🛠️ Use `sa.text()` for DESC/ASC ordering
5. ⚠️ **CRITICAL: Remove `audit.event` table from migration if present**
6. ✅ Apply migration (`alembic upgrade head`)
7. 🔍 Verify indexes exist via pg_indexes query
8. 🧪 Create simple existence tests (2 tests recommended)
9. 🔄 Run regression tests (minimal change expected)
10. ↩️ Test rollback (`alembic downgrade -1`, then `upgrade head`)
11. 📚 Update project plan

Remember: This task adds **5 critical performance indexes** for communication features - conversation threading and notification scheduling. The `idx_notif_outbox_status_sched` index is especially important for background worker efficiency. Be thorough, verify indexes exist, and always check for the `audit.event` table issue in migrations!
