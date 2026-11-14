# Implementation Prompt: TEAM-INVITE-2 — Invite-Landing Accept Flow (Password + Verify + Land-in-Tenant)

**Mode**: Pilot React Engineer
**Batch**: TEAM-INVITE-2
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §1.1 Ord 27 + §3.27
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-team-invite-2-design.md` (§A–§I — read every section)
**Estimated session**: ~2.5 hours
**Platform**: Web only (`apps/web`)
**Pure frontend — no backend changes needed** (no new endpoints, no DB, no OpenAPI diff)

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-react-engineer/react-engineer-rules.md`** — in full
- **`dev-docs/architecture-design/batch-designs/batch-team-invite-2-design.md`** — every section (A–I)

Critical rules for this batch:

- **Rule 1.1/1.2**: The only Pilot API endpoint this batch consumes is `GET /api/v1/invites/{token}` (already live, TEAM-INVITE-1). Do NOT invent any other URL. **The invite flow must NEVER call `POST /api/v1/signup`** — that is the owner Path 3 provisioner; the Lambda Path 2 attach fires at Cognito `ConfirmSignUp` (design §G.2).
- **Rule 2**: `apiClient` for `/api/v1/...` calls — with the one sanctioned exception already on this surface: the public landing fetch uses bare `fetch()` (unauthenticated-surface precedent, PublicQuotePage). That exception covers ONLY the existing `GET /api/v1/invites/{token}` call. No new bare-fetch calls.
- **Rule 7**: Check `packages/ui/src/index.ts` before creating any component — this batch needs **no** new shared components (verify, don't assume).
- **Rule 8**: No new npm dependencies. Everything needed (`react-hook-form`, `zod`, `@hookform/resolvers`, `@heroicons/react`, `aws-amplify`, `@tanstack/react-query`) is already installed — verify with `grep` against `apps/web/package.json`.
- **Rule 10**: If ANY test fails during your work — even a pre-existing one — fix it before declaring done. **Known upfront**: the Part B test `apps/web/src/__tests__/batch_team_invite_1/invite-landing.integration.test.tsx` asserts the OLD `invite-signup-cta` link that STEP 3 deletes — updating it is part of this batch (STEP 3).
- **Rule 11 (React Compiler)**: No hand-written `useMemo`/`useCallback`/`React.memo` for render-perf. Keep components pure.
- **Rule 13 (Zod v4 + RHF)**: `zodResolver`, top-level helpers, unified `error` param. Zod validates form input only.
- **Rule 15 (WCAG 2.2 AA)**: This is an **auth surface** — paste MUST work on password + code inputs (Accessible Authentication); read-only email displayed beside the form (Redundant Entry 3.3.7); ≥44 px primary targets; `aria-invalid` + `aria-describedby` non-color-only errors; visible password-policy hint.

## Design Decisions (Do Not Re-Litigate)

From Design Doc §G — these decisions are final:

| Decision | Outcome | Rationale |
|---|---|---|
| Where the accept form lives | On the `/invite/[token]` landing page (Option A) | §G.8 — zero regression risk to the owner `/signup` wizard days before founder onboarding; Tom green-lit Option A |
| Post-confirm destination | **Role-branched**: `office_staff`/`accountant`/`owner` → auto-`signIn` → `router.replace("/dashboard")`; `technician`/`null` → terminal "open the mobile app" panel, **no web sign-in** | §G.1 — technicians are deliberately blocked from web post-login (`usePostLoginRedirect.ts`) |
| `POST /api/v1/signup` from this flow | **Banned** | §G.2 — Lambda Path 2 attaches at `ConfirmSignUp`; the owner provisioner would create a stray business |
| Password schema | **Duplicated** into `InviteAcceptForm` with cross-ref comments both directions | §G.5 — do NOT extract a shared module (touches owner wizard) |
| Reload between signUp and confirm | Self-heals — re-submitting the form re-`signUp`s the unconfirmed Cognito user and re-sends the code | §G.3 — no recovery UI |
| `UsernameExistsException` | Inline error + "Sign in instead" link to `/login?email={email}` | §G.4 |
| `signInStep !== "DONE"` | Defensive route to `/login?confirmed=true&email={email}` | §G.6 |
| Designer-spec gate | **WAIVED by Tom 2026-09-03** — design §H/§I are the surface spec | §G.7 |

## Pre-Work: Establish Regression Baseline

Before touching any file:

```bash
cd <repo>/frontend
pnpm --filter web test 2>&1 | tail -5
```

Record the exact counts (Part B close: **2236 passed**). These must still pass at the end (plus your new tests). If anything is already failing → confirm with Tom before proceeding.

## Pre-Work: Sync API Types

```bash
cd <repo>/frontend
pnpm sync-api-types
```

No diff is expected (this batch adds no endpoints). If a diff appears, it is pre-existing drift — note it and continue; do not commit unrelated type changes.

## Pre-Work: Verify Endpoints

```bash
grep -B 2 -A 8 "invites/{token}" backend/openapi_schema_map.md
```

| Consumed call | Endpoint | Verified |
|---|---|---|
| Landing fetch (existing) | `GET /api/v1/invites/{token}` — public, uniform 404 | ✅ Live since TEAM-INVITE-1; confirm in map |

No new hooks against the API are created (`useCognitoSignUp` is Cognito-only). **If you find yourself wanting any other endpoint → STOP and ask Tom.**

## Pre-Work: Read These Source Files

Read each with `read_file` before writing any code:

- `frontend/apps/web/src/features/users/components/InviteLandingPage.tsx` ← the component you are modifying; note the RULE 1/RULE 2 header comments and the exact CTA block at lines 204–217
- `frontend/apps/web/src/features/signup/hooks/useCognitoSignUp.ts` ← reuse target: `{email, password}` mutation, mock-mode short-circuit, typed `CognitoSignUpError`
- `frontend/apps/web/src/features/signup/components/VerifyEmailStep.tsx` ← the confirm→signIn→route pattern to mirror (its `POST /api/v1/signup` step is the part you must NOT copy)
- `frontend/apps/web/src/features/signup/components/__tests__/VerifyEmailStep.test.tsx` ← test-mocking pattern for `aws-amplify/auth` + `useAuth` + `next/navigation`
- `frontend/apps/web/src/app/signup/account/page.tsx` (lines 63–101 + the eye-toggle markup) ← exact `passwordSchema` + reveal-toggle pattern
- `frontend/apps/web/src/mocks/handlers/teamInviteHandlers.ts` ← the fixtures you are extending (DEV_TOKEN block, lines ~101–102 + public handler, lines 264–281)
- `frontend/apps/web/src/mocks/handlers/index.ts` ← confirm `teamInviteHandlers` is registered (it is — verify, don't re-add)
- `frontend/apps/web/src/__tests__/batch_team_invite_1/invite-landing.integration.test.tsx` ← the Part B test you must update in STEP 3
- `frontend/packages/ui/src/index.ts` ← confirm no new shared component is needed

## MSW Handlers

No new handler file. STEP 4 extends the existing `teamInviteHandlers.ts` fixtures only — it is already registered in `mocks/handlers/index.ts`.

## Context: What This Batch Does

Tom's prod smoke found the invite landing page's **Create your account** CTA links to `/signup` — the **owner** onboarding wizard (business name, industry, plan). An invitee must instead create their account **on the landing page itself**: password + confirm → Cognito `SignUp` → 6-digit verification code → `ConfirmSignUp` (fires the Lambda Path 2 tenant-attach) → land in the tenant (office roles) or a mobile-app success panel (technician).

| # | Change | File |
|---|---|---|
| 1 | New accept form (email display + password/confirm + Zod + `useCognitoSignUp`) | `features/users/components/InviteAcceptForm.tsx` |
| 2 | New verify step (code + confirm + role-branched completion + resend) | `features/users/components/InviteVerifyStep.tsx` |
| 3 | Landing page orchestration; **delete** the `/signup` CTA; update the Part B test that asserts it | `features/users/components/InviteLandingPage.tsx`, `__tests__/batch_team_invite_1/invite-landing.integration.test.tsx` |
| 4 | MSW fixture: add an `office_staff` invite token | `mocks/handlers/teamInviteHandlers.ts` |
| 5 | Unit ×2 + integration tests | `__tests__/batch_team_invite_2/` + co-located `__tests__/` |

## STEP 1 — `InviteAcceptForm`

**Create** `frontend/apps/web/src/features/users/components/InviteAcceptForm.tsx` (`"use client"`).

Props (exact — from design §F):

```typescript
interface InviteAcceptFormProps {
  email: string;                            // display only — from the public invite fetch
  onSignedUp: (password: string) => void;   // advance to the verify phase
}
```

Requirements:

- **Zod schema** (Zod v4 + `zodResolver`): duplicate the `passwordSchema` from `signup/account/page.tsx` verbatim (min 12, ≥1 upper, ≥1 lower, ≥1 digit, ≥1 symbol) + confirm-password match refine. Add a cross-reference comment in BOTH files (`// TEAM-INVITE-2 §G.5: keep in sync with the copy in InviteAcceptForm.tsx` / vice-versa). Do NOT extract a shared module.
- **Email is display-only** — a labeled `<div>`/`<dd>` row, NOT an input (Redundant Entry is satisfied by prominent display; the invite already owns the email).
- **Password + confirm inputs**: `type` toggles with the eye-icon reveal pattern from the account page (`EyeIcon`/`EyeSlashIcon` from `@heroicons/react/24/outline`); `autoComplete="new-password"`; **paste must work** (never intercept `onPaste`); `aria-invalid` + `aria-describedby` on error; visible policy hint text under the password field ("At least 12 characters with upper, lower, number, and symbol").
- **Submit**: `useCognitoSignUp().mutateAsync({ email, password })` → on success call `onSignedUp(password)`. Button ≥44 px, full width, label **"Create your account"**, pending label **"Creating…"**.
- **Error mapping** (from `CognitoSignUpError.code`, inline + non-color-only):
  - `UsernameExistsException` → "An account already exists for **{email}**." + a **"Sign in instead"** link to `/login?email={encodeURIComponent(email)}` (design §G.4)
  - `InvalidPasswordException` → surface the Cognito message (should not occur — Zod pre-validates to pool policy)
  - `LimitExceededException` → "Too many attempts. Wait a minute and try again."
  - `unknown` → "Sign-up failed. Please try again."
- **Test IDs**: `invite-accept-form`, `invite-password-input`, `invite-confirm-password-input`, `invite-accept-submit`, `invite-accept-error`, `invite-signin-instead`.
- React Compiler: plain code, no hand memoization.

*Code examples in the design doc are starting points — read the referenced source files first and match what you find.*

## STEP 2 — `InviteVerifyStep`

**Create** `frontend/apps/web/src/features/users/components/InviteVerifyStep.tsx` (`"use client"`).

Props (exact — from design §F):

```typescript
interface InviteVerifyStepProps {
  email: string;
  password: string;                 // in-memory from the form step — never persisted
  roleCode: string | null;          // drives the §G.1 branch
}
```

Requirements (mirror `VerifyEmailStep.tsx` where noted — **never** its `POST /api/v1/signup` step):

- **Code input**: 6-digit, controlled; `inputMode="numeric"`, `autoComplete="one-time-code"`, paste allowed, `maxLength={6}`.
- **Confirm**: dynamic `const { confirmSignUp } = await import("aws-amplify/auth")` with the `isMockMode()` short-circuit guard copied from `VerifyEmailStep` (lines 135–143) so tests never hit real Cognito.
- **Error mapping**: identical codes + copy as `VerifyEmailStep` (`CodeMismatchException` → "That code doesn't match…", `ExpiredCodeException` → "That code expired. Request a new one.", `LimitExceededException` → "Too many attempts…", `UserNotFoundException` → "We couldn't find that account…", `unknown` → mapped message). Inline, non-color-only.
- **Resend**: `resendSignUpCode` (dynamic import, mock-guarded) + 30 s cooldown ticker mirroring `VerifyEmailStep` (`RESEND_COOLDOWN_SECONDS = 30`); success notification via `useNotificationQueue` ("A new code was sent to your email.").
- **On confirm success — role branch (design §G.1, exact)**:
  - `roleCode` is `"office_staff"` | `"accountant"` | `"owner"` → switch the button to **"Setting up your account…"**, then `const { nextStep } = await signIn(email, password)` via `useAuth()`:
    - `nextStep.signInStep === "DONE"` → `router.replace("/dashboard")`
    - otherwise → `router.replace("/login?confirmed=true&email={encodeURIComponent(email)}")` (§G.6 defensive)
  - `roleCode` is `"technician"` or `null` → **no sign-in**. Render the terminal panel (design §H State 3b): "You're in, **{email}**!" + "Open the Pilot mobile app and sign in with this email to get started." `data-testid="invite-joined-mobile"`.
- Note on the landing page's RULE 1 header comment ("NEVER calls useAuth()…"): the auth call lives HERE, inside the verify step, mirroring `VerifyEmailStep`. Do not add auth hooks to `InviteLandingPage` itself.
- **Test IDs**: `invite-verify-step`, `invite-code-input`, `invite-verify-submit`, `invite-verify-error`, `invite-resend-code`, `invite-joined-mobile`.

## STEP 3 — `InviteLandingPage` Orchestration + Part B Test Update

**Modify** `frontend/apps/web/src/features/users/components/InviteLandingPage.tsx`:

- Add the phase state (design §F):
  ```typescript
  type AcceptPhase = { step: "form" } | { step: "verify"; password: string };
  const [acceptPhase, setAcceptPhase] = useState<AcceptPhase>({ step: "form" });
  ```
- In the **valid** branch, replace the entire CTA block (lines 204–217: the `<a href="/signup">` + "Sign up with {email}" paragraph) with:
  - `acceptPhase.step === "form"` → `<InviteAcceptForm email={data.email} onSignedUp={(password) => setAcceptPhase({ step: "verify", password })} />`
  - `acceptPhase.step === "verify"` → `<InviteVerifyStep email={data.email} password={acceptPhase.password} roleCode={data.role_code} />`
- Keep the existing header/"You've been invited to join {tenant_name}"/email/role/expiry rows — they remain visible on both phases (the email row satisfies Redundant Entry).
- Loading / invalid / error states: **unchanged**.
- Keep the `role_code ?? "technician"` display fallback as-is.

**Update** `frontend/apps/web/src/__tests__/batch_team_invite_1/invite-landing.integration.test.tsx` (Rule 10 — it asserts the deleted CTA):

- The test `"valid token renders the join panel with tenant name, email, role, and CTA"` → replace the `invite-signup-cta` assertions with assertions that `invite-accept-form` + `invite-accept-submit` render and that `queryByTestId("invite-signup-cta")` is **null**.
- The 404/invalid and error tests need no changes.
- Do not weaken any other assertion.

**Intermediate verification** (after STEPs 1–3):

```bash
cd <repo>/frontend
pnpm --filter web test -- apps/web/src/__tests__/batch_team_invite_1/invite-landing.integration.test.tsx 2>&1 | tail -10
```

## STEP 4 — MSW Fixture Extension

**Modify** `frontend/apps/web/src/mocks/handlers/teamInviteHandlers.ts`:

- Add a second known token so both role branches are testable:
  ```typescript
  const DEV_TOKEN = "dev-invite-token-0001";          // existing — technician
  const DEV_TOKEN_OFFICE = "dev-invite-token-0002";   // new — office_staff
  ```
- Restructure the public `GET /api/v1/invites/:token` handler into a lookup over both tokens. `DEV_TOKEN` keeps its current payload (`newguy@pilot.local`, `technician`); `DEV_TOKEN_OFFICE` returns `{ tenant_name: "Pilot Dev Tenant", email: "sarah-office@pilot.local", role_code: "office_staff", expires_at: futureExpiry }`. Every other token keeps the uniform RFC 7807 404 (`invite_invalid`) — do not change that contract.
- Verify `teamInviteHandlers` remains registered in `mocks/handlers/index.ts` (it is — no barrel change needed).

## STEP 5 — Tests

Framework: Vitest + Testing Library (web). `retry: false` on every QueryClient. MSW `setupServer` with `server.resetHandlers()` in `afterEach`. Web assertions: `toBeInTheDocument()`. Mock `next/navigation` (`useRouter` → `{ push: vi.fn(), replace: mockReplace, back: vi.fn() }`). **Never mock `apiClient`** (none is used on this surface). Never assert counts — assert by testid/specific content.

**5a — Unit: `features/users/components/__tests__/InviteAcceptForm.test.tsx`**

- Renders the invited email + both password inputs + policy hint.
- Zod: rejects <12 chars / missing symbol (error text visible, submit does not call the mutation); rejects mismatched confirm.
- Happy path: valid passwords → submit → `onSignedUp` called with the password (mock mode short-circuits Cognito — no Amplify mock needed).
- `UsernameExistsException`: `vi.mock("@/features/signup/hooks/useCognitoSignUp")` with a controllable `mutateAsync` rejection (`new CognitoSignUpError("UsernameExistsException", "...")` — import the real error class) → `invite-signin-instead` link appears with `href="/login?email=..."`.
- Paste is not blocked: assert no `onPaste` handler prevents default (fireEvent.paste on the password input).

**5b — Unit: `features/users/components/__tests__/InviteVerifyStep.test.tsx`**

- Mock `aws-amplify/auth` (`confirmSignUp`, `resendSignUpCode`) + `@pilot/ui/auth` `useAuth` (`signIn` returning `{ nextStep: { signInStep: "DONE" } }`) — follow the `VerifyEmailStep.test.tsx` pattern.
- Office role (`office_staff`): enter code → submit → `confirmSignUp` called with `{ username: email, confirmationCode }` → `signIn` called with `(email, password)` → `mockReplace` called with `"/dashboard"`.
- Technician role: submit → `confirmSignUp` called → **no** `signIn` → `invite-joined-mobile` panel visible, no router call.
- `CodeMismatchException` → "That code doesn't match…" inline error.
- Resend: click `invite-resend-code` → `resendSignUpCode` called → cooldown text ("30") appears.
- Non-`DONE` signInStep → `mockReplace` called with `/login?confirmed=true&email=...`.

**5c — Integration: `apps/web/src/__tests__/batch_team_invite_2/invite-accept.integration.test.tsx`**

MSW default handlers already include the invites fixtures (STEP 4). Cover:

1. **Office flow end-to-end** (`/invite/dev-invite-token-0002` → render `<InviteLandingPage token="dev-invite-token-0002" />`): tenant name + email render → fill valid password/confirm → submit → `invite-verify-step` appears → enter `123456` → submit → `mockReplace("/dashboard")`.
2. **Technician flow** (`dev-invite-token-0001`): same through verify → `invite-joined-mobile` renders, email shown, **no** `mockReplace("/dashboard")`.
3. **Invalid token regression** (`garbage-token`): neutral "no longer valid" panel renders; `invite-accept-form` is absent; uniform 404 contract intact.
4. **No `/signup` anywhere**: after the valid page renders, `document.body.innerHTML` contains no `href="/signup"` (assert via `queryByRole("link", { name: /create your account/i })` being null + form present).

## Final Verification

> ❌ **BANNED COMMAND**: `npx vitest run` — never use it. Only `pnpm --filter web test` (full) or `pnpm --filter web test -- <path>` (targeted).

### Phase 1 — Targeted (after each STEP)

```bash
cd <repo>/frontend
pnpm --filter web test -- apps/web/src/features/users/components/__tests__/InviteAcceptForm.test.tsx 2>&1 | tail -10
pnpm --filter web test -- apps/web/src/features/users/components/__tests__/InviteVerifyStep.test.tsx 2>&1 | tail -10
pnpm --filter web test -- apps/web/src/__tests__/batch_team_invite_2/ 2>&1 | tail -10
pnpm --filter web test -- apps/web/src/__tests__/batch_team_invite_1/invite-landing.integration.test.tsx 2>&1 | tail -10
```

Fix any failure before moving on — including apparent pre-existing ones.

### Phase 2 — Full (once, at the end)

```bash
cd <repo>/frontend && echo "=== UI - Type Check ===" && pnpm --filter @pilot/ui check-types && echo "=== Web - Type Check ===" && pnpm --filter web check-types && echo "=== Mobile - Type Check ===" && pnpm --filter mobile build && echo "=== UI - Lint ===" && pnpm --filter @pilot/ui lint && echo "=== Web - Lint ===" && pnpm --filter web lint && echo "=== Mobile - Lint ===" && pnpm --filter mobile lint && echo "=== TYPE+LINT PASS ===" && echo "=== UI - Tests ===" && pnpm --filter @pilot/ui test 2>&1 | tail -6 && echo "=== Web - Tests ===" && pnpm --filter web test 2>&1 | tail -6 && echo "=== Mobile - Tests ===" && pnpm --filter mobile test 2>&1 | tail -8 && echo "=== MVP FINAL VERIFICATION COMPLETE ==="
```

Known benign warnings (do not chase): mobile `[apiClient] fetchAuthSession threw: ERR_VM_DYNAMIC_IMPORT_CALLBACK_MISSING_FLAG`; mobile Babel loose-mode warnings (inclusions §10.2).

## Definition of Done — TEAM-INVITE-2

Check off each item **in this prompt doc** as it completes:

- [ ] Pre-modification regression baseline captured (web: 2236 passed — or confirmed with Tom)
- [ ] `pnpm sync-api-types` run — no unexpected diff
- [ ] Design doc (§A–§I) fully read before writing any code
- [ ] All mandatory source files read before modifying
- [ ] `GET /api/v1/invites/{token}` verified in `openapi_schema_map.md`; **no other endpoint called**; `POST /api/v1/signup` never called
- [ ] **STEP 1**: `InviteAcceptForm.tsx` created — email display, duplicated passwordSchema + cross-ref comments, eye toggles, error mapping incl. `UsernameExistsException` → "Sign in instead"
- [ ] **STEP 2**: `InviteVerifyStep.tsx` created — confirm + error mapping + 30 s resend + role-branched completion (office → signIn → `/dashboard`; technician → `invite-joined-mobile`, no sign-in)
- [ ] **STEP 3**: `InviteLandingPage.tsx` — phase orchestration; `/signup` CTA block deleted; Part B landing test updated (no `invite-signup-cta` assertions remain)
- [ ] **STEP 4**: `teamInviteHandlers.ts` — `dev-invite-token-0002` (`office_staff`) added; uniform 404 contract unchanged; barrel registration verified untouched
- [ ] **STEP 5**: all three test files created and passing
- [ ] No `useAuth`/`RequireAuth`/`RoleGate` added to `InviteLandingPage` (auth call lives in `InviteVerifyStep` only)
- [ ] No hand-written `useMemo`/`useCallback`/`React.memo` (React Compiler); components pure
- [ ] Zod v4 + `zodResolver` on the accept form; paste works on password + code inputs; ≥44 px primary targets; `aria-invalid`/`aria-describedby` errors (WCAG 2.2 AA)
- [ ] No new npm dependencies; no new shared components in `packages/ui`; no new `PermissionKey`
- [ ] No regressions — Part B team-invite suites (`batch_team_invite_1/`) pass with the updated assertions
- [ ] Phase 1 targeted runs pass
- [ ] **Phase 2 FULL verification passes** (`=== MVP FINAL VERIFICATION COMPLETE ===`) — the exact command in the Final Verification section
- [ ] Final test count (before → after) documented in the Completion Summary appendix
- [ ] Completion Summary filled in at this prompt doc's ending `## Appendix — Completion Summary` (ADR-0017)

## Completion Summary

After all Definition of Done items are complete, fill in the appendix at the end of THIS prompt doc using this format:

```markdown
### TEAM-INVITE-2 — Invite-Landing Accept Flow: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot React Engineer
**Baseline**: 2236 passed (web)
**Final**: X+N passed (+N new tests)

#### What Was Accomplished
- …

#### Files Changed / Created
| File | Action |
|---|---|

#### Tests Added
| Test File | Type | Tests | All Pass |
|---|---|---|---|
```

## Handoff

When done: commit, and tell Tom the batch is ready for **web deploy + prod re-smoke** — the prod test plan (`dev-docs/testing-support/team-invite-1-prod-test-plan.md`) Tests 3–5 (landing render → SignUp → attach → login, incl. the technician mobile-panel path) now exercise this flow end-to-end. No backend deploy, no migration, no `sync-api-types` handoff is required (no endpoint changes).

---

## Appendix — Completion Summary

### TEAM-INVITE-2 — Invite-Landing Accept Flow: Completion Summary

**Completed**: 2026-09-03
**Mode**: Pilot React Engineer
**Baseline**: 2236 passed (web)
**Final**: 2256 passed (+20 new tests)

#### What Was Accomplished
- Replaced the broken `/signup` CTA link on the invite landing page with a full accept flow: password + confirm → Cognito `SignUp` → 6-digit verification code → `ConfirmSignUp` (fires Lambda Path 2 tenant-attach) → role-branched completion.
- Office roles (`office_staff`/`accountant`/`owner`) auto-sign-in and land in `/dashboard`; technicians (and `null` role) see a terminal "open the mobile app" panel with no web sign-in (per `usePostLoginRedirect.ts` technician block).
- `POST /api/v1/signup` is never called from this flow (design §G.2 — that is the owner Path 3 provisioner).
- Password schema duplicated (not extracted) with cross-reference comments in both `InviteAcceptForm.tsx` and `signup/account/page.tsx` (§G.5).
- WCAG 2.2 AA: paste works on password + code inputs; read-only email display (Redundant Entry 3.3.7); ≥44px primary targets; `aria-invalid`/`aria-describedby` non-color-only errors; visible password-policy hint.
- MSW fixture extended with `dev-invite-token-0002` (`office_staff`) for both role branches; uniform 404 contract unchanged.
- React Compiler: no hand-written `useMemo`/`useCallback`/`React.memo`; components are pure.

#### Files Changed / Created
| File | Action |
|---|---|
| `frontend/apps/web/src/features/users/components/InviteAcceptForm.tsx` | Created |
| `frontend/apps/web/src/features/users/components/InviteVerifyStep.tsx` | Created |
| `frontend/apps/web/src/features/users/components/InviteLandingPage.tsx` | Modified — phase orchestration; `/signup` CTA deleted |
| `frontend/apps/web/src/app/signup/account/page.tsx` | Modified — cross-ref comment added (§G.5) |
| `frontend/apps/web/src/mocks/handlers/teamInviteHandlers.ts` | Modified — `dev-invite-token-0002` office_staff fixture |
| `frontend/apps/web/src/__tests__/batch_team_invite_1/invite-landing.integration.test.tsx` | Modified — `invite-signup-cta` assertions replaced; `QueryClientProvider` wrapper added |
| `frontend/apps/web/src/features/users/components/__tests__/InviteAcceptForm.test.tsx` | Created |
| `frontend/apps/web/src/features/users/components/__tests__/InviteVerifyStep.test.tsx` | Created |
| `frontend/apps/web/src/__tests__/batch_team_invite_2/invite-accept.integration.test.tsx` | Created |

#### Tests Added
| Test File | Type | Tests | All Pass |
|---|---|---|---|
| `InviteAcceptForm.test.tsx` | Unit | 8 | ✅ |
| `InviteVerifyStep.test.tsx` | Unit | 8 | ✅ |
| `invite-accept.integration.test.tsx` | Integration | 4 | ✅ |
| **Total new** | | **20** | ✅ |

#### Verification
- Phase 1 targeted: all 23 new + updated tests pass
- Phase 2 full canonical: `=== MVP FINAL VERIFICATION COMPLETE ===`
  - UI: 685 passed · Web: 2256 passed · Mobile: 701 passed
  - Type checks: UI ✅ Web ✅ Mobile ✅
  - Lint: UI ✅ Web ✅ Mobile ✅ (zero warnings)
