# Implementation Prompt: FE-UI-NAV-S1 — Settings Navigation Redesign (Frontend)

**Mode**: Pilot React Engineer  
**Batch**: `FE-UI-NAV-S1`  
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §2 Active Dev Work Queue  
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-fe-ui-nav-s1-design.md`  
**UI spec**: `dev-docs/architecture-design/batch-designs/batch-ui-nav-s1-ui-design-spec.md`  
**Estimated session**: 4–6 hours  
**Platform**: Web only (`apps/web`) + Shared UI (`packages/ui`)  
**Backend companion**: `BE-UI-NAV-S1` must complete first. MSW handlers cover avatar + tenant-policy endpoints until the backend is merged.  

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-react-engineer/react-engineer-rules.md`** — in full
- **`dev-docs/architecture-design/batch-designs/batch-fe-ui-nav-s1-design.md`** — every section (A–I)
- **`dev-docs/architecture-design/batch-designs/batch-ui-nav-s1-ui-design-spec.md`** — §15, §16A, §20.3, §21, §22, §29 (the confirmed decisions)

**Critical rules for this batch:**

- **Rule 1.1**: Before writing ANY hook or API call, verify the endpoint exists in `backend/openapi_schema_map.md`. For avatar + tenant-policy endpoints that are NOT yet there (backend batch pending): write MSW stubs and document as Companion Backend Tasks.
- **Rule 1.2**: Do NOT invent URL patterns. Every endpoint shape comes from the design doc (§D, which was authored from the backend batch design).
- **Rule 1.3**: Run `pnpm sync-api-types` before starting — all TypeScript types for backend payloads come from `@pilot/shared-types`.
- **Rule 2**: All API calls use `apiClient` from `@pilot/shared-api`. `fetch()` is permanently banned for `/api/v1/...` calls.
- **Rule 7**: Check `packages/ui/src/index.ts` before creating any new component — `<LoadingState>`, `<ErrorState>`, `<RoleGate>`, `<NotificationPreferenceMatrix>` (if it exists) are available.
- **Rule 8**: No new npm dependencies (e.g., `react-easy-crop`) without first checking `package.json`. If not installed → implement a simplified crop without the library. Do NOT install new packages without Tom's approval.
- **Rule 9**: Route files in `apps/web/src/app/(authed)/` MUST be thin server components — no `"use client"`, no data fetching.
- **Rule 10**: If ANY test fails — fix it before declaring the batch done.

---

## Design Decisions (Do Not Re-Litigate)

From design doc §G and UI spec §22 — these decisions are final:

| Decision | Outcome | Rationale |
|---|---|---|
| Settings navigation pattern | **Option 3 — Stripe/Clio Settings Index Page** | Eliminates double-sidebar; most scannable |
| `SettingsDropdownPanel` | **Not built** — gear navigates to `/settings` directly | SettingsGearIcon already does this |
| AppSidebar expanded width | **`w-fit min-w-[160px] max-w-[200px]`** (drop `style={{ width }}`) | Recovers ~56px wasted whitespace |
| Collapse toggle | **Option A — `«`/`»` pill button, top-right border overlap** | Most discoverable; moves toggle from bottom |
| ProfileDropdown items | **3 items: My Profile + Security + Notifications** | Subscription/Payment Method removed; Notifications added |
| Avatar dropdown arrow | **No arrow — hover ring only** (`hover:ring-2 hover:ring-brand-300`) | Matches Stripe/Linear pattern |
| Profile photo upload | **Yes — implement with presigned S3 flow** | MSW stub until BE-UI-NAV-S1 lands |
| Notifications arch | **Two separate pages** — personal via ProfileDropdown; tenant defaults via Settings Index | No tab strip |

Do NOT change these without asking Tom.

---

## Companion Backend Tasks (MSW — Do Not Block React Work)

The following endpoints are required but not yet in `openapi_schema_map.md` (pending `BE-UI-NAV-S1`):

| # | What's Needed | Endpoint | Notes |
|---|---|---|---|
| BE-01 | Avatar presigned upload URL | `POST /api/v1/users/me/avatar/presigned-url` | Returns `{ upload_url, s3_key }` |
| BE-02 | Avatar delete | `DELETE /api/v1/users/me/avatar` | Returns `{ success: true }` |
| BE-03 | Tenant policy bulk GET | `GET /api/v1/notifications/tenant-policy` | Returns `{ policies: [{category_id, channel, enabled}] }` |
| BE-04 | Tenant policy bulk DELETE (reset) | `DELETE /api/v1/notifications/tenant-policy` | Returns `{ deleted_count: N }` |
| BE-05 | `profile_photo_url` in profile GET | `GET /api/v1/users/me/profile` (modified) | `profile_photo_url: string \| null` added to response |

Build MSW handlers for all 5. After `BE-UI-NAV-S1` merges and `pnpm sync-api-types` is run, replace stubs with real hook calls.

---

## Pre-Work: Establish Regression Baseline

Before touching any file:

```bash
cd <repo>/frontend

# Web tests
pnpm --filter web test 2>&1 | tail -5

# Shared UI (if touching packages/ui)
pnpm --filter @pilot/ui test 2>&1 | tail -5
```

Record exact counts. Fix any pre-existing failures or confirm with Tom before proceeding.

---

## Pre-Work: Sync API Types

```bash
cd <repo>/frontend
pnpm sync-api-types
```

If `pnpm sync-api-types` fails because avatar endpoints are not yet deployed → note the affected types, write stubs marked `// TODO: remove when BE-UI-NAV-S1 lands`, and proceed with MSW.

---

## Pre-Work: Verify Endpoints

For existing endpoints (already in `openapi_schema_map.md`):

```bash
grep -A 5 "users/me/profile" backend/openapi_schema_map.md
grep -A 5 "notifications/preferences" backend/openapi_schema_map.md
grep -A 5 "notification-categories" backend/openapi_schema_map.md
```

