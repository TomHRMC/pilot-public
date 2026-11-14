# Adding Tests to the Pilot Backend Test Suite

**Version**: 1.3
**Date**: June 1, 2026
**Audience**: AI agents and engineers adding, updating, or debugging backend tests

---

## Quick Rules

1. **New tests always go in an existing `tests/domains/<domain>/` folder** — never in a new `batch_*` folder and never in a new domain folder without explicit approval
2. **File naming**: `test_<feature_or_entity>_<action>.py` (e.g., `test_quote_approval_webhook.py`)
3. **Use the root `conftest.py` fixtures** — do not re-declare `db_session`, `client`, or auth mocks in individual test files
4. **Always declare `pytestmark`** at the top of every new test file with at least one domain marker and the correct test-type marker
5. **Never declare a module-level `TestClient`** — this is the most critical rule (see [The Module-Level TestClient Anti-Pattern](#the-module-level-testclient-anti-pattern))
6. **Never count all rows for a tenant in an assertion** — use ID-scoped assertions (see [Seed Data Coexistence Rules](#seed-data-coexistence-rules))
7. **Never use deterministic UUIDs `...0001` through `...0004`** in test fixtures — those are permanently reserved (see [Reserved UUIDs](#reserved-uuids))
8. **Never insert open-ended temporal ranges for seeded tenants** — use past CLOSED ranges (see [GiST Temporal Conflicts](#gist-temporal-conflicts))

---

## Where to Put New Tests

### Rule: Use an EXISTING `tests/domains/<domain>/` folder

All tests written from May 2026 forward go in one of the 16 existing domain directories:

```
backend/tests/domains/
  audit_compliance/        PRD §3.1 — Audit logs, deletion pathways, S3 archive
  catalog_pricing/         PRD §3.2 — Pricebook, supplier prices, labor rates
  crm/                     PRD §3.3 — Customers, sites, contacts
  field_operations/        PRD §3.4 — Jobs, change orders, LOTO, ETC, GPS
  identity_access/         PRD §3.5 — RBAC, MFA, sessions, tenant signup, onboarding
  invoicing_billing/       PRD §3.6 — Invoices, Stripe, public links, dunning
  notifications_comms/     PRD §3.7 — Notification outbox, SMS, push, preference matrix
  platform_infrastructure/ PRD §3.8 — Settings resolver, dashboard, reports, webhooks
  quickbooks/              PRD §3.9 — QB OAuth, sync, conflict resolution, invoice push
  sales_quoting/           PRD §3.10 — Quotes, discounts, pending edits, templates
  subscriptions_usage/     PRD §3.11 — Subscription tiers, entitlements, Stripe lifecycle
  tax_calculation/         PRD §3.12 — Tax rate versions, taxability propagation
  voice_ai/                PRD §3.13 — Voice intents, conversation sessions, multi-turn
  scheduling_dispatch/     PRD §3.14 — Dispatch board, assignments, conflict detection
  mobile_offline/          PRD §3.15 — Offline sync, photo upload, dedup, auth expiry
  help_support/            PRD §3.16 — Help chat, RAG corpus, feedback, HNSW index
```

### IMPORTANT: Do NOT Create New Directories

- ❌ Do not create a new `tests/domains/<new_name>/` directory — all 16 MVP domains already exist
- ❌ Do not create new `batch_*`, `phase_*`, or any other top-level test subdirectory
- If you believe a feature does not fit into any of the 16 existing domains, **stop and ask the engineer** before creating a new folder. Do not proceed unilaterally.
- If a new domain is approved and added in the future, it will be listed in this README with its corresponding PRD section reference

### Do NOT Modify Historical Batch/Phase Folders (organizationally)

The `batch_b*`, `batch_tp_b*`, `batch_mkt_*`, `batch_1*`, and `phase_*` folders are **organizationally read-only**:
- Do not add new test files to them
- Do not move or rename files within them (preserves git history)
- **Exception**: If fixing a confirmed bug in an existing legacy test file (e.g., the module-level `TestClient` anti-pattern), edit that file in-place with a clear docstring noting the fix
- For all net-new feature tests, always use `tests/domains/`

---

## `__init__.py` Files

- All `tests/domains/<domain>/` subdirectories have `__init__.py` files ✅
- Legacy `batch_*` and `phase_*` folders have **inconsistent** `__init__.py` coverage (some have it, some don't — this is a known technical debt item)
- When adding a new test file to `tests/domains/<domain>/`, the `__init__.py` is already present — do not remove it
- Do NOT add `__init__.py` to legacy batch/phase folders that don't already have one (risk of breaking existing imports)

---

## The Module-Level TestClient Anti-Pattern

**This is the most critical mistake to avoid.** It causes permanent data accumulation in the dev database and is the root cause of the 7,850 test-stub customer/job/site records found in `pilot_dev` as of May 2026.

### What the anti-pattern looks like

```python
# ❌ WRONG — module-level TestClient, bypasses the rollback fixture entirely
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)   # ← this line is the bug

class TestMyFeature:
    def test_something(self):
        resp = client.post("/api/v1/customers/test", json={...})
        # ↑ This call commits permanently to pilot_dev — no rollback happens
```

### Why it causes permanent DB writes

The `conftest.py` `client` fixture overrides `get_db` with the rollback-wrapped `db_session`:

```python
@pytest.fixture(scope="function")
def db_session(db_engine):
    connection = db_engine.connect()
    transaction = connection.begin()   # ← wrapping transaction
    session = Session(bind=connection)
    yield session
    transaction.rollback()            # ← EVERY DB write in this test is undone
    connection.close()

@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        yield db_session               # ← FastAPI uses this session, not the real one
    app.dependency_overrides[get_db] = override_get_db
    ...
```

A module-level `TestClient(app)` has **no `dependency_overrides`**. FastAPI uses the real `get_db` dependency, which opens a committed session. Every API call permanently writes to the database and is never rolled back.

### The `/test` endpoint trap

The 128 `/test` endpoints (`POST /api/v1/customers/test`, `POST /api/v1/jobs/test`, etc.) are designed for seeding test data. They bypass JWT authentication, which makes them convenient — but **they still commit to the real database if called via a module-level `TestClient`**.

A helper function like this inside a test file will permanently write 1 customer + 1 site + 1 job per call, per test run:

```python
# ❌ WRONG — called from a module-level TestClient context
def _create_test_job() -> str:
    cust = client.post("/api/v1/customers/test", json={...})   # commits to pilot_dev
    site = client.post("/api/v1/sites/test", json={...})       # commits to pilot_dev
    job  = client.post("/api/v1/jobs/test", json={...})        # commits to pilot_dev
    return job.json()["id"]
```

Run a test suite with 30 test methods, each calling this helper, across multiple development sessions → thousands of orphaned records in `pilot_dev`.

### The correct pattern

```python
# ✅ CORRECT — always use the conftest client fixture
import pytest
from fastapi.testclient import TestClient  # only import, no module-level instantiation

class TestMyFeature:
    def test_something(self, client):   # ← client fixture injected here
        resp = client.post("/api/v1/customers/test", json={...})
        # ↑ This call uses db_session (rollback-wrapped) — no permanent writes

    def test_needs_a_job(self, client, db_session):
        # Create a job first, then test something about it
        cust = client.post("/api/v1/customers/test", json={...})
        site = client.post("/api/v1/sites/test", json={"customer_id": cust.json()["id"]})
        job  = client.post("/api/v1/jobs/test", json={"customer_id": cust.json()["id"], "site_id": site.json()["id"]})
        # All of the above are rolled back after this test completes
        assert job.status_code == 201
```

### For helper functions that need to create entities

Pass `client` as an explicit parameter to the helper — never rely on a module-level variable:

```python
# ✅ CORRECT — helper accepts client as parameter
def _create_test_job(client) -> str:    # ← explicit parameter
    cust = client.post("/api/v1/customers/test", json={"display_name": "Test", "type": "person"})
    assert cust.status_code == 201
    site = client.post("/api/v1/sites/test", json={"customer_id": cust.json()["id"]})
    assert site.status_code == 201
    job  = client.post("/api/v1/jobs/test", json={"customer_id": cust.json()["id"], "site_id": site.json()["id"]})
    assert job.status_code == 201
    return job.json()["id"]

class TestScheduling:
    def test_assign_tech(self, client):    # ← fixture injected
        job_id = _create_test_job(client)  # ← fixture passed through
        resp = client.post(f"/api/v1/scheduling/jobs/{job_id}/assignments/test", json={...})
        assert resp.status_code == 201
```

### Detecting the anti-pattern in legacy files

Search for this pattern to find files that need fixing:

```bash
grep -r "^client = TestClient" backend/tests/
grep -r "^client = TestClient" backend/tests/batch_*/
```

If you find a match, the file must be refactored to pass `client` as a fixture parameter before the next test run — otherwise the accumulation continues.

---

## Minimum Viable Test File Template

```python
"""
Tests for: <brief description of what is being tested>
Domain: <domain name> (PRD §3.X)
"""
import uuid
import pytest

# REQUIRED: At least one domain marker (see full list below)
# REQUIRED: pytest.mark.unit OR pytest.mark.integration (not both)
# OPTIONAL: Service-specific markers if this test calls external APIs
pytestmark = [
    pytest.mark.domain_sales_quoting,  # change to your domain
    pytest.mark.unit,                  # or pytest.mark.integration for real external calls
]


class TestQuoteApprovalWebhook:
    """Tests for the quote approval webhook handler."""

    def test_webhook_sets_status_to_approved(self, client, db_session, test_tenant, test_user):
        """Webhook POST with event=approved transitions quote status correctly."""
        # Arrange
        # ... set up data using db_session and fixtures from conftest.py ...

        # Act
        response = client.post(
            "/api/v1/quotes/<id>/webhook",
            json={"event": "approved"},
            headers={"Authorization": "Bearer mock_token"},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "approved"

    def test_webhook_returns_404_for_unknown_quote(self, client, test_tenant):
        """Webhook for non-existent quote returns RFC 7807 404."""
        response = client.post(
            f"/api/v1/quotes/{uuid.uuid4()}/webhook",
            json={"event": "approved"},
            headers={"Authorization": "Bearer mock_token"},
        )
        assert response.status_code == 404
        assert response.json()["type"].startswith("https://")  # RFC 7807
```

---

## Key Fixtures Available from `conftest.py`

You do **not** need to import these — they are automatically available in all test functions via pytest's fixture injection.

### Infrastructure (always required)

| Fixture | Type | What It Gives You |
|---|---|---|
| `db_session` | `sqlmodel.Session` | Transaction-wrapped PostgreSQL session; **auto-rolls back after each test** — no data persists |
| `client` | `fastapi.testclient.TestClient` | FastAPI test client with `get_db` overridden to use `db_session` |

### Authentication

| Fixture | How to Use |
|---|---|
| `mock_cognito_jwt_verify` | Patches `verify_cognito_jwt` globally — returns `{"sub": "00000000-0000-0000-0000-000000000002", "email": "dev@pilot.local"}` |
| `mock_jwt_for_user` | Callable: `token = mock_jwt_for_user(user.email)` → returns a `"Bearer mock_token_<uuid>"` string |
| `mock_cognito_jwt` | Callable: `mock_cognito_jwt(user_obj)` → patches JWT AND injects `Authorization` header into the test client automatically |

### Tenant & User Context

| Fixture | What It Creates |
|---|---|
| `test_tenant` | Canonical test tenant (`id = 00000000-0000-0000-0000-000000000001`) — used with unauthenticated test endpoints |
| `test_user` | Canonical test user (`id = 00000000-0000-0000-0000-000000000002`, `email = dev@pilot.local`) |
| `tenant_a` / `tenant_b` | Two fully isolated tenants for cross-tenant IDOR/security tests |
| `user_tenant_a` / `user_tenant_b` | Users linked as `owner` to `tenant_a` / `tenant_b` |
| `second_tenant` | A third tenant for additional isolation tests — **use this for "empty state" tests** |

### Domain Entity Fixtures

| Fixture | What It Creates |
|---|---|
| `test_customer` | `Customer` (type: person) in `test_tenant` |
| `test_site` | `Site` linked to `test_customer` |
| `test_contact` | `Contact` linked to `test_customer` |
| `test_job` | `Job` in draft status in `tenant_a` |
| `test_quote_status` | `QuoteStatus` (code: draft) |
| `test_quote_version` | `Quote` + child `QuoteVersion` with empty snapshot |
| `test_invoice_status` | `InvoiceStatus` (code: draft) |
| `test_supplier` | `Supplier` |
| `test_notification_outbox` | `NotificationOutbox` with required FK chain |
| `test_notification_event` | `NotificationEvent` |
| `test_webhook_endpoint` / `test_webhook_event` | Webhook infrastructure |
| `test_app_service` | `AppService` (QuickBooks provider) |
| `test_qco_line_type` | `QcoLineType` (material) |
| `test_platform_role_staff` / `test_platform_role_superadmin` | `PlatformRole` rows for platform admin tests |
| `utc_now` | `datetime.now(UTC)` — timezone-aware datetime |
| `aware_datetime` | Factory: `aware_datetime(2026, 12, 31)` → timezone-aware |

---

## Autouse Fixtures (Applied to Every Test Automatically)

These run without you declaring them:

### `mock_cognito_jwks` (autouse)
Patches `core.auth.get_jwks` with a dummy RSA JWKS object. AWS Cognito is never called.

### `mock_entitlement_allowed` (autouse)
Patches `services.entitlement_service.get_cached_entitlement` to always return `is_allowed=True`. This means subscription tier checks are bypassed in all tests by default.

**To test actual entitlement enforcement**, opt out with:
```python
@pytest.mark.skip_mock_entitlement_allowed
def test_feature_blocked_without_subscription(self, client, db_session):
    # entitlement check is now real — will return 402 if no active subscription
    ...
```

---

## Database Rules

- **PostgreSQL only** — the test suite requires a live PostgreSQL instance. SQLite cannot support `JSONB`, `CITEXT`, and `INET` column types.
- **Default connection**: `postgresql://pilot_user:CHANGE_ME_LOCAL_DB_PW@localhost:5432/pilot_dev`
- **Override**: set `DATABASE_URL` env var
- **Migration state required**: Before running tests, the DB must have `alembic upgrade head` applied. Fixtures that create Tenant rows require the `SubscriptionTier` trial tier to be seeded by migrations. If you see `RuntimeError: Trial subscription tier not seeded`, run `alembic upgrade head`.
- **Transaction rollback**: Every test that uses the `client` or `db_session` fixture wraps its DB work in a transaction that is rolled back after the test completes. Tests are fully isolated — **no manual cleanup code is needed**.
- **`requires_db` marker** is for tests in `tests/integration/` that bypass the rollback fixture and require a persistent live DB connection. Do NOT use it for regular domain tests — they already use the DB via `db_session`.

### Verifying DB isolation during debugging

If you suspect a test is leaking data to the real DB, use this SQL to check before and after a test run:

```sql
-- Run BEFORE the test suite
SELECT COUNT(*) FROM public.customer WHERE display_name LIKE '%Test%';
SELECT COUNT(*) FROM public.job;
SELECT COUNT(*) FROM public.site;
```

If counts increase after the test run, the test is using a module-level `TestClient` instead of the fixture `client`. See [The Module-Level TestClient Anti-Pattern](#the-module-level-testclient-anti-pattern).

The postgres-local MCP server is available in Roo Code and can run these queries directly. Reference [`dev-docs/db-design/postgres-mcp-guide.md`](../../dev-docs/db-design/postgres-mcp-guide.md) for query syntax.

---

## Seed Data Coexistence Rules

**Context**: From June 2026 forward, the dev/test database contains **persistent seed data** from `seed_test_tenant.py`. This data lives in the same DB used by the pytest suite. Tests must be written to coexist safely with it.

### Reserved UUIDs

The following UUIDs are **permanently reserved** for the seed infrastructure (`seed_test_tenant.py`). **Never use these as deterministic IDs in test fixtures** — doing so causes `UniqueViolation` PK errors.

| UUID | Owner |
|---|---|
| `00000000-0000-0000-0000-000000000001` | Test Tenant |
| `00000000-0000-0000-0000-000000000002` | Owner user (`dev@pilot.local`) |
| `00000000-0000-0000-0000-000000000003` | Technician user (`tech@pilot.local`) |
| `00000000-0000-0000-0000-000000000004` | Office Staff user (`office@pilot.local`) |

**Rule**: All test fixtures that create additional users, tenants, or any entity with a fixed UUID must use `uuid.uuid4()`, not a hardcoded deterministic value.

```python
# ❌ WRONG — conflicts with seeded office@pilot.local user
user = User(id=uuid.UUID("00000000-0000-0000-0000-000000000004"), email="test@example.com")

# ✅ CORRECT — generates a fresh UUID that won't collide
user = User(id=uuid.uuid4(), email="test@example.com")
```

### Canonical Test User Email

The `test_user` fixture and `mock_cognito_jwt_verify` both use **`dev@pilot.local`** (not `test@pilot.local`). This was changed when the seed system was renamed from the AevoFab era. Any test that hardcodes the old email will fail authentication.

```python
# ❌ WRONG — old email, auth lookup fails → 404 on authenticated routes
mock_verify.return_value = {"sub": "...", "email": "test@pilot.local"}

# ✅ CORRECT
mock_verify.return_value = {"sub": "...", "email": "dev@pilot.local"}
```

### GiST Temporal Conflicts

Tables with GiST exclusion constraints (`tenant_markup_version`, `labor_rate_version`) enforce that no two rows for the same `(tenant_id, category_code/skill_level_code)` can have overlapping `valid_period` ranges.

The seed data inserts **open-ended rows** for `TEST_TENANT_ID` (`...0001`):
- `tenant_markup_version`: `materials` → `[2026-06-01, NULL)` (open-ended)
- `labor_rate_version`: `master`, `journeyman`, `apprentice` → `[2026-06-01, NULL)` (open-ended)

**Any test that inserts a row with an overlapping range for `TEST_TENANT_ID` will fail with a GiST ExclusionViolation.**

```python
# ❌ WRONG — [2020-01-01, NULL) overlaps with seeded [2026-06-01, NULL) for TEST_TENANT_ID
markup = TenantMarkupVersion(
    tenant_id=test_tenant.id,  # this is TEST_TENANT_ID = ...0001
    job_expense_category_code="materials",
    valid_period=DateTimeTZRange(lower=datetime(2020, 1, 1, tzinfo=UTC), upper=None),
)

# ✅ OPTION A — use a past CLOSED range that doesn't overlap with current seed rows
markup = TenantMarkupVersion(
    tenant_id=test_tenant.id,
    job_expense_category_code="materials",
    valid_period=DateTimeTZRange(
        lower=datetime(2020, 1, 1, tzinfo=UTC),
        upper=datetime(2020, 12, 31, 23, 59, 59, tzinfo=UTC),  # ← closed upper bound
        bounds="[)"
    ),
)

# ✅ OPTION B — use second_tenant which has no seeded markup/labor rows
markup = TenantMarkupVersion(
    tenant_id=second_tenant.id,  # ← no seed data here
    job_expense_category_code="materials",
    valid_period=DateTimeTZRange(lower=datetime.now(UTC), upper=None),
)
```

**Closed range years to use safely**: 2019, 2020, 2021, 2022, 2023, 2024 — all before the seed data's `[2026-06-01, ...)` lower bound.

### Never Count All Rows — Always Scope by ID

Tests that insert N rows and then assert `len(result) == N` by counting all tenant rows will break as soon as any seed data exists in that table for that tenant.

```python
# ❌ WRONG — counts ALL rows for test_tenant including seeded ones
result = db_session.exec(
    select(TenantMarkupVersion).where(TenantMarkupVersion.tenant_id == test_tenant.id)
).all()
assert len(result) == 2  # fails if seed data exists

# ✅ CORRECT — scope by the IDs this test created
v1 = TenantMarkupVersion(...)
v2 = TenantMarkupVersion(...)
db_session.add(v1)
db_session.add(v2)
db_session.commit()

inserted_ids = {v1.id, v2.id}
result = db_session.exec(
    select(TenantMarkupVersion).where(TenantMarkupVersion.id.in_(inserted_ids))
).all()
assert len(result) == 2  # ✅ only counts this test's rows
```

### "Empty State" Tests: Use `second_tenant`

Tests that verify a tenant has zero rows (e.g., `assert data["total"] == 0`) must use `second_tenant`, which has no pre-seeded data. `test_tenant` (`...0001`) has seeded markup, labor rates, and other config rows.

```python
# ❌ WRONG — test_tenant has seeded rows, will never be empty
def test_get_active_markups_empty(self, client, test_tenant):
    response = client.get("/api/v1/settings/markups/test")
    assert response.json()["total"] == 0  # fails — seeded row exists

# ✅ CORRECT — second_tenant has no seeded markup rows
def test_get_active_markups_empty(self, client, second_tenant):
    response = client.get(
        "/api/v1/settings/markups/test",
        params={"test_tenant_id": str(second_tenant.id)},  # pass as query param
    )
    assert response.json()["total"] == 0  # ✅ passes — no rows for second_tenant
```

### Seeded Config Rows: Delete Before Testing Defaults

Tests that use the `test_tenant` and expect certain tables to be empty (e.g., `tenant_onboarding_checklist`) must delete the seeded row at the start of the test.

```python
# ✅ CORRECT — delete the seeded row so the endpoint creates a fresh default
def test_get_checklist_returns_defaults(self, client, db_session, test_tenant):
    from sqlalchemy import text
    db_session.execute(
        text("DELETE FROM public.tenant_onboarding_checklist WHERE tenant_id = :tid"),
        {"tid": str(test_tenant.id)},
    )
    db_session.commit()

    response = client.get(f"/api/v1/tenants/{test_tenant.id}/onboarding/checklist/test")
    data = response.json()
    assert data["quickbooks_connected"] is False  # ✅ fresh default state
```

### What the Seed System Populates for `test_tenant`

The following tables have persistent rows for `TEST_TENANT_ID` (`...0001`) after running `seed_test_tenant.py`. Tests that need these tables to be empty must use `second_tenant` or explicitly delete these rows:

| Table | Seeded rows | Category code / skill |
|---|---|---|
| `tenant_markup_version` | 1 row | `materials` @ 20% — `[2026-06-01, NULL)` |
| `labor_rate_version` | 3 rows | `master`, `journeyman`, `apprentice` — open-ended |
| `tenant_onboarding_checklist` | 1 row | All flags dismissed/completed |
| `password_policy` | 1 row | min_length=8 |
| `tenant_email_branding` | 1 row | brand_color=#2563EB |
| `subscription` | 1 row (if `seed_platform.py` ran) | starter_plan, active |

For the full seed data reference (exact values, UUIDs, pricing constants), see [`dev-docs/seed-data/seed-scripts-usage-reference-analysis.md`](../../dev-docs/seed-data/archived/seed-scripts-usage-reference-analysis.md).

---

## Marking Requirements

Every new test file **must** declare a `pytestmark` list at the module level. The following rules apply:

### Rule 1 — Domain Marker (REQUIRED)
Every test file must have **at least one** domain marker from the list below.
A file may have more than one domain marker if it legitimately spans two domains (uncommon).

### Rule 2 — Test Type Marker (REQUIRED — declare explicitly)
Every test file must have **exactly one** of:
- `pytest.mark.unit` — the test uses mocked external dependencies and the `db_session` rollback fixture (the default for all `tests/domains/` files)
- `pytest.mark.integration` — the test calls real external services (SendGrid, Telnyx, Stripe sandbox, etc.)

> **Note on auto-tagging**: The `pytest_collection_modifyitems` hook in `conftest.py` auto-adds `unit` to any test not marked with an integration-family marker, and auto-adds `integration` to any test marked with `e2e`, `requires_sendgrid`, `requires_telnyx`, `requires_twilio`, or `requires_db`. However, **you must still declare the marker explicitly in `pytestmark`** — relying on the auto-tag is fragile and makes the test's intent opaque to future readers.

### Rule 3 — Service-Specific Markers (REQUIRED when applicable)
If a test calls a real external service, **always add the service-specific marker** in addition to `pytest.mark.integration`. This enables targeted filtering by service:

| If the test calls... | Add this marker |
|---|---|
| SendGrid (real API) | `pytest.mark.requires_sendgrid` |
| Telnyx (real SMS) | `pytest.mark.requires_telnyx` |
| Persistent DB (no rollback) | `pytest.mark.requires_db` |
| Full pipeline (all services) | `pytest.mark.e2e` |
| Slow operation (>1 second) | `pytest.mark.slow` |

These markers enable surgical test selection:
```bash
pytest -m requires_sendgrid    # only SendGrid tests
pytest -m requires_telnyx      # only Telnyx/SMS tests
pytest -m requires_db          # only tests needing persistent DB
pytest -m e2e                  # only full pipeline tests
pytest -m slow                 # only slow tests
```

### Complete `pytestmark` Examples

```python
# Standard unit test (most common):
pytestmark = [
    pytest.mark.domain_sales_quoting,
    pytest.mark.unit,
]

# Integration test hitting SendGrid:
pytestmark = [
    pytest.mark.domain_notifications_comms,
    pytest.mark.integration,
    pytest.mark.requires_sendgrid,
]

# End-to-end test hitting multiple services:
pytestmark = [
    pytest.mark.domain_invoicing_billing,
    pytest.mark.integration,
    pytest.mark.e2e,
    pytest.mark.requires_db,
]

# Slow unit test:
pytestmark = [
    pytest.mark.domain_voice_ai,
    pytest.mark.unit,
    pytest.mark.slow,
]
```

---

### Available Domain Markers

| Marker | Domain |
|---|---|
| `pytest.mark.domain_audit_compliance` | Audit & Compliance (PRD §3.1) |
| `pytest.mark.domain_catalog_pricing` | Catalog & Pricing (PRD §3.2) |
| `pytest.mark.domain_crm` | CRM (PRD §3.3) |
| `pytest.mark.domain_field_operations` | Field Operations & Jobs (PRD §3.4) |
| `pytest.mark.domain_identity_access` | Identity, Access & Tenant (PRD §3.5) |
| `pytest.mark.domain_invoicing_billing` | Invoicing & Billing (PRD §3.6) |
| `pytest.mark.domain_notifications_comms` | Notifications & Communications (PRD §3.7) |
| `pytest.mark.domain_platform_infrastructure` | Platform Infrastructure (PRD §3.8) |
| `pytest.mark.domain_quickbooks` | QuickBooks Integration (PRD §3.9) |
| `pytest.mark.domain_sales_quoting` | Sales & Quoting (PRD §3.10) |
| `pytest.mark.domain_subscriptions_usage` | Subscriptions & Usage (PRD §3.11) |
| `pytest.mark.domain_tax_calculation` | Tax Calculation (PRD §3.12) |
| `pytest.mark.domain_voice_ai` | Voice AI (PRD §3.13) |
| `pytest.mark.domain_scheduling_dispatch` | Scheduling & Dispatch (PRD §3.14) |
| `pytest.mark.domain_mobile_offline` | Mobile Offline Operations (PRD §3.15) |
| `pytest.mark.domain_help_support` | Help & Support (PRD §3.16) |

---

## Running Tests

**NOTE:** make sure you append the folloing to all commands below to minimize out of the pytest command and reduce our token usage:

"tests/ -v 2>&1 | grep -E "(passed|failed|error|warning|===)" | tail -20"

```bash
cd backend

# All unit tests (fastest — no external services):
pytest -m unit

# All non-integration tests (same result as above):
pytest -m "not integration"

# All tests in a single domain:
pytest -m domain_voice_ai

# All tests in a single domain, unit only:
pytest -m "domain_voice_ai and unit"

# Multiple domains:
pytest -m "domain_voice_ai or domain_sales_quoting"

# All integration tests (run intentionally — may incur external API costs):
pytest -m integration

# Only SendGrid integration tests:
pytest -m requires_sendgrid

# Only Telnyx/SMS integration tests:
pytest -m requires_telnyx

# Only persistent-DB integration tests:
pytest -m requires_db

# Only end-to-end pipeline tests:
pytest -m e2e

# Only slow tests:
pytest -m slow
```

**NOTE:** Run the following bash commands as is:

```bash
# Run a specific test file only:
pytest tests/batch_1e/test_task_1b2_job_assignment_scheduling.py -v

# Run a specific test class:
pytest tests/batch_1e/test_task_1b2_job_assignment_scheduling.py::TestAssignTech -v

# Run a specific test method:
pytest tests/batch_1e/test_task_1b2_job_assignment_scheduling.py::TestAssignTech::test_assign_primary_returns_201 -v

# Run with stdout output (useful for debugging):
pytest -s tests/domains/scheduling_dispatch/
```

### Getting a test count baseline before making changes

Before any refactor or fix that touches test files, always capture the full suite baseline:

```bash
cd backend
pytest tests/ --co -q 2>/dev/null | tail -1   # count collected tests
pytest -m unit /tests -q 2>&1 | tail -3       # unit test pass/fail summary
```

Record these numbers. After your changes, re-run and confirm the counts match and no regressions were introduced.

### Complete marker reference command list

```bash
# Fast local tests only (everything except real external services)
pytest -m unit

# Exclude all external-service tests (equivalent to unit)
pytest -m "not integration"

# Run only integration/e2e tests (requires real services running)
pytest -m integration
pytest -m e2e
pytest -m requires_sendgrid
pytest -m requires_telnyx
pytest -m requires_ollama   # real LLM container
pytest -m requires_whisper  # real Whisper container

# Domain-scoped fast runs (unit only)
pytest -m "unit and domain_quickbooks"
pytest -m "unit and domain_voice_ai"
pytest -m "unit and domain_sales_quoting"
pytest -m "unit and domain_crm"
pytest -m "unit and domain_identity_access"
pytest -m "unit and domain_notifications_comms"
pytest -m "unit and domain_platform_infrastructure"
pytest -m "unit and domain_scheduling_dispatch"
pytest -m "unit and domain_mobile_offline"
pytest -m "unit and domain_help_support"
pytest -m "unit and domain_invoicing_billing"
pytest -m "unit and domain_subscriptions_usage"
pytest -m "unit and domain_tax_calculation"
pytest -m "unit and domain_field_operations"
pytest -m "unit and domain_audit_compliance"
pytest -m "unit and domain_catalog_pricing"

# Skip entitlement mocking for real subscription enforcement tests
pytest -m skip_mock_entitlement_allowed
```

---

## Error Response Format

All API endpoints return RFC 7807 `application/problem+json` for errors. Assert this in tests:

```python
assert response.status_code == 422
body = response.json()
assert "type" in body       # URI identifying the problem type
assert "title" in body      # Short human-readable summary
assert "status" in body     # HTTP status code
assert "detail" in body     # Human-readable explanation
```

---

## What NOT to Do

- ❌ **Do not declare `client = TestClient(app)` at module level** — this bypasses the rollback fixture and permanently writes to the dev database (see [The Module-Level TestClient Anti-Pattern](#the-module-level-testclient-anti-pattern))
- ❌ Do not create a new `tests/domains/<new_folder>/` directory — use an existing one
- ❌ Do not create new `batch_*`, `phase_*`, or other top-level test directories
- ❌ Do not add new test files to existing `batch_*` or `phase_*` folders
- ❌ Do not move or rename existing `batch_*` or `phase_*` test files (preserves git history)
- ❌ Do not re-declare `db_engine`, `db_session`, or `client` in individual test files or domain `conftest.py` files — use the root `conftest.py`
- ❌ Do not use SQLite — only PostgreSQL
- ❌ Do not call `db_session.rollback()` manually in tests — the fixture handles rollback automatically (calling it manually may cause `SAWarning`)
- ❌ Do not hardcode `tenant_id = "00000000-0000-0000-0000-000000000001"` as a string — use the `test_tenant` fixture and access `test_tenant.id`
- ❌ Do not omit the `pytestmark` list — every new test file must declare domain and type markers explicitly
- ❌ Do not rely on the `conftest.py` auto-tagging hook as a substitute for declaring `pytestmark` — declare it explicitly so intent is clear
- ❌ Do not pass `/test` endpoint calls through a module-level `TestClient` — always use the `client` fixture (see [The `/test` endpoint trap](#the-module-level-testclient-anti-pattern))
- ❌ **Do not count all rows for `test_tenant` and assert a specific number** — seed data persists in those tables; use ID-scoped assertions (see [Never Count All Rows](#never-count-all-rows--always-scope-by-id))
- ❌ **Do not use deterministic UUIDs `...0001` through `...0004`** in test fixtures — permanently reserved for seed infrastructure; always use `uuid.uuid4()` (see [Reserved UUIDs](#reserved-uuids))
- ❌ **Do not insert open-ended temporal ranges (`[date, NULL)`) for `test_tenant`** in `tenant_markup_version` or `labor_rate_version` — GiST constraint will reject overlaps with seeded rows; use past closed ranges or `second_tenant` (see [GiST Temporal Conflicts](#gist-temporal-conflicts))
- ❌ **Do not hardcode `"test@pilot.local"` as the test user email** — it is now `"dev@pilot.local"` since June 2026 seed system rename
- ❌ **Do not expect `test_tenant` to have empty `tenant_onboarding_checklist`, `tenant_markup_version`, or `labor_rate_version`** — use `second_tenant` or delete the seeded row (see [Seeded Config Rows: Delete Before Testing Defaults](#seeded-config-rows-delete-before-testing-defaults))

---

## Historical Batch Folders Reference

Existing tests are in batch/phase folders created during iterative development. These are read-only organizationally. See `dev-docs/analysis/pilot-app-be-tests-list.md` _(private)_ for the complete inventory of all ~199 existing test files and which domain each batch covers.

### Known Legacy Issues in Batch Folders

The following files in legacy batch folders have confirmed issues that must be fixed before running the full suite in a way that touches the dev DB:

| File | Issue | Fix Required |
|---|---|---|
| [`tests/batch_1e/test_task_1b2_job_assignment_scheduling.py`](batch_1e/test_task_1b2_job_assignment_scheduling.py) | Module-level `client = TestClient(app)` — permanently writes customers, sites, jobs to `pilot_dev` on every test run | Replace module-level `client` with fixture; pass `client` as parameter to `_create_test_job()` |
| [`tests/batch_1e/test_task_1b4_conflict_detection.py`](batch_1e/test_task_1b4_conflict_detection.py) | Same anti-pattern — module-level `client = TestClient(app)` | Replace module-level `client` with fixture; pass `client` as parameter to `_create_scheduled_assigned_job()` |

These two files are responsible for accumulating 7,850 orphaned customer/site/job stub records in `pilot_dev` (confirmed May 31, 2026). The fix must be applied AND the orphaned records purged before the dev DB is suitable for UI testing.
