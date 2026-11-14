# Batch FE-B7 Design — Offline Sync Mobile (Pass 3 Flow 7)

**Batch**: FE-B7
**Phase**: Phase 1 — Surface Design Session
**Date**: 2026-05-22
**Author**: Pilot Architect
**Status**: Design Complete — Ready for React Engineer Handoff

---

## Prerequisites Confirmed

- FE-B0 through FE-B6 complete; all shared hooks and components verified in `packages/ui/src/index.ts`
- `VoiceConfirmTurn` — FE-B3 ✅
- `useStalenessRetry()` — FE-B4 ✅
- `DiffView` (with `variant="entity"` already in locked interface) — FE-B5 ✅
- `MessagePreviewModal` — FE-B6 ✅
- `InFlightSyncIndicator` skeleton — FE-B1 ✅
- `CONFLICT_CLASS_TOKENS` — FE-B4 ✅
- Backend endpoints **confirmed live** in `api-schema.d.ts`: `mobile-sync/conflicts/{id}/resolve`, `owner/mobile-sync-escalations`, `mobile/sync-sessions/{session_id}/complete`

---

## Key Codebase Facts Established During Design Session

| Fact | Detail |
|:---|:---|
| Mobile app path convention | `apps/mobile/` — **NO `src/` prefix** (per methods doc §1) |
| `database/` folder exists? | **NO** — created fresh in FE-B7 at `apps/mobile/database/` |
| `PendingBadge` in codebase? | **NO** — created new in FE-B7 |
| `useOptimisticMutation` in codebase? | **NO** — created new in FE-B7 |
| `EscalationStatusRow` in codebase? | **NO** — created new in FE-B7 |
| `SyncOrchestrator` in codebase? | **NO** — created new in FE-B7 |
| `useDeferredVoiceUpload.ts` | **EXISTS** as AsyncStorage stub at `features/voice-quote-creation/hooks/useDeferredVoiceUpload.ts` — FE-B7 **upgrades persistence to WatermelonDB, public API unchanged** |
| Backend sync endpoints | **LIVE** in `api-schema.d.ts` — `ConflictDetailResponse`, `ConflictResolveRequest`, `MobileSyncStateResponse` shapes are generated types |
| `job_time_entry` offline columns | `client_capture_at TIMESTAMPTZ NULL`, `server_received_at TIMESTAMPTZ NULL` confirmed in DB schema |

---

## Section A — Component Implementation Plan

### A.1 New Shared Components (`packages/ui/src/`)

#### A.1.1 `<PendingBadge>` — Optimistic UI pending count badge

| Field | Value |
|:---|:---|
| **File** | `packages/ui/src/pending-badge/PendingBadge.tsx` |
| **Web variant** | `packages/ui/src/pending-badge/web/PendingBadge.tsx` |
| **Mobile variant** | `packages/ui/src/pending-badge/mobile/PendingBadge.tsx` |
| **Types** | `packages/ui/src/pending-badge/types.ts` |
| **Pattern** | §16.8 Optimistic UI with Pending Badges |
| **Consumers** | FE-B9 (background sync), FE-B12 (account settings async ops) |

See Section F for full TypeScript interface.

#### A.1.2 `useOptimisticMutation()` — Offline-write + pending badge hook

| Field | Value |
|:---|:---|
| **File** | `packages/ui/src/hooks/useOptimisticMutation.ts` |
| **Pattern** | §16.8 Optimistic UI |
| **Consumers** | FE-B9, FE-B12 |

See Section F for full TypeScript interface.

#### A.1.3 `<EscalationStatusRow>` — Mobile-to-web escalation status display

| Field | Value |
|:---|:---|
| **File** | `packages/ui/src/escalation-status/EscalationStatusRow.tsx` |
| **Platform** | Mobile only (Gluestack primitives) — web-only display is in FE-B9 owner queue |
| **Pattern** | §16.11 Mobile-to-Web Escalation |
| **Consumers** | FE-B9 (Phase 2 cross-platform escalation surfaces) |

See Section F for full TypeScript interface.

---

### A.2 New Mobile-Only Infrastructure (`apps/mobile/database/`)

#### A.2.1 WatermelonDB Local Schema

| File | Purpose |
|:---|:---|
| `apps/mobile/database/schema.ts` | `appSchema` defining all 7 offline entity tables + sync queue metadata |
| `apps/mobile/database/index.ts` | Database singleton; JSI SQLite adapter configuration |

#### A.2.2 WatermelonDB Model Classes — 7 Entity Types

All models live at `apps/mobile/database/models/`. Each extends WatermelonDB `Model` and carries:
- `sync_status: 'pending' | 'syncing' | 'synced' | 'failed' | 'conflict'`
- `idempotency_key: string` — UUID v4 generated at capture time (never changes across retries)
- `client_capture_at: number` — Unix timestamp ms (WatermelonDB `@date` field)
- `server_received_at: number | null` — populated after successful sync

| Model Class | File | Backend Table | Key Fields Mirrored |
|:---|:---|:---|:---|
| `TimeEntry` | `models/TimeEntry.ts` | `job_time_entry` | `jobId`, `userId`, `startedAt`, `endedAt`, `hours`, `notes`, `checkInLat`, `checkInLng`, `hourlyRateCents`, `hoursRemainingEstimate`, `quoteLineId` |
| `Expense` | `models/Expense.ts` | `job_expense` | `jobId`, `userId`, `jobExpenseCategoryCode`, `costCents`, `description`, `isBillable`, `incurredAt` |
| `Photo` | `models/Photo.ts` | `job_attachment` | `jobId`, `expenseId?`, `localUri`, `mimeType`, `fileSizeBytes`, `pilotPhotoId?`, `uploadProgress`, `s3SessionId?` |
| `ChangeOrder` | `models/ChangeOrder.ts` | `change_order` | `jobId`, `title`, `description`, `totalAmountCents`, `status` |
| `LotoCheck` | `models/LotoCheck.ts` | `loto_check` | `jobId`, `checkType`, `confirmedAt`, `gpsLat?`, `gpsLng?` |
| `JobStatusChange` | `models/JobStatusChange.ts` | `job_status_change` | `jobId`, `fromStatus`, `toStatus`, `changedAt`, `notes?` |
| `JobNote` | `models/JobNote.ts` | `job_notes` | `jobId`, `createdBy`, `content`, `noteType?` |