For new endpoints (expected to be absent until BE-UI-NAV-S1):
```bash
grep "avatar/presigned-url\|tenant-policy" backend/openapi_schema_map.md || echo "Not yet — use MSW stubs"
```

Verified endpoints for this batch:
| Hook | Endpoint | Status |
|---|---|---|
| `useProfile` (existing) | `GET /api/v1/users/me/profile` | ✅ Exists |
| `usePatchProfile` (existing) | `PATCH /api/v1/users/me/profile` | ✅ Exists |
| `useNotificationPreferences` (existing) | `GET /api/v1/notifications/preferences` | ✅ Exists |
| `useAvatarPresignedUrl` | `POST /api/v1/users/me/avatar/presigned-url` | ⏳ MSW stub |
| `useAvatarDelete` | `DELETE /api/v1/users/me/avatar` | ⏳ MSW stub |
| `useTeamNotificationDefaults` | `GET /api/v1/notifications/tenant-policy` | ⏳ MSW stub |
| `useTeamNotificationDefaultsReset` | `DELETE /api/v1/notifications/tenant-policy` | ⏳ MSW stub |

---

## Pre-Work: Read These Source Files

Use `read_file` on each before writing any code:

```
frontend/apps/web/src/components/AppSidebar.tsx                               ← understand current width + toggle pattern
frontend/apps/web/src/app/(authed)/layout.tsx                                ← understand sidebar/header structure
frontend/apps/web/src/components/ProfileDropdown.tsx                         ← understand current 4-item dropdown
frontend/apps/web/src/components/SettingsGearIcon.tsx                        ← confirm already calls router.push("/settings")
frontend/apps/web/src/features/settings/components/SettingsShell.tsx         ← understand what to remove
frontend/apps/web/src/features/settings/components/SettingsSidebar.tsx       ← understand current structure (to be deprecated)
frontend/apps/web/src/app/(authed)/settings/page.tsx                         ← current stub to replace
frontend/apps/web/src/hooks/useSidebarState.ts                               ← understand sidebar state hook
frontend/packages/ui/src/index.ts                                            ← confirm available shared components
frontend/packages/ui/src/role-gate/permissions.ts                            ← confirm PermissionKey union before extending
frontend/apps/web/src/mocks/handlers/index.ts                                ← how to register new MSW handlers
```

Also run:
```bash
# Find existing notification preference components
find frontend/apps/web/src/features/notification-preferences -name "*.tsx" -o -name "*.ts" | head -20

# Find ProfileSettingsPage
find frontend/apps/web/src -name "ProfileSettings*" | head -5

# Confirm all settings sub-page files that use SettingsShell
grep -rl "SettingsShell" frontend/apps/web/src/app/ | head -20

# Check for existing crop library
grep "react-easy-crop\|react-avatar-editor" frontend/apps/web/package.json
```

---

## MSW Handlers for Missing Endpoints

**Step 1 — Check existing handler files:**
```bash
find frontend/apps/web/src/mocks/handlers -name "*.ts" | head -20
cat frontend/apps/web/src/mocks/handlers/index.ts
```

**Step 2 — Create `settingsNavHandlers.ts`:**

```typescript
// apps/web/src/mocks/handlers/settingsNavHandlers.ts
import { http, HttpResponse } from "msw";

export const settingsNavHandlers = [
  // BE-01: Avatar presigned upload URL
  http.post("/api/v1/users/me/avatar/presigned-url", () =>
    HttpResponse.json(
      {
        upload_url: "https://mock-s3.example.com/presigned-put-url",
        s3_key: "avatars/mock-tenant/mock-user/avatar.jpg",
      },
      { status: 201 },
    ),
  ),

  // BE-02: Avatar delete
  http.delete("/api/v1/users/me/avatar", () =>
    HttpResponse.json({ success: true }),
  ),

  // BE-03: Tenant notification policy GET
  http.get("/api/v1/notifications/tenant-policy", () =>
    HttpResponse.json({
      policies: [
        { category_id: "job_activity", channel: "email", enabled: true },
        { category_id: "job_activity", channel: "sms", enabled: false },
      ],
    }),
  ),

  // BE-04: Tenant notification policy reset
  http.delete("/api/v1/notifications/tenant-policy", () =>
    HttpResponse.json({ deleted_count: 2 }),
  ),
];
```

**Step 3 — Register in `index.ts`:**

```typescript
// apps/web/src/mocks/handlers/index.ts — add:
import { settingsNavHandlers } from "./settingsNavHandlers";

export const handlers = [
  ...existingHandlers,
  ...settingsNavHandlers, // ← ADD
];
```

> **This step is mandatory.** Creating the file without registering it in `index.ts` means the handlers are never loaded.

---

## Context: What This Batch Does

| Task | Files Changed | Design Spec |
|---|---|---|
| 1. AppSidebar: w-fit + pill toggle | `AppSidebar.tsx` | §15, §16A |
| 2. ProfileDropdown: 3 items + hover ring + photo | `ProfileDropdown.tsx` | §20.3, §29.2 |
| 3. PilotUser type: `profile_photo_url` | `packages/ui/src/auth/types.ts` | §21.5 |
| 4. Settings Index Page (replace stub) | `/settings/page.tsx` + `SettingsIndexPage.tsx` (new) | §17.5, §29.3 |
| 5. Remove SettingsShell from all sub-pages | All `/settings/*/page.tsx` using `<SettingsShell>` | §17.7 |
| 6. Tenant notification defaults page | `/settings/notifications/tenant-defaults/page.tsx` (new) + `TenantNotificationDefaultsPage.tsx` (new) + `useTeamNotificationDefaults.ts` (new) | §29.4 |
| 7. Avatar upload UI + crop modal | `ProfileSettingsPage.tsx` + `AvatarCropModal.tsx` (new) + `useAvatarUpload.ts` (new) | §21.3–§21.4 |
| 8. MSW handlers | `settingsNavHandlers.ts` (new) + `index.ts` update | — |
| 9. Tests | Various | — |

