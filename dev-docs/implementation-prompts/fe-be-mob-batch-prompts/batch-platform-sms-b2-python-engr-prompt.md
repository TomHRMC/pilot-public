# Implementation Prompt: PLATFORM-SMS-B2 — Pathway C Platform SMS: Security-Alert (New-Device) + Maintenance Broadcast Senders

**Mode**: Pilot Python Engineer
**Batch**: PLATFORM-SMS-B2 (Part 1 of 2 — backend + Lambda source; runs FIRST)
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §2.4 PLATFORM-SMS-B2
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-platform-sms-b2-design.md` ✅ APPROVED 2026-08-16
**Estimated session**: 3–4 hours
**Platform**: Backend only (`backend/` — including `backend/lambda/` and `backend/scripts/`)
**Companion**: Part 2 is the DevOps deploy prompt (`batch-platform-sms-b2-devops-prompt.md`) — it packages and wires the Lambda you author here. **There is no frontend work and no OpenAPI handoff in this batch** (no endpoints change — design §D).

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-python-engineer/python-engineer-rules.md`** — full document; the 25 hard rules are non-negotiable STOPs
- **`dev-docs/architecture-design/pilot-python-engineer-methods.md`** — §13 (Alembic), §16 (Standard Task Workflow)
- **`backend/tests/README-adding-tests.md`** — full document; governs test file structure, domain markers, fixture rules
- **`dev-docs/integrations/telnyx/telnyx-10dlc-p4t-tenant-comms-campaign.md`** — §6: the verbatim Sample 3/4 strings this batch seeds (§6↔§8 code-match / error-806 rule)
- **The design doc** (linked above) — §B (migration SQL), §F (interfaces), §G (locked decisions). The SQL in this prompt is copied verbatim from the approved design.

Critical rules for this batch:

- **Rule 1 / Rule 16 (verify-before-write)**: Never guess column names, data types, or table names. The Architect MCP-verified every table on 2026-08-14/16, but you MUST independently re-run the Pre-Work MCP queries below before writing SQL. If MCP returns an error → **STOP and ask Tom**. If a column name in this prompt disagrees with MCP → use the MCP name and note the discrepancy in your Completion Summary.
- **Rule 4 (Alembic)**: Blank migration only (`alembic revision -m "..."`, never `--autogenerate`); raw `op.execute()` SQL; `SET LOCAL session_replication_role = 'replica';` at the top of `upgrade()`; `downgrade()` exactly reverses; test the full `upgrade → downgrade → upgrade` cycle.
- **Rule 5**: Never module-level `TestClient` — use the `client` fixture.
- **Rule 7 (MCP read-only)**: `postgres-local` MCP is verification only — never INSERT/UPDATE/DELETE through it.
- **Rule 11**: Any test failure — even apparently pre-existing — must be fixed or explicitly confirmed with Tom before declaring done.
- **Rule 12 (sync-by-design, rules §21)**: All DB-touching code is sync `def` — the CLI, the task `_impl`, and the Lambda handler included. Never `async def` around the blocking `Session`.
- **Rule 14 (Ruff)**: changed files only (`git diff --name-only --diff-filter=d HEAD -- '*.py' | sed 's|^backend/||'`), fix ALL errors in those files.
- **Campaign-verbatim rule (B1 §G-1/§G-2 — the error-806 rule)**: The two SMS bodies are **campaign-locked**. The only places the Sample 3 / Sample 4 strings may exist as literals are: the Alembic migration, `seed_platform.py`, and guardrail-test constants. **Never** hardcode a fallback body; **never** let a `Pilot for Trades:` literal appear in the task, CLI, or Lambda code — the guardrail test greps for exactly that.
- **⚠️ En-dash warning**: Sample 4's registered window string contains an **en-dash (U+2013)** in `2:00–3:00 AM ET`. Do not "normalize" it to a hyphen anywhere (migration, seed, test constants) — the guardrail asserts byte-equality and a hyphen would break the registered-campaign match.
- **Seed DELETE safety (Rule 11.1)**: `seed_platform.py` uses **update-or-insert only** for these rows — no DELETE anywhere in the `mode_seed` path.

---

