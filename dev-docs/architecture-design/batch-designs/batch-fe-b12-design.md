# FE-B12 Batch Design — Settings Sub-Surfaces (Pass 4 Tier 2 #5, #6, #7)

**Status**: Ready for Implementation
**Date**: 2026-05-26
**Author**: Pilot Architect
**Prerequisite Batches**: FE-B0 through FE-B11 complete
**Backend Gates**: BE-B10 (A56–A58 notifications), BE-B12 (A67 voice persona), BE-B13 (A68–A71 account security)
**Gates Downstream**: FE-B13 (onboarding surfaces `MFAEnrollmentWizard` and `NotificationPreferenceMatrix` inline; onboarding confirmation screen may embed `NotificationCenterBell`)
**Test Subfolder**: `apps/{web,mobile}/__tests__/batch_fe_b12/`

---

## Prerequisite Reads Completed

| Source | Key facts extracted |
|:---|:---|
| `frontend-pass-4-tier-2-flow-5-notification-preference-center-spec.md` | 8 categories × 3 channels = 24 cells; forced-minimum push for 4 categories with user-context asymmetry (Customer activity); SSE-backed in-app banner; notification center bell with 50-item history |
| `frontend-pass-4-tier-2-flow-6-voice-persona-tone-spec.md` | Three-position enum `conservative\|balanced\|playful`; preview audio from S3 CDN (`preview_audio_urls` in response); per-user override with tenant meta-toggle `voice_persona_tone_user_override_allowed` |
| `frontend-pass-4-tier-2-flow-7-account-settings-spec.md` | Six My Account sub-pages; MFA 3-method enrollment (TOTP/SMS/Email) with force-flow + grace period; active sessions; data export async pipeline |
| `pilot-app-mvp-frontend-impl-plan.md §6 FE-B12` | 9-item execution order; test targets (80+ unit, 20+ integration, 4+ E2E); canonical use-case for `EffectiveSettingDisplay` is notification matrix |
| `backend/api/routes/notification_preferences.py` | Confirmed: `GET /api/v1/notifications/preferences` returns 24 cells each with `{category_id, channel, enabled, scope, forced_minimum, can_disable}`; `PUT /{category_id}/{channel}` returns 403 on forced-minimum push disable; bulk mute + reset endpoints present |
| `backend/api/routes/account_security.py` | A68–A71 confirmed. MFA: `enroll-start` returns `qr_code_uri+secret` (TOTP) or `destination_masked` (SMS/Email); `enroll-confirm` creates `UserMfaMethod`; `DELETE /me/mfa/methods/{method_id}` returns 409 if last method and tenant requires MFA. Data export: `POST /me/data-exports` returns `{export_id, status, requested_at}`; `GET /me/data-exports/{export_id}` for polling |
| `backend/api/routes/voice_persona.py` | `GET /api/v1/settings/voice-persona-tone` returns `{effective_tone, effective_scope, user_override, tenant_default, system_default, user_override_allowed, available_tones, preview_audio_urls}`; PUT returns 403 when tenant has disabled user overrides |
| `packages/ui/src/mfa-enrollment-wizard/types.ts` | FE-B1 skeleton props: `forcedPath?`, `allowedPaths?`, `onComplete(enrolledPath)`, `onCancel()`, `gracePeriodDaysRemaining?`, `currentStep?`, `testID?`; steps: `method-select → setup → verify → complete` |
| `packages/ui/src/hooks/useSseChannel.ts` | Locked interface: `{path, onMessage, fallbackToPollingMs?, pollFn?, enabled?, maxRetryDelayMs?, eventSourceFactory?}` → `{isConnected, isPolling, lastMessage, connectionError, disconnect, reconnect}` |
| `packages/ui/src/notification-banner/types.ts` | `NotificationItem`: `{id, severity, title, detail?, deepLinkTarget?, dismissAfterMs?}`; `AUTO_DISMISS_MS`: standard 6000 / critical 12000 |
| `packages/ui/src/setting-control/EffectiveSettingDisplay.tsx` | Three-tier stacked display: user/tenant/system rows with `activeTier`, `allowsUserOverride`, `displayMode` (`web`\|`mobile`); `onUserSave(value)` for user-layer edit |
| `packages/ui/src/index.ts` | FE-B11 exports confirmed: `SettingControl`, `EffectiveSettingDisplay`, `RevertToDefaultDialog`, `SaveOnGroupCompleteIndicator`, `SettingsSidebarSearch`, `useFormSaveStrategy` — all present. `MFAEnrollmentWizard` skeleton present. `useSseChannel` and `NotificationBanner/useNotificationQueue/NotificationPortal` present. |
| `apps/web/src/app/(authed)/settings/` | Settings shell established in FE-B11; FE-B12 slots sub-surfaces into the IA tree |

---

## Resolved Design Decisions

### Decision 1 — Notification Preference Matrix Rendering Strategy

**Decision**: The matrix renders as a **CSS grid table** at `Settings > Notifications > Preferences`: category labels as row headers, Push / Email / In-app as column headers. 24 cells arranged in 8 category rows × 3 channel columns. Each cell composes `<EffectiveSettingDisplay>` operating in a compact "cell mode" (a new optional `displayMode="cell"` prop — additive, backward-compatible).

**Forced-minimum cell render**: The `can_disable` field in the `GET /api/v1/notifications/preferences` response is the authoritative signal — the backend evaluates user-context (e.g., originating tech vs. owner) on the server side. When `can_disable === false`:
- Toggle renders with `pointer-events: none` + lock glyph
- `aria-disabled="true"` on the toggle element
- Tooltip on hover/focus: the explainer text from spec Decision 4 (e.g., "Push for Customer activity can't be turned off when you're the tech in a conversation")
- No `(locked)` annotation visible in normal view; lock icon communicates state without taking column space

**Role detection for asymmetric forced-minimum**: Entirely server-side. The matrix endpoint returns per-cell `can_disable` already computed for the requesting user's context. Frontend composes `<EffectiveSettingDisplay>` cells from the response without additional role checks.

**Customer activity asymmetric rows**: Rendered as **two separate rows** in the matrix:
- "Customer activity (you)" — `category_id = "customer_activity"` with `forced_minimum: true` on push
- "Customer activity (other techs)" — synthesized from the same `customer_activity` category but the server returns `can_disable: true` for the ambient-awareness sub-trigger
- The matrix receives the full 24-cell response + a `contextRows` metadata from the backend indicating which categories render with asymmetric dual-row treatment. FE-B12 derives the two rows client-side from the category metadata.

**Rationale**: Grid table is the most scannable layout for a matrix. Cell-mode `EffectiveSettingDisplay` avoids building a parallel 24-cell component. Server-side `can_disable` computation keeps the force-flow business logic in one place.

---

### Decision 2 — In-App Notification Banner and Bell Architecture

**Decision**: The in-app notification infrastructure has two surfaces:

**Ephemeral banner**: The existing `NotificationBanner` + `NotificationPortal` + `useNotificationQueue` from FE-B1 are the correct primitives. FE-B12 wires them to SSE by creating a new hook `useInAppNotifications` in `packages/ui/src/hooks/useInAppNotifications.ts`. This hook:
- Subscribes to `useSseChannel` with `path: '/sse/notifications'`
- On each SSE message, calls `useNotificationQueue().addNotification(...)` to push ephemeral banners
- Manages the bell's unread count (incrementing on new SSE notification, decrementing on mark-read)
- Provides `{notifications, unreadCount, markRead, markAllRead, clearAll, isConnected}` return value

There is **no new** `NotificationToast` component. The existing `NotificationBanner` is the ephemeral surface.

**Bell location**: Web — in `apps/web/src/app/(authed)/layout.tsx` header row as a slot. Mobile — in the top bar of the `(tabs)` layout. A new `NotificationCenterBell` component in `packages/ui/src/notification-center-bell/` renders the icon + badge + opens the drawer.

**Unread count derivation**: `useInAppNotifications` initializes unread count by fetching `GET /api/v1/notifications/in-app/recent?limit=50` on mount and counting entries where `read_at === null`. Subsequent SSE events increment the count. `POST /api/v1/notifications/in-app/mark-read` decrements. No separate `/unread-count` endpoint needed — the recent-50 response is sufficient for the 24-hour window.

