# FE-B9 Batch Design — Tier 1 Conflict UIs + Background Sync (Pass 4 Tier 1 #1, #2, #3)

**Batch**: FE-B9
**Phase**: Phase 1 — Surface Design Session
**Date**: 2026-05-25
**Author**: Pilot Architect
**Status**: Design Complete — Ready for React Engineer Handoff
**Prerequisite Batches**: FE-B0, FE-B1, FE-B2, FE-B3, FE-B4, FE-B5, FE-B6, FE-B7, FE-B8
**Backend Gate**: BE-B7b (mobile conflict engine / A47–A48), BE-B8 (QB conflicts + background sync / A49–A51)
**Gates Downstream**: FE-B15 (`<InFlightSyncIndicator surface="quickbooks">` + background sync surface added here)
**Test Subfolder**: `apps/{web,mobile}/__tests__/batch_fe_b9/`

---

## Prerequisites Confirmed

- `EscalationStatusRow` — **ALREADY EXISTS** from FE-B7 ✅ (FE-B9 is a consumer, not the creator)
- `IntegrationConflictResolver` — FE-B8 ✅ **LOCKED interface — FE-B9 extends via optional additive props only**
- `DiffView` (`variant="qb-entity"` already in the union; `variant="entity"` for mobile escalation) — FE-B5 ✅
- `useStalenessRetry()` — FE-B4 ✅
- `useSseChannel()` — FE-B4 ✅
- `PendingBadge` — FE-B7 ✅
- `useOptimisticMutation()` — FE-B7 ✅
- `NotificationBanner` — FE-B1 ✅
- `InFlightSyncIndicator` skeleton — FE-B1 ✅
- `SyncOrchestrator` — FE-B7 ✅
- `CONFLICT_CLASS_TOKENS` / `ConflictVisualTokens` — FE-B4 ✅
- WatermelonDB models (7 entity types) — FE-B7 ✅
- Backend endpoints confirmed live in `api-schema.d.ts`: `owner/field-issues`, `owner/field-issues/{id}/resolve`, `integrations/quickbooks/conflicts`, `integrations/quickbooks/conflicts/{id}/resolve`

---

## Key Codebase Facts Established During Design Session

| Fact | Detail |
|:---|:---|
| `EscalationStatusRow` exists? | **YES** — established in FE-B7 at `packages/ui/src/escalation-status/EscalationStatusRow.tsx`. FE-B9 IMPORTS it; does NOT recreate it. |
| `IntegrationConflictResolver` interface | **LOCKED** from FE-B8 — see Section F.1 for the base interface. FE-B9 adds `masterDirection` as an optional prop. |
| Mobile escalation queue route | `/dashboard/approvals/field-issues` — sub-tabbed alongside existing Quotes tab at `/dashboard/approvals` |
| QB conflict queue route | `/settings/integrations/quickbooks/conflicts` — parallel to FE-B8's calendar pattern |
| `apps/web` uses `src/` prefix | YES — `apps/web/src/app/(authed)/...` |
| `apps/mobile` has no `src/` prefix | NO `src/` — `apps/mobile/features/...`, `apps/mobile/app/(tabs)/...` |
| Voice for QB conflicts | **READ-ONLY STATUS QUERY ONLY** — `list_pending_qb_conflicts` intent only; no resolve intent. All QB resolution routes to web. |
| Voice for field issues | Active resolution via `resolve_field_issue` intent with confirm-as-turn — same as FE-B8 calendar pattern. |
| Background sync photos/voice | **EXCLUDED** from background sync scope — data queue only (time entries, expenses, status changes, LOTO, change orders) |
| Background sync settings UI location | `Settings > Sync & Storage > Background sync` on mobile (actual full settings UI deferred to FE-B11) — FE-B9 builds the status indicator row in the existing sync queue drawer only |
| QB conflict auto-expiry | **OFF by default** for all QB entity types — opposite default from calendar (Flow 6). Tenants opt-in per entity type. Actual settings UI in FE-B11. |
| QB master-aware column ordering | Quotes → Pilot left. Invoices → QuickBooks left. Customers/Expenses → Pilot left by default (tenant override in FE-B11). |

---

## Resolved Design Decisions

### Decision 1 — Mobile Escalation Queue Location

**Decision**: `/dashboard/approvals/field-issues` sub-tabbed alongside the existing Quotes tab. Tab labels: **Quotes** and **Field issues**. Each tab has its own count badge.

**Rationale**: Mobile escalations are operational ("items waiting on owner"), not integration concerns. Settings → Integrations is for external systems (QB, Calendar). The existing Approvals surface already collects owner-action items; escalations are a kind of approval.

**Route tree**:
```
apps/web/src/app/(authed)/dashboard/approvals/
  page.tsx                  ← Approvals shell with tab navigation
  field-issues/
    page.tsx                ← FieldIssuesQueuePage (the escalation list)
    [id]/
      page.tsx              ← FieldIssueDetailPage (the resolution view)
    history/
      page.tsx              ← FieldIssueHistoryPage (full archive + filters)
```

### Decision 2 — QB Conflict Queue Location

**Decision**: `/settings/integrations/quickbooks/conflicts` as a fourth tab within the existing QuickBooks integration settings page (alongside Connection, Mapping, Sync log tabs). This is parallel to FE-B8's calendar conflict placement.

**Rationale**: QB conflicts are an integration concern — they live with the integration. Identical reasoning to FE-B8's calendar placement; same mental model for owners.

**Route tree**:
```
apps/web/src/app/(authed)/settings/integrations/quickbooks/
  page.tsx                   ← QuickBooksIntegrationSettingsPage (existing — add Conflicts tab)
  conflicts/
    page.tsx                 ← QbConflictQueuePage
    [id]/
      page.tsx               ← QbConflictDetailPage
```

### Decision 3 — IntegrationConflictResolver Extension for QB

**FE-B8 locked interface is the base.** FE-B9 adds exactly one optional prop: `masterDirection`. All existing FE-B8 props are unchanged.

```typescript
// FE-B9 ADDITIVE EXTENSION — backward-compatible; FE-B8 usage unaffected
// masterDirection defaults to 'pilot' when not provided (preserves FE-B8 calendar behavior)
masterDirection?: 'pilot' | 'external';
```

The `masterDirection` prop determines column ordering:
- `'pilot'` (default): Pilot on left (read-leftward primacy = Pilot is master)
- `'external'`: external system on left (QB is master for invoices)

Per-entity-type ordering for QB:
| Entity | `masterDirection` value |
|:---|:---|
| Quote | `'pilot'` |
| Invoice | `'external'` |
| Customer | `'pilot'` (tenant override in FE-B11) |
| Expense | `'pilot'` (tenant override in FE-B11) |

The `renderDomainSpecificFields` slot (already in the FE-B8 locked interface) is used by FE-B9 to inject `<InvoiceFinancialDeltaCallout>` for invoice entity type conflicts only.

### Decision 4 — Per-Field Resolution UI

**Decision**: The "per-field" resolution option is surfaced via a **third action button** on the detail page: "Choose field by field →" (secondary, neutral style). Tapping it expands an inline field-picker below the two-column diff. Each `DiffField` row gains a radio button pair (pick Pilot value / pick QB or Server value). A "Commit field selections" button at the bottom of the picker submits the per-field resolution payload.

This pattern reuses the `DiffField` row component already established in FE-B5 (extended for this batch). The per-field picker **does not** appear for deletion-conflict types (existence-level decisions are always all-or-nothing).

**Scope**: Per-field resolution applies to both mobile escalations (field issues) and QB conflicts. It does NOT apply to calendar conflicts (FE-B8 did not support per-field; calendar is always "accept one side").

