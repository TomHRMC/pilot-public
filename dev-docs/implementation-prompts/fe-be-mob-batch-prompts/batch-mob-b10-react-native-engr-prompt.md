# Implementation Prompt: MOB-B10 — Mobile Account Settings: Profile + Security + MFA

**Mode**: Pilot React Engineer  
**Batch**: MOB-B10  
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §Section 2 — P1 Beta Launch Blockers  
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-mob-b10-design.md`  
**Estimated session**: 3–4 hours  
**Platform**: Mobile only (`apps/mobile`)  
**Backend companion**: None — all three endpoints confirmed in `backend/openapi_schema_map.md`

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-react-engineer/react-engineer-rules.md`** — in full
- **`dev-docs/architecture-design/batch-designs/batch-mob-b10-design.md`** — every section (A–J)

**Critical rules for this batch:**

- **Rule 1**: No new npm dependencies without checking `frontend/apps/mobile/package.json` first. The timezone picker (§G.2) and any icon lib must be verified before use.
- **Rule 2**: All API calls use `apiClient` from `@pilot/shared-api`. The existing `voice.tsx` settings screen uses raw `fetch()` — this is a **pre-existing violation. Do NOT copy it**. Use `apiClient` for all `/api/v1/...` calls in this batch.
- **Rule 3**: WatermelonDB must be mocked in all tests. Expo Router must be mocked in all screen tests.
- **Rule 4**: Use `.toBeTruthy()` / `not.toBeNull()` in mobile tests — never `toBeInTheDocument()`.
- **Rule 5**: Mobile integration tests go in `__tests__/batch_mob_b10/` — never co-located with source.
- **Rule 6**: `pnpm --filter mobile build` is the mobile type check. There is no `check-types` script.
- **Rule 7**: If ANY test fails — fix it before declaring done.
- **Rule 8**: The 10DLC-compliant SMS disclosure copy in §G.1 of the design doc is **mandatory and verbatim**. Do not omit or reword it on the MFA screen.
- **Rule 9**: Three layout/navigation files need modification (`(home)/_layout.tsx`, `(tabs)/_layout.tsx`, `(home)/index.tsx` or layout-only approach). Read all three before touching any of them.

---

## Design Decisions (Do Not Re-Litigate)

From Design Doc §G — these decisions are final:

| Decision | Outcome | Rationale |
|---|---|---|
| Settings Stack registration | Add all 7 `Stack.Screen` entries to `(home)/_layout.tsx` including existing `operations`, `sync-storage`, `voice` which were also missing | Fixes the navigation regression for all existing settings screens too |
| Gear icon approach | Add `headerRight` to `index` Stack.Screen in `(home)/_layout.tsx` — not via `useEffect` in `(home)/index.tsx` | Cleaner — layout owns the header |
| Password change on mobile | Pressable card → `Linking.openURL('https://app.pilotfortrades.com/settings/my-account/password')` | Password change requires browser/Cognito hosted session |
| LOTO gate: N/A | Not applicable to this batch | — |
| Sessions + Data Export | Not built on mobile in MVP | Web-only flows |

---

## Pre-Work: Establish Regression Baseline

Before touching any file:

```bash
cd <repo>/frontend
pnpm --filter mobile test 2>&1 | tail -8
```

Record the exact counts. These must still pass at the end of the batch.

> **If any tests are already failing before you start**: Either confirm with Tom that it is a known accepted failure, or fix it before touching batch files. Do NOT start implementation work while tests are in an unexplained failed state.

---

## Pre-Work: Sync API Types

```bash
cd <repo>/frontend
pnpm sync-api-types
```

This regenerates `packages/shared-types/src/api-schema.d.ts` from the live OpenAPI spec. All backend payload types must come from `@pilot/shared-types`.

---

## Pre-Work: Verify Endpoints

For each new hook in this batch, verify the endpoint exists before writing any code:

```bash
grep -A 5 "users/me" backend/openapi_schema_map.md | head -40
```

Verified endpoints for this batch:

| Hook | Endpoint | Verified |
|---|---|---|
| `useMyProfile` (GET) | `GET /api/v1/users/me` | ✅ Confirmed in openapi_schema_map.md |
| `useMyProfile` (PATCH) | `PATCH /api/v1/users/me` | ✅ Confirmed in openapi_schema_map.md |
| `useMfaStatus` | `GET /api/v1/users/me/mfa-status` | ✅ Confirmed (used by web MFA page) |

**If any endpoint is NOT in `openapi_schema_map.md` → STOP. Do not invent a URL. Ask Tom.**

---

## Pre-Work: Read These Source Files

Read each of these with `read_file` before writing any code:

```
frontend/apps/mobile/app/(tabs)/(home)/_layout.tsx
  ← why: you will add 7 Stack.Screen entries + index headerRight here

frontend/apps/mobile/app/(tabs)/_layout.tsx
  ← why: you will add 3 href: null suppressions for new settings routes

frontend/apps/mobile/app/(tabs)/(home)/index.tsx
  ← why: understand existing screen structure before evaluating if any changes needed

frontend/apps/mobile/app/(tabs)/(home)/settings/index.tsx
  ← why: understand existing settings menu — this file stays unchanged

frontend/apps/mobile/app/(tabs)/(home)/settings/operations.tsx
  ← why: pattern reference for the screen layout and StyleSheet approach

frontend/apps/mobile/app/(tabs)/(home)/settings/voice.tsx
  ← why: pattern reference — BUT note: it uses raw fetch(). Do NOT copy that. Use apiClient.

frontend/apps/mobile/mocks/handlers/index.ts
  ← why: understand how to register the new accountSettingsHandlers

frontend/packages/ui/src/index.ts
  ← why: confirm MFAEnrollmentWizard (mobile) export name and MFAEnrollmentPath type
```

Also run these before assuming paths:

```bash
# Confirm MFAEnrollmentWizard export from @pilot/ui
grep -n "MFAEnrollmentWizard\|MFAEnrollmentPath" frontend/packages/ui/src/index.ts

# Check if @react-native-picker/picker is installed
grep "react-native-picker\|@react-native-picker" frontend/apps/mobile/package.json

# Confirm apiClient import works in mobile
grep -rn "from \"@pilot/shared-api\"" frontend/apps/mobile/features/ | head -5

# Confirm style-constants file location
ls frontend/apps/mobile/constants/style-constants.ts 2>/dev/null || echo "NOT FOUND"

# Find existing mobile MSW handlers
find frontend/apps/mobile/mocks/handlers -name "*.ts" | head -20
```

---

## Context: What This Batch Delivers

| Task | Files Created/Modified | Notes |
|---|---|---|
| Fix navigation plumbing | `(home)/_layout.tsx`, `(tabs)/_layout.tsx` | All settings routes now work |
| Gear icon on Home header | `(home)/_layout.tsx` | Routes to settings/index |
| Profile screen | `settings/my-account.tsx` | GET+PATCH /api/v1/users/me, save-on-blur |
| Security index screen | `settings/my-account/security.tsx` | Nav cards: MFA + Password (web link) |
| MFA screen | `settings/my-account/security/mfa.tsx` | MFAEnrollmentWizard + 10DLC SMS copy |
| Mobile hooks | `features/account-settings/hooks/useMyProfile.ts`, `useMfaStatus.ts` | TanStack Query |
| MSW handlers | `mocks/handlers/accountSettingsHandlers.ts` + register in `index.ts` | Dev + test support |

---

## STEP 1 — Fix Navigation Plumbing

### 1a. Update `(home)/_layout.tsx`

Read the file first. Then add all missing Stack.Screen registrations + headerRight gear icon on the Home screen.

**Goal**: Every settings screen must be registered in the Stack so it gets a proper header and back button.

```tsx
// Approximate — read the file first and adjust to match the existing structure
import { Stack } from "expo-router";
import React from "react";
import { Pressable, Text } from "react-native";
import { useRouter } from "expo-router";

function GearButton() {
  const router = useRouter();
  return (
    <Pressable
      onPress={() => router.push("/(tabs)/(home)/settings/index" as any)}
      style={{ paddingRight: 16, paddingVertical: 8 }}
      hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
      accessibilityLabel="Open settings"
      accessibilityRole="button"
      testID="home-gear-button"
    >
      <Text style={{ fontSize: 20 }}>⚙️</Text>
    </Pressable>
  );
}

export default function HomeLayout() {
  return (
    <Stack screenOptions={{ headerShown: false }}>
      {/* Home screen — now shows header with gear icon */}
      <Stack.Screen
        name="index"
        options={{
          title: "Home",
          headerShown: true,
          headerRight: () => <GearButton />,
        }}
      />
      {/* Existing voice routes */}
      <Stack.Screen name="voice/index" options={{ title: "Voice Sessions", headerShown: true }} />
      <Stack.Screen name="voice/[sessionId]" options={{ title: "Voice Session", headerShown: false }} />
      {/* Settings stack — all 7 routes registered */}
      <Stack.Screen name="settings/index" options={{ title: "Settings", headerShown: true }} />
      <Stack.Screen name="settings/my-account" options={{ title: "My Account", headerShown: true }} />
      <Stack.Screen name="settings/my-account/security" options={{ title: "Security", headerShown: true }} />
      <Stack.Screen name="settings/my-account/security/mfa" options={{ title: "Two-Factor Authentication", headerShown: true }} />
      <Stack.Screen name="settings/operations" options={{ title: "Operations", headerShown: true }} />
      <Stack.Screen name="settings/sync-storage" options={{ title: "Sync & Storage", headerShown: true }} />
      <Stack.Screen name="settings/voice" options={{ title: "Voice & AI", headerShown: true }} />
    </Stack>
  );
}
```

> **Adjust to match what you actually find in the file.** The `GearButton` component can be defined in the same file or extracted to a feature component. Keep it simple — a `Pressable` with an emoji or icon character is sufficient for MVP.

### 1b. Update `(tabs)/_layout.tsx`

Read the file first. Add `href: null` suppression for the 3 new deep settings routes:

