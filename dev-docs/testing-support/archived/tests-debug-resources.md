> **📦 ARCHIVED 2026-08-20 — MARCH-ERA SNAPSHOT, SUPERSEDED.** This 2026-03-28 reference ("367/367 passing" baseline) is stale: Twilio-era markers (the project uses Telnyx), a defunct `python -m migrations.seed_test_data` command, and pre-canonical pytest invocations. Living successors: `backend/tests/README-adding-tests.md` (mandatory pre-test read), `.roo/rules-pilot-qa-python-engineer/`, and `pilot-python-engineer-methods.md`. Archived to `dev-docs/testing-support/archived/` per Tom's decision. **Frozen reference — do not update.**

---

# Pilot for Trades Backend Testing & Debugging Reference

**Purpose:** Concise technical reference for developers debugging test failures in the Pilot for Trades pytest environment.

**Last Updated:** 2026-03-28  
**Baseline Tests:** 367/367 passing  
**Python Version:** 3.11+  
**Test Framework:** pytest 7.0+

---

## 1. Pytest Configuration

### pytest.ini Settings

**File:** `backend/pytest.ini`

```ini
[pytest]
python_files = test_*.py
python_classes = Test*
python_functions = test_*
testpaths = tests
minversion = 7.0

# Default flags (auto-applied to all test runs)
addopts = -v --strict-markers --tb=short -ra
```

**Key Settings:**
- **`-v`**: Verbose output (shows each test name)
- **`--strict-markers`**: Fail on unregistered markers (prevents typos)
- **`--tb=short`**: Short traceback format (concise error messages)
- **`-ra`**: Show summary of all test results at end
- **`--ignore=tests/integration/`**: Ignore integration tests until all other tests are passing
  - **Integration Tests**: We have limited emails and texts we can send thru Twilio, so for now we want to limit the number of times we run these tests in a single day. By default, we use this flag, until all other tests are passing, then we run this as a `final check` on our entire test suite.

### Test Markers

**Purpose:** Categorize and selectively run tests

```python
@pytest.mark.unit          # Isolated, mocked dependencies
@pytest.mark.integration   # Real external services (SendGrid, Twilio)
@pytest.mark.e2e          # Full pipeline verification
@pytest.mark.slow         # Tests > 1 second
@pytest.mark.requires_db  # Needs database connection
@pytest.mark.requires_redis
@pytest.mark.requires_sendgrid
@pytest.mark.requires_twilio
```

**Usage:**
```bash
# Run only unit tests
pytest -m unit

# Run all except integration tests
pytest -m "not integration"

# Run slow tests only
pytest -m slow
```

---

## 2. Database Architecture

### Connection Management

**File:** `backend/core/db.py`

```python
DATABASE_URL = "postgresql://pilot_user:CHANGE_ME_LOCAL_DB_PW@localhost:5432/pilot_dev"
engine = create_engine(DATABASE_URL, echo=False)

def get_db():
    with Session(engine) as session:
        yield session
```

**Key Points:**
- Uses PostgreSQL (required for JSONB, CITEXT, INET types)
- Single `engine` instance shared across all tests
- Each test gets isolated session via `db_session` fixture

### Transaction Isolation Pattern

**File:** `backend/tests/conftest.py`

```python
@pytest.fixture(scope="function")
def db_session(db_engine):
    connection = db_engine.connect()
    transaction = connection.begin()
    
    session = Session(bind=connection)
    yield session
    
    session.close()
    if transaction.is_active:
        transaction.rollback()  # Auto-cleanup
    connection.close()
```

**How It Works:**
1. Each test starts a fresh transaction
2. Test creates/modifies data freely
3. Transaction auto-rollback after test completes
4. Database state restored for next test

**⚠️ Critical:** Tests run in **function scope** = each test is isolated

---

## 3. Fixture System (conftest.py)

### Core Infrastructure Fixtures

