# Implementation Prompt: C-B10 — Recurring 10DLC Pass-Through Subscription Item + Month-4 Celery Scheduler

**Mode**: Pilot Python Engineer
**Batch**: C-B10
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §2.0 row 14o, §2.1a C-7
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-c-b10-design.md`
**Estimated session**: 2–3 hours
**Platform**: Backend only (`backend/`)
**Frontend companion**: None — backend-only batch (no UI changes; C-B9's `/settings/messaging` page already displays the recurring cost)

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-python-engineer/python-engineer-rules.md`** — full document; the 25 hard rules are non-negotiable STOPs
- **`dev-docs/architecture-design/pilot-python-engineer-methods.md`** — §13 (Alembic), §16 (Standard Task Workflow)
- **`backend/tests/README-adding-tests.md`** — full document; this governs all test file structure, domain markers, and fixture rules

Critical rules for this batch:

- **Rule 1**: Never guess column names, data types, or table names. Use `postgres-local` MCP to verify every name before use. If MCP returns an error → **STOP and ask Tom**.
- **Rule 2**: After any model file change → regenerate `backend/db_models_map.md` via `python generate_db_model_map.py app > db_models_map.md`.
- **Rule 4**: All Alembic migrations must be written as **blank** migrations (never `--autogenerate`).
- **Rule 6**: `db.get()` is permanently banned on tenant-scoped models. Always use tenant-scoped `select()` with an explicit `WHERE tenant_id = :tid` clause.
- **Rule 7**: The `postgres-local` MCP is for **read-only verification only**. Never use it to INSERT, UPDATE, or DELETE data.
- **Rule 11**: If ANY test fails during your work — even one that appears to be a pre-existing failure — **you must fix it before declaring the batch done**.
- **Rule 12 (sync routes)**: This app is **synchronous by design**. Every DB-touching route and `_impl()` is a plain `def`. **Never convert a handler that touches the sync `Session` to `async def`**.
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
-- 1. Verify current tenant_messaging_registration columns (confirm stripe_recurring_item_id + recurring_item_created_at do NOT exist yet)
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'tenant_messaging_registration'
ORDER BY ordinal_position;

-- 2. Verify subscription table has psp_subscription_id + psp_provider + is_active + tenant_id
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'subscription'
  AND column_name IN ('psp_subscription_id', 'psp_provider', 'is_active', 'tenant_id')
ORDER BY ordinal_position;

-- 3. Verify carrier_fee_schedule has recurring fees (campaign_quarterly + phone_number)
SELECT fee_code, entity_type, amount_millicents, effective_to
FROM carrier_fee_schedule
WHERE effective_to IS NULL
  AND (fee_code LIKE '%quarterly%' OR fee_code = 'phone_number')
ORDER BY fee_code, entity_type;

-- 4. Verify current alembic head
SELECT version_num FROM public.alembic_version;

-- 5. Verify tenant_messaging_registration has quoted_monthly_cents column
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'tenant_messaging_registration'
  AND column_name = 'quoted_monthly_cents';
