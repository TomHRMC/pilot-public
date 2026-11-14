# Implementation Prompt: MOB-B8 Part B — Background Sync: Push Token Registration + OS Background Tasks + Settings UI

**Mode**: Pilot React Engineer  
**Batch**: MOB-B8 Part B (Background-Sync-B1 — Mobile)  
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §Phase 1 — Batch 9 (Background-Sync-B1)  
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-mob-b8-design.md`  
**Estimated session**: 3–4 hours  
**Platform**: Mobile only (`apps/mobile`)  
**Backend companion**: MOB-B8 Part A (Python Engineer) — **must be complete and `python export_openapi_json.py` run before starting this prompt**

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-react-engineer/react-engineer-rules.md`** — in full
- **`dev-docs/architecture-design/batch-designs/batch-mob-b8-design.md`** — every section (A–I)

**Critical rules for this batch:**

- **Rule 1**: Run `pnpm sync-api-types` **first**, before writing any hook. The push token registration endpoint and background-sync-policy endpoint were just added by Part A. Types come from `@pilot/shared-types`.
- **Rule 2**: Before writing any hook or API call, verify the endpoint exists in `backend/openapi_schema_map.md`. If it is NOT there → **STOP and ask Tom**.
- **Rule 3**: All API calls use `apiClient` from `@pilot/shared-api`. `fetch()` is permanently banned for `/api/v1/...` calls.
- **Rule 4**: No new npm dependencies without first checking `apps/mobile/package.json`. `expo-task-manager` and `expo-background-fetch` **require Tom approval before installation** (per architecture rules §9.8). See the approval gate below.
- **Rule 5**: WatermelonDB must be mocked in all tests — never write real DB operations in tests.
- **Rule 6**: Expo Router must be mocked in all screen tests (`jest.mock("expo-router", ...)`).
- **Rule 7**: Background task handler must complete within 30 seconds — iOS BGAppRefreshTask hard limit.
- **Rule 8**: All mobile integration tests go in `__tests__/batch_mob_b8/` — never co-located with source.
- **Rule 9**: If ANY test fails during your work — even pre-existing — you must fix it before declaring done.
- **Rule 10**: `pnpm --filter mobile build` is the mobile type-check command — there is no `check-types` script for mobile.

---

## ⚠️ Native Dependency Approval Gate

`expo-task-manager` and `expo-background-fetch` are native Expo dependencies that require explicit Tom approval before installation.

**Before running `pnpm --filter mobile add expo-task-manager expo-background-fetch`:**

1. Confirm with Tom that these two packages are approved for this batch
2. Tom's approval is documented in the batch description in `pilot-launch-plan.md` §Phase 1 Batch 9

> Per `.roo/rules-pilot-architect/pilot-architect-rules.md §9.8`: "Native Expo dependencies require explicit founder approval before being added."

If Tom has not explicitly approved these packages for this batch → **STOP and ask before installing**.

---

## Design Decisions (Do Not Re-Litigate)

From Design Doc §G — these decisions are final:

| Decision | Outcome | Rationale |
|---|---|---|
| Background sync scope | Data queue only (no photos, no voice audio) | Battery concern; PRD §3.15 explicit scope |
| Push delivery | Expo Push Notification API (reuse from backend `notification_worker.py`) | Already in stack; no new FCM/APNs SDKs |
| Silent push iOS | `_contentAvailable: true`, no title/body | Wakes app without showing a notification |
| Silent push Android | `priority: "high"`, data-only | FCM high-priority data message wakes app |
| Conflict handling in background | Auto-resolve only; defer tech-resolvable/owner-escalation to foreground | Cannot show conflict UI when app is closed |
| User toggle | `background_sync_enabled` user override stored client-side (AsyncStorage/SecureStore) in MVP | Server-side user override is post-MVP |
| WiFi-only enforcement | Client-side in background task handler via `@react-native-community/netinfo` | Already installed from foreground sync |

---

## Pre-Work: Establish Regression Baseline

Before touching any file:

```bash
cd <repo>/frontend

# Mobile baseline
pnpm --filter mobile test 2>&1 | tail -8
```

