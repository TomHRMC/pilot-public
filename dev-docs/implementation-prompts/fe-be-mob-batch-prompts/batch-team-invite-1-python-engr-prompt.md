# Implementation Prompt: TEAM-INVITE-1 (Part A) — Tenant-Owner Invite Endpoints + Email + Lambda Role-at-Invite

**Mode**: Pilot Python Engineer
**Batch**: TEAM-INVITE-1 — Part A (Backend, runs first)
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §3.8 (card) + §7 founder-gate row
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-team-invite-1-design.md` — **read in full before starting**; sections B–G are the binding contract
**Estimated session**: 3–4 hours
**Platform**: Backend only (`backend/` + `backend/lambda/`)
**Frontend companion**: TEAM-INVITE-1 Part B (React) — gated on this batch's OpenAPI regen **and** the Tom-approved Web UI designer spec; you do not hand off to React directly (see §Handoff)

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-python-engineer/python-engineer-rules.md`** — full document; the 25 hard rules are non-negotiable STOPs
- **`dev-docs/architecture-design/pilot-python-engineer-methods.md`** — §13 (Alembic), §8 (Router Design), §5 (Model Design), §16 (Standard Task Workflow)
- **`backend/tests/README-adding-tests.md`** — full document; governs all test file structure, domain markers, fixture rules
- **`backend/README-seed-data.md`** — §3 (Group A–D), §6 (run order), §7 (DELETE safety rule) — required before touching any seed script

Critical rules for this batch:

- **Rule 1 / 16 (verify-before-write)**: Never guess column names or table shapes. Run every MCP query in Pre-Work before writing SQL. The live DB is the only authority — if this prompt and MCP disagree, MCP wins; note the discrepancy in your Completion Summary and proceed with the MCP-verified shape.
- **Rule 4 (blank migrations + ADR-0016)**: `alembic revision -m "..."` blank only — never autogenerate. **Migrations are DDL-only (ADR-0016)**: the `team_invite` email template and the dev pending-invite row ship via seed scripts, **never** as migration INSERTs. A migration-embedded INSERT is a code-review reject.
- **Rule 6**: `db.get()` permanently banned on tenant-scoped models — tenant-scoped `select()` with explicit `WHERE tenant_id = :tid` everywhere.
- **Rule 8 (RFC 7807)**: Every error response is a Problem Details dict (`type`/`title`/`status`/`detail`). Plain-string `detail` is banned. 404 (not 403) for tenant-scoped misses — no UUID enumeration.
- **Rule 9 (audit context)**: `set_audit_context_sync(db, user_id=current_user.id)` before the first `db.add()`/`db.commit()` in every authenticated mutation endpoint.
- **Rule 12 (sync-by-design §21)**: Every route/`_impl()`/service touching the `Session` is plain `def` — never `async def` with the blocking psycopg2 Session.
- **Rule 13 (Pydantic v2)**: `model_config = ConfigDict`, `@field_validator`, `.model_dump()`. `response_model` on every route.
- **Rule 14 (ruff, changed files only)**: `git diff --name-only --diff-filter=d HEAD -- '*.py' | sed 's|^backend/||'` → `ruff check --fix` + `ruff format` on that set only; fix ALL errors in those files including pre-existing.
- **Phantom-gate rule (rules §17/§18 + PLP-FIX-1 standing rule)**: **No `feature_code=` on any endpoint in this batch.** Users are unlimited on every plan (PRD §3.11; MKT-B11 permanent invariant). `require_permission("users.manage")` / `require_permission("users.view")` — RBAC only.
- **Seed DELETE safety (README §7 / Architect Rule 11.1)**: any DELETE in a seed script's `mode_seed` path must be value-scoped to the exact row being re-inserted (full business key) — never channel/partial-key scoped.
- **Lambda never-raise invariant (ADR-0011)**: the Post-Confirmation handler must never raise to Cognito. The new usage-counter write is a **separate post-commit, fully wrapped** best-effort step (design §F.3).
- **Rule 11**: Any test failure during your work — even one that looks pre-existing — gets fixed or explicitly confirmed with Tom before you declare done.

---

## Pre-Work: Establish Regression Baseline

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=no -q 2>&1 | tail -5
```

Record the exact count: **`X passed, Y failed`**. If anything is failing before you start: fix it or get Tom's written confirmation it's known/accepted. You may NOT start implementation with unexplained failures. (Last known green: **4769 passed / 0 failed** at PLP-FIX-5 close.)

---

## Pre-Work: Run MCP Verification Queries

Run **all** of these via `postgres-local` MCP before writing any code. If any returns unexpected results → **STOP and ask Tom**.

```sql
-- 1. Confirm tenant_user_invite has NO role_code yet (12 columns expected) + exact existing columns
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'tenant_user_invite'
ORDER BY ordinal_position;

