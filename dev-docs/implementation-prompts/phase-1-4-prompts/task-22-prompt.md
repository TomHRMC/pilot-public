# Next Task Prompt

```
Task: Phase 4, Task #22 - Rate Limiting
Reference: dev-docs/analysis/phase-4-5-implementation-roadmap.md Task #22
(Original: Gap #42 in phase-1-4-implementation-gap-analysis.md)

## Context

We're building AevoFab AI, an AI-powered SaaS platform for electrical contractors with voice-controlled quoting and QuickBooks integration. Following the 80/20 rule to reach MVP quickly.

## Completed So Far

**Phase 1-A: Critical Blockers (COMPLETE - 7 tasks)**
✅ Test Endpoints, Tenant ID Fix, Idempotency, Request Tracing
✅ Database Triggers, Tax Calculations, Multi-Tenancy Tests

**Phase 1-B: Core Completeness (COMPLETE - 4 tasks)**
✅ Polymorphic Relationships, Contact Management
✅ Quote Acceptance Workflow, Voice Action Execution

**Phase 2: Background Processing Infrastructure (COMPLETE - 4 tasks)**
✅ Celery Setup & Configuration (Redis/SQS broker, Beat scheduler)
✅ Profitability Rollup Worker (16 tests, real-time job cost tracking)
✅ Notification Outbox Worker (Email verified with SendGrid, SMS deferred)
✅ Session Expiration & Cleanup (20 tests, memory leak prevention)

**Phase 3: QuickBooks Integration (COMPLETE - 4 tasks)**
✅ OAuth 2.0 Flow & Hybrid Schema Refactoring (100% functional)
✅ Sync Mapping & Upsert Logic (27 tests, bidirectional sync)
✅ Conflict Detection & Resolution (15 tests, 3 resolution strategies)
✅ Webhook Handler (13 tests, Cloud Events format)

**Phase 4: Enterprise Hardening (IN PROGRESS - 2/4 tasks complete)**
✅ Task 20: Audit Event Logging (20 tests, database-level enforcement)
✅ Task 21: RBAC Permission System (40 tests, 4 default roles, 38+ routes protected)
🔴 Task 22: Rate Limiting (CURRENT TASK)
⏳ Task 23: Integration Test Suite

**Test Coverage:** 398/398 passing (100% pass rate)
**See:** dev-docs/analysis/phase-4-5-implementation-roadmap.md for full details

## Current Task

Implement API rate limiting to protect against abuse and DDoS attacks. The system must enforce tenant-based limits (not IP-based) using Redis as the storage backend. Rate limits should be tier-aware to support different subscription plans.

**Priority:** HIGH (DDoS protection, cost control)
**Estimated Effort:** 2-3 days
**Task Spec:** See dev-docs/analysis/phase-4-5-implementation-roadmap.md Task #22 (lines 492-517)
**Design Context:** dev-docs/db-design/aevofab-db-process-v2.6h.md

## Requirements

### 1. Documentation Standards
- **New docs go in dev-docs/** organized by topic:
  - `analysis/` - Gap analysis, remediation plans, implementation plans
  - `architecture-design/` - System architecture docs
  - `db-design/` - Database schema and process docs
  - `product-requirements/` - PRD and user stories
  - `testing-support/` - Test guides and examples
  - `api-guides/` - API usage documentation
- **Always reference the authoritative design docs:**
  - `dev-docs/analysis/phase-4-5-implementation-roadmap.md` - **Active task roadmap (Phases 4-5)**
  - `dev-docs/db-design/aevofab-db-process-v2.6h.md` - Database operations & schema
  - `dev-docs/architecture-design/mvp-arch.md` - System architecture
  - `dev-docs/analysis/phase-1-4-implementation-gap-analysis.md` - Historical gap tracking
  - `.roo/rules-aevofab-architect/infrastructure-constraints.md` - Cost limits ($1k/mo cap)
  - `.roo/rules-aevofab-architect/scaling-logic.md` - When/how to scale resources
- **Create implementation plan first** (task-22-rate-limiting-impl-plan.md) before coding
- **Update implementation roadmap** when marking tasks complete

### 2. Testing Standards (CRITICAL FOR MVP)

**⚠️ ZERO FAILING TESTS POLICY:**
- **ALL tests MUST pass before marking a gap as RESOLVED**
- **NO exceptions** - MVP requires 100% test pass rate
- If tests fail after implementation, after up to 10 attempts to resolve, you have TWO options:
  1. **Fix immediately** (preferred for simple fixes)
  2. **Create detailed fix document** (for complex test issues)
     - Document ALL failing tests with concrete, actionable fixes
     - Mark gap as "PARTIALLY COMPLETE" not "RESOLVED" in analysis doc
     - Include estimated time to fix each test
     - Provide step-by-step fix instructions
     - Example: `dev-docs/testing-support/task-22-test_rate_limiting_fixes.md`

**Test Execution:**
- **Current Baseline:** 398/398 tests passing - DO NOT regress this
- **Tests are MANDATORY** - No code without tests
- **Test Configuration Files:**
  - **pytest.ini:** Default flags (`-v`, `--strict-markers`, `--tb=short`, `-ra`)
  - **.coveragerc:** Coverage settings (covers `api/`, `app/`, `core/`, `services/`, `tasks/`, branch coverage, omits `tests/` and `alembic/`)
- **Run existing tests first:** (this ensures that you validate the total number of tests and that they are all passing)
  - **DEFAULT (recommended):** `cd backend && source .venv/bin/activate && pytest --ignore=tests/integration/ tests/`
    - Excludes integration tests that trigger SendGrid emails (daily limit applies)
    - Faster execution for development workflow
  - **With coverage:** `cd backend && source .venv/bin/activate && pytest --cov=. --ignore=tests/integration/ tests/`
    - Shows code coverage report for all source code (api/, app/, core/, services/, tasks/)
    - Branch coverage enabled, shows missing lines
  - **All tests (including integration):** `cd backend && source .venv/bin/activate && pytest tests/`
    - ⚠️ Only run when needed - fires SendGrid emails (limited daily quota)
  - **Concise output:** `cd backend && source .venv/bin/activate && pytest --ignore=tests/integration/ tests/ 2>&1 | grep -E "(passed|failed|===)" | tail -5`
- **All existing tests must pass** - Baseline must not regress
- **All new tests must pass** - No failing tests allowed

**Test Development:**
- **BEFORE writing tests:** Review `backend/tests/conftest.py` to understand existing fixtures
  - Use `pytest --fixtures` to see all available fixtures
  - Reuse existing fixtures (e.g., `db_session`, `test_tenant`, `client`) instead of creating duplicates
  - Match fixture naming conventions and patterns from conftest.py
  - Example: Use `db_session` not `db`, use `test_tenant` not `tenant`
- **Create new test file:** `backend/tests/test_rate_limiting.py`
- **Test coverage required:**
  - Unit tests for rate limit logic (token bucket algorithm)
  - Integration tests for API endpoints
  - Error handling and edge cases (429 responses)
  - Tenant isolation verification (limits apply per tenant)
  - Rate limit headers verification
  - Limit reset verification

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
- **Phase 4 Cost Awareness** - Respect $1k/mo budget cap (see infrastructure-constraints.md)

### 4. Database Standards
- **DO NOT hallucinate schema** - Always read backend/app/models/*.py first
- **JSON Schema as Source of Truth** - Models implement the schema in `dev-docs/db-design/pilot-db-schema-v2.6h.json`
  - **Before schema changes:** Review JSON schema to understand current structure and relationships
  - **After schema changes:** Update BOTH the SQLModel code AND the JSON schema file
  - **For questions:** JSON schema provides authoritative table/column definitions
  - JSON schema must stay synchronized with actual models (single source of truth)
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
8. **Update documentation** - **ALL THREE documents MUST be updated (with different detail levels):**
   
   **Document 1: phase-4-5-implementation-roadmap.md (Current Active Roadmap) - FULL DETAILS**
   - ✅ **This document gets FULL implementation details**
   - Find your task section (e.g., "Task 22: Rate Limiting")
   - Check off completed deliverables using `- [x]` checkbox format
   - Add "Status: ✅ COMPLETE (YYYY-MM-DD)" at top of task section
   - Add "Test Results:" line showing X/X tests passing
   - Include ALL implementation details:
     - Files created/modified with line counts
     - Code snippets showing key implementations
     - Test coverage breakdown
     - Integration notes and verification steps
     - Any deferred work or future enhancements
   
   **Document 2: phase-2-5-implementation-roadmap.md (Historical Roadmap) - SUMMARY ONLY**
   - ⚠️ **This document gets HIGH-LEVEL summary ONLY (prevent bloat)**
   - Find the corresponding task section (same task number)
   - Mark task as ✅ COMPLETE with completion date
   - Add brief summary (2-3 sentences maximum):
     - "Completed YYYY-MM-DD. Implemented [core feature]. X/X tests passing."
   - **DO NOT include:** Code snippets, detailed file lists, or implementation notes
   - **DO include:** Test count if new tests were added
   - This maintains historical record without duplicating details
   
   **Document 3: phase-1-4-implementation-gap-analysis.md (Original Gap Tracking) - SUMMARY ONLY**
   - ⚠️ **This document gets HIGH-LEVEL summary ONLY (prevent bloat)**
   - Find the original gap section (Gap #42: No Rate Limiting)
   - Update the gap status at the top:
     - ✅ **RESOLVED** if all tests pass and implementation 100% complete
     - ⚠️ **PARTIALLY COMPLETE** if fix document created or deliverables incomplete
   - Add "Resolved Date: YYYY-MM-DD" line if marking RESOLVED
   - Add brief summary (2-3 sentences maximum):
     - "Implemented [what was built]. X/X tests passing. See Task #22 in phase-4-5-implementation-roadmap.md for full details."
   - **DO NOT include:** Code snippets, detailed file lists, or long implementation notes
   - **DO include:** Cross-reference to current roadmap for full details
   
   **⚠️ CRITICAL: Prevent Document Bloat**
   - **ONLY phase-4-5-implementation-roadmap.md gets full details** (code snippets, file lists, etc.)
   - **phase-2-5-implementation-roadmap.md and phase-1-4-implementation-gap-analysis.md get summaries only**
   - This prevents massive context bloat across three documents
   - Historical docs remain scannable and readable
   - Full details always available in current roadmap
   
   **All three documents must match status:**
   - If phase-4-5 roadmap shows incomplete deliverables → gap status = PARTIALLY COMPLETE
   - If phase-4-5 roadmap shows all complete + tests pass → gap status = RESOLVED
   - phase-2-5 roadmap should mirror the completion status from phase-4-5 roadmap
   - Follow existing patterns from Phases 1-3 completed tasks
   
   **Why update all three?**
   - **phase-4-5-implementation-roadmap.md** = Current working document with FULL details
   - **phase-2-5-implementation-roadmap.md** = Historical baseline with summary status
   - **phase-1-4-implementation-gap-analysis.md** = Original gap tracking with resolution summary
   - Together, these provide complete audit trail without duplication: Problem → Plan → Execution → Completion

## Key Files to Review

### Architecture & Roadmaps
- `dev-docs/analysis/phase-4-5-implementation-roadmap.md` - **Current active roadmap (Phases 4-5)** ⭐ PRIMARY
- `dev-docs/analysis/phase-2-5-implementation-roadmap.md` - Historical roadmap (original Phases 2-5 plan)
- `dev-docs/analysis/phase-1-4-implementation-gap-analysis.md` - Original gap tracking (all phases)
- `dev-docs/architecture-design/mvp-arch.md` - Overall system design
- `dev-docs/db-design/aevofab-db-process-v2.6h.md` - Database operations & schema
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - **JSON schema source of truth** (must stay synced with models)

### Backend Code
- `backend/app/models/` - Database models (SQLModel ORM)
- `backend/api/routes/` - API endpoints
- `backend/core/` - Core utilities (auth, db, middleware, encryption)
- `backend/tasks/` - Celery background jobs
- `backend/services/` - Business logic (QuickBooks sync, email, SMS, voice)
- `backend/tests/` - Test suite (unit + integration)

### Recent Examples (Phases 1-3 Completed Work)

**Phase 1 Examples:**
- **Middleware:** `backend/core/idempotency.py`, `backend/core/middleware.py` (Request ID)
- **Database Triggers:** `backend/migrations/versions/2026_03_17_1451-*.py` (Quote/CO totals)
- **Tax Calculations:** `backend/core/tax_calculation.py` (IRS-compliant rounding)
- **Voice Actions:** `backend/services/voice_action_router.py` (10 MVP handlers)
- **Polymorphic Relations:** `backend/api/routes/contacts.py`, `addresses.py` (800+ lines each)

**Phase 2 Examples (Background Processing):**
- **Celery Setup:** `backend/core/celery_app.py` (Redis/SQS broker, Beat scheduler)
- **Background Workers:** `backend/tasks/profitability_rollup.py`, `notification_worker.py`
- **Email Service:** `backend/services/email_service.py` (SendGrid integration)
- **Session Cleanup:** `backend/tasks/cleanup_sessions.py` (3 scheduled tasks)

**Phase 3 Examples (QuickBooks Integration):**
- **OAuth Flow:** `backend/api/routes/integrations.py` (OAuth 2.0 callback handler)
- **Token Encryption:** `backend/core/encryption.py` (Fernet: AES-128-CBC + HMAC)
- **Sync Logic:** `backend/services/quickbooks_sync.py` (bidirectional sync, 450 lines)
- **Conflict Detection:** Enhanced detect_conflict() with version tokens
- **Webhook Handler:** `backend/api/routes/webhooks.py` (Cloud Events format, HMAC verification)

**Phase 4 Examples (Enterprise Hardening):**
- **Audit Logging:** `backend/core/db.py` (set_audit_context helpers)
- **RBAC Infrastructure:** `backend/core/permissions.py` (has_permission, require_permission decorators)
- **Role Management:** `backend/api/routes/roles.py` (5 endpoints)
- **Permission Tests:** `backend/tests/test_rbac_permissions.py` (40 tests)

**Test Patterns:**
- **Unit Tests:** `backend/tests/test_voice_actions.py`, `backend/tests/test_quickbooks_oauth.py`
- **Integration Tests:** `backend/tests/integration/test_sendgrid_integration.py`
- **Multi-tenancy:** `backend/tests/test_multi_tenancy_isolation.py` (26 tests)

**Documentation:**
- **Implementation Plans:** `dev-docs/analysis/phase-1-5-tasks/task-*-impl-plan.md` (25+ examples)
- **Gap Remediation:** `dev-docs/analysis/phase-1-4-gaps/gap-*-remediation-plan.md`
- **Testing Support:** `dev-docs/testing-support/` (Manual testing guides, fix documents)

## Success Criteria

**MUST COMPLETE ALL BEFORE MARKING GAP AS RESOLVED:**

- [ ] Implementation plan created and approved
- [ ] Slowapi library integrated with Redis backend
- [ ] Tenant-based rate limiting implemented (not IP-based)
- [ ] Tier-aware limits configured (free: 100/hour, standard: 1000/hour, premium: 5000/hour, enterprise: unlimited)
- [ ] Rate limit headers added to all responses (`X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`)
- [ ] 429 error responses with `retry_after` implemented
- [ ] Rate limiting applied to 30+ critical routes (all mutations, expensive reads)
- [ ] **ALL existing tests pass** (no regression from 398/398 baseline)
- [ ] **ALL new tests pass** (zero failures)
- [ ] **Test pass rate: 100%** (X/X passing, 0 failing)
- [ ] Documentation updated with what was delivered
- [ ] Code follows existing patterns and standards

**Specific Success Criteria from Roadmap:**
- ✅ Tenant exceeding 1000 req/hour gets 429 response
- ✅ Rate limit headers present on all responses
- ✅ Limit resets correctly after window expires
- ✅ Different tiers have different limits
- ✅ Performance impact < 5ms per request

**Gap Status in Analysis Doc:**
- ✅ **RESOLVED** - If all tests pass (implementation + tests 100% complete)
- ⚠️ **PARTIALLY COMPLETE** - If fix document created for failing tests
  - Must include: "Implementation complete, tests require fixes (see test_rate_limiting_fixes.md)"
  - Cannot mark RESOLVED until all tests pass

**If Tests Fail:**
- Create `dev-docs/testing-support/task-22-test_rate_limiting_fixes.md` with concrete fixes for ALL failing tests
- Update gap status to "PARTIALLY COMPLETE" in analysis doc
- Document exact steps to achieve 100% test pass rate
- Include time estimates for each fix

## Questions to Ask

Before starting:
1. Have I read the gap analysis entry thoroughly (Gap #42)?
2. Have I reviewed the design specification for rate limiting?
3. Do I understand the tenant-based vs. IP-based distinction?
4. What existing middleware patterns can I reference?
5. What tests need to be written?

During implementation:
1. Am I following existing middleware patterns (e.g., RequestIDMiddleware, IdempotencyMiddleware)?
2. Are ALL tests passing (100% pass rate)?
3. Am I documenting as I go?
4. Is this aligned with 80/20 MVP priorities?
5. Is Redis configured correctly for rate limiting storage?
6. Are rate limit headers being added to all responses?

After implementation:
1. Do I have 100% test pass rate (X/X passing, 0 failing)?
2. If tests fail, have I created a detailed fix document?
3. Have I marked the gap status correctly (RESOLVED vs PARTIALLY COMPLETE)?
4. Can another developer execute my test fixes successfully?
5. Have I verified tenant isolation (tenant A cannot exhaust tenant B's limits)?

## Implementation Guidance

### Library Selection
- **Use `slowapi==0.1.9`** - FastAPI-native rate limiting library
- Redis backend for distributed rate limiting (shares ElastiCache with Celery)
- Token bucket algorithm with sliding window

### Key Implementation Components

1. **Rate Limit Configuration** (`backend/core/rate_limit.py`)
   ```python
   from slowapi import Limiter, _rate_limit_exceeded_handler
   from slowapi.util import get_remote_address
   from slowapi.errors import RateLimitExceeded
   
   # Custom key function for tenant-based limiting (NOT IP-based)
   def get_tenant_identifier(request: Request) -> str:
       """Extract tenant_id from authenticated user for rate limiting"""
       # Use tenant_id from JWT, not IP address
       # Multi-user tenants share the same limit pool
   
   # Tier-based limits
   RATE_LIMITS = {
       "free": "100/hour",
       "standard": "1000/hour", 
       "premium": "5000/hour",
       "enterprise": None  # unlimited
   }
   ```

2. **Middleware Integration** (`backend/app/main.py`)
   - Register Slowapi limiter with FastAPI app
   - Add rate limit exception handler
   - Configure Redis connection (reuse existing ElastiCache)

3. **Route Protection** (Apply to all mutation endpoints)
   ```python
   from slowapi import Limiter
   
   limiter = Limiter(key_func=get_tenant_identifier)
   
   @router.post("/quotes")
   @limiter.limit("1000/hour")  # Apply tenant-based limit
   def create_quote(...):
       ...
   ```

4. **Rate Limit Headers**
   - `X-RateLimit-Limit` - Total requests allowed in window
   - `X-RateLimit-Remaining` - Requests remaining in current window
   - `X-RateLimit-Reset` - Unix timestamp when limit resets

5. **429 Error Response** (RFC 7807 format)
   ```python
   {
       "type": "rate_limit_exceeded",
       "title": "Rate Limit Exceeded",
       "status": 429,
       "detail": "Tenant has exceeded rate limit of 1000 requests per hour",
       "retry_after": 1800,  # seconds until reset
       "instance": "/api/v1/quotes"
   }
   ```

### Routes to Protect (30+ endpoints)

**High Priority (Mutations):**
- All POST, PUT, PATCH, DELETE endpoints in:
  - `/api/v1/customers/*`
  - `/api/v1/sites/*`
  - `/api/v1/jobs/*`
  - `/api/v1/quotes/*`
  - `/api/v1/contacts/*`
  - `/api/v1/addresses/*`
  - `/api/v1/integrations/*`

**Medium Priority (Expensive Reads):**
- `/api/v1/audit/events` (query audit logs)
- `/api/v1/voice` (AI transcription/processing)
- `/api/v1/catalog/search` (catalog search queries)

**DO NOT Rate Limit:**
- Health checks (`/health`)
- Authentication endpoints (`/auth/*`)
- Public quote acceptance (`/quotes/public/{token}/accept`)
- Test endpoints (`/*/test`) if TEST_ENDPOINT_ENABLED

### Test Coverage Requirements (10+ tests)

1. **Basic Rate Limiting** (3 tests)
   - Tenant can make requests up to limit
   - Tenant exceeding limit gets 429 response
   - 429 response includes retry_after header

2. **Rate Limit Headers** (2 tests)
   - All responses include X-RateLimit-* headers
   - Headers accurately reflect remaining quota

3. **Limit Resets** (2 tests)
   - Limit resets after time window expires
   - Counter resets to full quota on new window

4. **Tenant Isolation** (2 tests)
   - Tenant A hitting limit doesn't affect Tenant B
   - Different tenants have independent counters

5. **Tier-Based Limits** (2 tests)
   - Free tier limited to 100/hour
   - Standard tier limited to 1000/hour
   - Premium tier limited to 5000/hour

6. **Error Handling** (1 test)
   - 429 error format matches RFC 7807
   - Error includes helpful retry guidance

### Performance Considerations

- Rate limit check must complete in < 5ms
- Use Redis pipelining for batch operations
- Cache tier lookups to avoid repeated database queries
- Consider connection pooling for Redis

### Cost Considerations

- Reuse existing ElastiCache Redis instance (no additional infrastructure cost)
- Redis memory usage: ~50 bytes per tenant per hour = negligible
- No additional services needed (within $1k/mo budget)

## Notes

- **MVP Focus:** Follow dev-docs/product-requirements/mvp-prd.md for scope
- **80/20 Rule:** See .roo/rules-mvp-builder/80-20-prioritization.md
- **Mike the Solo Contractor:** Our primary persona - keep it simple!
- **No Enterprise Features:** Multi-trade, complex scheduling, etc. are out of scope
- **Infrastructure Constraints:** Respect $1k/mo budget cap (see infrastructure-constraints.md)
- **Phase 4 Focus:** Enterprise hardening (audit, RBAC, rate limiting, integration tests)
- **Redis Reuse:** Leverage existing ElastiCache instance used by Celery (no additional cost)
- **Tenant-Based Not IP-Based:** Multi-user tenants (owner + technicians) share the same rate limit pool
- **Tier Implementation:** For MVP, use single "standard" tier (1000/hour) - tier selection can be added post-launch
- **Grey Areas:** If you are unsure, ask Tom, the solo-entrepreneur developing the application with you
```
