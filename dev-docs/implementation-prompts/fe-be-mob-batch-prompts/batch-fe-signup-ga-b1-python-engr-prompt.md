# Implementation Prompt: SIGNUP-GA-B1 (Part A) — Return owner names from the signup state endpoint

**Mode**: Pilot Python Engineer
**Batch**: SIGNUP-GA-B1 (Part A — Backend)
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §2.3 row 14b
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-fe-signup-ga-b1-design.md` — read §D.1, §C (Part A), §G, §I
**Estimated session**: 30–60 minutes
**Platform**: Backend only (`backend/`)
**Frontend companion**: SIGNUP-GA-B1 (Part B — React) — **this Part A runs first**; the React Engineer starts after your handoff + `pnpm sync-api-types`.

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-python-engineer/python-engineer-rules.md`** — full document; the hard rules are non-negotiable STOPs
- **`dev-docs/architecture-design/pilot-python-engineer-methods.md`** — §8 (Router Design), §16 (Standard Task Workflow)
- **`backend/tests/README-adding-tests.md`** — full document; governs test file structure, domain markers, fixture rules
- **`dev-docs/architecture-design/batch-designs/batch-fe-signup-ga-b1-design.md` §D.1** — the exact one-function change

Critical rules for this batch:

- **Rule 1 / Rule 16 (verify, don't assume)**: The `owner_first_name`/`owner_last_name` columns on `tenant_signup` are asserted to exist. **Confirm via `postgres-local` MCP before referencing them** (Pre-Work below). If MCP disagrees with this prompt → use the MCP-returned names and note it in your Completion Summary.
- **Rule 12 (sync routes — §21)**: `get_signup_state()` and its routes are plain sync `def`. **Do not** convert anything to `async def`.
- **Rule 13 (Pydantic v2 — §22)**: `SignupStateResponse.collected_data` is typed `dict` — the new keys flow through with **no schema field change**. Do not add typed sub-fields, do not introduce a `class Config`, do not change `response_model`.
- **Rule 11**: If ANY test fails during your work — even one that looks pre-existing — fix it before declaring done. If you can't find the root cause → STOP and ask Tom.

> **This is a surgical, additive change to ONE function.** No migration. No new endpoint. No model change. No new SQLModel field. Do NOT expand scope.

---

## Pre-Work: Establish Regression Baseline

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=no -q 2>&1 | tail -5
```

Record the exact count: **`X passed, Y failed`**. It must be ≥ this (plus your new/updated test) at the end.

> If any tests are already failing before you start: do NOT treat them as "pre-existing" and proceed. Confirm with Tom it's a known accepted failure, or fix it first.

---

## Pre-Work: Run MCP Verification Queries

> **MCP Usage Rule**: `postgres-local` is **read-only verification only**. Never INSERT/UPDATE/DELETE. If a query errors → STOP and ask Tom.

Run both via `postgres-local` MCP before writing any code:

```sql
-- 1. Confirm the owner-identity columns exist on tenant_signup (the fields §D.1 returns)
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'tenant_signup'
  AND column_name IN ('owner_first_name', 'owner_last_name', 'owner_email')
ORDER BY ordinal_position;

-- 2. Confirm no other columns are named differently than the service expects
SELECT column_name FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'tenant_signup'
ORDER BY ordinal_position;
```

Expected: `owner_first_name`, `owner_last_name` both present, `is_nullable = YES`, `data_type = text`. If they are absent or named differently → STOP and ask Tom (the design assumes they were added by the SIGNUP-GA-1 migration).

---

## Pre-Work: Read These Source Files

Use `read_file` on each before writing any code:

```
backend/services/tenant_signup.py         ← the get_signup_state() function to edit (~line 348); also read initiate_signup() for the field names it persists
backend/api/routes/signup.py              ← SignupStateResponse (collected_data: dict) + the /state and /state/test routes that call get_signup_state()
backend/tests/domains/identity_access/test_signup_resolve_or_attach.py   ← existing signup service tests + helpers/fixtures pattern to mirror
backend/tests/batch_b14/test_a73_tenant_signup_state_machine.py          ← the get_signup_state test that already asserts collected_data (test_get_signup_state_test)
backend/tests/README-adding-tests.md      ← domain markers + fixtures
```

Grep to confirm every caller of the function you're changing:

```bash
grep -rn "get_signup_state\b" backend/ --include="*.py"
```

---

## Background / Context

The self-serve signup wizard's legal page renders a "Welcome back, {owner_first_name}" personalization, but it is always blank because `get_signup_state()` builds `collected_data` without the owner names — even though `initiate_signup()` already persists `owner_first_name`/`owner_last_name` to `tenant_signup`. This is the MVP onboarding personalization requirement. The fix is to add the two fields to the returned `collected_data` dict. Because the API schema types `collected_data` as an untyped `dict`, no Pydantic/OpenAPI type change is needed — the keys just start appearing.

Part B (React) then relies on the now-populated field (its FE type already declares `owner_first_name?`).

---

## Task 1 — Add owner names to `get_signup_state()` `collected_data`

**File**: `backend/services/tenant_signup.py` — the `get_signup_state()` function (~line 348).
**Read it first.** It currently returns:

```python
return {
    "tenant_id": str(tenant_id),
    "signup_state": signup.signup_state,
    "collected_data": {
        "business_name": signup.business_name,
        "trade": signup.trade,
        "business_size": signup.business_size,
        "zip": signup.zip,
        "time_zone": signup.time_zone,
        "tier_selected": signup.signup_state
        in ("step4_tier", "step5_confirm", "complete"),
    },
}
```

Add the two owner-identity fields (use the exact column/attribute names MCP confirmed — expected `owner_first_name`, `owner_last_name`):

```python
    "collected_data": {
        "business_name": signup.business_name,
        "trade": signup.trade,
        "business_size": signup.business_size,
        "zip": signup.zip,
        "time_zone": signup.time_zone,
        "owner_first_name": signup.owner_first_name,   # ADDED (nullable — may be None)
        "owner_last_name": signup.owner_last_name,     # ADDED (nullable — may be None)
        "tier_selected": signup.signup_state
        in ("step4_tier", "step5_confirm", "complete"),
    },
```

- Do **not** change `SignupStateResponse` in `signup.py` — `collected_data: dict` already accepts the new keys.
- Do **not** touch `initiate_signup()` or `advance_wizard_step()`.
- The fields are nullable — returning `None` for a signup that predates owner-name capture is correct and expected; do not coerce to `""`.

Intermediate check:

```bash
python -m pytest -m unit --tb=short -q 2>&1 | tail -5
```

---

## Task 2 — Test the enriched response

Per `backend/tests/README-adding-tests.md`, domain = **`identity_access`** (signup/auth). Add a focused test to `backend/tests/domains/identity_access/` (extend the existing `test_signup_resolve_or_attach.py` or add a small `test_signup_state_owner_names.py` — mirror the file's existing `pytestmark` + helper pattern you read in Pre-Work).

```python
pytestmark = [
    pytest.mark.domain_identity_access,
    pytest.mark.unit,
]
```

Minimum coverage:

1. **Owner names returned when set**: create a `TenantSignup` (use the file's existing helper / `test_tenant`-style pattern — **no hardcoded `...0001` UUIDs**) with `owner_first_name="Mike"`, `owner_last_name="Johnson"`, then call `get_signup_state(db, tenant_id)` and assert `result["collected_data"]["owner_first_name"] == "Mike"` and `["owner_last_name"] == "Johnson"`.
2. **Null-safe**: a signup row with owner names `None` returns `collected_data["owner_first_name"] is None` (not a KeyError, not `""`).

Follow the Test Resilience Rule: assert by the fields you inserted, never by row counts; use `db_session` (transaction rollback) and fixtures — never module-level `TestClient`, never mutate shared seed rows.

If `test_get_signup_state_test` in `test_a73_tenant_signup_state_machine.py` asserts the exact `collected_data` key set, update it to allow/expect the new keys (do not delete its existing assertions).

---

## Regenerate OpenAPI

The endpoint's returned payload changed (even though `collected_data` is an untyped `dict`). Per standard process:

```bash
cd <repo>/backend
source .venv/bin/activate
python export_openapi_json.py
```

This refreshes `openapi.json` + `openapi_schema_map.md`. (No new path will appear; `collected_data` stays `dict` — that's expected. The regen is required so the FE `pnpm sync-api-types` runs against a current spec.)

No `db_models_map.md` regen (no model change). No `schema_manager.py` (no schema change). No seed rollout (no new column/lookup value).

---

## Final Verification

### Phase 1 — Unit only (during development)

```bash
cd <repo>/backend && source .venv/bin/activate
python -m pytest -m unit --tb=short -q 2>&1 | tail -10
```

### Phase 2 — Lint + full suite (once, before DoD sign-off)

```bash
cd <repo>/backend && source .venv/bin/activate
ruff check . --fix
ruff format .
python -m pytest --tb=short -q 2>&1 | tail -10
python -m pytest tests/domains/identity_access/ -v 2>&1 | tail -20
echo "=== SIGNUP-GA-B1 (Part A) FINAL VERIFICATION COMPLETE ==="
```

> Warning-clean is part of done. Any failure in either phase must be fixed before declaring done — no "pre-existing" exception without Tom's written confirmation. If you can't find a root cause → STOP and ask Tom.

---

## Definition of Done — SIGNUP-GA-B1 (Part A)

- [ ] Pre-modification regression baseline captured (`X passed, Y failed`) via `pytest -m unit`; zero unexplained pre-existing failures
- [ ] MCP confirmed `tenant_signup.owner_first_name` + `owner_last_name` exist (nullable text) before writing code
- [ ] All mandatory source files read (incl. `api/routes/signup.py` for the `dict`-typed `collected_data`)
- [ ] **Task 1**: `get_signup_state()` returns `owner_first_name` + `owner_last_name` in `collected_data`; `initiate_signup()`/`advance_wizard_step()` untouched; `SignupStateResponse` unchanged
- [ ] All DB-touching code remains sync `def` (no `async def`) (rules §21)
- [ ] No Pydantic v1 carryover introduced (rules §22)
- [ ] **Task 2**: test added under `tests/domains/identity_access/` with `domain_identity_access` + `unit` markers; asserts owner names returned when set + null-safe; assert-by-value not by count
- [ ] Any existing `collected_data` assertion (e.g. `test_a73` `test_get_signup_state_test`) updated to accommodate the new keys
- [ ] `python export_openapi_json.py` run — `openapi.json` + `openapi_schema_map.md` refreshed
- [ ] `ruff check . --fix && ruff format .` clean; no unjustified `# noqa`
- [ ] **Phase 1**: all unit tests pass (zero failures)
- [ ] **Phase 2**: full suite passes, warning-clean
- [ ] Final test count (before → after) documented
- [ ] Completion Summary added to `pilot-launch-plan.md` §SIGNUP-GA-B1
- [ ] **Handoff performed** (see below) — React Engineer notified

---

## Handoff Instructions (MANDATORY — Part B depends on this)

After all DoD items pass:

1. Confirm `python export_openapi_json.py` was run and `backend/openapi.json` is committed.
2. Notify the React Engineer that **SIGNUP-GA-B1 Part A is complete** and their **first Pre-Work step is `pnpm sync-api-types`** (it will re-export the current spec; the `dict`-typed `collected_data` means no TS diff is expected, which is fine).
3. State explicitly: the `/api/v1/signup/{tenant_id}/state` response now includes `collected_data.owner_first_name` and `collected_data.owner_last_name` at runtime — Part B's legal "Welcome back, {name}" banner will now populate.

---

## Completion Summary

After all DoD items are complete, add this to `pilot-launch-plan.md` §SIGNUP-GA-B1:

### SIGNUP-GA-B1 (Part A — Backend) — Owner names in signup state: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot Python Engineer
**Baseline**: X passed, Y failed
**Final**: X+N passed, Y failed (+N new tests)

#### What Was Accomplished

- `get_signup_state()` now returns `owner_first_name`/`owner_last_name` in `collected_data`, populating the signup "Welcome back, {name}" personalization (MVP requirement). No migration — columns already existed; no Pydantic/OpenAPI type change (`collected_data: dict`).

#### Files Changed / Created

| File | Action |
|---|---|
| `backend/services/tenant_signup.py` | Updated — `get_signup_state()` adds owner names to `collected_data` |
| `backend/tests/domains/identity_access/…` | Created/Updated — owner-names-returned + null-safe tests |
| `backend/openapi.json` / `openapi_schema_map.md` | Regenerated |

#### Tests Added

| Test File | Domain | Tests | All Pass |
|---|---|---|---|
| `tests/domains/identity_access/test_signup_state_owner_names.py` | `identity_access` | N | ✅ |

---

## After This Task — Next Step

Hand off to **SIGNUP-GA-B1 Part B** (`batch-fe-signup-ga-b1-react-engr-prompt.md`) — the React Engineer fixes the wizard state-machine guards and wires the now-populated "Welcome back, {name}" banner.
