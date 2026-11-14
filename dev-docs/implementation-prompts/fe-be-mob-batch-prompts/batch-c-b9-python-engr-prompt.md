# Implementation Prompt: C-B9 — 10DLC Provisioning State Machine + Stripe Checkout + Sole-Prop OTP + Temporal Fee Schedule

**Mode**: Pilot Python Engineer
**Batch**: C-B9 (Part A — Backend)
**Source plan**: `pilot-launch-plan.md` §2.0 row 14n
**Design doc**: `batch-c-b9-design.md` — read ALL sections (A–L) before writing any code
**Estimated session**: 4–6 hours
**Platform**: Backend only (`backend/`)
**Frontend companion**: C-B9 Part B (React Engineer) — runs after this batch completes + `pnpm sync-api-types`

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-python-engineer/python-engineer-rules.md`** — full document; the 25 hard rules are non-negotiable STOPs
- **`dev-docs/architecture-design/pilot-python-engineer-methods.md`** — §13 (Alembic), §8 (Router Design), §5 (Model Design), §16 (Standard Task Workflow)
- **`backend/tests/README-adding-tests.md`** — full document; this governs all test file structure, domain markers, and fixture rules
- **`dev-docs/integrations/telnyx/10dlc-registration-automation-requirements.md`** — §3 (Telnyx API reference) + §4 (temporal fee schedule design) — the authoritative source for Telnyx API endpoints, schemas, enum endpoints, and fee codes

Critical rules for this batch:

- **Rule 1**: Never guess column names, data types, or table names. Use `postgres-local` MCP to verify every name before use. If MCP returns an error → **STOP and ask Tom**.
- **Rule 2**: After any model file change → regenerate `backend/db_models_map.md` via `python generate_db_model_map.py app > db_models_map.md`.
- **Rule 3**: After any endpoint change → run `python export_openapi_json.py` (updates both `openapi.json` and `openapi_schema_map.md`).
- **Rule 4**: All Alembic migrations must be written as **blank** migrations (never `--autogenerate`). Data changes use raw `op.execute()` with `SET LOCAL session_replication_role = 'replica';`.
- **Rule 6**: `db.get()` is permanently banned on tenant-scoped models. Always use tenant-scoped `select()` with an explicit `WHERE tenant_id = :tid` clause.
- **Rule 8**: All API error responses MUST follow RFC 7807 Problem Details format.
- **Rule 9**: Every mutation endpoint MUST call `set_audit_context_sync(db, user_id=current_user.id)` before committing.
- **Rule 12 (sync routes)**: Every DB-touching route and `_impl()` is a plain `def` — never `async def` on the blocking `Session`.
- **Rule 13 (Pydantic v2)**: Use v2 idioms only. Money is integer millicents (`_millicents: int`) — never a float. (This batch uses millicents, not cents — see design doc §B.6.)
- **Rule 14 (Ruff)**: Run ruff only against changed files. Fix ALL errors in those files.
- **Rule 15 (audit mixins)**: New tables inherit exactly one mixin. No new table in this batch — but the `carrier_fee_schedule` migration adds columns to an existing table.
- **Rule 16 (verify, don't assume)**: 186 tables exist. Query `information_schema.columns` for every table you touch this session before writing SQL.

---

## Pre-Work: Establish Regression Baseline

Before touching any file, capture the current **unit-only** test baseline:

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=no -q 2>&1 | tail -5
```

Record the exact count: **`X passed, Y failed`**.

> **If any tests are already failing before you start**: Do NOT treat them as "pre-existing" and proceed anyway. Either confirm with Tom or fix the failure before touching any batch files.

---

## Pre-Work: Run MCP Verification Queries

> **MCP Usage Rule**: The `postgres-local` MCP is for **read-only verification only**. Never use it to INSERT, UPDATE, or DELETE. If a query fails → STOP and ask Tom.

Run **all** of these via `postgres-local` MCP before writing any code:

```sql
-- 1. Verify tenant_10dlc_profile columns (confirm website/stock_symbol/vertical don't exist yet)
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'tenant_10dlc_profile'
ORDER BY ordinal_position;

-- 2. Verify tenant_messaging_registration columns (confirm all state machine fields exist)
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'tenant_messaging_registration'
ORDER BY ordinal_position;

-- 3. Verify carrier_fee_schedule columns (confirm amount_cents/is_active exist, amount_millicents/effective_from/effective_to don't)
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'carrier_fee_schedule'
ORDER BY ordinal_position;

-- 4. Verify carrier_fee_schedule constraints (confirm UNIQUE on fee_code, entity_type)
SELECT conname, contype, pg_get_constraintdef(oid)
FROM pg_constraint
WHERE conrelid = 'public.carrier_fee_schedule'::regclass;

-- 5. Verify btree_gist extension exists (needed for GiST exclusion constraint)
SELECT extname FROM pg_extension WHERE extname = 'btree_gist';

-- 6. Verify tenant has stripe_customer_id
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'tenant'
  AND column_name = 'stripe_customer_id';

-- 7. Verify current alembic head
SELECT version_num FROM public.alembic_version;
```

---

## Pre-Work: Read These Source Files

Use `read_file` on each of these before writing any code:

```
backend/app/models/sms.py                          ← why: TenantMessagingRegistration model (state machine table)
backend/app/models/core.py                         ← why: Tenant10DlcProfile model (brand data table)
backend/app/models/billing.py                      ← why: CarrierFeeSchedule model (temporal fee schedule)
backend/services/sms_carrier.py                    ← why: SmsCarrier ABC + MockSmsCarrier (add 7 new methods)
backend/services/telnyx_sms_carrier.py              ← why: TelnyxSmsCarrier (add 7 new implementations)
backend/services/telnyx_quoting.py                 ← why: get_carrier_quote() (update for temporal + millicents)
backend/services/stripe_subscriptions.py           ← why: handle_checkout_session_completed() stub (implement)
backend/api/routes/messaging_quote.py              ← why: C-B8 quote endpoint pattern reference
backend/api/routes/tenant_10dlc_profile.py          ← why: DLC-1 profile CRUD pattern reference
backend/api/schemas/dlc.py                          ← why: existing schemas (extend with provisioning + millicents)
backend/migrations/versions/2026_08_05_1423-025ac61ea0a6_c_b8_create_carrier_fee_schedule.py  ← why: C-B8 migration pattern reference
backend/migrations/scripts/seed_platform.py         ← why: carrier_fee_schedule seed block (update for millicents)
backend/tests/domains/subscriptions_usage/test_cb8_carrier_quote.py  ← why: C-B8 test pattern + update assertions
backend/tests/conftest.py                           ← why: available fixtures
backend/db_models_map.md                            ← why: confirm model names and table mappings
```

Also run:
```bash
grep -rn "handle_checkout_session_completed" backend/ --include="*.py" -l
grep -rn "carrier_fee_schedule" backend/ --include="*.py" -l
```

---

## Background / Context

C-B9 implements the full 10DLC provisioning lifecycle. Read the design doc `batch-c-b9-design.md` in full — it has the complete state machine, API contracts, migration DDL, and module interfaces. Key points:

1. **Two migrations**: (a) add 3 columns to `tenant_10dlc_profile` (website, stock_symbol, vertical); (b) temporal `carrier_fee_schedule` migration (add effective_from/effective_to/amount_millicents, drop amount_cents/is_active, add GiST exclusion, seed 12 new fee codes)
2. **13-state machine**: `not_started → quoting → awaiting_payment → brand_submitted → awaiting_otp → brand_verified → campaign_submitted → awaiting_number_selection → number_assigned → active` (plus terminal/error states)
3. **8 API endpoints** + `/test` twins: provision, checkout, otp, status, retry, verticals, available-numbers, assign-number
4. **7 new carrier methods** on `SmsCarrier` ABC: `create_brand`, `get_brand`, `create_campaign`, `get_campaign`, `get_verticals`, `list_available_numbers`, `assign_number_to_campaign`
5. **Stripe Checkout** with `setup_future_usage: off_session` — one-time setup charge
6. **Webhook handler** — replace the C-B4 stub in `handle_checkout_session_completed()`
7. **3 Celery tasks**: `provision_brand`, `provision_campaign`, `check_otp_timeout`
8. **Millicents** (not cents): 1 millicent = $0.00001. All fee amounts use `amount_millicents BIGINT`.

