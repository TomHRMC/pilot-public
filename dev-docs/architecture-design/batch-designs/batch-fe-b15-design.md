# Batch FE-B15 Design — In-Flight Sync Indicator Refinement (Pass 4 Tier 4 #12)

**Batch**: FE-B15
**Design Date**: May 27, 2026
**Architect**: Pilot Architect mode
**Consumer**: Pilot React Engineer mode (Phase 2 implementation)
**Source Plan**: `dev-docs/analysis/pilot-app-mvp-frontend-impl-plan.md` §6 FE-B15
**Spec**: `frontend-pass-4-tier-4-flow-12-in-flight-sync-indicator-spec.md` v1.0
**Arch ref**: `mvp-arch.md §16.13`
**Prerequisite Batches**: FE-B4 ✅, FE-B7 ✅, FE-B8 ✅, FE-B9 ✅
**Backend Gate**: BE-B15 (sync_status.py — A79) ✅ confirmed present at `backend/api/routes/sync_status.py`
**Gates Downstream**: None (FE-B15 is the final batch touching `InFlightSyncIndicator` before MVP launch)
**Estimated Effort**: 4–6 days
**Test Subfolder**: `apps/{web,mobile}/__tests__/batch_fe_b15/`

---

## A — Audit Findings + Component Implementation Plan

### A.1 Audit Findings: Actual Prop Drift, Surface Usage, and Visual Drift

All four consuming batches and the FE-B1 skeleton were read before writing this section. Findings are empirical.

#### A.1.1 FE-B1 Skeleton State

**`packages/ui/src/sync-indicator/types.ts`** — the shared props interface.

The FE-B1 skeleton's `InFlightSyncIndicatorProps` is **almost complete** — the design anticipated most needs at skeleton time. The full interface as-built:

| Prop | Type | Present? | Notes |
|:---|:---|:---:|:---|
| `surface` | `SyncSurface` | ✅ | Union includes dispatch, mobile-sync, calendar, quickbooks |
| `pendingCount` | `number?` | ✅ | Defaults to `0` |
| `lastSyncedAt` | `Date \| null` | ✅ | Accepts `null` (mobile coerces null from no-session) |
| `state` | `SyncState?` | ✅ | Defaults to `"idle"` |
| `amberThreshold` | `number?` | ✅ | Defaults to `5`; mobile skeleton accepts but ignores it |
| `onManualSync` | `() => void` | ✅ | Optional; excluded for `mobile-sync` |
| `compact` | `boolean?` | ✅ | Defaults to `false` |
| `onResolve` | `() => void` | ✅ | In types; **NOT wired** in either platform skeleton |
| `testID` | `string?` | ✅ | Present |

**`SyncSurface` union is missing `"background-sync"`**. The FE-B9 completion record and spec both reference `surface="background-sync"` but `types.ts` only has `"dispatch" | "mobile-sync" | "calendar" | "quickbooks"`.

**`SyncState` union is complete**: `"idle" | "synced-pending" | "syncing" | "error" | "paused"` — all five compositional states present.

#### A.1.2 Web Skeleton — `packages/ui/src/sync-indicator/web/InFlightSyncIndicator.tsx`

**Gaps found:**

1. **`onResolve` not wired** — prop accepted in types but the web component never calls it. `MobileSyncStatusBar` (FE-B7) passes `onResolve={openDrawer}` which silently does nothing. The error-state "[Resolve]" CTA from the spec is not rendered.

2. **State label text does not match spec** — skeleton renders abbreviated labels (`"In sync"`, `"Pending sync"`, `"Syncing…"`) instead of the spec's context-rich labels (`"Synced · last 12s ago"`, `"Synced · 3 pending · syncing in 2m"`, `"Syncing 3 changes..."`). This is acceptable skeleton behavior; FE-B15 finalizes the labels.

3. **`lastSyncedAt` only shown in `idle` state** — the conditional `state === "idle"` hides the timestamp in `synced-pending` state, where it's also relevant per spec.

4. **Pending count badge uses `bg-neutral-200`** — spec (Section H) targets `alert-500` for the badge background. Token ramp has `alert-400` and `alert-600`; no `alert-500`. FE-B8 batch notes flagged this. The refined design resolves this with `alert-400`.

5. **Hover detail tooltip not implemented** — skeleton renders no `<details>` or popover. FE-B15 adds this.

#### A.1.3 Mobile Skeleton — `packages/ui/src/sync-indicator/mobile/InFlightSyncIndicator.tsx`

**Critical gap: dot has no color**. The dot `<View>` in the mobile skeleton has `width`, `height`, and `borderRadius` set, but **no `backgroundColor`**. Every mobile sync indicator renders a transparent/invisible dot. The `amberThreshold` prop is explicitly discarded (`void _amberThreshold`).

