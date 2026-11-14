# Implementation Prompt: UI-FIX-2E — Navigation Redesign

**Mode**: Pilot React Engineer  
**Batch**: UI-FIX-2E  
**Source decisions**: `dev-docs/architecture-design/batch-designs/ui-fix-2-decisions.md § FIX-019`  
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-ui-fix-2e-design.md`  
**UI Design spec**: `dev-docs/architecture-design/batch-designs/batch-ui-fix-2e-ui-design-spec.md` ← **Primary implementation reference — read every section**  
**Estimated session**: 6–8 hours  
**Platform**: Web only (`apps/web`)  
**Backend companion**: None — pure frontend, no API changes

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-react-engineer/react-engineer-rules.md`** — in full
- **`dev-docs/architecture-design/batch-designs/batch-ui-fix-2e-ui-design-spec.md`** — **every section A through 15**. This is the pixel-level authoritative spec. Every dimension, token, icon name, state, and transition is specified there. Do not invent anything — implement exactly what the spec says.

**Critical rules for this batch:**

- **Rule 1**: Before using any Heroicons, verify `@heroicons/react` is in `frontend/apps/web/package.json`. If not present, add it and run `pnpm install` first. The spec mandates Heroicons 2.0 outline variant for all nav icons — no emoji.
- **Rule 2**: All API calls use `apiClient`. `fetch()` is permanently banned. (This batch has no API calls — but the rule stands for any future modifications.)
- **Rule 7**: Check `packages/ui/src/index.ts` before creating any new component — `NotificationBell`, `RoleGate`, `useAuth` are all there.
- **Rule 8**: No new npm dependencies beyond `@heroicons/react` (if not already present). Check `package.json` first.
- **Rule 9**: Route files in `apps/web/src/app/(authed)/` MUST be thin server components — the only route file this batch touches is `dashboard/page.tsx` to remove the Sign Out button. That file is a client component — check before assuming.
- **Rule 10**: If ANY test fails during your work — including pre-existing failures — fix it before declaring done.

---

## Design Decisions (Do Not Re-Litigate)

From the UI design spec — these decisions are final:

| Decision | Outcome | Rationale |
|---|---|---|
| Sidebar width expanded | 256px (`w-64`) | Design spec §2 |
| Sidebar width collapsed | 64px (`w-16`) | Design spec §3 |
| Transition mechanism | `transition-[width] duration-200 ease-in-out` via inline `style={{ width }}` | Design spec §10 |
| Icon set | Heroicons 2.0, outline variant exclusively for nav | Design spec §2 |
| localStorage key | `pilot.sidebar.collapsed` | Design spec §11 |
| Logo switching | `logo-primary.jpg` (expanded) / `logo-icon.jpg` (collapsed) | Design spec §4 |
| Active item left border | `border-l-2 border-brand-600` | Design spec §2 |
| Toggle button position | Bottom of sidebar, `mt-auto` | Design spec §2 |
| Profile dropdown dismiss | Outside-click (`mousedown` on `document`) + Escape key | Design spec §7 |
| Sign Out removal | Remove from `dashboard/page.tsx` entirely — it lives in Profile dropdown now | Design spec §8 |

Do NOT change these decisions without asking Tom.

---

## Pre-Work: Establish Regression Baseline

Before touching any file:

```bash
cd <repo>/frontend
pnpm --filter web test 2>&1 | tail -5
pnpm --filter @pilot/ui test 2>&1 | tail -5
```

Record the exact counts. Fix any pre-existing failures before starting.

---

## Pre-Work: Sync API Types

```bash
cd <repo>/frontend
pnpm sync-api-types
```

This batch has no new API endpoints, but run it to ensure types are current.

---

## Pre-Work: Verify Heroicons

```bash
grep "heroicons" <repo>/frontend/apps/web/package.json
```

If `@heroicons/react` is NOT present:
```bash
cd <repo>/frontend
pnpm --filter web add @heroicons/react
```

Verify it installed:
```bash
grep "heroicons" <repo>/frontend/apps/web/package.json
```

---

## Pre-Work: Read These Source Files

Read each of these with `read_file` before writing any code:

```
frontend/apps/web/src/components/AppSidebar.tsx
  ← Understand current nav items, emoji icons, width, wordmark block — this file gets fully rewritten

frontend/apps/web/src/app/(authed)/layout.tsx
  ← Understand current header structure before modifying

frontend/apps/web/src/app/(authed)/dashboard/page.tsx
  ← Find the Sign Out button (approx line 65) — remove it completely

frontend/apps/web/src/features/settings/components/SettingsSidebar.tsx
  ← Find My Account group, Billing item, Communications label, Security & MFA label — all change

frontend/packages/ui/src/index.ts
  ← Confirm imports for useAuth, NotificationBell, RoleGate before using

frontend/apps/web/src/__tests__/batch_beta_v1_b6/sidebar-rbac.integration.test.tsx
  ← This test imports AppSidebar and asserts on nav items — must update for new nav

frontend/apps/web/src/mocks/handlers/index.ts
  ← Understand handler barrel before any new handlers (none needed here — but confirm)
```

Also run:
```bash
# Confirm useAuth hook location
grep -rn "export.*useAuth" frontend/packages/ui/src/ --include="*.ts" --include="*.tsx" | head -5

# Find the Sign Out button in dashboard
grep -n "logout\|Sign Out\|signOut" frontend/apps/web/src/app/(authed)/dashboard/page.tsx

# Find current SettingsSidebar items
grep -n "My Account\|Billing\|Communications\|Security" frontend/apps/web/src/features/settings/components/SettingsSidebar.tsx

# Check existing sidebar RBAC test
cat frontend/apps/web/src/__tests__/batch_beta_v1_b6/sidebar-rbac.integration.test.tsx
```

---

## Context: What This Batch Does

Complete redesign of the authenticated shell navigation. All changes are purely frontend — no backend, no API calls, no new routes (only modifying existing components and creating 3 new ones).

| Surface | Before | After |
|---|---|---|
| Left sidebar | Fixed 224px, emoji icons, "Pilot for Trades" wordmark, 13 items | Collapsible 256px/64px, Heroicons SVGs, no wordmark, 9 items |
| Top header | Right-justified, `NotificationBell` only | Logo left + Bell + Settings gear + Profile avatar right |
| Profile access | Sign Out button on Dashboard page | Profile dropdown in header |
| Settings access | Left-nav "Settings" item | Settings gear icon in header |
| Settings sidebar | My Account at top, Billing item, wrong labels | Reordered, My Account removed, Billing removed, renamed items |

---

## STEP 1 — Copy Brand Assets

Before writing any code, copy the logo assets from the marketing app to the web app:

```bash
cp <repo>/frontend/apps/marketing/public/brand/logo-primary.jpg \
   <repo>/frontend/apps/web/public/brand/logo-primary.jpg

cp <repo>/frontend/apps/marketing/public/brand/logo-primary.svg \
   <repo>/frontend/apps/web/public/brand/logo-primary.svg

cp <repo>/frontend/apps/marketing/public/brand/logo-icon.jpg \
   <repo>/frontend/apps/web/public/brand/logo-icon.jpg

cp <repo>/frontend/apps/marketing/public/brand/logo-icon.svg \
   <repo>/frontend/apps/web/public/brand/logo-icon.svg
```

Create the `public/brand/` directory first if it doesn't exist:
```bash
mkdir -p <repo>/frontend/apps/web/public/brand
```

---

## STEP 2 — Create `useSidebarState` Hook

**File**: `apps/web/src/hooks/useSidebarState.ts` (new file)

```typescript
/**
 * useSidebarState — persists sidebar collapsed/expanded state to localStorage
 *
 * localStorage key: "pilot.sidebar.collapsed"
 * Default: false (expanded)
 * Both AppSidebar and AuthedLayout consume this hook to share state.
 */
"use client";

import { useState, useCallback } from "react";

interface SidebarState {
  isSidebarCollapsed: boolean;
  toggleSidebar: () => void;
}

export function useSidebarState(): SidebarState {
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState<boolean>(() => {
    if (typeof window === "undefined") return false;
    try {
      return JSON.parse(
        localStorage.getItem("pilot.sidebar.collapsed") ?? "false"
      );
    } catch {
      return false;
    }
  });

  const toggleSidebar = useCallback(() => {
    setIsSidebarCollapsed((prev) => {
      const next = !prev;
      try {
        localStorage.setItem("pilot.sidebar.collapsed", String(next));
      } catch {
        // localStorage unavailable — continue without persistence
      }
      return next;
    });
  }, []);

  return { isSidebarCollapsed, toggleSidebar };
}
```

> **Adjust to match what you actually find** when reading the existing hooks pattern in `apps/web/src/hooks/`. The above is a starting point.

**Intermediate test run:**
```bash
pnpm --filter web test -- apps/web/src/hooks/ 2>&1 | tail -8
```

---

