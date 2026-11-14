# Phase 4.5 Task Prompt
## Phase 1, Task #1 - Timezone Enforcement (9 Violations)

Task: Phase 1, Task #1 - Timezone Enforcement (9 Violations)
Reference: dev-docs/analysis/phase-4.5-db-schema-sync-to-design-plan.md Task 1
(Analysis: Section 1 - Global Rule Violations in db-schema-dump-vs-design-analysis-v1.0.md)

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
- **Current Status:** 30/30 schema sync tests passing (100%)
- **Remaining Work:** 13 tasks across 4 phases

**Test Coverage:** 439/439 passing (100% pass rate) (includes: 412 regular tests, 27 integration tests)
**See:** dev-docs/analysis/phase-4.5-db-schema-sync-to-design-plan.md for full details

## Current Task

**Fix 9 Timezone Violations to Enforce v2.0 "Double-Lock" Standard**

The v2.0 "Double-Lock" standard mandates that **ALL datetime fields** use `timestamp with time zone` (TIMESTAMPTZ). This task addresses 9 columns that currently violate this rule by using `timestamp without time zone`.

**Why This Matters:**
- **Financial disputes:** Invoice timestamps in wrong timezone
- **Audit trail corruption:** Events recorded in server local time
- **QuickBooks sync failures:** Timestamp mismatch between systems
- **Compliance risk:** Legal/regulatory requirement for accurate timestamps

**Priority:** CRITICAL  
**Estimated Effort:** 1-2 days  
**Task Spec:** See dev-docs/analysis/phase-4.5-db-schema-sync-to-design-plan.md Task #1 (Lines 83-150)  
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
  - 412/412 tests passing without integration tests
  - 439/439 tests passing with integration
- **Schema Sync Tests:** 30/30 passing (test_schema_sync_v2_6h.py, test_database_triggers.py)
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

**Test Development for Schema Changes:**
- **BEFORE writing tests:** Review `backend/tests/conftest.py` for existing fixtures
- **Create new test file:** `backend/tests/test_timezone_compliance.py`
- **Test coverage required:**
  - Verify each column has `tzinfo` set after retrieval
  - Test that datetime values round-trip with timezone preservation
  - Validate data migration didn't corrupt existing timestamps
  - Test edge cases (NULL values, epoch timestamps, far future dates)

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
- **Respect timezone standard** - All datetime fields MUST be `timestamptz` (CRITICAL)
- **Naming conventions:**
  - Triggers: `trg_[table]_[action]` (e.g., `trg_user_set_updated_at`)
  - Functions: `[function_name]_fn` (e.g., `set_updated_at_fn`)
  - Indexes: `idx_[table]_[columns]` (e.g., `idx_invoice_balance`)
  - Constraints: `[table]_[field]_chk` (e.g., `customer_type_chk`)

**Migration Standards:**
- **Use `CONCURRENTLY` for indexes** - Prevents table locks
- **Pre-migration validation** - Check for constraint violations in existing data
- **Post-migration verification** - Verify constraint was created successfully
- **Rollback testing** - Test downgrade migration before committing

**Timezone Compliance (v2.0 "Double-Lock" Standard):**
```python
# Python: AwareDatetime type hint
from core.db import AwareDatetime

# SQLAlchemy: DateTime(timezone=True)
from sqlalchemy import Column, DateTime

field: AwareDatetime = Field(
    sa_column=Column(DateTime(timezone=True), nullable=False)
)

# Database: TIMESTAMPTZ
ALTER TABLE table_name 
  ALTER COLUMN field_name 
  TYPE timestamp with time zone 
  USING field_name AT TIME ZONE 'UTC';
```

### 5. Workflow

1. **Read the Phase 4.5 roadmap** to understand the task requirements
2. **Review Golden Master JSON** for exact specification
3. **Read technical instruction doc** for implementation patterns
4. **Check existing schema** - Read current SQLModel files and migrations
5. **Implement SQLModel changes** - Update models with timezone-aware fields
6. **Create Alembic migration:**
   ```bash
   cd backend
   source .venv/bin/activate
   alembic revision --autogenerate -m "fix_timezone_violations_task1"
   # Review and manually enhance if needed
   ```
7. **Test migration:**
   ```bash
   alembic upgrade head  # Apply
   alembic downgrade -1  # Rollback
   alembic upgrade head  # Re-apply
   ```
8. **Write tests** - Create test_timezone_compliance.py with 9 tests
9. **Run all tests** - Must pass before completion
10. **Update Phase 4.5 roadmap:**
    - Check off deliverables: `- [x] Deliverable description`
    - Add status: `**Status:** ✅ COMPLETE (2026-MM-DD)`
    - Add test results: `**Test Results:** X/X passing`
    - Add implementation summary (files modified, SQL snippets, etc.)