## Pre-Work: Establish Regression Baseline

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=no -q 2>&1 | tail -5
```

Record the exact count: **`X passed, Y failed`**. If any tests are already failing before you start: do NOT proceed with unexplained failures — confirm with Tom or fix first.

---

## Pre-Work: Run MCP Verification Queries

Run **all** of these via `postgres-local` MCP before writing any code. If any query returns unexpected results → **STOP and ask Tom**.

> **MCP Usage Rule**: `postgres-local` is read-only verification. Never mutate data through it. On any error → STOP and ask Tom.

```sql
-- 1. Target table shapes (both tables the migration inserts into)
SELECT table_name, column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name IN ('notification_type', 'notification_template')
ORDER BY table_name, ordinal_position;

-- 2. Existing platform rows: expect 5 active platform_% types + 5 sms templates;
--    and ZERO rows for the two new codes
SELECT code, is_active FROM public.notification_type
WHERE code LIKE 'platform_%' ORDER BY code;
SELECT notification_type_code, channel, locale, is_active
FROM public.notification_template
WHERE notification_type_code LIKE 'platform_%'
ORDER BY notification_type_code;

-- 3. Identity join key for the Lambda: confirm `user.email` exists (citext)
--    and that there is NO cognito_sub column
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'user'
ORDER BY ordinal_position;

-- 4. Eligibility fan-out tables the CLI/task rely on
SELECT table_name, column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name IN ('tenant_user', 'user_endpoint')
ORDER BY table_name, ordinal_position;

