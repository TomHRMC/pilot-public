# Phase 4, Task #23 - Integration Test Suite (Remaining E2E Workflows)

Task: Phase 4, Task #23 - Integration Test Suite
Reference: dev-docs/analysis/phase-4-5-implementation-roadmap.md Task #23
(Original: Gap #37 in phase-1-4-implementation-gap-analysis.md)

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

**Phase 4: Enterprise Hardening (3/4 COMPLETE)**
✅ Task 20: Audit Event Logging (2026-03-26)
✅ Task 21: RBAC Permission System (2026-03-28)
✅ Task 22: Rate Limiting (2026-03-28)
🟡 Task 23: Integration Test Suite (PARTIALLY COMPLETE)

**Test Coverage:** 411/411 passing (100% pass rate)
**See:** dev-docs/analysis/phase-4-5-implementation-roadmap.md for full details

## Current Task

**Task 23: Integration Test Suite (Remaining E2E Workflows)**

Integration testing ensures that end-to-end business workflows function correctly and that components integrate properly. While unit tests verify individual functions, integration tests validate entire user journeys and critical business processes.

**Priority:** HIGH (quality assurance, regression prevention)
**Estimated Effort:** 3-4 days (for remaining 3 priorities)
**Task Spec:** See dev-docs/analysis/phase-4-5-implementation-roadmap.md Task #23 (lines 722-1108)
**Design Context:** dev-docs/db-design/aevofab-db-process-v2.6h.md

## What's Already Complete ✅

### 1. SendGrid Email Integration (COMPLETE - March 20, 2026)
- ✅ 3 test files created (168-201 lines each)
- ✅ Real API calls verified with SendGrid
- ✅ Complete pipeline tested: API → Database → Worker → SendGrid → Status Update
- ✅ Test files:
  - `backend/tests/integration/test_sendgrid_integration.py`
  - `backend/tests/integration/test_notification_e2e.py`
  - `backend/tests/integration/test_sendgrid_diagnostics.py`

### 2. QuickBooks Integration (COMPLETE - March 24-25, 2026)
- ✅ 40 manual test steps (100% pass rate)
- ✅ OAuth, bidirectional sync, conflicts, webhooks all verified
- ✅ 1,790+ lines of test documentation
- ✅ 55 existing unit tests
- ✅ Documentation:
  - `dev-docs/testing-support/task-16-19-qb-int-testing-plan.md`
  - `dev-docs/testing-support/task-16-19-test-run-01.md`

### 3. Twilio SMS (DEFERRED - No Credentials)
- ⏸️ Deferred until Twilio account setup
- ✅ SMS service has passing unit tests with mocks
- 📝 Will be tested after phone number verification

## What Needs to Be Done 🔴

You must implement the following 3 integration test priorities:

### PRIORITY 1: Quote-to-Job Business Flow ⭐⭐⭐ CRITICAL
**Status:** 🔴 NOT STARTED
**Effort:** 1-2 days
**Priority:** CRITICAL - This is the core revenue cycle
**File to Create:** `backend/tests/integration/test_quote_to_job_flow.py`

**Why This Matters:**
- Tests 80% of your data mutations across 8+ tables
- Validates the complete cash flow pipeline from quote → job → payment
- Any bug here directly impacts revenue
- Covers RBAC, audit trail, and profitability tracking in one comprehensive flow

**Test Flow (15+ assertions required):**

```python
# Step 1: Setup tenant and users with RBAC roles
owner_user = create_user(role="owner")
technician_user = create_user(role="technician")

# Step 2: Create customer (owner permission required)
customer = create_customer(
    display_name="Mike's Diner",
    email="mike@mikesdiner.example.com"
)
assert customer.id is not None
assert audit_log_created(entity="customer", action="create")

# Step 3: Create site linked to customer
site = create_site(
    customer_id=customer.id,
    address="123 Main St, Boston, MA 02101"
)
assert site.customer_id == customer.id

# Step 4: Create quote with multiple line items
quote = create_quote(
    customer_id=customer.id,
    site_id=site.id
)
line_1 = add_quote_line(
    quote_id=quote.id,
    description="200A Service Panel",
    quantity=1,
    unit_price=1500.00
)
line_2 = add_quote_line(
    quote_id=quote.id,
    description="Wire #12 AWG",
    quantity=250,  # feet
    unit_price=1.50  # per foot
)
assert quote.subtotal == 1875.00  # 1500 + (250 * 1.50)

# Step 5: Calculate tax (IRS rounding rules)
quote = calculate_tax(quote_id=quote.id, tax_rate=0.0625)  # MA sales tax
assert quote.tax_total == 117.19  # Round to nearest cent
assert quote.grand_total == 1992.19  # 1875.00 + 117.19

# Step 6: Customer accepts quote (public link)
acceptance = accept_quote_public(
    quote_id=quote.id,
    accepted_by_name="Mike Anderson",
    accepted_by_email="mike@mikesdiner.example.com"
)
assert quote.quote_status_code == "accepted"
assert audit_log_created(entity="quote", action="accept")

# Step 7: Convert quote to job (owner permission)
job = convert_quote_to_job(quote_id=quote.id)
assert job.quote_id == quote.id
assert job.job_status_code == "scheduled"
assert job.quoted_amount == 1992.19

# Step 8: Technician logs time (technician permission)
time_entry = log_time_entry(
    job_id=job.id,
    user_id=technician_user.id,
    hours=6.5,
    billable_rate=85.00  # $85/hour
)
assert time_entry.total_cost == 552.50  # 6.5 * 85

# Step 9: Technician adds expenses
expense = add_job_expense(
    job_id=job.id,
    category_code="materials",
    description="Wire and conduit from supplier",
    amount=425.00
)
assert expense.amount == 425.00

# Step 10: Verify profitability rollup (Celery task)
trigger_profitability_rollup(job_id=job.id)
wait_for_task_completion(timeout=10)

job = get_job(job.id)
assert job.actual_cost_total == 977.50  # 552.50 + 425.00
assert job.actual_profit == 1014.69  # 1992.19 - 977.50
assert job.profit_margin_pct == 50.95  # (1014.69 / 1992.19) * 100

# Step 11: Verify referential integrity
assert job.customer_id == customer.id
assert job.site_id == site.id

# Step 12: Verify RBAC enforcement
with pytest.raises(PermissionDenied):
    update_quote(quote_id=quote.id, user=technician_user)

# Step 13: Verify audit trail
audit_events = get_audit_events(entity_id=job.id)
assert len(audit_events) >= 5

# Step 14: Verify no orphaned records
delete_job(job_id=job.id)
assert get_time_entries(job_id=job.id) == []

# Step 15: Performance verification
assert quote_creation_time < 500  # ms (p95 latency target)
assert profitability_rollup_time < 5000  # ms (5 second SLA)
```

**Related Code Files:**
- Quote CRUD: `backend/api/routes/quotes.py`
- Job CRUD: `backend/api/routes/jobs.py`
- Customer CRUD: `backend/api/routes/customers.py`
- Profitability Rollup: `backend/tasks/profitability_rollup.py`
- RBAC Permissions: `backend/core/permissions.py`
- Audit Logging: `backend/api/routes/audit.py`

**Success Criteria:**
- ✅ All 15+ assertions pass
- ✅ Test completes in < 30 seconds
- ✅ No database errors or constraint violations
- ✅ Profitability calculations accurate to 2 decimal places
- ✅ RBAC denies unauthorized actions
- ✅ Audit log captures all state changes

---

### PRIORITY 2: Voice AI Multi-Turn Conversation ⭐⭐ HIGH
**Status:** 🔴 NOT STARTED
**Effort:** 1 day
**Priority:** HIGH - Your core differentiator
**File to Create:** `backend/tests/integration/test_voice_multi_turn_e2e.py`

**Why This Matters:**
- Voice AI with context awareness is your unique selling proposition
- Multi-turn conversations must maintain state correctly
- Entity resolution (pronoun → concrete entity_id) is complex
- Context window must retrieve last 5 messages accurately

**Test Flow (4 conversation turns):**

```python
# TURN 1: "Create quote for Mike's Diner"
turn_1 = process_voice_command(
    text="Create quote for Mike's Diner",
    user_id=owner_user.id,
    tenant_id=tenant.id
)
assert turn_1.session_id is not None
assert turn_1.action == "quote.create"
assert turn_1.entities["customer"]["name"] == "Mike's Diner"
quote_id = turn_1.created_entity_id

# TURN 2: "Add 100 feet of 12 AWG wire"
turn_2 = process_voice_command(
    text="Add 100 feet of 12 AWG wire",
    user_id=owner_user.id,
    tenant_id=tenant.id,
    session_id=turn_1.session_id  # Continue conversation
)
assert turn_2.session_id == turn_1.session_id
assert turn_2.action == "quote_line.create"
assert turn_2.context["quote_id"] == quote_id  # Retrieved from context
assert turn_2.entities["quantity"] == 100
assert turn_2.entities["description"] == "12 AWG wire"

# TURN 3: "Calculate voltage drop"
turn_3 = process_voice_command(
    text="Calculate voltage drop",
    user_id=owner_user.id,
    tenant_id=tenant.id,
    session_id=turn_1.session_id
)
assert turn_3.action == "nec.calculate"
assert turn_3.context["quote_id"] == quote_id  # Uses quote context
assert turn_3.entities["wire_gauge"] == "12 AWG"  # From previous turn

# TURN 4: "Send it to the customer"
turn_4 = process_voice_command(
    text="Send it to the customer",
    user_id=owner_user.id,
    tenant_id=tenant.id,
    session_id=turn_1.session_id
)
assert turn_4.action == "quote.send"
assert turn_4.context["quote_id"] == quote_id  # Resolves "it" → quote_id
assert turn_4.entities["recipient"] == "mike@mikesdiner.example.com"

# Verify session context window
session_messages = get_session_messages(turn_1.session_id)
assert len(session_messages) == 4
assert session_messages[-1].text == "Send it to the customer"

# Verify session expiration
assert session.expires_at > datetime.utcnow()
```

**What to Validate:**
- ✅ Conversation session maintains context across 4+ turns
- ✅ Entity resolution (pronoun → concrete entity_id)
- ✅ Context window retrieval (last 5 messages from `conversation_session_message`)
- ✅ Action execution with inherited context
- ✅ Session expiration after 30 minutes (configurable via `ConversationSession.expires_at`)

**Related Code Files:**
- Voice Action Router: `backend/services/voice_action_router.py`
- Voice API: `backend/api/routes/voice.py`
- Session Model: `backend/app/models/ai.py`
- Existing Tests: `backend/tests/test_voice_actions.py` (6 tests)

**Success Criteria:**
- ✅ 4 conversation turns complete successfully
- ✅ Context correctly passed between turns
- ✅ Pronoun resolution works ("it" → quote_id)
- ✅ Session stores all messages
- ✅ Test completes in < 15 seconds

---

### PRIORITY 3: Financial Math Edge Cases ⭐ MEDIUM
**Status:** 🔴 NOT STARTED
**Effort:** 1 day
**Priority:** MEDIUM - Data integrity
**File to Create:** `backend/tests/integration/test_financial_math_edge_cases.py`

**Why This Matters:**
- Financial calculations must be accurate to the cent
- Rounding errors compound over multiple operations
- Tax calculations must comply with IRS Publication 1779
- Profitability calculations affect business decisions

**Test Coverage Required:**

```python
# Test 1: IRS Tax Rounding (Publication 1779)
quote = create_quote_with_tax(
    subtotal=100.00,
    tax_rate=0.0625  # 6.25%
)
assert quote.tax_total == 6.25  # Not 6.249999...
assert quote.grand_total == 106.25

# Test 2: Quote with 100+ Line Items (No Accumulation Errors)
quote = create_quote()
for i in range(100):
    add_quote_line(
        quote_id=quote.id,
        quantity=1,
        unit_price=1.99  # Tricky decimal
    )
assert quote.subtotal == 199.00  # 100 * 1.99
assert quote.tax_total == 12.44  # 199.00 * 0.0625 rounded
assert quote.grand_total == 211.44

# Test 3: Change Order Impact on Profitability
job = create_job(quoted_amount=1000.00)
add_time_entry(job_id=job.id, cost=300.00)
add_expense(job_id=job.id, cost=200.00)

# Initial profitability
trigger_profitability_rollup(job.id)
assert job.actual_cost_total == 500.00
assert job.actual_profit == 500.00

# Add change order
change_order = create_change_order(job_id=job.id, amount=500.00)
approve_change_order(change_order.id)

# Updated profitability (no double-counting)
trigger_profitability_rollup(job.id)
assert job.quoted_amount == 1500.00  # Original + change order
assert job.actual_profit == 1000.00  # 1500 - 500

# Test 4: Negative Adjustments (Discounts)
quote = create_quote(subtotal=1000.00)
apply_discount(quote.id, amount=-100.00)  # $100 discount
assert quote.subtotal == 900.00
assert quote.grand_total > 0  # No negative totals

# Test 5: Overflow Protection
large_quote = create_quote()
add_quote_line(
    quote_id=large_quote.id,
    quantity=1,
    unit_price=999999.99  # Maximum practical value
)
assert large_quote.subtotal == 999999.99  # No truncation

# Test 6: Currency Precision (Cents-Based Math)
# All monetary values stored as integers (cents)
quote = create_quote_with_line(
    quantity=3,
    unit_price=1.33  # $1.33
)
assert quote.subtotal == 3.99  # 3 * 1.33 = 3.99 (not 3.9899999...)

# Test 7: Profitability Formula Accuracy
job = create_job(quoted_amount=5000.00)
add_time_entry(job_id=job.id, hours=40, rate=85.00)  # $3,400
add_expense(job_id=job.id, amount=800.00)  # $800

trigger_profitability_rollup(job.id)
assert job.actual_cost_total == 4200.00  # 3400 + 800
assert job.actual_profit == 800.00  # 5000 - 4200
assert job.profit_margin_pct == 16.00  # (800 / 5000) * 100
```

**Related Code Files:**
- Tax Calculation: `backend/api/routes/quotes.py` (uses IRS rounding rules)
- Profitability Rollup: `backend/tasks/profitability_rollup.py`
- Database Triggers: Quote totals, change order totals (see `backend/migrations/versions/`)

**Success Criteria:**
- ✅ All 7 test scenarios pass
- ✅ No floating-point accumulation errors
- ✅ Tax calculations comply with IRS Publication 1779
- ✅ Profitability formula accurate to 2 decimal places
- ✅ Currency precision maintained (cents-based math)

---

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
- **No implementation plan needed** (integration tests are straightforward)
- **Update implementation roadmap** when marking task complete

### 2. Testing Standards (CRITICAL FOR MVP)

**⚠️ ZERO FAILING TESTS POLICY:**
- **ALL tests MUST pass before marking a gap as RESOLVED**
- **NO exceptions** - MVP requires 100% test pass rate
- If tests fail after implementation, you have TWO options:
  1. **Fix immediately** (preferred for simple fixes)
  2. **Create detailed fix document** (for complex test issues)

**Test Execution:**
- **Current Baseline:** 411/411 tests passing - DO NOT regress this
- **Tests are MANDATORY** - No code without tests
- **Test Configuration Files:**
  - **pytest.ini:** Default flags (`-v`, `--strict-markers`, `--tb=short`, `-ra`)
  - **.coveragerc:** Coverage settings (covers `api/`, `app/`, `core/`, `services/`, `tasks/`, branch coverage, omits `tests/` and `alembic/`)
- **Run existing tests first:**
  - **DEFAULT (recommended):** `cd backend && source .venv/bin/activate && pytest --ignore=tests/integration/ tests/`
    - Excludes integration tests that trigger SendGrid emails (daily limit applies)
  - **All tests (including integration):** `cd backend && source .venv/bin/activate && pytest tests/`
    - ⚠️ Only run when needed - fires SendGrid emails (limited daily quota)
- **All existing tests must pass** - Baseline must not regress
- **All new tests must pass** - No failing tests allowed

**Test Development:**
- **BEFORE writing tests:** Review `backend/tests/conftest.py` to understand existing fixtures
- **Create new test files:**
  - `backend/tests/integration/test_quote_to_job_flow.py`
  - `backend/tests/integration/test_voice_multi_turn_e2e.py`
  - `backend/tests/integration/test_financial_math_edge_cases.py`
- **Test coverage required:**
  - Integration tests for end-to-end workflows
  - Error handling and edge cases
  - Tenant isolation verification (multi-tenancy tests)
  - Performance benchmarks (p95 latency targets)

**Pytest Markers:**
```python
# Mark integration tests appropriately
@pytest.mark.integration
@pytest.mark.e2e
def test_quote_to_job_flow():
    """Test complete revenue cycle"""
```

**Test Data Management:**
- **Reference data seeding:** Review `backend/migrations/seed_test_data.py` for existing seed patterns
- **Test data creation:** Create necessary test data in fixtures or test setup
- **Test data cleanup:** Database automatically rolls back after each test (session scope)

### 3. Code Standards
- **Follow existing patterns** - Check similar implementations first
- **Type hints required** - Use AuthenticatedUser, not User
- **Error handling** - RFC 7807 format (see existing routes)
- **Docstrings required** - Document all functions/classes
- **No feature creep** - Strictly follow 80/20 MVP prioritization

### 4. Database Standards
- **DO NOT hallucinate schema** - Always read backend/app/models/*.py first
- **JSON Schema as Source of Truth** - Models implement the schema in `dev-docs/db-design/pilot-db-schema-v2.6h.json`
- **Use Alembic migrations** for schema changes
- **Respect tenant isolation** - All queries filter by tenant_id
- **Follow ORM patterns** - Use SQLModel/SQLAlchemy correctly

### 5. Workflow
1. **Read the task roadmap** to understand the requirements (lines 722-1108)
2. **Review design specs** (db-process-v2.6h.md, mvp-arch.md)
3. **Review existing integration tests** in `backend/tests/integration/`
4. **Implement Priority 1** (Quote-to-Job Flow) - 1-2 days
5. **Implement Priority 2** (Voice AI Multi-Turn) - 1 day
6. **Implement Priority 3** (Financial Math Edge Cases) - 1 day
7. **Run all tests** - Must pass before completion
8. **Update documentation** - **ALL THREE documents MUST be updated:**
   
   **Document 1: phase-4-5-implementation-roadmap.md (Current Active Roadmap) - FULL DETAILS**
   - ✅ **This document gets FULL implementation details**
   - Find Task 23 section (line 722)
   - Check off completed deliverables using `- [x]` checkbox format
   - Add "Status: ✅ COMPLETE (YYYY-MM-DD)" at top of task section
   - Add "Test Results:" line showing X/X tests passing
   - Include ALL implementation details:
     - Files created with line counts
     - Test scenarios covered (15+ for Priority 1, 4 for Priority 2, 7 for Priority 3)
     - Performance benchmarks
     - Integration notes and verification steps
   
   **Document 2: phase-2-5-implementation-roadmap.md (Historical Roadmap) - SUMMARY ONLY**
   - ⚠️ **This document gets HIGH-LEVEL summary ONLY (prevent bloat)**
   - Find Task 23 section
   - Mark task as ✅ COMPLETE with completion date
   - Add brief summary (2-3 sentences maximum):
     - "Completed YYYY-MM-DD. Implemented 3 integration test priorities: Quote-to-Job flow (15+ assertions), Voice AI multi-turn (4 turns), Financial math edge cases (7 scenarios). X/X tests passing."
   - **DO NOT include:** Test details, code snippets, or implementation notes
   
   **Document 3: phase-1-4-implementation-gap-analysis.md (Original Gap Tracking) - SUMMARY ONLY**
   - ⚠️ **This document gets HIGH-LEVEL summary ONLY (prevent bloat)**
   - Find Gap #37 section (line 956)
   - Update the gap status at the top:
     - ✅ **RESOLVED** if all tests pass and implementation 100% complete
   - Add "Resolved Date: YYYY-MM-DD" line
   - Add brief summary (2-3 sentences maximum):
     - "Implemented 3 E2E test priorities. Quote-to-Job flow tests complete revenue cycle with 15+ assertions. Voice AI multi-turn tests context management. Financial math tests validate IRS compliance and profitability accuracy. X/X tests passing. See Task #23 in phase-4-5-implementation-roadmap.md for full details."
   - **DO NOT include:** Code snippets, detailed file lists, or long implementation notes

## Key Files to Review

### Architecture & Roadmaps
- `dev-docs/analysis/phase-4-5-implementation-roadmap.md` - **Current active roadmap (Phases 4-5)** ⭐ PRIMARY (lines 722-1108 for Task 23)
- `dev-docs/analysis/phase-2-5-implementation-roadmap.md` - Historical roadmap (original Phases 2-5 plan)
- `dev-docs/analysis/phase-1-4-implementation-gap-analysis.md` - Original gap tracking (Gap #37 at line 956)
- `dev-docs/architecture-design/mvp-arch.md` - Overall system design
- `dev-docs/db-design/aevofab-db-process-v2.6h.md` - Database operations & schema

### Existing Integration Tests (Examples)
- `backend/tests/integration/test_sendgrid_integration.py` - SendGrid API tests (168 lines)
- `backend/tests/integration/test_notification_e2e.py` - Notification pipeline (201 lines)
- `backend/tests/conftest.py` - Test fixtures and helpers

### Backend Code (For Integration Testing)
- `backend/app/models/` - Database models (SQLModel ORM)
- `backend/api/routes/` - API endpoints
- `backend/core/` - Core utilities (auth, db, middleware, encryption)
- `backend/tasks/` - Celery background jobs (profitability_rollup.py)
- `backend/services/` - Business logic (voice_action_router.py, quickbooks_sync.py)

### Recent Examples
- **Integration Tests:** `backend/tests/integration/test_sendgrid_integration.py` (5 tests)
- **E2E Pipeline:** `backend/tests/integration/test_notification_e2e.py` (complete workflow)
- **Unit Tests:** `backend/tests/test_voice_actions.py` (6 tests for voice AI)
- **Financial Tests:** `backend/tests/test_database_triggers.py` (quote totals verification)

## Success Criteria

**MUST COMPLETE ALL BEFORE MARKING GAP AS RESOLVED:**

- [ ] Priority 1: Quote-to-Job Flow test file created (15+ assertions)
- [ ] Priority 2: Voice AI Multi-Turn test file created (4 conversation turns)
- [ ] Priority 3: Financial Math Edge Cases test file created (7 scenarios)
- [ ] **ALL existing tests pass** (no regression from 411/411 baseline)
- [ ] **ALL new tests pass** (zero failures)
- [ ] **Test pass rate: 100%** (X/X passing, 0 failing)
- [ ] Documentation updated in all 3 files
- [ ] Tests run in reasonable time (< 2 minutes for all integration tests)

**Gap Status in Analysis Doc:**
- ✅ **RESOLVED** - If all 3 priorities complete and all tests pass (100%)

**If Tests Fail:**
- Create `backend/tests/integration/test_[feature]_fixes.md` with concrete fixes
- Update gap status to "PARTIALLY COMPLETE" in analysis doc
- Document exact steps to achieve 100% test pass rate

## Test Execution Commands

```bash
# Run only new integration tests (faster during development)
cd backend && source .venv/bin/activate && pytest tests/integration/test_quote_to_job_flow.py -v
cd backend && source .venv/bin/activate && pytest tests/integration/test_voice_multi_turn_e2e.py -v
cd backend && source .venv/bin/activate && pytest tests/integration/test_financial_math_edge_cases.py -v

# Run all integration tests
cd backend && source .venv/bin/activate && pytest tests/integration/ -v

# Run full test suite (exclude SendGrid to avoid daily quota)
cd backend && source .venv/bin/activate && pytest --ignore=tests/integration/test_sendgrid_integration.py --ignore=tests/integration/test_notification_e2e.py tests/

# Run everything including SendGrid (⚠️ Limited daily quota)
cd backend && source .venv/bin/activate && pytest tests/

# Check test count
cd backend && source .venv/bin/activate && pytest --collect-only tests/
```

## Notes

- **MVP Focus:** Follow dev-docs/product-requirements/mvp-prd.md for scope
- **80/20 Rule:** See .roo/rules-mvp-builder/80-20-prioritization.md
- **Mike the Solo Contractor:** Our primary persona - keep it simple!
- **Test Execution Order:** Priority 1 → Priority 2 → Priority 3
- **Quote-to-Job is CRITICAL:** This tests your core revenue cycle (80% of business value)
- **Voice AI is DIFFERENTIATOR:** Multi-turn context is what makes you unique
- **Financial Math is TRUST:** Accurate calculations = customer trust
- **No Feature Creep:** Stick to the 3 priorities, defer QB internal logic automation
- **Grey Areas:** If you are unsure, ask Tom, the solo-entrepreneur developing the application with you