Record the exact count. Fix any pre-existing failures or confirm with Tom before starting.

---

## Pre-Work: Sync API Types

```bash
cd <repo>/frontend
pnpm sync-api-types
```

This picks up the `POST /api/v1/mobile/push-tokens/register` and `GET /api/v1/settings/background-sync-policy` endpoints added by Part A.

> If `pnpm sync-api-types` fails: confirm Part A is complete and `python export_openapi_json.py` was run. If the backend server is not running → note the affected hooks, write stubs marked `// TODO: delete when pnpm sync-api-types delivers this type`.

---

## Pre-Work: Verify Endpoints

```bash
# Verify both endpoints from Part A are in the spec
grep -A 5 "background-sync-policy" backend/openapi_schema_map.md
grep -A 5 "push-tokens/register" backend/openapi_schema_map.md
```

Verified endpoints for this batch:
| Hook | Endpoint | Must confirm |
|---|---|---|
| `usePushTokenRegistration` | `POST /api/v1/mobile/push-tokens/register` | ✅ Confirm in openapi_schema_map.md |
| `useSyncPolicy` | `GET /api/v1/settings/background-sync-policy` | ✅ Confirm in openapi_schema_map.md |

---

## Pre-Work: Read These Source Files

Read each with `read_file` before writing any code:

```
frontend/apps/mobile/app/_layout.tsx                          ← WHY: understand root layout structure before wiring hooks
frontend/apps/mobile/database/sync/orchestrator.ts            ← WHY: understand sync() function signature + how to call it from background
frontend/apps/mobile/hooks/                                   ← WHY: list existing hooks to avoid naming conflicts
frontend/apps/mobile/features/settings/                       ← WHY: understand existing settings screen structure
frontend/apps/mobile/mocks/handlers/index.ts                  ← WHY: understand how to register new MSW handlers
frontend/apps/mobile/package.json                             ← WHY: confirm expo-task-manager, expo-background-fetch, @react-native-community/netinfo presence
frontend/apps/mobile/app.json                                 ← WHY: understand existing permissions before adding background permissions
```

Also run:
```bash
# Find existing hooks
find frontend/apps/mobile/hooks -name "*.ts" | head -20
find frontend/apps/mobile/features/settings -name "*.ts" -o -name "*.tsx" | head -20

# Confirm netinfo is installed
grep "netinfo" frontend/apps/mobile/package.json

# Confirm expo-notifications is installed (push token retrieval)
grep "expo-notifications" frontend/apps/mobile/package.json

# Confirm database orchestrator location
find frontend/apps/mobile/database/sync -name "*.ts" | head -10

# Find existing mock handler files
find frontend/apps/mobile/mocks/handlers -name "*.ts" | head -20
```

---

## Context: What This Batch Does

| # | Step | File(s) | Notes |
|---|---|---|---|
| B1 | Sync API types | — | Picks up Part A endpoints |
| B2 | Approval gate + install `expo-task-manager` + `expo-background-fetch` | `package.json`, `app.json` | Tom approval required first |
| B3 | Create `hooks/usePushTokenRegistration.ts` | New file | Registers device push token on app start |
| B4 | Wire push token registration into `app/_layout.tsx` | Existing file | One-time call on mount |
| B5 | Create `lib/backgroundSync.ts` | New file | Task name constant + handler that calls orchestrator |
| B6 | Register background task in `app/_layout.tsx` | Existing file | `TaskManager.defineTask` + `BackgroundFetch.registerTaskAsync` |
| B7 | Create `features/settings/hooks/useSyncPolicy.ts` | New file | Fetches background-sync-policy |
| B8 | Create `features/settings/components/BackgroundSyncSettingsSection.tsx` | New file | Settings UI — 1 editable toggle + 3 read-only values |
| B9 | Wire settings section into existing settings screen | Existing file | Find the right settings screen to add it |
| B10 | Create MSW handlers + register in index.ts | New + existing | Cover both new endpoints |
| B11 | Write tests + full verification | `__tests__/batch_mob_b8/` | |

---

