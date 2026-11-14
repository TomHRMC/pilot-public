# Batch SIGNUP-GA-B1 (FE) — Signup Wizard State-Machine Guard Alignment

**Version**: 1.0
**Date**: 2026-07-31
**Author**: Pilot Architect
**Batch type**: **Mixed** — Part A Backend (Python Engineer) + Part B Frontend (React Engineer) — web only (`apps/web`). Part A is a **small response-shape addition** (no DB, no migration); Part B is the state-machine guard fix. **Python Engineer runs first.**
**Priority / Phase**: P1 / **Pre-GA** (unblocks end-to-end self-serve onboarding testing — the legal page is currently unreachable)
**Plan link**: `pilot-launch-plan.md §2.3 row 14b`
**Predecessor**: `SIGNUP-GA-1` (BE ✅ + DevOps ✅ + FE ✅, 2026-07-30) — this batch fixes a defect discovered in live smoke testing of that batch.
**ADRs**: None new. Governed by the existing backend state machine (no boundary-crossing decision — the backend contract is authoritative).
**Prompts**: `batch-fe-signup-ga-b1-python-engr-prompt.md` (Part A — first) · `batch-fe-signup-ga-b1-react-engr-prompt.md` (Part B — after Part A handoff)

> **v1.1 change (Tom, 2026-07-31)**: promoted the `owner_first_name` return (previously deferred as P3 in §G) into **Part A backend scope** — it is an MVP requirement for the signup "Welcome back, {name}" personalization. This converts the batch from pure-FE to mixed BE+FE. See §D.1 and §G.

> **Why this batch now (Tom, 2026-07-31)**: In live smoke testing of the self-serve flow, `owner@example.com` completed Cognito SignUp → email verification → the Post-Confirmation Lambda (Path 3) created the tenant + owner, `POST /api/v1/signup` attached the wizard at `step1_account` — then `/signup/legal` **bounced back to `/signup/account`**. The infra (Cognito + Lambda + RDS) is verified working. The reset is a **frontend state-machine guard defect**: the legal page demands `step2_legal` on mount, but the correct backend state at that point is `step1_account`.

---

## A. Input Read Summary

