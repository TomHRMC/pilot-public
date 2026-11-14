# Implementation Prompt: SIGNUP-GA-1 — Post-Confirmation Lambda Router + Self-Serve Signup Backend

**Mode**: Pilot Python Engineer
**Batch**: SIGNUP-GA-1 (backend half)
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §2.3 row 14a
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-signup-ga-1-design.md` (v2.0)
**ADRs**: `ADR-0011` (self-sign-up → Lambda 3-path router) + `ADR-0012` (drop tenant-name uniqueness) — both **Accepted**
**Estimated session**: 4–5 hours
**Platform**: Backend only (`backend/`)
**DevOps companion**: `batch-signup-ga-1-devops-prompt.md` — DevOps **packages and deploys** the Lambda handler you author here, flips the Cognito pool to self-sign-up, and wires the trigger. **You author the handler code; DevOps owns packaging/IAM/VPC/deploy.** Hand off when your code + migration land.

> **Sequencing**: You run **first**. DevOps cannot package/deploy the Lambda until the handler module exists in the repo. End with the Handoff Instructions section (bottom) so DevOps knows the package is ready.

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-python-engineer/python-engineer-rules.md`** — full document; the 25 hard rules are non-negotiable STOPs
- **`dev-docs/architecture-design/pilot-python-engineer-methods.md`** — §13 (Alembic), §8 (Router Design), §5 (Model Design), §16 (Standard Task Workflow)
- **`backend/tests/README-adding-tests.md`** — full document; governs all test file structure, domain markers, and fixture rules
- **`dev-docs/architecture-design/batch-designs/batch-signup-ga-1-design.md`** — §A.2 (the 4 user types → 3 Lambda paths) and §F (module interfaces) are the spec you implement

### Critical rules for this batch

