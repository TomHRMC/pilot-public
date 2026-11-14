# Implementation Prompt: B17 — API Contract Fixes + Missing Endpoints (Part A)

**Mode**: Pilot Python Engineer  
**Batch**: B17 Part A (Backend)  
**Source plan**: `dev-docs/analysis/pilot-app-pre-wkstm-3-prep-plan.md` §Phase 0.9 — B17  
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-b17-design.md`  
**Estimated session**: 3–5 hours  
**Platform**: Backend only (`backend/`)  
**Frontend companion**: B17 Part B (React Engineer) — runs after this batch + `pnpm sync-api-types`

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`dev-docs/architecture-design/pilot-python-engineer-methods.md`** — §13 (Alembic), §8 (Router Design), §5 (Model Design), §16 (Standard Task Workflow)
- **`backend/tests/README-adding-tests.md`** — full document; governs all test file structure, domain markers, and fixture rules

**Critical rules for this batch:**

- **Rule 1**: Never guess column names, data types, or table names. Use `postgres-local` MCP to verify every name before use. If MCP returns an error → **STOP and ask Tom**.
- **Rule 2**: After any endpoint change → run `python export_openapi_json.py` (updates both `openapi.json` and `openapi_schema_map.md`).
- **Rule 3**: All API error responses MUST follow RFC 7807 Problem Details format (`{"type": "https://...", "title": "...", "status": N, "detail": "..."}`). Non-standard error shapes break the frontend `<NotificationBanner>` severity routing.
- **Rule 4**: Never use module-level `TestClient` in any test file. Always use the `client` fixture from `conftest.py`.
- **Rule 5**: `db.get()` is permanently banned on tenant-scoped models. Always use tenant-scoped `select()` with an explicit `WHERE tenant_id = :tid` clause.
- **Rule 6**: The `postgres-local` MCP is for **read-only verification only**. Never use it to INSERT, UPDATE, or DELETE data — all data changes go through the application code.
- **Rule 7**: Every new mutation endpoint MUST call `set_audit_context_sync(db, user_id=user.id)` before committing. Without this, `actor_id` is NULL in `audit_log` — silent audit attribution loss.
- **Rule 8**: If ANY test fails during your work — even one that appears to be pre-existing — **you must fix it before declaring the batch done**. There is no "not my fault" exception. If you cannot identify the root cause → STOP and ask Tom.

---

## Pre-Work: Establish Regression Baseline

Before touching any file, capture the current **unit-only** test baseline:

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=no -q 2>&1 | tail -5
```

Record the exact count: **`X passed, Y failed`**.

> **If any tests are already failing before you start**: Do NOT treat them as "pre-existing" and proceed anyway. Either:
> (a) Confirm with Tom that this is a known, accepted failure with a documented reason before proceeding, OR
> (b) Fix the failure before touching any batch files.
>
> You may NOT start implementation work while tests are in an unexplained failed state.

---

## Pre-Work: Run MCP Verification Queries

Run **all** of these via `postgres-local` MCP before writing any code. If any query returns unexpected results → **STOP and ask Tom**.

> **MCP Usage Rule**: The `postgres-local` MCP is for **read-only verification only**. Never use it to INSERT, UPDATE, or DELETE. If a query fails or returns an error → STOP and ask Tom before proceeding.

```sql
-- 1. Confirm job_expense_category rows exist with correct codes
SELECT code, name, is_default FROM public.job_expense_category ORDER BY code;
-- Expected: equipment (false), materials (true), permits (false)

-- 2. Confirm Customer model has mobile_phone column
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'customer' AND column_name = 'mobile_phone';
-- Expected: 1 row returned

-- 3. Find the mobile sync conflict / escalation table name
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
  AND (table_name LIKE '%sync_conflict%' OR table_name LIKE '%escalation%' OR table_name LIKE '%field_issue%')
ORDER BY table_name;
-- Record the exact table name returned — use it in A4

-- 4. Find the customer communication table name
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
  AND (table_name LIKE '%customer_comm%' OR table_name LIKE '%communication%')
ORDER BY table_name;
-- Record exact table name — use it in A2

-- 5. Verify current alembic head is at expected revision
SELECT version_num FROM public.alembic_version;

-- 6. Check owner role permissions (wildcard expected)
SELECT u.email, pr.code AS role_code, pr.permissions
FROM "user" u
JOIN tenant_user tu ON u.id = tu.user_id
JOIN tenant_user_role tur ON tu.id = tur.tenant_user_id
JOIN platform_role pr ON tur.role_id = pr.id
WHERE u.email = 'dev@pilot.local';
-- Expected: role_code='owner', permissions includes '*'
```

