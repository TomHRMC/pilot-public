# Implementation Prompt: C-B4 — Stripe Subscription Creation + Webhook Expansion + Usage Reporting

**Mode**: Pilot Python Engineer  
**Batch**: C-B4  
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §2.0 row 14i  
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-c-b4-design.md`  
**Estimated session**: 3–5 hours  
**Platform**: Backend only (`backend/`)  
**Frontend companion**: C-B5 (wizard step 4/5 conditional logic — depends on C-B4 service functions)

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
- **Rule 8**: All API error responses MUST follow RFC 7807 Problem Details format.
- **Rule 9**: Every mutation endpoint MUST call `set_audit_context_sync(db, user_id=user.id)` before committing.
- **Rule 11**: If ANY test fails during your work — even one that appears to be a pre-existing failure — **you must fix it before declaring the batch done**.
- **Rule 12 (sync routes)**: Every DB-touching route and `_impl()` is a plain `def` — never `async def`.
- **Rule 13 (Pydantic v2)**: Use v2 idioms only. `model_config = ConfigDict(...)`, `@field_validator`, `.model_dump()`. Money is always integer cents.
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

---

## Pre-Work: Run MCP Verification Queries

Run **all** of these via `postgres-local` MCP before writing any code. If any query returns unexpected results → **STOP and ask Tom**.

> **MCP Usage Rule**: The `postgres-local` MCP is for **read-only verification only**. Use it to confirm table names, column types, and existing data. Never use it to INSERT, UPDATE, or DELETE — all data changes go through the application code, seed scripts, or Alembic migrations. If a query fails or returns an error → STOP and ask Tom before proceeding.

```sql
-- 1. Verify subscription_tier columns (C-B2 added free_period_days, requires_payment_method, price_locked)
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'subscription_tier'
ORDER BY ordinal_position;

-- 2. Verify tenant columns (C-B2 added free_period_ends_at, charter_member_number, charter_eligible)
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'tenant'
ORDER BY ordinal_position;

-- 3. Verify subscription table columns (psp_subscription_id, status_id, billing_interval, trial_ends_at, is_active)
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'subscription'
ORDER BY ordinal_position;

-- 4. Verify subscription_status codes (must have: active, trialing, paused, canceled)
SELECT code, name, is_billing_active FROM subscription_status ORDER BY code;

-- 5. Verify charter tier has stripe_price_id_monthly set (from C-B3)
SELECT tier_name, stripe_price_id_monthly, free_period_days, requires_payment_method, price_locked
FROM subscription_tier WHERE tier_name = 'charter';

