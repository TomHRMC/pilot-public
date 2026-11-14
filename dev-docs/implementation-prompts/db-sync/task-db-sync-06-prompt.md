# Phase 4.5 Task Prompt
## Task: Phase 2, Task #6 - Audit Trigger Coverage

```
Task: Phase 2, Task #6 - Audit Trigger Coverage (Dozens of Missing Tables)
Reference: dev-docs/analysis/phase-4.5-db-schema-sync-to-design-plan.md Task #6
(Analysis: Section 1 - Audit Trigger Coverage in db-schema-dump-vs-design-analysis-v1.0.md)

## Context

We're building AevoFab AI, an AI-powered SaaS platform for electrical contractors with voice-controlled quoting and QuickBooks integration. We are now synchronizing our physical database schema with the Golden Master design (v2.6h JSON) to ensure 100% alignment.

## Completed So Far

**Phases 1-3: Core MVP Development (COMPLETE)**
- ✅ Phase 1-A: Critical Blockers (7 tasks) - Test endpoints, tenant isolation, idempotency
- ✅ Phase 1-B: Core Completeness (4 tasks) - Polymorphic relationships, quote acceptance
- ✅ Phase 2: Background Processing (4 tasks) - Celery, profitability rollup, notifications
- ✅ Phase 3: QuickBooks Integration (4 tasks) - OAuth, sync, conflicts, webhooks

**Phase 4: Enterprise Hardening (COMPLETE)**
- ✅ Task 20: Audit Event Logging (20 tests)
- ✅ Task 21: RBAC Permission System (40 tests)
- ✅ Task 22: Rate Limiting (13 tests)
- ✅ Task 23: Integration Test Suite (27 tests)

**Phase 4.5: Database Schema Synchronization (IN PROGRESS)**
- ✅ Gap 1: ContactPortalInvite UNIQUE constraint (March 30, 2026)
- ✅ Gap 2: User Endpoint Primary Email Guard function + triggers
- ✅ Gap 3: Componentized Tax Logic (3 functions, 6 triggers)
- ✅ Gap 4: NotificationDeliveryAttempt lifecycle fields
- ✅ Gap 5: QuoteAcceptance timezone compliance
- ✅ Gap 6: AuditEvent actor_type CHECK constraint
- ✅ Phase 1, Task 1: Timezone Enforcement (9 violations fixed)
- ✅ Phase 1, Task 2: Citext Conversion for User Email
- ✅ Phase 1, Task 3: QuickBooks Identity Rule (Customer Table)
- ✅ Phase 2, Task 4: Missing PL/pgSQL Functions (3 functions + 200 triggers)
- ✅ Phase 2, Task 5: Function Naming Standard Compliance
- **Current Status:** 444/444 tests passing without integration tests, 471/471 total (100%)
- **Remaining Work:** 8 tasks across Phases 2-4

**Test Coverage:** 444/444 passing (100% pass rate) without integration tests; 471/471 with integration tests
**See:** dev-docs/analysis/phase-4.5-db-schema-sync-to-design-plan.md for full details

## Current Task

**Phase 2, Task 6: Audit Trigger Coverage (Dozens of Missing Tables)**

Add `audit.log_changes()` triggers to all critical tables that are currently missing audit trail coverage. Currently only 12 tables have audit triggers, but dozens more require them for compliance and security.

**The Problem:**
The Golden Master requires an `AFTER` trigger executing `audit.log_changes()` on all critical tables for comprehensive change history tracking. Currently, audit triggers exist on only **12 tables** (customer, invoice, job, quote, payment, site, contact, address, job_time_entry, job_expense, supplier_item, pricebook_item), but are **missing** from dozens of critical tables including:

**Critical Missing Tables:**
- **`user`** - User account changes (CRITICAL for security audit)
- **`tenant`** - Tenant configuration changes (CRITICAL for compliance)
- **`change_order`** - Scope change approvals (CRITICAL for legal protection)
- **`subscription`** - Billing tier changes (CRITICAL for revenue audit)
- **`product_plan`** - SaaS pricing changes (CRITICAL for contract compliance)
- **`supplier`** - Supplier master data (HIGH for procurement audit)
- **`payment_method`** - Payment instrument changes (HIGH for PCI compliance)
- **`app_service`** - Service configuration (HIGH for debugging)
- **All temporal/versioned tables:**
  - `tenant_markup_version`
  - `supplier_item_price`
  - `tax_rate_version`
  - `pricebook_item_version`
  - `product_plan_version`
  - `product_plan_product_feature_version`

**Priority:** CRITICAL (compliance requirement)  
**Estimated Effort:** 1-2 days  
**Task Spec:** See dev-docs/analysis/phase-4.5-db-schema-sync-to-design-plan.md Task #6  
**Design Authority:** dev-docs/db-design/pilot-db-schema-v2.6h.json  
**Analysis Reference:** dev-docs/analysis/db-schema-vs-design/db-schema-dump-vs-design-analysis-v1.0.md Section 1

## Requirements

### 1. Documentation Standards
- **Active roadmap:** `dev-docs/analysis/phase-4.5-db-schema-sync-to-design-plan.md` - ⭐ PRIMARY for Phase 4.5
- **Always reference authoritative design docs:**
  - `dev-docs/db-design/pilot-db-schema-v2.6h.json` - **Golden Master** (source of truth)
  - `dev-docs/db-design/aevofab-db-process-v2.6h.md` - Database operations & schema
  - `dev-docs/analysis/db-schema-vs-design/db-schema-dump-vs-design-analysis-v1.0.md` - Gap analysis
  - `dev-docs/analysis/db-schema-vs-design/db-schema-sync-technical-instruction-v1.0.md` - Implementation guide
  - `dev-docs/architecture-design/mvp-arch.md` - System architecture
- **Create implementation notes** in roadmap as you work (inline documentation)
- **Update Phase 4.5 roadmap** when marking tasks complete

### 2. Testing Standards (CRITICAL FOR SCHEMA WORK)

**⚠️ ZERO FAILING TESTS POLICY:**
- **ALL tests MUST pass before marking task complete**
- **NO exceptions** - Database schema changes require 100% test pass rate
- If tests fail after implementation:
  1. **Fix immediately** (preferred for simple fixes)
  2. **Create detailed fix document** (for complex test issues)
     - Document ALL failing tests with concrete, actionable fixes
     - Mark task as "PARTIALLY COMPLETE" in roadmap
     - Include estimated time to fix each test

**Test Execution:**
- **Current Baseline:** (DO NOT regress these numbers)
  - 444/444 tests passing without integration tests
  - 471/471 tests passing with integration
- **Run existing tests first:**
  ```bash
  cd backend && source .venv/bin/activate
  pytest tests/ --ignore=tests/integration/ -v
  ```
- **Run schema sync tests:**
  ```bash
  pytest tests/test_schema_sync_v2_6h.py tests/test_database_triggers.py -v
  ```
- **All existing tests must pass** - Baseline must not regress
- **All new tests must pass** - No failing tests allowed

**Test Development for Audit Triggers:**
- **BEFORE writing tests:** Review `backend/tests/conftest.py` for existing fixtures
- **Create new test file:** `backend/tests/test_audit_trigger_coverage.py`
- **Test coverage required:**
  - For each critical table, verify:
    1. INSERT creates audit event
    2. UPDATE creates audit event with old/new values
    3. DELETE creates audit event
  - Test tenant isolation (user A cannot see user B's audit events)
  - Verify audit events contain correct metadata (table_name, operation, actor_id, tenant_id)
  - Verify JSON change payload structure (old_values, new_values)

### 3. Code Standards
- **Follow existing patterns** - Check similar implementations first (see existing audit triggers on 12 tables)
- **Type hints required** - All functions/methods must have type hints
- **Error handling** - Database errors must be caught and logged
- **Docstrings required** - Document all functions/classes/triggers
- **No feature creep** - Strictly follow Golden Master v2.6h specification

### 4. Database Standards (CRITICAL FOR PHASE 4.5)

**Golden Master Compliance:**
- **DO NOT deviate from `pilot-db-schema-v2.6h.json`** - It is the source of truth
- **Trigger naming convention:**
  - Pattern: `trg_[table]_audit_changes`
  - Example: `trg_user_audit_changes`, `trg_tenant_audit_changes`
- **Trigger timing:** AFTER INSERT OR UPDATE OR DELETE
- **Trigger level:** FOR EACH ROW
- **Function:** `audit.log_changes()` (already exists from Phase 4, Task 20)

**Migration Standards:**
- **Use database introspection** to find all tables requiring audit triggers
- **Exclude system tables** (alembic_version, pg_*, information_schema)
- **Group triggers logically** in migration (by criticality: CRITICAL → HIGH → MEDIUM)
- **No downtime** - Trigger creation is non-blocking operation
- **Post-migration verification** - Query all triggers to confirm coverage
- **Rollback testing** - Test downgrade migration before committing

### 5. Workflow

1. **Read the Phase 4.5 roadmap** to understand the task requirements
2. **Identify all missing tables:**
   ```sql
   -- Query to find tables without audit triggers
   SELECT t.tablename
   FROM pg_tables t
   LEFT JOIN pg_trigger tr ON tr.tgrelid = (t.schemaname || '.' || t.tablename)::regclass
     AND tr.tgname LIKE '%audit%'
   WHERE t.schemaname = 'public'
     AND tr.tgname IS NULL
     AND t.tablename NOT LIKE 'alembic%'
   ORDER BY t.tablename;
   ```
3. **Review existing audit triggers:**
   ```sql
   SELECT 
     tgrelid::regclass AS table_name,
     tgname AS trigger_name,
     proname AS function_name
   FROM pg_trigger t
   JOIN pg_proc p ON t.tgfoid = p.oid
   WHERE tgname LIKE '%audit%'
   ORDER BY table_name;
   ```
4. **Create Alembic migration:**
   ```bash
   cd backend
   source .venv/bin/activate
   alembic revision -m "add_missing_audit_triggers"
   ```
5. **Write migration SQL:**
   - Generate CREATE TRIGGER statements for all missing tables
   - Group by criticality (CRITICAL → HIGH → MEDIUM → LOW)
   - Use consistent naming: `trg_[table]_audit_changes`
6. **Test migration:**
   ```bash
   alembic upgrade head  # Apply
   alembic downgrade -1  # Rollback
   alembic upgrade head  # Re-apply
   ```
7. **Verify trigger coverage:**
   ```sql
   -- Verify all critical tables have audit triggers
   SELECT 
     t.tablename,
     tr.tgname AS audit_trigger
   FROM pg_tables t
   LEFT JOIN pg_trigger tr ON tr.tgrelid = (t.schemaname || '.' || t.tablename)::regclass
     AND tr.tgname LIKE '%audit%'
   WHERE t.schemaname = 'public'
     AND t.tablename IN ('user', 'tenant', 'change_order', 'subscription', 'product_plan', 'supplier', 'payment_method', 'app_service')
   ORDER BY t.tablename;
   -- All rows should have audit_trigger populated
   ```
8. **Write comprehensive tests** in `test_audit_trigger_coverage.py`
9. **Run all tests** - Must pass before completion
10. **Update Phase 4.5 roadmap:**
    - Check off deliverables: `- [x] Deliverable description`
    - Add status: `**Status:** ✅ COMPLETE (2026-MM-DD)`
    - Add test results: `**Test Results:** X/X passing`
    - Add implementation summary (migration file, trigger count, verification results)

## Key Files to Review

### Golden Master & Analysis
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - **Source of truth**
- `dev-docs/analysis/phase-4.5-db-schema-sync-to-design-plan.md` - **Active roadmap**
- `dev-docs/analysis/db-schema-vs-design/db-schema-dump-vs-design-analysis-v1.0.md` - Gap analysis

### Backend Code
- `backend/app/models/system.py` - AuditEvent model and `audit.log_changes()` function
- `backend/migrations/versions/` - Alembic migrations
- `backend/tests/test_audit_logging.py` - Existing audit tests (Phase 4, Task 20)
- `backend/tests/test_database_triggers.py` - Trigger tests

### Recent Schema Work (March 30-31, 2026)
- **Audit System Creation:** Phase 4, Task 20 (created `audit.log_changes()` function and AuditEvent model)
- **Existing Audit Triggers:** 12 tables already have audit triggers (customer, invoice, job, quote, payment, site, contact, address, job_time_entry, job_expense, supplier_item, pricebook_item)
- **Database Trigger Functions:** `2026_03_31_1850-6b525454c89c_add_missing_plpgsql_functions.py`

## Success Criteria

**MUST COMPLETE ALL BEFORE MARKING TASK AS COMPLETE:**

### Deliverables

- [ ] **Generate Missing Trigger Statements:**
  ```sql
  -- Example for user table
  CREATE TRIGGER trg_user_audit_changes
  AFTER INSERT OR UPDATE OR DELETE ON "user"
  FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
  
  -- Example for tenant table
  CREATE TRIGGER trg_tenant_audit_changes
  AFTER INSERT OR UPDATE OR DELETE ON tenant
  FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
  
  -- Repeat for all missing critical tables (~30 tables)
  ```

- [ ] **Create Migration:**
  - Filename: `2026_03_XX_XXXX-add_missing_audit_triggers.py`
  - Add ~30 CREATE TRIGGER statements
  - Group triggers by criticality (CRITICAL → HIGH → MEDIUM)
  - Include comprehensive downgrade logic (DROP TRIGGER statements)

- [ ] **Verification Script:**
  ```sql
  -- Query to find tables without audit triggers
  SELECT t.tablename
  FROM pg_tables t
  LEFT JOIN pg_trigger tr ON tr.tgrelid = (t.schemaname || '.' || t.tablename)::regclass
    AND tr.tgname LIKE '%audit%'
  WHERE t.schemaname = 'public'
    AND tr.tgname IS NULL
    AND t.tablename NOT LIKE 'alembic%'
  ORDER BY t.tablename;
  -- Should return minimal results after migration (only reference/lookup tables without audit needs)
  ```

- [ ] **Test Coverage:**
  - Create `backend/tests/test_audit_trigger_coverage.py`
  - For each critical table, verify:
    1. INSERT creates audit event
    2. UPDATE creates audit event with old/new values
    3. DELETE creates audit event
  - Test tenant isolation (user A cannot see user B's audit events)
  - Test audit event structure (table_name, operation, actor_id, tenant_id, change_payload)

### Database Verification

- [ ] **All critical tables have audit triggers:**
  ```sql
  -- Verify user table
  SELECT tgname FROM pg_trigger 
  WHERE tgrelid = '"user"'::regclass AND tgname LIKE '%audit%';
  -- Should return: trg_user_audit_changes
  
  -- Verify tenant table
  SELECT tgname FROM pg_trigger 
  WHERE tgrelid = 'tenant'::regclass AND tgname LIKE '%audit%';
  -- Should return: trg_tenant_audit_changes
  
  -- Verify change_order table
  SELECT tgname FROM pg_trigger 
  WHERE tgrelid = 'change_order'::regclass AND tgname LIKE '%audit%';
  -- Should return: trg_change_order_audit_changes
  ```

- [ ] **Trigger count verification:**
  ```sql
  -- Count all audit triggers
  SELECT COUNT(*) AS audit_trigger_count
  FROM pg_trigger
  WHERE tgname LIKE '%audit%';
  -- Should show: ~42 triggers (12 existing + ~30 new)
  ```

### Testing

- [ ] Alembic migration created and tested (upgrade + downgrade)
- [ ] Migration applied successfully to local database
- [ ] **ALL existing tests pass** (444/444 baseline maintained without integration, 471/471 with integration)
- [ ] **ALL new tests pass** (expect ~30 new tests for audit trigger coverage)
- [ ] **Test pass rate: 100%** (X/X passing, 0 failing)
- [ ] Phase 4.5 roadmap updated with completion status

### Functional Verification

- [ ] Editing `user` record creates audit event
- [ ] Changing `subscription` tier logs to audit trail
- [ ] Deleting `change_order` preserves audit history
- [ ] Audit events contain correct metadata (table_name, operation, actor_id, tenant_id)
- [ ] Audit change payload has old_values and new_values
- [ ] Tenant isolation enforced (users only see their tenant's audit events)
- [ ] No critical table omissions (verified by query)

**Task Status in Roadmap:**
- ✅ **COMPLETE** - If all tests pass (implementation + tests 100% complete)
- 🟡 **PARTIALLY COMPLETE** - If fix document created for failing tests
  - Must include: "Implementation complete, tests require fixes (see test_audit_trigger_coverage_fixes.md)"
  - Cannot mark COMPLETE until all tests pass

**If Tests Fail:**
- Create `dev-docs/testing-support/task-db-sync-06-test-fixes.md` with concrete fixes
- Update task status to "🟡 PARTIALLY COMPLETE" in Phase 4.5 roadmap
- Document exact steps to achieve 100% test pass rate
- Include time estimates for each fix

## Implementation Details

### Tables Requiring Audit Triggers

**CRITICAL Priority (Must Have):**
1. **`user`** - User account changes (security audit)
2. **`tenant`** - Tenant configuration changes (compliance)
3. **`change_order`** - Scope change approvals (legal protection)
4. **`subscription`** - Billing tier changes (revenue audit)
5. **`product_plan`** - SaaS pricing changes (contract compliance)

**HIGH Priority:**
6. **`supplier`** - Supplier master data (procurement audit)
7. **`payment_method`** - Payment instrument changes (PCI compliance)
8. **`app_service`** - Service configuration (debugging)
9. **`tenant_markup_version`** - Markup pricing history
10. **`supplier_item_price`** - Supplier price history
11. **`tax_rate_version`** - Tax rate history
12. **`pricebook_item_version`** - Pricebook history
13. **`product_plan_version`** - SaaS plan history
14. **`product_plan_product_feature_version`** - Feature history

**MEDIUM Priority (Additional Tables - Identify via Query):**
- Use the verification query to find all remaining tables without audit triggers
- Exclude system tables (alembic_version, pg_*, information_schema)
- Exclude pure reference/lookup tables if appropriate (discuss with architect)

### Trigger Template

```sql
-- Standard audit trigger pattern
CREATE TRIGGER trg_[table_name]_audit_changes
AFTER INSERT OR UPDATE OR DELETE ON [table_name]
FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
```

### Migration Structure

```python
"""add_missing_audit_triggers

Revision ID: [generated]
Revises: [previous_revision]
Create Date: 2026-03-XX XX:XX:XX.XXXXXX

"""
from alembic import op

