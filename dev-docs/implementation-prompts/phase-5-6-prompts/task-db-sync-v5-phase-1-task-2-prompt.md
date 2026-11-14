# Task 2: Normalize webhook_delivery_attempt Status Values

**Reference:** `dev-docs/analysis/phase-4.9-db-schema-sync-5-plan.md` - Task 2
**Authority (Golden Master):**
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - Golden Master JSON
- Current Live Database (Phase 4.8 Post-State)
**Type:** Phase 4.9 - CHECK Constraint Value Alignment
**Priority:** HIGH
**Change Type:** MIGRATION + MODEL UPDATE

---

## Context

This is **Phase 4.9 - DB Sync v#5**, a fifth forensic reconciliation after completing Phases 4.5, 4.6, 4.7, and 4.8. A comprehensive comparison between the current database state and the Golden Master JSON revealed **CHECK constraint value mismatches** in three tables.

**Critical Finding:** The database currently allows legacy status strings that the JSON schema (and Python backend models) do not support. We must normalize the data to match the JSON definitions, then replace the database constraints to lock these values permanently.

**Key Focus Areas:**
1. **connector_run_log** (HIGH) - Status values: 'completed' → 'success', 'cancelled' → 'failed'
2. **webhook_delivery_attempt** (HIGH) - Status values: 'delivered' → 'success', 'retrying' → 'pending'
3. **notification_outbox** (MEDIUM) - Spelling: 'cancelled' → 'canceled' (British → American)

**Key Principle:** All three tables are currently empty or nearly empty (1 row in notification_outbox with valid status 'sent'), making data migration trivial. This is primarily a constraint replacement and model update exercise.

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

**Current Baseline:** 633/633 unit tests, 660/660 total tests passing (100%)

**See:**
- `dev-docs/analysis/phase-4.5-db-schema-sync-to-design-plan.md` for Phase 4.5 history
- `dev-docs/analysis/phase-4.6-db-schema-sync-2-plan.md` for Phase 4.6 history
- `dev-docs/analysis/phase-4.7-db-schema-sync-3-plan.md` for Phase 4.7 history
- `dev-docs/analysis/phase-4.8-db-schema-sync-4-plan.md` for Phase 4.8 history

---

## Current Task: Normalize webhook_delivery_attempt Status Values

**Effort:** 0.5 days
**Gap Reference:** Phase 4.9 Analysis - webhook_delivery_attempt Status Mismatch
**Change Type:** MIGRATION + MODEL UPDATE

The `webhook_delivery_attempt` table CHECK constraint currently allows legacy status values ('delivered', 'retrying') that conflict with the JSON schema definition. This task normalizes the constraint to accept only the correct values ('pending', 'success', 'failed', 'giving_up') as defined in the Golden Master JSON.

### What Needs to Be Fixed

| # | Component | Issue | Impact | Complexity |
|---|-----------|-------|--------|------------|
| **1** | `webhook_delivery_attempt` | CHECK constraint allows legacy status values not in JSON schema | Runtime errors when backend uses JSON-defined values | LOW |

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

**Record the output of both results:** `633/633 & 660/660 tests passing` (Phase 4.9 Task 2 baseline - starting from Task 1 completion)

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

**Phase 4.9 Task 2: Normalize webhook_delivery_attempt Status Values (HIGH)**

**Problem:** The `webhook_delivery_attempt` table CHECK constraint allows legacy status values that conflict with the JSON schema definition.

**Current State (Database - WRONG):**
```sql
-- Allows: 'pending', 'delivered', 'failed', 'retrying'
CHECK (status IN ('pending', 'delivered', 'failed', 'retrying'))
```

**Target State (JSON Schema - CORRECT):**
```json
{
  "check_constraints": [
    {
      "name": "webhook_delivery_attempt_status_chk",
      "definition": "status IN ('pending','success','failed','giving_up')"
    }
  ]
}
```

**Data State:** 0 rows (table is empty - no data migration needed)

**Value Mapping:**
- `'delivered'` → `'success'`
- `'retrying'` → `'pending'`

