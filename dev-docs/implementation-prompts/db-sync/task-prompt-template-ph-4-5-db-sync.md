# Phase 4.5 Task Prompt Template
## Database Schema Synchronization to Golden Master

Use this prompt template to create the prompt that will be used to start a new Phase 4.5 database schema synchronization task session. Copy and customize for each task and then create a new prompt document named task-db-sync-##-prompt.md located in the same folder as this template doc.

---

## INSTRUCTIONS FOR ARCHITECT AGENT

When the user says "Create prompt for Phase 4.5 Task X" or "Create prompt for Task X: [Task Name]":

### Your Job (Architect Agent)
1. **Read the roadmap:** Extract task details from `dev-docs/analysis/phase-4.5-db-schema-sync-to-design-plan.md`
2. **Fill in the template:** Replace all [bracketed placeholders] with actual task details
3. **Create output file:** Save as `dev-docs/implementation-prompts/task-db-sync-##-prompt.md` (zero-padded)
4. **Present to user:** Show a concise summary of what was created for review

### Information to Extract from Roadmap
For the specified task number, extract:
- **Task number and phase** (e.g., "Phase 1, Task #1" or "Phase 4, Task #13")
- **Feature name** (e.g., "Timezone Enforcement" or "Vector Indexes")
- **Priority level** (CRITICAL/HIGH/MEDIUM/LOW)
- **Estimated effort** (e.g., "1-2 days")
- **Status** (🔴 NOT STARTED / 🟡 IN PROGRESS / ✅ COMPLETE)
- **Gap reference** (which section in analysis doc)
- **Deliverables list** - Copy checkboxes from roadmap "Deliverables" section
- **Success criteria** - Extract from roadmap task spec
- **Files to modify** - List of specific files with line numbers if available
- **Migration details** - SQL snippets and migration strategy
- **Test requirements** - Specific test scenarios to implement

### Template Customization Checklist
Replace these placeholders in the template below:
- [ ] `[Phase X, Task #XX - Feature Name]` → actual task (e.g., "Phase 1, Task #1 - Timezone Enforcement")
- [ ] `[Describe the specific gap/feature to implement]` → full description from roadmap
- [ ] `[CRITICAL/HIGH/MEDIUM/LOW]` → actual priority from roadmap
- [ ] `[X days]` → actual effort estimate (e.g., "1-2 days")
- [ ] `Task #XX` → replace all instances with actual task number
- [ ] `[Gap Reference]` → actual analysis section reference
- [ ] **Success Criteria section** → Add task-specific deliverables from roadmap
- [ ] **Files to Modify section** → Add specific file paths from roadmap
- [ ] **Migration SQL section** → Add SQL snippets from roadmap

### Output File Naming
Format: `task-db-sync-##-prompt.md` where ## is zero-padded (e.g., `task-db-sync-01-prompt.md`, `task-db-sync-13-prompt.md`)

### Critical Reminder for Coding Agent
The prompt you create MUST instruct the coding agent to update the Phase 4.5 roadmap document when complete:

**Document to Update:** `dev-docs/analysis/phase-4.5-db-schema-sync-to-design-plan.md`
- Check off completed deliverables using `- [x]` checkbox format
- Add "Status: ✅ COMPLETE (YYYY-MM-DD)" at top of task section
- Add "Test Results:" line showing X/X tests passing
- Include implementation summary with files modified and test coverage

---

## PROMPT FOR NEXT TASK

