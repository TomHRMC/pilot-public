# Implementation Prompt: PLP-FIX-11 Part A — Accountant `schedule.view_all` Seed Grant (INV-BUG-18)

**Mode**: Pilot Python Engineer
**Batch**: PLP-FIX-11 (Part A of 2 — runs first; launch plan Ord 32, card §3.32)
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §3.32
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-plp-fix-11-design.md` — read fully (A–I); §G decisions are binding
**Estimated session**: ~1 hour
**Platform**: Backend only (`backend/`) — seed script + tests; **no migration, no endpoint changes**
**Frontend companion**: PLP-FIX-11 Part B (React) — mirrors the grant in the static map + MSW fixtures and gates the bare "Technicians" header

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-python-engineer/python-engineer-rules.md`** — full document; the 25 hard rules are non-negotiable STOPs
- **`dev-docs/architecture-design/pilot-python-engineer-methods.md`** — §16 (Standard Task Workflow)
- **`backend/tests/README-adding-tests.md`** — full document; governs test structure, domain markers, fixture rules
- **`backend/README-seed-data.md`** — §3 (Group A–D model), §6 (run order), §7 (DELETE safety rule)

Critical rules for this batch:

- **Rule 1/16**: Never guess column names. Verify `tenant_user_role` via `postgres-local` MCP before writing any SQL (queries below).
- **Rule 7**: MCP is **read-only** — the grant change ships ONLY through the `seed_core.py` edit; never hand-UPDATE the DB.
- **Rule 11**: If ANY test fails during your work — even one that appears pre-existing — fix it before declaring done. Root cause unidentifiable → STOP and ask Tom.
- **Rule 14 (Ruff)**: lint/format **changed files only** (`git diff --name-only HEAD -- '*.py'`).

---

## Design Decisions (Do Not Re-Litigate)

From Design Doc §G — these decisions are final:

| Decision | Outcome | Rationale |
|---|---|---|
| Mechanism | **Seed grant** `schedule.view_all` on the accountant role — NOT a route re-gate | Re-gating `scheduling.py` to `jobs.view` would expose assignments to technician too — wider than Tom's ruling (§G-Q1) |
| Side effect | **Accepted** — accountant gains Schedule nav + read-only dispatch board | Same read key by design; write affordances stay `schedule.manage`-gated (§G-Q2) |
| `schedule.manage` / `schedule.view_own` | **NOT granted** | Ruling is *view*; write stays owner/office_staff (§G-Q3/Q6) |
| 1E invariant test | **Update, don't preserve** — `test_accountant_has_no_schedule_permissions` reverses | Tom's 2026-09-06 ruling supersedes the 1E-era invariant (§G-Q4) |
| Converge mechanism | Existing `seed_core.py` UPDATE (lines 2587-2607) — no code change to the mechanism | Value-scoped, no-op when equal; permissions + updated_at only (PLP-FIX-7 §C.1) |

---

## Pre-Work: Establish Regression Baseline

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=no -q 2>&1 | tail -5
```

Record the exact counts. **Expected: `4848 passed, 1 skipped`** (post-PLP-FIX-10 state). Any pre-existing failure → confirm with Tom or fix first.

---

## Pre-Work: Run MCP Verification Queries

Run **all** of these via `postgres-local` MCP before writing any code. If any query returns unexpected results → **STOP and ask Tom**.

> **MCP Usage Rule**: `postgres-local` is **read-only verification only** — never INSERT/UPDATE/DELETE via MCP. `postgres-prod` exists but needs Tom's SSH tunnel — **not needed this batch** (the prod converge is Tom's post-batch step, design §B.7).

```sql
-- 1. Verify the table shape (Rule 25 — engineer safety net)
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'tenant_user_role'
ORDER BY ordinal_position;
-- expect: code (text PK), name, description, permissions (jsonb), is_default, is_active, created_at, updated_at

-- 2. Current accountant grants (pre-edit state — design §A dump must match)
SELECT code, permissions
FROM public.tenant_user_role
WHERE table_schema IS NOT NULL AND code = 'accountant';
-- expect: jsonb array containing "*.view" and NOT containing "schedule.view_all"

