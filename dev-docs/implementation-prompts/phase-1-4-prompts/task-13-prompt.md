# Task 13 Implementation Prompt

```
Task: Phase 2, Task #13 - Profitability Rollup Worker
Reference: dev-docs/analysis/phase-2-5-implementation-roadmap.md Task #13
(Original: Gap #10, #25 in phase-1-4-implementation-gap-analysis.md)

## Context

We're building AevoFab AI, an AI-powered SaaS platform for electrical contractors with voice-controlled quoting and QuickBooks integration. Following the 80/20 rule to reach MVP quickly.

## Completed So Far

**Phase 1-A: Critical Blockers (COMPLETE - 7 tasks)**
✅ Test Endpoints, Tenant ID Fix, Idempotency, Request Tracing
✅ Database Triggers, Tax Calculations, Multi-Tenancy Tests

**Phase 1-B: Core Completeness (COMPLETE - 4 tasks)**
✅ Polymorphic Relationships, Contact Management
✅ Quote Acceptance Workflow, Voice Action Execution

**Phase 2: Background Processing (IN PROGRESS)**
✅ Task 12: Celery Setup & Configuration (COMPLETE - 221/221 tests passing)

**Test Coverage:** 221/221 passing (100% pass rate)
**See:** dev-docs/analysis/phase-2-5-implementation-roadmap.md for full details

## Current Task

Implement a Celery background worker that automatically recalculates job profitability metrics in real-time. Currently, `job.actual_labor_cost_cents`, `job.actual_material_cost_cents`, and `job.actual_profit_cents` never update after job creation, making the profitability dashboard show stale $0 values.

**Current State:**
- `job.actual_labor_cost_cents` never updates after creation
- `job.actual_material_cost_cents` never updates after expenses added
- `job.actual_profit_cents` always $0
- Dashboard shows incorrect profitability data

**Priority:** BLOCKER (real-time dashboard essential)
**Estimated Effort:** 4 days
**Task Spec:** See dev-docs/analysis/phase-2-5-implementation-roadmap.md Task #13
**Design Context:** dev-docs/db-design/aevofab-db-process-v2.6h.md

## Requirements

### 1. Documentation Standards
- **New docs go in dev-docs/** organized by topic:
  - `analysis/` - Gap analysis, remediation plans
  - `architecture-design/` - System architecture docs
  - `db-design/` - Database schema and process docs
  - `product-requirements/` - PRD and user stories
  - `testing-support/` - Test guides and examples
  - `api-guides/` - API usage documentation
- **Always reference the authoritative design docs:**
  - `dev-docs/analysis/phase-2-5-implementation-roadmap.md` - Active task roadmap (Phases 2-5)
  - `dev-docs/db-design/aevofab-db-process-v2.6h.md` - Database operations & schema
  - `dev-docs/architecture-design/mvp-arch.md` - System architecture
  - `dev-docs/analysis/phase-1-4-implementation-gap-analysis.md` - Historical gap tracking
  - `.roo/rules-aevofab-architect/infrastructure-constraints.md` - Cost limits ($1k/mo cap)
  - `.roo/rules-aevofab-architect/scaling-logic.md` - When/how to scale resources
- **Create implementation plan first** (task-13-profitability-rollup-impl-plan.md) before coding
- **Update implementation roadmap** when marking tasks complete

### 2. Testing Standards (CRITICAL FOR MVP)

**⚠️ ZERO FAILING TESTS POLICY:**
- **ALL tests MUST pass before marking a gap as RESOLVED**
- **NO exceptions** - MVP requires 100% test pass rate
- If tests fail after implementation, you have TWO options:
  1. **Fix immediately** (preferred for simple fixes)
  2. **Create detailed fix document** (for complex test issues)
     - Document ALL failing tests with concrete, actionable fixes
     - Mark gap as "PARTIALLY COMPLETE" not "RESOLVED" in analysis doc
     - Include estimated time to fix each test
     - Provide step-by-step fix instructions
     - Example: `backend/tests/test_profitability_rollup_fixes.md`

**Test Execution:**
- **Current Baseline:** 221/221 tests passing - DO NOT regress this
- **Tests are MANDATORY** - No code without tests
- **Run existing tests first:**
  - verbose: `cd backend && source .venv/bin/activate && pytest tests/ -v`
  - standard: `cd backend && source .venv/bin/activate && pytest tests/`
  - concise: `cd backend && source .venv/bin/activate && pytest tests/ -v 2>&1 | grep -E "(passed|failed|===)" | tail -5`
- **All existing tests must pass** - Baseline must not regress
- **All new tests must pass** - No failing tests allowed

**Test Development:**
- **BEFORE writing tests:** Review `backend/tests/conftest.py` to understand existing fixtures
  - Use `pytest --fixtures` to see all available fixtures
  - Reuse existing fixtures (e.g., `db_session`, `test_tenant`, `client`) instead of creating duplicates
  - Match fixture naming conventions and patterns from conftest.py
  - Example: Use `db_session` not `db`, use `test_tenant` not `tenant`
- **Create new test file:** `backend/tests/test_profitability_rollup.py`
- **Test coverage required:**
  - Unit tests for core logic
  - Integration tests for Celery task execution
  - Error handling and edge cases
  - Tenant isolation verification (multi-tenancy tests)
  - Race condition and atomicity tests
  - Performance tests (task completes within 5 seconds)

**Test Data Management:**
- **Reference data seeding:** Review `backend/migrations/seed_test_data.py` for existing seed patterns
  - Seed reference tables (EntityType, ContactType, TaxabilityCode, etc.) in migrations
  - Use fixtures in conftest.py for test-specific data (tenants, users, etc.)
- **Test data creation:** Create necessary test data in fixtures or test setup
  - Follow existing patterns in `conftest.py` (e.g., `test_tenant`, `test_customer`)
  - Use factory patterns for complex entities (see existing test files)
- **Test data cleanup:** Database automatically rolls back after each test (session scope)
  - conftest.py uses `pytest` fixtures with `db_session` that auto-rollback
  - No manual cleanup needed - each test runs in isolated transaction
  - Exception: Integration tests that commit - must explicitly clean up

### 3. Code Standards
- **Follow existing patterns** - Check similar implementations first
- **Type hints required** - Use AuthenticatedUser, not User
- **Error handling** - RFC 7807 format (see existing routes)
- **Docstrings required** - Document all functions/classes
- **No feature creep** - Strictly follow 80/20 MVP prioritization
- **Phase 2+ Cost Awareness** - For infrastructure tasks (Celery, Redis, integrations), respect $1k/mo budget cap (see infrastructure-constraints.md)

### 4. Database Standards
- **DO NOT hallucinate schema** - Always read backend/app/models/*.py first
- **Use Alembic migrations** for schema changes
- **Respect tenant isolation** - All queries filter by tenant_id
- **Follow ORM patterns** - Use SQLModel/SQLAlchemy correctly

### 5. Workflow
1. **Read the task roadmap** to understand the requirements
2. **Review design specs** (db-process-v2.6h.md, mvp-arch.md)
3. **Create implementation plan** document with detailed tasks
4. **Get approval** on the plan before coding
5. **Implement** following the plan step-by-step
6. **Write tests** alongside implementation
7. **Run all tests** - Must pass before completion
8. **Update documentation** - **BOTH documents MUST be updated:**
   
   **Document 1: phase-2-5-implementation-roadmap.md (Active Task Tracking)**
   - Find your task section (e.g., "Task 13: Profitability Rollup Worker")
   - Check off completed deliverables using `- [x]` checkbox format
   - Update any inline status notes or test results
   - If all deliverables complete, task is ✅ COMPLETE
   - If some deliverables incomplete, task is ⚠️ PARTIALLY COMPLETE
   
   **Document 2: phase-1-4-implementation-gap-analysis.md (Historical Gap Tracking)**
   - Find the original gap sections (e.g., "Gap #10: Profitability Rollup", "Gap #25")
   - Update the gap status at the top:
     - ✅ **RESOLVED** if all tests pass and implementation 100% complete
     - ⚠️ **PARTIALLY COMPLETE** if fix document created or deliverables incomplete
   - Add "Resolved Date" line if marking RESOLVED
   - Add implementation summary (what was built, files created/modified, test results)
   - Cross-reference to task number (e.g., "See also: Task 13 in phase-2-5-implementation-roadmap.md")
   
   **Both documents must match:**
   - If roadmap task shows incomplete deliverables → gap status = PARTIALLY COMPLETE
   - If roadmap task shows all complete + tests pass → gap status = RESOLVED
   - Follow existing patterns from Phase 1-A/1-B completed tasks (see Gaps #1, #6, #11, #13, #17, etc.)

## Key Files to Review

### Architecture
- `dev-docs/analysis/phase-2-5-implementation-roadmap.md` - **Active task roadmap (Phases 2-5)**
- `dev-docs/architecture-design/mvp-arch.md` - Overall system design
- `dev-docs/db-design/aevofab-db-process-v2.6h.md` - Database operations & schema
- `dev-docs/analysis/phase-1-4-implementation-gap-analysis.md` - Historical gap tracking

### Backend Code
- `backend/app/models/` - Database models (SQLModel ORM)
- `backend/app/models/crm.py` - Job, JobTimeEntry, JobExpense models
- `backend/api/routes/` - API endpoints
- `backend/core/` - Core utilities (auth, db, middleware)
- `backend/core/celery_app.py` - Celery configuration (Task 12 - COMPLETE)
- `backend/tasks/` - Background jobs (cleanup_idempotency_keys.py exists)
- `backend/tests/` - Test suite
- `backend/tests/test_celery.py` - Celery test patterns (24 tests)

### Recent Examples (Phase 1 & Phase 2 Completed Work)
- **Celery Setup:** `backend/core/celery_app.py`, `backend/tests/test_celery.py` (Task 12 - COMPLETE)
- **Database Triggers:** `backend/migrations/versions/2026_03_17_1451-*.py` (Quote/CO totals)
- **Tax Calculations:** `backend/core/tax_calculation.py` (IRS-compliant rounding)
- **Voice Actions:** `backend/services/voice_action_router.py` (10 MVP handlers)
- **Polymorphic Relations:** `backend/api/routes/contacts.py`, `addresses.py` (800+ lines each)
- **Test Patterns:** `backend/tests/test_voice_actions.py`, `test_multi_tenancy_isolation.py`
- **Documentation:** `dev-docs/analysis/gap-*-remediation-plan.md` (10+ examples)
- **Implementation Plans:** `dev-docs/analysis/task-12-celery-impl-plan.md` (Task 12 pattern)

## Implementation Details

### Celery Task Definition

Create `backend/tasks/profitability_rollup.py` with the following structure:

```python
from core.celery_app import celery_app
from core.db import get_db
from sqlmodel import select
from app.models.crm import Job, JobTimeEntry, JobExpense
from typing import Optional
import logging

