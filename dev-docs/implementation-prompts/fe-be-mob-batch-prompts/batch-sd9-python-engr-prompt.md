# Implementation Prompt: SD-9 — Voice AI Seed Data (`seed_scenario_voice_ai.py` + Second-Tenant Seed)

**Mode**: Pilot Python Engineer
**Batch**: SD-9
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §2.3 SD-9 (Order 3 enabler; named trigger for resuming the deferred UI-INT-TEST full regression)
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-sd9-design.md` v1.0 ✅ APPROVED — **the binding specification; the content manifests in its §F are authoritative**
**Estimated session**: 4–5 hours
**Platform**: Backend only (`backend/` — seed tooling; no runtime code, no endpoints, no migrations)
**Frontend companion**: none — but this batch makes the web Voice AI History / Session Detail surfaces (`/voice`) demonstrable

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-python-engineer/python-engineer-rules.md`** — full document; the 25 hard rules are non-negotiable STOPs
- **`dev-docs/architecture-design/pilot-python-engineer-methods.md`** — §16 (Standard Task Workflow)
- **`backend/tests/README-adding-tests.md`** — full document; governs test file structure, domain markers, fixture rules, and the Test Resilience Rule
- **`dev-docs/architecture-design/batch-designs/batch-sd9-design.md`** — full document; §F content manifests are the spec you implement

Critical rules for this batch:

- **Rule 1**: Never guess column names, data types, or table names. Use `postgres-local` MCP to verify every name before use. If MCP returns an error → **STOP and ask Tom**.
- **Rule 7**: The `postgres-local` MCP is for **read-only verification only**. Never use it to INSERT, UPDATE, or DELETE data — all data changes go through the seed scripts you are writing.
- **Rule 16 (verify, don't assume — rules §25)**: 186+ tables exist. Query `information_schema.columns` for every table you touch this session before writing SQL — the design doc's column lists are MCP-verified as of 2026-08-18 but the live DB is the only authority at implementation time.
- **Rule 11**: If ANY test fails during your work — even one that appears pre-existing — fix it before declaring the batch done. If you cannot identify the root cause → STOP and ask Tom.
- **Rule 14 (Ruff — rules §23)**: Run ruff **only against the files you changed** (`git diff --name-only --diff-filter=d HEAD -- '*.py' | sed 's|^backend/||'`), fix ALL errors in those files including pre-existing ones, no unjustified `# noqa`.
- **Seed DELETE safety (Rule 11.1 / README §7)**: `mode_seed` performs **zero DELETEs** (existence-check-then-insert only). `mode_reset` may full-wipe only the scenario-owned tables for the tenant(s) the scenario owns. Never delete rows outside your scenario's ownership.
- **Env gating (DB-MGMT-1)**: `seed_second_tenant.py` asserts group `"C"`; `seed_scenario_voice_ai.py` asserts group `"D"` — both are prod-refused by `_env_profiles.py`. Wire the standard banner + guards on both scripts.
- **Test Resilience Rule (README-adding-tests)**: your tests call the **injectable inner functions** (`_seed_voice_ai(db_session, …)` etc.) against the rollback-wrapped `db_session` fixture. **Never** call `mode_seed`/`mode_reset` from a test — they open their own engine and commit to the shared dev DB.

---

## Pre-Work: Establish Regression Baseline

Before touching any file, capture the current **unit-only** test baseline:

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=no -q 2>&1 | tail -5
```

Record the exact count: **`X passed, Y failed`** (post-DB-MGMT-1 baseline: 4631 passed, 1 skipped, 0 failed).

> **If any tests are already failing before you start**: Do NOT treat them as "pre-existing" and proceed anyway. Either (a) confirm with Tom that it is a known, accepted failure, or (b) fix it before touching any batch files. You may NOT start implementation work while tests are in an unexplained failed state.

---

## Pre-Work: Run MCP Verification Queries

> **MCP Usage Rule**: The `postgres-local` MCP is for **read-only verification only**. Use it to confirm table names, column types, and existing data. Never use it to INSERT, UPDATE, or DELETE — all data changes go through the application code, seed scripts, or Alembic migrations. If a query fails or returns an error → STOP and ask Tom before proceeding.
>
> **Two read-only MCP servers exist** (global rule `.roo/rules/02-database-mcp-access.md`): **`postgres-local`** is the default for all verification. **`postgres-prod`** reads production but **requires an SSH tunnel that only Tom controls** — ask Tom to confirm the tunnel is up before your first `postgres-prod` query, and STOP on any connection error. This batch needs **`postgres-local` only** (Group C/D scripts are prod-refused by design).

Run **all** of these via `postgres-local` MCP before writing any code. If any query returns unexpected results → **STOP and ask Tom**.

```sql
-- 1. Column dumps for all 5 voice tables (the design's §A table is from 2026-08-18 — re-verify)
SELECT table_name, column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name IN ('conversation_session', 'conversation_message', 'voice_command_log',
                     'voice_command_entity_link', 'voice_feedback')
ORDER BY table_name, ordinal_position;

-- 2. CHECK constraints the seed content must satisfy
SELECT conrelid::regclass::text AS table_name, conname, pg_get_constraintdef(oid) AS definition
FROM pg_constraint
WHERE connamespace = 'public'::regnamespace
  AND conrelid::regclass::text IN ('conversation_session', 'conversation_message', 'voice_command_log',
                                   'voice_command_entity_link', 'voice_feedback')
  AND contype = 'c'
ORDER BY conrelid::regclass::text, conname;

-- 3. Confirm the 5 tables are still empty (expected: 0 rows each)
SELECT 'conversation_session' AS tbl, COUNT(*) AS rows FROM public.conversation_session
UNION ALL SELECT 'conversation_message', COUNT(*) FROM public.conversation_message
UNION ALL SELECT 'voice_command_log', COUNT(*) FROM public.voice_command_log
UNION ALL SELECT 'voice_command_entity_link', COUNT(*) FROM public.voice_command_entity_link
UNION ALL SELECT 'voice_feedback', COUNT(*) FROM public.voice_feedback;

-- 4. Confirm single tenant + second-tenant UUIDs are free + lookup anchors
SELECT id, name FROM public.tenant ORDER BY created_at;
SELECT tier_id, tier_name FROM public.subscription_tier WHERE tier_name = 'charter';
SELECT id, code FROM public.tenant_user_status WHERE code = 'active' AND tenant_id IS NULL;

-- 5. Anchor entities for runtime lookups (design §F.4/§F.5) — confirm these exist in tenant …-0001
SELECT id, job_number, title FROM public.job
WHERE tenant_id = '00000000-0000-0000-0000-000000000001'
  AND (job_number = 'JOB-900001' OR title ILIKE '%In Progress%' OR title ILIKE '%Metro%')
ORDER BY job_number;
SELECT id, quote_number, customer_id FROM public.quote
WHERE tenant_id = '00000000-0000-0000-0000-000000000001' AND quote_number IN ('QUO-900003')
ORDER BY quote_number;
SELECT id, email FROM public."user" WHERE id IN
  ('00000000-0000-0000-0000-000000000002', '00000000-0000-0000-0000-000000000003');
```

> **Engineer safety net — independent column verification (MANDATORY)**: Before writing ANY SQL statement or script INSERT in this batch, run the `information_schema.columns` query for **every table you will touch** (the 5 voice tables + `tenant`, `user`, `tenant_user`, `user_endpoint`, `subscription_tier`, `tenant_user_status`, `job`, `quote`, `job_time_entry`, `job_expense`). If any column name in this prompt or the design doc does not match what MCP returns → use the MCP-returned name, note the discrepancy in your Completion Summary, and proceed. Do NOT ask the Architect to re-do the prompt.

---

## Pre-Work: Read These Source Files

Use `read_file` on each of these before writing any code:

```
dev-docs/architecture-design/batch-designs/batch-sd9-design.md   ← THE SPEC — §F content manifests are authoritative
backend/app/models/ai.py                                          ← SQLModel shapes of all 5 tables; note voice_command_log has NO created_by; conversation_message is append-only
backend/migrations/scripts/seed_scenario_mobile_sync.py           ← canonical scenario-script pattern (modes, _env_profiles wiring, raw-SQL idempotency)
backend/migrations/scripts/seed_test_tenant.py                    ← lines ~440–500: user upsert + tenant upsert pattern (CONFLICT path omits created_by — immutable trigger)
backend/migrations/scripts/reset_dev_db.py                        ← SCENARIOS registry + GROUP_D_TABLES + mode_seed/mode_reset module contract
backend/migrations/scripts/seed_qa_db.py                          ← 11-step orchestrator you extend to 13
backend/migrations/scripts/_env_profiles.py                       ← add_env_args / resolve_profile_from_args / assert_group_allowed / assert_target_compatible / print_seed_banner
backend/migrations/scripts/_db_utils.py                           ← get_db_session()
backend/tests/domains/platform_infrastructure/test_seed_platform_env.py  ← DB-touching seed-test precedent (db_session rollback, key-scoped assertions)
backend/tests/README-adding-tests.md                              ← test structure, domain markers, fixtures, Test Resilience Rule
backend/README-seed-data.md                                       ← §2–§10 (you will reconcile §2, §3, §4, §5, §6, §7.6, §8.1, §9, §10 in Task 7)
backend/services/voice_session_service.py                         ← get_sessions_with_numbers: sessions are user-scoped, is_active filter, derived per-day session_number, title fallback
backend/services/report_service.py                                ← lines 609–726: get_voice_analytics_report aggregation contract (null-latency exclusion, group by intent/user/day)
dev-docs/architecture-design/mvp-arch.md                          ← §6.1–6.7 (Voice AI pipeline, intent vocabulary, context_window_json, structured_content_json, deferred processing)
```

Also run this grep to find every place the scenario registry is consumed:

```bash
grep -rn "seed_scenario_mobile_sync\|SCENARIOS" backend/ --include="*.py" -l
```

---

## Background / Context

All five voice tables (`conversation_session`, `conversation_message`, `voice_command_log`, `voice_command_entity_link`, `voice_feedback`) are **empty in every environment**. The web Voice surfaces (`/voice` session list + session detail with message bubbles and structured-content cards), the voice feedback review API, and the voice analytics report all render empty states. This batch seeds realistic, CHECK-valid, multi-user, multi-day voice history for the primary test tenant **and a brand-new second tenant** (tenant isolation cannot be visually validated with one tenant), then wires both scripts into `reset_dev_db.py` and `seed_qa_db.py`, and reconciles `README-seed-data.md` (including removing the now-stale §8.1 "permanently excluded" row for these tables).

**No migrations, no endpoints, no model changes, no OpenAPI/schema regen.** This is seed tooling only.

---

## Task 1 — MCP verification + baseline (15m)

Run the Pre-Work MCP queries and file reads above. Confirm: 5 tables empty; single tenant; charter `tier_id` and active `tenant_user_status.id` resolved; anchor jobs/quote present. If JOB-900001 / QUO-900003 / the dispatch in-progress job are missing (e.g., Group D was recently wiped), re-run the relevant scenario scripts (`seed_scenario_quote_to_cash.py`, `seed_scenario_dispatch.py`) before continuing.

---

## Task 2 — `backend/migrations/scripts/seed_second_tenant.py` (new, Group C) (~1h)

Create the script per design §F.1. Requirements:

- **Constants**: `SECOND_TENANT_ID = UUID("00000000-0000-0000-0000-000000000006")`, `TENANT_B_OWNER_ID = UUID("…-0007")`, `TENANT_B_TECH_ID = UUID("…-0008")`.
- **Injectable inner functions** (design §F.6 — mandatory test-isolation seam): `_seed_tenant_b(db) -> dict[str, int]` and `_reset_tenant_b(db) -> dict[str, int]` do all DB work against a passed connection; `mode_seed()` / `mode_reset()` are thin wrappers that open `get_db_session()`, call the inner function, commit.
- **Rows** (all upserts mirror `seed_test_tenant.py`; charter tier looked up at runtime `WHERE tier_name='charter'`; `tenant_user_status` looked up `WHERE code='active' AND tenant_id IS NULL` — **never hardcode these lookup UUIDs**, DB-MGMT-1 Task-4 precedent):
  - `tenant`: id `…-0006`, name "Pilot Dev Tenant B", is_active true, charter tier FK, created_by `…-0007`, `stripe_customer_id` NULL
  - `user` ×2: `devb@pilot.local` "Dev"/"Owner B" `#EF4444`; `techb@pilot.local` "Dev"/"Technician B" `#06B6D4`; `email_verified_at = created_at`; same INSERT column list as `seed_test_tenant.py`
  - `tenant_user` ×2: owner (master, EMP-B01) + technician (journeyman, EMP-B02); `joined_at = created_at`
  - `user_endpoint` ×2: email channel only per user (`is_primary=true`, `verification_status='verified'`, `consent_status='opted_in'`)
- **`mode_reset`**: FK-ordered wipe of tenant-B only — tenant-B voice rows first (all 5 tables `WHERE tenant_id = :b`), then `tenant_user`, `user_endpoint`, `tenant`, then `user` rows `…-0007`/`…-0008` (their `user_endpoint` rows first). Never touches tenant-1 data.
- **CLI**: `--mode seed|inspect|show`, `--reset`, `add_env_args(parser)`; `assert_group_allowed(profile, "C", "seed_second_tenant.py")`; `assert_target_compatible` + `print_seed_banner` per the canonical `__main__` block in `seed_scenario_mobile_sync.py`.

Run an intermediate smoke: `python migrations/scripts/seed_second_tenant.py --mode seed` then `--mode inspect`; re-run seed to confirm idempotency; then `--reset` and re-seed (leaves dev seeded).

---

## Task 3 — `backend/migrations/scripts/seed_scenario_voice_ai.py` (new, Group D) (~1.75h)

Create the script per design §F.2–§F.6 — **the content manifests are the binding spec** (sessions S1–S6 + SB1–SB2, ~24 messages, 16 command logs V1–V13 + VB1–VB3, 6 entity links, 2 feedback rows). Key implementation requirements:

- **Injectable inner functions**: `_seed_voice_ai(db, tenant_id: UUID) -> dict[str, int]` and `_reset_voice_ai(db, tenant_id: UUID) -> dict[str, int]`; thin `mode_seed`/`mode_reset` wrappers (design §F.6).
- **Deterministic UUID families** (design §B.3 — registered in README §5 in Task 7): sessions `00000000-0000-0000-0010-0000000000NN`, messages `…-0011-…`, feedback `…-0012-…`, offline-log idempotency UUIDs `…-0013-…`, sync-log idempotency UUIDs `…-0014-…`. All distinct from the reserved `…-0001`–`…-0005` range.
- **Insert order**: session → messages → command logs (capture each log's `RETURNING id`) → entity links + feedback (reference the captured bigint ids).
- **Idempotency (design §B.4)**: sessions/messages/feedback by deterministic-PK existence; command logs by `(tenant_id, idempotency_uuid)` existence; entity links by `(voice_command_log_id, entity_type, entity_id)` existence — log id resolved at runtime via the log's `idempotency_uuid`. **Zero DELETEs in seed mode.**
- **Rolling timestamps**: `NOW()` at run time with the fixed offsets in §F.2 (not a fixed 2026-07-01 anchor).
- **Runtime business-key lookups** for all entity-link targets and context references (job by job_number/title ILIKE, quote by quote_number, latest time entry/expense on the target job) — never hardcode scenario row UUIDs.
- **Tenant-B side**: skipped with a printed notice if tenant `…-0006` does not exist (ordering: Task 2 runs first; QA orchestrator runs second-tenant before scenarios). Tenant-B gets sessions/messages/logs only — **no entity links** (design §G-8).
- **Audit columns**: explicit `created_at` (+ `updated_at` where it exists); `created_by`/`updated_by` = session user where the column exists. Remember: `voice_command_log` has **no** `created_by`; `conversation_message` is append-only (`created_at` + `created_by` only).
- **NULL discipline**: `embedding`/`context_embedding`, `audio_object_key`, `expires_at` all NULL (design §G-6/§G-7). Deferred rows distinguished by non-NULL `processing_status` + timestamp chain.
- **CLI**: `--mode seed|inspect|show`, `--reset`, `add_env_args(parser)`; `assert_group_allowed(profile, "D", "seed_scenario_voice_ai.py")`; standard banner/guards. Inspect prints per-tenant counts for all 5 tables.

Intermediate smoke: `--mode seed` → `--mode inspect` (both tenants) → re-run for idempotency → `pytest -m unit --tb=short -q | tail -5`.

---

## Task 4 — `reset_dev_db.py` integration (~30m)

- Add to `SCENARIOS`: `"voice_ai": "migrations.scripts.seed_scenario_voice_ai",  # SD-9: Voice AI history surfaces`
- Append to `GROUP_D_TABLES` (after `nec_calculation_log`, design §B.5 — child-first FK order):

```python
# ── Voice AI (SD-9) ─────────────────────────────────────────────────────────
"voice_feedback",              # SD-9: FK → voice_command_log (SET NULL; deleted first for a clean wipe)
"voice_command_entity_link",   # SD-9: FK → voice_command_log (RESTRICT — must precede log)
"voice_command_log",           # SD-9: FK → conversation_message
"conversation_message",        # SD-9: FK → conversation_session
"conversation_session",        # SD-9
```

- Verify: `python migrations/scripts/reset_dev_db.py --scenarios voice_ai` (wipe+reseed cycle for the scenario) and a full `--wipe-only` pass complete without FK errors. Note: `reset_dev_db.py` full wipe is single-tenant (…-0001) — tenant-B rows are wiped via the scenario's own `mode_reset`, which handles both tenants (design §G-9).

---

## Task 5 — `seed_qa_db.py` integration (~15m)

- Insert a new step after the Group C step: run `seed_second_tenant.py --env qa`.
- Append `("seed_scenario_voice_ai.py", "voice_ai")` to the scenarios list.
- Renumber the step prints from 11 to 13 total.

---

## Task 6 — Tests (~1h)

Create `backend/tests/domains/platform_infrastructure/test_seed_scenario_voice_ai.py` implementing the 12-test manifest in design §F.7. Per `backend/tests/README-adding-tests.md`:

- `pytestmark = [pytest.mark.domain_platform_infrastructure, pytest.mark.unit]`
- DB-touching tests call the **injectable inner functions** against the `db_session` fixture (rollback-wrapped) — `_seed_voice_ai(db_session, TEST_TENANT_ID)`, `_reset_voice_ai(db_session, TEST_TENANT_ID)`, `_seed_tenant_b(db_session)`. **Never** call `mode_seed`/`mode_reset` from a test.
- Assertions scope by the deterministic `0010`–`0014` UUID families and business keys (`tier_name='charter'`, `devb@pilot.local`) — never unscoped table counts; tolerate the real seed already being present (existence-check idempotency).
- Autouse fixtures (`mock_cognito_jwks`, `mock_ai_services`, `mock_entitlement_allowed`) require **no opt-outs** here — these tests touch neither endpoints, entitlements, nor AI services.

### Test Requirements (summary — full manifest is design §F.7)

| Area | Tests |
|---|---|
| Seed creates full manifest (both tenants) | 1 |
| Idempotent re-run (0 new rows) | 2 (voice + tenant-B upsert) |
| CHECK-set validity (role/status/processing_status) | 1 |
| Referential integrity (message links, entity links same-tenant, feedback → log) | 3 |
| Reset removes deterministic rows for both tenants | 1 |
| Tenant-B shape (charter FK, 2 tenant_user rows) | 1 |
| Deferred-row timestamp chain + `idempotency_uuid` presence | 1 |
| Structured-content JSON shape (`render_mode` live/snapshot) | 1 |
| UUID-family purity (unit, no DB) | 1 |

---

## Task 7 — README-seed-data.md reconciliation + live dev run (~30m)

Per design §B.2, update `backend/README-seed-data.md`:

- **§2** script inventory: add both new scripts
- **§3** Group C row: add `seed_second_tenant.py`
- **§4**: Group C — second-tenant block; Group D — new "Voice AI scenario (`seed_scenario_voice_ai.py`)" subsection with per-table counts and content notes
- **§5** deterministic-UUID registry: add the 8 new entries (design §B.3)
- **§6** run order: second-tenant step after `seed_test_tenant.py`; `seed_scenario_voice_ai.py` in the scenario block
- **§7.6** QA runbook: 13 steps
- **§8.1**: **remove the voice-table exclusion row** (`voice_command_log`, `voice_command_entity_link`, `voice_feedback`, `conversation_session`, `conversation_message`) and replace with a one-line pointer to the §4 Group D voice scenario
- **§9** scenario registry: add `voice_ai` (dev-only, ✅ SD-9)
- **§10**: add entry "**SD-9 (Voice AI) — Voice AI seed data + second tenant ✅ Complete (2026-08-…)**" — named explicitly to avoid the existing "Task SD-09" collision (design §G-2)
- Also update `dev-docs/testing-support/scenario-coverage-catalog.md` W-06: Seed Data column ☐ → ✅ SD-9 (Tier 1/Tier 2 E2E columns stay ☐ — GPU-dependent, Phase 7)

Then the **live dev run** (evidence for the Completion Summary):

```bash
cd <repo>/backend && source .venv/bin/activate
python migrations/scripts/seed_second_tenant.py --mode seed
python migrations/scripts/seed_second_tenant.py --mode inspect
python migrations/scripts/seed_scenario_voice_ai.py --mode seed
python migrations/scripts/seed_scenario_voice_ai.py --mode inspect
```

Capture the inspect output (both tenants, all 5 tables) into the Completion Summary.

---

## Seed Data Rollout (Core + Scenario)

Per `backend/README-seed-data.md` — read §3 (Group A–D model), §6 (run order), and §7 (DELETE safety rule) before editing any seed script. **This batch IS a seed-data batch** — the rollout below satisfies Rule 11.5:

### Layer 1 — Core / Platform values (Group A / B)

- None. No new lookup/reference rows. Verified in design §B.2.

### Layer 2 — Scenario data (Group D)

- New `voice_ai` scenario content per design §F.2–§F.5 (this batch's core deliverable), plus the Group C second tenant (design §F.1).
- FK values (charter tier, `tenant_user_status`, entity-link targets) are looked up by business key at runtime — **never hardcode a `gen_random_uuid()`-generated scenario UUID** (README §7 pricebook rule).
- `mode_seed` performs **zero DELETEs** — existence-check-then-insert only (DELETE-safety rule).

### Verification

- After seeding: `python migrations/scripts/seed_scenario_voice_ai.py --mode inspect` (per-tenant counts for all 5 tables) + `python migrations/scripts/seed_second_tenant.py --mode inspect`.
- Run `pytest -m unit` after each seed change — a seed row a test doesn't expect will break tests (README §7 "shared DB" rule). Fix any seed-resilience failures (assert-by-ID, never by count).
- Manual UI sanity (optional, Tom): `/voice` session list shows the seeded sessions; a session detail shows message bubbles + the two structured-content cards.

### README update

- Task 7 covers the full README reconciliation, including §4 (Current Seed State) and the §10 SD-9 (Voice AI) entry.

---

## Regeneration Steps

- `python generate_app_import_map.py tests > app_model_imports.md` — **required** (new test file added). Note the explicit dir arg + stdout redirect.
- **NOT required** (state this in your Completion Summary): `generate_db_model_map.py` (no model changes), `export_openapi_json.py` (no endpoint changes), `schema_manager.py` (no schema changes), `pnpm sync-api-types` (no OpenAPI delta).

---

## Final Verification

### Phase 1 — Unit Tests Only (run after each task group during development)

```bash
cd <repo>/backend
source .venv/bin/activate

# Unit tests only — fast feedback loop during implementation
python -m pytest -m unit --tb=short -q 2>&1 | tail -10
```

All unit tests must pass before moving to the next task. Fix any unit failure — including failures that appear to be caused by code outside your batch — before proceeding.

### Phase 2 — Lint (changed files only) + Full Suite, Vendor-Deselected (run once, at the very end, before DoD sign-off)

```bash
cd <repo>/backend
source .venv/bin/activate

# Lint + format gate (rules §23) — CHANGED FILES ONLY, not the whole codebase
# Get the Python files changed this session (staged + unstaged vs HEAD; excludes deletions)
# The sed strips the "backend/" prefix because git diff returns repo-root-relative paths
# but ruff runs from inside backend/ and needs backend/-relative paths
CHANGED_PY=$(git diff --name-only --diff-filter=d HEAD -- '*.py' | sed 's|^backend/||')

if [ -n "$CHANGED_PY" ]; then
    ruff check --fix $CHANGED_PY     # lint + isort (I) + pyupgrade (UP) autofix
    ruff format $CHANGED_PY          # format (line-length 88)
    ruff check $CHANGED_PY           # re-check: any remaining errors need manual fixing
fi

# Full suite — vendor/live-service suites deselected (Tom's standing instruction 2026-08-16;
# they add 9+ min: Telnyx/Stripe/SendGrid vendor APIs, Redis-dependent, e2e).
# All six markers are registered in backend/pytest.ini; conftest auto-marks vendor tests
# with `integration`, so this expression is doubly safe under --strict-markers.
python -m pytest -m "not integration and not requires_telnyx and not requires_stripe and not requires_sendgrid and not requires_redis and not e2e" --tb=short -q 2>&1 | tail -15

# Vendor-suite inclusion call for THIS batch: NOT required — this batch touches only
# migrations/scripts seed tooling + tests; NO runtime vendor-covered code
# (services/telnyx*, Stripe billing/webhooks, SendGrid dispatch, Redis-dependent modules).

# Batch-specific spot checks
python -m pytest tests/domains/platform_infrastructure/test_seed_scenario_voice_ai.py -v 2>&1 | tail -20
python migrations/scripts/seed_scenario_voice_ai.py --mode inspect 2>&1 | tail -25
python migrations/scripts/seed_second_tenant.py --mode inspect 2>&1 | tail -12

echo "=== SD-9 FINAL VERIFICATION COMPLETE ==="
```

> **Warning-clean is part of done.** `ruff` must report no remaining issues **in your changed files** (no unjustified `# noqa`), and the pytest run must be free of `DeprecationWarning` noise. **Do not run `ruff check .` against the entire codebase** — scope to changed files only (rules §23). Pre-existing ruff notes in seed scripts from prior batches (RUF001, B905, RUF013 per DB-MGMT-1) are documented — if your changed lines touch them, fix them per the iterative-cleanup policy.

> **Any failure in either phase — unit or the vendor-deselected full suite — must be fixed before the batch is declared done.** There is no "pre-existing failure" exception without explicit written confirmation from Tom. If you cannot identify the root cause of a failing test → STOP and ask Tom before proceeding.

---

## Definition of Done

- [ ] Pre-modification regression baseline captured (`X passed, Y failed`) using `pytest -m unit`
- [ ] Zero pre-existing unit failures confirmed before starting work (or confirmed with Tom)
- [ ] All 5 MCP pre-work queries run — 5 voice tables verified via `information_schema.columns`, CHECK sets captured, tables confirmed empty, charter tier + active status + anchor entities resolved (rules §25)
- [ ] All mandatory source files read before writing any code (including `batch-sd9-design.md` in full)
- [ ] `seed_second_tenant.py` created — Group C, injectable inner functions, env gating "C", idempotent upserts, FK-ordered tenant-B-only reset
- [ ] `seed_scenario_voice_ai.py` created — Group D, injectable inner functions, env gating "D", full §F content manifest (8 sessions, ~24 messages, 16 logs, 6 entity links, 2 feedback), deterministic UUID families, zero DELETEs in seed mode
- [ ] `reset_dev_db.py` — `voice_ai` in SCENARIOS + 5 tables appended to GROUP_D_TABLES in child-first order; scenario wipe+reseed and full `--wipe-only` cycles verified
- [ ] `seed_qa_db.py` — second-tenant step + `voice_ai` scenario; steps renumbered to 13
- [ ] `tests/domains/platform_infrastructure/test_seed_scenario_voice_ai.py` — 12 tests per §F.7; `pytestmark` domain + unit; inner-function/db_session isolation; key-scoped assertions; **no calls to mode_seed/mode_reset**
- [ ] README-seed-data.md reconciled — §2, §3, §4, §5, §6, §7.6, §8.1 (voice exclusion row removed), §9, §10 (SD-9 (Voice AI) entry)
- [ ] `scenario-coverage-catalog.md` W-06 Seed Data column → ✅ SD-9
- [ ] `python generate_app_import_map.py tests > app_model_imports.md` run (new test file)
- [ ] Live dev run completed — both scripts seeded + inspect evidence captured
- [ ] `ruff check --fix && ruff format` run **on changed files only** — zero remaining issues in those files, no unjustified `# noqa` (rules §23)
- [ ] **Phase 1**: All unit tests pass (`pytest -m unit`) — zero failures including any pre-existing
- [ ] **Phase 2**: Full suite (vendor-deselected) passes — zero failures, warning-clean; vendor-suite inclusion call recorded as NOT required (seed tooling only)
- [ ] Final test count (before → after) documented
- [ ] Completion Summary appended to `pilot-launch-plan.md` Appendix C + README §10 entry marked ✅ (source-spec update rule)

---

## Completion Summary

After all Definition of Done items are complete:

1. Append a **Completion Summary** to `dev-docs/analysis/pilot-launch-plan.md` **Appendix C (end of file)** using the format below. Do **not** edit §2.0/§2.3 yourself — the Architect updates the plan tables at batch close.
2. **Source-spec update rule**: update `backend/README-seed-data.md` §10 — the "SD-9 (Voice AI)" entry must show ✅ Complete with a one-line summary BEFORE declaring the batch done (Task 7 creates the entry; mark it complete here).

```markdown
### SD-9 — Voice AI Seed Data: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot Python Engineer
**Baseline**: X passed, Y skipped, Z failed
**Final**: X+N passed, Y skipped, Z failed (+N new tests)

#### What Was Accomplished

- [seed_second_tenant.py — tenant …-0006 + 2 users; key decisions]
- [seed_scenario_voice_ai.py — content manifest landed; both tenants; key decisions]
- [reset_dev_db.py / seed_qa_db.py integration]
- [README reconciliation incl. §8.1 exclusion-row removal]
- [Live dev run evidence: inspect counts both tenants]

#### Files Changed / Created

| File | Action |
|---|---|
| `backend/migrations/scripts/seed_second_tenant.py` | Created — … |
| `backend/migrations/scripts/seed_scenario_voice_ai.py` | Created — … |
| `backend/migrations/scripts/reset_dev_db.py` | Modified — … |
| `backend/migrations/scripts/seed_qa_db.py` | Modified — … |
| `backend/tests/domains/platform_infrastructure/test_seed_scenario_voice_ai.py` | Created — … |
| `backend/README-seed-data.md` | Modified — … |
| `dev-docs/testing-support/scenario-coverage-catalog.md` | Modified — W-06 seed column |
| `backend/app_model_imports.md` | Regenerated |

#### Tests Added

| Test File | Domain | Tests | All Pass |
|---|---|---|---|
| `tests/domains/platform_infrastructure/test_seed_scenario_voice_ai.py` | `platform_infrastructure` | 12 | ✅ |
```

---

## After This Task — Next Step

Hand off to Tom: (1) browse `/voice` on the web dashboard — the session list should show the seeded sessions (owner + tech histories, per-day numbering, archived/abandoned states) and session detail should render message bubbles + the two structured-content cards; (2) verify tenant isolation — the UI shows only tenant-1 rows while `seed_scenario_voice_ai.py --mode inspect` proves tenant-B rows exist in the DB; (3) SD-9 (with HELP-B1) is the named trigger to resume the deferred UI-INT-TEST full regression — tell the Architect when this closes so the launch plan Order 3 row and UI-INT-TEST gate note are updated.
