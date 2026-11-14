# FE-B8 Batch Design — Calendar Conflict Resolution Web (Pass 3 Flow 6)

**Status**: Ready for Implementation  
**Date**: 2026-05-25  
**Author**: Pilot Architect  
**Prerequisite Batches**: FE-B0, FE-B1, FE-B2, FE-B3, FE-B4, FE-B5, FE-B6, FE-B7  
**Backend Gate**: BE-B6 (A32–A36 calendar conflict resolution — all endpoints live)  
**Gates Downstream**: FE-B9 (`<IntegrationConflictResolver>` with `integration="quickbooks"`)  
**Test Subfolder**: `apps/web/__tests__/batch_fe_b8/`

---

## Prerequisite Reads Completed

| Source | Key facts extracted |
|:---|:---|
| `frontend-pass-3-flow-6-calendar-conflict-resolution-spec.md` | 14 locked design decisions; A32–A36 BE additions; voice patterns; deletion-conflict UX; auto-expiry two-tier config |
| `pilot-app-mvp-frontend-impl-plan.md §6 FE-B8` | 7-item execution order; 40+ unit, 10+ integration, 2+ E2E targets; `<IntegrationConflictResolver>` locked interface requirement |
| `mvp-arch.md §13.5, §13.7, §16.2–16.4, §16.6, §16.10, §16.13` | Field-diff payload shape; resolution paths; SSE channel; four-class severity; bilateral integration pattern |
| `backend/api/routes/calendar_conflicts.py` | Exact Pydantic schemas: `ConflictListItem`, `ConflictDetailResponse`, `FieldDiffResponse`, `ConflictResolveRequest/Response`; resolution enum values per conflict_type |
| `backend/api/routes/calendar_integration.py` | `CalendarConnectionStatus` schema: `is_connected`, `connection_status`, `last_successful_sync_at`, `pending_conflicts_count`, `requires_reconnect` |
| `packages/ui/src/diff-view/types.ts` | `IntegrationDiffViewProps` for `variant="calendar-event"`: `fieldDiffs: DiffField[]`, `entityLabel`, `sideLabels` — LOCKED interface |
| `packages/ui/src/hooks/useStalenessRetry.ts` | Exact signature: `mutationFn`, `onConflict(refreshedState, prevVars)`, `renderConflictContent`, `StalenessDialog` return component |
| `packages/ui/src/hooks/useSseChannel.ts` | `path`, `onMessage(SseMessage)`, `fallbackToPollingMs`, `pollFn`, `enabled` props; LOCKED interface |
| `packages/ui/src/diff-view/web/DiffView.tsx` | `calendar-event` branch already renders side-by-side with `sideLabels.base` / `sideLabels.modified` headers and amber/green/red `DiffField` rows |
| `packages/ui/src/voice-confirm-turn/VoiceConfirmTurn.tsx` | RN component; `prompt: string`, `onConfirm`, `onCancel`, `isProcessing`; announces to accessibility |
| `packages/ui/src/sync-indicator/web/InFlightSyncIndicator.tsx` | `surface`, `state`, `pendingCount`, `lastSyncedAt`, `amberThreshold`, `onManualSync`, `compact` props |
| `packages/ui/src/index.ts` | All components confirmed exported; `normalizeFieldDiffs` exported from `diff-view/utils` |
| `apps/web/src/app/` | Settings currently has only `(authed)/settings/page.tsx` — no `integrations/` subtree yet |
| `packages/ui/src/tokens.ts` | Full token ramps confirmed: `alert`, `margin`, `fault`, `brand`, `neutral` |

---

## Resolved Design Decisions

### Decision 1 — `IntegrationConflictResolver` Component API

**How fieldDiffs are passed**: The component receives the **full `ConflictDetailResponse` object as a prop** (`conflict: CalendarConflictDetail`). It does NOT fetch internally — the parent page hook fetches and passes the resolved data down. This keeps the resolver presentation-only and independently testable.

**Integration type parameterization**: Union literal `integration: 'calendar' | 'quickbooks'`. Not generic — the union literal is sufficient for two known integrations, keeps the public API scannable, and avoids TypeScript complexity that buys nothing in practice.

**Domain-specific slot**: An optional `renderDomainSpecificFields?: (conflict: T) => React.ReactNode` render-prop slot allows FE-B9 to render QB-only fields (`financial_delta_cents`, `tax_period_warning`) without forking the resolver. For the calendar integration in FE-B8, this slot receives `null`.

**DiffView composition**: `<DiffView variant="calendar-event">` already supports `IntegrationDiffViewProps` with `fieldDiffs: DiffField[]` and `sideLabels`. The `field_diffs` from BE-B6/A32 are mapped via the existing `normalizeFieldDiffs()` utility. No extension needed to `DiffView`.

**sideLabels source**: The `sideLabels.modified` label comes from `conflict.provider_display_name` (read from the integration record, not hardcoded as "Google Calendar"), satisfying spec Decision C.E.

### Decision 2 — Deletion Conflict Layout Branching

The resolver detects conflict type via `conflict.conflict_type`:
- `'modified_modified'` → standard two-column diff layout with `<DiffView variant="calendar-event">`
- `'deleted_modified'` | `'modified_deleted'` → deletion conflict layout (no DiffView)

**Deletion conflict layout**: A separate sub-component `<DeletionConflictView>` renders inside `IntegrationConflictResolver` when the type discriminator matches. It shows:
- A contextual icon + amber banner explaining what happened
- Two large verb buttons (primary + secondary) with explicit language per spec Decision 7
- The verb pairs per conflict_type:
  - `deleted_modified`: `"Restore the Job from Calendar"` (primary) / `"Delete from Calendar Too"` (secondary-destructive)
  - `modified_deleted`: `"Recreate the Calendar Event"` (primary) / `"Delete the Pilot Job"` (secondary-destructive)

Both sub-layouts live in `IntegrationConflictResolver` behind a `conflictType` type-discriminator. They are **not** separate exported components — the resolver's public API remains a single component regardless of layout.

### Decision 3 — Two-Column Diff Layout Strategy

**Layout**: CSS Grid with `grid-cols-2 gap-4` Tailwind class. The existing `<DiffView variant="calendar-event">` implementation already renders a two-column header (`sideLabels.base` / `sideLabels.modified`) with field rows below. The `DiffField` component renders a two-cell layout with base value on the left and modified value on the right, using amber/green/red tints from the token system.

**Alignment**: `DiffField` rows span the full width as a grid row — the field name is a spanning header, then values appear side-by-side in columns. This matches the existing `DiffView.tsx` implementation exactly; no new layout primitives needed.

**Responsive narrowing**: Below `md` breakpoint, the two-column diff collapses to a stacked layout via `md:grid-cols-2 grid-cols-1`. The spec notes this is web-only; narrow viewports are informational quality degradation only, not a blocker (conflict resolution is a deliberate "at my desk" action).

**shadcn/ui primitives**: The existing `DiffView` uses plain Tailwind div+span primitives — no shadcn `Card` or `Table` needed. The page layout shell (two-panel Settings layout) uses standard Pilot `(authed)/layout.tsx` padding conventions.

### Decision 4 — Route Structure and Page Component Tree

**Route tree** (new files, none exist yet):

```
apps/web/src/app/(authed)/settings/integrations/
  calendar/
    page.tsx                          ← CalendarIntegrationSettingsPage
    conflicts/
      [id]/
        page.tsx                      ← CalendarConflictDetailPage
```

**Conflict queue placement**: The queue is a **section within** `/settings/integrations/calendar` (spec Decision 1 + 2). It renders below the connection status section with a `#conflicts` anchor. When routed from the dispatch board sync indicator, the URL appends `?scroll=conflicts` and the page scrolls to the anchor on mount.

