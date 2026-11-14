# Task [TASK_NUMBER]: [TASK_NAME]

**Reference:** `dev-docs/analysis/phase-4.5-db-schema-sync-to-design-plan.md` - Task [TASK_NUMBER]
**Authority:** `dev-docs/db-design/pilot-db-schema-v2.6h.json`
**Type:** Phase [PHASE_NUMBER] - [CATEGORY]
**Priority:** [HIGH/MEDIUM/LOW]

---

## Context

We're building AevoFab AI, an AI-powered SaaS platform for electrical contractors with voice-controlled quoting and QuickBooks integration. Following the 80/20 rule to reach MVP quickly.

This is a **Phase [PHASE_NUMBER] [category] task** to achieve 100% alignment between our SQLModel implementations and the Golden Master Database Schema (v2.6h JSON). This is NOT a new feature - it's surgical corrections to ensure database-level data integrity and business rule enforcement.

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

**Phase 3: Data Integrity (PARTIAL):**
- ✅ Task 8: Missing unique constraints (4/4 complete)
- ✅ Task 9: Missing check constraints (9/9 complete)
- 📋 Task 10: Missing temporal exclusion constraints (not started)

**Current Test Baseline:** [BASELINE_COUNT] tests passing (100%)
**See:** `dev-docs/analysis/phase-4.5-db-schema-sync-to-design-plan.md` for full context

---

## Current Task: [TASK_NAME]

**Effort:** [X] days
**Gap Reference:** [SECTION_REFERENCE]

[TASK_DESCRIPTION - 2-3 sentences explaining what this task accomplishes]

### What Needs to Be Fixed

[TABLE OF GAPS/ISSUES]

| # | Entity/Component | Issue | Impact | Complexity |
|---|------------------|-------|--------|------------|
| **1** | `EntityName` | [Issue description] | [Impact] | LOW/MEDIUM/HIGH |
| **2** | ... | ... | ... | ... |

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

**Record the output:** `[BASELINE_NON_INTEGRATION_COUNT] tests passing`

Example output:
```
========================== 490 passed in 45.23s ==========================
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
========================== 517 passed in 62.11s ==========================
```

### Step 4: Document Your Baseline

**Write down these numbers before proceeding:**
- Non-Integration Baseline: `___/___` passing
- Total Tests Baseline: `___/___` passing

**These are your regression checkpoints. All these tests MUST still pass after your work.**

---

## Requirements

### 1. Implementation Details

[DETAILED IMPLEMENTATION INSTRUCTIONS FOR EACH GAP]

#### Gap 1: [GAP_NAME]

**Problem:** [Detailed description of the issue]

**SQLModel Fix:**
```python
# backend/app/models/[file].py
from sqlalchemy import [imports]

class ClassName:
    __tablename__ = "[table_name]"
    __table_args__ = (
        [Constraint definitions],
    )
    # ... existing fields ...
```

**Migration SQL:**
```sql
-- Pre-migration check (if applicable)
[VALIDATION QUERY]

-- Add constraint/modification
[ALTER TABLE STATEMENT]
```

---

[REPEAT FOR EACH GAP]

---

### 2. Database Query Tools

**You have access to the postgres-local MCP server for direct database queries:**

```python
# Example: Query to check for duplicates
await mcp__postgres_local__query({
    "sql": """
        SELECT [columns], COUNT(*) as count
        FROM [table]
        GROUP BY [columns]
        HAVING COUNT(*) > 1
    """
})
```

Use this tool to:
- Validate data before applying constraints
- Verify constraints exist after migration
- Debug migration issues
- Confirm test data state

---

### 3. Implementation Order

Execute in this exact sequence:

1. **✅ Establish Regression Baseline** (see "Before You Start" section above)

2. **Pre-Migration Data Validation**
   - Run validation queries to check for constraint violations
   - Clean up any invalid data found
   - Document any data cleanup performed

3. **Update SQLModel Classes**
   - Modify `backend/app/models/[file].py`
   - Add necessary imports (`CheckConstraint`, `UniqueConstraint`, etc.)
   - Update `__table_args__` with new constraints

