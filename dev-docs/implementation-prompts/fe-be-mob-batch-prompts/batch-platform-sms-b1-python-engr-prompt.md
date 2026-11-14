# Implementation Prompt: PLATFORM-SMS-B1 — Pathway C Platform SMS Templates (DB Single-Path) + Payment-Failed Sender

**Mode**: Pilot Python Engineer
**Batch**: PLATFORM-SMS-B1
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §2.3
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-platform-sms-b1-design.md` — **read in full before starting; sections A–G are binding**
**Estimated session**: 3–4 hours
**Platform**: Backend only (`backend/`)
**Frontend companion**: none — but **(v1.1)** FU3 adds a field to the `/state` response, so `python export_openapi_json.py` + commit is a required handoff step (Task 9)

**v1.1 scope addition (Tom decision 2026-08-10)** — **SIGNUP-C-FU3** folded in as Task 6a: `GET /signup/{tenant_id}/state` `collected_data` is missing `sms_consent_status`, which the live web phone page polls for (`=== "opted_in"`). Found during the 10DLC Step 3 test on the author's own phone — a verified user would hang on "Check your phone" forever. See design doc v1.1 §Purpose-2a / §G-8/§G-9.

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-python-engineer/python-engineer-rules.md`** — full document; the 25 hard rules are non-negotiable STOPs
- **`dev-docs/architecture-design/pilot-python-engineer-methods.md`** — §13 (Alembic), §8 (Router Design), §5 (Model Design), §16 (Standard Task Workflow)
- **`backend/tests/README-adding-tests.md`** — full document; this governs all test file structure, domain markers, and fixture rules
- **`dev-docs/integrations/telnyx/telnyx-10dlc-p4t-tenant-comms-campaign.md`** — §6 (samples), §8 (auto-replies): the verbatim strings this batch seeds

Critical rules for this batch:

- **Rule 1**: Never guess column names, data types, or table names. Use `postgres-local` MCP to verify every name before use. If MCP returns an error → **STOP and ask Tom**.
- **Rule 4**: All Alembic migrations must be written as **blank** migrations (never `--autogenerate`). Data changes use raw `op.execute()` with `SET LOCAL session_replication_role = 'replica';`.
- **Rule 5**: Never use module-level `TestClient` in any test file. Always use the `client` fixture from `conftest.py`.
- **Rule 6**: `db.get()` is permanently banned on tenant-scoped models. Always use tenant-scoped `select()` with an explicit `WHERE tenant_id = :tid` clause. (The `notification_template` system rows in this batch are `tenant_id IS NULL` — query with `.where(NotificationTemplate.tenant_id == None)`, not `db.get()`.)
- **Rule 7**: The `postgres-local` MCP is for **read-only verification only**. Never use it to INSERT, UPDATE, or DELETE data.
- **Rule 11**: If ANY test fails during your work — even one that appears to be pre-existing — **you must fix it before declaring the batch done**. If you cannot identify the root cause → STOP and ask Tom.
- **Rule 12 (sync routes — rules §21)**: This app is **synchronous by design**. Every DB-touching route, `_impl()`, and service function is a plain `def`. **Never** `async def` anything that touches the sync `Session`.
- **Rule 14 (Ruff — rules §23)**: Run ruff **only against the files you changed**. Fix ALL errors in those files, including pre-existing ones.
- **Rule 16 (verify, don't assume — rules §25)**: Query `information_schema.columns` for every table you touch this session before writing SQL.
- **Batch-specific — §6↔§8 code-match rule (error 806)**: The five template bodies are **campaign-locked verbatim strings** registered with Telnyx under campaign `CXXXXXX`. Character-for-character fidelity is a carrier-compliance requirement. Never paraphrase, re-punctuate, or "improve" them. If the design doc table and the live code constants disagree, **the code constants win** — flag the discrepancy in your Completion Summary.

---

## Mission

Campaign `CXXXXXX` (Pathway C — Pilot→tenant-owner platform SMS) is **approved**, but `notification_template` has zero `sms`-channel rows and the live compliance strings exist only as code constants in two files. This batch creates the single DB content path for all Pilot→tenant SMS:

1. Seed 5 `notification_type` + 5 `notification_template` (channel `sms`) system rows — the double opt-in, the three auto-replies, and the payment-failed sample — via an Alembic data migration **and** `seed_platform.py`.
2. Replace the code constants in `tasks/sms_compliance_platform.py` and `api/routes/webhooks_sms.py` with a fail-loud DB loader (`services/platform_sms_templates.py`).
3. Wire the first real Account-Notifications sender: `invoice.payment_failed` → platform SMS to verified, opted-in owners.
4. Lock it all in with a verbatim-guardrail test.
5. **(v1.1 — FU3)** Fix the `/state` contract: `collected_data.sms_consent_status` derived from the owner's SMS `user_endpoint` — `"opted_in"` only when `verification_status == "verified"` (YES confirmed), `"pending"` when an SMS endpoint exists unverified, `null` when none. Never source it from `consent_status` (that flips at checkbox attestation, before YES).

---

## Pre-Work: Establish Regression Baseline

Before touching any file, capture the current **unit-only** test baseline:

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=no -q 2>&1 | tail -5
```

Record the exact count: **`X passed, Y failed`**.

> **If any tests are already failing before you start**: Do NOT treat them as "pre-existing" and proceed anyway. Either (a) confirm with Tom that this is a known, accepted failure with a documented reason, or (b) fix the failure before touching any batch files. You may NOT start implementation work while tests are in an unexplained failed state.

---

## Pre-Work: Run MCP Verification Queries

> **MCP Usage Rule**: The `postgres-local` MCP is for **read-only verification only**. Use it to confirm table names, column types, and existing data. Never use it to INSERT, UPDATE, or DELETE — all data changes go through the application code, seed scripts, or Alembic migrations. If a query fails or returns an error → STOP and ask Tom before proceeding.

Run **all** of these via `postgres-local` MCP before writing any code:

```sql
-- 1. Confirm zero pre-existing system sms templates (expect 0 rows)
SELECT notification_type_code, channel FROM public.notification_template
WHERE channel = 'sms' AND tenant_id IS NULL;

-- 2. Confirm none of the 5 new type codes exist (expect 0 rows)
SELECT code FROM public.notification_type
WHERE code IN ('platform_sms_double_optin','platform_sms_optin_reply','platform_sms_optout_reply',
               'platform_sms_help_reply','platform_payment_failed');

-- 3. Verify notification_template column shape (mandatory before writing any INSERT)
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'notification_template'
ORDER BY ordinal_position;

-- 4. Verify notification_type column shape + audience CHECK constraint
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'notification_type'
ORDER BY ordinal_position;

SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint
WHERE conrelid = 'public.notification_type'::regclass AND contype = 'c';

-- 5. Current alembic head
SELECT version_num FROM public.alembic_version;
```

> **Engineer safety net — independent column verification (MANDATORY)**: The Architect verified these tables on 2026-08-09, but the live DB is the only authoritative source. If any column name in this prompt or the design doc does not match what MCP returns → use the MCP-returned name and note the discrepancy in your Completion Summary.

---

## Pre-Work: Read These Source Files

Use `read_file` on each of these before writing any code:

```
backend/tasks/sms_compliance_platform.py        ← the double-opt-in task + _PLATFORM_DOUBLE_OPTIN_TEMPLATE constant being replaced
backend/api/routes/webhooks_sms.py              ← the three _PLATFORM_*_REPLY constants (lines ~53–70) + their send sites (~166, ~228, ~251); owner user_endpoint resolution
backend/services/notification_endpoints.py      ← get_owner_sms_endpoint(), hash_consent_text(), upsert_owner_sms_endpoint()
backend/services/stripe_subscriptions.py        ← handle_invoice_payment_failed (~line 343) — the TODO at ~line 371 is your wiring point
backend/services/template_renderer.py           ← render_template() signature (not needed for these static bodies, but confirm)
backend/services/sms_carrier.py                 ← get_sms_carrier() factory + SendResult shape
backend/migrations/scripts/seed_platform.py     ← notification_type + notification_template seed blocks (~lines 491–707) — you are extending this pattern
backend/tests/conftest.py                       ← available fixtures
backend/tests/domains/notifications_comms/test_signup_c_platform_sms.py  ← the SIGNUP-C tests you will need to update (they patch the constants)
backend/app/models/system.py                    ← NotificationTemplate / NotificationType SQLModel classes (confirm field names)
backend/db_models_map.md                        ← confirm model → table mappings
backend/README-seed-data.md                     ← §3 (Group A–D), §4 (Current Seed State), §6 (run order), §7 (DELETE safety)
```

Also run these greps to find every consumer of the constants being deleted:

```bash
grep -rn "_PLATFORM_DOUBLE_OPTIN_TEMPLATE\|_PLATFORM_OPTOUT_REPLY\|_PLATFORM_OPTIN_REPLY\|_PLATFORM_HELP_REPLY" backend/ --include="*.py" -l
grep -rn "handle_invoice_payment_failed" backend/ --include="*.py" -l
```

---

## Batch Context & Design Decisions (binding)

From the design doc (§E/§G) — do not re-litigate:

1. **Single content path**: `notification_template` (system rows, `tenant_id IS NULL`, `channel='sms'`, `locale='en'`) becomes the ONLY source for Pathway C SMS bodies. All four code constants are **deleted** — no fallback constants anywhere.
2. **Fail-loud loader**: a missing/inactive campaign-locked template raises `PlatformSmsTemplateMissingError` and sends nothing. A silent hardcoded fallback would recreate the two-path problem and defer error 806 discovery to production.
3. **Direct carrier send** (not `notification_outbox`): platform sends use `get_sms_carrier()` with `PILOT_PLATFORM_SMS_NUMBER` FROM — the worker's sms branch resolves tenant/sandbox FROM numbers and does per-user category preference gating, neither of which applies to Pathway C.
4. **Consent gate for account notifications**: send only to owner `user_endpoint` rows with `consent_status='opted_in'` AND `verification_status='verified'`. The compliance auto-replies (STOP/START/HELP) are carrier-mandatory and **never** gated.
5. **Out of scope** (do not build): Samples 3–4 senders (→ PLATFORM-SMS-B2), Sample 5 / Customer Care (→ SUPPORT-B1), tenant-editable overrides, any UI.

---

## Tasks

### Task 1 — Alembic data migration

Blank revision (never `--autogenerate`):

```bash
cd <repo>/backend && source .venv/Scripts/activate 2>/dev/null || source .venv/bin/activate
alembic revision -m "platform_sms_b1_pathway_c_templates"
```

`upgrade()`:
- `op.execute("SET LOCAL session_replication_role = 'replica';")` first.
- INSERT the 5 `notification_type` rows (design §B.1) — `audience='tenant'`, `is_active=true`, `tenant_id=NULL`, `ON CONFLICT (code) DO NOTHING`, explicit `created_at, updated_at = NOW(), NOW()`.
- INSERT the 5 `notification_template` rows (design §B.2) — `id = gen_random_uuid()`, `tenant_id=NULL`, `channel='sms'`, `locale='en'`, `subject=NULL`, `is_active=true`, guarded by `WHERE NOT EXISTS` on `(notification_type_code, channel, tenant_id IS NULL)` (no unique constraint on the natural key — check first).
- **Verbatim strings**: copy from design §B.2, but FIRST diff them character-for-character against the live constants in `webhooks_sms.py` / `sms_compliance_platform.py`. Code wins on any disagreement — note it in the Completion Summary.

`downgrade()`: DELETE exactly the 5 template rows + 5 type rows (scoped by the exact codes — value-scoped per the seed DELETE-safety rule).

Test the full cycle: `alembic upgrade head` → verify rows → `alembic downgrade -1` → verify gone → `alembic upgrade head`.

### Task 2 — `services/platform_sms_templates.py` (new)

Per design §F: `PlatformSmsTemplateMissingError` + `get_platform_sms_body(db, type_code) -> str`. Direct `select()` on `NotificationTemplate` where `notification_type_code == type_code`, `channel == 'sms'`, `tenant_id == None`, `is_active == True` (SQLModel `== None`, not `is None`). Raise on missing. Add a module docstring stating these rows are **campaign-locked** (editing requires a Telnyx portal resubmission — reference the campaign doc §6↔§8 rule).

### Task 3 — Refactor `tasks/sms_compliance_platform.py`

Replace `body = _PLATFORM_DOUBLE_OPTIN_TEMPLATE` with `body = get_platform_sms_body(db, "platform_sms_double_optin")` inside `_send_platform_double_optin_sms_impl` (the `db` session is already in scope). Delete the constant. `hash_consent_text(body)` and the audit-row flow are unchanged. Update the module docstring to reference the DB single-path.

### Task 4 — Refactor `api/routes/webhooks_sms.py`

At the three send sites (opt-in ~line 166, opt-out ~line 228, help ~line 251), load bodies via `get_platform_sms_body(db, "platform_sms_optin_reply" | "platform_sms_optout_reply" | "platform_sms_help_reply")`. Delete the three constants. `hash_consent_text(...)` calls use the loaded body. Keep the sync `def` handlers — no `async def`.

### Task 5 — `tasks/sms_platform_notifications.py` (new)

Per design §F: `_send_platform_account_notification_sms_impl(tenant_id, type_code)` + `@celery_app.task(name="send_platform_account_notification_sms", bind=True, max_retries=3, default_retry_delay=60)` wrapper. Two-layer pattern mirroring `sms_compliance_platform.py` (session created inside `_impl` via `Session(engine)`, str UUID params). Resolve ALL owner sms endpoints for the tenant (`user_endpoint` channel='sms', role owner — follow `get_owner_sms_endpoint`'s resolution approach and generalize it to all owners of the tenant; if the existing helper is single-user, add a sibling helper `get_verified_owner_sms_endpoints(db, tenant_id)` in `services/notification_endpoints.py`). Gates: `consent_status='opted_in'` + `verification_status='verified'`; FROM from `settings.PILOT_PLATFORM_SMS_NUMBER` (skip + error-log if unset); body via `get_platform_sms_body`. Structured logging per send. Return dict per design §F.

### Task 6 — Wire `handle_invoice_payment_failed`

In `services/stripe_subscriptions.py`, replace the `# TODO (Phase 2): Dispatch billing.payment_failed notification via notification_outbox` comment: after the existing paywall transition, enqueue `send_platform_account_notification_sms.delay(tenant_id=str(tenant.id), type_code="platform_payment_failed")`. Import inside the function (matching the existing lazy-import style in this codebase for tasks). Do not alter the paywall logic.

### Task 6a — (v1.1, SIGNUP-C-FU3) `sms_consent_status` in `/state`

In `backend/services/tenant_signup.py` `get_signup_state()`:

1. After loading `signup`/`tenant`, resolve the signup owner's SMS endpoint: `user_endpoint` where `channel='sms'` for the signup's owner user (owner = the `tenant_user` with the owner role for this tenant — follow the same resolution `notification_endpoints.get_owner_sms_endpoint()` uses; reuse that helper if its signature fits, else a scoped `select()`).
2. Add to the `collected_data` dict: `"sms_consent_status": "opted_in" if endpoint and endpoint.verification_status == "verified" else ("pending" if endpoint else None)`.
3. Update the `SignupStateResponse` schema (in `backend/api/schemas/` — find the signup schema file) so `collected_data` carries the new field.
4. **Regression test** in `tests/domains/identity_access/` (e.g. extend `test_signup_c_step3.py`): call the **real route** via the `client` fixture (no module-level `TestClient`) and assert the response JSON contains `collected_data.sms_consent_status` across the three states (no endpoint → `null`; endpoint pending → `"pending"`; endpoint verified → `"opted_in"`). This test exists specifically to prevent the MSW-mock divergence that hid this bug — it must exercise the real handler, not a mock.

### Task 6b — (v1.1, mandatory with Task 5) Register the new Celery module

**Hard rule (learned from the 2026-08-10 deploy failure on the pre-release AWS environment)**: a new `tasks/*.py` module is invisible to workers until it is added to the `imports=[...]` list in `backend/core/celery_app.py`. Add:

```python
"tasks.sms_platform_notifications",  # PLATFORM-SMS-B1: Pathway C account-notification SMS (event-driven, no Beat entry)
```

Without this, the API enqueues `send_platform_account_notification_sms` and every worker discards it as an unregistered task — silently. Verify after registration: `celery -A core.celery_app inspect registered` (or the worker boot `[tasks]` banner) lists the task name.

### Task 7 — Seed platform rollout

Extend `seed_platform.py`: the 5 `notification_type` rows + 5 entries in `notification_template_copy` keyed `("platform_...", "sms")` flowing through the existing update-or-insert loop. Verify with `python migrations/scripts/seed_platform.py --mode inspect` — the 5 new rows print. **Migration INSERT and seed INSERT must produce identical rows.**

### Task 8 — Tests

All under `backend/tests/domains/notifications_comms/`, `pytestmark = [pytest.mark.domain_notifications_comms, pytest.mark.unit]` (confirm the exact domain marker name in `pytest.ini` / README-adding-tests.md):

1. **`test_platform_sms_b1_verbatim_guardrail.py`** — holds the five campaign-doc strings as test constants; asserts (a) each seeded template body (inserted via the test fixture) equals the constant exactly, and (b) source scan: `tasks/sms_compliance_platform.py` and `api/routes/webhooks_sms.py` contain no remaining `Pilot for Trades:` SMS body literals / no `_PLATFORM_` constants (read the files and assert the constant names are absent).
2. **`test_platform_sms_b1_template_loader.py`** — loader returns the body for an active row; raises `PlatformSmsTemplateMissingError` for missing type code and for `is_active=false`; ignores tenant-scoped rows.
3. **Update `test_signup_c_platform_sms.py`** — it patches `_PLATFORM_DOUBLE_OPTIN_TEMPLATE`; refactor to insert the template rows via a shared `platform_sms_templates` fixture and assert against the loaded body. Same for any webhook tests referencing the deleted constants (find via the Task-grep).
4. **`test_platform_sms_b1_payment_failed_sender.py`** — `_impl` with mocked carrier: sends to verified+opted-in endpoints only (insert endpoint rows in mixed states: opted_out, unverified, verified — assert only verified receives); skips when `PILOT_PLATFORM_SMS_NUMBER` unset; `handle_invoice_payment_failed` enqueues the task (patch `.delay`).

Fixture: add a `platform_sms_templates` fixture (module-local or in `tests/domains/notifications_comms/conftest.py`) that INSERTs the 5 type + 5 template rows — the shared test DB is not guaranteed to carry them. Scope all assertions by inserted IDs/codes; never assert table counts.

### Task 9 — Docs

- `backend/README-seed-data.md` §4 (Current Seed State): add the 5 `notification_type` + 5 `notification_template` rows.
- **(v1.1) OpenAPI regeneration IS required** — Task 6a changes the `SignupStateResponse` schema. Run `python export_openapi_json.py`, commit `openapi.json`, and note in the Completion Summary that the next React session must run `pnpm sync-api-types` first.
- No `db_models_map.md` regeneration expected (no model changes — you are reading existing models only). If you touch a model file → run `python generate_db_model_map.py`.

---

## Seed Data Rollout (Core + Scenario)

Per `backend/README-seed-data.md` — read §3 (Group A–D model), §6 (run order), and §7 (DELETE safety rule) before editing any seed script.

### Layer 1 — Core / Platform values (Group B)
- The 5 `notification_type` + 5 `notification_template` rows go into **both** the Alembic migration (Task 1) and `seed_platform.py` (Task 7) — idempotent, producing **identical rows** in both paths (`seed_platform.py` is the post-schema-restore recovery path). Explicit `created_at, updated_at = NOW(), NOW()`.
- Update the script's `seed` and `inspect` modes (the template inspect block already selects all system rows — confirm the new rows appear).

### Layer 2 — Scenario data (Group D)
- N/A — system platform rows are not tenant-scoped; no scenario script changes.

### Verification
- `python migrations/scripts/seed_platform.py --mode inspect` (new rows present) + `pytest -m unit` after the seed change — fix any seed-resilience failures (assert-by-ID, never by count).

### README update
- Update `backend/README-seed-data.md` §4 (Current Seed State) with the new rows.

---

## Celery Task Structure

All Celery tasks MUST follow the two-layer pattern — business logic separated from the Celery entry point so the logic is unit-testable without a running worker. Test `_impl()` directly with the `db_session` fixture — never call `.delay()` or `.apply()` in unit tests. Reference: `backend/tasks/sms_compliance_platform.py` (the in-repo pattern for this exact domain, including its `Session(engine)` usage).

### Sync-by-Design (rules §21)

Every route/`_impl()`/service that touches the `Session` MUST be `def` (sync). This applies to the new loader, the new task, and the webhook refactor. Only use `async def` for handlers that exclusively `await` non-blocking I/O and never touch the `Session`. When in doubt → `def`.

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

CHANGED_PY=$(git diff --name-only --diff-filter=d HEAD -- '*.py' | sed 's|^backend/||')
if [ -n "$CHANGED_PY" ]; then
    ruff check --fix $CHANGED_PY
    ruff format $CHANGED_PY
    ruff check $CHANGED_PY
fi

# Full suite including integration tests
python -m pytest --tb=short -q 2>&1 | tail -10

# Batch-specific spot checks
python -m pytest tests/domains/notifications_comms/ -v 2>&1 | tail -25
python migrations/scripts/seed_platform.py --mode inspect 2>&1 | grep -A 8 "notification_template"
grep -rn "_PLATFORM_DOUBLE_OPTIN_TEMPLATE\|_PLATFORM_OPTOUT_REPLY\|_PLATFORM_OPTIN_REPLY\|_PLATFORM_HELP_REPLY" backend/ --include="*.py" || echo "CONSTANTS FULLY REMOVED ✅"

echo "=== PLATFORM-SMS-B1 FINAL VERIFICATION COMPLETE ==="
```

> **Warning-clean is part of done.** `ruff` must report no remaining issues **in your changed files**, and the pytest run must be free of `DeprecationWarning` noise. Do not run `ruff check .` against the entire codebase.
>
> **Any failure in either phase must be fixed before the batch is declared done.** There is no "pre-existing failure" exception without explicit written confirmation from Tom.

---

## Definition of Done

Update `pilot-launch-plan.md` per its maintenance protocol when complete (the Architect/Orchestrator owns the §2.0 flip; you own the Appendix C summary):

- [ ] Pre-modification regression baseline captured (`X passed, Y failed`) using `pytest -m unit`
- [ ] Zero pre-existing unit failures confirmed before starting work (or confirmed with Tom)
- [ ] All 5 MCP pre-work queries run — zero pre-existing sms system templates confirmed; `notification_template` + `notification_type` columns verified via `information_schema.columns` (rules §25)
- [ ] All mandatory source files read before writing any code
- [ ] Task 1: Alembic data migration created; full upgrade/downgrade/upgrade cycle verified
- [ ] Task 2: `services/platform_sms_templates.py` created (fail-loud loader, campaign-locked docstring)
- [ ] Task 3: double-opt-in task refactored; `_PLATFORM_DOUBLE_OPTIN_TEMPLATE` deleted
- [ ] Task 4: webhook auto-replies refactored; all three `_PLATFORM_*_REPLY` constants deleted
- [ ] Task 5: `tasks/sms_platform_notifications.py` created (two-layer, consent+verification gates)
- [ ] Task 6: `handle_invoice_payment_failed` wired to enqueue the task
- [ ] Task 6a (FU3): `sms_consent_status` in `/state` `collected_data`; schema updated; real-route regression test covers all three endpoint states
- [ ] Task 6b: `tasks.sms_platform_notifications` registered in `celery_app.py` imports; task visible in `inspect registered` / worker boot banner
- [ ] Task 7: `seed_platform.py` extended; `--mode inspect` shows the 5 new rows; migration/seed rows identical
- [ ] Task 8: verbatim-guardrail test + loader tests + payment-failed sender tests added; `test_signup_c_platform_sms.py` (and any other constant-referencing tests) updated
- [ ] Task 9: `README-seed-data.md` §4 updated
- [ ] All DB-touching code is sync `def` — no `async def` on the blocking `Session` (rules §21)
- [ ] All new test files use `pytestmark` with domain marker + `pytest.mark.unit`; no module-level `TestClient`; fixtures over hardcoded UUIDs; assertions scoped by inserted IDs
- [ ] The five template bodies match the campaign doc §6/§8 **verbatim** (or match the pre-existing code constants, with the discrepancy flagged)
- [ ] `python export_openapi_json.py` run + `openapi.json` committed (FU3 response-field addition); `pnpm sync-api-types` flagged for the next React session
- [ ] `ruff check --fix && ruff format` run **on changed files only** — zero remaining issues, no unjustified `# noqa` (rules §23)
- [ ] **Phase 1**: All unit tests pass (`pytest -m unit`) — zero failures
- [ ] **Phase 2**: Full test suite passes (`pytest`) — zero failures, warning-clean
- [ ] Final test count (before → after) documented
- [ ] Completion Summary appended to `pilot-launch-plan.md` Appendix C
- [ ] Campaign playbook `telnyx-10dlc-p4t-tenant-comms-campaign.md` §11 checklist: tick the "live templates match §6/§8" item if present, or note the batch closure in the doc's status line

---

## Completion Summary

After all Definition of Done items are complete:

1. Append a **Completion Summary** to `pilot-launch-plan.md` **Appendix C** (end of file) using the format below.
2. This batch does not close any task tracked in a non-launch-plan source spec except the `README-seed-data.md` §4 update (Task 9) — confirm §10 needs no flip.

```markdown
### PLATFORM-SMS-B1 — Pathway C Platform SMS Templates: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot Python Engineer
**Baseline**: X passed, Y failed
**Final**: X+N passed, Y failed (+N new tests)

#### What Was Accomplished
- [e.g., 5 campaign-locked Pathway C SMS strings moved from code constants into system notification_template rows — single DB content path]
- [e.g., fail-loud loader + verbatim-guardrail test installed (error-806 protection)]
- [e.g., invoice.payment_failed now enqueues platform SMS to verified opted-in owners]

#### Files Changed / Created
| File | Action |
|---|---|
| `backend/path/to/file.py` | Created / Updated — [what changed] |

#### Tests Added
| Test File | Domain | Tests | All Pass |
|---|---|---|---|
| `tests/domains/notifications_comms/test_....py` | `notifications_comms` | N | ✅ |
```
