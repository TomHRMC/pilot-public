# Task 7: Add Missing EXCLUDE Constraint (Supplier Item Price Overlap)

**Reference:** `dev-docs/analysis/phase-4.7-db-schema-sync-3-plan.md` - Phase 4, Task 7
**Authority (Dual Master):**
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - Golden Master JSON
- `dev-docs/db-design/aevofab-db-schema-dump-phase-4.6-post.sql` - Production SQL Dump (Phase 4.6 Baseline)
**Type:** Phase 4 - Data Integrity Enforcement
**Priority:** MEDIUM
**Change Type:** MIGRATION

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

**Phase 4.7 Status (Prior Tasks):**
- ✅ Task 1: Convert `customer.type` ENUM → TEXT (582/582 unit, 609/609 total)
- ✅ Task 2: Convert `user.preferred_mfa_channel` ENUM → TEXT (591/591 unit, 618/618 total)
- ✅ Task 3: Fix `tax_rate_version_id` FK type mismatches (597/597 unit, 624/624 total)
- ✅ Task 4: Fix `ux_global_primary_email` unique index logic (602/602 unit, 629/629 total)
- ✅ Task 5: Add missing DEFAULT values (35+ columns) (605/605 unit, 632/632 total)
- ✅ Task 6: Add missing CHECK constraints (605/605 unit, 632/632 total)

**Current Baseline:** 605/605 unit tests, 632/632 total tests passing (100%)

**See:**
- `dev-docs/analysis/phase-4.5-db-schema-sync-to-design-plan.md` for Phase 4.5 history
- `dev-docs/analysis/phase-4.6-db-schema-sync-2-plan.md` for Phase 4.6 history

---

## Current Task: Add Missing EXCLUDE Constraint (Supplier Item Price Overlap)

**Effort:** 0.5 days
**Gap Reference:** Phase 4.7 Analysis - Section 4 (Data Integrity Enforcement - Exclusion Constraints)
**Change Type:** MIGRATION

The JSON schema defines an EXCLUDE constraint `sip_no_overlap` on `supplier_item_price` to prevent overlapping price date ranges for the same supplier item within a tenant, but this constraint is **missing from the physical database**. This creates a business logic risk where conflicting price ranges could be inserted, causing ambiguity in pricing calculations.

### What Needs to Be Fixed

| # | Component | Issue | Direction | Complexity |
|---|-----------|-------|-----------|------------|
| **1** | `supplier_item_price` | Missing EXCLUDE constraint preventing overlapping valid_period ranges for same supplier_item_id + tenant_id | JSON→SQL | MEDIUM |

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

**Record the output of both results:** `605/605 & 632/632 tests passing` (Phase 4.7 baseline - Task 6 completion)

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

#### For MIGRATION Tasks (Phase 4.7 - All Phases Have Migrations)

**Problem:** 
The JSON schema defines an EXCLUDE constraint `sip_no_overlap` on `supplier_item_price` to prevent overlapping price date ranges for the same supplier item within a tenant. This constraint is **missing from the physical database**.

**Business Impact:**
Without this constraint, the system could insert conflicting price records:
- Supplier Item 123, Tenant 1, Price valid 2024-01-01 to 2024-12-31 ($100)
- Supplier Item 123, Tenant 1, Price valid 2024-06-01 to 2025-06-01 ($150) → **Should be REJECTED but isn't**

This causes ambiguity: Which price applies on 2024-07-15? The constraint ensures only one valid price range exists at any point in time.

**Current State (Missing Constraint):**
```sql
-- Database: No EXCLUDE constraint exists
-- Table: supplier_item_price
--   - supplier_item_id (FK to supplier_item)
--   - tenant_id (FK to tenant)
--   - valid_period (TSTZRANGE - timestamptz range type)
--   - No constraint preventing overlaps!
```

**JSON Schema (Correct Definition):**
```json
{
  "table": "supplier_item_price",
  "constraints": {
    "exclude": [
      {
        "name": "sip_no_overlap",
        "using": "gist",
        "elements": [
          {"column": "supplier_item_id", "operator": "="},
          {"column": "tenant_id", "operator": "="},
          {"column": "valid_period", "operator": "&&"}
        ]
      }
    ]
  }
}
```

