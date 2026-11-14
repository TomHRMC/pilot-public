# Batch Design: E2E-B1 — E2E Gap Closure (W-05, W-07, W-11, W-14, W-16)

**Batch**: E2E-B1  
**Engineer**: Python Engineer  
**Date**: 2026-07-12  
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §Phase 1 — E2E Test Harness  
**Source spec**: `dev-docs/testing-support/scenario-coverage-catalog.md` §6.5  
**Status**: 🟡 Design complete — awaiting implementation  

---

## A. Input Read Summary

| Input | What Was Read | Key Finding |
|---|---|---|
| `pilot-launch-plan.md` | Full doc | E2E-B1 is item #11 in Phase 1 batch sequence — all prerequisite batches (B19, FE-B26 through FE-B31, MOB-B8, MOB-B9) complete. Tom added real Stripe test key to `backend/.env.e2e` on 2026-07-07 ✅ |
| `scenario-coverage-catalog.md` §6.3–6.5 | Full gap register + recommended tasks | E2E-B1 closes P0 + P1 gaps: W-05 (Stripe), W-07 (NEC calc), W-11 (mobile sync), W-14 (full MFA), W-16 (notification delivery). 5 tasks defined with exact output file paths. |
| `backend/tests/e2e/conftest_e2e.py` | Full file | E2E fixture pattern: `e2e_engine` (session-scoped, port 5433), `e2e_client` (FastAPI TestClient with E2E DB override), `e2e_mock_cognito`, `e2e_mock_entitlement`, `e2e_mock_ai`. No per-test rollback — tests use unique IDs. |
| `backend/tests/e2e/cp1_auth_tenant/test_auth_rbac.py` | Full file | Pattern: `patch("core.auth.verify_cognito_jwt")` for RBAC tests; `/test` endpoints for data creation; `pytestmark = [pytest.mark.e2e]`. |
| `backend/api/routes/nec.py` | Full file | `POST /api/v1/nec/calculate/test` exists. Accepts `NecCalculateRequest(calc_type, inputs, job_id?, idempotency_key?)`. Returns `NecCalculateResponse(log_id, calc_type, result, nec_guide_version, nec_citation)`. No new endpoints needed. |
| `backend/api/routes/mobile_push.py` | Lines 130–240 | `_complete_sync_session_impl` exists + `POST /api/v1/mobile/sync-sessions/{session_id}/complete` and `/test` variant. Session creation endpoints also exist in mobile routes. |
| `backend/tasks/notification_worker.py` | Lines 1–80 | `_send_via_channel()` handles `in_app` channel by returning `{"status": "sent"}` immediately — no external API call. Safe for E2E test. |
| MCP: `nec_calculation_log` | Columns verified | `id`, `tenant_id`, `user_id`, `job_id`, `calc_type`, `nec_guide_version`, `inputs_json`, `result_json`, `is_offline_calc`, `idempotency_key`, `client_capture_at`, `created_at`, `updated_at` |
| MCP: `mobile_sync_session` | Columns verified | `id`, `tenant_id`, `user_id`, `device_id`, `triggered_by`, `started_at`, `completed_at`, `outcome`, `items_attempted`, `items_committed`, `items_deferred`, `items_failed`, `failure_reason`, `created_at` |
| MCP: `mobile_sync_event` | Columns verified | `id`, `tenant_id`, `user_id`, `device_id`, `operation_type`, `operation_payload_summary`, `status`, `conflict_severity`, `client_capture_at`, `synced_at`, `error_detail`, `idempotency_uuid`, `created_at`, `created_by`, `resolution_action` |
| MCP: `user_mfa_method` | Columns verified | PK: `mfa_method_id`, columns: `tenant_id`, `user_id`, `method_type`, `enrolled_at`, `last_used_at`, `cognito_method_id`, `verification_status`, `metadata`, `created_at`, `updated_at` |
| MCP: `notification_event` | Columns verified | `id`, `tenant_id`, `notification_type_code`, `entity_type_code`, `entity_id`, `occurred_at`, `payload` |
| MCP: `notification_outbox` | Columns verified | `id`, `notification_event_id`, `tenant_id`, `channel`, `body`, `status` (default `'pending'`), `attempt_count` (default 0), `category_id`, `priority` |
| MCP: `notification_delivery_attempt` | Columns verified | PK: `bigint id`, `notification_outbox_id`, `tenant_id`, `attempt_no`, `status`, `provider`, `details`, `attempted_at` |
| MCP: `auth_mfa_otp` | Columns verified | `id`, `user_id`, `contact_id`, `channel`, `code_hash`, `expires_at`, `consumed_at`, `attempt_count` |
| MCP: all 12 target tables | Table existence check | All 12 tables confirmed to exist in live DB. No migrations needed for this batch. |
| `alembic_version` | Current head | `b1bd90914b77` (B21 migration — recurring job scheduled notification template) |

