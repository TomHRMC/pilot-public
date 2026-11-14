# Task 3: Fix `tax_rate_version_id` Foreign Key Type Mismatches

**Reference:** `dev-docs/analysis/phase-4.7-db-schema-sync-3-plan.md` - Phase 2, Task 3
**Authority (Dual Master):**
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - Golden Master JSON
- `dev-docs/db-design/aevofab-db-schema-dump-phase-4.6-post.sql` - Production SQL Dump (Phase 4.6 Baseline)
**Type:** Phase 2 - Integer Capacity Risks
**Priority:** CRITICAL
**Change Type:** MIGRATION

---

## Context

This is **Phase 4.7 - DB Sync v#3**, a third forensic reconciliation after completing Phases 4.5 and 4.6. A comprehensive comparison between the latest SQL dump (`aevofab-db-schema-dump-phase-4.6-post.sql`) and the Golden Master JSON revealed **5 major remaining discrepancies** requiring final alignment before production deployment.

**Key Focus Areas:**
1. **Enumerated type standardization** (ENUM → TEXT + CHECK)
2. **Integer capacity risks** (Foreign key type mismatches) ⭐ **THIS TASK**
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

**Phase 4.7 Phase 1 Status:** ✅ COMPLETE (April 3-4, 2026)
- ✅ Task 1: customer.type ENUM → TEXT (7 tests)
- ✅ Task 2: user.preferred_mfa_channel ENUM → TEXT (9 tests)
- ✅ 591/591 unit tests passing (100%)
- ✅ 618/618 total tests passing (100%)

**Current Baseline:** 591/591 unit tests, 618/618 total tests passing (100%)

**See:**
- `dev-docs/analysis/phase-4.5-db-schema-sync-to-design-plan.md` for Phase 4.5 history
- `dev-docs/analysis/phase-4.6-db-schema-sync-2-plan.md` for Phase 4.6 history

---

## Current Task: Fix `tax_rate_version_id` Foreign Key Type Mismatches

**Effort:** 0.5 days
**Gap Reference:** Phase 4.7 Analysis - Phase 2: Resolve Integer Capacity Risks
**Change Type:** MIGRATION

Three foreign key columns referencing `tax_rate_version.id` (BIGINT primary key) are incorrectly defined as standard `INTEGER`. This creates a **critical capacity risk** where after 2.1 billion tax rate versions, FK overflow would cause data corruption. This task upgrades all three FK columns to BIGINT to match the parent PK type.

### What Needs to Be Fixed

| # | Component | Issue | Direction | Complexity |
|---|-----------|-------|-----------|------------|
| **1** | `quote_line_tax_component.tax_rate_version_id` | INTEGER FK referencing BIGINT PK → capacity overflow risk | SQL→SQL | LOW |
| **2** | `invoice_line_tax_component.tax_rate_version_id` | INTEGER FK referencing BIGINT PK → capacity overflow risk | SQL→SQL | LOW |
| **3** | `change_order_line_tax_component.tax_rate_version_id` | INTEGER FK referencing BIGINT PK → capacity overflow risk | SQL→SQL | LOW |

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

**Record the output of both results:** `591/591 & 618/618 tests passing` (Phase 4.7 baseline - after Phase 1 completion)

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

#### For MIGRATION Tasks (This Task)

**Problem:** 
Three foreign key columns reference `tax_rate_version.id` (BIGINT primary key) but are incorrectly defined as `INTEGER`:

1. `quote_line_tax_component.tax_rate_version_id`
2. `invoice_line_tax_component.tax_rate_version_id`
3. `change_order_line_tax_component.tax_rate_version_id`

**Current State:**
```sql
-- Parent table (CORRECT):
CREATE TABLE tax_rate_version (
  id bigint PRIMARY KEY,
  -- ...
);

-- Child tables (WRONG):
CREATE TABLE quote_line_tax_component (
  tax_rate_version_id integer,  -- Should be bigint!
  FOREIGN KEY (tax_rate_version_id) REFERENCES tax_rate_version(id)
);

-- Repeat for invoice_line_tax_component and change_order_line_tax_component
```

**Capacity Risk:**
```
INTEGER max value:    2,147,483,647 (2.1 billion)
BIGINT max value:     9,223,372,036,854,775,807 (9.2 quintillion)

After 2.1 billion tax rate versions → FK overflow → data corruption
```

