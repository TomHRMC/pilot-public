# Implementation Prompt: FE-B23 Part B — Dashboard BI + Notification Bell + Voice on Web

**Mode**: Pilot React Engineer  
**Batch**: FE-B23 Part B (Frontend)  
**Source plan**: `dev-docs/analysis/pilot-app-pre-wkstm-3-prep-plan.md` §Phase 0.9 — FE-B23  
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-fe-b23-design.md`  
**Estimated session**: 4–6 hours  
**Platform**: Web only (`apps/web`)  
**Backend companion**: FE-B23 Part A (Python Engineer) — **must be complete before starting**. Prerequisites: FE-B21 + FE-B22 complete + `pnpm sync-api-types` after Part A.

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-react-engineer/react-engineer-rules.md`** — in full
- **`dev-docs/architecture-design/batch-designs/batch-fe-b23-design.md`** — every section (A–I)

**Critical rules for this batch:**

- **Rule 1.1**: Before ANY hook, verify endpoint in `backend/openapi_schema_map.md`. The `at-risk-jobs` and `pending-approvals-summary` endpoints were just added in Part A — confirm they appear.
- **Rule 1.3**: Run `pnpm sync-api-types` before starting — Part A added new endpoints.
- **Rule 2**: All API calls use `apiClient`. `fetch()` banned.
- **Rule 3**: SSE endpoints require `?token=JWT`. `useNotificationSse` MUST use `useSseChannel` with `getToken` prop (centralized in B17).
- **Rule 7**: Check `packages/ui/src/index.ts` before creating any new component.
- **Rule 8**: No new npm packages without checking `package.json`.
- **Rule 9**: Route files are thin server components.
- **Rule 10**: Any test failure must be fixed before declaring done.
- **Notification bell is global state**: The unread count must be accessible from the layout header AND updated by the SSE stream in real-time. Use a simple Zustand store or `useState` lifted to the layout — do NOT pass the count through multiple prop layers.
- **Voice on web is session list + history only in FE-B23**: Do NOT implement microphone capture or audio upload in this batch. Those are complex and mobile-focused. The `/voice` page shows past sessions; `/voice/[id]` shows message history. A "Start New Session" button calls `POST /api/v1/voice/sessions` and navigates to the new session.

---

## Design Decisions (Do Not Re-Litigate)

From Design Doc §G:

| Decision | Outcome | Rationale |
|---|---|---|
| Voice on web scope | Session list + message history only; no mic capture | Mic + audio is complex; address post-FE-B23 |
| Notification bell state | Simple Zustand store or layout-level state | Global unread count must be accessible in header |
| Notification drawer | Slide-in from right, same pattern as help drawer | Consistent with FE-B16 help drawer |
| At-risk jobs threshold | `margin_target_pct` from backend (20% default) | Computed server-side; no client-side calculation needed |

---

## Pre-Work: Establish Regression Baseline

```bash
cd <repo>/frontend
pnpm --filter web test 2>&1 | tail -5
pnpm --filter @pilot/ui test 2>&1 | tail -5
```

Record exact counts. Fix pre-existing failures or confirm with Tom.

---

## Pre-Work: Sync API Types

```bash
cd <repo>/frontend
pnpm sync-api-types
```

If this fails: FE-B23 Part A may not be complete. Stop and confirm.

---

## Pre-Work: Verify Endpoints

```bash
# Confirm new Part A endpoints appear
grep -A 3 "at-risk-jobs" backend/openapi_schema_map.md | head -10
grep -A 3 "pending-approvals-summary" backend/openapi_schema_map.md | head -10

# Confirm notification SSE + bell endpoints
grep -A 3 "notifications/in-app" backend/openapi_schema_map.md | head -20
grep -A 3 "sse/notifications" backend/openapi_schema_map.md | head -10

# Confirm voice sessions endpoints
grep -A 3 "voice/sessions" backend/openapi_schema_map.md | head -20

# Check voice sessions POST (created in Part A or pre-existing)
python3 -c "
import json
spec = json.load(open('backend/openapi.json'))
voice = [p for p in spec['paths'] if 'voice/sessions' in p]
for p in voice:
    print(p, '->', list(spec['paths'][p].keys()))
"

# Check SSE endpoint path exactly
python3 -c "
import json
spec = json.load(open('backend/openapi.json'))
sse = [p for p in spec['paths'] if 'sse' in p.lower()]
print('SSE paths:', sse)
"
```

