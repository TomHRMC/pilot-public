# Task 2: Alembic Migration Generation with Data Validation

**Reference:** `dev-docs/analysis/phase-5.2-db-schema-sync-8-plan.md` - Task 2
**Authority (Golden Master):**
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - Golden Master JSON
- `dev-docs/analysis/phase-5.2-db-schema-sync-8-analysis.md` - **Exclusion Constraints & Index Gap Analysis** ⭐
- Current Live Database (Phase 5.1 Post-State)
**Type:** Phase 5.2 - Exclusion Constraints & Critical Performance Indexes
**Priority:** CRITICAL
**Change Type:** MIGRATION + DATA VALIDATION

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

**Phase 5.2 Task 1 Status:** ✅ COMPLETE (April 11, 2026)
- ✅ All 4 constraint/index definitions verified in Python models
- ✅ COALESCE logic added to `sip_no_overlap` constraint
- ✅ tenant_id parameter added to `piv_no_overlap` constraint
- ✅ All 3 missing indexes added to model definitions
- ✅ 640/640 unit tests, 667/667 total tests passing (100%)
- ✅ All Python models import successfully

**Current Baseline:** 640/640 unit tests, 667/667 total tests passing (100%)

**Previous Phases:**
- **Phase 4.5-4.9:** ✅ COMPLETE - Full schema synchronization
- **Phase 5.0:** ✅ COMPLETE - Server defaults enforcement
- **Phase 5.1:** ✅ COMPLETE - Missing unique constraints & foreign keys
- **Phase 5.2 Task 1:** ✅ COMPLETE - Model verification

**See:**
- `dev-docs/analysis/phase-5.2-db-schema-sync-8-plan.md` - Task 2 details (lines 507-780)
- `dev-docs/implementation-prompts/task-db-sync-v8-phase-1-task-1-prompt.md` - Previous task

---

## Current Task: Alembic Migration Generation with Data Validation

**Effort:** 0.5 days
**Gap Reference:** Phase 5.2 Analysis - Exclusion Constraints & Performance Indexes
**Change Type:** MIGRATION + DATA VALIDATION
**Dependencies:** Task 1 must be complete

Generate Alembic migration to fix 2 exclusion constraints and create 3 performance indexes, with comprehensive pre-migration temporal overlap validation. This task ensures existing data will not violate the new constraints before applying them.

### What Needs to Be Created

**Migration Operations:**

| Operation | Table | Action | SQL |
|-----------|-------|--------|-----|
| 1 | `supplier_item_price` | Fix exclusion constraint | DROP + CREATE with COALESCE logic |
| 2 | `pricebook_item_version` | Fix exclusion constraint | DROP + CREATE with tenant_id |
| 3 | `webhook_delivery_attempt` | Create index | CREATE INDEX CONCURRENTLY |
| 4 | `webhook_event` | Create index | CREATE INDEX CONCURRENTLY (tenant_time) |
| 5 | `webhook_event` | Create index | CREATE INDEX CONCURRENTLY (entity) |

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

**Record the output of both results:** `640/640 & 667/667 tests passing` (Phase 5.2 Task 2 baseline - starting from Task 1 completion)

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

### 3. MANDATORY: Pre-Migration Temporal Overlap Validation

**CRITICAL:** You MUST run these validation queries BEFORE creating the migration.

**Validation Query 1: supplier_item_price temporal overlaps (NULL-safe)**
```sql
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
```
**Expected: 0 rows (no overlaps)**

**Validation Query 2: pricebook_item_version temporal overlaps (tenant-scoped)**
```sql
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
```
**Expected: 0 rows (no overlaps)**

**If ANY query returns rows > 0:**
- **STOP** - Do not proceed with migration
- **Document** - Save query results showing overlapping periods
- **Report** - Ask for guidance on data cleanup strategy
- **Clean** - Create script to resolve overlaps (adjust periods, delete duplicates, etc.)
- **Re-validate** - Run all queries again to confirm 0 violations

---

### 4. Index Creation Should Use CONCURRENTLY Flag

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

### 5. Compound Indexes Have Column Order Requirements

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

## Requirements

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

**Step 3: Generate Migration (Manual Construction Recommended)**

**Why Manual?** Alembic autogenerate is unreliable for exclusion constraint modifications and DESC index ordering. Manually construct the migration for precision.

```bash
cd backend
source .venv/bin/activate
alembic revision -m "phase_5_2_fix_exclusion_constraints_and_add_indexes"
```

---

**Step 4: Complete Migration File**

**Location:** `backend/migrations/versions/YYYY_MM_DD_HHMM_<hash>_phase_5_2_fix_exclusion_constraints_and_add_indexes.py`

**Complete Migration Template:**

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

## 🎯 AFTER YOU COMPLETE - Verify No Regressions

**CRITICAL:** After all work is complete, verify the baseline.

### Step 1: Run Full Test Suite

