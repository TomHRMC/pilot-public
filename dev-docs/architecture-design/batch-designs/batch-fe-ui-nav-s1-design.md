# Batch Design: FE-UI-NAV-S1 — Settings Navigation Redesign (Frontend)

**Batch code**: `FE-UI-NAV-S1`  
**Type**: Frontend web (`apps/web`) — no backend changes in this batch  
**Design spec**: `batch-ui-nav-s1-ui-design-spec.md`  
**Backend companion**: `BE-UI-NAV-S1` — must complete first for avatar upload endpoint; frontend stubs with MSW until then  
**Estimated effort**: 4–6 hours  
**Date**: 2026-07-21  

---

## A. Input Read Summary

| Input | What was read | Key finding |
|---|---|---|
| UI design spec | `batch-ui-nav-s1-ui-design-spec.md` §22 (confirmed decisions), §17–§29 | Option 3 (Stripe/Clio index page), pill toggle, w-fit sidebar, 3-item dropdown, tenant defaults separate page |
| `AppSidebar.tsx` | Full file — UI-FIX-2E rewrite | Uses `style={{ width: sidebarWidth }}` with `"16rem"` hardcoded; toggle at bottom; no pill |
| `layout.tsx` | Full file — UI-FIX-2E | `<AppSidebar />` direct child of flex container; no `relative` wrapper needed (pill can be inside sidebar) |
| `SettingsSidebar.tsx` | Full file | `renderItem` guards sub-items with `isExpanded`; pure text, no icons; `w-56` sidebar |
| `SettingsShell.tsx` | Full file | Wraps `<aside>` + `<main>`; renders `<SettingsBreadcrumb />` + children |
| `ProfileDropdown.tsx` | Full file | 4 items: Account, Subscription, Payment Method, Security |
| `SettingsGearIcon.tsx` | Full file | Already calls `router.push("/settings")` — **no change needed** |
| `/settings/page.tsx` | Full file | Stub — renders `<h1>Settings</h1>` only |
| `/settings/my-account/page.tsx` | Full file | Redirects to `/settings/my-account/profile` |
| Settings routes directory | Full tree | `/settings/my-account/profile` route exists (confirmed by redirect) |
| Live DB — `user` table | MCP query | `profile_photo_s3_key TEXT NULL` **already exists** — no migration needed |
| Live DB — `notification_default_policy` | MCP query | `(tenant_id UUID NULL, category_id TEXT, channel TEXT, enabled BOOL)` — already exists; `tenant_id=NULL` = platform default |
| `notification_preference` table | MCP query | `(tenant_id, user_id NULL, category_id, channel, enabled)` — per-user prefs table |
| Launch plan | Current state | Last FE batch: UI-FIX-2F (FE). Next web frontend batch is FE-UI-NAV-S1 |

---

## B. Migration Plan

**No database migrations required for this batch.**

`user.profile_photo_s3_key TEXT NULL` already exists. The backend companion batch `BE-UI-NAV-S1` handles:
- Avatar upload endpoint (`PATCH /api/v1/users/me/avatar`)
- `profile_photo_url` signed URL field added to `GET /api/v1/users/me` response
- Tenant notification defaults endpoints (using existing `notification_default_policy` table)

This frontend batch scaffolds avatar and tenant notifications with **MSW handlers** until the backend is ready.

---

## C. Execution Order

