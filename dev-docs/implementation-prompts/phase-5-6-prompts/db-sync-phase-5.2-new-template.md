# Task [TASK_NUMBER]: [TASK_NAME]

**Reference:** `dev-docs/analysis/phase-5.2-db-schema-sync-8-plan.md` - Task [TASK_NUMBER]
**Authority (Golden Master):**
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - Golden Master JSON
- `dev-docs/analysis/phase-5.2-db-schema-sync-8-analysis.md` - **Exclusion Constraints & Index Gap Analysis** ⭐
- Current Live Database (Phase 5.1 Post-State)
**Type:** Phase 5.2 - Exclusion Constraints & Critical Performance Indexes
**Priority:** CRITICAL
**Change Type:** CONSTRAINT FIX + INDEX CREATION + TESTING

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

## Current Task: [TASK_NAME]

**Effort:** [EFFORT_ESTIMATE]
**Gap Reference:** Phase 5.2 Analysis - Exclusion Constraints & Performance Indexes
**Change Type:** [MODEL VERIFICATION | MIGRATION + DATA VALIDATION | CONSTRAINT/INDEX TESTING]

[TASK_DESCRIPTION - 2-3 sentences explaining what this task accomplishes and WHY it matters]

### What Needs to Be Fixed

[TASK_SPECIFIC_TABLE - Customize per task]

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

### Task 2: Alembic Migration Generation with Data Validation

**Effort:** 0.5 days
**Dependencies:** Task 1 must be complete
**CRITICAL:** Temporal overlap validation is mandatory before applying exclusion constraints

#### What This Task Accomplishes

Generate Alembic migration to fix 2 exclusion constraints and create 3 performance indexes, with comprehensive pre-migration temporal overlap validation.

#### Step-by-Step Implementation

**Step 1: Pre-Migration Data Validation (MANDATORY)**

Run these queries via postgres-local MCP server **BEFORE** generating migration:

```sql
-- Validation 1: supplier_item_price temporal overlaps (NULL-safe)
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
  AND sip1.valid_period && sip2.valid_period
  AND sip1.id < sip2.id;
-- Expected: 0 rows (no overlaps)

-- Validation 2: pricebook_item_version temporal overlaps (tenant-scoped)
SELECT 
    piv1.id AS id1, 
    piv2.id AS id2,
    piv1.tenant_id,
    piv1.pricebook_item_id,
    piv1.valid_period,
    piv2.valid_period
FROM pricebook_item_version piv1
JOIN pricebook_item_version piv2 
  ON piv1.tenant_id = piv2.tenant_id
  AND piv1.pricebook_item_id = piv2.pricebook_item_id
  AND piv1.valid_period && piv2.valid_period
  AND piv1.id < piv2.id;
-- Expected: 0 rows (no overlaps)
```

**If ANY query returns rows > 0:**
- **STOP** - Do not proceed with migration
- **Document** - Save query results showing overlapping periods
- **Report** - Ask for guidance on data cleanup strategy
- **Clean** - Create script to resolve overlaps (adjust periods, delete duplicates, etc.)
- **Re-validate** - Run all queries again to confirm 0 violations

---

**Step 2: Verify btree_gist Extension**

```sql
-- Check if btree_gist extension is installed
SELECT * FROM pg_extension WHERE extname = 'btree_gist';
-- If no rows returned, install it:
-- CREATE EXTENSION IF NOT EXISTS btree_gist;
```

---

**Step 3: Generate Migration**

```bash
cd backend
source .venv/bin/activate
alembic revision --autogenerate -m "phase_5_2_fix_exclusion_constraints_and_add_indexes"
```

---

**Step 4: Manual Migration Construction (Recommended)**

**Why Manual?** Alembic autogenerate is unreliable for exclusion constraint modifications and DESC index ordering. Manually construct the migration for precision.

**Complete Migration File Template:**

