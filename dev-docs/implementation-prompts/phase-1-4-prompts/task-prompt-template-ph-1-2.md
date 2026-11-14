# Next Task Prompt Template

Use this prompt to start a new development task session. Copy and customize for each task.

---

## PROMPT FOR NEXT TASK

```
Task: [Implement Gap #X - Feature Name]
Reference: dev-docs/analysis/phase-1-4-implementation-gap-analysis.md line XXX

## Context

We're building AevoFab AI, an AI-powered SaaS platform for electrical contractors with voice-controlled quoting and QuickBooks integration. Following the 80/20 rule to reach MVP quickly.

## Completed So Far

✅ Gap #28A: Test Endpoints - All endpoints have /test variants for dev testing
✅ Gap #40: Fixed current_user.tenant_id - All routes use AuthenticatedUser type
✅ Gap #28B: Idempotency Handling - Middleware prevents duplicate transactions

## Current Task

[Describe the specific gap/feature to implement]

**Priority:** [BLOCKER/HIGH/MEDIUM]  
**Estimated Effort:** [X days]  
**Design Spec:** See dev-docs/analysis/phase-1-4-implementation-gap-analysis.md

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
  - `dev-docs/db-design/aevofab-db-process-v2.6h.md` - Database operations
  - `dev-docs/architecture-design/mvp-arch.md` - System architecture
  - `dev-docs/analysis/phase-1-4-implementation-gap-analysis.md` - Gap tracking
- **Create remediation plan first** (gap-XX-[name]-remediation-plan.md) before coding
- **Update gap analysis** when marking tasks complete

### 2. Testing Standards
- **Tests are MANDATORY** - No code without tests
- **Run existing tests first:**
  - Run the response type below based on the purpose for running the tests
  - verbose response: `cd backend && source .venv/bin/activate && pytest tests/ -v`
  - standard response: `cd backend && source .venv/bin/activate && pytest tests/`
  - concise response: cd backend && source .venv/bin/activate && pytest tests/ -v 2>&1 | grep -E "(passed|failed|===)" | tail -5
- **All existing tests must pass** before new code is merged
- **Create new test file:** `backend/tests/test_[feature].py`
- **Test coverage required:**
  - Unit tests for core logic
  - Integration tests for API endpoints
  - Edge cases and error conditions
- **Use existing fixtures:** See `backend/tests/conftest.py`

### 3. Code Standards
- **Follow existing patterns** - Check similar implementations first
- **Type hints required** - Use AuthenticatedUser, not User
- **Error handling** - RFC 7807 format (see existing routes)
- **Docstrings required** - Document all functions/classes
- **No feature creep** - Strictly follow 80/20 MVP prioritization

### 4. Database Standards
- **DO NOT hallucinate schema** - Always read backend/app/models/*.py first
- **Use Alembic migrations** for schema changes
- **Respect tenant isolation** - All queries filter by tenant_id
- **Follow ORM patterns** - Use SQLModel/SQLAlchemy correctly

### 5. Workflow
1. **Read the gap analysis** to understand the issue
2. **Review design specs** (db-process-v2.6h.md, mvp-arch.md)
3. **Create remediation plan** document with detailed tasks
4. **Get approval** on the plan before coding
5. **Implement** following the plan step-by-step
6. **Write tests** alongside implementation
7. **Run all tests** - Must pass before completion
8. **Update documentation** - Mark gap as RESOLVED with details of what was accomplished similar to existing resolved updates

## Key Files to Review

### Architecture
- `dev-docs/architecture-design/mvp-arch.md` - Overall system design
- `dev-docs/db-design/aevofab-db-process-v2.6h.md` - Database operations
- `dev-docs/analysis/phase-1-4-implementation-gap-analysis.md` - Gap tracking

### Backend Code
- `backend/app/models/` - Database models (SQLModel ORM)
- `backend/api/routes/` - API endpoints
- `backend/core/` - Core utilities (auth, db, middleware)
- `backend/tasks/` - Background jobs
- `backend/tests/` - Test suite

### Recent Examples
- `backend/core/idempotency.py` - Middleware pattern example
- `backend/tests/test_idempotency.py` - Test pattern example
- `dev-docs/analysis/gap-28b-idempotency-remediation-plan.md` - Documentation pattern

## Success Criteria

- [ ] Remediation plan created and approved
- [ ] Implementation complete per plan
- [ ] All existing tests pass (37/37 minimum)
- [ ] New tests written and passing
- [ ] Documentation updated
- [ ] Gap marked RESOLVED in phase-1-4-implementation-gap-analysis.md
- [ ] Code follows existing patterns and standards

## Questions to Ask

Before starting:
1. Have I read the gap analysis entry thoroughly?
2. Have I reviewed the design specification?
3. Do I understand how this fits into the MVP scope?
4. What existing code can I reference for patterns?
5. What tests need to be written?

During implementation:
1. Am I following existing patterns?
2. Are all tests passing?
3. Am I documenting as I go?
4. Is this aligned with 80/20 MVP priorities?

## Example Task Flow

```bash
# 1. Review the gap
cat dev-docs/analysis/phase-1-4-implementation-gap-analysis.md | grep -A 20 "Gap #1"

# 2. Check database models
ls -la backend/app/models/

# 3. Run existing tests
cd backend && source .venv/bin/activate && pytest tests/ -v

# 4. Create your implementation
# [write code]

# 5. Run tests again
pytest tests/ -v

# 6. Commit
git add .
git commit -m "feat: implement gap #1 - X-Request-ID tracing"
```

## Notes

- **MVP Focus:** Follow dev-docs/product-requirements/mvp-prd.md for scope
- **80/20 Rule:** See .roo/rules-mvp-builder/80-20-prioritization.md
- **Mike the Solo Contractor:** Our primary persona - keep it simple!
- **No Enterprise Features:** Multi-trade, complex scheduling, etc. are out of scope
```

---

## Usage

1. Copy the prompt section above
2. Fill in the specific task details
3. Start new Roo Coder session with the prompt
4. The AI will have full context and standards