```tsx
{/* MOB-B10: New settings deep routes — suppress from tab bar */}
<Tabs.Screen name="(home)/settings/my-account" options={{ href: null }} />
<Tabs.Screen name="(home)/settings/my-account/security" options={{ href: null }} />
<Tabs.Screen name="(home)/settings/my-account/security/mfa" options={{ href: null }} />
```

Add these alongside the existing suppression block. Read the existing patterns first to match the exact format.

**After Step 1 — verify no TypeScript errors before continuing:**
```bash
cd <repo>/frontend
pnpm --filter mobile build 2>&1 | tail -10
```

---

## STEP 2 — Create Mobile Hooks

### 2a. `useMyProfile.ts`

Create: `frontend/apps/mobile/features/account-settings/hooks/useMyProfile.ts`

```typescript
// Read packages/shared-types/src/api-schema.d.ts after pnpm sync-api-types to get
// the actual UserProfile type. Use it instead of a hand-written interface.
// If the type is not yet exported, write a temporary stub marked:
//   // TODO: delete when pnpm sync-api-types delivers UserProfile type
import { apiClient } from "@pilot/shared-api";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";

export const MY_PROFILE_QUERY_KEY = ["users", "me", "profile"] as const;

// Adjust field names to match what pnpm sync-api-types returns for /api/v1/users/me
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

export function useMyProfile() {
  const queryClient = useQueryClient();

  const { data: profile, isLoading, isError } = useQuery({
    queryKey: MY_PROFILE_QUERY_KEY,
    queryFn: async () => {
      const res = await apiClient.get("/api/v1/users/me");
      return res.data as UserProfile;
    },
    staleTime: 60_000,
  });

  const { mutateAsync: updateProfileMutation, isPending, error: updateError } =
    useMutation({
      mutationFn: async (fields: Partial<UserProfile>) => {
        const res = await apiClient.patch("/api/v1/users/me", fields);
        return res.data as UserProfile;
      },
      onSuccess: () => {
        void queryClient.invalidateQueries({ queryKey: MY_PROFILE_QUERY_KEY });
      },
    });

  async function updateField(field: string, value: string | null) {
    await updateProfileMutation({ [field]: value } as Partial<UserProfile>);
  }

  return { profile, isLoading, isError, updateField, isPending, updateError };
}
```

### 2b. `useMfaStatus.ts`

Create: `frontend/apps/mobile/features/account-settings/hooks/useMfaStatus.ts`

```typescript
import { apiClient } from "@pilot/shared-api";
import { useQuery } from "@tanstack/react-query";
import type { MFAEnrollmentPath } from "@pilot/ui";
// Verify this import compiles — if MFAEnrollmentPath is not exported from @pilot/ui,
// check packages/ui/src/index.ts and use the correct export name.

export const MFA_STATUS_QUERY_KEY = ["users", "me", "mfa-status"] as const;

interface MfaStatusResponse {
  enrolled_methods: MFAEnrollmentPath[];
  tenant_policy_required: boolean;
  grace_period_active: boolean;
  grace_ends_at: string | null;
  enforcement_activated: boolean;
}

export function useMfaStatus() {
  return useQuery({
    queryKey: MFA_STATUS_QUERY_KEY,
    queryFn: async () => {
      const res = await apiClient.get("/api/v1/users/me/mfa-status");
      return res.data as MfaStatusResponse;
    },
    staleTime: 30_000,
  });
}
```

---

## STEP 3 — Create MSW Handlers

### 3a. Create `accountSettingsHandlers.ts`

Create: `frontend/apps/mobile/mocks/handlers/accountSettingsHandlers.ts`

Read `frontend/apps/mobile/mocks/handlers/index.ts` first to understand the existing handler registration pattern.

```typescript
import { http, HttpResponse } from "msw";

const MOCK_PROFILE = {
  user_id: "00000000-0000-0000-0000-000000000001",
  first_name: "Tom",
  last_name: "Lang",
  email: "dev@pilot.local",
  phone: "+13035550001",
  timezone: "America/Denver",
  role: "owner",
  display_name: "Tom Lang",
};

const MOCK_MFA_STATUS = {
  enrolled_methods: [] as string[],
  tenant_policy_required: false,
  grace_period_active: false,
  grace_ends_at: null,
  enforcement_activated: false,
};

export const accountSettingsHandlers = [
  http.get("/api/v1/users/me", () => HttpResponse.json(MOCK_PROFILE)),
  http.patch("/api/v1/users/me", async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>;
    return HttpResponse.json({ ...MOCK_PROFILE, ...body });
  }),
  http.get("/api/v1/users/me/mfa-status", () =>
    HttpResponse.json(MOCK_MFA_STATUS),
  ),
];
```

### 3b. Register in `mocks/handlers/index.ts`

Read the current `index.ts` first. Add:

```typescript
import { accountSettingsHandlers } from "./accountSettingsHandlers";

export const handlers = [
  ...existingHandlers,
  ...accountSettingsHandlers, // ← MOB-B10: profile + MFA status endpoints
];
```