-- 5. Current alembic head (record it; your new revision becomes the next head)
SELECT version_num FROM public.alembic_version;
```

---

## Pre-Work: Read These Source Files

Use `read_file` on each before writing any code:

```
dev-docs/architecture-design/batch-designs/batch-platform-sms-b2-design.md   ← THE design — §B SQL, §F interfaces, §G locked decisions
backend/tasks/sms_platform_notifications.py        ← the file Task 3 modifies (impl + wrapper, 244 lines)
backend/services/platform_sms_templates.py         ← fail-loud loader (get_platform_sms_body)
backend/services/template_renderer.py              ← render_template — Jinja2 with autoescape=True (design §G-5)
backend/services/notification_endpoints.py         ← get_verified_owner_sms_endpoints (~line 206) — eligibility fn reused by CLI
backend/migrations/scripts/seed_platform.py        ← platform SMS block (~lines 485–830): three structures to extend in Task 2
backend/lambda/post_confirmation/handler.py        ← Lambda pattern Task 5 mirrors (engine cache, _resolve_db_url, never-raise)
backend/scripts/stripe_bootstrap.py                ← CLI conventions (argparse, modes, logging) for Task 4
backend/tests/domains/notifications_comms/conftest.py             ← platform_sms_templates fixture (line ~95) — extend 5→7 pairs
backend/tests/domains/notifications_comms/test_platform_sms_b1_verbatim_guardrail.py   ← guardrail pattern for Task 6
backend/tests/domains/notifications_comms/test_platform_sms_b1_payment_failed_sender.py ← carrier-mock + verified-endpoint setup pattern
backend/tests/domains/identity_access/test_post_confirmation_router.py  ← Lambda importlib test pattern for Task 6
backend/tests/README-adding-tests.md               ← domain markers, fixture rules
backend/README-seed-data.md                        ← §3 (Group A–D), §6 (run order), §7 (DELETE safety)
```

Also:

- `list_files` on `backend/lambda/post_confirmation/` — mirror its package layout exactly (whether `__init__.py` files exist) for the new `backend/lambda/post_authentication/` directory.
- Confirm the exact domain marker names in `backend/pytest.ini` (`domain_notifications_comms`, `domain_identity_access`).

```bash
grep -rn "send_platform_account_notification_sms" backend/ --include="*.py" -l   # all callers — the stripe_subscriptions.py call site must keep working unchanged (template_context defaults to None)
grep -rn "platform_sms_templates" backend/tests --include="*.py" -l              # all consumers of the fixture you extend in Task 6
```

---

## Background / Context

**Pathway C** (ADR-0013): Pilot → tenant-owner platform SMS over the approved `CXXXXXX` Account-Notifications campaign, FROM the single platform number (`PILOT_PLATFORM_SMS_NUMBER`), sent directly via `get_sms_carrier()` (never `notification_outbox`), consent-gated only by `user_endpoint.consent_status='opted_in' AND verification_status='verified'` (TCPA double-opt-in — no preference gating; design §G-7).

PLATFORM-SMS-B1 ✅ shipped the substrate: the fail-loud loader (`get_platform_sms_body()`), the two-layer fan-out task (`send_platform_account_notification_sms`), the seed block, the conftest fixture, and the verbatim-guardrail test — all for the first 5 campaign strings. **This batch wires the remaining two approved samples** (design §0):

| Sample | Type code | Trigger | Body |
|---|---|---|---|
| 3 — new-device security alert | `platform_security_new_device` | Cognito **Post Authentication** Lambda (device tracking on; `newDeviceUsed` gate) → direct Redis enqueue | Fully static, stored verbatim |
| 4 — scheduled maintenance | `platform_maintenance_broadcast` | Operator-run CLI script → `.delay()` per eligible tenant with a `template_context` | Stored with `{{ maint_date }}` / `{{ maint_window }}` placeholders; renders to the registered string |

**Locked decisions (Tom-approved — do not re-litigate; design §G)**: device tracking = "Always remember" (not alert-on-every-login, not custom fingerprinting, not Cognito advanced security); Lambda enqueues directly to the Redis broker via a minimal Celery producer (documented contingency: event table + beat poller — NOT built); SMS-only (no parallel email); CLI trigger (no operator endpoint, no beat schedule); Sample 3 fans out to ALL verified+opted-in owner endpoints of the signing-in user's active tenant(s); no billing-status filtering anywhere.

**⚠️ Design refinement (Architect, 2026-08-16 — supersedes one line of design §F.3)**: Lambda environment variables are plain strings — they **cannot** use the ECS-style `${secret_arn}:json_key::` extraction. So the handler resolves the broker URL the same way it resolves the DB URL: env `CELERY_BROKER_URL` if set (local dev/tests), else fetch the `REDIS_SECRET_ARN` secret JSON from Secrets Manager at runtime and read its **`broker_url`** key (that key name is verified in `compute/main.tf` line 222 and the `database/main.tf` comment block). DevOps wires `REDIS_SECRET_ARN` in Part 2.

**Two-prompt batch**: you author the migration, seed parity, task extension, CLI, Lambda handler source, and all tests. DevOps (Part 2) builds/packages/deploys the Lambda and does the Cognito wiring — your handler must be merged and green before Part 2 runs.

---

## Task 1 — Alembic Data Migration (2 type rows + 2 template rows)

Create a **blank** migration:

```bash
cd <repo>/backend && source .venv/bin/activate
alembic revision -m "platform_sms_b2_security_maintenance_templates"
```

Implement `upgrade()` starting with `SET LOCAL session_replication_role = 'replica';`, then execute **this exact SQL** (verbatim from design §B.1/§B.2 — `WHERE NOT EXISTS` guards make it idempotent; this is the deliberate equivalent of `ON CONFLICT DO NOTHING`, used because `notification_template` has no unique constraint on its natural key and `tenant_id IS NULL` never conflict-matches):

```sql
INSERT INTO public.notification_type
    (code, tenant_id, audience, name, description, is_active,
     created_at, updated_at, created_by, updated_by)
SELECT v.code, NULL, 'tenant', v.name, v.description, true,
       now(), now(), NULL, NULL
FROM (VALUES
    ('platform_security_new_device',
     'Platform: New-Device Sign-In Alert',
     'Pathway C security alert to tenant owners when a successful sign-in occurs from a device Cognito has not remembered (Post-Authentication trigger, newDeviceUsed). Campaign CXXXXXX Sample 3.'),
    ('platform_maintenance_broadcast',
     'Platform: Scheduled Maintenance Broadcast',
     'Pathway C broadcast to all tenant owners announcing a scheduled platform maintenance window (operator-run CLI). Campaign CXXXXXX Sample 4.')
) AS v(code, name, description)
WHERE NOT EXISTS (
    SELECT 1 FROM public.notification_type t WHERE t.code = v.code
);

INSERT INTO public.notification_template
    (id, tenant_id, notification_type_code, channel, locale, subject, body, is_active,
     created_at, updated_at, created_by, updated_by)
