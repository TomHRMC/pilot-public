# Task 4: Fix Global Primary Email Unique Index Logic

**Reference:** `dev-docs/analysis/phase-4.7-db-schema-sync-3-plan.md` - Phase 3, Task 4
**Authority (Dual Master):**
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - Golden Master JSON
- `dev-docs/db-design/aevofab-db-schema-dump-phase-4.6-post.sql` - Production SQL Dump (Phase 4.6 Baseline)
**Type:** Phase 3 - Database Index Repair
**Priority:** CRITICAL
**Change Type:** MIGRATION

---

## Context

This is **Phase 4.7 - DB Sync v#3**, a third forensic reconciliation after completing Phases 4.5 and 4.6. A comprehensive comparison between the latest SQL dump (`aevofab-db-schema-dump-phase-4.6-post.sql`) and the Golden Master JSON revealed **5 major remaining discrepancies** requiring final alignment before production deployment.

**Key Focus Areas:**
1. **Enumerated type standardization** (ENUM → TEXT + CHECK)
2. **Integer capacity risks** (Foreign key type mismatches)
3. **Unique indexing logic** (Broken email uniqueness constraint) ⭐ **THIS TASK**
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

**Phase 4.7 Progress:**
- ✅ Phase 1 COMPLETE - Enum standardization (Tasks 1-2, 16 new tests)
- ✅ Phase 2 COMPLETE - Integer capacity fixes (Task 3, 6 new tests)
- 🔴 Phase 3 NOT STARTED - Unique indexing fix ⭐ **YOU ARE HERE**

**Current Baseline:** 597/597 unit tests, 624/624 total tests passing (100%)

**See:**
- `dev-docs/analysis/phase-4.5-db-schema-sync-to-design-plan.md` for Phase 4.5 history
- `dev-docs/analysis/phase-4.6-db-schema-sync-2-plan.md` for Phase 4.6 history

---

## Current Task: Fix Global Primary Email Unique Index Logic

**Effort:** 0.5 days
**Gap Reference:** Phase 4.7 Analysis - Phase 3: Fix Broken Unique Indexing
**Change Type:** MIGRATION

The unique index `ux_global_primary_email` on the `user_endpoint` table is **logically broken**. It currently prevents one user from having multiple primary emails (already prevented by other constraints) but **fails to prevent multiple users from sharing the same primary email address**, creating a critical security vulnerability for email-based authentication and password reset flows.

### What Needs to Be Fixed

| # | Component | Issue | Direction | Complexity |
|---|-----------|-------|-----------|------------|
| **1** | `user_endpoint` | Unique index `ux_global_primary_email` targets `user_id` instead of `LOWER(value)` | SQL→SQL | MEDIUM |

### Security Impact

**Current Broken State:**
```sql
-- Database (WRONG):
CREATE UNIQUE INDEX ux_global_primary_email 
ON user_endpoint (user_id) 
WHERE channel = 'email' AND is_primary = true;

-- Problem: Allows duplicates
-- User 1: email = "admin@company.com", is_primary = true  ✓ Allowed
-- User 2: email = "admin@company.com", is_primary = true  ✓ Allowed (BUG!)
```

**Security Vulnerabilities:**
- Multiple users can have the same primary email (e.g., admin@company.com)
- Email-based password reset could affect wrong user
- Violates "one email = one identity" security principle
- Authentication bypasses possible

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

**Record the output of both results:** `597/597 & 624/624 tests passing` (Phase 4.7 baseline after Tasks 1-3)

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

**Action:** Search existing tests to confirm: `grep -r "def test_.*db_session" backend/tests/` shows 217 tests use `db_session`.

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
    op.drop_index(...)  # Your actual changes
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

#### For MIGRATION Tasks (This Task is a MIGRATION)

**Problem:** 
The unique index `ux_global_primary_email` is incorrectly targeting `user_id` instead of the email value itself, allowing multiple users to share the same primary email address.

**Current Broken State:**
```sql
-- Database (WRONG):
CREATE UNIQUE INDEX ux_global_primary_email 
ON user_endpoint (user_id) 
WHERE channel = 'email' AND is_primary = true;

-- This only ensures one user doesn't have multiple primary emails
-- (already prevented by another constraint)
-- But ALLOWS multiple users to have the same primary email!
```

**Required Correct State:**
```sql
-- JSON Schema (CORRECT):
CREATE UNIQUE INDEX ux_global_primary_email 
ON user_endpoint (LOWER(value)) 
WHERE channel = 'email' AND is_primary = true;

-- This ensures GLOBAL uniqueness of primary email addresses
-- (case-insensitive comparison via LOWER())
```

