# Task 1: Convert `customer.type` from ENUM to TEXT

**Reference:** `dev-docs/analysis/phase-4.7-db-schema-sync-3-plan.md` - Phase 1, Task 1
**Authority (Dual Master):**
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - Golden Master JSON
- `dev-docs/db-design/aevofab-db-schema-dump-phase-4.6-post.sql` - Production SQL Dump (Phase 4.6 Baseline)
**Type:** Phase 1 - ENUM Standardization
**Priority:** HIGH
**Change Type:** MIGRATION

---

## Context

This is **Phase 4.7 - DB Sync v3**, a third forensic reconciliation after completing Phases 4.5 and 4.6. A comprehensive comparison between the latest SQL dump (`aevofab-db-schema-dump-phase-4.6-post.sql`) and the Golden Master JSON revealed **5 major remaining discrepancies** requiring final alignment before production deployment.

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

## Current Task: Convert `customer.type` from ENUM to TEXT

**Effort:** 0.5 days
**Gap Reference:** Phase 4.7 Analysis - Phase 1: Standardize Enumerated Types
**Change Type:** MIGRATION

The `customer.type` column currently uses the native PostgreSQL ENUM `customertype`, but the JSON schema and `enum-vs-text-design-decision.md` mandate TEXT + CHECK constraints for flexibility and SQLModel compatibility.

**Why This Matters:**
- ENUMs are harder to modify (require migrations to add values)
- Alembic autogenerate has issues with ENUM changes
- TEXT + CHECK provides same validation with better flexibility
- Aligns with architectural decision made in Phase 4.5

### What Needs to Be Fixed

| # | Component | Issue | Direction | Complexity |
|---|-----------|-------|-----------|------------|
| **1** | `customer.type` | Column uses native PostgreSQL ENUM `customertype` instead of TEXT + CHECK constraint | SQL→SQL | MEDIUM |
| **2** | `public.customertype` | Native ENUM type must be dropped after conversion | SQL→SQL | LOW |

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

---

## Requirements

### 1. Implementation Details

#### Problem: Native ENUM Type Used Instead of TEXT + CHECK

**Current Database State (WRONG):**
```sql
-- Native PostgreSQL ENUM exists
CREATE TYPE public.customertype AS ENUM ('person', 'company');

-- Column uses ENUM type
ALTER TABLE customer ALTER COLUMN type TYPE public.customertype;
```

**JSON Schema Specification (CORRECT):**
```json
{
  "name": "type",
  "type": "text",
  "nullable": false,
  "constraints": {
    "check": "type IN ('person', 'company')"
  }
}
```

**SQLModel Fix:**
```python
# backend/app/models/crm.py
from sqlalchemy import CheckConstraint

class Customer(TenantIsolatedMixin, SQLModel, table=True):
    __tablename__ = "customer"
    __table_args__ = (
        UniqueConstraint('tenant_id', 'display_name', name='uq_customer_tenant_display_name'),
        CheckConstraint(
            "type IN ('person', 'company')",
            name='customer_type_chk'
        ),
    )
    
    # Change from ENUM to TEXT (model already uses str, but DB has ENUM)
    type: str = Field(nullable=False)
```

**Migration SQL:**
```sql
-- Pre-migration validation
-- Check for invalid values (should be 0 rows)
SELECT id, type, COUNT(*)
FROM customer
WHERE type NOT IN ('person', 'company')
GROUP BY id, type;

-- Verify current value distribution
SELECT type, COUNT(*) FROM customer GROUP BY type;

-- Migration upgrade():
-- Step 1: Add temporary CHECK constraint (for safety before type change)
ALTER TABLE customer
ADD CONSTRAINT customer_type_chk_temp
CHECK (type::text IN ('person', 'company'));

-- Step 2: Convert column to TEXT
ALTER TABLE customer
ALTER COLUMN type TYPE text
USING type::text;

-- Step 3: Drop the ENUM type
DROP TYPE IF EXISTS public.customertype CASCADE;

-- Step 4: Rename temporary constraint
ALTER TABLE customer
DROP CONSTRAINT customer_type_chk_temp;

ALTER TABLE customer
ADD CONSTRAINT customer_type_chk
CHECK (type IN ('person', 'company'));

-- Migration downgrade():
-- Step 1: Recreate ENUM type
CREATE TYPE public.customertype AS ENUM ('person', 'company');

-- Step 2: Drop CHECK constraint
ALTER TABLE customer DROP CONSTRAINT customer_type_chk;

-- Step 3: Convert column back to ENUM
ALTER TABLE customer
ALTER COLUMN type TYPE public.customertype
USING type::public.customertype;
```

