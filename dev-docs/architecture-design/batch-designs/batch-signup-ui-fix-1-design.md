# Batch SIGNUP-UI-FIX-1 — Signup Wizard UI Fixes (Password Reveal + Partial-Signup Resume + Mode-Dependent Trial Text + Stale Session Cleanup)

**Batch code**: SIGNUP-UI-FIX-1
**Design doc owner**: Pilot Architect
**Created**: 2026-08-01
**Status**: ✅ Complete — React Engineer implementation done 2026-08-01 (see completion summary)
**Plan link**: `pilot-launch-plan.md`
**Batch type**: Frontend-only (`apps/web`) — no backend, no DB, no migration, no API changes
**Engineer**: Pilot React Engineer
**Prerequisite**: SIGNUP-C ✅

---

## Problem Statement

Three UI defects discovered during live smoke testing of the self-serve signup flow (post-SIGNUP-GA-1 + SIGNUP-GA-B1 + SIGNUP-C):

1. **Password fields have no reveal toggle** — the password and confirm-password fields on `/signup/account` use `type="password"` with no eyeball toggle. Users cannot verify what they typed before submitting (especially painful with the 12+ char policy requiring upper/lower/number/symbol).

2. **Partial-signup resume lands on `/dashboard` instead of the wizard** — a user who exits the browser after entering their mobile number (step 3) and later navigates to `app.pilotfortrades.com` is authenticated (Cognito session is valid) but their `tenant_signup.signup_state` is not `complete`. The root page redirects to `/dashboard`, `RequireAuth` lets them through (they ARE authenticated), and they land on the dashboard with an incomplete onboarding. They should be redirected back to the correct wizard step.

3. **Trial text is hardcoded, not mode-aware** — `/signup/plan` shows "Start with a 14-day free trial — no credit card required." regardless of whether the app is in Founders mode (no trial tier exists) or General Release mode (trial tier exists). In Founders mode this text is misleading — there is no trial tier, and the Founders plan is not a trial.

4. **Stale Cognito session blocks re-signup** — if a user previously started the signup wizard (Cognito SignUp + email verification → Amplify `signIn` on the verify page), then their user/tenant was deleted (e.g., Tom cleaned up test data), and they try to sign up again with the same email, the browser still holds a **stale Amplify session** (tokens in localStorage). When the verify step calls `confirmSignUp` → `signIn`, Amplify detects the existing session and the user sees "already logged in" or a conflict. The fix: on `/signup/account` mount, if the user is already authenticated (stale session), sign out + clear the session before showing the signup form.

---

## A. Input Read Summary

| Input | Section(s) read | What it established |
|---|---|---|
| `account/page.tsx` | full | Password fields at lines 507–538 + 548–574 use `type="password"` with no toggle. RHF `register()` — no state-level show/hide. Zod schema validates 12+ chars + complexity. |
| `plan/page.tsx` | full | Line 202: hardcoded `"Start with a 14-day free trial — no credit card required."`. `useSubscriptionTiers` hook fetches tiers including `is_trial` + `tier_name`. `trialTier` derived at line 124. `selectedTierIsTrial` at line 130. |
| `(authed)/layout.tsx` | full | `RequireAuth` wraps all authed routes — checks `isAuthenticated` only. No signup-state check. `useAuth()` provides `user.tenantId` after login. |
| `RequireAuth.tsx` | full | Pure auth guard — redirects to `/login` if not authenticated. Does not know about signup state. Correctly platform-agnostic; should NOT be modified to know about signup. |
| `AuthProvider.tsx` | `loadUserFromBackend` | After Cognito signIn, fetches `GET /api/v1/auth/me` → sets `user.tenantId` from `data.tenant_id`. So `tenantId` is available on the `PilotUser` object post-login. |
| `types.ts` | `PilotUser` | `tenantId: string` is on the user object. |
| `useSubscriptionTiers.ts` | full | Fetches `GET /api/v1/subscription-tiers`, filters `is_active`. Returns `SubscriptionTierAPI[]` with `is_trial`, `tier_name`, `trial_duration_days`. |
| `useSiteMode.ts` | full (marketing app) | Marketing app has `getSiteMode()` (server-side) + `useSiteMode()` — resolves Founders vs General by checking if `founders` tier exists vs `starter`/`teams`. The web app does NOT have this hook. |
| `signup/types.ts` | `signupStateToStep`, `stepToUrl`, `WizardSignupState` | Model B state→step mapping (corrected by SIGNUP-GA-B1). `complete` → dashboard; all others → their wizard page. |
| `app/page.tsx` | full | Root page: `redirect("/dashboard")` — server component. The dashboard then hits `(authed)/layout.tsx` → `RequireAuth`. |
| `VerifyEmailStep.tsx` | full | Calls `confirmSignUp` → `signIn` from `useAuth()`. If a stale Amplify session exists from a previous signup, `signIn` may conflict or short-circuit. The stale session originates here (the verify page is where `signIn` was last called successfully). |
| `AuthProvider.tsx` | `signOut` | `useAuth()` exposes `signOut()` — clears the Amplify session + sets `user = null`. Available on all pages that consume `useAuth`. |