| Hook | Endpoint | Verified |
|---|---|---|
| `useAtRiskJobs` | `GET /api/v1/dashboard/at-risk-jobs` | Confirm before coding |
| `usePendingApprovals` | `GET /api/v1/dashboard/pending-approvals-summary` | Confirm before coding |
| `useInAppNotifications` | `GET /api/v1/notifications/in-app/recent?limit=50` | Confirm before coding |
| `useMarkNotificationsRead` | `POST /api/v1/notifications/in-app/mark-read` | Confirm before coding |
| `useNotificationSse` | `GET /sse/notifications?token={JWT}` | Confirm path |
| `useVoiceSessions` | `GET /api/v1/voice/sessions` | Confirm before coding |
| `useVoiceSessionMessages` | `GET /api/v1/voice/sessions/{id}/messages` | Confirm before coding |
| (new session) | `POST /api/v1/voice/sessions` | Confirm exists after Part A |

---

## Pre-Work: Read These Source Files

```
frontend/apps/web/src/app/(authed)/layout.tsx
  ← understand current layout structure before adding header bar + bell

frontend/apps/web/src/app/(authed)/dashboard/page.tsx
  ← understand current widget layout before adding new widgets

frontend/apps/web/src/features/help/store/helpPanelStore.ts
  ← reference for drawer open/close state pattern

frontend/apps/web/src/features/notifications-center/
  ← list what already exists (likely just hooks from FE-B12)

frontend/apps/web/src/mocks/handlers/index.ts
  ← understand barrel before adding handlers

frontend/packages/ui/src/index.ts
  ← confirm available components
```

Also run:
```bash
# What exists in notifications-center features?
find frontend/apps/web/src/features/notifications-center -type f | sort

# What exists in voice features on web?
find frontend/apps/web/src/features/voice 2>/dev/null | sort

# Check useSseChannel to confirm getToken prop (from B17)
find frontend/packages -name "useSseChannel*" | head -3
grep -n "getToken" $(find frontend/packages -name "useSseChannel*" | head -1) | head -5
```

---

## Step B1 — Create MSW Handlers for New Endpoints

Check existing handlers first. Add new handlers for:

```typescript
// GET /api/v1/dashboard/at-risk-jobs
// GET /api/v1/dashboard/pending-approvals-summary
// GET /api/v1/notifications/in-app/recent
// POST /api/v1/notifications/in-app/mark-read
// GET /api/v1/voice/sessions
// GET /api/v1/voice/sessions/:sessionId/messages
// POST /api/v1/voice/sessions (create new session)
// GET /sse/notifications (SSE — return a simple persistent response or mock stream)
```

Create `mocks/handlers/b23Handlers.ts` and register in `mocks/handlers/index.ts`.

> **Test resilience**: Never mutate fixture arrays. POST handlers return new items with generated IDs.

**Intermediate check:**
```bash
pnpm --filter web test 2>&1 | tail -5
```

---

## Steps B2–B7 — Create Hooks

**Directory structure**:
- `apps/web/src/features/dashboard/hooks/` — BI widget hooks
- `apps/web/src/features/notifications-center/hooks/` — notification hooks (check what exists)
- `apps/web/src/features/voice/hooks/` — voice session hooks

### `useAtRiskJobs.ts`
```typescript
// Query key: ['dashboard-at-risk-jobs']
// GET /api/v1/dashboard/at-risk-jobs?limit=5
// Returns AtRiskJobsResponse
// staleTime: 60_000
```

### `usePendingApprovals.ts`
```typescript
// Query key: ['dashboard-pending-approvals']
// GET /api/v1/dashboard/pending-approvals-summary
// Returns { pending_quotes, pending_field_issues }
// staleTime: 30_000
```