**Database Verification Query:**
```sql
-- Verify constraint exists after migration
SELECT conname, contype, pg_get_constraintdef(oid)
FROM pg_constraint
WHERE conname = 'customer_type_chk';

-- Verify ENUM type no longer exists
SELECT typname FROM pg_type WHERE typname = 'customertype';
-- Should return 0 rows

-- Verify column is TEXT type
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'customer' AND column_name = 'type';
-- Should show data_type = 'text'
```

---

### 2. Implementation Order

**For MIGRATION Tasks (Phase 1):**

1. **✅ Establish Regression Baseline** (575/575 unit, 602/602 total tests)
2. **Pre-Migration Data Validation**
   - Run validation queries
   - Verify no invalid values exist
3. **Update SQLModel Classes**
   - Modify `backend/app/models/crm.py`
   - Add CHECK constraint to `__table_args__`
4. **Generate Alembic Migration**
   ```bash
   cd backend
   source .venv/bin/activate
   alembic revision --autogenerate -m "phase_4_7_enum_to_text_customer_type_task1"
   ```
5. **Review & Enhance Migration**
   - ⚠️ **CRITICAL: Check for and remove `audit.event` table if present**
   - Verify ENUM → TEXT conversion captured
   - Add pre-migration validation queries as comments
   - Ensure downgrade() is complete
6. **Apply Migration**
   ```bash
   alembic upgrade head
   ```
7. **Create Test Suite**
   - Create `backend/tests/test_phase_4_7_customer_type_enum_to_text.py`
   - Use `db_session` NOT `session`
   - Use `select()/exec()` pattern
8. **Run New Tests**
   ```bash
   pytest tests/test_phase_4_7_customer_type_enum_to_text.py -v
   ```
9. **Run Regression Tests** (see "After You Complete" section)
10. **Update Documentation**

---

### 3. Test Requirements

**⚠️ ZERO REGRESSION POLICY:**
- **ALL 575 existing unit tests MUST still pass**
- **ALL 602 total tests (including integration) MUST still pass**
- **New tests MUST pass**
- **Target: 100% pass rate on both test suites**

**Test File:** `backend/tests/test_phase_4_7_customer_type_enum_to_text.py`

**Required Coverage (Minimum 5 Tests):**
```python
"""
Test Suite: Phase 4.7 Task 1 - Convert customer.type from ENUM to TEXT
Tests ENUM → TEXT + CHECK constraint migration for customer.type field

Reference: phase-4.7-db-schema-sync-3-plan.md - Phase 1, Task 1
"""
import pytest
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from app.models.crm import Customer

# ✅ CORRECT: Use db_session parameter and select()/exec() pattern

class TestCustomerTypeEnumToText:
    """Test customer.type uses TEXT + CHECK constraint instead of ENUM"""
    
    def test_customer_type_person_valid(self, db_session: Session, test_tenant):
        """Valid 'person' type should be accepted"""
        customer = Customer(
            tenant_id=test_tenant.id,
            type="person",
            display_name="John Doe"
        )
        db_session.add(customer)
        db_session.commit()
        
        # Use select() with exec() - NOT query()
        result = db_session.exec(
            select(Customer).where(Customer.id == customer.id)
        ).first()
        assert result is not None
        assert result.type == "person"
    
    def test_customer_type_company_valid(self, db_session: Session, test_tenant):
        """Valid 'company' type should be accepted"""
        customer = Customer(
            tenant_id=test_tenant.id,
            type="company",
            display_name="Acme Corp"
        )
        db_session.add(customer)
        db_session.commit()
        
        result = db_session.exec(
            select(Customer).where(Customer.id == customer.id)
        ).first()
        assert result is not None
        assert result.type == "company"
    
    def test_customer_type_invalid_rejected(self, db_session: Session, test_tenant):
        """Invalid type value should be rejected by CHECK constraint"""
        customer = Customer(
            tenant_id=test_tenant.id,
            type="business",  # Invalid value
            display_name="Test Business"
        )
        db_session.add(customer)
        
        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()
        assert "customer_type_chk" in str(exc_info.value)
        
        # Rollback to clean up failed transaction
        db_session.rollback()
    
    def test_customer_type_null_rejected(self, db_session: Session, test_tenant):
        """NULL type value should be rejected (nullable=False)"""
        customer = Customer(
            tenant_id=test_tenant.id,
            type=None,
            display_name="Test Customer"
        )
        db_session.add(customer)
        
        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()
        # Should fail on NOT NULL constraint
        db_session.rollback()
    
    def test_customer_type_is_text_not_enum(self, db_session: Session):
        """Verify database column is TEXT type, not ENUM"""
        # Query system catalog to verify column type
        result = db_session.exec(
            select(
                "SELECT data_type FROM information_schema.columns "
                "WHERE table_name = 'customer' AND column_name = 'type'"
            )
        ).first()
        
        # Should be 'text' not 'USER-DEFINED' (which indicates ENUM)
        assert result == ('text',) or result[0] == 'text'
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
- `utc_now` - Timezone-aware current timestamp function

---

### 4. JSON Change Tracking

**No JSON Schema Changes Required** - This is a database migration only. The JSON schema already correctly specifies TEXT + CHECK constraint.

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
- **For this MIGRATION task:** `[575 + 5] = 580 passed` (unit), `[602 + 5] = 607 passed` (total)
- **If ANY tests fail:** Fix ALL failures before proceeding

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

Find Phase 1, Task 1 and update with:

```markdown
### Task 1: Convert `customer.type` from ENUM to TEXT

