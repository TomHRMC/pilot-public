# Phase 4.5 Task Prompt
## Task: Phase 2, Task #5 - Function Naming Standard Compliance

```
Task: Phase 2, Task #5 - Function Naming Standard Compliance
Reference: dev-docs/analysis/phase-4.5-db-schema-sync-to-design-plan.md Task #5
(Analysis: Section 1 - Function Naming Standard in db-schema-dump-vs-design-analysis-v1.0.md)

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
- ✅ Phase 1, Task 1: Timezone Enforcement (9 violations fixed)
- ✅ Phase 1, Task 2: Citext Conversion for User Email
- ✅ Phase 1, Task 3: QuickBooks Identity Rule (Customer Table)
- ✅ Phase 2, Task 4: Missing PL/pgSQL Functions (3 functions + 200 triggers)
- **Current Status:** 444/444 tests passing without integration tests, 471/471 total (100%)
- **Remaining Work:** 9 tasks across Phases 2-4

**Test Coverage:** 444/444 passing (100% pass rate) without integration tests; 471/471 with integration tests
**See:** dev-docs/analysis/phase-4.5-db-schema-sync-to-design-plan.md for full details

## Current Task

**Phase 2, Task 5: Function Naming Standard Compliance**

Ensure all trigger functions follow the Golden Master naming standard by renaming `guard_user_endpoint_primary_email()` to `guard_user_endpoint_primary_email_fn()`.

**The Problem:**
The function `guard_user_endpoint_primary_email()` was created on March 30, 2026 (Gap 2), but doesn't follow the Golden Master standard that requires all trigger functions to end with `_fn` suffix.

**Priority:** LOW (cosmetic, but required by design standard)  
**Estimated Effort:** 0.5 days  
**Task Spec:** See dev-docs/analysis/phase-4.5-db-schema-sync-to-design-plan.md Task #5  
**Design Authority:** dev-docs/db-design/pilot-db-schema-v2.6h.json  
**Analysis Reference:** dev-docs/analysis/db-schema-vs-design/db-schema-dump-vs-design-analysis-v1.0.md Section 1

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
  - 444/444 tests passing without integration tests
  - 471/471 tests passing with integration
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
- **For this task:** Verify existing trigger tests still pass after rename
- **Test coverage required:**
  - Verify function exists with new name
  - Verify triggers reference correct function name
  - Verify Highlander rule still enforced (only one primary email per user)
  - Verify existing functionality unchanged

### 3. Code Standards
- **Follow existing patterns** - Check similar implementations first
- **Type hints required** - All functions/methods must have type hints
- **Error handling** - Database errors must be caught and logged
- **Docstrings required** - Document all functions/classes/triggers
- **No feature creep** - Strictly follow Golden Master v2.6h specification

### 4. Database Standards (CRITICAL FOR PHASE 4.5)

**Golden Master Compliance:**
- **DO NOT deviate from `pilot-db-schema-v2.6h.json`** - It is the source of truth
- **Naming conventions:**
  - **Functions MUST end with `_fn` suffix** (e.g., `guard_user_endpoint_primary_email_fn`)
  - Triggers: `trg_[table]_[action]` (e.g., `trg_user_endpoint_guard_biu`)

**Migration Standards:**
- **Use `ALTER FUNCTION ... RENAME TO` for renaming**
- **Drop and recreate triggers** (triggers reference function by name)
- **No downtime** - Function rename is atomic operation
- **Post-migration verification** - Verify triggers reference new function name
- **Rollback testing** - Test downgrade migration before committing

### 5. Workflow

1. **Read the Phase 4.5 roadmap** to understand the task requirements
2. **Review existing function** - Check current implementation and triggers
3. **Create Alembic migration:**
   ```bash
   cd backend
   source .venv/bin/activate
   alembic revision -m "rename_user_endpoint_guard_function"
   ```
4. **Write migration SQL:**
   - Rename function using `ALTER FUNCTION ... RENAME TO`
   - Drop existing triggers
   - Recreate triggers with new function name
5. **Test migration:**
   ```bash
   alembic upgrade head  # Apply
   alembic downgrade -1  # Rollback
   alembic upgrade head  # Re-apply
   ```
6. **Verify function rename:**
   ```sql
   SELECT proname FROM pg_proc 
   WHERE proname LIKE '%guard_user_endpoint%';
   -- Should show: guard_user_endpoint_primary_email_fn
   ```
7. **Run all tests** - Must pass before completion
8. **Update Phase 4.5 roadmap:**
   - Check off deliverables: `- [x] Deliverable description`
   - Add status: `**Status:** ✅ COMPLETE (2026-MM-DD)`
   - Add test results: `**Test Results:** X/X passing`
   - Add implementation summary (migration file, verification results)

## Key Files to Review

### Golden Master & Analysis
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - **Source of truth**
- `dev-docs/analysis/phase-4.5-db-schema-sync-to-design-plan.md` - **Active roadmap**
- `dev-docs/analysis/db-schema-vs-design/db-schema-dump-vs-design-analysis-v1.0.md` - Gap analysis

### Backend Code
- `backend/migrations/versions/` - Alembic migrations
- `backend/tests/test_schema_sync_v2_6h.py` - Schema sync test suite
- `backend/tests/test_database_triggers.py` - Trigger tests

### Recent Schema Work (March 30-31, 2026)
- **Original Function Creation:** `2026_03_30_1819-102c1d8d3d4a_fix_user_endpoint_guard_trigger_logic.py`
- **Function Enhancement:** `2026_03_30_1929-cbf672175f02_fix_user_endpoint_sync_race_condition.py`

## Success Criteria

**MUST COMPLETE ALL BEFORE MARKING TASK AS COMPLETE:**

- [ ] **Function Renamed:**
  ```sql
  ALTER FUNCTION guard_user_endpoint_primary_email() 
  RENAME TO guard_user_endpoint_primary_email_fn;
  ```

- [ ] **Triggers Updated:**
  ```sql
  -- Drop old triggers
  DROP TRIGGER IF EXISTS trg_user_endpoint_guard_biu ON user_endpoint;
  DROP TRIGGER IF EXISTS trg_user_endpoint_guard_bd ON user_endpoint;
  
  -- Recreate with correct function name
  CREATE TRIGGER trg_user_endpoint_guard_biu
  BEFORE INSERT OR UPDATE ON user_endpoint
  FOR EACH ROW EXECUTE FUNCTION guard_user_endpoint_primary_email_fn();
  
  CREATE TRIGGER trg_user_endpoint_guard_bd
  BEFORE DELETE ON user_endpoint
  FOR EACH ROW EXECUTE FUNCTION guard_user_endpoint_primary_email_fn();
  ```

- [ ] **Database Verification:**
  ```sql
  -- 1. Verify old function name doesn't exist
  SELECT proname FROM pg_proc 
  WHERE proname = 'guard_user_endpoint_primary_email';
  -- Should return: 0 rows
  
  -- 2. Verify new function name exists
  SELECT proname FROM pg_proc 
  WHERE proname = 'guard_user_endpoint_primary_email_fn';
  -- Should return: guard_user_endpoint_primary_email_fn
  
  -- 3. Verify triggers reference new function
  SELECT 
    tgname AS trigger_name,
    tgrelid::regclass AS table_name,
    pg_get_functiondef(tgfoid) AS function_def
  FROM pg_trigger
  WHERE tgrelid = 'user_endpoint'::regclass
    AND tgname LIKE '%guard%';
  -- Should show: both triggers executing guard_user_endpoint_primary_email_fn()
  ```

- [ ] Alembic migration created and tested (upgrade + downgrade)
- [ ] Migration applied successfully to local database
- [ ] **ALL existing tests pass** (444/444 baseline maintained without integration, 471/471 with integration)
- [ ] **ALL new tests pass** (zero failures) - or existing trigger tests verified
- [ ] **Test pass rate: 100%** (X/X passing, 0 failing)
- [ ] Phase 4.5 roadmap updated with completion status
- [ ] Function naming follows Golden Master standard (`_fn` suffix)
- [ ] Existing functionality unchanged (Highlander rule still works)

**Task Status in Roadmap:**
- ✅ **COMPLETE** - If all tests pass (implementation + tests 100% complete)
- 🟡 **PARTIALLY COMPLETE** - If fix document created for failing tests
  - Must include: "Implementation complete, tests require fixes (see test_[feature]_fixes.md)"
  - Cannot mark COMPLETE until all tests pass

**If Tests Fail:**
- Create `dev-docs/testing-support/task-db-sync-05-test-fixes.md` with concrete fixes
- Update task status to "🟡 PARTIALLY COMPLETE" in Phase 4.5 roadmap
- Document exact steps to achieve 100% test pass rate
- Include time estimates for each fix

## Implementation Details

### Current State (March 30, 2026)

**Existing Function:**
```sql
-- Created in migration: 2026_03_30_1819-102c1d8d3d4a
CREATE OR REPLACE FUNCTION guard_user_endpoint_primary_email()
RETURNS TRIGGER AS $$
-- ... function logic ...
$$ LANGUAGE plpgsql;
```

**Existing Triggers:**
```sql
CREATE TRIGGER trg_user_endpoint_guard_biu
BEFORE INSERT OR UPDATE ON user_endpoint
FOR EACH ROW EXECUTE FUNCTION guard_user_endpoint_primary_email();

