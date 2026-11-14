# Batch Design: TEST-UPLIFT-1A — Mechanical Error-Coverage (Python Track) + Ops Guards

**Version**: 1.0
**Date**: 2026-08-27
**Author**: Pilot Architect
**Batch**: TEST-UPLIFT-1A (Phase 1 — launch plan §1.1 Ord 18; sub-batch of TEST-UPLIFT-1, Ord 4 / §3.4)
**Owner**: Pilot Python Engineer (executing); Tom (Terraform apply + prod verification steps)
**Prompt**: `batch-test-uplift-1a-python-engr-prompt.md`
**Source plan**: `pilot-launch-plan.md` §3.4 scope items **1, 4, 5, 7, 8, 9** (items 2, 3, 6 belong to sub-batches 1B React / 1C RN — sequential sub-batches per Tom 2026-08-27: *"single sub-batch approach… we may learn things that we will need to feed into the next sub-batch work"*)
**Estimated session**: 4–5 hours
**Cost impact**: **$0** — no new AWS resources, no new services; the MAP_CACHE Terraform change is two env vars on existing task defs (infrastructure-constraints §1: no founder cost review required)

---

## A. Input Read Summary

| Input | What was read / verified | Date |
|---|---|---|
| `pilot-launch-plan.md` | §1.1 Ord 4 (TEST-UPLIFT-1, deps met: seeded DB ✅); §3.4 full card (scope 1–9, out-of-scope, rules); §7 gate row; §1.2 row 2 (BE-TESTS-MAINT — receives the error-coverage remainder, §G Q1) | 2026-08-27 |
| `pilot-architect-methods.md` | §3 Standard Architecture Design Workflow (A–G sections); §3.0.1 inclusions compliance | 2026-08-27 |
| `backend/python-engr-std-prompt-inclusions.md` | Full file (943 lines) — all REQUIRED/CONDITIONAL sections; §20 Seed Data Rollout trigger analysis (§G Q6) | 2026-08-27 |
| `postgres-mcp-guide.md` | Canonical MCP query patterns; two-server access gates | 2026-08-27 |
| `backend/core/celery_app.py` | `imports=[…]` list (39 entries) + full `beat_schedule` — diffed against `backend/tasks/` directory (40 task modules excl. `__init__.py`) → **`tasks/tenant_site_emails.py` is NOT registered** (live bug, §G Q2) | 2026-08-27 |
| `backend/tasks/` (directory listing) | 40 task modules inventoried for the registration-guard diff | 2026-08-27 |
| `backend/tasks/tenant_site_emails.py` usage | Grep: lazy in-function imports in `api/routes/tenant_site.py` + `api/routes/tenant_10dlc_profile.py`; `.delay()` mocked in `test_cb16_tenant_site*.py` — event-driven task, no Beat entry needed, but worker never imports the module → `NotRegistered`/silent queue pile-up class (2026-08-10 incident) | 2026-08-27 |
| INV-ROUTE-FIX pattern sources | `batch-inv-route-fix-python-engr-prompt.md`; RFC 7807 assertion exemplars `test_alpha_fix_1_webhook_disconnect.py` + `test_cb15_impersonation.py`; archive completion row (+4 regression tests) | 2026-08-27 |
| `backend/openapi.json` | Mutating ops (`post`/`put`/`patch`/`delete`) grep → **300+ hits (truncated at search cap)** → full in-batch closure impossible (§G Q1 ratchet decision) | 2026-08-27 |
| `backend/migrations/scripts/_env_profiles.py` | Prod profile `allowed_db_host_patterns=("rds.amazonaws.com", "localhost:5433")` — missing `127.0.0.1:5433` (scope 9c); guard logic at lines 294–296 (fail-closed confirmed) | 2026-08-27 |
| `test_seed_env_profiles.py` | `test_prod_accepts_tunnel_5433` covers the `localhost` spelling only — sibling assertion spec'd for the IP spelling | 2026-08-27 |
| `backend/README-seed-data.md` | §7.6 QA scratch-DB proof (verified 2026-08-18, 13 steps); §8.1 exclusions; §7 DELETE-safety rule | 2026-08-27 |
| `backend/services/map_service.py` | Cache implemented: key `drive_time:{olat}:{olng}:{dlat}:{dlng}:{hour}`, `setex` with `settings.MAP_CACHE_TTL_SECONDS`, hit-ratio counters, graceful Redis degradation | 2026-08-27 |
| `backend/core/config.py` | `MAP_CACHE_TTL_SECONDS: int = 86400` ✓ · **`MAP_CACHE_ENABLED: bool = False` — default OFF, must be explicitly enabled in prod env** | 2026-08-27 |
| `infrastructure/terraform/modules/compute/main.tf` | Grep `MAP_CACHE` → **0 hits** — prod task defs do not set the toggle → cache almost certainly OFF in prod (§G Q3) | 2026-08-27 |
| `backend/services/tenant_signup.py` | Lines 493–519: post-wizard `create_stripe_customer(db, tenant_id, billing_email)` when `not tenant.stripe_customer_id` + charter-subscription branch — C-B5 partial fix present (scope 9a residual = audit + test, §G Q4) | 2026-08-27 |
| `aws-ops-runbook.md` | §19.7 image-hygiene incident + check; §19.6 deploy checklist already embeds the hygiene check (lines 3152, 3280, 3381) — scope 5 = mechanize, not document | 2026-08-27 |
| `aws-env-mgmt-ops-plan.md` | §9 Environment × Testing Responsibility Matrix (target for test-trigger docs, scope 8); §10 document maintenance rules | 2026-08-27 |
| `postgres-local` MCP (3 queries) | ① `tenant` cols: `stripe_customer_id text NULL`, `free_period_ends_at timestamptz NULL`, four audit cols ✓ (**`subscription_status`/`is_billing_active` are NOT `tenant` columns** — do not reference) · ② `pricebook_item_version`: append-only — `created_at timestamptz NOT NULL **no server default**` (only `recorded_at` has `now()`) — root cause of the 2026-08-25 first-prod-use `NotNullViolation` · ③ dev data point: `tenant` 2 rows / 2 NULL `stripe_customer_id` (expected — seed-created); `alembic_version` = `58c3ad26129f` (head) | 2026-08-27 |
| `batch-int-bug-1-design.md` | Design-doc format exemplar (header block, A–G, §G open-questions pattern) | 2026-08-27 |

