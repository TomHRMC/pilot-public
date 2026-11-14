# Task Prompt: Phase 2, Task #14 - Notification Outbox Worker

```
Task: Phase 2, Task #14 - Notification Outbox Worker
Reference: dev-docs/analysis/phase-2-5-implementation-roadmap.md Task #14
(Original: Gap #26 in phase-1-4-implementation-gap-analysis.md)

## Context

We're building AevoFab AI, an AI-powered SaaS platform for electrical contractors with voice-controlled quoting and QuickBooks integration. Following the 80/20 rule to reach MVP quickly.

## Completed So Far

**Phase 1-A: Critical Blockers (COMPLETE - 7 tasks)**
✅ Test Endpoints, Tenant ID Fix, Idempotency, Request Tracing
✅ Database Triggers, Tax Calculations, Multi-Tenancy Tests

**Phase 1-B: Core Completeness (COMPLETE - 4 tasks)**
✅ Polymorphic Relationships, Contact Management
✅ Quote Acceptance Workflow, Voice Action Execution

**Phase 2: Background Processing (IN PROGRESS - 2/4 tasks)**
✅ Task 12: Celery Setup & Configuration (COMPLETE - 221/221 tests passing)
✅ Task 13: Profitability Rollup Worker (COMPLETE - 237/237 tests passing)

**Test Coverage:** 237/237 passing (100% pass rate)
**See:** dev-docs/analysis/phase-2-5-implementation-roadmap.md for full details

## Current Task

Implement a reliable notification delivery system using Celery background workers to send email and SMS notifications via SendGrid and Twilio. The system must handle quote acceptances, customer communications, and system alerts with automatic retry logic and delivery tracking.

**Priority:** BLOCKER (customer communications essential for MVP)
**Estimated Effort:** 5 days
**Task Spec:** See dev-docs/analysis/phase-2-5-implementation-roadmap.md Task #14
**Design Context:** dev-docs/db-design/aevofab-db-process-v2.6h.md

## Architecture Overview

```
API creates notification_outbox record (status=pending)
   ↓
Celery worker polls every 30s (or triggered immediately)
   ↓
Sends via SendGrid (email) or Twilio (SMS)
   ↓
Updates notification_delivery_attempt with result
   ↓
Exponential backoff on failure (1m, 5m, 15m, 1h, 6h)
   ↓
