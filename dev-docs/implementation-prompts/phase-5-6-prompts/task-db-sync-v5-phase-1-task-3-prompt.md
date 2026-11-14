# Task 3: Normalize notification_outbox Status Spelling

**Reference:** `dev-docs/analysis/phase-4.9-db-schema-sync-5-plan.md` - Task 3
**Authority (Golden Master):**
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - Golden Master JSON
- Current Live Database (Phase 4.8 Post-State)
**Type:** Phase 4.9 - CHECK Constraint Value Alignment
**Priority:** MEDIUM
**Change Type:** MIGRATION + MODEL UPDATE

---

## Context

This is **Phase 4.9 - DB Sync v#5**, a fifth forensic reconciliation after completing Phases 4.5, 4.6, 4.7, and 4.8. A comprehensive comparison between the current database state and the Golden Master JSON revealed **CHECK constraint value mismatches** in three tables.

**Critical Finding:** The database currently allows legacy status strings that the JSON schema (and Python backend models) do not support. We must normalize the data to match the JSON definitions, then replace the database constraints to lock these values permanently.

**Key Focus Areas:**
1. ✅ **connector_run_log** (HIGH) - Status values: 'completed' → 'success', 'cancelled' → 'failed' - COMPLETE
2. ✅ **webhook_delivery_attempt** (HIGH) - Status values: 'delivered' → 'success', 'retrying' → 'pending' - COMPLETE
3. **notification_outbox** (MEDIUM) - Spelling: 'cancelled' → 'canceled' (British → American) - THIS TASK

**Key Principle:** The notification_outbox table currently has 1 row with valid status 'sent'. This is primarily a constraint replacement exercise with a spelling normalization safety UPDATE.

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

**Phase 4.8 Status:** ✅ COMPLETE (April 8, 2026)
- ✅ 631/631 unit tests passing (100%)
- ✅ 658/658 total tests passing (100%)
- ✅ Legacy user check constraints replaced
- ✅ 18+ composite performance indexes added

**Phase 4.9 Task 1 Status:** ✅ COMPLETE (April 8, 2026)
- ✅ 633/633 unit tests passing (100%)
- ✅ 660/660 total tests passing (100%)
- ✅ connector_run_log status values normalized

**Phase 4.9 Task 2 Status:** ✅ COMPLETE (April 8, 2026)
- ✅ 636/636 unit tests passing (100%), 1 skipped
- ✅ webhook_delivery_attempt status values normalized

**Current Baseline:** 636/636 unit tests passing (100%), 1 skipped

**See:**
- `dev-docs/analysis/phase-4.5-db-schema-sync-to-design-plan.md` for Phase 4.5 history
- `dev-docs/analysis/phase-4.6-db-schema-sync-2-plan.md` for Phase 4.6 history
- `dev-docs/analysis/phase-4.7-db-schema-sync-3-plan.md` for Phase 4.7 history
- `dev-docs/analysis/phase-4.8-db-schema-sync-4-plan.md` for Phase 4.8 history
- `dev-docs/analysis/phase-4.9-db-schema-sync-5-plan.md` for Phase 4.9 Task 1 & 2 history

---

## Current Task: Normalize notification_outbox Status Spelling

**Effort:** 0.5 days
**Gap Reference:** Phase 4.9 Analysis - notification_outbox Spelling Inconsistency
**Change Type:** MIGRATION + MODEL UPDATE

This task normalizes the `notification_outbox` table's status field to enforce American spelling ('canceled' with one 'L') instead of British spelling ('cancelled' with two 'L's). This ensures consistency across the codebase, API responses, and database constraints with the Golden Master JSON schema definition.

### What Needs to Be Fixed

| # | Component | Issue | Impact | Complexity |
|---|-----------|-------|--------|------------|
| **1** | `notification_outbox` | CHECK constraint allows British spelling 'cancelled' not in JSON schema | Code consistency, API standardization | LOW |

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

