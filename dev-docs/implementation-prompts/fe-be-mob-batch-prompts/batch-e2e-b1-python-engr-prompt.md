# Implementation Prompt: E2E-B1 — E2E Gap Closure (W-05, W-07, W-11, W-14, W-16)

**Mode**: Pilot Python Engineer  
**Batch**: E2E-B1  
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §Phase 1 — E2E Test Harness  
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-e2e-b1-design.md`  
**Estimated session**: 2–3 hours  
**Platform**: Backend only (`backend/`)  
**Frontend companion**: None  

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`dev-docs/architecture-design/pilot-python-engineer-methods.md`** — §16 (Standard Task Workflow), §8 (Router Design), §13 (Alembic — not needed here, but review for context)
- **`backend/tests/README-adding-tests.md`** — full document; this governs all test file structure, domain markers, and fixture rules

**Critical rules for this batch:**

- **Rule 1**: Never guess column names, data types, or table names. Use `postgres-local` MCP to verify every name before use. If MCP returns an error → **STOP and ask Tom**.
- **Rule 5**: Never use module-level `TestClient` in any test file. Always use the `client` fixture or `e2e_client` fixture from conftest files.
- **Rule 7**: The `postgres-local` MCP is for **read-only verification only**. Never use it to INSERT, UPDATE, or DELETE data.
- **Rule 11**: If ANY test fails during your work — even one that appears pre-existing — **you must fix it before declaring the batch done**.
- **E2E-specific**: E2E tests use `pytest.mark.e2e` (not `pytest.mark.unit`). They are session-scoped, do NOT rollback between tests, and use the `pilot_e2e_db` database (port 5433). Tests must use unique IDs and assert on those IDs — never on total counts.
- **No migrations**: This batch makes zero DB schema changes. No `alembic revision` commands needed.
- **No new endpoints**: This batch consumes only existing API endpoints. Do not add any new routes.

---

## Pre-Work: Establish Regression Baseline

Before touching any file, capture the current **unit-only** test baseline:

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=no -q 2>&1 | tail -5
```

Record the exact count: **`X passed, Y failed`**.

Also capture the existing E2E count (they should all pass from SD-10):
```bash
python -m pytest tests/e2e/ --e2e --tb=no -q 2>&1 | tail -5
```

> **If any tests are already failing before you start**: Confirm with Tom that this is a known, accepted failure before proceeding. Do NOT start implementation while tests are in an unexplained failed state.

---

## Pre-Work: Run MCP Verification Queries

Run **all** of these via `postgres-local` MCP before writing any code. If any query returns unexpected results → **STOP and ask Tom**.

> **MCP Usage Rule**: The `postgres-local` MCP is for **read-only verification only**. Use it to confirm table names, column types, and existing data. Never use it to INSERT, UPDATE, or DELETE.

```sql
-- 1. Verify current alembic head
SELECT version_num FROM public.alembic_version;

-- 2. Confirm all target tables exist
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public' AND table_name IN (
  'nec_calculation_log','mobile_sync_session','mobile_sync_event',
  'user_mfa_method','auth_mfa_otp','notification_event',
  'notification_outbox','notification_delivery_attempt','in_app_notification'
)
ORDER BY table_name;

-- 3. Verify nec_calculation_log columns (used by W-07 test)
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'nec_calculation_log'
ORDER BY ordinal_position;

-- 4. Verify user_mfa_method PK column name (critical — PK is mfa_method_id not id)
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'user_mfa_method'
ORDER BY ordinal_position;

-- 5. Verify notification_outbox status values in live data
SELECT DISTINCT status FROM notification_outbox LIMIT 20;

-- 6. Verify mobile_sync_session columns
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'mobile_sync_session'
ORDER BY ordinal_position;
```

---

## Pre-Work: Read These Source Files

Use `read_file` on each of these before writing any code:

```
backend/tests/e2e/conftest_e2e.py                 ← E2E fixture definitions (e2e_client, e2e_engine, e2e_mock_*)
backend/tests/e2e/cp1_auth_tenant/test_auth_rbac.py  ← E2E test pattern to follow exactly
backend/tests/e2e/cp5_dunning_cycle/test_dunning.py  ← Pattern for calling _impl() functions directly
backend/api/routes/nec.py                          ← NEC endpoint signatures + _nec_calculate_impl
backend/services/nec_service.py                    ← Valid calc_type values + input shapes
backend/api/routes/webhooks_stripe.py              ← Check if /test endpoint exists for Stripe webhooks
backend/tasks/notification_worker.py               ← Find the _process_notification_impl function
backend/migrations/scripts/seed_scenario_reporting.py  ← Seed script pattern (seed/mode_reset/mode_inspect)
backend/migrations/scripts/seed_e2e_db.py          ← How E2E DB seeds are called
backend/migrations/scripts/reset_dev_db.py         ← How dev seeds are registered
```

---

## Background / Context

The E2E test harness (SD-10, completed 2026-07-07) established CP-1 through CP-5 covering 5 of 16 defined workflows. The `scenario-coverage-catalog.md` §6.3 identified 5 P0/P1 gaps:

| Workflow | Gap | Priority |
|---|---|---|
| **W-05**: Invoice/Stripe payment | No Tier 1 test. Stripe `sk_test_` key is now in `.env.e2e`. | **P0** |
| **W-14**: MFA enrollment (full) | CP-1 covers login only. MFA row creation not tested. | **P0** |
| **W-16**: Notification delivery | CP-5 dunning fires a notification but delivery pipeline not asserted. | P1 |
| **W-07**: NEC calculation | No seed, no test. `/calculate/test` endpoint exists. | P1 |
| **W-11**: Mobile sync lifecycle | No seed, no test. Tables exist. | P1 |

This batch closes all 5 gaps. No migrations, no new endpoints — pure test + seed engineering.

**Pass gate**: `pytest tests/e2e/ --e2e --tb=short -q` shows 0 failures across CP-1 through CP-9.

---

## Task 1 — Seed Script: `seed_scenario_nec.py` (W-07)

**File to create**: `backend/migrations/scripts/seed_scenario_nec.py`

Create a seed scenario script that inserts synthetic `nec_calculation_log` rows for the test tenant. Follow the established pattern from `seed_scenario_reporting.py`.

**What to seed**:
- 2 `nec_calculation_log` rows for the test tenant (use `tenant_id=uuid.UUID("00000000-0000-0000-0000-000000000001")` — verify this is the correct test tenant UUID by checking `seed_core.py`)
- Use `user_id=uuid.UUID("00000000-0000-0000-0000-000000000002")` (dev@pilot.local owner)
- Row 1: `calc_type="box_fill"`, `is_offline_calc=False`, `inputs_json={"box_type": "square_4inch", "conductors": [{"size": "12", "type": "thhn", "count": 4}]}`, `result_json={"volume_required_in3": 18.0, "volume_available_in3": 21.0, "passed": True}`
- Row 2: `calc_type="box_fill"`, `is_offline_calc=True`, `client_capture_at=<3 days ago>`, `inputs_json={"box_type": "square_4inch", "conductors": [{"size": "14", "type": "thhn", "count": 6}]}`, `result_json={"volume_required_in3": 21.0, "volume_available_in3": 21.0, "passed": True}`
- `nec_guide_version="2023"` on both rows

> **Before using any column names above**: run MCP query #3 to confirm they match the live DB. If a column name differs from what's above, use the MCP-returned name.

**Required functions** (per seed_scenario_reporting.py pattern):
```python
def seed(db_url: str | None = None) -> None: ...
def mode_reset(db_url: str | None = None) -> None: ...
def mode_inspect(db_url: str | None = None) -> None: ...

if __name__ == "__main__":
    seed()
```

