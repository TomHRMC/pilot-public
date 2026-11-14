# Task 2: Alembic Migration Generation & Manual Constraint Addition

**Reference:** `dev-docs/analysis/phase-5.1-db-schema-sync-7-plan.md` - Task 2
**Authority (Golden Master):**
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - Golden Master JSON
- `dev-docs/analysis/phase-5.1-db-schema-sync-7-analysis.md` - **Constraint Gap Analysis** ⭐
- Current Live Database (Phase 5.0 Post-State)
**Type:** Phase 5.1 - Missing Unique Constraints & Foreign Keys
**Priority:** CRITICAL
**Change Type:** MIGRATION + DATA VALIDATION + DATABASE CHANGES

---

## Context

This is **Phase 5.1 - DB Sync v#7**, a focused surgical sync to add missing database constraints. A forensic comparison revealed **10 missing constraints** in the physical database that are correctly defined in the Golden Master JSON.

**Root Cause:** SQLModel/Alembic did not materialize these constraints during model-to-database generation, despite them being present in the JSON schema.

**Critical Impact:**
- **Data Integrity Risk:** Without unique constraints, the application can create duplicate records that violate business logic
- **Audit Trail Gaps:** Missing foreign keys on `tenant.created_by` and `tenant.updated_by` prevent proper referential integrity
- **Schema Drift:** Database constraints don't match the Golden Master specification
- **QuickBooks Integration Risk:** `integration_sync_mapping` unique constraints are critical for preventing duplicate sync mappings

**Scope:** **10 constraints across 8 tables** - Much smaller than Phase 5.0, but requires careful data validation before applying constraints.

**Key Principle:** All existing data MUST be validated for violations (duplicates/orphans) BEFORE applying constraints. If violations exist, clean the data first.

---

## What Was Completed in Previous Phases

**Phase 5.1 Task 1 Status:** ✅ COMPLETE (April 9, 2026)
- ✅ All 8 unique constraints verified in Python SQLModel definitions
- ✅ Both foreign keys verified in Tenant model (created_by, updated_by)
- ✅ All models import successfully without errors
- ✅ 640/640 unit tests passing, 667/667 total tests passing (100%)

**Phase 5.0 Status:** ✅ COMPLETE (April 9, 2026)
- ✅ 200/200 fields with server defaults enforced at PostgreSQL layer (100% coverage)
- ✅ 640/640 unit tests, 667/667 total tests passing (100%)
- ✅ All fields now have database-layer defaults for direct SQL operations

**Current Baseline:** 640/640 unit tests, 667/667 total tests passing (100%)

**Previous Phases:**
- **Phase 4.5-4.9:** ✅ COMPLETE - Full schema synchronization
- **Phase 5.0:** ✅ COMPLETE - Server defaults enforcement
- **Phase 5.1 Task 1:** ✅ COMPLETE - Model constraint verification

**See:**
- `dev-docs/analysis/phase-5.0-db-schema-sync-6-plan.md` for Phase 5.0 history
- `dev-docs/analysis/phase-5.1-db-schema-sync-7-analysis.md` for constraint gap details
- `dev-docs/analysis/phase-5.1-db-schema-sync-7-plan.md` - Task 2 section

---

## Current Task: Alembic Migration Generation & Manual Constraint Addition

**Effort:** 0.5 days
**Gap Reference:** Phase 5.1 Analysis - Missing Unique Constraints & Foreign Keys
**Change Type:** MIGRATION + DATA VALIDATION + DATABASE CONSTRAINT ADDITION

Generate Alembic migration to add all 10 constraints to the physical database, with comprehensive pre-migration data validation to detect and resolve any violations. This task is critical because Alembic's autogenerate may not detect all missing constraints, requiring manual verification and addition.

### What Needs to Be Fixed

**10 Constraints to Add via Migration:**