> **This step is mandatory.** Without registration in `index.ts`, the handlers are never loaded — tests will fail with unhandled request warnings.

---

## STEP 4 — Create Profile Screen (`settings/my-account.tsx`)

Create: `frontend/apps/mobile/app/(tabs)/(home)/settings/my-account.tsx`

Read `settings/operations.tsx` first for the exact StyleSheet pattern to mirror.

Key implementation notes:
- **Save-on-blur**: `TextInput` uses `onEndEditing` prop (React Native equivalent of `onBlur`)
- **Saved confirmation**: `useState<Record<string, 'saved' | 'error' | null>>({})` per field, 2-second timeout then clear
- **Email field**: `editable={false}` + muted background color + hint text "Contact support to change your email address."
- **Phone field**: `keyboardType="phone-pad"`. Call `updateField("phone", value || null)` — pass `null` if cleared
- **Timezone**: First check if `@react-native-picker/picker` is installed. If yes, use `<Picker>`. If no, implement a `Pressable` that opens a `Modal` with a `FlatList` of the 8 US timezone options (see design doc §G.2). Do NOT add the dependency without verification.
- **Loading state**: `<ActivityIndicator size="large" color="#4F46E5" />` in centered `<View>`
- **Error state**: `<Text style={styles.errorText}>Failed to load profile. Please try again.</Text>` in centered `<View>`

```tsx
/**
 * My Account — Profile Settings (MOB-B10)
 * Route: /(tabs)/(home)/settings/my-account
 */
import React, { useState } from "react";
import {
  ScrollView,
  Text,
  TextInput,
  View,
  StyleSheet,
  ActivityIndicator,
} from "react-native";
import { useMyProfile } from "../../../../features/account-settings/hooks/useMyProfile";
// Adjust relative path depth as needed after reading the existing settings files

export default function MyAccountScreen() {
  const { profile, isLoading, isError, updateField, isPending } = useMyProfile();
  const [saveStatus, setSaveStatus] = useState<Record<string, "saved" | "error" | null>>({});

  const handleEndEditing = async (field: string, value: string) => {
    try {
      await updateField(field, value || (field === "phone" ? null : value));
      setSaveStatus((prev) => ({ ...prev, [field]: "saved" }));
      setTimeout(
        () => setSaveStatus((prev) => ({ ...prev, [field]: null })),
        2000,
      );
    } catch {
      setSaveStatus((prev) => ({ ...prev, [field]: "error" }));
    }
  };

  if (isError) {
    return (
      <View style={styles.center}>
        <Text style={styles.errorText}>Failed to load profile. Please try again.</Text>
      </View>
    );
  }

  if (isLoading || !profile) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#4F46E5" />
      </View>
    );
  }

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
      testID="my-account-screen"
    >
      {/* First name */}
      {/* Last name */}
      {/* Email (read-only) */}
      {/* Phone */}
      {/* Timezone */}
      {/* Implement each field following the save-on-blur pattern above */}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#F9FAFB" },
  content: { padding: 16, gap: 16 },
  center: { flex: 1, justifyContent: "center", alignItems: "center" },
  label: { fontSize: 13, fontWeight: "500", color: "#374151", marginBottom: 4 },
  input: {
    borderWidth: 1,
    borderColor: "#D1D5DB",
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 10,
    fontSize: 15,
    color: "#111827",
    backgroundColor: "#FFFFFF",
  },
  inputDisabled: {
    backgroundColor: "#F3F4F6",
    color: "#9CA3AF",
  },
  savedText: { fontSize: 12, color: "#059669", marginTop: 2 },
  errorText: { fontSize: 14, color: "#DC2626" },
  hint: { fontSize: 12, color: "#6B7280", marginTop: 2 },
});
```

> **Implement all 5 fields.** The snippet above is a skeleton — flesh it out fully.

---

## STEP 5 — Create Security Index Screen (`settings/my-account/security.tsx`)

Create: `frontend/apps/mobile/app/(tabs)/(home)/settings/my-account/security.tsx`

Key implementation notes:
- Two Pressable nav cards: MFA (pushes to `.../mfa`) and Password (opens web URL)
- MFA card description: load from `useMfaStatus` — show method count
- Password card: `Linking.openURL('https://app.pilotfortrades.com/settings/my-account/password')`
- Card layout mirrors the existing settings index screen `Pressable` style (icon + label + chevron)

