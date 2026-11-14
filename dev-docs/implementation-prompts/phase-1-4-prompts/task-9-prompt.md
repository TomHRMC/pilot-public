# Task 9: Quote Acceptance Workflow

**Reference:** `dev-docs/analysis/phase-1-4-implementation-gap-analysis.md` line 695 (Task #9) and line 259 (Gap #13)

---

## PROMPT FOR TASK 9

```
Task: Implement Gap #13 - Quote Acceptance Workflow
Reference: dev-docs/analysis/phase-1-4-implementation-gap-analysis.md line 259

## Context

We're building AevoFab AI, an AI-powered SaaS platform for electrical contractors with voice-controlled quoting and QuickBooks integration. Following the 80/20 rule to reach MVP quickly.

The Quote Acceptance Workflow is critical for converting quotes into jobs and capturing legally-binding customer approvals with audit trails.

## Completed So Far

✅ Gap #1: X-Request-ID Tracing - All requests have unique trace IDs
✅ Gap #28A: Test Endpoints - All endpoints have /test variants for dev testing
✅ Gap #28B: Idempotency Handling - Middleware prevents duplicate transactions
✅ Gap #40: Fixed current_user.tenant_id - All routes use AuthenticatedUser type
✅ Gap #31-33: Database Triggers - Quote/change order totals auto-recalculate
✅ Gap #11: Tax Calculations - IRS-compliant tax components with jurisdiction lookup
✅ Gap #6-8: Polymorphic Relationships - EntityContact and EntityAddress fully implemented
✅ Gap #38: Multi-Tenancy Isolation - 26 tests verify cross-tenant access prevention

**Test Status:** 129/129 tests passing

## Current Task

**Implement Quote Acceptance Workflow** to enable customers to approve quotes via public links and capture legally-binding acceptance details.

**Priority:** HIGH  
**Estimated Effort:** 3 days  
**Design Spec:** See `dev-docs/analysis/phase-1-4-implementation-gap-analysis.md` line 259

**Gap #13 Details:**
- **Design Requirement:** Section 5.2 - `quote_acceptance` captures approval details
- **Current State:** Table exists, no API endpoint
- **Impact:** Cannot track customer approvals, signature capture, or conversion to jobs
- **Missing:** `/quotes/{id}/accept` endpoint capturing IP, user agent, signature URL

## Requirements

### 1. API Endpoints to Create

#### `/api/v1/quotes/{quote_id}/accept` (POST) - Authenticated
Accept a quote on behalf of a customer (for internal use by tenant users).

**Request Body:**
```json
{
  "accepted_by_name": "John Smith",
  "accepted_by_email": "john@example.com",
  "signature_url": "s3://bucket/signatures/uuid.png",
  "acceptance_notes": "Optional customer comments",
  "ip_address": "192.168.1.1",
  "user_agent": "Mozilla/5.0..."
}
```

**Response:** `QuoteAcceptanceResponse` with acceptance details and updated quote status

#### `/api/v1/quotes/public/{token}/accept` (POST) - Public/Unauthenticated
Accept a quote via public link (customer-facing).

**Request Body:**
```json
{
  "accepted_by_name": "John Smith",
  "accepted_by_email": "john@example.com",
  "signature_url": "s3://bucket/signatures/uuid.png",
  "acceptance_notes": "Optional customer comments"
}
```

**Automatically captures:**
- IP address from request
- User agent from request headers
- Timestamp from server
- Links to existing `quote_public_link` record

**Response:** Public-friendly acceptance confirmation

#### `/api/v1/test/quotes/{quote_id}/accept` (POST) - Test Endpoint
Test variant for development without JWT authentication.

### 2. Database Operations

#### `quote_acceptance` Table (already exists)
**Model:** `backend/app/models/quoting.py`

**Fields to Populate:**
- `quote_id` - Link to quote being accepted
- `accepted_at` - Timestamp (server time, UTC)
- `accepted_by_name` - Customer name
- `accepted_by_email` - Customer email
- `accepted_by_user_id` - If accepted by authenticated user (nullable)
- `signature_url` - S3 URL to signature image
- `ip_address` - Client IP for audit trail
- `user_agent` - Browser/client info
- `acceptance_notes` - Optional customer comments
- `quote_public_link_id` - If accepted via public link (nullable)

#### Quote Status Update
When a quote is accepted:
1. Update `quote.status_id` to "Accepted" status
2. Set `quote.accepted_at` timestamp (if field exists, verify in model)
3. Create `quote_acceptance` record
4. Return updated quote with acceptance details

### 3. Business Logic Requirements

#### Validation Rules
1. **Quote must be in "Sent" or "Draft" status** - Cannot accept a quote that's already accepted, expired, or cancelled
2. **One acceptance per quote** - Check if `quote_acceptance` already exists for this quote_id
3. **Required fields:**
   - `accepted_by_name` (cannot be empty)
   - `accepted_by_email` (must be valid email format)
   - `signature_url` (required for legal validity)
4. **Public link validation:**
   - Verify `quote_public_link.is_active = true`
   - Check `quote_public_link.expires_at > now()` if expiration is set
   - Verify link hasn't been revoked

#### Security Considerations
1. **Tenant Isolation:** Authenticated endpoint must verify `quote.tenant_id == current_user.tenant_id`
2. **Public Link Security:** Public endpoint must verify token matches active link
3. **Rate Limiting:** Consider adding rate limit to public endpoint (future enhancement)
4. **Signature Validation:** Trust signature_url is already validated/uploaded (out of scope for this task)

#### Audit Trail
1. Log acceptance event with request ID
2. Capture full user agent string
3. Store IP address for compliance
4. Link to public link if applicable

### 4. Testing Standards

Create comprehensive test file: `backend/tests/test_quote_acceptance.py`

**Required Test Coverage:**

#### Unit Tests (12 tests)
1. ✅ Accept quote via authenticated endpoint - success case
2. ✅ Accept quote via public link - success case  
3. ✅ Reject acceptance if quote already accepted (409 Conflict)
4. ✅ Reject acceptance if quote status is "Cancelled" (400 Bad Request)
5. ✅ Reject acceptance if required fields missing (422 Validation Error)
6. ✅ Reject acceptance if invalid email format (422 Validation Error)
7. ✅ Reject acceptance if public link expired (403 Forbidden)
8. ✅ Reject acceptance if public link inactive (403 Forbidden)
9. ✅ Reject acceptance if public link token invalid (404 Not Found)
10. ✅ Verify quote status updates to "Accepted" after acceptance
11. ✅ Verify IP address and user agent are captured
12. ✅ Verify acceptance_notes are stored correctly

#### Integration Tests (4 tests)
1. ✅ Complete flow: Create quote → Generate public link → Accept via link → Verify status
2. ✅ Tenant isolation: User from Tenant A cannot accept Tenant B's quote
3. ✅ Idempotency: Same acceptance request returns 409 (not duplicate record)
4. ✅ Test endpoint works without authentication

**Before starting:**
```bash
cd backend && source .venv/bin/activate && pytest tests/ -v
```
All 129 existing tests must pass before proceeding.

**After implementation:**
```bash
pytest tests/test_quote_acceptance.py -v
```
All 16 new tests must pass.

### 5. Database Schema Verification

**CRITICAL:** Before implementing, verify the actual schema:

```python
# Read the model to confirm fields
cat backend/app/models/quoting.py | grep -A 30 "class QuoteAcceptance"
```

**Check for:**
- Does `Quote` model have `accepted_at` field? (may need to add)
- Does `QuoteAcceptance` model have all required fields?
- Are there any constraints (unique, nullable) that affect logic?
- Is there a `status_id` for "Accepted" in the reference data?

**If schema is missing fields, create Alembic migration FIRST:**
```bash
cd backend
alembic revision --autogenerate -m "add accepted_at to quote table"
alembic upgrade head
```

### 6. Pydantic Schemas to Create

**File:** `backend/api/schemas/quotes.py` (add to existing file)

```python
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional
from uuid import UUID

class QuoteAcceptanceCreate(BaseModel):
    """Request body for accepting a quote"""
    accepted_by_name: str = Field(..., min_length=1, max_length=255)
    accepted_by_email: EmailStr
    signature_url: str = Field(..., description="S3 URL to signature image")
    acceptance_notes: Optional[str] = Field(None, max_length=1000)
    ip_address: Optional[str] = Field(None, description="Auto-captured from request")
    user_agent: Optional[str] = Field(None, description="Auto-captured from request")

class QuoteAcceptanceResponse(BaseModel):
    """Response after accepting a quote"""
    id: UUID
    quote_id: UUID
    accepted_at: datetime
    accepted_by_name: str
    accepted_by_email: str
    signature_url: str
    acceptance_notes: Optional[str]
    quote_status: str  # New status of the quote (e.g., "Accepted")
    
    class Config:
        from_attributes = True
```

### 7. Route Implementation Pattern

**File:** `backend/api/routes/quotes.py` (add to existing file)

```python
from fastapi import Request

@router.post("/quotes/{quote_id}/accept", response_model=QuoteAcceptanceResponse)
async def accept_quote(
    quote_id: UUID,
    acceptance_data: QuoteAcceptanceCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user)
) -> QuoteAcceptanceResponse:
    """Accept a quote (authenticated endpoint)"""
    return await _accept_quote_impl(
        quote_id=quote_id,
        acceptance_data=acceptance_data,
        request=request,
        db=db,
        user_context=current_user
    )

