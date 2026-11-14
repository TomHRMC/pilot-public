# Implementation Prompt: SIGNUP-GA-B1 (Part B) — Signup Wizard State-Machine Guard Alignment

**Mode**: Pilot React Engineer
**Batch**: SIGNUP-GA-B1 (Part B — Frontend)
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §2.3 row 14b
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-fe-signup-ga-b1-design.md` ← read every section A–I (esp. §D.1 for the owner-names field)
**Estimated session**: 2–3 hours
**Platform**: Web only (`apps/web`)
**Backend companion**: **SIGNUP-GA-B1 (Part A — Python) must complete first.** Part A adds `owner_first_name`/`owner_last_name` to the `GET /signup/{id}/state` `collected_data` (§D.1). Do NOT start until Part A is handed off. Your first Pre-Work step is `pnpm sync-api-types`. No `packages/ui` change; no DB change.

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-react-engineer/react-engineer-rules.md`** — in full
- **`dev-docs/architecture-design/batch-designs/batch-fe-signup-ga-b1-design.md`** — every section (A–I). §A, §F, and §G are the crux.

Critical rules for this batch:

- **Rule 2**: All API calls use `apiClient` from `@pilot/shared-api` (**not** `@/lib/api-client` — that module does not exist). `fetch()` is permanently banned for `/api/v1/...` calls. The signup pages already use `apiClient` — keep it.
- **Rule 9**: Route files in `apps/web/src/app/` must be thin. The signup pages are `"use client"` page components under `app/signup/` (a **public**, non-`(authed)` group — no JWT on the account/verify pages). Do not restructure them; only change the guard logic inside.
- **Rule 10**: If ANY test fails during your work — even one that appears pre-existing — you must fix it before declaring the batch done. There is no "not my fault" exception. If you cannot identify the root cause → STOP and ask Tom.
- **Rule 11 (React Compiler — §32)**: React 19.2 with the compiler. Do NOT hand-write `useMemo`/`useCallback`/`React.memo` for render-perf. The guard logic is a plain synchronous computation inside a `useEffect` / `useQuery` callback — no memoization needed. (Note: the dead `useSignupWizard` hook currently uses `useCallback` for `isStepAccessible` — leave its existing shape; do not add new memoization.)
- **Rule 12 (TanStack Query v5 — §33)**: The legal page uses `useQuery({ queryKey, queryFn })` object-form — keep it. Other signup pages use raw `apiClient.get(...).then(...)` inside `useEffect` — you may leave that pattern as-is (this is a surgical guard fix, not a data-layer rewrite).
- **Rule 15 (WCAG 2.2 AA — §36)**: No visual change in this batch. Do not regress any existing accessibility affordance (focus rings, non-color-only errors) while editing.

**This is a surgical navigation-guard fix + one personalization wire-up. Do NOT refactor the signup data layer, do NOT restyle any page, do NOT change any API call shape.**

---

## Design Decisions (Do Not Re-Litigate)

From Design Doc §F and §G — these are final:

| Decision | Outcome | Rationale |
|---|---|---|
| Fix direction | **Frontend conforms to the backend** | The backend state machine (Model B) is authoritative, internally consistent, and locked by passing tests + the 409-staleness contract (ADR-0008). |
| The canonical model | **Model B**: `signup_state = stepN` means *step N is complete; user is now on UI page N+1* | Proven by `advance_wizard_step()` + every `PUT /stepN` route + `test_a73`. |
| "Advance state to `step2_legal` after `POST /signup`"? | **NO — do not do this** | The legal page's own submit (`PUT /step2`) advances `step1_account → step2_legal`. Pre-advancing would trip the 409 staleness guard and corrupt the meaning of `step2_legal`. The fix is to let the legal page **load** at `step1_account`. |
| Scope | Fix **all 5 page guards + the shared map + the MSW handlers + tests** | The off-by-one is systemic; fixing only legal moves the bounce downstream. |
| Dead `useSignupWizard` hook | **Keep it, make it internally consistent, do NOT force a full page refactor onto it** | Full hook adoption is an optional follow-on. This batch fixes behavior, the shared map, mocks, and tests only. |
| `owner_first_name` in the legal "Welcome back" banner | **In scope — Part A (Python) already returns it in `collected_data` (§D.1).** Part B verifies the banner populates. | MVP personalization. Part A ran first; the FE type `SignupStateResponse.collected_data.owner_first_name?` already exists — no FE type change, the field is just populated at runtime now. |