logger = logging.getLogger(__name__)

@celery_app.task(name="calculate_job_profitability")
def calculate_job_profitability(job_id: str) -> dict:
    """
    Recalculate job profitability by summing:
    - job_time_entry.total_cost_cents → actual_labor_cost_cents
    - job_expense.cost_cents → actual_material_cost_cents
    - invoiced_total - actual_costs → actual_profit_cents
    
    Returns dict with updated values for verification.
    """
    # Query job_time_entry WHERE job_id AND status=approved
    # Query job_expense WHERE job_id
    # Update job table atomically (use SELECT FOR UPDATE)
    # Log to audit.event (future enhancement)
    pass
```

### Database Query Pattern

**CRITICAL:** Use atomic updates to prevent race conditions:

```python
# Inside database transaction
with get_db() as session:
    # Lock the job row for update
    job = session.exec(
        select(Job).where(Job.id == job_id).with_for_update()
    ).first()
    
    # Calculate labor costs
    labor_total = session.exec(
        select(func.sum(JobTimeEntry.total_cost_cents))
        .where(JobTimeEntry.job_id == job_id)
        .where(JobTimeEntry.status == "approved")
    ).first() or 0
    
    # Calculate material costs
    material_total = session.exec(
        select(func.sum(JobExpense.cost_cents))
        .where(JobExpense.job_id == job_id)
    ).first() or 0
    
    # Update atomically
    job.actual_labor_cost_cents = labor_total
    job.actual_material_cost_cents = material_total
    job.actual_profit_cents = (
        job.invoiced_total_cents - labor_total - material_total
    )
    
    session.add(job)
    session.commit()
