# FE-B2 — Login & Auth Shell: Batch Design Document

**Batch**: FE-B2  
**Phase**: 1 — Surface Design Session (Architect → React Engineer handoff)  
**Date**: 2026-05-21  
**Status**: READY FOR IMPLEMENTATION  
**Prereqs confirmed complete**: FE-B0 (foundation wired), FE-B1 (component library built)  
**Backend gate**: BE-B14 soft — Cognito-only login path works before BE-B14 lands; full signup wizard gates hard on BE-B14  
**Estimated effort**: 6–8 days  
**Test subfolder**: `apps/{web,mobile}/__tests__/batch_fe_b2/`  

---

## Source Reads Completed (Phase 1 Steps 1–7)

| # | Read | Source | Status |
|:--|:-----|:-------|:-------|
| 1 | FE-B2 batch detail | `pilot-app-mvp-frontend-impl-plan.md` §6 | ✅ |
| 2 | Auth architecture | `mvp-arch.md` §4.1–4.6 | ✅ |
| 3 | Auth & RBAC patterns | `pilot-react-engineer-methods.md` §5, §8 | ✅ |
| 4 | `AuthProvider`, `useAuth`, `types.ts`, `RequireAuth` | `packages/ui/src/auth/` | ✅ |
| 5 | `apiClient` interceptor | `packages/shared-api/src/client.ts` | ✅ |
| 6 | Web authed layout | `apps/web/src/app/(authed)/layout.tsx` | ✅ |
| 7 | Web login placeholder | `apps/web/src/app/login/page.tsx` | ✅ |
| 8 | Mobile root layout | `apps/mobile/app/_layout.tsx` | ✅ |
| 9 | Mobile tabs layout | `apps/mobile/app/(tabs)/_layout.tsx` | ✅ |
| 10 | `packages/ui/src/index.ts` component manifest | `packages/ui/src/index.ts` | ✅ |
| 11 | Codebase grep for existing login surface code | All `*.tsx` files | ✅ — none beyond placeholders |

---

## Table of Contents

