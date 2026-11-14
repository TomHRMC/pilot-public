# Phase 4.5 Task Prompt
## Phase 1, Task #3 - QuickBooks Identity Rule (Customer Table)

Task: Phase 1, Task #3 - QuickBooks Identity Rule (Customer Table)
Reference: dev-docs/analysis/phase-4.5-db-schema-sync-to-design-plan.md Task 3 (Lines 268-288)
(Analysis: Section 1 - QuickBooks Identity Rule in db-schema-dump-vs-design-analysis-v1.0.md)

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
- ✅ Task 1: Timezone Enforcement (9 violations) - March 30, 2026
- ✅ Task 2: Citext Conversion for User Email - March 31, 2026
- **Current Status:** 455/455 tests passing (100% pass rate) including 448 with integration tests + 7 new citext tests
- **Remaining Work:** 11 tasks across 4 phases

**Test Coverage:** 455/455 passing (100% pass rate) (includes: 421 baseline tests, 27 integration tests, 7 citext tests)
**See:** dev-docs/analysis/phase-4.5-db-schema-sync-to-design-plan.md for full details

## Current Task

**Add QuickBooks Identity Rule to Prevent Duplicate Customer Names**

QuickBooks Online enforces a business rule that customer names must be unique within a company. AevoFab must enforce the same rule at the database level to prevent sync conflicts when pushing customers to QuickBooks.

**Why This Matters:**
- **QuickBooks Sync Failures:** Attempting to sync duplicate customer names will fail
- **Data Quality:** Prevents confusion between customers with identical names
- **Business Logic:** Mirrors QuickBooks constraint for consistency
- **Multi-tenant Safety:** Different tenants can have the same customer name (isolation maintained)

**Priority:** HIGH  
**Estimated Effort:** 0.5-1 day  
**Task Spec:** See dev-docs/analysis/phase-4.5-db-schema-sync-to-design-plan.md Task #3 (Lines 268-288)  
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
  - 428/428 tests passing without integration tests (421 baseline + 7 citext)
  - 455/455 tests passing with integration (448 baseline + 7 citext)
- **Schema Sync Tests:** 37/37 passing (test_schema_sync_v2_6h.py, test_database_triggers.py, test_timezone_compliance.py, test_citext_email.py)
- **Run existing tests first:**
  ```bash
  cd backend && source .venv/bin/activate
  pytest tests/ --ignore=tests/integration/ -v
  ```
- **Run schema sync tests:**
  ```bash
  pytest tests/test_schema_sync_v2_6h.py tests/test_database_triggers.py tests/test_timezone_compliance.py tests/test_citext_email.py -v
  ```
- **All existing tests must pass** - Baseline must not regress
- **All new tests must pass** - No failing tests allowed

**Test Development for Schema Changes:**
- **BEFORE writing tests:** Review `backend/tests/conftest.py` for existing fixtures
- **Create new test file or add to existing:** `backend/tests/test_qb_identity_constraints.py`
- **Test coverage required:**
  - Duplicate customer name rejection within same tenant (IntegrityError)
  - Different tenants can have same customer name (success)
  - Case sensitivity testing (if applicable)
  - Pre-migration data cleanup validation
  - Constraint exists in database verification

### 3. Code Standards
- **Follow existing patterns** - Check similar implementations first
- **Type hints required** - All functions/methods must have type hints
- **Error handling** - Database errors must be caught and logged
- **Docstrings required** - Document all functions/classes/triggers
- **No feature creep** - Strictly follow Golden Master v2.6h specification

### 4. Database Standards (CRITICAL FOR PHASE 4.5)

**Golden Master Compliance:**
- **DO NOT deviate from `pilot-db-schema-v2.6h.json`** - It is the source of truth
- **Always read SQLModel files first** - Don't hallucinate existing schema
- **Use Alembic migrations** for ALL schema changes
- **Test migrations both ways** - Upgrade AND downgrade must work cleanly
- **Naming conventions:**
  - Constraints: `uq_[table]_[columns]` for UNIQUE (e.g., `uq_customer_tenant_display_name`)

