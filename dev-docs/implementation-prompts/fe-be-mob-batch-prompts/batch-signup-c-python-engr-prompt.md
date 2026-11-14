# Implementation Prompt: SIGNUP-C — Signup Step 3 "Stay Informed" + Pathway C Platform SMS (Backend)

**Mode**: Pilot Python Engineer
**Batch**: SIGNUP-C (Backend half — runs FIRST)
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md`
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-signup-c-design.md` — read every section (A–I)
**Estimated session**: 4–5 hours
**Platform**: Backend only (`backend/`)
**Frontend companion**: SIGNUP-C React half (`batch-signup-c-react-engr-prompt.md`) — depends on this; run `pnpm sync-api-types` after this closes.

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-python-engineer/python-engineer-rules.md`** — full document; the 25 hard rules are non-negotiable STOPs
- **`dev-docs/architecture-design/pilot-python-engineer-methods.md`** — §13 (Alembic), §8 (Router Design), §5 (Model Design), §16 (Standard Task Workflow)
- **`backend/tests/README-adding-tests.md`** — full document; governs test structure, domain markers, fixtures
- **`dev-docs/architecture-design/batch-designs/batch-signup-c-design.md`** — the design; §B (migration), §D (endpoints), §F (canonical SMS strings — MUST match the Telnyx submission)
- **`dev-docs/integrations/telnyx/telnyx-10dlc-p4t-tenant-comms-campaign.md`** — §6/§8 are the exact strings your code MUST emit (Pathway C, Pilot-sender). ADR: `pilot-adr-log.md` ADR-0013
- **`dev-docs/pilot-operations.md`** §13.1 — the three-pathway SMS model. Pathway C = Pilot→owner, platform FROM number (NOT a tenant number).

Critical rules for this batch:

- **Rule 1 (verify, don't assume — §25)**: 186 tables exist. Query `information_schema.columns` for every table you touch this session before writing SQL. If MCP errors → **STOP and ask Tom**.
- **Rule 4 (blank migrations)**: `alembic revision -m "..."` only — never `--autogenerate`. Implement `downgrade()` exactly reversing `upgrade()`.
- **Rule 12 (sync-by-design — §21)**: every DB-touching route/`_impl()`/service is plain `def`. Never `async def` on the sync `Session`.
- **Rule 8 / RFC 7807**: all error responses use Problem Details dict shape (`{type,title,status,detail}`).
- **Rule 9 (audit context)**: every mutation endpoint calls `set_audit_context_sync(db, user_id=current_user.id)` before the first write.
- **Rule 15 (mixins — §24)**: `user_sms_consent_audit` inherits `AppendOnlyMixin` (mirrors `customer_sms_consent_audit`) + explicit `tenant_id`. **No hand-rolled timestamps. No DB triggers** (see §B — the mirror table has none).
- **§6↔§8 code-match rule (10DLC)**: the SMS strings your code emits MUST match the Telnyx-doc §6/§8 verbatim (design §F table). A mismatch = MNO review failure (error 806). Copy the strings from design §F exactly.

---

## Design Decisions (Do Not Re-Litigate — from design §G + ADR-0013)

| Decision | Outcome |
|---|---|
| Owner consent storage | **`user_endpoint`** (channel=`sms`) — NOT new `user` columns. Only new table is `user_sms_consent_audit`. |
| `notification_preference` sms rows | **NOT created** — `chk_notif_pref_channel` allows only push/email/in_app (MCP-verified). Send-time gates on `user_endpoint.consent_status`. |
| Consent checkbox | **Unchecked by default**; reply-YES double-opt-in is the authoritative consent. |
| Phone at step 3 | **Required** — `phone_skipped` path removed. |
| Platform FROM number | Pilot's ONE shared number from config/Secrets (`PILOT_PLATFORM_SMS_NUMBER` / `pilot/prod/telnyx`), NOT a `TenantPhoneNumber` row. |
| `user_sms_consent_audit` action vocab | Mirror `customer_sms_consent_audit`: `attested / double_opt_in_sent / double_opt_in_confirmed / opted_out`. |

---

## Pre-Work: Establish Regression Baseline

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=no -q 2>&1 | tail -5
```

