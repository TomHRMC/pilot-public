# Implementation Prompt: FE-B23 Part A — Dashboard Aggregation Endpoints

**Mode**: Pilot Python Engineer  
**Batch**: FE-B23 Part A (Backend)  
**Source plan**: `dev-docs/analysis/pilot-app-pre-wkstm-3-prep-plan.md` §Phase 0.9 — FE-B23  
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-fe-b23-design.md`  
**Estimated session**: 1–2 hours  
**Platform**: Backend only (`backend/`)  
**Frontend companion**: FE-B23 Part B (React Engineer) — runs after this batch + `pnpm sync-api-types`

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`dev-docs/architecture-design/pilot-python-engineer-methods.md`** — §13 (Alembic), §8 (Router Design), §16 (Standard Task Workflow)
- **`backend/tests/README-adding-tests.md`** — full document

**Critical rules for this batch:**

- **Rule 1**: Never guess column names. Use `postgres-local` MCP to verify every join before writing SQL. If MCP returns an error → STOP and ask Tom.
- **Rule 2**: After endpoint changes → run `python export_openapi_json.py`.
- **Rule 3**: All error responses MUST follow RFC 7807 Problem Details format.
- **Rule 4**: Never use module-level `TestClient`. Always use the `client` fixture.
- **Rule 5**: `db.get()` is permanently banned on tenant-scoped models. Always use tenant-scoped `select()`.
- **Rule 6**: Every mutation endpoint MUST call `set_audit_context_sync()` before committing.
- **Rule 7**: If ANY test fails — fix it before declaring done.

---

## Pre-Work: Establish Regression Baseline

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=no -q 2>&1 | tail -5
```

Record exact count. Fix any pre-existing failures or confirm with Tom before proceeding.

---

## Pre-Work: Run MCP Verification Queries

> **MCP Usage Rule**: Read-only verification only. Never INSERT, UPDATE, or DELETE.

```sql
-- 1. Confirm job profitability columns exist
SELECT column_name FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'job'
  AND column_name IN ('actual_labor_cost_cents', 'actual_material_cost_cents', 'actual_profit_cents');

-- 2. Find the mobile sync conflict/escalation table for pending_field_issues count
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
  AND (table_name LIKE '%escalation%' OR table_name LIKE '%sync_conflict%')
ORDER BY table_name;

-- 3. Confirm quote_status table and code column
SELECT code FROM public.quote_status ORDER BY code;

-- 4. Confirm job_status table and code column
SELECT code FROM public.job_status ORDER BY code;
-- We need to know which codes are 'in_progress' style (active jobs)

-- 5. Confirm conversation_session table exists (for POST /voice/sessions)
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public' AND table_name = 'conversation_session';
```

---

## Pre-Work: Read These Source Files

```
backend/api/routes/dashboard.py       ← full file — understand existing structure
backend/api/routes/voice_sessions.py  ← check if POST /sessions exists or needs adding
backend/api/schemas/reports.py        ← existing dashboard widget schemas
backend/tests/conftest.py             ← understand available fixtures
backend/db_models_map.md              ← confirm model names
```

Also check:
```bash
# Does POST /voice/sessions exist?
grep -n "@router.post" backend/api/routes/voice_sessions.py

# What model class is used for conversation_session?
grep -n "class ConversationSession" backend/app/models/ai.py | head -5
```

---

## Task A1 — Add `GET /api/v1/dashboard/at-risk-jobs`

**File**: `backend/api/routes/dashboard.py`

Read the full file first. Add the endpoint following the existing patterns.

**Pydantic schemas** (add to `dashboard.py` or appropriate schema file):

```python
class AtRiskJobItem(BaseModel):
    job_id: UUID
    customer_name: str
    site_name: str | None = None
    status_code: str | None = None
    scheduled_start_at: datetime | None = None
    actual_cost_cents: int      # actual_labor_cost_cents + actual_material_cost_cents
    quoted_budget_cents: int | None = None   # from linked quote total (if exists)
    projected_margin_pct: float | None = None

class AtRiskJobsResponse(BaseModel):
    jobs: list[AtRiskJobItem]
    total: int
```

**Implementation**:

```python
@router.get("/at-risk-jobs", response_model=AtRiskJobsResponse)
def get_at_risk_jobs(
    limit: int = Query(10, ge=1, le=50),
    current_user: AuthenticatedUser = Depends(require_permission("reports.view")),
    db: Session = Depends(get_db),
) -> AtRiskJobsResponse:
    return _get_at_risk_jobs_impl(limit, db, current_user)
```