**Page vs composable split**:
- `CalendarIntegrationSettingsPage` — page-level; composes `<CalendarConnectionStatusCard>`, `<CalendarConflictQueue>`, `<CalendarSyncActivityLog>`, `<CalendarAutoExpirySettings>`, `<InFlightSyncIndicator surface="calendar">`
- `CalendarConflictDetailPage` — page-level; composes `<IntegrationConflictResolver integration="calendar">` + `<StalenessDialog>` from `useStalenessRetry`
- All composable sub-components live in `apps/web/src/features/calendar-conflict/`

### Decision 5 — SSE-Driven Live Queue Updates

**Channel**: `useSseChannel` with `path: '/api/v1/integrations/calendar/conflicts/stream'`. This is a new SSE endpoint (BE-B6/A35 scope). If the endpoint is not yet live, an MSW handler mocks it.

**Event handling strategy**: SSE messages carry cache-invalidation cues only (consistent with dispatch board pattern from FE-B4). When an SSE event arrives:
- `conflict_detected` event → `queryClient.invalidateQueries({ queryKey: ['calendar-conflicts'] })`
- `conflict_resolved` event → `queryClient.invalidateQueries({ queryKey: ['calendar-conflicts'] })` + invalidate specific `['calendar-conflict', id]`
- `calendar_sync_status` event → `queryClient.invalidateQueries({ queryKey: ['calendar-status'] })`

**No splice of individual records** — full list refetch on every event. At the expected conflict volume (< 20 pending at any time for a 100-user tenant per architecture constraints), full refetch is cheaper than conflict-free splice logic.

**SSE event shape** (matches existing `useSseChannel` `SseMessage.type` pattern):
```json
{ "type": "conflict_detected", "data": "{\"conflict_id\": \"...\", \"job_id\": \"...\"}" }
{ "type": "conflict_resolved", "data": "{\"conflict_id\": \"...\", \"resolution\": \"accept_local\"}" }
{ "type": "calendar_sync_status", "data": "{\"connection_status\": \"connected\", \"pending_conflicts_count\": 3}" }
```

**Fallback**: `fallbackToPollingMs: 60_000` with `pollFn` that invalidates `['calendar-conflicts']`. Matches the dispatch board's 60s fallback pattern.

### Decision 6 — Auto-Expiry Countdown UI Placement

**Queue row**: An inline `<ExpiryCountdownBadge>` renders in the `ConflictType` column area of the queue table row when `days_until_expiry <= 7`. This is a computed value derived from `detected_at + auto_expire_days` (fetched from tenant settings or system default 30 days).

**Detail page header**: A `<NotificationBanner>` (from `packages/ui/src/notification-banner/`) renders at the top of the conflict detail view when the pre-warning is active.

**Color threshold**:
- `> 3 days remaining` → amber: `bg-alert-50` border `border-alert-200` text `text-alert-600`
- `<= 3 days remaining` → red: `bg-fault-50` border `border-fault-200` text `text-fault-600`

Tokens used: `colors.alert[50]`, `colors.alert[200]`, `colors.alert[600]`, `colors.fault[50]`, `colors.fault[200]`, `colors.fault[600]`.

The 3-day threshold aligns with urgency: if the conflict auto-resolves in 3 days and the owner hasn't acted, it's operationally urgent (affects scheduled jobs). Token value `3` is a named constant `EXPIRY_URGENT_THRESHOLD_DAYS = 3` in the component file.

### Decision 7 — Mobile Owner Calendar Sync Status Row

**Shared component**: A new `<CalendarSyncStatusRow>` component in `packages/ui/src/calendar-sync-status/` mirrors the QuickBooks sync status row pattern (from FE-B7 `<EscalationStatusRow>` for comparison). It is mobile-scoped in implementation (React Native primitives) but lives in `packages/ui/` for architectural consistency.

**File path**: `packages/ui/src/calendar-sync-status/CalendarSyncStatusRow.tsx`

**Data consumption**: A `useCalendarStatus()` TanStack Query hook in `apps/mobile/features/owner-tab/hooks/useCalendarStatus.ts` calls `GET /api/v1/integrations/calendar/status` (A35 endpoint with `pending_conflicts_count`, `connection_status`, `last_successful_sync_at`, `requires_reconnect`).

**Reuse of existing pattern**: The FE-B7 batch added the QuickBooks sync row concept (visible in the batch tracker). `CalendarSyncStatusRow` mirrors the same three-state dot+label+subtitle layout without importing QuickBooks-specific types.

---

## A — Component Implementation Plan

### A.1 New Shared Components (`packages/ui/src/`)

#### A.1.1 `IntegrationConflictResolver`

**File**: `packages/ui/src/integration-conflict-resolver/IntegrationConflictResolver.tsx`

**Purpose**: The canonical bilateral integration conflict resolver UI. Established here with `integration="calendar"`; extended by FE-B9 with `integration="quickbooks"`. Houses layout branching, action buttons, staleness dialog composition, and voice readback slot. Composes `<DiffView variant="calendar-event">` and `<DeletionConflictView>`.

**Pattern references**: mvp-arch.md §16.10 (bilateral integration conflict resolution pattern); spec Decision 4 (side-by-side diff); spec Decision 7 (deletion conflict distinct treatment); spec Decision 6 (bottom action bar)

**Downstream consumers**: FE-B8 (calendar), FE-B9 (quickbooks)

**Props interface**: See Section F.

**Sub-components co-located in same directory**:
- `packages/ui/src/integration-conflict-resolver/DeletionConflictView.tsx` — renders verb-button layout for deletion-type conflicts
- `packages/ui/src/integration-conflict-resolver/ExpiryCountdownBadge.tsx` — renders amber/red expiry countdown
- `packages/ui/src/integration-conflict-resolver/ConflictTypeLabel.tsx` — renders `Modified ↔ Modified` / `Deleted ↔ Modified` / `Modified ↔ Deleted` pill
- `packages/ui/src/integration-conflict-resolver/index.ts` — barrel export

**Export from**: `packages/ui/src/index.ts` — FE-B8 adds the FE-B8 section

#### A.1.2 `CalendarSyncStatusRow` (mobile)

**File**: `packages/ui/src/calendar-sync-status/CalendarSyncStatusRow.tsx`

**Purpose**: Mobile Owner tab status row for calendar sync health. Three-state: healthy (green), pending conflicts (amber), error (red). Deep-links to web resolution surface. Mirrors FE-B7's QuickBooks sync row pattern.

**Pattern reference**: mvp-arch.md §16.9 (mobile owner status row + deep-link); spec Decision 10

**Downstream consumers**: `apps/mobile/features/owner-tab/` (this batch); FE-B9 does not extend this component

**Export from**: `packages/ui/src/index.ts`

### A.2 New Web Feature Components (`apps/web/src/features/calendar-conflict/`)

All surface-scoped components live in this feature folder.