## STEP 1 — Install Dependencies (After Tom Approval)

After Tom approves `expo-task-manager` and `expo-background-fetch`:

```bash
cd <repo>/frontend
pnpm --filter mobile add expo-task-manager expo-background-fetch
```

Update `frontend/apps/mobile/app.json` to add background permissions. Read `app.json` first, then add:

```json
{
  "expo": {
    "ios": {
      "infoPlist": {
        "UIBackgroundModes": ["fetch", "remote-notification"]
      }
    },
    "android": {
      "permissions": [
        "RECEIVE_BOOT_COMPLETED",
        "FOREGROUND_SERVICE"
      ]
    }
  }
}
```

> Read the existing `app.json` first. Merge carefully — do NOT overwrite existing iOS `infoPlist` or Android `permissions` entries. Add only these entries if they don't exist.

---

## STEP 2 — Create `hooks/usePushTokenRegistration.ts`

This hook runs once on app mount to register the device's push token with the backend. It is safe to call on every app open — the backend endpoint uses an upsert.

```typescript
// frontend/apps/mobile/hooks/usePushTokenRegistration.ts
// Read existing hooks in this directory for the established import/pattern style

import { useEffect } from "react";
import * as Notifications from "expo-notifications";    // already installed
import * as Device from "expo-device";                  // check if installed; use Device.deviceName for device identification
import { apiClient } from "@pilot/shared-api";
import AsyncStorage from "@react-native-async-storage/async-storage";  // confirm installed

const DEVICE_ID_KEY = "pilot_device_id";

async function getOrCreateDeviceId(): Promise<string> {
  // Retrieve or generate a stable device UUID stored in AsyncStorage
  const existing = await AsyncStorage.getItem(DEVICE_ID_KEY);
  if (existing) return existing;
  const newId = `${Date.now()}-${Math.random().toString(36).slice(2)}`;  // simple stable ID
  await AsyncStorage.setItem(DEVICE_ID_KEY, newId);
  return newId;
}

export function usePushTokenRegistration(): void {
  useEffect(() => {
    const register = async () => {
      try {
        // 1. Get Expo push token (expo-notifications already handles FCM/APNs)
        const { status } = await Notifications.getPermissionsAsync();
        if (status !== "granted") return;  // no token if no permission — skip silently

        const tokenData = await Notifications.getExpoPushTokenAsync();
        const pushToken = tokenData.data;
        const deviceId = await getOrCreateDeviceId();
        const platform = Device.osName?.toLowerCase().includes("ios") ? "ios" : "android";

        // 2. Register with backend (upsert — safe to call every app open)
        await apiClient.post("/api/v1/mobile/push-tokens/register", {
          device_id: deviceId,
          platform,
          push_token: pushToken,
          app_version: undefined,   // optional
          os_version: Device.osVersion ?? undefined,
        });
      } catch (err) {
        // Silent failure — push registration is best-effort; never block app startup
        console.warn("[usePushTokenRegistration] failed:", err);
      }
    };
    register();
  }, []);  // runs once on mount
}
```

> **Adjust to match actual file patterns.** Read the existing hooks before finalizing import paths. If `expo-device` is not installed, use a simpler platform detection: `import { Platform } from "react-native"; const platform = Platform.OS;`

---

## STEP 3 — Wire Push Token Registration in `app/_layout.tsx`

Read `app/_layout.tsx` before modifying. Add:

```typescript
// In the root layout component (adjust to actual file structure)
import { usePushTokenRegistration } from "../hooks/usePushTokenRegistration";

export default function RootLayout() {
  usePushTokenRegistration();  // ← add this line in the body (before return)
  // ... rest of existing layout
}
```

**Intermediate check:**
```bash
pnpm --filter mobile test 2>&1 | tail -5
```

---

## STEP 4 — Create `lib/backgroundSync.ts`