| Fixture | Scope | Purpose | Returns |
|---------|-------|---------|---------|
| `db_engine` | session | Database engine (reused across tests) | SQLModel Engine |
| `db_session` | function | Isolated DB session with auto-rollback | Session |
| `client` | function | FastAPI TestClient with DB override | TestClient |

### Authentication Fixtures

| Fixture | Purpose | Auto-use |
|---------|---------|----------|
| `mock_cognito_jwks` | Mocks AWS Cognito JWKS endpoint | ✅ Yes (all tests) |
| `mock_cognito_jwt_verify` | Mocks JWT token verification | ❌ No (explicit use) |
| `mock_jwt_for_user(email)` | Helper to mock JWT for specific user | ❌ No (factory) |

**Mock JWT Pattern:**
```python
def test_customer_creation(client, db_session, mock_cognito_jwt_verify):
    # Mock JWT will return this user
    mock_cognito_jwt_verify.return_value = {
        "sub": "test-user-id",
        "email": "user@example.com"
    }
    
    headers = {"Authorization": "Bearer fake_token"}
    response = client.post("/api/v1/customers/", headers=headers, json={...})
```

### Multi-Tenancy Fixtures

| Fixture | Purpose | Returns |
|---------|---------|---------|
| `tenant_a` | Create test tenant A | Tenant |
| `tenant_b` | Create isolated test tenant B | Tenant |
| `user_tenant_a` | User belonging to tenant A | User |
| `user_tenant_b` | User belonging to tenant B | User |

**Cross-Tenant Isolation Testing:**
```python
def test_tenant_isolation(client, user_tenant_a, user_tenant_b, mock_jwt_for_user):
    # User A creates a customer
    token_a = mock_jwt_for_user(user_tenant_a.email)
    response = client.post("/api/v1/customers/", 
                          headers={"Authorization": token_a},
                          json={"display_name": "Customer A"})
    customer_id = response.json()["id"]
    
    # User B (different tenant) tries to access customer A
    token_b = mock_jwt_for_user(user_tenant_b.email)
    response = client.get(f"/api/v1/customers/{customer_id}",
                         headers={"Authorization": token_b})
    
    assert response.status_code == 404  # Tenant isolation enforced
```

### Seeded Test Data Fixtures

| Fixture | Purpose | ID |
|---------|---------|-----|
| `test_tenant` | Standard test tenant (seeded) | `00000000-0000-0000-0000-000000000001` |
| `test_user` | Standard test user (seeded) | `00000000-0000-0000-0000-000000000002` |
| `second_tenant` | Second tenant for isolation tests | Random UUID |

**When to Use:**
- `test_tenant`/`test_user`: For test endpoints (`/test` routes) that use `get_test_context()`
- `tenant_a`/`tenant_b`: For multi-tenancy isolation tests
- Create custom tenants: For specific test scenarios requiring clean state

### Datetime Fixtures

```python
@pytest.fixture
def utc_now():
    """Timezone-aware UTC datetime"""
    return datetime.now(UTC)

@pytest.fixture
def aware_datetime():
    """Factory for creating timezone-aware datetimes"""
    def _make_aware(year, month, day, hour=0, minute=0, second=0):
        return datetime(year, month, day, hour, minute, second, tzinfo=UTC)
    return _make_aware
```

**Usage:**
```python
def test_quote_expiry(db_session, utc_now, aware_datetime):
    future_date = aware_datetime(2026, 12, 31, 23, 59, 59)
    quote = Quote(created_at=utc_now, expires_at=future_date, ...)
```

---

## 4. Model Structure & Relationships

### Core Models

**File:** `backend/app/models/core.py`

| Model | Primary Key | Key Fields | Purpose |
|-------|------------|------------|---------|
| `User` | `id` (UUID) | `email`, `first_name`, `last_name` | Global user account |
| `Tenant` | `id` (UUID) | `name`, `is_active` | Multi-tenant isolation |
| `PlatformRole` | `code` (str) | `permissions` (JSONB) | Platform-level roles |

### Auth Models

**File:** `backend/app/models/auth.py`