# revision identifiers
revision = '[generated]'
down_revision = '[previous_revision]'
branch_labels = None
depends_on = None


def upgrade():
    # CRITICAL PRIORITY TABLES
    op.execute("""
        CREATE TRIGGER trg_user_audit_changes
        AFTER INSERT OR UPDATE OR DELETE ON "user"
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)
    
    op.execute("""
        CREATE TRIGGER trg_tenant_audit_changes
        AFTER INSERT OR UPDATE OR DELETE ON tenant
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)
    
    # ... repeat for all critical tables
    
    # HIGH PRIORITY TABLES
    # ... repeat for high priority tables
    
    # MEDIUM PRIORITY TABLES
    # ... repeat for medium priority tables


def downgrade():
    # Drop all triggers in reverse order
    op.execute("DROP TRIGGER IF EXISTS trg_user_audit_changes ON \"user\";")
    op.execute("DROP TRIGGER IF EXISTS trg_tenant_audit_changes ON tenant;")
    # ... repeat for all tables
```

### Test Structure

```python
# backend/tests/test_audit_trigger_coverage.py
"""
Test audit trigger coverage for all critical tables.
Ensures comprehensive change history tracking for compliance and security.
"""
import pytest
from sqlmodel import select
from backend.app.models.system import AuditEvent
from backend.app.models.core import User
from backend.app.models.crm import Tenant
# ... import other models

