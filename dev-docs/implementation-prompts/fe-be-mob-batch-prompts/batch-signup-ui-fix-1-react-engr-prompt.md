# Implementation Prompt: SIGNUP-UI-FIX-1 — Signup Wizard UI Fixes (Password Reveal + Partial-Signup Resume + Mode-Dependent Trial Text + Stale Session Cleanup)

**Mode**: Pilot React Engineer
**Batch**: SIGNUP-UI-FIX-1
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §14d (line 150) + §SIGNUP-UI-FIX-1 (line 604)
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-signup-ui-fix-1-design.md`
**Estimated session**: 2–3 hours
**Platform**: Web only (`apps/web`)
**Backend companion**: None — pure frontend, no backend changes, no DB, no migration, no API changes

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-react-engineer/react-engineer-rules.md`** — in full
- **`dev-docs/architecture-design/batch-designs/batch-signup-ui-fix-1-design.md`** — every section (A–I)

Critical rules for this batch:

- **Rule 2**: All API calls use `apiClient` from `@pilot/shared-api` (not `@/lib/api-client` — that module does not exist). `fetch()` is permanently banned for `/api/v1/...` calls. The `SignupCompletionGuard` uses `apiClient.get` for the signup-state fetch.
- **Rule 7**: Check `packages/ui/src/index.ts` before creating any new component. This batch creates NO new `packages/ui` components — `SignupCompletionGuard` is app-specific (lives in `apps/web/src/components/`).
- **Rule 8**: No new npm dependencies. `@heroicons/react@^2.2.0` is already in `apps/web/package.json` (line 19) — `EyeIcon` + `EyeSlashIcon` from `@heroicons/react/24/outline` are available. Do NOT add any new dependency.
- **Rule 10**: If ANY test fails during your work — even one that appears pre-existing — you must fix it before declaring the batch done. There is no "not my fault" exception.
- **Rule 11 (React Compiler — rules §32)**: The web app runs React 19.2 with the React Compiler enabled. Do NOT hand-write `useMemo`/`useCallback`/`React.memo` for render-perf. Keep components pure.
- **Rule 12 (TanStack Query v5 — rules §33)**: Object-form API only (`useQuery({ queryKey, queryFn })`). `gcTime` not `cacheTime`; `isPending` not `isLoading`. Colocated query keys that include every `queryFn` variable. `SignupCompletionGuard` uses `staleTime: 0` + `retry: false`.
- **Rule 14 (server vs client — rules §35)**: `SignupCompletionGuard` is a `"use client"` component — it fetches tenant data client-side via `apiClient` + TanStack Query. Never fetch tenant data in a Server Component.
- **Rule 15 (WCAG 2.2 AA — rules §36)**: The password reveal toggle must satisfy: `aria-label` that changes with state, `type="button"` (no form submit), ≥24×24px target size, `focus-visible:ring`, and paste is still allowed (WCAG 2.2 SC 3.3.8 — the toggle does not restrict input).

---

## Design Decisions (Do Not Re-Litigate)

From Design Doc §G — these decisions are final:

| Decision | Outcome | Rationale |
|---|---|---|
| Should the password toggle be a shared `PasswordField` component? | **No** — inline state in the account page | Only one consumer today. Promote to `packages/ui` when a 2nd consumer appears (Rule 7). |
| Should `SignupCompletionGuard` live in `packages/ui` or `apps/web`? | **`apps/web`** (`apps/web/src/components/SignupCompletionGuard.tsx`) | It imports from `@/features/signup/types` (app-specific). `packages/ui` is platform-agnostic and should not know about the signup wizard. |
| Should the guard fail open or closed on API error? | **Fail open** | A fully-onboarded user must not be blocked by a transient API failure. The cost of a partially-onboarded user slipping through during an outage is low. |
| Should the guard render null or a loading spinner while checking? | **Null** | The check is one API call (~100ms). A spinner would flash. Null prevents dashboard content flash before redirect. |
| Should the account page fetch tiers just for the subtitle? | **Yes** — `useSubscriptionTiers()` | Already written, cached by TanStack Query (5-min staleTime), future-proofs the page. Cost is negligible. |
| What Founders-mode text to use? | `"Join the Founders program — free during development, no credit card required."` | Accurate: Founders tier is $0/mo, no trial, no card. |
| Does this batch touch the Founders plan payment issue? | **No** — separate batch (FOUNDERS-PLAN-1) | This batch only fixes the trial text to be mode-aware; it does NOT change payment/Continue-button logic. |

These were resolved in the design doc. Do NOT change them without asking Tom.

---

## Pre-Work: Establish Regression Baseline

Before touching any file:

```bash
cd <repo>/frontend
pnpm --filter web test 2>&1 | tail -5
```

Record the exact counts. These must still pass at the end of the batch.

> **If any tests are already failing before you start**: Do NOT treat them as "pre-existing" and proceed. Either:
> (a) Confirm with Tom that this is a known, accepted failure with a documented reason, OR
> (b) Fix the failure before touching any batch files.
>
> You may NOT start implementation work while tests are in an unexplained failed state.