```typescript
// frontend/apps/mobile/lib/backgroundSync.ts
// Background task handler — calls the existing sync orchestrator

import * as TaskManager from "expo-task-manager";
import * as BackgroundFetch from "expo-background-fetch";
import NetInfo from "@react-native-community/netinfo";   // already installed
// Import the sync function from the orchestrator — verify exact export name
// e.g.: import { sync } from "../database/sync/orchestrator";

export const BACKGROUND_SYNC_TASK_NAME = "PILOT_BACKGROUND_SYNC";

// Maximum time budget: 25 seconds (iOS BGAppRefreshTask limit is 30s; leave 5s buffer)
const BACKGROUND_SYNC_TIMEOUT_MS = 25_000;

TaskManager.defineTask(BACKGROUND_SYNC_TASK_NAME, async () => {
  try {
    // 1. Check connectivity — skip if offline
    const netState = await NetInfo.fetch();
    if (!netState.isConnected) {
      return BackgroundFetch.BackgroundFetchResult.NoData;
    }

    // 2. Check WiFi-only setting (client-side enforcement)
    //    Read background_sync_wifi_only from AsyncStorage (cached from last useSyncPolicy call)
    //    If wifi_only = true AND connection type != wifi → skip
    // Note: For MVP, we check the cached value. If cache miss: default to allowing sync.

    // 3. Check battery floor (client-side enforcement)
    //    For MVP: skip battery check if expo-battery is not installed.
    //    Post-MVP: add expo-battery and enforce background_sync_battery_floor_pct.

    // 4. Call the sync orchestrator with a timeout
    await Promise.race([
      // Verify the exact sync() function name/import path from orchestrator.ts
      sync(),  // existing WatermelonDB sync function
      new Promise((_, reject) =>
        setTimeout(() => reject(new Error("background sync timeout")), BACKGROUND_SYNC_TIMEOUT_MS)
      ),
    ]);

    return BackgroundFetch.BackgroundFetchResult.NewData;
  } catch (err) {
    console.warn("[BACKGROUND_SYNC] error:", err);
    return BackgroundFetch.BackgroundFetchResult.Failed;
  }
});
```

> **Read `database/sync/orchestrator.ts` first** to find the exact exported function name and signature. It may be `sync()`, `runSync()`, `triggerSync()`, or another name. Use what's actually exported.

---

## STEP 5 — Register Background Task in `app/_layout.tsx`

Add background task registration to the root layout. Read the existing `_layout.tsx` again — find the right place to add registration (typically in a `useEffect` on mount, after checking permissions).

```typescript
import * as BackgroundFetch from "expo-background-fetch";
import * as TaskManager from "expo-task-manager";
import "../lib/backgroundSync";  // ← import the file to register the task definition

// In root layout useEffect (or a dedicated hook):
useEffect(() => {
  const registerBackgroundSync = async () => {
    try {
      const isRegistered = await TaskManager.isTaskRegisteredAsync(BACKGROUND_SYNC_TASK_NAME);
      if (!isRegistered) {
        await BackgroundFetch.registerTaskAsync(BACKGROUND_SYNC_TASK_NAME, {
          minimumInterval: 15 * 60,  // 15 minutes minimum (OS enforces this regardless)
          stopOnTerminate: false,    // continue after app is terminated (Android)
          startOnBoot: true,         // register on device boot (Android)
        });
      }
    } catch (err) {
      console.warn("[BackgroundSync] registration failed:", err);
      // Silent failure — background sync is enhancement, not critical path
    }
  };
  registerBackgroundSync();
}, []);
```

**Intermediate check:**
```bash
pnpm --filter mobile build 2>&1 | tail -10
pnpm --filter mobile test 2>&1 | tail -5
```

---

## STEP 6 — Create `features/settings/hooks/useSyncPolicy.ts`

```typescript
// frontend/apps/mobile/features/settings/hooks/useSyncPolicy.ts
// Read features/settings/ to understand existing hook patterns before writing

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";

interface BackgroundSyncPolicy {
  background_sync_enabled: boolean;
  background_sync_wifi_only: boolean;
  background_sync_battery_floor_pct: number;
  background_sync_push_interval_minutes: number;
}

const SYNC_POLICY_QUERY_KEY = ["background-sync-policy"] as const;

export function useSyncPolicy() {
  return useQuery<BackgroundSyncPolicy>({
    queryKey: SYNC_POLICY_QUERY_KEY,
    queryFn: async () => {
      const response = await apiClient.get<BackgroundSyncPolicy>(
        "/api/v1/settings/background-sync-policy"
      );
      return response.data;
    },
    staleTime: 5 * 60 * 1000,  // 5 minutes — setting rarely changes mid-session
    retry: false,
    // On error: return safe defaults (don't block settings screen)
  });
}
```

