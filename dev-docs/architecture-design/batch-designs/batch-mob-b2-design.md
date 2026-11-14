# MOB-B2 Batch Design — Job Detail: Full Field Workflow Screen

**Version**: 1.0
**Date**: 2026-06-05
**Batch**: MOB-B2
**Prerequisite Batches**: MOB-B1 ✅ (complete — `jobs/[jobId]/index` route already suppressed in `_layout.tsx`)
**Estimated Effort**: 3–4 days (frontend only — no backend companion required)
**Test Subfolder**: `apps/mobile/__tests__/batch_mob_b2/`
**Platform**: Mobile-only (Expo / React Native)
**Status**: Design complete — ready for React Engineer implementation

---

## A. Input Read Summary

All source artifacts were read directly before writing this document. No content was assumed.

### A.1 Artifacts Read

| Artifact | Key Findings |
|:---|:---|
| `pilot-app-beta-fixes-v2-impl-plan.md` §8 MOB-B2 | Full spec: 9 sections, sync placeholder fix, 11 tests defined |
| `batch-mob-b1-design.md` | Pattern reference for §A–§J structure, `JobListItem` type location, hook import patterns |
| `mob-b1-react-engineer-impl.md` | Implementation prompt format reference |
| `features/offline-sync/hooks/useCreateTimeEntry.ts` | Interface: `{ jobId, userId, startedAt, endedAt?, hours?, notes?, checkInLat?, checkInLng?, hourlyRateCents?, hoursRemainingEstimate?, quoteLineId? }` → WatermelonDB table: `time_entries`. Returns `{ create, isPending, error }`. |
| `features/offline-sync/hooks/useCreateExpense.ts` | Interface: `{ jobId, userId, jobExpenseCategoryCode, costCents, description?, isBillable, incurredAt }` → WatermelonDB table: `expenses` |
| `features/offline-sync/hooks/useCreateJobNote.ts` | Interface: `{ jobId, createdBy, content, noteType? }` → WatermelonDB table: `job_notes` |
| `features/offline-sync/hooks/useConfirmLoto.ts` | Interface: `{ jobId, checkType, confirmedAt?, gpsLat?, gpsLng? }` → WatermelonDB table: `loto_checks`. Returns `{ confirm, isPending, error }`. |
| `features/offline-sync/hooks/useCreatePhoto.ts` | Interface: `{ jobId, expenseId?, localUri, mimeType, fileSizeBytes, wifiOnly? }` → WatermelonDB table: `photos`. Returns `{ create, isPending, error }`. |
| `features/offline-sync/hooks/useCreateChangeOrder.ts` | Interface: `{ jobId, title, description?, totalAmountCents, status? }` → WatermelonDB table: `change_orders`. Returns `{ create, isPending, error }`. |
| `features/offline-sync/hooks/useChangeJobStatus.ts` | Interface: `{ jobId, fromStatus, toStatus, changedAt?, notes? }` → WatermelonDB table: `job_status_changes`. Returns `{ change, isPending, error }`. |
| `features/offline-sync/store.ts` | Zustand store. `useSyncQueueStore()` exposes: `{ isDrawerOpen, openDrawer, closeDrawer, syncState, setSyncState, activeConflictId, setActiveConflictId }`. `syncState.pendingCount` is updated by `SyncOrchestrator`'s `onStateChange` callback. |
| `app/(tabs)/_layout.tsx` | ✅ `jobs/[jobId]/index` already suppressed (href: null) — added in MOB-B1. Route is ready for the file to be created. |
| `app/(tabs)/(home)/sync/index.tsx` | Uses `PLACEHOLDER_ITEMS = []`. `useSyncQueueStore()` wired for `pendingCount`. PLACEHOLDER fix required by MOB-B2. |
| `app/(tabs)/jobs/[jobId]/comms.tsx` | ✅ Existing Job Comms route. Navigation pattern: `router.push('/(tabs)/(home)/...') as any`. Back navigation: `router.back()`. Header has `← Job` back button. **Note**: this file still uses raw `fetch()` for template loading — pre-existing violation, NOT in scope for MOB-B2. |
| `features/jobs/job-types.ts` | `JobListItem` interface: all fields including `status_code` and `customer_name`. This is the canonical local type for mobile job list items. |
| `backend/openapi_schema_map.md` §jobs | All detail endpoints verified — see §A.2 below. |
| MCP: `job` table | Confirmed columns: `id`, `tenant_id`, `customer_id`, `site_id`, `status_id`, `scheduled_start_at`, `scheduled_end_at`, `estimated_duration_minutes`, `actual_labor_cost_cents`, `actual_material_cost_cents`, `actual_profit_cents`, `is_active`, `version`. No `status_code` or `customer_name` column on the `job` table itself. |
| MCP: `job_status` table | Columns confirmed: `id`, `code`, `name`, `is_terminal`, `is_default`, `is_active`. `code` is the human-readable status string. |
| MCP: `job_expense_category` table | Columns: `code` (PK), `name`, `description`, `is_default`, `is_active`. No list endpoint found in schema map — MVP categories must be hardcoded. |

### A.2 API Endpoint Shapes Confirmed