---

## B. Migration Plan — **None (zero schema, zero data changes)**

This batch authors **no Alembic migrations**, changes **no columns**, and adds **no seed data**. It is tests + guards + scripts + docs, plus three one-line code fixes (Celery import, host-guard tuple, TF env vars prepared-not-applied).

### B.1 Pre-Migration Verification (MCP state at design time — informational only)

| Check | Result | Source |
|---|---|---|
| Dev alembic head | `58c3ad26129f` | `postgres-local` MCP 2026-08-27 |
| `tenant.stripe_customer_id` | `text`, nullable ✓ | `postgres-local` MCP 2026-08-27 |
| `pricebook_item_version` audit cols | `created_at` NOT NULL **no default**; `created_by` nullable; **no** `updated_at`/`updated_by` (append-only version table) | `postgres-local` MCP 2026-08-27 |
| Dev tenants NULL `stripe_customer_id` | 2/2 (expected — seed-created tenants never traverse the signup wizard; §G Q4) | `postgres-local` MCP 2026-08-27 |

### B.2 Seed Data Rollout (Rule 11.5) — **NOT REQUIRED** (see §G Q6)

No new column, table, lookup row, enum value, or seed row is added. Scope 9d *executes* existing seed scripts against a throwaway scratch DB to prove the write path — it adds no seed content. The absence of a rollout section is deliberate and auditable here.

---

## C. Execution Order

