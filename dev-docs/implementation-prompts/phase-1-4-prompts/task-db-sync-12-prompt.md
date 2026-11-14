# Task 12: Partial Unique Indexes (Email Endpoint Logic)

**Reference:** `dev-docs/analysis/phase-4.5-db-schema-sync-to-design-plan.md` - Task 12
**Authority:** `dev-docs/db-design/pilot-db-schema-v2.6h.json`
**Type:** Phase 4 - Advanced Indexing & Temporal Logic
**Priority:** MEDIUM

---

## Context

We're building AevoFab AI, an AI-powered SaaS platform for electrical contractors with voice-controlled quoting and QuickBooks integration. Following the 80/20 rule to reach MVP quickly.

This is a **Phase 4 Advanced Indexing task** to achieve 100% alignment between our SQLModel implementations and the Golden Master Database Schema (v2.6h JSON). This is NOT a new feature - it's surgical corrections to ensure database-level data integrity and business rule enforcement.

---

## Completed So Far

**Phase 1: Foundation (COMPLETE - March 30-31, 2026):**
- ✅ Task 1: Timezone enforcement (9 columns fixed)
- ✅ Task 2: Citext conversion for user email
- ✅ Task 3: QuickBooks identity rules on Customer table

**Phase 2: Functions & Triggers (COMPLETE - March 31, 2026):**
- ✅ Task 4: Missing PL/pgSQL functions (3 functions + 200 triggers)
- ✅ Task 5: Function naming standard compliance
- ✅ Task 6: Audit trigger coverage (85 audit triggers)
- ✅ Task 7: Operational trigger verification (293 total triggers)

**Phase 3: Data Integrity (COMPLETE - April 1, 2026):**
- ✅ Task 8: Missing unique constraints (4/4 complete)
- ✅ Task 9: Missing check constraints (9/9 complete)
- ✅ Task 10: Missing temporal exclusion constraints (6/6 complete)

**Phase 4: Advanced Indexing (PARTIAL):**
- ✅ Task 11: Partial indexes (2/2 complete - invoice balance, unbilled expenses)
- 📋 Task 12: Partial unique indexes (NOT STARTED - this task)

**Current Test Baseline:** 543 tests passing (100%)
**See:** `dev-docs/analysis/phase-4.5-db-schema-sync-to-design-plan.md` for full context

---

## Current Task: Partial Unique Indexes (Email Endpoint Logic)

**Effort:** 0.5 days
**Gap Reference:** Analysis Section 4 - Missing Indexes (Partial Unique)

The `user_endpoint` table requires two complex partial unique indexes to enforce business rules around primary contact endpoints. These indexes ensure data integrity at the database level for the "Highlander rule" (there can be only one primary endpoint).

### What Needs to Be Fixed

| # | Entity/Component | Issue | Impact | Complexity |
|---|------------------|-------|--------|------------|
| **1** | `user_endpoint` | Missing `ux_user_email_primary` index | User can have multiple primary emails (data integrity violation) | MEDIUM |
| **2** | `user_endpoint` | Missing `ux_global_primary_email` index | User can have primary email AND primary phone simultaneously (business rule violation) | MEDIUM |

---

## ⚠️ BEFORE YOU START - Establish Regression Baseline

**CRITICAL:** You MUST capture the current test baseline BEFORE making ANY changes. This ensures we can detect regressions.

### Step 1: Activate Virtual Environment

All Python and pytest commands MUST be run in the virtual environment:

```bash
cd backend
source .venv/bin/activate
```

### Step 2: Run Regression Tests (Non-Integration)

```bash
# Run all tests EXCEPT integration tests
pytest --ignore=tests/integration/ tests/ -v

# Concise output to capture baseline count
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed|===)" | tail -5
```

**Record the output:** `543 tests passing` (baseline from Task 11)

Example output:
```
========================== 543 passed in 45.23s ==========================
```

### Step 3: Run ALL Tests (Including Integration)

```bash
# Run ALL tests
pytest tests/ -v

# Concise output
pytest tests/ -v 2>&1 | grep -E "(passed|failed|===)" | tail -5
```

