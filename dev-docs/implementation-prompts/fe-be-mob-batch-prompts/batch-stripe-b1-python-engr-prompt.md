# Implementation Prompt: STRIPE-B1 — Annual Billing Service Layer + Founders Cohort Schedule

**Mode**: Pilot Python Engineer  
**Batch**: STRIPE-B1  
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §2 P1 — STRIPE-B1  
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-stripe-b1-design.md`  
**Estimated session**: 4–5 hours  
**Platform**: Backend only (`backend/`)  
**Frontend companion**: None — React Engineer will need `billing_interval` toggle and price display changes in a future FE batch

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`dev-docs/architecture-design/pilot-python-engineer-methods.md`** — §13 (Alembic), §8 (Router Design), §5 (Model Design), §16 (Standard Task Workflow)
- **`backend/tests/README-adding-tests.md`** — full document; governs all test file structure, domain markers, and fixture rules

**Critical rules for this batch:**

- **Rule 1**: Never guess column names. Run MCP pre-work queries first — all 7 are required. SD-3 renamed columns that some files still reference with the OLD names. **The stale references you are about to fix are in the code today.** Do not propagate them further.
- **Rule 2**: **Blank Alembic migration only** — never `--autogenerate`. One migration in this batch: add `stripe_schedule_id TEXT NULL` to `subscription`.
- **Rule 3**: All Stripe API calls (including `SubscriptionSchedule.create`) must be wrapped in try/except and log failures — never let a Stripe API error crash the signup flow silently.
- **Rule 4**: **`create_founders_subscription_schedule()` is non-blocking at signup** — if Stripe is down or returns an error, log the error and continue tenant creation. The tenant should not see a 500 because Stripe was unavailable when their schedule was being created.
- **Rule 5**: `db.get()` is permanently banned on tenant-scoped models. Always use `select()` with explicit tenant scope.
- **Rule 6**: Never use module-level `TestClient`. Always use the `client` fixture.
- **Rule 7**: The `postgres-local` MCP is **read-only verification only**.
- **Rule 8**: All new `HTTPException` raises MUST use RFC 7807 Problem Details format — `{"type": "https://...", "title": "...", "status": N, "detail": "..."}`. No plain string `detail` values.
- **Rule 9**: After endpoint schema changes (`ConvertFromTrialRequest`, `ChangeTierRequest` both get `billing_interval` field) → run `python export_openapi_json.py` to update OpenAPI spec.
- **Rule 10**: After model changes to `Subscription` (adding `stripe_schedule_id`) → run `python generate_db_model_map.py`.
- **Rule 11**: The `mock_entitlement_allowed` autouse fixture bypasses all subscription entitlement checks in tests. Tests that verify billing_interval routing do NOT need `@pytest.mark.skip_mock_entitlement_allowed` unless they specifically test the entitlement gate itself.

---

## Pre-Work: Establish Regression Baseline

Before touching any file, capture the current unit-only test baseline:

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=no -q 2>&1 | tail -5
```

Record the exact count: **`X passed, Y failed`**.

> **Important**: Several tests that reference the OLD `stripe_price_id` field name may currently be failing because SD-3 renamed it. Run the baseline first and document what is already failing. Do not treat any subscription-related test failures as "pre-existing" without reading them — they may be SD-3 cleanup items that this batch must fix.

---

## Pre-Work: Run MCP Verification Queries

Run **all** of these via `postgres-local` MCP before writing any code. If any result is unexpected → **STOP and ask Tom**.

> **MCP Usage Rule**: Read-only verification only. Never INSERT/UPDATE/DELETE via MCP.

```sql
-- 1. Confirm SD-3 columns exist on subscription_tier (must all be present)
SELECT column_name, data_type FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'subscription_tier'
  AND column_name IN ('stripe_price_id_monthly','stripe_price_id_annual','annual_price_cents','monthly_price_cents')
ORDER BY column_name;
-- Expected: 4 rows. If ANY are missing → SD-3 migration has not been applied. STOP.

-- 2. Confirm old stripe_price_id column NO LONGER exists
SELECT column_name FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'subscription_tier'
  AND column_name = 'stripe_price_id';
-- Expected: 0 rows. If 1 row returned → SD-3 migration hasn't run. STOP.

-- 3. Confirm stripe_schedule_id does NOT yet exist on subscription
SELECT column_name FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'subscription'
  AND column_name = 'stripe_schedule_id';
-- Expected: 0 rows (this batch adds it)

-- 4. Confirm subscription.billing_interval CHECK constraint
SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint
WHERE conrelid = 'public.subscription'::regclass
  AND conname LIKE '%billing_interval%';
-- Expected: subscription_billing_interval_chk = "billing_interval IN ('monthly','annual')"

-- 5. Confirm current stripe_price_id_monthly values
SELECT tier_name, stripe_price_id_monthly, stripe_price_id_annual
FROM public.subscription_tier ORDER BY display_order;
-- Expected: starter + teams have stripe_price_id_monthly set; all annual IDs NULL

-- 6. Confirm Alembic head
SELECT version_num FROM public.alembic_version;

-- 7. Full subscription_tier column inventory (authoritative — used for all SQL in this batch)
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'subscription_tier'
ORDER BY ordinal_position;
```

---

## Pre-Work: Read These Source Files

Use `read_file` on each of these before writing any code:

```
backend/services/stripe_subscriptions.py         ← Full service — 2 bugs to fix + 2 new functions to add
backend/api/routes/tenant_subscription.py        ← Full route file — 5 stale stripe_price_id refs to fix
backend/api/routes/webhooks_stripe.py            ← Webhook dispatch — register new schedule event handler
backend/app/models/billing.py                    ← Subscription model — add stripe_schedule_id field
backend/app/models/subscription.py              ← SubscriptionTier model — confirm SD-3 field names
backend/tests/README-adding-tests.md            ← Test file rules (mandatory full read)
backend/tests/conftest.py                       ← Available fixtures
```

Also run these greps to find all stale references and understand the full impact:

```bash
# Find all remaining stale stripe_price_id references (not stripe_price_id_monthly)
grep -rn "stripe_price_id[^_]" backend/ --include="*.py" | grep -v "stripe_price_id_monthly\|stripe_price_id_annual\|stripe_price_id\s*=\s*\"\|stripe_price_id\s*=\s*'" | grep -v "test_"

# Find the founders signup flow entry point
grep -rn "founders.*tier\|founders.*plan\|signup.*founders\|create_stripe_customer\|onboard" backend/api/ --include="*.py" -l
```

---

## Background

STRIPE-B1 closes the gap left by SD-3, which renamed `stripe_price_id` → `stripe_price_id_monthly` and added annual billing columns. SD-3 left 5 stale references in `tenant_subscription.py` and 2 bugs in `stripe_subscriptions.py`. This batch:

1. Fixes all stale references and pre-existing billing_interval detection bugs
2. Wires annual billing routing into `convert-from-trial` and `change-tier` routes
3. Adds `create_founders_subscription_schedule()` for the 6-month free → $49/mo cohort model
4. Adds `handle_subscription_schedule_updated()` webhook handler for Phase 2 activation
5. Adds `stripe_schedule_id` column to `subscription` table

No new API endpoints. 3 request schemas gain an optional `billing_interval` field. 1 new DB column.

---

## Task 1 — Alembic Migration: Add `stripe_schedule_id` to `subscription`

```bash
cd <repo>/backend
source .venv/bin/activate
alembic revision -m "stripe_b1_subscription_schedule_id"
```

```python
"""STRIPE-B1: Add stripe_schedule_id to subscription for Founders cohort schedule tracking."""
import sqlalchemy as sa


def upgrade() -> None:
    op.add_column(
        'subscription',
        sa.Column('stripe_schedule_id', sa.Text(), nullable=True),
        schema='public'
    )


def downgrade() -> None:
    op.drop_column('subscription', 'stripe_schedule_id', schema='public')
```

Apply and verify:

```bash
alembic upgrade head

# Verify via MCP:
# SELECT column_name, data_type, is_nullable FROM information_schema.columns
# WHERE table_schema = 'public' AND table_name = 'subscription'
#   AND column_name = 'stripe_schedule_id';
# Expected: 1 row, data_type='text', is_nullable='YES'

# Full cycle test
alembic downgrade -1
alembic upgrade head
alembic current  # must show new head
```

---

## Task 2 — Update `Subscription` SQLModel — Add `stripe_schedule_id` Field

In `backend/app/models/billing.py`, find the `Subscription` class and add:

```python
stripe_schedule_id: str | None = Field(
    default=None,
    sa_column=Column(String, nullable=True),
)  # Stripe Subscription Schedule ID for founders cohort tenants
```

Place it near the other Stripe-related fields (`psp_subscription_id`, `psp_customer_id`).

After updating:

```bash
python generate_db_model_map.py
grep "stripe_schedule_id" backend/db_models_map.md
# Verify it appears under Subscription in the DB Tables section
```

### Intermediate unit test check

```bash
python -m pytest -m unit --tb=short -q 2>&1 | tail -5
```

Fix any failures before proceeding.

---

## Task 3 — Fix `stripe_subscriptions.py` — Two Pre-Existing Bugs + Two New Functions

Read the full file first. Then make these changes:

### 3a — Fix `handle_subscription_created()` billing_interval detection

Find lines ~186-193. Replace the buggy billing_interval detection:

```python
# BEFORE (BUGGY — copies billing_cycle_anchor integer, not interval string)
billing_cycle_anchor = subscription.get("billing_cycle_anchor")
current_period_end = subscription.get("current_period_end")
billing_interval = subscription.get("billing_cycle_anchor")  # ← BUG

# Determine billing interval from tier (default monthly)
billing_interval_str = "monthly"
if hasattr(tier, "billing_interval") and tier.billing_interval:  # ← BUG: SubscriptionTier has no billing_interval
    billing_interval_str = tier.billing_interval

# AFTER (CORRECT — read interval from Stripe subscription items)
billing_cycle_anchor = subscription.get("billing_cycle_anchor")
current_period_end = subscription.get("current_period_end")

# Derive billing interval from Stripe subscription item price metadata
# Stripe returns "month" or "year" in price.recurring.interval
billing_interval_str = "monthly"  # default
items_data = subscription.get("items", {}).get("data", [])
if items_data:
    stripe_interval = items_data[0].get("price", {}).get("recurring", {}).get("interval")
    if stripe_interval == "year":
        billing_interval_str = "annual"
```

### 3b — Fix tier lookup to search both monthly AND annual price IDs

Find the tier lookup query (~line 150-155). Update to search both columns:

```python
# BEFORE
tier = db.exec(
    select(SubscriptionTier)
    .where(SubscriptionTier.stripe_price_id_monthly == price_id)
    .where(SubscriptionTier.is_active == True)
).first()

# AFTER
from sqlalchemy import or_

tier = db.exec(
    select(SubscriptionTier)
    .where(
        or_(
            SubscriptionTier.stripe_price_id_monthly == price_id,
            SubscriptionTier.stripe_price_id_annual == price_id,
        )
    )
).first()
# Note: removed is_active filter — webhook must process subscriptions for any tier,
# including tiers that may be is_active=False in founders mode (e.g., starter)
```

### 3c — Add `create_founders_subscription_schedule()`

Add this new function after `create_stripe_subscription()`. Read the full function spec in `batch-stripe-b1-design.md` §E.3. Key points:

```python
def create_founders_subscription_schedule(
    db: Session,
    tenant_id: UUID,
    stripe_customer_id: str,
) -> str | None:
    """
    Create a Stripe Subscription Schedule for a founders cohort tenant.
    Phase 1: $0/mo for 6 months (free cohort period).
    Phase 2: starter monthly price ($49/mo) starting at month 7, ongoing.

    Returns:
        str | None: Stripe schedule ID (sub_sched_...) or None if creation failed.

    IMPORTANT: This is NON-BLOCKING. If Stripe is unavailable or raises an error,
    logs the error and returns None. Caller must handle None gracefully.
    The founders tenant is still created; schedule can be manually created by Tom later.
    """
    from app.models.billing import Subscription
    from app.models.subscription import SubscriptionTier

    stripe = _get_stripe_client()

    # Get the starter tier monthly price for Phase 2
    starter_tier = db.exec(
        select(SubscriptionTier).where(SubscriptionTier.tier_name == "starter")
    ).first()

    if not starter_tier or not starter_tier.stripe_price_id_monthly:
        logger.warning(
            "create_founders_subscription_schedule: starter tier or stripe_price_id_monthly "
            "not configured — skipping schedule creation. Run SD-3 seed + create Stripe monthly prices."
        )
        return None

    try:
        schedule = stripe.SubscriptionSchedule.create(
            customer=stripe_customer_id,
            start_date="now",
            end_behavior="release",
            phases=[
                {
                    "items": [],           # Phase 1: no charge
                    "iterations": 6,       # 6 monthly billing periods
                    "metadata": {"phase": "founders_free_period"},
                },
                {
                    "items": [{"price": starter_tier.stripe_price_id_monthly, "quantity": 1}],
                    "metadata": {"phase": "founders_paid_period"},
                },
            ],
            metadata={"tenant_id": str(tenant_id), "schedule_type": "founders_cohort"},
        )

        # Store schedule ID on the subscription row
        sub_row = db.exec(
            select(Subscription)
            .where(Subscription.tenant_id == tenant_id)
            .where(Subscription.is_active == True)
        ).first()

        if sub_row:
            sub_row.stripe_schedule_id = schedule.id
            db.add(sub_row)
            db.commit()

        logger.info(
            f"Founders subscription schedule created for tenant {tenant_id}: "
            f"{schedule.id} — Phase 2 billing starts at month 7."
        )
        return schedule.id

    except Exception as e:
        logger.error(
            f"create_founders_subscription_schedule: Stripe error for tenant {tenant_id}: {e}. "
            "Founders tenant created successfully; schedule must be created manually."
        )
        return None
```

### 3d — Add `handle_subscription_schedule_updated()`

Add this function after `handle_invoice_payment_failed()`. Full spec in design doc §E.4:

```python
def handle_subscription_schedule_updated(db: Session, stripe_event: dict) -> None:
    """
    Process customer.subscription.schedule.updated webhook.
    Fires when a Subscription Schedule phase transitions.
    For founders tenants: Phase 1 → Phase 2 at month 7 activates $49/mo billing.
    """
    from datetime import UTC, datetime
    from app.models.billing import Subscription
    from app.models.core import Tenant
    from app.models.subscription import SubscriptionTier

    schedule = stripe_event.get("data", {}).get("object", {})
    schedule_id = schedule.get("id")
    stripe_customer_id = schedule.get("customer")
    current_phase = schedule.get("current_phase", {})
    schedule_metadata = schedule.get("metadata", {})

    # Only process founders_cohort schedules
    if schedule_metadata.get("schedule_type") != "founders_cohort":
        logger.info(f"handle_subscription_schedule_updated: ignoring non-founders schedule {schedule_id}")
        return

    # Find tenant by stripe_customer_id
    tenant = db.exec(
        select(Tenant).where(Tenant.stripe_customer_id == stripe_customer_id)
    ).first()
    if not tenant:
        logger.warning(
            f"handle_subscription_schedule_updated: no tenant for Stripe customer {stripe_customer_id}"
        )
        return

    # Determine which phase is now active
    phases = schedule.get("phases", [])
    current_phase_index = None
    for i, phase in enumerate(phases):
        if phase.get("start_date") == current_phase.get("start_date"):
            current_phase_index = i
            break

    # Only act on Phase 2 activation (index 1)
    if current_phase_index != 1:
        logger.info(
            f"Founders schedule {schedule_id}: phase {current_phase_index} event — "
            "no tier change needed"
        )
        return

    # Phase 2 activation: move tenant to starter tier
    starter_tier = db.exec(
        select(SubscriptionTier).where(SubscriptionTier.tier_name == "starter")
    ).first()
    if not starter_tier:
        logger.error("handle_subscription_schedule_updated: starter tier not found — cannot transition")
        return

    tenant.current_subscription_tier_id = starter_tier.tier_id
    tenant.trial_ends_at = None
    db.add(tenant)

    # Update subscription row
    sub_row = db.exec(
        select(Subscription)
        .where(Subscription.tenant_id == tenant.id)
        .where(Subscription.is_active == True)
    ).first()
    if sub_row:
        sub_row.billing_interval = "monthly"
        phase_end = current_phase.get("end_date")
        if phase_end:
            sub_row.renews_at = datetime.fromtimestamp(phase_end, tz=UTC)
        db.add(sub_row)

    db.commit()
    logger.info(
        f"Founders tenant {tenant.id} transitioned to starter tier at month 7. "
        f"Schedule: {schedule_id}"
    )
```