#### A.2.3 Custom Sync Orchestrator

| File | Purpose |
|:---|:---|
| `apps/mobile/database/sync/orchestrator.ts` | `SyncOrchestrator` class — push/pull, idempotency, natural-key dedup, conflict routing |
| `apps/mobile/database/sync/conflict-handlers.ts` | Per-severity class handlers: `handleAutoSilent`, `handleAutoNotice`, `handleTechResolvable`, `handleOwnerEscalation` |
| `apps/mobile/database/sync/photo-upload.ts` | S3 multipart resumable upload pipeline per §15.5 |
| `apps/mobile/database/sync/voice-upload.ts` | Deferred voice upload; wraps existing `useDeferredVoiceUpload` persistence upgrade |

See Section F for `SyncOrchestrator` full interface.

---

### A.3 New Mobile Feature Components (`apps/mobile/features/offline-sync/`)

#### A.3.1 Offline Write Hooks — 7 Entity Types

Each hook lives at `apps/mobile/features/offline-sync/hooks/`:

| Hook | File | Writes To |
|:---|:---|:---|
| `useCreateTimeEntry()` | `hooks/useCreateTimeEntry.ts` | WatermelonDB `TimeEntry` model |
| `useCreateExpense()` | `hooks/useCreateExpense.ts` | WatermelonDB `Expense` model |
| `useCreatePhoto()` | `hooks/useCreatePhoto.ts` | WatermelonDB `Photo` model + queues S3 upload |
| `useCreateChangeOrder()` | `hooks/useCreateChangeOrder.ts` | WatermelonDB `ChangeOrder` model |
| `useConfirmLoto()` | `hooks/useConfirmLoto.ts` | WatermelonDB `LotoCheck` model |
| `useChangeJobStatus()` | `hooks/useChangeJobStatus.ts` | WatermelonDB `JobStatusChange` model |
| `useCreateJobNote()` | `hooks/useCreateJobNote.ts` | WatermelonDB `JobNote` model |

Each hook follows the pattern:
1. Write to WatermelonDB with `sync_status = 'pending'` and generated `idempotency_key`
2. TanStack Query cache is NOT used for offline writes — WatermelonDB is the source of truth
3. Hook returns `{ create, isPending, error }` consistent with `useOptimisticMutation()` shape

#### A.3.2 Sync Queue UI Components

| Component | File | Purpose |
|:---|:---|:---|
| `<SyncQueueDrawer>` | `components/SyncQueueDrawer.tsx` | Bottom-sheet drawer; 4 sections: action-needed, syncing, pending, recently-synced |
| `<SyncQueueItem>` | `components/SyncQueueItem.tsx` | Single queue item row with status pill, entity type icon, timestamp, action CTA |
| `<SyncQueueSection>` | `components/SyncQueueSection.tsx` | Section header + list within the drawer |
| `<ConnectionStatePill>` | `components/ConnectionStatePill.tsx` | Global status pill (hidden / amber pulsing / red solid / red action-needed) |
| `<SyncNowButton>` | `components/SyncNowButton.tsx` | Manual trigger; disabled while sync in flight |

#### A.3.3 Conflict Resolution UI Components

| Component | File | Purpose |
|:---|:---|:---|
| `<ConflictResolutionScreen>` | `components/ConflictResolutionScreen.tsx` | Full-screen conflict resolution; vertical stacked layout per spec §11 |
| `<ConflictExplainer>` | `components/ConflictExplainer.tsx` | Plain-language description at top of conflict screen |
| `<ConflictVersionCard>` | `components/ConflictVersionCard.tsx` | "Your version" or "Server version" card; composes `<DiffView variant="entity">` |
| `<ConflictActionBar>` | `components/ConflictActionBar.tsx` | Bottom bar: "Use my version" / "Use server version" / "Send to owner" |

#### A.3.4 Photo Upload Components

| Component | File | Purpose |
|:---|:---|:---|
| `<PhotoUploadProgress>` | `components/PhotoUploadProgress.tsx` | Per-photo thumbnail overlay: uploading progress / WiFi pending / success / failed |
| `usePhotoUpload()` | `hooks/usePhotoUpload.ts` | S3 multipart state machine; reads `photo_upload_wifi_only` setting |

#### A.3.5 Sync Indicator Integration

| Component | File | Purpose |
|:---|:---|:---|
| `<MobileSyncStatusBar>` | `components/MobileSyncStatusBar.tsx` | Bottom status bar composing `<InFlightSyncIndicator>` from FE-B1 + pending count from local DB |

#### A.3.6 Auth Edge Case Components

| Component | File | Purpose |
|:---|:---|:---|
| `<DisabledAccountExportScreen>` | `components/DisabledAccountExportScreen.tsx` | "Account disabled" affordance with JSON export button (§15.12) |
| `<OfflineHardLimitWarning>` | `components/OfflineHardLimitWarning.tsx` | Full-screen 72hr hard limit warning with sync-now trigger (§15.11) |

---

### A.4 New Routes

| Route | File | Auth | Gate |
|:---|:---|:---|:---|
| Sync queue drawer | Modal composable (not a route) — opened from `<ConnectionStatePill>` tap | Required | `tech` role |
| Conflict resolution | `app/(tabs)/(home)/sync/conflict/[conflictId].tsx` | Required | `tech` role |
| Pending changes overview | `app/(tabs)/(home)/sync/index.tsx` | Required | `tech` role |

---

## Section B — Execution Order

Items executed in this strict order within FE-B7:

| # | Item | Rationale |
|:---|:---|:---|
| 1 | WatermelonDB schema + database index + 7 model classes | Foundation; nothing else works without local DB |
| 2 | `useOptimisticMutation()` + `<PendingBadge>` shared components | FE-B9 and FE-B12 gate on these; establish before wiring entity hooks |
| 3 | 7 offline write hooks (`useCreateTimeEntry` etc.) | Establishes offline-first write contract per §11.3 rule 1 |
| 4 | `SyncOrchestrator` push/pull class (no conflict logic yet) | Happy-path sync end-to-end; enables integration testing |
| 5 | Conflict handler stubs + `conflict-handlers.ts` | Four-class routing logic; required before conflict UI |
| 6 | `<SyncQueueDrawer>` + `<ConnectionStatePill>` | Sync visibility UX; validates orchestrator state transitions |
| 7 | `<ConflictResolutionScreen>` (composing `<DiffView variant="entity">`) | Tech-resolvable conflict path; most complex UI work |
| 8 | `<EscalationStatusRow>` shared component | Owner-escalation class mobile display; consumed by FE-B9 web queue |
| 9 | S3 multipart photo upload pipeline (`photo-upload.ts` + `<PhotoUploadProgress>`) | Photos are separate queue per §15.5 |
| 10 | Deferred voice upload integration (`voice-upload.ts`; upgrades FE-B3 stub) | Replaces `AsyncStorage` stub in `useDeferredVoiceUpload.ts` |
| 11 | `<MobileSyncStatusBar>` composing FE-B1 `<InFlightSyncIndicator>` | Composes all sync state into the persistent bottom bar |
| 12 | Auth edge case screens (`<DisabledAccountExportScreen>`, `<OfflineHardLimitWarning>`) | Robustness; deferred to last as rare paths |

---

## Section C — New Routes

| Route | File Path | Auth Required | RBAC | Notes |
|:---|:---|:---|:---|:---|
| Sync queue pending overview | `apps/mobile/app/(tabs)/(home)/sync/index.tsx` | Yes | `tech` | Full-screen list of pending operations; accessible from status bar tap |
| Conflict resolution detail | `apps/mobile/app/(tabs)/(home)/sync/conflict/[conflictId].tsx` | Yes | `tech` | Receives `conflictId`; loads from `GET /api/v1/mobile-sync/conflicts/{id}` |

> **Note**: The sync queue `<SyncQueueDrawer>` is a **bottom sheet modal**, not a route. It is composed into the app-level `_layout.tsx` and opened via `<ConnectionStatePill>` tap. This matches the spec §4 design decision: bottom-sheet accessible from anywhere without navigation.

---

## Section D — API Endpoint Consumption

All mobile-sync backend endpoints are **confirmed live** in `frontend/packages/shared-types/src/api-schema.d.ts`. No MSW stubs needed for sync endpoints. MSW stubs ARE needed for the sync session creation path during unit tests.

| Endpoint | Method | TanStack Query Hook | MSW Handler | Notes |
|:---|:---|:---|:---|:---|
| `/api/v1/mobile/sync-sessions/{id}/complete` | `POST` | `useCompleteSyncSession()` — `apps/mobile/features/offline-sync/hooks/useCompleteSyncSession.ts` | Not needed (live) | Called by orchestrator after successful push+pull cycle |
| `/api/v1/mobile-sync/conflicts/{id}` | `GET` | `useConflictDetail()` — same folder | Not needed (live) | Fetches full conflict for resolution screen |
| `/api/v1/mobile-sync/conflicts/{id}/resolve` | `POST` | `useResolveConflict()` — same folder | Not needed (live) | `resolution: 'use_local' \| 'use_server' \| 'escalate_to_owner'` |
| `/api/v1/owner/mobile-sync-escalations` | `GET` | Not consumed in FE-B7 (owner-side is FE-B9 web) | Not needed | Referenced for `<EscalationStatusRow>` deep-link only |
| `/api/v1/mobile-sync/state/{user_id}` | `GET` | `useSyncState()` — owner/admin visibility | Not needed (live) | Used by owner's mobile Owner tab status row |
| `/api/v1/photos/initiate-upload` | `POST` | Called directly in `photo-upload.ts` (not TanStack Query — fire-and-forget pipeline) | MSW stub needed for unit tests | Returns S3 presigned chunk URLs |
| `/api/v1/photos/complete-upload` | `POST` | Called directly in `photo-upload.ts` | MSW stub needed for unit tests | Finalizes after all chunks uploaded |
| `/api/v1/voice/upload-audio` | `POST` | Called directly in `voice-upload.ts` | MSW stub exists from FE-B3 (`mocks/handlers/voice.ts`) | FE-B7 upgrades to use WatermelonDB-persisted queue |

**MSW handlers to add for FE-B7**:

```
apps/mobile/mocks/handlers/sync.ts
  — POST /api/v1/mobile/sync-sessions   (create session)
  — POST /api/v1/mobile/sync-sessions/:id/complete
  — GET  /api/v1/mobile-sync/conflicts/:id  (mock conflict payloads for 4 severity classes)
  — POST /api/v1/mobile-sync/conflicts/:id/resolve

apps/mobile/mocks/handlers/photos.ts
  — POST /api/v1/photos/initiate-upload
  — POST /api/v1/photos/complete-upload
```

---

## Section E — Pattern Reuse Decisions

| Pattern | Arch §Reference | Component/Hook Used | Import Path |
|:---|:---|:---|:---|
| Optimistic UI with pending badges | §16.8 | `<PendingBadge>` (new in FE-B7) + `useOptimisticMutation()` (new in FE-B7) | `@pilot/ui/pending-badge` |
| Four-class severity visual treatment | §16.6 | `CONFLICT_CLASS_TOKENS` from FE-B4 | `@pilot/ui` |
| Track-changes diff renderer | §16.2 | `<DiffView variant="entity">` from FE-B5 — already has `entity` variant in locked interface | `@pilot/ui/diff-view` |
| In-flight sync indicator | §16.13 | `<InFlightSyncIndicator surface="mobile-sync">` from FE-B1 skeleton | `@pilot/ui/sync-indicator` |
| Mobile-to-web escalation | §16.11 | `<EscalationStatusRow>` (new in FE-B7) | `@pilot/ui/escalation-status` |
| Notification banner | — | `useNotificationQueue()` from FE-B1 — for `auto_notice` conflict banners | `@pilot/ui/notification-banner` |
| RFC 7807 error handling | §7.4 | `isProblemDetails()` from `apiClient` | `@pilot/shared-api` |
| Deferred voice processing | §15.7 / §6.7 | Upgrade `useDeferredVoiceUpload.ts` (FE-B3 stub) — same public API, WatermelonDB persistence | `apps/mobile/features/voice-quote-creation/hooks/useDeferredVoiceUpload.ts` |

**Critical reuse note — `<DiffView variant="entity">`**:
The `DiffView` `EntityDiffViewProps` variant was pre-included in the FE-B5 locked interface specifically for FE-B7. The mobile conflict resolution screen uses it with `showToggle={true}` and `defaultShowChanges={true}` (fields are visible by default in conflict context). No changes to the DiffView component are needed.