| Model | Primary Key | Key Fields | Purpose |
|-------|------------|------------|---------|
| `TenantUser` | `(tenant_id, user_id)` | `role_code`, `status_id` | User-tenant membership |
| `TenantUserRole` | `code` (str) | `permissions` (JSONB) | Tenant-level roles |
| `TenantUserStatus` | `id` (UUID) | `code`, `name` | User status (active, suspended, etc.) |

**Critical Relationships:**
```python
# A user can belong to multiple tenants
User (1) <---> (N) TenantUser (N) <---> (1) Tenant

# Each tenant user has one role
TenantUser (N) <---> (1) TenantUserRole

# RBAC permissions stored in role.permissions JSONB field
# Example: {"permissions": ["*"]} for owner role
```

### AuthenticatedUser (Runtime Object)

**File:** `backend/core/auth.py`

```python
class AuthenticatedUser(BaseModel):
    user: User                 # User model instance
    tenant_id: uuid.UUID       # Active tenant context
    role_code: str             # e.g., "owner", "technician"
    permissions: List[str]     # Cached from role (performance)
    
    def has_permission(self, required_permission: str) -> bool:
        """Check permission with wildcard support"""
```

**Created by:** `get_current_user()` dependency  
**Used in:** All authenticated API endpoints  
**Performance:** Permissions cached to avoid repeated DB queries

---

## 5. Test Data Management

### Seeding Strategy

**File:** `backend/migrations/seed_test_data.py`

**What Gets Seeded (Idempotent):**
1. Test tenant (`00000000-0000-0000-0000-000000000001`)
2. Test user (`00000000-0000-0000-0000-000000000002`)
3. Default roles (`owner`, `technician`, `office_staff`, `accountant`)
4. Job statuses (`draft`, `scheduled`, `in_progress`, `completed`, `cancelled`)
5. Quote statuses (`draft`, `pending`, `sent`, `accepted`, `rejected`, `expired`)
6. Taxability codes (`taxable`, `exempt`, `zero_rated`)
7. Tax rates (US-DEFAULT, US-TX-HARRIS, US-CA-LA)
8. Currencies (USD, CAD, EUR, GBP)
9. Entity types (`customer`, `site`, `job`, `quote`)
10. Contact types (`primary`, `billing`, `technical`, `decision_maker`)
11. Address types (`billing`, `service_location`, `mailing`, `shipping`)

**Run Seeding:**
```bash
cd backend
python -m migrations.seed_test_data
```

### Test Data Lifecycle

**Pattern 1: Use Fixtures (Recommended)**
```python
def test_with_fixtures(db_session, tenant_a, user_tenant_a):
    # Data auto-created by fixtures
    # Auto-cleaned up after test via rollback
    customer = Customer(tenant_id=tenant_a.id, display_name="Test Customer")
    db_session.add(customer)
    db_session.flush()  # Get ID without committing
    
    # Test logic here
    
    # No manual cleanup needed - rollback handles it
```

**Pattern 2: Create Inline (For Custom Data)**
```python
def test_with_inline_data(db_session):
    tenant = Tenant(id=uuid.uuid4(), name=f"Custom Tenant {uuid.uuid4()}")
    db_session.add(tenant)
    db_session.flush()
    
    # Use tenant in test
    
    # Still auto-cleaned via rollback
```

**Pattern 3: Factory Functions (For Complex Objects)**
```python
def create_test_quote(db_session, tenant_id, **kwargs):
    """Helper to create quote with sensible defaults"""
    defaults = {
        "tenant_id": tenant_id,
        "quote_number": f"Q-{uuid.uuid4().hex[:8]}",
        "status_code": "draft",
        # ... more defaults
    }
    defaults.update(kwargs)
    quote = Quote(**defaults)
    db_session.add(quote)
    db_session.flush()
    return quote

def test_with_factory(db_session, tenant_a):
    quote = create_test_quote(db_session, tenant_a.id, subtotal_cents=10000)
    # Test logic
```