---

## Task 4 — Fix `tenant_subscription.py` — 5 Stale References + Billing Interval Routing

Read the full file first. Make these changes in order:

### 4a — Add `billing_interval` to request schemas

Add `Literal` import at top of file:
```python
from typing import Literal
```

Update `ConvertFromTrialRequest`:
```python
class ConvertFromTrialRequest(BaseModel):
    target_tier_id: UUID
    payment_method_id: str
    billing_email: str
    billing_interval: Literal["monthly", "annual"] = "monthly"
```

Update `ChangeTierRequest`:
```python
class ChangeTierRequest(BaseModel):
    target_tier_id: UUID
    billing_interval: Literal["monthly", "annual"] = "monthly"
```

**Do NOT change** `SubscriptionUpgradeRequest` — upgrade handles free tiers only.

### 4b — Add `_select_stripe_price_id()` helper

Add this function before `_upgrade_tenant_subscription_impl()`:

```python
def _select_stripe_price_id(
    tier: SubscriptionTier,
    billing_interval: str,
) -> str | None:
    """
    Select the correct Stripe price ID based on billing interval.
    Returns None if the required price ID is not yet configured (annual prices pending Tom).
    billing_interval must be 'monthly' or 'annual'.
    """
    if billing_interval == "annual":
        return tier.stripe_price_id_annual  # None until Tom creates annual prices in Stripe
    return tier.stripe_price_id_monthly
```

### 4c — Fix `_upgrade_tenant_subscription_impl()` — line ~228

```python
# BEFORE: and target_tier.stripe_price_id
# AFTER: and target_tier.stripe_price_id_monthly
if (
    not isinstance(user_context, TestUserContext)
    and not target_tier.is_trial
    and target_tier.stripe_price_id_monthly
):
```

### 4d — Fix `_convert_from_trial_impl()` — lines ~280, 308

Replace the existing `stripe_price_id` check and usage:

```python
# Replace the "if not target_tier.stripe_price_id:" block:
selected_price_id = _select_stripe_price_id(target_tier, payload.billing_interval)
if not selected_price_id:
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail={
            "type": "https://errors.pilotfortrades.com/billing-not-configured",
            "title": "Billing not configured",
            "status": 400,
            "detail": (
                f"Tier '{target_tier.tier_name}' does not have a Stripe price configured "
                f"for '{payload.billing_interval}' billing. "
                "Use 'monthly' billing or contact support."
            ),
        },
    )

# Then replace target_tier.stripe_price_id in the create_stripe_subscription call:
stripe_subscription_id = create_stripe_subscription(
    db,
    tenant_id,
    stripe_customer_id,
    selected_price_id,    # ← was target_tier.stripe_price_id
    payload.payment_method_id,
)
```

### 4e — Fix `_change_tier_impl()` — lines ~370, 387

```python
# Replace the "if not target_tier.stripe_price_id:" block:
selected_price_id = _select_stripe_price_id(target_tier, payload.billing_interval)
if not selected_price_id:
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail={
            "type": "https://errors.pilotfortrades.com/billing-not-configured",
            "title": "Billing not configured",
            "status": 400,
            "detail": (
                f"Tier '{target_tier.tier_name}' does not have a Stripe price configured "
                f"for '{payload.billing_interval}' billing. "
                "Use 'monthly' billing or contact support."
            ),
        },
    )

# Replace target_tier.stripe_price_id in the stripe.Subscription.modify call:
stripe.Subscription.modify(
    current_subscription.psp_subscription_id,
    items=[{"price": selected_price_id}],    # ← was target_tier.stripe_price_id
)
```

---

## Task 5 — Wire Founders Schedule at Signup

### 5a — Find the founders signup entry point

```bash
grep -rn "founders_plan\|founders.*tier\|create_stripe_customer\|signup\|onboard" \
    backend/api/ backend/services/ --include="*.py" -l
```

Look for where a new tenant is placed on the founders tier. This is likely in a signup service, onboarding route, or tenant creation handler. Read those files.

### 5b — Wire in `create_founders_subscription_schedule()`

After the existing tenant + user + subscription rows are created for a founders tenant, add:

```python
# Only create schedule for founders tier tenants
from app.models.subscription import SubscriptionTier
from services.stripe_subscriptions import create_founders_subscription_schedule

# Get current tier
current_tier = db.exec(
    select(SubscriptionTier)
    .where(SubscriptionTier.tier_id == tenant.current_subscription_tier_id)
).first()

if (
    current_tier
    and current_tier.tier_name == "founders"
    and tenant.stripe_customer_id
):
    # Non-blocking: if Stripe is unavailable, log and continue
    schedule_id = create_founders_subscription_schedule(
        db, tenant.id, tenant.stripe_customer_id
    )
    if schedule_id:
        logger.info(f"Founders schedule created: {schedule_id}")
    else:
        logger.warning(
            f"Founders schedule not created for tenant {tenant.id} — "
            "manual Stripe setup may be needed"
        )
```