All other gaps match the web skeleton (no `onResolve`, abbreviated labels, no tap detail popover).

#### A.1.4 Dispatch Board (FE-B4) — `apps/web/src/features/dispatch-board/components/DispatchToolbar.tsx`

```
surface="dispatch"       ✅ correct
pendingCount={optimisticMoveCount}   — local mutation count, NOT BE-B15
state derived locally    — "syncing" when count > 0, else syncState from board hook
lastSyncedAt={lastBoardFetch}        ✅ present
compact                  ✅ present
onResolve                ✗ not passed — no click-to-detail on dispatch
onManualSync             ✗ not passed — correct; dispatch does not support manual sync
```

**Assessment**: Dispatch is intentionally decoupled from BE-B15. Its `pendingCount` comes from optimistic move mutations (TanStack Query `useMutationState`), not the unified sync status endpoint. This is correct behavior — dispatch's "pending" means "moves not yet confirmed by server," not the same as calendar/QB conflict counts. **FE-B15 does not change dispatch's data source.** It only wires `onResolve` to navigate to `/schedule#conflicts` and ensures the dot color is rendered correctly.

#### A.1.5 Mobile Sync (FE-B7) — `apps/mobile/features/offline-sync/components/MobileSyncStatusBar.tsx`

```
surface="mobile-sync"    ✅ correct
pendingCount             — from useSyncQueueStore (WatermelonDB local count) — NOT BE-B15
state derived locally    — correct 5-state derivation from syncState.status
lastSyncedAt             — passed (with null coercion, type gap: null vs undefined)
onManualSync={undefined} ✅ correct — mobile sync is OS-scheduled, no manual trigger
onResolve={openDrawer}   — PASSES this prop; skeleton silently ignores it — BUG
compact={true}           ✅ correct
```

**Critical bug**: `onResolve={openDrawer}` is passed but never called because the web and mobile skeletons do not render a clickable element in the non-error states that calls `onResolve`. The `SyncQueueDrawer` never opens from the status bar tap. FE-B15 wires this.

**Assessment**: Like dispatch, mobile-sync's `pendingCount` stays local (WatermelonDB). BE-B15's `mobile_data` surface endpoint provides last-session outcome for the `state` signal, but the raw pending count comes from WatermelonDB which has fresher local data. FE-B15 wires `useInFlightSyncStatus("mobile-sync")` as an **ambient background refetch only** (30s interval) — the primary count stays from the store.

#### A.1.6 Calendar (FE-B8) — `packages/ui/src/calendar-sync-status/CalendarSyncStatusRow.tsx`

**Most significant drift**: `CalendarSyncStatusRow` is a **completely separate bespoke component** that does not compose `<InFlightSyncIndicator>` at all. It has its own `DotState` enum (`"healthy" | "pending_conflicts" | "error" | "loading"`), its own dot color logic, its own subtitle logic. It lives in `packages/ui/src/calendar-sync-status/` — a separate directory from the shared sync-indicator.

Token choices: `colors.margin[400]` / `colors.alert[400]` / `colors.fault[600]` — identical token choices to the web skeleton (independent convergence).

The web feature-scoped calendar surface (`apps/web/src/features/calendar-conflict/`) has no `InFlightSyncIndicator` usage at all.

**Assessment**: The calendar surface split into two separate UI surfaces: a mobile owner status row (`CalendarSyncStatusRow` in `packages/ui`) and a web settings page (`CalendarConnectionStatusCard`). Neither composes `<InFlightSyncIndicator>`. FE-B15 must add `<InFlightSyncIndicator surface="calendar">` to the web calendar settings page AND refactor `CalendarSyncStatusRow` (mobile) to compose it — OR leave `CalendarSyncStatusRow` as-is and accept that mobile calendar status stays as a bespoke component. **Decision resolved in A.2 below.**

#### A.1.7 QuickBooks (FE-B9) — `apps/web/src/features/quickbooks-conflict/components/QbConflictQueue.tsx`

```
surface="quickbooks"     ✅ correct
compact={true}           ✅ correct
pendingCount             ✗ NOT passed — defaults to 0; indicator always shows 0
state                    ✗ NOT passed — defaults to "idle"; indicator always shows idle
onResolve                ✗ NOT passed
onManualSync             ✗ NOT passed
```

**Assessment**: The QB indicator is decorative only — it renders but never reflects actual sync state. `QbConflictQueue` already fetches conflict data via `useQbConflicts` and has `totalPending` available locally. FE-B15 adds `useInFlightSyncStatus("quickbooks")` to wire actual state from BE-B15 and passes the result as props.

#### A.1.8 Backend (BE-B15) — Confirmed Present