---

## Section F — Shared Module Interfaces

### F.1 `<PendingBadge>` Props Interface

**File**: `packages/ui/src/pending-badge/types.ts`

```typescript
// packages/ui/src/pending-badge/types.ts

export type PendingBadgeVariant =
  | 'pending'    // amber — queued, awaiting sync
  | 'syncing'    // amber pulse — actively in flight
  | 'failed'     // red — failed; retry/resolve CTA available
  | 'conflict';  // red — conflict requiring action

export interface PendingBadgeProps {
  /** Number of pending operations on this entity. 0 renders nothing. */
  count: number;
  /** Visual state determines color and animation */
  variant?: PendingBadgeVariant;
  /** Accessible label for screen readers. Defaults to "{count} pending sync" */
  accessibilityLabel?: string;
  /** Mobile: testID for Maestro targeting */
  testID?: string;
  /** Optional tap handler — typically opens sync queue drawer */
  onPress?: () => void;
  /** Web: additional Tailwind classes */
  className?: string;
}
```

**Rendering rules**:
- `count === 0`: renders `null` (no badge)
- `count > 0, variant='pending'`: amber dot with count number
- `count > 0, variant='syncing'`: pulsing amber dot
- `count > 0, variant='failed' | 'conflict'`: red dot with count; `onPress` opens sync queue or conflict resolution

---

### F.2 `useOptimisticMutation()` Hook Interface

**File**: `packages/ui/src/hooks/useOptimisticMutation.ts`

```typescript
// packages/ui/src/hooks/useOptimisticMutation.ts

export interface UseOptimisticMutationOptions<TVariables, TLocalRecord> {
  /**
   * Write to local state (WatermelonDB, Zustand, etc.) immediately.
   * Called synchronously on mutate(); receives full variables.
   * Must return a record that can be passed to rollbackFn if needed.
   */
  optimisticUpdate: (variables: TVariables) => Promise<TLocalRecord>;

  /**
   * Optional: undo the optimistic write on server error.
   * Called with the record returned from optimisticUpdate().
   * Defaults to marking the local record sync_status = 'failed'.
   */
  rollbackFn?: (localRecord: TLocalRecord, error: Error) => Promise<void>;

  /**
   * The mutation function itself (e.g., apiClient call).
   * Only called when device is online; otherwise the operation
   * stays in the local queue.
   */
  mutationFn?: (variables: TVariables) => Promise<void>;

  /** If true, skips calling mutationFn and defers to the SyncOrchestrator. Default: true */
  deferToOrchestrator?: boolean;
}

export interface UseOptimisticMutationReturn<TVariables> {
  mutate: (variables: TVariables) => void;
  mutateAsync: (variables: TVariables) => Promise<void>;
  isPending: boolean;
  isError: boolean;
  error: Error | null;
  reset: () => void;
}

export function useOptimisticMutation<TVariables, TLocalRecord = unknown>(
  options: UseOptimisticMutationOptions<TVariables, TLocalRecord>
): UseOptimisticMutationReturn<TVariables>;
```

**Key design decision**: `deferToOrchestrator = true` by default. The offline write hooks (`useCreateTimeEntry` etc.) write to WatermelonDB immediately; the `SyncOrchestrator` handles the push when it runs. `useOptimisticMutation` is the hook interface abstraction consumed by FE-B9 and FE-B12 for non-offline-entity optimistic patterns (e.g., settings saves, QB queue items).

---

### F.3 `<EscalationStatusRow>` Props Interface

**File**: `packages/ui/src/escalation-status/EscalationStatusRow.tsx`

```typescript
// packages/ui/src/escalation-status/types.ts

export type EscalationStatus =
  | 'pending'    // owner has not yet reviewed
  | 'resolved'   // owner resolved; loop closed
  | 'rejected';  // owner rejected the escalation

export interface EscalationStatusRowProps {
  /** The entity type involved in the escalation */
  entityType: 'time_entry' | 'expense' | 'photo' | 'change_order' | 'loto_check' | 'job_status_change' | 'job_note';
  /** Human-readable summary of the conflicting entity */
  entitySummary: string;
  /** Current resolution status */
  status: EscalationStatus;
  /** ISO timestamp when escalation was created */
  escalatedAt: string;
  /**
   * Deep-link URL to the owner's web resolution surface.
   * In FE-B7: stubbed as 'https://pilotfortrades.com/sync/escalations'.
   * In FE-B9: this becomes the real owner escalation queue route.
   */
  webDeepLink: string;
  /** Resolution outcome message (when status === 'resolved' | 'rejected') */
  resolutionMessage?: string;
  /** Mobile testID */
  testID?: string;
}
```

**Rendering rules**:
- `status='pending'`: amber accent, "Owner reviewing your sync conflict" + "View on web →" deep-link
- `status='resolved'`: green accent, "Owner resolved · {resolutionMessage}"
- `status='rejected'`: neutral accent, "Owner declined — your version discarded"

---

### F.4 `SyncOrchestrator` Class Interface

**File**: `apps/mobile/database/sync/orchestrator.ts`