4. **Generate Alembic Migration**
   ```bash
   cd backend
   source .venv/bin/activate
   alembic revision --autogenerate -m "[migration_description]"
   ```

5. **Review & Enhance Migration**
   - Verify all changes are captured
   - Add any manual SQL needed (PL/pgSQL functions, complex constraints)
   - Add pre-migration validation checks if applicable
   - Ensure downgrade() is complete

6. **Apply Migration**
   ```bash
   alembic upgrade head
   ```

7. **Create Test Suite**
   - Create `backend/tests/test_[task_name].py`
   - Write comprehensive tests (see Test Requirements below)
   - **CRITICAL:** Use `session.query()` NOT `session.exec()` to avoid deprecation warnings

8. **Run New Tests**
   ```bash
   pytest tests/test_[task_name].py -v
   ```

9. **Run Regression Tests** (see "After You Complete" section below)

10. **Update Documentation** (see Documentation Update section below)

---

### 4. Test Requirements

**⚠️ ZERO FAILING TESTS POLICY:**
- **ALL [BASELINE_COUNT] existing tests MUST still pass** (baseline cannot regress)
- **ALL new tests MUST pass** (schema sync verification)
- **Target: [NEW_TOTAL]/[NEW_TOTAL] passing (100%)**

**Test File:** `backend/tests/test_[task_name].py`

**Test Standards:**

```python
"""
Test Suite: Phase [PHASE_NUMBER] Task [TASK_NUMBER] - [TASK_NAME]
Tests [description] from Golden Master v2.6h
"""
import pytest
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from app.models.[module] import [Models]

# ⚠️ CRITICAL: Use session.query() NOT session.exec()
# This avoids deprecation warnings

class Test[FeatureName]:
    """[Description of what this test class covers]"""
    
    def test_[scenario]_valid(self, session: Session, test_tenant, test_user):
        """[Description - valid data should be accepted]"""
        # Use session.query() pattern
        entity = [Entity](
            field1="value1",
            field2="value2"
        )
        session.add(entity)
        session.commit()
        
        # Verify using session.query()
        result = session.query([Entity]).filter([Entity].id == entity.id).first()
        assert result is not None
        assert result.field1 == "value1"
    
    def test_[scenario]_invalid(self, session: Session, test_tenant, test_user):
        """[Description - invalid data should be rejected]"""
        entity = [Entity](
            field1="invalid_value",  # Violates constraint
            field2="value2"
        )
        session.add(entity)
        
        with pytest.raises(IntegrityError) as exc_info:
            session.commit()
        assert "[constraint_name]" in str(exc_info.value)
```

**Required Test Coverage (Minimum [X] Tests):**
- [ ] Valid data acceptance tests
- [ ] Invalid data rejection tests (constraint violations)
- [ ] Boundary condition tests
- [ ] NULL handling tests (if applicable)
- [ ] Tenant isolation tests (multi-tenant scenarios)
- [ ] Edge cases specific to the constraint type

**Test Fixtures:**
Review `backend/tests/conftest.py` for available fixtures:
- `session` - Database session with auto-rollback
- `test_tenant` - Test tenant record
- `test_user` - Test user record
- `test_customer` - Test customer record
- Add new fixtures if needed following existing patterns

---

### 5. Database Verification

**After Migration Applied:**

Use the MCP server or psql to verify constraints:

```sql
-- Verify constraints exist
SELECT 
    conname AS constraint_name,
    conrelid::regclass AS table_name,
    contype AS constraint_type,
    pg_get_constraintdef(oid) AS definition
FROM pg_constraint
WHERE conname IN (
    '[constraint_name_1]',
    '[constraint_name_2]'
)
ORDER BY conname;

-- Expected output:
-- [constraint_name_1] | [table] | [type] | [definition]
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

**Expected:** `[BASELINE_NON_INTEGRATION_COUNT + NEW_TEST_COUNT] passed`

Example: If baseline was 490 and you added 12 tests → expect 502 passed

### Step 3: Run ALL Tests (Including Integration)

```bash
# Run ALL tests
pytest tests/ -v