SELECT gen_random_uuid(), NULL, 'platform_security_new_device', 'sms', 'en', NULL,
       'Pilot for Trades: New sign-in to your account from a new device. If this wasn''t you, secure your account now. Reply STOP to opt out.',
       true, now(), now(), NULL, NULL
WHERE NOT EXISTS (
    SELECT 1 FROM public.notification_template
    WHERE notification_type_code = 'platform_security_new_device'
      AND channel = 'sms' AND locale = 'en' AND tenant_id IS NULL
);

INSERT INTO public.notification_template
    (id, tenant_id, notification_type_code, channel, locale, subject, body, is_active,
     created_at, updated_at, created_by, updated_by)
SELECT gen_random_uuid(), NULL, 'platform_maintenance_broadcast', 'sms', 'en', NULL,
       'Pilot for Trades: Scheduled maintenance {{ maint_date }} from {{ maint_window }}. The app may be briefly unavailable. Reply STOP to opt out.',
       true, now(), now(), NULL, NULL
WHERE NOT EXISTS (
    SELECT 1 FROM public.notification_template
    WHERE notification_type_code = 'platform_maintenance_broadcast'
      AND channel = 'sms' AND locale = 'en' AND tenant_id IS NULL
);
```

`downgrade()` deletes exactly these rows:

```sql
DELETE FROM public.notification_template
WHERE notification_type_code IN ('platform_security_new_device', 'platform_maintenance_broadcast')
  AND channel = 'sms' AND tenant_id IS NULL;
DELETE FROM public.notification_type
WHERE code IN ('platform_security_new_device', 'platform_maintenance_broadcast')
  AND tenant_id IS NULL;
```

Test the full cycle:

```bash
alembic upgrade head && alembic downgrade -1 && alembic upgrade head && alembic current
```

Then MCP-verify the rows landed (read-only):

```sql
SELECT notification_type_code, channel, locale, is_active, body
FROM public.notification_template
WHERE notification_type_code IN ('platform_security_new_device', 'platform_maintenance_broadcast');
```

---

## Task 2 — Seed Parity (`seed_platform.py`) + README §4

Extend the existing platform-SMS block in `backend/migrations/scripts/seed_platform.py` (~lines 485–830) so the seed produces **rows identical to the migration** (the seed is the post-schema-restore recovery path):

1. `_platform_sms_notification_types` list (~line 491): add the two type dicts (same `code`/`name`/`description` as the migration; match the existing dicts' exact key set — read the block first).
2. `notification_template_copy` dict (~line 700): add `("platform_security_new_device", "sms")` and `("platform_maintenance_broadcast", "sms")` entries with `subject: None` and the **byte-identical** bodies from Task 1 (en-dash warning applies to any registered-value strings in tests; the stored maintenance body contains only `{{ maint_date }}` / `{{ maint_window }}` placeholders — no en-dash in the stored row).
3. `_platform_sms_type_codes` list (~line 816): add both codes.

The existing block's update-or-insert pattern (keyed `(notification_type_code, channel)` with `tenant_id IS NULL`) is reused as-is — **no DELETE anywhere** (Rule 11.1).

Verify idempotency — run twice; row counts unchanged on the second run:

```bash
python migrations/scripts/seed_platform.py --mode seed
python migrations/scripts/seed_platform.py --mode seed    # must be a no-op
python migrations/scripts/seed_platform.py --mode inspect # confirm the 7 platform pairs
```

**README update**: `backend/README-seed-data.md` §4 (Current Seed State) — add the two new `platform_%` type+template rows to the platform notification list.

---

## Task 3 — Additive `template_context` Param on the B1 Task

Modify `backend/tasks/sms_platform_notifications.py` — **the only existing-code change in this batch** (design §F.1):

```python
def _send_platform_account_notification_sms_impl(
    tenant_id: str,
    type_code: str,
    template_context: dict[str, str] | None = None,   # NEW — optional
) -> dict[str, Any]:
    # ... step 1 (FROM resolution) and step 2 (body = get_platform_sms_body(...)) unchanged ...
    # NEW: render only when a context is supplied; None preserves B1 behavior exactly.
    if template_context is not None:
        body = render_template(body, template_context)
    # ... steps 3–4 (endpoint fan-out, carrier sends, results) unchanged ...
