# Task 19 Implementation Prompt

```
Task: Phase 3, Task #19 - QuickBooks Webhook Handler
Reference: dev-docs/analysis/phase-2-5-implementation-roadmap.md Task #19
(Original: Gap #27 in phase-1-4-implementation-gap-analysis.md)

## Context

We're building AevoFab AI, an AI-powered SaaS platform for electrical contractors with voice-controlled quoting and QuickBooks integration. Following the 80/20 rule to reach MVP quickly.

## Completed So Far

**Phase 1-A: Critical Blockers (COMPLETE - 7 tasks)**
✅ Test Endpoints, Tenant ID Fix, Idempotency, Request Tracing
✅ Database Triggers, Tax Calculations, Multi-Tenancy Tests

**Phase 1-B: Core Completeness (COMPLETE - 4 tasks)**
✅ Polymorphic Relationships, Contact Management
✅ Quote Acceptance Workflow, Voice Action Execution

**Phase 2: Background Processing (COMPLETE - 4 tasks)**
✅ Celery Setup & Configuration
✅ Profitability Rollup Worker
✅ Notification Outbox Worker
✅ Session Expiration & Cleanup

**Phase 3: QuickBooks Integration (IN PROGRESS - 3 of 4 tasks complete)**
✅ Task 16: OAuth 2.0 Flow & Hybrid Schema Refactoring
✅ Task 17: Sync Mapping & Upsert Logic
✅ Task 18: Conflict Detection & Resolution

**Test Coverage:** 326/326 passing (100% pass rate)
**See:** dev-docs/analysis/phase-2-5-implementation-roadmap.md for full details

## Current Task

Implement the QuickBooks webhook handler to enable **real-time sync** triggered by QuickBooks Cloud Events. When customers, invoices, or payments are created/updated/deleted in QuickBooks, a webhook notification is sent to AevoFab, which immediately triggers an incremental sync via Celery background tasks.

**Priority:** HIGH (enables real-time sync)
**Estimated Effort:** 3 days
**Task Spec:** See dev-docs/analysis/phase-2-5-implementation-roadmap.md Task #19 (lines 1604-1941)
**Design Context:** dev-docs/db-design/aevofab-db-process-v2.6h.md

**ngrok Public Endpoint:** `https://your-tunnel.ngrok-free.dev/api/v1/webhooks/quickbooks`

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
- **Create implementation plan first** (task-19-webhook-handler-impl-plan.md) before coding
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
     - Example: `dev-docs/testing-support/task-19-test_webhook_handler_fixes.md`

**Test Execution:**
- **Current Baseline:** 326/326 tests passing - DO NOT regress this
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
- **Create new test file:** `backend/tests/test_webhook_handler.py`
- **Test coverage required:**
  - HMAC signature verification (valid/invalid/missing)
  - Cloud Events payload parsing
  - Tenant lookup from realm_id (success/failure)
  - Background task triggering (Customer/Invoice entities)
  - Webhook event logging
  - Error handling and edge cases
  - Tenant isolation verification

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
- **Phase 3 QuickBooks Integration** - Respect webhook security requirements (HMAC validation)