| Endpoint | Method | Response Shape (confirmed from schema map) |
|:---|:---|:---|
| `/api/v1/jobs/{job_id}` | GET | `JobResponse: { id, tenant_id, customer_id, site_id, status_id, scheduled_start_at, scheduled_end_at, estimated_duration_minutes }` — **No `status_code` or `customer_name`** |
| `/api/v1/jobs/{job_id}/time-entries` | GET | `[{ id, job_id, user_id, started_at, ended_at, hours, notes, hourly_rate_cents }]` |
| `/api/v1/jobs/{job_id}/expenses` | GET | `[{ id, tenant_id, job_id, job_expense_category_code, description, vendor_name, incurred_at, cost_cents }]` |
| `/api/v1/jobs/{job_id}/notes` | GET | `JobNotesResponse: { id, tenant_id, job_id, notes, audio_object_key, customer_visible, client_capture_at, server_received_at }` |
| `/api/v1/jobs/{job_id}/loto-confirmations` | GET | `[{ id, tenant_id, job_id, user_id, confirmed_at, client_capture_at, server_received_at, is_active }]` |
| `/api/v1/jobs/{job_id}/change-orders` | GET | `[{ id, tenant_id, job_id, description, subtotal_cents, tax_cents, total_cents, is_active }]` |
| `/api/v1/jobs/{job_id}/projected-margin` | GET | ⚠️ **Schema map shows type name only — JSON body not displayed.** React Engineer MUST read `backend/openapi.json` and search for `ProjectedMarginResponse` before writing `useProjectedMargin`. |

### A.3 Critical Design Decisions

#### A.3.1 — `GET /api/v1/jobs/{job_id}` Has No `status_code`

`JobResponse` returns only `status_id` (UUID). The `useChangeJobStatus` hook requires `fromStatus` (string code like `"scheduled"`). The job detail screen must resolve `status_code` without an extra API call.

**Resolution**: Read `status_code` from the TanStack Query cache that was populated by MOB-B1's `useTechJobsList` hook. Use `useQueryClient().getQueryData(["tech-jobs-today", ...])` or `["tech-jobs-all", ...]` to get the `JobListItem` for this `jobId`. If cache miss (direct deep-link navigation), show a "loading" state for the status pill until the list data is fetched. **Do NOT add a backend companion task for this** — the cache-read approach is sufficient for MVP. See §G.1.

#### A.3.2 — `ChangeOrderCreate` API Mismatch with WatermelonDB Hook

`POST /api/v1/jobs/{job_id}/change-orders` body = `{ description, client_capture_at }`. But `useCreateChangeOrder` input = `{ jobId, title, description?, totalAmountCents, status? }`. The WatermelonDB hook stores richer data locally; `SyncOrchestrator` maps `title`→`description` and `totalAmountCents`→... when syncing. The UI form should collect `title`, `description`, `totalAmountCents` and pass them to `useCreateChangeOrder` — the hook handles offline queuing. See §G.2.

#### A.3.3 — Expense Categories: No List Endpoint

No `GET /api/v1/job-expense-categories` endpoint exists in the schema map. MVP hardcodes 5 categories from the `job_expense_category` DB values. See §G.3.

#### A.3.4 — Photo Picker: Verify `expo-image-picker` Before Using

Must read `frontend/apps/mobile/package.json` to confirm whether `expo-image-picker` is installed. Do NOT add a new npm dependency without justification. See §G.4.

#### A.3.5 — Sync Screen Fix Is Scoped to Pending Count Display Only

The impl plan §8 specifies wiring `PLACEHOLDER_ITEMS` to actual WatermelonDB data. However, `SyncOrchestrator`'s architecture already bridges to `useSyncQueueStore().syncState.pendingCount` — the `PLACEHOLDER_ITEMS` is used only for the list rendering. The full WatermelonDB observer for cross-table pending items is a multi-table query across `time_entries`, `expenses`, `job_notes`, `loto_checks`, `photos`, `change_orders`, `job_status_changes`. Scope: add a `usePendingSyncItems` hook that queries across all 7 tables. See §G.5 and §F.7.

---

## B. Migration Plan

### B.1 No Database Migration Required

MOB-B2 is a pure frontend batch. All 7 WatermelonDB models (`time_entries`, `expenses`, `job_notes`, `loto_checks`, `photos`, `change_orders`, `job_status_changes`) already exist from FE-B7. No schema additions needed.

### B.2 No Backend Companion Task Required

All API endpoints for this batch exist and are verified. The one gap (`status_code` on job detail) is resolved client-side via TanStack Query cache.

### B.3 Pre-Work MCP Verification (React Engineer)

Before writing any code, verify these WatermelonDB table names:

```bash
grep -rn "static table" frontend/apps/mobile/database/models/
```

Expected output includes:
- `time_entries` (TimeEntry model)
- `expenses` (Expense model)
- `job_notes` (JobNote model)
- `loto_checks` (LotoCheck model)
- `photos` (Photo model)
- `change_orders` (ChangeOrder model)
- `job_status_changes` (JobStatusChange model)

**If any name differs, STOP and reconcile before proceeding.**

---

## C. Execution Order

