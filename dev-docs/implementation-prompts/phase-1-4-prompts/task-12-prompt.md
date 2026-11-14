# Task 12 Prompt: Celery Setup & Configuration

Task: Phase 2, Task #12 - Celery Setup & Configuration
Reference: dev-docs/analysis/phase-2-5-implementation-roadmap.md Task #12
(Original: Gap #21 in phase-1-4-implementation-gap-analysis.md)

## Context

We're building AevoFab AI, an AI-powered SaaS platform for electrical contractors with voice-controlled quoting and QuickBooks integration. Following the 80/20 rule to reach MVP quickly.

## Completed So Far

**Phase 1-A: Critical Blockers (COMPLETE - 7 tasks)**
✅ Test Endpoints, Tenant ID Fix, Idempotency, Request Tracing
✅ Database Triggers, Tax Calculations, Multi-Tenancy Tests

**Phase 1-B: Core Completeness (COMPLETE - 4 tasks)**
✅ Polymorphic Relationships, Contact Management
✅ Quote Acceptance Workflow, Voice Action Execution

**Test Coverage:** 197/197 passing (100% pass rate)
**See:** dev-docs/analysis/phase-2-5-implementation-roadmap.md for full details

## Current Task

Set up Celery distributed task queue infrastructure to enable background processing. This is a **CRITICAL BLOCKER** for Phase 2 because:
- Profitability rollup worker needs background jobs (Task 13)
- Notification outbox worker needs async processing (Task 14)
- Session cleanup needs scheduled cron jobs (Task 15)
- Real-time features cannot function without async task execution

Currently, `backend/core/celery_app.py` exists but lacks proper broker configuration, task autodiscovery, and health monitoring.

**Priority:** CRITICAL (BLOCKER)
**Estimated Effort:** 3 days
**Task Spec:** See dev-docs/analysis/phase-2-5-implementation-roadmap.md Task #12
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
- **Create implementation plan first** (task-12-celery-impl-plan.md) before coding
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
     - Example: `backend/tests/test_celery_fixes.md`

**Test Execution:**
- **Current Baseline:** 197/197 tests passing - DO NOT regress this
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
- **Create new test file:** `backend/tests/test_celery.py`
- **Test coverage required:**
  - Unit tests for Celery app configuration
  - Integration tests for task autodiscovery
  - Health monitoring endpoint tests
  - Task execution tests (simple test task)
  - Redis connection tests (local dev)

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
- **Type hints required** - Use proper typing for task signatures
- **Error handling** - RFC 7807 format (see existing routes)
- **Docstrings required** - Document all functions/classes
- **No feature creep** - Strictly follow 80/20 MVP prioritization
- **Phase 2 Cost Awareness** - Respect $1k/mo budget cap:
  - **Redis:** Use `cache.t4g.micro` for ElastiCache (MVP tier)
  - **Local Dev:** Use Docker Redis container (no cloud cost)
  - **SQS:** Defer to production deployment (AWS free tier: 1M requests/month)
  - **Workers:** Single ECS Fargate task (0.25 vCPU) for MVP
  - See `.roo/rules-aevofab-architect/infrastructure-constraints.md` for details

### 4. Database Standards
- **DO NOT hallucinate schema** - Always read backend/app/models/*.py first
- **Use Alembic migrations** for schema changes (if needed for task state tracking)
- **Respect tenant isolation** - All queries filter by tenant_id
- **Follow ORM patterns** - Use SQLModel/SQLAlchemy correctly

### 5. Workflow
1. **Read the task roadmap** to understand the requirements
2. **Review design specs** (db-process-v2.6h.md, mvp-arch.md, infrastructure-constraints.md)
3. **Create implementation plan** document with detailed tasks
4. **Get approval** on the plan before coding
5. **Implement** following the plan step-by-step
6. **Write tests** alongside implementation
7. **Run all tests** - Must pass before completion
8. **Update documentation** - **BOTH documents MUST be updated:**
   
   **Document 1: phase-2-5-implementation-roadmap.md (Active Task Tracking)**
   - Find Task 12 section (lines 83-106)
   - Check off completed deliverables using `- [x]` checkbox format
   - Update any inline status notes or test results
   - If all deliverables complete, task is ✅ COMPLETE
   - If some deliverables incomplete, task is ⚠️ PARTIALLY COMPLETE
   
   **Document 2: phase-1-4-implementation-gap-analysis.md (Historical Gap Tracking)**
   - Find Gap #21: Celery Configuration section
   - Update the gap status at the top:
     - ✅ **RESOLVED** if all tests pass and implementation 100% complete
     - ⚠️ **PARTIALLY COMPLETE** if fix document created or deliverables incomplete
   - Add "Resolved Date" line if marking RESOLVED
   - Add implementation summary (what was built, files created/modified, test results)
   - Cross-reference to Task 12 (e.g., "See also: Task 12 in phase-2-5-implementation-roadmap.md")
   
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
- `.roo/rules-aevofab-architect/infrastructure-constraints.md` - Cost limits ($1k/mo cap)
- `.roo/rules-aevofab-architect/scaling-logic.md` - When/how to scale resources

### Backend Code
- `backend/core/celery_app.py` - **PRIMARY FILE TO MODIFY** - Current Celery stub
- `backend/core/config.py` - Add Celery settings (broker URL, result backend)
- `backend/tasks/` - Directory for task definitions (autodiscovery target)
- `backend/tasks/test_task.py` - Example task for testing
- `backend/tasks/cleanup_idempotency_keys.py` - Existing scheduled task example
- `docker-compose.yml` - Add Celery worker + beat services
- `backend/tests/` - Test suite

### Recent Examples (Phase 1 Completed Work)
- **Middleware:** `backend/core/idempotency.py`, `backend/core/middleware.py` (Request ID)
- **Database Triggers:** `backend/migrations/versions/2026_03_17_1451-*.py` (Quote/CO totals)
- **Tax Calculations:** `backend/core/tax_calculation.py` (IRS-compliant rounding)
- **Voice Actions:** `backend/services/voice_action_router.py` (10 MVP handlers)
- **Polymorphic Relations:** `backend/api/routes/contacts.py`, `addresses.py` (800+ lines each)
- **Test Patterns:** `backend/tests/test_voice_actions.py`, `test_multi_tenancy_isolation.py`
- **Documentation:** `dev-docs/analysis/gap-*-remediation-plan.md` (10+ examples)

## Success Criteria

**MUST COMPLETE ALL BEFORE MARKING GAP AS RESOLVED:**

- [ ] Implementation plan created and approved (`task-12-celery-impl-plan.md`)
- [ ] Implementation complete per plan
- [ ] **ALL existing tests pass** (no regression from 197/197 baseline)
- [ ] **ALL new tests pass** (zero failures)
- [ ] **Test pass rate: 100%** (X/X passing, 0 failing)
- [ ] Redis broker connection works (local dev environment)
- [ ] Task autodiscovery finds tasks in `backend/tasks/`
- [ ] Celery Beat scheduler configured for cron jobs
- [ ] Worker health monitoring endpoint responds
- [ ] Docker Compose includes worker + beat services
- [ ] Configuration supports SQS broker fallback (production ready)
- [ ] Documentation updated with what was delivered
- [ ] Code follows existing patterns and standards

**Task Deliverables (from Roadmap):**
- [ ] Redis broker connection (local dev)
- [ ] SQS broker fallback (production)
- [ ] Task autodiscovery from `backend/tasks/`
- [ ] Celery Beat scheduler for cron jobs
- [ ] Worker health monitoring endpoint

**Gap Status in Analysis Doc:**
- ✅ **RESOLVED** - If all tests pass (implementation + tests 100% complete)
- ⚠️ **PARTIALLY COMPLETE** - If fix document created for failing tests
  - Must include: "Implementation complete, tests require fixes (see test_celery_fixes.md)"
  - Cannot mark RESOLVED until all tests pass

**If Tests Fail:**
- Create `backend/tests/test_celery_fixes.md` with concrete fixes for ALL failing tests
- Update gap status to "PARTIALLY COMPLETE" in analysis doc
- Document exact steps to achieve 100% test pass rate
- Include time estimates for each fix

**Verification Commands:**
```bash
# Start Celery worker locally
cd backend && source .venv/bin/activate
celery -A core.celery_app worker --loglevel=info

# Verify task registration
celery -A core.celery_app inspect registered

# Start Celery Beat scheduler
celery -A core.celery_app beat --loglevel=info

# Run health check (if endpoint created)
curl http://localhost:8000/health/celery
```

## Questions to Ask

Before starting:
1. Have I read Gap #21 in the gap analysis document?
2. Have I reviewed the existing `backend/core/celery_app.py` file?
3. Do I understand the infrastructure cost constraints ($1k/mo cap)?
4. What existing task files are in `backend/tasks/` for autodiscovery testing?
5. What tests need to be written for Celery configuration?

During implementation:
1. Am I following existing patterns from Phase 1 work?
2. Are ALL tests passing (100% pass rate maintained)?
3. Am I documenting as I go?
4. Is my Celery configuration production-ready (SQS fallback)?
5. Does the health endpoint provide useful monitoring data?

After implementation:
1. Do I have 100% test pass rate (X/X passing, 0 failing)?
2. Can I successfully start a Celery worker locally?
3. Does task autodiscovery find all tasks in `backend/tasks/`?
4. Have I marked the gap status correctly (RESOLVED vs PARTIALLY COMPLETE)?
5. Did I update BOTH documentation files (roadmap + gap analysis)?

## Example Task Flow

```bash
# 1. Review the task in roadmap
cat dev-docs/analysis/phase-2-5-implementation-roadmap.md | grep -A 30 "Task 12"

# 2. Check original gap for context
cat dev-docs/analysis/phase-1-4-implementation-gap-analysis.md | grep -A 20 "Gap #21"

# 3. Review existing Celery stub
cat backend/core/celery_app.py

# 4. Check existing task files
ls -la backend/tasks/

# 5. Review infrastructure constraints
cat .roo/rules-aevofab-architect/infrastructure-constraints.md

# 6. Run existing tests (baseline: 197 passing)
cd backend && source .venv/bin/activate && pytest tests/ -v

# 7. Create your implementation
# [write code for celery_app.py, config.py, docker-compose.yml]

# 8. Test Celery worker startup
celery -A core.celery_app worker --loglevel=info

# 9. Verify task registration
celery -A core.celery_app inspect registered

# 10. Run tests again (must maintain 100% pass rate)
pytest tests/ -v

# 11. Update documentation (both roadmap and gap analysis)
```

## Notes

- **MVP Focus:** Follow dev-docs/product-requirements/mvp-prd.md for scope
- **80/20 Rule:** See .roo/rules-mvp-builder/80-20-prioritization.md
- **Cost Constraints:** Phase 2 tasks must respect $1k/mo infrastructure budget
- **Infrastructure Setup:**
  - **Local Dev:** Use Docker Redis container (free)
  - **Production:** ElastiCache Redis `cache.t4g.micro` (~$12/mo)
  - **Workers:** Single ECS Fargate task 0.25 vCPU (~$7/mo)
  - **Total Phase 2 Cost Impact:** ~$19/mo (within $643 MVP budget)
- **Mike the Solo Contractor:** Our primary persona - keep it simple!
- **No Enterprise Features:** Focus on MVP core functionality only
- **Dependency Note:** Tasks 13, 14, 15 all depend on Task 12 completion
- **Production Readiness:** SQS broker configuration enables AWS deployment without Redis costs in production (optional optimization)

## Infrastructure Context

From `.roo/rules-aevofab-architect/infrastructure-constraints.md`:

### Cost Impact Analysis
- **ElastiCache Redis** (cache.t4g.micro): ~$12/mo
- **ECS Fargate Worker** (0.25 vCPU, 0.5GB): ~$7/mo
- **SQS** (optional, 1M requests/mo): Free tier
- **Total Phase 2 Addition**: ~$19/mo

### Scaling Path
- **100 users:** 1 worker (0.25 vCPU) - sufficient for MVP
- **500 users:** 2 workers (0.5 vCPU total) - incremental scaling
- **1,000 users:** 4 workers (1.0 vCPU total) - still cost-effective

See `scaling-logic.md` for when to scale Celery workers based on queue depth metrics.