**The authoritative state contract (backend `VALID_STATE_TRANSITIONS` — do not deviate):**

```
step1_account → step2_legal → step3_phone → step4_tier → step5_confirm → complete
```

**Which UI page a user should be ON for a given backend state (Model B):**

| backend `signup_state` | user is on page | route |
|---|---|---|
| `step1_account` | Legal | `/signup/legal` |
| `step2_legal` | Phone | `/signup/phone` |
| `step3_phone` | Plan | `/signup/plan` |
| `step4_tier` | Ready | `/signup/ready` |
| `step5_confirm` | Ready (confirm/pay) | `/signup/ready` |
| `complete` | Dashboard | `/dashboard` |

> Note the entry pages `account` and `verify` precede `step1_account` existing — a brand-new user with no `tenant_id` in sessionStorage starts on `/signup/account`. Once `POST /signup` returns `step1_account`, the canonical page is **Legal**.

---

## Pre-Work: Establish Regression Baseline

Before touching any file:

```bash
cd <repo>/frontend
pnpm --filter web test 2>&1 | tail -5
```

Record the exact pass/fail counts. These must still pass (plus your new tests) at the end.

> If any tests are already failing before you start: do NOT treat them as "pre-existing" and proceed. Either confirm with Tom it's a known accepted failure, or fix it first. You may not start while tests are in an unexplained failed state.

---

## Pre-Work: Sync API Types

```bash
cd <repo>/frontend
pnpm sync-api-types
```

Part A (Python) re-exported `openapi.json` after adding owner names to `collected_data`. Because `collected_data` is typed as an untyped `dict` in the spec, `pnpm sync-api-types` should produce **no TS diff** to `packages/shared-types/src/api-schema.d.ts` — that is expected and fine. Run it anyway (mandatory): it confirms you are building against Part A's current spec. If it produces an **unexpected** diff beyond `collected_data`, STOP and tell Tom (independent backend drift).

> **Dependency gate**: if Part A has NOT been handed off yet (the `/signup/{id}/state` response does not include `owner_first_name` when you smoke-test), STOP — Part B runs after Part A.

---

## Pre-Work: Verify Endpoints

No new endpoints. Confirm the existing signup contract is present (it must be — SIGNUP-GA-1 shipped it):

```bash
cd <repo>/backend
python3 -c "
import json
spec = json.load(open('openapi.json'))
print([p for p in spec['paths'] if '/signup' in p])
"
```

Verified endpoints for this batch (all pre-existing, unchanged):

| Call | Endpoint | Model-B contract |
|---|---|---|
| initiate | `POST /api/v1/signup` | returns `step1_account` |
| state | `GET /api/v1/signup/{id}/state` | returns current `signup_state` |
| legal advance | `PUT /api/v1/signup/{id}/step2` | requires `step1_account` → returns `step2_legal` |
| phone advance | `PUT /api/v1/signup/{id}/step3` | requires `step2_legal` → returns `step3_phone` |
| plan advance | `PUT /api/v1/signup/{id}/step4` | requires `step3_phone` → returns `step4_tier` |
| confirm advance | `PUT /api/v1/signup/{id}/step5` | requires `step4_tier` → returns `step5_confirm`/`complete` |

**If any of these is missing → STOP and ask Tom (SIGNUP-GA-1 is supposed to have shipped them).**

---

## Pre-Work: Read These Source Files

Read each with `read_file` before writing any code:

```
frontend/apps/web/src/features/signup/types.ts                          ← the shared model; contains BOTH correct + wrong maps
frontend/apps/web/src/features/signup/hooks/useSignupWizard.ts          ← dead-but-correct Model-B hook (isStepAccessible)
frontend/apps/web/src/app/signup/account/page.tsx                       ← resume guard (Model-A, off by one)
frontend/apps/web/src/app/signup/legal/page.tsx                         ← the reported bounce (line ~84)
frontend/apps/web/src/app/signup/phone/page.tsx                         ← same off-by-one (line ~61)
frontend/apps/web/src/app/signup/plan/page.tsx                          ← same off-by-one (line ~115)
frontend/apps/web/src/app/signup/ready/page.tsx                         ← same off-by-one (line ~72)
frontend/apps/web/src/mocks/handlers/signupHandlers.ts                  ← MSW double-jump that masked the bug
frontend/apps/web/src/features/onboarding/mocks/onboardingFixtures.ts   ← state fixtures used by handlers
frontend/apps/web/src/mocks/handlers/index.ts                           ← confirm signupHandlers is registered (it is; no new file)
frontend/apps/web/src/features/signup/components/VerifyEmailStep.tsx    ← the confirm→signIn→POST /signup→push(/legal) flow (context only; do NOT change its logic)
```

Also confirm the dead hook is truly unused before deciding how light-touch to be:

```bash
grep -rn "useSignupWizard\|signupStateToStep\|isStepAccessible" frontend/apps/web/src --include=*.tsx --include=*.ts | grep -v "features/signup/hooks/useSignupWizard.ts" | grep -v "features/signup/types.ts"
```

If that grep returns only test files (or nothing), the pages do not consume the hook — proceed with the surgical guard fix in each page as described.

---

## Context: What This Batch Does

A single off-by-one **state-machine model conflict** makes `/signup/legal` bounce back to `/signup/account` right after email verification. The backend correctly leaves the wizard at `step1_account` (Model B: "account step done → now collect legal"), but every FE page guard was written as if `stepN` = "user is on page N" (Model A), so the legal page demands `step2_legal` and rejects the correct `step1_account`. The same off-by-one is in the phone, plan, ready, and account-resume guards, and the MSW handlers double-jump transitions which hid it from tests.

| Change | File |
|---|---|
| Correct `signupStateToStep` to Model B; keep `stepToMinimumSignupState`; export a shared `stateOrder` | `types.ts` |
| Replace each page's inline `orderMap`/`stateOrderMap` guard with the canonical minimum-state check | 5 signup pages |
| Correct MSW `PUT /stepN` transitions to single-step (mirror backend) | `signupHandlers.ts` |
| Verify the legal "Welcome back, {owner_first_name}" banner populates (Part A now returns the field) | `legal/page.tsx` |
| Make the dead `useSignupWizard` hook internally consistent with the corrected map | `useSignupWizard.ts` |
| Add an integration test that walks the whole machine and would catch a reintroduced off-by-one | new `__tests__/batch_signup_ga_b1/` |

---

## STEP 1 — Consolidate the canonical model in `types.ts`

**File**: `frontend/apps/web/src/features/signup/types.ts`
**Read the file first.** It already exports `WizardSignupState`, `OnboardingStep`, `signupStateToStep` (WRONG), and `stepToMinimumSignupState` (CORRECT — keep as-is).

Correct `signupStateToStep` so it maps a backend state to the page the user should be **on** under Model B (see the table in Design Decisions above):

```ts
// Starting point — adjust to the actual OnboardingStep enum members you find in the file.
export const signupStateToStep: Record<WizardSignupState, OnboardingStep> = {
  step1_account: OnboardingStep.Legal,   // account done ⇒ collect legal
  step2_legal:   OnboardingStep.Phone,
  step3_phone:   OnboardingStep.Plan,
  step4_tier:    OnboardingStep.Ready,
  step5_confirm: OnboardingStep.Ready,
  complete:      OnboardingStep.Ready,   // complete is special-cased to /dashboard in guards
};
```

