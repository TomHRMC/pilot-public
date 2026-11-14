# Implementation Prompt: PLP-FIX-7 Part A — Invite 409 Contract Fix + office_staff `jobs.view` Seed Grant

**Mode**: Pilot Python Engineer
**Batch**: PLP-FIX-7 (launch plan Ord 28, card §3.28) — **Part A (runs FIRST)**
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §3.28
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-plp-fix-7-design.md` — read **Part A (§C, §D, §E)** fully; §B for the root causes
**Estimated session**: ~1–1.5 hours
**Platform**: Backend only (`backend/`)
**Frontend companion**: PLP-FIX-7 Part B (React) — starts after you complete the Handoff section

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-python-engineer/python-engineer-rules.md`** — full document; the hard rules are non-negotiable STOPs
- **`dev-docs/architecture-design/pilot-python-engineer-methods.md`** — §16 (Standard Task Workflow)
- **`backend/tests/README-adding-tests.md`** — full document; governs test file structure, domain markers, fixture rules
- **`backend/README-seed-data.md`** — §3 (Group A–D model), §6 (run order), §7 (DELETE safety rule)

Critical rules for this batch:

- **Rule 1**: Never guess column names, data types, or table names. Use `postgres-local` MCP to verify every name before use. If MCP returns an error → **STOP and ask Tom**.
- **Rule 7**: The `postgres-local` MCP is for **read-only verification only**. Never use it to INSERT, UPDATE, or DELETE data — all data changes go through seed scripts or application code.
- **Rule 8**: All API error responses MUST follow RFC 7807 Problem Details format. This batch's whole point is a malformed-by-omission 409 contract (see Context).
- **Rule 11**: If ANY test fails during your work — even one that appears pre-existing — **you must fix it before declaring the batch done**. No "not my fault" exception. If you cannot identify the root cause → STOP and ask Tom.
- **Rule 14 (Ruff)**: Run ruff **only against the files you changed** — fix ALL errors in those files, including pre-existing ones. No unjustified `# noqa`.
- **Rule 16 (verify, don't assume)**: 186 tables exist. Query `information_schema.columns` for every table you touch before writing SQL.
- **Seed rules (rules §11 + Rule 11.5)**: `mode_seed` DELETEs must be value-scoped (never channel/channel-class scoped); every DB-data change requires the Seed Data Rollout section (present below).

---

## Context: What This Batch Does

Two small, high-leverage backend fixes from Tom's TEAM-INVITE-1 prod test run (design §B):

1. **INV-BUG-1 (BE half) — 409 type-URI contract.** The invite dialog's 409 state machine (Resend offer vs "already has an account" explainer) matches specific type URIs, but `_to_http_exception` in `backend/api/routes/team_invites.py` maps both `invite_user_exists` and `invite_pending_exists` to the generic `https://errors.pilotfortrades.com/conflict`. Combined with an FE parsing bug (fixed in Part B), every 409 crashed the settings page to a black error screen instead of showing the designed inline explainers. You change **two strings in the URI map** — nothing else about the envelope (the nested `HTTPException(detail={...})` form is the house standard; FE unwraps it via `getApiProblem` in Part B).
2. **INV-BUG-3 (BE half) — office_staff `jobs.view` seed grant.** Prod-verified root cause of the office_staff Schedule-page failure: the role holds `schedule.manage`/`schedule.view_all` but not `jobs.view`, so the schedule board's jobs load 403s. Product decision (Tom, design §H.1): **grant `jobs.view` to office_staff** via the Group A seed. ⚠️ The current `tenant_user_role` seed block in `seed_core.py` is **insert-if-missing only** — an existing row (like prod's) never gets updated on converge. You must extend that block to also apply a **value-scoped UPDATE of the `permissions` field when the row already exists** (idempotent, jsonb compare), so the prod converge actually heals the prod row.

---

