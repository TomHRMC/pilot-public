# MOB-B1 Batch Design — Jobs Tab: Assigned Jobs List

**Version**: 1.0
**Date**: 2026-06-05
**Batch**: MOB-B1
**Prerequisite Batches**: None
**Estimated Effort**: 2–3 days (frontend) + 1 day (companion backend)
**Test Subfolder**: `apps/mobile/__tests__/batch_mob_b1/`
**Platform**: Mobile-only (Expo / React Native)
**Status**: Design complete — ready for React Engineer implementation

---

## A. Input Read Summary

All source artifacts were read directly before writing this document. No content was assumed.

### A.1 Artifacts Read

| Artifact | Key Findings |
|:---|:---|
| `frontend/apps/mobile/app/(tabs)/jobs.tsx` | 10-line stub: `<View><Text style={{fontSize:22,fontWeight:'500'}}>Jobs</Text></View>`. Replace entirely. |
| `frontend/apps/mobile/app/(tabs)/_layout.tsx` | 5 tab screens: `index`, `jobs`, `customers`, `calcs`, `owner`. Suppresses: `more/about`, `more/help/*`, `customers/[id]/comms`, `jobs/[jobId]/comms`. **No `jobs/[jobId]` screen registered** — must be added to the layout to suppress it from the tab bar. |
| `backend/openapi_schema_map.md` §jobs | `GET /api/v1/jobs/`: only `skip` (int, default 0) and `limit` (int, default 100) params. **No `?assigned_to=`, `?status=`, `?date=` filters exist.** Response: `[{ id, tenant_id, customer_id, site_id, status_id, scheduled_start_at, scheduled_end_at, estimated_duration_minutes }]`. `customer_id` and `status_id` are UUIDs — no denormalized names. |
| `backend/openapi_schema_map.md` §dispatch-board | `GET /api/v1/scheduling/dispatch-board?start_date=&end_date=`: returns `{ start_date, end_date, techs: DispatchBoardTechGroup[], unassigned: DispatchBoardJobEntry[] }`. `DispatchBoardTechGroup: { tech_id, jobs: DispatchBoardJobEntry[], eta_minutes_to_first_job }`. `DispatchBoardJobEntry: { id, tenant_id, customer_id, site_id, status_id, scheduled_start_at, scheduled_end_at, estimated_duration_minutes, ... }`. **The correct endpoint for "today's assigned jobs per tech."** Jobs are grouped by `tech_id` — filter by `currentUser.id` to get just this tech's jobs. Same raw shape as `/jobs/` — still no customer name, still status_id UUID. |
| `backend/openapi_schema_map.md` §scheduling-assignments | `GET /api/v1/scheduling/jobs/{job_id}/assignments`: returns `[{ id, tenant_id, job_id, user_id, assigned_by_user_id, role, ordinal, assigned_at }]`. Per-job endpoint — not scalable for a job list (would require N+1 calls). Not suitable for the list view. |
| `frontend/apps/mobile/features/quote-approval-status/hooks/useTechQuotes.ts` | Uses raw `fetch("/api/v1/quotes?submitted_by=me&status=...")`. Violation: must be migrated to `apiClient` in this batch (Jobs tab links to the quotes section — if we're touching the jobs area, fix this adjacent violation). |
| `frontend/apps/mobile/app/(tabs)/(home)/quotes/pending.tsx` | Wraps `<TechPendingQuotesList />`. Route: `/(tabs)/(home)/quotes/pending`. This is the target for the "My Quotes" entry in the Jobs tab. |
| `frontend/apps/mobile/mocks/handlers/index.ts` | Registers: `healthHandlers`, `authHandlers`, `voiceHttpHandlers`, `voiceWsHandler`, `syncHandlers`, `photoHandlers`, `communicationsHandlers`, `customerCommsPreviewHandlers`. **No jobs handler exists.** New `jobsHandlers` MSW file required. |
| `frontend/apps/mobile/app/(tabs)/(home)/_layout.tsx` | Stack navigator with 3 screens: `index`, `voice/index`, `voice/[sessionId]`. Quotes routes (`quotes/pending`, `quotes/[id]`) are NOT registered here — Expo Router discovers them automatically via file system. The nested `(home)` layout pattern is the model for how deep routes are structured. |

### A.2 Critical Design Decision: Data Source for Jobs List

**Problem**: No single endpoint returns "this tech's assigned jobs with customer name and status code." The two candidate endpoints both return raw UUIDs:

| Endpoint | Pro | Con |
|:---|:---|:---|
| `GET /api/v1/jobs/` | Simple; returns all tenant jobs | No assignment filter; no date filter; no customer name; no status code |
| `GET /api/v1/scheduling/dispatch-board` | Groups by tech_id — correct assignment filter; date-scoped | Still no customer name; still status_id UUID; only returns scheduled jobs (not unscheduled) |

**Resolution**: Use **two-endpoint strategy**:
1. **Today's scheduled jobs**: `GET /api/v1/scheduling/dispatch-board?start_date=TODAY&end_date=TODAY` — filter `techs` array for `tech_id = currentUser.id` → today's assigned scheduled jobs
2. **All my jobs (upcoming + unscheduled)**: `GET /api/v1/jobs/?limit=100` filtered client-side by date — returns all tenant jobs; cross-reference with dispatch board to identify which are assigned to this tech

**Companion Backend Task (required before implementation — MOB-B1-BE)**:
The `GET /api/v1/jobs/` endpoint needs two new query parameters (same pattern as BETA-B3 companion which added `?search=` to customers and `?status=` to quotes):
- `?tech_id=` — filter jobs by tech assignment (requires JOIN on `scheduling_job_tech_assignment`)
- `?scheduled_date=` — filter jobs by date of `scheduled_start_at`

And the response needs two new fields (same pattern as BETA-B3 companion adding `customer_name` and `status_code` to quotes):
- `status_code: string` — the status code string (e.g., `"scheduled"`, `"in_progress"`, `"completed"`) from the `job_status` table
- `customer_name: string | null` — `display_name` from the `customer` table via JOIN

Without these backend additions, the Jobs tab list would show only UUID values for status and customer — unacceptable UX. The companion task is on the critical path.

---

## B. Migration Plan

### B.1 Backend Companion Task (MOB-B1-BE) — Python Engineer

**This must complete BEFORE the React Engineer begins MOB-B1 frontend implementation.**

#### B.1.1 Pre-Migration Verification

Before writing any backend code, the Python Engineer MUST run these MCP queries:

```sql
-- Verify the job table columns
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'job'
ORDER BY ordinal_position;

-- Verify the job_status table (to understand the status code lookup)
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'job_status'
ORDER BY ordinal_position;

-- Verify the scheduling_job_tech_assignment table (to understand tech filtering)
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'scheduling_job_tech_assignment'
ORDER BY ordinal_position;
```

**If any table name returns 0 rows, STOP and ask Tom. Do not guess.**

#### B.1.2 Changes to `GET /api/v1/jobs/`

**No schema migration required** — existing tables support these queries via JOINs.

Add two optional query params to `_list_jobs_impl()` in `backend/api/routes/jobs.py`:

| Param | Type | Behavior |
|:---|:---|:---|
| `tech_id` | `str \| None` | If provided, JOIN on `scheduling_job_tech_assignment` table to filter only jobs assigned to this `user_id`. Verify exact table name from MCP before coding. |
| `scheduled_date` | `str \| None` | If provided (YYYY-MM-DD), filter where `DATE(job.scheduled_start_at) = scheduled_date`. Use PostgreSQL `DATE()` cast or `::date`. |

Add two new fields to the response (new `JobListItem` schema, analogous to `QuoteListItem` from BETA-B3):

| Field | Source | Join Required |
|:---|:---|:---|
| `status_code` | `job_status.code` | JOIN `job_status` on `job.status_id = job_status.id` |
| `customer_name` | `customer.display_name` | JOIN `customer` on `job.customer_id = customer.id` |

New schema class `JobListItem` in `backend/api/schemas/jobs.py`:
```python
class JobListItem(SQLModel):
    id: str
    tenant_id: str
    customer_id: str
    site_id: str
    status_id: str
    status_code: str | None = None        # new
    customer_name: str | None = None      # new
    scheduled_start_at: datetime | None = None
    scheduled_end_at: datetime | None = None
    estimated_duration_minutes: int | None = None
```

**Multi-tenancy**: The existing job list endpoint already applies tenant scoping. The new JOIN on `customer` MUST also include `.where(Customer.tenant_id == current_user.tenant_id)` to prevent IDOR — same pattern as `QuoteListItem` in BETA-B3.

**Dual-endpoint pattern**: Both `GET /api/v1/jobs/` (authenticated) and `GET /api/v1/jobs/test` (no auth) must accept the new params and return `JobListItem`.

**Regenerate OpenAPI**: Run `python export_openapi_json.py` after changes.

#### B.1.3 Tests for MOB-B1-BE

New test file: `backend/tests/domains/field_operations/test_job_list_enhancements.py`

| Test | Assertion |
|:---|:---|
| `?tech_id=` filter | Returns only jobs assigned to the specified tech; excludes jobs assigned to other techs |
| `?scheduled_date=` filter | Returns only jobs scheduled on the specified date |
| `status_code` in response | Response includes `status_code` string (e.g., `"scheduled"`) — not null |
| `customer_name` in response | Response includes `customer_name` — not null when customer exists |
| Multi-tenancy on customer JOIN | Customer from different tenant does not appear in response |
| Combined `?tech_id=&scheduled_date=` | Filters by both params simultaneously |

---

## C. Execution Order

| # | Task | Agent | Dependency |
|:---:|:---|:---|:---|
| 1 | Python Engineer: Run MCP queries to verify table names | Python Engineer | None |
| 2 | Python Engineer: Add `?tech_id=` and `?scheduled_date=` params + `JobListItem` schema | Python Engineer | #1 |
| 3 | Python Engineer: Write MOB-B1-BE tests; confirm all pass | Python Engineer | #2 |
| 4 | Python Engineer: Regenerate `openapi.json` + `openapi_schema_map.md` | Python Engineer | #3 |
| 5 | React Engineer: Confirm #4 is done; run `pnpm sync-api-types` | React Engineer | #4 |
| 6 | React Engineer: Read all source files before writing any code | React Engineer | #5 |
| 7 | React Engineer: Create MSW jobs handler for mobile | React Engineer | #6 |
| 8 | React Engineer: Implement `useTechJobsList` hook | React Engineer | #7 |
| 9 | React Engineer: Migrate `useTechQuotes.ts` raw `fetch()` → `apiClient` | React Engineer | #6 |
| 10 | React Engineer: Replace `jobs.tsx` stub with `JobsTabScreen` component | React Engineer | #8 |
| 11 | React Engineer: Add `jobs/[jobId]` Stack screen to `(tabs)/_layout.tsx` | React Engineer | #10 |
| 12 | React Engineer: Write unit + integration tests | React Engineer | #10 |
| 13 | React Engineer: Regression check + TypeScript + lint | React Engineer | #12 |

---

## D. New API Endpoints Consumed

### D.1 `GET /api/v1/jobs/` (enhanced by MOB-B1-BE)

**Used by**: `useTechJobsList` hook in Jobs tab

For today's assigned jobs:
```
GET /api/v1/jobs/?tech_id={currentUser.id}&scheduled_date={YYYY-MM-DD}&limit=50
```

For upcoming jobs (next 7 days, this tech):
```
GET /api/v1/jobs/?tech_id={currentUser.id}&limit=100
```
Client-side filter by `scheduled_start_at` date prefix after fetch.

**Response** (after MOB-B1-BE):
```json
[
  {
    "id": "uuid",
    "tenant_id": "uuid",
    "customer_id": "uuid",
    "site_id": "uuid",
    "status_id": "uuid",
    "status_code": "scheduled",
    "customer_name": "Acme Electric",
    "scheduled_start_at": "2026-06-05T09:00:00Z",
    "scheduled_end_at": "2026-06-05T12:00:00Z",
    "estimated_duration_minutes": 180
  }
]
```

### D.2 `GET /api/v1/quotes` (existing — used by `useTechQuotes`)

**Used by**: `useTechQuotes` hook for the "My Quotes" section count badge

```
GET /api/v1/quotes?submitted_by=me&status=pending_approval,approved,rejected,draft
```

**Existing response shape** — no changes needed.

---

## E. Pattern Reuse Decisions

### E.1 BETA-B3 Companion Pattern — Job List Enhancement

The backend task (MOB-B1-BE) follows the identical pattern as BETA-B3's companion backend tasks (BE-1 through BE-4):
- Add optional filter params to existing list endpoint
- Add denormalized display fields to response via JOIN
- Return a new schema class (`JobListItem` vs `QuoteListItem`)
- Maintain dual-endpoint pattern (`/jobs/` + `/jobs/test`)
- Run `export_openapi_json.py` after changes

### E.2 `useTechQuotes` → `apiClient` Migration

`useTechQuotes.ts` currently uses raw `fetch()`. Migrate following the BETA-B2 pattern:
1. Read the file
2. Replace `fetch(url)` with `apiClient.get(path, { params })`
3. Update the existing MSW handler if one exists for quotes in mobile (none found — create one in `mocks/handlers/quotesHandlers.ts`)
4. Run existing `TechPendingQuotesList` tests to confirm no regressions

### E.3 Pull-to-Refresh Pattern — `<RefreshControl>`

`TechPendingQuotesList` already uses the standard React Native `<FlatList refreshControl={<RefreshControl>}>` pattern. The Jobs list reuses this exact pattern.

### E.4 Tab Stack Navigator — `(home)/_layout.tsx` Pattern

The `(home)` tab group uses `<Stack>` with `headerShown: false` for the root and selectively shows headers for sub-screens. The Jobs tab needs its own nested stack for the job detail screen (MOB-B2). See §H for the tab architecture decision.

---

## F. Shared Module Interfaces

### F.1 `useTechJobsList` — New Hook

```typescript
// frontend/apps/mobile/features/jobs/hooks/useTechJobsList.ts
interface JobListItem {
  id: string;
  tenant_id: string;
  customer_id: string;
  site_id: string;
  status_id: string;
  status_code: string | null;       // from MOB-B1-BE
  customer_name: string | null;     // from MOB-B1-BE
  scheduled_start_at: string | null;
  scheduled_end_at: string | null;
  estimated_duration_minutes: number | null;
}

interface UseTechJobsListReturn {
  todaysJobs: JobListItem[];
  upcomingJobs: JobListItem[];
  pendingQuoteCount: number;
  isLoading: boolean;
  isError: boolean;
  refetch: () => void;
  isFetching: boolean;
}

export function useTechJobsList(): UseTechJobsListReturn
```

**Internal behavior**:
1. Fetch `GET /api/v1/jobs/?tech_id={userId}&scheduled_date={today}` for today's jobs
2. Fetch `GET /api/v1/jobs/?tech_id={userId}&limit=100` for all jobs (filter client-side for upcoming next 7 days, excluding today)
3. Fetch pending quote count via `useTechQuotes()` (reuse existing hook)
4. `userId` comes from `useAuth().user.id` — read `useAuth` return shape before implementing

**Note on `apiClient` in mobile**: Before implementing, verify the `apiClient` import path for mobile. Read `frontend/apps/mobile/mocks/handlers/auth.ts` and the existing feature hooks (`useCustomerThreads`, etc.) to locate the correct import.

### F.2 `JobsTabScreen` — New Component

```typescript
// frontend/apps/mobile/features/jobs/components/JobsTabScreen.tsx
// Replaces the stub in jobs.tsx
// Props: none (reads from useTechJobsList internally)
```

**Renders**:
- `JobsSectionHeader` — "Today · {formatted date}" with refresh indicator
- `FlatList` of `JobCardRow` items for today's jobs
- `JobsSectionHeader` — "Upcoming" (collapsible, default expanded)
- `FlatList` of `JobCardRow` items for upcoming jobs (next 7 days)
- `MyQuotesEntryRow` — navigation row to `(home)/quotes/pending` with badge count
- All wrapped in a `ScrollView` with `<RefreshControl>`

### F.3 `JobCardRow` — New Component

```typescript
// frontend/apps/mobile/features/jobs/components/JobCardRow.tsx
interface JobCardRowProps {
  job: JobListItem;
  onPress: (jobId: string) => void;
  testID?: string;
}
```

**Displays**:
- Customer name (from `job.customer_name` — falls back to `job.customer_id.slice(0, 8)` if null until MOB-B1-BE is confirmed)
- Scheduled time: formatted as `"9:00 AM – 12:00 PM"` using the `scheduled_start_at` / `scheduled_end_at` ISO strings
- Status pill using `job.status_code` — color-coded: `scheduled` → brand blue, `in_progress` → amber, `completed` → green, null/unknown → neutral grey
- Estimated duration: `"~3h"` from `estimated_duration_minutes`
- Right arrow chevron (accessibility: `accessibilityRole="button"`)

### F.4 `MyQuotesEntryRow` — New Component

```typescript
// frontend/apps/mobile/features/jobs/components/MyQuotesEntryRow.tsx
interface MyQuotesEntryRowProps {
  pendingCount: number;
  onPress: () => void;
  testID?: string;
}
```

**Displays**:
- Label: "My Quotes"
- Badge: `pendingCount` if > 0 (brand-600 circle, white text)
- If count = 0: shows "All caught up" secondary text instead of badge
- Right arrow chevron

---

## G. Open Questions Resolved

### G.1 "Today's Jobs" Endpoint — Dispatch Board vs Enhanced Jobs List

**Decision**: Use the enhanced `GET /api/v1/jobs/?tech_id=&scheduled_date=` (MOB-B1-BE) for both today's and upcoming jobs.

**Rationale**: The dispatch board endpoint (`/scheduling/dispatch-board`) is designed for the web's tech-column × time-row grid view. Its response nests jobs inside `DispatchBoardTechGroup[]` — requires unwrapping to get a flat job list. The enhanced `GET /api/v1/jobs/` is simpler, returns a flat array already, and the `?tech_id=` filter gives us correct assignment filtering. Both endpoints return the same raw `JobResponse` shape — the companion backend task adds the display fields to only one of them (the simpler one).

### G.2 Upcoming Jobs Section — What Date Range?

**Decision**: Show jobs for the next 7 calendar days (excluding today), client-side filtered after fetching `GET /api/v1/jobs/?tech_id={userId}&limit=100`.

**Rationale**: Avoid a separate API call for a bounded date range. 100 jobs is a safe upper limit for a single tech. Client-side date filtering is trivial: `job.scheduled_start_at?.slice(0, 10) > todayStr && job.scheduled_start_at?.slice(0, 10) <= sevenDaysStr`.

### G.3 Jobs Tab Navigation Architecture — Stack Navigator or Separate Tab

**Decision**: Jobs tab (`jobs.tsx`) renders the list directly. Job detail (`jobs/[jobId]/index.tsx` — built in MOB-B2) is a **separate file-based route** under `app/(tabs)/jobs/[jobId]/index.tsx`, not nested inside a `(home)` sub-group.

**Rationale**: The `(home)` route group is for the voice/inbox/quotes sub-screens that live under the Home tab's Stack navigator. The Jobs tab has its own Expo Router Stack navigator that needs to be registered in `(tabs)/_layout.tsx`. The `jobs/[jobId]/comms.tsx` route already exists as a sibling — the detail screen follows the same pattern.

**Required change to `(tabs)/_layout.tsx`**:
Add a `<Tabs.Screen name="jobs/[jobId]/index" options={{ href: null }} />` to suppress the job detail screen from appearing as a tab bar item. This follows the same pattern as `jobs/[jobId]/comms` suppression that already exists.

### G.4 Unscheduled Jobs — Show or Hide?

**Decision**: Hide unscheduled jobs (where `scheduled_start_at === null`) from the Jobs tab list.

**Rationale**: A job with no scheduled time has no date to sort by and no useful information to display in a time-ordered list. Unscheduled jobs are visible to the owner on the dispatch board's "Unassigned" column. The tech does not need to see them on their Jobs tab.

### G.5 Status Color Coding Without a Status List Endpoint

**Decision**: Hard-code 4 status codes for the MVP status pill: `scheduled` (brand), `in_progress` (amber), `completed` (green), any other (neutral). Do not fetch a dynamic status list.

**Rationale**: There is no `GET /api/v1/job-statuses/` endpoint confirmed in `openapi_schema_map.md`. The 4 MVP status codes are well-known from the PRD. A dynamic status list endpoint would add an extra API call and complexity for minimal MVP benefit.

### G.6 `apiClient` in Mobile — Import Path

**Decision**: The React Engineer MUST read the existing `useMobileInboxSse.ts`, `useSmsQuota.ts`, and `useReplyToThread.ts` files to identify the correct `apiClient` import before writing any new hook. Do NOT assume the same path as the web app.

---

## H. Surface Mockup Reference

### H.1 Jobs Tab Screen Layout

```
┌──────────────────────────────────┐
│  Jobs                             │  ← Screen header (SafeAreaView)
│ ─────────────────────────────── │
│  TODAY · Thu, Jun 5              │  ← Section header
│ ─────────────────────────────── │
│  [Acme Electric        ] [Sched] │  ← JobCardRow
│   9:00 AM – 12:00 PM  · ~3h  >  │
│ ─────────────────────────────── │
│  [Smith Residence      ] [InProg]│
│   1:00 PM – ?          · ~2h  >  │
│ ─────────────────────────────── │
│  UPCOMING                        │  ← Section header (collapsible)
│ ─────────────────────────────── │
│  [Jones Commercial     ] [Sched] │
│   Tomorrow, 8:00 AM     · ~4h >  │
│ ─────────────────────────────── │
│  MY QUOTES                       │  ← MyQuotesEntryRow
│  2 pending approval           >  │
│ ─────────────────────────────── │
│                                   │
│  [Empty state when no jobs]       │
└──────────────────────────────────┘
```

### H.2 `JobCardRow` Component

```
┌─────────────────────────────────────┐
│ Acme Electric          [Scheduled]  │  ← customer_name + status pill
│ 9:00 AM – 12:00 PM  ·  ~3h      >  │  ← time range + duration + chevron
└─────────────────────────────────────┘
```

Status pill colors:
- `scheduled` → `bg-brand-50 text-brand-700`
- `in_progress` → `bg-alert-50 text-alert-700`
- `completed` → `bg-margin-50 text-margin-700`
- unknown → `bg-neutral-100 text-neutral-600`

---

## I. Component Manifest

| Component / Hook | File Path | Action | Batch |
|:---|:---|:---|:---|
| `useTechJobsList` | `apps/mobile/features/jobs/hooks/useTechJobsList.ts` | **New** | MOB-B1 |
| `JobsTabScreen` | `apps/mobile/features/jobs/components/JobsTabScreen.tsx` | **New** | MOB-B1 |
| `JobCardRow` | `apps/mobile/features/jobs/components/JobCardRow.tsx` | **New** | MOB-B1 |
| `MyQuotesEntryRow` | `apps/mobile/features/jobs/components/MyQuotesEntryRow.tsx` | **New** | MOB-B1 |
| `jobs.tsx` (stub) | `apps/mobile/app/(tabs)/jobs.tsx` | **Replace** — import `JobsTabScreen` | MOB-B1 |
| `(tabs)/_layout.tsx` | `apps/mobile/app/(tabs)/_layout.tsx` | **Modify** — add `jobs/[jobId]/index` href:null suppression | MOB-B1 |
| `useTechQuotes.ts` | `apps/mobile/features/quote-approval-status/hooks/useTechQuotes.ts` | **Modify** — migrate raw `fetch()` → `apiClient` | MOB-B1 |
| `jobsHandlers.ts` | `apps/mobile/mocks/handlers/jobsHandlers.ts` | **New** — MSW fixtures for jobs list | MOB-B1 |
| `handlers/index.ts` | `apps/mobile/mocks/handlers/index.ts` | **Modify** — register `jobsHandlers` | MOB-B1 |
| `JobListItem` type stub | `apps/mobile/features/jobs/types-stub.ts` | **New** — `// TODO: delete when pnpm sync-api-types delivers this type` | MOB-B1 |

---

## J. Test Plan

**Test subfolder**: `apps/mobile/__tests__/batch_mob_b1/`

### J.1 Unit Tests

| Test | File | Assertion |
|:---|:---|:---|
| `useTechJobsList` calls correct endpoint | `useTechJobsList.test.ts` | Calls `GET /api/v1/jobs/?tech_id=<userId>&scheduled_date=<today>` for today's section |
| `useTechJobsList` filters upcoming 7 days | `useTechJobsList.test.ts` | Jobs with `scheduled_start_at` > today and ≤ 7 days out appear in `upcomingJobs`; jobs 8+ days out excluded |
| `useTechJobsList` hides unscheduled jobs | `useTechJobsList.test.ts` | Job with `scheduled_start_at = null` not in `todaysJobs` or `upcomingJobs` |
| `JobCardRow` renders customer name | `JobCardRow.test.tsx` | `customer_name='Acme Electric'` → "Acme Electric" in rendered output |
| `JobCardRow` renders scheduled time | `JobCardRow.test.tsx` | `scheduled_start_at='2026-06-05T09:00:00Z'` → "9:00 AM" in rendered output |
| `JobCardRow` status pill `scheduled` → brand color | `JobCardRow.test.tsx` | `status_code='scheduled'` → element with `bg-brand-50` class |
| `JobCardRow` status pill `in_progress` → amber | `JobCardRow.test.tsx` | `status_code='in_progress'` → element with `bg-alert-50` class |
| `MyQuotesEntryRow` shows badge count | `MyQuotesEntryRow.test.tsx` | `pendingCount=3` → "3" badge visible |
| `MyQuotesEntryRow` shows "All caught up" | `MyQuotesEntryRow.test.tsx` | `pendingCount=0` → "All caught up" visible; no badge |
| `useTechQuotes` uses `apiClient` (not fetch) | `useTechQuotes.test.ts` | No raw `fetch` call; `apiClient.get` called with correct path |

### J.2 Integration Tests

| Test | File | Assertion |
|:---|:---|:---|
| Jobs tab renders today's section | `batch_mob_b1/jobs-tab.integration.test.tsx` | MSW fixture returns 2 today-jobs → "TODAY" section with 2 job cards visible |
| Jobs tab renders upcoming section | `batch_mob_b1/jobs-tab.integration.test.tsx` | MSW fixture returns 1 upcoming job → "UPCOMING" section visible with 1 card |
| Jobs tab renders empty state | `batch_mob_b1/jobs-tab.integration.test.tsx` | MSW fixture returns 0 jobs → empty state copy visible; no sections |
| Jobs tab shows "My Quotes" entry | `batch_mob_b1/jobs-tab.integration.test.tsx` | MSW fixture returns 2 pending quotes → "My Quotes" row with badge "2" |
| Tap job row → navigates | `batch_mob_b1/jobs-tab.integration.test.tsx` | `fireEvent.press` on job card → `router.push` called with `jobs/${jobId}` |
| Tap "My Quotes" → navigates | `batch_mob_b1/jobs-tab.integration.test.tsx` | `fireEvent.press` on My Quotes row → `router.push` called with `(home)/quotes/pending` |
| Pull-to-refresh calls refetch | `batch_mob_b1/jobs-tab.integration.test.tsx` | Simulate `onRefresh` → `refetch` called |
| Error state renders on API failure | `batch_mob_b1/jobs-tab.integration.test.tsx` | MSW handler returns 500 → error state copy visible |

### J.3 Regression Tests

| Test | Assertion |
|:---|:---|
| Existing `TechPendingQuotesList` tests still pass | No regression from `useTechQuotes` apiClient migration |
| `(tabs)/_layout.tsx` still suppresses correct routes | `jobs/[jobId]/comms` still hidden from tab bar after new suppression added |
| All existing voice/inbox/sync screens navigate correctly | Adding the jobs stack screen suppression doesn't break other routes |

---

## Design Doc Quality Gate Checklist

- [x] Every code file referenced was actually read (not assumed)
- [x] `GET /api/v1/jobs/` current params documented — only `skip` and `limit`
- [x] Missing params documented — `?tech_id=` and `?scheduled_date=` specified for backend companion task
- [x] `JobListItem` schema with `status_code` and `customer_name` additions specified
- [x] Backend multi-tenancy rule for customer JOIN explicitly stated
- [x] Dual-endpoint pattern (auth + `/test`) stated for all new backend endpoints
- [x] `useTechQuotes.ts` raw `fetch()` violation identified and fix batch assigned
- [x] `(tabs)/_layout.tsx` Jobs detail screen suppression explicitly required
- [x] MSW handler gap identified and new `jobsHandlers.ts` specified
- [x] Status color mapping hardcoded with explicit rationale (no status list endpoint exists)
- [x] `apiClient` import path verification step explicitly required in Rule F
- [x] Unscheduled jobs exclusion decision documented in §G.4
- [x] No backend changes for the frontend batch (MOB-B1-BE is the companion task)
- [x] Infrastructure constraint: zero cost impact (no new AWS services)