**Required Migration SQL:**
```sql
-- Pre-migration validation (Run BEFORE migration)
-- Find overlapping price ranges (should be 0 rows)
SELECT 
  a.id AS price_a_id,
  b.id AS price_b_id,
  a.supplier_item_id,
  a.tenant_id,
  a.valid_period AS a_period,
  b.valid_period AS b_period
FROM supplier_item_price a
JOIN supplier_item_price b 
  ON a.supplier_item_id = b.supplier_item_id
  AND a.tenant_id = b.tenant_id
  AND a.id < b.id
WHERE a.valid_period && b.valid_period;

-- Migration upgrade():
-- Step 1: Ensure btree_gist extension exists (required for EXCLUDE with =)
CREATE EXTENSION IF NOT EXISTS btree_gist;

-- Step 2: Add EXCLUDE constraint
ALTER TABLE supplier_item_price
ADD CONSTRAINT sip_no_overlap
EXCLUDE USING gist (
  supplier_item_id WITH =,
  tenant_id WITH =,
  valid_period WITH &&
);

-- Migration downgrade():
ALTER TABLE supplier_item_price
DROP CONSTRAINT sip_no_overlap;

-- Note: Don't drop btree_gist extension (other constraints may use it)
```

**Database Verification Query:**
```sql
-- Verify constraint exists after migration
SELECT
  con.conname AS constraint_name,
  con.contype AS constraint_type,
  pg_get_constraintdef(con.oid) AS constraint_definition
FROM pg_constraint con
JOIN pg_class rel ON rel.oid = con.conrelid
WHERE rel.relname = 'supplier_item_price'
  AND con.conname = 'sip_no_overlap';

-- Expected output:
-- constraint_name: sip_no_overlap
-- constraint_type: x (exclusion)
-- constraint_definition: EXCLUDE USING gist (supplier_item_id WITH =, tenant_id WITH =, valid_period WITH &&)
```

**SQLModel Fix:**
No SQLModel changes required. SQLModel/SQLAlchemy doesn't support EXCLUDE constraints in `__table_args__`. The constraint must be managed through Alembic migrations only.

However, for documentation purposes, you may add a comment:
```python
# backend/app/models/catalog.py
class SupplierItemPrice(TenantIsolatedMixin, SQLModel, table=True):
    __tablename__ = "supplier_item_price"
    __table_args__ = (
        # Note: EXCLUDE constraint 'sip_no_overlap' defined in migration
        # Prevents overlapping valid_period ranges for same supplier_item_id + tenant_id
        # See: phase_4_7_add_missing_exclude_constraint_task7.py
    )
    
    supplier_item_id: int = Field(foreign_key="supplier_item.id", nullable=False)
    valid_period: str = Field(nullable=False)  # TSTZRANGE type
    # ... other fields ...
```

---

### 2. Implementation Order

**For MIGRATION Tasks (Phase 4, Task 7):**

1. **✅ Establish Regression Baseline** (605/605 unit, 632/632 total tests)
2. **Pre-Migration Data Validation**
   - Run validation query to find overlapping price ranges
   - If overlaps found, manually resolve conflicts before proceeding
3. **Generate Alembic Migration**
   ```bash
   cd backend
   source .venv/bin/activate
   alembic revision --autogenerate -m "phase_4_7_add_missing_exclude_constraint_task7"
   ```
4. **Review & Enhance Migration**
   - **CRITICAL:** Remove any `audit.event` table creation/drop statements
   - Add pre-migration validation query as comment
   - Add btree_gist extension creation
   - Add EXCLUDE constraint
   - Ensure downgrade() drops constraint only (not extension)
5. **Apply Migration**
   ```bash
   alembic upgrade head
   ```
6. **Create Test Suite**
   - Create `backend/tests/test_phase_4_7_supplier_price_overlap.py`
   - Use `db_session` parameter (not `session`)
   - Use `select()` + `exec()` pattern (not `query()`)
7. **Run New Tests**
   ```bash
   pytest tests/test_phase_4_7_supplier_price_overlap.py -v
   ```
8. **Run Regression Tests** (see "After You Complete" section)
9. **Update Documentation**

---

### 3. Test Requirements

**⚠️ ZERO REGRESSION POLICY:**
- **ALL 605 existing unit tests MUST still pass**
- **ALL 632 total tests (including integration) MUST still pass**
- **New tests MUST pass**
- **Target: 100% pass rate on both test suites**