---

## STEP 7 — Create `features/settings/components/BackgroundSyncSettingsSection.tsx`

```tsx
// frontend/apps/mobile/features/settings/components/BackgroundSyncSettingsSection.tsx
// Per design doc §H.1 mockup

import React, { useState } from "react";
import { View, Text, Switch, StyleSheet } from "react-native";
import { useSyncPolicy } from "../hooks/useSyncPolicy";
// Import style constants from constants/style-constants.ts — never hardcode hex or px values

interface BackgroundSyncSettingsSectionProps {}

export function BackgroundSyncSettingsSection({}: BackgroundSyncSettingsSectionProps) {
  const { data: policy, isLoading } = useSyncPolicy();

  // User-level override — stored locally in MVP
  const [userEnabledOverride, setUserEnabledOverride] = useState<boolean>(
    policy?.background_sync_enabled ?? true
  );

  if (isLoading) {
    // Render a simple skeleton or nothing while loading
    return null;
  }

  return (
    <View style={styles.section} testID="background-sync-settings-section">
      <Text style={styles.sectionTitle}>Background Sync</Text>
      <Text style={styles.sectionDescription}>
        Keep your data current even when the app is closed.
      </Text>

      {/* Editable: user can toggle background sync on/off */}
      <View style={styles.row}>
        <Text style={styles.rowLabel}>Background Sync</Text>
        <Switch
          testID="background-sync-toggle"
          value={userEnabledOverride}
          onValueChange={(val) => {
            setUserEnabledOverride(val);
            // TODO post-MVP: persist to server via PUT /api/v1/settings/user-overrides
            // For MVP: client-side state only (resets on app restart — acceptable)
          }}
        />
      </View>

      {/* Read-only: controlled by owner */}
      <View style={styles.row}>
        <Text style={styles.rowLabel}>WiFi Only</Text>
        <Text style={styles.rowValue} testID="wifi-only-value">
          {policy?.background_sync_wifi_only ? "On" : "Off"}
        </Text>
      </View>

      <View style={styles.row}>
        <Text style={styles.rowLabel}>Battery Floor</Text>
        <Text style={styles.rowValue} testID="battery-floor-value">
          {policy?.background_sync_battery_floor_pct ?? 20}%
        </Text>
      </View>

      <View style={styles.row}>
        <Text style={styles.rowLabel}>Sync Interval</Text>
        <Text style={styles.rowValue} testID="sync-interval-value">
          {policy?.background_sync_push_interval_minutes ?? 5} min
        </Text>
      </View>

      {/* Owner-controlled note */}
      <Text style={styles.ownerNote}>
        WiFi and battery settings are controlled by your account owner.
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  // Use style tokens from constants/style-constants.ts — do not hardcode values
  // Example:
  section: { paddingHorizontal: 16, paddingVertical: 12 },
  sectionTitle: { fontSize: 16, fontWeight: "600", marginBottom: 4 },
  sectionDescription: { fontSize: 14, marginBottom: 12 },
  row: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", paddingVertical: 8 },
  rowLabel: { fontSize: 15 },
  rowValue: { fontSize: 15 },
  ownerNote: { fontSize: 12, marginTop: 8 },
});
```

> **Read `constants/style-constants.ts` first.** Replace hardcoded values above with the actual design tokens from that file. If a token doesn't exist: use a reasonable value and add a `// TODO: use token` comment.

---

## STEP 8 — Wire Settings Section into Existing Settings Screen

Find the existing settings screen(s):
```bash
find frontend/apps/mobile/features/settings -name "*.tsx" | head -20
find frontend/apps/mobile/app -name "*setting*" -o -name "*Setting*" | head -10
```

