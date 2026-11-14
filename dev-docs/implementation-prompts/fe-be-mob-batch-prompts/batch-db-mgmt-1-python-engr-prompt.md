# Implementation Prompt: DB-MGMT-1 — DB Management Strategy (Schema-Restore Provisioning + Environment-Aware Seeds)

**Mode**: Pilot Python Engineer
**Batch**: DB-MGMT-1
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §DB-MGMT-1 (Order 3, item 5)
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-db-mgmt-1-design.md` v1.1 ✅ APPROVED 2026-08-18
**Binding decision**: ADR-0016 (schema-restore provisioning + env-aware seeds; migrations DDL-only)
**Estimated session**: 5–6 hours
**Platform**: Backend tooling only (`backend/migrations/scripts/` + `backend/tests/`) — **no API endpoints, no models, no migrations**
**Frontend companion**: none

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-python-engineer/python-engineer-rules.md`** — full document; the 25 hard rules are non-negotiable STOPs
- **`dev-docs/architecture-design/pilot-python-engineer-methods.md`** — §16 (Standard Task Workflow); §13 (Alembic) for context only — **this batch authors NO migrations**
- **`backend/tests/README-adding-tests.md`** — full document; governs all test file structure, domain markers, fixture rules
- **`dev-docs/architecture-design/batch-designs/batch-db-mgmt-1-design.md`** — the full design (v1.1); §B matrices, §F interfaces, and §G decisions are your spec

Critical rules for this batch:

- **Rule 1 / 16 / 25**: Never guess column names, table names, or constraint names. Use `postgres-local` MCP to verify every name before use. If MCP returns an error → **STOP and ask Tom**.
- **Rule 7 (MCP read-only)**: `postgres-local` MCP is for **read-only verification only**. Never INSERT/UPDATE/DELETE through it — all data changes go through seed scripts or application code.
- **Rule 11**: If ANY test fails during your work — even one that appears pre-existing — fix it before declaring the batch done. No "not my fault" exception. If you cannot identify the root cause → STOP and ask Tom.
- **Rule 14/§23 (Ruff)**: Run ruff on **changed files only** (`git diff --name-only --diff-filter=d HEAD -- '*.py' | sed 's|^backend/||'`), fix ALL errors in those files including pre-existing ones, no unjustified `# noqa`.
- **Seed DELETE safety (Rule 11.1, architect rules)**: `mode_seed` DELETEs must be value-scoped (include the full business key, e.g. `value` or `sku`), never channel-/class-scoped. `ON CONFLICT DO NOTHING` requires a verified unique constraint — verify via MCP before relying on it.
- **ADR-0016 contract (new, binding)**: Every seed script accepts `--env {dev,e2e,qa,prod}` (or `SEED_ENV`), resolved through `_env_profiles.py`; prod runs Groups A+B only; env-specific values come from the profile registry, never hardcoded in script bodies. **`--env` is decoupled from pydantic `ENVIRONMENT`** — never assign it to `settings.ENVIRONMENT` (its literal rejects `e2e`; see `core/config.py` line 57).

---

## Pre-Work: Establish Regression Baseline

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=no -q 2>&1 | tail -5
```

Record the exact count: **`X passed, Y failed`**. If any tests are already failing: confirm with Tom or fix them before touching any batch files. You may NOT start while tests are in an unexplained failed state.

---

## Pre-Work: Run MCP Verification Queries

> **MCP Usage Rule**: `postgres-local` is **read-only verification only**; never INSERT/UPDATE/DELETE. On any error → STOP and ask Tom. (`postgres-prod` exists but is **not used in this batch** — the prod seed run is executed by Tom, not the engineer.)

Run **all** of these via `postgres-local` MCP before writing any code. Expected values come from the Architect's 2026-08-17/18 session — if any result differs, note the discrepancy in your Completion Summary and proceed with the MCP-returned truth.

```sql
-- 1. Current alembic head (expect 58c3ad26129f)
SELECT version_num FROM public.alembic_version;