```python
"""phase_5_2_fix_exclusion_constraints_and_add_indexes

Revision ID: <hash>
Revises: <previous_hash>
Create Date: 2026-04-11

Description:
Fixes 2 flawed exclusion constraints and adds 3 critical performance indexes
to align physical database with Golden Master JSON schema.

Reference:
- Analysis: dev-docs/analysis/phase-5.2-db-schema-sync-8-analysis.md
- Plan: dev-docs/analysis/phase-5.2-db-schema-sync-8-plan.md
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '<hash>'
down_revision = '<previous_hash>'
branch_labels = None
depends_on = None


def upgrade():
    # =====================================================
    # PHASE 1: FIX EXCLUSION CONSTRAINTS
    # =====================================================
    
    # 1. Fix supplier_item_price.sip_no_overlap (add COALESCE logic)
    op.execute("""
        ALTER TABLE supplier_item_price 
        DROP CONSTRAINT sip_no_overlap;
    """)
    
    op.execute("""
        ALTER TABLE supplier_item_price 
        ADD CONSTRAINT sip_no_overlap 
        EXCLUDE USING gist (
            supplier_item_id WITH =, 
            COALESCE(tenant_id, '00000000-0000-0000-0000-000000000000'::uuid) WITH =, 
            valid_period WITH &&
        );
    """)
    
    # 2. Fix pricebook_item_version.piv_no_overlap (add tenant_id parameter)
    op.execute("""
        ALTER TABLE pricebook_item_version 
        DROP CONSTRAINT piv_no_overlap;
    """)
    
    op.execute("""
        ALTER TABLE pricebook_item_version 
        ADD CONSTRAINT piv_no_overlap 
        EXCLUDE USING gist (
            tenant_id WITH =, 
            pricebook_item_id WITH =, 
            valid_period WITH &&
        );
    """)
    
    # =====================================================
    # PHASE 2: CREATE PERFORMANCE INDEXES
    # =====================================================
    
    # 3. Create webhook_delivery_attempt worker queue index
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_webhook_delivery_pending 
        ON webhook_delivery_attempt (status, next_attempt_after);
    """)
    
    # 4. Create webhook_event tenant dashboard query index
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_webhook_event_tenant_time 
        ON webhook_event (tenant_id, created_at DESC);
    """)
    
    # 5. Create webhook_event entity lookup query index
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_webhook_event_entity 
        ON webhook_event (entity_type_code, entity_id, created_at DESC);
    """)


def downgrade():
    # Drop indexes first
    op.execute("""
        DROP INDEX IF EXISTS idx_webhook_event_entity;
    """)
    
    op.execute("""
        DROP INDEX IF EXISTS idx_webhook_event_tenant_time;
    """)
    
    op.execute("""
        DROP INDEX IF EXISTS idx_webhook_delivery_pending;
    """)
    
    # Revert exclusion constraints to original (flawed) definitions
    
    # Revert pricebook_item_version
    op.execute("""
        ALTER TABLE pricebook_item_version 
        DROP CONSTRAINT piv_no_overlap;
    """)
    
    op.execute("""
        ALTER TABLE pricebook_item_version 
        ADD CONSTRAINT piv_no_overlap 
        EXCLUDE USING gist (
            pricebook_item_id WITH =, 
            valid_period WITH &&
        );
    """)
    
    # Revert supplier_item_price
    op.execute("""
        ALTER TABLE supplier_item_price 
        DROP CONSTRAINT sip_no_overlap;
    """)
    
    op.execute("""
        ALTER TABLE supplier_item_price 
        ADD CONSTRAINT sip_no_overlap 
        EXCLUDE USING gist (
            supplier_item_id WITH =, 
            tenant_id WITH =, 
            valid_period WITH &&
        );
    """)
```

---

**Step 5: Migration Testing**

```bash
# Test forward migration
alembic upgrade head

# Verify constraints recreated (via MCP server)
SELECT conname, pg_get_constraintdef(c.oid) 
FROM pg_constraint c
JOIN pg_class t ON c.conrelid = t.oid
WHERE t.relname IN ('supplier_item_price', 'pricebook_item_version') 
  AND c.contype = 'x'
ORDER BY t.relname, conname;
-- Expected: sip_no_overlap with COALESCE, piv_no_overlap with tenant_id

# Verify indexes created (via MCP server)
SELECT indexname, indexdef 
FROM pg_indexes 
WHERE tablename IN ('webhook_delivery_attempt', 'webhook_event')
  AND indexname IN (
      'idx_webhook_delivery_pending',
      'idx_webhook_event_tenant_time',
      'idx_webhook_event_entity'
  )
ORDER BY tablename, indexname;
-- Expected: 3 rows

# Test constraint enforcement (spot check)
-- Try to insert overlapping temporal period (should fail with IntegrityError)

# Test backward migration
alembic downgrade -1

# Verify constraints/indexes removed
-- Run verification queries again (should show old constraint definitions, indexes dropped)

# Re-apply for continued work
alembic upgrade head
```

