# Task [TASK_NUMBER]: [TASK_NAME]

**Reference:** `dev-docs/analysis/phase-5.1-db-schema-sync-7-plan.md` - Task [TASK_NUMBER]
**Authority (Golden Master):**
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - Golden Master JSON
- `dev-docs/analysis/phase-5.1-db-schema-sync-7-analysis.md` - **Constraint Gap Analysis** ⭐
- Current Live Database (Phase 5.0 Post-State)
**Type:** Phase 5.1 - Missing Unique Constraints & Foreign Keys
**Priority:** CRITICAL
**Change Type:** CONSTRAINT VERIFICATION + MIGRATION + TESTING

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

**Phase 5.0 Status:** ✅ COMPLETE (April 9, 2026)
- ✅ 200/200 fields with server defaults enforced at PostgreSQL layer (100% coverage)
- ✅ 640/640 unit tests, 667/667 total tests passing (100%)
- ✅ All fields now have database-layer defaults for direct SQL operations

**Current Baseline:** 640/640 unit tests, 667/667 total tests passing (100%)

**Previous Phases:**
- **Phase 4.5-4.9:** ✅ COMPLETE - Full schema synchronization
- **Phase 5.0:** ✅ COMPLETE - Server defaults enforcement

**See:**
- `dev-docs/analysis/phase-5.0-db-schema-sync-6-plan.md` for Phase 5.0 history
- `dev-docs/analysis/phase-5.1-db-schema-sync-7-analysis.md` for constraint gap details

---

## Current Task: [TASK_NAME]

**Effort:** [EFFORT_ESTIMATE]
**Gap Reference:** Phase 5.1 Analysis - Missing Unique Constraints & Foreign Keys
**Change Type:** [MODEL VERIFICATION | MIGRATION + DATA VALIDATION | CONSTRAINT TESTING]

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

**Record the output of both results:** `640/640 & 667/667 tests passing` (Phase 5.1 baseline - starting from Phase 5.0 completion)

### Step 3: Document Your Baseline

**Write down both of these numbers before proceeding**

**This is your regression checkpoint. ALL these tests MUST still pass after your work.**

---

## ⚠️ CRITICAL: Phase 5.1 Specific Warnings

**BEFORE writing ANY code, review these Phase 5.1 critical issues:**

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

### 2. Unique Constraints Prevent Duplicates Forever

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

### 3. Foreign Keys Enforce Referential Integrity

**What This Means:**
- Cannot insert `tenant.created_by` with a user_id that doesn't exist in `user` table
- Deleting a user will trigger the `ondelete` action (SET NULL, CASCADE, RESTRICT)

**Phase 5.1 Foreign Keys:**
- `tenant.created_by` → `user.id` (ondelete='SET NULL')
- `tenant.updated_by` → `user.id` (ondelete='SET NULL')

**Why SET NULL:** Deleting a user should not cascade delete tenants. The audit trail becomes NULL but the tenant remains.

---

### 4. Constraint Names Must Be Unique and Descriptive

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

### 5. integration_sync_mapping Has TWO Unique Constraints

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

### 6. Alembic May or May Not Detect Missing Constraints

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

### 3. Test Constraint Violations with pytest.raises(IntegrityError)

**Pattern for Testing Unique Constraints:**
```python
import pytest
from sqlalchemy.exc import IntegrityError

def test_unique_constraint_enforced(db_session):
    # Insert first record
    db_session.execute(text("""
        INSERT INTO tenant_domain (tenant_id, domain, verified)
        VALUES (:tenant_id, 'example.com', false)
    """), {"tenant_id": tenant_id})
    
    # Attempt duplicate (should fail)
    with pytest.raises(IntegrityError) as exc_info:
        db_session.execute(text("""
            INSERT INTO tenant_domain (tenant_id, domain, verified)
            VALUES (:tenant_id, 'example.com', false)
        """), {"tenant_id": tenant_id})
    
    assert "duplicate key" in str(exc_info.value).lower()
    db_session.rollback()
```

---

## Requirements

### Task 1: SQLModel Constraint Definitions Verification

**Effort:** 0.25 days
**Scope:** Verify 8 unique constraints + 2 foreign keys in Python models

#### What This Task Accomplishes

Confirm that all 10 missing constraints are correctly defined in the Python SQLModel definitions (they should be, but verification is needed). If any are missing, add them.

#### Tables to Check

**Model Files & Tables:**
1. `backend/app/models/core.py`
   - `TenantDomain` - UNIQUE (tenant_id, domain)
   - `Tenant` - FK (created_by → user.id), FK (updated_by → user.id)

