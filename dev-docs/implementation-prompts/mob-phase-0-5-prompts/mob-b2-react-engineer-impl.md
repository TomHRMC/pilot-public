# Implementation Prompt: MOB-B2 — Job Detail: Full Field Workflow Screen

**Mode**: Pilot React Engineer
**Batch**: MOB-B2
**Source plan**: `dev-docs/analysis/pilot-app-beta-fixes-v2-impl-plan.md` §8 MOB-B2
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-mob-b2-design.md`
**Estimated session**: 3–4 days
**Platform**: Mobile only (`apps/mobile`)
**Backend companion**: None required — all endpoints exist

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:
- **`dev-docs/architecture-design/batch-designs/batch-mob-b2-design.md`** — every section (A–J)
- **`.roo/rules-pilot-react-engineer/react-engineer-rules.md`** — in full

Critical rules for this batch:
- **Rule A**: Never assume an API endpoint path or response shape. Use verified shapes from §D of the design doc. For `projected-margin`, read `backend/openapi.json` directly (schema map missing the JSON body).
- **Rule B**: Confirm WatermelonDB table names via `grep -rn "static table" frontend/apps/mobile/database/models/` before any `database.get<>()` call. Verified tables from design doc: `time_entries`, `expenses`, `job_notes`, `loto_checks`, `photos`, `change_orders`, `job_status_changes`.
- **Rule C**: All READ API calls use `apiClient` — not raw `fetch()`. WRITE calls go through the 7 existing WatermelonDB write hooks — not `apiClient`.
- **Rule D**: Read every source file before editing it. Use `read_file` — never assume contents.
- **Rule E**: Do NOT re-implement the 7 offline write hooks. Build UI that calls them.

---

## Pre-Work: Establish Regression Baseline

```bash
cd <repo>/frontend
pnpm --filter mobile test 2>&1 | tail -8
```

Record the exact test count (suites + tests) before any changes. Expected: 57 suites / 369 tests (MOB-B1 final state).

---

## Pre-Work: Read All Source Files First

Run each `read_file` call before writing code. Do not skip any.

```bash
# The 7 offline write hooks — read every one to confirm exact input interfaces
cat frontend/apps/mobile/features/offline-sync/hooks/useCreateTimeEntry.ts
cat frontend/apps/mobile/features/offline-sync/hooks/useCreateExpense.ts
cat frontend/apps/mobile/features/offline-sync/hooks/useCreateJobNote.ts
cat frontend/apps/mobile/features/offline-sync/hooks/useConfirmLoto.ts
cat frontend/apps/mobile/features/offline-sync/hooks/useCreatePhoto.ts
cat frontend/apps/mobile/features/offline-sync/hooks/useCreateChangeOrder.ts
cat frontend/apps/mobile/features/offline-sync/hooks/useChangeJobStatus.ts

# WatermelonDB table names — verify before using database.get<>()
grep -rn "static table" frontend/apps/mobile/database/models/

# Sync screen and store
cat frontend/apps/mobile/app/(tabs)/(home)/sync/index.tsx
cat frontend/apps/mobile/features/offline-sync/store.ts
cat frontend/apps/mobile/features/offline-sync/components/SyncQueueItem.tsx
cat frontend/apps/mobile/features/offline-sync/components/SyncQueueSection.tsx

# Existing job routes
cat frontend/apps/mobile/app/(tabs)/_layout.tsx
cat frontend/apps/mobile/app/(tabs)/jobs/[jobId]/comms.tsx

# Existing job types
cat frontend/apps/mobile/features/jobs/job-types.ts

# MSW handler registration
cat frontend/apps/mobile/mocks/handlers/index.ts

# Styling tokens (use these — do NOT hardcode colors or spacing)
cat frontend/apps/mobile/constants/style-constants.ts
cat frontend/apps/mobile/constants/theme.ts

# apiClient import path for mobile (verify before using)
cat frontend/apps/mobile/features/customer-comms/hooks/useReplyToThread.ts

# Photo picker check — run BEFORE implementing PhotoSection
grep "expo-image-picker\|expo-camera\|react-native-image-picker" frontend/apps/mobile/package.json