**Success Criteria for Task 2:**
- [ ] Both temporal overlap validation queries return 0 rows
- [ ] btree_gist extension verified/installed
- [ ] Migration file created with all 5 operations (2 constraint fixes + 3 indexes)
- [ ] Migration runs successfully forward
- [ ] Database verification confirms constraints have correct definitions
- [ ] Database verification confirms all 3 indexes exist
- [ ] Migration runs successfully backward
- [ ] Migration re-applies successfully

---

### Task 3: Comprehensive Constraint & Index Testing

**Effort:** 0.5 days
**Dependencies:** Tasks 1 & 2 must be complete

#### What This Task Accomplishes

Validate that:
1. Exclusion constraints prevent temporal overlaps
2. COALESCE logic correctly handles NULL tenant_id
3. Performance indexes are used by expected queries
4. No performance regressions in webhook operations

#### Test File Structure

**File:** `backend/tests/test_phase_5_2_exclusion_and_indexes.py`

**Test Pattern:**

```python
"""
Test Suite: Phase 5.2 - Exclusion Constraints & Index Verification
Validates temporal overlap prevention and query performance optimization

Reference: phase-5.2-db-schema-sync-8-plan.md
"""
import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
import uuid
from datetime import datetime, timedelta


class TestExclusionConstraintsEnforced:
    """Verify exclusion constraints prevent temporal overlaps"""
    
    def test_supplier_item_price_null_tenant_overlap_prevented(self, db_session):
        """Verify COALESCE logic prevents overlaps when tenant_id is NULL"""
        item_id = uuid.uuid4()
        
        # Create supplier_item
        db_session.execute(text("""
            INSERT INTO supplier_item (id, tenant_id, supplier_id, sku, unit_cost_cents)
            VALUES (:id, NULL, :supplier_id, 'ITEM-001', 1000)
        """), {"id": item_id, "supplier_id": uuid.uuid4()})
        
        # Insert first price with NULL tenant_id
        db_session.execute(text("""
            INSERT INTO supplier_item_price 
            (supplier_item_id, tenant_id, valid_period, price_cents)
            VALUES (:item_id, NULL, '[2024-01-01, 2024-12-31)'::tstzrange, 10000)
        """), {"item_id": item_id})
        
        # Attempt overlapping period with NULL tenant_id (should fail)
        with pytest.raises(IntegrityError) as exc_info:
            db_session.execute(text("""
                INSERT INTO supplier_item_price 
                (supplier_item_id, tenant_id, valid_period, price_cents)
                VALUES (:item_id, NULL, '[2024-06-01, 2025-06-01)'::tstzrange, 12000)
            """), {"item_id": item_id})
        
        assert "sip_no_overlap" in str(exc_info.value).lower()
        db_session.rollback()
    
    def test_supplier_item_price_adjacent_periods_allowed(self, db_session):
        """Verify adjacent periods (no overlap) are allowed"""
        item_id = uuid.uuid4()
        
        # Create supplier_item
        db_session.execute(text("""
            INSERT INTO supplier_item (id, tenant_id, supplier_id, sku, unit_cost_cents)
            VALUES (:id, NULL, :supplier_id, 'ITEM-002', 1000)
        """), {"id": item_id, "supplier_id": uuid.uuid4()})
        
        # Insert first period
        db_session.execute(text("""
            INSERT INTO supplier_item_price 
            (supplier_item_id, tenant_id, valid_period, price_cents)
            VALUES (:item_id, NULL, '[2024-01-01, 2024-06-01)'::tstzrange, 10000)
        """), {"item_id": item_id})
        
        # Insert adjacent period (should succeed - no overlap due to exclusive upper bound)
        db_session.execute(text("""
            INSERT INTO supplier_item_price 
            (supplier_item_id, tenant_id, valid_period, price_cents)
            VALUES (:item_id, NULL, '[2024-06-01, 2024-12-31)'::tstzrange, 12000)
        """), {"item_id": item_id})
        
        db_session.commit()  # Should succeed
    
    def test_pricebook_item_version_tenant_scoped_overlap_prevented(self, db_session, test_tenant):
        """Verify tenant-scoped temporal overlap prevention"""
        item_id = uuid.uuid4()
        
        # Create pricebook_item
        db_session.execute(text("""
            INSERT INTO pricebook_item (id, tenant_id, item_code, description)
            VALUES (:id, :tenant_id, 'PB-001', 'Test Item')
        """), {"id": item_id, "tenant_id": test_tenant.id})
        
        # Insert first version
        db_session.execute(text("""
            INSERT INTO pricebook_item_version 
            (tenant_id, pricebook_item_id, valid_period, price_cents)
            VALUES (:tenant_id, :item_id, '[2024-01-01, 2024-12-31)'::tstzrange, 15000)
        """), {"tenant_id": test_tenant.id, "item_id": item_id})
        
        # Attempt overlapping version for same tenant (should fail)
        with pytest.raises(IntegrityError) as exc_info:
            db_session.execute(text("""
                INSERT INTO pricebook_item_version 
                (tenant_id, pricebook_item_id, valid_period, price_cents)
                VALUES (:tenant_id, :item_id, '[2024-06-01, 2025-06-01)'::tstzrange, 18000)
            """), {"tenant_id": test_tenant.id, "item_id": item_id})
        
        assert "piv_no_overlap" in str(exc_info.value).lower()
        db_session.rollback()


class TestPerformanceIndexes:
    """Verify performance indexes improve query performance"""
    
    def test_webhook_delivery_pending_index_used(self, db_session):
        """Verify worker queue query uses idx_webhook_delivery_pending"""
        
        # Use EXPLAIN to verify index usage
        result = db_session.execute(text("""
            EXPLAIN (FORMAT JSON)
            SELECT * FROM webhook_delivery_attempt
            WHERE status = 'pending' 
              AND next_attempt_after <= NOW()
            ORDER BY next_attempt_after ASC
            LIMIT 100
        """))
        
        explain_output = result.scalar()
        
        # Verify index scan is used (not sequential scan)
        assert "idx_webhook_delivery_pending" in str(explain_output)
        assert "Index Scan" in str(explain_output) or "Bitmap Index Scan" in str(explain_output)
    
    def test_webhook_event_tenant_time_index_used(self, db_session, test_tenant):
        """Verify tenant dashboard query uses idx_webhook_event_tenant_time"""
        
        result = db_session.execute(text("""
            EXPLAIN (FORMAT JSON)
            SELECT * FROM webhook_event
            WHERE tenant_id = :tenant_id
            ORDER BY created_at DESC
            LIMIT 50
        """), {"tenant_id": test_tenant.id})
        
        explain_output = result.scalar()
        
        # Verify index scan is used
        assert "idx_webhook_event_tenant_time" in str(explain_output)
        assert "Index Scan" in str(explain_output) or "Bitmap Index Scan" in str(explain_output)
    
    def test_webhook_event_entity_index_used(self, db_session):
        """Verify entity lookup query uses idx_webhook_event_entity"""
        
        result = db_session.execute(text("""
            EXPLAIN (FORMAT JSON)
            SELECT * FROM webhook_event
            WHERE entity_type_code = 'customer'
              AND entity_id = :entity_id
            ORDER BY created_at DESC
            LIMIT 20
        """), {"entity_id": uuid.uuid4()})
        
        explain_output = result.scalar()
        
        # Verify index scan is used
        assert "idx_webhook_event_entity" in str(explain_output)
        assert "Index Scan" in str(explain_output) or "Bitmap Index Scan" in str(explain_output)
```