| Table | Constraint Type | Columns | Constraint Name |
|-------|----------------|---------|-----------------|
| `tenant_domain` | UNIQUE | `(tenant_id, domain)` | `uq_tenant_domain_tenant_id_domain` |
| `tenant_user_invite` | UNIQUE | `(tenant_id, email)` | `uq_tenant_user_invite_tenant_id_email` |
| `quote_version` | UNIQUE | `(quote_id, version_no)` | `uq_quote_version_quote_id_version_no` |
| `subscription_usage` | UNIQUE | `(subscription_id, product_feature_code, period_start, period_end)` | `uq_subscription_usage_subscription_id_feature_period` |
| `supplier_item` | UNIQUE | `(tenant_id, supplier_id, sku)` | `uq_supplier_item_tenant_id_supplier_id_sku` |
| `integration_sync_mapping` | UNIQUE | `(app_service_id, entity_type_code, entity_id)` | `uq_integration_sync_mapping_internal` |
| `integration_sync_mapping` | UNIQUE | `(app_service_id, entity_type_code, external_id)` | `uq_integration_sync_mapping_external` |
| `entity_address` | UNIQUE | `(entity_type_code, entity_id, address_id)` | `uq_entity_address_entity_type_entity_id_address_id` |
| `entity_contact` | UNIQUE | `(entity_type_code, entity_id, contact_id)` | `uq_entity_contact_entity_type_entity_id_contact_id` |
| `tenant.created_by` | FOREIGN KEY | → `user.id` | `fk_tenant_created_by` |
| `tenant.updated_by` | FOREIGN KEY | → `user.id` | `fk_tenant_updated_by` |

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

**Record the output of both results:** `640/640 & 667/667 tests passing` (Phase 5.1 Task 1 completion baseline)

### Step 3: Document Your Baseline

**Write down both of these numbers before proceeding**

**This is your regression checkpoint. ALL these tests MUST still pass after your work.**

---

## ⚠️ CRITICAL: Phase 5.1 Task 2 Specific Warnings

**BEFORE writing ANY code, review these Phase 5.1 Task 2 critical issues:**

### 1. Data Validation is MANDATORY Before Applying Constraints

**Critical Rule:** You CANNOT apply unique constraints or foreign keys if existing data has violations.

**MANDATORY Pre-Migration Validation:**
```sql
-- Check for duplicate records BEFORE adding UNIQUE constraint
SELECT tenant_id, domain, COUNT(*)
FROM tenant_domain
GROUP BY tenant_id, domain
HAVING COUNT(*) > 1;
-- Expected: 0 rows (no duplicates)

-- Check for orphaned references BEFORE adding FOREIGN KEY
SELECT t.id, t.created_by
FROM tenant t
LEFT JOIN "user" u ON t.created_by = u.id
WHERE t.created_by IS NOT NULL
  AND u.id IS NULL;
-- Expected: 0 rows (no orphans)
```

**If ANY violations found:**
1. **STOP** - Do not apply migration
2. **Document** - Record the violation details
3. **Clean** - Create data cleanup script to resolve duplicates/orphans
4. **Re-validate** - Run queries again to confirm 0 violations
5. **Then proceed** with migration

**Common Data Cleanup Approaches:**
- **Duplicates:** Keep the oldest record, delete newer ones (or merge if possible)
- **Orphans:** Either SET NULL or create missing parent records
- **Consult:** If cleanup strategy unclear, ask before proceeding

---

### 2. Alembic May or May Not Detect Missing Constraints

**Reality:** Alembic's autogenerate is somewhat reliable for constraints but not guaranteed.

**Expected Behavior:**
- May detect all 10 constraints ✅
- May detect some (5-7) and miss others ⚠️
- May detect none (unlikely but possible) ❌

**MANDATORY Process:**
```bash
# After alembic revision --autogenerate:
1. Open the generated migration file
2. Count op.create_unique_constraint() calls
   - Expected: 8 (8 unique constraints)
3. Count op.create_foreign_key() calls
   - Expected: 2 (2 foreign keys)
4. If total != 10, add missing operations manually
```

---

### 3. Unique Constraints Prevent Duplicates Forever

**Reality Check:** Once a UNIQUE constraint is applied, PostgreSQL will **permanently reject** any duplicate INSERT/UPDATE attempts.

**Application Impact:**
- Code that assumes duplicates are allowed will start failing with IntegrityError
- Background jobs, imports, and QuickBooks sync MUST handle constraint violations gracefully
- API endpoints should return 409 Conflict for duplicate attempts

**Pre-Migration Code Review:**
```bash
# Search for code that might create duplicates
# Example: integration_sync_mapping insertions
grep -r "IntegrationSyncMapping" backend/app/ --include="*.py"

# Check for duplicate handling logic
grep -r "duplicate" backend/app/ --include="*.py" -i
```