---

## STEP 1 — AppSidebar: w-fit Width + Pill Toggle

**File**: `apps/web/src/components/AppSidebar.tsx`

Read the file before modifying. It currently uses `style={{ width: sidebarWidth }}` with `"16rem"` / `"4rem"`.

**Changes:**

1. **Remove `const sidebarWidth = ...` and `style={{ width: sidebarWidth }}` from `<nav>`.**

2. **Replace with Tailwind classes on the `<nav>` element:**
```tsx
className={`flex flex-col h-full bg-white border-r border-neutral-200 shrink-0 overflow-hidden relative
  ${isSidebarCollapsed
    ? "w-16"
    : "w-fit min-w-[160px] max-w-[200px]"
  }`}
```

3. **Remove the bottom toggle button** (the `<div className="border-t ...">` block at the bottom of `<nav>`).

4. **Add the pill toggle button** — positioned `absolute top-3 -right-3` to overlap the sidebar/content border:

```tsx
{/* Pill toggle — overlaps sidebar right border (z-20 to stay above nav content) */}
<button
  type="button"
  onClick={toggleSidebar}
  aria-label={isSidebarCollapsed ? "Expand navigation" : "Collapse navigation"}
  title={isSidebarCollapsed ? "Expand navigation" : "Collapse navigation"}
  className="absolute top-3 -right-3 z-20 flex items-center justify-center w-6 h-6 rounded-full bg-white border border-neutral-200 shadow-sm hover:bg-neutral-50 transition-colors duration-150 cursor-pointer"
>
  <ChevronDoubleLeftIcon
    className={`w-3 h-3 text-neutral-500 transition-transform duration-200 ease-in-out ${
      isSidebarCollapsed ? "rotate-180" : "rotate-0"
    }`}
    aria-hidden="true"
  />
</button>
```

5. **Add `ChevronDoubleLeftIcon` to heroicons imports** (replace `ChevronLeftIcon` + `ChevronRightIcon` imports):
```tsx
import { ChevronDoubleLeftIcon } from "@heroicons/react/24/outline";
```

6. **Remove unused `ChevronLeftIcon` and `ChevronRightIcon` imports.**

> **Animation note** (spec §16A): Remove `transition-[width]` from `<nav>` — collapse is instant (acceptable B2B UX). This is because CSS cannot animate `w-fit`. The icon rotates with `transition-transform` for visual feedback.

> **`layout.tsx` note** (read before editing): The spec says to add a `relative` wrapper around `<AppSidebar />` in `layout.tsx`. However, since the pill is already `absolute` *inside* `AppSidebar` (which is now `relative`), the layout wrapper is NOT needed. The pill is a sibling to `<ul>` inside the `<nav>`, not outside the component.

**Intermediate verification:**
```bash
cd <repo>/frontend
pnpm --filter web test -- apps/web/src/components/__tests__/AppSidebar.test.tsx 2>&1 | tail -10
```

---

## STEP 2 — ProfileDropdown: 3 Items + Hover Ring + Photo

**File**: `apps/web/src/components/ProfileDropdown.tsx`

Read the file before modifying. It currently has 4 `DROPDOWN_ITEMS`.

**Changes:**

1. **Update `DROPDOWN_ITEMS`** — remove Subscription + Payment Method; add Notifications:

```tsx
const DROPDOWN_ITEMS = [
  { label: "My Profile", href: "/settings/my-account/profile" },
  { label: "Security", href: "/settings/my-account/security" },
  { label: "Notifications", href: "/settings/notifications/preferences" },
] as const;
```

2. **Add hover ring to avatar button** (spec §20.3):

```tsx
// Before: ...bg-brand-600 hover:bg-brand-700 transition-colors...
// After:
className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-semibold text-white bg-brand-600 hover:bg-brand-700 hover:ring-2 hover:ring-brand-300 hover:ring-offset-1 transition-all duration-150 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2"
```

3. **Conditionally render photo** (spec §21.2). The `user` object from `useAuth()` will have `profile_photo_url` after Step 3 adds it to `PilotUser`. Add the conditional render:

```tsx
{/* Avatar button interior */}
{user?.profile_photo_url ? (
  <img
    src={user.profile_photo_url}
    alt={user.displayName ?? "Profile"}
    className="w-full h-full rounded-full object-cover object-center"
    onError={(e) => {
      // Fallback to initials if image fails to load
      (e.target as HTMLImageElement).style.display = "none";
    }}
  />
) : (
  initials
)}
```

> **Note**: `user.profile_photo_url` will be `undefined` until Step 3 is complete and `pnpm sync-api-types` delivers the type. Mark with a comment if the type error appears; it resolves after Step 3.

---

## STEP 3 — PilotUser Type: Add `profile_photo_url`

**File**: Find the exact path with:
```bash
grep -rn "PilotUser\|interface.*User" frontend/packages/ui/src/auth/ | head -10
```

Add `profile_photo_url?: string | null` to the `PilotUser` interface.

```typescript
// Adjust to match the actual interface you find:
export interface PilotUser {
  // ... existing fields ...
  profile_photo_url?: string | null;  // ← ADD (populated from GET /api/v1/users/me/profile)
}
```

After modifying `packages/ui/src/auth/types.ts` (or wherever `PilotUser` lives), run:
```bash
pnpm --filter @pilot/ui check-types 2>&1 | tail -10
pnpm --filter @pilot/ui test 2>&1 | tail -5
```

---

## STEP 4 — Settings Index Page

**Files**:
- `apps/web/src/app/(authed)/settings/page.tsx` — replace stub
- `apps/web/src/features/settings/components/SettingsIndexPage.tsx` — new component

