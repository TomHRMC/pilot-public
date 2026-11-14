# Implementation Prompt: ALPHA-FIX-1 — Alpha-Testing Backend Fixes (Signup Wizard Contract + Telnyx Webhook Disconnect + Worker Non-Root)

**Mode**: Pilot Python Engineer
**Batch**: ALPHA-FIX-1
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §2.3 (ALPHA-FIX-1 card)
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-alpha-fix-1-design.md` — read §D/§F/§G carefully; they contain the exact contract decisions
**Estimated session**: 3–4 hours
**Platform**: Backend only (`backend/`)
**Frontend companion**: none — no frontend changes; the web app already implements the contract this batch aligns the backend to

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-python-engineer/python-engineer-rules.md`** — full document; the 25 hard rules are non-negotiable STOPs
- **`dev-docs/architecture-design/pilot-python-engineer-methods.md`** — §8 (Router Design), §5 (Model Design), §16 (Standard Task Workflow)
- **`backend/tests/README-adding-tests.md`** — full document; governs all test file structure, domain markers, and fixture rules
- **`batch-alpha-fix-1-design.md`** — the design doc; §D defines the corrected route contract, §G resolves every ambiguity you might hit

Critical rules for this batch:

- **Rule 1 / 16**: Never guess column names, data types, or table names. Use `postgres-local` MCP to verify every name before use. If MCP returns an error → **STOP and ask Tom**.
- **Rule 11**: If ANY test fails during your work — even one that appears pre-existing — **you must fix it before declaring the batch done**. If you cannot identify the root cause → STOP and ask Tom.
- **Rule 12 (sync routes — rules §21)**: This app is **synchronous by design**. Never convert a handler that touches the sync `Session` to `async def`. (The Telnyx webhook handler is already `async def` and stays async — it performs only non-blocking I/O on the request path; do not "fix" that either.)
- **Rule 13 (Pydantic v2 — rules §22)**: v2 idioms only. No `class Config`, `@validator`, `.dict()`.
- **Rule 14 (Ruff — rules §23)**: Ruff on **changed files only** (`git diff --name-only --diff-filter=d HEAD -- '*.py' | sed 's|^backend/||'`); fix ALL errors in those files, including pre-existing ones.
- **Rule 7**: The `postgres-local` MCP is **read-only verification only** — never INSERT/UPDATE/DELETE via MCP.

---

## Pre-Work: Establish Regression Baseline

Before touching any file, capture the current **unit-only** test baseline:

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=no -q 2>&1 | tail -5
```

Record the exact count: **`X passed, Y failed`**.

> **If any tests are already failing before you start**: Do NOT treat them as "pre-existing" and proceed anyway. Either (a) confirm with Tom that it is a known, accepted failure with a documented reason, or (b) fix it before touching any batch files. You may NOT start implementation work while tests are in an unexplained failed state.

---

## Pre-Work: Run MCP Verification Queries

Run **all** of these via `postgres-local` MCP before writing any code. If any query returns unexpected results → **STOP and ask Tom**.

> **MCP Usage Rule**: The `postgres-local` MCP is for **read-only verification only**. Use it to confirm table names, column types, and existing data. Never use it to INSERT, UPDATE, or DELETE — all data changes go through the application code, seed scripts, or Alembic migrations. If a query fails or returns an error → STOP and ask Tom before proceeding. This batch verifies against `postgres-local` only — do not use `postgres-prod`.

```sql
-- 1. Confirm tenant_signup columns (the wizard writes signup_state + signup_completed_at)
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'tenant_signup'
ORDER BY ordinal_position;
-- Expect: signup_state text NOT NULL DEFAULT 'step1_account'; signup_completed_at timestamptz NULL;
-- 16 columns total including owner_email/owner_first_name/owner_last_name.

-- 2. Confirm the signup_state CHECK constraint values (must already include 'complete')
SELECT conname, contype, pg_get_constraintdef(oid)
FROM pg_constraint
WHERE conrelid = 'public.tenant_signup'::regclass
ORDER BY contype, conname;
-- Expect: tenant_signup_state_chk with all 6 states incl. 'step5_confirm' and 'complete'.