-- 6. Verify stripe_webhook_event_processed dedup table exists
SELECT column_name, data_type FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'stripe_webhook_event_processed'
ORDER BY ordinal_position;
```

---

## Pre-Work: Read These Source Files

Use `read_file` on each of these before writing any code:

```
backend/services/stripe_subscriptions.py          ← why: existing Stripe service — add new functions here
backend/api/routes/webhooks_stripe.py             ← why: existing webhook dispatcher — add 7 new event routes
backend/api/routes/tenant_subscription.py          ← why: existing subscription routes — add resume endpoint
backend/scripts/stripe_ids.test.json              ← why: the 14 Stripe object IDs this batch loads at runtime
backend/core/config.py                            ← why: STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET settings
backend/app/models/billing.py                      ← why: Subscription, SubscriptionStatus, StripeWebhookEventProcessed models
backend/app/models/subscription.py                 ← why: SubscriptionTier model
backend/app/models/core.py                        ← why: Tenant model (free_period_ends_at, charter_eligible)
backend/tests/conftest.py                          ← why: available fixtures (client, test_tenant, mock_cognito_jwt)
backend/db_models_map.md                           ← why: confirm model names and table mappings
```

Also run these grep commands to find related files:

```bash
grep -rn "handle_subscription\|handle_invoice\|_process_stripe_event" backend/ --include="*.py" -l
grep -rn "stripe_config\|stripe_ids\|get_stripe_ids" backend/ --include="*.py" -l
```

---

## Background / Context

C-B4 builds the Stripe subscription lifecycle for the Charter program. The Charter tier gives users 90 days free (no payment method required), then pauses the subscription if no card is added. This batch implements:

1. **`core/stripe_config.py`** — Runtime loader for `stripe_ids.{mode}.json` (created by C-B3's `stripe_bootstrap.py`)
2. **`create_charter_subscription()`** — Creates a trialing subscription with `trial_end` + `trial_settings.end_behavior.missing_payment_method: pause` + 3 items (charter monthly + 2 metered overage)
3. **`resume_subscription()`** — Resumes a paused subscription after PM addition (C-SPIKE-1 flow: attach PM → set default → `Subscription.resume()` → **check status**)
4. **`report_usage_event()`** — Reports Billing Meter events to Stripe with idempotency key
5. **7 new webhook handlers** — `trial_will_end`, `paused`, `resumed`, `deleted`, `invoice.paid`, `checkout.session.completed`, `payment_method.attached`
6. **`POST /api/v1/tenants/{tenant_id}/subscription/resume`** — New API endpoint + `/test` twin

**No DB migration** — all columns exist from C-B2 and B14. **No seed changes** — no schema changes.

### Sync-by-Design (rules §21)

This app is **synchronous by design**: FastAPI 0.135 runs plain `def` routes in a threadpool, and the SQLModel/SQLAlchemy 2.0 `Session` is the **blocking** psycopg2 driver.

- Every route/`_impl()`/service that touches the `Session` MUST be `def` (sync).
- Only use `async def` for a handler that *exclusively* `await`s genuinely non-blocking I/O and never touches the sync `Session`.
- The existing webhook handler (`stripe_webhook_handler`) is `async def` because it reads raw `request.body()` — but it dispatches to sync `_process_stripe_event()`. Keep this pattern.

---

## Task 1 — Create `core/stripe_config.py`

Create `backend/core/stripe_config.py` — a singleton loader for `stripe_ids.{mode}.json`.

**What to build:**

```python
"""
Runtime loader for Stripe object IDs.
Reads stripe_ids.{mode}.json at startup; provides singleton accessor.
Mode determined by STRIPE_SECRET_KEY prefix: sk_test_ → test, sk_live_ → live.
"""
from pathlib import Path
import json
import logging

logger = logging.getLogger(__name__)

_ids_cache: dict | None = None

def get_stripe_ids() -> dict:
    """
    Return the Stripe object ID mapping for the current mode.
    Structure matches stripe_ids.test.json:
    {
        "mode": "test",
        "products": {"prod_starter": "...", "prod_teams": "...", "prod_passthrough": "..."},
        "meters": {"meter_voice_minutes": "...", "meter_sms_segments": "..."},
        "prices": {"price_charter_monthly": "...", "price_voice_overage": "...", ...}
    }
    """
    global _ids_cache
    if _ids_cache is not None:
        return _ids_cache

    from core.config import settings
    mode = "test" if settings.STRIPE_SECRET_KEY.startswith("sk_test_") else "live"
    ids_file = Path(__file__).parent.parent / "scripts" / f"stripe_ids.{mode}.json"

    if not ids_file.exists():
        raise FileNotFoundError(f"Stripe IDs file not found: {ids_file}")

    _ids_cache = json.loads(ids_file.read_text())
    logger.info(f"Loaded Stripe IDs for {mode} mode: {len(_ids_cache.get('prices', {}))} prices")
    return _ids_cache
```

**Key points:**
- The file path is `backend/scripts/stripe_ids.{mode}.json` — relative to `core/stripe_config.py`, that's `Path(__file__).parent.parent / "scripts" / ...`
- `sk_test_` prefix → test mode, anything else → live mode
- Singleton cache — loaded once per process

**Intermediate test run:** `pytest -m unit --tb=short -q | tail -5`

---

## Task 2 — Add `create_charter_subscription()` to `stripe_subscriptions.py`

Add a new function that creates a Charter subscription with trial (no payment method required).

**What to build:**

```python
def create_charter_subscription(
    db: Session,
    tenant_id: UUID,
    stripe_customer_id: str,
    free_period_ends_at: datetime,
    charter_member_number: int | None = None,
) -> str:
    """
    Create a Charter subscription with trial (no payment method required).
    Uses trial_end + trial_settings.end_behavior.missing_payment_method: pause.
    3 items: charter_monthly (quantity=1) + voice_overage + sms_overage (metered).
    Returns: Stripe Subscription ID (sub_...).
    """
    from core.stripe_config import get_stripe_ids

    stripe = _get_stripe_client()
    ids = get_stripe_ids()

    sub = stripe.Subscription.create(
        customer=stripe_customer_id,
        items=[
            {"price": ids["prices"]["price_charter_monthly"], "quantity": 1},
            {"price": ids["prices"]["price_voice_overage"]},
            {"price": ids["prices"]["price_sms_overage"]},
        ],
        trial_end=int(free_period_ends_at.timestamp()),
        trial_settings={"end_behavior": {"missing_payment_method": "pause"}},
        payment_behavior="allow_incomplete",
        collection_method="charge_automatically",
        metadata={
            "tenant_id": str(tenant_id),
            "tier_code": "charter",
            "charter_member_number": str(charter_member_number) if charter_member_number else "",
        },
    )

    logger.info(
        f"Charter subscription created for tenant {tenant_id}: {sub.id} "
        f"(status: {sub.status}, trial_end: {free_period_ends_at})"
    )
    return sub.id