| Input | Section(s) read | What it told us |
|---|---|---|
| `backend/services/tenant_signup.py` | `VALID_STATE_TRANSITIONS`, `initiate_signup()`, `advance_wizard_step()` | **The backend state machine is authoritative and defines "Model B"**: `signup_state = stepN` means *step N is complete; the user is now on UI page N+1*. `initiate_signup()` returns `step1_account`. `advance_wizard_step()` for the legal submit (`PUT /step2`) **requires** `current_state == "step1_account"` and advances to `step2_legal`. **Therefore the legal page is designed to load while the state is `step1_account`.** |
| `backend/api/routes/signup.py` | all `PUT /{id}/stepN` routes | Confirms the transition contract: `step2` route passes `current_state="step1_account"`; `step3` passes `"step2_legal"`; `step4` → `"step3_phone"`; `step5` → `"step4_tier"`. The route number (`stepN`) is the **UI page the user is submitting FROM**, and the state it requires is `step(N-1)`'s completion marker. |
| `backend/tests/batch_b14/test_a73_tenant_signup_state_machine.py` | `test_step1_to_step2_transition`, `test_wrong_state_returns_409` | Backend tests lock Model B: advancing from `step1_account` yields `step2_legal`; claiming `step2_legal` when the DB is `step1_account` is a **409**. The backend cannot be changed to satisfy the FE guards without breaking these tests and the 409-staleness contract. |
| `apps/web/src/features/signup/types.ts` | `signupStateToStep`, `stepToMinimumSignupState` | **The file contains BOTH models simultaneously.** `stepToMinimumSignupState` (lines 42–52) is **correct Model B** (`Legal → step1_account`, `Phone → step2_legal`, …). `signupStateToStep` (lines 32–39) is **wrong Model A** (`step2_legal → Legal`), i.e. it treats the state name as the page the user is on. |
| `apps/web/src/features/signup/hooks/useSignupWizard.ts` | `isStepAccessible`, `stateOrder`, reducer | `isStepAccessible` (lines 250–265) encodes **correct Model B** via `stepMinimumStateMap`. **But this hook is DEAD CODE** — a codebase search confirms no page imports `useSignupWizard`, `signupStateToStep` (outside the hook itself), or `isStepAccessible`. The pages each rolled their own inline guard instead. |
| The 5 route pages: `account`, `legal`, `phone`, `plan`, `ready` | inline `orderMap`/`stateOrderMap` + `urlMap` mount guards | **Every page's inline guard encodes wrong Model A.** Legal requires `orderMap[state] >= 2` (`step2_legal`); phone requires `>= 3`; plan `>= 4`; ready `>= 5`. Under Model B the correct minimums are `step1_account` (1), `step2_legal` (2), `step3_phone` (3), `step4_tier` (4) respectively — each guard is off by one. |
| `apps/web/src/mocks/handlers/signupHandlers.ts` | `PUT /step2`…`/step5`, `GET /state` | **The MSW handlers also encode wrong Model A and masked the bug.** `PUT /step2` returns `signup_state: "step3_phone"` — a **double jump** (`step1→step3`), skipping `step2_legal` entirely, which is exactly the value the wrong Model-A legal guard needs to not bounce. Real backend returns `step2_legal`. This is why the integration tests passed while the live flow broke. |
| Live DB via `postgres-local` MCP (2026-07-31) | `tenant_signup` columns + constraints | `signup_state` CHECK allows `step1_account…complete`; PK is `tenant_id`. `owner_first_name`/`owner_last_name` columns exist (nullable) — but note `get_signup_state()` does **not** return `owner_first_name` in `collected_data` (see §G open question resolved). No schema change is needed for this batch. |

**Key findings**:
1. The backend is a single, consistent, tested source of truth (**Model B**). The frontend contains **two conflicting models in the same feature folder**, and the *correct* one (`useSignupWizard` + `stepToMinimumSignupState`) is dead code while the *wrong* one (inline page guards + `signupStateToStep` + MSW) is what actually runs.
2. The reported legal-page bounce is **one instance of a systemic off-by-one**. The same defect exists in the phone, plan, and ready guards, and the account-page resume guard. Fixing only the legal page would move the bounce one step downstream.
3. The MSW `PUT /stepN` handlers return the wrong next-state (double-jumping), which is why the existing integration tests are green against a broken contract. **The mocks must be corrected to mirror the real backend** or the fix cannot be verified and future regressions will re-hide.

---

## B. Migration Plan

**None.** No database change. No Alembic migration. No `tenant_signup` column added or altered. MCP was consulted only to confirm no schema work is required (it is not).

---

## C. Execution Order

> **Part A (Python Engineer) runs first** — the single `get_signup_state()` enrichment (§D.1). On completion the Python Engineer runs `python export_openapi_json.py`, commits, and notifies the React Engineer. **Part B (React Engineer)** then runs the guard-alignment steps below after `pnpm sync-api-types`. Part B's steps 1–9 do not depend on Part A code-wise (the FE type already declares `owner_first_name?`), but the sequencing keeps the "Welcome back, {name}" personalization verifiable end-to-end in Part B's tests.

### Part A — Backend (Python Engineer)

| # | Step | File | Notes |
|---|---|---|---|
| A1 | Add `owner_first_name` + `owner_last_name` to the `collected_data` dict returned by `get_signup_state()` | `tenant_signup.py` | §D.1. Columns exist (MCP-confirmed). No migration, no Pydantic field change (`collected_data: dict`). |
| A2 | Unit test: `get_signup_state()` returns the owner names when set | `backend/tests/domains/identity_access/` | Assert-by-value; use a signup row with owner names populated. |
| A3 | `python export_openapi_json.py`; commit; notify React Engineer (handoff) | — | Standard process even though the `dict`-typed field yields no TS diff. |

