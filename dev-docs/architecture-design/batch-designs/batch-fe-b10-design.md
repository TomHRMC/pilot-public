# FE-B10 Batch Design — Customer Comms Extension: Inbound SMS (Pass 4 Tier 1.5)

**Batch**: FE-B10
**Phase**: Phase 1 — Surface Design Session
**Date**: 2026-05-26
**Author**: Pilot Architect
**Status**: Design Complete — Ready for React Engineer Handoff
**Prerequisite Batches**: FE-B0, FE-B1, FE-B2, FE-B3, FE-B4, FE-B5, FE-B6, FE-B7, FE-B8, FE-B9
**Backend Gate**: BE-B11 (SMS / Telnyx stack — A59–A66)
**Gates Downstream**: None (FE-B10 has no downstream batch dependencies)
**Test Subfolder**: `apps/{web,mobile}/__tests__/batch_fe_b10/`

---

## Prerequisites Confirmed

- `MessagePreviewModal` — **LOCKED** from FE-B6 ✅; `free-form` mode path already implemented; FE-B10 is a consumer
- `usePreviewBeforeSend()` — **LOCKED** from FE-B6 ✅; supports `mode: 'free-form'` with `freeFormBody` + `threadId` params
- `VoiceConfirmTurn` — **LOCKED** from FE-B3 ✅; props: `{ prompt, onConfirm, onCancel, isProcessing, testID }`
- `useVoiceStream()` — FE-B3 ✅; used for single-utterance mic capture in composer
- `useSseChannel()` — FE-B4 ✅; web-only; **MOBILE EXTENSION NOTE already in file** — requires `react-native-sse` for mobile inbox live updates
- `PendingBadge` — FE-B7 ✅; used for optimistic outbound reply pending state
- `useOptimisticMutation()` — FE-B7 ✅; used for optimistic quota decrement + reply dispatch
- `NotificationBanner` — FE-B1 ✅; quota warnings use this
- Mobile tab layout confirmed: **5 tabs** — `index` (Home), `jobs`, `customers`, `calcs`, `owner` — in `(tabs)/_layout.tsx`; NO existing Inbox tab
- Outbound comms route pattern confirmed: `(tabs)/jobs/[jobId]/comms.tsx` uses `usePreviewBeforeSend` with `mode: 'template'`
- Web `features/` directory confirmed: **no `customer-comms/` folder exists** — FE-B10 creates it
- Backend quota API confirmed from `backend/services/sms_quota.py`: `QuotaCheckResult.blocked_reason` values: `'monthly_quota_reached' | 'customer_opted_out' | None`

---

## Key Codebase Facts Established During Design Session

| Fact | Detail |
|:---|:---|
| Mobile tab for SMS inbox | **Sub-section of `(home)` stack group** — no new tab; new stack screens under `(tabs)/(home)/inbox/` |
| `usePreviewBeforeSend` free-form path | Already calls `/api/v1/communications/send-free-form` in `send()`. FE-B10 must wire `threadId` → BE-B11/A62 `POST /threads/{thread_id}/reply`. Hook's free-form send path is the bridge. |
| `useSseChannel` on mobile | **Requires `react-native-sse`** — comment already in hook. Mobile inbox SSE hook must inject `eventSourceFactory` using `react-native-sse`. |
| `computeSmsSegments` in hook | `usePreviewBeforeSend.ts` has a **simple ASCII heuristic** only (line 57–63). FE-B10's `useSegmentCount` implements proper GSM-7 charset validation with multi-segment boundaries. |
| Web comms surface | FE-B6 established `MessagePreviewModal` + template send flow (mobile + web modal). FE-B10 creates `apps/web/src/features/customer-comms/` for the inbound thread view. |
| `sms_opted_out` field | `customer.sms_opted_out` (boolean) confirmed in `check_quota()` at line 68. `blocked_reason = 'customer_opted_out'` when true. |
| `cap_policy` source | Period's `cap_policy` field OR resolved from `platform_setting` key `sms_quota_cap_policy`. Both `'soft'` and `'hard'` values confirmed. |
| Unrouted queue route | Confirmed: `GET /api/v1/communications/unrouted` per A60. Assignment creates thread and removes unrouted entry. |
| Dashboard widget endpoint | `GET /api/v1/dashboard/widgets/recent-customer-messages?limit=10` per A64. Confirmed by workstream analysis doc. |

---

## Resolved Design Decisions

### Decision 1 — Mobile Inbox Tab Placement and Route Structure

**Decision**: The SMS inbox lives as a **sub-surface within the existing `(home)` stack group** — NOT a new dedicated tab. A new "(Customer messages)" section appears in the Home screen below Today's schedule, per spec Decision 10. The dedicated screen stack is nested under `(tabs)/(home)/inbox/`.

**Rationale**: The current tab layout (`_layout.tsx`) has exactly 5 tabs. Adding a sixth "Inbox" tab would change the tab bar geometry and force refactoring of `_layout.tsx` — a risky change mid-stream. The spec explicitly says "existing Mobile > Today tab gains a new sub-section." The (home) group uses Expo Router's nested stack pattern (already established for `voice/`, `sync/`, `quotes/`), so inbox screens fit cleanly.

**Route tree**:
```
apps/mobile/app/(tabs)/(home)/
  inbox/
    _layout.tsx         ← Stack layout for inbox sub-navigation
    index.tsx           ← CustomerThreadsInboxScreen (full threads list, "View all")
    [threadId].tsx      ← ThreadConversationScreen (full message history + composer)
```

**Home screen modification**: `apps/mobile/app/(tabs)/(home)/index.tsx` gains a `<CustomerMessagesSectionRow>` component showing the 5 most recent threads with unread count badge, placed below today's schedule and above the sync queue affordance.

**Push notification deep-link** (cold-start to specific thread):
- Deep-link URL: `pilot:///(tabs)/(home)/inbox/[threadId]`
- Expo Router's `Linking.config` handles cold-start: app opens, auth gate passes, navigates to `(tabs)/(home)/inbox/[threadId]`
- Query param `?unread=true` scrolls to first unread message in thread
- Handler lives in `apps/mobile/features/customer-comms/notifications/customerMessagePushHandler.ts`

**Unread count badge on Home tab icon**: The `(tabs)/_layout.tsx` Home tab's `tabBarIcon` renders an `<UnreadBadge>` overlay when `inboxUnreadCount > 0` (driven by `useCustomerThreadsSummary()` polling TanStack Query).

### Decision 2 — Segment Counter Implementation

**Decision**: `useSegmentCount` is a **hook** in `packages/ui/src/hooks/useSegmentCount.ts` — **shared** in `packages/ui/` because both the mobile reply composer and any future web reply composer consume it.

**Rationale**: The existing `computeSmsSegments()` helper in `usePreviewBeforeSend.ts` is a simplified ASCII-only heuristic. FE-B10 needs proper GSM-7 charset validation (including extended table characters: `€ { } [ ] ~ \ |` each count as 2 chars in the extended table). Since the spec explicitly requires "real-time GSM-7 vs Unicode segment count" and two surfaces (mobile composer, and spec §17 implies the web reply composer if added) need this, it belongs in the shared package.

**Interface**:
```typescript
interface UseSegmentCountOptions {
  body: string;
}

interface SegmentCountResult {
  segmentCount: number;
  encoding: 'gsm7' | 'unicode';
  charCount: number;
  charsPerSegment: number;   // 160 (GSM-7 single) | 153 (GSM-7 multi) | 70 (Unicode single) | 67 (Unicode multi)
  charsRemaining: number;    // chars remaining until next segment boundary
}

function useSegmentCount(options: UseSegmentCountOptions): SegmentCountResult
```

**GSM-7 detection rule**: if ALL characters in `body` belong to the GSM-7 basic charset + extended table, encoding is `'gsm7'`; any character outside → `'unicode'`. Emoji forces `'unicode'`.

**Multi-segment boundary**: single-segment: 160/70 chars. Multi-segment (> 1 segment): 153/67 chars per segment due to UDH header.

**Web usage**: the web thread view is owner-read-only — no compose surface → no segment counter needed on web for MVP. If web reply composer is added in Phase 2, it imports from `packages/ui/`.

### Decision 3 — Voice-to-Text Reply Composition Flow

**Decision**: Voice is a **transcription-only input path** — distinct from the full voice session in FE-B3. The mic button in the reply composer captures a **single utterance**, Whisper transcribes it, and the text populates the text input field. The tech edits text normally, then sends through `usePreviewBeforeSend` as a free-form message. `MessagePreviewModal` (§16.7) gates send. `VoiceConfirmTurn` is NOT part of the touch-initiated flow — it is used only for the **web voice session** path (`reply_to_customer_sms` intent from A63).

**Mobile composer voice flow**:
1. Tech taps mic button → `useVoiceStream()` opens WebSocket, records single utterance
2. Whisper transcribes → text appears in `TextInput` field (`transcribedText` state)
3. Tech can edit the transcribed text freely
4. Tech taps Send → `preview({ mode: 'free-form', freeFormBody: editedText, threadId })` → `MessagePreviewModal` opens
5. Tech taps "Send" in modal → `usePreviewBeforeSend.send()` → `POST /threads/{threadId}/reply`
6. Voice session state machine: `idle → recording → transcribed → editing → sent`

**Web voice session path** (A63 voice intent `reply_to_customer_sms`):
- Resolves thread by customer name from utterance
- Backend renders preview text: *"I'll send to [customer]: '[body].' That's [N] segments, you have [N] left this month. Confirm?"*
- Frontend renders `<VoiceConfirmTurn>` with this readback as `prompt`
- On confirm: calls `POST /threads/{thread_id}/reply`
- This path **bypasses** `MessagePreviewModal` because the AI readback IS the preview (§16.3 confirm-as-turn IS the preview for voice path)

