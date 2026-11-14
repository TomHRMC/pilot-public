# Implementation Prompt: C-B12 (Part A — Python Engineer) — Charter → Teams Upgrade Flow

**Mode**: Pilot Python Engineer
**Batch**: C-B12 (Part A — Python Engineer runs FIRST)
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §2.0 row 14q, §2.1a C-5
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-c-b12-design.md`
**Estimated session**: 2–3 hours
**Platform**: Backend only (`backend/`)
**Frontend companion**: C-B12 Part B (React Engineer) — **gated on a UI design spec from pilot-web-ui-designer + Tom approval**. Do NOT start Part B until the UI spec is approved. After Part A closes, run `python export_openapi_json.py` + `pnpm sync-api-types` as the handoff signal.

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-python-engineer/python-engineer-rules.md`** — full document; the 25 hard rules are non-negotiable STOPs
- **`dev-docs/architecture-design/pilot-python-engineer-methods.md`** — §13 (Alembic), §8 (Router Design), §5 (Model Design), §16 (Standard Task Workflow)
- **`backend/tests/README-adding-tests.md`** — full document; this governs all test file structure, domain markers, and fixture rules

**Before writing any subscription, billing, or entitlement code:**
Read `dev-docs/pilot-operations.md` — covers: tier→plan→ppfv cascade, `is_billing_active` paywall gate, Charter cohort Stripe schedule, notification template resolution order, and all 6 subscription status codes. The billing logic is NOT inferrable from the schema alone.

Critical rules for this batch:

- **Rule 1**: Never guess column names, data types, or table names. Use `postgres-local` MCP to verify every name before use. If MCP returns an error → **STOP and ask Tom**.
- **Rule 3**: After any endpoint change → run `python export_openapi_json.py` (updates both `openapi.json` and `openapi_schema_map.md`).
- **Rule 6**: `db.get()` is permanently banned on tenant-scoped models. Always use tenant-scoped `select()` with an explicit `WHERE tenant_id = :tid` clause.
- **Rule 7**: The `postgres-local` MCP is for **read-only verification only**. Never use it to INSERT, UPDATE, or DELETE data.
- **Rule 8**: All API error responses MUST follow RFC 7807 Problem Details format.
- **Rule 9**: Every mutation endpoint MUST call `set_audit_context_sync(db, user_id=user.id)` before committing.
- **Rule 11**: If ANY test fails during your work — even one that appears to be a pre-existing failure — **you must fix it before declaring the batch done**.
- **Rule 12 (sync routes)**: This app is **synchronous by design**. Every DB-touching route and `_impl()` is a plain `def`. **Never convert a handler that touches the sync `Session` to `async def`**.
- **Rule 13 (Pydantic v2)**: Use v2 idioms only. Banned v1 carryover: `class Config`, `@validator`, `.dict()`, `.json()`, `.parse_obj()`. Use `model_config = ConfigDict(...)`, `@field_validator` / `@model_validator`, `.model_dump()`, `.model_validate()`. Every route needs `response_model`. Money is always integer cents.
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

> **If any tests are already failing before you start**: Do NOT treat them as "pre-existing" and proceed anyway. Either:
> (a) Confirm with Tom that this is a known, accepted failure with a documented reason before proceeding, OR
> (b) Fix the failure before touching any batch files.
>
> You may NOT start implementation work while tests are in an unexplained failed state.

---

## Pre-Work: Run MCP Verification Queries

> **MCP Usage Rule**: The `postgres-local` MCP is for **read-only verification only**. Use it to confirm table names, column types, and existing data. Never use it to INSERT, UPDATE, or DELETE — all data changes go through the application code, seed scripts, or Alembic migrations. If a query fails or returns an error → STOP and ask Tom before proceeding.

Run **all** of these via `postgres-local` MCP before writing any code. If any query returns unexpected results → **STOP and ask Tom**.

