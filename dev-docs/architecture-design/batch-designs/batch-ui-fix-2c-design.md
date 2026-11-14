# Batch UI-FIX-2C Design — Notifications Settings Consolidation (3 Tabs → 1 Unified Page)

**Batch**: UI-FIX-2C  
**Fix**: FIX-017  
**Engineer**: React Engineer  
**Type**: Frontend-only  
**Estimated effort**: ~1.5–2h  
**Dependencies**: None — can run immediately, no backend changes  
**Source decisions**: `ui-fix-2-decisions.md § FIX-017`

---

## A. Input Read Summary

| Input | Key Finding |
|---|---|
| `ui-fix-2-decisions.md` FIX-017 | 3 single-channel pages each link to the full matrix as "View full notification preferences matrix →" — the full matrix already exists and is better |
| `SettingsSidebar.tsx` lines 90–96 | `Notifications` group has 3 sub-items: Email `/email`, SMS `/sms`, In-app `/in-app` |
| `/settings/notifications/preferences/page.tsx` | Already renders `<NotificationPreferenceMatrix>` with full 3-column layout — this is the destination |
| `NotificationEmailPrefsPage.tsx` | Email-only single-column table — redundant; to be deleted |
| `NotificationSmsPrefsPage.tsx` | SMS-only single-column table — redundant; to be deleted |
| `NotificationInAppPrefsPage.tsx` | In-app-only table + **recent notifications history** (via `useRecentInAppNotifications`) — the history section must be preserved in the unified page |
| `packages/ui/src/notification-preference-matrix/` | `NotificationPreferenceMatrix` shared component — already does 3-column layout |

---

## B. Migration Plan

No DB changes. No API changes. No Alembic migration required.

---

## C. Execution Order

| # | Task | File(s) | Action |
|---|---|---|---|
| 1 | Read all source files listed in Pre-Work | — | Read |
| 2 | Update `SettingsSidebar.tsx` — collapse 3 sub-items to 1 direct link | `SettingsSidebar.tsx` | Update |
| 3 | Update unified preferences page — add Recent In-App Notifications section | `preferences/page.tsx` | Update |
| 4 | Replace 3 sub-route pages with redirects | `/email/page.tsx`, `/sms/page.tsx`, `/in-app/page.tsx` | Update |
| 5 | Verify `/settings/notifications/page.tsx` index redirects to preferences | `notifications/page.tsx` | Verify/update |
| 6 | Delete 3 redundant component files | 3 `Notification*PrefsPage.tsx` files | Delete |
| 7 | Update/delete tests for the removed components | Test files | Update/delete |
| 8 | Run tests and full Phase 2 verification | — | Verify |

---

## D. New API Endpoints

None — this is a pure frontend routing + sidebar cleanup batch.

**Endpoints consumed by the unified page** (already wired, no changes needed):
- `GET /api/v1/notifications/preferences` — consumed by existing `useNotificationPreferences()` hook
- `PATCH /api/v1/notifications/preferences` — consumed by existing hook
- `GET /api/v1/notifications/in-app` — consumed by existing `useRecentInAppNotifications()` hook (from `NotificationInAppPrefsPage.tsx`)

---

## E. Pattern Reuse Decisions

