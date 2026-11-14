# Batch Design: ALPHA-FIX-1 — Alpha-Testing Backend Fixes (Signup Wizard Contract + Telnyx Webhook Disconnect + Worker Non-Root)

**Version**: 1.0
**Date**: 2026-08-11
**Author**: Pilot Architect
**Owner**: Pilot Python Engineer
**Priority**: P1 — Pre-GA (blocks Charter signup E2E)
**Estimated**: 3–4 hours
**Source plan**: `pilot-launch-plan.md` §2.3 (ALPHA-FIX-1 card)
**Evidence doc**: `be-ecs-logging-issues-discovered-2026.08.11.md`
**Supersedes/corrects**: launch plan **INT-BUG-1** root-cause note (§5) — see §G Q4.

---

## Background

Three defects surfaced during 2026-08-11 alpha testing of account signup against the deployed integration environment:

1. **Signup wizard contract off-by-one (P0-class, blocks all self-serve signup).** Clicking "Join Charter" on `/signup/plan` fails with the generic "Failed to save your plan selection." The browser capture shows `PUT /api/v1/signup/{tid}/step4` → **422** `"phone_number is required for step 3."` Root cause: the authenticated step routes in `backend/api/routes/signup.py` advance the wizard *from the previous state* and `_process_step_data()` dispatches on the **origin** state — so `PUT /step4` is processed as *step-3 phone data*, which since SIGNUP-C requires `phone_number`. The web frontend submits each step's data to the same-numbered route (`/step3` ← phone, `/step4` ← tier, `/step5` ← confirm). Side effects:
   - Phone numbers submitted by the phone page to `PUT /step3` are **silently dropped** (processed as the `step2_legal` no-op branch) — SIGNUP-C compliance break (phone persisted only because `POST /phone/consent` independently upserts the endpoint).
   - Tier selection submitted to `PUT /step4` hard-fails 422.
   - No route advances `step5_confirm → complete`, so `tenant_signup.signup_completed_at` is never set (the signup-cleanup runbook gate keys on this).
   - The `/test` route twins mirror the same origin-keyed mapping, so the test suite never caught the drift.

2. **Unhandled `ClientDisconnect` in the Telnyx inbound webhook.** `webhooks_sms.py` — `payload_bytes = await request.body()` raises `starlette.requests.ClientDisconnect` when the caller (Telnyx edge) drops the connection mid-body. It propagates through the middleware stack as an `ExceptionGroup: unhandled errors in a TaskGroup` and logs a full-page ASGI ERROR traceback. Log evidence shows bursts of duplicate `POST /webhooks/sms/telnyx-inbound` from multiple Telnyx egress IPs (203.0.113.x) in the same second — retry behavior — so this will recur under production load.

3. **Celery worker runs as root.** Worker boot log: `SecurityWarning: You're running the worker with superuser privileges ... uid=0`. `backend/Dockerfile` has no `USER` directive; the same image serves worker, beat, and API.

### Explicitly out of scope (documented, not fixed here)

- **`POST /api/v1/signup/{tenant_id}/payment-intent` does not exist** in the backend (verified absent from `openapi.json`). The plan page calls it only for non-trial, non-Charter paid tiers (GA mode); in Charter mode the call fires but its failure is non-blocking (`useQuery`, `clientSecret` unused for Charter). Deferring to the GA paid-tier signup batch — logged as a follow-up in the launch plan card.
- Frontend 409-message mis-mapping on the plan page (any 409 shows "tier has reached its signup cap") — cosmetic, React-side, not this batch.

---

## A. Input Read Summary