`backend/api/routes/sync_status.py` is confirmed present and functional.

**Key finding**: Backend surface names use underscores (`mobile_data`, `background`), frontend `SyncSurface` type uses hyphens (`mobile-sync`). A mapping layer is required in the hook.

**Backend response shape** (from `SyncStatusResponse`):

```json
{
  "surface": "calendar",
  "state": "synced_idle | synced_pending | syncing | sync_error | sync_paused",
  "pending_count": 3,
  "pending_items": [{"type": "conflict", "label": "Conflict #abc — calendar conflict"}],
  "last_sync_at": "2026-05-27T14:32:18Z",
  "next_sync_at": null,
  "manual_trigger_supported": true,
  "resolve_target": "/api/v1/calendar/conflicts",
  "amber_threshold": 5
}
```

**Note**: backend `state` strings use underscores (`synced_idle`, `sync_error`); frontend `SyncState` union uses hyphens (`synced-pending`, `error`). The hook must translate.

`manual_trigger_supported` is returned per surface: `calendar=False`, `quickbooks=True`, `mobile=True`. The frontend currently uses `surface !== "mobile-sync"` as the gate — FE-B15 should respect the backend-returned value instead.

#### A.1.9 Token Audit: Confirmed Ramp Gaps

FE-B8 batch notes flagged this; confirmed by reading both `CalendarSyncStatusRow` and the web skeleton. The token ramp for `margin`, `alert`, and `fault` does not have `500` stops:

- `margin` ramp: `50/100/200/400/600/800/900` — no `500`
- `alert` ramp: `50/100/200/400/600/800/900` — no `500`  
- `fault` ramp: `50/100/200/400/600/800/900` — no `500`

Both existing implementations independently settled on `400` for green/amber dots and `600` for red. FE-B15 standardizes on these confirmed token stops. The spec's "500" references are approximations; the design doc H token table must reflect the actual available stops.

---

### A.2 Updated `InFlightSyncIndicator` in `packages/ui` — Changes from Skeleton to Unified

#### Changes to `packages/ui/src/sync-indicator/types.ts`

**1. Add `"background-sync"` to `SyncSurface`**:

```
SyncSurface: "dispatch" | "mobile-sync" | "calendar" | "quickbooks" | "background-sync"
```

**2. No other prop changes** — the existing `InFlightSyncIndicatorProps` interface is already correct and complete. All changes are additive or behavioral (wiring `onResolve`, fixing dot color in mobile, adding tooltip).

#### Changes to web `packages/ui/src/sync-indicator/web/InFlightSyncIndicator.tsx`

| Change | What | Why |
|:---|:---|:---|
| Wire `onResolve` | Render clickable wrapper in error/synced-pending states; call `onResolve()` on click | FE-B7 passes it; was silently dropped |
| Fix pending count badge token | `bg-neutral-200` → `bg-alert-400 text-white` (or `bg-alert-100 text-alert-800` for softer treatment) | Matches H token spec |
| Extend `lastSyncedAt` display | Show in `synced-pending` state as well as `idle` | Spec shows timestamp in both |
| Finalize state label copy | Match spec copy: `"Synced · {relativeTime}"`, `"Synced · {N} pending · syncing in {T}"`, `"Syncing {N} changes..."`, `"Sync error · {N} pending"`, `"Paused · {N} queued"` | Skeleton had abbreviated stubs |
| Add hover detail tooltip | Popover showing `pending_items` from BE-B15 (capped at 5) | Core spec behavior; missing from skeleton |
| Respect `manual_trigger_supported` from hook | Hide "Sync now" based on hook result, not hard-coded surface exclusion | Backend is authoritative |

#### Changes to mobile `packages/ui/src/sync-indicator/mobile/InFlightSyncIndicator.tsx`

| Change | What | Why |
|:---|:---|:---|
| **Fix dot color** (critical) | Add `backgroundColor: getDotColor(state, pendingCount, amberThreshold)` to dot `<View>` | Dot is invisible today |
| Wire `onResolve` | Wrap outer `<View>` in `<Pressable>` calling `onResolve()` | FE-B7 passes `onResolve={openDrawer}`; was dropped |
| Apply `amberThreshold` | Use `amberThreshold` in dot color derivation instead of discarding it | Was `void _amberThreshold` |
| Add tap detail popover | Bottom sheet or `<Modal>` with `pending_items` list, auto-dismiss on outside press | Spec Decision 2 |
| Finalize state label copy | Same as web | Consistency |

#### Calendar Surface — Resolution of A.1.6 Drift

`CalendarSyncStatusRow` is **left in place** — it serves the mobile owner tab's needs with its existing navigation affordance (deep-link to web). FE-B15 does **not** refactor it to compose `<InFlightSyncIndicator>`.