**SQLModel Fix:**
```python
# backend/app/models/quoting.py
from sqlalchemy import Column, BigInteger

class QuoteLineTaxComponent(SQLModel, table=True):
    __tablename__ = "quote_line_tax_component"
    
    # Change from int to int (SQLModel uses Python int for both)
    # The sa_column parameter ensures BIGINT in database
    tax_rate_version_id: int = Field(
        foreign_key="tax_rate_version.id",
        nullable=False,
        sa_column=Column(BigInteger, nullable=False)
    )

# Repeat for InvoiceLineTaxComponent and ChangeOrderLineTaxComponent
# in backend/app/models/fulfillment.py
```

**Migration SQL:**
```sql
-- Pre-migration validation
-- Verify no data exceeds INTEGER max (should be 0 rows)
SELECT MAX(tax_rate_version_id) AS max_value
FROM (
  SELECT tax_rate_version_id FROM quote_line_tax_component
  UNION ALL
  SELECT tax_rate_version_id FROM invoice_line_tax_component
  UNION ALL
  SELECT tax_rate_version_id FROM change_order_line_tax_component
) AS combined;

-- Should return max_value < 2147483647

-- Migration upgrade():
-- Fix all 3 foreign key columns
ALTER TABLE quote_line_tax_component
ALTER COLUMN tax_rate_version_id TYPE bigint;

ALTER TABLE invoice_line_tax_component
ALTER COLUMN tax_rate_version_id TYPE bigint;

ALTER TABLE change_order_line_tax_component
ALTER COLUMN tax_rate_version_id TYPE bigint;

-- Migration downgrade():
-- WARNING: Downgrade unsafe if values exceed INTEGER max
ALTER TABLE quote_line_tax_component
ALTER COLUMN tax_rate_version_id TYPE integer;

ALTER TABLE invoice_line_tax_component
ALTER COLUMN tax_rate_version_id TYPE integer;

ALTER TABLE change_order_line_tax_component
ALTER COLUMN tax_rate_version_id TYPE integer;
```

**Database Verification Query:**
```sql
-- Verify all 3 columns are now BIGINT
SELECT 
  table_name,
  column_name,
  data_type,
  character_maximum_length,
  numeric_precision
FROM information_schema.columns
WHERE table_schema = 'public'
  AND column_name = 'tax_rate_version_id'
  AND table_name IN (
    'quote_line_tax_component',
    'invoice_line_tax_component',
    'change_order_line_tax_component'
  )
ORDER BY table_name;

-- Expected: All 3 rows show data_type = 'bigint'
```

---

### 2. Implementation Order

**For MIGRATION Tasks (This Task):**

1. **✅ Establish Regression Baseline** (591/591 unit, 618/618 total tests)
2. **Pre-Migration Data Validation**
   - Run validation queries
   - Verify max FK values < INTEGER max
3. **Update SQLModel Classes**
   - Modify `backend/app/models/quoting.py` (QuoteLineTaxComponent)
   - Modify `backend/app/models/fulfillment.py` (InvoiceLineTaxComponent, ChangeOrderLineTaxComponent)
4. **Generate Alembic Migration**
   ```bash
   cd backend
   source .venv/bin/activate
   alembic revision --autogenerate -m "phase_4_7_fix_tax_rate_version_id_fk_types_task3"
   ```
5. **Review & Enhance Migration**
   - ⚠️ **CRITICAL: Check for and remove `audit.event` table operations**
   - Add pre-migration validation queries as comments
   - Verify all 3 ALTER COLUMN statements present
   - Ensure downgrade() is complete
6. **Apply Migration**
   ```bash
   alembic upgrade head
   ```
7. **Create Test Suite**
   - Create `backend/tests/test_phase_4_7_tax_rate_version_id_fk_types.py`
   - Use `db_session` parameter (NOT `session`)
   - Use `select()` with `exec()` (NOT `query()`)
8. **Run New Tests**
   ```bash
   pytest tests/test_phase_4_7_tax_rate_version_id_fk_types.py -v
   ```
9. **Run Regression Tests** (see "After You Complete" section)
10. **Update Documentation**

---

### 3. Test Requirements

