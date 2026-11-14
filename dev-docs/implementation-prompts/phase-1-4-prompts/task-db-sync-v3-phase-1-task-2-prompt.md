# Task 2: Convert `user.preferred_mfa_channel` from ENUM to TEXT

**Reference:** `dev-docs/analysis/phase-4.7-db-schema-sync-3-plan.md` - Phase 1, Task 2
**Authority (Dual Master):**
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - Golden Master JSON
- `dev-docs/db-design/aevofab-db-schema-dump-phase-4.6-post.sql` - Production SQL Dump (Phase 4.6 Baseline)
**Type:** Phase 1 - Type Standardization
**Priority:** HIGH
**Change Type:** MIGRATION

---

## Context

This is **Phase 4.7 - DB Sync v#3**, a third forensic reconciliation after completing Phases 4.5 and 4.6. A comprehensive comparison between the latest SQL dump (`aevofab-db-schema-dump-phase-4.6-post.sql`) and the Golden Master JSON revealed **5 major remaining discrepancies** requiring final alignment before production deployment.

**Key Focus Areas:**
1. **Enumerated type standardization** (ENUM → TEXT + CHECK)
2. **Integer capacity risks** (Foreign key type mismatches)
3. **Unique indexing logic** (Broken email uniqueness constraint)
4. **Data integrity enforcement** (Missing defaults and constraints)
5. **Function/trigger alignment** (Database vs JSON discrepancies)

**Key Principle:** This phase focuses on **architectural decisions** and **implementation gaps** that need final resolution, not new features.

---

## What Was Completed in Previous Phases

**Phase 4.5 Status:** ✅ COMPLETE (March 30 - April 1, 2026)
- ✅ 572/572 tests passing (100%)
- ✅ 100% alignment between physical database and Golden Master JSON achieved
- ✅ All unique, check, and temporal exclusion constraints implemented
- ✅ All 293 triggers verified and functional

**Phase 4.6 Status:** ✅ COMPLETE (April 1-2, 2026)
- ✅ 575/575 unit tests passing (100%)
- ✅ 602/602 total tests passing (100%)
- ✅ Dual-master reconciliation completed
- ✅ Function logic and constraint backporting from SQL to JSON

**Phase 4.7 Task 1 Status:** ✅ COMPLETE (April 3, 2026)
- ✅ 582/582 unit tests passing (100%)
- ✅ 609/609 total tests passing (100%)
- ✅ Converted `customer.type` from ENUM to TEXT
- ✅ Added CHECK constraint `customer_type_chk`
- ✅ Dropped native ENUM type `public.customertype`

**Current Baseline:** 582/582 unit tests, 609/609 total tests passing (100%)

**See:**
- `dev-docs/analysis/phase-4.5-db-schema-sync-to-design-plan.md` for Phase 4.5 history
- `dev-docs/analysis/phase-4.6-db-schema-sync-2-plan.md` for Phase 4.6 history
- `dev-docs/analysis/phase-4.7-db-schema-sync-3-plan.md` for Phase 4.7 Task 1

---

## Current Task: Convert `user.preferred_mfa_channel` from ENUM to TEXT

**Effort:** 0.5 days
**Gap Reference:** Phase 4.7 Analysis - Phase 1: Standardize Enumerated Types
**Change Type:** MIGRATION

This task completes the ENUM standardization initiative by converting the second and final native PostgreSQL ENUM (`user.preferred_mfa_channel`) to TEXT with CHECK constraint validation, aligning with the architectural decision from `enum-vs-text-design-decision.md`.

### What Needs to Be Fixed

| # | Component | Issue | Direction | Complexity |
|---|-----------|-------|-----------|------------|
| **1** | `backend/app/models/core.py` - `User.preferred_mfa_channel` | Column uses native PostgreSQL ENUM `preferredmfachannel` instead of TEXT + CHECK constraint | SQL→SQL | LOW |
| **2** | Database Schema | Native ENUM type `public.preferredmfachannel` exists and must be dropped | SQL→SQL | LOW |
| **3** | `dev-docs/db-design/pilot-db-schema-v2.6h.json` | JSON schema already specifies TEXT + CHECK (correct) - database needs to align | SQL→JSON | LOW |

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