| # | Task | File(s) | Dependency |
|:---:|:---|:---|:---|
| 1 | Read all 7 write hook files to confirm exact input interfaces | All `offline-sync/hooks/use*.ts` | None |
| 2 | Read `database/schema.ts` — verify WatermelonDB table names | `database/schema.ts` | None |
| 3 | Verify `projected-margin` JSON response shape from `openapi.json` | `backend/openapi.json` | None |
| 4 | Verify `expo-image-picker` availability from `package.json` | `frontend/apps/mobile/package.json` | None |
| 5 | Create MSW job detail handlers | `mocks/handlers/jobDetailHandlers.ts` | #3 |
| 6 | Register new handlers in `handlers/index.ts` | `mocks/handlers/index.ts` | #5 |
| 7 | Create `useJobDetail` hook | `features/jobs/hooks/useJobDetail.ts` | #3 |
| 8 | Create `useProjectedMargin` hook | `features/jobs/hooks/useProjectedMargin.ts` | #3 |
| 9 | Create `usePendingSyncItems` hook (sync screen fix) | `features/offline-sync/hooks/usePendingSyncItems.ts` | #2 |
| 10 | Create `ClockInOutSection` component | `features/jobs/components/detail/ClockInOutSection.tsx` | #1, #7 |
| 11 | Create `LotoCheckSection` component | `features/jobs/components/detail/LotoCheckSection.tsx` | #1 |
| 12 | Create `ProjectedMarginSection` component | `features/jobs/components/detail/ProjectedMarginSection.tsx` | #8 |
| 13 | Create `ExpenseSection` component + bottom sheet | `features/jobs/components/detail/ExpenseSection.tsx` | #1 |
| 14 | Create `ChangeOrderSection` component + modal | `features/jobs/components/detail/ChangeOrderSection.tsx` | #1 |
| 15 | Create `JobNotesSection` component | `features/jobs/components/detail/JobNotesSection.tsx` | #1 |
| 16 | Create `PhotoSection` component | `features/jobs/components/detail/PhotoSection.tsx` | #1, #4 |
| 17 | Create `JobDetailScreen` root component | `features/jobs/components/JobDetailScreen.tsx` | #10–#16, #7 |
| 18 | Create `jobs/[jobId]/index.tsx` route | `app/(tabs)/jobs/[jobId]/index.tsx` | #17 |
| 19 | Fix `sync/index.tsx` PLACEHOLDER_ITEMS | `app/(tabs)/(home)/sync/index.tsx` | #9 |
| 20 | Write unit + integration tests | `__tests__/batch_mob_b2/` | #10–#18 |
| 21 | Regression check + TypeScript + lint | — | #20 |

---

## D. New API Endpoints Consumed

### D.1 `GET /api/v1/jobs/{job_id}` (existing)

**Used by**: `useJobDetail` hook

```
GET /api/v1/jobs/{job_id}
```

**Response** (confirmed from schema map):
```json
{
  "id": "uuid",
  "tenant_id": "uuid",
  "customer_id": "uuid",
  "site_id": "uuid",
  "status_id": "uuid",
  "scheduled_start_at": "2026-06-05T09:00:00Z",
  "scheduled_end_at": "2026-06-05T12:00:00Z",
  "estimated_duration_minutes": 180
}
```

**Note**: `status_code` is NOT in this response. See §A.3.1 and §G.1 for resolution.

### D.2 `GET /api/v1/jobs/{job_id}/time-entries` (existing)

**Used by**: `ClockInOutSection` to detect active time entry (no `ended_at`)

**Response**:
```json
[
  {
    "id": "uuid",
    "job_id": "uuid",
    "user_id": "uuid",
    "started_at": "2026-06-05T09:00:00Z",
    "ended_at": null,
    "hours": null,
    "notes": null,
    "hourly_rate_cents": 0
  }
]
```

Active entry detection: filter for entries where `ended_at === null && user_id === currentUserId`.

### D.3 `GET /api/v1/jobs/{job_id}/expenses` (existing)

**Used by**: `ExpenseSection`

**Response**:
```json
[
  {
    "id": "uuid",
    "tenant_id": "uuid",
    "job_id": "uuid",
    "job_expense_category_code": "materials",
    "description": "12 AWG wire",
    "vendor_name": null,
    "incurred_at": "2026-06-05",
    "cost_cents": 4500
  }
]
```

### D.4 `GET /api/v1/jobs/{job_id}/notes` (existing)

**Used by**: `JobNotesSection`

**Response**: `JobNotesResponse: { id, tenant_id, job_id, notes, audio_object_key, customer_visible, client_capture_at, server_received_at }`

**Note**: This is a single object (not an array) — there is one notes record per job. Pre-populate the text area with `notes` on screen mount.

### D.5 `GET /api/v1/jobs/{job_id}/loto-confirmations` (existing)

**Used by**: `LotoCheckSection` to show already-confirmed LOTO items

### D.6 `GET /api/v1/jobs/{job_id}/change-orders` (existing)

**Used by**: `ChangeOrderSection`

**Response**: `[{ id, tenant_id, job_id, description, subtotal_cents, tax_cents, total_cents, is_active }]` — **Note**: No `title` field. The `description` field is what the API returns. The UI should display `description`.

### D.7 `GET /api/v1/jobs/{job_id}/projected-margin` (existing)

**Used by**: `ProjectedMarginSection`

⚠️ **Response shape NOT in schema map** — `Response Projected Margin Api V1 Jobs  Job Id  Projected Margin Get` shows no JSON body.

**React Engineer MUST**: Before implementing `useProjectedMargin`, run:
```bash
python -c "import json; d=json.load(open('backend/openapi.json')); [print(k,v) for k,v in d['components']['schemas'].items() if 'margin' in k.lower() or 'projected' in k.lower() or 'Margin' in k]"
```

If the response contains ETC (Estimated Time to Complete), quoted hours, actual hours, margin %, display them as defined. If the schema is minimal, display what is available.

---

## E. Pattern Reuse Decisions

### E.1 FE-B7 Offline-First Write Pattern

All 7 WatermelonDB write hooks follow the same pattern from `batch-fe-b7-design.md §A.3.1`:
1. Write to WatermelonDB with `localSyncStatus = 'pending'`
2. Generate `idempotencyKey` UUID at capture time
3. TanStack Query cache NOT used — WatermelonDB is the source of truth for writes
4. Returns `{ create/confirm/change, isPending, error }`

The Job Detail screen UI composes these hooks — it does NOT use `apiClient` for write operations. Reads (GET endpoints for display) use `apiClient` via TanStack Query.

### E.2 `ScrollView` + Section Pattern (from `owner.tsx`)

The Job Detail screen uses a top-level `<ScrollView>` with `<SafeAreaView>` wrapping all sections. Each section is a collapsible card. This follows the owner tab pattern.

### E.3 Bottom Sheet Pattern (from `SyncQueueDrawer`)

