# UI-FIX-2E — Navigation Redesign: Design Spec

**Batch**: UI-FIX-2E  
**Fix**: FIX-019  
**Designer**: Pilot Web UI Designer  
**Status**: ⏳ Awaiting Tom's approval — React Engineer must NOT implement until approved  
**Output path**: `dev-docs/architecture-design/batch-designs/batch-ui-fix-2e-ui-design-spec.md`  
**Architect blueprint**: `batch-ui-fix-2e-design.md`  
**RBAC scope**: All authenticated roles — shell-level, visible to all  
**Platform**: Web (`apps/web`) — desktop-first, minimum viewport 1280px

---

## 1. Overview

This spec covers a full redesign of the authenticated shell navigation: the left sidebar, the top header bar, the profile avatar dropdown, the settings gear icon, and the settings sidebar order. The goal is a modern, clean SaaS navigation pattern matching the quality bar of Linear, Vercel dashboard, and Stripe dashboard.

**What changes:**
- Left sidebar: fixed 224px `w-56` → collapsible 256px/64px with Heroicons (replacing emoji), persisted via `localStorage`, no wordmark block
- Top header: right-justified bell-only → `justify-between` with logo left and bell + gear + avatar right
- Profile dropdown: new component anchored to avatar, replaces the dashboard-page Sign Out button
- Settings gear: new icon component in header with active state
- Settings sidebar: reordered and renamed groups, `My Account` and `Billing` removed

**What does NOT change in this batch:** routes, backend, any page content, `NotificationBell`, `NotificationDrawer`

---

## 2. Sidebar — Expanded State

### Dimensions
| Property | Value |
|---|---|
| Width | 256px (Tailwind: `w-64`) |
| Height | Full viewport height minus header (`flex-1`, `min-h-0`) |
| Background | `bg-white` |
| Right border | `border-r border-neutral-200` |
| Vertical padding (nav list) | `py-2` top and bottom |
| Horizontal padding (nav list container) | `px-2` |

### Nav Item Dimensions
| Property | Value |
|---|---|
| Item height | 36px — achieved via `py-2 px-3` with `text-sm` line-height |
| Icon size | 20px (`w-5 h-5`) |
| Gap between icon and label | 12px (`gap-3`) |
| Border-radius | `rounded-md` (6px) |
| Font size | `text-sm` (14px) |

### Nav Item Order and Icon Mapping

All icons are **Heroicons 2.0, outline variant**. This is the canonical icon set — do not mix solid and outline in the nav list.

| Position | Label | Route | Heroicon (outline) | RBAC Gate |
|---|---|---|---|---|
| 1 | Dashboard | `/dashboard` | `Squares2X2Icon` | None |
| 2 | Schedule | `/schedule` | `CalendarDaysIcon` | None |
| 3 | Customers | `/customers` | `UsersIcon` | None |
| 4 | Quotes | `/quotes` | `DocumentTextIcon` | None |
| 5 | Jobs | `/jobs` | `WrenchScrewdriverIcon` | None |
| 6 | Invoices | `/invoices` | `BanknotesIcon` | None |
| 7 | Comms | `/comms` | `ChatBubbleLeftRightIcon` | None |
| 8 | Catalog | `/catalog` | `CubeIcon` | `catalog.view` |
| 9 | Reports | `/reports` | `ChartBarIcon` | `reports.view` |

**Removed from nav list** (previously present): Operations, Sync, Notifications, Settings — all accessed via the Settings gear icon in the header.

### Active State
| Element | Token |
|---|---|
| Background | `bg-brand-50` |
| Text color | `text-brand-700` |
| Font weight | `font-medium` |
| Left border accent | `border-l-2 border-brand-600` — 2px left border, flush with item left edge |
| Icon color | `text-brand-600` |

**Active detection logic:** `pathname === item.href || pathname.startsWith(item.href + "/")` — same pattern as current `AppSidebar.tsx`.

### Hover State (inactive items only)
| Element | Token |
|---|---|
| Background | `hover:bg-neutral-100` |
| Text color | `hover:text-neutral-900` |
| Icon color | `hover:text-neutral-600` |
| Transition | `transition-colors duration-150` |

### Default (non-active, non-hover)
| Element | Token |
|---|---|
| Text color | `text-neutral-700` |
| Icon color | `text-neutral-500` |