**Boundary**: Mobile = UI-level single-utterance transcription → text field → MessagePreviewModal. Web = intent-level voice action → AI readback → VoiceConfirmTurn. Two distinct flows; neither reimplements the other's pattern.

**`useVoiceStream` usage**: called with `{ mode: 'single-utterance' }` config — existing hook supports this. No multi-turn context needed for dictation; full session not started.

### Decision 4 — Quota Indicator Integration with Real-Time State

**Decision**:

**TanStack Query key**: `['sms-quota']`; `staleTime: 60_000`; `refetchOnWindowFocus: true`; optimistic update subtracts estimated segment count on send dispatch.

**Optimistic update**: YES — via `useOptimisticMutation()` from FE-B7. On `mutate()`:
1. `onMutate`: decrement `remaining_segments` by estimated segment count from `useSegmentCount`
2. `onSuccess`: invalidate `['sms-quota']` to fetch actual server value
3. `onError`: rollback to snapshot value

**Three visual states** (rendered in `<SmsQuotaIndicator>`):

| State | Trigger | Token class | Copy |
|:---|:---|:---|:---|
| Normal | `remaining > 0.2 × included` | `text-neutral-500` | `"N segments remaining this month"` |
| Warning | `remaining ≤ 0.2 × included` AND `remaining > 0` | `text-alert-600 bg-alert-50` | `"⚠ N segments left this month"` |
| Blocked (soft cap) | `remaining === 0` AND `cap_policy === 'soft'` | `text-fault-700 bg-fault-50` | `"Monthly quota reached — overages billed at $0.05/segment"` |
| Blocked (hard cap) | `remaining === 0` AND `cap_policy === 'hard'` | `text-fault-700 bg-fault-50` | `"Monthly SMS limit reached — contact your owner"` |

**Hard cap vs soft cap distinction**: `GET /api/v1/sms/quota` response includes `cap_policy: 'soft' | 'hard'`. The `SmsQuotaIndicatorProps` receives `capPolicy` directly; the component does not derive it.

**Send button disabled**: ONLY when `cap_policy === 'hard'` AND `remaining === 0`. Soft cap allows send with visual warning.

### Decision 5 — Web Thread View and Dashboard Widget Placement

**Decision (a) — Threaded customer comm history**:
- **Route**: `/customers/[id]/comms` — FE-B6 may have established this route or it may be new. Given no `customer-comms/` feature folder exists in `apps/web/src/features/`, FE-B10 creates it.
- **Layout change**: The existing comm history table (outbound-only, flat list per FE-B6 spec Decision 10) is replaced/extended with a **chat-bubble chronological view**. Two directions: outbound (brand-indigo, right-aligned) + inbound (neutral-100, left-aligned).
- **Multiple threads**: when a customer has had conversations with multiple techs, they are shown as **collapsed thread groups** (one per `thread_id`) with a thread header showing the tech name + date range.

**Decision (b) — Dashboard widget**:
- **Route**: Widget on `/dashboard` page (the main dashboard). Per Pass 2 §5 pin-to-dashboard pattern, the owner can pin/unpin it from the widget catalog.
- **TanStack Query key**: `['dashboard-widget-recent-messages', { limit: 10 }]`; `staleTime: 30_000`
- **Live updates**: SSE via `/api/v1/dashboard/stream` events — `customer_message_received` event type invalidates the widget query. Falls back to 30s polling if SSE unavailable.
- **Endpoint confirmed**: `GET /api/v1/dashboard/widgets/recent-customer-messages?limit=10` per A64.
- **Widget click-through**: each message row links to `/customers/[id]/comms?thread=[threadId]` to open the full thread view.

### Decision 6 — Unrouted Message Management Queue (Web)

**Decision**: Route is `/settings/integrations/sms/unrouted` — parallel to the SMS settings surface at `/settings/integrations/sms`.

**Rationale**: Unrouted messages are an SMS-integration operational concern — they live with the integration settings, not with the Approvals surface (which is for field issues and owner-action items). Pattern is consistent with QB conflicts at `/settings/integrations/quickbooks/conflicts`.

**Route tree**:
```
apps/web/src/app/(authed)/settings/integrations/sms/
  page.tsx              ← SmsIntegrationSettingsPage (number, quota, cap policy)
  unrouted/
    page.tsx            ← UnroutedMessageQueuePage (list of unrouted inbound)
    [id]/
      page.tsx          ← UnroutedMessageAssignPage (assign customer + tech)
```

**Assignment UI**: The `<UnroutedMessageAssignForm>` contains:
1. Message preview (body text, received timestamp, sender phone)
2. Customer search (typeahead, `GET /api/v1/customers?search=`) → selects customer
3. Tech selector (dropdown of active techs for the tenant)
4. "Create thread and assign" button → `POST /api/v1/communications/unrouted/{id}/assign` with `{ customer_id, tech_id }`
5. On success: banner "Thread created · message assigned to [Tech]"; navigate back to unrouted queue

**No shared components with FE-B9 field issues**: different domain (SMS routing vs mobile sync escalation). The queue table pattern is similar but entirely separate components.

**Owner notification**: when a new unrouted message arrives, `NotificationBanner` (in-app, per §B Cross-Domain G) appears with "A customer texted but we couldn't match them to a conversation — review" with deep-link to `/settings/integrations/sms/unrouted`.

### Decision 7 — STOP Opt-Out UX and TCPA Compliance Surfacing

**Decision**: Block is applied at **both levels** — composer-level (proactive, pre-send) AND API error-response level (defensive fallback).

**Composer-level**: `GET /api/v1/sms/quota` (with `customer_id` param) returns `blocked_reason: 'customer_opted_out'` when `customer.sms_opted_out === true`. The composer detects this at load time (when the thread screen opens, quota is fetched with `customerId`). Send button is **disabled** and the `<SmsQuotaIndicator>` shows the error banner:
> `"Customer has opted out — they cannot be reached via SMS"`

**Thread header**: When `customer.sms_opted_out === true`, the thread header displays a `<SmsOptOutBadge>` chip: "SMS opted out · `[date opted out]`". This appears in both mobile thread screen header and web comm history thread header. Token: `bg-fault-50 text-fault-700 border-fault-200`.

**API error-response level (fallback)**: `POST /threads/{threadId}/reply` returns `422` with `{ "detail": "customer_opted_out" }` if somehow the send is attempted. `usePreviewBeforeSend.send()` catches this and surfaces `NotificationBanner severity="error"` with the same copy.

**Historical messages**: Remain fully visible after opt-out. The thread is read-only (composer hidden or disabled) but the full message history is displayed. Audit trail principle is non-negotiable.

**STOP processing notification to owner**: when a customer sends STOP and is added to the opt-out list (BE-B11/A59 webhook processes this), the owner receives a push notification: "A customer (John Smith) has opted out of SMS" — this is a Customer activity push notification per Tier 2 #5 spec.

---

## A — Component Implementation Plan

### A.1 New Shared Components (`packages/ui/src/`)

#### A.1.1 `useSegmentCount()` — SMS Segment Count Hook

| Field | Value |
|:---|:---|
| **File** | `packages/ui/src/hooks/useSegmentCount.ts` |
| **Platform** | Web + Mobile (pure TypeScript — no platform dependency) |
| **Pattern** | Decision 2 above |
| **Consumers** | `apps/mobile/features/customer-comms/components/ReplyComposer.tsx` (this batch); any future web reply composer |
| **Export from** | `packages/ui/src/index.ts` under `// ── FE-B10 Exports ──` |

**Interface**:
```typescript
export interface SegmentCountResult {
  segmentCount: number;
  encoding: 'gsm7' | 'unicode';
  charCount: number;
  charsPerSegment: number;
  charsRemaining: number;
}

export function useSegmentCount(body: string): SegmentCountResult
```

**Implementation notes**:
- Must validate actual GSM-7 basic charset + extended table (not ASCII heuristic)
- Extended table chars (`€ { } [ ] ~ \ |`) each count as **2** GSM-7 code units
- Multi-segment UDH: when `segmentCount > 1`, use 153 (GSM-7) / 67 (Unicode) per segment
- Memoized via `useMemo([body])`

#### A.1.2 `<SmsQuotaIndicator>` — Quota Footer Component

| Field | Value |
|:---|:---|
| **File** | `packages/ui/src/sms-quota-indicator/SmsQuotaIndicator.tsx` |
| **Platform** | Mobile (Gluestack primitives for mobile composer); separate web variant not needed for MVP (web is owner-read-only) |
| **Pattern** | Decision 4 above |
| **Consumers** | `apps/mobile/features/customer-comms/components/ReplyComposer.tsx` |
| **Export from** | `packages/ui/src/index.ts` |

**Interface**: See Section F.5.

#### A.1.3 `<SmsThreadBubble>` — Message Bubble Component (Polymorphic)

| Field | Value |
|:---|:---|
| **File** | `packages/ui/src/sms-thread-bubble/SmsThreadBubble.tsx` |
| **Platform** | Both (web + mobile variants, same pattern as `DiffView` from FE-B5): `SmsThreadBubble.tsx` (web), `SmsThreadBubble.native.tsx` (mobile) |
| **Purpose** | Renders a single message bubble with direction (outbound/inbound), body, timestamp, delivery status badge, `<PendingBadge>` for optimistic messages |
| **Consumers** | Mobile: `ThreadConversationScreen`; Web: `CustomerCommsHistoryView` |
| **Export from** | `packages/ui/src/index.ts` |