```sql
-- 1. Verify tenant has Charter-related columns
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'tenant'
  AND column_name IN ('charter_eligible', 'charter_member_number', 'free_period_ends_at',
                      'current_subscription_tier_id', 'stripe_customer_id')
ORDER BY ordinal_position;

-- 2. Verify subscription has product_plan_code + billing_interval + trial_ends_at + status_id + psp_subscription_id
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'subscription'
  AND column_name IN ('psp_subscription_id', 'status_id', 'is_active', 'product_plan_code',
                      'billing_interval', 'trial_ends_at', 'tenant_id', 'psp_customer_id')
ORDER BY ordinal_position;

-- 3. Verify subscription_tier has Teams price IDs + charter price_locked
SELECT tier_name, monthly_price_cents, annual_price_cents,
       stripe_price_id_monthly, stripe_price_id_annual, is_active, price_locked
FROM subscription_tier WHERE tier_name IN ('charter', 'teams') ORDER BY tier_name;

-- 4. Verify subscription_status codes
SELECT code, name, is_billing_active FROM subscription_status ORDER BY code;

-- 5. Verify subscription row for a Charter tenant (if seed data exists)
SELECT s.psp_subscription_id, s.status_id, s.product_plan_code, s.billing_interval,
       s.is_active, s.trial_ends_at, st.code as status_code, t.charter_eligible
FROM subscription s
JOIN subscription_status st ON s.status_id = st.id
JOIN tenant t ON s.tenant_id = t.id
WHERE t.charter_eligible = true
LIMIT 5;
```

---

## Pre-Work: Read These Source Files

Use `read_file` on each of these before writing any code:

```
backend/services/stripe_subscriptions.py          ← why: _get_stripe_client() + create_charter_subscription() (3-item structure) + resume_subscription() — add upgrade_charter_to_teams() here
backend/core/stripe_config.py                      ← why: get_stripe_ids() — load price_teams_monthly / price_teams_annual
backend/api/routes/tenant_subscription.py          ← why: existing _change_tier_impl() + _resume_subscription_impl() patterns — add upgrade-from-charter endpoint here
backend/app/models/billing.py                      ← why: Subscription + SubscriptionStatus models
backend/app/models/core.py                         ← why: Tenant model (charter_eligible, current_subscription_tier_id, free_period_ends_at)
backend/app/models/subscription.py                 ← why: SubscriptionTier model (tier_name, product_plan_code, stripe_price_id_monthly/annual)
backend/scripts/stripe_ids.test.json               ← why: verify all 9 price IDs are present
backend/db_models_map.md                           ← why: confirm model names and table mappings
backend/tests/conftest.py                           ← why: available fixtures — test_tenant, test_user, mock_cognito_jwt
```

Also run these grep commands to find related files:

```bash
grep -rn "upgrade\|change.tier\|change_tier" backend/api/routes/tenant_subscription.py
grep -rn "charter_eligible" backend/services/ backend/app/models/ --include="*.py"
grep -rn "Subscription.modify" backend/services/ --include="*.py"
```

---

## Background / Context

C-B12 builds the Charter → Teams upgrade flow — the self-service path for a Charter member to voluntarily give up their locked $49/mo rate and move to the Teams plan at standard pricing.

**Key design decision — Dedicated endpoint**: The existing `_change_tier_impl()` in `tenant_subscription.py` calls `stripe.Subscription.modify(sub_id, items=[{"price": selected_price_id}])` — this **adds** a new item without deleting the old one (double-billing). It also does not flip `charter_eligible`, does not end the trial, and does not use `proration_behavior`. C-B12 creates a **dedicated endpoint** (`upgrade-from-charter`) because the Charter flow is fundamentally different.

**Tom decision (2026-08-07)**: Charter members can stay on the Charter rate ($49/mo, Starter features, monthly billing, locked) forever. When they outgrow Starter and want Teams, they upgrade and become a "regular" customer — they choose their billing interval (monthly $179/mo or annual $149/mo effective). The Charter rate is gone for good (`charter_eligible = False` permanently), even if they later downgrade back to Starter.

**No migration** — all required columns already exist from C-B2.

---

## Task 1 — Upgrade Service Function: `upgrade_charter_to_teams()`