#### For MIGRATION Tasks (Phase 4.7 Task 7)

**Test File:** `backend/tests/test_phase_4_7_supplier_price_overlap.py`

**Required Coverage (Minimum 4 Tests):**
```python
"""
Test Suite: Phase 4.7 Task 7 - Supplier Item Price Overlap Prevention
Tests EXCLUDE constraint enforcement - final schema alignment for production deployment

Reference: phase-4.7-db-schema-sync-3-plan.md - Phase 4, Task 7
"""
import pytest
from datetime import datetime, timezone
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from app.models.catalog import SupplierItemPrice, SupplierItem, Supplier

# ✅ CORRECT: Use db_session parameter and select()/exec() pattern

class TestSupplierPriceOverlapPrevention:
    """Test EXCLUDE constraint prevents overlapping price date ranges"""
    
    def test_non_overlapping_adjacent_ranges_allowed(
        self, db_session: Session, test_tenant, test_supplier, test_supplier_item
    ):
        """Adjacent non-overlapping date ranges should be allowed"""
        # Price 1: 2024-01-01 to 2024-12-31
        price1 = SupplierItemPrice(
            tenant_id=test_tenant.id,
            supplier_item_id=test_supplier_item.id,
            valid_period="[2024-01-01 00:00:00+00,2024-12-31 23:59:59+00]",
            unit_price_cents=10000
        )
        db_session.add(price1)
        db_session.commit()
        
        # Price 2: 2025-01-01 to 2025-12-31 (adjacent, no overlap)
        price2 = SupplierItemPrice(
            tenant_id=test_tenant.id,
            supplier_item_id=test_supplier_item.id,
            valid_period="[2025-01-01 00:00:00+00,2025-12-31 23:59:59+00]",
            unit_price_cents=12000
        )
        db_session.add(price2)
        db_session.commit()  # Should succeed
        
        # Verify both exist
        prices = db_session.exec(
            select(SupplierItemPrice)
            .where(SupplierItemPrice.supplier_item_id == test_supplier_item.id)
            .order_by(SupplierItemPrice.id)
        ).all()
        assert len(prices) == 2
    
    def test_overlapping_ranges_rejected(
        self, db_session: Session, test_tenant, test_supplier, test_supplier_item
    ):
        """Overlapping date ranges for same supplier item + tenant should be rejected"""
        # Price 1: 2024-01-01 to 2024-12-31
        price1 = SupplierItemPrice(
            tenant_id=test_tenant.id,
            supplier_item_id=test_supplier_item.id,
            valid_period="[2024-01-01 00:00:00+00,2024-12-31 23:59:59+00]",
            unit_price_cents=10000
        )
        db_session.add(price1)
        db_session.commit()
        
        # Price 2: 2024-06-01 to 2025-06-01 (overlaps with Price 1)
        price2 = SupplierItemPrice(
            tenant_id=test_tenant.id,
            supplier_item_id=test_supplier_item.id,
            valid_period="[2024-06-01 00:00:00+00,2025-06-01 23:59:59+00]",
            unit_price_cents=12000
        )
        db_session.add(price2)
        
        # Should fail with exclusion constraint violation
        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()
        assert "sip_no_overlap" in str(exc_info.value)
        
        db_session.rollback()
    
    def test_different_tenant_same_range_allowed(
        self, db_session: Session, test_tenant, test_supplier, test_supplier_item
    ):
        """Different tenants can have same supplier item with overlapping ranges"""
        # Create second tenant
        from app.models.core import Tenant
        tenant2 = Tenant(name="Tenant 2", business_name="Tenant 2 LLC")
        db_session.add(tenant2)
        db_session.commit()
        
        # Price 1: Tenant 1, 2024-01-01 to 2024-12-31
        price1 = SupplierItemPrice(
            tenant_id=test_tenant.id,
            supplier_item_id=test_supplier_item.id,
            valid_period="[2024-01-01 00:00:00+00,2024-12-31 23:59:59+00]",
            unit_price_cents=10000
        )
        db_session.add(price1)
        db_session.commit()
        
        # Price 2: Tenant 2, 2024-01-01 to 2024-12-31 (same range, different tenant)
        price2 = SupplierItemPrice(
            tenant_id=tenant2.id,
            supplier_item_id=test_supplier_item.id,
            valid_period="[2024-01-01 00:00:00+00,2024-12-31 23:59:59+00]",
            unit_price_cents=12000
        )
        db_session.add(price2)
        db_session.commit()  # Should succeed (different tenant)
        
        # Verify both exist
        prices = db_session.exec(
            select(SupplierItemPrice)
            .where(SupplierItemPrice.supplier_item_id == test_supplier_item.id)
        ).all()
        assert len(prices) == 2
    
    def test_different_supplier_item_same_range_allowed(
        self, db_session: Session, test_tenant, test_supplier
    ):
        """Different supplier items can have overlapping ranges"""
        # Create two supplier items
        from app.models.catalog import SupplierItem
        item1 = SupplierItem(
            tenant_id=test_tenant.id,
            supplier_id=test_supplier.id,
            supplier_sku="SKU-001"
        )
        item2 = SupplierItem(
            tenant_id=test_tenant.id,
            supplier_id=test_supplier.id,
            supplier_sku="SKU-002"
        )
        db_session.add_all([item1, item2])
        db_session.commit()
        
        # Price 1: Item 1, 2024-01-01 to 2024-12-31
        price1 = SupplierItemPrice(
            tenant_id=test_tenant.id,
            supplier_item_id=item1.id,
            valid_period="[2024-01-01 00:00:00+00,2024-12-31 23:59:59+00]",
            unit_price_cents=10000
        )
        db_session.add(price1)
        db_session.commit()
        
        # Price 2: Item 2, 2024-01-01 to 2024-12-31 (same range, different item)
        price2 = SupplierItemPrice(
            tenant_id=test_tenant.id,
            supplier_item_id=item2.id,
            valid_period="[2024-01-01 00:00:00+00,2024-12-31 23:59:59+00]",
            unit_price_cents=12000
        )
        db_session.add(price2)
        db_session.commit()  # Should succeed (different supplier item)
        
        # Verify both exist
        prices = db_session.exec(select(SupplierItemPrice)).all()
        assert len(prices) == 2
```