**Migration SQL:**
```sql
-- Pre-migration validation
-- Find duplicate primary emails (should be 0 rows if data is clean)
SELECT LOWER(value) AS email, COUNT(*) AS user_count
FROM user_endpoint
WHERE channel = 'email' AND is_primary = true
GROUP BY LOWER(value)
HAVING COUNT(*) > 1;

-- If duplicates exist, resolve manually before migration

-- Drop broken index
DROP INDEX IF EXISTS ux_global_primary_email;

-- Create correct index (case-insensitive email uniqueness)
CREATE UNIQUE INDEX ux_global_primary_email 
ON user_endpoint (LOWER(value)) 
WHERE channel = 'email' AND is_primary = true;
```

**Database Verification Query:**
```sql
-- Verify correct index exists after migration
SELECT 
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE indexname = 'ux_global_primary_email';

-- Expected: indexdef should contain "lower(value)" not "user_id"
```

**⚠️ IMPORTANT: No SQLModel Changes Required**
- The index is partial and expression-based (manual Alembic migration only)
- SQLModel doesn't support expression-based partial indexes in `__table_args__`
- The index definition exists only in the Alembic migration
- No changes needed to `backend/app/models/core.py`

---

### 2. Implementation Order

**For MIGRATION Tasks:**

1. **✅ Establish Regression Baseline** (597/597 unit, 624/624 total tests)
2. **Pre-Migration Data Validation**
   - Run validation query to find duplicate primary emails
   - Clean up invalid data if found (manually resolve duplicates)
3. **Create Alembic Migration**
   ```bash
   cd backend
   source .venv/bin/activate
   alembic revision -m "phase_4_7_fix_global_primary_email_index_task4"
   ```
4. **Write Migration Manually** (NOT autogenerate - this is index-only)
   - Open the generated migration file
   - Add DROP INDEX statement in upgrade()
   - Add CREATE INDEX with LOWER(value) in upgrade()
   - Add reverse operations in downgrade()
5. **Review Migration**
   - Verify DROP INDEX IF EXISTS used (safe operation)
   - Verify CREATE INDEX uses LOWER(value) not user_id
   - Ensure downgrade() recreates broken index (for rollback)
6. **Apply Migration**
   ```bash
   alembic upgrade head
   ```
7. **Create Test Suite**
   - Create `backend/tests/test_phase_4_7_global_primary_email_index.py`
   - Use `db_session` parameter and `select()/exec()` pattern
8. **Run New Tests**
   ```bash
   pytest tests/test_phase_4_7_global_primary_email_index.py -v
   ```
9. **Run Regression Tests** (see "After You Complete" section)
10. **Update Documentation**

---

### 3. Test Requirements

**⚠️ ZERO REGRESSION POLICY:**
- **ALL 597 existing unit tests MUST still pass**
- **ALL 624 total tests (including integration) MUST still pass**
- **New tests (minimum 5) MUST pass**
- **Target: 100% pass rate on both test suites**

#### Test Coverage Requirements (Minimum 5 Tests)

**Test File:** `backend/tests/test_phase_4_7_global_primary_email_index.py`

**Required Tests:**