```

- Add `from services.template_renderer import render_template` to the module's existing service imports.
- Wrapper: add the same optional parameter and pass it through — decorator (`name="send_platform_account_notification_sms"`, `bind=True`, `max_retries=3`, `default_retry_delay=60`) and retry semantics **unchanged**:

```python
def send_platform_account_notification_sms(
    self,
    tenant_id: str,
    type_code: str,
    template_context: dict[str, str] | None = None,   # NEW — optional
) -> dict[str, Any]:
```

- Update both docstrings (new param documented: string values only, Celery-serializable).
- The existing caller in `services/stripe_subscriptions.py` passes no context → zero change needed there; confirm via the grep from Pre-Work.

---

## Task 4 — Maintenance Broadcast CLI (new)

Create `backend/scripts/broadcast_maintenance_sms.py` (design §F.2; conventions from `stripe_bootstrap.py`; `backend/scripts/` is a package with `__init__.py`, so it runs as `python -m scripts.broadcast_maintenance_sms`):

```
Usage:
  python -m scripts.broadcast_maintenance_sms --date "Sun 08-02-2026" --window "2:00–3:00 AM ET"
      → DRY RUN (default): logs eligible-tenant count + per-tenant endpoint counts. Enqueues NOTHING.
  python -m scripts.broadcast_maintenance_sms --date ... --window ... --i-am-sure
      → enqueues send_platform_account_notification_sms per eligible tenant.
```

Required behavior:

- **argparse**: `--date` (required), `--window` (required), `--i-am-sure` (`store_true`).
- **Validation**: both values must match `re.compile(r"^[A-Za-z0-9: \-–]+$")` — alphanumerics, colon, space, hyphen, **en-dash U+2013** (design §G-5: keeps the Jinja `autoescape=True` render byte-identical and blocks `{`/`}` template injection). On failure: print a clear error, exit code 2.
- **Eligibility** (single source of truth = the same function the task uses):
  1. `SELECT DISTINCT tenant_id FROM tenant_user WHERE is_active = true` (via SQLModel `select` on the `TenantUser` model — sync `Session` over `core.db.engine`).
  2. For each, `get_verified_owner_sms_endpoints(db, tenant_id=tid)` ≥ 1 → eligible.
  3. **No billing/subscription filtering** (design §G-10).
- **Dry run (default)**: per eligible tenant, log `tenant_id` + endpoint count; final summary line: `DRY RUN — tenants_eligible=N endpoints=M (re-run with --i-am-sure to enqueue)`.
- **`--i-am-sure`**: per eligible tenant:

```python
send_platform_account_notification_sms.delay(
    tenant_id=str(tid),
    type_code="platform_maintenance_broadcast",
    template_context={"maint_date": args.date, "maint_window": args.window},
)
```

  then log a per-tenant enqueue line and a final summary (`tenants_eligible=N tasks_enqueued=N`).
- **Logging**: standard `logging` (INFO) — when DevOps/Tom runs this via `aws ecs execute-command` on the worker service, stdout lands in CloudWatch (design §F.2).
- **The file must contain no `Pilot for Trades:` literal** (guardrail grep target).
- Sync `def` throughout (Rule 12). Importing `tasks.sms_platform_notifications` pulls `core.celery_app` — expected and fine in the backend environment.

Manual smoke (local, against your dev DB — dry run only):

```bash
python -m scripts.broadcast_maintenance_sms --date "Sun 08-02-2026" --window "2:00–3:00 AM ET"
```

---

## Task 5 — Post-Authentication Lambda Handler (new)

Create `backend/lambda/post_authentication/handler.py`, mirroring `backend/lambda/post_confirmation/handler.py` structure and discipline (design §F.3). Mirror the post_confirmation directory's package layout exactly (check for `__init__.py` via your Pre-Work `list_files`).

Handler contract:

```python
def handler(event: dict, context) -> dict:
    """
    Cognito Post Authentication trigger (triggerSource "PostAuthentication_Authentication").
    Fires only after FULLY successful auth (incl. MFA) — never on failed logins,
    never on silent token refresh.

    Gate: alert only when event["request"]["newDeviceUsed"] is True — present only
    because device tracking = Always remember (DevOps Part 2 enables it).

    ⚠️ NEVER raises: any exception is logged and `event` is returned — an
    unhandled raise would fail the user's sign-in.
    """
