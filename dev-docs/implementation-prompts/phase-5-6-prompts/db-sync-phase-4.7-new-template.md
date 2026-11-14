# Task [TASK_NUMBER]: [TASK_NAME]

**Reference:** `dev-docs/analysis/phase-4.7-db-schema-sync-3-plan.md` - Phase [PHASE_NUMBER], Task [TASK_NUMBER]
**Authority (Dual Master):**
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - Golden Master JSON
- `dev-docs/db-design/aevofab-db-schema-dump-phase-4.6-post.sql` - Production SQL Dump (Phase 4.6 Baseline)
**Type:** Phase [PHASE_NUMBER] - [CATEGORY]
**Priority:** [CRITICAL/HIGH/MEDIUM/LOW]
**Change Type:** [MIGRATION/JSON_UPDATE/DOCUMENTATION]

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

**Current Baseline:** 575/575 unit tests, 602/602 total tests passing (100%)

**See:**
- `dev-docs/analysis/phase-4.5-db-schema-sync-to-design-plan.md` for Phase 4.5 history
- `dev-docs/analysis/phase-4.6-db-schema-sync-2-plan.md` for Phase 4.6 history

---

## Current Task: [TASK_NAME]

**Effort:** [X] days
**Gap Reference:** Phase 4.6 Analysis - [SECTION_REFERENCE]
**Change Type:** [MIGRATION/JSON_UPDATE/DOCUMENTATION]

[TASK_DESCRIPTION - 2-3 sentences explaining what this task accomplishes and WHY it matters]

### What Needs to Be Fixed

| # | Component | Issue | Direction | Complexity |
|---|-----------|-------|-----------|------------|
| **1** | `Component` | [Issue description] | SQL→JSON / JSON→SQL | LOW/MEDIUM/HIGH |
| **2** | ... | ... | ... | ... |

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

**Record the output of both results:** `575/575 & 602/602 tests passing` (Phase 4.7 baseline - starting from Phase 4.6 completion)

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

[IMPLEMENTATION INSTRUCTIONS - Choose appropriate section based on Change Type]

#### For MIGRATION Tasks (Phase 4.7 - All Phases Have Migrations)

**Problem:** [Detailed description of the database gap]

**SQLModel Fix:**
```python
# backend/app/models/[file].py
from sqlalchemy import [imports]

class ClassName:
    __tablename__ = "[table_name]"
    __table_args__ = (
        [Constraint definitions],
    )
    # ... fields ...
```

**Migration SQL:**
```sql
-- Pre-migration validation
[VALIDATION QUERY]

-- Add constraint/table
[ALTER TABLE STATEMENT or CREATE TABLE]
```

**Database Verification Query:**
```sql
-- Verify constraint/table exists after migration
SELECT [verification query];
```

---

#### For JSON_UPDATE Tasks (Phase 4.7 - Task 9 Only)

**Problem:** [Description of JSON schema gap]