**Migration Standards:**
- **Pre-migration validation** - Check for constraint violations in existing data
- **Post-migration verification** - Verify constraint was created successfully
- **Rollback testing** - Test downgrade migration before committing

**Unique Constraint Pattern:**
```python
# SQLModel: Add __table_args__ to model
from sqlalchemy import UniqueConstraint

class Customer(TenantIsolatedMixin, SQLModel, table=True):
    __tablename__ = "customer"
    __table_args__ = (
        UniqueConstraint('tenant_id', 'display_name', name='uq_customer_tenant_display_name'),
    )
```

```sql
-- Migration SQL:
ALTER TABLE customer 
ADD CONSTRAINT uq_customer_tenant_display_name 
UNIQUE (tenant_id, display_name);
```

### 5. Workflow

1. **Read the Phase 4.5 roadmap** to understand the task requirements
2. **Review Golden Master JSON** for exact specification
3. **Read technical instruction doc** for implementation patterns
4. **Check existing schema** - Read current Customer model in crm.py
5. **Pre-migration data validation** - Check for existing duplicates
6. **Implement SQLModel changes** - Add __table_args__ with UniqueConstraint
7. **Create Alembic migration:**
   ```bash
   cd backend
   source .venv/bin/activate
   alembic revision --autogenerate -m "add_qb_identity_constraints"
   ```
8. **Test migration:**
   ```bash
   alembic upgrade head  # Apply
   alembic downgrade -1  # Rollback
   alembic upgrade head  # Re-apply
   ```
9. **Write tests** - Test constraint enforcement, multi-tenant isolation
10. **Run all tests** - Must pass before completion
11. **Update Phase 4.5 roadmap:**
    - Check off deliverables: `- [x] Deliverable description`
    - Add status: `**Status:** ✅ COMPLETE (2026-MM-DD)`
    - Add test results: `**Test Results:** X/X passing`
    - Add implementation summary (files modified, SQL snippets, etc.)

## Key Files to Review

### Golden Master & Analysis
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - **Source of truth**
- `dev-docs/analysis/phase-4.5-db-schema-sync-to-design-plan.md` - **Active roadmap** (Lines 268-288 for Task 3)
- `dev-docs/analysis/db-schema-vs-design/db-schema-dump-vs-design-analysis-v1.0.md` - Gap analysis
- `dev-docs/analysis/db-schema-vs-design/db-schema-sync-technical-instruction-v1.0.md` - Implementation guide

### Backend Code (Files to Modify)
1. `backend/app/models/crm.py` - Customer model
   - Add `__table_args__` with UniqueConstraint
   - Ensure proper imports: `from sqlalchemy import UniqueConstraint`

### Test Files
- `backend/tests/conftest.py` - Existing fixtures
- `backend/tests/test_schema_sync_v2_6h.py` - Schema sync test suite
- **NEW or EXISTING:** `backend/tests/test_qb_identity_constraints.py` - Create or add to this file

### Recent Schema Work (Reference Patterns)
- **Gap 1 Implementation:** `2026_03_30_1810-6907731fd637_sync_with_golden_master_v2_6h.py` - ContactPortalInvite UNIQUE constraint (similar pattern)
- **Task 1 Implementation:** `2026_03_30_2129-cf20e60ce5f3_fix_timezone_violations_task1.py` - Timezone fixes
- **Task 2 Implementation:** `2026_03_31_1733-c748980dbeee_convert_user_email_to_citext.py` - Citext conversion with duplicate detection

## Success Criteria

**MUST COMPLETE ALL BEFORE MARKING TASK AS COMPLETE:**

### Deliverables (from Roadmap)

- [ ] **SQLModel Update:**
  - [ ] File: `backend/app/models/crm.py`
  - [ ] Add `__table_args__` to Customer model with UniqueConstraint
  
  **Required Pattern:**
  ```python
  from sqlalchemy import UniqueConstraint
  
  class Customer(TenantIsolatedMixin, SQLModel, table=True):
      __tablename__ = "customer"
      __table_args__ = (
          UniqueConstraint('tenant_id', 'display_name', name='uq_customer_tenant_display_name'),
      )
      # ... existing fields ...
  ```