```

---

## Pre-Work: Read These Source Files

Use `read_file` on each of these before writing any code:

```
backend/app/models/sms.py                              ← why: TenantMessagingRegistration model — add 2 new fields
backend/services/messaging_provisioning.py             ← why: C-B9 state machine — understand assign_phone_number() + transition_status() + initiate_provisioning()
backend/services/messaging_checkout.py                 ← why: C-B9 checkout — understand how quoted_monthly_cents is stored
backend/services/telnyx_quoting.py                     ← why: get_carrier_quote() — understand recurring_monthly_millicents computation
backend/services/stripe_subscriptions.py               ← why: _get_stripe_client() + handle_checkout_session_completed() + create_charter_subscription() — understand Stripe patterns
backend/core/stripe_config.py                          ← why: get_stripe_ids() — load prod_passthrough ID
backend/core/celery_app.py                             ← why: beat_schedule dict + task imports list — add new task
backend/tasks/messaging_provisioning.py                ← why: C-B9 two-layer Celery pattern reference
backend/app/models/billing.py                          ← why: Subscription model + CarrierFeeSchedule model
backend/migrations/scripts/seed_platform.py            ← why: carrier_fee_schedule seed block (no changes needed, just reference)
backend/db_models_map.md                               ← why: confirm model names and table mappings
backend/tests/domains/subscriptions_usage/test_cb9_messaging_provisioning.py  ← why: C-B9 test patterns to follow
```

Also run these grep commands to find related files:

```bash
grep -rn "TenantMessagingRegistration" backend/app/models/ --include="*.py" -l
grep -rn "stripe_recurring_item_id\|recurring_item_created_at" backend/ --include="*.py"
```

---

## Background / Context

C-B9 built the one-time 10DLC setup charge (Stripe Checkout, `mode="payment"`, `setup_future_usage="off_session"`). The setup charge covers brand registration, 3 months of campaign fees (prepaid), and the first month of the phone number. After those 3 prepaid months, the tenant must be billed monthly for the recurring carrier costs — campaign fee (monthly) + phone number (monthly) — as a pass-through with zero markup (D25).

C-B10 implements the recurring billing: a service function that creates a Stripe SubscriptionItem on the tenant's existing Charter subscription, and a daily Celery beat task that finds eligible registrations (active + >90 days old + no recurring item yet) and calls the service function.

**Key design decisions (from the design doc §G):**

1. **Stripe Subscription ID location**: The Charter subscription ID is stored on the `subscription` table as `psp_subscription_id` (NOT on `tenant` — the spec's `tenant.stripe_subscription_id` is a simplification). Query `subscription` by `tenant_id` where `is_active = True` and `psp_provider = 'stripe'`.

2. **Amount source**: Use `registration.quoted_monthly_cents` — the amount stored on the registration row at provisioning time by C-B9's `initiate_provisioning()`. This is the amount the tenant was quoted and agreed to pay. If the fee schedule changes later, the recurring item amount does NOT change (locked at quote time).

3. **90-day countdown**: Use `registration.created_at + 90 days`. The registration row is created when `initiate_provisioning()` runs. This is a safe approximation — it may be off by a few days (time between registration creation and checkout completion), but it errs on the side of starting the recurring charge slightly later (no double-charge risk).

4. **Paused subscriptions**: The Celery task still creates the recurring item if the subscription is paused (not canceled). When the tenant resumes, the recurring item will be charged on the next invoice. The task checks `subscription.is_active = True` — a canceled subscription has `is_active = False`.

5. **No new API endpoints**: This is a background-only batch. The recurring item is created by the Celery scheduler, not by a user action.

---

## Task 1 — Alembic Migration: Add 2 Nullable Columns to `tenant_messaging_registration`

Create a blank migration:

```bash
cd <repo>/backend
source .venv/bin/activate
alembic revision -m "c_b10_recurring_item_cols"
```

In the migration file:

```python
def upgrade() -> None:
    op.execute("SET LOCAL session_replication_role = 'replica';")
    op.add_column("tenant_messaging_registration", sa.Column("stripe_recurring_item_id", sa.Text(), nullable=True))
    op.add_column("tenant_messaging_registration", sa.Column("recurring_item_created_at", sa.DateTime(timezone=True), nullable=True))

def downgrade() -> None:
    op.execute("SET LOCAL session_replication_role = 'replica';")
    op.drop_column("tenant_messaging_registration", "recurring_item_created_at")
    op.drop_column("tenant_messaging_registration", "stripe_recurring_item_id")
```

Test the full cycle:

```bash
alembic upgrade head
alembic downgrade -1
alembic upgrade head
alembic current   # must show new head revision
```

**Intermediate unit test run**: `pytest -m unit --tb=short -q | tail -5` — confirm no regressions from the migration.

---

## Task 2 — SQLModel Update: Add 2 New Fields to `TenantMessagingRegistration`

In `backend/app/models/sms.py`, add to the `TenantMessagingRegistration` class:

```python
stripe_recurring_item_id: str | None = Field(default=None, nullable=True)
recurring_item_created_at: datetime | None = Field(default=None, nullable=True)
```

Follow the existing field patterns in the class. Use `str | None` (modern typing, Rule 13).

**Intermediate unit test run**: `pytest -m unit --tb=short -q | tail -5`

---

## Task 3 — Service Function: `services/messaging_recurring.py` (NEW)

Create `backend/services/messaging_recurring.py` with the `create_recurring_carrier_item()` function.

**Full function signature and logic** (from design doc §J.1):

```python
"""
C-B10 — Recurring 10DLC carrier fee pass-through service.

Creates a recurring Stripe SubscriptionItem on the tenant's existing Charter
subscription for monthly carrier fee pass-through (campaign fee + phone number).
Uses inline price_data against prod_passthrough ("Carrier fees (pass-through)").
Amount = registration.quoted_monthly_cents (stored at provisioning time by C-B9).
proration_behavior="none" to avoid prorating the first charge.

Called by the Celery task after the 90-day prepaid window expires.
"""