Export a single shared `stateOrder` (the pages currently each re-declare it inline — centralize it here so it can't drift):

```ts
export const stateOrder: Record<WizardSignupState, number> = {
  step1_account: 1, step2_legal: 2, step3_phone: 3,
  step4_tier: 4, step5_confirm: 5, complete: 6,
};
```

> **Verify immediately after this step** (this file is imported widely):
> ```bash
> pnpm --filter web check-types 2>&1 | tail -5
> ```

---

## STEP 2 — Fix the legal page guard (the reported bounce)

**File**: `frontend/apps/web/src/app/signup/legal/page.tsx` (guard is the `useEffect` around line 61–89).
**Read it first.** It fetches state via `useQuery(["signup-state", tenantId])` and currently does `if (orderMap[state] < 2) router.replace(...)`.

Replace the inline `orderMap`/`urlMap` with the shared model. The rule is: **if the page the user belongs on is not THIS page, redirect there.**

```ts
// Illustrative — adjust names to what you find. Import stateOrder, signupStateToStep,
// stepToMinimumSignupState and a stepToUrl map from the shared module.
const current = signupStateData.signup_state as WizardSignupState;
const belongsOn = signupStateToStep[current];              // Model B page for this state
if (belongsOn !== OnboardingStep.Legal) {
  router.replace(stepToUrl[belongsOn] ?? "/signup/account");
}
```

- For a `step1_account` user: `signupStateToStep["step1_account"] === Legal` ⇒ **no redirect**. This fixes the bounce.
- For a `step2_legal`+ user: resolves to Phone/Plan/Ready ⇒ forward correctly.
- `complete` ⇒ `signupStateToStep` maps to Ready, but complete must go to `/dashboard`; keep the existing explicit `complete → /dashboard` special-case (and clear `sessionStorage` as the ready page does).

There is a `stepToUrl` map already in `useSignupWizard.ts`. Move/export it to the shared module (or add one in `types.ts`) so all pages use the same URL mapping — do not re-declare `urlMap` inline in each page.

---

## STEP 3 — Apply the same guard correction to phone, plan, ready

**Files**: `phone/page.tsx` (~line 61), `plan/page.tsx` (~line 115), `ready/page.tsx` (~line 72).
Each currently uses a `stateOrderMap` + `urlMap` with a `< N` comparison off by one. Replace each with the same canonical check, substituting the page's own `OnboardingStep`:

- phone: `if (signupStateToStep[current] !== OnboardingStep.Phone) redirect`
- plan: `if (signupStateToStep[current] !== OnboardingStep.Plan) redirect`
- ready: `if (signupStateToStep[current] !== OnboardingStep.Ready) redirect` — **but** keep the ready page's existing `complete → clear session + /dashboard` branch, and note both `step4_tier` and `step5_confirm` map to Ready (both legitimately sit on ready), so the guard must allow both. Since `signupStateToStep` maps both `step4_tier` and `step5_confirm` to Ready, the single-rule check handles this correctly.

Preserve each page's non-guard behavior (phone's `businessSize` read on plan, `owner_first_name`/`business_name` reads on ready, the `.catch()` that clears sessionStorage on a 404/expired session).

---

## STEP 4 — Fix the account-page resume guard

**File**: `account/page.tsx` (~line 126–150).
On mount, if a `tenant_id` is in sessionStorage it fetches state and redirects to the current step. Currently uses a `stepMap` that (per Model A) sends `step1_account → /signup/account` (i.e. stays), which under Model B is **wrong** — a `step1_account` user should be forwarded to `/signup/legal`.

Change the resume redirect to use `signupStateToStep` + shared `stepToUrl`:

```ts
const current = res.data.signup_state as WizardSignupState;
const target = stepToUrl[signupStateToStep[current]] ?? "/signup/account";
if (current === "complete") { /* clear session → /dashboard */ }
else if (target !== "/signup/account") router.replace(target);
```

Keep the `.catch()` that removes the stale `WIZARD_TENANT_ID_KEY` on a failed/expired state fetch.

> Do NOT change `VerifyEmailStep.tsx` — its `router.push("/signup/legal")` after `POST /signup` is already correct under Model B (the legal page will now accept the `step1_account` user).

---

## STEP 5 — Correct the MSW handlers to mirror the real backend

**File**: `frontend/apps/web/src/mocks/handlers/signupHandlers.ts`.
The mutable `currentSignupState` transitions currently double-jump. Make them **single-step**, matching `VALID_STATE_TRANSITIONS`:

| Handler | Change `currentSignupState = ` |
|---|---|
| `PUT /step2` | `"step2_legal"` (was `"step3_phone"`) — and return `signup_state: "step2_legal"`, `next_step: "phone"` |
| `PUT /step3` | `"step3_phone"` (was `"step4_tier"`) — return `signup_state: "step3_phone"`, `next_step: "plan"` |
| `PUT /step4` | `"step4_tier"` (was `"step5_confirm"`) — return `signup_state: "step4_tier"`, `next_step: "ready"` |
| `PUT /step5` | `"complete"` (unchanged) |

