# MOB-B10 Batch Design — Mobile Account Settings: Profile + Security + MFA

**Version**: 1.0  
**Date**: 2026-07-17  
**Batch**: MOB-B10  
**Prerequisite Batches**: MOB-B9 ✅  
**Estimated Effort**: 3–4 hours (pure mobile frontend — no backend companion)  
**Test Subfolder**: `apps/mobile/__tests__/batch_mob_b10/`  
**Platform**: Mobile only (Expo / React Native)  
**Status**: Design complete — ready for React Native Engineer implementation

---

## A. Input Read Summary

All source artifacts read directly before writing this document.

| Artifact | Key Findings |
|:---|:---|
| `(home)/settings/index.tsx` | 4 menu items defined: My Account (links to `settings/my-account` — **file does not exist**), Sync & Storage ✅, Operations ✅, Voice ✅. |
| `(home)/_layout.tsx` | Only `index`, `voice/index`, `voice/[sessionId]` Stack.Screen registered. **No settings/* Stack.Screen entries** — any push to settings routes silently fails. |
| `(tabs)/_layout.tsx` | Existing `href: null` suppressions for `more/*`, `customers/[id]/*`, `jobs/[jobId]/*`, `calcs/*`. **No suppression entries for `(home)/settings/*`** deep screens. |
| `(home)/settings/operations.tsx` | Pattern reference: `ScrollView` + `StyleSheet` + loading/error guard + heading `Text`. Uses `useMobileSettingsCatalog` hook. |
| `(home)/settings/voice.tsx` | Same pattern as operations. Uses `useMutation` + `useQueryClient`. Note: uses raw `fetch()` — **pre-existing violation, do NOT copy this pattern.** Use `apiClient` from `@pilot/shared-api`. |
| `web/src/features/account-settings/components/ProfileSettingsForm.tsx` | Fields: first_name (editable, save-on-blur), last_name (editable, save-on-blur), email (read-only), phone (editable, save-on-blur), timezone (picker, save-on-blur). Calls `PATCH /api/v1/users/me`. |
| `web/src/features/account-settings/components/SecurityIndexPage.tsx` | Nav cards: MFA (shows enrolled count), Active Sessions (view/revoke), Password (change), Data Export. Mobile scope: MFA only — sessions/password/data-export are web-only in MVP. |
| `web/src/app/(authed)/settings/my-account/security/mfa/page.tsx` | Calls `GET /api/v1/users/me/mfa-status` → `enrolled_methods[]`. Shows method list. "Add this method" → `MFAEnrollmentWizard`. |
| `packages/ui/src/mfa-enrollment-wizard/mobile/MFAEnrollmentWizard.tsx` | Mobile skeleton already exists. Supports `totp` and `sms` paths. `MOBILE_ALLOWED_PATHS = ["totp", "sms"]`. Import: `from "@pilot/ui"` (mobile re-export). |
| `backend/openapi_schema_map.md` (MCP verified) | `GET /api/v1/users/me` ✅, `PATCH /api/v1/users/me` ✅, `GET /api/v1/users/me/mfa-status` ✅. All three endpoints confirmed. |

---

## B. Migration Plan

### B.1 No Database Migration Required
MOB-B10 is a pure frontend batch. No schema changes.

### B.2 No Backend Companion Required
All three API endpoints are confirmed in `openapi_schema_map.md`:

| Endpoint | Method | Used By |
|---|---|---|
| `/api/v1/users/me` | GET | `useMyProfile` hook — loads profile for display |
| `/api/v1/users/me` | PATCH | `useMyProfile` hook — save-on-blur field updates |
| `/api/v1/users/me/mfa-status` | GET | `useMfaStatus` (mobile) — enrolled methods count + list |

MFA enrollment calls Cognito directly via the Amplify SDK — no Pilot API endpoint required for that flow. The `MFAEnrollmentWizard` mobile skeleton handles this internally.

### B.3 Pre-Work Verification (React Native Engineer)

Before writing any code, run:

```bash
# Confirm the 3 API endpoints exist
grep -A 3 "users/me" backend/openapi_schema_map.md | head -30

# Confirm mobile MFAEnrollmentWizard export path
grep -n "MFAEnrollment" frontend/packages/ui/src/index.ts

# Confirm apiClient is importable in mobile
grep -rn "from \"@pilot/shared-api\"" frontend/apps/mobile/features/ | head -5

# Confirm style-constants token file exists
ls frontend/apps/mobile/constants/style-constants.ts
```

---

## C. Execution Order

| # | Task | File(s) | Dependency |
|:---:|:---|:---|:---|
| 1 | Read all source files listed in §A | — | None |
| 2 | Register settings Stack.Screen entries in Home layout | `(home)/_layout.tsx` | None |
| 3 | Add tab bar suppressions for new deep settings routes | `(tabs)/_layout.tsx` | None |
| 4 | Add gear icon `headerRight` to Home tab header | `(home)/index.tsx` | #2 |
| 5 | Create `useMyProfile` mobile hook | `features/account-settings/hooks/useMyProfile.ts` | None |
| 6 | Create `useMfaStatus` mobile hook | `features/account-settings/hooks/useMfaStatus.ts` | None |
| 7 | Create MSW handler: `accountSettingsHandlers.ts` | `mocks/handlers/accountSettingsHandlers.ts` | #5, #6 |
| 8 | Register handler in mobile `mocks/handlers/index.ts` | `mocks/handlers/index.ts` | #7 |
| 9 | Create `my-account.tsx` — Profile screen | `settings/my-account.tsx` | #5 |
| 10 | Create `my-account/security.tsx` — Security index | `settings/my-account/security.tsx` | #6 |
| 11 | Create `my-account/security/mfa.tsx` — MFA enrollment | `settings/my-account/security/mfa.tsx` | #6 |
| 12 | Write unit + integration tests | `__tests__/batch_mob_b10/` | #9–#11 |
| 13 | Regression check + TypeScript + lint | — | #12 |

---

## D. API Endpoints Consumed

### D.1 `GET /api/v1/users/me`

**Used by**: `useMyProfile` — load profile on mount

**Response** (confirmed from openapi_schema_map.md):
```json
{
  "user_id": "uuid",
  "first_name": "Tom",
  "last_name": "Lang",
  "email": "tom@example.com",
  "phone": "+13035550001",
  "timezone": "America/Denver",
  "role": "owner",
  "display_name": "Tom Lang"
}
```

### D.2 `PATCH /api/v1/users/me`

**Used by**: `useMyProfile` — save-on-blur field updates

**Request body** (partial update — send only the changed field):
```json
{ "first_name": "Thomas" }
```
or
```json
{ "phone": "+13035550002" }
```

**Response**: Updated user object (same shape as GET).

### D.3 `GET /api/v1/users/me/mfa-status`

**Used by**: `useMfaStatus` (mobile)

**Response** (confirmed from web implementation):
```json
{
  "enrolled_methods": ["totp"],
  "tenant_policy_required": false,
  "grace_period_active": false,
  "grace_ends_at": null,
  "enforcement_activated": false
}
```

`enrolled_methods` is an array of `MFAEnrollmentPath` values: `"totp"`, `"sms"`, `"email"`.

---

## E. Pattern Reuse Decisions

### E.1 Save-on-Blur (Profile fields)
Mirror the web `ProfileSettingsForm.tsx` pattern exactly:
- User edits a field → on focus loss, `PATCH /api/v1/users/me` fires with just that field.
- Show inline "Saved ✓" confirmation (green text, 2s, then hide).
- Show inline error on failure. No full-form save button.
- Mobile: `onEndEditing` on `TextInput` = equivalent of web's `onBlur`.

### E.2 Existing settings screen pattern (from `operations.tsx`)
All settings screens use:
- `StyleSheet.create` for styles (no inline style objects)
- `ScrollView` with `contentContainerStyle={{ padding: 16, gap: 8 }}`
- Loading state: `ActivityIndicator size="large" color="#4F46E5"`
- Error state: `<View style={styles.center}><Text style={styles.errorText}>...</Text></View>`
- No `fetch()` — use `apiClient` from `@pilot/shared-api`

### E.3 Nav card pattern (from web `SecurityIndexPage`)
Mobile security index uses `Pressable` cards (same layout as settings index) to navigate to sub-screens.

### E.4 Mobile MFAEnrollmentWizard (from `packages/ui`)
The mobile wizard skeleton already exists. Import:
```typescript
import { MFAEnrollmentWizard } from "@pilot/ui";
```
It supports `totp` and `sms` paths. The `sms` path requires 10DLC-compliant copy in the wrapper screen (see §G.1).

---

## F. Shared Module Interfaces

### F.1 `useMyProfile` — New Mobile Hook

```typescript
// frontend/apps/mobile/features/account-settings/hooks/useMyProfile.ts
import { apiClient } from "@pilot/shared-api";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";

export const MY_PROFILE_QUERY_KEY = ["users", "me", "profile"] as const;

interface UserProfile {
  user_id: string;
  first_name: string;
  last_name: string;
  email: string;
  phone: string | null;
  timezone: string;
  role: string;
  display_name: string;
}

interface UseMyProfileReturn {
  profile: UserProfile | undefined;
  isLoading: boolean;
  isError: boolean;
  updateField: (field: string, value: string | null) => Promise<void>;
  isPending: boolean;
}

export function useMyProfile(): UseMyProfileReturn
```

**Behavior**:
1. `GET /api/v1/users/me` on mount → TanStack Query key `["users", "me", "profile"]`
2. `PATCH /api/v1/users/me` mutation → on success, invalidate query key to refresh
3. `updateField(field, value)` is the save-on-blur handler called by the profile screen

### F.2 `useMfaStatus` — New Mobile Hook

```typescript
// frontend/apps/mobile/features/account-settings/hooks/useMfaStatus.ts
import { apiClient } from "@pilot/shared-api";
import { useQuery } from "@tanstack/react-query";
import type { MFAEnrollmentPath } from "@pilot/ui";

export const MFA_STATUS_QUERY_KEY = ["users", "me", "mfa-status"] as const;

interface MfaStatusResponse {
  enrolled_methods: MFAEnrollmentPath[];
  tenant_policy_required: boolean;
  grace_period_active: boolean;
  grace_ends_at: string | null;
  enforcement_activated: boolean;
}

export function useMfaStatus(): {
  data: MfaStatusResponse | undefined;
  isLoading: boolean;
  isError: boolean;
  refetch: () => void;
}
```

**Behavior**: `GET /api/v1/users/me/mfa-status`, `staleTime: 30_000`.

### F.3 `my-account.tsx` — Profile Screen

**Route**: `/(tabs)/(home)/settings/my-account`

```
┌─────────────────────────────────────────┐
│ ← Settings        My Account            │  ← Stack header (headerShown: true)
├─────────────────────────────────────────┤
│  ▼ Profile                              │
│                                         │
│  First name                            │
│  ┌──────────────────────────────────┐  │
│  │  Tom                    [Saved ✓]│  │
│  └──────────────────────────────────┘  │
│                                         │
│  Last name                             │
│  ┌──────────────────────────────────┐  │
│  │  Lang                            │  │
│  └──────────────────────────────────┘  │
│                                         │
│  Email                                 │
│  ┌──────────────────────────────────┐  │
│  │  tom@example.com  (read-only)    │  │
│  └──────────────────────────────────┘  │
│  Contact support to change your email. │
│                                         │
│  Phone number                          │
│  ┌──────────────────────────────────┐  │
│  │  +1 (303) 555-0001               │  │
│  └──────────────────────────────────┘  │
│                                         │
│  Timezone                              │
│  ┌──────────────────────────────────┐  │
│  │  America/Denver              ▼   │  │  (Picker)
│  └──────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

Fields:
- `first_name`: `TextInput`, `onEndEditing` → `updateField("first_name", value)`
- `last_name`: `TextInput`, `onEndEditing` → `updateField("last_name", value)`
- `email`: `TextInput` read-only (`editable={false}`, `style.opacity=0.5`)
- `phone`: `TextInput`, `keyboardType="phone-pad"`, `onEndEditing` → `updateField("phone", value || null)`
- `timezone`: React Native `Picker` (from `@react-native-picker/picker` — check package.json; if unavailable, use a `Pressable` that presents a modal with `FlatList` of options)

### F.4 `my-account/security.tsx` — Security Index Screen

**Route**: `/(tabs)/(home)/settings/my-account/security`

```
┌─────────────────────────────────────────┐
│ ← My Account      Security              │  ← Stack header
├─────────────────────────────────────────┤
│                                         │
│  ┌──────────────────────────────────┐  │
│  │  🔐 Two-Factor Authentication    │  │  → pushes to .../security/mfa
│  │     1 method enrolled        ›   │  │
│  └──────────────────────────────────┘  │
│                                         │
│  ┌──────────────────────────────────┐  │
│  │  🔑 Password                     │  │  (informational only — web-only action)
│  │     Change password on web   ›   │  │
│  └──────────────────────────────────┘  │
│                                         │
└─────────────────────────────────────────┘
```

**MFA card description**:
- While loading: `"Loading…"`
- Loaded 0 methods: `"No methods enrolled — tap to add"`
- Loaded 1+ methods: `"N method(s) enrolled"`

**Password card**: Pressable, navigates to `Linking.openURL` of the web app `/settings/my-account/password`. Shows `"Manage on web app"` subtitle. This is correct — password change requires browser/web flow.

### F.5 `my-account/security/mfa.tsx` — MFA Enrollment Screen

**Route**: `/(tabs)/(home)/settings/my-account/security/mfa`

```
┌─────────────────────────────────────────┐
│ ← Security   Two-Factor Authentication  │
├─────────────────────────────────────────┤
│                                         │
│  Add an extra layer of security to      │
│  your account.                          │
│                                         │
│  ┌──────────────────────────────────┐  │
│  │  Enrolled methods:               │  │
│  │  • Authenticator app (TOTP)      │  │
│  └──────────────────────────────────┘  │
│  (or "No methods enrolled" if empty)   │
│                                         │
│  [ Add authentication method ]         │ ← shows MFAEnrollmentWizard below
│                                         │
│  ┌──────────────────────────────────┐  │
│  │  MFAEnrollmentWizard (mobile)    │  │
│  │  (when showEnrollWizard=true)    │  │
│  └──────────────────────────────────┘  │
│                                         │
│  ────── SMS / Text Message Note ─────  │
│  📱 SMS verification uses your          │
│  carrier's network. Standard message   │
│  and data rates may apply. By          │
│  enrolling, you agree to receive       │
│  one-time verification codes from      │
│  Pilot for Trades. Reply STOP to any   │
│  message to unenroll.                  │
└─────────────────────────────────────────┘
```

---

## G. Open Questions Resolved

### G.1 — 10DLC-Compliant SMS MFA Copy

**Requirement**: When presenting the SMS enrollment path, the screen must include TCPA/10DLC-compliant disclosure copy because SMS OTP messages will be sent via the Telnyx Campaign A number.

**Resolution**: Display the following static disclosure below the `MFAEnrollmentWizard` whenever the screen is shown (always visible, not conditional on wizard being open):

> "📱 **SMS verification** uses your carrier's standard messaging network. Message and data rates may apply. By enrolling your phone number, you consent to receive one-time verification codes from Pilot for Trades. You can unenroll at any time by returning to this screen and removing the SMS method."

This copy is shown on the MFA screen regardless of which path the user is in — it informs the user before they begin. This matches the TCPA requirement to display consent language before SMS contact.

### G.2 — Timezone Picker Library

**Required pre-work**: React Native Engineer must check:
```bash
grep "react-native-picker\|@react-native-picker" frontend/apps/mobile/package.json
```

**If `@react-native-picker/picker` is present**: Use `<Picker>` component directly.

**If not present**: Use a `Pressable` that opens a `Modal` with a `FlatList` of timezone options. Do NOT add a new npm dependency. The same 8 US timezone options from the web form are sufficient for MVP:
```typescript
const TIMEZONE_OPTIONS = [
  "America/New_York",
  "America/Chicago",
  "America/Denver",
  "America/Los_Angeles",
  "America/Phoenix",
  "America/Anchorage",
  "Pacific/Honolulu",
  "America/Puerto_Rico",
];
```

### G.3 — Password Screen: Web-Only Action

Changing a password requires a browser session (Cognito hosted UI or web app flow). Mobile cannot perform this action natively in MVP.

**Resolution**: The password "card" on the security index screen is a `Pressable` that calls `Linking.openURL('<WEB_APP_URL>/settings/my-account/password')`. The subtitle text: `"Manage on the web app"`. No password form on mobile. This is the correct MVP scope — do not build a native password change form.

The web app URL for deep linking: `https://app.pilotfortrades.com`. This can be hardcoded as a constant in the file — no env variable needed for this MVP.

### G.4 — Gear Icon on Home Tab Header

The `(home)/_layout.tsx` Stack has `headerShown: false` globally (line 16). The gear icon must be added at the **Home screen level** by overriding `navigation.setOptions` in `(home)/index.tsx` with a `headerShown: true` and `headerRight` gear icon button.

**Resolution**: In `(home)/index.tsx`, use `useNavigation()` + `useEffect` to call `navigation.setOptions({ headerShown: true, title: 'Home', headerRight: () => <GearButton /> })`. The `GearButton` component calls `router.push('/(tabs)/(home)/settings/index' as any)` on press.

**Alternative (simpler)**: Update `(home)/_layout.tsx` to set `headerShown: true` on the `index` Stack.Screen only (not globally), with `headerRight`. This is cleaner and avoids the `useEffect` pattern.

**Chosen approach**: Modify `(home)/_layout.tsx` — add `<Stack.Screen name="index" options={{ title: 'Home', headerShown: true, headerRight: () => <GearButton onPress={...} /> }} />`. The `GearButton` is a simple `Pressable` with a gear ⚙ text/icon.

### G.5 — New Routes Must Be Suppressed in Tab Bar

The following new deep settings routes must be added to `(tabs)/_layout.tsx` with `href: null`:
- `(home)/settings/my-account`
- `(home)/settings/my-account/security`
- `(home)/settings/my-account/security/mfa`

### G.6 — Stack.Screen Registrations for Settings Routes

Add the following to `(home)/_layout.tsx`:
```tsx
<Stack.Screen name="settings/index" options={{ title: "Settings", headerShown: true }} />
<Stack.Screen name="settings/my-account" options={{ title: "My Account", headerShown: true }} />
<Stack.Screen name="settings/my-account/security" options={{ title: "Security", headerShown: true }} />
<Stack.Screen name="settings/my-account/security/mfa" options={{ title: "Two-Factor Authentication", headerShown: true }} />
<Stack.Screen name="settings/operations" options={{ title: "Operations", headerShown: true }} />
<Stack.Screen name="settings/sync-storage" options={{ title: "Sync & Storage", headerShown: true }} />
<Stack.Screen name="settings/voice" options={{ title: "Voice & AI", headerShown: true }} />
```

Note: `settings/operations`, `settings/sync-storage`, and `settings/voice` are also registered here — they currently lack Stack headers because they were never added to `(home)/_layout.tsx`. This batch fixes all 7 at once.

---

## H. Surface Mockup Reference

### H.1 Settings Entry Point (existing — no change to content, only navigation fixed)

The existing `settings/index.tsx` is correct. No content changes required. Navigation is fixed by the layout changes in §G.6.

### H.2 My Account Screen Layout

```
┌─────────────────────────────────────────┐
│ ← Settings        My Account            │
├─────────────────────────────────────────┤
│  First name                             │
│  ┌──────────────────────────────────┐   │
│  │  Tom                   ✓ Saved   │   │
│  └──────────────────────────────────┘   │
│                                         │
│  Last name                              │
│  ┌──────────────────────────────────┐   │
│  │  Lang                            │   │
│  └──────────────────────────────────┘   │
│                                         │
│  Email                                  │
│  ┌──────────────────────────────────┐   │
│  │  tom@example.com         (locked)│   │
│  └──────────────────────────────────┘   │
│  Contact support to change your email.  │
│                                         │
│  Phone number                           │
│  ┌──────────────────────────────────┐   │
│  │  +1 (303) 555-0001               │   │
│  └──────────────────────────────────┘   │
│                                         │
│  Timezone                               │
│  ┌──────────────────────────────────┐   │
│  │  America/Denver            ▼     │   │
│  └──────────────────────────────────┘   │
└─────────────────────────────────────────┘
```

### H.3 Security Index Screen Layout

```
┌─────────────────────────────────────────┐
│ ← My Account      Security              │
├─────────────────────────────────────────┤
│                                         │
│  ┌──────────────────────────────────┐   │
│  │ 🔐  Two-Factor Authentication    │   │
│  │     1 method enrolled        ›   │   │
│  └──────────────────────────────────┘   │
│                                         │
│  ┌──────────────────────────────────┐   │
│  │ 🔑  Password                     │   │
│  │     Manage on the web app    ›   │   │
│  └──────────────────────────────────┘   │
│                                         │
└─────────────────────────────────────────┘
```

### H.4 MFA Enrollment Screen Layout

```
┌─────────────────────────────────────────┐
│ ← Security  Two-Factor Authentication   │
├─────────────────────────────────────────┤
│                                         │
│  Add an extra layer of security.        │
│                                         │
│  ┌──────────────────────────────────┐   │
│  │  Enrolled:                       │   │
│  │  • Authenticator app (TOTP)      │   │
│  └──────────────────────────────────┘   │
│  (or "No methods enrolled.")           │
│                                         │
│  [  Add authentication method  ]        │
│                                         │
│  ┌──────────────────────────────────┐   │  ← appears when wizard is open
│  │  MFAEnrollmentWizard (mobile)    │   │
│  └──────────────────────────────────┘   │
│                                         │
│  ──────────────────────────────────    │
│  📱 SMS verification uses your          │
│  carrier's messaging network.           │
│  Message and data rates may apply.      │
│  By enrolling, you consent to receive   │
│  one-time codes from Pilot for Trades.  │
│  Return here to unenroll at any time.   │
└─────────────────────────────────────────┘
```

---

## I. Component Manifest

| Component / Hook / File | Path | Action | Batch |
|:---|:---|:---|:---|
| `(home)/_layout.tsx` | `apps/mobile/app/(tabs)/(home)/_layout.tsx` | **Modify** — add 7 Stack.Screen registrations (settings/*); add headerShown+headerRight to index | MOB-B10 |
| `(tabs)/_layout.tsx` | `apps/mobile/app/(tabs)/_layout.tsx` | **Modify** — add href: null for 3 new deep settings routes | MOB-B10 |
| `(home)/index.tsx` | `apps/mobile/app/(tabs)/(home)/index.tsx` | **Modify** — gear icon `headerRight` via Stack.Screen in layout (no changes to this file if approach G.4 is used — layout handles it) | MOB-B10 |
| `useMyProfile` | `apps/mobile/features/account-settings/hooks/useMyProfile.ts` | **New** — GET + PATCH /api/v1/users/me | MOB-B10 |
| `useMfaStatus` (mobile) | `apps/mobile/features/account-settings/hooks/useMfaStatus.ts` | **New** — GET /api/v1/users/me/mfa-status | MOB-B10 |
| `accountSettingsHandlers.ts` | `apps/mobile/mocks/handlers/accountSettingsHandlers.ts` | **New** — MSW handlers for /users/me and /users/me/mfa-status | MOB-B10 |
| `mocks/handlers/index.ts` | `apps/mobile/mocks/handlers/index.ts` | **Modify** — register accountSettingsHandlers | MOB-B10 |
| `settings/my-account.tsx` | `apps/mobile/app/(tabs)/(home)/settings/my-account.tsx` | **New** — Profile screen | MOB-B10 |
| `settings/my-account/security.tsx` | `apps/mobile/app/(tabs)/(home)/settings/my-account/security.tsx` | **New** — Security index | MOB-B10 |
| `settings/my-account/security/mfa.tsx` | `apps/mobile/app/(tabs)/(home)/settings/my-account/security/mfa.tsx` | **New** — MFA enrollment screen | MOB-B10 |

---

## J. Test Plan

**Test subfolder**: `apps/mobile/__tests__/batch_mob_b10/`

### J.1 Unit Tests

| Test | File | Assertion |
|:---|:---|:---|
| `useMyProfile` loads profile | `useMyProfile.test.ts` | Calls `GET /api/v1/users/me`; returns `profile.first_name`, `profile.email` |
| `useMyProfile` `updateField` fires PATCH | `useMyProfile.test.ts` | `updateField("first_name", "Thomas")` → `PATCH /api/v1/users/me` with `{ first_name: "Thomas" }` |
| `useMfaStatus` loads enrolled methods | `useMfaStatus.test.ts` | Calls `GET /api/v1/users/me/mfa-status`; returns `enrolled_methods` array |
| Profile screen renders all 5 fields | `my-account.integration.test.tsx` | first_name, last_name, email, phone, timezone all visible |
| Email field is read-only | `my-account.integration.test.tsx` | email TextInput `editable={false}` or equivalent |
| Save-on-blur fires PATCH | `my-account.integration.test.tsx` | `fireEvent(firstNameInput, 'endEditing')` → PATCH called |
| "Saved ✓" message appears after save | `my-account.integration.test.tsx` | Success state text visible after PATCH mock resolves |
| Security index renders MFA card | `security.integration.test.tsx` | "Two-Factor Authentication" text + enrolled method count visible |
| MFA card description shows count | `security.integration.test.tsx` | MSW returns 1 method → "1 method enrolled" text |
| Security index renders Password card | `security.integration.test.tsx` | "Password" + "Manage on the web app" text visible |
| MFA screen shows enrolled methods | `mfa.integration.test.tsx` | MSW returns `["totp"]` → "Authenticator app (TOTP)" text visible |
| MFA screen shows "No methods" state | `mfa.integration.test.tsx` | MSW returns `[]` → "No methods enrolled" text |
| "Add authentication method" button shows wizard | `mfa.integration.test.tsx` | Press button → `MFAEnrollmentWizard` rendered |
| SMS disclosure copy visible | `mfa.integration.test.tsx` | "Message and data rates may apply" text visible |
| Settings gear icon navigates to settings | `home-gear.integration.test.tsx` | Press gear icon → `router.push` called with `settings/index` path |

### J.2 Regression Tests

| Test | Assertion |
|---|---|
| Existing settings/operations renders | `MobileOperationsSettings` renders without crash |
| Existing settings/voice renders | `MobileVoiceSettings` renders without crash |
| Existing settings/sync-storage renders | `MobileSyncStorageSettings` renders without crash |
| Home tab still renders | `HomeScreen` renders correctly after layout changes |
| MOB-B9 recurring badge still renders | No regressions from layout changes |

---

## Design Doc Quality Gate Checklist

- [x] All source files read — findings documented in §A
- [x] 3 API endpoints confirmed in openapi_schema_map.md — shapes in §D
- [x] Mobile MFAEnrollmentWizard skeleton confirmed exists — import path documented
- [x] Settings stack registration gap documented and resolved — §G.6
- [x] Tab bar suppression gap documented and resolved — §G.5
- [x] Gear icon wiring decided — §G.4 layout approach
- [x] 10DLC-compliant SMS copy specified — §G.1
- [x] Password card: web-only action — §G.3
- [x] Timezone picker library: verify-first pattern — §G.2
- [x] No new npm dependencies proposed without pre-check gate
- [x] No backend companion required — all endpoints exist
- [x] All new file paths specified in §I component manifest
- [x] Infrastructure constraint: zero cost impact — no new AWS services
- [x] Test plan covers all new screens and hooks — §J
