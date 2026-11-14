# Implementation Prompt: SD-10 — E2E Test Harness Scaffold (Priority 5 Scenarios)

**Mode**: Pilot Python Engineer  
**Batch**: SD-10  
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §E2E Test Harness  
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-sd-design-sprint-design.md` §SD-10  
**Estimated session**: 4–6 hours  
**Platform**: Backend (`backend/`) + infrastructure config files  
**Frontend companion**: React Engineer will wire Playwright specs (Phase 2) after this scaffold is in place — that is a separate batch  
**Prerequisite**: SD-BE-1 and SD-BE-2 must be complete before this batch starts (harness depends on seeded data and revised feature set)

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`dev-docs/architecture-design/pilot-python-engineer-methods.md`** — §13, §16
- **`backend/tests/README-adding-tests.md`** — full document; the Seed Data Coexistence Rules (v1.3) are the most critical section for this batch

**Critical rules for this batch:**

- **Rule — Separate E2E DB**: The E2E harness MUST use a separate database (`pilot_e2e_db`). **Never run teardown against the dev DB (`pilot_dev_db` or `pilot`)**. The `reset_dev_db.py` script targets the dev DB — do not call it from the E2E harness.
- **Rule — No live external API calls in CI**: E2E tests must mock Stripe, QuickBooks, Google OAuth, and Telnyx. Tests that require real external API calls are NOT part of Tier 1 (pytest) and belong in Tier 2 (Playwright) or manual testing only.
- **Rule 11**: If ANY test fails — fix it. No exceptions.
- **Rule 1**: Verify DB state with MCP before writing any SQL.
- **Rule — Scope boundaries**: This batch scaffolds the harness and automates the first 5 priority scenarios. Do NOT attempt to automate all 16 workflows catalogued in the design doc — that is out of scope for this batch.

---

## Pre-Work: Establish Regression Baseline

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=no -q 2>&1 | tail -5
```

Record the exact count. Fix any pre-existing failures before starting.

---

## Pre-Work: Run MCP Verification Queries

```sql
-- 1. Confirm SD-BE-1 is complete — invoice should have reminder columns
SELECT column_name FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'invoice'
AND column_name IN ('last_reminder_sent_at', 'reminder_count')
ORDER BY column_name;

-- 2. Confirm SD-BE-2 is complete — dispatch_slots should be in product_feature
SELECT code FROM public.product_feature ORDER BY code;

-- 3. Confirm test DB setup (pilot_e2e_db does not exist yet — expected)
SELECT datname FROM pg_database WHERE datname LIKE 'pilot%';

-- 4. Confirm seed scripts are up to date — quote_template should have 3 rows
SELECT COUNT(*) FROM public.quote_template WHERE tenant_id IS NULL;

-- 5. Confirm supplier catalog seed ran
SELECT COUNT(*) FROM public.supplier;
```

> **MCP Usage Rule**: Read-only. If any query returns unexpected results — STOP and complete SD-BE-1 / SD-BE-2 first.

---

## Pre-Work: Read These Source Files

```
backend/tests/conftest.py                                    ← understand all available fixtures before creating new ones
backend/migrations/scripts/reset_dev_db.py                  ← understand Group D tables, SCENARIOS dict, teardown pattern
backend/migrations/scripts/seed_core.py                     ← Group A recovery — will be called in E2E globalSetup
backend/migrations/scripts/seed_platform.py                 ← Group B
backend/migrations/scripts/seed_test_tenant.py              ← Group C
backend/migrations/scripts/seed_scenario_quote_to_cash.py  ← read before writing E2E scenario data
backend/migrations/scripts/seed_scenario_dispatch.py        ← same
docker-compose.yml                                           ← understand current service definitions before adding e2e variant
```

---

## Background

This batch implements the Tier 1 (pytest + httpx integration tests) layer of the 3-tier E2E harness recommended in the design doc. The full recommendation:

- **Tier 1**: `pytest` + `httpx` integration tests — covers all backend API flows — runs on every PR merge
- **Tier 2**: Playwright browser E2E — covers web UI critical paths — runs nightly (separate batch)
- **Tier 3**: Maestro mobile — runs weekly (separate batch)

**This batch** = Tier 1 scaffold + first 5 priority scenarios as pytest integration tests.

The 5 priority scenarios:
1. **CP-1: Auth + Tenant Isolation** — login paths for owner/tech/office_staff; RBAC enforcement; cross-tenant isolation
2. **CP-2: Quote-to-Cash** — create quote → send → customer accepts (via public link) → invoice created → payment recorded → status=paid
3. **CP-3: Dispatch + Field Sync** — create job → assign tech → log time entry → log expense → mark job complete
4. **CP-4: Customer SMS Thread** — create customer with phone → send SMS → simulate inbound reply → assert unread badge
5. **CP-5: Dunning Cycle** — create overdue invoice → run `_send_overdue_invoice_reminders_impl` → assert reminder_count=1 → record payment → assert dunning stops

---

## Task 1 — Create `docker-compose.e2e.yml`

Create `backend/docker-compose.e2e.yml` (or at project root — check where `docker-compose.yml` currently lives):

```yaml
version: "3.9"

services:
  db_e2e:
    image: pgvector/pgvector:pg17
    environment:
      POSTGRES_DB: pilot_e2e_db
      POSTGRES_USER: pilot
      POSTGRES_PASSWORD: pilot_e2e_password
    ports:
      - "5433:5432"   # different port from dev DB (5432)
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U pilot -d pilot_e2e_db"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis_e2e:
    image: redis:7-alpine
    ports:
      - "6380:6379"   # different port from dev Redis (6379)
```

---

## Task 2 — Create `backend/.env.e2e`

Create `backend/.env.e2e` (add to `.gitignore` — never commit):

```bash
# E2E environment — isolated from dev
DATABASE_URL=postgresql://pilot:pilot_e2e_password@localhost:5433/pilot_e2e_db
REDIS_URL=redis://localhost:6380

# Mock/test mode flags
SMS_CARRIER=mock              # SmsCarrier adapter uses MockCarrier — no real Telnyx calls
STRIPE_WEBHOOK_SECRET=whsec_test_e2e_placeholder
STRIPE_SECRET_KEY=sk_test_e2e_placeholder

# Cognito — use same test values as dev (Cognito JWT is mocked in tests anyway)
COGNITO_USER_POOL_ID=us-east-1_XXXXXXXXX
COGNITO_CLIENT_ID=test_client_id
COGNITO_REGION=us-east-1

# Disable actual email sending in E2E
EMAIL_BACKEND=console

# Feature flags
ENVIRONMENT=e2e
```

---

## Task 3 — Create `backend/tests/e2e/` directory structure

```
backend/tests/e2e/
├── __init__.py
├── conftest_e2e.py          ← E2E-specific fixtures (separate from unit conftest.py)
├── seed_e2e_db.py           ← E2E seed script (runs A→B→C→D for the e2e DB)
├── cp1_auth_tenant/
│   ├── __init__.py
│   └── test_auth_rbac.py
├── cp2_quote_to_cash/
│   ├── __init__.py
│   └── test_quote_to_cash.py
├── cp3_dispatch_field_sync/
│   ├── __init__.py
│   └── test_dispatch.py
├── cp4_customer_sms/
│   ├── __init__.py
│   └── test_sms_thread.py
└── cp5_dunning_cycle/
    ├── __init__.py
    └── test_dunning.py
```

### `backend/tests/e2e/conftest_e2e.py`

```python
"""
E2E-specific fixtures. Uses pilot_e2e_db — NEVER the dev DB.
Run with: pytest tests/e2e/ --e2e
"""
import os
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, create_engine

# E2E DB URL — from .env.e2e
E2E_DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://pilot:pilot_e2e_password@localhost:5433/pilot_e2e_db",
)

@pytest.fixture(scope="session")
def e2e_engine():
    """Session-scoped engine pointing at pilot_e2e_db."""
    engine = create_engine(E2E_DATABASE_URL)
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def e2e_client(e2e_engine):
    """TestClient with the E2E DB injected."""
    from app.main import app
    from core.db import get_db

    def override_get_db():
        with Session(e2e_engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()
```