```python
"""
Test Suite: Phase 4.7 Task 4 - Fix Global Primary Email Unique Index
Tests global email uniqueness enforcement - final schema alignment for production

Reference: phase-4.7-db-schema-sync-3-plan.md - Phase 3, Task 4
"""
import pytest
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from app.models.core import User, UserEndpoint

class TestGlobalPrimaryEmailUniqueness:
    """Test global uniqueness of primary email addresses across all users"""
    
    def test_user_can_set_primary_email(self, db_session: Session, test_tenant, test_user):
        """User should be able to set a primary email"""
        endpoint = UserEndpoint(
            user_id=test_user.id,
            channel='email',
            value='unique@test.com',
            is_primary=True,
            verification_status='verified'
        )
        db_session.add(endpoint)
        db_session.commit()
        
        result = db_session.exec(
            select(UserEndpoint).where(UserEndpoint.id == endpoint.id)
        ).first()
        assert result is not None
        assert result.value == 'unique@test.com'
        assert result.is_primary is True
    
    def test_duplicate_primary_email_rejected_same_case(self, db_session: Session, test_tenant):
        """Second user cannot use same primary email (same case)"""
        # Create two users
        user1 = User(
            email='user1@temp.com',
            tenant_id=test_tenant.id,
            full_name='User One'
        )
        user2 = User(
            email='user2@temp.com',
            tenant_id=test_tenant.id,
            full_name='User Two'
        )
        db_session.add(user1)
        db_session.add(user2)
        db_session.commit()
        
        # User 1 sets primary email
        endpoint1 = UserEndpoint(
            user_id=user1.id,
            channel='email',
            value='shared@test.com',
            is_primary=True,
            verification_status='verified'
        )
        db_session.add(endpoint1)
        db_session.commit()
        
        # User 2 attempts same primary email (should fail)
        endpoint2 = UserEndpoint(
            user_id=user2.id,
            channel='email',
            value='shared@test.com',
            is_primary=True,
            verification_status='verified'
        )
        db_session.add(endpoint2)
        
        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()
        assert 'ux_global_primary_email' in str(exc_info.value)
        
        db_session.rollback()
    
    def test_duplicate_primary_email_rejected_different_case(self, db_session: Session, test_tenant):
        """Second user cannot use same primary email (different case - case-insensitive)"""
        # Create two users
        user1 = User(
            email='user1@temp.com',
            tenant_id=test_tenant.id,
            full_name='User One'
        )
        user2 = User(
            email='user2@temp.com',
            tenant_id=test_tenant.id,
            full_name='User Two'
        )
        db_session.add(user1)
        db_session.add(user2)
        db_session.commit()
        
        # User 1 sets primary email (lowercase)
        endpoint1 = UserEndpoint(
            user_id=user1.id,
            channel='email',
            value='admin@company.com',
            is_primary=True,
            verification_status='verified'
        )
        db_session.add(endpoint1)
        db_session.commit()
        
        # User 2 attempts same email with different case (should fail)
        endpoint2 = UserEndpoint(
            user_id=user2.id,
            channel='email',
            value='ADMIN@COMPANY.COM',
            is_primary=True,
            verification_status='verified'
        )
        db_session.add(endpoint2)
        
        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()
        assert 'ux_global_primary_email' in str(exc_info.value)
        
        db_session.rollback()
    
    def test_same_email_allowed_as_non_primary(self, db_session: Session, test_tenant):
        """Multiple users can have same email as non-primary contact"""
        # Create two users
        user1 = User(
            email='user1@temp.com',
            tenant_id=test_tenant.id,
            full_name='User One'
        )
        user2 = User(
            email='user2@temp.com',
            tenant_id=test_tenant.id,
            full_name='User Two'
        )
        db_session.add(user1)
        db_session.add(user2)
        db_session.commit()
        
        # User 1 uses email as non-primary
        endpoint1 = UserEndpoint(
            user_id=user1.id,
            channel='email',
            value='shared@contact.com',
            is_primary=False,
            verification_status='verified'
        )
        db_session.add(endpoint1)
        db_session.commit()
        
        # User 2 can also use same email as non-primary (allowed)
        endpoint2 = UserEndpoint(
            user_id=user2.id,
            channel='email',
            value='shared@contact.com',
            is_primary=False,
            verification_status='verified'
        )
        db_session.add(endpoint2)
        db_session.commit()  # Should succeed
        
        assert endpoint1.value == endpoint2.value
        assert endpoint1.is_primary is False
        assert endpoint2.is_primary is False
    
    def test_index_definition_targets_value_not_user_id(self, db_session: Session):
        """Verify index definition targets LOWER(value) not user_id"""
        result = db_session.exec(
            select(text("indexdef")).select_from(text("pg_indexes"))
            .where(text("indexname = 'ux_global_primary_email'"))
        ).first()
        
        # Note: This test verifies index structure
        # Adjust SQL if needed based on actual query pattern
        # The key assertion: indexdef should contain "lower(value)" not "user_id"
```

**Test Patterns to Follow:**
- Review `backend/tests/test_check_constraints_task9.py` - Shows proper constraint testing
- Review `backend/tests/test_citext_email.py` - Shows correct `select()/exec()` usage
- Use fixtures from `backend/tests/conftest.py`

**Common Test Fixtures Available:**
- `db_session` - Database session (use this, NOT `session`)
- `test_tenant` - Pre-created tenant for testing
- `test_user` - Pre-created user linked to test_tenant
- `test_customer` - Pre-created customer
- `test_site` - Pre-created site
- `utc_now` - Timezone-aware current timestamp function

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
# Run unit tests (no integration)
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed|===)" | tail -5

# Run all tests (including integration)
pytest tests/ -v 2>&1 | grep -E "(passed|failed|===)" | tail -5
```

**Expected:**
- **Unit tests:** `602 passed` (597 baseline + 5 new tests)
- **Total tests:** `629 passed` (624 baseline + 5 new tests)

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

Find Phase 3, Task 4 and update with:

```markdown
### Task 4: Fix `ux_global_primary_email` Unique Index Logic

