# Task Prompt: Phase 3, Task 17 - Sync Mapping & Upsert Logic

```
Task: Phase 3, Task #17 - Sync Mapping & Upsert Logic
Reference: dev-docs/analysis/phase-2-5-implementation-roadmap.md Task #17
(Original: Gap #23 in phase-1-4-implementation-gap-analysis.md)

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
✅ Celery Setup & Configuration (Task 12)
✅ Profitability Rollup Worker (Task 13)
✅ Notification Outbox Worker (Task 14 - Email verified, SMS deferred)
✅ Session Expiration & Cleanup (Task 15)

**Phase 3: QuickBooks Integration (IN PROGRESS - 1 of 4 complete)**
✅ OAuth 2.0 Flow & Hybrid Schema Refactoring (Task 16 - COMPLETE 2026-03-20)
  - OAuth flow tested with sandbox account
  - Tokens encrypted and stored securely
  - Token refresh mechanism working
  - Hybrid schema refactoring complete with indexed external_account_id

**Test Coverage:** 272/272 passing (100% pass rate)
**See:** dev-docs/analysis/phase-2-5-implementation-roadmap.md for full details

## Current Task

Implement the QuickBooks synchronization logic to prevent duplicate records and enable bidirectional data sync between AevoFab and QuickBooks Online. This task builds on the OAuth foundation from Task 16 and creates the core sync engine that will be triggered by webhooks (Task 19) and conflict resolution (Task 18).

**Current Risk:** Every sync creates duplicate customers because no deduplication logic exists. The `integration_sync_mapping` table exists but is not being populated.

**Priority:** BLOCKER (prevents duplicate records)
**Estimated Effort:** 6 days
**Task Spec:** See dev-docs/analysis/phase-2-5-implementation-roadmap.md Task #17 (lines 1036-1296)
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
- **Create implementation plan first** (task-17-sync-mapping-impl-plan.md) before coding
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
     - Example: `dev-docs/testing-support/task-17-test_quickbooks_sync_fixes.md`

**Test Execution:**
- **Current Baseline:** 272/272 tests passing - DO NOT regress this
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
- **Create new test file:** `backend/tests/test_quickbooks_sync.py`
- **Test coverage required:**
  - Unit tests for core sync logic (QuickBooksSync service class)
  - Integration tests with mocked QuickBooks API responses
  - Upsert logic verification (create vs update detection)
  - Deduplication tests (no duplicate records after multiple syncs)
  - Error handling and edge cases (missing fields, API failures)
  - Tenant isolation verification (multi-tenancy tests)
  - Version token tracking tests (SyncToken comparison)
  - Incremental sync tests (timestamp filtering)

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
- **Follow existing patterns** - Check similar implementations first (see Task 16 OAuth implementation)
- **Type hints required** - Use `AuthenticatedUser`, not `User`
- **Error handling** - RFC 7807 format (see existing routes)
- **Docstrings required** - Document all functions/classes
- **No feature creep** - Strictly follow 80/20 MVP prioritization
- **Phase 3 Cost Awareness** - QuickBooks API calls are free during sandbox testing but have rate limits; ensure incremental sync logic minimizes unnecessary API calls

### 4. Database Standards
- **DO NOT hallucinate schema** - Always read backend/app/models/*.py first
- **Schema already complete** - Task 16 created `app_service.external_account_id` and updated `integration_credential` with hybrid schema
- **Use existing models:** `IntegrationSyncMapping`, `IntegrationCredential`, `AppService`
- **Respect tenant isolation** - All queries filter by tenant_id
- **Follow ORM patterns** - Use SQLModel/SQLAlchemy correctly
- **Timezone awareness** - Use `AwareDatetime` type for all timestamp fields (already enforced in schema)

### 5. QuickBooks API Integration Standards

**API Endpoints (Sandbox):**
- **Base URL:** `https://sandbox-quickbooks.api.intuit.com/v3/company/{realmId}`
- **Customer Query:** `GET /v3/company/{realmId}/query?query=SELECT * FROM Customer WHERE MetaData.LastUpdatedTime > '{timestamp}'`
- **Customer Create:** `POST /v3/company/{realmId}/customer`
- **Customer Update:** `POST /v3/company/{realmId}/customer` (same endpoint, include `Id` and `SyncToken` in body)
- **Invoice Query:** `GET /v3/company/{realmId}/query?query=SELECT * FROM Invoice WHERE MetaData.LastUpdatedTime > '{timestamp}'`