**Record the output of both results:** `582/582 & 609/609 tests passing` (Phase 4.7 baseline - after Task 1 completion)

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

**Action:** Search existing tests to confirm: `grep -r "def test_.*db_session" backend/tests/` shows 217+ tests use `db_session`.

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

### 4. Use Explicit `sa_column` for Type Overrides

❌ **WRONG (Type Mismatch Between Model and DB):**
```python
class MyTable(SQLModel, table=True):
    # Python int maps to INTEGER by default, but you need BIGINT
    big_number: int = Field(foreign_key="other_table.id")
```

✅ **CORRECT (Explicit Type Control):**
```python
from sqlalchemy import Column, BigInteger

class MyTable(SQLModel, table=True):
    # Explicitly specify BIGINT via sa_column
    big_number: int = Field(
        foreign_key="other_table.id",
        sa_column=Column(BigInteger, nullable=False)
    )
```

**Why:** SQLModel's default type mapping for `int` is `INTEGER` (32-bit). If the parent table uses `BIGINT` (64-bit), you must explicitly specify the column type.

**Action:** Review `backend/app/models/quoting.py` and search for `sa_column=Column(BigInteger` to see examples.

---

### 5. Test NULL Handling for Nullable Constraints

❌ **INCOMPLETE TEST (Doesn't Test NULL):**
```python
def test_channel_valid(db_session, test_user):
    """Test valid channel values"""
    endpoint = UserEndpoint(channel='email', value='test@example.com')
    db_session.add(endpoint)
    db_session.commit()
    # Missing: What if channel is NULL?
```

✅ **COMPLETE TEST (Tests NULL if Nullable):**
```python
def test_channel_valid(db_session, test_user):
    """Test valid channel values"""
    endpoint = UserEndpoint(channel='email', value='test@example.com')
    db_session.add(endpoint)
    db_session.commit()

def test_channel_null_allowed(db_session, test_user):
    """Test NULL channel allowed (if nullable=True)"""
    endpoint = UserEndpoint(channel=None, value='test@example.com')
    db_session.add(endpoint)
    db_session.commit()  # Should succeed if nullable
```

**Why:** If a field is nullable, you must test that NULL values are accepted. If it's NOT nullable, test that NULL is rejected.

**Action:** For CHECK constraints with nullable fields, always include `field IS NULL OR field IN (...)` in the constraint.

---

### 6. Pre-Migration Data Validation is MANDATORY

❌ **WRONG (Apply Constraint Without Checking Data):**
```python
def upgrade():
    # Directly add constraint - might fail if existing data invalid!
    op.create_check_constraint(
        'user_email_chk',
        'user',
        "email ~ '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$'"
    )
```

✅ **CORRECT (Validate Data First, Clean if Needed):**
```python
# BEFORE migration, run validation query:
# SELECT email FROM "user"
# WHERE email IS NOT NULL
#   AND email !~ '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$';
# If rows returned, fix data before running migration

def upgrade():
    # Only add constraint after confirming data is clean
    op.create_check_constraint(...)
```

**Why:** Adding a CHECK constraint when existing data violates it will cause the migration to fail. Always validate first.

**Action:** Include validation queries in the migration file as comments. Run them manually before `alembic upgrade`.

### 7. Use the text() wrapper for new SQL

SQLAlchemy requires explicit text() wrapper for raw SQL.

---

## Requirements

### 1. Implementation Details

#### For MIGRATION Tasks (Phase 4.7 - Task 2)

**Problem:** 
The `user.preferred_mfa_channel` column currently uses the native PostgreSQL ENUM `preferredmfachannel`, but the JSON schema mandates TEXT + CHECK constraints per the architectural decision in `enum-vs-text-design-decision.md`.

**Business Rationale:**
- Native ENUMs require migrations to add new values (inflexible)
- Alembic has known issues with ENUM autogenerate
- TEXT + CHECK provides same validation with better maintainability
- Consistent with Task 1 (`customer.type` already converted)

**Current Database State (WRONG):**
```sql
-- Native ENUM type exists:
CREATE TYPE public.preferredmfachannel AS ENUM ('email', 'sms', 'totp');

-- Column uses ENUM:
ALTER TABLE "user" ALTER COLUMN preferred_mfa_channel TYPE public.preferredmfachannel;
```

**JSON Schema (CORRECT - Target State):**
```json
{
  "name": "preferred_mfa_channel",
  "type": "text",
  "nullable": true,
  "constraints": {
    "check": "preferred_mfa_channel IS NULL OR preferred_mfa_channel IN ('email', 'sms', 'totp')"
  }
}
```

**SQLModel Fix:**
```python
# backend/app/models/core.py
from sqlalchemy import CheckConstraint

class User(SQLModel, table=True):
    __tablename__ = "user"
    __table_args__ = (
        # ... existing constraints ...
        CheckConstraint(
            "preferred_mfa_channel IS NULL OR preferred_mfa_channel IN ('email', 'sms', 'totp')",
            name='user_preferred_mfa_channel_chk'
        ),
    )
    
    # Field is nullable (users can opt out of MFA)
    preferred_mfa_channel: str | None = Field(default=None, nullable=True)
```

**Migration SQL:**
```sql
-- Pre-migration validation (RUN FIRST - use postgres-local MCP)
-- Check for invalid values (should be 0 rows):
SELECT id, email, preferred_mfa_channel
FROM "user"
WHERE preferred_mfa_channel NOT IN ('email', 'sms', 'totp')
  AND preferred_mfa_channel IS NOT NULL;

-- Verify current value distribution:
SELECT preferred_mfa_channel, COUNT(*) 
FROM "user" 
GROUP BY preferred_mfa_channel;

-- Migration upgrade():
-- Step 1: Add CHECK constraint (nullable allowed)
ALTER TABLE "user"
ADD CONSTRAINT user_preferred_mfa_channel_chk_temp
CHECK (
  preferred_mfa_channel IS NULL OR
  preferred_mfa_channel::text IN ('email', 'sms', 'totp')
);

-- Step 2: Convert column to TEXT
ALTER TABLE "user"
ALTER COLUMN preferred_mfa_channel TYPE text
USING preferred_mfa_channel::text;

-- Step 3: Drop the ENUM type
DROP TYPE IF EXISTS public.preferredmfachannel CASCADE;

-- Step 4: Rename constraint
ALTER TABLE "user"
DROP CONSTRAINT user_preferred_mfa_channel_chk_temp;

ALTER TABLE "user"
ADD CONSTRAINT user_preferred_mfa_channel_chk
CHECK (
  preferred_mfa_channel IS NULL OR
  preferred_mfa_channel IN ('email', 'sms', 'totp')
);

-- Migration downgrade():
-- Step 1: Recreate ENUM type
CREATE TYPE public.preferredmfachannel AS ENUM ('email', 'sms', 'totp');

-- Step 2: Drop CHECK constraint
ALTER TABLE "user" DROP CONSTRAINT user_preferred_mfa_channel_chk;

-- Step 3: Convert column back to ENUM
ALTER TABLE "user"
ALTER COLUMN preferred_mfa_channel TYPE public.preferredmfachannel
USING preferred_mfa_channel::public.preferredmfachannel;
```

**Database Verification Query:**
```sql
-- Verify column is TEXT type:
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'user' 
  AND column_name = 'preferred_mfa_channel';
-- Expected: data_type = 'text', is_nullable = 'YES'

-- Verify CHECK constraint exists:
SELECT conname, pg_get_constraintdef(oid)
FROM pg_constraint
WHERE conrelid = '"user"'::regclass
  AND conname = 'user_preferred_mfa_channel_chk';
-- Expected: 1 row with CHECK constraint definition

-- Verify ENUM type no longer exists:
SELECT typname FROM pg_type WHERE typname = 'preferredmfachannel';
-- Expected: 0 rows
```

---

### 2. Implementation Order

**For MIGRATION Tasks (Phase 1):**

1. **✅ Establish Regression Baseline** (582/582 unit, 609/609 total tests)
2. **Pre-Migration Data Validation**
   - Run validation queries using postgres-local MCP server
   - Verify no invalid values exist
   - Check current value distribution
3. **Update SQLModel Classes**
   - Modify `backend/app/models/core.py`
   - Add CHECK constraint to `User.__table_args__`
   - Ensure field definition matches JSON schema (nullable=True)
4. **Generate Alembic Migration**
   ```bash
   cd backend
   source .venv/bin/activate
   alembic revision --autogenerate -m "phase_4_7_enum_to_text_preferred_mfa_channel_task2"
   ```
5. **Review & Enhance Migration**
   - **⚠️ CRITICAL: Check for and remove any `audit.event` table references**
   - Verify all changes captured correctly
   - Add pre-migration validation queries as comments
   - Ensure downgrade() is complete and tested
6. **Apply Migration**
   ```bash
   alembic upgrade head
   ```
7. **Create Test Suite**
   - Create `backend/tests/test_phase_4_7_preferred_mfa_channel_enum_to_text.py`
   - Use `db_session` NOT `session`
   - Use `select()` with `exec()` NOT `query()`
8. **Run New Tests**
   ```bash
   pytest tests/test_phase_4_7_preferred_mfa_channel_enum_to_text.py -v
   ```
9. **Run Regression Tests** (see "After You Complete" section)
10. **Update Documentation**

---

### 3. Test Requirements

**⚠️ ZERO REGRESSION POLICY:**
- **ALL 582 existing unit tests MUST still pass**
- **ALL 609 total tests (including integration) MUST still pass**
- **New tests (minimum 7) MUST pass**
- **Target: 100% pass rate on both test suites**

#### Test File: `backend/tests/test_phase_4_7_preferred_mfa_channel_enum_to_text.py`

**Required Coverage (Minimum 7 Tests):**
```python
"""
Test Suite: Phase 4.7 Task 2 - Convert user.preferred_mfa_channel ENUM to TEXT

Tests conversion of user.preferred_mfa_channel from native PostgreSQL ENUM 
to TEXT with CHECK constraint validation - final ENUM standardization for 
production deployment.

Reference: phase-4.7-db-schema-sync-3-plan.md - Phase 1, Task 2
"""
import pytest
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from app.models.core import User

# ✅ CORRECT: Use db_session parameter and select()/exec() pattern

class TestPreferredMfaChannelEnumToText:
    """Test user.preferred_mfa_channel ENUM → TEXT conversion"""
    
    def test_email_channel_valid(self, db_session: Session, test_tenant):
        """Test 'email' value accepted"""
        user = User(
            email="mfa-email@test.com",
            preferred_mfa_channel='email',
            tenant_id=test_tenant.id
        )
        db_session.add(user)
        db_session.commit()
        
        # Verify stored correctly
        result = db_session.exec(
            select(User).where(User.id == user.id)
        ).first()
        assert result is not None
        assert result.preferred_mfa_channel == 'email'
    
    def test_sms_channel_valid(self, db_session: Session, test_tenant):
        """Test 'sms' value accepted"""
        user = User(
            email="mfa-sms@test.com",
            preferred_mfa_channel='sms',
            tenant_id=test_tenant.id
        )
        db_session.add(user)
        db_session.commit()
        
        result = db_session.exec(
            select(User).where(User.id == user.id)
        ).first()
        assert result.preferred_mfa_channel == 'sms'
    
    def test_totp_channel_valid(self, db_session: Session, test_tenant):
        """Test 'totp' value accepted"""
        user = User(
            email="mfa-totp@test.com",
            preferred_mfa_channel='totp',
            tenant_id=test_tenant.id
        )
        db_session.add(user)
        db_session.commit()
        
        result = db_session.exec(
            select(User).where(User.id == user.id)
        ).first()
        assert result.preferred_mfa_channel == 'totp'
    
    def test_null_channel_allowed(self, db_session: Session, test_tenant):
        """Test NULL value accepted (users can opt out of MFA)"""
        user = User(
            email="mfa-none@test.com",
            preferred_mfa_channel=None,
            tenant_id=test_tenant.id
        )
        db_session.add(user)
        db_session.commit()
        
        result = db_session.exec(
            select(User).where(User.id == user.id)
        ).first()
        assert result.preferred_mfa_channel is None
    
    def test_invalid_channel_rejected(self, db_session: Session, test_tenant):
        """Test invalid value rejected (e.g., 'phone')"""
        user = User(
            email="mfa-invalid@test.com",
            preferred_mfa_channel='phone',  # Invalid value
            tenant_id=test_tenant.id
        )
        db_session.add(user)
        
        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()
        assert 'user_preferred_mfa_channel_chk' in str(exc_info.value)
        
        # Rollback to clean up failed transaction
        db_session.rollback()
    
    def test_column_type_is_text(self, db_session: Session):
        """Verify column is TEXT type in database"""
        result = db_session.exec(
            select("column_name", "data_type").select_from(
                "information_schema.columns"
            ).where(
                "table_name = 'user' AND column_name = 'preferred_mfa_channel'"
            )
        ).first()
        
        assert result is not None
        assert result[1] == 'text'
    
    def test_enum_type_dropped(self, db_session: Session):
        """Verify native ENUM type 'preferredmfachannel' no longer exists"""
        result = db_session.exec(
            select("typname").select_from("pg_type").where(
                "typname = 'preferredmfachannel'"
            )
        ).first()
        
        # Should return None (0 rows) - ENUM type dropped
        assert result is None


class TestMfaWorkflowIntegration:
    """Test MFA workflow still functions correctly after migration"""
    
    def test_user_can_update_mfa_preference(self, db_session: Session, test_tenant):
        """Test user can change MFA channel preference"""
        # Create user with email MFA
        user = User(
            email="mfa-update@test.com",
            preferred_mfa_channel='email',
            tenant_id=test_tenant.id
        )
        db_session.add(user)
        db_session.commit()
        
        # Update to SMS
        user.preferred_mfa_channel = 'sms'
        db_session.commit()
        
        # Verify change persisted
        result = db_session.exec(
            select(User).where(User.id == user.id)
        ).first()
        assert result.preferred_mfa_channel == 'sms'
        
        # Update to NULL (opt out)
        user.preferred_mfa_channel = None
        db_session.commit()
        
        result = db_session.exec(
            select(User).where(User.id == user.id)
        ).first()
        assert result.preferred_mfa_channel is None
```

**Test Patterns to Follow:**
- Review `backend/tests/test_phase_4_7_customer_type_enum_to_text.py` - Task 1 reference
- Review `backend/tests/test_check_constraints_task9.py` - Shows proper constraint testing
- Use fixtures from `backend/tests/conftest.py`

**Common Test Fixtures Available:**
- `db_session` - Database session (use this, NOT `session`)
- `test_tenant` - Pre-created tenant for testing
- `test_user` - Pre-created user linked to test_tenant
- `utc_now` - Timezone-aware current timestamp function

---

### 4. JSON Change Tracking

**Not Applicable for This Task** - This is a migration task (SQL → SQL alignment). JSON schema already has the correct definition.

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
# Run unit tests (no integration) FIRST
# Concise output to capture baseline count (this is preferred option to minimize tokens)
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed|===)" | tail -5