**Record the output of both results:** `636/636 unit tests passing, 1 skipped` (Phase 4.9 baseline - starting from Task 2 completion)

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
    op.execute(...)  # Your actual data updates
    op.drop_constraint(...)  # Your constraint changes
    op.create_check_constraint(...)  # Your new constraints
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

### 4. Use Literal Types for Status Value Validation in Models

❌ **WRONG (No Runtime Validation):**
```python
from sqlmodel import Field

class MyModel(SQLModel, table=True):
    status: str = Field(default="pending")  # No validation!
```

✅ **CORRECT (Type-Safe Validation):**
```python
from typing import Literal
from sqlmodel import Field

class MyModel(SQLModel, table=True):
    status: Literal["pending", "success", "failed"] = Field(
        default="pending",
        sa_column_kwargs={
            "nullable": False,
            "server_default": text("'pending'")
        }
    )
```

**Why:** Literal types provide compile-time and runtime validation that status values match the allowed set. This prevents runtime errors from invalid status strings.

**Action:** Always use Literal types for enum-like text fields with CHECK constraints.

---

### 5. Order of Operations in Migrations: UPDATE Data BEFORE Replacing Constraints

❌ **WRONG (Constraint Violation):**
```python
def upgrade():
    # Drop old constraint first
    op.drop_constraint('table_status_chk', 'table', type_='check')
    
    # Add new constraint
    op.create_check_constraint('table_status_chk', 'table', "status IN ('new', 'values')")
    
    # Update data LAST - too late, constraint already enforced!
    op.execute("UPDATE table SET status = 'new' WHERE status = 'old'")
```

✅ **CORRECT (Data First, Then Constraints):**
```python
def upgrade():
    # Step 1: Update data FIRST (while old constraint still allows it)
    op.execute("""
        UPDATE table
        SET status = CASE
            WHEN status = 'old_value' THEN 'new_value'
            ELSE status
        END
        WHERE status IN ('old_value')
    """)
    
    # Step 2: Drop old constraint
    op.drop_constraint('table_status_chk', 'table', type_='check')
    
    # Step 3: Add new constraint (data already normalized)
    op.create_check_constraint('table_status_chk', 'table', "status IN ('new', 'values')")
```

**Why:** PostgreSQL enforces CHECK constraints immediately. If you drop the old constraint and add a new one before updating the data, existing rows with old values will violate the new constraint.

**Critical Order:** **Data Updates → Drop Old Constraint → Add New Constraint**

---

## Requirements

### 1. Implementation Details

**Task 3: Normalize notification_outbox Status Spelling (MEDIUM)**

**Problem:** The `notification_outbox` table CHECK constraint allows British spelling 'cancelled' but the JSON schema uses American spelling 'canceled'.

**Current State (Database - WRONG):**
```sql
-- Allows: 'pending', 'sent', 'failed', 'cancelled' (British spelling)
CHECK (status IN ('pending', 'sent', 'failed', 'cancelled'))
```

**Target State (JSON Schema - CORRECT):**
```json
{
  "check_constraints": [
    {
      "name": "notification_outbox_status_chk",
      "definition": "status IN ('pending','sent','failed','canceled')"
    }
  ]
}
```

**Data State:** 1 row with status='sent' (valid - no migration needed)

**Value Mapping:**
- `'cancelled'` → `'canceled'` (British → American spelling)

**Implementation Steps:**
1. **Update Python Model** - Use `Literal["pending", "sent", "failed", "canceled"]`
2. **Create Migration** - Data update (handles British→American), drop old constraint, add new constraint
3. **Create Tests** - Verify valid statuses accepted, British spelling rejected

---

### 2. Implementation Order

**For Task 3 (Status Spelling Normalization):**

1. **✅ Establish Regression Baseline** (636/636 unit tests, 1 skipped)

2. **Update Python Model First** (IMPORTANT: Do this BEFORE migration)
   ```python
   # backend/app/models/system.py
   
   from typing import Literal
   from sqlmodel import Field, text
   
   class NotificationOutbox(SQLModel, table=True):
       # ... other fields ...
       
       status: Literal["pending", "sent", "failed", "canceled"] = Field(
           default="pending",
           sa_column_kwargs={
               "nullable": False,
               "server_default": text("'pending'")
           }
       )
   ```

