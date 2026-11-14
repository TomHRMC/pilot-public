# Task 18 Prompt: Conflict Detection & Resolution

Task: Phase 3, Task #18 - Conflict Detection & Resolution
Reference: dev-docs/analysis/phase-2-5-implementation-roadmap.md Task #18
(Original: Gap #24 in phase-1-4-implementation-gap-analysis.md)

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
✅ Notification Outbox Worker (Task 14)
✅ Session Expiration & Cleanup (Task 15)

**Phase 3: QuickBooks Integration (IN PROGRESS - 4 tasks)**
✅ Task 16: OAuth 2.0 Flow & Hybrid Schema Refactoring (COMPLETE)
✅ Task 17: Sync Mapping & Upsert Logic (COMPLETE - 27/27 tests passing)
⏸️ Task 18: Conflict Detection & Resolution (CURRENT TASK)
⬜ Task 19: Webhook Handler (NOT STARTED)

**Test Coverage:** 314/314 passing (100% pass rate)
**See:** dev-docs/analysis/phase-2-5-implementation-roadmap.md for full details

## Current Task

Implement conflict detection and resolution for QuickBooks bidirectional sync. When a customer is edited in both AevoFab and QuickBooks between sync cycles, detect the conflict using version tokens and queue it for manual resolution instead of silently overwriting data.

**Priority:** HIGH
**Estimated Effort:** 6 days
**Task Spec:** See dev-docs/analysis/phase-2-5-implementation-roadmap.md Task #18 (lines 1340-1566)
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
- **Create implementation plan first** (task-18-conflict-detection-impl-plan.md) before coding
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
     - Example: `dev-docs/testing-support/task-18-test_conflict_detection_fixes.md`

**Test Execution:**
- **Current Baseline:** 314/314 tests passing - DO NOT regress this
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
- **Create new test file:** `backend/tests/test_conflict_detection.py`
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
- **Type hints required** - Use AwareDatetime for timestamps, AuthenticatedUser not User
- **Error handling** - RFC 7807 format (see existing routes)
- **Docstrings required** - Document all functions/classes
- **No feature creep** - Strictly follow 80/20 MVP prioritization
- **Phase 3 Cost Awareness** - QuickBooks integration must respect $1k/mo budget cap

### 4. Database Standards
- **DO NOT hallucinate schema** - Always read backend/app/models/*.py first
- **Use Alembic migrations** for schema changes
- **Respect tenant isolation** - All queries filter by tenant_id
- **Follow ORM patterns** - Use SQLModel/SQLAlchemy correctly
- **Timezone compliance** - Use AwareDatetime and DateTime(timezone=True) for all timestamps

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
   - Find Task 18: Conflict Detection & Resolution section
   - Check off completed deliverables using `- [x]` checkbox format
   - Update any inline status notes or test results
   - If all deliverables complete, task is ✅ COMPLETE
   - If some deliverables incomplete, task is ⚠️ PARTIALLY COMPLETE
   
   **Document 2: phase-1-4-implementation-gap-analysis.md (Historical Gap Tracking)**
   - Find Gap #24: Conflict Resolution UI section
   - Update the gap status at the top:
     - ✅ **RESOLVED** if all tests pass and implementation 100% complete
     - ⚠️ **PARTIALLY COMPLETE** if fix document created or deliverables incomplete
   - Add "Resolved Date" line if marking RESOLVED
   - Add implementation summary (what was built, files created/modified, test results)
   - Cross-reference to task number (e.g., "See also: Task 18 in phase-2-5-implementation-roadmap.md")
   
   **Both documents must match:**
   - If roadmap task shows incomplete deliverables → gap status = PARTIALLY COMPLETE
   - If roadmap task shows all complete + tests pass → gap status = RESOLVED
   - Follow existing patterns from Phase 1-A/1-B completed tasks

## Key Files to Review

### Architecture
- `dev-docs/analysis/phase-2-5-implementation-roadmap.md` - **Active task roadmap (Task 18 at lines 1340-1566)**
- `dev-docs/architecture-design/mvp-arch.md` - Overall system design
- `dev-docs/db-design/aevofab-db-process-v2.6h.md` - Database operations & schema
- `dev-docs/analysis/phase-1-4-implementation-gap-analysis.md` - Historical gap tracking

### Backend Code
- `backend/app/models/system.py` - IntegrationSyncMapping, IntegrationSyncConflict models
- `backend/services/quickbooks_sync.py` - QuickBooksSync service (Task 17)
- `backend/api/routes/integrations.py` - QuickBooks OAuth & sync endpoints (Tasks 16-17)
- `backend/core/` - Core utilities (auth, db, middleware)
- `backend/tests/` - Test suite

### Recent Examples (Phase 2-3 Completed Work)
- **QuickBooks OAuth:** `backend/api/routes/integrations.py` (Task 16)
- **Sync Logic:** `backend/services/quickbooks_sync.py` (Task 17)
- **Schema Refactoring:** Migration adding external_account_id, connection_status, explicit timestamps
- **Test Patterns:** `backend/tests/test_quickbooks_oauth.py`, `test_quickbooks_sync.py`
- **Documentation:** `dev-docs/analysis/task-16-quickbooks-oauth-impl-plan.md`, `task-17-sync-mapping-impl-plan.md`

## Success Criteria

**MUST COMPLETE ALL BEFORE MARKING GAP AS RESOLVED:**

- [ ] Implementation plan created and approved (task-18-conflict-detection-impl-plan.md)
- [ ] Conflict detection logic implemented (compare version tokens)
- [ ] IntegrationSyncConflict table usage implemented
- [ ] Conflict queuing system working
- [ ] Conflict listing API endpoint (`GET /integrations/quickbooks/conflicts`)
- [ ] Conflict resolution API endpoint (`POST /conflicts/{id}/resolve`)
- [ ] Support for 3 resolution strategies: accept_local, accept_remote, merge
- [ ] Notification system triggers on conflict detection
- [ ] **ALL existing tests pass** (no regression from 314 baseline)
- [ ] **ALL new tests pass** (zero failures)
- [ ] **Test pass rate: 100%** (X/X passing, 0 failing)
- [ ] Documentation updated with what was delivered
- [ ] Code follows existing patterns and standards

**Conflict Detection Requirements:**
- ✅ Detect when both QuickBooks SyncToken AND AevoFab updated_at changed since last sync
- ✅ Store conflict in integration_sync_conflict table with both payloads
- ✅ Prevent automatic overwrites when conflict exists
- ✅ Support resolution via API (3 strategies)

**Gap Status in Analysis Doc:**
- ✅ **RESOLVED** - If all tests pass (implementation + tests 100% complete)
- ⚠️ **PARTIALLY COMPLETE** - If fix document created for failing tests
  - Must include: "Implementation complete, tests require fixes (see test_conflict_detection_fixes.md)"
  - Cannot mark RESOLVED until all tests pass

**If Tests Fail:**
- Create `dev-docs/testing-support/task-18-test_conflict_detection_fixes.md` with concrete fixes for ALL failing tests
- Update gap status to "PARTIALLY COMPLETE" in analysis doc
- Document exact steps to achieve 100% test pass rate
- Include time estimates for each fix

## Technical Implementation Details

### Conflict Detection Logic

**Scenario:**
1. User edits customer in AevoFab at 2:00 PM
2. Simultaneously, accountant edits same customer in QuickBooks at 2:01 PM
3. Sync runs at 2:05 PM → conflict detected (both version tokens changed)
4. Conflict queued for manual resolution

**Version Token Strategy:**
- **QuickBooks:** Uses `SyncToken` field (auto-incremented integer)
- **AevoFab:** Uses `updated_at` timestamp
- **Mapping Table:** Stores both tokens in integration_sync_mapping

**Core Detection Algorithm:**
```python
async def detect_conflict(self, customer_id: uuid.UUID, qb_customer: dict):
    """
    Detect if both systems modified the same record
    
    Returns: (has_conflict, mapping)
    """
    mapping = await self.get_mapping("customer", qb_customer["Id"])
    
    if not mapping:
        return False, None  # No conflict on first sync
    
    customer = await self.db.get(Customer, customer_id)
    
    # Check both version tokens
    qb_changed = qb_customer["SyncToken"] != mapping.external_version_token
    aevofab_changed = customer.updated_at.isoformat() != mapping.internal_version_token
    
    if qb_changed and aevofab_changed:
        # CONFLICT: Both sides modified since last sync
        return True, mapping
    
    return False, mapping
```

### Conflict Queuing

Store conflict details in `integration_sync_conflict` table:
```python
async def queue_conflict(self, customer_id: uuid.UUID, qb_customer: dict, mapping):
    """
    Store conflict for manual resolution
    """
    customer = await self.db.get(Customer, customer_id)
    
    conflict = IntegrationSyncConflict(
        tenant_id=self.tenant_id,
        sync_mapping_id=mapping.id,
        entity_type_code="customer",
        entity_id=customer.id,
        local_payload_json={
            "display_name": customer.display_name,
            "company_name": customer.company_name,
            "email_primary": customer.email_primary,
            "phone_primary": customer.phone_primary,
            "updated_at": customer.updated_at.isoformat(),
        },
        remote_payload_json={
            "DisplayName": qb_customer.get("DisplayName"),
            "CompanyName": qb_customer.get("CompanyName"),
            "PrimaryEmailAddr": qb_customer.get("PrimaryEmailAddr", {}).get("Address"),
            "PrimaryPhone": qb_customer.get("PrimaryPhone", {}).get("FreeFormNumber"),
            "SyncToken": qb_customer["SyncToken"],
            "MetaData": qb_customer.get("MetaData"),
        },
        resolution_strategy_code="manual",
        detected_at=datetime.now(timezone.utc)
    )
    self.db.add(conflict)
    await self.db.commit()
    
    # Send notification to tenant
    await create_notification(
        tenant_id=self.tenant_id,
        subject="QuickBooks Sync Conflict Detected",
        body=f"Customer '{customer.display_name}' was modified in both systems. Please resolve."
    )
```

### API Endpoints

**List Conflicts:**
```python
@router.get("/integrations/quickbooks/conflicts")
async def list_conflicts(
    current_user: AuthenticatedUser,
    skip: int = 0,
    limit: int = 20
):
    """List all unresolved conflicts for tenant"""
    conflicts = await db.execute(
        select(IntegrationSyncConflict)
        .where(IntegrationSyncConflict.tenant_id == current_user.tenant_id)
        .where(IntegrationSyncConflict.resolved_at == None)
        .order_by(IntegrationSyncConflict.detected_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return conflicts.scalars().all()
```

**Resolve Conflict:**
```python
@router.post("/integrations/quickbooks/conflicts/{conflict_id}/resolve")
async def resolve_conflict(
    conflict_id: uuid.UUID,
    resolution: ConflictResolution,
    current_user: AuthenticatedUser
):
    """
    Resolve conflict with user decision
    
    Resolution strategies:
    - accept_local: Keep AevoFab version, overwrite QuickBooks
    - accept_remote: Keep QuickBooks version, overwrite AevoFab
    - merge: User provides merged data (advanced)
    """
    conflict = await db.get(IntegrationSyncConflict, conflict_id)
    sync = QuickBooksSync(current_user.tenant_id, db)
    
    if resolution.strategy == "accept_local":
        await sync.sync_customer_to_qb(conflict.entity_id, force=True)
    elif resolution.strategy == "accept_remote":
        qb_customer = conflict.remote_payload_json
        await sync.sync_customer_from_qb(qb_customer, force=True)
    elif resolution.strategy == "merge":
        # Apply merged data to both systems
        merged_data = resolution.merged_payload
        customer = await db.get(Customer, conflict.entity_id)
        for key, value in merged_data.items():
            setattr(customer, key, value)
        await db.commit()
        await sync.sync_customer_to_qb(conflict.entity_id, force=True)
    
    # Mark conflict as resolved
    conflict.resolved_at = datetime.now(timezone.utc)
    conflict.resolved_by_user_id = current_user.user_id
    conflict.resolution_notes = resolution.notes
    await db.commit()
    
    return {"status": "resolved", "conflict_id": conflict_id}
```

### Modified Sync Logic

Update `QuickBooksSync.sync_customer_from_qb()` to detect conflicts:
```python
async def sync_customer_from_qb_with_conflict_detection(self, qb_customer: dict):
    """Modified sync logic with conflict detection"""
    mapping = await self.get_mapping("customer", qb_customer["Id"])
    
    if mapping:
        # Check for conflicts
        has_conflict, mapping = await self.detect_conflict(mapping.entity_id, qb_customer)
        
        if has_conflict:
            # Queue conflict instead of overwriting
            await self.queue_conflict(mapping.entity_id, qb_customer, mapping)
            return None  # Don't sync until resolved
    
    # No conflict, proceed with normal sync
    return await self.sync_customer_from_qb(qb_customer)
```

## Testing Requirements

### Test Scenarios

1. **No Conflict (Baseline)**
   - Create customer in QuickBooks
   - Sync to AevoFab
   - Verify no conflict record created

2. **QuickBooks-Only Change (No Conflict)**
   - Create customer in QuickBooks, sync to AevoFab
   - Edit customer in QuickBooks only
   - Sync again
   - Verify AevoFab updated, no conflict

3. **AevoFab-Only Change (No Conflict)**
   - Create customer in QuickBooks, sync to AevoFab
   - Edit customer in AevoFab only
   - Sync to QuickBooks
   - Verify QuickBooks updated, no conflict

4. **Simultaneous Edit (CONFLICT)**
   - Create customer in QuickBooks, sync to AevoFab
   - Edit display_name in AevoFab to "John Smith Electric"
   - Edit display_name in QuickBooks to "Smith Electrical Services"
   - Trigger sync
   - Verify conflict record created in database
   - Verify neither system overwritten
   - Verify notification sent

5. **Conflict Resolution - Accept Local**
   - Create conflict scenario (test #4)
   - Call conflict resolution API with strategy="accept_local"
   - Verify QuickBooks customer updated to AevoFab version
   - Verify conflict marked as resolved
   - Verify version tokens updated

6. **Conflict Resolution - Accept Remote**
   - Create conflict scenario
   - Call API with strategy="accept_remote"
   - Verify AevoFab customer updated to QuickBooks version
   - Verify conflict marked as resolved

7. **Conflict Resolution - Merge**
   - Create conflict scenario
   - Call API with strategy="merge" and merged_payload
   - Verify both systems updated with merged data
   - Verify conflict marked as resolved

8. **Tenant Isolation**
   - Create conflicts for two different tenants
   - Verify Tenant A cannot see or resolve Tenant B's conflicts
   - Verify API filters by tenant_id correctly

### Test File Structure

```python
# backend/tests/test_conflict_detection.py

import pytest
from datetime import datetime, timezone
from app.models.system import IntegrationSyncConflict

class TestConflictDetection:
    """Test conflict detection logic"""
    
    async def test_no_conflict_on_first_sync(self, db_session, test_tenant):
        """First sync should never create conflict"""
        
    async def test_no_conflict_when_only_qb_changed(self, db_session, test_tenant):
        """QuickBooks-only change should sync normally"""
        
    async def test_no_conflict_when_only_aevofab_changed(self, db_session, test_tenant):
        """AevoFab-only change should sync normally"""
        
    async def test_conflict_when_both_systems_changed(self, db_session, test_tenant):
        """Simultaneous edits should create conflict record"""

class TestConflictQueuing:
    """Test conflict queue creation"""
    
    async def test_conflict_record_created_with_payloads(self, db_session, test_tenant):
        """Conflict record should store both versions"""
        
    async def test_notification_sent_on_conflict(self, db_session, test_tenant):
        """Notification should be queued when conflict detected"""

class TestConflictResolutionAPI:
    """Test conflict resolution endpoints"""
    
    async def test_list_conflicts_endpoint(self, client, test_tenant, test_user):
        """GET /integrations/quickbooks/conflicts should return unresolved conflicts"""
        
    async def test_resolve_conflict_accept_local(self, client, test_tenant, test_user):
        """Resolution strategy 'accept_local' should overwrite QuickBooks"""
        
    async def test_resolve_conflict_accept_remote(self, client, test_tenant, test_user):
        """Resolution strategy 'accept_remote' should overwrite AevoFab"""
        
    async def test_resolve_conflict_merge(self, client, test_tenant, test_user):
        """Resolution strategy 'merge' should apply merged data to both systems"""

class TestConflictTenantIsolation:
    """Test multi-tenancy for conflicts"""
    
    async def test_conflicts_filtered_by_tenant(self, db_session, test_tenant, test_tenant2):
        """Tenant A cannot see Tenant B's conflicts"""
```

## Questions to Ask

Before starting:
1. Have I read the roadmap Task 18 section thoroughly?
2. Have I reviewed the QuickBooksSync service from Task 17?
3. Do I understand the IntegrationSyncConflict model structure?
4. What existing code can I reference for patterns?
5. What tests need to be written?

During implementation:
1. Am I following existing patterns from Tasks 16-17?
2. Are ALL tests passing (100% pass rate)?
3. Am I documenting as I go?
4. Is conflict detection working correctly?
5. Are version tokens tracked accurately?

After implementation:
1. Do I have 100% test pass rate (X/X passing, 0 failing)?
2. If tests fail, have I created a detailed fix document?
3. Have I marked the gap status correctly (RESOLVED vs PARTIALLY COMPLETE)?
4. Can another developer execute my test fixes successfully?
5. Can conflicts be resolved via all 3 strategies?

## Example Task Flow

```bash
# 1. Review Task 18 in roadmap
cat dev-docs/analysis/phase-2-5-implementation-roadmap.md | grep -A 200 "Task 18"

# 2. Review IntegrationSyncConflict model
cat backend/app/models/system.py | grep -A 50 "IntegrationSyncConflict"

# 3. Review QuickBooksSync service (Task 17)
cat backend/services/quickbooks_sync.py | head -100

# 4. Run existing tests (baseline: 314 passing)
cd backend && source .venv/bin/activate && pytest tests/ -v

# 5. Create implementation plan
# Write dev-docs/analysis/task-18-conflict-detection-impl-plan.md

# 6. Implement conflict detection
# Modify backend/services/quickbooks_sync.py

# 7. Implement conflict APIs
# Modify backend/api/routes/integrations.py

# 8. Write tests
# Create backend/tests/test_conflict_detection.py

# 9. Run tests again (must maintain 100% pass rate)
pytest tests/ -v

# 10. Test manually with QuickBooks sandbox
# Create conflict scenario and verify API responses
```

## Notes

- **MVP Focus:** Follow dev-docs/product-requirements/mvp-prd.md for scope
- **80/20 Rule:** See .roo/rules-mvp-builder/80-20-prioritization.md
- **Mike the Solo Contractor:** Our primary persona - keep conflict resolution simple and clear
- **No Enterprise Features:** Complex merge UIs or automatic resolution strategies are out of scope for MVP
- **Grey Areas:** If you are unsure, ask Tom, the solo-entrepreneur developing the application with you
- **Dependencies:** This task builds on Tasks 16 (OAuth) and 17 (Sync Logic) - review those implementations first
- **Frontend:** Conflict resolution UI is deferred to Phase 5 or later - API-only for MVP
- **QuickBooks Sandbox:** Use sandbox company from Task 16 for testing conflict scenarios