```

### Trigger Points

The task should be triggered from:
1. **API routes that create/update job_time_entry**
2. **API routes that create/update job_expense**
3. **Invoice creation/update (affects invoiced_total_cents)**

Example in API endpoint:
```python
from tasks.profitability_rollup import calculate_job_profitability

@router.post("/time-entries")
async def create_time_entry(...):
    # Create time entry
    db.add(time_entry)
    db.commit()
    
    # Trigger async profitability recalculation
    calculate_job_profitability.delay(str(time_entry.job_id))
    
    return time_entry
```

## Success Criteria

**MUST COMPLETE ALL BEFORE MARKING GAP AS RESOLVED:**

- [ ] Implementation plan created and approved (task-13-profitability-rollup-impl-plan.md)
- [ ] Celery task implementation complete (`backend/tasks/profitability_rollup.py`)
- [ ] Task triggered from time entry/expense API routes
- [ ] Atomic database updates (SELECT FOR UPDATE pattern)
- [ ] Comprehensive test suite (15+ tests minimum):
  - [ ] Basic rollup calculation test
  - [ ] Multiple time entries aggregation
  - [ ] Multiple expenses aggregation
  - [ ] Approved vs non-approved time entry filtering
  - [ ] Empty job (no time entries/expenses) edge case
  - [ ] Negative profit scenario (over budget)
  - [ ] Race condition test (concurrent updates)
  - [ ] Tenant isolation verification
  - [ ] Performance test (completes within 5 seconds)
  - [ ] Idempotency test (same result on repeated calls)
  - [ ] Error handling (invalid job_id, missing job)
  - [ ] Integration test (create entry → verify rollup)
- [ ] **ALL existing tests pass** (no regression from 221/221 baseline)
- [ ] **ALL new tests pass** (zero failures)
- [ ] **Test pass rate: 100%** (X/X passing, 0 failing)
- [ ] Documentation updated in BOTH analysis documents
- [ ] Code follows existing patterns and standards
- [ ] Performance verified: Add time entry → profitability updates within 5 seconds
- [ ] Dashboard query returns accurate cents values
- [ ] No database deadlocks under concurrent updates

**Gap Status in Analysis Doc:**
- ✅ **RESOLVED** - If all tests pass (implementation + tests 100% complete)
- ⚠️ **PARTIALLY COMPLETE** - If fix document created for failing tests
  - Must include: "Implementation complete, tests require fixes (see test_profitability_rollup_fixes.md)"
  - Cannot mark RESOLVED until all tests pass

**If Tests Fail:**
- Create `backend/tests/test_profitability_rollup_fixes.md` with concrete fixes for ALL failing tests
- Update gap status to "PARTIALLY COMPLETE" in analysis doc
- Document exact steps to achieve 100% test pass rate
- Include time estimates for each fix

## Questions to Ask

Before starting:
1. Have I read Gap #10 and Gap #25 thoroughly?
2. Have I reviewed the Job, JobTimeEntry, and JobExpense models?
3. Do I understand the difference between approved vs. non-approved time entries?
4. What existing code can I reference for Celery task patterns? (See Task 12)
5. How do database triggers currently calculate quote/change order totals? (Similar pattern)

During implementation:
1. Am I following the atomic update pattern (SELECT FOR UPDATE)?
2. Are ALL tests passing (100% pass rate)?
3. Am I documenting as I go?
4. Is this aligned with 80/20 MVP priorities?
5. Does the task complete within 5 seconds?

After implementation:
1. Do I have 100% test pass rate (X/X passing, 0 failing)?
2. If tests fail, have I created a detailed fix document?
3. Have I marked BOTH gap statuses correctly (Gap #10 and Gap #25)?
4. Can the profitability dashboard now show real-time data?

## Example Task Flow

```bash
# 1. Review the task in roadmap
cat dev-docs/analysis/phase-2-5-implementation-roadmap.md | grep -A 50 "Task 13"

