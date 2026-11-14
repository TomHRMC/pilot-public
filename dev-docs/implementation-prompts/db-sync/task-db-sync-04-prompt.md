# Task: Phase 4.5, Phase 2, Task 4 - Missing PL/pgSQL Functions

**Reference:** `dev-docs/analysis/phase-4.5-db-schema-sync-to-design-plan.md` Phase 2, Task 4  
**Gap Reference:** Analysis Section 5 - Missing Functions & Operational Triggers

---

## Context

We're building AevoFab AI, an AI-powered SaaS platform for electrical contractors with voice-controlled quoting and QuickBooks integration. We are aligning the physical database schema with the Golden Master design (`pilot-db-schema-v2.6h.json`).

---

## Completed So Far

**Phase 4.5 Database Schema Synchronization:**

**Phase 1: Foundation (Data Types & Column Fixes) - COMPLETE (3/3 tasks)**
- ✅ Task 1: Timezone Enforcement (9 columns) - 421/421 tests passing
- ✅ Task 2: Citext Conversion for User Email - 428/428 tests passing (455/455 with integration)
- ✅ Task 3: QuickBooks Identity Rule (Customer Table) - 433/433 tests passing (460/460 with integration)

**Baseline:** 433/433 tests passing (100% pass rate without integration tests)  
**With Integration:** 460/460 tests passing (100% pass rate)

**See:** `phase-4.5-db-schema-sync-to-design-plan.md` for full Phase 4.5 details

---

## Current Task

**Implement 3 missing PL/pgSQL functions** that are specified in the Golden Master schema but do not exist in the physical database. These functions provide critical database-level enforcement of business rules.

**Priority:** CRITICAL  
**Estimated Effort:** 2 days  
**Task Spec:** See `phase-4.5-db-schema-sync-to-design-plan.md` Phase 2, Task 4  
**Design Context:** `aevofab-db-process-v2.6h.md`  
**Golden Master:** `pilot-db-schema-v2.6h.json`

---

## Problem Statement

The Golden Master JSON schema specifies 3 critical PL/pgSQL functions that are **completely missing** from the physical database:

### Function 1: `set_updated_at()`
**Purpose:** Automatically bump `updated_at` timestamp on any UPDATE operation

**Missing Triggers:** 20+ tables including:
- `invoice` - Missing `trg_invoice_set_updated_at`
- `quote` - Verify if trigger exists
- `change_order` - Missing trigger
- `job` - Missing trigger
- `customer` - Missing trigger
- All tables with `updated_at` column (see Golden Master for full list)

### Function 2: `guard_created_fields_immutable()`
**Purpose:** Prevent modification of `created_at` and `created_by` fields after initial insert (data integrity protection)

**Missing Triggers:** 50+ tables including:
- `invoice` - `trg_invoice_guard_created_immutable`
- `quote` - Missing trigger
- `job` - Missing trigger
- `customer` - Missing trigger
- All tables with `created_at` column

### Function 3: `guard_tenant_user_platform_isolation()`
**Purpose:** Prevent platform users (staff, superadmin) from being assigned as tenant users (security violation prevention)

**Missing Trigger:**
- `tenant_user` - `trg_tenant_user_guard_platform_biu`

**Impact of Missing Functions:**
- ⚠️ **Data Integrity Risk:** `created_at` can be changed after insert (audit corruption)
- ⚠️ **Stale Data Risk:** `updated_at` not auto-bumping (requires manual SET in every query)
- ⚠️ **Security Risk:** Platform users can be assigned to tenants (isolation violation)
- ⚠️ **Audit Compliance Risk:** Immutable fields can be modified (regulatory violation)

---

## Requirements

### 1. Function Implementations

#### Function 1: `set_updated_at()`

**Implementation:**
```sql
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  NEW.updated_at := NOW();
  RETURN NEW;
END;
$$;
```

**Trigger Pattern (apply to all tables with `updated_at`):**
```sql
CREATE TRIGGER trg_invoice_set_updated_at
BEFORE UPDATE ON invoice
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- Repeat for: quote, change_order, job, customer, site, contact, address, 
-- job_time_entry, job_expense, supplier_item, pricebook_item, etc.
```

**Auto-Generate Trigger List:**
- Query the database to find all tables with `updated_at` column
- Generate CREATE TRIGGER statements for each table
- Verify no existing `set_updated_at()` triggers exist first