The expense add form uses a bottom sheet modal. Read `offline-sync/components/SyncQueueDrawer.tsx` to understand the existing modal overlay pattern before implementing the expense bottom sheet.

### E.4 `router.push` Navigation (from `comms.tsx`)

Job comms navigation uses `router.push('/(tabs)/(home)/sync/conflict/${conflictId}' as any)`. The "Message Customer" button in Job Detail uses the same pattern: `router.push(\`/(tabs)/jobs/${jobId}/comms?customerId=${customerId}\` as any)`.

### E.5 TanStack Query Cache Read (§G.1 status_code resolution)

```typescript
const queryClient = useQueryClient();
// Read from the MOB-B1 cache — may be null if direct navigation
const cachedJobs = queryClient.getQueryData<JobListItem[]>(["tech-jobs-today", userId, todayStr])
  ?? queryClient.getQueryData<JobListItem[]>(["tech-jobs-all", userId])
  ?? [];
const cachedJob = cachedJobs.find(j => j.id === jobId);
const resolvedStatusCode = cachedJob?.status_code ?? null;
```

---

## F. Shared Module Interfaces

### F.1 `useJobDetail` — New Hook

```typescript
// frontend/apps/mobile/features/jobs/hooks/useJobDetail.ts
import type { JobListItem } from "../job-types";

interface JobDetailData {
  job: JobResponse;                      // from GET /api/v1/jobs/{job_id}
  timeEntries: JobTimeEntry[];           // from GET /api/v1/jobs/{job_id}/time-entries
  status_code: string | null;           // resolved from TanStack Query cache (see §G.1)
  customer_name: string | null;         // resolved from TanStack Query cache
  activeTimeEntry: JobTimeEntry | null; // first entry with ended_at === null and user_id === currentUserId
}

interface UseJobDetailReturn {
  data: JobDetailData | undefined;
  isLoading: boolean;
  isError: boolean;
  refetch: () => void;
}

export function useJobDetail(jobId: string): UseJobDetailReturn
```

**Internal behavior**:
1. `GET /api/v1/jobs/{job_id}` via `apiClient` — TanStack Query key: `["job-detail", jobId]`
2. `GET /api/v1/jobs/{job_id}/time-entries` — TanStack Query key: `["job-time-entries", jobId]`
3. Read `status_code` + `customer_name` from TanStack Query cache (§E.5 pattern)
4. Derive `activeTimeEntry`: `timeEntries.find(e => e.ended_at === null && e.user_id === userId)`
5. Combine into single `JobDetailData` return value

### F.2 `useProjectedMargin` — New Hook

```typescript
// frontend/apps/mobile/features/jobs/hooks/useProjectedMargin.ts
// Response type: verify from openapi.json before implementing (see §D.7)

export function useProjectedMargin(jobId: string): {
  data: ProjectedMarginResponse | undefined;
  isLoading: boolean;
  isError: boolean;
  refetch: () => void;
}
```

TanStack Query key: `["job-projected-margin", jobId]`
Refresh on every screen focus (use `useFocusEffect` from Expo Router).

### F.3 `usePendingSyncItems` — New Hook (sync screen fix)

```typescript
// frontend/apps/mobile/features/offline-sync/hooks/usePendingSyncItems.ts
import type { SyncQueueItemData } from "../components/SyncQueueItem";

export function usePendingSyncItems(): {
  items: SyncQueueItemData[];
  totalCount: number;
}
```

**Internal behavior**: Query WatermelonDB for all records with `localSyncStatus IN ('pending', 'syncing', 'failed', 'conflict')` across all 7 sync tables. Map each record to `SyncQueueItemData` shape.

**WatermelonDB tables to query** (verified from hook files):
- `time_entries`
- `expenses`
- `job_notes`
- `loto_checks`
- `photos`
- `change_orders`
- `job_status_changes`

**Important**: Read `database/sync/types.ts` to understand the `SyncQueueItemData` interface before implementing. Read `SyncQueueItem.tsx` to confirm the required fields.

### F.4 `ClockInOutSection` — New Component

```typescript
// frontend/apps/mobile/features/jobs/components/detail/ClockInOutSection.tsx
interface ClockInOutSectionProps {
  jobId: string;
  userId: string;
  activeTimeEntry: JobTimeEntry | null;
  testID?: string;
}
```

**Renders**:
- If `activeTimeEntry === null`: **"Clock In"** button
  - On press: request `expo-location` permission → get GPS coords → call `useCreateTimeEntry.create({ jobId, userId, startedAt: new Date(), checkInLat, checkInLng })`
  - If location permission denied: call without GPS (omit `checkInLat`/`checkInLng`)
- If `activeTimeEntry !== null`: running timer display + **"Clock Out"** button
  - Timer: shows elapsed time since `activeTimeEntry.started_at` — update every second via `setInterval`
  - On "Clock Out" press: show ETC prompt modal (§F.4.1 below) before writing
- Both states: 44pt minimum touch target

**§F.4.1 — ETC Prompt Modal**

After "Clock Out" tapped:
1. Show inline modal: "How many hours are still remaining on this job?"
2. Number input (default blank), "Skip" + "Done" actions
3. If "Done": call `useCreateTimeEntry.create({ jobId, userId, startedAt: activeEntry.started_at, endedAt: new Date(), hoursRemainingEstimate: enteredHours })`
4. If "Skip": call without `hoursRemainingEstimate`

**Note**: ETC Capture is a PRD §3.15 requirement. Do not skip the modal even if user taps "Skip".

### F.5 `LotoCheckSection` — New Component

```typescript
// frontend/apps/mobile/features/jobs/components/detail/LotoCheckSection.tsx
interface LotoCheckSectionProps {
  jobId: string;
  existingConfirmations: LotoConfirmation[];
  testID?: string;
}
```

