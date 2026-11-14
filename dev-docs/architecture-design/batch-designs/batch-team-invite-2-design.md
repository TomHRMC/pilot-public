# Batch Design: TEAM-INVITE-2 — Invite-Landing Accept Flow (Password + Verify + Land-in-Tenant)

**Status**: ✅ Approved 2026-09-03 (Tom green-light in session: *"Yes — author the TEAM-INVITE-2 React prompt now"*)
**Author**: Pilot Architect
**Batch code**: TEAM-INVITE-2 (Phase 1, Ord 27)
**Platform**: Web only (`apps/web`) — pure frontend; **zero backend, zero DB, zero endpoint changes**
**Prompt**: `batch-team-invite-2-react-engr-prompt.md`
**Estimate**: ~2.5 h

---

## Defect Statement (Why This Batch Exists)

Tom's prod smoke of TEAM-INVITE-1 (2026-09-03): the invite email + landing page work, but the landing page's **Create your account** CTA is a plain link to `/signup` (`InviteLandingPage.tsx`) — the **tenant-owner onboarding wizard** (business name, industry, legal, phone, plan). An invitee is an *employee joining an existing tenant*; the wizard is the **Path 3 owner-provisioning flow** whose `VerifyEmailStep.tsx` calls `POST /api/v1/signup` (creates a NEW business + plan steps). Wrong questions, wrong provisioning path — hazardous, not merely confusing.

**Root cause (architect spec miss, faithfully implemented)**: TEAM-INVITE-1 design §H row 3 intended *"SignUp CTA (email prefilled, Cognito SignUp → verification → login → lands in tenant)"*, but the Part B prompt STEP 6 (line 191) instructed *"verify whether `features/signup` supports an email query-param prefill; if yes use `/signup?email=`, **if not link `/signup`**"*. No invite-scoped account-creation step existed to link to, and the prefill-fallback masked that gap. The engineer executed the prompt exactly as written. This batch builds the missing step.

**Backend is already correct and complete**: `GET /api/v1/invites/{token}` (public, uniform 404) serves the landing page; the Post-Confirmation Lambda **Path 2** attaches *any* Cognito self-`SignUp` whose email matches a pending invite (email-keyed, UI-agnostic). This batch is frontend-only.

---

## A. Input Read Summary

| Input | What it contributed |
|---|---|
| `frontend/react-engr-std-prompt-inclusions.md` (full re-read, 1002 lines, per Rule 9.1) | Prompt section order + mandatory gates |
| `InviteLandingPage.tsx` (full, 225 lines) | Current 4-state component; exact CTA block being replaced (lines 204–217); bare-`fetch()` public-surface pattern |
| `app/invite/[token]/page.tsx` (full, 31 lines) | Thin server shell — **untouched** by this batch |
| `useCognitoSignUp.ts` (full, 113 lines) | Reuse-as-is: `{email, password}` mutation, mock-mode short-circuit, typed `CognitoSignUpError` (`UsernameExistsException`/`InvalidPasswordException`/`LimitExceededException`/`unknown`) |
| `VerifyEmailStep.tsx` (lines 1–240) | Confirm→signIn→route pattern to mirror — **minus** its `POST /api/v1/signup` step; error mapping table; resend cooldown (30 s); `isMockMode()` guard; non-`DONE` signInStep defensive fallback |
| `signup/account/page.tsx` (lines 1–120) | Exact `passwordSchema` (min 12 / upper / lower / digit / symbol + confirm refine); eye-toggle pattern (`EyeIcon`/`EyeSlashIcon` from `@heroicons/react/24/outline`) |
| `login/page.tsx` (lines 1–50) | Already-authenticated → `/dashboard`; banner query-param convention (`?confirmed=true&email=`) |
| `usePostLoginRedirect.ts` (lines 1–80) | **Technicians are blocked from web post-login** ("use the mobile app" + sign-out after 5 s) → drives §G.1 role-branched terminal state |
| TEAM-INVITE-1 design §H + Part B prompt STEP 6 | Original intent vs. shipped delta (root-cause record above) |
| `invite-landing.integration.test.tsx` | Existing MSW fixture (`dev-invite-token-0001`) + 404 contract to extend |
| Tom's prod defect report (2026-09-03) | Repro: invite link → landing → "Create account" → owner wizard asks account name/industry |

## B. Migration Plan

**None.** No DDL, no seed changes, no new/modified endpoints, no OpenAPI regeneration (`pnpm sync-api-types` still runs per Pre-Work but produces no diff). The batch consumes the TEAM-INVITE-1 public endpoint unchanged.

## C. Execution Order