| File | Purpose |
|:---|:---|
| `components/CalendarConnectionStatusCard.tsx` | Connected/syncing/error/disconnected status with reconnect button; consumes `GET /api/v1/integrations/calendar/status` |
| `components/CalendarConflictQueue.tsx` | Paginated conflict list table with urgency sort; SSE-driven live updates; anchor target for `#conflicts` |
| `components/CalendarConflictRow.tsx` | Single table row: event title, conflict type pill, Pilot change summary, calendar change summary, job link, `<ExpiryCountdownBadge>`, Resolve button |
| `components/CalendarConflictDetail.tsx` | Page-level shell for the detail view: breadcrumb, back nav, composes `<IntegrationConflictResolver>` |
| `components/CalendarSyncActivityLog.tsx` | Collapsible last-10 sync events; renders when no pending conflicts (spec Decision 12 empty state) |
| `components/CalendarAutoExpirySettings.tsx` | Two integer inputs for auto_expire_days + pre_warning_days with "Use system default" and "Disable" toggles; composes `<SettingControl>` pattern (FE-B11 provides — use MSW stub here) |
| `components/CalendarEmptyState.tsx` | Empty state when no pending conflicts: "No sync conflicts. Last successful sync: X min ago." + expandable activity log |
| `hooks/useCalendarConflicts.ts` | TanStack Query list hook; `GET /api/v1/integrations/calendar/conflicts`; cursor-paginated |
| `hooks/useCalendarConflictDetail.ts` | TanStack Query detail hook; `GET /api/v1/integrations/calendar/conflicts/{id}` |
| `hooks/useResolveCalendarConflict.ts` | Mutation hook; composes `useStalenessRetry` for the 409 staleness path |
| `hooks/useCalendarConflictSse.ts` | Composes `useSseChannel`; invalidates conflict list on SSE events |
| `hooks/useCalendarStatus.ts` | TanStack Query status hook; `GET /api/v1/integrations/calendar/status` |
| `mocks/calendarConflictFixtures.ts` | Typed fixture data for unit tests and MSW handlers |

**Page route components** (live in App Router tree, not feature folder):

| File | Route |
|:---|:---|
| `apps/web/src/app/(authed)/settings/integrations/calendar/page.tsx` | `/settings/integrations/calendar` |
| `apps/web/src/app/(authed)/settings/integrations/calendar/conflicts/[id]/page.tsx` | `/settings/integrations/calendar/conflicts/[id]` |

### A.3 New Mobile Feature Components

**Scope**: Notification badge + status row only per spec Decision 10. No resolution surface on mobile.

| File | Purpose |
|:---|:---|
| `apps/mobile/features/owner-tab/hooks/useCalendarStatus.ts` | TanStack Query: `GET /api/v1/integrations/calendar/status`; 60s staleTime; feeds `<CalendarSyncStatusRow>` |
| `apps/mobile/features/owner-tab/components/CalendarSyncStatusSection.tsx` | Wires `useCalendarStatus` to `<CalendarSyncStatusRow>`; placed below QB sync row on Owner tab |

The Owner tab route (`apps/mobile/app/(tabs)/owner.tsx`) gets `<CalendarSyncStatusSection>` added below the existing QuickBooks sync row.

### A.4 New Routes

| Route | File | Auth | Role Gate | Notes |
|:---|:---|:---:|:---|:---|
| `/settings/integrations/calendar` | `apps/web/src/app/(authed)/settings/integrations/calendar/page.tsx` | Required | `integrations.manage` (owner/accountant) via `<RoleGate>` + `useRequiresPermission` | Conflict queue section anchored at `#conflicts`; `?scroll=conflicts` query param scrolls on mount |
| `/settings/integrations/calendar/conflicts/[id]` | `apps/web/src/app/(authed)/settings/integrations/calendar/conflicts/[id]/page.tsx` | Required | Same; redirects to 404 if user lacks `integrations.manage` | Modal-feeling but URL-routed; bookmarkable |

---

## B — Execution Order

| Step | Item | Rationale |
|:---:|:---|:---|
| 1 | **`<IntegrationConflictResolver>` + `<DeletionConflictView>` + `<ExpiryCountdownBadge>` + `<ConflictTypeLabel>` in `packages/ui/`** | Shared component must exist before all consumers. FE-B9 inherits this locked interface. Build + fully test before any surface work. |
| 2 | **MSW handlers for all three calendar endpoints + SSE stream** | Enables all subsequent surface work to run without a live BE-B6 backend. MSW is the development contract. |
| 3 | **`CalendarConnectionStatusCard` + `useCalendarStatus` hook** | Connection status renders above the conflict queue; must render in all states (connected / error / disconnected) before building the queue that sits below it. |
| 4 | **`CalendarConflictQueue` + `useCalendarConflicts` + `useCalendarConflictSse`** | Owner's primary entry point. List + SSE wiring before detail. `staleness` wiring not needed here — the queue is read-only. |
| 5 | **`CalendarConflictDetail` + `useCalendarConflictDetail` + `useResolveCalendarConflict` (with `useStalenessRetry`)** | Detail view composes the resolver. `useStalenessRetry` must be wired on the resolve mutation so the `StalenessDialog` appears on 409. |
| 6 | **Settings page route + `CalendarSyncActivityLog` + `CalendarEmptyState` + `CalendarAutoExpirySettings`** | Page shell wires everything together. Activity log and empty state are secondary concerns after the primary conflict flow works. |
| 7 | **Mobile `CalendarSyncStatusRow` + `useCalendarStatus` (mobile) + Owner tab integration** | Mobile is notification + status row only. Built last because it has no web dependency; it's independently verifiable. |

**Rationale summary**: Shared component first (Rule 1); queue before detail (user must navigate the list to reach detail); staleness wiring before voice (voice confirmation depends on a working resolve mutation); mobile after web (spec Decision 10 explicitly scopes mobile to notification + status only).

---

## C — API Contracts

### C.1 `GET /api/v1/integrations/calendar/conflicts`

**TanStack Query key**: `['calendar-conflicts', { status, cursor, limit }]`  
**Cache**: 30s staleTime; refetchOnWindowFocus  
**Hook**: `useCalendarConflicts(params)`

**Request** (query params):
```typescript
interface CalendarConflictsParams {
  status?: 'pending' | 'resolved' | 'all';  // default: 'pending'
  cursor?: string;                            // opaque base64 cursor
  limit?: number;                             // 1–100, default 20
}
```

**Response** (typed from `ConflictListResponse`):
```typescript
interface CalendarConflictsResponse {
  conflicts: CalendarConflictQueueItem[];
  next_cursor: string | null;
  total_pending: number;
}
```

**Cache invalidation**: On SSE `conflict_detected` / `conflict_resolved`; on successful `POST …/resolve`.

---

### C.2 `GET /api/v1/integrations/calendar/conflicts/{id}`

**TanStack Query key**: `['calendar-conflict', id]`  
**Cache**: 0s staleTime (always fresh for a decision surface); refetchOnWindowFocus  
**Hook**: `useCalendarConflictDetail(id: string)`

**Response** (typed from `ConflictDetailResponse`):
```typescript
interface CalendarConflictDetail {
  id: string;                                    // UUID
  conflict_type: 'modified_modified' | 'deleted_modified' | 'modified_deleted';
  job_id: string;
  job_title: string | null;
  scheduled_start_at: string | null;             // ISO datetime
  urgency_score: number | null;
  pilot_modified_by_user_id: string | null;
  pilot_modified_by_name: string | null;
  pilot_modified_at: string;                     // ISO datetime
  external_modified_at: string;                  // ISO datetime
  resolution: string | null;
  resolved_by_user_id: string | null;
  resolved_at: string | null;
  auto_resolved_stale: boolean;
  pilot_snapshot: Record<string, unknown> | null;
  external_snapshot: Record<string, unknown> | null;
  base_snapshot: Record<string, unknown> | null;
  field_diffs: CalendarFieldDiff[];
  detected_at: string;                           // ISO datetime
}

interface CalendarFieldDiff {
  field_name: string;
  pilot_value: unknown;
  external_value: unknown;
  base_value: unknown;
  pilot_change: 'unchanged' | 'modified' | 'added' | 'removed';
  external_change: 'unchanged' | 'modified' | 'added' | 'removed';
}
```