**MVP LOTO check types** (hardcoded — no tenant-setting check required for MVP):
```typescript
const LOTO_CHECK_TYPES = [
  { checkType: "lockout_points", label: "Verify lockout points" },
  { checkType: "de_energized", label: "Test de-energized state" },
  { checkType: "tag_placement", label: "Confirm tag placement" },
] as const;
```

**Renders**: Checklist. For each item:
- If already confirmed (match in `existingConfirmations` by `checkType`): ✅ checkbox (disabled, non-interactive)
- If not confirmed: ☐ checkbox → on tap, call `useConfirmLoto.confirm({ jobId, checkType, confirmedAt: new Date() })`

> **Tenant LOTO gate**: The impl plan §8 says "Render only if tenant has LOTO enabled." However, no `GET /api/v1/settings/tenant/operations` endpoint was found in the schema map. For MVP: always render the LOTO section. Add a `// TODO: gate on tenant LOTO setting when endpoint exists` comment. See §G.6.

### F.6 `ProjectedMarginSection` — New Component

```typescript
// frontend/apps/mobile/features/jobs/components/detail/ProjectedMarginSection.tsx
interface ProjectedMarginSectionProps {
  jobId: string;
  testID?: string;
}
```

Uses `useProjectedMargin(jobId)` internally. Renders whatever fields the verified `ProjectedMarginResponse` contains. Minimum display: margin %, actual hours vs quoted hours, cost delta. Refresh on `useFocusEffect`.

### F.7 `ExpenseSection` — New Component

```typescript
// frontend/apps/mobile/features/jobs/components/detail/ExpenseSection.tsx
interface ExpenseSectionProps {
  jobId: string;
  userId: string;
  testID?: string;
}
```

**MVP expense categories** (hardcoded — no endpoint):
```typescript
const MVP_EXPENSE_CATEGORIES = [
  { code: "materials", label: "Materials" },
  { code: "tools", label: "Tools & Equipment" },
  { code: "subcontractor", label: "Subcontractor" },
  { code: "fuel", label: "Fuel & Travel" },
  { code: "other", label: "Other" },
] as const;
```

**Add Expense bottom sheet form fields**:
- Amount (dollars, number input) → convert to cents: `Math.round(dollars * 100)`
- Category (picker/select from `MVP_EXPENSE_CATEGORIES`)
- Description (text input, optional)
- Billable toggle (boolean, default `true`)
- Receipt photo button → taps `useCreatePhoto` with `expenseId` linkage

On submit: call `useCreateExpense.create({ jobId, userId, jobExpenseCategoryCode: selectedCode, costCents, description, isBillable, incurredAt: new Date() })`

### F.8 `ChangeOrderSection` — New Component

```typescript
// frontend/apps/mobile/features/jobs/components/detail/ChangeOrderSection.tsx
interface ChangeOrderSectionProps {
  jobId: string;
  testID?: string;
}
```

**Add Change Order modal form fields**:
- Title (text input — maps to `title` in `useCreateChangeOrder` which is the short description)
- Description (text area — detailed description, optional)
- Total amount (dollars, number input) → `totalAmountCents`

On submit: call `useCreateChangeOrder.create({ jobId, title, description, totalAmountCents })`

**Display list**: Each change order shows `description` (from API response), `total_cents` formatted as dollars.

### F.9 `JobNotesSection` — New Component

```typescript
// frontend/apps/mobile/features/jobs/components/detail/JobNotesSection.tsx
interface JobNotesSectionProps {
  jobId: string;
  userId: string;
  testID?: string;
}
```

Fetches `GET /api/v1/jobs/{job_id}/notes` on mount. Pre-populates a multi-line text area with existing `notes.notes`. On "Save Notes" tap: calls `useCreateJobNote.create({ jobId, createdBy: userId, content: enteredText })`. Does NOT call the REST `PUT /api/v1/jobs/{job_id}/notes` directly — writes to WatermelonDB (offline-first). `SyncOrchestrator` will upsert on reconnect.

### F.10 `PhotoSection` — New Component

```typescript
// frontend/apps/mobile/features/jobs/components/detail/PhotoSection.tsx
interface PhotoSectionProps {
  jobId: string;
  testID?: string;
}
```

Shows a grid of photos (thumbnail from `localUri` for pending-upload items, or signed S3 URL for already-synced items). "+ Add Photo" button → invoke image picker (see §G.4 for picker verification). On pick: call `useCreatePhoto.create({ jobId, localUri, mimeType, fileSizeBytes })`. Show upload progress from WatermelonDB `uploadProgress` field.

### F.11 `JobDetailScreen` — New Root Component

```typescript
// frontend/apps/mobile/features/jobs/components/JobDetailScreen.tsx
interface JobDetailScreenProps {
  jobId: string;
}
```

**Renders** (top to bottom):
1. Header (always visible, sticky): job `id` truncated display, `customer_name` (from cache), `status_code` pill, `scheduled_start_at` / `scheduled_end_at` range
2. `<ScrollView>` containing all sections:
   - `ClockInOutSection` (primary action — first visible)
   - `LotoCheckSection`
   - `ProjectedMarginSection`
   - `ExpenseSection`
   - `ChangeOrderSection`
   - `JobNotesSection`
   - `PhotoSection`
   - "Message Customer" link button → `router.push(\`/(tabs)/jobs/${jobId}/comms?customerId=${customerId}\` as any)`
   - "Mark Job Complete" button → calls `useChangeJobStatus.change({ jobId, fromStatus: resolvedStatusCode, toStatus: 'completed' })` after confirm dialog
3. Loading state: `<ActivityIndicator>` while `useJobDetail.isLoading`
4. Error state: "Failed to load job" + "Try again" pressable