```

**Key points:**
- Uses `get_stripe_ids()` from Task 1 — no hardcoded price IDs
- `trial_end` is an absolute Unix timestamp (not `trial_period_days`)
- `trial_settings.end_behavior.missing_payment_method: "pause"` — subscription pauses if no PM at trial end
- 3 items: charter monthly (quantity=1) + 2 metered overage prices (no quantity — metered)
- `payment_behavior="allow_incomplete"` — allows creating with no PM
- The existing `create_stripe_subscription()` (old PM-required pattern) stays unchanged — it's used by the convert-from-trial flow for non-Charter tiers

**Intermediate test run:** `pytest -m unit --tb=short -q | tail -5`

---

## Task 3 — Add `resume_subscription()` to `stripe_subscriptions.py`

Add the resume flow from C-SPIKE-1. **This is the most critical function in the batch** — the C-SPIKE-1 research found that `Subscription.resume()` can return HTTP 200 with `status: "paused"` if the payment method fails.

**What to build:**

```python
class ResumeFailedError(Exception):
    """Subscription remained paused after resume — payment method may have failed."""
    pass

def resume_subscription(
    db: Session,
    tenant_id: UUID,
    stripe_payment_method_id: str,
) -> dict:
    """
    Resume a paused Charter subscription after PM addition.
    C-SPIKE-1 flow: attach PM → set default → Subscription.resume() → check status.
    Returns: {"psp_subscription_id": str, "status": str, "billing_cycle_anchor": int|None}
    Raises: ResumeFailedError if subscription stays paused after resume.
    """
    from app.models.billing import Subscription
    from app.models.core import Tenant

    stripe = _get_stripe_client()

    # 1. Load tenant
    tenant = db.exec(select(Tenant).where(Tenant.id == tenant_id)).first()
    if not tenant or not tenant.stripe_customer_id:
        raise ValueError(f"Tenant {tenant_id} not found or has no Stripe customer ID")

    # 2. Load active subscription
    sub_row = db.exec(
        select(Subscription).where(
            Subscription.tenant_id == tenant_id,
            Subscription.is_active == True,
        )
    ).first()
    if not sub_row or not sub_row.psp_subscription_id:
        raise ValueError(f"No active subscription found for tenant {tenant_id}")

    # 3. Verify Stripe subscription is paused
    stripe_sub = stripe.Subscription.retrieve(sub_row.psp_subscription_id)
    if stripe_sub.status != "paused":
        raise ValueError(
            f"Subscription {sub_row.psp_subscription_id} is not paused (status: {stripe_sub.status})"
        )

    # 4. Attach payment method to customer
    stripe.PaymentMethod.attach(
        stripe_payment_method_id,
        customer=tenant.stripe_customer_id,
    )

    # 5. Set as default payment method (REQUIRED before resume)
    stripe.Customer.modify(
        tenant.stripe_customer_id,
        invoice_settings={"default_payment_method": stripe_payment_method_id},
    )

    # 6. Resume the subscription
    resumed_sub = stripe.Subscription.resume(
        sub_row.psp_subscription_id,
        billing_cycle_anchor="now",
    )

    # 7. CRITICAL — check returned status (resume can silently fail!)
    if resumed_sub.status == "paused":
        logger.error(
            f"Resume failed for tenant {tenant_id}: subscription {sub_row.psp_subscription_id} "
            f"remains paused after resume — payment method may have failed"
        )
        raise ResumeFailedError(
            "Subscription remains paused after resume — payment method may have failed"
        )

    # 8. Update subscription status to active
    from app.models.billing import SubscriptionStatus
    active_status = db.exec(
        select(SubscriptionStatus)
        .where(SubscriptionStatus.code == "active")
        .where(SubscriptionStatus.is_billing_active == True)
    ).first()
    if active_status:
        sub_row.status_id = active_status.id
        db.add(sub_row)
        db.commit()

    logger.info(f"Subscription resumed for tenant {tenant_id}: {resumed_sub.id} (status: {resumed_sub.status})")

    return {
        "psp_subscription_id": resumed_sub.id,
        "status": resumed_sub.status,
        "billing_cycle_anchor": resumed_sub.billing_cycle_anchor,
    }