**Record the output:** `[BASELINE_TOTAL_COUNT] tests passing`

Example output:
```
========================== 570 passed in 62.11s ==========================
```

### Step 4: Document Your Baseline

**Write down these numbers before proceeding:**
- Non-Integration Baseline: `543/543` passing
- Total Tests Baseline: `___/___` passing

**These are your regression checkpoints. All these tests MUST still pass after your work.**

---

## Requirements

### 1. Implementation Details

#### Gap 1: `ux_user_email_primary` - One Primary Email Per User

**Problem:** The `user_endpoint` table currently allows multiple email endpoints to be marked as `is_primary = true` for the same user. This violates the Highlander rule established in Gap 2 (March 30, 2026) via the `guard_user_endpoint_primary_email_fn()` trigger.

**Current State:**
```python
# backend/app/models/core.py
class UserEndpoint(SQLModel, table=True):
    __tablename__ = "user_endpoint"
    # No partial unique index enforcing single primary email
```

**Business Rule:**
- User can have multiple email endpoints (work@company.com, personal@gmail.com)
- But only ONE email can be marked `is_primary = true`
- Attempting to set a second email as primary → **UNIQUE VIOLATION**

**Migration SQL:**
```sql
-- Enforce: Only one primary email per user
CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS ux_user_email_primary 
ON user_endpoint (user_id) 
WHERE channel = 'email' AND is_primary = true;
```

**Why CONCURRENTLY:** Prevents table lock during index creation (production-safe, online operation)

**What This Enforces:**
- Multiple non-primary emails allowed: `is_primary = false` ✅
- Only one primary email: `is_primary = true` ✅ (enforced by index)
- Violates constraint if two emails marked primary ❌ (IntegrityError raised)

---

#### Gap 2: `ux_global_primary_email` - One Global Primary Per User

**Problem:** The `user_endpoint` table currently allows a user to have BOTH a primary email AND a primary phone number simultaneously. The Golden Master requires only ONE endpoint of ANY type to be primary at a time.

**Business Rule:**
- User can have multiple endpoints (email, phone, sms)
- But only ONE endpoint across ALL types can be marked `is_primary = true`
- If email is primary, phone cannot be primary
- If phone is primary, email cannot be primary

**Migration SQL:**
```sql
-- Enforce: Only one primary endpoint of ANY type per user
CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS ux_global_primary_email 
ON user_endpoint (user_id) 
WHERE is_primary = true;
```

**What This Enforces:**
- User has primary email (work@company.com) + non-primary phone ✅
- User has primary phone + non-primary email ✅
- User has primary email + primary phone ❌ (UNIQUE VIOLATION)

---

### 2. Database Query Tools

**You have access to the postgres-local MCP server for direct database queries:**

```python
# Example: Check for users with multiple primary endpoints
await mcp__postgres_local__query({
    "sql": """
        SELECT user_id, COUNT(*) as primary_count
        FROM user_endpoint
        WHERE is_primary = true
        GROUP BY user_id
        HAVING COUNT(*) > 1
    """
})

# Example: Check for users with multiple primary emails
await mcp__postgres_local__query({
    "sql": """
        SELECT user_id, COUNT(*) as primary_email_count
        FROM user_endpoint
        WHERE channel = 'email' AND is_primary = true
        GROUP BY user_id
        HAVING COUNT(*) > 1
    """
})

# Example: Verify indexes exist after migration
await mcp__postgres_local__query({
    "sql": """
        SELECT 
            indexname,
            indexdef
        FROM pg_indexes
        WHERE indexname IN ('ux_user_email_primary', 'ux_global_primary_email')
        ORDER BY indexname
    """
})
```

Use this tool to:
- Validate data before applying indexes
- Verify indexes exist after migration
- Debug constraint violations
- Confirm test data state

---

### 3. Implementation Order

Execute in this exact sequence:

1. **✅ Establish Regression Baseline** (see "Before You Start" section above)