In `backend/services/stripe_subscriptions.py`, add `upgrade_charter_to_teams()` after the existing `resume_subscription()` function (around line 681).

**Full implementation** (from design doc §J.1):

```python
def upgrade_charter_to_teams(
    db: Session,
    tenant_id: uuid.UUID,
    billing_interval: str,
) -> dict:
    """Upgrade a Charter member to the Teams plan.

    This is a PERMANENT, IRREVERSIBLE action:
    1. Deletes the Charter monthly item from the Stripe subscription
    2. Adds the Teams item (monthly or annual price based on billing_interval)
    3. Ends the trial immediately (trial_end="now") if the subscription is trialing
    4. Sets proration_behavior="create_prorations" (immediate invoice for the difference)
    5. Flips tenant.charter_eligible = False (permanent — D23)
    6. Updates tenant.current_subscription_tier_id to Teams
    7. Nulls tenant.free_period_ends_at (no longer in free period)
    8. Updates subscription row: product_plan_code, billing_interval, status_id→active

    The metered items (voice_overage, sms_overage) are preserved — they are
    shared across all tiers and should NOT be deleted.

    Args:
        db: Database session
        tenant_id: Tenant to upgrade
        billing_interval: "monthly" or "annual"

    Returns:
        {"psp_subscription_id", "new_tier_name", "billing_interval",
         "charter_eligible_forfeited"}

    Raises:
        ValueError: tenant is not Charter, no active subscription,
                    no payment method, or Stripe API error
    """
    from app.models.billing import Subscription, SubscriptionStatus
    from app.models.core import Tenant
    from app.models.subscription import SubscriptionTier
    from core.stripe_config import get_stripe_ids

    if billing_interval not in ("monthly", "annual"):
        raise ValueError("billing_interval must be 'monthly' or 'annual'")

    stripe = _get_stripe_client()
    ids = get_stripe_ids()

    # 1. Load tenant (tenant-scoped select — Rule 7.1)
    tenant = db.exec(select(Tenant).where(Tenant.id == tenant_id)).first()
    if not tenant:
        raise ValueError(f"Tenant {tenant_id} not found")

    # 2. Verify tenant is Charter
    if not tenant.charter_eligible:
        raise ValueError("Tenant is not a Charter member")

    charter_tier = db.exec(
        select(SubscriptionTier).where(SubscriptionTier.tier_name == "charter")
    ).first()
    if not charter_tier:
        raise ValueError("Charter tier not found")

    if tenant.current_subscription_tier_id != charter_tier.tier_id:
        raise ValueError("Tenant is not on the Charter tier")

    # 3. Load active subscription
    sub_row = db.exec(
        select(Subscription).where(
            Subscription.tenant_id == tenant_id,
            Subscription.is_active == True,
        )
    ).first()
    if not sub_row or not sub_row.psp_subscription_id:
        raise ValueError("No active subscription found")

    # 4. Verify payment method on file
    customer = stripe.Customer.retrieve(
        tenant.stripe_customer_id,
        expand=["invoice_settings.default_payment_method"],
    )
    if not customer.get("invoice_settings", {}).get("default_payment_method"):
        raise ValueError(
            "No payment method on file. Add a card before upgrading."
        )

    # 5. Retrieve Stripe subscription to find the Charter item
    stripe_sub = stripe.Subscription.retrieve(sub_row.psp_subscription_id)
    charter_price_id = ids["prices"]["price_charter_monthly"]
    teams_price_id = (
        ids["prices"]["price_teams_annual"]
        if billing_interval == "annual"
        else ids["prices"]["price_teams_monthly"]
    )

    charter_item = None
    for item in stripe_sub["items"]["data"]:
        if item["price"]["id"] == charter_price_id:
            charter_item = item
            break

    if not charter_item:
        raise ValueError("Charter price item not found on subscription")

    # 6. Build modify call
    modify_kwargs = {
        "items": [
            {"id": charter_item["id"], "deleted": True},
            {"price": teams_price_id, "quantity": 1},
        ],
        "proration_behavior": "create_prorations",
    }

    # End trial if active
    if stripe_sub.status == "trialing":
        modify_kwargs["trial_end"] = "now"

    # 7. Call Stripe
    updated_sub = stripe.Subscription.modify(
        sub_row.psp_subscription_id,
        **modify_kwargs,
    )

    # 8. Update tenant (AFTER Stripe success)
    teams_tier = db.exec(
        select(SubscriptionTier).where(SubscriptionTier.tier_name == "teams")
    ).first()

    tenant.charter_eligible = False  # D23 — permanent forfeiture
    tenant.current_subscription_tier_id = teams_tier.tier_id
    tenant.free_period_ends_at = None  # No longer in free period
    db.add(tenant)

    # 9. Update subscription row
    active_status = db.exec(
        select(SubscriptionStatus).where(
            SubscriptionStatus.code == "active",
            SubscriptionStatus.is_billing_active == True,
        )
    ).first()

    sub_row.product_plan_code = teams_tier.product_plan_code
    sub_row.billing_interval = billing_interval
    sub_row.trial_ends_at = None
    if active_status:
        sub_row.status_id = active_status.id
    db.add(sub_row)

    db.commit()

    logger.info(
        "Charter tenant %s upgraded to Teams (billing_interval=%s, "
        "charter_eligible=false, sub_id=%s)",
        tenant_id,
        billing_interval,
        updated_sub.id,
    )

    return {
        "psp_subscription_id": updated_sub.id,
        "new_tier_name": "teams",
        "billing_interval": billing_interval,
        "charter_eligible_forfeited": True,
    }
```