Dead letter queue after 5 failures
```

**Existing Database Tables:**
- `notification_outbox` - Queue of pending notifications
- `notification_delivery_attempt` - Delivery attempt tracking (table exists but may need verification)

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
- **Create implementation plan first** (task-14-notification-outbox-impl-plan.md) before coding
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
     - Example: `backend/tests/test_notification_outbox_fixes.md`

**Test Execution:**
- **Current Baseline:** 237/237 tests passing - DO NOT regress this
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
- **Create new test file:** `backend/tests/test_notification_outbox.py`
- **Test coverage required:**
  - Unit tests for core logic (SendGrid/Twilio integration, retry logic)
  - Integration tests for Celery task execution
  - Error handling and edge cases (provider failures, network errors)
  - Tenant isolation verification (multi-tenancy tests)
  - Exponential backoff verification
  - Dead letter queue behavior
  - Template rendering tests

**Test Data Management:**
- **Reference data seeding:** Review `backend/migrations/seed_test_data.py` for existing seed patterns
  - Seed reference tables (notification types, template types) in migrations
  - Use fixtures in conftest.py for test-specific data (tenants, users, etc.)
- **Test data creation:** Create necessary test data in fixtures or test setup
  - Follow existing patterns in `conftest.py` (e.g., `test_tenant`, `test_customer`)
  - Use factory patterns for complex entities (see existing test files)
- **Test data cleanup:** Database automatically rolls back after each test (session scope)
  - conftest.py uses `pytest` fixtures with `db_session` that auto-rollback
  - No manual cleanup needed - each test runs in isolated transaction
  - Exception: Integration tests that commit - must explicitly clean up

### 3. Code Standards
- **Follow existing patterns** - Check similar implementations first (e.g., profitability_rollup.py)
- **Type hints required** - Use AuthenticatedUser, not User
- **Error handling** - RFC 7807 format (see existing routes)
- **Docstrings required** - Document all functions/classes
- **No feature creep** - Strictly follow 80/20 MVP prioritization
- **Phase 2+ Cost Awareness** - For infrastructure tasks (Celery, Redis, integrations), respect $1k/mo budget cap (see infrastructure-constraints.md)

### 4. Database Standards
- **DO NOT hallucinate schema** - Always read backend/app/models/*.py first
- **Review notification_outbox and notification_delivery_attempt models** in backend/app/models/system.py
- **Use Alembic migrations** for schema changes (if needed)
- **Respect tenant isolation** - All queries filter by tenant_id
- **Follow ORM patterns** - Use SQLModel/SQLAlchemy correctly

### 5. Workflow
1. **Read the task roadmap** to understand the requirements
2. **Review design specs** (db-process-v2.6h.md, mvp-arch.md)
3. **Review existing models** (backend/app/models/system.py for notification tables)
4. **Create implementation plan** document with detailed tasks
5. **Get approval** on the plan before coding
6. **Implement** following the plan step-by-step
7. **Write tests** alongside implementation
8. **Run all tests** - Must pass before completion
9. **Update documentation** - **BOTH documents MUST be updated:**
   
   **Document 1: phase-2-5-implementation-roadmap.md (Active Task Tracking)**
   - Find Task 14 section (lines 198-231)
   - Check off completed deliverables using `- [x]` checkbox format
   - Update any inline status notes or test results
   - If all deliverables complete, task is ✅ COMPLETE
   - If some deliverables incomplete, task is ⚠️ PARTIALLY COMPLETE
   
   **Document 2: phase-1-4-implementation-gap-analysis.md (Historical Gap Tracking)**
   - Find Gap #26 section (lines 567-571)
   - Update the gap status at the top:
     - ✅ **RESOLVED** if all tests pass and implementation 100% complete
     - ⚠️ **PARTIALLY COMPLETE** if fix document created or deliverables incomplete
   - Add "Resolved Date" line if marking RESOLVED
   - Add implementation summary (what was built, files created/modified, test results)
   - Cross-reference to task number (e.g., "See also: Task 14 in phase-2-5-implementation-roadmap.md")
   
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
- `backend/app/models/system.py` - **notification_outbox and notification_delivery_attempt models**
- `backend/core/celery_app.py` - Celery configuration (for task registration)
- `backend/core/config.py` - Application configuration (add SendGrid/Twilio settings)
- `backend/tasks/` - Background jobs (create notification_worker.py here)
- `backend/tests/` - Test suite

### Recent Examples (Phase 1 & 2 Completed Work)
- **Celery Setup:** `backend/core/celery_app.py`, `backend/tests/test_celery.py` (24 tests)
- **Profitability Rollup:** `backend/tasks/profitability_rollup.py`, `backend/tests/test_profitability_rollup.py` (16 tests)
- **Middleware:** `backend/core/idempotency.py`, `backend/core/middleware.py` (Request ID)
- **Database Triggers:** `backend/migrations/versions/2026_03_17_1451-*.py` (Quote/CO totals)
- **Tax Calculations:** `backend/core/tax_calculation.py` (IRS-compliant rounding)
- **Voice Actions:** `backend/services/voice_action_router.py` (10 MVP handlers)
- **Test Patterns:** `backend/tests/test_voice_actions.py`, `backend/tests/test_multi_tenancy_isolation.py`

## Success Criteria

**MUST COMPLETE ALL BEFORE MARKING GAP AS RESOLVED:**

- [ ] Implementation plan created and approved (task-14-notification-outbox-impl-plan.md)
- [ ] SendGrid email integration implemented and tested
- [ ] Twilio SMS integration implemented and tested
- [ ] Celery task `send_notification` created in backend/tasks/notification_worker.py
- [ ] Exponential backoff logic implemented (1m, 5m, 15m, 1h, 6h)
- [ ] Dead letter queue handling after 5 failures
- [ ] Template rendering system for email/SMS bodies
- [ ] notification_delivery_attempt tracking implemented
- [ ] Celery Beat scheduler configured (if using polling) OR immediate task triggering
- [ ] **ALL existing tests pass** (237/237 - no regression)
- [ ] **ALL new tests pass** (zero failures)
- [ ] **Test pass rate: 100%** (X/X passing, 0 failing)
- [ ] Documentation updated with what was delivered
- [ ] Code follows existing patterns and standards
- [ ] Cost impact documented (SendGrid/Twilio API costs estimated)

**Gap Status in Analysis Doc:**
- ✅ **RESOLVED** - If all tests pass (implementation + tests 100% complete)
- ⚠️ **PARTIALLY COMPLETE** - If fix document created for failing tests
  - Must include: "Implementation complete, tests require fixes (see test_notification_outbox_fixes.md)"
  - Cannot mark RESOLVED until all tests pass

**If Tests Fail:**
- Create `backend/tests/test_notification_outbox_fixes.md` with concrete fixes for ALL failing tests
- Update gap status to "PARTIALLY COMPLETE" in analysis doc
- Document exact steps to achieve 100% test pass rate
- Include time estimates for each fix

## Deliverables Checklist

From roadmap Task #14:
- [ ] SendGrid integration (email)
- [ ] Twilio integration (SMS)
- [ ] Exponential backoff logic (1m, 5m, 15m, 1h, 6h)
- [ ] Dead letter queue after 5 failures
- [ ] Template rendering system

**Success Criteria from Roadmap:**
- [ ] Quote acceptance triggers email within 1 minute
- [ ] Failed sends retry automatically
- [ ] Delivery status visible in admin UI (or queryable via API)

## Implementation Guidance

### Core Components to Build

1. **backend/tasks/notification_worker.py** - Main Celery task
   - `send_notification(notification_outbox_id: UUID)` - Process single notification
   - `poll_pending_notifications()` - Periodic polling task (optional if using immediate triggers)
   - Helper functions for exponential backoff calculation

2. **backend/services/email_service.py** - SendGrid wrapper
   - `send_email(to: str, subject: str, body: str, template_id: str | None)`
   - Error handling and retry logic
   - API key management from config

3. **backend/services/sms_service.py** - Twilio wrapper
   - `send_sms(to: str, body: str)`
   - Error handling and retry logic
   - Account SID and auth token from config

4. **backend/services/template_renderer.py** - Template system
   - `render_template(template_name: str, context: dict) -> str`
   - Support for Jinja2 or similar templating
   - Email and SMS template variants

5. **backend/core/config.py** - Configuration updates
   - SENDGRID_API_KEY
   - TWILIO_ACCOUNT_SID
   - TWILIO_AUTH_TOKEN
   - TWILIO_FROM_NUMBER
   - Notification retry configuration

6. **backend/.env.example** - Environment variable documentation
   - Add SendGrid and Twilio configuration

7. **backend/tests/test_notification_outbox.py** - Comprehensive tests
   - Test SendGrid email sending (mocked)
   - Test Twilio SMS sending (mocked)
   - Test exponential backoff calculation
   - Test dead letter queue behavior
   - Test template rendering
   - Test tenant isolation
   - Test retry logic on provider failures

### Retry Logic Pattern

```python
# Exponential backoff schedule
RETRY_DELAYS = [
    60,      # 1 minute
    300,     # 5 minutes
    900,     # 15 minutes
    3600,    # 1 hour
    21600,   # 6 hours
]