@router.post("/quotes/public/{token}/accept")
async def accept_quote_via_public_link(
    token: str,
    acceptance_data: QuoteAcceptanceCreate,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Accept a quote via public link (no auth required)"""
    # Lookup quote by public link token
    # Validate link is active and not expired
    # Call shared implementation
    pass

@router.post("/test/quotes/{quote_id}/accept", response_model=QuoteAcceptanceResponse)
async def accept_quote_test(
    quote_id: UUID,
    acceptance_data: QuoteAcceptanceCreate,
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> QuoteAcceptanceResponse:
    """Test endpoint for accepting quotes without auth"""
    test_context = get_test_context(db)
    return await _accept_quote_impl(
        quote_id=quote_id,
        acceptance_data=acceptance_data,
        request=request,
        db=db,
        user_context=test_context
    )

async def _accept_quote_impl(
    quote_id: UUID,
    acceptance_data: QuoteAcceptanceCreate,
    request: Request,
    db: AsyncSession,
    user_context: AuthenticatedUser | TestUserContext
) -> QuoteAcceptanceResponse:
    """Shared implementation for quote acceptance"""
    # 1. Fetch quote and verify tenant isolation
    # 2. Validate quote status (must be "Sent" or "Draft")
    # 3. Check for existing acceptance (prevent duplicates)
    # 4. Capture IP and user agent from request
    # 5. Create quote_acceptance record
    # 6. Update quote status to "Accepted"
    # 7. Commit transaction
    # 8. Return response
    pass
```

### 8. IP Address and User Agent Extraction

```python
def get_client_ip(request: Request) -> str:
    """Extract client IP from request, respecting X-Forwarded-For"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"

def get_user_agent(request: Request) -> str:
    """Extract user agent from request headers"""
    return request.headers.get("User-Agent", "unknown")
```

### 9. Error Handling

Follow RFC 7807 format for errors:

```python
# Quote already accepted
raise HTTPException(
    status_code=409,
    detail={
        "type": "quote_already_accepted",
        "title": "Quote Already Accepted",
        "detail": f"Quote {quote_id} was already accepted on {existing_acceptance.accepted_at}",
        "quote_id": str(quote_id)
    }
)

# Invalid quote status
raise HTTPException(
    status_code=400,
    detail={
        "type": "invalid_quote_status",
        "title": "Invalid Quote Status",
        "detail": f"Quote must be in 'Sent' or 'Draft' status. Current status: {quote.status.name}",
        "current_status": quote.status.name
    }
)

# Public link expired
raise HTTPException(
    status_code=403,
    detail={
        "type": "public_link_expired",
        "title": "Public Link Expired",
        "detail": f"This quote link expired on {link.expires_at}",
        "expired_at": str(link.expires_at)
    }
)
```

## Key Files to Review

### Architecture & Design
- `dev-docs/db-design/aevofab-db-process-v2.6h.md` - Section 5.2 (Quote Acceptance)
- `dev-docs/analysis/phase-1-4-implementation-gap-analysis.md` - Gap #13 (line 259)

### Backend Code to Study
- `backend/app/models/quoting.py` - QuoteAcceptance model
- `backend/api/routes/quotes.py` - Existing quote routes for pattern reference
- `backend/api/schemas/quotes.py` - Existing quote schemas
- `backend/core/test_context.py` - Test context pattern

### Related Models
- `Quote` - The quote being accepted
- `QuotePublicLink` - For public acceptance flow
- `LifecycleStatus` - For "Accepted" status lookup
- `User` - For authenticated user acceptance

### Testing References
- `backend/tests/test_quotes.py` - Existing quote tests
- `backend/tests/conftest.py` - Fixtures for testing
- `backend/tests/test_test_endpoints.py` - Test endpoint patterns

## Success Criteria

- [ ] Remediation plan created: `dev-docs/analysis/gap-13-quote-acceptance-remediation-plan.md`
- [ ] Schema verification completed (verify QuoteAcceptance model fields)
- [ ] Alembic migration created if needed (add `accepted_at` to Quote if missing)
- [ ] Pydantic schemas created (QuoteAcceptanceCreate, QuoteAcceptanceResponse)
- [ ] Authenticated endpoint implemented: `/api/v1/quotes/{quote_id}/accept`
- [ ] Public endpoint implemented: `/api/v1/quotes/public/{token}/accept`
- [ ] Test endpoint implemented: `/api/v1/test/quotes/{quote_id}/accept`
- [ ] IP address and user agent capture working
- [ ] Quote status updates to "Accepted" on acceptance
- [ ] Duplicate acceptance prevented (409 Conflict)
- [ ] Public link validation (active, not expired)
- [ ] All 129 existing tests still pass
- [ ] New test file created: `backend/tests/test_quote_acceptance.py` (16 tests)
- [ ] All 16 new tests passing (145 total tests)
- [ ] Gap #13 marked RESOLVED in phase-1-4-implementation-gap-analysis.md
- [ ] Code follows existing patterns (shared `_impl()` functions)
- [ ] RFC 7807 error responses implemented
- [ ] Documentation updated with usage examples

## Workflow

1. **Create Remediation Plan** (30 min)
   - Document: `dev-docs/analysis/gap-13-quote-acceptance-remediation-plan.md`
   - Break down into detailed subtasks
   - Identify any schema changes needed
   
2. **Review Database Schema** (20 min)
   ```bash
   # Verify QuoteAcceptance model
   cat backend/app/models/quoting.py | grep -A 40 "class QuoteAcceptance"
   
   # Check Quote model for accepted_at field
   cat backend/app/models/quoting.py | grep -A 100 "class Quote"
   
   # Verify lifecycle statuses include "Accepted"
   cat backend/migrations/seed_test_data.py | grep -i "accepted"
   ```

3. **Create Migration if Needed** (30 min)
   - Add `accepted_at` to Quote model if missing
   - Add "Accepted" status to seed data if missing
   - Run migration
   
4. **Implement Schemas** (1 hour)
   - Add to `backend/api/schemas/quotes.py`
   - QuoteAcceptanceCreate with validation
   - QuoteAcceptanceResponse
   
5. **Implement Shared Logic** (3 hours)
   - Create `_accept_quote_impl()` in quotes.py
   - Implement validation logic
   - Implement database operations
   - Add error handling
   
6. **Implement Endpoints** (2 hours)
   - Authenticated endpoint
   - Public link endpoint (with token lookup)
   - Test endpoint
   
7. **Write Tests** (4 hours)
   - Create `backend/tests/test_quote_acceptance.py`
   - 12 unit tests
   - 4 integration tests
   - Run and debug
   
8. **Integration Testing** (1 hour)
   - Test complete flow manually
   - Verify with curl commands
   - Check database records
   
9. **Update Documentation** (1 hour)
   - Mark Gap #13 as RESOLVED
   - Add implementation notes
   - Document any deviations from plan

## Questions to Ask

Before starting:
1. ✅ Have I read Gap #13 thoroughly?
2. ✅ Do I understand the QuoteAcceptance model schema?
3. ❓ Does the Quote model have an `accepted_at` field? (need to verify)
4. ❓ Is there a lifecycle status for "Accepted"? (need to verify)
5. ✅ How do public links work in the existing code?

During implementation:
1. Am I following the shared `_impl()` function pattern?
2. Are IP and user agent being captured correctly?
3. Is tenant isolation enforced on authenticated endpoint?
4. Are all error cases handled with RFC 7807 format?
5. Do tests cover all validation scenarios?

## Example Manual Testing Flow

```bash
# 1. Create a quote (authenticated)
curl -X POST http://localhost:8000/api/v1/test/quotes \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "...",
    "site_id": "...",
    "valid_until": "2026-12-31T23:59:59Z"
  }'