**Key implementation notes**:
- The Charter subscription has **3 items**: `price_charter_monthly` (quantity=1) + `price_voice_overage` (metered) + `price_sms_overage` (metered). The upgrade deletes only the charter_monthly item and adds the Teams item. The metered items are NOT in the `items` array → they are preserved automatically by Stripe.
- The `charter_eligible = False` flip happens **AFTER** the Stripe call succeeds. If Stripe fails, we don't forfeit eligibility.
- `trial_end="now"` is only set if the subscription is currently `trialing`. A Charter member who has already passed their trial (status `active` or `paused`) does not need this parameter.

**Intermediate unit test run**: `pytest -m unit --tb=short -q | tail -5`

---

## Task 2 — Request/Response Schemas

Add the schemas to `backend/api/routes/tenant_subscription.py` (inline with the existing schemas at the top of the file, around line 80-96) OR create a new `backend/api/schemas/subscription.py` file — your choice. The existing pattern in `tenant_subscription.py` uses inline schemas.

```python
class UpgradeFromCharterRequest(BaseModel):
    billing_interval: Literal["monthly", "annual"]


class UpgradeFromCharterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    psp_subscription_id: str
    new_tier_name: str
    billing_interval: str
    charter_eligible_forfeited: bool
```

**Note**: `Literal` is already imported at the top of `tenant_subscription.py` (line 8). `BaseModel` and `ConfigDict` are imported from `pydantic` (line 12).

**Intermediate unit test run**: `pytest -m unit --tb=short -q | tail -5`

---

## Task 3 — API Route: `POST /upgrade-from-charter` + `/test` twin

In `backend/api/routes/tenant_subscription.py`, add the upgrade endpoint. Place it after the existing `resume_subscription` endpoint (around line 645).

**Shared impl function** (follows the existing `_impl()` pattern in this file):

