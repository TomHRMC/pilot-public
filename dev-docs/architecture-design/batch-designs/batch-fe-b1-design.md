# Batch FE-B1 Design — Component Library Foundation (States Catalog + Platform Patterns)

**Batch**: FE-B1
**Design Date**: May 21, 2026
**Architect**: Pilot Architect mode
**Consumer**: Pilot React Engineer mode (Phase 2 implementation)
**Source Plan**: `dev-docs/analysis/pilot-app-mvp-frontend-impl-plan.md` §6 FE-B1
**Prerequisite Batches**: FE-B0 ✅ COMPLETE (May 21, 2026 — 43 tests, all pass)
**Gates**: FE-B2 (login surface); all subsequent surface batches FE-B3 through FE-B16

---

## Prerequisite Verification

FE-B0 completion confirmed via `pilot-app-mvp-frontend-impl-plan.md` §7 Implementation Detail Record. The following are live and verified before FE-B1 begins:

| Item | Status |
|:---|:---|
| `@pilot/ui` package name (renamed from `@repo/ui`) | ✅ Confirmed — `packages/ui/package.json` `"name": "@pilot/ui"` |
| `packages/ui/src/tokens.ts` — Pass 1 design tokens | ✅ Confirmed — full token system with `colors`, `lightTheme`, `darkTheme`, `spacing`, `radii`, `motion`, `voiceStateTokens` |
| `packages/ui/src/auth/` — `AuthProvider`, `useAuth`, `RequireAuth`, `types` | ✅ Confirmed — all files present |
| `packages/ui/src/role-gate/` — `RoleGate`, `useRequiresPermission`, `permissions` | ✅ Confirmed — all files present |
| `packages/ui/src/hooks/index.ts` — placeholder | ✅ Confirmed — placeholder present |
| Web routing skeleton (11 sections under `(authed)/`) | ✅ Confirmed — all route files present |
| Mobile 5-tab skeleton (`index`, `jobs`, `customers`, `calcs`, `owner`) | ✅ Confirmed — all tab files present |
| ESLint `no-hardcoded-design-values` rule — WARNING severity | ✅ Confirmed (upgraded to ERROR at FE-B1 close per §G-6) |
| TanStack Query + apiClient + MSW | ✅ Confirmed — installed and wired |

**Codebase grep result (confirmed new — none pre-exist)**:

```
frontend/ grep for: EmptyState, LoadingState, ErrorState, NotificationBanner,
  InFlightSyncIndicator, EmailBrandingPreview, MFAEnrollmentWizard, TierPickerCard,
  FirstTimeUserState, FTU, states/, notification-banner/, sync-indicator/
→ 0 results in *.tsx, 0 results in *.ts
```

All 20+ components in this batch are confirmed **new**. No pre-existing implementations to extend or conflict with.

---

## A. Component Implementation Plan

All components are new (confirmed above via grep). Organized by category folder.

### A.1 States Catalog — `packages/ui/src/states/`

The states catalog uses a **discriminated-union API** (see §G-1). A single `<EmptyState type="…" />` covers all 5 variants; same for `<LoadingState>`, `<ErrorState>`, `<FirstTimeUserState>`. This keeps the component count low while preserving per-variant visual treatment.

**Platform variant strategy**: `states/` uses web and mobile subfolders with a shared `types.ts` because the rendering primitives differ significantly (shadcn/ui for web; Gluestack for mobile), but the prop API is identical.

| Component | File Path | Discriminant Values | Parent Surface |
|:---|:---|:---|:---|
| `EmptyStateWeb` | `packages/ui/src/states/web/EmptyState.tsx` | `type: "no-data" \| "no-results" \| "not-yet-set-up" \| "permission-denied" \| "filtered-empty"` | Every web surface |
| `EmptyStateMobile` | `packages/ui/src/states/mobile/EmptyState.tsx` | Same `type` union | Every mobile surface |
| `LoadingStateWeb` | `packages/ui/src/states/web/LoadingState.tsx` | `type: "full-page" \| "inline" \| "optimistic"` | Every web surface |
| `LoadingStateMobile` | `packages/ui/src/states/mobile/LoadingState.tsx` | Same `type` union | Every mobile surface |
| `ErrorStateWeb` | `packages/ui/src/states/web/ErrorState.tsx` | `type: "network" \| "server" \| "validation" \| "permission"` | Every web surface |
| `ErrorStateMobile` | `packages/ui/src/states/mobile/ErrorState.tsx` | Same `type` union | Every mobile surface |
| `FirstTimeUserStateWeb` | `packages/ui/src/states/web/FirstTimeUserState.tsx` | `type: "dashboard" \| "quotes" \| "schedule" \| "customers" \| "invoices" \| "reports" \| "comms" \| "settings"` | Dashboard, Quotes, Schedule, Customers, Invoices, Reports, Comms, Settings (new tenants) |
| `FirstTimeUserStateMobile` | `packages/ui/src/states/mobile/FirstTimeUserState.tsx` | Same `type` union | Home, Jobs, Customers (new techs) |
| `StateTypes` | `packages/ui/src/states/types.ts` | Shared TypeScript interfaces and discriminated unions | — |
| `StatesIndex` | `packages/ui/src/states/index.ts` | Re-exports via platform conditional | — |

> **Mobile subset for FTU**: Not all 8 FTU variants are relevant on mobile. Mobile FTU only renders for `"dashboard"` (Home tab), `"schedule"` (Jobs tab), and `"customers"` (Customers tab). The remaining 5 variants exist in the mobile component but return `null` when rendered on mobile — consumers don't need to check. This is enforced in the mobile component via a `MOBILE_SUPPORTED_FTU_TYPES` constant.

### A.2 Notification Banner — `packages/ui/src/notification-banner/`

| Component / Hook | File Path | Notes |
|:---|:---|:---|
| `NotificationBannerWeb` | `packages/ui/src/notification-banner/web/NotificationBanner.tsx` | Web portal-based toast; renders into `#notification-root` DOM node; uses shadcn/ui primitives |
| `NotificationBannerMobile` | `packages/ui/src/notification-banner/mobile/NotificationBanner.tsx` | Gluestack `Toast` primitive; stacks via Gluestack's built-in toast queue |
| `useNotificationQueue` | `packages/ui/src/notification-banner/useNotificationQueue.ts` | Cross-platform hook; manages queue state; consumed by both platforms |
| `NotificationQueueProvider` | `packages/ui/src/notification-banner/NotificationQueueProvider.tsx` | React context provider; must wrap the app root in both web and mobile |
| `NotificationPortal` | `packages/ui/src/notification-banner/web/NotificationPortal.tsx` | Web-only; React Portal target injected into layout; provides `#notification-root` DOM node |
| `BannerTypes` | `packages/ui/src/notification-banner/types.ts` | `NotificationItem`, `NotificationSeverity`, `NotificationQueueContextValue` |
| `NotificationBannerIndex` | `packages/ui/src/notification-banner/index.ts` | Re-exports public API |

### A.3 In-Flight Sync Indicator — `packages/ui/src/sync-indicator/`

Skeleton only in FE-B1. Props interface and visual shell locked. FE-B4 is the first consumer; FE-B15 fleshes out data-fetching against `services/sync_status.py`.

| Component | File Path | Notes |
|:---|:---|:---|
| `InFlightSyncIndicatorWeb` | `packages/ui/src/sync-indicator/web/InFlightSyncIndicator.tsx` | Skeleton web implementation |
| `InFlightSyncIndicatorMobile` | `packages/ui/src/sync-indicator/mobile/InFlightSyncIndicator.tsx` | Skeleton mobile implementation |
| `SyncIndicatorTypes` | `packages/ui/src/sync-indicator/types.ts` | Props interface locked in FE-B1 |
| `SyncIndicatorIndex` | `packages/ui/src/sync-indicator/index.ts` | Re-exports |

### A.4 Email Branding Preview Skeleton — `packages/ui/src/email-branding-preview/`

Web-only skeleton. Fleshed out in FE-B14. Mobile is not in scope (email branding is a settings surface, web-only per Settings IA three-question mobile rule).

| Component | File Path | Notes |
|:---|:---|:---|
| `EmailBrandingPreview` | `packages/ui/src/email-branding-preview/EmailBrandingPreview.tsx` | Web-only skeleton with placeholder render |
| `EmailBrandingPreviewTypes` | `packages/ui/src/email-branding-preview/types.ts` | Props interface locked in FE-B1 |
| `EmailBrandingPreviewIndex` | `packages/ui/src/email-branding-preview/index.ts` | Re-exports |

