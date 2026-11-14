# Task #6: Multi-Tenancy Isolation Tests

Use this prompt to start the development task session for implementing comprehensive multi-tenancy isolation tests.

---

## PROMPT FOR TASK #6

```
Task: Implement Gap #38 - Multi-Tenancy Isolation Tests
Reference: dev-docs/analysis/phase-1-4-implementation-gap-analysis.md line 499, 626

## Context

We're building AevoFab AI, an AI-powered SaaS platform for electrical contractors with voice-controlled quoting and QuickBooks integration. Following the 80/20 rule to reach MVP quickly.

**Critical Security Gap:** While the backend implements basic tenant_id filtering across all routes, there is ZERO test coverage verifying that cross-tenant data access is actually prevented. This is a **BLOCKER** issue as it represents a potential data leakage vulnerability in production.

## Completed So Far

✅ Gap #28A: Test Endpoints - All endpoints have /test variants for dev testing
✅ Gap #40: Fixed current_user.tenant_id - All routes use AuthenticatedUser type
✅ Gap #28B: Idempotency Handling - Middleware prevents duplicate transactions
✅ Gap #1: X-Request-ID Tracing - Request tracking and logging implemented
✅ Gap #31-33: Database Triggers - Quote totals, change order totals, user email sync
✅ Gap #11: Tax Calculations - Jurisdiction-based tax with IRS-compliant rounding

## Current Task

**Implement comprehensive test suite to verify multi-tenancy isolation across all API endpoints and database operations.**

**Priority:** BLOCKER  
**Estimated Effort:** 3 days  
**Design Spec:** See dev-docs/analysis/phase-1-4-implementation-gap-analysis.md line 499
**Deliverable:** System safe for single-tenant pilot customer (Phase 1-A completion criteria)

## Requirements

### 1. Gap Analysis Context

**From phase-1-4-implementation-gap-analysis.md (line 499):**

```
### 38. **No Multi-Tenancy Isolation Tests** (BLOCKER)
**Missing:** Tests verifying User A from Tenant 1 cannot access Tenant 2 data  
**Risk:** Data leakage in production
```

**Current State (line 37):**
- ✓ Basic Tenant Isolation implemented - Queries filter by `tenant_id` across all routes
- ✓ Cognito JWT Verification - `backend/core/auth.py`
- ✓ TenantUser Association - Role & Status assignment
- ✗ NO TESTS verifying the isolation actually works

**Executive Summary Note (line 16):**
> Multi-Tenancy: Basic tenant_id filtering but missing comprehensive RBAC and polymorphic relationships

### 2. Test Coverage Requirements

The test suite must verify isolation across ALL entities:

#### Phase 1: Authentication & Multi-Tenancy
- ❌ User from Tenant A cannot list/view/update users from Tenant B
- ❌ Cross-tenant authentication attempts fail properly

#### Phase 2: Core Domain (CRM & Job Costing)
- ❌ Customers - Cannot list/view/update customers from other tenants
- ❌ Sites - Cannot access sites belonging to other tenant's customers
- ❌ Jobs - Cannot list/view/update jobs from other tenants
- ❌ Job Time Entries - Cannot view time entries for other tenant's jobs
- ❌ Job Expenses - Cannot access expenses for other tenant's jobs

#### Phase 3: Quote Engine
- ❌ Quotes - Cannot list/view/update quotes from other tenants
- ❌ Quote Lines - Cannot add lines to other tenant's quotes
- ❌ Quote Versions - Cannot access quote history from other tenants
- ❌ Public Links - Cannot generate/access links for other tenant's quotes

#### Phase 4: Voice AI
- ❌ Voice Sessions - Cannot access conversation sessions from other tenants
- ❌ Voice Telemetry - Cannot view AI metrics from other tenants

#### Catalog & Reference Data
- ❌ Supplier Items - Cannot access catalog items from other tenants
- ❌ Pricebook Items - Cannot view pricing from other tenants

### 3. Test Implementation Strategy

Create a new test file: **`backend/tests/test_multi_tenancy_isolation.py`**

#### Test Structure Pattern:
```python
import pytest
from fastapi.testclient import TestClient
from core.auth import create_access_token