-- 2. subscription_tier current values (expect: charter monthly price_REDACTED09 / annual NULL;
--    starter + teams test-mode IDs; trial NULL/NULL)
SELECT tier_name, is_active, stripe_price_id_monthly, stripe_price_id_annual
FROM public.subscription_tier ORDER BY display_order;

-- 3. pricebook_item constraint verification (expect uq_pricebook_item_tenant_sku UNIQUE (tenant_id, sku))
SELECT conname, contype, pg_get_constraintdef(oid)
FROM pg_constraint WHERE conrelid = 'public.pricebook_item'::regclass;

-- 4. pricebook_item_version columns (expect: id bigint PK, pricebook_item_id uuid,
--    tenant_id uuid NOT NULL, default_unit_price_cents integer NOT NULL,
--    valid_period tstzrange NOT NULL, recorded_at, + audit cols) AND any exclusion
--    constraints (contype='x') — the GiST overlap rule governs valid_period writes
SELECT column_name, data_type, is_nullable FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'pricebook_item_version' ORDER BY ordinal_position;
SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint
WHERE conrelid = 'public.pricebook_item_version'::regclass AND contype = 'x';

-- 5. Seed-state manifest counts vs README §4 (expect: platform_setting_catalog 48,
--    communication_template 17, notification_type 17, notification_template 58 platform-default
--    (README says 41 — drift you will reconcile), job_type 11, email_template 16,
--    quote_template 3, quote_template_line 9, product_plan 3, subscription_tier 4)
SELECT 'platform_setting_catalog' AS t, COUNT(*) FROM public.platform_setting_catalog
UNION ALL SELECT 'communication_template', COUNT(*) FROM public.communication_template
UNION ALL SELECT 'notification_type', COUNT(*) FROM public.notification_type
UNION ALL SELECT 'notification_template_defaults', COUNT(*) FROM public.notification_template WHERE tenant_id IS NULL
UNION ALL SELECT 'job_type', COUNT(*) FROM public.job_type
UNION ALL SELECT 'email_template', COUNT(*) FROM public.email_template
ORDER BY t;
```

---

## Pre-Work: Read These Source Files

Use `read_file` on each before writing any code:

```
dev-docs/architecture-design/batch-designs/batch-db-mgmt-1-design.md  ← your spec (§B matrices, §F interfaces, §G decisions)
backend/README-seed-data.md                                           ← full doc: Group A–D model, run order, §7 gotchas (DELETE safety, GiST, reserved UUIDs)
backend/migrations/scripts/_db_utils.py                               ← get_db_session(db_url) seam — DATABASE_URL read at call time
backend/migrations/scripts/seed_core.py                               ← Group A structure, _upsert patterns, --mode contract
backend/migrations/scripts/seed_platform.py                           ← Group B; lines 311–332 + 378–390 hold the hardcoded test-mode Stripe IDs you will replace
backend/migrations/scripts/seed_test_tenant.py                        ← Group C; --reset countdown pattern
backend/migrations/scripts/reset_dev_db.py                            ← wipe tool; gains env gating (refuses e2e/prod)
backend/migrations/scripts/seed_scenario_quote_to_cash.py             ← representative Group D script (argparse + mode wiring to replicate)
backend/migrations/scripts/seed_scenario_tenant_site.py               ← newest script; ON CONFLICT (tenant_id) pattern
backend/tests/e2e/init_e2e_schema.py                                  ← the schema-restore reference you are generalizing (incl. the 24-table UUID-default patch list, lines 148–174)
backend/tests/e2e/seed_e2e_db.py                                      ← orchestrator pattern + ENVIRONMENT=dev override comment (lines 49–56)
backend/core/config.py                                                ← line 57: ENVIRONMENT Literal["dev","qa","staging","production"] — why --env is decoupled
docker-compose.e2e.yml                                                ← E2E DB is port 5434 (5433 = prod SSH tunnel; README says 5433 — you will fix that drift)
dev-docs/integrations/stripe/stripe-pricing-config.md                 ← §4: canonical test + live price IDs (copy from here, never from memory)
dev-docs/pilot-operations.md                                          ← tier→plan→ppfv cascade + subscription status semantics (context for seed_platform values)
dev-docs/devops/aws-env-mgmt-ops-plan.md                              ← §§1–5: env phase model + vendor test modes (the posture your registry encodes)
dev-docs/db-design/postgres-mcp-guide.md                              ← MCP query patterns
```

Also run: `grep -rn "price_1" backend/migrations/scripts/ --include="*.py"` to find every hardcoded Stripe ID in seed scripts.

---

## Background / Context

Today, only dev is properly seeded (migrations + seed scripts); e2e uses a schema-restore + seed re-route; prod was provisioned by migrations with migration-embedded data and has drifted (SEED-FIX-1, 2026-08-09), and Stripe price IDs were flipped in prod via one-off SQL. ADR-0016 replaces this: **every env is provisioned by schema-restore from dev at alembic head, then populated by env-aware seed scripts; migrations are DDL-only going forward.**

Environments differ in vendor posture (design §B.3): prod is the Phase 1 integration env running uniform vendor **test** modes (`sk_test_` keys in `pilot/prod/stripe`); dev runs real QuickBooks-sandbox / Cognito-dev-pool / SendGrid-shared; e2e is fully mocked; Telnyx is mock outside prod until Phase 2 QA (real profile + number — Tom, Option A). The seed layer must know which env it is populating so env-coupled values (Stripe price IDs, Stripe customer IDs, phone numbers) match the target's posture, and it must **fail closed** on mismatch. Founder signup is gated on this batch.

**Hard safety rails (from design §B.4 / §F.1):**
- prod = Groups A+B only. Group C/D scripts invoked with `--env prod` exit non-zero with an explicit message. `reset_dev_db.py` refuses `e2e`/`prod`.
- `--env prod` requires `--stripe-mode {test|live}` — no default — plus a Secrets preflight (below). `--stripe-mode live` with a non-prod env is rejected.
- Bidirectional host guard: non-prod profiles refuse RDS hosts; prod profile refuses the localhost dev DB.
- Existing prod is **converged in place** (idempotent re-runs), never wiped. You validate dry-runs only — **Tom executes the real prod run.**

---

## Task 1 — `_env_profiles.py` registry + `--env` rollout (12 scripts)

**Create `backend/migrations/scripts/_env_profiles.py`** implementing design §F.1 exactly:

- `SeedEnv(str, Enum)` = dev / e2e / qa / prod; `StripeMode(str, Enum)` = test / live.
- `EnvProfile` frozen dataclass: `env`, `allowed_groups: frozenset[str]` (prod `{"A","B"}`; others `{"A","B","C","D"}`), `stripe_mode: StripeMode | None` (dev/e2e/qa hardwired TEST; prod None = caller must supply), `stripe_price_ids` mapping (tier → `{"monthly": ..., "annual": ...}` — both modes; source IDs from `stripe-pricing-config.md §4`), `allowed_db_host_patterns` / `forbidden_db_host_patterns`, `require_typed_confirmation: bool`, `vendor_posture: Mapping[str, str]` (design §B.3: e.g. dev = `{"quickbooks": "sandbox", "cognito": "dev-pool", "sendgrid": "shared", "telnyx": "mock", "stripe": "test"}`).
- `resolve_seed_env(cli_value)` — precedence `--env` > `SEED_ENV` env var > default `dev`; unknown value → `SystemExit` with usage message. **Never touches pydantic settings.**
- `get_profile(env, stripe_mode)` — fail-closed: prod without stripe_mode → SystemExit; `--stripe-mode live` with non-prod → SystemExit.
- `assert_target_compatible(profile, database_url)` — runs before any connection opens. prod: requires RDS host or `localhost:5433` (the tunnel port); refuses `:5432/pilot_dev`. non-prod: refuses hosts containing `rds.amazonaws.com`.
- `print_seed_banner(profile, database_url, script_name)` — every run prints: script, resolved env, stripe_mode, vendor_posture, host/dbname, allowed groups.
- `verify_stripe_key_alignment(profile, secret_id)` — prod/remote preflight via `subprocess` `aws secretsmanager get-secret-value --secret-id <secret_id>` (no boto3 dependency; matches the psql-subprocess pattern in `init_e2e_schema.py`): `sk_test_` must pair with TEST, `sk_live_` with LIVE. Unreadable secret → refuse unless `--skip-preflight` (loud warning). Auto-skipped for local dev/e2e/qa.

**Add the standard argparse block to all 12 seed scripts** (`seed_core`, `seed_platform`, `seed_test_tenant`, 8× `seed_scenario_*`, `reset_dev_db`): identical `--env` wiring, banner call at start of `seed`/`inspect` modes, `assert_target_compatible` before any DB work, and group gating (a Group C/D script with a prod profile exits non-zero; `reset_dev_db.py` accepts only `dev`/`qa-local`). Default behavior with no flags must be byte-for-byte equivalent to today (dev profile).

**Inventory sub-deliverable (design §G-7/G-8):** verify the §B.3 env-value matrix against the live DB and scripts; **classify the charter price ID `price_REDACTED09`** (search `backend/scripts/stripe_ids.test.json`, C-B14/C-B11 artifacts, and `stripe-pricing-config.md`; if it cannot be confirmed test-or-live from repo artifacts, flag it to Tom in the Completion Summary and leave the charter row untouched by prod converge). Land the completed matrix as a new §B.3-equivalent table in `README-seed-data.md`.

Intermediate check: `python -m pytest -m unit --tb=short -q 2>&1 | tail -5` + manual smoke: `python migrations/scripts/seed_core.py --env dev --mode show | head -20` shows the banner.

## Task 2 — `seed_platform.py` env-aware Stripe resolution + converge

- Replace the hardcoded test-mode price IDs (lines 311–332, 378–390) with registry lookups from the resolved profile.
- Add an idempotent **converge-UPDATE** path: on `seed` mode, `UPDATE subscription_tier SET stripe_price_id_monthly=..., stripe_price_id_annual=... WHERE tier_name=...` for the 4 slots across starter/teams (and charter ONLY if its ID was classified in Task 1), so re-running with a different `--stripe-mode` flips modes cleanly (this retires the one-off SQL in `stripe-pricing-config.md §4`). Converge only touches the 5 price-ID columns — never pricing/lifecycle columns.
- `--mode show` prints which IDs *would* be written per tier without touching the DB.

## Task 3 — `provision_schema.py` (generalize the E2E reference)

Create `backend/migrations/scripts/provision_schema.py` per design §F.2: `--env {e2e|qa|prod}`; steps = guard → `pg_dump --schema-only` from local `pilot_dev` (or accept `--schema-dump PATH`) → `psql -f` apply to `DATABASE_URL` → patch `gen_random_uuid()` defaults on the 24 lookup tables (carry the list over from `init_e2e_schema.py` lines 148–174 verbatim) → `alembic stamp head` → write a dated dump artifact to `dev-docs/db-design/dbbackups/` → print the next-step seed command. The prod mode is double-gated (`--i-understand-prod-rebuild` + interactive confirmation) and documented as rebuild-only. Rewrite `tests/e2e/init_e2e_schema.py` as a thin wrapper delegating to `--env e2e` (existing CLI signature keeps working — positional dump path + same guards).

## Task 4 — `seed_qa_db.py` + scratch-DB proof

Create `backend/migrations/scripts/seed_qa_db.py` per design §F.3: orchestrates Groups A→B→C→D with **all 8** scenario scripts, propagating `SEED_ENV=qa` + `DATABASE_URL` to children. Prove end-to-end against a scratch local DB:

```bash
createdb -h localhost -p 5432 -U pilot pilot_qa_scratch
DATABASE_URL=postgresql://pilot:pilot@localhost:5432/pilot_qa_scratch python migrations/scripts/provision_schema.py --env qa
DATABASE_URL=postgresql://pilot:pilot@localhost:5432/pilot_qa_scratch python migrations/scripts/seed_qa_db.py
DATABASE_URL=postgresql://pilot:pilot@localhost:5432/pilot_qa_scratch python migrations/scripts/seed_core.py --env qa --mode inspect
# inspect counts must match the dev baseline manifest (Pre-Work query 5)
dropdb -h localhost -p 5432 -U pilot pilot_qa_scratch
```

(Adjust local credentials to your dev compose file.) Capture the inspect output for the Completion Summary.

## Task 5 — `seed_prod_db.py` (converge-in-place orchestrator)

Create `backend/migrations/scripts/seed_prod_db.py` per design §F.4: typed confirmation `PILOT-PROD-SEED` (required for `seed` mode only) → `verify_stripe_key_alignment("pilot/prod/stripe")` → `seed_core.py --env prod` → `seed_platform.py --env prod --stripe-mode <mode>` → inspect summary vs manifest. `--mode show|inspect` requires no confirmation and opens no writes. Validate with `--mode show` locally (pointless-host guard will correctly refuse to run it against dev for `seed` mode — capture that refusal as guard evidence). **Do not run the real prod converge — that is Tom's step.**

## Task 6 — `seed_pricebook_starter.py` + JSON catalog

Per design §F.5 (decision §G-5: `pricebook_item.tenant_id` is NOT NULL — per-tenant seeding, MCP-verified):

- New script + `backend/migrations/scripts/data/pricebook_starter/default_catalog.json` — starter electrical catalog (~10–15 items: sku, name, description, uom, taxability_code, unit price in cents). **Catalog content is gated on Tom's sign-off** — ship a first-pass list in the PR description/summary for his review; do not run against prod until he approves content.
- CLI: `--env {dev,qa,prod} --tenant-id <uuid> [--mode seed|show|inspect]`.
- Idempotency: `INSERT ... ON CONFLICT (tenant_id, sku) DO NOTHING` — the `uq_pricebook_item_tenant_sku` unique constraint is **MCP-verified to exist** (Pre-Work query 3), so no DELETE path is needed.
- For each item also insert one current `pricebook_item_version` row (`default_unit_price_cents` int NOT NULL; `valid_period` tstzrange NOT NULL — **check Pre-Work query 4 for an exclusion constraint**; if present, use a single open-ended range per item starting at a past date, per the README §7 GiST caveat).
- Add the concierge step to `dev-docs/pilot-founder-onboarding-process.md` Stage C: "run `seed_pricebook_starter.py --env prod --tenant-id <new tenant>` after tenant provisioning."

## Task 7 — Runbooks + doc reconciliation

Land into `README-seed-data.md` (new sections): (a) the completed env-value/posture matrix (from Task 1); (b) the per-env provisioning runbook (design §H.1); (c) the migration-sync runbook (design §H.2 — incl. the ADR-0016 DDL-only rule: migration-embedded INSERTs are a review reject; new reference data ships in `seed_core.py`/`seed_platform.py` in the same PR). Fix the two known drifts: E2E DB port **5434** (not 5433 — that is the prod tunnel) and `notification_template` platform-default count **58** (not 41). Add a cross-reference in `dev-docs/devops/aws-ops-runbook.md` to the new runbook sections. File the charter price-ID follow-up for `stripe-pricing-config.md §4` (Integrations Lead owns; note it in the Completion Summary for the Architect to verify).

---

## Verification Checkpoints

- After Task 1: unit suite green; `--mode show` banners on 3 scripts; group-gate refusal demos (`seed_scenario_quote_to_cash.py --env prod` exits non-zero).
- After Task 2: `seed_platform.py --env dev --mode show` prints test-mode IDs; `--stripe-mode live` with `--env dev` refused.
- After Task 4: scratch `pilot_qa_scratch` inspect counts == dev baseline manifest.
- After Task 5: `seed_prod_db.py --mode show` output + the host-guard refusal captured.

---

## Regeneration Steps

- **OpenAPI / `export_openapi_json.py`**: NOT applicable — no endpoints changed. Do not run `pnpm sync-api-types`.
- **`db_models_map.md` / `schema_manager.py`**: NOT applicable — no model or schema changes.
- **`app_model_imports.md`**: REQUIRED if you add test files (you will):
  ```bash
  cd <repo>/backend && source .venv/bin/activate
  python generate_app_import_map.py tests > app_model_imports.md
  ```

---

## Final Verification

### Phase 1 — Unit Tests Only (after each task)

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=short -q 2>&1 | tail -10
```