**⚠️ ZERO REGRESSION POLICY:**
- **ALL 591 existing unit tests MUST still pass**
- **ALL 618 total tests (including integration) MUST still pass**
- **New tests (if added) MUST pass**
- **Target: 100% pass rate on both test suites**

#### For MIGRATION Tasks (This Task)

**Test File:** `backend/tests/test_phase_4_7_tax_rate_version_id_fk_types.py`

**Required Coverage (Minimum 6 Tests):**
```python
"""
Test Suite: Phase 4.7 Task 3 - Fix tax_rate_version_id FK Type Mismatches
Tests BIGINT FK capacity for tax rate version references - final schema alignment for production deployment

Reference: phase-4.7-db-schema-sync-3-plan.md
"""
import pytest
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError
from decimal import Decimal

from app.models.catalog import TaxRateVersion
from app.models.quoting import QuoteLineTaxComponent
from app.models.fulfillment import InvoiceLineTaxComponent, ChangeOrderLineTaxComponent

# ✅ CORRECT: Use db_session parameter and select()/exec() pattern

class TestTaxRateVersionIdBigintCapacity:
    """Test that all tax_rate_version_id FKs can handle BIGINT values"""
    
    def test_quote_line_tax_component_bigint_fk(self, db_session: Session, test_tenant, test_quote_line):
        """QuoteLineTaxComponent.tax_rate_version_id can store large BIGINT values"""
        # Create a tax rate version with a large ID (simulating high capacity)
        # Note: In practice, we can't actually set the ID to >2B due to sequence limits
        # But we can verify the column TYPE is bigint via information_schema
        
        component = QuoteLineTaxComponent(
            quote_line_id=test_quote_line.id,
            tax_rate_version_id=test_quote_line.tax_rate_version_id,  # Use existing valid ID
            tenant_id=test_tenant.id
        )
        db_session.add(component)
        db_session.commit()
        
        # Use select() with exec() - NOT query()
        result = db_session.exec(
            select(QuoteLineTaxComponent).where(QuoteLineTaxComponent.id == component.id)
        ).first()
        assert result is not None
        assert result.tax_rate_version_id is not None
    
    def test_invoice_line_tax_component_bigint_fk(self, db_session: Session, test_tenant, test_invoice_line):
        """InvoiceLineTaxComponent.tax_rate_version_id can store large BIGINT values"""
        component = InvoiceLineTaxComponent(
            invoice_line_id=test_invoice_line.id,
            tax_rate_version_id=test_invoice_line.tax_rate_version_id,
            tenant_id=test_tenant.id
        )
        db_session.add(component)
        db_session.commit()
        
        result = db_session.exec(
            select(InvoiceLineTaxComponent).where(InvoiceLineTaxComponent.id == component.id)
        ).first()
        assert result is not None
        assert result.tax_rate_version_id is not None
    
    def test_change_order_line_tax_component_bigint_fk(self, db_session: Session, test_tenant, test_change_order_line):
        """ChangeOrderLineTaxComponent.tax_rate_version_id can store large BIGINT values"""
        component = ChangeOrderLineTaxComponent(
            change_order_line_id=test_change_order_line.id,
            tax_rate_version_id=test_change_order_line.tax_rate_version_id,
            tenant_id=test_tenant.id
        )
        db_session.add(component)
        db_session.commit()
        
        result = db_session.exec(
            select(ChangeOrderLineTaxComponent).where(ChangeOrderLineTaxComponent.id == component.id)
        ).first()
        assert result is not None
        assert result.tax_rate_version_id is not None
    
    def test_verify_columns_are_bigint(self, db_session: Session):
        """Verify all 3 FK columns are BIGINT type in database schema"""
        from sqlalchemy import text
        
        query = text("""
            SELECT 
              table_name,
              column_name,
              data_type
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND column_name = 'tax_rate_version_id'
              AND table_name IN (
                'quote_line_tax_component',
                'invoice_line_tax_component',
                'change_order_line_tax_component'
              )
            ORDER BY table_name
        """)
        
        result = db_session.exec(query).all()
        
        # Should return 3 rows, all with data_type = 'bigint'
        assert len(result) == 3
        for row in result:
            assert row[2] == 'bigint', f"{row[0]}.{row[1]} should be bigint, got {row[2]}"
    
    def test_fk_referential_integrity_maintained(self, db_session: Session, test_tenant, test_quote_line):
        """FK constraints still enforce referential integrity after type change"""
        # Attempt to insert with invalid tax_rate_version_id (should fail)
        component = QuoteLineTaxComponent(
            quote_line_id=test_quote_line.id,
            tax_rate_version_id=999999999,  # Non-existent tax rate version
            tenant_id=test_tenant.id
        )
        db_session.add(component)
        
        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()
        
        # Should violate FK constraint
        assert "fk_quote_line_tax_component_tax_rate_version" in str(exc_info.value).lower() or \
               "foreign key" in str(exc_info.value).lower()
        
        # Rollback to clean up failed transaction
        db_session.rollback()
    
    def test_all_component_types_can_reference_same_tax_rate_version(
        self, db_session: Session, test_tenant, test_quote_line, test_invoice_line, test_change_order_line
    ):
        """All 3 component types can reference the same tax_rate_version_id"""
        # Use the tax rate version from test_quote_line as the common reference
        tax_rate_version_id = test_quote_line.tax_rate_version_id
        
        # Create components for all 3 types
        quote_component = QuoteLineTaxComponent(
            quote_line_id=test_quote_line.id,
            tax_rate_version_id=tax_rate_version_id,
            tenant_id=test_tenant.id
        )
        
        invoice_component = InvoiceLineTaxComponent(
            invoice_line_id=test_invoice_line.id,
            tax_rate_version_id=tax_rate_version_id,
            tenant_id=test_tenant.id
        )
        
        change_order_component = ChangeOrderLineTaxComponent(
            change_order_line_id=test_change_order_line.id,
            tax_rate_version_id=tax_rate_version_id,
            tenant_id=test_tenant.id
        )
        
        db_session.add(quote_component)
        db_session.add(invoice_component)
        db_session.add(change_order_component)
        db_session.commit()
        
        # Verify all can read back with same tax_rate_version_id
        assert quote_component.tax_rate_version_id == tax_rate_version_id
        assert invoice_component.tax_rate_version_id == tax_rate_version_id
        assert change_order_component.tax_rate_version_id == tax_rate_version_id
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
- `test_quote_line` - Pre-created quote line with tax rate version
- `test_invoice_line` - Pre-created invoice line with tax rate version
- `test_change_order_line` - Pre-created change order line with tax rate version
- `utc_now` - Timezone-aware current timestamp function

---

### 4. JSON Change Tracking

**Not Applicable:** This is a MIGRATION task only. No JSON schema changes required.

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
- **For MIGRATION tasks:** `[591 + NEW_TEST_COUNT] passed` (unit), `[618 + NEW_TEST_COUNT] passed` (total)

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

Find Phase 2, Task 3 and update with:

```markdown
### Task 3: Fix `tax_rate_version_id` Foreign Key Type Mismatches