| # | Step | Files |
|---|---|---|
| 1 | `InviteAcceptForm` component (email display + password/confirm + Zod + `useCognitoSignUp`) | `features/users/components/InviteAcceptForm.tsx` (new) |
| 2 | `InviteVerifyStep` component (6-digit code + confirm + role-branched completion + resend) | `features/users/components/InviteVerifyStep.tsx` (new) |
| 3 | `InviteLandingPage` phase orchestration — replace the `/signup` CTA link with the accept flow; loading/invalid/error states unchanged | `features/users/components/InviteLandingPage.tsx` (modify lines ~204–217 + state) |
| 4 | MSW fixtures — extend invites handler(s) with an `office_staff` token and a `technician` token; keep `dev-invite-token-0001` + 404 contract | `apps/web/src/mocks/handlers/` (verify existing Part B registration first) |
| 5 | Tests — unit ×2 + batch integration folder | `__tests__/batch_team_invite_2/` + co-located `__tests__/` |

## D. New API Endpoints

**None.**

Consumed (no changes):
| Endpoint | Auth | Use |
|---|---|---|
| `GET /api/v1/invites/{token}` | Public (uniform 404) | Landing-page fetch (existing) |
| Cognito `SignUp` / `ConfirmSignUp` / `ResendSignUpCode` | Amplify, dynamic import | Account creation + confirmation (client-side, no Pilot API) |

**Explicit prohibition**: the invite flow must **never** call `POST /api/v1/signup` — that is the owner Path 3 resolve-or-attach call. The Post-Confirmation Lambda Path 2 attaches the invitee to the inviting tenant at `ConfirmSignUp` time; no authenticated provisioning call is needed or wanted.

## E. Pattern Reuse Decisions

| Pattern | Application |
|---|---|
| Public-surface bare `fetch()` exception (PublicQuotePage precedent, TEAM-INVITE-1) | Unchanged — landing page keeps its existing fetch + states |
| `isMockMode()` short-circuit (`NEXT_PUBLIC_USE_MOCK_AUTH === "true"`) | Both new components mirror `useCognitoSignUp`/`VerifyEmailStep` so tests never touch real Cognito |
| Dynamic `import("aws-amplify/auth")` | Never a static top-level import (keeps Amplify out of the SSR bundle) |
| WCAG 2.2 AA (rules §36) | Paste allowed on password + code inputs (Accessible Authentication); read-only email display beside the form (Redundant Entry 3.3.7); ≥44 px primary targets; `aria-invalid` + `aria-describedby` non-color-only errors; visible password-policy hint text |
| §16 platform patterns | None new — no locked-pattern surface is touched |

## F. Shared Module Interfaces

**Phase state machine** (lives in `InviteLandingPage`):

```typescript
type AcceptPhase =
  | { step: "form" }                                  // password + confirm
  | { step: "verify"; password: string }              // 6-digit code; password in-memory ONLY
  | { step: "joined" };                               // terminal (role-branched UI)
```

The password is held in React state for the form→verify handoff — **never** `sessionStorage` (mirrors the signup wizard rule). A page reload resets to `step: "form"` and self-heals (§G.3).

**`InviteAcceptForm`** (new):

```typescript
interface InviteAcceptFormProps {
  email: string;                       // from the public invite fetch — display only
  onSignedUp: (password: string) => void;  // advances phase to verify
}
```

**`InviteVerifyStep`** (new):

```typescript
interface InviteVerifyStepProps {
  email: string;
  password: string;                    // in-memory from the form step
  roleCode: string | null;             // from the public invite fetch — drives §G.1 branch
}
```

Completion behavior is internal: `office_staff`/`accountant`/`owner` → auto-`signIn` via `useAuth()` → `router.replace("/dashboard")`; `technician` (or `null`) → render the mobile-app success panel (no web sign-in; §G.1).

**Password Zod schema**: identical rules to `signup/account/page.tsx` — min 12, ≥1 upper, ≥1 lower, ≥1 digit, ≥1 symbol, plus confirm-match refine (§G.5).

## G. Open Questions Resolved

**G.1 — Post-confirm destination branches by invite role.** Technicians are deliberately blocked from the web app post-login (`usePostLoginRedirect.ts` — "use the mobile app" + sign-out after 5 s). Routing a newly-joined technician into `/dashboard` would dump them into that sign-out loop. Resolved: `office_staff`/`accountant` → auto-sign-in → `/dashboard` (lands inside the inviting tenant — the TEAM-INVITE-1 design §H intent); `technician` (and defensive `null`) → terminal success panel: *"You're in! Open the Pilot mobile app and sign in with {email}."* — no web session created. The invite's `role_code` is already on the page from the public fetch.

**G.2 — No `POST /api/v1/signup`, ever, from this flow.** That endpoint is the owner Path 3 provisioner (new business + plan). The Lambda Path 2 attach fires synchronously on `ConfirmSignUp`, so by the time auto-sign-in completes the `tenant_user` row exists and the JWT carries tenant context.

**G.3 — Page reload between signUp and confirm self-heals.** The phase state is in-memory, so a reload returns the page to the form step. Re-submitting the same email + password calls Cognito `SignUp` against the still-*unconfirmed* user — Cognito re-sends the confirmation code (and updates to the latest password) instead of erroring. No persistence, no recovery UI needed.