2. **Pre-Migration Data Validation**
   - Check for users with multiple primary emails
   - Check for users with multiple primary endpoints (across all channels)
   - Clean up any violations found (set one to `is_primary = false`)
   - Document any data cleanup performed

3. **Create Alembic Migration (Manual)**
   ```bash
   cd backend
   source .venv/bin/activate
   alembic revision -m "add_partial_unique_indexes_user_endpoint_task12"
   ```
   
   **Note:** Use manual migration (not autogenerate) because SQLModel doesn't support partial unique indexes in `__table_args__`

4. **Implement Migration**
   - Edit the generated migration file
   - Add both `CREATE UNIQUE INDEX CONCURRENTLY` statements
   - Add corresponding `DROP INDEX CONCURRENTLY` in downgrade
   - Use AUTOCOMMIT isolation level for CONCURRENTLY operations

5. **Apply Migration**
   ```bash
   alembic upgrade head
   ```

6. **Verify Indexes in Database**
   - Use MCP server to query `pg_indexes`
   - Confirm both indexes exist with correct WHERE clauses

7. **Create Test Suite**
   - Create `backend/tests/test_partial_unique_indexes_task12.py`
   - Write comprehensive tests (see Test Requirements below)
   - **CRITICAL:** Use `session.add()` and `session.commit()` with proper exception handling

8. **Run New Tests**
   ```bash
   pytest tests/test_partial_unique_indexes_task12.py -v
   ```

9. **Run Regression Tests** (see "After You Complete" section below)

10. **Update Documentation** (see Documentation Update section below)

---

### 4. Test Requirements

**⚠️ ZERO FAILING TESTS POLICY:**
- **ALL 543 existing tests MUST still pass** (baseline cannot regress)
- **ALL new tests MUST pass** (schema sync verification)
- **Target: 551/551 passing (100%)** (543 baseline + 8 new tests)

**Test File:** `backend/tests/test_partial_unique_indexes_task12.py`

**Test Standards:**

```python
"""
Test Suite: Phase 4 Task 12 - Partial Unique Indexes (Email Endpoint Logic)
Tests partial unique indexes on user_endpoint from Golden Master v2.6h
"""
import pytest
from sqlmodel import Session
from sqlalchemy.exc import IntegrityError

from app.models.core import UserEndpoint

class TestUserEmailPrimaryIndex:
    """Test ux_user_email_primary: Only one primary email per user"""
    
    def test_multiple_non_primary_emails_allowed(self, session: Session, test_user):
        """User can have multiple non-primary emails"""
        email1 = UserEndpoint(
            user_id=test_user.id,
            channel="email",
            value="work@company.com",
            is_primary=False,
            is_verified=True
        )
        email2 = UserEndpoint(
            user_id=test_user.id,
            channel="email",
            value="personal@gmail.com",
            is_primary=False,
            is_verified=False
        )
        session.add(email1)
        session.add(email2)
        session.commit()
        
        # Should succeed - both are non-primary
        assert email1.id is not None
        assert email2.id is not None
    
    def test_one_primary_email_allowed(self, session: Session, test_user):
        """User can have one primary email"""
        email = UserEndpoint(
            user_id=test_user.id,
            channel="email",
            value="primary@company.com",
            is_primary=True,
            is_verified=True
        )
        session.add(email)
        session.commit()
        
        # Should succeed
        assert email.id is not None
    
    def test_two_primary_emails_rejected(self, session: Session, test_user):
        """User cannot have two primary emails"""
        email1 = UserEndpoint(
            user_id=test_user.id,
            channel="email",
            value="first@company.com",
            is_primary=True,
            is_verified=True
        )
        session.add(email1)
        session.commit()
        
        email2 = UserEndpoint(
            user_id=test_user.id,
            channel="email",
            value="second@company.com",
            is_primary=True,
            is_verified=False
        )
        session.add(email2)
        
        with pytest.raises(IntegrityError) as exc_info:
            session.commit()
        assert "ux_user_email_primary" in str(exc_info.value)

class TestGlobalPrimaryIndex:
    """Test ux_global_primary_email: Only one primary endpoint of ANY type per user"""
    
    def test_primary_email_and_non_primary_phone_allowed(self, session: Session, test_user):
        """User can have primary email and non-primary phone"""
        email = UserEndpoint(
            user_id=test_user.id,
            channel="email",
            value="user@company.com",
            is_primary=True,
            is_verified=True
        )
        phone = UserEndpoint(
            user_id=test_user.id,
            channel="phone",
            value="+15551234567",
            is_primary=False,
            is_verified=True
        )
        session.add(email)
        session.add(phone)
        session.commit()
        
        # Should succeed - only one primary
        assert email.id is not None
        assert phone.id is not None
    
    def test_primary_phone_and_non_primary_email_allowed(self, session: Session, test_user):
        """User can have primary phone and non-primary email"""
        phone = UserEndpoint(
            user_id=test_user.id,
            channel="phone",
            value="+15551234567",
            is_primary=True,
            is_verified=True
        )
        email = UserEndpoint(
            user_id=test_user.id,
            channel="email",
            value="user@company.com",
            is_primary=False,
            is_verified=True
        )
        session.add(phone)
        session.add(email)
        session.commit()
        
        # Should succeed - only one primary
        assert phone.id is not None
        assert email.id is not None
    
    def test_primary_email_and_primary_phone_rejected(self, session: Session, test_user):
        """User cannot have both primary email and primary phone"""
        email = UserEndpoint(
            user_id=test_user.id,
            channel="email",
            value="user@company.com",
            is_primary=True,
            is_verified=True
        )
        session.add(email)
        session.commit()
        
        phone = UserEndpoint(
            user_id=test_user.id,
            channel="phone",
            value="+15551234567",
            is_primary=True,
            is_verified=True
        )
        session.add(phone)
        
        with pytest.raises(IntegrityError) as exc_info:
            session.commit()
        assert "ux_global_primary_email" in str(exc_info.value)
```