```typescript
// apps/mobile/database/sync/orchestrator.ts

import type { Database } from '@nozbe/watermelondb';
import type { SyncPushResult, SyncPullResult, SyncConflict, SyncTrigger } from './types';

export type SyncTrigger =
  | 'foreground_transition'  // app came to foreground
  | 'network_online'          // OS reported connectivity
  | 'periodic_check'          // 30-second interval while active
  | 'manual'                  // user pressed "Sync now"
  | 'background';             // server-initiated silent push (BE-B9/A51; FE-B9 extends)

export interface SyncOrchestratorOptions {
  database: Database;
  /** Bound apiClient with current JWT */
  apiClient: typeof import('../../../lib/api-client').apiClient;
  /** Device identifier (Expo Constants.deviceId) */
  deviceId: string;
  /** Called on every sync state change for UI updates */
  onStateChange?: (state: SyncState) => void;
  /** Called when a conflict requires tech action */
  onTechResolvableConflict?: (conflict: SyncConflict) => void;
  /** Called when a conflict is escalated to owner */
  onOwnerEscalation?: (conflict: SyncConflict) => void;
}

export type SyncState =
  | { status: 'idle'; pendingCount: number; lastSyncedAt: string | null }
  | { status: 'syncing'; pendingCount: number; progress: number }
  | { status: 'error'; pendingCount: number; error: Error; lastSyncedAt: string | null }
  | { status: 'paused'; pendingCount: number; reason: 'offline' | 'hard_limit_exceeded' };

export class SyncOrchestrator {
  constructor(options: SyncOrchestratorOptions);

  /**
   * Run a full push+pull sync cycle.
   * Called by all sync triggers. Safe to call concurrently — second call
   * is a no-op if a sync is already in progress.
   */
  sync(trigger: SyncTrigger): Promise<void>;

  /**
   * Push all pending items for a single operation type.
   * Used internally; also exposed for per-entity-type retry.
   */
  push(operationType?: OfflineEntityType): Promise<SyncPushResult>;

  /**
   * Pull server state updates for cached entities.
   */
  pull(): Promise<SyncPullResult>;

  /**
   * Handle a resolved conflict (from ConflictResolutionScreen).
   * Updates local WatermelonDB state after server ACKs the resolution.
   */
  applyConflictResolution(
    conflictId: string,
    resolution: 'use_local' | 'use_server'
  ): Promise<void>;

  /**
   * Returns the current sync state observable.
   */
  getState(): SyncState;

  /** Get pending count from local DB */
  getPendingCount(): Promise<number>;

  /**
   * Force-quit recovery: on app launch, reset 'syncing' → 'pending'
   * for all items stuck in-flight per §15.8.
   */
  recoverFromForceQuit(): Promise<void>;
}

export type OfflineEntityType =
  | 'time_entry'
  | 'expense'
  | 'photo'
  | 'change_order'
  | 'loto_check'
  | 'job_status_change'
  | 'job_note'
  | 'voice_audio';
```

**Sync triggers — implementation notes**:
- `foreground_transition`: subscribe to `AppState.addEventListener('change')` in app `_layout.tsx`
- `network_online`: `NetInfo.addEventListener()` — triggers on connectivity change to `isConnected === true`
- `periodic_check`: `setInterval(30_000)` in a `useEffect` inside the sync provider; cleared on unmount
- `manual`: called directly from `<SyncNowButton>` handler
- `background`: FE-B9 extends this path when it implements the background sync settings UI. In FE-B7, the `'background'` trigger type is defined in the interface but its invocation is wired in FE-B9.

**Auth expiry during sync**:
- On `401`: `apiClient` JWT interceptor (FE-B2) fires refresh → on success, `SyncOrchestrator` retries
- On permanent auth failure (account disabled): orchestrator calls `onStateChange({ status: 'error', error: DisabledAccountError })` → app renders `<DisabledAccountExportScreen>`

---

### F.5 WatermelonDB Model Base Fields Interface

All 7 model classes share these sync-control fields:

```typescript
// apps/mobile/database/models/SyncableModel.ts (abstract base)

import { Model } from '@nozbe/watermelondb';
import { field, date, readonly } from '@nozbe/watermelondb/decorators';

export abstract class SyncableModel extends Model {
  @field('sync_status') syncStatus!: 'pending' | 'syncing' | 'synced' | 'failed' | 'conflict';
  @field('idempotency_key') idempotencyKey!: string;     // UUID v4; never changes
  @field('sync_error') syncError?: string;               // last sync error message
  @field('retry_count') retryCount!: number;             // for exponential backoff
  @date('client_capture_at') clientCaptureAt!: Date;     // device time at capture
  @date('server_received_at') serverReceivedAt?: Date;   // populated after sync
  @readonly @date('created_at') createdAt!: Date;
}
```

---

### F.6 `SyncQueueDrawer` State Interface (Zustand store)

```typescript
// apps/mobile/features/offline-sync/store.ts

export interface SyncQueueStore {
  isDrawerOpen: boolean;
  openDrawer: () => void;
  closeDrawer: () => void;
  /** Current sync state from SyncOrchestrator — updated via onStateChange callback */
  syncState: SyncState;
  setSyncState: (state: SyncState) => void;
}
```

---

## Section G — Open Questions Resolved

### G.1 WatermelonDB model location: `apps/mobile/database/` or `apps/mobile/src/database/`?

**Resolution**: **`apps/mobile/database/`** — NO `src/` prefix.

The methods doc §1 project structure table explicitly shows `apps/mobile/database/` at the top level, matching the `apps/mobile/features/`, `apps/mobile/hooks/`, `apps/mobile/theme/` pattern already in place from FE-B0 through FE-B6. The confirmed `apps/mobile/` directory listing shows no `src/` directory anywhere; all code lives directly under the app root.

### G.2 Which fields from the backend schema does each WatermelonDB model mirror?

**Resolution**: Each model mirrors the **minimum set of fields needed for offline capture + sync push payload**, not the full backend schema. This is intentional — WatermelonDB is a write buffer, not a relational mirror.

Key confirmed facts from DB schema:
- `job_time_entry` has `client_capture_at TIMESTAMPTZ NULL` and `server_received_at TIMESTAMPTZ NULL` — matches §15.2 schema requirement
- `job_expense` (the `expense` entity) has `incurred_at`, `cost_cents`, `job_expense_category_code`, natural-key dedup index on `(user_id, job_id, incurred_at, cost_cents)` — model mirrors these
- `job_notes` has natural-key dedup index on `(created_by, job_id, created_at)` — model captures `createdBy` and `clientCaptureAt`
- `change_order` has `job_id`, `tenant_id`, soft-delete pattern via `is_active`
- `loto_check` — not in the shared DB schema JSON excerpt but confirmed in §15.2 offline contract; model is minimal: `jobId`, `checkType`, `confirmedAt`, `gpsLat?`, `gpsLng?`
- `job_status_change` — confirmed in §15.2 as an offline-capable operation; minimal fields: `jobId`, `fromStatus`, `toStatus`

### G.3 Custom sync orchestrator vs WatermelonDB built-in sync

**Resolution**: **Custom `SyncOrchestrator` class**. Confirmed per:
- Methods doc §11.2: "custom sync logic against BE-B7a/A37 push/pull endpoints"
- FE impl plan §6 FE-B7 batch detail: "Custom sync logic, not WatermelonDB built-in sync"
- The four-class conflict classification (BE-B7b/A40), idempotency UUID + natural-key fallback, deferred-voice upload reconnect logic, and S3 multipart photo pipeline all require custom orchestration that WatermelonDB's built-in `synchronize()` cannot provide

