# Pilot for Trades Design System — Pass 4, Tier 4 #12: In-Flight Sync Indicator with Pending Count

**Version**: 1.0
**Status**: Locked
**Date**: April 27, 2026
**Author**: Tom (Founder) with Claude
**Scope**: Refinement to Flow 3 Decision 11 (Calendar Sync Status Indicator), generalized as a platform pattern for all sync surfaces. Adds pending-count visibility to the previously-binary green/amber/red indicator. Smallest remaining Pass 4 surface.
**Resolves**: Pass 4 framework doc Tier 4 #12 ("dispatch board sync indicator amber-with-count refinement") · Tier 3 #8/#9 states catalog Cross-Domain F (extension of L3 background indicator)
**Depends On**: Pass 3 Flow 3 Decision 11 (Calendar Sync Status Indicator) · Pass 3 Flow 6 (Calendar conflict resolution) · Pass 4 Tier 1 #2 (QuickBooks sync) · Pass 4 Tier 1 #3 (Background sync) · Tier 3 #8/#9 (L3 background indicator visual treatment) · `mvp-arch.md` §13.5 (calendar sync) · §5.4 (QuickBooks sync) · §15 (mobile offline operations)
**Backend additions**: A79 (pending-sync count exposure across sync surfaces)
**Deliverable shape**: Shape D (incremental addendum to existing spec) per Pass 4 framework doc

---

## Purpose

Flow 3 Decision 11 established a calendar sync status indicator with three states: green "synced," amber "syncing," red "sync error." The amber state was conceived as transient — visible only while a sync was actively running. In practice, this design has a gap that surfaces during operational use: between sync cycles the board may show stale data, and the green "synced" state implies "everything is current" which is only literally true at the moment of sync completion.

The refinement: surface the count of pending sync operations alongside the indicator state. Instead of binary "syncing or not," users see "Syncing 3 changes..." while in flight, and "Synced (no pending)" when at rest. The indicator now carries information about what's in flight, not just whether sync is active.

