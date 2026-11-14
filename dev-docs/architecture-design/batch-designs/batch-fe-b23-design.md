# Batch FE-B23 Design — Dashboard Business Intelligence + Notification Bell + Voice on Web

**Batch**: FE-B23 (Mixed — Python Engineer then React Engineer)  
**Date**: June 17, 2026  
**Author**: Pilot Architect  
**Status**: DESIGN COMPLETE — Ready for implementation  
**Reference gap analysis**: `dev-docs/analysis/pilot-app-pre-wkstm-3-mvp-ui-api-gap-analysis.md` §1.8, §1.12, §1.13  
**Prerequisites**: FE-B21 + FE-B22 complete (jobs + invoices data exists), B17 Part A complete + `pnpm sync-api-types`

---

## Overview

FE-B23 is a **mixed batch** that closes the remaining major P1 gaps on the web app:

1. **Dashboard Business Intelligence** — at-risk jobs widget, pending quote approvals count, and pending invoices summary to make the dashboard demonstrable
2. **Notification Bell** — persistent bell icon in the web app shell with SSE-driven unread count badge and notification center drawer
3. **Voice Session Interface on Web** — `/voice` route showing session list and `/voice/[sessionId]` session detail with voice composer

**Part A (Python Engineer)**: Adds two missing backend aggregation endpoints that the BI widgets need. Runs first.  
**Part B (React Engineer)**: Builds all three UI surfaces. Runs after Part A + `pnpm sync-api-types`.

---

## A. Input Read Summary

| Input | What was read | Key finding |
|---|---|---|
| Gap analysis §1.8, §1.12, §1.13 | Dashboard BI, notification bell, voice on web | Dashboard only has onboarding + SMS widgets; no business data |
| `backend/api/routes/dashboard.py` lines 1–180 | Widget CRUD + `_get_recent_customer_messages_impl` | Dashboard widget system (CRUD for configurable widgets) exists; `GET /api/v1/dashboard/widgets/recent-customer-messages` exists; no at-risk jobs or pending approvals aggregation endpoints |
| `backend/api/routes/notification_sse.py` lines 1–135 | SSE stream at `GET /sse/notifications` with `?token=JWT` pattern | Notification SSE endpoint confirmed at `/sse/notifications`; `GET /api/v1/notifications/in-app/recent?limit=50` returns bell panel data |
| `backend/api/routes/voice_sessions.py` lines 1–80 | `GET /api/v1/voice/sessions` + `GET /api/v1/voice/sessions/{id}/messages` | Session list + messages endpoints exist; cursor-based pagination |
| `mvp-arch.md` §3.5.6, §16.13 | In-app banner + notification bell | Bell icon shows unread count from last 24h + last 50 notifications |
| `frontend/apps/web/src/app/(authed)/` listing | No `/voice` route exists on web | Must create `/voice` and `/voice/[sessionId]` routes |
| Dashboard current state | `app/(authed)/dashboard/page.tsx` has trial banner + onboarding checklist + SMS widget | AR aging widget added in FE-B22; FE-B23 adds BI widgets |

---

## B. Migration Plan

### Part A — Python Engineer (New Endpoints)

Two new aggregation endpoints are needed for the dashboard BI widgets:

**New Endpoint 1: `GET /api/v1/dashboard/at-risk-jobs`**

Returns jobs where projected margin (from `actual_labor_cost_cents + actual_material_cost_cents + ETC` vs `quote.total_cents`) is below the tenant's `margin_target_pct` setting (default 20%).

```python
# Response schema
class AtRiskJobItem(BaseModel):
    job_id: UUID
    customer_name: str
    site_name: str | None
    status_code: str
    scheduled_start_at: datetime | None
    actual_cost_cents: int      # actual_labor + actual_material
    quoted_budget_cents: int    # from linked quote total (if exists)
    projected_margin_pct: float

class AtRiskJobsResponse(BaseModel):
    jobs: list[AtRiskJobItem]
    total: int
```

Implementation: Join `job` → `customer` → `site` → `quote` (for quoted_budget); filter where `actual_cost_cents / quote.total_cents` exceeds `(1 - margin_target_pct)`; limit to active/in-progress jobs only.