### Cleanup Mechanics

**Automatic (Default):**
- All tests using `db_session` fixture get auto-rollback
- No manual cleanup needed
- Database returns to pre-test state

**Manual (Exception Case):**
```python
def test_that_commits(db_session):
    # Some tests need to commit to test triggers
    customer = Customer(...)
    db_session.add(customer)
    db_session.commit()  # Trigger fires here
    
    # Must manually clean up
    db_session.delete(customer)
    db_session.commit()
```

**⚠️ Warning:** Avoid manual commits unless testing database triggers or background workers

---

## 6. Authentication & Authorization Testing

### Mocking Cognito JWT

**Auto-Applied (All Tests):**
```python
@pytest.fixture(autouse=True)
def mock_cognito_jwks():
    """Mocks AWS Cognito JWKS endpoint"""
    # Always active - no explicit use needed
```

**Explicit Use (Per Test):**
```python
def test_authenticated_endpoint(client, db_session, mock_cognito_jwt_verify):
    # Configure what JWT verification returns
    mock_cognito_jwt_verify.return_value = {
        "sub": "user-cognito-id",
        "email": "user@example.com"
    }
    
    headers = {"Authorization": "Bearer fake_token_12345"}
    response = client.post("/api/v1/resource", headers=headers, json={...})
```

### Testing RBAC Permissions

**File:** `backend/tests/test_rbac_permissions.py`

**Role-Specific Fixtures:**
```python
@pytest.fixture
def owner_user(db_session, tenant_a):
    """User with wildcard (*) permission"""
    # Creates user, tenant_user with role_code="owner"
    # Role has permissions=["*"]

@pytest.fixture
def technician_user(db_session, tenant_a):
    """User with field operations permissions only"""
    # Role has permissions=["jobs.view", "jobs.update", "time_entries.*"]

@pytest.fixture
def office_staff_user(db_session, tenant_a):
    """User with administrative permissions"""
    # Role has permissions=["customers.*", "quotes.*", "sites.*"]

@pytest.fixture
def accountant_user(db_session, tenant_a):
    """User with read-only access"""
    # Role has permissions=["*.view", "audit.view"]
```

**Testing Permission Denial:**
```python
def test_technician_cannot_create_quotes(client, technician_user, mock_jwt_for_user):
    token = mock_jwt_for_user(technician_user.email)
    
    response = client.post("/api/v1/quotes/",
                          headers={"Authorization": token},
                          json={"customer_id": str(uuid.uuid4())})
    
    assert response.status_code == 403
    assert "quotes.create" in response.json()["detail"]["required_permission"]
```

### Test Endpoints (Unauthenticated)

**Pattern:** Routes with `/test` suffix bypass JWT authentication

**File:** `backend/core/test_context.py`

```python
def get_test_context() -> TestUserContext:
    """Returns mock user context for /test endpoints"""
    # Only works when:
    # - TEST_ENDPOINT_ENABLED=true
    # - ENVIRONMENT=dev or qa
    # Otherwise raises 403 Forbidden
```

**Usage in Routes:**
```python
@router.post("/customers/test")
def create_customer_test(data: CustomerCreate, db: Session = Depends(get_db)):
    test_context = get_test_context()  # No JWT needed
    return _create_customer_impl(data, db, test_context)
```

**Testing Test Endpoints:**
```python
def test_endpoint_no_auth_needed(client, db_session):
    # No Authorization header needed for /test routes
    response = client.post("/api/v1/customers/test",
                          json={"display_name": "Test Customer"})
    assert response.status_code == 201
```

---

## 7. Test Execution Patterns

NOTE: When running tests from the Roo Code extension chat window, make sure to add either of the following to the pytest command:
```bash
# To see only the passed / failed summary lines
`2>&1 | grep -E "(passed|failed|===)" | tail -20`

# To see the last 100 lines only
2>&1 | tail -100
```

### Standard Test Run (Recommended)

