# C-B10 — Recurring 10DLC Pass-Through Subscription Item + Month-4 Celery Scheduler

**Batch**: C-B10
**Mode**: Pilot Python Engineer (backend-only)
**Prerequisite**: C-B9 ✅ (10DLC provisioning state machine + Stripe Checkout setup charge)
**Source of truth**: `pilot-tech-impl-spec-v1.md` §5.6 (Recurring Pass-Through), §6.2 (Object Model — `prod_passthrough`), §11.2 scenario 8 (Month 4 recurring item creation)
**Status**: Design — awaiting Tom approval
**Date**: August 6, 2026

---

## Overview

C-B9 built the one-time 10DLC setup charge (Stripe Checkout, `mode="payment"`, `setup_future_usage="off_session"`). The setup charge covers brand registration, 3 months of campaign fees (prepaid), and the first month of the phone number. After those 3 prepaid months, the tenant must be billed monthly for the recurring carrier costs — campaign fee (monthly) + phone number (monthly) — as a pass-through with zero markup (D25).

C-B10 implements:

1. **A service function** that creates a recurring Stripe SubscriptionItem on the tenant's existing Charter subscription, using inline `price_data` against the dedicated `prod_passthrough` Product ("Carrier fees (pass-through)"). The amount is read from `tenant_messaging_registration.quoted_monthly_cents` (stored at provisioning time by C-B9's `initiate_provisioning()`).
2. **A Celery beat task** (`create_recurring_carrier_item`) that runs daily and finds all `tenant_messaging_registration` rows in `status='active'` whose `created_at + 90 days` has passed and that don't yet have a `stripe_recurring_item_id`. For each, it calls the service function to create the subscription item, stores the Stripe SubscriptionItem ID on the registration row, and logs the event.
3. **A new column** `stripe_recurring_item_id` (TEXT, nullable) on `tenant_messaging_registration` to track that the recurring item has been created (idempotency guard — prevents double-charging).
4. **A new column** `recurring_item_created_at` (TIMESTAMPTZ, nullable) on `tenant_messaging_registration` to record when the recurring item was created (for audit + operator visibility).

