# Implementation Prompt: C-B13 (Part A — Python Engineer) — Public Charter Availability Endpoint

**Mode**: Pilot Python Engineer
**Batch**: C-B13 (Part A — Python Engineer runs FIRST)
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §2.0 row 14r, §2.1a C-5
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-c-b13-design.md`
**Estimated session**: 1–2 hours
**Platform**: Backend only (`backend/`)
**Frontend companion**: C-B13 Part B (React Engineer) — **gated on a UI design spec from pilot-marketing-ui-designer + Tom approval**. Do NOT start Part B until the UI spec is approved. After Part A closes, run `python export_openapi_json.py` + `pnpm sync-api-types` as the handoff signal.

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-python-engineer/python-engineer-rules.md`** — full document; the 25 hard rules are non-negotiable STOPs
- **`dev-docs/architecture-design/pilot-python-engineer-methods.md`** — §13 (Alembic), §8 (Router Design), §5 (Model Design), §16 (Standard Task Workflow)
- **`backend/tests/README-adding-tests.md`** — full document; this governs all test file structure, domain markers, and fixture rules

Critical rules for this batch:

- **Rule 1**: Never guess column names, data types, or table names. Use `postgres-local` MCP to verify every name before use. If MCP returns an error → **STOP and ask Tom**.
- **Rule 3**: After any endpoint change → run `python export_openapi_json.py` (updates both `openapi.json` and `openapi_schema_map.md`).
- **Rule 7**: The `postgres-local` MCP is for **read-only verification only**. Never use it to INSERT, UPDATE, or DELETE data.
- **Rule 11**: If ANY test fails during your work — even one that appears to be a pre-existing failure — **you must fix it before declaring the batch done**.
- **Rule 12 (sync routes)**: This app is **synchronous by design**. Every DB-touching route and `_impl()` is a plain `def`. **Never convert a handler that touches the sync `Session` to `async def`**.
- **Rule 13 (Pydantic v2)**: Use v2 idioms only. Banned v1 carryover: `class Config`, `@validator`, `.dict()`, `.json()`, `.parse_obj()`. Use `model_config = ConfigDict(...)`, `@field_validator` / `@model_validator`, `.model_dump()`, `.model_validate()`. Every route needs `response_model`.
- **Rule 14 (Ruff)**: Run ruff **only against the files you changed** — `git diff --name-only HEAD -- '*.py'` to get the list, then `ruff check --fix <files> && ruff format <files>`. Fix ALL errors in those files.
- **Rule 16 (verify, don't assume)**: 186 tables exist. Query `information_schema.columns` for every table you touch this session before writing SQL.

---

## Pre-Work: Establish Regression Baseline

Before touching any file, capture the current **unit-only** test baseline:

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=no -q 2>&1 | tail -5
```

Record the exact count: **`X passed, Y failed`**.

> **If any tests are already failing before you start**: Do NOT treat them as "pre-existing" and proceed. Either confirm with Tom or fix before starting.

---

## Pre-Work: Run MCP Verification Queries

> **MCP Usage Rule**: The `postgres-local` MCP is for **read-only verification only**. Use it to confirm table names, column types, and existing data. Never use it to INSERT, UPDATE, or DELETE. If a query fails or returns an error → STOP and ask Tom before proceeding.

Run **all** of these via `postgres-local` MCP before writing any code:

```sql
-- 1. Verify subscription_tier has is_active + signup_cap for Charter
SELECT tier_name, is_active, signup_cap, price_locked
FROM subscription_tier WHERE tier_name = 'charter';

-- 2. Count Charter-eligible tenants
SELECT COUNT(*) as charter_count FROM tenant WHERE charter_eligible = true;

-- 3. Verify tenant has charter_eligible column
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'tenant'
  AND column_name IN ('charter_eligible', 'charter_member_number')
ORDER BY ordinal_position;

-- 4. Verify subscription_tier columns
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'subscription_tier'
  AND column_name IN ('tier_name', 'is_active', 'signup_cap')
ORDER BY ordinal_position;
```

---

## Pre-Work: Read These Source Files

Use `read_file` on each of these before writing any code:

```
backend/api/routes/public_quotes.py          ← why: existing public endpoint pattern (no auth, APIRouter, prefix="/api/v1/public")
backend/app/main.py                          ← why: router registration pattern — see how public_quotes/public_invoices are registered
backend/app/models/subscription.py            ← why: SubscriptionTier model (tier_name, is_active, signup_cap)
backend/app/models/core.py                    ← why: Tenant model (charter_eligible)
backend/db_models_map.md                      ← why: confirm model names and table mappings
backend/tests/conftest.py                     ← why: available fixtures
```

Also run:
```bash
grep -rn "prefix.*api/v1/public" backend/app/main.py
grep -rn "charter_eligible" backend/app/models/ --include="*.py"
```

---

## Background / Context

C-B13 builds the public Charter availability endpoint — a single read-only, no-auth endpoint that the marketing site (`/charter` page) calls to determine whether the Charter cohort is still open and how many spots remain.

**Spec reference**: `pilot-tech-impl-spec-v1.md` §10 — `GET /api/v1/public/charter-availability` → `{open, remaining}`. Suppress numeric counter until `remaining <= 8` (GTM §6.8 — this suppression is a frontend concern, the API always returns the true count).

**No migration** — all required columns exist from C-B2.

**This is a very small batch** — one endpoint, one file, 5 tests. Estimated 1–2 hours.

---

## Task 1 — Create `api/routes/public_charter.py` (NEW)

Create `backend/api/routes/public_charter.py` with the public charter-availability endpoint.

**Full implementation** (from design doc §F.1):

```python
"""C-B13 — Public Charter availability endpoint.

GET /api/v1/public/charter-availability → {open: bool, remaining: int}
No auth required. Read-only query.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlmodel import Session, select, func

from app.models.core import Tenant
from app.models.subscription import SubscriptionTier
from core.db import get_db

router = APIRouter()


class CharterAvailabilityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    open: bool
    remaining: int


@router.get(
    "/charter-availability",
    response_model=CharterAvailabilityResponse,
)
def get_charter_availability(db: Session = Depends(get_db)):
    """Public endpoint — returns Charter cohort availability.

    Returns {open: false, remaining: 0} when:
    - Charter tier not found
    - Charter tier is_active = false (cohort closed)
    - remaining <= 0 (cap reached)
    """
    charter_tier = db.exec(
        select(SubscriptionTier).where(SubscriptionTier.tier_name == "charter")
    ).first()

    if not charter_tier or not charter_tier.is_active:
        return CharterAvailabilityResponse(open=False, remaining=0)

    charter_count = db.exec(
        select(func.count(Tenant.id)).where(Tenant.charter_eligible == True)  # noqa: E712
    ).one()

    remaining = charter_tier.signup_cap - charter_count

    if remaining <= 0:
        return CharterAvailabilityResponse(open=False, remaining=0)

    return CharterAvailabilityResponse(open=True, remaining=remaining)
```

**Key notes**:
- This is a **public endpoint** — no `get_current_user()`, no `require_permission()`, no `TestUserContext`. Anyone can call it.
- No `/test` twin needed — the endpoint has no auth to bypass.
- The `noqa: E712` on `== True` is required because SQLModel/SQLAlchemy needs `== True` for boolean comparisons (not `is True`). This is a known pattern in the codebase.
- The endpoint always returns 200 — even when the cohort is closed. The `open: false` field tells the frontend.

**Intermediate unit test run**: `pytest -m unit --tb=short -q | tail -5`

---

## Task 2 — Register Router in `app/main.py`

In `backend/app/main.py`, add the public_charter router. Place it near the other public route registrations (around line 348-360):

```python
from api.routes import public_charter

app.include_router(
    public_charter.router,
    prefix="/api/v1/public",
    tags=["public"],
)
```

Follow the existing pattern — `public_quotes`, `public_invoices`, and `public_short_redirect` are all registered with `prefix="/api/v1/public"`.

**Intermediate unit test run**: `pytest -m unit --tb=short -q | tail -5`

---

## Task 3 — Regenerate OpenAPI

```bash
cd <repo>/backend
source .venv/bin/activate
python export_openapi_json.py
```

Verify the new endpoint appears:

```bash
grep -A 5 "charter-availability" backend/openapi_schema_map.md
```

---

## Task 4 — Regenerate Import Map

```bash
cd <repo>/backend && source .venv/bin/activate
python generate_app_import_map.py tests > app_model_imports.md
```

---

## Task 5 — Write Tests

Create `backend/tests/domains/subscriptions_usage/test_cb13_charter_availability.py`.

### Test Requirements

Per `backend/tests/README-adding-tests.md`:

**Every new test file MUST:**
- Declare `pytestmark` with both domain marker and `pytest.mark.unit`:
  ```python
  pytestmark = [
      pytest.mark.domain_subscriptions_usage,
      pytest.mark.unit,
  ]
  ```
- Use the `client` fixture (never module-level `TestClient`)
- Be placed in `backend/tests/domains/subscriptions_usage/`

**Test Resilience Rule (MANDATORY):**
- Never UPDATE or DELETE rows you did not INSERT in the current test.
- The `db_session` fixture is the correct isolation mechanism (transaction rollback).

**Mock pattern for this batch**: No mocking needed — this is a read-only endpoint with no auth. The test calls the endpoint directly via the `client` fixture. The test relies on the existing seed data (Charter tier with `signup_cap=12`, at least 1 Charter-eligible tenant).

### Required Tests (minimum 5)

| Test | Description |
|---|---|
| `test_charter_availability_open` | Charter tier active, Charter tenants exist → `{open: true, remaining: N}` where N = 12 - count. Assert `open == True` and `remaining > 0`. |
| `test_charter_availability_no_auth_required` | Endpoint returns 200 without any auth headers. |
| `test_charter_availability_response_shape` | Response has `open` (bool) and `remaining` (int) fields. |
| `test_charter_availability_closed_tier` | If Charter tier `is_active=false` → `{open: false, remaining: 0}`. (This test may need to create a mock scenario or skip if it can't modify the tier — use `db_session` to insert a test scenario or assert on the current state.) |
| `test_charter_availability_remaining_calculation` | `remaining == signup_cap - charter_count`. Assert the math is correct against the live DB state. |

**Note on the "closed tier" test**: Since the Charter tier is `is_active=true` in the seed data, you can't easily test the `is_active=false` path without modifying shared data. Options:
1. Use `db_session` to temporarily flip `is_active` within the test transaction (it rolls back) — but this modifies a shared row, which the resilience rule discourages.
2. Test the logic indirectly by asserting the response shape and that `open` is a boolean.
3. If you can safely flip `is_active` within the transaction and it rolls back, do so — but assert only on the response, not on the tier row state.

**Preferred approach**: Test the happy path (open, remaining > 0) + response shape + no-auth. For the closed-tier path, test the service logic directly (not via the endpoint) by calling the function with a mock session, OR skip it and note it as a manual test.

---

## Final Verification

### Phase 1 — Unit Tests Only

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=short -q 2>&1 | tail -10
```

### Phase 2 — Lint (changed files only) + Full Suite

```bash
cd <repo>/backend
source .venv/bin/activate

CHANGED_PY=$(git diff --name-only --diff-filter=d HEAD -- '*.py' | sed 's|^backend/||')

if [ -n "$CHANGED_PY" ]; then
    ruff check --fix $CHANGED_PY
    ruff format $CHANGED_PY
    ruff check $CHANGED_PY
fi

python -m pytest --tb=short -q 2>&1 | tail -10

python -m pytest tests/domains/subscriptions_usage/test_cb13_charter_availability.py -v 2>&1 | tail -20

grep -A 5 "charter-availability" backend/openapi_schema_map.md

echo "=== C-B13 PART A FINAL VERIFICATION COMPLETE ==="
```

---

## Definition of Done

- [ ] Pre-modification regression baseline captured (`X passed, Y failed`) using `pytest -m unit`
- [ ] Zero pre-existing unit failures confirmed before starting work (or confirmed with Tom)
- [ ] All MCP pre-work queries run — all 4 queries confirmed expected results
- [ ] All mandatory source files read before writing any code
- [ ] `api/routes/public_charter.py` created with `GET /charter-availability` endpoint
- [ ] `app/main.py` updated with router registration (`prefix="/api/v1/public"`)
- [ ] OpenAPI regenerated (1 new endpoint)
- [ ] `app_model_imports.md` regenerated
- [ ] All new test files use `pytestmark` with `domain_subscriptions_usage` + `pytest.mark.unit`
- [ ] No module-level `TestClient` in any test file
- [ ] All DB-touching routes are sync `def` — no `async def`
- [ ] Only Pydantic v2 idioms used; route has `response_model`
- [ ] `ruff check --fix && ruff format` run on changed files only — zero remaining issues
- [ ] **Phase 1**: All unit tests pass (`pytest -m unit`) — zero failures
- [ ] **Phase 2**: Full test suite passes (`pytest`) — zero failures, warning-clean
- [ ] Final test count (before → after) documented
- [ ] Completion Summary added to launch plan Appendix B

---

## Completion Summary

After all Definition of Done items are complete:

1. Add a **Completion Summary** subsection to `dev-docs/analysis/pilot-launch-plan.md` Appendix B.
2. **Handoff**: Run `python export_openapi_json.py` (already done in Task 3). The React Engineer (Part B) is gated on a UI design spec from pilot-marketing-ui-designer + Tom approval.

```markdown
### C-B13 (Part A — Python Engineer) — Public Charter Availability Endpoint: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot Python Engineer
**Source design doc**: `batch-c-b13-design.md`
**Baseline**: X passed, Y failed
**Final**: X+N passed, Y failed (+N new tests)

#### What Was Accomplished

- [Brief description]

#### Files Changed / Created

| File | Action |
|---|---|
| `backend/api/routes/public_charter.py` | Created — [what it does] |
| `backend/app/main.py` | Updated — registered public_charter router |
| ... | ... |

#### Tests Added

| Test File | Domain | Tests | All Pass |
|---|---|---|---|
| `tests/domains/subscriptions_usage/test_cb13_charter_availability.py` | `subscriptions_usage` | N | ✅ |
```

---

## After This Task — Next Step

**Part A is complete.** The React Engineer (Part B) is gated on:
1. A UI design spec from the pilot-marketing-ui-designer (must be Tom-approved before the React prompt is authored)
2. `pnpm sync-api-types` to regenerate TypeScript types from the new OpenAPI spec

Return to Pilot Architect mode to coordinate the UI design spec + React Engineer prompt.