```
Task: [Phase X, Task #XX - Feature Name]
Reference: dev-docs/analysis/phase-4.5-db-schema-sync-to-design-plan.md Task #XX
(Analysis: [Gap Reference] in db-schema-dump-vs-design-analysis-v1.0.md)

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

[Describe the specific gap/feature to implement]

**Priority:** [CRITICAL/HIGH/MEDIUM/LOW]  
**Estimated Effort:** [X days]  
**Task Spec:** See dev-docs/analysis/phase-4.5-db-schema-sync-to-design-plan.md Task #XX  
**Design Authority:** dev-docs/db-design/pilot-db-schema-v2.6h.json  
**Analysis Reference:** dev-docs/analysis/db-schema-vs-design/db-schema-dump-vs-design-analysis-v1.0.md

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
- **Create new test file:** `backend/tests/test_[feature].py`
- **Test coverage required:**
  - Database constraint tests (UNIQUE, CHECK, FK violations)
  - Trigger behavior tests (INSERT/UPDATE/DELETE)
  - Data migration tests (existing data integrity)
  - Performance benchmarks (query times before/after indexes)
  - Rollback tests (downgrade migration)

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
5. **Implement SQLModel changes** - Update models with constraints/fields
6. **Create Alembic migration:**
   ```bash
   cd backend
   source .venv/bin/activate
   alembic revision --autogenerate -m "descriptive_name"
   # Manually add PL/pgSQL functions/triggers if needed
   ```
7. **Test migration:**
   ```bash
   alembic upgrade head  # Apply
   alembic downgrade -1  # Rollback
   alembic upgrade head  # Re-apply
   ```
8. **Write tests** - Test constraints, triggers, data integrity
9. **Run all tests** - Must pass before completion
10. **Update Phase 4.5 roadmap:**
    - Check off deliverables: `- [x] Deliverable description`
    - Add status: `**Status:** ✅ COMPLETE (2026-MM-DD)`
    - Add test results: `**Test Results:** X/X passing`
    - Add implementation summary (files modified, SQL snippets, etc.)

## Key Files to Review

### Golden Master & Analysis
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - **Source of truth**
- `dev-docs/analysis/phase-4.5-db-schema-sync-to-design-plan.md` - **Active roadmap**
- `dev-docs/analysis/db-schema-vs-design/db-schema-dump-vs-design-analysis-v1.0.md` - Gap analysis
- `dev-docs/analysis/db-schema-vs-design/db-schema-sync-technical-instruction-v1.0.md` - Implementation guide

### Backend Code
- `backend/app/models/` - Database models (SQLModel ORM)
- `backend/migrations/versions/` - Alembic migrations
- `backend/tests/test_schema_sync_v2_6h.py` - Schema sync test suite
- `backend/tests/test_database_triggers.py` - Trigger tests

### Recent Schema Work (March 30, 2026)
- **Gap 1-6 Implementation:** `2026_03_30_1810-6907731fd637_sync_with_golden_master_v2_6h.py`
- **Highlander Rule Fix:** `2026_03_30_1819-102c1d8d3d4a_fix_user_endpoint_guard_trigger_logic.py`
- **Race Condition Fix:** `2026_03_30_1929-cbf672175f02_fix_user_endpoint_sync_race_condition.py`

## Success Criteria

**MUST COMPLETE ALL BEFORE MARKING TASK AS COMPLETE:**

- [ ] SQLModel changes implemented per Golden Master spec
- [ ] Alembic migration created and tested (upgrade + downgrade)
- [ ] Pre-migration data validation completed (no constraint violations)
- [ ] Migration applied successfully to local database
- [ ] **ALL existing tests pass** (439/439 baseline maintained)
- [ ] **ALL new tests pass** (zero failures)
- [ ] **Test pass rate: 100%** (X/X passing, 0 failing)
- [ ] Performance benchmarks met (if applicable)
- [ ] Phase 4.5 roadmap updated with completion status
- [ ] Code follows Golden Master specification exactly

**Task Status in Roadmap:**
- ✅ **COMPLETE** - If all tests pass (implementation + tests 100% complete)
- 🟡 **PARTIALLY COMPLETE** - If fix document created for failing tests
  - Must include: "Implementation complete, tests require fixes (see test_[feature]_fixes.md)"
  - Cannot mark COMPLETE until all tests pass

**If Tests Fail:**
- Create `dev-docs/testing-support/task-db-sync-##-test-fixes.md` with concrete fixes
- Update task status to "🟡 PARTIALLY COMPLETE" in Phase 4.5 roadmap
- Document exact steps to achieve 100% test pass rate
- Include time estimates for each fix

## Questions to Ask

Before starting:
1. Have I read the Golden Master JSON for this specific task?
2. Have I reviewed the gap analysis to understand WHY this change is needed?
3. Do I understand the data migration impact (existing data)?
4. What existing code can I reference for similar patterns?
5. What tests need to be written?

During implementation:
1. Am I following the Golden Master specification exactly?
2. Have I tested the migration in both directions (upgrade + downgrade)?
3. Are ALL tests passing (100% pass rate)?
4. Am I documenting as I go (inline in roadmap)?
5. Is this aligned with v2.6h schema standard?