All unit tests must pass before moving to the next task — including failures that appear to come from outside your batch.

### Phase 2 — Lint (changed files only) + Full Suite, Vendor-Deselected (once, at the end)

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

# Vendor-suite inclusion call (explicit, per standing rule): this batch touches NO runtime
# vendor-covered code (seed/tooling scripts only; no telnyx*/Stripe billing/SendGrid/Redis
# runtime paths) — vendor marker suites are NOT required. If you find yourself modifying
# any services/telnyx*, Stripe, SendGrid, or Redis-covered module, STOP — that is out of scope.

# Spot checks
python migrations/scripts/seed_core.py --env dev --mode inspect | head -15
python migrations/scripts/seed_platform.py --env dev --mode show | head -25

echo "=== DB-MGMT-1 FINAL VERIFICATION COMPLETE ==="
```

> Warning-clean is part of done: no remaining ruff issues in changed files; pytest free of `DeprecationWarning` noise. Any failure in either phase must be fixed before done — no "pre-existing" exception without Tom's written confirmation.

---

## Test Requirements

Per `backend/tests/README-adding-tests.md`. New test file(s) under `backend/tests/domains/platform_infrastructure/` (e.g. `test_seed_env_profiles.py`, `test_seed_platform_env.py`):

- `pytestmark = [pytest.mark.domain_platform_infrastructure, pytest.mark.unit]` in every new file.
- Profile-resolution tests are pure logic (no DB): precedence (flag > `SEED_ENV` > default), unknown env → SystemExit, prod without `--stripe-mode` → SystemExit, `--stripe-mode live` + non-prod → SystemExit, group gating, host guards (prod↔localhost-dev and non-prod↔RDS refusals), price-ID map selection per mode, banner output (capsys).
- DB-touching tests use the `db_session` fixture (transaction rollback): e.g., `seed_platform` converge against the real `subscription_tier` rows is safe inside `db_session` (rollback undoes it) — assert the 4 slots flip test→live→test; pricebook-starter insert for `second_tenant` run twice → rows scoped by that tenant unchanged on re-run (assert by inserted IDs, never table counts).
- Never hardcode the reserved UUIDs (`...0001`–`...0005`); use `test_tenant`/`second_tenant` fixtures.
- Target: **≥12 new tests**, all passing.

---

## Seed Data Rollout (Core + Scenario)

Per `backend/README-seed-data.md` — §3, §6, §7 read in Pre-Work.

### Layer 1 — Core / Platform values (Group A / B)
- This batch's Group B change **is** the seed rollout: Stripe price IDs move from hardcoded script bodies into the env-profile registry; `seed_platform.py` `seed`/`show`/`inspect` modes all reflect the resolved profile. No new lookup rows are added.
- Charter price-ID row: updated only if Task 1 classifies `price_REDACTED09`; otherwise prod converge leaves charter untouched (documented in Completion Summary).

### Layer 2 — Scenario data (Group D)
- **Not applicable**: no scenario columns or values change; scenario scripts gain only the `--env` flag + gating.

### Verification
- `python migrations/scripts/seed_core.py --mode inspect` + `python migrations/scripts/seed_platform.py --env dev --mode inspect` after changes; scratch-qa inspect counts == dev manifest (Task 4); `pytest -m unit` green after seed changes (shared-DB rule).

### README update
- `README-seed-data.md`: new env-matrix + runbook sections (Task 7), §4 drift fixes (port 5434 note lives in §6 E2E commands; `notification_template` 58), script inventory table gains the 4 new scripts.

---

## Definition of Done

Update `pilot-launch-plan.md` §DB-MGMT-1 task rows when each item is done:

- [ ] Pre-modification regression baseline captured (`X passed, Y failed`) using `pytest -m unit`
- [ ] Zero pre-existing unit failures confirmed before starting (or confirmed with Tom)
- [ ] All 5 MCP pre-work queries run — alembic head, tier values, `uq_pricebook_item_tenant_sku`, `pricebook_item_version` columns + exclusion check, manifest counts confirmed (discrepancies noted in Completion Summary)
- [ ] All mandatory source files read (incl. `seed_platform.py` price-ID lines and `init_e2e_schema.py` UUID-patch list)
- [ ] Task 1: `_env_profiles.py` + `--env`/`SEED_ENV` on all 12 scripts + banner + guards + group gating; env-value matrix completed; charter price ID classified or explicitly flagged to Tom
- [ ] Task 2: `seed_platform.py` registry-driven IDs + idempotent converge-UPDATE (5 slots; charter conditional)
- [ ] Task 3: `provision_schema.py` + `init_e2e_schema.py` wrapper; E2E setup flow still works (`tests/e2e` README commands unchanged)
- [ ] Task 4: `seed_qa_db.py` + scratch `pilot_qa_scratch` end-to-end proof (inspect == dev manifest), scratch DB dropped
- [ ] Task 5: `seed_prod_db.py` with typed confirmation + preflight + dry-run modes; guard evidence captured; **no real prod run by engineer**
- [ ] Task 6: `seed_pricebook_starter.py` + JSON catalog (content sent to Tom for sign-off; not run against prod); founder-onboarding Stage C step added
- [ ] Task 7: runbooks + env matrix in `README-seed-data.md`; port 5434 + `notification_template` 58 drift fixed; `aws-ops-runbook.md` cross-ref; charter follow-up filed
- [ ] ≥12 new unit tests in `tests/domains/platform_infrastructure/`, `pytestmark` correct, all passing
- [ ] No module-level `TestClient`; no hardcoded reserved UUIDs; assertions scoped by inserted IDs
- [ ] `python generate_app_import_map.py tests > app_model_imports.md` run (new test files)
- [ ] `ruff check --fix && ruff format` on changed files only — zero remaining issues, no unjustified `# noqa`
- [ ] **Phase 1**: all unit tests pass — zero failures
- [ ] **Phase 2**: vendor-deselected full suite passes — zero failures, warning-clean; vendor-suite inclusion call recorded (expected: not required — tooling only)
- [ ] Final test count (before → after) documented
- [ ] Completion Summary added to `pilot-launch-plan.md` §DB-MGMT-1 (Appendix C format)

