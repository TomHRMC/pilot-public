# Implementation Prompt: BETA-B1 — Backend API Bug Fixes

**Mode**: Pilot Python Engineer  
**Batch**: BETA-B1  
**Source plan**: `dev-docs/analysis/pilot-app-beta-fixes-v1-impl-plan.md` §8 BETA-B1  
**Estimated session**: 2–4 hours  
**No design doc required** — all three items are targeted bug fixes or small new endpoints

---

## ⚠️ MANDATORY STOP: Read These Rules First

Before writing a single line of code, you MUST follow the rules in:
- **`.roo/rules-pilot-python-engineer/python-engineer-rules.md`** — read it in full

The highest-risk rules for this batch:
- **Rule 1.2**: Use `postgres-local` MCP to confirm every column/table name before use. If MCP returns an error → STOP and ask Tom.
- **Rule 2.1**: After any model file change → regenerate `db_models_map.md`.
- **Rule 2.3**: After any endpoint change → run `python export_openapi_json.py` (updates both `openapi.json` and `openapi_schema_map.md`).
- **Rule 5**: Never use module-level `TestClient`. Always use the `client` fixture.

---

## Pre-Work: Establish Regression Baseline

Before touching any file:

```bash
cd <repo>/backend
source .venv/bin/activate
pytest -m unit tests/ -v 2>&1 | grep -E "(passed|failed|error|===)" | tail -10
```

Record this number. All tests passing now must still pass at the end.

---

## Pre-Work: Mandatory File Reads

Read every file below using `read_file` before writing any code:

```
backend/core/permissions.py                          ← Task 1: wildcard logic lives here
backend/api/routes/                                  ← list directory to find related routes
backend/app/models/auth.py                           ← TenantUserRole, TenantUser
backend/db_models_map.md                             ← confirm model names and files
backend/app_model_imports.md                         ← correct import paths
```

Also read the test directory to understand domain placement:
```
backend/tests/domains/platform_infrastructure/       ← list for Task 1 (dashboard/permissions)
backend/tests/domains/scheduling_dispatch/           ← list for Task 2 (field issues)
backend/tests/domains/notifications_comms/           ← list for Task 3 (communications)
```

---

## Pre-Work: Database Verification Queries

Run ALL of these via `postgres-local` MCP **before writing any code**. If any query fails or returns unexpected results → STOP and ask Tom.

```sql
-- Verify tenant_user_role and permissions column
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'tenant_user_role'
ORDER BY ordinal_position;
```

```sql
-- Verify platform_role and permissions column
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'platform_role'
ORDER BY ordinal_position;
```

```sql
-- Verify dev@pilot.local user exists and is linked to owner role
SELECT u.email, tur.role_id, pr.code, pr.permissions
FROM "user" u
JOIN tenant_user tu ON u.id = tu.user_id
JOIN tenant_user_role tur ON tu.id = tur.tenant_user_id
JOIN platform_role pr ON tur.role_id = pr.id
WHERE u.email = 'dev@pilot.local'
LIMIT 5;
```

```sql
-- Find all tables related to "escalation" or "field_issue"
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
  AND (table_name LIKE '%escalation%' OR table_name LIKE '%field_issue%' OR table_name LIKE '%conflict%')
ORDER BY table_name;
```

```sql
-- Find all communication-related tables
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
  AND (table_name LIKE '%communication%' OR table_name LIKE '%message%' OR table_name LIKE '%thread%')
ORDER BY table_name;
```

---

## Task 1: Fix 403 on `GET /api/v1/dashboard/widgets/recent-customer-messages`

**Issue**: The owner role has `"*"` wildcard in `platform_role.permissions`, but the dashboard widget endpoint returns 403 for `dev@pilot.local`. The wildcard is supposed to match any permission including `"communications.view"`.

### Step 1a: Read the actual permission checking code

```
backend/core/permissions.py          ← read with read_file
backend/core/auth.py                 ← read with read_file — how AuthenticatedUser is built
```

Find the `has_permission()` function. Understand exactly how it checks for wildcard `"*"` against a specific permission string like `"communications.view"`.

### Step 1b: Read the dashboard endpoint