**Authentication:**
- Use access token from Task 16 OAuth implementation
- Tokens are encrypted in `integration_credential.secret_json`
- Use `decrypt_token()` from `backend/core/encryption.py`
- Automatic refresh if token expires within 5 minutes (already implemented in Task 16)

**Field Mappings (QuickBooks ↔ AevoFab):**

Customer entity mapping:
```python
# QuickBooks → AevoFab
qb_customer["DisplayName"] → customer.display_name
qb_customer["CompanyName"] → customer.company_name
qb_customer["PrimaryEmailAddr"]["Address"] → customer.email_primary
qb_customer["PrimaryPhone"]["FreeFormNumber"] → customer.phone_primary
qb_customer["Id"] → integration_sync_mapping.external_id
qb_customer["SyncToken"] → integration_sync_mapping.external_version_token

# AevoFab → QuickBooks (reverse mapping)
```

**Version Token Strategy:**
- **QuickBooks:** Uses `SyncToken` field (auto-incremented integer string, e.g., "0", "1", "2")
- **AevoFab:** Uses `updated_at` timestamp (timezone-aware datetime)
- **Mapping Table:** Store both in `integration_sync_mapping`:
  - `external_version_token` = QuickBooks SyncToken
  - `internal_version_token` = AevoFab updated_at.isoformat()
  - `last_synced_at` = timestamp of last successful sync

### 6. Workflow
1. **Read the task roadmap** to understand the requirements (lines 1036-1296)
2. **Review design specs** (db-process-v2.6h.md, mvp-arch.md)
3. **Review Task 16 implementation** to understand OAuth token retrieval and encryption
4. **Create implementation plan** document with detailed tasks (task-17-sync-mapping-impl-plan.md)
5. **Get approval** on the plan before coding
6. **Implement** following the plan step-by-step:
   - Create `QuickBooksSync` service class
   - Implement customer sync (QB → AevoFab)
   - Implement customer sync (AevoFab → QB)
   - Implement incremental batch sync
   - Create Celery background tasks
   - Add sync trigger endpoints
7. **Write tests** alongside implementation
8. **Test with QuickBooks sandbox** using ngrok tunnel (already configured from Task 16)
9. **Run all tests** - Must pass before completion
10. **Update documentation** - **BOTH documents MUST be updated:**
   
   **Document 1: phase-2-5-implementation-roadmap.md (Active Task Tracking)**
   - Find Task 17 section (lines 1036-1296)
   - Check off completed deliverables using `- [x]` checkbox format
   - Update any inline status notes or test results
   - If all deliverables complete, update status to ✅ COMPLETE
   - If some deliverables incomplete, update status to ⚠️ PARTIALLY COMPLETE
   
   **Document 2: phase-1-4-implementation-gap-analysis.md (Historical Gap Tracking)**
   - Find Gap #23 section
   - Update the gap status at the top:
     - ✅ **RESOLVED** if all tests pass and implementation 100% complete
     - ⚠️ **PARTIALLY COMPLETE** if fix document created or deliverables incomplete
   - Add "Resolved Date" line if marking RESOLVED
   - Add implementation summary (what was built, files created/modified, test results)
   - Cross-reference to Task 17 in phase-2-5-implementation-roadmap.md
   
   **Both documents must match:**
   - If roadmap task shows incomplete deliverables → gap status = PARTIALLY COMPLETE
   - If roadmap task shows all complete + tests pass → gap status = RESOLVED

## Key Files to Review

### Architecture & Design
- `dev-docs/analysis/phase-2-5-implementation-roadmap.md` - **Task 17 details (lines 1036-1296)**
- `dev-docs/architecture-design/mvp-arch.md` - Overall system design
- `dev-docs/db-design/aevofab-db-process-v2.6h.md` - Database operations & schema
- `dev-docs/analysis/phase-1-4-implementation-gap-analysis.md` - Gap #23 context

