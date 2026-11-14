# Task #10: Voice Action Execution
## Intent-Based Business Logic Router

**Reference:** `dev-docs/analysis/phase-1-4-implementation-gap-analysis.md` line 772 (Task #10) and line 365 (Gap #17)

---

## PROMPT FOR CODING AGENT

```
Task: Implement Gap #17 - Voice Action Execution (Intent Router)
Reference: dev-docs/analysis/phase-1-4-implementation-gap-analysis.md line 365

## Context

We're building AevoFab AI, an AI-powered SaaS platform for electrical contractors with voice-controlled quoting and QuickBooks integration. Following the 80/20 rule to reach MVP quickly.

**Current State:** Voice AI can transcribe audio and parse intent using Whisper + Ollama, but intents are NOT executed. Voice commands generate telemetry only—no business logic is triggered.

**Problem:** Gap #17 is a BLOCKER. Voice AI is the core differentiator but currently useless without action execution.

## Completed So Far

✅ Gap #28A: Test Endpoints - All endpoints have /test variants for dev testing
✅ Gap #40: Fixed current_user.tenant_id - All routes use AuthenticatedUser type  
✅ Gap #28B: Idempotency Handling - Middleware prevents duplicate transactions  
✅ Gap #1: X-Request-ID Tracing - All requests tracked with UUID  
✅ Gap #31-33: Database Triggers - Quote totals, change order totals, user email sync  
✅ Gap #11: Tax Calculations - Jurisdiction-based tax with IRS-compliant rounding  
✅ Gap #6-8: Polymorphic Relationships - EntityContact, EntityAddress full CRUD  
✅ Gap #13: Quote Acceptance - Three acceptance flows (auth, public link, test)  
✅ Gap #38: Multi-Tenancy Isolation - 26 tests verifying tenant isolation  

**Test Status:** 182/182 tests passing (as of 2026-03-18)

## Current Task

**Implement Intent-Based Action Execution Router**

**Priority:** BLOCKER  
**Estimated Effort:** 8 days  
**Design Spec:** See `dev-docs/architecture-design/mvp-arch.md` Section 6 - Voice AI Pipeline  
**Database Process:** See `dev-docs/db-design/aevofab-db-process-v2.6h.md` Section 6 - Voice AI Integration

### What Needs to Be Built

After `parse_intent()` extracts intent type and entities, route to business logic handlers:

```python
# New file: backend/services/voice_action_router.py
intent_handlers = {
    "create_quote": create_quote_via_voice,
    "add_quote_line": add_line_via_voice,
    "calculate_voltage_drop": calculate_nec_voltage_drop,
    "query_job_profit": get_job_profitability,
    "navigate": return_navigation_command,
    "create_customer": create_customer_via_voice,
    "create_job": create_job_via_voice,
    "log_time_entry": log_time_entry_via_voice,
    "add_expense": add_expense_via_voice,
    "send_quote": send_quote_via_voice
}

result = await intent_handlers[intent_type](entities, current_user, db, session)
```

### Top 10 Voice Commands to Implement (MVP)

1. **create_quote** - "Create a new quote for Mike's Diner"
2. **add_quote_line** - "Add 10 feet of 12-gauge wire"
3. **query_job_profit** - "What's the profit on the Smith job?"
4. **calculate_voltage_drop** - "Calculate voltage drop for 200 feet of 10 AWG"
5. **navigate** - "Show me active jobs" / "Go to quotes"
6. **create_customer** - "Create customer John Smith at 123 Main Street"
7. **create_job** - "Create a service call job for Site 42"
8. **log_time_entry** - "Log 3 hours on the Johnson panel upgrade"
9. **add_expense** - "Add $45.99 expense for breakers from Home Depot"
10. **send_quote** - "Send quote #123 to the customer"

## Requirements

### 1. Documentation Standards
- **Create remediation plan first:** `dev-docs/analysis/gap-17-voice-action-execution-remediation-plan.md`
- **Reference authoritative docs:**
  - `dev-docs/db-design/aevofab-db-process-v2.6h.md` - Database schema and operations
  - `dev-docs/architecture-design/mvp-arch.md` - Voice AI architecture (Section 6)
  - `dev-docs/analysis/phase-1-4-implementation-gap-analysis.md` - Gap tracking
- **Update gap analysis** when marking task complete (mark Gap #17 as RESOLVED)

### 2. Testing Standards
- **Tests are MANDATORY** - No code without tests
- **Run existing tests first:**
  ```bash
  cd backend && source .venv/bin/activate && pytest tests/ -v
  ```
- **All 182 existing tests must pass** before new code
- **BEFORE writing tests:** Review `backend/tests/conftest.py`
  - Use existing fixtures: `db_session`, `test_tenant`, `client`, `mock_jwt_for_user`
  - Match fixture naming conventions
- **Create new test file:** `backend/tests/test_voice_actions.py`
- **Test coverage required:**
  - Unit tests for each of the 10 action handlers
  - Integration tests for voice.py → action router → business logic
  - Error handling (invalid intents, missing entities, permission errors)
  - Multi-turn conversation with context window updates
  - Tenant isolation verification

### 3. Code Standards
- **Follow existing patterns** - Check similar implementations:
  - `backend/api/routes/quotes.py` - Quote creation patterns
  - `backend/api/routes/jobs.py` - Job creation patterns
  - `backend/api/routes/voice.py` - Voice session management
- **Type hints required** - Use `AuthenticatedUser`, not `User`
- **Error handling** - RFC 7807 format (see existing routes)
- **Docstrings required** - Document all functions/classes
- **No feature creep** - Strictly follow 80/20 MVP prioritization
- **Session state management** - Update `context_window_json` after actions
- **Response format** - Return structured JSON for mobile app rendering

### 4. Database Standards
- **DO NOT hallucinate schema** - Read `backend/app/models/` first
- **Use existing models:**
  - `Quote`, `QuoteLine`
  - `Job`, `JobTimeEntry`, `JobExpense`
  - `Customer`, `Site`
  - `VoiceSession`, `VoiceIntent`
- **Respect tenant isolation** - All queries filter by `current_user.tenant_id`
- **Update context window** - After creating entities, store IDs in `session.context_window_json`

### 5. Workflow
1. **Read the gap analysis** - Understand Gap #17 requirements (line 365)
2. **Review design specs** - Voice AI section in mvp-arch.md and db-process-v2.6h.md
3. **Create remediation plan** - Document with detailed tasks and examples
4. **Get approval** on the plan before coding
5. **Implement router** - Create `backend/services/voice_action_router.py`
6. **Implement top 10 handlers** - One handler per voice command
7. **Update voice.py** - Integrate router after `parse_intent()`
8. **Write tests** - Comprehensive coverage of all 10 actions
9. **Run all tests** - Must pass before completion (182 baseline + new tests)
10. **Update documentation** - Mark Gap #17 as RESOLVED

## Key Files to Review

### Architecture
- `dev-docs/architecture-design/mvp-arch.md` - Section 6: Voice AI Pipeline
- `dev-docs/db-design/aevofab-db-process-v2.6h.md` - Section 6: Voice AI Integration
- `dev-docs/analysis/phase-1-4-implementation-gap-analysis.md` - Gap #17 (line 365), Task #10 (line 772)

### Backend Code - Voice AI
- `backend/api/routes/voice.py` - Voice endpoints (transcribe, parse intent)
- `backend/services/ai_service.py` - Whisper + Ollama integration
- `backend/app/models/voice.py` - VoiceSession, VoiceIntent models (DOES NOT EXIST - need to check models/system.py or create)

### Backend Code - Business Logic
- `backend/api/routes/quotes.py` - Quote creation (reuse for create_quote action)
- `backend/api/routes/jobs.py` - Job/expense/time entry creation
- `backend/api/routes/customers.py` - Customer creation
- `backend/api/routes/catalog.py` - Supplier item lookup

### Backend Code - Database Models
- `backend/app/models/quoting.py` - Quote, QuoteLine, QuoteAcceptance
- `backend/app/models/fulfillment.py` - Job, JobTimeEntry, JobExpense
- `backend/app/models/auth.py` - AuthenticatedUser type
- `backend/app/models/system.py` - Check for VoiceSession, VoiceIntent

### Testing Examples
- `backend/tests/test_voice.py` - Existing voice tests
- `backend/tests/test_quotes.py` - Quote creation test patterns
- `backend/tests/test_multi_tenancy_isolation.py` - Tenant isolation patterns

## Success Criteria

- [ ] Remediation plan created and approved
- [ ] Voice action router implemented (`backend/services/voice_action_router.py`)
- [ ] Top 10 voice command handlers implemented
- [ ] Voice.py integrated with router (calls after parse_intent)
- [ ] Context window JSON updated after entity creation
- [ ] All existing tests pass (182/182 minimum)
- [ ] New tests written and passing (target: 30+ new tests)
- [ ] Documentation updated
- [ ] Gap #17 marked RESOLVED in phase-1-4-implementation-gap-analysis.md
- [ ] Code follows existing patterns and standards

## Technical Architecture

### Expected Flow

```
1. User speaks: "Create a quote for Mike's Diner"
2. POST /api/v1/voice/transcribe → Whisper returns transcript
3. POST /api/v1/voice/parse-intent → Ollama extracts:
   {
     "intent_type": "create_quote",
     "entities": [
       {"type": "customer_name", "value": "Mike's Diner"}
     ],
     "confidence": 0.92
   }
4. **NEW:** voice_action_router.execute_action(intent_type, entities, user, db, session)
5. create_quote_via_voice() handler:
   - Look up or create customer "Mike's Diner"
   - Create Quote linked to customer
   - Update session.context_window_json = {"active_quote_id": 123}
   - Return structured response for mobile UI
6. Return to user: "I created Quote #123 for Mike's Diner. What would you like to add?"
```

### Context Window Management (Critical!)

After creating entities, update `session.context_window_json`:

```python
# Example after create_quote:
session.context_window_json = {
    "active_quote_id": quote.id,
    "active_customer_id": customer.id,
    "last_action": "create_quote",
    "timestamp": datetime.utcnow().isoformat()
}

# Next command: "Add 10 feet of wire" resolves to active_quote_id
```

### Response Format for Mobile App

Return structured JSON for UI rendering:

```python
{
    "action": "create_quote",
    "success": true,
    "message": "Created Quote #123 for Mike's Diner",
    "data": {
        "quote_id": 123,
        "customer_name": "Mike's Diner",
        "total_cents": 0
    },
    "next_prompts": [
        "Add line items",
        "Send to customer",
        "Cancel quote"
    ]
}
```

## Questions to Ask

Before starting:
1. Have I read Gap #17 thoroughly (line 365)?
2. Have I reviewed the Voice AI architecture in mvp-arch.md Section 6?
3. Do I understand the VoiceSession and VoiceIntent models?
4. What's the structure of `entities` returned by parse_intent()?
5. How does context_window_json currently work?

During implementation:
1. Am I reusing existing business logic (quotes.py, jobs.py)?
2. Am I updating context_window_json after each action?
3. Are all handlers respecting tenant isolation?
4. Is the response format mobile-app friendly?
5. Are all tests passing?

## Implementation Hints

### Reuse Existing Logic

**DO NOT duplicate code.** Reuse existing route handlers:

```python
# BAD - Duplicating quote creation logic
async def create_quote_via_voice(...):
    quote = Quote(...)
    db.add(quote)
    db.commit()  # Duplicates quotes.py logic

# GOOD - Reuse existing implementation
from backend.api.routes.quotes import _create_quote_impl

async def create_quote_via_voice(entities, user, db, session):
    # Extract customer from entities
    customer_id = await _resolve_customer(entities, user, db)
    
    # Reuse existing quote creation
    quote = await _create_quote_impl(
        customer_id=customer_id,
        current_user=user,
        db=db
    )
    
    # Update context window
    session.context_window_json = {"active_quote_id": quote.id}
    db.commit()
    
    return {
        "action": "create_quote",
        "success": True,
        "data": {"quote_id": quote.id}
    }
```

### Handle Missing Entities Gracefully

```python
# Example: "Add wire" without specifying quote
if "active_quote_id" not in session.context_window_json:
    return {
        "action": "add_quote_line",
        "success": False,
        "error": "No active quote. Say 'Create quote for [customer]' first.",
        "prompt": "Which customer should I create a quote for?"
    }
```

### NEC Calculations (Out of Scope for MVP)

For `calculate_voltage_drop`, return a placeholder:

```python
async def calculate_nec_voltage_drop(entities, user, db, session):
    # MVP: Return static response
    return {
        "action": "calculate_voltage_drop",
        "success": True,
        "message": "NEC calculations coming soon. Use the NEC tables for now.",
        "data": None
    }
```

**Post-MVP:** Integrate actual NEC formula library (Gap #20)

## Example Test Flow

```python
# backend/tests/test_voice_actions.py
def test_create_quote_via_voice(client, test_tenant, mock_jwt_for_user):
    """Test voice command: 'Create quote for ABC Electric'"""
    
    # 1. Create customer
    customer = Customer(
        tenant_id=test_tenant.id,
        name="ABC Electric",
        email="abc@example.com"
    )
    db.add(customer)
    db.commit()
    
    # 2. Create voice session
    session = VoiceSession(
        tenant_id=test_tenant.id,
        user_id=test_tenant.users[0].id,
        context_window_json={}
    )
    db.add(session)
    db.commit()
    
    # 3. Execute voice action
    from backend.services.voice_action_router import execute_action
    
    result = await execute_action(
        intent_type="create_quote",
        entities=[{"type": "customer_name", "value": "ABC Electric"}],
        current_user=test_tenant.users[0],
        db=db,
        session=session
    )
    
    # 4. Verify quote created
    assert result["success"] is True
    assert "quote_id" in result["data"]
    
    # 5. Verify context window updated
    db.refresh(session)
    assert session.context_window_json["active_quote_id"] == result["data"]["quote_id"]
    
    # 6. Verify tenant isolation
    quote = db.query(Quote).get(result["data"]["quote_id"])
    assert quote.tenant_id == test_tenant.id
```

## Notes

- **MVP Focus:** Follow `dev-docs/product-requirements/mvp-prd.md` for scope
- **80/20 Rule:** See `.roo/rules-mvp-builder/80-20-prioritization.md`
- **Mike the Solo Contractor:** Our primary persona - keep responses conversational and helpful
- **Voice AI is the Differentiator:** This is AevoFab's killer feature vs. ServiceTitan/Jobber
- **Context Window is Critical:** Multi-turn conversations rely on session state management
- **Error Handling:** Voice commands should NEVER crash - always return helpful fallback messages
- **Mobile-First:** Response format must be renderable on React Native UI

## Potential Challenges

1. **Entity Resolution:** "Mike's Diner" might match multiple customers → return disambiguation prompt
2. **Pronoun Resolution:** "Add it to the quote" → requires context_window_json
3. **Permission Checks:** Office staff might not have permission to create jobs → return friendly error
4. **Incomplete Information:** "Create a quote" without customer → prompt for missing data
5. **Context Expiration:** 1-hour-old session might have stale context → verify entities still exist

## Post-MVP Enhancements (Out of Scope)

- ⚠️ NEC calculation library integration (Gap #20)
- ⚠️ Voice command suggestions based on current UI screen
- ⚠️ Multi-language support (Spanish for field techs)
- ⚠️ Voice shortcuts (aliases like "log time" → "log_time_entry")
- ⚠️ Undo voice actions
- ⚠️ Voice command analytics (which commands are most used?)

```

---

## Usage

1. Copy the prompt section above
2. Start new Roo Coder session in **Code mode**
3. Paste the prompt
4. The AI will create remediation plan first, then implement

---

**Prepared By:** AevoFab Architect  
**Date:** March 19, 2026  
**Task Reference:** Phase 1-B, Task #10 (Gap #17)  
**Estimated Effort:** 8 days  
**Prerequisites:** All Phase 1-A tasks complete (Gaps #1, #28A, #28B, #31-33, #40 resolved)
