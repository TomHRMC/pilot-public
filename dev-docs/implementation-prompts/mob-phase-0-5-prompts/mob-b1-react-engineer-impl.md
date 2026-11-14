# Implementation Prompt: MOB-B1 — Jobs Tab: Assigned Jobs List

**Mode**: Pilot React Engineer
**Batch**: MOB-B1
**Source plan**: `dev-docs/analysis/pilot-app-beta-fixes-v2-impl-plan.md` §8 MOB-B1
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-mob-b1-design.md`
**Estimated session**: 2–3 days
**Platform**: Mobile only (`apps/mobile`)
**Backend companion**: MOB-B1-BE **must be complete before this session begins** (see §0 below)

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:
- **`dev-docs/architecture-design/batch-designs/batch-mob-b1-design.md`** — every section (A–J)
- **`.roo/rules-pilot-react-engineer/react-engineer-rules.md`** — in full

Critical rules for this batch:
- **Rule A**: Never assume an API endpoint path or response shape. Verify from `backend/openapi_schema_map.md` after MOB-B1-BE completes.
- **Rule B**: Confirm `static table` names in `frontend/apps/mobile/database/models/` before any WatermelonDB reference.
- **Rule C**: All API calls use `apiClient` — not raw `fetch()`. Verify the correct `apiClient` import path for mobile before writing any hook.
- **Rule D**: Read every source file before editing it. Use `read_file` — never assume contents.

---

## §0 Pre-Condition: Backend Companion Task (MOB-B1-BE)

**This session cannot begin until the Python Engineer has completed MOB-B1-BE.** Before writing any code, verify:

```bash
# Confirm ?tech_id and ?scheduled_date params now exist in the endpoint
grep -A 30 "GET /api/v1/jobs/" backend/openapi_schema_map.md | grep -E "tech_id|scheduled_date"

# Confirm JobListItem now includes status_code and customer_name
grep -A 20 "Response 200.*List Jobs" backend/openapi_schema_map.md | grep -E "status_code|customer_name"
```

If either command returns no results, **STOP — MOB-B1-BE is not done**. Do not proceed.

If confirmed, run:
```bash
cd frontend && pnpm sync-api-types
```

Then verify `JobListItem` type is present in `packages/shared-types/src/api-schema.d.ts`. If the generated types do not include `status_code` and `customer_name`, create a stub interface as described in §I.

---

## Pre-Work: Establish Regression Baseline

```bash
cd <repo>/frontend
pnpm --filter mobile test 2>&1 | tail -8
```

Record the exact test count before any changes.

---

## Pre-Work: Read These Files First

Read every file with `read_file` before writing any code. Do not assume what they contain.

```bash
# Confirm stubs and existing structure
cat frontend/apps/mobile/app/(tabs)/jobs.tsx
cat frontend/apps/mobile/app/(tabs)/_layout.tsx
cat frontend/apps/mobile/app/(tabs)/(home)/_layout.tsx

# Understand the quotes entry target
cat frontend/apps/mobile/app/(tabs)/(home)/quotes/pending.tsx
cat frontend/apps/mobile/features/quote-approval-status/hooks/useTechQuotes.ts
cat frontend/apps/mobile/features/quote-approval-status/TechPendingQuotesList.tsx

# Understand the MSW setup for mobile
cat frontend/apps/mobile/mocks/handlers/index.ts
cat frontend/apps/mobile/mocks/server.ts

# Find the correct apiClient import path for mobile
# Read existing hooks that may already use it:
cat frontend/apps/mobile/features/customer-comms/hooks/useReplyToThread.ts
cat frontend/apps/mobile/features/offline-sync/store.ts

# Understand token and auth patterns
cat frontend/apps/mobile/mocks/handlers/auth.ts