**Implementation Steps:**
1. **Update Python Model** - Use `Literal["pending", "success", "failed", "giving_up"]`
2. **Create Migration** - Data update (no-op), drop old constraint, add new constraint
3. **Create Tests** - Verify valid statuses accepted, legacy values rejected

---

### 2. Implementation Order

**For Phase 4.9 Task 2 (webhook_delivery_attempt Status Normalization):**

1. **✅ Establish Regression Baseline** (633/633 unit, 660/660 total tests)

2. **Update Python Model First** (IMPORTANT: Do this BEFORE migration)
   ```python
   # backend/app/models/system.py
   
   from typing import Literal
   from sqlmodel import Field, text
   
   class WebhookDeliveryAttempt(SQLModel, table=True):
       # ... other fields ...
       
       status: Literal["pending", "success", "failed", "giving_up"] = Field(
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
   alembic revision --autogenerate -m "phase_4_9_normalize_webhook_delivery_status_task2"
   ```

4. **Edit Migration File** (CRITICAL ORDER: Data → Drop → Add)
   ```python
   def upgrade():
       # Step 1: Data normalization (no-op since table is empty, but included for safety)
       op.execute("""
           UPDATE webhook_delivery_attempt
           SET status = CASE
               WHEN status = 'delivered' THEN 'success'
               WHEN status = 'retrying' THEN 'pending'
               ELSE status
           END
           WHERE status IN ('delivered', 'retrying')
       """)
       
       # Step 2: Drop old constraint
       op.drop_constraint('webhook_delivery_attempt_status_chk', 'webhook_delivery_attempt', type_='check')
       
       # Step 3: Add new constraint with correct values
       op.create_check_constraint(
           'webhook_delivery_attempt_status_chk',
           'webhook_delivery_attempt',
           "status IN ('pending', 'success', 'failed', 'giving_up')"
       )
   
   def downgrade():
       # Reverse order: Drop new → Add old → Reverse data
       op.drop_constraint('webhook_delivery_attempt_status_chk', 'webhook_delivery_attempt', type_='check')
       
       op.create_check_constraint(
           'webhook_delivery_attempt_status_chk',
           'webhook_delivery_attempt',
           "status IN ('pending', 'delivered', 'failed', 'retrying')"
       )
       
       # Reverse data mapping (only if needed)
       op.execute("""
           UPDATE webhook_delivery_attempt
           SET status = CASE
               WHEN status = 'success' THEN 'delivered'
               ELSE status
           END
           WHERE status = 'success'
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
   WHERE t.relname = 'webhook_delivery_attempt'
     AND contype = 'c'
     AND conname = 'webhook_delivery_attempt_status_chk';
   ```

8. **Create Test Suite**
   - Create `backend/tests/test_phase_4_9_webhook_delivery_status.py`
   - Test all valid status values accepted
   - Test legacy status values rejected
   - Test default status value

9. **Run New Tests**
   ```bash
   pytest tests/test_phase_4_9_webhook_delivery_status.py -v
   ```

10. **Run Regression Tests** (see "After You Complete" section)

11. **Update Documentation**

---

### 3. Test Requirements

**⚠️ ZERO REGRESSION POLICY:**
- **ALL 633 existing unit tests MUST still pass**
- **ALL 660 total tests (including integration) MUST still pass**
- **New tests (3 per task) MUST pass**
- **Target: 100% pass rate on both test suites**

#### Test File Template

**Test File:** `backend/tests/test_phase_4_9_webhook_delivery_status.py`