2. `backend/app/models/auth.py`
   - `TenantUserInvite` - UNIQUE (tenant_id, email)

3. `backend/app/models/quoting.py`
   - `QuoteVersion` - UNIQUE (quote_id, version_no)

4. `backend/app/models/billing.py`
   - `SubscriptionUsage` - UNIQUE (subscription_id, product_feature_code, period_start, period_end)

5. `backend/app/models/catalog.py`
   - `SupplierItem` - UNIQUE (tenant_id, supplier_id, sku)

6. `backend/app/models/system.py`
   - `IntegrationSyncMapping` - 2× UNIQUE:
     - UNIQUE (app_service_id, entity_type_code, entity_id)
     - UNIQUE (app_service_id, entity_type_code, external_id)

7. `backend/app/models/crm.py`
   - `EntityAddress` - UNIQUE (entity_type_code, entity_id, address_id)
   - `EntityContact` - UNIQUE (entity_type_code, entity_id, contact_id)

#### Constraint Syntax Reference

**Unique Constraint Definition:**
```python
from sqlalchemy import UniqueConstraint

class TenantDomain(SQLModel, table=True):
    __tablename__ = "tenant_domain"
    
    # Columns
    tenant_id: uuid.UUID = Field(foreign_key="tenant.id")
    domain: str = Field(max_length=255)
    
    # Table-level constraints
    __table_args__ = (
        UniqueConstraint("tenant_id", "domain", name="uq_tenant_domain_tenant_id_domain"),
    )
```

**Multiple Unique Constraints (integration_sync_mapping):**
```python
from sqlalchemy import UniqueConstraint

class IntegrationSyncMapping(SQLModel, table=True):
    __tablename__ = "integration_sync_mapping"
    
    # Columns
    app_service_id: uuid.UUID = Field(foreign_key="app_service.id")
    entity_type_code: str = Field(max_length=50)
    entity_id: uuid.UUID
    external_id: str = Field(max_length=255)
    
    # Multiple unique constraints
    __table_args__ = (
        UniqueConstraint(
            "app_service_id", "entity_type_code", "entity_id",
            name="uq_integration_sync_mapping_internal"
        ),
        UniqueConstraint(
            "app_service_id", "entity_type_code", "external_id",
            name="uq_integration_sync_mapping_external"
        ),
    )
```

**Foreign Key Definition:**
```python
from sqlmodel import Field

class Tenant(SQLModel, table=True):
    __tablename__ = "tenant"
    
    # Audit fields with foreign keys
    created_by: Optional[uuid.UUID] = Field(
        default=None,
        foreign_key="user.id",
        nullable=True
    )
    updated_by: Optional[uuid.UUID] = Field(
        default=None,
        foreign_key="user.id",
        nullable=True
    )
```

**Success Criteria for Task 1:**
- [ ] All 8 unique constraints present in Python model `__table_args__`
- [ ] Both foreign keys defined with `foreign_key="user.id"` in Tenant model
- [ ] Code passes Python syntax validation
- [ ] All models import successfully (`python -c "from app.models import *"`)

---

### Task 2: Alembic Migration Generation with Data Validation

**Effort:** 0.5 days
**Dependencies:** Task 1 must be complete
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
    -- ... all 10 constraint names
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

### Task 3: Comprehensive Constraint Enforcement Testing

**Effort:** 0.5 days
**Dependencies:** Tasks 1 & 2 must be complete

#### What This Task Accomplishes

Validate that all 10 constraints are enforced at the PostgreSQL layer using tests that attempt to violate constraints and verify IntegrityError is raised.

#### Test File Structure

**File:** `backend/tests/test_phase_5_1_constraint_enforcement.py`