# Run all tests (including integration) SECOND
# Concise output to capture baseline count (this is preferred option to minimize tokens)
pytest tests/ -v 2>&1 | grep -E "(passed|failed|===)" | tail -5
```

**Expected:**
- **Unit tests:** `589 passed` (582 baseline + 7 new tests)
- **Total tests:** `616 passed` (609 baseline + 7 new tests)

### Step 3: Verify 100% Pass Rate

**If ANY tests fail:**
1. Identify failing tests
2. Determine if new or existing tests
3. Fix ALL failures before proceeding
4. Re-run until 100% pass rate

**For MIGRATION tasks:**
- If new tests fail → Fix implementation or test logic
- If existing tests fail → Your migration broke something (rollback and fix)

---

## Documentation Update

### Update Project Plan Document

**File to Update:** `dev-docs/analysis/phase-4.7-db-schema-sync-3-plan.md`

Find Phase 1, Task 2 (lines 203-325) and update with:

```markdown
### Task 2: Convert `user.preferred_mfa_channel` from ENUM to TEXT

**Status:** ✅ COMPLETE (2026-04-XX)
**Effort:** 0.5 days (actual)
**Change Type:** MIGRATION

**Implementation Summary:**

- Modified: `backend/app/models/core.py`
- Migration: `YYYY_MM_DD_HHMM-[hash]_phase_4_7_enum_to_text_preferred_mfa_channel_task2.py`
- Test Suite: `test_phase_4_7_preferred_mfa_channel_enum_to_text.py` - 8 tests ✅
- Final Results: 589/589 unit tests passing (100%), 616/616 total tests passing (100%)