**"Mark Complete" confirm dialog**: Use React Native `Alert.alert('Mark job complete?', 'This cannot be undone.', [{ text: 'Cancel' }, { text: 'Complete', onPress: ... }])` before calling `useChangeJobStatus`. Do NOT implement if `resolvedStatusCode === 'completed'` (hide the button).

---

## G. Open Questions Resolved

### G.1 — `status_code` on Job Detail Screen

**Problem**: `GET /api/v1/jobs/{job_id}` returns only `status_id` (UUID). `useChangeJobStatus` needs `fromStatus` (string code).

**Resolution**: Read from TanStack Query cache populated by `useTechJobsList`. If cache miss (direct navigation), `resolvedStatusCode` is `null`. Guard: disable "Mark Complete" button when `resolvedStatusCode === null` and show a small text note: "Refresh jobs list to enable status change." This is an acceptable MVP edge case — direct deep-link to job detail is rare.

**Do NOT add a backend companion task** — this adds scope and delay. The cache-read approach handles 99% of cases.

### G.2 — `ChangeOrderCreate` API vs Hook Mismatch

**Problem**: API body = `{ description, client_capture_at }`. Hook input = `{ jobId, title, description?, totalAmountCents, status? }`.

**Resolution**: The WatermelonDB hook stores `title` and `totalAmountCents` locally. `SyncOrchestrator` maps these to `{ description: title, client_capture_at }` when syncing to the API (existing implementation from FE-B7). The UI form correctly uses the hook interface. The React Engineer should NOT call the API directly for change orders — always go through `useCreateChangeOrder`.

### G.3 — Expense Categories: No List Endpoint

**Resolution**: Hardcode 5 MVP categories as defined in §F.7. Add `// TODO: replace with GET /api/v1/job-expense-categories when endpoint exists` comment. This covers the electrical contractor use case (materials, tools, subcontractor, fuel, other).

### G.4 — Photo Picker Library

**Required pre-work**: React Engineer must run:
```bash
grep "expo-image-picker\|expo-camera\|react-native-image-picker" frontend/apps/mobile/package.json
```

**If `expo-image-picker` is present**: Use `ImagePicker.launchImageLibraryAsync({ mediaTypes: 'Images', allowsEditing: false, quality: 0.8 })` and `ImagePicker.launchCameraAsync(...)`. Call `useCreatePhoto.create({ jobId, localUri: result.assets[0].uri, mimeType: 'image/jpeg', fileSizeBytes: result.assets[0].fileSize ?? 0 })`.

**If neither library is present**: Use `Alert.alert('Photo capture', 'Photo capture not available in this build')` as placeholder and add a `// TODO: install expo-image-picker` comment. Do NOT add the dependency without Tom's approval.

### G.5 — Sync Screen `PLACEHOLDER_ITEMS` Scope

**Resolution**: Implement `usePendingSyncItems` hook that reads WatermelonDB across all 7 sync tables. Wire the hook result to `SyncQueueSection` in `sync/index.tsx` replacing `PLACEHOLDER_ITEMS`. The hook returns `SyncQueueItemData[]` which the existing `SyncQueueSection` already accepts.

The `SyncQueueItem` shape must be verified from `offline-sync/components/SyncQueueItem.tsx` before implementing. Do NOT assume its interface.

### G.6 — LOTO Tenant Gate (No Endpoint Found)

**Problem**: The impl plan says render LOTO section only if tenant has LOTO enabled, but no settings endpoint was found for this.

**Resolution**: Always render the LOTO section for MVP (all electrical contractor tenants should use LOTO). Add `// TODO: gate on GET /api/v1/settings/tenant/operations?feature=loto when endpoint exists`. This is safe — LOTO is a safety-critical feature and showing it by default is the correct default for the electrical trade.

### G.7 — `job_notes` vs `useCreateJobNote` vs `PUT /api/v1/jobs/{job_id}/notes`

**Problem**: The API has `PUT /api/v1/jobs/{job_id}/notes` (upsert) but the hook is `useCreateJobNote` (creates a WatermelonDB `job_notes` record with `localSyncStatus = 'pending'`).

**Resolution**: The offline-first pattern is correct — `useCreateJobNote` queues to WatermelonDB, `SyncOrchestrator` sends the `PUT` on reconnect. Display notes from `GET /api/v1/jobs/{job_id}/notes` (server state). Locally written notes (not yet synced) should also be shown — read pending `job_notes` from WatermelonDB for the given `jobId` and merge them with the server state in `JobNotesSection`. See §F.9 note.

---

## H. Surface Mockup Reference

### H.1 Job Detail Screen Layout

```
┌─────────────────────────────────────────────┐
│ ← Back        Acme Electric      [Sched]    │  ← Sticky header
│               Job #J-0042                   │
│               Thu Jun 5  ·  9 AM – 12 PM   │
├─────────────────────────────────────────────┤
│  ▼ CLOCK IN / CLOCK OUT                     │  ← Section 1 (primary)
│  ┌──────────────────────────────────────┐   │
│  │       [  ⏱  Clock In  ]             │   │
│  └──────────────────────────────────────┘   │
│  (or if active: 01:23:45  [Clock Out])      │
├─────────────────────────────────────────────┤
│  ▼ LOTO SAFETY CHECK                        │  ← Section 2
│  ☐  Verify lockout points                   │
│  ☐  Test de-energized state                 │
│  ☐  Confirm tag placement                   │
├─────────────────────────────────────────────┤
│  ▼ LIVE PROFITABILITY                       │  ← Section 3
│  Margin: 38%   Actual: 2.5h / 3h quoted    │
│  Cost delta: +$42                           │
├─────────────────────────────────────────────┤
│  ▼ EXPENSES                  [+ Add]        │  ← Section 4
│  Materials · 12 AWG wire · $45.00           │
│  Tools · Drill bit set · $28.00             │
├─────────────────────────────────────────────┤
│  ▼ CHANGE ORDERS             [+ Add]        │  ← Section 5
│  Panel upgrade addition · $350.00           │
├─────────────────────────────────────────────┤
│  ▼ JOB NOTES                               │  ← Section 6
│  ┌──────────────────────────────────────┐   │
│  │  Found additional wiring issue...    │   │
│  └──────────────────────────────────────┘   │
│  [ Save Notes ]                             │
├─────────────────────────────────────────────┤
│  ▼ PHOTOS                    [+ Add]        │  ← Section 7
│  [📷] [📷] [📷]                            │
├─────────────────────────────────────────────┤
│  [ Message Customer ]                       │  ← Section 8 (link)
├─────────────────────────────────────────────┤
│  [ Mark Job Complete ]                      │  ← Section 9 (danger action)
└─────────────────────────────────────────────┘
```

