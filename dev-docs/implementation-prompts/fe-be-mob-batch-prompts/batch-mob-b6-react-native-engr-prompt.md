# Implementation Prompt: MOB-B6 — GPS Clock-In + Photo Upload + Structured Messages

**Mode**: Pilot React Native Engineer  
**Batch**: MOB-B6  
**Source plan**: `dev-docs/analysis/pilot-app-pre-wkstm-3-prep-plan.md` §Phase 0.9 — MOB-B6  
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-mob-b6-design.md`  
**Estimated session**: 4–6 hours  
**Platform**: Mobile only (`apps/mobile`)  
**Backend companion**: None — all endpoints exist. Prerequisites: B17 Part A complete (adds `job-expense-categories` endpoint).

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-react-engineer/react-engineer-rules.md`** — in full (applies to React Native too — rules §8.2 mobile section applies here)
- **`dev-docs/architecture-design/batch-designs/batch-mob-b6-design.md`** — every section (A–I)

**Critical rules for this batch:**

- **Rule 1.1**: Before hooking up any new API call, verify the endpoint in `backend/openapi_schema_map.md`. The `job-expense-categories` endpoint was added in B17 Part A — confirm it appears.
- **Rule 1.3**: Run `pnpm sync-api-types` before starting — check which voice types can now be sourced from `@pilot/shared-types` instead of `types-stub.ts`.
- **Rule 8**: Check `apps/mobile/package.json` before installing ANY dependency. `expo-location` and `expo-image-picker` are NOT yet in the file — install via `pnpm --filter mobile add` (see Step 1).
- **Rule 9 (mobile)**: WatermelonDB must be mocked in ALL tests. Real DB writes are banned in tests.
- **Rule 16 (mobile)**: Expo Router must be mocked in ALL screen tests that use navigation.
- **GPS must never block clock-in**: If GPS permission is denied or capture fails, clock-in proceeds without coordinates. GPS is additive — never a blocker.
- **`types-stub.ts` partial replacement only**: Replace imports that have available types in `@pilot/shared-types` after `pnpm sync-api-types`. Keep stubs for any types not yet delivered. Mark kept stubs with `// TODO: remove when pnpm sync-api-types delivers this type`.
- **expo-location / expo-image-picker approval**: Tom has approved these dependencies by directing this batch. Proceed with installation.

---

## Design Decisions (Do Not Re-Litigate)

From Design Doc §G:

| Decision | Outcome | Rationale |
|---|---|---|
| GPS permission timing | Request on first clock-in attempt, not at app launch | Contextual permission at point of use |
| GPS failure handling | Soft failure — proceed without coordinates | GPS must never block a tech from clocking in |
| Photo source | Both camera AND library options | Show action sheet with "Take Photo" / "Choose from Library" |
| `JobEtcStatusCard` | Live mode fetches projected-margin; snapshot renders from payload | Matches PRD §3.13 live/snapshot mode pattern |
| `ConflictSummaryCard` | Simple summary card + "Resolve on web →" deep link | Full conflict resolution is web-only per PRD |
| Expense categories | API call after B17; fall back to hardcoded if API fails | Resilient: hardcoded fallback ensures expense logging always works |

---

## Pre-Work: Establish Regression Baseline

```bash
cd <repo>/frontend
pnpm --filter mobile test 2>&1 | tail -8
```

Record exact count. Fix pre-existing failures or confirm with Tom.

---

## Pre-Work: Sync API Types

```bash
cd <repo>/frontend
pnpm sync-api-types
```

Check which voice types are now available from `@pilot/shared-types`:
```bash
# Look for SessionResponse, SessionMessageResponse, etc. in generated types
grep -n "Session\|VoiceSession" frontend/packages/shared-types/src/api-schema.d.ts | head -20
```

---

## Pre-Work: Verify Endpoints