```bash
# From project root
cd backend && source .venv/bin/activate && pytest --ignore=tests/integration/ tests/

# From backend directory (if already there)
source .venv/bin/activate && pytest --ignore=tests/integration/ tests/
```

**Why ignore integration tests?**
- Integration tests call SendGrid API (limited daily quota)
- Integration tests may call Twilio API (costs money)
- Faster execution for development workflow

### With Coverage Report

```bash
cd backend && source .venv/bin/activate && pytest --cov=. --ignore=tests/integration/ tests/

# Coverage report shows:
# - Line coverage for api/, app/, core/, services/, tasks/
# - Branch coverage enabled
# - Missing lines highlighted
```

**Coverage settings:** `backend/.coveragerc`

### Run All Tests (Including Integration)

```bash
cd backend && source .venv/bin/activate && pytest tests/

# ⚠️ WARNING: This will:
# - Send real emails via SendGrid
# - Potentially send SMS via Twilio
# - Use API quotas/credits
```

### Selective Test Execution

```bash
# Single test file
pytest tests/test_rbac_permissions.py

# Single test function
pytest tests/test_rbac_permissions.py::test_wildcard_permission_match

# Tests matching pattern
pytest -k "permission"  # Runs all tests with "permission" in name

# Tests with specific marker
pytest -m unit  # Only unit tests
pytest -m "not slow"  # Exclude slow tests
```

### Concise Output (CI/CD Friendly)

```bash
pytest --ignore=tests/integration/ tests/ 2>&1 | grep -E "(passed|failed|===)" | tail -5

# Output:
# ============================= test session starts ==============================
# tests/test_phase2.py::test_customer_creation PASSED
# tests/test_phase2.py::test_job_creation PASSED
# ============================== 367 passed in 12.45s ============================
```

### Verbose Debugging

```bash
# Show print statements
pytest -s tests/test_rbac_permissions.py

# Show local variables on failure
pytest --showlocals tests/test_rbac_permissions.py

# Full traceback
pytest --tb=long tests/test_rbac_permissions.py

# Stop on first failure
pytest -x tests/

# Re-run only failed tests
pytest --lf tests/
```

---

## 8. Common Test Patterns

### Pattern 1: Basic CRUD Test

```python
def test_create_customer(client, db_session, mock_cognito_jwt_verify):
    # 1. Setup: Configure auth mock
    mock_cognito_jwt_verify.return_value = {
        "sub": "test-sub",
        "email": "test@pilot.local"
    }
    
    # 2. Execute: Call API endpoint
    headers = {"Authorization": "Bearer fake_token"}
    response = client.post("/api/v1/customers/",
                          headers=headers,
                          json={"display_name": "John Doe", "type": "person"})
    
    # 3. Assert: Verify response
    assert response.status_code == 201
    data = response.json()
    assert data["display_name"] == "John Doe"
    assert "id" in data
    
    # 4. Verify DB state (optional)
    customer = db_session.get(Customer, UUID(data["id"]))
    assert customer is not None
    assert customer.display_name == "John Doe"
```

### Pattern 2: Multi-Tenancy Isolation Test

```python
def test_cross_tenant_access_denied(client, tenant_a, tenant_b, 
                                    user_tenant_a, user_tenant_b,
                                    mock_jwt_for_user):
    # User A creates resource
    token_a = mock_jwt_for_user(user_tenant_a.email)
    response = client.post("/api/v1/customers/",
                          headers={"Authorization": token_a},
                          json={"display_name": "Tenant A Customer"})
    resource_id = response.json()["id"]
    
    # User B (different tenant) attempts access
    token_b = mock_jwt_for_user(user_tenant_b.email)
    response = client.get(f"/api/v1/customers/{resource_id}",
                         headers={"Authorization": token_b})
    
    # Should be denied (404 or 403)
    assert response.status_code in [403, 404]
```

### Pattern 3: Permission Testing