class TestUserAuditTrigger:
    """Test audit logging for user table."""
    
    def test_insert_creates_audit_event(self, db_session, test_tenant):
        """Inserting a user should create an INSERT audit event."""
        # Create user
        user = User(...)
        db_session.add(user)
        db_session.commit()
        
        # Verify audit event
        audit_event = db_session.exec(
            select(AuditEvent)
            .where(AuditEvent.table_name == "user")
            .where(AuditEvent.operation == "INSERT")
            .where(AuditEvent.row_id == user.id)
        ).first()
        
        assert audit_event is not None
        assert audit_event.table_name == "user"
        assert audit_event.operation == "INSERT"
    
    def test_update_creates_audit_event(self, db_session, test_user):
        """Updating a user should create an UPDATE audit event with old/new values."""
        # Update user
        old_email = test_user.email
        test_user.email = "newemail@example.com"
        db_session.add(test_user)
        db_session.commit()
        
        # Verify audit event
        audit_event = db_session.exec(
            select(AuditEvent)
            .where(AuditEvent.table_name == "user")
            .where(AuditEvent.operation == "UPDATE")
            .where(AuditEvent.row_id == test_user.id)
        ).first()
        
        assert audit_event is not None
        assert old_email in str(audit_event.change_payload)
        assert "newemail@example.com" in str(audit_event.change_payload)
    
    def test_delete_creates_audit_event(self, db_session, test_user):
        """Deleting a user should create a DELETE audit event."""
        user_id = test_user.id
        db_session.delete(test_user)
        db_session.commit()
        
        # Verify audit event
        audit_event = db_session.exec(
            select(AuditEvent)
            .where(AuditEvent.table_name == "user")
            .where(AuditEvent.operation == "DELETE")
            .where(AuditEvent.row_id == user_id)
        ).first()
        
        assert audit_event is not None


