# Task 1: SQLModel Exclusion Constraint & Index Definitions Verification

**Reference:** `dev-docs/analysis/phase-5.2-db-schema-sync-8-plan.md` - Task 1
**Authority (Golden Master):**
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - Golden Master JSON
- `dev-docs/analysis/phase-5.2-db-schema-sync-8-analysis.md` - **Exclusion Constraints & Index Gap Analysis** ⭐
- Current Live Database (Phase 5.1 Post-State)
**Type:** Phase 5.2 - Exclusion Constraints & Critical Performance Indexes
**Priority:** CRITICAL
**Change Type:** MODEL VERIFICATION

---

## Context

This is **Phase 5.2 - DB Sync v#8**, a focused surgical sync to fix flawed exclusion constraints and add critical performance indexes. A forensic comparison revealed **4 critical gaps** in the physical database that don't match the Golden Master JSON.

**Root Cause:** 
- Exclusion constraints missing COALESCE logic for NULL-safe comparisons
- Exclusion constraint missing tenant_id parameter for multi-tenant isolation
- Performance indexes not created during initial table setup

**Critical Impact:**
- **Data Integrity Risk:** Flawed exclusion constraints allow overlapping temporal periods (violates temporal data integrity)
- **Multi-Tenancy Breach:** Missing tenant_id in exclusion constraint allows cross-tenant temporal overlaps
- **Performance Degradation:** Missing indexes cause O(n) queries instead of O(log n) for webhook workers and dashboards
- **Scalability Risk:** Webhook delivery queue will exponentially slow down without compound index

**Scope:** **2 exclusion constraint fixes + 3 missing indexes across 4 tables** - Small but critical fixes requiring constraint recreation and index creation.

**Key Principle:** Exclusion constraints require PostgreSQL btree_gist extension and MUST be dropped and recreated (not ALTERed). Validate no existing data violates constraints before applying.

---

## What Was Completed in Previous Phases

**Phase 5.1 Status:** ✅ COMPLETE (April 11, 2026)
- ✅ 10 missing constraints added (8 unique + 2 foreign keys)
- ✅ 648/648 unit tests, 675/675 total tests passing (100%)
- ✅ Database schema fully aligned with Golden Master for constraint coverage

**Current Baseline:** 648/648 unit tests, 675/675 total tests passing (100%)

**Previous Phases:**
- **Phase 4.5-4.9:** ✅ COMPLETE - Full schema synchronization
- **Phase 5.0:** ✅ COMPLETE - Server defaults enforcement
- **Phase 5.1:** ✅ COMPLETE - Missing unique constraints & foreign keys

**See:**
- `dev-docs/analysis/phase-5.1-db-schema-sync-7-plan.md` for Phase 5.1 history
- `dev-docs/analysis/phase-5.2-db-schema-sync-8-analysis.md` for constraint/index gap details

---

## Current Task: SQLModel Exclusion Constraint & Index Definitions Verification

**Effort:** 0.25 days
**Gap Reference:** Phase 5.2 Analysis - Exclusion Constraints & Performance Indexes
**Change Type:** MODEL VERIFICATION

This task verifies that all 4 missing constraints/indexes are correctly defined in the Python SQLModel definitions. We'll confirm COALESCE logic is present in exclusion constraints and that all performance indexes are properly configured. If any definitions are missing or incorrect, we'll update them to match the Golden Master JSON schema.

### What Needs to Be Fixed

**Model Files & Required Fixes:**

| Model File | Table | Issue | Required Fix |
|-----------|-------|-------|-------------|
| `backend/app/models/supplier_item_price.py` | `supplier_item_price` | `sip_no_overlap` missing COALESCE logic | Add `COALESCE(tenant_id, '00000000-0000-0000-0000-000000000000')` |
| `backend/app/models/pricebook_item_version.py` | `pricebook_item_version` | `piv_no_overlap` missing tenant_id | Add `tenant_id` as first parameter |
| `backend/app/models/webhook_delivery_attempt.py` | `webhook_delivery_attempt` | Missing index | Add `idx_webhook_delivery_pending` on `(status, next_attempt_after)` |
| `backend/app/models/webhook_event.py` | `webhook_event` | Missing 2 indexes | Add `idx_webhook_event_tenant_time` and `idx_webhook_event_entity` |

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

**Record the output of both results:** `648/648 & 675/675 tests passing` (Phase 5.2 baseline - starting from Phase 5.1 completion)

### Step 3: Document Your Baseline