# Styling constants reference
cat frontend/apps/mobile/constants/style-constants.ts
```

---

## Context: What This Batch Does

Replaces the 10-line `jobs.tsx` stub with a fully functional assigned jobs list surface. The `Jobs` tab currently shows only a centered "Jobs" text label.

| Item | Change |
|---|---|
| `jobs.tsx` | Replace stub with `<JobsTabScreen />` |
| `(tabs)/_layout.tsx` | Add `jobs/[jobId]/index` href:null suppression (unblocks MOB-B2) |
| `useTechQuotes.ts` | Migrate raw `fetch()` → `apiClient` |
| New: `useTechJobsList` hook | Calls `GET /api/v1/jobs/?tech_id=&scheduled_date=` |
| New: `JobsTabScreen` | Today's jobs + Upcoming jobs + My Quotes entry |
| New: `JobCardRow` | Job card: customer name, time range, status pill, duration |
| New: `MyQuotesEntryRow` | Navigation row with pending count badge |
| New: `jobsHandlers.ts` | MSW fixtures for jobs list integration tests |

---

## Step 0: Fix `useTechQuotes.ts` Raw `fetch()` Violation

Read `useTechQuotes.ts` first. Then:

1. Identify the correct `apiClient` import path for mobile (read `useReplyToThread.ts` and other hooks for the pattern)
2. Replace `fetch("/api/v1/quotes?...")` with `apiClient.get("/api/v1/quotes", { params: {...} })`
3. Verify the exact quote endpoint params against `openapi_schema_map.md`:
   ```bash
   grep -A 20 "GET /api/v1/quotes" backend/openapi_schema_map.md | head -30
   ```
4. If a quotes MSW handler exists in mobile, update it. If not, create `mocks/handlers/quotesHandlers.ts` and register it in `handlers/index.ts`
5. Run existing `TechPendingQuotesList` tests to confirm no regressions before proceeding

---

## Step 1: Create MSW Jobs Handler

**File**: `frontend/apps/mobile/mocks/handlers/jobsHandlers.ts`

Before writing, read `mocks/handlers/communicationsHandlers.ts` to understand the handler pattern used in the mobile MSW setup.

The handler must cover:

```typescript
// GET /api/v1/jobs/ with optional tech_id and scheduled_date params
// Return shape per JobListItem from openapi_schema_map.md after MOB-B1-BE
// Fixture should include:
//   - 2 today-jobs (scheduled_start_at = today, same tech_id as mock user)
//   - 1 upcoming job (scheduled_start_at = 3 days from now)
//   - 1 job with scheduled_start_at = null (should be excluded by useTechJobsList)
//   - 1 job assigned to a different tech (should be excluded by ?tech_id= filter)
```

Register the handler in `mocks/handlers/index.ts`:
```typescript
import { jobsHandlers } from "./jobsHandlers";
// Add to handlers array: ...jobsHandlers
```

---

## Step 2: Create `useTechJobsList` Hook

**File**: `frontend/apps/mobile/features/jobs/hooks/useTechJobsList.ts`

Read the design doc §F.1 for the full interface. Key points:

1. **Confirm the `apiClient` import** — read 2–3 existing hooks to find the correct path before writing
2. **Get `userId`** — read `useAuth` to understand how to get the current user's ID (verify the exact return shape — do not assume it matches the web app's `useAuth`)
3. **Today's jobs query**:
   ```
   GET /api/v1/jobs/?tech_id={userId}&scheduled_date={YYYY-MM-DD}&limit=50
   ```
4. **All jobs query** (for upcoming section):
   ```
   GET /api/v1/jobs/?tech_id={userId}&limit=100
   ```
5. **Client-side filter for upcoming**: Jobs where `scheduled_start_at?.slice(0, 10)` is between tomorrow and 7 days from today (inclusive). Exclude jobs where `scheduled_start_at === null`.
6. **Pending quote count**: Use the existing `useTechQuotes()` hook — extract `data?.filter(q => q.status === 'pending_approval').length ?? 0`
7. **TanStack Query keys**:
   ```typescript
   queryKey: ["tech-jobs-today", userId, todayStr]
   queryKey: ["tech-jobs-all", userId]
   ```

**Type stub** (create `features/jobs/types-stub.ts` if `pnpm sync-api-types` did not deliver `JobListItem`):
```typescript
// TODO: delete when pnpm sync-api-types delivers this type
export interface JobListItem {
  id: string;
  tenant_id: string;
  customer_id: string;
  site_id: string;
  status_id: string;
  status_code: string | null;        // from MOB-B1-BE
  customer_name: string | null;      // from MOB-B1-BE
  scheduled_start_at: string | null;
  scheduled_end_at: string | null;
  estimated_duration_minutes: number | null;
}
```

---

## Step 3: Create `JobCardRow` Component

**File**: `frontend/apps/mobile/features/jobs/components/JobCardRow.tsx`

Design doc §F.3 specifies the full props interface. Key implementation points:

1. **Customer name**: Display `job.customer_name` — fall back to `job.customer_id.slice(0, 8) + '…'` if null (handles race condition before MOB-B1-BE confirmed)
2. **Time display**: Parse `scheduled_start_at` and `scheduled_end_at` ISO strings → formatted as `"9:00 AM – 12:00 PM"`. Use `Intl.DateTimeFormat` (already available in React Native). **Do not hardcode timezone** — use the device locale.
3. **Status pill**: 4 hardcoded statuses (§G.5 rationale):
   - `scheduled` → `bg-brand-50 text-brand-700`
   - `in_progress` → `bg-alert-50 text-alert-700`
   - `completed` → `bg-margin-50 text-margin-700`
   - unknown/null → `bg-neutral-100 text-neutral-600`
4. **Duration**: `estimated_duration_minutes ? '~${Math.round(minutes/60)}h' : null`
5. **Chevron**: `>` arrow on the right, `accessibilityRole="button"`
6. **Touch target**: `minHeight` must meet mobile accessibility standards (44pt minimum). Check `constants/style-constants.ts` for `touchTargets.mobile.sm`

---

## Step 4: Create `MyQuotesEntryRow` Component

**File**: `frontend/apps/mobile/features/jobs/components/MyQuotesEntryRow.tsx`

Design doc §F.4 specifies the interface. Key points:

1. `pendingCount > 0` → show brand-600 badge circle with white count number
2. `pendingCount === 0` → show "All caught up" in `text-neutral-400` instead of badge
3. Minimum height 44pt (touch target)
4. Accessible: `accessibilityRole="button"`, `accessibilityLabel="My Quotes, {N} pending approval"`

---

## Step 5: Create `JobsTabScreen` Component

**File**: `frontend/apps/mobile/features/jobs/components/JobsTabScreen.tsx`

This is the main component that replaces the stub. It composes all other pieces:

1. Wrap in `<SafeAreaView>` (React Native) for safe area insets
2. Use `<ScrollView refreshControl={<RefreshControl>}>` for pull-to-refresh
3. **Today section header**: `"TODAY · {formatted date}"` — format as `"Thu, Jun 5"` using `Intl.DateTimeFormat`
4. Today's jobs: `FlatList` of `JobCardRow` — on tap, call `router.push(\`/jobs/${job.id}\`)` (Expo Router path — verify the correct path format against the existing `customers/[id]/comms` navigation pattern)
5. **Upcoming section header**: `"UPCOMING"` — collapsible (use `useState(true)` default expanded; toggle on header press)
6. **Empty today state** (when `todaysJobs.length === 0`): `"No jobs scheduled for today"` — neutral body text, centered in the Today section
7. **Empty upcoming state** (when `upcomingJobs.length === 0`): `"No upcoming jobs this week"`
8. **My Quotes row**: Always visible at the bottom of the list, above the `ScrollView` bottom padding
9. **Loading state**: Show a simple `ActivityIndicator` from React Native while `isLoading === true`
10. **Error state**: `"Failed to load jobs"` with a "Try again" pressable that calls `refetch()`

---

## Step 6: Replace `jobs.tsx` Stub

**File**: `frontend/apps/mobile/app/(tabs)/jobs.tsx`

Read the file first (confirm it is still the 10-line stub), then replace entirely:

```typescript
import { JobsTabScreen } from "@/features/jobs/components/JobsTabScreen";

export default function JobsTab() {
  return <JobsTabScreen />;
}
```

> **Import path**: Use the `@/` alias — confirm it resolves correctly by reading `tsconfig.json` for mobile.

---

## Step 7: Update `(tabs)/_layout.tsx`

Read the file first. Add the jobs detail screen suppression (so the job detail route MOB-B2 will build doesn't appear as a tab bar item):

```typescript
// Add alongside existing suppressions:
<Tabs.Screen name="jobs/[jobId]/index" options={{ href: null }} />
```

> **Pattern reference**: This follows the same pattern as the existing `jobs/[jobId]/comms` and `customers/[id]/comms` suppressions already in the file. Verify the exact syntax in the existing file before adding.

---

## Tests

### Unit Tests (co-located or in `__tests__/batch_mob_b1/`)

**`useTechJobsList.test.ts`**:
- Calls `GET /api/v1/jobs/` with `tech_id` and `scheduled_date` params
- Filters upcoming jobs to next 7 days only
- Excludes jobs with `scheduled_start_at = null`
- Returns `pendingQuoteCount` from `useTechQuotes`

**`JobCardRow.test.tsx`**:
- Renders `customer_name` when provided
- Falls back to `customer_id.slice(0,8)` when `customer_name` is null
- Shows "9:00 AM – 12:00 PM" for correct ISO strings
- Status pill `scheduled` → brand class applied
- Status pill `in_progress` → alert class applied
- Calls `onPress` with `job.id` on tap

**`MyQuotesEntryRow.test.tsx`**:
- Shows badge when `pendingCount > 0`
- Shows "All caught up" when `pendingCount === 0`
- Calls `onPress` on tap

**`useTechQuotes.test.ts`** (update existing if present, create if not):
- No raw `fetch()` call — uses `apiClient.get`
- Calls the correct endpoint path

### Integration Tests (`apps/mobile/__tests__/batch_mob_b1/`)

**`jobs-tab.integration.test.tsx`**:
- MSW returns 2 today-jobs → "TODAY" section shows 2 `JobCardRow` elements
- MSW returns 1 upcoming job → "UPCOMING" section shows 1 `JobCardRow`
- MSW returns 0 jobs → empty state copy visible for both sections
- MSW returns 2 pending quotes → `MyQuotesEntryRow` shows badge "2"
- Tap job card → `router.push` called with `jobs/${jobId}`
- Tap "My Quotes" row → `router.push` called with `(home)/quotes/pending`
- Pull-to-refresh → `refetch` invoked
- MSW returns 500 → error state visible; "Try again" pressable visible

### Regression Tests

- Existing `TechPendingQuotesList` renders correctly after `useTechQuotes` migration
- `(tabs)/_layout.tsx` still suppresses `jobs/[jobId]/comms` and `customers/[id]/comms`
- All existing voice/inbox/sync test suites pass

---

## Final Verification

```bash
cd <repo>/frontend && pnpm --filter mobile check-types && pnpm --filter mobile lint && echo "=== TYPE+LINT PASS ===" && pnpm --filter mobile test 2>&1 | tail -10 && echo "=== MVP FINAL VERIFICATION COMPLETE ==="
```

---

## Definition of Done — MOB-B1

Update `pilot-app-beta-fixes-v2-impl-plan.md` §9 Batch Completion Tracker:

- [ ] Pre-modification regression baseline captured (exact mobile test count)
- [ ] MOB-B1-BE confirmed complete — `?tech_id=` and `?scheduled_date=` verified in `openapi_schema_map.md`
- [ ] `pnpm sync-api-types` run — `JobListItem` type present (or stub created with `// TODO` comment)
- [ ] All source files read before modification (`jobs.tsx`, `_layout.tsx`, `useTechQuotes.ts`, `handlers/index.ts`)
- [ ] `apiClient` import path for mobile confirmed from existing hooks
- [ ] `useTechQuotes.ts` migrated from raw `fetch()` to `apiClient` — no raw fetch remaining
- [ ] `jobsHandlers.ts` MSW handler created with fixtures for: 2 today-jobs, 1 upcoming, 1 null-date (excluded), 1 different-tech (excluded)
- [ ] `jobsHandlers.ts` registered in `mocks/handlers/index.ts`
- [ ] `useTechJobsList` hook created — calls correct endpoints, filters correctly, returns all required fields
- [ ] `JobCardRow` renders customer name, time range, status pill, duration
- [ ] `JobCardRow` status pill color-coded for `scheduled`, `in_progress`, `completed`, unknown
- [ ] `MyQuotesEntryRow` shows badge when `pendingCount > 0`; shows "All caught up" when 0
- [ ] `JobsTabScreen` renders today section, upcoming section (collapsible), My Quotes row
- [ ] `JobsTabScreen` shows loading state during fetch
- [ ] `JobsTabScreen` shows error state with "Try again" on API failure
- [ ] `JobsTabScreen` shows empty states per section when no jobs
- [ ] `jobs.tsx` stub replaced — no longer shows centered "Jobs" text
- [ ] `(tabs)/_layout.tsx` updated — `jobs/[jobId]/index` suppressed from tab bar
- [ ] Unit tests pass (all per §J.1 in design doc)
- [ ] Integration tests pass (all per §J.2 in design doc)
- [ ] Regression tests pass — existing voice/inbox/sync tests unaffected
- [ ] `useTechQuotes` regression — `TechPendingQuotesList` still renders correctly
- [ ] Zero TypeScript errors (`pnpm --filter mobile check-types`)
- [ ] Zero ESLint warnings
- [ ] No regressions in pre-existing mobile test suite
- [ ] Full verification command passes (`=== MVP FINAL VERIFICATION COMPLETE ===`)
- [ ] Final test count (before → after) documented in impl plan tracker
- [ ] Summary of work accomplished added to impl plan §9 tracker as a new sub-section after the MOB-B1 row