- [ ] **Alembic Migration:**
  - [ ] Create migration: `alembic revision --autogenerate -m "add_qb_identity_constraints"`
  - [ ] Review autogenerated SQL (should add UNIQUE constraint)
  - [ ] Add pre-migration duplicate detection if needed
  - [ ] Test upgrade: `alembic upgrade head`
  - [ ] Test downgrade: `alembic downgrade -1`
  - [ ] Re-apply: `alembic upgrade head`
  
  **SQL Pattern:**
  ```sql
  -- Upgrade:
  ALTER TABLE customer 
  ADD CONSTRAINT uq_customer_tenant_display_name 
  UNIQUE (tenant_id, display_name);
  
  -- Downgrade:
  ALTER TABLE customer 
  DROP CONSTRAINT uq_customer_tenant_display_name;
  ```

- [ ] **Pre-Migration Data Validation:**
  ```sql
  -- Check for existing duplicate customer names within same tenant
  SELECT tenant_id, display_name, COUNT(*) as dup_count
  FROM customer
  GROUP BY tenant_id, display_name
  HAVING COUNT(*) > 1
  ORDER BY dup_count DESC;
  
  -- If duplicates exist, they must be manually resolved before migration
  ```

- [ ] **Post-Migration Verification:**
  ```sql
  -- Verify constraint exists
  SELECT conname, contype 
  FROM pg_constraint 
  WHERE conrelid = 'customer'::regclass 
    AND contype = 'u'
    AND conname = 'uq_customer_tenant_display_name';
  -- Should return: uq_customer_tenant_display_name | u
  ```

- [ ] **Test Coverage:**
  - [ ] Create or add to `backend/tests/test_qb_identity_constraints.py`
  - [ ] Test 1: `test_customer_duplicate_name_same_tenant_rejected`
    - Create customer with name "ABC Electric"
    - Attempt to create another customer with same name in same tenant
    - Verify IntegrityError raised
  - [ ] Test 2: `test_customer_duplicate_name_different_tenant_allowed`
    - Create customer "ABC Electric" in Tenant A
    - Create customer "ABC Electric" in Tenant B
    - Verify both succeed (tenant isolation maintained)
  - [ ] Test 3: `test_customer_constraint_exists`
    - Query pg_constraint to verify constraint exists
    - Verify constraint name is `uq_customer_tenant_display_name`
  - [ ] Test 4: `test_customer_name_case_sensitivity` (if applicable)
    - Test if "ABC Electric" vs "abc electric" are considered duplicates
    - Document expected behavior

### Success Verification

- [ ] Customer model has `__table_args__` with UniqueConstraint
- [ ] Database constraint `uq_customer_tenant_display_name` exists
- [ ] Attempting to create duplicate customer name in same tenant raises IntegrityError
- [ ] Different tenants can have same customer name (isolation works)
- [ ] No existing duplicate customer names (pre-migration cleanup successful)
- [ ] **ALL existing tests pass** (455/455 baseline maintained)
- [ ] **ALL new tests pass** (3-4 new tests passing)
- [ ] **Test pass rate: 100%** (458-459/458-459 passing = 455 baseline + 3-4 new)
- [ ] Phase 4.5 roadmap updated with completion status
- [ ] Code follows Golden Master specification exactly

**Task Status in Roadmap:**
- ✅ **COMPLETE** - If all tests pass (implementation + tests 100% complete)
- 🟡 **PARTIALLY COMPLETE** - If fix document created for failing tests
  - Must include: "Implementation complete, tests require fixes (see test_qb_identity_constraints_fixes.md)"
  - Cannot mark COMPLETE until all tests pass

**If Tests Fail:**
- Create `dev-docs/testing-support/task-db-sync-03-test-fixes.md` with concrete fixes
- Update task status to "🟡 PARTIALLY COMPLETE" in Phase 4.5 roadmap
- Document exact steps to achieve 100% test pass rate
- Include time estimates for each fix