**SQL Verification Queries:**
```sql
-- Query 1: Verify exclusion constraints have correct definitions
SELECT 
    t.relname AS table_name,
    c.conname AS constraint_name,
    pg_get_constraintdef(c.oid) AS constraint_definition
FROM pg_constraint c
JOIN pg_class t ON c.conrelid = t.oid
WHERE t.relname IN ('supplier_item_price', 'pricebook_item_version')
  AND c.contype = 'x'
ORDER BY t.relname, c.conname;
-- Expected: sip_no_overlap with COALESCE, piv_no_overlap starting with tenant_id

-- Query 2: Verify all 3 indexes exist
SELECT 
    tablename, 
    indexname, 
    indexdef
FROM pg_indexes
WHERE tablename IN ('webhook_delivery_attempt', 'webhook_event')
  AND indexname IN (
      'idx_webhook_delivery_pending',
      'idx_webhook_event_tenant_time',
      'idx_webhook_event_entity'
  )
ORDER BY tablename, indexname;
-- Expected: 3 rows
```

**Success Criteria for Task 3:**
- [ ] Test file created with exclusion constraint and index tests
- [ ] Tests validate NULL-safe temporal overlap prevention (COALESCE logic)
- [ ] Tests validate tenant-scoped temporal overlap prevention
- [ ] Tests validate adjacent periods are allowed (no false positives)
- [ ] EXPLAIN tests confirm all 3 indexes are used by expected queries
- [ ] Full test suite passes: 652+/652+ unit tests, 679+/679+ total (100%)
- [ ] SQL verification confirms constraints and indexes are correct