# projected-margin response shape — schema map missing body, read openapi.json directly
python3 -c "import json; d=json.load(open('backend/openapi.json')); [print(k) for k in d.get('components',{}).get('schemas',{}).keys() if 'margin' in k.lower() or 'Projected' in k]"
```

---

## §0 Pre-Condition: MOB-B1 Must Be Complete

Before writing any code, verify MOB-B1 is complete:

```bash
# jobs/[jobId]/index must already be suppressed in layout
grep "jobs/\[jobId\]/index" frontend/apps/mobile/app/(tabs)/_layout.tsx
```

Expected output: `<Tabs.Screen name="jobs/[jobId]/index" options={{ href: null }} />`

If this line is NOT present, MOB-B1 is not done. **STOP.**

---

## Context: What This Batch Does

Builds the `jobs/[jobId]/index.tsx` job detail screen — the tap-through destination from the MOB-B1 jobs list. This is the primary field workflow surface for technicians.

| Item | Change |
|---|---|
| New: `jobs/[jobId]/index.tsx` | Main route file — renders `<JobDetailScreen jobId={jobId} />` |
| New: `features/jobs/components/JobDetailScreen.tsx` | Root component: header + all sections |
| New: `features/jobs/components/detail/ClockInOutSection.tsx` | Clock in/out with GPS + ETC prompt |
| New: `features/jobs/components/detail/LotoCheckSection.tsx` | LOTO safety checklist |
| New: `features/jobs/components/detail/ProjectedMarginSection.tsx` | Live profitability |
| New: `features/jobs/components/detail/ExpenseSection.tsx` | Expense list + add form |
| New: `features/jobs/components/detail/ChangeOrderSection.tsx` | Change order list + add modal |
| New: `features/jobs/components/detail/JobNotesSection.tsx` | Notes text area + save |
| New: `features/jobs/components/detail/PhotoSection.tsx` | Photo grid + add photo |
| New: `features/jobs/hooks/useJobDetail.ts` | Fetches job + time entries, resolves status_code from cache |
| New: `features/jobs/hooks/useProjectedMargin.ts` | Fetches projected margin |
| New: `features/offline-sync/hooks/usePendingSyncItems.ts` | Queries pending items across 7 WDB tables |
| Modify: `app/(tabs)/(home)/sync/index.tsx` | Replace `PLACEHOLDER_ITEMS` with `usePendingSyncItems()` |
| New: `mocks/handlers/jobDetailHandlers.ts` | MSW fixtures for all job detail endpoints |
| Modify: `mocks/handlers/index.ts` | Register `jobDetailHandlers` |

---

## Step 1: Create MSW Job Detail Handlers

**File**: `frontend/apps/mobile/mocks/handlers/jobDetailHandlers.ts`

Read `mocks/handlers/communicationsHandlers.ts` and `mocks/handlers/jobsHandlers.ts` first to understand the pattern.

The handler must cover:

```typescript
// GET /api/v1/jobs/:jobId — JobResponse shape (no status_code, no customer_name)
// GET /api/v1/jobs/:jobId/time-entries — array; include one with ended_at=null for clock-in fixture
// GET /api/v1/jobs/:jobId/expenses — array with 2 fixture expenses
// GET /api/v1/jobs/:jobId/notes — single object JobNotesResponse
// GET /api/v1/jobs/:jobId/loto-confirmations — array (empty for default; 1 confirmed for other fixture)
// GET /api/v1/jobs/:jobId/change-orders — array with 1 fixture CO
// GET /api/v1/jobs/:jobId/projected-margin — verify shape from openapi.json first, then fixture it
```

Use the fixture `jobId` from `jobsHandlers.ts` (the first today-job's UUID) so integration tests can navigate from list → detail.

Register in `mocks/handlers/index.ts`:
```typescript
import { jobDetailHandlers } from "./jobDetailHandlers";
// Add to handlers array: ...jobDetailHandlers
```

---

## Step 2: Create `useJobDetail` Hook

**File**: `frontend/apps/mobile/features/jobs/hooks/useJobDetail.ts`

Key implementation points (design doc §F.1):

1. **Two parallel TanStack Query calls**:
   ```typescript
   // Job header data
   queryKey: ["job-detail", jobId]
   queryFn: () => apiClient.get(`/api/v1/jobs/${jobId}`).then(r => r.data)

   // Time entries for clock-in state
   queryKey: ["job-time-entries", jobId]
   queryFn: () => apiClient.get(`/api/v1/jobs/${jobId}/time-entries`).then(r => r.data)
   ```

2. **Resolve `status_code` and `customer_name` from TanStack Query cache**:
   ```typescript
   import { useQueryClient } from "@tanstack/react-query";
   import type { JobListItem } from "../job-types";

   const queryClient = useQueryClient();
   const { user } = useAuth(); // verify useAuth return shape first
   const todayStr = new Date().toISOString().slice(0, 10);

   // Try today's cache first, then all-jobs cache
   const cachedToday = queryClient.getQueryData<JobListItem[]>(["tech-jobs-today", user?.id, todayStr]) ?? [];
   const cachedAll = queryClient.getQueryData<JobListItem[]>(["tech-jobs-all", user?.id]) ?? [];
   const cachedJob = [...cachedToday, ...cachedAll].find(j => j.id === jobId);

   const status_code = cachedJob?.status_code ?? null;
   const customer_name = cachedJob?.customer_name ?? null;
   ```

3. **Derive `activeTimeEntry`**:
   ```typescript
   const activeTimeEntry = timeEntries?.find(
     e => e.ended_at === null && e.user_id === user?.id
   ) ?? null;
   ```

4. **Return shape**:
   ```typescript
   return {
     data: job && timeEntries ? { job, timeEntries, status_code, customer_name, activeTimeEntry } : undefined,
     isLoading: isJobLoading || isEntriesLoading,
     isError: isJobError || isEntriesError,
     refetch: () => { refetchJob(); refetchEntries(); },
   };
   ```

---

## Step 3: Create `useProjectedMargin` Hook

**File**: `frontend/apps/mobile/features/jobs/hooks/useProjectedMargin.ts`

Before writing this hook, read `backend/openapi.json` to find the `ProjectedMarginResponse` schema shape. Then:

```typescript
import { useFocusEffect } from "expo-router";