**Key findings**:
1. The password reveal is a pure local-state toggle — no API, no schema, no shared component needed.
2. The partial-signup resume fix belongs in a **new guard component** rendered inside `(authed)/layout.tsx` (after `RequireAuth` confirms authentication). It fetches `GET /api/v1/signup/{tenantId}/state` and redirects to the wizard if `signup_state !== 'complete'`. This keeps `RequireAuth` platform-agnostic (it should not know about signup) and avoids touching the shared `packages/ui` auth layer.
3. The trial text fix derives Founders mode from the already-fetched `useSubscriptionTiers` data: if no tier has `is_trial === true`, the app is in Founders mode. No new hook or env var needed — the tier data IS the mode signal.

---

## B. Migration Plan

**None.** No database changes. No Alembic migration. No new columns, no triggers, no MCP verification. This batch is entirely frontend.

---

## C. Execution Order

| # | Step | Owner | Notes |
|---|---|---|---|
| 1 | Add password reveal toggle to `/signup/account` password + confirm-password fields | React | §D.1 |
| 2 | Create `SignupCompletionGuard` component | React | §D.2 — rendered inside `(authed)/layout.tsx` |
| 3 | Wire `SignupCompletionGuard` into `(authed)/layout.tsx` | React | §D.2 — after `RequireAuth`, before children |
| 4 | Make `/signup/plan` trial text mode-aware | React | §D.3 — derive from `useSubscriptionTiers` data |
| 5 | Make `/signup/account` subtitle text mode-aware | React | §D.3 — same derivation; the account page also says "Start your free 14-day trial" |
| 6 | Sign out stale session on `/signup/account` mount if already authenticated | React | §D.4 |
| 7 | Tests + Phase 2 verification | React | §G |

---

## D. New / Changed Code

### D.1 — Password reveal toggle (`/signup/account`)

**Files**: `account/page.tsx`

Add local state for show/hide on both password fields:

```tsx
const [showPassword, setShowPassword] = useState(false);
const [showConfirmPassword, setShowConfirmPassword] = useState(false);
```

Change the password input `type` from `"password"` to `showPassword ? "text" : "password"`. Same for confirm password with `showConfirmPassword`.

Add a toggle button inside each field container (absolute-positioned, right-aligned):

```tsx
<div className="relative">
  <input
    id="password"
    type={showPassword ? "text" : "password"}
    autoComplete="new-password"
    ...
    className={`... pr-10`}  // add right padding for the button
    {...register("password")}
  />
  <button
    type="button"
    onClick={() => setShowPassword((v) => !v)}
    className="absolute right-2 top-1/2 -translate-y-1/2 text-neutral-400 hover:text-neutral-600 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-1 rounded"
    aria-label={showPassword ? "Hide password" : "Show password"}
    data-testid="toggle-password-visibility"
  >
    {showPassword ? (
      <EyeSlashIcon className="w-5 h-5" />
    ) : (
      <EyeIcon className="w-5 h-5" />
    )}
  </button>
</div>
```