---

#### Function 2: `guard_created_fields_immutable()`

**Implementation:**
```sql
CREATE OR REPLACE FUNCTION guard_created_fields_immutable()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF TG_OP = 'UPDATE' THEN
    -- Reject attempts to change created_at
    IF NEW.created_at IS DISTINCT FROM OLD.created_at THEN
      RAISE EXCEPTION 'created_at is immutable (cannot be changed after insert)'
        USING ERRCODE = '23514',
              HINT = 'Remove created_at from UPDATE statement';
    END IF;
    
    -- Reject attempts to change created_by (if column exists)
    -- Use TG_TABLE_NAME to conditionally check for created_by column
    BEGIN
      IF (SELECT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = TG_TABLE_SCHEMA 
          AND table_name = TG_TABLE_NAME 
          AND column_name = 'created_by'
      )) AND NEW.created_by IS DISTINCT FROM OLD.created_by THEN
        RAISE EXCEPTION 'created_by is immutable (cannot be changed after insert)'
          USING ERRCODE = '23514',
                HINT = 'Remove created_by from UPDATE statement';
      END IF;
    END;
  END IF;
  
  RETURN NEW;
END;
$$;
```

**Trigger Pattern (apply to all tables with `created_at`):**
```sql
CREATE TRIGGER trg_invoice_guard_created_immutable
BEFORE UPDATE ON invoice
FOR EACH ROW EXECUTE FUNCTION guard_created_fields_immutable();

-- Repeat for 50+ tables (all tables with created_at column)
```

---

#### Function 3: `guard_tenant_user_platform_isolation()`

**Implementation:**
```sql
CREATE OR REPLACE FUNCTION guard_tenant_user_platform_isolation()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
  platform_role_code text;
BEGIN
  IF TG_OP IN ('INSERT', 'UPDATE') THEN
    -- Check if user has platform role assigned
    SELECT u.platform_role_code INTO platform_role_code
    FROM "user" u
    WHERE u.id = NEW.user_id;
    
    IF platform_role_code IS NOT NULL THEN
      RAISE EXCEPTION 'User % has platform role % and cannot be assigned to a tenant',
        NEW.user_id, platform_role_code
        USING ERRCODE = '23514',
              HINT = 'Platform users (staff, superadmin) cannot be tenant users';
    END IF;
  END IF;
  
  RETURN NEW;
END;
$$;
```

**Trigger (single table: tenant_user):**
```sql
CREATE TRIGGER trg_tenant_user_guard_platform_biu
BEFORE INSERT OR UPDATE ON tenant_user
FOR EACH ROW EXECUTE FUNCTION guard_tenant_user_platform_isolation();
```

---

### 2. Migration Strategy

**Create Alembic Migration:**
- Filename: `2026_03_XX_XXXX-add_missing_plpgsql_functions.py`
- Migration must include:
  1. Create all 3 functions
  2. Auto-generate trigger list from database introspection
  3. Apply triggers to all relevant tables
  4. Downgrade: Drop all triggers, then drop functions

**Pre-Migration Checks:**
- [ ] Verify no existing functions with same names
- [ ] Identify all tables with `updated_at` column (for Function 1)
- [ ] Identify all tables with `created_at` column (for Function 2)
- [ ] Verify `tenant_user` table exists (for Function 3)

**Auto-Generate Trigger Statements:**
```python
# In migration file, use SQL query to find tables
query_updated_at = """
SELECT table_name 
FROM information_schema.columns 
WHERE table_schema = 'public' 
  AND column_name = 'updated_at'
ORDER BY table_name;
"""

query_created_at = """
SELECT table_name 
FROM information_schema.columns 
WHERE table_schema = 'public' 
  AND column_name = 'created_at'
ORDER BY table_name;
"""

# Generate CREATE TRIGGER statements dynamically
```

---

### 3. Test Coverage

**Create:** `backend/tests/test_plpgsql_functions.py`

**Test Cases:**

**Function 1: `set_updated_at()` - 3 tests**
- [ ] Test auto-bump on UPDATE (verify `updated_at` changes without explicit SET)
- [ ] Test multiple UPDATEs (verify timestamp increases each time)
- [ ] Test INSERT does not trigger (only UPDATE should fire trigger)