class TestTenantAuditTrigger:
    """Test audit logging for tenant table."""
    # Similar structure to TestUserAuditTrigger

# ... repeat for all critical tables
```

## Questions to Ask

Before starting:
1. Have I identified all tables requiring audit triggers?
2. Have I reviewed the existing `audit.log_changes()` function from Phase 4, Task 20?
3. Do I understand the audit event structure and change payload format?
4. What tests currently verify audit logging for the 12 existing tables?

During implementation:
1. Am I following the naming convention `trg_[table]_audit_changes`?
2. Have I grouped triggers by priority (CRITICAL → HIGH → MEDIUM)?
3. Have I excluded system tables from audit coverage?
4. Are ALL tests passing (100% pass rate)?
5. Have I verified triggers exist on all critical tables?

After implementation:
1. Do I have 100% test pass rate (X/X passing, 0 failing)?
2. Have I verified all critical tables have audit triggers?
3. Can I insert/update/delete records and see audit events created?
4. Are audit events properly isolated by tenant_id?
5. Have I updated the Phase 4.5 roadmap with completion status?

## Example Task Flow

```bash
# ============================================================================
# Phase 4.5 Task 6: Audit Trigger Coverage
# ============================================================================

# 1. Review the task in Phase 4.5 roadmap
cat dev-docs/analysis/phase-4.5-db-schema-sync-to-design-plan.md | grep -A 80 "Task 6:"