---

## B. Migration Plan

**No Alembic migrations in this batch.** E2E-B1 is purely a test engineering batch — all target tables (`nec_calculation_log`, `mobile_sync_session`, `mobile_sync_event`, `user_mfa_method`, `notification_event`, `notification_outbox`, `notification_delivery_attempt`) already exist in the live DB. No new columns, no new tables.

The only file-system additions are:
- 2 seed scripts: `seed_scenario_nec.py` + `seed_scenario_mobile_sync.py`
- 5 E2E test files across 4 new CP directories (cp6, cp7, cp8, cp9)
- 1 existing file extended: `cp1_auth_tenant/test_auth_rbac.py`

---

## C. Execution Order

| Step | What | Why |
|---|---|---|
| 1 | Write `seed_scenario_nec.py` | W-07 seed — must exist before cp8 test runs |
| 2 | Write `seed_scenario_mobile_sync.py` | W-11 seed — must exist before cp9 test runs |
| 3 | Register both seeds in `reset_dev_db.py` | Makes seeds available to development environment |
| 4 | Create `tests/e2e/cp6_invoice_stripe/` + `test_invoice_stripe.py` | W-05 — Stripe payment E2E |
| 5 | Extend `tests/e2e/cp1_auth_tenant/test_auth_rbac.py` | W-14 — MFA enrollment class appended |
| 6 | Create `tests/e2e/cp7_notifications/` + `test_notification_delivery.py` | W-16 — notification delivery pipeline |
| 7 | Create `tests/e2e/cp8_nec/` + `test_nec_calculation.py` | W-07 — NEC calculation round-trip |
| 8 | Create `tests/e2e/cp9_mobile_sync/` + `test_mobile_sync.py` | W-11 — mobile sync session lifecycle |
| 9 | Update `seed_e2e_db.py` to call new scenario seeds | Seeds must run against `pilot_e2e_db` before the full E2E suite |
| 10 | Run `pytest tests/e2e/ --e2e --tb=short` | Validate all CP-1 through CP-9 pass |
| 11 | Update `scenario-coverage-catalog.md` Part 1 matrix | Mark W-05, W-07, W-11, W-14, W-16 Tier 1 = ✅ |

---

## D. New API Endpoints

**No new API endpoints.** This batch consumes existing endpoints:

| Endpoint | Used By | Purpose |
|---|---|---|
| `POST /api/v1/nec/calculate/test` | cp8 | Run NEC box_fill calculation + persist log |
| `GET /api/v1/nec/calc-logs/test` | cp8 | Verify log row returned |
| `POST /api/v1/invoices/test` | cp6 | Create invoice in E2E DB |
| `POST /api/v1/customers/test`, `POST /api/v1/sites/test` | cp6 | Create supporting entities |
| `POST /api/v1/webhooks/stripe/test` | cp6 | Receive simulated Stripe webhook |
| Existing CP-1 pattern | cp1 (extended) | RBAC assertion pattern unchanged |

The W-16 notification delivery test calls `_process_notification_outbox_impl()` directly via module import (same pattern as CP-5 dunning test which calls `_send_overdue_invoice_reminders_impl(db)`). No new endpoint required.

