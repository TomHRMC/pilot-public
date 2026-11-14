# C-B4 — Stripe Subscription Creation + Webhook Expansion + Usage Reporting

**Batch**: C-B4
**Mode**: Pilot Python Engineer
**Prerequisite**: C-B3 ✅ (Stripe bootstrap script — `stripe_ids.test.json` committed)
**Source of truth**: `pilot-tech-impl-spec-v1.md` §6.4-6.8 + C-SPIKE-1 findings (Q#3 resume call signature)
**Status**: Design complete — ready for prompt authoring
**Date**: August 4, 2026

---

## Overview

C-B4 builds the Stripe subscription lifecycle for the Charter program: creating trialing subscriptions with no payment method, expanding the webhook handler to 10 events, implementing the resume-from-pause flow (C-SPIKE-1), and adding Billing Meter usage reporting. This is a **backend-only batch** — no DB migration, no frontend.

**Key architectural change**: The old `create_charter_subscription_schedule()` (STRIPE-B1 schedule-based approach) is **replaced** by direct `Subscription.create()` with `trial_end` + `trial_settings.end_behavior.missing_payment_method: pause`. The schedule approach was designed for the old "founders cohort" model; the Charter program uses a simpler trial-pause model.

---

## A. Input Read Summary

| Input | Sections read | Key takeaways |
|---|---|---|
| `pilot-tech-impl-spec-v1.md` | §6.4 (subscription creation), §6.5 (usage reporting), §6.6 (price lock), §6.8 (webhooks), §6.9 (test mode) | 3-item subscription (charter monthly + 2 metered overage); `trial_end` absolute timestamp; `trial_settings.end_behavior.missing_payment_method: pause`; 10 webhook events; `MeterEvent.create()` with `identifier` idempotency key |
| C-SPIKE-1 findings | Q#3 (resume call signature), Q#4 (meter/test-clock) | `Subscription.resume(sub_id, billing_cycle_anchor="now")` — **can return 200 with status="paused"** if payment fails; meter events are async (2-5s sleep before test-clock advance) |
| `stripe_subscriptions.py` | Full file (517 lines) | Existing: `_get_stripe_client()`, `create_stripe_customer()`, `create_stripe_subscription()` (old PM-required pattern), `handle_subscription_created()`, `create_charter_subscription_schedule()` (to be replaced), `handle_invoice_payment_failed()`, `handle_subscription_schedule_updated()`, `_handle_refund_event()` |
| `webhooks_stripe.py` | Full file (187 lines) | Existing dispatcher handles 6 event types; `customer.subscription.deleted` + `invoice.paid` are log-only stubs; missing 7 events for C-B4 |
| `tenant_subscription.py` | Full file | Existing routes: GET subscription, PUT upgrade, POST convert-from-trial, POST change-tier — all with `/test` twins. C-B4 adds POST resume. |
| `stripe_ids.test.json` | Full file | 14 object IDs: 3 products, 2 meters, 9 prices. `price_charter_monthly` = `price_REDACTED09` |
| Live DB — `subscription_tier` | MCP query | Charter: `free_period_days=90`, `requires_payment_method=false`, `price_locked=true`, `stripe_price_id_monthly` set, `stripe_price_id_annual=NULL` |
| Live DB — `tenant` | MCP query | `free_period_ends_at`, `charter_member_number`, `charter_eligible` columns exist (C-B2) |
| Live DB — `subscription` | MCP query | `psp_subscription_id`, `status_id`, `billing_interval`, `trial_ends_at`, `is_active`, `stripe_schedule_id` columns exist |
| Live DB — `subscription_status` | MCP query | 6 codes: `active`(billing_active=true), `trialing`(true), `past_due`(true), `paused`(false), `canceled`(false), `unpaid`(false) |
| Live DB — `tenant_messaging_registration` | MCP query | 18 columns incl. `stripe_checkout_id`, `status`, `telnyx_brand_id` — C-B9 will flesh out; C-B4 stubs the webhook handler |
| Live DB — `stripe_webhook_event_processed` | MCP query (B14 migration) | Dedup table exists; `event_id` TEXT PK, `event_type` TEXT, `processed_at` TIMESTAMPTZ |

---

## B. Migration Plan

**No migration needed.** All required columns exist:
- `subscription_tier`: `free_period_days`, `requires_payment_method`, `price_locked` (C-B2 ✅)
- `tenant`: `free_period_ends_at`, `charter_member_number`, `charter_eligible` (C-B2 ✅)
- `subscription`: `psp_subscription_id`, `status_id`, `trial_ends_at`, `is_active` (B14 ✅)
- `subscription_status`: `paused`, `trialing`, `active`, `canceled` codes all exist (seeded ✅)
- `stripe_webhook_event_processed`: dedup table exists (B14 ✅)

**Pre-migration state**: N/A (no migration).

---

## C. Execution Order

| # | Task | File(s) |
|---|---|---|
| 1 | Create `core/stripe_config.py` — singleton loader for `stripe_ids.{mode}.json` | `backend/core/stripe_config.py` |
| 2 | Add `create_charter_subscription()` to `stripe_subscriptions.py` — uses `trial_end` + `trial_settings` + 3 items from `stripe_config` | `backend/services/stripe_subscriptions.py` |
| 3 | Add `resume_subscription()` to `stripe_subscriptions.py` — C-SPIKE-1 resume flow with status check | `backend/services/stripe_subscriptions.py` |
| 4 | Add `report_usage_event()` to `stripe_subscriptions.py` — `MeterEvent.create()` with idempotency key | `backend/services/stripe_subscriptions.py` |
| 5 | Add 7 new webhook handler functions to `stripe_subscriptions.py` | `backend/services/stripe_subscriptions.py` |
| 6 | Update `_process_stripe_event()` dispatcher in `webhooks_stripe.py` — add 7 new event routes | `backend/api/routes/webhooks_stripe.py` |
| 7 | Add `POST /api/v1/tenants/{tenant_id}/subscription/resume` endpoint to `tenant_subscription.py` | `backend/api/routes/tenant_subscription.py` |
| 8 | Add `POST /api/v1/tenants/{tenant_id}/subscription/resume/test` test twin | `backend/api/routes/tenant_subscription.py` |
| 9 | Write unit tests for all new service functions | `backend/tests/domains/subscriptions_usage/` |
| 10 | Write webhook handler tests (mock Stripe events) | `backend/tests/domains/subscriptions_usage/` |
| 11 | Write resume endpoint tests | `backend/tests/domains/subscriptions_usage/` |
| 12 | Run `python export_openapi_json.py` — adds resume endpoint to OpenAPI spec | `backend/openapi.json` |
| 13 | Run `ruff check --fix && ruff format` on all changed files | — |
| 14 | Run full test suite (Phase 2 verification) | — |

---

## D. New API Endpoints

### POST /api/v1/tenants/{tenant_id}/subscription/resume

Resumes a paused Charter subscription after the user adds a payment method.

| Field | Value |
|---|---|
| **Path** | `/api/v1/tenants/{tenant_id}/subscription/resume` |
| **Method** | POST |
| **Auth** | `require_permission("subscription.tier.change")` |
| **RBAC** | Owner only (same as convert-from-trial) |
| **Request body** | `{"stripe_payment_method_id": "pm_..."}` |
| **Response** | `ResumeSubscriptionResponse` (see below) |
| **Errors** | 404 (tenant not found), 400 (subscription not paused), 502 (resume failed — Stripe returned paused) |
| **Test twin** | `POST /api/v1/tenants/{tenant_id}/subscription/resume/test` |

```python
class ResumeSubscriptionRequest(BaseModel):
    stripe_payment_method_id: str

class ResumeSubscriptionResponse(BaseModel):
    psp_subscription_id: str
    status: str  # "active" on success, "paused" on silent fail
    billing_cycle_anchor: int | None  # Unix timestamp of new billing cycle start
```

**Implementation flow** (from C-SPIKE-1):
1. Load tenant, verify `stripe_customer_id` exists
2. Load active `Subscription` row by `tenant_id` where `is_active=true`
3. Verify Stripe subscription status is `paused` (via `stripe.Subscription.retrieve()`)
4. Attach PM: `stripe.PaymentMethod.attach(pm_id, customer=customer_id)`
5. Set default: `stripe.Customer.modify(customer_id, invoice_settings={"default_payment_method": pm_id})`
6. Resume: `sub = stripe.Subscription.resume(sub_id, billing_cycle_anchor="now")`
7. **CRITICAL**: Check `sub.status` — if still `"paused"`, return 502 with `status="paused"` (silent fail)
8. If `sub.status == "active"`: update `subscription.status_id` to `active` status, return 200

---

## E. Pattern Reuse Decisions

| Pattern | How it applies |
|---|---|
| **Idempotency** (§16) | `MeterEvent.create()` uses `identifier` as idempotency key (spec §6.5). The resume endpoint is a POST but is naturally idempotent — calling resume on an already-active subscription is a no-op (Stripe returns the active subscription). |
| **Webhook dedup** (existing B14) | The `stripe_webhook_event_processed` dedup table already handles event idempotency. New handlers just add business logic; the dedup layer is unchanged. |
| **Background task processing** (existing B14) | `_process_stripe_event()` already runs as a BackgroundTask. New handlers follow the same pattern — return 200 fast, process in background. |
| **Sync routes** (Rule §21) | All new routes and `_impl()` functions are plain `def` — never `async def`. The webhook handler is already `async def` for the raw body read, but dispatches to sync `_process_stripe_event()`. |
| **RFC 7807 errors** (Rule §8) | Resume endpoint returns RFC 7807 Problem Details for error cases (404, 400, 502). |
| **Audit context** (Rule §9) | Resume endpoint calls `set_audit_context_sync(db, user_id=user.id)` before committing. Webhook handlers don't have a user context (system events) — audit is via the webhook dedup table. |

---

## F. Shared Module Interfaces

### core/stripe_config.py

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

### services/stripe_subscriptions.py — New Functions

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

def handle_subscription_trial_will_end(db: Session, payload: dict) -> None:
    """customer.subscription.trial_will_end — fires 3 days before trial ends.
    Stub: log event. Full notification schedule is C-B6."""

def handle_subscription_paused(db: Session, payload: dict) -> None:
    """customer.subscription.paused — update subscription.status_id to 'paused'.
    Do NOT disable SMS if tenant_messaging_registration.status='active' (spec §6.8)."""

def handle_subscription_resumed(db: Session, payload: dict) -> None:
    """customer.subscription.resumed — update subscription.status_id to 'active'."""

def handle_subscription_deleted(db: Session, payload: dict) -> None:
    """customer.subscription.deleted — set tenant.charter_eligible=false permanently;
    update subscription.status_id to 'canceled'; audit log."""

def handle_invoice_paid(db: Session, payload: dict) -> None:
    """invoice.paid — clear dunning state (if any). Log payment success."""

def handle_checkout_session_completed(db: Session, payload: dict) -> None:
    """checkout.session.completed — stub for C-B9 (10DLC setup).
    If metadata.purpose == 'a2p_10dlc_setup': log and return.
    C-B9 will implement the full Telnyx provisioning transition."""

def handle_payment_method_attached(db: Session, payload: dict) -> None:
    """payment_method.attached — if tenant's subscription is paused, log.
    Frontend will surface resume affordance via subscription status polling."""
```

### api/routes/webhooks_stripe.py — Updated Dispatcher

The `_process_stripe_event()` function adds 7 new event routes:

```python
# Existing (keep):
if event_type == "customer.subscription.created":
    handle_subscription_created(db, payload)
elif event_type == "customer.subscription.updated":
    handle_subscription_created(db, payload)
elif event_type == "invoice.payment_failed":
    handle_invoice_payment_failed(db, payload)
elif event_type == "payment_intent.succeeded":
    handle_payment_intent_succeeded(db, payload)
elif event_type == "payment_intent.payment_failed":
    handle_payment_intent_failed(db, payload)
elif event_type == "subscription_schedule.updated":
    handle_subscription_schedule_updated(db, payload)
elif event_type in ("charge.refunded", "refund.created"):
    _handle_refund_event(db, payload)

# NEW (add):
elif event_type == "customer.subscription.trial_will_end":
    handle_subscription_trial_will_end(db, payload)
elif event_type == "customer.subscription.paused":
    handle_subscription_paused(db, payload)
elif event_type == "customer.subscription.resumed":
    handle_subscription_resumed(db, payload)
elif event_type == "customer.subscription.deleted":
    handle_subscription_deleted(db, payload)  # was log-only stub
elif event_type == "invoice.paid":
    handle_invoice_paid(db, payload)  # was log-only stub
elif event_type == "checkout.session.completed":
    handle_checkout_session_completed(db, payload)
elif event_type == "payment_method.attached":
    handle_payment_method_attached(db, payload)
```

---

## G. Open Questions Resolved

| Question | Resolution | Source |
|---|---|---|
| **Q#3**: Exact resume-from-trial-end-pause call signature | ✅ Resolved by C-SPIKE-1. `Subscription.resume(sub_id, billing_cycle_anchor="now")` after setting `customer.invoice_settings.default_payment_method`. **Critical**: check `sub.status` after resume — can return 200 but stay `paused`. | C-SPIKE-1 card |
| **Q#4**: Billing Meter aggregation across test-clock advances | ✅ Resolved by C-SPIKE-1. Meter events work but are async — add 2-5s sleep before advancing test clock. Only affects C-B14 test suite, not C-B4 production code. | C-SPIKE-1 card |
| **Old `create_charter_subscription_schedule()`** | **Replaced** by `create_charter_subscription()`. The schedule-based approach (STRIPE-B1) was for the old founders cohort model. The Charter program uses a simpler trial-pause model. The old function stays in the codebase (not deleted) but is no longer called by new code. | Spec §6.4 |
| **`handle_subscription_created()` vs Charter** | The existing `handle_subscription_created()` looks up the tier by `stripe_price_id_monthly` or `stripe_price_id_annual`. For Charter, the first item is `price_charter_monthly` which is already in the DB (C-B3 updated the tier). The existing handler will work — it finds the charter tier by price ID. **No change needed** to `handle_subscription_created()`. | MCP: `subscription_tier.stripe_price_id_monthly` = `price_REDACTED...` for charter |
| **Subscription status for trialing** | The `subscription_status` table has a `trialing` code (`is_billing_active=true`). `handle_subscription_created()` currently sets status to `active` — for Charter trialing subscriptions, it should set `trialing` when `subscription.status == "trialing"`. **Update**: `handle_subscription_created()` should check the Stripe subscription status and map it: `trialing` → `trialing` status, `active` → `active` status. | MCP: `subscription_status` codes confirmed |
| **`checkout.session.completed` scope** | Stub only in C-B4. Full 10DLC provisioning transition is C-B9. The stub checks `metadata.purpose == "a2p_10dlc_setup"` and logs — C-B9 will add the `tenant_messaging_registration` status transition. | Spec §6.8 |
| **`trial_will_end` notification scope** | Stub only in C-B4. Full notification schedule (T-30/14/7/3/1) is C-B6. The stub logs the event — C-B6 will add Celery beat + email/push/in-app. | Spec §6.8, launch plan C-B6 |