### A.5 MFA Enrollment Wizard Skeleton — `packages/ui/src/mfa-enrollment-wizard/`

Cross-platform skeleton (web + mobile — account settings has mobile subset in FE-B12). Props interface and enrollment-path enum locked. Fleshed out in FE-B12.

| Component | File Path | Notes |
|:---|:---|:---|
| `MFAEnrollmentWizardWeb` | `packages/ui/src/mfa-enrollment-wizard/web/MFAEnrollmentWizard.tsx` | Web skeleton |
| `MFAEnrollmentWizardMobile` | `packages/ui/src/mfa-enrollment-wizard/mobile/MFAEnrollmentWizard.tsx` | Mobile skeleton (fewer steps — mobile-compatible paths only) |
| `MFAEnrollmentTypes` | `packages/ui/src/mfa-enrollment-wizard/types.ts` | Props + enrollment path enum locked |
| `MFAEnrollmentIndex` | `packages/ui/src/mfa-enrollment-wizard/index.ts` | Re-exports |

### A.6 Tier Picker Card Skeleton — `packages/ui/src/tier-picker-card/`

Web-only skeleton (signup wizard is web-only in FE-B13; mobile setup phase is a separate screen that doesn't use the tier picker). Fleshed out in FE-B13.

| Component | File Path | Notes |
|:---|:---|:---|
| `TierPickerCard` | `packages/ui/src/tier-picker-card/TierPickerCard.tsx` | Web-only skeleton |
| `TierPickerCardTypes` | `packages/ui/src/tier-picker-card/types.ts` | Props interface locked in FE-B1 |
| `TierPickerCardIndex` | `packages/ui/src/tier-picker-card/index.ts` | Re-exports |

### A.7 Package Manifest and ESLint Promotion

| Item | File Path | Change |
|:---|:---|:---|
| `packages/ui` index barrel | `packages/ui/src/index.ts` | Add exports for all FE-B1 components |
| `packages/ui` exports map | `packages/ui/package.json` | Add named exports for all 6 new categories |
| ESLint rule severity | `packages/eslint-config/rules/no-hardcoded-design-values.ts` | Change severity from `'warn'` → `'error'` |
| ESLint config | `packages/eslint-config/index.js` (or equivalent flat config) | Verify rule is wired at `'error'` level |

---

## B. Execution Order

Implementation order within FE-B1, with intra-batch dependency rationale:

| Step | Item | Rationale |
|:---|:---:|:---|
| 1 | **`packages/ui/src/states/types.ts`** — shared discriminated union types for all 4 state components | Types must exist before any component file imports them |
| 2 | **`EmptyState` (web + mobile)**  — 5-variant discriminated union | Highest reuse count; FE-B2 login surfaces use it first |
| 3 | **`LoadingState` (web + mobile)** — 3-variant discriminated union | Login surface needs `inline` loading state immediately |
| 4 | **`ErrorState` (web + mobile)** — 4-variant discriminated union | Login surface needs `network` and `validation` error states |
| 5 | **`FirstTimeUserState` (web + mobile)** — 8-variant FTU | Lower priority than generic states; only shown to new tenants; no FE-B2 dependency |
| 6 | **`notification-banner/types.ts`** — shared banner types | Must exist before web/mobile banner components import them |
| 7 | **`useNotificationQueue` hook** — cross-platform queue state | The hook is the source of truth; both platform components depend on it |
| 8 | **`NotificationQueueProvider`** — React context provider | Must exist before web/mobile components can call `useNotificationQueue` |
| 9 | **`NotificationBanner` (web + mobile)** — portal-based toast | Depends on hook and provider |
| 10 | **`NotificationPortal` (web only)** — DOM portal target | Depends on web banner; must be added to `apps/web/src/app/layout.tsx` as well |
| 11 | **`sync-indicator/types.ts` + `InFlightSyncIndicator` (web + mobile skeleton)** | FE-B4 dispatch board is the first consumer; skeleton unblocks that batch |
| 12 | **`EmailBrandingPreview` skeleton (web)** | FE-B11 settings may reference it; lower urgency than banners |
| 13 | **`MFAEnrollmentWizard` skeleton (web + mobile)** | FE-B12 account settings fleshes it out; skeleton here establishes the contract |
| 14 | **`TierPickerCard` skeleton (web)** | FE-B13 signup wizard fleshes it out |
| 15 | **`packages/ui/src/index.ts`** — add all FE-B1 exports | Cannot export until all components are written |
| 16 | **`packages/ui/package.json` exports map** — add named exports | Must come after all `index.ts` barrel files are created |
| 17 | **ESLint `no-hardcoded-design-values` → `error`** | Final step; run `pnpm lint` to verify zero violations across all new components before closing the batch |

---

## C. New Routes

**FE-B1 introduces no new routes.** This is a component library batch — all new code lives in `packages/ui/src/`. No file-based routes are created in `apps/web/src/app/` or `apps/mobile/app/`.

However, two **layout-level changes** are required in existing files:

| File | Change Required | Rationale |
|:---|:---|:---|
| `apps/web/src/app/layout.tsx` | Add `<NotificationPortal />` and `<NotificationQueueProvider>` at root | The portal DOM node must exist in the layout; the queue provider must wrap all surfaces |
| `apps/mobile/app/_layout.tsx` | Add `<NotificationQueueProvider>` at root | Same provider required for mobile banner queue |

These are extensions to FE-B0's layout files, not new routes.

---

## D. API Endpoint Consumption

FE-B1 is primarily a visual component library batch. Only `<NotificationBanner>` has a future API integration path — but it is **not wired in FE-B1**. The SSE subscription happens in FE-B12.

| Component | Future Endpoint | FE-B1 Status | Wired In | MSW Handler Location |
|:---|:---|:---|:---|:---|
| `NotificationBanner` | `GET /sse/notifications` (BE-B10/A57) — SSE stream of `in_app` channel events | **Not wired** — FE-B1 establishes the queue API shape only; `useNotificationQueue` accepts an `addNotification(item)` function for programmatic injection | FE-B12 | `apps/web/src/mocks/handlers/notifications.ts` (to be created in FE-B12) |
| `InFlightSyncIndicator` | `GET /api/v1/sync/status?surface={surface}` (BE-B15/A79) | **Not wired** — skeleton accepts `pendingCount`, `lastSyncedAt`, `state` as direct props; data-fetching hook (`useInFlightSyncStatus`) created in FE-B15 | FE-B15 | `apps/web/src/mocks/handlers/sync.ts` (to be created in FE-B15) |
| All other FE-B1 components | None | N/A — no API calls | — | — |

**`useNotificationQueue` injection API** (FE-B1 establishes this for downstream use):

```typescript
// Any surface batch can inject a notification:
const { addNotification } = useNotificationQueue();
addNotification({
  id: crypto.randomUUID(),
  severity: 'success',
  title: 'Quote Sent',
  detail: 'Q-1042 sent to Acme Electrical',
  deepLinkTarget: '/quotes/q-1042',
});
```

The hook stores the queue in Zustand client state. SSE-sourced notifications (FE-B12) will call `addNotification` from an SSE event handler — the hook's API is compatible with both programmatic injection and SSE delivery.

---

## E. Pattern Reuse Decisions

### E.1 §16.13 In-Flight Sync Indicator

FE-B1 establishes the **skeleton** that FE-B4 (dispatch), FE-B7 (mobile sync), FE-B8 (calendar), and FE-B9 (QB) consume, and FE-B15 refines.

Import path (established now, stable for all consumers):
```typescript
import { InFlightSyncIndicator } from '@pilot/ui/sync-indicator';
```

Pattern established per `mvp-arch.md §16.13`: five compositional states (`idle`, `syncing`, `error`, `paused`, `synced-pending`), amber threshold at 5 pending items (tenant-configurable in FE-B15), manual sync trigger for applicable surfaces. FE-B1 skeleton renders a placeholder that accepts and displays props; FE-B15 connects the real data hook.

### E.2 §16.7 Always-Preview-Before-Send (NotificationBanner infrastructure)

`<NotificationBanner>` is the canonical in-app feedback mechanism for all preview-before-send confirmation outcomes. FE-B6's `usePreviewBeforeSend()` calls `addNotification()` after send confirmation. FE-B1 establishes the hook API that FE-B6 will call.

Import path:
```typescript
import { NotificationBanner, useNotificationQueue, NotificationQueueProvider } from '@pilot/ui/notification-banner';
```

### E.3 §16.6 Four-Class Severity via NotificationBanner

`NotificationBanner` severity directly maps to the four-class severity pattern from `mvp-arch.md §16.6`:

| Severity Prop | §16.6 Class | Auto-Dismiss |
|:---|:---|:---|
| `info` | Auto-with-notice | 6s |
| `success` | Auto-with-notice | 6s |
| `warning` | Auto-with-notice | 6s |
| `error` | User-resolvable | 12s |
| `critical` | User-resolvable | 12s (no auto-dismiss for `critical` — requires explicit dismiss) |

> **Token consumption** for severity colors:
> - `info` → `colors.brand[600]` background
> - `success` → `colors.margin[600]` background
> - `warning` → `colors.alert[400]` background
> - `error` → `colors.fault[600]` background
> - `critical` → `colors.fault[800]` background

### E.4 States Catalog as Universal Surface Vocabulary

Every surface batch (FE-B2 onward) imports from the states catalog without any local implementation:

```typescript
// Web surface import (resolved to web variant via package.json exports):
import { EmptyState, LoadingState, ErrorState, FirstTimeUserState } from '@pilot/ui/states';

// Usage:
<LoadingState type="full-page" />
<EmptyState type="no-data" title="No jobs yet" />
<ErrorState type="network" onRetry={() => refetch()} />
<FirstTimeUserState type="quotes" />
```

### E.5 Skeleton-vs-Fleshed Pattern (canonical in FE-B1)

FE-B1 establishes the **skeleton-vs-fleshed** pattern that applies to all three skeleton components:

1. **API is locked in FE-B1** — prop interface is the contract, not the render output
2. **Fleshing-out batches must not rename existing props** — adding new optional props is permitted
3. **Skeleton renders must pass all unit tests** — placeholder content is acceptable but must match the props API exactly
4. **Fleshing batch updates only the render** — no changes to `types.ts` signatures for existing props

---

## F. Shared Module Interfaces

> **Critical**: these interfaces are consumed by FE-B2 through FE-B16. The React Engineer must not deviate from these signatures. Adding optional props is allowed; removing or renaming props is a breaking change requiring Architect review.

### F.1 States Catalog — `packages/ui/src/states/types.ts`

```typescript
// packages/ui/src/states/types.ts

// ── Empty States ──────────────────────────────────────────────────────────────

export type EmptyStateType =
  | 'no-data'         // Entity list is empty (no records exist yet)
  | 'no-results'      // Search/filter returned zero results
  | 'not-yet-set-up'  // Feature requires setup before use (e.g., QuickBooks not connected)
  | 'permission-denied'  // Role gate — user cannot view this content
  | 'filtered-empty'; // Date range / filter selection returns nothing

export interface EmptyStateProps {
  type: EmptyStateType;
  /** Override the default heading for this type */
  title?: string;
  /** Override the default body copy for this type */
  description?: string;
  /** Primary CTA label (e.g., "Create your first quote") */
  ctaLabel?: string;
  /** Primary CTA handler */
  onCta?: () => void;
  /** Secondary CTA label (e.g., "Learn more") */
  secondaryCtaLabel?: string;
  onSecondaryCta?: () => void;
  /** Illustration key; resolves to platform-appropriate art */
  illustration?: EmptyStateIllustration;
  testID?: string;  // Mobile e2e targeting
}

export type EmptyStateIllustration =
  | 'empty-clipboard'  // no-data, no-results
  | 'lock'             // permission-denied
  | 'wrench'           // not-yet-set-up
  | 'filter'           // filtered-empty
  | 'none';            // No illustration (compact layouts)

// ── Loading States ────────────────────────────────────────────────────────────

export type LoadingStateType =
  | 'full-page'   // Full-viewport skeleton screen for initial page loads
  | 'inline'      // Spinner for embedded async areas (form submits, button loads)
  | 'optimistic'; // Subtle pulse on an entity that has a pending operation

export interface LoadingStateProps {
  type: LoadingStateType;
  /** For 'full-page': number of skeleton rows to render (default: 4) */
  skeletonRows?: number;
  /** For 'inline': label for screen readers (default: "Loading…") */
  label?: string;
  /** For 'optimistic': applies pulse animation to children */
  children?: React.ReactNode;
  testID?: string;
}

// ── Error States ──────────────────────────────────────────────────────────────

export type ErrorStateType =
  | 'network'      // No internet / connection timeout
  | 'server'       // Backend 5xx error
  | 'validation'   // Form validation failure (rendered inline in forms, not as full-page)
  | 'permission';  // 403 / unauthorized — distinct from permission-denied empty state

export interface ErrorStateProps {
  type: ErrorStateType;
  /** Override default heading for this error type */
  title?: string;
  /** Override default body copy */
  description?: string;
  /** Show a retry CTA (applicable for network, server errors) */
  onRetry?: () => void;
  /** For 'validation': field-level error map — renders inline under relevant inputs */
  fieldErrors?: Record<string, string>;
  /** Contact-support CTA for persistent server errors */
  onContactSupport?: () => void;
  testID?: string;
}

// ── First-Time-User States ────────────────────────────────────────────────────

export type FTUSurface =
  | 'dashboard'   // Owner's first login: guide to adding tech, sending first quote
  | 'quotes'      // No quotes created yet: guide to voice quote creation
  | 'schedule'    // No jobs scheduled: guide to dispatch board
  | 'customers'   // No customers added: guide to customer management
  | 'invoices'    // No invoices sent: guide to invoice workflow
  | 'reports'     // No data for reports: guide to data-generating actions
  | 'comms'       // No messages sent: guide to customer communications
  | 'settings';   // Settings not yet configured: guide to key settings

export interface FirstTimeUserStateProps {
  type: FTUSurface;
  /**
   * Override the default headline for this FTU surface.
   * Default copy is baked into the component per Pass 4 Tier 3 #9 spec.
   */
  headingText?: string;
  /** Override the default body copy */
  bodyText?: string;
  /** Override the primary CTA label */
  ctaLabel?: string;
  /** CTA handler — typically navigates to the first onboarding action */
  onCta?: () => void;
  /** Optional secondary CTA (e.g., "Watch a 2-minute demo") */
  secondaryCtaLabel?: string;
  onSecondaryCta?: () => void;
  testID?: string;
}

/**
 * Default FTU content map — used when props are not overridden.
 * Copy sourced from Pass 4 Tier 3 #9 spec; parameterized here for
 * discoverability and future copy iteration without code changes.
 */
export const FTU_DEFAULTS: Record<
  FTUSurface,
  { heading: string; body: string; ctaLabel: string; ctaPath: string }
> = {
  dashboard: {
    heading: "Welcome to Pilot",
    body: "Start by adding your first technician or sending a voice quote.",
    ctaLabel: "Add a technician",
    ctaPath: "/settings/team",
  },
  quotes: {
    heading: "No quotes yet",
    body: "Use the Pilot mobile app to create your first quote by voice, hands-free.",
    ctaLabel: "Learn how voice quotes work",
    ctaPath: "/help?context=voice-quotes",
  },
  schedule: {
    heading: "Your dispatch board is empty",
    body: "Schedule your first job by dragging a tech to a time slot.",
    ctaLabel: "View the dispatch board",
    ctaPath: "/schedule",
  },
  customers: {
    heading: "No customers yet",
    body: "Add your first customer to start sending quotes and tracking jobs.",
    ctaLabel: "Add a customer",
    ctaPath: "/customers/new",
  },
  invoices: {
    heading: "No invoices sent",
    body: "Invoices are generated automatically when a quote is approved and work is complete.",
    ctaLabel: "View quotes",
    ctaPath: "/quotes",
  },
  reports: {
    heading: "Not enough data yet",
    body: "Complete your first job to start seeing profitability and efficiency reports.",
    ctaLabel: "Go to the dispatch board",
    ctaPath: "/schedule",
  },
  comms: {
    heading: "No messages sent",
    body: "Send your first customer communication — on the way, running late, job complete.",
    ctaLabel: "Send a message",
    ctaPath: "/comms/new",
  },
  settings: {
    heading: "Configure your account",
    body: "Set your company name, logo, and notification preferences to personalize Pilot.",
    ctaLabel: "Open settings",
    ctaPath: "/settings",
  },
};
```

### F.2 Notification Banner — `packages/ui/src/notification-banner/types.ts`

```typescript
// packages/ui/src/notification-banner/types.ts

export type NotificationSeverity =
  | 'info'      // Informational; auto-dismiss 6s
  | 'success'   // Action succeeded; auto-dismiss 6s
  | 'warning'   // Needs attention; auto-dismiss 6s
  | 'error'     // Recoverable error; auto-dismiss 12s
  | 'critical'; // Requires explicit user dismiss — NO auto-dismiss

export interface NotificationItem {
  /** Unique ID for this notification; used for dedup and dismiss targeting */
  id: string;
  severity: NotificationSeverity;
  /** Bold title line */
  title: string;
  /** Optional second-line detail */
  detail?: string;
  /**
   * When provided, the entire banner is clickable and navigates to this path.
   * Matches the `deep_link_target` field from BE-B10/A57 SSE payload.
   */
  deepLinkTarget?: string;
  /**
   * Override auto-dismiss duration in ms.
   * Defaults: info/success/warning = 6000; error = 12000; critical = never
   */
  dismissAfterMs?: number;
  /** Timestamp the notification was created (for queue ordering) */
  createdAt: Date;
}

export interface NotificationQueueContextValue {
  /** Current queue of visible notifications (max 3 shown) */
  notifications: NotificationItem[];
  /** Inject a new notification into the queue */
  addNotification: (item: Omit<NotificationItem, 'createdAt'>) => void;
  /** Dismiss a specific notification by ID */
  dismissNotification: (id: string) => void;
  /** Dismiss all visible notifications */
  dismissAll: () => void;
}

// ── Web-specific props ───────────────────────────────────────────────────────

export interface NotificationBannerWebProps {
  notification: NotificationItem;
  onDismiss: (id: string) => void;
  /**
   * Navigation callback — called when user clicks banner with deepLinkTarget.
   * Surfaces pass their router's push/navigate function here.
   * Defaults to window.location.href assignment if not provided.
   */
  onNavigate?: (path: string) => void;
}

// ── Mobile-specific props ────────────────────────────────────────────────────

export interface NotificationBannerMobileProps {
  notification: NotificationItem;
  onDismiss: (id: string) => void;
  onNavigate?: (path: string) => void;
}
```

### F.3 Notification Queue Hook — `packages/ui/src/notification-banner/useNotificationQueue.ts`

```typescript
/**
 * useNotificationQueue — cross-platform hook for managing the notification queue.
 *
 * @location packages/ui/src/notification-banner/useNotificationQueue.ts
 *
 * Must be called inside a <NotificationQueueProvider>.
 * Queue max size: 3 visible notifications. Oldest is automatically dismissed
 * when a 4th notification is added (FIFO).
 */
export function useNotificationQueue(): NotificationQueueContextValue;

// ── NotificationQueueProvider ────────────────────────────────────────────────
// packages/ui/src/notification-banner/NotificationQueueProvider.tsx

export interface NotificationQueueProviderProps {
  children: React.ReactNode;
  /**
   * Maximum visible notifications in the queue.
   * Default: 3. When exceeded, oldest is auto-dismissed.
   */
  maxVisible?: number;
}

export function NotificationQueueProvider(
  props: NotificationQueueProviderProps
): JSX.Element;
```

### F.4 In-Flight Sync Indicator — `packages/ui/src/sync-indicator/types.ts`

```typescript
// packages/ui/src/sync-indicator/types.ts

/**
 * The four sync surfaces that consume <InFlightSyncIndicator>.
 * Matches arch doc §16.13 surface-specific count semantics.
 */
export type SyncSurface =
  | 'dispatch'       // FE-B4: Dispatch board move optimistic locking
  | 'mobile-sync'    // FE-B7: Mobile offline queue → server sync
  | 'calendar'       // FE-B8: Calendar conflict pending changes
  | 'quickbooks';    // FE-B9: QuickBooks bilateral sync pending

export type SyncState =
  | 'idle'           // No active sync; 0 pending operations
  | 'synced-pending' // Sync complete but N>0 operations queued (will sync in ~Xm)
  | 'syncing'        // Active sync in progress
  | 'error'          // Last sync attempt failed; N pending still queued
  | 'paused';        // Sync explicitly paused (e.g., user paused QB sync)

export interface InFlightSyncIndicatorProps {
  surface: SyncSurface;
  /**
   * Number of operations pending sync.
   * FE-B1: passed as prop directly.
   * FE-B15: supplied by useInFlightSyncStatus(surface) data hook.
   */
  pendingCount?: number;
  /**
   * Last successful sync timestamp.
   * FE-B1: passed as prop directly.
   * FE-B15: supplied by data hook.
   */
  lastSyncedAt?: Date | null;
  /**
   * Current sync state.
   * FE-B1: passed as prop directly; defaults to 'idle'.
   * FE-B15: derived from sync_status backend service.
   */
  state?: SyncState;
  /**
   * Pending-count threshold above which the indicator dot turns amber.
   * Default: 5. Per §16.13 tenant_sync_indicator_pending_amber_threshold.
   * FE-B15 reads this from settings; FE-B1 consumers pass it directly.
   */
  amberThreshold?: number;
  /**
   * Optional handler for manual sync trigger.
   * When provided, renders "Sync now" link in synced-pending state.
   * Not available for 'mobile-sync' (mobile sync is OS-scheduled foreground only).
   */
  onManualSync?: () => void;
  /**
   * Render a compact version (dot + count only, no text).
   * Used in header nav bar slots where space is constrained.
   */
  compact?: boolean;
  /**
   * Optional navigate-to-resolution-surface callback.
   * FE-B1 skeleton ignores this; FE-B15 wires it per surface:
   *   dispatch → /schedule
   *   calendar → /settings/integrations/calendar/conflicts
   *   quickbooks → /settings/integrations/quickbooks/conflicts
   *   mobile-sync → pending-changes drawer (mobile)
   */
  onResolve?: () => void;
  testID?: string;
}
```

### F.5 Email Branding Preview Skeleton — `packages/ui/src/email-branding-preview/types.ts`

```typescript
// packages/ui/src/email-branding-preview/types.ts

/** Tenant branding data consumed by the preview pane. */
export interface TenantBranding {
  /** Primary accent color (hex string from tenant settings) */
  primaryColorHex: string;
  /** Logo URL (S3 signed URL or null if not yet uploaded) */
  logoUrl: string | null;
  /** Display name for emails (defaults to tenant company name) */
  senderName: string;
  /** Reply-to email address */
  replyToEmail: string;
}

export interface EmailBrandingPreviewProps {
  /**
   * Tenant branding to preview.
   * FE-B1 skeleton: renders placeholder layout.
   * FE-B14 fleshed: renders actual email preview using branded template.
   */
  branding: TenantBranding | null;
  /**
   * Which email template to preview.
   * FE-B1 skeleton: ignored (shows placeholder).
   * FE-B14 fleshed: renders the actual template.
   */
  templateKey?: string;
  /** Width of the preview pane in pixels (default: 560 — standard email width) */
  previewWidth?: number;
  className?: string;
}
```

### F.6 MFA Enrollment Wizard Skeleton — `packages/ui/src/mfa-enrollment-wizard/types.ts`

```typescript
// packages/ui/src/mfa-enrollment-wizard/types.ts

export type MFAEnrollmentPath =
  | 'totp'   // Authenticator app (TOTP) — QR code scan
  | 'sms'    // SMS one-time code to phone number
  | 'email'; // Email one-time code to account email

export type MFAEnrollmentStep =
  | 'method-select'  // Choose totp / sms / email
  | 'setup'          // Method-specific setup (QR scan, phone entry, etc.)
  | 'verify'         // Enter the code to confirm enrollment
  | 'complete';      // Enrollment confirmed; wizard closes

export interface MFAEnrollmentWizardProps {
  /**
   * Enrollment path preselected (e.g., tenant policy requires TOTP).
   * If not provided, user sees method-select step first.
   */
  forcedPath?: MFAEnrollmentPath;
  /**
   * Allowed enrollment paths.
   * Default: all three paths allowed.
   */
  allowedPaths?: MFAEnrollmentPath[];
  /**
   * Called when enrollment completes successfully.
   */
  onComplete: (enrolledPath: MFAEnrollmentPath) => void;
  /**
   * Called when user cancels or closes the wizard.
   * Wizards rendered during forced-enrollment flows should not provide
   * an escape — in that case, do not render a Cancel button and pass
   * a no-op or redirect handler here.
   */
  onCancel: () => void;
  /**
   * Days remaining in MFA enrollment grace period.
   * When > 0, shows "You have N days to complete enrollment" banner.
   * When 0, shows "Enrollment required today" urgent banner.
   * When undefined, no grace period UI is shown.
   */
  gracePeriodDaysRemaining?: number;
  /**
   * User's current step (for external state management).
   * If not provided, wizard manages step state internally.
   */
  currentStep?: MFAEnrollmentStep;
  testID?: string;
}
```

### F.7 Tier Picker Card Skeleton — `packages/ui/src/tier-picker-card/types.ts`

```typescript
// packages/ui/src/tier-picker-card/types.ts

export interface TierFeature {
  label: string;
  /** When true, feature is included. When false, feature is grayed-out with strikethrough. */
  included: boolean;
  /** Optional callout (e.g., "Unlimited", "Up to 5") */
  callout?: string;
}

export type TierName = 'trial' | 'starter' | 'growth' | 'pro';

export interface TierPickerCardProps {
  tierName: TierName;
  /** Display name (e.g., "Starter", "Growth Plan") */
  displayName: string;
  /** Monthly price in cents (e.g., 14900 = $149) */
  monthlyPriceCents: number;
  /** Annual price in cents, if applicable */
  annualPriceCents?: number;
  /** Array of feature line items */
  features: TierFeature[];
  /**
   * When true, renders the card with a highlighted/featured treatment.
   * Typically used for the "trial" tier card.
   */
  isFeatured?: boolean;
  /**
   * When true, this card is the currently selected tier.
   * Applies a border + checkmark treatment.
   */
  isSelected?: boolean;
  onSelect: (tierName: TierName) => void;
  /** CTA label override (default: "Select {displayName}") */
  ctaLabel?: string;
  testID?: string;
  className?: string;
}
```

### F.8 `packages/ui/src/index.ts` — Updated Barrel Export

```typescript
// packages/ui/src/index.ts
// Public API for @pilot/ui — every shared component exported here

// ── FE-B0 Exports (existing) ──────────────────────────────────────────────────
export { AuthProvider, RequireAuth } from './auth';
export type { AuthProviderProps, RequireAuthProps, AuthContextValue, PilotUser, PilotRole } from './auth';
export { useAuth } from './auth';
export { RoleGate, useRequiresPermission } from './role-gate';
export type { RoleGateProps } from './role-gate';
export { ROLE_PERMISSION_MAP } from './role-gate';
export type { PermissionKey } from './role-gate';

// ── FE-B1 Exports (new) ───────────────────────────────────────────────────────

// States catalog
export { EmptyState } from './states';
export { LoadingState } from './states';
export { ErrorState } from './states';
export { FirstTimeUserState } from './states';
export type {
  EmptyStateProps, EmptyStateType, EmptyStateIllustration,
  LoadingStateProps, LoadingStateType,
  ErrorStateProps, ErrorStateType,
  FirstTimeUserStateProps, FTUSurface,
  FTU_DEFAULTS,
} from './states/types';

// Notification Banner
export { NotificationBanner } from './notification-banner';
export { useNotificationQueue, NotificationQueueProvider } from './notification-banner';
export type {
  NotificationItem, NotificationSeverity, NotificationQueueContextValue,
  NotificationBannerWebProps, NotificationBannerMobileProps,
  NotificationQueueProviderProps,
} from './notification-banner/types';

// In-Flight Sync Indicator (skeleton)
export { InFlightSyncIndicator } from './sync-indicator';
export type {
  InFlightSyncIndicatorProps, SyncSurface, SyncState,
} from './sync-indicator/types';

// Email Branding Preview (skeleton)
export { EmailBrandingPreview } from './email-branding-preview';
export type { EmailBrandingPreviewProps, TenantBranding } from './email-branding-preview/types';

// MFA Enrollment Wizard (skeleton)
export { MFAEnrollmentWizard } from './mfa-enrollment-wizard';
export type {
  MFAEnrollmentWizardProps, MFAEnrollmentPath, MFAEnrollmentStep,
} from './mfa-enrollment-wizard/types';

// Tier Picker Card (skeleton)
export { TierPickerCard } from './tier-picker-card';
export type {
  TierPickerCardProps, TierFeature, TierName,
} from './tier-picker-card/types';
```

### F.9 `packages/ui/package.json` — Updated Exports Map

```json
{
  "name": "@pilot/ui",
  "exports": {
    "./tokens": "./src/tokens.ts",
    "./tailwind.preset": "./tailwind.preset.ts",
    "./styles/globals.css": "./src/styles/globals.css",
    "./auth": "./src/auth/index.ts",
    "./role-gate": "./src/role-gate/index.ts",
    "./hooks": "./src/hooks/index.ts",
    "./states": "./src/states/index.ts",
    "./notification-banner": "./src/notification-banner/index.ts",
    "./sync-indicator": "./src/sync-indicator/index.ts",
    "./email-branding-preview": "./src/email-branding-preview/index.ts",
    "./mfa-enrollment-wizard": "./src/mfa-enrollment-wizard/index.ts",
    "./tier-picker-card": "./src/tier-picker-card/index.ts",
    "./*": "./src/*.tsx"
  }
}
```

---

## G. Open Questions Resolved

### G-1: States Catalog Component API — Discriminated Union ✅ CONFIRMED

**Decision**: Single component per state category with discriminated union `type` prop.
```tsx
<EmptyState type="no-data" />
<LoadingState type="full-page" />
<ErrorState type="network" onRetry={refetch} />
<FirstTimeUserState type="quotes" />
```

**Rationale for discriminated union over separate components (e.g., `<NoDataState />`)**:
1. Consumers import one name, not five — less cognitive overhead
2. Bundle tree-shaking works per discriminant value (only referenced variants included)
3. Easier to enforce visual consistency across variants — one component manages them all
4. Matches the impl plan recommendation exactly (§6 FE-B1 Key Architectural Patterns)
5. Discriminated union `type` prop means TypeScript narrows to the exact variant interface

**Override rejected**: No reason to deviate from the impl plan recommendation.

---

### G-2: Web + Mobile Variant Strategy ✅ RESOLVED

**Decision**: Explicit `web/` and `mobile/` subfolders with a shared `types.ts` for all components that need platform-specific rendering. Pure platform-agnostic components (hooks, types) live at the category root.

Components with **web + mobile variants** (fundamentally different rendering primitives):
- `states/web/` + `states/mobile/` — shadcn/ui Skeleton for web; Gluestack primitives for mobile
- `notification-banner/web/` + `notification-banner/mobile/` — Portal-based for web; Gluestack Toast for mobile
- `sync-indicator/web/` + `sync-indicator/mobile/` — different layout contexts
- `mfa-enrollment-wizard/web/` + `mfa-enrollment-wizard/mobile/` — complex form vs mobile-optimized wizard

Components that are **web-only** (feature not surfaced on mobile per Settings IA three-question rule):
- `email-branding-preview/` — email branding is a settings surface, web only
- `tier-picker-card/` — signup wizard is web-only; mobile setup phase is a separate screen

**`states/index.ts` platform resolution**: The states barrel uses a package.json conditional exports pattern (browser vs react-native) to resolve platform variants:
```json
// In packages/ui/package.json, under the ./states export:
"./states": {
  "react-native": "./src/states/mobile/index.ts",
  "default": "./src/states/web/index.ts"
}
```
This allows both web and mobile to import `from '@pilot/ui/states'` and receive the correct platform variant automatically.

---

### G-3: NotificationBanner Queue Behavior ✅ RESOLVED

**Queue behavior**: **Stack** (FIFO queue, not replace). Multiple banners fire in parallel routinely (e.g., quote approved + sync completed + new message). Replacing would cause silent information loss.

**Maximum visible**: 3 banners stacked. When queue exceeds 3, the oldest is auto-dismissed to make room. This prevents the screen from becoming a wall of toasts.

**Auto-dismiss timing**:
- `info`, `success`, `warning`: 6,000ms (6s) — per impl plan spec
- `error`: 12,000ms (12s) — per impl plan spec
- `critical`: **No auto-dismiss** — user must explicitly click × to dismiss. This handles critical sync errors, security notifications, and forced-action scenarios where silent dismissal would cause user harm.

**Portal vs in-tree**: **Portal** (web). The banner container renders via `ReactDOM.createPortal()` into a `#notification-root` div inserted at the bottom of `apps/web/src/app/layout.tsx`. This ensures banners render above all page content (including modals) regardless of z-index stacking contexts. Mobile uses Gluestack's native Toast overlay system.

**`#notification-root` placement**: The `<NotificationPortal />` component (A.2 above) creates this DOM node. It must be rendered in the `(authed)/layout.tsx` NOT in the root `layout.tsx`, because guest/public surfaces (public quote/invoice pages in FE-B14) should not have the notification queue.

---

### G-4: InFlightSyncIndicator Skeleton API ✅ RESOLVED

**Props locked in FE-B1** (see §F.4 for full interface):
- `surface: SyncSurface` — required; drives the "resolve here" navigation target in FE-B15
- `pendingCount?: number` — optional in FE-B1 (no data hook yet); required in FE-B15 runtime
- `lastSyncedAt?: Date | null` — optional in FE-B1
- `state?: SyncState` — optional; defaults to `'idle'`
- `amberThreshold?: number` — defaults to 5 per §16.13
- `onManualSync?: () => void` — optional; renders "Sync now" link when provided
- `compact?: boolean` — for constrained header slots
- `onResolve?: () => void` — wired in FE-B15; skeleton ignores

**FE-B1 skeleton render**: A small `<div>` with a colored dot and text string displaying the current state. No animations, no hover detail. The skeleton is functional enough for FE-B4 to compose it into the dispatch board header.

**What FE-B15 adds**: The `useInFlightSyncStatus(surface)` data hook that polls/SSE-subscribes to `GET /api/v1/sync/status?surface={surface}` (BE-B15/A79) and feeds the live values. FE-B15 also adds hover/tap detail panel, pending-item list, animations per the §16.13 spec, and wires `onResolve` to the correct route per surface.

---

### G-5: Skeleton Component Depth ✅ RESOLVED

**`<EmailBrandingPreview>` (FE-B1 depth)**:
- ✅ Props interface locked (see §F.5)
- ✅ Outer container layout: a `<div className="email-branding-preview" data-testid="email-branding-preview">` with a branded border, a "Email Preview" heading, and a placeholder "Template preview will appear here" message
- ✅ Renders when `branding` is null (shows shimmer placeholder)
- ❌ No actual template rendering (FE-B14 concern)

**`<MFAEnrollmentWizard>` (FE-B1 depth)**:
- ✅ Props interface and step enum locked (see §F.6)
- ✅ Outer shell: a modal/full-page wrapper with a `currentStep` display (`method-select` → `setup` → `verify` → `complete`)
- ✅ Step indicator component (breadcrumb dots showing progress)
- ✅ Renders each step as a placeholder panel: "TOTP setup will render here"
- ❌ No actual QR code generation, no SMS code sending, no Cognito MFA API calls (FE-B12 concern)

**`<TierPickerCard>` (FE-B1 depth)**:
- ✅ Props interface locked (see §F.7)
- ✅ Full card layout structure: tier name heading, price display, feature list (renders from `features` prop with ✓/✗ icons), CTA button with `onSelect` wired
- ✅ `isFeatured` and `isSelected` visual treatments applied (this is visual styling, not data-fetching)
- ❌ No Stripe price ID lookup, no payment intent (FE-B13 concern)

**Rationale**: The `<TierPickerCard>` gets deeper treatment because its layout is pure visual composition from passed props — there is no async concern. The card can be visually complete in FE-B1 and FE-B13 simply wires the surrounding signup wizard logic. `<MFAEnrollmentWizard>` and `<EmailBrandingPreview>` have deeper async dependencies that would force stub implementations, so those get structural skeletons only.

---

### G-6: ESLint Rule Promotion — `warn` → `error` ✅ RESOLVED

**Mechanism** (at FE-B1 close, after all components pass lint):

**Change 1**: `packages/eslint-config/rules/no-hardcoded-design-values.ts`
```typescript
// Change severity from 'warn' to 'error':
// Before:
severity: 'warn',
// After:
severity: 'error',
```

**Change 2**: Verify `packages/eslint-config/index.js` (or `eslint.config.mjs` depending on format):
```javascript
// Confirm rule is active at 'error' level:
'pilot/no-hardcoded-design-values': 'error',  // was 'warn'
```

**CI gate**: `pnpm lint --max-warnings 0` is already in the CI pipeline (per FE-B0 batch gate). With severity promoted to `error`, any violation now fails the lint command outright, not just the `--max-warnings` check. This is the cleanest enforcement mechanism.

**Pre-promotion verification**: Before changing severity, run `pnpm lint` across the entire `frontend/` workspace and confirm the current output is zero warnings. All FE-B0 and FE-B1 components must pass at zero warnings BEFORE the rule is promoted. If any FE-B1 component triggers a warning during development, it must be fixed using Pass 1 tokens before the batch completion gate.

**Effect**: From FE-B2 onward, any PR that introduces a hardcoded hex code, magic pixel value outside the 4px spacing grid, or raw RGB value will fail CI immediately. This is the "lock the discipline early" principle from the impl plan.

---

### G-7: FTU Variant Content Source ✅ RESOLVED

**Source**: Pass 4 Tier 3 #9 spec (referenced in impl plan). The detailed per-surface copy is embedded as **defaults** in `FTU_DEFAULTS` constant in `packages/ui/src/states/types.ts` (see §F.1). The spec's copy is transcribed into the defaults at implementation time.

**Why in `types.ts`, not a separate content file**: The `types.ts` location makes the defaults immediately adjacent to the type definitions they apply to. Any future copy iteration is a one-file change that's easy to grep for. A separate `content.ts` would create an extra lookup hop without meaningful benefit at this scale.

**Why parameterized** (props override the defaults): The defaults encode the Pass 4 Tier 3 #9 spec copy exactly. However, some surfaces that consume `<FirstTimeUserState>` may have context-specific variations (e.g., the `quotes` FTU for a tenant with voice quotes enabled vs. one without). Props overrides allow per-surface customization without forking the component.

**Deep-link targets**: `ctaPath` values in `FTU_DEFAULTS` are static route paths. For deep-links that require dynamic parameters (e.g., "Open the first quote you received"), the consuming surface passes `onCta` as a handler rather than relying on `ctaPath`.

**Mobile FTU content**: Mobile renders only 3 of the 8 FTU surfaces (`dashboard`, `schedule`, `customers`). The mobile component uses the same `FTU_DEFAULTS` content for these three; the remaining 5 return `null` on mobile.

---

## H. External Dependency Status

| Dependency | Blocks | Mock Strategy | Status | Tom Action Required |
|:---|:---|:---|:---|:---|
| **AWS Cognito user pool** | `<MFAEnrollmentWizard>` full implementation (FE-B12) | Skeleton renders structural placeholder with no Cognito calls | ⚠️ Not yet provisioned — `MockAuthProvider` active | Provision before FE-B12 production delivery; FE-B1 unblocked |
| **BE-B10/A57 SSE notifications endpoint** | `useNotificationQueue()` SSE subscription | `addNotification()` programmatic injection for dev + tests; MSW handler created in FE-B12 | ⏳ Not yet built (BE-B10 batch) | None before FE-B12 |
| **BE-B15/A79 sync status endpoint** | `<InFlightSyncIndicator>` live data | Skeleton accepts props directly; `useInFlightSyncStatus()` data hook created in FE-B15 | ⏳ Not yet built (BE-B15 batch) | None before FE-B15 |
| **Pass 4 Tier 3 #9 spec doc** | FTU copy accuracy | `FTU_DEFAULTS` in `types.ts` uses best-available copy from impl plan descriptions | ⚠️ Spec not read in this session | Tom: confirm `FTU_DEFAULTS` copy matches Tier 3 #9 spec before FE-B1 close; update if copy differs |
| **`@gluestack-ui/themed` Toast API** | `NotificationBannerMobile` | `@gluestack-ui/themed` installed in FE-B0; Toast API available | ✅ Available | No action |
| **`react-dom` Portal** | `NotificationPortal` (web) | `react-dom` is a React dependency, already installed | ✅ Available | No action |

**New npm packages required in FE-B1**: None. All rendering is accomplished with:
- shadcn/ui primitives (web) — already available
- Gluestack-UI primitives (mobile) — installed in FE-B0
- React core APIs (Portal, Context, Zustand for queue state) — installed in FE-B0
- No new third-party dependencies are introduced in FE-B1

---

## I. Test Plan

**Test targets per impl plan §5.5**:
- Unit tests: **80+ minimum** (FE-B1 batch target)
- Integration tests: **12+ minimum**
- E2E tests: **0** (component library; no end-to-end user flow involving only shared components — first e2e in FE-B2)

### I.1 Unit Test Files — `packages/ui/src/{category}/__tests__/` (co-located)

#### States Catalog

| Test File | Component | Key Scenarios | Est. Count |
|:---|:---|:---|:---:|
| `states/web/EmptyState.test.tsx` | `EmptyState` (web) | (1) All 5 types render with default content; (2) `title`/`description` overrides respected; (3) `onCta` fires on button click; (4) `illustration` prop renders correct art; (5) ARIA: rendered region has `role="region"` with meaningful label; (6) No hardcoded colors (ESLint mock) | 8 |
| `states/mobile/EmptyState.test.tsx` | `EmptyState` (mobile) | Same scenarios with React Native testing library | 8 |
| `states/web/LoadingState.test.tsx` | `LoadingState` (web) | (1) `full-page` renders N skeleton rows per `skeletonRows` prop; (2) `inline` renders spinner with `aria-live="polite"` region; (3) `optimistic` wraps children with pulse animation; (4) default `skeletonRows=4`; (5) `label` prop updates `aria-label` on spinner | 6 |
| `states/mobile/LoadingState.test.tsx` | `LoadingState` (mobile) | Same scenarios for React Native | 6 |
| `states/web/ErrorState.test.tsx` | `ErrorState` (web) | (1) All 4 types render appropriate icon + default copy; (2) `onRetry` CTA renders for `network` and `server`; (3) `onRetry` does not render for `validation` or `permission`; (4) `fieldErrors` map renders inline for `validation` type; (5) `onContactSupport` renders for `server` type; (6) ARIA `role="alert"` on error container | 8 |
| `states/mobile/ErrorState.test.tsx` | `ErrorState` (mobile) | Same scenarios for React Native | 8 |
| `states/web/FirstTimeUserState.test.tsx` | `FirstTimeUserState` (web) | (1) All 8 types render with `FTU_DEFAULTS` content; (2) `headingText` override replaces default heading; (3) `onCta` handler fires on CTA button click; (4) `ctaLabel` override replaces default label; (5) ARIA: heading is an `<h2>`; (6) `secondaryCtaLabel` renders second button | 7 |
| `states/mobile/FirstTimeUserState.test.tsx` | `FirstTimeUserState` (mobile) | (1) `dashboard`, `schedule`, `customers` types render; (2) `invoices`, `reports`, `comms`, `settings`, `quotes` types return null on mobile; (3) Same override prop scenarios | 6 |
| `states/types.test.ts` | `FTU_DEFAULTS` | (1) All 8 `FTUSurface` values have entries in `FTU_DEFAULTS`; (2) Each entry has non-empty `heading`, `body`, `ctaLabel`, `ctaPath` | 3 |

**States subtotal**: ~60 unit tests

#### Notification Banner

| Test File | Component / Hook | Key Scenarios | Est. Count |
|:---|:---|:---|:---:|
| `notification-banner/web/NotificationBanner.test.tsx` | `NotificationBanner` (web) | (1) Renders `title` and `detail`; (2) ARIA `role="alert"` present; (3) `info/success/warning` auto-dismiss at 6,000ms via fake timers; (4) `error` auto-dismiss at 12,000ms; (5) `critical` does NOT auto-dismiss after 30,000ms; (6) `onDismiss` fires on × button click; (7) `onNavigate` fires on banner click when `deepLinkTarget` provided; (8) Severity → correct token-based color class applied; (9) `detail` text rendered when provided; (10) Banner absent from DOM after dismiss | 10 |
| `notification-banner/mobile/NotificationBanner.test.tsx` | `NotificationBanner` (mobile) | Same 10 scenarios using `@testing-library/react-native` | 10 |
| `notification-banner/useNotificationQueue.test.ts` | `useNotificationQueue` | (1) `addNotification` adds to queue; (2) Auto-generated `id` deduplicated (same id → replace, not duplicate); (3) Queue max-3 cap: adding 4th dismisses oldest; (4) `dismissNotification(id)` removes by id; (5) `dismissAll` clears queue; (6) Queue persists across hook re-renders | 7 |
| `notification-banner/NotificationQueueProvider.test.tsx` | `NotificationQueueProvider` | (1) Context value accessible via `useNotificationQueue()` in children; (2) `maxVisible` prop controls queue cap; (3) Throws error when `useNotificationQueue` called outside provider | 3 |

**Notification Banner subtotal**: ~30 unit tests

#### Sync Indicator Skeleton

| Test File | Component | Key Scenarios | Est. Count |
|:---|:---|:---|:---:|
| `sync-indicator/web/InFlightSyncIndicator.test.tsx` | `InFlightSyncIndicator` (web) | (1) `surface` prop renders surface name; (2) `state="idle"` → green dot; (3) `state="syncing"` → amber pulsing dot; (4) `state="error"` → red dot; (5) `state="paused"` → neutral dot; (6) `pendingCount=0` no badge; (7) `pendingCount=3` badge shows `3`; (8) `pendingCount=6` (above default threshold 5) amber indicator; (9) `amberThreshold=10` overrides: count of 6 stays green; (10) `onManualSync` provided → "Sync now" link renders; (11) `compact` mode: only dot + count, no text; (12) `testID` propagated | 12 |
| `sync-indicator/mobile/InFlightSyncIndicator.test.tsx` | `InFlightSyncIndicator` (mobile) | Same 12 scenarios for React Native | 12 |

**Sync Indicator subtotal**: ~24 unit tests

#### Skeleton Components

| Test File | Component | Key Scenarios | Est. Count |
|:---|:---|:---|:---:|
| `email-branding-preview/EmailBrandingPreview.test.tsx` | `EmailBrandingPreview` | (1) Renders `data-testid="email-branding-preview"`; (2) Shows placeholder when `branding=null`; (3) Shows sender name when `branding` provided; (4) Logo `<img>` renders when `logoUrl` present; (5) `previewWidth` applied | 5 |
| `mfa-enrollment-wizard/web/MFAEnrollmentWizard.test.tsx` | `MFAEnrollmentWizard` (web) | (1) `method-select` step renders 3 path options; (2) `forcedPath="totp"` skips method-select; (3) `gracePeriodDaysRemaining=3` shows countdown banner; (4) `gracePeriodDaysRemaining=0` shows urgent banner; (5) `onCancel` fires on cancel button; (6) Step indicator shows correct active step | 7 |
| `tier-picker-card/TierPickerCard.test.tsx` | `TierPickerCard` | (1) Renders `displayName`, `monthlyPriceCents` formatted as `$X/mo`; (2) `features` list renders with ✓/✗ per `included`; (3) `isSelected=true` applies selected border; (4) `isFeatured=true` applies highlight treatment; (5) `onSelect(tierName)` fires on CTA button click; (6) `ctaLabel` override respected | 7 |

**Skeleton subtotal**: ~19 unit tests

**Total unit test estimate**: 60 + 30 + 24 + 19 = **~133 unit tests**. Exceeds the 80+ minimum target.

---

### I.2 Integration Test Files — `packages/ui/src/` + `apps/{web|mobile}/__tests__/batch_fe_b1/`

| Test File | Surface | Scenarios | Est. Count |
|:---|:---|:---|:---:|
| `apps/web/__tests__/batch_fe_b1/states-in-route-layout.integration.test.tsx` | Web route layout | (1) `<EmptyState>` renders inside `(authed)/layout.tsx` without layout breakage; (2) `<LoadingState type="full-page">` renders as full-viewport; (3) `<ErrorState>` inside `<RoleGate>` — permission-denied route renders ErrorState permission type; (4) All 8 FTU variants render inside real route context without crashes | 4 |
| `apps/mobile/__tests__/batch_fe_b1/states-in-tab-layout.integration.test.tsx` | Mobile tab layout | (1) `<EmptyState>` renders inside Jobs tab layout; (2) `<FirstTimeUserState type="schedule">` renders in Jobs tab; (3) `<FirstTimeUserState type="invoices">` returns null in mobile context without crashing | 3 |
| `apps/web/__tests__/batch_fe_b1/notification-queue.integration.test.tsx` | `NotificationQueueProvider` + web layout | (1) Single `addNotification` shows banner in DOM; (2) 4 simultaneous notifications → only 3 visible, oldest dismissed; (3) Click `deepLinkTarget` banner calls `onNavigate` with correct path; (4) `error` severity banner persists for full 12s (fake timers); (5) Portal renders outside of component tree root (axe-core DOM check) | 5 |
| `apps/mobile/__tests__/batch_fe_b1/notification-queue-mobile.integration.test.tsx` | Mobile notification queue | (1) Mobile banner renders using Gluestack Toast; (2) Auto-dismiss at correct timing; (3) Queue stacks correctly on mobile | 3 |
| `apps/web/__tests__/batch_fe_b1/sync-indicator-in-layout.integration.test.tsx` | `InFlightSyncIndicator` skeleton in web layout | (1) Renders in a header nav slot without layout breakage; (2) All `SyncSurface` values render without crashes; (3) `state="syncing"` prop causes amber dot; (4) `compact` mode fits in constrained header | 4 |
| `apps/web/__tests__/batch_fe_b1/ftu-variants-accessibility.integration.test.tsx` | FTU variants a11y | (1) axe-core zero violations for all 8 FTU variants on web; (2) Heading hierarchy correct (FTU heading is `<h2>` inside a `<main>`); (3) CTA button is keyboard-focusable with visible focus indicator | 3 |
| `apps/web/__tests__/batch_fe_b1/tier-picker-card.integration.test.tsx` | `TierPickerCard` selection flow | (1) Renders a 3-card tier comparison layout; (2) Clicking a card calls `onSelect` and that card shows `isSelected` treatment; (3) axe-core zero violations; (4) Trial card `isFeatured` renders highlight treatment | 4 |

**Total integration test estimate**: ~26 tests. Exceeds the 12+ minimum target.

---

### I.3 E2E Tests

**E2E target for FE-B1: 0** (per impl plan §5.5 — no end-to-end user flow involving only shared components).

First e2e tests: **FE-B2** (`apps/web/e2e/batch_fe_b2/login.e2e.spec.ts`), which will implicitly exercise the states catalog (`LoadingState type="inline"` on the login form submit button).

---

### I.4 Accessibility Audit Checkpoints

All FE-B1 components must pass axe-core with **zero violations** before batch close. Specific ARIA requirements:

| Component | Required ARIA | Verified By |
|:---|:---|:---|
| `<ErrorState>` | `role="alert"` on error container; `aria-live="assertive"` for inline validation | Unit test + integration test |
| `<LoadingState type="inline">` | `aria-live="polite"` region; spinner has `aria-label` | Unit test |
| `<LoadingState type="full-page">` | `aria-busy="true"` on root container | Unit test |
| `<EmptyState>` | Heading is `<h2>` (not `<h1>` — page already has an h1); CTA button has accessible name | Unit test |
| `<FirstTimeUserState>` | `<h2>` heading; CTA accessible name from `ctaLabel`; secondary CTA accessible | Unit test |
| `<NotificationBanner>` (web) | `role="alert"` on banner; `aria-live="polite"` for info/success/warning; `aria-live="assertive"` for error/critical | Unit test |
| `<NotificationBanner>` (mobile) | `accessibilityRole="alert"` on root view; `accessibilityLabel` includes title | Unit test |
| `<TierPickerCard>` | Radio-group-like pattern: `role="radio"` on card + `aria-checked` for selected state; keyboard-focusable | Unit test |
| `<MFAEnrollmentWizard>` | Step indicator accessible (e.g., `aria-current="step"`); form fields labeled | Unit test |
| All mobile interactive elements | `accessibilityLabel` + `testID` on all buttons, links | Unit test |

### I.5 Token Validation Gate

At FE-B1 close, run the full validation sequence:

```bash
# Verify zero lint violations (includes no-hardcoded-design-values at ERROR severity):
pnpm lint

# Verify zero TypeScript errors across all packages:
pnpm typecheck

# Verify web build compiles:
pnpm --filter web build

# Verify mobile build compiles:
pnpm --filter mobile tsc --noEmit

# Verify marketing app not broken:
pnpm --filter marketing build

# Run full test suite:
pnpm test
```

All commands must exit 0. If any fail, the batch is not complete.

---

## Appendix: File Creation Summary

**Net-new files created in FE-B1**:

```
packages/ui/src/
├── states/
│   ├── types.ts
│   ├── web/
│   │   ├── EmptyState.tsx
│   │   ├── EmptyState.test.tsx
│   │   ├── LoadingState.tsx
│   │   ├── LoadingState.test.tsx
│   │   ├── ErrorState.tsx
│   │   ├── ErrorState.test.tsx
│   │   ├── FirstTimeUserState.tsx
│   │   └── FirstTimeUserState.test.tsx
│   ├── mobile/
│   │   ├── EmptyState.tsx
│   │   ├── EmptyState.test.tsx
│   │   ├── LoadingState.tsx
│   │   ├── LoadingState.test.tsx
│   │   ├── ErrorState.tsx
│   │   ├── ErrorState.test.tsx
│   │   ├── FirstTimeUserState.tsx
│   │   └── FirstTimeUserState.test.tsx
│   └── index.ts
│
├── notification-banner/
│   ├── types.ts
│   ├── useNotificationQueue.ts
│   ├── useNotificationQueue.test.ts
│   ├── NotificationQueueProvider.tsx
│   ├── NotificationQueueProvider.test.tsx
│   ├── web/
│   │   ├── NotificationBanner.tsx
│   │   ├── NotificationBanner.test.tsx
│   │   └── NotificationPortal.tsx
│   ├── mobile/
│   │   ├── NotificationBanner.tsx
│   │   └── NotificationBanner.test.tsx
│   └── index.ts
│
├── sync-indicator/
│   ├── types.ts
│   ├── web/
│   │   ├── InFlightSyncIndicator.tsx
│   │   └── InFlightSyncIndicator.test.tsx
│   ├── mobile/
│   │   ├── InFlightSyncIndicator.tsx
│   │   └── InFlightSyncIndicator.test.tsx
│   └── index.ts
│
├── email-branding-preview/
│   ├── types.ts
│   ├── EmailBrandingPreview.tsx
│   ├── EmailBrandingPreview.test.tsx
│   └── index.ts
│
├── mfa-enrollment-wizard/
│   ├── types.ts
│   ├── web/
│   │   ├── MFAEnrollmentWizard.tsx
│   │   └── MFAEnrollmentWizard.test.tsx
│   ├── mobile/
│   │   └── MFAEnrollmentWizard.tsx
│   └── index.ts
│
├── tier-picker-card/
│   ├── types.ts
│   ├── TierPickerCard.tsx
│   ├── TierPickerCard.test.tsx
│   └── index.ts
│
└── index.ts                           (MODIFIED — adds all FE-B1 exports)

apps/web/src/
└── app/
    ├── (authed)/
    │   └── layout.tsx                 (MODIFIED — add NotificationPortal + NotificationQueueProvider)
    └── __tests__/
        └── batch_fe_b1/
            ├── states-in-route-layout.integration.test.tsx
            ├── notification-queue.integration.test.tsx
            ├── sync-indicator-in-layout.integration.test.tsx
            ├── ftu-variants-accessibility.integration.test.tsx
            └── tier-picker-card.integration.test.tsx

apps/mobile/
└── app/
    ├── _layout.tsx                    (MODIFIED — add NotificationQueueProvider)
    └── __tests__/
        └── batch_fe_b1/
            ├── states-in-tab-layout.integration.test.tsx
            └── notification-queue-mobile.integration.test.tsx

packages/
├── ui/
│   └── package.json                   (MODIFIED — add 6 new named exports)
└── eslint-config/
    └── rules/
        └── no-hardcoded-design-values.ts   (MODIFIED — severity warn → error)
```

**Total new files**: ~45 files
**Total modified files**: 4 files (`packages/ui/src/index.ts`, `packages/ui/package.json`, `apps/web/src/app/(authed)/layout.tsx`, `apps/mobile/app/_layout.tsx`, `packages/eslint-config/rules/no-hardcoded-design-values.ts`)

---

*Design session complete. This document is the authoritative handoff to the Pilot React Engineer for FE-B1 Phase 2 implementation. All 7 key design decisions are resolved; all 20+ component file paths and TypeScript interfaces are specified. No unresolved interaction questions remain.*

*Consult `dev-docs/architecture-design/pilot-react-engineer-methods.md` v2.1 §7 (UI Component Standards), §8 (Shared Component Catalog), and §16 (Standard Implementation Task Workflow) for implementation conventions.*