### `useInAppNotifications.ts`
```typescript
// Query key: ['notifications-recent']
// GET /api/v1/notifications/in-app/recent?limit=50
// Returns list of { notification_id, body, deep_link_target, priority, created_at, read_at }
// staleTime: 0 (always fresh — SSE keeps it up to date)
```

### `useMarkNotificationsRead.ts`
```typescript
// POST /api/v1/notifications/in-app/mark-read
// Body: { notification_ids: string[] } OR mark all
// onSuccess: invalidate ['notifications-recent']
```

### `useNotificationSse.ts`
```typescript
// Opens SSE to /sse/notifications?token={JWT}
// Uses useSseChannel with getToken prop:
import { fetchAuthSession } from 'aws-amplify/auth';
const getToken = async () => {
  const session = await fetchAuthSession();
  return session.tokens?.accessToken?.toString() ?? '';
};

// On 'in_app_notification' event: 
//   1. Increment unread count in notification store
//   2. Invalidate ['notifications-recent'] query
// Note: SSE path may be /sse/notifications (not /api/v1/sse/...) — verify from pre-work
```

### `useVoiceSessions.ts`
```typescript
// Query key: ['voice-sessions']
// GET /api/v1/voice/sessions?limit=20
// Returns SessionListResponse (sessions[], next_cursor, has_more)
```

### `useVoiceSessionMessages.ts`
```typescript
// Query key: ['voice-session-messages', sessionId]
// GET /api/v1/voice/sessions/{sessionId}/messages?limit=50
// Returns SessionMessagesResponse
// enabled: !!sessionId
```

---

## Steps B8–B10 — Dashboard BI Widgets

### `AtRiskJobsWidget.tsx`

```typescript
"use client";
// Shows top N jobs below margin target
// Job name (customer name), status badge, actual cost vs quoted budget
// Margin % in red when below target
// "View Jobs" link → /jobs (filtered to at-risk — pass query param if supported)
// EmptyState: "All jobs are tracking within margin"
// RoleGate: reports.view
```

### `PendingApprovalsWidget.tsx`

```typescript
"use client";
// Shows counts: X quotes pending review, Y field issues
// "Review Quotes" link → /quotes/pending
// "Field Issues" link → /dashboard/approvals/field-issues
// EmptyState: "No pending approvals"
// RoleGate: quotes.view
```

### Add widgets to `dashboard/page.tsx`

Read the file first. Add both new widgets in a 2-column grid row. Position them as the first action-requiring row (above AR aging from FE-B22, below trial banner + onboarding checklist).

---

## Steps B11–B13 — Notification Bell

### `notificationBellStore.ts`

```typescript
// Simple Zustand store (or useState in layout — prefer Zustand for global access):
interface NotificationBellStore {
  unreadCount: number;
  setUnreadCount: (count: number) => void;
  incrementUnread: () => void;
  drawerOpen: boolean;
  setDrawerOpen: (open: boolean) => void;
}
```

### `NotificationBell.tsx`

```typescript
"use client";
// Bell icon button in app header
// Shows unread count badge when unreadCount > 0
// On click: opens NotificationDrawer (sets drawerOpen = true in store)
// Opens SSE connection via useNotificationSse when mounted
// Syncs initial unreadCount from useInAppNotifications (count of unread items)
```

### `NotificationDrawer.tsx`

```typescript
"use client";
// Slide-in drawer from right edge
// Shows last 50 notifications from useInAppNotifications
// Each notification: body text, relative time, click navigates to deep_link_target
// "Mark all read" button → useMarkNotificationsRead
// Read notifications shown in muted style
// Closes on backdrop click or "×" button
```

### `NotificationItem.tsx`

```typescript
// Single notification row:
// - priority badge (critical vs standard)
// - body text (truncate at 120 chars)
// - relative time (2m ago, 1h ago)
// - unread indicator (dot)
// On click: mark as read + navigate to deep_link_target
```

### Modify `app/(authed)/layout.tsx`

Read the file first. The current layout has sidebar + content area. Add a **top header bar**:

```tsx
<div className="flex flex-col h-full">
  {/* Header */}
  <header className="h-12 bg-white border-b border-neutral-200 flex items-center justify-end px-4 shrink-0">
    <NotificationBell />
  </header>
  
  {/* Existing: sidebar + content */}
  <div className="flex flex-1 min-h-0">
    <AppSidebar />
    <main className="flex-1 overflow-auto">
      {children}
    </main>
  </div>
  
  <NotificationDrawer />
</div>
```

> Adjust the exact structure to match what you find in the file. Do NOT break the existing sidebar layout.

---

## Steps B14–B16 — Voice Session Interface

### `VoiceSessionsPage.tsx`

```typescript
"use client";
// List of past voice sessions from useVoiceSessions
// Each row: session number (#5), title, message count, date
// "+ New Session" button: calls POST /api/v1/voice/sessions → navigates to /voice/{sessionId}
// Each row links to /voice/[sessionId]
// EmptyState: "Start your first voice session"
```

### `VoiceSessionDetailPage.tsx`

```typescript
"use client";
// Shows message history from useVoiceSessionMessages
// Session title in header
// Messages in chronological order
// User messages right-aligned; AI messages left-aligned
// Each message shows content_text; structured_content_json rendered if present
// Scroll to bottom on load
// Back link to /voice
```

### `VoiceMessageBubble.tsx`

```typescript
// Props: message: SessionMessageResponse
// Role 'user': right-aligned, brand background
// Role 'assistant': left-aligned, neutral background
// Show content_text; if structured_content_json present, show a simple JSON card
// Timestamp shown below bubble
```

### Route files

```typescript
// app/(authed)/voice/page.tsx
import { VoiceSessionsPage } from "@/features/voice/components/VoiceSessionsPage";
export default function VoicePage() { return <VoiceSessionsPage />; }
export const metadata = { title: "Voice Sessions | Pilot" };

// app/(authed)/voice/[sessionId]/page.tsx
import { VoiceSessionDetailPage } from "@/features/voice/components/VoiceSessionDetailPage";
interface Props { params: Promise<{ sessionId: string }> }
export default async function VoiceSessionDetailRoute({ params }: Props) {
  const { sessionId } = await params;
  return <VoiceSessionDetailPage sessionId={sessionId} />;
}
```

---

## Test Requirements

### Platform: Web (`apps/web`) — Vitest

- `vi.mock()`, `toBeInTheDocument()`, mock `next/navigation`
- `createWrapper()` with `retry: false`

### Test Resilience (per `react-engineer-rules.md` Rule 15)

- Never mutate fixture arrays
- Per-test `server.use(...)` + `server.resetHandlers()` in `afterEach`

### Unit Tests

**`features/dashboard/components/__tests__/AtRiskJobsWidget.test.tsx`:**
- Renders at-risk jobs list with margin percentages from MSW data
- EmptyState when no at-risk jobs
- "View Jobs" link present
- RoleGate: hidden from tech role

**`features/notifications-center/components/__tests__/NotificationBell.test.tsx`:**
- Renders bell icon
- Shows badge with count when unreadCount > 0
- No badge when unreadCount = 0
- Click opens drawer (sets store state)

**`features/notifications-center/components/__tests__/NotificationDrawer.test.tsx`:**
- Renders notification list from MSW data
- "Mark all read" button fires `useMarkNotificationsRead`
- Unread items show indicator; read items do not

**`features/voice/components/__tests__/VoiceSessionsPage.test.tsx`:**
- Renders session list from MSW data
- "+ New Session" button visible
- Each session row links to `/voice/[sessionId]`

### Integration Tests

**`apps/web/src/__tests__/batch_fe_b23/dashboardBI.integration.test.tsx`:**
1. Dashboard renders `AtRiskJobsWidget` and `PendingApprovalsWidget`
2. At-risk jobs widget shows jobs from MSW
3. Pending approvals widget shows count from MSW

**`apps/web/src/__tests__/batch_fe_b23/notificationBell.integration.test.tsx`:**
1. Layout renders notification bell in header
2. Bell shows correct unread count from MSW data
3. Clicking bell opens notification drawer
4. Notification items appear with body text