| # | Task | File(s) changed | Notes |
|---|---|---|---|
| 1 | Sync API types | `packages/shared-types` | Run `pnpm sync-api-types` first |
| 2 | AppSidebar — w-fit + pill toggle | `AppSidebar.tsx` | Replace `style={{ width }}` with Tailwind classes; move toggle to top-right pill |
| 3 | ProfileDropdown — 3 items + hover ring | `ProfileDropdown.tsx` | Remove Subscription + Payment Method; add Notifications; add hover ring; conditional photo `<img>` |
| 4 | Settings Index Page | `/settings/page.tsx` (replace stub) + new `SettingsIndexPage.tsx` | 3-section card grid; RBAC-gated sections |
| 5 | SettingsShell removal | All `/settings/*/layout.tsx` and `page.tsx` files using `<SettingsShell>` | Remove shell wrapper; content renders directly |
| 6 | Tenant notification defaults page | `settings/notifications/tenant-defaults/page.tsx` (new) + `useTeamNotificationDefaults.ts` (new) | RBAC-gated; MSW stub until BE ready |
| 7 | Avatar upload UI | `ProfileSettingsPage.tsx` (modify) + `AvatarCropModal.tsx` (new) | Profile page upload control + crop modal |
| 8 | PilotUser type update | `packages/ui/src/auth/types.ts` or equivalent | Add `profile_photo_url?: string \| null` |
| 9 | MSW handlers | `mocks/handlers/settingsNavHandlers.ts` (new) | Stubs for avatar + tenant-defaults endpoints |
| 10 | Tests | Various `__tests__/` files | Unit + integration |

---

## D. New API Endpoints (No New Endpoints This Batch)

This batch consumes endpoints from `BE-UI-NAV-S1`. Until that backend batch completes, MSW handlers stub all calls.

**Endpoints consumed by this batch (backend companion):**

| Hook | Endpoint | Auth | Notes |
|---|---|---|---|
| `useAvatarUpload` | `PATCH /api/v1/users/me/avatar` | JWT | Sends S3 key after crop + upload to presigned URL |
| `useAvatarDelete` | `DELETE /api/v1/users/me/avatar` | JWT | Remove photo |
| `useTeamNotificationDefaults` (read) | `GET /api/v1/tenants/{id}/notification-defaults` | JWT + `settings.tenant.write` | Reads `notification_default_policy` tenant rows |
| `useTeamNotificationDefaults` (write) | `PATCH /api/v1/tenants/{id}/notification-defaults` | JWT + `settings.tenant.write` | Upserts policy rows |
| `useTeamNotificationDefaults` (reset) | `DELETE /api/v1/tenants/{id}/notification-defaults` | JWT + `settings.tenant.write` | Deletes tenant rows; reverts to platform defaults |

Avatar URL is delivered via the existing `GET /api/v1/users/me` response — the backend adds `profile_photo_url?: string | null` to `UserMeResponse`. Frontend reads it from `user.profile_photo_url` via `useAuth()`.

---

## E. Pattern Reuse Decisions

| Pattern | Source (mvp-arch.md §16) | Applied where |
|---|---|---|
| **hide-not-disable RBAC** | `RoleGate` | Settings Index Page — Workspace section hidden for `tech` role; Notifications card in Workspace owner-only |
| **optimistic UI** | §16 optimistic pattern | Avatar upload — show new photo immediately on crop save; revert on error |
| **`<RoleGate>`** | `@pilot/ui/role-gate` | `SettingsIndexPage` Workspace section + tenant defaults page |
| **`<LoadingState>` / `<ErrorState>`** | `@pilot/ui/states` | Tenant defaults matrix + avatar load states |
| **SSE** | Not applicable | Settings pages are not real-time |

---

## F. Shared Module Interfaces

### F.1 — `PilotUser` type extension

File: `packages/ui/src/auth/types.ts` (exact path to be confirmed with `read_file`)

```ts
// Add to PilotUser interface:
profile_photo_url?: string | null;
```

### F.2 — `useTeamNotificationDefaults` hook

File: `apps/web/src/features/notification-preferences/hooks/useTeamNotificationDefaults.ts` (new)