---

## Task 1 — Alembic Migration: Brand Fields on tenant_10dlc_profile

Create a blank migration adding `website`, `stock_symbol`, `vertical` (all TEXT, nullable) to `tenant_10dlc_profile`.

```bash
cd <repo>/backend
source .venv/bin/activate
alembic revision -m "c_b9_add_brand_fields"
```

Per design doc §B.1. All 3 columns nullable — `website` required at app layer, not DB. Implement `downgrade()` to drop the 3 columns.

Test: `alembic upgrade head && alembic downgrade -1 && alembic upgrade head && alembic current`

---

## Task 2 — Alembic Migration: Temporal carrier_fee_schedule

Create a blank migration per design doc §B.6. This is the most complex migration in the batch:

1. Add `effective_from TIMESTAMPTZ NOT NULL DEFAULT now()`, `effective_to TIMESTAMPTZ`, `amount_millicents BIGINT`
2. Migrate existing rows: `amount_millicents = amount_cents * 1000`, `effective_from = created_at`, `effective_to = NULL`
3. Drop `amount_cents` and `is_active` columns
4. Set `amount_millicents` NOT NULL
5. `CREATE EXTENSION IF NOT EXISTS btree_gist` (check if it already exists first via MCP)
6. Add GiST exclusion constraint on `(fee_code, entity_type, tstzrange(effective_from, effective_to))`
7. Drop old UNIQUE constraint `uq_carrier_fee_schedule_code_entity`
8. Seed 12 new fee codes (brand_vetting, campaign_registration_tmobile, phone_number_assignment, surcharge_att, surcharge_tmobile, surcharge_verizon — each x2 entity types)

Use `SET LOCAL session_replication_role = 'replica';` at the start of `upgrade()`. Implement full `downgrade()`.

Test: `alembic upgrade head && alembic downgrade -1 && alembic upgrade head && alembic current`

Run intermediate unit tests: `python -m pytest -m unit --tb=short -q 2>&1 | tail -5`

---

## Task 3 — Update SQLModels + Schemas + Quoting Adapter

Per design doc §C steps 1b–1f, 2–4:

1. **`CarrierFeeSchedule`** (`app/models/billing.py`): replace `amount_cents` with `amount_millicents`, add `effective_from`/`effective_to`, remove `is_active`
2. **`Tenant10DlcProfile`** (`app/models/core.py`): add `website`, `stock_symbol`, `vertical` fields
3. **`get_carrier_quote()`** (`services/telnyx_quoting.py`): query `WHERE effective_to IS NULL` instead of `WHERE is_active = true`, return `amount_millicents`
4. **`CarrierQuoteLineItem` + `CarrierQuoteResponse`** (`api/schemas/dlc.py`): `amount_cents` → `amount_millicents`, `setup_total_cents` → `setup_total_millicents`, `recurring_monthly_cents` → `recurring_monthly_millicents`
5. **`Tenant10DlcProfileRequest/Response`** (`api/schemas/dlc.py`): add `website`, `stock_symbol`, `vertical` fields
6. **`tenant_10dlc_profile.py` route**: update `_upsert_10dlc_profile_impl` to persist new fields
7. **`seed_platform.py`**: update carrier_fee_schedule seed block to use `amount_millicents` + `effective_from`/`effective_to`
8. **C-B8 tests** (`test_cb8_carrier_quote.py`): update assertions from `amount_cents` to `amount_millicents`

Run: `python -m pytest -m unit --tb=short -q 2>&1 | tail -5`

---

## Task 4 — Carrier ABC + Telnyx Implementation + Mock

Per design doc §C steps 5–7, §F.3–F.4:

1. **`SmsCarrier` ABC** (`services/sms_carrier.py`): add 7 abstract methods + 2 new dataclasses (`BrandResult`, `CampaignResult`):
   - `create_brand(brand_data: dict) -> BrandResult`
   - `get_brand(brand_id: str) -> BrandResult`
   - `create_campaign(brand_id: str, campaign_data: dict) -> CampaignResult`
   - `get_campaign(campaign_id: str) -> CampaignResult`
   - `get_verticals() -> list[str]`
   - `list_available_numbers(area_code: str, limit: int = 10) -> list[dict]`
   - `assign_number_to_campaign(phone_number: str, campaign_id: str) -> str`

2. **`TelnyxSmsCarrier`** (`services/telnyx_sms_carrier.py`): implement all 7 methods using lazy SDK import. See `10dlc-registration-automation-requirements.md` §3 for exact API endpoints + curl examples. EntityType mapping: `standard` → `PRIVATE_PROFIT`, `sole_proprietor` → `INDIVIDUAL`.

3. **`MockSmsCarrier`** (`services/sms_carrier.py`): implement all 7 methods with deterministic test responses.

Run: `python -m pytest -m unit --tb=short -q 2>&1 | tail -5`

---

## Task 5 — State Machine Service + Checkout Service

Per design doc §C steps 8–9, §F.1–F.2, §F.5–F.6:

1. **`services/messaging_provisioning.py`** (new): state machine with `MESSAGING_STATES`, `VALID_TRANSITIONS`, `transition_status()`, `initiate_provisioning()`, `submit_otp()`, `get_provisioning_status()`, `poll_brand_status()`, `poll_campaign_status()`, `assign_phone_number()`, `_build_campaign_payload()`

2. **`services/messaging_checkout.py`** (new): `create_10dlc_checkout_session()` — Stripe Checkout with `mode="payment"`, `setup_future_usage: "off_session"`, inline `price_data` with millicents amount

Run: `python -m pytest -m unit --tb=short -q 2>&1 | tail -5`

---

## Task 6 — Webhook Handler + API Routes + Schemas

Per design doc §C steps 10–13, §D.1–D.8:

1. **`handle_checkout_session_completed()`** (`services/stripe_subscriptions.py`): replace the C-B4 stub. For `a2p_10dlc_setup` purpose: attach PM as `customer.invoice_settings.default_payment_method`, transition to `brand_submitted`, enqueue `provision_brand` Celery task.

2. **`api/routes/messaging_provisioning.py`** (new): 8 endpoints + `/test` twins:
   - `POST /messaging/provision` — initiate provisioning (settings.manage, Idempotency-Key)
   - `POST /messaging/checkout` — create Stripe Checkout session (settings.manage, Idempotency-Key)
   - `POST /messaging/otp` — submit sole-prop OTP (settings.manage)
   - `GET /messaging/status` — get provisioning status (settings.view)
   - `POST /messaging/retry` — retry from payment_failed (settings.manage)
   - `GET /messaging/verticals` — proxy carrier verticals enum (settings.view)
   - `GET /messaging/available-numbers` — proxy carrier available numbers (settings.view)
   - `POST /messaging/assign-number` — assign selected number (settings.manage, Idempotency-Key)

3. **Schemas** (`api/schemas/dlc.py`): add `ProvisionRequest`, `ProvisionResponse`, `CheckoutResponse`, `OtpRequest`, `ProvisioningStatusResponse`, `RetryResponse`, `VerticalsResponse`, `AvailablePhoneNumber`, `AvailableNumbersResponse`, `AssignNumberRequest`, `AssignNumberResponse`

4. **Register router** in `app/main.py`

All endpoints: sync `def`, RFC 7807 errors, `set_audit_context_sync()` on mutations, `require_permission()` RBAC.

Run: `python -m pytest -m unit --tb=short -q 2>&1 | tail -5`

---

## Task 7 — Celery Tasks + Beat Schedule

Per design doc §C steps 14–15, §F.7:

1. **`tasks/messaging_provisioning.py`** (new): 3 Celery tasks using the two-layer pattern (`_impl()` + `@celery_app.task`):
   - `provision_brand` — post-checkout: create Telnyx brand, poll for verification/rejection
   - `provision_campaign` — post-brand-verified: create Telnyx campaign, poll for approval, transition to `awaiting_number_selection`
   - `check_otp_timeout` — hourly: find registrations in `awaiting_otp` > 18h → alert Tom; > 24h → transition to `quoting`

2. **Register beat schedule** for `check_otp_timeout` (hourly) in `core/celery_app.py`

Run: `python -m pytest -m unit --tb=short -q 2>&1 | tail -5`

---

## Task 8 — Unit Tests

Per design doc §J.1. Domain: `subscriptions_usage`. Test file: `tests/domains/subscriptions_usage/test_cb9_messaging_provisioning.py`

```python
pytestmark = [
    pytest.mark.domain_subscriptions_usage,
    pytest.mark.unit,
]
```

Tests to write (per design doc §J.1 — 19 tests):
- `test_initiate_provisioning_standard`, `test_initiate_provisioning_sole_proprietor`, `test_initiate_provisioning_idempotent`, `test_initiate_provisioning_conflict_active`
- `test_create_checkout_session`, `test_checkout_session_completed_handler`
- `test_submit_otp_success`, `test_submit_otp_wrong_state`
- `test_otp_timeout_transition`, `test_brand_rejected_refund`, `test_campaign_rejected_partial_refund`
- `test_state_transition_invalid`, `test_retry_from_payment_failed`, `test_retry_wrong_state`
- `test_get_provisioning_status`, `test_get_provisioning_status_not_found`
- `test_mock_carrier_create_brand`, `test_mock_carrier_create_campaign`, `test_campaign_payload_template`
- `test_get_verticals`, `test_list_available_numbers`, `test_assign_number`

Use `db_session` fixture, `test_tenant`/`second_tenant` fixtures, `mock_cognito_jwt` for auth. Never assert on total row counts.

Run: `python -m pytest -m unit --tb=short -q 2>&1 | tail -5`

---

## Seed Data Rollout (Core + Scenario)

Per `backend/README-seed-data.md` — read §3 (Group A–D model), §6 (run order), and §7 (DELETE safety rule) before editing any seed script.

**⚠️ MANDATORY (Tom, 2026-08-06): This batch adds data to the DB (3 new columns on `tenant_10dlc_profile` + 12 new fee codes on `carrier_fee_schedule` + migration of existing fee rows to millicents). The seed system MUST be updated to produce realistic data for all new fields.**

### Layer 1 — Core / Platform values (Group A / B)

- **`carrier_fee_schedule`** — the migration seeds 12 new fee code rows (brand_vetting, campaign_registration_tmobile, phone_number_assignment, surcharge_att, surcharge_tmobile, surcharge_verizon — each x2 entity_types). The `seed_platform.py` carrier_fee_schedule block MUST be updated to match the migration's seed rows exactly:
  - Use `amount_millicents` (not `amount_cents`)
  - Use `effective_from = now()` and `effective_to = NULL` for all rows
  - Include all 20 rows (8 original migrated + 12 new)
  - Idempotent: `INSERT ... ON CONFLICT DO NOTHING`
  - `StandardAuditMixin` tables need explicit `created_at, updated_at = NOW(), NOW()`
  - The migration INSERT and the `seed_platform.py` INSERT MUST produce **identical rows** (`seed_platform.py` is the post-schema-restore recovery path)

- **`tenant_10dlc_profile`** — no new lookup/reference rows needed (the 3 new columns are tenant-specific data, not platform defaults). But if any scenario seed scripts create `tenant_10dlc_profile` rows, they must be updated (see Layer 2).

### Layer 2 — Scenario data (Group D)

- **`tenant_10dlc_profile` new columns** (`website`, `stock_symbol`, `vertical`) — check if any `seed_scenario_*.py` scripts create `tenant_10dlc_profile` rows. If they do, populate the new columns with realistic, varied values:
  - `website` — realistic contractor website URLs (e.g., `https://acmeelectric.example.com`, `https://contractor-a.example.com`)
  - `stock_symbol` — NULL for all scenario tenants (electricians are not publicly traded)
  - `vertical` — varied values from the Telnyx `/enum/vertical` endpoint (e.g., `ENERGY`, `CONTRACTOR`, `HOME_SERVICES`)
  - Non-uniform values where the field drives a display or filter