---

## Final Verification

### Phase 1 — Targeted

```bash
cd <repo>/frontend

# After hooks:
pnpm --filter web test -- --testPathPattern="useAtRisk|usePending|useNotification|useVoice" 2>&1 | tail -6

# After components:
pnpm --filter web test -- --testPathPattern="AtRiskJobs|NotificationBell|NotificationDrawer|VoiceSessions" 2>&1 | tail -8

# After integration:
pnpm --filter web test -- --testPathPattern="batch_fe_b23" 2>&1 | tail -8
```

### Phase 2 — Full Verification

```bash
cd <repo>/frontend && pnpm --filter @pilot/ui check-types && pnpm --filter web check-types && pnpm --filter @pilot/ui lint && pnpm --filter web lint && echo "=== TYPE+LINT PASS ===" && pnpm --filter @pilot/ui test 2>&1 | tail -6 && pnpm --filter web test 2>&1 | tail -6 && echo "=== FE-B23 PART B FINAL VERIFICATION COMPLETE ==="
```

---

## Definition of Done — FE-B23 Part B

Update `dev-docs/analysis/pilot-app-pre-wkstm-3-prep-plan.md` §Phase 0.9:

- [ ] Regression baseline captured (zero pre-existing failures or confirmed with Tom)
- [ ] `pnpm sync-api-types` run after Part A
- [ ] Design doc read in full (A–I)
- [ ] All mandatory source files read (layout.tsx, dashboard/page.tsx, helpPanelStore.ts, mocks/handlers/index.ts)
- [ ] All endpoints verified in `openapi_schema_map.md`
- [ ] **B1**: MSW handlers for new endpoints created + registered in barrel
- [ ] **B2–B7**: All 7 hooks created
- [ ] **B8**: `AtRiskJobsWidget` created with RoleGate
- [ ] **B9**: `PendingApprovalsWidget` created
- [ ] **B10**: Both BI widgets added to dashboard page
- [ ] **B11**: `notificationBellStore.ts` created (or equivalent global state)
- [ ] **B12**: `NotificationBell` component created; SSE connection opens; unread count updates in real-time
- [ ] **B13**: `NotificationDrawer` created; bell click opens drawer; mark-read works
- [ ] **B13**: Layout header bar added with `NotificationBell`; existing sidebar layout unaffected
- [ ] **B14**: `VoiceSessionsPage` created; session list renders
- [ ] **B15**: `VoiceSessionDetailPage` created; message history renders
- [ ] **B16**: `/voice` and `/voice/[sessionId]` routes created
- [ ] `AtRiskJobsWidget` unit tests pass (RoleGate)
- [ ] `NotificationBell` unit tests pass (badge count)
- [ ] `NotificationDrawer` unit tests pass (mark-read)
- [ ] `VoiceSessionsPage` unit tests pass
- [ ] Integration tests in `__tests__/batch_fe_b23/` pass
- [ ] Layout header bar doesn't break existing page layout (dispatch board, customers, etc.)
- [ ] All new MSW handlers registered in barrel
- [ ] Zero TypeScript errors
- [ ] Zero ESLint `no-hardcoded-design-values` warnings
- [ ] **Phase 2 FULL verification passes** (`=== FE-B23 PART B FINAL VERIFICATION COMPLETE ===`):
  ```bash
  cd <repo>/frontend && pnpm --filter @pilot/ui check-types && pnpm --filter web check-types && pnpm --filter @pilot/ui lint && pnpm --filter web lint && echo "=== TYPE+LINT PASS ===" && pnpm --filter @pilot/ui test 2>&1 | tail -6 && pnpm --filter web test 2>&1 | tail -6 && echo "=== FE-B23 PART B FINAL VERIFICATION COMPLETE ==="
  ```
- [ ] Final test count documented
- [ ] Completion Summary added to impl plan §Phase 0.9

---

## Completion Summary

After all DoD items, add a **Completion Summary** to `dev-docs/analysis/pilot-app-pre-wkstm-3-prep-plan.md` under Phase 0.9 — FE-B23:

```markdown
### FE-B23 — Dashboard BI + Notification Bell + Voice on Web: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot React Engineer
**Baseline**: X passed (ui) | X passed (web)
**Final**: X+N passed (+N new tests)

#### What Was Accomplished

- Added at-risk jobs widget and pending approvals widget to dashboard
- Dashboard is now demonstrable to a prospective customer
- Notification bell in app header with real-time SSE-driven unread count
- Notification drawer with last 50 notifications, mark-read
- /voice route showing past voice sessions
- /voice/[id] showing session message history
- "Start New Session" creates a new voice session

#### Files Changed / Created

| File | Action |
|---|---|
| `apps/web/src/mocks/handlers/b23Handlers.ts` | Created |
| `apps/web/src/mocks/handlers/index.ts` | Updated |
| `apps/web/src/features/dashboard/hooks/useAtRiskJobs.ts` | Created |
| `apps/web/src/features/dashboard/hooks/usePendingApprovals.ts` | Created |
| `apps/web/src/features/notifications-center/hooks/useInAppNotifications.ts` | Created |
| `apps/web/src/features/notifications-center/hooks/useMarkNotificationsRead.ts` | Created |
| `apps/web/src/features/notifications-center/hooks/useNotificationSse.ts` | Created |
| `apps/web/src/features/notifications-center/store/notificationBellStore.ts` | Created |
| `apps/web/src/features/notifications-center/components/NotificationBell.tsx` | Created |
| `apps/web/src/features/notifications-center/components/NotificationDrawer.tsx` | Created |
| `apps/web/src/features/notifications-center/components/NotificationItem.tsx` | Created |
| `apps/web/src/features/dashboard/components/AtRiskJobsWidget.tsx` | Created |
| `apps/web/src/features/dashboard/components/PendingApprovalsWidget.tsx` | Created |
| `apps/web/src/features/voice/hooks/useVoiceSessions.ts` | Created |
| `apps/web/src/features/voice/hooks/useVoiceSessionMessages.ts` | Created |
| `apps/web/src/features/voice/components/VoiceSessionsPage.tsx` | Created |
| `apps/web/src/features/voice/components/VoiceSessionDetailPage.tsx` | Created |
| `apps/web/src/features/voice/components/VoiceMessageBubble.tsx` | Created |
| `apps/web/src/app/(authed)/layout.tsx` | Updated — header bar + bell |
| `apps/web/src/app/(authed)/dashboard/page.tsx` | Updated — BI widgets |
| `apps/web/src/app/(authed)/voice/page.tsx` | Created |
| `apps/web/src/app/(authed)/voice/[sessionId]/page.tsx` | Created |

#### Tests Added

| Test File | Type | Tests | All Pass |
|---|---|---|---|
| `features/dashboard/components/__tests__/AtRiskJobsWidget.test.tsx` | Unit | N | ✅ |
| `features/notifications-center/components/__tests__/NotificationBell.test.tsx` | Unit | N | ✅ |
| `features/notifications-center/components/__tests__/NotificationDrawer.test.tsx` | Unit | N | ✅ |
| `features/voice/components/__tests__/VoiceSessionsPage.test.tsx` | Unit | N | ✅ |
| `apps/web/src/__tests__/batch_fe_b23/dashboardBI.integration.test.tsx` | Integration | N | ✅ |
| `apps/web/src/__tests__/batch_fe_b23/notificationBell.integration.test.tsx` | Integration | N | ✅ |
```

---

## After This Batch

FE-B23 is complete. **All 7 Phase 0.9 web frontend batches are now done.** The web app has:
- Full customer, quote, job, invoice, catalog management
- Dashboard with business intelligence (at-risk jobs, pending approvals, AR aging, SMS)
- Real-time notification bell
- Voice session history on web

**Remaining Phase 0.9 batches:**
- MOB-B6 — GPS clock-in + Photo upload + Structured messages (React Native Engr)
- MOB-B7 (mixed) — LOTO config + Create customer + Today tab refactor
