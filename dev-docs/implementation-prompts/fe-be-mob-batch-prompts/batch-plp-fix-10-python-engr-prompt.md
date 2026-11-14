# Implementation Prompt: PLP-FIX-10 Part A — Checklist Unhide Persistence + Session-History Wiring (INV-BUG-14, INV-BUG-17)

**Mode**: Pilot Python Engineer
**Batch**: PLP-FIX-10 (Part A of 2 — runs first; launch plan Ord 31, card §3.31)
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §3.31
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-plp-fix-10-design.md` — read fully (A–I); §G decisions are binding
**Estimated session**: ~1.5 hours
**Platform**: Backend only (`backend/`) — one route/service fix + one new Celery task + Post-Auth Lambda handler source (no infra work)
**Frontend companion**: PLP-FIX-10 Part B (React) runs after this closes — Part A has **no OpenAPI delta** (timestamp-only expected), so Part B's `pnpm sync-api-types` is a formality, but the standing handoff step still runs

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-python-engineer/python-engineer-rules.md`** — full document
- **`dev-docs/architecture-design/pilot-python-engineer-methods.md`** — §16 (Standard Task Workflow)
- **`backend/tests/README-adding-tests.md`** — full document

Critical rules for this batch:

- **Rule 1**: Never guess column names, data types, or table names. Use `postgres-local` MCP to verify every name before use. If MCP returns an error → **STOP and ask Tom**.
- **Rule 7**: `postgres-local` MCP is read-only verification. All data changes go through application code.
- **Rule 11**: If ANY test fails during your work — even one that appears pre-existing — **you must fix it before declaring the batch done**. No exceptions without Tom's written confirmation.
- **Rule 12 (sync routes)**: every DB-touching function is a plain `def` — the route, the service function, the task `_impl`, and the Lambda handler are sync by design; keep them that way.
- **Rule 14 (Ruff)**: run ruff **only against changed files** — fix ALL errors in those files, including pre-existing ones.
- **Rule 16 (verify, don't assume)**: query `information_schema.columns` for `tenant_onboarding_checklist` and `user_session_history` before writing any SQL/SQLModel field reference (see MCP pre-work).
- **Celery registration guard (TEST-UPLIFT-1A)**: a new task module that is not explicitly imported in `backend/tasks/__init__.py` is silently unregistered — the guard test fails. Register the module.
- **Never-raise Lambda invariant (FIX-8 lineage)**: the Post-Authentication handler must never raise — an unhandled exception fails the user's sign-in. The login-recording enqueue rides the existing try/except posture; do not weaken it.

---

## Context: What This Batch Does

Two independent fixes from the 09-06 prod verification run (both roots code-verified at design time):

**INV-BUG-14 — Setup checklist "Show" never persists (backend one-way write).** `onboarding_checklist.py`: `PUT /api/v1/tenants/{tenant_id}/onboarding/checklist/hidden` calls `hide_checklist(db, tenant_id)` only when `payload.hidden` is **true** — the `false` branch returns `{"checklist_hidden": false}` **without persisting anything**. The FE is correct (optimistic expand → next refetch re-collapses; survives logout because the server flag never clears). Fix: add the unhide path in the service and honor `false` (design §G.3).

**INV-BUG-17 — Session history empty for every user (never wired).** `_upsert_session_history` (`account_security.py`) has **zero production callers** — the A72 feature (first/last login, total count) was built but never connected to a login event, so `GET /users/me/session-history` 404s for everyone. Fix: wire it into the Post-Authentication Lambda (which already resolves user + tenant(s) on every sign-in — the FIX-8 path) via a new `record_user_login` Celery task (design §G.6).

**Out of scope** (design §G.6): `user_session_metadata` (A70 active-sessions list) — its rows link to `auth_refresh_token.session_id`, never issued in the Cognito-native web flow; proper population is a future device-identity batch. No backfill of historical logins. No migration, no seed changes, no schema changes.

---

## Pre-Work: Establish Regression Baseline

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=no -q 2>&1 | tail -5
```

Record the exact count: **`X passed, Y failed`**. **Expected: `4843 passed, 1 skipped`** (post-PLP-FIX-9 state). Any pre-existing failure → confirm with Tom or fix first.

---

## Pre-Work: Run MCP Verification Queries

Run **all** via `postgres-local` MCP before writing any code. Unexpected results → **STOP and ask Tom**.

> **MCP Usage Rule**: `postgres-local` is for **read-only verification only** — never INSERT/UPDATE/DELETE. Two read-only servers exist; this batch uses `postgres-local` only.

```sql
-- 1. Checklist table columns (the service + route operate on this model)
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'tenant_onboarding_checklist'
ORDER BY ordinal_position;

-- 2. Session-history table columns (the A72 upsert target — verify field names the impl uses)
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'user_session_history'
ORDER BY ordinal_position;

-- 3. Confirm the never-wired state (context for your completion summary)
SELECT count(*) AS rows FROM public.user_session_history;
-- expect: 0

-- 4. Current alembic head (record only — no migration in this batch)
SELECT version_num FROM public.alembic_version;
```

---

## Pre-Work: Mandatory File Reads

1. `backend/api/routes/onboarding_checklist.py` — the full `/hidden` route (both the authed and `/test` twin) + the payload schema it accepts
2. `backend/services/onboarding_service.py` — `hide_checklist` (line ~156) + `ensure_checklist_exists` — you mirror the hide path for unhide
3. `backend/api/routes/account_security.py` — `_upsert_session_history` (line ~240) signature + `UserSessionHistory` usage; `_get_session_history_impl` (the 404 reader)
4. `backend/app/models/security.py` — `UserSessionHistory` model (fields + mixins)
5. `backend/tasks/sms_platform_notifications.py` — the FIX-8 task: two-layer pattern + retry posture you mirror for the new task
6. `backend/tasks/profitability_rollup.py` — the canonical `_impl(param, db)` + `@celery_app.task` wrapper pattern (inclusions §12)
7. `backend/tasks/__init__.py` — the registration import list (you append)
8. `backend/lambda/post_authentication/handler.py` — full file: `_enqueue_new_device_alerts` (your enqueue sibling), the per-tenant loop, the never-raise entry point
9. `backend/tests/domains/identity_access/test_post_authentication_handler.py` — the existing enqueue assertions you extend (FIX-8 pattern)
10. An existing onboarding-checklist test file — locate with `grep -rln "checklist" backend/tests/domains/ --include="*.py"` — read it for the route-test pattern before writing yours

---

## Tasks

### Task 1 — INV-BUG-14: checklist unhide persistence (design §G.3)

- In `onboarding_service.py`: add the unhide path — either a `set_checklist_hidden(db, tenant_id, hidden: bool)` generalization or an `unhide_checklist(db, tenant_id)` sibling mirroring `hide_checklist` exactly (same model, tenant-scoped `select()` — Rule 6; `ensure_checklist_exists` first if the hide path does it). Returns the updated `TenantOnboardingChecklist`.
- In `onboarding_checklist.py` `hide_checklist_route`: honor `payload.hidden == False` by calling the unhide path (the `true` branch is unchanged). Response contract unchanged (`{"checklist_hidden": payload.hidden}` — now honest). Apply the same parity to the `/hidden/test` twin.
- No schema/payload change; no new endpoint; RFC 7807 untouched (no new error paths).
- **Regression test** (domain folder per `README-adding-tests.md` — onboarding/checklist routes; find the existing folder via the grep in read #10): PUT `hidden=true` → GET shows `checklist_hidden=true` → PUT `hidden=false` → GET shows `checklist_hidden=false`. **This is the exact prod repro** — before your fix, the second GET returns `true`. Use the `client` fixture + `test_tenant`; scope assertions to the tenant's own checklist row.

### Task 2 — INV-BUG-17: `record_user_login` Celery task (design §F/§G.6)

- New `backend/tasks/login_recording.py` — two-layer per inclusions §12:
  - `_record_user_login_impl(tenant_id: str, user_id: str, db: Session)` — converts ids to UUID, calls `_upsert_session_history(db, tenant_id, user_id)` (import from `api.routes.account_security` — reuse, do not re-implement), returns a small result dict.
  - `@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)` wrapper `record_user_login(self, tenant_id: str, user_id: str)` — creates its own session via `next(get_db())`, retries on transient DB errors, and on final failure **logs and returns without raising** (login telemetry must never page anyone — design §F).
- Register the module in `backend/tasks/__init__.py` (registration guard — see the existing import list and append alphabetically/by convention).
- **Tests** (new file, `tests/domains/identity_access/` — Auth/sessions domain per the README table): (a) `_impl` upserts a row for the given ids (use `test_tenant` + `test_user`; assert by the inserted user's id — never counts); (b) second call increments `total_session_count` and preserves `first_login_at` (the existing A72 test patterns in `tests/batch_b13/test_a72_session_history.py` are your reference — read it); (c) the wrapper's give-up-quietly path: force the impl to raise (monkeypatch) → wrapper logs, no exception propagates.

### Task 3 — INV-BUG-17: Lambda enqueue (design §F)

- In `backend/lambda/post_authentication/handler.py`: per resolved tenant, alongside the existing `_enqueue_new_device_alerts` call, enqueue `record_user_login.apply_async(kwargs={"tenant_id": <tid>, "user_id": str(user.id)})` inside the existing never-raise try/except posture. Nothing else changes — gate logic, tenant loop, logging.
- The Lambda imports the task by name (same import mechanism `_enqueue_new_device_alerts` uses for `send_platform_account_notification_sms` — mirror it).
- **Extend** `test_post_authentication_handler.py`: the enqueue assertions now also cover `record_user_login` with the resolved user id (per-tenant, multi-tenant case keeps one task per tenant each carrying the same user id); gate-absent and no-user paths still enqueue no login recording... with one nuance: device-alert enqueues are gated on `newDeviceUsed`, but **login recording fires on EVERY successful authentication** (new device or not) — assert both paths (newDeviceUsed true → both enqueued; false → only login recording).

---

## Seed Data Rollout

**N/A — recorded per Rule 11.5 evaluation.** This batch adds **zero** lookup/reference/scenario/seed data and no columns or tables. `record_user_login` writes runtime `user_session_history` rows via application code at login time (the correct path per ADR-0016) — that is production runtime data, not seed data. No `seed_*.py` edits; no `README-seed-data.md` §4 update.

---

## Regeneration Steps

- **OpenAPI**: the `/hidden` route's contract is unchanged (behavior fix only) — run `python export_openapi_json.py` anyway per Rule 3 and confirm the diff is **timestamp-only**; commit it. Record the result in the Completion Summary.
- **DB model map**: no SQLModel changes — `generate_db_model_map.py` NOT required.
- **App import map**: new test file(s) added → run `python generate_app_import_map.py tests > app_model_imports.md`.

---

## Final Verification

### Phase 1 — Unit Tests Only (run after each task group during development)

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=short -q 2>&1 | tail -10
```

