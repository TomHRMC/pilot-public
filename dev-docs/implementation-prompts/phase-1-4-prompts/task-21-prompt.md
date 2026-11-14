# Task 21 Prompt: RBAC Permission System

```
Task: Phase 4, Task #21 - RBAC Permission System
Reference: dev-docs/analysis/phase-4-5-implementation-roadmap.md Task #21
(Original: Gap #41 in phase-1-4-implementation-gap-analysis.md)

## Context

We're building AevoFab AI, an AI-powered SaaS platform for electrical contractors with voice-controlled quoting and QuickBooks integration. Following the 80/20 rule to reach MVP quickly.

## Completed So Far

**Phase 1-A: Critical Blockers (COMPLETE - 7 tasks)**
✅ Test Endpoints, Tenant ID Fix, Idempotency, Request Tracing
✅ Database Triggers, Tax Calculations, Multi-Tenancy Tests

**Phase 1-B: Core Completeness (COMPLETE - 4 tasks)**
✅ Polymorphic Relationships, Contact Management
✅ Quote Acceptance Workflow, Voice Action Execut ion

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

**Phase 4: Enterprise Hardening (IN PROGRESS - 1 of 4 tasks complete)**
✅ Task 20: Audit Event Logging (COMPLETE - implementation complete, 16 test fixes pending)

**Test Coverage:** 339/339 passing (100% pass rate)
**See:** dev-docs/analysis/phase-4-5-implementation-roadmap.md for full details

## Current Task

Implement Role-Based Access Control (RBAC) permission enforcement to secure all API endpoints. Currently, all authenticated users have full access to all tenant data regardless of their role. This is a **CRITICAL security vulnerability** that blocks production deployment.

The database already has the RBAC schema in place (`tenant_user_role.permissions` JSONB field), but there is no permission checking logic in the API layer. This task implements the authorization layer to enforce permission-based access control.

**Priority:** CRITICAL (security vulnerability)
**Estimated Effort:** 5-6 days
**Task Spec:** See dev-docs/analysis/phase-4-5-implementation-roadmap.md Task #21
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
- **Create implementation plan first** (task-21-rbac-impl-plan.md) before coding
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
     - Example: `dev-docs/testing-support/task-21-test_rbac_fixes.md`

**Test Execution:**
- **Current Baseline:** 339/339 tests passing - DO NOT regress this
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
- **Create new test file:** `backend/tests/test_rbac_permissions.py`
- **Test coverage required:**
  - Unit tests for permission checking logic (has_permission, wildcard matching)
  - Integration tests for permission decorator on routes
  - Error handling and edge cases (missing permissions, invalid roles)
  - Tenant isolation verification (users can't access other tenant's permissions)
  - Role enforcement tests (owner vs technician vs office_staff vs accountant)

**Test Data Management:**
- **Reference data seeding:** Review `backend/migrations/seed_test_data.py` for existing seed patterns
  - Seed default roles (owner, technician, office_staff, accountant) in migrations
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
- **Phase 4 Cost Awareness** - RBAC is a software feature with minimal infrastructure cost impact

### 4. Database Standards
- **DO NOT hallucinate schema** - Always read backend/app/models/*.py first
- **JSON Schema as Source of Truth** - Models implement the schema in `dev-docs/db-design/pilot-db-schema-v2.6h.json`
  - **Before schema changes:** Review JSON schema to understand current structure and relationships
  - **After schema changes:** Update BOTH the SQLModel code AND the JSON schema file
  - **For questions:** JSON schema provides authoritative table/column definitions
  - JSON schema must stay synchronized with actual models (single source of truth)
- **Use Alembic migrations** for schema changes (if needed for default roles seeding)
- **Respect tenant isolation** - All permission queries filter by tenant_id
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
   - Find your task section (Task 21: RBAC Permission System)
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
   - Find the corresponding task section (Task 21: RBAC Permission System, line ~2028)
   - Mark task as ✅ COMPLETE with completion date
   - Add brief summary (2-3 sentences maximum):
     - "Completed YYYY-MM-DD. Implemented [core feature]. X/X tests passing."
   - **DO NOT include:** Code snippets, detailed file lists, or implementation notes
   - **DO include:** Test count if new tests were added
   - This maintains historical record without duplicating details
   
   **Document 3: phase-1-4-implementation-gap-analysis.md (Original Gap Tracking) - SUMMARY ONLY**
   - ⚠️ **This document gets HIGH-LEVEL summary ONLY (prevent bloat)**
   - Find the original gap section (Gap #41: No RBAC Permission Checks, line ~1021)
   - Update the gap status at the top:
     - ✅ **RESOLVED** if all tests pass and implementation 100% complete
     - ⚠️ **PARTIALLY COMPLETE** if fix document created or deliverables incomplete
   - Add "Resolved Date: YYYY-MM-DD" line if marking RESOLVED
   - Add brief summary (2-3 sentences maximum):
     - "Implemented [what was built]. X/X tests passing. See Task #21 in phase-4-5-implementation-roadmap.md for full details."
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
- `backend/app/models/auth.py` - **CRITICAL:** Review TenantUserRole model (line ~19) and permissions JSONB field
- `backend/core/auth.py` - Review existing AuthenticatedUser dependency
- `backend/api/routes/` - All API endpoints that need permission checks
- `backend/tests/conftest.py` - Existing fixtures for test setup
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

**Phase 4 Example (Current Phase):**
- **Audit Logging:** `backend/api/routes/audit.py` (462 lines, 3 endpoints)
- **Audit Triggers:** `backend/migrations/versions/2026_03_26_1541-*.py` (256 lines)
- **Session Context:** `backend/core/db.py` (set_audit_context_sync/async functions)

**Test Patterns:**
- **Unit Tests:** `backend/tests/test_voice_actions.py`, `backend/tests/test_quickbooks_oauth.py`
- **Integration Tests:** `backend/tests/integration/test_sendgrid_integration.py`
- **Multi-tenancy:** `backend/tests/test_multi_tenancy_isolation.py` (26 tests)
- **Audit Logging:** `backend/tests/test_audit_logging.py` (20 tests, 4 passing currently)

**Documentation:**
- **Implementation Plans:** `dev-docs/analysis/phase-1-5-tasks/task-*-impl-plan.md` (25+ examples)
- **Gap Remediation:** `dev-docs/analysis/phase-1-4-gaps/gap-*-remediation-plan.md`
- **Testing Support:** `dev-docs/testing-support/` (Manual testing guides, fix documents)

## Success Criteria

**MUST COMPLETE ALL BEFORE MARKING GAP AS RESOLVED:**

- [ ] Implementation plan created and approved
- [ ] Permission checking module created (`backend/core/permissions.py`)
- [ ] Permission decorator `@require_permission()` implemented
- [ ] Permission check function `has_permission()` implemented with wildcard support
- [ ] Default roles seeded via Alembic migration (owner, technician, office_staff, accountant)
- [ ] Role management API endpoints created (assign role, revoke role, query user permissions)
- [ ] Permission checks applied to 30+ sensitive routes across all route modules
- [ ] **ALL existing tests pass** (no regression from 339/339 baseline)
- [ ] **ALL new tests pass** (zero failures)
- [ ] **Test pass rate: 100%** (339+X/339+X passing, 0 failing)
- [ ] Documentation updated in all three roadmap documents
- [ ] Code follows existing patterns and standards

**Specific Enforcement Criteria:**
- ✅ Technician cannot create quotes (403 Forbidden - missing `quotes.create`)
- ✅ Office staff cannot log time entries (403 Forbidden - missing `time_entries.create`)
- ✅ Owner can perform all actions (wildcard `*` permission grants everything)
- ✅ Accountant has read-only access to financial data (`*.view` and `audit.view`)
- ✅ Permission checks add < 10ms latency per request (performance requirement)
- ✅ Tenant isolation enforced (users cannot access another tenant's role permissions)
- ✅ Invalid permissions raise clear 403 errors with helpful messages

**Gap Status in Analysis Doc:**
- ✅ **RESOLVED** - If all tests pass (implementation + tests 100% complete)
- ⚠️ **PARTIALLY COMPLETE** - If fix document created for failing tests
  - Must include: "Implementation complete, tests require fixes (see test_rbac_fixes.md)"
  - Cannot mark RESOLVED until all tests pass

**If Tests Fail:**
- Create `dev-docs/testing-support/task-21-test_rbac_fixes.md` with concrete fixes for ALL failing tests
- Update gap status to "PARTIALLY COMPLETE" in analysis doc
- Document exact steps to achieve 100% test pass rate
- Include time estimates for each fix

## Role Definitions

Implement these four default roles in the migration:

**1. Owner Role**
```python
{
    "code": "owner",
    "name": "Owner",
    "description": "Full access to all tenant resources",
    "permissions": ["*"]  # Wildcard grants all permissions
}
```

**2. Technician Role**
```python
{
    "code": "technician",
    "name": "Field Technician",
    "description": "Can view and update jobs, log time and expenses, use voice AI",
    "permissions": [
        "jobs.view",
        "jobs.update",
        "time_entries.create",
        "expenses.create",
        "voice.use",
        "nec.calculate"
    ]
}
```

**3. Office Staff Role**
```python
{
    "code": "office_staff",
    "name": "Office Staff",
    "description": "Manages customers, quotes, and administrative tasks",
    "permissions": [
        "customers.*",  # All customer operations
        "quotes.*",     # All quote operations
        "sites.*",      # All site operations
        "invoices.view",
        "reports.view"
    ]
}
```

**4. Accountant Role**
```python
{
    "code": "accountant",
    "name": "Accountant",
    "description": "Read-only access to financial data and audit logs",
    "permissions": [
        "*.view",       # Read-only access to all entities
        "audit.view"    # Audit log access for compliance
    ]
}
```

## Permission Syntax Specification

Implement permission checking with wildcard support:

**Format:** `resource.action`
- **resource:** Entity type (customers, quotes, jobs, invoices, etc.)
- **action:** Operation (create, view, update, delete, or custom actions)

**Wildcard Support:**
- `*` = All resources and actions (owner role)
- `customers.*` = All actions on customers resource
- `*.view` = View action on all resources (read-only)
- `quotes.create` = Specific action on specific resource

**Permission Matching Algorithm:**
```python
def has_permission(user: AuthenticatedUser, required_permission: str) -> bool:
    """
    Check if user has required permission with wildcard support
    
    Returns True if:
    - User has exact permission ("quotes.create")
    - User has wildcard permission ("*")
    - User has resource wildcard ("quotes.*")
    - User has action wildcard ("*.create")
    """
    user_permissions = user.role.permissions  # JSONB array from tenant_user_role
    
    # Check for exact match
    if required_permission in user_permissions:
        return True
    
    # Check for full wildcard
    if "*" in user_permissions:
        return True
    
    # Parse required permission
    resource, action = required_permission.split(".")
    
    # Check for resource wildcard (e.g., "quotes.*")
    if f"{resource}.*" in user_permissions:
        return True
    
    # Check for action wildcard (e.g., "*.view")
    if f"*.{action}" in user_permissions:
        return True
    
    return False