**Cache invalidation**: On SSE `conflict_resolved`; on successful `POST …/resolve` (invalidate + remove).

---

### C.3 `POST /api/v1/integrations/calendar/conflicts/{id}/resolve`

**TanStack Query key**: Mutation; on success invalidates `['calendar-conflicts']` + `['calendar-conflict', id]` + `['calendar-status']`  
**Hook**: `useResolveCalendarConflict(id: string)` — wraps `useStalenessRetry`

**Request body**:
```typescript
interface ConflictResolveRequest {
  resolution: CalendarResolution;
  expected_pilot_modified_at: string;      // ISO datetime echoed from detail response
  expected_external_modified_at: string;   // ISO datetime echoed from detail response
}

type CalendarResolution =
  | 'accept_local'                  // modified_modified: keep Pilot
  | 'accept_remote'                 // modified_modified: apply calendar version
  | 'restore_from_calendar'         // deleted_modified: recreate Pilot job from calendar
  | 'delete_calendar_too'           // deleted_modified: push deletion to calendar
  | 'recreate_calendar_event'       // modified_deleted: push Pilot job back to calendar
  | 'delete_pilot_job';             // modified_deleted: accept calendar's deletion
```

**Response** (success 200):
```typescript
interface ConflictResolveResponse {
  id: string;           // UUID
  resolution: CalendarResolution;
  resolved_at: string;  // ISO datetime
  resolved_by_user_id: string;
}
```

**409 Conflict** (staleness): Backend returns RFC 7807 body with `refreshed_conflict: CalendarConflictDetail`. The `useStalenessRetry` hook parses this from `error.response.data.detail.refreshed_conflict`, opens `StalenessDialog`, and re-renders the resolver with the refreshed diff.

The `onConflict` callback returns `null` (forces dialog open, no auto-retry) because the owner must review the updated diff before re-submitting.

---

### C.4 `GET /api/v1/integrations/calendar/status`

**TanStack Query key**: `['calendar-status']`  
**Cache**: 60s staleTime on web; 60s on mobile  
**Hook**: `useCalendarStatus()` (web) / `useCalendarStatus()` (mobile — identical signature, different location)

**Response** (typed from `CalendarConnectionStatus`):
```typescript
interface CalendarConnectionStatus {
  is_connected: boolean;
  provider_code: string | null;                   // 'google_calendar' | 'outlook' | null
  sync_status: string | null;
  connection_status: 'connected' | 'syncing' | 'error' | 'disconnected' | null;
  connected_at: string | null;
  token_expires_at: string | null;
  last_sync_at: string | null;
  last_successful_sync_at: string | null;
  pending_conflicts_count: number;
  requires_reconnect: boolean;
}
```

**Cache invalidation**: On SSE `calendar_sync_status`.

---

### C.5 SSE Channel — `GET /api/v1/integrations/calendar/conflicts/stream`

**Hook**: `useCalendarConflictSse()` — composes `useSseChannel` from `@pilot/ui`

**Configuration**:
```typescript
useSseChannel({
  path: '/api/v1/integrations/calendar/conflicts/stream',
  onMessage: (msg: SseMessage) => {
    const event = JSON.parse(msg.data) as CalendarSseEvent;
    if (event.type === 'conflict_detected' || event.type === 'conflict_resolved') {
      queryClient.invalidateQueries({ queryKey: ['calendar-conflicts'] });
      if (event.conflict_id) {
        queryClient.invalidateQueries({ queryKey: ['calendar-conflict', event.conflict_id] });
      }
    }
    if (event.type === 'calendar_sync_status') {
      queryClient.invalidateQueries({ queryKey: ['calendar-status'] });
    }
  },
  fallbackToPollingMs: 60_000,
  pollFn: () => {
    queryClient.invalidateQueries({ queryKey: ['calendar-conflicts'] });
    queryClient.invalidateQueries({ queryKey: ['calendar-status'] });
  },
  enabled: true,
});
```

**MSW SSE handler** (for development): `apps/web/src/mocks/handlers/calendarConflicts.ts` registers a mock SSE endpoint using the existing MSW EventSource pattern established in FE-B4.

---

## D — State Management

### D.1 `CalendarIntegrationSettingsPage`

| State | Location | Notes |
|:---|:---|:---|
| Conflicts list | TanStack Query `['calendar-conflicts']` | Paginated; cursor managed in local state |
| Calendar status | TanStack Query `['calendar-status']` | 60s staletime |
| SSE connection | `useCalendarConflictSse` internal | Connected/polling determined by hook return |
| Scroll-to-conflicts flag | `useSearchParams()` + `useEffect` | `?scroll=conflicts` → `document.getElementById('conflicts')?.scrollIntoView()` on mount |
| Cursor (pagination) | `useState<string | null>(null)` | Local; reset to null when status filter changes |
| Status filter | `useState<'pending' | 'resolved' | 'all'>('pending')` | Local; drives query param |

### D.2 `CalendarConflictDetailPage`

| State | Location | Notes |
|:---|:---|:---|
| Conflict detail | TanStack Query `['calendar-conflict', id]` | 0s staleTime; always refetched on focus |
| Staleness dialog open | `useStalenessRetry` internal (`isStalenessDialogOpen`) | Owned by hook; not in local state |
| Staleness refresh payload | `useStalenessRetry` internal (`conflictPayloadRef`) | Ref-based; not React state |
| Resolve mutation status | `useStalenessRetry.mutation.status` | `'idle' | 'pending' | 'success' | 'error'` |
| Success redirect | `useRouter().push('/settings/integrations/calendar')` | Triggered in `onSuccess` of resolve mutation |

### D.3 Voice Confirm-as-Turn State Machine

This state machine applies when the owner initiates a voice resolution via `resolve_calendar_conflict` intent. The web surface renders a `<VoiceConfirmTurn>` component when a pending confirmation is active.

```typescript
type VoiceConflictResolutionState =
  | { phase: 'idle' }
  | { phase: 'identifying'; conflictIdentifier: string }
  | { phase: 'confirming'; conflictId: string; chosenResolution: CalendarResolution; readbackText: string }
  | { phase: 'committed'; conflictId: string; resolution: CalendarResolution }
  | { phase: 'cancelled'; reason: 'user_cancelled' | 'staleness_detected' | 'deletion_conflict_redirect' };
```

State is derived from the backend's `context_window_json.pending_confirmation` in the voice session. The FE-B8 voice path:
1. Voice intent arrives → `identifying` phase (AI disambiguates if multiple matches)
2. AI reads diff back → `confirming` phase; web renders `<VoiceConfirmTurn prompt={readbackText}`
3. Owner says "confirm" → `mutate` called → `committed` phase
4. 409 staleness during confirmation → `cancelled` with `staleness_detected`; push notification deep-link to detail page

**Local voice state**: `useState<VoiceConflictResolutionState>({ phase: 'idle' })` in `CalendarConflictDetail`. Not in global store — scoped to the detail page lifecycle.

### D.4 SSE → Cache-Invalidation Flow

```
BE-B6 Celery detects new conflict
  → emits SSE event to /api/v1/integrations/calendar/conflicts/stream
  → useSseChannel onMessage fires
  → queryClient.invalidateQueries(['calendar-conflicts'])
  → useCalendarConflicts refetch triggered (React Query automatic)
  → CalendarConflictQueue re-renders with new row
  → badge count updates on dispatch board indicator (via calendar-status invalidation)
```

---

## E — Error States

### E.1 409 Staleness During Web Resolution

**Trigger**: Owner clicks "Use Pilot version" / "Use Calendar version" after someone else (or the auto-expiry task) has changed the conflict.