**Test Patterns to Follow:**
- Review `backend/tests/test_temporal_exclusion_constraints_task10.py` - Shows EXCLUDE constraint testing patterns
- Review `backend/tests/test_check_constraints_task9.py` - Shows proper constraint testing
- Use fixtures from `backend/tests/conftest.py`

**Common Test Fixtures Available:**
- `db_session` - Database session (use this, NOT `session`)
- `test_tenant` - Pre-created tenant for testing
- `test_user` - Pre-created user linked to test_tenant
- `test_customer` - Pre-created customer
- `test_site` - Pre-created site
- `utc_now` - Timezone-aware current timestamp function

**Additional Fixtures Needed:**
You may need to add fixtures for:
- `test_supplier` - Pre-created supplier
- `test_supplier_item` - Pre-created supplier item

Check if these exist in conftest.py, or create them within the test file using session scope.

---

### 4. JSON Change Tracking

**Not Applicable:** This is a MIGRATION task. The JSON schema already has the correct definition; we're adding the missing constraint to the physical database.

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

# Run ALL tests
pytest tests/ -v 2>&1 | grep -E "(passed|failed|===)" | tail -5
```

**Expected:**
- **For MIGRATION tasks:** `[605 + 4] = 609 passed` (unit), `[632 + 4] = 636 passed` (total)

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

Find Phase 4, Task 7 and update with:

```markdown
### Task 7: Add Missing EXCLUDE Constraint (Supplier Item Price Overlap)

**Status:** ✅ COMPLETE (YYYY-MM-DD)
**Effort:** 0.5 days (actual)
**Change Type:** MIGRATION

**Implementation Summary:**

- Modified: No SQLModel changes (EXCLUDE constraints managed via Alembic only)
- Migration: `YYYY_MM_DD_HHMM-[hash]_phase_4_7_add_missing_exclude_constraint_task7.py`
- Test Suite: `test_phase_4_7_supplier_price_overlap.py` - 4 tests ✅
- Final Results: 609/609 unit tests passing (100%), 636/636 total tests passing (100%)

**Key Changes:**
- ✅ Added btree_gist extension (required for EXCLUDE with equality operators)
- ✅ Added EXCLUDE constraint `sip_no_overlap` to prevent overlapping price date ranges
- ✅ Verified zero existing overlapping data before applying constraint
- ✅ Constraint enforces: same supplier_item_id + tenant_id cannot have overlapping valid_period

