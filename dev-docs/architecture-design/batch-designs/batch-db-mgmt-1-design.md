# DB-MGMT-1 — DB Management Strategy: Schema-Restore Provisioning + Environment-Aware Seeds

**Batch code**: DB-MGMT-1
**Owner**: Pilot Architect (design) → Python Engineer (implementation)
**Priority**: P1 — pre-Beta enabler; gates Founder signup (`pilot-launch-plan.md` Order 3, item 5)
**Status**: v1.1 — AUTHORED 2026-08-17, amended 2026-08-18 (vendor-posture matrix §B.3 + Telnyx Option A decision §G-11 per Tom), awaiting Tom approval

**Changelog**: v1.1 (2026-08-18) — Tom's refinement: dev must support real testing of selected integrations (QuickBooks via multiple sandbox companies, Cognito via the dev pool — a QA pool can be added when needed, SendGrid via the single shared account). Telnyx non-prod **resolved 2026-08-18 (Tom): Option A** (§G-11) — mock carrier in dev/e2e permanently; Phase 2 QA gets its own real messaging profile + number (~$1/mo). Stripe confirmed: only live/test modes exist; qa → test and prod → live in the future, but **prod stays linked to test mode for now** (Phase 1). The dev seed-data delta is intentionally near-zero — the change is the posture *contract* (§B.3) so future seeds never break real-integration testing from dev.
**Estimate**: 5–6h Python (single batch; natural split point noted in §C if Tom prefers two)
**Cost impact**: $0 — no new AWS services, no infra change; conforms to `aws-env-mgmt-ops-plan.md` Phase 1/2 model

---

## 0. Context, Problem & Directive

**Current state (being replaced):** QA/prod/e2e databases have historically been provisioned by replaying Alembic migrations. That chain was authored against a dev DB that already held reference data, so migrations embed data INSERTs that fail from a blank DB (`init_e2e_schema.py` docstring documents this). Prod data drifted from dev (the 2026-08-09 "SEED-FIX-1" prod sync found migration-embedded seed gaps in `platform_setting_catalog` and `communication_template`). Stripe price IDs were flipped in prod via one-off deployment SQL (`stripe-pricing-config.md §4` UPDATE statements) — exactly the "no one-off deployment SQL" anti-pattern this batch eliminates.

**Target state:** Every database is provisioned by **schema-only restore from the dev DB** (the working E2E reference), then populated by **purpose-specific, environment-aware seed scripts**. Going forward, **migrations are DDL-only** — all data is owned by seed scripts (§E rule E-4).

**Tom's directive (2026-08-17, refined 2026-08-18) — the centerpiece of this design:** *Seed scripts must know which system they are populating (dev / e2e / qa / prod), because the environments have different integration postures.* Per `aws-env-mgmt-ops-plan.md` and Tom's 2026-08-18 refinement: **prod is our integration-testing environment** in Phase 1 (real vendors in test modes — Stripe test keys, real Telnyx, live SendGrid, QBO sandbox), while **local dev runs a deliberate subset of real integrations** — **QuickBooks** (sandbox; multiple sandbox companies supported), **Cognito** (dedicated dev pool; a QA pool can be added when needed), **SendGrid** (one shared account serves all environments). Telnyx beyond prod is decided (§G-11 Option A — mock in dev/e2e permanently, real messaging profile + number for Phase 2 QA); Stripe is test-mode in every env today and only flips prod → live at GA (§G-2). Seeded values that interact with vendor posture (Stripe price IDs, Stripe customer IDs, phone numbers) must therefore be **selected by target environment**, and the scripts must **fail closed** when the selected values would mismatch the target's vendor mode (env-mgmt §4.1.1 — mixed mode is the failure class that stranded the 2026-08-10 signup test).

---

## A. Input Read Summary