| Input | What was read / verified | Date |
|---|---|---|
| `frontend/apps/web/src/app/signup/plan/page.tsx` | Step4 PUT payload (`selected_tier_id` only), step5 skip for Charter, 409/generic error mapping | 2026-08-11 |
| `frontend/apps/web/src/app/signup/phone/page.tsx` | Step3 PUT payload (`phone_number`, `sms_consent`) + `POST /phone/consent` + `POST /phone/send-optin` | 2026-08-11 |
| `frontend/apps/web/src/app/signup/ready/page.tsx` | Step5 PUT (`confirmed: true`) on "Get Started"; paid tiers PUT step5 twice (plan + ready) | 2026-08-11 |
| `backend/api/routes/signup.py` | Authenticated + `/test` route families; origin-state mapping; no `payment-intent` route | 2026-08-11 |
| `backend/services/tenant_signup.py` | `advance_wizard_step()` guard/transition/dispatch; `_process_step_data()` branches; C-B5 step4/step5 logic | 2026-08-11 |
| `backend/api/routes/webhooks_sms.py` (lines 530–596) | `telnyx_inbound_sms` body-read, signature verify, background dispatch | 2026-08-11 |
| `backend/Dockerfile` | No `USER` directive; shared image for worker/beat/API | 2026-08-11 |
| `backend/openapi.json` | Confirmed no `/signup/{tenant_id}/payment-intent` path exists | 2026-08-11 |
| `dev-docs/testing-support/alpha-testing/be-ecs-logging-issues-discovered-2026.08.11.md` | Worker root warning; API `ClientDisconnect` traceback; signup request timeline | 2026-08-11 |
| Browser network capture (Tom) | `PUT /step4` → 422 `"phone_number is required for step 3."` | 2026-08-11 |
| MCP `postgres-local`: `information_schema.columns` for `tenant_signup` | 16 cols incl. `signup_state` (text, default `'step1_account'`), `signup_completed_at` (nullable) — verified | 2026-08-11 |
| MCP `postgres-local`: `information_schema.columns` for `user_endpoint` | 15 cols incl. `channel`, `value`, `verification_status`, `consent_status` — verified | 2026-08-11 |
| `backend/python-engr-std-prompt-inclusions.md` | Full read — prompt section requirements | 2026-08-11 |
| `dev-docs/analysis/pilot-launch-plan.md` | §2.0/§2.3 format; INT-BUG-1 row (§5) | 2026-08-11 |

---

## B. Migration Plan

**None.** No schema changes, no data changes, no seed rollout (rule §11.5 N/A — nothing added to the DB). All three fixes are code/packaging only.

---

## C. Execution Order

| # | Task | Files | Depends on |
|---|---|---|---|
| 1 | Signup wizard contract fix (destination-state dispatch + auto-complete + step5 forward-idempotency) | `backend/services/tenant_signup.py` | — |
| 2 | Update existing service/route tests broken by the contract correction + add wizard E2E regression test | `backend/tests/batch_b14/test_a73_*`, `backend/tests/domains/identity_access/test_signup_c_step3.py`, `test_cb5_step4_*.py`, new `test_alpha_fix_1_signup_wizard_contract.py` | 1 |
| 3 | Telnyx webhook `ClientDisconnect` handling + test | `backend/api/routes/webhooks_sms.py`, new test file | — |
| 4 | Dockerfile non-root user | `backend/Dockerfile` | — |
| 5 | Ruff gate (changed files only) + full suite | — | 1–4 |

---

## D. New API Endpoints

**None.** All route paths, methods, request/response schemas, and RBAC stay identical. The fix changes *which step's data each existing route processes* — aligning the backend with the long-standing frontend contract:

| Route (unchanged) | Origin state (guard) | Data processed after fix (destination state) |
|---|---|---|
| `PUT /signup/{tid}/step2` (+`/test`) | `step1_account` | `step2_legal` — no-op (legal via `POST /legal/accept`) |
| `PUT /signup/{tid}/step3` (+`/test`) | `step2_legal` | `step3_phone` — **phone_number required**, consent, disclosure hash, endpoint upsert, double-opt-in enqueue |
| `PUT /signup/{tid}/step4` (+`/test`) | `step3_phone` | `step4_tier` — tier lock/cap/charter number/free period/Stripe creation |
| `PUT /signup/{tid}/step5` (+`/test`) | `step4_tier` | `step5_confirm` — confirm + trial/checklist; then **auto-advance to `complete`** |

Behavioral changes (both are bug corrections, not contract changes):

