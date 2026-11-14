# Implementation Prompt: C-B6 — Free-Period Notification Schedule

**Mode**: Pilot Python Engineer  
**Batch**: C-B6  
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §2.0 row 14k  
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-c-b6-design.md`  
**Estimated session**: 2–3 hours  
**Platform**: Backend only (`backend/`)  
**Frontend companion**: None (notifications are delivered via existing email/push/in-app pipeline)

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-python-engineer/python-engineer-rules.md`** — full document; the 25 hard rules are non-negotiable STOPs
- **`dev-docs/architecture-design/pilot-python-engineer-methods.md`** — §13 (Alembic), §16 (Standard Task Workflow), §17.1 (Periodic Poll Task pattern)
- **`backend/tests/README-adding-tests.md`** — full document

Critical rules for this batch:

- **Rule 1**: Never guess column names. Use `postgres-local` MCP to verify before use.
- **Rule 4**: All Alembic migrations must be **blank** migrations. Data changes use raw `op.execute()` with `SET LOCAL session_replication_role = 'replica';`.
- **Rule 11**: If ANY test fails — fix it before declaring done.
- **Rule 12 (sync)**: All DB-touching code is `def` — never `async def`.
- **Rule 16 (verify)**: Query `information_schema.columns` for every table you touch.

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
-- 1. Verify notification_type columns
SELECT column_name, data_type, is_nullable FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'notification_type' ORDER BY ordinal_position;

-- 2. Check if free_period_warning notification type already exists
SELECT code, name FROM notification_type WHERE code = 'free_period_warning';

-- 3. Verify notification_template columns
SELECT column_name, data_type, is_nullable FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'notification_template' ORDER BY ordinal_position;

-- 4. Verify notification_event columns (for idempotency check)
SELECT column_name, data_type, is_nullable FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'notification_event' ORDER BY ordinal_position;

-- 5. Verify notification_outbox columns
SELECT column_name, data_type, is_nullable FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'notification_outbox' ORDER BY ordinal_position;

-- 6. Verify tenant.free_period_ends_at column + index
SELECT column_name, data_type FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'tenant' AND column_name = 'free_period_ends_at';