This refinement also generalizes beyond calendar sync. QuickBooks sync (Tier 1 #2), mobile-to-web data sync (Flow 7 + Tier 1 #1), and background sync (Tier 1 #3) all have the same operational concern. Tier 4 #12 establishes the **In-Flight Sync Indicator pattern** as platform vocabulary applied to all four sync surfaces.

The pattern earns a §16 entry as the platform's canonical sync-status visualization. Phase 2 surfaces with sync semantics inherit it by default.

## Strategic direction

### Visibility into in-flight work, not just sync state

The original three-state indicator answered "is sync running?" The refinement answers a more useful question: "what is sync doing?" When the owner sees "Syncing 3 changes..." they know the board state is actively transitioning and can wait. When they see "Synced · no pending," they know the displayed data is current as of the last sync cycle. This is operationally meaningful in a way the binary state isn't.

### Generalize first, apply specifically

The same operational concern applies across calendar, QuickBooks, mobile, and background sync. The pattern is one specification with four reference instances. Each surface inherits the pattern verbatim with surface-specific count semantics (calendar counts calendar events; QuickBooks counts entity changes; mobile counts queued offline operations; background counts data sync queue items).

Specifying the pattern once and applying everywhere prevents fragmentation as Pilot grows. Phase 2 surfaces (Salesforce, HubSpot, generic webhooks) inherit by default.

### Pending count is informational, not actionable

The count surfaces what's in flight; it does not become a clickable affordance to drill into individual pending items. That would conflict with the existing Flow 6 conflict resolution queue (which is the actionable surface for sync items requiring user attention). Pending count is ambient awareness; conflict counts and queues are actionable surfaces. The two compose without overlap: the indicator shows in-flight work, the conflict queue shows blocked work.

### Naming: "In-Flight Sync Indicator" replaces "amber-with-count"

The Pass 4 framework doc and Tier 3 #8/#9 cross-references both used the working phrase "amber-with-count" to describe this surface. That phrase is descriptive but imprecise — the indicator's state can be green, amber, or red, and the count applies in all three. The platform pattern name is **In-Flight Sync Indicator with Pending Count**. Cross-references in framework doc and states catalog should update to this name at Pass 4 close.

## Locked design decisions

### 1. Indicator visual states with pending count

**Decision**: The existing three-state indicator from Flow 3 Decision 11 is extended to incorporate a pending count. The count appears alongside the state label when greater than zero.

#### Five compositional states

The state × count combinations produce five visually distinct states:

| State | Count | Display | Use case |
| :--- | :--- | :--- | :--- |
| **Synced (idle)** | 0 | 🟢 Synced · last 12s ago | Normal at-rest state. No work pending. |
| **Synced (pending detected)** | N>0, no active sync | 🟢 Synced · 3 pending · syncing in 2m | Detected changes; next scheduled sync will pick them up. Includes time-to-next-sync if tenant is on intervals. |
| **Syncing** | N≥0 | 🟡 Syncing 3 changes... | Active sync in flight. Count is the count of items being processed in this cycle. |
| **Sync error** | N≥0 | 🔴 Sync error · 3 pending · [Resolve] | Sync attempt failed. Count is the items that didn't make it. CTA opens the relevant resolution surface (Flow 6 for calendar, Tier 1 #2 for QB, etc.). |
| **Sync paused** (deliberately offline) | N≥0 | ⚪ Paused · 3 queued · [Resume] | Mobile offline mode or owner-paused integration. Count is queued operations. CTA resumes sync or surfaces the offline state. |

#### Visual treatment

```
┌─────────────────────────────────────────────────────────────┐
│ Calendar sync · 🟢 Synced · last 12s ago                    │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ Calendar sync · 🟢 Synced · 3 pending · syncing in 2m       │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ Calendar sync · 🟡 Syncing 3 changes...                     │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ Calendar sync · 🔴 Sync error · 3 pending · [Resolve]       │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ Calendar sync · ⚪ Paused · 3 queued · [Resume]             │
└─────────────────────────────────────────────────────────────┘
```

#### Token usage

- Synced (idle): `text-margin-700`, `bg-margin-50` background pill
- Synced (pending): `text-margin-700`, `text-neutral-600` for count, `bg-margin-50` pill — count differentiated by neutral color
- Syncing: `text-alert-amber-700`, `bg-alert-amber-50` pill, with subtle pulse animation
- Sync error: `text-fault-700`, `bg-fault-50` pill, with `text-brand-indigo` for the Resolve link
- Paused: `text-neutral-600`, `bg-neutral-50` pill, with `text-brand-indigo` for the Resume link

#### Component reference

`<InFlightSyncIndicator surface="calendar|quickbooks|mobile|background" />` — single shared component across all four reference instances. The `surface` prop determines the data source for state and count.

**Rationale**: extending rather than replacing the existing three-state indicator preserves visual familiarity from Flow 3 (the dot color semantics carry over). The count addition is a pill-internal text addition rather than a new visual element. Five compositional states cover the realistic operational situations without state explosion. Pause state is new (not in original Flow 3 Decision 11) but matches the Tier 1 #3 background sync pause semantics naturally.

### 2. Hover / tap detail

**Decision**: Hovering (web) or tapping (mobile) the indicator surfaces a detail tooltip with additional context:

```
┌──────────────────────────────────────────────────────────┐
│ Calendar sync · last full sync 12s ago                   │
│                                                          │
│ Pending changes (3):                                     │
│  • New event: "Johnson panel upgrade" — 4:30 PM today    │
│  • Updated: "Smith service call" — moved to Friday       │
│  • Deleted: "Davis estimate" — removed externally        │
│                                                          │
│ Next sync: in 2 minutes 14 seconds                       │
└──────────────────────────────────────────────────────────┘
```

The tooltip lists individual pending items with brief descriptions. This is informational only — items in the tooltip don't have actions. To act on a pending item, the user navigates to the relevant entity surface (calendar event, QB invoice, mobile sync queue).

For QuickBooks the tooltip shows entity types: "Updated invoices (2), New customers (1)." For mobile sync it shows operation types: "Time entries (3), Photos (1)." For background sync it shows category: "Last attempt 4 min ago · 3 items succeeded · 1 deferred."

**Cap on tooltip detail**: maximum 5 items shown; if pending count exceeds 5, tooltip shows top 5 plus "+ N more" line.

**Mobile tap behavior**: tapping the indicator opens a small popover (similar to web hover tooltip) that auto-dismisses on tap-outside. Same content as web tooltip but in mobile-appropriate layout.

**Rationale**: pending count is a number; useful but limited. The tooltip surfaces the meaning behind the number — what's actually in flight. Without it, the count is abstract; with it, the count becomes concrete operational information. Cap at 5 items prevents tooltip overflow during high-activity periods.

### 3. Application to four reference instances

**Decision**: The pattern applies to four sync surfaces, each with surface-specific count semantics:

#### A. Calendar sync (Flow 3 dispatch board, Flow 6 calendar conflict resolution)

- **Count source**: pending changes detected in calendar_sync_pending_change table; events created/updated/deleted externally not yet pushed to Pilot, plus events created/updated/deleted in Pilot not yet pushed to external calendar
- **Located**: dispatch board top bar (per Flow 3 Decision 11), `Settings > Integrations > Calendar` page (per Flow 6)
- **Resolve target on error**: `/settings/integrations/calendar/conflicts` — Flow 6's conflict queue

#### B. QuickBooks sync (Tier 1 #2)

- **Count source**: pending changes in `integration_sync_pending_change` for QB integration; entity changes detected on either side not yet reconciled
- **Located**: `Settings > Integrations > QuickBooks` page (per Tier 1 #2 Decision 1), Mobile owner status row when applicable
- **Resolve target on error**: `/settings/integrations/quickbooks/conflicts` — Tier 1 #2's conflict queue

#### C. Mobile-to-web data sync (Flow 7 + Tier 1 #1)

- **Count source**: count of items in mobile sync queue (`mobile_sync_pending_operation`)
- **Located**: mobile sync queue surface (per Flow 7), connection state pill in mobile app shell (per Flow 7 §2)
- **Resolve target on error**: mobile sync queue surface plus owner field-issues queue (per Tier 1 #1)

#### D. Background sync (Tier 1 #3)

- **Count source**: count of items pending background sync from `mobile_sync_pending_operation` filtered for the device + `mobile_sync_session` last outcome
- **Located**: mobile sync queue surface (per Tier 1 #3 Decision 5 — last background sync indicator), `Mobile > Settings > Sync & Storage > Background sync` page
- **Resolve target on error**: mobile sync queue surface

#### Cross-instance consistency

All four instances use the same `<InFlightSyncIndicator>` component. Each instance reads from the appropriate count source via the surface-specific data hook. Visual treatment, hover/tap behavior, color tokens, and copy template are uniform.

**Rationale**: surface-specific count sources reflect the operational reality of each sync domain. Calendar counts events; QuickBooks counts entities; mobile/background count queue items. Common visual treatment ensures the user learns the indicator vocabulary once and transfers it across surfaces.

### 4. Mobile owner status row integration

**Decision**: The mobile owner status row pattern (arch doc §16.9) is extended to incorporate the in-flight sync indicator.

For each integration (Calendar sync, QuickBooks sync, etc.), the existing mobile owner status row now includes the pending count when greater than zero:

```
🟢 Calendar sync · synced (no pending)
🟢 QuickBooks sync · 2 pending · next sync 1m
🟡 Mobile sync · syncing 3 changes...
🔴 Calendar sync · sync error · [Resolve on web →]
```

This is a small extension to the existing pattern — the row format is unchanged; the count is added to the subtitle text when applicable.

**Rationale**: mobile owner status row is the right surface for at-a-glance sync awareness on mobile (per Flow 6 Decision 10, Tier 1 #1 Decision 9). Adding the count makes the row more informative without changing its structural role.

### 5. The 5-pending threshold for "amber treatment"

**Decision**: When pending count is high (>5 items in either direction), the at-rest "synced (pending detected)" state shifts visual emphasis from green to amber to signal "your view may be stale" more strongly.

```
🟢 Synced · 3 pending · syncing in 2m            (≤5 pending: standard green)
🟡 Synced · 12 pending · syncing in 2m           (>5 pending: amber to draw attention)
```

The state is still semantically "synced and waiting for next cycle," but the visual emphasis shifts because high pending counts indicate the displayed data is meaningfully out of date. Owner sees the visual shift and may choose to manually trigger sync rather than wait.

**Threshold tunable**: `tenant_sync_indicator_pending_amber_threshold` (default: 5) is a tenant setting. Tenants doing heavy bidirectional integration can raise it; quieter tenants might lower it. System default + tenant override per arch doc §16.5.

**Rationale**: a small pending count (1–5) is normal operational background. A large pending count (10, 20, 50) signals something operationally meaningful — either the integration is heavy with activity right now, or the sync schedule is too slow for the tenant's pace. Amber visual treatment for high pending count gives the owner a passive signal to act if they want.

The threshold tunable handles the edge case where the default doesn't fit a particular tenant — solo Mike doing 1 calendar event a day shouldn't see amber for "5 pending"; an active multi-tech shop might routinely have 10+ pending and not need amber until 20+.

### 6. Manual sync trigger

**Decision**: Each indicator becomes clickable in the at-rest "synced (pending detected)" state to manually trigger a sync. Clicking the indicator (or tapping on mobile) initiates an immediate sync rather than waiting for the next scheduled cycle.

```
🟢 Synced · 3 pending · syncing in 2m · [Sync now]
```

The "[Sync now]" link appears as part of the pill text. Clicking transitions the indicator to "Syncing N changes..." state.

**Manual trigger behavior**:
- **Calendar**: triggers an immediate `calendar_sync` Celery task
- **QuickBooks**: triggers an immediate `quickbooks_sync` Celery task
- **Mobile**: triggers an immediate sync session (in foreground; bypasses background sync interval)
- **Background sync**: not applicable — background sync is OS-scheduled or push-triggered, no user-initiated flow

For surfaces where manual trigger doesn't apply (background sync), the link is hidden in the at-rest state.

**Rationale**: manual trigger is a small operational nicety that handles the "I see 3 pending; I don't want to wait 2 minutes; let me sync now" case. Cost of building it is low (existing Celery tasks, just dispatched on user action rather than schedule). Available only when relevant; hidden when not.

### 7. Settings cross-link

**Decision**: When the indicator is in error state, the resolve CTA opens the relevant resolution surface. This already exists in Flow 3 / Flow 6 / Tier 1 #2 / Flow 7. Tier 4 #12 confirms the resolve target mappings:

| Surface | Error CTA target |
| :--- | :--- |
| Calendar | `/settings/integrations/calendar/conflicts` |
| QuickBooks | `/settings/integrations/quickbooks/conflicts` |
| Mobile data sync | mobile sync queue surface (web for owners; on-device for tech) |
| Background sync | mobile sync queue surface |

**Rationale**: error states should always have a resolution path. The existing flow specs covered the resolution surfaces; this addendum just confirms the indicator routes correctly.

## UX patterns established (for inheritance / reuse)

| Pattern | This spec | Inherits from / extends |
| :--- | :--- | :--- |
| **In-Flight Sync Indicator with Pending Count** (platform pattern) | **NEW** | Flow 3 Decision 11 (extends), Tier 3 #8/#9 L3 (extends background indicator) |
| Pending count tooltip with capped item detail | **NEW** | — |
| Manual sync trigger inline in indicator | **NEW** | — |
| Tunable threshold for visual emphasis shift | Reused | Arch doc §16.5 system-default-with-tenant-override |
| Surface-specific count semantics with shared component | **NEW** | — |

The In-Flight Sync Indicator pattern is the central new contribution. Two reuses (system-default-with-tenant-override for the threshold, plus inheritance from Flow 3 Decision 11 and Tier 3 L3). The other patterns are sub-decisions within the main pattern.

This pattern earns a §16 entry as platform vocabulary. Phase 2 sync surfaces (Salesforce, HubSpot, generic webhooks) inherit by default.

## Cross-domain considerations

### A. Cross-references in framework doc and states catalog need updating

Per the naming change from "amber-with-count" to "In-Flight Sync Indicator":

- Pass 4 framework doc Tier 4 #12 row should be updated to read "Flow 3 dispatch board sync indicator refinement (In-Flight Sync Indicator with Pending Count)"
- Tier 3 #8/#9 states catalog Cross-Domain F should be updated to reference the new pattern name
- Both updates are touch-up edits at Pass 4 close, not now

### B. Arch doc §16 entry

The In-Flight Sync Indicator pattern is the third pattern this Pass 4 deliverable adds to the platform vocabulary (after Tier 1's three patterns and Tier 1.5's three patterns). It earns a §16 entry — likely §16.13 (next available after Tier 1.5's §16.10–§16.12).

The §16 entry definition for arch doc v4.3:

> **In-Flight Sync Indicator with Pending Count** — a sync surface (calendar sync, QuickBooks sync, mobile data sync, background sync) renders its current state plus a count of pending operations that haven't yet completed. Five compositional states cover synced-idle, synced-with-pending, syncing-active, sync-error, and sync-paused. Hover/tap surfaces individual pending items as ambient awareness. Manual sync trigger inline for owner-initiated immediate sync. Tunable threshold (`tenant_sync_indicator_pending_amber_threshold`) shifts visual emphasis to amber when pending count is operationally meaningful.
>
> **Reference instances**: Calendar (Flow 3 + Flow 6), QuickBooks (Tier 1 #2), Mobile-to-web data sync (Flow 7 + Tier 1 #1), Background sync (Tier 1 #3).
>
> **Future surfaces inheriting this pattern**: Salesforce sync, HubSpot sync, generic webhook integrations, any future bilateral-sync integration.

This update lands at Pass 4 close as part of the consolidated v4.3 → v5 arch doc work.

### C. Tier 2 #4 settings inventory needs the threshold setting

The new tenant setting `tenant_sync_indicator_pending_amber_threshold` should be added to the Tier 2 #4 settings inventory at Pass 4 close. Lives at `Settings > Integrations > Sync display preferences` (a new sub-page) or as a single setting under each integration's existing settings page (Calendar, QuickBooks). My recommendation: single setting under `Settings > Operations > Display preferences` (a sub-page of the existing Operations group from Tier 2 #4) with a helper text explaining what it controls.

A75-equivalent backend addition for this setting is small — a single tenant setting field + standard read/write endpoints per A52/A54 from Tier 2 #4.

### D. Backend addition consolidation with existing sync infrastructure

A79 below covers the pending-count exposure. The infrastructure to count pending operations already exists for each sync surface — calendar has `calendar_sync_pending_change`; QB has `integration_sync_pending_change`; mobile has `mobile_sync_pending_operation`. A79 creates a unified API surface that reads from all four sources via a single endpoint pattern.

This means A79 is more "API consolidation" than "new infrastructure" — the underlying data exists; we're surfacing it consistently.

### E. Real-time updates via SSE

The indicator updates in real time via SSE (per arch doc §13.11). When sync state changes (sync starts, sync completes, error occurs, count changes), the SSE channel pushes the update; the indicator re-renders without page refresh.

Existing SSE infrastructure handles this; A79 just emits the right events.

### F. Tier 3 #8/#9 L3 background indicator integration

The In-Flight Sync Indicator is essentially a more informative variant of L3 (background indicator) from Tier 3 #8/#9. The two should be implemented as a layered component design:

- `<BackgroundIndicator>` (L3 from Tier 3 #8/#9) is the base component — single dot with state coloring
- `<InFlightSyncIndicator>` (this spec) extends `<BackgroundIndicator>` with count display, hover detail, manual trigger, and tunable threshold

Component file structure:
- `packages/ui/src/states/BackgroundIndicator.tsx` — base
- `packages/ui/src/states/InFlightSyncIndicator.tsx` — extends base with sync-specific behavior

This keeps the L3 catalog entry honored (basic background indicator works without the sync extension) while the sync surfaces get the richer treatment.

### G. Mobile vs web rendering

The component renders identically on web and mobile (single shared React/Gluestack component). Mobile adapts:
- Tap (instead of hover) opens the detail tooltip
- Tooltip becomes a small popover (auto-dismiss on tap-outside)
- Indicator's text label becomes more concise on narrow viewports — e.g., "🟡 Syncing..." without count when viewport is too narrow for full text; full text on tablet/web

Responsive variants are handled at the component level; this spec's visual treatments cover the desktop/tablet case.

## Deferred items (Phase 2 / for future iteration)

- **Sync analytics dashboard** — historical pending counts over time, sync latency stats, error frequency — Phase 2
- **Predictive sync indicators** — ML-based prediction of next sync completion time given current load — Phase 2 (likely never; nice-to-have)
- **Per-integration sync intervals configurable** — currently fixed; Phase 2 may add tenant-controlled intervals
- **Detail tooltip "act on this item" affordances** — currently informational only — Phase 2 if observed user demand
- **Tooltip pagination beyond top 5** — currently capped — Phase 2 if needed
- **Sync notification preferences** — getting notified when sync errors occur — already covered by Tier 2 #5 "Sync conflicts" notification category; no Phase 2 work needed
- **Differential pending counts** (e.g., "3 pending → 5 pending in last minute") — trend awareness — Phase 2
- **Multi-integration aggregate indicator** — single "all syncs" indicator at app shell — Phase 2

## Validation checklist

Before implementation begins:

- [ ] `<InFlightSyncIndicator>` component implemented with five compositional states
- [ ] Component extends `<BackgroundIndicator>` (L3) per Cross-Domain F
- [ ] Hover (web) / tap (mobile) detail tooltip with capped 5-item display
- [ ] Manual sync trigger functional for calendar, QB, mobile (not background)
- [ ] Resolve CTA mappings verified for each surface (Cross-Domain B)
- [ ] Tunable threshold setting `tenant_sync_indicator_pending_amber_threshold` per Decision 5
- [ ] Mobile owner status row updated to show pending count per Decision 4
- [ ] SSE real-time updates wired for indicator state changes
- [ ] All four reference instances (Calendar, QuickBooks, Mobile, Background) using the same component
- [ ] Surface-specific count sources tested per Decision 3 mapping table
- [ ] Cross-references in framework doc and states catalog updated to "In-Flight Sync Indicator" naming at Pass 4 close
- [ ] Arch doc §16.13 entry drafted for v4.3 → v5 consolidation

## Backend additions (new for Tier 4 #12)

### A79. Unified Pending-Count Exposure for Sync Surfaces

**Triggered by**: Decisions 1, 3, 4 — pending-count visibility across all four sync surfaces.

**Scope**:

**Unified pending-count API**:
- New endpoint: `GET /api/v1/sync/{surface}/status` — returns sync state + pending count for a given surface
- Path parameter `surface`: `calendar | quickbooks | mobile_data | background`
- Response shape:
  ```json
  {
    "surface": "calendar",
    "state": "synced_pending | syncing | sync_error | sync_paused | synced_idle",
    "pending_count": 3,
    "pending_items": [
      {"type": "event_added", "label": "Johnson panel upgrade — 4:30 PM today"},
      {"type": "event_updated", "label": "Smith service call — moved to Friday"},
      {"type": "event_deleted", "label": "Davis estimate — removed externally"}
    ],
    "last_sync_at": "2026-04-27T14:32:18Z",
    "next_sync_at": "2026-04-27T14:37:18Z",
    "manual_trigger_supported": true,
    "resolve_target": null
  }
  ```
- Pending items array capped at 5 by server (matches tooltip cap from Decision 2)

**Backend reads from existing per-surface tables**:
- Calendar: aggregates from `calendar_sync_pending_change` table
- QuickBooks: aggregates from `integration_sync_pending_change` (filtered for QB)
- Mobile: aggregates from `mobile_sync_pending_operation` (filtered for the device or tenant scope)
- Background: aggregates from `mobile_sync_pending_operation` + `mobile_sync_session` last outcome

**SSE event emission**:
- Existing SSE channels emit `sync_status_changed` events when state or count changes for any surface
- Frontend subscribes to relevant channels and re-renders indicator on event

**Manual trigger endpoints**:
- Existing endpoints for triggering syncs already exist per individual flow specs:
  - `POST /api/v1/integrations/calendar/sync` — triggers immediate calendar sync
  - `POST /api/v1/integrations/quickbooks/sync` — triggers immediate QB sync
  - `POST /api/v1/mobile/sync-now` — triggers immediate mobile sync session
- A79 doesn't add new trigger endpoints; just confirms existing ones support the indicator's manual-trigger affordance

**New tenant setting**:
- `tenant_sync_indicator_pending_amber_threshold` (integer, default 5, range 1–100) per Decision 5
- Standard read/write via A52/A54 from Tier 2 #4

**Effort estimate**: Small — 2 days. The infrastructure exists; A79 is API consolidation + SSE event wiring + the threshold setting. Most of the work is in the frontend component (separate frontend effort, not in this backend addition).

### Total Tier 4 #12 backend additions

A79 (2 days) = **2 days**.

---

## What this surface does NOT cover

- The actual `<InFlightSyncIndicator>` component implementation — frontend coding work, not design spec work (estimated 2–3 frontend days for the component plus SSE integration)
- Sync analytics dashboard — Phase 2
- Predictive sync timing — Phase 2 (likely never)
- Per-integration sync interval configurability — Phase 2
- Tooltip drill-into-individual-pending-items affordances — Phase 2
- Multi-integration aggregate indicator — Phase 2

## Cumulative effects on Pass 4 totals

**Backend additions ledger**: A79 added (1 addition). Cumulative through Tier 4 #12: A1–A79.

**Backend day estimate update**:
- Pre-Tier-4-#12 cumulative remaining MVP: 227–296.5 days
- Tier 4 #12 additions: 2 days
- New cumulative remaining MVP: **229–298.5 days**

**Frontend component-library work** (not in backend ledger but worth tracking): ~2–3 days for the `<InFlightSyncIndicator>` component including SSE integration and four-surface application.

**Framework doc**: Tier 4 #12 status flips from `pending` to `locked`. Tier 4 continues with #13 (customer-facing public link styling) and #14 (help/about/feedback).

**Arch doc touch-up needed at Pass 4 close**: §16.13 entry per Cross-Domain B.

**Cross-references to update at Pass 4 close**:
- Framework doc Tier 4 #12 row → "In-Flight Sync Indicator with Pending Count" naming
- Tier 3 #8/#9 states catalog Cross-Domain F → updated naming reference

## Next: Tier 4 #13 — Customer-Facing Public Quote/Invoice Link Styling

Tier 4 #13 is Shape E (visual design + content composition). Hosts pre-launch hygiene email template designs and privacy footer content slots. Includes the customer-facing public quote and invoice URLs that recipients access without logging into Pilot.

Estimated 350–450 lines per the framework's Shape E deliverable definition.

After #13, Tier 4 closes with #14 (help/about/feedback). Then Pass 4 closes — full v3.1 PRD, v5 arch doc, v6 backend ledger get issued; framework doc gets its third (and final) full rewrite.
