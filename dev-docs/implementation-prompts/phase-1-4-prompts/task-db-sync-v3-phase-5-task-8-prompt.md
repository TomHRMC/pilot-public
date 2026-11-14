# Task 8: Update guard_tenant_user_platform_isolation() Function Logic

**Reference:** `dev-docs/analysis/phase-4.7-db-schema-sync-3-plan.md` - Phase 5, Task 8
**Authority (Dual Master):**
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - Golden Master JSON
- `dev-docs/db-design/aevofab-db-schema-dump-phase-4.6-post.sql` - Production SQL Dump (Phase 4.6 Baseline)
**Type:** Phase 5 - Function Logic Alignment
**Priority:** MEDIUM
**Change Type:** MIGRATION + JSON_UPDATE

---

## Context

This is **Phase 4.7 - DB Sync v#3**, a third forensic reconciliation after completing Phases 4.5 and 4.6. A comprehensive comparison between the latest SQL dump (`aevofab-db-schema-dump-phase-4.6-post.sql`) and the Golden Master JSON revealed **5 major remaining discrepancies** requiring final alignment before production deployment.

**Key Focus Areas:**
1. **Enumerated type standardization** (ENUM → TEXT + CHECK) ✅ COMPLETE
2. **Integer capacity risks** (Foreign key type mismatches) ✅ COMPLETE
3. **Unique indexing logic** (Broken email uniqueness constraint) ✅ COMPLETE
4. **Data integrity enforcement** (Missing defaults and constraints) ✅ COMPLETE
5. **Function/trigger alignment** (Database vs JSON discrepancies) ← **THIS TASK**

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

**Phase 4.7 Phases 1-4 Status:** ✅ COMPLETE (April 3-7, 2026)
- ✅ Phase 1: ENUM standardization (Tasks 1-2) - 591/591 unit, 618/618 total tests
- ✅ Phase 2: Integer capacity fixes (Task 3) - 597/597 unit, 624/624 total tests
- ✅ Phase 3: Unique indexing fix (Task 4) - 602/602 unit, 629/629 total tests
- ✅ Phase 4: Data integrity enforcement (Tasks 5-7) - 609/609 unit, 636/636 total tests

**Current Baseline:** 609/609 unit tests, 636/636 total tests passing (100%)

**See:**
- `dev-docs/analysis/phase-4.5-db-schema-sync-to-design-plan.md` for Phase 4.5 history
- `dev-docs/analysis/phase-4.6-db-schema-sync-2-plan.md` for Phase 4.6 history
- `dev-docs/analysis/phase-4.7-db-schema-sync-3-plan.md` for Phase 4.7 roadmap

---

## Current Task: Update guard_tenant_user_platform_isolation() Function Logic

**Effort:** 0.5 days
**Gap Reference:** Phase 4.7 Analysis - Phase 5: Align Function Logic
**Change Type:** MIGRATION (SQL function update) + JSON_UPDATE (documentation alignment)

This task aligns the `guard_tenant_user_platform_isolation()` function between the SQL database and JSON schema. The function enforces a critical security rule: **platform users (staff, superadmin) cannot be assigned to tenants**.

Currently, the SQL database and JSON schema use different logic to detect platform users, causing documentation drift and potential future confusion.

### What Needs to Be Fixed

| # | Component | Issue | Direction | Complexity |
|---|-----------|-------|-----------|------------|
| **1** | `guard_tenant_user_platform_isolation()` function | JSON checks `platform_role_code IS NOT NULL`, SQL checks `is_platform_user = true` | SQL→SQL (make explicit) + JSON→JSON (update docs) | LOW |

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

**Record the output of both results:** `609/609 & 636/636 tests passing` (Phase 4.7 baseline - after Phase 4 completion)

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
    op.execute("CREATE OR REPLACE FUNCTION ...")  # Your actual changes
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

#### Problem: Logic Discrepancy in Platform User Detection

The `guard_tenant_user_platform_isolation()` function prevents platform users from being assigned to tenants. However, the SQL database and JSON schema use different logic to detect platform users.