### Top Section
The "Pilot for Trades" wordmark block is **removed entirely**. The nav list starts immediately at the top of the sidebar body, just below the header bar boundary. No `border-b` divider, no padding block above the first nav item — just `py-2` on the `<ul>`.

### Toggle Button — Expanded State
- **Position**: Bottom of sidebar, full-width button zone — `mt-auto` push to bottom; button sits in a `border-t border-neutral-100 py-2 px-2` container
- **Appearance**: 36px height, `w-full`, `flex items-center justify-end px-3`, `rounded-md`, `text-neutral-400`, `hover:bg-neutral-100 hover:text-neutral-600`, `transition-colors duration-150`
- **Icon**: `ChevronLeftIcon` (Heroicons 2.0, outline, `w-4 h-4`) — indicates "click to collapse"
- **Label**: `text-xs text-neutral-400` reading "Collapse" — visible in expanded state to the left of the chevron, `mr-1`
- **No tooltip needed in expanded state** — the "Collapse" label is visible

---

## 3. Sidebar — Collapsed State

### Dimensions
| Property | Value |
|---|---|
| Width | 64px (`w-16`) |
| Background | `bg-white` |
| Right border | `border-r border-neutral-200` |
| Transition from expanded | `transition-[width] duration-200 ease-in-out` (see §9) |

### Nav Item — Collapsed
| Property | Value |
|---|---|
| Layout | `flex items-center justify-center` — icon centered horizontally |
| Item height | 36px — `py-2` maintains height consistency |
| Icon size | 20px (`w-5 h-5`) — same as expanded |
| Label | Hidden (`hidden` or `opacity-0 w-0 overflow-hidden`) |
| Border-radius | `rounded-md` |
| Active background | `bg-brand-50` |
| Active icon color | `text-brand-600` |
| Active left border | `border-l-2 border-brand-600` |
| Hover background | `hover:bg-neutral-100` |

### Tooltip Behavior (collapsed state)
- **Mechanism**: `title` attribute on the `<Link>` element — e.g., `title="Dashboard"`. Do NOT require Radix `Tooltip` (not in `@pilot/ui`, would add a new dependency).
- **Note for React Engineer**: If Radix UI is already in `package.json` for `apps/web`, the React Engineer may optionally upgrade to Radix `<Tooltip>` for better styling. If not present, `title` attribute is sufficient and required for MVP.

### Toggle Button — Collapsed State
- **Position**: Bottom of sidebar, same `mt-auto border-t border-neutral-100 py-2 px-2` container
- **Appearance**: `flex items-center justify-center w-full h-9 rounded-md text-neutral-400 hover:bg-neutral-100 hover:text-neutral-600 transition-colors duration-150`
- **Icon**: `ChevronRightIcon` (Heroicons 2.0, outline, `w-4 h-4`) — indicates "click to expand"
- **Tooltip**: `title="Expand navigation"` on the button element
- **No label text** — sidebar is collapsed, space is at 64px, label is hidden

### Logo Behavior in Header (collapsed state)
When sidebar is collapsed, the header logo switches from full wordmark to icon-only mark. See §4 for exact logo spec.

---

## 4. Top Header Bar

### Dimensions and Base Styles
| Property | Value |
|---|---|
| Height | 48px — keep `h-12`, no change |
| Background | `bg-white` |
| Bottom border | `border-b border-neutral-200` |
| Z-index | `z-30` — keep existing value |
| Padding | `px-4` left and right |
| Layout | `flex items-center justify-between` — change from `justify-end` to `justify-between` |
| Position | `shrink-0` — keep existing |

### Left Side — Logo

**Expanded sidebar state (logo-primary)**:
- Component: Next.js `<Image>` inside a `<Link href="/dashboard">`
- Source: `/brand/logo-primary.jpg` (copied from `frontend/apps/marketing/public/brand/logo-primary.jpg` to `frontend/apps/web/public/brand/logo-primary.jpg` during implementation)
- Width: 120px, Height: 32px
- `alt="Pilot for Trades"`
- `priority` prop on `<Image>` (above-the-fold)
- `className="block"` — prevent inline bottom gap

**Collapsed sidebar state (logo-icon)**:
- Source: `/brand/logo-icon.jpg` (copied from `frontend/apps/marketing/public/brand/logo-icon.jpg`)
- Width: 32px, Height: 32px
- `alt="Pilot for Trades"`
- Same `<Link href="/dashboard">` wrapper