The W-11 mobile sync test creates rows directly via the `e2e_engine` session (raw ORM insert) — no mobile sync creation endpoint exists that is unauthenticated. The test then calls `GET /api/v1/mobile/sync-sessions/test` or equivalent to verify state, or asserts directly on the DB row.

---

## E. Pattern Reuse Decisions

| Pattern | Source | Applied Where |
|---|---|---|
| E2E fixture pattern | `conftest_e2e.py` — `e2e_client`, `e2e_mock_entitlement`, `e2e_mock_ai` | All new CP test classes use the same session-scoped fixtures |
| Direct `_impl()` function call for Celery logic | CP-5 dunning test pattern — `_send_overdue_invoice_reminders_impl(db)` | W-16: calls `_process_pending_notifications_impl(db)` directly (avoids Celery worker dependency) |
| JWT patch pattern | CP-1 `patch("core.auth.verify_cognito_jwt")` | W-14 MFA extension class |
| `/test` endpoint for entity creation | All existing CPs | W-05 (customer, site, invoice), W-07 (nec calculate) |
| Direct DB ORM insert for seed data | `conftest_e2e.py` uses `e2e_engine` | W-11 (mobile sync session + event created directly via Session) |
| `pytest.mark.e2e` | All existing CP files | All new CP files — excludes from `pytest -m unit` |
| Unique ID + assert-on-ID resilience | CP-1 through CP-5 — never asserts total counts | All new tests must filter by inserted ID, never by count |

---

## F. Shared Module Interfaces

### F.1 — `_process_pending_notifications_impl(db: Session)` (W-16 call target)

The W-16 test calls the notification worker's processing function directly. The engineer must locate the correct function signature in `backend/tasks/notification_worker.py`. Based on the file structure, the impl function processes a single `notification_outbox` record by ID:

```python
# In notification_worker.py — the impl function to call directly in tests:
# _process_notification_impl(notification_id: str, db: Session) -> dict
# 
# OR the batch processor (if it exists):
# _flush_pending_notifications_impl(db: Session) -> dict
#
# Engineer must read notification_worker.py in full to find the correct function.
# Use in_app channel — no external service needed. Pattern: call with db_session.
```

**W-16 test approach**: 
1. Insert `notification_event` + `notification_outbox(channel='in_app', status='pending')` rows directly via `e2e_engine` session
2. Call the worker impl function with the outbox ID
3. Assert `notification_delivery_attempt` row created (`status='sent'`)
4. Assert `notification_outbox.status='sent'`

### F.2 — W-05 Stripe Test Approach

The Stripe E2E test uses the Stripe Python SDK with the real `sk_test_` key from `.env.e2e`. Test flow:

```python
import stripe
stripe.api_key = settings.STRIPE_SECRET_KEY  # sk_test_... from .env.e2e

# 1. Create customer + payment method using Stripe test card
stripe_customer = stripe.Customer.create(email="e2e@pilot.local")
stripe_pm = stripe.PaymentMethod.create(
    type="card",
    card={"token": "tok_visa"},  # Stripe test token — always succeeds
)

# 2. Create PaymentIntent
pi = stripe.PaymentIntent.create(
    amount=total_cents,
    currency="usd",
    customer=stripe_customer.id,
    payment_method=stripe_pm.id,
    confirm=True,
    automatic_payment_methods={"enabled": True, "allow_redirects": "never"},
)

# 3. Simulate Stripe webhook via POST /api/v1/webhooks/stripe/test
# The /test endpoint bypasses signature verification
webhook_payload = {
    "type": "payment_intent.succeeded",
    "data": {"object": pi},
}
resp = e2e_client.post("/api/v1/webhooks/stripe/test", json=webhook_payload)

# 4. Assert invoice status = 'paid'
```

> **Engineer note**: If `POST /api/v1/webhooks/stripe/test` does not exist, check `backend/api/routes/webhooks_stripe.py` for the `/test` endpoint pattern. If it is missing, the Stripe E2E test must use the HMAC-signed webhook path with the real `whsec_test_` key from `.env.e2e` via `stripe.WebhookSignature`. Read the webhook route file first.

### F.3 — W-07 NEC Calculation Inputs

