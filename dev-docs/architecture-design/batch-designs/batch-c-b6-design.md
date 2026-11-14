# C-B6 — Free-Period Notification Schedule (Celery Beat, T-30/14/7/3/1 + Expiry Day)

**Batch**: C-B6
**Mode**: Pilot Python Engineer
**Prerequisite**: C-B4 ✅ (Stripe subscription lifecycle + `handle_subscription_trial_will_end` stub)
**Source of truth**: `pilot-tech-impl-spec-v1.md` §4.1 (notification schedule), §6.8 (webhook events)
**Status**: Design complete — ready for prompt authoring
**Date**: August 5, 2026

---

## Overview

C-B6 implements the Charter free-period notification schedule: Celery beat jobs that send email + push + in-app banner notifications at T-30, T-14, T-7, T-3, T-1, and on expiry day. This replaces the C-B4 stub in `handle_subscription_trial_will_end()` with a full notification dispatch.

**Backend-only batch** — no DB migration, no frontend. The existing notification pipeline (`NotificationOutbox` → `send_notification` Celery task → `_send_notification_impl`) is reused.

---

## A. Input Read Summary

| Input | Sections read | Key takeaways |
|---|---|---|
| `pilot-tech-impl-spec-v1.md` | §4.1 (free_period_days), §6.8 (webhooks) | "Celery beat job emits at T-30, T-14, T-7, T-3, T-1 and on expiry day. Channels: email + push + in-app banner." Trial tier keeps 7/3/1 (14 days can't support T-30). `customer.subscription.trial_will_end` fires 3 days out (Stripe's own webhook). |
| `trial_management.py` | Full file (90 lines) | Existing `enforce_trial_expirations` task runs hourly; `WARNING_DAYS = [7, 3, 1, 0]`; calls `dispatch_trial_warning()`. C-B6 extends this pattern to Charter free-period using `free_period_ends_at`. |
| `celery_app.py` | Beat schedule (lines 89-238) | `enforce-trial-expirations-hourly` runs at top of every hour. C-B6 adds a new beat entry for free-period notifications. |
| `dunning.py` | Full file (370 lines) | Pattern reference: `_dunning_reminders_impl()` + `dunning_reminders()` wrapper. Two-layer approach (_impl + task). Creates `NotificationEvent` + `NotificationOutbox` rows, enqueues `send_notification.delay()`. |
| `notification_worker.py` | Key functions | `_send_notification_impl()` processes outbox rows → email/push/in_app channels. `poll_pending_notifications` runs every 30s. |
| `stripe_subscriptions.py` | C-B4 `handle_subscription_trial_will_end` | Currently a stub: logs event. C-B6 replaces with full notification dispatch. |
| Live DB — `tenant` | MCP (C-B5 session) | `free_period_ends_at` column exists (C-B2). Indexed: `ix_tenant_free_period_ends_at WHERE free_period_ends_at IS NOT NULL`. |
| Live DB — `notification_template` | MCP (prior sessions) | Platform-level templates (tenant_id IS NULL) for 9 notification types × 3 channels = 27 rows. C-B6 needs new template rows for `free_period_warning` type. |
| Live DB — `notification_type` | Needs MCP verification | Must check if a `free_period_warning` notification type exists. |

---

## B. Migration Plan

**One migration required** — add `free_period_warning` notification type + template rows.

### Pre-migration state (verify via MCP)

```sql
-- Check if free_period_warning notification type exists
SELECT code, name FROM notification_type WHERE code = 'free_period_warning';

-- Check existing notification types
SELECT code, name FROM notification_type ORDER BY code;
```

### Migration: Add `free_period_warning` notification type + templates

```sql
-- Alembic blank migration
def upgrade() -> None:
    op.execute("SET LOCAL session_replication_role = 'replica';")

    # 1. Add notification_type
    op.execute("""
        INSERT INTO notification_type (code, name, is_active, created_at, updated_at)
        VALUES ('free_period_warning', 'Free Period Warning', true, NOW(), NOW())
        ON CONFLICT (code) DO NOTHING;
    """)

    # 2. Add notification_template rows (3 channels: email, push, in_app)
    # Platform-level (tenant_id IS NULL)
    for channel in ['email', 'push', 'in_app']:
        op.execute(f"""
            INSERT INTO notification_template (id, tenant_id, notification_type_code, channel, locale, subject, body, is_active, created_at, updated_at)
            VALUES (gen_random_uuid(), NULL, 'free_period_warning', '{channel}', 'en',
                    'Your free period ends soon',
                    'Your Pilot for Trades free period ends on {expiry_date}. Add a payment method to keep your account running.',
                    true, NOW(), NOW())
            ON CONFLICT DO NOTHING;
        """)

    op.execute("SET LOCAL session_replication_role = 'origin';")

def downgrade() -> None:
    op.execute("SET LOCAL session_replication_role = 'replica';")
    op.execute("DELETE FROM notification_template WHERE notification_type_code = 'free_period_warning' AND tenant_id IS NULL;")
    op.execute("DELETE FROM notification_type WHERE code = 'free_period_warning';")
    op.execute("SET LOCAL session_replication_role = 'origin';")
```

