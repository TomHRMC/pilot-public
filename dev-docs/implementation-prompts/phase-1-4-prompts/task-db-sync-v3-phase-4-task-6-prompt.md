# Task 6: Add Missing CHECK Constraints

**Reference:** `dev-docs/analysis/phase-4.7-db-schema-sync-3-plan.md` - Phase 4, Task 6
**Authority (Dual Master):**
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - Golden Master JSON
- `dev-docs/db-design/aevofab-db-schema-dump-phase-4.6-post.sql` - Production SQL Dump (Phase 4.6 Baseline)
**Type:** Phase 4 - Data Integrity (Constraints)
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

**Phase 4.7 Progress:**
- ✅ Task 1: Convert customer.type from ENUM to TEXT (582/582 unit, 609/609 total)
- ✅ Task 2: Convert user.preferred_mfa_channel from ENUM to TEXT (591/591 unit, 618/618 total)
- ✅ Task 3: Fix tax_rate_version_id FK Type Mismatches (597/597 unit, 624/624 total)
- ✅ Task 4: Fix ux_global_primary_email Unique Index Logic (602/602 unit, 629/629 total)
- ✅ Task 5: Add Missing DEFAULT Values (605/605 unit, 632/632 total)

**Current Baseline:** 605/605 unit tests, 632/632 total tests passing (100%)

**See:**
- `dev-docs/analysis/phase-4.5-db-schema-sync-to-design-plan.md` for Phase 4.5 history
- `dev-docs/analysis/phase-4.6-db-schema-sync-2-plan.md` for Phase 4.6 history

---

## Current Task: Add Missing CHECK Constraints

**Effort:** 1 day
**Gap Reference:** Phase 4.7 Analysis - Phase 4: Enforce Data Integrity (Constraints)
**Change Type:** MIGRATION

The JSON schema defines numerous CHECK constraints that are **missing from the physical database**. These constraints validate business rules at the database level, ensuring invalid data cannot be inserted even if application code has bugs. Without database-level enforcement, the application must remember to validate all data (error-prone), and invalid data can slip through causing data corruption and business logic failures.

### What Needs to Be Fixed

| # | Component | Issue | Direction | Complexity |
|---|-----------|-------|-----------|------------|
| **1** | `address` | Missing `address_has_physical_or_gps_chk` constraint | JSON→SQL | MEDIUM |
| **2** | `user_endpoint` | Missing `user_endpoint_channel_chk` constraint | JSON→SQL | LOW |
| **3** | `user_endpoint` | Missing `user_endpoint_verification_status_chk` constraint | JSON→SQL | LOW |
| **4** | `tax_rate_version` | Missing `tmv_valid_period_chk` constraint | JSON→SQL | LOW |
| **5** | `subscription` | Missing `subscription_billing_interval_chk` constraint | JSON→SQL | LOW |
| **6** | `conversation_session` | Missing `conv_session_status_chk` constraint | JSON→SQL | LOW |

**Note:** Review the JSON schema systematically for ALL missing CHECK constraints - the above list is a subset of examples from the plan document. The complete audit requires examining every table in the JSON schema.

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

**Record the output of both results:** `605/605 & 632/632 tests passing` (Phase 4.7 baseline - starting from Task 5 completion)

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

#### For MIGRATION Tasks (Phase 4.7 - Task 6)

**Problem:** The JSON schema defines numerous CHECK constraints that are missing from the physical database. These constraints validate business rules at the database level.

**Missing CHECK Constraints (Examples from Plan):**

1. **Address Validation:**
   ```sql
   ALTER TABLE address
   ADD CONSTRAINT address_has_physical_or_gps_chk
   CHECK (
     (street_address IS NOT NULL AND city IS NOT NULL AND postal_code IS NOT NULL) OR
     (gps_latitude IS NOT NULL AND gps_longitude IS NOT NULL)
   );
   ```

2. **User Endpoint Channel Validation:**
   ```sql
   ALTER TABLE user_endpoint
   ADD CONSTRAINT user_endpoint_channel_chk
   CHECK (channel IN ('email', 'sms', 'phone', 'slack'));
   ```

3. **User Endpoint Verification Status:**
   ```sql
   ALTER TABLE user_endpoint
   ADD CONSTRAINT user_endpoint_verification_status_chk
   CHECK (verification_status IN ('unverified', 'pending', 'verified', 'failed'));
   ```

4. **Tax Rate Version Valid Period:**
   ```sql
   ALTER TABLE tax_rate_version
   ADD CONSTRAINT tmv_valid_period_chk
   CHECK (LOWER(valid_period) IS NOT NULL);
   ```