```bash
# 1. Confirm job-expense-categories endpoint (from B17 Part A)
grep -A 5 "job-expense-categories" backend/openapi_schema_map.md | head -10

# 2. Check if time entry create supports GPS fields
python3 -c "
import json
spec = json.load(open('backend/openapi.json'))
te_schema = spec.get('components', {}).get('schemas', {}).get('JobTimeEntryCreate', {})
props = te_schema.get('properties', {})
print('Time entry fields:', list(props.keys()))
"

# 3. Find the sync trigger API in mobile
grep -rn "SyncOrchestrator\|syncNow\|triggerSync\|sync()" frontend/apps/mobile/ --include="*.ts" --include="*.tsx" | grep -v "test\|__tests__" | head -20

# 4. Check existing photo upload pipeline  
grep -rn "initiate-upload\|complete-upload\|PhotoUpload" frontend/apps/mobile/ --include="*.ts" --include="*.tsx" | head -15
```

---

## Pre-Work: Read These Source Files

```
frontend/apps/mobile/features/jobs/components/detail/ClockInOutSection.tsx
  ← read fully — understand existing clock-in handler before adding GPS

frontend/apps/mobile/features/jobs/components/detail/PhotoSection.tsx
  ← read fully — understand existing WatermelonDB write logic before enabling picker

frontend/apps/mobile/features/jobs/components/detail/ExpenseSection.tsx
  ← read lines 1–100 — understand hardcoded categories before replacing with API

frontend/apps/mobile/features/voice-quote-creation/components/StructuredMessage.tsx
  ← read fully — understand stub cards before replacing

frontend/apps/mobile/features/voice-quote-creation/components/VoiceQuotePreview.tsx
  ← reference implementation for live/snapshot pattern (used for JobEtcStatusCard)

frontend/apps/mobile/features/voice-quote-creation/types-stub.ts
  ← understand what types are there before deciding what can be replaced

frontend/apps/mobile/app/(tabs)/(home)/sync/index.tsx
  ← find the console.log and understand the sync context

frontend/apps/mobile/app.json
  ← understand current permissions before adding new ones
```

---

## Step 1 — Install Dependencies + Update Permissions

```bash
cd <repo>/frontend

# Install native dependencies
pnpm --filter mobile add expo-location expo-image-picker

# Verify installation
grep '"expo-location"\|"expo-image-picker"' apps/mobile/package.json
```

**Update `apps/mobile/app.json`** — add permissions:

Read the file first, then add to the iOS and Android infoPlist/permissions sections:

```json
{
  "ios": {
    "infoPlist": {
      "NSLocationWhenInUseUsageDescription": "Pilot uses your location to verify on-site presence when you clock in.",
      "NSCameraUsageDescription": "Pilot uses your camera to take job site photos.",
      "NSPhotoLibraryUsageDescription": "Pilot accesses your photo library to add existing photos to jobs."
    }
  },
  "android": {
    "permissions": [
      "ACCESS_FINE_LOCATION",
      "CAMERA",
      "READ_EXTERNAL_STORAGE",
      "READ_MEDIA_IMAGES"
    ]
  }
}
```

> Adjust to match the structure you find in the actual `app.json`. Do NOT overwrite existing permissions.

**Intermediate check:**
```bash
pnpm --filter mobile build 2>&1 | tail -5
```

---

## Step 2 — Update `types-stub.ts` / Replace with `@pilot/shared-types`

Read `types-stub.ts` fully first. For each type defined there:

1. Check if it's now in `@pilot/shared-types` (from the pre-work grep)
2. If yes: delete the stub and update the import to use `@pilot/shared-types`
3. If no: keep the stub and add comment: `// TODO: remove when pnpm sync-api-types delivers this type`

**Find all consumers of types-stub:**
```bash
grep -rn "from.*types-stub" frontend/apps/mobile/ --include="*.ts" --include="*.tsx" | sort
```

Update each consumer file's import. The goal is to replace as many stub types as possible without breaking TypeScript compilation.