**Test Pattern:**
```python
"""
Test Suite: Phase 5.1 - Constraint Enforcement Verification
Validates that unique constraints and foreign keys are enforced at PostgreSQL layer

Reference: phase-5.1-db-schema-sync-7-plan.md
"""
import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
import uuid


class TestUniqueConstraintsEnforced:
    """Verify unique constraints prevent duplicate records"""
    
    def test_tenant_domain_unique_constraint(self, db_session):
        """Verify UNIQUE (tenant_id, domain) enforced"""
        tenant_id = uuid.uuid4()
        
        # Create tenant
        db_session.execute(text("""
            INSERT INTO tenant (id, tenant_name, default_timezone)
            VALUES (:id, 'Test Tenant', 'America/New_York')
        """), {"id": tenant_id})
        
        # Insert first domain
        db_session.execute(text("""
            INSERT INTO tenant_domain (tenant_id, domain, verified)
            VALUES (:tenant_id, 'example.com', false)
        """), {"tenant_id": tenant_id})
        
        # Attempt duplicate (should fail)
        with pytest.raises(IntegrityError) as exc_info:
            db_session.execute(text("""
                INSERT INTO tenant_domain (tenant_id, domain, verified)
                VALUES (:tenant_id, 'example.com', false)
            """), {"tenant_id": tenant_id})
        
        assert "duplicate key" in str(exc_info.value).lower()
        db_session.rollback()
    
    def test_integration_sync_mapping_internal_unique_constraint(self, db_session):
        """Verify UNIQUE (app_service_id, entity_type_code, entity_id)"""
        service_id = uuid.uuid4()
        entity_id = uuid.uuid4()
        
        # Create app_service
        db_session.execute(text("""
            INSERT INTO app_service (id, service_name, provider_name)
            VALUES (:id, 'QuickBooks', 'Intuit')
        """), {"id": service_id})
        
        # Insert first mapping
        db_session.execute(text("""
            INSERT INTO integration_sync_mapping (
                app_service_id, entity_type_code, entity_id, external_id
            )
            VALUES (:service_id, 'customer', :entity_id, 'qb-123')
        """), {"service_id": service_id, "entity_id": entity_id})
        
        # Attempt duplicate internal mapping (should fail)
        with pytest.raises(IntegrityError) as exc_info:
            db_session.execute(text("""
                INSERT INTO integration_sync_mapping (
                    app_service_id, entity_type_code, entity_id, external_id
                )
                VALUES (:service_id, 'customer', :entity_id, 'qb-456')
            """), {"service_id": service_id, "entity_id": entity_id})
        
        assert "duplicate key" in str(exc_info.value).lower()
        db_session.rollback()
    
    def test_integration_sync_mapping_external_unique_constraint(self, db_session):
        """Verify UNIQUE (app_service_id, entity_type_code, external_id)"""
        service_id = uuid.uuid4()
        entity_id = uuid.uuid4()
        
        # Create app_service
        db_session.execute(text("""
            INSERT INTO app_service (id, service_name, provider_name)
            VALUES (:id, 'QuickBooks', 'Intuit')
        """), {"id": service_id})
        
        # Insert first mapping
        db_session.execute(text("""
            INSERT INTO integration_sync_mapping (
                app_service_id, entity_type_code, entity_id, external_id
            )
            VALUES (:service_id, 'customer', :entity_id, 'qb-123')
        """), {"service_id": service_id, "entity_id": entity_id})
        
        # Attempt duplicate external mapping (should fail)
        with pytest.raises(IntegrityError) as exc_info:
            db_session.execute(text("""
                INSERT INTO integration_sync_mapping (
                    app_service_id, entity_type_code, entity_id, external_id
                )
                VALUES (:service_id, 'customer', :new_entity_id, 'qb-123')
            """), {"service_id": service_id, "new_entity_id": uuid.uuid4()})
        
        assert "duplicate key" in str(exc_info.value).lower()
        db_session.rollback()


class TestForeignKeysEnforced:
    """Verify foreign key constraints prevent orphaned references"""
    
    def test_tenant_created_by_foreign_key(self, db_session):
        """Verify tenant.created_by → user.id enforced"""
        # Test 1: Valid reference (should succeed)
        user_id = uuid.uuid4()
        tenant_id = uuid.uuid4()
        
        db_session.execute(text("""
            INSERT INTO "user" (id, username, email)
            VALUES (:id, 'testuser', 'test@example.com')
        """), {"id": user_id})
        
        db_session.execute(text("""
            INSERT INTO tenant (id, tenant_name, default_timezone, created_by)
            VALUES (:id, 'Test Tenant', 'America/New_York', :created_by)
        """), {"id": tenant_id, "created_by": user_id})
        
        db_session.commit()
        
        # Test 2: Invalid reference (should fail)
        invalid_user_id = uuid.uuid4()
        
        with pytest.raises(IntegrityError) as exc_info:
            db_session.execute(text("""
                INSERT INTO tenant (id, tenant_name, default_timezone, created_by)
                VALUES (:id, 'Test Tenant 2', 'America/New_York', :created_by)
            """), {"id": uuid.uuid4(), "created_by": invalid_user_id})
        
        assert "foreign key" in str(exc_info.value).lower()
        db_session.rollback()
```

**SQL Verification Queries:**
```sql
-- Query: Verify all 10 constraints exist
SELECT 
    constraint_type,
    COUNT(*) AS constraint_count
FROM information_schema.table_constraints
WHERE table_schema = 'public'
  AND constraint_name IN (
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
  )
GROUP BY constraint_type;
-- Expected: UNIQUE = 8, FOREIGN KEY = 2
```