5. **Subscription Billing Interval:**
   ```sql
   ALTER TABLE subscription
   ADD CONSTRAINT subscription_billing_interval_chk
   CHECK (billing_interval IN ('monthly', 'annual'));
   ```

6. **Conversation Session Status:**
   ```sql
   ALTER TABLE conversation_session
   ADD CONSTRAINT conv_session_status_chk
   CHECK (status IN ('active', 'ended', 'abandoned'));
   ```

**SQLModel Fix (Example for user_endpoint):**
```python
# backend/app/models/core.py
from sqlalchemy import CheckConstraint

class UserEndpoint(SQLModel, table=True):
    __tablename__ = "user_endpoint"
    __table_args__ = (
        # ... existing constraints ...
        CheckConstraint(
            "channel IN ('email', 'sms', 'phone', 'slack')",
            name='user_endpoint_channel_chk'
        ),
        CheckConstraint(
            "verification_status IN ('unverified', 'pending', 'verified', 'failed')",
            name='user_endpoint_verification_status_chk'
        ),
    )
```

**Migration SQL Template:**
```sql
-- Pre-migration validation
-- Check for invalid values (should be 0 rows)
SELECT id, channel FROM user_endpoint
WHERE channel NOT IN ('email', 'sms', 'phone', 'slack');

-- Add constraint
ALTER TABLE user_endpoint
ADD CONSTRAINT user_endpoint_channel_chk
CHECK (channel IN ('email', 'sms', 'phone', 'slack'));
```

**Database Verification Query:**
```sql
-- Verify constraint exists after migration
SELECT conname, contype, pg_get_constraintdef(oid)
FROM pg_constraint
WHERE conrelid = 'user_endpoint'::regclass
AND contype = 'c'
ORDER BY conname;
```

**IMPORTANT:** The above examples are from the plan document. You MUST systematically audit the JSON schema for ALL missing CHECK constraints across all tables before implementing.

---

### 2. Implementation Order

**For MIGRATION Tasks (Phase 4.7 Task 6):**

1. **✅ Establish Regression Baseline** (605/605 unit, 632/632 total)
2. **Audit JSON Schema for ALL CHECK Constraints**
   - Read `dev-docs/db-design/pilot-db-schema-v2.6h.json`
   - Extract all CHECK constraint definitions from each table
   - Create comprehensive list of missing constraints
3. **Pre-Migration Data Validation**
   - For each constraint, run validation query
   - Clean up invalid data if found
4. **Update SQLModel Classes**
   - Modify model files in `backend/app/models/`
   - Add CheckConstraint definitions to `__table_args__`
5. **Generate Alembic Migration**
   ```bash
   cd backend
   source .venv/bin/activate
   alembic revision --autogenerate -m "phase_4_7_add_missing_check_constraints_task6"
   ```
6. **Review & Enhance Migration**
   - ⚠️ **CRITICAL: Remove any `audit.event` table operations**
   - Verify all CHECK constraints captured
   - Add pre-migration validation queries as comments
   - Ensure downgrade() is complete
7. **Apply Migration**
   ```bash
   alembic upgrade head
   ```
8. **Create Test Suite**
   - Create `backend/tests/test_phase_4_7_check_constraints.py`
   - Use `db_session` NOT `session`
   - Use `select()` with `exec()` NOT `query()`
9. **Run New Tests**
   ```bash
   pytest tests/test_phase_4_7_check_constraints.py -v
   ```
10. **Run Regression Tests** (see "After You Complete" section)
11. **Update Documentation**

---

### 3. Test Requirements

**⚠️ ZERO REGRESSION POLICY:**
- **ALL 605 existing unit tests MUST still pass**
- **ALL 632 total tests (including integration) MUST still pass**
- **New tests MUST pass**
- **Target: 100% pass rate on both test suites**

#### For MIGRATION Tasks (Task 6)

**Test File:** `backend/tests/test_phase_4_7_check_constraints.py`