## Key Files to Review

### Golden Master & Analysis
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - **Source of truth**
- `dev-docs/analysis/phase-4.5-db-schema-sync-to-design-plan.md` - **Active roadmap** (Lines 83-150 for Task 1)
- `dev-docs/analysis/db-schema-vs-design/db-schema-dump-vs-design-analysis-v1.0.md` - Gap analysis
- `dev-docs/analysis/db-schema-vs-design/db-schema-sync-technical-instruction-v1.0.md` - Implementation guide

### Backend Code (Files to Modify)
1. `backend/app/models/system.py` - 2 columns:
   - `IdempotencyKey.first_seen_at`
   - `NotificationEvent.occurred_at`

2. `backend/app/models/integrations.py` - 1 column:
   - `IntegrationSyncMapping.last_synced_at`

3. `backend/app/models/quoting.py` - 2 columns:
   - `PricebookItemVersion.recorded_at`
   - `QuotePublicLinkContactAction.occurred_at`

4. `backend/app/models/saas.py` - 2 columns:
   - `ProductPlanProductFeatureVersion.recorded_at`
   - `ProductPlanVersion.recorded_at`

5. `backend/app/models/tax.py` - 1 column:
   - `TaxRateVersion.recorded_at`

6. `backend/app/models/catalog.py` - 1 column:
   - `TenantMarkupVersion.recorded_at`

### Test Files
- `backend/tests/conftest.py` - Existing fixtures
- `backend/tests/test_schema_sync_v2_6h.py` - Schema sync test suite
- `backend/tests/test_database_triggers.py` - Trigger tests
- **NEW:** `backend/tests/test_timezone_compliance.py` - Create this file with 9 tests

### Recent Schema Work (March 30, 2026)
- **Gap 1-6 Implementation:** `2026_03_30_1810-6907731fd637_sync_with_golden_master_v2_6h.py`
- **Highlander Rule Fix:** `2026_03_30_1819-102c1d8d3d4a_fix_user_endpoint_guard_trigger_logic.py`
- **Race Condition Fix:** `2026_03_30_1929-cbf672175f02_fix_user_endpoint_sync_race_condition.py`

## Success Criteria

**MUST COMPLETE ALL BEFORE MARKING TASK AS COMPLETE:**

### Deliverables (from Roadmap)

- [ ] **SQLModel Updates (9 files):**
  - [ ] `backend/app/models/system.py` - `IdempotencyKey.first_seen_at`
  - [ ] `backend/app/models/system.py` - `NotificationEvent.occurred_at`
  - [ ] `backend/app/models/integrations.py` - `IntegrationSyncMapping.last_synced_at`
  - [ ] `backend/app/models/quoting.py` - `PricebookItemVersion.recorded_at`
  - [ ] `backend/app/models/quoting.py` - `QuotePublicLinkContactAction.occurred_at`
  - [ ] `backend/app/models/saas.py` - `ProductPlanProductFeatureVersion.recorded_at`
  - [ ] `backend/app/models/saas.py` - `ProductPlanVersion.recorded_at`
  - [ ] `backend/app/models/tax.py` - `TaxRateVersion.recorded_at`
  - [ ] `backend/app/models/catalog.py` - `TenantMarkupVersion.recorded_at`
  
  **Required Pattern for Each:**
  ```python
  # BEFORE (wrong):
  first_seen_at: datetime = Field(nullable=False)
  
  # AFTER (correct):
  from core.db import AwareDatetime
  from sqlalchemy import Column, DateTime
  
  first_seen_at: AwareDatetime = Field(
      sa_column=Column(DateTime(timezone=True), nullable=False)
  )
  ```

- [ ] **Alembic Migration:**
  - [ ] Create migration file: `alembic revision --autogenerate -m "fix_timezone_violations_task1"`
  - [ ] Add ALTER COLUMN statements for all 9 fields (example below)
  - [ ] Test upgrade: `alembic upgrade head`
  - [ ] Test downgrade: `alembic downgrade -1`
  - [ ] Re-apply: `alembic upgrade head`
  
  **SQL Pattern for Each Column:**
  ```sql
  -- Example for idempotency_key.first_seen_at
  ALTER TABLE idempotency_key 
    ALTER COLUMN first_seen_at 
    TYPE timestamp with time zone 
    USING first_seen_at AT TIME ZONE 'UTC';
  
  -- Repeat for all 9 columns:
  -- 1. idempotency_key.first_seen_at
  -- 2. notification_event.occurred_at
  -- 3. integration_sync_mapping.last_synced_at
  -- 4. pricebook_item_version.recorded_at
  -- 5. quote_public_link_contact_action.occurred_at
  -- 6. product_plan_product_feature_version.recorded_at
  -- 7. product_plan_version.recorded_at
  -- 8. tax_rate_version.recorded_at
  -- 9. tenant_markup_version.recorded_at
  ```