## STEP 3 — Rewrite `AppSidebar.tsx`

**File**: `apps/web/src/components/AppSidebar.tsx`

Read the full existing file first. Then rewrite it per design spec §2, §3, §12.

**Key implementation points:**

**Nav items array** (9 items, new order, Heroicons):
```typescript
import {
  Squares2X2Icon,
  CalendarDaysIcon,
  UsersIcon,
  DocumentTextIcon,
  WrenchScrewdriverIcon,
  BanknotesIcon,
  ChatBubbleLeftRightIcon,
  CubeIcon,
  ChartBarIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
} from "@heroicons/react/24/outline";

const NAV_ITEMS = [
  { label: "Dashboard", href: "/dashboard", icon: Squares2X2Icon },
  { label: "Schedule",  href: "/schedule",  icon: CalendarDaysIcon },
  { label: "Customers", href: "/customers", icon: UsersIcon },
  { label: "Quotes",    href: "/quotes",    icon: DocumentTextIcon },
  { label: "Jobs",      href: "/jobs",      icon: WrenchScrewdriverIcon },
  { label: "Invoices",  href: "/invoices",  icon: BanknotesIcon },
  { label: "Comms",     href: "/comms",     icon: ChatBubbleLeftRightIcon },
  { label: "Catalog",   href: "/catalog",   icon: CubeIcon,       permission: "catalog.view" },
  { label: "Reports",   href: "/reports",   icon: ChartBarIcon,   permission: "reports.view" },
] as const;
```

**Active state** (design spec §2 — left border accent):
```typescript
const activeClasses = "bg-brand-50 text-brand-700 font-medium border-l-2 border-brand-600 pl-2.5";
const inactiveClasses = "text-neutral-700 hover:bg-neutral-100 hover:text-neutral-900 pl-3";
```

**Sidebar width** (transitions):
```tsx
<nav
  className="flex flex-col h-full bg-white border-r border-neutral-200 shrink-0 transition-[width] duration-200 ease-in-out overflow-hidden"
  style={{ width: isSidebarCollapsed ? "64px" : "256px" }}
  aria-label="Main navigation"
>
```

**No wordmark block** — remove the `"Pilot for Trades"` header div entirely. Nav list starts immediately after `<nav>`.

**Toggle button** (bottom, design spec §2 toggle button):
- Expanded: `ChevronLeftIcon`, label "Collapse", `justify-end`
- Collapsed: `ChevronRightIcon`, no label, `justify-center`, `title="Expand navigation"`

**Labels hidden when collapsed**:
```tsx
{!isSidebarCollapsed && <span>{item.label}</span>}
```

**Tooltip when collapsed**:
```tsx
<Link
  ...
  title={isSidebarCollapsed ? item.label : undefined}
  className={...}
>
```

**Intermediate test run:**
```bash
pnpm --filter web test -- apps/web/src/__tests__/batch_beta_v1_b6/sidebar-rbac.integration.test.tsx 2>&1 | tail -10
```

The sidebar RBAC test will likely fail because it asserts on old nav items. **Update the test** to assert on the new nav order (Dashboard, Schedule, Customers, Quotes, Jobs, Invoices, Comms, Catalog, Reports) and the removed items (Operations, Sync, Notifications, Settings must NOT be rendered).

---

## STEP 4 — Create `SettingsGearIcon.tsx`

**File**: `apps/web/src/components/SettingsGearIcon.tsx` (new file)

Per design spec §5:

```typescript
import { Cog6ToothIcon } from "@heroicons/react/24/outline";
import { usePathname, useRouter } from "next/navigation";

export function SettingsGearIcon() {
  const pathname = usePathname();
  const router = useRouter();
  const isActive = pathname.startsWith("/settings");

  return (
    <button
      type="button"
      onClick={() => router.push("/settings")}
      title="Settings"
      aria-label="Settings"
      aria-current={isActive ? "page" : undefined}
      className={`flex items-center justify-center w-9 h-9 rounded-md transition-colors duration-150 ${
        isActive
          ? "bg-brand-50 text-brand-600 hover:bg-brand-100 hover:text-brand-700"
          : "text-neutral-500 hover:bg-neutral-100 hover:text-neutral-700"
      }`}
    >
      <Cog6ToothIcon className="w-5 h-5" aria-hidden="true" />
    </button>
  );
}
```

> Adjust imports and className details to match the actual implementation patterns you find.

---

## STEP 5 — Create `ProfileDropdown.tsx`