**Intermediate check:**
```bash
pnpm --filter mobile build 2>&1 | tail -5
```

---

## Step 3 — Replace Hardcoded Expense Categories with API

**File**: `apps/mobile/features/jobs/components/detail/ExpenseSection.tsx`

Read the file fully first. Replace the hardcoded `MVP_EXPENSE_CATEGORIES` array with a hook call:

```typescript
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@pilot/shared-api';

interface ExpenseCategoryItem {
  code: string;
  name: string;
  is_default: boolean;
}

// New hook (inline or extracted to separate file):
function useExpenseCategories() {
  return useQuery({
    queryKey: ['job-expense-categories'],
    queryFn: async (): Promise<ExpenseCategoryItem[]> => {
      const res = await apiClient.get('/api/v1/job-expense-categories');
      return (res.data as { categories: ExpenseCategoryItem[] }).categories;
    },
    staleTime: 300_000,  // 5 min — categories rarely change
    // Fallback to hardcoded if API fails
  });
}
```

In the component, use the API data. If `isError` or `data` is empty, fall back to the existing hardcoded list (resilience):

```typescript
const { data: apiCategories } = useExpenseCategories();
const categories = apiCategories?.length ? apiCategories : MVP_EXPENSE_CATEGORIES;
```

Keep `MVP_EXPENSE_CATEGORIES` as a fallback constant — do NOT delete it.

---

## Step 4 — Add GPS Capture to `ClockInOutSection`

**File**: `apps/mobile/features/jobs/components/detail/ClockInOutSection.tsx`

Read the full file first. Find the `handleClockIn` function and modify it:

```typescript
import * as Location from 'expo-location';

const handleClockIn = useCallback(async () => {
  let checkInLat: number | null = null;
  let checkInLng: number | null = null;

  // Request and capture GPS (soft failure — never blocks clock-in)
  try {
    const { status } = await Location.requestForegroundPermissionsAsync();
    if (status === 'granted') {
      const loc = await Location.getCurrentPositionAsync({
        accuracy: Location.Accuracy.High,
        timeInterval: 5000,  // give up after 5 seconds
      });
      checkInLat = loc.coords.latitude;
      checkInLng = loc.coords.longitude;
    }
    // If denied: proceed without GPS (no error shown)
  } catch (gpsError) {
    // GPS failed (timeout, device error) — proceed without coordinates
    console.warn('[ClockInOutSection] GPS capture failed:', gpsError);
  }

  // Proceed with clock-in regardless
  await create({
    jobId,
    userId,
    startedAt: new Date().toISOString(),
    // Add GPS only if captured:
    ...(checkInLat !== null ? { checkInLat, checkInLng } : {}),
  });
}, [jobId, userId, create]);
```

> Adapt the existing handler logic — the above is a starting point. Preserve all existing ETC prompt, loading state, and error handling.

Check pre-work result: if `JobTimeEntryCreate` does NOT have `check_in_lat`/`check_in_lng` fields, still capture GPS locally but don't pass the fields to the API call. Log a note: `// GPS captured locally but not sent — backend doesn't have lat/lng fields yet`.

---

## Step 5 — Enable `+ Add Photo` in `PhotoSection`

**File**: `apps/mobile/features/jobs/components/detail/PhotoSection.tsx`

Read the full file first. Find the `handleAddPhoto` function (currently just a `console.log`) and replace it:

```typescript
import * as ImagePicker from 'expo-image-picker';
import { ActionSheetIOS, Platform, Alert } from 'react-native';