- If no scenario scripts currently create `tenant_10dlc_profile` rows, this layer is N/A — note it in the Completion Summary.

### Verification

- After seeding: `python migrations/scripts/seed_platform.py --mode inspect` (carrier_fee_schedule rows present with millicents)
- Confirm the `GET /messaging/quote` endpoint returns millicents (not cents) after the seed update
- Run `pytest -m unit` after the seed change — a seed row a test doesn't expect will break tests. Fix any seed-resilience failures (assert-by-ID, never by count).

### README update

- Update `backend/README-seed-data.md` §4 (Current Seed State) with:
  - `carrier_fee_schedule`: 20 rows (8 original migrated to millicents + 12 new fee codes), temporal design with `effective_from`/`effective_to`
  - `tenant_10dlc_profile`: 3 new columns (website, stock_symbol, vertical) — note if scenario seeds were updated

---

## Regeneration Steps

After all tests pass:

```bash
cd <repo>/backend
source .venv/bin/activate

# 1. Regenerate db_models_map.md
python generate_db_model_map.py app > db_models_map.md

# 2. Regenerate app_model_imports.md (if new test files added)
python generate_app_import_map.py tests > app_model_imports.md

# 3. Update JSON schema via schema_manager.py (path-based, never edit JSON directly)
#    Add website/stock_symbol/vertical to tenant_10dlc_profile
#    Update carrier_fee_schedule: amount_cents → amount_millicents, add effective_from/effective_to, remove is_active
#    Add 12 new seed rows
python schema_manager.py get --path tables.tenant_10dlc_profile.columns
python schema_manager.py get --path tables.carrier_fee_schedule.columns

# 4. Regenerate OpenAPI
python export_openapi_json.py

# 5. Verify new endpoints appear
grep -A 5 "messaging/provision" backend/openapi_schema_map.md
grep -A 5 "messaging/verticals" backend/openapi_schema_map.md
grep -A 5 "messaging/available-numbers" backend/openapi_schema_map.md
grep -A 5 "messaging/assign-number" backend/openapi_schema_map.md
```

---

## Final Verification

### Phase 1 — Unit Tests Only (run after each task group during development)

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=short -q 2>&1 | tail -10
```

### Phase 2 — Lint (changed files only) + Full Suite (run once at the very end)

```bash
cd <repo>/backend
source .venv/bin/activate

# Lint + format gate — CHANGED FILES ONLY
CHANGED_PY=$(git diff --name-only --diff-filter=d HEAD -- '*.py' | sed 's|^backend/||')
if [ -n "$CHANGED_PY" ]; then
    ruff check --fix $CHANGED_PY
    ruff format $CHANGED_PY
    ruff check $CHANGED_PY
fi

# Full suite including integration tests
python -m pytest --tb=short -q 2>&1 | tail -10

# Batch-specific spot checks
python -m pytest tests/domains/subscriptions_usage/ -v 2>&1 | tail -20
grep -A 5 "messaging/provision" backend/openapi_schema_map.md