export function useProjectedMargin(jobId: string) {
  const query = useQuery({
    queryKey: ["job-projected-margin", jobId],
    queryFn: () => apiClient.get(`/api/v1/jobs/${jobId}/projected-margin`).then(r => r.data),
    staleTime: 0, // Always fresh on focus
  });

  // Refresh every time screen gains focus
  useFocusEffect(
    useCallback(() => {
      query.refetch();
    }, [query.refetch])
  );

  return query;
}
```

---

## Step 4: Create `usePendingSyncItems` Hook

**File**: `frontend/apps/mobile/features/offline-sync/hooks/usePendingSyncItems.ts`

Before writing, read:
1. `frontend/apps/mobile/features/offline-sync/components/SyncQueueItem.tsx` — confirm `SyncQueueItemData` interface
2. `frontend/apps/mobile/database/` — read the model files for the 7 tables to confirm WatermelonDB field names

This hook queries WatermelonDB for pending sync items across all 7 tables:

```typescript
// WatermelonDB table names (verified from design doc §B.3):
// time_entries, expenses, job_notes, loto_checks, photos, change_orders, job_status_changes

import { useDatabase } from "@nozbe/watermelondb/react"; // verify import path
import { Q } from "@nozbe/watermelondb";
import { withObservables } from "@nozbe/watermelondb/react"; // verify import path

const SYNC_TABLES = [
  "time_entries",
  "expenses",
  "job_notes",
  "loto_checks",
  "photos",
  "change_orders",
  "job_status_changes",
] as const;

const PENDING_STATUSES = ["pending", "syncing", "failed", "conflict"] as const;
```

Map each record to `SyncQueueItemData` shape (verify the interface from `SyncQueueItem.tsx`).

> **Note**: If WatermelonDB reactive queries are complex to implement in this batch, use a simpler `Q.where('local_sync_status', Q.oneOf([...]))` query across each table and combine results. Use `database.get('table').query(...)` pattern.

---

## Step 5: Create `ClockInOutSection`

**File**: `frontend/apps/mobile/features/jobs/components/detail/ClockInOutSection.tsx`

Design doc §F.4. Key implementation points:

### Clock In flow:
```typescript
import * as Location from "expo-location"; // verify this is installed in package.json

async function handleClockIn() {
  let lat: number | undefined;
  let lng: number | undefined;

  const { status } = await Location.requestForegroundPermissionsAsync();
  if (status === "granted") {
    const loc = await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.Balanced });
    lat = loc.coords.latitude;
    lng = loc.coords.longitude;
  }
  // If denied, proceed without GPS

  await create({
    jobId,
    userId,
    startedAt: new Date(),
    checkInLat: lat,
    checkInLng: lng,
  });
  // Refetch time entries to update UI
}
```

### Running timer display:
```typescript
const [elapsedSeconds, setElapsedSeconds] = useState(0);