Add `<BackgroundSyncSettingsSection />` to the appropriate settings screen (likely the main settings/general section). Read the file first to understand the existing layout structure.

---

## STEP 9 — Create MSW Handlers

Create `frontend/apps/mobile/mocks/handlers/backgroundSyncHandlers.ts`:

```typescript
// frontend/apps/mobile/mocks/handlers/backgroundSyncHandlers.ts
import { http, HttpResponse } from "msw";

export const MOCK_SYNC_POLICY = {
  background_sync_enabled: true,
  background_sync_wifi_only: false,
  background_sync_battery_floor_pct: 20,
  background_sync_push_interval_minutes: 5,
};

export const MOCK_PUSH_TOKEN_RESPONSE = {
  id: "mock-token-id-001",
  device_id: "mock-device-id-001",
  registered_at: "2026-07-12T12:00:00Z",
  last_seen_at: "2026-07-12T12:00:00Z",
};

export const backgroundSyncHandlers = [
  http.get("/api/v1/settings/background-sync-policy", () =>
    HttpResponse.json(MOCK_SYNC_POLICY)
  ),
  http.post("/api/v1/mobile/push-tokens/register", async () =>
    HttpResponse.json(MOCK_PUSH_TOKEN_RESPONSE, { status: 200 })
  ),
];
```

Register in `frontend/apps/mobile/mocks/handlers/index.ts`:
```typescript
import { backgroundSyncHandlers } from "./backgroundSyncHandlers";

export const handlers = [
  ...existingHandlers,
  ...backgroundSyncHandlers,  // ← ADD THIS
];
```

> **Read the existing `index.ts` first** to ensure you don't create a duplicate handler for any path already registered.

---

## STEP 10 — Write Tests

All tests go in `frontend/apps/mobile/__tests__/batch_mob_b8/`. Do NOT co-locate with source.

### Test file 1: `__tests__/batch_mob_b8/push_token_registration.test.tsx`

```typescript
// jest-expo preset — use jest.mock(), not vi.mock()
// Use @testing-library/react-native
// Required mocks:
jest.mock("expo-router", () => ({ /* standard expo-router mock */ }));
jest.mock("expo-notifications", () => ({
  getPermissionsAsync: jest.fn().mockResolvedValue({ status: "granted" }),
  getExpoPushTokenAsync: jest.fn().mockResolvedValue({ data: "ExponentPushToken[test]" }),
}));
jest.mock("expo-device", () => ({ osName: "iOS", osVersion: "17.4" }));
jest.mock("@react-native-async-storage/async-storage", () => ({
  getItem: jest.fn().mockResolvedValue(null),
  setItem: jest.fn().mockResolvedValue(undefined),
}));
```

Tests (4 total):
1. `test_push_token_registration_calls_api` — renders a component that uses `usePushTokenRegistration`; MSW handler is called with correct payload (`platform: "ios"`, `push_token: "ExponentPushToken[test]"`)
2. `test_push_token_skips_when_no_permission` — `getPermissionsAsync` returns `{ status: "denied" }`; API call NOT made
3. `test_push_token_silent_on_error` — MSW returns 500; component renders without crash (silent failure)
4. `test_push_token_device_id_is_stable` — `AsyncStorage.getItem` returns an existing ID; that same ID is sent in API payload

### Test file 2: `__tests__/batch_mob_b8/sync_policy_hook.test.tsx`

Tests (4 total):
1. `test_sync_policy_returns_data` — `useSyncPolicy` returns the MSW mock data correctly
2. `test_sync_policy_loading_state` — hook returns `isLoading: true` before data arrives
3. `test_sync_policy_error_state` — MSW returns 500; hook returns `isError: true` (but does NOT throw)
4. `test_sync_policy_stale_time` — query key is `['background-sync-policy']`

### Test file 3: `__tests__/batch_mob_b8/background_sync_settings.integration.test.tsx`

```typescript
// Integration test — renders BackgroundSyncSettingsSection with MSW mock
```