```

**Key points:**
- **Step 7 is the C-SPIKE-1 critical finding** — `Subscription.resume()` returns 200 but `status` can still be `"paused"` if the payment fails. Never assume resume succeeded.
- `billing_cycle_anchor="now"` starts a fresh billing cycle immediately
- The `ResumeFailedError` is a custom exception — the API endpoint catches it and returns 502

**Intermediate test run:** `pytest -m unit --tb=short -q | tail -5`

---

## Task 4 — Add `report_usage_event()` to `stripe_subscriptions.py`

Add Billing Meter event reporting. This is called from the voice session service and SMS service.

**What to build:**

```python
def report_usage_event(
    db: Session,
    tenant_id: UUID,
    event_name: str,          # "voice_minutes" or "sms_segments"
    identifier: str,           # idempotency key (e.g., voice_session.id or sms_message.id)
    value: int,                # minutes or segments
    timestamp: datetime,
) -> None:
    """
    Report a Billing Meter event to Stripe.
    Uses stripe.billing.MeterEvent.create() with identifier as idempotency key.
    Non-blocking: logs error and returns None on failure (usage data is best-effort).
    """
    from app.models.core import Tenant

    stripe = _get_stripe_client()

    # Get stripe_customer_id
    tenant = db.exec(select(Tenant).where(Tenant.id == tenant_id)).first()
    if not tenant or not tenant.stripe_customer_id:
        logger.warning(f"report_usage_event: tenant {tenant_id} has no stripe_customer_id — skipping")
        return

    try:
        stripe.billing.MeterEvent.create(
            event_name=event_name,
            identifier=identifier,      # idempotency key — REQUIRED
            payload={
                "stripe_customer_id": tenant.stripe_customer_id,
                "value": str(value),
            },
            timestamp=int(timestamp.timestamp()),
        )
        logger.debug(f"Meter event reported: {event_name}={value} for tenant {tenant_id} (id: {identifier})")
    except Exception as e:
        # Non-blocking — usage data is best-effort
        logger.error(f"Failed to report meter event {event_name} for tenant {tenant_id}: {e}")
```

**Key points:**
- `identifier` is the idempotency key — without it, a Celery retry double-bills the customer (spec §6.5)
- `payload.stripe_customer_id` maps the event to the Stripe customer
- `payload.value` must be a string (Stripe API requirement)
- Non-blocking: logs error and returns None on failure — usage reporting should never break the user's workflow
- Stripe meters usage but does not gate it — all soft/hard cap enforcement stays in the existing Pilot quota model

**Intermediate test run:** `pytest -m unit --tb=short -q | tail -5`

---

## Task 5 — Add 7 New Webhook Handler Functions to `stripe_subscriptions.py`

Add these functions to `backend/services/stripe_subscriptions.py`:

### 5a. `handle_subscription_trial_will_end()`

```python
def handle_subscription_trial_will_end(db: Session, stripe_event: dict) -> None:
    """customer.subscription.trial_will_end — fires 3 days before trial ends.
    Stub: log event. Full notification schedule (T-30/14/7/3/1) is C-B6."""
    sub = stripe_event.get("data", {}).get("object", {})
    logger.info(f"Trial will end for subscription {sub.get('id')} (tenant metadata: {sub.get('metadata', {})})")
    # C-B6 will add: Celery beat → email + push + in-app banner