**New Endpoint 2: `GET /api/v1/dashboard/pending-approvals-summary`**

Returns counts of items pending owner action.

```python
class PendingApprovalsSummaryResponse(BaseModel):
    pending_quotes: int       # quotes with status_code = 'pending_approval'
    pending_field_issues: int # mobile sync conflicts with severity = 'owner_escalation' + status = 'pending'
```

These two endpoints are additions to `backend/api/routes/dashboard.py`.

### Pre-Migration MCP Verification

```sql
-- Verify job table has the profitability columns we need
SELECT column_name FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'job'
  AND column_name IN ('actual_labor_cost_cents', 'actual_material_cost_cents', 'actual_profit_cents');

-- Verify notification tables exist
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public' AND table_name LIKE '%in_app_notif%';

-- Verify conversation_session columns
SELECT column_name FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'conversation_session'
ORDER BY ordinal_position;
```

---

## C. Execution Order

### Part A — Python Engineer (runs first)

| # | Task | File | Dependency |
|---|---|---|---|
| A1 | Add `GET /api/v1/dashboard/at-risk-jobs` endpoint | `backend/api/routes/dashboard.py` | None |
| A2 | Add `GET /api/v1/dashboard/pending-approvals-summary` endpoint | `backend/api/routes/dashboard.py` | None |
| A3 | Run `pytest -q` — zero new failures | — | A1, A2 |
| A4 | Run `python export_openapi_json.py` | — | A3 |
| **Handoff** | `cd frontend && pnpm sync-api-types` | — | A4 |

### Part B — React Engineer (after Part A + sync-api-types)

| # | Task | Files | Dependency |
|---|---|---|---|
| B1 | Create notification + voice + dashboard MSW handlers | `mocks/handlers/` | None — first |
| B2 | Create `useAtRiskJobs` hook | `features/dashboard/hooks/useAtRiskJobs.ts` | B1 |
| B3 | Create `usePendingApprovals` hook | `features/dashboard/hooks/usePendingApprovals.ts` | B1 |
| B4 | Create `useInAppNotifications` + `useMarkNotificationsRead` | `features/notifications-center/hooks/` | B1 |
| B5 | Create `useNotificationSse` hook | `features/notifications-center/hooks/useNotificationSse.ts` | B1 |
| B6 | Create `useVoiceSessions` hook | `features/voice/hooks/useVoiceSessions.ts` | B1 |
| B7 | Create `useVoiceSessionMessages` hook | `features/voice/hooks/useVoiceSessionMessages.ts` | B1 |
| B8 | Create `AtRiskJobsWidget` | `features/dashboard/components/AtRiskJobsWidget.tsx` | B2 |
| B9 | Create `PendingApprovalsWidget` | `features/dashboard/components/PendingApprovalsWidget.tsx` | B3 |
| B10 | Add widgets to dashboard page | `app/(authed)/dashboard/page.tsx` | B8, B9 |
| B11 | Create `NotificationBell` shell component | `features/notifications-center/components/NotificationBell.tsx` | B4, B5 |
| B12 | Create `NotificationDrawer` (last 50 notifications) | `features/notifications-center/components/NotificationDrawer.tsx` | B4 |
| B13 | Add notification bell to web app layout | `app/(authed)/layout.tsx` | B11, B12 |
| B14 | Create `VoiceSessionsPage` | `features/voice/components/VoiceSessionsPage.tsx` | B6 |
| B15 | Create `VoiceSessionDetailPage` | `features/voice/components/VoiceSessionDetailPage.tsx` | B7 |
| B16 | Create `/voice` and `/voice/[sessionId]` routes | Route files | B14, B15 |
| B17 | Write tests | `__tests__/batch_fe_b23/` | All |
| B18 | Full verification | — | B17 |

---

## D. New API Endpoints (Part A)

### D.1 `GET /api/v1/dashboard/at-risk-jobs`