**Required Coverage (Minimum 3 Tests):**
```python
"""
Test Suite: Phase 4.9 Task 2 - Normalize webhook_delivery_attempt Status Values
Tests CHECK constraint value alignment with JSON schema

Reference: phase-4.9-db-schema-sync-5-plan.md - Task 2
"""
import pytest
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from app.models.system import WebhookDeliveryAttempt, WebhookEvent, WebhookEndpoint

class TestWebhookDeliveryAttemptStatusConstraint:
    """Test updated webhook_delivery_attempt CHECK constraint"""
    
    def test_webhook_delivery_valid_statuses(self, db_session: Session, test_tenant):
        """Verify all JSON-defined status values are accepted"""
        # Create necessary parent objects
        endpoint = WebhookEndpoint(
            tenant_id=test_tenant.id,
            url="https://example.com/webhook",
            events=["test.event"]
        )
        db_session.add(endpoint)
        db_session.commit()
        
        event = WebhookEvent(
            tenant_id=test_tenant.id,
            event_type="test.event",
            payload={"test": "data"}
        )
        db_session.add(event)
        db_session.commit()
        
        # Test all valid statuses from JSON schema
        for status in ['pending', 'success', 'failed', 'giving_up']:
            attempt = WebhookDeliveryAttempt(
                webhook_event_id=event.id,
                webhook_endpoint_id=endpoint.id,
                status=status,
                attempt_number=1
            )
            db_session.add(attempt)
            db_session.commit()
            db_session.delete(attempt)
            db_session.commit()
    
    def test_webhook_delivery_rejects_legacy_statuses(self, db_session: Session, test_tenant):
        """Verify legacy status values are rejected"""
        # Create necessary parent objects
        endpoint = WebhookEndpoint(
            tenant_id=test_tenant.id,
            url="https://example.com/webhook",
            events=["test.event"]
        )
        db_session.add(endpoint)
        db_session.commit()
        
        event = WebhookEvent(
            tenant_id=test_tenant.id,
            event_type="test.event",
            payload={"test": "data"}
        )
        db_session.add(event)
        db_session.commit()
        
        # Test legacy statuses are rejected
        for legacy_status in ['delivered', 'retrying']:
            attempt = WebhookDeliveryAttempt(
                webhook_event_id=event.id,
                webhook_endpoint_id=endpoint.id,
                status=legacy_status,
                attempt_number=1
            )
            with pytest.raises(IntegrityError) as exc_info:
                db_session.add(attempt)
                db_session.commit()
            assert 'webhook_delivery_attempt_status_chk' in str(exc_info.value).lower()
            db_session.rollback()
    
    def test_webhook_delivery_default_status(self, db_session: Session, test_tenant):
        """Verify default status value"""
        # Create necessary parent objects
        endpoint = WebhookEndpoint(
            tenant_id=test_tenant.id,
            url="https://example.com/webhook",
            events=["test.event"]
        )
        db_session.add(endpoint)
        db_session.commit()
        
        event = WebhookEvent(
            tenant_id=test_tenant.id,
            event_type="test.event",
            payload={"test": "data"}
        )
        db_session.add(event)
        db_session.commit()
        
        attempt = WebhookDeliveryAttempt(
            webhook_event_id=event.id,
            webhook_endpoint_id=endpoint.id,
            attempt_number=1
            # Don't set status - let default apply
        )
        db_session.add(attempt)
        db_session.commit()
        
        assert attempt.status == 'pending'
```

**Test Patterns to Follow:**
- Review `backend/tests/test_phase_4_9_connector_run_log_status.py` - Task 1 test patterns
- Review `backend/tests/test_phase_4_8_*.py` - Recent phase test patterns
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
- **After Task 2:** `636/636 passed` (unit), `663/663 passed` (total)
- **Calculation:** 633 + 3 new = 636 unit tests, 660 + 3 new = 663 total tests

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

Find Task 2 and update with:

```markdown
### Task 2: Normalize webhook_delivery_attempt Status Values

**Status:** ✅ COMPLETE (2026-04-XX)
**Effort:** 0.5 days (actual)
**Priority:** HIGH
**Change Type:** MIGRATION + MODEL UPDATE

**Implementation Summary:**

- Model Update: `backend/app/models/system.py` - Added Literal type validation
- Migration: `YYYY_MM_DD_HHMM-[hash]_phase_4_9_normalize_webhook_delivery_status_task2.py`
- Test Suite: `test_phase_4_9_webhook_delivery_status.py` - 3 tests ✅
- Final Results: 636/636 unit tests passing (100%), 663/663 total tests passing (100%)

**Key Changes:**
- ✅ Status values normalized to JSON schema definitions
- ✅ Python model uses Literal type for validation
- ✅ CHECK constraint updated to enforce correct values
- ✅ Legacy status values rejected by database

**Verification:**
- Database constraint verified via pg_constraint query
- All valid status values tested and accepted
- Legacy status values rejected with IntegrityError
- Migration rollback tested successfully
```