const handleAddPhoto = async () => {
  // Show action sheet (camera vs library)
  const pickSource = async (): Promise<'camera' | 'library' | null> => {
    if (Platform.OS === 'ios') {
      return new Promise((resolve) => {
        ActionSheetIOS.showActionSheetWithOptions(
          {
            options: ['Cancel', 'Take Photo', 'Choose from Library'],
            cancelButtonIndex: 0,
          },
          (buttonIndex) => {
            if (buttonIndex === 1) resolve('camera');
            else if (buttonIndex === 2) resolve('library');
            else resolve(null);
          }
        );
      });
    } else {
      // Android: simple Alert with two buttons
      return new Promise((resolve) => {
        Alert.alert('Add Photo', 'Choose a source', [
          { text: 'Cancel', onPress: () => resolve(null) },
          { text: 'Take Photo', onPress: () => resolve('camera') },
          { text: 'Choose from Library', onPress: () => resolve('library') },
        ]);
      });
    }
  };

  const source = await pickSource();
  if (!source) return;

  // Request permission
  if (source === 'camera') {
    const { status } = await ImagePicker.requestCameraPermissionsAsync();
    if (status !== 'granted') {
      Alert.alert('Camera permission required', 'Please allow camera access in Settings.');
      return;
    }
  } else {
    const { status } = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (status !== 'granted') {
      Alert.alert('Photo library access required', 'Please allow photo library access in Settings.');
      return;
    }
  }

  const result = source === 'camera'
    ? await ImagePicker.launchCameraAsync({ mediaTypes: 'images', quality: 0.8 })
    : await ImagePicker.launchImageLibraryAsync({ mediaTypes: 'images', quality: 0.8, allowsMultipleSelection: false });

  if (!result.canceled && result.assets[0]) {
    const uri = result.assets[0].uri;
    // Write to WatermelonDB via existing photo write logic
    // Read the existing PhotoSection code — it already has the WatermelonDB write
    // Just pass `uri` to that logic
  }
};
```

> Read the existing `PhotoSection` fully — it already has WatermelonDB write logic for the photo record. Find where it creates a `Photo` database record and call that same code with the `uri` from `ImagePicker`.

---

## Step 6 — Create `JobEtcStatusCard`

**File**: `apps/mobile/features/voice-quote-creation/components/JobEtcStatusCard.tsx` (new)

Read `VoiceQuotePreview.tsx` as the reference implementation for the live/snapshot pattern.

```typescript
interface JobEtcStatusCardProps {
  mode: 'live' | 'snapshot';
  entityId?: string;  // jobId for live mode
  payload?: {        // snapshot_payload for snapshot mode
    job_id?: string;
    customer_name?: string;
    actual_cost_cents?: number;
    quoted_budget_cents?: number;
    projected_margin_pct?: number;
    hours_remaining?: number;
  };
}
```

**Live mode**: call `GET /api/v1/jobs/{entityId}/projected-margin` — use `useQuery` with the endpoint from B17/FE-B21. Show a loading spinner while fetching.

**Snapshot mode**: render from `payload` directly — no API call.

Both modes display:
- Job identifier or customer name
- Actual cost vs quoted budget (formatted as $X.XX)
- Projected margin % (with green/amber/red color based on target)
- Hours remaining (ETC)

---

## Step 7 — Create `ConflictSummaryCard`

**File**: `apps/mobile/features/voice-quote-creation/components/ConflictSummaryCard.tsx` (new)

Simple card that shows conflict metadata and a "Resolve on web →" link:

```typescript
interface ConflictSummaryCardProps {
  payload?: {
    conflict_id?: string;
    entity_type?: string;    // 'customer' | 'quote' | 'invoice' | 'job'
    conflict_type?: string;  // 'modified_modified' | 'deleted_modified' etc.
    summary?: string;
  };
}

// Display:
// "Conflict: [entity_type] [conflict_type]"
// "[summary or simplified description]"
// [Resolve on web →] button — uses Linking.openURL to deep link
```

The "Resolve on web" URL is `https://app.pilotfortrades.com/settings/integrations/quickbooks/conflicts/{conflict_id}` (or calendar equivalent based on entity_type).

---

## Step 8 — Wire New Cards into `StructuredMessage`