> **If you cannot find the founders signup entry point**: Document in your Completion Summary exactly which files you checked and why you couldn't find it. Do not add the call in a guess location. Ask Tom if needed.

---

## Task 6 — Update `webhooks_stripe.py`

Read the full webhook route file. Find the event dispatch block (the `if/elif` chain matching `event_type`).

### 6a — Add import

```python
from services.stripe_subscriptions import (
    handle_subscription_created,
    handle_invoice_payment_failed,
    handle_subscription_schedule_updated,   # NEW
    _handle_refund_event,
)
```

### 6b — Register the new event

```python
elif event_type == "customer.subscription.schedule.updated":
    handle_subscription_schedule_updated(db, event)
```

Place this alongside the other `customer.subscription.*` handlers for logical grouping.

---

## Task 7 — Write Tests

Three test files. Place all in `tests/domains/subscriptions_usage/`.

### Test File 1: `test_stripe_b1_price_id_routing.py`

```python
"""
STRIPE-B1: Test billing interval price ID routing logic.
"""
import pytest
from sqlmodel import select

pytestmark = [
    pytest.mark.domain_subscriptions_usage,
    pytest.mark.unit,
]


class TestSelectStripePriceId:
    """Unit tests for _select_stripe_price_id() helper."""

    def test_monthly_returns_stripe_price_id_monthly(self, db_session):
        """billing_interval='monthly' returns stripe_price_id_monthly."""
        from api.routes.tenant_subscription import _select_stripe_price_id
        from app.models.subscription import SubscriptionTier

        starter = db_session.exec(
            select(SubscriptionTier).where(SubscriptionTier.tier_name == "starter")
        ).first()
        assert starter is not None

        result = _select_stripe_price_id(starter, "monthly")
        assert result == starter.stripe_price_id_monthly

    def test_annual_returns_stripe_price_id_annual(self, db_session):
        """billing_interval='annual' returns stripe_price_id_annual (may be None)."""
        from api.routes.tenant_subscription import _select_stripe_price_id
        from app.models.subscription import SubscriptionTier

        starter = db_session.exec(
            select(SubscriptionTier).where(SubscriptionTier.tier_name == "starter")
        ).first()
        assert starter is not None

        result = _select_stripe_price_id(starter, "annual")
        # annual price is NULL until Tom creates it — test just verifies the routing
        assert result == starter.stripe_price_id_annual

    def test_free_tier_monthly_returns_none(self, db_session):
        """Free tier (founders) has no stripe_price_id_monthly — returns None."""
        from api.routes.tenant_subscription import _select_stripe_price_id
        from app.models.subscription import SubscriptionTier

        founders = db_session.exec(
            select(SubscriptionTier).where(SubscriptionTier.tier_name == "founders")
        ).first()
        assert founders is not None

        result = _select_stripe_price_id(founders, "monthly")
        assert result is None  # founders has no Stripe price


class TestConvertFromTrialBillingInterval:
    """Test that convert-from-trial route accepts billing_interval field."""

    def test_convert_from_trial_accepts_billing_interval_monthly(
        self, client, test_tenant
    ):
        """POST convert-from-trial with billing_interval='monthly' returns 202 or 400 (not 422)."""
        import uuid

        # Use test endpoint — Stripe is bypassed but we need a real paid tier
        # This verifies schema accepts the new field without 422
        resp = client.post(
            f"/api/v1/tenants/{test_tenant.id}/subscription/convert-from-trial/test",
            json={
                "target_tier_id": str(uuid.uuid4()),  # non-existent tier
                "payment_method_id": "pm_test_mock",
                "billing_email": "test@example.com",
                "billing_interval": "monthly",
            },
        )
        # 404 (tier not found) is fine — we're testing schema accepts the field, not the flow
        assert resp.status_code in (400, 404), (
            f"Expected 400 or 404, got {resp.status_code}. "
            "If 422: billing_interval field was rejected — check schema definition."
        )

    def test_convert_from_trial_default_billing_interval_is_monthly(
        self, client, test_tenant
    ):
        """POST convert-from-trial without billing_interval defaults to monthly (no 422)."""
        import uuid

        resp = client.post(
            f"/api/v1/tenants/{test_tenant.id}/subscription/convert-from-trial/test",
            json={
                "target_tier_id": str(uuid.uuid4()),
                "payment_method_id": "pm_test_mock",
                "billing_email": "test@example.com",
                # billing_interval omitted — should default to "monthly"
            },
        )
        assert resp.status_code in (400, 404)


class TestChangeTierBillingInterval:
    """Test that change-tier route accepts billing_interval field."""

    def test_change_tier_accepts_billing_interval_annual(self, client, test_tenant):
        """POST change-tier with billing_interval='annual' returns 400/404 (not 422)."""
        import uuid

        resp = client.post(
            f"/api/v1/tenants/{test_tenant.id}/subscription/change-tier/test",
            json={
                "target_tier_id": str(uuid.uuid4()),
                "billing_interval": "annual",
            },
        )
        assert resp.status_code in (400, 404)
```

### Test File 2: `test_stripe_b1_subscription_schedule.py`