**Key Changes:**
- ✅ Converted `user.preferred_mfa_channel` from PostgreSQL ENUM to TEXT
- ✅ Added CHECK constraint `user_preferred_mfa_channel_chk` to enforce valid values ('email', 'sms', 'totp')
- ✅ Dropped native ENUM type `public.preferredmfachannel`
- ✅ Aligned with architectural decision from enum-vs-text-design-decision.md
- ✅ Maintained nullable semantics (users can opt out of MFA)
- ✅ Phase 1 (Enum Standardization) now COMPLETE - zero native ENUMs remain

**Verification:**
- Column type verified as TEXT with nullable=true via information_schema query
- CHECK constraint active and enforcing ('email', 'sms', 'totp', NULL) values
- ENUM type 'preferredmfachannel' confirmed dropped
- Migration rollback tested successfully (downgrade → upgrade)
- All baseline tests still passing + 7+ new tests
- MFA workflow integration verified
```

---

## Success Criteria

**MUST COMPLETE ALL BEFORE MARKING TASK AS DONE:**

### For MIGRATION Tasks (Task 2):
- [ ] **Regression baseline captured** (582/582 unit, 609/609 total tests)
- [ ] **Pre-migration data validation completed** (queries run via postgres-local MCP, data clean)
- [ ] **SQLModel classes updated** with CHECK constraint in `__table_args__`
- [ ] **Used `db_session` parameter** (not `session`) in code
- [ ] **Used `select()/exec()` pattern** (not `query()`) where applicable
- [ ] **Alembic migration created** using autogenerate
- [ ] **⚠️ CRITICAL: Checked migration for `audit.event` table** and removed if present
- [ ] **Migration applied successfully** (`alembic upgrade head`)
- [ ] **All 7+ new tests written and passing**
- [ ] **Tests use `db_session` parameter** and `select()/exec()` pattern
- [ ] **ALL 582 existing unit tests still passing**
- [ ] **ALL 609 total tests still passing** (including integration)
- [ ] **New total: 589/589 unit passing, 616/616 total passing (100%)**
- [ ] **Database verification query confirms** changes active
- [ ] **Migration rollback tested** (`alembic downgrade -1` then `upgrade head` again)
- [ ] **Project plan document updated**
- [ ] **Phase 1 marked COMPLETE** (all enum standardization done)

### For ALL Tasks:
- [ ] **100% test pass rate** - No failing tests
- [ ] **Zero regression** - Baseline maintained or exceeded

---

## Key Files to Review

### Architecture & Design
- `dev-docs/analysis/phase-4.7-db-schema-sync-3-plan.md` - **Task 2 Details** ⭐
- `dev-docs/analysis/phase-4.7-db-schema-sync-3-analysis.md` - Forensic Analysis
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - **Golden Master JSON**
- `dev-docs/db-design/aevofab-db-schema-dump-phase-4.6-post.sql` - **Production SQL Dump (Phase 4.6 Baseline)**
- `dev-docs/db-design/enum-vs-text-design-decision.md` - **Design Decision for ENUM vs TEXT** ⭐

### Backend Code
- `backend/app/models/core.py` - `User` model (preferred_mfa_channel field)

### Tests (Reference for Patterns)
- `backend/tests/test_phase_4_7_customer_type_enum_to_text.py` - **Task 1 reference (similar pattern)** ⭐
- `backend/tests/test_check_constraints_task9.py` - CHECK constraint patterns
- `backend/tests/conftest.py` - Test fixtures (`db_session`, `test_tenant`, etc.)

---

## Risk Assessment

**Data Validation Risk:** LOW
- Current field is nullable, so NULL values are expected
- Only 3 valid ENUM values to check
- **Mitigation:** Pre-migration query validates no invalid values exist

**Regression Risk:** LOW
- Task 1 (customer.type conversion) successfully completed with same pattern
- MFA functionality is well-tested
- **Mitigation:** Maintain 582/609 baseline, test after migration, check alembic for audit.event

**Security Risk:** NONE
- CHECK constraint maintains same validation as ENUM
- No change to authentication/authorization logic
- **Mitigation:** MFA workflow integration tests verify functionality

**Rollback Risk:** LOW
- Downgrade recreates ENUM and converts column back
- TEXT → ENUM conversion is safe (all values are valid ENUM members)
- **Mitigation:** Test rollback before marking task complete

---

## Notes

### Important Patterns to Follow
- **Virtual Environment Required:** All Python/pytest commands use `source .venv/bin/activate`
- **Use `db_session` Parameter:** NOT `session` (pytest fixture naming)
- **Use `select()/exec()` Pattern:** NOT `query()` (SQLModel standard, no deprecation warnings)
- **Check Alembic Migrations:** ALWAYS remove `audit.event` table creation if autogenerated
- **Test NULL Handling:** This field is nullable - test both NULL and valid values
- **Follow Task 1 Pattern:** Use `test_phase_4_7_customer_type_enum_to_text.py` as template
- **Zero Regression Policy:** All 582 unit + 609 total tests MUST pass after changes

### Phase 4.7 Specific
- **Task 2 completes Phase 1** - After this, zero native PostgreSQL ENUMs remain
- **Consistency with Task 1** - Same conversion pattern (ENUM → TEXT + CHECK)
- **Architectural alignment** - Implements `enum-vs-text-design-decision.md`
- **Pre-validate all data** - Run validation queries BEFORE applying constraints
- **Test NULL handling** - Field is nullable, test both NULL and valid values

### If You Get Stuck
- Check Task 1 implementation for reference pattern
- Review the SQL dump for exact production definitions
- Use `postgres-local` MCP server to query database in real-time
- Search existing tests for `db_session` and `exec()` patterns
- Review the "Best Practices" section at the top of this prompt
- Remember: This is the second (and final) ENUM conversion - follow Task 1 pattern

---

## Example Task Flow

### For MIGRATION Tasks (Task 2):

```bash
# 1. Baseline - Capture starting point
cd backend
source .venv/bin/activate