---

## Pre-Work: Sync API Types

```bash
cd <repo>/frontend
pnpm sync-api-types
```

This batch does NOT add new hooks or new endpoints, but it DOES consume the existing `GET /api/v1/signup/{tenant_id}/state` response shape in the new `SignupCompletionGuard`. Running `pnpm sync-api-types` ensures `packages/shared-types/src/api-schema.d.ts` matches the live backend. All backend payload types must come from `@pilot/shared-types` — never from hand-written interfaces.

> **If `pnpm sync-api-types` fails** because the backend is not running locally → note it and proceed; the signup-state endpoint already exists in `openapi.json` (verified — see §Verify Endpoints below).

---

## Pre-Work: Verify Endpoints

This batch consumes one existing endpoint in the new `SignupCompletionGuard`. Verify it exists before writing any code:

```bash
grep -A 5 "signup/{tenant_id}/state" backend/openapi_schema_map.md
```

**If the endpoint is NOT in `openapi_schema_map.md` or `openapi.json` → STOP. Do not invent a URL. Ask Tom.**

Verified endpoints for this batch:

| Consumer | Endpoint | Verified |
|---|---|---|
| `SignupCompletionGuard` | `GET /api/v1/signup/{tenant_id}/state` | ✅ Confirmed in `backend/openapi_schema_map.md` line 20630 (`Get Signup State Route`) — returns `{ tenant_id, signup_state, collected_data }` |
| `useSubscriptionTiers` (existing, reused) | `GET /api/v1/subscription-tiers` | ✅ Already in use by `plan/page.tsx` — no change needed |

The signup-state endpoint is **already mocked** in `signupHandlers.ts` (line 8: `GET /api/v1/signup/:tenantId/state`). No new MSW handler is needed for this batch.

---

## Pre-Work: Read These Source Files

Read each of these with `read_file` before writing any code. **Never assume you know what's in a file — even recently-modified files may have changed.**

| File | Why read it |
|---|---|
| `frontend/apps/web/src/app/signup/account/page.tsx` | The page you're modifying for password reveal (§D.1), mode-aware subtitle (§D.3), and stale-session sign-out (§D.4). Password fields are at lines 507–538 + 548–574. Subtitle at line 242. Resume-check `useEffect` at line 133. |
| `frontend/apps/web/src/app/signup/plan/page.tsx` | The page you're modifying for mode-aware subtitle (§D.3). Hardcoded subtitle at line 202. `trialTier` derived at line 124. `useSubscriptionTiers` already imported (line 21). |
| `frontend/apps/web/src/app/(authed)/layout.tsx` | Where you'll wire `SignupCompletionGuard` (§D.2). `RequireAuth` wraps content at lines 62–121. Children + `NotificationDrawer` are inside `RequireAuth`. |
| `frontend/apps/web/src/features/signup/types.ts` | Exports `signupStateToStep`, `stepToUrl`, `WizardSignupState`, `WIZARD_TENANT_ID_KEY` — all consumed by `SignupCompletionGuard` and the account-page sign-out. |
| `frontend/apps/web/src/features/signup/hooks/useSubscriptionTiers.ts` | The hook you'll reuse on the account page for mode-aware subtitle. Returns `SubscriptionTierAPI[]` with `is_trial`. `staleTime: 5 * 60 * 1000`. |
| `frontend/packages/ui/src/auth/AuthProvider.tsx` | Confirms `useAuth()` exposes `isAuthenticated`, `signOut()`, and `user.tenantId`. Read the `signOut` + `loadUserFromBackend` sections. |
| `frontend/packages/ui/src/auth/types.ts` | Confirms `PilotUser` has `tenantId: string`. |
| `frontend/packages/ui/src/auth/RequireAuth.tsx` | Confirms `RequireAuth` is a pure auth guard — do NOT modify it. The signup-state guard is separate. |
| `frontend/apps/web/src/mocks/handlers/signupHandlers.ts` | Confirms `GET /api/v1/signup/:tenantId/state` is already mocked with `step2_legal`, `step3_phone`, `step4_tier`, `complete` states. No new handler needed. |
| `frontend/apps/web/src/mocks/handlers/index.ts` | Confirms `signupHandlers` is already registered in the barrel (line 23). No new registration needed. |
| `frontend/packages/ui/src/index.ts` | Confirms no existing `PasswordField` or `SignupCompletionGuard` component — you are NOT creating a `packages/ui` component. |

Also run these to confirm import paths and existing patterns:

```bash
# Confirm heroicons is installed (it is — ^2.2.0 in package.json line 19)
grep -n "@heroicons/react" frontend/apps/web/package.json

# Confirm EyeIcon + EyeSlashIcon are valid exports (used elsewhere in the app)
grep -rn "EyeIcon\|EyeSlashIcon" frontend/apps/web/src | head -5

# Confirm useAuth exposes signOut + isAuthenticated
grep -n "signOut\|isAuthenticated" frontend/packages/ui/src/auth/AuthProvider.tsx | head -10

# Confirm the signup-state MSW handler exists
grep -n "signup/:tenantId/state\|signup_state" frontend/apps/web/src/mocks/handlers/signupHandlers.ts | head -10
```