**Required Coverage (Comprehensive Testing):**
```python
"""
Test Suite: Phase 4.7 Task 6 - Add Missing CHECK Constraints
Tests business rule validation via database-level CHECK constraints

Reference: phase-4.7-db-schema-sync-3-plan.md
"""
import pytest
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from app.models.core import UserEndpoint
from app.models.crm import Address
from app.models.catalog import TaxRateVersion
from app.models.billing import Subscription
from app.models.voice_ai import ConversationSession

# ✅ CORRECT: Use db_session parameter and select()/exec() pattern

class TestUserEndpointChannelConstraint:
    """Test user_endpoint_channel_chk constraint"""
    
    def test_valid_channels_accepted(self, db_session: Session, test_user):
        """Valid channel values should be accepted"""
        for channel in ['email', 'sms', 'phone', 'slack']:
            endpoint = UserEndpoint(
                user_id=test_user.id,
                channel=channel,
                value=f"test_{channel}@example.com",
                is_primary=False
            )
            db_session.add(endpoint)
            db_session.commit()
            
            # Verify stored correctly
            result = db_session.exec(
                select(UserEndpoint).where(UserEndpoint.id == endpoint.id)
            ).first()
            assert result.channel == channel
            
            # Clean up for next iteration
            db_session.delete(endpoint)
            db_session.commit()
    
    def test_invalid_channel_rejected(self, db_session: Session, test_user):
        """Invalid channel values should be rejected"""
        endpoint = UserEndpoint(
            user_id=test_user.id,
            channel='invalid_channel',
            value='test@example.com',
            is_primary=False
        )
        db_session.add(endpoint)
        
        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()
        assert 'user_endpoint_channel_chk' in str(exc_info.value)
        
        db_session.rollback()

class TestAddressPhysicalOrGpsConstraint:
    """Test address_has_physical_or_gps_chk constraint"""
    
    def test_physical_address_accepted(self, db_session: Session, test_tenant):
        """Address with physical location should be accepted"""
        addr = Address(
            tenant_id=test_tenant.id,
            street_address='123 Main St',
            city='Springfield',
            postal_code='12345',
            gps_latitude=None,
            gps_longitude=None
        )
        db_session.add(addr)
        db_session.commit()
        assert addr.id is not None
    
    def test_gps_address_accepted(self, db_session: Session, test_tenant):
        """Address with GPS coordinates should be accepted"""
        addr = Address(
            tenant_id=test_tenant.id,
            street_address=None,
            city=None,
            postal_code=None,
            gps_latitude=40.7128,
            gps_longitude=-74.0060
        )
        db_session.add(addr)
        db_session.commit()
        assert addr.id is not None
    
    def test_incomplete_address_rejected(self, db_session: Session, test_tenant):
        """Address missing both physical and GPS should be rejected"""
        addr = Address(
            tenant_id=test_tenant.id,
            street_address=None,
            city=None,
            postal_code=None,
            gps_latitude=None,
            gps_longitude=None
        )
        db_session.add(addr)
        
        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()
        assert 'address_has_physical_or_gps_chk' in str(exc_info.value)
        
        db_session.rollback()

# Add similar test classes for:
# - TestUserEndpointVerificationStatusConstraint
# - TestTaxRateVersionValidPeriodConstraint
# - TestSubscriptionBillingIntervalConstraint
# - TestConversationSessionStatusConstraint
# ... and ALL other CHECK constraints found in JSON schema
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

### 4. JSON Change Tracking

**Not Applicable for Task 6:** This is a MIGRATION task (SQL changes only), not a JSON_UPDATE task. No JSON schema changes required.

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
- **For MIGRATION tasks:** `[605 + NEW_TEST_COUNT] passed` (unit), `[632 + NEW_TEST_COUNT] passed` (total)

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

Find Phase 4, Task 6 (lines 871-1007) and update with:

```markdown
### Task 6: Add Missing CHECK Constraints

**Status:** ✅ COMPLETE (YYYY-MM-DD)
**Effort:** 1 day (actual)
**Change Type:** MIGRATION

**Implementation Summary:**

- Modified: Multiple model files in `backend/app/models/`
- Migration: `YYYY_MM_DD_HHMM-[hash]_phase_4_7_add_missing_check_constraints_task6.py`
- Test Suite: `test_phase_4_7_check_constraints.py` - [X] tests ✅
- Final Results: [605 + X]/[605 + X] unit tests passing (100%), [632 + X]/[632 + X] total tests passing (100%)

**Key Changes:**
- ✅ Added [N] CHECK constraints across [M] tables
- ✅ Database now enforces business rules at constraint level
- ✅ Invalid data cannot be inserted even if application logic fails
- ✅ All constraints align with JSON schema definitions