Instead, FE-B15 adds `<InFlightSyncIndicator surface="calendar">` to the **web calendar settings page** (`CalendarConnectionStatusCard` / the integrations page header), which is the missing consumer. This is the surface the spec refers to for calendar: `Settings > Integrations > Calendar`.

`CalendarSyncStatusRow` gets a single additive prop `pendingCount?: number` so it can show the count in the subtitle text — this is the mobile owner status row integration per spec Decision 4 and §16.9. The component itself remains bespoke; only its data wiring improves.

---

### A.3 New Shared Hook: `useInFlightSyncStatus(surface)` in `packages/ui/src/hooks/`

**File**: `packages/ui/src/hooks/useInFlightSyncStatus.ts` *(new)*

This hook is the single data layer for all four sync surfaces. All consumers call it and receive a normalized `InFlightSyncStatus` object ready to spread as props.

**Responsibilities**:
1. Maps frontend surface names to backend surface path parameters (hyphen → underscore)
2. Calls `GET /api/v1/sync/{surface}/status` via TanStack Query
3. Maps backend state strings (underscored) to frontend `SyncState` values (hyphenated)
4. Subscribes to SSE `sync_status_changed` events via `useSseChannel` and invalidates the query on match
5. Returns a typed `InFlightSyncStatus` result including `pendingItems`, `nextSyncAt`, and `amberThreshold`

**Surface name mapping**:

| Frontend `SyncSurface` | Backend path param |
|:---|:---|
| `"dispatch"` | — (dispatch does not call BE-B15; local only) |
| `"mobile-sync"` | `"mobile_data"` |
| `"calendar"` | `"calendar"` |
| `"quickbooks"` | `"quickbooks"` |
| `"background-sync"` | `"background"` |

**State string mapping** (backend → frontend):

| Backend | Frontend `SyncState` |
|:---|:---|
| `"synced_idle"` | `"idle"` |
| `"synced_pending"` | `"synced-pending"` |
| `"syncing"` | `"syncing"` |
| `"sync_error"` | `"error"` |
| `"sync_paused"` | `"paused"` |

---

### A.4 Per-Consumer Migration Table

| Consumer | File | Changes Required | Props Added | Props Removed/Changed |
|:---|:---|:---|:---|:---|
| **Dispatch** | `DispatchToolbar.tsx` | Add `onResolve={() => router.push('/schedule#conflicts')}` | `onResolve` | None |
| **Mobile Sync** | `MobileSyncStatusBar.tsx` | Replace `lastSyncedAt` null coercion; confirm `onResolve` now works after skeleton fix | None new | `null` → `undefined` for `lastSyncedAt` |
| **Calendar (web)** | `CalendarConnectionStatusCard` + integrations page | **New consumer** — add `<InFlightSyncIndicator surface="calendar">` wired to `useInFlightSyncStatus("calendar")` | All props from hook | n/a (new usage) |
| **Calendar (mobile)** | `CalendarSyncStatusRow.tsx` | Add `pendingCount?: number` prop; show in subtitle text | `pendingCount?` | None (additive only) |
| **QuickBooks** | `QbConflictQueue.tsx` | Wire `useInFlightSyncStatus("quickbooks")` result; pass `state`, `pendingCount`, `onResolve` | `state`, `pendingCount`, `onResolve` | None |
| **Background Sync (mobile)** | `BackgroundSyncStatusRow.tsx` | Add `<InFlightSyncIndicator surface="background-sync">` wired to `useInFlightSyncStatus("background-sync")` | All props from hook | n/a |

**Migration safety**: `InFlightSyncIndicatorProps` is additive-only in FE-B15. No prop is renamed or removed. All four prior consumers compile without changes. The prop additions are all optional with working defaults. The only required change per consumer is passing new props for correct behavior; the component will not break if consumers delay adoption.

---

## B — Execution Order

Per `impl-plan §6 FE-B15` five-step order:

| Step | Item | Rationale | Est. Days |
|:---|:---|:---|:---:|
| **1** | **Audit pass** (complete — this document IS the audit) | Must document actual drift before writing a line | 0.5 |
| **2** | **Unified `InFlightSyncIndicator` API** — fix mobile dot color; wire `onResolve` in both variants; add `"background-sync"` to `SyncSurface`; finalize state label copy; add hover/tap detail panel | API consolidation; all consumers depend on this | 1 |
| **3** | **`useInFlightSyncStatus(surface)` hook** — new in `packages/ui/src/hooks/`; TanStack Query + SSE invalidation + state/surface name translation | Backend integration; produces the data all consumers will consume | 1 |
| **4** | **Apply to all surfaces** — QB: wire hook result as props; Calendar web: new consumer; Calendar mobile: additive `pendingCount`; Dispatch: add `onResolve`; Mobile sync: fix null→undefined; Background sync: add as new consumer | Consumer wiring | 1.5 |
| **5** | **Visual + behavioral consistency review** — cross-platform: web dispatch, web QB, web calendar, mobile sync bar, mobile owner tab; verify dot colors, label copy, tooltip, click-to-detail, SSE invalidation | Closes refinement | 0.5 |