**Interface**: See Section F.6.

#### A.1.4 `<SmsOptOutBadge>` — Customer Opt-Out Indicator

| Field | Value |
|:---|:---|
| **File** | `packages/ui/src/sms-opt-out-badge/SmsOptOutBadge.tsx` |
| **Platform** | Both (web + mobile) |
| **Purpose** | Compact fault-colored chip: "SMS opted out · [date]". Appears in thread headers on both platforms. |
| **Consumers** | Mobile thread header, web thread header |
| **Export from** | `packages/ui/src/index.ts` |

---

### A.2 New Web Feature Components

#### A.2.1 Customer Comms History Extension — `apps/web/src/features/customer-comms/`

| File | Purpose |
|:---|:---|
| `components/CustomerCommsHistoryView.tsx` | Full threaded comm history with direction-coded bubbles. Consumes `<SmsThreadBubble>`. Replaces/extends the flat table from FE-B6. Grouped by thread. |
| `components/CommThreadGroup.tsx` | Collapsible group for a single thread: header (tech name, date range, unread count), message list. |
| `components/SmsOptedOutBanner.tsx` | Fault-color banner at top of thread view when customer is opted out. Contains `<SmsOptOutBadge>`. |
| `hooks/useCustomerCommsHistory.ts` | TanStack Query; `GET /api/v1/customers/{customerId}/communication-history`; returns threaded list |
| `hooks/useCustomerCommsSse.ts` | Composes `useSseChannel`; SSE path `/api/v1/customers/{customerId}/comms/stream`; invalidates history query on new message event |
| `mocks/customerCommsFixtures.ts` | Typed fixture data: outbound + inbound messages; opted-out scenario; multi-thread scenario |

**Page route components** (App Router):

| File | Route |
|:---|:---|
| `apps/web/src/app/(authed)/customers/[id]/comms/page.tsx` | `/customers/[id]/comms` — owner/tech role gate |

#### A.2.2 Dashboard Widget — `apps/web/src/features/dashboard/`

| File | Purpose |
|:---|:---|
| `components/RecentCustomerMessagesWidget.tsx` | Dashboard widget: last 10 customer messages across tenant, color-coded by direction. Tapping a row navigates to `/customers/[id]/comms?thread=[threadId]`. |
| `hooks/useRecentCustomerMessages.ts` | TanStack Query; `GET /api/v1/dashboard/widgets/recent-customer-messages?limit=10`; `staleTime: 30_000`; SSE invalidation |

#### A.2.3 Unrouted Message Queue — `apps/web/src/features/sms-unrouted/`

| File | Purpose |
|:---|:---|
| `components/UnroutedMessageQueue.tsx` | Paginated list of unrouted inbound messages. Columns: received timestamp, sender phone (masked), message preview, Assign button. |
| `components/UnroutedMessageRow.tsx` | Single queue row. Shows received timestamp, first 80 chars of body, Assign CTA. |
| `components/UnroutedMessageAssignForm.tsx` | Customer typeahead search + tech dropdown + "Create thread and assign" button. |
| `hooks/useUnroutedMessages.ts` | TanStack Query; `GET /api/v1/communications/unrouted`; cursor-paginated |
| `hooks/useAssignUnrouted.ts` | Mutation hook; `POST /api/v1/communications/unrouted/{id}/assign`; invalidates unrouted queue on success |
| `mocks/unroutedFixtures.ts` | Typed fixture data for unit tests and MSW handlers |

**Page route components** (App Router):

| File | Route |
|:---|:---|
| `apps/web/src/app/(authed)/settings/integrations/sms/page.tsx` | `/settings/integrations/sms` — SMS number, quota, cap policy |
| `apps/web/src/app/(authed)/settings/integrations/sms/unrouted/page.tsx` | `/settings/integrations/sms/unrouted` — unrouted queue list |
| `apps/web/src/app/(authed)/settings/integrations/sms/unrouted/[id]/page.tsx` | `/settings/integrations/sms/unrouted/[id]` — assignment form |

---

### A.3 New Mobile Feature Components

#### A.3.1 Customer Comms Feature — `apps/mobile/features/customer-comms/`

| File | Purpose |
|:---|:---|
| `components/CustomerMessagesSectionRow.tsx` | Home-screen section widget showing up to 5 recent threads with unread count, last message preview, customer name, relative timestamp. Tap → `/(tabs)/(home)/inbox/`. |
| `components/ThreadListItem.tsx` | Single thread row in the inbox list: customer avatar initials, customer name, last message preview (50 chars), relative time, unread count badge. |
| `components/ReplyComposer.tsx` | Bottom-anchored composer zone: mic button (primary), `TextInput` (secondary), send button, `<SmsQuotaIndicator>` in footer. Composes `usePreviewBeforeSend` for the send path. |
| `components/ThreadConversationList.tsx` | Scrollable `FlatList` of `<SmsThreadBubble>` components. Inverted (newest at bottom). Loads paginated messages. |
| `components/ThreadHeader.tsx` | Screen header: customer name, job context (if available), `<SmsOptOutBadge>` (when opted out). |
| `hooks/useCustomerThreads.ts` | TanStack Query; `GET /api/v1/mobile/inbox/customer-threads`; `staleTime: 30_000`; returns tech's threads |
| `hooks/useThreadMessages.ts` | TanStack Query infinite; `GET /api/v1/communications/threads/{threadId}/messages?page={page}`; cursor-paginated |
| `hooks/useReplyToThread.ts` | Mutation hook; wraps `useOptimisticMutation` + `usePreviewBeforeSend` free-form path; calls `POST /threads/{threadId}/reply`; decrements quota optimistically |
| `hooks/useMarkThreadRead.ts` | Mutation; `POST /threads/{threadId}/mark-read`; invalidates `['customer-threads']` on success |
| `hooks/useSmsQuota.ts` | TanStack Query; `GET /api/v1/sms/quota?customer_id={customerId}`; returns `SmsQuotaStatus` |
| `hooks/useMobileInboxSse.ts` | Composes `useSseChannel` with `react-native-sse` eventSourceFactory; path `/api/v1/mobile/inbox/stream`; invalidates `['customer-threads']` on `customer_message_received` event |
| `hooks/useVoiceDictation.ts` | Single-utterance transcription hook: wraps `useVoiceStream()` with `mode: 'single-utterance'`; returns `{ startDictating, stopDictating, transcript, isRecording, error }` |
| `notifications/customerMessagePushHandler.ts` | Expo Notifications handler for `customer_message` push type. Navigates to `/(tabs)/(home)/inbox/[threadId]` on tap. Invalidates thread list query. |
| `mocks/customerCommsFixtures.ts` | Typed fixture data for MSW mobile handlers |

**Existing route modifications**:
- `apps/mobile/app/(tabs)/(home)/index.tsx` — add `<CustomerMessagesSectionRow>` below today's schedule section

**New route files**:

| File | Route |
|:---|:---|
| `apps/mobile/app/(tabs)/(home)/inbox/_layout.tsx` | Stack layout for inbox sub-navigation |
| `apps/mobile/app/(tabs)/(home)/inbox/index.tsx` | `CustomerThreadsInboxScreen` — full thread list ("View all") |
| `apps/mobile/app/(tabs)/(home)/inbox/[threadId].tsx` | `ThreadConversationScreen` — full message history + composer |

#### A.3.2 Owner Tab SMS Status Row — `apps/mobile/features/owner-tab/`

| File | Purpose |
|:---|:---|
| `components/SmsUsageStatusSection.tsx` | Wires `useSmsUsageStatus()` to owner tab status row. Shows when usage > 70% per spec Decision 8. Per §16.9 mobile owner status row pattern. |
| `hooks/useSmsUsageStatus.ts` | TanStack Query; `GET /api/v1/sms/quota` (owner-scoped, no `customer_id`); 60s staleTime; returns usage percentage for status row |

**Existing route modified**:
- `apps/mobile/app/(tabs)/owner.tsx` — add `<SmsUsageStatusSection>` when `usagePercent > 70`, below `<FieldIssuesSyncStatusSection>` (FE-B9)

---

### A.4 New Routes

| Route | File | Auth | Role Gate | Notes |
|:---|:---|:---:|:---|:---|
| `/customers/[id]/comms` | `apps/web/src/app/(authed)/customers/[id]/comms/page.tsx` | Required | `owner` / `tech` via `<RoleGate>` | Techs see their threads only; owner sees all threads for this customer |
| `/settings/integrations/sms` | `apps/web/src/app/(authed)/settings/integrations/sms/page.tsx` | Required | `owner` only | SMS number display, quota, cap policy |
| `/settings/integrations/sms/unrouted` | `...sms/unrouted/page.tsx` | Required | `owner` only | Unrouted queue — owner-only operational surface |
| `/settings/integrations/sms/unrouted/[id]` | `...sms/unrouted/[id]/page.tsx` | Required | `owner` only | Assignment form; 404 if unrouted entry not found |
| `/(tabs)/(home)/inbox` | `apps/mobile/app/(tabs)/(home)/inbox/index.tsx` | Required (Cognito) | `tech` only | Full inbox list ("View all" destination) |
| `/(tabs)/(home)/inbox/[threadId]` | `apps/mobile/app/(tabs)/(home)/inbox/[threadId].tsx` | Required (Cognito) | `tech` (own threads) / `owner` (all) | Deep-link entry point from push; supports cold-start |

---

## B — Execution Order