```

### 5b. `handle_subscription_paused()`

```python
def handle_subscription_paused(db: Session, stripe_event: dict) -> None:
    """customer.subscription.paused — update subscription.status_id to 'paused'.
    Do NOT disable SMS if tenant_messaging_registration.status='active' (spec §6.8)."""
    from app.models.billing import Subscription, SubscriptionStatus

    sub = stripe_event.get("data", {}).get("object", {})
    stripe_sub_id = sub.get("id")
    if not stripe_sub_id:
        return

    # Find subscription row by psp_subscription_id
    sub_row = db.exec(
        select(Subscription).where(Subscription.psp_subscription_id == stripe_sub_id)
    ).first()
    if not sub_row:
        logger.warning(f"handle_subscription_paused: no subscription row for {stripe_sub_id}")
        return

    # Update status to 'paused'
    paused_status = db.exec(
        select(SubscriptionStatus).where(SubscriptionStatus.code == "paused")
    ).first()
    if paused_status:
        sub_row.status_id = paused_status.id
        db.add(sub_row)
        db.commit()

    logger.info(f"Subscription {stripe_sub_id} paused — tenant {sub_row.tenant_id} enters read-only paywall")
    # Entitlement enforcement (job/quote/invoice creation blocked) is handled by
    # the existing is_billing_active paywall — paused status has is_billing_active=false
```

### 5c. `handle_subscription_resumed()`

```python
def handle_subscription_resumed(db: Session, stripe_event: dict) -> None:
    """customer.subscription.resumed — update subscription.status_id to 'active'."""
    from app.models.billing import Subscription, SubscriptionStatus

    sub = stripe_event.get("data", {}).get("object", {})
    stripe_sub_id = sub.get("id")
    if not stripe_sub_id:
        return

    sub_row = db.exec(
        select(Subscription).where(Subscription.psp_subscription_id == stripe_sub_id)
    ).first()
    if not sub_row:
        logger.warning(f"handle_subscription_resumed: no subscription row for {stripe_sub_id}")
        return

    active_status = db.exec(
        select(SubscriptionStatus)
        .where(SubscriptionStatus.code == "active")
        .where(SubscriptionStatus.is_billing_active == True)
    ).first()
    if active_status:
        sub_row.status_id = active_status.id
        db.add(sub_row)
        db.commit()

    logger.info(f"Subscription {stripe_sub_id} resumed — tenant {sub_row.tenant_id} full access restored")
```

### 5d. `handle_subscription_deleted()`

```python
def handle_subscription_deleted(db: Session, stripe_event: dict) -> None:
    """customer.subscription.deleted — set tenant.charter_eligible=false permanently;
    update subscription.status_id to 'canceled'; audit."""
    from app.models.billing import Subscription, SubscriptionStatus
    from app.models.core import Tenant

    sub = stripe_event.get("data", {}).get("object", {})
    stripe_sub_id = sub.get("id")
    stripe_customer_id = sub.get("customer")
    if not stripe_sub_id or not stripe_customer_id:
        return

    # Find tenant by stripe_customer_id
    tenant = db.exec(
        select(Tenant).where(Tenant.stripe_customer_id == stripe_customer_id)
    ).first()
    if not tenant:
        logger.warning(f"handle_subscription_deleted: no tenant for customer {stripe_customer_id}")
        return

    # Set charter_eligible = false permanently
    tenant.charter_eligible = False
    db.add(tenant)

    # Update subscription status to 'canceled'
    sub_row = db.exec(
        select(Subscription).where(Subscription.psp_subscription_id == stripe_sub_id)
    ).first()
    if sub_row:
        canceled_status = db.exec(
            select(SubscriptionStatus).where(SubscriptionStatus.code == "canceled")
        ).first()
        if canceled_status:
            sub_row.status_id = canceled_status.id
            sub_row.is_active = False
            from datetime import UTC, datetime
            sub_row.canceled_at = datetime.now(UTC)
            db.add(sub_row)

    db.commit()
    logger.info(f"Subscription {stripe_sub_id} deleted — tenant {tenant.id} charter_eligible=false, subscription canceled")