```

## Implementation Notes

**Key Technical Considerations:**

1. **Existing Auth Infrastructure:** The current `get_current_user()` dependency returns an `AuthenticatedUser` object. This already includes the user's role information via the `tenant_user` relationship. You should extend this existing pattern.

2. **Performance:** Permission checks will run on EVERY protected endpoint. Cache user permissions in the `AuthenticatedUser` object to avoid repeated database queries within a single request.

3. **Migration Strategy:** Create a new Alembic migration to seed the four default roles into the `tenant_user_role` table. Each tenant should get these roles automatically, or they can be created on-demand when users are assigned roles.

4. **Route Protection:** Apply `@require_permission()` decorator to routes in this priority order:
   - Financial routes (quotes, invoices, payments) - CRITICAL
   - Customer data routes (customers, sites, contacts) - HIGH
   - Job management routes (jobs, time entries, expenses) - HIGH
   - Administrative routes (audit, settings) - MEDIUM
   - Public routes (health, auth) - NO PROTECTION NEEDED

5. **Backward Compatibility:** Existing users may not have roles assigned. The migration should either:
   - Assign "owner" role to all existing users, OR
   - Make permission checks gracefully handle null roles (deny by default)

6. **Error Messages:** Return helpful 403 responses:
   ```json
   {
       "detail": "Insufficient permissions",
       "required_permission": "quotes.create",
       "user_permissions": ["jobs.view", "jobs.update"],
       "hint": "Contact your administrator to request the 'office_staff' role"
   }
   ```

7. **Testing Strategy:** Create test fixtures for each role type (owner_user, tech_user, staff_user, accountant_user) in `conftest.py` to simplify permission testing across routes.

## Questions to Ask

Before starting:
1. Have I read Gap #41 in the gap analysis thoroughly?
2. Have I reviewed the existing auth.py implementation?
3. Do I understand the TenantUserRole model and permissions JSONB field?
4. What existing code can I reference for decorator patterns?
5. What tests need to be written for each role type?

During implementation:
1. Am I following the existing auth patterns (`get_current_user` dependency)?
2. Are ALL tests passing (100% pass rate including the 339 baseline)?
3. Am I documenting as I go?
4. Is permission checking performant (< 10ms overhead)?
5. Are error messages helpful for debugging?

After implementation:
1. Do I have 100% test pass rate (339+X/339+X passing, 0 failing)?
2. If tests fail, have I created a detailed fix document?
3. Have I marked the gap status correctly (RESOLVED vs PARTIALLY COMPLETE)?
4. Can another developer understand the permission system from my documentation?
5. Have I tested all four role types against protected routes?

## Example Task Flow

```bash
# 1. Review the task in current roadmap (PRIMARY SOURCE)
cat dev-docs/analysis/phase-4-5-implementation-roadmap.md | grep -A 50 "Task 21:"