### G.4 `<PendingBadge>` and `useOptimisticMutation()` full TypeScript interface

**Resolution**: Defined in Section F.1 and F.2 above. Key decisions:
- `PendingBadge` renders `null` on `count === 0` — no visual noise when synced
- `useOptimisticMutation()` defaults to `deferToOrchestrator = true` — the hook writes locally; `SyncOrchestrator` handles the push. This is distinct from FE-B4's `useStalenessRetry()` which is for online-only optimistic mutations
- FE-B9 and FE-B12 consume these interfaces **unchanged**

### G.5 `requires_review` conflict — entity-type-specific DiffView variants

**Resolution**: Use `<DiffView variant="entity">` with the `field_diffs` array from the backend `ConflictDetailResponse`. The `entity` variant already exists in the FE-B5 locked `DiffViewProps` discriminated union (`EntityDiffViewProps`).

Entity-specific field label overrides (how `field_name` maps to human-readable labels) are handled by extending `fieldNameToLabel()` in `packages/ui/src/diff-view/utils.ts` with the offline-entity domain override map:

```typescript
// Additional entries added to fieldNameToLabel() in diff-view/utils.ts
const OFFLINE_ENTITY_FIELD_LABELS: Record<string, string> = {
  started_at: 'Clock In',
  ended_at: 'Clock Out',
  hours: 'Hours',
  hours_remaining_estimate: 'Estimated Hours Remaining',
  cost_cents: 'Amount',
  job_expense_category_code: 'Category',
  to_status: 'New Status',
  from_status: 'Previous Status',
  content: 'Note Text',
  // ... etc.
};
```

This is a non-breaking additive change to `diff-view/utils.ts` — not a prop interface change.

### G.6 `<EscalationStatusRow>` deep-link before FE-B9 web queue exists

**Resolution**: **Stub the deep-link**. In FE-B7, `webDeepLink` defaults to `https://pilotfortrades.com/sync/escalations` (the marketing-site URL with a path that will be wired in FE-B9). The `<EscalationStatusRow>` renders the link using `Linking.openURL()`. Before FE-B9 ships, tapping the link opens the browser to the Pilot site root. This is acceptable MVP behavior since `owner_escalation` class conflicts are rare and the owner receives a push notification directly.

FE-B9 will update the deep-link to `pilot://sync/escalations/{escalationId}` and set up the universal link handler.

### G.7 FE-B3 → FE-B7 deferred voice handoff — no breaking changes

**Resolution**: `useDeferredVoiceUpload.ts` already has this comment in its stub implementation:
> "STUB — FE-B7 will replace the queue persistence with WatermelonDB. When FE-B7 ships, the queue persistence is upgraded to WatermelonDB without changing this hook's public API."

The **public API stays identical**. FE-B7 only changes the internal persistence mechanism from `AsyncStorage` key `pilot:deferredVoiceQueue` to a WatermelonDB `voice_audio_queue` table. The hook signature:

```typescript
// Existing public API (unchanged):
interface UseDeferredVoiceUploadReturn {
  queueAudio: (audioUri: string, capturedAt: Date, sessionId?: string) => Promise<void>;
  pendingCount: number;
  uploadPending: () => Promise<void>; // called by SyncOrchestrator on reconnect
}
```

The `SyncOrchestrator.push('voice_audio')` calls `uploadPending()` internally. The FE-B3 voice session shell continues to call `queueAudio()` — no changes needed in FE-B3 code.

### G.8 Disabled-account export edge case (§15.12)

**Resolution**:
- **File format**: JSON dump of all WatermelonDB tables with `sync_status !== 'synced'`. Each record is serialized with field names matching the backend schema (not WatermelonDB internal names).
- **Where the button appears**: `<DisabledAccountExportScreen>` replaces the normal login screen when `sessionExpiredEmitter` fires with `reason: 'account_disabled'`. This is a new reason code added to the emitter in FE-B7.
- **Export mechanism**: uses `expo-sharing` + `expo-file-system` to write a `.json` file to the device temp directory and open the native share sheet. The tech can share via email, AirDrop, Files app, etc. **No Pilot API call** — the account is disabled.
- **Export schema**:
```json
{
  "export_format_version": 1,
  "exported_at": "2026-05-22T19:00:00Z",
  "tenant_id": "...",
  "user_id": "...",
  "records": {
    "time_entries": [...],
    "expenses": [...],
    "photos": [{ "local_uri": "...", "note": "Photo file not included in this export; URI references device storage" }],
    "change_orders": [...],
    "loto_checks": [...],
    "job_status_changes": [...],
    "job_notes": [...]
  }
}
```

---

## Section H — External Dependency Status

| Dependency | Status | Mock Strategy | Tom Action Required |
|:---|:---|:---|:---|
| **BE-B7a** (offline sync foundation) | ✅ **LIVE** — confirmed via `api-schema.d.ts`: `mobile-sync/state`, `sync-sessions/complete` endpoints present | N/A | None |
| **BE-B7b** (conflict engine) | ✅ **LIVE** — confirmed: `mobile-sync/conflicts/{id}/resolve`, `owner/mobile-sync-escalations/{id}/resolve` endpoints present | N/A | None |
| **S3 multipart photo upload** | ⚠️ **BE-B7a scope** — `POST /api/v1/photos/initiate-upload` and `complete-upload` NOT yet confirmed in `api-schema.d.ts` (not in search results for `photos/initiate-upload`) | MSW handlers in `apps/mobile/mocks/handlers/photos.ts` | Confirm photo upload endpoints with backend; if not shipped, use MSW through to integration testing |
| **iOS App Store Connect / provisioning** | ⚠️ Not provisioned | Expo Go dev client + EAS preview builds | Required before production release |
| **APNs certificate** | ⚠️ Not provisioned | Mock push notification queue in dev | Required before production release; needed by FE-B9 background sync |
| **FCM credentials** | ⚠️ Not provisioned | Mock push notification queue | Same as APNs |
| **`expo-sqlite` / WatermelonDB JSI adapter** | ✅ Listed in `apps/mobile/README.md` as installed: "Offline Sync: WatermelonDB + JSI SQLite" | N/A | Verify `@nozbe/watermelondb` is in `apps/mobile/package.json` before starting |
| **`expo-sharing` + `expo-file-system`** | Likely installed (standard Expo SDK 54) | N/A | Verify before implementing export feature |
| **`@react-native-community/netinfo`** | Needed for network state change triggers | — | Add to `apps/mobile/package.json` if not present |