**Function 2: `guard_created_fields_immutable()` - 4 tests**
- [ ] Test UPDATE `created_at` raises exception (IntegrityError)
- [ ] Test UPDATE `created_by` raises exception
- [ ] Test UPDATE other fields succeeds (does not block valid updates)
- [ ] Test INSERT with `created_at` succeeds (only blocks UPDATE)

**Function 3: `guard_tenant_user_platform_isolation()` - 3 tests**
- [ ] Test platform user (staff role) cannot be added to `tenant_user` (INSERT blocked)
- [ ] Test platform user (superadmin role) cannot be added to `tenant_user`
- [ ] Test normal user (no platform role) can be added to `tenant_user` (success case)
- [ ] Test changing user to platform role after assignment raises exception (UPDATE blocked)

**Integration Tests:**
- [ ] Test real-world workflow: Create invoice, update it, verify `updated_at` auto-bumped
- [ ] Test audit trail: Verify `created_at` immutability protects audit integrity
- [ ] Test security: Verify superadmin user cannot be assigned to tenant

**Expected Test Count:** 10+ new tests (3 + 4 + 3)

---

### 4. Documentation Standards

**Files to Create:**
- [ ] `backend/migrations/versions/2026_03_XX_XXXX-add_missing_plpgsql_functions.py` - Migration file
- [ ] `backend/tests/test_plpgsql_functions.py` - Test suite (10+ tests)
- [ ] Update `phase-4.5-db-schema-sync-to-design-plan.md` Phase 2, Task 4:
  - Mark status ✅ COMPLETE (YYYY-MM-DD)
  - Check off all deliverables
  - Add test results (X/X passing)
  - Include SQL snippets of created functions
  - List all tables with triggers applied

**Cross-References:**
- Golden Master: `pilot-db-schema-v2.6h.json` - Function definitions
- Analysis: `db-schema-dump-vs-design-analysis-v1.0.md` - Section 5

---

### 5. Database Standards

- **DO NOT guess table names** - Use information_schema queries to find tables with `updated_at` and `created_at` columns
- **Follow existing trigger patterns** - Review existing triggers (e.g., `guard_user_endpoint_primary_email()`) for naming conventions
- **Use Alembic migrations** - All schema changes via migration files
- **Test downgrade path** - Verify `alembic downgrade -1` works without errors
- **Function naming:** While existing functions don't follow `_fn` suffix (that's Task 5), new functions can follow current pattern for consistency

---

### 6. Code Standards

- **Type hints required** - Use proper PostgreSQL/SQLAlchemy types
- **Error handling** - Use RAISE EXCEPTION with proper ERRCODE and HINT
- **Docstrings required** - Document each function's purpose
- **Follow existing patterns** - Review existing triggers in migrations folder
- **Test isolation** - Each test must clean up (use db_session fixture with rollback)

---

### 7. Workflow

1. **Review Golden Master** - `pilot-db-schema-v2.6h.json` to understand function specifications
2. **Inspect existing triggers** - Find existing trigger patterns in migrations folder
3. **Query database** - Find all tables needing triggers (updated_at, created_at columns)
4. **Create migration** - Implement 3 functions + auto-generate all triggers
5. **Write tests** - 10+ tests covering all 3 functions
6. **Run tests** - Must pass 100% (baseline 433 + 10+ new = 443+ tests)
7. **Verify in database:**
   ```sql
   -- Check functions exist
   SELECT proname, prosrc FROM pg_proc WHERE proname LIKE '%set_updated_at%';
   SELECT proname, prosrc FROM pg_proc WHERE proname LIKE '%guard_created%';
   SELECT proname, prosrc FROM pg_proc WHERE proname LIKE '%guard_tenant_user%';
   
   -- Check triggers applied
   SELECT tgname, tgrelid::regclass, proname 
   FROM pg_trigger t 
   JOIN pg_proc p ON t.tgfoid = p.oid
   WHERE proname IN ('set_updated_at', 'guard_created_fields_immutable', 'guard_tenant_user_platform_isolation')
   ORDER BY tgrelid::regclass, tgname;
   ```
8. **Update documentation** - Mark Task 4 complete in Phase 4.5 roadmap

---

## Key Files to Review

### Schema & Analysis
- `dev-docs/analysis/phase-4.5-db-schema-sync-to-design-plan.md` - Phase 2, Task 4 spec
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - Golden Master function definitions
- `dev-docs/analysis/db-schema-vs-design/db-schema-dump-vs-design-analysis-v1.0.md` - Gap analysis