Record the exact count: **`X passed, Y failed`**. If any tests are already failing → confirm with Tom or fix before starting. Do NOT proceed on an unexplained red baseline.

> **MCP Usage Rule**: `postgres-local` is read-only verification. Never INSERT/UPDATE/DELETE via MCP. If a query errors → STOP and ask Tom. (Do not use `postgres-prod` — this batch is not about prod state.)

## Pre-Work: Run MCP Verification Queries

Run all of these via `postgres-local` before writing code. The design was authored from these — reconfirm nothing changed:

```sql
-- 1. alembic head (design was written at 990231f963b0)
SELECT version_num FROM public.alembic_version;

-- 2. Confirm user_sms_consent_audit does NOT exist yet
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public' AND table_name = 'user_sms_consent_audit';

-- 3. Mirror source — customer_sms_consent_audit columns (your new table copies this shape)
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'customer_sms_consent_audit'
ORDER BY ordinal_position;

-- 4. Mirror source — its constraints (action CHECK values + FK ON DELETE)
SELECT conname, contype, pg_get_constraintdef(oid)
FROM pg_constraint WHERE conrelid = 'public.customer_sms_consent_audit'::regclass
ORDER BY contype, conname;

-- 5. Confirm the mirror source has NO triggers (yours must match — none)
SELECT tgname FROM pg_trigger
WHERE tgrelid = 'public.customer_sms_consent_audit'::regclass AND NOT tgisinternal;

-- 6. user_endpoint columns + CHECK constraints (sms channel + consent/verification vocab)
SELECT column_name, data_type, is_nullable FROM information_schema.columns
WHERE table_schema='public' AND table_name='user_endpoint' ORDER BY ordinal_position;
SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint
WHERE conrelid='public.user_endpoint'::regclass AND contype='c';

-- 7. Confirm user_endpoint has NO unique constraint on (user_id,channel,value)
--    (drives the value-scoped DELETE+INSERT idempotency pattern)
SELECT conname, contype, pg_get_constraintdef(oid) FROM pg_constraint
WHERE conrelid='public.user_endpoint'::regclass AND contype='u';

-- 8. tenant_signup columns (step3 branch reads/writes here)
SELECT column_name, data_type, is_nullable FROM information_schema.columns
WHERE table_schema='public' AND table_name='tenant_signup' ORDER BY ordinal_position;
```

**Expected**: #2 empty; #5 empty (no triggers); #7 empty (no unique constraint). If any differ → STOP and ask Tom.

## Pre-Work: Read These Source Files

Use `read_file` on each before writing code:

```
backend/app/models/crm.py                         ← CustomerSmsConsentAudit — the exact model to mirror (AppendOnlyMixin, action CHECK)
backend/app/models/mixins.py                      ← AppendOnlyMixin definition (created_at/created_by only, no updated_at)
backend/app/models/sms.py                         ← TenantPhoneNumber + any UserEndpoint model location
backend/tasks/sms_compliance.py                   ← the EXISTING tenant double-opt-in task you are parallel-building (Pathway B) — mirror structure, change FROM resolution
backend/api/routes/webhooks_sms.py                ← STOP/START/HELP/YES routing — you extend this to resolve user_endpoint targets
backend/api/routes/signup.py                      ← step3 route (advance_signup_step3) + SignupStepRequest schema
backend/services/tenant_signup.py                 ← advance_wizard_step + _process_step_data step3 branch (the phone_verified/skipped logic you replace)
backend/services/sms_carrier.py                   ← get_sms_carrier() — how FROM/TO are passed to send_message
backend/api/schemas/                              ← find the signup schema file; add request/response shapes here (NOT inline)
backend/migrations/versions/                      ← read the most recent migration for the blank-migration pattern
backend/tests/conftest.py                         ← fixtures (test_tenant, test_user, client, mock_cognito_jwt)
backend/db_models_map.md                          ← confirm model→table names
```

```bash
grep -rn "UserEndpoint\|user_endpoint" backend/app/models --include="*.py" -l
grep -rn "CustomerSmsConsentAudit" backend/app/models --include="*.py" -l
grep -rn "PILOT_PLATFORM_SMS_NUMBER\|telnyx" backend/core backend/services --include="*.py" -l
```

---

## Background / Context