import logging
import uuid
from datetime import timedelta

from sqlmodel import Session, select

from app.models.billing import Subscription
from app.models.sms import TenantMessagingRegistration
from core.datetime_utils import safe_now_utc

logger = logging.getLogger(__name__)


def create_recurring_carrier_item(
    db: Session,
    registration_id: uuid.UUID,
) -> str:
    """Creates a recurring Stripe SubscriptionItem for 10DLC carrier fees.

    Idempotency: if registration.stripe_recurring_item_id is non-null, skip.
    Returns the Stripe SubscriptionItem ID (si_...).

    Raises:
        ValueError: If registration not found, not in 'active' status,
            quoted_monthly_cents is None/zero, or no active subscription found.
        Exception: On Stripe API error.
    """
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
        raise ValueError(
            f"No active Stripe subscription found for tenant {registration.tenant_id}"
        )

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

**Important**: Verify `safe_now_utc` is the correct import from `core.datetime_utils` — read the file to confirm. If it doesn't exist, use `datetime.now(UTC)` from `datetime` with `from datetime import UTC`.

**Intermediate unit test run**: `pytest -m unit --tb=short -q | tail -5`

---

## Task 4 — Celery Task: `tasks/messaging_recurring.py` (NEW)

Create `backend/tasks/messaging_recurring.py` following the two-layer pattern from C-B9's `tasks/messaging_provisioning.py`.

**Full task logic** (from design doc §J.2):

```python
"""
C-B10 — Recurring carrier fee Celery task.
==========================================

Daily beat task that finds eligible tenant_messaging_registration rows and
creates the recurring Stripe SubscriptionItem for carrier fee pass-through.

Eligibility:
  - status = 'active'
  - created_at + 90 days <= now()  (prepaid window expired)
  - stripe_recurring_item_id IS NULL  (not yet created)

Pattern: Two-layer approach (_impl + @celery_app.task wrapper).
"""

import logging

from sqlmodel import Session, select

from app.models.sms import TenantMessagingRegistration
from core.celery_app import celery_app
from core.db import get_db
from core.datetime_utils import safe_now_utc
from services.messaging_recurring import create_recurring_carrier_item

from datetime import timedelta

logger = logging.getLogger(__name__)


def _create_recurring_carrier_items_impl(db: Session) -> dict[str, int]:
    """Inner implementation — find eligible registrations and create recurring items.

    Returns: {"processed": N, "created": M, "skipped": K, "errors": E}
    """
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
            # Expected skip (already exists, invalid amount, no subscription, etc.)
            logger.info("Skipping registration %s: %s", reg.id, exc)
            skipped += 1
        except Exception as exc:
            logger.error("Failed to create recurring item for registration %s: %s", reg.id, exc)
            errors += 1
            db.rollback()

    return {"processed": processed, "created": created, "skipped": skipped, "errors": errors}


@celery_app.task(name="create_recurring_carrier_items")
def create_recurring_carrier_items() -> dict[str, int]:
    """Daily: create recurring carrier fee subscription items for eligible tenants."""
    db: Session = next(get_db())
    try:
        result = _create_recurring_carrier_items_impl(db)
        logger.info("create_recurring_carrier_items task complete: %s", result)
        return result
    except Exception as exc:
        db.rollback()
        logger.error("create_recurring_carrier_items failed: %s", exc)
        raise
```

**Testing the task**: test `_create_recurring_carrier_items_impl()` directly with the `db_session` fixture — never call `.delay()` or `.apply()` in unit tests.

---

## Task 5 — Register Celery Task in `core/celery_app.py`

In `backend/core/celery_app.py`:

1. **Add to the task imports list** (around line 89, after the C-B9 messaging_provisioning import):

```python
"tasks.messaging_recurring",  # C-B10: Recurring carrier fee pass-through (Beat: daily 09:30 UTC)
```

2. **Add to the beat_schedule dict** (after the `check-otp-timeout` entry):