### Database Models
- `backend/app/models/*.py` - All models (to verify column existence)
- `backend/app/models/core.py` - User model (for Function 3)
- `backend/app/models/auth.py` - TenantUser model (for Function 3)

### Existing Trigger Examples
- `backend/migrations/versions/2026_03_30_1810-6907731fd637_sync_with_golden_master_v2_6h.py` - Componentized tax triggers
- `backend/migrations/versions/2026_03_30_1819-102c1d8d3d4a_fix_user_endpoint_guard_trigger_logic.py` - Email guard trigger
- `backend/migrations/versions/2026_03_30_1929-cbf672175f02_fix_user_endpoint_sync_race_condition.py` - Email sync trigger

### Test Patterns
- `backend/tests/conftest.py` - Test fixtures (use existing `db_session`, `test_tenant`)
- `backend/tests/test_schema_sync_v2_6h.py` - Schema sync test examples (30 tests)
- `backend/tests/test_timezone_compliance.py` - Timezone test examples (9 tests)

---

## Success Criteria

**MUST COMPLETE ALL BEFORE MARKING TASK AS COMPLETE:**

- [ ] **All 3 PL/pgSQL functions created** in database
- [ ] **Triggers applied to all relevant tables:**
  - [ ] `set_updated_at()` on 20+ tables with `updated_at` column
  - [ ] `guard_created_fields_immutable()` on 50+ tables with `created_at` column
  - [ ] `guard_tenant_user_platform_isolation()` on `tenant_user` table
- [ ] **Migration file created** with upgrade/downgrade paths
- [ ] **Test file created:** `backend/tests/test_plpgsql_functions.py` (10+ tests)
- [ ] **ALL existing tests pass** (baseline 433/433 maintained)
- [ ] **ALL new tests pass** (10+ new tests, 100% pass rate)
- [ ] **Test pass rate: 100%** (443+/443+ passing, 0 failing)
- [ ] **Manual verification:**
  - Attempting to UPDATE `created_at` raises exception
  - `updated_at` auto-bumps without explicit SET clause
  - Platform users cannot be added to `tenant_user` table
- [ ] **Documentation updated:**
  - Phase 4.5 roadmap Task 4 marked ✅ COMPLETE
  - Test results added (X/X passing)
  - SQL function implementations documented

**Database Verification Queries:**
```sql
-- Verify function 1 exists
SELECT proname, prosrc FROM pg_proc WHERE proname = 'set_updated_at';

-- Verify function 2 exists
SELECT proname, prosrc FROM pg_proc WHERE proname = 'guard_created_fields_immutable';

-- Verify function 3 exists
SELECT proname, prosrc FROM pg_proc WHERE proname = 'guard_tenant_user_platform_isolation';

-- Count triggers using function 1 (should be 20+)
SELECT COUNT(*) FROM pg_trigger t 
JOIN pg_proc p ON t.tgfoid = p.oid 
WHERE p.proname = 'set_updated_at';

-- Count triggers using function 2 (should be 50+)
SELECT COUNT(*) FROM pg_trigger t 
JOIN pg_proc p ON t.tgfoid = p.oid 
WHERE p.proname = 'guard_created_fields_immutable';

-- Verify trigger on tenant_user (should be 1)
SELECT tgname FROM pg_trigger t 
JOIN pg_proc p ON t.tgfoid = p.oid 
WHERE p.proname = 'guard_tenant_user_platform_isolation' 
  AND t.tgrelid = 'tenant_user'::regclass;
```

---

## Testing Strategy

**Before Implementation:**
```bash
# Run baseline tests (should be 433/433 passing)
cd backend && source .venv/bin/activate && pytest --ignore=tests/integration/ tests/ -v
```

**During Implementation:**
```bash
# Run new tests as you write them
pytest backend/tests/test_plpgsql_functions.py -v

# Run full suite periodically
pytest --ignore=tests/integration/ tests/ -v
```

**After Implementation:**
```bash
# Run full suite (should be 443+/443+ passing)
pytest --ignore=tests/integration/ tests/ -v

# Run with integration tests (optional - uses SendGrid quota)
pytest tests/ -v

# Verify trigger behavior manually (connect to database)
psql $DATABASE_URL
# Try to UPDATE created_at (should fail)
# Try to INSERT platform user into tenant_user (should fail)
```

---

## Risk Assessment

