# Task 1: SQLModel Constraint Definitions Verification

**Reference:** `dev-docs/analysis/phase-5.1-db-schema-sync-7-plan.md` - Task 1
**Authority (Golden Master):**
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - Golden Master JSON
- `dev-docs/analysis/phase-5.1-db-schema-sync-7-analysis.md` - **Constraint Gap Analysis** ⭐
- Current Live Database (Phase 5.0 Post-State)
**Type:** Phase 5.1 - Missing Unique Constraints & Foreign Keys
**Priority:** CRITICAL
**Change Type:** CONSTRAINT VERIFICATION

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

## Current Task: SQLModel Constraint Definitions Verification

**Effort:** 0.25 days
**Gap Reference:** Phase 5.1 Analysis - Missing Unique Constraints & Foreign Keys
**Change Type:** MODEL VERIFICATION

Confirm that all 10 missing constraints are correctly defined in the Python SQLModel definitions. Based on previous phases, they should already be present, but verification is mandatory. If any are missing, add them using the correct SQLModel syntax.

### What Needs to Be Verified

**8 Unique Constraints to Verify:**

| Table | Model File | Constraint | Columns |
|-------|-----------|-----------|---------|
| `tenant_domain` | `backend/app/models/core.py` | UNIQUE | `(tenant_id, domain)` |
| `tenant_user_invite` | `backend/app/models/auth.py` | UNIQUE | `(tenant_id, email)` |
| `quote_version` | `backend/app/models/quoting.py` | UNIQUE | `(quote_id, version_no)` |
| `subscription_usage` | `backend/app/models/billing.py` | UNIQUE | `(subscription_id, product_feature_code, period_start, period_end)` |
| `supplier_item` | `backend/app/models/catalog.py` | UNIQUE | `(tenant_id, supplier_id, sku)` |
| `integration_sync_mapping` | `backend/app/models/system.py` | UNIQUE (2×) | `(app_service_id, entity_type_code, entity_id)` |
| `integration_sync_mapping` | `backend/app/models/system.py` | UNIQUE | `(app_service_id, entity_type_code, external_id)` |
| `entity_address` | `backend/app/models/crm.py` | UNIQUE | `(entity_type_code, entity_id, address_id)` |
| `entity_contact` | `backend/app/models/crm.py` | UNIQUE | `(entity_type_code, entity_id, contact_id)` |

**2 Foreign Keys to Verify:**

| Table | Model File | Column | References |
|-------|-----------|--------|------------|
| `tenant` | `backend/app/models/core.py` | `created_by` | `user.id` |
| `tenant` | `backend/app/models/core.py` | `updated_by` | `user.id` |

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

### 1. Unique Constraints Must Be Defined in __table_args__

**SQLModel Pattern for Unique Constraints:**

Multi-column unique constraints CANNOT be defined inline. They MUST use the `__table_args__` class attribute:

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

**For Multiple Constraints (integration_sync_mapping has TWO):**

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

---

### 2. Foreign Keys Are Defined Inline with Field()

**SQLModel Pattern for Foreign Keys:**

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

**Important:** The `foreign_key` parameter is a string reference to the target table and column.

---

### 3. integration_sync_mapping Requires TWO Unique Constraints

**CRITICAL:** This table needs **both** constraints to prevent mapping conflicts:

```python
# Constraint 1: Prevent duplicate internal entity mappings
# UNIQUE (app_service_id, entity_type_code, entity_id)

# Constraint 2: Prevent duplicate external entity mappings
# UNIQUE (app_service_id, entity_type_code, external_id)
```

**Why Two?** A single internal entity can only map to one external ID per service, AND a single external ID can only map to one internal entity per service.

**Common Mistake:** Only adding one of these constraints. Both are required.

---

### 4. Constraint Naming Conventions

**PostgreSQL Best Practices:**

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

## ⚠️ CRITICAL: Coding Agent Best Practices (From Previous Phases)

### 1. Use SQLModel `select()` with `exec()` NOT `query()`

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

## 🎯 AFTER YOU COMPLETE - Verify No Regressions

**CRITICAL:** After all work is complete, verify the baseline.

### Step 1: Run Full Test Suite

```bash
cd backend
source .venv/bin/activate

# Run unit tests (no integration)
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Expected: 640 passed (no new tests in this task, just verification)

# Run all tests
pytest tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Expected: 667 passed (no new tests in this task, just verification)
```

### Step 2: Verify Model Imports

```bash
cd backend
python -c "from app.models import *; print('✅ All models loaded successfully')"
```

### Step 3: Final Validation

**If ANY tests fail:**
1. Identify failing tests
2. Check if constraint syntax errors in models
3. Verify all imports are correct
4. Fix and re-run until 100% pass rate