| Input | What it contributed | Read? |
|---|---|:---:|
| `pilot-launch-plan.md` §DB-MGMT-1 (lines 209–222) + Order-3 row | Batch scope: schema-restore per env, per-purpose seed inventory, `--env` flag design, migration-sync runbook, prod live price IDs | ✅ |
| `backend/README-seed-data.md` (full, 996 lines) | Group A–D model, 12-script inventory, run order, schema-only-restore recovery, DELETE safety rule, deterministic UUIDs, GiST caveats | ✅ |
| `aws-env-mgmt-ops-plan.md` (Phase model, §2 test modes, §3 secrets, §4.1 binding rules) | Env integration postures; Phase 1 prod = uniform vendor test modes; `pilot/prod/*` vs `pilot/qa/*` secrets; `ENVIRONMENT` task-def values | ✅ |
| `pilot-adr-log.md` Decision Index (ADR-0001–0015) | No binding ADR governs DB provisioning/seeding — this design is unencumbered; ADR-0006 (idempotency) applies to seeds | ✅ |
| `backend/tests/e2e/init_e2e_schema.py` (full) | **Working schema-restore reference**: pg_dump `--schema-only` from dev → `psql -f` apply → `gen_random_uuid()` default patch on 24 lookup tables → `alembic stamp head`; dev-DB refusal guard | ✅ |
| `backend/tests/e2e/seed_e2e_db.py` (full) | Group A→B→C→D orchestration pattern; `DATABASE_URL` override; **`ENVIRONMENT=e2e` is invalid** (pydantic literal) — forces `dev` | ✅ |
| `backend/migrations/scripts/_db_utils.py` | `get_db_session(db_url)` reads `DATABASE_URL` at call time, fresh engine — the connection-injection seam `--env` builds on | ✅ |
| `backend/migrations/scripts/seed_platform.py` lines 311–332, 378–390 | Hardcoded **test-mode** Stripe price IDs for starter/teams — the values that become env-driven | ✅ |
| `backend/core/config.py` line 57 | `ENVIRONMENT: Literal["dev","qa","staging","production"]` — constrains flag design (§G-1) | ✅ |
| `docker-compose.e2e.yml` | E2E DB is port **5434** (README says 5433 — drift); **5433 reserved for the prod SSH tunnel** | ✅ |
| `postgresql-ext-setup-to-prod.md` | Prod access path: bastion SSH tunnel → `localhost:5433`; `pilot/prod/db` secret shape | ✅ |
| `pilot-founder-onboarding-process.md` §1 | Beta = concierge provisioning by Tom; charter tier — what prod data must support | ✅ |
| `stripe-pricing-config.md §4` | Canonical test/live price IDs for starter/teams (monthly + annual) | ✅ |
| `postgres-mcp-guide.md` | MCP query patterns (read before all queries below) | ✅ |

**MCP live-DB verification (postgres-local, 2026-08-17):**

| Check | Result | Notes |
|---|---|---|
| `alembic_version` | `58c3ad26129f` | Current head |
| Base tables | 193 `public` + 1 `audit` | — |
| Extensions | `vector` 0.8.2, `btree_gist` 1.7, `citext` 1.6, `plpgsql` | Target envs must have all four (RDS pgvector per `postgresql-ext-setup-to-prod.md`) |
| `subscription_tier` columns | `tier_id, tier_name, display_label, annual_price_cents, is_trial, trial_duration_days, is_active, display_order, stripe_price_id_monthly, stripe_price_id_annual, free_period_days, requires_payment_method, signup_cap, price_locked, product_plan_code, schedule_lanes, monthly_price_cents` + 4 audit cols | All SQL in this design uses only these names |
| `subscription_tier` values | charter: **monthly `price_REDACTED09`, annual NULL** ⚠️ undocumented in stripe-pricing-config.md (§G-7); starter/teams: test-mode IDs; trial: NULL/NULL | Env-specific field inventory anchor |
| Seed counts vs README | `platform_setting_catalog` 48 ✅ · `platform_setting` defaults 48 ✅ · `communication_template` 17 ✅ · `notification_type` 17 ✅ · `job_type` 11 ✅ · `email_template` 16 ✅ · `quote_template` 3 / `quote_template_line` 9 ✅ · `product_plan` 3 ✅ · `subscription_tier` 4 ✅ | — |
| `notification_template` | **58 platform-default rows — README §4 says 41** ❌ drift (§G-8) | Inventory task reconciles |
| `pricebook_item` | `tenant_id` is **NOT NULL**; 0 rows with `tenant_id IS NULL` | Platform-owned pricebook starters are schema-impossible → §G-5 decision |

---

## B. Migration & Seed Rollout Plan

### B.1 Schema migrations

**None. Zero DDL in this batch.** This batch is tooling/runbooks only — it changes *how* databases are provisioned and seeded, not the schema. The audit-mixin DDL rule and 3-part NOT NULL pattern are not triggered.