### Task 16 Implementation (OAuth Foundation)
- `backend/api/routes/integrations.py` - OAuth endpoints to reference
- `backend/core/encryption.py` - Token encryption/decryption utilities
- `backend/app/models/system.py` - IntegrationCredential, IntegrationSyncMapping, AppService models
- `backend/tests/test_quickbooks_oauth.py` - OAuth test patterns to follow
- `dev-docs/testing-support/quickbooks-oauth-sandbox-testing.md` - Testing guide

### Backend Code to Create/Modify
- `backend/services/quickbooks_sync.py` - **NEW FILE** - Core sync service class
- `backend/tasks/quickbooks_sync.py` - **NEW FILE** - Celery background tasks
- `backend/api/routes/integrations.py` - **UPDATE** - Add sync trigger endpoints
- `backend/core/celery_app.py` - **UPDATE** - Register new Celery tasks in beat schedule
- `backend/tests/test_quickbooks_sync.py` - **NEW FILE** - Comprehensive test suite

### Database Models (Already Complete from Task 16)
- `backend/app/models/system.py` - Lines 253-280 (IntegrationCredential with hybrid schema)
- `backend/app/models/system.py` - Lines 117-142 (IntegrationSyncMapping)
- Migration already exists from Task 16 - no new migrations needed

## Success Criteria

**MUST COMPLETE ALL BEFORE MARKING GAP AS RESOLVED:**

- [ ] Implementation plan created and approved (task-17-sync-mapping-impl-plan.md)
- [ ] `QuickBooksSync` service class implemented with token management
- [ ] `sync_customer_from_qb()` method - QB → AevoFab sync (upsert logic)
- [ ] `sync_customer_to_qb()` method - AevoFab → QB sync (bidirectional)
- [ ] `sync_all_customers_from_qb()` method - Incremental batch sync with timestamp filtering
- [ ] Version token tracking (SyncToken comparison logic)
- [ ] Last sync timestamp tracking in `integration_sync_mapping`
- [ ] Celery background task for scheduled syncs (every 15 minutes)
- [ ] API endpoints to trigger manual syncs
- [ ] **ALL existing tests pass** (272/272 baseline maintained)
- [ ] **ALL new tests pass** (zero failures)
- [ ] **Test pass rate: 100%** (X/X passing, 0 failing)
- [ ] Tested with QuickBooks sandbox account via ngrok
- [ ] Documentation updated with what was delivered
- [ ] Code follows existing patterns from Task 16

**Functional Verification (with Sandbox):**
- [ ] Create customer in QuickBooks sandbox → appears in AevoFab after sync
- [ ] Edit customer in AevoFab → updates in QuickBooks immediately
- [ ] Run sync 100 times → no duplicate records created
- [ ] Version tokens tracked correctly in `integration_sync_mapping`
- [ ] Incremental sync only fetches changed records (verify query filter)
- [ ] Tenant isolation verified (sync only affects authenticated tenant)

**Gap Status in Analysis Doc:**
- ✅ **RESOLVED** - If all tests pass AND all functional verification complete
- ⚠️ **PARTIALLY COMPLETE** - If fix document created for failing tests OR sandbox testing incomplete
  - Must include: "Implementation complete, tests/verification requires fixes (see test_quickbooks_sync_fixes.md)"
  - Cannot mark RESOLVED until all tests pass AND sandbox verification complete

**If Tests Fail:**
- Create `dev-docs/testing-support/task-17-test_quickbooks_sync_fixes.md` with concrete fixes for ALL failing tests
- Update gap status to "PARTIALLY COMPLETE" in analysis doc
- Document exact steps to achieve 100% test pass rate
- Include time estimates for each fix

## Implementation Guidance

### 1. QuickBooksSync Service Class Structure

Create `backend/services/quickbooks_sync.py` with this structure:

```python
"""
QuickBooks synchronization service

Handles bidirectional sync between AevoFab and QuickBooks Online:
- Customer sync (QB ↔ AevoFab)
- Invoice sync (QB → AevoFab only, per design)
- Deduplication via integration_sync_mapping table
- Version token tracking for conflict detection
"""

class QuickBooksSync:
    def __init__(self, tenant_id: uuid.UUID, db: AsyncSession):
        """Initialize sync service for specific tenant"""
        
    async def get_access_token(self) -> tuple[str, str]:
        """Get decrypted access token and realm_id for tenant
        
        Returns: (access_token, realm_id)
        Raises: ValueError if QuickBooks not connected
        """
        
    async def sync_customer_from_qb(self, qb_customer: dict) -> Customer:
        """Sync single customer from QuickBooks to AevoFab
        
        Upsert logic:
        1. Check if mapping exists (query by external_id)
        2. If exists: UPDATE customer in AevoFab
        3. If not exists: CREATE customer + mapping record
        4. Update version tokens in mapping
        
        Returns: Customer entity (created or updated)
        """
        
    async def sync_customer_to_qb(self, customer_id: uuid.UUID) -> dict:
        """Sync AevoFab customer to QuickBooks
        
        Bidirectional sync:
        1. Get customer from AevoFab
        2. Check if mapping exists
        3. Transform to QuickBooks format
        4. Create or update in QuickBooks
        5. Update mapping with new SyncToken
        
        Returns: QuickBooks customer response
        """
        
    async def sync_all_customers_from_qb(self, since: datetime = None) -> int:
        """Incremental batch sync from QuickBooks
        
        Performance optimization:
        - Use timestamp filter to fetch only changed records
        - If since=None, sync all customers (initial sync)
        - If since provided, sync only customers modified after timestamp
        
        Returns: Count of customers synced
        """
```

### 2. Integration Sync Mapping Usage

The `integration_sync_mapping` table prevents duplicate records:

```python
# Check if customer already exists
mapping = await db.execute(
    select(IntegrationSyncMapping)
    .where(IntegrationSyncMapping.tenant_id == tenant_id)
    .where(IntegrationSyncMapping.app_service_id == app_service_id)
    .where(IntegrationSyncMapping.entity_type_code == "customer")
    .where(IntegrationSyncMapping.external_id == qb_customer["Id"])
)
mapping = mapping.scalar_one_or_none()

if mapping:
    # UPDATE existing customer
    customer = await db.get(Customer, mapping.entity_id)
    # ... update fields ...
else:
    # CREATE new customer + mapping
    customer = Customer(**customer_data)
    db.add(customer)
    await db.flush()  # Get customer.id
    
    new_mapping = IntegrationSyncMapping(
        tenant_id=tenant_id,
        entity_id=customer.id,
        entity_type_code="customer",
        app_service_id=app_service_id,
        external_id=qb_customer["Id"],
        external_version_token=qb_customer["SyncToken"],
        internal_version_token=customer.updated_at.isoformat(),
        last_synced_at=datetime.now(timezone.utc)
    )
    db.add(new_mapping)
```

### 3. Celery Background Task Pattern

Create `backend/tasks/quickbooks_sync.py`:

```python
from core.celery_app import celery_app
from services.quickbooks_sync import QuickBooksSync

@celery_app.task(name="sync_quickbooks_customers")
def sync_quickbooks_customers_task(tenant_id: str):
    """Scheduled sync triggered every 15 minutes"""
    # Implementation using QuickBooksSync service
    
# Register in celery_app.py beat_schedule:
beat_schedule = {
    "quickbooks-customer-sync": {
        "task": "sync_quickbooks_customers",
        "schedule": crontab(minute="*/15"),  # Every 15 minutes
    }
}
```

### 4. Testing with QuickBooks Sandbox

**Prerequisites (from Task 16):**
- ngrok tunnel running: `https://your-tunnel.ngrok-free.dev`
- QuickBooks sandbox company connected (Realm ID: 1234567890123456)
- OAuth tokens stored and valid