**Logo switching mechanism**: The `AuthedLayout` passes `isSidebarCollapsed` (a boolean from sidebar state) as a prop, or the logo reads a shared context. The simplest approach: expose `isSidebarCollapsed` from a `useSidebarState()` hook (wraps the `localStorage` value) — both `AppSidebar` and `AuthedLayout` consume the same hook.

**Logo transition**: The logo image swap should feel natural — the logo `width` changes in sync with the sidebar width. Apply `transition-all duration-200 ease-in-out` on the `<Image>` wrapper `<div>` so width animates: `w-[120px]` → `w-8`.

**Logo hover state**: No background highlight — it is a plain link. `hover:opacity-80 transition-opacity duration-150`.

### Right Side — Icon Group

**Layout**: `flex items-center gap-2` (8px between each icon)  
**Vertical alignment**: All icons vertically centered in the 48px header (`items-center`)

**Right-side order (left to right)**:
1. `NotificationBell` — existing component, no changes
2. `SettingsGearIcon` — new component (see §5)
3. `ProfileDropdown` — new component (see §6 and §7)

---

## 5. Settings Gear Icon

### Component: `SettingsGearIcon`
**File**: `apps/web/src/components/SettingsGearIcon.tsx` (new file)

### Spec

| Property | Value |
|---|---|
| Icon | `Cog6ToothIcon` — Heroicons 2.0, **outline** variant |
| Icon size | 20px (`w-5 h-5`) |
| Hit target | 36px × 36px (`w-9 h-9`) centered with `flex items-center justify-center` |
| Border-radius on hit target | `rounded-md` |

### States

**Default (pathname does NOT start with `/settings`)**:
| Element | Token |
|---|---|
| Icon color | `text-neutral-500` |
| Background | `transparent` |
| Hover background | `hover:bg-neutral-100` |
| Hover icon | `hover:text-neutral-700` |
| Transition | `transition-colors duration-150` |

**Active (pathname starts with `/settings`)**:
| Element | Token |
|---|---|
| Icon color | `text-brand-600` |
| Background | `bg-brand-50` |
| Hover background | `hover:bg-brand-100` |
| Hover icon | `hover:text-brand-700` |

### Interaction
- **Click action**: `router.push("/settings")` — direct navigation, no dropdown
- **Tooltip**: `title="Settings"` on the button element — appears on hover via browser native tooltip
- **`aria-label`**: `"Settings"` on the `<button>` element
- **`aria-current`**: `"page"` when active

---

## 6. Profile Avatar

### Avatar Button Spec

| Property | Value |
|---|---|
| Shape | Circle — `rounded-full` |
| Diameter | 32px (`w-8 h-8`) |
| Font size for initials | `text-xs font-semibold` |
| Text color | `text-white` |
| Default background | `bg-brand-600` (fallback when no `display_color`) |
| Custom background | User's `display_color` field (inline `style={{ backgroundColor: user.display_color }}`) |
| Border | None |
| Hit target | 36px × 36px wrapper `<button>` with `flex items-center justify-center w-9 h-9 rounded-md` |
| Hover on wrapper | `hover:ring-2 hover:ring-brand-200 hover:ring-offset-1` |
| Transition | `transition-all duration-150` |

### Initials Computation Rule
```
if user.first_name && user.last_name:
  initials = first_name[0].toUpperCase() + last_name[0].toUpperCase()
elif user.first_name:
  initials = first_name.slice(0, 2).toUpperCase()
else:
  initials = email[0].toUpperCase()
```
Display maximum 2 characters.

### Data Source
- Calls `useAuth()` from `@pilot/ui` — returns `user` object with `first_name`, `last_name`, `display_color`
- `display_color` is a CSS color string (e.g., `#3B82F6`) — applied as inline `style`, NOT as a Tailwind class

### Tooltip
`title="Profile"` on the `<button>` wrapper. `aria-label="Profile menu"`.

---

## 7. Profile Dropdown

### Component: `ProfileDropdown`
**File**: `apps/web/src/components/ProfileDropdown.tsx` (new file)

### Dropdown Panel Dimensions

| Property | Value |
|---|---|
| Width | 200px (`w-50` — or use `min-w-[200px]`) |
| Position | `absolute top-full right-0 mt-1` — anchored below the avatar button, right-aligned |
| Background | `bg-white` |
| Border | `border border-neutral-200` |
| Border-radius | `rounded-lg` (8px) |
| Shadow | `shadow-lg` |
| Z-index | `z-40` — above sidebar (`z-30`) and header (`z-30`), below modals (`z-50`) |
| Padding | `py-1` top and bottom (4px) |
| Overflow | `overflow-hidden` — keeps border-radius clean |