**User sees**: `StalenessRefreshDialog` opens (from `useStalenessRetry`). Title: `"This conflict has been updated."` Body renders the refreshed `<DiffView variant="calendar-event">` via `renderConflictContent`. Action: "Retry with updated data" re-submits; "Cancel" closes dialog.

**Component**: `StalenessRefreshDialog` from `packages/ui/src/staleness-refresh-dialog/`  
**Token class**: `text-alert-600` warning icon in dialog header  
**Banner**: An additional `NotificationBanner` with severity `warning` fires: `"This conflict has been updated — review and pick again."`

### E.2 409 Staleness During Voice Resolution

**Trigger**: Voice intent committed between identification and confirmation turns.

**Backend behavior**: Returns 409 to the voice handler (A36 scope).

**User sees**: AI announces `"The conflict has changed since you last looked at it — opening the diff view on web."` A push notification with deep-link to the conflict detail page fires via `notification_outbox`.

**FE-B8 scope**: Web detail page must handle the deep-link arrival and show a `NotificationBanner` with severity `warning` when `?reason=voice_staleness` is present in the URL. Banner: `"Your voice resolution was cancelled — the conflict changed. Review the updated diff below."`

### E.3 Connection Error / Expired Token

**Trigger**: `calendar_status.requires_reconnect === true` or `connection_status === 'error'`.

**User sees**: `CalendarConnectionStatusCard` shows red dot + `"Calendar sync · reconnect needed"` + `<button>Reconnect</button>`. A `NotificationBanner` with severity `warning` renders at the top of the calendar settings page: `"Sync error blocking automatic conflict push — reconnect to resume."` Spec Decision 14.

**Conflicts remain visible and resolvable** while disconnected. The banner is informational; it does not disable the conflict queue.

**Component**: `NotificationBanner` from `packages/ui/src/notification-banner/`  
**Token class**: `bg-fault-50` border `border-fault-200`

### E.4 Auto-Expiry Pre-Warning Banner

**Trigger**: `days_until_expiry <= 7` for any pending conflict. Computed from `detected_at + effective_auto_expire_days`.

**In queue row**: `<ExpiryCountdownBadge>` renders inside the row. Text: `"Auto-resolves in N days"`. Color switches from amber to red at `<= 3 days`.

**In detail header**: `<NotificationBanner severity="warning">` with text: `"This conflict will auto-resolve to Pilot's version in N days if not resolved."` Token class: `bg-alert-50 border-alert-200 text-alert-600`. Switches to `bg-fault-50 border-fault-200 text-fault-600` at `<= 3 days`.

### E.5 Deletion Conflict — Voice Refusal Redirect

**Trigger**: Voice attempts `resolve_calendar_conflict` for a `deleted_modified` or `modified_deleted` conflict.

**User sees**: AI says `"That's a deletion conflict — it needs the diff view to be safe. I'll open it on web."` A push notification fires with deep-link. The web detail page renders `<DeletionConflictView>` (verb buttons, no DiffView).

**Banner on deep-link arrival**: `NotificationBanner severity="info"`: `"Your voice session routed here — please choose how to handle this deletion."` Present when `?reason=voice_deletion_redirect` in URL.

### E.6 Empty State (No Conflicts, Sync Healthy)

**Trigger**: `conflicts.length === 0` and `connection_status === 'connected'`.

**User sees**: `<CalendarEmptyState>` renders: `"No sync conflicts."` + `"Last successful sync: 2 minutes ago."` + collapsed `<CalendarSyncActivityLog>` (last 10 sync events).

**Token class**: `text-margin-600` for the "No sync conflicts" line (green = healthy). `text-neutral-600` for the timestamp.

### E.7 Network / Server Error Loading Conflict List

**Trigger**: `useCalendarConflicts` query returns error state.

**User sees**: `<ErrorState type="network">` from `packages/ui/src/states/` with retry CTA.

### E.8 Conflict Not Found (Deep-Link to Resolved Conflict)

**Trigger**: Owner navigates to `/settings/integrations/calendar/conflicts/{id}` for an already-resolved conflict.

**User sees**: Resolved conflict detail renders with a `NotificationBanner severity="info"`: `"This conflict was resolved on [date] by [name]. Viewing the final state."` Resolution action buttons are hidden. The diff is read-only.

---

## F — TypeScript Interfaces

### F.1 `IntegrationConflictResolverProps` (LOCKED for FE-B9)

```typescript
/**
 * <IntegrationConflictResolver> — Locked public API
 *
 * Location: packages/ui/src/integration-conflict-resolver/IntegrationConflictResolver.tsx
 *
 * ⚠️ INTERFACE LOCKED after FE-B8 ships.
 * FE-B9 may add OPTIONAL props via backward-compatible extension only.
 * Renaming or removing existing props requires multi-batch impact review.
 *
 * FE-B9 extension points:
 *   - renderDomainSpecificFields: inject QB-specific financial_delta_cents / tax_period_warning
 *   - provider_display_name: "QuickBooks" instead of "Google Calendar"
 *   - Any new props MUST be optional with sensible defaults
 */
export interface IntegrationConflictResolverProps<
  T extends CalendarConflictDetail | QbConflictDetail = CalendarConflictDetail,
> {
  /**
   * The integration type. Drives default labels, verb buttons for deletion
   * conflicts, and voice route-to-web messaging.
   * FE-B9 extends with 'quickbooks'.
   */
  integration: 'calendar' | 'quickbooks';

  /**
   * The fully-resolved conflict detail (includes field_diffs).
   * The parent page fetches this via its own hook.
   * The resolver is purely presentational — no internal fetching.
   */
  conflict: T;

  /**
   * Called when the owner selects a resolution.
   * The parent page's useResolveCalendarConflict hook handles the actual mutation.
   * The resolver communicates the choice upward via this callback.
   */
  onResolve: (resolution: CalendarResolution) => void;

  /**
   * True when the resolve mutation is in-flight.
   * Disables action buttons and shows spinner.
   */
  isResolving: boolean;

  /**
   * Called when the owner clicks "Resolve later" escape hatch.
   */
  onResolveLater: () => void;

  /**
   * The provider display name for the right-column header.
   * Defaults: calendar → from conflict.provider_display_name or 'Google Calendar';
   *            quickbooks → 'QuickBooks'
   * Must be read from the integration record, never hardcoded.
   */
  providerDisplayName?: string;

  /**
   * FE-B9 extension slot: render QB-specific fields (financial_delta_cents,
   * tax_period_warning) below the standard DiffView.
   * Calendar integration passes undefined.
   */
  renderDomainSpecificFields?: (conflict: T) => React.ReactNode;

  /**
   * Days until auto-expiry. Drives ExpiryCountdownBadge in the detail header.
   * null when auto-expiry is disabled for this tenant.
   */
  daysUntilExpiry?: number | null;

  /** Test ID for e2e and unit tests */
  testID?: string;
}
```

### F.2 `CalendarConflictQueueItem`

```typescript
/**
 * Typed from ConflictListItem in backend/api/routes/calendar_conflicts.py
 * Maps 1:1 with the API response — camelCase conversion happens in normalizeConflictListItem()
 */
export interface CalendarConflictQueueItem {
  id: string;                                   // UUID
  conflictType: 'modified_modified' | 'deleted_modified' | 'modified_deleted';
  jobId: string;
  jobTitle: string | null;
  scheduledStartAt: string | null;              // ISO datetime
  urgencyScore: number | null;
  pilotModifiedAt: string;                      // ISO datetime
  externalModifiedAt: string;                   // ISO datetime
  resolution: string | null;
  detectedAt: string;                           // ISO datetime
}

export interface CalendarConflictsResponse {
  conflicts: CalendarConflictQueueItem[];
  nextCursor: string | null;
  totalPending: number;
}
```