```ts
// Shape of one default policy row (matches notification_default_policy table)
interface TeamNotificationDefault {
  category_id: string;
  channel: string;  // "email" | "sms" | "in_app" | "push"
  enabled: boolean;
}

// GET response shape (array of tenant-scoped policy rows)
interface TeamNotificationDefaultsResponse {
  defaults: TeamNotificationDefault[];
}

// PATCH request shape (array of updates)
interface PatchTeamNotificationDefaultsRequest {
  defaults: TeamNotificationDefault[];
}

export function useTeamNotificationDefaults() {
  // GET: TanStack Query
  // PATCH mutation: save changes
  // DELETE mutation: reset to system defaults
  // All stubs via MSW until BE-UI-NAV-S1 is live
}
```

### F.3 — `useAvatarUpload` hook

File: `apps/web/src/features/settings/hooks/useAvatarUpload.ts` (new)

```ts
// PATCH /api/v1/users/me/avatar
// Body: { s3_key: string } — after client uploads blob to presigned S3 URL
// Response: { profile_photo_url: string }
```

Note: The full avatar upload flow involves a presigned URL endpoint from `BE-UI-NAV-S1`. Until then, the crop modal calls the MSW stub directly with a mock blob.

### F.4 — `SettingsIndexPage` component structure

File: `apps/web/src/features/settings/components/SettingsIndexPage.tsx` (new)

```ts
// Section data structure
interface SettingsCard {
  label: string;
  icon: HeroIcon;
  description: string;
  href: string;
  permission?: PermissionKey;  // hide-not-disable via RoleGate
}

interface SettingsSection {
  title: string;
  permission?: PermissionKey;  // entire section gated
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
```

---

## G. Open Questions Resolved

| Question | Resolution |
|---|---|
| Does `/settings/my-account/profile` route exist? | ✅ Yes — confirmed by `my-account/page.tsx` which redirects to it |
| Does `user.profile_photo_s3_key` need a migration? | ✅ No — column already exists (`TEXT NULL`) in live DB |
| Is there a `notification_default_policy` table already? | ✅ Yes — `(tenant_id UUID NULL, category_id TEXT, channel TEXT, enabled BOOL)`. `tenant_id=NULL` = platform default; `tenant_id=UUID` = tenant override |
| Does `SettingsGearIcon` need changes? | ✅ No — already calls `router.push("/settings")` which is exactly what Option 3 requires |
| Should SettingsSidebar be deleted? | Soft-deprecated — it still renders inside `SettingsShell` on all sub-pages. Deleting it in this batch would require removing `SettingsShell` from every settings sub-page (20+ files). Do both in Task 5. **SettingsSidebar stays but its import count goes to zero after Task 5.** |
| What breadcrumb behavior for individual settings pages? | `SettingsBreadcrumb` is kept; it renders inside each page content area once `SettingsShell` is removed. React Engineer must verify `SettingsBreadcrumb` can stand alone (not nested in `SettingsShell`). |
| Crop library dependency? | Use `react-easy-crop` if available; check `package.json` first. If not installed, implement a simplified crop (scale + center to 256×256 canvas) without a library. Do NOT install without confirming with Tom. |
| Does `tech` role see the Settings Index at all? | Tech role reaches `/settings` but only sees the Personal section (Profile & Account + Security). Workspace section hidden by `<RoleGate permission="settings.tenant.write">`. |

---

## H. Surface Mockup Reference

| Surface | Spec Section | Platform | Key patterns |
|---|---|---|---|
| Settings Index Page (`/settings`) | §17.5, §29.3 | Web only | 3-section icon+description card grid; RBAC-gated Workspace section |
| AppSidebar collapse toggle | §16A | Web only | Pill `«/»` button, top-right border overlap, `rotate-180` animation |
| AppSidebar width | §15 | Web only | `w-fit min-w-[160px] max-w-[200px]` when expanded; `w-16` collapsed |
| ProfileDropdown | §20.3, §29.2 | Web only | 3 items (My Profile, Security, Notifications); hover ring; conditional photo |
| Avatar upload UI | §21.3 | Web only | 64px preview, Change/Remove buttons, crop modal |
| Tenant notification defaults | §29.4 | Web only | Standalone page; owner-only; `NotificationPreferenceMatrix` reuse |

---