Tests (5 total):
1. `test_settings_section_renders` — `<BackgroundSyncSettingsSection />` renders without crash
2. `test_settings_shows_defaults` — renders with MSW mock data; `testID="wifi-only-value"` shows "Off"; `testID="battery-floor-value"` shows "20%"; `testID="sync-interval-value"` shows "5 min"
3. `test_settings_toggle_enabled` — pressing the toggle changes the displayed state
4. `test_settings_shows_owner_note` — "controlled by your account owner" text is present
5. `test_settings_policy_error_graceful` — MSW returns 500; section renders without crash (does not show error screen)

---

## Test Requirements

Per `apps/mobile/README-adding-tests.md`:

- All integration tests in `__tests__/batch_mob_b8/` — NOT co-located with source
- Use `jest.mock()` (not `vi.mock()`)
- Use `.toBeTruthy()` / `not.toBeNull()` (not `toBeInTheDocument()` — that's jsdom/web only)
- Use `fireEvent.press()` for user interactions
- WatermelonDB mock required for any test that imports from `../database`
- Expo Router mock required for any screen-level test
- **TanStack Query setup**: always use `retry: false`

```typescript
// TanStack Query wrapper for mobile tests
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

**MSW setup for mobile tests**:
```typescript
import { setupServer } from "msw/node";
import { backgroundSyncHandlers } from "../../mocks/handlers/backgroundSyncHandlers";

const server = setupServer(...backgroundSyncHandlers);
beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
```

---

## Final Verification

> ❌ **BANNED COMMAND**: `npx vitest run` — **NEVER use this**. Mobile uses Jest/jest-expo.

### Phase 1 — Targeted tests (after each step)

```bash
cd <repo>/frontend

# Run batch tests only
pnpm --filter mobile test -- __tests__/batch_mob_b8/ 2>&1 | tail -10

# Type check (mobile type check = build)
pnpm --filter mobile build 2>&1 | tail -10
```

Fix any failure before moving to the next step.

### Phase 2 — Full verification (run once at the very end)

```bash
cd <repo>/frontend && pnpm --filter @pilot/ui check-types && pnpm --filter web check-types && pnpm --filter mobile build && pnpm --filter @pilot/ui lint && pnpm --filter web lint && pnpm --filter mobile lint && echo "=== TYPE+LINT PASS ===" && pnpm --filter @pilot/ui test 2>&1 | tail -6 && pnpm --filter web test 2>&1 | tail -6 && pnpm --filter mobile test 2>&1 | tail -8 && echo "=== MVP FINAL VERIFICATION COMPLETE ==="
```

> Any failure in either phase must be fixed before declaring done.

---

## Definition of Done — MOB-B8 Part B

Update `dev-docs/analysis/pilot-launch-plan.md` §Phase 1 Batch 9 when each item is done:

- [ ] Pre-modification regression baseline captured — zero pre-existing mobile failures (or confirmed with Tom)
- [ ] `pnpm sync-api-types` run — no new type errors
- [ ] Design doc `batch-mob-b8-design.md` fully read before writing code
- [ ] All mandatory source files read before modifying (`_layout.tsx`, `orchestrator.ts`, `settings/`, `mocks/handlers/index.ts`, `package.json`, `app.json`)
- [ ] Both new endpoints confirmed in `openapi_schema_map.md` (`/background-sync-policy`, `/push-tokens/register`)
- [ ] **Tom approval obtained** for `expo-task-manager` and `expo-background-fetch` before installation
- [ ] **STEP 1**: `expo-task-manager` + `expo-background-fetch` installed; `app.json` background permissions added
- [ ] **STEP 2**: `hooks/usePushTokenRegistration.ts` created — calls register endpoint on mount, silent failure on error
- [ ] **STEP 3**: `usePushTokenRegistration` wired into `app/_layout.tsx`
- [ ] **STEP 4**: `lib/backgroundSync.ts` created — `BACKGROUND_SYNC_TASK_NAME` + `TaskManager.defineTask` handler with 25s timeout
- [ ] **STEP 5**: Background task registered in `app/_layout.tsx` — `BackgroundFetch.registerTaskAsync` + import of backgroundSync.ts
- [ ] **STEP 6**: `features/settings/hooks/useSyncPolicy.ts` created — `useQuery` with `staleTime: 5min`, `retry: false`
- [ ] **STEP 7**: `features/settings/components/BackgroundSyncSettingsSection.tsx` created — 1 editable toggle + 3 read-only values + owner note
- [ ] **STEP 8**: Settings section wired into existing settings screen
- [ ] **STEP 9**: `mocks/handlers/backgroundSyncHandlers.ts` created; registered in `mocks/handlers/index.ts`
- [ ] All 3 new MSW handlers registered in barrel `index.ts`
- [ ] Integration tests pass in `__tests__/batch_mob_b8/` (13 total across 3 files)
- [ ] Zero TypeScript errors (`pnpm --filter mobile build` passes)
- [ ] Zero ESLint warnings
- [ ] No regressions in mobile test suite
- [ ] **Phase 2 FULL verification command passes** (`=== MVP FINAL VERIFICATION COMPLETE ===`):
  ```bash
  cd <repo>/frontend && pnpm --filter @pilot/ui check-types && pnpm --filter web check-types && pnpm --filter mobile build && pnpm --filter @pilot/ui lint && pnpm --filter web lint && pnpm --filter mobile lint && echo "=== TYPE+LINT PASS ===" && pnpm --filter @pilot/ui test 2>&1 | tail -6 && pnpm --filter web test 2>&1 | tail -6 && pnpm --filter mobile test 2>&1 | tail -8 && echo "=== MVP FINAL VERIFICATION COMPLETE ==="
  ```
- [ ] Final test count (before → after) documented
- [ ] Completion Summary added to `pilot-launch-plan.md` §Phase 1 Batch 9

---

## Completion Summary

After all Definition of Done items are complete, add a Completion Summary to `dev-docs/analysis/pilot-launch-plan.md` §Phase 1 Batch 9 — Background-Sync-B1 using the format below:

```markdown
### MOB-B8 Part B — Background Sync Mobile: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot React Engineer
**Baseline**: X passed (mobile)
**Final**: X+N passed (+N new tests)

#### What Was Accomplished

- `usePushTokenRegistration` hook — registers Expo push token on app start via POST /api/v1/mobile/push-tokens/register
- `lib/backgroundSync.ts` — PILOT_BACKGROUND_SYNC task registers with expo-background-fetch; calls sync orchestrator with 25s timeout
- Background task registered in root layout — BGAppRefreshTask (iOS) + WorkManager (Android) via `BackgroundFetch.registerTaskAsync`
- `useSyncPolicy` hook + `BackgroundSyncSettingsSection` component — displays 4 settings with 1 editable toggle
- MSW handlers created for both endpoints; registered in handlers/index.ts

#### Files Changed / Created

| File | Action |
|---|---|
| `apps/mobile/hooks/usePushTokenRegistration.ts` | Created |
| `apps/mobile/lib/backgroundSync.ts` | Created |
| `apps/mobile/app/_layout.tsx` | Updated — hook wired + background task registered |
| `apps/mobile/features/settings/hooks/useSyncPolicy.ts` | Created |
| `apps/mobile/features/settings/components/BackgroundSyncSettingsSection.tsx` | Created |
| `apps/mobile/mocks/handlers/backgroundSyncHandlers.ts` | Created |
| `apps/mobile/mocks/handlers/index.ts` | Updated — backgroundSyncHandlers registered |
| `apps/mobile/app.json` | Updated — background permissions |
| `apps/mobile/package.json` | Updated — expo-task-manager + expo-background-fetch |

#### Tests Added

| Test File | Type | Tests | All Pass |
|---|---|---|---|
| `__tests__/batch_mob_b8/push_token_registration.test.tsx` | Unit/Integration | 4 | ✅ |
| `__tests__/batch_mob_b8/sync_policy_hook.test.tsx` | Unit | 4 | ✅ |
| `__tests__/batch_mob_b8/background_sync_settings.integration.test.tsx` | Integration | 5 | ✅ |
```