1. **`PUT /step5` success now advances `step4_tier → step5_confirm → complete` in one transaction**, setting `signup_completed_at = now()`. `SignupStepResponse.signup_state` returns `"complete"`. Rationale: no route existed for the final transition; `step5_confirm` becomes a transient state that never rests in the DB. `VALID_STATE_TRANSITIONS` is unchanged (the map still documents the logical chain).
2. **`PUT /step5` is forward-idempotent**: if the signup is already at `step5_confirm` or `complete`, return **200** with the current state instead of 409. Rationale: the paid-tier frontend flow PUTs step5 twice (plan page, then ready page); a network retry of a successful step5 must also not error. This exception applies **only to step5** — all other steps keep the strict 409 staleness guard (a repeated earlier step is a genuine resume conflict the frontend handles by redirect).

---

## E. Pattern Reuse Decisions

- **Idempotency** (`mvp-arch.md` §16 / infra constraints §5): the step5 forward-idempotent replay is the wizard-level analogue of the Idempotency-Key rule — a retried mutation must converge, not error.
- **RFC 7807** error shapes: unchanged; the new webhook 400 (below) uses the standard validation-error problem dict.
- **Sync-by-design**: no new routes; no `async def` changes. The webhook handler is already `async def` and stays async — it touches no sync `Session` on the request path (DB work runs in `BackgroundTasks`). The `ClientDisconnect` catch is pure async-I/O handling, consistent with rules §21.
- No new top-level UX patterns; no frontend changes at all in this batch.

---

## F. Shared Module Interfaces

### F.1 `advance_wizard_step()` — dispatch correction (`backend/services/tenant_signup.py`)

Change exactly one behavior: `_process_step_data` is invoked with the **destination** state, and the final transition auto-completes.

```python
# Validate transition
next_state = VALID_STATE_TRANSITIONS.get(current_state)
if not next_state:
    raise HTTPException(422, ...)

# ALPHA-FIX-1: process the data of the step being SUBMITTED (destination state),
# not the origin state. Frontend contract: PUT /stepN submits step N's data.
_process_step_data(db, tenant_id, next_state, step_data, signup, request)

# Advance state; step5 processing completes the wizard in the same transaction
# (no route advances step5_confirm → complete; step5_confirm is transient).
if next_state == "step5_confirm":
    signup.signup_state = "complete"
    signup.signup_completed_at = datetime.now(UTC)
else:
    signup.signup_state = next_state
```

`_process_step_data()` branches (`step2_legal`, `step3_phone`, `step4_tier`, `step5_confirm`) are **unchanged** — they were always written against the destination-step data; only the dispatch key was wrong.

### F.2 Step5 forward-idempotency (`backend/services/tenant_signup.py`)

In `advance_wizard_step()`, before the staleness guard:

```python
# ALPHA-FIX-1: forward-idempotent replay for the terminal step only.
# Paid-tier flow PUTs step5 twice (plan page + ready page); a retry of a
# completed step5 must converge, not 409.
if current_state == "step4_tier" and signup.signup_state in ("step5_confirm", "complete"):
    return {
        "tenant_id": str(tenant_id),
        "signup_state": signup.signup_state,
        "next_step": None,
    }
```

### F.3 Webhook `ClientDisconnect` handling (`backend/api/routes/webhooks_sms.py`)

```python
from starlette.requests import ClientDisconnect

# Step 1: Capture raw body BEFORE any parsing (required for signature verification)
try:
    payload_bytes = await request.body()
except ClientDisconnect:
    # ALPHA-FIX-1: Telnyx edge dropped mid-body (seen in prod as ASGI
    # ExceptionGroup noise). 400 → Telnyx retries on a fresh connection;
    # must never surface as an unhandled 500.
    logger.info("Telnyx inbound webhook: client disconnected before body read")
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail={
            "type": "https://errors.pilotfortrades.com/validation-error",
            "title": "Validation Error",
            "status": 400,
            "detail": "Request body could not be read (client disconnected).",
        },
    ) from None
```

### F.4 Dockerfile non-root user (`backend/Dockerfile`)