---

### 4. Foreign Keys Enforce Referential Integrity

**What This Means:**
- Cannot insert `tenant.created_by` with a user_id that doesn't exist in `user` table
- Deleting a user will trigger the `ondelete` action (SET NULL, CASCADE, RESTRICT)

**Phase 5.1 Foreign Keys:**
- `tenant.created_by` → `user.id` (ondelete='SET NULL')
- `tenant.updated_by` → `user.id` (ondelete='SET NULL')

**Why SET NULL:** Deleting a user should not cascade delete tenants. The audit trail becomes NULL but the tenant remains.

---

### 5. Constraint Names Must Be Unique and Descriptive

**PostgreSQL Naming Conventions:**
- Unique constraints: `uq_<table>_<col1>_<col2>`
- Foreign keys: `fk_<source_table>_<column>`

**Examples:**
```python
# Good constraint names (descriptive, unique)
'uq_tenant_domain_tenant_id_domain'
'uq_integration_sync_mapping_internal'
'fk_tenant_created_by'

# Bad constraint names (generic, unclear)
'unique_constraint_1'
'fk_constraint'
'tenant_constraint'
```

---

### 6. integration_sync_mapping Has TWO Unique Constraints

**CRITICAL:** This table requires **both** constraints to prevent mapping conflicts:

```python
# Constraint 1: Prevent duplicate internal entity mappings
# UNIQUE (app_service_id, entity_type_code, entity_id)

# Constraint 2: Prevent duplicate external entity mappings
# UNIQUE (app_service_id, entity_type_code, external_id)
```

**Why Two?** A single internal entity can only map to one external ID per service, AND a single external ID can only map to one internal entity per service.

**Common Mistake:** Only adding one of these constraints. Both are required.

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

## Requirements

### Task 2: Alembic Migration Generation with Data Validation

**Effort:** 0.5 days
**Dependencies:** Task 1 must be complete (✅ COMPLETE)
**CRITICAL:** Data validation is mandatory before applying constraints

#### What This Task Accomplishes

Generate Alembic migration to add all 10 constraints to the physical database, with comprehensive pre-migration data validation to detect and resolve any violations.

#### Step-by-Step Implementation

**Step 1: Pre-Migration Data Validation (MANDATORY)**

Run these queries via postgres-local MCP server **BEFORE** generating migration:

```sql
-- Validation 1: tenant_domain duplicates
SELECT tenant_id, domain, COUNT(*)
FROM tenant_domain
GROUP BY tenant_id, domain
HAVING COUNT(*) > 1;
-- Expected: 0 rows

-- Validation 2: tenant_user_invite duplicates
SELECT tenant_id, email, COUNT(*)
FROM tenant_user_invite
GROUP BY tenant_id, email
HAVING COUNT(*) > 1;
-- Expected: 0 rows

-- Validation 3: quote_version duplicates
SELECT quote_id, version_no, COUNT(*)
FROM quote_version
GROUP BY quote_id, version_no
HAVING COUNT(*) > 1;
-- Expected: 0 rows

-- Validation 4: subscription_usage duplicates
SELECT subscription_id, product_feature_code, period_start, period_end, COUNT(*)
FROM subscription_usage
GROUP BY subscription_id, product_feature_code, period_start, period_end
HAVING COUNT(*) > 1;
-- Expected: 0 rows

-- Validation 5: supplier_item duplicates
SELECT tenant_id, supplier_id, sku, COUNT(*)
FROM supplier_item
GROUP BY tenant_id, supplier_id, sku
HAVING COUNT(*) > 1;
-- Expected: 0 rows

-- Validation 6: integration_sync_mapping duplicates (internal)
SELECT app_service_id, entity_type_code, entity_id, COUNT(*)
FROM integration_sync_mapping
GROUP BY app_service_id, entity_type_code, entity_id
HAVING COUNT(*) > 1;
-- Expected: 0 rows

-- Validation 7: integration_sync_mapping duplicates (external)
SELECT app_service_id, entity_type_code, external_id, COUNT(*)
FROM integration_sync_mapping
GROUP BY app_service_id, entity_type_code, external_id
HAVING COUNT(*) > 1;
-- Expected: 0 rows

-- Validation 8: entity_address duplicates
SELECT entity_type_code, entity_id, address_id, COUNT(*)
FROM entity_address
GROUP BY entity_type_code, entity_id, address_id
HAVING COUNT(*) > 1;
-- Expected: 0 rows

-- Validation 9: entity_contact duplicates
SELECT entity_type_code, entity_id, contact_id, COUNT(*)
FROM entity_contact
GROUP BY entity_type_code, entity_id, contact_id
HAVING COUNT(*) > 1;
-- Expected: 0 rows

-- Validation 10: tenant.created_by orphans
SELECT t.id, t.created_by
FROM tenant t
LEFT JOIN "user" u ON t.created_by = u.id
WHERE t.created_by IS NOT NULL
  AND u.id IS NULL;
-- Expected: 0 rows

-- Validation 11: tenant.updated_by orphans
SELECT t.id, t.updated_by
FROM tenant t
LEFT JOIN "user" u ON t.updated_by = u.id
WHERE t.updated_by IS NOT NULL
  AND u.id IS NULL;
-- Expected: 0 rows
```