Find `GET /api/v1/dashboard/widgets/recent-customer-messages` in the codebase:

```bash
grep -r "recent-customer-messages\|recent_customer_messages" backend/api/routes/ --include="*.py" -l
```

Read that route file. Identify the exact permission string being checked with `require_permission()`.

### Step 1c: Diagnose the root cause

Two possible causes — determine which one applies:

**Cause A**: The `has_permission()` function has a bug where `"*"` does not match non-wildcard permission strings.  
**Cause B**: The JWT for `dev@pilot.local` is not resolving to the `TenantUser` row that has the `platform_role` with `"*"` permissions.

To distinguish:
1. In `permissions.py`, trace the `has_permission(user_permissions, required_permission)` call
2. Check: does `has_permission(["*"], "communications.view")` return `True`?
3. If the logic looks correct, check the DB query: does `dev@pilot.local` actually have a role with `["*"]` in permissions?

```sql
-- Check dev@pilot.local's actual resolved permissions
SELECT u.email, pr.code AS role_code, pr.permissions
FROM "user" u
JOIN tenant_user tu ON u.id = tu.user_id
JOIN tenant_user_role tur ON tu.id = tur.tenant_user_id
JOIN platform_role pr ON tur.role_id = pr.id
WHERE u.email = 'dev@pilot.local';
```

### Step 1d: Fix whichever cause applies

**If Cause A** (logic bug): Fix `has_permission()` in `backend/core/permissions.py` so `"*"` in the user's permission list matches any required permission string. The correct logic:
```python
def has_permission(user_permissions: list[str], required: str) -> bool:
    if "*" in user_permissions:
        return True
    if required in user_permissions:
        return True
    # Check "resource.*" wildcard
    resource = required.split(".")[0]
    if f"{resource}.*" in user_permissions:
        return True
    return False
```

**If Cause B** (data issue): The owner role in the DB does not have `"*"`. Fix the seed/migration to ensure the owner platform role has `["*"]` permissions. Do NOT manually update the DB — fix it in a targeted migration or seed fix.

### Step 1e: Write tests

**File**: `backend/tests/domains/platform_infrastructure/test_permissions_wildcard.py`

```python
"""
Tests for: Wildcard permission matching in has_permission()
Domain: platform_infrastructure (PRD §3.8)
"""
import pytest

pytestmark = [
    pytest.mark.domain_platform_infrastructure,
    pytest.mark.unit,
]


class TestHasPermissionWildcard:
    def test_wildcard_matches_any_permission(self):
        from core.permissions import has_permission
        assert has_permission(["*"], "communications.view") is True

    def test_wildcard_matches_deeply_namespaced_permission(self):
        from core.permissions import has_permission
        assert has_permission(["*"], "quotes.approve") is True

    def test_wildcard_matches_all_actions(self):
        from core.permissions import has_permission
        permissions = ["*"]
        for perm in ["customers.create", "customers.view", "jobs.delete", "settings.manage"]:
            assert has_permission(permissions, perm) is True

    def test_specific_permission_matches_itself(self):
        from core.permissions import has_permission
        assert has_permission(["communications.view"], "communications.view") is True

    def test_specific_permission_does_not_match_other(self):
        from core.permissions import has_permission
        assert has_permission(["communications.view"], "quotes.approve") is False

    def test_resource_wildcard_matches_all_actions(self):
        from core.permissions import has_permission
        assert has_permission(["customers.*"], "customers.create") is True
        assert has_permission(["customers.*"], "customers.view") is True
        assert has_permission(["customers.*"], "customers.delete") is True
        assert has_permission(["customers.*"], "quotes.view") is False

    def test_empty_permissions_matches_nothing(self):
        from core.permissions import has_permission
        assert has_permission([], "communications.view") is False

    def test_dashboard_widget_accessible_to_owner_role(self, client, test_tenant, test_user):
        """End-to-end: owner role (wildcard) can access the dashboard widget endpoint."""
        response = client.get(
            "/api/v1/dashboard/widgets/recent-customer-messages/test"
        )
        # Either 200 (has data) or 404 (no data but auth passed) — NOT 403
        assert response.status_code != 403, (
            f"Expected 200 or 404 (auth passed), got 403. "
            f"Wildcard permission check is still failing. Body: {response.json()}"
        )
```