```bash
cd backend
source .venv/bin/activate

# Run unit tests (no integration)
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Expected: 640 passed (no new tests in this task)

# Run all tests
pytest tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Expected: 667 passed (no new tests in this task)
```

### Step 2: Verify Database State

Run constraint and index verification queries via MCP server:

```sql
-- Verify exclusion constraints have correct definitions
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

-- Verify all 3 indexes exist
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

Find the appropriate section and update with:

```markdown
### Phase 1: Exclusion Constraint Fixes - Task 2 (Migration & Data Validation)

**Status:** ✅ COMPLETE (YYYY-MM-DD)
**Effort:** 0.5 days (actual)
**Priority:** CRITICAL

**Implementation Summary:**

- Data Validation: Both temporal overlap validation queries returned 0 violations
- Extension Check: btree_gist extension verified installed
- Migration: [`YYYY_MM_DD_HHMM_<hash>_phase_5_2_fix_exclusion_constraints_and_add_indexes.py`]
- Final Results: 640/640 unit tests (100%), 667/667 total tests (100%)

**Key Changes:**
- ✅ supplier_item_price `sip_no_overlap` constraint fixed with COALESCE logic
- ✅ pricebook_item_version `piv_no_overlap` constraint fixed with tenant_id parameter
- ✅ webhook_delivery_attempt `idx_webhook_delivery_pending` index created
- ✅ webhook_event `idx_webhook_event_tenant_time` index created
- ✅ webhook_event `idx_webhook_event_entity` index created
- ✅ Database state fully aligns with Golden Master JSON
- ✅ Zero regressions in existing test suite
- ✅ Migration rollback tested successfully

**Verification:**
- All constraint definitions verified via pg_get_constraintdef() query
- All indexes verified via pg_indexes query
- No temporal overlaps found in existing data
- Migration forward and backward operations successful
```

---

## Success Criteria

**MUST COMPLETE ALL BEFORE MARKING TASK AS DONE:**

### For Task 2 (Migration & Data Validation):
- [ ] **Regression baseline captured** (640/640 unit, 667/667 total)
- [ ] **Both temporal overlap validation queries run via MCP server**
- [ ] **Both validation queries returned 0 rows (no violations)**
- [ ] **btree_gist extension verified installed**
- [ ] **Migration file created manually**
- [ ] **Migration has all 5 operations** (2 constraint fixes + 3 indexes)
- [ ] **Migration includes CONCURRENTLY flag** for index creation
- [ ] **Migration includes proper downgrade** logic
- [ ] **Migration applied successfully** (`alembic upgrade head`)
- [ ] **Constraint verification query confirms COALESCE logic**
- [ ] **Constraint verification query confirms tenant_id parameter**
- [ ] **Index verification query confirms all 3 indexes exist**
- [ ] **Migration rollback tested** (`alembic downgrade -1`)
- [ ] **Migration re-applied successfully** (`alembic upgrade head`)
- [ ] **ALL 640 existing unit tests still passing**
- [ ] **ALL 667 total tests still passing**
- [ ] **Project plan document updated**

---

## Key Files to Review

### Architecture & Design
- `dev-docs/analysis/phase-5.2-db-schema-sync-8-plan.md` - **Master Plan** ⭐
- `dev-docs/analysis/phase-5.2-db-schema-sync-8-analysis.md` - **Constraint/Index Gap Analysis** ⭐⭐⭐
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - Golden Master JSON

### Migration Files
- `backend/migrations/versions/YYYY_MM_DD_HHMM_<hash>_phase_5_2_fix_exclusion_constraints_and_add_indexes.py` - New migration

---

## Risk Assessment

**For Task 2 (Migration & Data Validation):**
- **Data Violation Risk:** LOW (temporal overlaps unlikely in test data, validation queries confirm)
- **Constraint Recreation Risk:** MEDIUM (DROP/CREATE window during migration)
- **Index Creation Risk:** LOW (CONCURRENTLY flag prevents locks)
- **Application Impact:** LOW (fixes improve data integrity without breaking changes)
- **Migration Failure Risk:** LOW (additive changes, constraint replacements)
- **Rollback Complexity:** LOW (simple constraint/index drop/recreate)
- **Performance Impact:** POSITIVE (indexes improve query performance significantly)
- **Mitigation:** Comprehensive temporal overlap validation, migration testing, verification queries

---

## Notes

### Important Patterns to Follow
- **Temporal Overlap Validation:** ALWAYS run overlap detection queries before migration
- **Zero Violations:** If any temporal overlaps found, STOP and resolve them first
- **COALESCE for NULL:** Use sentinel UUID for NULL-safe exclusion constraints
- **btree_gist Extension:** Verify installed before creating exclusion constraints
- **CONCURRENTLY Flag:** Always use for index creation to avoid table locks
- **Manual Migration:** Construct migration manually for precision
- **Test Rollback:** Always test backward migration before proceeding
- **Zero Regression:** All 640 unit + 667 total tests MUST pass

### Task 2 Specific
- **Exclusion constraints:** Cannot be modified, must drop and recreate
- **Temporal validation:** MANDATORY before constraint creation
- **CONCURRENTLY:** Cannot run inside transaction block
- **Verification queries:** Confirm constraints and indexes after migration
- **Rollback testing:** Ensure migration can be safely reverted

### If You Get Stuck
- Use `postgres-local` MCP server to check database state
- Review Phase 5.2 analysis for constraint/index details
- Check if temporal overlap validation found violations
- Verify btree_gist extension is installed
- Search for migration examples in existing migration files
- Ask for help if spending >30 minutes on single issue

---

## Example Task Flow

### For Task 2 (Migration):

```bash
# 1. Baseline
cd backend
source .venv/bin/activate
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Record: 640 passed

