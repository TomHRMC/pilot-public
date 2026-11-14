# C-B14 — Full Test Suite + Stripe Live-Mode Bootstrap + End-to-End Rehearsal

**Batch**: C-B14
**Mode**: Pilot Python Engineer (Part A — test suites) → Tom (Part B — live-mode verification + E2E rehearsal)
**Prerequisite**: all C-B batches ✅ (C-B1 through C-B13 complete)
**Source of truth**: `pilot-tech-impl-spec-v1.md` §11 (Test Plan), §12 (Build Sequence)
**Status**: Design — Tom approved approach 2026-08-07
**Date**: August 7, 2026

> **Scope note**: C-B14 is the **launch gate** for the Charter program. It validates that the entire Charter lifecycle — signup, trial, pause, resume, upgrade, cancellation, 10DLC provisioning, entitlement enforcement, and cohort cap — works correctly end-to-end. All C-B1 through C-B13 batches must be complete before this batch runs.

---

## Overview

C-B14 has three deliverables:

1. **Part A (Python Engineer) — Automated test suites**: Three test files covering the 25 scenarios from spec §11:
   - **12 Stripe test-clock integration scenarios** (§11.1) — real Stripe test-mode API calls with test clocks
   - **8 Telnyx mock scenarios** (§11.2) — mocked Telnyx SDK responses simulating provisioning state machine transitions
   - **5 entitlement scenarios** (§11.3) — unit tests for entitlement enforcement across subscription states

2. **Part B (Tom) — Stripe live-mode verification**: Verify the live-mode Stripe objects created by C-B3's bootstrap script are correct and complete. This is a manual audit step using `stripe_bootstrap.py --mode live --audit`.

3. **Part B (Tom) — End-to-end rehearsal runbook**: A manual checklist Tom follows to sign up as a Charter member through the real production flow, attach a card, and verify the subscription is created correctly. This is added as a new section in `stripe-ops-runbook.md`.

---

## A. Input Read Summary