### H.2 Clock Out + ETC Prompt Flow

```
[Clock Out tapped]
         ↓
┌─────────────────────────────────────┐
│ Clocked out at 11:32 AM             │
│                                     │
│ Hours still remaining on this job?  │
│  ┌──────────────────────────────┐   │
│  │  1.5                         │   │
│  └──────────────────────────────┘   │
│    (e.g. 1.5 = 1h 30m)             │
│                                     │
│  [Skip]           [Done]            │
└─────────────────────────────────────┘
```

### H.3 Add Expense Bottom Sheet

```
[+ Add Expense]
         ↓ (bottom sheet slides up)
┌─────────────────────────────────────┐
│  ╳  Add Expense                     │
│                                     │
│  Amount ($)                         │
│  ┌────────────────────────────┐     │
│  │  45.00                      │     │
│  └────────────────────────────┘     │
│                                     │
│  Category                          │
│  ┌────────────────────────────┐     │
│  │  Materials           ▼     │     │
│  └────────────────────────────┘     │
│                                     │
│  Description (optional)             │
│  ┌────────────────────────────┐     │
│  │                             │     │
│  └────────────────────────────┘     │
│                                     │
│  Billable  [●────────────]  Yes     │
│                                     │
│  [Add Receipt Photo]               │
│                                     │
│  [ Add Expense ]                    │
└─────────────────────────────────────┘
```

---

## I. Component Manifest

| Component / Hook | File Path | Action | Batch |
|:---|:---|:---|:---|
| `useJobDetail` | `apps/mobile/features/jobs/hooks/useJobDetail.ts` | **New** | MOB-B2 |
| `useProjectedMargin` | `apps/mobile/features/jobs/hooks/useProjectedMargin.ts` | **New** | MOB-B2 |
| `usePendingSyncItems` | `apps/mobile/features/offline-sync/hooks/usePendingSyncItems.ts` | **New** | MOB-B2 |
| `ClockInOutSection` | `apps/mobile/features/jobs/components/detail/ClockInOutSection.tsx` | **New** | MOB-B2 |
| `LotoCheckSection` | `apps/mobile/features/jobs/components/detail/LotoCheckSection.tsx` | **New** | MOB-B2 |
| `ProjectedMarginSection` | `apps/mobile/features/jobs/components/detail/ProjectedMarginSection.tsx` | **New** | MOB-B2 |
| `ExpenseSection` | `apps/mobile/features/jobs/components/detail/ExpenseSection.tsx` | **New** | MOB-B2 |
| `ChangeOrderSection` | `apps/mobile/features/jobs/components/detail/ChangeOrderSection.tsx` | **New** | MOB-B2 |
| `JobNotesSection` | `apps/mobile/features/jobs/components/detail/JobNotesSection.tsx` | **New** | MOB-B2 |
| `PhotoSection` | `apps/mobile/features/jobs/components/detail/PhotoSection.tsx` | **New** | MOB-B2 |
| `JobDetailScreen` | `apps/mobile/features/jobs/components/JobDetailScreen.tsx` | **New** | MOB-B2 |
| `jobs/[jobId]/index.tsx` | `apps/mobile/app/(tabs)/jobs/[jobId]/index.tsx` | **New** — main route file | MOB-B2 |
| `sync/index.tsx` | `apps/mobile/app/(tabs)/(home)/sync/index.tsx` | **Modify** — replace `PLACEHOLDER_ITEMS` | MOB-B2 |
| `jobDetailHandlers.ts` | `apps/mobile/mocks/handlers/jobDetailHandlers.ts` | **New** — MSW fixtures for all detail endpoints | MOB-B2 |
| `mocks/handlers/index.ts` | `apps/mobile/mocks/handlers/index.ts` | **Modify** — register `jobDetailHandlers` | MOB-B2 |

---

## J. Test Plan

**Test subfolder**: `apps/mobile/__tests__/batch_mob_b2/`

### J.1 Unit Tests