The signup wizard step 3 (`/signup/phone`) currently records only `phone_verified`/`phone_skipped` booleans — its OTP endpoints were never built. This batch repurposes it into **"Stay Informed"**: collect the owner's mobile (required) + an unchecked-by-default consent box, and on consent send a **platform** double-opt-in text ("Reply YES") under Pilot's own 10DLC campaign (Pathway C). This is the first real SMS Pilot sends under its own brand. Consent lives on `user_endpoint`; an immutable `user_sms_consent_audit` trail is added for TCPA.

---

## Task 1 — Migration: `user_sms_consent_audit` table + SQLModel

**Model** (mirror `CustomerSmsConsentAudit` in `app/models/crm.py` — read it first; place the new model in the same file or the notifications model file, matching where `UserEndpoint` lives):

- Inherit **`AppendOnlyMixin`** (gives `created_at`, `created_by`) + explicit `tenant_id: uuid`.
- Columns per design §B: `id` (PK), `tenant_id`, `user_id` (FK user), `user_endpoint_id` (FK user_endpoint, nullable), `action` (text + CHECK), `consent_text_hash` (text), `ip_address` (text, nullable), `attested_at` (timestamptz).
- **action CHECK** — use the MCP-verified mirror vocabulary exactly: `attested`, `double_opt_in_sent`, `double_opt_in_confirmed`, `opted_out`.
- **FKs** all `ON DELETE RESTRICT` (matches the mirror table).
- **No triggers.** **No `updated_at`.** (MCP-verified the mirror table has none — do not add `immutable_guard`/`audit_log`/`updated_at_sync`.)

**Blank migration**:
```bash
alembic revision -m "signup_c_user_sms_consent_audit"
```
Write `op.create_table(...)` in `upgrade()` with the CHECK + FKs; `downgrade()` drops the table. Test the full cycle:
```bash
alembic upgrade head && alembic downgrade -1 && alembic upgrade head && alembic current
```

Then regenerate the model map + JSON schema:
```bash
python generate_db_model_map.py app > db_models_map.md
grep "UserSmsConsentAudit" backend/db_models_map.md
```
Update `dev-docs/db-design/pilot-db-schema-v2.6h.json` via `schema_manager.py` (path-based `set`/`array-append` — read `backend/README-schema_manager.md`; never edit the JSON directly).

Intermediate: `python -m pytest -m unit --tb=short -q | tail -5`

## Task 2 — `services/notification_endpoints.py`: `upsert_owner_sms_endpoint`

Add a service function (sync `def`) that writes/refreshes the owner's `sms` `user_endpoint` and the audit row. Because `user_endpoint` has **no unique constraint** on `(user_id,channel,value)` (MCP-verified #7), use the **value-scoped DELETE+INSERT** idempotency pattern (README-seed-data §7 analog): `DELETE FROM user_endpoint WHERE user_id=:uid AND channel='sms' AND value=:phone`, then INSERT.

Signature (design §F):
```python
def upsert_owner_sms_endpoint(db, *, user_id, tenant_id, phone, consent: bool, ip, disclosure_hash) -> UserEndpoint:
    # consent True  → consent_status='opted_in',  verification_status='pending'
    # consent False → consent_status='unknown',   verification_status='pending'
    # write user_sms_consent_audit(action='attested', consent_text_hash=disclosure_hash, ip_address=ip, attested_at=now)
```
Also mirror `user.phone_number = phone` (display copy). Sync `def`, tenant-scoped `select()` (never `db.get()`).

## Task 3 — `tasks/sms_compliance_platform.py`: platform double-opt-in Celery task

Mirror the two-layer pattern in `tasks/sms_compliance.py` (`_impl` + `@celery_app.task`), but resolve the **FROM** number from **config**, not `TenantPhoneNumber`:

```python
def _send_platform_double_optin_sms_impl(user_id: str, tenant_id: str) -> dict:
    # TO   = user_endpoint.value where user_id + channel='sms'
    # FROM = settings PILOT_PLATFORM_SMS_NUMBER (Secrets pilot/prod/telnyx) — read core config for the pattern
    # skip if consent_status != 'opted_in' OR already verified OR no sms endpoint
    # body = _PLATFORM_DOUBLE_OPTIN_TEMPLATE (design §F — verbatim)
    # on send: write user_sms_consent_audit(action='double_opt_in_sent')
```