**Verification:**
- Constraint active and preventing overlapping ranges
- Adjacent non-overlapping ranges still allowed
- Different tenants can have overlapping ranges (correct isolation)
- Migration rollback tested successfully
```

---

## Success Criteria

**MUST COMPLETE ALL BEFORE MARKING TASK AS DONE:**

### For MIGRATION Tasks (Task 7):
- [ ] **Regression baseline captured** (605/605 unit, 632/632 total tests)
- [ ] **Pre-migration data validation completed** (queries run, no overlaps found)
- [ ] **btree_gist extension verified** or created in migration
- [ ] **Used `db_session` parameter** (not `session`) in tests
- [ ] **Used `select()/exec()` pattern** (not `query()`) in tests
- [ ] **Alembic migration created** using autogenerate
- [ ] **⚠️ CRITICAL: Checked migration for `audit.event` table** and removed if present
- [ ] **Migration applied successfully** (`alembic upgrade head`)
- [ ] **All 4 new tests written and passing**
- [ ] **Tests use `db_session` parameter** and `select()/exec()` pattern
- [ ] **ALL 605 existing unit tests still passing**
- [ ] **ALL 632 total tests still passing** (including integration)
- [ ] **New total: 609/609 unit passing, 636/636 total passing (100%)**
- [ ] **Database verification query confirms** EXCLUDE constraint active
- [ ] **Migration rollback tested** (`alembic downgrade -1` then `upgrade head` again)
- [ ] **Project plan document updated**

### For ALL Tasks:
- [ ] **100% test pass rate** - No failing tests
- [ ] **Zero regression** - Baseline maintained or exceeded

---

## Key Files to Review

### Architecture & Design
- `dev-docs/analysis/phase-4.7-db-schema-sync-3-plan.md` - **Task 7 Details** ⭐
- `dev-docs/analysis/phase-4.7-db-schema-sync-3-analysis.md` - Forensic Analysis
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - **Golden Master JSON**
- `dev-docs/db-design/aevofab-db-schema-dump-phase-4.6-post.sql` - **Production SQL Dump (Phase 4.6 Baseline)**

### Backend Code
- `backend/app/models/catalog.py` - SupplierItemPrice model

### Tests (Reference for Patterns)
- `backend/tests/test_temporal_exclusion_constraints_task10.py` - EXCLUDE constraint testing patterns ⭐
- `backend/tests/test_check_constraints_task9.py` - CHECK constraint patterns
- `backend/tests/conftest.py` - Test fixtures (`db_session`, `test_tenant`, etc.)

---

## Risk Assessment

**Data Validation Risk:** MEDIUM
- Must verify no existing overlapping price ranges before migration
- If overlaps exist, must manually resolve conflicts
- **Mitigation:** Run pre-migration validation query, clean data if needed

**Regression Risk:** LOW
- EXCLUDE constraints don't affect existing valid data
- Only prevents future invalid inserts
- **Mitigation:** Maintain 605/632 baseline, test after migration

**Performance Risk:** LOW
- GIST indexes are efficient for range overlaps
- Minimal overhead for constraint checking
- **Mitigation:** Monitor query performance on supplier_item_price table

---

## Notes

### Important Patterns to Follow
- **Virtual Environment Required:** All Python/pytest commands use `source .venv/bin/activate`
- **Use `db_session` Parameter:** NOT `session` (pytest fixture naming)
- **Use `select()/exec()` Pattern:** NOT `query()` (SQLModel standard, no deprecation warnings)
- **Check Alembic Migrations:** ALWAYS remove `audit.event` table creation if autogenerated
- **Pre-Validate Data:** Run validation queries BEFORE applying constraints
- **Extension Required:** btree_gist extension needed for EXCLUDE with equality operators

### Phase 4.7 Specific
- **Final production alignment** - Last schema sync before deployment
- **Task 7 is EXCLUDE constraint** - Prevents overlapping price ranges
- **TSTZRANGE overlap operator:** `&&` checks if two ranges overlap
- **Tenant isolation:** Different tenants can have overlapping ranges (correct behavior)
- **Pre-validate all data** - Run validation queries BEFORE applying constraints

### If You Get Stuck
- Check the SQL dump for exact production definitions
- Review Phase 4.5 Task 10 for EXCLUDE constraint patterns (temporal exclusion)
- Use `postgres-local` MCP server to query database in real-time
- Search existing tests for `db_session` and `exec()` patterns
- Review the "Best Practices" section at the top of this template
- Remember: btree_gist extension is required for EXCLUDE with equality operators

---

## Example Task Flow

### For MIGRATION Tasks (Task 7):

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

# 2. Pre-migration data validation (CRITICAL!)
# Use postgres-local MCP to check for overlapping ranges
# Query: Check for overlapping valid_period for same supplier_item_id + tenant_id
# Expected: 0 rows (no overlaps)
# If overlaps found: STOP and resolve manually before proceeding

# 3. Generate migration
alembic revision --autogenerate -m "phase_4_7_add_missing_exclude_constraint_task7"

# 4. ⚠️ CRITICAL: Review migration file
# Open backend/migrations/versions/[timestamp]_phase_4_7_add_missing_exclude_constraint_task7.py
# Search for 'audit' and 'event'
# DELETE any op.create_table('event', ... schema='audit') blocks
# DELETE any op.drop_table('event', ... schema='audit') blocks
# Verify EXCLUDE constraint addition is present
# Add pre-migration validation query as comment
# Ensure btree_gist extension creation is included

# 5. Apply migration
alembic upgrade head

# 6. Create test suite
# Create backend/tests/test_phase_4_7_supplier_price_overlap.py
# - Use db_session: Session parameter
# - Use select() with exec()
# - Test non-overlapping ranges allowed
# - Test overlapping ranges rejected
# - Test different tenant same range allowed
# - Test different supplier item same range allowed

# 7. Run new tests
pytest tests/test_phase_4_7_supplier_price_overlap.py -v
# All new tests should pass

# 8. Regression check - Ensure no breaks
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Expected: 609 passed (605 + 4)

pytest tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Expected: 636 passed (632 + 4)

# 9. Rollback test - Verify downgrade works
alembic downgrade -1
alembic upgrade head
pytest tests/ -v  # Should still pass

# 10. Update docs
# Edit dev-docs/analysis/phase-4.7-db-schema-sync-3-plan.md
# Mark task as complete with test results
```

