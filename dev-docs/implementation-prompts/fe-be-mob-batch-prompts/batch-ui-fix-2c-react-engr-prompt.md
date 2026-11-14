# Implementation Prompt: UI-FIX-2C — Notifications Settings Consolidation (3 Tabs → 1 Unified Page)

**Mode**: Pilot React Engineer  
**Batch**: UI-FIX-2C  
**Source decisions**: `dev-docs/architecture-design/batch-designs/ui-fix-2-decisions.md § FIX-017`  
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-ui-fix-2c-design.md`  
**Estimated session**: 1.5–2 hours  
**Platform**: Web only (`apps/web`)  
**Backend companion**: None — pure frontend, no backend changes needed

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-react-engineer/react-engineer-rules.md`** — in full
- **`dev-docs/architecture-design/batch-designs/batch-ui-fix-2c-design.md`** — every section

**Critical rules for this batch:**

- **Rule 9**: Route files in `apps/web/src/app/(authed)/` MUST be thin server components — no `"use client"`, no data fetching. The redirect pages in this batch are zero-logic server components.
- **Rule 7**: Check `packages/ui/src/index.ts` before creating any new component — the `NotificationPreferenceMatrix` is already in `@pilot/ui` and must NOT be duplicated.
- **Rule 2**: All API calls use `apiClient` from `@pilot/shared-api`. `fetch()` is permanently banned for `/api/v1/...` calls.
- **Rule 10**: If ANY test fails — even one that appears pre-existing — **fix it before declaring done**. No exceptions without Tom's written confirmation.
- **Rule 8**: No new npm dependencies without first checking `package.json`.

---

## Design Decisions (Do Not Re-Litigate)

From `ui-fix-2-decisions.md` § FIX-017 and the design doc — these decisions are final:

| Decision | Outcome | Rationale |
|---|---|---|
| Which page becomes the canonical Notifications page | `/settings/notifications/preferences` — already built, already correct | The full 3-column `NotificationPreferenceMatrix` is already live there |
| What happens to the 3 sub-routes | Each gets `redirect("/settings/notifications/preferences")` | Preserve any bookmarks; no 404s |
| Recent in-app notification history | Moves to the bottom of the unified preferences page | Feature is preserved, not deleted |
| Sidebar sub-items | Removed — single flat "Notifications" link pointing directly to `/preferences` | Cleaner nav; sub-nav added no value |
| The "View full matrix →" link on each sub-page | Removed (pages become redirects, links become irrelevant) | Self-referential link |

Do NOT change these decisions without asking Tom.

---

## Pre-Work: Establish Regression Baseline

Before touching any file:

```bash
cd <repo>/frontend
pnpm --filter web test 2>&1 | tail -5
```

Record the exact count. Fix any pre-existing failures before starting.

---

## Pre-Work: Sync API Types

```bash
cd <repo>/frontend
pnpm sync-api-types
```

This batch does not add new hooks, but run it anyway to ensure types are current.

---

## Pre-Work: Read These Source Files

Use `read_file` on each of these before writing any code:

```
frontend/apps/web/src/features/settings/components/SettingsSidebar.tsx
  ← Understand the current SIDEBAR_ITEMS structure before modifying the Notifications group

frontend/apps/web/src/app/(authed)/settings/notifications/preferences/page.tsx
  ← Read the full existing unified page before adding to it

frontend/apps/web/src/app/(authed)/settings/notifications/page.tsx
  ← Check what this index page currently does (redirect target may need updating)

frontend/apps/web/src/app/(authed)/settings/notifications/email/page.tsx
  ← Understand current structure before replacing

frontend/apps/web/src/features/settings/components/NotificationEmailPrefsPage.tsx
  ← Read to understand the pattern before deleting

frontend/apps/web/src/features/settings/components/NotificationInAppPrefsPage.tsx
  ← READ IN FULL — contains the useRecentInAppNotifications logic that must be preserved

frontend/apps/web/src/features/notification-preferences/hooks/useRecentInAppNotifications.ts
  ← Understand hook signature and return shape before wiring into the unified page

frontend/apps/web/src/mocks/handlers/index.ts
  ← Understand handler registration before adding any new handlers
```

Also run:
```bash
# Find all test files that reference the deleted components
grep -rn "NotificationEmailPrefsPage\|NotificationSmsPrefsPage\|NotificationInAppPrefsPage" \
  frontend/apps/web/src/__tests__/ --include="*.tsx" -l

# Confirm the unified page's existing imports
grep -n "import" frontend/apps/web/src/app/(authed)/settings/notifications/preferences/page.tsx
```

---

## Context: What This Batch Does

The three single-channel notification pages (`/email`, `/sms`, `/in-app`) each show a 1-column toggle table and have a "View full notification preferences matrix →" link — an admission that a better page already exists. This batch eliminates the redundant pages and makes the full 3-column matrix the canonical destination.