- **Rule 1 (verify, don't guess)**: Never guess column/table names. Use `postgres-local` MCP to verify every name before use. If MCP errors → **STOP and ask Tom**.
- **Rule 16 (186 tables)**: Query `information_schema.columns` for every table you touch this session before writing SQL. The column lists in this prompt are derived from a prior MCP session — re-verify; if any differ, use the MCP-returned name and note it in the Completion Summary.
- **Rule 4 (blank migrations)**: The migration MUST be a blank migration (`alembic revision -m "..."`), never `--autogenerate`. Implement `downgrade()` exactly reversing `upgrade()`.
- **Rule 12 / §21 (sync-by-design)**: `initiate_signup()` and all route `_impl()`s touch the sync `Session` → they stay plain `def`. Never `async def` a `Session`-touching function.
- **Rule 6 / ADR-0005 (tenant-scoped select)**: `db.get()` is banned. All lookups use `select().where(...)`. Return **404 not 403** on tenant-scoped misses.
- **Rule 8 / RFC 7807**: All error responses use Problem Details dict shape. Reuse the existing `signup-state-conflict` 409 shape already in `tenant_signup.py`.
- **Rule 9 (audit context)**: Any authenticated mutation endpoint calls `set_audit_context_sync(db, user_id=...)` before the first write. (The Lambda handler and the public step-1 path have no authenticated user — see the Lambda audit note in Task 2.)
- **Rule 11 (no "not my fault" failures)**: If ANY test fails during your work — even one that looks pre-existing — fix it before declaring done, or STOP and ask Tom.

### ⚠️ Batch-specific landmine — the Lambda MUST NEVER raise

The Post-Confirmation Lambda runs inside Cognito's confirmation flow. **An unhandled exception makes Cognito treat the confirmation as failed and can strand the user in an unconfirmed/limbo state.** Every path in the handler must be wrapped so that any error is logged and swallowed (return `event`), never propagated. This is why ADR-0012 drops the tenant-name unique constraint — so the placeholder-name insert cannot raise a unique violation. Do not reintroduce any `SELECT`-then-fail branch in the Lambda.

---

## Background / Context

**What exists today** (verified):
- The wizard state machine `services/tenant_signup.py` creates a `Tenant` + `TenantSignup(step1_account)` but **drops** the `owner_email`/name args (`initiate_signup()` returns `owner_email` but never persists it).
- `api/routes/auth.py::_signup_impl` is the **dev/test stand-in** for the prod Lambda: it creates `User` + `UserEndpoint(email)` + `TenantUser(owner)` + role/status. It also has a `Tenant.name` uniqueness pre-check (`auth.py`) that **must be removed** (ADR-0012).
- **The real Post-Confirmation Lambda has never been implemented.** `backend/lambda/` does not exist; the Terraform function is a placeholder stub. **You are writing this handler from scratch.**
- Cognito↔RDS join is **email only** — MCP-confirmed the `user` table has no `cognito_sub` column. Do not add one.

**What this batch does** (design §A.2): implement the Post-Confirmation Lambda as a **3-path router** (keyed on `email`), make wizard step 1 **resolve-or-attach by email**, persist `owner_email`, drop the tenant-name unique constraint, and reconcile the two signup backends (G6). Only the **type-(iii)** self-serve owner surface is exercised now; the router's Path 1/Path 2 are built to protect types (i)/(ii)/(iv) whose UIs are follow-on batches.

**The 4 user types → 3 Lambda paths** (design §A.2 — memorize this):

| Path | Condition (by `email`) | Action |
|---|---|---|
| **Path 1 — no-op** | a `user` row already exists | do nothing (platform users i/ii; or a re-fired confirmation). Idempotent. |
| **Path 2 — attach** | a pending `tenant_user_invite` (`accepted_at IS NULL`, `is_active`, not expired) exists | create `user`, attach `tenant_user` to `invite.tenant_id` (`joined_at=now`), set `invite.accepted_at` (type iv). No tenant. |
| **Path 3 — create** | neither of the above | create `tenant`(placeholder name) + owner `user` + `tenant_user(owner, joined_at=now)` + role/status (type iii). |

---

## Pre-Work: Establish Regression Baseline

Before touching any file, capture the current **unit-only** test baseline:

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=no -q 2>&1 | tail -5
```

Record the exact count: **`X passed, Y failed`**.

> If any tests are already failing before you start: do NOT treat them as "pre-existing" and proceed. Either confirm with Tom it's a known accepted failure, or fix it first. You may not start while tests are in an unexplained failed state.

---

## Pre-Work: Run MCP Verification Queries

> **MCP Usage Rule**: `postgres-local` is **read-only verification only**. Never INSERT/UPDATE/DELETE through it. If a query errors → STOP and ask Tom.

Run **all** of these before writing any code:

```sql
-- 1. Confirm the tenant-name UNIQUE index exists + its exact name (before dropping it)
SELECT indexname, indexdef FROM pg_indexes
WHERE schemaname='public' AND tablename='tenant' AND indexdef ILIKE '%UNIQUE%';
-- expect: tenant_name_key = CREATE UNIQUE INDEX tenant_name_key ON public.tenant USING btree (name)

-- 2. Confirm NO FK targets tenant.name (safe to drop) — expect zero rows referencing (name)
SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint
WHERE confrelid = 'public.tenant'::regclass;

-- 3. tenant_signup shape — confirm no id PK, keyed by tenant_id, NO owner_email yet
SELECT column_name, data_type, is_nullable, column_default FROM information_schema.columns
WHERE table_schema='public' AND table_name='tenant_signup' ORDER BY ordinal_position;

-- 4. user has NO cognito_sub (email is the only join) — expect EMPTY
SELECT column_name FROM information_schema.columns
WHERE table_schema='public' AND table_name='user'
  AND (column_name ILIKE '%cognito%' OR column_name ILIKE '%sub%');

-- 5. user discriminator columns for the router (is_platform_user, platform_role_code)
SELECT column_name, data_type, is_nullable FROM information_schema.columns
WHERE table_schema='public' AND table_name='user'
  AND column_name IN ('id','email','first_name','last_name','is_platform_user','platform_role_code','email_verified_at')
ORDER BY ordinal_position;

-- 6. tenant_user_invite shape (Path 2) — email, token_hash, expires_at, accepted_at, is_active, tenant_id
SELECT column_name, data_type, is_nullable FROM information_schema.columns
WHERE table_schema='public' AND table_name='tenant_user_invite' ORDER BY ordinal_position;

-- 7. tenant_user shape (invited_at / joined_at / role_code / status_id)
SELECT column_name, data_type, is_nullable FROM information_schema.columns
WHERE table_schema='public' AND table_name='tenant_user' ORDER BY ordinal_position;

-- 8. current alembic head (for the migration down_revision)
SELECT version_num FROM public.alembic_version;
```

If query 1 does not return `tenant_name_key`, or query 4 returns any row → **STOP and ask Tom** (the design assumptions are invalidated).

---

## Pre-Work: Read These Source Files

Use `read_file` on each before writing any code:

```
backend/services/tenant_signup.py            ← the function you're changing (initiate_signup + state machine)
backend/api/routes/auth.py                   ← _signup_impl: the dev/test Lambda stand-in you'll mirror + de-dupe (G6)
backend/api/routes/signup.py                 ← the wizard router that calls initiate_signup (public step 1)
backend/app/models/core.py                   ← Tenant, User, UserEndpoint models
backend/app/models/auth.py                   ← TenantUser, TenantUserRole, TenantUserStatus
backend/app/models/signup.py                 ← TenantSignup model (add owner_email fields here)
backend/api/schemas/signup.py                ← Pydantic request/response for /signup (if it exists; else note it)
backend/migrations/versions/<latest>.py      ← most recent migration = pattern reference + down_revision
backend/tests/conftest.py                    ← available fixtures (test_tenant, mock_cognito_jwt, tenant_a/b, etc.)
backend/db_models_map.md                     ← confirm model→table names
backend/tests/README-adding-tests.md         ← test structure (identity_access domain)
```

Also grep for related usages:

```bash
grep -rn "initiate_signup\|_signup_impl\|TenantSignup\|tenant_user_invite\|TenantUserInvite" backend/ --include="*.py" -l
grep -rn "Tenant with this name already exists" backend/ --include="*.py"
```

> **`api/schemas/` vs `app/models/`**: `app/models/` are SQLModel ORM classes; `api/schemas/` are Pydantic request/response shapes. Adding `owner_email` to `TenantSignup` requires the model change; any change to what `/signup` returns requires the schema change too.

---

## Task 1 — Migration: drop `tenant_name_key` + add `tenant_signup.owner_email` (+names)

Create ONE blank migration (design §B):

```bash
cd <repo>/backend && source .venv/bin/activate
alembic revision -m "signup_ga1_drop_tenant_name_unique_add_owner_email"
```

`upgrade()`:
```python
def upgrade() -> None:
    # ADR-0012 — tenant.name is display-only; nothing FKs off it. Drop global uniqueness.
    op.drop_constraint("tenant_name_key", "tenant", type_="unique")

    # Persist owner identity on the signup record (previously dropped by initiate_signup)
    op.add_column("tenant_signup", sa.Column("owner_email", sa.Text(), nullable=True))
    op.add_column("tenant_signup", sa.Column("owner_first_name", sa.Text(), nullable=True))
    op.add_column("tenant_signup", sa.Column("owner_last_name", sa.Text(), nullable=True))
```

`downgrade()` (exact reverse — note the one-way-door caveat in a comment):
```python
def downgrade() -> None:
    op.drop_column("tenant_signup", "owner_last_name")
    op.drop_column("tenant_signup", "owner_first_name")
    op.drop_column("tenant_signup", "owner_email")
    # NOTE: re-adding uniqueness will FAIL if duplicate tenant names now exist (accepted, ADR-0012).
    op.create_unique_constraint("tenant_name_key", "tenant", ["name"])
```

> Verify `tenant_name_key` is a UNIQUE **constraint** vs a bare unique **index** from MCP query 1. If `pg_constraint` (MCP query 2 area) shows it as a constraint, `op.drop_constraint(..., type_="unique")` is correct. If it is only an index (no matching `pg_constraint` row), use `op.drop_index("tenant_name_key", table_name="tenant")` and `op.create_index("tenant_name_key", "tenant", ["name"], unique=True)` in downgrade instead. **Use whichever MCP proves.**

Add the `owner_email` / `owner_first_name` / `owner_last_name` fields to the `TenantSignup` SQLModel in `app/models/signup.py` as `str | None = None`.

Test the full cycle:
```bash
alembic upgrade head && alembic downgrade -1 && alembic upgrade head && alembic current
```

Run intermediate unit check: `python -m pytest -m unit --tb=short -q | tail -5`

---

## Task 2 — Author the Post-Confirmation Lambda handler (3-path router)

Create a **new** module — this directory does not exist yet:

```
backend/lambda/post_confirmation/handler.py
backend/lambda/post_confirmation/__init__.py
```

**Design constraints** (design §F):
- Entry point signature: `def handler(event, context):` (Cognito calls `handler.handler`).
- Extract email: `email = event["request"]["userAttributes"]["email"].strip().lower()`. Guard for missing keys.
- **The handler MUST NEVER raise.** Wrap the entire body in `try/except Exception` → log + `return event`. Cognito requires the event returned.
- The Lambda runs in the VPC with its **own** DB connection (env `DB_SECRET_ARN`, `COGNITO_USER_POOL_ID` — DevOps sets these; already in the TF). It does **not** import the FastAPI app. Create a minimal SQLAlchemy/SQLModel `Session` from the DB secret. Keep imports light (Lambda cold-start) — a self-contained DB connect helper is fine; do not pull in the whole `app` package if it drags heavy deps. Confirm with a neighbor pattern if any Lambda helper exists; otherwise use `psycopg2`/SQLAlchemy directly with parameterized SQL.
- **Router logic** (keyed on `email`, in this order):
  1. **Path 1**: `SELECT id FROM "user" WHERE email = :email`. If found → log "existing user, no-op" → `return event`.
  2. **Path 2**: `SELECT id, tenant_id FROM tenant_user_invite WHERE email = :email AND accepted_at IS NULL AND is_active = true AND expires_at > now()` (most recent). If found → INSERT `user`, INSERT `tenant_user(tenant_id=invite.tenant_id, role_code=..., status_id=..., joined_at=now())`, UPDATE `invite.accepted_at = now()`. Commit. `return event`.
  3. **Path 3**: neither → INSERT `tenant(name = "{local_part}'s Company", is_active=true)` **unconditionally** (no collision check — ADR-0012), INSERT owner `user`, INSERT owner `tenant_user(role_code='owner', joined_at=now())` + status. Commit. `return event`.
- **Placeholder name**: `local_part = email.split("@")[0]; placeholder = f"{local_part}'s Company"`. Insert as-is; the wizard overwrites it (Task 3).
- **Audit context**: the Lambda has no authenticated app user. Set the audit actor to the newly-created user's own id where the audit trigger requires it (or the DB session's replica-role bypass if the Lambda writes are treated as system writes — mirror whatever the `_signup_impl` path does today; if `_signup_impl` doesn't call `set_audit_context_sync`, match that behavior and note it). Do not block a confirmation on audit context.
- Use the **exact** role/status resolution `_signup_impl` uses (`role_code='owner'`, active status) so the Lambda and the dev/test stand-in produce identical rows.

> **Reuse over duplication**: factor the create/attach logic so it reads clearly, but do NOT try to import `auth.py::_signup_impl` into the Lambda (it depends on FastAPI request models). The Lambda is standalone. The *shared contract* is "produce the same rows"; enforce that with the parity test in Task 5.

Run intermediate unit check after this task.

---

## Task 3 — `initiate_signup()` → resolve-or-attach by email (design §F)

Rewrite `services/tenant_signup.py::initiate_signup` to:

1. `SELECT` an existing owner `user` by `owner_email`; if found, get its tenant via `tenant_user`.
2. **If found** (normal self-serve case — Lambda Path 3 already ran): attach/return a `TenantSignup(step1_account)` for that tenant; persist `owner_email`/`owner_first_name`/`owner_last_name`; **overwrite `tenant.name` with the real `business_name`** (now safe — no unique constraint). Idempotent — a repeat call returns the existing signup state.
3. **If not found** (client raced ahead of Cognito confirmation): create a pending-credential `TenantSignup` keyed by `owner_email` (persist it), to be reconciled when the Lambda fires. Return `credential_pending: True`.
4. **Never create a second tenant** when the Lambda already made one for this email.
5. **Race safety**: wrap in one transaction; on a concurrent-insert anomaly (Lambda + client racing), re-`SELECT` and attach rather than raising.
6. Return `{ tenant_id, signup_state, owner_email, credential_pending: bool }`.

Reuse the existing `signup-state-conflict` **409** shape from `tenant_signup.py` when the email maps to a tenant already past `step1_account` (resume, don't recreate). `422` for invalid business fields.

Update `api/routes/signup.py` step-1 handler if its response shape changes (add `credential_pending`); update `api/schemas/signup.py` response model accordingly. Step 1 stays **public** (no JWT); steps 2–5 unchanged.

Run intermediate unit check.

---

## Task 4 — G6 reconciliation: remove the `_signup_impl` name pre-check

In `api/routes/auth.py`:
- **Remove** the `Tenant.name` uniqueness pre-check (`auth.py`) — ADR-0012. Keep the "user with this email already exists" check (that's still valid — email is the join key).
- Update the docstring/comment to clearly label `_signup_impl` as the **dev/test stand-in for the prod Post-Confirmation Lambda router** (design §A.2), so the two `signup` backends (G6) are unambiguous.
- Update the corresponding test assertion `tests/test_auth.py` that expects `"Tenant with this name already exists"` — retire that assertion (the behavior is gone). Do not delete the whole test if it covers other cases; remove only the now-invalid duplicate-name expectation.

Run intermediate unit check.

---

## Task 5 — Cleanup helper (abandoned signups, `signup_state`-keyed)

Add a small helper (in `services/tenant_signup.py` or a new `services/signup_cleanup.py`) that **identifies** abandoned self-serve signups by state, not by name (design §F):

```sql
SELECT t.id, ts.owner_email, ts.signup_state, t.created_at
FROM public.tenant t
JOIN public.tenant_signup ts ON ts.tenant_id = t.id
WHERE ts.signup_state <> 'complete'
  AND t.created_at < now() - (:days || ' days')::interval;
```

- This helper **reports/identifies only** — do **not** auto-delete in this batch (deletion is a separate guarded op). Expose it as a `def list_abandoned_signups(db, older_than_days: int) -> list[dict]`.
- **No Celery task, no schedule** in this batch.

---

## Test Requirements

Per `backend/tests/README-adding-tests.md` — domain folder: **`identity_access/`**.

Every new test file MUST declare:
```python
pytestmark = [pytest.mark.domain_identity_access, pytest.mark.unit]
```
Use the `client` fixture (never module-level `TestClient`), `test_tenant`/`test_user`/`tenant_a`/`tenant_b` fixtures (never hardcoded UUIDs), and scope every assertion by inserted IDs (never total row counts — shared seed data is always present). Use `second_tenant` for empty-state cases.

**Required test coverage:**

| Area | Tests |
|---|---|
| Lambda router | Path 1 (existing user → no-op, no tenant created); Path 2 (pending invite → user+tenant_user attached to invite tenant, `accepted_at` set, no new tenant); Path 3 (new owner → tenant+user+tenant_user created, placeholder name = `"{local}'s Company"`); **re-fire idempotency** (same email twice → Path 1 no-op the second time, exactly one user/tenant); **handler never raises** (feed a malformed event → returns `event`, logs, does not throw). |
| Placeholder name | Two different emails with the **same local-part** (e.g. `tom@a.com`, `tom@b.com`) both create tenants named `"tom's Company"` with **no** unique violation (proves the constraint is gone). |
| `initiate_signup` resolve-or-attach | Lambda-created tenant then `/signup` → attaches, overwrites `tenant.name` to business_name, persists `owner_email`, no 2nd tenant; repeat call idempotent; email past `step1_account` → 409 `signup-state-conflict`; client-ahead-of-confirmation → `credential_pending: True`. |
| G6 | `_signup_impl` no longer rejects a duplicate tenant name (two signups, same `tenant_name` → both succeed); email-dup still rejected. |
| Cleanup helper | seed a `tenant_signup` at `step1_account` older than N days → appears; a `complete` one → excluded; a recent incomplete one → excluded. |

> The Lambda handler is standalone (no FastAPI). Test its `handler(event, context)` / internal `_impl` functions directly with the `db_session` fixture — construct a synthetic Cognito `event` dict. Do not invoke real AWS.

**Autouse fixtures**: `mock_cognito_jwks` covers JWKS. No entitlement gating here, so `skip_mock_entitlement_allowed` is not needed. No Ollama/Whisper.

---

## Regeneration Steps

After tests pass and `ruff` is clean:

- **Models changed** (`TenantSignup` gained columns) → regenerate the model map:
  ```bash
  cd <repo>/backend && source .venv/bin/activate
  python generate_db_model_map.py app > db_models_map.md
  grep "TenantSignup" backend/db_models_map.md
  ```
- **New test files added** → regenerate the import map:
  ```bash
  python generate_app_import_map.py tests > app_model_imports.md
  ```
- **Endpoint response shape changed** (`/signup` gained `credential_pending`) → regenerate OpenAPI (this is the FE handoff signal for `SIGNUP-GA-1-FE`):
  ```bash
  python export_openapi_json.py
  grep -A 5 "signup" backend/openapi_schema_map.md
  ```
- **Schema JSON sync** (per §7 of inclusions): apply the `tenant_signup` column additions + the `tenant_name_key` removal to `pilot-db-schema-v2.6h.json` via `schema_manager.py` path-based verbs (`set` for the new columns under `tables.tenant_signup.columns`; `array-remove` the unique index under `tables.tenant.indexes`). Read `README-schema_manager.md` first. **Never** edit the JSON with sed/awk/inline Python — if `schema_manager.py` errors, STOP and ask Tom.

---

## Seed Data Rollout (Core + Scenario)

Per `backend/README-seed-data.md` — read §3 (Group A–D), §6 (run order), §7 (DELETE safety) before editing any seed script.

- The new `tenant_signup.owner_email`/names columns are **nullable and not lookup values** — no core/platform seed change is required. **However**, if any `seed_scenario_*.py` script creates `tenant_signup` rows, populate `owner_email` with a realistic value on those rows (value-scoped `UPDATE`/insert, per §7) so the resumable-signup UI has data. Grep:
  ```bash
  grep -rn "TenantSignup\|tenant_signup" backend/migrations/scripts/
  ```
- If none seed it, note "no scenario seeds create tenant_signup rows" in the Completion Summary and skip Layer 2.
- Run `python -m pytest -m unit` after any seed change (a new seed row a test doesn't expect will break assert-by-count tests — fix by scoping to inserted IDs).

---

## Final Verification

### Phase 1 — Unit Tests Only (during development)
```bash
cd <repo>/backend && source .venv/bin/activate
python -m pytest -m unit --tb=short -q 2>&1 | tail -10
```
All unit tests pass before moving on. Fix any failure (even seemingly unrelated) before proceeding.

### Phase 2 — Lint + Full Suite (once, at the end)
```bash
cd <repo>/backend && source .venv/bin/activate
ruff check . --fix
ruff format .
python -m pytest --tb=short -q 2>&1 | tail -10
python -m pytest tests/domains/identity_access/ -v 2>&1 | tail -30
alembic upgrade head && alembic downgrade -1 && alembic upgrade head && alembic current
echo "=== SIGNUP-GA-1 BACKEND FINAL VERIFICATION COMPLETE ==="
```

> Warning-clean is part of done: `ruff` reports zero issues; no Pydantic v1 carryover; no `DeprecationWarning` noise. Any failure in either phase must be fixed before done — no "pre-existing" exception without Tom's written OK.

---

## Definition of Done

- [ ] Pre-modification regression baseline captured (`X passed, Y failed`) via `pytest -m unit`
- [ ] Zero pre-existing unit failures confirmed before starting (or confirmed with Tom)
- [ ] All 8 MCP pre-work queries run; `tenant_name_key` confirmed, `user` has no `cognito_sub` confirmed; any column-name discrepancies noted
- [ ] All mandatory source files read (incl. `api/schemas/signup.py`)
- [ ] Migration: `tenant_name_key` dropped + `tenant_signup.owner_email`/names added (nullable); `downgrade()` exact reverse; full `upgrade/downgrade/upgrade` cycle passes
- [ ] `TenantSignup` model gained the three nullable fields
- [ ] `backend/lambda/post_confirmation/handler.py` authored — 3-path router, **never raises**, placeholder name inserted unconditionally, produces rows identical to `_signup_impl`
- [ ] `initiate_signup()` = resolve-or-attach by email; overwrites placeholder `tenant.name`; persists `owner_email`; idempotent + race-safe; never creates a 2nd tenant; returns `credential_pending`
- [ ] `_signup_impl` name pre-check removed (G6); docstring labels it the dev/test Lambda stand-in; `test_auth.py` duplicate-name assertion retired
- [ ] `list_abandoned_signups()` helper added (report-only, `signup_state`-keyed); no Celery/schedule
- [ ] All DB-touching routes/`_impl()`/service fns are sync `def` (§21)
- [ ] Pydantic v2 only; `/signup` response has `response_model`; RFC 7807 errors (reused `signup-state-conflict` 409)
- [ ] New test files use `pytestmark` (domain_identity_access + unit); no module-level `TestClient`; fixtures not hardcoded UUIDs; assert-by-ID
- [ ] `generate_db_model_map.py app > db_models_map.md` run; `generate_app_import_map.py tests > app_model_imports.md` run
- [ ] `schema_manager.py` used for the JSON schema delta (columns added, unique index removed) — never hand-edited
- [ ] `export_openapi_json.py` run — `/signup` `credential_pending` present in `openapi_schema_map.md`
- [ ] `ruff check . --fix && ruff format .` — zero issues
- [ ] **Phase 1**: all unit tests pass
- [ ] **Phase 2**: full suite passes (incl. integration), warning-clean
- [ ] Final test count (before → after) documented
- [ ] Completion Summary added to the launch plan §2.3 SIGNUP-GA-1 card
- [ ] Handoff Instructions executed (notify DevOps the Lambda package is ready)

---

## Handoff Instructions (to DevOps + FE) — REQUIRED final step

After all DoD items are complete:

1. **Confirm the Lambda handler location** for DevOps packaging: `backend/lambda/post_confirmation/handler.py` (entry `handler.handler`, runtime `python3.12`, matches the Terraform in `infrastructure/terraform/modules/security/main.tf`). List any pip dependencies the handler needs (e.g. `psycopg2-binary`, `sqlalchemy`) so DevOps builds the deployment package/layer correctly.
2. **Notify the DevOps engineer** (`batch-signup-ga-1-devops-prompt.md`) that the handler + migration are merged: DevOps now (a) packages/deploys this handler replacing the placeholder stub, (b) flips `allow_admin_create_user_only = false` (re-enable self-sign-up), and (c) wires/confirms the Post-Confirmation trigger.
3. **Notify the React Engineer** (`SIGNUP-GA-1-FE`, separate batch) that OpenAPI is regenerated — their first Pre-Work step is `pnpm sync-api-types` to pick up the `/signup` `credential_pending` field.
4. Confirm the migration has been applied to the shared dev DB so the FE/DevOps environments are consistent.

---

## Completion Summary

Add a **Completion Summary** subsection to `pilot-launch-plan.md` §2.3 (SIGNUP-GA-1 card) using this format:

```markdown
### SIGNUP-GA-1 (Backend) — Post-Confirmation Lambda Router + Self-Serve Signup: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot Python Engineer
**Baseline**: X passed, Y failed
**Final**: X+N passed, Y failed (+N new tests)

#### What Was Accomplished
- 3-path Post-Confirmation Lambda router authored (Path 1 no-op / Path 2 invite-attach / Path 3 new-owner) — never raises to Cognito
- initiate_signup() → resolve-or-attach by email; owner_email persisted; placeholder name overwritten
- tenant_name_key dropped (ADR-0012); G6 _signup_impl name pre-check removed
- [any MCP column-name discrepancies discovered]

#### Files Changed / Created
| File | Action |
|---|---|
| `backend/lambda/post_confirmation/handler.py` | Created — 3-path router |
| `backend/services/tenant_signup.py` | Updated — resolve-or-attach + cleanup helper |
| `backend/api/routes/auth.py` | Updated — removed name pre-check (G6) |
| `backend/migrations/versions/<rev>_signup_ga1_*.py` | Created — drop unique + add owner_email |
| ... | ... |

#### Tests Added
| Test File | Domain | Tests | All Pass |
|---|---|---|---|
| `tests/domains/identity_access/test_post_confirmation_router.py` | `domain_identity_access` | N | ✅ |
| `tests/domains/identity_access/test_signup_resolve_or_attach.py` | `domain_identity_access` | N | ✅ |
```

---

## After This Task — Next Step

DevOps runs `batch-signup-ga-1-devops-prompt.md` (package/deploy the Lambda + flip the pool). Then the React Engineer runs `SIGNUP-GA-1-FE` (password field + Amplify `SignUp`) after `pnpm sync-api-types`. Path 2 (invite) and Path 1 (platform admin) UIs are the follow-on `TEAM-INVITE-1` / `PLATFORM-ADMIN-1` batches — the router already supports them.
