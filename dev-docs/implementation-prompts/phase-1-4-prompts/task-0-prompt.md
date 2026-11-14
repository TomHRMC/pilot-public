# Week 1, Days 1-2: Implement Test Endpoints (Gap #28A)

**Task:** Implement unauthenticated `/test` endpoint variants for all authenticated API routes to enable rapid development without JWT token generation overhead.

---

## Context Documents (READ THESE FIRST)

1. **Gap Analysis:** `dev-docs/analysis/phase-1-4-implementation-gap-analysis.md` - Lines 319-336 reference this gap
2. **Detailed Implementation Guide:** `dev-docs/analysis/gap-28-test-endpoints-requirement.md` - COMPLETE specification with code examples
3. **Architecture Requirement:** `dev-docs/architecture-design/mvp-arch.min.md` - Section 7.1.2 (lines 686-719)

---

## Objective

Enable all 30+ API endpoints to be tested WITHOUT JWT authentication by creating `/test` suffix variants that:
- Use hard-coded test tenant context (UUID: `00000000-0000-0000-0000-000000000001`)
- Only work when `TEST_ENDPOINT_ENABLED=true` environment variable is set
- Only work in `dev` and `qa` environments (blocked in `staging` and `production`)
- Share identical business logic with authenticated endpoints (via refactored `_impl()` functions)

---

## Deliverables

### 1. Configuration Infrastructure
**Files to Create:**
- [ ] `backend/core/config.py` - Add test endpoint environment flags
- [ ] `backend/core/test_context.py` - Test user context helper (NEW FILE)

**Environment Variables to Add:**
```bash
# backend/.env.development
TEST_ENDPOINT_ENABLED=true
ENVIRONMENT=dev
TEST_TENANT_ID=00000000-0000-0000-0000-000000000001
TEST_USER_ID=00000000-0000-0000-0000-000000000002
```

### 2. Database Seeding
**Files to Create:**
- [ ] `backend/migrations/seed_test_data.py` - Create test tenant and user (NEW FILE)

**Action Required:**
```bash
python backend/migrations/seed_test_data.py
```

### 3. Refactored Route Files (Extract Business Logic)
**Files to Modify:**
- [ ] `backend/api/routes/auth.py` - 1 endpoint
- [ ] `backend/api/routes/customers.py` - 5 endpoints ⭐ START HERE (pilot implementation)
- [ ] `backend/api/routes/sites.py` - 4 endpoints
- [ ] `backend/api/routes/catalog.py` - 5 endpoints
- [ ] `backend/api/routes/jobs.py` - 7 endpoints
- [ ] `backend/api/routes/quotes.py` - 8 endpoints
- [ ] `backend/api/routes/voice.py` - 1 endpoint

**Refactoring Pattern:**
```python
# BEFORE:
@router.post("/", response_model=CustomerResponse)
def create_customer(
    customer_in: CustomerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),  # Requires JWT
):
    customer = Customer(
        tenant_id=current_user.tenant_id,  # This will fail - user has no tenant_id!
        # ... business logic ...
    )
    db.add(customer)
    db.commit()
    return customer

# AFTER:
# 1. Extract shared implementation
def _create_customer_impl(
    customer_in: CustomerCreate,
    db: Session,
    user_context: User | TestUserContext,  # Accept both types
) -> Customer:
    """Shared business logic"""
    customer = Customer(
        tenant_id=user_context.tenant_id,  # Works for both User and TestUserContext
        # ... business logic ...
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer

# 2. Authenticated endpoint (unchanged externally)
@router.post("/", response_model=CustomerResponse)
def create_customer(
    customer_in: CustomerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create customer (requires JWT authentication)"""
    return _create_customer_impl(customer_in, db, current_user)

# 3. NEW: Test endpoint (no authentication)
@router.post("/test", response_model=CustomerResponse)
def create_customer_test(
    customer_in: CustomerCreate,
    db: Session = Depends(get_db),
):
    """
    Create customer (TEST ENDPOINT - no authentication).
    Only available in dev/qa when TEST_ENDPOINT_ENABLED=true.
    """
    test_context = get_test_context()  # Injects test tenant/user
    return _create_customer_impl(customer_in, db, test_context)
```

### 4. Testing & Validation
**Files to Create:**
- [ ] `backend/tests/test_test_endpoints.py` - Verify test endpoint behavior (NEW FILE)

**Test Cases:**
```python
# 1. Test endpoint works without auth in dev
# 2. Test endpoint returns 403 when TEST_ENDPOINT_ENABLED=false
# 3. Test endpoint returns 403 in production environment
# 4. Test endpoint creates data in test tenant
# 5. Authenticated and test endpoints produce identical results
```

### 5. Documentation
**Files to Update:**
- [ ] `backend/README.md` - Add "Testing with Test Endpoints" section
- [ ] Create Postman collection using test endpoints

---

## Implementation Order (2.5 Days)

### Day 1 Morning (3 hours): Foundation
1. **Create configuration** (`core/config.py`, `core/test_context.py`)
2. **Create seed script** (`migrations/seed_test_data.py`)
3. **Run seed script** to create test tenant/user in dev database
4. **Verify:** Test tenant exists with UUID `00000000-0000-0000-0000-000000000001`

### Day 1 Afternoon (4 hours): Pilot Implementation
5. **Refactor customers.py** as pilot (5 endpoints: create, list, get, update, delete)
   - Extract `_create_customer_impl()`, `_list_customers_impl()`, etc.
   - Add `/test` variants for all 5 endpoints
   - Test manually with curl (no JWT needed!)