```python
def test_permission_enforcement(client, technician_user, mock_jwt_for_user):
    # Technician tries to create quote (should fail - lacks quotes.create)
    token = mock_jwt_for_user(technician_user.email)
    response = client.post("/api/v1/quotes/",
                          headers={"Authorization": token},
                          json={"customer_id": str(uuid.uuid4())})
    
    assert response.status_code == 403
    detail = response.json()["detail"]
    assert detail["required_permission"] == "quotes.create"
    assert "quotes.create" not in detail["user_permissions"]
```

### Pattern 4: Database Trigger Testing

```python
def test_audit_trigger_logs_change(db_session, utc_now):
    # Create entity
    customer = Customer(
        tenant_id=uuid.uuid4(),
        display_name="Original Name",
        type=CustomerType.person
    )
    db_session.add(customer)
    db_session.commit()  # Trigger fires on commit
    
    # Verify audit log entry created
    audit_log = db_session.exec(
        select(AuditEvent)
        .where(AuditEvent.entity_type == "customer")
        .where(AuditEvent.entity_id == customer.id)
        .where(AuditEvent.operation == "INSERT")
    ).first()
    
    assert audit_log is not None
    assert audit_log.new_values["display_name"] == "Original Name"
```

### Pattern 5: Performance Testing

```python
import time

def test_permission_check_performance(owner_user, mock_jwt_for_user):
    # Measure permission check latency
    start = time.perf_counter()
    
    # Simulate 100 permission checks
    for _ in range(100):
        has_permission(owner_user.permissions, "quotes.create")
    
    elapsed = time.perf_counter() - start
    avg_latency_ms = (elapsed / 100) * 1000
    
    # Should be < 1ms per check (in-memory operation)
    assert avg_latency_ms < 1.0, f"Avg latency: {avg_latency_ms}ms"
```

---

## 9. Debugging Common Issues

### Issue 1: ImportError - Cannot Import Model

**Error:**
```
ImportError: cannot import name 'User' from 'app.models.auth'
```

**Cause:** Wrong module path for model

**Solution:** Check actual model location
```bash
# Find where User is defined
grep -r "class User" backend/app/models/

# Correct imports:
from app.models.core import User          # ✅ Correct
from app.models.auth import TenantUser    # ✅ Correct
from app.models.auth import User          # ❌ Wrong
```

### Issue 2: Fixture Not Found

**Error:**
```
E   fixture 'test_customer' not found
```

**Cause:** Fixture doesn't exist or wrong name

**Solution:**
```bash
# List all available fixtures
pytest --fixtures

# Check conftest.py for fixture name
grep -n "@pytest.fixture" backend/tests/conftest.py

# Use correct fixture name from conftest.py
# Common fixtures: db_session, client, tenant_a, test_tenant
```

### Issue 3: Tests Pass Individually, Fail Together

**Error:**
```bash
pytest tests/test_file.py::test_one  # PASSES
pytest tests/test_file.py::test_two  # PASSES
pytest tests/test_file.py              # test_two FAILS
```

**Cause:** Shared state contamination (test order dependency)

**Solution:**
```python
# BAD: Modifying module-level state
_global_cache = {}

def test_one(db_session):
    _global_cache['key'] = 'value'  # ❌ Pollutes next test

# GOOD: Use fixtures or local state
def test_one(db_session):
    local_data = {'key': 'value'}  # ✅ Isolated
```

### Issue 4: Transaction Already Rolled Back

**Error:**
```
SAWarning: transaction already rolled back
```

**Cause:** Test manually rolled back, then fixture tries again

**Solution:**
```python
# Fixture already handles rollback
# Don't manually rollback unless absolutely needed
def test_rollback(db_session):
    customer = Customer(...)
    db_session.add(customer)
    # db_session.rollback()  # ❌ Don't do this - fixture handles it
    # Just let test end naturally
```

### Issue 5: Foreign Key Constraint Violation

**Error:**
```
IntegrityError: insert or update on table "tenant_user" violates foreign key constraint
```

**Cause:** Referenced entity doesn't exist (e.g., role_code='owner' but role not seeded)