```python
def _upgrade_from_charter_impl(
    tenant_id: UUID,
    payload: UpgradeFromCharterRequest,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> UpgradeFromCharterResponse:
    """Shared logic for upgrading a Charter member to Teams.
    For TestUserContext: bypasses Stripe API calls and returns mock response."""
    if tenant_id != user_context.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "type": "https://errors.pilotfortrades.com/not-found",
                "title": "Tenant not found",
                "status": 404,
                "detail": "Cannot upgrade subscription for another tenant.",
            },
        )

    # For TestUserContext: skip Stripe API calls entirely
    if isinstance(user_context, TestUserContext):
        return UpgradeFromCharterResponse(
            psp_subscription_id="test_sub_mock_id",
            new_tier_name="teams",
            billing_interval=payload.billing_interval,
            charter_eligible_forfeited=True,
        )

    if isinstance(user_context, AuthenticatedUser):
        set_audit_context_sync(db, user_id=user_context.id)

    from services.stripe_subscriptions import upgrade_charter_to_teams

    try:
        result = upgrade_charter_to_teams(
            db=db,
            tenant_id=tenant_id,
            billing_interval=payload.billing_interval,
        )
    except ValueError as exc:
        msg = str(exc)
        # Determine status code from error message
        if "not a charter" in msg.lower() or "not on the charter tier" in msg.lower():
            code = status.HTTP_400_BAD_REQUEST
        elif "no active subscription" in msg.lower():
            code = status.HTTP_400_BAD_REQUEST
        elif "no payment method" in msg.lower():
            code = status.HTTP_400_BAD_REQUEST
        elif "not found" in msg.lower():
            code = status.HTTP_404_NOT_FOUND
        else:
            code = status.HTTP_502_BAD_GATEWAY

        raise HTTPException(
            status_code=code,
            detail={
                "type": "https://errors.pilotfortrades.com/charter-upgrade-error",
                "title": "Charter upgrade failed",
                "status": code,
                "detail": msg,
            },
        )

    return UpgradeFromCharterResponse(**result)
```

**Test endpoint** (register BEFORE authenticated — follows the existing pattern):

```python
@router.post(
    "/{tenant_id}/subscription/upgrade-from-charter/test",
    response_model=UpgradeFromCharterResponse,
    status_code=status.HTTP_200_OK,
)
def upgrade_from_charter_test(
    tenant_id: UUID,
    payload: UpgradeFromCharterRequest,
    db: Session = Depends(get_db),
):
    """Upgrade Charter to Teams (TEST ENDPOINT — no auth; Stripe bypassed)."""
    test_context = get_test_context()
    return _upgrade_from_charter_impl(tenant_id, payload, db, test_context)
```

**Authenticated endpoint**:

```python
@router.post(
    "/{tenant_id}/subscription/upgrade-from-charter",
    response_model=UpgradeFromCharterResponse,
    status_code=status.HTTP_200_OK,
)
def upgrade_from_charter(
    tenant_id: UUID,
    payload: UpgradeFromCharterRequest,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(
        require_permission("subscription.tier.change")
    ),
):
    """Upgrade a Charter member to the Teams plan. PERMANENT — forfeits the Charter rate.

    Deletes the Charter monthly item, adds the Teams item (monthly or annual),
    ends the trial if active, and permanently sets charter_eligible=false.

    RBAC: subscription.tier.change.
    """
    return _upgrade_from_charter_impl(tenant_id, payload, db, current_user)
```

**Important**: The test endpoint must be registered BEFORE the authenticated endpoint (FastAPI route ordering — the `/test` path must match before the parameterized path). Follow the existing pattern in this file where all `/test` endpoints come before their authenticated counterparts.

**Intermediate unit test run**: `pytest -m unit --tb=short -q | tail -5`

---

## Task 4 — Regenerate OpenAPI

After all tests pass:

```bash
cd <repo>/backend
source .venv/bin/activate
python export_openapi_json.py
```

Verify the new endpoints appear:

```bash
grep -A 5 "upgrade-from-charter" backend/openapi_schema_map.md
```

---

## Task 5 — Regenerate DB Model Map + Import Map

No model files are changed in this batch (no new SQLModel classes). However, if you add a new test file, regenerate the import map:

```bash
cd <repo>/backend && source .venv/bin/activate
python generate_app_import_map.py tests > app_model_imports.md
```

---

## Task 6 — Write Tests

Create `backend/tests/domains/subscriptions_usage/test_cb12_charter_upgrade.py`.

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
- Use `test_tenant` and `test_user` fixtures (never hardcoded UUIDs)
- Scope assertions by inserted IDs — never `assert len(all_rows) == N`
- Be placed in `backend/tests/domains/subscriptions_usage/`