CREATE TRIGGER trg_user_endpoint_guard_bd
BEFORE DELETE ON user_endpoint
FOR EACH ROW EXECUTE FUNCTION guard_user_endpoint_primary_email();
```

### Required State (Golden Master v2.6h)

**Function Name:** `guard_user_endpoint_primary_email_fn` (with `_fn` suffix)

**Triggers:** Reference `guard_user_endpoint_primary_email_fn()` instead of `guard_user_endpoint_primary_email()`

### Migration Strategy

**Upgrade:**
1. Rename function using `ALTER FUNCTION ... RENAME TO`
2. Drop existing triggers (they reference old function name)
3. Recreate triggers with new function name

**Downgrade:**
1. Drop triggers (they reference new function name)
2. Rename function back to original name
3. Recreate triggers with original function name

**Why This Works:**
- `ALTER FUNCTION ... RENAME TO` is atomic and instantaneous
- No downtime (function remains available during rename)
- Triggers must be recreated because they store function name at creation time
- No data migration needed (pure metadata change)

## Questions to Ask

Before starting:
1. Have I reviewed the existing function implementation?
2. Have I checked which triggers reference this function?
3. Do I understand the Highlander rule this function enforces?
4. What tests currently verify this function's behavior?

During implementation:
1. Am I using `ALTER FUNCTION ... RENAME TO` (not DROP + CREATE)?
2. Have I dropped all triggers before recreating them?
3. Have I tested the migration in both directions (upgrade + downgrade)?
4. Are ALL tests passing (100% pass rate)?

After implementation:
1. Do I have 100% test pass rate (X/X passing, 0 failing)?
2. Have I verified the function name in the database?
3. Have I verified triggers reference the new function name?
4. Does the Highlander rule still work (only one primary email)?
5. Have I updated the Phase 4.5 roadmap with completion status?

## Example Task Flow

```bash
# ============================================================================
# Phase 4.5 Task 5: Function Naming Standard Compliance
# ============================================================================