6. **Write tests** for customer test endpoints
7. **Document pattern** in README

### Day 2 Morning (3 hours): Bulk Rollout Part 1
8. **Refactor sites.py** (4 endpoints)
9. **Refactor catalog.py** (5 endpoints)
10. **Run test suite** - ensure nothing broke

### Day 2 Afternoon (4 hours): Bulk Rollout Part 2
11. **Refactor jobs.py** (7 endpoints) - most complex
12. **Refactor quotes.py** (8 endpoints) - most complex
13. **Refactor voice.py** (1 endpoint)
14. **Refactor auth.py** (1 endpoint - signup/test)

### Day 3 Morning (2 hours): Polish & Documentation
15. **Run full test suite**
16. **Create Postman collection** with test endpoints
17. **Update README** with examples
18. **Verify production safeguards** (TEST_ENDPOINT_ENABLED=false blocks access)

---

## Acceptance Criteria

### Functional Requirements
- [ ] Every authenticated endpoint has working `/test` variant
- [ ] Test endpoints return 403 when `TEST_ENDPOINT_ENABLED=false`
- [ ] Test endpoints return 403 when `ENVIRONMENT=production` or `ENVIRONMENT=staging`
- [ ] Test endpoints use test tenant context (UUID: `00000000-0000-0000-0000-000000000001`)
- [ ] Business logic identical between authenticated and test endpoints
- [ ] All test endpoints queryable via `GET /openapi.json` (appear in API docs)

### Code Quality
- [ ] No code duplication (shared `_impl()` functions)
- [ ] Type hints: `user_context: User | TestUserContext`
- [ ] Clear docstrings explaining authenticated vs. test variants
- [ ] Consistent naming: `create_customer()` and `create_customer_test()`

### Testing
- [ ] Pytest suite runs 30%+ faster (no JWT mocking overhead)
- [ ] New test file `test_test_endpoints.py` has 100% coverage of test endpoint guards
- [ ] All existing tests still pass (no breaking changes)

### Developer Experience
- [ ] Can test any endpoint with curl in <10 seconds (no JWT generation)
- [ ] Postman collection works out-of-the-box in dev environment
- [ ] README has clear examples of test vs. authenticated usage
- [ ] New developers can test APIs within 5 minutes of cloning repo

---

## Example Usage (Before & After)

### BEFORE (Requires JWT):
```bash
# 1. Generate Cognito JWT token (2-3 seconds)
TOKEN=$(aws cognito-idp initiate-auth ...)

# 2. Make authenticated request
curl -X POST http://localhost:8000/v1/customers \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"display_name": "John Doe", "type": "person"}'
```

### AFTER (No Auth Needed):
```bash
# Just call the test endpoint directly
curl -X POST http://localhost:8000/v1/customers/test \
  -H "Content-Type: application/json" \
  -d '{"display_name": "John Doe", "type": "person"}'
```

---

## Key Implementation Details from Guide

**Reference:** `gap-28-test-endpoints-requirement.md` has complete code examples for:
- Configuration setup (Section "Step 1")
- Test context helper (Section "Step 2")
- Refactoring pattern (Section "Step 3")
- Database seeding (Section "Step 4")
- Testing strategy (Section "Testing the Implementation")

**DO NOT:**
- Skip the environment guards (security vulnerability)
- Hardcode test tenant UUID in route files (use config)
- Duplicate business logic between authenticated and test endpoints

**DO:**
- Start with `customers.py` as pilot (simplest endpoints)
- Run tests after each file refactor (prevent regression)
- Use type hints `User | TestUserContext` for shared functions

---

## Troubleshooting

### Issue: `current_user.tenant_id` doesn't exist
**Cause:** User model doesn't have tenant_id attribute (Gap #40 - not fixed yet)  
**Workaround:** The test endpoints will work because TestUserContext HAS tenant_id. Authenticated endpoints are currently broken anyway (Gap #40 blocker).

### Issue: Test endpoints work in production
**Cause:** `ENVIRONMENT` env var not set correctly  
**Fix:** Verify `backend/core/config.py` checks `ENVIRONMENT in ["dev", "qa"]`

### Issue: Test data conflicts with real data
**Cause:** Test tenant UUID conflicts with existing tenant  
**Fix:** Drop and recreate database, or change TEST_TENANT_ID in `.env`

---

## Success Metrics

After completion:
- ✅ 30+ test endpoints functional
- ✅ Pytest runs <2 minutes (was 3+ minutes with auth mocking)
- ✅ Can test full quote creation workflow in 30 seconds via curl
- ✅ New developer onboarding: 5 minutes to first API call (was 1 hour)

---

## Next Steps After Completion

Once test endpoints are working:
1. **Week 1, Days 3-4:** Fix Gap #40 (`current_user.tenant_id` issue)
2. **Week 1, Day 5:** Integration testing + deploy to staging
3. **Week 2:** Continue Phase 1-A (Idempotency, Request Tracing, Database Triggers)

---

## Questions? Issues?

**Reference Documents:**
- Full implementation guide: `gap-28-test-endpoints-requirement.md`
- Phase 1-A overview: `phase-1-4-implementation-gap-analysis.md` (lines 483-509)
- Architecture spec: `mvp-arch.min.md` (Section 7.1.2)

**Stuck?** The pattern is identical across all 7 route files. If `customers.py` works, the rest are copy-paste with different models.

---

**Ready? Let's build test endpoints and unlock fast iteration! 🚀**
