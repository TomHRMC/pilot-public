# Implementation Prompt: SIGNUP-GA-1-FE — Self-Serve Credential Creation (Web Signup + Amplify SignUp)

**Mode**: Pilot React Engineer
**Batch**: SIGNUP-GA-1-FE
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §2.3 row 14a
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-signup-ga-1-design.md` (v2.0 — §A.2, §D, §H)
**Reference**: `dev-docs/devops/aws-cognito-testing.md` §1 (the exact self-sign-up flow this UI drives)
**Estimated session**: 4–6 hours
**Platform**: Web only (`apps/web`)
**Backend companion**: **SIGNUP-GA-1 backend + DevOps — both COMPLETE.** The Post-Confirmation Lambda 3-path router is deployed and Cognito self-sign-up is live. Your job is the client half: collect a password, call Cognito `SignUp`, confirm the email code, then hand off to the existing wizard.

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-react-engineer/react-engineer-rules.md`** — in full
- **`dev-docs/architecture-design/batch-designs/batch-signup-ga-1-design.md`** — §A.2 (the 4 user types / 3 Lambda paths — this UI drives **Path 3**), §D (the `/signup` contract change), §H (handoff)
- **`dev-docs/devops/aws-cognito-testing.md`** — §1 "How the Self-Sign-Up Flow Works" — the 4-step SignUp → confirm → Lambda → RDS flow your UI initiates

Critical rules for this batch:

- **Rule 1.1 / 1.2**: Verify every endpoint in `backend/openapi_schema_map.md` before writing a hook. The only backend endpoint here is the **existing** `POST /api/v1/signup` (behavior changed, path unchanged). Do NOT invent new endpoints — credential creation is a **Cognito** call, not a backend call.
- **Rule 1.3**: Run `pnpm sync-api-types` first — the `/signup` response gained `credential_pending`. Consume it from `@pilot/shared-types`, do not hand-edit the local `features/signup/types.ts` shape without reconciling.
- **Rule 2**: All `/api/v1/...` calls use `apiClient` from `@pilot/shared-api`. `fetch()` is banned.
- **Rule 8 (no new deps)**: `aws-amplify` is **already installed** (used by `AuthProvider`, `LoginForm`). Do NOT add any auth library. Cognito `SignUp`/`confirmSignUp` come from `aws-amplify/auth` via **dynamic import**, exactly the pattern in `AuthProvider.tsx` (`const { signIn } = await import("aws-amplify/auth")`).
- **Rule 9**: Route files (`app/signup/*/page.tsx`) — note these signup pages are **already `"use client"`** and live **outside** the `(authed)` group (no JWT guard). Keep them client components; that is correct for the pre-login account-birth flow (rules §35's "no tenant data in Server Components" is about authenticated data — the public signup step is fine client-side).
- **Rule 10**: Fix every failing test before done — no "pre-existing" exception without Tom's OK.
- **Rule 15 (WCAG 2.2 AA)**: This is an **authentication surface** — Accessible Authentication is mandatory: **allow paste** on the password and verification-code fields, ≥24px targets, non-color-only errors, focus-visible rings. The existing account page already models the error pattern (`aria-invalid` + `aria-describedby` + `role="alert"`) — match it.

---

## Design Decisions (Do Not Re-Litigate)

From the design doc §A.2 / ADR-0011 — these are final:

| Decision | Outcome | Rationale |
|---|---|---|
| Where the credential is created | **Cognito `SignUp` (client-side via Amplify)** — never a backend call | ADR-0011: password never touches our servers; no backend Cognito IAM |
| Flow ordering | **Cognito `SignUp` + email confirm FIRST, then `POST /api/v1/signup`** | Makes the Lambda's Path 3 run first so the wizard's resolve-or-attach hits the normal "tenant already exists" path (design §D case 1) |
| What creates the tenant | The **Post-Confirmation Lambda (Path 3)** on email confirmation — NOT the wizard | The wizard step 1 now **resolves-or-attaches by email** and overwrites the placeholder tenant name with `business_name` |
| Password field placement | **On `/signup/account`** (add to the existing form) | Lowest-friction — one screen collects business + owner + password; matches the design's "wizard keeps business_name where it already lives" |
| Email verification UX | **A new confirm-code step** between account submit and the wizard | Cognito returns `UserConfirmed: false` + emails a 6-digit code; the user must `ConfirmSignUp` before the Lambda fires |
| Getting a JWT for wizard steps 2–5 | **Auto-`signIn` after successful `ConfirmSignUp`** using the email+password just collected | Wizard steps 2–5 are JWT-gated; the user must be authenticated before `/signup/legal` |
| Types source | Backend payload types from `@pilot/shared-types` after `pnpm sync-api-types`; Cognito step types from `aws-amplify/auth` | Rule 1.3 |

> **Do NOT** build a backend endpoint for password/credential creation. **Do NOT** re-enable any Hosted UI. **Do NOT** create a second tenant client-side — the Lambda owns tenant creation.

---

## Context: What This Batch Does

Today, `/signup/account` collects business + owner fields and POSTs `/api/v1/signup` — with **no password and no Cognito account** (Gap G1). A user completes the wizard but has no way to log in. This batch closes that:

| Change | File(s) |
|---|---|
| Add a **password** (+ confirm) field to the account form; add Zod validation matching the Cognito policy (min 12, upper/lower/number/symbol) | `app/signup/account/page.tsx` (or extract to a feature component) |
| On submit: call **Cognito `SignUp`** (email + password) BEFORE `/api/v1/signup` | new hook `features/signup/hooks/useCognitoSignUp.ts` |
| New **email-verification step** — user enters the 6-digit code → **`ConfirmSignUp`** → **auto-`signIn`** → then `POST /api/v1/signup` → `/signup/legal` | new page `app/signup/verify/page.tsx` + component |
| Handle Cognito errors (UsernameExistsException, CodeMismatchException, ExpiredCodeException, resend code) as field/inline errors | verify component + account form |
| Consume the new `/signup` `credential_pending` response field | `features/signup/types.ts` reconciled with `@pilot/shared-types` |

The 5 wizard steps after account (legal → phone → plan → ready) are **unchanged** — they already assume an authenticated session; your auto-sign-in makes that true for the self-serve path.

---

## Pre-Work: Establish Regression Baseline

```bash
cd <repo>/frontend
pnpm --filter web test 2>&1 | tail -6
```
Record the exact count. Fix any pre-existing failure (or confirm with Tom) before starting.

## Pre-Work: Sync API Types

```bash
cd <repo>/frontend
pnpm sync-api-types
```
This regenerates `packages/shared-types/src/api-schema.d.ts` from the live backend (the SIGNUP-GA-1 backend batch changed the `/signup` response to include `credential_pending`). Consume via:
```typescript
import type { components } from "@pilot/shared-types";
// find the signup response schema name in api-schema.d.ts after sync
```

## Pre-Work: Verify Endpoints

```bash
grep -A 8 "\"/api/v1/signup\"" backend/openapi_schema_map.md
```
Confirm `POST /api/v1/signup` exists and note its response fields (expect `tenant_id`, `signup_state`, `owner_email`, and the new `credential_pending`). **If it's missing → STOP and ask Tom** — the backend batch must be merged + OpenAPI regenerated first.

| Call | Endpoint / API | Verified |
|---|---|---|
| initiate signup (resolve-or-attach) | `POST /api/v1/signup` (existing) | ☐ confirm in `openapi_schema_map.md` |
| create credential | **Cognito `signUp`** (`aws-amplify/auth`) — not a backend endpoint | n/a |
| confirm email | **Cognito `confirmSignUp`** (`aws-amplify/auth`) | n/a |
| auto login | `signIn` from `useAuth()` (already exists) | ✅ |

## Pre-Work: Read These Source Files

```
frontend/apps/web/src/app/signup/account/page.tsx        ← the form you extend (add password + reorder submit)
frontend/apps/web/src/app/signup/legal/page.tsx          ← the step you hand off to (JWT-gated — needs the auto-signIn)
frontend/apps/web/src/features/signup/types.ts           ← SignupInitiateRequest/Response (reconcile credential_pending)
frontend/apps/web/src/features/signup/components/WizardProgressBar.tsx  ← add the verify step to the progress UI if present
frontend/packages/ui/src/auth/AuthProvider.tsx           ← the dynamic-import Amplify pattern (signIn) to mirror for signUp/confirmSignUp
frontend/packages/ui/src/auth/types.ts                   ← AuthContextValue: has signIn, NOT signUp — you call Amplify directly for signUp/confirm
frontend/apps/web/src/features/login/components/LoginForm.tsx  ← password field + error-as-notification pattern reference
frontend/apps/web/src/lib/amplify-config.ts              ← confirm Amplify is configured (pool/client) before any auth call
frontend/apps/web/src/mocks/handlers/signupHandlers.ts   ← existing MSW signup handlers to extend
frontend/apps/web/src/mocks/handlers/index.ts            ← register any new/updated handlers here
```

Then locate related files:
```bash
grep -rn "import(\"aws-amplify/auth\")" frontend/apps/web/src frontend/packages/ui/src
grep -n "signUp\|confirmSignUp\|resendSignUpCode" frontend/packages/ui/src/auth/*.ts*
find frontend/apps/web/src/app/signup -name "page.tsx"
```

---

## STEP 1 — Add password fields + Zod validation to the account form

> Read `app/signup/account/page.tsx` first. It currently uses local `useState` + a hand-rolled `validate()`. You may either (a) add password inline in the same pattern, or (b) refactor to React Hook Form + Zod (preferred per rules §34). If you refactor, preserve every existing field, `data-testid`, and the duplicate-email inline error + "Sign in instead" link.

- Add **`password`** and **`confirm_password`** fields (both `type="password"`, `autoComplete="new-password"`, **paste allowed** — do not block paste, WCAG §36).
- Zod schema for the password (mirror the Cognito pool policy from `aws-cognito-testing.md` §4 / `aws-cognito-prod-setup.md` Step 3): **min 12 chars, ≥1 upper, ≥1 lower, ≥1 number, ≥1 symbol**, and `confirm_password` must match. Use Zod v4 idioms (`z.string().min(12,...)`, `.refine()` for the match; top-level `z.email()` for the email field).
- Surface password rules as helper text (not color-only) so the user knows the policy before submitting.
- **Do NOT POST `/api/v1/signup` from this page anymore.** Instead, on valid submit, this page now (STEP 2) calls Cognito `SignUp` and routes to `/signup/verify`. Keep the business/owner fields in `sessionStorage` (or pass via the wizard machine) so the verify step can complete `/api/v1/signup` after confirmation. **Never store the password in `sessionStorage`** — hold it only in memory (React state / navigation state) for the auto-sign-in; if a full reload happens on the verify page, prompt the user to sign in manually instead of persisting the password.

Intermediate check after this step:
```bash
pnpm --filter web test -- apps/web/src/app/signup 2>&1 | tail -10
```

## STEP 2 — `useCognitoSignUp` hook (Amplify SignUp)

Create `features/signup/hooks/useCognitoSignUp.ts`. Mirror the dynamic-import pattern from `AuthProvider.tsx` — **do not** add a static `aws-amplify` import at module top (keeps it out of SSR bundle):

```typescript
// Starting point — adjust to the actual Amplify v6 API you find. Verify against the installed aws-amplify version.
export function useCognitoSignUp() {
  return useMutation({
    mutationFn: async ({ email, password }: { email: string; password: string }) => {
      const { signUp } = await import("aws-amplify/auth");
      const res = await signUp({
        username: email,
        password,
        options: { userAttributes: { email } },
      });
      return res; // { isSignUpComplete, userId, nextStep }
    },
  });
}
```

- On success (`nextStep.signUpStep === "CONFIRM_SIGN_UP"`), navigate to `/signup/verify` carrying the email (and hold the password in memory for auto-sign-in).
- Map `UsernameExistsException` → the existing inline "An account with this email already exists." + "Sign in instead" link (reuse the account page's `email_duplicate` pattern). This is the **same UX** the current 409 path uses.
- **Mock mode**: when `NEXT_PUBLIC_USE_MOCK_AUTH === "true"`, `Amplify.configure` has no real pool. Guard the hook so mock mode short-circuits to a fake "confirm" step (mirror how `AuthProvider` handles `isMockMode`) so local dev + tests don't hit real Cognito.

## STEP 3 — `/signup/verify` email-confirmation step

Create `app/signup/verify/page.tsx` (client, outside `(authed)`) + `features/signup/components/VerifyEmailStep.tsx`.

- 6-digit code input (`inputMode="numeric"`, `autoComplete="one-time-code"`, **paste allowed**).
- On submit → `confirmSignUp({ username: email, confirmationCode })` (dynamic import). On success:
  1. **Auto-sign-in**: call `signIn(email, password)` from `useAuth()` (the password held in memory). Handle the MFA `nextStep` shape defensively — for a brand-new self-serve owner there is no MFA yet, so expect `signInStep === "DONE"`; if a non-DONE step ever returns, route to `/login` with a friendly message rather than crashing.
  2. **Then** `POST /api/v1/signup` with the business/owner fields (now authenticated) → persist `tenant_id` to `sessionStorage` (`WIZARD_TENANT_ID_KEY`) exactly as the account page does today → `router.push("/signup/legal")`.
- **Resend code**: button calling `resendSignUpCode({ username: email })` with a 30–60s cooldown; announce success via the notification queue.
- Error mapping (inline, non-color-only): `CodeMismatchException` → "That code doesn't match. Check your email and try again."; `ExpiredCodeException` → "That code expired. Request a new one." (surface the resend button); `LimitExceededException` → "Too many attempts. Wait a minute and try again."
- If the user hard-reloads `/signup/verify` and the in-memory password is gone: still allow entering the code + confirm, but after `ConfirmSignUp` route to `/login?confirmed=true` (they log in manually) instead of auto-sign-in. Do not persist the password to survive reload.

> The Lambda's Path 3 fires on `ConfirmSignUp`, creating the tenant with the placeholder name. Your subsequent `POST /api/v1/signup` is the **resolve-or-attach** call that overwrites the placeholder with `business_name` (design §D). This ordering is why confirm precedes the backend POST.

Intermediate check:
```bash
pnpm --filter web test -- apps/web/src/app/signup 2>&1 | tail -10
```

## STEP 4 — Reconcile signup types + progress bar

- After `pnpm sync-api-types`, update `features/signup/types.ts` `SignupInitiateResponse` to include `credential_pending: boolean` (or re-export the generated type). If the account page reads it, branch: `credential_pending === true` should not normally occur in the confirm-first flow, but if it does (edge race), keep the user on a "we're finishing setting up your account" state and retry the wizard resolve, rather than erroring.
- If `WizardProgressBar` enumerates steps, add the **verify** step between account and legal so the progress UI reflects reality. Read the component first.

## MSW Handlers

The `/api/v1/signup` handler already exists in `signupHandlers.ts`. Update its POST response to include `credential_pending: false`. **Cognito calls are not HTTP to our API** — they're Amplify SDK calls, so MSW does not intercept them; instead your `useCognitoSignUp` hook and the verify component must be **mock-mode aware** (STEP 2) OR you mock `aws-amplify/auth` in tests (see Test Requirements). Register any new/changed handler in `mocks/handlers/index.ts`.

---

## Test Requirements

Web — Vitest + `@testing-library/react`. Domain: signup/onboarding.

**Mock `aws-amplify/auth` in tests** (it's a dynamic import — mock the module):
```typescript
vi.mock("aws-amplify/auth", () => ({
  signUp: vi.fn().mockResolvedValue({ isSignUpComplete: false, nextStep: { signUpStep: "CONFIRM_SIGN_UP" } }),
  confirmSignUp: vi.fn().mockResolvedValue({ isSignUpComplete: true }),
  resendSignUpCode: vi.fn().mockResolvedValue({}),
  signIn: vi.fn().mockResolvedValue({ nextStep: { signInStep: "DONE" } }),
}));
```
Also mock `next/navigation` (`useRouter`, `useSearchParams`) per the inclusion §8.1 pattern.

Use `retry: false` on every test QueryClient; use MSW (`setupServer`) for the `/api/v1/signup` HTTP call; `server.resetHandlers()` in `afterEach`. Never mock `apiClient` directly.

**Unit tests:**
- `useCognitoSignUp` — calls Amplify `signUp` with `{ username: email, password, options.userAttributes.email }`; surfaces `UsernameExistsException` as the duplicate error; mock-mode short-circuit works.
- Account form — password-policy Zod validation (rejects <12 chars / missing symbol; confirms match); does **not** POST `/api/v1/signup` on submit (asserts Cognito `signUp` is called instead); paste is allowed on password.
- `VerifyEmailStep` — `confirmSignUp` on submit; on success calls `signIn` then POSTs `/api/v1/signup` then routes to `/signup/legal`; `CodeMismatchException` renders the inline error; resend calls `resendSignUpCode`.

**Integration test** (`apps/web/src/__tests__/batch_signup_ga_1/signup_flow.integration.test.tsx`):
1. Account page renders (no 404); filling valid fields + password → submitting calls Amplify `signUp` and navigates to verify (assert `signUp` mock called + router.push `/signup/verify`).
2. Verify page: entering a code → `confirmSignUp` + `signIn` called, then `POST /api/v1/signup` fires (assert via MSW handler capturing the request body has `business_name`), then routes to `/signup/legal`.
3. Duplicate email (`UsernameExistsException`) shows the inline "already exists" + "Sign in instead" link.
4. WCAG spot: password + code inputs allow paste; errors are `role="alert"` with `aria-invalid` (not color-only).

Assert by specific content/IDs, never by total counts.

---

## Final Verification

### Phase 1 — Targeted (during development)
```bash
cd <repo>/frontend
pnpm --filter web test -- apps/web/src/app/signup 2>&1 | tail -10
pnpm --filter web test -- apps/web/src/__tests__/batch_signup_ga_1/ 2>&1 | tail -10
```
> ❌ Never use `npx vitest run` — only `pnpm --filter web test`.

### Phase 2 — Full verification (once, at the end)
```bash
cd <repo>/frontend && echo "=== UI - Type Check ===" && pnpm --filter @pilot/ui check-types && echo "=== Web - Type Check ===" && pnpm --filter web check-types && echo "=== Mobile - Type Check ===" && pnpm --filter mobile build && echo "=== UI - Lint ===" && pnpm --filter @pilot/ui lint && echo "=== Web - Lint ===" && pnpm --filter web lint && echo "=== Mobile - Lint ===" && pnpm --filter mobile lint && echo "=== TYPE+LINT PASS ===" && echo "=== UI - Tests ===" && pnpm --filter @pilot/ui test 2>&1 | tail -6 && echo "=== Web - Tests ===" && pnpm --filter web test 2>&1 | tail -6 && echo "=== Mobile - Tests ===" && pnpm --filter mobile test 2>&1 | tail -8 && echo "=== MVP FINAL VERIFICATION COMPLETE ==="
```

> Any failure in either phase must be fixed before done — no "pre-existing" exception without Tom's written OK.

---

## Definition of Done — SIGNUP-GA-1-FE

Update the launch plan §2.3 SIGNUP-GA-1 card when each item is done:

- [ ] Regression baseline captured (zero pre-existing web failures, or confirmed with Tom)
- [ ] `pnpm sync-api-types` run — `/signup` `credential_pending` present; no new type errors
- [ ] Design doc §A.2/§D + `aws-cognito-testing.md §1` read before coding
- [ ] All mandatory source files read
- [ ] `POST /api/v1/signup` verified in `openapi_schema_map.md`
- [ ] **STEP 1**: password + confirm fields added with Zod policy validation (min 12 / classes / match); paste allowed; helper text non-color-only
- [ ] **STEP 2**: `useCognitoSignUp` calls Amplify `signUp` (dynamic import); UsernameExists → inline duplicate error; mock-mode short-circuit
- [ ] **STEP 3**: `/signup/verify` — `confirmSignUp` → auto `signIn` → `POST /api/v1/signup` → `/signup/legal`; resend + code errors handled; hard-reload fallback to `/login?confirmed=true`
- [ ] **STEP 4**: signup types reconciled with `@pilot/shared-types` (`credential_pending`); progress bar includes verify step
- [ ] Password never written to `sessionStorage` (in-memory only)
- [ ] No new npm dependency added (`aws-amplify` already present)
- [ ] No hand-written `useMemo`/`useCallback` for perf; components pure (React Compiler §32)
- [ ] Hooks use TanStack Query v5 object-form; Zod v4 idioms (§33–§34)
- [ ] Signup pages remain client components outside `(authed)` (correct for pre-login)
- [ ] WCAG 2.2 AA: paste allowed on auth/code inputs, ≥24px targets, focus-visible, non-color-only errors; axe-core clean
- [ ] MSW `/signup` handler returns `credential_pending`; any new handler registered in `index.ts`
- [ ] Unit tests pass (hook + account form + verify step)
- [ ] Integration test passes in `__tests__/batch_signup_ga_1/`
- [ ] **Phase 2 FULL verification passes** (`=== MVP FINAL VERIFICATION COMPLETE ===`)
- [ ] Final test count (before → after) documented
- [ ] Completion Summary added to launch plan §2.3

---

## Completion Summary

Add to `pilot-launch-plan.md` §2.3 (SIGNUP-GA-1 card):

```markdown
### SIGNUP-GA-1-FE — Self-Serve Credential Creation (Web): Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot React Engineer
**Baseline**: X passed (web)
**Final**: X+N passed (+N new tests)

#### What Was Accomplished
- Password field + Cognito policy validation on /signup/account
- useCognitoSignUp (Amplify signUp) + /signup/verify email-confirmation step
- Auto-signIn after confirm → POST /api/v1/signup (resolve-or-attach) → wizard
- credential_pending consumed from @pilot/shared-types

#### Files Changed / Created
| File | Action |
|---|---|
| `apps/web/src/app/signup/account/page.tsx` | Updated — password fields + Cognito SignUp on submit |
| `apps/web/src/app/signup/verify/page.tsx` | Created — email code confirm + auto-signIn |
| `apps/web/src/features/signup/hooks/useCognitoSignUp.ts` | Created |
| `apps/web/src/features/signup/components/VerifyEmailStep.tsx` | Created |
| ... | ... |

#### Tests Added
| Test File | Type | Tests | All Pass |
|---|---|---|---|
| `apps/web/src/__tests__/batch_signup_ga_1/signup_flow.integration.test.tsx` | Integration | N | ✅ |
| `features/signup/hooks/__tests__/useCognitoSignUp.test.ts` | Unit | N | ✅ |
```

---

## After This Task — Next Step

This closes the **web** self-serve credential path. A **mobile** counterpart (Expo `SignUp` on the RN signup screen) is a separate follow-on if/when mobile self-serve is in scope. Once web is verified end-to-end against the live pool (use the manual flow in `aws-cognito-testing.md §2`), the Architect moves Gap G1 out of `pilot-founder-onboarding-process.md §10`.