| Step | Item | Rationale |
|:---:|:---|:---|
| 1 | **MSW handlers for all new endpoints** (mobile inbox threads, thread messages, reply POST, quota GET, unrouted GET + assign, customer comms history, dashboard widget, SSE channels) | All surface work requires mocked backends. Write fixtures and MSW before any component. |
| 2 | **`useSegmentCount()` in `packages/ui/`** | Foundational utility; unblocks `<ReplyComposer>` and `<SmsQuotaIndicator>`. No dependencies. |
| 3 | **`<SmsThreadBubble>` + `<SmsOptOutBadge>` + `<SmsQuotaIndicator>` in `packages/ui/`** | Shared visual components; mobile thread screen and web thread view both depend on these. Build before surfaces. |
| 4 | **Mobile inbox list** — `CustomerThreadsInboxScreen` + `ThreadListItem` + `useCustomerThreads` + `useMobileInboxSse` | Tech's primary entry point. Build the list before the detail. SSE live updates proven early. |
| 5 | **Mobile thread screen** — `ThreadConversationScreen` + `ThreadConversationList` + `ThreadHeader` + `useThreadMessages` + `useMarkThreadRead` | Full conversation view. Depends on step 3 (`SmsThreadBubble`). |
| 6 | **Mobile reply composer** — `ReplyComposer` + `useReplyToThread` + `useSmsQuota` + voice dictation path | Core Tier 1.5 deliverable. Composes `usePreviewBeforeSend` (FE-B6 LOCKED) + `useVoiceStream` (FE-B3). |
| 7 | **Quota indicator + warnings** — `SmsQuotaIndicator` wired into composer + `useOptimisticMutation` decrement | Quota UX layer; depends on step 6 composer being in place. |
| 8 | **Push notification loop closure** — `customerMessagePushHandler` + Home screen `CustomerMessagesSectionRow` + unread badge on tab | Closes the inbound loop. Depends on thread screen (step 5) existing as the deep-link target. |
| 9 | **Web Comm history extension** — `CustomerCommsHistoryView` + `CommThreadGroup` + `useCustomerCommsHistory` + SSE | Owner visibility surface. Web-side; can proceed in parallel with steps 6–8. |
| 10 | **Dashboard widget** — `RecentCustomerMessagesWidget` + `useRecentCustomerMessages` | Owner at-a-glance affordance. Thin consumer of A64 endpoint. |
| 11 | **Unrouted message queue** — `UnroutedMessageQueue` + `UnroutedMessageAssignForm` + hooks + route pages + STOP opt-out UX | Edge-case robustness. Last because it has no unblocking dependencies and is lowest-frequency usage path. Also closes out STOP opt-out UX (`SmsOptedOutBanner` + disabled composer on web). |

**Rationale summary**: MSW-first (Rule from methods doc). Shared components before surfaces (Rule 1). Mobile inbox → thread → composer → voice is the natural dependency chain (can't have thread without list; can't have composer without thread context). Web surfaces come after mobile because they are owner-visibility layer, not critical path for the tech-facing deliverable. Unrouted queue last — it's the robustness edge case, not the MVP flow.

---

## C — API Contracts

### C.1 `GET /api/v1/mobile/inbox/customer-threads`

**TanStack Query key**: `['customer-threads', { techId }]`  
**Cache**: `staleTime: 30_000`; `refetchOnWindowFocus`  
**Hook**: `useCustomerThreads()`

**Response** (A66):
```typescript
interface CustomerThreadsResponse {
  threads: SmsThreadListItem[];
  next_cursor: string | null;
  total_unread: number;
}
```

### C.2 `GET /api/v1/communications/threads/{threadId}/messages`

**TanStack Query key**: `['thread-messages', threadId, { page }]`  
**Cache**: `staleTime: 0` (always fresh); cursor-paginated infinite query  
**Hook**: `useThreadMessages(threadId)`

**Request** (query params):
```typescript
interface ThreadMessagesParams {
  cursor?: string;
  limit?: number;   // default: 50
}
```

**Response** (A66):
```typescript
interface ThreadMessagesResponse {
  messages: SmsMessage[];
  next_cursor: string | null;
  thread: SmsThread;
}
```

### C.3 `POST /api/v1/communications/threads/{threadId}/reply`

**Hook**: `useReplyToThread()`  
**Composes**: `useOptimisticMutation()` + `usePreviewBeforeSend()` free-form path

**Request** (A62):
```typescript
interface SmsReplyRequest {
  body: string;
  composition_method: 'free_form_text' | 'free_form_voice';
  voice_audio_id?: string;   // UUID — only for voice-dictated replies
}
```

**Optimistic update**: Add optimistic `SmsMessage` with `status: 'pending_send'` to `['thread-messages', threadId]` cache before server confirms. `<PendingBadge variant="sending">` shown until server response.

**Response** (A62):
```typescript
interface SmsReplyResponse {
  message_id: string;
  thread_id: string;
  status: 'pending_send' | 'sent';
  segment_count: number;
  sent_at: string | null;
}
```

**Error responses**:
- `422 { detail: 'customer_opted_out' }` → surface opted-out error banner
- `429 { detail: 'monthly_quota_reached' }` → surface hard-cap error banner (soft cap does NOT block)
- `409` → `useStalenessRetry` pattern (thread state changed; refresh and retry)

### C.4 `GET /api/v1/sms/quota`

**TanStack Query key**: `['sms-quota', { customerId? }]`  
**Cache**: `staleTime: 60_000`; refetchOnWindowFocus  
**Hook**: `useSmsQuota({ customerId? })`

**Request** (query params):
```typescript
interface SmsQuotaParams {
  customer_id?: string;   // when provided, also checks opt-out status for that customer
}
```

**Response** (A65):
```typescript
interface SmsQuotaStatus {
  period_id: string;
  used_segments: number;
  included_segments: number;
  remaining_segments: number;
  overage_segments: number;
  cap_policy: 'soft' | 'hard';
  period_start: string;   // ISO date
  period_end: string;     // ISO date
  blocked_reason: 'customer_opted_out' | 'monthly_quota_reached' | null;
  projected_month_end_segments: number;   // for web owner widget
}
```

### C.5 `POST /api/v1/communications/threads/{threadId}/mark-read`

**Hook**: `useMarkThreadRead()`  
**Cache invalidation**: `['customer-threads']` on success (unread count decrements)

**Response**:
```typescript
interface MarkReadResponse {
  thread_id: string;
  marked_read_count: number;
}
```

### C.6 `GET /api/v1/customers/{customerId}/communication-history`

**TanStack Query key**: `['customer-comms-history', customerId]`  
**Cache**: `staleTime: 30_000`  
**Hook**: `useCustomerCommsHistory(customerId)`

**Response** (A64):
```typescript
interface CustomerCommsHistoryResponse {
  threads: SmsThread[];   // each thread contains messages[]
  customer_opted_out: boolean;
  opted_out_at: string | null;
}
```

### C.7 `GET /api/v1/dashboard/widgets/recent-customer-messages`

**TanStack Query key**: `['dashboard-widget-recent-messages', { limit }]`  
**Cache**: `staleTime: 30_000`  
**Hook**: `useRecentCustomerMessages({ limit: 10 })`

**Request** (query params):
```typescript
interface RecentCustomerMessagesParams {
  limit?: number;   // default: 10
}
```

**Response** (A64):
```typescript
interface RecentCustomerMessagesResponse {
  messages: RecentCustomerMessage[];
}

interface RecentCustomerMessage {
  message_id: string;
  thread_id: string;
  customer_id: string;
  customer_name: string;
  direction: 'outbound' | 'inbound';
  body_preview: string;   // first 80 chars
  received_at: string;
  tech_name: string | null;
}
```

### C.8 `GET /api/v1/communications/unrouted`

**TanStack Query key**: `['unrouted-messages', { cursor, limit }]`  
**Cache**: `staleTime: 30_000`  
**Hook**: `useUnroutedMessages()`

**Response** (A60):
```typescript
interface UnroutedMessagesResponse {
  messages: UnroutedMessage[];
  next_cursor: string | null;
  total_count: number;
}
```

### C.9 `POST /api/v1/communications/unrouted/{id}/assign`

**Hook**: `useAssignUnrouted()`

**Request** (A60):
```typescript
interface UnroutedAssignRequest {
  customer_id: string;
  tech_id: string;
}
```

**Response**:
```typescript
interface UnroutedAssignResponse {
  thread_id: string;
  message_id: string;
  customer_name: string;
  tech_name: string;
}
```

### C.10 SSE Channels

| Surface | Channel path | Events | Handler |
|:---|:---|:---|:---|
| Mobile inbox (live updates) | `/api/v1/mobile/inbox/stream` | `customer_message_received`, `thread_read` | Invalidate `['customer-threads']`; append message to `['thread-messages', threadId]` |
| Web customer comms history | `/api/v1/customers/{customerId}/comms/stream` | `customer_message_received` | Invalidate `['customer-comms-history', customerId]` |
| Web dashboard widget | `/api/v1/dashboard/stream` | `customer_message_received` | Invalidate `['dashboard-widget-recent-messages']` |

Mobile SSE uses `useSseChannel` with `eventSourceFactory` = `react-native-sse` instance. All channels use `fallbackToPollingMs: 60_000`.

---

## D — State Management

### D.1 `CustomerThreadsInboxScreen` (Mobile)

| State | Location | Notes |
|:---|:---|:---|
| Thread list | TanStack Query `['customer-threads']` | 30s staleTime; SSE invalidates |
| Live SSE connection | `useMobileInboxSse` internal | Auto-invalidates thread list |
| Unread total badge | Derived from `threads.reduce(sum unread_count)` | Used for Home tab `tabBarBadge` |