`_PLATFORM_DOUBLE_OPTIN_TEMPLATE` — copy verbatim from design §F / Telnyx §8:
> `Pilot for Trades: Reply YES to get important account, billing & security alerts by text. Msg freq varies. Msg & data rates may apply. Reply HELP for help, STOP to cancel.`

Test `_impl` directly with `db_session` — never `.delay()` in unit tests. Mock the carrier `send_message`.

## Task 4 — Extend `api/routes/webhooks_sms.py` for `user_endpoint` targets

Today the inbound STOP/START/HELP/YES handler resolves against `customer`. Extend it to **also** resolve `user_endpoint` (channel=`sms`) by the inbound `from` number:
- **YES/START/UNSTOP** → set matching `user_endpoint.consent_status='opted_in'`, `verification_status='verified'`, `verified_at=now`, `consent_updated_at=now`; write `user_sms_consent_audit(action='double_opt_in_confirmed')`; reply with the §8 opt-in string.
- **STOP** (+ variants) → `consent_status='opted_out'`; write audit `action='opted_out'`; reply §8 opt-out string.
- **HELP/INFO** → reply §8 help string (no state change).

Keep the existing customer-resolution path intact — resolve owner `user_endpoint` as an **additional** match, not a replacement. Reply strings copy verbatim from design §F / Telnyx §8. This handler is signature-verified already — do not change verification.

## Task 5 — Rewrite step 3 (`signup.py` + `tenant_signup.py`) — phone required

- **Schema** (`api/schemas/[signup].py`): step3 request becomes `{ phone_number: str (required), sms_consent: bool, disclosure_hash: str }`. Remove `phone_verified`/`phone_skipped` from the step3 path. Add response shapes for the two new endpoints (§D).
- **`_process_step_data` step3 branch** (`services/tenant_signup.py`): replace the `phone_verified/phone_skipped` validation with: require `phone_number`; call `upsert_owner_sms_endpoint(...)`; if `sms_consent` is true, enqueue `send_platform_double_optin_sms.delay(user_id, tenant_id)`. Advance state as today.
- **New endpoints** (§D) in `signup.py`, JWT-gated `require_permission("tenant.signup.complete")`, `set_audit_context_sync` first, RFC 7807 errors, `Idempotency-Key` accepted:
  - `POST /{tenant_id}/phone/consent` → `{phone_number, sms_consent, disclosure_hash}` → upsert endpoint → `{user_endpoint_id, verification_status}`
  - `POST /{tenant_id}/phone/send-optin` → `{user_endpoint_id}` → enqueue platform double-opt-in → `{status:"sent"}` (429 on resend cooldown)
- Keep the existing `/{tenant_id}/step3/test` counterpart working with the new shape (test suite depends on it).

Sync `def` throughout. After endpoints change:
```bash
python export_openapi_json.py
grep -A 5 "phone/consent\|phone/send-optin" backend/openapi_schema_map.md
```

---

## Test Requirements

Per `backend/tests/README-adding-tests.md`. Domain folder: **`notifications_comms/`** (SMS/consent) for Tasks 2–4; **`identity_access/`** for the signup step3 changes.

- `pytestmark = [pytest.mark.domain_notifications_comms, pytest.mark.unit]` (and `domain_identity_access` for step3 tests).
- Use `client`, `test_tenant`, `test_user`, `mock_cognito_jwt` fixtures — no hardcoded UUIDs, no module-level `TestClient`.
- Scope assertions by inserted IDs — never total row counts (shared seed DB).
- Mock the SMS carrier (`send_message`) — never hit Telnyx.

Minimum coverage:
- Migration: `user_sms_consent_audit` insert accepts each valid `action`; rejects an invalid action (CHECK); append-only (no updated_at column).
- `upsert_owner_sms_endpoint`: consent=True → `opted_in/pending` + `attested` audit; consent=False → `unknown/pending`; re-call with same phone does not create a duplicate endpoint (value-scoped delete works); writes `user.phone_number`.
- Platform task `_impl`: opted_in → sends + writes `double_opt_in_sent`; not-opted-in → skipped; no sms endpoint → skipped. FROM = platform number (assert the carrier was called with the config number, not a tenant number).
- webhooks_sms: inbound YES from owner number → endpoint `opted_in/verified` + `double_opt_in_confirmed` audit; STOP → `opted_out` audit; customer path still works (regression).
- step3: missing `phone_number` → 422 (RFC 7807); consent=True enqueues the task (assert `.delay` called via mock); `/step3/test` works with the new shape.