useEffect(() => {
  if (!activeTimeEntry) return;
  const start = new Date(activeTimeEntry.started_at).getTime();

  const interval = setInterval(() => {
    setElapsedSeconds(Math.floor((Date.now() - start) / 1000));
  }, 1000);

  return () => clearInterval(interval);
}, [activeTimeEntry?.started_at]);

// Format: "01:23:45"
const formatted = [
  Math.floor(elapsedSeconds / 3600),
  Math.floor((elapsedSeconds % 3600) / 60),
  elapsedSeconds % 60,
].map(n => String(n).padStart(2, "0")).join(":");
```

### ETC Prompt (inline modal):
```typescript
const [showEtcPrompt, setShowEtcPrompt] = useState(false);
const [hoursRemaining, setHoursRemaining] = useState("");

// On "Clock Out" tap:
// setShowEtcPrompt(true);
// When "Done":
// await create({ jobId, userId, startedAt: activeTimeEntry.started_at, endedAt: new Date(), hoursRemainingEstimate: parseFloat(hoursRemaining) });
// When "Skip":
// await create({ jobId, userId, startedAt: activeTimeEntry.started_at, endedAt: new Date() });
```

---

## Step 6: Create `LotoCheckSection`

**File**: `frontend/apps/mobile/features/jobs/components/detail/LotoCheckSection.tsx`

Design doc §F.5. Hardcoded LOTO check types:

```typescript
const LOTO_CHECK_TYPES = [
  { checkType: "lockout_points", label: "Verify lockout points" },
  { checkType: "de_energized", label: "Test de-energized state" },
  { checkType: "tag_placement", label: "Confirm tag placement" },
] as const;
```

Fetch `GET /api/v1/jobs/{jobId}/loto-confirmations` to show already-confirmed items. Each confirmed item should show a ✅ checkmark and be non-interactive.

For unconfirmed items, on tap call:
```typescript
await confirm({ jobId, checkType: item.checkType, confirmedAt: new Date() });
// Refetch loto-confirmations to update UI
```

---

## Step 7: Create `ProjectedMarginSection`

**File**: `frontend/apps/mobile/features/jobs/components/detail/ProjectedMarginSection.tsx`

Uses `useProjectedMargin(jobId)` internally. Verify the response shape from `openapi.json` first, then render available fields. Minimum viable display (adapt to actual schema):

```
Margin: 38%
Actual: 2.5h / 3h quoted
Cost delta: +$42
```

Show loading spinner while `isLoading`, error state if `isError`.

---

## Step 8: Create `ExpenseSection`

**File**: `frontend/apps/mobile/features/jobs/components/detail/ExpenseSection.tsx`

Fetch `GET /api/v1/jobs/{jobId}/expenses` on mount.

**MVP expense categories** (hardcoded — no list endpoint):
```typescript
const MVP_EXPENSE_CATEGORIES = [
  { code: "materials", label: "Materials" },
  { code: "tools", label: "Tools & Equipment" },
  { code: "subcontractor", label: "Subcontractor" },
  { code: "fuel", label: "Fuel & Travel" },
  { code: "other", label: "Other" },
] as const;
// TODO: replace with GET /api/v1/job-expense-categories when endpoint exists
```

**Add Expense bottom sheet form**:
- Amount (dollars `TextInput`, numeric keyboard) → `Math.round(parseFloat(dollars) * 100)` for `costCents`
- Category (picker)
- Description (optional text)
- Billable toggle (default `true`)
- On submit: `useCreateExpense.create({ jobId, userId, jobExpenseCategoryCode, costCents, description, isBillable, incurredAt: new Date() })`

After successful create, refetch expenses list.

---

## Step 9: Create `ChangeOrderSection`

**File**: `frontend/apps/mobile/features/jobs/components/detail/ChangeOrderSection.tsx`

Fetch `GET /api/v1/jobs/{jobId}/change-orders` on mount.

**Important**: API response `description` field is what the change order record stores. The `useCreateChangeOrder` hook input uses `title` (which maps to `description` on sync). Display `co.description` in the list.

**Add Change Order modal form**:
- Title (text input, required) → `title` in hook call
- Description (text area, optional) → `description` in hook call
- Total amount (dollars number input) → `totalAmountCents`
- On submit: `useCreateChangeOrder.create({ jobId, title, description, totalAmountCents })`

After successful create, refetch change orders list.

---

## Step 10: Create `JobNotesSection`

**File**: `frontend/apps/mobile/features/jobs/components/detail/JobNotesSection.tsx`

Fetch `GET /api/v1/jobs/{jobId}/notes` on mount. Pre-populate text area with `notesData.notes`.

> **Note**: `GET /api/v1/jobs/{jobId}/notes` returns a **single object** (not array). It may return 404 if no notes exist — handle this gracefully (start with empty text area).

On "Save Notes":
```typescript
await useCreateJobNote.create({
  jobId,
  createdBy: userId,
  content: noteText,
});
// Local save — SyncOrchestrator sends PUT /api/v1/jobs/{jobId}/notes on reconnect
```

---

## Step 11: Create `PhotoSection`

**File**: `frontend/apps/mobile/features/jobs/components/detail/PhotoSection.tsx`

**First**: Check if `expo-image-picker` is available:
```bash
grep "expo-image-picker" frontend/apps/mobile/package.json
```

**If available**:
```typescript
import * as ImagePicker from "expo-image-picker";