```tsx
/**
 * Security Settings Index (MOB-B10)
 * Route: /(tabs)/(home)/settings/my-account/security
 */
import React from "react";
import { ScrollView, Text, Pressable, View, StyleSheet, Linking } from "react-native";
import { useRouter } from "expo-router";
import { useMfaStatus } from "../../../../../features/account-settings/hooks/useMfaStatus";

export default function SecurityIndexScreen() {
  const router = useRouter();
  const { data: mfaStatus, isLoading: mfaLoading } = useMfaStatus();

  const mfaDescription = mfaLoading
    ? "Loading…"
    : `${mfaStatus?.enrolled_methods.length ?? 0} method${
        (mfaStatus?.enrolled_methods.length ?? 0) !== 1 ? "s" : ""
      } enrolled`;

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
      testID="security-index-screen"
    >
      {/* MFA Card */}
      <Pressable
        style={({ pressed }) => [styles.card, pressed && styles.cardPressed]}
        onPress={() => router.push("/(tabs)/(home)/settings/my-account/security/mfa" as any)}
        accessibilityRole="button"
        accessibilityLabel="Two-Factor Authentication settings"
        testID="mfa-nav-card"
      >
        <Text style={styles.cardIcon}>🔐</Text>
        <View style={styles.cardText}>
          <Text style={styles.cardTitle}>Two-Factor Authentication</Text>
          <Text style={styles.cardSubtitle}>{mfaDescription}</Text>
        </View>
        <Text style={styles.chevron}>›</Text>
      </Pressable>

      {/* Password Card — web link */}
      <Pressable
        style={({ pressed }) => [styles.card, pressed && styles.cardPressed]}
        onPress={() =>
          Linking.openURL("https://app.pilotfortrades.com/settings/my-account/password")
        }
        accessibilityRole="link"
        accessibilityLabel="Change password on web app"
        testID="password-nav-card"
      >
        <Text style={styles.cardIcon}>🔑</Text>
        <View style={styles.cardText}>
          <Text style={styles.cardTitle}>Password</Text>
          <Text style={styles.cardSubtitle}>Manage on the web app</Text>
        </View>
        <Text style={styles.chevron}>›</Text>
      </Pressable>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#F9FAFB" },
  content: { padding: 16, gap: 8 },
  card: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#FFFFFF",
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 14,
    borderWidth: 1,
    borderColor: "#E5E7EB",
    marginBottom: 4,
    gap: 12,
  },
  cardPressed: { backgroundColor: "#F3F4F6" },
  cardIcon: { fontSize: 18 },
  cardText: { flex: 1 },
  cardTitle: { fontSize: 15, fontWeight: "500", color: "#111827" },
  cardSubtitle: { fontSize: 12, color: "#6B7280", marginTop: 2 },
  chevron: { fontSize: 20, color: "#9CA3AF" },
});
```

---

## STEP 6 — Create MFA Enrollment Screen (`settings/my-account/security/mfa.tsx`)

Create: `frontend/apps/mobile/app/(tabs)/(home)/settings/my-account/security/mfa.tsx`

Key implementation notes:
- Confirm `MFAEnrollmentWizard` mobile export from `@pilot/ui` before importing (Step 1 pre-work)
- Show enrolled methods list (or "No methods enrolled" if empty)
- "Add authentication method" button → `useState` toggles wizard visibility
- On wizard `onComplete` → `setShowWizard(false)` + `refetch()` MFA status
- **MANDATORY**: Display the 10DLC SMS disclosure copy below the wizard section (always visible)