**Success Criteria for Task 3:**
- [ ] Test file created with constraint enforcement tests
- [ ] Tests validate all 8 unique constraints prevent duplicates
- [ ] Tests validate both foreign keys prevent orphaned references
- [ ] Full test suite passes: 648+/648+ unit tests, 675+/675+ total (100%)
- [ ] SQL verification confirms all 10 constraints exist

---

## 🎯 AFTER YOU COMPLETE - Verify No Regressions

**CRITICAL:** After all work is complete, verify the baseline.

### Step 1: Run Full Test Suite

```bash
cd backend
source .venv/bin/activate

# Run unit tests (no integration)
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Expected: 648+ passed (640 baseline + ~8 new tests)

# Run all tests
pytest tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Expected: 675+ passed (667 baseline + ~8 new tests)
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

Find Task [TASK_NUMBER] and update with:

```markdown
### Task [TASK_NUMBER]: [TASK_NAME]

**Status:** ✅ COMPLETE (YYYY-MM-DD)
**Effort:** [ACTUAL_DAYS] days (actual)
**Priority:** CRITICAL

**Implementation Summary:**

- Model Verification: All 8 unique constraints + 2 FKs verified in Python models
- Data Validation: All 11 validation queries returned 0 violations
- Migration: [`YYYY_MM_DD_HHMM-[hash]_phase_5_1_add_missing_unique_constraints_and_foreign_keys.py`]
- Test Suite: [`test_phase_5_1_constraint_enforcement.py`] - 8+ tests ✅
- Final Results: 648/648 unit tests (100%), 675/675 total tests (100%)

**Key Changes:**
- ✅ 8 unique constraints added at database layer
- ✅ 2 foreign keys added for tenant audit trail
- ✅ Database state fully aligns with Golden Master JSON
- ✅ Zero regressions in existing test suite
- ✅ Constraint enforcement verified via duplicate/orphan tests

**Verification:**
- All 10 constraints verified via information_schema query
- IntegrityError tests confirm constraints enforced at database layer
- Migration rollback tested successfully
```

---

## Success Criteria

**MUST COMPLETE ALL BEFORE MARKING TASK AS DONE:**

### For ALL Phase 5.1 Tasks:
- [ ] **Regression baseline captured** (640/640 unit, 667/667 total)
- [ ] **All 11 pre-migration validation queries returned 0 rows**
- [ ] **All 10 constraints verified in Python models**
- [ ] **Alembic migration generated and verified**
- [ ] **All missing constraint operations added manually (if needed)**
- [ ] **Migration applied successfully** (`alembic upgrade head`)
- [ ] **Verification tests written and passing**
- [ ] **ALL 640 existing unit tests still passing**
- [ ] **ALL 667 total tests still passing**
- [ ] **New total: 648/648 unit, 675/675 total (100%)**
- [ ] **information_schema confirms 10 constraints exist**
- [ ] **Migration rollback tested** (`alembic downgrade -1`)
- [ ] **Project plan document updated**

### Task-Specific Validation:

**Task 1 (Model Verification):**
- [ ] All 8 unique constraints present in model `__table_args__`
- [ ] Both foreign keys defined in Tenant model
- [ ] Python syntax valid (`python -c "from app.models import *"`)

**Task 2 (Migration):**
- [ ] All data validation queries passed (0 violations)
- [ ] Migration file generated with all 10 operations
- [ ] Migration runs forward successfully
- [ ] Migration runs backward successfully
- [ ] Constraints verified in database

**Task 3 (Testing):**
- [ ] Constraint enforcement tests validate duplicate prevention
- [ ] Foreign key tests validate orphan prevention
- [ ] Full regression suite passes

---

## Key Files to Review

### Architecture & Design
- `dev-docs/analysis/phase-5.1-db-schema-sync-7-plan.md` - **Master Plan** ⭐
- `dev-docs/analysis/phase-5.1-db-schema-sync-7-analysis.md` - **Constraint Gap Analysis** ⭐⭐⭐
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - Golden Master JSON

### Backend Models
- `backend/app/models/core.py` - Tenant, TenantDomain
- `backend/app/models/auth.py` - TenantUserInvite
- `backend/app/models/quoting.py` - QuoteVersion
- `backend/app/models/billing.py` - SubscriptionUsage
- `backend/app/models/catalog.py` - SupplierItem
- `backend/app/models/system.py` - IntegrationSyncMapping
- `backend/app/models/crm.py` - EntityAddress, EntityContact

---

## Risk Assessment

**For Phase 5.1:**
- **Data Violation Risk:** MEDIUM (existing data may have duplicates or orphans)
- **Constraint Conflict Risk:** LOW (constraints match business logic)
- **Application Impact:** MEDIUM (code may need updates for constraint handling)
- **Migration Failure Risk:** LOW (additive changes, no data modification)
- **Rollback Complexity:** LOW (simple constraint removal)
- **Performance Impact:** MINIMAL (constraint checks are highly optimized)
- **Mitigation:** Comprehensive data validation, systematic testing

---

## Notes

### Important Patterns to Follow
- **Data Validation First:** ALWAYS run all 11 validation queries before migration
- **Zero Violations:** If any violations found, STOP and clean data first
- **Both Constraints:** Remember integration_sync_mapping needs TWO unique constraints
- **Foreign Key Actions:** Use ondelete='SET NULL' for audit fields
- **Constraint Names:** Use descriptive, unique names following PostgreSQL conventions
- **Zero Regression:** All 640 unit + 667 total tests MUST pass

### Phase 5.1 Specific
- **Small focused sync:** 10 constraints across 8 tables
- **Data validation critical:** Constraints can't be applied if violations exist
- **Duplicate prevention:** Unique constraints permanently prevent duplicates
- **Referential integrity:** Foreign keys ensure audit trail validity
- **QuickBooks safety:** Sync mapping constraints prevent integration conflicts

### If You Get Stuck
- Use `postgres-local` MCP server to check database state
- Review Phase 5.1 analysis for constraint details
- Check if data validation found violations
- Search for existing constraint definitions in models
- Verify migration with information_schema queries
- Ask for help if spending >30 minutes on single issue

---

## Example Task Flow

### For Phase 5.1 Task 1 (Model Verification):

```bash
# 1. Baseline
cd backend
source .venv/bin/activate
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Record: 640 passed

