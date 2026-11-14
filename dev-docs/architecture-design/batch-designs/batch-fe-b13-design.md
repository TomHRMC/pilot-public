# FE-B13 Batch Design — Onboarding & Push Permissions (Pass 4 Tier 3 #10 + #11)

**Status**: Ready for Implementation
**Date**: 2026-05-26
**Author**: Pilot Architect
**Prerequisite Batches**: FE-B0 through FE-B12 complete
**Backend Gate**: BE-B14 (A73–A78: tenant signup, legal acceptance, subscription tier infrastructure, Stripe integration, onboarding checklist, mobile push permission)
**Gates Downstream**: FE-B14 (`StripePaymentForm` subscription mode established here; FE-B14 consumes in one-time-payment mode)
**Test Subfolder**: `apps/{web,mobile}/__tests__/batch_fe_b13/`

---

## Prerequisite Reads Completed

| Source | Key facts extracted |
|:---|:---|
| `frontend-pass-4-tier-3-flow-10-11-onboarding-and-push-permission-spec.md` | 5-step wizard (account → legal → phone → plan → ready/pay); 8-item post-wizard checklist (3 auto-complete from wizard steps 1/2/4); trial-as-tier framing (no special mode branching); push permission pre-explainer before OS prompt; mobile setup phase for first-login techs; trial expiration read-only + paywall; resumable wizard state via backend A77 |
| `pilot-app-mvp-frontend-impl-plan.md §6 FE-B13` | 10-item execution order; test targets (70+ unit, 18+ integration, 4+ E2E); key patterns: Stripe wrapper shared across batches; state machine drives wizard navigation; trial-as-tier framing throughout |
| `mvp-arch.md §16.8 Optimistic UI` | Optimistic update pattern used for checklist item completion: item appears complete immediately; pending badge until server confirms; failed completion rolls back with retry affordance |
| `mvp-arch.md §20 Subscription Tier + Stripe` | Stripe Subscriptions for recurring (subscription mode); Stripe Payment Intents for one-time (FE-B14); same account; webhook handler at `POST /api/v1/webhooks/stripe`; trial tier `is_trial=true`, `monthly_price_cents=0`; tier schema data-driven from DB |
| `pilot-react-engineer-methods.md §1 Project Structure` | `packages/ui/src/{category}/` for cross-platform shared; `apps/web/src/features/{surface}/` for web-only; `apps/mobile/features/{surface}/` for mobile-only; barrel export from `packages/ui/src/index.ts` |
| `packages/ui/src/tier-picker-card/TierPickerCard.tsx` | FE-B1 skeleton: `TierName = "trial" \| "starter" \| "growth" \| "pro"`; `TierPickerCardProps`: `tierName, displayName, monthlyPriceCents, annualPriceCents?, features[], isFeatured?, isSelected?, onSelect(tierName), ctaLabel?, testID?, className?`; `isFeatured` renders "Recommended" badge; `isSelected` renders `border-brand-600` + checkmark |
| `packages/ui/src/tier-picker-card/types.ts` | `TierFeature: {label, included, callout?}`; `TierName` is string union — needs extending for `professional` and `enterprise` tiers from DB |
| `packages/ui/src/mfa-enrollment-wizard/` | FE-B12 fleshed: `MFAEnrollmentWizardPropsExtended` adds `forceFlow?, showRecoveryCodes?, onRecoveryCodesAcknowledged?, enrolledMethods?`; `wizardMode` is surfaced via `forceFlow` boolean; FE-B13 embeds with `forceFlow={true}` for tenants requiring MFA at signup |
| `backend/api/routes/signup.py` | `POST /api/v1/signup` (public, no JWT) → `{tenant_id, signup_state, owner_email}`; `PUT /api/v1/signup/{id}/step{2-5}` (JWT required); `GET /api/v1/signup/{id}/state` → `{tenant_id, signup_state, collected_data}`; `POST /api/v1/signup/{id}/legal/accept`; `GET /api/v1/signup/{id}/legal/required`; states: `step1_account → step2_legal → step3_phone → step4_tier → step5_confirm → complete` |
| `backend/api/routes/subscription_tiers.py` | `GET /api/v1/subscription-tiers` → `{tiers: SubscriptionTierResponse[]}`; shape: `{tier_id, tier_name, display_label, monthly_price_cents, is_trial, trial_duration_days?, max_users, max_sms_segments_per_month?, display_order, is_active}` |
| `backend/api/routes/onboarding_checklist.py` | `GET /api/v1/tenants/{id}/onboarding/checklist` → `OnboardingChecklistResponse` with 8 boolean fields + timestamps; `PUT .../skip/{item}` (items: `quickbooks`, `calendar`, `team`); `PUT .../hidden` with `{hidden: bool}`; `PUT .../dismissed` for permanent dismiss |
| `backend/api/routes/mobile_push_permission.py` | `PUT/GET /api/v1/users/me/devices/{device_id}/push-permission`; `permission_state` ∈ `{not_asked, granted, denied_by_user_choice, denied_by_os, revoked_in_settings}`; response includes `banner_should_appear: bool` (computed from 7-day reappearance logic) |
| `apps/web/src/app/(authed)/` | Confirmed: all existing routes are inside `(authed)` group with JWT guard. Signup wizard is pre-auth → must live at `apps/web/src/app/signup/` (outside `(authed)`) |
| `apps/web/src/app/login/` | Login and `password-reset/` are already outside `(authed)`. Signup sits adjacent at same level |

---

## Resolved Design Decisions

### Decision 1 — Signup Wizard Route Structure and State Machine Integration

**Decision**: The 5-step signup wizard lives entirely outside `(authed)` at `apps/web/src/app/signup/`. File paths per step:

```
apps/web/src/app/
├── signup/
│   ├── layout.tsx              # Wizard shell: logo, step progress bar, no nav
│   ├── page.tsx                # Redirects → /signup/account (step 1 entry)
│   ├── account/
│   │   └── page.tsx            # Step 1: Account creation (public, no JWT)
│   ├── legal/
│   │   └── page.tsx            # Step 2: Legal acceptance (JWT from Cognito signup)
│   ├── phone/
│   │   └── page.tsx            # Step 3: Phone verification (optional)
│   ├── plan/
│   │   └── page.tsx            # Step 4: Tier selection
│   └── ready/
│       ├── page.tsx            # Step 5a: Trial confirmation (trial path)
│       └── pay/
│           └── page.tsx        # Step 5b: Stripe payment (paid path)
```

**Resumability**: On mount, every step page runs `GET /api/v1/signup/{tenant_id}/state`. `tenant_id` is stored in `sessionStorage` after step 1 completes. If the fetched `signup_state` maps to a later step than the current URL, the wizard redirects forward. If the state maps to an earlier step, the wizard redirects backward. This guarantees cross-device and refresh-safe resumption.

**Step-to-state mapping**:
| URL | Requires `signup_state` ≥ | Redirects to if behind |
|:---|:---|:---|
| `/signup/account` | (none — step 1 entry) | — |
| `/signup/legal` | `step1_account` | `/signup/account` |
| `/signup/phone` | `step2_legal` | `/signup/legal` |
| `/signup/plan` | `step3_phone` | `/signup/phone` |
| `/signup/ready` | `step4_tier` where `is_trial=true` selected | `/signup/plan` |
| `/signup/ready/pay` | `step4_tier` where paid tier selected | `/signup/plan` |

**Post-wizard redirect**: Step 5 "Get started →" button (`/signup/ready`) → `router.replace('/dashboard')`. The `(authed)` layout detects `signup_state === 'complete'` and renders the post-wizard checklist widget on the dashboard.

**Forward navigation guard**: "Continue" button submits the current step to `PUT /api/v1/signup/{id}/step{N}`. Only on server success (200) does the router navigate to the next step. Client-side validation gates submission before the network call; server-side validation is the final authority.

**Resume welcome banner**: If a user returns to `/signup/legal` (or later) with pre-filled state, the wizard header renders "Welcome back, {name}. Let's pick up where you left off." keyed on `collected_data.owner_first_name` from the state response.

**Rationale**: Dynamic `[step]` routing was evaluated and rejected — each step has genuinely different layout requirements (step 1 is largest; step 5 paid path has Stripe Elements). Flat per-step directories are explicit and easier to unit test in isolation. The `sessionStorage`-based `tenant_id` cache is cleared on successful wizard completion.

---

### Decision 2 — `StripePaymentForm` Shared Component API (LOCKED FOR FE-B14)