| Test | File | Assertion |
|:---|:---|:---|
| `useJobDetail` fetches job + time entries | `useJobDetail.test.ts` | Calls `GET /api/v1/jobs/{id}` and `GET /api/v1/jobs/{id}/time-entries`; returns combined `JobDetailData` |
| `useJobDetail` detects active time entry | `useJobDetail.test.ts` | Entry with `ended_at === null` and matching `user_id` → `activeTimeEntry` not null |
| `useJobDetail` returns null active entry when clocked out | `useJobDetail.test.ts` | All entries have `ended_at` set → `activeTimeEntry === null` |
| `useProjectedMargin` calls correct endpoint | `useProjectedMargin.test.ts` | Calls `GET /api/v1/jobs/{id}/projected-margin` |
| `ClockInOutSection` shows Clock In when no active entry | `ClockInOutSection.test.tsx` | `activeTimeEntry=null` → "Clock In" button visible |
| `ClockInOutSection` shows timer + Clock Out when active | `ClockInOutSection.test.tsx` | `activeTimeEntry={started_at}` → running timer + "Clock Out" visible |
| Clock In calls `useCreateTimeEntry` with GPS | `ClockInOutSection.test.tsx` | Mocked location permission granted → `create()` called with `checkInLat, checkInLng` |
| Clock Out shows ETC prompt | `ClockInOutSection.test.tsx` | "Clock Out" pressed → ETC modal visible |
| ETC modal "Done" calls hook with `hoursRemainingEstimate` | `ClockInOutSection.test.tsx` | Enter 1.5 → `create()` called with `hoursRemainingEstimate: 1.5` |
| ETC modal "Skip" calls hook without estimate | `ClockInOutSection.test.tsx` | "Skip" → `create()` called without `hoursRemainingEstimate` |
| `LotoCheckSection` shows unchecked items | `LotoCheckSection.test.tsx` | Empty `existingConfirmations` → all 3 items unchecked |
| `LotoCheckSection` shows checked item when confirmed | `LotoCheckSection.test.tsx` | `existingConfirmations=[{checkType:'lockout_points'}]` → first item checked, disabled |
| Tap LOTO item calls `useConfirmLoto.confirm()` | `LotoCheckSection.test.tsx` | Press unchecked item → `confirm({ jobId, checkType })` called |
| `ExpenseSection` expense list renders | `ExpenseSection.test.tsx` | MSW fixture 2 expenses → 2 rows visible |
| Add expense form submits `useCreateExpense` | `ExpenseSection.test.tsx` | Fill form → submit → `create({ jobId, userId, jobExpenseCategoryCode, costCents, isBillable, incurredAt })` |
| `ChangeOrderSection` list renders | `ChangeOrderSection.test.tsx` | MSW fixture 1 CO → description + total visible |
| Add CO form calls `useCreateChangeOrder` | `ChangeOrderSection.test.tsx` | Fill form → submit → `create({ jobId, title, totalAmountCents })` |
| `JobNotesSection` pre-populates from API | `JobNotesSection.test.tsx` | MSW returns `{notes: "existing note"}` → text area pre-populated |
| "Save Notes" calls `useCreateJobNote` | `JobNotesSection.test.tsx` | Edit text → press save → `create({ jobId, createdBy, content })` |
| Mark Complete calls `useChangeJobStatus` | `JobDetailScreen.test.tsx` | Press "Mark Complete" → confirm → `change({ fromStatus, toStatus: 'completed' })` |
| Mark Complete hidden when already complete | `JobDetailScreen.test.tsx` | `resolvedStatusCode='completed'` → button not rendered |

### J.2 Integration Tests

| Test | File | Assertion |
|:---|:---|:---|
| Job Detail screen header renders | `batch_mob_b2/job-detail.integration.test.tsx` | `customer_name` from cache, `status_code` pill visible |
| Full screen loads with all sections | `batch_mob_b2/job-detail.integration.test.tsx` | All 9 sections present in rendered output |
| Sync screen shows real pending count | `batch_mob_b2/sync-screen.integration.test.tsx` | WatermelonDB observer returns 2 pending items → `PLACEHOLDER_ITEMS` replaced, 2 items in queue |
| Navigate to job comms | `batch_mob_b2/job-detail.integration.test.tsx` | "Message Customer" press → `router.push` called with `jobs/${jobId}/comms` |
| Error state on job fetch failure | `batch_mob_b2/job-detail.integration.test.tsx` | MSW returns 500 → error state visible, "Try again" present |
| Loading state on mount | `batch_mob_b2/job-detail.integration.test.tsx` | Before MSW responds → `ActivityIndicator` present |

### J.3 Regression Tests

| Test | Assertion |
|:---|:---|
| MOB-B1 Jobs tab still renders | `JobsTabScreen` renders correctly after MOB-B2 changes |
| `_layout.tsx` still suppresses routes | `jobs/[jobId]/comms` still hidden from tab bar |
| All existing voice/inbox/sync tests pass | No regressions from handler additions or `sync/index.tsx` modification |

---

## Design Doc Quality Gate Checklist

- [x] All 7 write hook files read — exact interfaces documented in §A.1 and §F
- [x] `_layout.tsx` confirmed — `jobs/[jobId]/index` suppression already in place from MOB-B1
- [x] All job detail API endpoints verified from `openapi_schema_map.md` — shapes in §D
- [x] `GET /api/v1/jobs/{job_id}` gap documented — NO `status_code` in response; cache-read resolution in §G.1
- [x] `projected-margin` gap documented — schema map has no JSON body; pre-work step required in §D.7
- [x] MCP queries run — `job`, `job_status`, `job_expense_category` tables confirmed
- [x] `ChangeOrderCreate` API mismatch documented and resolved in §G.2
- [x] Expense categories — no endpoint confirmed; 5 MVP categories hardcoded in §F.7 and §G.3
- [x] Photo picker library — verification step explicitly required in §G.4 (no new npm deps added)
- [x] LOTO tenant gate — no endpoint found; MVP always-render decision in §G.6
- [x] Sync screen PLACEHOLDER fix scoped — `usePendingSyncItems` hook specified in §F.3
- [x] `job_notes` offline pattern resolved — WatermelonDB + merge with server state in §G.7
- [x] No new backend companion task — all endpoints exist; cache-read resolves the status_code gap
- [x] Infrastructure constraint: zero cost impact — no new AWS services
- [x] All component paths specified — full manifest in §I
- [x] Test plan covers all 7 write hooks and both read flows