**Step 4a** — Replace the route file stub:

```tsx
// apps/web/src/app/(authed)/settings/page.tsx
// Thin server component — no "use client", no data fetching
import { SettingsIndexPage } from "@/features/settings/components/SettingsIndexPage";

export default function SettingsPage() {
  return <SettingsIndexPage />;
}
```

**Step 4b** — Create `SettingsIndexPage.tsx`:

```tsx
// apps/web/src/features/settings/components/SettingsIndexPage.tsx
"use client";

import Link from "next/link";
import { RoleGate } from "@pilot/ui/role-gate";
import {
  UserCircleIcon,
  ShieldCheckIcon,
  UsersIcon,
  AdjustmentsHorizontalIcon,
  BellIcon,
  SwatchIcon,
  MicrophoneIcon,
  ArrowsRightLeftIcon,
  CloudArrowUpIcon,
  LockClosedIcon,
} from "@heroicons/react/24/outline";
import type { PermissionKey } from "@pilot/ui/role-gate";

// Adjust to match the actual HeroIcon ElementType used in AppSidebar.tsx
type HeroIcon = React.ElementType<{ className?: string; "aria-hidden"?: boolean | "false" | "true" }>;

interface SettingsCard {
  label: string;
  icon: HeroIcon;
  description: string;
  href: string;
  permission?: PermissionKey;
}

interface SettingsSection {
  title: string;
  permission?: PermissionKey;  // gates entire section
  cards: SettingsCard[];
}

const SETTINGS_SECTIONS: SettingsSection[] = [
  {
    title: "Personal",
    cards: [
      { label: "Profile & Account", icon: UserCircleIcon, description: "Your name, email, photo, and account preferences", href: "/settings/my-account/profile" },
      { label: "Security", icon: ShieldCheckIcon, description: "Password, MFA enrollment, and active sessions", href: "/settings/security" },
    ],
  },
  {
    title: "Workspace",
    permission: "settings.tenant.write",
    cards: [
      { label: "Team", icon: UsersIcon, description: "Manage team members, roles, and permissions", href: "/settings/team" },
      { label: "Operations", icon: AdjustmentsHorizontalIcon, description: "Margin buckets, profitability rules, and field operation defaults", href: "/settings/operations" },
      { label: "Notifications", icon: BellIcon, description: "Set default notification preferences for new team members", href: "/settings/notifications/tenant-defaults" },
      { label: "Branding", icon: SwatchIcon, description: "Email branding, SMS compliance, and 10DLC registration", href: "/settings/communications" },
      { label: "Voice & AI", icon: MicrophoneIcon, description: "Voice capture settings and AI transcription preferences", href: "/settings/voice-ai" },
    ],
  },
  {
    title: "Integrations & System",
    cards: [
      { label: "Integrations", icon: ArrowsRightLeftIcon, description: "Connect QuickBooks, calendar, and third-party apps", href: "/settings/integrations", permission: "integrations.manage" },
      { label: "Sync & Storage", icon: CloudArrowUpIcon, description: "Background sync, offline data limits, photos, and voice file storage", href: "/settings/sync-storage", permission: "settings.tenant.write" },
      { label: "Data & Privacy", icon: LockClosedIcon, description: "Data export, retention policies, and privacy settings", href: "/settings/data-privacy" },
    ],
  },
];

function SettingsCardItem({ card }: { card: SettingsCard }) {
  const Icon = card.icon;
  const content = (
    <Link
      href={card.href}
      className="group block bg-white border border-neutral-200 rounded-lg p-5 shadow-sm hover:shadow-md hover:border-brand-200 transition-all duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
    >
      <div className="flex items-center gap-3">
        <Icon className="w-5 h-5 text-brand-500 shrink-0" aria-hidden="true" />
        <span className="text-sm font-semibold text-brand-600 group-hover:text-brand-700">
          {card.label}
        </span>
      </div>
      <p className="mt-2 text-sm text-neutral-500 leading-relaxed">
        {card.description}
      </p>
    </Link>
  );

  if (card.permission) {
    return <RoleGate permission={card.permission}>{content}</RoleGate>;
  }
  return content;
}

export function SettingsIndexPage() {
  return (
    <div className="bg-neutral-50 flex-1 min-h-0 overflow-y-auto">
      <div className="max-w-5xl mx-auto px-6 py-8">
        {/* Page header */}
        <div className="mb-8">
          <h1 className="text-h1 font-semibold text-neutral-900">Settings</h1>
          <p className="text-sm text-neutral-500 mt-1">
            Manage your account, workspace, and integrations
          </p>
        </div>

        {/* Sections */}
        {SETTINGS_SECTIONS.map((section) => {
          const sectionContent = (
            <div key={section.title} className="mt-8 first:mt-0">
              <div className="pb-2 mb-6 border-b border-neutral-200">
                <h2 className="text-h2 font-semibold text-neutral-900">{section.title}</h2>
              </div>
              <div className="grid grid-cols-3 gap-4 mb-10 lg:grid-cols-2 md:grid-cols-1">
                {section.cards.map((card) => (
                  <SettingsCardItem key={card.href} card={card} />
                ))}
              </div>
            </div>
          );

          if (section.permission) {
            return (
              <RoleGate key={section.title} permission={section.permission}>
                {sectionContent}
              </RoleGate>
            );
          }
          return sectionContent;
        })}
      </div>
    </div>
  );
}
```

> **Read before writing**: Verify `RoleGate` import path from `packages/ui/src/index.ts`. Confirm exact Tailwind `text-h1` / `text-h2` token names are used elsewhere in the app (grep for them in other settings pages).

---

## STEP 5 — Remove SettingsShell from All Settings Sub-Pages

This is the largest task in scope but lowest in complexity — it is pure surgical removal.

**Step 5a** — Run this to find all files using `SettingsShell`:
```bash
grep -rl "SettingsShell" frontend/apps/web/src/app/ | sort
```