**Decision**: `StripePaymentForm` lives at `packages/ui/src/stripe-payment/StripePaymentForm.tsx`. It **owns** the `Elements` provider internally — consumers pass `stripePublishableKey` rather than wrapping with `<Elements>` externally. This keeps consumption ergonomic and prevents Elements nesting errors.

**Mode differentiation via `mode` prop**:

```typescript
type StripePaymentMode = 'subscription' | 'one-time';
```

- `subscription`: renders `PaymentElement` for card/bank setup. On submit, calls `stripe.confirmSetup()` or `stripe.confirmPayment()` against the `clientSecret` prop. Backend creates the Stripe Subscription; Pilot does not handle subscription lifecycle in the component.
- `one-time`: renders `PaymentElement` with amount display. On submit, calls `stripe.confirmPayment()`. FE-B14 passes `paymentAmount` and `invoiceToken` for one-time invoice payment.

**Stripe Elements surface**: Both modes use the unified `PaymentElement` (not the legacy `CardElement`). This handles card, Apple Pay, Google Pay, and local payment methods in a single surface with built-in PCI compliance. Billing address is collected via `AddressElement` composed below `PaymentElement`.

**Provider placement**: `StripePaymentForm` calls `loadStripe(stripePublishableKey)` internally and wraps its own render with `<Elements stripe={stripePromise} options={elementsOptions}>`. The `stripePublishableKey` must be passed on every render but `loadStripe()` is memoized by the Stripe.js SDK.

**Error handling**: dual-surface:
1. `onError?: (error: StripePaymentError) => void` — callback for parent-level error handling (e.g., showing a toast outside the component)
2. Internal inline error rendering below the `PaymentElement` using `fault-600` tokens — always shows, regardless of `onError` presence

**Locked interface for FE-B13 (subscription mode)**:

```typescript
// packages/ui/src/stripe-payment/types.ts
export interface StripePaymentFormProps {
  /** Required: Stripe publishable key from env */
  stripePublishableKey: string;
  /** Required: clientSecret from backend (SetupIntent or PaymentIntent client secret) */
  clientSecret: string;
  /** Required: mode determines which Stripe flow is used */
  mode: StripePaymentMode;
  /** Amount in cents — required for 'one-time' mode; ignored for 'subscription' */
  paymentAmountCents?: number;
  /** Display label for the submit button */
  submitLabel?: string;
  /** Called on successful Stripe payment confirmation */
  onSuccess: (result: StripePaymentResult) => void;
  /** Called on Stripe error (card declined, insufficient funds, etc.) */
  onError?: (error: StripePaymentError) => void;
  /** Called when form is loading (Elements loading or submit in-flight) */
  onLoadingChange?: (isLoading: boolean) => void;
  /** Optional: disable the submit button externally */
  disabled?: boolean;
  testID?: string;
}

export interface StripePaymentResult {
  paymentMethodId?: string;
  paymentIntentId?: string;
}

export interface StripePaymentError {
  code: string;
  message: string;
  declineCode?: string;
}
```

**FE-B14 additive-only extension**: FE-B14 may add `invoiceToken?: string` and `allowAmountVariance?: boolean` as OPTIONAL props for one-time mode. It must NOT modify any props listed above.

**Rationale**: Internal Elements provider avoids consumer errors with nested providers. The `mode` prop is preferable to two separate components because both contexts share all Stripe lifecycle logic (loading, error, confirmation). Separating error callback from inline rendering handles both the modal-dismiss case (FE-B14) and the inline wizard case (FE-B13).

---

### Decision 3 — `TierPickerCard` Fleshing from FE-B1 Skeleton

**Decision**: The FE-B1 skeleton is **fully backward-compatible**. FE-B13 adds optional props for trial-specific display and extends the `TierName` union.

**`TierName` extension** (FE-B1 had `"trial" | "starter" | "growth" | "pro"`; DB seed data uses `"professional"` and `"enterprise"`):
```typescript
// Extended in FE-B13 — additive, backward-compatible
export type TierName =
  | "trial"
  | "starter"
  | "professional"
  | "enterprise"
  | "growth"    // kept for FE-B1 backward compatibility
  | "pro"       // kept for FE-B1 backward compatibility
  | (string & {}); // open extension for future DB-driven tiers
```

**New optional props (additive)**:
```typescript
interface TierPickerCardPropsExtended extends TierPickerCardProps {
  /** When true, renders "FREE for N days" instead of "$0" price display */
  isTrialTier?: boolean;
  /** Trial duration in days — shown as "FREE for {N} days" when isTrialTier=true */
  trialDurationDays?: number;
  /** User count limit — rendered as "Up to N users" in features list if provided */
  maxUsers?: number;
  /** When true and card is selected: show "(current)" label instead of CTA button */
  isCurrentTier?: boolean;
  /** "Recommended" badge label override — defaults to "Recommended" when isFeatured=true */
  recommendedBadgeLabel?: string;
}
```

**Data flow**: `GET /api/v1/subscription-tiers` → `SubscriptionTierResponse[]` → map to `TierPickerCardProps` in the wizard. The tier recommended for the user's business size is determined client-side:
- Solo / Small (1–5 users from step 1 `business_size`) → recommend `starter`
- Medium (6–15) → recommend `professional`
- Large (16+) → recommend `enterprise`
The recommended card gets `isFeatured={true}`.

**Trial card display**: When `isTrialTier={true}` and `trialDurationDays={N}`, the price section renders "FREE" with a subtitle "for {N} days" instead of the formatted cents price.

**Paid tier selection → Stripe form appearance**: When a paid tier is selected in step 4, the Stripe payment form appears **inline below the tier cards** on the same page (not a separate sub-step). This is controlled by a local `selectedTierRequiresPayment` state derived from `selectedTierId !== trialTierId`. No navigation occurs; the form slides in below the grid. "Continue" advances to step 5 (confirmation) only after successful Stripe payment method capture.

**Trial selected → step 5 direct**: When trial is selected (default), "Continue" on step 4 calls `PUT /api/v1/signup/{id}/step5` with `{confirmed: true}`, which completes the wizard. Navigation goes to `/signup/ready`.

**Conversion flow reuse**: The same `TierPickerCard` grid is used in the trial-to-paid paywall (Decision 7). The `isCurrentTier={true}` prop marks the current tier without a CTA.

**Rationale**: Inline Stripe form below tier cards avoids a separate navigation step for paid users, keeping the page count at 5 steps. The `isTrialTier` prop cleanly handles the free-tier display without branching the price formatter.

---

### Decision 4 — Post-Wizard Setup Checklist Architecture

**Decision**: The checklist is **server-driven**. `GET /api/v1/tenants/{tenant_id}/onboarding/checklist` is the single source of truth. The `OnboardingChecklistResponse` boolean fields (`account_created`, `legal_accepted`, `tier_selected`, `first_customer_added`, `catalog_setup`, `quickbooks_connected`, `calendar_connected`, `team_invited`) plus skip/hidden/dismissed flags are authoritative; the UI renders directly from this shape.

**TanStack Query strategy**:
- `queryKey: ['onboarding-checklist', tenantId]`
- `staleTime: 30_000` (30 seconds)
- `refetchOnWindowFocus: true` — catches completions from other browser tabs
- Manual invalidation via `queryClient.invalidateQueries(['onboarding-checklist', tenantId])` on:
  - Successful customer add
  - Successful catalog item add
  - Successful QB OAuth completion
  - Successful calendar OAuth completion
  - Successful team invite send

**Checklist item completion via optimistic UI (§16.8)**: When a user completes an item through the checklist's action button (e.g., "Add now" → customer create flow), the optimistic update marks the item done immediately. If the underlying action fails, the item reverts to pending with an inline error. This matches the §16.8 pattern already established in FE-B7 via `useOptimisticMutation`.

**Skip behavior**: Skippable items (`quickbooks`, `calendar`, `team`) have a "Skip" link. On click: optimistic update to skipped state → `PUT .../skip/{item}`. If fails: revert. Skipped items show strikethrough + "(skipped)" + "Undo" link (which calls the same endpoint with a toggle — backend `skip_item` service handles re-enable).

**Hide/dismiss behavior**:
- "Hide" → `PUT .../hidden` with `{hidden: true}` → checklist collapses to compact pill "Setup checklist (N of 8 done) · [Show]"
- "Don't show again" → `PUT .../dismissed` → permanent dismiss; widget disappears and does not return
- Both hidden and dismissed states persist across sessions via the backend response fields