**Verification:**
- All CHECK constraints verified via pg_constraint query
- Pre-migration validation confirmed zero invalid data
- Migration rollback tested successfully (downgrade → upgrade)
```

---

## Success Criteria

**MUST COMPLETE ALL BEFORE MARKING TASK AS DONE:**

### For MIGRATION Tasks (Task 6):
- [ ] **Regression baseline captured** (605/605 unit, 632/632 total tests)
- [ ] **JSON schema audited** for ALL missing CHECK constraints
- [ ] **Comprehensive constraint list created** (document all missing constraints)
- [ ] **Pre-migration data validation completed** (queries run, data clean)
- [ ] **SQLModel classes updated** with all CheckConstraint definitions
- [ ] **Used `db_session` parameter** (not `session`) in code
- [ ] **Used `select()/exec()` pattern** (not `query()`) where applicable
- [ ] **Alembic migration created** using autogenerate
- [ ] **⚠️ CRITICAL: Checked migration for `audit.event` table** and removed if present
- [ ] **Migration applied successfully** (`alembic upgrade head`)
- [ ] **Comprehensive test suite written** covering all constraints
- [ ] **Tests use `db_session` parameter** and `select()/exec()` pattern
- [ ] **ALL tests pass** (valid values accepted, invalid values rejected)
- [ ] **ALL 605 existing unit tests still passing**
- [ ] **ALL 632 total tests still passing** (including integration)
- [ ] **New total: [605 + X]/[605 + X] unit passing, [632 + X]/[632 + X] total passing (100%)**
- [ ] **Database verification query confirms** all constraints active
- [ ] **Migration rollback tested** (`alembic downgrade -1` then `upgrade head` again)
- [ ] **Project plan document updated**

### For ALL Tasks:
- [ ] **100% test pass rate** - No failing tests
- [ ] **Zero regression** - Baseline maintained or exceeded

---

## Key Files to Review

### Architecture & Design
- `dev-docs/analysis/phase-4.7-db-schema-sync-3-plan.md` - **Task 6 Details** ⭐
- `dev-docs/analysis/phase-4.7-db-schema-sync-3-analysis.md` - Forensic Analysis
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - **Golden Master JSON** ⭐
- `dev-docs/db-design/aevofab-db-schema-dump-phase-4.6-post.sql` - Production SQL Dump

### Backend Models (Update These)
- `backend/app/models/core.py` - User, UserEndpoint
- `backend/app/models/crm.py` - Customer, Contact, Address, Site
- `backend/app/models/catalog.py` - TaxRateVersion, SupplierItemPrice
- `backend/app/models/billing.py` - Subscription
- `backend/app/models/voice_ai.py` - ConversationSession
- `backend/app/models/fulfillment.py` - Job-related models
- `backend/app/models/quoting.py` - Quote-related models
- `backend/app/models/system.py` - System tables

### Tests (Reference for Patterns)
- `backend/tests/test_check_constraints_task9.py` - CHECK constraint patterns
- `backend/tests/test_citext_email.py` - Correct `select()/exec()` usage
- `backend/tests/conftest.py` - Test fixtures (`db_session`, `test_tenant`, etc.)

---

## Risk Assessment

**Data Validation Risk:** HIGH
- Must validate existing data doesn't violate any new constraints
- **Mitigation:** Run comprehensive validation queries before migration, clean up invalid data

**Regression Risk:** MEDIUM
- Adding many constraints could expose existing data issues or application bugs
- **Mitigation:** Maintain 605/632 baseline, test after every change, check alembic for audit.event

**Migration Complexity:** HIGH
- Many constraints to add across multiple tables
- **Mitigation:** Systematic JSON audit, comprehensive pre-validation, thorough testing

---

## Notes

### Important Patterns to Follow
- **Virtual Environment Required:** All Python/pytest commands use `source .venv/bin/activate`
- **Use `db_session` Parameter:** NOT `session` (pytest fixture naming)
- **Use `select()/exec()` Pattern:** NOT `query()` (SQLModel standard, no deprecation warnings)
- **Check Alembic Migrations:** ALWAYS remove `audit.event` table creation if autogenerated
- **Dual Master Strategy:** JSON is documentation authority, SQL dump is runtime authority
- **Zero Regression Policy:** All 605 unit + 632 total tests MUST pass after changes

### Task 6 Specific
- **Systematic JSON audit required** - Don't rely on plan examples, audit the entire schema
- **Pre-validate ALL data** - Run validation queries BEFORE applying constraints
- **Test valid AND invalid values** - Ensure constraints actually work
- **Test NULL handling** - If field is nullable, constraint must allow NULL
- **Comprehensive testing** - Every constraint needs positive and negative tests

### If You Get Stuck
- Review `dev-docs/db-design/pilot-db-schema-v2.6h.json` for complete constraint definitions
- Check existing constraint tests in `backend/tests/test_check_constraints_task9.py`
- Use `postgres-local` MCP server to query database in real-time
- Search existing tests for `db_session` and `exec()` patterns
- Review the "Best Practices" section at the top of this template

---

## Example Task Flow

### For MIGRATION Tasks (Task 6):

```bash
# 1. Baseline - Capture starting point
cd backend
source .venv/bin/activate