```tsx
/**
 * MFA Enrollment Screen (MOB-B10)
 * Route: /(tabs)/(home)/settings/my-account/security/mfa
 *
 * 10DLC COMPLIANCE NOTE: The SMS disclosure text in this file is mandatory
 * per TCPA requirements for any screen that initiates SMS verification.
 * Do NOT remove or abbreviate this text.
 */
import React, { useState } from "react";
import {
  ScrollView,
  Text,
  Pressable,
  View,
  StyleSheet,
  ActivityIndicator,
} from "react-native";
import { MFAEnrollmentWizard } from "@pilot/ui";
// If this import fails, check packages/ui/src/index.ts for the correct export name.
import { useMfaStatus, MFA_STATUS_QUERY_KEY } from "../../../../../features/account-settings/hooks/useMfaStatus";
import { useQueryClient } from "@tanstack/react-query";

export default function MfaScreen() {
  const { data: mfaStatus, isLoading, isError, refetch } = useMfaStatus();
  const queryClient = useQueryClient();
  const [showWizard, setShowWizard] = useState(false);

  const handleComplete = () => {
    setShowWizard(false);
    void queryClient.invalidateQueries({ queryKey: MFA_STATUS_QUERY_KEY });
  };

  if (isError) {
    return (
      <View style={styles.center}>
        <Text style={styles.errorText}>
          Could not load MFA status. Please try again.
        </Text>
      </View>
    );
  }

  if (isLoading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#4F46E5" />
      </View>
    );
  }

  const enrolledMethods = mfaStatus?.enrolled_methods ?? [];

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
      testID="mfa-screen"
    >
      <Text style={styles.subtitle}>
        Add an extra layer of security to your account.
      </Text>

      {/* Enrolled methods */}
      <View style={styles.enrolledBox} testID="enrolled-methods-box">
        {enrolledMethods.length === 0 ? (
          <Text style={styles.enrolledText}>No methods enrolled.</Text>
        ) : (
          enrolledMethods.map((method) => (
            <Text key={method} style={styles.enrolledText}>
              • {method === "totp" ? "Authenticator app (TOTP)" : method === "sms" ? "SMS / Text message" : method}
            </Text>
          ))
        )}
      </View>

      {/* Add method button */}
      {!showWizard && (
        <Pressable
          style={({ pressed }) => [styles.addButton, pressed && styles.addButtonPressed]}
          onPress={() => setShowWizard(true)}
          accessibilityRole="button"
          testID="add-mfa-method-btn"
        >
          <Text style={styles.addButtonText}>Add authentication method</Text>
        </Pressable>
      )}

      {/* MFAEnrollmentWizard */}
      {showWizard && (
        <View style={styles.wizardContainer} testID="mfa-wizard-container">
          <MFAEnrollmentWizard
            onComplete={handleComplete}
            onCancel={() => setShowWizard(false)}
            enrolledMethods={enrolledMethods}
            forceFlow={false}
            testID="mfa-enrollment-wizard"
          />
        </View>
      )}

      {/* ─── 10DLC-COMPLIANT SMS DISCLOSURE — MANDATORY — DO NOT REMOVE OR EDIT ─── */}
      <View style={styles.disclosureBox} testID="sms-disclosure">
        <Text style={styles.disclosureText}>
          📱{" "}
          <Text style={styles.disclosureBold}>SMS verification</Text> uses your
          carrier's standard messaging network. Message and data rates may apply.
          By enrolling your phone number, you consent to receive one-time
          verification codes from Pilot for Trades. You can unenroll at any time
          by returning to this screen and removing the SMS method.
        </Text>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#F9FAFB" },
  content: { padding: 16, gap: 16 },
  center: { flex: 1, justifyContent: "center", alignItems: "center" },
  subtitle: { fontSize: 14, color: "#6B7280" },
  enrolledBox: {
    backgroundColor: "#FFFFFF",
    borderRadius: 8,
    padding: 14,
    borderWidth: 1,
    borderColor: "#E5E7EB",
  },
  enrolledText: { fontSize: 14, color: "#374151" },
  addButton: {
    backgroundColor: "#4F46E5",
    borderRadius: 8,
    paddingVertical: 12,
    paddingHorizontal: 16,
    alignItems: "center",
  },
  addButtonPressed: { opacity: 0.85 },
  addButtonText: { color: "#FFFFFF", fontSize: 15, fontWeight: "500" },
  wizardContainer: {
    borderRadius: 12,
    borderWidth: 1,
    borderColor: "#E5E7EB",
    backgroundColor: "#FFFFFF",
    overflow: "hidden",
  },
  disclosureBox: {
    backgroundColor: "#EEF2FF",
    borderRadius: 8,
    padding: 14,
    borderWidth: 1,
    borderColor: "#C7D2FE",
    marginTop: 8,
  },
  disclosureText: { fontSize: 13, color: "#4338CA", lineHeight: 20 },
  disclosureBold: { fontWeight: "600" },
  errorText: { fontSize: 14, color: "#DC2626" },
});
```

---

## STEP 7 — Write Tests

Create all test files in: `frontend/apps/mobile/__tests__/batch_mob_b10/`

### Required Mock Setup (apply to every test file)

```typescript
// Expo Router mock — required for every screen test
const mockPush = jest.fn();
jest.mock("expo-router", () => ({
  useRouter: () => ({ push: mockPush, back: jest.fn(), replace: jest.fn() }),
  useLocalSearchParams: () => ({}),
  router: { push: mockPush, back: jest.fn() },
  Link: ({ children }: { children: React.ReactNode }) => children,
}));
beforeEach(() => { mockPush.mockClear(); });

// WatermelonDB mock — required for every mobile test
jest.mock("../../../database", () => ({
  database: {
    write: jest.fn((fn: () => unknown) => fn()),
    get: jest.fn(() => ({
      create: jest.fn((fn: (r: Record<string, unknown>) => void) => {
        const record = { id: "mock-id", localSyncStatus: "pending" };
        fn(record);
        return Promise.resolve(record);
      }),
    })),
  },
}));

// TanStack Query wrapper — always retry: false
function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}

// MSW server setup
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
const server = setupServer(...accountSettingsHandlers);
beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
```

### Test Files Required

**`useMyProfile.test.ts`**
- `useMyProfile` loads profile from `GET /api/v1/users/me` — returns `first_name`, `email`
- `updateField("first_name", "Thomas")` fires `PATCH /api/v1/users/me` with `{ first_name: "Thomas" }`
- `updateField("phone", "")` fires `PATCH` with `{ phone: null }` (empty string → null)

**`useMfaStatus.test.ts`**
- Returns `enrolled_methods: []` when server returns empty array
- Returns `enrolled_methods: ["totp"]` when server returns one method

**`my-account.integration.test.tsx`**
- Screen renders with `testID="my-account-screen"` (not 404)
- All 5 field labels visible: "First name", "Last name", "Email", "Phone number", "Timezone"
- First name input pre-populated from MSW mock data ("Tom")
- Email field is not editable (`editable={false}` or equivalent — verify rendered state)
- `endEditing` on first name input fires PATCH with updated value
- "Saved" confirmation text visible after successful PATCH

**`security.integration.test.tsx`**
- Screen renders with `testID="security-index-screen"` (not 404)
- "Two-Factor Authentication" text visible
- MFA card shows "0 methods enrolled" when MSW returns empty array
- "Password" card and "Manage on the web app" subtitle visible
- Press MFA card → `router.push` called with `.../security/mfa` path