**Required Test Coverage (Minimum 8 Tests):**
- [ ] Multiple non-primary emails allowed (ux_user_email_primary)
- [ ] One primary email allowed (ux_user_email_primary)
- [ ] Two primary emails rejected (ux_user_email_primary)
- [ ] Primary email + non-primary phone allowed (ux_global_primary_email)
- [ ] Primary phone + non-primary email allowed (ux_global_primary_email)
- [ ] Primary email + primary phone rejected (ux_global_primary_email)
- [ ] Different users can have their own primary emails (tenant isolation)
- [ ] Index existence verification (database query)

**Test Fixtures:**
Review `backend/tests/conftest.py` for available fixtures:
- `session` - Database session with auto-rollback
- `test_user` - Test user record
- Add new fixtures if needed following existing patterns

---

### 5. Database Verification

**After Migration Applied:**

Use the MCP server or psql to verify indexes:

```sql
-- Verify indexes exist
SELECT 
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename = 'user_endpoint'
  AND indexname IN ('ux_user_email_primary', 'ux_global_primary_email')
ORDER BY indexname;

-- Expected output:
-- ux_global_primary_email | CREATE UNIQUE INDEX ux_global_primary_email ON public.user_endpoint USING btree (user_id) WHERE (is_primary = true)
-- ux_user_email_primary | CREATE UNIQUE INDEX ux_user_email_primary ON public.user_endpoint USING btree (user_id) WHERE ((channel = 'email'::text) AND (is_primary = true))

-- Verify index sizes are reasonable
SELECT 
    indexname,
    pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
FROM pg_stat_user_indexes
WHERE indexname IN ('ux_user_email_primary', 'ux_global_primary_email')
ORDER BY indexname;
```

---

## 🎯 AFTER YOU COMPLETE - Verify No Regressions

**CRITICAL:** After all implementation and new tests pass, you MUST verify the regression baseline.

### Step 1: Activate Virtual Environment

```bash
cd backend
source .venv/bin/activate
```

### Step 2: Run Non-Integration Tests