**Test Resilience Rule (MANDATORY):**
- Never UPDATE or DELETE rows you did not INSERT in the current test.
- Never assert on total row counts for a table.
- The `db_session` fixture is the correct isolation mechanism (transaction rollback).

**Mock pattern for this batch**: Mock `stripe.Subscription.retrieve`, `stripe.Subscription.modify`, `stripe.Customer.retrieve`, and `_get_stripe_client()` to return fake objects. Mock `get_stripe_ids()` to return the test price IDs from `stripe_ids.test.json`. Use the `db_session` fixture for direct DB access.

**For Charter tenant setup in tests**: You need a tenant with `charter_eligible=True`, `current_subscription_tier_id` set to the Charter tier, and an active `subscription` row with `psp_subscription_id`. Use `test_tenant` and update its fields within the test transaction (the `db_session` fixture rolls back after each test). Alternatively, use `second_tenant` and set it up as a Charter member.

### Required Tests (minimum 14)

| Test | Description |
|---|---|
| `test_upgrade_charter_to_teams_monthly` | Valid Charter tenant, monthly interval → Charter item deleted, Teams item added, `charter_eligible=False`, tier updated, `free_period_ends_at=None`. |
| `test_upgrade_charter_to_teams_annual` | Valid Charter tenant, annual interval → uses `price_teams_annual`, `billing_interval="annual"`. |
| `test_upgrade_ends_trial_immediately` | Charter tenant in `trialing` status → `trial_end="now"` passed to `Subscription.modify()`. |
| `test_upgrade_preserves_metered_items` | After upgrade, the voice_overage + sms_overage items are still on the subscription (not deleted). |
| `test_upgrade_not_charter_tenant` | Tenant with `charter_eligible=False` → ValueError. |
| `test_upgrade_not_charter_tier` | Tenant on Starter tier → ValueError. |
| `test_upgrade_no_subscription` | No active subscription row → ValueError. |
| `test_upgrade_no_payment_method` | Stripe customer has no `default_payment_method` → ValueError. |
| `test_upgrade_invalid_billing_interval` | `billing_interval="weekly"` → ValueError. |
| `test_upgrade_stripe_error` | Stripe API raises → error propagates, `charter_eligible` NOT flipped (DB unchanged). |
| `test_endpoint_happy_path` | Authenticated Charter tenant → 200, response has `charter_eligible_forfeited=True`. |
| `test_endpoint_not_charter` | Non-Charter tenant → 400. |
| `test_endpoint_tenant_isolation` | `tenant_id != current_user.tenant_id` → 404. |
| `test_endpoint_test_twin` | Test endpoint bypasses Stripe, returns mock. |

**Mocking `stripe.Subscription.retrieve`**: Return a fake subscription object with `items.data` containing 3 items (charter_monthly, voice_overage, sms_overage). The charter item must have an `id` field (e.g., `"si_charter_123"`) and `price.id` matching `price_charter_monthly`.

**Mocking `stripe.Customer.retrieve`**: Return a fake customer with `invoice_settings.default_payment_method` set to `"pm_test_123"` (for happy path) or `None` (for the no-PM test).

**Mocking `stripe.Subscription.modify`**: Return a fake subscription object with `id="sub_test_456"` and `status="active"`.

---

## Final Verification

### Phase 1 — Unit Tests Only (run after each task group during development)

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=short -q 2>&1 | tail -10
```

All unit tests must pass before moving to the next task. Fix any unit failure before proceeding.

### Phase 2 — Lint (changed files only) + Full Suite (run once, at the very end, before DoD sign-off)

```bash
cd <repo>/backend
source .venv/bin/activate

# Lint + format gate (rules §23) — CHANGED FILES ONLY
CHANGED_PY=$(git diff --name-only --diff-filter=d HEAD -- '*.py' | sed 's|^backend/||')