After implementation:
1. Do I have 100% test pass rate (X/X passing, 0 failing)?
2. If tests fail, have I created a detailed fix document?
3. Have I marked the task status correctly (COMPLETE vs PARTIALLY COMPLETE)?
4. Can another developer understand what was changed and why?
5. Does the migration rollback cleanly without errors?

## Example Task Flow

```bash
# ============================================================================
# Phase 4.5 Task Execution Example
# ============================================================================

# 1. Review the task in Phase 4.5 roadmap
cat dev-docs/analysis/phase-4.5-db-schema-sync-to-design-plan.md | grep -A 50 "Task 1:"

# 2. Review Golden Master specification
cat dev-docs/db-design/pilot-db-schema-v2.6h.json | jq '.tables[] | select(.name == "idempotency_key")'

# 3. Check current schema
cd backend
source .venv/bin/activate
python -c "from app.models.system import IdempotencyKey; import inspect; print(inspect.getsource(IdempotencyKey))"

# 4. Check existing migrations
ls -la migrations/versions/ | grep -i timezone

# 5. Update SQLModel file
# [Edit backend/app/models/system.py with AwareDatetime changes]

# 6. Create migration
alembic revision --autogenerate -m "fix_timezone_violations_phase1"

# 7. Review and enhance migration
# [Edit migration file to add any manual SQL if needed]

# 8. Test migration upgrade
alembic upgrade head

# 9. Verify schema change
psql -d pilot_dev -c "\d idempotency_key" | grep first_seen_at
# Should show: timestamptz

# 10. Test migration downgrade
alembic downgrade -1

# 11. Re-apply migration
alembic upgrade head

# 12. Run baseline tests (baseline tests without integration is 412 tests)
pytest tests/ --ignore=tests/integration/ -v 2>&1 | grep -E "(passed|failed|===)" | tail -5

# 13. Run schema sync tests
pytest tests/test_schema_sync_v2_6h.py -v

# 14. Write new tests for this task
# [Create test_timezone_compliance.py]

# 15. Run all tests (this should return 412 test plus new tests)
pytest --ignore=tests/integration/ tests/ -v

# 16. If baseline tests pass, run ALL tests (expect 439 tests plus new tests)
pytest tests/ -v

# 17. Update Phase 4.5 roadmap
# [Edit phase-4.5-db-schema-sync-to-design-plan.md]
# - [x] SQLModel updates (9 files)
# - [x] Alembic migration
# - [x] Test coverage
# **Status:** ✅ COMPLETE (2026-04-02)
# **Test Results:**
# - Baseline tests plus new without integration tests:421/421 passing (9 new tests added)
# - Baseline tests plus new with integration tests: 448/448 passing (9 new tests added)
```

## Notes

- **Golden Master is Law:** `pilot-db-schema-v2.6h.json` is the single source of truth
- **v2.0 Timezone Standard:** ALL datetime fields MUST be `timestamptz` (no exceptions)
- **Zero Downtime:** Use `CONCURRENTLY` for index creation, avoid `ACCESS EXCLUSIVE` locks
- **Data Safety:** Always validate existing data before adding constraints
- **Test First:** Write tests before implementing complex triggers/functions
- **Document Inline:** Update Phase 4.5 roadmap as you work (don't wait until end)
- **Migration Rollback:** MUST test downgrade migration (production safety)
- **No Feature Creep:** Only implement what Golden Master specifies

## Schema Synchronization Phases

**Phase 1: Foundation (Data Types & Columns)** - CRITICAL
- Fix timezone violations (9 columns)
- Convert user email to citext
- Verify QuickBooks identity rules

**Phase 2: Functions & Triggers** - CRITICAL
- Implement 3 missing PL/pgSQL functions
- Add audit triggers to 30+ tables
- Rename functions to follow _fn standard
- Verify operational trigger inventory

**Phase 3: Data Integrity (Constraints)** - HIGH
- Add 4 unique constraints
- Add extensive CHECK constraints
- Add 6 temporal GIST exclusion constraints

**Phase 4: Advanced Indexing** - MEDIUM
- Add 2 partial indexes (performance)
- Add 2 partial unique indexes
- Add 2 HNSW vector indexes (Voice AI)
```

---

## Usage

1. Start this task with the `MVP Builder` custom Roo Code mode
2. Copy the prompt section above to begin
3. Fill in the specific task details as outlined and detailed
4. When finished, the AI will update the Phase 4.5 roadmap with completion status
5. The AI will have full context and standards from Golden Master v2.6h