**Solution:**
```bash
# Re-run seed script to ensure reference data exists
cd backend
python -m migrations.seed_test_data

# Or create required reference data in test
def test_with_role(db_session):
    role = TenantUserRole(code="test_role", name="Test Role", permissions=["*"])
    db_session.add(role)
    db_session.flush()
    
    tenant_user = TenantUser(role_code="test_role", ...)
```

### Issue 6: Naive Datetime Error

**Error:**
```
ValueError: Datetime fields must be timezone-aware
```

**Cause:** Using `datetime.now()` instead of `datetime.now(UTC)`

**Solution:**
```python
from datetime import UTC, datetime

# BAD
created_at = datetime.now()  # ❌ Naive

# GOOD
created_at = datetime.now(UTC)  # ✅ Aware

# Or use fixture
def test_with_datetime(utc_now):
    customer = Customer(created_at=utc_now, ...)
```

### Issue 7: Test Passes in IDE, Fails in CLI

**Cause:** Different working directory or environment variables

**Solution:**
```bash
# Always run from backend directory
cd backend
source .venv/bin/activate
pytest tests/

# Check environment variables
echo $DATABASE_URL
echo $TEST_ENDPOINT_ENABLED

# Set if missing
export TEST_ENDPOINT_ENABLED=true
export ENVIRONMENT=dev
```

---

## 10. Quick Reference Commands

### Essential Test Commands

```bash
# Standard test run (recommended)
cd backend && source .venv/bin/activate && pytest --ignore=tests/integration/ tests/

# With coverage
cd backend && source .venv/bin/activate && pytest --cov=. --ignore=tests/integration/ tests/

# Single test file
pytest tests/test_rbac_permissions.py

# Single test function
pytest tests/test_rbac_permissions.py::test_wildcard_permission_match

# Verbose output with prints
pytest -s tests/test_file.py

# Stop on first failure
pytest -x tests/

# Re-run only failed tests
pytest --lf tests/
```

### Debugging Commands

```bash
# List all fixtures
pytest --fixtures

# Show test collection
pytest --collect-only tests/

# Show local variables on failure
pytest --showlocals tests/test_file.py

# Full traceback
pytest --tb=long tests/test_file.py

# Profile slow tests
pytest --durations=10 tests/
```

### Database Commands

```bash
# Re-seed test data
cd backend && python -m migrations.seed_test_data

# Connect to test database
psql -U pilot_user -d pilot_dev

# Check seeded roles
psql -U pilot_user -d pilot_dev -c "SELECT code, name FROM tenant_user_role;"
```

---

## 11. File Reference Map

### Configuration Files
- `backend/pytest.ini` - Pytest settings
- `backend/.coveragerc` - Coverage settings
- `backend/.env.example` - Environment variables template

### Core Test Files
- `backend/tests/conftest.py` - Global fixtures
- `backend/migrations/seed_test_data.py` - Reference data seeding

### Test Categories
- **Unit Tests:** `test_voice_actions.py`, `test_tax_calculation.py`, `test_rbac_permissions.py`
- **Integration Tests:** `tests/integration/test_sendgrid_integration.py`
- **Multi-Tenancy:** `test_multi_tenancy_isolation.py`
- **RBAC:** `test_rbac_permissions.py`
- **Audit:** `test_audit_logging.py`
- **QuickBooks:** `test_quickbooks_oauth.py`, `test_quickbooks_sync.py`

### Model Files
- `backend/app/models/core.py` - User, Tenant, PlatformRole
- `backend/app/models/auth.py` - TenantUser, TenantUserRole, TenantUserStatus
- `backend/app/models/crm.py` - Customer, Contact, Address
- `backend/app/models/quoting.py` - Quote, QuoteLine
- `backend/app/models/fulfillment.py` - Job, TimeEntry, Expense

### Helper Files
- `backend/core/auth.py` - AuthenticatedUser, get_current_user()
- `backend/core/test_context.py` - TestUserContext for /test endpoints
- `backend/core/db.py` - Database engine, get_db() dependency