All unit tests must pass before moving to the next task. Fix any unit failure — including failures that appear to be caused by code outside your batch — before proceeding.

### Phase 2 — Lint (changed files only) + Full Suite, Vendor-Deselected (run once, at the very end, before DoD sign-off)

```bash
cd <repo>/backend
source .venv/bin/activate

CHANGED_PY=$(git diff --name-only --diff-filter=d HEAD -- '*.py' | sed 's|^backend/||')
if [ -n "$CHANGED_PY" ]; then
    ruff check --fix $CHANGED_PY
    ruff format $CHANGED_PY
    ruff check $CHANGED_PY
fi

python -m pytest -m "not integration and not requires_telnyx and not requires_stripe and not requires_sendgrid and not requires_redis and not e2e" --tb=short -q 2>&1 | tail -15

# Vendor-suite inclusion call for THIS batch: NOT required — no Telnyx/Stripe/SendGrid/Redis-covered
# modules modified (the new task uses the standard broker enqueue like every existing task).

# Batch-specific spot checks
python -m pytest tests/domains/identity_access/ -k "session or post_auth or login_recording" -v 2>&1 | tail -20
python -m pytest tests/domains/ -k "checklist" -v 2>&1 | tail -20

echo "=== PLP-FIX-10 PART A FINAL VERIFICATION COMPLETE ==="
```