## Risk Assessment

- **Data Integrity Risk:** MEDIUM
  - Existing customers may have duplicate names within same tenant
  - **Mitigation:** Run pre-migration duplicate detection query
  - **Action:** Manually resolve duplicates before applying constraint
  
- **QuickBooks Sync Impact:** LOW
  - Constraint aligns with QuickBooks business rules
  - Prevents future sync failures
  
- **Downtime Required:** None
  - ADD CONSTRAINT is online operation in PostgreSQL 12+
  - No table locks required for this size constraint
  
- **Rollback Complexity:** LOW
  - Straightforward DROP CONSTRAINT in downgrade migration
  - No data loss on rollback

## Questions to Ask

Before starting:
1. Have I read the Golden Master JSON for the Customer table constraint?
2. Have I reviewed the gap analysis to understand WHY this change is needed?
3. Do I understand the QuickBooks identity rule this enforces?
4. What existing code can I reference for similar patterns? (Check Gap 1: ContactPortalInvite UNIQUE constraint)
5. Are there existing duplicate customer names in the database?

During implementation:
1. Am I following the Golden Master specification exactly?
2. Have I checked for existing duplicate customer names?
3. Have I tested the migration in both directions (upgrade + downgrade)?
4. Are ALL tests passing (100% pass rate)?
5. Does this constraint maintain tenant isolation?

After implementation:
1. Do I have 100% test pass rate (458-459/458-459 passing)?
2. If tests fail, have I created a detailed fix document?
3. Have I marked the task status correctly (COMPLETE vs PARTIALLY COMPLETE)?
4. Can duplicate customer names be created in different tenants?
5. Does the migration rollback cleanly without errors?

## Example Task Flow

```bash
# ============================================================================
# Phase 4.5 Task 3 Execution
# ============================================================================

# 1. Review the task in Phase 4.5 roadmap
cat dev-docs/analysis/phase-4.5-db-schema-sync-to-design-plan.md | grep -A 20 "Task 3:"

# 2. Review Golden Master specification for Customer table
cat dev-docs/db-design/pilot-db-schema-v2.6h.json | jq '.tables[] | select(.name == "customer")'

# 3. Check current Customer model
cd backend
source .venv/bin/activate
python -c "from app.models.crm import Customer; import inspect; print(inspect.getsource(Customer))"

# 4. Check for existing duplicate customer names
psql -d pilot_dev -c "
SELECT tenant_id, display_name, COUNT(*) as dup_count
FROM customer
GROUP BY tenant_id, display_name
HAVING COUNT(*) > 1
ORDER BY dup_count DESC;
"
# Expected: 0 rows (no duplicates)

# 5. Update Customer model
# [Edit backend/app/models/crm.py - Add __table_args__ with UniqueConstraint]

# 6. Create migration
alembic revision --autogenerate -m "add_qb_identity_constraints"

# 7. Review migration file
# [Verify ALTER TABLE ADD CONSTRAINT statement is correct]

# 8. Test migration upgrade
alembic upgrade head

# 9. Verify constraint exists
psql -d pilot_dev -c "
SELECT conname, contype 
FROM pg_constraint 
WHERE conrelid = 'customer'::regclass 
  AND contype = 'u'
  AND conname = 'uq_customer_tenant_display_name';
"
# Expected: uq_customer_tenant_display_name | u

# 10. Test migration downgrade
alembic downgrade -1

# 11. Verify constraint removed
psql -d pilot_dev -c "
SELECT conname 
FROM pg_constraint 
WHERE conrelid = 'customer'::regclass 
  AND conname = 'uq_customer_tenant_display_name';
"
# Expected: 0 rows

# 12. Re-apply migration
alembic upgrade head

# 13. Run baseline tests (expect 428/428)
pytest tests/ --ignore=tests/integration/ -v 2>&1 | grep -E "(passed|failed|===)" | tail -5

# 14. Run schema sync tests (expect 37/37)
pytest tests/test_schema_sync_v2_6h.py tests/test_database_triggers.py tests/test_timezone_compliance.py tests/test_citext_email.py -v

# 15. Write new tests
# [Create or add to backend/tests/test_qb_identity_constraints.py]

# 16. Run all tests without integration (expect 431-432/431-432 = 428 baseline + 3-4 new)
pytest tests/ --ignore=tests/integration/ -v

# 17. If baseline tests pass, run ALL tests (expect 458-459/458-459 = 455 baseline + 3-4 new)
pytest tests/ -v

# 18. Update Phase 4.5 roadmap
# [Edit dev-docs/analysis/phase-4.5-db-schema-sync-to-design-plan.md]
# Mark Task 3 as complete:
# - [x] SQLModel update
# - [x] Alembic migration
# - [x] Pre-migration validation
# - [x] Post-migration verification
# - [x] Test coverage
# **Status:** ✅ COMPLETE (2026-03-31)
# **Test Results:**
# - Without integration: 431/431 passing (3 new tests added)
# - With integration: 458/458 passing (3 new tests added)
# **Migration:** 2026_03_31_XXXX-add_qb_identity_constraints.py
# **Files Modified:** backend/app/models/crm.py, 1 migration, 1 test file
```