```python
"create-recurring-carrier-items-daily": {
    "task": "create_recurring_carrier_items",
    "schedule": crontab(hour=9, minute=30),  # 09:30 UTC daily (after free-period-notifications at 09:00)
},
```

**Intermediate unit test run**: `pytest -m unit --tb=short -q | tail -5`

---

## Task 6 — Schema JSON Sync

After the Alembic migration runs and all tests pass, update the master JSON schema file via `schema_manager.py`.

```bash
cd <repo>/backend
source .venv/bin/activate

# 1. Inspect current state first
python schema_manager.py get --path tables.tenant_messaging_registration.columns

# 2. Add stripe_recurring_item_id column
cat << 'EOF' > temp_recurring_item_id.json
{ "type": "text", "nullable": true, "description": "Stripe SubscriptionItem ID for recurring carrier fee pass-through (set by C-B10 Celery task after 90-day prepaid window)" }
EOF
python schema_manager.py set --path tables.tenant_messaging_registration.columns.stripe_recurring_item_id --payload temp_recurring_item_id.json

# 3. Add recurring_item_created_at column
cat << 'EOF' > temp_recurring_created.json
{ "type": "timestamp with time zone", "nullable": true, "description": "When the recurring carrier fee SubscriptionItem was created (C-B10)" }
EOF
python schema_manager.py set --path tables.tenant_messaging_registration.columns.recurring_item_created_at --payload temp_recurring_created.json

# 4. Clean up temp files
rm temp_recurring_item_id.json temp_recurring_created.json
```

**NEVER edit the JSON with `sed`, `awk`, `grep`, or inline Python.** If `schema_manager.py` errors → STOP and ask Tom.

---

## Task 7 — Regenerate DB Model Map

After the `app/models/sms.py` change, regenerate `db_models_map.md`:

```bash
cd <repo>/backend && source .venv/bin/activate
python generate_db_model_map.py app > db_models_map.md
```

After adding the new test file, regenerate `app_model_imports.md`:

```bash
python generate_app_imports.py tests > app_model_imports.md
```

Verify the model appears:

```bash
grep "TenantMessagingRegistration" backend/db_models_map.md
```

---

## Task 8 — Write Tests

Create `backend/tests/domains/subscriptions_usage/test_cb10_recurring_item.py`.

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
- Never assume a table is empty before your test runs.
- The `db_session` fixture is the correct isolation mechanism (transaction rollback).

**Autouse fixtures (run on every test automatically):**
- `mock_cognito_jwks` — patches AWS Cognito JWKS
- `mock_ai_services` — patches all Ollama + Whisper HTTP calls
- `mock_entitlement_allowed` — bypasses all subscription entitlement checks

**Mock pattern for this batch**: Mock `stripe.SubscriptionItem.create` to return a fake object with `.id = "si_test_..."`. Mock `_get_stripe_client()` and `get_stripe_ids()`. Use the `db_session` fixture for direct DB access.

### Required Tests (minimum 9)

| Test | Description |
|---|---|
| `test_create_recurring_item_happy_path` | Registration in `active` status, `quoted_monthly_cents` set, active subscription exists → creates SubscriptionItem, stores ID + timestamp. |
| `test_create_recurring_item_idempotent` | `stripe_recurring_item_id` already set → returns existing ID, no Stripe call. |
| `test_create_recurring_item_wrong_status` | Registration not in `active` status → raises ValueError. |
| `test_create_recurring_item_no_subscription` | No active Stripe subscription for tenant → raises ValueError. |
| `test_create_recurring_item_zero_amount` | `quoted_monthly_cents` is 0 or None → raises ValueError. |
| `test_celery_task_finds_eligible` | Two registrations: one eligible (active, >90d, no item), one not (active, <90d) → only eligible one processed. |
| `test_celery_task_skips_existing` | Registration with `stripe_recurring_item_id` already set → skipped. |
| `test_celery_task_handles_errors` | Stripe API error on one registration → error logged, others still processed. |
| `test_celery_task_no_eligible` | No eligible registrations → returns `{"processed": 0, "created": 0, "skipped": 0, "errors": 0}`. |

**For the Celery task tests**: test `_create_recurring_carrier_items_impl()` directly with the `db_session` fixture — never call `.delay()` or `.apply()`.

**For creating test registrations**: INSERT a `TenantMessagingRegistration` row directly via the `db_session` fixture (not via an API endpoint — this batch has no endpoints). Set `created_at` to a past date for the >90d eligibility test.