**Status:** ✅ COMPLETE (2026-04-03)
**Effort:** 0.5 days (actual)
**Change Type:** MIGRATION

**Implementation Summary:**

- Modified: `backend/app/models/crm.py`
- Migration: `YYYY_MM_DD_HHMM-[hash]_phase_4_7_enum_to_text_customer_type_task1.py`
- Test Suite: `test_phase_4_7_customer_type_enum_to_text.py` - 5 tests ✅
- Final Results: 580/580 unit tests passing (100%), 607/607 total tests passing (100%)

**Key Changes:**
- ✅ Converted `customer.type` from PostgreSQL ENUM to TEXT
- ✅ Added CHECK constraint `customer_type_chk` to enforce valid values
- ✅ Dropped native ENUM type `public.customertype`
- ✅ Aligned with architectural decision from enum-vs-text-design-decision.md

**Verification:**
- Column type verified as TEXT via information_schema query
- CHECK constraint active and enforcing ('person', 'company') values
- Zero data loss during migration
- All 575 baseline tests still passing
```

---

## Success Criteria

**MUST COMPLETE ALL BEFORE MARKING TASK AS DONE:**

- [ ] **Regression baseline captured** (575/575 unit, 602/602 total tests)
- [ ] **Pre-migration data validation completed** (queries run, data clean)
- [ ] **SQLModel classes updated** with CHECK constraint in `__table_args__`
- [ ] **Used `db_session` parameter** (not `session`) in tests
- [ ] **Used `select()/exec()` pattern** (not `query()`) in tests
- [ ] **Alembic migration created** using autogenerate
- [ ] **⚠️ CRITICAL: Checked migration for `audit.event` table** and removed if present
- [ ] **Migration applied successfully** (`alembic upgrade head`)
- [ ] **All 5 new tests written and passing**
- [ ] **Tests use `db_session` parameter** and `select()/exec()` pattern
- [ ] **ALL 575 existing unit tests still passing**
- [ ] **ALL 602 total tests still passing** (including integration)
- [ ] **New total: 580/580 unit passing, 607/607 total passing (100%)**
- [ ] **Database verification query confirms** `customer.type` is TEXT with CHECK constraint
- [ ] **Database verification confirms** ENUM type `customertype` no longer exists
- [ ] **Migration rollback tested** (`alembic downgrade -1` then `upgrade head` again)
- [ ] **Project plan document updated**

---

## Key Files to Review

### Architecture & Design
- `dev-docs/analysis/phase-4.7-db-schema-sync-3-plan.md` - **Task 1 Details** ⭐
- `dev-docs/analysis/phase-4.7-db-schema-sync-3-analysis.md` - Forensic Analysis
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - **Golden Master JSON**
- `dev-docs/db-design/aevofab-db-schema-dump-phase-4.6-post.sql` - **Production SQL Dump (Phase 4.6 Baseline)**
- `dev-docs/db-design/enum-vs-text-design-decision.md` - **Design Decision for ENUM vs TEXT** ⭐

### Backend Code
- `backend/app/models/crm.py` - Customer model (contains `type` field)

### Tests (Reference for Patterns)
- `backend/tests/test_check_constraints_task9.py` - CHECK constraint patterns
- `backend/tests/test_citext_email.py` - Correct `select()/exec()` usage
- `backend/tests/conftest.py` - Test fixtures (`db_session`, `test_tenant`, etc.)

---

## Risk Assessment

**Data Validation Risk:** LOW
- ENUM values ('person', 'company') are simple and well-defined
- Existing data highly unlikely to have invalid values
- **Mitigation:** Pre-migration validation query confirms data is clean

**Regression Risk:** LOW
- ENUM → TEXT is a safe type conversion (no data loss)
- CHECK constraint provides same validation as ENUM
- **Mitigation:** Maintain 575/602 baseline, test after every change, check alembic for audit.event

**Rollback Risk:** MEDIUM
- Downgrade requires recreating ENUM type
- PostgreSQL doesn't allow easy TEXT → ENUM conversion if new values added
- **Mitigation:** Test rollback (`alembic downgrade -1`) before marking complete

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
- **Focus on architectural decisions** - ENUM standardization, type safety, data integrity
- **Critical issues first** - Priority order: CRITICAL → HIGH → MEDIUM → LOW
- **Pre-validate all data** - Run validation queries BEFORE applying constraints

### If You Get Stuck
- Check the SQL dump for current ENUM definition
- Review Phase 4.5/4.6 completed tasks for patterns
- Use `postgres-local` MCP server to query database in real-time
- Search existing tests for `db_session` and `exec()` patterns
- Review the "Best Practices" section at the top of this template
- Consult `enum-vs-text-design-decision.md` for architectural rationale

---

## Example Task Flow

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
# Use postgres-local MCP to query:
# SELECT id, type, COUNT(*) FROM customer WHERE type NOT IN ('person', 'company') GROUP BY id, type;
# Should return 0 rows

# 3. Update SQLModel classes
# Edit backend/app/models/crm.py
# Add CheckConstraint to __table_args__

# 4. Generate migration
alembic revision --autogenerate -m "phase_4_7_enum_to_text_customer_type_task1"

# 5. ⚠️ CRITICAL: Review migration file
# Open backend/migrations/versions/[timestamp]_phase_4_7_enum_to_text_customer_type_task1.py
# Search for 'audit' and 'event'
# DELETE any op.create_table('event', ... schema='audit') blocks
# Verify your ENUM → TEXT conversion is present
# Add pre-migration validation queries as comments

# 6. Apply migration
alembic upgrade head

# 7. Create test suite
# Create backend/tests/test_phase_4_7_customer_type_enum_to_text.py
# Use db_session: Session parameter
# Use select() with exec()
# Test valid cases ('person', 'company'), invalid case, NULL

# 8. Run new tests
pytest tests/test_phase_4_7_customer_type_enum_to_text.py -v
# All 5 new tests should pass

# 9. Regression check - Ensure no breaks
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Expected: 580 passed

pytest tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Expected: 607 passed

# 10. Rollback test - Verify downgrade works
alembic downgrade -1
alembic upgrade head
pytest tests/ -v  # Should still pass

# 11. Update docs
# Edit dev-docs/analysis/phase-4.7-db-schema-sync-3-plan.md
# Mark Task 1 as complete with test results
```