---

## C — API Contracts

### C.1 Endpoint

**Path**: `GET /api/v1/sync/{surface}/status`
**Auth**: JWT bearer; `settings.view` permission
**Path param**: `surface` — `calendar | quickbooks | mobile_data | background`

**Request**: No query params; no body.

**Response** (`SyncStatusResponse`):

```typescript
interface SyncStatusResponse {
  surface:                  string;         // "calendar" | "quickbooks" | "mobile_data" | "background"
  state:                    string;         // "synced_idle" | "synced_pending" | "syncing" | "sync_error" | "sync_paused"
  pending_count:            number;
  pending_items:            PendingItem[];  // max 5 items (server-capped)
  last_sync_at:             string | null;  // ISO-8601
  next_sync_at:             string | null;
  manual_trigger_supported: boolean;
  resolve_target:           string | null;  // internal API path (hook maps to UI route)
  amber_threshold:          number;         // resolved from tenant setting; default 5
}

interface PendingItem {
  type:  string;
  label: string;
}
```

**Error cases**:
- `400`: invalid `surface` value
- `403`: missing `settings.view` permission
- `404`: surface has no data yet (returns `synced_idle` with `pending_count: 0`, not 404)

### C.2 TanStack Query Key and Cache Strategy

**Query key**: `["sync-status", surface]` — keyed per surface; each surface is an independent query.

**Cache config**:

| Parameter | Value | Rationale |
|:---|:---|:---|
| `staleTime` | `30_000` (30s) | Sync state changes at sub-minute frequency; 30s is acceptable ambient awareness lag |
| `refetchInterval` | `60_000` (60s) | Background polling; SSE invalidation is the primary freshness mechanism |
| `refetchOnWindowFocus` | `true` | Refresh on tab focus to catch state changes while tab was hidden |
| `retry` | `2` | Transient network errors; do not block UI on retry |

**SSE invalidation**: `useSseChannel` emits `sync_status_changed` events. The hook listens for events matching the current surface and calls `queryClient.invalidateQueries(["sync-status", surface])`. This makes the indicator update in near-real-time without polling pressure.

### C.3 Polling vs SSE

Both mechanisms are active simultaneously:
- **SSE** is the primary freshness mechanism — near-instant state updates on sync start/complete/error
- **Polling** (60s) is the fallback — ensures the indicator recovers after an SSE channel drop

---

## D — State Management

### D.1 `useInFlightSyncStatus` Hook State

The hook returns a normalized `InFlightSyncStatus` object:

```typescript
interface InFlightSyncStatus {
  state:                    SyncState;      // translated to frontend enum
  pendingCount:             number;
  pendingItems:             PendingItem[];
  lastSyncedAt:             Date | undefined;
  nextSyncAt:               Date | undefined;
  manualTriggerSupported:   boolean;        // from backend; replaces hard-coded surface check
  amberThreshold:           number;
  isLoading:                boolean;
  isError:                  boolean;
}

// Usage:
const status = useInFlightSyncStatus("quickbooks");
// Then: <InFlightSyncIndicator surface="quickbooks" {...status} />
```

### D.2 Per-Surface Data Sources

| Surface | `pendingCount` source | `state` source |
|:---|:---|:---|
| `dispatch` | Local — `useMutationState` (optimistic move count) | Local — board hook `syncState` |
| `mobile-sync` | Local — `useSyncQueueStore` (WatermelonDB) | `useInFlightSyncStatus` (last session outcome) |
| `calendar` | `useInFlightSyncStatus` (BE-B15 conflict count) | `useInFlightSyncStatus` |
| `quickbooks` | `useInFlightSyncStatus` (BE-B15 conflict count) | `useInFlightSyncStatus` |
| `background-sync` | `useInFlightSyncStatus` (BE-B15 session deferred/failed) | `useInFlightSyncStatus` |

**Rationale for mixed sources on mobile-sync**: WatermelonDB has fresher local pending-count data than the backend (operations are written locally before they sync). The backend endpoint's `mobile_data` surface reflects the *last session outcome*, which is useful for deriving `state` (did the last sync succeed?) but lags on raw count. The hybrid approach uses each source for what it knows best.

### D.3 Per-Surface Query Invalidation

SSE `sync_status_changed` event payload: `{ surface: string, state: string, pending_count: number }`.