| Surface | Before | After |
|---|---|---|
| Settings sidebar | Notifications (3 sub-items: Email, SMS, In-app) | Notifications (no sub-items, links to `/preferences`) |
| `/settings/notifications/email` | Single-column email toggles | `redirect("/settings/notifications/preferences")` |
| `/settings/notifications/sms` | Single-column SMS toggles | `redirect("/settings/notifications/preferences")` |
| `/settings/notifications/in-app` | Single-column in-app toggles + recent history | `redirect("/settings/notifications/preferences")` |
| `/settings/notifications/preferences` | Full 3-column matrix | Full 3-column matrix + recent in-app history section below |
| `NotificationEmailPrefsPage.tsx` | Exists | Deleted |
| `NotificationSmsPrefsPage.tsx` | Exists | Deleted |
| `NotificationInAppPrefsPage.tsx` | Exists | Deleted (logic absorbed) |

---

## STEP 1 — Update `SettingsSidebar.tsx`

**File**: `apps/web/src/features/settings/components/SettingsSidebar.tsx`

Read the file first. Find the `Notifications` entry in `SIDEBAR_ITEMS`:

```typescript
// BEFORE — remove this:
{
  label: "Notifications",
  href: "/settings/notifications",
  subItems: [
    { label: "Email", href: "/settings/notifications/email" },
    { label: "SMS", href: "/settings/notifications/sms" },
    { label: "In-app", href: "/settings/notifications/in-app" },
  ],
},

// AFTER — replace with this:
{
  label: "Notifications",
  href: "/settings/notifications/preferences",
  // No subItems — direct navigation to unified page
},
```

The `renderItem()` function handles active/ancestor state automatically — no other changes needed.

**Intermediate test run:**
```bash
pnpm --filter web test -- apps/web/src/features/settings/components/__tests__/SettingsSidebar.test.tsx 2>&1 | tail -8
```

Fix any test failures before proceeding. The `SettingsSidebar.test.tsx` file likely has tests for the old sub-item structure — update those tests to match the new single-item structure.

---

## STEP 2 — Update the Unified Preferences Page

**File**: `apps/web/src/app/(authed)/settings/notifications/preferences/page.tsx`

Read the full existing file first. Then:

1. **Add `useRecentInAppNotifications` import** — find the hook by reading `NotificationInAppPrefsPage.tsx` to get the exact import path
2. **Wire the hook** — call `useRecentInAppNotifications()` alongside the existing `useNotificationPreferences()` call
3. **Add the Recent In-App Notifications section** below the existing `<NotificationPreferenceMatrix>` — use the exact same rendering pattern you find in `NotificationInAppPrefsPage.tsx`
4. **Remove the "View full notification preferences matrix →" link** if it exists on this page (check the current file)

The page is already a `"use client"` component — no need to change that.

> **Adjust to match what you actually find** in the file. The examples above are starting points — your edit must match the actual imports, state variables, and JSX structure already present.

**Intermediate test run:**
```bash
pnpm --filter web test -- apps/web/src/app/(authed)/settings/notifications/ 2>&1 | tail -8
```

---

## STEP 3 — Replace 3 Sub-Route Pages with Redirects

**Files** (replace each entirely):
- `apps/web/src/app/(authed)/settings/notifications/email/page.tsx`
- `apps/web/src/app/(authed)/settings/notifications/sms/page.tsx`
- `apps/web/src/app/(authed)/settings/notifications/in-app/page.tsx`

Each becomes:

```tsx
/**
 * Redirects to unified notifications preferences page — UI-FIX-2C
 * Route: /settings/notifications/[email|sms|in-app]
 */
import { redirect } from "next/navigation";

export default function NotificationChannelRedirectPage() {
  redirect("/settings/notifications/preferences");
}
```

Note: use the same function name pattern for each file or give each a distinct name — Next.js doesn't care as long as it's the default export.

---

## STEP 4 — Verify/Update Notifications Index Page

**File**: `apps/web/src/app/(authed)/settings/notifications/page.tsx`

Read this file. If it currently redirects to `/email` or any other sub-page → update to redirect to `/settings/notifications/preferences`. If it already redirects to `/preferences` → no change needed.

---

## STEP 5 — Delete 3 Redundant Component Files

Delete these files entirely (they will no longer be imported anywhere after Steps 1–4):

- `apps/web/src/features/settings/components/NotificationEmailPrefsPage.tsx`
- `apps/web/src/features/settings/components/NotificationSmsPrefsPage.tsx`
- `apps/web/src/features/settings/components/NotificationInAppPrefsPage.tsx`

Before deleting, confirm with grep that nothing else imports them:

```bash
grep -rn "NotificationEmailPrefsPage\|NotificationSmsPrefsPage\|NotificationInAppPrefsPage" \
  frontend/apps/web/src/ --include="*.tsx" --include="*.ts"
```

If anything still imports them → fix those imports first, then delete.

---

## STEP 6 — Update/Delete Tests

### 6.1 — Find existing tests for the deleted components

```bash
grep -rn "NotificationEmailPrefsPage\|NotificationSmsPrefsPage\|NotificationInAppPrefsPage\|notifications/email\|notifications/sms\|notifications/in-app" \
  frontend/apps/web/src/__tests__/ --include="*.tsx" -l
```

For each test file found:
- If the test file is **exclusively testing one of the deleted components** → delete the test file
- If the test file tests other things too → remove only the tests for the deleted component, keep the rest

### 6.2 — Update `SettingsSidebar.test.tsx`

Read the existing sidebar test file. Update any tests that assert the presence of "Email", "SMS", or "In-app" sub-items under Notifications. These items no longer exist. The test should assert that "Notifications" appears as a single item with `href="/settings/notifications/preferences"`.

### 6.3 — Create integration test for the unified page

**File**: `apps/web/src/__tests__/batch_ui_fix_2c/notifications_unified.integration.test.tsx`

Minimum coverage:
1. The preferences page renders without crashing
2. `<NotificationPreferenceMatrix>` is present (use `testID="notification-preference-matrix"` which is already set in the page)
3. Recent in-app notifications section renders when there is data
4. Redirect pages navigate to `/settings/notifications/preferences`

```typescript
// Minimal test structure — adjust to match actual component interfaces
import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import React from "react";

vi.mock("next/navigation", () => ({
  usePathname: () => "/settings/notifications/preferences",
  useRouter: () => ({ push: vi.fn(), back: vi.fn(), replace: vi.fn() }),
  redirect: vi.fn(),
}));

// Mock the hooks — adjust import paths to match actual locations
vi.mock(
  "@/features/notification-preferences/hooks/useNotificationPreferences",
  () => ({
    useNotificationPreferences: () => ({
      preferences: [],
      categories: [],
      isLoading: false,
      isError: false,
      isPending: false,
      onCellChange: vi.fn(),
      onCellRevert: vi.fn(),
      onRowRevert: vi.fn(),
      onMuteAllPush: vi.fn(),
      onMuteAllEmail: vi.fn(),
      onResetAll: vi.fn(),
    }),
  }),
);

vi.mock(
  "@/features/notification-preferences/hooks/useRecentInAppNotifications",
  () => ({
    useRecentInAppNotifications: () => ({
      notifications: [],
      isLoading: false,
    }),
  }),
);

// Also mock NotificationPreferenceMatrix from @pilot/ui since it has its own internals
vi.mock("@pilot/ui", () => ({
  NotificationPreferenceMatrix: ({ testID }: { testID?: string }) =>
    React.createElement("div", { "data-testid": testID ?? "matrix" }, "Mock Matrix"),
}));
```

> **These are starting-point stubs.** Read the actual import paths from the real page file before finalizing mock paths.

---

## Final Verification

### Phase 1 — Targeted (run after each step)

```bash
cd <repo>/frontend
pnpm --filter web test -- apps/web/src/__tests__/batch_ui_fix_2c/ 2>&1 | tail -8
pnpm --filter web test -- apps/web/src/features/settings/components/__tests__/ 2>&1 | tail -8
```

### Phase 2 — Full (run once at the very end)

```bash
cd <repo>/frontend && echo "=== UI - Type Check ===" && pnpm --filter @pilot/ui check-types && echo "=== Web - Type Check ===" && pnpm --filter web check-types && echo "=== Mobile - Type Check ===" && pnpm --filter mobile build && echo "=== UI - Lint ===" && pnpm --filter @pilot/ui lint && echo "=== Web - Lint ===" && pnpm --filter web lint && echo "=== Mobile - Lint ===" && pnpm --filter mobile lint && echo "=== TYPE+LINT PASS ===" && echo "=== UI - Tests ===" && pnpm --filter @pilot/ui test 2>&1 | tail -6 && echo "=== Web - Tests ===" && pnpm --filter web test 2>&1 | tail -6 && echo "=== Mobile - Tests ===" && pnpm --filter mobile test 2>&1 | tail -8 && echo "=== MVP FINAL VERIFICATION COMPLETE ==="
```

> Any failure must be fixed before declaring done. No "pre-existing" exception without Tom's written confirmation.

---

## Definition of Done — UI-FIX-2C