# 1. Review the task in Phase 4.5 roadmap
cat dev-docs/analysis/phase-4.5-db-schema-sync-to-design-plan.md | grep -A 30 "Task 5:"

# 2. Check current function name in database
cd backend
source .venv/bin/activate
psql -d pilot_dev -c "SELECT proname FROM pg_proc WHERE proname LIKE '%guard_user_endpoint%';"
# Should show: guard_user_endpoint_primary_email

# 3. Check existing triggers
psql -d pilot_dev -c "
  SELECT 
    tgname AS trigger_name,
    tgrelid::regclass AS table_name,
    proname AS function_name
  FROM pg_trigger t
  JOIN pg_proc p ON t.tgfoid = p.oid
  WHERE tgrelid = 'user_endpoint'::regclass
    AND tgname LIKE '%guard%'
  ORDER BY trigger_name;
"

# 4. Create migration
alembic revision -m "rename_user_endpoint_guard_function"

# 5. Edit migration file to add SQL
# [Edit migration file with ALTER FUNCTION and trigger recreation]

# 6. Test migration upgrade
alembic upgrade head

# 7. Verify function rename
psql -d pilot_dev -c "SELECT proname FROM pg_proc WHERE proname = 'guard_user_endpoint_primary_email_fn';"
# Should show: guard_user_endpoint_primary_email_fn