# Run unit tests (no integration)
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Record: 582 passed

# Run all tests (including integration)
pytest tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Record: 609 passed

# 2. Pre-migration data validation using postgres-local MCP server
# Query: SELECT id, email, preferred_mfa_channel FROM "user" 
#        WHERE preferred_mfa_channel NOT IN ('email', 'sms', 'totp') 
#          AND preferred_mfa_channel IS NOT NULL;
# Expected: 0 rows (no invalid data)

# Query: SELECT preferred_mfa_channel, COUNT(*) FROM "user" GROUP BY preferred_mfa_channel;
# Expected: Distribution of 'email', 'sms', 'totp', NULL values

# 3. Update SQLModel classes
# Edit backend/app/models/core.py
# - Add CheckConstraint to User.__table_args__
# - Ensure preferred_mfa_channel field is nullable=True

# 4. Generate migration
alembic revision --autogenerate -m "phase_4_7_enum_to_text_preferred_mfa_channel_task2"

# 5. ⚠️ CRITICAL: Review migration file
# Open backend/migrations/versions/[timestamp]_phase_4_7_enum_to_text_preferred_mfa_channel_task2.py
# Search for 'audit' and 'event'
# DELETE any op.create_table('event', ... schema='audit') blocks
# DELETE any op.drop_table('event', ... schema='audit') blocks
# Verify your actual changes are present (ALTER COLUMN, DROP TYPE, etc.)
# Add pre-migration validation queries as comments

