# Implementation Prompt: STRIPE-CONNECT-1-B2 — Billing-Contact Fields (Part A Addendum A9)

**Mode**: Pilot Python Engineer
**Batch**: STRIPE-CONNECT-1-B2 (Part A addendum — design doc v1.1 §B.4, §C A9, §D, §G Q9)
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §3.6
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-stripe-connect-1-design.md` **v1.1** — read §B.4, §C (A9 row), §D (v1.1 rows), §G Q9
**Driver**: `mkt-stripe-connect-1-design-spec.md` §12.1 — the Part C `ManualPaymentPanel` needs contractor phone/email on the 200 GET; Part A shipped the payment-state flags only
**Estimated session**: 1.5–2.5 hours (small addendum)
**Platform**: Backend only (`backend/`)
**Frontend companion**: **STRIPE-CONNECT-1-C (React)** — gated on this batch's OpenAPI regen (`pnpm sync-api-types` is the handoff signal)

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-python-engineer/python-engineer-rules.md`** — full document; the 25 hard rules are non-negotiable STOPs
- **`dev-docs/architecture-design/pilot-python-engineer-methods.md`** — §13 (Alembic), §8 (Router Design), §5 (Model Design), §16 (Standard Task Workflow)
- **`backend/tests/README-adding-tests.md`** — full document; governs all test file structure, domain markers, and fixture rules

Critical rules for this batch:

- **Rule 1**: Never guess column names, data types, or table names. Use `postgres-local` MCP to verify every name before use. If MCP returns an error → **STOP and ask Tom**.
- **Rule 2**: After any model file change → regenerate `backend/db_models_map.md` via `python generate_db_model_map.py app > db_models_map.md`.
- **Rule 3**: After any endpoint change → run `python export_openapi_json.py` (updates both `openapi.json` and `openapi_schema_map.md`).
- **Rule 4**: All Alembic migrations must be written as **blank** migrations (never `--autogenerate`). Data changes use raw `op.execute()` with `SET LOCAL session_replication_role = 'replica';`.
- **Rule 6**: `db.get()` is permanently banned on tenant-scoped models. Always use tenant-scoped `select()` with an explicit `WHERE tenant_id = :tid` clause.
- **Rule 8**: All API error responses MUST follow RFC 7807 Problem Details format. Non-standard error shapes break the frontend `<NotificationBanner>` severity routing.
- **Rule 9**: Every mutation endpoint MUST call `set_audit_context_sync(db, user_id=user.id)` before committing.
- **Rule 11**: If ANY test fails during your work — even one that appears pre-existing — you must fix it before declaring the batch done.
- **Rule 12 (sync routes)**: This app is **synchronous by design**. Every DB-touching route and `_impl()` is a plain `def`. **Never convert a handler that touches the sync `Session` to `async def`.**
- **Rule 13 (Pydantic v2)**: v2 idioms only (`ConfigDict`, `@field_validator`, `.model_dump()`). Every route needs `response_model`.
- **Rule 14 (Ruff)**: Run ruff **only against the files you changed** (`git diff --name-only HEAD -- '*.py'`). Fix ALL errors in those files.
- **Rule 16 (verify, don't assume)**: 186 tables exist. Query `information_schema.columns` for every table you touch this session before writing SQL.

---

## Pre-Work: Establish Regression Baseline

Before touching any file, capture the current **unit-only** test baseline:

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=no -q 2>&1 | tail -5
```

Record the exact count: **`X passed, Y failed`** (Part A closed at 4719 passed / 0 failed — expect ≈ that).

> **If any tests are already failing before you start**: Do NOT treat them as "pre-existing" and proceed anyway. Confirm with Tom or fix first. You may NOT start implementation work while tests are in an unexplained failed state.

---

## Pre-Work: Run MCP Verification Queries

> **MCP Usage Rule**: The `postgres-local` MCP is for **read-only verification only**. Never use it to INSERT, UPDATE, or DELETE — all data changes go through application code, seed scripts, or Alembic migrations. If a query fails or returns an error → STOP and ask Tom before proceeding.
>
> **Two read-only MCP servers exist** (global rule `.roo/rules/02-database-mcp-access.md`): **`postgres-local`** is the default. **`postgres-prod`** requires Tom's SSH tunnel — not needed for this batch.

Run **all** of these via `postgres-local` MCP before writing any code. If any query returns unexpected results → **STOP and ask Tom**.

```sql
-- 1. Confirm the two billing-contact columns do NOT yet exist on tenant (this batch adds them),
--    and re-verify the exact existing column set you will reference (Architect-verified 2026-08-29 —
--    you re-verify independently per the engineer safety net).
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'tenant'
ORDER BY ordinal_position;
-- EXPECT: stripe_connect_charges_enabled + stripe_connect_payouts_enabled present (Part A);
--         billing_contact_phone / billing_contact_email ABSENT.

-- 2. Confirm the current alembic head (Part A's migration — your new migration's down_revision).
SELECT version_num FROM public.alembic_version;
-- EXPECT: d038d647ec41 (Architect-verified 2026-08-29). If different, use the returned head
--         as down_revision and note the discrepancy in your Completion Summary.

-- 3. Confirm the dev tenant row you will seed (returns one row; note current values).
SELECT id, name, stripe_connect_account_id, billing_contact_phone, billing_contact_email
FROM public.tenant
WHERE id = '00000000-0000-0000-0000-000000000001';
-- NOTE: this query will ERROR before your migration lands (columns don't exist) — if it errors,
--       that CONFIRMS expectation #1. Re-run after Task 1 to confirm NULL defaults.

-- 4. Confirm no payment-contact route already exists (belt-and-braces).
SELECT proname FROM pg_proc WHERE proname ILIKE '%payment_contact%';
-- EXPECT: 0 rows (route-level check happens in code grep below — no DB object expected).
```

---

## Pre-Work: Read These Source Files

Use `read_file` on each of these before writing any code:

```
backend/app/models/core.py                              ← Tenant SQLModel class — where the two new fields go (near the stripe_connect_* fields added by Part A)
backend/api/routes/public_invoices.py                   ← PublicInvoiceResponse (line ~49) + the GET /invoices/{signed_token} handler — where tenant_phone/tenant_email populate from
backend/api/routes/stripe_connect.py                    ← house patterns for this exact surface: require_permission("settings.tenant.write"), RFC 7807 raises, sync def, _impl split
backend/core/idempotency.py                             ← the 24h Idempotency-Key stack Part A adopted on the public payment POSTs (A5) — adopt the same dependency/decorator on the new PATCH
backend/api/routes/payment_schedules.py                 ← established Idempotency-Key adopter precedent (header pattern)
backend/app/main.py                                     ← router registration (stripe_connect.router is registered at prefix /api/v1/settings/billing, ~line 426) — your new router registers at the same prefix
backend/migrations/versions/<part-A-d038d647ec41 file>  ← most recent migration — blank-migration pattern reference + confirm down_revision chain
backend/migrations/scripts/seed_test_tenant.py          ← dev-tenant seed — the UPDATE public.tenant block (~line 307) is where the billing-contact seed values go
backend/tests/conftest.py                               ← available fixtures (do not re-declare)
backend/db_models_map.md                                ← confirm Tenant mapping before/after your model change
backend/README-seed-data.md                             ← §3 (Group A–D model), §6 (run order), §7 (DELETE safety rule) — before editing any seed script
backend/README-schema_manager.md                        ← path-based CRUD reference — before your first schema_manager mutation
```

Also run these to locate related files:

```bash
grep -rn "billing_contact" backend/ --include="*.py" -l        # EXPECT: no hits (new fields)
grep -n "tenant_name" backend/api/routes/public_invoices.py    # locate where the GET response is assembled
grep -rn "stripe-connect/status" backend/api/routes/stripe_connect.py  # confirm sibling endpoint pattern
```

---

## Background / Context

The STRIPE-CONNECT-1 Part B designer spec (Tom-approved 2026-08-29) renders a `ManualPaymentPanel` on the public invoice page (`/i/[token]`) when `card_payments_enabled` is false. The panel shows the contractor's phone + email so their customer can arrange payment (`pilot-operations.md §11.2`). Part A (✅ 2026-08-28) shipped `card_payments_enabled` / `payment_unavailable_reason` on the 200 GET but **no contact fields** — the panel has no data source.

**Decision (design doc §G Q9 — do not re-litigate):**

| Decision | Outcome |
|---|---|
| Storage | `tenant.billing_contact_phone TEXT NULL` + `tenant.billing_contact_email TEXT NULL` (option a — two nullable columns; NO new table; `tenant_email_branding` was MCP-verified to have no contact fields and is email-branding-scoped) |
| Fallback chain | **None** — never implicitly publish the owner user's personal phone/email on a public money page. Both-null is a valid state (the frontend renders a fallback line) |
| Public response naming | 200 GET ships `tenant_phone` / `tenant_email` (public-contract semantics); storage keeps `billing_contact_*` |
| Settings API | New router: `GET` + `PATCH /api/v1/settings/billing/payment-contact`, RBAC `settings.tenant.write` (consistent with the sibling Connect endpoints; NOT owner-only) |
| Seed | Dev tenant `…0001` gains realistic values in `seed_test_tenant.py` (Layer 2 only — these are per-tenant business data, not core/platform lookup values) |

**Cost impact**: $0 — no new AWS resources.

---

## Task 1 — Alembic Migration `stripe_connect_1_billing_contact`

Per `pilot-python-engineer-methods.md` §13 — blank migration, full-cycle tested.

```bash
cd <repo>/backend && source .venv/bin/activate
alembic revision -m "stripe_connect_1_billing_contact"
```

`upgrade()` — two nullable columns (no NOT NULL → 3-part pattern NOT required; no backfill — null = "contractor hasn't entered it"):

```python
def upgrade() -> None:
    op.execute("SET LOCAL session_replication_role = 'replica';")
    op.execute("ALTER TABLE tenant ADD COLUMN billing_contact_phone TEXT NULL;")
    op.execute("ALTER TABLE tenant ADD COLUMN billing_contact_email TEXT NULL;")


def downgrade() -> None:
    op.execute("SET LOCAL session_replication_role = 'replica';")
    op.execute("ALTER TABLE tenant DROP COLUMN IF EXISTS billing_contact_email;")
    op.execute("ALTER TABLE tenant DROP COLUMN IF EXISTS billing_contact_phone;")
```

Set `down_revision` to the head confirmed in MCP query #2 (`d038d647ec41` expected).

**Full-cycle test (mandatory):**

```bash
alembic upgrade head
alembic downgrade -1
alembic upgrade head
alembic current   # must show your new revision
```

Re-run MCP query #3 — both columns present, NULL.

---

## Task 2 — Tenant Model Fields + Regenerations

1. In `backend/app/models/core.py`, add to the `Tenant` class (adjacent to the Part A `stripe_connect_charges_enabled` / `stripe_connect_payouts_enabled` fields):

```python
    billing_contact_phone: str | None = Field(default=None)
    billing_contact_email: str | None = Field(default=None)
```

(Read the file first — match the exact Field/sa_column style the neighboring stripe_connect_* fields use.)

2. Regenerate the model map (Rule 2):

```bash
python generate_db_model_map.py app > db_models_map.md
grep "billing_contact" db_models_map.md   # confirm both fields appear under Tenant
```

3. Schema JSON sync — **read `README-schema_manager.md` first**; path-based CRUD only; never edit the JSON by hand:

```bash
cat << 'EOF' > temp_payload.json
{ "type": "text", "nullable": true, "description": "Contractor-entered billing contact phone shown to customers on the public invoice manual-payment panel (STRIPE-CONNECT-1-B2)." }
EOF
python schema_manager.py set --path tables.tenant.columns.billing_contact_phone --payload temp_payload.json
cat << 'EOF' > temp_payload.json
{ "type": "text", "nullable": true, "description": "Contractor-entered billing contact email shown to customers on the public invoice manual-payment panel (STRIPE-CONNECT-1-B2)." }
EOF
python schema_manager.py set --path tables.tenant.columns.billing_contact_email --payload temp_payload.json
rm temp_payload.json
```

(Verify the exact payload shape against a neighboring nullable text column first: `python schema_manager.py get --path tables.tenant.columns.stripe_connect_account_id` — mirror its keys.)

Intermediate gate: `python -m pytest -m unit --tb=short -q 2>&1 | tail -5`

---

## Task 3 — Settings Payment-Contact Router (GET + PATCH)

Create **`backend/api/routes/billing_payment_contact.py`** — a new small router (mirrors the `tenant_email_branding.py` single-surface precedent; do NOT bolt this onto `stripe_connect.py` — its module docstring and cohesion are Connect-scoped).

**Endpoints** (both sync `def`, both `require_permission("settings.tenant.write")`, both RFC 7807 errors):

| Path | Method | Request → Response | Notes |
|---|---|---|---|
| `/payment-contact` | GET | → `PaymentContactResponse` | Hydrates the settings form |
| `/payment-contact` | PATCH | `PaymentContactUpdateRequest` + `Idempotency-Key` header → `PaymentContactResponse` | 24h idempotency cache via `core/idempotency.py` (Part A A5 precedent) |

**Schemas** (Pydantic v2, in the route file or `api/schemas/` per the house convention you find in sibling files):

```python
class PaymentContactResponse(BaseModel):
    billing_contact_phone: str | None
    billing_contact_email: str | None


class PaymentContactUpdateRequest(BaseModel):
    billing_contact_phone: str | None = Field(default=None, max_length=32)
    billing_contact_email: EmailStr | None = None
```

**Semantics — read carefully:**
- **Partial update via `model_fields_set`**: omitted field = unchanged; explicit `null` = cleared. (`"billing_contact_phone" in body.model_fields_set` distinguishes the two.)
- **Phone**: store as-entered after `strip()` (contractors write `(804) 555-0142` — no E.164 coercion); empty-string-after-strip → store `None`. `max_length=32` sanity cap.
- **Email**: `EmailStr` validation; 422 RFC 7807 on invalid (`type: https://errors.pilotfortrades.com/validation-error`).
- **Tenant resolution**: tenant-scoped `select(Tenant).where(Tenant.id == current_user.tenant_id)` (Rule 6 — never `db.get()`); 404 RFC 7807 if somehow absent.
- **Audit**: `set_audit_context_sync(db, user_id=current_user.id)` before the commit (Rule 9).
- **Idempotency**: adopt the same `Idempotency-Key` header pattern Part A put on the public payment POSTs — read `core/idempotency.py` + the A5 usage in `public_invoices.py` and replicate (24h cache; replay returns the cached response). PATCH is naturally idempotent for identical payloads; the header protects the mobile/offline retry path per infra-constraints §5.

**Register in `backend/app/main.py`** at the same prefix as `stripe_connect.router` (`/api/v1/settings/billing`, ~line 426) — the full path becomes `/api/v1/settings/billing/payment-contact`. Add the import next to the `stripe_connect` import.

Intermediate gate: `python -m pytest -m unit --tb=short -q 2>&1 | tail -5`

---

## Task 4 — Public GET Gains `tenant_phone` / `tenant_email`

In `backend/api/routes/public_invoices.py`:

1. `PublicInvoiceResponse` gains:

```python
    # STRIPE-CONNECT-1-B2: contractor-entered billing contact for the
    # manual-payment panel (null = not entered — frontend renders fallback line).
    tenant_phone: str | None = None
    tenant_email: str | None = None
```

2. In the GET `/invoices/{signed_token}` handler, populate both from the already-loaded tenant's `billing_contact_phone` / `billing_contact_email` (None-safe; no extra query if the tenant row is already in hand — read the handler first). **No live Stripe call, no owner-user fallback — by design (§G Q9).**

Intermediate gate: `python -m pytest -m unit --tb=short -q 2>&1 | tail -5`

---

## Task 5 — Seed Data Rollout (Rule 11.5 — REQUIRED)

Per `backend/README-seed-data.md` — you read §3, §6, §7 in Pre-Work.

### Layer 1 — Core / Platform values

**Not applicable** — these are per-tenant business fields, not lookup/reference data. (Explicitly recorded so the section is not "missing.")

### Layer 2 — Scenario data (Group D)

In `backend/migrations/scripts/seed_test_tenant.py`, near the existing `UPDATE public.tenant` block (~line 307), add an **idempotent, value-scoped** update so the dev tenant's manual-payment panel renders locally:

```sql
UPDATE public.tenant
SET billing_contact_phone = '(804) 555-0142',
    billing_contact_email = 'billing@pilotdevtenant.example.com',
    updated_at = NOW()
WHERE id = '00000000-0000-0000-0000-000000000001';
```

- Idempotent by construction (same values every run — no DELETE needed; §7 DELETE-safety rule not triggered).
- Also add a line to the script's **inspect/show mode** output where `tenant` fields are reported (mirror the existing `[tenant]` inspect lines).
- Do **not** seed scenario tenants other than the dev tenant — a null contact on other tenants is a *desired* state (it exercises the frontend both-null fallback).

### Verification

- `python migrations/scripts/seed_test_tenant.py --mode seed` (or the documented run order per README §6) → re-run MCP query #3: both values present on `…0001`.
- `python migrations/scripts/seed_core.py --mode inspect` still clean (no Layer 1 change — confirm no regression).
- `python -m pytest -m unit --tb=short -q 2>&1 | tail -5` — a seed row a test doesn't expect can break tests; fix any seed-resilience failures (assert-by-ID, never by count).

### README update

- Update `backend/README-seed-data.md` §4 (Current Seed State) — `tenant` gains `billing_contact_phone` / `billing_contact_email` seeded on the dev tenant.

---

## Task 6 — Tests

Per `backend/tests/README-adding-tests.md`. Domain folder: **`tests/domains/invoicing_billing/`** (Invoices / Stripe / public links). New file `test_billing_payment_contact.py`:

```python
pytestmark = [
    pytest.mark.domain_invoicing_billing,
    pytest.mark.unit,
]
```

**Settings endpoint tests** (use `client`, `test_tenant`, `test_user`, `mock_cognito_jwt` fixtures — never hardcoded UUIDs):

1. **PATCH round-trip**: PATCH both fields → 200 → GET returns them.
2. **Partial update**: PATCH phone only → email unchanged (pre-set email first via an earlier PATCH).
3. **Explicit null clears**: PATCH `{"billing_contact_phone": null}` → GET shows phone null, email preserved.
4. **Empty-string phone → null**: PATCH `{"billing_contact_phone": "   "}` → GET shows null.
5. **Invalid email → 422** with RFC 7807 shape (`type`/`title`/`status`/`detail` keys present).
6. **Idempotency replay**: same `Idempotency-Key` + same payload twice → second response equals first (and exactly one audit-visible write path — assert response equality + `X-Idempotency-Replay` header if the stack emits one, per the A5 tests you'll read).
7. **Unauthenticated → 401**.
8. **Cross-tenant isolation**: PATCH in `tenant_a` is invisible in `tenant_b`'s GET (use `tenant_a`/`tenant_b` + `user_tenant_a`/`user_tenant_b` fixtures).

**Public GET tests** (extend the existing public-invoice test file you find via `grep -rln "public/invoices" backend/tests/domains/invoicing_billing/` — read it first and follow its token-minting pattern):

9. Tenant with billing contact set → 200 response includes `tenant_phone` / `tenant_email` with those values.
10. Tenant with both null (use `second_tenant` — empty state) → response fields are `null` (the frontend both-null fallback case). Assert the keys exist and are null.

Scope every assertion by the IDs you inserted — never total counts. `db_session` rollback is the cleanup mechanism.

After adding test files:

```bash
python generate_app_import_map.py tests > app_model_imports.md
```

---

## Regenerate OpenAPI (Handoff Signal)

After all tests pass (and after the changed-files ruff gate):

```bash
cd <repo>/backend
source .venv/bin/activate
python export_openapi_json.py
grep -A 5 "payment-contact" backend/openapi_schema_map.md
grep -n "tenant_phone" backend/openapi.json | head -3
```

Both the new GET/PATCH pair and the two new response fields must appear. **`pnpm sync-api-types` is the Part C handoff signal (§9.3)** — see Handoff Instructions below.

---

## Final Verification

### Phase 1 — Unit Tests Only (run after each task group during development)

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=short -q 2>&1 | tail -10
```

All unit tests must pass before moving to the next task. Fix any unit failure — including failures that appear to be caused by code outside your batch — before proceeding.

### Phase 2 — Lint (changed files only) + Full Suite, Vendor-Deselected (run once, at the very end)

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

# Batch-specific spot checks:
python -m pytest tests/domains/invoicing_billing/test_billing_payment_contact.py -v 2>&1 | tail -20
grep -A 5 "payment-contact" backend/openapi_schema_map.md

echo "=== STRIPE-CONNECT-1-B2 FINAL VERIFICATION COMPLETE ==="
```

**Vendor-suite inclusion call (explicit)**: this batch modifies **no** Stripe-covered code (pure-DB columns + a settings router + two response fields on the public GET — zero Stripe SDK calls). `requires_stripe` is **not** run. Recorded here per the Phase 2 rule.

> **Warning-clean is part of done.** Ruff must report no remaining issues in your changed files; the pytest run must be free of `DeprecationWarning` noise. Do not run `ruff check .` against the whole codebase.
>
> **Any failure in either phase must be fixed before the batch is declared done.** No "pre-existing failure" exception without explicit written confirmation from Tom.

---

## Definition of Done

Check off each item **in this prompt doc** as it completes:

- [ ] Pre-modification regression baseline captured (`X passed, Y failed`) using `pytest -m unit`
- [ ] Zero pre-existing unit failures confirmed before starting work (or confirmed with Tom)
- [ ] All MCP pre-work queries run — `tenant` columns verified absent-then-present, alembic head confirmed (`information_schema.columns`, rules §25)
- [ ] All mandatory source files read before writing any code (including `core/idempotency.py` + the A5 adopter)
- [ ] Task 1: migration `stripe_connect_1_billing_contact` — blank, full-cycle tested (upgrade → downgrade → upgrade → current)
- [ ] Task 2: `Tenant` model fields added; `generate_db_model_map.py app > db_models_map.md` run; `schema_manager.py set` ×2 (path-based, payload files — never hand-edited JSON)
- [ ] Task 3: `api/routes/billing_payment_contact.py` created (GET + PATCH), registered in `main.py` at `/api/v1/settings/billing`; `settings.tenant.write` RBAC; `set_audit_context_sync()` before commit; `Idempotency-Key` 24h pattern adopted; partial-update semantics via `model_fields_set`
- [ ] Task 4: `PublicInvoiceResponse` + GET handler — `tenant_phone` / `tenant_email` populated from local columns, None-safe, no owner fallback
- [ ] Task 5: seed rollout — dev-tenant values in `seed_test_tenant.py` (idempotent, value-scoped) + inspect-mode line; README-seed-data §4 updated; `pytest -m unit` green after seeding
- [ ] Task 6: `test_billing_payment_contact.py` (10 tests) + public-GET field tests; `pytestmark` domain + unit; `generate_app_import_map.py tests > app_model_imports.md` run
- [ ] All DB-touching routes/`_impl()` are sync `def` (rules §21)
- [ ] Only Pydantic v2 idioms; every new route has `response_model` (rules §22)
- [ ] All new API errors follow RFC 7807 Problem Details format
- [ ] No module-level `TestClient`; all tests use `test_tenant`/`test_user` fixtures; assertions scoped by inserted IDs
- [ ] `python export_openapi_json.py` run — `payment-contact` pair + `tenant_phone`/`tenant_email` verified in `openapi_schema_map.md` / `openapi.json`
- [ ] `ruff check --fix && ruff format` on changed files only — zero remaining issues, no unjustified `# noqa` (rules §23)
- [ ] **Phase 1**: All unit tests pass — zero failures including any pre-existing
- [ ] **Phase 2**: Full suite (vendor-deselected) passes — zero failures, warning-clean; `requires_stripe` exclusion call recorded above
- [ ] Final test count (before → after) documented
- [ ] Completion Summary filled in at this prompt doc's ending `## Appendix — Completion Summary` (ADR-0017 — never the launch plan)
- [ ] **Handoff Instructions** below executed (commit + notify Part C)

---

## Handoff Instructions (→ STRIPE-CONNECT-1-C React Engineer)

When the Definition of Done is fully checked:

1. Confirm `python export_openapi_json.py` has been run and `git status` shows `backend/openapi.json` + `backend/openapi_schema_map.md` updated.
2. Commit all backend work.
3. Notify Tom / the React Engineer that **STRIPE-CONNECT-1-C is unblocked** — its first Pre-Work step is `pnpm sync-api-types`, which will deliver `PaymentContactResponse`, the `payment-contact` paths, and the new `tenant_phone` / `tenant_email` fields on the public invoice response into `packages/shared-types/src/api-schema.d.ts`.

## After This Task — Next Step

**STRIPE-CONNECT-1-C** (React Engineer) — prompt: `batch-stripe-connect-1-c-react-engr-prompt.md`. It consumes everything this batch ships.

---

## Appendix — Completion Summary

### STRIPE-CONNECT-1-B2 — Billing-Contact Fields: Completion Summary

**Completed**: 2026-08-29
**Mode**: Pilot Python Engineer
**Baseline**: 4719 passed, 0 failed (1 skipped)
**Final**: 4729 passed, 0 failed (1 skipped) (+10 new tests)

#### What Was Accomplished

- Added two nullable `TEXT` columns (`billing_contact_phone`, `billing_contact_email`) to the `tenant` table via a blank Alembic migration (`c8d06a6ffdd2`), full-cycle tested (upgrade → downgrade → upgrade → current).
- Added the two fields to the `Tenant` SQLModel class in `app/models/core.py` (adjacent to the Part A `stripe_connect_*` fields, matching the `sa_column=Column(Text, nullable=True)` style).
- Created a new settings router `api/routes/billing_payment_contact.py` with `GET` + `PATCH /api/v1/settings/billing/payment-contact` (plus `/test` twins), RBAC `settings.tenant.write`, sync `def`, RFC 7807 errors, `set_audit_context_sync()` before commit, partial-update semantics via `model_fields_set`, and idempotency via the existing `idempotency_middleware` (24h cache).
- Added `tenant_phone` / `tenant_email` to `PublicInvoiceResponse` and the public GET handler, populated from the already-loaded tenant's local columns (None-safe, no extra query, no owner-user fallback — by design §G Q9).
- Seeded the dev tenant (`…0001`) with realistic billing-contact values in `seed_test_tenant.py` (idempotent upsert — set on both INSERT and ON CONFLICT DO UPDATE), plus inspect-mode and show-mode output lines.
- Wrote 10 tests (8 settings-endpoint + 2 public-GET field) — all pass.
- Regenerated `db_models_map.md`, `app_model_imports.md`, `openapi.json`, `openapi_schema_map.md`.
- Updated `pilot-db-schema-v2.6h.json` via `schema_manager.py` (path-based, payload files — never hand-edited).
- Updated `README-seed-data.md` §4 (Group C `tenant` row) to document the new seeded fields.
- Ruff: zero issues across all 7 changed/new Python files. Full suite (vendor-deselected): 4729 passed, 0 failed, warning-clean.

#### Files Changed / Created

| File | Action |
|---|---|
| `backend/migrations/versions/2026_08_29_1806-c8d06a6ffdd2_stripe_connect_1_billing_contact.py` | Created — blank Alembic migration adding `billing_contact_phone` + `billing_contact_email` TEXT NULL columns on `tenant` |
| `backend/app/models/core.py` | Updated — added `billing_contact_phone` + `billing_contact_email` fields to `Tenant` class |
| `backend/api/routes/billing_payment_contact.py` | Created — new settings router (GET + PATCH + /test twins) for billing payment-contact |
| `backend/app/main.py` | Updated — registered `billing_payment_contact.router` at `/api/v1/settings/billing` prefix + import |
| `backend/api/routes/public_invoices.py` | Updated — added `tenant_phone` / `tenant_email` to `PublicInvoiceResponse` + GET handler |
| `backend/migrations/scripts/seed_test_tenant.py` | Updated — billing-contact constants, idempotent upsert columns, inspect-mode + show-mode output |
| `backend/tests/domains/invoicing_billing/test_billing_payment_contact.py` | Created — 10 tests (8 settings + 2 public-GET) |
| `backend/db_models_map.md` | Regenerated |
| `backend/app_model_imports.md` | Regenerated |
| `backend/openapi.json` | Regenerated |
| `backend/openapi_schema_map.md` | Regenerated |
| `dev-docs/db-design/pilot-db-schema-v2.6h.json` | Updated via `schema_manager.py` (2 new column entries) |
| `backend/README-seed-data.md` | Updated — §4 Group C `tenant` row documents the new seeded billing-contact fields |

#### Tests Added

| Test File | Domain | Tests | All Pass |
|---|---|---|---|
| `tests/domains/invoicing_billing/test_billing_payment_contact.py` | `invoicing_billing` | 10 | ✅ |

#### MCP Discrepancies Noted

- None. All MCP pre-work queries matched expectations: `billing_contact_*` columns absent before migration, present+NULL after; alembic head `d038d647ec41` confirmed as `down_revision`; 0 `payment_contact` procs. The `postgres-local` MCP server was used as the master schema source throughout (per Tom's instruction).

#### Vendor-Suite Inclusion Call

- `requires_stripe` was **not** run — this batch modifies no Stripe-covered code (pure-DB columns + a settings router + two response fields on the public GET — zero Stripe SDK calls). Recorded per the Phase 2 rule.