# 2. Open model files and check for constraints
# Edit backend/app/models/core.py
# Find TenantDomain class
# Look for __table_args__ with UniqueConstraint

# Expected:
class TenantDomain(SQLModel, table=True):
    __table_args__ = (
        UniqueConstraint("tenant_id", "domain", name="uq_tenant_domain_tenant_id_domain"),
    )

# If missing, add it
# Repeat for all 8 tables

# 3. Verify syntax
python -c "from app.models import *"
# Should load without errors
```

### For Phase 5.1 Task 2 (Migration):

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

# 5. If missing any, add manually using syntax from plan

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
2. Do I have the Phase 5.1 analysis document open for reference?
3. Do I understand the difference between unique constraints and foreign keys?
4. Am I prepared to stop if data validation finds violations?

**During Task 1 (Models):**
1. Does this table need a unique constraint or foreign key?
2. Is the constraint defined in __table_args__?
3. For integration_sync_mapping, are BOTH unique constraints present?
4. Are foreign keys defined with correct ondelete action?

**During Task 2 (Migration):**
1. Did I run all 11 data validation queries?
2. Did any queries return violations?
3. How many constraint operations did Alembic generate?
4. Are all 10 constraints accounted for in the migration?
5. Does the migration run forward and backward successfully?

**After implementation:**
1. Do I have 100% test pass rate (648/648 unit, 675/675 total)?
2. Do all 10 constraints exist in information_schema?
3. Do duplicate INSERT attempts raise IntegrityError as expected?
4. Have I updated the project plan document?
5. Have I tested migration rollback?

---

**Ready to Begin!** 🚀

### Phase 5.1 Task Checklist:
1. ✅ Capture baseline (640/640 unit, 667/667 total)
2. 🔍 **Verify all 8 unique constraints in Python models**
3. 🔍 **Verify both foreign keys in Tenant model**
4. ✅ Verify Python syntax (`python -c "from app.models import *"`)
5. ⚠️ **CRITICAL: Run all 11 data validation queries via MCP server**
6. ⚠️ **MANDATORY: Stop if ANY query returns violations**
7. 🔧 **Generate Alembic migration**
8. 🔍 **Verify migration has all 10 constraint operations**
9. ✅ Apply migration (`alembic upgrade head`)
10. 🧪 **Create constraint enforcement tests (IntegrityError tests)**
11. 🔄 Run regression tests (648/648 unit, 675/675 total expected)
12. ↩️ Test rollback
13. 📚 Update project plan

Remember: Phase 5.1 is about **database constraint enforcement**. Validate data first, verify all constraints are added, and test that duplicates/orphans are rejected. This is surgical, focused work - validate everything before applying constraints!