3. **Create Alembic Migration**
   ```bash
   cd backend
   source .venv/bin/activate
   alembic revision --autogenerate -m "phase_4_9_normalize_notification_status_spelling_task3"
   ```

4. **Edit Migration File** (CRITICAL ORDER: Data → Drop → Add)
   ```python
   def upgrade():
       # Step 1: Data normalization (fix British spelling to American)
       op.execute("""
           UPDATE notification_outbox
           SET status = 'canceled'
           WHERE status = 'cancelled'
       """)
       
       # Step 2: Drop old constraint
       op.drop_constraint('notification_outbox_status_chk', 'notification_outbox', type_='check')
       
       # Step 3: Add new constraint with American spelling
       op.create_check_constraint(
           'notification_outbox_status_chk',
           'notification_outbox',
           "status IN ('pending', 'sent', 'failed', 'canceled')"
       )
   
   def downgrade():
       # Reverse order: Drop new → Add old → Reverse data
       op.drop_constraint('notification_outbox_status_chk', 'notification_outbox', type_='check')
       
       op.create_check_constraint(
           'notification_outbox_status_chk',
           'notification_outbox',
           "status IN ('pending', 'sent', 'failed', 'cancelled')"
       )
       
       # Reverse spelling change
       op.execute("""
           UPDATE notification_outbox
           SET status = 'cancelled'
           WHERE status = 'canceled'
       """)
   ```

5. **⚠️ CRITICAL: Review Migration for audit.event**
   - Search for `'event'` and `schema='audit'`
   - DELETE any `op.create_table('event', ... schema='audit')` blocks
   - Verify your constraint changes are present

6. **Apply Migration**
   ```bash
   alembic upgrade head
   ```

7. **Verify Constraint Updated** (Using MCP Server)
   ```sql
   SELECT 
       conname AS constraint_name,
       pg_get_constraintdef(c.oid) AS constraint_definition
   FROM pg_constraint c
   JOIN pg_class t ON c.conrelid = t.oid
   WHERE t.relname = 'notification_outbox'
     AND contype = 'c'
     AND conname = 'notification_outbox_status_chk';
   ```

8. **Create Test Suite**
   - Create `backend/tests/test_phase_4_9_notification_outbox_status.py`
   - Test all valid status values accepted
   - Test British spelling rejected
   - Test default status value
   - Test American spelling consistency

9. **Run New Tests**
   ```bash
   pytest tests/test_phase_4_9_notification_outbox_status.py -v
   ```

10. **Run Regression Tests** (see "After You Complete" section)

11. **Update Documentation**

---

### 3. Test Requirements

**⚠️ ZERO REGRESSION POLICY:**
- **ALL 636 existing unit tests MUST still pass**
- **New tests (4 for this task) MUST pass**
- **Target: 100% pass rate on test suite**

#### Test File Template

**Test File:** `backend/tests/test_phase_4_9_notification_outbox_status.py`