---

## Platform: Web (`apps/web`) — Mandatory Constraints

- **Route files are thin server components**: `app/(authed)/path/page.tsx` files must NOT have `"use client"`, must NOT fetch data. NOTE: `/signup/account/page.tsx` and `/signup/plan/page.tsx` are NOT in the `(authed)` group — they are public signup pages and already have `"use client"` (correct). Do not change this.
- **Feature components own logic**: All `"use client"`, hooks, state, and data fetching belong in feature components or page components (for the signup flow, the pages themselves own the logic — this is the existing pattern).
- **Component placement rule**: `SignupCompletionGuard` is app-specific (imports `@/features/signup/types`) → `apps/web/src/components/SignupCompletionGuard.tsx`. NOT `packages/ui`.
- **React Compiler (React 19.2)**: Do NOT hand-write `useMemo`/`useCallback`/`React.memo` for render-perf. Keep components pure. (rules §32)
- **TanStack Query v5**: Object-form only; `gcTime`/`isPending`; colocate query keys incl. every `queryFn` variable; `staleTime` deliberately; `retry: false` in `SignupCompletionGuard`. (rules §33)
- **Test framework: Vitest + `@testing-library/react`** — use `vi.mock()`, `toBeInTheDocument()` assertions, `import { describe, it, expect, vi } from "vitest"`.
- **Mock Next.js in web tests**: Any component using `next/navigation` requires mocking in tests:
  ```typescript
  vi.mock("next/navigation", () => ({ usePathname: () => "/dashboard", useRouter: () => ({ replace: vi.fn(), push: vi.fn() }) }));
  ```

---

## Context: What This Batch Does

Four UI defects in the self-serve signup flow, all frontend-only:

| # | Defect | Fix | Files |
|---|---|---|---|
| 1 | Password fields have no reveal toggle | Add `showPassword`/`showConfirmPassword` local state + `EyeIcon`/`EyeSlashIcon` toggle button | `account/page.tsx` |
| 2 | Partial-signup resume lands on `/dashboard` | New `SignupCompletionGuard` in `(authed)/layout.tsx` — fetches signup state, redirects incomplete users to wizard | `SignupCompletionGuard.tsx` (new), `(authed)/layout.tsx` |
| 3 | Trial text hardcoded, not mode-aware | Derive Founders vs General Release from `useSubscriptionTiers` data (no `is_trial` tier = Founders mode) | `plan/page.tsx`, `account/page.tsx` |
| 4 | Stale Cognito session blocks re-signup | On `/signup/account` mount, if `isAuthenticated`, call `signOut()` + clear `WIZARD_TENANT_ID_KEY` | `account/page.tsx` |

**No backend. No DB. No migration. No new `packages/ui` components. No new MSW handlers. No new npm dependencies.**

---

## STEP 1 — Password Reveal Toggle (`/signup/account`)

**File**: `frontend/apps/web/src/app/signup/account/page.tsx`

Read the file first. Adjust prop names, import paths, and logic to match what you actually find. The password fields are at lines 507–538 (password) and 548–574 (confirm password).

### 1a. Add the icon import

At the top of the file, add to the existing React import or as a new import:

```tsx
import { EyeIcon, EyeSlashIcon } from "@heroicons/react/24/outline";
```

> `@heroicons/react@^2.2.0` is already in `apps/web/package.json` (line 19). `EyeIcon` + `EyeSlashIcon` are valid Heroicons 2.0 outline exports. Do NOT add a new dependency.

### 1b. Add local state for show/hide

Inside the `SignupAccountPage` component (after the existing `useForm` destructure, around line 128), add:

```tsx
const [showPassword, setShowPassword] = useState(false);
const [showConfirmPassword, setShowConfirmPassword] = useState(false);
```

> You'll need to add `useState` to the React import on line 27: `import React, { useEffect, useState } from "react";`

### 1c. Wrap the password input in a relative container + add toggle button

Replace the password input block (lines 507–523). The input `type` changes from `"password"` to `showPassword ? "text" : "password"`, and add `pr-10` to the className for button clearance. Add the toggle button inside a `relative` wrapper:

```tsx
{/* Password */}
<div className="flex flex-col gap-1">
  <label
    htmlFor="password"
    className="text-sm font-medium text-neutral-800"
  >
    Password <span className="text-fault-600">*</span>
  </label>
  <div className="relative">
    <input
      id="password"
      type={showPassword ? "text" : "password"}
      autoComplete="new-password"
      placeholder="At least 12 characters"
      aria-invalid={!!errors.password}
      aria-describedby={
        errors.password ? "password-error" : "password-rules"
      }
      data-testid="field-password"
      className={`
        w-full rounded-lg border px-3 py-2.5 pr-10 text-sm focus:outline-none
        focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-2
        ${errors.password ? "border-fault-600 bg-fault-50" : "border-neutral-300"}
      `}
      {...register("password")}
    />
    <button
      type="button"
      onClick={() => setShowPassword((v) => !v)}
      className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-neutral-400 hover:text-neutral-600 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-1 rounded"
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
  {/* Helper text — non-color-only (WCAG §36): states the policy. */}
  <p id="password-rules" className="text-xs text-neutral-500 mt-0.5">
    At least 12 characters with one uppercase, one lowercase, one
    number, and one symbol.
  </p>
  {errors.password && (
    <p
      id="password-error"
      className="text-fault-600 text-xs mt-0.5"
      role="alert"
    >
      {errors.password.message}
    </p>
  )}
</div>
```