---

## 🎯 AFTER YOU COMPLETE - Verify No Regressions

**CRITICAL:** After all work is complete, verify the baseline.

### Step 1: Run Full Test Suite

```bash
cd backend
source .venv/bin/activate

# Run unit tests (no integration)
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Expected: 652+ passed (648 baseline + ~4 new tests)

# Run all tests
pytest tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Expected: 679+ passed (675 baseline + ~4 new tests)
```

### Step 2: Verify Database State

```bash
# Run constraint and index verification queries via MCP server
# All constraints should have correct definitions
# All 3 indexes should exist
```

### Step 3: Final Validation

**If ANY tests fail:**
1. Identify failing tests
2. Check if COALESCE syntax is correct in constraint definition
3. Check if tenant_id is first parameter in piv_no_overlap
4. Verify all 3 indexes created successfully
5. Fix and re-run until 100% pass rate

---

## Documentation Update

**File to Update:** `dev-docs/analysis/phase-5.2-db-schema-sync-8-plan.md`

Find Task [TASK_NUMBER] and update with:

```markdown
### Task [TASK_NUMBER]: [TASK_NAME]

**Status:** ✅ COMPLETE (YYYY-MM-DD)
**Effort:** [ACTUAL_DAYS] days (actual)
**Priority:** CRITICAL

**Implementation Summary:**

- Model Verification: Verified 2 exclusion constraints + 3 indexes in Python models
- Data Validation: Both temporal overlap validation queries returned 0 violations
- Extension Check: btree_gist extension verified installed
- Migration: [`YYYY_MM_DD_HHMM-[hash]_phase_5_2_fix_exclusion_constraints_and_add_indexes.py`]
- Test Suite: [`test_phase_5_2_exclusion_and_indexes.py`] - 4+ tests ✅
- Final Results: 652/652 unit tests (100%), 679/679 total tests (100%)

**Key Changes:**
- ✅ supplier_item_price `sip_no_overlap` constraint fixed with COALESCE logic
- ✅ pricebook_item_version `piv_no_overlap` constraint fixed with tenant_id parameter
- ✅ webhook_delivery_attempt `idx_webhook_delivery_pending` index created
- ✅ webhook_event `idx_webhook_event_tenant_time` index created
- ✅ webhook_event `idx_webhook_event_entity` index created
- ✅ Database state fully aligns with Golden Master JSON
- ✅ Zero regressions in existing test suite
- ✅ Temporal overlap prevention verified via exclusion constraint tests
- ✅ Query performance verified via EXPLAIN index usage tests

**Verification:**
- All constraint definitions verified via pg_get_constraintdef() query
- All indexes verified via pg_indexes query
- EXPLAIN tests confirm indexes used by worker queue and dashboard queries
- IntegrityError tests confirm temporal overlaps rejected at database layer
- Migration rollback tested successfully
```

---

## Success Criteria

**MUST COMPLETE ALL BEFORE MARKING TASK AS DONE:**