**Write down both of these numbers before proceeding**

**This is your regression checkpoint. ALL these tests MUST still pass after your work.**

---

## ⚠️ CRITICAL: Phase 5.2 Specific Warnings

**BEFORE writing ANY code, review these Phase 5.2 critical issues:**

### 1. Exclusion Constraints CANNOT Be Modified - Must Drop & Recreate

**Critical Rule:** You CANNOT ALTER an exclusion constraint. You must DROP it and CREATE a new one.

**Why This Matters:**
```sql
-- ❌ WRONG - This will fail:
ALTER TABLE supplier_item_price 
ALTER CONSTRAINT sip_no_overlap ... -- PostgreSQL doesn't support this

-- ✅ CORRECT - Drop and recreate:
ALTER TABLE supplier_item_price DROP CONSTRAINT sip_no_overlap;
ALTER TABLE supplier_item_price ADD CONSTRAINT sip_no_overlap 
  EXCLUDE USING gist (...);
```

**Impact:** During the DROP/CREATE window, the constraint is NOT enforced. Migration MUST run in a transaction to prevent data corruption.

---

### 2. Exclusion Constraints Require btree_gist Extension

**CRITICAL:** Before creating any exclusion constraint, verify the extension exists:

```sql
-- Verify extension installed
SELECT * FROM pg_extension WHERE extname = 'btree_gist';
-- If not found, run:
CREATE EXTENSION IF NOT EXISTS btree_gist;
```

**Why:** GIST indexes with `=` operator on UUID/TEXT columns require btree_gist extension. Without it, constraint creation will fail.

---

### 3. COALESCE Logic for NULL-Safe Exclusion Constraints

**Problem:** In `supplier_item_price`, the `tenant_id` column can be NULL (tenant-agnostic pricing). 

**SQL NULL Behavior:** In exclusion constraints, `NULL != NULL` (NULL values are never equal to each other).

**Impact Without COALESCE:**
```sql
-- Both of these would succeed (WRONG - they overlap!):
INSERT INTO supplier_item_price (supplier_item_id, tenant_id, valid_period)
VALUES ('item-123', NULL, '[2024-01-01, 2024-12-31)');

INSERT INTO supplier_item_price (supplier_item_id, tenant_id, valid_period)
VALUES ('item-123', NULL, '[2024-06-01, 2025-06-01)'); -- OVERLAPS but would succeed!
```

**Solution:** Use `COALESCE(tenant_id, '00000000-0000-0000-0000-000000000000')` to treat NULL as a sentinel UUID:

```sql
EXCLUDE USING gist (
  supplier_item_id WITH =,
  COALESCE(tenant_id, '00000000-0000-0000-0000-000000000000'::uuid) WITH =,
  valid_period WITH &&
)
```

Now NULL values are treated as the sentinel UUID, and overlaps are correctly detected.

---

### 4. Temporal Overlap Detection with tstzrange

**Phase 5.2 involves temporal exclusion constraints** using PostgreSQL's `tstzrange` (timestamp with time zone range) type.

**Overlap Operator:** `&&` - Returns TRUE if two ranges overlap

**Examples:**
```sql
-- Overlapping periods (would violate constraint):
'[2024-01-01, 2024-12-31)'::tstzrange && '[2024-06-01, 2025-06-01)'::tstzrange
-- TRUE (they overlap from June to December)

-- Adjacent periods (no overlap, constraint allows):
'[2024-01-01, 2024-06-01)'::tstzrange && '[2024-06-01, 2024-12-31)'::tstzrange
-- FALSE (end of first = start of second, no overlap due to exclusive upper bound)

-- Disjoint periods (no overlap, constraint allows):
'[2024-01-01, 2024-06-01)'::tstzrange && '[2025-01-01, 2025-12-31)'::tstzrange
-- FALSE (completely separate periods)
```

**Critical Detail:** `tstzrange` uses `[lower, upper)` notation where lower is INCLUSIVE and upper is EXCLUSIVE.

---

### 5. Index Creation Should Use CONCURRENTLY Flag

**Best Practice:** Create indexes with the CONCURRENT flag to avoid table locks:

```sql
-- ✅ RECOMMENDED (no table lock):
CREATE INDEX CONCURRENTLY idx_webhook_delivery_pending 
ON webhook_delivery_attempt (status, next_attempt_after);

-- ❌ RISKY (locks entire table):
CREATE INDEX idx_webhook_delivery_pending 
ON webhook_delivery_attempt (status, next_attempt_after);
```