class TestCustomerIsolation:
    """Verify customers are isolated by tenant_id"""
    
    def test_cannot_list_other_tenant_customers(
        self, client: TestClient, db_session
    ):
        # ARRANGE: Create two tenants with customers
        tenant_a = create_test_tenant(db_session, name="Tenant A")
        tenant_b = create_test_tenant(db_session, name="Tenant B")
        
        user_a = create_test_user(db_session, tenant_a.id)
        user_b = create_test_user(db_session, tenant_b.id)
        
        customer_a = create_test_customer(db_session, tenant_a.id, name="Customer A")
        customer_b = create_test_customer(db_session, tenant_b.id, name="Customer B")
        
        # ACT: User A tries to list customers
        token_a = create_access_token(user_a.id, tenant_a.id)
        response = client.get(
            "/api/v1/customers",
            headers={"Authorization": f"Bearer {token_a}"}
        )
        
        # ASSERT: Only sees their own tenant's data
        assert response.status_code == 200
        customers = response.json()
        assert len(customers) == 1
        assert customers[0]["id"] == str(customer_a.id)
        assert customers[0]["name"] == "Customer A"
        # Verify Tenant B customer is NOT in results
        customer_ids = [c["id"] for c in customers]
        assert str(customer_b.id) not in customer_ids
    
    def test_cannot_get_other_tenant_customer_by_id(
        self, client: TestClient, db_session
    ):
        # ARRANGE
        tenant_a = create_test_tenant(db_session, name="Tenant A")
        tenant_b = create_test_tenant(db_session, name="Tenant B")
        
        user_a = create_test_user(db_session, tenant_a.id)
        customer_b = create_test_customer(db_session, tenant_b.id, name="Customer B")
        
        # ACT: User A tries to access Tenant B's customer
        token_a = create_access_token(user_a.id, tenant_a.id)
        response = client.get(
            f"/api/v1/customers/{customer_b.id}",
            headers={"Authorization": f"Bearer {token_a}"}
        )
        
        # ASSERT: Should return 404 (not 403, to prevent enumeration)
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_cannot_update_other_tenant_customer(
        self, client: TestClient, db_session
    ):
        # ARRANGE
        tenant_a = create_test_tenant(db_session, name="Tenant A")
        tenant_b = create_test_tenant(db_session, name="Tenant B")
        
        user_a = create_test_user(db_session, tenant_a.id)
        customer_b = create_test_customer(db_session, tenant_b.id, name="Original Name")
        
        # ACT: User A tries to update Tenant B's customer
        token_a = create_access_token(user_a.id, tenant_a.id)
        response = client.patch(
            f"/api/v1/customers/{customer_b.id}",
            headers={"Authorization": f"Bearer {token_a}"},
            json={"name": "Hacked Name"}
        )
        
        # ASSERT: Should fail with 404
        assert response.status_code == 404
        
        # VERIFY: Original customer unchanged
        db_session.refresh(customer_b)
        assert customer_b.name == "Original Name"
```

#### Test Helper Functions Needed:
```python
# backend/tests/conftest.py additions

@pytest.fixture
def tenant_a(db_session):
    """Create test tenant A"""
    tenant = Tenant(
        id=uuid4(),
        name="Test Tenant A",
        subdomain="tenant-a-test",
        status="active"
    )
    db_session.add(tenant)
    db_session.commit()
    return tenant

@pytest.fixture
def tenant_b(db_session):
    """Create test tenant B (separate from A)"""
    tenant = Tenant(
        id=uuid4(),
        name="Test Tenant B",
        subdomain="tenant-b-test",
        status="active"
    )
    db_session.add(tenant)
    db_session.commit()
    return tenant

@pytest.fixture
def user_tenant_a(db_session, tenant_a):
    """User belonging to Tenant A"""
    user = User(
        id=uuid4(),
        email=f"user-a-{uuid4()}@example.com",
        cognito_user_id=f"cognito-a-{uuid4()}"
    )
    db_session.add(user)
    
    # Link to tenant
    tenant_user = TenantUser(
        tenant_id=tenant_a.id,
        user_id=user.id,
        status="active"
    )
    db_session.add(tenant_user)
    db_session.commit()
    return user

@pytest.fixture
def user_tenant_b(db_session, tenant_b):
    """User belonging to Tenant B"""
    user = User(
        id=uuid4(),
        email=f"user-b-{uuid4()}@example.com",
        cognito_user_id=f"cognito-b-{uuid4()}"
    )
    db_session.add(user)
    
    # Link to tenant
    tenant_user = TenantUser(
        tenant_id=tenant_b.id,
        user_id=user.id,
        status="active"
    )
    db_session.add(tenant_user)
    db_session.commit()
    return user