### Part B — Frontend (React Engineer)

| # | Step | File(s) | Notes |
|---|---|---|---|
| 1 | Establish the single canonical state model in one place | `types.ts` | Fix `signupStateToStep` to Model B (see §F). Keep `stepToMinimumSignupState` (already correct). This is the shared source every page reads. |
| 2 | Replace the legal page's inline guard with the canonical minimum-state check | `legal/page.tsx` | The bug the user hit. Legal is accessible when `state >= step1_account`; redirect **forward** only when `state > step2` per Model B ordering (see §F). |
| 3 | Apply the identical correction to the phone, plan, ready guards | `phone/page.tsx`, `plan/page.tsx`, `ready/page.tsx` | Same off-by-one; fix all three so the bounce doesn't just move downstream. |
| 4 | Fix the account-page resume guard | `account/page.tsx` | Resume redirect must send a returning user to the page matching their state under Model B (a `step1_account` user stays on account; `step2_legal` → legal; etc. via `signupStateToStep`). |
| 5 | Correct the MSW handlers to mirror the real backend single-step transitions | `signupHandlers.ts` | `PUT /step2` → `step2_legal` (not `step3_phone`); `PUT /step3` → `step3_phone`; `PUT /step4` → `step4_tier`; `PUT /step5` → `complete`. `GET /state` returns the mutable current state. This is what makes the tests meaningful. |
| 6 | Update onboarding fixtures if they assert Model-A state→step mapping | `onboardingFixtures.ts` | Only if a fixture encodes the wrong mapping; verify against the real contract. |
| 7 | Retire OR wire the dead `useSignupWizard` hook | `useSignupWizard.ts` | **Decision in §G**: keep the hook, make it the single guard authority, but do NOT attempt a full page refactor to consume it in this batch (scope control). At minimum its `signupStateToStep` import must resolve to the corrected Model-B map so it is internally consistent if later adopted. |
| 8 | Update/repair the signup integration + component tests | `apps/web/src/__tests__/batch_signup_ga_1/`, `VerifyEmailStep.test.tsx` | Tests must assert the **real** single-step transitions (Model B) and that the legal page renders when state is `step1_account`. |
| 9 | Full Phase-2 verification | — | §Final Verification. |

---

## D. New / Changed API Endpoints

**No new endpoint or new path.** The existing signup wizard contract is otherwise unchanged:
- `POST /api/v1/signup` → returns `signup_state: "step1_account"`
- `GET /api/v1/signup/{tenant_id}/state` → returns current `signup_state` + `collected_data` **(response body enriched — see §D.1)**
- `PUT /api/v1/signup/{tenant_id}/step2` (legal) → requires state `step1_account`, returns `step2_legal`
- `PUT …/step3` (phone) → requires `step2_legal`, returns `step3_phone`
- `PUT …/step4` (plan) → requires `step3_phone`, returns `step4_tier`
- `PUT …/step5` (confirm) → requires `step4_tier`, returns `step5_confirm` (then `complete` on trial activation)

### D.1 — `GET /api/v1/signup/{tenant_id}/state` — add owner names to `collected_data` (Part A — Python Engineer)

**Change**: `get_signup_state()` currently builds `collected_data` from `business_name`, `trade`, `business_size`, `zip`, `time_zone`, `tier_selected`. Add the two owner-identity fields (both **already exist** on `tenant_signup`, MCP-confirmed nullable Text — no migration):

```python
"collected_data": {
    "business_name": signup.business_name,
    "trade": signup.trade,
    "business_size": signup.business_size,
    "zip": signup.zip,
    "time_zone": signup.time_zone,
    "owner_first_name": signup.owner_first_name,   # ADDED
    "owner_last_name": signup.owner_last_name,     # ADDED
    "tier_selected": signup.signup_state in ("step4_tier", "step5_confirm", "complete"),
},
```