**Trade-off:** CONCURRENTLY takes longer but allows other transactions to continue. For production systems, always use CONCURRENTLY.

**Important:** CONCURRENTLY cannot run inside a transaction block. Alembic migrations using `op.execute()` should use CONCURRENTLY.

---

### 6. Compound Indexes Have Column Order Requirements

**Critical Rule:** Column order in compound indexes matters for query performance.

**Example:** `idx_webhook_delivery_pending (status, next_attempt_after)`

**Query Pattern:**
```sql
-- This query WILL use the index:
SELECT * FROM webhook_delivery_attempt
WHERE status = 'pending' AND next_attempt_after <= NOW();

-- This query will also use the index (prefix match):
SELECT * FROM webhook_delivery_attempt
WHERE status = 'pending';

-- This query will NOT use the index (skips first column):
SELECT * FROM webhook_delivery_attempt
WHERE next_attempt_after <= NOW();
```

**Rule:** Index is only used if query filters on the first column (or first N columns in order).

---

### 7. Validation Queries Must Check for Temporal Overlaps

**MANDATORY Pre-Migration Validation for Exclusion Constraints:**

Unlike unique constraints (check for duplicates), exclusion constraints require checking for **overlapping ranges**.

**Example Validation Query:**
```sql
-- Check for overlapping supplier_item_price periods
SELECT 
    sip1.id AS id1, 
    sip2.id AS id2,
    sip1.supplier_item_id,
    COALESCE(sip1.tenant_id::text, 'NULL') AS tenant1,
    COALESCE(sip2.tenant_id::text, 'NULL') AS tenant2,
    sip1.valid_period,
    sip2.valid_period
FROM supplier_item_price sip1
JOIN supplier_item_price sip2 
  ON sip1.supplier_item_id = sip2.supplier_item_id
  AND COALESCE(sip1.tenant_id, '00000000-0000-0000-0000-000000000000'::uuid) = 
      COALESCE(sip2.tenant_id, '00000000-0000-0000-0000-000000000000'::uuid)
  AND sip1.valid_period && sip2.valid_period  -- Overlap operator
  AND sip1.id < sip2.id;  -- Prevent duplicate pairs
-- Expected: 0 rows (no overlaps)
```

**If ANY rows returned:** You have overlapping temporal periods that MUST be resolved before applying the constraint.

---

## ⚠️ CRITICAL: Coding Agent Best Practices (From Previous Phases)

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

**Why:** The pytest fixture is named `db_session` in `backend/tests/conftest.py`.

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

---

### 3. Test Exclusion Constraints with pytest.raises(IntegrityError)

**Pattern for Testing Temporal Overlap Prevention:**
```python
import pytest
from sqlalchemy.exc import IntegrityError
from datetime import date

def test_exclusion_constraint_prevents_overlaps(db_session):
    # Insert first temporal record
    db_session.execute(text("""
        INSERT INTO supplier_item_price 
        (supplier_item_id, tenant_id, valid_period, price_cents)
        VALUES (:item_id, NULL, '[2024-01-01, 2024-12-31)'::tstzrange, 10000)
    """), {"item_id": "item-123"})
    
    # Attempt overlapping period (should fail)
    with pytest.raises(IntegrityError) as exc_info:
        db_session.execute(text("""
            INSERT INTO supplier_item_price 
            (supplier_item_id, tenant_id, valid_period, price_cents)
            VALUES (:item_id, NULL, '[2024-06-01, 2025-06-01)'::tstzrange, 12000)
        """), {"item_id": "item-123"})
    
    assert "exclusion constraint" in str(exc_info.value).lower()
    db_session.rollback()
```

---

## Requirements

### Task 1: SQLModel Exclusion Constraint & Index Definitions Verification

**Effort:** 0.25 days
**Scope:** Verify 2 exclusion constraints + 3 performance indexes in Python models

#### What This Task Accomplishes

Confirm that all 4 missing constraints/indexes are correctly defined in the Python SQLModel definitions. Verify COALESCE logic is present in exclusion constraints. If any are missing or incorrect, update them.

#### Tables to Check

**Model Files & Tables:**
1. `backend/app/models/supplier_item_price.py`
   - **Issue:** `sip_no_overlap` constraint missing COALESCE logic
   - **Fix:** Update to use `COALESCE(tenant_id, '00000000-0000-0000-0000-000000000000')`