```

### 4. Test Scenarios by Entity

#### Minimum Required Tests (30-40 tests total):

1. **Customers** (4 tests)
   - ✓ Cannot list other tenant's customers
   - ✓ Cannot GET other tenant's customer by ID
   - ✓ Cannot PATCH other tenant's customer
   - ✓ Cannot DELETE other tenant's customer

2. **Sites** (4 tests)
   - ✓ Cannot list other tenant's sites
   - ✓ Cannot GET other tenant's site by ID
   - ✓ Cannot PATCH other tenant's site
   - ✓ Cannot create site for other tenant's customer

3. **Jobs** (5 tests)
   - ✓ Cannot list other tenant's jobs
   - ✓ Cannot GET other tenant's job by ID
   - ✓ Cannot PATCH other tenant's job
   - ✓ Cannot create time entry on other tenant's job
   - ✓ Cannot create expense on other tenant's job

4. **Quotes** (6 tests)
   - ✓ Cannot list other tenant's quotes
   - ✓ Cannot GET other tenant's quote by ID
   - ✓ Cannot PATCH other tenant's quote
   - ✓ Cannot create quote line on other tenant's quote
   - ✓ Cannot create quote version for other tenant's quote
   - ✓ Cannot create public link for other tenant's quote

5. **Catalog** (2 tests)
   - ✓ Cannot list other tenant's supplier items
   - ✓ Cannot GET other tenant's supplier item by ID

6. **Voice AI** (2 tests)
   - ✓ Cannot list other tenant's voice sessions
   - ✓ Cannot create voice transcript in other tenant's session

7. **Edge Cases** (3 tests)
   - ✓ Cannot create entity with manipulated tenant_id in request body
   - ✓ Polymorphic relationships respect tenant boundaries
   - ✓ Database-level tenant_id filtering cannot be bypassed

### 5. Documentation Standards

Create remediation plan: **`dev-docs/analysis/gap-38-multi-tenancy-isolation-remediation-plan.md`**

Include:
- Test design philosophy (fail with 404, not 403)
- Coverage matrix (entity × operation table)
- Test execution results
- Security recommendations for production

### 6. Testing Standards

- **Run existing tests first:** Ensure all 91+ existing tests still pass
- **Test file location:** `backend/tests/test_multi_tenancy_isolation.py`
- **Use existing fixtures:** Leverage `conftest.py` patterns
- **Minimum coverage:** 30 isolation tests covering all major entities
- **Edge case testing:** Verify no request body manipulation bypasses isolation

### 7. Code Standards

- **Follow existing patterns:** Check `backend/tests/test_auth.py` for auth patterns
- **Type hints required:** Use `AuthenticatedUser` for user context
- **Error handling:** Return 404 (not 403) to prevent tenant enumeration
- **Docstrings required:** Document what each test verifies
- **No feature creep:** Focus on isolation, not RBAC (that's Gap #41)

### 8. Database Standards

- **DO NOT hallucinate schema:** Review `backend/app/models/` first
- **Respect tenant isolation:** All test data uses proper `tenant_id` assignment
- **Use transactions:** Tests must clean up properly (already handled by fixtures)
- **Follow ORM patterns:** Use SQLModel relationships correctly

### 9. Workflow

1. **Read the gap analysis** - Understand the security risk (line 499)
2. **Review existing auth code** - Study `backend/core/auth.py`
3. **Create remediation plan** document with test matrix
4. **Review route implementations** - Verify all routes filter by tenant_id
5. **Implement test suite** - Create `test_multi_tenancy_isolation.py`
6. **Run all tests** - Must pass 91+ existing + 30+ new = 121+ total
7. **Update documentation** - Mark Gap #38 as RESOLVED
8. **Commit** with message: "test: add multi-tenancy isolation test suite (gap #38)"

## Key Files to Review

### Architecture
- `dev-docs/architecture-design/mvp-arch.md` - Multi-tenancy design
- `dev-docs/db-design/aevofab-db-process-v2.6h.md` - Tenant isolation patterns
- `dev-docs/analysis/phase-1-4-implementation-gap-analysis.md` - Gap #38 details (line 499)

### Backend Code
- `backend/core/auth.py` - JWT verification, `get_current_user()`, `AuthenticatedUser`
- `backend/api/routes/customers.py` - Example tenant filtering
- `backend/api/routes/jobs.py` - Example tenant filtering
- `backend/api/routes/quotes.py` - Example tenant filtering
- `backend/app/models/auth.py` - Tenant, User, TenantUser models

### Existing Tests
- `backend/tests/conftest.py` - Test fixtures
- `backend/tests/test_auth.py` - Authentication test patterns
- `backend/tests/test_phase2.py` - Customer/Job CRUD patterns
- `backend/tests/test_quotes.py` - Quote test patterns

## Success Criteria

- [ ] Remediation plan created: `gap-38-multi-tenancy-isolation-remediation-plan.md`
- [ ] Test file created: `backend/tests/test_multi_tenancy_isolation.py`
- [ ] Minimum 30 isolation tests implemented covering:
  - [ ] Customers (4 tests)
  - [ ] Sites (4 tests)
  - [ ] Jobs (5 tests)
  - [ ] Quotes (6 tests)
  - [ ] Catalog (2 tests)
  - [ ] Voice AI (2 tests)
  - [ ] Edge cases (3 tests)
- [ ] All existing tests still pass (91+ tests)
- [ ] All new tests pass (30+ tests)
- [ ] Total test count: 121+ passing
- [ ] Gap #38 marked RESOLVED in phase-1-4-implementation-gap-analysis.md
- [ ] Phase 1-A completion criterion met: "Cross-tenant access attempts return 403/404"
- [ ] Documentation includes security recommendations

## Questions to Ask Before Starting

1. Have I reviewed how `get_current_user()` injects `tenant_id` into requests?
2. Do I understand the difference between returning 404 vs 403 for security?
3. Have I identified all entities that require tenant isolation?
4. What existing test patterns can I reuse from `test_auth.py`?
5. How do I create JWT tokens for test users in different tenants?

## Questions During Implementation

1. Am I testing all CRUD operations (LIST, GET, PATCH, DELETE, CREATE)?
2. Are my fixtures creating truly isolated tenants?
3. Am I verifying data doesn't leak in LIST endpoints?
4. Am I testing nested resources (e.g., quote lines)?
5. Have I covered edge cases like request body manipulation?

## Example Test Execution

```bash
# 1. Activate virtual environment
cd backend && source .venv/bin/activate