**File**: `apps/web/src/components/ProfileDropdown.tsx` (new file)

Per design spec §6 and §7. Read `@pilot/ui` auth exports to find the correct `useAuth` import and `user` shape before coding.

**Key implementation points:**

1. **Initials computation** (design spec §6):
```typescript
function getInitials(user: { first_name?: string | null; last_name?: string | null; email?: string }): string {
  if (user.first_name && user.last_name)
    return (user.first_name[0] + user.last_name[0]).toUpperCase();
  if (user.first_name)
    return user.first_name.slice(0, 2).toUpperCase();
  return (user.email?.[0] ?? "?").toUpperCase();
}
```

2. **Avatar circle**: `w-8 h-8 rounded-full flex items-center justify-center text-xs font-semibold text-white bg-brand-600` — override `bg-brand-600` with inline `style={{ backgroundColor: user.display_color }}` when `display_color` is set.

3. **Outside-click dismiss**: Use `useEffect` to add a `mousedown` listener on `document` when open; check if click target is outside the panel ref; close if so. Remove listener on cleanup.

4. **Escape key**: `useEffect` adds `keydown` listener; check `e.key === "Escape"` → close.

5. **Dropdown panel** (design spec §7):
   - `min-w-[200px]`
   - `absolute top-full right-0 mt-1`
   - `bg-white border border-neutral-200 rounded-lg shadow-lg z-40 py-1 overflow-hidden`

6. **Sign Out**: Find the current logout hook by reading `dashboard/page.tsx` before implementing. Likely `useLogout().logout()` or `useAuth().logout()`. Use the same hook.

7. **Dropdown items** (in order):
   - `Account` → `/settings/my-account/profile`
   - `Subscription` → `/settings/billing`
   - `Payment Method` → `/settings/billing/payment-method`
   - `Security` → `/settings/my-account/security`
   - Divider (`border-t border-neutral-100 my-1`)
   - `Sign Out` → `logout()` call, `text-fault-600 font-medium hover:bg-fault-50 hover:text-fault-700`

**Intermediate test run:**
```bash
pnpm --filter web test -- apps/web/src/components/ 2>&1 | tail -8
```

---

## STEP 6 — Update `layout.tsx`

**File**: `apps/web/src/app/(authed)/layout.tsx`

Read the full file first. Changes per design spec §4:

1. **Import `useSidebarState`** — consume `isSidebarCollapsed`
2. **Import `AppSidebar`**, `ProfileDropdown`, `SettingsGearIcon`, `NotificationBell`
3. **Import `Image`** from `next/image`
4. **Import `Link`** from `next/link`
5. **Header change** — `justify-end` → `justify-between`:

```tsx
<header className="h-12 bg-white border-b border-neutral-200 flex items-center justify-between px-4 shrink-0 z-30">
  {/* Left: Logo — switches between full wordmark and icon mark */}
  <Link href="/dashboard" className="flex-shrink-0 hover:opacity-80 transition-opacity duration-150">
    <div
      className="overflow-hidden transition-[width] duration-200 ease-in-out"
      style={{ width: isSidebarCollapsed ? "32px" : "120px" }}
    >
      {isSidebarCollapsed ? (
        <Image
          src="/brand/logo-icon.jpg"
          alt="Pilot for Trades"
          width={32}
          height={32}
          priority
          className="block"
        />
      ) : (
        <Image
          src="/brand/logo-primary.jpg"
          alt="Pilot for Trades"
          width={120}
          height={32}
          priority
          className="block"
        />
      )}
    </div>
  </Link>

  {/* Right: icon group */}
  <div className="flex items-center gap-2">
    <NotificationBell />
    <SettingsGearIcon />
    <ProfileDropdown />
  </div>
</header>
```

6. **Pass `isSidebarCollapsed` to `AppSidebar`** — or have `AppSidebar` consume `useSidebarState()` directly (simpler, both read the same hook). If `AppSidebar` reads the hook itself, no prop needed on the layout.

> Adjust to match actual file structure. Read the full file before modifying.

---

## STEP 7 — Remove Sign Out from `dashboard/page.tsx`

**File**: `apps/web/src/app/(authed)/dashboard/page.tsx`

Read the full file. Find the Sign Out button (currently around line 65). Remove it entirely — the button element, its `onClick` handler, and the `useLogout` import if it is no longer used anywhere else in the file.

Do NOT remove any other content from the dashboard page.

---

## STEP 8 — Update `SettingsSidebar.tsx`

**File**: `apps/web/src/features/settings/components/SettingsSidebar.tsx`