**Icons**: `EyeIcon` + `EyeSlashIcon` from `@heroicons/react/24/outline` (Heroicons 2.0).

**WCAG 2.2 AA**:
- The toggle button has `aria-label` that changes with state ("Show password" / "Hide password").
- `type="button"` prevents form submission on click.
- Target size: `w-5 h-5` (20px) icon inside a padded button — the click area includes the padding, meeting ≥24×24px minimum.
- `focus-visible:ring-2` for keyboard users.
- Paste is still allowed (WCAG 2.2 SC 3.3.8) — the toggle does not restrict input.

**No new component** — this is inline state in the existing page. The pattern is simple enough that extracting a shared `PasswordField` is premature (Rule 7 — only promote to `packages/ui` when a 2nd consumer appears).

### D.2 — `SignupCompletionGuard` (new component)

**File**: `apps/web/src/components/SignupCompletionGuard.tsx` (new)

**Purpose**: After `RequireAuth` confirms the user is authenticated, check whether their signup wizard is complete. If not, redirect them to the correct wizard step.

```tsx
"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";
import { useAuth } from "@pilot/ui/auth";
import {
  signupStateToStep,
  stepToUrl,
  type WizardSignupState,
} from "@/features/signup/types";

/**
 * SignupCompletionGuard — rendered inside (authed)/layout.tsx after RequireAuth.
 *
 * Fetches GET /api/v1/signup/{tenantId}/state. If signup_state !== 'complete',
 * redirects to the correct wizard step. This prevents a partially-onboarded
 * user from landing on /dashboard with an incomplete tenant setup.
 *
 * - Only fires when user.tenantId is available (post-login).
 * - Uses TanStack Query with staleTime: 0 (always refetch on mount — signup
 *   state is short-lived and changes during onboarding).
 * - Renders null while checking (the layout shows nothing for a brief moment).
 * - On fetch error: fail open to dashboard (don't block a fully-onboarded user
 *   if the signup endpoint is temporarily unavailable).
 */
export function SignupCompletionGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { user } = useAuth();
  const tenantId = user?.tenantId;

  const { data, isLoading, isError } = useQuery({
    queryKey: ["signup-state-guard", tenantId],
    queryFn: async () => {
      const res = await apiClient.get<{
        signup_state: WizardSignupState;
      }>(`/api/v1/signup/${tenantId}/state`);
      return res.data;
    },
    enabled: !!tenantId,
    staleTime: 0, // always refetch on mount
    retry: false,
  });

  useEffect(() => {
    if (!tenantId || isLoading) return;

    if (isError) {
      // Fail open — let the user through to the dashboard. A fully-onboarded
      // user should not be blocked by a transient signup-state endpoint failure.
      return;
    }

    const currentState = data?.signup_state;
    if (currentState && currentState !== "complete") {
      const targetStep = signupStateToStep[currentState];
      const targetUrl = stepToUrl[targetStep] ?? "/signup/account";
      router.replace(targetUrl);
    }
  }, [tenantId, isLoading, isError, data, router]);

  // While checking (and user has a tenantId), render nothing to prevent
  // flashing the dashboard before the redirect fires.
  if (tenantId && isLoading) {
    return null;
  }

  // If no tenantId (shouldn't happen post-RequireAuth, but defensive),
  // or state is complete, or we're failing open — render children.
  return <>{children}</>;
}
```

**Wiring in `(authed)/layout.tsx`**:

```tsx
import { SignupCompletionGuard } from "@/components/SignupCompletionGuard";

// Inside the RequireAuth wrapper, wrapping the content:
<RequireAuth redirectTo="/login" onRedirect={(path) => router.replace(path)}>
  <SignupCompletionGuard>
    <div className="flex flex-col h-full min-h-screen">
      {/* ... existing layout ... */}
    </div>
    <NotificationDrawer />
  </SignupCompletionGuard>
</RequireAuth>
```