-- 3. Confirm user_endpoint columns (step3 phone processing upserts channel='sms' rows)
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'user_endpoint'
ORDER BY ordinal_position;
-- Expect: user_id, channel, value, verification_status, consent_status, is_primary, is_active, etc.

-- 4. Confirm current alembic head (no migration in this batch — this is the drift check)
SELECT version_num FROM public.alembic_version;
```

> **Engineer safety net — independent column verification (MANDATORY)**: before writing ANY SQL or SQLModel field reference, run the `information_schema.columns` query for every table you touch. The live DB is the only authoritative source. If a column name in this prompt does not match MCP output → use the MCP-returned name and note the discrepancy in your Completion Summary.

---

## Pre-Work: Read These Source Files

Use `read_file` on each of these before writing any code:

```
backend/services/tenant_signup.py                 ← core of Task 1: advance_wizard_step + _process_step_data
backend/api/routes/signup.py                      ← authenticated + /test route families; SignupStepRequest schema
backend/api/routes/webhooks_sms.py                ← Task 3: telnyx_inbound_sms (read the full handler, ~lines 520-596)
backend/Dockerfile                                ← Task 4
backend/app/models/signup.py                      ← TenantSignup model + state CHECK constraint
backend/services/notification_endpoints.py        ← upsert_owner_sms_endpoint signature (called by step3 branch)
backend/services/trial_management.py              ← activate_trial signature (called by step5 branch)
backend/services/onboarding_service.py            ← ensure_checklist_exists (step5 Charter branch)
backend/tests/conftest.py                         ← available fixtures
backend/tests/domains/identity_access/test_signup_c_step3.py        ← encodes the buggy origin-keyed contract — you will update it
backend/tests/domains/identity_access/test_cb5_step4_stripe_creation.py  ← same
backend/tests/domains/identity_access/test_cb5_step4_cohort_cap.py       ← same
backend/tests/batch_b14/test_a73_tenant_signup_state_machine.py          ← same
backend/db_models_map.md                          ← confirm TenantSignup / UserEndpoint mappings
```

Also run these greps to find every caller that encodes the old contract:

```bash
grep -rn "advance_wizard_step" backend/ --include="*.py" -l
grep -rn "step3_phone\|step4_tier\|step5_confirm" backend/tests --include="*.py" -l
grep -rn "telnyx_inbound_sms\|ClientDisconnect" backend/ --include="*.py" -l
```

---

## Background / Context

During Tom's 2026-08-11 alpha test of account signup (Charter plan selection), the plan page's "Join Charter" click failed with a generic error. The browser capture shows:

```
PUT /api/v1/signup/{tid}/step4  →  422
{"detail": {..., "detail": "phone_number is required for step 3."}}
```

**Root cause**: the authenticated step routes pass the **origin** state to `advance_wizard_step()`, and `_process_step_data()` dispatches on that origin state — so `PUT /step4` (which the frontend sends `selected_tier_id` to) is processed by the `step3_phone` branch, which since SIGNUP-C requires `phone_number`. The web frontend consistently submits **each step's own data to the same-numbered route**:

| Page | Calls | Payload |
|---|---|---|
| `/signup/phone` | `PUT /step3` | `phone_number`, `sms_consent` |
| `/signup/plan` | `PUT /step4` | `selected_tier_id` |
| `/signup/ready` | `PUT /step5` | `confirmed: true` |

This batch aligns the backend to that contract (design §G Q1–Q2 explain why the backend changes, not the frontend). Two more production log defects from the same test session are fixed in Tasks 3–4. **No DB migration, no seed changes, no new endpoints, no OpenAPI changes.**

Full detail: `be-ecs-logging-issues-discovered-2026.08.11.md`.

---

## Task 1 — Signup wizard contract fix (`backend/services/tenant_signup.py`)

Implement design §D/§F.1/§F.2 exactly:

1. **Destination-state dispatch**: in `advance_wizard_step()`, call `_process_step_data(db, tenant_id, next_state, step_data, signup, request)` — the destination state, not `current_state`. Do not modify the `_process_step_data` branches themselves; they were always written against destination-step data.

2. **Auto-complete on step5**: when `next_state == "step5_confirm"`, set `signup.signup_state = "complete"` and `signup.signup_completed_at = datetime.now(UTC)` in the same transaction (the `step5_confirm → complete` transition has no route; `step5_confirm` is transient). Otherwise advance to `next_state` as today. Do not modify `VALID_STATE_TRANSITIONS`.

3. **Step5 forward-idempotency** (design §F.2): before the staleness guard, if `current_state == "step4_tier"` (i.e., a step5 PUT) and the DB state is already `step5_confirm` or `complete`, return `{"tenant_id": str(tenant_id), "signup_state": signup.signup_state, "next_step": None}` with 200 — no reprocessing. **All other steps keep the strict 409 staleness guard** — do not generalize this.

4. Verify the `/test` route twins in `api/routes/signup.py` need no changes (they call the same service — the fix propagates). If any `/test` route passes a state inconsistent with the corrected dispatch, align it and note it.

Intermediate check:

```bash
python -m pytest -m unit tests/domains/identity_access/ --tb=short -q 2>&1 | tail -10
```

Expect failures in the four test files listed in Pre-Work — they encode the old contract. That is Task 2.

---

## Task 2 — Repair contract-encoding tests + add wizard regression test

1. **Update** the tests that call `advance_wizard_step()` with origin-keyed payloads so the payload matches the destination state (e.g., a call advancing `step2_legal → step3_phone` must now carry `phone_number`; `step3_phone → step4_tier` carries `selected_tier_id`; `step4_tier → step5_confirm` carries `confirmed`):
   - `backend/tests/batch_b14/test_a73_tenant_signup_state_machine.py`
   - `backend/tests/domains/identity_access/test_signup_c_step3.py`
   - `backend/tests/domains/identity_access/test_cb5_step4_stripe_creation.py`
   - `backend/tests/domains/identity_access/test_cb5_step4_cohort_cap.py`
   - Any others found by the Pre-Work greps.

2. **Create** `backend/tests/domains/identity_access/test_alpha_fix_1_signup_wizard_contract.py` covering (design §H):
   1. Full wizard chain step1→step5 with per-step payloads → final state `complete`, `signup_completed_at` set.
   2. The production failure case: origin `step3_phone` + `{"selected_tier_id": ...}` → advances to `step4_tier` and sets `tenant.current_subscription_tier_id` (no more 422).
   3. Origin `step2_legal` + phone payload → SMS `user_endpoint` row persisted for the inserted user (scope assertions by inserted IDs — never row counts).
   4. Origin `step2_legal` **without** `phone_number` → 422 (SIGNUP-C guard intact).
   5. Step5 replay when already `complete` → 200, and `activate_trial` / `ensure_checklist_exists` are NOT re-invoked (mock call counts).
   6. Non-terminal replay (step4 payload when already past `step3_phone`) → 409 unchanged.

Domain folder: `identity_access/`. Per the Test Requirements below for markers/fixtures.

---

## Task 3 — Telnyx webhook `ClientDisconnect` handling (`backend/api/routes/webhooks_sms.py`)

Implement design §F.3 exactly: wrap `payload_bytes = await request.body()` in `try/except starlette.requests.ClientDisconnect`; on disconnect, `logger.info(...)` and raise `HTTPException(400)` with the RFC 7807 validation-error problem dict from the design (never an unhandled 500; 400 so Telnyx retries on a fresh connection). Do not change anything after the body read — signature verification, event routing, and background dispatch are untouched.

**Test**: add a test beside the existing `webhooks_sms` tests (find via the Pre-Work grep; expected domain folder `notifications_comms/`): monkeypatch `starlette.requests.Request.body` (or the request fixture) to raise `ClientDisconnect` → assert 400 response, RFC 7807 body, and that signature verification is never invoked. Name the file `test_alpha_fix_1_webhook_disconnect.py` in the same folder as the existing webhook tests.

Intermediate check:

```bash
python -m pytest -m unit --tb=short -q 2>&1 | tail -10
```

---

## Task 4 — Non-root container user (`backend/Dockerfile`)

Implement design §F.4: after `COPY . .` and before `CMD`, add:

```dockerfile
# Run as non-root (ALPHA-FIX-1) — same image serves worker, beat, and API.
RUN useradd --create-home --uid 10001 pilot \
    && chown -R pilot:pilot /app