# Concise output
pytest tests/ -v 2>&1 | grep -E "(passed|failed|===)" | tail -5
```

**Expected:** `[BASELINE_TOTAL_COUNT + NEW_TEST_COUNT] passed`

Example: If baseline was 517 and you added 12 tests → expect 529 passed

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

Find Task [TASK_NUMBER] section and update with:

```markdown
### Task [TASK_NUMBER]: [TASK_NAME]

**Status:** ✅ COMPLETE (YYYY-MM-DD)
**Effort:** [X] days (actual)
**Priority:** [HIGH/MEDIUM/LOW]
**Gap Reference:** [Section reference]

**Completed [Count] [constraints/functions/fixes]:**
- ✅ [Item 1 description]
- ✅ [Item 2 description]
- ✅ [Item 3 description]

**Implementation Summary:**

#### [Component 1 Name]
- Modified: `backend/app/models/[file].py`
- Added: [What was added]
- Test: `test_[name]` ✅ PASSING

[REPEAT FOR EACH COMPONENT]

**Migration:** `YYYY_MM_DD_HHMM-[hash]_[description].py`
**Test Suite:** `test_[task_name].py` - [X] tests
**Final Test Results:** [NEW_TOTAL]/[NEW_TOTAL] tests passing (100%)

**Database Verification:**
- All [X] constraints confirmed active
- Migration upgrade/downgrade tested successfully
- No data corruption detected

**Test Coverage Breakdown:**
- New tests added: [X]
- Baseline maintained: [BASELINE_COUNT]
- Total passing: [NEW_TOTAL]/[NEW_TOTAL] (100%)