### 1d. Same pattern for confirm password (lines 548–564)

Replace the confirm-password input block with the same relative-wrapper + toggle pattern, using `showConfirmPassword` state, `data-testid="toggle-confirm-password-visibility"`, and `aria-label={showConfirmPassword ? "Hide password" : "Show password"}`.

### WCAG 2.2 AA checklist for this step (rules §36):

- ✅ `aria-label` changes with state ("Show password" / "Hide password")
- ✅ `type="button"` prevents form submission on click
- ✅ Target size: `w-5 h-5` (20px) icon inside a `p-1` padded button — click area ≥24×24px
- ✅ `focus-visible:ring-2` for keyboard users
- ✅ Paste is still allowed (WCAG 2.2 SC 3.3.8) — the toggle does not restrict input

### Intermediate verification

```bash
cd <repo>/frontend
pnpm --filter web test -- apps/web/src/features/signup/components/__tests__/SignupAccountPage.test.tsx 2>&1 | tail -10
```

Fix any failure before moving to STEP 2.

---

## STEP 2 — Create `SignupCompletionGuard` (new component)

**File**: `frontend/apps/web/src/components/SignupCompletionGuard.tsx` (new)

**Purpose**: After `RequireAuth` confirms the user is authenticated, check whether their signup wizard is complete. If not, redirect them to the correct wizard step. This prevents a partially-onboarded user from landing on `/dashboard` with an incomplete tenant setup.

Read `frontend/apps/web/src/app/(authed)/layout.tsx` and `frontend/apps/web/src/features/signup/types.ts` first. Adjust import paths to match what you actually find.

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

  const { data, isPending, isError } = useQuery({
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
    if (!tenantId || isPending) return;

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
  }, [tenantId, isPending, isError, data, router]);

  // While checking (and user has a tenantId), render nothing to prevent
  // flashing the dashboard before the redirect fires.
  if (tenantId && isPending) {
    return null;
  }

  // If no tenantId (shouldn't happen post-RequireAuth, but defensive),
  // or state is complete, or we're failing open — render children.
  return <>{children}</>;
}
```

### Design notes (do not re-litigate — see §Design Decisions):

- **Why a separate component, not in `RequireAuth`?** `RequireAuth` is in `packages/ui` — platform-agnostic (web + mobile), should not know about the Pilot signup wizard. The signup-state guard is web-app-specific.
- **Why TanStack Query?** Uses a separate query key (`["signup-state-guard", tenantId]`) from the page-level queries — no interference. `staleTime: 0` ensures a fresh check on every layout mount.
- **Why fail open on error?** A fully-onboarded user (the common case post-launch) must never be blocked from their dashboard by a transient API failure.
- **Why render null while loading?** Prevents a flash of dashboard content before the redirect fires. The loading window is one API call (~100ms) — imperceptible.
- **Why `isPending` not `isLoading`?** TanStack Query v5 (rules §33) — `isPending` is the v5 property; `isLoading` is deprecated.

### Intermediate verification

```bash
cd <repo>/frontend
pnpm --filter web check-types 2>&1 | tail -10
```

Fix any type error before moving to STEP 3.

---

## STEP 3 — Wire `SignupCompletionGuard` into `(authed)/layout.tsx`

**File**: `frontend/apps/web/src/app/(authed)/layout.tsx`

Read the file first. The current structure (lines 62–121) is:

```tsx
<RequireAuth redirectTo="/login" onRedirect={(path) => router.replace(path)}>
  <div className="flex flex-col h-full min-h-screen">
    {/* header + sidebar + children */}
  </div>
  <NotificationDrawer />
</RequireAuth>
```

### 3a. Add the import

After the existing `RequireAuth` import (line 38), add:

```tsx
import { SignupCompletionGuard } from "@/components/SignupCompletionGuard";
```

### 3b. Wrap the content inside `RequireAuth`

Wrap the existing `<div>` + `<NotificationDrawer />` in `<SignupCompletionGuard>`:

```tsx
<RequireAuth
  redirectTo="/login"
  onRedirect={(path) => router.replace(path)}
>
  <SignupCompletionGuard>
    <div className="flex flex-col h-full min-h-screen">
      {/* ... existing header + sidebar + children ... */}
    </div>
    <NotificationDrawer />
  </SignupCompletionGuard>