### B.2 Seed Data Rollout (Rule 11.5 — mandatory)

| Layer | Change | Script(s) |
|---|---|---|
| **Layer 1 — Core/Platform** | Stripe price IDs move out of hardcoded script bodies into the env-profile registry (§F.1); `seed_platform.py` resolves them per `--env`/`--stripe-mode` and **converges** (idempotent UPDATE on the 5 price-ID slots across 4 tiers, not insert-only). Charter price ID `price_REDACTED09` is added to the registry once its mode is classified (§G-7). No other Group A/B value changes — `seed_core.py` has no env-specific fields (engineer confirms during inventory). | `seed_platform.py`, `_env_profiles.py` (new) |
| **Layer 2 — Scenario** | No scenario data changes. Scenario scripts gain `--env` acceptance + group gating only. | 8× `seed_scenario_*.py` |
| **New** | `seed_pricebook_starter.py` + JSON catalog (§F.5) — per-tenant, concierge-run; content gated on Tom sign-off. | new script + `data/pricebook_starter/default_catalog.json` |
| **Verification** | `seed_core.py --mode inspect` + `seed_platform.py --mode inspect` per env after each run; `pytest -m unit` green; README §4 updated. | — |

### B.3 The environment-value matrix (the heart of Tom's directive)

Values that differ by target environment. **This is the complete known inventory** — the Python Engineer's first task MCP-verifies and completes it (charter ID mode, any missed fields) and lands it as a permanent table in `README-seed-data.md`.

| Seeded value | dev | e2e | qa | prod Phase 1 (now) | prod Phase 2 (GA cutover) |
|---|---|---|---|---|---|
| `subscription_tier.stripe_price_id_monthly` / `_annual` (starter, teams) | test IDs | test IDs | test IDs | **test IDs** (matches `sk_test_` keys in `pilot/prod/stripe`) | **live IDs** (after key flip) |
| `subscription_tier` charter price ID(s) | current value (classify mode — §G-7) | same as dev | same as dev | per `--stripe-mode` | per `--stripe-mode` |
| Group C test tenant incl. `tenant.stripe_customer_id = 'cus_REDACTEDX01'` (test-mode) | ✅ | ✅ | ✅ | ❌ **never** (concierge tenants would come from real signups after launch) | ❌ |
| Group D scenarios (incl. `tenant_phone_number +15125559001` `provisioning_failed`) | ✅ all 8 | 5 of 8 (cp-covered, per `seed_e2e_db.py`) | ✅ all 8 | ❌ **never** | ❌ |
| `@pilot.local` users, reserved UUIDs `...0001`–`...0005` | ✅ | ✅ | ✅ | ❌ | ❌ |
| Pricebook starter catalog | optional per-tenant | — | optional per-tenant | per-tenant at concierge provisioning | per-tenant (GA: fold into signup flow — future batch) |