- **No Pydantic schema field change required**: `SignupStateResponse.collected_data` is typed `dict`, so the new keys flow through without a schema edit. The `/state` and `/state/test` routes both return this shape.
- **OpenAPI**: `collected_data` is an untyped `dict` in the spec, so the generated TS type won't change — but the Python Engineer MUST still run `python export_openapi_json.py` per standard process, and the React Engineer MUST still run `pnpm sync-api-types` (see §H handoff). The FE type `SignupStateResponse.collected_data` already declares `owner_first_name?` — so no FE type change is needed; the field simply becomes populated at runtime.
- **Why it's real MVP**: the legal page renders a "Welcome back, {owner_first_name}" personalization (`legal/page.tsx`) that silently no-ops today because the backend never returns the name. This is the personalization the MVP onboarding requires.

**Part B (React)** consumes this by simply relying on the now-populated field — no new hook, no new endpoint. `pnpm sync-api-types` is a mandatory Pre-Work step (and now genuinely re-exports a changed `openapi.json`, even if the `dict`-typed `collected_data` yields no TS diff).

---

## E. Pattern Reuse Decisions (`mvp-arch.md §16`)

| Pattern | Applies? | How |
|---|---|---|
| 409-and-refresh staleness guard (ADR-0008) | ✅ (preserve) | The backend already returns `signup-state-conflict` 409 when a `PUT /stepN` is called with a stale `current_state`. The FE fix must NOT introduce a client-side model that would cause the FE to send a stale advance and trip this 409. Aligning to Model B keeps FE and BE in lockstep. |
| Single source of truth (canonical mapping) | ✅ | Consolidate the state→step + step→minimum-state mapping in `types.ts`; pages read from it rather than re-declaring inline `orderMap` literals. This is the structural fix that prevents the two-models drift from recurring. |
| Redundant Entry / wizard resumability (WCAG §36, rules) | ✅ (preserve) | Resume-from-backend must land the user on the correct page for their true state — the account-page and per-page guards implement this; the fix makes them correct. |

No new top-level UX pattern. No `packages/ui` change.

---

## F. Shared Module Interfaces (the exact corrections)

> These are **starting points derived from the current files** — the React Engineer must read each file first and adjust to the actual surrounding code.

### F.1 — The canonical model (the crux)

Under the **authoritative backend Model B**, define one ordering and two derived maps in `types.ts`:

```
stateOrder:   step1_account=1, step2_legal=2, step3_phone=3, step4_tier=4, step5_confirm=5, complete=6

The UI page a user should be ON for a given backend state (Model B — "stepN done ⇒ on page N+1"):
  step1_account  → Legal    (account step done ⇒ collect legal)
  step2_legal    → Phone
  step3_phone    → Plan
  step4_tier     → Ready
  step5_confirm  → Ready (payment/confirm) / complete → Dashboard
```

**`signupStateToStep` must be corrected** from the current wrong Model-A mapping to the above. `stepToMinimumSignupState` (already correct) stays and becomes the guard authority:

```
Account → min step? (account is the entry page; a user with state step1_account may also legitimately sit on Legal)
Legal   → step1_account
Phone   → step2_legal
Plan    → step3_phone
Ready   → step4_tier
```

### F.2 — The per-page guard shape (replace inline `orderMap` literals)

Each page's mount guard becomes (illustrative — adjust to the real file):

```
const minState = stepToMinimumSignupState[THIS_PAGE_STEP];   // from types.ts
const current  = res.data.signup_state;
if (stateOrder[current] < stateOrder[minState]) {
  // user hasn't reached this page yet → send them to the page for their real state
  router.replace(stepToUrl[signupStateToStep[current]] ?? "/signup/account");
} else if (stateOrder[current] > stateOrder[maxStateForThisPage]) {
  // user is past this page → forward to the page for their real state
  router.replace(stepToUrl[signupStateToStep[current]] ?? "/signup/account");
}
```