---

## Questions to Ask

**Before starting:**
1. Have I captured the 575/575 unit and 602/602 total baselines?
2. Have I validated that existing `customer.type` data only contains 'person' or 'company'?
3. Have I reviewed the enum-vs-text-design-decision.md to understand WHY we're doing this?
4. Do I understand the ENUM → TEXT conversion process and potential rollback issues?

**During implementation:**
1. Am I using `db_session` parameter (NOT `session`) in tests?
2. Am I using `select()/exec()` pattern (NOT `query()`) in tests?
3. After running `alembic revision --autogenerate`, did I check for and remove `audit.event` table creation?
4. Are my tests consistent with existing test patterns?
5. Am I testing both valid values ('person', 'company') and invalid values?
6. Am I testing NULL rejection (since nullable=False)?

**After implementation:**
1. Do I have 100% test pass rate on BOTH unit tests (580) and total tests (607)?
2. Did the baseline increase by exactly 5 tests (the tests I added)?
3. Have I verified the column is TEXT type in the database?
4. Have I verified the ENUM type no longer exists?
5. Have I updated the project plan document?
6. Have I tested migration rollback (`alembic downgrade -1`)?

---

**Ready to Begin!** 🚀

### Task 1 Checklist:
1. ✅ Capture baseline (575/575 unit, 602/602 total)
2. 🔍 Validate existing data (verify only 'person'/'company' values exist)
3. 🛠️ Update SQLModel class (add CHECK constraint to `Customer.__table_args__`)
4. 📝 Generate migration (`alembic revision --autogenerate`)
5. ⚠️ **CRITICAL: Remove `audit.event` table from migration if present**
6. ✅ Apply migration (`alembic upgrade head`)
7. 🧪 Create comprehensive tests (5 tests minimum: valid person, valid company, invalid value, NULL, column type verification)
8. 🔄 Run regression tests (expect 580 unit, 607 total)
9. ↩️ Test rollback (`alembic downgrade -1`, then `upgrade head`)
10. 📚 Update project plan

Remember: This task aligns the database with the architectural decision made in Phase 4.5 to use TEXT + CHECK constraints instead of native PostgreSQL ENUMs for better flexibility and SQLModel compatibility!