```

Logic (all sync `def`; module-level `_engine` / `_producer` caches for warm starts):

1. `if event.get("request", {}).get("newDeviceUsed") is not True: return event` — the common path is one dict lookup.
2. `email = event["request"]["userAttributes"]["email"]` (missing/empty → log + return event).
3. `user = select(User).where(User.email == email, User.is_active.is_(True))` — `email` is citext (case-insensitive). No user → log + return event. (**Do not** look for a `cognito_sub` column — MCP-verified it does not exist; email is the join key, same as the post-confirmation handler.)
4. `tenant_ids = select(TenantUser.tenant_id).where(TenantUser.user_id == user.id, TenantUser.is_active.is_(True))` — enqueue once per active tenant (multi-tenant users fan out to each).
5. Per tenant:

```python
_get_producer().send_task(
    "send_platform_account_notification_sms",
    kwargs={
        "tenant_id": str(tid),
        "type_code": "platform_security_new_device",
    },
)
```

   No `template_context` — Sample 3 is static. No explicit queue — the worker consumes the default `celery` queue (design §G-6).
6. `return event`.

Resource resolution (mirror the post-confirmation patterns):

- `_resolve_db_url()` — copy the pattern verbatim: env `DATABASE_URL` → else `DB_SECRET_ARN` via Secrets Manager (boto3 imported lazily inside the function; pre-bundled in the Lambda runtime), JSON `url` field. Never log the URL.
- `_resolve_broker_url()` — **same pattern, new** (design refinement note in Background): env `CELERY_BROKER_URL` → else `REDIS_SECRET_ARN` via Secrets Manager, JSON **`broker_url`** field. Never log the URL.
- `_get_producer()` — lazy minimal `Celery("pilot_lambda_producer", broker=_resolve_broker_url())`. **Do NOT import `core.celery_app`** (drags FastAPI/config into the Lambda package).
- ORM imports only: `User` from `app.models.core`, `TenantUser` from `app.models.auth` (same as post-confirmation — no FastAPI/route/service imports).
- Everything after the gate wrapped so any exception → `logger.exception(...)` + `return event`.
- Module docstring: design link + ADR-0013 + the never-raise discipline + packaging note (deps: `psycopg2-binary`, `sqlalchemy`, `sqlmodel`, `celery`; boto3 NOT packaged).

---

## Task 6 — Tests

Per `backend/tests/README-adding-tests.md`. Confirm exact marker names in `pytest.ini`. Mirror the B1 files' fixture/carrier-mock patterns (read them in Pre-Work). Test the `_impl`/functions directly — never `.delay()`/`.apply()` in unit tests (mock/monkeypatch the delay boundary instead).

### 6.1 — Extend the shared fixture (5 → 7 pairs)

`backend/tests/domains/notifications_comms/conftest.py` `platform_sms_templates` fixture (~line 95): add the two new type+template pairs with the **byte-identical** bodies from Task 1. Existing consumers key by code, so extension is non-breaking — but run the B1 files after the change to prove it.

### 6.2 — `test_platform_sms_b2_verbatim_guardrail.py` (new, `domain_notifications_comms`)

1. **Sample 3 verbatim**: `get_platform_sms_body(db_session, "platform_security_new_device")` == the registered constant byte-for-byte:
   `Pilot for Trades: New sign-in to your account from a new device. If this wasn't you, secure your account now. Reply STOP to opt out.`
2. **Sample 4 render-verbatim (the 806-safety assertion)**: `render_template(get_platform_sms_body(db_session, "platform_maintenance_broadcast"), {"maint_date": "Sun 08-02-2026", "maint_window": "2:00–3:00 AM ET"})` == the registered Sample 4 constant byte-for-byte (en-dash U+2013 in the constant — do not substitute a hyphen):
   `Pilot for Trades: Scheduled maintenance Sun 08-02-2026 from 2:00–3:00 AM ET. The app may be briefly unavailable. Reply STOP to opt out.`
