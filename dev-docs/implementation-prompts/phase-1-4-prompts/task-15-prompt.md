# Task Prompt: Phase 2, Task #15 - Session Expiration & Cleanup

```
Task: Phase 2, Task #15 - Session Expiration & Cleanup
Reference: dev-docs/analysis/phase-2-5-implementation-roadmap.md Task #15
(Original: Gap #19 in phase-1-4-implementation-gap-analysis.md)

## Context

We're building AevoFab AI, an AI-powered SaaS platform for electrical contractors with voice-controlled quoting and QuickBooks integration. Following the 80/20 rule to reach MVP quickly.

## Completed So Far

**Phase 1-A: Critical Blockers (COMPLETE - 7 tasks)**
✅ Test Endpoints, Tenant ID Fix, Idempotency, Request Tracing
✅ Database Triggers, Tax Calculations, Multi-Tenancy Tests

**Phase 1-B: Core Completeness (COMPLETE - 4 tasks)**
✅ Polymorphic Relationships, Contact Management
✅ Quote Acceptance Workflow, Voice Action Execution

**Phase 2: Background Processing (3/4 tasks COMPLETE)**
✅ Task 12: Celery Setup & Configuration (221/221 tests passing)
✅ Task 13: Profitability Rollup Worker (237/237 tests passing)
✅ Task 14: Notification Outbox Worker (252/252 tests passing)

**Test Coverage:** 252/252 passing (100% pass rate)
**See:** dev-docs/analysis/phase-2-5-implementation-roadmap.md for full details

## Current Task

Implement background job to manage voice AI conversation session lifecycle. Currently, `conversation_session` records never expire, leading to database bloat with abandoned conversations. Need Celery task to mark sessions > 24 hours old as expired, generate final summaries from `context_window_json`, archive old sessions to cold storage, and cleanup orphaned `conversation_message` records.

**Priority:** MEDIUM
**Estimated Effort:** 2 days
**Task Spec:** See dev-docs/analysis/phase-2-5-implementation-roadmap.md Task #15
**Design Context:** dev-docs/db-design/aevofab-db-process-v2.6h.md Section 8

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
- **Create implementation plan first** (task-15-session-cleanup-impl-plan.md) before coding
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
     - Example: `backend/tests/test_session_cleanup_fixes.md`

**Test Execution:**
- **Current Baseline:** 252/252 tests passing - DO NOT regress this
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
- **Create new test file:** `backend/tests/test_session_cleanup.py`
- **Test coverage required:**
  - Unit tests for core logic (session expiration logic, summary generation, archival)
  - Integration tests with database (mark expired, cleanup orphaned messages)
  - Edge cases (active sessions not expired, sessions without context, null handling)
  - Tenant isolation verification (multi-tenancy tests)
  - Celery task execution tests (task registration, cron schedule verification)

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
- **Use Alembic migrations** for schema changes (if needed)
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
   - Find your task section (Task 15: Session Expiration & Cleanup)
   - Check off completed deliverables using `- [x]` checkbox format
   - Update any inline status notes or test results
   - If all deliverables complete, task is ✅ COMPLETE
   - If some deliverables incomplete, task is ⚠️ PARTIALLY COMPLETE
   
   **Document 2: phase-1-4-implementation-gap-analysis.md (Historical Gap Tracking)**
   - Find the original gap section (Gap #19: Session Expiration & Pruning)
   - Update the gap status at the top:
     - ✅ **RESOLVED** if all tests pass and implementation 100% complete
     - ⚠️ **PARTIALLY COMPLETE** if fix document created or deliverables incomplete
   - Add "Resolved Date" line if marking RESOLVED
   - Add implementation summary (what was built, files created/modified, test results)
   - Cross-reference to task number (e.g., "See also: Task 15 in phase-2-5-implementation-roadmap.md")
   
   **Both documents must match:**
   - If roadmap task shows incomplete deliverables → gap status = PARTIALLY COMPLETE
   - If roadmap task shows all complete + tests pass → gap status = RESOLVED
   - Follow existing patterns from Phase 1-A/1-B completed tasks (see Gaps #1, #6, #11, #13, #17, etc.)

## Key Files to Review

### Architecture
- `dev-docs/analysis/phase-2-5-implementation-roadmap.md` - **Active task roadmap (Phases 2-5)**
- `dev-docs/architecture-design/mvp-arch.md` - Overall system design
- `dev-docs/db-design/aevofab-db-process-v2.6h.md` - Database operations & schema (Section 8 for session lifecycle)
- `dev-docs/analysis/phase-1-4-implementation-gap-analysis.md` - Historical gap tracking (Gap #19)

### Backend Code
- `backend/app/models/voice_ai.py` - ConversationSession and ConversationMessage models
- `backend/app/models/` - Database models (SQLModel ORM)
- `backend/api/routes/voice.py` - Voice AI endpoints (session creation/management)
- `backend/core/celery_app.py` - Celery configuration (add new task here)
- `backend/tasks/` - Background jobs (create cleanup_sessions.py here)
- `backend/tests/` - Test suite

### Recent Examples (Phase 2 Completed Work)
- **Celery Configuration:** `backend/core/celery_app.py`, `backend/core/config.py` (Redis broker, Beat scheduler)
- **Profitability Rollup:** `backend/tasks/profitability_rollup.py` (Celery task with atomic updates, 239 lines)
- **Notification Outbox:** `backend/tasks/notification_worker.py` (exponential backoff, dead letter queue)
- **Idempotency Cleanup:** `backend/tasks/cleanup_idempotency_keys.py` (scheduled cleanup pattern)
- **Test Patterns:** `backend/tests/test_celery.py` (24 Celery tests), `backend/tests/test_profitability_rollup.py` (16 tests)
- **Documentation:** `dev-docs/analysis/task-12-celery-impl-plan.md`, `task-13-profitability-rollup-impl-plan.md`, `task-14-notification-outbox-impl-plan.md`

## Success Criteria

**MUST COMPLETE ALL BEFORE MARKING GAP AS RESOLVED:**

- [ ] Implementation plan created and approved (task-15-session-cleanup-impl-plan.md)
- [ ] Celery task created: `backend/tasks/cleanup_sessions.py`
- [ ] Mark sessions > 24 hours old as expired (update `status` field)
- [ ] Generate final summary from `context_window_json` (store in session record)
- [ ] Archive sessions to cold storage after 30 days (MVP: mark for archival)
- [ ] Cleanup orphaned `conversation_message` records (messages without valid session)
- [ ] Celery Beat schedule registered (daily at 3 AM)
- [ ] Task registered in `backend/core/celery_app.py` (autodiscovery via imports)
- [ ] Comprehensive test suite created (`backend/tests/test_session_cleanup.py`)
- [ ] **ALL existing tests pass** (no regression from 252/252 baseline)
- [ ] **ALL new tests pass** (zero failures)
- [ ] **Test pass rate: 100%** (X/X passing, 0 failing)
- [ ] Documentation updated with what was delivered
- [ ] Code follows existing patterns and standards

**Gap Status in Analysis Doc:**
- ✅ **RESOLVED** - If all tests pass (implementation + tests 100% complete)
- ⚠️ **PARTIALLY COMPLETE** - If fix document created for failing tests
  - Must include: "Implementation complete, tests require fixes (see test_session_cleanup_fixes.md)"
  - Cannot mark RESOLVED until all tests pass

**If Tests Fail:**
- Create `backend/tests/test_session_cleanup_fixes.md` with concrete fixes for ALL failing tests
- Update gap status to "PARTIALLY COMPLETE" in analysis doc
- Document exact steps to achieve 100% test pass rate
- Include time estimates for each fix

## Questions to Ask

Before starting:
1. Have I read Gap #19 in the gap analysis thoroughly?
2. Have I reviewed the ConversationSession and ConversationMessage models?
3. Do I understand the session lifecycle (active → expired → archived)?
4. What existing code can I reference for patterns (cleanup_idempotency_keys.py)?
5. What tests need to be written?

During implementation:
1. Am I following existing Celery task patterns?
2. Are ALL tests passing (100% pass rate)?
3. Am I documenting as I go?
4. Is this aligned with 80/20 MVP priorities?
5. Am I respecting tenant isolation in cleanup queries?

After implementation:
1. Do I have 100% test pass rate (X/X passing, 0 failing)?
2. If tests fail, have I created a detailed fix document?
3. Have I marked the gap status correctly (RESOLVED vs PARTIALLY COMPLETE)?
4. Can another developer execute my test fixes successfully?

## Example Task Flow

```bash
# 1. Review the task in roadmap
cat dev-docs/analysis/phase-2-5-implementation-roadmap.md | grep -A 30 "Task 15"