# 2. Generate public link for the quote
curl -X POST http://localhost:8000/api/v1/test/quotes/{quote_id}/public-link \
  -H "Content-Type: application/json" \
  -d '{
    "expires_at": "2026-12-31T23:59:59Z"
  }'

# 3. Accept via test endpoint (authenticated flow)
curl -X POST http://localhost:8000/api/v1/test/quotes/{quote_id}/accept \
  -H "Content-Type: application/json" \
  -d '{
    "accepted_by_name": "John Smith",
    "accepted_by_email": "john@example.com",
    "signature_url": "s3://bucket/sigs/test.png",
    "acceptance_notes": "Looks great!"
  }'

# 4. Accept via public link (unauthenticated flow)
curl -X POST http://localhost:8000/api/v1/quotes/public/{token}/accept \
  -H "Content-Type: application/json" \
  -d '{
    "accepted_by_name": "Jane Doe",
    "accepted_by_email": "jane@example.com",
    "signature_url": "s3://bucket/sigs/test2.png"
  }'

# 5. Try to accept again (should get 409 Conflict)
curl -X POST http://localhost:8000/api/v1/test/quotes/{quote_id}/accept \
  -H "Content-Type: application/json" \
  -d '{
    "accepted_by_name": "John Smith",
    "accepted_by_email": "john@example.com",
    "signature_url": "s3://bucket/sigs/test.png"
  }'
```

## Notes

- **MVP Focus:** Signature validation is out of scope - trust the signature_url is valid
- **Future Enhancement:** Add webhook notification when quote is accepted
- **Future Enhancement:** Auto-convert accepted quote to job (Phase 1-B task)
- **Signature Storage:** S3 upload logic is separate (frontend responsibility)
- **Public Links:** Existing `quote_public_link` infrastructure already works
- **Rate Limiting:** Not required for MVP but note in TODO for production

## Related Tasks

- **Prerequisite:** None (all blockers resolved)
- **Follows:** Task #8 (Contact Management - completed)
- **Precedes:** Task #10 (Voice Action Execution - uses accepted quotes)
- **Related:** Task #16 (Change Orders - similar acceptance pattern)

---

**Estimated Time Breakdown:**
- Planning & schema review: 1.5 hours
- Schema changes (if needed): 0.5 hours  
- Pydantic schemas: 1 hour
- Core implementation: 5 hours
- Testing: 4 hours
- Documentation: 1 hour
- **Total: ~13 hours (2 work days with buffer)**

**Start Condition:** All 129 existing tests passing  
**End Condition:** All 145 tests passing (129 + 16 new)
```