if [ -n "$CHANGED_PY" ]; then
    ruff check --fix $CHANGED_PY
    ruff format $CHANGED_PY
    ruff check $CHANGED_PY
fi

# Full suite including integration tests
python -m pytest --tb=short -q 2>&1 | tail -10

# Batch-specific spot checks
python -m pytest tests/domains/subscriptions_usage/test_cb12_charter_upgrade.py -v 2>&1 | tail -20
grep -A 5 "upgrade-from-charter" backend/openapi_schema_map.md

echo "=== C-B12 PART A FINAL VERIFICATION COMPLETE ==="
```

> **Warning-clean is part of done.** `ruff` must report no remaining issues in your changed files.

> **Any failure in either phase must be fixed before the batch is declared done.**

---

## Definition of Done

- [ ] Pre-modification regression baseline captured (`X passed, Y failed`) using `pytest -m unit`
- [ ] Zero pre-existing unit failures confirmed before starting work (or confirmed with Tom)
- [ ] All MCP pre-work queries run — all 5 queries confirmed expected results
- [ ] All mandatory source files read before writing any code
- [ ] `upgrade_charter_to_teams()` service function added to `services/stripe_subscriptions.py`
- [ ] `UpgradeFromCharterRequest` + `UpgradeFromCharterResponse` schemas added
- [ ] `POST /{tenant_id}/subscription/upgrade-from-charter` + `/test` twin added to `api/routes/tenant_subscription.py`
- [ ] OpenAPI regenerated (1 new endpoint + test twin)
- [ ] `app_model_imports.md` regenerated (if new test file added)
- [ ] All new test files use `pytestmark` with `domain_subscriptions_usage` + `pytest.mark.unit`
- [ ] No module-level `TestClient` in any test file
- [ ] All new tests use `test_tenant` and `test_user` fixtures (no hardcoded UUIDs)
- [ ] All API errors follow RFC 7807 Problem Details format
- [ ] All mutation endpoints call `set_audit_context_sync()` before committing
- [ ] All DB-touching routes/`_impl()` are sync `def` — no `async def` on the blocking `Session`
- [ ] Only Pydantic v2 idioms used; every route has `response_model`
- [ ] `ruff check --fix && ruff format` run on changed files only — zero remaining issues
- [ ] **Phase 1**: All unit tests pass (`pytest -m unit`) — zero failures
- [ ] **Phase 2**: Full test suite passes (`pytest`) — zero failures, warning-clean
- [ ] Final test count (before → after) documented
- [ ] Completion Summary added to launch plan Appendix B

---

## Completion Summary

After all Definition of Done items are complete:

1. Add a **Completion Summary** subsection to `dev-docs/analysis/pilot-launch-plan.md` Appendix B using the format below.
2. **Handoff**: Run `python export_openapi_json.py` (already done in Task 4). The React Engineer (Part B) is gated on a UI design spec from pilot-web-ui-designer + Tom approval. Do NOT start Part B until the UI spec is approved.

```markdown
### C-B12 (Part A — Python Engineer) — Charter → Teams Upgrade Flow: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot Python Engineer
**Source design doc**: `batch-c-b12-design.md`
**Baseline**: X passed, Y failed
**Final**: X+N passed, Y failed (+N new tests)

#### What Was Accomplished

- [Brief description of key change 1]
- [Brief description of key change 2]

#### Files Changed / Created

| File | Action |
|---|---|
| `backend/path/to/file.py` | Created / Updated — [what changed] |
| ... | ... |

#### Tests Added

| Test File | Domain | Tests | All Pass |
|---|---|---|---|
| `tests/domains/subscriptions_usage/test_cb12_charter_upgrade.py` | `subscriptions_usage` | N | ✅ |
```

---

## After This Task — Next Step

**Part A is complete.** The React Engineer (Part B) is gated on:
1. A UI design spec from the pilot-web-ui-designer (must be Tom-approved before the React prompt is authored)
2. `pnpm sync-api-types` to regenerate TypeScript types from the new OpenAPI spec

Return to Pilot Architect mode to coordinate the UI design spec + React Engineer prompt.