---

## Documentation Update

**File to Update:** `dev-docs/analysis/phase-5.1-db-schema-sync-7-plan.md`

Find Task 1 and update with:

```markdown
### Task 1: SQLModel Constraint Definitions Verification

**Status:** ✅ COMPLETE (YYYY-MM-DD)
**Effort:** [ACTUAL_HOURS] hours (actual)
**Priority:** CRITICAL

**Implementation Summary:**

- Model Verification: All 8 unique constraints + 2 FKs verified in Python models
- Changes Made: [List any constraints that were added, or "No changes - all constraints already present"]
- Models Checked: core.py, auth.py, quoting.py, billing.py, catalog.py, system.py, crm.py
- Test Results: 640/640 unit tests (100%), 667/667 total tests (100%)

**Key Findings:**
- ✅ All constraints correctly defined in Python models (or added if missing)
- ✅ Zero regressions in existing test suite
- ✅ Model imports successful
```

---

## Success Criteria

**MUST COMPLETE ALL BEFORE MARKING TASK AS DONE:**

### For Task 1 (Model Verification):
- [ ] All 8 unique constraints present in model `__table_args__`
- [ ] Both foreign keys defined in Tenant model
- [ ] Python syntax valid (`python -c "from app.models import *"`)
- [ ] **Regression baseline maintained** (640/640 unit, 667/667 total)
- [ ] **Project plan document updated**

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

**For Task 1:**
- **Syntax Error Risk:** LOW (simple constraint definitions)
- **Import Error Risk:** LOW (straightforward imports)
- **Logic Error Risk:** MINIMAL (verification only, no complex logic)
- **Regression Risk:** MINIMAL (no changes to database, only model verification)

---

## Notes

### Important Patterns to Follow
- **Unique Constraints:** Use `__table_args__` with `UniqueConstraint()`
- **Foreign Keys:** Use `Field(foreign_key="table.column")`
- **Both Constraints:** Remember integration_sync_mapping needs TWO unique constraints
- **Constraint Names:** Use descriptive, unique names following PostgreSQL conventions
- **Zero Regression:** All 640 unit + 667 total tests MUST pass

### Phase 5.1 Task 1 Specific
- **Verification focus:** Check existing model definitions, don't assume changes needed
- **Import check:** Ensure all SQLAlchemy imports are present (UniqueConstraint)
- **Naming consistency:** Constraint names should match expected database names
- **Documentation:** Note which constraints were already present vs. which were added

### If You Get Stuck
- Review Phase 5.1 analysis for constraint details
- Check Golden Master JSON for authoritative constraint definitions
- Search for existing constraint patterns in other models
- Verify SQLModel/SQLAlchemy import statements
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

# 4. Re-run tests to ensure no regressions
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Expected: 640 passed (same as baseline)
```

---

## Questions to Ask

**Before starting:**
1. Have I captured the 640/640 unit and 667/667 total baselines?
2. Do I have the Phase 5.1 analysis document open for reference?
3. Do I understand the difference between unique constraints and foreign keys?
4. Do I know which models need to be checked?

**During Task 1 (Models):**
1. Does this table need a unique constraint or foreign key?
2. Is the constraint defined in __table_args__?
3. For integration_sync_mapping, are BOTH unique constraints present?
4. Are foreign keys defined with correct ondelete action?

**After implementation:**
1. Do I have 100% test pass rate (640/640 unit, 667/667 total)?
2. Do all models import successfully?
3. Have I updated the project plan document?
4. Have I documented which constraints were added vs. already present?

---

**Ready to Begin!** 🚀

### Task 1 Checklist:
1. ✅ Capture baseline (640/640 unit, 667/667 total)
2. 🔍 **Open backend/app/models/core.py - check TenantDomain and Tenant**
3. 🔍 **Open backend/app/models/auth.py - check TenantUserInvite**
4. 🔍 **Open backend/app/models/quoting.py - check QuoteVersion**
5. 🔍 **Open backend/app/models/billing.py - check SubscriptionUsage**
6. 🔍 **Open backend/app/models/catalog.py - check SupplierItem**
7. 🔍 **Open backend/app/models/system.py - check IntegrationSyncMapping (2 constraints!)**
8. 🔍 **Open backend/app/models/crm.py - check EntityAddress and EntityContact**
9. ✅ Verify Python syntax (`python -c "from app.models import *"`)
10. 🔄 Run regression tests (640/640 unit, 667/667 total expected)
11. 📚 Update project plan

Remember: Task 1 is about **verification first, additions second**. Check if the constraints are already present before making changes. This is focused work - verify all 10 constraints systematically!