After creating:
- Register in `backend/migrations/scripts/reset_dev_db.py` as scenario `"nec"` (follow the existing pattern for scenario registration)
- Do NOT add to `seed_e2e_db.py` yet — that happens in Task 2

---

## Task 2 — Seed Script: `seed_scenario_mobile_sync.py` (W-11)

**File to create**: `backend/migrations/scripts/seed_scenario_mobile_sync.py`

Create a seed scenario script that inserts synthetic `mobile_sync_session` + `mobile_sync_event` rows.

**What to seed**:
- 1 `mobile_sync_session` row: `triggered_by="background"`, `outcome="success"`, `items_attempted=3`, `items_committed=3`, `items_deferred=0`, `items_failed=0`, `started_at=<2 hours ago>`, `completed_at=<1 hour ago 59 minutes ago>`. Use `device_id=uuid.UUID("00000000-0000-0000-0001-000000000001")` (synthetic device).
- 2 `mobile_sync_event` rows linked to that session (same `device_id`, same `user_id`):
  - Event 1: `operation_type="create_time_entry"`, `status="committed"`, `idempotency_uuid=<random uuid>`
  - Event 2: `operation_type="create_expense"`, `status="committed"`, `idempotency_uuid=<random uuid>`

> **Check MCP query #6** for exact column names on `mobile_sync_session`. `mobile_sync_event` has no FK to `mobile_sync_session` — they are linked by `device_id` + `user_id` context.

**Required functions**: same 3-function pattern as Task 1.

After creating:
- Register in `reset_dev_db.py` as scenario `"mobile_sync"`
- Add BOTH new seeds to `backend/tests/e2e/seed_e2e_db.py` — they should run against `pilot_e2e_db`. Read `seed_e2e_db.py` to understand the call pattern.

After both seeds are done, run unit tests to confirm nothing broke:
```bash
python -m pytest -m unit --tb=short -q 2>&1 | tail -5
```

---

## Task 3 — E2E Test: W-05 Stripe Invoice Payment (cp6)

**File to create**: `backend/tests/e2e/cp6_invoice_stripe/test_invoice_stripe.py`
**File to create**: `backend/tests/e2e/cp6_invoice_stripe/__init__.py` (empty)

**`pytestmark`**: `[pytest.mark.e2e]`

> **First**: Read `backend/api/routes/webhooks_stripe.py`. Determine if a `/test` endpoint exists that bypasses HMAC verification. If yes, use it. If no `/test` endpoint exists, construct a properly HMAC-signed payload using `stripe.WebhookSignature` and the `STRIPE_WEBHOOK_SECRET` from settings.

> **`tok_visa` note**: Stripe's test card token `tok_visa` creates a reusable PaymentMethod for test mode. Use `stripe.PaymentMethod.create(type="card", card={"token": "tok_visa"})` + `stripe.PaymentMethod.attach(pm.id, customer=customer.id)`.

**Test class: `TestInvoiceStripePayment`** (3 tests):

```
test_stripe_payment_intent_created_and_succeeds
  1. Skip if STRIPE_SECRET_KEY is placeholder (sk_test_e2e_placeholder): pytest.skip("Real Stripe key not configured")
  2. import stripe; stripe.api_key = settings.STRIPE_SECRET_KEY
  3. Create customer entity via POST /api/v1/customers/test → customer_id
  4. Create site via POST /api/v1/sites/test → site_id
  5. Create invoice via POST /api/v1/invoices/test with total_cents=5000 → invoice_id
  6. stripe.Customer.create(email="e2e-stripe@pilot.local")
  7. stripe.PaymentMethod.create(type="card", card={"token": "tok_visa"})
  8. stripe.PaymentMethod.attach(pm.id, customer=stripe_customer.id)
  9. stripe.PaymentIntent.create(amount=5000, currency="usd", customer=stripe_customer.id, 
       payment_method=pm.id, confirm=True,
       automatic_payment_methods={"enabled": True, "allow_redirects": "never"})
  10. Assert pi.status == "succeeded"

test_webhook_payment_intent_succeeded_marks_invoice_paid
  1. Skip if placeholder key
  2. (Use the PaymentIntent from test 1 — OR create fresh entities + new PI)
  3. Send webhook event to backend (via /test endpoint or HMAC-signed)
  4. GET /api/v1/invoices/{invoice_id} with owner JWT
  5. Assert invoice.status_code == "paid" OR invoice.balance_due_cents == 0

test_invoice_payment_creates_payment_row
  1. Skip if placeholder key
  2. GET /api/v1/invoices/{invoice_id}/payments (or equivalent)
  3. Assert at least 1 payment row with amount_cents == 5000
```