**Required Coverage (4 Tests):**
```python
"""
Test Suite: Phase 4.9 Task 3 - Normalize notification_outbox Status Spelling
Tests CHECK constraint value alignment with JSON schema (American spelling)

Reference: phase-4.9-db-schema-sync-5-plan.md - Task 3
"""
import pytest
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from app.models.system import NotificationOutbox

class TestNotificationOutboxStatusConstraint:
    """Test updated notification_outbox CHECK constraint"""
    
    def test_notification_outbox_valid_statuses(self, db_session: Session, test_tenant):
        """Verify all JSON-defined status values (American spelling) are accepted"""
        # Test all valid statuses
        for status in ['pending', 'sent', 'failed', 'canceled']:
            outbox = NotificationOutbox(
                tenant_id=test_tenant.id,
                channel='email',
                to_address='test@example.com',
                subject='Test',
                body='Test message',
                status=status
            )
            db_session.add(outbox)
            db_session.commit()
            db_session.delete(outbox)
            db_session.commit()
    
    def test_notification_outbox_rejects_british_spelling(self, db_session: Session, test_tenant):
        """Verify British spelling 'cancelled' is rejected"""
        # Test British spelling is rejected
        outbox = NotificationOutbox(
            tenant_id=test_tenant.id,
            channel='email',
            to_address='test@example.com',
            subject='Test',
            body='Test message',
            status='cancelled'  # British spelling
        )
        with pytest.raises(IntegrityError) as exc_info:
            db_session.add(outbox)
            db_session.commit()
        assert 'notification_outbox_status_chk' in str(exc_info.value).lower()
        db_session.rollback()
    
    def test_notification_outbox_default_status(self, db_session: Session, test_tenant):
        """Verify default status is 'pending'"""
        outbox = NotificationOutbox(
            tenant_id=test_tenant.id,
            channel='email',
            to_address='test@example.com',
            subject='Test',
            body='Test message'
            # Don't set status - let default apply
        )
        db_session.add(outbox)
        db_session.commit()
        
        assert outbox.status == 'pending'
    
    def test_notification_outbox_american_spelling_consistency(self, db_session: Session):
        """Verify American spelling is used consistently in code"""
        # Verify Literal type uses American spelling
        status_field = NotificationOutbox.__fields__['status']
        assert 'canceled' in str(status_field.type_)
        assert 'cancelled' not in str(status_field.type_)
```

**Test Patterns to Follow:**
- Review `backend/tests/test_phase_4_9_connector_run_log_status.py` - Task 1 pattern
- Review `backend/tests/test_phase_4_9_webhook_delivery_status.py` - Task 2 pattern
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
- **Unit Tests:** `640/640 passed` (636 + 4 new), 1 skipped
- **Total Tests:** `[total] passed` (including integration)

### Step 3: Verify 100% Pass Rate

**If ANY tests fail:**
1. Identify failing tests
2. Determine if new or existing tests
3. Fix ALL failures before proceeding
4. Re-run until 100% pass rate

**Common Failure Scenarios:**
- **Existing tests fail** → Model changes or constraint logic broke something (rollback and fix)
- **New tests fail** → Constraint not updated correctly or test logic issue
- **IntegrityError in tests** → Constraint too strict or test setup incomplete

---

## Documentation Update

### Update Project Plan Document

**File to Update:** `dev-docs/analysis/phase-4.9-db-schema-sync-5-plan.md`

Find Task 3 and update with:

```markdown
### Task 3: Normalize notification_outbox Status Spelling

**Status:** ✅ COMPLETE (YYYY-MM-DD)
**Effort:** 0.5 days (actual)
**Priority:** MEDIUM
**Change Type:** MIGRATION + MODEL UPDATE

**Implementation Summary:**

- Model Update: `backend/app/models/system.py` - Added Literal type validation
- Migration: `YYYY_MM_DD_HHMM-[hash]_phase_4_9_normalize_notification_status_spelling_task3.py`
- Test Suite: `test_phase_4_9_notification_outbox_status.py` - 4 tests ✅
- Final Results: 640/640 unit tests passing (100%), 1 skipped

**Key Changes:**
- ✅ Status values normalized to JSON schema definitions (American spelling)
- ✅ Python model uses Literal type for validation
- ✅ CHECK constraint updated to enforce American spelling 'canceled'
- ✅ British spelling 'cancelled' rejected by database
- ✅ Migration rollback tested successfully

**Verification:**
- Database constraint verified via pg_constraint query
- All valid status values tested and accepted
- British spelling rejected with IntegrityError
- Migration rollback tested successfully
```

---

## Success Criteria

**MUST COMPLETE ALL BEFORE MARKING TASK AS DONE:**