**Status:** ✅ COMPLETE (YYYY-MM-DD)
**Effort:** 0.5 days (actual)
**Change Type:** MIGRATION

**Implementation Summary:**

- Migration: `YYYY_MM_DD_HHMM-[hash]_phase_4_7_fix_global_primary_email_index_task4.py`
- Test Suite: `test_phase_4_7_global_primary_email_index.py` - 5 tests ✅
- Final Results: 602/602 unit tests passing (100%), 629/629 total tests passing (100%)

**Key Changes:**
- ✅ Dropped broken index targeting `user_id`
- ✅ Created correct index targeting `LOWER(value)` for case-insensitive global uniqueness
- ✅ Verified no duplicate primary emails exist in database
- ✅ Email-based authentication now secure (one primary email = one user globally)

**Verification:**
- Index `ux_global_primary_email` confirmed to target `LOWER(value)`
- Duplicate primary emails rejected (case-insensitive)
- Same email allowed as non-primary contact (business requirement)
- Migration rollback tested successfully (downgrade → upgrade)
```

---

## Success Criteria

**MUST COMPLETE ALL BEFORE MARKING TASK AS DONE:**

### For MIGRATION Tasks:
- [ ] **Regression baseline captured** (597/597 unit, 624/624 total tests)
- [ ] **Pre-migration data validation completed** (query run, duplicates resolved if found)
- [ ] **Manual Alembic migration created** (NOT autogenerate - index operations only)
- [ ] **Migration includes DROP INDEX IF EXISTS** (safe operation)
- [ ] **Migration includes CREATE INDEX with LOWER(value)** (correct uniqueness)
- [ ] **Migration applied successfully** (`alembic upgrade head`)
- [ ] **All 5 new tests written and passing**
- [ ] **Tests use `db_session` parameter** and `select()/exec()` pattern
- [ ] **ALL 597 existing unit tests still passing**
- [ ] **ALL 624 total tests still passing** (including integration)
- [ ] **New total: 602/602 unit passing, 629/629 total passing (100%)**
- [ ] **Database verification query confirms** index targets LOWER(value)
- [ ] **Migration rollback tested** (`alembic downgrade -1` then `upgrade head` again)
- [ ] **Project plan document updated**

### For ALL Tasks:
- [ ] **100% test pass rate** - No failing tests
- [ ] **Zero regression** - Baseline maintained or exceeded

---

## Key Files to Review

### Architecture & Design
- `dev-docs/analysis/phase-4.7-db-schema-sync-3-plan.md` - **Task 4 Details** ⭐
- `dev-docs/analysis/phase-4.7-db-schema-sync-3-analysis.md` - Forensic Analysis
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - **Golden Master JSON**
- `dev-docs/db-design/aevofab-db-schema-dump-phase-4.6-post.sql` - **Production SQL Dump**

### Backend Code
- `backend/app/models/core.py` - UserEndpoint model (NO CHANGES NEEDED for this task)

### Tests (Reference for Patterns)
- `backend/tests/test_check_constraints_task9.py` - CHECK constraint patterns
- `backend/tests/test_citext_email.py` - Correct `select()/exec()` usage
- `backend/tests/conftest.py` - Test fixtures (`db_session`, `test_tenant`, etc.)

---

## Risk Assessment

**Data Validation Risk:** MEDIUM
- Must check for existing duplicate primary emails before migration
- If duplicates exist, must resolve manually (business decision: which user keeps email?)
- **Mitigation:** Run validation query, document duplicates, resolve before migration

**Security Risk:** HIGH (if not fixed)
- Current state allows duplicate primary emails (authentication vulnerability)
- Password reset could affect wrong user
- Email-based login could be ambiguous
- **Mitigation:** Fix immediately (CRITICAL priority)

**Regression Risk:** LOW
- Index change should not affect application code
- Other constraints already prevent invalid data
- **Mitigation:** Maintain 597/624 baseline, test after every change

---

## Notes

### Important Patterns to Follow
- **Virtual Environment Required:** All Python/pytest commands use `source .venv/bin/activate`
- **Use `db_session` Parameter:** NOT `session` (pytest fixture naming)
- **Use `select()/exec()` Pattern:** NOT `query()` (SQLModel standard, no deprecation warnings)
- **Manual Migration:** Don't use autogenerate for index-only changes
- **No SQLModel Changes:** Expression-based indexes can't be defined in `__table_args__`
- **Zero Regression Policy:** All 597 unit + 624 total tests MUST pass after changes

### Phase 4.7 Specific
- **Final production alignment** - Last schema sync before deployment
- **This is a CRITICAL security fix** - Email authentication depends on uniqueness
- **Focus on data validation** - Check for duplicates BEFORE migration
- **Test case-insensitivity** - LOWER(value) ensures case-insensitive uniqueness
- **Manual migration required** - Alembic autogenerate won't capture index expression

### If You Get Stuck
- Check existing partial indexes in the database for patterns
- Review how other unique constraints are tested
- Use `postgres-local` MCP server to inspect current index definition
- Search existing tests for `IntegrityError` and `rollback()` patterns
- Remember: This is index-only, no SQLModel changes needed

---

## Example Task Flow

### For MIGRATION Tasks (This Task):

```bash
# 1. Baseline - Capture starting point
cd backend
source .venv/bin/activate