- **`<LoadingState>`, `<ErrorState>`** from `@pilot/ui/states` — already used in all three `Notification*PrefsPage` components; keep the same pattern in the unified page
- **Redirect pattern**: `import { redirect } from "next/navigation"; export default function Page() { redirect("/settings/notifications/preferences"); }` — same pattern used in `/settings/communications/page.tsx` and `/settings/sync-storage/page.tsx`
- **Route file as thin server component** — `preferences/page.tsx` is a client component (`"use client"`) that renders a feature component; after adding `useRecentInAppNotifications` it remains in the same file (it's already a client component)

---

## F. Shared Module Interfaces

### `SettingsSidebar.tsx` change

**Before** (lines 90–96):
```typescript
{
  label: "Notifications",
  href: "/settings/notifications",
  subItems: [
    { label: "Email", href: "/settings/notifications/email" },
    { label: "SMS", href: "/settings/notifications/sms" },
    { label: "In-app", href: "/settings/notifications/in-app" },
  ],
},
```

**After** (no sub-items — direct link):
```typescript
{
  label: "Notifications",
  href: "/settings/notifications/preferences",
  // No subItems — navigates directly to the unified page
},
```

### `/settings/notifications/preferences/page.tsx` addition

Add `useRecentInAppNotifications` below the matrix. Read the existing page file before modifying. Approximate new content to add below `<NotificationPreferenceMatrix ... />`:

```tsx
// Add after the existing matrix section
const {
  notifications: recentNotifications,
  isLoading: isHistoryLoading,
} = useRecentInAppNotifications();

// In JSX, below the NotificationPreferenceMatrix:
{recentNotifications && recentNotifications.length > 0 && (
  <div className="mt-8">
    <h2 className="text-h3 font-semibold text-neutral-900 mb-4">
      Recent In-App Notifications
    </h2>
    {/* render the notifications list — use the same pattern as NotificationInAppPrefsPage */}
  </div>
)}
```

Read `NotificationInAppPrefsPage.tsx` in full to understand exactly how `useRecentInAppNotifications` is used and what shape the data is before writing this section.

### Redirect files (3 files, same pattern each)

```tsx
// apps/web/src/app/(authed)/settings/notifications/email/page.tsx
import { redirect } from "next/navigation";
export default function NotificationEmailPage() {
  redirect("/settings/notifications/preferences");
}

// Same pattern for /sms/page.tsx and /in-app/page.tsx
```

---

## G. Open Questions Resolved

| Question | Resolution |
|---|---|
| Does the `/settings/notifications/page.tsx` index already redirect correctly? | Check the file — if it redirects to `/email` or another sub-page, update to redirect to `/preferences`. If it already redirects to `/preferences`, no change needed. |
| Should "Recent In-App Notifications" be visible when there are no recent notifications? | No — render the section only when there are notifications (guard with `recentNotifications.length > 0`). Match the existing behavior in `NotificationInAppPrefsPage.tsx`. |
| Is `tenant-defaults` page affected? | No — `/settings/notifications/tenant-defaults` (if it exists) is not touched by this batch. |

---

## H. Surface Mockup Reference

**Platform scope**: Web only (`apps/web`)

**Before (current)**: Three separate sidebar sub-nav items each navigate to a single-column toggle table. Each page has a "View full notification preferences matrix →" link pointing elsewhere.

**After**: One sidebar item "Notifications" navigates directly to the full 3-column matrix. The "View full..." link is removed (it's now the page itself). The recent in-app notifications history section appears below the matrix.

```
Settings sidebar:

  Team
  Operations
  Notifications  ←  single item, no sub-nav, links to /settings/notifications/preferences
  Sync & Storage
  ...

/settings/notifications/preferences page:

  Notification preferences
  Choose how you'd like to be notified about activity in Pilot.

  ┌─────────────────────────────┬────────┬─────┬────────┐
  │ Category                    │ Email  │ SMS │ In-app │
  ├─────────────────────────────┼────────┼─────┼────────┤
  │ Job assigned to you         │  🔘   │ 🔘  │   🔘   │
  │ ...                         │  ...  │ ... │   ...  │
  └─────────────────────────────┴────────┴─────┴────────┘

  Recent In-App Notifications
  ─────────────────────────────
  [list of recent notifications if any exist]
```

---

## I. Component Manifest

| File | Action | Notes |
|---|---|---|
| `apps/web/src/features/settings/components/SettingsSidebar.tsx` | **Update** | Remove Notifications sub-items; change href to `/settings/notifications/preferences` |
| `apps/web/src/app/(authed)/settings/notifications/preferences/page.tsx` | **Update** | Add `useRecentInAppNotifications` + recent history section; remove "View full..." link if present |
| `apps/web/src/app/(authed)/settings/notifications/email/page.tsx` | **Update** | Replace entire body with `redirect("/settings/notifications/preferences")` |
| `apps/web/src/app/(authed)/settings/notifications/sms/page.tsx` | **Update** | Replace entire body with redirect |
| `apps/web/src/app/(authed)/settings/notifications/in-app/page.tsx` | **Update** | Replace entire body with redirect |
| `apps/web/src/app/(authed)/settings/notifications/page.tsx` | **Verify/update** | Ensure redirects to `/preferences` (may already do so) |
| `apps/web/src/features/settings/components/NotificationEmailPrefsPage.tsx` | **Delete** | No longer rendered |
| `apps/web/src/features/settings/components/NotificationSmsPrefsPage.tsx` | **Delete** | No longer rendered |
| `apps/web/src/features/settings/components/NotificationInAppPrefsPage.tsx` | **Delete** | Logic migrated to unified page |
| `apps/web/src/__tests__/batch_ui_fix_2c/notifications_unified.integration.test.tsx` | **Create** | Integration test for unified page — renders matrix + recent history section |