### Dropdown Item Dimensions

| Property | Value |
|---|---|
| Padding | `px-4 py-2.5` (16px horizontal, 10px vertical) |
| Font size | `text-sm` (14px) |
| Font weight | `font-normal` |
| Min height | ~37px (from `py-2.5` + line-height) |
| Border-radius | None — items are full-width within the rounded panel |

### Item List and Styling

```
┌──────────────────────────┐
│  Account            →  /settings/my-account/profile       │
│  Subscription       →  /settings/billing                  │
│  Payment Method     →  /settings/billing/payment-method   │
│  Security           →  /settings/my-account/security      │
├──────────────────────────┤  ← divider: border-t border-neutral-100
│  Sign Out           →  logout()                           │
└──────────────────────────┘
```

**Navigation items (Account, Subscription, Payment Method, Security)**:
| State | Token |
|---|---|
| Default text | `text-neutral-700` |
| Hover background | `hover:bg-neutral-50` |
| Hover text | `hover:text-neutral-900` |
| Transition | `transition-colors duration-100` |
| Click action | `router.push(href)` + close dropdown |

**Divider**:
| Property | Value |
|---|---|
| Element | `<div>` or `<hr>` |
| Style | `border-t border-neutral-100 my-1` |

**Sign Out item**:
| State | Token |
|---|---|
| Default text | `text-fault-600` |
| Default background | transparent |
| Hover background | `hover:bg-fault-50` |
| Hover text | `hover:text-fault-700` |
| Transition | `transition-colors duration-100` |
| Click action | Call `useAuth().logout()` (or `useLogout().logout()` per existing pattern) + close dropdown |
| Font weight | `font-medium` (visually distinguishes the destructive action) |

### Dismiss Behavior
| Trigger | Action |
|---|---|
| Click outside the dropdown panel | Close dropdown — attach `mousedown` listener on `document`, check if click target is outside the panel ref |
| Press `Escape` key | Close dropdown — `keydown` listener when dropdown is open |
| Item selection (any item click) | Close dropdown after navigation/action completes |

### Open/Close Animation
- **Open**: No animation — dropdown appears immediately on click. A simple `opacity` fade is acceptable but not required. If implemented: `transition-opacity duration-100 ease-out`, `opacity-0` → `opacity-100`.
- **Close**: Mirror of open — immediate or `duration-100 ease-in`.

### Positioning Container
The `ProfileDropdown` component renders as a `<div className="relative">` wrapping both the avatar button and the dropdown panel. This allows `absolute` positioning of the dropdown relative to the avatar button without needing `position: fixed` or portal rendering.

---

## 8. Remove Sign Out from Dashboard

**File to update**: `apps/web/src/app/(authed)/dashboard/page.tsx`

The Sign Out button (currently at approximately line 65 per the architect blueprint) must be **completely removed** from the dashboard page. Sign Out is exclusively in the Profile dropdown. No replacement element is needed — the dashboard page content will reflow naturally.

---

## 9. Settings Sidebar — New Order

### Updated `SIDEBAR_ITEMS` Array

The following is the new canonical order for `SettingsSidebar.tsx`. All existing sub-items for retained groups are preserved. Only the order, naming, and group membership change.

| # | Label | Route | Role Gate | Sub-items | Notes |
|---|---|---|---|---|---|
| 1 | Team | `/settings/team` | None | None | Moved to top |
| 2 | Operations | `/settings/operations` | `settings.tenant.write` | Margin buckets, Profitability rules, Field operations | Unchanged sub-items |
| 3 | Notifications | `/settings/notifications/preferences` | None | None | Direct link — no sub-items (from UI-FIX-2C) |
| 4 | Sync & Storage | `/settings/sync-storage` | `settings.tenant.write` | Background sync, Offline limits, Photos, Voice capture | Unchanged sub-items |
| 5 | Integrations | `/settings/integrations` | `integrations.manage` | General, Calendar, QuickBooks (+ Auto-expiry & sync) | Unchanged sub-items |
| 6 | **Branding** | `/settings/communications` | None | Email Branding, SMS & 10DLC | **Renamed from "Communications"** |
| 7 | Voice & AI | `/settings/voice-ai` | None | None | Unchanged |
| 8 | **Security** | `/settings/security` | None | None | **Renamed from "Security & MFA"** |
| 9 | Data & Privacy | `/settings/data-privacy` | None | None | Unchanged |