def calculate_next_retry(attempt_count: int) -> datetime | None:
    if attempt_count >= len(RETRY_DELAYS):
        return None  # Dead letter - no more retries
    
    delay_seconds = RETRY_DELAYS[attempt_count]
    return datetime.utcnow() + timedelta(seconds=delay_seconds)
```

### Cost Considerations

**SendGrid Pricing:**
- Free tier: 100 emails/day (sufficient for MVP testing)
- Essentials: $19.95/mo for 50k emails/month
- **MVP Budget Impact:** ~$20/mo (within $643 budget)

**Twilio Pricing:**
- SMS: $0.0079/message (US)
- 100 SMS/day = ~$24/mo
- **MVP Budget Impact:** ~$24/mo (within $643 budget)

**Total Notification Cost:** ~$44/mo (stays within infrastructure constraints)

## Questions to Ask

Before starting:
1. Have I read the gap analysis entry thoroughly?
2. Have I reviewed the notification_outbox and notification_delivery_attempt models?
3. Do I understand the exponential backoff requirements?
4. What existing code can I reference for patterns? (profitability_rollup.py, celery_app.py)
5. What tests need to be written?

During implementation:
1. Am I following existing Celery task patterns from profitability_rollup.py?
2. Are ALL tests passing (100% pass rate)?
3. Am I documenting as I go?
4. Is this aligned with 80/20 MVP priorities?
5. Am I properly mocking external API calls in tests?

After implementation:
1. Do I have 100% test pass rate (X/X passing, 0 failing)?
2. If tests fail, have I created a detailed fix document?
3. Have I marked the gap status correctly (RESOLVED vs PARTIALLY COMPLETE)?
4. Can another developer execute my test fixes successfully?
5. Have I documented the cost impact of SendGrid/Twilio?

## Example Task Flow

```bash
# 1. Review the task in roadmap
cat dev-docs/analysis/phase-2-5-implementation-roadmap.md | grep -A 35 "Task 14"

# 2. Check original gap for context
cat dev-docs/analysis/phase-1-4-implementation-gap-analysis.md | grep -A 10 "Gap #26"

# 3. Check notification models
cat backend/app/models/system.py | grep -A 30 "notification_outbox"

# 4. Review existing Celery patterns
cat backend/tasks/profitability_rollup.py

# 5. Run existing tests (baseline: 237 passing)
cd backend && source .venv/bin/activate && pytest tests/ -v

# 6. Create your implementation
# [write code]

# 7. Run tests again (must maintain 100% pass rate)
pytest tests/ -v
```

## Notes

- **MVP Focus:** Follow dev-docs/product-requirements/mvp-prd.md for scope
- **80/20 Rule:** See .roo/rules-mvp-builder/80-20-prioritization.md
- **Mike the Solo Contractor:** Our primary persona - keep it simple!
- **No Enterprise Features:** Advanced notification analytics, A/B testing, etc. are out of scope
- **Infrastructure Constraints:** $1k/mo budget cap - SendGrid/Twilio costs must fit within this
- **Security:** Ensure API keys are never committed to git (use .env)
- **Testing:** Mock external API calls (SendGrid/Twilio) - do not make real API calls in tests
- **Template System:** Keep MVP simple - plain text emails/SMS initially, HTML later if needed
- **Immediate Trigger Option:** Consider triggering notification task immediately when notification_outbox record created (instead of polling every 30s) for better user experience
```
