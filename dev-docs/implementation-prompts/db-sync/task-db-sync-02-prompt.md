# Phase 4.5 Task Prompt: Task #2 - Citext Conversion for User Email

Task: Phase 1, Task #2 - Citext Conversion for User Email
Reference: dev-docs/analysis/phase-4.5-db-schema-sync-to-design-plan.md Task #2
(Analysis: Section 2 - Column & Data Type Mismatches in db-schema-dump-vs-design-analysis-v1.0.md)

## Context

We're building AevoFab AI, an AI-powered SaaS platform for electrical contractors with voice-controlled quoting and QuickBooks integration. We are now synchronizing our physical database schema with the Golden Master design (v2.6h JSON) to ensure 100% alignment.

## Completed So Far

**Phases 1-3: Core MVP Development (COMPLETE)**
- ✅ Phase 1-A: Critical Blockers (7 tasks) - Test endpoints, tenant isolation, idempotency
- ✅ Phase 1-B: Core Completeness (4 tasks) - Polymorphic relationships, quote acceptance
- ✅ Phase 2: Background Processing (4 tasks) - Celery, profitability rollup, notifications
- ✅ Phase 3: QuickBooks Integration (4 tasks) - OAuth, sync, conflicts, webhooks

**Phase 4: Enterprise Hardening (COMPLETE)**
- ✅ Task 20: Audit Event Logging (20 tests)
- ✅ Task 21: RBAC Permission System (40 tests)
- ✅ Task 22: Rate Limiting (13 tests)
- ✅ Task 23: Integration Test Suite (27 tests)

**Phase 4.5: Database Schema Synchronization (IN PROGRESS)**
- ✅ Gap 1: ContactPortalInvite UNIQUE constraint (March 30, 2026)
- ✅ Gap 2: User Endpoint Primary Email Guard function + triggers
- ✅ Gap 3: Componentized Tax Logic (3 functions, 6 triggers)
- ✅ Gap 4: NotificationDeliveryAttempt lifecycle fields
- ✅ Gap 5: QuoteAcceptance timezone compliance
- ✅ Gap 6: AuditEvent actor_type CHECK constraint
- ✅ **Task 1: Timezone Enforcement** (9 violations fixed, March 30, 2026)
- **Current Status:** 421/421 tests passing without integration (412 baseline + 9 new timezone tests)
- **Remaining Work:** 12 tasks across 4 phases

**Test Coverage:** 448/448 passing (100% pass rate) (includes: 421 non-integration tests, 27 integration tests)
**See:** dev-docs/analysis/phase-4.5-db-schema-sync-to-design-plan.md for full details

## Current Task

**Convert `User.email` from `character varying` to `citext` for case-insensitive uniqueness and lookups.**

The current implementation allows `user@example.com` and `USER@example.com` to be treated as different values, which can cause:
- Duplicate account creation
- Login failures due to case mismatch
- User confusion when case doesn't match registration

The Golden Master specifies `citext` type to ensure:
- `user@example.com` = `USER@example.com` = `User@Example.COM` (all equivalent)
- Case-insensitive UNIQUE constraint enforcement
- Case-insensitive email lookups (login works regardless of case)

**Priority:** HIGH  
**Estimated Effort:** 0.5 days  
**Task Spec:** See dev-docs/analysis/phase-4.5-db-schema-sync-to-design-plan.md Task #2 (lines 172-229)  
**Design Authority:** dev-docs/db-design/pilot-db-schema-v2.6h.json  
**Analysis Reference:** dev-docs/analysis/db-schema-vs-design/db-schema-dump-vs-design-analysis-v1.0.md Section 2

## Requirements

### 1. Documentation Standards
- **Active roadmap:** `dev-docs/analysis/phase-4.5-db-schema-sync-to-design-plan.md` - ⭐ PRIMARY for Phase 4.5
- **Always reference authoritative design docs:**
  - `dev-docs/db-design/pilot-db-schema-v2.6h.json` - **Golden Master** (source of truth)
  - `dev-docs/db-design/aevofab-db-process-v2.6h.md` - Database operations & schema
  - `dev-docs/analysis/db-schema-vs-design/db-schema-dump-vs-design-analysis-v1.0.md` - Gap analysis
  - `dev-docs/analysis/db-schema-vs-design/db-schema-sync-technical-instruction-v1.0.md` - Implementation guide
  - `dev-docs/architecture-design/mvp-arch.md` - System architecture