# 6. Apply migration
alembic upgrade head

# 7. Create test suite
# Create backend/tests/test_phase_4_7_preferred_mfa_channel_enum_to_text.py
# - Use db_session: Session parameter
# - Use select() with exec()
# - Test 'email', 'sms', 'totp', NULL, invalid values
# - Test column type is TEXT
# - Test ENUM type no longer exists
# - Test MFA workflow integration

# 8. Run new tests
pytest tests/test_phase_4_7_preferred_mfa_channel_enum_to_text.py -v
# All new tests should pass

# 9. Regression check - Ensure no breaks
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Expected: 589 passed (582 + 7)

pytest tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Expected: 616 passed (609 + 7)

# 10. Rollback test - Verify downgrade works
alembic downgrade -1
alembic upgrade head
pytest tests/ -v  # Should still pass

# 11. Update docs
# Edit dev-docs/analysis/phase-4.7-db-schema-sync-3-plan.md
# Mark Task 2 as complete with test results
# Mark Phase 1 as COMPLETE (all enum standardization done)
```

---

## Questions to Ask

**Before starting:**
1. Have I captured the 582/582 unit and 609/609 total baselines?
2. Have I validated existing data won't violate new CHECK constraint (using postgres-local MCP)?
3. Do I understand the nullable semantics (users can opt out of MFA = NULL allowed)?
4. Have I reviewed Task 1 implementation as a reference pattern?
5. Do I have the enum-vs-text-design-decision.md context?

**During implementation:**
1. Am I using `db_session` parameter (NOT `session`) in tests?
2. Am I using `select()/exec()` pattern (NOT `query()`) in tests?
3. After running `alembic revision --autogenerate`, did I check for and remove `audit.event` table creation?
4. Am I testing NULL handling (field is nullable)?
5. Are my tests consistent with Task 1 test patterns?
6. Did I include the NULL clause in CHECK constraint: `preferred_mfa_channel IS NULL OR ...`?

**After implementation:**
1. Do I have 100% test pass rate on BOTH unit tests (589) and total tests (616)?
2. Did baseline increase by exactly 7 tests (582+7=589, 609+7=616)?
3. Have I verified the column is TEXT type in database?
4. Have I verified the ENUM type no longer exists?
5. Have I tested migration rollback (`alembic downgrade -1`)?
6. Have I updated the project plan document?
7. Have I marked Phase 1 as COMPLETE (all enum standardization done)?

---

**Ready to Begin!** 🚀

### MIGRATION Task Checklist (Task 2):
1. ✅ Capture baseline (582/582 unit, 609/609 total)
2. 🔍 Validate existing data (run pre-migration queries via postgres-local MCP)
3. 🛠️ Update SQLModel classes (add CHECK constraint, ensure nullable=True)
4. 📝 Generate migration (`alembic revision --autogenerate`)
5. ⚠️ **CRITICAL: Remove `audit.event` table from migration if present**
6. ✅ Apply migration (`alembic upgrade head`)
7. 🧪 Create comprehensive tests (7+ tests, use Task 1 as template)
8. 🔄 Run regression tests (589 unit, 616 total)
9. ↩️ Test rollback (`alembic downgrade -1`, then `upgrade head`)
10. 📚 Update project plan (mark Task 2 COMPLETE, mark Phase 1 COMPLETE)

Remember: This task completes Phase 1 (Enum Standardization) - after this, the database will have **zero native PostgreSQL ENUMs**, fully aligned with the architectural decision for TEXT + CHECK constraints. Be thorough, validate data, test NULL handling, and always check for the `audit.event` table issue in migrations!