**If ANY query returns rows > 0:**
- **STOP** - Do not proceed with migration
- **Document** - Save query results
- **Report** - Ask for guidance on cleanup strategy
- **Clean** - Create and run data cleanup script
- **Re-validate** - Run all queries again to confirm 0 violations

---

**Step 2: Generate Migration**

```bash
cd backend
source .venv/bin/activate
alembic revision --autogenerate -m "phase_5_1_add_missing_unique_constraints_and_foreign_keys"
```

---

**Step 3: Verify Migration Contents**

```bash
# Open generated migration file
# Expected operations: 8 unique constraints + 2 foreign keys = 10 total

# Count unique constraint operations
grep -c "op.create_unique_constraint" backend/migrations/versions/<file>
# Expected: 8

# Count foreign key operations
grep -c "op.create_foreign_key" backend/migrations/versions/<file>
# Expected: 2

# If totals don't match, add missing operations manually
```

---

**Step 4: Migration Operation Syntax**

**Unique Constraint Syntax:**
```python
# In upgrade()
op.create_unique_constraint(
    'uq_tenant_domain_tenant_id_domain',  # Constraint name
    'tenant_domain',                       # Table name
    ['tenant_id', 'domain']                # Column list
)

# In downgrade()
op.drop_constraint('uq_tenant_domain_tenant_id_domain', 'tenant_domain', type_='unique')
```

**Foreign Key Syntax:**
```python
# In upgrade()
op.create_foreign_key(
    'fk_tenant_created_by',           # Constraint name
    'tenant',                          # Source table
    'user',                            # Target table
    ['created_by'],                    # Source columns
    ['id'],                            # Target columns
    ondelete='SET NULL'                # What to do on delete
)

# In downgrade()
op.drop_constraint('fk_tenant_created_by', 'tenant', type_='foreignkey')
```

---

**Step 5: Complete Migration File Template**