# 2. Check original gaps for context
cat dev-docs/analysis/phase-1-4-implementation-gap-analysis.md | grep -A 20 "Gap #10"
cat dev-docs/analysis/phase-1-4-implementation-gap-analysis.md | grep -A 20 "Gap #25"

# 3. Check database models
cat backend/app/models/crm.py | grep -A 30 "class Job"
cat backend/app/models/crm.py | grep -A 20 "class JobTimeEntry"
cat backend/app/models/crm.py | grep -A 20 "class JobExpense"

# 4. Review existing Celery patterns (Task 12)
cat backend/core/celery_app.py
cat backend/tasks/cleanup_idempotency_keys.py
cat backend/tests/test_celery.py

# 5. Run existing tests (baseline: 221 passing)
cd backend && source .venv/bin/activate && pytest tests/ -v

# 6. Create your implementation
# [write code]

# 7. Run tests again (must maintain 100% pass rate)
pytest tests/ -v

# 8. Test manually
# Start Celery worker
celery -A core.celery_app worker --loglevel=info

# Create time entry via API and verify rollup
curl -X POST http://localhost:8000/api/v1/time-entries/test \
  -H "Content-Type: application/json" \
  -d '{"job_id": "...", "hours": 8, "hourly_rate_cents": 7500}'

# Query job to verify profitability updated
curl http://localhost:8000/api/v1/jobs/test/{job_id}
```

## Notes

- **MVP Focus:** Follow dev-docs/product-requirements/mvp-prd.md for scope
- **80/20 Rule:** See .roo/rules-mvp-builder/80-20-prioritization.md
- **Mike the Solo Contractor:** Our primary persona - keep it simple!
- **No Enterprise Features:** Multi-trade, complex scheduling, etc. are out of scope
- **Cost Constraints:** Background workers must be efficient (see infrastructure-constraints.md)
- **Celery Configuration:** Already complete from Task 12 - reuse existing setup
- **Audit Logging:** Defer to Phase 4, Task 20 - focus on core functionality first
- **Database Triggers Alternative:** Consider if database triggers are more appropriate than Celery for real-time updates (discuss in implementation plan)
```