2. `backend/app/models/pricebook_item_version.py`
   - **Issue:** `piv_no_overlap` constraint missing `tenant_id` parameter
   - **Fix:** Add `tenant_id` as first parameter in exclusion constraint

3. `backend/app/models/webhook_delivery_attempt.py`
   - **Issue:** Missing `idx_webhook_delivery_pending` index
   - **Fix:** Add `Index("idx_webhook_delivery_pending", "status", "next_attempt_after")`

4. `backend/app/models/webhook_event.py`
   - **Issue:** Missing 2 compound indexes for query optimization
   - **Fix:** Add `idx_webhook_event_tenant_time` and `idx_webhook_event_entity`

#### Exclusion Constraint Syntax Reference

**Exclusion Constraint with COALESCE (for NULL-safe comparison):**
```python
from sqlalchemy import Column, func, literal
from sqlalchemy.dialects.postgresql import UUID as SQLAlchemyUUID, ExcludeConstraint

class SupplierItemPrice(SQLModel, table=True):
    __tablename__ = "supplier_item_price"
    
    # Columns
    supplier_item_id: uuid.UUID = Field(foreign_key="supplier_item.id")
    tenant_id: Optional[uuid.UUID] = Field(default=None, foreign_key="tenant.id")
    valid_period: str  # tstzrange stored as text in Python
    
    # Table-level constraints
    __table_args__ = (
        # NULL-safe overlap prevention (for tenant-agnostic pricing)
        ExcludeConstraint(
            (Column("supplier_item_id"), "="),
            (
                func.coalesce(
                    Column("tenant_id"), 
                    literal("00000000-0000-0000-0000-000000000000", type_=SQLAlchemyUUID)
                ), 
                "="
            ),
            (Column("valid_period"), "&&"),
            name="sip_no_overlap",
            using="gist",
        ),
        # Tenant-scoped overlap prevention (for tenant-specific pricing)
        ExcludeConstraint(
            (Column("supplier_item_id"), "="),
            (Column("tenant_id"), "="),
            (Column("valid_period"), "&&"),
            name="sip_no_overlap_per_tenant",
            using="gist",
        ),
    )
```

**Exclusion Constraint with Tenant-Scoped Temporal Check:**
```python
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import ExcludeConstraint

class PricebookItemVersion(SQLModel, table=True):
    __tablename__ = "pricebook_item_version"
    
    # Columns
    tenant_id: uuid.UUID = Field(foreign_key="tenant.id")
    pricebook_item_id: uuid.UUID = Field(foreign_key="pricebook_item.id")
    valid_period: str  # tstzrange
    
    # Table-level constraints
    __table_args__ = (
        # Prevent overlapping valid_period for same pricebook_item_id within a tenant
        ExcludeConstraint(
            (Column("tenant_id"), "="),
            (Column("pricebook_item_id"), "="),
            (Column("valid_period"), "&&"),
            name="piv_no_overlap",
            using="gist",
        ),
    )
```

#### Index Syntax Reference

**Compound Index for Worker Queue:**
```python
from sqlalchemy import Index

class WebhookDeliveryAttempt(SQLModel, table=True):
    __tablename__ = "webhook_delivery_attempt"
    
    # Columns
    status: str
    next_attempt_after: Optional[datetime]
    
    # Table-level indexes
    __table_args__ = (
        Index("idx_webhook_delivery_pending", "status", "next_attempt_after"),
        Index("idx_webhook_delivery_event", "webhook_event_id"),
    )
```

**Compound Indexes with DESC Ordering:**
```python
from sqlalchemy import Index, desc

class WebhookEvent(SQLModel, table=True):
    __tablename__ = "webhook_event"
    
    # Columns
    tenant_id: Optional[uuid.UUID]
    entity_type_code: Optional[str]
    entity_id: Optional[uuid.UUID]
    created_at: datetime
    
    # Table-level indexes
    __table_args__ = (
        # Tenant dashboard query optimization
        Index("idx_webhook_event_tenant_time", "tenant_id", desc("created_at")),
        # Entity lookup query optimization
        Index("idx_webhook_event_entity", "entity_type_code", "entity_id", desc("created_at")),
        # Existing indexes
        Index("ix_webhook_event_event_id", "event_id"),
        Index("ix_webhook_event_source_app", "source_app"),
    )
```