3. **Grep assertions** (mirror the B1 guardrail's file-scan approach): no `Pilot for Trades:` literal in `scripts/broadcast_maintenance_sms.py`, `lambda/post_authentication/handler.py`, or `tasks/sms_platform_notifications.py`.

### 6.3 — `test_platform_sms_b2_template_context.py` (new, `domain_notifications_comms`)

Call `_send_platform_account_notification_sms_impl` directly with the B1 carrier-mock pattern + verified-endpoint setup:

1. `template_context=None` on `platform_security_new_device` → carrier receives the raw stored body (B1 regression).
2. `template_context={"maint_date": ..., "maint_window": ...}` on `platform_maintenance_broadcast` → carrier receives the rendered body; assert the provided values appear and no `{{` remains.
3. Registered-values integration: context = the registered values → carrier body == registered Sample 4 constant.

### 6.4 — `test_platform_sms_b2_broadcast_cli.py` (new, `domain_notifications_comms`)

Monkeypatch `send_platform_account_notification_sms.delay`; use `test_tenant`/`test_user` + the B1 verified-endpoint setup:

1. Validation rejects: `&`, `<`, `{`, empty string → exit 2, zero delay calls. (Also assert a valid en-dash window passes validation.)
2. Dry run (no `--i-am-sure`): zero delay calls; summary logs the eligible count.
3. `--i-am-sure`: one delay call per eligible tenant with exact kwargs `tenant_id`/`type_code="platform_maintenance_broadcast"`/`template_context={"maint_date", "maint_window"}`.
4. A tenant with no verified+opted-in owner endpoints is excluded (seed a second tenant or strip consent — scope assertions by inserted IDs, never counts).

### 6.5 — `tests/domains/identity_access/test_post_authentication_handler.py` (new, `domain_identity_access`)

Mirror `test_post_confirmation_router.py`'s `importlib.import_module("lambda.post_authentication.handler")` pattern and its approach to pointing the module engine at the test DB. Monkeypatch the producer (`_get_producer`) with a capturing fake. Cases:

1. `newDeviceUsed=True`, user with **two** active tenant_user rows → two `send_task` calls, correct task name + kwargs; returns the event.
2. `newDeviceUsed=False` → zero calls; returns event.
3. `newDeviceUsed` absent → zero calls; returns event.
4. Email not present in `user` table → zero calls; returns event (no raise).
5. Producer `send_task` raises → handler still returns event (never-raise discipline).
6. `userAttributes` missing `email` → zero calls; returns event.

---

## Regeneration Steps (this batch)

- **Run**: `python generate_app_import_map.py tests > app_model_imports.md` (new test files added — required).
- **Do NOT run** `export_openapi_json.py` (no endpoints change — design §D), `generate_db_model_map.py` (no model changes), or `schema_manager.py` (no schema change — data-only migration). DoD items for these are marked N/A deliberately.

---

## Final Verification

### Phase 1 — Unit Tests Only (run after each task group)

```bash
cd <repo>/backend && source .venv/bin/activate
python -m pytest -m unit --tb=short -q 2>&1 | tail -10
```

All unit tests must pass before moving on — fix any failure, including apparently-out-of-scope ones.

### Phase 2 — Lint (changed files only) + Full Suite (once, at the end)

```bash
cd <repo>/backend && source .venv/bin/activate

CHANGED_PY=$(git diff --name-only --diff-filter=d HEAD -- '*.py' | sed 's|^backend/||')
if [ -n "$CHANGED_PY" ]; then
    ruff check --fix $CHANGED_PY
    ruff format $CHANGED_PY
    ruff check $CHANGED_PY
fi

python -m pytest --tb=short -q 2>&1 | tail -10

# Batch-specific spot checks
python -m pytest tests/domains/notifications_comms/ -v 2>&1 | tail -30
python -m pytest tests/domains/identity_access/test_post_authentication_handler.py -v 2>&1 | tail -15
alembic current
python migrations/scripts/seed_platform.py --mode inspect

echo "=== PLATFORM-SMS-B2 PART 1 FINAL VERIFICATION COMPLETE ==="
```

Warning-clean is part of done (no Pydantic v1 / deprecation noise). Any failure in either phase must be fixed before declaring done — no "pre-existing" exception without Tom's written confirmation.

---

## Definition of Done

- [ ] Regression baseline captured (`X passed, Y failed` via `pytest -m unit`); zero unexplained pre-existing failures
- [ ] All 5 MCP pre-work queries run — table shapes confirmed; 5 existing `platform_%` pairs active; both new codes absent; `user.email` citext + no `cognito_sub`; alembic head recorded
- [ ] All mandatory source files read (incl. design doc, playbook §6, conftest, both B1 test files, post-confirmation handler + its test)
- [ ] Task 1: blank migration with verbatim design SQL + `SET LOCAL session_replication_role='replica'` + exact-reverse downgrade; full `upgrade → downgrade → upgrade` cycle passes; rows MCP-verified
- [ ] Task 2: `seed_platform.py` three structures extended (identical rows); seed run twice (second run no-op); `--mode inspect` shows 7 platform pairs; `README-seed-data.md` §4 updated
- [ ] Task 3: `template_context` added to impl + wrapper; renders only when not None; decorator/retry unchanged; `stripe_subscriptions.py` caller untouched and working
- [ ] Task 4: CLI validates allowlist (exit 2 on rejection), dry-run enqueues nothing, `--i-am-sure` enqueues per eligible tenant with exact kwargs; no `Pilot for Trades:` literal in the file; local dry-run smoke executed
- [ ] Task 5: handler gates on `newDeviceUsed is True`, joins by email, fans out per active tenant, never raises; `_resolve_broker_url()` mirrors `_resolve_db_url()` (env → `REDIS_SECRET_ARN` → `broker_url` key); minimal producer; ORM-only imports; package layout mirrors `post_confirmation/`
- [ ] Task 6: fixture extended 5→7; all 5 new/updated test groups green; B1 guardrail + loader + sender files still green after fixture extension
- [ ] All new test files use `pytestmark` with the correct domain marker + `pytest.mark.unit`; `client`/`db_session` fixtures only; `test_tenant`/`test_user` fixtures (no hardcoded UUIDs); assertions scoped by inserted IDs
- [ ] Sync `def` everywhere DB is touched (CLI, task impl, Lambda handler) — no `async def` (rules §21)
- [ ] Pydantic v2 idioms only where schemas are touched (none expected this batch)
- [ ] `python generate_app_import_map.py tests > app_model_imports.md` run (stdout redirect + dir arg)
- [ ] N/A confirmed: `export_openapi_json.py` (no endpoints), `generate_db_model_map.py` (no models), `schema_manager.py` (no schema change)
- [ ] Ruff gate on changed files only — zero remaining issues, no unjustified `# noqa`
- [ ] **Phase 1**: all unit tests pass
- [ ] **Phase 2**: full suite passes, warning-clean
- [ ] Final test count (before → after) documented
- [ ] Completion Summary added (format below) + playbook §6 note updated

---

## Completion Summary

After all DoD items are complete:

1. Add a **Completion Summary** to `pilot-launch-plan.md` Appendix C titled `### PLATFORM-SMS-B2 (Part 1) — Security-Alert + Maintenance Senders (Backend + Lambda): Completion Summary` using the standard format (Completed / Mode / Baseline / Final / What Was Accomplished / Files Changed / Tests Added tables).
2. Update `telnyx-10dlc-p4t-tenant-comms-campaign.md` §6 — add a note that Samples 3 & 4 are now live in code (type codes `platform_security_new_device` / `platform_maintenance_broadcast`; Sample 4 stored parameterized, guardrail renders the registered values verbatim — §6↔§8 code-match satisfied); Sample 5 remains with SUPPORT-B1.
3. The launch plan §2.4 card flip is the Architect's job — note in your summary that Part 1 is complete and Part 2 (DevOps) is next.

---

## After This Task — Next Step

Hand off to **Part 2 — DevOps** (`batch-platform-sms-b2-devops-prompt.md`): it packages `backend/lambda/post_authentication/handler.py` (build script), adds the Terraform resources (Lambda + permission + CloudWatch log group + Redis SG ingress + IAM secrets-policy widening), and does the manual Cognito wiring (device tracking = Always remember; `update-user-pool --lambda-config` with **both** triggers — the whole-block overwrite warning). Part 2 cannot run until this part is merged and green.

**No frontend handoff** — there are no endpoint changes; do not run `export_openapi_json.py` or `pnpm sync-api-types`.
