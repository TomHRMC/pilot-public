# Task #3: Implement Gap #1 - X-Request-ID Tracing Middleware

**Reference:** dev-docs/analysis/phase-1-4-implementation-gap-analysis.md line 41  
**Date Created:** March 16, 2026  
**Priority:** 🔴 BLOCKER  
**Estimated Effort:** 1 day

---

## Context

We're building AevoFab AI, an AI-powered SaaS platform for electrical contractors with voice-controlled quoting and QuickBooks integration. Following the 80/20 rule to reach MVP quickly.

## Completed So Far

✅ **Gap #28A:** Test Endpoints - All endpoints have /test variants for dev testing  
✅ **Gap #40:** Fixed current_user.tenant_id - All routes use AuthenticatedUser type  
✅ **Gap #28B:** Idempotency Handling - Middleware prevents duplicate transactions (37/37 tests passing)

## Current Task: X-Request-ID Tracing

**Design Requirement:** Section 1.1 - Every request must have unique trace ID for distributed debugging  
**Current State:** Basic RequestIDMiddleware exists in backend/core/middleware.py but incomplete  
**Impact:** Cannot debug production issues across service boundaries  

### What We Need

A comprehensive request tracing system that:
1. Generates unique request ID for every request (if not provided)
2. Accepts `X-Request-ID` header from clients (for correlation)
3. Returns `X-Request-ID` in response headers
4. Enriches all logs with the request ID
5. Propagates request ID to background jobs

### Design Specification

From `aevofab-db-process-v2.6h.md` Section 1.1:
> Every request must have unique trace ID for distributed debugging. The system should accept `X-Request-ID` from clients or generate a UUID if not provided, return it in response headers, and include it in all log entries.

**Example Implementation:**
```python
# backend/core/middleware.py
from fastapi import Request
import uuid

async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response
```

---

## Requirements