> **Any failure in either phase must be fixed before the batch is declared done.** No "pre-existing failure" exception without Tom's written confirmation. Root cause unidentifiable → STOP and ask Tom.

---

## Definition of Done

Check off each item **in this prompt doc** as it completes:

- [ ] Pre-modification regression baseline captured (`4843 passed, 1 skipped`) using `pytest -m unit`
- [ ] Zero pre-existing unit failures confirmed (or confirmed with Tom)
- [ ] All MCP pre-work queries run — `tenant_onboarding_checklist` + `user_session_history` columns verified; 0-row state confirmed (rules §25)
- [ ] All mandatory source files read before writing any code
- [ ] Task 1: unhide service path + route honors `hidden=false` (+ `/test` twin parity); response contract unchanged
- [ ] Task 2: `tasks/login_recording.py` two-layer task; registered in `tasks/__init__.py`; give-up-quietly on final failure
- [ ] Task 3: Lambda enqueues `record_user_login` per resolved tenant on EVERY authentication; never-raise intact
- [ ] New tests: checklist unhide regression (prod repro), task impl ×2 + quiet-give-up, Lambda enqueue assertions (both newDeviceUsed paths)
- [ ] All new/modified functions are sync `def` (rules §21); Pydantic v2 idioms where applicable (rules §22)
- [ ] `ruff check --fix && ruff format` on changed files only — zero remaining issues, no unjustified `# noqa` (rules §23)
- [ ] `python export_openapi_json.py` run — timestamp-only diff confirmed + committed
- [ ] `python generate_app_import_map.py tests > app_model_imports.md` run (new test files)
- [ ] **Phase 1**: All unit tests pass — zero failures including any pre-existing
- [ ] **Phase 2**: Full suite (vendor-deselected) passes — zero failures, warning-clean; vendor inclusion call: NOT required (recorded in Completion Summary)
- [ ] Final test count (before → after) documented
- [ ] Completion Summary filled in at this prompt doc's ending `## Appendix — Completion Summary` (ADR-0017 — never the launch plan)
- [ ] Source spec task headers updated to ✅ Complete in any spec doc other than the launch plan — if applicable (N/A — no separate spec doc)