# Run unit tests (no integration)
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Record: 597 passed

# Run all tests (including integration)
pytest tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Record: 624 passed

# 2. Pre-migration data validation
# Run validation query to find duplicate primary emails
# Use postgres-local MCP or direct psql connection

# 3. Create manual migration (NOT autogenerate)
alembic revision -m "phase_4_7_fix_global_primary_email_index_task4"

# 4. Edit migration file manually
# Open backend/migrations/versions/[timestamp]_phase_4_7_fix_global_primary_email_index_task4.py
# Add DROP INDEX IF EXISTS in upgrade()
# Add CREATE INDEX with LOWER(value) in upgrade()
# Add reverse operations in downgrade()

# 5. Apply migration
alembic upgrade head

# 6. Verify index changed
# Query pg_indexes to confirm index targets LOWER(value)

# 7. Create test suite
# Create backend/tests/test_phase_4_7_global_primary_email_index.py
# - Use db_session: Session parameter
# - Use select() with exec()
# - Test valid cases, duplicate rejection, case-insensitivity

# 8. Run new tests
pytest tests/test_phase_4_7_global_primary_email_index.py -v
# All new tests should pass

# 9. Regression check - Ensure no breaks
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Expected: 602 passed (597 + 5 new)

pytest tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Expected: 629 passed (624 + 5 new)

# 10. Rollback test - Verify downgrade works
alembic downgrade -1
alembic upgrade head
pytest tests/ -v  # Should still pass

# 11. Update docs
# Edit dev-docs/analysis/phase-4.7-db-schema-sync-3-plan.md
# Mark task as complete with test results
```

---

## Questions to Ask

**Before starting:**
1. Have I captured the 597/597 unit and 624/624 total baselines?
2. Have I run the validation query to check for existing duplicate primary emails?
3. Do I understand this is a MANUAL migration (not autogenerate)?
4. Do I understand no SQLModel changes are needed for this task?

**During implementation:**
1. Did I use DROP INDEX IF EXISTS (safe operation)?
2. Did I create the index with LOWER(value) not user_id?
3. Am I using `db_session` parameter (NOT `session`) in tests?
4. Am I using `select()/exec()` pattern (NOT `query()`) in tests?
5. Did I test case-insensitive uniqueness (lowercase vs uppercase)?

**After implementation:**
1. Do I have 100% test pass rate on BOTH unit tests (602) and total tests (629)?
2. Did baseline increase by exactly 5 tests (597+5=602, 624+5=629)?
3. Does the index definition target LOWER(value) when I query pg_indexes?
4. Have I updated the project plan document?
5. Have I tested migration rollback (`alembic downgrade -1`)?

---

**Ready to Begin!** 🚀

### MIGRATION Task Checklist (This Task):
1. ✅ Capture baseline (597/597 unit, 624/624 total)
2. 🔍 Validate existing data (check for duplicate primary emails)
3. 📝 Create manual migration (`alembic revision -m ...`)
4. ✏️ Write migration manually (DROP old index, CREATE new index with LOWER(value))
5. ✅ Apply migration (`alembic upgrade head`)
6. 🔍 Verify index definition (query pg_indexes)
7. 🧪 Create comprehensive tests (5 tests minimum)
8. 🔄 Run regression tests (602 unit, 629 total)
9. ↩️ Test rollback (`alembic downgrade -1`, then `upgrade head`)
10. 📚 Update project plan

Remember: Phase 4.7 is about **final production alignment** - this is a CRITICAL security fix for email authentication. Validate data thoroughly, test case-insensitivity, and maintain the zero-regression policy!