---

## Section I — Test Plan

### I.1 Unit Tests (target: 100+, Jest mobile / Vitest packages/ui)

| Test File | Component/Hook | Coverage |
|:---|:---|:---|
| `packages/ui/src/pending-badge/__tests__/PendingBadge.test.tsx` | `<PendingBadge>` | count=0 renders null; all 4 variants; onPress fires; ARIA label; testID present |
| `packages/ui/src/hooks/useOptimisticMutation.test.ts` | `useOptimisticMutation()` | immediate local write; deferToOrchestrator path; rollback on error; isPending state |
| `packages/ui/src/escalation-status/__tests__/EscalationStatusRow.test.tsx` | `<EscalationStatusRow>` | all 3 status variants; deep-link href; accessibility role |
| `apps/mobile/__tests__/batch_fe_b7/database-models.unit.test.ts` | All 7 model classes | CRUD in WatermelonDB; sync_status transitions; idempotency_key generation |
| `apps/mobile/__tests__/batch_fe_b7/orchestrator.unit.test.ts` | `SyncOrchestrator` | push happy path; idempotency UUID sent as header; natural-key dedup; force-quit recovery; concurrent sync no-op |
| `apps/mobile/__tests__/batch_fe_b7/conflict-handlers.unit.test.ts` | `conflict-handlers.ts` | all 4 severity class handlers; `auto_silent` clears badge; `auto_notice` fires banner; `tech_resolvable` opens resolution screen; `owner_escalation` creates escalation row |
| `apps/mobile/__tests__/batch_fe_b7/offline-write-hooks.unit.test.ts` | 7 `useCreate*` hooks | each hook writes to WatermelonDB with pending status; generates idempotency key; `<PendingBadge>` count increases |
| `apps/mobile/__tests__/batch_fe_b7/photo-upload.unit.test.ts` | `usePhotoUpload()` / `photo-upload.ts` | chunk tracking; resume from last completed chunk; WiFi preference gate |
| `apps/mobile/__tests__/batch_fe_b7/voice-upload-upgrade.unit.test.ts` | `useDeferredVoiceUpload.ts` | public API unchanged after FE-B3 stub → WatermelonDB upgrade; queue persists across app restart |
| `apps/mobile/__tests__/batch_fe_b7/offline-limit.unit.test.ts` | `<OfflineHardLimitWarning>`, soft/hard limit logic | 24h soft notification; 72h hard block; `offline_hard_limit_hours=null` disables block |
| `apps/mobile/__tests__/batch_fe_b7/connection-pill.unit.test.ts` | `<ConnectionStatePill>` | all 4 states render correctly; tap opens drawer |
| `apps/mobile/__tests__/batch_fe_b7/sync-queue-drawer.unit.test.ts` | `<SyncQueueDrawer>` | 4 sections render; action-needed first; inline retry/resolve CTAs |
| `apps/mobile/__tests__/batch_fe_b7/conflict-resolution-screen.unit.test.tsx` | `<ConflictResolutionScreen>` | DiffView renders with entity variant; "Use my version" calls resolve API; "Send to owner" creates escalation |
| `apps/mobile/__tests__/batch_fe_b7/disabled-account.unit.test.tsx` | `<DisabledAccountExportScreen>` | renders on account-disabled emitter; export button triggers share sheet; JSON structure correct |

**Total unit target: 100+** (14 test files × 7–10 assertions average)

### I.2 Integration Tests (target: 20+)

```
apps/mobile/__tests__/batch_fe_b7/

offline-write-sync-cycle.integration.test.ts
  — offline write time entry → reconnect → sync → server state matches

offline-write-multi-entity.integration.test.ts
  — offline create expense + photo + note → sync → all 3 entities appear server-side

conflict-requires-review-modal.integration.test.tsx
  — sync triggers conflict with tech_resolvable severity → ConflictResolutionScreen renders
  — → use_local resolution → conflict cleared in WatermelonDB → badge clears

auto-recovery-flow.integration.test.ts
  — auto_silent conflict → sync proceeds silently → no UI interruption
  — auto_notice conflict → NotificationBanner fires → queue drawer shows note

owner-escalation-flow.integration.test.tsx
  — owner_escalation severity → EscalationStatusRow appears → deep-link renders

photo-multipart-upload.integration.test.ts
  — initiate upload → chunk 1 succeeds → simulate mid-upload failure → resume from chunk 2

photo-wifi-preference.integration.test.ts
  — photo_upload_wifi_only=true + cellular network → photo stays 'pending' with WiFi tag
  — → switch to WiFi → photo upload proceeds

deferred-voice-upload.integration.test.ts
  — go offline → queueAudio() → reconnect → orchestrator calls uploadPending() → voice endpoint hit

hard-limit-block.integration.test.ts
  — advance time to 72h offline → OfflineHardLimitWarning renders → new writes blocked

force-quit-recovery.integration.test.ts
  — write entities with status='syncing' to WatermelonDB → simulate app restart
  — → recoverFromForceQuit() resets to 'pending' → sync retries with same idempotency keys

disabled-account-export.integration.test.tsx
  — auth emitter fires with account_disabled reason → DisabledAccountExportScreen renders
  — → export button → share sheet opens → JSON contains all pending records

sync-indicator-composes-fe-b1.integration.test.tsx
  — MobileSyncStatusBar renders InFlightSyncIndicator with surface="mobile-sync"
  — → pending count from WatermelonDB reflected in indicator

rbac-sync-routes.integration.test.tsx
  — tech role can access conflict resolution screen
  — → RoleGate applied at (home)/sync routes
```

**Total integration target: 20+** (13 test files with primary + error paths)

### I.3 E2E Tests (target: 5+, Maestro)

```
apps/mobile/e2e/batch_fe_b7/

offline-sync-full-cycle.flow.yaml
  — go offline → create time entry, expense, job note → reconnect → sync completes → 
    server shows all 3 entities; badges clear on all

mid-sync-network-drop.flow.yaml
  — begin sync → toggle airplane mode → reconnect → sync resumes; no duplicates

conflict-resolution-e2e.flow.yaml
  — (requires two-device simulation OR backend seeding) seed a tech_resolvable conflict
  — → app foreground → ConflictResolutionScreen appears → tap "Use my version" → resolves

deferred-voice-processed-online.flow.yaml
  — go offline → start voice session → record audio → reconnect → 
    "Processing your voice command..." banner → intent completes

photo-upload-resume.flow.yaml
  — capture photo → start upload → kill app mid-upload → reopen → 
    upload resumes from last chunk → thumbnail shows uploaded state
```