**Status:** ✅ COMPLETE (YYYY-MM-DD)
**Effort:** 0.5 days (actual)
**Change Type:** MIGRATION

**Implementation Summary:**

- Modified: `backend/app/models/quoting.py` - QuoteLineTaxComponent
- Modified: `backend/app/models/fulfillment.py` - InvoiceLineTaxComponent, ChangeOrderLineTaxComponent
- Migration: `YYYY_MM_DD_HHMM-[hash]_phase_4_7_fix_tax_rate_version_id_fk_types_task3.py`
- Test Suite: `test_phase_4_7_tax_rate_version_id_fk_types.py` - 6 tests ✅
- Final Results: [591 + 6]/[591 + 6] unit tests passing (100%), [618 + 6]/[618 + 6] total tests passing (100%)

**Key Changes:**
- ✅ Upgraded quote_line_tax_component.tax_rate_version_id from INTEGER to BIGINT
- ✅ Upgraded invoice_line_tax_component.tax_rate_version_id from INTEGER to BIGINT
- ✅ Upgraded change_order_line_tax_component.tax_rate_version_id from INTEGER to BIGINT
- ✅ Eliminated integer overflow risk (capacity now 9.2 quintillion vs 2.1 billion)
- ✅ FK types now match parent PK type (tax_rate_version.id is BIGINT)