**Key Implementation Notes:**
- [Important decision or issue encountered]
- [Workaround or fix applied]
- [Future consideration]
```

---

## Success Criteria

**MUST COMPLETE ALL BEFORE MARKING TASK AS DONE:**

- [ ] **Regression baseline captured** (non-integration and total test counts recorded)
- [ ] **Pre-migration data validation completed** (no constraint violations in existing data)
- [ ] **All SQLModel classes updated** with necessary constraints/modifications
- [ ] **Alembic migration created** using autogenerate
- [ ] **Migration applied successfully** (`alembic upgrade head` completes without errors)
- [ ] **All [X] new tests written and passing**
- [ ] **Use session.query() in all tests** (not session.exec() - avoids deprecation warnings)
- [ ] **ALL existing tests still passing** - Zero regression
- [ ] **Non-integration tests:** [BASELINE + NEW] passing
- [ ] **Total tests:** [BASELINE + NEW] passing
- [ ] **100% test pass rate** - No failing tests
- [ ] **Database verification query** confirms all changes active
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
- `dev-docs/analysis/phase-4.5-db-schema-sync-to-design-plan.md` - **Task [TASK_NUMBER] Details** ⭐
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - **GOLDEN MASTER**
- `dev-docs/db-design/aevofab-db-process-v2.6h.md` - Database operations

### Backend Code (Files to Modify)
- `backend/app/models/[file].py` - [Model descriptions]

### Migration (To Create)
- `backend/migrations/versions/YYYY_MM_DD_HHMM-*_[migration_name].py`

### Tests (To Create)
- `backend/tests/test_[task_name].py` - [X] tests minimum

---

## Risk Assessment

**Data Validation Risk:** [LOW/MEDIUM/HIGH]
- [Risk description]
- **Mitigation:** [Strategy]

**Performance Impact:** [LOW/MEDIUM/HIGH]
- [Impact description]
- **Measurement:** [How to measure]

**Rollback Complexity:** [LOW/MEDIUM/HIGH]
- [Rollback considerations]
- **Testing:** [Rollback test plan]

---

## Notes

- **Virtual Environment Required:** All Python/pytest commands use `source .venv/bin/activate`
- **MCP Server Available:** Use `postgres-local` MCP server for direct database queries
- **Deprecation Warnings:** Use `session.query()` not `session.exec()` in all tests
- **Regression Testing:** Capture baseline BEFORE, verify AFTER - both non-integration and total
- **Golden Master Authority:** The JSON schema is the single source of truth
- **Zero Regression Policy:** All existing tests MUST still pass after changes
- **Cost Impact:** [Cost considerations if any]
- **Production Safe:** [Backward compatibility notes]

**Important Patterns:**
- [Pattern 1 to follow]
- [Pattern 2 to follow]

**If you get stuck:**
- Check the Golden Master JSON for exact specifications
- Review similar completed tasks (Tasks 8, 9) for patterns
- Use MCP server to query database state
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
# Record: ___ passed

# 3. Capture total baseline
pytest tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Record: ___ passed

# ============================================
# PHASE 2: VALIDATE DATA
# ============================================

# 4. Check for data that would violate constraints
# [Use MCP server or direct SQL queries]

# 5. Clean up any invalid data found
# [Document cleanup performed]

# ============================================
# PHASE 3: IMPLEMENT CHANGES
# ============================================

# 6. Review current model structure
grep -A 20 "class [ClassName]" backend/app/models/[file].py

# 7. Implement SQLModel changes
# [Edit backend/app/models/[file].py]

# 8. Generate migration
alembic revision --autogenerate -m "[description]"

# 9. Review and enhance migration
cat backend/migrations/versions/[timestamp]_*.py

# 10. Apply migration
alembic upgrade head

# ============================================
# PHASE 4: VERIFY DATABASE
# ============================================

# 11. Verify constraints in database (using MCP server)
# [Query pg_constraint to confirm]

# ============================================
# PHASE 5: TEST
# ============================================

# 12. Create test file
# [Create backend/tests/test_[task_name].py]
# REMEMBER: Use session.query() not session.exec()

# 13. Run new tests only
pytest tests/test_[task_name].py -v
# Expected: [X] passed

# ============================================
# PHASE 6: REGRESSION VERIFICATION
# ============================================

# 14. Run non-integration regression tests
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Expected: [BASELINE + NEW] passed

# 15. Run ALL tests (full regression)
pytest tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Expected: [BASELINE + NEW] passed

# 16. Verify 100% pass rate
# If any failures → FIX IMMEDIATELY

# ============================================
# PHASE 7: ROLLBACK TEST
# ============================================

# 17. Test migration reversibility
alembic downgrade -1
alembic upgrade head
pytest tests/test_[task_name].py -v
# Expected: Still [X] passed

# ============================================
# PHASE 8: DOCUMENTATION
# ============================================

# 18. Update project plan document
# [Edit phase-4.5-db-schema-sync-to-design-plan.md]
# Add completion details, test counts, implementation notes
```

---

## Questions to Ask

**Before starting:**
1. Have I reviewed the Golden Master JSON for ALL [constraints/functions/etc.] in scope?
2. Have I captured the regression baseline (non-integration AND total test counts)?
3. Have I activated the virtual environment?
4. Are all test fixtures available in conftest.py?

**During implementation:**
1. Am I using `session.query()` instead of `session.exec()` in tests?
2. Have I validated existing data won't violate new constraints?
3. Are all new tests passing?
4. Am I documenting decisions and issues as I go?

**After implementation:**
1. Did I run BOTH non-integration and total regression tests?
2. Do I have 100% test pass rate (no failures)?
3. Did baseline tests increase by exactly the number of new tests I added?
4. Have I updated the project plan document?
5. Can the migration be rolled back cleanly?

---

**Ready to Begin!** 🚀

1. ✅ Capture regression baseline (non-integration and total)
2. 🔍 Validate existing data
3. 🛠️ Implement SQLModel changes
4. 📝 Generate and enhance migration
5. ✅ Create comprehensive tests (use session.query())
6. 🔄 Run regression tests
7. 📚 Update project plan document

Remember: Virtual environment required, use postgres-local MCP server, avoid session.exec(), maintain 100% pass rate!