### Task 3 Specific:
- [ ] **Regression baseline captured** (636/636 unit tests, 1 skipped)
- [ ] **Python model updated FIRST** with Literal type validation
- [ ] **Alembic migration created** with proper order (Data → Drop → Add)
- [ ] **⚠️ CRITICAL: Checked migration for `audit.event` table** and removed if present
- [ ] **Migration applied successfully** (`alembic upgrade head`)
- [ ] **All 4 new tests written and passing**
- [ ] **Tests use `db_session` parameter** and `select()/exec()` pattern
- [ ] **ALL 636 existing unit tests still passing**
- [ ] **New total: 640/640 unit tests (100%), 1 skipped**
- [ ] **Database verification query confirms** constraint updated
- [ ] **Valid status values accepted** ('pending', 'sent', 'failed', 'canceled')
- [ ] **British spelling rejected** ('cancelled' raises IntegrityError)
- [ ] **Migration rollback tested** (`alembic downgrade -1` then `upgrade head`)
- [ ] **Project plan document updated**

### Task-Specific Validation:
- [ ] Model accepts: 'pending', 'sent', 'failed', 'canceled' (American spelling)
- [ ] Model rejects: 'cancelled' (British spelling)
- [ ] Default status is 'pending'
- [ ] No rows in database have status = 'cancelled'
- [ ] Literal type uses American spelling exclusively

---

## Key Files to Review

### Architecture & Design
- `dev-docs/analysis/phase-4.9-db-schema-sync-5-plan.md` - **Task 3 Details** ⭐
- `dev-docs/analysis/phase-4.9-db-schema-sync-5-analysis.md` - Forensic Analysis
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - **Golden Master JSON**

### Backend Code
- `backend/app/models/system.py` - NotificationOutbox model

### Tests (Reference for Patterns)
- `backend/tests/test_phase_4_9_connector_run_log_status.py` - Task 1 pattern
- `backend/tests/test_phase_4_9_webhook_delivery_status.py` - Task 2 pattern
- `backend/tests/conftest.py` - Test fixtures

---

## Risk Assessment