**Success Criteria for Task 1:**
- [ ] supplier_item_price `sip_no_overlap` uses COALESCE for NULL-safe comparison
- [ ] pricebook_item_version `piv_no_overlap` includes tenant_id parameter
- [ ] webhook_delivery_attempt has `idx_webhook_delivery_pending` index
- [ ] webhook_event has both `idx_webhook_event_tenant_time` and `idx_webhook_event_entity` indexes
- [ ] Code passes Python syntax validation
- [ ] All models import successfully (`python -c "from app.models import *"`)

---

## 🎯 AFTER YOU COMPLETE - Verify No Regressions

**CRITICAL:** After all work is complete, verify the baseline.

### Step 1: Run Full Test Suite

```bash
cd backend
source .venv/bin/activate

# Run unit tests (no integration)
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Expected: 648 passed (no new tests in this task, just model updates)

# Run all tests
pytest tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Expected: 675 passed (no new tests in this task, just model updates)
```

### Step 2: Verify Model Imports

```bash
# Verify all models import without errors
python -c "from app.models import *"
# Should complete without errors
```

### Step 3: Final Validation

**If ANY tests fail:**
1. Identify failing tests
2. Check if COALESCE syntax is correct in constraint definition
3. Check if tenant_id is first parameter in piv_no_overlap
4. Verify all index definitions are syntactically correct
5. Fix and re-run until 100% pass rate

---

## Documentation Update

**File to Update:** `dev-docs/analysis/phase-5.2-db-schema-sync-8-plan.md`

Find the appropriate section and update with:

```markdown
### Phase 1: Exclusion Constraint Fixes - Task 1 (Model Verification)

**Status:** ✅ COMPLETE (YYYY-MM-DD)
**Effort:** 0.25 days (actual)
**Priority:** CRITICAL

**Implementation Summary:**

- Model Verification: Verified 2 exclusion constraints + 3 indexes in Python models
- supplier_item_price: Updated `sip_no_overlap` with COALESCE logic
- pricebook_item_version: Updated `piv_no_overlap` with tenant_id parameter
- webhook_delivery_attempt: Added `idx_webhook_delivery_pending` index
- webhook_event: Added `idx_webhook_event_tenant_time` and `idx_webhook_event_entity` indexes
- Final Results: 648/648 unit tests (100%), 675/675 total tests (100%)

**Key Changes:**
- ✅ supplier_item_price `sip_no_overlap` constraint definition updated with COALESCE logic
- ✅ pricebook_item_version `piv_no_overlap` constraint definition updated with tenant_id parameter
- ✅ webhook_delivery_attempt `idx_webhook_delivery_pending` index definition added
- ✅ webhook_event `idx_webhook_event_tenant_time` index definition added
- ✅ webhook_event `idx_webhook_event_entity` index definition added
- ✅ All Python models import successfully
- ✅ Zero regressions in existing test suite

**Verification:**
- All model imports complete without errors
- Python syntax validation passed
- Ready for Alembic migration generation (Task 2)
```

---

## Success Criteria

**MUST COMPLETE ALL BEFORE MARKING TASK AS DONE:**

### For Task 1 (Model Verification):
- [ ] **Regression baseline captured** (648/648 unit, 675/675 total)
- [ ] **supplier_item_price model checked** for `sip_no_overlap` constraint
- [ ] **COALESCE logic added** to `sip_no_overlap` if missing
- [ ] **pricebook_item_version model checked** for `piv_no_overlap` constraint
- [ ] **tenant_id parameter added** to `piv_no_overlap` if missing
- [ ] **webhook_delivery_attempt model checked** for indexes
- [ ] **idx_webhook_delivery_pending added** if missing
- [ ] **webhook_event model checked** for indexes
- [ ] **idx_webhook_event_tenant_time added** if missing
- [ ] **idx_webhook_event_entity added** if missing
- [ ] **Python syntax valid** (`python -c "from app.models import *"` succeeds)
- [ ] **ALL 648 existing unit tests still passing**
- [ ] **ALL 675 total tests still passing**
- [ ] **Project plan document updated**

---

## Key Files to Review

### Architecture & Design
- `dev-docs/analysis/phase-5.2-db-schema-sync-8-plan.md` - **Master Plan** ⭐
- `dev-docs/analysis/phase-5.2-db-schema-sync-8-analysis.md` - **Constraint/Index Gap Analysis** ⭐⭐⭐
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - Golden Master JSON

### Backend Models
- `backend/app/models/supplier_item_price.py` - Exclusion constraint fix
- `backend/app/models/pricebook_item_version.py` - Exclusion constraint fix
- `backend/app/models/webhook_delivery_attempt.py` - Worker queue index
- `backend/app/models/webhook_event.py` - Dashboard query indexes