### `backend/tests/e2e/seed_e2e_db.py`

```python
"""
Run once before the E2E suite to bring pilot_e2e_db to a known seed state.
Called by pytest's session-scoped fixture or as a standalone script.

Usage:
    python tests/e2e/seed_e2e_db.py
"""
import subprocess
import sys

E2E_ENV = {"DATABASE_URL": "postgresql://pilot:pilot_e2e_password@localhost:5433/pilot_e2e_db"}

def run(cmd: list[str]) -> None:
    result = subprocess.run(cmd, env={**__import__("os").environ, **E2E_ENV}, check=True)
    if result.returncode != 0:
        sys.exit(result.returncode)

if __name__ == "__main__":
    print("=== Seeding E2E DB ===")
    run(["alembic", "upgrade", "head"])
    run(["python", "migrations/scripts/seed_core.py"])
    run(["python", "migrations/scripts/seed_platform.py"])
    run(["python", "migrations/scripts/seed_test_tenant.py"])
    run(["python", "migrations/scripts/seed_scenario_quote_to_cash.py"])
    run(["python", "migrations/scripts/seed_scenario_dispatch.py"])
    run(["python", "migrations/scripts/seed_scenario_customer_comms.py"])
    run(["python", "migrations/scripts/seed_scenario_supplier_catalog.py"])
    print("=== E2E DB Seed Complete ===")
```

---

## Task 4 — Add `pytest.ini` / `pyproject.toml` E2E marker

In `backend/pyproject.toml` (or `pytest.ini`), add an `e2e` marker:

```toml
[tool.pytest.ini_options]
markers = [
    # ... existing markers ...
    "e2e: marks tests as end-to-end integration tests (use --e2e flag to run)",
]
```

Add a custom `--e2e` CLI option so E2E tests are excluded by default from `pytest -m unit`:

```python
# In conftest.py (main, not e2e) — add a conftest hook to skip e2e tests unless --e2e is passed
def pytest_addoption(parser):
    parser.addoption("--e2e", action="store_true", default=False, help="Run E2E tests")

def pytest_collection_modifyitems(config, items):
    if not config.getoption("--e2e"):
        skip_e2e = pytest.mark.skip(reason="Pass --e2e to run E2E tests")
        for item in items:
            if "e2e" in item.nodeid:
                item.add_marker(skip_e2e)
```

---

## Task 5 — CP-1: Auth + Tenant Isolation Tests

File: `backend/tests/e2e/cp1_auth_tenant/test_auth_rbac.py`

```python
"""
CP-1: Auth + Tenant Isolation
- Owner, tech, office_staff can log in and access correct surfaces
- Tenant ID scoping prevents cross-tenant data access
"""
import pytest

pytestmark = [pytest.mark.e2e]


def test_owner_can_access_dashboard(e2e_client):
    """Owner login → GET /api/v1/dashboard → 200"""
    # Use the test endpoint pattern to get an auth token for dev@pilot.local (owner)
    # Then assert dashboard returns data
    token = _get_test_token(e2e_client, "dev@pilot.local")
    resp = e2e_client.get("/api/v1/dashboard", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200


def test_technician_cannot_access_billing(e2e_client):
    """Tech (tech@pilot.local) should get 403 on billing endpoints"""
    token = _get_test_token(e2e_client, "tech@pilot.local")
    resp = e2e_client.get("/api/v1/invoices", headers={"Authorization": f"Bearer {token}"})
    # Adjust expected status based on RBAC — tech may see invoices but not billing settings
    assert resp.status_code in (200, 403)


def test_cross_tenant_isolation(e2e_client):
    """A customer created in tenant A must NOT be visible in tenant B"""
    # Create a customer in test_tenant via /test endpoint
    create_resp = e2e_client.post("/api/v1/customers/test", json={
        "first_name": "E2E", "last_name": "IsolationTest",
        "customer_type": "person", "lifecycle_status_code": "active",
    })
    assert create_resp.status_code == 201
    customer_id = create_resp.json()["id"]

    # Try to access this customer using second_tenant context
    # The /test endpoint uses test_tenant — second_tenant should return 404
    # Read conftest_e2e.py to understand how to create a second-tenant context


def _get_test_token(client, email: str) -> str:
    """Get a test JWT token for the given email via the /test/token endpoint."""
    # Check if a test token endpoint exists — if not, use mock_cognito_jwt pattern
    # Read conftest.py to understand the mock JWT pattern before implementing
    raise NotImplementedError("Read conftest.py mock_jwt_for_user pattern and implement")
```