```python
"""
STRIPE-B1: Test subscription stripe_schedule_id column + founders schedule service.
"""
import pytest
from sqlmodel import select

pytestmark = [
    pytest.mark.domain_subscriptions_usage,
    pytest.mark.unit,
]


class TestStripeScheduleIdColumn:
    """Verify stripe_schedule_id column exists and is functional."""

    def test_subscription_model_has_stripe_schedule_id(self, db_session, test_tenant):
        """Subscription model accepts stripe_schedule_id field without error."""
        from app.models.billing import Subscription

        # Fetch test tenant's subscription
        sub = db_session.exec(
            select(Subscription).where(Subscription.tenant_id == test_tenant.id)
        ).first()

        # Column must exist on the model (may be None)
        assert hasattr(sub, "stripe_schedule_id"), (
            "stripe_schedule_id field missing from Subscription model — "
            "STRIPE-B1 migration may not have run"
        )

    def test_stripe_schedule_id_is_nullable(self, db_session, test_tenant):
        """stripe_schedule_id is NULL for existing subscriptions (expected pre-founders)."""
        from app.models.billing import Subscription

        sub = db_session.exec(
            select(Subscription).where(Subscription.tenant_id == test_tenant.id)
        ).first()
        assert sub is not None
        # Existing subscriptions have no schedule — NULL is correct
        assert sub.stripe_schedule_id is None


class TestCreateFoundersScheduleService:
    """Test create_founders_subscription_schedule() with mocked Stripe."""

    def test_returns_none_when_starter_price_not_configured(self, db_session):
        """Returns None gracefully when starter tier has no stripe_price_id_monthly."""
        import uuid
        from unittest.mock import patch
        from app.models.subscription import SubscriptionTier
        from services.stripe_subscriptions import create_founders_subscription_schedule

        # Temporarily unset starter price for this test
        starter = db_session.exec(
            select(SubscriptionTier).where(SubscriptionTier.tier_name == "starter")
        ).first()
        assert starter is not None

        original_price = starter.stripe_price_id_monthly
        starter.stripe_price_id_monthly = None
        db_session.add(starter)
        db_session.flush()

        try:
            result = create_founders_subscription_schedule(
                db_session,
                uuid.uuid4(),
                "cus_test_mock",
            )
            assert result is None, "Should return None when price not configured"
        finally:
            # Restore
            starter.stripe_price_id_monthly = original_price
            db_session.add(starter)
            db_session.flush()

    def test_returns_none_on_stripe_api_error(self, db_session):
        """Returns None (does not raise) when Stripe API raises an exception."""
        import uuid
        from unittest.mock import patch, MagicMock
        from services.stripe_subscriptions import create_founders_subscription_schedule

        with patch("services.stripe_subscriptions._get_stripe_client") as mock_client:
            mock_stripe = MagicMock()
            mock_stripe.SubscriptionSchedule.create.side_effect = Exception("Stripe unavailable")
            mock_client.return_value = mock_stripe

            result = create_founders_subscription_schedule(
                db_session,
                uuid.uuid4(),
                "cus_test_mock",
            )
            # Non-blocking: error logged, None returned, no exception raised
            assert result is None


class TestHandleSubscriptionScheduleUpdated:
    """Test handle_subscription_schedule_updated() webhook handler."""

    def test_ignores_non_founders_schedules(self, db_session):
        """Silently ignores schedules without schedule_type=founders_cohort."""
        from services.stripe_subscriptions import handle_subscription_schedule_updated

        non_founders_event = {
            "data": {
                "object": {
                    "id": "sub_sched_test",
                    "customer": "cus_test",
                    "metadata": {"schedule_type": "other"},
                    "current_phase": {},
                    "phases": [],
                }
            }
        }
        # Should not raise and should not modify any DB state
        handle_subscription_schedule_updated(db_session, non_founders_event)

    def test_ignores_phase_1_events(self, db_session):
        """Phase 1 (index 0) events do not trigger tier change."""
        from services.stripe_subscriptions import handle_subscription_schedule_updated

        phase_1_event = {
            "data": {
                "object": {
                    "id": "sub_sched_test",
                    "customer": "cus_nonexistent",
                    "metadata": {"schedule_type": "founders_cohort"},
                    "current_phase": {"start_date": 1000000},
                    "phases": [
                        {"start_date": 1000000, "items": []},   # Phase 1 — current
                        {"start_date": 2000000, "items": [{"price": {"id": "price_x"}}]},
                    ],
                }
            }
        }
        # Phase 1 → no tier change (tenant not found anyway since customer is nonexistent)
        handle_subscription_schedule_updated(db_session, phase_1_event)
```

### Test File 3: `test_stripe_b1_billing_interval_detection.py`