```bash
# Run all tests EXCEPT integration tests
pytest --ignore=tests/integration/ tests/ -v

# Concise output
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed|===)" | tail -5
```

**Expected:** `551 passed` (543 baseline + 8 new tests)

### Step 3: Run ALL Tests (Including Integration)

```bash
# Run ALL tests
pytest tests/ -v

# Concise output
pytest tests/ -v 2>&1 | grep -E "(passed|failed|===)" | tail -5
```

**Expected:** `[BASELINE_TOTAL + 8] passed`

### Step 4: Verify 100% Pass Rate

**If ANY tests fail:**
1. Identify which tests are failing
2. Determine if they are:
   - New tests you wrote (fix them)
   - Existing tests that regressed (CRITICAL - fix immediately)
3. Fix ALL failing tests before proceeding
4. Re-run regression tests until 100% pass rate

**Regression Analysis:**
- New tests failing → Fix your test code
- Existing tests failing → Your changes broke something - ROLLBACK and fix
- Cannot achieve 100% → Create fix document (see Zero Tolerance Policy below)

---

## Documentation Update

### Update Project Plan Document

**File to Update:** `dev-docs/analysis/phase-4.5-db-schema-sync-to-design-plan.md`

Find Task 12 section (lines 1422-1481) and update with:

```markdown
### Task 12: Partial Unique Indexes (Email Endpoint Logic)

**Status:** ✅ COMPLETE (2026-04-01)
**Effort:** 0.5 days (actual)
**Priority:** MEDIUM
**Gap Reference:** Analysis Section 4 - Missing Indexes (Partial Unique)

**Completed 2 partial unique indexes:**
- ✅ `ux_user_email_primary` - Only one primary email per user
- ✅ `ux_global_primary_email` - Only one primary endpoint (any type) per user

**Implementation Summary:**

#### 1. `ux_user_email_primary` - Primary Email Uniqueness
- **Index:** `CREATE UNIQUE INDEX ux_user_email_primary ON user_endpoint (user_id) WHERE channel = 'email' AND is_primary = true`
- **Purpose:** Prevent multiple primary emails for same user
- **Test:** `test_two_primary_emails_rejected` ✅ PASSING

#### 2. `ux_global_primary_email` - Global Primary Uniqueness
- **Index:** `CREATE UNIQUE INDEX ux_global_primary_email ON user_endpoint (user_id) WHERE is_primary = true`
- **Purpose:** Prevent primary email + primary phone simultaneously
- **Test:** `test_primary_email_and_primary_phone_rejected` ✅ PASSING

**Migration:** `2026_04_01_HHMM-[hash]_add_partial_unique_indexes_user_endpoint_task12.py`
**Test Suite:** `test_partial_unique_indexes_task12.py` - 8 tests
**Final Test Results:** 551/551 tests passing (100%)

**Database Verification:**
- Both partial unique indexes confirmed active ✅
- Pre-migration validation: 0 violations found ✅
- Migration upgrade/downgrade tested successfully ✅

**Test Coverage Breakdown:**
- New tests added: 8
- Baseline maintained: 543
- Total passing: 551/551 (100%)
- Test categories: Email uniqueness (3), Global uniqueness (3), Tenant isolation (1), Index existence (1)

**Key Implementation Notes:**
- Used `CREATE INDEX CONCURRENTLY` for production-safe deployment
- Manual migration required (SQLModel doesn't support partial unique indexes in __table_args__)
- Indexes work in conjunction with existing `guard_user_endpoint_primary_email_fn()` trigger
- No redundancy - trigger provides runtime validation, indexes provide database-level enforcement
```

---

## Success Criteria

**MUST COMPLETE ALL BEFORE MARKING TASK AS DONE:**