# 2. Check existing audit triggers
cd backend
source .venv/bin/activate
psql -d pilot_dev -c "
  SELECT 
    tgrelid::regclass AS table_name,
    tgname AS trigger_name,
    proname AS function_name
  FROM pg_trigger t
  JOIN pg_proc p ON t.tgfoid = p.oid
  WHERE tgname LIKE '%audit%'
  ORDER BY table_name;
"
# Should show: 12 tables with audit triggers

# 3. Find tables WITHOUT audit triggers
psql -d pilot_dev -c "
  SELECT t.tablename
  FROM pg_tables t
  LEFT JOIN pg_trigger tr ON tr.tgrelid = (t.schemaname || '.' || t.tablename)::regclass
    AND tr.tgname LIKE '%audit%'
  WHERE t.schemaname = 'public'
    AND tr.tgname IS NULL
    AND t.tablename NOT LIKE 'alembic%'
  ORDER BY t.tablename;
"

# 4. Create migration
alembic revision -m "add_missing_audit_triggers"

# 5. Edit migration file to add CREATE TRIGGER statements
# [Edit migration file with ~30 CREATE TRIGGER statements]

# 6. Test migration upgrade
alembic upgrade head

# 7. Verify trigger count
psql -d pilot_dev -c "
  SELECT COUNT(*) AS audit_trigger_count
  FROM pg_trigger
  WHERE tgname LIKE '%audit%';