const handleAddPhoto = async () => {
  Alert.alert("Add Photo", "Choose source", [
    {
      text: "Camera",
      onPress: async () => {
        const result = await ImagePicker.launchCameraAsync({ quality: 0.8 });
        if (!result.canceled && result.assets[0]) {
          await create({
            jobId,
            localUri: result.assets[0].uri,
            mimeType: "image/jpeg",
            fileSizeBytes: result.assets[0].fileSize ?? 0,
          });
        }
      },
    },
    {
      text: "Photo Library",
      onPress: async () => {
        const result = await ImagePicker.launchImageLibraryAsync({ mediaTypes: "Images", quality: 0.8 });
        if (!result.canceled && result.assets[0]) {
          await create({ ... });
        }
      },
    },
    { text: "Cancel", style: "cancel" },
  ]);
};
```

**If NOT available**: Render a disabled "+ Add Photo" button with comment:
```typescript
// TODO: install expo-image-picker — photo capture requires Tom approval
```

Show existing photos from WatermelonDB `photos` table for this `jobId` (query by `jobId`). Show `uploadProgress` as a small progress indicator on pending photos.

---

## Step 12: Create `JobDetailScreen` Root Component

**File**: `frontend/apps/mobile/features/jobs/components/JobDetailScreen.tsx`

Composes all section components. Props:
```typescript
interface JobDetailScreenProps {
  jobId: string;
}
```

Structure:
```typescript
const { data, isLoading, isError, refetch } = useJobDetail(jobId);
const { user } = useAuth();

if (isLoading) return <ActivityIndicator ... />;
if (isError) return <ErrorState ... />;

return (
  <SafeAreaView>
    {/* Sticky header */}
    <View> {/* Back button + customer_name + status pill + time range */}

    {/* Scrollable sections */}
    <ScrollView>
      <ClockInOutSection jobId={jobId} userId={user.id} activeTimeEntry={data.activeTimeEntry} />
      <LotoCheckSection jobId={jobId} existingConfirmations={lotoData ?? []} />
      <ProjectedMarginSection jobId={jobId} />
      <ExpenseSection jobId={jobId} userId={user.id} />
      <ChangeOrderSection jobId={jobId} />
      <JobNotesSection jobId={jobId} userId={user.id} />
      <PhotoSection jobId={jobId} />

      {/* Message Customer link */}
      <Pressable onPress={() => router.push(`/(tabs)/jobs/${jobId}/comms?customerId=${data.job.customer_id}` as any)}>
        <Text>Message Customer</Text>
      </Pressable>

      {/* Mark Complete — hidden when already completed */}
      {data.status_code !== "completed" && (
        <Pressable onPress={handleMarkComplete}>
          <Text>Mark Job Complete</Text>
        </Pressable>
      )}
    </ScrollView>
  </SafeAreaView>
);
```

**Mark Complete** confirm dialog:
```typescript
const handleMarkComplete = () => {
  Alert.alert(
    "Mark job complete?",
    "This action cannot be undone.",
    [
      { text: "Cancel", style: "cancel" },
      {
        text: "Complete",
        onPress: async () => {
          await changeStatus.change({
            jobId,
            fromStatus: data.status_code ?? "scheduled",
            toStatus: "completed",
          });
        },
      },
    ]
  );
};
```

> **Guard**: If `data.status_code === null` (cache miss on direct navigation), disable the "Mark Complete" button and add text: `"Refresh jobs list to enable status change"`. See design doc §G.1.

---

## Step 13: Create `jobs/[jobId]/index.tsx` Route

**File**: `frontend/apps/mobile/app/(tabs)/jobs/[jobId]/index.tsx`

```typescript
import { useLocalSearchParams } from "expo-router";
import { JobDetailScreen } from "@/features/jobs/components/JobDetailScreen";