### Seed Data Rollout

- **Layer 1 (core/platform)**: Add `free_period_warning` to `seed_platform.py` notification_type + notification_template blocks. Idempotent (`ON CONFLICT DO NOTHING`).
- **Layer 2 (scenario)**: No scenario seed change — notifications are runtime events, not display data.

---

## C. Execution Order

| # | Task | File(s) |
|---|---|---|
| 1 | Alembic migration: add `free_period_warning` notification type + 3 template rows | `backend/migrations/versions/` |
| 2 | Update `seed_platform.py`: add `free_period_warning` type + templates | `backend/migrations/scripts/seed_platform.py` |
| 3 | Create `tasks/free_period_notifications.py` — Celery beat task with `_impl` + wrapper | `backend/tasks/free_period_notifications.py` |
| 4 | Register task in `celery_app.py` imports + beat_schedule | `backend/core/celery_app.py` |
| 5 | Update `handle_subscription_trial_will_end()` in `stripe_subscriptions.py` — replace stub with notification dispatch | `backend/services/stripe_subscriptions.py` |
| 6 | Write unit tests for the notification task | `backend/tests/domains/notifications_comms/` |
| 7 | Write unit tests for the webhook handler update | `backend/tests/domains/subscriptions_usage/` |
| 8 | Run `python export_openapi_json.py` (no endpoint changes, but verify) | `backend/openapi.json` |
| 9 | Run ruff + full test suite (Phase 2) | — |

---

## D. New API Endpoints

**No new endpoints.** C-B6 is purely backend: a Celery beat task + webhook handler update.

---

## E. Pattern Reuse Decisions

| Pattern | How it applies |
|---|---|
| **§17.1 Periodic Poll Task** | The free-period notification task follows the existing pattern: no `bind=True`, no retry, log errors and move on. Same as `enforce_trial_expirations`, `dunning_reminders`, `notify_mfa_grace_period_reminders`. |
| **Two-layer _impl + task** | `_free_period_notifications_impl(db)` contains business logic (testable without Celery). `free_period_notifications()` wrapper opens a session, calls _impl, handles exceptions. Same as `dunning_reminders()`. |
| **Notification pipeline** | Creates `NotificationEvent` + `NotificationOutbox` rows, enqueues `send_notification.delay()`. The existing `notification_worker.py` handles delivery (email/push/in_app). No new delivery code. |
| **Idempotency** | Each notification is dispatched once per threshold. The task checks if a notification was already sent for this tenant + threshold (via `NotificationEvent` lookup) before creating a new one. Prevents duplicate notifications on re-runs. |
| **Sync routes** (Rule §21) | All new code is in `def` functions — no `async def`. |

---

## F. Shared Module Interfaces

### tasks/free_period_notifications.py