- **Create implementation notes** in roadmap as you work (inline documentation)
- **Update Phase 4.5 roadmap** when marking tasks complete

### 2. Testing Standards (CRITICAL FOR SCHEMA WORK)

**⚠️ ZERO FAILING TESTS POLICY:**
- **ALL tests MUST pass before marking task complete**
- **NO exceptions** - Database schema changes require 100% test pass rate
- If tests fail after implementation:
  1. **Fix immediately** (preferred for simple fixes)
  2. **Create detailed fix document** (for complex test issues)
     - Document ALL failing tests with concrete, actionable fixes
     - Mark task as "PARTIALLY COMPLETE" in roadmap
     - Include estimated time to fix each test

**Test Execution:**
- **Current Baseline:** (DO NOT regress these numbers)
  - 421/421 tests passing without integration tests (includes 9 new timezone tests from Task 1)
  - 448/448 tests passing with integration
- **Schema Sync Tests:** 30/30 passing (test_schema_sync_v2_6h.py, test_database_triggers.py)
- **Run existing tests first:**
  ```bash
  cd backend && source .venv/bin/activate
  pytest tests/ --ignore=tests/integration/ -v
  ```
- **Run schema sync tests:**
  ```bash
  pytest tests/test_schema_sync_v2_6h.py tests/test_database_triggers.py -v
  ```
- **All existing tests must pass** - Baseline must not regress
- **All new tests must pass** - No failing tests allowed

**Test Development for Schema Changes:**
- **BEFORE writing tests:** Review `backend/tests/conftest.py` for existing fixtures
- **Create or update test file:** `backend/tests/test_citext_email.py` (or add to existing test file)
- **Test coverage required for this task:**
  - Case-insensitive uniqueness: Attempt to insert `user@test.com` and `USER@test.com` → constraint violation
  - Case-insensitive lookups: Query for `USER@test.com` finds `user@test.com`
  - Email login scenario: User registers with `user@test.com`, logs in with `USER@test.com` → success
  - Pre-migration duplicate detection: Verify no existing case-insensitive duplicates
  - Data migration integrity: Verify existing emails preserved correctly

### 3. Code Standards
- **Follow existing patterns** - Check similar implementations first
- **Type hints required** - All functions/methods must have type hints
- **Error handling** - Database errors must be caught and logged
- **Docstrings required** - Document all functions/classes/triggers
- **No feature creep** - Strictly follow Golden Master v2.6h specification

### 4. Database Standards (CRITICAL FOR PHASE 4.5)

**Golden Master Compliance:**
- **DO NOT deviate from `pilot-db-schema-v2.6h.json`** - It is the source of truth
- **Always read SQLModel files first** - Don't hallucinate existing schema
- **Use Alembic migrations** for ALL schema changes
- **Test migrations both ways** - Upgrade AND downgrade must work cleanly
- **Naming conventions:**
  - Constraints: `[table]_[field]_[type]` (e.g., `user_email_key` for unique)
  - Indexes: `idx_[table]_[columns]` (already exists: `user_email` index)

**Migration Standards:**
- **Pre-migration data cleanup** - Convert all emails to lowercase BEFORE changing column type
- **Post-migration verification** - Verify citext type was applied successfully
- **Rollback testing** - Test downgrade migration before committing

**CITEXT Type Implementation:**
```python
# Python: Use str type hint (citext is database-level)
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import CITEXT

# SQLModel pattern for User.email
email: str = Field(
    sa_column=Column(CITEXT, nullable=False, index=True)
)
```

**Migration SQL Pattern:**
```sql
-- Step 1: Convert existing emails to lowercase (data cleanup)
UPDATE "user" SET email = LOWER(email);

-- Step 2: Detect case-insensitive duplicates (MUST BE ZERO)
-- (Add check query in migration validation)

-- Step 3: Change column type to citext
ALTER TABLE "user" 
  ALTER COLUMN email 
  TYPE citext 
  USING email::citext;
```

### 5. Workflow