**Auth**: JWT required  
**RBAC**: `reports.view` (owner + accountant)  
**Query params**: `limit=10` (default)  
**Response**:
```json
{
  "jobs": [
    {
      "job_id": "uuid",
      "customer_name": "Johnson Electrical",
      "site_name": "Main Office",
      "status_code": "in_progress",
      "scheduled_start_at": "2026-06-16T09:00:00Z",
      "actual_cost_cents": 48000,
      "quoted_budget_cents": 53000,
      "projected_margin_pct": 9.4
    }
  ],
  "total": 3
}
```

### D.2 `GET /api/v1/dashboard/pending-approvals-summary`

**Auth**: JWT required  
**RBAC**: `quotes.approve` or `field_issue.view` (owner-accessible)  
**Response**:
```json
{
  "pending_quotes": 2,
  "pending_field_issues": 1
}
```

---

## E. Pattern Reuse Decisions

| Pattern | Applied in FE-B23 |
|---|---|
| SSE `?token=JWT` pattern | `useNotificationSse` uses `useSseChannel` with `getToken` prop (centralized in B17 React half) |
| `<LoadingState>`, `<ErrorState>`, `<EmptyState>` | All new widgets and voice pages |
| `<RoleGate>` | At-risk jobs and pending approvals widgets gated to owner/accountant |
| `apiClient` | All hooks |
| `retry: false` | All test QueryClient wrappers |

---

## F. Shared Module Interfaces

### F.1 `useNotificationSse`

```typescript
// features/notifications-center/hooks/useNotificationSse.ts
// Opens SSE connection to GET /sse/notifications?token={JWT}
// On new 'in_app_notification' event: calls queryClient.invalidateQueries(['notifications-recent'])
// Updates bell badge count in real-time
// Uses useSseChannel with getToken prop (from B17)
```

### F.2 `useInAppNotifications`

```typescript
// Query key: ['notifications-recent']
// GET /api/v1/notifications/in-app/recent?limit=50
// Returns list of InAppNotification items with read_at, deep_link_target, body
```

### F.3 `useVoiceSessions`

```typescript
// Query key: ['voice-sessions']
// GET /api/v1/voice/sessions?limit=20
// Returns SessionListResponse (cursor-based pagination)
```

### F.4 `useVoiceSessionMessages`

```typescript
// Query key: ['voice-session-messages', sessionId]
// GET /api/v1/voice/sessions/{sessionId}/messages?limit=50
// Returns SessionMessagesResponse
// enabled: !!sessionId
```

---

## G. Open Questions Resolved

| Question | Resolution |
|---|---|
| **Does voice on web need a mic/audio composer?** | For FE-B23 MVP: voice session **list** + **message history** only. The actual mic capture + `POST /api/v1/voice/command` is complex (microphone permissions, audio streaming) — deferred to after FE-B23 is stable. The `/voice` route shows session history; new session creation is a "Start" button that calls `POST /api/v1/voice/sessions` (check if this endpoint exists — if not, create in Part A). |
| **Does `POST /api/v1/voice/sessions` exist?** | Check in pre-work. `voice_sessions.py` only shows GET endpoints. If POST doesn't exist: add to Part A alongside the dashboard endpoints. |
| **Notification bell — where in the layout?** | In the authenticated layout header area (`app/(authed)/layout.tsx`). Currently that layout has just the sidebar + content area. Add a top header bar with bell icon in the upper right. |
| **Notification drawer — slide-in or page?** | Slide-in drawer from the right edge (as per PRD §3.7). Same pattern as the help drawer from FE-B16. Use `helpPanelStore.ts` as reference for drawer open/close state pattern. |
| **At-risk jobs widget — what threshold?** | Use the `margin_target_pct` platform setting (default 20%). The `projected_margin_pct` returned by the new endpoint uses the same calculation as `GET /api/v1/jobs/{id}/projected-margin`. |
| **Voice session list — link to `/jobs` or `/quotes`?** | Link each session to `/voice/[sessionId]` which shows the message history. Context chips in session messages link to related entities (quote/job links) where relevant. |

---

## H. Surface Mockup Reference

**Platform**: Web only (`apps/web`)

### H.1 Dashboard — Business Intelligence Widgets

