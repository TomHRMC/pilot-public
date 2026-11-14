# Task #4: Implement Database Triggers for Data Integrity

**Reference:** dev-docs/analysis/phase-1-4-implementation-gap-analysis.md line 576  
**Date Created:** March 17, 2026  
**Priority:** 🔴 BLOCKER  
**Estimated Effort:** 4 days

---

## Context

We're building AevoFab AI, an AI-powered SaaS platform for electrical contractors with voice-controlled quoting and QuickBooks integration. Following the 80/20 rule to reach MVP quickly.

## Completed So Far

✅ **Gap #28A:** Test Endpoints - All endpoints have /test variants for dev testing (30 tests passing)  
✅ **Gap #40:** Fixed current_user.tenant_id - All routes use AuthenticatedUser type  
✅ **Gap #28B:** Idempotency Handling - Middleware prevents duplicate transactions (15 tests passing)  
✅ **Gap #1:** X-Request-ID Tracing - Request ID middleware with logging helpers (21 tests passing)

**Total: 73/73 tests passing** ✅

## Current Task: Database Triggers

**Design Requirement:** Sections in aevofab-db-process-v2.6h.md  
**Current State:** Manual calculations in Python - error-prone and inconsistent  
**Impact:** Data integrity issues with quote totals, user email sync

### What We Need

Implement three critical PostgreSQL triggers to maintain data integrity:

1. **Quote Totals Recalculation Trigger** (#31 - BLOCKER)
2. **Change Order Totals Trigger** (#32 - HIGH PRIORITY)  
3. **User Email Sync Trigger** (#33 - HIGH PRIORITY)

### Design Specification

From `aevofab-db-process-v2.6h.md`:

**Section 5.1 - Quote Totals:**
> When quote_line records are inserted, updated, or deleted, the quote header totals (subtotal_cents, tax_amount_cents, total_cents) must be automatically recalculated via PostgreSQL trigger.

**Section 1.1 - User Email Sync:**
> When user_endpoint.email changes and is_primary=true, automatically update user.email via trigger to maintain consistency.

**Architecture Rationale:**
- Database triggers guarantee atomicity and consistency
- Eliminate race conditions from concurrent updates
- Reduce application-level complexity
- Ensure data integrity even if bugs exist in API code

---

## Requirements

### 1. Documentation Standards
- **New docs go in dev-docs/** organized by topic:
  - `analysis/` - Gap analysis, remediation plans
  - `architecture-design/` - System architecture docs
  - `db-design/` - Database schema and process docs
- **Always reference the authoritative design docs:**
  - `dev-docs/db-design/aevofab-db-process-v2.6h.md` - Database operations
  - `dev-docs/architecture-design/mvp-arch.md` - System architecture
  - `dev-docs/analysis/phase-1-4-implementation-gap-analysis.md` - Gap tracking
- **Create remediation plan first:** `gap-31-33-database-triggers-remediation-plan.md` before coding
- **Update gap analysis** when marking tasks complete

### 2. Testing Standards
- **Tests are MANDATORY** - No code without tests
- **Run existing tests first:** `cd backend && pytest tests/ -v` (should show 73 passing)
- **All existing tests must pass** before new code is merged
- **Create new test file:** `backend/tests/test_database_triggers.py`
- **Test coverage required:**
  - Quote totals recalculation (insert, update, delete quote_line)
  - Change order totals (if implemented)
  - User email sync (update user_endpoint with is_primary=true)
  - Edge cases (NULL values, concurrent updates, transaction rollback)
- **Use existing fixtures:** See `backend/tests/conftest.py`

### 3. Code Standards
- **Follow existing patterns** - Check similar Alembic migrations
- **Type hints required** - All function parameters and returns
- **Test in transaction** - Triggers should work within pytest transactions
- **Docstrings required** - Document all trigger functions
- **No feature creep** - Implement only the three specified triggers

### 4. Database Standards
- **DO NOT hallucinate schema** - Always read backend/app/models/*.py first
- **Use Alembic migrations** - Create new migration file
- **Test trigger behavior** - Verify triggers fire correctly
- **PostgreSQL pl/pgsql** - Use native PostgreSQL procedural language
- **Handle edge cases** - NULL values, zero amounts, concurrent updates

### 5. Implementation Checklist

Current state:
- ✅ Quote model exists with manual total calculation in routes
- ✅ QuoteLine model exists 
- ✅ ChangeOrder and ChangeOrderLine models exist
- ✅ User and UserEndpoint models exist
- ❌ **No triggers implemented**

Tasks:
1. **Review existing schema** - Read models/quoting.py, models/auth.py
2. **Create remediation plan** - Document trigger logic, test strategy
3. **Create Alembic migration** - New migration file with trigger DDL
4. **Implement Quote Totals Trigger:**
   - Create `recalc_quote_totals_fn()` PL/pgSQL function
   - Sums quote_line.subtotal_cents → quote.subtotal_cents
   - Sums quote_line.tax_amount_cents → quote.tax_amount_cents
   - Calculates quote.total_cents = subtotal + tax
   - Updates quote.updated_at timestamp
   - Fires on INSERT, UPDATE, DELETE of quote_line
5. **Implement Change Order Totals Trigger (if time permits):**
   - Similar logic for change_order table
6. **Implement User Email Sync Trigger:**
   - Updates user.email when user_endpoint.email changes
   - Only fires when user_endpoint.is_primary = true
   - Updates user.updated_at timestamp
7. **Write comprehensive tests** - Cover all scenarios
8. **Run migration** - Apply triggers to database
9. **Run all tests** - Must pass (73+ tests)
10. **Update documentation** - Mark gaps resolved

### 6. Workflow
1. **Read the gap analysis** - Lines 31-33, 551-554 in phase-1-4-implementation-gap-analysis.md
2. **Review database models** - backend/app/models/quoting.py, backend/app/models/auth.py
3. **Create remediation plan** - dev-docs/analysis/gap-31-33-database-triggers-remediation-plan.md
4. **Get approval** on the plan
5. **Create Alembic migration** - `alembic revision -m "add_database_triggers"`
6. **Implement trigger functions** - PL/pgSQL code in migration
7. **Write tests** - backend/tests/test_database_triggers.py
8. **Run migration** - `alembic upgrade head`
9. **Run all tests** - Must pass (73+ tests)
10. **Update documentation** - Mark Gaps #31-33 as RESOLVED

---

## Key Files to Review

### Database Models
- **backend/app/models/quoting.py** - Quote, QuoteLine, ChangeOrder, ChangeOrderLine models
- **backend/app/models/auth.py** - User, UserEndpoint models

### Current Manual Calculation
- **backend/api/routes/quotes.py** - Lines 200-202 (manual totals update)

### Reference Examples
- **backend/migrations/versions/** - Existing migration patterns
- **dev-docs/db-design/aevofab-db-process-v2.6h.md** - Section 5.1 (triggers)

### Design Specs
- **dev-docs/architecture-design/mvp-arch.md** - Database section
- **dev-docs/db-design/aevofab-db-process-v2.6h.md** - Sections 1.1, 5.1

---

## Success Criteria

- [ ] Remediation plan created in dev-docs/analysis/gap-31-33-database-triggers-remediation-plan.md
- [ ] Alembic migration created with trigger DDL
- [ ] Quote totals trigger implemented:
  - [ ] `recalc_quote_totals_fn()` function created
  - [ ] Trigger fires on INSERT/UPDATE/DELETE of quote_line
  - [ ] Correctly sums subtotal_cents, tax_amount_cents
  - [ ] Updates quote.total_cents atomically
  - [ ] Updates quote.updated_at timestamp
- [ ] User email sync trigger implemented:
  - [ ] `sync_user_email_from_endpoint_fn()` function created
  - [ ] Trigger fires on UPDATE of user_endpoint.email
  - [ ] Only updates when is_primary = true
  - [ ] Updates user.updated_at timestamp
- [ ] Change order totals trigger (optional/stretch):
  - [ ] Similar to quote totals logic
- [ ] Comprehensive tests in backend/tests/test_database_triggers.py:
  - [ ] Test quote totals recalc on insert quote_line
  - [ ] Test quote totals recalc on update quote_line
  - [ ] Test quote totals recalc on delete quote_line
  - [ ] Test user email sync on primary endpoint change
  - [ ] Test edge cases (NULL, zero, concurrent)
- [ ] All 73+ existing tests still pass
- [ ] Migration applied successfully
- [ ] Documentation updated:
  - [ ] Gaps #31-33 marked RESOLVED in phase-1-4-implementation-gap-analysis.md
  - [ ] Trigger logic documented in remediation plan
- [ ] Code follows PostgreSQL best practices

---

## Implementation Notes

### Trigger Pattern Example

```sql
-- Function: Recalculate quote totals
CREATE OR REPLACE FUNCTION recalc_quote_totals_fn()
RETURNS TRIGGER AS $$
BEGIN
    -- Determine which quote_id to update
    DECLARE
        v_quote_id UUID;
    BEGIN
        IF (TG_OP = 'DELETE') THEN
            v_quote_id := OLD.quote_id;
        ELSE
            v_quote_id := NEW.quote_id;
        END IF;

        -- Recalculate totals
        UPDATE quote
        SET 
            subtotal_cents = COALESCE((
                SELECT SUM(subtotal_cents)
                FROM quote_line
                WHERE quote_id = v_quote_id
                  AND deleted_at IS NULL
            ), 0),
            tax_amount_cents = COALESCE((
                SELECT SUM(tax_amount_cents)
                FROM quote_line
                WHERE quote_id = v_quote_id
                  AND deleted_at IS NULL
            ), 0),
            updated_at = NOW()
        WHERE id = v_quote_id;

        -- Calculate total = subtotal + tax
        UPDATE quote
        SET total_cents = subtotal_cents + tax_amount_cents
        WHERE id = v_quote_id;

        RETURN NEW;
    END;
END;
$$ LANGUAGE plpgsql;

-- Trigger: Fire on quote_line changes
CREATE TRIGGER quote_line_totals_trigger
AFTER INSERT OR UPDATE OR DELETE ON quote_line
FOR EACH ROW
EXECUTE FUNCTION recalc_quote_totals_fn();
```

### Test Pattern Example

```python
def test_quote_totals_recalculated_on_line_insert(client, db_session):
    """Test that quote totals update when quote_line is inserted."""
    # Create quote
    quote = Quote(
        tenant_id=TEST_TENANT_ID,
        customer_id=customer.id,
        subtotal_cents=0,
        tax_amount_cents=0,
        total_cents=0
    )
    db_session.add(quote)
    db_session.commit()
    
    # Add quote line
    line = QuoteLine(
        quote_id=quote.id,
        description="Test line",
        subtotal_cents=10000,  # $100.00
        tax_amount_cents=800,  # $8.00
    )
    db_session.add(line)
    db_session.commit()
    db_session.refresh(quote)
    
    # Verify trigger fired and updated quote totals
    assert quote.subtotal_cents == 10000
    assert quote.tax_amount_cents == 800
    assert quote.total_cents == 10800
```

---

## Questions to Ask Before Starting

1. **Have I reviewed the existing Quote and QuoteLine models?**
2. **Do I understand PL/pgSQL syntax and trigger mechanics?**
3. **What happens if a quote_line is soft-deleted (deleted_at set)?**
4. **Should triggers handle concurrent updates? (Answer: PostgreSQL handles via MVCC)**
5. **What if quote has no lines? (Answer: Totals should be 0)**

## Questions During Implementation

1. **Am I using COALESCE to handle NULL sums?**
2. **Am I filtering by deleted_at IS NULL for soft deletes?**
3. **Are all tests passing after migration?**
4. **Does the trigger handle INSERT, UPDATE, AND DELETE?**
5. **Am I updating updated_at timestamp?**

---

## Example Task Flow

```bash
# 1. Review the gap
cat dev-docs/analysis/phase-1-4-implementation-gap-analysis.md | grep -A 10 "Database Triggers"

# 2. Check database models
cat backend/app/models/quoting.py | grep -A 20 "class Quote"
cat backend/app/models/quoting.py | grep -A 20 "class QuoteLine"

# 3. Run existing tests to establish baseline
cd backend && source .venv/bin/activate && pytest tests/ -v
# Should show: 73 passed

# 4. Create remediation plan
# (Create dev-docs/analysis/gap-31-33-database-triggers-remediation-plan.md)

# 5. Create Alembic migration
alembic revision -m "add_database_triggers_for_quote_totals_and_user_email"

# 6. Write trigger functions in migration file
# (Edit backend/migrations/versions/XXXX_add_database_triggers.py)

# 7. Apply migration
alembic upgrade head

# 8. Write tests
# (Create backend/tests/test_database_triggers.py)

# 9. Run all tests
pytest tests/ -v

# 10. Update gap analysis
# (Mark Gaps #31-33 as RESOLVED)

# 11. Commit
git add .
git commit -m "feat: implement database triggers for quote totals and user email sync (Gaps #31-33)"
```

---

## Estimated Timeline

**Total: 4 days (28-32 hours)**

- **Day 1 (Morning - 3 hours):**
  - Review existing code and models
  - Create remediation plan
  - Get approval

- **Day 1 (Afternoon - 4 hours):**
  - Create Alembic migration
  - Implement quote totals trigger function
  - Test manually in psql

- **Day 2 (Morning - 3 hours):**
  - Implement user email sync trigger
  - Refine trigger logic
  - Apply migration

- **Day 2 (Afternoon - 4 hours):**
  - Write comprehensive test suite
  - Debug failing tests
  - Fix edge cases

- **Day 3 (Full day - 6 hours):**
  - Implement change order totals trigger (stretch)
  - Additional testing
  - Edge case handling

- **Day 4 (Morning - 3 hours):**
  - Final testing and verification
  - Update documentation
  - Mark gaps resolved

- **Day 4 (Afternoon - 2 hours):**
  - Code review
  - Final commit
  - Buffer for issues

---

## Related Context

- **Gap #11:** Tax Calculations - Will benefit from trigger-based totals
- **Gap #12:** Quote Totals Recalculation - This IS Gap #12
- **Gap #5:** User Endpoint Sync - This IS Gap #5

---

## Notes

- **MVP Focus:** Implement only the three specified triggers
- **80/20 Rule:** Quote totals is highest priority (60%), user email sync (30%), change order (10%)
- **Mike the Solo Contractor:** Needs accurate quote totals for profitability tracking
- **No Enterprise Features:** Advanced trigger monitoring, audit trails via triggers is post-MVP

---

## Database Considerations

### Soft Deletes
All models use `deleted_at` for soft deletes. Triggers must filter:
```sql
WHERE deleted_at IS NULL
```

### Timestamps
Always update `updated_at` when trigger modifies records:
```sql
SET updated_at = NOW()
```

### NULL Handling
Use `COALESCE` for SUM operations:
```sql
COALESCE(SUM(subtotal_cents), 0)
```

### Transaction Safety
Triggers run within the same transaction, so rollback works correctly.

---

## Ready to Start?

Once you've reviewed this prompt and the existing code, create the remediation plan first in `dev-docs/analysis/gap-31-33-database-triggers-remediation-plan.md` before writing any trigger code. Get approval on the plan, then proceed with implementation.

**Good luck! 🚀**