### F.3 `CalendarConflictDetail`

```typescript
/**
 * Typed from ConflictDetailResponse in backend/api/routes/calendar_conflicts.py
 */
export interface CalendarConflictDetail {
  id: string;
  conflictType: 'modified_modified' | 'deleted_modified' | 'modified_deleted';
  jobId: string;
  jobTitle: string | null;
  scheduledStartAt: string | null;
  urgencyScore: number | null;
  pilotModifiedByUserId: string | null;
  pilotModifiedByName: string | null;
  pilotModifiedAt: string;
  externalModifiedAt: string;
  resolution: CalendarResolution | null;
  resolvedByUserId: string | null;
  resolvedAt: string | null;
  autoResolvedStale: boolean;
  pilotSnapshot: Record<string, unknown> | null;
  externalSnapshot: Record<string, unknown> | null;
  baseSnapshot: Record<string, unknown> | null;
  fieldDiffs: CalendarApiFieldDiff[];
  detectedAt: string;
}

export interface CalendarApiFieldDiff {
  fieldName: string;
  pilotValue: unknown;
  externalValue: unknown;
  baseValue: unknown;
  pilotChange: 'unchanged' | 'modified' | 'added' | 'removed';
  externalChange: 'unchanged' | 'modified' | 'added' | 'removed';
}

export type CalendarResolution =
  | 'accept_local'
  | 'accept_remote'
  | 'restore_from_calendar'
  | 'delete_calendar_too'
  | 'recreate_calendar_event'
  | 'delete_pilot_job';
```

### F.4 `FieldDiff` (existing, confirmed from `diff-view/types.ts`)

```typescript
/**
 * Existing locked type from packages/ui/src/diff-view/types.ts
 * Used as the target type when normalizing CalendarApiFieldDiff[].
 * No changes needed — IntegrationDiffViewProps already accepts DiffField[].
 */
export interface DiffField {
  fieldName: string;
  label?: string;
  baseValue: string | number | boolean | null;
  modifiedValue: string | number | boolean | null;
  changeType?: 'unchanged' | 'modified' | 'added' | 'removed';
  annotation?: string;
  pendingEditId?: string;
}
```

**Normalization function** (new, co-located in `calendar-conflict/` feature folder):

```typescript
/**
 * normalizeCalendarFieldDiffs()
 *
 * Converts CalendarApiFieldDiff[] (snake_case from API) to DiffField[]
 * (camelCase for <DiffView variant="calendar-event">).
 *
 * The "base" side maps to DiffField.baseValue (Pilot version).
 * The "modified" side maps to DiffField.modifiedValue (external calendar version).
 * changeType is derived from external_change (what the calendar did).
 */
export function normalizeCalendarFieldDiffs(
  apiDiffs: CalendarApiFieldDiff[],
  providerDisplayName: string,
): DiffField[] {
  return apiDiffs.map((d) => ({
    fieldName: d.fieldName,
    baseValue: d.pilotValue !== undefined ? String(d.pilotValue ?? '') : null,
    modifiedValue: d.externalValue !== undefined ? String(d.externalValue ?? '') : null,
    changeType: d.externalChange === 'unchanged' ? 'unchanged'
      : d.externalChange === 'added' ? 'added'
      : d.externalChange === 'removed' ? 'removed'
      : 'modified',
  }));
}
```

### F.5 `CalendarConnectionStatus` (web + mobile)

```typescript
/**
 * Typed from CalendarConnectionStatus in backend/api/routes/calendar_integration.py
 */
export interface CalendarConnectionStatus {
  isConnected: boolean;
  providerCode: string | null;
  syncStatus: string | null;
  connectionStatus: 'connected' | 'syncing' | 'error' | 'disconnected' | null;
  connectedAt: string | null;
  tokenExpiresAt: string | null;
  lastSyncAt: string | null;
  lastSuccessfulSyncAt: string | null;
  pendingConflictsCount: number;
  requiresReconnect: boolean;
}
```

### F.6 `CalendarSyncStatusRowProps` (mobile)

```typescript
/**
 * Props for <CalendarSyncStatusRow> in packages/ui/src/calendar-sync-status/
 */
export interface CalendarSyncStatusRowProps {
  /** The resolved CalendarConnectionStatus data (caller fetches, passes down) */
  status: CalendarConnectionStatus | undefined;

  /** True while useCalendarStatus is loading */
  isLoading: boolean;

  /** Deep-link URL to open on web when owner taps the row */
  resolveWebUrl: string;

  /** Test ID for e2e and unit tests */
  testID?: string;
}
```

### F.7 `VoiceConflictResolutionState`

```typescript
/**
 * State machine type for the voice conflict resolution confirm-as-turn flow.
 * Managed in local useState() on CalendarConflictDetailPage.
 */
export type VoiceConflictResolutionState =
  | { phase: 'idle' }
  | {
      phase: 'identifying';
      conflictIdentifier: string;
    }
  | {
      phase: 'confirming';
      conflictId: string;
      chosenResolution: CalendarResolution;
      /** AI-rendered readback text from server-side diff payload */
      readbackText: string;
    }
  | {
      phase: 'committed';
      conflictId: string;
      resolution: CalendarResolution;
    }
  | {
      phase: 'cancelled';
      reason: 'user_cancelled' | 'staleness_detected' | 'deletion_conflict_redirect';
    };
```

---

## G — Test Plan

### G.1 Unit Tests (target: 40+)

**`packages/ui/src/integration-conflict-resolver/`**

| Test | File |
|:---|:---|
| Renders field-level diff layout for `modified_modified` conflict type | `IntegrationConflictResolver.test.tsx` |
| Renders deletion layout (`<DeletionConflictView>`) for `deleted_modified` | `IntegrationConflictResolver.test.tsx` |
| Renders deletion layout (`<DeletionConflictView>`) for `modified_deleted` | `IntegrationConflictResolver.test.tsx` |
| Deletion layout shows correct verb pair for `deleted_modified`: "Restore / Delete from Calendar" | `DeletionConflictView.test.tsx` |
| Deletion layout shows correct verb pair for `modified_deleted`: "Recreate / Delete Pilot Job" | `DeletionConflictView.test.tsx` |
| Calls `onResolve('accept_local')` when "Use Pilot version" clicked | `IntegrationConflictResolver.test.tsx` |
| Calls `onResolve('accept_remote')` when "Use Calendar version" clicked | `IntegrationConflictResolver.test.tsx` |
| Disables action buttons when `isResolving=true` | `IntegrationConflictResolver.test.tsx` |
| Shows spinner when `isResolving=true` | `IntegrationConflictResolver.test.tsx` |
| Calls `onResolveLater` when "Resolve later" clicked | `IntegrationConflictResolver.test.tsx` |
| `providerDisplayName` appears in right-column header and button label | `IntegrationConflictResolver.test.tsx` |
| `renderDomainSpecificFields` slot renders its content | `IntegrationConflictResolver.test.tsx` |
| `renderDomainSpecificFields` undefined → renders nothing in slot area | `IntegrationConflictResolver.test.tsx` |
| `ExpiryCountdownBadge` renders amber token class when `daysUntilExpiry > 3` | `ExpiryCountdownBadge.test.tsx` |
| `ExpiryCountdownBadge` renders red token class when `daysUntilExpiry <= 3` | `ExpiryCountdownBadge.test.tsx` |
| `ExpiryCountdownBadge` hidden when `daysUntilExpiry === null` | `ExpiryCountdownBadge.test.tsx` |
| `ConflictTypeLabel` renders correct text for all three conflict types | `ConflictTypeLabel.test.tsx` |