> **Resilience**: If the Stripe payment tests interact with external Stripe API and are slow, accept that. Do NOT mock Stripe in these tests — the entire point is to test real Stripe integration.

> **Independence**: Each test should be self-contained — create fresh customer/site/invoice in each test to avoid state dependency.

---

## Task 4 — E2E Test: W-14 MFA Enrollment (extends cp1)

**File to modify**: `backend/tests/e2e/cp1_auth_tenant/test_auth_rbac.py`

**Append** a new test class at the end of the file (do NOT modify existing classes):

```python
class TestMfaEnrollment:
    """W-14: MFA enrollment — user_mfa_method row can be created and queried."""

    def test_mfa_method_row_can_be_inserted_for_user(
        self, e2e_client, e2e_engine, e2e_mock_entitlement, e2e_mock_ai
    ):
        """
        Insert a user_mfa_method row directly via e2e_engine for the test user.
        Verifies the MFA enrollment data model is correct.

        Note: MFA enrollment in production goes through Cognito. In E2E tests,
        we verify the local tracking table (user_mfa_method) can receive rows,
        since the Cognito enrollment step cannot be mocked in E2E without a
        live Cognito pool.
        """
        import uuid
        from datetime import UTC, datetime
        from sqlmodel import Session, select
        from app.models.system import UserMfaMethod  # verify import path

        enrolled_at = datetime.now(UTC)
        mfa_id = uuid.uuid4()

        with Session(e2e_engine) as db:
            # PK is mfa_method_id (not id) — verified via MCP
            row = UserMfaMethod(
                mfa_method_id=mfa_id,
                tenant_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
                user_id=uuid.UUID("00000000-0000-0000-0000-000000000002"),
                method_type="totp",
                enrolled_at=enrolled_at,
                cognito_method_id=f"e2e-test-{uuid.uuid4().hex[:8]}",
                verification_status="verified",
                created_at=enrolled_at,
                updated_at=enrolled_at,
            )
            db.add(row)
            db.commit()

            # Verify row was inserted
            fetched = db.exec(
                select(UserMfaMethod).where(UserMfaMethod.mfa_method_id == mfa_id)
            ).first()
            assert fetched is not None, "MFA method row must be retrievable after insert"
            assert fetched.method_type == "totp"
            assert fetched.verification_status == "verified"

            # Cleanup — delete the row we created (not shared seed data)
            db.delete(fetched)
            db.commit()

    def test_mfa_otp_table_accessible(
        self, e2e_client, e2e_engine, e2e_mock_entitlement, e2e_mock_ai
    ):
        """
        Verify auth_mfa_otp table is accessible (W-14 guard).
        OTP rows are ephemeral — just confirm the table exists and can be queried.
        """
        from sqlmodel import Session, select, text

        with Session(e2e_engine) as db:
            result = db.exec(text("SELECT COUNT(*) FROM auth_mfa_otp")).first()
            assert result is not None, "auth_mfa_otp table must be queryable"
            # Result is a count (may be 0 if no OTPs in E2E DB) — that's fine
            assert isinstance(result[0], int)
```