```python
"""
C-B6 — Free-period notification schedule.
Celery Beat task: daily at 09:00 UTC.
Sends email + push + in-app banner at T-30, T-14, T-7, T-3, T-1, and on expiry day.
"""

import logging
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlmodel import Session, select

from core.celery_app import celery_app
from core.db import get_db

logger = logging.getLogger(__name__)

# Charter free-period notification thresholds (days before expiry)
FREE_PERIOD_WARNING_DAYS = [30, 14, 7, 3, 1, 0]  # 0 = expiry day


@celery_app.task(name="free_period_notifications")
def free_period_notifications() -> dict[str, int]:
    """Celery Beat task (daily 09:00 UTC)."""
    db: Session = next(get_db())
    try:
        return _free_period_notifications_impl(db)
    except Exception as e:
        db.rollback()
        logger.error(f"Error in free_period_notifications: {e}")
        raise
    finally:
        db.close()


def _free_period_notifications_impl(db: Session) -> dict[str, int]:
    """
    Inner implementation — separated for testability.

    Queries tenants with free_period_ends_at set, computes days remaining,
    dispatches notifications at T-30/14/7/3/1/0 thresholds.

    Idempotent: checks NotificationEvent for existing dispatch at same threshold.
    """
    from app.models.core import Tenant
    from app.models.system import NotificationEvent, NotificationOutbox

    now = datetime.now(UTC)
    notifications_sent = 0

    # Find all tenants with a free period end date
    tenants = db.exec(
        select(Tenant)
        .where(Tenant.free_period_ends_at != None)
        .where(Tenant.is_active == True)
    ).all()

    for tenant in tenants:
        days_remaining = (tenant.free_period_ends_at - now).days

        if days_remaining not in FREE_PERIOD_WARNING_DAYS:
            continue

        # Idempotency: check if already notified for this threshold
        existing = db.exec(
            select(NotificationEvent)
            .where(NotificationEvent.tenant_id == tenant.id)
            .where(NotificationEvent.notification_type_code == "free_period_warning")
            .where(NotificationEvent.metadata.op("->>")("days_remaining") == str(days_remaining))
        ).first()

        if existing:
            continue  # Already sent for this threshold

        # Create notification event + outbox entries (3 channels)
        # ... (follow dunning.py pattern: create NotificationEvent, then
        #      NotificationOutbox rows for email/push/in_app, then
        #      send_notification.delay() for each)

        notifications_sent += 1

    logger.info(f"Free-period notifications: {notifications_sent} sent")
    return {"notifications_sent": notifications_sent}
```

### services/stripe_subscriptions.py — Updated `handle_subscription_trial_will_end()`

```python
def handle_subscription_trial_will_end(db: Session, stripe_event: dict) -> None:
    """customer.subscription.trial_will_end — fires 3 days before trial ends.
    Dispatches T-3 notification via the free-period notification pipeline."""
    sub = stripe_event.get("data", {}).get("object", {})
    stripe_customer_id = sub.get("customer")

    if not stripe_customer_id:
        return

    # Find tenant by stripe_customer_id
    from app.models.core import Tenant
    tenant = db.exec(
        select(Tenant).where(Tenant.stripe_customer_id == stripe_customer_id)
    ).first()

    if not tenant or not tenant.free_period_ends_at:
        return

    # The Stripe webhook fires 3 days out — this is our T-3 notification
    # Dispatch via the same notification pipeline as the Celery beat task
    from tasks.free_period_notifications import _dispatch_free_period_notification
    _dispatch_free_period_notification(db, tenant, days_remaining=3)
```

### core/celery_app.py — New Beat Entry

```python
# C-B6: Free-period notification schedule (daily at 09:00 UTC)
"free-period-notifications-daily": {
    "task": "free_period_notifications",
    "schedule": crontab(hour=9, minute=0),  # 09:00 UTC daily
},
```

And add to imports:
```python
"tasks.free_period_notifications",  # C-B6: Free-period notification schedule
```

---

## G. Open Questions Resolved

| Question | Resolution | Source |
|---|---|---|
| **Relationship to existing trial warnings** | The existing `enforce_trial_expirations` task handles the Trial tier (14-day, T-7/3/1). C-B6 handles the Charter free period (90-day, T-30/14/7/3/1). They are separate tasks with separate thresholds. The trial task uses `trial_ends_at`; the free-period task uses `free_period_ends_at`. | Spec §4.1: "The PRD's existing 7/3/1 trial schedule is extended, not replaced" |
| **Stripe `trial_will_end` webhook vs Celery beat** | Both fire at T-3. The Stripe webhook is the authoritative trigger (it fires from Stripe's side). The Celery beat task is the primary scheduler for all other thresholds (T-30/14/7/1/0). The webhook handler calls the same `_dispatch_free_period_notification()` function — idempotency prevents duplicates. | Spec §6.8 + design decision |
| **Notification type code** | `free_period_warning` — new notification type. 3 template rows (email/push/in_app), platform-level (tenant_id IS NULL). | Design decision |
| **Expiry day (T-0) notification** | On expiry day, the notification says "Your free period ends today. Add a payment method now to avoid interruption." The Stripe webhook `customer.subscription.paused` fires when the subscription actually pauses — that's a separate event handled by C-B4's `handle_subscription_paused()`. | Spec §4.1 + §6.8 |
| **Silent extension interaction** | If the operator extends `free_period_ends_at` (§4.4), the T-0 notification for the old date was already sent. The new date triggers new notifications at the new thresholds. The idempotency check uses `days_remaining` as the key — a new `days_remaining` value (from the new end date) is a new notification, not a duplicate. | Spec §4.4 |