| # | Task | Scope item | Gate to proceed |
|---|---|---|---|
| 1 | **Celery registration guard + live fix** — add `"tasks.tenant_site_emails"` to `celery_app.py` `imports` (C-B16 comment); new test `tests/domains/platform_infrastructure/test_celery_registration.py` asserting every `backend/tasks/*.py` module (excl. `__init__.py`) ∈ `celery_app.conf.imports` | 4 | Guard test fails BEFORE the import fix (proves the bug), passes after |
| 2 | **Seed host-guard IP spelling** — `_env_profiles.py` prod `allowed_db_host_patterns` gains `"127.0.0.1:5433"`; `test_seed_env_profiles.py` gains `test_prod_accepts_tunnel_5433_ip_spelling` + a forbidden-spelling negative assertion | 9c | New tests pass; guard remains fail-closed for `:5432/pilot_dev` |
| 3 | **API error-path coverage ratchet + priority burn-down** — audit meta-test + checked-in baseline (`tests/baselines/error_path_coverage.json`); close gaps for the §C.1 priority list (≤10 endpoints) with RFC 7807 assertions; baseline holds the remainder | 1 | Meta-test green: zero NEW gaps vs baseline; baseline shrinks by exactly the endpoints closed |
| 4 | **Maps cache verify + prod-enable prep** — unit tests (TTL default 86400, key shape, set/get via monkeypatched Redis); Terraform diff prepared (NOT applied) adding `MAP_CACHE_ENABLED="true"` + `MAP_CACHE_TTL_SECONDS="86400"` to api + worker container env in `infrastructure/terraform/modules/compute/main.tf`; env-var inventory row added to `aws-env-mgmt-ops-plan.md` §3 | 9b | Unit tests pass; TF diff reviewed by Tom; Tom/DevOps applies at next deploy window |
| 5 | **G3 founders-billing residual verify** — audit all tenant-creation paths (`tenant_signup.py` ✓ already creates customer; Lambda Path 2 attaches to existing tenant; seed scripts intentionally NULL); unit test asserting signup `_impl` calls `create_stripe_customer` when `tenant.stripe_customer_id` is NULL (Stripe mocked); README-seed-data §4 note documenting intentional NULL on seed tenants | 9a | Audit matrix in completion summary; new test passes |
| 6 | **Seed write-path scratch-DB proof** — extend `README-seed-data.md` §7.6 with the per-tenant-seed proof step + the standing rule ("no seed script ships write-path-unexecuted"); execute the full scratch-DB proof in-batch incl. `seed_pricebook_starter.py --mode seed`; record output | 9d | Proof run clean; §7.6 updated |
| 7 | **Image-hygiene mechanization** — `admin-tools/check_image_hygiene.sh` (both images, exit 1 on find); `runbook §19.7` gains the script as the canonical one-liner; verify `backend/.dockerignore` ✓ (design-time confirmed) + `frontend/.dockerignore` exists and covers `.env*` | 5 | Script exits clean on locally built images (or reports the violation it exists to catch) |
| 8 | **Master Troubleshooting runbook** — new `dev-docs/devops/troubleshooting-runbook.md`: symptom → likely cause → diagnostic → fix; sections: deploy drift (§19.6 canary), Cognito auth/MFA, Stripe subs + Connect, QB sync, Telnyx + SMS delivery, SSE, GPU/voice pipeline, Maps cache (Task 4), Celery unregistered task (Task 1), seed env guards (Task 2) | 7 | Doc merged; cross-links §19.6 + INT-H1 dev-ref docs as they land |
| 9 | **Test-trigger docs** — `aws-env-mgmt-ops-plan.md` §9 gains "Test Suite Trigger Reference": unit / system-domain / integration / E2E — command, marker expression, environment, vendor posture per suite (per launch-plan §3 standing test-layering policy) | 8 | Section merged per the doc's §10 maintenance rules |
| 10 | **Regen + Final gate** — `python generate_app_import_map.py tests > app_model_imports.md` (new test files); changed-files ruff gate; Phase 1 unit → Phase 2 full vendor-deselected suite | — | Zero failures, warning-clean |

### C.1 Task 3 priority burn-down list (money + founder path; verify against audit output, skip any already covered)

| # | Endpoint | Error test to add (≥1) |
|---|---|---|
| 1 | `POST /api/v1/invoices/{invoice_id}/record-payment` | 404 unknown invoice in tenant — RFC 7807 body |
| 2 | `POST /api/v1/invoices/{invoice_id}/send` | 404 / 409-or-422 invalid state — RFC 7807 body |
| 3 | `POST /api/v1/public/invoices/{signed_token}/payment-intent` | 401 garbage token — RFC 7807 (INV-ROUTE-FIX pattern) |
| 4 | `POST /api/v1/public/invoices/{signed_token}/confirm-payment` | 401 garbage token — RFC 7807 |
| 5 | `PUT /api/v1/tenants/{tenant_id}/subscription/upgrade` | 404 cross-tenant / 422 invalid tier |
| 6 | `POST /api/v1/tenants/{tenant_id}/subscription/change-tier` | 422 invalid tier code |
| 7 | `POST /api/v1/signup/` | 422 invalid payload — RFC 7807 validation body |
| 8 | `PUT /api/v1/signup/{tenant_id}/step2` | 404 unknown tenant |
| 9 | `POST /api/v1/customers/` | 422 validation error shape |
| 10 | `POST /api/v1/jobs/` | 404/422 unknown `customer_id`/`site_id` FK |