### For ALL Phase 5.2 Tasks:
- [ ] **Regression baseline captured** (648/648 unit, 675/675 total)
- [ ] **Both temporal overlap validation queries returned 0 rows**
- [ ] **btree_gist extension verified installed**
- [ ] **All 4 constraint/index issues verified in Python models**
- [ ] **Alembic migration generated/constructed manually**
- [ ] **Migration applied successfully** (`alembic upgrade head`)
- [ ] **Verification tests written and passing**
- [ ] **ALL 648 existing unit tests still passing**
- [ ] **ALL 675 total tests still passing**
- [ ] **New total: 652/652 unit, 679/679 total (100%)**
- [ ] **pg_get_constraintdef confirms COALESCE logic and tenant_id parameter**
- [ ] **pg_indexes confirms all 3 indexes exist**
- [ ] **EXPLAIN tests confirm indexes are used**
- [ ] **Migration rollback tested** (`alembic downgrade -1`)
- [ ] **Project plan document updated**

### Task-Specific Validation:

**Task 1 (Model Verification):**
- [ ] supplier_item_price `sip_no_overlap` uses COALESCE
- [ ] pricebook_item_version `piv_no_overlap` includes tenant_id
- [ ] webhook_delivery_attempt has `idx_webhook_delivery_pending`
- [ ] webhook_event has both compound DESC indexes
- [ ] Python syntax valid (`python -c "from app.models import *"`)

**Task 2 (Migration):**
- [ ] Both temporal overlap queries passed (0 violations)
- [ ] btree_gist extension verified
- [ ] Migration file created with all 5 operations
- [ ] Migration runs forward successfully
- [ ] Migration runs backward successfully
- [ ] Constraints and indexes verified in database

**Task 3 (Testing):**
- [ ] Exclusion constraint tests validate temporal overlap prevention
- [ ] COALESCE logic tested with NULL tenant_id values
- [ ] Adjacent period tests confirm no false positives
- [ ] EXPLAIN tests confirm index usage
- [ ] Full regression suite passes

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

**For Phase 5.2:**
- **Data Violation Risk:** LOW (temporal overlaps unlikely in existing test data)
- **Constraint Recreation Risk:** MEDIUM (DROP/CREATE window during migration)
- **Index Creation Risk:** LOW (CONCURRENTLY flag prevents locks)
- **Application Impact:** LOW (fixes improve data integrity without breaking changes)
- **Migration Failure Risk:** LOW (additive changes, constraint replacements)
- **Rollback Complexity:** LOW (simple constraint/index drop/recreate)
- **Performance Impact:** POSITIVE (indexes improve query performance significantly)
- **Mitigation:** Comprehensive temporal overlap validation, migration testing, EXPLAIN verification

---

## Notes

### Important Patterns to Follow
- **Temporal Overlap Validation:** ALWAYS run overlap detection queries before migration
- **Zero Violations:** If any temporal overlaps found, STOP and resolve them first
- **COALESCE for NULL:** Use sentinel UUID for NULL-safe exclusion constraints
- **btree_gist Extension:** Verify installed before creating exclusion constraints
- **CONCURRENTLY Flag:** Always use for index creation to avoid table locks
- **EXPLAIN Testing:** Verify indexes are actually used by expected queries
- **Zero Regression:** All 648 unit + 675 total tests MUST pass

### Phase 5.2 Specific
- **Exclusion constraints:** Cannot be modified, must drop and recreate
- **Temporal types:** tstzrange uses `[lower, upper)` notation (exclusive upper bound)
- **Overlap operator:** `&&` returns TRUE if ranges overlap
- **COALESCE logic:** Treats NULL as sentinel UUID for comparison
- **Compound indexes:** Column order matters for query optimization
- **DESC ordering:** Required for descending time-series queries

### If You Get Stuck
- Use `postgres-local` MCP server to check database state
- Review Phase 5.2 analysis for constraint/index details
- Check if temporal overlap validation found violations
- Search for exclusion constraint syntax in existing models
- Verify btree_gist extension is installed
- Use EXPLAIN to check if indexes are being used
- Ask for help if spending >30 minutes on single issue

---

## Example Task Flow

### For Phase 5.2 Task 1 (Model Verification):

```bash
# 1. Baseline
cd backend
source .venv/bin/activate
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Record: 648 passed

# 2. Open model files and check for constraints/indexes
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
# Repeat for pricebook_item_version and webhook models

# 3. Verify syntax
python -c "from app.models import *"
# Should load without errors
```