---

## Pre-Work: Read These Source Files

Use `read_file` on each of these before writing any code:

```
backend/core/permissions.py                        ← understand wildcard matching logic (A1)
backend/api/routes/communications.py               ← existing send endpoint + file structure (A2, A7)
backend/api/routes/dashboard.py                    ← recent-customer-messages endpoint handler (A3)
backend/api/routes/owner_escalations.py            ← existing route structure and imports (A4)
backend/api/routes/invoices.py lines 100–200       ← GET public invoice handler + POST pay handler (A5)
backend/api/routes/tenant_email_branding.py        ← PUT branding endpoint to change to PATCH (A6)
backend/api/routes/quotes.py _list_quotes_impl()   ← existing list implementation (A9)
backend/api/routes/catalog.py                      ← check if job_expense_category model imported (A8)
backend/api/schemas/schemas.py                     ← CustomerResponse, QuoteListItem, existing patterns (A10, A11)
backend/db_models_map.md                           ← confirm model names and table mappings
```

Also run:
```bash
# Find where CustomerResponse is defined
grep -rn "class CustomerResponse" backend/ --include="*.py"

# Find where QuoteListItem is defined
grep -rn "class QuoteListItem" backend/ --include="*.py"

# Find where SoftDeleteResponse may already exist
grep -rn "SoftDeleteResponse" backend/ --include="*.py"

# Locate the job_expense_category model
grep -rn "JobExpenseCategory\|job_expense_category" backend/app/models/ --include="*.py"
```

---

## Context: What This Batch Does

B17 Part A is the **unblocking batch** — it fixes broken API contracts and adds missing endpoints causing P0 failures. The web app's `/reports` page returns 422 on every call, the `/comms` page is 404, the dashboard widget is 403 for all owners, and the mobile owner tab 404s on field issues count. These must be fixed first because all other Phase 0.9 batches depend on correct API behavior.

**No Alembic migrations required.** All changes are Python code and Pydantic schema additions.

---

## Task A1 — Fix Wildcard Permission Bug in `core/permissions.py`

**File**: `backend/core/permissions.py`

Read the file first. Find the `has_permission()` function and identify why `has_permission(["*"], "communications.view")` returns `False`.

Common root cause: the wildcard check compares `"*"` only against the exact permission string without treating it as a catch-all. Fix so that `"*"` in the permissions list grants any permission.

**Expected behavior after fix**:
```python
assert has_permission(["*"], "communications.view") is True
assert has_permission(["*"], "invoices.view") is True
assert has_permission(["*"], "any.permission") is True
assert has_permission(["quotes.view"], "quotes.view") is True
assert has_permission(["quotes.*"], "quotes.create") is True
assert has_permission(["quotes.view"], "quotes.create") is False
assert has_permission([], "quotes.view") is False
```

**Add these as a unit test** in the appropriate test file for permissions (check `tests/domains/identity_access/` or `tests/` for existing permission tests before creating a new file).

> ⚠️ Fix this FIRST. Tasks A2–A11 all depend on RBAC working correctly for testing.

**Intermediate check after A1**:
```bash
python -m pytest -m unit -k "permission" --tb=short -q 2>&1 | tail -10
```

---

## Task A2 — Add `GET /api/v1/communications/recent`

**File**: `backend/api/routes/communications.py`

Read the file first. Add a new endpoint following the existing patterns in the file.

**Pydantic schemas to add** (in `api/schemas/schemas.py` or the appropriate schema file for this route — check what the existing communications endpoints use):

```python
class RecentCommunicationItem(BaseModel):
    communication_id: UUID
    customer_id: UUID
    customer_name: str
    rendered_message: str
    actual_channel: str
    status: str
    sent_at: datetime | None = None

class RecentCommunicationsResponse(BaseModel):
    items: list[RecentCommunicationItem]
    total: int
```

**Implementation**: Use the table name found in MCP query #4. JOIN to `Customer` for `customer.display_name` as `customer_name`. Filter by `tenant_id` on both tables (IDOR protection). Order by `sent_at DESC`. Offset pagination: `skip = (page - 1) * page_size`.