### D.2 `ThreadConversationScreen` (Mobile)

| State | Location | Notes |
|:---|:---|:---|
| Thread messages | TanStack Query infinite `['thread-messages', threadId]` | 0s staleTime; paginated |
| Thread metadata | Part of `ThreadMessagesResponse.thread` | Includes `customer.sms_opted_out` |
| Optimistic sent messages | Injected via `useOptimisticMutation` | `status: 'pending_send'` until confirmed |
| Mark-read on mount | `useMarkThreadRead` fires on screen focus | Invalidates `['customer-threads']` |

### D.3 `ReplyComposer` (Mobile)

| State | Location | Notes |
|:---|:---|:---|
| Compose text | `useState<string>('')` | Local; updated by voice transcription or keyboard |
| Voice state machine | `useState<VoiceDictationState>` | See state machine below |
| Quota | TanStack Query `['sms-quota', { customerId }]` | 60s staleTime; optimistic decrement on send |
| Segment count | `useSegmentCount(text)` | Derived; updates on text change |
| Send in progress | `isSending` from `usePreviewBeforeSend()` | Disables send button |
| Preview modal | `isModalOpen` from `usePreviewBeforeSend()` | Controls `MessagePreviewModal` visibility |

### D.4 Voice Dictation State Machine (Mobile Composer)

```typescript
type VoiceDictationState =
  | { phase: 'idle' }
  | { phase: 'recording' }
  | { phase: 'transcribing' }
  | { phase: 'transcribed'; transcript: string }
  | { phase: 'error'; error: string };
```

Transitions:
- `idle → recording`: mic button pressed, `startDictating()` called
- `recording → transcribing`: mic released, Whisper processing
- `transcribing → transcribed`: Whisper returns transcript; text inserted into composer field
- `transcribed → idle`: tech edits or sends; state resets
- `* → error`: any Whisper failure; `NotificationBanner severity="warning"` shown

### D.5 Quota State Machine

```typescript
type QuotaVisualState =
  | { state: 'normal'; remaining: number; included: number }
  | { state: 'warning'; remaining: number; included: number }
  | { state: 'blocked_soft'; used: number; included: number }
  | { state: 'blocked_hard'; used: number; included: number }
  | { state: 'opted_out' };

function deriveQuotaState(quota: SmsQuotaStatus): QuotaVisualState
```

- `opted_out`: when `blocked_reason === 'customer_opted_out'`
- `blocked_hard`: when `blocked_reason === 'monthly_quota_reached'` AND `cap_policy === 'hard'`
- `blocked_soft`: when `remaining === 0` AND `cap_policy === 'soft'`
- `warning`: when `remaining > 0` AND `remaining / included ≤ 0.2`
- `normal`: all other states

### D.6 Optimistic Send State Machine

```
tech taps Send in MessagePreviewModal
  → useOptimisticMutation.mutate(replyRequest)
  → onMutate: inject SmsMessage{ status: 'pending_send' } into ['thread-messages'] cache
              decrement ['sms-quota'].remaining_segments by estimated segmentCount
  → POST /threads/{threadId}/reply
  → onSuccess: replace optimistic message with server response (status: 'sent')
               invalidate ['sms-quota'] to fetch actual remaining
  → onError: remove optimistic message; rollback quota snapshot
             surface NotificationBanner severity="error" with error copy
```

`<PendingBadge variant="sending">` shown on the optimistic bubble until `status` transitions out of `pending_send`.

### D.7 SSE → Cache Invalidation Flow (Mobile)

```
Telnyx inbound SMS arrives → BE webhook → route_inbound_message()
  → push notification dispatched to tech
  → SSE event 'customer_message_received' emitted on /api/v1/mobile/inbox/stream
  → useMobileInboxSse onMessage fires
  → queryClient.invalidateQueries(['customer-threads'])
  → if ThreadConversationScreen open for this thread:
      queryClient.invalidateQueries(['thread-messages', threadId])
      → new message appears in FlatList
```

---

## E — Error States

### E.1 Customer Opted-Out Block

**Trigger**: `SmsQuotaStatus.blocked_reason === 'customer_opted_out'`  
**Component**: `<ReplyComposer>` (mobile) or `<SmsOptedOutBanner>` (web)  
**User sees**: Send button disabled. Fault-color banner:  
> `"Customer has opted out — they cannot be reached via SMS"`  
**Token**: `bg-fault-50 border-fault-200 text-fault-700`  
**Thread header**: `<SmsOptOutBadge>` chip shown with opt-out date

### E.2 Hard Cap Quota Block (Monthly Limit)

**Trigger**: `blocked_reason === 'monthly_quota_reached'` AND `cap_policy === 'hard'`  
**User sees**: Send button disabled. Fault-color banner:  
> `"Monthly SMS limit reached — contact your owner to adjust your plan"`  
**Token**: `bg-fault-50 border-fault-200 text-fault-700`  
**`SmsQuotaIndicator`** state: `blocked_hard`

### E.3 Soft Cap Quota Warning (Overage Will Be Billed)

**Trigger**: `remaining === 0` AND `cap_policy === 'soft'`  
**User sees**: Send button **enabled**. Amber warning in `<SmsQuotaIndicator>`:  
> `"Monthly quota reached — overages billed at $0.05/segment"`  
**Token**: `bg-alert-50 border-alert-200 text-alert-700`

### E.4 80% Quota Warning

**Trigger**: `remaining / included ≤ 0.2` AND `remaining > 0`  
**User sees**: Amber annotation in `<SmsQuotaIndicator>` in composer footer:  
> `"⚠ N segments left this month"`  
**Token**: `text-alert-600`; no banner — subtle footer annotation only

### E.5 Delivery Failure (Telnyx Returns Non-Delivered)

**Trigger**: After optimistic send, server confirms `status: 'failed'`  
**User sees**: Optimistic bubble transitions to error state via `<PendingBadge variant="failed">`. `NotificationBanner severity="error"`:  
> `"Message delivery failed — tap to retry"`  
**Token**: `bg-fault-50 text-fault-700`  
**Retry**: tapping the notification re-opens the composer with the same body pre-filled

### E.6 Network Error During Send

**Trigger**: `useReplyToThread` mutation fails with network error  
**User sees**: Optimistic bubble removed. `NotificationBanner severity="warning"`:  
> `"Couldn't send — check your connection and try again"`  
**Token**: `bg-alert-50 text-alert-700`  
Composer retains the typed text (not cleared on failure)

### E.7 Voice Transcription Failure

**Trigger**: `useVoiceDictation` enters `{ phase: 'error' }`  
**User sees**: Mic button returns to idle. `NotificationBanner severity="warning"`:  
> `"Voice transcription failed — type your message instead"`  
**Token**: `bg-alert-50 text-alert-700`  
**Fallback**: composer `TextInput` gains focus automatically

### E.8 Unrouted Message Alert (Owner)

**Trigger**: `customer_message_unrouted` SSE event or push notification  
**User sees**: In-app `NotificationBanner severity="info"` (web):  
> `"A customer texted but we couldn't match them to a conversation — [Review →]"`  
`deepLinkTarget`: `/settings/integrations/sms/unrouted`  
**Token**: `bg-neutral-50 border-neutral-200 text-neutral-700`

### E.9 STOP Keyword Received (Owner Notification)

**Trigger**: `customer_sms_opt_out` push notification to owner  
**User sees**: Push notification: *"John Smith has opted out of SMS"*  
In-app banner (web): `"John Smith has opted out — they won't receive SMS"`  
**Token**: `bg-fault-50 text-fault-700`

### E.10 Offline Send Attempt

**Trigger**: Tech taps mic or Send button while `!navigator.onLine`  
**User sees**: `NotificationBanner severity="warning"`:  
> `"No internet — messages require a connection to send"`  
Send button disabled while offline. Composer stays open; text preserved.

### E.11 Empty States

| Surface | Trigger | Copy |
|:---|:---|:---|
| Mobile inbox (no threads) | `threads.length === 0` | "No customer messages yet. When customers reply, they'll appear here." |
| Mobile thread (no messages) | `messages.length === 0` | "Conversation started. Your messages will appear here." |
| Web comm history (no history) | Empty threads array | "No communication history for this customer." |
| Unrouted queue (empty) | `messages.length === 0` | "No unrouted messages. All customer texts have been matched successfully." |

**Token**: `text-neutral-500` for empty state descriptions

---

## F — TypeScript Interfaces

### F.1 `SmsThread`

```typescript
/**
 * A conversation thread keyed by (tenant_id × customer_id × tech_id × tenant_phone_number_id).
 * Canonical type for Phase 2 SMS features. DO NOT extend without impact review.
 */
export interface SmsThread {
  thread_id: string;
  tenant_id: string;
  customer_id: string;
  customer_name: string;
  customer_phone: string;      // E.164 format; display-only (never used to dial)
  customer_sms_opted_out: boolean;
  customer_opted_out_at: string | null;
  tech_id: string;
  tech_name: string;
  tenant_phone_number_id: string;
  status: 'active' | 'archived';
  first_message_at: string;
  last_message_at: string;
  message_count: number;
  unread_count: number;
  originating_job_id: string | null;
  originating_job_display: string | null;  // "Job #1042 — Panel Upgrade"
  created_at: string;
  updated_at: string;
  messages: SmsMessage[];
}
```

### F.2 `SmsMessage`

