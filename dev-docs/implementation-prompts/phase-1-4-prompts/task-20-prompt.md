# Task 20: Audit Event Logging

```
Task: Phase 4, Task #20 - Audit Event Logging
Reference: dev-docs/analysis/phase-4-5-implementation-roadmap.md Task #20
(Original: Gap #29 in phase-1-4-implementation-gap-analysis.md)

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

**Test Coverage:** 339/339 passing (100% pass rate)
**See:** dev-docs/analysis/phase-4-5-implementation-roadmap.md for full details

## Current Task

Implement comprehensive audit event logging system to capture all data mutations for compliance, debugging, and security tracking. The `audit.event` table exists in the database schema but has never been written to. We need to implement database-level trigger functions to automatically capture old/new values for all critical tables, provide APIs to query audit history, and establish retention policies for long-term compliance.

**Priority:** CRITICAL (compliance requirement)
**Estimated Effort:** 4-5 days
**Task Spec:** See dev-docs/analysis/phase-4-5-implementation-roadmap.md Task #20
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
- **Create implementation plan first** (task-20-audit-logging-impl-plan.md) before coding
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
     - Example: `dev-docs/testing-support/task-20-test_audit_logging_fixes.md`

**Test Execution:**
- **Current Baseline:** 339/339 tests passing - DO NOT regress this
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
- **Create new test file:** `backend/tests/test_audit_logging.py`
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
- **Follow existing patterns** - Check similar implementations first (see Task 12-15 trigger examples)
- **Type hints required** - Use AuthenticatedUser, not User
- **Error handling** - RFC 7807 format (see existing routes)
- **Docstrings required** - Document all functions/classes
- **No feature creep** - Strictly follow 80/20 MVP prioritization
- **Phase 4 Cost Awareness** - Audit log storage costs must stay within $1k/mo budget cap

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
   - Find your task section (e.g., "Task 20: Audit Event Logging")
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
   - Find the corresponding task section (Task 20: Audit Event Logging, line 1964)
   - Mark task as ✅ COMPLETE with completion date
   - Add brief summary (2-3 sentences maximum):
     - "Completed YYYY-MM-DD. Implemented [core feature]. X/X tests passing."
   - **DO NOT include:** Code snippets, detailed file lists, or implementation notes
   - **DO include:** Test count if new tests were added
   - This maintains historical record without duplicating details
   
   **Document 3: phase-1-4-implementation-gap-analysis.md (Original Gap Tracking) - SUMMARY ONLY**
   - ⚠️ **This document gets HIGH-LEVEL summary ONLY (prevent bloat)**
   - Find the original gap section (Gap #29: Audit Event Logging, line 891)
   - Update the gap status at the top:
     - ✅ **RESOLVED** if all tests pass and implementation 100% complete
     - ⚠️ **PARTIALLY COMPLETE** if fix document created or deliverables incomplete
   - Add "Resolved Date: YYYY-MM-DD" line if marking RESOLVED
   - Add brief summary (2-3 sentences maximum):
     - "Implemented [what was built]. X/X tests passing. See Task #20 in phase-4-5-implementation-roadmap.md for full details."
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
- `backend/app/models/system.py` - **Contains `audit.event` table definition (line 144)**
- `backend/api/routes/` - API endpoints
- `backend/core/` - Core utilities (auth, db, middleware, encryption)
- `backend/tasks/` - Celery background jobs
- `backend/services/` - Business logic (QuickBooks sync, email, SMS, voice)
- `backend/tests/` - Test suite (unit + integration)

### Recent Examples (Phases 1-3 Completed Work)

**Phase 1 Examples:**
- **Middleware:** `backend/core/idempotency.py`, `backend/core/middleware.py` (Request ID)
- **Database Triggers:** `backend/migrations/versions/2026_03_17_1451-*.py` (Quote/CO totals) ⭐ **USE THIS AS PATTERN**
- **Tax Calculations:** `backend/core/tax_calculation.py` (IRS-compliant rounding)
- **Voice Actions:** `backend/services/voice_action_router.py` (10 MVP handlers)
- **Polymorphic Relations:** `backend/api/routes/contacts.py`, `addresses.py` (800+ lines each)

**Phase 2 Examples (Background Processing):**
- **Celery Setup:** `backend/core/celery_app.py` (Redis/SQS broker, Beat scheduler)
- **Background Workers:** `backend/tasks/profitability_rollup.py`, `notification_worker.py`
- **Email Service:** `backend/services/email_service.py` (SendGrid integration)
- **Session Cleanup:** `backend/tasks/cleanup_sessions.py` (3 scheduled tasks) ⭐ **USE FOR ARCHIVE TASK PATTERN**

**Phase 3 Examples (QuickBooks Integration):**
- **OAuth Flow:** `backend/api/routes/integrations.py` (OAuth 2.0 callback handler)
- **Token Encryption:** `backend/core/encryption.py` (Fernet: AES-128-CBC + HMAC)
- **Sync Logic:** `backend/services/quickbooks_sync.py` (bidirectional sync, 450 lines)
- **Conflict Detection:** Enhanced detect_conflict() with version tokens
- **Webhook Handler:** `backend/api/routes/webhooks.py` (Cloud Events format, HMAC verification)

**Test Patterns:**
- **Unit Tests:** `backend/tests/test_voice_actions.py`, `test_quickbooks_oauth.py`
- **Integration Tests:** `backend/tests/integration/test_sendgrid_integration.py`
- **Multi-tenancy:** `backend/tests/test_multi_tenancy_isolation.py` (26 tests)
- **Database Triggers:** `backend/tests/test_database_triggers.py` ⭐ **USE AS TEST PATTERN**

**Documentation:**
- **Implementation Plans:** `dev-docs/analysis/phase-1-5-tasks/task-*-impl-plan.md` (25+ examples)
- **Gap Remediation:** `dev-docs/analysis/phase-1-4-gaps/gap-*-remediation-plan.md`
- **Testing Support:** `dev-docs/testing-support/` (Manual testing guides, fix documents)

## Success Criteria

**MUST COMPLETE ALL BEFORE MARKING GAP AS RESOLVED:**

- [ ] Implementation plan created and approved (task-20-audit-logging-impl-plan.md)
- [ ] Database trigger function `audit.log_changes()` created for automatic logging
- [ ] Apply triggers to 12 critical tables (customer, quote, job, invoice, payment, site, contact, address, time_entry, expense, catalog_item, pricebook_item)
- [ ] Session context `set_audit_context()` to capture user_id for trigger function
- [ ] Audit query API `GET /api/v1/audit/events` with filtering and pagination
- [ ] Entity change history API `GET /api/v1/audit/diff/{entity_type}/{entity_id}` showing field-level changes
- [ ] Retention policy implementation (90 days hot, 7 years cold archive)
- [ ] Archive Celery task scheduled (daily at 1 AM) to move old records
- [ ] Test suite (15+ tests covering triggers, API, tenant isolation)
- [ ] **ALL existing tests pass** (no regression from 339/339 baseline)
- [ ] **ALL new tests pass** (zero failures)
- [ ] **Test pass rate: 100%** (X/X passing, 0 failing)
- [ ] Documentation updated in all three roadmap documents
- [ ] Code follows existing patterns and standards

**Specific Success Criteria:**
- ✅ Edit customer → `audit.event` record created with old/new values in JSONB
- ✅ Audit query API returns complete change history with tenant isolation verified
- ✅ Field-level diff shows exact changes chronologically (old value → new value)
- ✅ Performance impact < 5ms per mutation (database-level enforcement, minimal overhead)
- ✅ Cannot bypass audit logging (PostgreSQL triggers run automatically, no application-level bypass possible)
- ✅ Archive task moves records older than 90 days without data loss
- ✅ Tenant isolation: Tenant A cannot see Tenant B's audit events

**Gap Status in Analysis Doc:**
- ✅ **RESOLVED** - If all tests pass (implementation + tests 100% complete)
- ⚠️ **PARTIALLY COMPLETE** - If fix document created for failing tests
  - Must include: "Implementation complete, tests require fixes (see test_audit_logging_fixes.md)"
  - Cannot mark RESOLVED until all tests pass

**If Tests Fail:**
- Create `dev-docs/testing-support/task-20-test_audit_logging_fixes.md` with concrete fixes for ALL failing tests
- Update gap status to "PARTIALLY COMPLETE" in analysis doc
- Document exact steps to achieve 100% test pass rate
- Include time estimates for each fix

## Implementation Notes

### Database Trigger Approach (RECOMMENDED)

**Why Database Triggers:**
- ✅ Cannot be bypassed by application code
- ✅ Captures changes from all sources (API, direct SQL, migrations)
- ✅ Minimal performance overhead (<5ms)
- ✅ Atomic with transaction (rollback if audit fails)
- ✅ Consistent with existing trigger pattern (see Quote/CO triggers)

**Pattern from Existing Triggers:**
Review `backend/migrations/versions/2026_03_17_1451-a4d2659a2921_add_database_triggers_for_quote_totals_.py` for:
- PostgreSQL function creation syntax
- Trigger attachment to tables
- Using `TG_OP`, `TG_TABLE_NAME`, `OLD`, `NEW` variables
- JSONB conversion with `row_to_json()`
- Transaction safety patterns

**Session Context Pattern:**
```python
# backend/core/database.py
async def set_audit_context(db: Session, user_id: uuid.UUID):
    """Set PostgreSQL session variable for audit trail user tracking"""
    await db.execute(text(f"SET LOCAL app.user_id = '{user_id}'"))