```

### 5e. `handle_invoice_paid()`

```python
def handle_invoice_paid(db: Session, stripe_event: dict) -> None:
    """invoice.paid — clear dunning state (if any). Log payment success."""
    invoice = stripe_event.get("data", {}).get("object", {})
    stripe_sub_id = invoice.get("subscription")
    amount_paid = invoice.get("amount_paid", 0)

    logger.info(f"Invoice paid for subscription {stripe_sub_id}: ${amount_paid / 100:.2f}")
    # Dunning state clearing: if the subscription was in 'past_due' or 'unpaid' status,
    # update to 'active'. The customer.subscription.updated webhook may also fire.
    # For MVP, just log — dunning recovery is handled by the subscription.updated handler.
```

### 5f. `handle_checkout_session_completed()`

```python
def handle_checkout_session_completed(db: Session, stripe_event: dict) -> None:
    """checkout.session.completed — stub for C-B9 (10DLC setup).
    If metadata.purpose == 'a2p_10dlc_setup': log and return.
    C-B9 will implement the full Telnyx provisioning transition."""
    session = stripe_event.get("data", {}).get("object", {})
    purpose = session.get("metadata", {}).get("purpose")

    if purpose == "a2p_10dlc_setup":
        logger.info(f"Checkout session completed for 10DLC setup: {session.get('id')} — C-B9 will handle provisioning")
    else:
        logger.debug(f"Checkout session completed: {session.get('id')} (purpose: {purpose})")
```

### 5g. `handle_payment_method_attached()`

```python
def handle_payment_method_attached(db: Session, stripe_event: dict) -> None:
    """payment_method.attached — if tenant's subscription is paused, log.
    Frontend will surface resume affordance via subscription status polling."""
    from app.models.billing import Subscription

    pm = stripe_event.get("data", {}).get("object", {})
    customer_id = pm.get("customer")
    if not customer_id:
        return

    # Check if tenant has a paused subscription
    sub_row = db.exec(
        select(Subscription).where(
            Subscription.psp_customer_id == customer_id,
            Subscription.is_active == True,
        )
    ).first()

    if sub_row:
        # Check Stripe status
        stripe = _get_stripe_client()
        try:
            stripe_sub = stripe.Subscription.retrieve(sub_row.psp_subscription_id)
            if stripe_sub.status == "paused":
                logger.info(f"Payment method attached for paused subscription {sub_row.psp_subscription_id} — tenant can resume")
        except Exception as e:
            logger.error(f"handle_payment_method_attached: failed to check subscription status: {e}")
```

**Intermediate test run:** `pytest -m unit --tb=short -q | tail -5`

---

## Task 6 — Update `_process_stripe_event()` Dispatcher in `webhooks_stripe.py`

Update the `_process_stripe_event()` function in `backend/api/routes/webhooks_stripe.py` to add the 7 new event routes.

**What to change:**

In the `_process_stripe_event()` function, update the import block and add the new event routes:

```python
from services.stripe_subscriptions import (
    handle_checkout_session_completed,
    handle_invoice_paid,
    handle_invoice_payment_failed,
    handle_payment_method_attached,
    handle_subscription_created,
    handle_subscription_deleted,
    handle_subscription_paused,
    handle_subscription_resumed,
    handle_subscription_schedule_updated,
    handle_subscription_trial_will_end,
)
```

Then add the new event routes to the if/elif chain (after the existing routes, before the `else`):

```python
elif event_type == "customer.subscription.trial_will_end":
    handle_subscription_trial_will_end(db, payload)
elif event_type == "customer.subscription.paused":
    handle_subscription_paused(db, payload)
elif event_type == "customer.subscription.resumed":
    handle_subscription_resumed(db, payload)
elif event_type == "customer.subscription.deleted":
    handle_subscription_deleted(db, payload)
elif event_type == "invoice.paid":
    handle_invoice_paid(db, payload)
elif event_type == "checkout.session.completed":
    handle_checkout_session_completed(db, payload)
elif event_type == "payment_method.attached":
    handle_payment_method_attached(db, payload)
```

**Remove** the old log-only stubs for `customer.subscription.deleted` and `invoice.paid`:
```python
# REMOVE this line:
elif event_type in ("customer.subscription.deleted", "invoice.paid"):
    logger.info(f"Stripe event {event_type} received (Phase 2 handling)")