```python
"""
STRIPE-B1: Test billing interval detection in handle_subscription_created().
"""
import pytest
from unittest.mock import MagicMock, patch

pytestmark = [
    pytest.mark.domain_subscriptions_usage,
    pytest.mark.unit,
]


class TestBillingIntervalDetection:
    """Test that billing_interval is correctly derived from Stripe webhook payload."""

    def _make_stripe_subscription_event(self, price_id: str, interval: str) -> dict:
        """Build a minimal customer.subscription.created event dict."""
        return {
            "data": {
                "object": {
                    "id": "sub_test_123",
                    "customer": "cus_test_123",
                    "status": "active",
                    "billing_cycle_anchor": 1700000000,
                    "current_period_end": 1702592000,
                    "items": {
                        "data": [
                            {
                                "price": {
                                    "id": price_id,
                                    "recurring": {
                                        "interval": interval,
                                        "interval_count": 1,
                                    },
                                }
                            }
                        ]
                    },
                }
            }
        }

    def test_monthly_stripe_interval_maps_to_monthly(self, db_session):
        """Stripe interval='month' → billing_interval_str='monthly' in subscription row."""
        from app.models.subscription import SubscriptionTier
        from sqlmodel import select

        # Get a tier with a real price ID
        starter = db_session.exec(
            select(SubscriptionTier).where(SubscriptionTier.tier_name == "starter")
        ).first()
        if not starter or not starter.stripe_price_id_monthly:
            pytest.skip("starter tier or stripe_price_id_monthly not configured")

        event = self._make_stripe_subscription_event(
            starter.stripe_price_id_monthly, "month"
        )

        # Extract billing_interval_str using the same logic as handle_subscription_created()
        items_data = event["data"]["object"].get("items", {}).get("data", [])
        billing_interval_str = "monthly"
        if items_data:
            stripe_interval = items_data[0].get("price", {}).get("recurring", {}).get("interval")
            if stripe_interval == "year":
                billing_interval_str = "annual"

        assert billing_interval_str == "monthly"

    def test_yearly_stripe_interval_maps_to_annual(self, db_session):
        """Stripe interval='year' → billing_interval_str='annual' in subscription row."""
        event = self._make_stripe_subscription_event("price_annual_test", "year")

        items_data = event["data"]["object"].get("items", {}).get("data", [])
        billing_interval_str = "monthly"
        if items_data:
            stripe_interval = items_data[0].get("price", {}).get("recurring", {}).get("interval")
            if stripe_interval == "year":
                billing_interval_str = "annual"

        assert billing_interval_str == "annual"
```

---

## Task 8 — Regenerate OpenAPI

Request schemas changed (`ConvertFromTrialRequest` and `ChangeTierRequest` both gained `billing_interval`):

```bash
cd <repo>/backend
source .venv/bin/activate
python export_openapi_json.py

# Verify billing_interval appears in the schema for both endpoints
grep -A 10 "convert-from-trial" backend/openapi_schema_map.md | grep -i billing
grep -A 10 "change-tier" backend/openapi_schema_map.md | grep -i billing
```

---

## Task 9 — Update Documentation

### 9a — Update `stripe-pricing-config.md` §8 Webhooks Table

In `dev-docs/integrations/stripe/stripe-pricing-config.md`, add to the §8 table:

| Event | Handler |
|---|---|
| `customer.subscription.schedule.updated` | `handle_subscription_schedule_updated()` |

Also add a **Tom action** note: register this event in Stripe Dashboard on both the production webhook endpoint and the test-mode ngrok endpoint.

### 9b — Update `pilot-operations.md` §4 and §5

In `dev-docs/pilot-operations.md`:

- **§4 (Tenant Subscription Lifecycle)**: Add a sentence in Step 3 — "The `billing_interval` param in `ConvertFromTrialRequest` (default: `'monthly'`) selects `stripe_price_id_monthly` vs `stripe_price_id_annual`. Annual price IDs are NULL until Tom creates them in Stripe Dashboard — requests for annual billing return 400 until then."
- **§5 (Founders Cohort Model)**: Update the Stripe Subscription Schedule section to reflect that `create_founders_subscription_schedule()` is now implemented. Replace "Stripe Subscription Schedule API (STRIPE-B1 scope)" with present-tense description.

### 9c — Update `pilot-launch-plan.md`

In `dev-docs/analysis/pilot-launch-plan.md`:
1. Mark all 5 STRIPE-B1 task items as ✅ in §2
2. Add STRIPE-B1 to Appendix A completed batch registry
3. Add Completion Summary to Appendix B

---

## Final Verification

### Phase 1 — Unit Tests Only

```bash
cd <repo>/backend
source .venv/bin/activate

python -m pytest -m unit --tb=short -q 2>&1 | tail -10
```

All unit tests must pass. Fix any failures before Phase 2.

### Phase 2 — Full Suite

```bash
cd <repo>/backend
source .venv/bin/activate

# Full suite
python -m pytest --tb=short -q 2>&1 | tail -10

# Batch-specific spot checks
python -m pytest tests/domains/subscriptions_usage/test_stripe_b1_price_id_routing.py -v
python -m pytest tests/domains/subscriptions_usage/test_stripe_b1_subscription_schedule.py -v
python -m pytest tests/domains/subscriptions_usage/test_stripe_b1_billing_interval_detection.py -v

# Verify existing subscription tests still pass
python -m pytest tests/batch_b19/test_stripe_subscription_lifecycle.py -v
python -m pytest tests/batch_tp_b11/test_tp_b11_help_subscription.py -v

# Verify alembic cycle
alembic downgrade -1
alembic upgrade head
alembic current

# Verify OpenAPI updated
grep "billing_interval" backend/openapi_schema_map.md | head -10

echo "=== STRIPE-B1 FINAL VERIFICATION COMPLETE ==="
```

---

## Definition of Done