# 2. Check original gap for context
cat dev-docs/analysis/phase-1-4-implementation-gap-analysis.md | grep -A 20 "Gap #19"

# 3. Check database models
cat backend/app/models/voice_ai.py | grep -A 30 "ConversationSession"

# 4. Review existing Celery task patterns
cat backend/tasks/cleanup_idempotency_keys.py
cat backend/tasks/profitability_rollup.py

# 5. Run existing tests (baseline: 252 passing)
cd backend && source .venv/bin/activate && pytest tests/ -v

# 6. Create your implementation
# [write code]

# 7. Run tests again (must maintain 100% pass rate)
pytest tests/ -v
```

## Implementation Notes

**Session Lifecycle States:**
- `active` - Conversation is ongoing (< 24 hours old)
- `expired` - Session > 24 hours old, no longer active
- `archived` - Session marked for cold storage (> 30 days old)

**Celery Task Structure (from roadmap):**
```python
# backend/tasks/cleanup_sessions.py

from core.celery_app import celery_app
from celery.schedules import crontab

@celery_app.task(name="expire_old_sessions")
def expire_old_sessions():
    """
    Mark conversation sessions > 24 hours old as expired.
    Generate final summary from context_window_json.
    """
    pass

@celery_app.task(name="archive_old_sessions")
def archive_old_sessions():
    """
    Mark sessions > 30 days old for archival to cold storage.
    MVP: Just mark as archived, actual S3 upload deferred to post-MVP.
    """
    pass