The `useInFlightSyncStatus` hook subscribes to the SSE channel and invalidates `["sync-status", surface]` when an event arrives for the matching surface. Dispatch does not use this hook and is not affected.

---

## E — Error States

### E.1 `state="error"` (Sync Error)

The indicator renders a red dot + `"Sync error · {N} pending"` label. The `onResolve` callback is called when the indicator is clicked/tapped, navigating to the surface-specific resolution page.

Per-surface resolve targets (UI routes, not API paths):

| Surface | `onResolve` target |
|:---|:---|
| `dispatch` | `/schedule` (board with conflict previewPane open) |
| `calendar` | `/settings/integrations/calendar/conflicts` |
| `quickbooks` | `/settings/integrations/quickbooks/conflicts` |
| `mobile-sync` | `openDrawer()` — opens `SyncQueueDrawer` |
| `background-sync` | Mobile sync queue surface |

**Note**: `resolve_target` in the backend response is an API path, not a UI route. The hook must map `resolve_target` to the appropriate UI route or `onResolve` callback pattern. The per-surface `onResolve` handlers remain in the consuming surface (not in the hook) since they involve React Router / Expo Router navigation.

### E.2 `pendingCount` Unavailable (BE-B15 Endpoint Down)

If the sync status endpoint returns an error (`isError: true`):
- The indicator renders with `state="idle"`, `pendingCount=0` — safe default (does not show false errors)
- A `console.warn` is emitted; no error state is surfaced to users for a status query failure
- The component does not unmount or show a skeleton; it silently falls back to idle appearance

**Rationale**: The sync indicator is ambient awareness, not critical path. Showing an error state because the *status query* failed would be confusing (is the sync broken, or just the status check?). Degrade gracefully to idle.

### E.3 SSE Channel Unavailable

If SSE drops, the 60s polling interval maintains freshness. No visible fallback state. The indicator continues to render from the last cached TanStack Query result.

---

## F — TypeScript Interfaces

### F.1 `SyncSurface` Union (FINAL — replaces FE-B1 version)

```typescript
export type SyncSurface =
  | "dispatch"        // FE-B4: Dispatch board optimistic move count
  | "mobile-sync"     // FE-B7: Mobile offline queue → server sync
  | "calendar"        // FE-B8: Calendar conflict pending changes
  | "quickbooks"      // FE-B9: QuickBooks bilateral sync pending
  | "background-sync"; // FE-B9: Background sync session (added FE-B15)
```

### F.2 `SyncState` Union (unchanged from FE-B1)

```typescript
export type SyncState =
  | "idle"           // No active sync; 0 pending
  | "synced-pending" // Sync complete; N>0 operations queued
  | "syncing"        // Active sync in progress
  | "error"          // Last sync attempt failed
  | "paused";        // Sync explicitly paused
```

### F.3 `InFlightSyncIndicatorProps` (FINAL — supersedes FE-B1 skeleton)

```typescript
export interface InFlightSyncIndicatorProps {
  /** Identifies the sync surface. Determines data source and click-to-detail behavior. */
  surface: SyncSurface;
  /** Count of pending sync operations. Default: 0. */
  pendingCount?: number;
  /** Timestamp of last successful sync. */
  lastSyncedAt?: Date | undefined;
  /** Current sync state. Default: "idle". */
  state?: SyncState;
  /** Pending count above which dot shifts to amber. Default: 5. */
  amberThreshold?: number;
  /** Manual sync handler. When provided, renders "Sync now" in synced-pending state. */
  onManualSync?: () => void;
  /** Navigate to resolution surface. Renders on error state and in synced-pending state. */
  onResolve?: () => void;
  /** Compact mode: dot + count only. No label text. */
  compact?: boolean;
  /** Pending items for hover/tap detail tooltip. Max 5. */
  pendingItems?: PendingItem[];
  /** Next scheduled sync time (for label "syncing in 2m"). */
  nextSyncAt?: Date | undefined;
  testID?: string;
}
```

**Migration delta from FE-B1**:
- `lastSyncedAt` type narrowed: `Date | null` → `Date | undefined` (null removed; null was a mobile-introduced inconsistency)
- `pendingItems?: PendingItem[]` — **new optional prop** for tooltip content
- `nextSyncAt?: Date | undefined` — **new optional prop** for "syncing in Xm" label

Both new props are optional with no behavior change when absent. All existing consumers continue to compile without changes.

### F.4 `InFlightSyncStatus` (hook return type — new in FE-B15)

```typescript
export interface InFlightSyncStatus {
  state:                    SyncState;
  pendingCount:             number;
  pendingItems:             PendingItem[];
  lastSyncedAt:             Date | undefined;
  nextSyncAt:               Date | undefined;
  manualTriggerSupported:   boolean;
  amberThreshold:           number;
  isLoading:                boolean;
  isError:                  boolean;
}
```