USER pilot
```

Constraints:
- All `pip install` / `apt-get` steps must remain **above** the `USER` switch (they need root).
- The image is shared by the API (uvicorn), Celery worker, and Celery beat — all run fine unprivileged; no port < 1024 is bound inside the container.
- **Verification**: if Docker is available locally, `docker compose up worker` (or `docker build`) and confirm the `SecurityWarning: You're running the worker with superuser privileges` line is gone from the boot log. If local Docker verification isn't possible in this session, say so explicitly in the Completion Summary and flag post-deploy CloudWatch verification to Tom.

---

## Verification Checkpoints

- After Task 1: `pytest -m unit tests/domains/identity_access/ --tb=short -q | tail -10` (expected: old-contract failures only)
- After Task 2: `pytest -m unit --tb=short -q | tail -5` — zero failures
- After Task 3: full unit pass again
- After Task 4: container boot check (above)

---

## Regeneration Steps

- **OpenAPI**: route paths/schemas unchanged → `python export_openapi_json.py` is **not required**. If you find you changed any route signature or schema, run it and note why.
- **db_models_map.md / app_model_imports.md**: models unchanged → model map regen not required. New test files added → run:
  ```bash
  python generate_app_import_map.py tests > app_model_imports.md
  ```
- **schema_manager.py / seed rollout**: N/A — no schema or data changes in this batch.