### 4. Database Standards
- **DO NOT hallucinate schema** - Always read backend/app/models/*.py first
- **Use Alembic migrations** for schema changes (WebhookEvent table)
- **Respect tenant isolation** - All queries filter by tenant_id
- **Follow ORM patterns** - Use SQLModel/SQLAlchemy correctly

### 5. Workflow
1. **Read the task roadmap** to understand the requirements (lines 1604-1941)
2. **Review design specs** (db-process-v2.6h.md, mvp-arch.md)
3. **Create implementation plan** document with detailed tasks
4. **Get approval** on the plan before coding
5. **Implement** following the plan step-by-step
6. **Write tests** alongside implementation
7. **Run all tests** - Must pass before completion
8. **Update documentation** - **BOTH documents MUST be updated:**
   
   **Document 1: phase-2-5-implementation-roadmap.md (Active Task Tracking)**
   - Find your task section (Task 19: Webhook Handler)
   - Check off completed deliverables using `- [x]` checkbox format
   - Update any inline status notes or test results
   - If all deliverables complete, task is ✅ COMPLETE
   - If some deliverables incomplete, task is ⚠️ PARTIALLY COMPLETE
   
   **Document 2: phase-1-4-implementation-gap-analysis.md (Historical Gap Tracking)**
   - Find the original gap section (Gap #27: Webhook Delivery Worker)
   - Update the gap status at the top:
     - ✅ **RESOLVED** if all tests pass and implementation 100% complete
     - ⚠️ **PARTIALLY COMPLETE** if fix document created or deliverables incomplete
   - Add "Resolved Date" line if marking RESOLVED
   - Add implementation summary (what was built, files created/modified, test results)
   - Cross-reference to task number (e.g., "See also: Task 19 in phase-2-5-implementation-roadmap.md")
   
   **Both documents must match:**
   - If roadmap task shows incomplete deliverables → gap status = PARTIALLY COMPLETE
   - If roadmap task shows all complete + tests pass → gap status = RESOLVED
   - Follow existing patterns from Phase 1-A/1-B/Phase 2 completed tasks

## Key Files to Review

### Architecture & QuickBooks Context
- `dev-docs/analysis/phase-2-5-implementation-roadmap.md` - **Task 19 spec (lines 1604-1941)**
- `dev-docs/architecture-design/mvp-arch.md` - Overall system design
- `dev-docs/db-design/aevofab-db-process-v2.6h.md` - Database operations & schema
- `dev-docs/analysis/phase-1-4-implementation-gap-analysis.md` - Original Gap #27

### Existing QuickBooks Implementation
- `backend/api/routes/integrations.py` - OAuth & sync endpoints (Task 16)
- `backend/services/quickbooks_sync.py` - Sync service class (Task 17)
- `backend/tasks/quickbooks_sync.py` - Celery background tasks (Task 17)
- `backend/core/encryption.py` - Token encryption utilities (Task 16)
- `backend/app/models/system.py` - IntegrationCredential, AppService models

### Backend Code
- `backend/app/models/` - Database models (SQLModel ORM)
- `backend/api/routes/webhooks.py` - **UPDATE THIS FILE** (existing webhook stubs)
- `backend/core/` - Core utilities (auth, db, middleware)
- `backend/tasks/` - Background jobs (Celery)
- `backend/tests/` - Test suite

### Recent Examples (Phase 2 & 3 Completed Work)
- **Celery Tasks:** `backend/tasks/cleanup_sessions.py`, `backend/tasks/quickbooks_sync.py`
- **QuickBooks OAuth:** `backend/tests/test_quickbooks_oauth.py` (47 tests)
- **QuickBooks Sync:** `backend/tests/test_quickbooks_sync.py` (27 tests)
- **Conflict Detection:** `backend/tests/test_conflict_detection.py` (15 tests)
- **Middleware:** `backend/core/idempotency.py` (security patterns)

## Technical Specifications

### ngrok Development Environment

**ngrok Public URL:** `https://your-tunnel.ngrok-free.dev`

This ngrok tunnel enables QuickBooks webhook callbacks during local development:
- **Webhook Endpoint:** `https://your-tunnel.ngrok-free.dev/api/v1/webhooks/quickbooks`
- **OAuth Redirect URI:** `https://your-tunnel.ngrok-free.dev/api/v1/integrations/quickbooks/callback`
- **Disconnect URI:** `https://your-tunnel.ngrok-free.dev/api/v1/integrations/quickbooks/disconnect`

**Critical:** The ngrok URL must remain stable during development. If ngrok URL changes, the QuickBooks app configuration must be updated in the Intuit Developer Portal.

### QuickBooks Cloud Events Payload Format

**IMPORTANT:** QuickBooks uses the CloudEvents 1.0 specification (industry-standard format). Enable "Cloud event payload format" checkbox in Intuit Developer Portal → Webhooks section.

**Example Payload:**
```json
{
  "specversion": "1.0",
  "type": "com.intuit.quickbooks.customer.create",
  "source": "//quickbooks.api.intuit.com/company/123456789",
  "id": "d9f5b5e8-3c8e-4f5e-8f5e-5f5e5f5e5f5e",
  "time": "2026-03-20T20:05:00Z",
  "datacontenttype": "application/json",
  "data": {
    "realmId": "123456789",
    "entityName": "Customer",
    "entityId": "67",
    "lastUpdated": "2026-03-20T20:05:00Z"
  }
}
```

**Event Types:**
- `com.intuit.quickbooks.customer.create`
- `com.intuit.quickbooks.customer.update`
- `com.intuit.quickbooks.customer.delete`
- `com.intuit.quickbooks.invoice.create`
- `com.intuit.quickbooks.invoice.update`
- `com.intuit.quickbooks.payment.create`

### Security: HMAC-SHA256 Signature Verification

**Critical Security Requirement:** All webhook requests MUST verify the HMAC signature to prevent spoofing attacks.

**Implementation Pattern:**
```python
# backend/core/quickbooks_webhook.py (NEW FILE)

import hmac
import hashlib
from fastapi import HTTPException, Request
from core.config import settings

async def verify_quickbooks_signature(request: Request, payload: bytes) -> bool:
    """
    Verify webhook authenticity using HMAC-SHA256
    
    Intuit sends signature in header: intuit-signature
    """
    signature = request.headers.get("intuit-signature")
    if not signature:
        raise HTTPException(401, detail="Missing signature header")
    
    # Get verifier token from environment
    verifier_token = settings.QUICKBOOKS_WEBHOOK_VERIFIER_TOKEN
    
    # Calculate expected signature
    expected_signature = hmac.new(
        verifier_token.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    # Compare signatures (timing-safe)
    if not hmac.compare_digest(signature, expected_signature):
        raise HTTPException(401, detail="Invalid signature")
    
    return True
```

**Environment Variable:**
```bash
# backend/.env
QUICKBOOKS_WEBHOOK_VERIFIER_TOKEN=<your_qb_webhook_verifier_token>
```

### Webhook Flow Architecture

```
QuickBooks detects change (customer created/updated/deleted)
   ↓
POST webhook to ngrok URL with HMAC signature
   ↓
ngrok forwards to localhost:8000
   ↓
Verify HMAC-SHA256 signature (security)
   ↓
Parse Cloud Events payload (get entity type + realm_id)
   ↓
Look up tenant_id from realm_id (via AppService.external_account_id)
   ↓
Trigger Celery task for incremental sync (QuickBooksSync service)
   ↓
Log webhook event to webhook_event table
   ↓
Return 200 OK within 5 seconds (QuickBooks requirement)
```

### Tenant Lookup from realm_id

**Critical for Webhook Routing:** The webhook must efficiently look up which tenant owns the QuickBooks company (realm_id) using the indexed `external_account_id` field (added in Task 16).

```python
async def get_tenant_by_realm_id(realm_id: str, db: AsyncSession) -> str | None:
    """
    Look up tenant_id from QuickBooks realm_id
    
    Uses indexed AppService.external_account_id for O(1) lookup
    """
    from app.models.system import AppService
    
    result = await db.execute(
        select(AppService)
        .where(AppService.external_account_id == realm_id)
        .where(AppService.provider_code == "quickbooks")
        .where(AppService.is_active == True)
    )
    service = result.scalar_one_or_none()
    return service.tenant_id if service else None
```

### Webhook Event Logging

**New Database Table Required:**

```python
# backend/app/models/system.py (add to existing file)

from sqlalchemy import JSONB, Column
from sqlalchemy.orm import Mapped, mapped_column
from pydantic import AwareDatetime

class WebhookEvent(StandardAuditMixin, SQLModel, table=True):
    __tablename__ = "webhook_event"
    __table_args__ = {"schema": "integration"}
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID | None = Field(
        default=None, foreign_key="tenant.id", index=True
    )
    source_app: str = Field(nullable=False, index=True)  # "quickbooks"
    event_type: str = Field(nullable=False)  # "com.intuit.quickbooks.customer.create"
    event_id: str | None = Field(default=None)  # CloudEvents ID
    payload_json: dict = Field(sa_column=Column(JSONB, nullable=False))
    signature_valid: bool = Field(nullable=False)
    processed_at: AwareDatetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True))
    )
    error_message: str | None = Field(default=None)
```

**Alembic Migration Required:** Create migration to add the `webhook_event` table with proper indexes.

### Celery Background Task Integration

**Leverage Existing Sync Infrastructure (Task 17):**

```python
# backend/tasks/quickbooks_sync.py (add to existing file)

@celery_app.task(name="sync_quickbooks_entity")
def sync_quickbooks_entity_task(
    tenant_id: str,
    entity_type: str,
    entity_id: str,
    operation: str
):
    """
    Sync a single entity triggered by webhook
    
    Faster than full sync (only fetches one record)
    """
    async with AsyncSession(engine) as db:
        sync = QuickBooksSync(tenant_id, db)
        
        if entity_type == "Customer":
            if operation == "delete":
                # Soft delete in AevoFab
                await sync.soft_delete_customer(entity_id)
            else:
                # Fetch customer from QuickBooks API
                qb_customer = await sync.fetch_customer_by_id(entity_id)
                # Sync to AevoFab (with conflict detection)
                await sync.sync_customer_from_qb(qb_customer)
        
        elif entity_type == "Invoice":
            # One-way sync: QB → AevoFab only
            qb_invoice = await sync.fetch_invoice_by_id(entity_id)
            await sync.sync_invoice_from_qb(qb_invoice)
        
        return f"Synced {entity_type} {entity_id}"
```

## Success Criteria

**MUST COMPLETE ALL BEFORE MARKING GAP AS RESOLVED:**

- [ ] Implementation plan created and approved (task-19-webhook-handler-impl-plan.md)
- [ ] Webhook receiver endpoint implemented (`POST /webhooks/quickbooks`)
- [ ] HMAC-SHA256 signature verification working (security)
- [ ] Cloud Events payload parsing implemented
- [ ] Tenant lookup from realm_id working (indexed query)
- [ ] Background task triggering for Customer entity
- [ ] Background task triggering for Invoice entity
- [ ] WebhookEvent table created (Alembic migration)
- [ ] Webhook event logging implemented
- [ ] Error handling for failed signature validation
- [ ] Error handling for tenant not found
- [ ] Error handling for unknown entity types
- [ ] **ALL existing tests pass** (no regression from 326/326 baseline)
- [ ] **ALL new tests pass** (zero failures)
- [ ] **Test pass rate: 100%** (X/X passing, 0 failing)
- [ ] Documentation updated with what was delivered
- [ ] Code follows existing patterns and standards

**Deliverables Checklist (from roadmap):**
- [ ] Webhook receiver endpoint (`POST /webhooks/quickbooks`)
- [ ] HMAC-SHA256 signature verification
- [ ] Entity-specific sync triggers (Customer, Invoice)
- [ ] Webhook event logging table
- [ ] Background task processing (Celery)
- [ ] ngrok integration testing guide

**Real-World Testing Criteria:**
- ✅ Create customer in QuickBooks sandbox → webhook received within 1 second
- ✅ Webhook signature validates correctly (no 401 errors)
- ✅ Customer syncs to AevoFab within 5 seconds
- ✅ Webhook event logged in database with all fields populated
- ✅ Failed webhooks don't crash the API (error handling)

**Gap Status in Analysis Doc:**
- ✅ **RESOLVED** - If all tests pass (implementation + tests 100% complete)
- ⚠️ **PARTIALLY COMPLETE** - If fix document created for failing tests
  - Must include: "Implementation complete, tests require fixes (see test_webhook_handler_fixes.md)"
  - Cannot mark RESOLVED until all tests pass

**If Tests Fail:**
- Create `dev-docs/testing-support/task-19-test_webhook_handler_fixes.md` with concrete fixes for ALL failing tests
- Update gap status to "PARTIALLY COMPLETE" in analysis doc
- Document exact steps to achieve 100% test pass rate
- Include time estimates for each fix

## Questions to Ask

Before starting:
1. Have I read the Task 19 roadmap section thoroughly? (lines 1604-1941)
2. Have I reviewed the Cloud Events payload format?
3. Do I understand the HMAC signature verification requirement?
4. Have I reviewed the existing QuickBooksSync service (Task 17)?
5. Do I understand how ngrok forwards requests to localhost?

During implementation:
1. Am I following existing webhook patterns?
2. Is HMAC signature verification working correctly?
3. Are ALL tests passing (100% pass rate)?
4. Am I documenting as I go?
5. Is this aligned with 80/20 MVP priorities?

After implementation:
1. Do I have 100% test pass rate (X/X passing, 0 failing)?
2. If tests fail, have I created a detailed fix document?
3. Have I marked the gap status correctly (RESOLVED vs PARTIALLY COMPLETE)?
4. Can I successfully test with QuickBooks sandbox via ngrok?
5. Does the webhook respond within 5 seconds (QuickBooks requirement)?

## Example Task Flow

```bash
# 1. Review the task in roadmap
cat dev-docs/analysis/phase-2-5-implementation-roadmap.md | grep -A 340 "Task 19"

# 2. Check original gap for context
cat dev-docs/analysis/phase-1-4-implementation-gap-analysis.md | grep -A 30 "Gap #27"

# 3. Review existing QuickBooks integration
cat backend/api/routes/integrations.py | grep -A 20 "quickbooks"
cat backend/services/quickbooks_sync.py | grep -A 20 "class QuickBooksSync"

# 4. Check webhook stubs
cat backend/api/routes/webhooks.py

# 5. Run existing tests (baseline: 326 passing)
cd backend && source .venv/bin/activate && pytest tests/ -v

# 6. Start ngrok tunnel (keep running during development)
ngrok http 8000 --domain=your-tunnel.ngrok-free.dev

# 7. Start FastAPI app in separate terminal
cd backend && source .venv/bin/activate && uvicorn app.main:app --reload

# 8. Monitor ngrok dashboard (view incoming webhooks)
open http://127.0.0.1:4040

# 9. Create your implementation
# [write code]

# 10. Test with QuickBooks sandbox
# - Create customer in QuickBooks UI
# - Watch ngrok dashboard for webhook POST
# - Verify signature validation passes
# - Check Celery worker logs for sync task

# 11. Run tests again (must maintain 100% pass rate)
pytest tests/ -v
```

## Notes

### MVP Focus
- **Primary Goal:** Enable real-time sync for Customer and Invoice entities
- **Out of Scope:** Advanced webhook features (retry logic, rate limiting, webhook verification endpoint)
- **80/20 Rule:** Focus on the most common webhook events (create/update), defer edge cases

### ngrok-Specific Considerations
- **Public Endpoint:** ngrok URL is publicly accessible, HMAC signature verification is CRITICAL
- **ngrok Dashboard:** Use http://127.0.0.1:4040 to view all incoming webhook requests in real-time
- **ngrok Stability:** If ngrok crashes or URL changes, update QuickBooks app configuration in Intuit Developer Portal
- **Production Migration:** Replace ngrok with production domain when deploying to AWS

### QuickBooks Webhook Requirements
- **Response Time:** Must respond with 200 OK within 5 seconds
- **Signature Validation:** Must validate HMAC signature on every request (security)
- **Idempotency:** Same webhook may be delivered multiple times (use event_id for deduplication)
- **Error Handling:** Failed webhooks should log errors but not crash the API

### Testing with QuickBooks Sandbox
1. Connect to sandbox QB company (Task 16 OAuth flow)
2. Create test data in QuickBooks sandbox UI
3. Monitor ngrok dashboard for incoming webhooks
4. Verify Celery worker processes sync tasks
5. Check AevoFab database for updated records
6. Verify `webhook_event` table logs all events

### Common Issues & Debugging
- **401 Invalid Signature:** Verifier token mismatch - copy from Intuit Developer Portal
- **Timeout (5 seconds):** Use `background_tasks.add_task()` for async processing
- **ngrok URL Changed:** Update webhook endpoint in QuickBooks app settings
- **No Tenant Found:** Ensure OAuth connection completed (realm_id stored in AppService)
- **Duplicate Events:** Use `event_id` field for idempotency checking

### Grey Areas
If you are unsure about any implementation details, ask Tom, the solo-entrepreneur developing the application with you.
```
