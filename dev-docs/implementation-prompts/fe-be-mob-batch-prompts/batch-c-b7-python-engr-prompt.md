# Implementation Prompt: C-B7 — Paused-State Service Block (All Services Including SMS)

**Mode**: Pilot Python Engineer  
**Batch**: C-B7  
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §2.0 row 14l  
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-c-b7-design.md`  
**Estimated session**: 1–2 hours  
**Platform**: Backend only (`backend/`)  
**Frontend companion**: None

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-python-engineer/python-engineer-rules.md`** — full document
- **`dev-docs/architecture-design/pilot-python-engineer-methods.md`** — §16 (Standard Task Workflow)
- **`backend/tests/README-adding-tests.md`** — full document

Critical rules for this batch:

- **Rule 1**: Never guess column names. Use `postgres-local` MCP to verify.
- **Rule 11**: If ANY test fails — fix it before declaring done.
- **Rule 12 (sync)**: All DB-touching code is `def` — never `async def`.
- **Rule 16 (verify)**: Query `information_schema.columns` for every table you touch.

---

## ⚠️ Key Design Decision (Tom, 2026-08-05)

**Spec §9.3 SMS exception is OVERRIDDEN.** The spec originally proposed allowing SMS when `tenant_messaging_registration.status = 'active'` even when the subscription is paused. **Tom overrode this**: when a subscription is paused, the tenant is not paying, and ALL services including SMS must be blocked. Allowing SMS creates costs Pilot is liable for, and once the tenant exceeds plan overage, they're charged in addition to the monthly fee. The Telnyx brand/campaign being theirs does not override this — they can resume the subscription to re-enable SMS.

**When paused → everything blocked, including SMS. No exceptions.**

---

## Pre-Work: Establish Regression Baseline

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=no -q 2>&1 | tail -5
```

---

## Pre-Work: Run MCP Verification Queries

```sql
-- 1. Verify subscription table columns (status_id FK)
SELECT column_name, data_type, is_nullable FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'subscription'
ORDER BY ordinal_position;

-- 2. Verify subscription_status codes + is_billing_active
SELECT code, name, is_billing_active FROM subscription_status ORDER BY code;

-- 3. Verify tenant_messaging_registration columns (for reference — NOT used for exception)
SELECT column_name, data_type FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'tenant_messaging_registration'
ORDER BY ordinal_position;
```

---

## Pre-Work: Read These Source Files

```
backend/services/entitlement_service.py     ← why: add is_subscription_billing_active() here
backend/services/sms_quota.py               ← why: check_quota() — where to add billing-active block
backend/services/customer_comms_service.py   ← why: SMS send path — find where to integrate the check
backend/services/trial_management.py         ← why: enforce_paywall() — only checks trial, not subscription
backend/services/stripe_subscriptions.py    ← why: handle_subscription_paused() — sets status to paused
backend/app/models/billing.py               ← why: Subscription, SubscriptionStatus models
backend/tests/conftest.py                    ← why: available fixtures
```

Also run:
```bash
grep -rn "check_quota\|send_sms\|customer_communication" backend/api/routes/ --include="*.py" -l
grep -rn "check_quota\|send_sms" backend/services/ --include="*.py" -l
```

---

## Background / Context

C-B7 is a small batch. Two of the three scope items are already done:

1. **D11 (data export to all plans)**: Already done — `data_exports` product_feature deleted in SD-07/MKT-B11. No code change.
2. **Q#6 (data retention)**: Resolved as "Standard for now" — no code change.
3. **Paused-state service block**: The only real work. When a subscription is `paused` (or `unpaid`/`canceled`), ALL services including SMS must be blocked. The existing `enforce_paywall()` only checks trial expiration — there is no billing-active check for non-trial tenants. C-B7 adds this check to the SMS send path.

**Key finding**: `sms_quota.check_quota()` checks customer opt-out + quota limits but does NOT check subscription billing status. SMS sends are not currently blocked when a subscription is paused. C-B7 adds the billing-active check to block them.

---

## Task 1 — Create `is_subscription_billing_active()` in `entitlement_service.py`

Add this function to `backend/services/entitlement_service.py`:

```python
def is_subscription_billing_active(db: Session, tenant_id: uuid.UUID) -> bool:
    """
    Check whether the tenant's subscription is billing-active.

    Returns False when the subscription status is 'paused', 'unpaid', or 'canceled'
    (is_billing_active=false). Returns True for 'active', 'trialing', 'past_due'.

    When False, ALL services are blocked — including SMS. The tenant is not paying
    for their subscription, and allowing SMS creates costs Pilot is liable for.

    Returns:
        True if subscription is billing-active, False otherwise.
    """
    from app.models.billing import Subscription, SubscriptionStatus

    sub = db.exec(
        select(Subscription)
        .where(Subscription.tenant_id == tenant_id)
        .where(Subscription.is_active == True)
    ).first()

    if not sub:
        return False

    status = db.exec(
        select(SubscriptionStatus).where(SubscriptionStatus.id == sub.status_id)
    ).first()

    if not status:
        return False

    return status.is_billing_active