**File**: `apps/mobile/features/voice-quote-creation/components/StructuredMessage.tsx`

Read the file fully first. Replace the stub cards:

```typescript
import { JobEtcStatusCard } from './JobEtcStatusCard';
import { ConflictSummaryCard } from './ConflictSummaryCard';

case "job_etc_status":
  return (
    <JobEtcStatusCard
      mode={render_mode}
      entityId={entity_id ?? undefined}
      payload={snapshot_payload as JobEtcStatusPayload}
    />
  );

case "conflict_summary":
  return (
    <ConflictSummaryCard
      payload={snapshot_payload as ConflictSummaryPayload}
    />
  );
```

Remove the `testID="job-etc-stub"` and `testID="conflict-stub"` test IDs — or update them to meaningful IDs like `"job-etc-status-card"`.

---

## Step 9 — Fix Manual Sync Trigger

**File**: `apps/mobile/app/(tabs)/(home)/sync/index.tsx`

Read the file. Find the `console.log("[SyncPendingScreen] Manual sync triggered")` line.

From the pre-work, identify the sync trigger function (e.g., from `SyncProvider` context or `SyncOrchestrator`). Replace the console.log with the actual trigger:

```typescript
// Example — adapt based on what pre-work finds:
const { triggerSync } = useSyncContext();  // or however sync is exposed
// ...
const handleManualSync = async () => {
  await triggerSync();
};
```

If the sync context doesn't expose a manual trigger, find the correct way to trigger sync from the pre-work grep output.

---

## Test Requirements

### Platform: Mobile (`apps/mobile`) — Jest + `@testing-library/react-native`

- `jest.mock()` not `vi.mock()`
- `.toBeTruthy()` or `.not.toBeNull()` for assertions (not `toBeInTheDocument()`)
- `fireEvent.press()` for touch interactions
- Mock Expo Router in ALL screen tests
- Mock WatermelonDB in ALL tests with DB interactions
- Mock `expo-location` and `expo-image-picker` in ALL tests

### Mock Patterns for New Dependencies

```typescript
// Mock expo-location in tests:
jest.mock('expo-location', () => ({
  requestForegroundPermissionsAsync: jest.fn().mockResolvedValue({ status: 'granted' }),
  getCurrentPositionAsync: jest.fn().mockResolvedValue({
    coords: { latitude: 37.7749, longitude: -122.4194, accuracy: 10 },
  }),
  Accuracy: { High: 5 },
}));

// Mock expo-image-picker in tests:
jest.mock('expo-image-picker', () => ({
  requestCameraPermissionsAsync: jest.fn().mockResolvedValue({ status: 'granted' }),
  requestMediaLibraryPermissionsAsync: jest.fn().mockResolvedValue({ status: 'granted' }),
  launchCameraAsync: jest.fn().mockResolvedValue({ canceled: false, assets: [{ uri: 'file://test-photo.jpg' }] }),
  launchImageLibraryAsync: jest.fn().mockResolvedValue({ canceled: false, assets: [{ uri: 'file://test-photo.jpg' }] }),
  MediaTypeOptions: { Images: 'images' },
}));
```

### Test Resilience (per `react-engineer-rules.md` Rule 15)

- Never mutate shared fixture objects — copy before modifying
- Real WatermelonDB writes are banned — always mock `database`

### Unit Tests to Write

**`features/jobs/components/detail/__tests__/ClockInOutSection.mob-b6.test.tsx`:**
- Clock-in proceeds when GPS permission granted — lat/lng captured
- Clock-in proceeds when GPS permission denied — no error, lat/lng null
- Clock-in proceeds when GPS capture throws — soft failure, proceeds without GPS
- Loading state shown while capturing GPS

**`features/jobs/components/detail/__tests__/PhotoSection.mob-b6.test.tsx`:**
- "+ Add Photo" button is now enabled (not disabled)
- Pressing "+ Add Photo" shows action sheet / permission request
- After image picked: photo record created in WatermelonDB mock