Ratchet exclusions: `/test` mirror endpoints (coverage counts on the canonical twin); `/api/v1/webhooks/*` (machine-consumed; own suites).

---

## D. New API Endpoints

**None.** No endpoint changes → **no OpenAPI regeneration** (`export_openapi_json.py` not run; `pnpm sync-api-types` NOT required for the 1B handoff — stated explicitly in the prompt because this deviates from the normal BE→FE handoff rule).

---

## E. Pattern Reuse Decisions

| Pattern / rule | Application |
|---|---|
| **RFC 7807 Problem Details** (inclusions §13; Rule 8) | Every new error test asserts the `detail` dict (`type`/`title`/`status`/`detail`) per the INV-ROUTE-FIX / ALPHA-FIX-1 / C-B15 exemplars; 404 (not 403) on tenant-scoped misses (no UUID enumeration) |
| **Sync-by-design** (rules §21) | All new test code + any `_impl` touched stays sync `def` |
| **MCP read-only** (`.roo/rules/02-database-mcp-access.md`) | Verification queries only; `postgres-local` default; no `postgres-prod` in this batch |
| **Fail-closed guards** (DB-MGMT-1 / ADR-0016) | Host guard widened by exactly one spelling; forbidden patterns untouched |
| **Ratchet guard** (new reusable pattern — see §F) | Checked-in baseline of known gaps; meta-test fails only on the *delta* (new gaps) or on a stale baseline entry; burn-down shrinks the baseline. This is how a 300+-endpoint audit fits Rule 9.6 without losing the mechanical net |
| **Test Resilience Rule** (inclusions §6) | All new tests: `client` fixture, `test_tenant`/`test_user`/`tenant_a` fixtures, assert-by-inserted-ID, no row-count assertions |
| **§16 platform UX patterns** | N/A — no user-facing surface |
| **Cost guardrail** | $0 delta; TF change is env vars on existing task defs — no new resource, no founder review required |

---

## F. Shared Module Interfaces & Celery Tasks

### F.1 Celery — one import-line addition, no new tasks

```python
# backend/core/celery_app.py  (imports list, appended)
"tasks.tenant_site_emails",  # C-B16: tenant-site requirement emails (event-driven, no Beat entry)
```

`send_website_requirements_email` is event-driven (`.delay()` from `api/routes/tenant_site.py` + `api/routes/tenant_10dlc_profile.py`) — **no `beat_schedule` entry**.

### F.2 Registration guard test (Task 1)

```python
# backend/tests/domains/platform_infrastructure/test_celery_registration.py
pytestmark = [pytest.mark.domain_platform_infrastructure, pytest.mark.unit]

def _task_modules_on_disk() -> set[str]:
    """Every importable module in backend/tasks/ (excl. __init__), as 'tasks.<name>'."""

def test_every_task_module_is_registered_in_celery_imports() -> None:
    """2026-08-10 incident class: worker silently never registers an unlisted module."""
    registered = set(celery_app.conf.imports or ())
    missing = _task_modules_on_disk() - registered
    assert not missing, f"Task modules missing from celery_app.conf.imports: {sorted(missing)}"
```

### F.3 Error-path coverage ratchet (Task 3)

```python
# backend/tests/domains/platform_infrastructure/test_error_path_coverage.py
pytestmark = [pytest.mark.domain_platform_infrastructure, pytest.mark.unit]

OPENAPI = Path(__file__).parents[3] / "openapi.json"
BASELINE = Path(__file__).parents[2] / "baselines" / "error_path_coverage.json"

def _mutating_operations() -> list[dict]:
    """[{method, path}] for post/put/patch/delete; excludes '/test' mirrors + /api/v1/webhooks/*."""

def _endpoints_with_error_tests() -> set[str]:
    """Endpoints evidenced by tests: path-string match AND a 4xx/5xx status assertion
    in the same test file (grep-based heuristic over backend/tests/**/*.py)."""

def test_no_new_error_path_gaps_vs_baseline() -> None:
    """Ratchet: fail only when an endpoint is uncovered AND not in the checked-in baseline;
    fail also when a baseline entry has become covered (prompt to prune the baseline)."""
```

Baseline file: `backend/tests/baselines/error_path_coverage.json` — `{ "method path": "reason" }`, generated by the audit on first run, then hand-pruned as burn-down lands.