> **Implementation note**: Read `backend/tests/conftest.py` fully to understand how `mock_cognito_jwt`, `mock_jwt_for_user`, and `test_tenant` fixtures work. The E2E tests must replicate the same authentication mechanism used in unit tests — not a new auth flow.

---

## Task 6 — CP-2: Quote-to-Cash Flow

File: `backend/tests/e2e/cp2_quote_to_cash/test_quote_to_cash.py`

```python
"""
CP-2: Quote-to-Cash
Asserts specific business outcomes at each step:
- quote total = expected cents
- invoice status = 'issued' after send
- payment status = 'succeeded' after record payment
"""
import pytest

pytestmark = [pytest.mark.e2e]


def test_quote_to_cash_full_flow(e2e_client):
    """
    Full quote-to-cash: create quote → send → accept (public link) → create invoice → record payment
    """
    # Step 1: Create a customer (uses test tenant context)
    customer = e2e_client.post("/api/v1/customers/test", json={
        "first_name": "E2E", "last_name": "QuoteCash",
        "customer_type": "person", "lifecycle_status_code": "active",
    }).json()
    customer_id = customer["id"]

    # Step 2: Create a site for the customer
    site = e2e_client.post("/api/v1/sites/test", json={
        "customer_id": customer_id,
        "name": "E2E Test Site",
        "address": {"street": "123 Test St", "city": "Denver", "state": "CO", "zip": "80202"},
    }).json()

    # Step 3: Create a quote
    quote_resp = e2e_client.post("/api/v1/quotes/test", json={
        "customer_id": customer_id,
        "site_id": site["id"],
        "line_items": [
            {"description": "Standard Outlet Install", "unit_price_cents": 15000, "quantity": 1, "line_type_code": "labor"}
        ],
    })
    assert quote_resp.status_code == 201
    quote = quote_resp.json()
    assert quote["total_cents"] == 15000, f"Expected 15000, got {quote['total_cents']}"
    assert quote["status_code"] == "draft"

    # Step 4: Send the quote (status → sent)
    # [Use the appropriate PATCH/POST endpoint — read openapi_schema_map.md]

    # Step 5: Customer accepts via public link
    # [GET /api/v1/quotes/public/{token} → POST accept]

    # Step 6: Create invoice from accepted quote
    # [POST /api/v1/invoices/test or from quote endpoint]

    # Step 7: Record payment
    # [POST /api/v1/payments/test with payment_type=manual_check]

    # Step 8: Assert final states
    # invoice = get_invoice(invoice_id)
    # assert invoice["status_code"] == "paid"
    # assert invoice["balance_due_cents"] == 0

    # IMPLEMENTATION NOTE: Read openapi_schema_map.md for exact endpoint paths before implementing steps 4-8
    # The test structure above shows the PATTERN — do not hardcode endpoint URLs from memory
```

> **Before implementing**: run `grep -A 5 "quotes\|invoice" backend/openapi_schema_map.md | head -60` to find the exact endpoint paths and request/response shapes. The test must assert on specific values, not just HTTP 200.

---

## Task 7 — CP-3: Dispatch + Field Sync

