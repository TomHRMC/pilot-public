# Implementation Prompt: UI-FIX-2F — Stripe Connect Backend (Payment Method)

**Mode**: Pilot Python Engineer  
**Batch**: UI-FIX-2F (Backend half)  
**Source decisions**: `dev-docs/architecture-design/batch-designs/ui-fix-2-decisions.md § FIX-020` + `ui-fix-1-decisions.md § FIX-004`  
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-ui-fix-2f-design.md` ← **Read every section**  
**Ops reference**: `dev-docs/pilot-operations.md § 11` ← Stripe Connect architecture explained  
**Estimated session**: 3–4 hours  
**Platform**: Backend only (`backend/`)  
**Frontend companion**: UI-FIX-2F React Engineer prompt (runs after this batch completes and `export_openapi_json.py` is regenerated)

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`dev-docs/architecture-design/pilot-python-engineer-methods.md`** — §13 (Alembic), §8 (Router Design), §16 (Standard Task Workflow)
- **`backend/tests/README-adding-tests.md`** — full document
- **`dev-docs/pilot-operations.md § 11`** — Stripe Connect architecture (two payment flows, Account Links pattern, sandbox account IDs)

**Critical rules for this batch:**

- **Rule 4**: All Alembic migrations must be **blank** — never `--autogenerate`. Use `alembic revision -m "add_stripe_connect_account_id_to_tenant"`.
- **Rule 1**: Never guess column names. Run `postgres-local` MCP to verify the `tenant` table before writing the migration.
- **Rule 8**: All API errors follow RFC 7807 Problem Details format — no plain string `detail`.
- **Rule 9**: Every mutation endpoint calls `set_audit_context_sync(db, user_id=user.id)` before any `db.commit()`.
- **Rule 10**: `require_permission("settings.tenant.write")` on all endpoints. The `settings.tenant.write` permission is held by owner + operator roles — no tech or office_staff access.
- **Rule 6**: `db.get()` is permanently banned on tenant-scoped models. Use `select()` with `WHERE tenant_id = :tid`.
- **Rule 3 (Alembic)**: Always implement a complete `downgrade()` — never leave it empty.
- **Rule 11**: If ANY test fails — fix it before declaring done.

> **Stripe Architecture Note (read before designing)**: This batch uses **Stripe Account Links** (server-side hosted onboarding), NOT the legacy OAuth 2.0 / `ca_` client ID approach. No `STRIPE_CONNECT_CLIENT_ID` environment variable is needed. The `STRIPE_SECRET_KEY` already in `.env` is reused. For local testing: `STRIPE_CONNECT_PLATFORM_KEY` has been added to `backend/.env` — this is the sandbox key for the Connect platform account.

> **MCP Usage Rule**: The `postgres-local` MCP is for **read-only verification only**. Never use it to INSERT, UPDATE, or DELETE.

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

Run all of these via `postgres-local` MCP before writing any code:

```sql
-- 1. Confirm stripe_connect_account_id does NOT yet exist on tenant
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'tenant'
AND column_name = 'stripe_connect_account_id';
-- Expected: 0 rows returned

-- 2. Confirm current tenant table structure (verify column names before using in code)
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'tenant'
ORDER BY ordinal_position;

-- 3. Confirm current alembic head
SELECT version_num FROM public.alembic_version;

-- 4. Verify stripe_customer_id exists (the subscription billing column — NOT the same as stripe_connect_account_id)
SELECT column_name, data_type FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'tenant'
AND column_name = 'stripe_customer_id';

-- 5. Check any existing Stripe-related settings routes
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public' AND table_name LIKE 'stripe%';
```

**Expected results:**
- Query 1: 0 rows — column does not exist yet
- Query 2: confirms `stripe_customer_id` (Pilot billing) but no `stripe_connect_account_id`
- If query 1 returns a row → **STOP and ask Tom before proceeding** (column may already be partially implemented)

---

## Pre-Work: Read These Source Files

```
backend/app/models/tenant.py         ← Find Tenant SQLModel class; confirm field naming pattern
backend/api/routes/settings.py       ← Understand existing settings route pattern before adding
backend/services/stripe_subscriptions.py  ← Understand existing Stripe usage pattern
backend/services/stripe_payment_intents.py  ← This file needs the PaymentNotConfiguredError guard update
backend/api/schemas/schemas.py       ← Understand existing Pydantic schema patterns
backend/core/auth.py                 ← Confirm AuthenticatedUser.tenant_id usage
```

Also run:
```bash
# Find existing Stripe-related routes
grep -rn "stripe" backend/api/routes/ --include="*.py" -l