**Vendor integration posture per environment (Tom's refinement, 2026-08-18).** Seeds must stay consistent with this posture; `_env_profiles.EnvProfile.vendor_posture` (§F.1) is the machine-readable source of truth, and the seed banner prints it on every run.

| Vendor | dev | e2e | qa (Phase 2) | prod Phase 1 (now) | prod Phase 2 (GA) |
|---|---|---|---|---|---|
| **QuickBooks** | sandbox company (multiple sandboxes supported) | none (mocked) | sandbox company — separate from dev's to avoid cross-talk | sandbox | production app |
| **Cognito** | dev pool (MFA Disabled) | mocked (`conftest_e2e.py`) | QA pool (mirrors prod; added when needed) | prod pool | prod pool |
| **SendGrid** | shared account — real sends supported | mocked | shared account (sandbox mode or dedicated QA key optional) | shared account, low volume | shared account, live |
| **Telnyx** | mock carrier | mock carrier | real (own messaging profile + number, ~$1/mo — §G-11 Option A) | real (campaign `CXXXXXX`) | real |
| **Stripe** | test mode | test mode | test mode | **test mode** (`pilot/prod/stripe` holds `sk_test_` keys) | **live mode** |

Seed-coupling notes by vendor:

- **Stripe** — the only vendor with env-valued seed data today: the 5 `subscription_tier` price-ID slots (§B.3). Enforced by `--stripe-mode` + the secrets preflight (§F.1).
- **Cognito** — Group C user emails (`dev@pilot.local` etc.) must match users in the target pool for login testing; seeds own the DB rows only (pool users are provisioned in the pool itself). Dev pool today; QA pool when added.
- **QuickBooks** — **never seed connection/token state** (`quickbooks_connected` checklist flags and webhook events are runtime-written). Sandbox connection is established via OAuth at runtime; `QUICKBOOKS_ENVIRONMENT=sandbox` is already the dev default (`core/config.py` line 29).
- **SendGrid** — no seed coupling: `email_template` / `communication_template` rows are env-independent; from-address is an env var.
- **Telnyx** — no env-valued seed fields; the Group D `tenant_phone_number +15125559001` row (`provisioning_failed`) is inert in every env. Posture decision is §G-11.

### B.4 Seed-group × environment gating matrix

Enforced in code by `_env_profiles.py` — a script invoked with a disallowed group/env combination **exits non-zero with an explicit message** (fail-closed, mirrors the `TEST_ENDPOINT` allowlist pattern in `core/config.py`).

| Group / script | dev | e2e | qa | prod |
|---|:---:|:---:|:---:|:---:|
| A — `seed_core.py` | ✅ | ✅ | ✅ | ✅ |
| B — `seed_platform.py` | ✅ | ✅ | ✅ | ✅ (env-driven values + `--stripe-mode` + preflight) |
| C — `seed_test_tenant.py` | ✅ | ✅ | ✅ | ❌ refused |
| D — 8× `seed_scenario_*.py` | ✅ | subset via orchestrator | ✅ | ❌ refused |
| `seed_pricebook_starter.py` (new) | ✅ | — | ✅ | ✅ (concierge, `--tenant-id`) |
| `reset_dev_db.py` (wipe tool) | ✅ | ❌ (docker volume wipe) | ✅ local-only | ❌ **refused — prod wipe is forbidden** |
| `test_fire_templates.py` | ✅ | — | ✅ | ❌ (unchanged; out of scope) |

---

## C. Execution Order

Single batch, 7 tasks, strictly ordered. **If Tom prefers two smaller batches (Rule 9.6): split after Task 4** — Tasks 1–4 = "DB-MGMT-1a (mechanism + qa/prod seeding)", Tasks 5–7 = "DB-MGMT-1b (pricebook starter + runbooks + reconciliation)".

| # | Task | Deliverable | ~Time |
|---|---|---|---|
| 1 | **Env-profile registry + `--env` rollout.** New `migrations/scripts/_env_profiles.py` (§F.1); add `--env` / `SEED_ENV` + banner + guards to all 12 seed scripts; group gating per §B.4. **Inventory sub-deliverable**: MCP-verify every env-specific seeded field (charter price-ID mode first), complete §B.3, land it as a permanent table in `README-seed-data.md`. | `_env_profiles.py` + 12 scripts patched + inventory table | 1.5h |
| 2 | **`seed_platform.py` env-aware Stripe resolution.** Replace hardcoded test IDs with registry lookup; idempotent converge-UPDATE for all 5 price-ID slots; `--stripe-mode` enforcement on prod; unit tests for profile resolution. | patched `seed_platform.py` | 45m |
| 3 | **Generalize schema provisioning.** New `migrations/scripts/provision_schema.py` (§F.2) — the `init_e2e_schema.py` logic, env-parameterized; `init_e2e_schema.py` becomes a thin back-compat wrapper. | `provision_schema.py` + wrapper | 1h |
| 4 | **QA orchestrator + scratch-DB proof.** New `seed_qa_db.py` (§F.3); prove end-to-end against a scratch local `pilot_qa` DB: `provision_schema.py --env qa` → `seed_qa_db.py` → inspect counts == dev baseline manifest. | `seed_qa_db.py` + verified scratch run | 45m |
| 5 | **Prod orchestrator (converge-in-place).** New `seed_prod_db.py` (§F.4) — Groups A+B only, Stripe preflight, typed confirmation, `--mode show\|inspect` dry-run support. **Tom executes the real prod run**; engineer validates dry-run output only. | `seed_prod_db.py` + dry-run evidence | 45m |
| 6 | **Pricebook starter.** `seed_pricebook_starter.py` + JSON catalog (§F.5); content sign-off gate = Tom. Founder-onboarding doc gains the concierge step. | script + JSON + doc step | 45m |
| 7 | **Runbooks + doc reconciliation.** Migration-sync runbook (§H.2) + per-env provisioning runbook (§H.1) landed in `README-seed-data.md`; cross-ref in `aws-ops-runbook.md`; fix README drift (E2E port 5434; `notification_template` 58); file Integrations follow-up for charter price ID in `stripe-pricing-config.md §4`. Final verification: `pytest -m unit` + inspect-matrix across dev/e2e/scratch-qa. | docs + green suite | 1h |

---

## D. New API Endpoints

**None.** This batch is CLI/tooling only — no FastAPI surface, no OpenAPI change, no `pnpm sync-api-types` handoff required. (The Python prompt will state this explicitly so the engineer skips OpenAPI regeneration.)

---

## E. Pattern Reuse Decisions

No user-facing `mvp-arch.md §16` patterns apply (ops batch — no UI, no endpoints). The binding platform rules that DO apply:

| Rule | Source | Application |
|---|---|---|
| **E-1. Idempotency by default** | ADR-0006 | Every seed script is safely re-runnable in every env: `INSERT ... ON CONFLICT DO NOTHING` where a unique constraint exists; value-scoped DELETE+INSERT where it doesn't (Rule 11.1 — DELETE must include `value`/natural key, never channel/class-scoped). Prod seeding is **converge-in-place**: re-running must repair drift, never duplicate. |
| **E-2. Fail-closed allowlists** | `core/config.py` FIND-001-049 pattern | Env/group gating, host guards, and `--stripe-mode` resolution are allowlists. Unknown env names, missing prod mode, unrecognized hosts → hard exit. |
| **E-3. Dev-DB refusal guards** | `init_e2e_schema.py` / `seed_e2e_db.py` | Generalized into `_env_profiles.assert_target_compatible()` — every script gets bidirectional guards (non-prod scripts refuse RDS hosts; `--env prod` refuses localhost dev DBs and requires the tunnel shape or an explicit RDS host). |
| **E-4. Migrations are DDL-only (NEW RULE — codifies SEED-FIX-1)** | this design; recommend **ADR-0016** | From this batch forward: Alembic migrations contain DDL only. All data (lookup rows, platform config, templates) is owned by seed scripts. A migration that needs new reference data lands it in `seed_core.py`/`seed_platform.py` **in the same PR**; the sync runbook's converge step (§H.2) applies it to each env. Migration-embedded INSERTs are a code-review reject. This is the architectural keystone that makes schema-restore provisioning sound. |
| **E-5. No one-off deployment SQL** | launch plan DB-MGMT-1 charter | All prod data changes flow through `--env prod` seed scripts (idempotent, auditable, re-runnable). The `stripe-pricing-config.md §4` UPDATE statements are replaced by `seed_platform.py --env prod --stripe-mode {test\|live}`. |

---

## F. Shared Module Interfaces

### F.1 `migrations/scripts/_env_profiles.py` (new) — the env-awareness registry

```python
class SeedEnv(str, Enum):
    DEV = "dev"; E2E = "e2e"; QA = "qa"; PROD = "prod"

class StripeMode(str, Enum):
    TEST = "test"; LIVE = "live"

@dataclass(frozen=True)
class EnvProfile:
    env: SeedEnv
    allowed_groups: frozenset[str]          # prod: {"A","B"}; others: {"A","B","C","D"}
    stripe_mode: StripeMode | None          # dev/e2e/qa: TEST (hardwired); prod: None = caller must supply
    stripe_price_ids: Mapping[str, dict[str, str | None]]  # tier_name -> {"monthly": ..., "annual": ...}
    allowed_db_host_patterns: tuple[str, ...]    # prod: ("rds.amazonaws.com", "localhost:5433")
    forbidden_db_host_patterns: tuple[str, ...]  # non-prod: ("rds.amazonaws.com",); prod: (":5432/pilot_dev",)
    require_typed_confirmation: bool             # prod seed mode: True
    vendor_posture: Mapping[str, str]            # §B.3 posture matrix, e.g. {"quickbooks": "sandbox",
                                               #  "cognito": "dev-pool", "sendgrid": "shared",
                                               #  "telnyx": "mock", "stripe": "test"}
                                               #  Declarative this batch (banner + runbooks); Stripe is the
                                               #  only actively enforced preflight (verify_stripe_key_alignment).

def resolve_seed_env(cli_value: str | None) -> SeedEnv:
    """Precedence: --env flag > SEED_ENV env var > default DEV. Never reads pydantic
    settings.ENVIRONMENT (§G-1). Unknown value -> SystemExit."""

def get_profile(env: SeedEnv, stripe_mode: str | None) -> EnvProfile:
    """Fail-closed: PROD without explicit stripe_mode -> SystemExit;
    --stripe-mode live with non-prod env -> SystemExit."""

def assert_target_compatible(profile: EnvProfile, database_url: str) -> None:
    """Bidirectional host guard (E-3). Runs BEFORE any connection opens."""

def print_seed_banner(profile: EnvProfile, database_url: str, script_name: str) -> None:
    """Audit banner on every run: env, stripe_mode, vendor_posture, host/dbname,
    groups allowed."""

def verify_stripe_key_alignment(profile: EnvProfile, secret_id: str) -> None:
    """Prod/remote-qa preflight: `aws secretsmanager get-secret-value` (subprocess,
    matching the psql pattern in init_e2e_schema.py — no boto3 dep). sk_test_ prefix
    must pair with StripeMode.TEST; sk_live_ with LIVE. Unreadable secret -> refuse
    unless --skip-preflight (loud warning). Local dev/e2e/qa: skipped automatically."""
```

Standard argparse block added to all 12 scripts (identical shape everywhere):

```python
parser.add_argument("--env", choices=["dev", "e2e", "qa", "prod"], default=None,
                    help="Target environment profile (default: $SEED_ENV, else dev)")
# prod-only, required when --env prod and the script touches env-specific values:
parser.add_argument("--stripe-mode", choices=["test", "live"], default=None)
```

### F.2 `migrations/scripts/provision_schema.py` (new) — generalized schema-restore

```
python migrations/scripts/provision_schema.py --env e2e [--schema-dump PATH]
python migrations/scripts/provision_schema.py --env qa  [--schema-dump PATH]
python migrations/scripts/provision_schema.py --env prod --i-understand-prod-rebuild   # double-gated; see §G-3
```

Steps (identical to the proven E2E flow): guard → `pg_dump --schema-only` from dev `pilot_dev` (or accept `--schema-dump`) → `psql -f` apply to `DATABASE_URL` target → patch `gen_random_uuid()` defaults on the 24 lookup tables (list carried over from `init_e2e_schema.py` lines 148–174) → `alembic stamp head` → print next-step seed command. Writes a dated dump artifact to `dev-docs/db-design/dbbackups/` for audit. `tests/e2e/init_e2e_schema.py` becomes a 5-line wrapper delegating with `--env e2e` (keeps existing muscle memory + docs valid).

### F.3 `seed_qa_db.py` (new) — QA orchestrator

Mirrors `seed_e2e_db.py` group ordering (A→B→C→D) but runs **all 8** scenario scripts (QA = full relational density for Tom's beta testing; E2E stays at the 5 cp-covered scenarios). Propagates `SEED_ENV=qa` + `DATABASE_URL` to children. Targets a local `pilot_qa` DB today; Phase 2 QA RDS via tunnel with zero code change (URL-only).

### F.4 `seed_prod_db.py` (new) — prod orchestrator (converge-in-place)

Groups A+B only (registry enforces). Sequence: typed confirmation (`PILOT-PROD-SEED`) → `verify_stripe_key_alignment("pilot/prod/stripe")` → `seed_core.py --env prod` → `seed_platform.py --env prod --stripe-mode <mode>` → inspect summary. `--mode show|inspect` requires no confirmation (read-only). **Existing prod is never reprovisioned — it is converged** (§G-3).

### F.5 `seed_pricebook_starter.py` (new) — per-tenant starter pricebook

```
python migrations/scripts/seed_pricebook_starter.py --env prod --tenant-id <uuid> [--mode seed|show|inspect]
```

JSON-driven (SD-8 supplier-catalog pattern): `migrations/scripts/data/pricebook_starter/default_catalog.json` — starter electrical items (SKU, name, uom, taxability, price). Inserts `pricebook_item` + `pricebook_item_version` rows **for the given tenant** (§G-5: platform-owned rows are schema-impossible). Idempotent per `(tenant_id, sku)` — engineer MCP-verifies whether a unique constraint exists at pre-work; if none, value-scoped DELETE+INSERT per Rule 11.1. **Content sign-off gate: Tom approves the catalog before first prod use** (concierge onboarding step added to `pilot-founder-onboarding-process.md` Stage C).

### F.6 Celery tasks

None.

---

## G. Open Questions Resolved

| # | Question | Resolution |
|---|---|---|
| G-1 | Does `--env` collide with pydantic `ENVIRONMENT` (which rejects `e2e`)? | **Decoupled.** Seed scripts read `--env`/`SEED_ENV` only — never `settings.ENVIRONMENT`. Pydantic `ENVIRONMENT` stays as-is (`dev` locally, `production` in prod task defs) and governs app runtime behavior, not seed values. This is why the flag vocabulary (`prod`) intentionally differs from pydantic's (`production`). |
| G-2 | Prod seeds get live or test Stripe price IDs? (launch plan says live; env-mgmt §4.1.1 mandates uniform test modes in Phase 1) | **Both, phase-driven and explicit.** `--env prod` **requires** `--stripe-mode {test\|live}` — no default, fail-closed. Phase 1 (now): `test` (matches `sk_test_` keys; preflight verifies). GA cutover: keys flip to live in Secrets Manager, then re-run with `--stripe-mode live` to converge the 5 price-ID slots. The launch plan's live IDs are the Phase 2 end state; the one-off UPDATE SQL is retired either way. |
| G-3 | Is existing prod reprovisioned (wipe + schema-restore)? | **No.** Prod already holds signup state from the author's Phase 1 test tenants and passes blue-green migration rules. Prod is **converged in place** by idempotent seed re-runs. The `--env prod` path in `provision_schema.py` exists only for a hypothetical fresh rebuild and is double-gated (`--i-understand-prod-rebuild` + snapshot confirmation). |
| G-4 | What is "qa" when no QA environment exists yet (Phase 1)? | **A data profile, not a location.** `--env qa` = full A+B+C+D density with test-mode values, targetable via `DATABASE_URL` at a local `pilot_qa` DB now and the Phase 2 QA RDS (via tunnel) later with zero code change. |
| G-5 | How do "pricebook starters" work if `pricebook_item.tenant_id` is NOT NULL (MCP-verified)? | **Per-tenant seeding**, not platform-owned rows. `seed_pricebook_starter.py --tenant-id` runs at concierge provisioning time (Beta) and gives each founder tenant a real, editable starter pricebook. GA self-serve signup integration is a future batch (fold into `tenant_signup.py`). Catalog content gated on Tom. |
| G-6 | Schema source of truth for restores — checked-in dump or live dev DB? | **Live dev DB at alembic head** (migrations are authored and verified there; `dev-schema-2026.07.30.sql` at repo root proves Tom already snapshots ad hoc). `provision_schema.py` dumps from dev at provision time AND writes a dated artifact to `dev-docs/db-design/dbbackups/` for audit/repeatability. |
| G-7 | Charter tier has `stripe_price_id_monthly = price_REDACTED09` (dev DB) but is undocumented in `stripe-pricing-config.md` — test or live? | **Inventory task item #1**: engineer locates the ID in the Stripe test vs live dashboard data (or the C-B14/C-B11 batch artifacts), records mode in the registry, and files the `stripe-pricing-config.md §4` update as an Integrations-Lead follow-up (Architect verifies per §12.1 RACI). Until classified, prod seeding leaves the charter row untouched (it is correct in prod already — C-B14 bootstrapped it). |
| G-8 | `notification_template` has 58 platform-default rows; README §4 says 41. | Inventory task reconciles (recent PLATFORM-SMS-B1/B2, B21, MFA-WIRE-1 rows) and updates README §4 in Task 7. No code impact. |
| G-9 | E2E DB port drift — README says 5433, `docker-compose.e2e.yml` says 5434 (5433 = prod tunnel). | README corrected to 5434 in Task 7; guards treat `localhost:5433` as a prod-tunnel shape (prod-only scripts). |
| G-10 | Does the sync runbook replay `pg_dump` on every new migration? | **No.** Schema-restore is for initial provisioning only. Steady-state: envs are stamped at head, so new migrations apply cleanly via `alembic upgrade head` per env (§H.2) — provided E-4 (DDL-only) holds, which is why E-4 is binding. |
| G-11 | Does Telnyx (SMS) get a real path outside prod? (Tom, 2026-08-18 — "we need to discuss") | **DECIDED 2026-08-18 — Option A (Tom):** mock carrier in dev/e2e permanently; Phase 2 QA gets its own real messaging profile + phone number (~$1/mo) per env-mgmt §2. Zero cost/change now; QA gains real SMS fidelity at beta. Lands in §B.3 and `_env_profiles.vendor_posture` (`telnyx: "mock"` for dev/e2e; `"real"` for qa/prod). |

---

## H. Runbook Skeletons (design content the engineer lands into docs)

### H.1 Per-env provisioning runbook (lands in `README-seed-data.md` new §, cross-ref from `aws-ops-runbook.md`)

| Env | Provision | Seed | Re-run cadence |
|---|---|---|---|
| dev | `alembic upgrade head` (unchanged) | existing quick commands | daily reset as today |
| e2e | `provision_schema.py --env e2e` | `tests/e2e/seed_e2e_db.py` (unchanged entry point) | after schema change |
| qa (local `pilot_qa` now; RDS Phase 2) | `provision_schema.py --env qa` | `seed_qa_db.py` | on demand for Tom's beta passes |
| prod | **n/a — converge only** (§G-3) | `seed_prod_db.py --stripe-mode <mode>` (Tom executes) | after any batch touching Group A/B data; at GA key flip |

### H.2 Migration-sync runbook (lands in `README-seed-data.md`; the pre-real-users deliverable)

1. **Author (dev)**: migration is DDL-only (E-4); new reference data goes to `seed_core.py`/`seed_platform.py` in the same PR. `alembic upgrade head` on dev; `pytest -m unit` green.
2. **e2e**: `alembic upgrade head` against `pilot_e2e_db` (stamped at head, so clean) → `seed_core.py --env e2e` + `seed_platform.py --env e2e` (converge new rows) → inspect.
3. **qa**: same as e2e against the qa target.
4. **prod** (blue-green window per `aws-ops-runbook.md`): RDS snapshot → `alembic upgrade head` via tunnel → `seed_prod_db.py --stripe-mode <current-mode>` converge → inspect counts vs README §4 manifest.
5. **Manifest upkeep**: any PR changing seed rows updates README §4 expected counts — the inspect output is the verification contract.

---

## Definition of Done (batch level)

- [ ] All 12 seed scripts accept `--env`/`SEED_ENV` with banner + guards; C/D scripts refuse `--env prod`; `reset_dev_db.py` refuses `e2e`/`prod`
- [ ] `_env_profiles.py` registry + fail-closed resolution + Stripe preflight implemented and unit-tested
- [ ] `seed_platform.py` converges all 5 tier price-ID slots per profile; no hardcoded price IDs remain in script bodies
- [ ] `provision_schema.py` provisions e2e and a scratch local `pilot_qa` from dev dump; stamps `58c3ad26129f`-or-later head; `init_e2e_schema.py` wrapper intact
- [ ] `seed_qa_db.py` scratch run evidence: inspect counts == dev baseline
- [ ] `seed_prod_db.py` dry-run (`--mode show` + `--mode inspect`) validated; **real prod run executed by Tom**
- [ ] `seed_pricebook_starter.py` + JSON catalog; **Tom content sign-off** before prod use
- [ ] Runbooks (§H.1, §H.2) + §B.3 env-value matrix landed in `README-seed-data.md`; `aws-ops-runbook.md` cross-ref; `pilot-founder-onboarding-process.md` concierge step
- [ ] Drift fixes: E2E port 5434; `notification_template` count; charter price-ID Integrations follow-up filed
- [ ] Vendor-posture matrix (§B.3) landed in `README-seed-data.md`; seed banner prints resolved vendor posture per env
- [ ] `pytest -m unit` baseline maintained (regression baseline captured at pre-work per standard inclusions)
- [ ] **ADR-0016** (schema-restore provisioning + env-aware seeds + DDL-only migrations) recorded by Architect upon Tom's approval of this design
- [ ] Zero new AWS cost (no new services, no infra delta)

---

## Handoff

On Tom's approval: Architect authors `batch-db-mgmt-1-python-engr-prompt.md` per `backend/python-engr-std-prompt-inclusions.md` (full read at authoring time — Rule 9.1), including the mandatory Seed Data Rollout section (§20 of the inclusions; content = §B.2 above), the two-phase verification gate with the vendor-deselected full-suite command, and MCP pre-work queries (already executed here — reused in the prompt's pre-work section). No React/RN prompt, no designer spec, no OpenAPI handoff.