</RequireAuth>
```

> **Placement is critical**: `SignupCompletionGuard` goes INSIDE `RequireAuth` (so it only renders for authenticated users) and wraps ALL content (so the redirect fires before any dashboard content flashes). `NotificationDrawer` stays inside the guard so it's available on all authed pages.

### Intermediate verification

```bash
cd <repo>/frontend
pnpm --filter web test 2>&1 | tail -6
```

Fix any failure before moving to STEP 4.

---

## STEP 4 — Mode-Dependent Trial Text (`/signup/plan`)

**File**: `frontend/apps/web/src/app/signup/plan/page.tsx`

Read the file first. The hardcoded subtitle is at line 202. The `trialTier` is already derived at line 124: `const trialTier = tiers?.find((t) => t.is_trial);`

### 4a. Derive the mode-aware subtitle text

After the existing `trialTier` derivation (line 124), add:

```tsx
// Mode-aware subtitle: if no trial tier exists, the app is in Founders mode.
const hasTrialTier = !!trialTier;
const subtitleText = hasTrialTier
  ? "Start with a 14-day free trial — no credit card required."
  : "Join the Founders program — free during development, no credit card required.";
```

> **Derivation logic**: The `useSubscriptionTiers` hook (already imported at line 21) fetches all active tiers. The app is in **Founders mode** when no tier has `is_trial === true`. In Founders mode, the `founders` tier is the only selectable plan (`is_trial: false`, `monthly_price_cents: 0`). In General Release mode, a `trial` tier exists (`is_trial: true`, `trial_duration_days: 14`). The tier data IS the mode signal — no new hook or env var needed.

### 4b. Replace the hardcoded subtitle

At line 201–203, replace:

```tsx
<p className="text-sm text-neutral-600">
  Start with a 14-day free trial — no credit card required.
</p>
```

with:

```tsx
<p className="text-sm text-neutral-600">
  {subtitleText}
</p>
```

### Intermediate verification

```bash
cd <repo>/frontend
pnpm --filter web check-types 2>&1 | tail -10
```

---

## STEP 5 — Mode-Dependent Subtitle (`/signup/account`)

**File**: `frontend/apps/web/src/app/signup/account/page.tsx`

Read the file first. The hardcoded subtitle is at line 242: `"Start your free 14-day trial — no credit card required."` The account page does NOT currently fetch subscription tiers — you'll add the hook call.

### 5a. Add the `useSubscriptionTiers` import

After the existing `useCognitoSignUp` import (line 40), add:

```tsx
import { useSubscriptionTiers } from "@/features/signup/hooks/useSubscriptionTiers";
```

### 5b. Call the hook + derive the subtitle

Inside the `SignupAccountPage` component (after the `useCognitoSignUp()` call, around line 105), add:

```tsx
// Mode-aware subtitle: if no trial tier exists, the app is in Founders mode.
const { data: tiers } = useSubscriptionTiers();
const hasTrialTier = !!tiers?.find((t) => t.is_trial);
const subtitleText = hasTrialTier
  ? "Start your free 14-day trial — no credit card required."
  : "Join the Founders program — free during development, no credit card required.";
```

> **Why fetch tiers on the account page?** `useSubscriptionTiers` is already written, cached by TanStack Query (5-min `staleTime`), and future-proofs the page. The data is already cached if the user navigated from a page that fetched it. The cost is negligible. (Design Doc §D.3 — Option A, decided.)

### 5c. Replace the hardcoded subtitle

At line 241–243, replace:

```tsx
<p className="text-sm text-neutral-600">
  Start your free 14-day trial — no credit card required.
</p>
```

with:

```tsx
<p className="text-sm text-neutral-600">
  {subtitleText}
</p>
```

### Intermediate verification

```bash
cd <repo>/frontend
pnpm --filter web test -- apps/web/src/features/signup/components/__tests__/SignupAccountPage.test.tsx 2>&1 | tail -10
```

---

## STEP 6 — Stale Session Cleanup on `/signup/account` Mount

**File**: `frontend/apps/web/src/app/signup/account/page.tsx`

Read the file first. The existing resume-check `useEffect` is at line 133.

### Problem

If a user previously completed Cognito SignUp + email verification (which calls Amplify `signIn` on the verify page), the browser holds a stale Amplify session. If their user/tenant was later deleted (e.g., Tom cleanup) and they try to sign up again, the stale session causes conflicts on the verify step (`confirmSignUp` → `signIn` detects the existing session).

### Fix

On `/signup/account` mount, if the user is already authenticated (`useAuth().isAuthenticated === true`), call `signOut()` to clear the stale session before showing the signup form. Also clear `WIZARD_TENANT_ID_KEY` from sessionStorage.

### 6a. Add the `useAuth` import

After the existing imports (around line 40), add:

```tsx
import { useAuth } from "@pilot/ui/auth";
```

### 6b. Destructure `isAuthenticated` + `signOut` from `useAuth`

Inside the `SignupAccountPage` component (near the top, around line 101), add:

```tsx
const { isAuthenticated, signOut } = useAuth();
```

### 6c. Add the stale-session sign-out `useEffect`

Add a new `useEffect` (can go right after the existing resume-check `useEffect` at line 156):

```tsx
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

### Design notes (do not re-litigate — see §Design Decisions):