> **Import path**: Read `backend/app/models/system.py` or `backend/db_models_map.md` to confirm the correct import path for `UserMfaMethod`. If it is in a different models file, adjust the import.

---

## Task 5 — E2E Test: W-16 Notification Delivery (cp7)

**File to create**: `backend/tests/e2e/cp7_notifications/test_notification_delivery.py`
**File to create**: `backend/tests/e2e/cp7_notifications/__init__.py` (empty)

**`pytestmark`**: `[pytest.mark.e2e]`

**Strategy**: Insert `notification_event` + `notification_outbox(channel='in_app', status='pending')` directly via `e2e_engine`. Then call the notification worker's `_impl` function. Assert `notification_delivery_attempt` row is created.

> **First**: Read `backend/tasks/notification_worker.py` in full. Find the impl function that processes a single outbox record by ID. It is likely named `_process_notification_impl(notification_id: str, db: Session)` or similar. Confirm the exact function name and signature before writing the test.

**Test class: `TestNotificationDelivery`** (3 tests):

```
test_in_app_notification_delivered_on_worker_call
  1. Insert notification_event row via e2e_engine:
       notification_type_code="dunning_reminder", entity_type_code="invoice",
       entity_id=str(uuid.uuid4()), tenant_id=test_tenant_id
  2. Insert notification_outbox row:
       channel="in_app", status="pending", body="Test notification body",
       category_id="billing", priority=5, attempt_count=0,
       notification_event_id=<event.id>
  3. Import _process_notification_impl (or the correct impl function)
  4. Call: result = _process_notification_impl(str(outbox.id), db)
  5. Assert: result is truthy OR outbox.status == "sent" after db refresh
  6. Query notification_delivery_attempt for outbox.id → assert 1 row exists

test_delivery_attempt_row_has_correct_fields
  1. (Continuation of test 1, or fresh notification + call)
  2. Fetch delivery_attempt row
  3. Assert: attempt_no >= 1, status == "sent", provider is a non-empty string

test_in_app_channel_requires_no_external_service
  1. Create fresh notification_event + notification_outbox(channel="in_app")
  2. Call _process_notification_impl
  3. Assert 200-equivalent result — no exception raised
  4. Confirm no real email was sent: check that the mock AI fixture is still active
     (this is a "no-side-effect" guard test)
```

> **`e2e_engine` + Session usage**: Open a `with Session(e2e_engine) as db:` block. Pass `db` to the `_impl` function. After calling the impl, call `db.refresh(outbox)` to see the updated status. Then query `notification_delivery_attempt` in the same db session.

---

## Task 6 — E2E Test: W-07 NEC Calculation (cp8)

**File to create**: `backend/tests/e2e/cp8_nec/test_nec_calculation.py`
**File to create**: `backend/tests/e2e/cp8_nec/__init__.py` (empty)

**`pytestmark`**: `[pytest.mark.e2e]`

> **First**: Read `backend/services/nec_service.py`. Confirm `box_fill` is a valid `calc_type` and verify the exact input dict shape expected. Use the simplest valid input that will produce a deterministic result.

**Test class: `TestNecCalculation`** (3 tests):

```
test_nec_calculate_persists_log_row
  1. POST /api/v1/nec/calculate/test with:
       {"calc_type": "box_fill", "inputs": <valid box_fill input from nec_service.py>}
  2. Assert resp.status_code == 201
  3. Assert resp.json() has "log_id", "calc_type", "result", "nec_guide_version"
  4. log_id = resp.json()["log_id"]

test_nec_calc_log_retrievable
  1. (Use log_id from test 1, or create fresh calculation)
  2. GET /api/v1/nec/calc-logs/test
  3. Assert resp.status_code == 200
  4. logs = resp.json()
  5. Assert any(log["id"] == log_id for log in logs), "Created log must appear in list"

test_nec_offline_calc_can_be_saved
  1. POST /api/v1/nec/calc-logs/test with:
       {"calc_type": "box_fill", "is_offline_calc": True, 
        "inputs": <valid inputs>, "result": <valid result dict>,
        "nec_guide_version": "2023", "idempotency_key": str(uuid4())}
  2. Assert resp.status_code == 201
  3. Assert resp.json()["status"] == "saved" (or 201 with ID)
```