- For **Legal** (`THIS_PAGE_STEP = Legal`): `minState = step1_account` (order 1). A `step1_account` user (order 1 ≥ 1) is **allowed** — this fixes the reported bounce. Forward only when the user is genuinely past legal (state ≥ `step2_legal`? No — see the boundary note below).

> **Boundary note (must get right):** under Model B, once the legal step is submitted the state becomes `step2_legal`, which maps to the **Phone** page. So the Legal page's "forward" condition is `stateOrder[current] > stateOrder[step1_account]` **AND** the target is `signupStateToStep[current]`. Because `signupStateToStep[step1_account] = Legal`, a `step1_account` user resolves to "stay on Legal" — no redirect. A `step2_legal` user resolves to Phone — forward. This single rule (`if signupStateToStep[current] !== THIS_PAGE → redirect to that page`) is cleaner than the `< N` / `> N` pair and the engineer may implement the guard that way instead, as long as behavior matches the table in §F.1.

### F.3 — MSW handler correction (mirror the real backend)

In `signupHandlers.ts`, the mutable `currentSignupState` transitions must be **single-step**, matching `VALID_STATE_TRANSITIONS`:

| Handler | Current (WRONG) next state | Corrected next state |
|---|---|---|
| `PUT /step2` | `step3_phone` (double jump) | `step2_legal` |
| `PUT /step3` | `step4_tier` | `step3_phone` |
| `PUT /step4` | `step5_confirm` | `step4_tier` |
| `PUT /step5` | `complete` | `complete` (unchanged — step5 → complete is correct) |

`GET /state` continues to return the fixture for the current mutable state; the fixtures themselves (`SIGNUP_STATE_STEP2` etc.) already carry the correct `signup_state` string, so only the transition targets change.

---

## G. Open Questions Resolved