- **Why sign out, not redirect?** The user is on `/signup/account` — they want to start a new signup. Redirecting them to `/dashboard` (if their session is valid) would be wrong if their tenant was deleted. Signing out clears the stale session and lets them proceed with a fresh `SignUp`.
- **Why clear `WIZARD_TENANT_ID_KEY`?** A stale `tenant_id` from a previous (now-deleted) tenant would cause the resume-check `useEffect` (line 133) to fetch `/api/v1/signup/{deletedTenantId}/state` → 404 → clear session + stay on account page. Clearing it proactively avoids the unnecessary 404.
- **Race condition**: The existing resume-check `useEffect` (line 133) and this new sign-out `useEffect` both fire on mount. The sign-out effect clears `WIZARD_TENANT_ID_KEY`, so the resume-check's `sessionStorage.getItem(WIZARD_TENANT_ID_KEY)` returns null → the resume-check is a no-op. No race.
- **Interaction with `SignupCompletionGuard` (STEP 2)**: `/signup/account` is OUTSIDE the `(authed)` group — so the guard never fires on this page. The sign-out here is the correct behavior for the account page: a user on `/signup/account` wants to start fresh.
- **`signOut()` is async**: It returns a Promise. The form renders immediately (the sign-out runs in the background). The `signOut` Promise resolves almost instantly (it's a local token clear, not a network call).

### Intermediate verification

```bash
cd <repo>/frontend
pnpm --filter web test -- apps/web/src/features/signup/components/__tests__/SignupAccountPage.test.tsx 2>&1 | tail -10
```

---

## Test Requirements

### TanStack Query — Required Setup for All Tests

**Always use `retry: false`** on the QueryClient in tests — default retry=3 causes test timeouts:

```typescript
function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}
```

**Never share a QueryClient instance across tests** — always create a fresh one per test.

### MSW in Tests — Correct Setup

The signup-state endpoint is **already mocked** in `signupHandlers.ts`. Use the existing handlers. For per-test overrides (e.g., testing the error/fail-open path):

```typescript
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import { handlers } from "@/mocks/handlers/index";

const server = setupServer(...handlers);
beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

// Per-test override — simulate API failure for the fail-open test:
server.use(
  http.get("/api/v1/signup/:tenantId/state", () =>
    HttpResponse.json({ error: "server error" }, { status: 500 }),
  ),
);
```

**Never mock `apiClient` directly** — MSW intercepts at the HTTP level.

### RBAC Testing — `AuthContext.Provider` Pattern (for SignupCompletionGuard tests)

`SignupCompletionGuard` consumes `useAuth()` for `user.tenantId`. Use the `AuthContext.Provider` directly:

```typescript
import { AuthContext } from "@pilot/ui/auth";
import type { AuthContextValue } from "@pilot/ui/auth";

function makeAuthValue(tenantId: string | null): AuthContextValue {
  return {
    user: tenantId
      ? { id: "u1", email: "test@example.com", role: "owner", tenantId, displayName: "Test", accessToken: "tok" }
      : null,
    isAuthenticated: !!tenantId,
    role: "owner",
    signIn: vi.fn(),
    confirmMfaChallenge: vi.fn(),
    signOut: vi.fn().mockResolvedValue(undefined),
    refreshSession: vi.fn().mockResolvedValue("tok"),
  };
}
```

### Unit Tests (co-located with source)

**`SignupCompletionGuard`** — file at `apps/web/src/components/__tests__/SignupCompletionGuard.test.tsx`:

Minimum coverage:
1. Renders children when `signup_state === 'complete'` (no redirect)
2. Redirects to the correct wizard step when `signup_state !== 'complete'` (e.g., `step3_phone` → `/signup/plan`)
3. Fails open on API error (renders children, no redirect)
4. Renders null while loading (when `tenantId` present + query pending)
5. Does not fire query when `tenantId` is null (no user)

**`SignupAccountPage`** — extend the existing test file at `apps/web/src/features/signup/components/__tests__/SignupAccountPage.test.tsx`:

Add tests for:
1. Password reveal toggle: clicking the toggle button changes input `type` from `password` to `text` and back
2. Toggle button has correct `aria-label` ("Show password" / "Hide password")
3. Mode-aware subtitle: shows Founders text when no trial tier exists (MSW override returning only `founders` tier)
4. Mode-aware subtitle: shows trial text when a trial tier exists (default MSW handler)
5. Stale session sign-out: when `isAuthenticated === true`, `signOut()` is called on mount

**`plan/page.tsx`** — extend existing tests or add to `apps/web/src/__tests__/batch_signup_ui_fix_1/`:

Add test for:
1. Mode-aware subtitle: shows Founders text when no trial tier exists

### Integration Tests (batch-scoped folder)

Create `apps/web/src/__tests__/batch_signup_ui_fix_1/`:

**`signup_completion_guard.integration.test.tsx`**:
1. Authenticated user with `signup_state === 'step3_phone'` is redirected to `/signup/plan`
2. Authenticated user with `signup_state === 'complete'` sees dashboard content (no redirect)
3. Authenticated user with API error sees dashboard content (fail open)

### Test Anti-Patterns — Never Do These

| ❌ Wrong | ✅ Correct |
|---|---|
| Mock `apiClient` directly in tests | Use MSW `setupServer` — never `vi.mock("@pilot/shared-api", ...)` |
| Shared `QueryClient` instance across tests | Create a fresh one per test via `createWrapper()` |
| Missing `retry: false` on QueryClient | Always set both `queries.retry: false` and `mutations.retry: false` |
| Asserting on total item count | Assert by specific IDs or content from the MSW fixture |
| Forget to mock `next/navigation` in web component test | Always `vi.mock("next/navigation", ...)` for any component using `useRouter` |
| Use `.toBeTruthy()` as the primary web test assertion | Web uses `toBeInTheDocument()` |

---

## Final Verification

> ❌ **BANNED COMMAND**: `npx vitest run` — **NEVER use this**. It bypasses the monorepo workspace setup and causes resolution failures. The ONLY correct test runner for `apps/web` is `pnpm --filter web test`.

### Phase 1 — Targeted tests (run after each task group during development)

```bash
cd <repo>/frontend

# ✅ CORRECT — Run only the package you're working in — fast feedback
pnpm --filter web test 2>&1 | tail -6

# ✅ CORRECT — Run a single test file (web):
pnpm --filter web test -- apps/web/src/components/__tests__/SignupCompletionGuard.test.tsx 2>&1 | tail -10
pnpm --filter web test -- apps/web/src/features/signup/components/__tests__/SignupAccountPage.test.tsx 2>&1 | tail -10
pnpm --filter web test -- apps/web/src/__tests__/batch_signup_ui_fix_1/ 2>&1 | tail -10

# ❌ WRONG — NEVER use these:
# npx vitest run ...          ← bypasses workspace; causes module resolution failures
# cd apps/web && npx vitest   ← same problem
```

Fix any failure before moving to the next task — including failures that appear pre-existing.

### Phase 2 — Full verification (run once at the very end, before DoD sign-off)

```bash
cd <repo>/frontend && echo "=== UI - Type Check ===" && pnpm --filter @pilot/ui check-types && echo "=== Web - Type Check ===" && pnpm --filter web check-types && echo "=== Mobile - Type Check ===" && pnpm --filter mobile build && echo "=== UI - Lint ===" && pnpm --filter @pilot/ui lint && echo "=== Web - Lint ===" && pnpm --filter web lint && echo "=== Mobile - Lint ===" && pnpm --filter mobile lint && echo "=== TYPE+LINT PASS ===" && echo "=== UI - Tests ===" && pnpm --filter @pilot/ui test 2>&1 | tail -6 && echo "=== Web - Tests ===" && pnpm --filter web test 2>&1 | tail -6 && echo "=== Mobile - Tests ===" && pnpm --filter mobile test 2>&1 | tail -8 && echo "=== MVP FINAL VERIFICATION COMPLETE ==="
```

> **Any failure in either phase must be fixed before the batch is declared done.** There is no "pre-existing failure" exception without explicit written confirmation from Tom. If you cannot identify the root cause → STOP and ask Tom.

---

## Definition of Done — SIGNUP-UI-FIX-1

Update `dev-docs/analysis/pilot-launch-plan.md` §14d (line 150) + §SIGNUP-UI-FIX-1 (line 604) when each item is done:

- [ ] Pre-modification regression baseline captured (zero pre-existing failures, or confirmed with Tom)
- [ ] `pnpm sync-api-types` run — no new type errors
- [ ] Design doc fully read before writing any code
- [ ] All mandatory source files read before modifying (account/page.tsx, plan/page.tsx, (authed)/layout.tsx, types.ts, useSubscriptionTiers.ts, AuthProvider.tsx, RequireAuth.tsx, signupHandlers.ts, handlers/index.ts, packages/ui/src/index.ts)
- [ ] `GET /api/v1/signup/{tenant_id}/state` endpoint verified in `openapi_schema_map.md`
- [ ] **STEP 1**: Password reveal toggle added to `/signup/account` — `showPassword`/`showConfirmPassword` state + `EyeIcon`/`EyeSlashIcon` buttons on both password fields
- [ ] **STEP 2**: `SignupCompletionGuard` created at `apps/web/src/components/SignupCompletionGuard.tsx` — fetches signup state, redirects incomplete users, fails open on error
- [ ] **STEP 3**: `SignupCompletionGuard` wired into `(authed)/layout.tsx` inside `RequireAuth`, wrapping all content
- [ ] **STEP 4**: `/signup/plan` subtitle is mode-aware (Founders text when no trial tier, trial text when trial tier exists)
- [ ] **STEP 5**: `/signup/account` subtitle is mode-aware (same derivation via `useSubscriptionTiers`)
- [ ] **STEP 6**: `/signup/account` calls `signOut()` on mount if `isAuthenticated` + clears `WIZARD_TENANT_ID_KEY`
- [ ] Password toggle: `aria-label` changes with state; `type="button"`; ≥24px target; `focus-visible:ring`; paste allowed
- [ ] `SignupCompletionGuard` fails open on API error (does not block authenticated users)
- [ ] No hand-written `useMemo`/`useCallback`/`React.memo` for render-perf; components are pure (React Compiler, rules §32)
- [ ] `SignupCompletionGuard` uses TanStack Query v5 object-form + colocated query key incl. `tenantId`; `staleTime: 0`; `retry: false`; `isPending` not `isLoading` (rules §33)
- [ ] No tenant-data fetching in Server Components — `SignupCompletionGuard` is `"use client"` (rules §35)
- [ ] axe-core zero violations + WCAG 2.2 AA spot-checks (target size ≥24px, focus not obscured, paste allowed on auth) (rules §36)
- [ ] No new `packages/ui` components (SignupCompletionGuard is app-specific)
- [ ] No new MSW handlers (signup-state endpoint already mocked in `signupHandlers.ts`)
- [ ] No new npm dependencies (`@heroicons/react` already installed)
- [ ] Unit tests pass (targeted run) — `SignupCompletionGuard.test.tsx` + extended `SignupAccountPage.test.tsx`
- [ ] Integration tests pass in `__tests__/batch_signup_ui_fix_1/`
- [ ] Zero TypeScript errors (`check-types` passes)
- [ ] Zero ESLint `no-hardcoded-design-values` warnings
- [ ] No regressions in pre-existing test suite (targeted run confirms)
- [ ] **Phase 2 FULL verification command passes** (`=== MVP FINAL VERIFICATION COMPLETE ===`):

  ```bash
  cd <repo>/frontend && echo "=== UI - Type Check ===" && pnpm --filter @pilot/ui check-types && echo "=== Web - Type Check ===" && pnpm --filter web check-types && echo "=== Mobile - Type Check ===" && pnpm --filter mobile build && echo "=== UI - Lint ===" && pnpm --filter @pilot/ui lint && echo "=== Web - Lint ===" && pnpm --filter web lint && echo "=== Mobile - Lint ===" && pnpm --filter mobile lint && echo "=== TYPE+LINT PASS ===" && echo "=== UI - Tests ===" && pnpm --filter @pilot/ui test 2>&1 | tail -6 && echo "=== Web - Tests ===" && pnpm --filter web test 2>&1 | tail -6 && echo "=== Mobile - Tests ===" && pnpm --filter mobile test 2>&1 | tail -8 && echo "=== MVP FINAL VERIFICATION COMPLETE ==="
  ```

- [ ] Final test count (before → after) documented in launch plan tracker
- [ ] Completion Summary added to launch plan §SIGNUP-UI-FIX-1

---

## Completion Summary

After all Definition of Done items are complete:

1. Add a **Completion Summary** subsection to `dev-docs/analysis/pilot-launch-plan.md` §SIGNUP-UI-FIX-1 (line 604) using the format below.
2. Update the launch plan §14d table row (line 150): change `☐ react prompt` → `✅ react` and the status column `☐` → `✅`.

### SIGNUP-UI-FIX-1 — Signup Wizard UI Fixes: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot React Engineer
**Baseline**: X passed, Y failed (web)
**Final**: X+N passed, Y failed (+N new tests)

#### What Was Accomplished

- Password reveal toggle (eyeball icon) added to both password fields on `/signup/account` — `aria-label` changes with state, paste still allowed (WCAG 2.2 SC 3.3.8)
- `SignupCompletionGuard` created and wired into `(authed)/layout.tsx` — redirects partially-onboarded users (signup_state !== 'complete') back to the correct wizard step; fails open on API error
- Mode-aware trial text on `/signup/plan` + `/signup/account` — derives Founders vs General Release mode from `useSubscriptionTiers` data (no trial tier = Founders mode)
- Stale Cognito session cleanup on `/signup/account` mount — calls `signOut()` if `isAuthenticated` + clears `WIZARD_TENANT_ID_KEY`

#### Files Changed / Created

| File | Action |
|---|---|
| `frontend/apps/web/src/components/SignupCompletionGuard.tsx` | Created — invisible guard; fetches signup state; redirects incomplete users to wizard |
| `frontend/apps/web/src/app/signup/account/page.tsx` | Updated — password reveal toggle + mode-aware subtitle + stale-session sign-out on mount |
| `frontend/apps/web/src/app/signup/plan/page.tsx` | Updated — mode-aware subtitle from `trialTier` derivation |
| `frontend/apps/web/src/app/(authed)/layout.tsx` | Updated — wrapped content in `<SignupCompletionGuard>` inside `<RequireAuth>` |

#### Tests Added

| Test File | Type | Tests | All Pass |
|---|---|---|---|
| `apps/web/src/components/__tests__/SignupCompletionGuard.test.tsx` | Unit | N | ✅ |
| `apps/web/src/features/signup/components/__tests__/SignupAccountPage.test.tsx` | Unit (extended) | +N | ✅ |
| `apps/web/src/__tests__/batch_signup_ui_fix_1/signup_completion_guard.integration.test.tsx` | Integration | N | ✅ |