**Step 5b** — For each file found, `read_file` it, then apply the following transformation:

**Before** (typical pattern):
```tsx
import { SettingsShell } from "@/features/settings/components/SettingsShell";

export default function SomeSettingsPage() {
  return (
    <SettingsShell>
      <SomeContent />
    </SettingsShell>
  );
}
```

**After**:
```tsx
import { SettingsBreadcrumb } from "@/features/settings/components/SettingsBreadcrumb";

export default function SomeSettingsPage() {
  return (
    <div className="flex-1 bg-neutral-50 overflow-y-auto">
      <div className="mx-auto max-w-3xl px-6 py-8 space-y-6">
        <SettingsBreadcrumb />
        <SomeContent />
      </div>
    </div>
  );
}
```

> **Important**: Read `SettingsBreadcrumb.tsx` before adding it — confirm it is a standalone component that does not require `SettingsShell` as a parent. If it renders fine standalone, add it. If it has a dependency on `SettingsShell`, leave it out and just render the content directly.

> **Some pages may use `catalog` prop on `SettingsShell`** (search pattern). If a page passes a `catalog` prop, the underlying search functionality lived in `SettingsSidebar`. Drop the `catalog` prop — the settings sidebar is being deprecated. The `SettingsSidebarSearch` is no longer rendered in the new architecture.

After completing all files:
```bash
# Verify no remaining SettingsShell imports
grep -rl "SettingsShell" frontend/apps/web/src/app/ | wc -l
# Expected: 0
```

---

## STEP 6 — Tenant Notification Defaults Page

**Files**:
- `apps/web/src/app/(authed)/settings/notifications/tenant-defaults/page.tsx` (new thin route)
- `apps/web/src/features/settings/components/TenantNotificationDefaultsPage.tsx` (new feature component)
- `apps/web/src/features/notification-preferences/hooks/useTeamNotificationDefaults.ts` (new hook)

**Step 6a** — Find and read the existing `NotificationPreferenceMatrix` component:
```bash
find frontend/apps/web/src/features/notification-preferences -name "NotificationPreferenceMatrix*" | head -5
grep -n "NotificationPreferenceMatrix" frontend/packages/ui/src/index.ts
```

**Step 6b** — Create the hook `useTeamNotificationDefaults.ts`:

```typescript
// apps/web/src/features/notification-preferences/hooks/useTeamNotificationDefaults.ts
"use client";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";

// TODO: delete when pnpm sync-api-types delivers BE-UI-NAV-S1 types
interface TeamNotificationDefault {
  category_id: string;
  channel: string;
  enabled: boolean;
}

interface TeamNotificationDefaultsResponse {
  policies: TeamNotificationDefault[];
}

interface TeamNotificationDefaultsResetResponse {
  deleted_count: number;
}

const QUERY_KEY = ["notifications", "tenant-policy"] as const;

export function useTeamNotificationDefaults() {
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: QUERY_KEY,
    queryFn: async () => {
      const resp = await apiClient.get<TeamNotificationDefaultsResponse>(
        "/api/v1/notifications/tenant-policy",
      );
      return resp.data;
    },
    retry: false,
  });

  const resetMutation = useMutation({
    mutationFn: async () => {
      const resp = await apiClient.delete<TeamNotificationDefaultsResetResponse>(
        "/api/v1/notifications/tenant-policy",
      );
      return resp.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEY });
    },
    retry: false,
  });

  return {
    policies: query.data?.policies ?? [],
    isLoading: query.isLoading,
    error: query.error,
    reset: resetMutation.mutate,
    isResetting: resetMutation.isPending,
  };
}
```

**Step 6c** — Create `TenantNotificationDefaultsPage.tsx`:

```tsx
// apps/web/src/features/settings/components/TenantNotificationDefaultsPage.tsx
"use client";
import { useState } from "react";
import { LoadingState, ErrorState } from "@pilot/ui/states";
import { useTeamNotificationDefaults } from "@/features/notification-preferences/hooks/useTeamNotificationDefaults";
// Read the actual import path for NotificationPreferenceMatrix from the codebase

export function TenantNotificationDefaultsPage() {
  const { policies, isLoading, error, reset, isResetting } = useTeamNotificationDefaults();
  const [showConfirm, setShowConfirm] = useState(false);

  if (isLoading) return <LoadingState />;
  if (error) return <ErrorState message="Failed to load team notification defaults" />;

  return (
    <div>
      <div className="mb-6">
        <h2 className="text-h2 font-semibold text-neutral-900">
          Team notification defaults
        </h2>
        <p className="text-sm text-neutral-500 mt-1">
          Set the default notification preferences for new team members.
          Individual users can override their own settings from their profile menu.
        </p>
      </div>

      {/* NotificationPreferenceMatrix — read existing component props before wiring */}
      {/* Wire policies from useTeamNotificationDefaults */}

      {/* Reset action */}
      <div className="mt-8">
        {showConfirm ? (
          <div className="flex items-center gap-3">
            <span className="text-sm text-neutral-600">
              Reset all to system defaults?
            </span>
            <button
              type="button"
              onClick={() => { reset(); setShowConfirm(false); }}
              disabled={isResetting}
              className="text-sm bg-fault-600 text-white rounded-md px-4 py-2 hover:bg-fault-700 disabled:opacity-50"
            >
              {isResetting ? "Resetting…" : "Confirm reset"}
            </button>
            <button
              type="button"
              onClick={() => setShowConfirm(false)}
              className="text-sm border border-neutral-300 text-neutral-700 rounded-md px-4 py-2 hover:bg-neutral-50"
            >
              Cancel
            </button>
          </div>
        ) : (
          <button
            type="button"
            onClick={() => setShowConfirm(true)}
            className="text-sm text-fault-600 hover:text-fault-700 hover:underline"
          >
            Reset all to system defaults
          </button>
        )}
      </div>
    </div>
  );
}
```