## I. Component Manifest

| File | Status | Description |
|---|---|---|
| `apps/web/src/app/(authed)/settings/page.tsx` | **Replace** | Was stub `<h1>Settings</h1>`; now renders `<SettingsIndexPage />` thin server component |
| `apps/web/src/features/settings/components/SettingsIndexPage.tsx` | **New** | 3-section card grid with RBAC; `"use client"` |
| `apps/web/src/components/AppSidebar.tsx` | **Modified** | Width: `w-fit min-w-[160px] max-w-[200px]` expanded; pill «/» toggle replaces bottom Collapse button |
| `apps/web/src/components/ProfileDropdown.tsx` | **Modified** | DROPDOWN_ITEMS → 3 items (My Profile, Security, Notifications); hover ring on avatar; conditional `<img>` for `profile_photo_url` |
| `apps/web/src/features/settings/components/SettingsShell.tsx` | **Deprecated** | Remove from all settings sub-page routes (Task 5); file left in place but unused |
| `apps/web/src/features/settings/components/SettingsSidebar.tsx` | **Deprecated** | Imported only by `SettingsShell`; goes unused after SettingsShell removal |
| All `/settings/*/page.tsx` or layout files using `<SettingsShell>` | **Modified** | Remove `<SettingsShell>` wrapper; add `<SettingsBreadcrumb />` directly if not already present |
| `apps/web/src/app/(authed)/settings/notifications/tenant-defaults/page.tsx` | **New** | Thin server component; renders `TenantNotificationDefaultsPage` |
| `apps/web/src/features/settings/components/TenantNotificationDefaultsPage.tsx` | **New** | Owner-only; `NotificationPreferenceMatrix` + `useTeamNotificationDefaults`; reset action |
| `apps/web/src/features/notification-preferences/hooks/useTeamNotificationDefaults.ts` | **New** | TanStack Query hook; MSW stub until BE-UI-NAV-S1 complete |
| `apps/web/src/features/settings/components/ProfileSettingsPage.tsx` | **Modified** | Add 64px avatar upload control, Change/Remove buttons, 2MB helper |
| `apps/web/src/components/AvatarCropModal.tsx` | **New** | Circular crop modal — 240px preview, Save/Cancel |
| `apps/web/src/features/settings/hooks/useAvatarUpload.ts` | **New** | PATCH `/api/v1/users/me/avatar`; MSW stub |
| `apps/web/src/mocks/handlers/settingsNavHandlers.ts` | **New** | MSW stubs for avatar + tenant-defaults endpoints |
| `apps/web/src/mocks/handlers/index.ts` | **Modified** | Register `settingsNavHandlers` |
| `packages/ui/src/auth/types.ts` (or PilotUser type file) | **Modified** | Add `profile_photo_url?: string \| null` to `PilotUser` |

---

## SettingsShell Removal — File Inventory

These files likely use `<SettingsShell>`. React Engineer must `read_file` each before removing the wrapper:

```
settings/team/page.tsx
settings/operations/page.tsx (+ sub-pages)
settings/notifications/preferences/page.tsx
settings/sync-storage/page.tsx (+ sub-pages)
settings/integrations/page.tsx (+ sub-pages)
settings/communications/page.tsx (+ sub-pages)
settings/voice-ai/page.tsx
settings/security/page.tsx
settings/data-privacy/page.tsx
settings/my-account/*/page.tsx files
```

**Pattern for removal**: Read each file. If it renders `<SettingsShell ...>`, replace with:
```tsx
// Before:
<SettingsShell catalog={catalog}>
  <MyContent />
</SettingsShell>

// After (SettingsBreadcrumb already renders inside SettingsShell; add it back directly):
<div className="flex-1 bg-neutral-50">
  <div className="mx-auto max-w-3xl px-6 py-8 space-y-6">
    <SettingsBreadcrumb />
    <MyContent />
  </div>
</div>
```

This preserves the exact same visual layout without the second sidebar.
