# Task [TASK_NUMBER]: [TASK_NAME]

**Reference:** `dev-docs/analysis/phase-4.6-db-schema-sync-2-plan.md` - Phase [PHASE_NUMBER], Task [TASK_NUMBER]
**Authority (Dual Master):**
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - Golden Master JSON
- `dev-docs/db-design/aevofab-db-schema-dump-phase-4.6.sql` - Production SQL Dump
**Type:** Phase [PHASE_NUMBER] - [CATEGORY]
**Priority:** [HIGH/MEDIUM/LOW]
**Change Type:** [MIGRATION/JSON_UPDATE/DOCUMENTATION]

---

## Context

This is **Phase 4.6 - DB Sync v#2**, a follow-up reconciliation after completing Phase 4.5. A forensic comparison between the production SQL dump and the Golden Master JSON revealed new inconsistencies. This task merges the best of both sources into a unified schema.

**Key Principle:** This is about **reconciliation and documentation**, not new features. Most Phase 2+ tasks are JSON updates only (no database migrations).

---

## What Was Completed in Phase 4.5

**Phase 4.5 Status:** ✅ COMPLETE (March 30 - April 1, 2026)
- ✅ 572/572 tests passing (100%)
- ✅ 100% alignment between physical database and Golden Master JSON achieved
- ✅ All unique, check, and temporal exclusion constraints implemented
- ✅ All 293 triggers verified and functional

**Current Baseline:** 572/572 tests passing (100%)

**See:** `dev-docs/analysis/phase-4.5-db-schema-sync-to-design-plan.md` for full Phase 4.5 history

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

You have access to the postgres-local MCP server to query the DB directly, in read-only mode.

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
# Run full test suite but without the integration tests
# Run all tests EXCEPT integration tests
pytest --ignore=tests/integration/ tests/ -v

# Concise output to capture baseline count
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed|===)" | tail -5
```

**Record the output:** `555/555 tests passing` (Phase 4.6 baseline)

### Step 3: Document Your Baseline

**Write down this number before proceeding:**
- Baseline: `555/555` passing

**This is your regression checkpoint. ALL these tests MUST still pass after your work.**

---

## Requirements

### 1. Implementation Details

[IMPLEMENTATION INSTRUCTIONS - Choose appropriate section based on Change Type]

#### For MIGRATION Tasks (Phase 1 Only)

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

#### For JSON_UPDATE Tasks (Phase 2, 3, 4)

**Problem:** [Description of JSON schema gap]

**SQL Database Reality (What's Actually Working):**
```sql
-- Production SQL (from phase-4.6 dump)
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

1. **✅ Establish Regression Baseline** (572/572 tests)
2. **Review SQL Dump**
   - Read `dev-docs/db-design/aevofab-db-schema-dump-phase-4.6.sql`
   - Locate the production function/definition
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
   pytest tests/ -v
   # Expected: 572/572 passing (no change)
   ```
7. **Optional: Add Verification Tests**
   - Only if testing a newly documented behavior
   - Keep consistent with existing test patterns
8. **Update Documentation**

---

### 3. Test Requirements

**⚠️ ZERO REGRESSION POLICY:**
- **ALL 572 existing tests MUST still pass**
- **New tests (if added) MUST pass**
- **Target: 100% pass rate**

#### For MIGRATION Tasks

**Test File:** `backend/tests/test_[task_name].py`

**Required Coverage (Minimum [X] Tests):**
```python
"""
Test Suite: Phase 4.6 Task [N] - [TASK_NAME]
Tests [description] - reconciliation after Phase 4.5
"""
import pytest
from sqlmodel import Session
from sqlalchemy.exc import IntegrityError

from app.models.[module] import [Models]

# ⚠️ Use session.query() NOT session.exec()

class Test[FeatureName]:
    """[Description]"""
    
    def test_[scenario]_valid(self, session: Session, test_tenant, test_user):
        """Valid data should be accepted"""
        entity = Entity
        session.add(entity)
        session.commit()
        
        result = session.query([Entity]).filter([Entity].id == entity.id).first()
        assert result is not None
    
    def test_[scenario]_invalid(self, session: Session, test_tenant, test_user):
        """Invalid data should be rejected"""
        entity = Entity
        session.add(entity)
        
        with pytest.raises(IntegrityError) as exc_info:
            session.commit()
        assert "[constraint_name]" in str(exc_info.value)