**Notification center (bell click → drawer)**: `NotificationCenterBell` lives in `packages/ui/` (shared web + mobile). It composes:
- Bell icon with `PendingBadge` (from FE-B7) for the unread count badge
- A drawer/sheet (platform-resolved) showing the last 50 notifications from the `GET /api/v1/notifications/in-app/recent` list
- Each row: category icon + title + relative timestamp + deep link tap action
- "Mark all read" affordance at the top

**Mobile notification delivery**: On mobile, SSE is not natively supported. Per `useSseChannel` MOBILE EXTENSION NOTE, the hook falls back to `fallbackToPollingMs: 60_000` on mobile. `useInAppNotifications` passes `fallbackToPollingMs: 60_000` and a `pollFn` that re-fetches the recent-50 list on mobile.

**Rationale**: Composing existing FE-B1 primitives rather than inventing a new toast system keeps the component count down and the behavior consistent. `NotificationCenterBell` in `packages/ui/` is required because FE-B13 embeds it in the onboarding confirmation screen.

---

### Decision 3 — MFAEnrollmentWizard: Fleshing Out the FE-B1 Skeleton

**Decision**: The FE-B1 skeleton's `MFAEnrollmentWizardProps` interface is **fully backward-compatible**. FE-B12 adds implementation behind the existing props plus new **optional** props.

**New optional props added (additive, non-breaking)**:
```typescript
interface MFAEnrollmentWizardPropsExtended extends MFAEnrollmentWizardProps {
  // Force-flow mode: renders full-page without cancel affordance
  forceFlow?: boolean;
  // Whether to show recovery codes step (skip when adding 2nd/3rd method)
  showRecoveryCodes?: boolean;
  // Callback after recovery codes are acknowledged
  onRecoveryCodesAcknowledged?: () => void;
  // Pre-enrolled methods (to show as already enrolled in the method-select step)
  enrolledMethods?: MFAEnrollmentPath[];
}
```

**State machine per path** (internal to the component — external `currentStep` prop still works):

TOTP path: `method-select → setup-totp (QR code + secret display) → verify-totp (6-digit code input) → recovery-codes (if showRecoveryCodes) → complete`

SMS path: `method-select → setup-sms (phone number input, pre-filled from profile) → verify-sms (6-digit code input) → recovery-codes (if showRecoveryCodes) → complete`

Email path: `method-select → setup-email (confirm email address, read-only) → verify-email (6-digit code input) → recovery-codes (if showRecoveryCodes) → complete`

`showRecoveryCodes` defaults to `true` when no recovery codes exist yet (checked via `GET /api/v1/users/me/mfa/recovery-codes/status` on wizard mount → `unused_code_count === 0` triggers show). Defaults to `false` when adding a second/third method.

**Recovery codes step**: displays 10 plaintext codes (from `POST /api/v1/users/me/mfa/recovery-codes/generate`). "Continue" button is disabled until the user clicks "I've saved my recovery codes" checkbox. Codes render in a monospace grid. "Copy all" button.

**Force-flow integration**: When `forceFlow={true}`:
- Wizard renders as a full-page route (`/settings/my-account/security/mfa/enroll`)
- Cancel button is hidden (the `onCancel` prop receives a no-op)
- Post-login redirect via FE-B2's auth interceptor passes a `?mfa_required=1&grace_days=N` query param which the MFA wizard route reads to set `gracePeriodDaysRemaining` and `forceFlow`
- FE-B2 established the redirect; FE-B12 implements the receiving page

**Modal mode (voluntary enrollment)**: `forceFlow` is `false` or absent → wizard renders in a `<dialog>` overlay accessible via the "Add this method" button on the MFA methods sub-page.

**Grace period display**: An amber alert banner at the top of the wizard: "Enrollment required in {N} days." `gracePeriodDaysRemaining === 0` → red alert "Enrollment required today." `gracePeriodDaysRemaining >= 4` → neutral info banner. Uses `alert` token variants.

**Rationale**: Backward-compatible extension via optional props keeps FE-B13 (which imports the fleshed wizard) unblocked. Force-flow as a boolean prop rather than a separate component avoids duplication. Recovery codes show/hide logic tied to the `status` endpoint prevents redundant code generation.

---

### Decision 4 — Password Change Cross-Device Session Invalidation UX

**Decision**:

**Current-device confirmation**: On successful `POST /api/v1/auth/password` (or equivalent Cognito password change route from FE-B2), the password form:
1. Clears all three fields (current, new, confirm)
2. Calls `useNotificationQueue().addNotification()` with a success `NotificationBanner`: title "Password changed", detail "You're still signed in here, but you'll need to sign in again on other devices." — `severity: "success"`, `dismissAfterMs: 8000`

**Other-device sessions**: When the backend (BE-B13/A70) invalidates other sessions on password change, those sessions' next API request returns `401`. **FE-B2's existing session-expired interceptor** handles this — it intercepts 401 responses, clears local auth state, and redirects to `/login?reason=session_expired`. FE-B12 does NOT introduce a new mechanism; it documents that FE-B2's interceptor is the intended handler. No changes to FE-B2 are needed.

**"Sign out all other devices" toggle**: NOT added. The spec (Decision 3 of the Account Settings spec) states that other-session revocation happens automatically on password change. The disclosure text in the password form footer reads: "Changing your password will sign you out on all other devices." This is a static info annotation, not an interactive toggle.

**Password change form uses explicit Save** (per spec Decision 3): three-field form with a "Change password" submit button. Not save-on-blur. `useFormSaveStrategy({ mode: 'explicit' })` from FE-B11.

**Rationale**: Composing existing FE-B2 interceptor eliminates the need for a new session-expiry notification mechanism. The automatic revocation model (no toggle) reduces UX complexity and matches the spec intent.

---

### Decision 5 — Data Export Async Flow UX

**Decision**: **TanStack Query polling** is the correct pattern — NOT `useOptimisticMutation` from FE-B7. `useOptimisticMutation` is scoped to WatermelonDB offline writes where local state must be optimistically pre-applied before server confirmation. Data export is a purely online async operation with no local state to pre-apply.

**Pattern**:
1. User clicks "Request export" → confirmation modal → on confirm, `POST /api/v1/users/me/data-exports` → response `{export_id, status: "pending", requested_at}`
2. TanStack Query `useQuery` on `GET /api/v1/users/me/data-exports/{export_id}` with `refetchInterval: 10_000` while `status === "pending" | "processing"`
3. When `status === "ready"`, `refetchInterval` stops; download CTA renders
4. When `status === "failed"`, error state with "Try again" affordance

**Status state machine UI transitions**:
- `pending`: spinner + "Export queued..." text
- `processing`: animated progress indicator + "Building your export (~5–15 min)..."
- `ready`: success green badge + "Download" button linking to `signed_url`; expiry annotation "Link expires {date}"
- `failed`: error state + failure_reason (if present) + "Try again" button
- `expired`: neutral grey badge + "Link expired" text; `expires_at` is past

**Download URL TTL**: 7 days (from `expires_at` field). "Expired" state uses `neutral-100` background + `neutral-500` text. "Ready" state uses `success-50` background + "Download" CTA with `brand-500` color. The `signed_url` field is `null` for expired exports.

**Frequency limit (24h)**: When `POST` returns `429`, surface: "You requested an export recently. You can request another in {hours}h." The `Retry-After` header provides the wait time.

**Rationale**: Polling is the right async polling pattern for a server-side background job. The export job has no offline component; `useOptimisticMutation` would add unnecessary complexity.

---

### Decision 6 — Active Sessions List UX

**Decision**:

**"Revoke all other sessions"**: Uses a `RevertToDefaultDialog` from FE-B11 for the confirmation. The dialog pattern already handles "destructive action with explanation text + confirm/cancel" precisely, which matches this use case. Dialog copy: "Revoke all other sessions? You'll be signed out on all your other devices. Confirm?" with current-value rendering of session count.

**Optimistic remove**: On "Revoke this session" confirm, the session row is **optimistically removed** from the list immediately. TanStack Query mutates the cached session list optimistically via `queryClient.setQueryData`. On error (network failure or 404), the query is invalidated and the list refetches. This matches the FE-B7 optimistic mutation pattern for list operations.

**Signing out the current session**: The current-session row renders with `(This device)` annotation. Clicking "Sign out" on the current session shows a distinct modal: "This will sign you out now. Continue?" On confirm, `DELETE /api/v1/users/me/sessions/{session_id}` is called; on success, `useAuth().signOut()` is called from FE-B0, which redirects to `/login`.