| Q | Resolution |
|---|---|
| Fix the backend or the frontend? | **Frontend.** The backend Model B is authoritative, internally consistent, and locked by passing tests + the 409-staleness contract (ADR-0008). Changing it has a far larger blast radius and would break `test_a73`. The FE has two conflicting models; we delete the wrong one. |
| Should we "advance the state to `step2_legal`" after `POST /signup` (the user's hypothesis)? | **No.** That would double-advance the machine: the legal page's own submit (`PUT /step2`) is what advances `step1_account → step2_legal`. Pre-advancing would make the legal submit trip the 409 staleness guard and would corrupt the meaning of `step2_legal` (legal *done*) for a user who hasn't accepted the docs yet. The correct fix is to let the legal page load at `step1_account`. |
| Is this only the legal page? | **No.** The identical off-by-one is in the phone, plan, ready guards and the account resume guard. All are fixed in this batch to prevent the bounce from relocating downstream. |
| `owner_first_name` for the legal "Welcome back" banner | **Promoted into Part A backend scope (v1.1, Tom 2026-07-31)** — was previously deferred as P3. `get_signup_state()` now returns `owner_first_name`/`owner_last_name` in `collected_data` (§D.1). Columns already exist; no migration. MVP personalization requirement — in-batch, not deferred. |
| Keep or delete the dead `useSignupWizard` hook? | **Keep, but do not force a full page refactor onto it in this batch.** Make it internally consistent (its `signupStateToStep` import resolves to the corrected map) so it is a correct future consolidation target. A follow-on (optional) can migrate all 5 pages to consume `isStepAccessible` from the hook and delete the inline guards entirely. Scope control: this batch fixes behavior + the shared map + the mocks + tests; the full hook adoption is a nice-to-have, not required to unblock testing. |
| Why did tests pass while the live flow broke? | The MSW `PUT /step2` handler double-jumped `step1→step3_phone`, feeding the wrong Model-A guard exactly the value it needed. Fixing the mocks to single-step is mandatory or the corrected guards can't be verified. |
| Any schema change? | **No migration.** The `owner_first_name`/`owner_last_name` columns already exist on `tenant_signup` (MCP-confirmed nullable Text). Part A only changes what `get_signup_state()` returns. |
| OpenAPI change? | **Re-exported, but no TS-type delta.** Part A runs `python export_openapi_json.py`; because `collected_data` is an untyped `dict` in the spec, the generated FE type is unchanged. `pnpm sync-api-types` remains mandatory Pre-Work for Part B. |
| Cost impact? | **$0.** No infra change. |

---

## H. Surface Mockup Reference (frontend batch)

**No new surface, no design spec required.** This batch changes **navigation-guard logic only** — no visual/layout change to any signup page. The existing pages (`account`, `verify`, `legal`, `phone`, `plan`, `ready`) render exactly as designed once the guards stop bouncing. No `pilot-web-ui-designer` spec is needed because no pixels change.

`§16` platform-pattern consumption: preserves the existing wizard resumability + 409-and-refresh behaviors; composes no new pattern.

---

## I. Component Manifest (mixed batch)

**No new components.** No `packages/ui` additions. All changes are edits to existing files:

**Part A — Backend (Python Engineer, runs first):**

| File | Action |
|---|---|
| `backend/services/tenant_signup.py` | Modified — `get_signup_state()` adds `owner_first_name`/`owner_last_name` to `collected_data` (§D.1). No migration; no Pydantic field change. |
| `backend/tests/domains/identity_access/` | Test added/updated — `get_signup_state()` returns owner names when set. |

**Part B — Frontend (React Engineer, after Part A handoff + `pnpm sync-api-types`):**

| File | Action |
|---|---|
| `features/signup/types.ts` | Modified — correct `signupStateToStep` to Model B; `stepToMinimumSignupState` unchanged (already correct); export a shared `stateOrder` if not already. |
| `app/signup/legal/page.tsx` | Modified — replace inline `orderMap` guard with canonical minimum-state check. |
| `app/signup/phone/page.tsx` | Modified — same guard correction. |
| `app/signup/plan/page.tsx` | Modified — same guard correction. |
| `app/signup/ready/page.tsx` | Modified — same guard correction. |
| `app/signup/account/page.tsx` | Modified — resume guard uses corrected `signupStateToStep`. |
| `mocks/handlers/signupHandlers.ts` | Modified — single-step transitions mirroring `VALID_STATE_TRANSITIONS`. |
| `features/signup/hooks/useSignupWizard.ts` | Modified (minimal) — internally consistent with the corrected map; not force-adopted by pages this batch. |
| `apps/web/src/__tests__/batch_signup_ga_b1/*.integration.test.tsx` | Created — verifies the full state-machine walk against corrected MSW; asserts legal renders at `step1_account`. |

---

## Definition of Done (design-level)

- The signup wizard navigates **forward through all 6 states without bouncing**, starting from the reported failure: a user at `step1_account` reaches `/signup/legal` and it renders (no redirect to `/signup/account`).
- Exactly **one** state model exists in the frontend (Model B), consolidated in `types.ts`; the wrong Model-A inline literals are gone.
- MSW handlers perform **single-step** transitions identical to the backend `VALID_STATE_TRANSITIONS`.
- New integration test walks `step1_account → … → complete` and would fail if any guard reintroduced the off-by-one.
- Part A: `get_signup_state()` returns `owner_first_name`/`owner_last_name`; backend Phase-2 (unit + full suite + ruff) passes; OpenAPI re-exported.
- Part B: the legal "Welcome back, {owner_first_name}" banner renders with the real name; full Phase-2 FE verification passes; zero new type/lint errors; no DB change.

---

*Authored by Pilot Architect (v1.1 — mixed BE+FE). Python Engineer prompt (`batch-fe-signup-ga-b1-python-engr-prompt.md`) runs first; React Engineer prompt (`batch-fe-signup-ga-b1-react-engr-prompt.md`) follows after handoff. Web-only. Governed by the existing backend signup state machine — no new ADR.*