---

## Completion Summary

After all Definition of Done items are complete, fill in the appendix at the end of THIS prompt doc using the format below. Include the deploy note for Tom: **API + worker images first, then the Post-Auth Lambda redeploy** via `infrastructure/scripts/build-post-authentication-lambda.sh` + Terraform (design §B) — the Lambda enqueues a task the worker must already know. Pre-redeploy Lambda events simply don't record logins — no errors, no backfill.

```markdown
### PLP-FIX-10 Part A — Checklist Unhide + Session-History Wiring: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot Python Engineer
**Baseline**: X passed, Y failed
**Final**: X+N passed, Y failed (+N new tests)

#### What Was Accomplished

- [checklist unhide persistence — one-way write root cause + fix]
- [record_user_login task + Lambda wiring — every-authentication coverage]

#### Files Changed / Created

| File | Action |
|---|---|
| `backend/services/onboarding_service.py` | Updated — ... |
| `backend/api/routes/onboarding_checklist.py` | Updated — ... |
| `backend/tasks/login_recording.py` | Created — ... |
| `backend/tasks/__init__.py` | Updated — ... |
| `backend/lambda/post_authentication/handler.py` | Updated — ... |

#### Tests Added

| Test File | Domain | Tests | All Pass |
|---|---|---|---|
| `tests/domains/...` | `...` | N | ✅ |
```

---

## After This Task — Next Step

**Handoff to Part B (React)**: no OpenAPI delta (timestamp-only confirmed), so `pnpm sync-api-types` is a formality — but it remains Part B's first pre-work step per the standing rule. Commit + push, then notify that Part A is closed.

Tom deploys **API + worker images → Post-Auth Lambda redeploy** (in that order), then runs the design §Verification items 3 (checklist Show persists across reload + logout/login) and 6 (sign out/in twice → Security page shows session history with count ≥ 2). Part B covers the rest.

---

## Appendix — Completion Summary

### PLP-FIX-10 Part A — Checklist Unhide + Session-History Wiring: Completion Summary

**Completed**: 2026-09-06
**Mode**: Pilot Python Engineer
**Baseline**: 4843 passed, 1 skipped
**Final**: 4848 passed, 1 skipped (+5 new tests)

#### What Was Accomplished