-- 2. Confirm the FK target: tenant_user_role PK is code + the 4 active role rows
SELECT conname, contype FROM pg_constraint
WHERE conrelid = 'public.tenant_user_role'::regclass AND contype IN ('p','u');
SELECT code, name, is_active, is_default FROM public.tenant_user_role ORDER BY code;

-- 3. Confirm current alembic head (expected: ec2df153a859)
SELECT version_num FROM public.alembic_version;

-- 4. Confirm email_template row count (expected: 16) and the template_id PK shape
SELECT count(*) AS email_template_rows FROM public.email_template;
SELECT column_name, data_type, is_nullable FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'email_template' ORDER BY ordinal_position;

-- 5. Confirm the natural-key unique constraint (idempotency fallback) + token index exist
SELECT conname, contype FROM pg_constraint
WHERE conrelid = 'public.tenant_user_invite'::regclass;
SELECT indexname FROM pg_indexes
WHERE schemaname = 'public' AND tablename = 'tenant_user_invite';
```

> **MCP Usage Rule**: `postgres-local` is **read-only verification only**. Never INSERT/UPDATE/DELETE via MCP — all data changes go through migrations, seed scripts, or application code. On any MCP error → STOP and ask Tom. `postgres-prod` exists but requires Tom's SSH tunnel — this batch does not use it.

---

## Pre-Work: Read These Source Files

Use `read_file` on each before writing any code:

```
backend/app/models/auth.py                          ← TenantUserInvite (line ~169), TenantUser, TenantUserRole, TenantUserStatus — the models you extend
backend/api/routes/roles.py                         ← Route file pattern: _impl() shared functions, /test twins registered BEFORE authenticated, require_permission wiring, last-owner guard
backend/api/schemas/roles.py                        ← Pydantic v2 schema shapes for this domain
backend/api/routes/invoices.py  (lines ~1473–1529)  ← THE Idempotency-Key house pattern: Header(alias="Idempotency-Key"), authenticated route raises when missing, test twin tolerates None
backend/api/routes/public_tenant_sites.py           ← Public-route pattern: no auth, @limiter.limit("60/minute"), def route
backend/core/rate_limit.py                          ← SlowAPI limiter, key_func behavior for unauthenticated requests
backend/core/idempotency.py                         ← The 24h response-cache middleware (X-Idempotency-Replay) — understand what it gives you for free
backend/services/email_template_renderer.py         ← render_and_send() signature + category behavior (internal ⇒ tenant_id=None)
backend/services/onboarding_service.py              ← mark_team_invited() (line ~119) — zero callers today; you wire it
backend/services/tier_limit_enforcer.py             ← check_user_add_allowed() + increment_user_count() bodies (lines ~100–193)
backend/lambda/post_confirmation/handler.py         ← Path 2 attach (lines ~206–273) + the TEAM-INVITE-1 comment at 248–250
backend/migrations/scripts/seed_core.py             ← email_template JSON-file loader section (verify it walks data/email_templates/*.json)
backend/migrations/scripts/seed_test_tenant.py      ← Group C insert patterns + value-scoped DELETE idempotency (README §7)
backend/migrations/scripts/data/email_templates/welcome.json  ← JSON file shape
backend/tests/conftest.py                           ← fixtures (test_tenant, test_user, second_tenant, mock_cognito_jwt…)
backend/tests/domains/identity_access/test_post_confirmation_router.py  ← existing Lambda Path 2 tests — you extend this file
backend/db_models_map.md                            ← model ↔ table map (regenerate after model change)
backend/migrations/versions/2026_09_02_*_ec2df153a859_*.py  ← most recent migration — blank-migration pattern reference (find exact filename via ls)
```

Also grep for related files:

```bash
grep -rn "TenantUserInvite" backend/ --include="*.py" -l
grep -rn "render_and_send" backend/ --include="*.py" -l
grep -rn "mark_team_invited" backend/ --include="*.py" -l
```

---

## Background / Context

Founders must invite up to ~5 employees before launch (§7 founder-gate row). The Cognito attach half already exists: when an invited person signs up and confirms, the Post-Confirmation Lambda's **Path 2** finds their pending `tenant_user_invite` (by email), creates their `user`, attaches `tenant_user` to the inviting tenant, and stamps `accepted_at`. What's missing is everything upstream: the owner's invite endpoint, the invite email, token lifecycle, the public token-validation endpoint for the landing page, and role selection at invite time (Path 2 currently hardcodes `technician` — see the comment it left for this batch at `handler.py–250`).

This batch is Part A (backend). Part B (React: invite dialog + pending list + `/invite/[token]` landing + ADR-0010 FE role-vocabulary reconciliation) runs after a designer spec; your OpenAPI regen is its contract source.

Design decisions already made (do not re-litigate; design §G): role carried on the invite (new nullable column — Migration 1); 7-day expiry; 409 for existing-user and duplicate-pending; all four roles invite-exposed; invite email via `render_and_send` category `internal`; `users.manage` RBAC (no new permission, no `feature_code`); usage counter fires best-effort in the Lambda post-commit.

---

## Task 1 — Migration: `tenant_user_invite.role_code` + model

Per design §B.2. Blank migration, DDL-only (ADR-0016 — **no data INSERTs**):

```bash
alembic revision -m "team_invite_1_tenant_user_invite_role_code"
```

```python
def upgrade() -> None:
    op.add_column("tenant_user_invite", sa.Column("role_code", sa.String(), nullable=True))
    op.create_foreign_key(
        "fk_tenant_user_invite_role_code",
        "tenant_user_invite",
        "tenant_user_role",
        ["role_code"],
        ["code"],
    )

def downgrade() -> None:
    op.drop_constraint("fk_tenant_user_invite_role_code", "tenant_user_invite", type_="foreignkey")
    op.drop_column("tenant_user_invite", "role_code")
```

Nullable add — the 3-part NOT NULL pattern does **not** apply (no backfill, no lock). Then add `role_code: str | None` (FK to `tenant_user_role.code`) to `TenantUserInvite` in `app/models/auth.py` — mirror how `TenantUser.role_code` declares its FK.

**Cycle test**: `alembic upgrade head` → `alembic downgrade -1` → `alembic upgrade head` → `alembic current` shows the new head. Then MCP-verify the column + FK landed.

Intermediate gate: `python -m pytest -m unit --tb=short -q 2>&1 | tail -5` — zero regressions.

---

## Task 2 — Seed Data Rollout (Rule 11.5 — mandatory)

Per design §B.3 and the inclusions §20 template.

### Layer 1 — Core/Platform (Group A, `seed_core.py`)

1. **Create `backend/migrations/scripts/data/email_templates/team_invite.json`** — shape mirrors `welcome.json`:
   - `template_id`: `"team_invite"`, `display_name`: `"Team Invite"`, `category`: `"internal"`
   - `subject_template`: `"You've been invited to join {{tenant_name}} on Pilot for Trades"`
   - Bodies (HTML + plain): inviter's company (`{{tenant_name}}`), role display (`{{role_name}}`), single CTA to `{{invite_url}}`, expiry line (`{{expires_date}}`), plain-text fallback URL. Transactional tone, no marketing chrome.
   - `variables`: `["invitee_email", "tenant_name", "role_name", "invite_url", "expires_date"]`
2. Verify `seed_core.py`'s email_template loader picks up new JSON files automatically (it walks `data/email_templates/*.json` — confirm in your file read; if it hardcodes a list, add `team_invite`). Idempotent `ON CONFLICT DO NOTHING`.
3. Run `python migrations/scripts/seed_core.py` then `--mode inspect` → `email_template` = **17**.
4. Update `backend/README-seed-data.md` §4: `email_template` row → 17, note TEAM-INVITE-1.

### Layer 2 — Scenario/dev data (Group C, `seed_test_tenant.py`)

5. Add one **pending** invite for the test tenant so the FE pending-list has real data:
   - `email='newguy@pilot.local'`, `role_code='technician'`, `expires_at = NOW() + 7 days`, `invited_by` = owner user id (looked up at runtime, never hardcoded beyond the reserved-UUID owner `...0002` which is a legitimate deterministic seed constant), `token_hash = hashlib.sha256(b'dev-invite-token-0001').hexdigest()` — with a script comment documenting raw token `dev-invite-token-0001` for FE landing-page dev. Never store the raw token in the DB.
   - Idempotency: the table HAS `uq_tenant_user_invite_tenant_id_email` → prefer `INSERT ... ON CONFLICT DO NOTHING`; if you DELETE first it must be scoped to `(tenant_id, email)` exactly (README §7 value-scoping rule).

### Verification

- `python migrations/scripts/seed_test_tenant.py` + `python migrations/scripts/seed_core.py --mode inspect`
- `python -m pytest -m unit --tb=short -q 2>&1 | tail -5` — the shared-DB rule: a seed row a test doesn't expect breaks tests. Fix any seed-resilience failures (assert-by-ID, never by count).

---

## Task 3 — Schemas + `services/team_invite_service.py`

New `backend/api/schemas/team_invites.py` (Pydantic v2):

- `TeamInviteCreateRequest` — `email: EmailStr`, `role_code: str`
- `TeamInviteResponse` — `id, email, role_code, expires_at, created_at`
- `TeamInviteListItem` — response fields + computed `status` (`accepted` → `revoked` → `expired` → `pending`, precedence per design §D2)
- `TeamInvitePublicResponse` — `tenant_name, email, role_code, expires_at` (D5)

New `backend/services/team_invite_service.py` (sync `def`; tenant-scoped `select()` everywhere; typed service exceptions the route maps to RFC 7807 codes):

- `_generate_invite_token() -> tuple[str, str]` — `secrets.token_urlsafe(32)` + SHA-256 hex (design §F.2). Raw token leaves the process **only** inside the invite email URL.
- `create_invite(db, *, tenant_id, email, role_code, invited_by)` → `(TenantUserInvite, raw_token)`:
  1. role must be an active `tenant_user_role` row → else `InvalidRoleError` (400)
  2. `check_user_add_allowed(db, tenant_id)` — call for forward-compat (always true)
  3. `user` row exists for email → `InviteUserExistsError` (409 `invite_user_exists`)
  4. pending invite exists for `(tenant_id, email)` (accepted_at NULL, is_active, expires_at > now) → `InvitePendingExistsError` (409 `invite_pending_exists`, carry the existing invite id)
  5. insert (`expires_at = now + 7 days`), then `render_and_send(db, "team_invite", context={invitee_email, tenant_name, role_name, invite_url, expires_date}, to_address=email)` — `tenant_name` from the tenant row, `role_name` from `tenant_user_role.name`, `invite_url` = web-app base + `/invite/{raw_token}` (**verify the base-URL config key** against `services/public_link_signer.py` and the public quote/invoice link construction — reuse the same mechanism; do not invent a new env var)
  6. `mark_team_invited(db, tenant_id)` wrapped non-fatal (log + continue — the invite must not fail on a checklist write)
- `list_invites(db, *, tenant_id)` → all invites `created_at DESC`
- `resend_invite(db, *, tenant_id, invite_id)` → rotate token, `expires_at = now + 7d`, resend email. 404 if not found in tenant; 409 `invite_already_accepted` / `invite_revoked`
- `revoke_invite(db, *, tenant_id, invite_id)` → `is_active=False`. 404 / 409 same shape
- `validate_invite_token(db, *, raw_token)` → `TenantUserInvite | None` — hash lookup via `ix_tenant_user_invite_token_hash`; `None` for unknown/expired/accepted/revoked (uniform-404 contract, design §G.9)

---

## Task 4 — Routes: `api/routes/team_invites.py` + registration

New router `APIRouter(prefix="/api/v1", tags=["team-invites"])`. **`/test` twins registered BEFORE the authenticated twins** (house pattern from `roles.py–256`). Authenticated POSTs use the hard-required Idempotency-Key pattern from `invoices.py–1517` (`Header(default=None, alias="Idempotency-Key")`; authenticated route raises 400 RFC 7807 `idempotency-key-required` when absent; `/test` twin tolerates `None`). The `core/idempotency.py` middleware supplies the 24h replay cache automatically. All mutations call `set_audit_context_sync()` first. All errors RFC 7807; **no `feature_code=` on any `require_permission`** (phantom-gate rule — users are unlimited).

| Endpoint | Auth | Contract |
|---|---|---|
| `POST /users/invites` + `/users/invites/test` | `users.manage` | 201 `TeamInviteResponse` — **never** the raw token. 400 `invalid_role` · 409 `invite_user_exists` / `invite_pending_exists` (detail carries existing invite id) · 422 |
| `GET /users/invites` + `/users/invites/test` | `users.view` | 200 `list[TeamInviteListItem]` with computed `status` |
| `POST /users/invites/{invite_id}/resend` + `/test` twin | `users.manage` | 200 `{id, email, expires_at}` · 404 `invite_not_found` · 409 `invite_already_accepted` / `invite_revoked` |
| `POST /users/invites/{invite_id}/revoke` + `/test` twin | `users.manage` | 200 `{id, is_active: false}` · 404 · 409 `invite_already_accepted` |
| `GET /invites/{token}` (public — NO auth) | — | `@limiter.limit("10/minute")` (verify unauthenticated keying in `core/rate_limit.py`); 200 `TeamInvitePublicResponse` (`tenant_name, email, role_code, expires_at`); **uniform 404 `invite_invalid` for every failure mode** (unknown/expired/accepted/revoked) — no enumeration oracle |

Register the router in `backend/app/main.py` alongside the other route registrations.

Intermediate gate: `python -m pytest -m unit --tb=short -q 2>&1 | tail -5`.

---

## Task 5 — Lambda Path 2: role-at-invite + best-effort usage counter

Per design §F.3, in `backend/lambda/post_confirmation/handler.py`:

1. Replace the hardcoded role in `_path2_attach_invite` (lines ~248–250):
   ```python
   # TEAM-INVITE-1: role carried on the invite; NULL = pre-TEAM-INVITE-1 rows → technician
   role_code = invite.role_code if invite.role_code else "technician"
   role = _get_or_create_role(db, role_code)
   ```
2. After the attach `db.commit()`, add a **separately wrapped** best-effort usage increment mirroring `increment_user_count()` inline (current-period `tenant_subscription_usage`; monthly-aligned create-if-missing — copy the period math from `tier_limit_enforcer.py–174`). Model imports only (the Lambda never imports services — packaging constraint); comment points at the canonical function. Its own `try/except` logs and swallows — analytics must never jeopardize account birth (ADR-0011).
3. Extend `backend/tests/domains/identity_access/test_post_confirmation_router.py`: invite with `role_code='office_staff'` → attached `tenant_user.role_code == 'office_staff'`; invite with `role_code=None` → `'technician'`; usage-increment failure path still completes the attach (force the failure via monkeypatch).

---

## Task 6 — Tests (domain: `identity_access/`)

Per `backend/tests/README-adding-tests.md`. New file `backend/tests/domains/identity_access/test_team_invites.py` with `pytestmark = [pytest.mark.domain_identity_access, pytest.mark.unit]` (verify the exact domain marker name in `pytest.ini` / an existing identity_access file). Use the `client` fixture, `test_tenant`/`test_user` fixtures, assert-by-inserted-ID (never counts), `/test` endpoints for creation where convenient.

**Email dispatch is mocked**: monkeypatch the `send_email` import inside `services.email_template_renderer` (the function `render_and_send` calls) — assert it was called with the `team_invite` context and capture the rendered `invite_url` for token assertions. No real SendGrid. (This batch calls but does not modify SendGrid dispatch code — see the Phase 2 vendor-suite call below.)

Coverage (minimum):

| # | Case | Expect |
|---|---|---|
| 1 | create invite happy path (owner JWT) | 201; row has role_code, ~7d expiry; email "sent" with `/invite/<token>` URL; checklist `team_invited=True` |
| 2 | create with bogus role | 400 `invalid_role` |
| 3 | create when `user` row exists for email | 409 `invite_user_exists` |
| 4 | create duplicate pending (same tenant+email) | 409 `invite_pending_exists` + existing id in detail |
| 5 | idempotency: same `Idempotency-Key` replay | middleware replay (same response, `X-Idempotency-Replay: true`) — verify against `core/idempotency.py` behavior; missing header on authenticated route → 400 |
| 6 | RBAC: non-owner (e.g. technician-context) create | 403 |
| 7 | list invites | status precedence correct (accepted > revoked > expired > pending) |
| 8 | resend happy path | new expiry in the future, email resent; old token invalid, new token valid (via `validate_invite_token`) |
| 9 | resend accepted invite | 409 `invite_already_accepted` |
| 10 | revoke pending | `is_active=False`; subsequent public lookup → 404 |
| 11 | revoke accepted | 409 |
| 12 | public `GET /invites/{token}` happy | 200 with tenant_name/email/role_code; unknown token → 404 `invite_invalid`; expired → 404; accepted → 404; revoked → 404 (all identical body) |
| 13 | cross-tenant: invite id from `tenant_a` targeted by `tenant_b` owner | 404 (no UUID leak) |
| 14 | service unit: `validate_invite_token` hash path | token from case 1's captured email URL validates; garbage token → None |

---

## Verification Checkpoints

- After Task 1: migration cycle test + MCP column/FK verify + unit gate
- After Task 2: seed inspect (`email_template`=17; pending invite present) + unit gate
- After Task 4: unit gate
- After Task 6: full Phase 1 unit gate

---

## Regeneration + Schema Steps

```bash
cd <repo>/backend && source .venv/bin/activate

# 1. Model changed → regenerate DB model map
python generate_db_model_map.py app > db_models_map.md

# 2. New test files → regenerate import map
python generate_app_import_map.py tests > app_model_imports.md

# 3. Schema JSON sync (path-based ONLY — read backend/README-schema_manager.md first;
#    NEVER sed/awk the JSON):
python schema_manager.py get --path tables.tenant_user_invite.columns
cat << 'EOF' > temp_payload.json
{ "type": "varchar", "nullable": true, "description": "Role assigned at invite time; applied to tenant_user at acceptance. NULL = legacy rows (technician fallback)." }
EOF
python schema_manager.py set --path tables.tenant_user_invite.columns.role_code --payload temp_payload.json
# append the FK entry per README-schema_manager.md (array-append on tables.tenant_user_invite.foreign_keys)
rm temp_payload.json

# 4. Endpoints changed → regenerate OpenAPI (both outputs)
python export_openapi_json.py
grep -A 5 "users/invites" backend/openapi_schema_map.md
grep -A 5 "invites/{token}" backend/openapi_schema_map.md
```

---

## Final Verification

### Phase 1 — Unit Tests Only

```bash
cd <repo>/backend && source .venv/bin/activate
python -m pytest -m unit --tb=short -q 2>&1 | tail -10
```

### Phase 2 — Lint (changed files only) + Full Suite, Vendor-Deselected

```bash
cd <repo>/backend && source .venv/bin/activate

CHANGED_PY=$(git diff --name-only --diff-filter=d HEAD -- '*.py' | sed 's|^backend/||')
if [ -n "$CHANGED_PY" ]; then
    ruff check --fix $CHANGED_PY
    ruff format $CHANGED_PY
    ruff check $CHANGED_PY
fi

python -m pytest -m "not integration and not requires_telnyx and not requires_stripe and not requires_sendgrid and not requires_redis and not e2e" --tb=short -q 2>&1 | tail -15

# Batch-specific spot checks
python -m pytest tests/domains/identity_access/ -v 2>&1 | tail -25
grep -A 5 "users/invites" backend/openapi_schema_map.md

echo "=== TEAM-INVITE-1 PART A FINAL VERIFICATION COMPLETE ==="
```

**Vendor-suite inclusion call**: `requires_sendgrid` is **NOT** required — this batch *calls* `render_and_send` but modifies no SendGrid dispatch code (`services/email_service.py`, `services/email_template_renderer.py` untouched); all sends are monkeypatched in tests. No Telnyx/Stripe/Redis-covered code touched. State any deviation in the Completion Summary.

> Warning-clean is part of done: ruff zero remaining issues in changed files; pytest free of DeprecationWarning noise. Any failure in either phase is fixed (or Tom-confirmed) before done.

---

## Definition of Done

Check off each item **in this prompt doc** as it completes:

- [ ] Pre-modification regression baseline captured (`X passed, Y failed`) using `pytest -m unit`
- [ ] Zero pre-existing unit failures confirmed before starting (or Tom-confirmed)
- [ ] All 5 MCP pre-work queries run — `tenant_user_invite` has no `role_code` pre-migration; `tenant_user_role` PK=code with 4 roles; head=`ec2df153a859`; `email_template`=16; uq constraint + token index present (every touched table re-verified via `information_schema.columns` before SQL, rules §25)
- [ ] All mandatory source files read (including `api/schemas/roles.py` + the idempotency/rate-limit references)
- [ ] Task 1: migration `role_code` + FK; cycle test clean; `TenantUserInvite` model updated
- [ ] Task 2: `team_invite.json` created; `seed_core.py` loads it; inspect shows `email_template`=17; pending dev invite seeded idempotently (value-scoped); README §4 updated
- [ ] Task 3: schemas + `team_invite_service.py` per design §F — token helper, create/list/resend/revoke/validate; `mark_team_invited` wired non-fatally; base-URL config verified against public-link mechanism (no invented env var)
- [ ] Task 4: `team_invites.py` router — 4 authenticated + 1 public + `/test` twins registered BEFORE authenticated; router registered in `app/main.py`
- [ ] Task 5: Lambda role-at-invite + NULL fallback + best-effort usage counter (separate wrapped transaction); Lambda tests extended
- [ ] Task 6: `test_team_invites.py` — all 14 cases green
- [ ] All DB-touching routes/`_impl()` are sync `def` (rules §21)
- [ ] Pydantic v2 idioms only; every route has `response_model` (rules §22)
- [ ] `set_audit_context_sync()` at the start of every authenticated mutation endpoint
- [ ] All errors RFC 7807; uniform 404 on the public endpoint; 404-not-403 on tenant-scoped misses
- [ ] **No `feature_code=` anywhere** (phantom-gate rule); RBAC = `users.manage`/`users.view` only
- [ ] Idempotency-Key hard-required on authenticated POSTs; replay behavior tested
- [ ] All new test files use `pytestmark` domain marker + `pytest.mark.unit`; `client` fixture only; assert-by-ID; no hardcoded UUIDs
- [ ] `generate_db_model_map.py app > db_models_map.md` + `generate_app_import_map.py tests > app_model_imports.md` run
- [ ] `schema_manager.py` path-based sync done (`role_code` column + FK) — JSON never hand-edited
- [ ] `python export_openapi_json.py` run — `users/invites` + `invites/{token}` visible in `openapi_schema_map.md`
- [ ] Ruff gate on changed files only — zero remaining issues, no unjustified `# noqa`
- [ ] **Phase 1**: all unit tests pass — zero failures including pre-existing
- [ ] **Phase 2**: full suite (vendor-deselected) passes — zero failures, warning-clean; vendor-inclusion call recorded
- [ ] Final test count (before → after) documented
- [ ] Completion Summary filled in at this prompt doc's ending `## Appendix — Completion Summary`
- [ ] Source spec headers updated ✅ where applicable (README-seed-data.md §4 done in Task 2; no §10 task row closes)

---

## Handoff (Part B gate — do NOT start React)

1. Commit including regenerated `openapi.json` + `openapi_schema_map.md`.
2. Notify the Architect/Tom: Part A complete. The React prompt is **not** issued until the Web UI designer spec (`batch-team-invite-1-ui-design-spec.md`) is Tom-approved (Rule 1.5); Part B's first Pre-Work step will be `pnpm sync-api-types` against your regenerated spec.
3. **Tom deploy tail** (not yours): prod migration via `aws-ops-runbook.md` §9.2 → `seed_prod_db.py --mode seed --stripe-mode test` converge (new `team_invite` template is Group A) → Lambda redeploy via `infrastructure/scripts/build-post-confirmation-lambda.sh` (design §B.4).

## After This Task — Next Step

Architect commissions the `pilot-web-ui-designer` spec (design §H brief). React prompt authors after Tom approves it.

---

## Appendix — Completion Summary

### TEAM-INVITE-1 Part A — Invite Endpoints + Email + Lambda Role-at-Invite: Completion Summary

**Completed**: 2026-09-03
**Mode**: Pilot Python Engineer
**Baseline**: 4769 passed, 0 failed, 1 skipped
**Final**: 4786 passed, 0 failed, 1 skipped (+17 new tests: 14 team_invites + 3 Lambda Path 2)

#### What Was Accomplished

- **Migration 1** (`3da9abdfb2f2`): Added nullable `role_code` column + FK to `tenant_user_invite` → `tenant_user_role(code)`. DDL-only (ADR-0016). Cycle test clean (upgrade → downgrade → upgrade). MCP-verified column + FK landed.
- **Seed Data**: Created `team_invite.json` email template (category=internal, 5 variables). `seed_core.py` auto-loads it; `email_template` count = 17. Added pending dev invite (`newguy@pilot.local`, role=technician, raw token `dev-invite-token-0001`) to `seed_test_tenant.py` with value-scoped `ON CONFLICT DO NOTHING` idempotency. README §4 updated.
- **Schemas** (`api/schemas/team_invites.py`): 6 Pydantic v2 schemas — create request, response, list item (with computed status), resend response, revoke response, public response.
- **Service** (`services/team_invite_service.py`): Token helper (`secrets.token_urlsafe(32)` + SHA-256), `create_invite` (role validation, user-exists check, pending-duplicate check, email send via `render_and_send`, `mark_team_invited` non-fatal), `list_invites`, `resend_invite` (token rotation), `revoke_invite`, `validate_invite_token` (uniform None for all failure modes), `compute_invite_status` (accepted > revoked > expired > pending). Typed service exceptions mapped to RFC 7807 by the route. Web app base URL resolved via `FRONTEND_URL`/`PUBLIC_BASE_URL` getattr pattern (no invented env var).
- **Routes** (`api/routes/team_invites.py`): 4 authenticated endpoints (create/list/resend/revoke) + 1 public endpoint (`GET /invites/{token}`) + 4 `/test` twins registered BEFORE authenticated. Idempotency-Key hard-required on authenticated POSTs (400 RFC 7807 when missing; `/test` twins tolerate None). `set_audit_context_sync()` on every mutation. RBAC = `users.manage`/`users.view` only — **no `feature_code=`** (phantom-gate rule). Public endpoint has `@limiter.limit("10/minute")` + uniform 404. Router registered in `app/main.py`.
- **Lambda Path 2** (`lambda/post_confirmation/handler.py`): Replaced hardcoded `"technician"` with `invite.role_code if invite.role_code else "technician"` (NULL fallback). Added `_increment_user_count_best_effort()` — separately wrapped, best-effort usage counter mirroring `tier_limit_enforcer.increment_user_count()` inline (Lambda never imports services — packaging constraint). Any failure is logged and swallowed (ADR-0011 never-raise invariant).
- **Tests**: 14 new test cases in `test_team_invites.py` (create happy/bogus-role/user-exists/duplicate-pending/missing-idem-key/RBAC, list status precedence, resend happy/accepted-conflict, revoke pending/accepted, public lookup happy+4 failure modes, cross-tenant 404, service token validation). 3 new Lambda tests (role=office_staff, role=NULL→technician, usage-counter failure still completes attach). Email dispatch mocked via `patch("services.email_service.send_email")`.
- **Regeneration**: `db_models_map.md`, `app_model_imports.md`, `openapi.json` + `openapi_schema_map.md` all regenerated. `schema_manager.py` path-based sync done (`role_code` column + FK in `pilot-db-schema-v2.6h.json`).
- **Ruff**: Zero remaining issues in changed files (fixed 3 pre-existing UP031 percent-format errors in `handler.py`). Warning-clean.
- **Vendor-suite inclusion call**: `requires_sendgrid` NOT required — this batch calls `render_and_send` but modifies no SendGrid dispatch code; all sends are monkeypatched in tests. No Telnyx/Stripe/Redis-covered code touched.

#### Files Changed / Created

| File | Action |
|---|---|
| `backend/migrations/versions/2026_09_03_1427-3da9abdfb2f2_team_invite_1_tenant_user_invite_role_.py` | Created — blank migration, DDL-only (role_code column + FK) |
| `backend/app/models/auth.py` | Updated — added `role_code: str \| None` FK field to `TenantUserInvite` |
| `backend/migrations/scripts/data/email_templates/team_invite.json` | Created — team invite email template (category=internal) |
| `backend/migrations/scripts/seed_test_tenant.py` | Updated — added `hashlib` import + pending dev invite seed |
| `backend/README-seed-data.md` | Updated — email_template count 16→17 |
| `backend/api/schemas/team_invites.py` | Created — 6 Pydantic v2 schemas |
| `backend/services/team_invite_service.py` | Created — invite service (create/list/resend/revoke/validate + token helper + typed exceptions) |
| `backend/api/routes/team_invites.py` | Created — 4 authenticated + 1 public + 4 /test endpoints |
| `backend/app/main.py` | Updated — router import + registration |
| `backend/lambda/post_confirmation/handler.py` | Updated — role-at-invite + best-effort usage counter + UP031 fixes |
| `backend/tests/domains/identity_access/test_team_invites.py` | Created — 14 test cases |
| `backend/tests/domains/identity_access/test_post_confirmation_router.py` | Updated — 3 new Lambda Path 2 tests |
| `backend/db_models_map.md` | Regenerated |
| `backend/app_model_imports.md` | Regenerated |
| `backend/openapi.json` | Regenerated |
| `backend/openapi_schema_map.md` | Regenerated |
| `dev-docs/db-design/pilot-db-schema-v2.6h.json` | Updated via schema_manager.py (role_code column + FK) |

#### Tests Added

| Test File | Domain | Tests | All Pass |
|---|---|---|---|
| `tests/domains/identity_access/test_team_invites.py` | `identity_access` | 14 | ✅ |
| `tests/domains/identity_access/test_post_confirmation_router.py` | `identity_access` | +3 (new) | ✅ |