**Widget disappearance**: When `checklist_dismissed_permanently === true` OR all 8 items are `true` (complete or skipped-as-complete), the checklist widget unmounts from the dashboard grid entirely.

**Rationale**: Server-driven checklist prevents drift between auto-completion events (triggered by domain services in other routes) and what the UI displays. The 30s stale time plus `refetchOnWindowFocus` provides near-real-time accuracy without polling overhead.

---

### Decision 5 — Mobile Tech Onboarding Flow

**Decision**: The mobile onboarding flow lives in a dedicated Expo Router route group: `apps/mobile/app/(onboarding)/`. This group appears for first-time users before they reach the main `(tabs)` shell.

**Route structure**:
```
apps/mobile/app/
├── (onboarding)/
│   ├── _layout.tsx             # Full-screen, no tab bar, no back nav
│   ├── welcome.tsx             # "Welcome to Pilot mobile, {name}!" + "Tap to continue"
│   ├── push-permission.tsx     # Push pre-explainer + OS prompt trigger
│   ├── tour-today.tsx          # Tutorial card: The Today tab
│   ├── tour-voice.tsx          # Tutorial card: Voice mic
│   └── tour-done.tsx           # "You're all set!" → transition to (tabs)
└── (tabs)/
    └── ...                     # Main app shell
```

**First-time detection**: On mobile app launch after login, the app calls `GET /api/v1/users/me/devices/{device_id}/push-permission`. If `permission_state === 'not_asked'`, the user is routed to `/(onboarding)/welcome`. If `permission_state !== 'not_asked'`, they go directly to `/(tabs)/today`.

The `device_id` is a UUID generated on first app launch and stored in `expo-secure-store`. It is stable across app restarts.

**Onboarding completion**: After `tour-done.tsx`, the app calls `PUT /api/v1/users/me/devices/{device_id}/push-permission` with the resulting state (`granted`, `denied_by_user_choice`, or `denied_by_os`). Then `router.replace('/(tabs)/today')`.

**"Skip tutorial" affordance**: A small "Skip" link in the top-right of each tutorial card. Tapping skip navigates directly to `/(tabs)/today` without calling any additional endpoints (push permission state was already set on the push-permission screen).

**Rationale**: A separate `(onboarding)` route group is the idiomatic Expo Router approach — it prevents back-navigation into onboarding from the main shell, and the group layout can suppress the tab bar cleanly.

---

### Decision 6 — Push Permission Pre-Explainer Placement and Fallback

**Decision**: Push permission request fires on `(onboarding)/push-permission.tsx` — the second screen of the mobile onboarding flow, after the welcome intro screen. This is the "first meaningful moment" per spec Decision 12.

**"Allow notifications" path**:
1. User taps "Allow notifications"
2. Call `expo-notifications` `requestPermissionsAsync()` → OS permission dialog fires
3. **If granted**: call `expo-notifications` `getExpoPushTokenAsync()` to register the push token; call `PUT /api/v1/users/me/devices/{device_id}/push-permission` with `{permission_state: 'granted'}`; show brief "Push notifications enabled ✓" confirmation (1.5s); auto-advance to `tour-today`
4. **If denied at OS level**: call `PUT ...` with `{permission_state: 'denied_by_os'}`; show fallback screen: "No worries — you'll get email and in-app alerts. You can change this anytime in Settings."; show "Open Settings" button; advance button also available

**"Maybe later" path**:
1. User taps "Maybe later"
2. No OS prompt fires
3. Call `PUT ...` with `{permission_state: 'denied_by_user_choice'}`
4. Screen advances to `tour-today` without any confirmation screen

**OS Settings deep-link mechanism**:
```typescript
// Platform-specific settings deep-link
import * as Linking from 'expo-linking';

const openNotificationSettings = () => {
  if (Platform.OS === 'ios') {
    Linking.openURL('app-settings:'); // Opens iOS Settings for this app
  } else {
    Linking.openURL(`package:${Application.applicationId}`); // Opens Android App Info
  }
};
```

**"Push is off" dismissable banner (Today tab)**: After onboarding, if `banner_should_appear === true` from the push-permission GET endpoint, a dismissable banner renders at the top of the Today tab: "📱 Push is off. [Turn on for instant alerts]". Tapping it calls `openNotificationSettings()`. Dismiss calls `PUT ...push-permission` with an updated `dismissable_banner_dismissed_at` timestamp (handled server-side via the existing endpoint).

**Rationale**: The pre-explainer screen is critical for iOS where the OS prompt is one-shot. Explaining value before the OS dialog maximizes grant rate. The platform-specific deep-link mechanism is the standard expo approach — `app-settings:` on iOS opens app-specific notification settings directly.

---

### Decision 7 — Trial-to-Paid Conversion UI: Paywall Triggering

**Decision**: Two distinct paywall surfaces based on urgency:

**Soft gate (7d/3d/1d remaining)**: A dismissable banner in the app shell header (`apps/web/src/app/(authed)/layout.tsx`): "Your trial ends in {N} days. [Upgrade now]". Tapping "Upgrade now" opens a `<dialog>` modal overlay on the current page. The modal embeds the `TierPickerCard` grid (same grid as step 4, minus the trial card) + inline `StripePaymentForm` (subscription mode). The soft-gate banner re-appears on the next session if dismissed, up to trial expiry.

**Hard gate (0d — trial expired)**: A dedicated full-page route at `apps/web/src/app/(authed)/trial-expired/page.tsx`. The `(authed)` layout checks `tenant.trial_expired` (returned on the `GET /api/v1/auth/me` response — backend returns `402` on write operations but the layout reads tenant status proactively). If `trial_expired === true`, the layout renders the trial-expired page instead of the normal content. **No existing UI is reachable** — hard gate.

The trial-expired page text: "Your trial has ended. Pick a plan to keep using Pilot. Your data is preserved — pick up right where you left off." + `TierPickerCard` grid + `StripePaymentForm`.

**402 handling on write operations**: A TanStack Query `onError` global handler in `apps/web/src/app/providers.tsx` intercepts `HTTP 402` responses with `{paywall: true}` payload and triggers the hard gate redirect to `/trial-expired`. This ensures any blocked write surfaces the paywall regardless of which page the user is on.