1. **Read the Phase 4.5 roadmap** Task #2 section (lines 172-229)
2. **Review Golden Master JSON** for `user` table specification
3. **Check for existing duplicates:**
   ```sql
   SELECT LOWER(email), COUNT(*) 
   FROM "user" 
   GROUP BY LOWER(email) 
   HAVING COUNT(*) > 1;
   ```
   - If duplicates exist: Create cleanup plan (merge accounts or reject migration)
   - If no duplicates: Proceed with migration
4. **Update SQLModel file:** `backend/app/models/core.py` - User.email field
5. **Create Alembic migration:**
   ```bash
   cd backend
   source .venv/bin/activate
   alembic revision --autogenerate -m "convert_user_email_to_citext"
   ```
6. **Manually enhance migration:**
   - Add pre-migration lowercase conversion: `UPDATE "user" SET email = LOWER(email);`
   - Add duplicate detection check (raise error if duplicates found)
   - Verify autogenerated `ALTER COLUMN` statement is correct
7. **Test migration:**
   ```bash
   alembic upgrade head  # Apply
   alembic downgrade -1  # Rollback
   alembic upgrade head  # Re-apply
   ```
8. **Verify in database:**
   ```bash
   psql -d pilot_dev -c "\d \"user\"" | grep email
   # Should show: email | citext | not null
   ```
9. **Write tests** - Test case-insensitive uniqueness and lookups
10. **Run all tests** - Must pass before completion
11. **Update Phase 4.5 roadmap:**
    - Check off deliverables: `- [x] SQLModel Update`, `- [x] Alembic Migration`, `- [x] Test Coverage`
    - Add status: `**Status:** ✅ COMPLETE (2026-MM-DD)`
    - Add test results: `**Test Results:** X/X passing`
    - Add implementation summary (files modified, migration details, etc.)

## Key Files to Review