---

## Risk Assessment

**For Task 1 (Model Verification):**
- **Syntax Error Risk:** LOW (can validate with Python import test)
- **Model Import Risk:** LOW (changes are additive constraint/index definitions)
- **Test Impact:** NONE (no test changes in this task)
- **Rollback Complexity:** TRIVIAL (just revert model file changes)
- **Mitigation:** Verify imports after each model file update

---

## Notes

### Important Patterns to Follow
- **COALESCE for NULL:** Use sentinel UUID for NULL-safe exclusion constraints
- **Tenant-Scoped Constraints:** Always include tenant_id as first parameter
- **Compound Indexes:** Column order matters for query optimization
- **DESC Ordering:** Required for descending time-series queries
- **Import Validation:** Test imports after each model change

### Task 1 Specific
- **This task only updates model definitions** - no migrations, no database changes
- **No new tests required** - existing tests will validate migrations in Task 2
- **Verify imports** after each model file update
- **Document changes** in commit messages for review

### If You Get Stuck
- Review existing ExcludeConstraint examples in other model files
- Check SQLAlchemy ExcludeConstraint documentation
- Verify COALESCE syntax in Golden Master JSON
- Use postgres-local MCP to check current database constraint definitions
- Ask for help if spending >15 minutes on single model file

---

## Example Task Flow

### For Task 1 (Model Verification):

```bash
# 1. Baseline
cd backend
source .venv/bin/activate
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Record: 648 passed

# 2. Open first model file
# Edit backend/app/models/supplier_item_price.py
# Find __table_args__ with ExcludeConstraint
# Look for COALESCE logic in sip_no_overlap

# Expected:
class SupplierItemPrice(SQLModel, table=True):
    __table_args__ = (
        ExcludeConstraint(
            (Column("supplier_item_id"), "="),
            (func.coalesce(Column("tenant_id"), literal("00000000-...")), "="),
            (Column("valid_period"), "&&"),
            name="sip_no_overlap",
            using="gist",
        ),
        # ... other constraints
    )

# If missing COALESCE, add it

# 3. Test import after each change
python -c "from app.models.supplier_item_price import SupplierItemPrice"
# Should load without errors

# 4. Repeat for other 3 model files
# - pricebook_item_version.py
# - webhook_delivery_attempt.py
# - webhook_event.py

# 5. Final verification
python -c "from app.models import *"
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Expected: 648 passed (no regressions)

# 6. Update documentation
```

---

## Questions to Ask

**Before starting:**
1. Have I captured the 648/648 unit and 675/675 total baselines?
2. Do I have the Phase 5.2 analysis document open for reference?
3. Do I understand the difference between exclusion constraints and unique constraints?
4. Do I know what COALESCE does for NULL-safe comparisons?

**During Task 1 (Models):**
1. Does sip_no_overlap use COALESCE for NULL-safe comparison?
2. Does piv_no_overlap include tenant_id as the first parameter?
3. Are all 3 performance indexes defined in the models?
4. Is DESC ordering specified for time-series indexes?
5. Do all models import successfully after each change?

**After implementation:**
1. Do I have 100% test pass rate (648/648 unit, 675/675 total)?
2. Do all models import without errors?
3. Have I updated the project plan document?
4. Are all 4 model files updated correctly?

---

**Ready to Begin!** 🚀

### Task 1 Checklist:
1. ✅ Capture baseline (648/648 unit, 675/675 total)
2. 🔍 **Open supplier_item_price.py and check sip_no_overlap**
3. 🔍 **Add COALESCE logic if missing**
4. ✅ Test import after change
5. 🔍 **Open pricebook_item_version.py and check piv_no_overlap**
6. 🔍 **Add tenant_id parameter if missing**
7. ✅ Test import after change
8. 🔍 **Open webhook_delivery_attempt.py and check indexes**
9. 🔍 **Add idx_webhook_delivery_pending if missing**
10. ✅ Test import after change
11. 🔍 **Open webhook_event.py and check indexes**
12. 🔍 **Add both compound indexes if missing**
13. ✅ Test import after change
14. ✅ Verify Python syntax (`python -c "from app.models import *"`)
15. 🔄 Run regression tests (648/648 unit, 675/675 total expected)
16. 📚 Update project plan

Remember: Task 1 is about **verifying and updating model definitions only**. No database changes, no migrations, no new tests. Just ensure the Python models correctly define the constraints and indexes that will be created in Task 2. Validate imports after each change!