echo "=== C-B9 FINAL VERIFICATION COMPLETE ==="
```

---

## Definition of Done

- [ ] Pre-modification regression baseline captured (`X passed, Y failed`) using `pytest -m unit`
- [ ] Zero pre-existing unit failures confirmed before starting work
- [ ] All MCP pre-work queries run — tenant_10dlc_profile, tenant_messaging_registration, carrier_fee_schedule, btree_gist, tenant, alembic_version verified
- [ ] All mandatory source files read before writing any code (including `api/schemas/dlc.py`)
- [ ] Migration 1: 3 columns added to `tenant_10dlc_profile` (website, stock_symbol, vertical)
- [ ] Migration 2: temporal `carrier_fee_schedule` (effective_from/effective_to/amount_millicents, GiST exclusion, 12 new fee codes)
- [ ] `CarrierFeeSchedule` SQLModel updated (amount_millicents, effective_from/effective_to, no is_active)
- [ ] `Tenant10DlcProfile` SQLModel updated (3 new fields)
- [ ] `get_carrier_quote()` updated (WHERE effective_to IS NULL, returns amount_millicents)
- [ ] `CarrierQuoteLineItem` + `CarrierQuoteResponse` schemas updated (millicents)
- [ ] `Tenant10DlcProfileRequest/Response` schemas updated (3 new fields)
- [ ] `tenant_10dlc_profile.py` route updated to persist new fields
- [ ] `seed_platform.py` carrier_fee_schedule block updated (millicents + temporal)
- [ ] C-B8 tests updated (amount_cents → amount_millicents assertions)
- [ ] `SmsCarrier` ABC: 7 new abstract methods + BrandResult/CampaignResult dataclasses
- [ ] `TelnyxSmsCarrier`: 7 new implementations (lazy SDK, EntityType mapping)
- [ ] `MockSmsCarrier`: 7 new deterministic implementations
- [ ] `services/messaging_provisioning.py` created (state machine + all functions)
- [ ] `services/messaging_checkout.py` created (Stripe Checkout)
- [ ] `handle_checkout_session_completed()` implemented (replaces C-B4 stub)
- [ ] `api/routes/messaging_provisioning.py` created (8 endpoints + /test twins)
- [ ] All provisioning schemas added to `api/schemas/dlc.py`
- [ ] Router registered in `app/main.py`
- [ ] `tasks/messaging_provisioning.py` created (3 Celery tasks, two-layer pattern)
- [ ] Celery beat schedule registered for `check_otp_timeout` (hourly)
- [ ] All DB-touching routes/`_impl()` are sync `def` — no `async def`
- [ ] Only Pydantic v2 idioms; every route has `response_model`; money is integer millicents
- [ ] `set_audit_context_sync()` called on every mutation endpoint
- [ ] All API errors follow RFC 7807 Problem Details format
- [ ] All new test files use `pytestmark` with domain marker + `pytest.mark.unit`
- [ ] No module-level `TestClient`; all tests use `client` fixture
- [ ] All tests use `test_tenant`/`second_tenant` fixtures (no hardcoded UUIDs)
- [ ] `python generate_db_model_map.py app > db_models_map.md` run
- [ ] `schema_manager.py` used for JSON schema changes (never edited directly)
- [ ] `python export_openapi_json.py` run — `openapi.json` and `openapi_schema_map.md` updated
- [ ] `ruff check --fix && ruff format` run on changed files only — zero remaining issues
- [ ] **Phase 1**: All unit tests pass (`pytest -m unit`) — zero failures
- [ ] **Phase 2**: Full test suite passes (`pytest`) — zero failures, warning-clean
- [ ] Final test count (before → after) documented
- [ ] Completion Summary added to launch plan §Appendix B

---

## Completion Summary

After all Definition of Done items are complete:

1. Add a **Completion Summary** subsection to `pilot-launch-plan.md` §Appendix B using the format below.

```markdown
### C-B9 (Part A — Python Engineer) — 10DLC Provisioning State Machine: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot Python Engineer
**Baseline**: X passed, Y failed
**Final**: X+N passed, Y failed (+N new tests)

#### What Was Accomplished

- [Brief description of key change 1]
- [Brief description of key change 2]

#### Files Changed / Created

| File | Action |
|---|---|
| `backend/path/to/file.py` | Created / Updated — [what changed] |
| ... | ... |

#### Tests Added

| Test File | Domain | Tests | All Pass |
|---|---|---|---|
| `tests/domains/subscriptions_usage/test_cb9_messaging_provisioning.py` | `subscriptions_usage` | N | ✅ |
```

---

## Handoff Instructions

After completing this batch:

1. Run `python export_openapi_json.py` to regenerate the OpenAPI spec
2. Commit all changes
3. Notify the React Engineer that C-B9 Part A is complete — they can now start Part B with `pnpm sync-api-types` as their first Pre-Work step