**Verification:**
- Column types verified as BIGINT via information_schema query
- Foreign key constraints still enforce referential integrity
- All 3 component types can reference same tax_rate_version_id
- Migration rollback tested successfully (downgrade → upgrade)
```

---

## Success Criteria

**MUST COMPLETE ALL BEFORE MARKING TASK AS DONE:**

### For MIGRATION Tasks (This Task):
- [ ] **Regression baseline captured** (591/591 unit, 618/618 total tests)
- [ ] **Pre-migration data validation completed** (queries run, max values checked)
- [ ] **SQLModel classes updated** with sa_column=Column(BigInteger)
- [ ] **Used `db_session` parameter** (not `session`) in code
- [ ] **Used `select()/exec()` pattern** (not `query()`) where applicable
- [ ] **Alembic migration created** using autogenerate
- [ ] **⚠️ CRITICAL: Checked migration for `audit.event` table** and removed if present
- [ ] **Migration applied successfully** (`alembic upgrade head`)
- [ ] **All 6 new tests written and passing**
- [ ] **Tests use `db_session` parameter** and `select()/exec()` pattern
- [ ] **ALL 591 existing unit tests still passing**
- [ ] **ALL 618 total tests still passing** (including integration)
- [ ] **New total: [591 + 6]/[591 + 6] unit passing, [618 + 6]/[618 + 6] total passing (100%)**
- [ ] **Database verification query confirms** all 3 columns are BIGINT
- [ ] **Migration rollback tested** (`alembic downgrade -1` then `upgrade head` again)
- [ ] **Project plan document updated**

### For ALL Tasks:
- [ ] **100% test pass rate** - No failing tests
- [ ] **Zero regression** - Baseline maintained or exceeded

---

## Key Files to Review

### Architecture & Design
- `dev-docs/analysis/phase-4.7-db-schema-sync-3-plan.md` - **Task 3 Details** ⭐
- `dev-docs/analysis/phase-4.7-db-schema-sync-3-analysis.md` - Forensic Analysis
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - **Golden Master JSON**
- `dev-docs/db-design/aevofab-db-schema-dump-phase-4.6-post.sql` - **Production SQL Dump (Phase 4.6 Baseline)**

### Backend Code
- `backend/app/models/quoting.py` - QuoteLineTaxComponent model ⭐
- `backend/app/models/fulfillment.py` - InvoiceLineTaxComponent, ChangeOrderLineTaxComponent models ⭐
- `backend/app/models/catalog.py` - TaxRateVersion model (parent table)

### Tests (Reference for Patterns)
- `backend/tests/test_check_constraints_task9.py` - CHECK constraint patterns
- `backend/tests/test_temporal_exclusion_constraints_task10.py` - EXCLUDE constraint patterns
- `backend/tests/test_citext_email.py` - Correct `select()/exec()` usage
- `backend/tests/conftest.py` - Test fixtures (`db_session`, `test_tenant`, etc.)

---

## Risk Assessment

**Data Validation Risk:** LOW
- Current data unlikely to exceed INTEGER max (2.1 billion)
- Pre-migration validation query will confirm no issues
- **Mitigation:** Run validation query before migration

**Regression Risk:** LOW
- Type change is transparent to application code
- FK constraints remain functionally identical
- **Mitigation:** Maintain 591/618 baseline, test after every change, check alembic for audit.event

**Migration Risk:** LOW
- ALTER COLUMN TYPE is online operation in PostgreSQL
- No data loss expected (INTEGER values fit in BIGINT)
- **Mitigation:** Test migration rollback before marking complete

---

## Notes

### Important Patterns to Follow
- **Virtual Environment Required:** All Python/pytest commands use `source .venv/bin/activate`
- **Use `db_session` Parameter:** NOT `session` (pytest fixture naming)
- **Use `select()/exec()` Pattern:** NOT `query()` (SQLModel standard, no deprecation warnings)
- **Check Alembic Migrations:** ALWAYS remove `audit.event` table creation if autogenerated
- **Use sa_column for BIGINT:** Explicit `sa_column=Column(BigInteger)` required for FK type matching
- **Zero Regression Policy:** All 591 unit + 618 total tests MUST pass after changes

### Phase 4.7 Specific
- **Final production alignment** - Last schema sync before deployment
- **Critical capacity fix** - Prevents future data corruption from integer overflow
- **Type safety enforcement** - FK types must match PK types for data integrity
- **Pre-validate all data** - Run validation queries BEFORE applying changes

### If You Get Stuck
- Check the SQL dump for exact production definitions
- Review Phase 4.7 Task 1/2 completed work for FK type patterns
- Use `postgres-local` MCP server to query database in real-time
- Search existing tests for `db_session` and `exec()` patterns
- Review the "Best Practices" section at the top of this template
- Look for existing `sa_column=Column(BigInteger)` usage in models

---

## Example Task Flow

### For MIGRATION Tasks (This Task):

```bash
# 1. Baseline - Capture starting point
cd backend
source .venv/bin/activate