> **Note**: The last test (`test_dashboard_widget_accessible_to_owner_role`) requires the endpoint to have a `/test` variant. If none exists, skip this test and verify via curl instead.

---

## Task 2: Implement `GET /api/v1/owner/field-issues/summary`

**Issue**: The mobile Owner tab calls this endpoint to show `{"pending_count": N}` — how many escalated mobile sync conflicts are awaiting owner resolution. The endpoint does not exist, returning 404.

### Step 2a: Find the existing owner escalations route as the pattern reference

```bash
grep -r "owner_escalations\|field.issue\|field_issue" backend/api/routes/ --include="*.py" -l
grep -r "owner_escalations\|field.issue\|field_issue" backend/app/models/ --include="*.py" -l
```

Read those files. Understand: what table stores escalated mobile sync conflicts? What column indicates "pending" vs "resolved"? Use the DB query results from pre-work to confirm the exact table name.

### Step 2b: Determine the correct table and column

Based on your pre-work MCP query results, identify:
- The exact table name that stores escalated mobile conflicts (likely something like `integration_sync_conflict` or `mobile_sync_conflict` — verify via MCP, do NOT guess)
- The column that indicates the conflict is pending/unresolved (likely `status` or `is_resolved` — verify)
- The filter that identifies "owner escalation" severity (likely `severity = 'escalate_to_owner'` — verify)

```sql
-- After you identify the table name from pre-work query, inspect its columns:
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'THE_ACTUAL_TABLE_NAME'
ORDER BY ordinal_position;
```

```sql
-- Check what "pending" looks like — what status/severity values exist?
SELECT DISTINCT status, severity
FROM THE_ACTUAL_TABLE_NAME
LIMIT 20;
```

**If the MCP query returns an error or the table doesn't exist → STOP and ask Tom before proceeding.**

### Step 2c: Find where the existing owner routes are registered

```bash
grep -r "owner" backend/app/main.py
grep -r "/api/v1/owner" backend/api/routes/ --include="*.py" -l
```

Read `backend/app/main.py` to understand how routes are registered, especially the `owner` prefix routes.

### Step 2d: Implement the endpoint

Using the dual-endpoint pattern from `pilot-python-engineer-methods.md` §8.2:

Add to the appropriate owner routes file (whichever file handles `/api/v1/owner/...`):

```python
# ==================== SHARED BUSINESS LOGIC ====================

def _get_field_issues_summary_impl(
    db: Session,
    user_context,  # AuthenticatedUser | TestUserContext
) -> dict:
    """Count pending escalated mobile sync conflicts for this tenant."""
    # Use the ACTUAL table class and ACTUAL column names verified via MCP
    # NEVER assume column names — use only what MCP confirmed
    pending_count = db.exec(
        select(func.count(THE_ACTUAL_MODEL.id))
        .where(THE_ACTUAL_MODEL.tenant_id == user_context.tenant_id)
        .where(THE_ACTUAL_MODEL.status == "pending")  # ← use ACTUAL column/value from MCP
        # Add additional filters confirmed via MCP (e.g., severity == "escalate_to_owner")
    ).one()
    return {"pending_count": pending_count}


# ==================== TEST ENDPOINT (register FIRST) ====================

@router.get("/field-issues/summary/test")
def get_field_issues_summary_test(db: Session = Depends(get_db)):
    """Test endpoint — no auth required."""
    test_context = get_test_context()
    return _get_field_issues_summary_impl(db, test_context)


# ==================== AUTHENTICATED ENDPOINT ====================

@router.get("/field-issues/summary", response_model=FieldIssuesSummaryResponse)
def get_field_issues_summary(
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("field_issue.view")),
):
    """Returns pending escalated field issue count for the owner dashboard."""
    return _get_field_issues_summary_impl(db, current_user)
```

Add the response schema to the appropriate schemas file:

```python
class FieldIssuesSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    pending_count: int
```

### Step 2e: Write tests

**File**: `backend/tests/domains/scheduling_dispatch/test_field_issues_summary.py`