### I.4 Accessibility Audit Checkpoints

- `<ConflictResolutionScreen>`: `role="main"`, `aria-label="Sync conflict"`, focus set to Conflict Explainer on mount; action bar buttons have explicit `accessibilityLabel`
- `<SyncQueueDrawer>`: section headers use `accessibilityRole="header"`; each item row has `accessibilityLabel` combining entity type + status; `<SyncNowButton>` disabled state announced to screen readers
- `<PendingBadge>`: `accessibilityLabel` defaults to `"{count} pending sync"` overridable via prop
- `<EscalationStatusRow>`: deep-link has `accessibilityHint="Opens owner resolution page in browser"`
- `<DisabledAccountExportScreen>`: `role="alert"`, `aria-live="assertive"` for the "account disabled" message; export button has accessible name
- All 7 offline write hooks: WatermelonDB operations are async — loading states wired via `<LoadingState type="optimistic">` from FE-B1

---

## Appendix — Mobile File Tree After FE-B7

```
apps/mobile/
├── app/
│   └── (tabs)/
│       └── (home)/
│           ├── sync/
│           │   ├── index.tsx                    # NEW: pending sync overview
│           │   └── conflict/
│           │       └── [conflictId].tsx          # NEW: conflict resolution detail
│           ├── voice/
│           ├── quotes/
│           └── _layout.tsx
├── database/                                    # NEW: WatermelonDB
│   ├── index.ts                                 # DB singleton
│   ├── schema.ts                                # appSchema
│   ├── models/
│   │   ├── SyncableModel.ts                     # Abstract base class
│   │   ├── TimeEntry.ts
│   │   ├── Expense.ts
│   │   ├── Photo.ts
│   │   ├── ChangeOrder.ts
│   │   ├── LotoCheck.ts
│   │   ├── JobStatusChange.ts
│   │   └── JobNote.ts
│   └── sync/
│       ├── orchestrator.ts                      # SyncOrchestrator class
│       ├── conflict-handlers.ts                 # 4-class handlers
│       ├── photo-upload.ts                      # S3 multipart pipeline
│       ├── voice-upload.ts                      # Deferred voice upload
│       └── types.ts
├── features/
│   ├── offline-sync/                            # NEW: surface feature folder
│   │   ├── components/
│   │   │   ├── ConnectionStatePill.tsx
│   │   │   ├── SyncQueueDrawer.tsx
│   │   │   ├── SyncQueueItem.tsx
│   │   │   ├── SyncQueueSection.tsx
│   │   │   ├── SyncNowButton.tsx
│   │   │   ├── ConflictResolutionScreen.tsx
│   │   │   ├── ConflictExplainer.tsx
│   │   │   ├── ConflictVersionCard.tsx
│   │   │   ├── ConflictActionBar.tsx
│   │   │   ├── PhotoUploadProgress.tsx
│   │   │   ├── MobileSyncStatusBar.tsx
│   │   │   ├── DisabledAccountExportScreen.tsx
│   │   │   └── OfflineHardLimitWarning.tsx
│   │   ├── hooks/
│   │   │   ├── useCreateTimeEntry.ts
│   │   │   ├── useCreateExpense.ts
│   │   │   ├── useCreatePhoto.ts
│   │   │   ├── useCreateChangeOrder.ts
│   │   │   ├── useConfirmLoto.ts
│   │   │   ├── useChangeJobStatus.ts
│   │   │   ├── useCreateJobNote.ts
│   │   │   ├── usePhotoUpload.ts
│   │   │   ├── useCompleteSyncSession.ts        # TanStack Query hook
│   │   │   ├── useConflictDetail.ts             # TanStack Query hook
│   │   │   └── useResolveConflict.ts            # TanStack Query hook
│   │   └── store.ts                             # SyncQueueStore (Zustand)
│   └── voice-quote-creation/
│       └── hooks/
│           └── useDeferredVoiceUpload.ts        # UPGRADED: AsyncStorage → WatermelonDB

packages/ui/src/
├── pending-badge/                               # NEW: FE-B7 establishes
│   ├── web/PendingBadge.tsx
│   ├── mobile/PendingBadge.tsx
│   ├── types.ts
│   └── index.ts
├── escalation-status/                           # NEW: FE-B7 establishes
│   ├── EscalationStatusRow.tsx                  # Mobile-only (Gluestack)
│   ├── types.ts
│   └── index.ts
├── hooks/
│   └── useOptimisticMutation.ts                 # NEW: FE-B7 establishes
└── diff-view/
    └── utils.ts                                 # EXTENDED: add offline entity field labels
```

---

## Appendix — `packages/ui/src/index.ts` Additions (FE-B7 section)

```typescript
// ── FE-B7 Exports ─────────────────────────────────────────────────────────────
// PendingBadge + useOptimisticMutation establish optimistic UI with pending badges (§16.8).
// Consumed by FE-B9 (background sync), FE-B12 (account settings async ops).
// ⚠️ Interfaces locked — changes require FE-B9 and FE-B12 impact review.

export { PendingBadge } from './pending-badge';
export type { PendingBadgeProps, PendingBadgeVariant } from './pending-badge/types';

export { useOptimisticMutation } from './hooks/useOptimisticMutation';
export type {
  UseOptimisticMutationOptions,
  UseOptimisticMutationReturn,
} from './hooks/useOptimisticMutation';

// EscalationStatusRow establishes the mobile-to-web escalation pattern (§16.11).
// Consumed by FE-B9 (full owner escalation flow).
export { EscalationStatusRow } from './escalation-status';
export type {
  EscalationStatusRowProps,
  EscalationStatus,
} from './escalation-status/types';
```

---

*Design session complete. All 8 open design questions resolved. Section F provides full TypeScript interfaces for `<PendingBadge>`, `useOptimisticMutation()`, `<EscalationStatusRow>`, and `SyncOrchestrator` — consumed without changes by FE-B9 and FE-B15.*