**Design decisions**:
- **Why a separate component, not in RequireAuth?** `RequireAuth` is in `packages/ui` — it's platform-agnostic (web + mobile) and should not know about the Pilot signup wizard. The signup-state guard is web-app-specific.
- **Why TanStack Query?** The signup state is already fetched by individual wizard pages via their own `useQuery` calls. Using a separate query here with `staleTime: 0` ensures a fresh check on every layout mount without interfering with the page-level queries (different query key).
- **Why fail open on error?** A fully-onboarded user (the common case post-launch) should never be blocked from their dashboard by a transient API failure. The cost of a partially-onboarded user slipping through during an outage is low (they'll see an empty dashboard and can navigate to `/signup` manually).
- **Why render null while loading?** To prevent a flash of the dashboard content before the redirect fires. The loading window is one API call (~100ms) — imperceptible.

### D.3 — Mode-dependent trial text (`/signup/plan` + `/signup/account`)

**Files**: `plan/page.tsx`, `account/page.tsx`

**Derivation**: The `useSubscriptionTiers` hook already fetches all active tiers. The app is in **Founders mode** when no tier has `is_trial === true`. In Founders mode, the `founders` tier is the only selectable plan (it has `is_trial: false`, `monthly_price_cents: 0` per the seed). In General Release mode, a `trial` tier exists (`is_trial: true`, `trial_duration_days: 14`).

**Plan page** (`plan/page.tsx`):

```tsx
// Derive mode from tier data (already fetched)
const hasTrialTier = !!trialTier;  // trialTier already derived at line 124
const subtitleText = hasTrialTier
  ? "Start with a 14-day free trial — no credit card required."
  : "Join the Founders program — free during development, no credit card required.";
```

Replace the hardcoded subtitle at line 202 with `{subtitleText}`.

**Account page** (`account/page.tsx`):

The account page also has a hardcoded subtitle at line 242: `"Start your free 14-day trial — no credit card required."` This needs the same mode-aware treatment. However, the account page does NOT currently fetch subscription tiers (it's step 1, before plan selection). Two options:

- **Option A (recommended)**: Fetch tiers on the account page too (lightweight — `useSubscriptionTiers` with 5-min staleTime; the data is already cached if the user navigated from a page that fetched it). Derive the subtitle from the cached data.
- **Option B**: Hardcode the Founders-mode text now (since the app is in Founders mode today) and add the dynamic derivation when General Release mode is activated. Simpler but creates a future tech-debt item.

**Decision**: Option A — use `useSubscriptionTiers()` on the account page. The hook is already written, the data is cached by TanStack Query, and it future-proofs the page. The subtitle becomes:

```tsx
const { data: tiers } = useSubscriptionTiers();
const hasTrialTier = !!tiers?.find((t) => t.is_trial);
const subtitleText = hasTrialTier
  ? "Start your free 14-day trial — no credit card required."
  : "Join the Founders program — free during development, no credit card required.";
```

**Text copy decisions**:
- **Founders mode**: `"Join the Founders program — free during development, no credit card required."` (plan page) / `"Join the Founders program — free during development, no credit card required."` (account page). Accurate: the Founders tier is $0/mo, no trial, no credit card.
- **General Release mode**: `"Start with a 14-day free trial — no credit card required."` (plan page) / `"Start your free 14-day trial — no credit card required."` (account page). Unchanged from current text — accurate when a trial tier exists.

### D.4 — Stale session cleanup on `/signup/account` mount

**File**: `account/page.tsx`

**Problem**: If a user previously completed Cognito SignUp + email verification (which calls Amplify `signIn` on the verify page), the browser holds a stale Amplify session. If their user/tenant is later deleted (e.g., Tom cleanup) and they try to sign up again, the stale session causes conflicts on the verify step.

**Fix**: On `/signup/account` mount, if the user is already authenticated (`useAuth().isAuthenticated === true`), call `signOut()` to clear the stale session before showing the signup form. This ensures a clean Cognito state for a new `SignUp` call.

```tsx
import { useAuth } from "@pilot/ui/auth";

// Inside SignupAccountPage component:
const { isAuthenticated, signOut } = useAuth();

// Clear any stale session before showing the signup form.
// This handles the case where a previous signup attempt left an Amplify
// session in localStorage that would conflict with a new SignUp call.
useEffect(() => {
  if (isAuthenticated) {
    signOut().then(() => {
      // Session cleared — the form is now usable for a fresh signup.
      // Also clear any stale wizard tenant_id from sessionStorage.
      sessionStorage.removeItem(WIZARD_TENANT_ID_KEY);
    });
  }
}, [isAuthenticated, signOut]);
```

**Design decisions**:
- **Why sign out, not redirect?** The user is on `/signup/account` — they want to start a new signup. Redirecting them to `/dashboard` (if their session is valid) would be wrong if their tenant was deleted. Signing out clears the stale session and lets them proceed with a fresh `SignUp`.
- **Why clear `WIZARD_TENANT_ID_KEY`?** A stale `tenant_id` in sessionStorage from a previous (now-deleted) tenant would cause the resume-check `useEffect` (line 133) to fetch `/api/v1/signup/{deletedTenantId}/state` → 404 → clear session + stay on account page. Clearing it proactively avoids the unnecessary 404.
- **Race condition**: The existing resume-check `useEffect` (line 133) and this new sign-out `useEffect` both fire on mount. The sign-out effect clears `WIZARD_TENANT_ID_KEY`, so the resume-check's `sessionStorage.getItem(WIZARD_TENANT_ID_KEY)` returns null → the resume-check is a no-op. No race.
- **Mock mode**: In mock mode (`getMockUser()` returns a mock user), `isAuthenticated` may be true. `signOut()` in mock mode clears the mock user. This is correct — a mock user should not block a new signup.
- **`signOut()` is async**: It returns a Promise. The form renders immediately (the sign-out runs in the background). If the user submits before sign-out completes, the `useCognitoSignUp` hook's `SignUp` call may still conflict — but this is an extreme edge case (user types + submits in <100ms). The `signOut` Promise resolves almost instantly (it's a local token clear, not a network call).

**Interaction with `SignupCompletionGuard` (§D.2)**:
- If the user has a valid session AND a valid (non-deleted) tenant with `signup_state !== 'complete'`, the guard in `(authed)/layout.tsx` would redirect them to the wizard. But `/signup/account` is OUTSIDE the `(authed)` group — so the guard never fires on this page. The sign-out here is the correct behavior for the account page: a user on `/signup/account` wants to start fresh.
- If the user has a valid session AND `signup_state === 'complete'`, they shouldn't be on `/signup/account` at all — but signing them out is still the right move (they navigated here manually, presumably to start a new account).

---

## E. Pattern Reuse Decisions (`mvp-arch.md` §16)

| Pattern | Applies? | How |
|---|---|---|
| 409-and-refresh staleness guard | ❌ | No mutations in this batch. |
| Optimistic UI | ❌ | No mutations. |
| `apiClient` mandatory | ✅ | `SignupCompletionGuard` uses `apiClient.get` for the signup-state fetch. |
| TanStack Query | ✅ | `SignupCompletionGuard` uses `useQuery` with `staleTime: 0`; account page reuses `useSubscriptionTiers`. |
| WCAG 2.2 AA | ✅ | Password toggle: `aria-label`, `focus-visible`, ≥24px target, paste allowed. |

No new top-level UX pattern. No `packages/ui` change.

---

## F. Shared Module Interfaces

**No new shared modules.** No Celery tasks. No backend services.

The `SignupCompletionGuard` is a web-app-specific component in `apps/web/src/components/` — not a shared `packages/ui` component (it knows about the Pilot signup wizard, which is app-specific).

---

## G. Open Questions Resolved

| Q | Resolution |
|---|---|
| Should the password toggle be a shared `PasswordField` component? | **No** — inline state in the account page. Only one consumer today. Promote to `packages/ui` when a 2nd consumer appears (Rule 7). |
| Should `SignupCompletionGuard` live in `packages/ui` or `apps/web`? | **`apps/web`** — it imports from `@/features/signup/types` (app-specific). `packages/ui` is platform-agnostic and should not know about the signup wizard. |
| Should the guard fail open or closed on API error? | **Fail open** — a fully-onboarded user must not be blocked by a transient API failure. The cost of a partially-onboarded user slipping through during an outage is low. |
| Should the guard render null or a loading spinner while checking? | **Null** — the check is one API call (~100ms). A spinner would flash. Null prevents dashboard content flash before redirect. |
| Should the account page fetch tiers just for the subtitle? | **Yes** — `useSubscriptionTiers` is already written, cached by TanStack Query (5-min staleTime), and future-proofs the page. The cost is negligible. |
| What Founders-mode text to use? | `"Join the Founders program — free during development, no credit card required."` — accurate ($0/mo, no trial, no card). |
| Does this batch touch the Founders plan payment issue (item 4)? | **No** — that's a separate batch (FOUNDERS-PLAN-1) requiring a product discussion first. This batch only fixes the trial text to be mode-aware; it does NOT change the payment/Continue-button logic. |

---

## H. Surface Mockup Reference (Frontend)

**No new surfaces.** No design spec required (Rule 1.5 — this batch changes existing surfaces only, no new visual layout). The changes are:

1. **Password field** — add an eyeball toggle button inside the existing input container (right-aligned, absolute position). No layout change.
2. **SignupCompletionGuard** — invisible component (renders null while checking, children otherwise). No visual change.
3. **Trial text** — string replacement in existing subtitle `<p>` tags. No layout change.
4. **Stale session sign-out** — invisible (calls `signOut()` in a `useEffect`; no visual change to the form).

No `pilot-web-ui-designer` spec needed — these are logic/string changes, not pixel-level design changes.

---

## I. Component Manifest (Frontend)

| Component | Path | New/Change | Notes |
|---|---|---|---|
| `SignupCompletionGuard` | `apps/web/src/components/SignupCompletionGuard.tsx` | **New** | Invisible guard; fetches signup state; redirects incomplete users to wizard |
| `account/page.tsx` | `apps/web/src/app/signup/account/page.tsx` | **Change** | Add password reveal toggle (showPassword/showConfirmPassword state + EyeIcon/EyeSlashIcon); add `useSubscriptionTiers` for mode-aware subtitle; add stale-session sign-out on mount if `isAuthenticated` |
| `plan/page.tsx` | `apps/web/src/app/signup/plan/page.tsx` | **Change** | Replace hardcoded trial subtitle with mode-aware derivation from `trialTier` |
| `(authed)/layout.tsx` | `apps/web/src/app/(authed)/layout.tsx` | **Change** | Wrap children in `<SignupCompletionGuard>` inside `<RequireAuth>` |

**No new `packages/ui` components.** No new hooks. No new MSW handlers (the signup-state endpoint is already mocked in `signupHandlers.ts`).

---

## Definition of Done (design-level)

- Password + confirm-password fields on `/signup/account` have a reveal toggle (eyeball icon) that shows/hides the typed value. `aria-label` changes with state. Paste is still allowed.
- A user who is authenticated but has `signup_state !== 'complete'` is redirected from `/dashboard` (or any `(authed)/` route) to the correct wizard step. A fully-onboarded user (`signup_state === 'complete'`) is never redirected.
- The `/signup/plan` and `/signup/account` subtitle text is mode-aware: Founders mode shows "Join the Founders program — free during development, no credit card required." General Release mode shows the trial text.
- On `/signup/account` mount, if the user is already authenticated (stale Amplify session from a previous signup), `signOut()` is called to clear the session before showing the form. `WIZARD_TENANT_ID_KEY` is also cleared.
- `SignupCompletionGuard` fails open on API error (does not block authenticated users).
- No backend changes. No migration. No new `packages/ui` components.
- Phase 2 FE verification passes; zero new type/lint errors.

---

## Cost Impact

**$0.** No infrastructure change. No new AWS service. No backend work.

---

*Authored by Pilot Architect, 2026-08-01. Frontend-only batch — no MCP verification needed (no DB touch). Governed by the existing signup state machine (SIGNUP-GA-B1 Model B). The Founders-plan payment issue (item 4) is a separate batch (FOUNDERS-PLAN-1) requiring a product discussion before design.*