---

## Final Verification

### Phase 1 — Unit only (during dev)
```bash
cd <repo>/backend && source .venv/bin/activate
python -m pytest -m unit --tb=short -q 2>&1 | tail -10
```

### Phase 2 — Lint + full suite (once, at end)
```bash
cd <repo>/backend && source .venv/bin/activate
ruff check . --fix && ruff format .
python -m pytest --tb=short -q 2>&1 | tail -10
python -m pytest tests/domains/notifications_comms/ tests/domains/identity_access/ -q 2>&1 | tail -20
grep -A 5 "phone/consent" backend/openapi_schema_map.md
echo "=== SIGNUP-C BACKEND FINAL VERIFICATION COMPLETE ==="
```

Any failure in either phase — including apparently pre-existing — must be fixed or confirmed with Tom before done.

---

## Definition of Done

- [ ] Regression baseline captured (`X passed, Y failed`) via `pytest -m unit`; zero unexplained pre-existing failures
- [ ] All 8 MCP pre-work queries run; #2/#5/#7 confirmed empty
- [ ] All mandatory source files read (incl. `api/schemas/` signup file + `CustomerSmsConsentAudit` model)
- [ ] `user_sms_consent_audit` migration created (blank), `AppendOnlyMixin`, action CHECK mirrors source, FKs ON DELETE RESTRICT, **no triggers**, no `updated_at`; upgrade/downgrade/upgrade cycle passes
- [ ] `upsert_owner_sms_endpoint` — value-scoped DELETE+INSERT (no unique constraint), sets consent/verification, writes `attested` audit, mirrors `user.phone_number`
- [ ] `tasks/sms_compliance_platform.py` — two-layer, FROM = platform config number, verbatim §F template, `double_opt_in_sent` audit
- [ ] `webhooks_sms.py` extended for `user_endpoint` YES/STOP/HELP; customer path regression-safe
- [ ] step3 rewritten — phone required, `phone_skipped` removed, consent enqueues platform task; `/step3/test` updated; 2 new endpoints (§D) with `set_audit_context_sync`, RFC 7807, `Idempotency-Key`
- [ ] All DB-touching routes/services are sync `def` (§21); Pydantic v2 only; `response_model` on new routes
- [ ] SMS strings emitted match Telnyx §6/§8 verbatim (§6↔§8 code-match)
- [ ] `generate_db_model_map.py app > db_models_map.md` run; `schema_manager.py` used for JSON (never hand-edited)
- [ ] `export_openapi_json.py` run — new endpoints in `openapi_schema_map.md`
- [ ] `ruff check . --fix && ruff format .` clean
- [ ] **Phase 1** unit green; **Phase 2** full suite green + warning-clean
- [ ] Final test count (before → after) documented
- [ ] Handoff: notify React Engineer to run `pnpm sync-api-types` (see below)
- [ ] Completion Summary added to the launch plan

## Handoff Instructions (to React Engineer)

After Phase 2 passes and OpenAPI is regenerated + committed:
1. `python export_openapi_json.py` is done and committed.
2. Notify the React Engineer that SIGNUP-C backend is live and their **first Pre-Work step** is `pnpm sync-api-types`.
3. The React batch consumes `POST /{tenant_id}/phone/consent`, `POST /{tenant_id}/phone/send-optin`, and the changed `PUT /{tenant_id}/step3` (phone required).

## Completion Summary

Add a **Completion Summary** to `pilot-launch-plan.md` using the standard format (Completed date, Mode, Baseline→Final counts, What Was Accomplished, Files Changed, Tests Added). Also update the design doc `batch-signup-c-design.md` execution-order §C backend rows to ✅.

## After This Task — Next Step

Frontend companion: `batch-signup-c-react-engr-prompt.md` — the "Stay Informed" screen. It is gated on this batch + the Tom-approved UI design spec.