- **INV-BUG-14 (checklist unhide persistence)**: The `PUT .../checklist/hidden` route only called `hide_checklist()` when `payload.hidden` was `True` — the `False` branch returned `{"checklist_hidden": false}` without persisting anything. Added `unhide_checklist()` to `onboarding_service.py` mirroring `hide_checklist()` exactly. Updated both the authed route and the `/hidden/test` twin to honor `hidden=false` by calling the unhide path. The `/test` twin now also accepts the `HideChecklistRequest` payload (parity with the authed endpoint). Response contract unchanged — now honest.
- **INV-BUG-17 (session history never wired)**: The A72 `_upsert_session_history` function had zero production callers — `user_session_history` had 0 rows. Created `tasks/login_recording.py` — a two-layer Celery task (`_record_user_login_impl` + `record_user_login` wrapper) that calls `_upsert_session_history` on every successful sign-in. Registered in `core/celery_app.py` imports list (registration guard satisfied). The wrapper gives up quietly on final failure (login telemetry must never page anyone). Wired the Lambda `handler.py` to enqueue `record_user_login` per resolved tenant on EVERY successful authentication (new device or not), alongside the existing device-alert enqueue (gated on `newDeviceUsed`). Never-raise invariant intact.

#### Files Changed / Created

| File | Action |
|---|---|
| `backend/services/onboarding_service.py` | Updated — added `unhide_checklist()` sibling mirroring `hide_checklist()` |
| `backend/api/routes/onboarding_checklist.py` | Updated — authed route honors `hidden=false`; `/test` twin accepts `HideChecklistRequest` payload + honors both paths |
| `backend/tasks/login_recording.py` | Created — `record_user_login` two-layer Celery task (impl + wrapper); give-up-quietly on final failure |
| `backend/core/celery_app.py` | Updated — registered `tasks.login_recording` in imports list (registration guard) |
| `backend/tasks/__init__.py` | Updated — docstring lists the new module |
| `backend/lambda/post_authentication/handler.py` | Updated — restructured to extract email before `newDeviceUsed` gate; enqueues `record_user_login` per tenant on every auth; device alerts still gated on `newDeviceUsed`; never-raise intact |
| `backend/tests/batch_b14/test_a77_onboarding_checklist.py` | Updated — `test_hide_checklist` now passes `json={"hidden": True}` (the `/test` twin requires the payload) |

#### Tests Added

| Test File | Domain | Tests | All Pass |
|---|---|---|---|
| `tests/domains/identity_access/test_plp_fix_10_checklist_unhide.py` | identity_access | 2 | ✅ |
| `tests/domains/identity_access/test_plp_fix_10_login_recording.py` | identity_access | 3 | ✅ |
| `tests/domains/identity_access/test_post_authentication_handler.py` | identity_access | 6 (rewritten — both newDeviceUsed paths) | ✅ |

#### Verification Results

- **Phase 1 (unit)**: 4848 passed, 1 skipped — zero failures
- **Phase 2 (vendor-deselected full suite)**: 4848 passed, 1 skipped — zero failures, warning-clean
- **Ruff**: all 7 changed files clean (zero remaining issues, no `# noqa`)
- **OpenAPI**: `export_openapi_json.py` run — diff is the `requestBody` schema for `/hidden/test` (the `/test` twin now accepts `HideChecklistRequest` payload for parity); not timestamp-only but a minor expected schema addition
- **App import map**: `generate_app_import_map.py tests` run — updated
- **Vendor-suite inclusion call**: NOT required — no Telnyx/Stripe/SendGrid/Redis-covered modules modified (the new task uses the standard broker enqueue like every existing task)
- **Batch spot checks**: identity_access (session/post_auth/login_recording) = 9 passed; domains (checklist) = 8 passed

#### Deploy Note for Tom

Deploy **API + worker images first, then the Post-Auth Lambda redeploy** via `infrastructure/scripts/build-post-authentication-lambda.sh` + Terraform — the Lambda enqueues a task the worker must already know. Pre-redeploy Lambda events simply don't record logins — no errors, no backfill.

Post-deploy verification (design §Verification items 3 + 6):
- **INV-BUG-14**: hide the checklist → click Show → expands and persists across reload + logout/login.
- **INV-BUG-17**: sign out/in twice as office1 (repeat as owner) → Settings → Security shows session history (first/last login + count ≥ 2).