**`apps/web/src/features/calendar-conflict/`**

| Test | File |
|:---|:---|
| `normalizeCalendarFieldDiffs` maps `pilot_value` → `baseValue`, `external_value` → `modifiedValue` | `hooks/normalizeCalendarFieldDiffs.test.ts` |
| `normalizeCalendarFieldDiffs` derives `changeType` from `external_change` | `hooks/normalizeCalendarFieldDiffs.test.ts` |
| `CalendarConflictRow` renders job title, conflict type pill, and Resolve button | `components/CalendarConflictRow.test.tsx` |
| `CalendarConflictRow` renders `ExpiryCountdownBadge` when `daysUntilExpiry <= 7` | `components/CalendarConflictRow.test.tsx` |
| `CalendarConnectionStatusCard` renders green dot for `connection_status=connected` | `components/CalendarConnectionStatusCard.test.tsx` |
| `CalendarConnectionStatusCard` renders red dot + Reconnect button for `requires_reconnect=true` | `components/CalendarConnectionStatusCard.test.tsx` |
| `CalendarConnectionStatusCard` renders amber dot for `pending_conflicts_count > 0` | `components/CalendarConnectionStatusCard.test.tsx` |
| `CalendarEmptyState` renders "No sync conflicts" message + last sync time | `components/CalendarEmptyState.test.tsx` |
| `CalendarConflictQueue` renders empty state when conflicts array is empty | `components/CalendarConflictQueue.test.tsx` |
| `CalendarConflictQueue` renders pagination controls when `next_cursor` present | `components/CalendarConflictQueue.test.tsx` |
| `useCalendarConflicts` constructs correct query key with status param | `hooks/useCalendarConflicts.test.ts` |
| `useResolveCalendarConflict` calls `useStalenessRetry.mutate` on resolve | `hooks/useResolveCalendarConflict.test.ts` |
| `useResolveCalendarConflict` onConflict returns `null` to force dialog open | `hooks/useResolveCalendarConflict.test.ts` |

**`packages/ui/src/calendar-sync-status/`** (mobile)

| Test | File |
|:---|:---|
| `CalendarSyncStatusRow` renders green dot for `connection_status=connected` | `CalendarSyncStatusRow.test.tsx` |
| `CalendarSyncStatusRow` renders amber dot + conflict count for `pending_conflicts_count > 0` | `CalendarSyncStatusRow.test.tsx` |
| `CalendarSyncStatusRow` renders red dot + "reconnect needed" for `requires_reconnect=true` | `CalendarSyncStatusRow.test.tsx` |
| `CalendarSyncStatusRow` renders loading skeleton when `isLoading=true` | `CalendarSyncStatusRow.test.tsx` |

### G.2 Integration Tests (target: 10+)

**Location**: `apps/web/__tests__/batch_fe_b8/`

| Test | File |
|:---|:---|
| Full resolve flow: list → click Resolve → detail → select "Use Pilot" → success → navigate back | `calendar-conflict-resolve.integration.test.tsx` |
| Full resolve flow: deletion conflict → `<DeletionConflictView>` verbs visible, standard diff hidden | `calendar-conflict-deletion.integration.test.tsx` |
| 409 staleness during resolve: dialog opens, shows refreshed diff, retry with new timestamps | `calendar-conflict-staleness.integration.test.tsx` |
| SSE event arrives → conflict list auto-updates (new row appears) | `calendar-conflict-sse.integration.test.tsx` |
| Empty state: no conflicts → "No sync conflicts" + last sync time renders | `calendar-conflict-empty.integration.test.tsx` |
| Connection error: `requires_reconnect=true` → reconnect banner + amber status card | `calendar-connection-error.integration.test.tsx` |
| Voice confirm-as-turn: `confirming` phase renders `<VoiceConfirmTurn>` with `readbackText`; Confirm triggers mutate | `calendar-conflict-voice.integration.test.tsx` |
| Auto-expiry warning banner renders on detail page when `daysUntilExpiry <= 7` | `calendar-conflict-expiry.integration.test.tsx` |
| RBAC: user without `integrations.manage` sees `<EmptyState type="permission-denied">` | `calendar-conflict-rbac.integration.test.tsx` |
| Resolved conflict deep-link: shows read-only diff + "Already resolved" banner | `calendar-conflict-resolved.integration.test.tsx` |

**MSW handlers required** (new file `apps/web/src/mocks/handlers/calendarConflicts.ts`):
- `GET /api/v1/integrations/calendar/conflicts` → `ConflictListResponse` with fixtures
- `GET /api/v1/integrations/calendar/conflicts/:id` → `ConflictDetailResponse` with `modified_modified` fixture
- `GET /api/v1/integrations/calendar/conflicts/:id` (deletion fixture variant) → `deleted_modified`
- `POST /api/v1/integrations/calendar/conflicts/:id/resolve` → success 200
- `POST /api/v1/integrations/calendar/conflicts/:id/resolve` (409 variant) → staleness payload
- `GET /api/v1/integrations/calendar/status` → `CalendarConnectionStatus`
- `GET /api/v1/integrations/calendar/conflicts/stream` → mock SSE endpoint

### G.3 E2E Tests (target: 2+)

**Location**: `e2e/web/batch_fe_b8/`

| Test | File |
|:---|:---|
| Web full conflict resolve cycle: load queue → navigate to detail → pick resolution → success redirect → conflict removed from queue | `calendar-conflict-resolve.e2e.spec.ts` |
| Staleness scenario: two-tab staleness race — tab A opens detail, tab B resolves, tab A attempts resolution → 409 → dialog opens → retry succeeds | `calendar-conflict-staleness-race.e2e.spec.ts` |

---

## H — Token Audit

Every color, spacing, and typography value in the new components must trace to a token from `packages/ui/src/tokens.ts`. No hex values or pixel values in component code.

### H.1 Color Tokens

| Usage | Tailwind class (web) | Token | Hex value |
|:---|:---|:---|:---|
| Modified-field amber background | `bg-alert-50` | `colors.alert[50]` | `#FFF7EB` |
| Modified-field amber border | `border-alert-200` | `colors.alert[200]` | `#FDD997` |
| Modified-field amber text | `text-alert-600` | `colors.alert[600]` | `#B45309` |
| Added-field green background | `bg-margin-50` | `colors.margin[50]` | `#ECFDF5` |
| Added-field green text | `text-margin-600` | `colors.margin[600]` | `#059669` |
| Removed-field red background | `bg-fault-50` | `colors.fault[50]` | `#FEF2F2` |
| Removed-field red text | `text-fault-600` | `colors.fault[600]` | `#DC2626` |
| "Use Pilot version" primary button | `bg-brand-600` | `colors.brand[600]` | `#3B43D6` |
| "Use Pilot version" button hover | `bg-brand-800` | `colors.brand[800]` | `#232AA3` |
| "Use Calendar version" button border | `border-brand-600` | `colors.brand[600]` | `#3B43D6` |
| Expiry countdown amber (> 3 days) | `bg-alert-50 text-alert-600` | above | — |
| Expiry countdown red (<= 3 days) | `bg-fault-50 text-fault-600` | above | — |
| Status card connected dot | `bg-margin-400` | `colors.margin[400]` | `#34D399` |
| Status card conflicts dot | `bg-alert-400` | `colors.alert[400]` | `#F59E0B` |
| Status card error dot | `bg-fault-600` | `colors.fault[600]` | `#DC2626` |
| Page body text | `text-neutral-900` | `colors.neutral[900]` | `#1C1917` |
| Secondary text / captions | `text-neutral-600` | `colors.neutral[600]` | `#57534E` |
| Disabled / hint text | `text-neutral-400` | `colors.neutral[400]` | `#A8A29E` |
| Subtle border | `border-neutral-200` | `colors.neutral[200]` | `#E7E5E4` |
| Card background | `bg-white` | `lightTheme.background.secondary` | `#FFFFFF` |
| Page background | `bg-neutral-50` | `lightTheme.background.primary` | `#FAFAF9` |
| Table stripe | `bg-neutral-100` | `lightTheme.background.tertiary` | `#F5F5F4` |