Read the full file. Changes per design spec §9:

1. **Remove** the entire `My Account` group entry (all sub-items including Profile and Security)
2. **Remove** the `Billing` standalone entry
3. **Reorder** remaining items per the spec table
4. **Rename** `"Communications"` → `"Branding"`
5. **Rename** `"Security & MFA"` → `"Security"`
6. **Update** Notifications to link directly to `/settings/notifications/preferences` with no sub-items (from UI-FIX-2C)

New `SIDEBAR_ITEMS` order:
1. Team → `/settings/team`
2. Operations → `/settings/operations`
3. Notifications → `/settings/notifications/preferences` (no sub-items)
4. Sync & Storage → `/settings/sync-storage`
5. Integrations → `/settings/integrations`
6. Branding → `/settings/communications` (renamed)
7. Voice & AI → `/settings/voice-ai`
8. Security → `/settings/security` (renamed)
9. Data & Privacy → `/settings/data-privacy`

Keep all existing sub-items for groups that retain them. Only labels and order change — sub-item `href` values are unchanged.

**Intermediate test run:**
```bash
pnpm --filter web test -- apps/web/src/features/settings/components/__tests__/ 2>&1 | tail -8
```

Update the `SettingsSidebar.test.tsx` to assert on the new item order. The test must NOT assert that "My Account", "Billing", "Communications", or "Security & MFA" appear in the sidebar.

---

## Test Requirements

### Unit tests to create/update:

**`AppSidebar` tests** (update `sidebar-rbac.integration.test.tsx` + create new unit tests):
- Collapsed state: only icons visible, no label text
- Expanded state: icons + labels visible
- `localStorage` key `pilot.sidebar.collapsed` persists state across renders
- New nav order: Dashboard, Schedule, Customers, Quotes, Jobs, Invoices, Comms, Catalog, Reports
- Removed items: Operations, Sync, Notifications, Settings do NOT render
- Reports hidden for `tech` role (RBAC)
- Catalog visible for `tech` role (RBAC)
- Toggle button: ChevronLeftIcon when expanded, ChevronRightIcon when collapsed

**`ProfileDropdown` tests** (create `ProfileDropdown.test.tsx`):
- Renders avatar circle with correct initials (first+last, first-only, email fallback)
- `display_color` applied as inline style
- Dropdown opens on avatar click
- Dropdown closes on Escape key
- Dropdown closes on outside-click
- Each nav item has correct `href`
- Sign Out calls the logout function

**`SettingsGearIcon` tests** (create `SettingsGearIcon.test.tsx`):
- Default state: `text-neutral-500` color
- Active state when `pathname.startsWith("/settings")`: `text-brand-600` color
- Click navigates to `/settings`

**`SettingsSidebar` test updates**:
- My Account group not present
- Billing item not present
- "Branding" label present (not "Communications")
- "Security" label present (not "Security & MFA")
- New order correct

**`DashboardPage` test update**:
- Sign Out button not present

**Integration test** (create `__tests__/batch_ui_fix_2e/nav_redesign.integration.test.tsx`):
- AuthedLayout renders logo linking to /dashboard
- AuthedLayout header contains NotificationBell, SettingsGearIcon, ProfileDropdown
- DashboardPage does not render Sign Out button

---

## Final Verification

### Phase 1 — Targeted (run after each major step)

```bash
cd <repo>/frontend
pnpm --filter web test -- apps/web/src/__tests__/batch_ui_fix_2e/ 2>&1 | tail -8
pnpm --filter web test -- apps/web/src/components/ 2>&1 | tail -8
pnpm --filter web test -- apps/web/src/features/settings/ 2>&1 | tail -8
pnpm --filter web test -- apps/web/src/__tests__/batch_beta_v1_b6/ 2>&1 | tail -8
```

### Phase 2 — Full (run once at the very end)

```bash
cd <repo>/frontend && echo "=== UI - Type Check ===" && pnpm --filter @pilot/ui check-types && echo "=== Web - Type Check ===" && pnpm --filter web check-types && echo "=== Mobile - Type Check ===" && pnpm --filter mobile build && echo "=== UI - Lint ===" && pnpm --filter @pilot/ui lint && echo "=== Web - Lint ===" && pnpm --filter web lint && echo "=== Mobile - Lint ===" && pnpm --filter mobile lint && echo "=== TYPE+LINT PASS ===" && echo "=== UI - Tests ===" && pnpm --filter @pilot/ui test 2>&1 | tail -6 && echo "=== Web - Tests ===" && pnpm --filter web test 2>&1 | tail -6 && echo "=== Mobile - Tests ===" && pnpm --filter mobile test 2>&1 | tail -8 && echo "=== MVP FINAL VERIFICATION COMPLETE ==="
```