**`features/voice-quote-creation/components/__tests__/JobEtcStatusCard.test.tsx`:**
- Snapshot mode: renders cost + margin from payload without API call
- Live mode: shows loading indicator; renders margin after MSW responds
- Low margin shows amber/red indicator

**`features/voice-quote-creation/components/__tests__/ConflictSummaryCard.test.tsx`:**
- Renders conflict type and entity type from payload
- "Resolve on web →" button present

### Integration Test

**`apps/mobile/__tests__/batch_mob_b6/structuredMessages.integration.test.tsx`:**
1. `job_etc_status` message renders `JobEtcStatusCard` (not raw JSON stub)
2. `conflict_summary` message renders `ConflictSummaryCard` (not raw JSON stub)
3. `testID="job-etc-stub"` NO LONGER present after MOB-B6

---

## Final Verification

### Phase 1 — Targeted

```bash
cd <repo>/frontend

# Type check (mobile build = tsc --noEmit)
pnpm --filter mobile build 2>&1 | tail -8

# Unit tests
pnpm --filter mobile test -- --testPathPattern="ClockInOut|PhotoSection|JobEtcStatus|ConflictSummary|ExpenseSection" 2>&1 | tail -8

# Integration tests
pnpm --filter mobile test -- --testPathPattern="batch_mob_b6" 2>&1 | tail -8
```

### Phase 2 — Full Verification (mobile only)

```bash
cd <repo>/frontend && pnpm --filter mobile build && pnpm --filter mobile lint && echo "=== TYPE+LINT PASS ===" && pnpm --filter mobile test 2>&1 | tail -8 && echo "=== MOB-B6 FINAL VERIFICATION COMPLETE ==="
```

---

## Definition of Done — MOB-B6

Update `dev-docs/analysis/pilot-app-pre-wkstm-3-prep-plan.md` §Phase 0.9:

- [ ] Regression baseline captured (zero pre-existing failures or confirmed with Tom)
- [ ] `pnpm sync-api-types` run; types-stub.ts updated
- [ ] Design doc read in full (A–I)
- [ ] All mandatory source files read before modifying (ClockInOutSection, PhotoSection, StructuredMessage, VoiceQuotePreview, ExpenseSection, sync/index.tsx, app.json)
- [ ] Pre-work complete: GPS fields in JobTimeEntryCreate confirmed, sync trigger function identified, photo upload pipeline confirmed
- [ ] **Step 1**: `expo-location` and `expo-image-picker` installed; `app.json` permissions updated
- [ ] **Step 2**: `types-stub.ts` updated; resolvable types replaced with `@pilot/shared-types`; kept stubs marked with TODO
- [ ] **Step 3**: `ExpenseSection` uses `GET /api/v1/job-expense-categories` with hardcoded fallback
- [ ] **Step 4**: GPS capture in `ClockInOutSection`; permission denied → proceeds without GPS (soft failure)
- [ ] **Step 5**: `+ Add Photo` enabled; action sheet shows camera + library options; photo record created in WatermelonDB on selection
- [ ] **Step 6**: `JobEtcStatusCard` renders live + snapshot job profitability data
- [ ] **Step 7**: `ConflictSummaryCard` renders conflict summary + "Resolve on web" link
- [ ] **Step 8**: `StructuredMessage` uses new cards; stub JSON no longer rendered; `testID="job-etc-stub"` and `testID="conflict-stub"` removed
- [ ] **Step 9**: Manual sync trigger calls actual sync function (not `console.log`)
- [ ] `ClockInOutSection` unit tests pass (GPS soft failure behavior)
- [ ] `PhotoSection` unit tests pass (`+ Add Photo` enabled)
- [ ] `JobEtcStatusCard` unit tests pass
- [ ] `ConflictSummaryCard` unit tests pass
- [ ] Integration test: `testID="job-etc-stub"` NOT present after MOB-B6
- [ ] `expo-location` and `expo-image-picker` mocked in all relevant test files
- [ ] Zero TypeScript errors (`pnpm --filter mobile build`)
- [ ] Zero ESLint errors
- [ ] **Phase 2 FULL verification passes** (`=== MOB-B6 FINAL VERIFICATION COMPLETE ===`):
  ```bash
  cd <repo>/frontend && pnpm --filter mobile build && pnpm --filter mobile lint && echo "=== TYPE+LINT PASS ===" && pnpm --filter mobile test 2>&1 | tail -8 && echo "=== MOB-B6 FINAL VERIFICATION COMPLETE ==="
  ```