**JSON Schema Logic (LESS SAFE):**
```sql
-- Checks if user has ANY platform role code
IF EXISTS (
  SELECT 1 FROM "user"
  WHERE id = NEW.user_id AND platform_role_code IS NOT NULL
) THEN
  RAISE EXCEPTION 'Platform users cannot be assigned to tenants';
END IF;
```

**SQL Database Logic (MORE EXPLICIT - CURRENTLY DEPLOYED):**
```sql
-- Checks explicit is_platform_user boolean computed field
IF EXISTS (
  SELECT 1 FROM "user"
  WHERE id = NEW.user_id AND is_platform_user = true
) THEN
  RAISE EXCEPTION 'Platform users cannot be assigned to tenants';
END IF;
```

**Why SQL Version is Better:**
- Uses the explicit `is_platform_user` computed field (GENERATED column)
- More semantic: "is this user a platform user?" vs. "does this user have a role code?"
- Future-proof: If we add more platform roles, logic doesn't change
- Aligns with the model's computed field design

**Decision:** Keep the SQL database logic (explicit boolean check) and update the JSON schema documentation to match.

---

#### ⚠️ CLARIFICATION: What This Task Actually Does

**IMPORTANT - Please Read Carefully:**

The SQL database **ALREADY HAS the correct logic** (`is_platform_user = true`). This task does TWO things:

1. **Migration (SQL Enhancement):** Improve error messages ONLY - no logic change
   - **Before:** Basic error "Platform users cannot be assigned to tenants"
   - **After:** Enhanced error with user_id, ERRCODE, and helpful HINT
   - **Security logic:** UNCHANGED (still uses `is_platform_user = true`)

2. **JSON Update (Documentation Fix):** Update JSON to match SQL reality
   - **Before:** JSON documents old logic (`platform_role_code IS NOT NULL`)
   - **After:** JSON documents current logic (`is_platform_user = true`)

**This is NOT a security fix - it's a developer experience enhancement.** The platform user isolation rule already works correctly in production.

---

#### Migration Task: Enhance SQL Function with Better Error Messages

**SQLModel Fix:**
No SQLModel changes required - the function is managed via migrations only.