```typescript
/**
 * A single message within a thread.
 * Canonical type for Phase 2 SMS features. DO NOT extend without impact review.
 */
export interface SmsMessage {
  message_id: string;
  thread_id: string;
  direction: 'outbound' | 'inbound';
  channel: 'sms';                     // MMS is Phase 2
  body: string;
  segment_count: number;
  status: 'pending_send' | 'sent' | 'delivered' | 'failed' | 'received';
  carrier_message_id: string | null;
  composition_method: 'template' | 'free_form_text' | 'free_form_voice';
  template_id: string | null;
  voice_audio_id: string | null;
  sent_at: string | null;
  delivered_at: string | null;
  received_at: string | null;
  audit_user_id: string;             // tech who sent or was routed to
}
```

### F.3 `SmsReplyRequest`

```typescript
export interface SmsReplyRequest {
  body: string;
  composition_method: 'free_form_text' | 'free_form_voice';
  voice_audio_id?: string;
}
```

### F.4 `SmsQuotaStatus`

```typescript
export interface SmsQuotaStatus {
  period_id: string;
  used_segments: number;
  included_segments: number;
  remaining_segments: number;
  overage_segments: number;
  cap_policy: 'soft' | 'hard';
  period_start: string;
  period_end: string;
  blocked_reason: 'customer_opted_out' | 'monthly_quota_reached' | null;
  projected_month_end_segments: number;
}
```

### F.5 `SmsQuotaIndicatorProps`

```typescript
/**
 * Location: packages/ui/src/sms-quota-indicator/SmsQuotaIndicator.tsx
 * Mobile only (Gluestack primitives). Web quota shown in owner settings surface.
 */
export interface SmsQuotaIndicatorProps {
  quota: SmsQuotaStatus;
  currentMessageSegmentCount: number;   // from useSegmentCount — for real-time preview
  isLoading?: boolean;
  testID?: string;
}
```

### F.6 `SmsThreadBubbleProps`

```typescript
/**
 * Location: packages/ui/src/sms-thread-bubble/SmsThreadBubble.tsx
 * Polymorphic: web/mobile variants per DiffView pattern from FE-B5.
 */
export interface SmsThreadBubbleProps {
  message: SmsMessage;
  /** Whether this bubble is from the perspective of the current user */
  isOwnMessage: boolean;
  showTimestamp?: boolean;
  showDeliveryStatus?: boolean;
  /** True for optimistic messages not yet confirmed by server */
  isPending?: boolean;
  testID?: string;
}
```

### F.7 `SmsThreadListItem`

```typescript
export interface SmsThreadListItem {
  thread_id: string;
  customer_id: string;
  customer_name: string;
  last_message_preview: string;    // first 50 chars of last message body
  last_message_at: string;
  last_message_direction: 'outbound' | 'inbound';
  unread_count: number;
  originating_job_id: string | null;
  originating_job_display: string | null;
  customer_sms_opted_out: boolean;
}
```

### F.8 `UnroutedMessage`

```typescript
export interface UnroutedMessage {
  unrouted_id: string;
  tenant_id: string;
  from_number: string;          // masked for display: "+1 (555) ***-1234"
  to_number: string;            // tenant's Telnyx number
  body: string;
  received_at: string;
  attempted_customer_match: string | null;  // best-guess from threading attempt
}
```

### F.9 `SegmentCountResult`

```typescript
/**
 * Location: packages/ui/src/hooks/useSegmentCount.ts
 * Canonical SMS segment count result.
 */
export interface SegmentCountResult {
  segmentCount: number;
  encoding: 'gsm7' | 'unicode';
  charCount: number;
  charsPerSegment: number;
  charsRemaining: number;        // chars until next segment boundary
}
```

### F.10 `VoiceDictationState`

```typescript
/**
 * Location: apps/mobile/features/customer-comms/hooks/useVoiceDictation.ts
 * State machine for single-utterance voice transcription in the reply composer.
 */
export type VoiceDictationState =
  | { phase: 'idle' }
  | { phase: 'recording' }
  | { phase: 'transcribing' }
  | { phase: 'transcribed'; transcript: string }
  | { phase: 'error'; error: string };

export interface UseVoiceDictationReturn {
  state: VoiceDictationState;
  startDictating: () => void;
  stopDictating: () => void;
  reset: () => void;
}
```

### F.11 `QuotaVisualState`

```typescript
/**
 * Derived quota display state for <SmsQuotaIndicator>.
 * Computed by deriveQuotaState() utility — export from packages/ui.
 */
export type QuotaVisualState =
  | { state: 'normal'; remaining: number; included: number }
  | { state: 'warning'; remaining: number; included: number }
  | { state: 'blocked_soft'; used: number; included: number }
  | { state: 'blocked_hard'; used: number; included: number }
  | { state: 'opted_out' };
```

### F.12 `SmsOptOutBadgeProps`

```typescript
/**
 * Location: packages/ui/src/sms-opt-out-badge/SmsOptOutBadge.tsx
 */
export interface SmsOptOutBadgeProps {
  optedOutAt: string | null;    // ISO date; null → "opted out" without date
  compact?: boolean;            // compact = no date shown (for tight headers)
  testID?: string;
}
```

---

## G — Test Plan

### G.1 Unit Tests (target: 80+)

**`packages/ui/src/hooks/useSegmentCount.ts`**

| Test | File |
|:---|:---|
| Single GSM-7 segment: 160 chars → segmentCount=1, encoding='gsm7' | `useSegmentCount.test.ts` |
| GSM-7 boundary: 161 chars → segmentCount=2, charsPerSegment=153 | `useSegmentCount.test.ts` |
| Multi-segment GSM-7: 306 chars → segmentCount=2 (306/153 = 2) | `useSegmentCount.test.ts` |
| Single Unicode segment: 70 chars with emoji → segmentCount=1, encoding='unicode' | `useSegmentCount.test.ts` |
| Unicode boundary: 71 chars → segmentCount=2, charsPerSegment=67 | `useSegmentCount.test.ts` |
| Empty string → segmentCount=1, charCount=0 | `useSegmentCount.test.ts` |
| Extended GSM-7 char `€` counts as 2 code units → GSM-7 encoding retained | `useSegmentCount.test.ts` |
| Mixed ASCII + emoji → encoding='unicode' (emoji forces Unicode) | `useSegmentCount.test.ts` |
| `charsRemaining` correct at single-segment boundary | `useSegmentCount.test.ts` |
| `charsRemaining` correct at multi-segment boundary | `useSegmentCount.test.ts` |

**`packages/ui/src/sms-quota-indicator/`**

| Test | File |
|:---|:---|
| `state='normal'` renders remaining count in neutral text | `SmsQuotaIndicator.test.tsx` |
| `state='warning'` renders amber "⚠ N segments left" | `SmsQuotaIndicator.test.tsx` |
| `state='blocked_soft'` renders fault-color overage-billed message | `SmsQuotaIndicator.test.tsx` |
| `state='blocked_hard'` renders fault-color limit-reached message; send button disabled | `SmsQuotaIndicator.test.tsx` |
| `state='opted_out'` renders opted-out copy | `SmsQuotaIndicator.test.tsx` |
| `currentMessageSegmentCount` updates preview copy in real-time | `SmsQuotaIndicator.test.tsx` |

**`packages/ui/src/sms-thread-bubble/`**

| Test | File |
|:---|:---|
| `direction='outbound'` renders right-aligned brand-indigo bubble | `SmsThreadBubble.test.tsx` |
| `direction='inbound'` renders left-aligned neutral bubble | `SmsThreadBubble.test.tsx` |
| `status='pending_send'` renders `<PendingBadge variant="sending">` | `SmsThreadBubble.test.tsx` |
| `status='delivered'` renders delivery confirmation icon | `SmsThreadBubble.test.tsx` |
| `status='failed'` renders `<PendingBadge variant="failed">` | `SmsThreadBubble.test.tsx` |
| `showTimestamp=true` renders formatted relative timestamp | `SmsThreadBubble.test.tsx` |
| `isPending=true` renders with pending opacity treatment | `SmsThreadBubble.test.tsx` |

**`packages/ui/src/sms-opt-out-badge/`**

| Test | File |
|:---|:---|
| Non-null `optedOutAt` renders "SMS opted out · [date]" | `SmsOptOutBadge.test.tsx` |
| `optedOutAt=null` renders "SMS opted out" (no date) | `SmsOptOutBadge.test.tsx` |
| `compact=true` omits date | `SmsOptOutBadge.test.tsx` |

**`apps/mobile/features/customer-comms/`**

| Test | File |
|:---|:---|
| `ThreadListItem` renders customer name, preview, unread badge | `components/ThreadListItem.test.tsx` |
| `ThreadListItem` with `unread_count=0` renders no badge | `components/ThreadListItem.test.tsx` |
| `ThreadListItem` opted-out thread shows opt-out indicator | `components/ThreadListItem.test.tsx` |
| `CustomerMessagesSectionRow` renders up to 5 threads | `components/CustomerMessagesSectionRow.test.tsx` |
| `CustomerMessagesSectionRow` with `total_unread > 0` renders count badge | `components/CustomerMessagesSectionRow.test.tsx` |
| `ThreadHeader` renders customer name and job context | `components/ThreadHeader.test.tsx` |
| `ThreadHeader` renders `<SmsOptOutBadge>` when opted out | `components/ThreadHeader.test.tsx` |
| `ReplyComposer` send button enabled when text non-empty | `components/ReplyComposer.test.tsx` |
| `ReplyComposer` send button disabled when text empty | `components/ReplyComposer.test.tsx` |
| `ReplyComposer` send button disabled when `quota.state === 'blocked_hard'` | `components/ReplyComposer.test.tsx` |
| `ReplyComposer` send button disabled when opted out | `components/ReplyComposer.test.tsx` |
| `ReplyComposer` mic button transitions to recording state on press | `components/ReplyComposer.test.tsx` |
| `useVoiceDictation` state machine: idle → recording → transcribed | `hooks/useVoiceDictation.test.ts` |
| `useVoiceDictation` error state on Whisper failure | `hooks/useVoiceDictation.test.ts` |
| `useCustomerThreads` constructs correct query key | `hooks/useCustomerThreads.test.ts` |
| `useReplyToThread` optimistic message injected into cache before server response | `hooks/useReplyToThread.test.ts` |
| `useReplyToThread` optimistic message removed on error; quota rolled back | `hooks/useReplyToThread.test.ts` |
| `useSmsQuota` derives `blocked_reason='customer_opted_out'` correctly | `hooks/useSmsQuota.test.ts` |
| `deriveQuotaState` all five states from quota fixture values | `hooks/useSmsQuota.test.ts` |

