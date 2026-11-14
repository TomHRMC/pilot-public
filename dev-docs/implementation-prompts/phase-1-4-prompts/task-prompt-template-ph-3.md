# Next Task Prompt Template

Use this prompt template to create the prompt that will be used to start a new development task session. Copy and customize for each task and then create a new prompt document named task-##-prompt.md located in the same folder as this template doc.

---

## INSTRUCTIONS FOR ARCHITECT AGENT

When the user says "Create prompt for Task X" or "Create prompt for Phase 2, Task 12":

### Your Job (Architect Agent)
1. **Read the roadmap:** Extract task details from `dev-docs/analysis/phase-2-5-implementation-roadmap.md`
2. **Fill in the template:** Replace all [bracketed placeholders] with actual task details
3. **Create output file:** Save as `dev-docs/implementation-prompts/task-##-prompt.md` (zero-padded)
4. **Present to user:** Show a concise summary of what was created for review

### Information to Extract from Roadmap
For the specified task number, extract:
- **Task number and phase** (e.g., "Phase 2, Task #12")
- **Feature name** (e.g., "Celery Setup & Configuration")
- **Priority level** (BLOCKER/HIGH/MEDIUM)
- **Estimated effort** (e.g., "3 days")
- **Original gap reference** (e.g., "Gap #21") - found in task description
- **Deliverables list** - Copy checkboxes from roadmap "Deliverables" section
- **Success criteria** - Extract from roadmap task spec
- **Implementation notes** - Any code examples, file references, or special considerations
- **Cost/infrastructure notes** - For Phase 2+ tasks, include infrastructure constraints

### Template Customization Checklist
Replace these placeholders in the template below:
- [ ] `[Phase X, Task #XX - Feature Name]` → actual task (e.g., "Phase 2, Task #12 - Celery Setup")
- [ ] `[Describe the specific gap/feature to implement]` → full description from roadmap
- [ ] `[BLOCKER/HIGH/MEDIUM]` → actual priority from roadmap
- [ ] `[X days]` → actual effort estimate (e.g., "3 days")
- [ ] `Task #XX` → replace all 3 instances with actual task number
- [ ] `Gap #XX` → actual original gap number from roadmap
- [ ] **Success Criteria section** → Add task-specific deliverables from roadmap
- [ ] **Notes section** → Add infrastructure constraints if Phase 2+ task

### Output File Naming
Format: `task-##-prompt.md` where ## is zero-padded (e.g., `task-12-prompt.md`, `task-03-prompt.md`)

### Critical Reminder for Coding Agent
The prompt you create MUST instruct the coding agent to update BOTH documents when complete with a concise summary of completed tasks as the examples in the Workflow section item #8 below show:
1. **phase-2-5-implementation-roadmap.md** - Check off completed deliverables
2. **phase-1-4-implementation-gap-analysis.md** - Update original gap status (RESOLVED/PARTIALLY COMPLETE)

---

## PROMPT FOR NEXT TASK

```
Task: [Phase X, Task #XX - Feature Name]
Reference: dev-docs/analysis/phase-2-5-implementation-roadmap.md Task #XX
(Original: Gap #XX in phase-1-4-implementation-gap-analysis.md)

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

[Describe the specific gap/feature to implement]

**Priority:** [BLOCKER/HIGH/MEDIUM]
**Estimated Effort:** [X days]
**Task Spec:** See dev-docs/analysis/phase-2-5-implementation-roadmap.md Task #XX
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
- **Create implementation plan first** (task-XX-[name]-impl-plan.md) before coding
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
     - Example: `dev-docs/testing-support/task-##-test_[feature]_fixes.md`