```

**Intermediate test run:** `pytest -m unit --tb=short -q | tail -5`

---

## Task 7 — Add `POST /subscription/resume` Endpoint to `tenant_subscription.py`

Add the resume endpoint + `/test` twin to `backend/api/routes/tenant_subscription.py`.

**What to build:**

```python
class ResumeSubscriptionRequest(BaseModel):
    stripe_payment_method_id: str

class ResumeSubscriptionResponse(BaseModel):
    psp_subscription_id: str
    status: str
    billing_cycle_anchor: int | None = None
```

Add the `_impl` function:

```python
def _resume_subscription_impl(
    tenant_id: UUID,
    payload: ResumeSubscriptionRequest,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> ResumeSubscriptionResponse:
    """Shared logic for resuming a paused subscription."""
    if tenant_id != user_context.tenant_id:
        raise HTTPException(status_code=403, detail="Cannot resume subscription for another tenant")

    if isinstance(user_context, TestUserContext):
        # Test mode — bypass Stripe
        return ResumeSubscriptionResponse(
            psp_subscription_id="test_sub_mock_id",
            status="active",
            billing_cycle_anchor=None,
        )

    from services.stripe_subscriptions import resume_subscription, ResumeFailedError

    try:
        result = resume_subscription(
            db=db,
            tenant_id=tenant_id,
            stripe_payment_method_id=payload.stripe_payment_method_id,
        )
    except ResumeFailedError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "type": "https://pilotfortrades.com/errors/stripe-resume-failed",
                "title": "Subscription resume failed",
                "status": 502,
                "detail": "Subscription remains paused after resume — payment method may have failed",
            },
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "type": "https://pilotfortrades.com/errors/invalid-request",
                "title": "Invalid request",
                "status": 400,
                "detail": str(e),
            },
        )

    return ResumeSubscriptionResponse(
        psp_subscription_id=result["psp_subscription_id"],
        status=result["status"],
        billing_cycle_anchor=result["billing_cycle_anchor"],
    )
```

Add the route + test twin:

```python
@router.post(
    "/{tenant_id}/subscription/resume/test",
    response_model=ResumeSubscriptionResponse,
)
def resume_subscription_test(
    tenant_id: UUID,
    payload: ResumeSubscriptionRequest,
    db: Session = Depends(get_db),
):
    """Resume paused subscription (TEST ENDPOINT — no auth; Stripe bypassed)."""
    test_context = get_test_context()
    return _resume_subscription_impl(tenant_id, payload, db, test_context)

@router.post(
    "/{tenant_id}/subscription/resume",
    response_model=ResumeSubscriptionResponse,
)
def resume_subscription(
    tenant_id: UUID,
    payload: ResumeSubscriptionRequest,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(
        require_permission("subscription.tier.change")
    ),
):
    """Resume a paused subscription after payment method addition. RBAC: subscription.tier.change."""
    return _resume_subscription_impl(tenant_id, payload, db, current_user)
```

**Key points:**
- RBAC: `subscription.tier.change` (same as convert-from-trial)
- Test twin bypasses Stripe and returns mock response
- 502 error for `ResumeFailedError` (silent fail — subscription stayed paused)
- 400 error for `ValueError` (tenant not found, subscription not paused, etc.)
- RFC 7807 Problem Details format for all errors

**Intermediate test run:** `pytest -m unit --tb=short -q | tail -5`

---

## Task 8 — Write Tests

### Test Requirements

Per `backend/tests/README-adding-tests.md`:

**Domain folder**: `backend/tests/domains/subscriptions_usage/`

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

**Test files to create:**

| Test File | Tests | Description |
|---|---|---|
| `test_stripe_config.py` | 2 | `get_stripe_ids()` loads test JSON; singleton cache returns same dict |
| `test_create_charter_subscription.py` | 3 | Creates subscription with trial_end + trial_settings; 3 items; metadata correct |
| `test_resume_subscription.py` | 4 | Resume success (status→active); resume silent fail (status stays paused → ResumeFailedError); resume non-paused (ValueError); PM attached + set as default |
| `test_report_usage_event.py` | 3 | Meter event created with identifier; missing stripe_customer_id → skip; Stripe error → non-blocking |
| `test_webhook_handlers.py` | 7 | trial_will_end (log); paused (status update); resumed (status update); deleted (charter_eligible=false); invoice.paid (log); checkout.session.completed (10DLC stub); payment_method.attached (paused check) |
| `test_resume_endpoint.py` | 3 | POST /resume/test returns mock; POST /resume 502 on ResumeFailedError; POST /resume 400 on ValueError |

**Mocking Stripe**: Use `unittest.mock.patch` to mock `stripe.Subscription.create`, `stripe.Subscription.resume`, `stripe.Subscription.retrieve`, `stripe.PaymentMethod.attach`, `stripe.Customer.modify`, `stripe.billing.MeterEvent.create`. Never make real Stripe API calls in tests.

**Autouse fixture opt-outs**: If any test touches entitlement logic, add `skip_mock_entitlement_allowed` to `pytestmark` or as a fixture.

**Intermediate test run after each test file:** `pytest -m unit --tb=short -q | tail -5`

---

## Task 9 — Regenerate OpenAPI

After adding the resume endpoint, regenerate the OpenAPI spec:

```bash
cd <repo>/backend
source .venv/bin/activate
python export_openapi_json.py
```

This updates both `backend/openapi.json` and `backend/openapi_schema_map.md`.

---

## Final Verification Gate

### Phase 1 — Unit Tests Only

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=short -q 2>&1 | tail -10
```