# 2. Check historical roadmap for original plan context
cat dev-docs/analysis/phase-2-5-implementation-roadmap.md | grep -A 50 "Task 21:"

# 3. Check original gap for context (Gap #41 = No RBAC Permission Checks)
cat dev-docs/analysis/phase-1-4-implementation-gap-analysis.md | grep -A 20 "^41\."

# 4. Review existing auth models
cat backend/app/models/auth.py | grep -A 30 "class TenantUserRole"

# 5. Review existing auth dependency
cat backend/core/auth.py | grep -A 20 "def get_current_user"

# 6. Run existing tests in concise mode to validate baseline (baseline: 339 passing)
cd backend && source .venv/bin/activate && pytest tests/ -v 2>&1 | grep -E "(passed|failed|===)" | tail -5

# 7. Create your implementation plan
# [create task-21-rbac-impl-plan.md]

# 8. Implement permission checking module
# [create backend/core/permissions.py]

# 9. Create migration for default roles
# [create Alembic migration]

# 10. Apply decorators to routes
# [update backend/api/routes/*.py files]

# 11. Write comprehensive tests
# [create backend/tests/test_rbac_permissions.py]

# 12. Run tests again (must maintain 100% pass rate + new tests)
pytest tests/ -v

# 13. Verify role enforcement (manual testing)
# Test that technician can't create quotes, office staff can't log time, etc.

# 14. Update all three roadmap documents
# - phase-4-5-implementation-roadmap.md (FULL DETAILS)
# - phase-2-5-implementation-roadmap.md (SUMMARY ONLY)
# - phase-1-4-implementation-gap-analysis.md (SUMMARY ONLY)
```

## Notes

- **MVP Focus:** Follow dev-docs/product-requirements/mvp-prd.md for scope
- **80/20 Rule:** Implement the four core roles (owner, technician, office_staff, accountant) - don't build custom role creation UI for MVP
- **Mike the Solo Contractor:** Our primary persona will likely run as "owner" - but his technicians need restricted access
- **No Enterprise Features:** Custom roles, fine-grained permissions, role hierarchy are out of scope for MVP
- **Security First:** This is a CRITICAL security vulnerability fix - all routes MUST have permission checks before launch
- **Performance Matters:** Permission checks run on every request - optimize for speed (< 10ms overhead)
- **Clear Errors:** 403 responses should clearly state what permission was required and what the user has
- **Grey Areas:** If you are unsure about which routes need which permissions, ask Tom, the solo-entrepreneur developing the application with you
```