**No new API endpoints.** This is a background-only batch — the recurring item is created by the Celery scheduler, not by a user action. The frontend (C-B9's `/settings/messaging` page) already shows the recurring cost in the carrier quote display; no UI change is needed.

**No new table.** Two nullable columns on the existing `tenant_messaging_registration` table.

---

## A. Input Read Summary

| Input | Source | Key findings |
|---|---|---|
| Spec §5.6 — Recurring Pass-Through | `pilot-tech-impl-spec-v1.md` §5.6 | After 3 prepaid months, add recurring subscription item via `stripe.SubscriptionItem.create()` with inline `price_data` (currency=usd, product=PRODUCT_PASSTHROUGH, recurring interval=month, unit_amount=quote.recurring_total_cents). `proration_behavior="none"`. Schedule at `campaign_created_at + 90 days` to avoid double-charging the prepaid window. Invoice presentation: pass-through line labeled "Carrier fees — passed through at cost" on same invoice as $49 Charter line. |
| Spec §6.2 — Object Model | Same, §6.2 | `prod_passthrough` = "Carrier fees (pass-through)" Product. Already created by C-B3's `stripe_bootstrap.py`. ID stored in `stripe_ids.{mode}.json` under `products.prod_passthrough`. |
| Spec §11.2 — Test Scenario 8 | Same, §11.2 | "Month 4 recurring item creation: correct amount, correct label, no double-charge for prepaid window." |
| C-B9 — `assign_phone_number()` | `messaging_provisioning.py` | Transitions `awaiting_number_selection → number_assigned → active`. The `active` state is the trigger point for the 90-day countdown. `registration.created_at` is the registration creation timestamp (set when `initiate_provisioning()` creates the row). |
| C-B9 — `initiate_provisioning()` | `messaging_provisioning.py` | Stores `quoted_setup_cents` and `quoted_monthly_cents` on the registration row (lines 199-200). `quoted_monthly_cents` is the recurring amount in cents (millicents // 1000). This is the amount for the recurring subscription item. |
| C-B9 — `handle_checkout_session_completed()` | `stripe_subscriptions.py` | On `a2p_10dlc_setup` purpose: attaches PM as `customer.invoice_settings.default_payment_method`, transitions to `brand_submitted`, enqueues `provision_brand` task. The PM attachment is what makes the recurring item chargeable off-session. |
| C-B9 — `create_10dlc_checkout_session()` | `messaging_checkout.py` | Creates the one-time Checkout Session. Stores `stripe_checkout_id` on registration. The `setup_future_usage="off_session"` saves the card for future recurring charges. |
| C-B4 — `create_charter_subscription()` | `stripe_subscriptions.py` | Creates the Charter Stripe Subscription (trial + no card). The subscription ID is stored on the `subscription` table as `psp_subscription_id` (NOT on `tenant` — the spec's `tenant.stripe_subscription_id` is a simplification). |
| Live DB — `subscription` table | MCP (this session) | 22 columns. `psp_subscription_id` (VARCHAR, nullable) holds the Stripe Subscription ID. `psp_customer_id` holds the Stripe Customer ID. `tenant_id` FK. `is_active` boolean. This is where the Charter subscription ID lives. |
| Live DB — `tenant_messaging_registration` | MCP (this session) | 18 columns. Has `quoted_monthly_cents` (INTEGER, nullable) — the recurring amount. Has `status` (TEXT, NOT NULL) — state machine. Has `created_at` (TIMESTAMPTZ, NOT NULL). **Missing**: `stripe_recurring_item_id` and `recurring_item_created_at` — C-B10 adds these. |
| Live DB — `carrier_fee_schedule` | MCP (this session) | 20 rows. Recurring fees: `campaign_quarterly` (sole_prop=$10.00, standard=$15.00 — quarterly, converted to monthly equivalent $3.33/$5.00 in quote) + `phone_number` ($1.00 monthly). The `quoted_monthly_cents` on the registration row is the sum of these monthly equivalents. |
| `stripe_ids.test.json` | `backend/scripts/stripe_ids.test.json` | `prod_passthrough` = `prod_REDACTEDX01` (test mode). Live mode: `prod_REDACTED03`. Loaded at runtime via `core/stripe_config.py:get_stripe_ids()`. |
| `core/stripe_config.py` | `backend/core/stripe_config.py` | Singleton loader. `get_stripe_ids()` returns dict with `products.prod_passthrough` key. Mode determined by `STRIPE_SECRET_KEY` prefix. |
| `core/celery_app.py` | `backend/core/celery_app.py` | Beat schedule dict. C-B9 added `check-otp-timeout` (hourly). C-B6 added `free-period-notifications-daily` (daily 09:00 UTC). Task imports list at line 87-89. C-B10 adds a new daily task. |
| mvp-arch §17 | `mvp-arch.md` §17 | SMS infrastructure: carrier adapter pattern (§17.1), A2P 10DLC compliance (§17.2). §16 patterns: carrier-agnostic adapter (§17.1). |

---

## B. Migration Plan

### B.1 — DB Changes

**One migration** — adds 2 nullable columns to `tenant_messaging_registration`:

```sql
ALTER TABLE tenant_messaging_registration
  ADD COLUMN stripe_recurring_item_id TEXT,
  ADD COLUMN recurring_item_created_at TIMESTAMPTZ;
```

- `stripe_recurring_item_id` — stores the Stripe SubscriptionItem ID (`si_...`) returned by `stripe.SubscriptionItem.create()`. Null until the recurring item is created. Acts as the idempotency guard: the Celery task skips any registration where this is non-null.
- `recurring_item_created_at` — timestamp when the recurring item was created. For audit + operator visibility (the operator dashboard in C-B11 will display this).

Both nullable because they are populated asynchronously by the Celery task, not at provisioning time. No NOT NULL pattern needed — no existing rows have these values (10DLC is not yet provisioned for any tenant).

**No changes to `carrier_fee_schedule`** — the recurring fees already exist (`campaign_quarterly`, `phone_number`). The `quoted_monthly_cents` on the registration row already holds the correct amount from C-B9's `initiate_provisioning()`.

**No changes to `subscription` table** — the `psp_subscription_id` column already holds the Charter subscription ID.

### B.2 — MCP Verification Queries (pre-migration)

```sql
-- Verify current tenant_messaging_registration columns (confirm new cols don't exist)
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'tenant_messaging_registration'
ORDER BY ordinal_position;

-- Verify subscription table has psp_subscription_id
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'subscription'
  AND column_name = 'psp_subscription_id';

-- Verify carrier_fee_schedule has recurring fees
SELECT fee_code, entity_type, amount_millicents
FROM carrier_fee_schedule
WHERE effective_to IS NULL
  AND (fee_code LIKE '%quarterly%' OR fee_code = 'phone_number')
ORDER BY fee_code, entity_type;
```

### B.3 — Pre-Migration State

- `tenant_messaging_registration`: 18 columns (no `stripe_recurring_item_id` or `recurring_item_created_at`)
- `subscription`: has `psp_subscription_id` (VARCHAR, nullable) + `tenant_id` FK + `is_active`
- `carrier_fee_schedule`: 20 rows, recurring fees present (`campaign_quarterly`, `phone_number`)
- No existing rows in `tenant_messaging_registration` for real tenants (10DLC not yet provisioned)

### B.4 — 3-Part NOT NULL Pattern

Not applicable — both new columns are intentionally nullable. They are populated asynchronously by the Celery task after the 90-day prepaid window expires.

### B.5 — Audit Columns

Not applicable — no new table. The `tenant_messaging_registration` table already has all 4 audit columns (`created_at`, `updated_at`, `created_by`, `updated_by`) from C-B2.

### B.6 — Seed Data Rollout

Not applicable — no new seed data. The `carrier_fee_schedule` recurring fees already exist from C-B8/C-B9. The `stripe_ids.test.json` already has `prod_passthrough` from C-B3.

---

## C. Execution Order

| # | Task | Files | Description |
|---|---|---|---|
| 1 | Migration | `backend/migrations/versions/2026_08_06_XXXX-<rev>_c_b10_recurring_item_cols.py` | Blank migration adding 2 nullable columns to `tenant_messaging_registration`. Triple-verify (upgrade → downgrade → upgrade). |
| 2 | SQLModel update | `backend/app/models/sms.py` | Add `stripe_recurring_item_id: str \| None` + `recurring_item_created_at: datetime \| None` to `TenantMessagingRegistration`. |
| 3 | Service function | `backend/services/messaging_recurring.py` (NEW) | `create_recurring_carrier_item(db, registration_id) -> str` — creates the Stripe SubscriptionItem, stores the ID + timestamp on the registration row. |
| 4 | Celery task | `backend/tasks/messaging_recurring.py` (NEW) | `create_recurring_carrier_items()` — daily beat task. Finds eligible registrations, calls the service function for each. Two-layer pattern (`_impl` + `@celery_app.task`). |
| 5 | Celery registration | `backend/core/celery_app.py` | Add task import + beat schedule entry (daily 09:30 UTC, after `free-period-notifications-daily` at 09:00). |
| 6 | Schema JSON sync | `dev-docs/db-design/pilot-db-schema-v2.6h.json` | Run `schema_manager.py` to add the 2 new columns to the `tenant_messaging_registration` entry. |
| 7 | Tests | `backend/tests/domains/subscriptions_usage/test_cb10_recurring_item.py` (NEW) | Unit tests for the service function + Celery task. Mock Stripe calls. |
| 8 | OpenAPI | — | No endpoint changes → no OpenAPI regen needed. |
| 9 | Verification | — | `pytest -m unit` + full suite + Ruff + Alembic triple-verify. |

---

## D. New API Endpoints

**None.** This is a background-only batch. The recurring item is created by the Celery scheduler, not by a user action. No new endpoints, no `/test` twins, no OpenAPI changes.

---

## E. Pattern Reuse Decisions

| Pattern | Source | How it applies |
|---|---|---|
| **Two-layer Celery task** | C-B9 `tasks/messaging_provisioning.py` | `_impl(db, ...) -> dict` inner function + `@celery_app.task` wrapper. Parameters use `str` UUIDs. |
| **Stripe singleton loader** | C-B4 `core/stripe_config.py:get_stripe_ids()` | Load `prod_passthrough` ID from `stripe_ids.{mode}.json`. Never hardcode Stripe IDs. |
| **`_get_stripe_client()`** | C-B4 `stripe_subscriptions.py` | Lazy Stripe client accessor. Reuse for `SubscriptionItem.create()`. |
| **Idempotency guard** | C-B9 `NON_RETRYABLE_STATES` pattern | The Celery task checks `stripe_recurring_item_id IS NULL` before creating. If non-null, skip (idempotent). |
| **Tenant-scoped `select()`** | Architect Rule §3 | All queries filter by `tenant_id` explicitly. The Celery task queries `tenant_messaging_registration` directly (no tenant_id param needed — it scans all active registrations). |
| **Audit context** | C-B9 `set_audit_context_sync()` | Not needed — the Celery task is a system action, not a user mutation. The `updated_at` column auto-updates via the DB trigger. |

---

## F. Shared Module Interfaces

### F.1 — `services/messaging_recurring.py` (NEW)

```python
def create_recurring_carrier_item(
    db: Session,
    registration_id: uuid.UUID,
) -> str:
    """Creates a recurring Stripe SubscriptionItem for 10DLC carrier fees.

    Called by the Celery task after the 90-day prepaid window expires.
    Uses inline price_data against prod_passthrough ("Carrier fees (pass-through)").
    Amount = registration.quoted_monthly_cents (stored at provisioning time).
    proration_behavior="none" to avoid prorating the first charge.

    Idempotency: if registration.stripe_recurring_item_id is non-null, skip.
    Returns the Stripe SubscriptionItem ID (si_...).

    Raises:
        ValueError: If registration not found, not in 'active' status,
            quoted_monthly_cents is None, or no active subscription found.
        Exception: On Stripe API error.
    """
```

### F.2 — `tasks/messaging_recurring.py` (NEW)

```python
def _create_recurring_carrier_items_impl(db: Session) -> dict[str, int]:
    """Inner implementation — find eligible registrations and create recurring items.

    Eligibility:
        - status = 'active'
        - created_at + 90 days <= now()  (prepaid window expired)
        - stripe_recurring_item_id IS NULL  (not yet created)

    Returns: {"processed": N, "created": M, "skipped": K, "errors": E}
    """

@celery_app.task(name="create_recurring_carrier_items")
def create_recurring_carrier_items() -> dict[str, int]:
    """Daily: create recurring carrier fee subscription items for eligible tenants."""
```

### F.3 — Celery Beat Schedule

```python
"create-recurring-carrier-items-daily": {
    "task": "create_recurring_carrier_items",
    "schedule": crontab(hour=9, minute=30),  # 09:30 UTC daily (after free-period-notifications at 09:00)
},
```

---

## G. Open Questions Resolved

| # | Question | Resolution |
|---|---|---|
| 1 | **Where is the Stripe Subscription ID stored?** The spec references `tenant.stripe_subscription_id` but the tenant table has no such column. | **Resolved via MCP.** The Charter subscription ID is stored on the `subscription` table as `psp_subscription_id`. The service function queries `subscription` by `tenant_id` where `is_active = True` and `psp_provider = 'stripe'` to find the subscription ID. |
| 2 | **What amount to use for the recurring item?** The spec says `quote.recurring_total_cents` but the quote is computed at provisioning time and may change if the fee schedule changes. | **Resolved.** Use `registration.quoted_monthly_cents` — the amount stored on the registration row at provisioning time by C-B9's `initiate_provisioning()`. This is the amount the tenant was quoted and agreed to pay. If the fee schedule changes later, the recurring item amount does NOT change (it was locked at quote time). A future batch could add a fee-schedule-change reconciliation flow, but that's out of scope for C-B10. |
| 3 | **When does the 90-day countdown start?** The spec says `campaign_created_at + 90 days` but there's no `campaign_created_at` column. | **Resolved.** Use `registration.created_at + 90 days`. The registration row is created when `initiate_provisioning()` runs (status='quoting'), and the setup charge (which includes 3 months prepaid) is paid shortly after. The 90-day window from `created_at` is a safe approximation — it may be off by a few days (the time between registration creation and checkout completion), but it errs on the side of starting the recurring charge slightly later, which is the safe direction (no double-charge risk). |
| 4 | **Should the recurring item use `proration_behavior="none"`?** | **Yes.** The spec explicitly says `proration_behavior="none"`. This prevents Stripe from prorating the first recurring charge against the current billing cycle anchor. The tenant pays the full monthly amount on their next invoice, separate from the Charter $49 line. |
| 5 | **What happens if the tenant's subscription is paused (free period ended, no payment method)?** | **The Celery task still creates the recurring item.** The subscription is paused, not canceled. When the tenant adds a payment method and resumes (C-B4's `resume_subscription()`), the recurring item will be charged on the next invoice. If the subscription is canceled (not just paused), the task should skip — a canceled subscription can't have new items added. The task checks `subscription.is_active = True` before creating. |
| 6 | **What if `quoted_monthly_cents` is 0 or None?** | **Skip with a warning log.** This shouldn't happen in production (the quote always has a recurring amount), but defensive coding prevents a Stripe API error. The task logs the skip and moves on. |

---

## H. Surface Mockup Reference

Not applicable — backend-only batch. No UI changes. The C-B9 `/settings/messaging` page already displays the recurring cost in the `CarrierQuoteDisplay` component.

---

## I. Component Manifest

Not applicable — no new frontend components.

---

## J. Detailed Design — Service Function

### J.1 — `create_recurring_carrier_item()`

```python
def create_recurring_carrier_item(
    db: Session,
    registration_id: uuid.UUID,
) -> str:
    # 1. Load registration
    registration = db.exec(
        select(TenantMessagingRegistration).where(
            TenantMessagingRegistration.id == registration_id
        )
    ).first()
    if not registration:
        raise ValueError(f"Registration {registration_id} not found")

    # 2. Idempotency guard
    if registration.stripe_recurring_item_id:
        logger.info(
            "Recurring item already exists for registration %s (si_id=%s), skipping",
            registration_id, registration.stripe_recurring_item_id,
        )
        return registration.stripe_recurring_item_id

    # 3. Validate status
    if registration.status != "active":
        raise ValueError(
            f"Registration {registration_id} not in 'active' status (current: {registration.status})"
        )

    # 4. Validate quoted_monthly_cents
    if not registration.quoted_monthly_cents or registration.quoted_monthly_cents <= 0:
        logger.warning(
            "Registration %s has invalid quoted_monthly_cents=%s, skipping",
            registration_id, registration.quoted_monthly_cents,
        )
        raise ValueError("quoted_monthly_cents is null or zero")

    # 5. Find the tenant's active Stripe subscription
    sub_row = db.exec(
        select(Subscription).where(
            Subscription.tenant_id == registration.tenant_id,
            Subscription.is_active == True,  # noqa: E712
            Subscription.psp_provider == "stripe",
        )
    ).first()
    if not sub_row or not sub_row.psp_subscription_id:
        raise ValueError(f"No active Stripe subscription found for tenant {registration.tenant_id}")

    # 6. Get prod_passthrough ID from stripe_ids config
    from core.stripe_config import get_stripe_ids
    stripe_ids = get_stripe_ids()
    prod_passthrough_id = stripe_ids["products"]["prod_passthrough"]

    # 7. Create the recurring SubscriptionItem
    from services.stripe_subscriptions import _get_stripe_client
    stripe = _get_stripe_client()

    sub_item = stripe.SubscriptionItem.create(
        subscription=sub_row.psp_subscription_id,
        price_data={
            "currency": "usd",
            "product": prod_passthrough_id,
            "recurring": {"interval": "month"},
            "unit_amount": registration.quoted_monthly_cents,  # already in cents
        },
        quantity=1,
        proration_behavior="none",
    )

    # 8. Store the SubscriptionItem ID + timestamp on the registration
    registration.stripe_recurring_item_id = sub_item.id
    registration.recurring_item_created_at = safe_now_utc()
    db.add(registration)
    db.commit()
    db.refresh(registration)

    logger.info(
        "Created recurring carrier item %s for registration %s (amount=%d cents/month)",
        sub_item.id, registration_id, registration.quoted_monthly_cents,
    )
    return sub_item.id
```

### J.2 — Celery Task

```python
def _create_recurring_carrier_items_impl(db: Session) -> dict[str, int]:
    # Find eligible registrations:
    # - status = 'active'
    # - created_at + 90 days <= now()
    # - stripe_recurring_item_id IS NULL
    cutoff = safe_now_utc() - timedelta(days=90)

    eligible = db.exec(
        select(TenantMessagingRegistration).where(
            TenantMessagingRegistration.status == "active",
            TenantMessagingRegistration.created_at <= cutoff,
            TenantMessagingRegistration.stripe_recurring_item_id.is_(None),
        )
    ).all()

    processed = len(eligible)
    created = 0
    skipped = 0
    errors = 0

    for reg in eligible:
        try:
            create_recurring_carrier_item(db, reg.id)
            created += 1
        except ValueError as exc:
            # Expected skip (already exists, invalid amount, etc.)
            logger.info("Skipping registration %s: %s", reg.id, exc)
            skipped += 1
        except Exception as exc:
            logger.error("Failed to create recurring item for registration %s: %s", reg.id, exc)
            errors += 1
            db.rollback()

    return {"processed": processed, "created": created, "skipped": skipped, "errors": errors}
```

---

## K. Test Plan

| Test | Type | Description |
|---|---|---|
| `test_create_recurring_item_happy_path` | Unit | Registration in `active` status, `quoted_monthly_cents` set, active subscription exists → creates SubscriptionItem, stores ID + timestamp. |
| `test_create_recurring_item_idempotent` | Unit | `stripe_recurring_item_id` already set → returns existing ID, no Stripe call. |
| `test_create_recurring_item_wrong_status` | Unit | Registration not in `active` status → raises ValueError. |
| `test_create_recurring_item_no_subscription` | Unit | No active Stripe subscription for tenant → raises ValueError. |
| `test_create_recurring_item_zero_amount` | Unit | `quoted_monthly_cents` is 0 or None → raises ValueError. |
| `test_celery_task_finds_eligible` | Unit | Two registrations: one eligible (active, >90d, no item), one not (active, <90d) → only eligible one processed. |
| `test_celery_task_skips_existing` | Unit | Registration with `stripe_recurring_item_id` already set → skipped. |
| `test_celery_task_handles_errors` | Unit | Stripe API error on one registration → error logged, others still processed. |
| `test_celery_task_no_eligible` | Unit | No eligible registrations → returns `{"processed": 0, "created": 0, "skipped": 0, "errors": 0}`. |

**Domain folder**: `tests/domains/subscriptions_usage/` (same as C-B8/C-B9 tests).

**Mock pattern**: Mock `stripe.SubscriptionItem.create` to return a fake `si_...` ID. Mock `_get_stripe_client()` and `get_stripe_ids()`. Use the existing test DB session fixture.

---

## L. Cost Impact

**$0.** No new AWS services, no new infrastructure. The Celery task runs daily (same as existing tasks) and makes at most N Stripe API calls per day (where N = number of tenants whose 90-day window just expired — typically 0-1 per day at MVP scale). Stripe SubscriptionItem creation is free (no per-item fee).

---

## M. Definition of Done

- [ ] Migration created + triple-verified (upgrade → downgrade → upgrade)
- [ ] SQLModel updated with 2 new fields
- [ ] `services/messaging_recurring.py` created with `create_recurring_carrier_item()`
- [ ] `tasks/messaging_recurring.py` created with two-layer Celery task
- [ ] `core/celery_app.py` updated with task import + beat schedule
- [ ] Schema JSON synced via `schema_manager.py`
- [ ] `db_models_map.md` regenerated (if model map changes)
- [ ] Unit tests written (9 tests minimum) — all passing
- [ ] `pytest -m unit` — 0 new failures
- [ ] Full suite — 0 new failures
- [ ] Ruff — 0 errors on changed/new files
- [ ] MCP-verified: `tenant_messaging_registration` now has 20 columns