Leave `GET /state` returning the fixture for the current mutable state. If any state fixture in `onboardingFixtures.ts` encodes a wrong `signup_state` string for its step, correct it — but the fixtures already carry the right strings, so likely only the handler transition targets change. **Do not create a new handler file; `signupHandlers` is already registered in `index.ts`.**

---

## STEP 6 — Verify the legal "Welcome back, {name}" banner populates

**File**: `frontend/apps/web/src/app/signup/legal/page.tsx` (the `ownerName` read ~line 91 + the banner JSX).
Part A (Python) now returns `owner_first_name` in `GET /signup/{id}/state` → `collected_data`. The page already reads `signupStateData?.collected_data?.owner_first_name` into `ownerName` and conditionally renders "Welcome back, {ownerName}." — so in most cases **no code change is required**; the banner simply starts populating.

Do this in STEP 6:
1. Read the current `ownerName` derivation and banner JSX. Confirm it reads `collected_data.owner_first_name` (the field Part A returns) and renders only when truthy.
2. If (and only if) the field name it reads does not match what Part A returns (`owner_first_name`), correct the read to `owner_first_name`. Do NOT restyle the banner or change its copy.
3. The FE type `SignupStateResponse.collected_data.owner_first_name?` already exists — no type change. If `pnpm sync-api-types` did not change it (expected, `collected_data` is `dict`), that is correct.

> Keep it null-safe: when `owner_first_name` is `null` (older signups), the banner must not render "Welcome back, ." — the existing `{ownerName && (...)}` guard handles this; preserve it.

---

## STEP 7 — Keep the dead hook internally consistent

**File**: `frontend/apps/web/src/features/signup/hooks/useSignupWizard.ts`.
It imports `signupStateToStep` (now corrected) and has its own correct `isStepAccessible`. After STEP 1, its `RESUME`/navigation logic using `signupStateToStep[serverState.signup_state]` now resolves to Model B — which is correct. **Make no behavioral change beyond what the corrected import gives you.** Do not force the 5 pages to consume this hook in this batch (out of scope). If leaving it entirely unused trips a lint "unused export" rule, keep the existing exports as-is (they are part of the public feature API and were already present).

---

## Test Requirements

### Integration test — the whole-machine walk (the regression lock)

Create `frontend/apps/web/src/__tests__/batch_signup_ga_b1/signup_state_machine.integration.test.tsx`.

Use MSW (`setupServer` from `msw/node`) with the **corrected** `signupHandlers`. Mock `next/navigation` (`vi.mock`) so you can assert `router.replace`/`router.push` targets.

Minimum coverage:

1. **The reported bug is fixed**: with `GET /state` returning `signup_state: "step1_account"`, rendering the legal page **does NOT redirect to `/signup/account`** and the legal form (`data-testid="signup-legal-form"`) renders.
2. **Forward walk**: driving `PUT /step2 → /step3 → /step4 → /step5`, each returns the correct **single-step** next state (`step2_legal`, `step3_phone`, `step4_tier`, `complete`) — assert on the response `signup_state` values, proving no double-jump.
3. **Each page admits its correct state and forwards others**: legal admits `step1_account`; phone admits `step2_legal` and bounces `step1_account` back to `/signup/legal`; plan admits `step3_phone`; ready admits `step4_tier` and `step5_confirm`.
4. **Account resume**: with a `tenant_id` in sessionStorage and state `step1_account`, the account page redirects to `/signup/legal` (not stays on account).
5. **Welcome-back banner**: with `GET /state` returning `collected_data.owner_first_name: "Mike"`, the legal page renders "Welcome back, Mike"; with `owner_first_name: null`, the banner does not render (no "Welcome back, ."). Ensure the MSW fixture / per-test override supplies `owner_first_name` so this is actually exercised.

TanStack Query in tests — always `retry: false`:

```ts
function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}
```

MSW setup:

```ts
import { setupServer } from "msw/node";
const server = setupServer(...signupHandlers);
beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
```

Mock Next navigation (assert redirect targets):

```ts
const replace = vi.fn(); const push = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace, push }),
  useSearchParams: () => new URLSearchParams(),
}));
beforeEach(() => { replace.mockClear(); push.mockClear(); });
```