**Device metadata per row**:
- `display_label` (e.g., "Chrome on macOS", "Pilot mobile on iPhone")
- `geolocation` (city/state approximate, or "Unknown location")
- `last_active_at` formatted as relative time ("2 days ago")
- `created_at` formatted as "Logged in: {relative time}"
- `is_current` flag → "(This device)" badge with `brand-50` background

**Rationale**: `RevertToDefaultDialog` is established for destructive confirm patterns in FE-B11. Optimistic remove is consistent with the FE-B7 pattern. Current-session sign-out composing the FE-B0 `signOut()` function ensures the auth state cleanup is handled by the canonical auth module.

---

### Decision 7 — Voice Persona Tone Preview Affordance

**Decision**: Preview **exists in MVP** — it is NOT deferred to Phase 2. The `GET /api/v1/settings/voice-persona-tone` response already includes `preview_audio_urls: { conservative: string, balanced: string, playful: string }` (confirmed from `backend/api/routes/voice_persona.py`). These are pre-generated static MP3 files served from S3/CDN.

**Web implementation**: Each of the three tone cards has a "▶ Hear preview" button. On click, an `<audio>` element (hidden; rendered once in the card's DOM) calls `.play()`. State: idle → playing → ended (button reverts to ▶). Only one preview plays at a time — clicking a second card pauses the first via a shared `currentlyPlayingRef`. Audio format: MP3, ~5–8 seconds per clip.

**Mobile implementation**: Uses `expo-av` `Audio.Sound`. Same state machine: idle → loading → playing → ended. The "▶ Hear preview" button shows a spinner during `loading` state.

**Audio component**: A new `TonePreviewButton` sub-component within the `VoicePersonaToneCard` component (feature-scoped, not shared — no other surface plays tone previews). Platform-resolved internally.

**Preview clips are universal** (same 3 files for all tenants/users). The `preview_audio_urls` dict from the API provides the CDN-served URLs. No per-user generation.

**Rationale**: The backend already provides preview URLs in the GET response — deferring preview would mean ignoring infrastructure that's already built. The UX spec (Decision 3 of Tier 2 #6) treats preview as non-negotiable for informed tone selection. Implementation is contained to the tone settings page with no shared-component complexity.

---

## A — Component Implementation Plan

### A.1 New Shared Components (`packages/ui/src/`)

These components live in `packages/ui/` and are exported from `packages/ui/src/index.ts` under a `// ── FE-B12 Exports ──` block.

#### `MFAEnrollmentWizard` (FLESHED OUT from FE-B1 skeleton)

**Location**: `packages/ui/src/mfa-enrollment-wizard/`

Replaces the FE-B1 skeleton with full enrollment logic. Web variant (`web/MFAEnrollmentWizard.tsx`) and mobile variant (`mobile/MFAEnrollmentWizard.tsx`) share the same types but platform-specific step renders.

**Interface** (backward-compatible — all new props are optional):
```typescript
interface MFAEnrollmentWizardPropsExtended extends MFAEnrollmentWizardProps {
  forceFlow?: boolean;                         // renders full-page, hides cancel
  showRecoveryCodes?: boolean;                 // auto-derived if undefined
  onRecoveryCodesAcknowledged?: () => void;
  enrolledMethods?: MFAEnrollmentPath[];       // pre-display which methods are already enrolled
}
```

**New types**:
```typescript
type MFAWizardInternalStep =
  | 'method-select'
  | 'setup-totp' | 'setup-sms' | 'setup-email'
  | 'verify-totp' | 'verify-sms' | 'verify-email'
  | 'recovery-codes'
  | 'complete';

interface MFAEnrollStartPayload {
  method_type: 'totp' | 'sms' | 'email';
  qr_code_uri?: string;
  secret?: string;
  destination_masked?: string;
}
```

The wizard orchestrates calls to:
- `POST /api/v1/users/me/mfa/methods/{method_type}/enroll-start`
- `POST /api/v1/users/me/mfa/methods/{method_type}/enroll-confirm`
- `GET /api/v1/users/me/mfa/recovery-codes/status` (on mount)
- `POST /api/v1/users/me/mfa/recovery-codes/generate` (on reaching recovery-codes step)

**⚠️ FE-B13 LOCK**: `MFAEnrollmentWizardProps` (including the new optional extensions) is LOCKED after FE-B12 ships. FE-B13 embeds this component; changes require impact review.

---

#### `NotificationPreferenceMatrix`

**Location**: `packages/ui/src/notification-preference-matrix/`

Renders the 8×3 (or 9×3 with asymmetric Customer activity row) preference matrix. Composes `EffectiveSettingDisplay` cells in "cell mode".

**Interface**:
```typescript
interface NotificationPreferenceMatrixProps {
  /** Full 24-cell response from GET /api/v1/notifications/preferences */
  preferences: NotificationPreferenceCell[];
  /** Category registry from GET /api/v1/notifications/categories */
  categories: NotificationCategoryRow[];
  /** Called when user toggles a cell */
  onCellChange: (categoryId: string, channel: NotificationChannel, enabled: boolean) => Promise<void>;
  /** Called when user reverts a row to tenant defaults */
  onRowRevert: (categoryId: string) => Promise<void>;
  /** Called when user reverts a single cell to tenant default */
  onCellRevert: (categoryId: string, channel: NotificationChannel) => Promise<void>;
  /** Page-level bulk action handlers */
  onMuteAllPush: () => Promise<void>;
  onMuteAllEmail: () => Promise<void>;
  onResetAll: () => Promise<void>;
  /** True when any mutation is pending (disables interactions during in-flight) */
  isPending?: boolean;
  /** Omit specific categories (FE-B13 onboarding embeds a subset) */
  visibleCategories?: string[];
  testID?: string;
}
```

Sub-component `NotificationMatrixCell` is internal (not exported separately). It wraps `EffectiveSettingDisplay` in `displayMode="cell"`.

**⚠️ FE-B13 LOCK**: `NotificationPreferenceMatrixProps` is LOCKED after FE-B12 ships. FE-B13 uses `visibleCategories` to embed a subset.

---

#### `NotificationCenterBell`

**Location**: `packages/ui/src/notification-center-bell/`

Shared web + mobile component for the notification bell icon + unread badge + history drawer.

**Interface**:
```typescript
interface NotificationCenterBellProps {
  /** Provided by useInAppNotifications hook */
  notifications: InAppNotification[];
  unreadCount: number;
  isConnected: boolean;
  onMarkRead: (notificationId: string) => Promise<void>;
  onMarkAllRead: () => Promise<void>;
  onNotificationNavigate: (deepLinkTarget: string) => void;
  testID?: string;
}
```

Web renders a `<button>` icon + `<aside>` drawer panel (slides in from right). Mobile renders a `<Pressable>` + `<BottomSheet>` from Gluestack.

---

### A.2 New Web Feature Components (`apps/web/src/features/` and `apps/web/src/app/(authed)/settings/`)

All web feature components live in `apps/web/src/features/{kebab-name}/components/`.

| Component | Location | Description |
|:---|:---|:---|
| `NotificationPreferencePage` | `features/notification-preferences/` | Full-page wrapper composing `NotificationPreferenceMatrix` with TanStack Query; also owns tenant-defaults sub-page |
| `useInAppNotifications` | `packages/ui/src/hooks/useInAppNotifications.ts` | SSE subscription + bell state management (shared because mobile also needs it) |
| `NotificationBellSlot` | `apps/web/src/app/(authed)/layout.tsx` | Slots `NotificationCenterBell` into the authenticated shell header |
| `VoicePersonaTonePage` | `features/voice-persona/` | Personal preference page + tenant defaults page; three `VoicePersonaToneCard` sub-components |
| `VoicePersonaToneCard` | `features/voice-persona/components/` | Single tone card with description + `TonePreviewButton` + "Use this tone" action |
| `TonePreviewButton` | `features/voice-persona/components/` | Play/pause button wrapping HTML5 `<audio>` |
| `ProfileSettingsPage` | `features/account-settings/` | Name, phone, language, timezone form with `SettingControl` in save-on-blur mode |
| `PasswordChangePage` | `features/account-settings/` | Three-field explicit-save form with session invalidation disclosure |
| `MfaMethodsPage` | `features/account-settings/` | Three method cards + recovery codes section; hosts `MFAEnrollmentWizard` in modal mode |
| `MfaMethodCard` | `features/account-settings/components/` | Single method card showing enrolled status + add/remove affordance |
| `RecoveryCodesSection` | `features/account-settings/components/` | Recovery code count + show/regenerate actions |
| `ActiveSessionsPage` | `features/account-settings/` | Sessions list with revoke affordances; uses optimistic remove |
| `SessionRow` | `features/account-settings/components/` | Single session row with device metadata display |
| `DataExportPage` | `features/account-settings/` | Request export + polling status + recent exports list |
| `DataExportStatusRow` | `features/account-settings/components/` | Single export row with status pill + download CTA |

---

### A.3 New Mobile Feature Components

Mobile settings live under `apps/mobile/app/(tabs)/owner.tsx` and `apps/mobile/features/{kebab}/`.

| Component | Description |
|:---|:---|
| `NotificationPreferencesScreen` | Mobile adaptation of the matrix (vertical stack per category) |
| `VoicePersonaToneScreen` | Three-card vertical stack with preview; composes `VoicePersonaToneCard` (mobile variant) |
| `ProfileSettingsScreen` | Vertical form; photo upload uses native camera/gallery picker |
| `PasswordChangeScreen` | Three-field form |
| `MfaMethodsScreen` | Three method cards; MFA enrollment uses stepped wizard (one step per screen) |
| `ActiveSessionsScreen` | Sessions list |
| `DataExportScreen` | Single-action page + recent exports |
| `NotificationCenterBell` (shared) | Already in A.1 — also embedded in mobile top bar |

---

### A.4 New Routes

#### Web routes (under `apps/web/src/app/(authed)/settings/`)

```
settings/
  notifications/
    preferences/                      → NotificationPreferencePage (personal)
    tenant-defaults/                  → NotificationPreferencePage (tenant mode; owner-only)
  voice-ai/
    persona-tone/                     → VoicePersonaTonePage (personal)
    tenant-defaults/persona-tone/     → VoicePersonaTonePage (tenant mode; owner-only)
  my-account/
    profile/                          → ProfileSettingsPage
    password/                         → PasswordChangePage
    security/
      mfa/                            → MfaMethodsPage
      mfa/enroll/                     → MFAEnrollmentWizard full-page (forceFlow route)
      sessions/                       → ActiveSessionsPage
    data-export/                      → DataExportPage
```

#### Mobile routes (under `apps/mobile/app/`)

```
(tabs)/
  owner/
    settings/
      notifications/preferences/      → NotificationPreferencesScreen
      voice/persona-tone/             → VoicePersonaToneScreen
      my-account/
        profile/                      → ProfileSettingsScreen
        password/                     → PasswordChangeScreen
        security/mfa/                 → MfaMethodsScreen
        security/sessions/            → ActiveSessionsScreen
        data-export/                  → DataExportScreen
```

---

## B — Execution Order

| # | Item | Rationale | Est. Days |
|:---|:---|:---|:---:|
| 1 | **`NotificationPreferenceMatrix` shared component + notification preferences web page** | Largest sub-surface; canonical `EffectiveSettingDisplay` use-case; gates FE-B13 `visibleCategories` embedding. Builds the 8×3 grid, forced-minimum lock cells, per-row/per-cell revert, page-level bulk actions. | 4 |
| 2 | **`useInAppNotifications` hook + `NotificationCenterBell` + SSE wiring in web shell** | In-app channel depends on the category registry established in step 1 (SSE events carry `category_id`). Wires `useSseChannel` to `useNotificationQueue`. Slots bell into the authed layout. | 2 |
| 3 | **Voice persona tone page (web + mobile) including preview audio** | Small, self-contained surface. Composes `EffectiveSettingDisplay` and introduces `VoicePersonaToneCard` + `TonePreviewButton`. | 1.5 |
| 4 | **Profile settings page (web + mobile)** | Standard CRUD; `SettingControl` in save-on-blur mode. Establishes the My Account section routing shell for steps 5–8. | 1.5 |
| 5 | **Password change page** | Explicit-save form; documents FE-B2 interceptor as the cross-device handler. Short implementation. | 1 |
| 6 | **`MFAEnrollmentWizard` flesh-out (all 3 paths + recovery codes + force-flow route)** | Largest FE-B12 implementation item. Implements all three enrollment paths behind the FE-B1 skeleton interface. Builds force-flow full-page route. | 3 |
| 7 | **MFA methods page (web + mobile) — hosts the fleshed wizard** | Composes step 6 wizard in modal mode; method cards with enrolled status; recovery codes section. | 1 |
| 8 | **Active sessions page** | Sessions list with optimistic remove; bulk revoke with `RevertToDefaultDialog`. | 1 |
| 9 | **Data export page + polling flow** | TanStack Query polling; status state machine; export history. RBAC-aware scope annotation. | 1.5 |

**Rationale for ordering**: Notification matrix first because it is the primary FE-B13 gate and the densest component requiring the most review. In-app bell second because it depends on the SSE infrastructure also needed by the notification matrix. Voice persona and account sub-surfaces follow in order of complexity (voice persona smallest; MFA wizard largest). Data export last because it is independent of all other steps.

---

## C — API Contracts

All endpoints confirmed against backend route files. Prefix notation: `NP` = notifications, `VP` = voice persona, `AS` = account security.

### C.1 Notification Preferences (BE-B10/A57)

#### `GET /api/v1/notifications/preferences?user_id={uuid?}`

Returns the full 24-cell matrix for the requesting user (or specified user).

```typescript
interface NotificationPreferencesResponse {
  user_id: string;
  preferences: NotificationPreferenceCell[];
}

interface NotificationPreferenceCell {
  category_id: string;           // e.g., "quote_approvals"
  channel: NotificationChannel;  // "push" | "email" | "in_app"
  enabled: boolean;
  scope: 'user' | 'tenant' | 'system' | 'fallback';
  forced_minimum: boolean;
  can_disable: boolean;          // false = toggle is locked (forced-minimum for this user)
}
```

#### `PUT /api/v1/notifications/preferences/{category_id}/{channel}`

```typescript
// Request
{ enabled: boolean }
// Response 200
{ category_id: string; channel: string; enabled: boolean; scope: 'user' }
// Response 403: forced-minimum push disable blocked
{ detail: string }
```

#### `DELETE /api/v1/notifications/preferences/{category_id}/{channel}`
```typescript
// Response 200
{ cleared: boolean; reverted_to_scope: 'tenant' | 'system' }
```

#### `PUT /api/v1/notifications/tenant-policy/{category_id}/{channel}` (owner only)
```typescript
{ enabled: boolean }
// Response 200: { category_id, channel, enabled, scope: 'tenant' }
```

#### `DELETE /api/v1/notifications/tenant-policy/{category_id}/{channel}` (owner only)
```typescript
// Response 200: { cleared: true, reverted_to_scope: 'system' }
```

#### `POST /api/v1/notifications/preferences/mute-all-push-non-critical`
```typescript
// Response 200: { muted_count: number }
```

#### `POST /api/v1/notifications/preferences/mute-all-email`
```typescript
// Response 200: { muted_count: number }
```

#### `POST /api/v1/notifications/preferences/reset-to-tenant-defaults`
```typescript
// Response 200: { cleared_count: number }
```

#### `GET /api/v1/notifications/categories`
```typescript
interface NotificationCategoryRow {
  category_id: string;       // e.g., "quote_approvals"
  display_label: string;
  description: string;
  display_order: number;
  category_group_id?: string; // Phase 2 grouping; null in MVP
  has_asymmetric_forced_minimum: boolean; // true for customer_activity
}
```

### C.2 In-App Notifications (BE-B10/A57)

#### SSE Channel: `GET /sse/notifications`

`useSseChannel` subscribes with `path: '/sse/notifications'`. Events carry `NotificationSseEvent`:
```typescript
interface NotificationSseEvent {
  notification_id: string;
  category_id: string;
  body: string;
  deep_link_target: string;
  priority: 'standard' | 'critical';
  created_at: string; // ISO 8601
}
```

#### `GET /api/v1/notifications/in-app/recent?limit=50`
```typescript
interface InAppNotification {
  notification_id: string;
  category_id: string;
  body: string;
  deep_link_target: string;
  priority: 'standard' | 'critical';
  created_at: string;
  read_at: string | null;
}
type RecentNotificationsResponse = InAppNotification[];
```

#### `POST /api/v1/notifications/in-app/mark-read`
```typescript
// Request
{ notification_ids: string[] }     // or omit for mark-all
// Response 200
{ marked_count: number }
```

### C.3 Voice Persona Tone (BE-B12/A67)

Mounted at `/api/v1/settings/`.

#### `GET /api/v1/settings/voice-persona-tone`
```typescript
interface VoicePersonaToneEffectiveResponse {
  effective_tone: VoicePersonaTone;      // 'conservative' | 'balanced' | 'playful'
  effective_scope: 'user' | 'tenant' | 'system';
  user_override: VoicePersonaTone | null;
  tenant_default: VoicePersonaTone | null;
  system_default: 'balanced';
  user_override_allowed: boolean;
  available_tones: VoicePersonaTone[];
  preview_audio_urls: Record<VoicePersonaTone, string>; // CDN MP3 URLs
}
```

#### `PUT /api/v1/settings/voice-persona-tone`
```typescript
// Request: { value: VoicePersonaTone }
// Response 200: { setting_key: 'voice_persona_tone', value, scope: 'user', updated_at }
// Response 403: tenant has disabled per-user override
```

#### `DELETE /api/v1/settings/voice-persona-tone`
```typescript
// Response 204
```

#### `GET /api/v1/settings/tenant/voice-persona-tone`
```typescript
interface VoicePersonaToneTenantResponse {
  tenant_default: VoicePersonaTone | null;
  tenant_default_scope: 'tenant' | 'system';
  system_default: 'balanced';
  user_override_policy: boolean;
  available_tones: VoicePersonaTone[];
  preview_audio_urls: Record<VoicePersonaTone, string>;
}
```

#### `PUT /api/v1/settings/tenant/voice-persona-tone` (owner only)
```typescript
// Request: { value: VoicePersonaTone }
```

#### `DELETE /api/v1/settings/tenant/voice-persona-tone` (owner only)
```typescript
// Response 204
```

#### `PUT /api/v1/settings/tenant/voice-persona-tone-user-override-allowed` (owner only)
```typescript
// Request: { value: boolean }
// Response 200: { setting_key: 'voice_persona_tone_user_override_allowed', value, scope: 'tenant', updated_at }
```

### C.4 MFA Status and Enrollment (BE-B13/A68–A69)

Mounted at `/api/v1/users/`.

#### `GET /api/v1/users/me/mfa-status`
```typescript
interface MfaStatusResponse {
  enrolled_methods: MFAEnrollmentPath[];
  tenant_policy_required: boolean;
  grace_period_active: boolean;
  grace_ends_at: string | null;     // ISO 8601
  enforcement_activated: boolean;
}
```

#### `POST /api/v1/users/me/mfa/methods/{method_type}/enroll-start`
```typescript
interface MfaEnrollStartResponse {
  method_type: MFAEnrollmentPath;
  qr_code_uri?: string;             // TOTP only
  secret?: string;                  // TOTP only
  destination_masked?: string;      // SMS/Email
}
```

#### `POST /api/v1/users/me/mfa/methods/{method_type}/enroll-confirm`
```typescript
// Request: { code: string }
interface MfaEnrollConfirmResponse {
  method_id: string;
  enrolled_at: string;
}
```

#### `DELETE /api/v1/users/me/mfa/methods/{method_id}`
```typescript
// Response 204 on success
// Response 409: { code: 'last_method_required', detail: string }
```

#### `POST /api/v1/users/me/mfa/recovery-codes/generate`
```typescript
interface MfaRecoveryCodesGenerateResponse {
  codes: string[];          // 10 plaintext codes; shown once
  set_id: string;
}
```

#### `GET /api/v1/users/me/mfa/recovery-codes/status`
```typescript
interface MfaRecoveryCodesStatusResponse {
  unused_code_count: number;
  last_generated_at: string | null;
}
```

### C.5 Active Sessions (BE-B13/A70)

#### `GET /api/v1/users/me/sessions`
```typescript
interface SessionResponse {
  session_id: string;
  display_label: string;       // "Chrome on macOS"
  ip_address: string;
  geolocation: string | null;
  created_at: string;
  last_active_at: string;
  is_current: boolean;
  revoked_at: string | null;
}
type SessionsResponse = SessionResponse[];
```

#### `DELETE /api/v1/users/me/sessions/{session_id}`
```typescript
// Response 204
// Response 404: session not found
```

#### `POST /api/v1/users/me/sessions/revoke-others`
```typescript
interface RevokeOthersResponse {
  revoked_count: number;
}
```

### C.6 Data Export (BE-B13/A71)

#### `POST /api/v1/users/me/data-exports`
```typescript
interface DataExportCreateResponse {
  export_id: string;
  status: 'pending';
  requested_at: string;
}
// Response 429: 24h frequency limit exceeded
```

#### `GET /api/v1/users/me/data-exports`
```typescript
type DataExportsListResponse = DataExportStatusResponse[];
```

#### `GET /api/v1/users/me/data-exports/{export_id}`
```typescript
interface DataExportStatusResponse {
  export_id: string;
  status: DataExportStatus;        // 'pending' | 'processing' | 'ready' | 'expired' | 'failed'
  requested_at: string;
  expires_at: string | null;       // 7 days after ready
  signed_url: string | null;       // non-null when status = 'ready'
  data_scope: 'full_tenant' | 'user_specific';
  failure_reason: string | null;
}
```

---

## D — State Management

### D.1 Notification Center Bell State

Managed by `useInAppNotifications` hook (shared, in `packages/ui/src/hooks/useInAppNotifications.ts`):

```typescript
interface UseInAppNotificationsReturn {
  notifications: InAppNotification[];          // last 50, descending by created_at
  unreadCount: number;
  isConnected: boolean;                        // SSE connection status
  isBellOpen: boolean;
  openBell: () => void;
  closeBell: () => void;
  markRead: (notificationId: string) => Promise<void>;
  markAllRead: () => Promise<void>;
  clearAll: () => void;                        // local clear; does not call API
}
```

State composition:
- `notifications` initialized from TanStack Query `GET /api/v1/notifications/in-app/recent`
- `unreadCount` = `notifications.filter(n => !n.read_at).length` derived value
- SSE `onMessage` prepends new notification to `notifications` list + increments unread count via `queryClient.setQueryData` mutation
- `markRead` calls `POST .../mark-read` + updates `read_at` optimistically in the list

### D.2 MFA Wizard State Machine

Internal state in `MFAEnrollmentWizard` — not lifted to TanStack Query (wizard is a transient flow):

```typescript
interface MfaWizardState {
  internalStep: MFAWizardInternalStep;
  selectedPath: MFAEnrollmentPath | null;
  enrollStartPayload: MfaEnrollStartPayload | null;  // QR code / masked destination
  codeInput: string;                                  // verification code field
  enrolledMethodId: string | null;                    // on confirm success
  recoveryCodes: string[] | null;                     // after generate
  recoveryCodesAcknowledged: boolean;
  isLoading: boolean;
  error: string | null;                               // inline error message
}
```

Transitions fire async API calls; `isLoading` blocks interaction during in-flight.

### D.3 Data Export Async State Machine

```typescript
type DataExportStatus = 'idle' | 'pending' | 'processing' | 'ready' | 'expired' | 'failed';

interface DataExportPageState {
  activeExportId: string | null;
  status: DataExportStatus;
  signedUrl: string | null;
  expiresAt: string | null;
  failureReason: string | null;
  recentExports: DataExportStatusResponse[];
}
```

`activeExportId` is set after `POST /me/data-exports`. TanStack Query `useQuery` on `GET .../data-exports/{activeExportId}` with `refetchInterval: (data) => data?.status === 'ready' || data?.status === 'failed' ? false : 10_000`.

### D.4 Password Change Form States

```typescript
type PasswordChangePhase =
  | 'idle'
  | 'submitting'
  | 'success'       // banner shown; form cleared
  | 'error';        // validation or server error

interface PasswordChangeFormState {
  currentPassword: string;
  newPassword: string;
  confirmPassword: string;
  phase: PasswordChangePhase;
  errorMessage: string | null;
}
```

`useFormSaveStrategy({ mode: 'explicit' })` from FE-B11 manages the form-level save behavior.

### D.5 Active Sessions Optimistic Remove

TanStack Query with optimistic updates:
```typescript
// In useMutation for DELETE /me/sessions/{session_id}
onMutate: async (sessionId) => {
  await queryClient.cancelQueries({ queryKey: ['sessions'] });
  const previous = queryClient.getQueryData<SessionResponse[]>(['sessions']);
  queryClient.setQueryData<SessionResponse[]>(['sessions'],
    (old) => old?.filter(s => s.session_id !== sessionId) ?? []);
  return { previous };
},
onError: (_err, _vars, context) => {
  queryClient.setQueryData(['sessions'], context?.previous);
},
onSettled: () => {
  queryClient.invalidateQueries({ queryKey: ['sessions'] });
},
```

---

## E — Error States

| Surface | Trigger | UI Treatment |
|:---|:---|:---|
| **Notification matrix — forced-minimum block** | `PUT .../preferences/{id}/{channel}` returns 403 | Toggle visually snaps back to `on`; inline explainer appears below the row: "Push for [category] can't be turned off here." No toast (the explainer is sufficient). |
| **Notification matrix — write failure** | `PUT` returns 500 or network timeout | Optimistic toggle reverts; `NotificationBanner` with `severity: "error"`: "Couldn't save preference — try again." |
| **Notification SSE disconnect** | `useSseChannel` `connectionError` fires | `NotificationCenterBell` shows a small disconnected indicator dot (amber). Reconnect attempt auto-retries with backoff. No blocking UI. |
| **MFA enrollment — wrong code** | `enroll-confirm` returns 400 | Inline error below code input: "That code doesn't match. Check your app and try again." Code input clears. Max attempts not tracked client-side (server handles lockout). |
| **MFA enrollment — code expired** | SMS/Email code expires before entry | Same 400 error path; error message: "Code expired. Request a new one." + "Resend code" link re-calls `enroll-start`. |
| **MFA enrollment — last method deletion blocked** | `DELETE /me/mfa/methods/{id}` returns 409 with `code: 'last_method_required'` | Modal dialog: "Can't remove last method — your team requires MFA. Add another method first or contact your owner." |
| **Password change — wrong current password** | API returns 400/401 | Inline error on current-password field: "Current password is incorrect." |
| **Password change — policy violation** | Cognito returns 400 (too short, reused) | Inline error below new-password field: "Password doesn't meet requirements: [reason]." |
| **Session revoke failure** | `DELETE /me/sessions/{id}` returns 404/500 | Optimistic remove reverts (row reappears); `NotificationBanner` error: "Couldn't revoke session — try again." |
| **Data export — service unavailable** | `POST /me/data-exports` returns 503 | `ErrorState` component replaces the request button: "Export service is temporarily unavailable. Try again later." |
| **Data export — frequency limit** | `POST` returns 429 | Inline: "You already requested an export recently. You can request another in {hours}h." Button disabled until window passes. |
| **Voice persona — write failure** | `PUT /settings/voice-persona-tone` returns 403 (user override disabled) | Card selection reverts; `NotificationBanner` info: "Your team has restricted voice tone to a single setting. Contact your owner to change it." |
| **Voice persona — write failure (network)** | `PUT` returns 500 | Card selection reverts; `NotificationBanner` error: "Couldn't save tone preference — try again." |
| **Preview audio load failure** | Audio file 404 / CORS error | `TonePreviewButton` renders error state: "Preview unavailable." No blocking UI. |

---

## F — TypeScript Interfaces

All interfaces are complete — no placeholders.

### F.1 MFA Wizard (LOCKED for FE-B13)

```typescript
// packages/ui/src/mfa-enrollment-wizard/types.ts — additive extensions to FE-B1 skeleton

export type MFAEnrollmentPath = 'totp' | 'sms' | 'email';

export type MFAEnrollmentStep =
  | 'method-select'
  | 'setup'
  | 'verify'
  | 'complete';

export type MFAWizardInternalStep =
  | 'method-select'
  | 'setup-totp' | 'setup-sms' | 'setup-email'
  | 'verify-totp' | 'verify-sms' | 'verify-email'
  | 'recovery-codes'
  | 'complete';

// FE-B1 skeleton interface — preserved exactly
export interface MFAEnrollmentWizardProps {
  forcedPath?: MFAEnrollmentPath;
  allowedPaths?: MFAEnrollmentPath[];
  onComplete: (enrolledPath: MFAEnrollmentPath) => void;
  onCancel: () => void;
  gracePeriodDaysRemaining?: number;
  currentStep?: MFAEnrollmentStep;
  testID?: string;
}

// FE-B12 additive extensions (all optional — no breaking changes)
export interface MFAEnrollmentWizardPropsExtended extends MFAEnrollmentWizardProps {
  forceFlow?: boolean;
  showRecoveryCodes?: boolean;
  onRecoveryCodesAcknowledged?: () => void;
  enrolledMethods?: MFAEnrollmentPath[];
}

export interface MfaEnrollStartPayload {
  method_type: MFAEnrollmentPath;
  qr_code_uri?: string;
  secret?: string;
  destination_masked?: string;
}

export interface MfaWizardState {
  internalStep: MFAWizardInternalStep;
  selectedPath: MFAEnrollmentPath | null;
  enrollStartPayload: MfaEnrollStartPayload | null;
  codeInput: string;
  enrolledMethodId: string | null;
  recoveryCodes: string[] | null;
  recoveryCodesAcknowledged: boolean;
  isLoading: boolean;
  error: string | null;
}
```

### F.2 Notification Preference Matrix (LOCKED for FE-B13)

```typescript
// packages/ui/src/notification-preference-matrix/types.ts

export type NotificationChannel = 'push' | 'email' | 'in_app';

export type NotificationPreferenceScope = 'user' | 'tenant' | 'system' | 'fallback';

export interface NotificationPreferenceCell {
  category_id: string;
  channel: NotificationChannel;
  enabled: boolean;
  scope: NotificationPreferenceScope;
  forced_minimum: boolean;
  can_disable: boolean;
}

export interface NotificationCategoryRow {
  category_id: string;
  display_label: string;
  description: string;
  display_order: number;
  category_group_id?: string;
  has_asymmetric_forced_minimum: boolean;
}

export interface NotificationPreferenceMatrixProps {
  preferences: NotificationPreferenceCell[];
  categories: NotificationCategoryRow[];
  onCellChange: (categoryId: string, channel: NotificationChannel, enabled: boolean) => Promise<void>;
  onRowRevert: (categoryId: string) => Promise<void>;
  onCellRevert: (categoryId: string, channel: NotificationChannel) => Promise<void>;
  onMuteAllPush: () => Promise<void>;
  onMuteAllEmail: () => Promise<void>;
  onResetAll: () => Promise<void>;
  isPending?: boolean;
  visibleCategories?: string[];  // FE-B13 uses this to show a subset
  testID?: string;
}
```

### F.3 In-App Notification Bell

```typescript
// packages/ui/src/notification-center-bell/types.ts

export interface InAppNotification {
  notification_id: string;
  category_id: string;
  body: string;
  deep_link_target: string;
  priority: 'standard' | 'critical';
  created_at: string;
  read_at: string | null;
}

export interface NotificationCenterBellProps {
  notifications: InAppNotification[];
  unreadCount: number;
  isConnected: boolean;
  onMarkRead: (notificationId: string) => Promise<void>;
  onMarkAllRead: () => Promise<void>;
  onNotificationNavigate: (deepLinkTarget: string) => void;
  testID?: string;
}

export interface UseInAppNotificationsReturn {
  notifications: InAppNotification[];
  unreadCount: number;
  isConnected: boolean;
  isBellOpen: boolean;
  openBell: () => void;
  closeBell: () => void;
  markRead: (notificationId: string) => Promise<void>;
  markAllRead: () => Promise<void>;
}
```

### F.4 Voice Persona Tone

```typescript
// apps/web/src/features/voice-persona/types.ts

export type VoicePersonaTone = 'conservative' | 'balanced' | 'playful';

export interface VoicePersonaToneEffectiveResponse {
  effective_tone: VoicePersonaTone;
  effective_scope: 'user' | 'tenant' | 'system';
  user_override: VoicePersonaTone | null;
  tenant_default: VoicePersonaTone | null;
  system_default: 'balanced';
  user_override_allowed: boolean;
  available_tones: VoicePersonaTone[];
  preview_audio_urls: Record<VoicePersonaTone, string>;
}

export interface VoicePersonaToneCard {
  tone: VoicePersonaTone;
  label: string;
  description: string;
  isSelected: boolean;
  isTeamDefault: boolean;
  previewAudioUrl: string;
  onSelect: () => void;
  disabled?: boolean;   // when user override not allowed
}

export type TonePreviewState = 'idle' | 'loading' | 'playing' | 'ended' | 'error';
```

### F.5 Active Sessions

```typescript
// apps/web/src/features/account-settings/types.ts

export interface ActiveSession {
  session_id: string;
  display_label: string;
  ip_address: string;
  geolocation: string | null;
  created_at: string;
  last_active_at: string;
  is_current: boolean;
  revoked_at: string | null;
}
```

### F.6 Data Export

```typescript
export type DataExportStatus = 'pending' | 'processing' | 'ready' | 'expired' | 'failed';

export interface DataExportStatusResponse {
  export_id: string;
  status: DataExportStatus;
  requested_at: string;
  expires_at: string | null;
  signed_url: string | null;
  data_scope: 'full_tenant' | 'user_specific';
  failure_reason: string | null;
}

export interface DataExportPageState {
  activeExportId: string | null;
  status: DataExportStatus | 'idle';
  signedUrl: string | null;
  expiresAt: string | null;
  failureReason: string | null;
}
```

---

## G — Test Plan

**Targets**: 80+ unit, 20+ integration, 4+ E2E per impl plan.
**Test subfolder**: `apps/{web,mobile}/__tests__/batch_fe_b12/`

### G.1 Unit Tests (target: 80+)

#### Notification Preference Matrix (25 tests)
- Matrix renders 8 category rows × 3 channel columns (24 cells)
- Customer activity renders as two rows (asymmetric) when user has owner context
- Customer activity renders as one row when user is tech-only
- Forced-minimum cell (`can_disable: false`) renders toggle with pointer-events-none + lock glyph
- Forced-minimum cell tooltip text renders on focus
- Non-forced-minimum cell toggles fire `onCellChange`
- Scope annotation renders `(user)` / `(tenant)` / `(system)` correctly per cell
- Per-row "Match tenant default" link appears when any cell in row has `scope: 'user'`
- Per-row revert link fires `onRowRevert(categoryId)`
- Per-cell revert popover fires `onCellRevert(categoryId, channel)`
- "Mute all push (non-critical)" fires `onMuteAllPush`
- "Mute all email" fires `onMuteAllEmail`
- "Reset to tenant defaults" fires `onResetAll`
- `isPending` prop disables all interactions
- `visibleCategories` prop filters to subset (FE-B13 use case)
- `PUT` returns 403 → toggle reverts + inline explainer shows
- Network error on toggle → toggle reverts + error banner fires
- Category rows render in `display_order` sequence
- Matrix is accessible: each toggle has aria-label `"{category} {channel} notification"`
- Forced-minimum cell has `aria-disabled="true"`

#### In-App Notification Bell (15 tests)
- `useInAppNotifications` initializes unread count from fetched recent-50 list
- SSE message → new notification prepended to list + unread count incremented
- `markRead` → `read_at` populated optimistically + unread count decremented
- `markAllRead` → all `read_at` set + unread count = 0
- `NotificationCenterBell` renders bell icon with badge showing unread count
- Badge does not render when `unreadCount === 0`
- Bell click opens drawer; click outside closes drawer
- Drawer shows at most 50 notifications
- Each notification row shows category icon + body + relative time
- Notification row click calls `onNotificationNavigate(deepLinkTarget)`
- "Mark all read" button in drawer fires `onMarkAllRead`
- SSE disconnect → bell renders disconnected indicator (amber dot)
- SSE reconnects → indicator clears
- Critical notification gets `dismissAfterMs: 12000`; standard gets 6000
- ARIA: bell button has `aria-label="Notifications (N unread)"` 

#### MFA Enrollment Wizard (20 tests)
- Renders method-select step with all 3 path options by default
- `forcedPath="totp"` skips to setup-totp step
- `enrolledMethods={['totp']}` shows TOTP as already enrolled in method-select
- Selecting TOTP path: QR code URI and secret render in setup-totp step
- QR code renders as `<img>` with `alt` containing the secret
- Selecting SMS path: `destination_masked` displays in setup-sms step
- Selecting Email path: masked email displays in setup-email step
- Code input accepts only 6-digit numeric input
- `enroll-confirm` success → advances to recovery-codes step (when `showRecoveryCodes: true`)
- `enroll-confirm` success → advances to complete step (when `showRecoveryCodes: false`)
- Recovery codes step: 10 codes rendered in monospace grid
- "Copy all" copies codes to clipboard
- Continue button disabled until "I've saved my recovery codes" checkbox is checked
- `gracePeriodDaysRemaining={3}` renders amber alert banner
- `gracePeriodDaysRemaining={0}` renders red alert banner
- `gracePeriodDaysRemaining` undefined → no banner
- `forceFlow={true}` → Cancel button not rendered
- Wrong code (400 response) → inline error shows; code input clears
- Last method deletion blocked (409) → specific error modal
- `onComplete(enrolledPath)` fires after complete step

#### Voice Persona Tone (10 tests)
- Page renders 3 tone cards
- `effective_tone = 'balanced'` → balanced card shows "✓ Selected"
- Team-default annotation appears on the card matching `tenant_default`
- "Use this tone" click fires PUT mutation with correct value
- Card selection updates immediately (optimistic)
- On PUT success: scope annotation updates to `(your preference)`
- On PUT 403 (override disabled): card reverts + info banner fires
- "Match team default" link fires DELETE mutation to clear user override
- `user_override_allowed: false` → all "Use this tone" buttons disabled; read-only annotation
- `TonePreviewButton` transitions through idle → playing → ended states

#### Account Settings — Password Change (5 tests)
- Form renders three password fields
- "Change password" button disabled when any field is empty
- Confirm-new mismatch shows inline validation error before submit
- On success: fields clear + success `NotificationBanner` fires
- On 401 (wrong current password): inline error on current-password field

#### Account Settings — Sessions (5 tests)
- Session list renders with device label, location, last-active
- Current session has "(This device)" badge; no revoke button
- "Revoke this session" → optimistic row removal
- Revoke 404 → row reappears + error banner
- "Revoke all other sessions" → `RevertToDefaultDialog` appears

#### Data Export (5 tests)
- Initial state: "Request export" button + empty recent exports list
- After POST: `pending` state renders with spinner
- `useQuery` refetch → `processing` state renders
- `status === 'ready'` → "Download" CTA renders; link points to `signed_url`
- `status === 'expired'` → neutral badge + "Link expired" text; no download link

### G.2 Integration Tests (target: 20+)

| # | Scenario |
|:---|:---|
| 1 | Full notification preference matrix → toggle cell → API write → matrix refetches with updated scope |
| 2 | Toggle forced-minimum push cell → 403 response → toggle reverts + inline explainer |
| 3 | "Mute all push" → bulk API call → matrix refetches with all push cells disabled |
| 4 | SSE notification arrives → `NotificationBanner` shows in portal → bell unread count increments |
| 5 | Bell opens → last-50 list loads → click notification → `deepLinkTarget` navigates |
| 6 | Mark notification read → `read_at` updates in list → bell count decrements |
| 7 | Mark all read → all `read_at` populated → bell badge clears |
| 8 | TOTP enrollment full flow: enroll-start → QR renders → code entry → enroll-confirm → recovery codes → complete |
| 9 | SMS enrollment: enroll-start → masked phone → code entry → enroll-confirm → complete (no recovery codes on 2nd method) |
| 10 | Email enrollment: enroll-start → masked email → code entry → enroll-confirm → complete |
| 11 | Force-flow redirect: login with `?mfa_required=1&grace_days=2` → wizard renders full-page with grace banner |
| 12 | Password change → success → `NotificationBanner` fires → form clears |
| 13 | Session list loads → revoke non-current session → row removes optimistically → list refetches |
| 14 | Revoke all other sessions → `RevertToDefaultDialog` → confirm → count returns |
| 15 | Data export: POST → `pending` → poll interval hits `ready` → download CTA appears with signed URL |
| 16 | Data export: POST → `429` response → inline frequency-limit message |
| 17 | Voice persona: select `playful` → PUT → page reflects `(your preference)` scope |
| 18 | Voice persona: tenant disables user override → PUT returns 403 → info banner; cards disabled |
| 19 | Voice preview: "Hear preview" click → audio plays → button transitions to ended state |
| 20 | Tenant notification defaults page (owner): PUT tenant-policy cell → `scope: tenant` in refetched matrix |

### G.3 E2E Tests (target: 4+)

| # | Scenario | Platform |
|:---|:---|:---|
| E2E-1 | **TOTP enrollment with real authenticator app** — trigger enroll-start, scan QR with authenticator app in test harness (or TOTP seed from secret), enter real 6-digit code, confirm enrollment, download recovery codes | Web |
| E2E-2 | **MFA force-flow on tenant policy activation** — owner enables tenant MFA, second user logs in, gets redirected to force-flow enrollment page, completes TOTP enrollment, lands on the intended post-login page | Web |
| E2E-3 | **Password change cross-device verification** — open two tabs in same browser, change password in tab A, verify tab B's next API request receives 401 and FE-B2 interceptor redirects to login | Web |
| E2E-4 | **Data export download** — request export, poll until ready, click download, verify the ZIP contains MANIFEST.json | Web |

---

## H — Token Audit

All design tokens from `packages/ui/src/tokens.ts`. No hardcoded values.

| Surface | Element | Token |
|:---|:---|:---|
| Notification matrix | Forced-minimum locked cell background | `neutral-100` |
| Notification matrix | Forced-minimum locked cell text (toggle label) | `neutral-400` |
| Notification matrix | Forced-minimum lock glyph icon | `neutral-400` |
| Notification matrix | Forced-minimum inline explainer text | `neutral-500` — subdued, not fault/red |
| Notification matrix | Active user-override toggle (on) | `brand-500` |
| Notification matrix | Per-row revert link | `brand-600` text link |
| Notification matrix | `(user)` scope annotation | `brand-50` background, `brand-700` text |
| Notification matrix | `(tenant)` scope annotation | `neutral-100` background, `neutral-600` text |
| Notification matrix | `(system)` scope annotation | `neutral-50` background, `neutral-400` text |
| Notification bell | Unread badge (1–9 count) | `brand-500` background, `white` text |
| Notification bell | Unread badge (10+) | `brand-700` background, `white` text (higher urgency) |
| Notification bell | SSE disconnected indicator | `alert-300` (amber dot) |
| MFA wizard | Grace period banner (>3 days) | `info-50` background, `info-700` text |
| MFA wizard | Grace period banner (≤3 days) | `alert-50` background, `alert-700` text |
| MFA wizard | Grace period banner (day 0) | `error-50` background, `error-700` text |
| MFA wizard | Recovery codes container | `neutral-50` background, monospace font |
| MFA wizard | "I've saved my codes" checkbox label (before check) | `error-700` — draws attention |
| Data export | `pending` / `processing` status pill | `alert-100` background, `alert-700` text |
| Data export | `ready` status pill | `success-50` background, `success-700` text |
| Data export | Download CTA button | `brand-500` background, `white` text |
| Data export | `expired` status pill | `neutral-100` background, `neutral-500` text |
| Data export | `failed` status pill | `error-50` background, `error-700` text |
| Voice persona | Selected tone card border | `brand-500` 2px border |
| Voice persona | Unselected tone card border | `neutral-200` 1px border |
| Voice persona | Team default annotation | `neutral-100` background, `neutral-600` text |
| Voice persona | `(your preference)` annotation | `brand-50` background, `brand-700` text |
| Active sessions | Current session row `(This device)` badge | `brand-50` background, `brand-700` text |
| Active sessions | "Revoke all" button | `error-600` text (destructive action color) |
| Password change | Success `NotificationBanner` | `success` severity → `success-500` left accent |

---

## I — Downstream Contract Lock (FE-B13 Imports)

FE-B13 (Onboarding & Push Permissions) imports three components from FE-B12. The following interfaces are **LOCKED** after FE-B12 ships. FE-B13 may NOT pass undocumented props; changes require architect review.

### `MFAEnrollmentWizard` — Locked Interface for FE-B13

FE-B13 embeds `MFAEnrollmentWizard` in the onboarding flow for tenants requiring MFA. FE-B13 **may use**:

```typescript
// Props FE-B13 may pass:
<MFAEnrollmentWizard
  forcedPath="totp"                           // optional: guide to TOTP
  allowedPaths={['totp', 'sms', 'email']}    // optional: restrict paths
  onComplete={(path) => { /* advance wizard */ }}
  onCancel={() => { /* skip if not required */ }}
  gracePeriodDaysRemaining={graceDays}        // from mfa-status response
  forceFlow={tenantRequiresMfa}               // hides cancel in required context
  showRecoveryCodes={!hasRecoveryCodes}       // from recovery-codes/status
  enrolledMethods={enrolledMethods}           // from mfa-status
/>
```

FE-B13 **must not**:
- Modify `MFAEnrollmentWizardProps` or `MFAEnrollmentWizardPropsExtended` types
- Import internal sub-components (`MfaMethodCard`, `RecoveryCodesSection`, etc.)
- Rely on internal state machine types (`MFAWizardInternalStep`, `MfaWizardState`)

### `NotificationPreferenceMatrix` — Locked Interface for FE-B13

FE-B13 embeds a **subset** of the matrix during onboarding ("Choose your notification preferences"). FE-B13 **may use**:

```typescript
// Props FE-B13 may pass:
<NotificationPreferenceMatrix
  preferences={preferences}                   // from GET /api/v1/notifications/preferences
  categories={categories}                     // from GET /api/v1/notifications/categories
  onCellChange={handleCellChange}
  onRowRevert={handleRowRevert}
  onCellRevert={handleCellRevert}
  onMuteAllPush={handleMuteAllPush}
  onMuteAllEmail={handleMuteAllEmail}
  onResetAll={handleResetAll}
  visibleCategories={['job_activity', 'quote_approvals', 'customer_activity']}
  // ^ FE-B13 shows a 3-category subset inline in the onboarding wizard step
/>
```

FE-B13 **must not**:
- Pass props not defined in `NotificationPreferenceMatrixProps`
- Import `NotificationMatrixCell` (internal sub-component; not exported)
- Implement its own matrix rendering; must always compose `NotificationPreferenceMatrix`

### `NotificationCenterBell` — Locked Interface for FE-B13

FE-B13 may embed `NotificationCenterBell` in the onboarding confirmation screen ("You're all set — notifications are active").

```typescript
// Props FE-B13 may pass:
<NotificationCenterBell
  notifications={notifications}
  unreadCount={unreadCount}
  isConnected={isConnected}
  onMarkRead={markRead}
  onMarkAllRead={markAllRead}
  onNotificationNavigate={router.push}
/>
```

`NotificationCenterBellProps` is fully exposed. FE-B13 composes `useInAppNotifications` to supply the bell's props.

### Type Exports for FE-B13

FE-B13 may import these types from `@pilot/ui`:
- `MFAEnrollmentPath`, `MFAEnrollmentStep` (FE-B1 originals)
- `MFAEnrollmentWizardProps`, `MFAEnrollmentWizardPropsExtended`
- `NotificationPreferenceMatrixProps`, `NotificationPreferenceCell`, `NotificationCategoryRow`, `NotificationChannel`
- `NotificationCenterBellProps`, `InAppNotification`
- `UseInAppNotificationsReturn`

FE-B13 must NOT import:
- `MFAWizardInternalStep`, `MfaWizardState` (internal implementation types)
- `NotificationMatrixCell`, `VoicePersonaToneCard`, `TonePreviewButton` (feature-scoped components)
- `DataExportPageState` (account-settings–scoped types)

---

*All backend endpoints confirmed against `backend/api/routes/notification_preferences.py`, `backend/api/routes/account_security.py`, and `backend/api/routes/voice_persona.py`. All FE-B11 locked interfaces confirmed against `packages/ui/src/index.ts`. FE-B1 skeleton interface confirmed against `packages/ui/src/mfa-enrollment-wizard/types.ts`. SSE hook interface confirmed against `packages/ui/src/hooks/useSseChannel.ts`.*