# 8. Verify triggers updated
psql -d pilot_dev -c "
  SELECT 
    tgname,
    pg_get_triggerdef(oid) AS trigger_def
  FROM pg_trigger
  WHERE tgrelid = 'user_endpoint'::regclass
    AND tgname LIKE '%guard%';
"
# Should show: EXECUTE FUNCTION guard_user_endpoint_primary_email_fn()

# 9. Test migration downgrade
alembic downgrade -1

# 10. Verify function reverted
psql -d pilot_dev -c "SELECT proname FROM pg_proc WHERE proname LIKE '%guard_user_endpoint%';"
# Should show: guard_user_endpoint_primary_email (original name)

# 11. Re-apply migration
alembic upgrade head

# 12. Run baseline tests (expect 444 tests without integration)
pytest tests/ --ignore=tests/integration/ -v 2>&1 | grep -E "(passed|failed|===)" | tail -5

# 13. Run schema sync tests
pytest tests/test_schema_sync_v2_6h.py tests/test_database_triggers.py -v

# 14. Run ALL tests including integration (expect 471 tests)
pytest tests/ -v

# 15. Update Phase 4.5 roadmap
# [Edit phase-4.5-db-schema-sync-to-design-plan.md]
# - [x] Rename Function
# - [x] Update Triggers
# **Status:** ✅ COMPLETE (2026-04-XX)
# **Test Results:** 444/444 passing without integration, 471/471 with integration (100%)
```

## Notes

- **Function Rename is Atomic:** `ALTER FUNCTION ... RENAME TO` is instantaneous, no downtime
- **Triggers Must Be Recreated:** Triggers store function name at creation time, must drop/recreate
- **No Data Migration:** This is a pure metadata change, no table data affected
- **Existing Behavior Preserved:** Function logic unchanged, only name changes
- **Golden Master Compliance:** The `_fn` suffix is required by v2.6h standard
- **Related Functions:** Check if other functions need renaming (Task 4 already fixed `set_updated_at_fn`, `guard_created_fields_immutable_fn`, `guard_tenant_user_platform_isolation_fn`)

## Schema Synchronization Context

**Phase 2: Functions & Triggers (Current Phase)**
- ✅ Task 4: Missing PL/pgSQL Functions (3 functions + 200 triggers) - COMPLETE
- 🔴 **Task 5: Function Naming Standard Compliance** - THIS TASK
- 🔴 Task 6: Audit Trigger Coverage (30+ tables) - NOT STARTED
- 🟡 Task 7: Operational Trigger Verification - PARTIALLY COMPLETE
```

---

## Usage

1. Start this task with the `MVP Builder` custom Roo Code mode
2. Copy the prompt section above to begin
3. The AI will have full context and standards from Golden Master v2.6h
4. When finished, the AI will update the Phase 4.5 roadmap with completion status