**G.4 — `UsernameExistsException` maps to "Sign in instead."** A confirmed Cognito account already exists for the email (e.g., a user of *another* tenant — same-tenant duplicates are already 409'd at invite-creation time). Render an inline, non-color-only error: *"An account already exists for {email}."* + link to `/login?email={email}`. **Known MVP limitation (out of scope)**: an existing-Cognito-account user invited to a second tenant cannot self-attach — Path 2 only fires on new confirmations. Cross-tenant membership is a post-MVP concern; do not design around it here.

**G.5 — Password schema is duplicated, not extracted.** The 10-line `passwordSchema` is copied into `InviteAcceptForm` with a cross-reference comment to `signup/account/page.tsx` (and vice-versa comment added there). Extracting a shared module would touch the owner wizard days before founder onboarding — churn risk outweighs DRY here. Consolidation candidate for a future signup-hardening batch.

**G.6 — `signInStep !== "DONE"` defensive fallback.** New invitees have no MFA, so `DONE` is expected; on any non-`DONE` step, route to `/login?confirmed=true&email={email}` (mirror `VerifyEmailStep:160-163`) rather than crashing.

**G.7 — Designer-spec gate (Rule 1.5 / methods §3.9): WAIVED by Tom 2026-09-03** via direct instruction to author the React prompt immediately. §H/§I of this doc serve as the surface spec. Justification: defect-repair batch composing two proven, already-WCAG-reviewed signup primitives on an existing surface; no new top-level UX.

**G.8 — Fix lives on the landing page (Option A), not the `/signup` wizard.** Tom green-lit Option A explicitly. The owner wizard remains untouched — zero regression risk to founder onboarding.

## H. Surface Mockup Reference (§G.7 waiver — this section + §I are the spec)

Platform: **web only**, public route `/invite/[token]` (mobile team-members accept via the same emailed web link). Existing states unchanged: loading skeleton, invalid (uniform neutral panel), error (retry). New states on the valid branch:

**State 1 — `form` (replaces the CTA block):** Header "Join **{tenant_name}**" + role/expiry rows (existing). Below: read-only **email** displayed as labeled text (not an editable input), **Password** and **Confirm password** inputs with eye-toggle reveal, visible policy hint ("At least 12 characters with upper, lower, number, and symbol"), inline Zod errors (`aria-invalid`/`aria-describedby`), primary **Create your account** submit (≥44 px, full width, `data-testid="invite-accept-submit"`). `UsernameExistsException` → inline error + *"Sign in instead"* link (§G.4).

**State 2 — `verify`:** "Check your email" — 6-digit code input (paste allowed, `inputMode="numeric"`, `autoComplete="one-time-code"`), **Verify** submit (≥44 px), resend link with 30 s cooldown ("Resend code in {n}s" → "Resend code"), mapped inline errors (CodeMismatch / ExpiredCode / LimitExceeded / UserNotFound per `VerifyEmailStep` mapping). While confirm+signIn are in flight, button reads **"Setting up your account…"** (the SIGNUP-UI-FIX-2 provisioning-label pattern).

**State 3a — joined, office roles:** brief success panel ("You're in — taking you to your dashboard…") then `router.replace("/dashboard")`.

**State 3b — joined, technician:** terminal panel — "You're in, {email}!" + "Open the Pilot mobile app and sign in with this email to get started." No web sign-in, no redirect.

## I. Component Manifest

| Component / File | Destination | Action |
|---|---|---|
| `InviteAcceptForm` | `apps/web/src/features/users/components/InviteAcceptForm.tsx` | **New** — §F signature, §H State 1 |
| `InviteVerifyStep` | `apps/web/src/features/users/components/InviteVerifyStep.tsx` | **New** — §F signature, §H States 2/3a/3b |
| `InviteLandingPage` | `apps/web/src/features/users/components/InviteLandingPage.tsx` | **Modify** — add `AcceptPhase` machine; valid branch renders form/verify/joined; **delete** the `<a href="/signup">` CTA block (lines 204–217) |
| `app/invite/[token]/page.tsx` | unchanged | — |
| MSW invites fixtures | `apps/web/src/mocks/handlers/` (verify Part B registration in `index.ts` first) | **Extend** — add `office_staff` + `technician` valid tokens |
| Unit tests ×2 | `apps/web/src/features/users/components/__tests__/InviteAcceptForm.test.tsx`, `InviteVerifyStep.test.tsx` | **New** |
| Integration test | `apps/web/src/__tests__/batch_team_invite_2/invite-accept.integration.test.tsx` | **New** |

**Reconciliation checks**: no new shared component → `packages/ui/src/index.ts` untouched (engineer verifies, per Rule 7); no new `PermissionKey` (public surface, no RBAC); no new npm dependencies (all imports already in `apps/web/package.json`).

---

*Design approved by Tom 2026-09-03. Changes require Architect review.*