```

**Intermediate test run:** `pytest -m unit --tb=short -q | tail -5`

---

## Task 2 — Integrate Billing-Active Check into SMS Send Path

**Read** `backend/services/customer_comms_service.py` and the SMS send route to find where SMS sends are gated.

**Add the billing-active check** early in the SMS send path — before or alongside `check_quota()`. When `is_subscription_billing_active()` returns False, block the SMS send with reason `"subscription_paused"`.

The exact integration depends on the code structure. Possible approaches:
- Add the check in `check_quota()` itself (return `blocked_reason="subscription_paused"`)
- Add the check in the SMS send route/service before calling `check_quota()`
- Add the check in `customer_comms_service.py` send function

**The engineer must** `read_file` on the relevant files to determine the best integration point. The check must happen BEFORE any SMS is sent — it's a gate, not a post-send check.

**Intermediate test run:** `pytest -m unit --tb=short -q | tail -5`

---

## Task 3 — Write Tests

**Domain folder**: `backend/tests/domains/notifications_comms/`

**Test file**: `test_cb7_billing_active_check.py`

| Test | Description |
|---|---|
| 1 | `is_subscription_billing_active()` returns True when status is `active` (is_billing_active=true) |
| 2 | `is_subscription_billing_active()` returns False when status is `paused` (is_billing_active=false) |
| 3 | `is_subscription_billing_active()` returns False when no active subscription exists |
| 4 | SMS send is blocked when subscription is paused (integration test — mock the send path) |
| 5 | SMS send is allowed when subscription is active (integration test) |

**Mocking**: Use `db_session` fixture with direct inserts. Mock the SMS carrier for integration tests.

**Intermediate test run:** `pytest -m unit --tb=short -q | tail -5`

---

## Final Verification Gate

### Phase 1 — Unit Tests
```bash
python -m pytest -m unit --tb=short -q 2>&1 | tail -10
```

### Phase 2 — Ruff + Full Suite
```bash
CHANGED_PY=$(git diff --name-only --diff-filter=d HEAD -- '*.py' | sed 's|^backend/||')
if [ -n "$CHANGED_PY" ]; then
    ruff check --fix $CHANGED_PY
    ruff format $CHANGED_PY
    ruff check $CHANGED_PY
fi
python -m pytest --tb=short -q 2>&1 | tail -10
```

---

## Definition of Done

- [ ] `is_subscription_billing_active()` created in `entitlement_service.py`
- [ ] Billing-active check integrated into SMS send path — blocks SMS when paused
- [ ] 5 unit tests pass
- [ ] Ruff clean on all changed files
- [ ] Full test suite passes

---

## Completion Summary

When done, append a completion summary to `dev-docs/analysis/pilot-launch-plan.md` Appendix B. Also add a one-row entry to Appendix A and mark C-B7 as ✅ in §2.0.

**Important**: Note in the completion summary that spec §9.3 SMS exception was overridden by Tom (2026-08-05) — when paused, ALL services including SMS are blocked with no exceptions.