---

## Definition of Done — UI-FIX-2E

- [ ] Pre-modification regression baseline captured (zero pre-existing failures, or confirmed with Tom)
- [ ] `pnpm sync-api-types` run — no new type errors
- [ ] All mandatory source files read before modifying
- [ ] `@heroicons/react` confirmed in `apps/web/package.json` (installed if missing)
- [ ] **STEP 1**: Brand assets copied to `apps/web/public/brand/` (4 files)
- [ ] **STEP 2**: `useSidebarState.ts` hook created — `localStorage` read/write, correct key `pilot.sidebar.collapsed`
- [ ] **STEP 3**: `AppSidebar.tsx` rewritten — 9 Heroicons items, no emoji, no wordmark, collapsible, active left-border, toggle button
- [ ] **STEP 4**: `SettingsGearIcon.tsx` created — `Cog6ToothIcon`, active state, tooltip, navigates to /settings
- [ ] **STEP 5**: `ProfileDropdown.tsx` created — avatar initials, display_color, dropdown with 5 items + divider, Sign Out in fault-600, outside-click + Escape dismiss
- [ ] **STEP 6**: `layout.tsx` updated — logo left links to /dashboard, right icons in order (Bell + Gear + Profile)
- [ ] **STEP 7**: `dashboard/page.tsx` updated — Sign Out button removed
- [ ] **STEP 8**: `SettingsSidebar.tsx` updated — My Account removed, Billing removed, reordered, Branding label, Security label
- [ ] `sidebar-rbac.integration.test.tsx` updated for new nav items
- [ ] `SettingsSidebar.test.tsx` updated for new order and labels
- [ ] All new component tests created and passing
- [ ] New integration test in `__tests__/batch_ui_fix_2e/` passing
- [ ] Zero TypeScript errors (`pnpm --filter web check-types` passes)
- [ ] Zero ESLint `no-hardcoded-design-values` warnings
- [ ] No regressions in pre-existing test suite
- [ ] **Phase 2 FULL verification command passes** (`=== MVP FINAL VERIFICATION COMPLETE ===`)
- [ ] Final test count (before → after) documented
- [ ] Completion Summary added to `ui-fix-2-decisions.md` batch overview section for UI-FIX-2E

---

## Completion Summary

After all Definition of Done items are complete, add a Completion Summary to `dev-docs/architecture-design/batch-designs/ui-fix-2-decisions.md` under the UI-FIX-2E batch row:

```markdown
### UI-FIX-2E — Navigation Redesign: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot React Engineer
**Baseline**: X passed (web)
**Final**: X+N passed (+N new tests)

#### What Was Accomplished

- AppSidebar rewritten: 9 Heroicons items, no emoji, collapsible 256px/64px with localStorage persistence, active left-border, toggle button
- useSidebarState hook created (localStorage key: pilot.sidebar.collapsed)
- SettingsGearIcon created: Cog6ToothIcon, active state when /settings
- ProfileDropdown created: initials avatar, 5 menu items, Sign Out in fault-600, outside-click + Escape dismiss
- layout.tsx updated: logo left (links to /dashboard, switches primary/icon on collapse), Bell + Gear + Profile right
- dashboard/page.tsx: Sign Out button removed
- SettingsSidebar: My Account removed, Billing removed, reordered, "Branding" and "Security" labels

#### Files Changed / Created

| File | Action |
|---|---|
| `apps/web/public/brand/logo-primary.jpg` / `.svg` | Copied from marketing |
| `apps/web/public/brand/logo-icon.jpg` / `.svg` | Copied from marketing |
| `apps/web/src/hooks/useSidebarState.ts` | Created |
| `apps/web/src/components/AppSidebar.tsx` | Rewritten |
| `apps/web/src/components/SettingsGearIcon.tsx` | Created |
| `apps/web/src/components/ProfileDropdown.tsx` | Created |
| `apps/web/src/app/(authed)/layout.tsx` | Updated |
| `apps/web/src/app/(authed)/dashboard/page.tsx` | Updated — removed Sign Out |
| `apps/web/src/features/settings/components/SettingsSidebar.tsx` | Updated |
| `apps/web/src/__tests__/batch_ui_fix_2e/nav_redesign.integration.test.tsx` | Created |
```