- [A. Component Implementation Plan](#a-component-implementation-plan)
- [B. Execution Order](#b-execution-order)
- [C. New Routes](#c-new-routes)
- [D. API Endpoint Consumption](#d-api-endpoint-consumption)
- [E. Pattern Reuse Decisions](#e-pattern-reuse-decisions)
- [F. Shared Module Interfaces](#f-shared-module-interfaces)
- [G. Open Questions Resolved](#g-open-questions-resolved)
- [H. External Dependency Status](#h-external-dependency-status)
- [I. Test Plan](#i-test-plan)

---

## A. Component Implementation Plan

### A.1 Confirmed Pre-Existing Code (Do Not Reimplement)

These exist in the codebase and are consumed by FE-B2 surfaces without modification:

| Module | File | Public API Used by FE-B2 |
|:---|:---|:---|
| `AuthProvider` | `packages/ui/src/auth/AuthProvider.tsx` | Already wired at root; FE-B2 calls `signIn()` and `signOut()` via `useAuth()` |
| `useAuth` | `packages/ui/src/auth/useAuth.ts` | `{ user, role, signIn, signOut, refreshSession, isAuthenticated }` |
| `RequireAuth` | `packages/ui/src/auth/RequireAuth.tsx` | Already in `(authed)/layout.tsx`; FE-B2 upgrades redirect from `window.location.replace` to `router.replace` |
| `RoleGate` | `packages/ui/src/role-gate/RoleGate.tsx` | `<RoleGate role={['owner', 'office_staff']}>` for web-restricted roles |
| `useRequiresPermission` | `packages/ui/src/role-gate/useRequiresPermission.ts` | Used in post-login routing logic |
| `NotificationBanner` / `useNotificationQueue` | `packages/ui/src/notification-banner/` | Session-expired banner, login error banner, signed-out confirmation banner |
| `LoadingState` | `packages/ui/src/states/web/LoadingState.tsx` | Inline loading on form submit; full-page during initial session check |
| `ErrorState` | `packages/ui/src/states/web/ErrorState.tsx` | Used if login page itself cannot render (e.g., Amplify config failure) |
| `apiClient` | `packages/shared-api/src/client.ts` | Post-login profile fetch; interceptor already handles 401 refresh |
| `MFAEnrollmentWizard` skeleton | `packages/ui/src/mfa-enrollment-wizard/` | **NOT consumed in FE-B2** — MFA challenge at login uses a surface-specific `<MfaChallengeStep>` component |

### A.2 New Surface-Specific Components

All components below are **new** — confirmed absent via codebase grep (no `LoginForm`, `loginForm`, `useLogin`, `passwordReset`, `MfaChallenge`, `sessionExpiry` exist in any `.tsx` or `.ts` file).

---

#### `LoginForm` (web)

| Field | Value |
|:---|:---|
| **File** | `apps/web/src/features/login/components/LoginForm.tsx` |
| **Purpose** | Email + password form for Cognito authentication on web |
| **Parent** | `apps/web/src/app/login/page.tsx` |

**Props interface:**
```typescript
interface LoginFormProps {
  onSuccess: (role: PilotRole) => void;
  /** Dev-only: when true, renders role-selector dropdown instead of password field */
  mockMode?: boolean;
}
```

**Behavior:**
- Email `<Input>` + password `<Input type="password">` using shadcn/ui primitives
- "Forgot password?" link → navigates to `/password-reset`
- Submit → calls `useAuth().signIn(email, password)`
- Loading state: submit button transitions to `<LoadingState type="inline" />` spinner inline within the button; form fields remain visible and read-only during submit
- Error state: inline below the form using `useNotificationQueue().enqueue()` with `severity="error"` — NOT a full `<ErrorState>` component (too heavy for a transient form error)
- Cognito MFA challenge: if `amplifySignIn` resolves with a `nextStep.signInStep !== 'DONE'` value, transitions form area to render `<MfaChallengeStep>` (see below)
- **Mock mode** (`NEXT_PUBLIC_USE_MOCK_AUTH=true`): renders email input + role-selector `<Select>` (owner / tech / office_staff / operator) + "Sign in as [role]" button; no password field; no Cognito calls
- `onSuccess(role)` fires after successful sign-in; caller performs role-based redirect

---

#### `LoginForm` (mobile)

| Field | Value |
|:---|:---|
| **File** | `apps/mobile/features/login/components/LoginForm.tsx` |
| **Purpose** | Email + password form for Cognito authentication on mobile |
| **Parent** | `apps/mobile/app/(auth)/login.tsx` |

**Props interface:**
```typescript
interface LoginFormProps {
  onSuccess: (role: PilotRole) => void;
  mockMode?: boolean;
}
```

**Behavior:**
- Gluestack-UI `Input` + `Button` primitives; minimum 44×44 px touch targets (`size="xl"`)
- `returnKeyType="next"` on email input; `returnKeyType="done"` on password input
- `keyboardType="email-address"` + `autoCapitalize="none"` on email input
- `secureTextEntry` on password input
- Haptic feedback via `expo-haptics` on error (`ImpactFeedbackStyle.Light`)
- Loading state: full-page `<LoadingState type="full-page" />` overlay during sign-in (mobile pattern — keyboard dismissed; user should not interact during auth roundtrip)
- Error state: `useNotificationQueue().enqueue()` with `severity="error"` — banner appears above content
- MFA challenge: same pattern as web — `<MfaChallengeStep>` renders in place of the form area
- **Mock mode** (`EXPO_PUBLIC_USE_MOCK_AUTH=true`): email input + role picker + "Sign in as [role]" button
- `onSuccess(role)` fires after successful sign-in; caller performs tab navigation

---

#### `MfaChallengeStep` (web + mobile, surface-scoped)

| Field | Value |
|:---|:---|
| **File (web)** | `apps/web/src/features/login/components/MfaChallengeStep.tsx` |
| **File (mobile)** | `apps/mobile/features/login/components/MfaChallengeStep.tsx` |
| **Purpose** | Minimal MFA code-entry UI for the login challenge. NOT the full enrollment wizard (FE-B12). |
| **Parent** | Rendered inline by `LoginForm` when Amplify returns a sign-in challenge |

**Props interface:**
```typescript
type MfaMethod = 'TOTP' | 'SMS_MFA' | 'EMAIL_OTP' | 'SOFTWARE_TOKEN_MFA';

interface MfaChallengeStepProps {
  challengeName: MfaMethod;
  /** Destination hint from Cognito (e.g., "****1234" for SMS, email domain for EMAIL_OTP) */
  destination?: string;
  onConfirm: (code: string) => Promise<void>;
  onCancel: () => void;
  /** If user has multiple enrolled methods, parent can pass alternatives */
  alternativeMethods?: MfaMethod[];
  onSwitchMethod?: (method: MfaMethod) => void;
}
```

**Behavior:**
- 6-digit code input (numeric keyboard on mobile)
- Submit button → calls `onConfirm(code)` → internally calls Amplify `confirmSignIn({ challengeResponse: code })`
- "Use a different method" link shown only if `alternativeMethods` is non-empty
- "Use recovery code" tertiary link → expands a free-text input for the 10-char recovery code
- Error: inline message below the code input ("Incorrect code. Try again.")
- Cancel → calls `onCancel()` → parent resets form to email+password step
- **Does NOT show enrollment progress** — if MFA is required but user has no method enrolled, this component is not shown; instead, user sees a separate `<MfaEnrollmentRequiredGate>` (see below)

> **Scope boundary**: `MfaChallengeStep` handles the *challenge* flow at login (for already-enrolled users). It is **not** the `<MFAEnrollmentWizard>` skeleton from FE-B1 — that is fleshed out in FE-B12 for the Settings surface. FE-B2 does not modify the FE-B1 `<MFAEnrollmentWizard>` skeleton's public API.

---

#### `MfaEnrollmentRequiredGate` (web + mobile, surface-scoped)

| Field | Value |
|:---|:---|
| **File (web)** | `apps/web/src/features/login/components/MfaEnrollmentRequiredGate.tsx` |
| **File (mobile)** | `apps/mobile/features/login/components/MfaEnrollmentRequiredGate.tsx` |
| **Purpose** | Shown when login succeeds but tenant-required MFA policy is active and user has no enrolled methods, AND grace period has expired |

**Props interface:**
```typescript
interface MfaEnrollmentRequiredGateProps {
  gracePeriodEndsAt?: string; // ISO date string — if present, we're still in grace
  onBeginEnrollment: () => void; // routes to MFA settings in FE-B12 (or shows banner for now)
  onSignOut: () => void;
}
```

**Behavior in FE-B2 (minimal):**
- During grace period: shows persistent `<NotificationBanner severity="warning">` "MFA enrollment required within N days. [Set up now →]" and allows app access. The "Set up now" link routes to `/settings/account` (which becomes real in FE-B12; in FE-B2 it's a placeholder route that already exists from FE-B0).
- Post-grace: shows a blocking screen — cannot access app — with copy "Multi-factor authentication is required by your organization. Set it up to continue." + "Set up MFA" button (routes to `/settings/account`) + "Sign out" link.
- Full MFA enrollment wizard lives in FE-B12; FE-B2 only provides this gate and routing stub.

---

#### `PasswordResetFlow` (web)

| Field | Value |
|:---|:---|
| **File** | `apps/web/src/features/login/components/PasswordResetFlow.tsx` |
| **Purpose** | Three-step Cognito `forgotPassword` → confirmation code → new password flow on web |
| **Parent** | `apps/web/src/app/password-reset/page.tsx` |

**Props interface:**
```typescript
interface PasswordResetFlowProps {
  onSuccess: () => void; // navigates to /login with success banner
}
```

**Internal step state** (managed internally, not via URL params):
```
step: 'request-reset' | 'enter-code' | 'success'
```

**Step 1 — `request-reset`:**
- Email input + "Send reset code" button
- Calls `resetPassword({ username: email })` (Amplify v6 API)
- On success → transitions to `enter-code` step
- Loading: inline button spinner

**Step 2 — `enter-code`:**
- Shows masked destination (e.g., "Code sent to `r***@example.com`")
- 6-digit code input + new password input + confirm password input
- Calls `confirmResetPassword({ username, confirmationCode, newPassword })` (Amplify v6 API)
- Password validation: min 12 chars, requires lowercase, uppercase, numbers, symbols (mirrors Cognito policy in `mvp-arch.md` §4.1)
- "Resend code" link → re-calls step 1 without form reset
- On success → transitions to `success` step

**Step 3 — `success`:**
- "Password updated!" confirmation with "Sign in" link → navigates to `/login?passwordReset=true`

**Rationale for single page with step transitions (not separate routes)**:
- No use case for deep-linking to a mid-flow reset step
- Simpler browser history (no back-button pollution mid-flow)
- Confirmation code is short-lived (Cognito default: 1h) — sharing a mid-flow URL serves no purpose

---

#### `PasswordResetFlow` (mobile)

| Field | Value |
|:---|:---|
| **File** | `apps/mobile/features/login/components/PasswordResetFlow.tsx` |
| **Purpose** | Same three-step flow on mobile, presented as a modal over the login screen |
| **Parent** | `apps/mobile/app/(auth)/password-reset.tsx` (modal presentation) |

**Behavior differences from web:**
- Presented as `Stack.Screen` with `presentation: "modal"` (same pattern as `apps/mobile/app/modal.tsx`)
- "Back to Sign In" header left button → dismiss modal
- Same step state machine as web
- Keyboard-aware scroll (`KeyboardAvoidingView`) for password inputs

---

#### `useLoginFlow` hook (web)

| Field | Value |
|:---|:---|
| **File** | `apps/web/src/features/login/hooks/useLoginFlow.ts` |
| **Purpose** | Encapsulates login form state, signIn call, MFA challenge handling, error management, and post-login redirect |

```typescript
interface UseLoginFlowResult {
  step: 'credentials' | 'mfa-challenge' | 'mfa-enrollment-required';
  isLoading: boolean;
  error: string | null;
  mfaChallenge: { challengeName: MfaMethod; destination?: string } | null;
  submitCredentials: (email: string, password: string) => Promise<void>;
  submitMfaCode: (code: string) => Promise<void>;
  cancelMfa: () => void;
}
```

**Behavior:**
- Calls `useAuth().signIn(email, password)`
- Current `AuthProvider.signIn()` does not surface Amplify's `nextStep` — FE-B2 must extend the `signIn` signature to return `{ nextStep: AmplifySignInNextStep }` so `useLoginFlow` can branch on MFA challenge (see §F for updated interface)
- On `nextStep.signInStep === 'CONFIRM_SIGN_IN_WITH_TOTP_CODE'` / `'CONFIRM_SIGN_IN_WITH_SMS_CODE'` / `'CONFIRM_SIGN_IN_WITH_EMAIL_CODE'` → sets `step = 'mfa-challenge'`
- On `nextStep.signInStep === 'CONTINUE_SIGN_IN_WITH_MFA_SETUP_SELECTION'` → sets `step = 'mfa-enrollment-required'`
- On `nextStep.signInStep === 'DONE'` → calls `onSuccess(role)` → role-based redirect

---

#### `useLoginFlow` hook (mobile)

| Field | Value |
|:---|:---|
| **File** | `apps/mobile/features/login/hooks/useLoginFlow.ts` |
| **Purpose** | Same as web hook, but for mobile — triggers haptic on error |

Same interface as web; platform-specific side effects only (haptics).

---

#### `usePostLoginRedirect` hook (web + mobile)

| Field | Value |
|:---|:---|
| **File (web)** | `apps/web/src/hooks/usePostLoginRedirect.ts` |
| **File (mobile)** | `apps/mobile/hooks/usePostLoginRedirect.ts` |
| **Purpose** | Centralizes role → route mapping. Called after successful login to redirect to correct destination. |

```typescript
// web
function usePostLoginRedirect(): { redirectForRole: (role: PilotRole) => void }

// mobile
function usePostLoginRedirect(): { navigateForRole: (role: PilotRole) => void }
```

**Role → Route mapping (authoritative):**

| Role | Web route | Mobile destination |
|:-----|:----------|:-------------------|
| `owner` | `/dashboard` | `(tabs)/` (Home tab) |
| `tech` | ❌ Blocked (see note) | `(tabs)/` (Home tab) |
| `office_staff` | `/dashboard` | `(tabs)/` (Home tab) |
| `operator` | `/dashboard` | `(tabs)/` (Home tab) |

> **Tech on web**: `tech` role users attempting web login see a `<NotificationBanner severity="info">` with copy "The Pilot web app is for owners and office staff. Please use the mobile app." and are signed out after 5 seconds, then redirected to `/login`. Techs are NOT silently redirected to a different page — the clear message is intentional so they understand where to go.

---

#### `useSessionExpiry` hook (web + mobile)

| Field | Value |
|:---|:---|
| **File (web)** | `apps/web/src/hooks/useSessionExpiry.ts` |
| **File (mobile)** | `apps/mobile/hooks/useSessionExpiry.ts` |
| **Purpose** | Subscribes to `auth:session-expired` custom event emitted by `apiClient` on unrecoverable 401. Enqueues a session-expired `<NotificationBanner>` and signs out. |

```typescript
function useSessionExpiry(): void
// Side-effects only: subscribes on mount, unsubscribes on unmount
// Enqueues NotificationBanner severity="critical" with 12s auto-dismiss
// Copy: "Your session expired — please sign in again."
// CTA: "Sign in" button → calls signOut() + router.replace('/login')
```

**Integration point**: This hook is called once in `apps/web/src/app/(authed)/layout.tsx` and once in the authenticated mobile layout (see §C). The `apiClient` 401 interceptor already has the scaffold in place — on refresh failure, it currently just `Promise.reject`s. FE-B2 adds the `window.dispatchEvent(new CustomEvent('auth:session-expired'))` call before the rejection (web) or equivalent EventEmitter (mobile).

---

#### `SessionExpiredBanner` (web + mobile, thin wrappers)

Not a standalone component — `useSessionExpiry()` calls `useNotificationQueue().enqueue()` directly. No new component needed; FE-B1's `<NotificationBanner>` handles the visual rendering.

---

### A.3 Route Files (New)

| File | Type |
|:-----|:-----|
| `apps/web/src/app/password-reset/page.tsx` | New Next.js page (client component) |
| `apps/mobile/app/(auth)/_layout.tsx` | New Expo Router layout (auth route group) |
| `apps/mobile/app/(auth)/login.tsx` | New Expo Router screen |
| `apps/mobile/app/(auth)/password-reset.tsx` | New Expo Router modal screen |

---

### A.4 `AuthProvider.signIn` Upgrade (FE-B2 modifies existing shared module)

The current `signIn(email, password): Promise<void>` in `packages/ui/src/auth/AuthProvider.tsx` does not surface Amplify's `nextStep` response. FE-B2 **must upgrade** this signature to:

```typescript
signIn: (email: string, password: string) => Promise<{ nextStep: SignInOutput['nextStep'] }>
```

This is a **backward-compatible extension**: existing callers that ignore the return value continue to work. The `useLoginFlow` hook reads `nextStep` to branch on MFA challenge vs. success.

**Required changes:**
- `packages/ui/src/auth/types.ts` — update `AuthContextValue.signIn` return type
- `packages/ui/src/auth/AuthProvider.tsx` — return `nextStep` from the resolved signIn
- `packages/ui/src/auth/useAuth.ts` — no change (hook just re-exports context)

> The `SignInOutput` type is imported from `aws-amplify/auth`. In mock mode, `signIn` returns `{ nextStep: { signInStep: 'DONE' } }`.

---

### A.5 `RequireAuth` Upgrade (FE-B2 removes `window.location.replace` placeholder)

`packages/ui/src/auth/RequireAuth.tsx` currently uses `window.location.replace(redirectTo)` as a placeholder (per FE-B0 Implementation Detail Record decision #3). FE-B2 upgrades this:

**Web**: `RequireAuth` is already used in a `"use client"` context (`(authed)/layout.tsx`). The upgrade passes a `redirect` function prop rather than calling `window.location.replace` directly, making the component testable and framework-agnostic:

```typescript
// Updated RequireAuth — adds onRedirect prop
interface RequireAuthProps {
  children: React.ReactNode;
  redirectTo: string;
  /** Platform-specific redirect function. Web: router.replace; Mobile: router.replace */
  onRedirect?: (path: string) => void;
}
```

The `(authed)/layout.tsx` consumer passes `router.replace` from `next/navigation`. Mobile `(authed)/_layout.tsx` passes `router.replace` from `expo-router`.

---

### A.6 MSW Handlers for FE-B2

Since BE-B14 (signup endpoints) is the soft gate, FE-B2 needs MSW handlers for the post-login profile fetch endpoint:

| File | Handlers |
|:-----|:---------|
| `apps/web/src/mocks/handlers/auth.ts` | `GET /api/v1/auth/me` — returns mock `PilotUser` shape matching role |
| `apps/mobile/mocks/handlers/auth.ts` | Same handlers for mobile |

---

## B. Execution Order

| # | Item | Dependency Rationale |
|:--|:-----|:--------------------|
| 1 | **Upgrade `AuthProvider.signIn` return type** | Unblocks `useLoginFlow` hook; all downstream login components depend on this. Must be first — shared module change. |
| 2 | **Upgrade `RequireAuth` with `onRedirect` prop** | Unblocks proper web + mobile redirect from `(authed)/layout.tsx`. Small change to existing module. |
| 3 | **`useSessionExpiry` hook (web)** + **wire into `(authed)/layout.tsx`** | Session expiry must be wired before building authenticated flows that would be silently broken on 401. Wire the event dispatch in `apiClient` at the same time. |
| 4 | **`usePostLoginRedirect` hook (web)** | Needed by `useLoginFlow`; defines the authoritative role → route table. |
| 5 | **`useLoginFlow` hook (web)** | Encapsulates form logic; `LoginForm` is a thin rendering shell over this hook. Build hook before form. |
| 6 | **`LoginForm` (web)** + **`MfaChallengeStep` (web)** + **`MfaEnrollmentRequiredGate` (web)** | Compose the complete login surface. Build together as the components are co-located and tested together. |
| 7 | **`apps/web/src/app/login/page.tsx`** (replace placeholder) | Slots `LoginForm` into the existing route. |
| 8 | **`PasswordResetFlow` (web)** + **`apps/web/src/app/password-reset/page.tsx`** (new route) | Self-contained sub-flow. No dependencies on login form beyond `useAuth`. |
| 9 | **`useSessionExpiry` hook (mobile)** + **wire into mobile auth layout** | Mirror of step 3 for mobile. |
| 10 | **`usePostLoginRedirect` hook (mobile)** + **`useLoginFlow` hook (mobile)** | Mobile equivalents of steps 4–5. |
| 11 | **`apps/mobile/app/(auth)/_layout.tsx`** (new Expo Router auth group) | Create the mobile `(auth)` route group before adding screens to it. |
| 12 | **`LoginForm` (mobile)** + **`MfaChallengeStep` (mobile)** + **`apps/mobile/app/(auth)/login.tsx`** | Mobile login surface. |
| 13 | **`PasswordResetFlow` (mobile)** + **`apps/mobile/app/(auth)/password-reset.tsx`** | Mobile password reset as modal presentation. |
| 14 | **Logout wiring (web + mobile)** | Wire `signOut()` + TanStack Query cache clear + redirect. Web: add to header/nav component placeholder. Mobile: add to Owner tab placeholder. |
| 15 | **MSW handlers** for `GET /api/v1/auth/me` | Wire the post-login profile fetch for integration tests. |
| 16 | **Unit tests** (per §I) | Co-located with each component. Write as each component is built. |
| 17 | **Integration tests** (per §I) | After all surfaces complete; tests compose multiple components. |
| 18 | **E2E tests** (per §I) | After integration tests pass; requires dev Cognito or stable MockAuthProvider. |

---

## C. New Routes

### Web (Next.js App Router)

| Route file | URL | Auth required | RBAC gate | Notes |
|:-----------|:----|:-------------|:----------|:------|
| `apps/web/src/app/login/page.tsx` | `/login` | No | None | Replace placeholder; client component |
| `apps/web/src/app/password-reset/page.tsx` | `/password-reset` | No | None | New file; single-page multi-step flow |

**No new authenticated routes** are added in FE-B2. The existing `(authed)/layout.tsx` at `apps/web/src/app/(authed)/layout.tsx` gains:
- `useSessionExpiry()` hook call
- Upgraded `<RequireAuth redirectTo="/login" onRedirect={router.replace}>` with `next/navigation` router

### Mobile (Expo Router)

| Route file | Screen | Auth required | RBAC gate | Notes |
|:-----------|:-------|:-------------|:----------|:------|
| `apps/mobile/app/(auth)/_layout.tsx` | Auth group layout | No | None | New route group; `Stack` presentation |
| `apps/mobile/app/(auth)/login.tsx` | Login screen | No | None | New file; replaces missing mobile login |
| `apps/mobile/app/(auth)/password-reset.tsx` | Password reset | No | None | Modal presentation over login |

**Mobile root `_layout.tsx` change**: Add `<Stack.Screen name="(auth)" options={{ headerShown: false }} />` to the `Stack` navigator. The current layout only has `(tabs)` and `modal` — `(auth)` must be added so Expo Router knows the route group exists.

**Mobile auth guard change**: The `(tabs)/_layout.tsx` does not currently guard against unauthenticated access. FE-B2 adds an auth-check hook at the root `_layout.tsx` level that redirects unauthenticated users to `(auth)/login`. This is consistent with how `RequireAuth` works on web — the check lives at the top-level layout, not per-tab.

> **Route slot confirmation**: All web routes slot into FE-B0's routing skeleton correctly. `/login` already exists as a placeholder (`apps/web/src/app/login/page.tsx`). `/password-reset` is new. No existing routes are removed or renamed.

---

## D. API Endpoint Consumption

### Cognito via Amplify (primary auth path — not FastAPI endpoints)

FE-B2 consumes Amplify Auth APIs directly. These are **not** FastAPI REST endpoints routed through `apiClient`.

| Amplify API | Amplify v6 function | Used in |
|:------------|:-------------------|:--------|
| Sign in | `signIn({ username, password })` from `aws-amplify/auth` | `AuthProvider.signIn()` |
| Confirm MFA challenge | `confirmSignIn({ challengeResponse })` from `aws-amplify/auth` | `useLoginFlow.submitMfaCode()` |
| Sign out | `signOut()` from `aws-amplify/auth` | `AuthProvider.signOut()` |
| Refresh session | `fetchAuthSession({ forceRefresh: true })` from `aws-amplify/auth` | `apiClient` 401 interceptor + `AuthProvider.refreshSession()` |
| Initiate password reset | `resetPassword({ username })` from `aws-amplify/auth` | `PasswordResetFlow` step 1 |
| Confirm password reset | `confirmResetPassword({ username, confirmationCode, newPassword })` from `aws-amplify/auth` | `PasswordResetFlow` step 2 |

### FastAPI endpoint (post-login profile fetch)

| Endpoint | Method | TanStack Query hook | MSW handler | When called |
|:---------|:-------|:--------------------|:------------|:------------|
| `/api/v1/auth/me` | `GET` | `useGetCurrentUser()` (new — see §F) | `apps/web/src/mocks/handlers/auth.ts` | After successful login, before redirect, to hydrate role into TanStack Query cache |

> **Note**: BE-B14 provides the full signup + user provisioning endpoints. The `/api/v1/auth/me` endpoint is a simpler "who am I" endpoint that returns the authenticated user's tenant + role from the backend DB (cross-referencing the Cognito JWT's `sub`). This endpoint must exist before production login works end-to-end. If it does not exist yet, the mock MSW handler stands in.

**MSW handler shape:**
```typescript
// apps/web/src/mocks/handlers/auth.ts
http.get('/api/v1/auth/me', () =>
  HttpResponse.json({
    user_id: 'mock-user-001',
    tenant_id: 'mock-tenant-001',
    email: 'mockuser@pilot-dev.example.com',
    display_name: 'Mock User',
    role: 'owner',
  })
)
```

### No Cognito social/SAML login in FE-B2

Google and Apple social login (arch doc §4.1) and SAML enterprise login are deferred to post-MVP. FE-B2 implements email+password only.

---

## E. Pattern Reuse Decisions

### From FE-B0

| Pattern | Shared Module | Import Path | How FE-B2 Uses It |
|:--------|:-------------|:------------|:------------------|
| `useAuth()` hook | `packages/ui/src/auth/useAuth.ts` | `import { useAuth } from '@pilot/ui/auth'` | `useLoginFlow` calls `signIn()`, `signOut()`, `refreshSession()` |
| `<AuthProvider>` | `packages/ui/src/auth/AuthProvider.tsx` | Already in providers; FE-B2 does not re-wire | Modified to return `nextStep` from `signIn` |
| `<RequireAuth>` | `packages/ui/src/auth/RequireAuth.tsx` | `import { RequireAuth } from '@pilot/ui/auth'` | Updated in `(authed)/layout.tsx` with `onRedirect` prop |
| `<RoleGate>` | `packages/ui/src/role-gate/RoleGate.tsx` | `import { RoleGate } from '@pilot/ui/role-gate'` | Wraps web-only content in post-login; gates `tech` role out of web |
| `apiClient` | `packages/shared-api/src/client.ts` | `import { apiClient } from '@pilot/shared-api'` | Post-login `GET /api/v1/auth/me` call; FE-B2 adds `auth:session-expired` event dispatch |
| `ROLE_PERMISSION_MAP` | `packages/ui/src/role-gate/permissions.ts` | `import { ROLE_PERMISSION_MAP } from '@pilot/ui/role-gate'` | `usePostLoginRedirect` references roles |

### From FE-B1

| Pattern | Shared Module | Import Path | How FE-B2 Uses It |
|:--------|:-------------|:------------|:------------------|
| `<LoadingState type="inline">` | `packages/ui/src/states/web/LoadingState.tsx` | `import { LoadingState } from '@pilot/ui/states'` | Web: inline spinner in submit button |
| `<LoadingState type="full-page">` | `packages/ui/src/states/mobile/LoadingState.tsx` | `import { LoadingState } from '@pilot/ui/states'` | Mobile: full-page overlay during sign-in |
| `useNotificationQueue()` | `packages/ui/src/notification-banner/useNotificationQueue.ts` | `import { useNotificationQueue } from '@pilot/ui/notification-banner'` | Login errors, session expiry, signed-out confirmation, tech-on-web restriction |
| `<NotificationBanner>` | Already rendered via `NotificationPortal` in `(authed)/layout.tsx` | No additional wiring needed for web | Session-expired + signed-out banners render via the queue |
| `AUTO_DISMISS_MS` | `packages/ui/src/notification-banner/types.ts` | `import { AUTO_DISMISS_MS } from '@pilot/ui/notification-banner/types'` | `useSessionExpiry` uses `AUTO_DISMISS_MS.CRITICAL` (12 000 ms) |

---

## F. Shared Module Interfaces

### F.1 Updated `AuthContextValue` (in `packages/ui/src/auth/types.ts`)

The `signIn` return type is upgraded from `Promise<void>` to surface Amplify's `nextStep`:

```typescript
// packages/ui/src/auth/types.ts — UPDATED

import type { SignInOutput } from 'aws-amplify/auth';

export type PilotRole = "owner" | "tech" | "office_staff" | "operator";

export interface PilotUser {
  id: string;
  email: string;
  role: PilotRole;
  tenantId: string;
  displayName: string;
  accessToken: string;
}

export interface AuthContextValue {
  user: PilotUser | null;
  isAuthenticated: boolean;
  role: PilotRole | null;
  /**
   * Signs in via Amplify Cognito. Returns nextStep so callers can handle
   * MFA challenges. In mock mode returns { nextStep: { signInStep: 'DONE' } }.
   *
   * Callers MUST check nextStep.signInStep before assuming login is complete.
   */
  signIn: (email: string, password: string) => Promise<{ nextStep: SignInOutput['nextStep'] }>;
  /**
   * Confirms an MFA challenge during sign-in. Called after signIn returns
   * a non-DONE nextStep. In mock mode, always resolves successfully.
   */
  confirmMfaChallenge: (code: string) => Promise<{ nextStep: SignInOutput['nextStep'] }>;
  signOut: () => Promise<void>;
  /** Returns a fresh accessToken; called by apiClient 401 interceptor */
  refreshSession: () => Promise<string>;
}
```

> **`confirmMfaChallenge` is new** — added to `AuthContextValue` so `useLoginFlow` doesn't need to import Amplify directly. In mock mode it returns `{ nextStep: { signInStep: 'DONE' } }`. In production it calls `confirmSignIn({ challengeResponse: code })`.

### F.2 `useGetCurrentUser` TanStack Query hook (new, in `packages/shared-api/`)

```typescript
// packages/shared-api/src/auth.ts (new file)

import { useQuery } from '@tanstack/react-query';
import { apiClient } from './client';

export interface CurrentUserApiResponse {
  user_id: string;
  tenant_id: string;
  email: string;
  display_name: string;
  role: 'owner' | 'tech' | 'office_staff' | 'operator';
}

export const AUTH_QUERY_KEYS = {
  currentUser: ['auth', 'currentUser'] as const,
};

export function useGetCurrentUser() {
  return useQuery({
    queryKey: AUTH_QUERY_KEYS.currentUser,
    queryFn: async (): Promise<CurrentUserApiResponse> => {
      const { data } = await apiClient.get<CurrentUserApiResponse>('/api/v1/auth/me');
      return data;
    },
    staleTime: 5 * 60 * 1000, // 5 min — role doesn't change mid-session
    retry: false,             // Don't retry auth errors
  });
}
```

### F.3 `useSessionExpiry` hook signature (new, platform-specific)

```typescript
// apps/web/src/hooks/useSessionExpiry.ts
// apps/mobile/hooks/useSessionExpiry.ts

/**
 * Subscribes to auth:session-expired events emitted by apiClient on
 * unrecoverable 401. On event: enqueues a critical NotificationBanner
 * and calls signOut() + redirects to /login.
 *
 * Usage: call once at the top of the authenticated layout.
 * No return value — side-effects only.
 */
function useSessionExpiry(): void
```

**Event dispatch location** — `packages/shared-api/src/client.ts` response interceptor, in the `catch` block after refresh fails:
```typescript
// Add to the existing catch block in the 401 interceptor:
if (typeof window !== 'undefined') {
  window.dispatchEvent(new CustomEvent('auth:session-expired'));
}
// On mobile: emit via a shared EventEmitter singleton
```

### F.4 `usePostLoginRedirect` hook signature (new, platform-specific)

```typescript
// apps/web/src/hooks/usePostLoginRedirect.ts
export function usePostLoginRedirect(): {
  redirectForRole: (role: PilotRole) => void;
}

// apps/mobile/hooks/usePostLoginRedirect.ts
export function usePostLoginRedirect(): {
  navigateForRole: (role: PilotRole) => void;
}
```

### F.5 Updated `RequireAuthProps` (in `packages/ui/src/auth/types.ts`)

```typescript
export interface RequireAuthProps {
  children: React.ReactNode;
  redirectTo: string;
  /**
   * Platform-specific redirect function.
   * Web: router.replace from next/navigation.
   * Mobile: router.replace from expo-router.
   * Falls back to window.location.replace if not provided (for test compatibility).
   */
  onRedirect?: (path: string) => void;
}
```

---

## G. Open Questions Resolved

### G.1 — Login surface form design: which state components?

**Decision**: Inline loading (not full-page) on web; full-page loading on mobile.

**Reasoning**: On web, the login form is a narrow centered card. Showing a full-page skeleton while a network request completes for ~200ms is visually jarring. An inline spinner in the submit button is standard SaaS UX (matches Vercel, Linear, etc.) and keeps the user's typed email/password visible. On mobile, the keyboard must be dismissed during auth; full-page overlay is appropriate to signal "processing, do not interact."

Error states: use `useNotificationQueue().enqueue()` for transient form errors (wrong password, network error). Do NOT use `<ErrorState type="network">` for login form errors — `<ErrorState>` is designed for empty-state surfaces, not inline form validation feedback.

### G.2 — MFA challenge handling at login

**Decision**: FE-B2 ships a **surface-scoped `<MfaChallengeStep>` component** that handles Cognito's MFA challenge inline in the login flow. This is NOT the full `<MFAEnrollmentWizard>` from FE-B1. Full enrollment is FE-B12.

**Reasoning**: Cognito's `signIn` can return an MFA challenge on first login if the tenant has required MFA and the user previously enrolled. This must be handled in FE-B2 or every MFA-enrolled user will be permanently unable to log in after FE-B2 ships. The challenge step is simple (enter a 6-digit code) and does NOT require the full enrollment wizard UI.

The `<MFAEnrollmentWizard>` skeleton from FE-B1 is for the *enrollment* flow at `/settings/account` (FE-B12). The `<MfaChallengeStep>` is for the *challenge* flow at login — distinct surfaces, distinct components.

**Edge case: user enrolled in MFA on Cognito but not yet via Pilot wizard** — Cognito challenge still fires. `<MfaChallengeStep>` handles it. No dependency on the Pilot `user_mfa_method` DB table for the challenge flow.

### G.3 — Password reset flow: single page vs. separate routes

**Decision**: Single page (`/password-reset`) with internal step state transitions. Same for mobile (modal with step transitions).

**Reasoning**: No use case for deep-linking to a mid-flow reset step. Confirmation codes are short-lived (~1h by Cognito default). The "Resend code" action is a link within the page, not a back-navigation. Using internal state (not URL params) means no "back" button takes the user to a mid-flow state they can't complete.

Alternative considered: `/password-reset/request`, `/password-reset/confirm` — rejected because it adds route management complexity for a flow that users complete in under 2 minutes.

### G.4 — JWT refresh failure modal design

**Decision**: No new modal component. FE-B1's `<NotificationBanner>` (via `useNotificationQueue`) handles the session-expired UX. `severity="critical"` (12-second auto-dismiss) with a "Sign in" CTA button.

**Reasoning**: A full-page modal for session expiry is heavy UX for an event that only occurs every 30 days (Cognito refresh token TTL). A top-of-page banner is less disruptive and is already the established pattern in this codebase. The CTA in the banner calls `signOut()` + `router.replace('/login')`.

The `useSessionExpiry` hook is the integration point — wired into the authenticated layout, it subscribes to the `auth:session-expired` custom event that `apiClient` dispatches when refresh fails.

### G.5 — Role-based redirect: exact routes

**Decision**: The authoritative role → route mapping is defined in §A.2 and §F.4. Exact routes confirmed against FE-B0 Implementation Detail Record:

| Role | Web | Mobile |
|:-----|:----|:-------|
| `owner` | `/dashboard` | `(tabs)/index` (Home tab) |
| `tech` | Blocked + signed out with info banner | `(tabs)/index` (Home tab) |
| `office_staff` | `/dashboard` | `(tabs)/index` (Home tab) |
| `operator` | `/dashboard` | `(tabs)/index` (Home tab) |

**`bookkeeper` role note**: The impl plan §6 references "bookkeeper → `/reports`" but `PilotRole` in `packages/ui/src/auth/types.ts` has no `bookkeeper` type. The arch doc §4.3 lists `accountant` as a role. The frontend code was implemented with `office_staff` and `operator` — no `accountant` or `bookkeeper`. **Resolution**: use the code's `PilotRole` as authoritative. If `accountant` is added as a distinct role in a future backend batch, a frontend type addition + redirect mapping update will be needed. For FE-B2, `office_staff` routes to `/dashboard`.

### G.6 — Logout flow UX: silent redirect or confirmation screen

**Decision**: Silent redirect to `/login` + 6-second `severity="info"` `<NotificationBanner>` on the login page reading "You've been signed out."

**How it works**: `signOut()` sets `?signedOut=true` query param when navigating to `/login`. The `LoginPage` reads this param on mount and enqueues the info banner if present.

**Reasoning**: No confirmation screen — logout is intentional. A "you've been signed out" full page serves no UX purpose. The banner on the login page acknowledges the action without adding friction. This pattern is used by Notion, Linear, GitHub, and other SaaS products.

**TanStack Query cache clear**: `queryClient.clear()` is called in the `signOut` handler before redirecting. This ensures no stale tenant data is visible to the next user who logs in on the same browser.

### G.7 — Dev vs production auth toggle: mock login form design

**Decision**: When `NEXT_PUBLIC_USE_MOCK_AUTH=true` (web) or `EXPO_PUBLIC_USE_MOCK_AUTH=true` (mobile), the login form renders a **role-selector dropdown** replacing the password field.

**Mock form elements:**
- Email input (pre-filled with `mockuser@pilot-dev.example.com`, editable)
- Role `<Select>` dropdown: `owner`, `tech`, `office_staff`, `operator`
- "Sign in as [selected role]" button
- No password field in mock mode
- Visible dev indicator: yellow badge "DEV MODE — Mock Auth Active" below the Pilot logo

**Rationale for dropdown vs. env var only**: the `NEXT_PUBLIC_MOCK_USER_ROLE` env var sets the default, but during development Tom needs to quickly test different role perspectives (e.g., switch from owner to tech to test the "blocked on web" flow) without restarting the dev server. The dropdown enables this in-browser without any env var change.

The dropdown's default value reads from `NEXT_PUBLIC_MOCK_USER_ROLE` on load, then updates `AuthProvider`'s mock user role when changed (by triggering a re-render with the new role via a local state in `providers.tsx` that re-passes `mockUser` to `<AuthProvider>`).

---

## H. External Dependency Status

| Dependency | Status | Mock Strategy | Blocks |
|:-----------|:-------|:--------------|:-------|
| **AWS Cognito user pool** (production) | ⚠️ Not provisioned | `MockAuthProvider` + `NEXT_PUBLIC_USE_MOCK_AUTH=true` / `EXPO_PUBLIC_USE_MOCK_AUTH=true` (FE-B0) | FE-B2 production login; all authenticated surfaces in production |
| **AWS Amplify CLI config** | ⚠️ Not configured | Mock mode bypasses Amplify entirely — no `Amplify.configure()` call needed in mock mode | FE-B2 production auth scaffolding |
| **`aws-amplify` v6 package** | ✅ Installed (`aws-amplify` in `packages/shared-api/src/client.ts` dynamic import) | Already wired in FE-B0 | Nothing — lazy-imported |
| **Cognito JWT custom claims** (`custom:role`, `custom:tenant_id`) | ⚠️ Requires Cognito user pool + Post-Signup Lambda (§4.4) | Mock user has role baked into `PilotUser` object; no JWT parsing needed | Production role-based redirect |
| **`GET /api/v1/auth/me` FastAPI endpoint** | ⚠️ Not yet built (BE-B14 soft gate) | MSW handler at `apps/web/src/mocks/handlers/auth.ts` + mobile equivalent | Post-login profile hydration in production |
| **MFA enrollment** (users with MFA enrolled in Cognito) | ⚠️ No users enrolled in dev Cognito (pool not provisioned) | `<MfaChallengeStep>` can be tested by mocking `signIn` to return an MFA `nextStep` in MSW or test stubs | MFA challenge flow can be unit/integration tested without real Cognito |

**Tom's required actions before production delivery:**
1. Provision AWS Cognito user pool with configuration from `mvp-arch.md` §4.1
2. Configure Amplify CLI and add `amplifyconfiguration.json` to `apps/web/` and `apps/mobile/`
3. Implement Post-Signup Lambda (creates `user` + `tenant` records in PostgreSQL; BE-B14 scope)
4. Deploy `GET /api/v1/auth/me` endpoint (BE-B14 scope)
5. Configure Cognito custom attributes `custom:role` and `custom:tenant_id` on the user pool

---

## I. Test Plan

### I.1 Unit Tests

**Target: 30+ tests** (cumulative target after FE-B2: 267+)

| File | Tests | Coverage |
|:-----|:------|:---------|
| `apps/web/src/features/login/components/LoginForm.test.tsx` | 8 | Email validation (empty, invalid format, valid); password validation (empty, too-short, valid); form submits with correct args; loading state activates on submit; error banner enqueued on `signIn` rejection; mock mode renders role dropdown not password input; mock mode submits with selected role |
| `apps/web/src/features/login/components/MfaChallengeStep.test.tsx` | 6 | Renders correct copy for TOTP vs SMS vs EMAIL_OTP; code input accepts 6 digits; submit calls `onConfirm`; error message shows on rejection; cancel calls `onCancel`; "use recovery code" expands free-text input |
| `apps/web/src/features/login/hooks/useLoginFlow.test.ts` | 6 | `step` transitions to `mfa-challenge` when `signIn` returns MFA nextStep; `step` stays `credentials` on error; `onSuccess` fires with correct role after `DONE`; `submitMfaCode` calls `confirmMfaChallenge`; `cancelMfa` resets to `credentials` step; loading flag set during async calls |
| `apps/web/src/hooks/usePostLoginRedirect.test.ts` | 4 | `owner` → `/dashboard`; `tech` → `/login` + banner enqueued; `office_staff` → `/dashboard`; `operator` → `/dashboard` |
| `apps/web/src/hooks/useSessionExpiry.test.ts` | 3 | Subscribes to `auth:session-expired` on mount; unsubscribes on unmount; dispatching event enqueues critical banner + calls `signOut` |
| `apps/web/src/features/login/components/PasswordResetFlow.test.tsx` | 5 | Step 1: email submitted calls `resetPassword`; transitions to step 2; step 2: calls `confirmResetPassword` with email + code + password; password mismatch validation error; transitions to step 3 on success; "Resend code" re-calls step 1 without resetting step 2 inputs |
| `packages/ui/src/auth/AuthProvider.test.tsx` (extend existing) | 3 | `signIn` returns `{ nextStep: { signInStep: 'DONE' } }` on success; `signIn` returns MFA nextStep shape when Amplify returns challenge; `confirmMfaChallenge` calls `confirmSignIn` in production mode |
| `apps/mobile/src/features/login/components/LoginForm.test.tsx` | 5 | Full-page loading overlay shown on submit; haptic feedback on error; `returnKeyType` props set correctly; mock mode renders role picker; `accessibilityLabel` on all inputs |

### I.2 Integration Tests

**Target: 8+ tests** (cumulative target after FE-B2: 273+)

Subfolder: `apps/web/__tests__/batch_fe_b2/` and `apps/mobile/__tests__/batch_fe_b2/`

| File | Flow | Coverage |
|:-----|:-----|:---------|
| `apps/web/__tests__/batch_fe_b2/login-web.integration.test.tsx` | Web login full flow | (1) Happy path: fill form → submit → MSW returns session → redirect to `/dashboard`; (2) Wrong password: MSW returns 400 → error banner; (3) Network error: MSW offline → error banner; (4) MFA challenge flow: `signIn` returns TOTP challenge → `<MfaChallengeStep>` renders → code submitted → `DONE` → redirect |
| `apps/web/__tests__/batch_fe_b2/login-rbac.integration.test.tsx` | Role-based redirect | (1) `owner` → `/dashboard`; (2) `tech` → blocked + info banner; (3) `office_staff` → `/dashboard` |
| `apps/web/__tests__/batch_fe_b2/password-reset.integration.test.tsx` | Password reset web flow | Full 3-step flow against MSW; resend code; password validation errors |
| `apps/web/__tests__/batch_fe_b2/session-expiry.integration.test.tsx` | Session expiry + logout | (1) `auth:session-expired` event → critical banner renders → "Sign in" CTA → redirect to `/login`; (2) Logout → TanStack cache cleared → redirect to `/login?signedOut=true` → "Signed out" banner on login page |
| `apps/mobile/__tests__/batch_fe_b2/login-mobile.integration.test.tsx` | Mobile login full flow | Happy path; error; MFA challenge |
| `apps/mobile/__tests__/batch_fe_b2/mobile-routing.integration.test.tsx` | Mobile auth routing | Unauthenticated user redirected to `(auth)/login`; authenticated user lands on `(tabs)/index` |

### I.3 E2E Tests

**Target: 2+** (cumulative target after FE-B2: 27+)

| File | Platform | Flow |
|:-----|:---------|:-----|
| `apps/web/e2e/batch_fe_b2/login-logout.e2e.spec.ts` | Web (Playwright) | Full login/logout cycle against dev Cognito (or `MockAuthProvider` if Cognito not provisioned); verify `/dashboard` route reached; verify TanStack cache cleared on logout; verify `/login?signedOut=true` banner appears |
| `apps/mobile/e2e/batch_fe_b2/login-mobile.e2e.test.ts` | Mobile (Maestro) | Login via MockAuthProvider → land on Home tab → Owner tab hidden for `tech` role; login as `owner` → Owner tab visible |

### I.4 Accessibility Audit Checkpoints

Per §5 Phase 2 Step 8, run `@axe-core/react` against all new surfaces. Zero violations required.

| Surface | Specific checks |
|:--------|:---------------|
| Web login page | `<form>` has `aria-label`; inputs have associated `<label>` elements; error messages are `role="alert"`; submit button has descriptive accessible name |
| Web password reset page | Step indicator (1/2) uses `aria-current="step"`; password inputs have `aria-describedby` linking to requirements |
| Mobile login screen | All inputs have `accessibilityLabel`; all buttons have `accessibilityLabel`; `testID` on all interactive elements |
| Session-expired banner | `NotificationBanner` already sets `role="alert"` (FE-B1 spec); verify it fires for session expiry |

---

## Design Doc Completion Checklist

- [x] All 7 key design decisions from the prompt resolved (§G)
- [x] No unresolved interaction or visual ambiguity in any surface
- [x] All component file paths follow `pilot-react-engineer-methods.md` §1 conventions
- [x] All import paths reference real module paths confirmed by codebase reads
- [x] No component listed as "new" pre-exists in codebase (confirmed by grep)
- [x] All shared module interfaces from FE-B0 and FE-B1 consumed via correct import paths
- [x] New shared module modifications documented in §F with backward-compatible contract
- [x] `packages/ui/src/index.ts` additions identified (none new — FE-B2 modifies but does not add new shared library entries)
- [x] External dependency status documented with Tom's required actions
- [x] Test plan meets minimums: 30+ unit, 8+ integration, 2+ e2e
- [x] Routes confirmed against FE-B0 routing skeleton; no naming conflicts

---

*This design doc is the authoritative Phase 1 output for FE-B2. The React Engineer begins Phase 2 (implementation) from this document. Any deviations from this spec discovered during implementation must be documented in the FE-B2 Implementation Detail Record in `pilot-app-mvp-frontend-impl-plan.md` §7.*
