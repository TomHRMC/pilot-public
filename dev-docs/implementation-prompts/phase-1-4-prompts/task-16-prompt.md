# Task Prompt: Phase 3, Task #16 - QuickBooks OAuth 2.0 Flow & Hybrid Schema Refactoring

Task: Phase 3, Task #16 - QuickBooks OAuth 2.0 Flow & Hybrid Schema Refactoring
Reference: dev-docs/analysis/phase-2-5-implementation-roadmap.md Task #16
(Original: Gap #22 in phase-1-4-implementation-gap-analysis.md)

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
✅ Notification Outbox Worker (Task 14) - Email verified, SMS deferred
✅ Session Expiration & Cleanup (Task 15)

**Test Coverage:** 283/283 passing (100% pass rate)
**See:** dev-docs/analysis/phase-2-5-implementation-roadmap.md for full details

## Current Task

Implement QuickBooks OAuth 2.0 authentication flow and refactor the integration schema to support high-performance webhook routing and timezone-aware lifecycle tracking. This is the foundation for all QuickBooks sync functionality.

**CRITICAL:** This task includes a **mandatory Hybrid Schema refactoring** before implementing OAuth. The current generic JSONB schema must be replaced with explicit indexed columns to support:
1. O(1) webhook routing via `realm_id` lookup (vs. decrypting every tenant's credentials)
2. Queryable token expiration for proactive refresh (vs. parsing millions of JSONB strings)
3. Full timezone-aware lifecycle tracking per v2.6h Architecture

**Priority:** BLOCKER (enables all QuickBooks sync functionality)
**Estimated Effort:** 7 days (increased from 5 days due to schema refactoring)
**Task Spec:** See dev-docs/analysis/phase-2-5-implementation-roadmap.md Task #16
**Design Context:** dev-docs/db-design/aevofab-db-process-v2.6h.md

**✅ Pre-Implementation Configuration COMPLETE (2026-03-20):**
- ngrok tunnel active: `https://your-tunnel.ngrok-free.dev`
- QuickBooks app created in Intuit Developer Portal: "AevoFab (Development)"
- OAuth redirect URIs configured in Developer Portal
- Sandbox test company created and accessible
- All credentials copied to `.env` file (CLIENT_ID, CLIENT_SECRET, WEBHOOK_VERIFIER_TOKEN, ENCRYPTION_KEY)
- Webhook endpoints registered in Developer Portal

**🎯 Ready to Begin Implementation:** All 8 checklist items complete, start with schema refactoring below.

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
- **Create implementation plan first** (task-16-quickbooks-oauth-impl-plan.md) before coding
- **Update implementation roadmap** when marking tasks complete

### 2. Testing Standards (CRITICAL FOR MVP)

**⚠️ ZERO FAILING TESTS POLICY:**
- **ALL tests MUST pass before marking a gap as RESOLVED**
- **NO exceptions** - MVP requires 100% test pass rate
- If tests fail after implementation, you have TWO options:
  1. **Fix immediately** (preferred for simple fixes)
  2. **Create detailed fix document** (for complex test issues)
     - Document ALL failing tests with concrete, actionable fixes
     - Mark gap as "PARTIALLY COMPLETE" not "RESOLVED" in analysis doc
     - Include estimated time to fix each test
     - Provide step-by-step fix instructions
     - Example: `backend/tests/test_quickbooks_oauth_fixes.md`

**Test Execution:**
- **Current Baseline:** 283/283 tests passing - DO NOT regress this
- **Tests are MANDATORY** - No code without tests
- **Run existing tests first:**
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
- **Create new test file:** `backend/tests/test_quickbooks_oauth.py`
- **Test coverage required:**
  - Unit tests for encryption/decryption utilities
  - Integration tests for OAuth flow (with mocked QuickBooks API)
  - Token refresh logic tests
  - State token validation tests (CSRF protection)
  - Schema migration tests (verify indexes created)
  - Tenant isolation verification (multi-tenancy tests)

**Test Data Management:**
- **Reference data seeding:** Review `backend/migrations/seed_test_data.py` for existing seed patterns
  - Seed reference tables (AppServiceProvider, AppServiceCategory) in migrations if needed
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
- **Type hints required** - Use `AwareDatetime`, not naive datetime
- **Error handling** - RFC 7807 format (see existing routes)
- **Docstrings required** - Document all functions/classes
- **No feature creep** - Strictly follow 80/20 MVP prioritization
- **Phase 3 Cost Awareness** - QuickBooks integration is core value but must respect $1k/mo budget cap (see infrastructure-constraints.md)

### 4. Database Standards
- **DO NOT hallucinate schema** - Always read `backend/app/models/*.py` first
- **Use Alembic migrations** for schema changes
- **Respect tenant isolation** - All queries filter by tenant_id
- **Follow ORM patterns** - Use SQLModel/SQLAlchemy correctly
- **CRITICAL: Timezone-aware timestamps** - All new datetime fields must use `AwareDatetime` type hints + `DateTime(timezone=True)` in sa_column (v2.6h "Double-Lock" standard)

### 5. Workflow
1. **Read the task roadmap** to understand the requirements (lines 594-1024 in phase-2-5-implementation-roadmap.md)
2. **Review design specs** (db-process-v2.6h.md, mvp-arch.md)
3. **Create implementation plan** document with detailed tasks
4. **Get approval** on the plan before coding
5. **Implement** following the plan step-by-step
6. **Write tests** alongside implementation
7. **Run all tests** - Must pass before completion
8. **Update documentation** - **BOTH documents MUST be updated:**
   
   **Document 1: phase-2-5-implementation-roadmap.md (Active Task Tracking)**
   - Find Task 16 section (lines 594-1024)
   - Check off completed deliverables using `- [x]` checkbox format
   - Update any inline status notes or test results
   - If all deliverables complete, task is ✅ COMPLETE
   - If some deliverables incomplete, task is ⚠️ PARTIALLY COMPLETE
   
   **Document 2: phase-1-4-implementation-gap-analysis.md (Historical Gap Tracking)**
   - Find Gap #22: QuickBooks OAuth Flow
   - Update the gap status at the top:
     - ✅ **RESOLVED** if all tests pass and implementation 100% complete
     - ⚠️ **PARTIALLY COMPLETE** if fix document created or deliverables incomplete
   - Add "Resolved Date" line if marking RESOLVED
   - Add implementation summary (what was built, files created/modified, test results)
   - Cross-reference to Task 16 in phase-2-5-implementation-roadmap.md
   
   **Both documents must match:**
   - If roadmap task shows incomplete deliverables → gap status = PARTIALLY COMPLETE
   - If roadmap task shows all complete + tests pass → gap status = RESOLVED
   - Follow existing patterns from Phase 1-A/1-B completed tasks

## Key Files to Review

### Architecture
- `dev-docs/analysis/phase-2-5-implementation-roadmap.md` - **Task 16 details (lines 594-1024)**
- `dev-docs/architecture-design/mvp-arch.md` - Overall system design
- `dev-docs/db-design/aevofab-db-process-v2.6h.md` - Database operations & schema
- `dev-docs/analysis/phase-1-4-implementation-gap-analysis.md` - Gap #22 reference
- `dev-docs/analysis/phase-3-quickbooks-integration-guide.md` - QuickBooks integration context

### Backend Code
- `backend/app/models/system.py` - **CRITICAL: AppService and IntegrationCredential models to refactor**
- `backend/app/models/mixins.py` - **AwareDatetime type definition**
- `backend/core/config.py` - Configuration settings (add QuickBooks & encryption keys)
- `backend/api/routes/` - API endpoint patterns
- `backend/core/` - Core utilities (auth, db, middleware)
- `backend/tests/` - Test suite patterns

### Configuration
- `backend/.env.example` - Environment variable template (add QuickBooks credentials)
- `backend/requirements.txt` - Python dependencies (add cryptography, httpx if needed)

### Recent Examples (Phase 2 Completed Work)
- **Celery Setup:** `backend/core/celery_app.py` (Task 12 - token refresh will use Beat scheduler)
- **Database Models:** `backend/app/models/system.py` (existing integration tables)
- **Test Patterns:** `backend/tests/test_celery.py`, `backend/tests/test_notification_outbox.py`
- **Configuration:** `backend/core/config.py` (pattern for new settings)

## Task-Specific Requirements

### Part 1: Hybrid Schema Refactoring (MUST COMPLETE FIRST)

**⚠️ CRITICAL:** Complete this schema refactoring before implementing OAuth endpoints.

#### 1.1 Update `app_service` Model

Add explicit column for QuickBooks realm_id (Company ID):

```python
# backend/app/models/system.py - AppService model

external_account_id: str | None = Field(
    default=None,
    sa_column=Column(String, nullable=True, index=True),
    description="QuickBooks realm_id (Company ID). Indexed for fast webhook routing."
)
```

**Why:** Enables O(1) webhook routing without decrypting credentials. Webhook handler can instantly find tenant via `WHERE external_account_id = '{realm_id}'`.

#### 1.2 Update `integration_credential` Model

Add explicit lifecycle timestamp columns (replace JSONB keys):

```python
# backend/app/models/system.py - IntegrationCredential model

# NEW FIELDS - Explicit timestamp columns for queryable lifecycle tracking
expires_at: AwareDatetime | None = Field(
    default=None,
    sa_column=Column(DateTime(timezone=True)),
    description="When the OAuth access token expires (typically 1 hour from issue)"
)

last_refresh_at: AwareDatetime | None = Field(
    default=None,
    sa_column=Column(DateTime(timezone=True)),
    description="Most recent token rotation timestamp"
)

connected_at: AwareDatetime | None = Field(
    default=None,
    sa_column=Column(DateTime(timezone=True)),
    description="Initial authorization timestamp (OAuth callback completion)"
)

disconnected_at: AwareDatetime | None = Field(
    default=None,
    sa_column=Column(DateTime(timezone=True)),
    description="When user revoked access or connection was terminated"
)

initiated_by_user_id: uuid.UUID | None = Field(
    default=None,
    foreign_key="user.id",
    description="User who authorized the QuickBooks connection"
)

connection_status: str = Field(
    default="pending",
    nullable=False,
    index=True,
    description="pending|active|disconnected|expired|revoked"
)
```

**CRITICAL:** All datetime fields MUST use:
- Type hint: `AwareDatetime | None` (from Pydantic)
- SQLAlchemy: `sa_column=Column(DateTime(timezone=True))`
- This is the "Double-Lock" timezone standard from v2.6h Architecture

**Why:** Allows background workers to query `SELECT * FROM integration_credential WHERE expires_at < NOW() + INTERVAL '5 minutes'` for proactive token refresh.

#### 1.3 Restrict `secret_json` to Encrypted Secrets Only

The `secret_json` JSONB field should **only** contain application-encrypted tokens:

```python
# Example secret_json structure
{
    "access_token_encrypted": "gAAAAABh...",  # Fernet-encrypted OAuth access token
    "refresh_token_encrypted": "gAAAAABh...", # Fernet-encrypted OAuth refresh token
    "state_token": "550e8400-e29b-41d4-a716-446655440000"  # OAuth CSRF protection token
}
```

**❌ DO NOT store in `secret_json`:**
- `realm_id` → Use `app_service.external_account_id`
- `token_expires_at` → Use `integration_credential.expires_at`
- `last_refresh_at` → Use explicit column
- `connected_at` → Use explicit column

#### 1.4 Create Alembic Migration

```sql
-- Alembic migration (generate with: alembic revision --autogenerate -m "add_quickbooks_hybrid_schema")

-- Update app_service table
ALTER TABLE app_service
ADD COLUMN external_account_id TEXT NULL;

CREATE INDEX idx_app_service_external_account
ON app_service(external_account_id)
WHERE external_account_id IS NOT NULL;

-- Update integration_credential table
ALTER TABLE integration_credential
ADD COLUMN expires_at TIMESTAMPTZ NULL,
ADD COLUMN last_refresh_at TIMESTAMPTZ NULL,
ADD COLUMN connected_at TIMESTAMPTZ NULL,
ADD COLUMN disconnected_at TIMESTAMPTZ NULL,
ADD COLUMN initiated_by_user_id UUID NULL REFERENCES "user"(id) ON DELETE SET NULL,
ADD COLUMN connection_status TEXT NOT NULL DEFAULT 'pending';

CREATE INDEX idx_integration_credential_status
ON integration_credential(connection_status);

CREATE INDEX idx_integration_credential_expires
ON integration_credential(expires_at)
WHERE expires_at IS NOT NULL;

ALTER TABLE integration_credential
ADD CONSTRAINT ck_integration_credential_status
CHECK (connection_status IN ('pending', 'active', 'disconnected', 'expired', 'revoked'));
```

#### 1.5 Update JSON Schema Documentation

Update `dev-docs/db-design/pilot-db-schema-v2.6h.json` with new fields.

### Part 2: OAuth 2.0 Flow Implementation

**Configuration (Already Complete):**
- `QUICKBOOKS_CLIENT_ID` - From Intuit Developer Portal
- `QUICKBOOKS_CLIENT_SECRET` - From Intuit Developer Portal
- `QUICKBOOKS_REDIRECT_URI` - `https://your-tunnel.ngrok-free.dev/api/v1/integrations/quickbooks/callback`
- `QUICKBOOKS_ENVIRONMENT` - Set to `sandbox`
- `ENCRYPTION_KEY` - Generated Fernet key for token encryption

#### 2.1 Create Encryption Utilities

```python
# backend/core/encryption.py (NEW FILE)

from cryptography.fernet import Fernet
from core.config import settings

def encrypt_token(token: str) -> str:
    """Encrypt OAuth token using Fernet (AES-128-CBC + HMAC)"""
    f = Fernet(settings.ENCRYPTION_KEY.encode())
    return f.encrypt(token.encode()).decode()

def decrypt_token(encrypted_token: str) -> str:
    """Decrypt OAuth token"""
    f = Fernet(settings.ENCRYPTION_KEY.encode())
    return f.decrypt(encrypted_token.encode()).decode()
```

#### 2.2 Create OAuth Endpoints

```python
# backend/api/routes/integrations.py (NEW FILE)

@router.get("/integrations/quickbooks/connect")
async def initiate_qbo_oauth(current_user: AuthenticatedUser):
    """
    Step 1: Initiate OAuth Flow
    
    1. Generate cryptographically secure state token (UUID4)
    2. Store state in integration_credential (status=pending, expires in 10 min)
    3. Build QuickBooks authorization URL
    4. Return 302 redirect to QuickBooks consent screen
    """

@router.get("/integrations/quickbooks/callback")
async def qbo_oauth_callback(
    code: str,           # Authorization code from QuickBooks
    state: str,          # State token for CSRF validation
    realmId: str         # QuickBooks Company ID
):
    """
    Step 2: Handle OAuth Callback (ngrok endpoint)
    
    1. Validate state token exists and not expired
    2. Exchange authorization code for tokens
    3. Encrypt tokens using Fernet
    4. Store in integration_credential with new explicit fields
    5. Update app_service.external_account_id with realm_id
    6. Set connection_status='active'
    7. Redirect to frontend success page
    """

@router.post("/integrations/quickbooks/refresh")
async def refresh_qbo_token(current_user: AuthenticatedUser):
    """
    Step 3: Automatic Token Refresh (background job)
    
    1. Check if expires_at < now + 5 minutes (proactive refresh)
    2. Use refresh_token to get new access_token
    3. Update expires_at and last_refresh_at fields
    """

@router.delete("/integrations/quickbooks/disconnect")
async def disconnect_qbo(current_user: AuthenticatedUser):
    """
    Step 4: Disconnect QuickBooks
    
    1. Update connection_status to 'disconnected'
    2. Set disconnected_at timestamp
    3. Preserve sync_mapping records (don't delete historical data)
    """
```

#### 2.3 Create Token Refresh Celery Task

```python
# backend/tasks/quickbooks_token_refresh.py (NEW FILE)

@celery_app.task(name="refresh_quickbooks_tokens")
def refresh_quickbooks_tokens_task():
    """
    Celery Beat task (runs every 30 minutes)
    
    Proactively refreshes tokens expiring within 5 minutes
    """
```

Register in `backend/core/celery_app.py` beat_schedule.

#### 2.4 ngrok Integration Testing

**Testing Flow:**
1. Start ngrok: `ngrok http 8000 --domain=your-tunnel.ngrok-free.dev`
2. Start FastAPI: `cd backend && uvicorn app.main:app --reload`
3. Start Celery worker: `cd backend && celery -A core.celery_app worker --loglevel=info`
4. Navigate to `http://localhost:8000/api/v1/integrations/quickbooks/connect`
5. Verify redirect to QuickBooks consent screen
6. Select sandbox company and authorize
7. Verify callback receives `code`, `state`, `realmId`
8. Verify tokens stored encrypted in database
9. Verify `app_service.external_account_id` populated
10. Verify all new timestamp fields populated
11. Verify connection_status shows "active"

## Success Criteria

**MUST COMPLETE ALL BEFORE MARKING GAP AS RESOLVED:**

### Schema Refactoring Deliverables
- [ ] `AppService` model updated with `external_account_id` field
- [ ] `IntegrationCredential` model updated with explicit timestamp columns (`expires_at`, `last_refresh_at`, `connected_at`, `disconnected_at`, `initiated_by_user_id`, `connection_status`)
- [ ] All new datetime fields use `AwareDatetime` + `DateTime(timezone=True)` (Double-Lock standard)
- [ ] Alembic migration created and applied
- [ ] Indexes created (`external_account_id`, `connection_status`, `expires_at`)
- [ ] Check constraint created for `connection_status` enum
- [ ] JSON schema documentation updated (`pilot-db-schema-v2.6h.json`)
- [ ] Schema migration tests pass

### OAuth Implementation Deliverables
- [ ] OAuth initiation endpoint (`/integrations/quickbooks/connect`)
- [ ] OAuth callback handler (ngrok-accessible)
- [ ] Token encryption/decryption utilities (`backend/core/encryption.py`)
- [ ] Automatic token refresh (Celery Beat task every 30 min)
- [ ] Disconnect endpoint
- [ ] Integration tests with sandbox credentials
- [ ] All OAuth endpoints tested via ngrok

### Test Requirements
- [ ] **ALL existing tests pass** (no regression from 283/283 baseline)
- [ ] **ALL new tests pass** (zero failures)
- [ ] **Test pass rate: 100%** (X/X passing, 0 failing)
- [ ] Schema migration tests verify indexes created
- [ ] OAuth flow tests (mocked QuickBooks API)
- [ ] Token encryption/decryption tests
- [ ] State token validation tests (CSRF protection)
- [ ] Token refresh logic tests
- [ ] Tenant isolation tests for new endpoints

### Documentation & Tracking
- [ ] Implementation plan created and approved (task-16-quickbooks-oauth-impl-plan.md)
- [ ] Code follows existing patterns and standards
- [ ] Documentation updated with what was delivered
- [ ] **Both tracking documents updated:**
  - [ ] phase-2-5-implementation-roadmap.md Task 16 deliverables checked off
  - [ ] phase-1-4-implementation-gap-analysis.md Gap #22 marked RESOLVED

**Gap Status in Analysis Doc:**
- ✅ **RESOLVED** - If all tests pass (implementation + tests 100% complete)
- ⚠️ **PARTIALLY COMPLETE** - If fix document created for failing tests
  - Must include: "Implementation complete, tests require fixes (see test_quickbooks_oauth_fixes.md)"
  - Cannot mark RESOLVED until all tests pass

**If Tests Fail:**
- Create `backend/tests/test_quickbooks_oauth_fixes.md` with concrete fixes for ALL failing tests
- Update gap status to "PARTIALLY COMPLETE" in analysis doc
- Document exact steps to achieve 100% test pass rate
- Include time estimates for each fix

## Success Validation

After implementation, verify:

1. **Schema Changes:**
   - [ ] `\d app_service` shows `external_account_id` column with index
   - [ ] `\d integration_credential` shows all 6 new columns with proper types
   - [ ] Check constraint exists for `connection_status`
   - [ ] Indexes exist and functional

2. **OAuth Flow:**
   - [ ] Can connect to QuickBooks sandbox via ngrok
   - [ ] Tokens stored encrypted (verify cannot read plaintext in DB)
   - [ ] `app_service.external_account_id` populated with realm_id
   - [ ] All new timestamp fields populated with timezone-aware values
   - [ ] `connection_status` = 'active' after successful connection
   - [ ] State token prevents CSRF attacks

3. **Token Refresh:**
   - [ ] Celery Beat task registered
   - [ ] Tokens refresh automatically before expiration
   - [ ] `last_refresh_at` updates correctly
   - [ ] Connection remains active after refresh

4. **Security:**
   - [ ] Tokens stored encrypted (Fernet)
   - [ ] State token validated on callback
   - [ ] Tenant isolation enforced
   - [ ] No tokens in logs

## Questions to Ask

Before starting:
1. Have I read Task 16 details in the roadmap thoroughly? (lines 594-1024)
2. Have I reviewed the Hybrid Schema requirements?
3. Do I understand why explicit columns are needed vs. JSONB?
4. What existing code patterns can I reference for OAuth?
5. How will I test the ngrok callback flow?

During implementation:
1. Am I following the v2.6h "Double-Lock" timezone standard for all datetime fields?
2. Are ALL tests passing (100% pass rate)?
3. Have I verified indexes are created correctly?
4. Am I encrypting tokens before storing?
5. Is tenant isolation enforced in all queries?

After implementation:
1. Do I have 100% test pass rate (X/X passing, 0 failing)?
2. If tests fail, have I created a detailed fix document?
3. Have I marked the gap status correctly (RESOLVED vs PARTIALLY COMPLETE)?
4. Have I updated BOTH tracking documents?
5. Can I successfully connect to QuickBooks sandbox via ngrok?

## Example Task Flow

```bash
# 1. Review the task in roadmap
cat dev-docs/analysis/phase-2-5-implementation-roadmap.md | grep -A 400 "Task 16"

# 2. Check original gap for context
cat dev-docs/analysis/phase-1-4-implementation-gap-analysis.md | grep -A 30 "Gap #22"

# 3. Review existing models
cat backend/app/models/system.py | grep -A 50 "class AppService"
cat backend/app/models/system.py | grep -A 80 "class IntegrationCredential"

# 4. Review timezone standard
cat backend/app/models/mixins.py | grep -A 10 "AwareDatetime"

# 5. Run existing tests (baseline: 283 passing)
cd backend && source .venv/bin/activate && pytest tests/ -v

# 6. Start ngrok tunnel
ngrok http 8000 --domain=your-tunnel.ngrok-free.dev

# 7. Create your implementation
# [write code]

# 8. Run tests again (must maintain 100% pass rate)
pytest tests/ -v

# 9. Test OAuth flow
curl http://localhost:8000/api/v1/integrations/quickbooks/connect
```

## Notes

- **ngrok URL:** `https://your-tunnel.ngrok-free.dev` (stable, already configured in QB Developer Portal)
- **Sandbox Environment:** Use sandbox.qbo.intuit.com for testing
- **Token Lifetime:** Access tokens expire in 1 hour, refresh tokens in 100 days
- **Schema Refactoring:** This is a one-time architectural upgrade that pays dividends in performance and maintainability
- **Webhook Routing:** Task 19 (Webhook Handler) will use the indexed `external_account_id` for fast tenant lookup
- **MVP Focus:** Follow dev-docs/product-requirements/mvp-prd.md for scope
- **80/20 Rule:** See .roo/rules-mvp-builder/80-20-prioritization.md
- **Mike the Solo Contractor:** Our primary persona - keep it simple!
- **Security:** QuickBooks production approval requires security review - build it right the first time
- **Cost Awareness:** QuickBooks integration is core value but must respect $1k/mo infrastructure budget

## Security Reminders

- **Never log tokens in plaintext**
- **Always validate state token on callback (CSRF protection)**
- **Use HTTPS only (enforced by ngrok)**
- **Encrypt tokens before storing (Fernet: AES-128-CBC + HMAC)**
- **Rotate encryption key periodically**
- **Respect tenant isolation in all queries**
- **Use explicit columns for searchable metadata (not JSONB)**
- **Follow v2.6h timezone standard for all datetime fields**