```python
"""phase_5_1_add_missing_unique_constraints_and_foreign_keys

Revision ID: <hash>
Revises: <previous_hash>
Create Date: 2026-04-09

Description:
Adds 8 missing multi-column unique constraints and 2 missing foreign keys
to align physical database with Golden Master JSON schema.

Reference:
- Analysis: dev-docs/analysis/phase-5.1-db-schema-sync-7-analysis.md
- Plan: dev-docs/analysis/phase-5.1-db-schema-sync-7-plan.md
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
    # UNIQUE CONSTRAINTS (8 Total)
    # =====================================================
    
    # 1. tenant_domain
    op.create_unique_constraint(
        'uq_tenant_domain_tenant_id_domain',
        'tenant_domain',
        ['tenant_id', 'domain']
    )
    
    # 2. tenant_user_invite
    op.create_unique_constraint(
        'uq_tenant_user_invite_tenant_id_email',
        'tenant_user_invite',
        ['tenant_id', 'email']
    )
    
    # 3. quote_version
    op.create_unique_constraint(
        'uq_quote_version_quote_id_version_no',
        'quote_version',
        ['quote_id', 'version_no']
    )
    
    # 4. subscription_usage
    op.create_unique_constraint(
        'uq_subscription_usage_subscription_id_feature_period',
        'subscription_usage',
        ['subscription_id', 'product_feature_code', 'period_start', 'period_end']
    )
    
    # 5. supplier_item
    op.create_unique_constraint(
        'uq_supplier_item_tenant_id_supplier_id_sku',
        'supplier_item',
        ['tenant_id', 'supplier_id', 'sku']
    )
    
    # 6a. integration_sync_mapping (internal)
    op.create_unique_constraint(
        'uq_integration_sync_mapping_internal',
        'integration_sync_mapping',
        ['app_service_id', 'entity_type_code', 'entity_id']
    )
    
    # 6b. integration_sync_mapping (external)
    op.create_unique_constraint(
        'uq_integration_sync_mapping_external',
        'integration_sync_mapping',
        ['app_service_id', 'entity_type_code', 'external_id']
    )
    
    # 7. entity_address
    op.create_unique_constraint(
        'uq_entity_address_entity_type_entity_id_address_id',
        'entity_address',
        ['entity_type_code', 'entity_id', 'address_id']
    )
    
    # 8. entity_contact
    op.create_unique_constraint(
        'uq_entity_contact_entity_type_entity_id_contact_id',
        'entity_contact',
        ['entity_type_code', 'entity_id', 'contact_id']
    )
    
    # =====================================================
    # FOREIGN KEYS (2 Total)
    # =====================================================
    
    # 1. tenant.created_by → user.id
    op.create_foreign_key(
        'fk_tenant_created_by',
        'tenant',
        'user',
        ['created_by'],
        ['id'],
        ondelete='SET NULL'
    )
    
    # 2. tenant.updated_by → user.id
    op.create_foreign_key(
        'fk_tenant_updated_by',
        'tenant',
        'user',
        ['updated_by'],
        ['id'],
        ondelete='SET NULL'
    )


def downgrade():
    # Drop foreign keys first (dependencies)
    op.drop_constraint('fk_tenant_updated_by', 'tenant', type_='foreignkey')
    op.drop_constraint('fk_tenant_created_by', 'tenant', type_='foreignkey')
    
    # Drop unique constraints
    op.drop_constraint('uq_entity_contact_entity_type_entity_id_contact_id', 'entity_contact', type_='unique')
    op.drop_constraint('uq_entity_address_entity_type_entity_id_address_id', 'entity_address', type_='unique')
    op.drop_constraint('uq_integration_sync_mapping_external', 'integration_sync_mapping', type_='unique')
    op.drop_constraint('uq_integration_sync_mapping_internal', 'integration_sync_mapping', type_='unique')
    op.drop_constraint('uq_supplier_item_tenant_id_supplier_id_sku', 'supplier_item', type_='unique')
    op.drop_constraint('uq_subscription_usage_subscription_id_feature_period', 'subscription_usage', type_='unique')
    op.drop_constraint('uq_quote_version_quote_id_version_no', 'quote_version', type_='unique')
    op.drop_constraint('uq_tenant_user_invite_tenant_id_email', 'tenant_user_invite', type_='unique')
    op.drop_constraint('uq_tenant_domain_tenant_id_domain', 'tenant_domain', type_='unique')
```

---

**Step 6: Migration Testing**

```bash
# Test forward migration
alembic upgrade head

# Verify constraints created (via MCP server)
SELECT
    tc.table_name,
    tc.constraint_name,
    tc.constraint_type,
    string_agg(kcu.column_name, ', ' ORDER BY kcu.ordinal_position) AS columns
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu
    ON tc.constraint_name = kcu.constraint_name
WHERE tc.table_schema = 'public'
  AND tc.constraint_type IN ('UNIQUE', 'FOREIGN KEY')
  AND tc.table_name IN (
      'tenant_domain', 'tenant_user_invite', 'quote_version',
      'subscription_usage', 'supplier_item', 'integration_sync_mapping',
      'entity_address', 'entity_contact', 'tenant'
  )
GROUP BY tc.table_name, tc.constraint_name, tc.constraint_type
ORDER BY tc.table_name;
-- Expected: 8 UNIQUE + 2 FOREIGN KEY = 10 rows

# Test constraint enforcement (spot check)
-- Try to insert duplicate (should fail with IntegrityError)

# Test backward migration
alembic downgrade -1

# Verify constraints removed
SELECT COUNT(*) FROM information_schema.table_constraints
WHERE constraint_name IN (
    'uq_tenant_domain_tenant_id_domain',
    'uq_tenant_user_invite_tenant_id_email',
    'uq_quote_version_quote_id_version_no',
    'uq_subscription_usage_subscription_id_feature_period',
    'uq_supplier_item_tenant_id_supplier_id_sku',
    'uq_integration_sync_mapping_internal',
    'uq_integration_sync_mapping_external',
    'uq_entity_address_entity_type_entity_id_address_id',
    'uq_entity_contact_entity_type_entity_id_contact_id',
    'fk_tenant_created_by',
    'fk_tenant_updated_by'
);
-- Expected: 0

# Re-apply for continued work
alembic upgrade head
```