## Pre-Work: Establish Regression Baseline

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=no -q 2>&1 | tail -5
```

Record the exact count: **`X passed, Y failed`**. If any tests are already failing before you start: do NOT proceed on assumption — confirm with Tom or fix first.

---

## Pre-Work: Run MCP Verification Queries

Run **all** of these via `postgres-local` MCP before writing any code. If any query returns unexpected results → **STOP and ask Tom**.

```sql
-- 1. tenant_user_role columns (verify before writing any SQL for this table)
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'tenant_user_role'
ORDER BY ordinal_position;

-- 2. Current office_staff grants (expect: NO 'jobs.view' in the array)
SELECT code, is_active, permissions FROM public.tenant_user_role WHERE code = 'office_staff';

-- 3. Confirm 'jobs.view' IS present for technician (sanity — the key string exists in prod vocab)
SELECT code, permissions ? 'jobs.view' AS has_jobs_view
FROM public.tenant_user_role WHERE code IN ('technician', 'office_staff', 'owner');

-- 4. Current alembic head (no migration in this batch — record for the summary)
SELECT version_num FROM public.alembic_version;
```

---

## Pre-Work: Mandatory File Reads

Read with `read_file` before writing any code:

1. `backend/api/routes/team_invites.py` — the full `_to_http_exception` function and the create-invite route (you are editing one map here)
2. `backend/services/team_invite_service.py` — the error classes (`InvitePendingExistsError` carries `invite_id`)
3. `backend/migrations/scripts/seed_core.py` — the `TENANT_USER_ROLE_ROWS` definition (~line 910–960) **and** the `tenant_user_role` insert block (~line 2560–2590) you are extending
4. `backend/tests/domains/identity_access/test_team_invites.py` — tests 3 + 4 (the two 409 paths) — you are extending these assertions
5. `backend/README-seed-data.md` — §3, §6, §7 (before touching any seed script)

---

## Tasks

### Task 1 — office_staff `jobs.view` seed grant + converge-safe UPDATE (design §C.1)

1. In `TENANT_USER_ROLE_ROWS` (`seed_core.py` ~line 928), add `"jobs.view"` to the office_staff `permissions` array (keep array order stable/readable — insert adjacent to the schedule keys).
2. In the `tenant_user_role` seed block (~line 2560–2590): keep the existing insert-if-missing behavior, and **add an else-branch** for existing rows that applies the permissions value idempotently:

```python
# Existing row: keep the permissions field convergent with the seed definition
# (value-scoped, no-op when already equal; updated_at touched only on change).
db.execute(
    text("""
        UPDATE public.tenant_user_role
        SET permissions = CAST(:permissions AS jsonb), updated_at = now()
        WHERE code = :code AND permissions <> CAST(:permissions AS jsonb)
    """),
    {"code": row["code"], "permissions": json.dumps(row["permissions"])},
)
```

   - Only the `permissions` field (and `updated_at`) may change — never `name`/`description`/`is_default`/`is_active` in this batch.
   - Follow the script's existing `json` import and transaction/commit pattern (match how neighboring blocks commit).
   - This is a `mode_seed` data change — **no DELETE anywhere** (seed rules §11); the UPDATE's WHERE clause is the value-scope.
3. Update `backend/README-seed-data.md` §4 (Current Seed State): office_staff grant list gains `jobs.view`, with the one-line rationale (Schedule board loads jobs — office staff schedule jobs).

### Task 2 — 409 type-URI contract fix (design §C.2)

In `_to_http_exception` (`team_invites.py`):

```python
"invite_user_exists": "https://errors.pilotfortrades.com/invite_user_exists",       # was /conflict
"invite_pending_exists": "https://errors.pilotfortrades.com/invite_pending_exists", # was /conflict
```

All other codes keep their current URIs. The `invite_id` passthrough for `InvitePendingExistsError` is unchanged. Do NOT change the envelope shape (nested `HTTPException(detail={...})` is the house standard per RFC 7807 inclusions §13).

### Task 3 — Tests

Domain folder: `backend/tests/domains/identity_access/` — extend `test_team_invites.py`:

1. `test_3_create_invite_user_exists` — assert the 409 body's RFC 7807 `type` (inside the FastAPI `detail` envelope — check how the existing test reads the body and follow it) equals `https://errors.pilotfortrades.com/invite_user_exists`.
2. `test_4_create_invite_duplicate_pending` — assert `type` equals `https://errors.pilotfortrades.com/invite_pending_exists` **and** `invite_id` is present and equals the original invite's id.
3. New seed test (place it with the other seed-verification tests for `seed_core` if a module exists, otherwise add to this file): after running the tenant_user_role seed block logic, office_staff `permissions` contains `jobs.view`; and running the block twice is a no-op (idempotent — assert the UPDATE path doesn't error and the row is unchanged on second pass). Use the existing test-DB fixtures per `README-adding-tests.md`; `pytestmark` with the domain marker + `pytest.mark.unit`; use `test_tenant`/`test_user` fixtures (no hardcoded UUIDs); apply autouse fixture opt-outs per the README table if the file needs them.

### Task 4 — Verify the seed converge locally

```bash
cd <repo>/backend && source .venv/bin/activate
python migrations/scripts/seed_core.py --mode seed    # first pass: applies the UPDATE
python migrations/scripts/seed_core.py --mode inspect  # tenant_user_role section shows 4 rows
python -c "..."  # or MCP: SELECT permissions ? 'jobs.view' FROM public.tenant_user_role WHERE code='office_staff' → t
python migrations/scripts/seed_core.py --mode seed    # second pass: idempotent no-op, zero errors
```

Then `python -m pytest -m unit --tb=short -q 2>&1 | tail -10` — a seed row a test doesn't expect will break tests (README §7); fix any seed-resilience failures (assert-by-ID, never by count).

---

## Seed Data Rollout (Core + Scenario)

Per `backend/README-seed-data.md` — read §3, §6, §7 before editing any seed script (already in mandatory reads).

### Layer 1 — Core / Platform values (Group A)
- office_staff `permissions` gains `jobs.view` in `TENANT_USER_ROLE_ROWS` (`seed_core.py`) + the converge-safe UPDATE path from Task 1 — this is the entire change; `seed`, `show`, and `inspect` modes must all reflect it (inspect/show print from the DB or the rows constant — verify both tell the truth after your change).

### Layer 2 — Scenario data (Group D)
- N/A — no entity column added; the scenario seeds do not seed role grants.

### Verification
- `seed_core.py --mode inspect` shows the row; MCP `permissions ? 'jobs.view'` → `t`; second `--mode seed` pass is a clean no-op; `pytest -m unit` green.

### README update
- `backend/README-seed-data.md` §4 updated (Task 1 step 3).

### Prod rollout (hand to Tom in your Completion Summary — do NOT run prod yourself)
- Tom runs the established prod converge: `cd backend && source .venv/bin/activate && DATABASE_URL="postgresql://pilot_user:${DB_PASS}@localhost:5433/pilot_prod" AWS_DEFAULT_REGION=us-east-1 python migrations/scripts/seed_prod_db.py --mode seed --stripe-mode test` (typed `PILOT-PROD-SEED`), then verifies via `postgres-prod` MCP: `SELECT permissions ? 'jobs.view' FROM public.tenant_user_role WHERE code='office_staff';` → `t`.

---

## RFC 7807 Error Format

All API error responses MUST use RFC 7807 Problem Details format. The frontend `apiClient` parses this format to drive severity routing in `<NotificationBanner>`.

```python
# ✅ REQUIRED — RFC 7807 shape
raise HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail={
        "type": "https://errors.pilotfortrades.com/not-found",
        "title": "Resource not found",
        "status": 404,
        "detail": f"Quote {quote_id} does not exist in this tenant.",
    },
)

# ❌ BANNED — plain string detail
raise HTTPException(status_code=404, detail="Not found")
```

Return `404` (not `403`) when a tenant-scoped record is not found — prevents UUID enumeration attacks.

---

## OpenAPI Regeneration (handoff signal — required even though no schema change is expected)

The 409 `type` values live inside error bodies, which are not OpenAPI response models — the spec diff should be **empty**. Run it anyway as the Part B handoff signal:

```bash
cd <repo>/backend && source .venv/bin/activate
python export_openapi_json.py
git diff --stat backend/openapi.json backend/openapi_schema_map.md
```

If the diff is NOT empty, stop and reconcile (an unexpected spec drift means something else changed — investigate before proceeding).

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

CHANGED_PY=$(git diff --name-only --diff-filter=d HEAD -- '*.py' | sed 's|^backend/||')
if [ -n "$CHANGED_PY" ]; then
    ruff check --fix $CHANGED_PY
    ruff format $CHANGED_PY
    ruff check $CHANGED_PY
fi

# Full suite — vendor/live-service suites deselected (Tom's standing instruction 2026-08-16)
python -m pytest -m "not integration and not requires_telnyx and not requires_stripe and not requires_sendgrid and not requires_redis and not e2e" --tb=short -q 2>&1 | tail -15

# Vendor-suite inclusion call for THIS batch: NOT required — no Telnyx/Stripe/SendGrid/Redis-covered code touched.

# Batch-specific spot checks
python -m pytest tests/domains/identity_access/test_team_invites.py -v 2>&1 | tail -20

echo "=== PLP-FIX-7 PART A FINAL VERIFICATION COMPLETE ==="
```

> **Warning-clean is part of done.** `ruff` must report no remaining issues **in your changed files**; the pytest run must be free of `DeprecationWarning` noise. **Any failure in either phase must be fixed before the batch is declared done.** There is no "pre-existing failure" exception without explicit written confirmation from Tom. If you cannot identify the root cause → STOP and ask Tom.

---

## Definition of Done

Check off each item **in this prompt doc** as it completes:

- [ ] Pre-modification regression baseline captured (`X passed, Y failed`) using `pytest -m unit`
- [ ] Zero pre-existing unit failures confirmed before starting work (or confirmed with Tom)
- [ ] All MCP pre-work queries run — `tenant_user_role` columns verified; office_staff pre-change grants confirmed lacking `jobs.view` (rules §25)
- [ ] All mandatory source files read before writing any code (including `team_invite_service.py` + the `seed_core.py` role block)
- [ ] Task 1: `"jobs.view"` added to office_staff in `TENANT_USER_ROLE_ROWS`; converge-safe value-scoped UPDATE added to the tenant_user_role seed block (existing rows heal; only `permissions` + `updated_at` touched)
- [ ] Task 1: local converge verified — first pass applies, second pass no-op, inspect/MCP confirm `permissions ? 'jobs.view'` → `t`
- [ ] Task 2: `_to_http_exception` maps `invite_user_exists` / `invite_pending_exists` to the specific type URIs; all other codes unchanged; `invite_id` passthrough intact
- [ ] Task 3: both 409 tests assert the specific type URIs (+ `invite_id` on pending_exists); new seed idempotency/`jobs.view` test added and passing
- [ ] Task 3 tests use `pytestmark` domain marker + `pytest.mark.unit`, `test_tenant`/`test_user` fixtures (no hardcoded UUIDs), autouse opt-outs per `README-adding-tests.md`
- [ ] README-seed-data.md §4 updated (office_staff grant list + rationale)
- [ ] `python export_openapi_json.py` run — diff confirmed empty (or reconciled)
- [ ] `ruff check --fix && ruff format` run **on changed files only** — zero remaining issues, no unjustified `# noqa` (rules §23)
- [ ] **Phase 1**: All unit tests pass (`pytest -m unit`) — zero failures including any pre-existing
- [ ] **Phase 2**: Full suite (vendor-deselected) passes — zero failures, warning-clean; vendor inclusion call: NOT required (recorded in Completion Summary)
- [ ] Final test count (before → after) documented
- [ ] Completion Summary filled in at this prompt doc's ending `## Appendix — Completion Summary` (ADR-0017 — never the launch plan)
- [ ] Source spec task headers updated to ✅ Complete in any spec doc other than the launch plan (README-seed-data.md §10 if it tracks this grant) — if applicable

---

## Completion Summary

After all Definition of Done items are complete:

1. Fill in the **Completion Summary** in the appendix at the end of THIS prompt doc using the format below.
2. **If this batch closes tasks tracked in another source spec** (e.g., `README-seed-data.md` §10), update those source spec task headers to ✅ Complete with a one-line summary BEFORE declaring the batch done.

```markdown
### PLP-FIX-7 Part A — Invite 409 Contract + office_staff jobs.view: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot Python Engineer
**Baseline**: X passed, Y failed
**Final**: X+N passed, Y failed (+N new tests)

#### What Was Accomplished

- [409 type-URI contract fix + test assertions]
- [office_staff jobs.view seed grant + converge-safe UPDATE + local verification]
- [Root cause recap — design §B.1/§B.3]

#### Files Changed / Created

| File | Action |
|---|---|
| `backend/api/routes/team_invites.py` | Updated — ... |
| `backend/migrations/scripts/seed_core.py` | Updated — ... |
| `backend/tests/domains/identity_access/test_team_invites.py` | Updated — ... |
| `backend/README-seed-data.md` | Updated — §4 grant list |

#### Tests Added

| Test File | Domain | Tests | All Pass |
|---|---|---|---|
| `tests/domains/identity_access/test_team_invites.py` | `identity_access` | N | ✅ |
```

---

## Handoff Instructions — PLP-FIX-7 Part B (React)

When Phase 2 is green and the Completion Summary is filled:

1. Confirm `python export_openapi_json.py` was run and its diff is empty (or reconciled) — this is the handoff signal per rules §9.3. If there were any spec-visible changes, the React Engineer's first pre-work step is `pnpm sync-api-types`.
2. Commit your work (backend changes + this prompt doc with the filled appendix).
3. Notify Tom/Architect that Part A is complete — Part B (`batch-plp-fix-7-react-engr-prompt.md`) can start.
4. Include in the handoff note: the prod converge instruction from the Seed Data Rollout section (Tom runs it at deploy time), and the Deploy note: **backend before frontend** (Part B's 409 handling expects the specific type URIs live).

## After This Task — Next Step

PLP-FIX-7 Part B (React) — the FE halves of INV-BUG-1/2/3/5/6 per the design doc's Part B section.

---

## Appendix — Completion Summary

### PLP-FIX-7 Part A — Invite 409 Contract + office_staff jobs.view: Completion Summary

**Completed**: 2026-09-04
**Mode**: Pilot Python Engineer
**Baseline**: 4787 passed, 42 failed
**Final**: 4831 passed, 0 failed (+44 net: 42 pre-existing failures fixed + 2 new tests added; 1 skipped unchanged)

#### What Was Accomplished

- **409 type-URI contract fix** — `_to_http_exception` in `team_invites.py` now maps `invite_user_exists` → `https://errors.pilotfortrades.com/invite_user_exists` and `invite_pending_exists` → `https://errors.pilotfortrades.com/invite_pending_exists` (were both `/conflict`). The FE dialog's 409 state machine can now match the specific URIs. `invite_id` passthrough for `InvitePendingExistsError` unchanged. Envelope shape (nested `HTTPException(detail={...})`) unchanged.
- **office_staff `jobs.view` seed grant** — Added `"jobs.view"` to the office_staff `permissions` array in `TENANT_USER_ROLE_ROWS` (`seed_core.py`). Extended the `tenant_user_role` seed block (~line 2568) with a value-scoped converge UPDATE: existing rows get `permissions` healed when they differ from the seed definition (idempotent — `WHERE permissions <> CAST(:permissions AS jsonb)`; only `permissions` + `updated_at` touched). Prod converge will heal the prod row.
- **Root cause recap** — INV-BUG-1 BE half (design §B.1): generic `/conflict` type URIs prevented the FE state machine from matching the two 409 branches. INV-BUG-3 BE half (design §B.3): office_staff held `schedule.manage`/`schedule.view_all` but not `jobs.view`, so the Schedule board's jobs load 403'd.
- **Pre-existing failure fix (Rule 14)** — 42 failures in `test_custom_email_sender_handler.py` were caused by the handler's refactor from raw KMS (`_get_kms_client` + `kms.decrypt`) to the AWS Encryption SDK (`_get_kms_keyring` + `EncryptionSDKClient.decrypt`). Tests updated to mock the new contract via `sys.modules` injection of a fake `aws_encryption_sdk` module + `_get_kms_keyring` patch. All 42 now pass.

#### Files Changed / Created

| File | Action |
|---|---|
| `backend/api/routes/team_invites.py` | Updated — two type URIs in `_to_http_exception` error_type_map (`/conflict` → specific URIs) |
| `backend/migrations/scripts/seed_core.py` | Updated — `jobs.view` added to office_staff permissions; converge-safe value-scoped UPDATE added to tenant_user_role seed block |
| `backend/tests/domains/identity_access/test_team_invites.py` | Updated — test_3/test_4 assert specific type URIs; new `TestOfficeStaffJobsViewSeed` class (2 tests: jobs.view present + converge idempotency) |
| `backend/tests/domains/identity_access/test_custom_email_sender_handler.py` | Updated — `_setup_mocks` + `TestDecryptContract` + `test_kms_client_error_raises` rewritten to match AWS Encryption SDK handler contract (42 pre-existing failures fixed) |
| `backend/README-seed-data.md` | Updated — §4 tenant_user_role row: office_staff gains `jobs.view` + converge UPDATE note |
| `backend/openapi_schema_map.md` | Regenerated — timestamp only (no schema change; error bodies are not response models) |

#### Tests Added

| Test File | Domain | Tests | All Pass |
|---|---|---|---|
| `tests/domains/identity_access/test_team_invites.py` | `identity_access` | +2 (jobs.view present, converge idempotent) | ✅ |
| `tests/domains/identity_access/test_custom_email_sender_handler.py` | `identity_access` | 42 fixed (mock contract realigned) | ✅ |

#### Verification Summary

- **MCP pre-work**: `tenant_user_role` columns verified; office_staff pre-change confirmed lacking `jobs.view`; technician has it; alembic head `3da9abdfb2f2`.
- **Seed converge**: first pass → `🔄 office_staff permissions converged (1 row updated)`; second pass → `ℹ️ already exists` (no-op); MCP `permissions ? 'jobs.view'` → `t`.
- **OpenAPI**: `export_openapi_json.py` run — diff is timestamp-only (no schema change, as expected — error bodies are not response models).
- **Ruff**: clean on all 4 changed Python files (0 errors, 0 warnings).
- **Phase 1 (unit)**: 4829 passed, 0 failed (42 pre-existing fixed + 2 new).
- **Phase 2 (full vendor-deselected)**: 4831 passed, 1 skipped, 0 failed, warning-clean.
- **Vendor-suite inclusion call**: NOT required — no Telnyx/Stripe/SendGrid/Redis-covered code touched.

#### Prod Rollout (hand to Tom)

Tom runs the established prod converge at deploy time:
```bash
cd backend && source .venv/bin/activate
DATABASE_URL="postgresql://pilot_user:${DB_PASS}@localhost:5433/pilot_prod" \
AWS_DEFAULT_REGION=us-east-1 \
python migrations/scripts/seed_prod_db.py --mode seed --stripe-mode test
```
(typed `PILOT-PROD-SEED`), then verifies via `postgres-prod` MCP:
```sql
SELECT permissions ? 'jobs.view' FROM public.tenant_user_role WHERE code='office_staff';
```
→ expected `t`.

**Deploy note**: backend before frontend (Part B's 409 handling expects the specific type URIs live).