"
# Should show: ~42 triggers (12 existing + ~30 new)

# 8. Verify critical tables have audit triggers
psql -d pilot_dev -c "
  SELECT 
    t.tablename,
    tr.tgname AS audit_trigger
  FROM pg_tables t
  LEFT JOIN pg_trigger tr ON tr.tgrelid = (t.schemaname || '.' || t.tablename)::regclass
    AND tr.tgname LIKE '%audit%'
  WHERE t.schemaname = 'public'
    AND t.tablename IN ('user', 'tenant', 'change_order', 'subscription', 'product_plan')
  ORDER BY t.tablename;
"
# All rows should have audit_trigger populated

# 9. Test migration downgrade
alembic downgrade -1

# 10. Verify triggers removed
psql -d pilot_dev -c "SELECT COUNT(*) FROM pg_trigger WHERE tgname LIKE '%audit%';"
# Should show: 12 (back to baseline)

# 11. Re-apply migration
alembic upgrade head

# 12. Create comprehensive test suite
# [Create backend/tests/test_audit_trigger_coverage.py]

# 13. Run baseline tests (expect 444 tests without integration)
pytest tests/ --ignore=tests/integration/ -v 2>&1 | grep -E "(passed|failed|===)" | tail -5

# 14. Run new audit coverage tests
pytest tests/test_audit_trigger_coverage.py -v