@celery_app.task(name="cleanup_orphaned_messages")
def cleanup_orphaned_messages():
    """
    Delete conversation_message records without valid session_id.
    Safety check: Only delete messages > 7 days old.
    """
    pass

# Register periodic tasks
@celery_app.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):
    # Run daily at 3 AM
    sender.add_periodic_task(
        crontab(hour=3, minute=0),
        expire_old_sessions.s(),
    )
    sender.add_periodic_task(
        crontab(hour=3, minute=30),
        archive_old_sessions.s(),
    )
    sender.add_periodic_task(
        crontab(hour=4, minute=0),
        cleanup_orphaned_messages.s(),
    )
```

**Summary Generation Logic:**
```python
# Extract key entities from context_window_json
context = session.context_window_json or {}
summary_parts = []

if "active_customer_id" in context:
    summary_parts.append(f"Customer: {context['active_customer_id']}")
if "active_quote_id" in context:
    summary_parts.append(f"Quote: {context['active_quote_id']}")
if "active_job_id" in context:
    summary_parts.append(f"Job: {context['active_job_id']}")

# Count messages
message_count = db.query(ConversationMessage).filter_by(session_id=session.id).count()
summary_parts.append(f"{message_count} messages")

session.final_summary = ", ".join(summary_parts)
```

**Tenant Isolation:**
- All cleanup queries MUST filter by `tenant_id`
- Use session-level locking to prevent race conditions
- Test with multi-tenant data to verify isolation

**Cost Awareness:**
- This task adds NO additional infrastructure cost
- Uses existing Celery worker and Beat scheduler
- Database cleanup reduces storage costs over time
- Within $643 MVP budget

**Phase 2 Completion:**
- This is the LAST task in Phase 2
- Upon completion, Phase 2 is ✅ COMPLETE
- All 4 background processing tasks will be done:
  - Task 12: Celery Setup ✅
  - Task 13: Profitability Rollup ✅
  - Task 14: Notification Outbox ✅
  - Task 15: Session Cleanup ← THIS TASK

## Notes

- **MVP Focus:** Follow dev-docs/product-requirements/mvp-prd.md for scope
- **80/20 Rule:** See .roo/rules-mvp-builder/80-20-prioritization.md
- **Mike the Solo Contractor:** Our primary persona - keep it simple!
- **No Enterprise Features:** Multi-trade, complex scheduling, etc. are out of scope
- **Cold Storage Archival:** MVP implementation just marks sessions as `archived`. Actual S3 upload deferred to post-MVP (Phase 4+).
- **Orphaned Message Safety:** Only delete messages > 7 days old to prevent accidental data loss from race conditions.
```