### F.5 `PendingItem` (new in FE-B15)

```typescript
export interface PendingItem {
  type:  string;
  label: string;
}
```

### F.6 Backend surface → Frontend surface mapping (hook-internal)

```typescript
const SURFACE_MAP: Record<Exclude<SyncSurface, "dispatch">, string> = {
  "mobile-sync":    "mobile_data",
  "calendar":       "calendar",
  "quickbooks":     "quickbooks",
  "background-sync": "background",
};

const STATE_MAP: Record<string, SyncState> = {
  "synced_idle":    "idle",
  "synced_pending": "synced-pending",
  "syncing":        "syncing",
  "sync_error":     "error",
  "sync_paused":    "paused",
};
```

---

## G — Test Plan

**Test subfolder**: `apps/{web,mobile}/__tests__/batch_fe_b15/`

### G.1 Unit Tests — Target: 20+ (Vitest — `@pilot/ui`)

| # | Test | Why Critical |
|:---|:---|:---|
| 1–5 | `InFlightSyncIndicator` web: renders correct dot class per `state` × `pendingCount` × `amberThreshold` (5 state combinations) | Core visual logic; covers amber threshold |
| 6 | `onResolve` is called when indicator is clicked in error state | Was silently dropped in skeleton |
| 7 | `onResolve` is called when indicator is clicked in synced-pending state | New behavior |
| 8 | `onManualSync` renders "Sync now" only when `state="synced-pending"` and prop is provided | Existing — regression test |
| 9 | "Sync now" not rendered when `manualTriggerSupported=false` | New behavior |
| 10 | Pending count badge shows `pendingCount` when `> 0` | Regression |
| 11 | `compact` mode renders dot + count only, no label | Regression |
| 12–14 | Mobile: dot `backgroundColor` is set for idle / syncing / error states | Critical — was invisible |
| 15 | Mobile: `amberThreshold` controls dot color at `pendingCount` boundary | Was discarded in skeleton |
| 16 | Mobile: `onResolve` is called on press (Pressable wraps content) | Was no-op in skeleton |
| 17 | Hover detail tooltip shows `pendingItems` (web; up to 5) | New feature |
| 18 | Hover detail tooltip shows "+N more" when `pendingCount > 5` | New feature |
| 19 | `lastSyncedAt` shown in both `idle` and `synced-pending` states | Fixed from skeleton |
| 20 | State label copy matches spec for all 5 states | Finalizes from abbreviated stubs |
| 21 | `useInFlightSyncStatus("calendar")` maps backend state `"sync_error"` → `"error"` | Name translation |
| 22 | `useInFlightSyncStatus` returns `idle` defaults when endpoint returns error | Graceful degradation |
| 23 | `useInFlightSyncStatus` invalidates query on matching SSE event | SSE integration |
| 24 | `SyncSurface` type accepts `"background-sync"` | Added in FE-B15 |

### G.2 Integration Tests — Target: 8+

| # | Test | Location |
|:---|:---|:---|
| 1 | Dispatch board toolbar renders indicator with `state="syncing"` during optimistic move | `batch_fe_b15/dispatch.integration.test.tsx` |
| 2 | QB conflict queue indicator shows actual `pendingCount` from `useInFlightSyncStatus` | `batch_fe_b15/qb.integration.test.tsx` |
| 3 | QB indicator click navigates to `/settings/integrations/quickbooks/conflicts` | Same |
| 4 | Calendar settings page indicator shows `pendingCount` from BE-B15 mock | `batch_fe_b15/calendar.integration.test.tsx` |
| 5 | Mobile sync bar tap opens `SyncQueueDrawer` (via `onResolve`) | `batch_fe_b15/mobile-sync.integration.test.tsx` |
| 6 | SSE `sync_status_changed` event triggers re-render with new `pendingCount` | `batch_fe_b15/sse-invalidation.integration.test.tsx` |
| 7 | BE-B15 endpoint error → indicator falls back to `idle` / `0` (no error shown) | `batch_fe_b15/error-fallback.integration.test.tsx` |
| 8 | All four surface usages compile with unified `InFlightSyncIndicatorProps` (TypeScript `check-types`) | CI gate |

### G.3 E2E — Not Required

Per impl plan §6 FE-B15 test focus note: E2E targets are listed as `2+` but are listed under "stretch / pending backend." Given the refinement scope (no new user flows, only visual consistency), E2E is not required for batch completion. The 8 integration tests cover the behavioral surface adequately.

---

## H — Token Audit

All four sync surfaces must use the same token mapping after FE-B15. Confirmed token stops from `packages/ui/src/tokens.ts` ramp audit (FE-B8 note + direct observation):