# 15. Run ALL tests including integration (expect 471+ tests)
pytest tests/ -v

# 16. Test functional audit logging manually
psql -d pilot_dev -c "
  -- Insert a user
  INSERT INTO \"user\" (id, email, tenant_id, created_at, updated_at)
  VALUES (gen_random_uuid(), 'test@example.com', (SELECT id FROM tenant LIMIT 1), NOW(), NOW());
  
  -- Check audit event
  SELECT * FROM audit.event WHERE table_name = 'user' ORDER BY occurred_at DESC LIMIT 1;
"

# 17. Update Phase 4.5 roadmap
# [Edit phase-4.5-db-schema-sync-to-design-plan.md]
# - [x] Generate Missing Trigger Statements
# - [x] Create Migration
# - [x] Verification Script
# - [x] Test Coverage
# **Status:** ✅ COMPLETE (2026-04-XX)
# **Test Results:** XXX/XXX passing (444 baseline + ~30 new audit tests, 100%)
```

## Notes

- **Audit Function Already Exists:** `audit.log_changes()` was created in Phase 4, Task 20
- **12 Tables Already Have Triggers:** customer, invoice, job, quote, payment, site, contact, address, job_time_entry, job_expense, supplier_item, pricebook_item
- **~30 New Triggers Required:** Focus on CRITICAL and HIGH priority tables first
- **No Schema Changes:** This is pure trigger addition, no table/column changes
- **Non-Blocking Operation:** Trigger creation doesn't lock tables or require downtime
- **Compliance Requirement:** Audit trail coverage is CRITICAL for security, compliance, and legal protection
- **Tenant Isolation:** Audit events are automatically isolated by tenant_id in the `audit.log_changes()` function
- **Performance Impact:** AFTER triggers have minimal performance impact (async audit writing)

## Schema Synchronization Context

**Phase 2: Functions & Triggers (Current Phase)**
- ✅ Task 4: Missing PL/pgSQL Functions (3 functions + 200 triggers) - COMPLETE
- ✅ Task 5: Function Naming Standard Compliance - COMPLETE
- 🔴 **Task 6: Audit Trigger Coverage (30+ tables)** - THIS TASK
- 🟡 Task 7: Operational Trigger Verification - PARTIALLY COMPLETE

**Remaining Phase 2 Work:**
- Task 6 (this task) - Add audit triggers to ~30 critical tables
- Task 7 (final) - Document trigger inventory and verify operational triggers
```

---

## Usage

1. Start this task with the `MVP Builder` custom Roo Code mode
2. Copy the prompt section above to begin
3. The AI will have full context and standards from Golden Master v2.6h
4. When finished, the AI will update the Phase 4.5 roadmap with completion status