# Run unit tests (no integration)
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Record: 605 passed

# Run all tests (including integration)
pytest tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Record: 632 passed

# 2. Audit JSON schema for ALL CHECK constraints
# Open dev-docs/db-design/pilot-db-schema-v2.6h.json
# Systematically review each table's "constraints" section
# Extract all CHECK constraint definitions
# Create comprehensive list

# 3. Pre-migration data validation
# For each constraint, run validation query
# Example: SELECT id, channel FROM user_endpoint WHERE channel NOT IN ('email', 'sms', 'phone', 'slack');
# If rows returned, clean data before proceeding

# 4. Update SQLModel classes
# Edit multiple files in backend/app/models/
# Add CheckConstraint definitions to __table_args__
# Use db_session parameter, sa_column if needed

# 5. Generate migration
alembic revision --autogenerate -m "phase_4_7_add_missing_check_constraints_task6"

# 6. ⚠️ CRITICAL: Review migration file
# Open backend/migrations/versions/[timestamp]_phase_4_7_add_missing_check_constraints_task6.py
# Search for 'audit' and 'event'
# DELETE any op.create_table('event', ... schema='audit') blocks
# Verify all CHECK constraints are present
# Add pre-migration validation queries as comments

# 7. Apply migration
alembic upgrade head

# 8. Create comprehensive test suite
# Create backend/tests/test_phase_4_7_check_constraints.py
# Use db_session: Session parameter
# Use select() with exec()
# Test valid cases, invalid cases, NULL handling for ALL constraints

# 9. Run new tests
pytest tests/test_phase_4_7_check_constraints.py -v
# All new tests should pass

# 10. Regression check - Ensure no breaks
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Expected: [605 + X] passed

pytest tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Expected: [632 + X] passed

# 11. Rollback test - Verify downgrade works
alembic downgrade -1
alembic upgrade head
pytest tests/ -v  # Should still pass

# 12. Update docs
# Edit dev-docs/analysis/phase-4.7-db-schema-sync-3-plan.md
# Mark task as complete with test results
```

---

## Questions to Ask

**Before starting:**
1. Have I captured the 605/605 unit and 632/632 total baselines?
2. Have I systematically audited the JSON schema for ALL CHECK constraints?
3. Do I have a comprehensive list of missing constraints to implement?
4. Have I validated existing data won't violate new constraints?
5. Do I understand which fields are nullable vs non-nullable?

**During implementation:**
1. Am I using `db_session` parameter (NOT `session`) in tests?
2. Am I using `select()/exec()` pattern (NOT `query()`) in tests?
3. After running `alembic revision --autogenerate`, did I check for and remove `audit.event` table creation?
4. Are my CHECK constraints handling NULL values correctly for nullable fields?
5. Am I testing both valid AND invalid values for each constraint?
6. Am I testing NULL handling for nullable fields?

**After implementation:**
1. Do I have 100% test pass rate on BOTH unit tests (605+X) and total tests (632+X)?
2. Have I tested ALL constraints (not just the examples from the plan)?
3. Have I updated the project plan document?
4. Have I tested migration rollback (`alembic downgrade -1`)?
5. Have I verified all constraints are active in the database?

---

**Ready to Begin!** 🚀

### MIGRATION Task Checklist (Task 6):
1. ✅ Capture baseline (605/605 unit, 632/632 total)
2. 🔍 Audit JSON schema for ALL CHECK constraints (create comprehensive list)
3. 🔍 Validate existing data (run pre-migration queries for ALL constraints)
4. 🛠️ Update SQLModel classes (add CheckConstraint to __table_args__)
5. 📝 Generate migration (`alembic revision --autogenerate`)
6. ⚠️ **CRITICAL: Remove `audit.event` table from migration if present**
7. ✅ Apply migration (`alembic upgrade head`)
8. 🧪 Create comprehensive tests (use `db_session`, `select()/exec()`, test ALL constraints)
9. 🔄 Run regression tests (605+X unit, 632+X total)
10. ↩️ Test rollback (`alembic downgrade -1`, then `upgrade head`)
11. 📚 Update project plan

Remember: Phase 4.7 is about **final production alignment** - architectural decisions and data integrity enforcement. This is the last major schema sync before deployment. Be thorough, validate ALL data, systematically audit the JSON schema for ALL constraints, and always check for the `audit.event` table issue in migrations!