```

**Trigger Function (Example):**
```sql
CREATE OR REPLACE FUNCTION audit.log_changes()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO audit.event (
        tenant_id, 
        user_id, 
        entity_type, 
        entity_id,
        operation, 
        old_values_json, 
        new_values_json,
        changed_at
    ) VALUES (
        COALESCE(NEW.tenant_id, OLD.tenant_id),
        COALESCE(
            current_setting('app.user_id', true)::uuid,
            '00000000-0000-0000-0000-000000000000'::uuid
        ),
        TG_TABLE_NAME::text,
        COALESCE(NEW.id, OLD.id),
        TG_OP,
        CASE WHEN TG_OP = 'DELETE' THEN row_to_json(OLD) ELSE NULL END,
        CASE WHEN TG_OP IN ('INSERT', 'UPDATE') THEN row_to_json(NEW) ELSE NULL END,
        NOW()
    );
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;
```

**Apply to Tables:**
```sql
-- Customer table
CREATE TRIGGER audit_customer_changes
    AFTER INSERT OR UPDATE OR DELETE ON customer
    FOR EACH ROW EXECUTE FUNCTION audit.log_changes();

-- Repeat for: quote, job, invoice, payment, site, contact, 
-- address, time_entry, expense, catalog_item, pricebook_item
```

### Archive Task Pattern

**Reference:** `backend/tasks/cleanup_sessions.py` for Celery scheduled task pattern

**Archive Logic:**
- Move records where `changed_at < NOW() - INTERVAL '90 days'`
- Archive to S3 or separate `audit.event_archive` table (choose based on cost)
- Delete from hot `audit.event` table after successful archive
- Log archive metrics (records moved, errors)

**Celery Beat Schedule:**
```python
# backend/core/celery_app.py
beat_schedule = {
    'archive-audit-logs': {
        'task': 'backend.tasks.archive_audit_logs.archive_old_events',
        'schedule': crontab(hour=1, minute=0),  # Daily at 1 AM
    }
}
```

### API Query Patterns

**Filtering Requirements:**
- By entity_type (e.g., 'customer', 'quote')
- By entity_id (specific record)
- By user_id (who made the change)
- By date range (changed_at between X and Y)
- Always filter by tenant_id (automatic via middleware)

**Pagination:**
- Use offset/limit or cursor-based pagination
- Default page size: 50 records
- Max page size: 500 records

**Diff Calculation:**
- Compare `old_values_json` and `new_values_json`
- Return only changed fields: `[{field: "email", old: "a@x.com", new: "b@x.com"}]`
- Handle NULL values (insert has no old_values, delete has no new_values)

### Cost Awareness

**Storage Optimization:**
- Audit events grow linearly with mutations (~1KB per event)
- 100 customers × 10 changes/customer/month = 1,000 events/month = ~1MB/month
- At 100 tenants: ~100MB/month hot storage
- Archive to S3 Glacier after 90 days: $0.004/GB/month vs RDS $0.10/GB/month
- **Budget Impact:** Minimal (<$5/month for 100 tenants)

**Query Performance:**
- Index on `(tenant_id, entity_type, entity_id, changed_at DESC)`
- Index on `(tenant_id, changed_at DESC)` for timeline queries
- Partition table by month if growth exceeds 10M records (post-MVP)

## Questions to Ask

Before starting:
1. Have I read the gap analysis entry thoroughly? (Gap #29, line 891)
2. Have I reviewed the design specification? (db-process-v2.6h.md Section 8)
3. Do I understand the existing trigger pattern? (Quote/CO triggers migration)
4. What audit tables exist and what is their structure? (backend/app/models/system.py)
5. What tests need to be written? (Trigger firing, API queries, tenant isolation, diff calculation)

During implementation:
1. Am I following the existing database trigger pattern from Task 12?
2. Are ALL tests passing (100% pass rate)?
3. Am I documenting as I go?
4. Is the performance impact measured and <5ms per mutation?
5. Have I tested tenant isolation for audit queries?

After implementation:
1. Do I have 100% test pass rate (X/X passing, 0 failing)?
2. If tests fail, have I created a detailed fix document?
3. Have I marked the gap status correctly (RESOLVED vs PARTIALLY COMPLETE)?
4. Can another developer understand my implementation from the docs?
5. Are all three roadmap documents updated with appropriate detail levels?

## Example Task Flow

```bash
# 1. Review the task in current roadmap (PRIMARY SOURCE)
cat dev-docs/analysis/phase-4-5-implementation-roadmap.md | grep -A 50 "Task 20:"