- [ ] **Test Coverage:**
  - [ ] Create `backend/tests/test_timezone_compliance.py`
  - [ ] Write 9 tests (one per column):
    - `test_idempotency_key_first_seen_at_timezone`
    - `test_notification_event_occurred_at_timezone`
    - `test_integration_sync_mapping_last_synced_at_timezone`
    - `test_pricebook_item_version_recorded_at_timezone`
    - `test_quote_public_link_contact_action_occurred_at_timezone`
    - `test_product_plan_product_feature_version_recorded_at_timezone`
    - `test_product_plan_version_recorded_at_timezone`
    - `test_tax_rate_version_recorded_at_timezone`
    - `test_tenant_markup_version_recorded_at_timezone`
  - [ ] Each test verifies:
    1. Column has `tzinfo` set after retrieval
    2. Data round-trips with timezone preservation
    3. No data corruption from migration

### Success Verification

- [ ] All 9 columns use `AwareDatetime` type hint in Python code
- [ ] All 9 columns have `DateTime(timezone=True)` in SQLAlchemy
- [ ] Database shows `timestamptz` for all 9 columns (verify with `\d table_name`)
- [ ] Existing data migrated without corruption (validate timestamps)
- [ ] 9/9 timezone compliance tests passing
- [ ] **ALL existing tests pass** (439/439 baseline maintained)
- [ ] **ALL new tests pass** (9/9 timezone tests passing)
- [ ] **Test pass rate: 100%** (448/448 passing = 439 baseline + 9 new)
- [ ] Performance benchmarks met (no performance regression)
- [ ] Phase 4.5 roadmap updated with completion status
- [ ] Code follows Golden Master specification exactly

**Task Status in Roadmap:**
- ✅ **COMPLETE** - If all tests pass (implementation + tests 100% complete)
- 🟡 **PARTIALLY COMPLETE** - If fix document created for failing tests
  - Must include: "Implementation complete, tests require fixes (see test_timezone_compliance_fixes.md)"
  - Cannot mark COMPLETE until all tests pass

**If Tests Fail:**
- Create `dev-docs/testing-support/task-db-sync-01-test-fixes.md` with concrete fixes
- Update task status to "🟡 PARTIALLY COMPLETE" in Phase 4.5 roadmap
- Document exact steps to achieve 100% test pass rate
- Include time estimates for each fix

## Risk Assessment (from Roadmap)

- **Data Loss Risk:** MEDIUM
  - Requires careful `AT TIME ZONE 'UTC'` conversion
  - Existing timestamps must be preserved exactly
  - **Mitigation:** Test migration on copy of production data first
  
- **Downtime Required:** None
  - ALTER COLUMN is online operation in PostgreSQL 12+
  - No table locks required
  
- **Rollback Complexity:** LOW
  - Straightforward column type revert
  - Downgrade migration removes timezone awareness

## Questions to Ask

Before starting:
1. Have I read the Golden Master JSON for these 9 columns?
2. Have I reviewed the gap analysis to understand WHY this change is needed?
3. Do I understand the data migration impact (existing data)?
4. What existing code can I reference for similar patterns? (Check `QuoteAcceptance.approved_at` - Gap 5)
5. What tests need to be written? (9 timezone compliance tests)

During implementation:
1. Am I following the Golden Master specification exactly?
2. Have I tested the migration in both directions (upgrade + downgrade)?
3. Are ALL tests passing (100% pass rate)?
4. Am I documenting as I go (inline in roadmap)?
5. Is this aligned with v2.6h schema standard?

After implementation:
1. Do I have 100% test pass rate (448/448 passing = 439 baseline + 9 new)?
2. If tests fail, have I created a detailed fix document?
3. Have I marked the task status correctly (COMPLETE vs PARTIALLY COMPLETE)?
4. Can another developer understand what was changed and why?
5. Does the migration rollback cleanly without errors?

## Example Task Flow