### For Phase 5.2 Task 2 (Migration):

```bash
# 1. Temporal overlap validation (MANDATORY)
# Use postgres-local MCP server to run both overlap detection queries
# STOP if any return rows > 0

# 2. Verify btree_gist extension
# Use postgres-local MCP server:
# SELECT * FROM pg_extension WHERE extname = 'btree_gist';

# 3. Create migration manually (recommended)
alembic revision -m "phase_5_2_fix_exclusion_constraints_and_add_indexes"

# 4. Open migration file and add all 5 operations:
# Location: backend/migrations/versions/2026_04_11_<hash>_phase_5_2_...py
# - DROP/CREATE sip_no_overlap with COALESCE
# - DROP/CREATE piv_no_overlap with tenant_id
# - CREATE INDEX idx_webhook_delivery_pending
# - CREATE INDEX idx_webhook_event_tenant_time
# - CREATE INDEX idx_webhook_event_entity

# 5. Apply migration
alembic upgrade head

# 6. Verify (via MCP server)
SELECT conname, pg_get_constraintdef(c.oid) 
FROM pg_constraint c
JOIN pg_class t ON c.conrelid = t.oid
WHERE t.relname IN ('supplier_item_price', 'pricebook_item_version') 
  AND c.contype = 'x';
# Expected: COALESCE in sip_no_overlap, tenant_id in piv_no_overlap

# 7. Test rollback
alembic downgrade -1
alembic upgrade head
```

---

## Questions to Ask

**Before starting:**
1. Have I captured the 648/648 unit and 675/675 total baselines?
2. Do I have the Phase 5.2 analysis document open for reference?
3. Do I understand the difference between exclusion constraints and unique constraints?
4. Am I prepared to stop if temporal overlap validation finds violations?
5. Is btree_gist extension installed?

**During Task 1 (Models):**
1. Does sip_no_overlap use COALESCE for NULL-safe comparison?
2. Does piv_no_overlap include tenant_id as the first parameter?
3. Are all 3 performance indexes defined in the models?
4. Is DESC ordering specified for time-series indexes?

**During Task 2 (Migration):**
1. Did I run both temporal overlap validation queries?
2. Did any queries return violations?
3. Is btree_gist extension installed?
4. Did I use DROP/CREATE for exclusion constraints (not ALTER)?
5. Did I use CONCURRENTLY flag for index creation?
6. Does the migration run forward and backward successfully?

**After implementation:**
1. Do I have 100% test pass rate (652/652 unit, 679/679 total)?
2. Do constraint definitions show COALESCE and tenant_id?
3. Do all 3 indexes exist in pg_indexes?
4. Do EXPLAIN tests confirm indexes are used?
5. Do temporal overlap attempts raise IntegrityError as expected?
6. Have I updated the project plan document?
7. Have I tested migration rollback?

---

**Ready to Begin!** 🚀

### Phase 5.2 Task Checklist:
1. ✅ Capture baseline (648/648 unit, 675/675 total)
2. 🔍 **Verify sip_no_overlap uses COALESCE in Python model**
3. 🔍 **Verify piv_no_overlap includes tenant_id in Python model**
4. 🔍 **Verify all 3 performance indexes in Python models**
5. ✅ Verify Python syntax (`python -c "from app.models import *"`)
6. ⚠️ **CRITICAL: Run both temporal overlap validation queries via MCP server**
7. ⚠️ **CRITICAL: Verify btree_gist extension installed**
8. ⚠️ **MANDATORY: Stop if ANY overlap query returns violations**
9. 🔧 **Create/generate Alembic migration**
10. 🔍 **Verify migration has all 5 operations (2 constraint fixes + 3 indexes)**
11. ✅ Apply migration (`alembic upgrade head`)
12. 🧪 **Create exclusion constraint + index tests (IntegrityError + EXPLAIN tests)**
13. 🔄 Run regression tests (652/652 unit, 679/679 total expected)
14. ↩️ Test rollback
15. 📚 Update project plan

Remember: Phase 5.2 is about **temporal data integrity and query performance**. Validate overlaps first, verify COALESCE and tenant_id logic, create indexes with CONCURRENTLY, and test that temporal overlaps are rejected and indexes are used. This is surgical, focused work - validate everything before applying constraints!