```
┌─────────────────────────────────────────────────────────────┐
│  Dashboard                                    [🔔 3]       │
│  ─────────────────────────────────────────────────────────  │
│  [Trial Banner if applicable]                               │
│  ─────────────────────────────────────────────────────────  │
│  PENDING APPROVALS          AT-RISK JOBS                    │
│  2 quotes pending review    3 jobs below 20% margin         │
│  1 field issue              Johnson Panel (9.4%)            │
│  [Review Quotes →]          Smith Residence (11.2%)         │
│                             [View Jobs →]                   │
│  ─────────────────────────────────────────────────────────  │
│  AR Aging (from FE-B22)    Recent Messages (existing)       │
│  ...                        ...                             │
│  ─────────────────────────────────────────────────────────  │
│  Onboarding Checklist (existing, until dismissed)           │
└─────────────────────────────────────────────────────────────┘
```

### H.2 Notification Bell + Drawer

```
App header: [Pilot for Trades]                    [🔔 3]
                                                    ↓
                                    ┌─────────────────────┐
                                    │ Notifications        │
                                    │ ─────────────────── │
                                    │ • Quote approved (2m)│
                                    │ • Field issue (1h)   │
                                    │ • SMS from Johnson   │
                                    │ [Mark all read]      │
                                    └─────────────────────┘
```

### H.3 `/voice` — Voice Sessions List

```
┌─────────────────────────────────────────────────────────────┐
│  Voice Sessions                         [+ New Session]     │
│  ─────────────────────────────────────────────────────────  │
│  #5  Johnson 200A panel quote           Jun 16 2:30pm  [→] │
│  #4  Davis service call estimate        Jun 15 10:15am [→] │
│  #3  Martinez properties quote          Jun 14 4pm     [→] │
└─────────────────────────────────────────────────────────────┘
```

---

## I. Component Manifest

| Component | Path | New or Modify | Engineer |
|---|---|---|---|
| `AtRiskJobsWidget` | `features/dashboard/components/AtRiskJobsWidget.tsx` | **New** | React |
| `PendingApprovalsWidget` | `features/dashboard/components/PendingApprovalsWidget.tsx` | **New** | React |
| `NotificationBell` | `features/notifications-center/components/NotificationBell.tsx` | **New** | React |
| `NotificationDrawer` | `features/notifications-center/components/NotificationDrawer.tsx` | **New** | React |
| `NotificationItem` | `features/notifications-center/components/NotificationItem.tsx` | **New** | React |
| `VoiceSessionsPage` | `features/voice/components/VoiceSessionsPage.tsx` | **New** | React |
| `VoiceSessionDetailPage` | `features/voice/components/VoiceSessionDetailPage.tsx` | **New** | React |
| `VoiceMessageBubble` | `features/voice/components/VoiceMessageBubble.tsx` | **New** | React |
| `useAtRiskJobs` | `features/dashboard/hooks/useAtRiskJobs.ts` | **New** | React |
| `usePendingApprovals` | `features/dashboard/hooks/usePendingApprovals.ts` | **New** | React |
| `useInAppNotifications` | `features/notifications-center/hooks/useInAppNotifications.ts` | **New** | React |
| `useMarkNotificationsRead` | `features/notifications-center/hooks/useMarkNotificationsRead.ts` | **New** | React |
| `useNotificationSse` | `features/notifications-center/hooks/useNotificationSse.ts` | **New** | React |
| `useVoiceSessions` | `features/voice/hooks/useVoiceSessions.ts` | **New** | React |
| `useVoiceSessionMessages` | `features/voice/hooks/useVoiceSessionMessages.ts` | **New** | React |
| `notificationBellStore.ts` | `features/notifications-center/store/notificationBellStore.ts` | **New** | React |
| `dashboard/page.tsx` | `app/(authed)/dashboard/page.tsx` | **Modify** | React |
| `(authed)/layout.tsx` | `app/(authed)/layout.tsx` | **Modify** | React — add header bar + bell |
| `voice/page.tsx` | `app/(authed)/voice/page.tsx` | **New** | React |
| `voice/[sessionId]/page.tsx` | `app/(authed)/voice/[sessionId]/page.tsx` | **New** | React |
| `backend/api/routes/dashboard.py` | — | **Modify** | Python — 2 new endpoints |