| State | Dot Color | Dot Class (web) | RN value (mobile) | Badge/Pill |
|:---|:---|:---|:---|:---|
| `idle` (0 pending) | Green | `bg-margin-400` | `tokens.colors.margin[400]` | none |
| `synced-pending` (≤ threshold) | Green | `bg-margin-400` | `tokens.colors.margin[400]` | `bg-alert-100 text-alert-800` |
| `synced-pending` (> threshold) | Amber | `bg-alert-400` | `tokens.colors.alert[400]` | `bg-alert-100 text-alert-800` |
| `syncing` | Amber + pulse | `bg-alert-400 animate-pulse` | `tokens.colors.alert[400]` + animation | `bg-alert-100 text-alert-800` |
| `error` | Red | `bg-fault-600` | `tokens.colors.fault[600]` | `bg-fault-100 text-fault-700` |
| `paused` | Neutral | `bg-neutral-400` | `tokens.colors.neutral[400]` | `bg-neutral-100 text-neutral-600` |

**Note on "alert-500" spec references**: The spec and arch doc §16.13 reference `alert-500` for the pending badge. The token ramp has no `500` stop. The correct substitution is `bg-alert-100 text-alert-800` (soft amber pill — passes WCAG AA contrast on white). This is consistent with how `CalendarSyncStatusRow` handles amber subtitles (`subtitleWarning: colors.alert[800]`).

**CalendarSyncStatusRow token alignment**: After FE-B15, `CalendarSyncStatusRow` uses `colors.margin[400]` / `colors.alert[400]` / `colors.fault[600]` — identical to the unified `InFlightSyncIndicator` token choices. No change needed.

---

## I — Final Integration Notes

### I.1 Locked API — Platform Canonical Sync Status Pattern

After FE-B15, `<InFlightSyncIndicator>` in `packages/ui/src/sync-indicator/` is the **platform-canonical sync status visualization** for MVP and Phase 2. The API defined in Section F.3 (`InFlightSyncIndicatorProps`) is **locked for MVP**.

**Rule for Phase 2**: Any Phase 2 sync surface (Salesforce, HubSpot, generic webhook integration) wanting a sync indicator:
1. Imports `InFlightSyncIndicator` from `@pilot/ui`
2. Implements `useInFlightSyncStatus(surface)` — or extends the hook if the new surface requires a new backend surface path param
3. Adds the new surface string to `SyncSurface` union in `types.ts`
4. Does **not** create a new bespoke sync status component

**The pattern is extensible, not replaceable.** `CalendarSyncStatusRow` remains as a legacy exception for the mobile owner tab, but no new exceptions are created.

### I.2 `background-sync` Surface Note

The `"background-sync"` surface was referenced in FE-B9 completion notes but was never added to `SyncSurface`. FE-B15 adds it. `BackgroundSyncStatusRow` in `apps/mobile/features/offline-sync/components/BackgroundSyncStatusRow.tsx` is the consumer. The backend uses `"background"` as the path param (handled by `SURFACE_MAP` in the hook).

### I.3 `dispatch` Surface Remains Locally Sourced

The dispatch indicator is the one surface that does **not** use `useInFlightSyncStatus`. Its pending count is the count of in-flight optimistic move mutations — a real-time local signal that is more responsive than polling BE-B15. BE-B15's `sync_status.py` does not have a dispatch surface. This is intentional and correct. After FE-B15, dispatch remains locally sourced.

### I.4 Barrel Export Update

`packages/ui/src/sync-indicator/index.ts` must be updated to also export the new `PendingItem` type and the `InFlightSyncStatus` interface. The `useInFlightSyncStatus` hook exports from `packages/ui/src/hooks/` and is re-exported from the main `packages/ui/src/index.ts` barrel under the `// ── FE-B15 Exports ──` comment block.

### I.5 `background-sync` Manual Trigger Gate

Per spec Decision 6: background sync does not support manual trigger (OS-scheduled). The backend confirms this: `_get_mobile_status` returns `manual_trigger_supported: True` for `mobile_data` (foreground mobile sync) but the background surface's conceptual role excludes manual trigger. The hook's `manualTriggerSupported` field reflects the backend value; `"background-sync"` should return `false`. Implementation must verify the backend returns the correct value or the hook should hard-override it to `false` for `"background-sync"`.

---

*Design document produced by: Pilot Architect mode — May 27, 2026*
*Based on: `frontend-pass-4-tier-4-flow-12-in-flight-sync-indicator-spec.md` v1.0, `mvp-arch.md §16.13`, `pilot-app-mvp-frontend-impl-plan.md §6 FE-B15`, codebase audit of all four prior sync surface consumers and the FE-B1 skeleton*