File: `backend/tests/e2e/cp3_dispatch_field_sync/test_dispatch.py`

```python
"""
CP-3: Dispatch + Field Sync
Asserts:
- Job can be created and assigned to tech
- Time entry logged correctly (uses live labor_rate_version rate)
- Job marked complete
"""
import pytest

pytestmark = [pytest.mark.e2e]


def test_dispatch_field_flow(e2e_client):
    """
    Create job → assign tech → log time entry (2 hours master rate) → mark complete
    Expected: time_entry.cost_cents = 2 * 12000 = 24000 (master @ $120/hr)
    """
    # Step 1: Create a job using test tenant context
    # Step 2: Assign tech user (UUID ...0003 = tech@pilot.local)
    # Step 3: Log a time entry (2 hours, skill_level_code=master)
    # Assert: time entry cost_cents = 2 * 12000 = 24000
    # Step 4: Mark job complete (PATCH job status → completed)
    # Assert: job.status_code == "completed"
    pass  # Implement after reading openapi_schema_map.md for job + time_entry endpoints
```

---

## Task 8 — CP-4: Customer SMS Thread

File: `backend/tests/e2e/cp4_customer_sms/test_sms_thread.py`

```python
"""
CP-4: Customer SMS Thread
Asserts:
- Customer can be created with a phone number
- SMS can be sent (MockCarrier — no real Telnyx call)
- Inbound reply creates an unread message
- Unread count is correct
"""
import pytest

pytestmark = [pytest.mark.e2e]


def test_sms_thread_flow(e2e_client):
    """
    Create customer + phone → send SMS → simulate inbound → assert unread=1
    Uses SMS_CARRIER=mock (set in .env.e2e) so no real Telnyx calls are made.
    """
    # Step 1: Create customer with a phone number (E.164 format)
    # Step 2: Send an outbound SMS via the comms API
    # Assert: thread exists with 1 outbound message
    # Step 3: Simulate inbound reply (POST to the webhook endpoint with mock payload)
    # Assert: thread now has 1 unread message
    pass  # Implement after reading webhooks_sms.py and comms route endpoints
```

---

## Task 9 — CP-5: Dunning Cycle

File: `backend/tests/e2e/cp5_dunning_cycle/test_dunning.py`

```python
"""
CP-5: Dunning Cycle
Asserts the enhanced dunning task (SD-06B) works end-to-end:
- Overdue invoice gets reminder_count incremented
- Recently reminded invoice is skipped on second run
- Paid invoice is not dunned
"""
import pytest
from datetime import datetime, timedelta, UTC

pytestmark = [pytest.mark.e2e]


def test_dunning_increments_reminder_count(e2e_client, e2e_engine):
    """
    Create an overdue invoice → run _send_overdue_invoice_reminders_impl → assert reminder_count=1
    """
    from sqlmodel import Session
    from tasks.dunning import _send_overdue_invoice_reminders_impl

    # Create a customer + invoice that's 3 days overdue
    # [Use /test endpoints to create the necessary data]

    # Run the impl directly (not .delay() — unit test pattern)
    with Session(e2e_engine) as db:
        result = _send_overdue_invoice_reminders_impl(db)
        assert result["overdue_invoices"] >= 1

    # Assert: invoice.reminder_count == 1, invoice.last_reminder_sent_at IS NOT NULL
    # [Query the invoice and assert]


def test_dunning_skips_paid_invoice(e2e_client, e2e_engine):
    """A paid invoice must NOT be dunned."""
    from sqlmodel import Session
    from tasks.dunning import _send_overdue_invoice_reminders_impl

    # Create a paid invoice with past due_at
    # [Use /test endpoints]

    with Session(e2e_engine) as db:
        before_count = _get_reminder_count(db, invoice_id)
        _send_overdue_invoice_reminders_impl(db)
        after_count = _get_reminder_count(db, invoice_id)

    assert before_count == after_count  # paid invoice not touched
```

---

## Task 10 — GitHub Actions Workflow

Create `.github/workflows/e2e-nightly.yml`:

```yaml
name: E2E Nightly (Tier 1 — pytest integration)

on:
  schedule:
    - cron: "0 2 * * *"   # 02:00 UTC nightly
  workflow_dispatch:       # Manual trigger

jobs:
  e2e:
    name: E2E Integration Tests
    runs-on: ubuntu-latest

    services:
      postgres:
        image: pgvector/pgvector:pg17
        env:
          POSTGRES_DB: pilot_e2e_db
          POSTGRES_USER: pilot
          POSTGRES_PASSWORD: pilot_e2e_password
        ports:
          - 5433:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

      redis:
        image: redis:7-alpine
        ports:
          - 6380:6379

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python 3.12
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install backend dependencies
        working-directory: backend
        run: pip install -e ".[dev]"

      - name: Seed E2E DB
        working-directory: backend
        env:
          DATABASE_URL: postgresql://pilot:pilot_e2e_password@localhost:5433/pilot_e2e_db
          REDIS_URL: redis://localhost:6380
          SMS_CARRIER: mock
          ENVIRONMENT: e2e
        run: python tests/e2e/seed_e2e_db.py

      - name: Run E2E tests
        working-directory: backend
        env:
          DATABASE_URL: postgresql://pilot:pilot_e2e_password@localhost:5433/pilot_e2e_db
          REDIS_URL: redis://localhost:6380
          SMS_CARRIER: mock
          ENVIRONMENT: e2e
        run: python -m pytest tests/e2e/ --e2e --tb=short -q 2>&1 | tee e2e-results.txt

      - name: Upload E2E results
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: e2e-results
          path: backend/e2e-results.txt
```

---

## Test Requirements

All E2E tests use `pytestmark = [pytest.mark.e2e]`. They are excluded from the default `pytest -m unit` run. They only run when `--e2e` flag is passed or via the nightly GitHub Actions workflow.

**Assertion quality rule**: Every test must assert **specific business values**, not just HTTP status codes:
- ✅ `assert quote["total_cents"] == 15000`  
- ✅ `assert invoice["status_code"] == "paid"`
- ✅ `assert invoice["balance_due_cents"] == 0`
- ❌ `assert resp.status_code == 200`  ← not sufficient on its own

---

## Final Verification

### Phase 1 — Unit Tests Only (confirm no regressions from scaffold)

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=short -q 2>&1 | tail -10
# Must match or exceed baseline — adding E2E files must not break unit tests
```

### Phase 2 — E2E Tests (run with E2E DB running)

```bash
# Start E2E services first
docker-compose -f docker-compose.e2e.yml up -d
sleep 5  # wait for DB to be ready

# Seed the E2E DB
cd <repo>/backend
source .venv/bin/activate
DATABASE_URL=postgresql://pilot:pilot_e2e_password@localhost:5433/pilot_e2e_db \
SMS_CARRIER=mock \
ENVIRONMENT=e2e \
python tests/e2e/seed_e2e_db.py

# Run E2E tests
DATABASE_URL=postgresql://pilot:pilot_e2e_password@localhost:5433/pilot_e2e_db \
SMS_CARRIER=mock \
ENVIRONMENT=e2e \
python -m pytest tests/e2e/ --e2e --tb=short -q 2>&1 | tail -20