-- 7. Verify current alembic head
SELECT version_num FROM public.alembic_version;
```

---

## Pre-Work: Read These Source Files

```
backend/tasks/trial_management.py          ← why: existing trial warning pattern (WARNING_DAYS, dispatch_trial_warning)
backend/tasks/dunning.py                    ← why: two-layer _impl + task pattern; NotificationEvent + NotificationOutbox creation
backend/tasks/notification_worker.py        ← why: _send_notification_impl + send_notification.delay() pipeline
backend/core/celery_app.py                  ← why: beat_schedule + imports registration
backend/services/stripe_subscriptions.py   ← why: handle_subscription_trial_will_end stub to replace
backend/services/trial_management.py       ← why: dispatch_trial_warning() service function pattern
backend/app/models/system.py                ← why: NotificationEvent, NotificationOutbox, NotificationTemplate models
backend/migrations/scripts/seed_platform.py ← why: notification_type + notification_template seed blocks
backend/tests/conftest.py                   ← why: available fixtures
```

---

## Background / Context

C-B6 implements the Charter free-period notification schedule. The existing trial system sends warnings at T-7/3/1 (14-day trial). The Charter program has a 90-day free period, so the schedule extends to T-30/14/7/3/1 + expiry day.

**Key architectural decisions:**
1. **Separate task from `enforce_trial_expirations`** — the trial task uses `trial_ends_at`; the free-period task uses `free_period_ends_at`. Different thresholds, different tenant sets.
2. **Daily beat at 09:00 UTC** — same time as dunning reminders. The Stripe `trial_will_end` webhook (fires at T-3) calls the same dispatch function — idempotency prevents duplicates.
3. **Idempotency via `NotificationEvent` metadata** — each notification records `days_remaining` in the event metadata. Before dispatching, check if a notification was already sent for this tenant + threshold.
4. **Reuses existing notification pipeline** — creates `NotificationEvent` + `NotificationOutbox` rows, enqueues `send_notification.delay()`. No new delivery code.

---

## Task 1 — Alembic Migration: Add `free_period_warning` Notification Type + Templates

Create a blank migration:

```bash
cd <repo>/backend
source .venv/bin/activate
alembic revision -m "c_b6_add_free_period_warning_notification_type"
```

**Migration content** — add `free_period_warning` notification_type + 3 platform-level notification_template rows (email/push/in_app). Follow the pattern from the design doc §B. Use `ON CONFLICT DO NOTHING` for idempotency. Include `SET LOCAL session_replication_role = 'replica'`.

**Template body content** (adjust per channel):
- **Email subject**: "Your Pilot free period ends soon"
- **Email body**: "Your Pilot for Trades free period ends on {expiry_date}. Add a payment method in Settings → Subscription & Billing to keep your account running past that date."
- **Push body**: "Free period ends {expiry_date}. Add a payment method to avoid interruption."
- **In-app body**: "Your free period ends on {expiry_date}. Add a payment method to keep your account running."

**Test the full cycle:**
```bash
alembic upgrade head
alembic downgrade -1
alembic upgrade head
alembic current
```

**Intermediate test run:** `pytest -m unit --tb=short -q | tail -5`

---

## Task 2 — Update `seed_platform.py`

Add `free_period_warning` to the notification_type seed block and the notification_template seed block in `backend/migrations/scripts/seed_platform.py`. Follow the existing pattern (idempotent `INSERT ... ON CONFLICT DO NOTHING`).

**Intermediate test run:** `pytest -m unit --tb=short -q | tail -5`

---

## Task 3 — Create `tasks/free_period_notifications.py`

Create `backend/tasks/free_period_notifications.py` following the two-layer pattern (`_impl` + task wrapper).

**Key implementation details:**

1. **`FREE_PERIOD_WARNING_DAYS = [30, 14, 7, 3, 1, 0]`** — 0 = expiry day
2. **Query**: `SELECT Tenant WHERE free_period_ends_at IS NOT NULL AND is_active = true`
3. **For each tenant**: compute `days_remaining = (free_period_ends_at - now).days`
4. **Idempotency check**: query `NotificationEvent` where `tenant_id = tenant.id` AND `notification_type_code = 'free_period_warning'` AND `metadata->>'days_remaining' = str(days_remaining)`. Skip if exists.
5. **Dispatch**: create `NotificationEvent` (with metadata `{"days_remaining": N}`) + `NotificationOutbox` rows for 3 channels (email/push/in_app), then `send_notification.delay()` for each.
6. **`_dispatch_free_period_notification(db, tenant, days_remaining)`** — extracted helper, called by both the Celery task and the Stripe webhook handler.

Follow the `dunning.py` pattern for `NotificationEvent` + `NotificationOutbox` creation. Look up the owner user via `TenantUser` (same as dunning does).

**Expiry day (T-0) copy**: "Your free period ends today. Add a payment method now to avoid interruption."

**Intermediate test run:** `pytest -m unit --tb=short -q | tail -5`

---

## Task 4 — Register in `celery_app.py`

In `backend/core/celery_app.py`:

1. Add `"tasks.free_period_notifications"` to the `imports` list
2. Add beat schedule entry:
```python
# C-B6: Free-period notification schedule (daily at 09:00 UTC)
"free-period-notifications-daily": {
    "task": "free_period_notifications",
    "schedule": crontab(hour=9, minute=0),  # 09:00 UTC daily
},
```

**Intermediate test run:** `pytest -m unit --tb=short -q | tail -5`

---

## Task 5 — Update `handle_subscription_trial_will_end()` in `stripe_subscriptions.py`

Replace the C-B4 stub in `backend/services/stripe_subscriptions.py`:

```python
def handle_subscription_trial_will_end(db: Session, stripe_event: dict) -> None:
    """customer.subscription.trial_will_end — fires 3 days before trial ends.
    Dispatches T-3 notification via the free-period notification pipeline."""
    sub = stripe_event.get("data", {}).get("object", {})
    stripe_customer_id = sub.get("customer")
    if not stripe_customer_id:
        return

    from app.models.core import Tenant
    tenant = db.exec(
        select(Tenant).where(Tenant.stripe_customer_id == stripe_customer_id)
    ).first()

    if not tenant or not tenant.free_period_ends_at:
        return

    from tasks.free_period_notifications import _dispatch_free_period_notification
    _dispatch_free_period_notification(db, tenant, days_remaining=3)
```

**Key**: The Stripe webhook fires at T-3. The Celery beat task also fires at T-3 (daily check). The idempotency check in `_dispatch_free_period_notification` prevents duplicate notifications.

**Intermediate test run:** `pytest -m unit --tb=short -q | tail -5`

---

## Task 6 — Write Tests

**Domain folder**: `backend/tests/domains/notifications_comms/` (notification task) + `backend/tests/domains/subscriptions_usage/` (webhook handler)

**Test files:**

| Test File | Domain | Tests | Description |
|---|---|---|---|
| `test_cb6_free_period_notifications.py` | `notifications_comms` | 5 | Task registered in celery imports + beat_schedule; _impl sends at T-30; _impl sends at T-0 (expiry day); idempotent (skip if already sent); skips tenants without free_period_ends_at |
| `test_cb6_trial_will_end_webhook.py` | `subscriptions_usage` | 2 | Webhook handler dispatches T-3 notification; idempotent with Celery beat (no duplicate) |

**Mocking**: Mock `send_notification.delay()` to avoid actual Celery dispatch. Use `db_session` fixture for direct _impl testing.

**Intermediate test run:** `pytest -m unit --tb=short -q | tail -5`

---

## Task 7 — Regenerate + Verify

```bash
cd <repo>/backend
source .venv/bin/activate
python export_openapi_json.py  # No endpoint changes, but verify no breakage
```

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

- [ ] Alembic migration created + tested (upgrade/downgrade/upgrade cycle)
- [ ] `seed_platform.py` updated with `free_period_warning` type + templates
- [ ] `tasks/free_period_notifications.py` created — two-layer _impl + task
- [ ] `celery_app.py` updated — imports + beat_schedule entry
- [ ] `handle_subscription_trial_will_end()` updated — replaces stub with dispatch
- [ ] All unit tests pass
- [ ] Ruff clean on all changed files
- [ ] Full test suite passes

---

## Completion Summary

When done, append a completion summary to `dev-docs/analysis/pilot-launch-plan.md` Appendix B. Also add a one-row entry to Appendix A and mark C-B6 as ✅ in §2.0.