### H.2 Spacing Tokens

All `padding`, `margin`, `gap` values use the Tailwind spacing scale from the pilot preset, which is derived from `tokens.ts` `spacing` object. Component code uses only Tailwind utility classes — no raw pixel values.

| Usage | Class | Token |
|:---|:---|:---|
| Card internal padding | `p-4` | `spacing[4]` = 16px |
| Section vertical rhythm | `space-y-6` | `spacing[6]` = 24px |
| Button padding | `px-4 py-2` | `spacing[4]` / `spacing[2]` |
| Row gap between columns | `gap-4` | `spacing[4]` = 16px |
| Badge padding | `px-2 py-0.5` | `spacing[2]` / `spacing[0.5]` |

### H.3 Typography Tokens

| Usage | Class | Token |
|:---|:---|:---|
| Page heading | `text-h2 font-medium` | `fontSizes.h2`, `fontWeights.medium` |
| Body copy | `text-body` | `fontSizes.body` |
| Caption / meta | `text-caption` | `fontSizes.caption` |
| Large body (column labels) | `text-body-lg` | `fontSizes.bodyLg` |

### H.4 Token Gaps Flagged

No token gaps identified. All design values used in this batch have corresponding tokens in `tokens.ts`. No hardcoding needed.

**One note**: The "Deletion conflict icon" (a trash can or warning SVG) uses `text-fault-600 currentColor` — the icon fills from the token via `currentColor` inheritance, never a hardcoded fill attribute. Same pattern as `StalenessRefreshDialog`'s warning icon.

---

## I — Downstream Contract Lock

### I.1 Interface Locked by FE-B8 (Consumed by FE-B9)

FE-B9 imports the following from this batch. These are **locked**. FE-B9 may only extend via backward-compatible optional props — never rename, never remove, never change existing prop semantics.

| Import | From | FE-B9 usage |
|:---|:---|:---|
| `IntegrationConflictResolver` | `packages/ui/src/integration-conflict-resolver/` | `<IntegrationConflictResolver integration="quickbooks" conflict={qbConflict} ...>` |
| `IntegrationConflictResolverProps` | same | FE-B9 instantiates with `QbConflictDetail` type parameter |
| `ExpiryCountdownBadge` | same | Reused in QB conflict queue rows |
| `ConflictTypeLabel` | same | Reused in QB conflict queue rows (QB conflict types differ but badge shape is the same) |
| `CalendarResolution` (type only) | `apps/web/src/features/calendar-conflict/` | FE-B9 defines its own `QbResolution` type; does not import `CalendarResolution` |

### I.2 Props That FE-B9 Will Extend

FE-B9 must extend `IntegrationConflictResolverProps` by providing:

```typescript
// FE-B9 extension (illustrative — these props must be OPTIONAL with defaults):
interface IntegrationConflictResolverProps<T> {
  // ... all existing FE-B8 locked props above ...

  // FE-B9 adds: (MUST be optional, MUST not break FE-B8 usage)
  integration: 'calendar' | 'quickbooks';  // no change — FE-B9 just uses 'quickbooks'
  renderDomainSpecificFields?: (conflict: T) => React.ReactNode;  // already in FE-B8 interface
}
```

No new required props may be added to `IntegrationConflictResolverProps` by FE-B9. If FE-B9 needs a required behavioral customization, it must be achieved via the `renderDomainSpecificFields` slot or a new optional prop with a default that preserves FE-B8 behavior.

### I.3 Migration Note for FE-B9

FE-B9 will use `<IntegrationConflictResolver>` with `integration="quickbooks"` and will pass a QB conflict detail object. The component's type parameter `T` (defaulting to `CalendarConflictDetail` in FE-B8) will be widened to `CalendarConflictDetail | QbConflictDetail`. This is a backward-compatible extension — no FE-B8 code changes required.

FE-B9 must map its `QbConflictDetail.field_diffs` through its own normalization function (parallel to FE-B8's `normalizeCalendarFieldDiffs`) that produces `DiffField[]` for `<DiffView variant="qb-entity">`.

### I.4 Notification That FE-B15 Consumes

The `<InFlightSyncIndicator surface="calendar">` instance added in this batch is the third consumer (after `dispatch` in FE-B4 and `mobile-sync` in FE-B7). FE-B15 will generalize all four indicator instances. FE-B8 must use the `surface="calendar"` prop value exactly — this is the string FE-B15 will query when it audits all four sync surfaces.

The calendar sync indicator in FE-B8 wires to `useCalendarStatus()` and passes:
```typescript
<InFlightSyncIndicator
  surface="calendar"
  state={mapConnectionStatusToSyncState(calendarStatus.connectionStatus)}
  pendingCount={calendarStatus.pendingConflictsCount}
  lastSyncedAt={calendarStatus.lastSuccessfulSyncAt ? new Date(calendarStatus.lastSuccessfulSyncAt) : undefined}
  onManualSync={handleManualSync}  // calls POST /api/v1/integrations/calendar/sync (if available)
  compact={false}
/>
```

FE-B15 will replace this inline usage with a `useInFlightSyncStatus('calendar')` hook — no interface changes required at the `<InFlightSyncIndicator>` component level.

---

## Appendix: MSW Handler Requirements

File: `apps/web/src/mocks/handlers/calendarConflicts.ts`

```typescript
// Required handlers (export as calendarConflictHandlers array):
// 1. GET /api/v1/integrations/calendar/conflicts
//    - Default: returns 3 modified_modified conflicts (urgency-sorted)
//    - Variant 'empty': returns { conflicts: [], next_cursor: null, total_pending: 0 }
//    - Variant 'deletion': returns 1 deleted_modified + 1 modified_deleted conflict
//
// 2. GET /api/v1/integrations/calendar/conflicts/:id
//    - Default: returns a modified_modified ConflictDetailResponse with 3 field_diffs
//    - Variant 'deletion': returns deleted_modified with no field_diffs
//    - Variant 'resolved': returns conflict with resolution='accept_local' + resolved_at
//
// 3. POST /api/v1/integrations/calendar/conflicts/:id/resolve
//    - Default (resolve succeeds): returns ConflictResolveResponse 200
//    - Variant '409': returns RFC 7807 409 with refreshed_conflict in detail
//
// 4. GET /api/v1/integrations/calendar/status
//    - Default: { is_connected: true, connection_status: 'connected', pending_conflicts_count: 3, ... }
//    - Variant 'error': { requires_reconnect: true, connection_status: 'error', ... }
//    - Variant 'disconnected': { is_connected: false, connection_status: 'disconnected', ... }
//
// 5. GET /api/v1/integrations/calendar/conflicts/stream (SSE)
//    - Use HttpResponse.text() with EventStream mimetype
//    - Emits conflict_detected event after 500ms delay in tests
```

---

*This document is the complete handoff artifact for the Pilot React Engineer. All 7 design decisions are resolved. All TypeScript interfaces are complete. All token references use exact token names from `tokens.ts`. The engineer can execute FE-B8 without returning for architectural decisions.*