**Success Criteria for Task 2:**
- [ ] All 11 pre-migration validation queries return 0 rows
- [ ] Migration file generated with all 10 constraint operations
- [ ] Migration runs successfully forward
- [ ] Database verification confirms all 10 constraints exist
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
# Expected: 640 passed (no new tests in Task 2)

# Run all tests
pytest tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Expected: 667 passed (no new tests in Task 2)
```

### Step 2: Verify Database State

```bash
# Run constraint verification queries via MCP server
# All 10 constraints should be present and enforced
```

### Step 3: Final Validation

**If ANY tests fail:**
1. Identify failing tests
2. Check if constraint syntax errors in migration
3. Verify all 10 constraints applied successfully
4. Fix and re-run until 100% pass rate

---

## Documentation Update

**File to Update:** `dev-docs/analysis/phase-5.1-db-schema-sync-7-plan.md`

Find Task 2 and update with:

```markdown
### Task 2: Alembic Migration Generation & Manual Constraint Addition

**Status:** ✅ COMPLETE (YYYY-MM-DD)
**Effort:** 0.5 days (actual: [ACTUAL_DAYS] days)
**Priority:** CRITICAL

**Implementation Summary:**

- Data Validation: All 11 validation queries returned 0 violations ✅
- Migration: [`YYYY_MM_DD_HHMM-[hash]_phase_5_1_add_missing_unique_constraints_and_foreign_keys.py`]
- Alembic Autogenerate: Detected [X] of 10 constraints (manually added [Y] missing)
- Forward Migration: Applied successfully ✅
- Backward Migration: Rolled back successfully ✅
- Final Results: 640/640 unit tests (100%), 667/667 total tests (100%)

**Key Changes:**
- ✅ 8 unique constraints added at database layer
- ✅ 2 foreign keys added for tenant audit trail
- ✅ Database state fully aligns with Golden Master JSON
- ✅ Zero regressions in existing test suite
- ✅ All 10 constraints verified via information_schema query

**Verification:**
- All 10 constraints verified via information_schema query
- Migration rollback tested successfully
- Zero data violations found during pre-migration validation
```

---

## Success Criteria

**MUST COMPLETE ALL BEFORE MARKING TASK AS DONE:**

### For Task 2:
- [ ] **Regression baseline captured** (640/640 unit, 667/667 total)
- [ ] **All 11 pre-migration validation queries returned 0 rows** ⭐ CRITICAL
- [ ] **Migration file generated** (`alembic revision --autogenerate`)
- [ ] **Migration manually verified** (counted operations, added missing if needed)
- [ ] **All 10 constraint operations present** (8 unique + 2 FK)
- [ ] **Migration applied successfully** (`alembic upgrade head`)
- [ ] **Database verification confirms 10 constraints exist** (information_schema query)
- [ ] **ALL 640 existing unit tests still passing**
- [ ] **ALL 667 total tests still passing**
- [ ] **Migration rollback tested** (`alembic downgrade -1`)
- [ ] **Migration re-applied** (`alembic upgrade head`)
- [ ] **Project plan document updated**

---

## Key Files to Review

### Architecture & Design
- `dev-docs/analysis/phase-5.1-db-schema-sync-7-plan.md` - **Master Plan - Task 2** ⭐
- `dev-docs/analysis/phase-5.1-db-schema-sync-7-analysis.md` - **Constraint Gap Analysis** ⭐⭐⭐
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - Golden Master JSON

### Migration Files
- `backend/migrations/` - Alembic migration directory
- Check for latest migration file after generating

---

## Risk Assessment

**For Task 2:**
- **Data Violation Risk:** MEDIUM (existing data may have duplicates or orphans)
- **Alembic Miss Risk:** MEDIUM (Alembic may not detect all constraints)
- **Migration Failure Risk:** LOW (additive changes, no data modification)
- **Rollback Complexity:** LOW (simple constraint removal)
- **Performance Impact:** MINIMAL (constraint checks are highly optimized)
- **Mitigation:** Comprehensive data validation, manual migration verification

---

## Notes

### Important Patterns to Follow
- **Data Validation First:** ALWAYS run all 11 validation queries before migration
- **Zero Violations:** If any violations found, STOP and clean data first
- **Manual Verification:** Count operations in generated migration (8 unique + 2 FK = 10 total)
- **Both Constraints:** Remember integration_sync_mapping needs TWO unique constraints
- **Foreign Key Actions:** Use ondelete='SET NULL' for audit fields
- **Constraint Names:** Use descriptive, unique names following PostgreSQL conventions
- **Zero Regression:** All 640 unit + 667 total tests MUST pass

### Phase 5.1 Task 2 Specific
- **Data validation is mandatory** before applying constraints
- **Alembic may miss constraints** - manual verification is critical
- **10 total constraints** - 8 unique + 2 foreign keys
- **integration_sync_mapping** requires TWO unique constraints (don't forget!)
- **Test rollback** to ensure migration is reversible

### If You Get Stuck
- Use `postgres-local` MCP server to check database state
- Review Phase 5.1 plan Task 2 section for detailed steps
- Check if data validation found violations
- Verify Alembic detected all 10 constraints (count operations manually)
- Verify migration with information_schema queries
- Ask for help if spending >30 minutes on single issue

---

## Example Task Flow

### For Task 2 (Migration):

```bash
# 1. Data validation (MANDATORY)
# Use postgres-local MCP server to run all 11 validation queries
# STOP if any return rows > 0