**Endpoint**:
```python
@router.get("/recent", response_model=RecentCommunicationsResponse, status_code=status.HTTP_200_OK)
def get_recent_communications(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user: AuthenticatedUser = Depends(require_permission("communications.view")),
    db: Session = Depends(get_db),
) -> RecentCommunicationsResponse:
    return _get_recent_communications_impl(page, page_size, db, current_user)
```

Add the `/test` mirror endpoint (unauthenticated, dev/QA only) using `TestUserContext` per the standard pattern in `backend/python-engr-std-prompt-inclusions.md` §11.

All new API errors must use RFC 7807 format. Example:
```python
raise HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail={
        "type": "https://errors.pilotfortrades.com/not-found",
        "title": "Resource not found",
        "status": 404,
        "detail": "No communications found for this tenant.",
    },
)
```

---

## Task A3 — Fix Owner 403 on `GET /api/v1/dashboard/widgets/recent-customer-messages`

**File**: `backend/api/routes/dashboard.py`

Read the file. After A1 fixes `has_permission()`, re-test this endpoint. If it still returns 403 after A1:

1. Identify the exact permission string the route requires
2. Verify `has_permission(["*"], "<that permission>")` returns `True` after A1
3. If the handler uses a non-standard permission check (not `require_permission()`), refactor it to use `require_permission()` consistently

If A1 fully resolves the 403, add a code comment noting that A1 was the root cause and no code change was needed here.

---

## Task A4 — Add `GET /api/v1/owner/field-issues/summary`

**File**: `backend/api/routes/owner_escalations.py`

Read the file first. Use the table name found in MCP query #3.

**Pydantic schema**:
```python
class FieldIssuesSummaryResponse(BaseModel):
    pending_count: int
```

Query the escalation/conflict table for records where `tenant_id = current_user.tenant_id` AND status is pending/unresolved. Confirm the exact column name for "pending" status using MCP before writing the WHERE clause:
```sql
SELECT column_name FROM information_schema.columns
WHERE table_name = '<escalation_table_from_query_3>';
```

Add the `/test` mirror endpoint using `TestUserContext`.

All new errors must use RFC 7807 format.

---

## Task A5 — Move Usage Tracking from GET to POST on Public Invoice

**File**: `backend/api/routes/invoices.py`

Read lines 100–200 of the file first (specifically the GET public invoice handler and POST pay handler).

**In the GET handler**: Remove `link.used_count += 1` and `link.last_used_at = datetime.now(UTC)` and the `db.commit()` that exists solely for those writes.

**In the POST `/pay` handler**: Verify that `used_count` and `last_used_at` are tracked here. If not, add:
```python
link.used_count = (link.used_count or 0) + 1
link.last_used_at = datetime.now(UTC)
```
Include these writes in the existing payment transaction commit — do NOT add a separate `db.commit()`.

> ⚠️ Verify POST handler tracking exists BEFORE removing from GET. Never have a period where neither handler tracks usage.

---

## Task A6 — Change `PUT /api/v1/settings/email-branding` → `PATCH`

**File**: `backend/api/routes/tenant_email_branding.py`

Read the file first. Find both the authenticated and test endpoints and change:
```python
@router.put("")       →    @router.patch("")
@router.put("/test")  →    @router.patch("/test")
```

No schema changes needed — `EmailBrandingUpdate` already uses all-Optional fields (correct for PATCH).

---

## Task A7 — Add `status_code=201` to `POST /api/v1/communications/send`

**File**: `backend/api/routes/communications.py`

Read the file first. Find the `/send` endpoint decorator and add `status_code=status.HTTP_201_CREATED`:
```python
@router.post("/send", status_code=status.HTTP_201_CREATED)
@router.post("/send/test", status_code=status.HTTP_201_CREATED)
```

---

## Task A8 — Add `GET /api/v1/job-expense-categories`

**File**: `backend/api/routes/catalog.py` (preferred if `JobExpenseCategory` model already imported) — otherwise create `backend/api/routes/job_expense_categories.py` and register in `backend/app/main.py`

Check imports first:
```bash
grep -n "JobExpenseCategory\|job_expense_category" backend/api/routes/catalog.py
```