### Golden Master & Analysis
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - **Source of truth** (check `user` table spec)
- `dev-docs/analysis/phase-4.5-db-schema-sync-to-design-plan.md` - **Active roadmap** (Task #2, lines 172-229)
- `dev-docs/analysis/db-schema-vs-design/db-schema-dump-vs-design-analysis-v1.0.md` - Gap analysis Section 2

### Backend Code
- `backend/app/models/core.py` - **User model** (email field to modify)
- `backend/migrations/versions/` - Alembic migrations
- `backend/tests/conftest.py` - Test fixtures
- `backend/tests/test_schema_sync_v2_6h.py` - Schema sync test suite (may need updates)

### Related Work
- **Task 1 (completed):** `2026_03_30_2129-cf20e60ce5f3_fix_timezone_violations_task1.py` - Reference for migration pattern
- **Task 1 tests:** `backend/tests/test_timezone_compliance.py` - Reference for test pattern

## Success Criteria

**MUST COMPLETE ALL BEFORE MARKING TASK AS COMPLETE:**

- [ ] **SQLModel Update:**
  - [ ] File: `backend/app/models/core.py` modified
  - [ ] `User.email` field uses `Column(CITEXT, nullable=False, index=True)`
  - [ ] Type hint remains `str` (Python-level)

- [ ] **Pre-Migration Validation:**
  - [ ] Query detects any case-insensitive duplicate emails
  - [ ] If duplicates exist: Create cleanup plan or abort migration
  - [ ] If no duplicates: Proceed with confidence

- [ ] **Alembic Migration Created:**
  - [ ] Migration filename: `2026_03_XX_XXXX-*_convert_user_email_to_citext.py`
  - [ ] Migration includes `UPDATE "user" SET email = LOWER(email);`
  - [ ] Migration includes duplicate detection check
  - [ ] Migration includes `ALTER TABLE "user" ALTER COLUMN email TYPE citext USING email::citext;`
  - [ ] Downgrade migration reverts to `character varying`

- [ ] **Migration Testing:**
  - [ ] `alembic upgrade head` succeeds
  - [ ] Database shows `email` column as `citext` type
  - [ ] `alembic downgrade -1` succeeds (rollback works)
  - [ ] `alembic upgrade head` succeeds again (re-apply works)

- [ ] **Test Coverage:**
  - [ ] Test: Case-insensitive uniqueness enforced (duplicate rejected)
  - [ ] Test: Email lookup works regardless of case
  - [ ] Test: Login scenario (register lowercase, login uppercase)
  - [ ] Test: Existing data preserved after migration
  - [ ] **ALL existing tests pass** (421/421 baseline without integration maintained)
  - [ ] **ALL new tests pass** (zero failures)
  - [ ] **Test pass rate: 100%** (X/X passing, 0 failing)

- [ ] **Database Verification:**
  - [ ] `\d "user"` shows `email | citext | not null`
  - [ ] Case-insensitive uniqueness works: `INSERT ... VALUES ('USER@test.com')` after `'user@test.com'` → error
  - [ ] Case-insensitive lookup works: `SELECT * FROM "user" WHERE email = 'USER@test.com'` finds `'user@test.com'`

- [ ] **Phase 4.5 Roadmap Updated:**
  - [ ] Task #2 deliverables checked off
  - [ ] Status updated: `**Status:** ✅ COMPLETE (2026-MM-DD)`
  - [ ] Test results documented: `**Test Results:** X/X passing`
  - [ ] Implementation summary added with files modified and migration details

**Task Status in Roadmap:**
- ✅ **COMPLETE** - If all tests pass (implementation + tests 100% complete)
- 🟡 **PARTIALLY COMPLETE** - If fix document created for failing tests
  - Must include: "Implementation complete, tests require fixes (see task-db-sync-02-test-fixes.md)"
  - Cannot mark COMPLETE until all tests pass

**If Tests Fail:**
- Create `dev-docs/testing-support/task-db-sync-02-test-fixes.md` with concrete fixes
- Update task status to "🟡 PARTIALLY COMPLETE" in Phase 4.5 roadmap
- Document exact steps to achieve 100% test pass rate
- Include time estimates for each fix

## Deliverables (from Roadmap Task #2)

- [ ] **SQLModel Update:**
  - File: `backend/app/models/core.py`
  - Change `email` field to use `CITEXT` column type

- [ ] **Alembic Migration:**
  ```sql
  -- Convert existing email addresses to lowercase first
  UPDATE "user" SET email = LOWER(email);
  
  -- Change column type
  ALTER TABLE "user" 
    ALTER COLUMN email 
    TYPE citext 
    USING email::citext;
  ```

- [ ] **Test Coverage:**
  - Test case-insensitive uniqueness: `user@test.com` vs `USER@test.com` → constraint violation
  - Test email lookup: `session.exec(select(User).where(User.email == 'USER@test.com'))` finds `user@test.com`

## Questions to Ask

Before starting:
1. Have I read the Golden Master JSON for the `user` table `email` column specification?
2. Have I reviewed the gap analysis Section 2 to understand WHY this change is needed?
3. Do I understand the risk of case-insensitive duplicates in existing data?
4. Have I checked for existing duplicate emails (case-insensitive)?
5. What existing code can I reference for CITEXT column pattern?

During implementation:
1. Am I following the Golden Master specification exactly?
2. Have I converted existing emails to lowercase BEFORE changing column type?
3. Have I tested the migration in both directions (upgrade + downgrade)?
4. Are ALL tests passing (100% pass rate)?
5. Am I documenting as I go (inline in roadmap)?

After implementation:
1. Do I have 100% test pass rate (X/X passing, 0 failing)?
2. Can I demonstrate case-insensitive uniqueness enforcement?
3. Can I demonstrate case-insensitive email lookups work correctly?
4. Have I verified the database column type is `citext`?
5. Does the migration rollback cleanly without errors?

## Example Task Flow

```bash
# ============================================================================
# Phase 4.5 Task #2 Execution: Citext Conversion for User Email
# ============================================================================

# 1. Review the task in Phase 4.5 roadmap
cat dev-docs/analysis/phase-4.5-db-schema-sync-to-design-plan.md | grep -A 60 "Task 2:"

# 2. Review Golden Master specification for user table
cat dev-docs/db-design/pilot-db-schema-v2.6h.json | jq '.tables[] | select(.name == "user") | .columns[] | select(.name == "email")'

# 3. Check current User model
cd backend
source .venv/bin/activate
cat app/models/core.py | grep -A 5 "class User"

# 4. Check for existing case-insensitive duplicates
psql -d pilot_dev -c "SELECT LOWER(email), COUNT(*) FROM \"user\" GROUP BY LOWER(email) HAVING COUNT(*) > 1;"
# Expected: 0 rows (no duplicates)

# 5. Update SQLModel file
# [Edit backend/app/models/core.py]
# Change: email: str = Field(nullable=False, index=True)
# To: email: str = Field(sa_column=Column(CITEXT, nullable=False, index=True))
# Add import: from sqlalchemy.dialects.postgresql import CITEXT

# 6. Create migration
alembic revision --autogenerate -m "convert_user_email_to_citext"

# 7. Enhance migration file manually
# [Edit migration file to add:]
# - Pre-migration: op.execute("UPDATE \"user\" SET email = LOWER(email);")
# - Duplicate check query (optional, but recommended)

# 8. Test migration upgrade
alembic upgrade head

# 9. Verify schema change
psql -d pilot_dev -c "\d \"user\"" | grep email
# Should show: email | citext | not null

# 10. Test case-insensitive behavior
psql -d pilot_dev -c "INSERT INTO \"user\" (id, email, ...) VALUES (uuid_generate_v4(), 'test@example.com', ...);"
psql -d pilot_dev -c "INSERT INTO \"user\" (id, email, ...) VALUES (uuid_generate_v4(), 'TEST@example.com', ...);"
# Should fail with unique constraint violation

# 11. Test migration downgrade
alembic downgrade -1

# 12. Verify rollback
psql -d pilot_dev -c "\d \"user\"" | grep email
# Should show: email | character varying | not null

# 13. Re-apply migration
alembic upgrade head

# 14. Run baseline tests
pytest tests/ --ignore=tests/integration/ -v 2>&1 | tail -10
# Expected: 421/421 passing (no regressions)

# 15. Write new tests for citext behavior
# [Create or update test file with case-insensitive tests]

# 16. Run all tests without integration
pytest tests/ --ignore=tests/integration/ -v
# Expected: 421 + new tests passing

# 17. Run all tests with integration
pytest tests/ -v
# Expected: 448 + new tests passing

# 18. Update Phase 4.5 roadmap
# [Edit phase-4.5-db-schema-sync-to-design-plan.md Task #2 section]
# - [x] SQLModel Update
# - [x] Alembic Migration
# - [x] Test Coverage
# **Status:** ✅ COMPLETE (2026-MM-DD)
# **Test Results:** X/X passing without integration, Y/Y with integration
# **Implementation Summary:**
# - Modified: backend/app/models/core.py (User.email field)
# - Migration: 2026_03_XX_XXXX-*_convert_user_email_to_citext.py
# - Tests: X new tests added (case-insensitive uniqueness and lookups)
```

## Notes

- **Golden Master is Law:** `pilot-db-schema-v2.6h.json` is the single source of truth
- **CITEXT Extension:** PostgreSQL citext extension may need to be enabled (check if already enabled)
- **Data Safety:** MUST check for case-insensitive duplicates before migration
- **Backward Compatibility:** citext is backward compatible with varchar (safe conversion)
- **Performance:** citext has negligible performance impact for typical usage
- **Test Scenarios:** Focus on case-insensitive uniqueness and lookups (critical for login)
- **Migration Rollback:** MUST test downgrade migration (production safety)
- **No Feature Creep:** Only implement what Golden Master specifies (citext for email)
- **User Experience:** This fixes the "can't login with uppercase email" bug

## Risk Assessment (from Roadmap)

- **Data Corruption Risk:** LOW (citext is backward compatible with varchar)
- **Duplicate Detection:** CRITICAL - Must check for existing case-insensitive duplicates before migration
  - If duplicates exist: Abort migration and create cleanup plan
  - If no duplicates: Safe to proceed

## Related Schema Work

**Phase 1 Completed:**
- ✅ Task 1: Timezone Enforcement (9 columns fixed)

**Phase 1 Remaining:**
- 🔴 Task 2: Citext Conversion (THIS TASK)
- ✅ Task 3: QuickBooks Identity Rule (already complete)

**Next Up After Task 2:**
- Phase 2: Functions & Triggers (4 tasks)

---

## Usage

1. Start this task with the `MVP Builder` custom Roo Code mode
2. Copy this entire prompt to begin
3. The AI will have full context from the Golden Master v2.6h and Phase 4.5 roadmap
4. When finished, the AI will update the Phase 4.5 roadmap with completion status
5. All deliverables and success criteria must be met before marking complete
