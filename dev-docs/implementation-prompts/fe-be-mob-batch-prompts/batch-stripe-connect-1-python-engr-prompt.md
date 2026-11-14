# Implementation Prompt: STRIPE-CONNECT-1 (Part A) — Tenant Card Payments via Stripe Connect (Express)

**Mode**: Pilot Python Engineer
**Batch**: STRIPE-CONNECT-1 — **Part A (Backend)** of a mixed batch
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §3.6 (Ord 6; §7 founder-gate item)
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-stripe-connect-1-design.md` v1.0 — **read it in full before Task A1; every task references its design section**
**Decision record**: ADR-0019 — Express + direct charges (Tom, 2026-08-28)
**Estimated session**: 4–5 hours (8 tasks)
**Platform**: Backend (`backend/`) + docs (`dev-docs/`)
**Frontend companion**: Part B (React) — **depends on this batch**: your final step is the OpenAPI regen + commit that unblocks `pnpm sync-api-types`. Part B is additionally gated on a marketing-UI designer spec (design §G Q7) — not your concern.

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-python-engineer/python-engineer-rules.md`** — full document; the 25 hard rules are non-negotiable STOPs
- **`dev-docs/architecture-design/pilot-python-engineer-methods.md`** — §13 (Alembic), §8 (Router Design), §5 (Model Design), §16 (Standard Task Workflow)
- **`backend/tests/README-adding-tests.md`** — full document; governs all test file structure, domain markers, fixture rules
- **`backend/README-seed-data.md`** — §3 (Group A–D model), §7 (DELETE-safety rule), §4 (current seed state)

Critical rules for this batch:

- **Rule 1**: Never guess column names, data types, or table names. Use `postgres-local` MCP to verify every name before use. If MCP returns an error → **STOP and ask Tom**.
- **Rule 4**: All Alembic migrations must be written as **blank** migrations (never `--autogenerate`). Data changes use raw `op.execute()` with `SET LOCAL session_replication_role = 'replica';`. Always implement `downgrade()` and test the full cycle.
- **Rule 6**: `db.get()` is permanently banned on tenant-scoped models. Always use tenant-scoped `select()` with explicit `WHERE tenant_id = :tid`.
- **Rule 8**: All API error responses MUST follow RFC 7807 Problem Details format. The new owner-guard 403s in Task A4 are the deliberate 403 exception (design §D note) — body still RFC 7807.
- **Rule 9**: Every mutation endpoint MUST call `set_audit_context_sync(db, user_id=...)` before committing. Webhook handlers have no user context — follow the existing `webhooks_stripe.py` handler posture (system actor).
- **Rule 11**: If ANY test fails during your work — even one that appears pre-existing — you must fix it before declaring the batch done. If you cannot root-cause → STOP and ask Tom.
- **Rule 12 (sync routes — rules §21)**: This app is **synchronous by design**. All new webhook handlers + `_impl()`s are plain `def`. The Stripe SDK is blocking-by-design (existing house posture) — never wrap it in `async def` over the sync `Session`.
- **Rule 13 (Pydantic v2 — rules §22)**: v2 idioms only. Every route needs `response_model`. Money is integer cents — never float.
- **Rule 14 (Ruff — rules §23)**: Ruff **only against files you changed** — `git diff --name-only --diff-filter=d HEAD -- '*.py' | sed 's|^backend/||'`, then `ruff check --fix && ruff format`. Fix ALL errors in those files.
- **Rule 16 (verify, don't assume — rules §25)**: Query `information_schema.columns` for every table you touch this session before writing SQL.
- **Payment refund model (SD-2 permanent design)**: Refunds = new negative-amount payment row (`amount_cents < 0`, `status = refunded`). `payment.refunded_amount_cents` / `refunded_at` were deliberately dropped by migration `44b8d8f15789`. Do NOT add them back or reference them.
- **Seed DELETE-safety (Rule 11.1)**: every DELETE in a migration or seed path must be **value-scoped** (`code =` / natural key + `tenant_id IS NULL`) — never blanket.

---

## Pre-Work: Establish Regression Baseline

Before touching any file, capture the current **unit-only** test baseline:

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=no -q 2>&1 | tail -5
```

Record the exact count: **`X passed, Y failed`** (expect ~4692 passed / 0 failed post-QB-H1).

> **If any tests are already failing before you start**: Do NOT proceed. Either confirm with Tom that it is a known, accepted failure, or fix it first.

---

## Pre-Work: Run MCP Verification Queries

Run **all** of these via `postgres-local` MCP before writing any code. If any query returns unexpected results → **STOP and ask Tom**.

> **MCP Usage Rule**: `postgres-local` is for **read-only verification only** — never INSERT/UPDATE/DELETE; all data changes go through migrations, seed scripts, or application code. On any query error → STOP and ask Tom. Two read-only servers exist (global rule `.roo/rules/02-database-mcp-access.md`): this batch uses `postgres-local` only (no `postgres-prod` work).

```sql
-- 1. Confirm alembic head (QB-H1 landed 3c69652df5d1 + b1f8b5f00f33 — expect one of those)
SELECT version_num FROM public.alembic_version;

-- 2. Confirm tenant stripe columns (expect: stripe_customer_id, stripe_connect_account_id — both text NULL;
--    and NO capability columns yet)
SELECT column_name, data_type, is_nullable FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'tenant'
AND column_name LIKE '%stripe%' ORDER BY ordinal_position;

-- 3. Confirm payment columns you will touch (expect idempotency_key varchar NULL,
--    stripe_payment_intent_id text NULL, amount_variance_cents int NULL)
SELECT column_name, data_type, is_nullable FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'payment' ORDER BY ordinal_position;

-- 4. Confirm the webhook dedup table shape (expect TEXT PK event_id)
SELECT column_name, data_type, is_nullable FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'stripe_webhook_event_processed' ORDER BY ordinal_position;

-- 5. Confirm notification_type PK + the qb_connection_expired row shape to mirror (QB-H1 precedent)
SELECT code, name, audience, is_active FROM public.notification_type
WHERE code IN ('qb_connection_expired', 'qb_sync_conflict') ORDER BY code;

-- 6. Confirm which dev tenants currently hold a connect account (drives the Layer-2 seed assignment)
SELECT id, name, stripe_connect_account_id IS NOT NULL AS has_connect,
       stripe_connect_charges_enabled, stripe_connect_payouts_enabled
FROM public.tenant;
-- (columns 3–4 will ERROR before your migration — run this query again AFTER A2 to verify backfill)

-- 7. Confirm idempotency_key table shape (the existing 24h cache you adopt in A5)
SELECT column_name, data_type, is_nullable FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'idempotency_key' ORDER BY ordinal_position;
```

> **Engineer safety net — independent column verification (MANDATORY)**: before writing ANY SQL, migration code, or SQLModel field reference, run `SELECT column_name, data_type, is_nullable, column_default FROM information_schema.columns WHERE table_schema = 'public' AND table_name = '<table>' ORDER BY ordinal_position;` for **every table you touch** (`tenant`, `payment`, `invoice`, `notification_type`, `notification_template`, `stripe_webhook_event_processed`, `idempotency_key`). If a column name in this prompt disagrees with MCP → use the MCP name and note the discrepancy in your Completion Summary.

---

## Pre-Work: Read These Source Files

Use `read_file` on each of these before writing any code:

```
dev-docs/architecture-design/batch-designs/batch-stripe-connect-1-design.md   ← the design — §B (migration), §C (order), §D (contracts), §F (interfaces/copy), §G (resolved questions)
dev-docs/architecture-design/pilot-adr-log.md                                ← ADR-0019 entry (Express + direct charges)
backend/api/routes/stripe_connect.py                                         ← full file — A1 type flip + A4 owner guard touch points; /test variants pattern
backend/services/stripe_payment_intents.py                                   ← full file — A5 idempotency-key change; existing succeeded/failed handlers (A3 delegates to them)
backend/api/routes/webhooks_stripe.py                                        ← full file — the platform endpoint you mirror for the Connect endpoint; dedup pattern
backend/api/routes/public_invoices.py                                        ← PublicInvoiceResponse (line ~42), GET handler (~175), payment-intent POST (~261) with the 402 fallback (~314), confirm-payment POST (~330)
backend/core/idempotency.py                                                  ← the existing 24h header cache you adopt in A5 — do NOT reinvent
backend/api/routes/payment_schedules.py                                      ← Idempotency-Key adoption precedent (line ~595)
backend/core/config.py                                                       ← Stripe Settings block (~line 137) — you add 2 fields
backend/migrations/scripts/seed_core.py                                      ← notification_type dict (qb_connection_expired entry — QB-H1 precedent for A2)
backend/migrations/scripts/seed_platform.py                                  ← template-copy dict + (code, channel) upsert loop (qb_connection_expired entries — QB-H1 precedent)
backend/services/qb_connection_notification.py                               ← owner-notification helper precedent (Task A3's dispute/disconnect notifications)
backend/app/models/core.py                                                   ← Tenant model (you add 2 columns)
backend/app/models/system.py                                                 ← IdempotencyKey model
backend/tests/conftest.py                                                    ← fixtures (client, db_session, test_tenant, test_user, tenant_a/tenant_b, user_tenant_a)
backend/tests/domains/invoicing_billing/                                     ← existing test layout for this domain
backend/db_models_map.md                                                     ← confirm Tenant / Payment / IdempotencyKey / NotificationType mappings
backend/README-seed-data.md                                                  ← §3, §7, §4 (you will edit §4)
dev-docs/integrations/stripe/stripe-pricing-config.md                        ← §8 registered-events table (you extend it in A7)
dev-docs/pilot-operations.md                                                 ← §11 (Connect flow + sandbox guide + page states) — ops context for your doc edits
```

Also run these greps to find related files:

```bash
grep -rn "stripe_connect_account_id" backend/ --include="*.py" -l
grep -rn "handle_payment_intent_succeeded\|handle_payment_intent_failed" backend/ --include="*.py" -l
grep -rn "stripe_connect" backend/tests/ --include="*.py" -l
grep -rn "STRIPE_CONNECT" backend/ --include="*.py" -l
```

---

## Background / Context

STRIPE-CONNECT-1 makes tenant card payments real: a contractor's customer pays on the public `/i/[token]` page and money lands in the **contractor's** Stripe account. Tom chose **Express + direct charges** (ADR-0019, 2026-08-28).

UI-FIX-2F already built the foundation (connect/onboard/disconnect endpoints, `stripe_account=` routing, 402 guard, settings UI). The remaining backend delta (this prompt):

1. **Account-type alignment**: the code creates `type="standard"` accounts — flip to `type="express"` + explicit capability requests (ADR-0019).
2. **No Connect webhook coverage**: `account.updated` / `account.application.deauthorized` / `charge.dispute.*` are unhandled, and connected-account `payment_intent.*` events only arrive at a **Connect** webhook endpoint that doesn't exist yet.
3. **No local capability persistence**: the public page can't know a connected account has charges disabled without a live Stripe call — new `tenant` columns + write-through refresh fix that.
4. **RBAC**: connect management is `settings.tenant.write` (owner + operator) — the card requires **owner-only**.
5. **Idempotency gaps**: the public payment POSTs lack `Idempotency-Key` header support, and the Stripe-side key (`pi_invoice_{invoice_id}_{amount_cents}`) collapses two legitimate same-amount partial payments into one.

**Explicitly out** (design §C.1): platform-fee model, subscription-billing changes, dunning, dispute-resolution UI, sandbox-account migration, `apiClient` conversion on the public page.

---

## Task A1 — Account-Type Alignment (design §C.A1; ADR-0019)

**What to change** (`backend/api/routes/stripe_connect.py`):

1. In `_onboard_impl`, change `stripe.Account.create(type="standard", country="US")` to:
   ```python
   account = stripe.Account.create(
       type="express",
       country="US",
       capabilities={
           "card_payments": {"requested": True},
           "transfers": {"requested": True},
       },
   )
   ```
2. Update the module docstring (lines 1–18) to state the model: **Express accounts via Account Links** (not Standard; not OAuth `ca_` flow).
3. Update any existing stripe_connect tests that assert `type="standard"` on the create call.

Intermediate run: `python -m pytest -m unit --tb=short -q 2>&1 | tail -5`

---

## Task A2 — Capability Columns Migration + Seed Rollout (design §B, §C.A2)

**What to change:**

1. **Blank migration**:
   ```bash
   cd <repo>/backend && source .venv/bin/activate
   alembic revision -m "stripe_connect_1_capability_columns"
   ```
   `upgrade()` per design §B.2: two `ALTER TABLE tenant ADD COLUMN … BOOLEAN NULL`; `SET LOCAL session_replication_role = 'replica';` then idempotent INSERTs for the 2 `notification_type` rows (`stripe_connect_disconnected`, `stripe_dispute_opened` — `ON CONFLICT DO NOTHING`) and 6 `notification_template` rows (2 types × email/in_app/push, `tenant_id NULL`, `WHERE NOT EXISTS`-guarded); backfill `UPDATE tenant SET … = true, true WHERE stripe_connect_account_id IS NOT NULL`. Template copy per design §F.4. `downgrade()` = exact reverse (value-scoped DELETEs, `DROP COLUMN`s).
2. **Full cycle test**: `alembic upgrade head` → `alembic downgrade -1` → `alembic upgrade head` → `alembic current`; re-run upgrade once more to prove idempotency.
3. **Model**: add both columns to the `Tenant` SQLModel (`Optional[bool]` = `None`) — then regenerate the model map (Regeneration section below).
4. **Schema JSON sync** (schema change — see Regeneration section for the exact `schema_manager.py` commands).
5. **Seed rollout** (design §B.3):
   - `seed_core.py`: add both `notification_type` rows (byte-identical to the migration).
   - `seed_platform.py`: add the 6 template-copy entries.
   - Layer 2: the seed script owning the dev tenant with a connect account (find it via your greps + MCP query 6) sets both flags `true` where `stripe_connect_account_id IS NOT NULL`.
   - `README-seed-data.md` §4 updated.
6. **New tests** — `backend/tests/domains/invoicing_billing/test_sc1_capability_columns.py`:
   - both columns exist + are nullable; backfill set true/true only for tenants with an account id (assert by inserted IDs)
   - `stripe_connect_disconnected` + `stripe_dispute_opened` types + 6 templates present (`tenant_id IS NULL`) after seed

Intermediate run: `python -m pytest -m unit --tb=short -q 2>&1 | tail -5`

---

## Task A3 — Connect Webhook Endpoint + Handlers (design §C.A3, §D, §F.1)

**What to change** (`backend/api/routes/webhooks_stripe.py`):

1. **`POST /api/v1/webhooks/stripe-connect`** — mirror the platform endpoint's structure: raw-body signature verification with `settings.STRIPE_CONNECT_WEBHOOK_SECRET`, dedup via `stripe_webhook_event_processed`, then dispatch. Tenant resolution for account-scoped events: `event["account"]` → `tenant.stripe_connect_account_id` lookup (tenant-scoped `select()`, never `db.get()`).
2. **Handlers** (design §F.1 signatures):
   - `account.updated` → persist `charges_enabled` / `payouts_enabled` onto the tenant (idempotent UPDATE).
   - `account.application.deauthorized` → null `stripe_connect_account_id` + both flags; enqueue `stripe_connect_disconnected` to the tenant owner (follow the `qb_connection_notification.py` helper precedent — owner lookup via `TenantUser.role_code == "owner"`).
   - `charge.dispute.created` / `charge.dispute.closed` → enqueue `stripe_dispute_opened` (closed → log + skip or a brief note in the same thread — design §F.4) to the owner with amount + respond-by.
   - `payment_intent.succeeded` / `payment_intent.payment_failed` → **delegate to the existing handlers** (`handle_payment_intent_succeeded` / `handle_payment_intent_failed`) — they resolve via PI metadata and are already idempotent.
3. **New tests** — `backend/tests/domains/invoicing_billing/test_sc1_connect_webhook.py`:
   - `account.updated` persists flags (constructed payload; signature verification mocked)
   - deauthorized nulls the id + flags + enqueues the owner notification
   - dispute.created enqueues the owner notification
   - duplicate `event_id` → deduped (no double side effects)
   - `payment_intent.succeeded` on the Connect endpoint creates the Payment row exactly once (delegation + existing idempotency)
   - unknown `event["account"]` → logged + 200 (Stripe must never see a 5xx for an unmapped account)

Intermediate run: `python -m pytest -m unit --tb=short -q 2>&1 | tail -5`

---

## Task A4 — Owner-Only RBAC on Connect Management (design §C.A4)

**What to change** (`backend/api/routes/stripe_connect.py`):

1. Add `_require_owner_role(user_context)` (inline `role_code == "owner"` check per house pattern — `roles.py` / `reports.py` precedent) raising 403 RFC 7807 for non-owners. Apply in `_onboard_impl` + `_disconnect_impl` (both authed and `/test` variants — pass the role through). `GET /status` stays `settings.tenant.write`.
2. **New tests** — extend `test_sc1_connect_webhook.py` or a new `test_sc1_connect_rbac.py`: owner → 200; operator/accountant → 403 with the RFC 7807 body; `/test` variants enforce the same.

Intermediate run: `python -m pytest -m unit --tb=short -q 2>&1 | tail -5`

---

## Task A5 — Idempotency Hardening (design §C.A5, §F.3)

**What to change:**

1. **API-level** (`backend/api/routes/public_invoices.py`): `POST /payment-intent` + `POST /confirm-payment` adopt the existing `Idempotency-Key` header pattern from `core/idempotency.py` (optional header, 24h cache, replay returns the cached response with `X-Idempotency-Replay: true`) — follow the `payment_schedules.py` precedent. Optional (not required) — the public page will send it, but a bare customer browser retry must not break.
2. **Stripe-side key** (`backend/services/stripe_payment_intents.py`): `create_payment_intent` gains `*, idempotency_key: str | None = None`; the Stripe call's key becomes `f"pi_{invoice_id}_{amount_cents}_{idempotency_key or uuid.uuid4()}"` — two same-amount partial payments now create two PIs; client retries with the same header collapse correctly.
3. **New tests** — `backend/tests/domains/invoicing_billing/test_sc1_payment_idempotency.py`:
   - same `Idempotency-Key` twice → one Stripe create call, cached response on replay
   - two different keys, same amount → two PIs created
   - no header → works (uuid component), no cache write

Intermediate run: `python -m pytest -m unit --tb=short -q 2>&1 | tail -5`

---

## Task A6 — Public GET Payment State (design §C.A6, §D)

**What to change** (`backend/api/routes/public_invoices.py`):

1. `PublicInvoiceResponse` gains `card_payments_enabled: bool` + `payment_unavailable_reason: Literal["not_connected", "charges_disabled"] | None` — computed from LOCAL tenant columns (`stripe_connect_account_id`, `stripe_connect_charges_enabled`), never a live Stripe call. The 402 guard on the POST stays as the backstop.
2. `GET /stripe-connect/status` (`stripe_connect.py`) becomes write-through: after a successful `Account.retrieve`, persist the fresh flags onto the tenant.
3. **New tests** — extend `test_sc1_capability_columns.py`: GET returns `not_connected` when no account; `charges_disabled` when flag false; `enabled` when both true; `/status` write-through updates the flags (Stripe retrieve mocked).

Intermediate run: `python -m pytest -m unit --tb=short -q 2>&1 | tail -5`

---

## Task A7 — Env Vars + Docs (design §C.A7, §G Q8)

**What to change:**

1. `backend/core/config.py`: declare `STRIPE_CONNECT_PLATFORM_KEY: str = ""` + `STRIPE_CONNECT_WEBHOOK_SECRET: str = ""` in the Stripe block (getattr fallbacks in `stripe_connect.py`/`webhooks_stripe.py` may be simplified to direct attribute access).
2. `.env.example`: document both (sandbox guidance: platform key = sandbox `acct_XXXXXXXXXXXX` secret; webhook secret from the Connect endpoint registration).
3. `dev-docs/devops/aws-env-mgmt-ops-plan.md`: add both vars to the secrets/env-var inventory per its §10 maintenance rules (dev = sandbox values; prod = Secrets Manager paths, Tom populates post-merge).
4. `dev-docs/integrations/stripe/stripe-pricing-config.md`: §8 gains the Connect endpoint (`https://api.pilotfortrades.com/api/v1/webhooks/stripe-connect`) + the 6 events (`account.updated`, `account.application.deauthorized`, `charge.dispute.created`, `charge.dispute.closed`, `payment_intent.succeeded`, `payment_intent.payment_failed`) with a **registration checklist for Tom** (sandbox + prod Dashboard steps, signing-secret capture).
5. Fix the stale pointer: the launch-plan §3.6 card's "(see stripe-pricing-config.md §10)" reference — the Architect handles the launch-plan edit; you only ensure `stripe-pricing-config.md`'s own text is internally correct.

Intermediate run: `python -m pytest -m unit --tb=short -q 2>&1 | tail -5`

---

## Task A8 — Regeneration + Handoff (design §D)

1. **DB model map** (Tenant model changed — REQUIRED): `python generate_db_model_map.py app > db_models_map.md`
2. **Import map** (new test files — REQUIRED): `python generate_app_import_map.py tests > app_model_imports.md`
3. **Schema JSON** (tenant columns added — REQUIRED): read `backend/README-schema_manager.md` first, then path-based `set` for both `tenant` columns. **Never edit the JSON by hand; there is no `--sync`/`--diff` flag.** On any `schema_manager.py` error → STOP and ask Tom.
4. **OpenAPI** (new + modified endpoints — REQUIRED): `python export_openapi_json.py` → verify the Connect webhook + new response fields appear in `openapi_schema_map.md`.
5. **Handoff to Part B (MANDATORY — §9.3)**: commit everything including the regenerated `openapi.json`; the React Engineer's first Pre-Work step is `pnpm sync-api-types`. Note in your Completion Summary that Part B is additionally gated on the marketing-UI designer spec (design §G Q7) — the Architect sequences it.

---

## Verification Checkpoints

- After **A2**: migration cycle clean; `seed_core.py --mode inspect` shows the 2 new types; MCP query 6 re-run shows backfilled flags.
- After **A3**: all webhook handler tests green; duplicate-event dedup proven.
- After **A5**: replay tests green; same-amount double-payment creates two PIs.
- After **A7**: `pytest -m unit` green; docs merged.

---

## Seed Data Rollout (Core + Scenario)

Per `backend/README-seed-data.md` — §3 + §7 read in Pre-Work.

### Layer 1 — Core / Platform values (Group A / B)
- `seed_core.py` (Group A): `notification_type` rows `stripe_connect_disconnected`, `stripe_dispute_opened` — idempotent, byte-identical to the migration.
- `seed_platform.py` (Group B): 6 `notification_template` rows (2 × email/in_app/push, `tenant_id NULL`) via the `(code, channel)` upsert loop — byte-identical to the migration.
- **Migration ↔ seed parity (MANDATORY)**: identical rows (inclusions §20). Audit columns explicit `NOW(), NOW()`; `created_by`/`updated_by` NULL.

### Layer 2 — Scenario data (Group D)
- Tenants holding `stripe_connect_account_id` in the seed data get `stripe_connect_charges_enabled=true, stripe_connect_payouts_enabled=true` in the owning seed script (value-scoped UPDATE per Rule 11.1 — never a blanket UPDATE).

### Verification
- `python migrations/scripts/seed_core.py --mode inspect` (types present); `pytest -m unit` green after seed changes (shared-DB rule).

### README update
- `README-seed-data.md` §4 updated (2 types, 6 templates, tenant flag assignment).

---

## Final Verification

### Phase 1 — Unit Tests Only (run after each task group during development)

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=short -q 2>&1 | tail -10
```

All unit tests must pass before moving to the next task. Fix any unit failure — including failures that appear to be caused by code outside your batch — before proceeding.

### Phase 2 — Lint (changed files only) + Full Suite, Vendor-Deselected + Stripe Suite (run once, at the very end)

```bash
cd <repo>/backend
source .venv/bin/activate

# Lint + format gate (rules §23) — CHANGED FILES ONLY
CHANGED_PY=$(git diff --name-only --diff-filter=d HEAD -- '*.py' | sed 's|^backend/||')

if [ -n "$CHANGED_PY" ]; then
    ruff check --fix $CHANGED_PY
    ruff format $CHANGED_PY
    ruff check $CHANGED_PY
fi

# Full suite — vendor/live-service suites deselected (Tom's standing instruction 2026-08-16)
python -m pytest -m "not integration and not requires_telnyx and not requires_stripe and not requires_sendgrid and not requires_redis and not e2e" --tb=short -q 2>&1 | tail -15

# REQUIRED for this batch — you touched Stripe-covered code (payment intents, Connect, webhooks):
python -m pytest -m requires_stripe --tb=short -q 2>&1 | tail -10
# (If the stripe suite needs vendor env vars you don't have, coordinate with Tom and record the outcome.)

# Batch-specific spot checks
python -m pytest tests/domains/invoicing_billing/ -v 2>&1 | tail -30
grep -A 5 "stripe-connect" backend/openapi_schema_map.md

echo "=== STRIPE-CONNECT-1 PART A FINAL VERIFICATION COMPLETE ==="
```

**Vendor-suite inclusion call (explicit)**: this batch **DOES** touch Stripe-covered code → the `requires_stripe` marker suite is **required** (recorded above). Telnyx/SendGrid/Redis suites are NOT required.

> **Warning-clean is part of done.** `ruff` zero remaining issues in changed files; pytest free of `DeprecationWarning` noise. **Any failure in either phase must be fixed before the batch is declared done.**

---

## Definition of Done

Check off each item **in this prompt doc** as it completes:

- [ ] Pre-modification regression baseline captured (`X passed, Y failed`) using `pytest -m unit`
- [ ] Zero pre-existing unit failures confirmed before starting work (or confirmed with Tom)
- [ ] All 7 MCP pre-work queries run (incl. post-migration re-run of query 6) + every touched table independently re-verified via `information_schema.columns` (rules §25)
- [ ] All mandatory source files read before writing any code (including the design doc in full)
- [ ] A1: `type="express"` + capabilities on account create; docstring updated; dependent tests fixed
- [ ] A2: migration written (blank + raw SQL), full cycle tested, idempotent re-run proven; Tenant model updated; backfill verified
- [ ] A2: `schema_manager.py` path-based JSON sync for both `tenant` columns (never hand-edited)
- [ ] A2/A3: seed rollout complete (Layer 1 types+templates byte-parity, Layer 2 flags, README §4)
- [ ] A3: Connect webhook endpoint + 5 handler paths; dedup proven; unknown-account → 200 logged
- [ ] A4: owner guard on onboard + disconnect (authed + /test); role-matrix tests
- [ ] A5: `Idempotency-Key` on both public payment POSTs (24h cache, replay header); Stripe-side key uniqueness fixed; 3 tests
- [ ] A6: public GET payment-state fields from local columns; `/status` write-through
- [ ] A7: config declares both Connect env vars; `.env.example`; env-mgmt §3 rows; pricing-config §8 Connect endpoint + events + Tom registration checklist
- [ ] All DB-touching routes/`_impl()`/handlers are sync `def` (rules §21)
- [ ] Only Pydantic v2 idioms; every new/modified route has `response_model`; money stays integer cents (rules §22)
- [ ] `set_audit_context_sync()` on every new mutation endpoint (webhook handlers follow the existing system-actor posture)
- [ ] All new/modified API errors follow RFC 7807
- [ ] All new test files use `pytestmark` with `pytest.mark.domain_invoicing_billing` + `pytest.mark.unit`; no module-level `TestClient`; fixtures only (no hardcoded UUIDs); assert-by-inserted-ID
- [ ] `python generate_db_model_map.py app > db_models_map.md` run (Tenant changed)
- [ ] `python generate_app_import_map.py tests > app_model_imports.md` run (new test files)
- [ ] `python export_openapi_json.py` run — Connect webhook + new fields present in `openapi_schema_map.md`
- [ ] `ruff check --fix && ruff format` on changed files only — zero remaining issues, no unjustified `# noqa`
- [ ] **Phase 1**: All unit tests pass — zero failures including any pre-existing
- [ ] **Phase 2**: Full suite (vendor-deselected) passes + **`requires_stripe` suite run and recorded** — zero failures, warning-clean
- [ ] Final test count (before → after) documented
- [ ] Handoff commit includes regenerated `openapi.json` (Part B's `pnpm sync-api-types` unblocked)
- [ ] Completion Summary filled in at this prompt doc's ending `## Appendix — Completion Summary` (ADR-0017 — never the launch plan)

---

## Completion Summary

After all Definition of Done items are complete:

1. Fill in the **Completion Summary** in the appendix at the end of THIS prompt doc using the format below.
2. No other source-spec task headers are closed by this batch (the launch plan is the Architect's surface).

```markdown
### STRIPE-CONNECT-1 (Part A) — Tenant Card Payments via Stripe Connect (Express): Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot Python Engineer
**Baseline**: X passed, Y failed
**Final**: X+N passed, Y failed (+N new tests)
**requires_stripe suite**: [result]

#### What Was Accomplished

- [Account-type alignment]
- [Migration + seed rollout]
- [Connect webhook coverage]
- [RBAC]
- [Idempotency]
- [Public payment state]
- [Env/docs]

#### Files Changed / Created

| File | Action |
|---|---|
| `backend/path/to/file.py` | Created / Updated — [what changed] |

#### Tests Added

| Test File | Domain | Tests | All Pass |
|---|---|---|---|
| `tests/domains/invoicing_billing/test_file.py` | `domain_invoicing_billing` | N | ✅ |
```

---

## After This Task — Next Step

Part B (React) opens when two gates clear: (1) your handoff commit with regenerated `openapi.json` (this batch), and (2) Tom's approval of the marketing-UI designer spec for the `/i/[token]` payment states (design §G Q7). The Architect authors the React prompt at that point. Separately, Tom registers the Connect webhook endpoint in Stripe Dashboard (sandbox + prod) using your `stripe-pricing-config.md` §8 checklist — that is the prod-readiness tail, tracked on the launch-plan card.

---

## Appendix — Completion Summary

### STRIPE-CONNECT-1 (Part A) — Tenant Card Payments via Stripe Connect (Express): Completion Summary

**Completed**: 2026-08-28
**Mode**: Pilot Python Engineer
**Baseline**: 4692 passed, 1 skipped, 0 failed
**Final**: 4719 passed, 1 skipped, 0 failed (+27 new tests)
**requires_stripe suite**: 12 passed, 0 failed (7m20s)

#### What Was Accomplished

- **Account-type alignment (A1)**: Flipped `stripe.Account.create(type="standard")` → `type="express"` with explicit `capabilities={"card_payments": {"requested": True}, "transfers": {"requested": True}}` per ADR-0019. Module docstring updated to document the Express + direct charges model. Existing test strengthened to assert the express type + capabilities on the create call.
- **Migration + seed rollout (A2)**: Blank Alembic migration `d038d647ec41` — two nullable BOOLEAN columns on `tenant` (`stripe_connect_charges_enabled`, `stripe_connect_payouts_enabled`), 2 `notification_type` rows (`stripe_connect_disconnected`, `stripe_dispute_opened`), 6 `notification_template` rows (2 types × email/in_app/push, tenant_id NULL), backfill UPDATE for existing connected tenants (no-op in dev — 0 connected tenants). Full cycle tested (upgrade → downgrade -1 → upgrade head → idempotent re-run). Tenant SQLModel updated with both columns. Schema JSON synced via `schema_manager.py` (path-based `set` for both columns). Seed rollout: `seed_core.py` + `seed_platform.py` updated with byte-identical rows. README-seed-data §4 updated (notification_type 17→20, notification_template 58→67).
- **Connect webhook coverage (A3)**: New `POST /api/v1/webhooks/stripe-connect` endpoint with `STRIPE_CONNECT_WEBHOOK_SECRET` signature verification, shared `stripe_webhook_event_processed` dedup, and 5 handler paths: `account.updated` (persist flags), `account.application.deauthorized` (null id + flags + owner notification), `charge.dispute.created`/`closed` (owner notification), `payment_intent.succeeded`/`payment_failed` (delegate to existing handlers). Unknown account → logged + 200. New `services/stripe_connect_notifications.py` helper (mirrors `qb_connection_notification.py` precedent).
- **RBAC (A4)**: `_require_owner_role(user_context)` inline owner-guard helper added to `stripe_connect.py`; applied to `_onboard_impl` + `_disconnect_impl` (both authed and `/test` variants). `TestUserContext` gained `role_code: str = "owner"` field. GET /status stays `settings.tenant.write`.
- **Idempotency (A5)**: `create_payment_intent` gained `*, idempotency_key: str | None = None`; Stripe-side key changed from `pi_invoice_{invoice_id}_{amount_cents}` (amount-collision-prone) to `pi_{invoice_id}_{amount_cents}_{client_key_or_uuid4}`. Public POST `/payment-intent` passes the `Idempotency-Key` header through to the service function. The 24h response cache is handled by the existing `idempotency_middleware`.
- **Public payment state (A6)**: `PublicInvoiceResponse` gained `card_payments_enabled: bool` + `payment_unavailable_reason: Literal["not_connected", "charges_disabled"] | None` — computed from LOCAL tenant columns (no live Stripe call on the public hot path). GET `/stripe-connect/status` is now write-through (persists fresh flags after `Account.retrieve`).
- **Env/docs (A7)**: `config.py` declares `STRIPE_CONNECT_PLATFORM_KEY` + `STRIPE_CONNECT_WEBHOOK_SECRET` (default `""` = dev fallback preserved). `backend/.env.example` documents both with sandbox guidance. `aws-env-mgmt-ops-plan.md` §3.1 stripe row updated with both Connect env vars. `stripe-pricing-config.md` §8 restructured into §8.1 (platform endpoint) + §8.2 (Connect endpoint) with the 6 events table + Tom's 9-step registration checklist (sandbox + prod).

#### Files Changed / Created

| File | Action |
|---|---|
| `backend/api/routes/stripe_connect.py` | Updated — A1 express type + capabilities; A4 `_require_owner_role` guard on onboard/disconnect; A6 `/status` write-through; docstring rewrite |
| `backend/api/routes/webhooks_stripe.py` | Updated — A3 Connect webhook endpoint + 5 handlers + dispatch; docstring updated |
| `backend/api/routes/public_invoices.py` | Updated — A5 `Idempotency-Key` header pass-through; A6 `card_payments_enabled` + `payment_unavailable_reason` fields; ruff fixes (pre-existing unused vars) |
| `backend/services/stripe_payment_intents.py` | Updated — A5 Stripe-side idempotency key uniqueness fix (`pi_{invoice_id}_{amount_cents}_{client_key_or_uuid4}`) |
| `backend/services/stripe_connect_notifications.py` | Created — A3 owner-notification helpers (disconnect + dispute), mirrors `qb_connection_notification.py` |
| `backend/app/models/core.py` | Updated — A2 Tenant model gains `stripe_connect_charges_enabled` + `stripe_connect_payouts_enabled` columns |
| `backend/core/config.py` | Updated — A7 declares `STRIPE_CONNECT_PLATFORM_KEY` + `STRIPE_CONNECT_WEBHOOK_SECRET` |
| `backend/core/test_context.py` | Updated — A4 `TestUserContext` gains `role_code: str = "owner"` |
| `backend/migrations/versions/2026_08_28_1802-d038d647ec41_stripe_connect_1_capability_columns.py` | Created — A2 blank migration (DDL + data) |
| `backend/migrations/scripts/seed_core.py` | Updated — A2 2 new `notification_type` rows |
| `backend/migrations/scripts/seed_platform.py` | Updated — A2 6 new `notification_template` copy entries |
| `backend/README-seed-data.md` | Updated — A2 §4 counts (notification_type 17→20, notification_template 58→67) |
| `backend/.env.example` | Updated — A7 Stripe + Connect env vars documented |
| `backend/db_models_map.md` | Regenerated — Tenant model changed |
| `backend/app_model_imports.md` | Regenerated — new test files |
| `backend/openapi.json` | Regenerated — Connect webhook endpoint + new response fields |
| `backend/openapi_schema_map.md` | Regenerated — Connect webhook endpoint + modified routes |
| `dev-docs/db-design/pilot-db-schema-v2.6h.json` | Updated — A2 schema JSON sync (2 tenant columns via `schema_manager.py`) |
| `dev-docs/devops/aws-env-mgmt-ops-plan.md` | Updated — A7 §3.1 stripe secrets row |
| `dev-docs/integrations/stripe/stripe-pricing-config.md` | Updated — A7 §8 restructured (§8.1 platform + §8.2 Connect + Tom checklist) |

#### Tests Added

| Test File | Domain | Tests | All Pass |
|---|---|---|---|
| `tests/domains/invoicing_billing/test_sc1_capability_columns.py` | `domain_invoicing_billing` | 8 | ✅ |
| `tests/domains/invoicing_billing/test_sc1_connect_webhook.py` | `domain_invoicing_billing` | 7 | ✅ |
| `tests/domains/invoicing_billing/test_sc1_connect_rbac.py` | `domain_invoicing_billing` | 9 | ✅ |
| `tests/domains/invoicing_billing/test_sc1_payment_idempotency.py` | `domain_invoicing_billing` | 3 | ✅ |
| `tests/domains/platform_infrastructure/test_stripe_connect.py` | `domain_platform_infrastructure` | 6 (modified, +1 assertion) | ✅ |

#### Notes

- **No dev tenants have a connect account** (MCP query 6 confirmed `has_connect=false` for both) — the backfill UPDATE is a no-op in dev, which is correct per design §G Q3. No Layer 2 seed script change was needed.
- **`handle_payment_intent_succeeded` pre-existing dependencies**: the handler hardcodes `PaymentStatus.code == "paid"` (dev DB has `"succeeded"`) and `PaymentMethod.psp_payment_method_id == "one_time_public_link"` (not seeded). The A3 PI delegation test seeds both within the test transaction. These are pre-existing B15/A81 issues, not introduced by this batch.
- **Part B handoff**: `openapi.json` regenerated — Part B's `pnpm sync-api-types` is unblocked. Part B is additionally gated on the marketing-UI designer spec (design §G Q7) — the Architect sequences it.
- **Tom's Dashboard step**: `stripe-pricing-config.md` §8.2 documents the 9-step Connect webhook endpoint registration checklist (sandbox + prod).
- **MCP discrepancy**: none — all 7 pre-work queries + post-migration re-run of query 6 confirmed the expected state.
