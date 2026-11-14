# Implementation Prompt: TEST-UPLIFT-1A — Mechanical Error-Coverage (Python Track) + Ops Guards

**Mode**: Pilot Python Engineer
**Batch**: TEST-UPLIFT-1A
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §1.1 Ord 4 (umbrella) + Ord 18 (this sub-batch); full umbrella card §3.4 — **this batch owns scope items 1, 4, 5, 7, 8, 9 only**
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-test-uplift-1a-design.md` — read in full; §G holds 8 binding design decisions (Q1 ratchet scoping, Q2 Celery live bug, Q3 Maps TF ownership, Q4 G3 no-backfill, Q5 test domain, Q6 seed-rollout N/A, Q7 baseline semantics, Q8 runbook bounds)
**Estimated session**: 4–5 hours
**Platform**: Backend (`backend/`) + `infrastructure/terraform` (diff prep only — NOT applied) + `admin-tools/` + `dev-docs/devops/` docs
**Frontend companion**: none. **Handoff deviation**: this batch changes **zero endpoints** → do **not** run `python export_openapi_json.py`, and the React sub-batch (TEST-UPLIFT-1B) does **not** need `pnpm sync-api-types` as a handoff signal. State this in your Completion Summary for the Architect.

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-python-engineer/python-engineer-rules.md`** — full document; the 25 hard rules are non-negotiable STOPs
- **`dev-docs/architecture-design/pilot-python-engineer-methods.md`** — §13 (Alembic), §8 (Router Design), §5 (Model Design), §16 (Standard Task Workflow)
- **`backend/tests/README-adding-tests.md`** — full document; governs all test file structure, domain markers, fixture rules
- **`batch-test-uplift-1a-design.md`** — the design doc; §C is your task sequence, §F your interface specs, §G your binding decisions

Critical rules for this batch:

- **Rule 1**: Never guess column names, data types, or table names. Use `postgres-local` MCP to verify every name before use. If MCP returns an error → **STOP and ask Tom**.
- **Rule 5**: Never use module-level `TestClient` in any test file. Always use the `client` fixture from `conftest.py`.
- **Rule 7**: The `postgres-local` MCP is for **read-only verification only**. Never use it to INSERT, UPDATE, or DELETE data — all data changes go through the application code.
- **Rule 8**: All API error responses MUST follow RFC 7807 Problem Details format (`{"type": "https://...", "title": "...", "status": N, "detail": "..."}`). Your new error-path tests **assert this shape** — if any endpoint in the §C.1 burn-down list returns a non-RFC-7807 error body, that is a real bug: fix the endpoint to the RFC 7807 dict pattern (see `test_alpha_fix_1_webhook_disconnect.py` for the assertion exemplar) and note it in the Completion Summary.
- **Rule 11**: If ANY test fails during your work — even one that appears pre-existing — **you must fix it before declaring the batch done**. If you cannot identify the root cause → STOP and ask Tom.
- **Rule 12 (sync routes — rules §21)**: This app is **synchronous by design**. Any helper or `_impl()` you touch that uses the `Session` stays a plain `def`. Never `async def` around the blocking `Session`.
- **Rule 14 (Ruff — rules §23)**: Run ruff **only against the files you changed** — `git diff --name-only --diff-filter=d HEAD -- '*.py' | sed 's|^backend/||'` from `backend/`, then `ruff check --fix <files> && ruff format <files> && ruff check <files>`. **Fix ALL errors in those files**, including pre-existing ones.
- **Rule 16 (verify, don't assume — rules §25)**: 186 tables exist. Query `information_schema.columns` for every table you reference this session before writing SQL. The Architect's MCP results (design §B.1) are a design-time snapshot — you re-verify independently (see Pre-Work).

**Billing/subscription context for Task 5** (inclusions §19 callout): before writing the G3 verify test, read `dev-docs/pilot-operations.md` — tier→plan→ppfv cascade, `is_billing_active` paywall gate, Charter cohort Stripe schedule, and the 6 subscription status codes. The billing logic is NOT inferrable from the schema alone.

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
> **Two read-only MCP servers exist** (global rule `.roo/rules/02-database-mcp-access.md`): **`postgres-local`** is the default for all verification. **`postgres-prod`** reads production but **requires an SSH tunnel that only Tom controls** — ask Tom to confirm the tunnel is up before your first `postgres-prod` query, and STOP on any connection error. **This batch uses `postgres-local` only** — no prod queries.

```sql
-- 1. G3 context (Task 5): tenant Stripe columns — confirm names/types before any test SQL.
--    Architect design-time result: stripe_customer_id text NULL; free_period_ends_at timestamptz NULL.
--    NOTE: subscription_status / is_billing_active are NOT tenant columns — do not reference them here.
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'tenant'
  AND column_name IN ('id','stripe_customer_id','free_period_ends_at','created_at','updated_at','created_by','updated_by')
ORDER BY ordinal_position;

-- 2. Scope 9d root-cause context (Task 6): pricebook_item_version is append-only —
--    created_at NOT NULL with NO server default (only recorded_at has now()).
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'pricebook_item_version'
ORDER BY ordinal_position;

-- 3. Dev DB migration head (context only — no migration work in this batch).
SELECT version_num FROM public.alembic_version;

-- 4. G3 data point (Task 5): dev seed tenants are expected NULL (they never traverse the signup wizard).
SELECT count(*) AS tenants_total,
       count(*) FILTER (WHERE stripe_customer_id IS NULL) AS tenants_null_stripe_customer
FROM public.tenant;
```

> **Engineer safety net — independent column verification (MANDATORY)**: Before writing ANY SQL statement, Alembic migration code, or SQLModel field reference in this batch, run `SELECT column_name, data_type, is_nullable, column_default FROM information_schema.columns WHERE table_schema = 'public' AND table_name = '<table>' ORDER BY ordinal_position;` for **every table you will touch**. If any column name in this prompt does not match what MCP returns → use the MCP-returned name, not the prompt's name, and note the discrepancy in your Completion Summary.

---

## Pre-Work: Read These Source Files

Use `read_file` on each of these before writing any code:

```
backend/core/celery_app.py                                  ← imports list + beat_schedule (Task 1 target)
backend/tasks/tenant_site_emails.py                         ← the unregistered module being fixed (Task 1)
backend/api/routes/tenant_site.py                           ← lazy-import call site (lines ~177–180)
backend/migrations/scripts/_env_profiles.py                 ← prod profile allowed_db_host_patterns (Task 2 target)
backend/tests/domains/platform_infrastructure/test_seed_env_profiles.py  ← sibling test pattern (Task 2)
backend/services/map_service.py                             ← cache key/TTL/counters (Task 4)
backend/core/config.py                                      ← MAP_CACHE_TTL_SECONDS=86400, MAP_CACHE_ENABLED=False default (Task 4)
backend/services/tenant_signup.py                           ← lines ~490–520: post-wizard create_stripe_customer (Task 5)
backend/services/stripe_subscriptions.py                    ← create_stripe_customer signature/behavior (Task 5)
backend/README-seed-data.md                                 ← §7.6 QA scratch-DB proof; §4 Current Seed State (Task 6 targets)
backend/tests/conftest.py                                   ← available fixtures (never re-declare)
backend/tests/domains/notifications_comms/test_alpha_fix_1_webhook_disconnect.py  ← RFC 7807 assertion exemplar
backend/tests/domains/platform_infrastructure/test_cb15_impersonation.py          ← RFC 7807 assertion exemplar (detail dict)
backend/openapi_schema_map.md                               ← endpoint reference for the Task 3 burn-down list
infrastructure/terraform/modules/compute/main.tf            ← container environment lists (Task 4 diff target — DO NOT APPLY)
dev-docs/devops/aws-ops-runbook.md                          ← §19.6 (deploy checklist), §19.7 (image hygiene) — Tasks 7–8
dev-docs/devops/aws-env-mgmt-ops-plan.md                    ← §3 (env-var inventory), §9 (testing matrix), §10 (maintenance rules) — Tasks 4, 9
dev-docs/pilot-operations.md                                ← billing context (Task 5 — see MANDATORY STOP callout)
backend/db_models_map.md                                    ← model ↔ table orientation (reference only — no model changes)
```

Also run these grep commands to find related files:

```bash
cd <repo>
grep -rn "create_stripe_customer" backend/ --include="*.py" -l
grep -rn "MAP_CACHE" backend/ infrastructure/ -l
grep -rn "tenant_site_emails" backend/ --include="*.py" -l
grep -rln "dockerignore" frontend/ --include="*.md" | head -5; ls -la frontend/.dockerignore backend/.dockerignore 2>&1
```

---

## Background / Context

TEST-UPLIFT-1 (launch plan §3.4) is Tom's mandate: *every 500-class failure must be caught mechanically before Phase 2*. Tom split it into sequential sub-batches (2026-08-27) — **1A is the Python track**: API error-path coverage ratchet, Celery registration guard, image-hygiene mechanization, the troubleshooting runbook, test-trigger docs, and the four PLAT-DEBT/INT-H1 cherry-picks (G3 billing verify, Maps cache verify, seed host-guard fix, seed write-path proof). Learnings from 1A feed the 1B (React) and 1C (RN) designs.

**Design-time discoveries already verified by the Architect (your job: fix + lock with tests):**
1. `tasks/tenant_site_emails.py` is **not** in `celery_app.conf.imports` — the C-B16 website-requirements email task never registers on the worker (2026-08-10 incident class, live bug).
2. The prod seed host guard accepts `localhost:5433` but not the `127.0.0.1:5433` spelling the runbook teaches.
3. `MAP_CACHE_ENABLED=False` by default and `MAP_CACHE*` appears **nowhere** in Terraform — the Maps 24h Redis cache is almost certainly OFF in prod (~$77/mo variable cost unprotected).
4. `pricebook_item_version.created_at` is NOT NULL with **no server default** — the exact cause of the 2026-08-25 first-prod-use seed failure that scope 9d prevents from recurring.

---

## Task 1 — Celery Registration Guard + Live Fix (scope item 4)

**What to change:**

1. Add the missing import to `backend/core/celery_app.py` `imports=[...]` (append after `tasks.messaging_recurring`, keep the comment style):

```python
"tasks.tenant_site_emails",  # C-B16: tenant-site requirement emails (event-driven, no Beat entry)
```

No `beat_schedule` entry — the task is event-driven (`.delay()` from `api/routes/tenant_site.py` and `api/routes/tenant_10dlc_profile.py`).

2. Create `backend/tests/domains/platform_infrastructure/test_celery_registration.py`:

```python
"""Guard: every module in backend/tasks/ must be registered in celery_app.conf.imports.

Incident class 2026-08-10 (and again design-time 2026-08-27: tasks/tenant_site_emails.py
was missing — event-driven .delay() publishes from the API container, but the worker only
imports listed modules, so messages never execute).
"""

from pathlib import Path

import pytest

from core.celery_app import celery_app

pytestmark = [
    pytest.mark.domain_platform_infrastructure,
    pytest.mark.unit,
]

TASKS_DIR = Path(__file__).parents[3] / "tasks"


def _task_modules_on_disk() -> set[str]:
    return {
        f"tasks.{p.stem}"
        for p in TASKS_DIR.glob("*.py")
        if p.stem != "__init__"
    }


def test_every_task_module_is_registered_in_celery_imports() -> None:
    registered = set(celery_app.conf.imports or ())
    missing = _task_modules_on_disk() - registered
    assert not missing, (
        f"Task modules missing from celery_app.conf.imports: {sorted(missing)}. "
        "Add them or the worker will never register their tasks."
    )
```

**Write the test FIRST and watch it FAIL** (it must report `tasks.tenant_site_emails` missing) — that failure is the proof the bug is real. Then apply the import fix and watch it pass. Record both runs in the Completion Summary.

**Intermediate run**: `python -m pytest tests/domains/platform_infrastructure/test_celery_registration.py -v 2>&1 | tail -5`

---

## Task 2 — Seed Host-Guard IP Spelling (scope item 9c)

**What to change** in `backend/migrations/scripts/_env_profiles.py` (prod profile, ~line 187):

```python
allowed_db_host_patterns=("rds.amazonaws.com", "localhost:5433", "127.0.0.1:5433"),
```

The runbook teaches `127.0.0.1:5433` for the SSH tunnel; the guard only accepted the `localhost` spelling. Guard stays fail-closed — `forbidden_db_host_patterns=(":5432/pilot_dev",)` is untouched.

**Add to** `test_seed_env_profiles.py` (sibling of `test_prod_accepts_tunnel_5433`):

```python
def test_prod_accepts_tunnel_5433_ip_spelling(self):
    """Runbook teaches 127.0.0.1:5433 — same tunnel as localhost:5433, guard accepts both."""
    p = get_profile(SeedEnv.PROD, "test")
    assert_target_compatible(p, "postgresql://pilot:pilot@127.0.0.1:5433/pilot_prod")

def test_prod_still_refuses_dev_db_on_ip_spelling(self):
    """Fail-closed: the IP spelling must not widen the guard to the dev DB."""
    p = get_profile(SeedEnv.PROD, "test")
    with pytest.raises(SystemExit):
        assert_target_compatible(p, "postgresql://pilot:pilot@127.0.0.1:5432/pilot_dev")
```

Match the file's existing class structure/imports. **Intermediate run**: `python -m pytest tests/domains/platform_infrastructure/test_seed_env_profiles.py -v 2>&1 | tail -10`

---

## Task 3 — API Error-Path Coverage Ratchet + Priority Burn-Down (scope item 1)

`openapi.json` carries **300+ mutating operations** — full closure in one batch is impossible (design §G Q1). You are building the **ratchet**: a mechanical audit + checked-in baseline + meta-test that fails on any NEW gap, plus closing the 10-endpoint money/founder-path priority list (design §C.1).

**3.1 — Audit meta-test.** Create `backend/tests/domains/platform_infrastructure/test_error_path_coverage.py` implementing the design §F.3 interface:

```python
pytestmark = [pytest.mark.domain_platform_infrastructure, pytest.mark.unit]

OPENAPI = Path(__file__).parents[3] / "openapi.json"
BASELINE = Path(__file__).parents[2] / "baselines" / "error_path_coverage.json"
```

- `_mutating_operations() -> list[dict]` — parse `openapi.json`; keep `post`/`put`/`patch`/`delete`; **exclude** paths ending in `/test` (coverage counts on the canonical twin) and paths under `/api/v1/webhooks/` (machine-consumed, own suites). Key each op as `"METHOD /path"`.
- `_endpoints_with_error_tests() -> set[str]` — grep-based heuristic over `backend/tests/**/*.py`: an endpoint counts as covered when a test file contains the endpoint's path string **and** a 4xx/5xx status assertion (`status_code == 4`, `== 401/403/404/409/410/422/500`, `HTTP_4`, `HTTP_5`). Document the heuristic's fuzziness in the module docstring — it is a ratchet, not a proof.
- `test_no_new_error_path_gaps_vs_baseline()` — fail when (a) an uncovered mutating endpoint is **absent** from the baseline (new gap), or (b) a baseline entry has **become covered** (stale entry — prune reminder).

**3.2 — Generate the baseline.** Run the audit once to produce `backend/tests/baselines/error_path_coverage.json` (`{ "METHOD /path": "not-yet-covered" }`). Spot-check ~10 entries manually for sanity (false positives from the heuristic are acceptable in the baseline; false negatives are not — err toward listing).

**3.3 — Priority burn-down (design §C.1, ≤10 endpoints).** For each endpoint below: check coverage via the audit; if uncovered, add ≥1 test asserting the 4xx/5xx response **and the RFC 7807 `detail` dict** (`type`/`title`/`status`/`detail` keys), then remove the entry from the baseline:

| # | Endpoint | Error test to add |
|---|---|---|
| 1 | `POST /api/v1/invoices/{invoice_id}/record-payment` | 404 unknown invoice in tenant |
| 2 | `POST /api/v1/invoices/{invoice_id}/send` | 404 / 409-or-422 invalid state |
| 3 | `POST /api/v1/public/invoices/{signed_token}/payment-intent` | 401 garbage token |
| 4 | `POST /api/v1/public/invoices/{signed_token}/confirm-payment` | 401 garbage token |
| 5 | `PUT /api/v1/tenants/{tenant_id}/subscription/upgrade` | 404 cross-tenant / 422 invalid tier |
| 6 | `POST /api/v1/tenants/{tenant_id}/subscription/change-tier` | 422 invalid tier code |
| 7 | `POST /api/v1/signup/` | 422 invalid payload |
| 8 | `PUT /api/v1/signup/{tenant_id}/step2` | 404 unknown tenant |
| 9 | `POST /api/v1/customers/` | 422 validation error shape |
| 10 | `POST /api/v1/jobs/` | 404/422 unknown `customer_id`/`site_id` FK |

Domain folders: invoicing → `tests/domains/invoicing_billing/`; subscription → `subscriptions_usage/`; signup → `subscriptions_usage/` (or the folder existing signup tests live in — grep first); customers → `crm/`; jobs → `field_operations/`. Prefer **appending tests to the existing test files** for those endpoints where a natural home exists; create new files only where none exists. If an endpoint turns out to already be covered, record that and move on — do not duplicate.

**If a burn-down endpoint returns a non-RFC-7807 error body**: fix the endpoint to the RFC 7807 dict (Rule 8) — that is exactly the class of bug this batch exists to catch. Keep endpoint fixes minimal and RFC-shaped; no behavior redesign.

**3.4 — Ratchet semantics** (design §G Q7): the baseline may only shrink in this batch. Growing it (adding uncovered endpoints beyond what the first generation produced) requires a note to the Architect in the Completion Summary.

**Intermediate run**: `python -m pytest tests/domains/platform_infrastructure/test_error_path_coverage.py tests/domains/invoicing_billing/ tests/domains/subscriptions_usage/ -m unit --tb=short -q 2>&1 | tail -10`

---

## Task 4 — Maps Cache Verification + Prod-Enable Prep (scope item 9b)

The cache is implemented (`map_service.py`: key `drive_time:{olat}:{olng}:{dlat}:{dlng}:{hour}`, `setex` with `MAP_CACHE_TTL_SECONDS`, hit-ratio counters) but `MAP_CACHE_ENABLED=False` by default and **Terraform never sets it**.

**4.1 — Unit tests** (add to the existing `map_service` test file if one exists — grep `backend/tests/` for `map_service` first; otherwise create `tests/domains/scheduling_dispatch/test_map_service_cache.py` with `domain_scheduling_dispatch` + `unit`):
- `MAP_CACHE_TTL_SECONDS` default == `86400` (assert on `core.config.settings`).
- `_make_cache_key` shape: `drive_time:...:{hour}` with 4-decimal coordinate rounding.
- Cache set→get round-trip with the Redis client **monkeypatched/faked** (no real Redis — do NOT mark `requires_redis`; follow the `_redis_client_instance = None` reset pattern documented in `map_service.py` comments).
- Cache-miss → provider-call → cache-populate flow: second call hits cache, provider mock called once.

**4.2 — Terraform diff (prepare, DO NOT APPLY)** in `infrastructure/terraform/modules/compute/main.tf` — add to the **api** and **celery-worker** container `environment` lists (match existing entry style):

```hcl
{ name = "MAP_CACHE_ENABLED",     value = "true" },
{ name = "MAP_CACHE_TTL_SECONDS", value = "86400" },
```

Leave the change **uncommitted-infrastructure-diff for Tom review** (manual-deploy policy; Tom/DevOps applies at the next deploy window). Note in the Completion Summary whether you committed the TF file on the batch branch or left it staged — Tom decides when `terraform apply` runs.

**4.3 — Env-var inventory** — add the two vars to `aws-env-mgmt-ops-plan.md` §3 (match the existing row format; per its §10 maintenance rules, an env-var addition must update that doc in the same change).

**Intermediate run**: `python -m pytest -m unit -k map -q 2>&1 | tail -5`

---

## Task 5 — G3 Founders-Billing Residual Verify (scope item 9a)

**Read `dev-docs/pilot-operations.md` first** (MANDATORY STOP callout). Design §G Q4 is binding: **no backfill** — seed tenants intentionally carry NULL `stripe_customer_id`.

**5.1 — Tenant-creation path audit.** Enumerate every path that creates a `tenant` row and record its Stripe-customer behavior in the Completion Summary matrix: ① self-serve signup wizard (`tenant_signup.py` ~lines 493–519 — creates customer post-transaction when NULL ✓); ② invite-landing Lambda Path 2 (attaches users to an existing tenant — no new tenant; verify by reading the Lambda source under `backend/lambda/`); ③ seed scripts (intentional NULL — document); ④ any other `Tenant(` construction site (grep `grep -rn "Tenant(" backend/services backend/api --include="*.py" -l`).

**5.2 — Locking test** (add to the existing signup test file in `tests/domains/subscriptions_usage/` if one exists — grep `tenant_signup` under `backend/tests/` first): simulate a tenant row with `stripe_customer_id IS NULL` reaching the post-wizard step, mock `create_stripe_customer` (and `create_charter_subscription` if the free-period branch is exercised — see the imports at `tenant_signup.py` ~line 498), assert the customer-creation call fires with `(db, tenant_id, billing_email)` and the tenant is reloaded. Stripe must be **mocked** — do NOT mark `requires_stripe`.

**5.3 — Doc note** — one line in `backend/README-seed-data.md` §4 (Current Seed State): seed tenants intentionally carry NULL `stripe_customer_id` (never traverse the signup wizard); G3 verified TEST-UPLIFT-1A.

**Intermediate run**: `python -m pytest tests/domains/subscriptions_usage/ -m unit --tb=short -q 2>&1 | tail -5`

---

## Task 6 — Seed Write-Path Scratch-DB Proof (scope item 9d)

Root cause (MCP-verified): `pricebook_item_version.created_at` is NOT NULL with no server default — `seed_pricebook_starter.py --mode seed` had never executed against a live DB before first prod use (2026-08-25 `NotNullViolation`, fixed same day). The standing rule you are codifying: **no seed script ships write-path-unexecuted.**

**6.1 — Execute the proof** (full §7.6 flow + the new per-tenant step) against a throwaway scratch DB:

```bash
cd <repo>/backend
source .venv/bin/activate

# 1. Fresh scratch DB + schema (per README §7.6)
createdb -h localhost -p 5432 -U pilot_user pilot_seed_proof_scratch || dropdb -h localhost -p 5432 -U pilot_user pilot_seed_proof_scratch && createdb -h localhost -p 5432 -U pilot_user pilot_seed_proof_scratch
DATABASE_URL=postgresql://pilot:pilot@localhost:5432/pilot_seed_proof_scratch python migrations/scripts/provision_schema.py --env qa

# 2. Full group seed (A→B→C→D, 13 steps)
DATABASE_URL=postgresql://pilot:pilot@localhost:5432/pilot_seed_proof_scratch python migrations/scripts/seed_qa_db.py

# 3. NEW — per-tenant seed write-path proof (the step that would have caught 2026-08-25)
DATABASE_URL=postgresql://pilot:pilot@localhost:5432/pilot_seed_proof_scratch python migrations/scripts/seed_pricebook_starter.py --mode seed

# 4. Inspect counts vs README §4 manifest
DATABASE_URL=postgresql://pilot:pilot@localhost:5432/pilot_seed_proof_scratch python migrations/scripts/seed_core.py --env qa --mode inspect

# 5. Drop the scratch DB
dropdb -h localhost -p 5432 -U pilot_user pilot_seed_proof_scratch
```

If step 3's CLI differs (flags/args), read `seed_pricebook_starter.py` argparse first and adjust — the requirement is: `mode_seed` executes end-to-end against the scratch DB with zero errors. **If the proof fails → fix the seed script in this batch** (that is the point of the proof) and record the fix.

**6.2 — Codify in `README-seed-data.md` §7.6**: add the per-tenant-seed proof step to the runbook block + a standing-rule line: *"Every new or changed seed script must execute its `mode_seed` write path against a scratch DB as part of the §7.6 QA-proof before its batch closes — no seed script ships write-path-unexecuted."* Update the "verified" date note with today's run result.

---

## Task 7 — Image-Hygiene Mechanization (scope item 5)

Runbook §19.7 documents the check manually; the deploy checklist (§19.6) already calls it. Mechanize it:

**7.1 — Create `admin-tools/check_image_hygiene.sh`** (executable, `set -euo pipefail`):

```bash
#!/usr/bin/env bash
# check_image_hygiene.sh [IMAGE ...] — runbook §19.7: built images must NOT contain /app/.env
# Default: pilot-api:latest pilot-web:latest. Exit 0 = all clean; exit 1 = violation found.
set -euo pipefail
images=("${@:-pilot-api:latest pilot-web:latest}")
# (word-split default intentionally; or accept explicit args)
fail=0
for img in ${images[*]}; do
  out=$(docker run --rm --entrypoint sh "$img" -c 'ls /app/.env 2>&1' || true)
  if echo "$out" | grep -q "No such file"; then
    echo "  ✅ PASS $img — no /app/.env"
  else
    echo "  ❌ FAIL $img — /app/.env FOUND in image ($out)"
    fail=1
  fi
done
exit "$fail"
```

(Tighten the arg-default handling as you see fit — behavior is the contract.)

**7.2 — Run it** against locally built images if present (`docker images | grep pilot`); if no local images exist, run it as a dry argument check and note that the next §8.1/§8.3 build must invoke it (it is now the canonical one-liner in §19.7 — **7.3**).

**7.3 — Edit runbook §19.7** (`aws-ops-runbook.md`): add the script as the canonical check command (keep the raw `docker run` form documented underneath for transparency).

**7.4 — Verify `.dockerignore` coverage**: `backend/.dockerignore` exists (Architect-confirmed) — confirm it excludes `.env*`; verify `frontend/.dockerignore` exists and excludes `.env*` (the web image builds from the `frontend/` context per §8.3). If `frontend/.dockerignore` is missing or leaks `.env`, fix it in-batch and flag prominently in the Completion Summary.

---

## Task 8 — Master Troubleshooting Runbook (scope item 7)

Create **`dev-docs/devops/troubleshooting-runbook.md`** — Tom-facing: *symptom → likely cause → diagnostic steps → fix*. Bounded scope (design §G Q8) — exactly these sections, compact table format per section:

1. **Deploy drift** — cross-link runbook §19.6 canary (revision vs image-digest parity; `:latest` corollary)
2. **Cognito auth/MFA** — login failures, MFA lockout, SMS delivery (cross-link `aws-cognito-prod-setup.md`)
3. **Stripe (subscriptions + Connect)** — webhook drift, test/live key mismatch, seed price-ID convergence (`_env_profiles.py` registry)
4. **QuickBooks sync** — token refresh, conflict queue, `intuit_tid`
5. **Telnyx + SMS delivery** — 10DLC status, TFN verification, quota periods
6. **SSE** — `?token=JWT` requirement, thread-per-connection limit
7. **GPU / voice pipeline** — Whisper/Ollama reachability from ECS, p95 latency trigger (2.5s per `scaling-logic.md`)
8. **Maps cache** — "Maps costs spiking" → check `MAP_CACHE_ENABLED` in the prod task def (Task 4 finding)
9. **Celery** — "task never runs" → registration guard (Task 1); beat-schedule vs event-driven distinction
10. **Seed env guards** — fail-closed host guard; `127.0.0.1:5433` vs `localhost:5433` spellings (Task 2)

Header block: title, version 1.0, date, author "Pilot Python Engineer (TEST-UPLIFT-1A)", purpose, and a maintenance note (append a row per incident; cross-link INT-H1 dev-ref docs as they land). Include a doc header per house style (match `aws-ops-runbook.md` conventions).

---

## Task 9 — Test-Trigger Documentation (scope item 8)

Add a **"Test Suite Trigger Reference"** subsection to `aws-env-mgmt-ops-plan.md` under §9 (Environment × Testing Responsibility Matrix), per its §10 maintenance rules. Cover per suite: **command**, **marker expression**, **environment**, **vendor posture**:

| Suite | Trigger command | Where it runs | Vendor posture |
|---|---|---|---|
| Unit | `python -m pytest -m unit` | local dev + CI | all vendors mocked (autouse fixtures) |
| System / domain | `python -m pytest tests/domains/<domain>/ -m unit` | local dev | mocked |
| Integration | `python -m pytest -m integration` | dev stack | per env plan §2 (Stripe test mode; Telnyx mock/live toggle) — **never fire real customer SMS on prod** (launch-plan §3 standing policy) |
| E2E web | Playwright suite (per `aws-ops-runbook.md` §20) | prod (Phase 1 integration env) | live, test tenants only |
| E2E mobile | Maestro specs | iOS Expo dev build | live, test tenants only |
| Vendor-marked | `-m requires_telnyx / requires_stripe / requires_sendgrid / requires_redis` | on demand, env vars coordinated with Tom | vendor test modes |

Align wording with the launch-plan §3 "Test environment layering" standing policy.

---

## Verification Checkpoints

- After Tasks 1–2: `python -m pytest tests/domains/platform_infrastructure/ -m unit --tb=short -q 2>&1 | tail -10`
- After Task 3: the Task 3 intermediate run (above) — zero new-gap ratchet failures
- After Tasks 4–5: `python -m pytest -m unit --tb=short -q 2>&1 | tail -5`
- After Task 6: scratch-DB proof output recorded (counts vs §4 manifest)

---

## Regeneration Steps (this batch)

New test files are added → regenerate the import map:

```bash
cd <repo>/backend && source .venv/bin/activate
python generate_app_import_map.py tests > app_model_imports.md
```

**Explicitly NOT run in this batch** (no changes of the relevant kind — stating for auditability):
- `python export_openapi_json.py` — **zero endpoint changes** (design §D)
- `python generate_db_model_map.py app > db_models_map.md` — **zero model changes**
- `schema_manager.py` — **zero schema changes**
- Alembic — **zero migrations**

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
python -m pytest tests/domains/platform_infrastructure/ -v 2>&1 | tail -25
echo "=== TEST-UPLIFT-1A FINAL VERIFICATION COMPLETE ==="
```

> **Vendor-suite inclusion call (explicit, per template)**: This batch modifies **no** Telnyx/Stripe/SendGrid/Redis-covered runtime code. The new map-cache tests use a monkeypatched/faked Redis client (NOT `requires_redis`); the G3 signup test mocks Stripe (NOT `requires_stripe`). Therefore the vendor marker suites are **NOT run**. If you find you must mark any new test with a vendor marker, STOP and tell Tom — that changes this call.

> **Warning-clean is part of done.** `ruff` must report no remaining issues **in your changed files** (no unjustified `# noqa`), and the pytest run must be free of `DeprecationWarning` noise. **Do not run `ruff check .` against the entire codebase** — scope to changed files only (rules §23).

> **Any failure in either phase must be fixed before the batch is declared done.** There is no "pre-existing failure" exception without explicit written confirmation from Tom. If you cannot identify the root cause → STOP and ask Tom.

---

## Test Requirements

Per `backend/tests/README-adding-tests.md`:

**Every new test file MUST:**
- Declare `pytestmark` with both domain marker and `pytest.mark.unit`:
  ```python
  pytestmark = [
      pytest.mark.domain_platform_infrastructure,   # or the domain folder's marker
      pytest.mark.unit,
  ]
  ```
- Use the `client` fixture (never module-level `TestClient`)
- Use `test_tenant` and `test_user` fixtures (never hardcoded UUIDs)
- Scope assertions by inserted IDs — never `assert len(all_rows) == N`
- Be placed in the correct domain folder under `backend/tests/domains/<domain>/` (see mapping in inclusions §6; meta/guard tests → `platform_infrastructure/` per design §G Q5)

**Test Resilience Rule (MANDATORY):** never UPDATE/DELETE rows you did not INSERT; never assert total row counts; never assume a table is empty (`second_tenant` for empty-state); `db_session` rollback is the cleanup mechanism.

**Autouse fixtures (do not declare; opt out only where needed):** `mock_cognito_jwks`, `mock_ai_services`, `mock_entitlement_allowed` (opt out with `@pytest.mark.skip_mock_entitlement_allowed` only if a test exercises entitlement gating — the Task 3 subscription error tests assert 4xx/422 shapes, not tier gates; add the opt-out marker only if you find the autouse mock masking the error you target).

---

## Seed Data Rollout — **NOT REQUIRED for this batch (design §G Q6)**

Rule 11.5 analysis (recorded for auditability): this batch adds **zero** DB data — no new column, table, lookup/reference row, enum-like value set, migration seed row, or change to existing seed data. Task 6 *executes* existing seed scripts against a throwaway scratch DB to prove their write path; it adds no seed content. The only seed-adjacent edits are the `_env_profiles.py` host-guard tuple (code, not data) and the `README-seed-data.md` §4/§7.6 documentation notes (Tasks 5.3, 6.2), which this prompt explicitly includes.

---

## Definition of Done

Check off each item **in this prompt doc** as it completes:

- [ ] Pre-modification regression baseline captured (`X passed, Y failed`) using `pytest -m unit`
- [ ] Zero pre-existing unit failures confirmed before starting work (or confirmed with Tom)
- [ ] All 4 MCP pre-work queries run — results match design §B.1 expectations (every referenced table verified via `information_schema.columns`, rules §25)
- [ ] All mandatory source files read before writing any code (including `pilot-operations.md` for Task 5)
- [ ] Task 1: guard test **failed before** the import fix (missing-module proof recorded), passes after; `"tasks.tenant_site_emails"` registered
- [ ] Task 2: `127.0.0.1:5433` accepted for prod; `:5432/pilot_dev` on the IP spelling still refused (fail-closed)
- [ ] Task 3: ratchet meta-test + `tests/baselines/error_path_coverage.json` checked in; §C.1 priority list burn-down done (or per-endpoint "already covered" recorded); baseline only shrank; any non-RFC-7807 endpoint found was fixed to the dict shape and noted
- [ ] Task 4: map-cache unit tests pass (TTL 86400, key shape, fake-Redis round-trip); TF diff prepared for Tom (NOT applied); `aws-env-mgmt-ops-plan.md` §3 inventory rows added
- [ ] Task 5: tenant-creation path audit matrix in Completion Summary; mocked-Stripe locking test passes; README-seed-data §4 note added
- [ ] Task 6: scratch-DB proof executed clean (schema → 13-step seed → `seed_pricebook_starter.py --mode seed` → inspect → drop); §7.6 runbook + standing-rule line updated
- [ ] Task 7: `admin-tools/check_image_hygiene.sh` executable + exercised (or dry-checked); §19.7 references the script; `frontend/.dockerignore` `.env*` coverage verified/fixed
- [ ] Task 8: `dev-docs/devops/troubleshooting-runbook.md` created with all 10 bounded sections
- [ ] Task 9: `aws-env-mgmt-ops-plan.md` §9 Test Suite Trigger Reference added
- [ ] All DB-touching test helpers are sync `def` — no `async def` on the blocking `Session` (rules §21)
- [ ] All new API error assertions follow RFC 7807 Problem Details shape
- [ ] All new test files use `pytestmark` with domain marker + `pytest.mark.unit`
- [ ] No module-level `TestClient` in any test file
- [ ] All new tests use `test_tenant`/`test_user`/domain fixtures (no hardcoded UUIDs); assertions scoped by inserted IDs
- [ ] `python generate_app_import_map.py tests > app_model_imports.md` run (new test files)
- [ ] `export_openapi_json.py` / `generate_db_model_map.py` / `schema_manager.py` confirmed N/A (no endpoint/model/schema changes)
- [ ] `ruff check --fix && ruff format` run **on changed files only** — zero remaining issues in those files (including pre-existing), no unjustified `# noqa` (rules §23)
- [ ] **Phase 1**: All unit tests pass (`pytest -m unit`) — zero failures including any pre-existing
- [ ] **Phase 2**: Full suite (vendor-deselected) passes — `pytest -m "not integration and not requires_telnyx and not requires_stripe and not requires_sendgrid and not requires_redis and not e2e"` — zero failures, warning-clean; vendor inclusion call as stated above (none run)
- [ ] Final test count (before → after) documented
- [ ] Completion Summary filled in at this prompt doc's ending `## Appendix — Completion Summary` (ADR-0017 — never the launch plan). Include: the handoff note that no OpenAPI regen / `pnpm sync-api-types` was needed; a "Findings for 1B/1C" subsection (anything FE-relevant, e.g. endpoints whose error shape you had to fix); the recommendation that the Architect register `troubleshooting-runbook.md` in `pilot-docs-list.md` at close
- [ ] Source spec task headers: none outside the launch plan are closed by this batch (launch-plan + registry flips happen at Architect close)

---

## Completion Summary

After all Definition of Done items are complete, fill in the **Completion Summary** in the appendix at the end of THIS prompt doc using the format below (ADR-0017). The Architect updates the launch plan status-only on close — never write summaries into the launch plan.

```markdown
### TEST-UPLIFT-1A — Mechanical Error-Coverage (Python Track) + Ops Guards: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot Python Engineer
**Baseline**: X passed, Y failed
**Final**: X+N passed, Y failed (+N new tests)

#### What Was Accomplished

- [Celery guard: proof-of-bug failure output → fix → pass]
- [Host-guard IP spelling]
- [Ratchet: baseline size at generation → size after burn-down; endpoints closed; any endpoint error-shape fixes]
- [Maps cache: tests + TF diff status + inventory rows]
- [G3: audit matrix result]
- [Seed proof: scratch-DB run result]
- [Image hygiene: script + .dockerignore findings]
- [Runbook + test-trigger docs]

#### Tenant-Creation Path Audit (Task 5)

| Path | Creates tenant? | stripe_customer_id behavior |
|---|---|---|
| Signup wizard (`tenant_signup.py`) | Yes | Created post-wizard when NULL ✓ |
| Invite-landing Lambda Path 2 | No (attaches to existing) | N/A — owner's tenant already has one |
| Seed scripts | Yes (dev/qa) | Intentionally NULL — documented |
| [any other site found] | … | … |

#### Findings for 1B (React) / 1C (RN)

- [FE-relevant discoveries: endpoints re-shaped to RFC 7807, error-contract notes]

#### Files Changed / Created

| File | Action |
|---|---|
| `backend/core/celery_app.py` | Updated — register `tasks.tenant_site_emails` |
| … | … |

#### Tests Added

| Test File | Domain | Tests | All Pass |
|---|---|---|---|
| `tests/domains/platform_infrastructure/test_celery_registration.py` | `domain_platform_infrastructure` | N | ✅ |
| … | … | … | … |
```

---

## After This Task — Next Step

1. Confirm the DoD is fully checked and the Completion Summary appendix is filled in.
2. Commit your work on the batch branch; leave the Terraform change visibly staged/flagged for Tom (do not apply).
3. Notify Tom + the Architect: **TEST-UPLIFT-1A complete**. The Architect then (a) flips the launch-plan rows (Ord 18 → ✅; §7 gate note), (b) registers the design/prompt/runbook docs in `pilot-docs-list.md`, (c) designs **TEST-UPLIFT-1B** (React: FE error-rendering audit + MSW error-shape fidelity) using your "Findings for 1B/1C" subsection as input. **No `pnpm sync-api-types` handoff is required** — zero endpoint changes (design §D).

---

## Appendix — Completion Summary

### TEST-UPLIFT-1A — Mechanical Error-Coverage (Python Track) + Ops Guards: Completion Summary

**Completed**: 2026-08-27
**Mode**: Pilot Python Engineer
**Baseline**: 4645 passed, 2 failed (pre-existing SES test stale-path — fixed in pre-work)
**Final**: 4662 passed, 0 failed (+17 new tests; +2 pre-existing fixed)

#### What Was Accomplished

- **Celery guard**: Guard test failed before the import fix (reported `tasks.tenant_site_emails` missing — proof the bug is real), passes after. `"tasks.tenant_site_emails"` registered in `celery_app.py`.
- **Host-guard IP spelling**: `127.0.0.1:5433` accepted for prod; `:5432/pilot_dev` on the IP spelling still refused (fail-closed). 2 new tests in `test_seed_env_profiles.py`.
- **Ratchet**: Baseline generated at 96 uncovered endpoints → burned down to 93 (3 endpoints closed). 2 non-RFC-7807 endpoints found and fixed: `_send_invoice_impl` (invoices.py — plain string → RFC 7807 dict) and `advance_wizard_step` (tenant_signup.py — plain string → RFC 7807 dict). Ratchet meta-test + baseline checked in at `tests/baselines/error_path_coverage.json`.
- **Maps cache**: 9 unit tests pass (TTL 86400, key shape, fake-Redis round-trip, miss→populate→hit). TF diff prepared in `compute/main.tf` (api + worker containers — NOT applied, staged for Tom). Env-var inventory rows added to `aws-env-mgmt-ops-plan.md` §3.2.
- **G3**: Audit matrix below; mocked-Stripe locking test passes (`test_cb5_step4_stripe_creation.py` — `TestG3FoundersBillingResidualVerify`). README-seed-data §4 note added.
- **Seed proof**: Scratch-DB proof executed clean (schema → 13-step seed → `seed_pricebook_starter.py --mode seed` → 13 items, 0 errors → inspect → drop). §7.6 runbook + standing rule updated.
- **Image hygiene**: `admin-tools/check_image_hygiene.sh` created + exercised. Initial run caught stale local `pilot-celery_worker:latest` / `pilot-celery_beat:latest` (May 19 builds) with `/app/.env` baked in. Tom rebuilt + deployed to prod (ECR) 2026-08-27 — all 4 ECR images (api, worker, beat, web) now pass clean. §19.7 updated with script as canonical check. Both `.dockerignore` files verified (exclude `.env*`).
- **Runbook + test-trigger docs**: `troubleshooting-runbook.md` created (10 bounded sections). `aws-env-mgmt-ops-plan.md` §9 Test Suite Trigger Reference added.

#### Tenant-Creation Path Audit (Task 5)

| Path | Creates tenant? | stripe_customer_id behavior |
|---|---|---|
| Signup wizard (`tenant_signup.py`) | Yes | Created post-wizard when NULL ✓ (lines 494–519) |
| Lambda Path 2 (`post_confirmation/handler.py`) | No (attaches to existing) | N/A — owner's tenant already has one |
| Lambda Path 3 (`post_confirmation/handler.py`) | Yes (placeholder name) | NULL — never traverses wizard until step4 (then created) |
| `api/routes/auth.py` (legacy) | Yes (`Tenant(name=...)`) | NULL — legacy route, no Stripe creation |
| Seed scripts | Yes (dev/qa) | Intentionally NULL — documented (G3 verified) |

#### Findings for 1B (React) / 1C (RN)

- **`POST /api/v1/invoices/{invoice_id}/send` 404**: error shape was plain string `"Invoice not found"` — fixed to RFC 7807 dict. FE error-handling for this endpoint should now parse `detail.title` / `detail.detail` (not a bare string).
- **`PUT /api/v1/signup/{tenant_id}/step2` 404**: error shape was plain string `"Signup record not found for this tenant"` — fixed to RFC 7807 dict. Same FE note.
- **`POST /api/v1/public/invoices/{signed_token}/confirm-payment` 401**: already RFC 7807 (no fix needed). FE public invoice page should handle the `invalid-link` type.
- **Maps cache**: `MAP_CACHE_ENABLED` is OFF by default and absent from prod TF — the TF diff is staged but NOT applied. FE drive-time ETA features will see cache misses until Tom applies the TF diff.
- **Image hygiene**: The initial run caught `pilot-celery_worker:latest` and `pilot-celery_beat:latest` (local tags, May 19 builds) with `/app/.env` baked in. Tom rebuilt and deployed to prod (ECR) on 2026-08-27 — all 4 ECR images (api, worker, beat, web) now pass clean. The local stale tags still show the violation (they point at old May 19 image IDs); re-pulling from ECR or rebuilding locally will update them. Prod is clean.

#### Files Changed / Created

| File | Action |
|---|---|
| `backend/core/celery_app.py` | Updated — register `tasks.tenant_site_emails` |
| `backend/migrations/scripts/_env_profiles.py` | Updated — add `127.0.0.1:5433` to prod allowed_db_host_patterns |
| `backend/api/routes/invoices.py` | Updated — RFC 7807 fix for `_send_invoice_impl` 404 + ruff fixes (unused var, EN DASH) |
| `backend/services/tenant_signup.py` | Updated — RFC 7807 fix for `advance_wizard_step` 404 |
| `backend/tests/batch_b17/test_find145_149_151_155_162_166_138_170.py` | Updated — fix stale doc path + ruff EN DASH fixes |
| `backend/tests/domains/platform_infrastructure/test_celery_registration.py` | Created — Celery registration guard |
| `backend/tests/domains/platform_infrastructure/test_seed_env_profiles.py` | Updated — 2 new IP-spelling tests |
| `backend/tests/domains/platform_infrastructure/test_error_path_coverage.py` | Created — ratchet meta-test |
| `backend/tests/baselines/error_path_coverage.json` | Created — ratchet baseline (93 entries) |
| `backend/tests/domains/invoicing_billing/test_test_uplift_1a_invoice_error_paths.py` | Created — 2 burn-down tests |
| `backend/tests/domains/identity_access/test_test_uplift_1a_signup_error_paths.py` | Created — 1 burn-down test |
| `backend/tests/domains/identity_access/test_cb5_step4_stripe_creation.py` | Updated — G3 locking test |
| `backend/tests/domains/scheduling_dispatch/test_map_service_cache.py` | Created — 9 map cache tests |
| `backend/app_model_imports.md` | Regenerated — new test files |
| `infrastructure/terraform/modules/compute/main.tf` | Updated — MAP_CACHE env vars (api + worker) — staged, NOT applied |
| `dev-docs/devops/aws-env-mgmt-ops-plan.md` | Updated — §3.2 env-var rows + §9 Test Suite Trigger Reference |
| `dev-docs/devops/aws-ops-runbook.md` | Updated — §19.7 canonical script reference |
| `dev-docs/devops/troubleshooting-runbook.md` | Created — 10 bounded sections |
| `backend/README-seed-data.md` | Updated — §4 G3 note + §7.6 per-tenant seed proof + standing rule |
| `admin-tools/check_image_hygiene.sh` | Created — image hygiene script |

#### Tests Added

| Test File | Domain | Tests | All Pass |
|---|---|---|---|
| `tests/domains/platform_infrastructure/test_celery_registration.py` | `domain_platform_infrastructure` | 1 | ✅ |
| `tests/domains/platform_infrastructure/test_seed_env_profiles.py` | `domain_platform_infrastructure` | +2 | ✅ |
| `tests/domains/platform_infrastructure/test_error_path_coverage.py` | `domain_platform_infrastructure` | 1 | ✅ |
| `tests/domains/invoicing_billing/test_test_uplift_1a_invoice_error_paths.py` | `domain_invoicing_billing` | 2 | ✅ |
| `tests/domains/identity_access/test_test_uplift_1a_signup_error_paths.py` | `domain_identity_access` | 1 | ✅ |
| `tests/domains/identity_access/test_cb5_step4_stripe_creation.py` | `domain_identity_access` | +1 | ✅ |
| `tests/domains/scheduling_dispatch/test_map_service_cache.py` | `domain_scheduling_dispatch` | 9 | ✅ |

#### Handoff Note

- **Zero endpoint changes** (design §D) → `export_openapi_json.py` NOT run → `pnpm sync-api-types` NOT required for the 1B (React) handoff.
- **Terraform diff** is staged on the batch branch (NOT applied) — Tom/DevOps applies at the next deploy window.
- **Architect**: register `troubleshooting-runbook.md` in `pilot-docs-list.md` at close.
- **`pilot-celery_worker:latest`** local image has `/app/.env` baked in — needs a rebuild before next deploy (the `.dockerignore` fix is in place; the image is just stale).

#### Regeneration Steps Confirmed N/A

- `export_openapi_json.py` — zero endpoint changes ✅
- `generate_db_model_map.py app > db_models_map.md` — zero model changes ✅
- `schema_manager.py` — zero schema changes ✅
- Alembic — zero migrations ✅
- `generate_app_import_map.py tests > app_model_imports.md` — run ✅ (new test files)

#### Vendor-Suite Inclusion Call

This batch modifies **no** Telnyx/Stripe/SendGrid/Redis-covered runtime code. The new map-cache tests use a monkeypatched/faked Redis client (NOT `requires_redis`); the G3 signup test mocks Stripe (NOT `requires_stripe`). Therefore the vendor marker suites are **NOT run**.