- [ ] Pre-modification regression baseline captured (zero pre-existing failures, or confirmed with Tom)
- [ ] `pnpm sync-api-types` run — no new type errors
- [ ] All mandatory source files read before modifying
- [ ] **STEP 1**: `SettingsSidebar.tsx` Notifications group updated — 3 sub-items replaced with single direct link to `/preferences`; sidebar test updated
- [ ] **STEP 2**: `preferences/page.tsx` updated — `useRecentInAppNotifications` wired; recent history section renders below matrix; "View full..." link removed if present
- [ ] **STEP 3**: `/email/page.tsx`, `/sms/page.tsx`, `/in-app/page.tsx` all replaced with `redirect("/settings/notifications/preferences")`
- [ ] **STEP 4**: `/settings/notifications/page.tsx` index confirmed redirects to `/preferences`
- [ ] **STEP 5**: `NotificationEmailPrefsPage.tsx`, `NotificationSmsPrefsPage.tsx`, `NotificationInAppPrefsPage.tsx` deleted — grep confirms no remaining imports
- [ ] **STEP 6**: Test files for deleted components deleted or updated; new integration test created in `__tests__/batch_ui_fix_2c/`
- [ ] Zero TypeScript errors (`pnpm --filter web check-types` passes)
- [ ] Zero ESLint warnings
- [ ] Unit + integration tests pass (targeted run)
- [ ] **Phase 2 FULL verification command passes** (`=== MVP FINAL VERIFICATION COMPLETE ===`):
  ```bash
  cd <repo>/frontend && echo "=== UI - Type Check ===" && pnpm --filter @pilot/ui check-types && echo "=== Web - Type Check ===" && pnpm --filter web check-types && echo "=== Mobile - Type Check ===" && pnpm --filter mobile build && echo "=== UI - Lint ===" && pnpm --filter @pilot/ui lint && echo "=== Web - Lint ===" && pnpm --filter web lint && echo "=== Mobile - Lint ===" && pnpm --filter mobile lint && echo "=== TYPE+LINT PASS ===" && echo "=== UI - Tests ===" && pnpm --filter @pilot/ui test 2>&1 | tail -6 && echo "=== Web - Tests ===" && pnpm --filter web test 2>&1 | tail -6 && echo "=== Mobile - Tests ===" && pnpm --filter mobile test 2>&1 | tail -8 && echo "=== MVP FINAL VERIFICATION COMPLETE ==="
  ```
- [ ] Final test count (before → after) documented
- [ ] Completion Summary added to `ui-fix-2-decisions.md` batch overview section

---

## Completion Summary

After all Definition of Done items are complete, add a Completion Summary to `dev-docs/architecture-design/batch-designs/ui-fix-2-decisions.md` under the UI-FIX-2C batch row:

```markdown
### UI-FIX-2C — Notifications Settings Consolidation: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot React Engineer
**Baseline**: X passed (web)
**Final**: X+N passed (+N new tests)

#### What Was Accomplished

- `SettingsSidebar.tsx` Notifications sub-nav collapsed to single direct link → `/settings/notifications/preferences`
- `preferences/page.tsx` updated — `useRecentInAppNotifications` wired, recent history section added below matrix
- 3 single-channel sub-routes (`/email`, `/sms`, `/in-app`) replaced with redirects to `/preferences`
- `NotificationEmailPrefsPage`, `NotificationSmsPrefsPage`, `NotificationInAppPrefsPage` deleted
- All related tests updated or deleted

#### Files Changed / Created

| File | Action |
|---|---|
| `apps/web/src/features/settings/components/SettingsSidebar.tsx` | Updated — Notifications sub-items collapsed |
| `apps/web/src/app/(authed)/settings/notifications/preferences/page.tsx` | Updated — added recent in-app section |
| `apps/web/src/app/(authed)/settings/notifications/email/page.tsx` | Updated — redirect |
| `apps/web/src/app/(authed)/settings/notifications/sms/page.tsx` | Updated — redirect |
| `apps/web/src/app/(authed)/settings/notifications/in-app/page.tsx` | Updated — redirect |
| `apps/web/src/features/settings/components/NotificationEmailPrefsPage.tsx` | Deleted |
| `apps/web/src/features/settings/components/NotificationSmsPrefsPage.tsx` | Deleted |
| `apps/web/src/features/settings/components/NotificationInAppPrefsPage.tsx` | Deleted |
| `apps/web/src/__tests__/batch_ui_fix_2c/notifications_unified.integration.test.tsx` | Created |

#### Tests Added

| Test File | Type | Tests | All Pass |
|---|---|---|---|
| `__tests__/batch_ui_fix_2c/notifications_unified.integration.test.tsx` | Integration | N | ✅ |
```

---

## After This Batch

UI-FIX-2C is independent — no other batch depends on it. After completion:
- Continue with any other UI-FIX-2 batch in parallel
- The unified `/settings/notifications/preferences` page is the permanent Notifications settings home