### Removed Groups
- **`My Account`** group (Profile + Security sub-items) — completely removed from `SIDEBAR_ITEMS`. Profile and Security are now accessed via Profile dropdown → Account and Security links.
- **`Billing`** — removed from `SIDEBAR_ITEMS`. Subscription and Payment Method are accessed via Profile dropdown.

**Note on routes**: The routes `/settings/my-account/profile`, `/settings/my-account/security`, and `/settings/billing` remain functional. They are simply no longer linked from the Settings sidebar. They are linked from the Profile dropdown.

---

## 10. Animations and Transitions

### Sidebar Width Collapse/Expand

| Property | Value |
|---|---|
| CSS property | `width` |
| Duration | 200ms |
| Easing | `ease-in-out` |
| Tailwind class | `transition-[width] duration-200 ease-in-out` |
| Implementation note | The sidebar must have an explicit `width` value in both states — NOT `min-width` or `max-width` — for `transition-[width]` to interpolate correctly. Use inline style or Tailwind: `style={{ width: isSidebarCollapsed ? '64px' : '256px' }}` |

### Logo Width Swap

| Property | Value |
|---|---|
| CSS property | `width` on the logo wrapper `<div>` |
| Duration | 200ms (synced with sidebar) |
| Easing | `ease-in-out` |
| Tailwind class | `transition-[width] duration-200 ease-in-out overflow-hidden` |
| Expanded | `w-[120px]` |
| Collapsed | `w-8` |

The image `src` also changes (primary → icon). To avoid a flash, preload both images via `<link rel="preload">` or use Next.js `<Image>` with both present in DOM (one hidden) if the React Engineer prefers.

### Content Area Shift

The main content area (`flex-1 min-w-0 overflow-auto`) naturally shifts as the sidebar width animates, because both live in the same `flex` row. No separate animation needed on the content area.

### Profile Dropdown Open/Close

| Property | Value |
|---|---|
| Animation | Optional — `opacity` fade |
| Duration | 100ms |
| Easing | `ease-out` (open), `ease-in` (close) |
| If not animated | Instant appear/disappear is acceptable |

---

## 11. State Persistence

### Sidebar Collapsed State
- **`localStorage` key**: `pilot.sidebar.collapsed`
- **Values**: `"true"` (collapsed) or `"false"` (expanded)
- **Default** (key absent or unreadable): expanded (`false`)
- **Read on mount**: Parse with `JSON.parse(localStorage.getItem("pilot.sidebar.collapsed") ?? "false")`
- **Write on toggle**: `localStorage.setItem("pilot.sidebar.collapsed", String(!isSidebarCollapsed))`
- **Hook name**: `useSidebarState()` — create in `apps/web/src/hooks/useSidebarState.ts`. Returns `{ isSidebarCollapsed: boolean; toggleSidebar: () => void }`. Both `AppSidebar` and `AuthedLayout` import this hook so they share state.

---

## 12. RBAC Visibility

| Nav item | Permission | Roles that see it |
|---|---|---|
| Dashboard | None | All authenticated |
| Schedule | None | All authenticated |
| Customers | None | All authenticated |
| Quotes | None | All authenticated |
| Jobs | None | All authenticated |
| Invoices | None | All authenticated |
| Comms | None | All authenticated |
| Catalog | `catalog.view` | All authenticated (tech role included) |
| Reports | `reports.view` | owner, office_staff, operator |

The `tech` role sees: Dashboard, Schedule, Customers, Quotes, Jobs, Invoices, Comms, Catalog. Does NOT see Reports.

