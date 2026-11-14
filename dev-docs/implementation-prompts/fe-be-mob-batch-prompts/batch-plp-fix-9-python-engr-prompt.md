# Implementation Prompt: PLP-FIX-9 Part A — Role-Grant Seed Changes (office_staff Comms + Self-Service Security Codes)

**Mode**: Pilot Python Engineer
**Batch**: PLP-FIX-9 (Part A of 2 — runs FIRST)
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §3.30 (Ord 30)
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-plp-fix-9-design.md`
**Estimated session**: ~1 hour
**Platform**: Backend only (`backend/`)
**Frontend companion**: PLP-FIX-9 Part B (React) — gated on this batch's converge

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-python-engineer/python-engineer-rules.md`** — full document; the 25 hard rules are non-negotiable STOPs
- **`dev-docs/architecture-design/pilot-python-engineer-methods.md`** — §16 (Standard Task Workflow)
- **`backend/tests/README-adding-tests.md`** — full document; governs all test file structure, domain markers, and fixture rules
- **`backend/README-seed-data.md`** — §3 (Group A–D model), §4 (Current Seed State), §6 (run order), §7 (DELETE safety rule)
- **The design doc** — every §G decision is binding; do not re-litigate

Critical rules for this batch:

- **Rule 1**: Never guess column names, data types, or table names. Use `postgres-local` MCP to verify every name before use. If MCP returns an error → **STOP and ask Tom**.
- **Rule 7**: The `postgres-local` MCP is for **read-only verification only**. Never use it to INSERT, UPDATE, or DELETE — all data changes go through seed scripts or application code.
- **Rule 11**: If ANY test fails during your work — even one that appears pre-existing — **you must fix it before declaring the batch done**. If you cannot identify the root cause → STOP and ask Tom.
- **Rule 14 (Ruff)**: Run ruff **only against the files you changed** — `git diff --name-only --diff-filter=d HEAD -- '*.py' | sed 's|^backend/||'`. Fix ALL errors in those files, including pre-existing ones. No unjustified `# noqa`.
- **Rule 16 (verify, don't assume)**: 186 tables exist. Query `information_schema.columns` for every table you touch this session before writing SQL.
- **Seed safety (architect Rule 11.1 + README §7)**: `mode_seed` DELETEs must be value-scoped. **This batch performs zero DELETEs** — the `tenant_user_role` seed block converges via a permissions-only UPDATE that is already in place (FIX-7). Do not add DELETEs, and do not touch the converge UPDATE logic itself — your change is data-only (the arrays).
- **Converge discipline (FIX-7 §C.1, standing)**: in the `tenant_user_role` seed block, only `permissions` + `updated_at` may ever change on existing rows — never `name`/`description`/`is_default`/`is_active`. This is already encoded; do not weaken it.

---

## Pre-Work: Establish Regression Baseline

Before touching any file, capture the current **unit-only** test baseline:

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=no -q 2>&1 | tail -5
```

Record the exact count. **Expected: `4836 passed, 1 skipped`** (post-PLP-FIX-8 state).

> **If any tests are already failing before you start**: Do NOT treat them as "pre-existing" and proceed anyway. Either confirm with Tom that the failure is known/accepted, or fix it before touching any batch files. You may NOT start implementation work while tests are in an unexplained failed state.

---

## Pre-Work: Run MCP Verification Queries

Run **all** of these via `postgres-local` MCP before writing any code. If any query returns unexpected results → **STOP and ask Tom**.

> **MCP Usage Rule**: `postgres-local` is read-only verification. Never INSERT/UPDATE/DELETE via MCP. If a query fails → STOP and ask Tom. (`postgres-prod` exists but is NOT used in this batch — prod verification is Tom's post-deploy step via the converge.)

```sql
-- 1. Confirm tenant_user_role columns (expect exactly these 10; code is the natural PK — no surrogate id)
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'tenant_user_role'
ORDER BY ordinal_position;
-- Expect: created_at, updated_at, created_by, updated_by, code, name, description, permissions (jsonb), is_default, is_active

-- 2. Dump all four role rows (pre-change state — confirm office_staff already has jobs.view from the FIX-7 converge, and NO role holds communications.*, mfa.enroll_self, account.session.*, or help_chat.*)
SELECT code, permissions FROM public.tenant_user_role ORDER BY code;

-- 3. Confirm the specific new codes are absent everywhere pre-change (expect 0 rows)
SELECT code, jsonb_array_elements_text(permissions) AS perm
FROM public.tenant_user_role
WHERE permissions ?| ARRAY['communications.view','communications.send','mfa.enroll_self','account.session.view_own','account.session.revoke_own','help_chat.delete_own_history'];

-- 4. Confirm alembic head is unchanged (this batch has NO migration)
SELECT version_num FROM public.alembic_version;
-- Expect: 3da9abdfb2f2
```

---

## Pre-Work: Read These Source Files

Use `read_file` on each of these before writing any code:

```
backend/migrations/scripts/seed_core.py            ← lines ~905-985 (TENANT_USER_ROLE_ROWS arrays) AND ~2560-2615 (the tenant_user_role seed block with the FIX-7 converge UPDATE) — your edit is arrays-only
backend/tests/domains/identity_access/test_team_invites.py  ← the TestOfficeStaffJobsViewSeed class (FIX-7) — the exact test pattern you will mirror (grant-present + converge-idempotency tests)
backend/README-seed-data.md                        ← §4 Current Seed State — find the tenant_user_role row you must update
backend/tests/conftest.py                          ← db_session / client fixtures (your tests are seed-definition + DB-converge tests, not endpoint tests)
```

> The `api/schemas/` layer is NOT touched in this batch (no endpoint or payload changes).

Also run:

```bash
grep -n "TENANT_USER_ROLE_ROWS" backend/migrations/scripts/seed_core.py | head -5
grep -rn "communications.view\|communications.send\|communications.manage" backend/api/routes/ --include="*.py" | head -12
```

The second grep re-proves the backend vocabulary you are granting (design §G.2 — the FE `comms.send` key is phantom; the BE gates are `communications.*`).

---

## Background / Context

The 2026-09-05 prod verification run (PLP-FIX-7/8) surfaced two grant-layer defects this batch fixes (design §B.1):

1. **INV-D-5 (Tom-ruled widen)**: office_staff holds zero `communications.*` grants, so the Comms module is unusable for the role that most needs it. Backend routes enforce `communications.view` (×3), `communications.send` (×4), `communications.manage` (×2) — MCP-verified.
2. **INV-BUG-8**: every self-scoped Security-page endpoint is gated on codes **no non-owner role holds**: `mfa.enroll_self` (×5 endpoints — status, enroll-start/confirm, delete method, recovery codes), `account.session.view_own`, `account.session.revoke_own`, `help_chat.delete_own_history`. Result: any non-owner opening Settings → My Account → Security gets "We couldn't load your MFA methods" (403). PRD §3.2 (line 349) mandates self-service MFA enrollment for users.

**The fix is seed-data-only**: edit four `permissions` arrays in `TENANT_USER_ROLE_ROWS`. The FIX-7 converge UPDATE (permissions-only, idempotent) is already in the seed block — it heals local + prod rows on the next converge run. **No Alembic migration. No OpenAPI change. No model change.**

Exact array edits (design §B.1 — binding):

| Role | Add to `permissions` |
|---|---|
| `office_staff` | `communications.view`, `communications.send`, `mfa.enroll_self`, `account.session.view_own`, `account.session.revoke_own`, `help_chat.delete_own_history` |
| `technician` | `mfa.enroll_self`, `account.session.view_own`, `account.session.revoke_own`, `help_chat.delete_own_history` |
| `accountant` | `mfa.enroll_self`, `account.session.view_own`, `account.session.revoke_own`, `help_chat.delete_own_history` |
| `owner` | **no change** (`*` wildcard already matches all) |

Do NOT add `communications.manage` anywhere (design §G.1 — thread lifecycle admin stays owner-only).

---

## Task 1 — Edit the four role arrays in `TENANT_USER_ROLE_ROWS`

**File**: `backend/migrations/scripts/seed_core.py` (arrays at ~lines 915-985)

**What to change**: append the §Background table's codes to the `office_staff`, `technician`, and `accountant` `permissions` lists. Keep array ordering tidy (append the new codes after the existing entries, grouped as in the design table — comms codes together, self-service codes together). Do not touch `owner`. Do not touch the seed-block converge logic (~lines 2562-2610) — it already does exactly the right thing.

**Intermediate verification**:

```bash
cd <repo>/backend && source .venv/bin/activate
ruff check --fix migrations/scripts/seed_core.py && ruff format migrations/scripts/seed_core.py && ruff check migrations/scripts/seed_core.py
```

---

## Task 2 — New test file: grant matrix + converge idempotency

**File**: `backend/tests/domains/identity_access/test_tenant_user_role_grants.py` (new)

Mirror the `TestOfficeStaffJobsViewSeed` pattern from FIX-7's `test_team_invites.py` (read it first). Required markers + structure:

```python
pytestmark = [
    pytest.mark.domain_identity_access,
    pytest.mark.unit,
]
```

Tests to write (6–8):

1. `test_office_staff_has_communications_grants` — the `office_staff` row in `TENANT_USER_ROLE_ROWS` (import the constant from the seed script) contains `communications.view` AND `communications.send`, and does NOT contain `communications.manage`.
2. `test_all_non_owner_roles_have_self_service_security_grants` — `office_staff`, `technician`, `accountant` each contain all four: `mfa.enroll_self`, `account.session.view_own`, `account.session.revoke_own`, `help_chat.delete_own_history`.
3. `test_owner_unchanged_wildcard` — owner still starts with `"*"` and gains none of the new literal codes (the wildcard matches them implicitly).
4. `test_converge_heals_db_rows` — using `db_session`: run the seed script's tenant_user_role block (or the full `seed_core.py --mode seed` equivalent used by the FIX-7 test) once; assert via SQL that each row's `permissions` now contains the new codes (scope assertions with `permissions ? 'communications.send'` style clauses per role code).
5. `test_converge_is_idempotent` — run the block a second time; assert the converge UPDATE affected 0 rows (second pass is a no-op — same proof shape as the FIX-7 idempotency test).
6. `test_only_permissions_and_updated_at_change` — converge must not alter `name`/`description`/`is_default`/`is_active` (FIX-7 §C.1 standing rule) — assert those columns are byte-identical before/after.

**Intermediate verification**: `python -m pytest tests/domains/identity_access/test_tenant_user_role_grants.py -v 2>&1 | tail -15` then `python -m pytest -m unit --tb=short -q 2>&1 | tail -5`.

---

## Task 3 — Local converge + MCP verify + README §4 update

1. Run the local converge **twice**:

```bash
cd <repo>/backend && source .venv/bin/activate
python migrations/scripts/seed_core.py --mode seed 2>&1 | grep -i "tenant_user_role"
python migrations/scripts/seed_core.py --mode seed 2>&1 | grep -i "tenant_user_role"
```

Expected: first pass prints `🔄 [tenant_user_role] '<role>' permissions converged (1 row updated)` for the three edited roles; second pass prints `ℹ️ … already exists` for all four.

2. MCP re-verify (`postgres-local`):

```sql
SELECT permissions ? 'communications.send' AS comms_send FROM public.tenant_user_role WHERE code='office_staff';      -- expect t
SELECT permissions ? 'mfa.enroll_self' AS mfa_self FROM public.tenant_user_role WHERE code='technician';            -- expect t
SELECT permissions ? 'mfa.enroll_self' AS mfa_self FROM public.tenant_user_role WHERE code='accountant';            -- expect t
SELECT permissions ? 'communications.manage' AS comms_manage FROM public.tenant_user_role WHERE code='office_staff'; -- expect f (deliberately excluded, design §G.1)
```

3. Update `backend/README-seed-data.md` §4 (Current Seed State) `tenant_user_role` row: office_staff now 19 perms (incl. `communications.view/send` + 4 self-service codes); technician 21 perms; accountant 9 perms (each incl. the 4 self-service codes); note the PLP-FIX-9 change with date.

4. `python migrations/scripts/seed_core.py --mode inspect` — confirm clean.

---

## Verification Checkpoints

- After Task 1: ruff clean on `seed_core.py`.
- After Task 2: new tests pass; `pytest -m unit` fully green (baseline 4836 + your new tests).
- After Task 3: converge idempotent locally; MCP post-change queries return expected `t`/`f`; README §4 updated.

---

## Regeneration Steps

- **OpenAPI**: run `python export_openapi_json.py` — **expect a timestamp-only diff** (seed-only batch; error bodies are not response models). Record the confirmation in your Completion Summary (this doubles as the Part B handoff signal that no `sync-api-types` delta exists).
- **db_models_map.md / app_model_imports.md**: model map N/A (no model changes). Run `python generate_app_import_map.py tests > app_model_imports.md` (new test file added).
- **schema_manager.py**: N/A (no schema change).

## Seed Data Rollout (Core + Scenario)

Per `backend/README-seed-data.md` — you already read §3/§4/§6/§7 in Pre-Work.

- **Layer 1 — Core/Platform values**: this batch **is** the Layer-1 change (Task 1 arrays + the pre-existing converge block). Nothing further.
- **Layer 2 — Scenario data**: N/A — no entity columns added; role grants are platform reference data (design §B.2).
- **Verification**: Task 3's inspect + `pytest -m unit` (a grant change can break tests that assert role permission sets — if any pre-existing test hard-codes the old arrays, update it to the new truth and note it in the Completion Summary).
- **README update**: Task 3 step 3.

---

## Final Verification

### Phase 1 — Unit Tests Only (run after each task group during development)

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=short -q 2>&1 | tail -10
```

All unit tests must pass before moving on. Fix any failure — including ones that appear caused by code outside this batch — before proceeding.

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

# Batch spot checks
python -m pytest tests/domains/identity_access/test_tenant_user_role_grants.py -v 2>&1 | tail -15

echo "=== PLP-FIX-9 PART A FINAL VERIFICATION COMPLETE ==="
```

**Vendor-suite inclusion call**: NOT required — this batch touches only a seed script + one new test file; no Telnyx/Stripe/SendGrid/Redis-covered code. State this call in your Completion Summary.

> Warning-clean is part of done: ruff reports zero remaining issues in changed files; pytest output free of new warnings.

---

## Definition of Done

Check off each item **in this prompt doc** as it completes:

- [ ] Pre-modification regression baseline captured (`4836 passed, 1 skipped` expected) using `pytest -m unit`
- [ ] Zero pre-existing unit failures confirmed before starting work (or confirmed with Tom)
- [ ] All 4 MCP pre-work queries run — columns match (code natural PK), role rows dumped, new codes confirmed absent, alembic head `3da9abdfb2f2` (every touched table verified, rules §25)
- [ ] All mandatory source files read (seed_core.py both regions, FIX-7 test pattern, README-seed §4, conftest)
- [ ] **Task 1**: the 4 role arrays edited per the design §B.1 table — office_staff +6 codes (incl. `communications.view/send`, NOT `.manage`); technician +4; accountant +4; owner untouched
- [ ] **Task 2**: `test_tenant_user_role_grants.py` created with `pytestmark` domain+unit markers; 6–8 tests incl. converge idempotency + only-permissions-updated_at-change guard
- [ ] **Task 3**: local converge run twice (heal → no-op); MCP post-change queries return expected `t`/`f`; README-seed-data §4 updated
- [ ] No DELETEs added anywhere; converge UPDATE logic untouched (seed safety rule)
- [ ] All new tests use `db_session` correctly; no module-level `TestClient`; no hardcoded UUIDs; assertions scoped by role code
- [ ] `python generate_app_import_map.py tests > app_model_imports.md` run
- [ ] `python export_openapi_json.py` run — timestamp-only diff confirmed and recorded
- [ ] `ruff check --fix && ruff format` run on changed files only — zero remaining issues, no unjustified `# noqa`
- [ ] **Phase 1**: All unit tests pass — zero failures including any pre-existing
- [ ] **Phase 2**: Full suite (vendor-deselected) passes — zero failures, warning-clean; vendor-suite inclusion call recorded (expected: NOT required)
- [ ] Final test count (before → after) documented
- [ ] Completion Summary filled in at this prompt doc's ending `## Appendix — Completion Summary` (ADR-0017 — never the launch plan)
- [ ] Source spec task headers updated (README-seed-data.md §4 row — included above)

---

## Completion Summary

After all Definition of Done items are complete:

1. Fill in the **Completion Summary** in the appendix at the end of THIS prompt doc using the format below.
2. Update `backend/README-seed-data.md` §4 (already Task 3 step 3) before declaring done.

```markdown
### PLP-FIX-9 Part A — Role-Grant Seed Changes: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot Python Engineer
**Baseline**: X passed, Y failed
**Final**: X+N passed, Y failed (+N new tests)

#### What Was Accomplished
- [array edits per role]
- [test file + what it proves]
- [converge + MCP verification results]

#### Files Changed / Created
| File | Action |
|---|---|

#### Tests Added
| Test File | Domain | Tests | All Pass |
|---|---|---|---|
```

---

## After This Task — Handoff to Part B (React)

This batch has **no OpenAPI delta** (seed-only), so the usual `pnpm sync-api-types` handoff signal is a timestamp-only confirmation — Part B still runs it per its Pre-Work (react-engr inclusions Rule 1.3) and expects no schema change.

Tell the React Engineer:
1. Part A is closed; the new grants are the **server truth** Part B's `ROLE_PERMISSION_MAP` mirror and MSW fixtures must match (office_staff: +`communications.view/send` +4 self-service codes; technician/accountant: +4 self-service codes; `communications.manage` deliberately absent).
2. Part B's MFA-page verification depends on the local converge having run (Task 3) — it has.

**Prod rollout note for Tom (include verbatim in your Completion Summary)**: at deploy time Tom runs the standard prod converge (`DATABASE_URL=... python migrations/scripts/seed_prod_db.py --mode seed --stripe-mode test`, typed `PILOT-PROD-SEED`), then verifies via `postgres-prod` MCP: `SELECT permissions ? 'communications.send' FROM public.tenant_user_role WHERE code='office_staff';` → `t` and `SELECT permissions ? 'mfa.enroll_self' FROM public.tenant_user_role WHERE code='technician';` → `t`. Deploy order: backend API image is unchanged (no code delta) — the converge is the only prod step, and it must land **before** the Part B web deploy (the web UI's comms nav + security pages key off the server-provided grants).

---

## Appendix — Completion Summary

### PLP-FIX-9 Part A — Role-Grant Seed Changes: Completion Summary

**Completed**: 2026-09-05
**Mode**: Pilot Python Engineer
**Baseline**: 4836 passed, 1 skipped
**Final**: 4843 passed, 1 skipped (+7 new tests)

#### What Was Accomplished
- **office_staff** permissions array: added `communications.view`, `communications.send` (INV-D-5 fix) + 4 self-service Security-page codes: `mfa.enroll_self`, `account.session.view_own`, `account.session.revoke_own`, `help_chat.delete_own_history` (INV-BUG-8 fix). Now 19 perms total. `communications.manage` deliberately excluded (design §G.1 — owner-only thread lifecycle admin).
- **technician** permissions array: added the 4 self-service Security-page codes. Now 21 perms total.
- **accountant** permissions array: added the 4 self-service Security-page codes. Now 9 perms total.
- **owner**: unchanged (`*` wildcard matches all new codes implicitly).
- New test file `test_tenant_user_role_grants.py` with 7 tests: 4 seed-definition (array) tests proving the grant matrix + 3 DB converge tests proving heal-once, idempotent no-op, and only-permissions+updated_at-change guard.
- Updated existing `test_team_invites.py::TestOfficeStaffJobsViewSeed` hardcoded office_staff array to match the new truth (6 new codes appended).
- Local converge run twice: first pass converged 3 roles (accountant, office_staff, technician); second pass no-op for all 4. MCP post-change verification confirmed: office_staff `communications.send`=t, `communications.manage`=f; technician/accountant `mfa.enroll_self`=t.
- `README-seed-data.md` §4 `tenant_user_role` row updated with PLP-FIX-9 change note and perm counts.

#### Files Changed / Created
| File | Action |
|---|---|
| `backend/migrations/scripts/seed_core.py` | Modified — 3 role arrays edited (office_staff +6, technician +4, accountant +4) |
| `backend/tests/domains/identity_access/test_tenant_user_role_grants.py` | Created — 7 tests (grant matrix + converge idempotency) |
| `backend/tests/domains/identity_access/test_team_invites.py` | Modified — updated hardcoded office_staff array in `TestOfficeStaffJobsViewSeed` to new truth |
| `backend/README-seed-data.md` | Modified — §4 `tenant_user_role` row updated with PLP-FIX-9 note |
| `backend/app_model_imports.md` | Regenerated — +1 line (new test file) |
| `backend/openapi_schema_map.md` | Regenerated — timestamp-only diff (seed-only batch, no API change) |
| `backend/openapi.json` | Regenerated — zero diff (timestamp-only, confirmed) |

#### Tests Added
| Test File | Domain | Tests | All Pass |
|---|---|---|---|
| `test_tenant_user_role_grants.py` | identity_access | 7 | ✅ |

#### Regeneration Confirmations
- **OpenAPI**: `python export_openapi_json.py` run — `openapi.json` has zero diff (timestamp-only, seed-only batch). `openapi_schema_map.md` has 1-line timestamp change. No `sync-api-types` delta exists for Part B.
- **app_model_imports.md**: `python generate_app_import_map.py tests > app_model_imports.md` run — +1 line (new test file).
- **db_models_map.md**: N/A (no model changes).
- **schema_manager.py**: N/A (no schema change).

#### Vendor-Suite Inclusion Call
**NOT required** — this batch touches only a seed script + one new test file + one existing test file. No Telnyx/Stripe/SendGrid/Redis-covered code was modified.

#### Ruff
Changed files (`seed_core.py`, `test_team_invites.py`, `test_tenant_user_role_grants.py`) — all pass `ruff check` with zero remaining issues, no `# noqa`.

#### Prod Rollout Note for Tom
At deploy time Tom runs the standard prod converge (`DATABASE_URL=... python migrations/scripts/seed_prod_db.py --mode seed --stripe-mode test`, typed `PILOT-PROD-SEED`), then verifies via `postgres-prod` MCP: `SELECT permissions ? 'communications.send' FROM public.tenant_user_role WHERE code='office_staff';` → `t` and `SELECT permissions ? 'mfa.enroll_self' FROM public.tenant_user_role WHERE code='technician';` → `t`. Deploy order: backend API image is unchanged (no code delta) — the converge is the only prod step, and it must land **before** the Part B web deploy (the web UI's comms nav + security pages key off the server-provided grants).

#### Handoff to Part B (React)
1. Part A is closed; the new grants are the **server truth** Part B's `ROLE_PERMISSION_MAP` mirror and MSW fixtures must match (office_staff: +`communications.view/send` +4 self-service codes; technician/accountant: +4 self-service codes; `communications.manage` deliberately absent).
2. Part B's MFA-page verification depends on the local converge having run (Task 3) — it has.
3. No OpenAPI delta — `pnpm sync-api-types` will produce no schema change.