-- 3. office_staff reference (the grant's target shape — already holds both keys)
SELECT permissions ? 'schedule.view_all' AS has_view_all, permissions ? 'schedule.manage' AS has_manage
FROM public.tenant_user_role
WHERE code IN ('office_staff', 'accountant')
ORDER BY code;
-- expect: accountant f/f (pre-edit); office_staff t/t
```

---

## Pre-Work: Read These Source Files

Use `read_file` on each of these before writing any code:

1. `backend/migrations/scripts/seed_core.py` — `TENANT_USER_ROLE_ROWS` (lines 913-1007; the accountant dict at 914-932) **and** the converge block (lines 2579-2627) — you are editing the array only; the UPDATE mechanism already exists
2. `backend/tests/domains/identity_access/test_tenant_user_role_grants.py` — the FIX-9 grant-test home you extend (marker/fixture patterns, wildcard-expansion assertions)
3. `backend/tests/batch_1e/test_task_1a4_scheduling_role_permissions.py` — the invariant test you update (lines 99-107 assert zero `schedule.*` for accountant)
4. `dev-docs/architecture-design/batch-designs/batch-plp-fix-11-design.md` — full design (A–I)

Also run this grep to find every other test that asserts accountant's schedule access (any hit beyond the two files above gets the same ruling-reversal treatment):

```bash
grep -rn "accountant" backend/tests --include="*.py" -l | xargs grep -ln "schedule" 
grep -rn "schedule\.view_all\|schedule\.manage\|schedule\.view_own" backend/tests --include="*.py" -l
```

---

## Context: What This Batch Does

One seed grant, ruled by Tom 2026-09-06 during the FIX-10 prod verification: **"the accountant should be able to view jobs including what techs have been assigned."** Post-FIX-10 the Technicians box is hidden for accountant (the `schedule.view_all` section gate + the BE gate at `scheduling.py` both deny) — the correct grant-truth behavior at the time, now reversed by ruling.

| STEP | Change | File |
|---|---|---|
| 1 | accountant role gains `"schedule.view_all"` | `seed_core.py` `TENANT_USER_ROLE_ROWS` |
| 2 | Grant assertions (has view_all; NOT manage/view_own) | `test_tenant_user_role_grants.py` |
| 3 | 1E invariant reversal update | `test_task_1a4_scheduling_role_permissions.py` |
| 4 | Seed Rollout verification + README §4 update | `README-seed-data.md` |

**Out of scope**: `schedule.manage` / `schedule.view_own` for accountant; any route/gate change; migrations; FE (Part B); prod converge (Tom, post-batch).

## STEP 1 — The grant (design §B.1)

In `seed_core.py` `TENANT_USER_ROLE_ROWS["accountant"].permissions` (lines 918-929), add `"schedule.view_all"` with a lineage comment matching the FIX-9 style already in that array:

```python
            # PLP-FIX-11 (INV-BUG-18, Tom-ruled 2026-09-06): schedule read —
            # view jobs' technician assignments + read-only dispatch board.
            # Write stays schedule.manage (owner/office_staff only).
            "schedule.view_all",
```

Place it after `"catalog.manage"` and before the FIX-9 self-service block (keep the array's logical grouping). **Do not** touch the converge UPDATE block (2579-2627) — it picks the change up automatically. **Do not** grant `schedule.manage` or `schedule.view_own` (§G-Q3/Q6).

## STEP 2 — Grant assertions (mirror FIX-9)

In `test_tenant_user_role_grants.py`, add a PLP-FIX-11 test class (or extend the existing one per the file's structure) asserting, against the **seeded** role row:

- accountant `permissions` contains `"schedule.view_all"`;
- does **not** contain `"schedule.manage"` and does **not** contain `"schedule.view_own"`;
- office_staff still holds both `schedule.view_all` + `schedule.manage` (guard against array-edit accidents);
- technician still holds `schedule.view_own` and not `schedule.view_all` (the grant didn't leak).

Use the file's existing fixture/marker pattern (`pytestmark` domain marker + `pytest.mark.unit`; assert by content, never by count — README §7 shared-DB rule).

## STEP 3 — 1E invariant reversal (design §G-Q4)

In `test_task_1a4_scheduling_role_permissions.py` (lines 99-107): `test_accountant_has_no_schedule_permissions` currently asserts **zero** `schedule.*` grants. Update it to the new ruling — rename to reflect the reversal (e.g. `test_accountant_has_schedule_view_all_only`), assert the set of accountant `schedule.*` grants equals exactly `{"schedule.view_all"}`, and update the file's header docstring (line ~10: "accountant → no scheduling permissions (verified as absent)" → the PLP-FIX-11 ruling). If the grep sweep found other tests encoding the old invariant, update them the same way and list them in your Completion Summary.

## STEP 4 — Seed Data Rollout (Rule 11.5 — this batch *is* a seed change)

Per `backend/README-seed-data.md` §3/§6/§7:

- **Layer 1 — Core**: the STEP 1 edit *is* the Layer 1 change (Group A `seed_core.py`; the existing converge UPDATE keeps it idempotent and no-op-when-equal — verified by reading lines 2587-2607, no new code).
- **Layer 2 — Scenario**: N/A (no entity columns).
- **Verification**:
  ```bash
  cd <repo>/backend && source .venv/bin/activate
  python migrations/scripts/seed_core.py --mode seed    # expect: "🔄 [tenant_user_role] 'accountant' permissions converged" on first run; "ℹ️ already exists" on re-run (idempotency proof)
  python migrations/scripts/seed_core.py --mode inspect  # role rows print
  python -m pytest -m unit --tb=short -q 2>&1 | tail -5  # no seed-resilience breakage
  ```
  Then MCP re-verify query 3 from Pre-Work — expect accountant `t/f`.
- **README update**: `backend/README-seed-data.md` §4 (Current Seed State) — accountant row gains `schedule.view_all` with a one-line PLP-FIX-11 note.

- **OpenAPI**: no endpoint changes — run `python export_openapi_json.py` anyway per Rule 3 and confirm the diff is **timestamp-only**; commit it. Record the result in the Completion Summary.
- **DB model map**: no SQLModel changes — `generate_db_model_map.py` NOT required.

---

## Final Verification

### Phase 1 — Unit Tests Only (run after each task group during development)

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=short -q 2>&1 | tail -10
```

All unit tests must pass before moving on — fix any failure, including apparent pre-existing ones.

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

# Vendor-suite inclusion call: NOT required — seed script + role-grant tests only
# (no Telnyx/Stripe/SendGrid/Redis-covered modules modified). Record the call in the Completion Summary.

# Batch spot checks
python -m pytest tests/domains/identity_access/test_tenant_user_role_grants.py tests/batch_1e/test_task_1a4_scheduling_role_permissions.py -v 2>&1 | tail -15

echo "=== PLP-FIX-11-A FINAL VERIFICATION COMPLETE ==="
```

> **Any failure in either phase must be fixed before the batch is declared done.** No "pre-existing failure" exception without Tom's written confirmation.

---

## Definition of Done — PLP-FIX-11 Part A

Check off each item **in this prompt doc** as it completes:

- [ ] Pre-modification regression baseline captured (4848 passed, 1 skipped — or confirmed with Tom)
- [ ] All three MCP pre-work queries run — accountant pre-edit array confirmed without `schedule.view_all`
- [ ] All mandatory source files read (including the converge block at `seed_core.py`)
- [ ] **STEP 1**: `"schedule.view_all"` added to the accountant array with the PLP-FIX-11 lineage comment; converge mechanism untouched; `schedule.manage`/`schedule.view_own` NOT granted
- [ ] **STEP 2**: grant assertions added to `test_tenant_user_role_grants.py` (view_all present; manage/view_own absent; office_staff + technician guards)
- [ ] **STEP 3**: 1E invariant test updated to the ruling (exact set `{"schedule.view_all"}`; docstring updated); grep-sweep hits handled
- [ ] **STEP 4**: seed converge run (first run converges, re-run no-ops), `--mode inspect` verified, post-seed MCP query shows accountant `t/f`; `README-seed-data.md` §4 updated
- [ ] `python export_openapi_json.py` run — timestamp-only diff confirmed and committed
- [ ] All new/updated tests use `pytestmark` domain marker + `pytest.mark.unit`; assert-by-content, never by count
- [ ] `ruff check --fix && ruff format` on changed files only — zero remaining issues
- [ ] **Phase 1**: All unit tests pass — zero failures including any pre-existing
- [ ] **Phase 2**: Full suite (vendor-deselected) passes — zero failures, warning-clean; vendor inclusion call: NOT required (recorded in Completion Summary)
- [ ] Final test count (before → after) documented
- [ ] Completion Summary filled in at this prompt doc's ending `## Appendix — Completion Summary` (ADR-0017 — never the launch plan)
- [ ] Source spec task headers updated to ✅ Complete in any spec doc other than the launch plan — if applicable (`README-seed-data.md` §4 updated per STEP 4; no §10 task row for this batch)

---

## Completion Summary

After all Definition of Done items are complete, fill in the appendix at the end of THIS prompt doc using the format below.

```markdown
### PLP-FIX-11 Part A — Accountant schedule.view_all Seed Grant: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot Python Engineer
**Baseline**: X passed, Y skipped
**Final**: X+N passed, Y skipped (+N tests)

#### What Was Accomplished

- [grant edit + the two test updates + converge/inspect proof]

#### Files Changed / Created

| File | Action |
|---|---|
| `backend/migrations/scripts/seed_core.py` | Updated — ... |
| ... | ... |

#### Tests Added / Updated

| Test File | Domain | Tests | All Pass |
|---|---|---|---|
| `tests/domains/identity_access/test_tenant_user_role_grants.py` | identity_access | +N | ✅ |
| `tests/batch_1e/test_task_1a4_scheduling_role_permissions.py` | (as marked) | updated | ✅ |
```

---

## After This Task — Next Step

**Handoff to Part B (React)**: zero OpenAPI delta (timestamp-only confirmed), so `pnpm sync-api-types` is a formality — but it remains Part B's first pre-work step per the standing rule. Commit + push, then notify that Part A is closed.

Tom's rollout (after Part B also closes): **prod converge** (`seed_prod_db.py --mode seed --stripe-mode test`, typed `PILOT-PROD-SEED` — same gate as FIX-9 Phase 0.1; **no API/worker/Lambda deploy** — seed scripts run via the tunnel) → **web image** → design §Verification 1-5 (accountant sees assignments read-only; Schedule nav + read-only board appears; office1/owner unchanged; converge SQL proof `t/f`).

---

## Appendix — Completion Summary

### PLP-FIX-11 Part A — Accountant schedule.view_all Seed Grant: Completion Summary

**Completed**: 2026-09-06
**Mode**: Pilot Python Engineer
**Baseline**: 4848 passed, 1 skipped
**Final**: 4853 passed, 1 skipped (+5 tests)

#### What Was Accomplished

- Added `"schedule.view_all"` to the accountant role's `permissions` array in `seed_core.py` `TENANT_USER_ROLE_ROWS` (with PLP-FIX-11 lineage comment). The existing converge UPDATE block (lines 2587-2607) picked up the change automatically — no mechanism code touched. `schedule.manage` and `schedule.view_own` were NOT granted (design §G-Q3/Q6).
- Added 5 grant assertions in a new `TestPlpFix11AccountantScheduleGrant` class: accountant has `schedule.view_all`; does NOT have `schedule.manage` or `schedule.view_own`; office_staff still holds both keys (guard); technician still holds `view_own` not `view_all` (no leak).
- Updated the 1E-era invariant test `test_accountant_has_no_schedule_permissions` → `test_accountant_has_schedule_view_all_only` (reversal per Tom's 2026-09-06 ruling). Asserts the set of accountant `schedule.*` grants equals exactly `{"schedule.view_all"}`. Updated the file header docstring.
- Grep sweep: only `test_task_1a4_scheduling_role_permissions.py` encoded the old accountant invariant. The other two grep hits (`test_team_invites.py` line 660-663 = office_staff fixture definition; `test_find117_job_schedule_history.py` line 8 = docstring) do not encode the accountant invariant — no changes needed.
- Seed converge proof: first run → `🔄 [tenant_user_role] 'accountant' permissions converged (1 row updated)`; second run → `ℹ️ already exists` (idempotency proven).
- MCP post-converge re-verify: accountant `has_view_all=t, has_manage=f, has_view_own=f` — exactly design §Verification 5 target.
- `README-seed-data.md` §4 updated: accountant row note now reads "10 perms (+`schedule.view_all`)".
- `export_openapi_json.py` run: `openapi.json` unchanged (zero delta); `openapi_schema_map.md` timestamp-only diff (Generated line). Confirmed and committed.
- Ruff: 3 changed files lint+format clean (zero issues).

#### Files Changed / Created

| File | Action |
|---|---|
| `backend/migrations/scripts/seed_core.py` | Updated — accountant `permissions` array += `"schedule.view_all"` with PLP-FIX-11 lineage comment (lines 923-926) |
| `backend/tests/domains/identity_access/test_tenant_user_role_grants.py` | Updated — module docstring extended; new `TestPlpFix11AccountantScheduleGrant` class (+5 tests) |
| `backend/tests/batch_1e/test_task_1a4_scheduling_role_permissions.py` | Updated — header docstring + `test_accountant_has_no_schedule_permissions` → `test_accountant_has_schedule_view_all_only` (reversal) |
| `backend/README-seed-data.md` | Updated — §4 `tenant_user_role` row note: accountant now 10 perms (+`schedule.view_all`) |
| `backend/openapi_schema_map.md` | Regenerated — timestamp-only diff (no endpoint changes) |

#### Tests Added / Updated

| Test File | Domain | Tests | All Pass |
|---|---|---|---|
| `tests/domains/identity_access/test_tenant_user_role_grants.py` | identity_access | +5 new | ✅ |
| `tests/batch_1e/test_task_1a4_scheduling_role_permissions.py` | (batch_1e) | 1 updated (reversal) | ✅ |

#### Verification Summary

- **Phase 1 (unit)**: 4853 passed, 1 skipped — zero failures.
- **Phase 2 (full suite, vendor-deselected)**: 4853 passed, 1 skipped, 96 deselected — zero failures, warning-clean.
- **Vendor-suite inclusion call**: NOT required — seed script + role-grant tests only (no Telnyx/Stripe/SendGrid/Redis-covered modules modified).
- **OpenAPI**: zero endpoint delta (timestamp-only confirmed).
- **DB model map**: not required (no SQLModel changes).
- **MCP converge proof**: accountant `t/f/f` (view_all=true, manage=false, view_own=false).