---

## 12. Architecture Context

### Multi-Tenancy Model

```
User (global)
  ↓
TenantUser (user ↔ tenant link)
  ↓
Tenant (isolation boundary)
  ↓
Customer, Quote, Job, etc. (tenant-scoped resources)
```

**Key Principle:** All business entities (Customer, Quote, Job) have `tenant_id` foreign key.  
**Enforcement:** API endpoints filter by `current_user.tenant_id` to prevent cross-tenant access.

### RBAC Model

```
TenantUser.role_code → TenantUserRole → permissions (JSONB array)
                                          ↓
                                     has_permission() checks
                                          ↓
                                     require_permission() decorator
```

**Permission Format:** `resource.action` (e.g., `quotes.create`, `customers.view`)  
**Wildcards:** `*` (all), `quotes.*` (all quote actions), `*.view` (view all resources)

### Test Endpoint Pattern

```
Production Route:         /api/v1/customers/           (requires JWT)
Test Route:              /api/v1/customers/test       (no JWT, uses test_context)

Shared Implementation:   _create_customer_impl(data, db, user_context)
                                                      ↑
                        AuthenticatedUser or TestUserContext
```

**Why:** Allows testing business logic without complex JWT mocking.  
**Security:** Only enabled when `TEST_ENDPOINT_ENABLED=true` and `ENVIRONMENT=dev|qa`.

---

## 13. Best Practices

### ✅ DO

1. **Use existing fixtures** from conftest.py instead of creating duplicates
2. **Run tests from backend directory** with venv activated
3. **Ignore integration tests** during development (save API quotas)
4. **Use `db_session` fixture** for automatic transaction rollback
5. **Create timezone-aware datetimes** using `datetime.now(UTC)` or `utc_now` fixture
6. **Follow existing test patterns** from test_phase2.py, test_rbac_permissions.py
7. **Mock external services** (Cognito, SendGrid, Twilio) in unit tests
8. **Test multi-tenancy isolation** for all CRUD operations
9. **Test permission enforcement** for protected endpoints

### ❌ DON'T

1. **Don't manually rollback** in tests (fixture handles it)
2. **Don't use naive datetimes** (causes validation errors)
3. **Don't create duplicate fixtures** (check conftest.py first)
4. **Don't run integration tests unnecessarily** (costs API credits)
5. **Don't modify module-level state** (causes test order dependencies)
6. **Don't skip `pytest --fixtures`** when looking for available fixtures
7. **Don't commit without running tests** (maintain 100% pass rate)
8. **Don't create tests without markers** (helps with selective execution)

---

## 14. Getting Help

### Documentation
- **Implementation Plans:** `dev-docs/analysis/phase-1-5-tasks/`
- **Architecture:** `dev-docs/architecture-design/mvp-arch.md`
- **Database Schema:** `dev-docs/db-design/pilot-db-schema-v2.6h.json`
- **Current Roadmap:** `dev-docs/analysis/phase-4-5-implementation-roadmap.md`

### Example Test Files (By Category)
- **Basic CRUD:** `test_phase2.py`
- **RBAC/Permissions:** `test_rbac_permissions.py`
- **Multi-Tenancy:** `test_multi_tenancy_isolation.py`
- **Database Triggers:** `test_database_triggers.py`
- **Background Workers:** `test_profitability_rollup.py`, `test_notification_outbox.py`
- **External APIs:** `test_quickbooks_oauth.py`, `test_quickbooks_sync.py`

### pytest Documentation
- List fixtures: `pytest --fixtures`
- Show test collection: `pytest --collect-only`
- Debug single test: `pytest -s --showlocals tests/test_file.py::test_name`
- Profile performance: `pytest --durations=10`

---

**Last Updated:** 2026-03-28  
**Maintainer:** Pilot for Trades Development Team  
**Questions:** Check existing test files for patterns or create new discussion in team chat