**`mfa.integration.test.tsx`**
- Screen renders with `testID="mfa-screen"` (not 404)
- "No methods enrolled." text visible when MSW returns empty `enrolled_methods`
- Enrolled method "Authenticator app (TOTP)" visible when MSW returns `["totp"]`
- "Add authentication method" button visible
- Press button → `testID="mfa-wizard-container"` appears
- SMS disclosure `testID="sms-disclosure"` is always visible (present both before and after pressing button)
- "Message and data rates may apply" text visible in disclosure

**`home-gear.integration.test.tsx`**
- Home screen renders
- Gear button `testID="home-gear-button"` is present
- Press gear button → `router.push` called with settings path

### Run tests frequently during development:

```bash
cd <repo>/frontend

# Run only MOB-B10 tests:
pnpm --filter mobile test -- __tests__/batch_mob_b10/ 2>&1 | tail -15

# Run full mobile suite:
pnpm --filter mobile test 2>&1 | tail -8
```

Fix every failure before moving forward — there is no "pre-existing" exception.

---

## Final Verification

### Phase 1 — Targeted (run during development after each step group)

```bash
cd <repo>/frontend
pnpm --filter mobile test -- __tests__/batch_mob_b10/ 2>&1 | tail -15
pnpm --filter mobile build 2>&1 | tail -10
```

### Phase 2 — Full (run once at the very end before DoD sign-off)

```bash
cd <repo>/frontend && echo "=== UI - Type Check ===" && pnpm --filter @pilot/ui check-types && echo "=== Web - Type Check ===" && pnpm --filter web check-types && echo "=== Mobile - Type Check ===" && pnpm --filter mobile build && echo "=== UI - Lint ===" && pnpm --filter @pilot/ui lint && echo "=== Web - Lint ===" && pnpm --filter web lint && echo "=== Mobile - Lint ===" && pnpm --filter mobile lint && echo "=== TYPE+LINT PASS ===" && echo "=== UI - Tests ===" && pnpm --filter @pilot/ui test 2>&1 | tail -6 && echo "=== Web - Tests ===" && pnpm --filter web test 2>&1 | tail -6 && echo "=== Mobile - Tests ===" && pnpm --filter mobile test 2>&1 | tail -8 && echo "=== MVP FINAL VERIFICATION COMPLETE ==="
```

> **`pnpm --filter mobile build` = mobile type check.** There is no separate `check-types` script for mobile.

> **Any failure must be fixed before the batch is declared done.**

---

## Definition of Done — MOB-B10

Update `dev-docs/analysis/pilot-launch-plan.md` §Section 2 when each item is done:

- [ ] Regression baseline captured before any file changes
- [ ] `pnpm sync-api-types` run — no new type errors
- [ ] Design doc read in full before writing any code
- [ ] All mandatory source files read before modifying
- [ ] All 3 API endpoint URLs verified in `openapi_schema_map.md`
- [ ] **STEP 1a**: `(home)/_layout.tsx` updated — 7 Stack.Screen registrations + index `headerRight` gear icon
- [ ] **STEP 1b**: `(tabs)/_layout.tsx` updated — 3 `href: null` suppressions for new settings routes
- [ ] **STEP 1 verify**: `pnpm --filter mobile build` passes with no type errors before continuing
- [ ] **STEP 2a**: `features/account-settings/hooks/useMyProfile.ts` created — GET + PATCH /api/v1/users/me
- [ ] **STEP 2b**: `features/account-settings/hooks/useMfaStatus.ts` created — GET /api/v1/users/me/mfa-status
- [ ] **STEP 3a**: `mocks/handlers/accountSettingsHandlers.ts` created — 3 MSW handlers
- [ ] **STEP 3b**: `accountSettingsHandlers` registered in `mocks/handlers/index.ts` barrel
- [ ] **STEP 4**: `settings/my-account.tsx` created — all 5 fields, save-on-blur, loading/error states
- [ ] **STEP 5**: `settings/my-account/security.tsx` created — MFA nav card + Password web-link card
- [ ] **STEP 6**: `settings/my-account/security/mfa.tsx` created — enrolled methods display, wizard toggle, **10DLC SMS disclosure copy present verbatim**
- [ ] Gear ⚙ icon on Home tab header routes to `settings/index`
- [ ] Save-on-blur fires `PATCH /api/v1/users/me` with only the changed field
- [ ] "Saved ✓" inline confirmation appears after successful save, clears after 2 seconds
- [ ] Email field is read-only (`editable={false}`)
- [ ] Password card opens web URL via `Linking.openURL`
- [ ] SMS disclosure text visible on MFA screen (both before and after opening wizard)
- [ ] MSW handlers registered in `index.ts` barrel — verified no double-registration
- [ ] `useMyProfile.test.ts` — all assertions pass
- [ ] `useMfaStatus.test.ts` — all assertions pass
- [ ] `my-account.integration.test.tsx` — all assertions pass
- [ ] `security.integration.test.tsx` — all assertions pass
- [ ] `mfa.integration.test.tsx` — all assertions pass (including SMS disclosure assertion)
- [ ] `home-gear.integration.test.tsx` — gear button present + routes correctly
- [ ] Zero TypeScript errors (`pnpm --filter mobile build` clean)
- [ ] Zero ESLint lint warnings
- [ ] Existing settings screens (operations, voice, sync-storage) still render — no regressions
- [ ] **Phase 2 FULL verification command passes** (`=== MVP FINAL VERIFICATION COMPLETE ===`):
  ```bash
  cd <repo>/frontend && echo "=== UI - Type Check ===" && pnpm --filter @pilot/ui check-types && echo "=== Web - Type Check ===" && pnpm --filter web check-types && echo "=== Mobile - Type Check ===" && pnpm --filter mobile build && echo "=== UI - Lint ===" && pnpm --filter @pilot/ui lint && echo "=== Web - Lint ===" && pnpm --filter web lint && echo "=== Mobile - Lint ===" && pnpm --filter mobile lint && echo "=== TYPE+LINT PASS ===" && echo "=== UI - Tests ===" && pnpm --filter @pilot/ui test 2>&1 | tail -6 && echo "=== Web - Tests ===" && pnpm --filter web test 2>&1 | tail -6 && echo "=== Mobile - Tests ===" && pnpm --filter mobile test 2>&1 | tail -8 && echo "=== MVP FINAL VERIFICATION COMPLETE ==="
  ```