**For creating test subscriptions**: INSERT a `Subscription` row directly with `psp_subscription_id="sub_test_..."`, `psp_provider="stripe"`, `is_active=True`, linked to the test tenant.

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

# Lint + format gate (rules §23) — CHANGED FILES ONLY, not the whole codebase
CHANGED_PY=$(git diff --name-only --diff-filter=d HEAD -- '*.py' | sed 's|^backend/||')

if [ -n "$CHANGED_PY" ]; then
    ruff check --fix $CHANGED_PY     # lint + isort (I) + pyupgrade (UP) autofix
    ruff format $CHANGED_PY          # format (line-length 88)
    ruff check $CHANGED_PY           # re-check: any remaining errors need manual fixing
fi

# Full suite including integration tests
python -m pytest --tb=short -q 2>&1 | tail -10

# Batch-specific spot checks
python -m pytest tests/domains/subscriptions_usage/ -v 2>&1 | tail -20

echo "=== C-B10 FINAL VERIFICATION COMPLETE ==="
```

> **Warning-clean is part of done.** `ruff` must report no remaining issues **in your changed files** (no unjustified `# noqa`), and the pytest run must be free of `DeprecationWarning` noise.

> **Any failure in either phase — unit or integration — must be fixed before the batch is declared done.** There is no "pre-existing failure" exception without explicit written confirmation from Tom.

---

## Definition of Done

- [ ] Pre-modification regression baseline captured (`X passed, Y failed`) using `pytest -m unit`
- [ ] Zero pre-existing unit failures confirmed before starting work (or confirmed with Tom)
- [ ] All MCP pre-work queries run — `tenant_messaging_registration` has 18 columns (no `stripe_recurring_item_id` or `recurring_item_created_at` yet); `subscription` has `psp_subscription_id` + `psp_provider` + `is_active`; `carrier_fee_schedule` has recurring fees
- [ ] All mandatory source files read before writing any code
- [ ] Migration created (blank, 2 nullable columns) + triple-verified (upgrade → downgrade → upgrade)
- [ ] `TenantMessagingRegistration` SQLModel updated with `stripe_recurring_item_id` + `recurring_item_created_at`
- [ ] `services/messaging_recurring.py` created with `create_recurring_carrier_item()`
- [ ] `tasks/messaging_recurring.py` created with two-layer Celery task (`_impl` + `@celery_app.task`)
- [ ] `core/celery_app.py` updated with task import + beat schedule entry (daily 09:30 UTC)
- [ ] Schema JSON synced via `schema_manager.py` (2 new columns on `tenant_messaging_registration`)
- [ ] `db_models_map.md` regenerated
- [ ] `app_model_imports.md` regenerated (new test file)
- [ ] All new test files use `pytestmark` with `domain_subscriptions_usage` + `pytest.mark.unit`
- [ ] No module-level `TestClient` in any test file
- [ ] All new tests use `test_tenant` and `test_user` fixtures (no hardcoded UUIDs)
- [ ] `ruff check --fix && ruff format` run **on changed files only** — zero remaining issues
- [ ] **Phase 1**: All unit tests pass (`pytest -m unit`) — zero failures
- [ ] **Phase 2**: Full test suite passes (`pytest`) — zero failures, warning-clean
- [ ] Final test count (before → after) documented
- [ ] Completion Summary added to launch plan Appendix B

---

## Completion Summary

After all Definition of Done items are complete:

1. Add a **Completion Summary** subsection to `dev-docs/analysis/pilot-launch-plan.md` Appendix B using the format below.

```markdown
### C-B10 — Recurring 10DLC Pass-Through Subscription Item: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot Python Engineer
**Source design doc**: `batch-c-b10-design.md`
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
| `tests/domains/subscriptions_usage/test_cb10_recurring_item.py` | `subscriptions_usage` | N | ✅ |
```

---

## After This Task — Next Step

C-B10 is the last batch in the C-B9 → C-B10 10DLC billing chain. After C-B10 closes, the remaining Charter batches are:
- **C-B11** — Operator cohort dashboard (Python + React)
- **C-B12** — Charter → Teams upgrade flow (Python + React)
- **C-B13** — Marketing site rebuild (Marketing React)
- **C-B14** — Full test suite + live-mode rehearsal (Python + React + Tom) — launch gate

Return to Pilot Architect mode for the next batch design.