> **Read the existing `NotificationPreferenceMatrix` component before wiring it.** Understand its props signature from its source file. The `policies` array from `useTeamNotificationDefaults` must be adapted to whatever shape `NotificationPreferenceMatrix` accepts. Do not assume — read the component first.

**Step 6d** — Create the thin route file:

```tsx
// apps/web/src/app/(authed)/settings/notifications/tenant-defaults/page.tsx
import { redirect } from "next/navigation";
import { RoleGate } from "@pilot/ui/role-gate";
import { SettingsBreadcrumb } from "@/features/settings/components/SettingsBreadcrumb";
import { TenantNotificationDefaultsPage } from "@/features/settings/components/TenantNotificationDefaultsPage";

// RBAC: non-owner roles redirect to personal preferences
// Note: RoleGate hides content but doesn't redirect — handle redirect server-side
// if the role check is needed at the server level, use a simple conditional.
export default function TenantNotificationDefaultsRoute() {
  return (
    <div className="flex-1 bg-neutral-50 overflow-y-auto">
      <div className="mx-auto max-w-3xl px-6 py-8 space-y-6">
        <SettingsBreadcrumb />
        <RoleGate permission="settings.tenant.write">
          <TenantNotificationDefaultsPage />
        </RoleGate>
      </div>
    </div>
  );
}
```

---

## STEP 7 — Avatar Upload UI + Crop Modal

**Step 7a** — Read `ProfileSettingsPage.tsx` before modifying:
```bash
find frontend/apps/web/src/features/settings -name "ProfileSettings*" | head -5
```

**Step 7b** — Check for crop library:
```bash
grep "react-easy-crop\|react-avatar-editor" frontend/apps/web/package.json
```

If **not** installed → implement a simple placeholder crop (Step 7c). Do NOT install the library without Tom's approval.

**Step 7c** — Create `AvatarCropModal.tsx`:

If no crop library is available, implement a simplified version that accepts the image and lets the user confirm upload without cropping:

```tsx
// apps/web/src/components/AvatarCropModal.tsx
"use client";
import { useCallback } from "react";

interface AvatarCropModalProps {
  imageFile: File;
  onSave: (croppedBlob: Blob) => void;
  onCancel: () => void;
}

export function AvatarCropModal({ imageFile, onSave, onCancel }: AvatarCropModalProps) {
  const imageUrl = URL.createObjectURL(imageFile);

  const handleSave = useCallback(() => {
    // Simplified: use the original file as a JPEG blob at 256×256 via canvas
    const img = new Image();
    img.onload = () => {
      const canvas = document.createElement("canvas");
      canvas.width = 256;
      canvas.height = 256;
      const ctx = canvas.getContext("2d")!;
      // Center-crop square from the image
      const size = Math.min(img.width, img.height);
      const x = (img.width - size) / 2;
      const y = (img.height - size) / 2;
      ctx.drawImage(img, x, y, size, size, 0, 0, 256, 256);
      canvas.toBlob(
        (blob) => { if (blob) onSave(blob); },
        "image/jpeg",
        0.9,
      );
      URL.revokeObjectURL(imageUrl);
    };
    img.src = imageUrl;
  }, [imageFile, onSave, imageUrl]);

  return (
    <div className="fixed inset-0 bg-neutral-900/50 z-50 flex items-start justify-center pt-16">
      <div className="bg-white rounded-lg shadow-xl max-w-sm w-full mx-4 p-6">
        <h3 className="text-h3 font-medium text-neutral-900 mb-4">Crop photo</h3>
        <div className="w-60 h-60 mx-auto rounded-full overflow-hidden border-2 border-neutral-200 mb-4">
          <img src={imageUrl} alt="Preview" className="w-full h-full object-cover" />
        </div>
        <div className="flex gap-3 justify-end">
          <button
            type="button"
            onClick={onCancel}
            className="border border-neutral-300 text-neutral-700 rounded-md px-4 py-2 text-sm hover:bg-neutral-50"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleSave}
            className="bg-brand-600 text-white rounded-md px-4 py-2 text-sm font-medium hover:bg-brand-700"
          >
            Save photo
          </button>
        </div>
      </div>
    </div>
  );
}
```

**Step 7d** — Create `useAvatarUpload.ts`:

```typescript
// apps/web/src/features/settings/hooks/useAvatarUpload.ts
import { useMutation } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";

// TODO: replace with @pilot/shared-types type when BE-UI-NAV-S1 delivers it
interface PresignedUrlResponse {
  upload_url: string;
  s3_key: string;
}

export function useAvatarUpload() {
  return useMutation({
    mutationFn: async (croppedBlob: Blob) => {
      // Step 1: Get presigned URL
      const { data } = await apiClient.post<PresignedUrlResponse>(
        "/api/v1/users/me/avatar/presigned-url",
      );

      // Step 2: Upload blob directly to S3 (raw fetch — this is NOT an API call, it's S3)
      await fetch(data.upload_url, {
        method: "PUT",
        body: croppedBlob,
        headers: { "Content-Type": "image/jpeg" },
      });

      // Step 3: Save s3_key to user profile
      await apiClient.patch("/api/v1/users/me/profile", {
        profile_photo_s3_key: data.s3_key,
      });

      return data.s3_key;
    },
    retry: false,
  });
}
```

**Step 7e** — Modify `ProfileSettingsPage.tsx` to add avatar upload control:

Read the file completely first. Add the avatar section at the top of the profile form:

```tsx
// Add to ProfileSettingsPage.tsx state:
const [cropFile, setCropFile] = useState<File | null>(null);
const avatarUpload = useAvatarUpload();

// Add avatar upload control block (before existing form fields):
<div className="flex items-start gap-4 mb-6">
  {/* 64px avatar preview */}
  <div className="w-16 h-16 rounded-full overflow-hidden ring-2 ring-neutral-200 shrink-0 bg-brand-600 flex items-center justify-center">
    {user?.profile_photo_url ? (
      <img src={user.profile_photo_url} alt="Profile" className="w-full h-full object-cover" />
    ) : (
      <span className="text-lg font-semibold text-white">{initials}</span>
    )}
  </div>

  <div className="flex flex-col gap-1">
    <div className="flex gap-2">
      <label className="border border-neutral-300 text-neutral-700 rounded-md px-3 py-1.5 text-sm hover:bg-neutral-50 cursor-pointer">
        Change
        <input
          type="file"
          accept="image/jpeg,image/png"
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file && file.size <= 2 * 1024 * 1024) {
              setCropFile(file);
            }
          }}
        />
      </label>
      {user?.profile_photo_url && (
        <button type="button" className="text-sm text-fault-600 hover:text-fault-700 hover:underline">
          Remove
        </button>
      )}
    </div>
    <p className="text-xs text-neutral-500">JPG or PNG, max 2MB</p>
    {avatarUpload.isError && (
      <p className="text-xs text-fault-600">Upload failed. Please try again.</p>
    )}
  </div>
</div>

{/* Crop modal */}
{cropFile && (
  <AvatarCropModal
    imageFile={cropFile}
    onSave={(blob) => {
      setCropFile(null);
      avatarUpload.mutate(blob);
    }}
    onCancel={() => setCropFile(null)}
  />
)}
```

---

## Test Implementation

### Unit tests

**File**: `apps/web/src/features/settings/components/__tests__/SettingsIndexPage.test.tsx`

```typescript
import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { SettingsIndexPage } from "../SettingsIndexPage";

vi.mock("next/navigation", () => ({ usePathname: () => "/settings" }));
vi.mock("next/link", () => ({ default: ({ href, children, ...rest }: any) => <a href={href} {...rest}>{children}</a> }));

// Wrap with AuthContext.Provider for RBAC tests
// (use the makeAuthValue helper pattern from the inclusions file)

describe("SettingsIndexPage", () => {
  it("renders Personal section for all roles", () => {
    // render with owner role; assert "Profile & Account" and "Security" visible
  });

  it("renders Workspace section for owner role", () => {
    // render with owner role; assert "Team", "Operations", "Notifications" visible
  });

  it("hides Workspace section for tech role", () => {
    // render with tech role; assert "Team" not in document
  });

  it("links Notifications card to tenant-defaults for workspace section", () => {
    // render with owner role; find Notifications link href
    // expect href to be /settings/notifications/tenant-defaults
  });
});
```

**File**: `apps/web/src/components/__tests__/AppSidebar.test.tsx` — update existing tests to account for pill toggle + w-fit class changes.

**File**: `apps/web/src/components/__tests__/ProfileDropdown.test.tsx` — update existing tests to match new 3-item DROPDOWN_ITEMS.

### Integration tests

**File**: `apps/web/src/__tests__/batch_fe_ui_nav_s1/settings_index.integration.test.tsx`

Minimum coverage:
1. `/settings` route does not 404
2. Owner role sees Personal + Workspace sections
3. Tech role sees only Personal section (Workspace hidden)
4. Notifications card links to `/settings/notifications/tenant-defaults`

**File**: `apps/web/src/__tests__/batch_fe_ui_nav_s1/tenant_notification_defaults.integration.test.tsx`

Minimum coverage:
1. `/settings/notifications/tenant-defaults` renders without 404
2. Matrix visible for owner role
3. `<RoleGate>` hides content for tech role
4. Reset button triggers DELETE mutation

---

## Final Verification

> ❌ **BANNED COMMAND**: `npx vitest run` — NEVER use this.

### Phase 1 — Targeted tests (during development)

```bash
cd <repo>/frontend

pnpm --filter @pilot/ui test 2>&1 | tail -6          # after Step 3 (PilotUser type)
pnpm --filter web test 2>&1 | tail -6                # after each step
```

Fix any failure before moving to the next step.

### Phase 2 — Full verification (once at the very end)

```bash
cd <repo>/frontend && echo "=== UI - Type Check ===" && pnpm --filter @pilot/ui check-types && echo "=== Web - Type Check ===" && pnpm --filter web check-types && echo "=== Mobile - Type Check ===" && pnpm --filter mobile build && echo "=== UI - Lint ===" && pnpm --filter @pilot/ui lint && echo "=== Web - Lint ===" && pnpm --filter web lint && echo "=== Mobile - Lint ===" && pnpm --filter mobile lint && echo "=== TYPE+LINT PASS ===" && echo "=== UI - Tests ===" && pnpm --filter @pilot/ui test 2>&1 | tail -6 && echo "=== Web - Tests ===" && pnpm --filter web test 2>&1 | tail -6 && echo "=== Mobile - Tests ===" && pnpm --filter mobile test 2>&1 | tail -8 && echo "=== MVP FINAL VERIFICATION COMPLETE ==="
```

---

## Definition of Done — FE-UI-NAV-S1

Update `dev-docs/analysis/pilot-launch-plan.md` §2 when each item is done:

- [ ] Pre-modification regression baseline captured — zero pre-existing failures or confirmed with Tom
- [ ] `pnpm sync-api-types` run — no new type errors
- [ ] Design doc and UI spec fully read before writing any code
- [ ] All mandatory source files read before modifying
- [ ] MSW handlers created in `settingsNavHandlers.ts` and registered in `mocks/handlers/index.ts`
- [ ] **STEP 1**: `AppSidebar.tsx` — `w-fit min-w/max-w` width; pill `«»` toggle at top-right; bottom toggle removed
- [ ] **STEP 2**: `ProfileDropdown.tsx` — 3 items (My Profile, Security, Notifications); hover ring on avatar; conditional photo `<img>`
- [ ] **STEP 3**: `PilotUser` type — `profile_photo_url?: string | null` added
- [ ] **STEP 4**: `SettingsIndexPage.tsx` created; `/settings/page.tsx` stub replaced with thin server component
- [ ] **STEP 5**: `<SettingsShell>` removed from all settings sub-pages; zero remaining imports confirmed
- [ ] **STEP 6**: `TenantNotificationDefaultsPage.tsx` + `useTeamNotificationDefaults.ts` + `/settings/notifications/tenant-defaults/page.tsx` created
- [ ] **STEP 7**: `AvatarCropModal.tsx` + `useAvatarUpload.ts` created; `ProfileSettingsPage.tsx` extended with 64px avatar upload control
- [ ] Owner role sees all 3 Settings Index sections; tech role sees only Personal section
- [ ] Notifications card in Workspace section links to `/settings/notifications/tenant-defaults`
- [ ] ProfileDropdown lists 3 items (My Profile, Security, Notifications); Subscription + Payment Method removed
- [ ] AppSidebar pill toggle works; `w-fit` applied; bottom Collapse button removed
- [ ] New `PermissionKey` entries (if any) added to `permissions.ts` AND `ROLE_PERMISSION_MAP`
- [ ] All new MSW handler files registered in `mocks/handlers/index.ts`
- [ ] Unit tests pass — `SettingsIndexPage` (role visibility), `AppSidebar` (pill toggle), `ProfileDropdown` (3 items)
- [ ] Integration tests pass in `__tests__/batch_fe_ui_nav_s1/`
- [ ] Zero TypeScript errors (`check-types` passes for all packages)
- [ ] Zero ESLint `no-hardcoded-design-values` warnings
- [ ] No regressions in pre-existing test suite
- [ ] **Phase 2 FULL verification command passes** (`=== MVP FINAL VERIFICATION COMPLETE ===`):
  ```bash
  cd <repo>/frontend && echo "=== UI - Type Check ===" && pnpm --filter @pilot/ui check-types && echo "=== Web - Type Check ===" && pnpm --filter web check-types && echo "=== Mobile - Type Check ===" && pnpm --filter mobile build && echo "=== UI - Lint ===" && pnpm --filter @pilot/ui lint && echo "=== Web - Lint ===" && pnpm --filter web lint && echo "=== Mobile - Lint ===" && pnpm --filter mobile lint && echo "=== TYPE+LINT PASS ===" && echo "=== UI - Tests ===" && pnpm --filter @pilot/ui test 2>&1 | tail -6 && echo "=== Web - Tests ===" && pnpm --filter web test 2>&1 | tail -6 && echo "=== Mobile - Tests ===" && pnpm --filter mobile test 2>&1 | tail -8 && echo "=== MVP FINAL VERIFICATION COMPLETE ==="
  ```
- [ ] Companion backend tasks documented — `BE-UI-NAV-S1` endpoints not yet in `openapi_schema_map.md` are all MSW-stubbed
- [ ] Final test count (before → after) documented

---

## Completion Summary

After all Definition of Done items are complete:

1. Add a **Completion Summary** to `dev-docs/analysis/pilot-launch-plan.md` Appendix B.

```markdown
### FE-UI-NAV-S1 — Settings Navigation Redesign: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot React Engineer
**Baseline**: X passed (web) | Y passed (ui)
**Final**: X+N passed (web) | Y+M passed (ui) (+N new tests)

#### What Was Accomplished

- Settings Index Page — 3-section Stripe-style card grid; RBAC-gated Workspace section
- AppSidebar — w-fit width; pill «/» toggle at top-right border; bottom Collapse removed
- ProfileDropdown — trimmed to 3 items (My Profile, Security, Notifications); hover ring; conditional avatar photo
- SettingsShell removed from all settings sub-pages (N files updated)
- Tenant notification defaults page — owner-only; `NotificationPreferenceMatrix` + reset action
- Avatar upload UI — 64px preview, crop modal, presigned S3 flow (MSW stub until BE-UI-NAV-S1)
- PilotUser type extended with `profile_photo_url`

#### Files Changed / Created

| File | Action |
|---|---|
| `apps/web/src/app/(authed)/settings/page.tsx` | Replaced stub with thin server component |
| `apps/web/src/features/settings/components/SettingsIndexPage.tsx` | Created |
| `apps/web/src/components/AppSidebar.tsx` | Updated — w-fit + pill toggle |
| `apps/web/src/components/ProfileDropdown.tsx` | Updated — 3 items, hover ring, avatar photo |
| `apps/web/src/components/AvatarCropModal.tsx` | Created |
| `apps/web/src/features/settings/components/TenantNotificationDefaultsPage.tsx` | Created |
| `apps/web/src/features/notification-preferences/hooks/useTeamNotificationDefaults.ts` | Created |
| `apps/web/src/features/settings/hooks/useAvatarUpload.ts` | Created |
| `apps/web/src/app/(authed)/settings/notifications/tenant-defaults/page.tsx` | Created |
| `packages/ui/src/auth/types.ts` | Updated — `profile_photo_url` on PilotUser |
| N settings sub-page files | Updated — SettingsShell removed |
| `apps/web/src/mocks/handlers/settingsNavHandlers.ts` | Created |
| `apps/web/src/mocks/handlers/index.ts` | Updated — registered settingsNavHandlers |

#### Tests Added

| Test File | Type | Tests | All Pass |
|---|---|---|---|
| `features/settings/components/__tests__/SettingsIndexPage.test.tsx` | Unit | N | ✅ |
| `__tests__/batch_fe_ui_nav_s1/settings_index.integration.test.tsx` | Integration | 4 | ✅ |
| `__tests__/batch_fe_ui_nav_s1/tenant_notification_defaults.integration.test.tsx` | Integration | 4 | ✅ |
```