- [ ] Final test count documented
- [ ] Completion Summary added to impl plan §Phase 0.9

---

## Completion Summary

After all DoD items, add a **Completion Summary** to `dev-docs/analysis/pilot-app-pre-wkstm-3-prep-plan.md` under Phase 0.9 — MOB-B6:

```markdown
### MOB-B6 — GPS Clock-In + Photo Upload + Structured Messages: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: React Native Engineer
**Baseline**: X passed (mobile)
**Final**: X+N passed (+N new tests)

#### What Was Accomplished

- Installed expo-location + expo-image-picker with Tom's approval
- GPS coordinates now captured at clock-in (soft failure if denied)
- Photo documentation enabled with camera + library picker
- Voice job_etc_status messages now show real profitability card
- Voice conflict_summary messages now show formatted conflict card
- Expense categories now fetched from API (not hardcoded)
- Manual sync trigger now calls actual sync function
- types-stub.ts cleaned up — N types replaced with @pilot/shared-types

#### Files Changed / Created

| File | Action |
|---|---|
| `apps/mobile/package.json` | Updated — added expo-location, expo-image-picker |
| `apps/mobile/app.json` | Updated — location + camera permissions |
| `apps/mobile/features/voice-quote-creation/types-stub.ts` | Updated — reduced stubs |
| `apps/mobile/features/jobs/components/detail/ClockInOutSection.tsx` | Updated — GPS capture |
| `apps/mobile/features/jobs/components/detail/PhotoSection.tsx` | Updated — enabled picker |
| `apps/mobile/features/jobs/components/detail/ExpenseSection.tsx` | Updated — API categories |
| `apps/mobile/features/voice-quote-creation/components/JobEtcStatusCard.tsx` | Created |
| `apps/mobile/features/voice-quote-creation/components/ConflictSummaryCard.tsx` | Created |
| `apps/mobile/features/voice-quote-creation/components/StructuredMessage.tsx` | Updated — new cards |
| `apps/mobile/app/(tabs)/(home)/sync/index.tsx` | Updated — real sync trigger |

#### Tests Added

| Test File | Type | Tests | All Pass |
|---|---|---|---|
| `features/jobs/components/detail/__tests__/ClockInOutSection.mob-b6.test.tsx` | Unit | N | ✅ |
| `features/jobs/components/detail/__tests__/PhotoSection.mob-b6.test.tsx` | Unit | N | ✅ |
| `features/voice-quote-creation/components/__tests__/JobEtcStatusCard.test.tsx` | Unit | N | ✅ |
| `features/voice-quote-creation/components/__tests__/ConflictSummaryCard.test.tsx` | Unit | N | ✅ |
| `apps/mobile/__tests__/batch_mob_b6/structuredMessages.integration.test.tsx` | Integration | N | ✅ |
```

---

## After This Batch

MOB-B6 is complete. Field technicians can now:
- Clock in with verified GPS coordinates
- Document job site photos from camera or library
- See rich profitability and conflict data in voice sessions

**Next batch**: `batch-mob-b7-python-engr-prompt.md` + `batch-mob-b7-react-native-engr-prompt.md` — LOTO tenant-configurable + Create Customer + Today Tab refactor. This is the final Phase 0.9 batch.