# 2. Generate migration
alembic revision --autogenerate -m "phase_5_1_add_missing_unique_constraints_and_foreign_keys"

# 3. Open migration file
# Location: backend/migrations/versions/2026_04_09_<hash>_phase_5_1_...py

# 4. Count operations
grep -c "op.create_unique_constraint" backend/migrations/versions/<file>
# Expected: 8
grep -c "op.create_foreign_key" backend/migrations/versions/<file>
# Expected: 2

# 5. If missing any, add manually using syntax from prompt

# 6. Apply migration
alembic upgrade head

# 7. Verify (via MCP server)
SELECT COUNT(*) FROM information_schema.table_constraints
WHERE constraint_name IN (/* all 10 constraint names */);
# Expected: 10

# 8. Test rollback
alembic downgrade -1
alembic upgrade head
```

---

## Questions to Ask

**Before starting:**
1. Have I captured the 640/640 unit and 667/667 total baselines?
2. Do I have the Phase 5.1 plan Task 2 section open for reference?
3. Do I understand the difference between unique constraints and foreign keys?
4. Am I prepared to stop if data validation finds violations?

**During Task 2 (Migration):**
1. Did I run all 11 data validation queries?
2. Did any queries return violations?
3. How many constraint operations did Alembic generate?
4. Are all 10 constraints accounted for in the migration?
5. Does the migration run forward and backward successfully?

**After implementation:**
1. Do I have 100% test pass rate (640/640 unit, 667/667 total)?
2. Do all 10 constraints exist in information_schema?
3. Have I updated the project plan document?
4. Have I tested migration rollback?

---

**Ready to Begin!** 🚀

### Task 2 Checklist:
1. ✅ Capture baseline (640/640 unit, 667/667 total)
2. ⚠️ **CRITICAL: Run all 11 data validation queries via MCP server**
3. ⚠️ **MANDATORY: Stop if ANY query returns violations**
4. 🔧 **Generate Alembic migration**
5. 🔍 **Verify migration has all 10 constraint operations**
6. 🔍 **Manually add any missing operations (if Alembic missed them)**
7. ✅ Apply migration (`alembic upgrade head`)
8. 🔍 **Verify all 10 constraints exist in database (information_schema query)**
9. ↩️ Test rollback (`alembic downgrade -1`)
10. ↩️ Re-apply migration (`alembic upgrade head`)
11. 🔄 Run regression tests (640/640 unit, 667/667 total expected)
12. 📚 Update project plan

Remember: Task 2 is about **generating and applying the migration**. Validate data first, verify Alembic detected all constraints (manually add any missing), test forward and backward, and confirm database state matches expectations!