---

## Final Verification

### Phase 1 — Unit Tests Only (run after each task group during development)

```bash
cd <repo>/backend
source .venv/bin/activate
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
    ruff check --fix $CHANGED_PY
    ruff format $CHANGED_PY
    ruff check $CHANGED_PY
fi

# Full suite including integration tests
python -m pytest --tb=short -q 2>&1 | tail -10

# Batch-specific spot checks
python -m pytest tests/domains/identity_access/test_alpha_fix_1_signup_wizard_contract.py -v 2>&1 | tail -20

echo "=== ALPHA-FIX-1 FINAL VERIFICATION COMPLETE ==="
```

> **Warning-clean is part of done.** `ruff` must report no remaining issues in your changed files, and the pytest run must be free of `DeprecationWarning` noise. Any failure in either phase must be fixed before the batch is declared done — no "pre-existing failure" exception without explicit written confirmation from Tom.

---

## Test Requirements

Per `backend/tests/README-adding-tests.md`:

**Every new test file MUST:**
- Declare `pytestmark` with both domain marker and `pytest.mark.unit`:
  ```python
  pytestmark = [
      pytest.mark.domain_identity_access,   # or domain_notifications_comms for the webhook test
      pytest.mark.unit,
  ]
  ```
- Use the `client` fixture (never module-level `TestClient`)
- Use `test_tenant` / `test_user` fixtures (never hardcoded UUIDs)
- Scope assertions by inserted IDs — never `assert len(all_rows) == N`
- Be placed in the correct domain folder: signup tests → `tests/domains/identity_access/`; webhook test → same folder as the existing `webhooks_sms` tests (expected `notifications_comms/`)

**Test Resilience Rule (MANDATORY)**: never UPDATE/DELETE rows you did not INSERT; never assert on total row counts; never assume a table is empty (use `second_tenant` for empty-state); `db_session` rollback is the cleanup mechanism.

**Autouse fixtures you do not declare**: `mock_cognito_jwks`, `mock_ai_services`, `mock_entitlement_allowed`. If a test exercises entitlement gating, add `@pytest.mark.skip_mock_entitlement_allowed`. Not expected to be needed here.