### 1. Documentation Standards
- **New docs go in dev-docs/** organized by topic:
  - `analysis/` - Gap analysis, remediation plans
  - `architecture-design/` - System architecture docs
  - `api-guides/` - API usage documentation
- **Always reference the authoritative design docs:**
  - `dev-docs/db-design/aevofab-db-process-v2.6h.md` - Database operations
  - `dev-docs/architecture-design/mvp-arch.md` - System architecture
  - `dev-docs/analysis/phase-1-4-implementation-gap-analysis.md` - Gap tracking
- **Create remediation plan first:** `gap-1-request-id-remediation-plan.md` before coding
- **Update gap analysis** when marking task complete

### 2. Testing Standards
- **Tests are MANDATORY** - No code without tests
- **Run existing tests first:** `cd backend && pytest tests/ -v` (should show 37+ passing)
- **All existing tests must pass** before new code is merged
- **Create new test file:** `backend/tests/test_request_id.py`
- **Test coverage required:**
  - Request ID generation (UUID format)
  - Header acceptance (client-provided ID)
  - Response header inclusion
  - Request state population
  - Invalid ID handling
- **Use existing fixtures:** See `backend/tests/conftest.py`

### 3. Code Standards
- **Follow existing patterns** - Check `backend/core/idempotency.py` for middleware example
- **Type hints required** - All function parameters and returns
- **Error handling** - RFC 7807 format (see existing routes)
- **Docstrings required** - Document all functions/classes
- **No feature creep** - Keep it simple: generate ID, add to headers, populate request.state

### 4. Implementation Checklist

Current state:
- ✅ `backend/core/middleware.py` exists with basic RequestIDMiddleware
- ✅ Registered in `backend/app/main.py`
- ❌ **Needs enhancement:** Log enrichment, validation, comprehensive tests

Tasks:
1. **Review existing middleware** - Check what's already implemented
2. **Enhance middleware** - Add logging, validation, edge case handling
3. **Create logging helper** - Function to include request_id in logs
4. **Write comprehensive tests** - Cover all scenarios
5. **Update documentation** - Add usage examples
6. **Mark gap resolved** - Update phase-1-4-implementation-gap-analysis.md

### 5. Workflow
1. **Read the gap analysis** - Lines 41-57 in phase-1-4-implementation-gap-analysis.md
2. **Review existing code** - backend/core/middleware.py, backend/app/main.py
3. **Create remediation plan** - dev-docs/analysis/gap-1-request-id-remediation-plan.md
4. **Get approval** on the plan
5. **Enhance middleware** - Add logging integration, validation
6. **Write tests** - backend/tests/test_request_id.py
7. **Run all tests** - Must pass (37+ tests)
8. **Update documentation** - Mark Gap #1 as RESOLVED
9. **Commit** with message: "feat: enhance X-Request-ID tracing with logging (Gap #1)"

---

## Key Files to Review

### Current Implementation
- **backend/core/middleware.py** - Existing RequestIDMiddleware (needs enhancement)
- **backend/app/main.py** - Middleware registration (verify order)

### Reference Examples
- **backend/core/idempotency.py** - Recent middleware implementation pattern
- **backend/tests/test_idempotency.py** - Test pattern for middleware
- **dev-docs/analysis/gap-28b-idempotency-remediation-plan.md** - Documentation pattern

### Design Specs
- **dev-docs/architecture-design/mvp-arch.md** - Monitoring & Observability section
- **dev-docs/db-design/aevofab-db-process-v2.6h.md** - Section 1.1

---

## Success Criteria

- [ ] Remediation plan created in dev-docs/analysis/gap-1-request-id-remediation-plan.md
- [ ] RequestIDMiddleware enhanced with:
  - [ ] UUID generation if X-Request-ID not provided
  - [ ] Request state population (request.state.request_id)
  - [ ] Response header inclusion
  - [ ] Input validation (reject invalid UUIDs)
- [ ] Logging helper created (optional but recommended)
- [ ] Comprehensive tests in backend/tests/test_request_id.py:
  - [ ] Test ID generation
  - [ ] Test header acceptance
  - [ ] Test response headers
  - [ ] Test invalid ID rejection
  - [ ] Test request state population
- [ ] All 37+ existing tests still pass
- [ ] Documentation updated:
  - [ ] Gap #1 marked RESOLVED in phase-1-4-implementation-gap-analysis.md
  - [ ] Usage examples in remediation plan
- [ ] Code follows existing patterns (see idempotency.py)

---

## Implementation Notes

### Existing Code Check
```bash
# Review what's already there
cat backend/core/middleware.py
cat backend/app/main.py | grep -A 3 "RequestIDMiddleware"
```

### Middleware Enhancement Areas
1. **Validation:** Check if provided X-Request-ID is valid UUID
2. **Logging:** Create helper to include request_id in all logs
3. **Error Handling:** What if middleware fails? Don't break requests
4. **Documentation:** Inline comments and docstrings

### Test Scenarios
```python
def test_generates_request_id_if_not_provided()
def test_accepts_request_id_from_client()
def test_adds_request_id_to_response_headers()
def test_populates_request_state()
def test_rejects_invalid_request_id_format()
def test_request_id_is_uuid_format()
```

### Logging Integration Example
```python
import logging
logger = logging.getLogger(__name__)

def log_with_request_id(request: Request, message: str, level: str = "info"):
    request_id = getattr(request.state, "request_id", "UNKNOWN")
    log_message = f"[{request_id}] {message}"
    getattr(logger, level)(log_message)
```

---

## Questions to Ask Before Starting

1. **Have I reviewed backend/core/middleware.py to see what exists?**
2. **Do I understand the difference between request.state vs request.headers?**
3. **What happens if middleware throws an exception? (Answer: Request fails)**
4. **Should request ID be logged automatically or manually in routes?**
5. **What UUID version should we use? (Recommendation: UUID4)**

## Questions During Implementation

1. **Am I enhancing the existing middleware or replacing it?** (Answer: Enhance)
2. **Are all existing tests still passing?**
3. **Have I added request_id to request.state for downstream use?**
4. **Is the response header consistently added?**
5. **What if someone sends an invalid UUID format?** (Recommendation: Generate new one with warning log)

---

## Example Task Flow

```bash
# 1. Review the gap
cat dev-docs/analysis/phase-1-4-implementation-gap-analysis.md | grep -A 15 "X-Request-ID"

# 2. Check existing implementation
cat backend/core/middleware.py
cat backend/app/main.py | grep -i request

# 3. Run existing tests to establish baseline
cd backend && source .venv/bin/activate && pytest tests/ -v

# 4. Create remediation plan
# (Create dev-docs/analysis/gap-1-request-id-remediation-plan.md)

# 5. Enhance middleware
# (Edit backend/core/middleware.py)

# 6. Write tests
# (Create backend/tests/test_request_id.py)

# 7. Run all tests
pytest tests/ -v

# 8. Update gap analysis
# (Mark Gap #1 as RESOLVED)

# 9. Commit
git add .
git commit -m "feat: enhance X-Request-ID tracing with logging (Gap #1)"
```

---

## Estimated Timeline

**Total: 1 day (6-8 hours)**

- **Morning (3 hours):**
  - Review existing code (30 min)
  - Create remediation plan (30 min)
  - Enhance middleware (1.5 hours)
  - Create logging helper (30 min)

- **Afternoon (3 hours):**
  - Write comprehensive tests (2 hours)
  - Update documentation (30 min)
  - Final testing and commit (30 min)

---

## Related Context

- **Gap #28B (Idempotency):** Just completed - similar middleware pattern
- **Gap #29 (Audit Logging):** Will benefit from request ID tracing
- **Background Jobs:** Future tasks will need request ID propagation

---

## Notes

- **MVP Focus:** Keep it simple - basic tracing is enough for now
- **80/20 Rule:** Don't over-engineer - UUID generation + headers is 80% of value
- **Mike the Solo Contractor:** Needs to debug production issues - this helps!
- **No Enterprise Features:** Advanced tracing (Jaeger, Zipkin) is post-MVP

---

## Ready to Start?

Once you've reviewed this prompt and the existing code, create the remediation plan first in `dev-docs/analysis/gap-1-request-id-remediation-plan.md` before writing any code. Get approval on the plan, then proceed with implementation.

**Good luck! 🚀**