**Testing Workflow:**
1. Start ngrok tunnel: `ngrok http 8000 --domain=your-tunnel.ngrok-free.dev`
2. Start FastAPI app: `cd backend && uvicorn app.main:app --reload`
3. Create customer in QuickBooks sandbox UI: https://app.sandbox.qbo.intuit.com
4. Trigger manual sync: `POST /api/v1/integrations/quickbooks/sync/customers/test`
5. Verify customer in AevoFab database: `SELECT * FROM customer.customer WHERE ...`
6. Check mapping table: `SELECT * FROM integration.integration_sync_mapping WHERE ...`
7. Edit customer in AevoFab
8. Verify customer updates in QuickBooks sandbox UI

**Manual Testing Endpoints to Create:**
- `POST /api/v1/integrations/quickbooks/sync/customers/test` - Trigger customer sync (test endpoint)
- `GET /api/v1/integrations/quickbooks/sync/status/test` - Check last sync timestamp

## Questions to Ask

Before starting:
1. Have I reviewed Task 16 implementation to understand OAuth token flow?
2. Have I read the QuickBooks API documentation for Customer entity?
3. Do I understand the upsert logic using `integration_sync_mapping`?
4. What existing code can I reference for patterns? (Task 16 OAuth implementation)
5. What tests need to be written? (Upsert, deduplication, version tokens, tenant isolation)

During implementation:
1. Am I following existing patterns from Task 16?
2. Are ALL tests passing (100% pass rate)?
3. Am I using the hybrid schema correctly (external_account_id, explicit timestamps)?
4. Is this aligned with 80/20 MVP priorities? (Customer sync only, skip invoice sync for now?)
5. Am I minimizing QuickBooks API calls (incremental sync, not full sync every time)?

After implementation:
1. Do I have 100% test pass rate (X/X passing, 0 failing)?
2. Have I tested with QuickBooks sandbox account?
3. Can I demonstrate: Create in QB → sync → appears in AevoFab?
4. Can I demonstrate: Edit in AevoFab → sync → updates in QB?
5. Have I verified no duplicate records after 100 sync cycles?
6. If tests fail, have I created a detailed fix document?
7. Have I marked the gap status correctly (RESOLVED vs PARTIALLY COMPLETE)?

## Example Task Flow

```bash
# 1. Review Task 17 in roadmap
cat dev-docs/analysis/phase-2-5-implementation-roadmap.md | grep -A 260 "Task 17"

# 2. Review Gap #23 for context
cat dev-docs/analysis/phase-1-4-implementation-gap-analysis.md | grep -A 20 "Gap #23"

# 3. Review Task 16 OAuth implementation
cat backend/api/routes/integrations.py | grep -A 50 "def initiate_qbo_oauth"
cat backend/core/encryption.py

# 4. Check database models (already complete from Task 16)
cat backend/app/models/system.py | grep -A 30 "class IntegrationSyncMapping"

# 5. Run existing tests (baseline: 272 passing)
cd backend && source .venv/bin/activate && pytest tests/ -v

# 6. Create implementation plan
# [architect mode creates task-17-sync-mapping-impl-plan.md]

# 7. Implement QuickBooksSync service
# [write backend/services/quickbooks_sync.py]

# 8. Implement Celery tasks
# [write backend/tasks/quickbooks_sync.py]

# 9. Write comprehensive tests
# [write backend/tests/test_quickbooks_sync.py]

# 10. Run tests again (must maintain 100% pass rate)
pytest tests/ -v

# 11. Test with QuickBooks sandbox
# [manual testing via ngrok + sandbox account]
```

## Notes

- **MVP Focus:** Follow dev-docs/product-requirements/mvp-prd.md for scope
- **80/20 Rule:** Focus on Customer sync first; Invoice sync can be deferred to Task 18 or later if time-constrained
- **QuickBooks Sandbox:** Task 16 already configured sandbox connection - reuse credentials
- **ngrok Tunnel:** Already configured from Task 16 - ensure it's running for testing
- **Token Encryption:** Reuse `encrypt_token()` / `decrypt_token()` from Task 16
- **Incremental Sync:** Critical for performance - don't fetch all customers every time
- **Tenant Isolation:** Every query must filter by tenant_id (security requirement)
- **Grey Areas:** If you are unsure about QuickBooks API field mappings, ask Tom for clarification
```