**`apps/web/src/features/customer-comms/`**

| Test | File |
|:---|:---|
| `CustomerCommsHistoryView` renders outbound bubbles right-aligned | `components/CustomerCommsHistoryView.test.tsx` |
| `CustomerCommsHistoryView` renders inbound bubbles left-aligned | `components/CustomerCommsHistoryView.test.tsx` |
| `CustomerCommsHistoryView` groups messages by thread | `components/CustomerCommsHistoryView.test.tsx` |
| `SmsOptedOutBanner` renders fault-color opted-out banner | `components/SmsOptedOutBanner.test.tsx` |
| `CommThreadGroup` expands/collapses thread on header click | `components/CommThreadGroup.test.tsx` |

**`apps/web/src/features/sms-unrouted/`**

| Test | File |
|:---|:---|
| `UnroutedMessageRow` renders masked phone, preview, timestamp | `components/UnroutedMessageRow.test.tsx` |
| `UnroutedMessageAssignForm` customer search populates tech dropdown | `components/UnroutedMessageAssignForm.test.tsx` |
| `UnroutedMessageAssignForm` submit disabled until both customer + tech selected | `components/UnroutedMessageAssignForm.test.tsx` |
| `useAssignUnrouted` invalidates `['unrouted-messages']` on success | `hooks/useAssignUnrouted.test.ts` |

**`apps/web/src/features/dashboard/`**

| Test | File |
|:---|:---|
| `RecentCustomerMessagesWidget` renders last 10 messages sorted by recency | `components/RecentCustomerMessagesWidget.test.tsx` |
| `RecentCustomerMessagesWidget` outbound rows styled brand-indigo | `components/RecentCustomerMessagesWidget.test.tsx` |
| `RecentCustomerMessagesWidget` inbound rows styled neutral | `components/RecentCustomerMessagesWidget.test.tsx` |

### G.2 Integration Tests (target: 18+)

**Location**: `apps/{web,mobile}/__tests__/batch_fe_b10/`

| Test | File |
|:---|:---|
| Full inbound SMS flow: MSW delivers `customer_message_received` SSE → thread list updates → unread badge appears | `mobile-inbox-sse-live-update.integration.test.tsx` |
| Full mobile reply (touch path): composer text → preview modal → confirm → `POST /reply` → message appears in thread | `mobile-reply-touch-path.integration.test.tsx` |
| Full mobile reply (voice path): mic tap → MSW returns transcript → text in field → preview → confirm → send | `mobile-reply-voice-path.integration.test.tsx` |
| Quota at 80%: `GET /sms/quota` returns warning threshold → amber indicator shown in composer | `mobile-quota-warning.integration.test.tsx` |
| Quota at 100% hard cap: `GET /sms/quota` returns blocked_hard → send button disabled, fault banner shown | `mobile-quota-hard-block.integration.test.tsx` |
| Quota at 100% soft cap: `GET /sms/quota` returns blocked_soft → send button ENABLED, overage warning shown | `mobile-quota-soft-cap.integration.test.tsx` |
| Customer opted out: `GET /sms/quota?customer_id=X` returns `opted_out` → send disabled + opted-out copy | `mobile-opted-out-block.integration.test.tsx` |
| Push notification deep-link: `customer_message` push → cold-start → navigates to `ThreadConversationScreen` | `mobile-push-deep-link.integration.test.tsx` |
| STOP opt-out end-to-end: customer sends STOP → customer record updated → next quota check returns opted_out | `mobile-stop-opt-out.integration.test.tsx` |
| Optimistic UI: reply dispatched → pending bubble appears → server confirms → pending badge clears | `mobile-optimistic-send.integration.test.tsx` |
| Optimistic failure: server returns 422 → optimistic bubble removed → composer retains text | `mobile-optimistic-failure.integration.test.tsx` |
| Web comm history: `GET /customers/{id}/communication-history` → threads rendered with correct bubble directions | `web-comm-history-render.integration.test.tsx` |
| Web SSE: `customer_message_received` event → comm history invalidated → new message appears | `web-comm-history-sse.integration.test.tsx` |
| Web dashboard widget: `GET /dashboard/widgets/recent-customer-messages` → 10 rows rendered | `web-dashboard-widget.integration.test.tsx` |
| Unrouted message assignment: assign form submit → `POST /unrouted/{id}/assign` → entry removed from queue | `web-unrouted-assign.integration.test.tsx` |
| RBAC: tech accesses `/customers/[id]/comms` → sees only own threads | `web-comms-rbac.integration.test.tsx` |
| RBAC: owner accesses `/customers/[id]/comms` → sees all threads for customer | `web-comms-owner-rbac.integration.test.tsx` |
| Segment counter real-time: type 160 chars → segmentCount=1; type 161st → segmentCount=2 | `web-segment-counter-boundary.integration.test.tsx` |

**MSW handlers required** (new files):
- `apps/mobile/src/mocks/handlers/communicationsHandlers.ts`
  - `GET /api/v1/mobile/inbox/customer-threads` (list with unread, empty, opted-out thread variants)
  - `GET /api/v1/communications/threads/:threadId/messages` (paginated, single page)
  - `POST /api/v1/communications/threads/:threadId/reply` (success, 422-opted-out, 429-hard-cap, 422-soft-cap-allowed)
  - `POST /api/v1/communications/threads/:threadId/mark-read`
  - `GET /api/v1/sms/quota` (normal, warning-80, blocked-hard, blocked-soft, opted-out)
  - `GET /api/v1/mobile/inbox/stream` (SSE)
- `apps/web/src/mocks/handlers/customerCommsHandlers.ts`
  - `GET /api/v1/customers/:customerId/communication-history` (multi-thread, opted-out, empty)
  - `GET /api/v1/dashboard/widgets/recent-customer-messages`
  - `GET /api/v1/communications/unrouted`
  - `POST /api/v1/communications/unrouted/:id/assign` (success, 404-not-found)
  - `GET /api/v1/customers/:customerId/comms/stream` (SSE)
  - `GET /api/v1/dashboard/stream` (SSE)

**Required fixtures**:
- `customerCommsFixtures.ts` (mobile): 3-thread inbox list; single thread with 10 messages (mix outbound/inbound); opted-out customer; quota at normal / 80% / 100%-hard / 100%-soft / opted-out
- `customerCommsFixtures.ts` (web): customer comms history with 2 threads (different techs); dashboard widget 10 messages; unrouted queue with 2 entries

### G.3 E2E Tests (target: 5+)

**Location**: `e2e/mobile/batch_fe_b10/` and `e2e/web/batch_fe_b10/`

| Test | File |
|:---|:---|
| Full SMS round-trip: `MockSmsCarrier` → inbound lands → push fires → tech taps → thread opens → tech replies → message confirmed | `e2e/mobile/batch_fe_b10/sms-round-trip.e2e.yaml` |
| Voice-to-text full flow: tap mic on real device → speak phrase → transcript in field → preview → send | `e2e/mobile/batch_fe_b10/voice-reply.e2e.yaml` |
| STOP handling end-to-end: customer texts STOP → opted_out status → next reply attempt blocked (mobile) | `e2e/mobile/batch_fe_b10/stop-opt-out.e2e.yaml` |
| Multi-tenant isolation: tenant A threads not visible to tenant B on web | `e2e/web/batch_fe_b10/multi-tenant-isolation.e2e.spec.ts` |
| Unrouted message full assignment: inbound to unknown number → unrouted queue → owner assigns → thread created | `e2e/web/batch_fe_b10/unrouted-assign-round-trip.e2e.spec.ts` |

---

## H — Token Audit

Every color, spacing, and typography value traces to a token from `packages/ui/src/tokens.ts`. No hex values or raw pixel values in component code.

### H.1 Color Tokens