**Existing fixtures to reuse**: `test_tenant`, `test_user`, `second_tenant`, `mock_cognito_jwt`, `utc_now`/`aware_datetime`. For Stripe-touching paths in step4 processing, follow the mocking pattern already used in `test_cb5_step4_stripe_creation.py`.

---

## Definition of Done

Update `pilot-launch-plan.md` §2.0 row 10b when done (mark ✅), and check off:

- [ ] Pre-modification regression baseline captured (`X passed, Y failed`) using `pytest -m unit`
- [ ] Zero pre-existing unit failures confirmed before starting work (or confirmed with Tom)
- [ ] All 4 MCP pre-work queries run — `tenant_signup` columns + state CHECK constraint (incl. `complete`), `user_endpoint` columns, alembic head confirmed
- [ ] All mandatory source files read before writing any code (including `notification_endpoints.py`, `trial_management.py`, `onboarding_service.py`)
- [ ] Task 1: destination-state dispatch + step5 auto-complete (`signup_completed_at` set) + step5 forward-idempotent replay; all other steps keep the 409 guard
- [ ] Task 2: four old-contract test files updated + new `test_alpha_fix_1_signup_wizard_contract.py` with all 6 design-§H cases passing
- [ ] Task 3: `ClientDisconnect` → 400 RFC 7807 in `telnyx_inbound_sms` + disconnect test passing
- [ ] Task 4: `USER pilot` in `backend/Dockerfile` (installs stay above the switch); boot-log verification done or explicitly flagged
- [ ] No new `async def` on DB-touching code; webhook handler left async (rules §21)
- [ ] Only Pydantic v2 idioms; no route signature changes (or OpenAPI regenerated with a note)
- [ ] All new test files use `pytestmark` with domain marker + `pytest.mark.unit`; no module-level `TestClient`; no hardcoded UUIDs
- [ ] `python generate_app_import_map.py tests > app_model_imports.md` run (new test files added)
- [ ] `ruff check --fix && ruff format` run **on changed files only** — zero remaining issues in those files, no unjustified `# noqa` (rules §23)
- [ ] **Phase 1**: All unit tests pass (`pytest -m unit`) — zero failures including any pre-existing
- [ ] **Phase 2**: Full test suite passes (`pytest`) — zero failures including integration tests, warning-clean
- [ ] Final test count (before → after) documented
- [ ] Completion Summary appended to `pilot-launch-plan.md` Appendix C + §2.0 row 10b marked ✅ + INT-BUG-1 row (§5) verified as corrected by the design reference

---

## Completion Summary

After all Definition of Done items are complete:

1. Append a **Completion Summary** to `dev-docs/analysis/pilot-launch-plan.md` **Appendix C** (end of file) using the format below.
2. Mark §2.0 row 10b ✅ with the one-line outcome.
3. This batch's design already corrected the INT-BUG-1 root-cause note — no other source spec has open task headers for this batch.

```markdown
### ALPHA-FIX-1 — Alpha-Testing Backend Fixes: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot Python Engineer
**Baseline**: X passed, Y failed
**Final**: X+N passed, Y failed (+N new tests)

#### What Was Accomplished

- Signup wizard contract corrected (destination-state dispatch; step5 auto-complete; forward-idempotent step5)
- Old-contract tests repaired; full-wizard regression test added
- Telnyx webhook ClientDisconnect → 400 (no more ASGI ExceptionGroup noise)
- Dockerfile non-root user (worker SecurityWarning eliminated)

#### Files Changed / Created

| File | Action |
|---|---|
| `backend/...` | Created / Updated — ... |

#### Tests Added

| Test File | Domain | Tests | All Pass |
|---|---|---|---|
| `tests/domains/identity_access/test_alpha_fix_1_signup_wizard_contract.py` | `identity_access` | N | ✅ |
```

---

## After This Task — Next Step

Tom redeploys the API + worker images and re-runs the Charter signup E2E (account → legal → phone → plan → ready). Expected: `PUT /step4` returns 200, wizard reaches `complete`, `signup_completed_at` set, no `ClientDisconnect` tracebacks or celery root warnings in CloudWatch. Then the next batch per launch plan §2.1 Order 4: **C-B16**.