---

## Success Criteria

**MUST COMPLETE ALL BEFORE MARKING TASK AS DONE:**

### For Phase 4.9 Task 2:
- [ ] **Regression baseline captured** (633/633 unit, 660/660 total tests)
- [ ] **Python model updated FIRST** with Literal type validation
- [ ] **Alembic migration created** with proper order (Data → Drop → Add)
- [ ] **⚠️ CRITICAL: Checked migration for `audit.event` table** and removed if present
- [ ] **Migration applied successfully** (`alembic upgrade head`)
- [ ] **All 3 new tests written and passing**
- [ ] **Tests use `db_session` parameter** and `select()/exec()` pattern
- [ ] **ALL 633 existing unit tests still passing**
- [ ] **ALL 660 total tests still passing** (including integration)
- [ ] **New total: 636/636 unit, 663/663 total (100%)**
- [ ] **Database verification query confirms** constraint updated
- [ ] **Valid status values accepted** by model and database
- [ ] **Legacy status values rejected** with IntegrityError
- [ ] **Migration rollback tested** (`alembic downgrade -1` then `upgrade head`)
- [ ] **Project plan document updated**

### Task-Specific Validation:

**Task 2 (webhook_delivery_attempt):**
- [ ] Model accepts: 'pending', 'success', 'failed', 'giving_up'
- [ ] Model rejects: 'delivered', 'retrying'
- [ ] Default status is 'pending'

---

## Key Files to Review

### Architecture & Design
- `dev-docs/analysis/phase-4.9-db-schema-sync-5-plan.md` - **Task 2 Details** ⭐
- `dev-docs/analysis/phase-4.9-db-schema-sync-5-analysis.md` - Forensic Analysis
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - **Golden Master JSON**

### Backend Code
- `backend/app/models/system.py` - WebhookDeliveryAttempt model

### Tests (Reference for Patterns)
- `backend/tests/test_phase_4_9_connector_run_log_status.py` - Task 1 patterns ⭐
- `backend/tests/test_phase_4_8_*.py` - Recent phase test patterns
- `backend/tests/conftest.py` - Test fixtures

---

## Risk Assessment