**Current Production SQL (What's Already Running):**
```sql
-- This is the CURRENT state (correct logic, basic errors)
CREATE FUNCTION guard_tenant_user_platform_isolation()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    -- Already uses is_platform_user = true ✅
    IF EXISTS (
        SELECT 1 FROM "user"
        WHERE id = NEW.user_id AND is_platform_user = true
    ) THEN
        RAISE EXCEPTION 'Platform users cannot be assigned to tenants';
    END IF;
    RETURN NEW;
END;
$$;
```

**Enhanced SQL (What We're Migrating To):**
```sql
-- Migration upgrade():
-- ONLY enhancing error messages - logic stays the same
CREATE OR REPLACE FUNCTION guard_tenant_user_platform_isolation()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    is_platform bool;
BEGIN
    -- Use explicit is_platform_user boolean (GENERATED column)
    SELECT is_platform_user INTO is_platform
    FROM "user"
    WHERE id = NEW.user_id;
    
    IF is_platform THEN
        RAISE EXCEPTION 'User % is a platform user and cannot be assigned to a tenant',
            NEW.user_id
            USING ERRCODE = '23514',
                  HINT = 'Platform users (staff, superadmin) cannot be tenant users';
    END IF;
    
    RETURN NEW;
END;
$$;

-- Migration downgrade():
-- Revert to platform_role_code IS NOT NULL check
CREATE OR REPLACE FUNCTION guard_tenant_user_platform_isolation()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    platform_role text;
BEGIN
    SELECT platform_role_code INTO platform_role
    FROM "user"
    WHERE id = NEW.user_id;
    
    IF platform_role IS NOT NULL THEN
        RAISE EXCEPTION 'User % has platform role % and cannot be assigned to a tenant',
            NEW.user_id, platform_role;
    END IF;
    
    RETURN NEW;
END;
$$;
```

**Database Verification Query:**
```sql
-- Verify function exists and uses is_platform_user
SELECT pg_get_functiondef(oid)
FROM pg_proc
WHERE proname = 'guard_tenant_user_platform_isolation';

-- Verify trigger is attached to tenant_user table
SELECT tgname, tgtype, tgenabled
FROM pg_trigger
WHERE tgname = 'trg_guard_tenant_user_platform_isolation';
```

---

#### JSON Schema Update Task

**Problem:** JSON schema function definition doesn't match SQL reality

**SQL Database Reality (What's Actually Working):**
```sql
-- Production SQL (from phase-4.6-post dump)
CREATE OR REPLACE FUNCTION guard_tenant_user_platform_isolation()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    is_platform bool;
BEGIN
    SELECT is_platform_user INTO is_platform
    FROM "user"
    WHERE id = NEW.user_id;
    
    IF is_platform THEN
        RAISE EXCEPTION 'User % is a platform user and cannot be assigned to a tenant',
            NEW.user_id
            USING ERRCODE = '23514',
                  HINT = 'Platform users (staff, superadmin) cannot be tenant users';
    END IF;
    
    RETURN NEW;
END;
$$;
```

**JSON Schema Gap (What's Missing in JSON):**
```json
{
  "functions": [{
    "name": "guard_tenant_user_platform_isolation",
    "returns": "trigger",
    "language": "plpgsql",
    "body": "... platform_role_code IS NOT NULL ..."
  }]
}
```

**JSON Schema Fix Required:**
Update the `functions` array in `pilot-db-schema-v2.6h.json` to match the enhanced SQL definition with explicit `is_platform_user` check.

**⚠️ IMPORTANT: Database migration is needed to enhance error messages**
- The database currently has the correct logic but basic error messages
- We're enhancing it with better error context (user_id in message, ERRCODE, HINT)
- JSON documentation will be updated to match the enhanced version

---

### 2. Implementation Order

**For This Task (MIGRATION + JSON_UPDATE):**

1. **✅ Establish Regression Baseline** (609/609 unit, 636/636 total tests)
2. **Query Current Function**
   - Use postgres-local MCP to review current function definition
   - Confirm it uses `is_platform_user` check
3. **Create Alembic Migration**
   ```bash
   cd backend
   source .venv/bin/activate
   alembic revision -m "phase_4_7_enhance_guard_platform_isolation_task8"
   ```
4. **Enhance Migration File**
   - Add `CREATE OR REPLACE FUNCTION` with enhanced error handling
   - Add proper downgrade() function
   - No autogenerate needed (function-only migration)
5. **Apply Migration**
   ```bash
   alembic upgrade head
   ```
6. **Create/Update Test Suite**
   - Verify existing `test_plpgsql_functions.py` tests still pass
   - Optionally add test for improved error message format
7. **Run Regression Tests** (see "After You Complete" section)
8. **Update JSON Schema**
   - Modify `dev-docs/db-design/pilot-db-schema-v2.6h.json`
   - Find `guard_tenant_user_platform_isolation` function definition
   - Update body to match enhanced SQL version
9. **Verify Database (Confirm Enhanced Function Active)**
   ```sql
   SELECT pg_get_functiondef(oid)
   FROM pg_proc
   WHERE proname = 'guard_tenant_user_platform_isolation';
   ```
10. **Run Final Tests**
    ```bash
    pytest --ignore=tests/integration/ tests/ -v
    # Expected: 609/609 passing (no new tests, verification only)
    pytest tests/ -v
    # Expected: 636/636 passing
    ```
11. **Update Documentation**

---

### 3. Test Requirements

**⚠️ ZERO REGRESSION POLICY:**
- **ALL 609 existing unit tests MUST still pass**
- **ALL 636 total tests (including integration) MUST still pass**
- **Target: 100% pass rate on both test suites**

#### Verification Testing (No New Tests Expected)

**Existing Test File:** `backend/tests/test_plpgsql_functions.py`

This file already tests the `guard_tenant_user_platform_isolation()` function behavior. The enhanced error messages don't change the function's core logic, so existing tests should pass without modification.

**What Existing Tests Cover:**
- Platform user (is_platform_user = true) cannot be added to tenant_user
- Regular user (is_platform_user = false) can be added to tenant_user
- Exception is raised with proper message

**Optional Enhancement Test (if you want to verify error message format):**
```python
def test_guard_platform_isolation_error_format(db_session: Session):
    """Verify enhanced error message format includes user_id and hint"""
    from sqlalchemy.exc import IntegrityError
    from app.models.core import User, Tenant, TenantUser
    
    # Create platform user
    platform_user = User(
        email="staff@aevofab.example.com",
        platform_role_code="staff",  # This sets is_platform_user = true
        is_active=True
    )
    db_session.add(platform_user)
    db_session.commit()
    
    # Create tenant
    tenant = Tenant(name="Test Tenant")
    db_session.add(tenant)
    db_session.commit()
    
    # Attempt to assign platform user to tenant (should fail)
    tenant_user = TenantUser(
        tenant_id=tenant.id,
        user_id=platform_user.id
    )
    db_session.add(tenant_user)
    
    with pytest.raises(IntegrityError) as exc_info:
        db_session.commit()
    
    error_msg = str(exc_info.value)
    
    # Verify error message includes user_id
    assert str(platform_user.id) in error_msg
    
    # Verify error message mentions platform user
    assert "platform user" in error_msg.lower()
    
    # Verify hint is included (if your PostgreSQL version supports it)
    assert "staff" in error_msg.lower() or "superadmin" in error_msg.lower()
    
    db_session.rollback()
```

**Test Patterns to Follow:**
- Review `backend/tests/test_plpgsql_functions.py` - Shows proper function testing
- Use fixtures from `backend/tests/conftest.py`
- Use `db_session` parameter and `select()/exec()` pattern

**Common Test Fixtures Available:**
- `db_session` - Database session (use this, NOT `session`)
- `test_tenant` - Pre-created tenant for testing
- `test_user` - Pre-created user linked to test_tenant
- `utc_now` - Timezone-aware current timestamp function

---

### 4. JSON Change Tracking

**For JSON_UPDATE Portion:** Provide a summary of all JSON changes for manual review.

**Format:**
```markdown
## JSON Schema Changes for Task 8

**File:** `dev-docs/db-design/pilot-db-schema-v2.6h.json`

### Changes Made:

1. **Function: `guard_tenant_user_platform_isolation`**
   - **Location:** `functions` array (search for "guard_tenant_user_platform_isolation")
   - **Before:** Uses `platform_role_code IS NOT NULL` check
   - **After:** Uses `is_platform_user = true` check with enhanced error handling
   - **Reason:** Align with production SQL implementation and improve error diagnostics

### Verification:

- [ ] JSON function body matches SQL function definition from pg_get_functiondef query
- [ ] Enhanced error message format documented (includes user_id, ERRCODE, HINT)
- [ ] All 609/636 tests still passing (no regression)
```

**⚠️ USER REVIEW REQUIRED:**
The founder will manually review these JSON changes against the SQL dump to confirm accuracy.

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
- **For this task:** `609 passed` (unit), `636 passed` (total) - no change from baseline
- This is a logic enhancement, not a new feature, so test count should remain the same

### Step 3: Verify 100% Pass Rate

**If ANY tests fail:**
1. Identify failing tests
2. Determine if function enhancement broke existing behavior
3. Fix ALL failures before proceeding
4. Re-run until 100% pass rate

**For this task:**
- If tests fail → Your function enhancement changed behavior (investigate)
- If tests still pass → Function enhancement is correct (proceed)

---

## Documentation Update

### Update Project Plan Document

**File to Update:** `dev-docs/analysis/phase-4.7-db-schema-sync-3-plan.md`

Find Phase 5, Task 8 (lines 1007-1130) and update with:

```markdown
### Task 8: Update `guard_tenant_user_platform_isolation()` Function Logic

**Status:** ✅ COMPLETE (YYYY-MM-DD)
**Effort:** 0.5 days (actual)
**Change Type:** MIGRATION + JSON_UPDATE

**Implementation Summary:**

- Migration: `YYYY_MM_DD_HHMM-[hash]_phase_4_7_enhance_guard_platform_isolation_task8.py`
- Updated: `pilot-db-schema-v2.6h.json` - Function definition aligned with SQL
- Test Suite: Existing `test_plpgsql_functions.py` - All tests ✅ (no new tests)
- Final Results: 609/609 unit tests passing (100%), 636/636 total tests passing (100% - no regression)

**Key Changes:**
- ✅ Enhanced `guard_tenant_user_platform_isolation()` function with explicit `is_platform_user` boolean check
- ✅ Improved error messages with user_id context, ERRCODE, and helpful HINT
- ✅ Updated JSON schema to match enhanced SQL function definition
- ✅ Aligned with `user.is_platform_user` computed field design

**Verification:**
- Function definition verified via pg_get_functiondef() query
- JSON schema updated to match SQL exactly
- All existing tests passing (609 unit, 636 total)
- Platform user isolation rule still enforced correctly
```

---

## Success Criteria

**MUST COMPLETE ALL BEFORE MARKING TASK AS DONE:**

### For This Task (MIGRATION + JSON_UPDATE):
- [ ] **Regression baseline captured** (609/609 unit, 636/636 total tests)
- [ ] **Current function reviewed** via postgres-local MCP query
- [ ] **Alembic migration created** with enhanced function definition
- [ ] **Migration applied successfully** (`alembic upgrade head`)
- [ ] **Function uses explicit `is_platform_user` boolean check**
- [ ] **Enhanced error messages** include user_id, ERRCODE, HINT
- [ ] **JSON schema updated** to match enhanced SQL function
- [ ] **JSON changes documented** for manual review
- [ ] **Database verification confirms** enhanced function active
- [ ] **ALL 609 existing unit tests still passing**
- [ ] **ALL 636 total tests still passing** (no regression)
- [ ] **Migration rollback tested** (`alembic downgrade -1` then `upgrade head` again)
- [ ] **Project plan document updated**

### Critical Verification:
- [ ] **100% test pass rate** - No failing tests
- [ ] **Zero regression** - Baseline maintained (609/636)
- [ ] **JSON ↔ SQL alignment** - Function definitions match exactly

---

## Key Files to Review

### Architecture & Design
- `dev-docs/analysis/phase-4.7-db-schema-sync-3-plan.md` - **Task 8 Details** ⭐
- `dev-docs/analysis/phase-4.7-db-schema-sync-3-analysis.md` - Phase 5 Analysis
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - **Golden Master JSON** (UPDATE THIS)
- `dev-docs/db-design/aevofab-db-schema-dump-phase-4.6-post.sql` - **Production SQL Dump**

### Backend Code
- `backend/app/models/core.py` - User model with `is_platform_user` computed field
- `backend/migrations/versions/2026_03_31_1850-6b525454c89c_add_missing_plpgsql_functions.py` - Original function creation

### Tests (Reference for Patterns)
- `backend/tests/test_plpgsql_functions.py` - **Existing tests for this function** ⭐
- `backend/tests/conftest.py` - Test fixtures

---

## Risk Assessment

**Logic Risk:** LOW
- Both implementations (platform_role_code IS NOT NULL vs is_platform_user = true) are functionally equivalent
- Enhancement maintains same security guarantee

**Regression Risk:** LOW
- Function enhancement improves error messages without changing core logic
- Existing tests should pass without modification

**JSON Documentation Risk:** LOW
- Simple text replacement in JSON file
- Founder will manually review changes

**Migration Risk:** LOW
- CREATE OR REPLACE FUNCTION is a safe operation
- Downgrade path provided for rollback

---

## Notes

### Important Patterns to Follow
- **Virtual Environment Required:** All Python/pytest commands use `source .venv/bin/activate`
- **Use `db_session` Parameter:** NOT `session` (pytest fixture naming)
- **Use `select()/exec()` Pattern:** NOT `query()` (SQLModel standard, no deprecation warnings)
- **Check Alembic Migrations:** ALWAYS remove `audit.event` table creation if autogenerated (not applicable here since manual migration)
- **Dual Master Strategy:** JSON is documentation authority, SQL dump is runtime authority
- **Zero Regression Policy:** All 609 unit + 636 total tests MUST pass after changes

### Phase 4.7 Phase 5 Specific
- **Function/trigger alignment** - Final gap between JSON documentation and SQL reality
- **Logic enhancement** - Better error messages improve debugging experience
- **Documentation sync** - JSON must match SQL exactly
- **No new features** - Just alignment and enhancement

### If You Get Stuck
- Check the SQL dump for exact production function definition
- Use `postgres-local` MCP server to query function in real-time: `SELECT pg_get_functiondef(oid) FROM pg_proc WHERE proname = 'guard_tenant_user_platform_isolation'`
- Review existing test file for current function behavior verification
- Search for similar function migrations in backend/migrations/versions/

---

## Example Task Flow

### For This Task (Function Enhancement + JSON Update):

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

# 2. Query current function (use MCP server or direct SQL)
# Verify it uses is_platform_user check

# 3. Create manual migration (no autogenerate needed)
alembic revision -m "phase_4_7_enhance_guard_platform_isolation_task8"

# 4. Edit migration file
# Add CREATE OR REPLACE FUNCTION with enhanced logic
# Add proper downgrade() function

# 5. Apply migration
alembic upgrade head

# 6. Verify function active
# Use postgres-local MCP or psql to check function definition

# 7. Run existing tests (should all pass)
pytest tests/test_plpgsql_functions.py -v

# 8. Regression check - Ensure no breaks
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Expected: 609 passed

pytest tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Expected: 636 passed

# 9. Rollback test - Verify downgrade works
alembic downgrade -1
alembic upgrade head
pytest tests/ -v  # Should still pass

# 10. Update JSON schema
# Edit dev-docs/db-design/pilot-db-schema-v2.6h.json
# Find "guard_tenant_user_platform_isolation" function
# Update body to match enhanced SQL

# 11. Document JSON changes for founder review

# 12. Update docs
# Edit dev-docs/analysis/phase-4.7-db-schema-sync-3-plan.md
# Mark task as complete with results
```

---

## Questions to Ask

**Before starting:**
1. Have I captured the 609/609 unit and 636/636 total baselines?
2. Do I have access to the postgres-local MCP server to query the current function?
3. Do I understand the difference between platform_role_code IS NOT NULL and is_platform_user = true?
4. Have I reviewed the existing test file to understand current test coverage?

**During implementation:**
1. Does the enhanced function use the explicit is_platform_user boolean?
2. Are the error messages more helpful (include user_id, ERRCODE, HINT)?
3. Does the downgrade() function revert to the previous logic?
4. Have I removed any `audit.event` table creation from autogenerate? (N/A - manual migration)
5. Am I documenting JSON changes for founder review?

**After implementation:**
1. Do I have 100% test pass rate on BOTH unit tests (609) and total tests (636)?
2. Did baseline stay at 609/636 (no regression)?
3. Have I verified the function definition via database query?
4. Have I updated the project plan document?
5. Have I provided a clear JSON change list for founder review?
6. Have I tested migration rollback (`alembic downgrade -1`)?

---

**Ready to Begin!** 🚀

### Task 8 Checklist:
1. ✅ Capture baseline (609/609 unit, 636/636 total)
2. 🔍 Query current function via MCP
3. 📝 Create manual migration
4. 🛠️ Add enhanced function with better errors
5. ✅ Apply migration (`alembic upgrade head`)
6. 🔄 Run existing tests (all should pass)
7. ✏️ Update JSON schema to match SQL
8. 📋 Document JSON changes for review
9. 🔄 Run regression tests (609/636)
10. ↩️ Test rollback
11. 📚 Update project plan

Remember: Phase 4.7 Phase 5 is about **final alignment** - function logic and documentation must match SQL reality exactly. This task enhances error messages while maintaining the correct security logic!