**Data Corruption Risk:** MEDIUM
- Function 2 blocks UPDATE attempts on `created_at` - may break existing code
- **Mitigation:** Run full test suite to identify any code that modifies created_at
- **Rollback Plan:** Alembic downgrade drops all triggers and functions

**Performance Risk:** LOW
- Triggers add ~1-2ms per UPDATE operation
- **Acceptable:** Trigger overhead negligible compared to network/query time
- **Monitoring:** Use EXPLAIN ANALYZE to verify no performance regressions

**Security Risk:** LOW
- Function 3 prevents platform/tenant user mixing (improves security)
- **Benefit:** Closes isolation loophole identified in gap analysis

**Downtime Required:** NONE
- CREATE FUNCTION and CREATE TRIGGER are online operations in PostgreSQL 12+
- No table locks, no downtime

---

## Notes

- **MVP Focus:** These functions are CRITICAL for data integrity and audit compliance
- **Phase 2 Context:** Part of "Core Functions & Triggers" phase
- **Blocking:** Task 6 (Audit Trigger Coverage) depends on this task
- **Follow-up:** Task 5 (Function Naming Standard) will rename existing functions to `_fn` suffix
- **Golden Master Alignment:** After this task, 3/3 missing functions will be implemented

---

## Questions to Ask

**Before starting:**
1. Have I reviewed the Golden Master JSON schema for function specifications?
2. Do I understand the purpose of each function (updated_at, immutability, isolation)?
3. What tables need triggers (query information_schema first)?
4. What existing trigger patterns should I follow?

**During implementation:**
1. Am I using information_schema queries to find tables (not hardcoding)?
2. Are all triggers following the naming convention (trg_[table]_[function]_[timing])?
3. Are my error messages clear and actionable (HINT clause)?
4. Are ALL tests passing (100% pass rate)?

**After implementation:**
1. Do I have 100% test pass rate (443+/443+ passing, 0 failing)?
2. Have I verified triggers work manually in database?
3. Can I demonstrate each function preventing invalid operations?
4. Is documentation updated with function implementations?

---

## Example Test Flow

```python
# backend/tests/test_plpgsql_functions.py

def test_set_updated_at_auto_bumps(db_session, test_tenant):
    """Test that updated_at auto-bumps on UPDATE without explicit SET"""
    from app.models.crm import Customer
    import time
    
    # Create customer
    customer = Customer(
        tenant_id=test_tenant.id,
        display_name="Test Customer",
        type="person"
    )
    db_session.add(customer)
    db_session.commit()
    
    original_updated_at = customer.updated_at
    time.sleep(0.1)  # Ensure time difference
    
    # Update customer (without setting updated_at)
    customer.display_name = "Updated Customer"
    db_session.commit()
    db_session.refresh(customer)
    
    # Verify updated_at changed
    assert customer.updated_at > original_updated_at

def test_guard_created_at_immutable(db_session, test_tenant):
    """Test that updating created_at raises exception"""
    from app.models.crm import Customer
    from datetime import datetime, timezone
    from sqlalchemy.exc import IntegrityError
    
    # Create customer
    customer = Customer(
        tenant_id=test_tenant.id,
        display_name="Test Customer",
        type="person"
    )
    db_session.add(customer)
    db_session.commit()
    
    # Try to change created_at (should fail)
    with pytest.raises(IntegrityError) as exc:
        customer.created_at = datetime.now(timezone.utc)
        db_session.commit()
    
    assert "created_at is immutable" in str(exc.value)

def test_guard_platform_user_isolation(db_session, test_tenant):
    """Test that platform users cannot be tenant users"""
    from app.models.core import User
    from app.models.auth import TenantUser
    from sqlalchemy.exc import IntegrityError
    
    # Create platform user (staff role)
    platform_user = User(
        email="staff@aevofab.example.com",
        platform_role_code="staff"
    )
    db_session.add(platform_user)
    db_session.commit()
    
    # Try to add to tenant (should fail)
    with pytest.raises(IntegrityError) as exc:
        tenant_user = TenantUser(
            tenant_id=test_tenant.id,
            user_id=platform_user.id,
            role_code="admin"
        )
        db_session.add(tenant_user)
        db_session.commit()
    
    assert "has platform role" in str(exc.value)
    assert "cannot be assigned to a tenant" in str(exc.value)
```

---

**End of Task Prompt**