**Never mock `apiClient` directly** — MSW intercepts at the HTTP level. Assert by specific content/target, never by list length. Reset handlers in `afterEach`.

### Existing tests

Repair any existing signup test that asserted the **wrong** Model-A transition (e.g. a test expecting `PUT /step2` to yield `step3_phone`, or expecting the legal page to redirect at `step1_account`). These assertions encoded the bug — update them to the corrected contract. Per Rule 10, every failing test must be green before done.

---

## Final Verification

> ❌ **BANNED COMMAND**: `npx vitest run` — never use it. The only correct web runner is `pnpm --filter web test`.

### Phase 1 — Targeted (during development)

```bash
cd <repo>/frontend

# The new integration test:
pnpm --filter web test -- apps/web/src/__tests__/batch_signup_ga_b1/ 2>&1 | tail -10

# The signup feature area + the prior batch's tests:
pnpm --filter web test -- apps/web/src/__tests__/batch_signup_ga_1/ 2>&1 | tail -10
pnpm --filter web test 2>&1 | tail -6
```

Fix any failure before moving on — including ones that look pre-existing.

### Phase 2 — Full verification (once, before DoD sign-off)

```bash
cd <repo>/frontend && echo "=== UI - Type Check ===" && pnpm --filter @pilot/ui check-types && echo "=== Web - Type Check ===" && pnpm --filter web check-types && echo "=== Mobile - Type Check ===" && pnpm --filter mobile build && echo "=== UI - Lint ===" && pnpm --filter @pilot/ui lint && echo "=== Web - Lint ===" && pnpm --filter web lint && echo "=== Mobile - Lint ===" && pnpm --filter mobile lint && echo "=== TYPE+LINT PASS ===" && echo "=== UI - Tests ===" && pnpm --filter @pilot/ui test 2>&1 | tail -6 && echo "=== Web - Tests ===" && pnpm --filter web test 2>&1 | tail -6 && echo "=== Mobile - Tests ===" && pnpm --filter mobile test 2>&1 | tail -8 && echo "=== MVP FINAL VERIFICATION COMPLETE ==="
```

> Any failure in either phase must be fixed before the batch is declared done. No "pre-existing failure" exception without explicit written confirmation from Tom. If you cannot identify a root cause → STOP and ask Tom.

---

## Definition of Done — SIGNUP-GA-B1

Update the `pilot-launch-plan.md` row 14b tracker + add the Completion Summary when done:

- [ ] **Part A (Python) confirmed handed off** — `/signup/{id}/state` returns `collected_data.owner_first_name` (do not start before this)
- [ ] Pre-modification regression baseline captured (zero pre-existing failures, or confirmed with Tom)
- [ ] `pnpm sync-api-types` run — no TS diff expected (`collected_data` is `dict`); any diff **beyond** that → STOP and tell Tom
- [ ] Design doc fully read (A–I, esp. §D.1) before writing any code
- [ ] All mandatory source files read before modifying
- [ ] Confirmed via grep that pages do not import `useSignupWizard` (surgical page fix justified)
- [ ] **STEP 1**: `types.ts` — `signupStateToStep` corrected to Model B; shared `stateOrder` + `stepToUrl` exported; `stepToMinimumSignupState` unchanged
- [ ] **STEP 2**: `legal/page.tsx` — inline guard replaced with canonical check; **legal renders at `step1_account` (bounce fixed)**
- [ ] **STEP 3**: `phone/page.tsx`, `plan/page.tsx`, `ready/page.tsx` — same guard correction; ready still special-cases `complete → /dashboard` and admits both `step4_tier` + `step5_confirm`
- [ ] **STEP 4**: `account/page.tsx` — resume guard forwards `step1_account` → `/signup/legal`
- [ ] **STEP 5**: `signupHandlers.ts` — `PUT /stepN` transitions are single-step mirroring `VALID_STATE_TRANSITIONS` (no double-jump)
- [ ] **STEP 6**: `legal/page.tsx` — "Welcome back, {owner_first_name}" banner populates from `collected_data.owner_first_name`; null-safe (no "Welcome back, ." when null); no restyle/copy change
- [ ] **STEP 7**: `useSignupWizard.ts` internally consistent with the corrected map; pages not force-refactored onto it
- [ ] Integration test walks `step1_account → complete` and would fail if any guard reintroduced the off-by-one; includes the banner populated + null-safe cases
- [ ] Existing Model-A assertions updated to the corrected contract; no failing tests
- [ ] No hand-written `useMemo`/`useCallback`/`React.memo` added (React Compiler, §32); components pure
- [ ] No visual/accessibility regression (no styling change intended)
- [ ] Zero TypeScript errors; zero ESLint `no-hardcoded-design-values`/purity warnings
- [ ] No DB or `packages/ui` change (backend change was Part A's `get_signup_state()` only)
- [ ] **Phase 2 FULL verification command passes** (`=== MVP FINAL VERIFICATION COMPLETE ===`):

  ```bash
  cd <repo>/frontend && echo "=== UI - Type Check ===" && pnpm --filter @pilot/ui check-types && echo "=== Web - Type Check ===" && pnpm --filter web check-types && echo "=== Mobile - Type Check ===" && pnpm --filter mobile build && echo "=== UI - Lint ===" && pnpm --filter @pilot/ui lint && echo "=== Web - Lint ===" && pnpm --filter web lint && echo "=== Mobile - Lint ===" && pnpm --filter mobile lint && echo "=== TYPE+LINT PASS ===" && echo "=== UI - Tests ===" && pnpm --filter @pilot/ui test 2>&1 | tail -6 && echo "=== Web - Tests ===" && pnpm --filter web test 2>&1 | tail -6 && echo "=== Mobile - Tests ===" && pnpm --filter mobile test 2>&1 | tail -8 && echo "=== MVP FINAL VERIFICATION COMPLETE ==="
  ```

- [ ] Final test count (before → after) documented in the launch-plan tracker
- [ ] Completion Summary added to `pilot-launch-plan.md` §SIGNUP-GA-B1

---

## Completion Summary

After all Definition of Done items are complete, add a **Completion Summary** subsection to `pilot-launch-plan.md` using this format:

### SIGNUP-GA-B1 (Part B — FE) — Signup Wizard State-Machine Guard Alignment: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot React Engineer
**Baseline**: X passed, Y failed (web)
**Final**: X+N passed, 0 failed (+N new tests)

#### What Was Accomplished

- Root cause: an off-by-one state-machine **model conflict** — the FE page guards + `signupStateToStep` + MSW encoded "Model A" (`stepN` = on page N) while the authoritative backend uses "Model B" (`stepN` = step N done, on page N+1). Consolidated the FE onto Model B.
- Fixed the reported `/signup/legal` bounce and the identical off-by-one in the phone/plan/ready guards and the account resume guard.
- Corrected the MSW `PUT /stepN` handlers from double-jump to single-step, so tests now exercise the real contract.
- Wired the legal "Welcome back, {owner_first_name}" banner to the field Part A now returns in `collected_data` (MVP personalization).

#### Files Changed / Created

| File | Action |
|---|---|
| `frontend/apps/web/src/features/signup/types.ts` | Updated — `signupStateToStep` → Model B; exported shared `stateOrder`/`stepToUrl` |
| `frontend/apps/web/src/app/signup/legal/page.tsx` | Updated — canonical guard; bounce fixed |
| `frontend/apps/web/src/app/signup/phone/page.tsx` | Updated — canonical guard |
| `frontend/apps/web/src/app/signup/plan/page.tsx` | Updated — canonical guard |
| `frontend/apps/web/src/app/signup/ready/page.tsx` | Updated — canonical guard (+ complete special-case retained) |
| `frontend/apps/web/src/app/signup/account/page.tsx` | Updated — resume guard forwards to correct page |
| `frontend/apps/web/src/mocks/handlers/signupHandlers.ts` | Updated — single-step transitions |
| `frontend/apps/web/src/app/signup/legal/page.tsx` | Updated — "Welcome back, {name}" banner populated (STEP 6) |
| `frontend/apps/web/src/features/signup/hooks/useSignupWizard.ts` | Updated — internally consistent with corrected map |

#### Tests Added

| Test File | Type | Tests | All Pass |
|---|---|---|---|
| `apps/web/src/__tests__/batch_signup_ga_b1/signup_state_machine.integration.test.tsx` | Integration | N | ✅ |