```

**Test Patterns to Follow:**
- Review `backend/tests/test_unique_constraints_task8.py`
- Review `backend/tests/test_check_constraints_task9.py`
- Use fixtures from `backend/tests/conftest.py`

---

#### For JSON_UPDATE Tasks

**No New Tests Required (Usually)**
- The database logic already works (proven by 555/555 passing tests)
- This is documentation alignment only

**Optional Verification Tests:**
- Add ONLY if documenting previously untested behavior
- Keep minimal and consistent with existing patterns
- Example: Test that `clock_timestamp()` produces monotonic timestamps

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
   - **Reason:** Backport `clock_timestamp()` optimization from production SQL

2. **Function: `[another_function]`**
   - **Location:** Line [Y], `functions` array
   - **Before:** `WHERE quote_id = $1`
   - **After:** `WHERE quote_id = $1 AND is_active = true`
   - **Reason:** Add active record filter (production-tested logic)

3. **Constraint: `[constraint_name]`**
   - **Location:** Line [Z], table `[table_name]`, `check_constraints` array
   - **Before:** Simple regex `^[^@\s]+@[^@\s]+$`
   - **After:** Strict regex `^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$`
   - **Reason:** Standardize on SQL production regex

### Verification:

- [ ] All JSON changes align with `aevofab-db-schema-dump-phase-4.6.sql`
- [ ] No functional database changes made (JSON doc only)
- [ ] All 572 tests still passing (no regression)
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
- **For MIGRATION tasks:** `[572 + NEW_TEST_COUNT] passed`
- **For JSON_UPDATE tasks:** `572 passed` (no change)

### Step 3: Verify 100% Pass Rate

**If ANY tests fail:**
1. Identify failing tests
2. Determine if new or existing tests
3. Fix ALL failures before proceeding
4. Re-run until 100% pass rate

**For JSON_UPDATE tasks:**
- If existing tests fail → Your JSON changes revealed a mismatch (investigate)
- If tests still pass → JSON documentation is correct

---

## Documentation Update

### Update Project Plan Document

**File to Update:** `dev-docs/analysis/phase-4.6-db-schema-sync-2-plan.md`

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
- Test Suite: `test_[name].py` - [X] tests ✅
- Final Results: [572 + X]/[572 + X] tests passing (100%)

[For JSON_UPDATE tasks:]
- Updated: `pilot-db-schema-v2.6h.json`
- Changes: [X] functions/constraints backported from SQL
- Database: No changes (already correct)
- Final Results: 572/572 tests passing (100% - no regression)

**Key Changes:**
- ✅ [Change 1]
- ✅ [Change 2]

**Verification:**
- [How correctness was verified]
```

---

## Success Criteria

**MUST COMPLETE ALL BEFORE MARKING TASK AS DONE:**

### For MIGRATION Tasks (Phase 1):
- [ ] **Regression baseline captured** (572/572 tests)
- [ ] **Pre-migration data validation completed**
- [ ] **SQLModel classes updated** with new constraints/tables
- [ ] **Alembic migration created** using autogenerate
- [ ] **Migration applied successfully** (`alembic upgrade head`)
- [ ] **All [X] new tests written and passing**
- [ ] **Use session.query() in tests** (not session.exec())
- [ ] **ALL 572 existing tests still passing**
- [ ] **New total: [572 + X]/[572 + X] passing (100%)**
- [ ] **Database verification query confirms** changes active
- [ ] **Migration rollback tested** (`alembic downgrade -1`)
- [ ] **Project plan document updated**

### For JSON_UPDATE Tasks (Phases 2, 3, 4):
- [ ] **Regression baseline captured** (572/572 tests)
- [ ] **SQL dump reviewed** for correct production logic
- [ ] **JSON schema updated** to match SQL dump
- [ ] **JSON changes documented** for manual review
- [ ] **Database verification confirms** no changes (already correct)
- [ ] **ALL 572 tests still passing** (no regression)
- [ ] **Optional verification tests added** (if applicable)
- [ ] **Project plan document updated**

### For ALL Tasks:
- [ ] **100% test pass rate** - No failing tests
- [ ] **Zero regression** - Baseline maintained or exceeded

---

## Key Files to Review

### Architecture & Design
- `dev-docs/analysis/phase-4.6-db-schema-sync-2-plan.md` - **Task [TASK_NUMBER] Details** ⭐
- `dev-docs/analysis/phase-4.6-db-schema-sync-2-analysis.md` - Forensic Analysis
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - **Golden Master JSON**
- `dev-docs/db-design/aevofab-db-schema-dump-phase-4.6.sql` - **Production SQL Dump**

### Backend Code
- `backend/app/models/[file].py` - [Model descriptions]

### Tests (Reference for Patterns)
- `backend/tests/test_unique_constraints_task8.py`
- `backend/tests/test_check_constraints_task9.py`
- `backend/tests/conftest.py` - Test fixtures

---

## Risk Assessment

**Data Validation Risk:** [LOW/MEDIUM/HIGH]
- [Risk description]
- **Mitigation:** [Strategy]

**Regression Risk:** [LOW/MEDIUM/HIGH]
- [Risk description for breaking existing tests]
- **Mitigation:** Maintain 572/572 baseline, test after every change