### Decision 5 — Background Sync Status Indicator Scope for FE-B9

**Decision**: FE-B9 builds the **status indicator row** inside the existing sync queue bottom-sheet drawer (the `<SyncQueueDrawer>` from FE-B7). This row shows last background sync attempt + state.

The full Background Sync *settings* UI at `Settings > Sync & Storage > Background sync` is deferred to FE-B11 (alongside other settings surfaces). FE-B9's scope:
1. Add `<BackgroundSyncStatusRow>` component at the top of `<SyncQueueDrawer>` (above the four queue sections)
2. Extend `<SyncQueueDrawer>` to show the row when `background_sync_enabled` is true
3. Add `useBackgroundSyncStatus()` hook consuming the telemetry from `SyncOrchestrator`

This is intentionally narrow — the OS throttle detection, push token registration, and silent push wiring are backend/infra concerns (A51). The UI observes state from the orchestrator; it does not manage OS APIs.

### Decision 6 — Push Notification Loop Closure (Tech Side)

**Decision**: When an owner resolves a field issue on web (BE-B8/A48 emits event), the tech's mobile app:
1. Receives silent push → `SyncOrchestrator.pull()` called
2. WatermelonDB `JobStatusChange` / escalation record transitions to terminal state
3. TanStack Query cache invalidated for escalation list
4. Queue item transitions to `resolved_in_favor_of_tech` | `resolved_in_favor_of_server` | `resolved_with_action`
5. A persistent log entry is added to the tech's activity log

**FE-B9 builds**: the terminal state rendering in `<SyncQueueItem>` and the push notification deep-link handler that routes to the escalation detail view on mobile.