Valid `calc_type` values are defined in `backend/services/nec_service.py`. The engineer must read that file to determine a safe calc type + minimal valid input dict. `box_fill` or `wire_ampacity` are likely safe choices that produce a deterministic result. Verify before writing the test.

### F.4 — Seed Scripts Pattern

Both `seed_scenario_nec.py` and `seed_scenario_mobile_sync.py` must follow the established pattern from `backend/migrations/scripts/seed_scenario_reporting.py`:

```python
# Required functions per seed_scenario pattern:
def seed(db_url: str | None = None) -> None: ...
def mode_reset(db_url: str | None = None) -> None: ...
def mode_inspect(db_url: str | None = None) -> None: ...

if __name__ == "__main__":
    seed()
```

---

## G. Open Questions Resolved

| Question | Resolution |
|---|---|
| Is the Stripe `sk_test_` key populated in `.env.e2e`? | **Yes — confirmed.** Launch plan shows Tom completed this 2026-07-07 (E2E-B1-T0 done). The `.env.e2e` entry was confirmed ✅ in the launch plan. |
| Does `POST /api/v1/nec/calculate/test` exist? | **Yes.** Confirmed in `backend/api/routes/nec.py` lines 215–222. No new endpoint needed. |
| Which NEC calc types are valid? | Engineer must read `backend/services/nec_service.py` to confirm. Design assumes `box_fill` or `wire_ampacity`. |
| Is there a `/test` endpoint for Stripe webhooks? | Engineer must verify in `backend/api/routes/webhooks_stripe.py`. If absent, use HMAC-signed webhook approach with the test signing secret. |
| Does W-14 require a real Cognito MFA enrollment flow? | **No.** Insert a `user_mfa_method` row directly via the E2E DB session (same pattern as seed data). PK column is `mfa_method_id`, not `id`. `method_type` = `"totp"`. `verification_status` defaults to `"verified"`. `cognito_method_id` can be any non-empty string in tests. |
| How does W-16 avoid sending real emails/SMS? | Use `channel='in_app'` exclusively. `in_app` channel in `_send_via_channel()` returns `{"status": "sent"}` immediately without any external call. `e2e_mock_ai` fixture already patches AI services. Email/SMS carrier is patched via `settings.SMS_CARRIER=mock` in `.env.e2e`. |
| Does W-11 have creation endpoints for `mobile_sync_session`? | Engineer must check `backend/api/routes/mobile_push.py` and any related route files for sync session creation. If no `/test` creation endpoint exists, insert rows directly via `e2e_engine` (acceptable for this test). |
| Should seeds run against `pilot_e2e_db`? | **Yes.** Both new seed scripts must be called from `seed_e2e_db.py` with the E2E DB URL, not the dev DB. Follow the existing pattern from `seed_e2e_db.py`. |
| Is `scenario-coverage-catalog.md` authoritative? | Yes. The engineer must update the Part 1 matrix ✅ markers and the Part 6.3 table after all tests pass. |
| Does any test need `skip_mock_entitlement_allowed`? | No — the `e2e_mock_entitlement` fixture already bypasses entitlement checks session-wide for E2E tests. |

---

## Test Count Budget

| Task | Expected New Tests | File |
|---|---|---|
| E2E-B1-T1: W-05 Stripe invoice payment | 3 | `cp6_invoice_stripe/test_invoice_stripe.py` |
| E2E-B1-T2: W-14 MFA enrollment (extends CP-1) | 2 | `cp1_auth_tenant/test_auth_rbac.py` (appended) |
| E2E-B1-T3: W-16 Notification delivery | 3 | `cp7_notifications/test_notification_delivery.py` |
| E2E-B1-T4: W-07 NEC calculation | 3 | `cp8_nec/test_nec_calculation.py` |
| E2E-B1-T5: W-11 Mobile sync lifecycle | 3 | `cp9_mobile_sync/test_mobile_sync.py` |
| **Total** | **14 new E2E tests** | All marked `pytest.mark.e2e` |

**Pass gate**: `pytest tests/e2e/ --e2e --tb=short -q` shows 0 failures across CP-1 through CP-9.