echo "=== SD-10 E2E FINAL VERIFICATION COMPLETE ==="
```

---

## Definition of Done

Update `dev-docs/analysis/pilot-launch-plan.md` §E2E Test Harness when each item is done:

- [ ] Pre-modification regression baseline captured (`pytest -m unit`)
- [ ] SD-BE-1 and SD-BE-2 confirmed complete before starting (MCP queries pass)
- [ ] All mandatory source files read before writing code
- [ ] **Task 1**: `docker-compose.e2e.yml` created — E2E DB on port 5433, E2E Redis on port 6380
- [ ] **Task 2**: `backend/.env.e2e` created — added to `.gitignore`
- [ ] **Task 3**: `backend/tests/e2e/` directory structure created
- [ ] **Task 3**: `conftest_e2e.py` created — E2E engine + client fixtures using pilot_e2e_db
- [ ] **Task 3**: `seed_e2e_db.py` created — seeds A→B→C→D into pilot_e2e_db
- [ ] **Task 4**: `--e2e` CLI flag + marker added to `pyproject.toml` + `conftest.py`
- [ ] **Task 5**: `cp1_auth_tenant/test_auth_rbac.py` — owner/tech/office login + cross-tenant isolation tests
- [ ] **Task 6**: `cp2_quote_to_cash/test_quote_to_cash.py` — full quote-to-cash flow with specific value assertions
- [ ] **Task 7**: `cp3_dispatch_field_sync/test_dispatch.py` — job → tech assign → time entry → complete
- [ ] **Task 8**: `cp4_customer_sms/test_sms_thread.py` — customer + SMS thread + inbound reply + unread count
- [ ] **Task 9**: `cp5_dunning_cycle/test_dunning.py` — overdue invoice → dunning runs → reminder_count=1 → paid invoice not dunned
- [ ] **Task 10**: `.github/workflows/e2e-nightly.yml` created — nightly cron at 02:00 UTC
- [ ] E2E tests are excluded from `pytest -m unit` (confirmed via baseline test run)
- [ ] `seed_e2e_db.py` runs without error against pilot_e2e_db
- [ ] **Phase 1**: All unit tests pass (`pytest -m unit`) — zero regressions
- [ ] **Phase 2**: All 5 CP tests pass against live pilot_e2e_db — specific value assertions all green
- [ ] Final test count (before → after unit; E2E new count) documented

---

## Completion Summary

After all Definition of Done items are complete, add a **Completion Summary** to `dev-docs/analysis/pilot-launch-plan.md` §E2E Test Harness:

```markdown
### SD-10 — E2E Test Harness Scaffold: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot Python Engineer
**Baseline (unit)**: X passed, Y failed
**Final (unit)**: X passed — zero regressions
**E2E new tests**: N tests across 5 critical path scenarios

#### What Was Accomplished
- [Brief description]

#### Files Changed / Created
| File | Action |
|---|---|
| `docker-compose.e2e.yml` | Created — E2E services (postgres port 5433, redis port 6380) |
| `backend/.env.e2e` | Created — .gitignore'd |
| `backend/tests/e2e/conftest_e2e.py` | Created |
| `backend/tests/e2e/seed_e2e_db.py` | Created |
| `backend/tests/e2e/cp1_auth_tenant/test_auth_rbac.py` | Created |
| `backend/tests/e2e/cp2_quote_to_cash/test_quote_to_cash.py` | Created |
| `backend/tests/e2e/cp3_dispatch_field_sync/test_dispatch.py` | Created |
| `backend/tests/e2e/cp4_customer_sms/test_sms_thread.py` | Created |
| `backend/tests/e2e/cp5_dunning_cycle/test_dunning.py` | Created |
| `.github/workflows/e2e-nightly.yml` | Created |

#### Tests Added
| Test File | Type | Tests | All Pass |
|---|---|---|---|
| `e2e/cp1_auth_tenant/test_auth_rbac.py` | E2E | N | ✅ |
| `e2e/cp2_quote_to_cash/test_quote_to_cash.py` | E2E | N | ✅ |
| `e2e/cp3_dispatch_field_sync/test_dispatch.py` | E2E | N | ✅ |
| `e2e/cp4_customer_sms/test_sms_thread.py` | E2E | N | ✅ |
| `e2e/cp5_dunning_cycle/test_dunning.py` | E2E | N | ✅ |
```

---

## After This Task — Next Step

After SD-10 scaffold is committed and nightly E2E is green:
- **Playwright Tier 2** (web browser E2E) is the next batch — it uses the same `pilot_e2e_db` and the same 5 critical paths, but driven through the browser via Playwright. That is a React Engineer batch.
- **Maestro Tier 3** (mobile E2E) follows Playwright and is a React Native batch.