# Run unit tests (no integration)
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Record: 591 passed

# Run all tests (including integration)
pytest tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Record: 618 passed

# 2. Pre-migration data validation
# Run validation query to check max FK values
# Use postgres-local MCP server or psql to verify max < 2147483647

# 3. Update SQLModel classes
# Edit backend/app/models/quoting.py (QuoteLineTaxComponent)
# Edit backend/app/models/fulfillment.py (InvoiceLineTaxComponent, ChangeOrderLineTaxComponent)
# Add sa_column=Column(BigInteger, nullable=False) to all 3 tax_rate_version_id fields

# 4. Generate migration
alembic revision --autogenerate -m "phase_4_7_fix_tax_rate_version_id_fk_types_task3"

# 5. ⚠️ CRITICAL: Review migration file
# Open backend/migrations/versions/[timestamp]_phase_4_7_fix_tax_rate_version_id_fk_types_task3.py
# Search for 'audit' and 'event'
# DELETE any op.create_table('event', ... schema='audit') blocks
# Verify your 3 ALTER COLUMN statements are present
# Add pre-migration validation query as comment

# 6. Apply migration
alembic upgrade head

# 7. Create test suite
# Create backend/tests/test_phase_4_7_tax_rate_version_id_fk_types.py
# - Use db_session: Session parameter
# - Use select() with exec()
# - Test all 3 component types
# - Test schema verification
# - Test FK referential integrity

# 8. Run new tests
pytest tests/test_phase_4_7_tax_rate_version_id_fk_types.py -v
# All new tests should pass

# 9. Regression check - Ensure no breaks
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Expected: [591 + 6] passed

pytest tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Expected: [618 + 6] passed

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
1. Have I captured the 591/591 unit and 618/618 total baselines?
2. Have I validated existing data won't exceed INTEGER max?
3. Do I understand which 3 models need sa_column updates?
4. Do I know where to find test fixtures for quote/invoice/change_order lines?

**During implementation:**
1. Am I using `db_session` parameter (NOT `session`) in tests?
2. Am I using `select()/exec()` pattern (NOT `query()`) in tests?
3. After running `alembic revision --autogenerate`, did I check for and remove `audit.event` table creation?
4. Are all 3 ALTER COLUMN statements present in the migration?
5. Did I add the pre-migration validation query as a comment?

**After implementation:**
1. Do I have 100% test pass rate on BOTH unit tests and total tests?
2. Did baseline increase by exactly 6 tests (591+6 unit, 618+6 total)?
3. Have I updated the project plan document?
4. Have I verified all 3 columns are BIGINT via information_schema?
5. Have I tested migration rollback (`alembic downgrade -1`)?

---

**Ready to Begin!** 🚀

### MIGRATION Task Checklist (This Task):
1. ✅ Capture baseline (591/591 unit, 618/618 total)
2. 🔍 Validate existing data (run pre-migration query for max FK values)
3. 🛠️ Update SQLModel classes (add sa_column=Column(BigInteger) to 3 fields)
4. 📝 Generate migration (`alembic revision --autogenerate`)
5. ⚠️ **CRITICAL: Remove `audit.event` table from migration if present**
6. ✅ Apply migration (`alembic upgrade head`)
7. 🧪 Create comprehensive tests (6 tests minimum)
8. 🔄 Run regression tests (591+6 unit, 618+6 total)
9. ↩️ Test rollback (`alembic downgrade -1`, then `upgrade head`)
10. 📚 Update project plan

Remember: Phase 4.7 Task 3 is about **preventing future data corruption** from integer overflow. This is a critical capacity fix that ensures tax rate versioning can scale to 9.2 quintillion records instead of being limited to 2.1 billion. Be thorough, validate data, and always check for the `audit.event` table issue in migrations!