> **Schema check**: Read `backend/api/schemas/nec.py` before writing the request payloads. `NecCalcLogCreate` has different required fields than `NecCalculateRequest`.

---

## Task 7 — E2E Test: W-11 Mobile Sync Lifecycle (cp9)

**File to create**: `backend/tests/e2e/cp9_mobile_sync/test_mobile_sync.py`
**File to create**: `backend/tests/e2e/cp9_mobile_sync/__init__.py` (empty)

**`pytestmark`**: `[pytest.mark.e2e]`

> **First**: Read `backend/api/routes/mobile_push.py` (the `_complete_sync_session_impl` function and any sync session creation endpoints). Also read `backend/api/routes/mobile_sync.py`. Determine if there is a `/test` endpoint for creating a sync session. If not, insert rows directly via `e2e_engine`.

**Test class: `TestMobileSyncLifecycle`** (3 tests):

```
test_mobile_sync_session_can_be_created_and_completed
  1. Create mobile_sync_session row directly via Session(e2e_engine):
       triggered_by="manual", outcome=None, items_attempted=0, items_committed=0,
       items_deferred=0, items_failed=0, started_at=datetime.now(UTC),
       device_id=uuid4(), user_id=uuid.UUID("00000000-0000-0000-0000-000000000003"),
       tenant_id=uuid.UUID("00000000-0000-0000-0000-000000000001")
  2. session_id = row.id
  3. If POST /api/v1/mobile/sync-sessions/{session_id}/complete/test exists:
       call it with {"outcome": "success", "items_committed": 1}
     Else: update the row directly via Session(e2e_engine)
  4. Refresh row → assert completed_at is not None

test_mobile_sync_event_row_can_be_inserted
  1. Create mobile_sync_event row directly via Session(e2e_engine):
       operation_type="create_time_entry", status="committed",
       idempotency_uuid=uuid4(), device_id=<same device_id as session>,
       user_id=uuid.UUID("00000000-0000-0000-0000-000000000003"),
       tenant_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
       client_capture_at=datetime.now(UTC)
  2. event_id = row.id
  3. Fetch back: assert event.operation_type == "create_time_entry"
  4. assert event.status == "committed"

test_seed_nec_scenario_data_present
  # Cross-check: verify that seed_scenario_mobile_sync.py data is visible in E2E DB
  1. Query mobile_sync_session for tenant_id=test_tenant_id
  2. Assert at least 1 row with triggered_by="background" exists
     (inserted by seed_scenario_mobile_sync.py called from seed_e2e_db.py)
  3. This test validates the seed was applied correctly — if it fails, seed_e2e_db.py
     needs to be re-run against pilot_e2e_db
```

> **If `MobileSyncSession` import path is unclear**: read `backend/db_models_map.md` to find the correct model import path.

---

## Task 8 — Update `seed_e2e_db.py`

Read `backend/tests/e2e/seed_e2e_db.py` and add calls to both new seed scripts:

```python
from migrations.scripts.seed_scenario_nec import seed as seed_nec
from migrations.scripts.seed_scenario_mobile_sync import seed as seed_mobile_sync

# Call after existing Group D seeds:
print("Seeding NEC scenario...")
seed_nec(db_url=E2E_DATABASE_URL)

print("Seeding mobile sync scenario...")
seed_mobile_sync(db_url=E2E_DATABASE_URL)
```

> Match the exact import + call pattern used for the existing scenarios in `seed_e2e_db.py`. Read the file first.

---

## Task 9 — Update `scenario-coverage-catalog.md`

After all tests pass, update `dev-docs/testing-support/scenario-coverage-catalog.md`:

**Part 1 matrix** — change these rows:

| Workflow | Tier 1 (pytest) | Update to |
|---|---|---|
| W-05 | ☐ | ✅ cp6_invoice_stripe |
| W-07 | ☐ | ✅ cp8_nec |
| W-11 | ☐ | ✅ cp9_mobile_sync |
| W-14 | 🔄 CP-1 (login only) | ✅ CP-1 extended (MFA enrollment) |
| W-16 | 🔄 CP-5 partial | ✅ cp7_notifications |

**Part 6.3** — update the "Tier 1 Gap" column for each workflow with a ✅ and the file path.

**Part 6.4** — update coverage summary table.

Do NOT modify Part 5 Maintenance Rules or Part 4 Playwright scope.

---

## Verification Checkpoints

**After Tasks 1–2 (seeds):**
```bash
python -m pytest -m unit --tb=short -q 2>&1 | tail -5
# Should show same unit count as baseline — seeds are not unit-tested directly
```

**After Tasks 3–7 (E2E tests written):**
```bash
# Run the E2E suite with --e2e flag
python -m pytest tests/e2e/ --e2e --tb=short -q 2>&1 | tail -20
```

Fix any failure before moving to the next task.

---

## Final Verification

### Phase 1 — Unit Tests Only

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=short -q 2>&1 | tail -10
```

Unit test count must be ≥ baseline (no regressions). This batch adds E2E tests, not unit tests, so the unit count should stay the same.

### Phase 2 — Full E2E Suite

```bash
cd <repo>/backend
source .venv/bin/activate

# Full E2E suite — all 9 CPs
python -m pytest tests/e2e/ --e2e --tb=short -v 2>&1 | tail -40

# Spot check new CPs
python -m pytest tests/e2e/cp6_invoice_stripe/ --e2e -v 2>&1 | tail -15
python -m pytest tests/e2e/cp7_notifications/ --e2e -v 2>&1 | tail -15
python -m pytest tests/e2e/cp8_nec/ --e2e -v 2>&1 | tail -15
python -m pytest tests/e2e/cp9_mobile_sync/ --e2e -v 2>&1 | tail -15
python -m pytest tests/e2e/cp1_auth_tenant/ --e2e -v 2>&1 | tail -15

echo "=== E2E-B1 FINAL VERIFICATION COMPLETE ==="
```

> **Any failure in the E2E suite must be fixed before declaring done.** If a Stripe test fails due to a missing `/test` endpoint on the webhook route, adapt the test to use the HMAC-signed approach. Document the adaptation in your Completion Summary.

---

## Definition of Done

- [ ] Pre-modification regression baseline captured (`X passed unit`)
- [ ] Zero pre-existing unit failures confirmed (or confirmed with Tom)
- [ ] All MCP pre-work queries run — all 12 target tables confirmed to exist
- [ ] `backend/services/nec_service.py` read — valid `calc_type` + input shape confirmed
- [ ] `backend/api/routes/webhooks_stripe.py` read — Stripe webhook `/test` endpoint verified or HMAC approach selected
- [ ] `backend/tasks/notification_worker.py` read — correct `_impl` function identified
- [ ] `backend/tests/e2e/conftest_e2e.py` read — E2E fixture pattern understood
- [ ] `backend/migrations/scripts/seed_e2e_db.py` read — call pattern understood
- [ ] `seed_scenario_nec.py` created with `seed()` / `mode_reset()` / `mode_inspect()`
- [ ] `seed_scenario_mobile_sync.py` created with same 3 functions
- [ ] Both seeds registered in `reset_dev_db.py`
- [ ] Both seeds added to `seed_e2e_db.py`
- [ ] `cp6_invoice_stripe/test_invoice_stripe.py` created — 3 E2E tests, `pytest.mark.e2e`
- [ ] `cp1_auth_tenant/test_auth_rbac.py` extended — `TestMfaEnrollment` class appended (2 tests)
- [ ] `cp7_notifications/test_notification_delivery.py` created — 3 E2E tests, `pytest.mark.e2e`
- [ ] `cp8_nec/test_nec_calculation.py` created — 3 E2E tests, `pytest.mark.e2e`
- [ ] `cp9_mobile_sync/test_mobile_sync.py` created — 3 E2E tests, `pytest.mark.e2e`
- [ ] All `__init__.py` files created for new CP directories
- [ ] `scenario-coverage-catalog.md` Part 1 matrix updated — W-05, W-07, W-11, W-14, W-16 Tier 1 = ✅
- [ ] **Phase 1**: Unit test count ≥ baseline (no regressions)
- [ ] **Phase 2**: Full E2E suite passes — `pytest tests/e2e/ --e2e --tb=short` shows 0 failures across CP-1 through CP-9
- [ ] Final E2E test count (before → after) documented
- [ ] Completion Summary added to `pilot-launch-plan.md` §E2E Test Harness

---

## Completion Summary

After all Definition of Done items are complete, add a **Completion Summary** subsection to `dev-docs/analysis/pilot-launch-plan.md` §E2E Test Harness, under the SD-10 Tier 2 summary, using this format:

```markdown
### E2E-B1 — E2E Gap Closure (W-05, W-07, W-11, W-14, W-16): Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot Python Engineer
**Unit baseline**: X passed (unchanged — no unit tests added)
**E2E baseline**: N passed (SD-10 CP-1 through CP-5)
**E2E final**: N+14 passed (CP-1 through CP-9 — 14 new E2E tests)