**For Phase 4.9 Task 2:**
- **Data Loss Risk:** NONE (table is empty)
- **Logic Risk:** LOW (straightforward value mapping)
- **Regression Risk:** LOW (constraint changes don't affect existing valid data)
- **Rollback Complexity:** LOW (simple constraint swap)
- **Deployment Impact:** MEDIUM (prevents use of legacy status strings)
- **Mitigation:** Update models first, verify no legacy data exists, test thoroughly

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
- **Zero Regression Policy:** All 633 unit + 660 total tests MUST pass

### Phase 4.9 Task 2 Specific
- **Value normalization** - 'delivered' → 'success', 'retrying' → 'pending'
- **Model-first approach** - Update Python models before migrations
- **Empty table** - No real data migration needed (safety UPDATE included)
- **Type safety** - Literal types prevent runtime errors from invalid status strings
- **Webhook integration** - Affects how webhook delivery attempts are tracked and retried

### If You Get Stuck
- Use `postgres-local` MCP server to query database state in real-time
- Review Phase 4.9 Task 1 completed implementation for migration patterns
- Search existing tests for `db_session` and `exec()` patterns
- Check the "Best Practices" section at the top of this document
- Verify migration order: Data → Drop old constraint → Add new constraint
- Ensure Python model Literal types match JSON schema exactly

---

## Example Task Flow

### For Phase 4.9 Task 2 (webhook_delivery_attempt Status Normalization):

```bash
# 1. Baseline - Capture starting point
cd backend
source .venv/bin/activate

# Run unit tests (no integration)
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Record: 633 passed

# Run all tests (including integration)
pytest tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Record: 660 passed

# 2. Update Python Model FIRST (before migration)
# Edit backend/app/models/system.py
# Change WebhookDeliveryAttempt status field from str to Literal["pending", "success", "failed", "giving_up"]

# 3. Verify table is empty (using MCP server)
SELECT COUNT(*) FROM webhook_delivery_attempt;
# Should return 0

# Check for any legacy status values
SELECT DISTINCT status, COUNT(*) 
FROM webhook_delivery_attempt 
GROUP BY status;
# Should show empty result (table is empty)

# 4. Create migration
alembic revision --autogenerate -m "phase_4_9_normalize_webhook_delivery_status_task2"

# 5. Edit migration file
# CRITICAL ORDER in upgrade():
# 1. Data UPDATE (normalize legacy values)
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
WHERE t.relname = 'webhook_delivery_attempt'
  AND contype = 'c'
  AND conname = 'webhook_delivery_attempt_status_chk';

# 9. Create test suite
# Create backend/tests/test_phase_4_9_webhook_delivery_status.py
# - Use db_session: Session parameter
# - Use select() with exec()
# - Test valid statuses accepted
# - Test legacy statuses rejected
# - Test default status value

# 10. Run new tests
pytest tests/test_phase_4_9_webhook_delivery_status.py -v
# All 3 new tests should pass

# 11. Regression check
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Expected: 636 passed (633 + 3 new)

pytest tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Expected: 663 passed (660 + 3 new)

# 12. Rollback test
alembic downgrade -1
alembic upgrade head
pytest tests/ -v  # Should still pass

# 13. Update docs
# Edit dev-docs/analysis/phase-4.9-db-schema-sync-5-plan.md
# Mark Task 2 as complete with test results
```

---

## Questions to Ask

**Before starting:**
1. Have I captured the 633/633 unit and 660/660 total baselines?
2. Have I updated the Python model with Literal type FIRST?
3. Do I understand the value mapping ('delivered' → 'success', 'retrying' → 'pending')?
4. Have I verified the table is empty (no legacy data)?

**During implementation:**
1. Am I using `db_session` parameter (NOT `session`) in tests?
2. Am I using `select()/exec()` pattern (NOT `query()`) in tests?
3. After running `alembic revision`, did I check for and remove `audit.event` table?
4. Is my migration in the correct order: Data UPDATE → DROP old → ADD new?
5. Does my Python model Literal type exactly match the JSON schema values?

**After implementation:**
1. Do I have 100% test pass rate on BOTH unit tests (636/636) and total tests (663/663)?
2. Can I create WebhookDeliveryAttempt objects with all valid status values?
3. Are legacy status values ('delivered', 'retrying') properly rejected with IntegrityError?
4. Does the default status value equal 'pending'?
5. Have I updated the project plan document?
6. Have I tested migration rollback (`alembic downgrade -1`)?

---

**Ready to Begin!** 🚀

### Phase 4.9 Task 2 Checklist:
1. ✅ Capture baseline (633/633 unit, 660/660 total)
2. 📝 **Update Python model with Literal type FIRST**
3. 🔍 Verify table is empty (no legacy data)
4. 📝 Create migration (Data → Drop → Add order)
5. ⚠️ **CRITICAL: Remove `audit.event` table from migration if present**
6. ✅ Apply migration (`alembic upgrade head`)
7. 🔍 Verify constraint via pg_constraint query
8. 🧪 Create 3 tests (valid values, reject legacy, default value)
9. 🔄 Run regression tests (636/636 unit, 663/663 total expected)
10. ↩️ Test rollback (`alembic downgrade -1`, then `upgrade head`)
11. 📚 Update project plan

Remember: Phase 4.9 Task 2 is about **CHECK constraint value alignment** for webhook_delivery_attempt. Update Python models first, ensure proper migration order (Data → Drop → Add), and use Literal types for type safety. The table is empty, making this a low-risk normalization exercise. Be thorough with testing!