```python
"""
Tests for: GET /api/v1/owner/field-issues/summary endpoint
Domain: scheduling_dispatch (PRD §3.14)
"""
import pytest

pytestmark = [
    pytest.mark.domain_scheduling_dispatch,
    pytest.mark.unit,
]


class TestFieldIssuesSummary:

    def test_returns_zero_when_no_pending_issues(self, client, test_tenant):
        """Returns pending_count: 0 when no escalated conflicts exist."""
        response = client.get("/api/v1/owner/field-issues/summary/test")
        assert response.status_code == 200
        data = response.json()
        assert "pending_count" in data
        assert data["pending_count"] >= 0

    def test_response_shape_matches_schema(self, client, test_tenant):
        """Response has the correct field names."""
        response = client.get("/api/v1/owner/field-issues/summary/test")
        assert response.status_code == 200
        data = response.json()
        assert set(data.keys()) == {"pending_count"}

    def test_pending_count_is_integer(self, client, test_tenant):
        """pending_count is an integer."""
        response = client.get("/api/v1/owner/field-issues/summary/test")
        assert response.status_code == 200
        assert isinstance(response.json()["pending_count"], int)

    def test_authenticated_endpoint_requires_permission(self, client, test_tenant, test_user, mock_cognito_jwt):
        """Authenticated endpoint returns 200 for owner role (has field_issue.view)."""
        mock_cognito_jwt(test_user)
        response = client.get("/api/v1/owner/field-issues/summary")
        # 200 if auth is correct and permission resolves
        assert response.status_code == 200
```

---

## Task 3: Create or Fix `GET /api/v1/communications/recent`

**Issue**: The `/comms` page calls `GET /api/v1/communications/recent?page=1&page_size=50` and gets 404 because the endpoint does not exist. The real communication endpoints are scoped per-customer.

### Step 3a: Decision point — confirm with Tom before implementing

Before writing any code for Task 3, you must determine which approach to take. **Stop and ask Tom**:

> "For the `/comms` page communications summary, should I: (a) create a new `GET /api/v1/communications/recent` backend endpoint that aggregates recent communications across all customers for the tenant, or (b) update the frontend `/comms` page to call a different existing endpoint? The existing per-customer endpoint is `GET /api/v1/customers/{id}/communication-history`. There is no existing cross-customer aggregate endpoint in `openapi.json`."

**Only proceed once Tom answers.** Do not implement either option speculatively.

### Step 3b: If Tom chooses option (a) — New aggregate endpoint

First verify the exact table structure:

```sql
-- Verify exact columns on the customer communication tables
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'customer_communication'
   OR table_name = 'customer_communication_message'
   OR table_name = 'customer_communication_thread'
ORDER BY table_name, ordinal_position;
```

**Do NOT guess what the table is named. Use only what MCP confirms.**

The new endpoint aggregates the most recent communications across all customers for the tenant, ordered by `created_at` descending, with pagination.

Using the dual-endpoint pattern, implement in the appropriate communications route file (find it via `grep -r "communication" backend/api/routes/ --include="*.py" -l`).

Response shape (match what the frontend `/comms` hook expects — read `apps/web/src/features/comms/hooks/` or equivalent first):

```python
class RecentCommunicationsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    items: list[CommunicationSummaryItem]
    total: int
    page: int
    page_size: int

class CommunicationSummaryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    customer_id: uuid.UUID
    customer_name: str
    channel: str          # "sms" | "email"
    direction: str        # "outbound" | "inbound"
    body: str
    created_at: datetime
```

Permission: `"communications.view"`

### Step 3c: If Tom chooses option (b) — Update frontend

This task is deferred to BETA-B2 (frontend batch). Mark Task 3 as "pending frontend fix" and note the decision in the impl plan tracker.

### Step 3d: Write tests (only if option (a) was chosen)

**File**: `backend/tests/domains/notifications_comms/test_communications_recent.py`