```dockerfile
# Run as non-root (ALPHA-FIX-1) — same image serves worker, beat, and API.
RUN useradd --create-home --uid 10001 pilot \
    && chown -R pilot:pilot /app
USER pilot
```

Placed after `COPY . .` and before `CMD`. No `pip install` after the `USER` switch (all installs happen earlier as root). Engineer must confirm the celery `SecurityWarning` is gone from a local `docker compose up worker` boot log (or document why local check isn't possible and flag for post-deploy log verification).

---

## G. Open Questions Resolved

- **Q1: Fix the frontend or the backend?** Backend. The frontend contract (`PUT /stepN` submits step N's data) matches the route names, the page flow, and resumability UX; three pages already implement it consistently. The backend's origin-keyed dispatch was the anomaly, and no route completed the wizard.
- **Q2: Why not keep origin-keyed dispatch and shift the frontend?** Would require a new `step6`/`complete` route and moving every payload one route later — strictly more churn, and the route names would permanently lie about their contents.
- **Q3: Does the phone data get double-persisted now (phone page `POST /phone/consent` + step3 processing)?** No — `upsert_owner_sms_endpoint()` is an upsert keyed on `(user_id, channel='sms', value=phone)`; the step3 branch re-runs it with the same values plus the consent-audit write, which is the SIGNUP-C-required attestation. Idempotent by design.
- **Q4: INT-BUG-1 said the prod image was stale.** Corrected: the deployed image was faithful to the repo — the repo itself had the contract mismatch (verified 2026-08-11: `advance_signup_step4` passes `"step3_phone"` in current `main`). The "route absent" half of INT-BUG-1 (`payment-intent` 404) is real and permanent until the GA paid-tier signup batch builds it (it never existed). The launch plan row is updated by this batch's design.
- **Q5: 400 vs 200 on `ClientDisconnect`?** 400. Telnyx retries on non-2xx, and a disconnect means the event was never received — a retry is the desired durability behavior. 200 would silently drop the event. The existing "always 200" rule in the handler docstring applies *post-signature-verification*; a body we could not read is pre-verification and cannot be processed.
- **Q6: Does auto-complete break the ready-page guard?** Ready page's guard redirects non-Ready states away; after completion `GET /state` returns `complete`, which `signupStateToStep` maps to dashboard (fails safe). The plan-page step5 PUT (paid tiers) returning `"complete"` is harmless — that response body is not read for state.
- **Q7: Charter cap 409 semantics preserved?** Yes — the tier-closed 409 raises inside the `step4_tier` processing branch, unchanged; it now correctly fires on `PUT /step4`.

---

## H. Test Plan (summary — full requirements in the engineer prompt)

- **Update** existing service-level tests that call `advance_wizard_step()` with origin-keyed data (they encode the buggy contract): `tests/batch_b14/test_a73_tenant_signup_state_machine.py`, `tests/domains/identity_access/test_signup_c_step3.py`, `test_cb5_step4_stripe_creation.py`, `test_cb5_step4_cohort_cap.py`.
- **New** `tests/domains/identity_access/test_alpha_fix_1_signup_wizard_contract.py`:
  1. Full wizard chain via service calls: step1→step5 payload per state → final state `complete`, `signup_completed_at` set.
  2. `PUT /step4`-equivalent (origin `step3_phone`, tier payload) advances and sets `tenant.current_subscription_tier_id` — the exact production failure.
  3. Step3-equivalent with phone payload persists the SMS `user_endpoint` row (scoped by inserted user; never count assertions).
  4. Step3-equivalent **without** `phone_number` → 422 (SIGNUP-C guard intact).
  5. Step5 replay when already `complete` → 200 idempotent (no double trial activation — `activate_trial`/checklist not re-run; assert via mock call counts).
  6. Non-terminal step replay (e.g. step4 when already past) → 409 unchanged.
- **New** webhook test (place beside existing `webhooks_sms` tests — `notifications_comms/`): monkeypatch `Request.body` to raise `ClientDisconnect` → response 400, no traceback, signature verification never invoked.
- Dockerfile change: no unit test; verified via local container boot log + post-deploy CloudWatch check (documented in DoD).
