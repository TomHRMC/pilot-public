# Implementation Prompt: C-B14 — Full Test Suite + Stripe Live-Mode Verification + E2E Rehearsal Runbook

**Mode**: Pilot Python Engineer
**Batch**: C-B14
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §2.0 row 14s
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-c-b14-design.md`
**Estimated session**: 4–6 hours
**Platform**: Backend only (`backend/`)
**Frontend companion**: None (test-only batch)

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-python-engineer/python-engineer-rules.md`** — full document; the 25 hard rules are non-negotiable STOPs
- **`dev-docs/architecture-design/pilot-python-engineer-methods.md`** — §13 (Alembic), §8 (Router Design), §5 (Model Design), §16 (Standard Task Workflow)
- **`backend/tests/README-adding-tests.md`** — full document; this governs all test file structure, domain markers, and fixture rules
- **`dev-docs/architecture-design/batch-designs/batch-c-b14-design.md`** — the full design doc for this batch

Critical rules for this batch:

- **Rule 1**: Never guess column names, data types, or table names. Use `postgres-local` MCP to verify every name before use. If MCP returns an error → **STOP and ask Tom**.
- **Rule 5**: Never use module-level `TestClient` in any test file. Always use the `client` fixture from `conftest.py`.
- **Rule 11**: If ANY test fails during your work — even one that appears to be a pre-existing failure — **you must fix it before declaring the batch done**. There is no "not my fault" exception.
- **Rule 12 (sync routes)**: This batch does NOT add new routes. All existing routes are sync `def`.
- **Rule 14 (Ruff)**: Run ruff only against changed files. Fix ALL errors in those files.
- **Rule 16 (verify, don't assume)**: 186 tables exist. Query `information_schema.columns` for every table you touch this session before writing SQL.

**This batch is test-only.** No migration, no new endpoints, no new production code (except two small infrastructure changes: `pytest.ini` marker + `conftest.py` implies_integration set). The only production-adjacent file you modify is `stripe-ops-runbook.md` (documentation).

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

```sql
-- 1. Verify subscription_tier Charter row (used by Stripe scenarios)
SELECT tier_name, is_active, signup_cap, price_locked, requires_payment_method,
       free_period_days, monthly_price_cents, stripe_price_id_monthly
FROM subscription_tier WHERE tier_name = 'charter';

-- 2. Verify subscription_status codes (used by entitlement scenarios)
SELECT code, name, is_billing_active FROM subscription_status ORDER BY code;

-- 3. Verify tenant charter columns (used by cohort cap scenarios)
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'tenant'
  AND column_name IN ('charter_eligible', 'charter_member_number', 'free_period_ends_at',
                       'stripe_customer_id', 'current_subscription_tier_id')
ORDER BY ordinal_position;

-- 4. Verify subscription columns (used by Stripe lifecycle scenarios)
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'subscription'
  AND column_name IN ('psp_subscription_id', 'psp_customer_id', 'billing_interval',
                       'trial_ends_at', 'renews_at', 'cancel_at_period_end', 'is_active',
                       'stripe_schedule_id', 'status_id')
ORDER BY ordinal_position;

-- 5. Verify stripe_webhook_event_processed dedup table (scenario 12)
SELECT column_name, data_type FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'stripe_webhook_event_processed'
ORDER BY ordinal_position;

-- 6. Verify tenant_messaging_registration columns (Telnyx scenarios)
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'tenant_messaging_registration'
ORDER BY ordinal_position;
```

> **MCP Usage Rule**: The `postgres-local` MCP is for **read-only verification only**. Use it to confirm table names, column types, and existing data. Never use it to INSERT, UPDATE, or DELETE — all data changes go through the application code, seed scripts, or Alembic migrations. If a query fails or returns an error → STOP and ask Tom before proceeding.

---

## Pre-Work: Read These Source Files

Read **all** of these before writing any code:

- `dev-docs/architecture-design/batch-designs/batch-c-b14-design.md` — the full design doc (sections A–G + test scenario details)
- `dev-docs/marketing-analysis/pilot-tech-impl-spec-v1.md` §11 (Test Plan) — the 25 scenarios you are implementing
- `backend/pytest.ini` — current markers (you will add `requires_stripe`)
- `backend/tests/conftest.py` — auto-tagging logic (you will add `requires_stripe` to `implies_integration`)
- `backend/tests/README-adding-tests.md` — test file structure, domain markers, fixture rules
- `backend/tests/e2e/cp6_invoice_stripe/test_invoice_stripe.py` — existing pattern for skip-if-no-real-Stripe-key (`_get_stripe_key()`)
- `backend/tests/domains/subscriptions_usage/test_cb4_create_charter_subscription.py` — existing pattern for mocked Stripe subscription creation
- `backend/tests/domains/subscriptions_usage/test_cb4_resume_subscription.py` — existing pattern for mocked resume (you will write the REAL version)
- `backend/tests/domains/subscriptions_usage/test_cb4_report_usage_event.py` — existing pattern for mocked meter events (you will write the REAL version)
- `backend/tests/domains/subscriptions_usage/test_cb5_step4_cohort_cap.py` — existing pattern for cohort cap transaction
- `backend/tests/domains/notifications_comms/test_dlc_b5_delivery_status.py` — existing pattern for mocked Telnyx SDK via `sys.modules`
- `backend/tests/domains/subscriptions_usage/test_cb9_messaging_provisioning.py` — existing pattern for 10DLC provisioning state machine tests
- `backend/tests/domains/notifications_comms/test_cb7_billing_active_check.py` — existing pattern for `is_subscription_billing_active()` tests
- `backend/tests/integration/test_entitlement_enforcement_e2e.py` — existing pattern for `skip_mock_entitlement_allowed` + real entitlement enforcement
- `backend/services/stripe_subscriptions.py` — the services you are testing (create_charter_subscription, resume_subscription, report_usage_event, upgrade_charter_to_teams)
- `backend/services/entitlement_service.py` — `is_subscription_billing_active()`, `check_entitlement()`
- `backend/services/messaging_provisioning.py` — 10DLC provisioning state machine
- `backend/services/messaging_checkout.py` — Stripe Checkout for 10DLC setup
- `backend/services/messaging_recurring.py` — recurring carrier item creation
- `backend/integrations/stripe/stripe-ops-runbook.md` — you will add §11 (E2E Rehearsal Runbook)
- `backend/scripts/stripe_ids.test.json` — Stripe object ID mapping (used by test-clock scenarios)

---

## Background / Context

C-B14 is the **launch gate** for the Charter program. It validates the entire Charter lifecycle end-to-end through 25 test scenarios from spec §11:

- **12 Stripe test-clock integration scenarios** — real Stripe test-mode API calls with test clocks (trial, pause, resume, upgrade, cancel, meter events, cohort cap, webhook dedup)
- **8 Telnyx mock scenarios** — mocked Telnyx SDK simulating 10DLC provisioning state machine transitions
- **5 entitlement scenarios** — real entitlement enforcement for paused/active/charter states

The Stripe scenarios are the most complex — they make real API calls against the Stripe test-mode account, each creating its own test-clocked customer. C-SPIKE-1 resolved the key technical question: meter events are async, so add a 2-5s sleep before advancing test clocks.

**Key correction**: Spec §11.3 scenario 3 (paused SMS) was corrected — when paused, ALL services including SMS are blocked (Tom decision 2026-08-05, C-B7 override). The test must expect **Blocked (402)**, not "Succeeds".

---

## Task 1 — pytest Infrastructure: Add `requires_stripe` Marker

### What to change

1. **`backend/pytest.ini`** — Add `requires_stripe` to the markers section (after `requires_whisper`):

```ini
    requires_stripe: Tests that require a real Stripe test-mode API key (sk_test_...)
```

2. **`backend/tests/conftest.py`** — Add `requires_stripe` to the `implies_integration` set (around line 202):

```python
implies_integration = {
    "e2e",
    "requires_sendgrid",
    "requires_telnyx",
    "requires_stripe",  # C-B14 — Stripe test-clock scenarios
}
```

This ensures `-m "not integration"` excludes Stripe test-clock tests, and `-m unit` does not include them.

### Verification

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=no -q 2>&1 | tail -5
```

Confirm the count matches your baseline (no tests should have changed yet).

---

## Task 2 — Telnyx Mock Scenarios (8 tests, unit-level)

### What to create

Create `backend/tests/domains/subscriptions_usage/test_cb14_telnyx_scenarios.py`:

- `pytestmark = [pytest.mark.domain_subscriptions_usage, pytest.mark.unit]`
- 8 test functions, one per spec §11.2 scenario
- Mock Telnyx SDK via `sys.modules` patching (same pattern as `test_dlc_b5_delivery_status.py`)
- Mock Stripe Checkout where needed (same pattern as `test_cb9_messaging_provisioning.py`)
- Test the provisioning state machine transitions, NOT real Telnyx API calls

### Scenario details (from design doc §11.2)

| # | Test name | What it tests | Key assertions |
|---|---|---|---|
| 1 | `test_ein_happy_path` | Standard EIN brand → campaign → number assignment | State: `not_started → brand_submitted → brand_approved → campaign_submitted → campaign_approved → awaiting_number_selection → active` |
| 2 | `test_sole_prop_happy_path` | Sole prop brand → OTP required | State halts at `awaiting_otp` |
| 3 | `test_sole_prop_otp_timeout` | OTP >24h timeout | Operator alerted at T+18h; state returns to `quoting` |
| 4 | `test_brand_rejected` | Brand creation rejected | Automatic Stripe refund; state `brand_rejected` |
| 5 | `test_campaign_rejected` | Campaign creation rejected | Partial refund; state `campaign_rejected` |
| 6 | `test_checkout_abandoned` | Checkout session created, not completed | No Telnyx call; state stays `awaiting_payment` |
| 7 | `test_fee_schedule_change` | Fee changes between quote and payment | Quote honored; delta logged |
| 8 | `test_month4_recurring_item` | Registration active >90d, no recurring item | Correct amount from `quoted_monthly_cents`; no double-charge |

### Key patterns

- Use `test_tenant` fixture for the tenant context
- Create `tenant_messaging_registration` rows directly in `db_session` (do NOT use real Telnyx API)
- Mock `TelnyxSmsCarrier` methods to return simulated responses (brand approved, campaign rejected, etc.)
- Mock `stripe_subscriptions._get_stripe_client` for Checkout scenarios
- Assert on `registration.status` field transitions
- Assert on DB state (refund rows, recurring item fields)

### Intermediate verification

```bash
python -m pytest tests/domains/subscriptions_usage/test_cb14_telnyx_scenarios.py -v --tb=short 2>&1 | tail -20
```

---

## Task 3 — Entitlement Scenarios (5 tests, unit-level)

### What to create

Create `backend/tests/domains/subscriptions_usage/test_cb14_entitlement_scenarios.py`:

- `pytestmark = [pytest.mark.domain_subscriptions_usage, pytest.mark.unit]`
- Scenarios 3, 4, 5 need `@pytest.mark.skip_mock_entitlement_allowed` (they test real entitlement enforcement)
- Scenarios 1, 2 can use the default autouse `mock_entitlement_allowed` (they test allowed behavior)

### Scenario details (from design doc §11.3)

| # | Test name | What it tests | Key assertions |
|---|---|---|---|
| 1 | `test_charter_data_export_succeeds` | Charter tenant (active) requests data export | Succeeds (D11 — data export on all plans) |
| 2 | `test_charter_teams_only_feature_blocked` | Charter tenant attempts Teams-only feature | Blocked with upgrade CTA |
| 3 | `test_paused_sms_blocked` | Paused tenant sends SMS | **Blocked (402 RFC 7807)** — ⚠️ corrected per Tom decision 2026-08-05 (C-B7 override). When paused → ALL services including SMS blocked. |
| 4 | `test_paused_job_creation_blocked` | Paused tenant creates a job | Blocked with paywall (402) |
| 5 | `test_paused_data_export_succeeds` | Paused tenant exports data | Succeeds (data export allowed even when paused) |

### Key patterns

- For scenarios 3-5: create a `Subscription` row with `status_id` pointing to the `paused` subscription_status (MCP-verified UUID)
- Use `is_subscription_billing_active()` directly for scenarios 3-5
- For scenario 3: call `_send_communication_impl` or the SMS send endpoint and assert 402
- For scenario 4: call the job creation endpoint and assert 402
- For scenario 5: call the data export endpoint and assert success
- Use `second_tenant` for isolation (avoid mutating `test_tenant` seed data)

### Intermediate verification

```bash
python -m pytest tests/domains/subscriptions_usage/test_cb14_entitlement_scenarios.py -v --tb=short 2>&1 | tail -20
```

---

## Task 4 — Stripe Test-Clock Scenarios (12 tests, integration-level)

### What to create

Create `backend/tests/domains/subscriptions_usage/test_cb14_stripe_scenarios.py`:

- `pytestmark = [pytest.mark.domain_subscriptions_usage, pytest.mark.requires_stripe]`
- Each test creates its own test-clocked customer
- Skip if `STRIPE_SECRET_KEY` is not a real `sk_test_...` key (same pattern as `test_invoice_stripe.py:_get_stripe_key()`)
- **2-5s sleep before advancing test clocks** (C-SPIKE-1 Q#4 resolution)
- **Cleanup**: delete test customers, subscriptions, clocks after each test
- **Reset `subscription_tier.is_active = true`** for Charter if modified (scenarios 10, 11)

### Conftest fixtures

Create `backend/tests/domains/subscriptions_usage/conftest_cb14.py` (or add to domain conftest if one exists):

```python
import time
import pytest
from datetime import datetime, timedelta, UTC

@pytest.fixture(scope="session")
def stripe_test_key():
    """Return sk_test_... key or skip if not available."""
    from core.config import settings
    key = getattr(settings, 'STRIPE_SECRET_KEY', None)
    if not key or not key.startswith('sk_test_'):
        pytest.skip("Real Stripe test-mode key not configured — Stripe scenarios skipped")
    return key

@pytest.fixture
def stripe_cleanup():
    """Track and clean up Stripe test objects after each test."""
    registry = []
    yield registry
    # Best-effort cleanup — delete clocks, subscriptions, customers
    # Import stripe here to avoid module-level import issues
    import stripe
    for obj_type, obj_id in reversed(registry):
        try:
            if obj_type == 'clock':
                stripe.test_helpers.TestClock.delete(obj_id)
            elif obj_type == 'subscription':
                stripe.Subscription.delete(obj_id, cancel_at_period_end=False)
            elif obj_type == 'customer':
                stripe.Customer.delete(obj_id)
        except Exception:
            pass  # best-effort

@pytest.fixture
def make_clocked_customer(stripe_test_key, stripe_cleanup):
    """Create a Stripe TestClock + Customer. Returns (clock, customer)."""
    import stripe
    stripe.api_key = stripe_test_key
    now = int(datetime.now(UTC).timestamp())
    clock = stripe.test_helpers.TestClock.create(frozen_time=now)
    customer = stripe.Customer.create(
        email=f"cb14-test-{clock.id[:8]}@pilot.local",
        test_clock=clock.id,
    )
    stripe_cleanup.append(('clock', clock.id))
    stripe_cleanup.append(('customer', customer.id))
    return clock, customer

def advance_clock_and_wait(stripe, clock_id, days, sleep_seconds=5):
    """Advance test clock by N days. Sleeps first for async meter processing."""
    time.sleep(sleep_seconds)
    new_time = int((datetime.now(UTC) + timedelta(days=days)).timestamp())
    stripe.test_helpers.TestClock.advance(clock_id, frozen_time=new_time)
```

### Scenario details (from design doc §11.1)

| # | Test name | Approach | Key assertions |
|---|---|---|---|
| 1 | `test_charter_signup_no_card_advance_91d` | Create clocked customer + charter subscription (trial, no PM). Advance 91d. | `sub.status == "paused"`; `is_subscription_billing_active() == False` |
| 2 | `test_charter_signup_card_at_85d_advance_91d` | Create clocked customer + charter subscription. Advance 85d. Attach PM (`4242...`). Call `resume_subscription()`. Advance 6d. | `sub.status == "active"`; invoice paid ($49) |
| 3 | `test_silent_extension_at_80d` | Create clocked customer + charter subscription. Advance 80d. Call `extend_free_period(+90d)`. Advance 15d. | `sub.status == "trialing"`; `free_period_ends_at` updated |
| 4 | `test_extension_at_95d_already_paused` | Create clocked customer + charter subscription. Advance 91d (pauses). Call `extend_free_period()`. | Rejected with operator error |
| 5 | `test_10dlc_checkout_at_20d_advance_91d` | Create clocked customer + charter subscription. Advance 20d. Create 10DLC Checkout (mock Stripe Checkout). Advance 71d. | PM retained; subscription converts automatically |
| 6 | `test_meter_events_during_trial` | Create clocked customer + charter subscription. Report `voice_minutes` meter event. Advance 91d. | Invoice at $0 (trial includes overage) |
| 7 | `test_meter_events_post_conversion_overage` | Create clocked customer + charter subscription + PM. Advance 91d. Report 100 voice + 100 SMS. Advance 30d. | Overage invoiced at $0.05/unit ($10 total) |
| 8 | `test_charter_to_teams_upgrade` | Create clocked customer + charter subscription + PM. Advance 91d. Call `upgrade_charter_to_teams()`. | Charter item removed; Teams item added; `charter_eligible == False` |
| 9 | `test_cancel` | Create clocked customer + charter subscription. Cancel. | `charter_eligible == False`; stays false on resubscribe |
| 10 | `test_12th_signup_cap_flip` | Create 12 clocked customers + charter subscriptions. On 12th: verify cap. | `subscription_tier.is_active == False`; 13th sees no Charter |
| 11 | `test_concurrent_11th_12th_signups` | Create 11 clocked customers. Fire 2 concurrent signups (threads). | Exactly 12 created; no duplicate `charter_member_number` |
| 12 | `test_duplicate_webhook_idempotent` | Create clocked customer + charter subscription. Send same webhook event twice. | Idempotent on `event.id`; 1 row in `stripe_webhook_event_processed` |

### Critical implementation notes

1. **Use `stripe_ids.test.json`** for price IDs — load via `core.stripe_config.get_stripe_ids()`
2. **Test cards**: `4242 4242 4242 4242` (success), `4000 0000 0000 0002` (decline)
3. **Meter events**: `stripe.billing.MeterEvent.create(event_name="voice_minutes", payload={"value": "25"}, customer=customer_id)` — then `time.sleep(5)` before advancing clock
4. **Verify via invoice amount**, not meter events (meter events are write-only)
5. **Scenario 10/11 cleanup**: Reset `subscription_tier.is_active = true` for Charter after the test (use `db_session`)
6. **Scenario 12**: Use the existing webhook endpoint `/api/v1/webhooks/stripe` with a real Stripe event payload (signed) — or call `_process_stripe_event()` directly with a mock event dict (same pattern as `test_stripe_webhook.py`)

### Intermediate verification

```bash
# These require STRIPE_SECRET_KEY=sk_test_... in .env
python -m pytest tests/domains/subscriptions_usage/test_cb14_stripe_scenarios.py -v --tb=short 2>&1 | tail -30
```

> **If Stripe test-clock tests are slow or flaky**: This is expected. Each test makes real API calls with sleeps. The full suite of 12 tests may take 5-10 minutes. If a specific scenario is consistently failing due to timing, use the fallback from spec §11.1: test overage with a daily subscription instead of a 90-day clocked one.

---

## Task 5 — Add §11 E2E Rehearsal Runbook to stripe-ops-runbook.md

### What to change

Add a new §11 section to `dev-docs/integrations/stripe/stripe-ops-runbook.md` after §10 (Secrets Management):

```markdown
## 11. End-to-End Rehearsal (C-B14)

### Prerequisites

- Stripe CLI running: `stripe listen --forward-to localhost:8000/api/v1/webhooks/stripe`
- `STRIPE_SECRET_KEY=sk_test_...` in `.env`
- `STRIPE_MODE=test` in `.env`
- Local dev server running (`uvicorn app.main:app --reload`)

### Steps

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
```

---

## Final Verification

### Phase 1 — Unit Tests Only (run after each task group during development)

```bash
cd <repo>/backend
source .venv/bin/activate

# Unit tests only — fast feedback loop during implementation
python -m pytest -m unit --tb=short -q 2>&1 | tail -10
```

All unit tests must pass before moving to the next task. Fix any unit failure — including failures that appear to be caused by code outside your batch — before proceeding.

### Phase 2 — Lint (changed files only) + Full Suite (run once, at the very end, before DoD sign-off)

```bash
cd <repo>/backend
source .venv/bin/activate

# Lint + format gate — CHANGED FILES ONLY
CHANGED_PY=$(git diff --name-only --diff-filter=d HEAD -- '*.py' | sed 's|^backend/||')

if [ -n "$CHANGED_PY" ]; then
    ruff check --fix $CHANGED_PY
    ruff format $CHANGED_PY
    ruff check $CHANGED_PY
fi

# Full suite including integration tests (requires STRIPE_SECRET_KEY=sk_test_... for Stripe scenarios)
python -m pytest --tb=short -q 2>&1 | tail -10

# Batch-specific spot checks
python -m pytest tests/domains/subscriptions_usage/test_cb14_telnyx_scenarios.py -v 2>&1 | tail -20
python -m pytest tests/domains/subscriptions_usage/test_cb14_entitlement_scenarios.py -v 2>&1 | tail -20
python -m pytest tests/domains/subscriptions_usage/test_cb14_stripe_scenarios.py -v 2>&1 | tail -30

echo "=== C-B14 FINAL VERIFICATION COMPLETE ==="
```

> **Warning-clean is part of done.** `ruff` must report no remaining issues in your changed files. The pytest run must be free of `DeprecationWarning` noise.

> **Any failure in either phase — unit or integration — must be fixed before the batch is declared done.** There is no "pre-existing failure" exception without explicit written confirmation from Tom.

---

## Test Requirements

Per `backend/tests/README-adding-tests.md`:

**Every new test file MUST:**
- Declare `pytestmark` with both domain marker and test type marker:
  - Telnyx/entitlement: `pytestmark = [pytest.mark.domain_subscriptions_usage, pytest.mark.unit]`
  - Stripe: `pytestmark = [pytest.mark.domain_subscriptions_usage, pytest.mark.requires_stripe]`
- Use the `client` fixture (never module-level `TestClient`)
- Use `test_tenant` and `test_user` fixtures (never hardcoded UUIDs)
- Scope assertions by inserted IDs — never `assert len(all_rows) == N`
- Be placed in `backend/tests/domains/subscriptions_usage/`

**Autouse fixture opt-outs:**
- Entitlement scenarios 3, 4, 5: `@pytest.mark.skip_mock_entitlement_allowed` (test real entitlement enforcement)
- Stripe scenarios: no opt-out needed (they test Stripe API, not entitlement)

**Test Resilience Rule:**
- Never UPDATE or DELETE rows you did not INSERT in the current test
- Never assert on total row counts for a table
- Use `second_tenant` for "empty state" tests
- The `db_session` fixture auto-rolls back after each test — use it as the primary cleanup mechanism

**Stripe test-clock specific rules:**
- Each test creates its own test-clocked customer (via `make_clocked_customer` fixture)
- `time.sleep(5)` before advancing test clocks (C-SPIKE-1 Q#4)
- Verify via invoice amount, not meter events (write-only)
- Clean up Stripe test objects after each test (via `stripe_cleanup` fixture)
- Reset `subscription_tier.is_active = true` for Charter if modified (scenarios 10, 11)

---

## Definition of Done

Update `pilot-launch-plan.md` §2.0 row 14s when complete:

- [ ] Pre-modification regression baseline captured (`X passed, Y failed`) using `pytest -m unit`
- [ ] Zero pre-existing unit failures confirmed before starting work
- [ ] All MCP pre-work queries run — subscription_tier, subscription_status, tenant, subscription, stripe_webhook_event_processed, tenant_messaging_registration verified
- [ ] All mandatory source files read before writing any code
- [ ] `requires_stripe` marker added to `pytest.ini`
- [ ] `requires_stripe` added to `implies_integration` set in `conftest.py`
- [ ] Stripe test-clock conftest fixtures created (`stripe_test_key`, `stripe_cleanup`, `make_clocked_customer`, `advance_clock_and_wait`)
- [ ] `test_cb14_telnyx_scenarios.py` — 8 Telnyx mock scenarios pass
- [ ] `test_cb14_entitlement_scenarios.py` — 5 entitlement scenarios pass (scenarios 3-5 with `skip_mock_entitlement_allowed`)
- [ ] `test_cb14_stripe_scenarios.py` — 12 Stripe test-clock scenarios pass (requires `STRIPE_SECRET_KEY=sk_test_...`)
- [ ] §11 "End-to-End Rehearsal" section added to `stripe-ops-runbook.md`
- [ ] All new test files use `pytestmark` with domain marker + correct test type marker
- [ ] No module-level `TestClient` in any test file
- [ ] All new tests use `test_tenant` / `test_user` / `second_tenant` fixtures (no hardcoded UUIDs)
- [ ] Autouse fixture opt-outs applied where needed (`skip_mock_entitlement_allowed` on entitlement scenarios 3-5)
- [ ] `ruff check --fix && ruff format` run on changed files only — zero remaining issues
- [ ] **Phase 1**: All unit tests pass (`pytest -m unit`) — zero failures including any pre-existing
- [ ] **Phase 2**: Full test suite passes (`pytest`) — zero failures including Stripe integration tests, warning-clean
- [ ] Final test count (before → after) documented
- [ ] Completion Summary added to `pilot-launch-plan.md` Appendix B

---

## Completion Summary

After all Definition of Done items are complete:

1. Add a **Completion Summary** subsection to `pilot-launch-plan.md` Appendix B using the format below.

```markdown
### C-B14 (Part A — Python Engineer) — Full Test Suite: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot Python Engineer
**Source design doc**: `batch-c-b14-design.md`
**Baseline**: X passed, Y failed (unit-only)
**Final**: X+N passed, Y failed (+N new tests, full suite)

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
| `tests/domains/subscriptions_usage/test_cb14_telnyx_scenarios.py` | `subscriptions_usage` | 8 | ✅ |
| `tests/domains/subscriptions_usage/test_cb14_entitlement_scenarios.py` | `subscriptions_usage` | 5 | ✅ |
| `tests/domains/subscriptions_usage/test_cb14_stripe_scenarios.py` | `subscriptions_usage` | 12 | ✅ (requires `sk_test_...`) |
```

---

## After This Task — Next Step

This batch is the **launch gate** for the Charter program. After C-B14 Part A (Python Engineer) completes:
1. Tom runs `python scripts/stripe_bootstrap.py --mode live --audit` to verify live-mode Stripe objects
2. Tom follows the E2E rehearsal runbook (§11 of `stripe-ops-runbook.md`)
3. The next batch in the Charter sequence is **C-B15** (Platform Shell + Tenant Impersonation) — design doc to be authored by the Architect