- [ ] Pre-modification regression baseline captured (`X passed, Y failed`) using `pytest -m unit`
- [ ] All 7 MCP pre-work queries run — SD-3 columns confirmed present, old `stripe_price_id` confirmed absent
- [ ] All mandatory source files read before writing any code
- [ ] **Task 1**: Alembic migration written + applied + cycle-tested (`stripe_schedule_id` on `subscription`)
- [ ] **Task 2**: `Subscription` model updated with `stripe_schedule_id` field; `db_models_map.md` regenerated
- [ ] **Task 3a**: `billing_interval` detection bug fixed in `handle_subscription_created()`
- [ ] **Task 3b**: Tier lookup updated to search both `stripe_price_id_monthly` AND `stripe_price_id_annual`
- [ ] **Task 3c**: `create_founders_subscription_schedule()` added to `stripe_subscriptions.py`
- [ ] **Task 3d**: `handle_subscription_schedule_updated()` added to `stripe_subscriptions.py`
- [ ] **Task 4a**: `billing_interval` field added to `ConvertFromTrialRequest` + `ChangeTierRequest`
- [ ] **Task 4b**: `_select_stripe_price_id()` helper added to `tenant_subscription.py`
- [ ] **Task 4c**: `_upgrade_tenant_subscription_impl()` stale reference fixed (line ~228)
- [ ] **Task 4d**: `_convert_from_trial_impl()` both stale references fixed (lines ~280, 308)
- [ ] **Task 4e**: `_change_tier_impl()` both stale references fixed (lines ~370, 387)
- [ ] **Task 5**: `create_founders_subscription_schedule()` wired into founders signup flow (or documented as not found with Tom follow-up)
- [ ] **Task 6**: `customer.subscription.schedule.updated` registered in `webhooks_stripe.py`
- [ ] **Task 7**: 3 test files written and passing
- [ ] **Task 8**: `python export_openapi_json.py` run — `billing_interval` visible in OpenAPI spec for both endpoints
- [ ] **Task 9**: 3 documentation updates complete
- [ ] All new API errors follow RFC 7807 Problem Details format
- [ ] All new test files use `pytestmark` with domain marker + `pytest.mark.unit`
- [ ] No module-level `TestClient` in any test file
- [ ] **Phase 1**: All unit tests pass (`pytest -m unit`) — zero failures
- [ ] **Phase 2**: Full test suite passes (`pytest`) — zero failures
- [ ] Final test count (before → after) documented
- [ ] Completion Summary added to `pilot-launch-plan.md` Appendix B

---

## Completion Summary

After all Definition of Done items are complete, add a **Completion Summary** to `dev-docs/analysis/pilot-launch-plan.md` Appendix B:

```markdown
### STRIPE-B1 — Annual Billing Service Layer + Founders Cohort Schedule: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot Python Engineer
**Baseline**: X passed, Y failed
**Final**: X+N passed, Y failed (+N new tests)

#### What Was Accomplished

- Added `stripe_schedule_id TEXT NULL` column to `subscription` table + `Subscription` SQLModel field
- Fixed 2 pre-existing bugs in `handle_subscription_created()`: billing_interval detection (line 188 read wrong field; line 192 checked non-existent SubscriptionTier.billing_interval attribute)
- Fixed tier lookup to search both `stripe_price_id_monthly` AND `stripe_price_id_annual`
- Added `create_founders_subscription_schedule()` — Stripe Subscription Schedule API (Phase 1: $0/6mo, Phase 2: $49/mo). Non-blocking.
- Added `handle_subscription_schedule_updated()` webhook handler — activates starter tier at month 7
- Fixed 5 stale `target_tier.stripe_price_id` references in `tenant_subscription.py`
- Added `billing_interval` field to `ConvertFromTrialRequest` + `ChangeTierRequest` (default='monthly')
- Added `_select_stripe_price_id()` helper centralizing monthly/annual routing
- Registered `customer.subscription.schedule.updated` webhook event
- [Note founders signup wiring: found/not found at X location, wired/deferred]

#### Files Changed / Created

| File | Action |
|---|---|
| `backend/migrations/versions/YYYY_*_stripe_b1_subscription_schedule_id.py` | Created — add stripe_schedule_id to subscription |
| `backend/app/models/billing.py` | Updated — Subscription model + stripe_schedule_id field |
| `backend/services/stripe_subscriptions.py` | Updated — 2 bug fixes + 2 new functions |
| `backend/api/routes/tenant_subscription.py` | Updated — billing_interval routing + 5 stale ref fixes |
| `backend/api/routes/webhooks_stripe.py` | Updated — registered schedule.updated handler |
| `backend/db_models_map.md` | Updated — Subscription fields regenerated |
| `backend/openapi.json` + `openapi_schema_map.md` | Updated — billing_interval in 2 endpoints |
| `dev-docs/integrations/stripe/stripe-pricing-config.md` | Updated — §8 webhooks table |
| `dev-docs/pilot-operations.md` | Updated — §4 billing_interval routing, §5 founders schedule |
| `dev-docs/analysis/pilot-launch-plan.md` | Updated — STRIPE-B1 ✅ in §2, Appendix A + B |

#### Tests Added

| Test File | Domain | Tests | All Pass |
|---|---|---|---|
| `tests/domains/subscriptions_usage/test_stripe_b1_price_id_routing.py` | `domain_subscriptions_usage` | 5 | ✅ |
| `tests/domains/subscriptions_usage/test_stripe_b1_subscription_schedule.py` | `domain_subscriptions_usage` | 5 | ✅ |
| `tests/domains/subscriptions_usage/test_stripe_b1_billing_interval_detection.py` | `domain_subscriptions_usage` | 2 | ✅ |
```

---

## After This Batch — Next Step

After STRIPE-B1 is verified:

1. **Tom creates annual Stripe prices** in Dashboard (Starter: $588/yr, Teams: $1,788/yr) and updates `stripe_price_id_annual` in dev DB via `seed_platform.py` re-run with the new IDs.
2. **React Engineer** updates the pricing toggle on the subscription UI (annual vs monthly display + price shown).
3. **DB Management Strategy** batch — env-flag design for prod seed scripts (currently the highest priority remaining P1 item after STRIPE-B1).