# 2. Run existing tests to ensure baseline
pytest tests/ -v

# Expected: 91/91 tests passing

# 3. Create and run new isolation tests
pytest tests/test_multi_tenancy_isolation.py -v

# Expected: 30+/30+ tests passing

# 4. Run full suite
pytest tests/ -v

# Expected: 121+/121+ tests passing

# 5. Verify no tenant leakage
pytest tests/test_multi_tenancy_isolation.py -v -k "cannot"

# All tests with "cannot" should pass
```

## Security Considerations

### Why Return 404 Instead of 403?

**Anti-Enumeration Pattern:**
- ❌ **403 Forbidden:** "I found the resource, but you can't access it" → Confirms resource exists
- ✅ **404 Not Found:** "Resource doesn't exist (for you)" → Prevents tenant enumeration

**Example:**
```python
# BAD: Allows tenant enumeration
customer = db.query(Customer).filter(Customer.id == customer_id).first()
if customer.tenant_id != current_user.tenant_id:
    raise HTTPException(status_code=403)  # ❌ Confirms customer exists

# GOOD: Prevents enumeration
customer = db.query(Customer).filter(
    Customer.id == customer_id,
    Customer.tenant_id == current_user.tenant_id  # ✅ Part of WHERE clause
).first()
if not customer:
    raise HTTPException(status_code=404)  # ✅ Indistinguishable from non-existent
```

### Database-Level Verification

Ensure all queries include `tenant_id` in WHERE clause:
```python
# Pattern to verify in route implementations
db.query(Entity).filter(
    Entity.id == entity_id,
    Entity.tenant_id == current_user.tenant_id  # ✅ Always present
).first()
```

## Notes

- **MVP Focus:** Follow `dev-docs/product-requirements/mvp-prd.md` for scope
- **80/20 Rule:** See `.roo/rules-mvp-builder/80-20-prioritization.md`
- **Mike the Solo Contractor:** Our primary persona - security matters!
- **Phase 1-A Blocker:** This is the LAST critical gap before single-tenant pilot
- **Production Safety:** Without these tests, we cannot deploy safely

## Phase 1-A Completion Checkpoint

This task completes **Phase 1-A: Critical Blockers**. After this is done:

✅ 0. Test Endpoints (#28A) - COMPLETED
✅ 1. Fix current_user.tenant_id (#40) - COMPLETED
✅ 2. Idempotency Handling (#28B) - COMPLETED
✅ 3. X-Request-ID Tracing (#1) - COMPLETED
✅ 4. Database Triggers (#31-33) - COMPLETED
✅ 5. Tax Calculations (#11) - COMPLETED
🔄 6. Multi-Tenancy Isolation Tests (#38) - THIS TASK

**Deliverable:** System safe for single-tenant pilot customer

Next Phase: **Phase 1-B: Core Completeness** (Polymorphic relationships, Contact management, Voice actions)
```

---

## Usage

1. Copy the prompt section above
2. Start new Roo Coder session with the prompt
3. The AI will have full context for implementing multi-tenancy isolation tests
4. This is a **BLOCKER** issue - prioritize accordingly