The Settings gear icon in the header is visible to **all authenticated roles** (it's a navigation shortcut). The Settings pages themselves are individually RBAC-gated at the page level — this is unchanged.

The Profile dropdown is visible to **all authenticated roles** (every user needs Account and Security access).

---

## 13. ASCII Layout Diagrams

### Expanded Sidebar (1280px+ viewport)

```
┌────────────────────────────────────────────────────────────────────┐
│ HEADER h-12                                                         │
│ [logo-primary.jpg 120×32px]         [🔔 Bell] [⚙ Gear] [AB Avatar] │
├──────────────────────┬──────────────────────────────────────────────┤
│ SIDEBAR w-256px      │ CONTENT AREA flex-1                          │
│ bg-white border-r    │ overflow-auto                                │
│ ──────────────────── │                                              │
│ ▣  Dashboard         │                                              │
│ 📅  Schedule         │   Page content renders here                  │
│ 👥  Customers        │                                              │
│ 📄  Quotes           │                                              │
│ 🔧  Jobs             │                                              │
│ 💵  Invoices         │                                              │
│ 💬  Comms            │                                              │
│ 📦  Catalog          │                                              │
│ 📊  Reports          │                                              │
│                      │                                              │
│ [mt-auto]            │                                              │
│ ‹ Collapse  ──────── │                                              │
└──────────────────────┴──────────────────────────────────────────────┘
```
*(icons are illustrative — actual implementation uses Heroicons SVGs)*

### Collapsed Sidebar (64px)

```
┌────────────────────────────────────────────────────────────────────┐
│ HEADER h-12                                                         │
│ [P icon 32×32px]                    [🔔 Bell] [⚙ Gear] [AB Avatar] │
├──────┬─────────────────────────────────────────────────────────────┤
│  64  │ CONTENT AREA flex-1                                          │
│ ──── │                                                              │
│  ▣   │                                                              │
│  📅  │   Page content (wider now)                                   │
│  👥  │                                                              │
│  📄  │                                                              │
│  🔧  │                                                              │
│  💵  │                                                              │
│  💬  │                                                              │
│  📦  │                                                              │
│  📊  │                                                              │
│      │                                                              │
│  ›   │                                                              │
└──────┴─────────────────────────────────────────────────────────────┘
```

### Profile Dropdown Open (right-aligned below avatar)

```
                                     [🔔][⚙][AB]
                                          ┌────────────────────┐
                                          │  Account           │
                                          │  Subscription      │
                                          │  Payment Method    │
                                          │  Security          │
                                          ├────────────────────┤
                                          │  Sign Out          │
                                          └────────────────────┘
```

---

## 14. Component Manifest

| File | Action | Description |
|---|---|---|
| `frontend/apps/web/src/components/AppSidebar.tsx` | **Rewrite** | Collapsible sidebar: 256px/64px states, Heroicons SVGs (no emoji), `useSidebarState()`, new nav order, active left-border, toggle button, no wordmark block |
| `frontend/apps/web/src/app/(authed)/layout.tsx` | **Update** | Change `justify-end` → `justify-between`; add logo `<Link>+<Image>` left; add `<SettingsGearIcon>` and `<ProfileDropdown>` to right icon group; consume `useSidebarState()` for logo swap |
| `frontend/apps/web/src/components/ProfileDropdown.tsx` | **Create** | Avatar circle with initials + `display_color`; dropdown menu with Account/Subscription/Payment Method/Security/Sign Out; outside-click + Escape dismiss |
| `frontend/apps/web/src/components/SettingsGearIcon.tsx` | **Create** | `Cog6ToothIcon` (outline, 20px), active state when `pathname.startsWith("/settings")`, `title="Settings"`, `router.push("/settings")` on click |
| `frontend/apps/web/src/hooks/useSidebarState.ts` | **Create** | Reads/writes `pilot.sidebar.collapsed` from `localStorage`; returns `{ isSidebarCollapsed: boolean; toggleSidebar: () => void }`; default: `false` (expanded) |
| `frontend/apps/web/src/features/settings/components/SettingsSidebar.tsx` | **Update** | Remove `My Account` group; remove `Billing` item; reorder remaining items per §9; rename "Communications" → "Branding"; rename "Security & MFA" → "Security" |
| `frontend/apps/web/src/app/(authed)/dashboard/page.tsx` | **Update** | Remove Sign Out button entirely |
| `frontend/apps/web/public/brand/logo-primary.jpg` | **Copy from marketing** | Full wordmark — source: `frontend/apps/marketing/public/brand/logo-primary.jpg` |
| `frontend/apps/web/public/brand/logo-primary.svg` | **Copy from marketing** | Full wordmark SVG — source: `frontend/apps/marketing/public/brand/logo-primary.svg` |
| `frontend/apps/web/public/brand/logo-icon.jpg` | **Copy from marketing** | Icon-only (P mark) — source: `frontend/apps/marketing/public/brand/logo-icon.jpg` |
| `frontend/apps/web/public/brand/logo-icon.svg` | **Copy from marketing** | Icon-only SVG — source: `frontend/apps/marketing/public/brand/logo-icon.svg` |

---

## 15. Implementation Notes for React Engineer

1. **Heroicons package verification**: Before using any `@heroicons/react` imports, run `grep "heroicons" frontend/apps/web/package.json`. If not present, add `@heroicons/react` to `apps/web/package.json` devDependencies and run `pnpm install`.

2. **`useSidebarState` hook pattern**: Use `useState` initialized from `localStorage` read inside a `useEffect` (or `useState(() => ...)` lazy initializer) to avoid SSR/hydration mismatch. Example:
   ```ts
   const [isSidebarCollapsed, setIsSidebarCollapsed] = useState<boolean>(() => {
     if (typeof window === "undefined") return false;
     return JSON.parse(localStorage.getItem("pilot.sidebar.collapsed") ?? "false");
   });
   ```

3. **`localStorage` key**: Exactly `pilot.sidebar.collapsed`. Do not change this key — it is specified in the architect blueprint (`batch-ui-fix-2e-design.md § E`).

4. **Logo `<Image>` next.config**: Ensure `/brand/` is served from `apps/web/public/brand/`. Next.js serves `public/` at root — no config change needed. Use `src="/brand/logo-primary.jpg"` (no import).

5. **`useAuth()` for avatar**: The hook is exported from `@pilot/ui` — `import { useAuth } from "@pilot/ui"`. The returned `user` object has `first_name`, `last_name`, `display_color`. If `display_color` is null/undefined, fall back to `bg-brand-600` via Tailwind. If it has a value, use `style={{ backgroundColor: user.display_color }}` and remove the `bg-brand-600` Tailwind class from the element.

6. **Sign Out hook**: Check how the current dashboard Sign Out button calls logout — use the same hook. Based on patterns in `@pilot/ui/auth`, this is likely `useAuth().logout()` or a dedicated `useLogout()` hook. The React Engineer should grep for the current logout call in `dashboard/page.tsx` before implementing.

7. **Settings sidebar routes unchanged**: The `href` values on existing items are not changing — only `label` text and order. The `My Account` group is fully deleted from `SIDEBAR_ITEMS`. `Billing` item (`{ label: "Billing", href: "/settings/billing" }`) is fully deleted.

8. **Active state border-l-2**: The left border on active nav items must be rendered as a `border-l-2 border-brand-600` applied directly to the `<Link>` element — not as an absolutely-positioned pseudo-element. This means the `<Link>` element's left padding should be `pl-2.5` (10px = 3px gap after 2px border) instead of `px-3` when active, so the text/icon alignment stays consistent with inactive items. Alternatively, use negative margin-left with padding compensation. The React Engineer has discretion on the exact technique but must ensure the visible left border does not cause layout shift between active and inactive states.

9. **Transition implementation**: Apply `transition-[width] duration-200 ease-in-out` on the `<nav>` element in `AppSidebar`. The `width` must be set as a CSS value (either inline `style={{ width: isSidebarCollapsed ? "64px" : "256px" }}` or by toggling a class that sets `width`). Tailwind's `w-64`/`w-16` work if you use the `[width]` transition property variant — do NOT use `transition-all` as it will also animate borders and colors unnecessarily.

10. **Test requirements** (for React Engineer to implement tests against):
    - `AppSidebar` collapsed state: only icons visible, no label text
    - `AppSidebar` `localStorage` persistence: toggle → refresh → state preserved
    - `AppSidebar` new nav order: Dashboard, Schedule, Customers, Quotes, Jobs, Invoices, Comms, Catalog, Reports
    - `AppSidebar` removed items: Operations, Sync, Notifications, Settings not rendered
    - `ProfileDropdown` opens on avatar click, closes on Escape and outside-click
    - `ProfileDropdown` Sign Out calls logout function
    - `ProfileDropdown` navigation items have correct hrefs
    - `SettingsGearIcon` active state when pathname starts with `/settings`
    - `AuthedLayout` header contains logo (links to /dashboard), bell, gear, avatar
    - `SettingsSidebar` new order: Team first, My Account absent, Billing absent, "Branding" label, "Security" label
    - `DashboardPage` Sign Out button not present

---

## Handoff Gate

This spec is ready for Tom's review. Implementation starts only after approval.

The React Engineer must NOT begin any code changes until Tom explicitly approves this design spec. Once approved, the React Engineer should reference this document as the authoritative specification for the UI-FIX-2E implementation batch.