export default function JobDetailRoute() {
  const { jobId } = useLocalSearchParams<{ jobId: string }>();
  return <JobDetailScreen jobId={jobId} />;
}
```

> **Verify the `@/` alias** resolves correctly by reading `frontend/apps/mobile/tsconfig.json` before using it.

---

## Step 14: Fix Sync Screen `PLACEHOLDER_ITEMS`

**File**: `frontend/apps/mobile/app/(tabs)/(home)/sync/index.tsx`

Read the file first. Replace:
```typescript
const PLACEHOLDER_ITEMS: SyncQueueItemData[] = [];
```

With:
```typescript
import { usePendingSyncItems } from "../../../../features/offline-sync/hooks/usePendingSyncItems";

// Inside the component:
const { items } = usePendingSyncItems();
```

Then replace all `PLACEHOLDER_ITEMS` references with `items`. The 4 `SyncQueueSection` components already filter by `localSyncStatus` — they will work correctly once `items` is wired.

---

## Tests

### Unit Tests

**`useJobDetail.test.ts`**:
- Calls `GET /api/v1/jobs/{id}` AND `GET /api/v1/jobs/{id}/time-entries`
- `activeTimeEntry` is non-null when an open entry exists with matching `user_id`
- `activeTimeEntry` is null when all entries have `ended_at`
- `status_code` resolved from TanStack Query cache
- `status_code` is null when cache is empty (direct navigation)

**`useProjectedMargin.test.ts`**:
- Calls `GET /api/v1/jobs/{id}/projected-margin`
- Refetches on `useFocusEffect`

**`ClockInOutSection.test.tsx`**:
- Renders "Clock In" when `activeTimeEntry === null`
- Renders running timer + "Clock Out" when `activeTimeEntry` is set
- Clock In with granted location → `create()` called with `checkInLat`, `checkInLng`
- Clock In with denied location → `create()` called without GPS fields
- "Clock Out" → ETC modal visible
- ETC "Done" → `create()` called with `hoursRemainingEstimate`
- ETC "Skip" → `create()` called without `hoursRemainingEstimate`

**`LotoCheckSection.test.tsx`**:
- All 3 items unchecked when `existingConfirmations = []`
- Confirmed item shows ✅ and is not interactive
- Tap unconfirmed item → `confirm({ jobId, checkType })` called

**`ExpenseSection.test.tsx`**:
- Expense list renders category code + cost
- "+ Add" opens bottom sheet form
- Submit form → `create({ jobId, userId, jobExpenseCategoryCode, costCents, isBillable, incurredAt })` called

**`ChangeOrderSection.test.tsx`**:
- CO list renders description + total_cents
- "+ Add" opens modal form
- Submit → `create({ jobId, title, totalAmountCents })` called

**`JobNotesSection.test.tsx`**:
- Notes text area pre-populated from MSW fixture `notes` field
- "Save Notes" → `create({ jobId, createdBy, content })` called
- Handles 404 gracefully (empty text area)

**`JobDetailScreen.test.tsx`**:
- "Mark Complete" visible when `status_code !== 'completed'`
- "Mark Complete" hidden when `status_code === 'completed'`
- Confirm dialog shown on "Mark Complete" press
- `change({ fromStatus, toStatus: 'completed' })` called after confirm
- "Mark Complete" disabled with note when `status_code === null`

### Integration Tests (`__tests__/batch_mob_b2/`)

**`job-detail.integration.test.tsx`**:
- Job detail screen renders header: customer name (from cache), status pill, time range
- All 9 sections present in rendered output
- "Message Customer" press → `router.push` called with `jobs/${jobId}/comms`
- Error state on `GET /api/v1/jobs/{id}` returning 500
- Loading state visible before MSW responds

**`sync-screen.integration.test.tsx`**:
- `PLACEHOLDER_ITEMS` replaced — 0 placeholder items; real WatermelonDB items shown
- `SyncQueueSection` receives real `items` array from `usePendingSyncItems`

### Regression Tests

- Existing MOB-B1 `jobs-tab.integration.test.tsx` — all 9 tests still pass
- `(tabs)/_layout.tsx` routes suppressed correctly after modifications
- All existing voice/inbox/sync screen tests pass (adding `jobDetailHandlers` must not conflict)

---

## Final Verification

```bash
cd <repo>/frontend
pnpm --filter mobile check-types && \
pnpm --filter mobile lint && \
echo "=== TYPE+LINT PASS ===" && \
pnpm --filter mobile test 2>&1 | tail -10 && \
echo "=== MOB-B2 FINAL VERIFICATION COMPLETE ==="
```

---

## Definition of Done — MOB-B2

Update `pilot-app-beta-fixes-v2-impl-plan.md` §9 Batch Completion Tracker:

- [ ] Pre-modification regression baseline captured (57 suites / 369 tests from MOB-B1)
- [ ] MOB-B1 confirmed complete — `jobs/[jobId]/index` suppression verified in `_layout.tsx`
- [ ] All 7 write hook interfaces read before building UI
- [ ] WatermelonDB table names confirmed via `grep -rn "static table"` before any `database.get<>()`
- [ ] `projected-margin` JSON response shape read from `backend/openapi.json` (not assumed)
- [ ] `expo-image-picker` availability checked before implementing `PhotoSection`
- [ ] `SyncQueueItemData` interface confirmed from `SyncQueueItem.tsx` before implementing `usePendingSyncItems`
- [ ] MSW `jobDetailHandlers.ts` created and registered in `handlers/index.ts`
- [ ] `useJobDetail` hook created — fetches job + time entries; resolves `status_code` from cache; derives `activeTimeEntry`
- [ ] `useProjectedMargin` hook created — refreshes on `useFocusEffect`
- [ ] `usePendingSyncItems` hook created — queries all 7 WDB tables
- [ ] `ClockInOutSection` — Clock In with GPS functional; running timer renders; ETC modal on clock-out
- [ ] `LotoCheckSection` — hardcoded 3 check types; confirmed items disabled; tap calls `useConfirmLoto.confirm()`
- [ ] `ProjectedMarginSection` — renders actual `ProjectedMarginResponse` fields (verified from `openapi.json`)
- [ ] `ExpenseSection` — expense list + add form; 5 hardcoded categories; `useCreateExpense.create()` called
- [ ] `ChangeOrderSection` — CO list + add modal; `useCreateChangeOrder.create()` called
- [ ] `JobNotesSection` — pre-populated from API; "Save Notes" calls `useCreateJobNote.create()`; 404 handled
- [ ] `PhotoSection` — picker availability checked; `useCreatePhoto.create()` called on pick; placeholder if no library
- [ ] `JobDetailScreen` — header + all 9 sections composed correctly
- [ ] "Mark Complete" confirm dialog + `useChangeJobStatus.change()` called
- [ ] "Mark Complete" hidden when `status_code === 'completed'`
- [ ] "Mark Complete" disabled with note when `status_code === null` (cache miss)
- [ ] "Message Customer" navigates to `jobs/[jobId]/comms` with `customerId`
- [ ] `jobs/[jobId]/index.tsx` route created — renders `<JobDetailScreen jobId={jobId} />`
- [ ] `sync/index.tsx` `PLACEHOLDER_ITEMS` replaced with `usePendingSyncItems()` output
- [ ] Unit tests pass (all per §J.1 in design doc)
- [ ] Integration tests pass (all per §J.2 in design doc)
- [ ] Regression tests pass — existing MOB-B1 and pre-MOB-B1 tests unaffected
- [ ] Zero TypeScript errors (`pnpm --filter mobile check-types`)
- [ ] Zero ESLint warnings
- [ ] No regressions in pre-existing mobile test suite
- [ ] Full verification command passes (`=== MOB-B2 FINAL VERIFICATION COMPLETE ===`)
- [ ] Final test count (before → after) documented in impl plan tracker
- [ ] Summary of work accomplished added to impl plan §9 as new sub-section after MOB-B2 row