### F.4 Image-hygiene script (Task 7)

```bash
# admin-tools/check_image_hygiene.sh [IMAGE ...]   (default: pilot-api:latest pilot-web:latest)
# For each image: docker run --rm --entrypoint sh <image> -c 'ls /app/.env 2>&1'
# PASS only on "No such file or directory"; exit 1 + FAIL banner otherwise. (runbook §19.7)
```

### F.5 Terraform env-var addition (Task 4 — prepared, Tom/DevOps applies)

```hcl
# infrastructure/terraform/modules/compute/main.tf — api + worker container `environment` lists
{ name = "MAP_CACHE_ENABLED",      value = "true" },
{ name = "MAP_CACHE_TTL_SECONDS",  value = "86400" },
```

---

## G. Open Questions Resolved

- **Q1 — Can the full error-path audit close in one batch?** **No.** `openapi.json` carries 300+ mutating ops (~150+ excluding `/test` mirrors) — full closure violates Rule 9.6 (context overflow). **Resolution**: ratchet design (§F.3) — the audit + meta-test + baseline IS the mechanical net; this batch closes the §C.1 money/founder-path subset (≤10 endpoints); the baseline remainder folds into **BE-TESTS-MAINT** (launch plan §1.2 row 2, Phase 2 engineering track) as its first input.
- **Q2 — `tasks/tenant_site_emails` missing from `celery_app.py` imports: real bug or handled?** **Real bug, fixed in-batch (Task 1).** Routes import the module lazily inside the function body, so the *API container* resolves `@celery_app.task` at call time and `.delay()` publishes — but the **worker** container only imports modules listed in `celery_app.conf.imports`, so the task is unregistered there and messages never execute. Same class as the 2026-08-10 incident. Discovered at design time by diffing the directory against the imports list; the new guard test must fail before the fix and pass after.
- **Q3 — Maps cache is implemented but `MAP_CACHE_ENABLED` defaults `False` and is absent from Terraform: who fixes prod?** Python Engineer adds unit tests + prepares the TF diff (§F.5) and the env-mgmt §3 inventory row; **Tom/DevOps applies TF at the next manual deploy window** (standing policy: manual prod deploys through founder beta). The troubleshooting runbook (Task 8) gains a "Maps costs spiking" symptom row pointing at the toggle. $0 cost delta; protects the ~$77/mo variable Maps spend per `scaling-logic.md` §4.
- **Q4 — G3 residual: should dev/prod seed tenants get a `stripe_customer_id` backfill?** **No.** Seed-created tenants intentionally carry NULL (they never traverse the signup wizard; creating real Stripe customers for fake tenants pollutes the Stripe account). The residual verify = ① audit of all tenant-creation paths (signup wizard ✓ creates customer per `tenant_signup.py`; invite-landing Lambda Path 2 attaches users to an existing tenant — no new tenant; seed scripts — intentional NULL), ② a mocked-Stripe unit test locking the signup behavior, ③ a README-seed-data §4 note. Dev DB shows 2/2 NULL — expected, recorded as the design-time data point.
- **Q5 — Where do meta/coverage tests live (no `meta` domain marker exists; `--strict-markers`)?** `tests/domains/platform_infrastructure/` with `pytest.mark.domain_platform_infrastructure` + `pytest.mark.unit` — platform/tooling guards belong to the platform-infrastructure domain. No new pytest marker is introduced.
- **Q6 — Is a Seed Data Rollout section (Rule 11.5) required?** **No, and the design says so explicitly (§B.2).** The batch adds zero DB data: no column, table, lookup row, enum value, or seed-row change. Scope 9d *executes* existing scripts on a throwaway scratch DB. The prompt carries an explicit "N/A — rationale" note so the omission is auditable rather than accidental.
- **Q7 — Does the coverage baseline risk blocking the Phase 2 full-suite gate?** No. The baseline is checked in, so the meta-test is deterministic; it fails only on (a) a NEW uncovered mutating endpoint, or (b) a baseline entry that has become covered (prune reminder). Burn-down work can only shrink the baseline, never grow it — additions to the baseline require Architect/Tom sign-off in review.
- **Q8 — Troubleshooting runbook scope creep?** Bounded to the nine symptom sections in §C Task 8, compact table format (symptom → likely cause → diagnostic → fix). Future incidents append rows via the doc's own maintenance note; INT-H1 dev-ref docs cross-link as they land (they are not a dependency).