---

## Questions to Ask

**Before starting:**
1. Have I captured the 605/605 unit and 632/632 total baselines?
2. Have I run the pre-migration validation query to check for overlapping price ranges?
3. If overlaps were found, have they been resolved?
4. Do I understand TSTZRANGE and the `&&` overlap operator?
5. Do I understand why btree_gist extension is required?

**During implementation:**
1. Am I using `db_session` parameter (NOT `session`) in tests?
2. Am I using `select()/exec()` pattern (NOT `query()`) in tests?
3. After running `alembic revision --autogenerate`, did I check for and remove `audit.event` table creation?
4. Did I include btree_gist extension creation in the migration?
5. Are my tests covering all scenarios: overlapping, adjacent, different tenant, different item?

**After implementation:**
1. Do I have 100% test pass rate on BOTH unit tests (609) and total tests (636)?
2. Does the EXCLUDE constraint actively prevent overlapping ranges?
3. Have I tested migration rollback (`alembic downgrade -1`)?
4. Have I updated the project plan document?
5. Have I verified the constraint via database query?

---

**Ready to Begin!** 🚀

### MIGRATION Task Checklist (Task 7):
1. ✅ Capture baseline (605/605 unit, 632/632 total)
2. 🔍 Validate existing data (run pre-migration query for overlaps)
3. 📝 Generate migration (`alembic revision --autogenerate`)
4. ⚠️ **CRITICAL: Remove `audit.event` table from migration if present**
5. ✅ Ensure btree_gist extension creation included
6. ✅ Apply migration (`alembic upgrade head`)
7. 🧪 Create comprehensive tests (4 tests: adjacent OK, overlap rejected, different tenant OK, different item OK)
8. 🔄 Run regression tests (609 unit, 636 total)
9. ↩️ Test rollback (`alembic downgrade -1`, then `upgrade head`)
10. 📚 Update project plan

Remember: Phase 4.7 is about **final production alignment** - data integrity enforcement through database constraints. The EXCLUDE constraint prevents overlapping price ranges, ensuring unambiguous pricing for supplier items. Be thorough with pre-migration validation to catch any existing overlaps!