```bash
# ============================================================================
# Phase 4.5 Task 1 Execution
# ============================================================================

# 1. Review the task in Phase 4.5 roadmap
cat dev-docs/analysis/phase-4.5-db-schema-sync-to-design-plan.md | grep -A 70 "Task 1:"

# 2. Review Golden Master specification for each column
cat dev-docs/db-design/pilot-db-schema-v2.6h.json | jq '.tables[] | select(.name == "idempotency_key")'

# 3. Check current schema for IdempotencyKey
cd backend
source .venv/bin/activate
python -c "from app.models.system import IdempotencyKey; import inspect; print(inspect.getsource(IdempotencyKey))"

# 4. Check existing migrations
ls -la migrations/versions/ | grep -i timezone

# 5. Update SQLModel files (6 files, 9 columns total)
# [Edit backend/app/models/system.py - 2 columns]
# [Edit backend/app/models/integrations.py - 1 column]
# [Edit backend/app/models/quoting.py - 2 columns]
# [Edit backend/app/models/saas.py - 2 columns]
# [Edit backend/app/models/tax.py - 1 column]
# [Edit backend/app/models/catalog.py - 1 column]

# 6. Create migration
alembic revision --autogenerate -m "fix_timezone_violations_task1"

# 7. Review and enhance migration (add USING clause for safe conversion)
# [Edit migration file to ensure AT TIME ZONE 'UTC' conversion]

# 8. Test migration upgrade
alembic upgrade head

# 9. Verify schema changes (all 9 columns should show timestamptz)
psql -d pilot_dev -c "\d idempotency_key" | grep first_seen_at
psql -d pilot_dev -c "\d notification_event" | grep occurred_at
psql -d pilot_dev -c "\d integration_sync_mapping" | grep last_synced_at
psql -d pilot_dev -c "\d pricebook_item_version" | grep recorded_at
psql -d pilot_dev -c "\d quote_public_link_contact_action" | grep occurred_at
psql -d pilot_dev -c "\d product_plan_product_feature_version" | grep recorded_at
psql -d pilot_dev -c "\d product_plan_version" | grep recorded_at
psql -d pilot_dev -c "\d tax_rate_version" | grep recorded_at
psql -d pilot_dev -c "\d tenant_markup_version" | grep recorded_at

# 10. Test migration downgrade
alembic downgrade -1

# 11. Re-apply migration
alembic upgrade head

# 12. Run baseline tests (expect 412/412)
pytest tests/ --ignore=tests/integration/ -v 2>&1 | grep -E "(passed|failed|===)" | tail -5

# 13. Run schema sync tests (expect 30/30)
pytest tests/test_schema_sync_v2_6h.py -v

# 14. Write new tests for this task
# [Create backend/tests/test_timezone_compliance.py with 9 tests]

# 15. Run all tests without integration (expect 421/421 = 412 baseline + 9 new)
pytest tests/ --ignore=tests/integration/ -v

# 16. If baseline tests pass, run ALL tests (expect 448/448 = 439 baseline + 9 new)
pytest tests/ -v

# 17. Update Phase 4.5 roadmap
# [Edit dev-docs/analysis/phase-4.5-db-schema-sync-to-design-plan.md]
# Mark Task 1 as complete:
# - [x] SQLModel updates (9 files)
# - [x] Alembic migration
# - [x] Test coverage
# **Status:** ✅ COMPLETE (2026-04-02)
# **Test Results:**
# - Baseline + new without integration: 421/421 passing (9 new tests added)
# - Baseline + new with integration: 448/448 passing (9 new tests added)
# **Migration:** 2026_04_02_XXXX-fix_timezone_violations_task1.py
# **Files Modified:** 6 SQLModel files, 1 migration, 1 test file
```

## Notes

- **Golden Master is Law:** `pilot-db-schema-v2.6h.json` is the single source of truth
- **v2.0 Timezone Standard:** ALL datetime fields MUST be `timestamptz` (no exceptions)
- **Reference Implementation:** Check `QuoteAcceptance.approved_at` (Gap 5) for timezone-aware pattern
- **Data Safety:** Always validate existing data before migration
- **Test First:** Write comprehensive tests (9 tests, one per column)
- **Document Inline:** Update Phase 4.5 roadmap as you work (don't wait until end)
- **Migration Rollback:** MUST test downgrade migration (production safety)
- **No Feature Creep:** Only implement what Golden Master specifies (9 columns, no more)

## Related Tasks

**Completed (Reference for Patterns):**
- ✅ Gap 5: `QuoteAcceptance.approved_at` timezone compliance (March 30, 2026)
  - File: `backend/migrations/versions/2026_03_30_1810-6907731fd637_sync_with_golden_master_v2_6h.py`
  - Pattern to follow for this task

**Next Task After Completion:**
- Task 2: Citext Conversion for User Email (0.5 days, HIGH priority)
- Blocked by: None (can start immediately after Task 1)

## Schema Synchronization Phases

**Phase 1: Foundation (Data Types & Columns)** - CRITICAL
- **Task 1: Fix timezone violations (9 columns)** ← YOU ARE HERE
- Task 2: Convert user email to citext
- Task 3: Verify QuickBooks identity rules (COMPLETE)

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
2. Copy this entire prompt to begin Task 1
3. When finished, the AI will update the Phase 4.5 roadmap with completion status
4. The AI will have full context and standards from Golden Master v2.6h
5. Expected completion: 448/448 tests passing (439 baseline + 9 new timezone tests)