- [ ] **Regression baseline captured** (non-integration: 543/543, total: ___/___ recorded)
- [ ] **Pre-migration data validation completed** (no existing violations)
- [ ] **Alembic migration created manually** (not autogenerate)
- [ ] **Migration uses CONCURRENTLY** for production safety
- [ ] **Migration applied successfully** (`alembic upgrade head` completes without errors)
- [ ] **Both indexes verified in database** (pg_indexes query confirms)
- [ ] **All 8 new tests written and passing**
- [ ] **ALL existing tests still passing** - Zero regression
- [ ] **Non-integration tests:** 551/551 passing (543 + 8)
- [ ] **Total tests:** [baseline + 8]/[baseline + 8] passing
- [ ] **100% test pass rate** - No failing tests
- [ ] **Database verification query** confirms both indexes active
- [ ] **Migration rollback tested** (`alembic downgrade -1` then `upgrade head` works)
- [ ] **Project plan document updated** with implementation summary

**Zero Tolerance Policy:**
- **Any failing test = INCOMPLETE**
- **Test pass rate MUST be 100%**
- **Regression baseline MUST be maintained or exceeded**
- If tests fail after 10+ attempts, create detailed fix document but mark task incomplete

---

## Key Files to Review

### Architecture & Design
- `dev-docs/analysis/phase-4.5-db-schema-sync-to-design-plan.md` - **Task 12 Details (lines 1422-1481)** ⭐
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - **GOLDEN MASTER**
- `dev-docs/db-design/aevofab-db-process-v2.6h.md` - Database operations

### Backend Code (Related Context)
- `backend/app/models/core.py` - UserEndpoint model (lines 117+)
- `backend/migrations/versions/2026_03_31_1954-0a26d3a349c2_rename_user_endpoint_guard_function.py` - Related trigger function

### Migration (To Create)
- `backend/migrations/versions/2026_04_01_HHMM-*_add_partial_unique_indexes_user_endpoint_task12.py`

### Tests (To Create)
- `backend/tests/test_partial_unique_indexes_task12.py` - 8 tests minimum

### Reference (Similar Task)
- `backend/tests/test_partial_indexes_task11.py` - Task 11 test patterns

---

## Risk Assessment

**Data Validation Risk:** LOW
- Pre-migration query will detect any existing violations
- Trigger function already prevents violations at runtime
- **Mitigation:** Clean up any violations before applying indexes

**Performance Impact:** LOW
- Partial unique indexes are very small (only primary endpoints)
- CONCURRENTLY prevents table locks during creation
- **Measurement:** Query pg_stat_user_indexes for index size

**Rollback Complexity:** LOW
- `DROP INDEX CONCURRENTLY` is straightforward
- No data changes, only index removal
- **Testing:** Downgrade/upgrade cycle in test environment

---

## Notes

- **Virtual Environment Required:** All Python/pytest commands use `source .venv/bin/activate`
- **MCP Server Available:** Use `postgres-local` MCP server for direct database queries
- **Manual Migration:** SQLModel doesn't support partial unique indexes, use manual migration
- **CONCURRENTLY Required:** Use `CREATE/DROP INDEX CONCURRENTLY` for production safety
- **Regression Testing:** Capture baseline BEFORE, verify AFTER - both non-integration and total
- **Golden Master Authority:** The JSON schema is the single source of truth
- **Zero Regression Policy:** All existing tests MUST still pass after changes
- **Trigger Relationship:** These indexes complement the existing `guard_user_endpoint_primary_email_fn()` trigger
- **Cost Impact:** Negligible - small partial indexes have minimal storage/performance cost
- **Production Safe:** CONCURRENTLY operations allow online index creation

**Important Patterns:**
- Use AUTOCOMMIT isolation level for CONCURRENTLY operations in migration
- Both indexes use `WHERE` clauses to create partial unique indexes
- `ux_user_email_primary`: Scoped to email channel only
- `ux_global_primary_email`: Scoped across ALL channels

**Relationship to Existing Code:**
- Task 5 (Phase 2): Created `guard_user_endpoint_primary_email_fn()` trigger
- Trigger provides runtime validation (raises exception)
- These indexes provide database-level enforcement (cannot be bypassed)
- No redundancy - both serve complementary purposes

**If you get stuck:**
- Check Task 11 migration for CONCURRENTLY pattern
- Review Golden Master JSON for exact index specifications
- Use MCP server to query existing pg_indexes for examples
- Verify virtual environment is activated for all commands