# 2. Pre-Migration Validation (CRITICAL)
# Use postgres-local MCP server to run both overlap detection queries
# STOP if any return rows > 0

# 3. Verify btree_gist extension
# Use postgres-local MCP server:
# SELECT * FROM pg_extension WHERE extname = 'btree_gist';

# 4. Create migration manually
alembic revision -m "phase_5_2_fix_exclusion_constraints_and_add_indexes"

# 5. Open migration file and add all 5 operations:
# Location: backend/migrations/versions/YYYY_MM_DD_HHMM_<hash>_phase_5_2_...py
# - DROP/CREATE sip_no_overlap with COALESCE
# - DROP/CREATE piv_no_overlap with tenant_id
# - CREATE INDEX idx_webhook_delivery_pending
# - CREATE INDEX idx_webhook_event_tenant_time
# - CREATE INDEX idx_webhook_event_entity

# 6. Apply migration
alembic upgrade head

# 7. Verify (via MCP server)
# Check constraints and indexes using verification queries

# 8. Test rollback
alembic downgrade -1
alembic upgrade head

# 9. Final test suite
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Expected: 640 passed
```

---

## Questions to Ask

**Before starting:**
1. Have I captured the 640/640 unit and 667/667 total baselines?
2. Do I have the Phase 5.2 analysis document open for reference?
3. Do I understand that temporal overlap validation is MANDATORY?
4. Am I prepared to stop if validation queries find violations?
5. Is btree_gist extension installed?

**During Task 2 (Migration):**
1. Did I run both temporal overlap validation queries?
2. Did any queries return violations?
3. Is btree_gist extension installed?
4. Did I use DROP/CREATE for exclusion constraints (not ALTER)?
5. Did I use CONCURRENTLY flag for index creation?
6. Does the migration have all 5 operations?
7. Does the migration have proper downgrade logic?
8. Does the migration run forward and backward successfully?

**After implementation:**
1. Do I have 100% test pass rate (640/640 unit, 667/667 total)?
2. Do constraint definitions show COALESCE and tenant_id?
3. Do all 3 indexes exist in pg_indexes?
4. Have I tested migration rollback?
5. Have I updated the project plan document?
6. Did I verify no temporal overlaps in existing data?
7. Are all constraint/index verification queries passing?

---

**Ready to Begin!** 🚀

### Task 2 Checklist:
1. ✅ Capture baseline (640/640 unit, 667/667 total)
2. ⚠️ **CRITICAL: Run temporal overlap validation query 1 via MCP server**
3. ⚠️ **CRITICAL: Run temporal overlap validation query 2 via MCP server**
4. ⚠️ **MANDATORY: Verify both queries returned 0 rows**
5. ⚠️ **CRITICAL: If ANY violations, STOP and report**
6. ⚠️ **CRITICAL: Verify btree_gist extension installed**
7. 🔧 **Create Alembic migration file**
8. 🔍 **Add supplier_item_price constraint fix (DROP + CREATE with COALESCE)**
9. 🔍 **Add pricebook_item_version constraint fix (DROP + CREATE with tenant_id)**
10. 🔍 **Add idx_webhook_delivery_pending index (CREATE CONCURRENTLY)**
11. 🔍 **Add idx_webhook_event_tenant_time index (CREATE CONCURRENTLY)**
12. 🔍 **Add idx_webhook_event_entity index (CREATE CONCURRENTLY)**
13. 🔍 **Add proper downgrade logic for all 5 operations**
14. ✅ Apply migration (`alembic upgrade head`)
15. 🔍 **Verify constraints via MCP server query**
16. 🔍 **Verify indexes via MCP server query**
17. ↩️ Test rollback (`alembic downgrade -1`)
18. ✅ Re-apply migration (`alembic upgrade head`)
19. 🔄 Run regression tests (640/640 unit, 667/667 total expected)
20. 📚 Update project plan

Remember: Task 2 is about **data validation and migration creation**. Validate overlaps FIRST, verify btree_gist extension, create migration with all 5 operations, test forward and backward, and verify database state. STOP if any temporal overlaps are found!