#### What Was Accomplished

- [Brief description of each CP added]
- [Any deviations from the design doc — e.g., Stripe webhook approach used]

#### Files Changed / Created

| File | Action |
|---|---|
| `backend/migrations/scripts/seed_scenario_nec.py` | Created |
| `backend/migrations/scripts/seed_scenario_mobile_sync.py` | Created |
| `backend/migrations/scripts/reset_dev_db.py` | Updated — 2 new scenarios registered |
| `backend/tests/e2e/seed_e2e_db.py` | Updated — 2 new seeds called |
| `backend/tests/e2e/cp6_invoice_stripe/__init__.py` | Created |
| `backend/tests/e2e/cp6_invoice_stripe/test_invoice_stripe.py` | Created — 3 tests |
| `backend/tests/e2e/cp1_auth_tenant/test_auth_rbac.py` | Updated — TestMfaEnrollment class added (2 tests) |
| `backend/tests/e2e/cp7_notifications/__init__.py` | Created |
| `backend/tests/e2e/cp7_notifications/test_notification_delivery.py` | Created — 3 tests |
| `backend/tests/e2e/cp8_nec/__init__.py` | Created |
| `backend/tests/e2e/cp8_nec/test_nec_calculation.py` | Created — 3 tests |
| `backend/tests/e2e/cp9_mobile_sync/__init__.py` | Created |
| `backend/tests/e2e/cp9_mobile_sync/test_mobile_sync.py` | Created — 3 tests |
| `dev-docs/testing-support/scenario-coverage-catalog.md` | Updated — W-05, W-07, W-11, W-14, W-16 Tier 1 = ✅ |

#### Tests Added

| Test File | Type | Tests | All Pass |
|---|---|---|---|
| `cp6_invoice_stripe/test_invoice_stripe.py` | E2E | 3 | ✅ |
| `cp1_auth_tenant/test_auth_rbac.py` (additions) | E2E | 2 | ✅ |
| `cp7_notifications/test_notification_delivery.py` | E2E | 3 | ✅ |
| `cp8_nec/test_nec_calculation.py` | E2E | 3 | ✅ |
| `cp9_mobile_sync/test_mobile_sync.py` | E2E | 3 | ✅ |
```

Also update `dev-docs/testing-support/scenario-coverage-catalog.md` Part 1 matrix ✅ markers before declaring done.