---

## Completion Summary

After all DoD items are complete:

1. Add a **Completion Summary** to `pilot-launch-plan.md` Appendix C and flip the §DB-MGMT-1 task rows to ✅.
2. This batch also closes the "Design batch / Inventory / QA DB seed scripts / Production DB seed scripts / Sync runbook" rows in the §DB-MGMT-1 task table — update each with a one-line outcome. (The launch plan is the tracker for this batch; no other source spec has ☐ rows for it.)

```markdown
### DB-MGMT-1 — DB Management Strategy: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot Python Engineer
**Baseline**: X passed, Y failed
**Final**: X+N passed, Y failed (+N new tests)

#### What Was Accomplished
- [env-profile registry + --env rollout; seed_platform converge; provision_schema; qa/prod orchestrators; pricebook starter; runbooks; charter ID classification outcome]

#### Files Changed / Created
| File | Action |
|---|---|
| `backend/migrations/scripts/_env_profiles.py` | Created — ... |
| ... | ... |

#### Tests Added
| Test File | Domain | Tests | All Pass |
|---|---|---|---|
| `tests/domains/platform_infrastructure/test_seed_env_profiles.py` | `platform_infrastructure` | N | ✅ |
```

---

## After This Task — Next Step

Hand back to Tom: he runs `seed_prod_db.py --mode inspect` and then the real prod converge (`--stripe-mode test`) when ready, and signs off on the pricebook starter catalog content before its first prod use. Batch close-out unblocks UI-INT-TEST resumption (QA seed density) and positions SD-9 / SD-DEFER as the following seed-line items. The Architect verifies the `stripe-pricing-config.md §4` charter-ID follow-up lands with the Integrations Lead.