**FE-B9 does NOT build**: the push notification permission request UI (FE-B13 scope per Tier 3 #11).

### Decision 7 — Mobile Owner Field Issues Status Row

**Decision**: Add `<FieldIssuesSyncStatusRow>` to the mobile Owner tab alongside the Calendar sync row (FE-B8) and QB sync row (established in FE-B7/Pass 2):

- **Healthy (none pending)**: green dot, "Field issues · None pending"
- **Pending issues**: amber dot, "Field issues · N pending," subtitle "Resolve on web →"
- No error state — escalations queue, they do not fail.

This is a new component in `packages/ui/src/field-issues-status/` (mobile-scoped, Gluestack primitives, lives in `packages/ui/` for architectural consistency).

---

## A — Component Implementation Plan

### A.1 New Shared Components (`packages/ui/src/`)

#### A.1.1 `IntegrationConflictResolver` — EXTENSION ONLY (not a new component)

| Field | Value |
|:---|:---|
| **File** | `packages/ui/src/integration-conflict-resolver/IntegrationConflictResolver.tsx` |
| **Change** | Add optional `masterDirection?: 'pilot' \| 'external'` prop. Default `'pilot'` preserves FE-B8 behavior. |
| **Do NOT fork** | FE-B9 extends the existing component in-place — zero new files in `integration-conflict-resolver/` for this extension |
| **Consumers** | FE-B8 (calendar, unaffected), FE-B9 (quickbooks), Phase 2 integrations |

#### A.1.2 `<FieldIssuesSyncStatusRow>` (mobile, new)

| Field | Value |
|:---|:---|
| **File** | `packages/ui/src/field-issues-status/FieldIssuesSyncStatusRow.tsx` |
| **Platform** | Mobile (Gluestack primitives) |
| **Pattern** | Mirrors `CalendarSyncStatusRow` (FE-B8) and QB sync row |
| **Consumers** | `apps/mobile/features/owner-tab/` (this batch); FE-B15 (status row refinement) |
| **Export from** | `packages/ui/src/index.ts` |

See Section F for full TypeScript interface.

#### A.1.3 `<InvoiceFinancialDeltaCallout>` (web, new shared)

| Field | Value |
|:---|:---|
| **File** | `packages/ui/src/invoice-financial-delta/InvoiceFinancialDeltaCallout.tsx` |
| **Platform** | Web only |
| **Purpose** | Renders financial delta + AR impact + tax-period warning for QB invoice conflicts. Passed via `renderDomainSpecificFields` slot on `<IntegrationConflictResolver>`. |
| **Consumers** | FE-B9 (QB invoice conflicts). Future: any integration with financial-stakes diff. |
| **Export from** | `packages/ui/src/index.ts` |

See Section F for full TypeScript interface.

---

### A.2 New Web Feature Components

#### A.2.1 Mobile Escalation (Field Issues) Surface — `apps/web/src/features/field-issues/`

| File | Purpose |
|:---|:---|
| `components/FieldIssuesQueue.tsx` | Paginated table; columns: Tech, Operation, Issue (server-generated explainer copy), Captured timestamp, Status pill, Resolve button; default sort descending by escalation creation time |
| `components/FieldIssueRow.tsx` | Single table row; operation type icon pill, status pill (`Pending` / `Auto-recovered` / `Stale`) |
| `components/FieldIssueFilterBar.tsx` | Filter chip row: Active techs (default on), Operation type multi-select, Auto-recovered toggle |
| `components/FieldIssueDetail.tsx` | Page shell: context header (explainer copy + tech identity + timestamps), two-column diff via `<IntegrationConflictResolver integration="calendar" masterDirection="pilot">` (escalations are always Pilot-authored = tech-side left), per-field picker, action bar |
| `components/EscalationContextHeader.tsx` | Server-generated plain-language explainer + tech identity row + collapsible timestamp details |
| `components/FieldIssueHistoryPanel.tsx` | Expandable last-30 resolved escalations; shown below queue and on empty state |
| `components/FieldIssueEmptyState.tsx` | "No field issues to resolve. Your team's captures are all syncing cleanly." + history panel |
| `hooks/useFieldIssues.ts` | TanStack Query list hook; `GET /api/v1/owner/field-issues`; cursor-paginated |
| `hooks/useFieldIssueDetail.ts` | TanStack Query detail hook; `GET /api/v1/owner/field-issues/{id}` |
| `hooks/useResolveFieldIssue.ts` | Mutation hook; composes `useStalenessRetry`; handles three 409 subtypes: `server_changed` / `auto_recovered` / `stale` |
| `hooks/useFieldIssuesSse.ts` | Composes `useSseChannel`; invalidates field-issues query on new escalation or resolution events |
| `mocks/fieldIssuesFixtures.ts` | Typed fixture data for unit tests and MSW handlers |

**Page route components** (App Router):

| File | Route |
|:---|:---|
| `apps/web/src/app/(authed)/dashboard/approvals/field-issues/page.tsx` | `/dashboard/approvals/field-issues` |
| `apps/web/src/app/(authed)/dashboard/approvals/field-issues/[id]/page.tsx` | `/dashboard/approvals/field-issues/[id]` |
| `apps/web/src/app/(authed)/dashboard/approvals/field-issues/history/page.tsx` | `/dashboard/approvals/field-issues/history` |

#### A.2.2 QuickBooks Conflict Surface — `apps/web/src/features/quickbooks-conflict/`

| File | Purpose |
|:---|:---|
| `components/QbConflictQueue.tsx` | Paginated table; columns: Entity, Type pill, Pilot change summary, QB change summary, Detail deep-link, Resolve button; default sort by financial impact (invoice > quote > customer/expense), then detection time |
| `components/QbConflictRow.tsx` | Single row; entity type pill (`Customer` / `Quote` / `Invoice` / `Expense`); `<ExpiryCountdownBadge>` if pre-warning active |
| `components/QbConflictFilterBar.tsx` | Entity-type multi-select pills with counts; Master filter pills (`Pilot is master` / `QB is master` / `User choice`) |
| `components/QbConflictDetail.tsx` | Page shell; composes `<IntegrationConflictResolver integration="quickbooks" masterDirection={entityMasterDirection}>` + `<InvoiceFinancialDeltaCallout>` via `renderDomainSpecificFields` for invoice type |
| `components/QbConflictEmptyState.tsx` | "No QuickBooks conflicts. Your data is in sync." + last sync time + expandable sync activity log |
| `hooks/useQbConflicts.ts` | TanStack Query list hook; `GET /api/v1/integrations/quickbooks/conflicts`; cursor-paginated |
| `hooks/useQbConflictDetail.ts` | TanStack Query detail hook; `GET /api/v1/integrations/quickbooks/conflicts/{id}` |
| `hooks/useResolveQbConflict.ts` | Mutation hook; composes `useStalenessRetry`; handles auto-recovery 409 scenario |
| `hooks/useQbConflictsSse.ts` | Composes `useSseChannel`; invalidates QB conflicts query on SSE events |
| `hooks/normalizeQbFieldDiffs.ts` | Maps BE `field_diffs` from A49 payload to `DiffField[]` for `<DiffView variant="qb-entity">` |
| `mocks/qbConflictFixtures.ts` | Typed fixture data: one fixture per entity type; invoice fixture includes financial_delta_cents + tax_period_warning |

**Page route components** (App Router):

| File | Route |
|:---|:---|
| `apps/web/src/app/(authed)/settings/integrations/quickbooks/conflicts/page.tsx` | `/settings/integrations/quickbooks/conflicts` |
| `apps/web/src/app/(authed)/settings/integrations/quickbooks/conflicts/[id]/page.tsx` | `/settings/integrations/quickbooks/conflicts/[id]` |

---

### A.3 New Mobile Feature Components

#### A.3.1 Background Sync Status Row — `apps/mobile/features/offline-sync/`

| File | Purpose |
|:---|:---|
| `components/BackgroundSyncStatusRow.tsx` | Status indicator row at top of `<SyncQueueDrawer>`. Six states per spec Decision 5. Taps deep-link to sync settings. |
| `hooks/useBackgroundSyncStatus.ts` | Reads last background sync attempt from `SyncOrchestrator` state + local AsyncStorage telemetry. Returns `{ state, lastAttemptAt, itemsSynced, retryCount }`. |

**Existing component modified**:
- `components/SyncQueueDrawer.tsx` — add `<BackgroundSyncStatusRow>` above the four queue sections.

#### A.3.2 Push Notification Loop Closure — `apps/mobile/features/offline-sync/`

| File | Purpose |
|:---|:---|
| `notifications/escalationResolutionHandler.ts` | Expo Notifications push handler for `escalation_resolved` silent push type. Triggers `SyncOrchestrator.pull()`, invalidates TanStack Query cache for escalation list. |
| `components/EscalationResolutionOutcome.tsx` | Terminal state display for a resolved `<SyncQueueItem>` — renders the three resolution outcome states with correct copy per spec Decision 8. |

#### A.3.3 Mobile Owner Field Issues Status Row

| File | Purpose |
|:---|:---|
| `apps/mobile/features/owner-tab/components/FieldIssuesSyncStatusSection.tsx` | Wires `useFieldIssuesStatus()` to `<FieldIssuesSyncStatusRow>`; placed below Calendar sync row on Owner tab |
| `apps/mobile/features/owner-tab/hooks/useFieldIssuesStatus.ts` | TanStack Query; `GET /api/v1/owner/field-issues/summary`; 60s staleTime; returns `{ pendingCount }` |

**Existing route modified**:
- `apps/mobile/app/(tabs)/owner.tsx` — add `<FieldIssuesSyncStatusSection>` below `<CalendarSyncStatusSection>` (FE-B8)

---

### A.4 New Routes

| Route | File | Auth | Role Gate | Notes |
|:---|:---|:---:|:---|:---|
| `/dashboard/approvals/field-issues` | `apps/web/src/app/(authed)/dashboard/approvals/field-issues/page.tsx` | Required | `owner` / `accountant` via `<RoleGate>` | Tab 2 on Approvals shell; count badge on tab label |
| `/dashboard/approvals/field-issues/[id]` | `...field-issues/[id]/page.tsx` | Required | Same; 404 if escalation not found | Modal-feeling but URL-routed; bookmarkable |
| `/dashboard/approvals/field-issues/history` | `...field-issues/history/page.tsx` | Required | Same | Full archive with tech / date / operation / outcome filters |
| `/settings/integrations/quickbooks/conflicts` | `apps/web/src/app/(authed)/settings/integrations/quickbooks/conflicts/page.tsx` | Required | `integrations.manage` | Fourth tab on existing QB integration page |
| `/settings/integrations/quickbooks/conflicts/[id]` | `...conflicts/[id]/page.tsx` | Required | Same | Redirect 404 if not authorized |

---

## B — Execution Order

| Step | Item | Rationale |
|:---:|:---|:---|
| 1 | **MSW handlers for all new endpoints** (field issues + QB conflicts + background sync summary) | All surface work requires mocked backends. Write fixtures and MSW before any component. |
| 2 | **`<IntegrationConflictResolver>` extension** — add `masterDirection` optional prop | Shared component change must land first; unblocks both QB detail and field issue detail surfaces. |
| 3 | **`<InvoiceFinancialDeltaCallout>` in `packages/ui/`** | Required by QB detail before QB detail surface can render invoice conflicts. |
| 4 | **`<FieldIssuesSyncStatusRow>` + `<FieldIssuesSyncStatusSection>` in `packages/ui/` and mobile** | Shared component; establishes the field issues owner-tab pattern. |
| 5 | **Field Issues queue + detail (web)** — items A.2.1 fully (queue → detail → per-field picker → resolve → loop closure) | Tier 1 #1 deliverable. Build the full flow end-to-end before QB work. |
| 6 | **QB Conflict queue + detail (web)** — items A.2.2 fully (queue → detail → resolve + invoice callout) | Tier 1 #2 deliverable; inherits from step 2/3/FE-B8. |
| 7 | **Background sync status row in mobile sync queue drawer** — items A.3.1 | Tier 1 #3 deliverable (UI slice). Narrow scope — status observer only. |
| 8 | **Push notification loop closure** — `escalationResolutionHandler` + terminal state rendering | Closes the field issue round-trip. Depends on step 5 being complete. |

**Rationale summary**: MSW-first (Rule from methods doc). Shared component changes before surfaces that consume them. Tier 1 #1 before Tier 1 #2 because the field-issue pattern is simpler and validates that the IntegrationConflictResolver extension works correctly before QB's added complexity.

---

## C — API Contracts

### C.1 `GET /api/v1/owner/field-issues`

**TanStack Query key**: `['field-issues', { status, cursor, limit, operationType, activeTechsOnly }]`
**Cache**: 30s staleTime; refetchOnWindowFocus
**Hook**: `useFieldIssues(params)`

**Request** (query params):
```typescript
interface FieldIssuesParams {
  status?: 'pending' | 'auto_recovered' | 'stale' | 'all';  // default: 'pending'
  operation_type?: 'time_entry' | 'expense' | 'photo' | 'status_change' | 'loto';
  active_techs_only?: boolean;  // default: true
  cursor?: string;
  limit?: number;  // 1–100, default: 20
}
```

**Response** (typed from A47 `FieldIssueListResponse`):
```typescript
interface FieldIssuesResponse {
  issues: FieldIssueQueueItem[];
  next_cursor: string | null;
  total_pending: number;
}
```

### C.2 `GET /api/v1/owner/field-issues/{id}`

**TanStack Query key**: `['field-issue', id]`
**Cache**: 0s staleTime; always refetch on focus
**Hook**: `useFieldIssueDetail(id)`

**Response** (typed from A47 `FieldIssueDetailResponse`):
```typescript
interface FieldIssueDetail {
  id: string;
  status: 'pending' | 'auto_recovered' | 'stale';
  operationType: 'time_entry' | 'expense' | 'photo' | 'status_change' | 'loto';
  techId: string;
  techName: string;
  techLastActiveAt: string | null;
  capturedAt: string;           // when tech captured the operation
  syncAttemptedAt: string;      // when it hit the conflict
  escalatedAt: string;
  explainerCopy: string;        // server-generated plain-language explanation — render verbatim
  techSnapshot: Record<string, unknown>;     // tech's local state at capture time
  serverSnapshot: Record<string, unknown>;   // server state at escalation time
  fieldDiffs: FieldIssueDiff[];  // server-computed diff between techSnapshot and serverSnapshot
  conflictType: 'modified_modified' | 'deleted_modified' | 'modified_deleted';
  resolution: FieldIssueResolution | null;
  resolvedByUserId: string | null;
  resolvedAt: string | null;
}
```

### C.3 `POST /api/v1/owner/field-issues/{id}/resolve`

**Hook**: `useResolveFieldIssue()`
**Composes**: `useStalenessRetry()`

**Request**:
```typescript
interface FieldIssueResolveRequest {
  resolution: FieldIssueResolution;
  per_field_selections?: PerFieldSelection[];  // only when resolution === 'per_field'
  expected_server_state_hash: string;          // staleness check token from detail response
}

type FieldIssueResolution = 'accept_tech' | 'accept_server' | 'per_field';

interface PerFieldSelection {
  field_name: string;
  chosen_side: 'tech' | 'server';
}
```

**409 Response** (three distinct subtypes per A48):
```typescript
type FieldIssue409Response =
  | { staleness_type: 'server_changed'; refreshed_issue: FieldIssueDetail }
  | { staleness_type: 'auto_recovered'; message: string }
  | { staleness_type: 'stale'; message: string };
```

**`useStalenessRetry` wiring**:
- `server_changed` → `onConflict` callback returns `refreshed_issue`; `StalenessRefreshDialog` renders updated diff
- `auto_recovered` → `onConflict` returns `null`; `NotificationBanner severity="success"` shown; navigate back to queue
- `stale` → `onConflict` returns `null`; `NotificationBanner severity="info"` shown; navigate back to queue

### C.4 `GET /api/v1/integrations/quickbooks/conflicts`

**TanStack Query key**: `['qb-conflicts', { status, entityType, cursor, limit }]`
**Cache**: 30s staleTime; refetchOnWindowFocus
**Hook**: `useQbConflicts(params)`

**Request** (query params):
```typescript
interface QbConflictsParams {
  status?: 'pending' | 'resolved' | 'all';
  entity_type?: 'customer' | 'quote' | 'invoice' | 'expense';
  cursor?: string;
  limit?: number;
}
```

**Response** (typed from A49 `QbConflictListResponse`):
```typescript
interface QbConflictsResponse {
  conflicts: QbConflictQueueItem[];
  next_cursor: string | null;
  total_pending: number;
}
```

### C.5 `GET /api/v1/integrations/quickbooks/conflicts/{id}`

**TanStack Query key**: `['qb-conflict', id]`
**Cache**: 0s staleTime
**Hook**: `useQbConflictDetail(id)`

**Response** (typed from A49 `QbConflictDetailResponse`):
```typescript
interface QbConflictDetail {
  id: string;
  entityType: 'customer' | 'quote' | 'invoice' | 'expense';
  entityId: string;
  entityDisplayName: string;
  conflictType: 'modified_modified' | 'deleted_modified' | 'modified_deleted';
  masterDirection: 'pilot' | 'external';   // pre-computed by backend per entity type
  pilotModifiedAt: string;
  externalModifiedAt: string;
  pilotModifiedByUserId: string | null;
  pilotModifiedByName: string | null;
  fieldDiffs: QbFieldDiff[];
  // Invoice-specific (null for non-invoice types):
  financialDeltaCents: number | null;
  pilotAmountCents: number | null;
  qbAmountCents: number | null;
  arImpactDescription: string | null;
  taxPeriodWarning: string | null;
  qbTransactionUrl: string | null;
  resolution: QbResolution | null;
  resolvedAt: string | null;
  autoResolvedStale: boolean;
}
```

### C.6 `POST /api/v1/integrations/quickbooks/conflicts/{id}/resolve`

**Hook**: `useResolveQbConflict()`
**Composes**: `useStalenessRetry()`

**Request**:
```typescript
interface QbConflictResolveRequest {
  resolution: QbResolution;
  per_field_selections?: PerFieldSelection[];
  expected_pilot_modified_at: string;
  expected_external_modified_at: string;
}

type QbResolution = 'accept_local' | 'accept_remote' | 'per_field';
```

**Note**: Voice resolution is disallowed for QB conflicts. No `resolve_qb_*` voice intent exists. The UI surfaces no voice confirmation UI for QB conflicts.

### C.7 `GET /api/v1/owner/field-issues/summary` (mobile)

**TanStack Query key**: `['field-issues-summary']`
**Cache**: 60s staleTime
**Hook**: `useFieldIssuesStatus()`

**Response**:
```typescript
interface FieldIssuesSummary {
  pending_count: number;
}
```

### C.8 SSE Channels

| Surface | Channel path | Events | Handler |
|:---|:---|:---|:---|
| Field Issues queue | `/api/v1/owner/field-issues/stream` | `escalation_created`, `escalation_resolved`, `escalation_auto_recovered` | Invalidate `['field-issues']` |
| QB Conflicts queue | `/api/v1/integrations/quickbooks/conflicts/stream` | `conflict_detected`, `conflict_resolved`, `conflict_auto_recovered` | Invalidate `['qb-conflicts']` |

Both channels use `useSseChannel` with `fallbackToPollingMs: 60_000`.

---

## D — State Management

### D.1 `FieldIssuesQueuePage`

| State | Location | Notes |
|:---|:---|:---|
| Issues list | TanStack Query `['field-issues', params]` | Cursor-paginated |
| Status filter | `useState<'pending' \| 'auto_recovered' \| 'stale' \| 'all'>('pending')` | Local; drives query |
| Operation type filter | `useState<string[]>([])` | Local multi-select |
| Active techs only | `useState<boolean>(true)` | Local |
| SSE connection | `useFieldIssuesSse` internal | Auto-invalidates list |
| Cursor | `useState<string \| null>(null)` | Reset on filter change |

### D.2 `FieldIssueDetailPage`

| State | Location | Notes |
|:---|:---|:---|
| Issue detail | TanStack Query `['field-issue', id]` | 0s staleTime |
| Staleness dialog | `useStalenessRetry` internal | Three 409 subtypes handled differently |
| Per-field picker open | `useState<boolean>(false)` | Local; toggled by "Choose field by field →" button |
| Per-field selections | `useState<PerFieldSelection[]>([])` | Local; passed to resolve mutation |
| Voice confirm state | `useState<VoiceFieldIssueResolutionState>({ phase: 'idle' })` | Scoped to detail page lifecycle |

### D.3 Voice Confirm-as-Turn State Machine (Field Issues only; NOT QB)

```typescript
type VoiceFieldIssueResolutionState =
  | { phase: 'idle' }
  | { phase: 'identifying'; issueIdentifier: string }
  | { phase: 'confirming'; issueId: string; chosenResolution: FieldIssueResolution; readbackText: string }
  | { phase: 'committed'; issueId: string; resolution: FieldIssueResolution }
  | { phase: 'cancelled'; reason: 'user_cancelled' | 'staleness_detected' | 'deletion_redirect' | 'permission_revoked_redirect' };
```

**QB conflicts have NO voice resolve state machine** — all QB resolution routes to web; no confirm-as-turn UI exists for QB.

### D.4 `QbConflictQueuePage`

| State | Location | Notes |
|:---|:---|:---|
| Conflicts list | TanStack Query `['qb-conflicts', params]` | Cursor-paginated |
| Entity type filter | `useState<string[]>([])` | Local multi-select |
| Master filter | `useState<string \| null>(null)` | Local |
| SSE connection | `useQbConflictsSse` internal | — |

### D.5 `QbConflictDetailPage`

| State | Location | Notes |
|:---|:---|:---|
| Conflict detail | TanStack Query `['qb-conflict', id]` | 0s staleTime |
| Staleness dialog | `useStalenessRetry` internal | Auto-recovered 409 navigates to queue |
| Per-field picker open | `useState<boolean>(false)` | Same as field issues |
| Per-field selections | `useState<PerFieldSelection[]>([])` | — |

### D.6 Background Sync Status Row State

```typescript
interface BackgroundSyncStatus {
  state: 'recent_success' | 'recent_success_no_work' | 'recent_failed' | 'disabled' | 'never_run' | 'no_permission';
  lastAttemptAt: Date | null;
  itemsSynced: number | null;
  retryCount: number;
}
```

Derived from `SyncOrchestrator` internal state + `AsyncStorage` key `@pilot/bg_sync_last_attempt`. Not in TanStack Query — local device state only.

### D.7 SSE → Cache-Invalidation Flow (both surfaces)

```
BE emits SSE event (escalation_created / conflict_detected)
  → useSseChannel onMessage fires
  → queryClient.invalidateQueries({ queryKey: ['field-issues'] }) OR ['qb-conflicts']
  → TanStack Query refetch triggered
  → Queue re-renders with new row
  → Owner tab badge count re-fetches via useFieldIssuesStatus / useQbStatus
```

---

## E — Error States

### E.1 409 Staleness `server_changed` — Field Issues

**Trigger**: Owner clicks resolve; server state changed since escalation creation.

**User sees**: `StalenessRefreshDialog` opens with refreshed diff. Banner: `"This issue has been updated. Review and pick again."` Token class: `text-alert-600`.

**Component**: `StalenessRefreshDialog` from `packages/ui/src/staleness-refresh-dialog/`

### E.2 409 Staleness `auto_recovered` — Field Issues

**Trigger**: Conflict resolved itself before owner triaged.

**User sees**: Dialog does NOT open. `NotificationBanner severity="success"`: `"This issue auto-recovered while you were viewing it. [Tech]'s data has been committed automatically."` → navigates back to queue.

**Component**: `NotificationBanner` from `packages/ui/src/notification-banner/`
**Token**: `bg-margin-50 border-margin-200 text-margin-700`

### E.3 409 Staleness `stale` — Field Issues

**Trigger**: Tech force-discarded their pending sync (Phase 2 stub; queue reset path).

**User sees**: `NotificationBanner severity="info"`: `"[Tech] discarded this captured data from their device. There's nothing to commit. Closing this issue."` → navigate to queue.

**Token**: `bg-neutral-50 border-neutral-200 text-neutral-700`

### E.4 Deletion Conflict — Voice Refusal

**Trigger**: Voice `resolve_field_issue` on a `deleted_modified` or `modified_deleted` type.

**User sees**: AI says `"That's a deletion conflict — it needs the diff view to be safe. I'll open it on web."` Push notification fires with deep-link.

**On deep-link arrival** (`?reason=voice_deletion_redirect`): `NotificationBanner severity="info"`: `"Your voice session routed here — please choose how to handle this deletion."`

### E.5 Permission-Revoked Capture — Voice Refusal

**Trigger**: Field issue type `permission_revoked`; voice attempts `resolve_field_issue`.

**User sees**: AI says `"That's a permission-change issue — I'll open it on web for you to review before deciding."` Push notification fires.

**On deep-link arrival** (`?reason=voice_permission_redirect`): `NotificationBanner severity="warning"`: `"Voice resolution paused for this issue — review the captured data before deciding."`

### E.6 QB Voice Resolution Attempt

**Trigger**: User voice-attempts to resolve a QB conflict (`resolve_qb_*` intent — which does not exist in the registry).

**User sees**: AI responds: `"QuickBooks conflicts need the diff view to be safe — opening on web."` Push notification fires. No state machine transition (QB has no voice resolve path).

### E.7 Auto-Recovery — QB Conflict

**Trigger**: QB sync task processed a state-restoration between detection and owner viewing.

**User sees**: Queue-level `NotificationBanner severity="success"` toast: `"This conflict resolved itself before you got to it."` Conflict removed from queue.

### E.8 Invoice Tax-Period Warning

**Trigger**: `qbConflict.taxPeriodWarning` is non-null.

**User sees**: Amber banner above the two-column diff: `"⚠ This invoice spans tax period [period]. Resolution may affect filed returns. Consider consulting your bookkeeper."` Renders inside `<InvoiceFinancialDeltaCallout>`.

**Token**: `bg-alert-50 border-alert-200 text-alert-600`

### E.9 Background Sync Permission Not Granted

**Trigger**: `BackgroundSyncStatus.state === 'no_permission'`.

**User sees**: Row in sync queue drawer shows amber dot + `"Background sync limited · Enable notifications for best performance"` + deep-link to OS notification settings.

**Token**: `text-alert-600`; dot `bg-alert-400`

### E.10 Empty States

| Surface | Trigger | Copy |
|:---|:---|:---|
| Field Issues queue | `issues.length === 0` | "No field issues to resolve. Your team's captures are all syncing cleanly." + expandable recent history |
| QB Conflicts queue | `conflicts.length === 0` | "No QuickBooks conflicts. Your data is in sync." + last sync time + expandable sync log |

**Tokens**: `text-margin-600` for healthy confirmation line; `text-neutral-600` for timestamps.

---

## F — TypeScript Interfaces

### F.1 `IntegrationConflictResolverProps` — FE-B8 Locked + FE-B9 Extension

```typescript
/**
 * FE-B8 LOCKED INTERFACE — do not modify existing props.
 * FE-B9 ADDITIVE EXTENSION: adds masterDirection (optional, default 'pilot').
 *
 * ⚠️ Interface locked after FE-B8. FE-B9 may add OPTIONAL props only.
 * Location: packages/ui/src/integration-conflict-resolver/IntegrationConflictResolver.tsx
 */
export interface IntegrationConflictResolverProps<
  T extends CalendarConflictDetail | QbConflictDetail | FieldIssueDetail = CalendarConflictDetail,
> {
  // ─── FE-B8 LOCKED PROPS (unchanged) ─────────────────────────────────────
  integration: 'calendar' | 'quickbooks';
  conflict: T;
  onResolve: (resolution: string) => void;
  isResolving: boolean;
  onResolveLater: () => void;
  providerDisplayName?: string;
  renderDomainSpecificFields?: (conflict: T) => React.ReactNode;
  daysUntilExpiry?: number | null;
  testID?: string;

  // ─── FE-B9 ADDITIVE OPTIONAL PROPS ──────────────────────────────────────
  /**
   * Column ordering. 'pilot' = Pilot on left (default, preserves FE-B8 behavior).
   * 'external' = external system on left (used for QB Invoice conflicts where QB is master).
   */
  masterDirection?: 'pilot' | 'external';

  /**
   * Whether per-field resolution is supported for this conflict type.
   * Default: false (preserves FE-B8 calendar behavior where per-field is not supported).
   * Set true for field issues and QB conflicts.
   */
  supportsPerFieldResolution?: boolean;

  /**
   * Per-field selections state — passed down when supportsPerFieldResolution=true.
   */
  perFieldSelections?: PerFieldSelection[];
  onPerFieldSelectionChange?: (selections: PerFieldSelection[]) => void;
}
```

### F.2 `FieldIssueQueueItem`

```typescript
export interface FieldIssueQueueItem {
  id: string;
  status: 'pending' | 'auto_recovered' | 'stale';
  operationType: 'time_entry' | 'expense' | 'photo' | 'status_change' | 'loto';
  techId: string;
  techName: string;
  capturedAt: string;
  escalatedAt: string;
  explainerSummary: string;    // short version of explainerCopy for queue row
  conflictType: 'modified_modified' | 'deleted_modified' | 'modified_deleted';
}
```

### F.3 `QbConflictQueueItem`

```typescript
export interface QbConflictQueueItem {
  id: string;
  entityType: 'customer' | 'quote' | 'invoice' | 'expense';
  entityId: string;
  entityDisplayName: string;
  conflictType: 'modified_modified' | 'deleted_modified' | 'modified_deleted';
  masterDirection: 'pilot' | 'external';
  pilotModifiedAt: string;
  externalModifiedAt: string;
  // Invoice-only: non-null for invoice entity type
  financialDeltaCents: number | null;
  resolution: QbResolution | null;
  detectedAt: string;
  daysUntilExpiry: number | null;
}

export type QbResolution = 'accept_local' | 'accept_remote' | 'per_field';
```

### F.4 `InvoiceFinancialDeltaCalloutProps`

```typescript
/**
 * Rendered via renderDomainSpecificFields slot for invoice entity type only.
 * Location: packages/ui/src/invoice-financial-delta/InvoiceFinancialDeltaCallout.tsx
 */
export interface InvoiceFinancialDeltaCalloutProps {
  pilotAmountCents: number;
  qbAmountCents: number;
  financialDeltaCents: number;                // positive = QB higher; negative = Pilot higher
  arImpactDescription: string;
  taxPeriodWarning: string | null;            // null → no tax-period banner rendered
  qbTransactionUrl: string | null;            // null → no QB deep-link rendered
}
```

### F.5 `FieldIssuesSyncStatusRowProps`

```typescript
/**
 * Location: packages/ui/src/field-issues-status/FieldIssuesSyncStatusRow.tsx
 * Mobile only (Gluestack primitives)
 */
export interface FieldIssuesSyncStatusRowProps {
  pendingCount: number;                       // 0 = healthy/no-pending state
  isLoading?: boolean;
  onPress: () => void;                        // deep-link to web field-issues URL
  webAppBaseUrl: string;                      // from config — never hardcoded
}
```

### F.6 `BackgroundSyncStatusRowProps`

```typescript
/**
 * Location: apps/mobile/features/offline-sync/components/BackgroundSyncStatusRow.tsx
 */
export interface BackgroundSyncStatusRowProps {
  status: BackgroundSyncStatus;
  onPress: () => void;                        // deep-link to sync settings
}

export interface BackgroundSyncStatus {
  state:
    | 'recent_success'
    | 'recent_success_no_work'
    | 'recent_failed'
    | 'disabled'
    | 'never_run'
    | 'no_permission';
  lastAttemptAt: Date | null;
  itemsSynced: number | null;
  retryCount: number;
}
```

### F.7 `PerFieldSelection`

```typescript
/**
 * Shared type — used in both field issue and QB conflict per-field resolution.
 * Export from packages/ui/src/index.ts.
 */
export interface PerFieldSelection {
  fieldName: string;
  chosenSide: 'tech' | 'server';    // field issue context
  // OR
  // chosenSide: 'pilot' | 'external'; // QB conflict context — same shape, different semantics
}
```

---

## G — Test Plan

### G.1 Unit Tests (target: 70+)

**`packages/ui/src/integration-conflict-resolver/`**

| Test | File |
|:---|:---|
| `masterDirection='external'` renders external system column on left | `IntegrationConflictResolver.test.tsx` |
| `masterDirection='pilot'` (default) renders Pilot on left — existing FE-B8 behavior preserved | `IntegrationConflictResolver.test.tsx` |
| `supportsPerFieldResolution=true` shows "Choose field by field →" button | `IntegrationConflictResolver.test.tsx` |
| `supportsPerFieldResolution=false` (default) hides per-field button | `IntegrationConflictResolver.test.tsx` |
| Per-field picker expands on "Choose field by field →" click | `IntegrationConflictResolver.test.tsx` |
| Per-field picker sends correct `PerFieldSelection[]` via `onPerFieldSelectionChange` | `IntegrationConflictResolver.test.tsx` |
| FE-B8 usage unaffected: `masterDirection` absent → Pilot left; per-field button absent | `IntegrationConflictResolver.regression.test.tsx` |

**`packages/ui/src/invoice-financial-delta/`**

| Test | File |
|:---|:---|
| Renders positive delta `financialDeltaCents > 0` as "QB higher" | `InvoiceFinancialDeltaCallout.test.tsx` |
| Renders negative delta as "Pilot higher" | `InvoiceFinancialDeltaCallout.test.tsx` |
| `taxPeriodWarning` non-null → amber tax-period banner renders | `InvoiceFinancialDeltaCallout.test.tsx` |
| `taxPeriodWarning` null → no amber banner | `InvoiceFinancialDeltaCallout.test.tsx` |
| `qbTransactionUrl` non-null → QB deep-link renders | `InvoiceFinancialDeltaCallout.test.tsx` |
| `qbTransactionUrl` null → no QB deep-link | `InvoiceFinancialDeltaCallout.test.tsx` |

**`packages/ui/src/field-issues-status/`**

| Test | File |
|:---|:---|
| `pendingCount=0` renders green dot + "None pending" | `FieldIssuesSyncStatusRow.test.tsx` |
| `pendingCount > 0` renders amber dot + count + "Resolve on web →" | `FieldIssuesSyncStatusRow.test.tsx` |
| `isLoading=true` renders loading skeleton | `FieldIssuesSyncStatusRow.test.tsx` |
| `onPress` called with correct web URL on tap | `FieldIssuesSyncStatusRow.test.tsx` |
| Deep-link URL is from `webAppBaseUrl` config, not hardcoded | `FieldIssuesSyncStatusRow.test.tsx` |

**`apps/web/src/features/field-issues/`**

| Test | File |
|:---|:---|
| `FieldIssueRow` renders tech name, operation pill, status pill, and Resolve button | `components/FieldIssueRow.test.tsx` |
| `FieldIssueRow` renders `Pending` / `Auto-recovered` / `Stale` status pills with correct tokens | `components/FieldIssueRow.test.tsx` |
| `FieldIssueFilterBar` active-techs chip is on by default | `components/FieldIssueFilterBar.test.tsx` |
| `FieldIssueFilterBar` operation-type multi-select emits correct filter value | `components/FieldIssueFilterBar.test.tsx` |
| `EscalationContextHeader` renders explainer copy verbatim from server | `components/EscalationContextHeader.test.tsx` |
| `EscalationContextHeader` tech identity row shows last-active time | `components/EscalationContextHeader.test.tsx` |
| `FieldIssueHistoryPanel` shows last-30 resolved issues when expanded | `components/FieldIssueHistoryPanel.test.tsx` |
| `FieldIssueEmptyState` renders correct copy | `components/FieldIssueEmptyState.test.tsx` |
| `useFieldIssues` constructs correct query key with all filter params | `hooks/useFieldIssues.test.ts` |
| `useResolveFieldIssue` calls `useStalenessRetry.mutate` with correct payload | `hooks/useResolveFieldIssue.test.ts` |
| `useResolveFieldIssue` routes `auto_recovered` 409 to success banner (no dialog) | `hooks/useResolveFieldIssue.test.ts` |
| `useResolveFieldIssue` routes `stale` 409 to info banner (no dialog) | `hooks/useResolveFieldIssue.test.ts` |
| `useResolveFieldIssue` routes `server_changed` 409 to `StalenessRefreshDialog` | `hooks/useResolveFieldIssue.test.ts` |

**`apps/web/src/features/quickbooks-conflict/`**

| Test | File |
|:---|:---|
| `QbConflictRow` renders entity type pill with correct label for all 4 entity types | `components/QbConflictRow.test.tsx` |
| `QbConflictRow` renders `ExpiryCountdownBadge` when `daysUntilExpiry <= 7` | `components/QbConflictRow.test.tsx` |
| `QbConflictFilterBar` entity-type pills show count in parentheses | `components/QbConflictFilterBar.test.tsx` |
| Invoice detail renders `<InvoiceFinancialDeltaCallout>` | `components/QbConflictDetail.test.tsx` |
| Customer detail does NOT render `<InvoiceFinancialDeltaCallout>` | `components/QbConflictDetail.test.tsx` |
| Invoice conflict detail: QB is master → `masterDirection='external'` → QB on left | `components/QbConflictDetail.test.tsx` |
| Quote conflict detail: Pilot is master → `masterDirection='pilot'` → Pilot on left | `components/QbConflictDetail.test.tsx` |
| `normalizeQbFieldDiffs` maps `pilot_value` → `baseValue`, `external_value` → `modifiedValue` | `hooks/normalizeQbFieldDiffs.test.ts` |
| `useQbConflicts` constructs correct query key with entity_type param | `hooks/useQbConflicts.test.ts` |

**`apps/mobile/features/offline-sync/`**

| Test | File |
|:---|:---|
| `BackgroundSyncStatusRow` renders "Last background sync: X min ago (N items)" for `recent_success` | `components/BackgroundSyncStatusRow.test.tsx` |
| `BackgroundSyncStatusRow` renders amber state for `recent_failed` | `components/BackgroundSyncStatusRow.test.tsx` |
| `BackgroundSyncStatusRow` renders "Background sync off · Items will sync when you open the app" for `disabled` | `components/BackgroundSyncStatusRow.test.tsx` |
| `BackgroundSyncStatusRow` renders amber + OS-settings link for `no_permission` | `components/BackgroundSyncStatusRow.test.tsx` |
| `BackgroundSyncStatusRow` renders "Background sync ready" for `never_run` | `components/BackgroundSyncStatusRow.test.tsx` |
| `EscalationResolutionOutcome` renders `resolved_in_favor_of_tech` state correctly | `components/EscalationResolutionOutcome.test.tsx` |
| `EscalationResolutionOutcome` renders `resolved_in_favor_of_server` state with correct dismissal copy | `components/EscalationResolutionOutcome.test.tsx` |
| `EscalationResolutionOutcome` renders `resolved_with_action` state with job-restored context | `components/EscalationResolutionOutcome.test.tsx` |

### G.2 Integration Tests (target: 16+)

**Location**: `apps/{web,mobile}/__tests__/batch_fe_b9/`

| Test | File |
|:---|:---|
| Field issue full resolve (modified_modified): queue → detail → "Use Tech's Version" → success → navigate to queue | `field-issue-resolve.integration.test.tsx` |
| Field issue deletion conflict: deletion verb buttons render; standard diff hidden | `field-issue-deletion.integration.test.tsx` |
| Field issue per-field resolve: picker expands → select fields → "Commit field selections" submits `PerFieldSelection[]` | `field-issue-per-field.integration.test.tsx` |
| Field issue 409 `server_changed`: StalenessDialog opens; retry succeeds | `field-issue-staleness.integration.test.tsx` |
| Field issue 409 `auto_recovered`: success banner shows; navigates to queue | `field-issue-auto-recovered.integration.test.tsx` |
| Field issue SSE: new escalation event → queue row appears | `field-issue-sse.integration.test.tsx` |
| QB conflict (invoice): renders InvoiceFinancialDeltaCallout with delta + tax warning | `qb-invoice-conflict.integration.test.tsx` |
| QB conflict full resolve (customer, per-field): per-field selection → submit | `qb-conflict-per-field.integration.test.tsx` |
| QB conflict auto-recovery: queue-level success toast | `qb-conflict-auto-recovery.integration.test.tsx` |
| QB conflict voice attempt: voice returns "route to web" message | `qb-conflict-voice-blocked.integration.test.tsx` |
| QB conflict RBAC: non-`integrations.manage` user sees EmptyState | `qb-conflict-rbac.integration.test.tsx` |
| Background sync row: `recent_success` state renders with correct copy | `background-sync-status.integration.test.tsx` |
| Background sync row: `no_permission` state renders amber + OS deep-link | `background-sync-no-permission.integration.test.tsx` |
| Push loop closure: `escalation_resolved` push → `SyncOrchestrator.pull()` called → queue item transitions to terminal state | `push-loop-closure.integration.test.tsx` |
| Owner tab field issues row: `pendingCount=3` renders amber + "3 pending" | `owner-tab-field-issues.integration.test.tsx` |
| Owner tab field issues row: deep-link navigates to correct web URL | `owner-tab-field-issues-deeplink.integration.test.tsx` |

**MSW handlers required** (new files):
- `apps/web/src/mocks/handlers/fieldIssuesHandlers.ts`
  - `GET /api/v1/owner/field-issues` (pending list, empty state, active-techs filter variants)
  - `GET /api/v1/owner/field-issues/:id` (modified_modified, deleted_modified, permission_revoked)
  - `POST /api/v1/owner/field-issues/:id/resolve` (success, 409-server_changed, 409-auto_recovered, 409-stale)
  - `GET /api/v1/owner/field-issues/stream` (SSE)
  - `GET /api/v1/owner/field-issues/summary` (mobile)
- `apps/web/src/mocks/handlers/qbConflictHandlers.ts`
  - `GET /api/v1/integrations/quickbooks/conflicts` (one fixture per entity type)
  - `GET /api/v1/integrations/quickbooks/conflicts/:id` (customer, quote, invoice-with-tax-warning, expense)
  - `POST /api/v1/integrations/quickbooks/conflicts/:id/resolve` (success, 409-auto-recovery)
  - `GET /api/v1/integrations/quickbooks/conflicts/stream` (SSE)

**Required fixtures**:
- `fieldIssuesFixtures.ts`: time_entry `modified_modified`; expense `deleted_modified`; time_entry `permission_revoked`; list of 3 for queue; 409 `server_changed` + `auto_recovered` + `stale` response bodies
- `qbConflictFixtures.ts`: customer `modified_modified`; quote `modified_modified`; invoice `modified_modified` with `financialDeltaCents=3750`, `taxPeriodWarning="Q1 2026"`, `qbTransactionUrl`; expense `modified_modified`; 409 auto-recovery body

### G.3 E2E Tests (target: 4+)

**Location**: `e2e/web/batch_fe_b9/` and `e2e/mobile/batch_fe_b9/`

| Test | File |
|:---|:---|
| Full field issue round-trip: web resolves → mobile tech receives push → queue item shows terminal state | `field-issue-round-trip.e2e.spec.ts` |
| QB invoice conflict resolution against dev QuickBooks sandbox: conflict appears → resolve → verify QB entity updated | `qb-invoice-resolve.e2e.spec.ts` |
| Cross-device escalation: mobile creates escalation (offline capture + force-escalation) → web resolves → mobile confirms | `cross-device-escalation.e2e.spec.ts` (requires two-device or simulator pair) |
| Background sync: force-queue items → kill app → wait → reopen → confirm items synced in background | `background-sync.e2e.test.ts` (mobile Maestro) |

---

## H — Token Audit

Every color, spacing, and typography value traces to a token from `packages/ui/src/tokens.ts`. No hex values or raw pixel values in component code.

### H.1 Color Tokens

| Usage | Tailwind class | Token | Notes |
|:---|:---|:---|:---|
| Field issue "Pending" status pill | `bg-alert-100 text-alert-700` | `colors.alert[100]`, `colors.alert[700]` | Amber — awaiting action |
| Field issue "Auto-recovered" status pill | `bg-margin-100 text-margin-700` | `colors.margin[100]`, `colors.margin[700]` | Green — resolved positively |
| Field issue "Stale" status pill | `bg-neutral-100 text-neutral-600` | `colors.neutral[100]`, `colors.neutral[600]` | Neutral — dismissed |
| QB entity type "Invoice" pill | `bg-brand-100 text-brand-700` | `colors.brand[100]`, `colors.brand[700]` | Brand indigo — highest-stakes entity |
| QB entity type "Customer" / "Quote" / "Expense" pills | `bg-neutral-100 text-neutral-700` | `colors.neutral[100]`, `colors.neutral[700]` | — |
| Invoice financial delta callout background | `bg-alert-50 border-alert-200` | `colors.alert[50]`, `colors.alert[200]` | — |
| Invoice tax-period warning banner | `bg-alert-50 border-alert-200 text-alert-700` | above | Amber warning |
| "Use Tech's version" primary button (field issues) | `bg-brand-600 hover:bg-brand-700 text-white` | `colors.brand[600]`, `colors.brand[700]` | — |
| "Use server version" secondary button | `border-brand-600 text-brand-600 hover:bg-brand-50` | `colors.brand[600]`, `colors.brand[50]` | — |
| Deletion conflict destructive button | `border-fault-200 text-fault-700 hover:bg-fault-50` | `colors.fault[200]`, `colors.fault[700]`, `colors.fault[50]` | — |
| QB master column (left, master side) header | `bg-brand-50 border-b border-brand-200` | `colors.brand[50]`, `colors.brand[200]` | Subtle highlight for master column |
| Auto-recovery success banner | `bg-margin-50 border-margin-200 text-margin-700` | `colors.margin[50]`, `colors.margin[200]`, `colors.margin[700]` | Green success |
| Stale-info banner | `bg-neutral-50 border-neutral-200 text-neutral-700` | `colors.neutral[50]`, `colors.neutral[200]`, `colors.neutral[700]` | Neutral info |
| Background sync healthy dot | `bg-margin-400` | `colors.margin[400]` | — |
| Background sync disabled dot | `bg-neutral-400` | `colors.neutral[400]` | — |
| Background sync failed dot | `bg-alert-400` | `colors.alert[400]` | Amber — degraded |
| Field issues owner tab healthy dot | `bg-margin-500` | `colors.margin[500]` | — |
| Field issues owner tab pending dot | `bg-alert-500` | `colors.alert[500]` | — |
| Empty state healthy text | `text-margin-600` | `colors.margin[600]` | — |
| Secondary / meta text | `text-neutral-600` | `colors.neutral[600]` | — |
| Page background | `bg-neutral-50` | `lightTheme.background.primary` | — |
| Card background | `bg-white` | `lightTheme.background.secondary` | — |

### H.2 Spacing Tokens

All `padding`, `margin`, `gap` values use Tailwind spacing scale from pilot preset only — no raw pixel values.

| Usage | Class | Token |
|:---|:---|:---|
| Queue row padding | `px-4 py-3` | `spacing[4]` / `spacing[3]` |
| Detail card padding | `p-6` | `spacing[6]` |
| Filter bar gap | `gap-2` | `spacing[2]` |
| Per-field picker row gap | `space-y-2` | `spacing[2]` |
| Callout internal padding | `p-4` | `spacing[4]` |
| Column header padding | `px-4 py-2` | `spacing[4]` / `spacing[2]` |

### H.3 Typography Tokens

| Usage | Class | Token |
|:---|:---|:---|
| Page heading | `text-h2 font-medium` | `fontSizes.h2`, `fontWeights.medium` |
| Queue entity label | `text-body font-medium` | `fontSizes.body`, `fontWeights.medium` |
| Explainer copy | `text-body` | `fontSizes.body` |
| Meta / timestamps | `text-caption` | `fontSizes.caption` |
| Financial delta amount | `text-body-lg font-semibold` | `fontSizes.bodyLg`, `fontWeights.semibold` |

### H.4 Token Gaps Flagged

No token gaps identified. All design values used in this batch trace to existing tokens in `tokens.ts`.

**Note on QB "master column" header tint**: uses `brand-50` / `brand-200` — these exist in the brand ramp. The tint is intentionally subtle (50-level background) to signal "this is the master side" without overwhelming the diff content.

---

## I — Downstream Contract Lock

### I.1 Interfaces Locked by FE-B9 (Consumed by FE-B15)

FE-B15 (In-Flight Sync Indicator Refinement) will audit all sync surfaces and unify the `<InFlightSyncIndicator>` API. FE-B9 must use the `surface="quickbooks"` prop value exactly on the QB conflicts page:

```typescript
<InFlightSyncIndicator
  surface="quickbooks"
  state={mapQbSyncState(qbStatus.connectionStatus)}
  pendingCount={qbStatus.pendingConflictsCount}
  lastSyncedAt={qbStatus.lastSuccessfulSyncAt ? new Date(qbStatus.lastSuccessfulSyncAt) : undefined}
  compact={false}
/>
```

FE-B15 will replace this inline usage with `useInFlightSyncStatus('quickbooks')`. No interface changes required at the component level — only the `surface="quickbooks"` string value must be correct.

Background sync surface: FE-B15 also audits `surface="background-sync"` if FE-B9 adds an in-flight indicator for the background sync row. Use `surface="background-sync"` if wired.

### I.2 Exports Locked by FE-B9

The following are added to `packages/ui/src/index.ts` and locked after FE-B9 ships:

| Export | From | FE-B10/11/15 usage |
|:---|:---|:---|
| `FieldIssuesSyncStatusRow` | `packages/ui/src/field-issues-status/` | FE-B15 (status row refinement) |
| `InvoiceFinancialDeltaCallout` | `packages/ui/src/invoice-financial-delta/` | Future: any integration with financial-delta diffs |
| `PerFieldSelection` (type) | `packages/ui/src/integration-conflict-resolver/types.ts` | FE-B11 settings surfaces that surface per-field conflict config |
| `BackgroundSyncStatus` (type) | `apps/mobile/features/offline-sync/` | FE-B11 (background sync settings UI extends this shape) |
| `VoiceFieldIssueResolutionState` (type) | `apps/web/src/features/field-issues/` | FE-B16 (help voice patterns may reference field issue resolution state) |

### I.3 IntegrationConflictResolver — Final Extension Note for Phase 2

After FE-B9, the `IntegrationConflictResolver` has been used for:
- `integration="calendar"` (FE-B8)
- `integration="quickbooks"` (FE-B9)

Phase 2 integrations (Salesforce, HubSpot, generic webhook) extend by:
1. Adding the new integration string to the `integration` union
2. Providing `providerDisplayName`
3. Passing domain-specific content via `renderDomainSpecificFields`

No other interface changes permitted. This is platform vocabulary; the two-column diff + staleness check + per-field picker pattern is the canonical integration conflict UI for all future integrations.

---

*This document is the complete handoff artifact for the Pilot React Engineer for FE-B9. All 7 design decisions are resolved. All TypeScript interfaces are complete with no `any` types. All token references use exact token names from `tokens.ts`. The engineer can execute FE-B9 without returning for architectural decisions.*