**Pydantic schemas**:
```python
class JobExpenseCategoryItem(BaseModel):
    code: str
    name: str
    is_default: bool

class JobExpenseCategoriesResponse(BaseModel):
    categories: list[JobExpenseCategoryItem]
```

**Implementation**: Query `job_expense_category` where `tenant_id IS NULL OR tenant_id = current_user.tenant_id`. For rows with the same `code`, prefer tenant-specific over global. Order by `name ASC`.

Add the `/test` mirror endpoint using `TestUserContext`.

---

## Task A9 — Add `?status=` Filter + Denormalized Fields to `GET /api/v1/quotes/`

**File**: `backend/api/routes/quotes.py`

Read `_list_quotes_impl()` first. Extend `QuoteListItem` in the appropriate schema file:
```python
class QuoteListItem(BaseModel):
    id: UUID
    customer_id: UUID
    customer_name: str | None = None     # NEW — from Customer JOIN
    status_id: UUID
    status_code: str | None = None       # NEW — from QuoteStatus JOIN
    total_cents: int
    created_at: datetime
    expires_at: datetime | None = None
```

In `_list_quotes_impl()`:
1. Add optional `status: str | None = None` parameter
2. If provided, filter by `QuoteStatus.code == status` (JOIN required)
3. JOIN `Customer` to get `customer.display_name` as `customer_name` (tenant-scoped)
4. JOIN `QuoteStatus` to get `code` as `status_code`

Update the authenticated endpoint decorator:
```python
status: str | None = Query(None, description="Filter by quote status code (e.g. 'draft', 'sent')")
```

Also update test mirror endpoint to accept `status` param.

---

## Task A10 — Add `mobile_phone` to `CustomerResponse`

**File**: `backend/api/schemas/schemas.py` (or wherever `CustomerResponse` is defined — check grep output from Pre-Work)

Add field:
```python
class CustomerResponse(BaseModel):
    # ... existing fields (preserve all) ...
    mobile_phone: str | None = None    # NEW
```

Verify `_get_customer_impl()` and `_list_customers_impl()` populate this from the `Customer` model. Since `Customer.mobile_phone` already exists on the SQLModel, the ORM should populate it automatically when serializing — verify this assumption by checking `Customer` model attributes.

---

## Task A11 — Add `SoftDeleteResponse` + Apply to 5 DELETE Endpoints

**File**: `backend/api/schemas/schemas.py`

Check if `SoftDeleteResponse` already exists:
```bash
grep -n "SoftDeleteResponse" backend/api/schemas/schemas.py
```

If not, add:
```python
class SoftDeleteResponse(BaseModel):
    message: str
    id: UUID
```

Apply `response_model=SoftDeleteResponse` to these 5 endpoints and ensure each handler returns `{"message": "...", "id": str(record.id)}`:
- `DELETE /api/v1/customers/{customer_id}` in `customers.py`
- `DELETE /api/v1/addresses/{address_id}` in `addresses.py`
- `DELETE /api/v1/contacts/{contact_id}` in `contacts.py`
- `DELETE /api/v1/scheduling/tech-availability/{record_id}` in `scheduling.py`
- `DELETE /api/v1/scheduling/jobs/{job_id}/assignments/{assignment_id}` in `scheduling.py`

Read each route file before modifying — verify current return shape before changing.

---

## Test Requirements

Per `backend/tests/README-adding-tests.md`:

**Every new test file MUST:**
- Declare `pytestmark` with both domain marker and `pytest.mark.unit`:
  ```python
  pytestmark = [
      pytest.mark.domain_notifications_comms,   # for communications/recent endpoint
      pytest.mark.unit,
  ]
  ```
- Use the `client` fixture (never module-level `TestClient`)
- Use `test_tenant` and `test_user` fixtures (never hardcoded UUIDs)
- Scope assertions by inserted IDs — never `assert len(all_rows) == N`

**Domain folder mapping for this batch:**
- `GET /api/v1/communications/recent` → `tests/domains/notifications_comms/`
- `GET /api/v1/owner/field-issues/summary` → `tests/domains/mobile_offline/` (or `platform_infrastructure/` — check what makes sense for the table found)
- `GET /api/v1/job-expense-categories` → `tests/domains/catalog_pricing/`
- `has_permission()` fix → `tests/domains/identity_access/`
- Quotes list denormalization → `tests/domains/sales_quoting/`