| Input | Source | Key findings |
|---|---|---|
| Spec §11.1 — Stripe Integration Scenarios | `pilot-tech-impl-spec-v1.md` §11.1 | 12 scenarios: trial pause, card attach + conversion, silent extension, extension rejection, 10DLC checkout + conversion, meter events during trial, meter overage, Charter→Teams upgrade, cancel, 12th signup cap flip, concurrent 11th/12th, duplicate webhook idempotency. Each requires its own test-clocked customer. |
| Spec §11.2 — Telnyx Scenarios | Same, §11.2 | 8 scenarios: EIN happy path, sole-prop happy path, sole-prop OTP timeout, brand rejected, campaign rejected, checkout abandoned, fee schedule change, month-4 recurring item. Use mock brands/campaigns. |
| Spec §11.3 — Entitlement Scenarios | Same, §11.3 | 5 scenarios: data export succeeds (D11), Teams-only feature blocked, paused SMS (⚠️ **corrected** — see §G), paused job creation blocked, paused data export succeeds. |
| Spec §13 — Q#4 resolution | Same, §13 + Appendix | Meter events aggregate across test-clock advances but are async — add 2-5s sleep before advancing clock. Verify via invoice amount, not meter events. Fallback: test overage with daily subscription if timing issues persist. |
| C-SPIKE-1 — Q#3 resolution | `pilot-launch-plan.md` §C-SPIKE-1 card | Resume call signature: `stripe.Subscription.resume(sub_id, billing_cycle_anchor="now")` after `customer.invoice_settings.default_payment_method`. **Critical**: check `sub.status` after resume — can return 200 but stay `paused` if payment fails. |
| C-SPIKE-1 — Q#4 resolution | Same | Meter events are write-only, processed async. Add `time.sleep(5)` before advancing test clock. Verify via `stripe.Invoice.list(subscription=...).data[0]` line item amount. |
| Live DB — `subscription_tier` | MCP (this session) | 4 tiers: charter (active, cap=12, price_locked, $49/mo, `price_REDACTED...`), trial (inactive, $0, 14d), starter (inactive, $59/mo, `price_REDACTED...`), teams (inactive, $179/mo, `price_REDACTED...`). Charter `stripe_price_id_annual` is NULL (monthly only). |
| Live DB — `tenant` | MCP (this session) | 1 active tenant, 1 `charter_eligible=true`, 0 `charter_member_number` assigned, 1 with `stripe_customer_id`. Columns: `charter_eligible` (bool, NOT NULL), `charter_member_number` (int, nullable), `free_period_ends_at` (timestamptz, nullable), `stripe_customer_id` (text, nullable). |
| Live DB — `subscription` | MCP (this session) | Columns: `psp_subscription_id`, `psp_customer_id`, `billing_interval` (default 'monthly'), `trial_ends_at`, `renews_at`, `cancel_at_period_end`, `is_active`, `stripe_schedule_id`. |
| Live DB — `subscription_status` | MCP (this session) | 6 codes: active (billing_active=true), canceled (false), past_due (true), paused (false), trialing (true), unpaid (false). |
| Live DB — `stripe_webhook_event_processed` | MCP (this session) | Columns: `id` (UUID PK), `event_id` (TEXT, unique — dedup), `processed_at`, `event_type`, `created_at`, `created_by`. AppendOnlyMixin (no updated_at). |
| Live DB — `alembic_version` | MCP (this session) | Head: `7f57c3f5f15c` (C-B10's migration). |
| Existing test infrastructure | `backend/tests/` search | All Stripe tests use mocked `_get_stripe_client`. No test-clock integration tests exist. E2E test in `test_invoice_stripe.py` uses real Stripe key (skips if not configured). Telnyx tests mock the SDK. Entitlement tests exist for `check_entitlement` + `is_subscription_billing_active`. |
| pytest.ini markers | `backend/pytest.ini` | `unit`, `integration`, `e2e`, `slow`, `requires_redis`, `requires_sendgrid`, `requires_telnyx`, `requires_whisper`, `skip_mock_entitlement_allowed`. No `requires_stripe` marker exists yet. |
| conftest auto-tagging | `backend/tests/conftest.py` | Tests marked `e2e`/`requires_sendgrid`/`requires_telnyx` auto-get `integration`. Tests with no integration-family marker auto-get `unit`. `-m "not integration"` excludes all external-service tests. |
| Stripe ops runbook | `stripe-ops-runbook.md` | Test mode: `sk_test_...`, `stripe_ids.test.json`, Stripe CLI for webhook forwarding. Test cards: `4242...` (success), `4000...0002` (decline), `4000...3155` (3DS). Live mode bootstrap already done (C-B3, August 4, 2026). |
| C-B7 override | `pilot-launch-plan.md` Appendix A, C-B7 row | **Tom decision 2026-08-05**: spec §9.3 SMS exception OVERRIDDEN — when paused → ALL services including SMS blocked, no exceptions. This corrects spec §11.3 scenario 3. |
| mvp-arch §16 | `mvp-arch.md` §16 | No §16 platform patterns apply to test suites. |

---

## B. Migration Plan

### B.1 — DB Changes

**No migration needed.** C-B14 is a test-only batch. All schema changes were made by C-B1 through C-B13. The test suites use existing tables, columns, and seed data.

### B.2 — Test Infrastructure Changes

Two small infrastructure changes are required:

#### B.2.1 — New pytest marker: `requires_stripe`

Add `requires_stripe` to `backend/pytest.ini` markers section:

```ini
requires_stripe: Tests that require a real Stripe test-mode API key (sk_test_...)
```

Add `requires_stripe` to the `implies_integration` set in `backend/tests/conftest.py` (around line 202):

```python
implies_integration = {
    "e2e",
    "requires_sendgrid",
    "requires_telnyx",
    "requires_stripe",  # NEW — C-B14 Stripe test-clock scenarios
}
```

This ensures `-m "not integration"` excludes Stripe test-clock tests, and `-m unit` does not accidentally include them.

#### B.2.2 — Stripe test-clock conftest fixtures

A new conftest file at `backend/tests/domains/subscriptions_usage/conftest_cb14.py` (or add to the domain conftest if one exists) providing:

| Fixture | Scope | Purpose |
|---|---|---|
| `stripe_test_key` | session | Returns `sk_test_...` from `settings.STRIPE_SECRET_KEY`; skips test if not a real test key (same pattern as `test_invoice_stripe.py:_get_stripe_key()`) |
| `stripe_cleanup` | function | Yields, then deletes all test customers/subscriptions/clocks created during the test (tracks created IDs in a list) |
| `make_clocked_customer` | function | Creates a Stripe `TestClock` + `Customer` on that clock; returns `(clock, customer)`; registers for cleanup |

### B.3 — MCP Verification Queries (pre-implementation)

The Python Engineer should run these before writing test assertions to verify current state:

```sql
-- 1. Verify subscription_tier Charter row
SELECT tier_name, is_active, signup_cap, price_locked, requires_payment_method,
       free_period_days, monthly_price_cents, stripe_price_id_monthly
FROM subscription_tier WHERE tier_name = 'charter';

-- 2. Verify subscription_status codes
SELECT code, name, is_billing_active FROM subscription_status ORDER BY code;

-- 3. Verify tenant charter columns
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'tenant'
  AND column_name IN ('charter_eligible', 'charter_member_number', 'free_period_ends_at',
                       'stripe_customer_id', 'current_subscription_tier_id')
ORDER BY ordinal_position;

-- 4. Verify subscription columns used in tests
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'subscription'
  AND column_name IN ('psp_subscription_id', 'psp_customer_id', 'billing_interval',
                       'trial_ends_at', 'renews_at', 'cancel_at_period_end', 'is_active',
                       'stripe_schedule_id', 'status_id')
ORDER BY ordinal_position;

-- 5. Verify stripe_webhook_event_processed dedup table
SELECT column_name, data_type FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'stripe_webhook_event_processed'
ORDER BY ordinal_position;
```

### B.4 — Pre-Implementation State

- `subscription_tier`: Charter active, cap=12, $49/mo, `stripe_price_id_monthly=price_REDACTED...`
- `subscription_status`: 6 codes (active, canceled, past_due, paused, trialing, unpaid)
- `tenant`: 1 active tenant, 1 charter_eligible, 0 charter_members
- `alembic_version`: `7f57c3f5f15c`
- Stripe test mode: `stripe_ids.test.json` committed, all 14 objects created (C-B3)
- Stripe live mode: bootstrap already run (C-B3, August 4, 2026), `pilot/prod/stripe` secrets active

### B.5 — Seed Data Rollout

**No seed data changes.** C-B14 is test-only. The test suites create their own test data (Stripe test customers, test clocks, mock Telnyx responses) and clean up after themselves.

---

## C. Execution Order

| Step | Task | Owner | Details |
|---|---|---|---|
| 1 | Add `requires_stripe` marker to `pytest.ini` | Python | One line in markers section |
| 2 | Add `requires_stripe` to `implies_integration` in `conftest.py` | Python | One line in the set |
| 3 | Create Stripe test-clock conftest fixtures | Python | `stripe_test_key`, `stripe_cleanup`, `make_clocked_customer` |
| 4 | Write `test_cb14_stripe_scenarios.py` — 12 Stripe scenarios | Python | `@pytest.mark.requires_stripe`; each creates own clocked customer; 2-5s sleep before clock advance |
| 5 | Write `test_cb14_telnyx_scenarios.py` — 8 Telnyx scenarios | Python | `@pytest.mark.unit`; mocked Telnyx SDK; simulates provisioning state machine transitions |
| 6 | Write `test_cb14_entitlement_scenarios.py` — 5 entitlement scenarios | Python | `@pytest.mark.unit`; `@pytest.mark.skip_mock_entitlement_allowed` on scenarios that test real entitlement enforcement |
| 7 | Run Phase 1 verification: `pytest -m unit --tb=no -q \| tail -5` | Python | Unit tests (Telnyx + entitlement) must pass |
| 8 | Run Phase 2 verification: `pytest -m "unit or requires_stripe" --tb=short` | Python | Full suite including Stripe integration tests (requires `STRIPE_SECRET_KEY=sk_test_...`) |
| 9 | Add §11 "End-to-End Rehearsal" section to `stripe-ops-runbook.md` | Python | Manual checklist for Tom |
| 10 | **Part B (Tom)**: Run `python scripts/stripe_bootstrap.py --mode live --audit` | Tom | Verify all live-mode Stripe objects exist |
| 11 | **Part B (Tom)**: Follow E2E rehearsal runbook | Tom | Sign up as Charter member, attach card, verify subscription, cancel |

---

## D. New API Endpoints

**No new API endpoints.** C-B14 tests existing endpoints and services from C-B1 through C-B13.

The test suites call these existing endpoints/services:

| Endpoint/Service | Used by scenario(s) | Source batch |
|---|---|---|
| `create_charter_subscription()` | Stripe 1, 2, 3, 6, 7, 10, 11 | C-B4 |
| `resume_subscription()` | Stripe 2 | C-B4 |
| `report_usage_event()` | Stripe 6, 7 | C-B4 |
| `upgrade_charter_to_teams()` | Stripe 8 | C-B12 |
| Cohort cap transaction (`SELECT FOR UPDATE`) | Stripe 10, 11 | C-B5 |
| Webhook dedup (`stripe_webhook_event_processed`) | Stripe 12 | C-B4 (batch_b14) |
| `extend_free_period()` | Stripe 3, 4 | C-B11 |
| 10DLC provisioning state machine | Telnyx 1-8 | C-B9 |
| `handle_checkout_session_completed()` | Telnyx 5, Stripe 5 | C-B9 |
| `create_recurring_carrier_item()` | Telnyx 8 | C-B10 |
| `is_subscription_billing_active()` | Entitlement 3, 4, 5 | C-B7 |
| `check_entitlement()` / `require_permission()` | Entitlement 1, 2 | Batch 1D |

---

## E. Pattern Reuse Decisions

No §16 platform patterns apply to test suites. However, the following test patterns from the existing codebase are reused:

| Pattern | Source | Applied to |
|---|---|---|
| Skip-if-no-real-key | `test_invoice_stripe.py:_get_stripe_key()` | Stripe test-clock scenarios (skip if `STRIPE_SECRET_KEY` is not a real `sk_test_...` key) |
| Mocked `_get_stripe_client` | All existing C-B4/C-B9/C-B11 tests | Telnyx scenarios (mock Stripe Checkout for 10DLC setup) |
| Mocked Telnyx SDK via `sys.modules` | `test_dlc_b5_delivery_status.py` | Telnyx scenarios (mock brand/campaign/number responses) |
| `skip_mock_entitlement_allowed` marker | `test_entitlement_enforcement_e2e.py` | Entitlement scenarios 3-5 (need real entitlement enforcement, not the autouse bypass) |
| Test-clock + sleep pattern | C-SPIKE-1 Q#4 resolution | Stripe scenarios 6, 7 (meter events) — `time.sleep(5)` before `TestClock.advance()` |

---

## F. Shared Module Interfaces & Celery Tasks

### F.1 — Stripe Test-Clock Helper Functions

The test suite needs helper functions (defined in the test file or conftest, not in production code):

```python
def create_clocked_customer(stripe, cleanup_registry: list) -> tuple:
    """Create a Stripe TestClock (frozen at now) + Customer on that clock.
    Returns (clock, customer). Registers both for cleanup."""
    ...

def advance_clock_and_wait(stripe, clock_id: str, days: int, sleep_seconds: int = 5):
    """Advance a test clock by N days. Sleeps before advancing to allow
    async meter event processing (C-SPIKE-1 Q#4 resolution)."""
    import time
    time.sleep(sleep_seconds)
    new_time = int((datetime.now(UTC) + timedelta(days=days)).timestamp())
    stripe.test_helpers.TestClock.advance(clock_id, frozen_time=new_time)

def cleanup_stripe_objects(stripe, registry: list):
    """Delete all test customers, subscriptions, and clocks in the registry.
    Best-effort — logs warnings on failure, does not raise."""
    ...
```

### F.2 — No New Celery Tasks

C-B14 does not add Celery tasks. The test suites call existing services directly.

### F.3 — No New Production Code

C-B14 is test-only. No changes to `backend/app/`, `backend/api/`, or `backend/services/` (except the two infrastructure changes in §B.2: pytest.ini marker + conftest.py implies_integration set).

---

## G. Open Questions Resolved

### G.1 — Spec §11.3 Scenario 3: Paused SMS Behavior (CORRECTED)

**Spec says**: "Paused tenant with active 10DLC sends SMS → **Succeeds** (§9.3)"

**Tom decision (2026-08-05, C-B7)**: spec §9.3 SMS exception OVERRIDDEN — when paused → **ALL services including SMS blocked, no exceptions**.

**Resolution**: The C-B14 entitlement scenario 3 test must expect **Blocked** (HTTP 402), not **Succeeds**. The test should verify that `_send_communication_impl` returns a 402 RFC 7807 error when the subscription is paused, regardless of 10DLC registration status.

**Spec update needed**: `pilot-tech-impl-spec-v1.md` §11.3 scenario 3 should be corrected from "Succeeds" to "Blocked (402)". This is a documentation fix, not a code change — the code already blocks SMS when paused (C-B7 implemented the override).

### G.2 — Stripe Live-Mode Bootstrap Already Complete

**Question**: Does C-B14 need to run `stripe_bootstrap.py --mode live`?

**Resolution**: No — C-B3 already ran the live-mode bootstrap on August 4, 2026. The ops runbook confirms: "✅ Activated — `pilot/prod/stripe` has live keys as of August 4, 2026" and "All 14 Stripe objects created via bootstrap script (C-B3)". C-B14's Part B is a **verification** step: run `--mode live --audit` to confirm all objects still exist and are correctly configured. If any are missing, Tom re-runs the bootstrap.

### G.3 — Test-Clock Cleanup Strategy

**Question**: How do we clean up Stripe test objects after integration tests?

**Resolution**: Each test registers created objects (customers, subscriptions, clocks) in a cleanup list. The `stripe_cleanup` fixture (function scope) deletes them after the test yields. Best-effort deletion — if a customer can't be deleted (e.g., has an active subscription), the fixture logs a warning and moves on. Stripe test-mode objects are automatically purged by Stripe after a period, so leftover objects are not a long-term concern.

### G.4 — Meter Event Timing (C-SPIKE-1 Q#4)

**Question**: Do Billing Meter events aggregate correctly across test-clock advances?

**Resolution**: Yes, but meter events are processed asynchronously. The test suite must:
1. Call `stripe.billing.MeterEvent.create()` to report usage
2. `time.sleep(5)` to allow async processing
3. Then advance the test clock
4. Verify the resulting invoice's line item amount (not the meter event itself — meter events are write-only)

**Fallback** (from spec §11.1 caveat): If timing issues persist, test overage scenarios (6, 7) against a short-interval (daily) subscription rather than a clocked 90-day one.

### G.5 — Scenario 10/11: Cohort Cap with Real Stripe API

**Question**: Scenarios 10 (12th signup) and 11 (concurrent 11th/12th) test the cohort cap transaction. Do they need real Stripe subscriptions?

**Resolution**: Yes — the scenarios create real Stripe test-mode subscriptions to count as charter members. The cohort cap logic (`SELECT ... FOR UPDATE` + `charter_member_number` assignment + `is_active` flip) is a DB transaction, but the Stripe subscription creation is part of the signup flow. The tests create 12 clocked customers with subscriptions, then verify the 12th signup flips `is_active=false` and the 13th attempt sees no Charter option.

**Important**: These tests modify the `subscription_tier.is_active` flag. The `stripe_cleanup` fixture must reset `is_active=true` for the Charter tier after each test to avoid breaking subsequent tests.

### G.6 — Telnyx Scenarios: Mock vs Real API

**Question**: Do the Telnyx scenarios use real Telnyx API calls (mock brands/campaigns) or mocked SDK responses?

**Resolution**: Mocked SDK responses. The spec says "Use Telnyx mock brands and campaigns" — but the existing test infrastructure mocks the Telnyx SDK entirely (via `sys.modules` patching). The C-B14 Telnyx scenarios simulate the provisioning state machine transitions by mocking Telnyx webhook responses (brand approved, campaign rejected, OTP delivered, etc.) and verifying the state machine transitions correctly. This keeps them as `@pytest.mark.unit` tests that run in the default unit suite without Telnyx credentials.

---

## H. Surface Mockup Reference

Not applicable — C-B14 is a backend test-only batch with no UI surfaces.

---

## I. Component Manifest

Not applicable — C-B14 is a backend test-only batch with no new UI components.

---

## Test Scenario Details

### §11.1 — Stripe Integration Scenarios (12)

All marked `@pytest.mark.requires_stripe`. Each creates its own test-clocked customer. Skip if `STRIPE_SECRET_KEY` is not a real `sk_test_...` key.

| # | Scenario | Test approach | Key assertions |
|---|---|---|---|
| 1 | Charter signup, no card, advance 91d | Create clocked customer + charter subscription (trial, no PM). Advance 91d. | `subscription.status == "paused"`; tenant read-only (`is_subscription_billing_active() == False`) |
| 2 | Charter signup, card at day 85, advance 91d | Create clocked customer + charter subscription. Advance 85d. Attach PM (`4242...`). Call `resume_subscription()`. Advance 6d. | `subscription.status == "active"`; invoice paid ($49); `is_subscription_billing_active() == True` |
| 3 | Silent extension at day 80 (+90d), advance to day 95 | Create clocked customer + charter subscription. Advance 80d. Call `extend_free_period(+90d)`. Advance 15d. | `subscription.status == "trialing"`; zero customer-facing events; `free_period_ends_at` updated |
| 4 | Extension at day 95 (already paused) | Create clocked customer + charter subscription. Advance 91d (pauses). Call `extend_free_period()`. | Rejected with operator error (subscription already paused) |
| 5 | 10DLC Checkout at day 20, advance to day 91 | Create clocked customer + charter subscription. Advance 20d. Create 10DLC Checkout session (mock Stripe Checkout). Advance 71d. | PM retained via `setup_future_usage: off_session`; subscription converts automatically |
| 6 | Meter events during trial | Create clocked customer + charter subscription. Report `voice_minutes` meter event. Advance 91d. | Invoice at $0 (trial includes overage); meter event landed |
| 7 | Meter events post-conversion above 90 min / 100 seg | Create clocked customer + charter subscription + PM. Advance 91d (converts). Report 100 voice minutes + 100 SMS segments. Advance 30d. | Overage invoiced at $0.05/unit ($5 voice + $5 SMS = $10 overage) |
| 8 | Charter → Teams upgrade | Create clocked customer + charter subscription + PM. Advance 91d (active). Call `upgrade_charter_to_teams()`. | Charter item removed; Teams item added; prorations correct; `charter_eligible == False` |
| 9 | Cancel | Create clocked customer + charter subscription. Cancel subscription. | `charter_eligible == False`; does not flip back on resubscribe attempt |
| 10 | 12th signup | Create 12 clocked customers + charter subscriptions. On 12th: verify cap transaction. | `subscription_tier.is_active == False` in same transaction; 13th attempt sees no Charter option |
| 11 | Concurrent 11th and 12th signups | Create 11 clocked customers. Fire 2 concurrent signup requests (threads). | Row lock holds; exactly 12 created; no duplicate `charter_member_number` |
| 12 | Duplicate webhook delivery | Create clocked customer + charter subscription. Send same webhook event twice. | Idempotent on `event.id`; no double-processing; `stripe_webhook_event_processed` has exactly 1 row |

**Cleanup**: After each test, delete test customers, subscriptions, and clocks. Reset `subscription_tier.is_active = true` for Charter if modified (scenarios 10, 11).

### §11.2 — Telnyx Mock Scenarios (8)

All marked `@pytest.mark.unit`. Mocked Telnyx SDK via `sys.modules` patching (same pattern as `test_dlc_b5_delivery_status.py`).

| # | Scenario | Test approach | Key assertions |
|---|---|---|---|
| 1 | Standard (EIN) happy path | Create `tenant_messaging_registration` in `not_started`. Mock Telnyx brand creation → `approved`. Mock campaign creation → `approved`. Mock number assignment. | State transitions: `not_started → brand_submitted → brand_approved → campaign_submitted → campaign_approved → awaiting_number_selection → active` |
| 2 | Sole prop happy path | Same as #1 but `entity_type = "sole_prop"`. Mock brand creation → `approved`. Mock OTP required. | State halts at `awaiting_otp`; in-app PIN panel appears (verify via state field) |
| 3 | Sole prop OTP timeout (>24h) | Same as #2. Advance time 18h. Mock OTP timeout alert. | Operator alerted at T+18h; state returns to `quoting` without re-charge |
| 4 | Brand rejected | Create registration. Mock brand creation → `rejected`. | Automatic Stripe refund; operator alert; terminal state (`brand_rejected`) |
| 5 | Campaign rejected | Create registration. Mock brand → `approved`. Mock campaign → `rejected`. | Partial refund; operator alert; state `campaign_rejected` |
| 6 | Checkout abandoned | Create registration. Mock Stripe Checkout session created. Do NOT complete checkout. | No Telnyx call made; state stays `awaiting_payment` |
| 7 | Fee schedule change between quote and payment | Create registration. Get quote ($X). Change `carrier_fee_schedule` fee. Complete checkout. | Quote honored (original $X); delta logged for operator review |
| 8 | Month 4 recurring item creation | Create registration (active, >90d old, no recurring item). Trigger `create_recurring_carrier_item()`. | Correct amount (from `registration.quoted_monthly_cents`); correct label; no double-charge for prepaid window |

### §11.3 — Entitlement Scenarios (5)

All marked `@pytest.mark.unit`. Scenarios 3-5 use `@pytest.mark.skip_mock_entitlement_allowed` to test real entitlement enforcement.

| # | Scenario | Test approach | Key assertions |
|---|---|---|---|
| 1 | Charter tenant requests data export | Create tenant with Charter subscription (active). Call data export endpoint. | Succeeds (D11 — data export on all plans) |
| 2 | Charter tenant attempts Teams-only feature | Create tenant with Charter subscription. Call a Teams-only feature endpoint. | Blocked with upgrade CTA (402 or feature-gate response) |
| 3 | Paused tenant sends SMS | Create tenant with paused subscription. Call `_send_communication_impl` with SMS channel. | **Blocked (402 RFC 7807)** — ⚠️ corrected from spec "Succeeds" per Tom decision 2026-08-05 (C-B7 override) |
| 4 | Paused tenant creates a job | Create tenant with paused subscription. Call job creation endpoint. | Blocked with paywall (402) |
| 5 | Paused tenant exports data | Create tenant with paused subscription. Call data export endpoint. | Succeeds (data export allowed even when paused) |

---

## Part B — Tom's Manual Steps

### B.1 — Stripe Live-Mode Audit

```bash
cd <repo>/backend
source .venv/bin/activate

# Verify all live-mode Stripe objects exist
python scripts/stripe_bootstrap.py --mode live --audit
```

**Expected**: 3 Products, 2 Meters, 9 Prices — all marked as "managed" (have `pilot_key` metadata). If any are missing, run:

```bash
python scripts/stripe_bootstrap.py --mode live --i-am-sure
```

### B.2 — End-to-End Rehearsal Runbook

This runbook will be added as §11 of `stripe-ops-runbook.md`. The Python Engineer authors the section; Tom executes it.

**Prerequisites**:
- Stripe CLI running: `stripe listen --forward-to localhost:8000/api/v1/webhooks/stripe`
- `STRIPE_SECRET_KEY=sk_test_...` in `.env`
- `STRIPE_MODE=test` in `.env`
- Local dev server running (`uvicorn app.main:app --reload`)

**Steps**:
1. Sign up as a new Charter member through the web app (`/signup`)
2. Complete the wizard (skip Step 4 payment — Charter requires no card)
3. Verify: subscription created in Stripe Dashboard (test mode) with `status=trialing`, `trial_end` = 90 days out
4. Verify: `tenant.charter_eligible=true`, `tenant.charter_member_number` assigned, `tenant.free_period_ends_at` set
5. Verify: `subscription_tier.charter` `is_active=true` (cap not reached)
6. Attach a test card (`4242 4242 4242 4242`) via the billing settings page
7. Verify: `stripe.Customer.modify` called with `invoice_settings.default_payment_method`
8. In Stripe Dashboard, advance the test clock to 91 days (or use the Stripe CLI)
9. Verify: subscription transitions to `active`, invoice paid ($49)
10. Verify: `is_subscription_billing_active() == True` — app fully functional
11. Cancel the subscription
12. Verify: `charter_eligible=false`, subscription `canceled`
13. Attempt to resubscribe — verify Charter option not available (`charter_eligible=false` persists)
14. Clean up: delete the test customer in Stripe Dashboard

---

## Cost Impact

**$0.** C-B14 is test-only. No new infrastructure, no new AWS services, no new external API costs. Stripe test-mode API calls are free. Telnyx mock scenarios use mocked SDK calls (no real Telnyx API calls). The live-mode audit is a read-only Stripe API call (free).

---

## Definition of Done

### Phase 1 (Unit tests only — no Stripe key required)

- [ ] `requires_stripe` marker added to `pytest.ini`
- [ ] `requires_stripe` added to `implies_integration` in `conftest.py`
- [ ] `test_cb14_telnyx_scenarios.py` — 8 Telnyx mock scenarios pass
- [ ] `test_cb14_entitlement_scenarios.py` — 5 entitlement scenarios pass
- [ ] `pytest -m unit --tb=no -q | tail -5` — 0 failures, 0 regressions
- [ ] §11 "End-to-End Rehearsal" section added to `stripe-ops-runbook.md`

### Phase 2 (Full suite — requires `STRIPE_SECRET_KEY=sk_test_...`)

- [ ] Stripe test-clock conftest fixtures created
- [ ] `test_cb14_stripe_scenarios.py` — 12 Stripe test-clock scenarios pass
- [ ] `pytest -m "unit or requires_stripe" --tb=short` — 0 failures
- [ ] Ruff: 0 errors on all changed files
- [ ] All DB-touching routes are sync `def` — no `async def`
- [ ] Pydantic v2 idioms only
- [ ] No module-level `TestClient`
- [ ] `pytestmark` with `domain_subscriptions_usage` + `pytest.mark.unit` (Telnyx/entitlement) or `pytest.mark.requires_stripe` (Stripe scenarios) on all new tests

### Part B (Tom — manual)

- [ ] `python scripts/stripe_bootstrap.py --mode live --audit` — all 14 objects confirmed
- [ ] E2E rehearsal runbook executed — all 14 steps pass
- [ ] Test customer cleaned up in Stripe Dashboard