**SQL Database Reality (What's Actually Working):**
```sql
-- Production SQL (from phase-4.6-post dump)
[SQL DEFINITION]
```

**JSON Schema Gap (What's Missing in JSON):**
```json
{
  "functions": [{
    "name": "[function_name]",
    "body": "[WRONG or MISSING logic]"
  }]
}
```

**JSON Schema Fix Required:**
```json
{
  "functions": [{
    "name": "[function_name]",
    "body": "[CORRECTED logic matching SQL]"
  }]
}
```

**⚠️ IMPORTANT: NO DATABASE MIGRATION NEEDED**
- The database already has the correct implementation
- This is a JSON documentation update only
- No `alembic revision` required
- Verification is comparing JSON to SQL dump

---

### 2. Implementation Order

**For MIGRATION Tasks (Phase 1):**

1. **✅ Establish Regression Baseline** (572/572 tests)
2. **Pre-Migration Data Validation**
   - Run validation queries
   - Clean up invalid data if found
3. **Update SQLModel Classes**
   - Modify `backend/app/models/[file].py`
4. **Generate Alembic Migration**
   ```bash
   cd backend
   source .venv/bin/activate
   alembic revision --autogenerate -m "[task_name]_task[N]"
   ```
5. **Review & Enhance Migration**
   - Verify all changes captured
   - Add pre-migration checks
   - Ensure downgrade() is complete
6. **Apply Migration**
   ```bash
   alembic upgrade head
   ```
7. **Create Test Suite**
   - Create `backend/tests/test_[task_name].py`
   - Use `session.query()` NOT `session.exec()` (avoid deprecation warnings)
8. **Run New Tests**
   ```bash
   pytest tests/test_[task_name].py -v
   ```
9. **Run Regression Tests** (see "After You Complete" section)
10. **Update Documentation**

---

**For JSON_UPDATE Tasks (Phases 2, 3, 4):**

1. **✅ Establish Regression Baseline** (575/575 unit, 602/602 total tests)
2. **Review SQL Dump**
   - Read `dev-docs/db-design/aevofab-db-schema-dump-phase-4.6-post.sql`
   - Locate the production function/trigger definition
3. **Update JSON Schema**
   - Modify `dev-docs/db-design/pilot-db-schema-v2.6h.json`
   - Copy correct logic from SQL dump to JSON
4. **Document JSON Changes** (see "JSON Change Tracking" section below)
5. **Verify Database (No Changes Expected)**
   ```sql
   -- Confirm database already has correct implementation
   SELECT prosrc FROM pg_proc WHERE proname = '[function_name]';
   ```
6. **Run Existing Tests (Verify No Regression)**
   ```bash
   pytest --ignore=tests/integration/ tests/ -v
   # Expected: 575/575 passing (no change)
   pytest tests/ -v
   # Expected: 602/602 passing (no change)
   ```
7. **Optional: Add Verification Tests**
   - Only if testing a newly documented behavior
   - Keep consistent with existing test patterns
8. **Update Documentation**

---

### 3. Test Requirements

**⚠️ ZERO REGRESSION POLICY:**
- **ALL 575 existing unit tests MUST still pass**
- **ALL 602 total tests (including integration) MUST still pass**
- **New tests (if added) MUST pass**
- **Target: 100% pass rate on both test suites**

#### For MIGRATION Tasks (Most Phase 4.7 Tasks)

**Test File:** `backend/tests/test_phase_4_7_[task_name].py`

**Required Coverage (Minimum [X] Tests):**
```python
"""
Test Suite: Phase 4.7 Task [N] - [TASK_NAME]
Tests [description] - final schema alignment for production deployment

Reference: phase-4.7-db-schema-sync-3-plan.md
"""
import pytest
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from app.models.[module] import [Models]

# ✅ CORRECT: Use db_session parameter and select()/exec() pattern

class Test[FeatureName]:
    """[Description]"""
    
    def test_[scenario]_valid(self, db_session: Session, test_tenant, test_user):
        """Valid data should be accepted"""
        entity = Entity
        db_session.add(entity)
        db_session.commit()
        
        # Use select() with exec() - NOT query()
        result = db_session.exec(
            select([Entity]).where([Entity].id == entity.id)
        ).first()
        assert result is not None
        assert result.field1 == "value1"
    
    def test_[scenario]_invalid(self, db_session: Session, test_tenant, test_user):
        """Invalid data should be rejected"""
        entity = Entity
        db_session.add(entity)
        
        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()
        assert "[constraint_name]" in str(exc_info.value)
        
        # Rollback to clean up failed transaction
        db_session.rollback()
    
    def test_[scenario]_null_handling(self, db_session: Session, test_tenant):
        """Test NULL values (if field is nullable)"""
        entity = Entity
        db_session.add(entity)
        
        # Should succeed if nullable=True, fail if nullable=False
        if nullable:
            db_session.commit()
            assert entity.field1 is None
        else:
            with pytest.raises(IntegrityError):
                db_session.commit()
            db_session.rollback()
```

**Test Patterns to Follow:**
- Review `backend/tests/test_check_constraints_task9.py` - Shows proper constraint testing
- Review `backend/tests/test_temporal_exclusion_constraints_task10.py` - Shows exclusion constraint testing
- Review `backend/tests/test_citext_email.py` - Shows select()/exec() pattern
- Use fixtures from `backend/tests/conftest.py`

**Common Test Fixtures Available:**
- `db_session` - Database session (use this, NOT `session`)
- `test_tenant` - Pre-created tenant for testing
- `test_user` - Pre-created user linked to test_tenant
- `test_customer` - Pre-created customer
- `test_site` - Pre-created site
- `utc_now` - Timezone-aware current timestamp function

---

#### For JSON_UPDATE Tasks

**No New Tests Required (Usually)**
- The database logic already works (proven by 575/602 passing tests)
- This is documentation alignment only

**Optional Verification Tests:**
- Add ONLY if documenting previously untested behavior
- Keep minimal and consistent with existing patterns
- Use `db_session` and `select()/exec()` patterns

---

### 4. JSON Change Tracking

**For JSON_UPDATE Tasks:** Provide a summary of all JSON changes for manual review.

**Format:**
```markdown
## JSON Schema Changes for Task [N]

**File:** `dev-docs/db-design/pilot-db-schema-v2.6h.json`

### Changes Made:

1. **Function: `[function_name]`**
   - **Location:** Line [X] (approx), `functions` array
   - **Before:** `[OLD logic or MISSING]`
   - **After:** `[NEW logic matching SQL]`
   - **Reason:** Align with production SQL implementation from Phase 4.6

2. **Trigger: `[trigger_name]`**
   - **Location:** Line [Y], `functions` array
   - **Before:** 3 separate triggers (INSERT, UPDATE, DELETE)
   - **After:** 1 consolidated trigger (INSERT OR UPDATE OR DELETE)
   - **Reason:** Match production SQL optimization

### Verification:

- [ ] All JSON changes align with `aevofab-db-schema-dump-phase-4.6-post.sql`
- [ ] No functional database changes made (JSON doc only)
- [ ] All 575/602 tests still passing (no regression)
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
- **For MIGRATION tasks:** `[575 + NEW_TEST_COUNT] passed` (unit), `[602 + NEW_TEST_COUNT] passed` (total)
- **For JSON_UPDATE tasks:** `575 passed` (unit), `602 passed` (total) - no change

### Step 3: Verify 100% Pass Rate

**If ANY tests fail:**
1. Identify failing tests
2. Determine if new or existing tests
3. Fix ALL failures before proceeding
4. Re-run until 100% pass rate

**For JSON_UPDATE tasks:**
- If existing tests fail → Your JSON changes revealed a mismatch (investigate)
- If tests still pass → JSON documentation is correct

**For MIGRATION tasks:**
- If new tests fail → Fix implementation or test logic
- If existing tests fail → Your migration broke something (rollback and fix)

---

## Documentation Update

### Update Project Plan Document

**File to Update:** `dev-docs/analysis/phase-4.7-db-schema-sync-3-plan.md`

Find Phase [PHASE_NUMBER], Task [TASK_NUMBER] and update with:

```markdown
### Task [TASK_NUMBER]: [TASK_NAME]

**Status:** ✅ COMPLETE (YYYY-MM-DD)
**Effort:** [X] days (actual)
**Change Type:** [MIGRATION/JSON_UPDATE/DOCUMENTATION]

**Implementation Summary:**

[For MIGRATION tasks:]
- Modified: `backend/app/models/[file].py`
- Migration: `YYYY_MM_DD_HHMM-[hash]_[name].py`
- Test Suite: `test_phase_4_7_[name].py` - [X] tests ✅
- Final Results: [575 + X]/[575 + X] unit tests passing (100%), [602 + X]/[602 + X] total tests passing (100%)

[For JSON_UPDATE tasks:]
- Updated: `pilot-db-schema-v2.6h.json`
- Changes: [X] functions/triggers documented from SQL
- Database: No changes (already correct)
- Final Results: 575/575 unit tests passing (100% - no regression), 602/602 total tests passing (100%)

**Key Changes:**
- ✅ [Change 1]
- ✅ [Change 2]

**Verification:**
- [How correctness was verified]
```

---

## Success Criteria

**MUST COMPLETE ALL BEFORE MARKING TASK AS DONE:**

### For MIGRATION Tasks (Most Phase 4.7 Tasks):
- [ ] **Regression baseline captured** (575/575 unit, 602/602 total tests)
- [ ] **Pre-migration data validation completed** (queries run, data clean)
- [ ] **SQLModel classes updated** with correct types/constraints
- [ ] **Used `db_session` parameter** (not `session`) in code
- [ ] **Used `select()/exec()` pattern** (not `query()`) where applicable
- [ ] **Alembic migration created** using autogenerate
- [ ] **⚠️ CRITICAL: Checked migration for `audit.event` table** and removed if present
- [ ] **Migration applied successfully** (`alembic upgrade head`)
- [ ] **All [X] new tests written and passing**
- [ ] **Tests use `db_session` parameter** and `select()/exec()` pattern
- [ ] **ALL 575 existing unit tests still passing**
- [ ] **ALL 602 total tests still passing** (including integration)
- [ ] **New total: [575 + X]/[575 + X] unit passing, [602 + X]/[602 + X] total passing (100%)**
- [ ] **Database verification query confirms** changes active
- [ ] **Migration rollback tested** (`alembic downgrade -1` then `upgrade head` again)
- [ ] **Project plan document updated**

### For JSON_UPDATE Tasks (Task 9 Only):
- [ ] **Regression baseline captured** (575/575 unit, 602/602 total tests)
- [ ] **SQL dump reviewed** for correct production logic
- [ ] **JSON schema updated** to match SQL dump exactly
- [ ] **JSON changes documented** for manual review
- [ ] **Database verification confirms** no changes (already correct)
- [ ] **ALL 575 unit tests still passing** (no regression)
- [ ] **ALL 602 total tests still passing** (no regression)
- [ ] **Optional verification tests added** (if applicable)
- [ ] **Project plan document updated**

### For ALL Tasks:
- [ ] **100% test pass rate** - No failing tests
- [ ] **Zero regression** - Baseline maintained or exceeded

---

## Key Files to Review

### Architecture & Design
- `dev-docs/analysis/phase-4.7-db-schema-sync-3-plan.md` - **Task [TASK_NUMBER] Details** ⭐
- `dev-docs/analysis/phase-4.7-db-schema-sync-3-analysis.md` - Forensic Analysis
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - **Golden Master JSON**
- `dev-docs/db-design/aevofab-db-schema-dump-phase-4.6-post.sql` - **Production SQL Dump (Phase 4.6 Baseline)**
- `dev-docs/db-design/enum-vs-text-design-decision.md` - Design Decision for ENUM vs TEXT

### Backend Code
- `backend/app/models/[file].py` - [Model descriptions]

### Tests (Reference for Patterns)
- `backend/tests/test_check_constraints_task9.py` - CHECK constraint patterns
- `backend/tests/test_temporal_exclusion_constraints_task10.py` - EXCLUDE constraint patterns
- `backend/tests/test_citext_email.py` - Correct `select()/exec()` usage
- `backend/tests/conftest.py` - Test fixtures (`db_session`, `test_tenant`, etc.)

---

## Risk Assessment

**Data Validation Risk:** [LOW/MEDIUM/HIGH]
- [Risk description]
- **Mitigation:** [Strategy]

**Regression Risk:** [LOW/MEDIUM/HIGH]
- [Risk description for breaking existing tests]
- **Mitigation:** Maintain 575/602 baseline, test after every change, check alembic for audit.event

**JSON Documentation Risk:** [LOW (for JSON_UPDATE tasks)]
- JSON changes might not perfectly match SQL reality
- **Mitigation:** Founder manually reviews all JSON changes against SQL dump

---

## Notes

### Important Patterns to Follow
- **Virtual Environment Required:** All Python/pytest commands use `source .venv/bin/activate`
- **Use `db_session` Parameter:** NOT `session` (pytest fixture naming)
- **Use `select()/exec()` Pattern:** NOT `query()` (SQLModel standard, no deprecation warnings)
- **Check Alembic Migrations:** ALWAYS remove `audit.event` table creation if autogenerated
- **Dual Master Strategy:** JSON is documentation authority, SQL dump is runtime authority
- **Zero Regression Policy:** All 575 unit + 602 total tests MUST pass after changes

### Phase 4.7 Specific
- **Final production alignment** - Last schema sync before deployment
- **Most tasks are migrations** - Unlike 4.6, only Task 9 is JSON-only
- **Focus on architectural decisions** - ENUM standardization, type safety, data integrity
- **Critical issues first** - Priority order: CRITICAL → HIGH → MEDIUM → LOW
- **Pre-validate all data** - Run validation queries BEFORE applying constraints
- **Test NULL handling** - If field is nullable, test both NULL and valid values

### If You Get Stuck
- Check the SQL dump for exact production definitions
- Review Phase 4.5/4.6 completed tasks for patterns
- Use `postgres-local` MCP server to query database in real-time
- Search existing tests for `db_session` and `exec()` patterns
- Review the "Best Practices" section at the top of this template
- Remember: Only Task 9 is JSON-only, all others are migrations

---

## Example Task Flow

### For MIGRATION Tasks (Most Phase 4.7 Tasks):

```bash
# 1. Baseline - Capture starting point
cd backend
source .venv/bin/activate

# Run unit tests (no integration)
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Record: 575 passed

# Run all tests (including integration)
pytest tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Record: 602 passed

# 2. Pre-migration data validation
# Run validation queries from task description
# Example: SELECT id, type FROM customer WHERE type NOT IN ('person', 'company');
# If rows returned, clean data before proceeding

# 3. Update SQLModel classes
# Edit backend/app/models/[file].py
# - Use db_session parameter
# - Use sa_column=Column(BigInteger) if needed
# - Add CHECK constraints to __table_args__

# 4. Generate migration
alembic revision --autogenerate -m "phase_4_7_[task_name]_task[N]"

# 5. ⚠️ CRITICAL: Review migration file
# Open backend/migrations/versions/[timestamp]_phase_4_7_[task_name]_task[N].py
# Search for 'audit' and 'event'
# DELETE any op.create_table('event', ... schema='audit') blocks
# Verify your actual changes are present
# Add pre-migration validation queries as comments

# 6. Apply migration
alembic upgrade head

# 7. Create test suite
# Create backend/tests/test_phase_4_7_[task_name].py
# - Use db_session: Session parameter
# - Use select() with exec()
# - Test valid cases, invalid cases, NULL handling

# 8. Run new tests
pytest tests/test_phase_4_7_[task_name].py -v
# All new tests should pass

# 9. Regression check - Ensure no breaks
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Expected: [575 + X] passed

pytest tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Expected: [602 + X] passed

# 10. Rollback test - Verify downgrade works
alembic downgrade -1
alembic upgrade head
pytest tests/ -v  # Should still pass

# 11. Update docs
# Edit dev-docs/analysis/phase-4.7-db-schema-sync-3-plan.md
# Mark task as complete with test results
```

### For JSON_UPDATE Tasks (Task 9 Only):

```bash
# 1. Baseline - Capture starting point
cd backend
source .venv/bin/activate

# Run unit tests
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Record: 575 passed

# Run all tests
pytest tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Record: 602 passed

# 2. Review SQL dump for exact definition
grep -A 30 "CREATE FUNCTION guard_tenant_user_platform_isolation" \
  dev-docs/db-design/aevofab-db-schema-dump-phase-4.6-post.sql

# OR for triggers:
grep -A 10 "CREATE TRIGGER trg_user_endpoint" \
  dev-docs/db-design/aevofab-db-schema-dump-phase-4.6-post.sql

# 3. Update JSON schema
# Edit dev-docs/db-design/pilot-db-schema-v2.6h.json
# Find the function/trigger definition
# Update to match SQL dump exactly
# Maintain proper JSON escaping

# 4. Document changes for founder review
# Create summary:
# - What changed
# - Why (align with production SQL)
# - Line numbers in JSON file

# 5. Verify database (no changes expected)
# Use postgres-local MCP server:
# SELECT prosrc FROM pg_proc WHERE proname = 'guard_tenant_user_platform_isolation';
# Confirm matches JSON update

# 6. Regression check - No tests should break
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Expected: 575 passed (no change)

pytest tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Expected: 602 passed (no change)

# 7. Optional verification tests
# Add only if documenting previously untested behavior
# Use db_session and select()/exec() patterns

# 8. Update docs
# Edit dev-docs/analysis/phase-4.7-db-schema-sync-3-plan.md
# Mark task as complete
```

---

## Questions to Ask

**Before starting:**
1. Is this a MIGRATION or JSON_UPDATE task?
2. Have I captured the 575/575 unit and 602/602 total baselines?
3. If JSON_UPDATE: Have I located the correct definition in the SQL dump?
4. If MIGRATION: Have I validated existing data won't violate new constraints?
5. If MIGRATION: Do I understand which fields are nullable vs non-nullable?

**During implementation:**
1. Am I using `db_session` parameter (NOT `session`) in tests?
2. Am I using `select()/exec()` pattern (NOT `query()`) in tests?
3. After running `alembic revision --autogenerate`, did I check for and remove `audit.event` table creation?
4. For JSON_UPDATE: Am I documenting all changes for founder review?
5. For MIGRATION: Are my tests consistent with existing test patterns?
6. For MIGRATION: Am I testing NULL handling for nullable fields?

**After implementation:**
1. Do I have 100% test pass rate on BOTH unit tests (575) and total tests (602)?
2. For JSON_UPDATE: Did baseline stay at 575/602 (no regression)?
3. For MIGRATION: Did baseline increase by exactly the tests I added (575+X/602+X)?
4. Have I updated the project plan document?
5. For JSON_UPDATE: Have I provided a clear change list for founder review?
6. Have I tested migration rollback (`alembic downgrade -1`)?

---

**Ready to Begin!** 🚀

### MIGRATION Task Checklist (Most Phase 4.7 Tasks):
1. ✅ Capture baseline (575/575 unit, 602/602 total)
2. 🔍 Validate existing data (run pre-migration queries)
3. 🛠️ Update SQLModel classes (use `db_session`, `sa_column` if needed)
4. 📝 Generate migration (`alembic revision --autogenerate`)
5. ⚠️ **CRITICAL: Remove `audit.event` table from migration if present**
6. ✅ Apply migration (`alembic upgrade head`)
7. 🧪 Create comprehensive tests (use `db_session`, `select()/exec()`, test NULL)
8. 🔄 Run regression tests (575+X unit, 602+X total)
9. ↩️ Test rollback (`alembic downgrade -1`, then `upgrade head`)
10. 📚 Update project plan

### JSON_UPDATE Task Checklist (Task 9 Only):
1. ✅ Capture baseline (575/575 unit, 602/602 total)
2. 📖 Review SQL dump for correct logic
3. ✏️ Update JSON schema to match SQL exactly
4. 📋 Document JSON changes for founder review
5. ✅ Verify database (no changes expected)
6. 🔄 Run regression tests (expect 575/602 - no change)
7. 📚 Update project plan

Remember: Phase 4.7 is about **final production alignment** - architectural decisions and data integrity enforcement. This is the last major schema sync before deployment. Be thorough, validate data, and always check for the `audit.event` table issue in migrations!