**JSON Documentation Risk:** [LOW (for JSON_UPDATE tasks)]
- JSON changes might not perfectly match SQL reality
- **Mitigation:** Founder manually reviews all JSON changes against SQL dump

---

## Notes

### Important Patterns to Follow
- **Virtual Environment Required:** All Python/pytest commands use `source .venv/bin/activate`
- **Deprecation Warnings:** Use `session.query()` not `session.exec()` in tests
- **Dual Master Strategy:** JSON is documentation authority, SQL dump is runtime authority
- **Phase 2+ = JSON Only:** Most tasks after Phase 1 require NO database migrations
- **Zero Regression Policy:** All 572 existing tests MUST pass after changes

### Phase 4.6 Specific
- **This is reconciliation work** - fixing drift found after Phase 4.5
- **Database is usually correct** - most fixes are JSON documentation updates
- **Simpler than Phase 4.5** - focused, surgical changes
- **Test consistency critical** - new tests must match existing patterns

### If You Get Stuck
- Check the SQL dump for exact production definitions
- Review completed Phase 4.5 tasks for patterns
- Use `postgres-local` MCP server to query database
- Verify JSON changes line-by-line against SQL dump
- Remember: Phase 2+ tasks should NOT create migrations

---

## Example Task Flow

### For MIGRATION Tasks (Phase 1):

```bash
# 1. Baseline
cd backend
source .venv/bin/activate
pytest tests/ -v 2>&1 | grep passed | tail -1
# Record: 572 passed

# 2. Validate data
# [Check for constraint violations]

# 3. Update SQLModel
# [Edit backend/app/models/[file].py]

# 4. Generate migration
alembic revision --autogenerate -m "[task_name]_task[N]"

# 5. Apply migration
alembic upgrade head

# 6. Create tests
# [Create backend/tests/test_[task_name].py]

# 7. Run new tests
pytest tests/test_[task_name].py -v

# 8. Regression check
pytest tests/ -v 2>&1 | grep passed | tail -1
# Expected: [572 + X] passed

# 9. Rollback test
alembic downgrade -1
alembic upgrade head

# 10. Update docs
# [Edit phase-4.6-db-schema-sync-2-plan.md]
```

### For JSON_UPDATE Tasks (Phases 2, 3, 4):

```bash
# 1. Baseline
cd backend
source .venv/bin/activate
pytest tests/ -v 2>&1 | grep passed | tail -1
# Record: 572 passed

# 2. Review SQL dump
grep -A 20 "CREATE FUNCTION [function_name]" \
  dev-docs/db-design/aevofab-db-schema-dump-phase-4.6.sql

# 3. Update JSON schema
# [Edit dev-docs/db-design/pilot-db-schema-v2.6h.json]
# Copy correct logic from SQL dump

# 4. Document changes
# [Create JSON change summary for founder review]

# 5. Verify database (no changes expected)
# [Use postgres-local MCP to confirm function exists]

# 6. Regression check
pytest tests/ -v 2>&1 | grep passed | tail -1
# Expected: 572 passed (no change)

# 7. Optional verification tests
# [Add only if testing newly documented behavior]

# 8. Update docs
# [Edit phase-4.6-db-schema-sync-2-plan.md]
```

---

## Questions to Ask

**Before starting:**
1. Is this a MIGRATION or JSON_UPDATE task?
2. Have I captured the 572/572 baseline?
3. If JSON_UPDATE: Have I located the correct definition in the SQL dump?
4. If MIGRATION: Have I validated existing data won't violate new constraints?

**During implementation:**
1. Am I using `session.query()` (not `session.exec()`) in tests?
2. For JSON_UPDATE: Am I documenting all changes for founder review?
3. For MIGRATION: Are my tests consistent with existing test patterns?

**After implementation:**
1. Do I have 100% test pass rate?
2. For JSON_UPDATE: Did baseline stay at 572/572 (no regression)?
3. For MIGRATION: Did baseline increase by exactly the tests I added?
4. Have I updated the project plan document?
5. For JSON_UPDATE: Have I provided a clear change list for founder review?

---

**Ready to Begin!** 🚀

### MIGRATION Task Checklist:
1. ✅ Capture baseline (572/572)
2. 🔍 Validate existing data
3. 🛠️ Update SQLModel classes
4. 📝 Generate and apply migration
5. ✅ Create comprehensive tests
6. 🔄 Run regression tests
7. 📚 Update project plan

### JSON_UPDATE Task Checklist:
1. ✅ Capture baseline (572/572)
2. 📖 Review SQL dump for correct logic
3. ✏️ Update JSON schema to match SQL
4. 📋 Document JSON changes for review
5. ✅ Verify database (no changes)
6. 🔄 Run regression tests (expect 572/572)
7. 📚 Update project plan

Remember: Phase 4.6 is about **reconciliation**, not new features. Keep it simple, maintain test success, and document thoroughly!