**For Task 3:**
- **Data Loss Risk:** NONE (1 row with valid status 'sent')
- **Logic Risk:** LOW (simple spelling normalization)
- **Regression Risk:** LOW (constraint changes don't affect existing valid data)
- **Rollback Complexity:** LOW (simple constraint swap)
- **Deployment Impact:** MEDIUM (prevents use of British spelling)
- **Mitigation:** Update models first, verify no 'cancelled' data exists, test thoroughly

---

## Notes

### Important Patterns to Follow
- **Virtual Environment Required:** All Python/pytest commands use `source .venv/bin/activate`
- **Use `db_session` Parameter:** NOT `session` (pytest fixture naming)
- **Use `select()/exec()` Pattern:** NOT `query()` (SQLModel standard)
- **Check Alembic Migrations:** ALWAYS remove `audit.event` table if autogenerated
- **Use Literal Types:** Required for type-safe status value validation
- **Migration Order:** Data updates BEFORE constraint changes (critical!)
- **Update Models First:** Python models should be updated BEFORE creating migration
- **Zero Regression Policy:** All 636 unit tests MUST pass

### Phase 4.9 Task 3 Specific
- **Spelling normalization** - British 'cancelled' → American 'canceled'
- **Model-first approach** - Update Python models before migrations
- **Safety UPDATE included** - Handles any legacy British spelling in data
- **API consistency** - Ensures consistent spelling in all API responses
- **Type safety** - Literal types prevent runtime errors from incorrect spelling

### If You Get Stuck
- Use `postgres-local` MCP server to query database state in real-time
- Review Phase 4.9 Task 1 & 2 completed tests for patterns
- Search existing tests for `db_session` and `exec()` patterns
- Check the "Best Practices" section at the top of this template
- Verify migration order: Data → Drop old constraint → Add new constraint
- Ensure Python model Literal types match JSON schema exactly

---

## Example Task Flow

### For Task 3 (Status Spelling Normalization):

```bash
# 1. Baseline - Capture starting point
cd backend
source .venv/bin/activate

# Run unit tests (no integration)
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Record: 636 passed, 1 skipped

# 2. Update Python Model FIRST (before migration)
# Edit backend/app/models/system.py
# Change NotificationOutbox status field from str to Literal["pending", "sent", "failed", "canceled"]

# 3. Verify table data state (using MCP server)
SELECT COUNT(*) FROM notification_outbox;
# Should return 1

# Check for any British spelling
SELECT status, COUNT(*) 
FROM notification_outbox 
GROUP BY status;
# Should show no 'cancelled' (likely just 'sent')

# 4. Create migration
alembic revision --autogenerate -m "phase_4_9_normalize_notification_status_spelling_task3"

# 5. Edit migration file
# CRITICAL ORDER in upgrade():
# 1. Data UPDATE (normalize British → American spelling)
# 2. DROP old constraint
# 3. ADD new constraint

# 6. ⚠️ CRITICAL: Review migration file
# Search for 'audit' and 'event'
# DELETE any op.create_table('event', ... schema='audit') blocks
# Verify your constraint changes are present

# 7. Apply migration
alembic upgrade head

# 8. Verify constraint updated (using MCP server)
SELECT 
    conname AS constraint_name,
    pg_get_constraintdef(c.oid) AS constraint_definition
FROM pg_constraint c
JOIN pg_class t ON c.conrelid = t.oid
WHERE t.relname = 'notification_outbox'
  AND contype = 'c'
  AND conname = 'notification_outbox_status_chk';

# 9. Create test suite
# Create backend/tests/test_phase_4_9_notification_outbox_status.py
# - Use db_session: Session parameter
# - Use select() with exec()
# - Test valid statuses accepted (American spelling)
# - Test British spelling rejected
# - Test default status value
# - Test Literal type consistency

# 10. Run new tests
pytest tests/test_phase_4_9_notification_outbox_status.py -v
# All 4 new tests should pass

# 11. Regression check
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Expected: 640 passed, 1 skipped (636 + 4 new)

# 12. Rollback test
alembic downgrade -1
alembic upgrade head
pytest tests/ -v  # Should still pass

# 13. Update docs
# Edit dev-docs/analysis/phase-4.9-db-schema-sync-5-plan.md
# Mark Task 3 as complete with test results
```

---

## Questions to Ask

**Before starting:**
1. Have I captured the 636/636 unit baseline (1 skipped)?
2. Have I updated the Python model with Literal type FIRST?
3. Do I understand the spelling mapping (British 'cancelled' → American 'canceled')?
4. Have I verified the table has 1 row with valid status 'sent'?

**During implementation:**
1. Am I using `db_session` parameter (NOT `session`) in tests?
2. Am I using `select()/exec()` pattern (NOT `query()`) in tests?
3. After running `alembic revision`, did I check for and remove `audit.event` table?
4. Is my migration in the correct order: Data UPDATE → DROP old → ADD new?
5. Does my Python model Literal type use American spelling 'canceled' (not 'cancelled')?

**After implementation:**
1. Do I have 100% test pass rate on unit tests (640/640)?
2. Can I create objects with all valid status values?
3. Is British spelling 'cancelled' properly rejected with IntegrityError?
4. Does the default status value match 'pending'?
5. Have I updated the project plan document?
6. Have I tested migration rollback (`alembic downgrade -1`)?

---

**Ready to Begin!** 🚀

### Task 3 Checklist:
1. ✅ Capture baseline (636/636 unit tests, 1 skipped)
2. 📝 **Update Python model with Literal type FIRST** (American spelling)
3. 🔍 Verify table has 1 row with valid status 'sent'
4. 📝 Create migration (Data → Drop → Add order)
5. ⚠️ **CRITICAL: Remove `audit.event` table from migration if present**
6. ✅ Apply migration (`alembic upgrade head`)
7. 🔍 Verify constraint via pg_constraint query
8. 🧪 Create 4 tests (valid values, reject British, default value, spelling consistency)
9. 🔄 Run regression tests (640/640 unit, 1 skipped expected)
10. ↩️ Test rollback (`alembic downgrade -1`, then `upgrade head`)
11. 📚 Update project plan

Remember: Task 3 is about **spelling consistency** (British → American). Update Python models first, ensure proper migration order (Data → Drop → Add), and use Literal types for type safety. The table has only 1 row with valid data, making this a low-risk normalization exercise. Be thorough with testing and verify that British spelling is properly rejected!