**Gate**: All unit tests must pass. If any fail → fix before proceeding to Phase 2.

### Phase 2 — Ruff + Full Suite

```bash
# Ruff gate — changed files only
CHANGED_PY=$(git diff --name-only --diff-filter=d HEAD -- '*.py' | sed 's|^backend/||')
if [ -n "$CHANGED_PY" ]; then
    ruff check --fix $CHANGED_PY
    ruff format $CHANGED_PY
    ruff check $CHANGED_PY
fi

# Full test suite
python -m pytest --tb=short -q 2>&1 | tail -10
```

**Gate**: Ruff must be clean on all changed files. Full suite must pass (0 failures).

---

## Definition of Done

### Phase 1 (Unit Tests)
- [ ] `core/stripe_config.py` created — `get_stripe_ids()` loads `stripe_ids.test.json` and caches
- [ ] `create_charter_subscription()` created — uses `trial_end` + `trial_settings` + 3 items from `get_stripe_ids()`
- [ ] `resume_subscription()` created — C-SPIKE-1 flow with **status check** after resume
- [ ] `report_usage_event()` created — `MeterEvent.create()` with `identifier` idempotency key
- [ ] 7 new webhook handler functions created in `stripe_subscriptions.py`
- [ ] `_process_stripe_event()` dispatcher updated with 7 new event routes
- [ ] `POST /subscription/resume` + `/test` twin added to `tenant_subscription.py`
- [ ] All unit tests pass (`pytest -m unit`)

### Phase 2 (Full Suite)
- [ ] `python export_openapi_json.py` run — resume endpoint in OpenAPI spec
- [ ] Ruff clean on all changed files
- [ ] Full test suite passes (`pytest --tb=short -q`)
- [ ] No new warnings in test output

---

## Completion Summary

When done, append a completion summary to `dev-docs/analysis/pilot-launch-plan.md` Appendix B using this format:

```markdown
### C-B4 — Stripe Subscription Creation + Webhook Expansion: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot Python Engineer
**Baseline**: X passed, Y failed
**Final**: X+N passed, Y failed (+N new tests)

#### What Was Accomplished

- [Brief description of key change 1]
- [Brief description of key change 2]

#### Files Changed / Created

| File | Action |
|---|---|
| `backend/core/stripe_config.py` | Created — [what changed] |
| ... | ... |

#### Tests Added

| Test File | Domain | Tests | All Pass |
|---|---|---|---|
| `tests/domains/subscriptions_usage/test_file.py` | `subscriptions_usage` | N | ✅ |
```

Also:
1. Add a one-row entry to Appendix A (Completed Work Registry) in the launch plan
2. Mark C-B4 as ✅ in the §2.0 Master Status Table

---

## After This Task — Next Step

C-B5 (wizard step 4/5 conditional on `requires_payment_method`; cohort cap transaction) can begin — it depends on C-B4 ✅. C-B5 will call `create_charter_subscription()` from the signup wizard and use `requires_payment_method` to conditionally skip the payment step.

Run `pnpm sync-api-types` so the frontend types include the new resume endpoint.
