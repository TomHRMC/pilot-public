# Implementation Prompt: QB-H1 — QuickBooks Coverage Audit + Sync Hardening

**Mode**: Pilot Python Engineer
**Batch**: QB-H1
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §3.5 (Ord 5; §7 founder-gate item)
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-qb-h1-design.md` v1.0 — **read it in full before Task 1; every task below references its design section**
**Estimated session**: 5–6 hours (7 tasks, sequenced prod-critical first; flex protocol in design §G Q5)
**Platform**: Backend only (`backend/`) + one doc (`dev-docs/integrations/quickbooks/`)
**Frontend companion**: none — no endpoint changes, no OpenAPI regen, no `pnpm sync-api-types` handoff (design §D)

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-python-engineer/python-engineer-rules.md`** — full document; the 25 hard rules are non-negotiable STOPs
- **`dev-docs/architecture-design/pilot-python-engineer-methods.md`** — §13 (Alembic), §8 (Router Design), §5 (Model Design), §16 (Standard Task Workflow)
- **`backend/tests/README-adding-tests.md`** — full document; governs all test file structure, domain markers, fixture rules
- **`backend/README-seed-data.md`** — §3 (Group A–D model), §6 (run order), §7 (DELETE-safety rule), §8.1 (the exclusion row this batch removes)

Critical rules for this batch:

- **Rule 1**: Never guess column names, data types, or table names. Use `postgres-local` MCP to verify every name before use. If MCP returns an error → **STOP and ask Tom**.
- **Rule 4**: All Alembic migrations must be written as **blank** migrations (never `--autogenerate`). Data changes use raw `op.execute()` with `SET LOCAL session_replication_role = 'replica';`. Always implement `downgrade()`.
- **Rule 6**: `db.get()` is permanently banned on tenant-scoped models. Always use tenant-scoped `select()` with explicit `WHERE tenant_id = :tid`.
- **Rule 7**: The `postgres-local` MCP is for **read-only verification only** — all data changes go through migrations, seed scripts, or application code.
- **Rule 11**: If ANY test fails during your work — even one that appears pre-existing — you must fix it before declaring the batch done. If you cannot identify the root cause → STOP and ask Tom.
- **Rule 12 (sync routes — rules §21)**: This app is **synchronous by design**. Every DB-touching route and `_impl()` is a plain `def`. **Exception already in the codebase**: the QB sync *service* methods (`services/quickbooks_sync.py`) are `async def` because they exclusively `await` `httpx.AsyncClient` — keep that existing pattern; do NOT convert them to sync, and do NOT make any new `async def` that touches the sync `Session`. Celery tasks stay sync `def` (they wrap `asyncio.run(...)`).
- **Rule 13 (Pydantic v2 — rules §22)**: v2 idioms only. Every route needs `response_model`. Money is integer cents — the QB service's cents→dollars conversion at the QB boundary is the existing, correct pattern.
- **Rule 14 (Ruff — rules §23)**: Ruff **only against files you changed** — `git diff --name-only --diff-filter=d HEAD -- '*.py' | sed 's|^backend/||'`, then `ruff check --fix <files> && ruff format <files>`. Fix ALL errors in those files, including pre-existing ones.
- **Rule 16 (verify, don't assume — rules §25)**: 186 tables exist. Query `information_schema.columns` for every table you touch this session before writing SQL.
- **Seed DELETE-safety (Rule 11.1 / README §7)**: every DELETE in a migration or seed `mode_seed` path must be **value-scoped** (deterministic UUID / `code =` / natural key + `tenant_id IS NULL`). Never blanket-delete provider/category rows.

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

Run **all** of these via `postgres-local` MCP before writing any code. If any query returns unexpected results → **STOP and ask Tom**.

> **MCP Usage Rule**: The `postgres-local` MCP is for **read-only verification only**. Use it to confirm table names, column types, and existing data. Never use it to INSERT, UPDATE, or DELETE — all data changes go through the application code, seed scripts, or Alembic migrations. If a query fails or returns an error → STOP and ask Tom before proceeding.
>
> **Two read-only MCP servers exist** (global rule `.roo/rules/02-database-mcp-access.md`): **`postgres-local`** is the default for all verification. **`postgres-prod`** reads production but **requires an SSH tunnel that only Tom controls** — ask Tom to confirm the tunnel is up before your first `postgres-prod` query, and STOP on any connection error. This batch uses `postgres-local` only; the post-deploy prod verification of Task 1 is Tom's step, not yours.

```sql
-- 1. Confirm the trio's current dev state (expect: category accounting; providers intuit + quickbooks;
--    app_service 2 rows — one global intuit row, one tenant-scoped quickbooks row with a realm id)
SELECT 'category' AS tbl, code::text AS key, description, is_active FROM public.app_service_category
UNION ALL SELECT 'provider', code, description, is_active FROM public.app_service_provider
ORDER BY tbl, key;
SELECT id, tenant_id, name, category_code, provider_code, is_active, external_account_id
FROM public.app_service ORDER BY provider_code, tenant_id NULLS FIRST;

-- 2. Confirm app_service constraints (expect: PK id; FKs to category/provider code + tenant; NO unique on natural key)
SELECT conname, contype, pg_get_constraintdef(oid) AS def FROM pg_constraint
WHERE conrelid = 'public.app_service'::regclass ORDER BY contype, conname;

-- 3. SAFETY GATE for design §G Q2 — the global row must have ZERO references before the migration
--    deletes/re-inserts it (expect: 0 and 0)
SELECT COUNT(*) AS cred_refs FROM public.integration_credential ic
JOIN public.app_service a ON a.id = ic.app_service_id WHERE a.tenant_id IS NULL;
SELECT COUNT(*) AS map_refs FROM public.integration_sync_mapping m
JOIN public.app_service a ON a.id = m.app_service_id WHERE a.tenant_id IS NULL;

-- 4. Confirm notification_type columns + PK (expect: PK code; cols incl. code, name, audience, is_active + audit cols)
SELECT column_name, data_type, is_nullable FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'notification_type' ORDER BY ordinal_position;

-- 5. Confirm the qb_sync_conflict template rows' exact column shape to mirror for qb_connection_expired
--    (note locale + any other populated column — your INSERTs must match this shape)
SELECT notification_type_code, channel, locale, subject, is_active FROM public.notification_template
WHERE notification_type_code = 'qb_sync_conflict' AND tenant_id IS NULL ORDER BY channel;

-- 6. Confirm the uniqueness constraint behind Task 5 (expect: UNIQUE (tenant_id, display_name))
SELECT conname, pg_get_constraintdef(oid) AS def FROM pg_constraint
WHERE conrelid = 'public.customer'::regclass AND contype = 'u';

-- 7. Confirm entity_type vocabulary (expect: customer, invoice, quote — NOTE whether payment exists;
--    record the result for the Task 7 matrix)
SELECT code, name FROM public.entity_type ORDER BY code;

-- 8. Confirm alembic head before creating the migration (expect: 58c3ad26129f)
SELECT version_num FROM public.alembic_version;
```

> **Engineer safety net — independent column verification (MANDATORY)**: Before writing ANY SQL statement, Alembic migration code, or SQLModel field reference in this batch, run `SELECT column_name, data_type, is_nullable, column_default FROM information_schema.columns WHERE table_schema = 'public' AND table_name = '<table>' ORDER BY ordinal_position;` for **every table you will touch** (`app_service`, `app_service_provider`, `app_service_category`, `notification_type`, `notification_template`, `integration_credential`, `integration_sync_mapping`, `integration_sync_conflict`, `customer`). If any column name in this prompt does not match what MCP returns → use the MCP-returned name, not the prompt's name, and note the discrepancy in your Completion Summary.

---

## Pre-Work: Read These Source Files

Use `read_file` on each of these before writing any code:

```
dev-docs/architecture-design/batch-designs/batch-qb-h1-design.md   ← the design — §B (migration), §C (order), §F (interfaces/copy), §G (resolved questions), Appendix 1 (matrix you verify + publish)
backend/migrations/versions/2026_05_31_2216-dd4ed7ed5f3b_seed_missing_lookup_tables_batch_1.py  ← the original trio INSERTs + downgrade pattern (lines 342–410)
backend/migrations/scripts/seed_core.py                          ← Group A dict patterns; stale NOTEs at lines 118–120 + 2381–2382; notification_type dict (~line 476–520); inspect manifest (~line 2995); help text (~line 3300)
backend/migrations/scripts/seed_platform.py                      ← Group B notification_template upsert loop + template-copy dict (lines 610–950); qb_sync_conflict entries at lines 682–694
backend/services/quickbooks_sync.py                              ← full file — sync service; intuit_tid exemplar (line ~571); queue_conflict; sync_customer_from_qb (Task 5 touch point)
backend/api/routes/integrations.py                               ← lines 395–529: dead sync _refresh_qbo_token_impl stub (396–449, delete) + async twin (452–529, modify); OAuth callback + connect flow
backend/tasks/quickbooks_token_refresh.py                        ← full file — Task 2's main touch point
backend/tasks/quickbooks_sync.py                                 ← sync_quickbooks_entity_task (Task 6 guard)
backend/api/routes/webhooks.py                                   ← webhook intake + get_tenant_by_realm_id (context for Task 6/matrix)
backend/tests/conftest.py                                        ← fixtures: test_app_service (line ~1270), test_qco_line_type, client/db_session/test_tenant/tenant_a
backend/tests/test_quickbooks_sync.py                            ← qb_app_service get-or-create fixture + mocked-httpx patterns you reuse in Tasks 2/5/6
backend/tests/batch_1e/test_task_1e4_qb_sync_notifications.py    ← notification assertion patterns (Task 4)
backend/db_models_map.md                                         ← confirm AppService / IntegrationCredential / IntegrationSyncMapping / IntegrationSyncConflict / NotificationType / NotificationTemplate mappings
backend/README-seed-data.md                                      ← §3, §6, §7, §8.1, §4 (you will edit §4 + §8.1)
```

Also run these greps to find related files:

```bash
grep -rn 'provider_code == "quickbooks"' backend/ --include="*.py" -l
grep -rn "qb_sync_conflict" backend/migrations/scripts/ -l
grep -rn "app_service" backend/tests/ --include="*.py" -l
```

---

## Background / Context

QB-H1 answers Tom's mission question (launch plan §3.5): *"Are we able to handle all of the necessary objects and fields of data that is in QuickBooks so that a sync is valid and meaningful for our customers?"* Two parts:

**Part 1 — Coverage audit (Task 7)**: publish the QB entity ↔ P4T mapping matrix at `dev-docs/integrations/quickbooks/qb-coverage-matrix.md`. The Architect pre-built the matrix from code evidence (design Appendix 1) — you verify each row against the code, correct drift, and publish. The triage table (in-batch fixes vs follow-on candidates) is Tom's QB-H2 approval gate.

**Part 2 — Hardening (Tasks 1–6)**:
- **Prod is broken end-to-end today**: prod has 0 rows in `app_service` / `app_service_provider` / `app_service_category` (schema-restore + `alembic stamp` never ran the 2026-05-31 migration's embedded INSERTs). OAuth connect FK-fails; webhook realm lookup finds no tenant. Task 1 restores the registry and moves ownership to `seed_core.py` Group A (the card's centerpiece).
- OAuth refresh marks connections `expired` on **any** error — a transient Intuit 5xx kills a healthy connection with no owner notification (Tasks 2–3).
- QB allows duplicate customer DisplayNames; P4T has `UNIQUE (tenant_id, display_name)` — the second same-name customer crashes the sync (Task 5).
- Webhook-driven sync silently drops non-customer entities (Task 6a).

**Canonical `provider_code` is `quickbooks`** (design §G Q1 — deliberate, evidence-based deviation from the card's parenthetical `intuit`; ~30 call sites use `quickbooks`, zero use `intuit`).

---

## Task 1 — `app_service*` Registry Restoration (design §B, §C.1)

**What to change:**

1. **Create the blank migration**:
   ```bash
   cd <repo>/backend && source .venv/bin/activate
   alembic revision -m "qb_h1_restore_app_service_registry"
   ```
   Implement `upgrade()` per design §B.3 steps 1–7 exactly (category + provider INSERTs `ON CONFLICT DO NOTHING`; dev re-point `intuit`→`quickbooks`; orphan `intuit` retire guarded by `NOT EXISTS`; global-row normalize DELETE+INSERT with deterministic UUID `00000000-0000-0000-0000-000000000aa5`; `qb_connection_expired` notification_type INSERT; 3 notification_template INSERTs each `WHERE NOT EXISTS`-guarded on `(notification_type_code, channel, locale, tenant_id IS NULL)`). Begin `upgrade()` with `SET LOCAL session_replication_role = 'replica';`. Implement `downgrade()` as the exact reverse per design §B.3. Template subject/body copy comes from design §F.3 — **byte-identical** to what you put in `seed_platform.py`.
2. **Test the full cycle**: `alembic upgrade head` → `alembic downgrade -1` → `alembic upgrade head` → `alembic current` shows the new head. Re-run `alembic upgrade head` once more to prove idempotency (no duplicate-row errors).
3. **`seed_core.py`**: add `app_service_category` + `app_service_provider` to the code-table dict (rows identical to the migration); add a global-`app_service` seed block (deterministic UUID above, `ON CONFLICT (id) DO NOTHING`); add `qb_connection_expired` to the `notification_type` dict; **delete the stale NOTEs at lines 118–120 and 2381–2382**; fix the help text (~line 3305: `quickbooks_online` → the real rows); add `app_service` to the inspect manifest. Ensure any reset-mode path deletes child-first (`app_service` before provider/category) and every `mode_seed` DELETE is value-scoped (Rule 11.1).
4. **`seed_platform.py`**: add the 3 `qb_connection_expired` template-copy entries following the `qb_sync_conflict` precedent (lines 682–694).
5. **`README-seed-data.md`**: remove the §8.1 exclusion row for `app_service` / `app_service_provider` (replace with a one-line "owned by seed_core.py Group A since QB-H1" pointer); update §4 with the trio rows, the deterministic UUID, and the new notification type/templates.
6. **Teardown-collision proof** (design §G Q3): run `python migrations/scripts/seed_core.py --mode reset` then `--mode seed`, then run the QB test cohort: `pytest tests/test_quickbooks_sync.py tests/batch_b8/ tests/batch_1e/ tests/batch_b19/test_qb_invoice_push.py --tb=short -q`. All must pass. If a collision surfaces, root-cause it (expected class: FK ordering or a fixture creating a duplicate provider row) and fix the fixture/seed — do NOT re-add an exclusion.
7. **New tests** — `backend/tests/domains/quickbooks/test_qb_h1_app_service_seed.py`:
   - trio rows present after seed (category `accounting`, provider `quickbooks`, global row at the deterministic UUID with `tenant_id NULL`)
   - seed re-run is idempotent (row counts unchanged; no error)
   - `qb_connection_expired` type + 3 channel templates present (`tenant_id IS NULL`)

Intermediate run: `python -m pytest -m unit --tb=short -q 2>&1 | tail -5`

---

## Task 2 — OAuth Refresh Robustness (design §F.1–F.2)

**What to change** (`tasks/quickbooks_token_refresh.py`, `api/routes/integrations.py`):

1. Add `_classify_refresh_error(exc) -> TokenRefreshOutcome` (design §F.1): `httpx.HTTPStatusError` with 400/401 (or `invalid_grant` in the body) → `PERMANENT_FAILURE`; 5xx + `httpx.TransportError`/timeout → `TRANSIENT_FAILURE`; anything else → `PERMANENT_FAILURE` (fail-safe).
2. `tasks/quickbooks_token_refresh.py`: on transient failure → `logger.warning(...)` (include `tenant_id`, `intuit_tid` if available, attempt context), leave `connection_status="active"`, count `transient_failed`; on permanent failure → `connection_status="expired"` + enqueue the `qb_connection_expired` notification to the tenant owner via the existing notification service path (mirror `queue_conflict`'s enqueue in `services/quickbooks_sync.py`). Replace **all** `print()` calls with `logger`. Return dict gains `transient_failed: int`.
3. `api/routes/integrations.py`: **delete the dead sync `_refresh_qbo_token_impl` stub (lines 396–449)** — it raises `NotImplementedError` and is shadowed by the async twin. In the async `_refresh_qbo_token_impl`: same classification; permanent failure still raises `HTTPException(500)` to the caller (contract preserved) after marking expired + enqueueing the notification; transient failure raises `HTTPException(503)` (RFC 7807 body) and leaves the connection active.
4. **New tests** — `backend/tests/domains/quickbooks/test_qb_h1_token_refresh.py` (httpx mocked; test `_impl`-level, never `.delay()`):
   - 400 `invalid_grant` → `expired` + notification enqueued (assert outbox/notification rows for the owner)
   - 503 from Intuit → still `active`, `transient_failed=1`, no notification
   - network `TransportError` → still `active`
   - success path → tokens rotated, `last_refresh_at` set (existing behavior preserved)
   - dead stub removal: `grep -c "def _refresh_qbo_token_impl" backend/api/routes/integrations.py` returns exactly 1

Intermediate run: `python -m pytest -m unit --tb=short -q 2>&1 | tail -5`

---

## Task 3 — `intuit_tid` → CloudWatch Extension (design §C task 3)

**What to change**: extend the existing structured-log pattern (exemplar: `services/quickbooks_sync.py` line ~571 — `logger.info("QBO API call: %s %s | status=%d | intuit_tid=%s", ...)` with **arg-style interpolation, never f-strings**) to every QB HTTP path that lacks it:

- `tasks/quickbooks_token_refresh.py::_refresh_access_token` (log the token-endpoint call + tid)
- `api/routes/integrations.py` — the async refresh path + the OAuth callback token exchange

**New tests** — extend `test_qb_h1_token_refresh.py`: `caplog` assertions that a refresh emits a log record containing `intuit_tid`. Grep gate: every `httpx` call site in QB code paths has an adjacent `intuit_tid` log (list the sites in your Completion Summary).

Intermediate run: `python -m pytest -m unit --tb=short -q 2>&1 | tail -5`

---

## Task 4 — Conflict Email to Owner: Verify + Close (design §C task 4)

**What to change**: PRD §3.9 requires the `qb_sync_conflict` notification to reach the **tenant owner** (SMS or email). Templates exist on all 3 channels (MCP-verified at design time). Write the test that proves the path:

**New tests** — `backend/tests/domains/quickbooks/test_qb_h1_conflict_owner_notification.py`:
- Seed (via fixtures) a tenant with an owner user holding an active `email` `user_endpoint`; trigger `queue_conflict` (reuse `batch_1e` helpers); assert the enqueued notification resolves to the **owner's** email endpoint (not all users, not in-app only).
- If the test proves a resolution gap → fix the recipient resolution (smallest change consistent with the existing notification service), keeping the SD-2/SD-3 resolution order documented in `dev-docs/pilot-operations.md`.

Intermediate run: `python -m pytest -m unit --tb=short -q 2>&1 | tail -5`

---

## Task 5 — `customer.display_name` Uniqueness Collision Resolution (design §F.4)

**What to change** (`services/quickbooks_sync.py`): implement `_insert_customer_with_dedup` per design §F.4 — on `IntegrityError` from `uq_customer_tenant_display_name` during `sync_customer_from_qb`, roll back the failed insert, retry once with `display_name = f"{DisplayName} (QB {Id})"`, then queue an `integration_sync_conflict` row with `conflict_subtype='display_name_dedup'` (both snapshots populated, status `pending`) so the owner sees the dedup in the existing conflict queue. No schema changes; no new endpoints.

**New tests** — `backend/tests/domains/quickbooks/test_qb_h1_display_name_dedup.py`:
- two QB customers with identical `DisplayName` and different `Id`s → two P4T customers; the second is suffixed `(QB <Id>)`; exactly one `display_name_dedup` conflict row exists (assert by the IDs you inserted — never row counts)
- same-name update on an already-mapped customer does **not** create a duplicate (mapping-first behavior preserved)
- existing `test_sync_customer_from_qb_*` tests stay green unchanged

Intermediate run: `python -m pytest -m unit --tb=short -q 2>&1 | tail -5`

---

## Task 6 — Webhook Entity Guard + Multi-Entity Volume Test (design §F.5)

**What to change**:

1. `tasks/quickbooks_sync.py::sync_quickbooks_entity_task`: add the explicit `else` branch per design §F.5 — `logger.warning("QB webhook entity type %r not handled — event logged, no sync queued", entity_type)` + clean return (no exception → no Celery retry storm).
2. **New tests** — `backend/tests/domains/quickbooks/test_qb_h1_sync_volume.py` (all httpx mocked, `unit`-marked):
   - guard: `entity_type="Invoice"` (or any non-customer) → WARNING captured via `caplog`, task returns cleanly
   - volume: 50 QB customers across 2 mocked pages through `sync_all_customers` → 50 mappings (assert by inserted IDs), 0 conflicts
   - volume: 25 invoice pushes + 25 payment pushes (mocked QB responses) → all mappings written with `external_version_token` set

Intermediate run: `python -m pytest -m unit --tb=short -q 2>&1 | tail -5`

---

## Task 7 — Coverage Matrix Publication (design §C task 7, Appendix 1)

**What to change**: create `dev-docs/integrations/quickbooks/qb-coverage-matrix.md` from design Appendix 1.

Verification protocol (per row): re-confirm the row against the actual code (`read_file`/`grep`), correct any drift you find, fill the "(verify)" cells (`due date`, `DocNumber`, invoice-payment `LinkedTxn`, TxnTaxDetail usage), then stamp the row `verified 2026-08-28 / <your initials>`. Include:

1. The full object matrix (12 rows from Appendix 1, corrected + verified).
2. The **triage table**: in-batch fixes ✅ (display_name dedup, webhook guard, registry restore, OAuth classification, intuit_tid, conflict-email proof) vs follow-on candidates (Quote→Estimate, refund/credit-memo mapping, QB→P4T invoice/payment pull, Item sync, TxnTaxDetail, `payment` entity_type row — record your MCP answer from Pre-Work query 7, classes/departments, attachments) with a one-line scope note each. This table is Tom's QB-H2 approval gate.
3. A "Connection health / telemetry" section summarizing Tasks 2–3 end states.

No code changes in this task beyond the doc.

---

## Verification Checkpoints

- After **Task 1**: migration cycle clean (upgrade → downgrade → upgrade → current); QB test cohort green after `reset + seed`; `python migrations/scripts/seed_core.py --mode inspect` shows the trio; `pytest -m unit` green.
- After **Tasks 2–6**: `pytest -m unit` green after each task (see intermediate runs above).
- After **Task 7**: doc merged; matrix rows carry verification stamps.

---

## Regeneration + Schema Steps

- **DB model map**: no SQLModel class changes expected → `generate_db_model_map.py` not required. If you touch any model: `python generate_db_model_map.py app > db_models_map.md`.
- **Import map** (new test files added — REQUIRED): `python generate_app_import_map.py tests > app_model_imports.md`
- **Schema JSON**: no DDL (data-only migration) → `schema_manager.py` not required. The migration adds seed **rows**, not schema.
- **OpenAPI**: no endpoint changes → **do NOT run `export_openapi_json.py`** (design §D; stated explicitly because this deviates from the normal rhythm).

---

## Seed Data Rollout (Core + Scenario)

Per `backend/README-seed-data.md` — §3, §6, §7 read in Pre-Work.

### Layer 1 — Core / Platform values (Group A / B)
- `seed_core.py` (Group A): `app_service_category` (`accounting`), `app_service_provider` (`quickbooks`), global `app_service` row (deterministic UUID `00000000-0000-0000-0000-000000000aa5`, `ON CONFLICT (id) DO NOTHING`), `notification_type` `qb_connection_expired` — all idempotent; `seed`, `show`/`inspect` modes updated.
- `seed_platform.py` (Group B): 3 `qb_connection_expired` template rows (`email`/`in_app`/`push`, `tenant_id NULL`) via the existing `(code, channel)` upsert loop.
- **Migration ↔ seed parity (MANDATORY)**: the Alembic INSERTs and the seed INSERTs produce **byte-identical rows** (inclusions §20 — `seed_core.py` is the post-schema-restore recovery path). Audit columns explicit: `created_at, updated_at = NOW(), NOW()`; `created_by`/`updated_by` NULL (system rows).

### Layer 2 — Scenario data
None — no entity columns added. Tenant-scoped `app_service` connection rows remain OAuth-flow-created runtime data (never seeded).

### Verification
- `python migrations/scripts/seed_core.py --mode inspect` shows the trio + new type.
- `pytest -m unit` green after seed changes (shared-DB rule — fix any seed-resilience failure by asserting-by-ID, never by count).

### README update
- `README-seed-data.md` §4 updated (trio rows, deterministic UUID, `qb_connection_expired` type + templates); §8.1 exclusion row removed with a pointer to QB-H1.

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

# Lint + format gate (rules §23) — CHANGED FILES ONLY
CHANGED_PY=$(git diff --name-only --diff-filter=d HEAD -- '*.py' | sed 's|^backend/||')

if [ -n "$CHANGED_PY" ]; then
    ruff check --fix $CHANGED_PY
    ruff format $CHANGED_PY
    ruff check $CHANGED_PY
fi

# Full suite — vendor/live-service suites deselected (Tom's standing instruction 2026-08-16)
python -m pytest -m "not integration and not requires_telnyx and not requires_stripe and not requires_sendgrid and not requires_redis and not e2e" --tb=short -q 2>&1 | tail -15

# Batch-specific spot checks
python -m pytest tests/domains/quickbooks/ -v 2>&1 | tail -30
grep -c "def _refresh_qbo_token_impl" api/routes/integrations.py   # expect: 1
grep -rn "intuit_tid" services/quickbooks_sync.py tasks/quickbooks_token_refresh.py api/routes/integrations.py | wc -l

echo "=== QB-H1 FINAL VERIFICATION COMPLETE ==="
```

**Vendor-suite inclusion call (explicit)**: this batch does NOT touch Telnyx/Stripe/SendGrid/Redis-covered code — the vendor marker suites are **not** required. (QB tests are all httpx-mocked `unit` tests by design; no live Intuit calls.)

> **Warning-clean is part of done.** `ruff` must report no remaining issues **in your changed files**, and the pytest run must be free of `DeprecationWarning` noise. **Any failure in either phase must be fixed before the batch is declared done.** There is no "pre-existing failure" exception without explicit written confirmation from Tom.

---

## Definition of Done

Check off each item **in this prompt doc** as it completes:

- [ ] Pre-modification regression baseline captured (`X passed, Y failed`) using `pytest -m unit`
- [ ] Zero pre-existing unit failures confirmed before starting work (or confirmed with Tom)
- [ ] All 8 MCP pre-work queries run — trio state, constraints, **zero global-row references (gate)**, notification shapes, `uq_customer_tenant_display_name`, entity_type vocabulary, alembic head — and every touched table independently re-verified via `information_schema.columns` (rules §25)
- [ ] All mandatory source files read before writing any code (including the design doc in full)
- [ ] Task 1: migration `qb_h1_restore_app_service_registry` written (blank + raw SQL + `SET LOCAL session_replication_role`), full cycle tested, idempotent re-run proven
- [ ] Task 1: `seed_core.py` trio + `qb_connection_expired` added; stale NOTEs (lines 118–120, 2381–2382) removed; help text corrected; inspect manifest updated
- [ ] Task 1: `seed_platform.py` 3 templates added (byte-identical to migration)
- [ ] Task 1: teardown-collision proof executed (reset+seed → QB cohort green); README §4 updated + §8.1 row removed
- [ ] Task 2: transient/permanent classification in both refresh paths; dead sync stub deleted (exactly 1 `_refresh_qbo_token_impl` remains); `print()` → `logger`; owner notification on permanent expiry
- [ ] Task 3: `intuit_tid` arg-style logging on every QB HTTP path; `caplog` test
- [ ] Task 4: conflict-email-to-owner path proven by test (gap fixed if proven)
- [ ] Task 5: `_insert_customer_with_dedup` + `display_name_dedup` conflict subtype; 3 new tests
- [ ] Task 6: webhook unhandled-entity guard + 50-customer/25+25-push volume tests (all mocked, `unit`)
- [ ] Task 7: `dev-docs/integrations/quickbooks/qb-coverage-matrix.md` published with verified rows + triage table
- [ ] All DB-touching routes/`_impl()`/Celery tasks are sync `def`; QB service async-httpx pattern preserved; no new `async def` over the Session (rules §21)
- [ ] Only Pydantic v2 idioms used; money stays integer cents except the existing cents→dollars QB boundary conversion (rules §22)
- [ ] All new test files use `pytestmark` with `pytest.mark.domain_quickbooks` + `pytest.mark.unit`; no module-level `TestClient`; `test_tenant`/`test_user`/fixtures only (no hardcoded UUIDs); assert-by-inserted-ID (never row counts)
- [ ] `python generate_app_import_map.py tests > app_model_imports.md` run (new test files)
- [ ] Seed Data Rollout complete (Layer 1 + verification + README updates) — migration ↔ seed byte-parity confirmed
- [ ] No OpenAPI regen run (no endpoint changes — design §D)
- [ ] `ruff check --fix && ruff format` run **on changed files only** — zero remaining issues, no unjustified `# noqa` (rules §23)
- [ ] **Phase 1**: All unit tests pass (`pytest -m unit`) — zero failures including any pre-existing
- [ ] **Phase 2**: Full suite (vendor-deselected) passes — zero failures, warning-clean; vendor inclusion call recorded above
- [ ] Final test count (before → after) documented
- [ ] Completion Summary filled in at this prompt doc's ending `## Appendix — Completion Summary` (ADR-0017 — never the launch plan)
- [ ] Source spec task headers updated to ✅ Complete in `README-seed-data.md` (§8.1 row removal is the tracked change)

---

## Completion Summary

After all Definition of Done items are complete:

1. Fill in the **Completion Summary** in the appendix at the end of THIS prompt doc using the format below.
2. **Source spec update (MANDATORY)**: `README-seed-data.md` §8.1 — the trio exclusion row removal must be committed with this batch. Note the `intuit`→`quickbooks` canonization (design §G Q1) explicitly in the summary — it is a deliberate, evidence-based deviation from the launch-plan card's parenthetical that Tom must see at close.

```markdown
### QB-H1 — QuickBooks Coverage Audit + Sync Hardening: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot Python Engineer
**Baseline**: X passed, Y failed
**Final**: X+N passed, Y failed (+N new tests)

#### What Was Accomplished

- [Registry restoration: migration id + seed ownership + teardown proof result]
- [OAuth classification: branches covered; notification path]
- [intuit_tid coverage: sites list]
- [Conflict email proof: current behavior confirmed or gap fixed]
- [display_name dedup: resolution summary]
- [Volume test: counts]
- [Matrix: published path + follow-on candidates triaged]

#### Files Changed / Created

| File | Action |
|---|---|
| `backend/path/to/file.py` | Created / Updated — [what changed] |

#### Tests Added

| Test File | Domain | Tests | All Pass |
|---|---|---|---|
| `tests/domains/quickbooks/test_file.py` | `domain_quickbooks` | N | ✅ |
```

---

## After This Task — Next Step

QB-H1 closes the §7 gate row "coverage matrix published; sync hardened". The Architect flips §1.1 Ord 5 ✅, adds the one-line Appendix A registry row, and presents the matrix's **triage table** to Tom for the QB-H2 follow-on decision (Estimate sync, refund mapping, QB→P4T pulls, Item sync — design §G Q4). Post-deploy, Tom runs the prod verification (trio rows present via `postgres-prod` after his SSH tunnel is up) and QB connect smoke in prod.

---

## Appendix — Completion Summary

### QB-H1 — QuickBooks Coverage Audit + Sync Hardening: Completion Summary

**Completed**: 2026-08-28
**Mode**: Pilot Python Engineer
**Baseline**: 4662 passed, 0 failed
**Final**: 4692 passed, 0 failed (+30 new tests)

#### What Was Accomplished

- **Registry restoration**: Migration `3c69652df5d1` (qb_h1_restore_app_service_registry) + `b1f8b5f00f33` (qb_h1_add_display_name_dedup_subtype) — full cycle tested (upgrade → downgrade → upgrade → idempotent re-run). `seed_core.py` Group A now owns the trio (category `accounting`, provider `quickbooks`, global `app_service` at deterministic UUID `…000aa5`). `seed_platform.py` owns the 3 `qb_connection_expired` templates. Stale NOTEs (lines 118–120, 2381–2382) removed; help text corrected (`quickbooks_online` → `quickbooks`); inspect manifest updated. README §8.1 exclusion row removed with QB-H1 pointer. Teardown-collision proof: reset+seed → QB test cohort (376 tests) green. **`intuit`→`quickbooks` canonization** (design §G Q1) — deliberate, evidence-based deviation from the launch-plan card's parenthetical; ~30 code call sites use `quickbooks`, zero use `intuit`.
- **OAuth classification**: `_classify_refresh_error()` in both `tasks/quickbooks_token_refresh.py` (beat task) and `api/routes/integrations.py` (async route). Transient (5xx/TransportError/timeout) → log WARNING, leave `active`, count `transient_failed`. Permanent (invalid_grant/400/401) → mark `expired` + enqueue `qb_connection_expired` notification to tenant owner via `services/qb_connection_notification.py`. Dead sync stub deleted (exactly 1 `_refresh_qbo_token_impl` remains). All `print()` → `logger`.
- **intuit_tid coverage**: 8 log sites total — 5 existing in `services/quickbooks_sync.py` (customer CRUD, query, fetch, invoice push, payment push) + 3 new (`tasks/quickbooks_token_refresh.py::_refresh_access_token`, `api/routes/integrations.py::_exchange_code_for_tokens`, `api/routes/integrations.py::_refresh_access_token`). All arg-style `%s` interpolation.
- **Conflict email proof**: `queue_conflict` resolves to the tenant owner's email (verified — existing behavior confirmed correct, no gap found).
- **display_name dedup**: Pre-check collision detection in `_insert_customer_with_dedup` → suffix `(QB <Id>)` + `display_name_dedup` conflict row. Migration `b1f8b5f00f33` added `display_name_dedup` to the `integration_sync_conflict_subtype_chk` CHECK constraint.
- **Volume test**: 50 QB customers synced via mocked query → 50 mappings, 0 conflicts, 0 failures. Webhook guard: Estimate/CreditMemo/Payment entity types → WARNING + clean return (no Celery retry storm).
- **Matrix**: Published at `dev-docs/integrations/quickbooks/qb-coverage-matrix.md` with 12 verified rows + triage table (6 in-batch fixes ✅, 9 follow-on candidates for QB-H2).

#### Files Changed / Created

| File | Action |
|---|---|
| `backend/migrations/versions/2026_08_28_1431-3c69652df5d1_qb_h1_restore_app_service_registry.py` | Created — data migration: trio restoration + `qb_connection_expired` type/templates |
| `backend/migrations/versions/2026_08_28_1530-b1f8b5f00f33_qb_h1_add_display_name_dedup_subtype.py` | Created — DDL migration: add `display_name_dedup` to CHECK constraint |
| `backend/migrations/scripts/seed_core.py` | Updated — trio added to SIMPLE_CODE_TABLES; global app_service block; `qb_connection_expired` in notification_type; stale NOTEs removed; help text fixed; inspect manifest updated |
| `backend/migrations/scripts/seed_platform.py` | Updated — 3 `qb_connection_expired` template-copy entries added |
| `backend/services/quickbooks_sync.py` | Updated — `_insert_customer_with_dedup` + `_queue_display_name_dedup_conflict`; imports fixed (E402) |
| `backend/services/qb_connection_notification.py` | Created — shared `enqueue_connection_expired_notification` helper |
| `backend/tasks/quickbooks_token_refresh.py` | Updated — `_classify_refresh_error`, `TokenRefreshOutcome` (StrEnum), transient/permanent classification, `print()`→`logger`, `intuit_tid` logging, `transient_failed` return field |
| `backend/tasks/quickbooks_sync.py` | Updated — webhook entity guard (WARNING + clean return for unhandled types) |
| `backend/api/routes/integrations.py` | Updated — dead sync stub deleted; async `_refresh_qbo_token_impl` classification + RFC 7807; `intuit_tid` logging on token exchange + refresh; whitespace/noqa fixes |
| `backend/README-seed-data.md` | Updated — §8.1 exclusion row removed with QB-H1 pointer |
| `backend/app_model_imports.md` | Regenerated — new test files |
| `dev-docs/integrations/quickbooks/qb-coverage-matrix.md` | Created — coverage matrix + triage table |
| `backend/tests/domains/quickbooks/test_qb_h1_app_service_seed.py` | Created — 9 tests (trio + notification verification) |
| `backend/tests/domains/quickbooks/test_qb_h1_token_refresh.py` | Created — 13 tests (classification + intuit_tid) |
| `backend/tests/domains/quickbooks/test_qb_h1_conflict_owner_notification.py` | Created — 1 test (owner email resolution) |
| `backend/tests/domains/quickbooks/test_qb_h1_display_name_dedup.py` | Created — 3 tests (dedup collision + mapping-first + normal create) |
| `backend/tests/domains/quickbooks/test_qb_h1_sync_volume.py` | Created — 4 tests (webhook guard + 50-customer volume) |

#### Tests Added

| Test File | Domain | Tests | All Pass |
|---|---|---|---|
| `tests/domains/quickbooks/test_qb_h1_app_service_seed.py` | `domain_quickbooks` | 9 | ✅ |
| `tests/domains/quickbooks/test_qb_h1_token_refresh.py` | `domain_quickbooks` | 13 | ✅ |
| `tests/domains/quickbooks/test_qb_h1_conflict_owner_notification.py` | `domain_quickbooks` | 1 | ✅ |
| `tests/domains/quickbooks/test_qb_h1_display_name_dedup.py` | `domain_quickbooks` | 3 | ✅ |
| `tests/domains/quickbooks/test_qb_h1_sync_volume.py` | `domain_quickbooks` | 4 | ✅ |

#### Notes

- **No OpenAPI regen run** (no endpoint changes — design §D).
- **No DB model map regen** (no SQLModel class changes).
- **Vendor-suite inclusion call**: this batch does NOT touch Telnyx/Stripe/SendGrid/Redis-covered code — vendor marker suites not required.
- **`payment` `entity_type` row absent** (MCP-verified) — flagged as QB-H2 follow-on candidate. Payment sync mappings use `entity_type_code="payment"` which may FK-fail.
- **`CustomerRef.value` bug** in `sync_payment_to_qb` (set to `invoice_id` not `customer_id`) — flagged as QB-H2 follow-on candidate.
- **Invoice push volume test** deferred (flex candidate per design §G Q5) — the 50-customer volume test + webhook guard tests cover the core Task 6 requirements.