---

## Example Task Flow

```bash
# ============================================
# PHASE 1: ESTABLISH BASELINE
# ============================================

# 1. Activate virtual environment
cd backend
source .venv/bin/activate

# 2. Capture non-integration baseline
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Expected: 543 passed

# 3. Capture total baseline
pytest tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Record: ___ passed

# ============================================
# PHASE 2: VALIDATE DATA
# ============================================

# 4. Check for users with multiple primary emails
# [Use MCP server query]

# 5. Check for users with multiple primary endpoints
# [Use MCP server query]

# 6. Clean up any violations found
# [Document cleanup if performed]

# ============================================
# PHASE 3: IMPLEMENT CHANGES
# ============================================

# 7. Create manual migration
alembic revision -m "add_partial_unique_indexes_user_endpoint_task12"

# 8. Edit migration file
# Add CREATE UNIQUE INDEX CONCURRENTLY statements
# Use AUTOCOMMIT isolation level
# Add DROP INDEX CONCURRENTLY in downgrade

# 9. Review migration
cat backend/migrations/versions/2026_04_01_*_add_partial_unique_indexes*.py

# 10. Apply migration
alembic upgrade head

# ============================================
# PHASE 4: VERIFY DATABASE
# ============================================

# 11. Verify indexes in database (using MCP server)
# Query pg_indexes to confirm both indexes exist

# 12. Check index sizes (should be very small)
# Query pg_stat_user_indexes

# ============================================
# PHASE 5: TEST
# ============================================

# 13. Create test file
# backend/tests/test_partial_unique_indexes_task12.py
# 8 tests covering both indexes

# 14. Run new tests only
pytest tests/test_partial_unique_indexes_task12.py -v
# Expected: 8 passed

# ============================================
# PHASE 6: REGRESSION VERIFICATION
# ============================================

# 15. Run non-integration regression tests
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Expected: 551 passed (543 + 8)

# 16. Run ALL tests (full regression)
pytest tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Expected: [baseline + 8] passed

# 17. Verify 100% pass rate
# If any failures → FIX IMMEDIATELY

# ============================================
# PHASE 7: ROLLBACK TEST
# ============================================

# 18. Test migration reversibility
alembic downgrade -1
alembic upgrade head
pytest tests/test_partial_unique_indexes_task12.py -v
# Expected: Still 8 passed

# ============================================
# PHASE 8: DOCUMENTATION
# ============================================

# 19. Update project plan document
# Edit phase-4.5-db-schema-sync-to-design-plan.md
# Update Task 12 section with completion details
```

---

## Questions to Ask

**Before starting:**
1. Have I reviewed the Golden Master JSON for the exact index specifications?
2. Have I captured the regression baseline (543 non-integration, ___ total)?
3. Have I activated the virtual environment?
4. Do I understand the difference between the two indexes?

**During implementation:**
1. Am I using `CREATE INDEX CONCURRENTLY` for production safety?
2. Have I set AUTOCOMMIT isolation level in the migration?
3. Have I validated no existing data violates the uniqueness constraints?
4. Are my tests using proper IntegrityError handling?

**After implementation:**
1. Did I run BOTH non-integration and total regression tests?
2. Do I have 100% test pass rate (no failures)?
3. Did the test count increase by exactly 8?
4. Have I updated the project plan document?
5. Can the migration be rolled back cleanly with CONCURRENTLY?

---

**Ready to Begin!** 🚀

1. ✅ Capture regression baseline (non-integration: 543, total: ___)
2. 🔍 Validate existing data for violations
3. 🛠️ Create manual migration with CONCURRENTLY indexes
4. ✅ Apply migration and verify in database
5. 📝 Create 8 comprehensive tests
6. 🔄 Run regression tests (expect 551/551 non-integration)
7. 📚 Update project plan document

Remember: Virtual environment required, use postgres-local MCP server, CONCURRENTLY for production safety, maintain 100% pass rate!