# Confirm require_permission import pattern
grep -n "require_permission\|settings.tenant.write" backend/api/routes/settings.py | head -10

# Find existing billing/settings route file
find backend/api/routes/ -name "billing*.py" -o -name "settings*.py" | head -10
```

---

## Background

This batch implements the **server-side Stripe Account Links** flow so contractors can connect their own Stripe accounts to Pilot. When connected, customer payments on invoice payment pages route directly to the contractor's Stripe account (not Pilot's platform account).

**Two payment flows — do not confuse:**
- `STRIPE_SECRET_KEY` → used for Pilot's subscription billing (charging tenants for Pilot). Already implemented. Not changed in this batch.
- `STRIPE_CONNECT_PLATFORM_KEY` → used for Connect API calls (creating connected accounts, generating Account Links). New in this batch.

**Core flow:**
1. Contractor clicks "Connect Stripe Account" in settings
2. `POST /api/v1/settings/billing/stripe-connect/onboard` — backend creates (or reuses) a Stripe connected account, generates an Account Link URL, returns it
3. Frontend redirects browser to the Stripe-hosted onboarding URL
4. Contractor completes onboarding on Stripe's website
5. Stripe redirects to `/settings/billing/payment-method?connected=true` — no backend callback needed
6. `GET /api/v1/settings/billing/stripe-connect/status` — frontend polls to confirm `charges_enabled=true`

---

## Task 1 — Alembic Migration: Add `stripe_connect_account_id` to `tenant`

```bash
cd <repo>/backend
source .venv/bin/activate
alembic revision -m "add_stripe_connect_account_id_to_tenant"
```

Write the migration:

```python
"""add_stripe_connect_account_id_to_tenant

Revision ID: <generated>
Revises: <current_head>
Create Date: <generated>

Adds stripe_connect_account_id to the tenant table.
This stores the Stripe connected account ID (acct_XXX) when a tenant
connects their Stripe account via the Payment Method settings page.
NULL = not connected (manual payment fallback).
"""

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    op.add_column(
        "tenant",
        sa.Column("stripe_connect_account_id", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("tenant", "stripe_connect_account_id")
```

Run and verify:
```bash
alembic upgrade head
alembic downgrade -1
alembic upgrade head
alembic current  # must show new head
```

**Update `Tenant` SQLModel** in `backend/app/models/tenant.py`:
- Add `stripe_connect_account_id: str | None = Field(default=None)` to the model
- Read the file first to match the existing field definition pattern (some use `sa_column=Column(...)`, some use plain `Field(...)`)

**Regenerate DB model map** after model change:
```bash
python generate_db_model_map.py
grep "stripe_connect_account_id" backend/db_models_map.md  # confirm it appears
```

**Intermediate unit test check:**
```bash
python -m pytest -m unit --tb=short -q 2>&1 | tail -5
```

---

## Task 2 — New Pydantic Schemas

Add these schemas to `backend/api/schemas/schemas.py` (or a new `backend/api/schemas/stripe_connect.py` if you prefer — read the existing schema organization first and match the pattern).

**Read the file first** to find the correct location and match the style.

```python
class StripeConnectStatusResponse(BaseModel):
    """Response for GET /api/v1/settings/billing/stripe-connect/status"""
    connected: bool
    account_id: str | None = None       # Stripe acct_XXX (shown masked in UI)
    account_name: str | None = None     # From stripe.Account.retrieve()
    charges_enabled: bool = False       # True once onboarding is complete
    payouts_enabled: bool = False       # True once bank account is added


class StripeConnectOnboardResponse(BaseModel):
    """Response for POST /api/v1/settings/billing/stripe-connect/onboard"""
    account_link_url: str       # Stripe-hosted URL — frontend redirects browser here
    expires_at: int             # Unix timestamp — Account Link expires in ~10 min


class StripeConnectDisconnectResponse(BaseModel):
    """Response for DELETE /api/v1/settings/billing/stripe-connect"""
    disconnected: bool = True
    message: str = "Stripe account disconnected. Customers will see manual payment instructions."
```

---

## Task 3 — New Route File: `stripe_connect.py`

Create `backend/api/routes/stripe_connect.py`. Read `backend/api/routes/settings.py` first to understand the existing routing pattern, auth imports, and how to register routes in `main.py`.

**Three endpoints:**

### 3.1 — `GET /api/v1/settings/billing/stripe-connect/status`

```python
@router.get(
    "/stripe-connect/status",
    response_model=StripeConnectStatusResponse,
    summary="Get Stripe Connect account status",
)
def get_stripe_connect_status(
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(
        require_permission("settings.tenant.write")
    ),
) -> StripeConnectStatusResponse:
    """Return Stripe Connect account connection status for the current tenant."""
    tenant = db.exec(
        select(Tenant)
        .where(Tenant.id == current_user.tenant_id)
    ).first()
    if not tenant:
        raise HTTPException(
            status_code=404,
            detail={
                "type": "https://errors.pilotfortrades.com/not-found",
                "title": "Tenant not found",
                "status": 404,
                "detail": "Tenant not found.",
            },
        )

    if not tenant.stripe_connect_account_id:
        return StripeConnectStatusResponse(connected=False)

    # Retrieve live status from Stripe
    try:
        stripe_key = getattr(cfg, "STRIPE_CONNECT_PLATFORM_KEY", None) or getattr(cfg, "STRIPE_SECRET_KEY", None)
        stripe.api_key = stripe_key
        account = stripe.Account.retrieve(tenant.stripe_connect_account_id)
        return StripeConnectStatusResponse(
            connected=True,
            account_id=account.id,
            account_name=account.get("business_profile", {}).get("name") or account.get("settings", {}).get("dashboard", {}).get("display_name"),
            charges_enabled=account.get("charges_enabled", False),
            payouts_enabled=account.get("payouts_enabled", False),
        )
    except stripe.error.PermissionError:
        # Account exists in DB but Stripe API can't access it — treat as not connected
        return StripeConnectStatusResponse(
            connected=True,
            account_id=tenant.stripe_connect_account_id,
            charges_enabled=False,
            payouts_enabled=False,
        )
    except stripe.error.StripeError as e:
        raise HTTPException(
            status_code=502,
            detail={
                "type": "https://errors.pilotfortrades.com/stripe-error",
                "title": "Stripe API error",
                "status": 502,
                "detail": f"Could not retrieve Stripe account status: {str(e)}",
            },
        )
```

### 3.2 — `POST /api/v1/settings/billing/stripe-connect/onboard`

```python
@router.post(
    "/stripe-connect/onboard",
    response_model=StripeConnectOnboardResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate Stripe Account Link for onboarding",
)
def stripe_connect_onboard(
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(
        require_permission("settings.tenant.write")
    ),
) -> StripeConnectOnboardResponse:
    """
    Creates (or retrieves) a Stripe connected account and generates an Account Link.
    Frontend redirects browser to the returned URL — Stripe hosts the onboarding UI.
    
    If the tenant already has a stripe_connect_account_id (e.g., incomplete onboarding),
    skip creation and generate a new Account Link for the existing account.
    """
    set_audit_context_sync(db, user_id=current_user.id)

    tenant = db.exec(
        select(Tenant).where(Tenant.id == current_user.tenant_id)
    ).first()
    if not tenant:
        raise HTTPException(status_code=404, detail={...})

    stripe_key = getattr(cfg, "STRIPE_CONNECT_PLATFORM_KEY", None) or getattr(cfg, "STRIPE_SECRET_KEY", None)
    stripe.api_key = stripe_key

    try:
        # Step 1: Create account if not yet present
        if not tenant.stripe_connect_account_id:
            account = stripe.Account.create(
                type="standard",
                country="US",
            )
            tenant.stripe_connect_account_id = account.id
            tenant.updated_at = datetime.now(UTC)
            db.add(tenant)
            db.commit()
            db.refresh(tenant)

        # Step 2: Generate Account Link (expires in ~10 min — OK, user clicks immediately)
        link = stripe.AccountLink.create(
            account=tenant.stripe_connect_account_id,
            refresh_url="https://app.pilotfortrades.com/settings/billing/payment-method?retry=true",
            return_url="https://app.pilotfortrades.com/settings/billing/payment-method?connected=true",
            type="account_onboarding",
        )
        return StripeConnectOnboardResponse(
            account_link_url=link.url,
            expires_at=link.expires_at,
        )
    except stripe.error.StripeError as e:
        raise HTTPException(
            status_code=502,
            detail={
                "type": "https://errors.pilotfortrades.com/stripe-error",
                "title": "Stripe API error",
                "status": 502,
                "detail": f"Could not initiate Stripe Connect onboarding: {str(e)}",
            },
        )
```

### 3.3 — `DELETE /api/v1/settings/billing/stripe-connect`

```python
@router.delete(
    "/stripe-connect",
    response_model=StripeConnectDisconnectResponse,
    summary="Disconnect Stripe connected account",
)
def stripe_connect_disconnect(
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(
        require_permission("settings.tenant.write")
    ),
) -> StripeConnectDisconnectResponse:
    """
    Nulls stripe_connect_account_id on the tenant record.
    Customers will see manual payment instructions on invoice pages until reconnected.
    Does NOT deauthorize the Stripe account — tenant can reconnect later.
    """
    set_audit_context_sync(db, user_id=current_user.id)

    tenant = db.exec(
        select(Tenant).where(Tenant.id == current_user.tenant_id)
    ).first()
    if not tenant:
        raise HTTPException(status_code=404, detail={...})

    tenant.stripe_connect_account_id = None
    tenant.updated_at = datetime.now(UTC)
    db.add(tenant)
    db.commit()

    return StripeConnectDisconnectResponse()
```

> **All three endpoints** must also have `/test` variants using `TestUserContext` per `pilot-python-engineer-methods.md` §11 pattern. Read an existing route file (e.g., `scheduling.py`) to confirm the test endpoint pattern before implementing.

---

## Task 4 — Add Test Endpoints

For each of the 3 authenticated endpoints above, add a corresponding `/test` unauthenticated variant using `get_test_context()`. Follow the exact pattern in `backend/api/routes/scheduling.py` or `backend/api/routes/roles.py`.

**Note**: The `/onboard` test endpoint should use a mock Stripe response (not call real Stripe). In the test environment, the `stripe.Account.create()` and `stripe.AccountLink.create()` calls will be patched by the `mock_ai_services` autouse fixture or a similar mechanism. Check `conftest.py` for existing Stripe mocking patterns.

---

## Task 5 — Register Routes in `main.py`

Find `backend/main.py`. Register the new router. Read the file first to see how existing routers are imported and registered. Add:

```python
from api.routes.stripe_connect import router as stripe_connect_router
app.include_router(stripe_connect_router, prefix="/api/v1/settings/billing")
```

Verify the route paths produce:
- `GET /api/v1/settings/billing/stripe-connect/status`
- `POST /api/v1/settings/billing/stripe-connect/onboard`
- `DELETE /api/v1/settings/billing/stripe-connect`

---

## Task 6 — Update `stripe_payment_intents.py`

**File**: `backend/services/stripe_payment_intents.py`

Read the full file before editing. Add the `PaymentNotConfiguredError` guard before any `PaymentIntent.create()` call:

```python
class PaymentNotConfiguredError(Exception):
    """Raised when a tenant tries to take a payment without a connected Stripe account."""
    pass


def create_payment_intent(tenant: Tenant, amount_cents: int, ...) -> stripe.PaymentIntent:
    # GUARD: must have a connected Stripe account
    if not tenant.stripe_connect_account_id:
        raise PaymentNotConfiguredError(
            "This tenant has not connected a Stripe account. "
            "Visit Settings → Payment Method to connect Stripe before accepting payments."
        )

    stripe_key = getattr(cfg, "STRIPE_CONNECT_PLATFORM_KEY", None) or getattr(cfg, "STRIPE_SECRET_KEY", None)
    stripe.api_key = stripe_key

    pi = stripe.PaymentIntent.create(
        amount=amount_cents,
        currency="usd",
        stripe_account=tenant.stripe_connect_account_id,  # Route to tenant's connected account
        ...existing params...
    )
    return pi
```

Also update the calling code that catches errors from `create_payment_intent()` — find where it's called and add a `except PaymentNotConfiguredError` handler that renders the manual payment instructions instead of a Stripe form. Read the calling code first to understand the error handling pattern.

---

## Task 7 — Update Schema Manager

After the migration runs and all tests pass, update the JSON schema file:

```bash
cd <repo>/backend
python schema_manager.py --help  # Read available commands first
# Then use the appropriate CRUD command to add stripe_connect_account_id to tenant
```

> ⚠️ `schema_manager.py` is a CRUD script — NOT a sync script. Always run `--help` first. Never run `--sync` or `--diff` — those flags do not exist.

---

## Task 8 — Regenerate OpenAPI

```bash
cd <repo>/backend
source .venv/bin/activate
python export_openapi_json.py
```

Verify new endpoints appear:
```bash
grep -A 5 "stripe-connect" backend/openapi_schema_map.md
```

Expected entries:
- `GET /api/v1/settings/billing/stripe-connect/status`
- `POST /api/v1/settings/billing/stripe-connect/onboard`
- `DELETE /api/v1/settings/billing/stripe-connect`

---

## Test Requirements

**Test file**: `backend/tests/domains/platform_infrastructure/test_stripe_connect.py`

```python
pytestmark = [
    pytest.mark.domain_platform_infrastructure,
    pytest.mark.unit,
]
```

**Test cases:**

| Test | What to verify |
|---|---|
| `test_status_not_connected` | `GET /test` endpoint → `{ connected: false }` when tenant has no `stripe_connect_account_id` |
| `test_status_connected` | Set `stripe_connect_account_id` on test tenant; mock `stripe.Account.retrieve`; verify `connected: true` + fields |
| `test_onboard_creates_account` | `POST /test` endpoint; mock `stripe.Account.create` + `stripe.AccountLink.create`; verify `account_link_url` in response; verify `stripe_connect_account_id` set on tenant |
| `test_onboard_reuses_existing_account` | Set existing `stripe_connect_account_id`; mock only `stripe.AccountLink.create` (not `Account.create`); verify `Account.create` NOT called |
| `test_disconnect_clears_account_id` | `DELETE /test` endpoint; tenant has `stripe_connect_account_id`; verify it's null after delete |
| `test_disconnect_already_null` | `DELETE /test` when `stripe_connect_account_id` is already null; verify 200 OK (idempotent) |

**Mocking Stripe in tests**: Use `unittest.mock.patch` or a pytest fixture to mock `stripe.Account.create`, `stripe.Account.retrieve`, and `stripe.AccountLink.create`. Do NOT call real Stripe in unit tests. Check `conftest.py` for any existing `mock_stripe_*` fixtures before creating new ones.

**Intermediate unit test check after each task:**
```bash
python -m pytest -m unit --tb=short -q 2>&1 | tail -5
```

---

## Final Verification

### Phase 1 — Unit Tests Only

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=short -q 2>&1 | tail -10
```

### Phase 2 — Full Suite

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest --tb=short -q 2>&1 | tail -10

# Spot-check new tests
python -m pytest backend/tests/domains/platform_infrastructure/test_stripe_connect.py -v 2>&1 | tail -20

# Verify new endpoints in OpenAPI
grep -A 3 "stripe-connect" backend/openapi_schema_map.md

echo "=== UI-FIX-2F BACKEND FINAL VERIFICATION COMPLETE ==="
```

---

## Definition of Done — UI-FIX-2F (Python Engineer)

- [ ] Pre-modification regression baseline captured using `pytest -m unit`
- [ ] Zero pre-existing unit failures confirmed (or confirmed with Tom)
- [ ] All 5 MCP pre-work queries run — query 1 confirms `stripe_connect_account_id` does NOT yet exist
- [ ] All mandatory source files read before writing any code
- [ ] **Task 1**: Alembic migration written and run; `alembic current` shows new head; downgrade/upgrade cycle verified; `Tenant` SQLModel updated; `db_models_map.md` regenerated
- [ ] **Task 2**: `StripeConnectStatusResponse`, `StripeConnectOnboardResponse`, `StripeConnectDisconnectResponse` Pydantic schemas added
- [ ] **Task 3**: `stripe_connect.py` route file created — 3 authenticated endpoints + 3 `/test` variants; `set_audit_context_sync()` called on POST and DELETE; all errors RFC 7807 format
- [ ] **Task 4**: Test endpoints added for all 3 routes
- [ ] **Task 5**: Routes registered in `main.py` — all 3 endpoints appear in OpenAPI output
- [ ] **Task 6**: `stripe_payment_intents.py` updated — `PaymentNotConfiguredError` guard added; `stripe_account=` param passed; platform key used for API auth
- [ ] **Task 7**: Schema manager run — `stripe_connect_account_id` recorded in JSON schema
- [ ] **Task 8**: `python export_openapi_json.py` run — 3 new endpoints appear in `openapi_schema_map.md`
- [ ] All new test files use `pytestmark` with `domain_platform_infrastructure` + `pytest.mark.unit`
- [ ] Stripe API calls are mocked in all unit tests — no real Stripe calls
- [ ] **Phase 1**: All unit tests pass (`pytest -m unit`) — zero failures
- [ ] **Phase 2**: Full test suite passes (`pytest`) — zero failures
- [ ] Final test count (before → after) documented
- [ ] Completion Summary added to `ui-fix-2-decisions.md` batch overview section for UI-FIX-2F

---

## Handoff to React Engineer

After all Definition of Done items are complete:

1. Run `python export_openapi_json.py` (confirm this was done in Task 8)
2. The React Engineer must run `pnpm sync-api-types` as their first step before implementing the Payment Method page

Add the following to the completion summary:

> **React Engineer handoff**: `openapi.json` and `openapi_schema_map.md` updated. Run `pnpm sync-api-types` before starting UI-FIX-2F React Engineer work. Three new endpoints available: `GET /stripe-connect/status`, `POST /stripe-connect/onboard`, `DELETE /stripe-connect`.

---

## Completion Summary

After all Definition of Done items are complete, add a Completion Summary to `dev-docs/architecture-design/batch-designs/ui-fix-2-decisions.md` under the UI-FIX-2F batch row:

```markdown
### UI-FIX-2F (Backend) — Stripe Connect Endpoints: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot Python Engineer
**Baseline**: X passed, Y failed
**Final**: X+N passed (+N new tests)

#### What Was Accomplished

- Alembic migration: `stripe_connect_account_id TEXT NULL` added to `tenant` table
- Tenant SQLModel updated; db_models_map.md regenerated
- 3 new Pydantic schemas: StripeConnectStatusResponse, StripeConnectOnboardResponse, StripeConnectDisconnectResponse
- 3 new endpoints (+ 3 /test variants): GET /status, POST /onboard, DELETE /stripe-connect
- Account Links pattern: POST /onboard calls stripe.Account.create() + stripe.AccountLink.create()
- stripe_payment_intents.py: PaymentNotConfiguredError guard + stripe_account= routing
- openapi.json + openapi_schema_map.md regenerated

#### Files Changed / Created

| File | Action |
|---|---|
| `backend/migrations/versions/<hash>_add_stripe_connect_account_id_to_tenant.py` | Created |
| `backend/app/models/tenant.py` | Updated — added stripe_connect_account_id field |
| `backend/db_models_map.md` | Regenerated |
| `backend/api/schemas/schemas.py` (or stripe_connect.py) | Updated — 3 new schemas |
| `backend/api/routes/stripe_connect.py` | Created — 3 endpoints + 3 /test variants |
| `backend/main.py` | Updated — registered stripe_connect router |
| `backend/services/stripe_payment_intents.py` | Updated — guard + stripe_account= |
| `backend/openapi.json` | Regenerated |
| `backend/openapi_schema_map.md` | Regenerated |
| `backend/tests/domains/platform_infrastructure/test_stripe_connect.py` | Created |

#### Tests Added

| Test File | Domain | Tests | All Pass |
|---|---|---|---|
| `tests/domains/platform_infrastructure/test_stripe_connect.py` | `domain_platform_infrastructure` | 6 | ✅ |
```