---

## Completion Summary

After all Definition of Done items are complete:

1. Add a **Completion Summary** subsection to `dev-docs/analysis/pilot-launch-plan.md` **Appendix B** using the format below.
2. Mark the MOB-B10 entry in Section 2 as ✅ with the completion date.
3. Mark the **Beta Launch Readiness Gate** entry for MOB-B10 as ✅ in Section 5 (if added there).

```markdown
### MOB-B10 — Mobile Account Settings (Profile + Security + MFA): Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot React Engineer
**Baseline**: X passed, Y failed (mobile)
**Final**: X+N passed, Y failed (+N new tests)

#### What Was Accomplished

- Fixed settings navigation plumbing — 7 Stack.Screen entries + 3 tab bar suppressions
- Added gear ⚙ icon to Home tab header routing to settings/index
- Built My Account profile screen (GET + PATCH /api/v1/users/me, save-on-blur, 5 fields)
- Built Security index screen (MFA nav card + Password web-link card)
- Built MFA enrollment screen (MFAEnrollmentWizard + 10DLC-compliant SMS disclosure)
- Created useMyProfile + useMfaStatus hooks with TanStack Query
- Created MSW accountSettingsHandlers (3 handlers) registered in index.ts

#### Files Changed / Created

| File | Action |
|---|---|
| `apps/mobile/app/(tabs)/(home)/_layout.tsx` | Updated — 7 Stack.Screen registrations + headerRight gear icon |
| `apps/mobile/app/(tabs)/_layout.tsx` | Updated — 3 href: null suppressions |
| `apps/mobile/features/account-settings/hooks/useMyProfile.ts` | Created |
| `apps/mobile/features/account-settings/hooks/useMfaStatus.ts` | Created |
| `apps/mobile/mocks/handlers/accountSettingsHandlers.ts` | Created |
| `apps/mobile/mocks/handlers/index.ts` | Updated — registered accountSettingsHandlers |
| `apps/mobile/app/(tabs)/(home)/settings/my-account.tsx` | Created |
| `apps/mobile/app/(tabs)/(home)/settings/my-account/security.tsx` | Created |
| `apps/mobile/app/(tabs)/(home)/settings/my-account/security/mfa.tsx` | Created |
| `apps/mobile/__tests__/batch_mob_b10/useMyProfile.test.ts` | Created |
| `apps/mobile/__tests__/batch_mob_b10/useMfaStatus.test.ts` | Created |
| `apps/mobile/__tests__/batch_mob_b10/my-account.integration.test.tsx` | Created |
| `apps/mobile/__tests__/batch_mob_b10/security.integration.test.tsx` | Created |
| `apps/mobile/__tests__/batch_mob_b10/mfa.integration.test.tsx` | Created |
| `apps/mobile/__tests__/batch_mob_b10/home-gear.integration.test.tsx` | Created |

#### Tests Added

| Test File | Type | Tests | All Pass |
|---|---|---|---|
| `__tests__/batch_mob_b10/useMyProfile.test.ts` | Unit | 3 | ✅ |
| `__tests__/batch_mob_b10/useMfaStatus.test.ts` | Unit | 2 | ✅ |
| `__tests__/batch_mob_b10/my-account.integration.test.tsx` | Integration | 6 | ✅ |
| `__tests__/batch_mob_b10/security.integration.test.tsx` | Integration | 4 | ✅ |
| `__tests__/batch_mob_b10/mfa.integration.test.tsx` | Integration | 6 | ✅ |
| `__tests__/batch_mob_b10/home-gear.integration.test.tsx` | Integration | 2 | ✅ |
```