**`_get_at_risk_jobs_impl()`**:
1. Query `Job` joined to `JobStatus`, `Customer`, `Site` (isouter=True), `Quote` (isouter=True via job.quote_id)
2. Filter: `Job.tenant_id == current_user.tenant_id`, `Job.is_active == True`
3. Filter: Only active/in-progress jobs — use `JobStatus.code` to identify in-flight jobs (verify exact codes from MCP query #4)
4. For each job: compute `actual_cost_cents = job.actual_labor_cost_cents + job.actual_material_cost_cents`
5. If linked quote exists: compute `projected_margin_pct = (quote.total_cents - actual_cost_cents) / quote.total_cents * 100`
6. Get tenant's `margin_target_pct` from platform settings (default 20%) — use `get_effective_setting(db, tenant_id, "margin_target_pct", fallback=20)`
7. Filter to jobs where `projected_margin_pct < margin_target_pct`
8. If no quote linked: include job if `actual_cost_cents > 0` with `projected_margin_pct=None`
9. Order by projected_margin_pct ASC (worst first) or by actual_cost_cents DESC

All RFC 7807 errors. All IDOR-protected by `tenant_id` filter.

Also add test endpoint:
```python
@router.get("/at-risk-jobs/test", response_model=AtRiskJobsResponse)
def get_at_risk_jobs_test(
    limit: int = Query(10),
    db: Session = Depends(get_db),
    ctx: TestUserContext = Depends(get_test_context),
) -> AtRiskJobsResponse:
    return _get_at_risk_jobs_impl(limit, db, ctx)
```

---

## Task A2 — Add `GET /api/v1/dashboard/pending-approvals-summary`

**File**: `backend/api/routes/dashboard.py`

**Pydantic schema**:

```python
class PendingApprovalsSummaryResponse(BaseModel):
    pending_quotes: int
    pending_field_issues: int
```

**Implementation**:

```python
@router.get("/pending-approvals-summary", response_model=PendingApprovalsSummaryResponse)
def get_pending_approvals_summary(
    current_user: AuthenticatedUser = Depends(require_permission("quotes.view")),
    db: Session = Depends(get_db),
) -> PendingApprovalsSummaryResponse:
    return _get_pending_approvals_impl(db, current_user)
```

**`_get_pending_approvals_impl()`**:
1. Count `Quote` records joined to `QuoteStatus` where `QuoteStatus.code == 'pending_approval'` AND `Quote.tenant_id == current_user.tenant_id` AND `Quote.is_active == True`
2. Count escalated mobile sync conflicts: use the table found in MCP query #2, where `severity == 'owner_escalation'` AND `status == 'pending'` AND `tenant_id == current_user.tenant_id`
3. Return `{ pending_quotes: N, pending_field_issues: M }`

Also add `/test` endpoint following the same pattern as A1.

---

## Task A3 — Add `POST /api/v1/voice/sessions` (if missing)

Check the pre-work grep: if `POST /voice/sessions` does NOT exist in `voice_sessions.py`, add it now.

**If it doesn't exist**: Add a minimal create endpoint:

```python
@router.post("/", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
def create_session(
    current_user: AuthenticatedUser = Depends(require_permission("voice.use")),
    db: Session = Depends(get_db),
) -> SessionResponse:
    """Create a new voice conversation session."""
    return _create_session_impl(db, current_user)
```

`_create_session_impl()`: Creates a new `ConversationSession` row with `status='active'`, `tenant_id`, `user_id`. Returns the session.

Also add `/test` endpoint.

**If it already exists**: skip this task.

---

## Task A4 — Final Verification

```bash
cd <repo>/backend
source .venv/bin/activate

# Unit tests — must match or beat baseline
python -m pytest -m unit --tb=short -q 2>&1 | tail -10

# Domain-specific
python -m pytest tests/domains/platform_infrastructure/ -v -k "dashboard" 2>&1 | tail -15

# Regenerate OpenAPI
python export_openapi_json.py

# Verify new endpoints appear
python3 -c "
import json
spec = json.load(open('openapi.json'))
for p in ['at-risk-jobs', 'pending-approvals-summary']:
    matches = [k for k in spec['paths'] if p in k]
    print(f'{p}: {matches}')
"
```

Full suite:
```bash
python -m pytest --tb=short -q 2>&1 | tail -10
echo "=== FE-B23 PART A FINAL VERIFICATION COMPLETE ==="
```

---

## Test Requirements

New tests go in `tests/domains/platform_infrastructure/`:

- `test_at_risk_jobs_b23.py`:
  - Returns empty list when no at-risk jobs
  - Returns only in-progress jobs below margin target
  - Tenant isolation: jobs from other tenants not returned
  - `pytestmark = [pytest.mark.domain_platform_infrastructure, pytest.mark.unit]`

- `test_pending_approvals_b23.py`:
  - Returns 0,0 when nothing pending
  - Counts pending_approval quotes correctly (scoped to tenant)
  - `pytestmark = [pytest.mark.domain_platform_infrastructure, pytest.mark.unit]`

Test resilience rules apply: never count all tenant rows — always scope by inserted IDs.

---

## Definition of Done — FE-B23 Part A

- [ ] Regression baseline captured (`pytest -m unit`)
- [ ] All MCP pre-work queries run — profitability columns confirmed, escalation table name confirmed, quote status codes confirmed
- [ ] All mandatory source files read before coding
- [ ] **A1**: `GET /api/v1/dashboard/at-risk-jobs` + `/test` added; returns at-risk jobs below margin target
- [ ] **A2**: `GET /api/v1/dashboard/pending-approvals-summary` + `/test` added; returns pending quote + field issue counts
- [ ] **A3**: `POST /api/v1/voice/sessions` added if missing (or confirmed to exist)
- [ ] All new errors use RFC 7807 Problem Details format
- [ ] Tests in `tests/domains/platform_infrastructure/` pass
- [ ] `python export_openapi_json.py` runs cleanly
- [ ] New endpoints visible in `openapi_schema_map.md`
- [ ] **Phase 1**: All unit tests pass (`pytest -m unit`)
- [ ] **Phase 2**: Full suite passes (`pytest`)
- [ ] Final test count documented
- [ ] Completion Summary added to impl plan §Phase 0.9

---

## Handoff Instructions

When all acceptance criteria pass:

1. Run `python export_openapi_json.py` one final time
2. Commit: `feat(fe-b23-be): dashboard aggregation endpoints + voice session create (FE-B23 Part A)`
3. Notify React Engineer: **"FE-B23 Part A complete. Run `cd frontend && pnpm sync-api-types` then proceed with `batch-fe-b23-react-engr-prompt.md`."**