| Usage | Tailwind class (web) / Token reference (mobile) | Token | Notes |
|:---|:---|:---|:---|
| Outbound message bubble | `bg-brand-600 text-neutral-50` | `colors.brand[600]`, `colors.neutral[50]` | Right-aligned; tech-sent |
| Inbound message bubble | `bg-neutral-100 text-neutral-900` | `colors.neutral[100]`, `colors.neutral[900]` | Left-aligned; customer-sent |
| Quota indicator normal text | `text-neutral-500` | `colors.neutral[500]` | Subdued; normal state |
| Quota warning amber | `bg-alert-50 border-alert-200 text-alert-600` | `colors.alert[50]`, `colors.alert[200]`, `colors.alert[600]` | 80% threshold |
| Quota blocked (soft + hard) | `bg-fault-50 border-fault-200 text-fault-700` | `colors.fault[50]`, `colors.fault[200]`, `colors.fault[700]` | 100% or opted-out |
| Opted-out badge background | `bg-fault-50 border-fault-200 text-fault-700` | Same fault ramp | Thread header chip |
| Opted-out banner | `bg-fault-50 border-fault-200 text-fault-700` | Same fault ramp | Composer + web banner |
| `<PendingBadge variant="sending">` | `bg-neutral-200 text-neutral-500` | `colors.neutral[200]`, `colors.neutral[500]` | Pending send state |
| `<PendingBadge variant="failed">` | `bg-fault-100 text-fault-700` | `colors.fault[100]`, `colors.fault[700]` | Failed send state |
| Delivered status icon | `text-margin-600` | `colors.margin[600]` | Green checkmark |
| Voice CTA panel (composer mic area) | `bg-alert-50 border-alert-200` | `colors.alert[50]`, `colors.alert[200]` | Matches FE-B6 voice CTA style |
| Unrouted notification banner | `bg-neutral-50 border-neutral-200 text-neutral-700` | `colors.neutral[50]`, `colors.neutral[200]`, `colors.neutral[700]` | Info severity |
| SMS owner status row healthy dot | `bg-margin-500` | `colors.margin[500]` | Green = within quota |
| SMS owner status row warning dot | `bg-alert-500` | `colors.alert[500]` | Amber = 80%+ usage |
| SMS owner status row blocked dot | `bg-fault-500` | `colors.fault[500]` | Red = hard cap reached |
| Thread group header | `bg-neutral-50 border-b border-neutral-200` | `colors.neutral[50]`, `colors.neutral[200]` | Collapsible section header |
| Empty state description | `text-neutral-500` | `colors.neutral[500]` | All empty state body text |
| Dashboard widget direction indicator (outbound) | `text-brand-600` | `colors.brand[600]` | Outbound direction pill |
| Dashboard widget direction indicator (inbound) | `text-neutral-500` | `colors.neutral[500]` | Inbound direction pill |

### H.2 Spacing Tokens

All `padding`, `margin`, `gap` values use Tailwind spacing scale from pilot preset only — no raw pixel values.

| Usage | Class (web) / `spacing[N]` (mobile) | Token |
|:---|:---|:---|
| Thread bubble padding | `px-4 py-3` / `spacing[4]`, `spacing[3]` | `spacing[4]`, `spacing[3]` |
| Composer zone padding | `px-4 py-3` / `spacing[4]`, `spacing[3]` | `spacing[4]`, `spacing[3]` |
| Quota indicator footer padding | `px-4 py-2` / `spacing[4]`, `spacing[2]` | `spacing[4]`, `spacing[2]` |
| Thread list item padding | `px-4 py-3` / `spacing[4]`, `spacing[3]` | `spacing[4]`, `spacing[3]` |
| Bubble gap between consecutive messages | `space-y-2` / `gap: spacing[2]` | `spacing[2]` |
| Inbox section gap | `space-y-3` / `gap: spacing[3]` | `spacing[3]` |
| Unrouted queue row padding | `px-4 py-3` | `spacing[4]`, `spacing[3]` |
| Dashboard widget row padding | `px-4 py-3` | `spacing[4]`, `spacing[3]` |

### H.3 Typography Tokens

| Usage | Class | Token |
|:---|:---|:---|
| Thread screen customer name (header) | `text-h3 font-medium` | `fontSizes.h3`, `fontWeights.medium` |
| Message bubble body | `text-body` | `fontSizes.body` |
| Timestamp / meta text | `text-caption` | `fontSizes.caption` |
| Quota indicator annotation | `text-caption` | `fontSizes.caption` |
| Thread list item preview text | `text-body` (truncated 1 line) | `fontSizes.body` |
| Thread list item customer name | `text-body font-medium` | `fontSizes.body`, `fontWeights.medium` |
| Unread count badge number | `text-caption font-semibold` | `fontSizes.caption`, `fontWeights.semibold` |
| Opted-out badge text | `text-caption font-medium` | `fontSizes.caption`, `fontWeights.medium` |

### H.4 Token Gaps Flagged

No token gaps identified. All design values used in this batch trace to existing tokens in `tokens.ts`.

**Note on bubble direction**: outbound uses `brand-600` fill (right-aligned, tech-sent); inbound uses `neutral-100` fill (left-aligned, customer-sent). This is the standard messaging app visual grammar. Both are within the existing token ramp — no new tokens required.

**Note on opted-out**: uses `fault-*` ramp consistently for both the badge chip and the composer banner. This is semantically correct — opt-out is an error state that blocks functionality, not a warning.

---

## I — Downstream Contract Lock

### I.1 FE-B10 Has No Downstream Batch Dependents

FE-B10 is the last cross-platform batch before the settings work (FE-B11). No subsequent batch in the 17-batch plan depends on FE-B10's shared components or interfaces. However, the following types and components are **canonical** and will be reused directly by Phase 2 SMS features without modification:

### I.2 Types Locked as Canonical for Phase 2

The following interfaces are locked after FE-B10 ships. Phase 2 SMS features **must not redefine them** — they import and extend.

| Type | File | Phase 2 Usage |
|:---|:---|:---|
| `SmsThread` | `packages/ui/src/sms-thread-bubble/types.ts` (or collocated) | Thread archiving, MMS, per-tech numbers — all extend `SmsThread` |
| `SmsMessage` | Same | MMS adds `media_urls?: string[]`; AI replies add `ai_suggested: boolean` — additive only |
| `SmsQuotaStatus` | `packages/shared-types` or `packages/ui` | Quota UI for Phase 2 add-on number purchasing |
| `SmsThreadListItem` | `packages/ui` | Phase 2 inbox enhancements (search, archive filter) |
| `UnroutedMessage` | `packages/ui` | Phase 2 auto-routing improvements |

**Extension rule**: Phase 2 additions are **strictly additive optional fields**. Mandatory new fields on these types require a migration plan for all existing consumers.

### I.3 Components Locked as Extension Points for Phase 2

| Component | Extension Mechanism | Phase 2 Extension |
|:---|:---|:---|
| `<SmsThreadBubble>` | `renderAttachment?: (message: SmsMessage) => React.ReactNode` slot (Phase 2 add) | MMS: render image attachments via slot |
| `<ReplyComposer>` | `attachmentButton?: boolean` prop (Phase 2 add) | MMS composer attachment button |
| `<SmsQuotaIndicator>` | `addOnNumbers?: number` prop (Phase 2 add) | Show quota contribution from add-on numbers |
| `useSegmentCount()` | Parameters extended for MMS (Phase 2 returns MMS cost estimate separately) | `mmsCount?: number` added to `SegmentCountResult` |

### I.4 Route Structure Locked for Phase 2 Deep-Links

The following route structures are locked — Phase 2 must not change them without a migration because push notification deep-links are baked into the OS notification payload:

```
pilot:///(tabs)/(home)/inbox/[threadId]          ← LOCKED — push notification deep-link
/customers/[id]/comms?thread=[threadId]          ← LOCKED — web comm history thread anchor
/settings/integrations/sms/unrouted             ← LOCKED — owner unrouted notification deep-link
```

### I.5 What FE-B10 Unlocks for Phase 2 (Non-Blocking Notes)

The following Phase 2 features are directly enabled by FE-B10's infrastructure and can be implemented without re-architecting:

- **Thread archiving**: add `status: 'archived'` filter to `useCustomerThreads()` + archive button on thread header
- **MMS (image attachments)**: extend `SmsMessage.media_urls?: string[]` + `<SmsThreadBubble>` attachment slot + composer attachment button
- **Per-tech phone numbers**: threading model already supports `tenant_phone_number_id` per thread; provisioning UI is the only Phase 2 addition
- **AI-suggested replies**: `SmsMessage.ai_suggested?: boolean` + suggested reply chips above the composer — `ReplyComposer` has a `suggestionSlot` for this
- **Self-service number purchasing**: extends `/settings/integrations/sms` with "Add a number" CTA; `SmsQuotaStatus` already returns `included_segments` which reflects add-on numbers
- **SMS conversation export**: audit trail exists via `SmsMessage` records; export UI at `/settings/integrations/sms/export` reads from existing endpoints

### I.6 Exports Added to `packages/ui/src/index.ts` by FE-B10

```typescript
// ── FE-B10 Exports ─────────────────────────────────────────────────────────────
// SMS Inbound / Customer Comms Extension (Pass 4 Tier 1.5)
// Canonical types for Phase 2 reuse — do not redefine.

export { useSegmentCount } from "./hooks/useSegmentCount";
export type { SegmentCountResult } from "./hooks/useSegmentCount";

export { SmsQuotaIndicator } from "./sms-quota-indicator";
export type { SmsQuotaIndicatorProps } from "./sms-quota-indicator/types";

export { SmsThreadBubble } from "./sms-thread-bubble";
export type { SmsThreadBubbleProps } from "./sms-thread-bubble/types";

export { SmsOptOutBadge } from "./sms-opt-out-badge";
export type { SmsOptOutBadgeProps } from "./sms-opt-out-badge/types";

// Canonical SMS domain types — locked for Phase 2
export type {
  SmsThread,
  SmsMessage,
  SmsReplyRequest,
  SmsQuotaStatus,
  SmsThreadListItem,
  UnroutedMessage,
  QuotaVisualState,
  VoiceDictationState,
} from "./sms-thread-bubble/types";

export { deriveQuotaState } from "./sms-quota-indicator/utils";
```

---

*This document is the complete handoff artifact for the Pilot React Engineer for FE-B10. All 7 design decisions are resolved. All TypeScript interfaces are complete with no `any` types. All token references use exact token names from `tokens.ts`. The engineer can execute FE-B10 without returning for architectural decisions.*