# 2. Check historical roadmap for original plan context
cat dev-docs/analysis/phase-2-5-implementation-roadmap.md | grep -A 50 "Task 20:"

# 3. Check original gap for context (Gap 29 = Audit Event Logging)
cat dev-docs/analysis/phase-1-4-implementation-gap-analysis.md | grep -A 20 "### 29"

# 4. Review existing audit model
cat backend/app/models/system.py | grep -A 30 "class.*Event"

# 5. Review existing trigger pattern
ls -la backend/migrations/versions/*trigger*
cat backend/migrations/versions/2026_03_17_1451-a4d2659a2921_add_database_triggers_for_quote_totals_.py

# 6. Run existing tests to validate baseline (baseline: 339 passing)
cd backend && source .venv/bin/activate && pytest tests/ -v 2>&1 | grep -E "(passed|failed|===)" | tail -5

# 7. Create implementation plan
# [Review and get approval]

# 8. Create migration file
cd backend && source .venv/bin/activate
alembic revision -m "add_audit_logging_triggers"

# 9. Implement trigger functions and apply to tables
# [Edit migration file]

# 10. Create audit API routes
# [Create backend/api/routes/audit.py]

# 11. Create archive Celery task
# [Create backend/tasks/archive_audit_logs.py]

# 12. Write tests
# [Create backend/tests/test_audit_logging.py]

# 13. Run all tests (must maintain 100% pass rate)
pytest tests/ -v

# 14. Test audit trail manually
# Create customer → Edit customer → Query audit API → Verify diff

# 15. Update all three roadmap documents with appropriate detail levels
```

## Notes

- **MVP Focus:** Audit logging is CRITICAL for compliance (SOC 2, GDPR, PCI)
- **Performance:** Database triggers add <5ms overhead vs 20-50ms for middleware approach
- **Cannot Bypass:** Database-level enforcement prevents application bugs from skipping audit
- **Compliance:** 90-day hot retention + 7-year archive meets most regulatory requirements
- **Cost Impact:** Minimal (<$5/month for 100 tenants with S3 Glacier archival)
- **Infrastructure Constraints:** Respect $1k/mo budget cap - use S3 Glacier for cold archive
- **Phase 4 Focus:** Enterprise hardening (this is 1 of 4 critical security/compliance tasks)
- **Pattern Consistency:** Follow existing trigger pattern from Task 12 (Quote/CO totals)
- **Grey Areas:** If you are unsure about retention policy details or archive strategy, ask Tom

## Tables Requiring Audit Triggers (12 Critical Tables)

1. **customer** - Customer master data changes
2. **quote** - Quote creation, updates, approval tracking
3. **job** - Job status changes, completion tracking
4. **invoice** - Billing records (financial audit requirement)
5. **payment** - Payment records (financial audit requirement)
6. **site** - Site/location changes
7. **contact** - Contact information changes
8. **address** - Address changes (polymorphic)
9. **time_entry** - Labor tracking (profitability audit)
10. **expense** - Expense tracking (profitability audit)
11. **catalog_item** - Product catalog changes
12. **pricebook_item** - Internal pricing changes

**Note:** Apply triggers to tables with business-critical data. Skip reference tables (entity_type, contact_type) that rarely change.
```