## Notes

- **Golden Master is Law:** `pilot-db-schema-v2.6h.json` is the single source of truth
- **QuickBooks Rule:** This constraint mirrors QuickBooks Online's customer name uniqueness rule
- **Reference Implementation:** Check Gap 1 (ContactPortalInvite UNIQUE constraint) for similar pattern
- **Tenant Isolation:** Constraint is scoped to tenant_id, so different tenants can have same customer name
- **Data Safety:** Check for existing duplicates before applying constraint
- **Document Inline:** Update Phase 4.5 roadmap as you work (don't wait until end)
- **Migration Rollback:** MUST test downgrade migration (production safety)
- **No Feature Creep:** Only implement what Golden Master specifies

## Related Tasks

**Completed (Reference for Patterns):**
- ✅ Gap 1: ContactPortalInvite UNIQUE constraint (March 30, 2026)
  - File: `2026_03_30_1810-6907731fd637_sync_with_golden_master_v2_6h.py`
  - Pattern to follow for UNIQUE constraint implementation
- ✅ Task 2: Citext Conversion (March 31, 2026)
  - File: `2026_03_31_1733-c748980dbeee_convert_user_email_to_citext.py`
  - Pattern for pre-migration duplicate detection

**Next Task After Completion:**
- Task 4: Missing PL/pgSQL Functions (2 days, CRITICAL priority)
- Blocked by: None (can start immediately after Task 3)

## Schema Synchronization Phases

**Phase 1: Foundation (Data Types & Columns)** - CRITICAL
- ✅ Task 1: Fix timezone violations (9 columns) - COMPLETE
- ✅ Task 2: Convert user email to citext - COMPLETE
- **Task 3: QuickBooks identity rules** ← YOU ARE HERE

**Phase 2: Functions & Triggers** - CRITICAL
- Task 4: Implement 3 missing PL/pgSQL functions
- Task 5: Rename functions to follow _fn standard
- Task 6: Add audit triggers to 30+ tables
- Task 7: Verify operational trigger inventory

**Phase 3: Data Integrity (Constraints)** - HIGH
- Task 8: Add 4 unique constraints
- Task 9: Add extensive CHECK constraints
- Task 10: Add 6 temporal GIST exclusion constraints

**Phase 4: Advanced Indexing** - MEDIUM
- Task 11: Add 2 partial indexes (performance)
- Task 12: Add 2 partial unique indexes
- Task 13: Add 2 HNSW vector indexes (Voice AI)

---

## Usage

1. Start this task with the `MVP Builder` custom Roo Code mode
2. Copy this entire prompt to begin Task 3
3. When finished, the AI will update the Phase 4.5 roadmap with completion status
4. The AI will have full context and standards from Golden Master v2.6h
5. Expected completion: 458-459/458-459 tests passing (455 baseline + 3-4 new constraint tests)