**Minimum test coverage per new endpoint:**
1. Returns 200 with expected schema shape
2. Tenant isolation — data from another tenant does NOT appear in response
3. RBAC — unauthenticated request returns 401 or 403
4. Empty state — returns empty list when no data exists (use `second_tenant`)

**Autouse fixtures (run automatically — do not re-declare):**
- `mock_cognito_jwks` — patches AWS Cognito JWKS
- `mock_ai_services` — patches Ollama + Whisper
- `mock_entitlement_allowed` — bypasses subscription entitlement checks

---

## Regenerate OpenAPI

After all tasks and tests pass:

```bash
cd <repo>/backend
source .venv/bin/activate
python export_openapi_json.py
```

This generates **two files**:
- `backend/openapi.json` — consumed by `pnpm sync-api-types` to generate TypeScript types
- `backend/openapi_schema_map.md` — human-readable endpoint summary for the React Engineer

Verify new endpoints appear:
```bash
grep -A 3 "communications/recent" backend/openapi_schema_map.md
grep -A 3 "field-issues/summary" backend/openapi_schema_map.md
grep -A 3 "job-expense-categories" backend/openapi_schema_map.md
```

Also run the spot-checks:
```bash
python3 -c "
import json
spec = json.load(open('openapi.json'))
paths = spec['paths']

assert '/api/v1/communications/recent' in paths, 'MISSING: communications/recent'
assert '/api/v1/owner/field-issues/summary' in paths, 'MISSING: field-issues/summary'
assert '/api/v1/job-expense-categories' in paths, 'MISSING: job-expense-categories'

eb_methods = list(paths.get('/api/v1/settings/email-branding', {}).keys())
assert 'patch' in eb_methods, 'email-branding: must be PATCH not PUT'
assert 'put' not in eb_methods, 'email-branding: PUT must be removed'

print('All spot-checks passed ✅')
"
```

---

## Final Verification

### Phase 1 — Unit Tests Only (run after each task group during development)

```bash
cd <repo>/backend
source .venv/bin/activate

# Unit tests only — fast feedback loop
python -m pytest -m unit --tb=short -q 2>&1 | tail -10
```

Fix any unit failure — including failures that appear caused by code outside your batch — before proceeding.

### Phase 2 — Full Suite (run once, at the very end, before DoD sign-off)

```bash
cd <repo>/backend
source .venv/bin/activate

# Full suite
python -m pytest --tb=short -q 2>&1 | tail -10

# Domain-specific spot checks
python -m pytest tests/domains/notifications_comms/ -v 2>&1 | tail -20
python -m pytest tests/domains/catalog_pricing/ -k "expense_cat" -v 2>&1 | tail -10
python -m pytest tests/domains/identity_access/ -k "permission" -v 2>&1 | tail -10

echo "=== B17 PART A FINAL VERIFICATION COMPLETE ==="
```

> **Any failure in either phase must be fixed before the batch is declared done.** There is no "pre-existing failure" exception without explicit written confirmation from Tom.

---

## Definition of Done — B17 Part A

Update `dev-docs/analysis/pilot-app-pre-wkstm-3-prep-plan.md` §Phase 0.9 milestone checklist when each item is done:

- [ ] Pre-modification regression baseline captured (`X passed, Y failed`) using `pytest -m unit`
- [ ] Zero pre-existing unit failures confirmed before starting work (or confirmed with Tom)
- [ ] All MCP pre-work queries run — job_expense_category codes confirmed, mobile_phone column confirmed, escalation table name confirmed, communication table name confirmed
- [ ] All mandatory source files read before writing any code
- [ ] **A1**: `has_permission(["*"], "any.permission")` returns `True` — unit test added to `tests/domains/identity_access/`
- [ ] **A2**: `GET /api/v1/communications/recent?page=1&page_size=50` → 200 with `items` array; `/test` mirror endpoint added
- [ ] **A3**: `GET /api/v1/dashboard/widgets/recent-customer-messages` → 200 for owner (not 403)
- [ ] **A4**: `GET /api/v1/owner/field-issues/summary` → 200 with `{ "pending_count": N }`; `/test` mirror added
- [ ] **A5**: Two GET calls to `/api/v1/public/invoices/{token}` — `used_count` does NOT increment; one POST pay call — it DOES increment
- [ ] **A6**: `PATCH /api/v1/settings/email-branding` → 200; `PUT` → 405
- [ ] **A7**: `POST /api/v1/communications/send` → 201 (not 200)
- [ ] **A8**: `GET /api/v1/job-expense-categories` → 200 with `{ "categories": [...] }`; `/test` mirror added
- [ ] **A9**: `GET /api/v1/quotes/?status=draft` → only draft quotes; items include `status_code` and `customer_name`
- [ ] **A10**: `GET /api/v1/customers/{id}` response includes `mobile_phone` field
- [ ] **A11**: `DELETE /api/v1/customers/{id}` → `SoftDeleteResponse` shape; same for addresses, contacts, tech-availability, assignment
- [ ] All new API errors follow RFC 7807 Problem Details format
- [ ] `set_audit_context_sync()` called in every new mutation endpoint (A2, A4)
- [ ] All new test files use `pytestmark` with domain marker + `pytest.mark.unit`
- [ ] No module-level `TestClient` in any test file
- [ ] All new tests use `test_tenant` and `test_user` fixtures (no hardcoded UUIDs)
- [ ] `python export_openapi_json.py` run — `openapi.json` and `openapi_schema_map.md` updated
- [ ] All spot-check assertions in Regenerate OpenAPI section pass
- [ ] **Phase 1**: All unit tests pass (`pytest -m unit`) — zero failures
- [ ] **Phase 2**: Full test suite passes (`pytest`) — zero failures including integration
- [ ] Final test count (before → after) documented
- [ ] Completion Summary added to impl plan §Phase 0.9

---

## Completion Summary

After all Definition of Done items are complete, add a **Completion Summary** to `dev-docs/analysis/pilot-app-pre-wkstm-3-prep-plan.md` under Phase 0.9 — B17 using this format:

```markdown
### B17 Part A — API Contract Fixes + Missing Endpoints: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot Python Engineer
**Baseline**: X passed, Y failed
**Final**: X+N passed, Y failed (+N new tests)

#### What Was Accomplished

- Fixed wildcard permission bug in `core/permissions.py` — owners now correctly receive all permissions
- Added `GET /api/v1/communications/recent` — resolves comms page 404
- Fixed 403 on dashboard recent-customer-messages endpoint — [root cause]
- Added `GET /api/v1/owner/field-issues/summary` — resolves mobile owner tab 404
- Moved public invoice usage tracking from GET to POST `/pay` — resolves S1 HTTP violation
- Changed email-branding from PUT → PATCH — resolves S2 HTTP violation
- Added 201 to communications/send — resolves S2 HTTP violation
- Added `GET /api/v1/job-expense-categories` — enables mobile dynamic categories
- Added server-side status filter + customer_name + status_code to quotes list
- Added mobile_phone to CustomerResponse
- Added SoftDeleteResponse to 5 soft-delete DELETE endpoints

#### Files Changed / Created

| File | Action |
|---|---|
| `backend/core/permissions.py` | Updated — wildcard match fix |
| `backend/api/routes/communications.py` | Updated — /recent endpoint + 201 on /send |
| `backend/api/routes/dashboard.py` | Updated — 403 fix |
| `backend/api/routes/owner_escalations.py` | Updated — /summary endpoint |
| `backend/api/routes/invoices.py` | Updated — move usage tracking to POST |
| `backend/api/routes/tenant_email_branding.py` | Updated — PUT → PATCH |
| `backend/api/routes/quotes.py` | Updated — status filter + denormalized fields |
| `backend/api/routes/catalog.py` | Updated — job-expense-categories endpoint |
| `backend/api/schemas/schemas.py` | Updated — CustomerResponse, QuoteListItem, SoftDeleteResponse, new response schemas |
| ... | ... |

#### Tests Added

| Test File | Domain | Tests | All Pass |
|---|---|---|---|
| `tests/domains/identity_access/test_permissions_b17.py` | `domain_identity_access` | N | ✅ |
| `tests/domains/notifications_comms/test_recent_comms_b17.py` | `domain_notifications_comms` | N | ✅ |
| ... | ... | ... | ... |
```

---

## Handoff Instructions

When all acceptance criteria pass:

1. Run `python export_openapi_json.py` one final time
2. Commit with message: `feat(b17-be): API contract fixes + missing endpoints (B17 Part A)`
3. Notify React Engineer: **"B17 Part A complete. Run `cd frontend && pnpm sync-api-types` then proceed with `batch-b17-react-engr-prompt.md`."**