**`TierPickerCard` reuse in both contexts**: The same component handles wizard, soft-gate modal, and hard-gate page. No new mode prop is needed — the parent container determines context. In conversion context, `isCurrentTier={true}` marks the trial card (so it's visible as "your current plan — expired" but not selectable), and the paid cards are selectable.

**Rationale**: Modal overlay for soft gate is less disruptive — user can dismiss and still access the app. Full-page hard gate at 0d enforces the data-preservation-without-write-access model while keeping data visible. Detecting via `(authed)` layout rather than per-page guards ensures the hard gate fires everywhere consistently.

---

## Section A — Component Implementation Plan

### A.1 New Shared Components (`packages/ui/src/`)

| Component | Path | Exports | Notes |
|:---|:---|:---|:---|
| `StripePaymentForm` | `stripe-payment/StripePaymentForm.tsx` | `StripePaymentForm` | Subscription + one-time mode; owns `Elements` provider; LOCKED for FE-B14 |
| `StripePaymentFormProps` / `StripePaymentResult` / `StripePaymentError` / `StripePaymentMode` | `stripe-payment/types.ts` | All four types | LOCKED interface |
| `TierPickerCardPropsExtended` | `tier-picker-card/types.ts` | Extends `TierPickerCardProps` | Additive-only; backward-compatible with FE-B1 skeleton |

**`TierPickerCard` (`tier-picker-card/TierPickerCard.tsx`)** — existing FE-B1 file receives additive changes:
- `TierName` union extended to include `"professional"` and `"enterprise"` (plus open extension)
- New optional props: `isTrialTier?`, `trialDurationDays?`, `maxUsers?`, `isCurrentTier?`, `recommendedBadgeLabel?`
- Price display branch: when `isTrialTier && trialDurationDays` → renders "FREE / for {N} days" instead of formatted cents
- `isCurrentTier` renders "(current)" label in place of CTA button

### A.2 New Web Components (`apps/web/src/`)

**Signup Wizard (pre-auth routes)**

| Component | Path | Notes |
|:---|:---|:---|
| `SignupLayout` | `app/signup/layout.tsx` | Wizard shell: Pilot logo, 5-step progress indicator, no nav sidebar |
| `SignupAccountPage` | `app/signup/account/page.tsx` | Step 1: 7 fields, public POST to create tenant + Cognito user |
| `SignupLegalPage` | `app/signup/legal/page.tsx` | Step 2: 3 required checkboxes + optional marketing email; inline legal doc modal |
| `SignupPhonePage` | `app/signup/phone/page.tsx` | Step 3: phone input + OTP verify sub-screen; skip affordance |
| `SignupPlanPage` | `app/signup/plan/page.tsx` | Step 4: `TierPickerCard` grid + inline `StripePaymentForm` (when paid selected) |
| `SignupReadyPage` | `app/signup/ready/page.tsx` | Step 5 trial path: confirmation summary + "Get started →" |
| `SignupReadyPayPage` | `app/signup/ready/pay/page.tsx` | Step 5 paid path: payment confirmation + receipt summary |
| `LegalDocModal` | `features/signup/components/LegalDocModal.tsx` | Inline modal for "Read full →" ToS/Privacy/EULA links |
| `PhoneOtpSubscreen` | `features/signup/components/PhoneOtpSubscreen.tsx` | 6-digit OTP input + resend + "Use different number" |
| `WizardProgressBar` | `features/signup/components/WizardProgressBar.tsx` | 5-step visual progress indicator in wizard layout |
| `useSignupWizard` | `features/signup/hooks/useSignupWizard.ts` | State machine hook: reads/writes signup state; manages step navigation |
| `useSubscriptionTiers` | `features/signup/hooks/useSubscriptionTiers.ts` | TanStack Query hook for `GET /api/v1/subscription-tiers` |
| `useSignupLegalAccept` | `features/signup/hooks/useSignupLegalAccept.ts` | Mutation hook for `POST /api/v1/signup/{id}/legal/accept` |

**Post-Wizard Dashboard Checklist**

| Component | Path | Notes |
|:---|:---|:---|
| `OnboardingChecklistWidget` | `features/onboarding/components/OnboardingChecklistWidget.tsx` | Pinned dashboard widget; server-driven; 8 items; hide/dismiss affordances |
| `ChecklistItem` | `features/onboarding/components/ChecklistItem.tsx` | Single row: icon + label + action button + optional skip link |
| `useOnboardingChecklist` | `features/onboarding/hooks/useOnboardingChecklist.ts` | TanStack Query: `queryKey: ['onboarding-checklist', tenantId]`; `staleTime: 30_000`; optimistic skip |
| `useChecklistMutations` | `features/onboarding/hooks/useChecklistMutations.ts` | Skip / hide / dismiss mutations with optimistic updates |

**Trial-to-Paid Conversion**

| Component | Path | Notes |
|:---|:---|:---|
| `TrialExpiryBanner` | `features/onboarding/components/TrialExpiryBanner.tsx` | Soft-gate banner in `(authed)/layout.tsx`; dismissable; N-day countdown |
| `TrialUpgradeModal` | `features/onboarding/components/TrialUpgradeModal.tsx` | `<dialog>` modal: `TierPickerCard` grid + `StripePaymentForm` subscription mode |
| `TrialExpiredPage` | `app/(authed)/trial-expired/page.tsx` | Hard-gate full page; same tier picker UI; blocks all other routes |
| `useTrialStatus` | `features/onboarding/hooks/useTrialStatus.ts` | Reads `tenant.trial_*` from auth context; computes days-remaining; triggers gate |

**Legal Acceptance**

| Component | Path | Notes |
|:---|:---|:---|
| `LegalCheckboxGroup` | `features/signup/components/LegalCheckboxGroup.tsx` | 3 required + 1 optional checkbox; "Continue" disabled until all 3 checked |

**Operator Placeholder**

| Component | Path | Notes |
|:---|:---|:---|
| `OperatorAdminPlaceholderPage` | `app/(authed)/_operator/page.tsx` | Hidden route (RBAC `operator` role only); placeholder "Operator admin — Phase 2" |

### A.3 New Mobile Components (`apps/mobile/`)

| Component | Path | Notes |
|:---|:---|:---|
| `OnboardingLayout` | `app/(onboarding)/_layout.tsx` | Full-screen, no tab bar; "Skip tutorial" link in top-right |
| `OnboardingWelcomeScreen` | `app/(onboarding)/welcome.tsx` | "Welcome to Pilot mobile, {name}!" + "Tap to continue" |
| `PushPermissionScreen` | `app/(onboarding)/push-permission.tsx` | Pre-explainer + "Allow" / "Maybe later"; OS prompt trigger |
| `TourTodayScreen` | `app/(onboarding)/tour-today.tsx` | Tutorial card 1: Today tab overview |
| `TourVoiceScreen` | `app/(onboarding)/tour-voice.tsx` | Tutorial card 2: Voice mic explanation |
| `TourDoneScreen` | `app/(onboarding)/tour-done.tsx` | "You're all set!" → transition to `(tabs)/today` |
| `PushDeniedFallback` | `features/onboarding/components/PushDeniedFallback.tsx` | "No worries" screen + "Open Settings" button |
| `PushBannerToday` | `features/onboarding/components/PushBannerToday.tsx` | Dismissable "Push is off" banner on Today tab |
| `usePushPermission` | `hooks/usePushPermission.ts` | Reads/writes `permission_state`; wraps `expo-notifications`; manages OS prompt timing |
| `useMobileOnboarding` | `hooks/useMobileOnboarding.ts` | Detects first-time user; coordinates route to `(onboarding)` vs `(tabs)` |
| `SetupBannerToday` | `features/onboarding/components/SetupBannerToday.tsx` | MVP mobile checklist: "Complete your setup on the web — {N} tasks remaining" |

### A.4 New Routes Summary

**Web routes (all new)**:

| Route | Auth required | Notes |
|:---|:---|:---|
| `/signup` | No | Redirects to `/signup/account` |
| `/signup/account` | No | Step 1 — public |
| `/signup/legal` | Cognito (just created) | Step 2 |
| `/signup/phone` | Cognito | Step 3 |
| `/signup/plan` | Cognito | Step 4 |
| `/signup/ready` | Cognito | Step 5 trial path |
| `/signup/ready/pay` | Cognito | Step 5 paid path |
| `/(authed)/trial-expired` | JWT | Hard-gate paywall |
| `/(authed)/_operator` | JWT + operator role | Placeholder admin |

**Mobile routes (all new)**:

| Route | Notes |
|:---|:---|
| `/(onboarding)/welcome` | First-time mobile landing |
| `/(onboarding)/push-permission` | Pre-explainer + OS prompt |
| `/(onboarding)/tour-today` | Tutorial card 1 |
| `/(onboarding)/tour-voice` | Tutorial card 2 |
| `/(onboarding)/tour-done` | Completion + transition |

---

## Section B — Execution Order

| # | Item | Rationale | Est. Days |
|:---|:---|:---|:---:|
| 1 | **`StripePaymentForm` shared component** (`packages/ui/src/stripe-payment/`) — both modes; owned Elements provider; locked interface | Establishes the Stripe integration boundary before any wizard that references it. FE-B14 depends on this interface being frozen. | 2 |
| 2 | **`TierPickerCard` fleshing** — extend `TierName` union; add optional trial/maxUsers/isCurrentTier props; trial price display branch; backward-compat verified | FE-B1 skeleton consumers are unaffected; step 4 wizard depends on fleshed card. | 1 |
| 3 | **Signup wizard web (steps 1–3)** — `account/`, `legal/`, `phone/` pages; `SignupLayout`; `useSignupWizard` state machine hook; `LegalDocModal`; `LegalCheckboxGroup`; `PhoneOtpSubscreen`; MSW handlers for signup API | Largest sub-flow; no Stripe dependency; establishes the wizard shell and state machine pattern. | 3 |
| 4 | **Signup wizard step 4 — tier selection + inline Stripe** — `SignupPlanPage`; `TierPickerCard` grid with recommended logic; inline `StripePaymentForm` when paid selected; `useSubscriptionTiers` hook | Consumes items 1 + 2; closes the paid-signup path. | 2 |
| 5 | **Signup wizard step 5 + onboarding state machine integration** — `SignupReadyPage`, `SignupReadyPayPage`; `useSignupWizard` resumability from `GET /signup/{id}/state`; cross-device resume; forward navigation guard | Completes the wizard. Onboarding state machine integration ensures all state transitions are server-confirmed before navigation. | 1.5 |
| 6 | **Post-wizard checklist (web)** — `OnboardingChecklistWidget`; `ChecklistItem`; `useOnboardingChecklist` + `useChecklistMutations`; optimistic skip; hide/dismiss; auto-completion invalidation wiring | Drives post-signup activation; depends on wizard completion routing. | 2 |
| 7 | **Trial-to-paid conversion UI** — `TrialExpiryBanner` in layout; `TrialUpgradeModal`; `TrialExpiredPage` hard gate; `useTrialStatus`; 402-interceptor in `providers.tsx`; `TierPickerCard` reuse in conversion context | Paywall closes the monetization loop; depends on `StripePaymentForm` (item 1) and `TierPickerCard` (item 2). | 2 |
| 8 | **Mobile onboarding flow** — `(onboarding)` route group; all 5 onboarding screens; `useMobileOnboarding` detection hook; `SetupBannerToday` web-redirect banner on Today tab | Mobile-only; depends on push permission item below for the push screen. | 2 |
| 9 | **Push permission pre-explainer (Tier 3 #11)** — `PushPermissionScreen`; `usePushPermission`; OS prompt via `expo-notifications`; `PushDeniedFallback`; `PushBannerToday`; `openNotificationSettings` deep-link | Tier 3 #11 deliverable. Composed into mobile onboarding (item 8). | 1.5 |
| 10 | **Operator override placeholder + MSW handler sweep** — `/(authed)/_operator` placeholder page; RBAC guard; complete MSW handler set for all new endpoints; MSW handlers for Stripe test mode | Low-scope MVP requirement; closes the batch. | 0.5 |

---

## Section C — API Contracts

### C.1 Signup Wizard (A73)

**`POST /api/v1/signup`** — Step 1, public (no JWT)
```typescript
// Request
interface SignupInitiateRequest {
  business_name: string;
  trade: string;              // 'electrical' | 'plumbing' | 'hvac' | 'other'
  business_size: string;      // 'solo' | 'small' | 'medium' | 'large'
  zip: string;
  time_zone: string;          // IANA tz (e.g., 'America/New_York')
  owner_email: string;
  owner_first_name: string;
  owner_last_name: string;
}
// Response 201
interface SignupInitiateResponse {
  tenant_id: string;          // UUID
  signup_state: 'step1_account';
  owner_email: string;
}
```

**`PUT /api/v1/signup/{tenant_id}/step{2-5}`** — Advance wizard (JWT required)
```typescript
// Request (fields relevant per step; others ignored)
interface SignupStepRequest {
  documents_accepted?: string[];          // Step 2: ['tos', 'privacy', 'eula']
  phone_verified?: boolean;               // Step 3: true after OTP success
  phone_skipped?: boolean;               // Step 3: true if user skipped
  selected_tier_id?: string;             // Step 4: UUID from tier list
  confirmed?: boolean;                   // Step 5: true
  stripe_payment_method_id?: string;     // Step 5 paid: from Stripe Elements
}
// Response 200
interface SignupStepResponse {
  tenant_id: string;
  signup_state: string;                  // next state
  next_step: string | null;
}
```

**`GET /api/v1/signup/{tenant_id}/state`** — Resumability (JWT required)
```typescript
// Response 200
interface SignupStateResponse {
  tenant_id: string;
  signup_state: 'step1_account' | 'step2_legal' | 'step3_phone' | 'step4_tier' | 'step5_confirm' | 'complete';
  collected_data: {
    business_name?: string;
    owner_first_name?: string;
    owner_email?: string;
    selected_tier_id?: string;
    phone_skipped?: boolean;
    phone_verified?: boolean;
  };
}
```

### C.2 Legal Acceptance (A74)

**`GET /api/v1/signup/{tenant_id}/legal/required`**
```typescript
// Response 200
interface LegalRequiredResponse {
  required_documents: Array<{
    document_type: 'tos' | 'privacy' | 'eula';
    current_version_hash: string;
    already_accepted: boolean;
  }>;
}
```

**`POST /api/v1/signup/{tenant_id}/legal/accept`**
```typescript
// Request
interface LegalAcceptRequest {
  document_type: 'tos' | 'privacy' | 'eula' | 'marketing_email_optin';
  document_version_hash: string;
  accepted_at: string;   // ISO 8601
}
// Response 201
interface LegalAcceptResponse {
  acceptance_id: string;
  document_type: string;
  accepted_at: string;
}
```

### C.3 Subscription Tiers (A75)

**`GET /api/v1/subscription-tiers`** (requires `subscription.view` permission)
```typescript
// Response 200
interface SubscriptionTiersListResponse {
  tiers: Array<{
    tier_id: string;                          // UUID
    tier_name: string;                        // 'trial' | 'starter' | 'professional' | 'enterprise'
    display_label: string;
    monthly_price_cents: number;              // 0 for trial
    is_trial: boolean;
    trial_duration_days: number | null;
    max_users: number;
    max_sms_segments_per_month: number | null;
    display_order: number;
    is_active: boolean;
  }>;
}
```

### C.4 Trial Conversion + Tier Upgrade (A76)

**`POST /api/v1/tenants/{tenant_id}/subscription/convert-from-trial`**
```typescript
// Request
interface ConvertFromTrialRequest {
  stripe_payment_method_id: string;   // from Stripe Elements PaymentElement
  selected_tier_id: string;
}
// Response 200
interface ConvertFromTrialResponse {
  new_tier_id: string;
  stripe_subscription_id: string;
  activated_at: string;               // ISO 8601
}
```

### C.5 Onboarding Checklist (A77)

**`GET /api/v1/tenants/{tenant_id}/onboarding/checklist`**
```typescript
// Response 200
interface OnboardingChecklistResponse {
  tenant_id: string;
  account_created: boolean;
  legal_accepted: boolean;
  tier_selected: boolean;
  first_customer_added: boolean;
  first_customer_added_at: string | null;
  catalog_setup: boolean;
  catalog_setup_at: string | null;
  quickbooks_connected: boolean;
  quickbooks_skipped: boolean;
  calendar_connected: boolean;
  calendar_skipped: boolean;
  team_invited: boolean;
  team_skipped: boolean;
  checklist_hidden: boolean;
  checklist_dismissed_permanently: boolean;
}
```

**`PUT /api/v1/tenants/{tenant_id}/onboarding/checklist/skip/{item}`** — `item` ∈ `['quickbooks', 'calendar', 'team']`
Returns: `OnboardingChecklistResponse` (full updated state)

**`PUT /api/v1/tenants/{tenant_id}/onboarding/checklist/hidden`**
Request: `{hidden: boolean}` · Returns: `{checklist_hidden: boolean}`

**`PUT /api/v1/tenants/{tenant_id}/onboarding/checklist/dismissed`**
Returns: `{checklist_dismissed_permanently: true}`

### C.6 Mobile Push Permission (A78)

**`GET /api/v1/users/me/devices/{device_id}/push-permission`**
```typescript
// Response 200
interface PushPermissionResponse {
  device_id: string;
  permission_state: 'not_asked' | 'granted' | 'denied_by_user_choice' | 'denied_by_os' | 'revoked_in_settings';
  last_state_change_at: string;
  dismissable_banner_dismissed_at: string | null;
  banner_should_appear: boolean;   // computed by backend (7-day reappearance logic)
}
```

**`PUT /api/v1/users/me/devices/{device_id}/push-permission`**
Request: `{permission_state: string}` · Returns: `PushPermissionResponse`

---

## Section D — State Management

### D.1 Wizard State Machine (`useSignupWizard`)

```typescript
// Managed by useSignupWizard hook
interface WizardMachineState {
  tenantId: string | null;              // Persisted in sessionStorage after step 1
  currentStep: OnboardingStep;
  signupState: string;                  // Backend canonical state
  collectedData: WizardFormData;        // Accumulated across steps
  isLoading: boolean;
  error: string | null;
  isResuming: boolean;                  // True when loading state for cross-device resume
}

// Actions
type WizardAction =
  | { type: 'STEP1_COMPLETE'; tenantId: string; email: string }
  | { type: 'STEP2_COMPLETE' }
  | { type: 'STEP3_COMPLETE'; phoneVerified: boolean }
  | { type: 'STEP4_COMPLETE'; tierId: string; isTrial: boolean }
  | { type: 'STEP5_COMPLETE' }
  | { type: 'RESUME'; state: SignupStateResponse }
  | { type: 'SET_ERROR'; error: string }
  | { type: 'CLEAR_ERROR' };
```

Step 1 is the only step that calls a **public** endpoint (no JWT). After step 1, Cognito issues a JWT which is stored in memory via `useAuth()`. Subsequent steps use that JWT.

### D.2 Stripe Elements State

Managed internally within `StripePaymentForm`. Exposed via callbacks only:
- `onLoadingChange(true)` → Elements loading or submit in-flight
- `onSuccess(result)` → payment confirmed
- `onError(error)` → Stripe error (card declined, insufficient funds, etc.)

The parent wizard page is stateless with respect to Stripe internals. It only reacts to the three callbacks.

### D.3 Checklist State (TanStack Query)

```typescript
// Primary query
useQuery({
  queryKey: ['onboarding-checklist', tenantId],
  queryFn: () => api.get(`/tenants/${tenantId}/onboarding/checklist`),
  staleTime: 30_000,
  refetchOnWindowFocus: true,
  enabled: !!tenantId,
});

// Skip mutation (optimistic)
useMutation({
  mutationFn: (item: string) => api.put(`/tenants/${tenantId}/onboarding/checklist/skip/${item}`),
  onMutate: async (item) => {
    await queryClient.cancelQueries(['onboarding-checklist', tenantId]);
    const previous = queryClient.getQueryData(['onboarding-checklist', tenantId]);
    queryClient.setQueryData(['onboarding-checklist', tenantId], (old) => ({
      ...old, [`${item}_skipped`]: true
    }));
    return { previous };
  },
  onError: (err, item, ctx) => {
    queryClient.setQueryData(['onboarding-checklist', tenantId], ctx.previous);
  },
  onSettled: () => queryClient.invalidateQueries(['onboarding-checklist', tenantId]),
});
```

### D.4 Trial Expiry State (`useTrialStatus`)

Reads from the auth context (populated via `GET /api/v1/auth/me` on session init). Fields consumed:
- `tenant.trial_ends_at` — computes `daysRemaining`
- `tenant.trial_expired` — boolean for hard gate
- `tenant.is_on_trial` — boolean for soft gate visibility

`useTrialStatus` returns `{isOnTrial, daysRemaining, isExpired, showSoftGate}`. The `(authed)` layout reads `isExpired` and renders `TrialExpiredPage` if true.

The global `QueryClient` `onError` handler in `providers.tsx` intercepts `HTTP 402 {paywall: true}` and calls `router.replace('/(authed)/trial-expired')`.

### D.5 Mobile Push Permission State (`usePushPermission`)

```typescript
interface PushPermissionState {
  deviceId: string;                     // From expo-secure-store
  permissionState: PermissionStateEnum;
  bannerShouldAppear: boolean;
  isLoading: boolean;
  error: string | null;
}

// Actions
const requestPermission = async (): Promise<PermissionStateEnum> => {
  const result = await Notifications.requestPermissionsAsync();
  const state = result.granted ? 'granted' : 'denied_by_os';
  await api.put(`/users/me/devices/${deviceId}/push-permission`, { permission_state: state });
  if (result.granted) {
    const token = await Notifications.getExpoPushTokenAsync();
    // Register token via existing A51 endpoint
  }
  return state;
};

const deferPermission = async (): Promise<void> => {
  await api.put(`/users/me/devices/${deviceId}/push-permission`, {
    permission_state: 'denied_by_user_choice'
  });
};
```

### D.6 Mobile Onboarding Progression (`useMobileOnboarding`)

On every app launch after authentication, reads `GET /api/v1/users/me/devices/{deviceId}/push-permission`. If `permission_state === 'not_asked'`, sets `shouldShowOnboarding = true`. Expo Router's `useRootNavigationState` is used to redirect to `/(onboarding)/welcome` before the tab shell renders.

---

## Section E — Error States

| Error | Surface | Treatment | Recovery |
|:---|:---|:---|:---|
| **Step 1: email already registered** | `signup/account` | Inline field error below email input: "An account with this email already exists. [Sign in instead]" | Link to `/login?email={email}` |
| **Step 1: invalid ZIP/postal code** | `signup/account` | Inline field error: "Enter a valid ZIP or postal code" | Re-enter correct ZIP |
| **Step 2: legal checkboxes not all checked** | `signup/legal` | "Continue" button disabled with `aria-disabled`; helper text: "All three agreements are required to continue" appears on first attempted click | Check all three boxes |
| **Step 3: OTP delivery failure** | `signup/phone` (OTP sub-screen) | Banner: "Couldn't deliver code. Check your number or try again." + "Resend" + "Use different number" + "Skip for now" | Resend / change number / skip |
| **Step 3: OTP wrong code** | `signup/phone` (OTP input) | Inline field error: "Incorrect code. Try again." (up to 3 attempts; 4th locks with 30s cooldown) | Re-enter code / resend |
| **Step 4: tier fetch failure** | `signup/plan` | `<ErrorState>` in the tier grid area: "Couldn't load plans. [Retry]" | Retry button calls `refetch()` |
| **Step 4: Stripe Elements not loaded** | `signup/plan` (paid path) | Spinner in the Stripe form area; timeout after 10s shows "Payment form couldn't load. [Retry]" | Retry re-mounts Elements |
| **Step 5: Stripe card declined** | `signup/ready/pay` | Inline error below payment form (from `StripePaymentForm` internal renderer): "Your card was declined. {Stripe decline message}." | User can change card and retry |
| **Step 5: Stripe insufficient funds** | `signup/ready/pay` | Same as above: "Insufficient funds. Try a different card." | Change card |
| **Step 5: Stripe SetupIntent confirmation failure** | `signup/ready/pay` | Er2 inline: "Payment couldn't be processed. {Stripe message}." | Retry or change payment method |
| **Checklist item completion fails** | Dashboard checklist widget | Optimistic rollback: item reverts to incomplete state; `NotificationBanner` error: "Couldn't mark '{item}' as complete. [Retry]" | Retry button re-triggers action |
| **Push permission OS denial** | Mobile `push-permission` screen | Transitions to `PushDeniedFallback` screen: "No worries — you'll get email and in-app alerts. [Open Settings]" | OS Settings deep-link for later re-enable |
| **Push permission endpoint failure** | Mobile onboarding | Non-blocking: silent retry once; if fails, log to error tracker; onboarding continues | Background retry on next launch |
| **Trial expired — write operation blocked (402)** | Any write surface | Global 402 interceptor redirects to `/trial-expired`; local error state cleared | Convert to paid tier |
| **Checklist skip of non-skippable item** | Dashboard checklist | 422 response → `NotificationBanner` error: "This item can't be skipped." | No action needed; backend guards |
| **Wizard resume: tenant not found** | Any wizard step after step 1 | If `GET /signup/{id}/state` returns 404: clear sessionStorage; redirect to `/signup/account` with banner "Your session expired. Start over." | Restart wizard |

---

## Section F — TypeScript Interfaces

### F.1 `StripePaymentFormProps` (LOCKED for FE-B14)

```typescript
// packages/ui/src/stripe-payment/types.ts

export type StripePaymentMode = 'subscription' | 'one-time';

export interface StripePaymentFormProps {
  /** Stripe publishable key (from env) */
  stripePublishableKey: string;
  /** Backend-provided client secret (SetupIntent or PaymentIntent) */
  clientSecret: string;
  /** Mode determines Stripe flow */
  mode: StripePaymentMode;
  /** Amount in cents — required for one-time mode; ignored for subscription */
  paymentAmountCents?: number;
  /** Submit button label (default: 'Pay' for one-time, 'Set up payment' for subscription) */
  submitLabel?: string;
  /** Called on confirmed payment */
  onSuccess: (result: StripePaymentResult) => void;
  /** Called on Stripe error */
  onError?: (error: StripePaymentError) => void;
  /** Loading state callback */
  onLoadingChange?: (isLoading: boolean) => void;
  /** Externally disable the submit button */
  disabled?: boolean;
  testID?: string;
}

export interface StripePaymentResult {
  paymentMethodId?: string;
  paymentIntentId?: string;
}

export interface StripePaymentError {
  code: string;
  message: string;
  declineCode?: string;
}
```

### F.2 `TierPickerCardPropsExtended` (LOCKED, backward-compatible)

```typescript
// packages/ui/src/tier-picker-card/types.ts — additions

export type TierName =
  | 'trial'
  | 'starter'
  | 'professional'
  | 'enterprise'
  | 'growth'       // kept for FE-B1 backward compat
  | 'pro'          // kept for FE-B1 backward compat
  | (string & {}); // open extension for future DB tiers

export interface TierPickerCardPropsExtended extends TierPickerCardProps {
  /** When true: renders "FREE / for {N} days" in price area */
  isTrialTier?: boolean;
  /** Trial duration in days — used with isTrialTier */
  trialDurationDays?: number;
  /** Max user count — rendered as "Up to {N} users" feature callout if provided */
  maxUsers?: number;
  /** When true: "(current)" label replaces CTA; card is not selectable */
  isCurrentTier?: boolean;
  /** Override for the "Recommended" badge text (default: "Recommended") */
  recommendedBadgeLabel?: string;
}
```

### F.3 `OnboardingStep` Enum

```typescript
// apps/web/src/features/signup/types.ts

export enum OnboardingStep {
  Account = 'account',
  Legal = 'legal',
  Phone = 'phone',
  Plan = 'plan',
  Ready = 'ready',
  Pay = 'pay',
}

export type WizardSignupState =
  | 'step1_account'
  | 'step2_legal'
  | 'step3_phone'
  | 'step4_tier'
  | 'step5_confirm'
  | 'complete';

export const signupStateToStep: Record<WizardSignupState, OnboardingStep> = {
  step1_account: OnboardingStep.Account,
  step2_legal: OnboardingStep.Legal,
  step3_phone: OnboardingStep.Phone,
  step4_tier: OnboardingStep.Plan,
  step5_confirm: OnboardingStep.Ready,
  complete: OnboardingStep.Ready,
};
```

### F.4 `WizardFormData` (accumulated across steps)

```typescript
// apps/web/src/features/signup/types.ts

export interface WizardFormData {
  // Step 1
  businessName?: string;
  trade?: string;
  businessSize?: 'solo' | 'small' | 'medium' | 'large';
  zip?: string;
  timeZone?: string;
  ownerEmail?: string;
  ownerFirstName?: string;
  ownerLastName?: string;
  // Step 2
  tosAccepted?: boolean;
  privacyAccepted?: boolean;
  eulaAccepted?: boolean;
  marketingEmailOptIn?: boolean;
  // Step 3
  phoneVerified?: boolean;
  phoneSkipped?: boolean;
  // Step 4
  selectedTierId?: string;
  selectedTierIsTrial?: boolean;
  // Step 5
  stripePaymentMethodId?: string;
}
```

### F.5 `OnboardingChecklistState`

```typescript
// apps/web/src/features/onboarding/types.ts

export interface OnboardingChecklistState {
  tenantId: string;
  accountCreated: boolean;
  legalAccepted: boolean;
  tierSelected: boolean;
  firstCustomerAdded: boolean;
  firstCustomerAddedAt: string | null;
  catalogSetup: boolean;
  catalogSetupAt: string | null;
  quickbooksConnected: boolean;
  quickbooksSkipped: boolean;
  calendarConnected: boolean;
  calendarSkipped: boolean;
  teamInvited: boolean;
  teamSkipped: boolean;
  checklistHidden: boolean;
  checklistDismissedPermanently: boolean;
}

export type SkippableChecklistItem = 'quickbooks' | 'calendar' | 'team';

export interface ChecklistItemConfig {
  key: keyof OnboardingChecklistState;
  skippedKey?: keyof OnboardingChecklistState;
  label: string;
  actionLabel: string;
  actionRoute: string;
  isSkippable: boolean;
}
```

### F.6 `SubscriptionTier` (from API)

```typescript
// Consumed from @pilot/shared-types (auto-generated) but typed explicitly for clarity

export interface SubscriptionTier {
  tierId: string;
  tierName: string;
  displayLabel: string;
  monthlyPriceCents: number;
  isTrial: boolean;
  trialDurationDays: number | null;
  maxUsers: number;
  maxSmsSegmentsPerMonth: number | null;
  displayOrder: number;
  isActive: boolean;
}
```

### F.7 Mobile Push Permission Types

```typescript
// apps/mobile/hooks/usePushPermission.ts

export type PushPermissionState =
  | 'not_asked'
  | 'granted'
  | 'denied_by_user_choice'
  | 'denied_by_os'
  | 'revoked_in_settings';

export interface UsePushPermissionReturn {
  permissionState: PushPermissionState;
  bannerShouldAppear: boolean;
  isLoading: boolean;
  requestPermission: () => Promise<PushPermissionState>;
  deferPermission: () => Promise<void>;
  openNotificationSettings: () => void;
}
```

---

## Section G — Test Plan

### G.1 Unit Tests (target: 70+)

**`StripePaymentForm` (`packages/ui/__tests__/`)**
- Renders `PaymentElement` in subscription mode
- Renders `PaymentElement` in one-time mode with amount display
- `onSuccess` callback fires with `paymentMethodId` after `stripe.confirmSetup()` resolves
- `onError` callback fires with `StripePaymentError` on card decline
- `onLoadingChange(true)` fires on submit; `onLoadingChange(false)` fires on resolve
- `disabled={true}` renders submit button as disabled
- Inline error renders with `fault-600` token class on Stripe error

**`TierPickerCard` extended props (unit)**
- `isTrialTier={true}` + `trialDurationDays={14}` renders "FREE" + "for 14 days" (not "$0")
- `isCurrentTier={true}` renders "(current)" label; `onSelect` is not called on click
- `recommendedBadgeLabel="Best value"` overrides the default "Recommended" badge text
- `maxUsers={5}` renders "Up to 5 users" in feature list
- Backward compat: FE-B1 skeleton props (`tierName, displayName, monthlyPriceCents, features, isSelected, onSelect`) all work without the extended props
- `TierName` open extension: passing `tierName="custom_enterprise"` does not throw

**Signup wizard step units**
- Step 1: "Continue" disabled when any required field is empty
- Step 1: email format validation triggers inline error on blur
- Step 1: password strength indicator renders correctly for weak/medium/strong
- Step 2: "Continue" disabled until all 3 required checkboxes checked
- Step 2: optional marketing-email checkbox does not affect button state
- Step 2: "Read full →" opens `LegalDocModal` with correct document type
- Step 2: `LegalDocModal` renders "Legal copy pending" placeholder text in dev
- Step 3: "Skip for now" shows confirmation dialog
- Step 3: skip confirmation "Confirm" advances to step 4
- Step 3: OTP input auto-advances on 6th digit entry
- Step 3: "Resend" calls resend endpoint and shows cooldown timer
- Step 4: Trial card is pre-selected by default
- Step 4: Business size "Solo" → "Recommended" badge on `starter` card
- Step 4: Business size "Medium" → "Recommended" badge on `professional` card
- Step 4: Selecting paid tier shows `StripePaymentForm` inline below cards
- Step 4: Selecting trial card hides `StripePaymentForm`
- Step 5 trial: summary shows all 4 completed items with ✓

**Checklist widget units**
- 3 auto-complete items (`account_created`, `legal_accepted`, `tier_selected`) render as ✓ on fresh dashboard load
- Incomplete items render action button
- Skippable items render "Skip" link
- Non-skippable items do not render "Skip" link
- "Skip" click triggers optimistic update → item shows `(skipped)` immediately
- Failed skip mutation rolls back item to incomplete state
- "Hide" collapses widget to compact pill
- Progress counter "N of 8 done" updates when items complete
- When all 8 complete, widget unmounts
- `checklist_dismissed_permanently === true` → widget does not render

**Trial expiry units**
- `useTrialStatus` returns `daysRemaining: 7` for tenant with 7 days left
- `TrialExpiryBanner` renders with correct day count from `useTrialStatus`
- `TrialExpiryBanner` does not render for non-trial tenants
- `TrialUpgradeModal` opens on "Upgrade now" click in banner
- Trial card in upgrade context shows `isCurrentTier={true}` (not selectable)

**Mobile push units**
- `PushPermissionScreen` renders pre-explainer copy (4 bullet points)
- "Maybe later" calls `deferPermission()` without firing OS prompt
- `openNotificationSettings` calls correct `Linking.openURL` for iOS vs Android
- `PushBannerToday` renders when `bannerShouldAppear === true`
- `PushBannerToday` does not render when `bannerShouldAppear === false`
- "Skip tutorial" on any tutorial card navigates to `/(tabs)/today`

### G.2 Integration Tests (target: 18+)

| Test | Approach |
|:---|:---|
| Full wizard steps 1–5 (trial path) against MSW | Submit each step, verify state progression, verify redirect to dashboard with checklist visible |
| Full wizard steps 1–5 (paid path) against MSW + Stripe test mode | Select paid tier, enter Stripe test card 4242 4242 4242 4242, verify payment intent confirmation, verify dashboard redirect |
| Stripe card decline (4000 0000 0000 0002) | Verify inline error renders; no wizard progression |
| Wizard cross-device resume | Start wizard on step 1; simulate navigation to step 4 URL; verify resume reads backend state and redirects to correct step |
| Legal acceptance logging | Complete step 2; verify `POST .../legal/accept` called 3 times (once per document); verify acceptance_id received |
| Post-wizard checklist renders on dashboard | After wizard complete, navigate to `/dashboard`; verify `OnboardingChecklistWidget` is visible; verify 3 items auto-complete |
| Checklist skip (quickbooks) | Click "Skip"; verify optimistic update; verify `PUT .../skip/quickbooks` called; verify "(skipped)" state persists on refetch |
| Checklist auto-completion via customer create | Create customer via Customers route; verify checklist `invalidateQueries` fires; verify `first_customer_added: true` on next fetch |
| Trial-to-paid conversion flow | `daysRemaining: 3` → banner visible; click "Upgrade now" → modal opens; select Starter; enter test card; verify conversion API called; verify banner disappears |
| Trial expiration 402 intercept | Mock any write API returning 402 `{paywall: true}`; verify router redirects to `/trial-expired` |
| Hard gate at trial-expired | Navigate to `/dashboard` with `trial_expired: true` in auth context; verify `TrialExpiredPage` renders instead |
| ToS/Privacy/EULA inline modal | Click "Read full →" on any legal doc; verify `LegalDocModal` opens with correct content (placeholder in dev); verify wizard does not navigate away |
| OTP verification sub-screen | Enter phone → send code → enter 6-digit OTP → verify `phone_verified: true` in step 3 payload |
| Phone skip with confirmation | Click "Skip for now"; confirm dialog → verify `phone_skipped: true` in step 3 payload |
| Mobile onboarding detection | Mock `GET .../push-permission` returning `not_asked`; verify `useMobileOnboarding` routes to `/(onboarding)/welcome` |
| Mobile push permission grant | Tap "Allow notifications"; mock OS grant; verify `PUT .../push-permission` called with `granted`; verify screen advances to tutorial |
| Mobile push permission deny | Tap "Allow notifications"; mock OS deny; verify `PUT .../push-permission` called with `denied_by_os`; verify `PushDeniedFallback` renders |
| Push banner appearance | Mock `banner_should_appear: true`; verify `PushBannerToday` renders on Today tab |

### G.3 E2E Tests (target: 4+)

| Test | Tool | Environment |
|:---|:---|:---|
| Full signup → dashboard (trial) | Playwright | Dev Cognito + dev backend + MSW Stripe |
| Full signup → payment → dashboard (paid, Starter) | Playwright | Dev Cognito + dev backend + Stripe test mode |
| Trial expiration cycle (advance clock) | Playwright | Dev backend with system clock override |
| Cross-device wizard resume | Playwright | Two browser contexts, same session |

---

## Section H — Token Audit

| Element | Token | Class |
|:---|:---|:---|
| Trial tier "FREE" price text | brand-600 (or `text-brand-600`) | Highlights the $0 price as the preferred path |
| Trial tier "Recommended" / featured badge background | `bg-brand-600 text-white` | Existing FE-B1 isFeatured treatment — no change |
| Paid tier selected state border | `border-brand-600` | Existing FE-B1 isSelected treatment — no change |
| Paid tier selected checkmark fill | `bg-brand-600` | Existing FE-B1 — no change |
| `StripePaymentForm` inline error text | `text-fault-600` | Fault tokens for payment errors |
| `StripePaymentForm` submit button | `bg-brand-600 hover:bg-brand-800 text-white` | Brand tokens for primary CTA |
| Legal checkbox required indicator | `text-fault-600` asterisk (`*`) beside each label | Fault tokens for required field markers |
| Legal checkbox "Continue" disabled state | `opacity-40 cursor-not-allowed` | Neutral treatment for disabled CTA |
| Post-wizard checklist completed item (✓) | `text-margin-600` (green check) | Margin/success tokens for completion |
| Post-wizard checklist skipped item | `text-neutral-400 line-through` | Neutral tokens for deprioritized items |
| Trial expiry countdown (7d / 3d) | `text-alert-600 bg-alert-50` banner | Alert tokens for early warning |
| Trial expiry countdown (1d / expired) | `text-fault-600 bg-fault-50` banner | Fault tokens for critical urgency |
| `TrialExpiredPage` headline | `text-fault-700` | Fault tokens; expiration is a negative state |
| Push banner on Today tab ("Push is off") | `bg-neutral-100 text-neutral-700` | Neutral; non-alarming for "can improve" state |
| Phone OTP verification success ("✓ Phone verified") | `text-margin-600` | Margin/success tokens |
| Wizard step progress bar — completed step | `bg-brand-600` | Brand tokens for completed steps |
| Wizard step progress bar — current step | `bg-brand-300` | Mid-brand for active step |
| Wizard step progress bar — future step | `bg-neutral-200` | Neutral for pending steps |

---

## Section I — Downstream Contract Lock (for FE-B14)

### I.1 `StripePaymentForm` — Locked Interface

FE-B14 imports `StripePaymentForm` from `@pilot/ui` for the public invoice one-time payment flow. The locked props that FE-B14 must not modify:

| Prop | Type | FE-B14 Usage |
|:---|:---|:---|
| `stripePublishableKey` | `string` | Same key (same Stripe account) |
| `clientSecret` | `string` | Payment Intent client secret from `POST /api/v1/public/invoices/{token}/payment-intent` |
| `mode` | `StripePaymentMode` | **`'one-time'`** — FE-B14 always uses one-time mode |
| `paymentAmountCents` | `number` | Required in FE-B14; customer-entered amount (full or partial) |
| `onSuccess` | `(result) => void` | FE-B14 shows "Payment received" confirmation |
| `onError` | `(error) => void` | FE-B14 shows inline error for customer |
| `submitLabel` | `string?` | FE-B14 passes `"Pay {amount}"` |

**Additive-only props FE-B14 may introduce** (in `packages/ui/src/stripe-payment/types.ts` as optional extensions):
- `invoiceToken?: string` — for one-time mode, passed to backend payment intent creation
- `allowAmountVariance?: boolean` — shows "Pay partial / full amount" selector
- `onAmountChange?: (cents: number) => void` — for the amount-variance UI

FE-B14 must NOT modify:
- `StripePaymentResult` or `StripePaymentError` shapes
- `StripePaymentMode` union (additive extension allowed: `| 'one-time-with-variance'` is acceptable if needed)
- Provider location (Elements wrapper remains internal to the component)
- Error rendering behavior (inline + callback; both must remain)

### I.2 `TierPickerCard` — Interface Frozen

FE-B14 does **not** consume `TierPickerCard` (FE-B14's public-facing surfaces have no tier picker). The interface is frozen as of FE-B13 completion. Future batches may add optional props only; the `TierPickerCardProps` required props (`tierName`, `displayName`, `monthlyPriceCents`, `features`, `onSelect`) must not change signature.

### I.3 FE-B12 Interfaces Consumed by FE-B13 (Reference)

Per FE-B12 lock notifications, FE-B13 uses these interfaces exactly as locked:

| Import | Source | FE-B13 usage |
|:---|:---|:---|
| `MFAEnrollmentWizard` + `MFAEnrollmentWizardPropsExtended` | `packages/ui/src/mfa-enrollment-wizard/` | Embedded in wizard for tenants with `mfa_required=true` at signup (Cognito force-flow redirect per FE-B2 pattern) |
| `NotificationPreferenceMatrix` | `packages/ui/src/notification-preference-matrix/` | Embedded in mobile onboarding final step with `visibleCategories={['job_updates', 'customer_activity', 'billing']}` (3-category subset) |
| `NotificationCenterBell` | `packages/ui/src/notification-center-bell/` | Embedded in step 5 confirmation screen as live proof of push notification delivery |
| `useInAppNotifications` | `packages/ui/src/hooks/useInAppNotifications.ts` | Used in trial expiry banner to surface billing notifications inline |

FE-B13 may only consume these with additive optional props. It must not fork or re-implement any of the above.

---

*Design document complete. All 7 Key Design Decisions resolved. All sections A–I written. Interfaces locked for FE-B14 consumption.*