**Test Execution:**
- **Current Baseline:** What ever the previous tests that passed were, e.g., 197/197 tests passing - DO NOT regress this
- **Tests are MANDATORY** - No code without tests
- **Run existing tests first:** (this ensures that you validate the total number of tests and that they are all passing)
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
- **Create new test file:** `backend/tests/test_[feature].py`
- **Test coverage required:**
  - Unit tests for core logic
  - Integration tests for API endpoints
  - Error handling and edge cases
  - Tenant isolation verification (multi-tenancy tests)

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
   - Find your task section (e.g., "Task 12: Celery Setup & Configuration")
   - Check off completed deliverables using `- [x]` checkbox format
   - Update any inline status notes or test results
   - If all deliverables complete, task is ✅ COMPLETE
   - If some deliverables incomplete, task is ⚠️ PARTIALLY COMPLETE
   
   **Document 2: phase-1-4-implementation-gap-analysis.md (Historical Gap Tracking)**
   - Find the original gap section (e.g., "Gap #21: Celery Configuration")
   - Update the gap status at the top:
     - ✅ **RESOLVED** if all tests pass and implementation 100% complete
     - ⚠️ **PARTIALLY COMPLETE** if fix document created or deliverables incomplete
   - Add "Resolved Date" line if marking RESOLVED
   - Add implementation summary (what was built, files created/modified, test results)
   - Cross-reference to task number (e.g., "See also: Task 12 in phase-2-5-implementation-roadmap.md")
   
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
- `backend/api/routes/` - API endpoints
- `backend/core/` - Core utilities (auth, db, middleware)
- `backend/tasks/` - Background jobs
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

- [ ] Implementation plan created and approved
- [ ] Implementation complete per plan
- [ ] **ALL existing tests pass** (no regression)
- [ ] **ALL new tests pass** (zero failures)
- [ ] **Test pass rate: 100%** (X/X passing, 0 failing)
- [ ] Documentation updated with what was delivered
- [ ] Code follows existing patterns and standards

**Gap Status in Analysis Doc:**
- ✅ **RESOLVED** - If all tests pass (implementation + tests 100% complete)
- ⚠️ **PARTIALLY COMPLETE** - If fix document created for failing tests
  - Must include: "Implementation complete, tests require fixes (see test_[feature]_fixes.md)"
  - Cannot mark RESOLVED until all tests pass

**If Tests Fail:**
- Create `backend/tests/test_[feature]_fixes.md` with concrete fixes for ALL failing tests
- Update gap status to "PARTIALLY COMPLETE" in analysis doc
- Document exact steps to achieve 100% test pass rate
- Include time estimates for each fix

## Questions to Ask

Before starting:
1. Have I read the gap analysis entry thoroughly?
2. Have I reviewed the design specification?
3. Do I understand how this fits into the MVP scope?
4. What existing code can I reference for patterns?
5. What tests need to be written?

During implementation:
1. Am I following existing patterns?
2. Are ALL tests passing (100% pass rate)?
3. Am I documenting as I go?
4. Is this aligned with 80/20 MVP priorities?

After implementation:
1. Do I have 100% test pass rate (X/X passing, 0 failing)?
2. If tests fail, have I created a detailed fix document?
3. Have I marked the gap status correctly (RESOLVED vs PARTIALLY COMPLETE)?
4. Can another developer execute my test fixes successfully?

## Example Task Flow

```bash
# 1. Review the task in roadmap
cat dev-docs/analysis/phase-2-5-implementation-roadmap.md | grep -A 30 "Task 12"

# 2. Check original gap for context (if needed)
cat dev-docs/analysis/phase-1-4-implementation-gap-analysis.md | grep -A 20 "Gap #21"

# 3. Check database models
ls -la backend/app/models/

# 4. Run existing tests (baseline: 197 passing)
cd backend && source .venv/bin/activate && pytest tests/ -v

# 5. Create your implementation
# [write code]

# 6. Run tests again (must maintain 100% pass rate)
pytest tests/ -v
```

## Notes

- **MVP Focus:** Follow dev-docs/product-requirements/mvp-prd.md for scope
- **80/20 Rule:** See .roo/rules-mvp-builder/80-20-prioritization.md
- **Mike the Solo Contractor:** Our primary persona - keep it simple!
- **No Enterprise Features:** Multi-trade, complex scheduling, etc. are out of scope
- **Grey Areas:** If you are unsure, ask Tom, the solo-entrepreneur developing the application with you
```

---

## Usage

1. Start this task with the `AevoFab Architect` custom Roo Code mode
2. Copy the prompt section above to begin
3. Fill in the specific task details as outlined and detailed
4. When finished, start a new Roo Code mode "MVP Builder" session with the prompt
5. The AI will have full context and standards