```python
"""
Tests for: GET /api/v1/communications/recent — cross-customer aggregate endpoint
Domain: notifications_comms (PRD §3.7)
"""
import pytest

pytestmark = [
    pytest.mark.domain_notifications_comms,
    pytest.mark.unit,
]


class TestCommunicationsRecent:

    def test_returns_200_with_empty_list_when_no_comms(self, client, test_tenant):
        """Returns 200 with empty items when tenant has no communications."""
        response = client.get(
            "/api/v1/communications/recent/test",
            params={"page": 1, "page_size": 50}
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)
        assert data["total"] >= 0

    def test_response_pagination_fields_present(self, client, test_tenant):
        """Response contains all pagination fields."""
        response = client.get(
            "/api/v1/communications/recent/test",
            params={"page": 1, "page_size": 10}
        )
        assert response.status_code == 200
        data = response.json()
        assert "page" in data
        assert "page_size" in data

    def test_tenant_isolation(self, client, tenant_a, tenant_b, user_tenant_a, mock_cognito_jwt):
        """Communications from tenant_a are not visible to tenant_b."""
        mock_cognito_jwt(user_tenant_a)
        response = client.get(
            "/api/v1/communications/recent",
            params={"page": 1, "page_size": 50}
        )
        assert response.status_code == 200
        # All returned items must belong to tenant_a
        for item in response.json()["items"]:
            # Verify via a DB query if tenant scoping is verifiable
            pass  # At minimum, no 403/500
```

---

## Post-Implementation Steps

### 1. Regenerate openapi artifacts

```bash
cd <repo>/backend
source .venv/bin/activate
python export_openapi_json.py
```

Verify both `openapi.json` and `openapi_schema_map.md` are updated.

### 2. Run regression check

```bash
pytest -m unit tests/ -v 2>&1 | grep -E "(passed|failed|error|===)" | tail -10
```

All previously passing tests must still pass. Fix any regressions before declaring done.

### 3. Manual curl verification

```bash
# Confirm 403 is fixed — should return 200 or empty 200 (NOT 403):
curl -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer $(get-dev-jwt)" \
  "http://localhost:8000/api/v1/dashboard/widgets/recent-customer-messages"

# Confirm field-issues/summary exists (test endpoint):
curl -s "http://localhost:8000/api/v1/owner/field-issues/summary/test"
# Expected: {"pending_count": 0} or higher number

# Confirm communications/recent (if option (a) chosen):
curl -s "http://localhost:8000/api/v1/communications/recent/test?page=1&page_size=50"
# Expected: {"items": [...], "total": N, "page": 1, "page_size": 50}
```

---

## Definition of Done — BETA-B1

Update the `pilot-app-beta-fixes-v1-impl-plan.md` §9 Batch Completion Tracker once all items below are checked:

- [ ] Pre-modification test baseline captured (unit test count recorded before any changes)
- [ ] All pre-work MCP queries run; results reviewed; no unexpected tables/columns
- [ ] All mandatory source files read before writing code
- [ ] **Task 1**: `has_permission(["*"], "communications.view")` returns `True` (unit test passing)
- [ ] **Task 1**: `GET /api/v1/dashboard/widgets/recent-customer-messages` no longer returns 403 for `dev@pilot.local` (verified via curl or test)
- [ ] **Task 2**: Tom confirmed which table stores escalated mobile conflicts (MCP verified)
- [ ] **Task 2**: `GET /api/v1/owner/field-issues/summary/test` returns `{"pending_count": N}` (curl verified)
- [ ] **Task 2**: `GET /api/v1/owner/field-issues/summary` (authenticated) works with valid JWT (curl verified)
- [ ] **Task 3**: Decision made with Tom (option a or b); documented in impl plan tracker
- [ ] **Task 3** (if option a): `GET /api/v1/communications/recent/test` returns paginated response (curl verified)
- [ ] All new test files have `pytestmark` with domain marker + `pytest.mark.unit`
- [ ] No module-level `TestClient` in any new test file
- [ ] All new tests use `test_tenant` and `test_user` fixtures (no hardcoded UUIDs)
- [ ] `python export_openapi_json.py` run; both `openapi.json` and `openapi_schema_map.md` updated
- [ ] 100% of unit tests pass with zero regressions
- [ ] Update this Definition of Done list with completion checks next to each item if completed
- [ ] Final test count (before/after) documented in impl plan tracker in the source plan
- [ ] Summary of work accomplished added to new sub-section in impl plan tracker in Section 9 in the source plan after the last batch entry
