# UI Design Spec — Settings Navigation Redesign
**Batch:** `ui-nav-s1`
**Designer:** Pilot Web UI Designer
**Date:** 2026-07-21
**Status:** Draft v2 — Awaiting Tom's Approval

> **v2 additions (same session):** §15 AppSidebar width fix, §16 Collapse toggle redesign options, §17 Settings navigation macro-pattern decision (SendGrid / Clio / Stripe reference analysis + recommendation), §18 updated component manifest.

---

## 0. What This Spec Covers

The user reported the Settings sub-navigation menu feels "rough" in both layout and UX. This spec targets the **settings navigation entry point and the settings sidebar** — not the individual settings page content, which is already clean and consistent.

Two surfaces are redesigned:

| Surface | Current problem | This spec's solution |
|---|---|---|
| `SettingsGearIcon` (header ⚙) | Hard-navigates to `/settings`, abandoning user's current context | Opens a **Settings Dropdown Panel** — grouped quick-access links without leaving the page |
| `SettingsSidebar` (second sidebar on settings pages) | Plain text list, no icons, no category grouping, sub-items hidden until active | Redesigned with icons, group section headers, always-visible sub-items, cleaner visual hierarchy |

---

## 1. Surface Overview

### 1A — Settings Dropdown Panel (new component)

- **Trigger:** `SettingsGearIcon` button in the top header bar
- **Route context:** Appears over any authenticated route — the user never leaves their current page
- **RBAC:** The dropdown itself is visible to all authenticated roles. Individual links within it are gated — `tech` role sees only "Voice & AI"; all other items are hidden via `<RoleGate>`
- **Component location:** `apps/web/src/components/SettingsDropdownPanel.tsx` (new)

### 1B — Improved SettingsSidebar

- **Route:** All `/settings/*` routes
- **Component location:** `apps/web/src/features/settings/components/SettingsSidebar.tsx` (modified)
- **RBAC:** Same hide-not-disable rules as current implementation; `tech` role cannot access `/settings/*` at all

---

## 2. UX Diagnosis — Current Pain Points

Reading the existing code reveals five structural problems:

1. **Hard navigation on gear click** — `SettingsGearIcon.tsx` calls `router.push("/settings")` on click. This abandons the user's working context (e.g., mid-way through viewing a job) to navigate to a full settings page. There is no way to "peek" at settings without leaving your place.

2. **Triple-column layout is visually heavy** — `SettingsShell.tsx` renders inside `AuthedLayout`/layout.tsx), which already has the `AppSidebar` at 256px. The `SettingsSidebar` adds another `w-56` (224px). At 1280px viewport, that is 480px of left chrome before any content — 37.5% of the screen.

3. **No icons in settings sidebar** — `SettingsSidebar.tsx` is pure text. The `AppSidebar` uses Heroicons for every item, making it scannable in ~300ms. The settings sidebar forces the user to read every word to orient.

4. **Sub-items are hidden until activated** — The `renderItem` function only shows `subItems` when `isExpanded = active || ancestor`. A user looking at "Team" cannot see that "Operations" contains "Margin buckets" without clicking into it. Discoverability is low.

5. **No category grouping** — 9 items (Team → Data & Privacy) are a flat list. There is no visual separation between personal settings, workspace settings, and system/integration settings. The eye has nowhere to anchor.

---

## 3. Design Pattern Reference — Industry Comparison

The following patterns from well-regarded SaaS products informed this spec:

| Product | Pattern | Why relevant |
|---|---|---|
| **Vercel Dashboard** | Gear click → grouped dropdown panel with direct links; sidebar uses icons + section headers | Same user type (technical operator), same density of settings |
| **Linear** | Settings open as full-page overlay (modal-like) over current page | Preserves working context; "close" returns user to exactly where they were |
| **Stripe Dashboard** | Settings sidebar: icon + label, group headers ("Account", "Business", "Product") | Makes 15+ settings items scannable without reading every word |
| **GitHub Settings** | Always-visible sidebar with section dividers; sub-items permanently shown as indented list | No surprise "hidden" items; user can see the full map at a glance |
| **Notion** | Dropdown from avatar: quick-access links for most common settings (name, email, notifications) + "More settings" to full page | Respects the 80/20 rule — users visit 2-3 settings far more than all others |

**Synthesis for Pilot:** The gear icon should open a **compact dropdown panel** (Vercel/Notion pattern) for quick access. The full settings pages retain the sidebar but it is redesigned (Stripe/GitHub pattern) with icons, group headers, and permanently-visible structure.

---

## 4. Design Decision: Dropdown Panel vs. Settings Modal Overlay

Two leading options were considered:

| Option | Pros | Cons |
|---|---|---|
| **A. Dropdown panel from gear** (chosen) | Lightweight, no route change, works with existing SettingsShell, zero layout risk | Limited space — can't show all settings in dropdown |
| **B. Full-screen modal overlay** | Context-preserving, full settings visible | Significant architecture change, two sidebars inside a modal is complex, risk to existing settings pages |

**Decision: Option A** — The dropdown panel from the gear icon provides immediate UX improvement with minimal implementation risk. The full settings pages remain at their routes and get the improved sidebar.

---

## 5. Component 1: `SettingsDropdownPanel`

### 5.1 Trigger Behavior

The `SettingsGearIcon` is modified to toggle a dropdown panel instead of calling `router.push("/settings")`.

- **Click:** Opens/closes `SettingsDropdownPanel`
- **Escape key:** Closes panel
- **Click outside:** Closes panel (focus trap not required — this is not a modal)
- **When `/settings/*` is active:** Gear icon remains in active state (`bg-brand-50 text-brand-600`); dropdown still opens/closes

### 5.2 Panel Dimensions & Positioning

```
┌─────────────────────────────────┐
│ [⚙] ← gear button (9×9, h-9)  │  ← anchor in header
└──────────┐                      │
           │ DROPDOWN PANEL       │
           │ w-72 (288px)        │
           │ Positioned: right-0  │
           │ top: calc(100% + 8px)│
           │ bg-white             │
           │ rounded-lg           │
           │ shadow-lg            │
           │ border border-neutral-200│
           │ z-40                 │
           └─────────────────────-┘
```

- **Width:** `w-72` (288px) — wide enough to read labels, narrow enough to not overlap sidebar
- **Max height:** `max-h-[480px] overflow-y-auto` — unlikely to need scroll, but safe
- **Position:** `absolute right-0 top-full mt-2` relative to the gear button container
- **z-index:** `z-40` (dropdowns per design system reference)
- **Border radius:** `rounded-lg` (`border-radius: 8px`)
- **Shadow:** `shadow-lg`
- **Border:** `border border-neutral-200`
- **Background:** `bg-white`

### 5.3 Panel Anatomy

```
┌──────────────────────────────────┐
│ PERSONAL                    12px │  ← section header, text-caption, text-neutral-500, uppercase, tracking-wider
│ ┌─────────────────────────────┐  │
│ │ 👤 Profile & Account        │  │  ← link row (hover:bg-neutral-50)
│ │ 🔐 Security & MFA          │  │
│ └─────────────────────────────┘  │
│                                  │
│ WORKSPACE                        │  ← section header
│ ┌─────────────────────────────┐  │
│ │ 👥 Team                    │  │
│ │ ⚙️  Operations              │  │  (role-gated: settings.tenant.write)
│ │ 🔔 Notifications            │  │
│ │ 🏷️  Branding                │  │  (role-gated: settings.tenant.write)
│ └─────────────────────────────┘  │
│                                  │
│ INTEGRATIONS & SYSTEM           │  ← section header
│ ┌─────────────────────────────┐  │
│ │ 🔗 Integrations             │  │  (role-gated: integrations.manage)
│ │ 🎙 Voice & AI              │  │
│ │ 🗄 Sync & Storage           │  │  (role-gated: settings.tenant.write)
│ │ 🛡 Data & Privacy           │  │
│ └─────────────────────────────┘  │
│ ────────────────────────────── │  ← divider (border-t border-neutral-100)
│ All settings →                   │  ← full settings link (text-brand-600, text-sm)
└──────────────────────────────────┘
```

*(Emoji above are for layout illustration only — actual icons are Heroicons per §5.5)*

### 5.4 Section Header Spec

```
padding: px-4 pt-3 pb-1
typography: text-[10px] font-semibold tracking-widest uppercase text-neutral-400
```

### 5.5 Link Row Spec

Each row is an anchor/link element:

```
height: 40px (h-10)
padding: px-4 py-2
display: flex items-center gap-3
border-radius: rounded-md (applied inside px-2 container)
```

**States:**
- Default: `bg-transparent text-neutral-700`
- Hover: `hover:bg-neutral-50 hover:text-neutral-900`
- Active (current route): `bg-brand-50 text-brand-700 font-medium`
- Focus-visible: `focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500`

**Icon:** `w-4 h-4` (16px), `text-neutral-500` default, inherits `text-brand-700` when active

**Label:** `text-sm text-neutral-700` default

**Transition:** `transition-colors duration-100`

### 5.6 Icon Inventory — Dropdown Panel

| Link label | Heroicon (outline) |
|---|---|
| Profile & Account | `UserCircleIcon` |
| Security | `ShieldCheckIcon` |
| Team | `UsersIcon` |
| Operations | `AdjustmentsHorizontalIcon` |
| Notifications | `BellIcon` |
| Branding | `SwatchIcon` |
| Integrations | `ArrowsRightLeftIcon` |
| Voice & AI | `MicrophoneIcon` |
| Sync & Storage | `CloudArrowUpIcon` |
| Data & Privacy | `LockClosedIcon` |
| All settings → | `Cog6ToothIcon` (w-4 h-4, inline before text) |

### 5.7 "All settings →" Footer Row

```
border-t border-neutral-100
padding: px-4 py-3
display: flex items-center gap-2
typography: text-sm font-medium text-brand-600
hover: text-brand-700 hover:bg-neutral-50
icon: Cog6ToothIcon w-4 h-4 inline-start; ChevronRightIcon w-3 h-3 inline-end
```

Clicking navigates to `/settings` (the full settings page experience).

### 5.8 RBAC in Dropdown Panel

All items are wrapped with `<RoleGate>` using hide-not-disable:

| Item | Permission gate |
|---|---|
| Profile & Account | None (all roles) |
| Security | None (all roles) |
| Team | `settings.tenant.write` |
| Operations | `settings.tenant.write` |
| Notifications | None (all roles) |
| Branding | `settings.tenant.write` |
| Integrations | `integrations.manage` |
| Voice & AI | None (all roles) |
| Sync & Storage | `settings.tenant.write` |
| Data & Privacy | None (all roles) |

**`tech` role result:** Dropdown shows Personal section (Profile, Security), Notifications, Voice & AI. All workspace/integration items hidden. "All settings →" link is also hidden for `tech` (they have no settings pages to land on).

### 5.9 Animation Spec — Dropdown Panel

```css
/* Enter */
transition: opacity 150ms ease-out, transform 150ms ease-out;
from: opacity-0 translate-y-[-4px]
to:   opacity-100 translate-y-0

/* Exit */
transition: opacity 100ms ease-in, transform 100ms ease-in;
from: opacity-100 translate-y-0
to:   opacity-0 translate-y-[-4px]
```

Implemented via Tailwind + Headless UI `Transition` component or CSS class toggling.

---

## 6. Component 2: `SettingsSidebar` Redesign

### 6.1 Layout Philosophy Changes

The current sidebar has no icons and uses hidden sub-items. The redesigned sidebar:

- **Adds icons** to all top-level items (same Heroicons set as the dropdown panel, §5.6)
- **Always shows sub-items** — no expand/collapse; all child links are permanently visible, indented
- **Adds group section headers** — three groups: PERSONAL, WORKSPACE, INTEGRATIONS & SYSTEM
- **Sub-items get subtle dot indicators** — instead of just indentation, a small `·` separator or left-border accent makes the hierarchy clear

### 6.2 Updated Sidebar Dimensions

The current sidebar is `w-56` (224px). This is sufficient but the internal structure needs refinement:

```
Width: w-56 (224px) — unchanged
Padding: py-4 px-3 (top/bottom, horizontal — tighter than current py-6 pr-4)
```

### 6.3 Section Header Spec (Sidebar)

```
margin-top: mt-4 (first section: mt-0)
padding: px-2 pb-1
typography: text-[10px] font-semibold tracking-widest uppercase text-neutral-400
```

### 6.4 Top-Level Item Spec

```
height: 36px
padding: px-2 py-2
display: flex items-center gap-2.5
border-radius: rounded-md
typography: text-sm font-medium
```

**States:**
- Default: `text-neutral-700 hover:bg-neutral-100 hover:text-neutral-900`
- Active (exact match): `bg-brand-50 text-brand-700 font-medium` + left accent border: `border-l-2 border-brand-600 pl-[6px]` (6px = 8px default left padding minus 2px border)
- Ancestor (sub-page active): `text-neutral-900` — no background, no border; sub-items shown
- Transition: `transition-colors duration-150`

**Icon:** `w-5 h-5 shrink-0` in `text-neutral-400` default; `text-brand-600` when active or ancestor

### 6.5 Sub-Item Spec (Always Visible)

Sub-items are **always rendered** (not toggled). This is the key UX improvement.

```
padding-left: pl-9 (36px — aligns with text after parent icon + gap)
height: 32px (h-8)
padding-vertical: py-1.5
border-radius: rounded-md
typography: text-xs text-neutral-600
```

**States:**
- Default: `text-neutral-600 hover:bg-neutral-50 hover:text-neutral-900`
- Active: `bg-brand-50 text-brand-700 font-medium`
- Transition: `transition-colors duration-100`

**Left accent:** For active sub-items, a 2px left border `border-l-2 border-brand-400` at `ml-[18px]` to distinguish from top-level active item. This creates a softer visual weight for the third-level indicator.

### 6.6 Third-Level Sub-Items (QuickBooks > Auto-expiry)

Only one item currently has depth-3: `Auto-expiry & sync` under `Integrations → QuickBooks`.

```
padding-left: pl-14 (56px)
height: 28px (h-7)
typography: text-xs text-neutral-500
States: same hover/active pattern as depth-2 but smaller
```

### 6.7 Updated Sidebar Structure with Section Headers

```
PERSONAL
  [UserCircleIcon] Profile & Account       → /settings/my-account/profile
  [ShieldCheckIcon] Security               → /settings/security

WORKSPACE
  [UsersIcon] Team                         → /settings/team
  [AdjustmentsHorizontalIcon] Operations   → /settings/operations  [RoleGate: settings.tenant.write]
    Margin buckets                         → /settings/operations/margin-buckets
    Profitability rules                    → /settings/operations/profitability-rules
    Field operations                       → /settings/operations/field-operations
  [BellIcon] Notifications                 → /settings/notifications/preferences
  [SwatchIcon] Branding                   → /settings/communications  [RoleGate: settings.tenant.write]
    Email Branding                         → /settings/communications/email-branding
    SMS & 10DLC                            → /settings/communications/sms-compliance

INTEGRATIONS & SYSTEM
  [ArrowsRightLeftIcon] Integrations       → /settings/integrations  [RoleGate: integrations.manage]
    General                                → /settings/integrations/general
    Calendar                               → /settings/integrations/calendar
    QuickBooks                             → /settings/integrations/quickbooks
      Auto-expiry & sync                   → /settings/integrations/quickbooks/auto-expiry
  [MicrophoneIcon] Voice & AI             → /settings/voice-ai
  [CloudArrowUpIcon] Sync & Storage       → /settings/sync-storage  [RoleGate: settings.tenant.write]
    Background sync                        → /settings/sync-storage/background-sync
    Offline limits                         → /settings/sync-storage/offline-limits
    Photos                                 → /settings/sync-storage/photos
    Voice capture                          → /settings/sync-storage/voice-capture
  [LockClosedIcon] Data & Privacy         → /settings/data-privacy
```

> **Note on "Profile & Account":** The current `SIDEBAR_ITEMS` in `SettingsSidebar.tsx` starts with "Team" — there is no Profile/Account top-level entry. The UI-FIX-2E redesign moved Profile to `ProfileDropdown`. For the settings sidebar redesign, "Profile & Account" and "Security" are added back as a PERSONAL group so the sidebar is a complete map of all settings — users should not need the header dropdown to find personal settings when they are already in the settings area. The React Engineer should confirm with Tom whether `/settings/my-account/profile` exists as a route.

### 6.8 Search Component Placement

The `<SettingsSidebarSearch>` currently renders at the top of the sidebar (`px-1` container above the nav list). This is kept in the redesign but visually improved:

```
position: top of sidebar, above section groups
padding: px-2 pb-3
input: w-full rounded-md border border-neutral-200 bg-neutral-50 px-3 py-2 text-sm
       placeholder: "Search settings…" text-neutral-400
       focus: ring-2 ring-brand-500 border-brand-500 bg-white
icon: MagnifyingGlassIcon w-4 h-4 text-neutral-400, inline-start of input
```

---

## 7. Modified Component: `SettingsGearIcon`

The existing `SettingsGearIcon` must change from a router-push button to a toggle button that controls the `SettingsDropdownPanel`.

**New behavior:**
- Becomes a controlled toggle: `isOpen` state drives dropdown visibility
- `onClick`: toggles `isOpen`; does NOT call `router.push`
- `aria-expanded`: `isOpen ? "true" : "false"`
- `aria-haspopup="true"`
- When `pathname.startsWith("/settings")`: keep active styling even when dropdown is closed

**State management options (for React Engineer):**
- Local `useState` in a new wrapper component `SettingsNavControl` that renders both the gear button and the dropdown panel, OR
- Lift state to the header area in `layout.tsx` with a shared boolean

Recommended: Create a new `SettingsNavControl` client component that encapsulates the gear button + dropdown panel pair, and replace `<SettingsGearIcon />` in `layout.tsx` with `<SettingsNavControl />`.

---

## 8. State Coverage

### 8.1 Dropdown Panel States

| State | Visual treatment |
|---|---|
| Closed | Panel not rendered (or `hidden`) |
| Opening | Fade + slide-down animation (§5.9) |
| Open — no active route | All links default style |
| Open — `/settings/team` active | "Team" link shows `bg-brand-50 text-brand-700` |
| Open — non-settings route | No link is active |
| `tech` role | Only Personal + Voice & AI items visible |
| `owner`/`operator` role | All items visible |

### 8.2 Settings Sidebar States

| State | Visual treatment |
|---|---|
| Top-level active | `bg-brand-50 text-brand-700 border-l-2 border-brand-600` |
| Ancestor (sub-page) | No background, icon `text-brand-600`, sub-items visible (always) |
| Sub-item active | `bg-brand-50 text-brand-700 border-l-2 border-brand-400` |
| Hover (any item) | `hover:bg-neutral-100` |
| Role-gated item hidden | Item not rendered |
| Search results | Filtered list replaces nav structure temporarily |

---

## 9. Full Layout Diagrams

### 9.1 Header with Dropdown Open

```
┌────────────────────────────────────────────────────────────────────────────────┐
│ HEADER h-12 bg-white border-b border-neutral-200 z-30                         │
│ [logo 120×32]                           [🔔 Bell] [⚙ Gear ←active] [Avatar]   │
│                                                        ┌──────────────────┐   │
│                                                        │ SETTINGS DROPDOWN│   │
│                                                        │ w-72, bg-white   │   │
│                                                        │ shadow-lg z-40   │   │
│                                                        │                  │   │
│                                                        │ PERSONAL         │   │
│                                                        │  Profile         │   │
│                                                        │  Security        │   │
│                                                        │                  │   │
│                                                        │ WORKSPACE        │   │
│                                                        │  Team            │   │
│                                                        │  Operations      │   │
│                                                        │  Notifications   │   │
│                                                        │  Branding        │   │
│                                                        │                  │   │
│                                                        │ INTEGRATIONS     │   │
│                                                        │  Integrations    │   │
│                                                        │  Voice & AI      │   │
│                                                        │  Sync & Storage  │   │
│                                                        │  Data & Privacy  │   │
│                                                        │ ─────────────── │   │
│                                                        │ ⚙ All settings → │   │
│                                                        └──────────────────┘   │
└────────────────────────────────────────────────────────────────────────────────┘
```

### 9.2 Settings Page Layout with Redesigned Sidebar

```
┌──────────────────────────────────────────────────────────────────────┐
│ HEADER (h-12)                                                        │
├──────────┬──────────────────────────────────────────────────────────┤
│ APP      │ SETTINGS SIDEBAR w-56          │ CONTENT                 │
│ SIDEBAR  │ bg-white border-r              │ flex-1 bg-neutral-50    │
│ 256px    │ border-neutral-200             │ max-w-3xl px-6 py-8     │
│          │                                │                         │
│ (icons   │ [🔍 Search settings…        ] │ [SettingsBreadcrumb]    │
│  only    │                                │                         │
│  in      │ PERSONAL                       │ Page content here       │
│  collapsed│  [👤] Profile & Account      │                         │
│  mode)   │  [🛡] Security               │                         │
│          │                                │                         │
│          │ WORKSPACE                      │                         │
│          │  [👥] Team                   │                         │
│          │  [⚙] Operations ←active     │                         │
│          │    Margin buckets              │                         │
│          │    Profitability rules         │                         │
│          │    Field operations ←active   │                         │
│          │  [🔔] Notifications           │                         │
│          │  [🎨] Branding               │                         │
│          │    Email Branding              │                         │
│          │    SMS & 10DLC                 │                         │
│          │                                │                         │
│          │ INTEGRATIONS & SYSTEM          │                         │
│          │  [🔗] Integrations            │                         │
│          │    General                     │                         │
│          │    Calendar                    │                         │
│          │    QuickBooks                  │                         │
│          │  [🎙] Voice & AI             │                         │
│          │  [☁] Sync & Storage          │                         │
│          │    Background sync             │                         │
│          │    Offline limits              │                         │
│          │    Photos                      │                         │
│          │    Voice capture               │                         │
│          │  [🔒] Data & Privacy         │                         │
└──────────┴────────────────────────────────┴─────────────────────────┘
```

---

## 10. Interaction Spec — Complete

### 10.1 Gear Button (Modified `SettingsGearIcon`)

| Interaction | Result |
|---|---|
| Click (closed) | Open `SettingsDropdownPanel` with enter animation |
| Click (open) | Close panel with exit animation |
| Escape key | Close panel |
| Click outside panel | Close panel |
| Tab focus | Focus-visible ring: `focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-1` |
| Hover | `hover:bg-neutral-100 hover:text-neutral-700` (non-settings) or `hover:bg-brand-100 hover:text-brand-700` (when on /settings) |

### 10.2 Dropdown Panel Link Rows

| Interaction | Result |
|---|---|
| Click | Navigate to settings route, close panel |
| Hover | `hover:bg-neutral-50 hover:text-neutral-900` |
| Focus | `focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-1 rounded-md` |
| Tab | Moves to next link row in order |
| Shift+Tab | Moves to previous link row |

### 10.3 Settings Sidebar — Top-Level Items

| Interaction | Result |
|---|---|
| Click | Navigate to top-level route; active style applied |
| Hover | `hover:bg-neutral-100` |
| Focus | `focus-visible:ring-2 focus-visible:ring-brand-500` |

### 10.4 Settings Sidebar — Sub-Items

| Interaction | Result |
|---|---|
| Click | Navigate to sub-route; active style on sub-item AND ancestor indicator on parent |
| Hover | `hover:bg-neutral-50` |
| Focus | `focus-visible:ring-2 focus-visible:ring-brand-500` |

---

## 11. Animation Spec — Summary

| Element | Property | Duration | Easing |
|---|---|---|---|
| Dropdown panel enter | `opacity`, `translateY` | `150ms` | `ease-out` |
| Dropdown panel exit | `opacity`, `translateY` | `100ms` | `ease-in` |
| Gear button active state | `background-color`, `color` | `150ms` | `ease-in-out` |
| Sidebar item hover | `background-color`, `color` | `150ms` | `ease-in-out` |

---

## 12. Implementation Notes for React Engineer

1. **`SettingsNavControl` wrapper:** Create `apps/web/src/components/SettingsNavControl.tsx` as a `"use client"` component. It owns `const [isOpen, setIsOpen] = useState(false)` and renders both the gear button and `SettingsDropdownPanel`. Replace `<SettingsGearIcon />` in `layout.tsx` with `<SettingsNavControl />`.

2. **Click-outside handling:** Use a `useEffect` that adds a `mousedown` listener on `document` when `isOpen === true`. Compare `event.target` against a ref on the dropdown panel. On mismatch, call `setIsOpen(false)`.

3. **Escape key handling:** Add a `keydown` listener when `isOpen === true`; close on `key === "Escape"`. Return focus to the gear button after close.

4. **`SettingsDropdownPanel` RBAC:** The dropdown has no data-fetch — it is pure static links. Use `useRequiresPermission` (from `@pilot/ui/role-gate`) for each gated item. The existing `permissionGranted` pattern from `AppSidebar.tsx` can be reused.

5. **Always-visible sub-items in sidebar:** Remove the `isExpanded` guard on `subItems` rendering in `SettingsSidebar.tsx`. Sub-items should always render regardless of active state.

6. **Section headers in sidebar:** Add a `group` property to `SidebarItem` or use a separate `SIDEBAR_GROUPS` config structure:
   ```ts
   const SIDEBAR_GROUPS = [
     { label: "PERSONAL", items: [profileItem, securityItem] },
     { label: "WORKSPACE", items: [teamItem, operationsItem, notificationsItem, brandingItem] },
     { label: "INTEGRATIONS & SYSTEM", items: [integrationsItem, voiceAiItem, syncStorageItem, dataPrivacyItem] },
   ]
   ```

7. **Profile & Account route:** The dropdown and sidebar both reference `/settings/my-account/profile`. If this route does not exist, use `/settings/security` as a fallback for the "Personal" group entry point, or confirm with Tom whether this route should be created as part of this batch.

8. **`SettingsGearIcon.tsx` file:** This file can be deleted and replaced by the gear button rendered inside `SettingsNavControl.tsx`. The `SettingsNavControl` component absorbs all its logic.

9. **Z-index reminder:** Dropdown at `z-40`, app header at `z-30`. The dropdown must be a sibling or child of the header element to stack correctly — not inside the header's `overflow: hidden` context. Render `SettingsDropdownPanel` with `position: absolute` inside a `position: relative` wrapper div around the gear button.

10. **`SettingsSidebarSearch` stays in place** — no changes to the search component API. It remains at the top of the sidebar, above the section groups.

---

## 13. Component Manifest

| File | Status | Description |
|---|---|---|
| `apps/web/src/components/SettingsNavControl.tsx` | **New** | Wrapper component owning dropdown open/close state; renders gear button + `SettingsDropdownPanel` |
| `apps/web/src/components/SettingsDropdownPanel.tsx` | **New** | Grouped settings quick-access dropdown panel, triggered from header gear button |
| `apps/web/src/components/SettingsGearIcon.tsx` | **Delete** | Replaced by gear button logic inside `SettingsNavControl.tsx` |
| `apps/web/src/app/(authed)/layout.tsx` | **Modified** | Replace `<SettingsGearIcon />` import/usage with `<SettingsNavControl />` |
| `apps/web/src/features/settings/components/SettingsSidebar.tsx` | **Modified** | Add icons, section group headers, always-visible sub-items; add PERSONAL group entries |

---

## 14. Out of Scope for This Batch (§5–§13, Option 1 only)

- Changes to individual settings page content (Team, Operations, Notifications, etc.)
- Settings search catalog changes (`SettingsSidebarSearch` behavior unchanged)
- Adding Profile & Account or My Account route/page (noted as dependency above)
- Mobile settings navigation (belongs to `pilot-voice-ui-designer`)
- `SettingsBreadcrumb` changes (already clean; no redesign needed)

---

## 15. AppSidebar Width — Fix Excessive Whitespace

### 15.1 Problem

The current `AppSidebar` uses fixed widths: `16rem` (256px) expanded, `4rem` (64px) collapsed. At 1280px viewport the expanded sidebar consumes 20% of the screen width. With the settings sidebar also open, it reaches 37.5%. The expanded sidebar at 256px has significant right-side padding waste — the longest label "Dashboard" is ~88px text + 20px icon + 12px gap = ~120px actual content, leaving ~136px of unused whitespace on the right.

### 15.2 Solution — Content-Fit Expanded Width

Instead of a fixed `16rem`, the expanded sidebar uses a Tailwind content-fit pattern with guards:

```
Expanded:  min-w-[160px] max-w-[200px] w-fit
Collapsed: w-16 (64px) — unchanged
```

`w-fit` lets the sidebar shrink to the widest nav label. `min-w-[160px]` prevents it becoming too narrow. `max-w-[200px]` caps growth if a future label is long. This recovers ~56px of horizontal space vs. the current 256px fixed width.

**Padding inside nav items:** Keep `px-2 py-2` on each item (unchanged). The sidebar outer container switches from inline `style={{ width }}` to Tailwind classes.

**Implementation note for React Engineer:** In `AppSidebar.tsx` replace:
```ts
const sidebarWidth = isSidebarCollapsed ? "4rem" : "16rem";
// ...
style={{ width: sidebarWidth }}
```
With Tailwind classes on the `<nav>` element (remove inline style):
```tsx
className={`... ${isSidebarCollapsed ? "w-16" : "w-fit min-w-[160px] max-w-[200px]"}`}
```

Also update `layout.tsx` — the logo container width `7.5rem` was sized for 256px sidebar context. It can remain at `7.5rem` unchanged (the logo overlaps header, not sidebar).

### 15.3 Animation for w-fit

CSS `transition-[width]` cannot animate to/from `fit-content`. Two options:

| Option | Approach | Recommendation |
|---|---|---|
| **A. JS-measured px** | `useRef` + `getBoundingClientRect` on expanded state; animate between measured px ↔ 64px | Accurate smooth animation, slightly more JS |
| **B. No transition on expand** | Remove `transition-[width]` for expand direction; keep instant expand, animate collapse only | Simpler — collapse animation is the visually important one |

**Recommendation: Option B.** Collapse animates (sidebar folding in); expand is instant snap. Acceptable UX for a B2B tool.

---

## 16. Collapse Toggle — Redesign Options

### 16.1 Current Design Problem

The current `AppSidebar.tsx` places the toggle at the bottom:

```
┌──────────────────┐
│ [nav items]      │
│                  │
│ ─────────────── │
│ [Collapse <]     │  ← text + icon, bottom-right
└──────────────────┘
```

Problems: (1) Far from where the eye tracks nav items. (2) Text label "Collapse" is redundant — icon communicates the action. (3) In collapsed state the `>` arrow at 16px is easy to miss.

### 16.2 Option A — `«` / `»` Pill Button (Tom's Suggestion) ⭐ Recommended

A compact round pill button at the **top-right corner of the sidebar**, overlapping the sidebar/content border by 50%:

```
EXPANDED STATE:
┌────────────────────[«]─  ← pill overlaps border
│ [Dashboard]
│ [Schedule]
│ ...

COLLAPSED STATE:
┌────[»]─
│  [icon]
│  [icon]
```

**Pill button spec:**
```
Size:       w-6 h-6 (24×24px)
Shape:      rounded-full
Background: bg-white
Border:     border border-neutral-200
Shadow:     shadow-sm
Position:   absolute top-3 -right-3 (overlaps sidebar right border by 12px)
z-index:    z-20 (above sidebar content, below header z-30)
Icon:       ChevronDoubleLeftIcon (expanded) / ChevronDoubleRightIcon (collapsed)
            w-3 h-3 (12px)
Icon color: text-neutral-500 hover:text-neutral-700
Hover bg:   hover:bg-neutral-50
Cursor:     cursor-pointer
Transition: transition-colors duration-150
```

**Animation:** Animate the icon only — use a single `ChevronDoubleLeftIcon` with `rotate-180` transform on collapsed state:
```
Expanded:  rotate-0   (« points left = "collapse left")
Collapsed: rotate-180 (now points right = "expand right")
transition: transform 200ms ease-in-out
```

**Implementation note:** The pill must sit outside the sidebar `<nav>` (which has `overflow: hidden`). Wrap `AppSidebar` in `layout.tsx` with a `relative` div:
```tsx
<div className="relative flex-shrink-0">
  <AppSidebar />
  {/* OR: move the pill inside AppSidebar as a sibling <div> after <nav>, inside a wrapper */}
</div>
```
The React Engineer should move the pill button out of the `<nav>` and into a wrapper `<div className="relative ...">` that contains both `<nav>` and the pill `<button>`.

### 16.3 Option B — Top-Right Corner Flat Icon (No Pill)

A borderless icon button at the top-right corner of the sidebar:

```
┌────────────────── [←] ┐  ← ChevronLeftIcon, 20px, absolute top-2 right-2
│ [Dashboard]           │
└───────────────────────┘
```

```
Size:       w-8 h-8 (32px touch target)
Position:   absolute top-2 right-2 inside sidebar
Background: transparent
Hover:      hover:bg-neutral-100 rounded-md
Icon:       ChevronLeftIcon (expanded), ChevronRightIcon (collapsed), w-4 h-4
Color:      text-neutral-400 hover:text-neutral-600
```

**Pros:** Simplest implementation — no overflow issues, no external wrapper.
**Cons:** Occupies corner real estate inside the sidebar; in collapsed state, the 32px button fills most of the 64px sidebar width.

### 16.4 Option C — Hover-Revealed Edge Handle (Most Minimal)

No persistent button. The right edge of the sidebar reveals a 4px colored handle on hover:

```
On hover of sidebar right edge:
  → 4px bg-brand-200 right border appears
  → cursor: col-resize
  → Tooltip: "Collapse" / "Expand"
```

**Pros:** Zero persistent UI clutter. Maximum content space.
**Cons:** Hidden affordance — low discoverability for non-technical trades users.

### 16.5 Comparison Table

| Option | Discoverability | Footprint | Implementation complexity | Recommended for Pilot |
|---|---|---|---|---|
| **A — Pill** | ⭐⭐⭐ High | Minimal (overlaps border) | Medium | ✅ Yes |
| **B — Flat icon** | ⭐⭐ Medium | Small (corner) | Low | Acceptable fallback |
| **C — Edge handle** | ⭐ Low | Zero | Medium | No |

**Recommendation: Option A (pill).** Most discoverable, most modern, zero internal sidebar footprint.

---

## 17. Settings Navigation Macro-Pattern — Reference Analysis & Recommendation

Tom provided three reference screenshots showing alternative settings navigation models. Analysis of each:

### 17.1 Pattern A — SendGrid: Inline Expand in Main Nav

**What it does:** "Settings" is a nav item in the primary left sidebar. Clicking expands a flat, scrollable list of settings links **inline within the same sidebar** (accordion). No second sidebar.

**Pros for Pilot:** Eliminates the double-sidebar chrome problem entirely. Settings feel like a peer nav item.

**Cons for Pilot:**
- Sidebar becomes very long when expanded — Pilot's 9 primary nav items + 10+ settings items requires scrolling
- SendGrid's list is flat/text-only with no grouping or icons — inconsistent with Pilot's icon-first nav style
- Pilot's settings have depth-2 and depth-3 sub-items; inline-expanding creates an extremely tall sidebar

**Verdict: Partial adoption only.** Could work with group headers and depth-1-only expansion (no sub-items), but still a tight fit for Pilot's content density.

### 17.2 Pattern B — Clio: Settings Index Page (Full Page, Dark Sidebar)

**What it does:** "Settings" at the bottom of the primary sidebar navigates to a **full-page settings index** — a 3-column card layout (SYSTEM / PERSONAL / CLIO SETTINGS) with titled links + one-sentence descriptions. The left sidebar stays visible with Settings highlighted. **No second settings sidebar.**

```
[Primary sidebar — Settings active]  |  SETTINGS index page
                                     |  SYSTEM        PERSONAL      CLIO SETTINGS
                                     |  Account Info  Profile       Firm Prefs
                                     |  Manage Users  Appearance    Billing
                                     |  ...           ...           ...
```

**Pros for Pilot:**
- Completely eliminates the double-sidebar layout — fixes the #1 chrome problem
- Every settings area gets a description — reduces "what is this?" cognitive load
- 3-column grid makes 10+ settings scannable in seconds
- RBAC-friendly: simply hide cards by role

**Cons for Pilot:**
- Requires a new `SettingsIndexPage` component
- `SettingsShell` and `SettingsSidebar` become deprecated — migration effort for all settings routes

**Verdict: Strong candidate.** Directly solves Tom's stated problem.

### 17.3 Pattern C — Stripe: Settings Index Page (Light Theme, Icon + Description Cards)

**What it does:** Settings gear (⚙) in the top header navigates to `/settings` — a full settings index page. Three category sections (Personal / Account / Product settings), each with a 3-column icon+title+description card grid. **No second sidebar whatsoever.**

```
Personal settings
  [👤] Personal details       [✉] Communication pref.  [<>] Developers
       Contact info, auth          Emails, SMS

Account settings
  [🏢] Business  [🔐] Team & Security  [💳] Plans & Fees
  [🌐] Profile   [📋] Compliance       [✨] Features & Previews

Product settings
  [💰] Billing  [🌍] Global Payouts  [📊] Sigma  [⚡] Tax  ...
```

**Pros for Pilot:**
- Most scannable of the three patterns — icon + bold title + description = 3-layer visual hierarchy
- Section separators with category labels give immediate orientation
- No second sidebar
- Scales gracefully with RBAC (hide cards)
- Most consistent with Pilot's existing design tokens and icon system

**Cons for Pilot:**
- Product settings section (Integrations, Sync, etc.) has fewer items than Stripe — grid may look sparse. Mitigated by using a 3-column grid only for larger sections and 2-column for smaller ones.

**Verdict: Best pattern for Pilot.** Most polished, most consistent with Pilot's design language.

### 17.4 Decision + Recommendation

**Recommended: Option 3 — Stripe/Clio Settings Index Page pattern**

| Option | What ships | Second sidebar eliminated? | Gear behavior |
|---|---|---|---|
| **1 — Original §5 (Dropdown + Sidebar)** | SettingsDropdownPanel + redesigned SettingsSidebar | No | Opens dropdown panel |
| **2 — SendGrid Inline Expand** | Settings as AppSidebar accordion item | Yes | Expands inline in nav |
| **3 — Clio/Stripe Index Page** ⭐ **Recommended** | SettingsIndexPage at `/settings`; SettingsShell + SettingsSidebar deprecated | Yes | Navigates to `/settings` index |
| **4 — Hybrid** | Option 3 index page + minimal dropdown (3 quick links + "Open settings") | Yes | Opens small dropdown first |

**Option 3 delivers:** most complete UX improvement, eliminates the most code complexity (removes SettingsShell + SettingsSidebar), matches what Stripe and Clio ship at this product maturity. The `SettingsDropdownPanel` from §5 becomes unnecessary if Option 3 is chosen.

---

### 17.5 Settings Index Page Spec (`SettingsIndexPage`)

**Route:** `/settings`
**Component:** `apps/web/src/features/settings/components/SettingsIndexPage.tsx` (new)
**Layout:** Renders inside `AuthedLayout` only (no `SettingsShell` wrapper)
**Page background:** `bg-neutral-50`
**Content container:** `max-w-5xl mx-auto px-6 py-8`

#### Page Header

```
Title:    "Settings"
          text-h1 font-semibold text-neutral-900
Sub-text: "Manage your account, workspace, and integrations"
          text-sm text-neutral-500 mt-1
Margin:   mb-8
```

#### Section Header

```
Padding:  pb-2 mb-6
Border:   border-b border-neutral-200
Typo:     text-h2 font-semibold text-neutral-900
Margin-top: mt-8 (first section: mt-0)
```

#### Card Grid

```
Display:  grid grid-cols-3 gap-4 mb-10
At 1024px: grid-cols-2
At 768px:  grid-cols-1
```

#### Individual Card Spec

```
Background:    bg-white
Border:        border border-neutral-200
Border-radius: rounded-lg
Padding:       p-5
Shadow:        shadow-sm
Hover:         hover:shadow-md hover:border-brand-200 transition-all duration-150
Cursor:        cursor-pointer (full card is the link)
Focus:         focus-visible:ring-2 focus-visible:ring-brand-500
```

Card interior:
```
┌──────────────────────────────────┐
│ [Icon 20px]  Title               │  ← flex row, items-center, gap-3
│                                  │
│ Description text                 │  ← text-sm text-neutral-500 mt-2 leading-relaxed
│ (1–2 sentences max)              │
└──────────────────────────────────┘

Icon:        w-5 h-5 text-brand-500
Title:       text-sm font-semibold text-brand-600 group-hover:text-brand-700
Description: text-sm text-neutral-500 mt-2 leading-relaxed
```

#### Section 1 — Personal

| Card | Icon | Description |
|---|---|---|
| Profile & Account | `UserCircleIcon` | Your name, email, photo, and account preferences |
| Security | `ShieldCheckIcon` | Password, MFA enrollment, and active sessions |
| Notifications | `BellIcon` | Email, SMS, and in-app notification preferences |

#### Section 2 — Workspace *(RoleGate: `settings.tenant.write`)*

| Card | Icon | Description |
|---|---|---|
| Team | `UsersIcon` | Manage team members, roles, and permissions |
| Operations | `AdjustmentsHorizontalIcon` | Margin buckets, profitability rules, and field operation defaults |
| Branding | `SwatchIcon` | Email branding, SMS compliance, and 10DLC registration |
| Voice & AI | `MicrophoneIcon` | Voice capture settings and AI transcription preferences |

#### Section 3 — Integrations & System

| Card | Icon | Description | Gate |
|---|---|---|---|
| Integrations | `ArrowsRightLeftIcon` | Connect QuickBooks, calendar, and third-party apps | `integrations.manage` |
| Sync & Storage | `CloudArrowUpIcon` | Background sync, offline data limits, photos, and voice file storage | `settings.tenant.write` |
| Data & Privacy | `LockClosedIcon` | Data export, retention policies, and privacy settings | None |

#### RBAC for `tech` Role

`tech` role sees only the Personal section (Profile, Security, Notifications). Workspace and Integrations sections are hidden via `<RoleGate>`. Page heading changes to "My Settings" when only the Personal section renders.

### 17.6 Navigation After Index — Individual Settings Pages

When a user clicks a card and lands on a settings page (e.g., `/settings/team`):
- **No second sidebar** — renders in `AuthedLayout` content area only
- **Breadcrumb at top:** `Settings > Team` — "Settings" links back to `/settings` index via `SettingsBreadcrumb.tsx` (already implemented, no changes needed)
- **Content container:** `max-w-3xl px-6 py-8` (unchanged from current `SettingsShell` inner area)

Migration for each settings page: remove the `<SettingsShell>` wrapper from page components/layouts. The content renders directly.

### 17.7 SettingsShell Deprecation Impact

| Component | Action if Option 3 adopted |
|---|---|
| `SettingsShell.tsx` | **Deprecated** — remove wrapper from all settings page routes |
| `SettingsSidebar.tsx` | **Deprecated** — replaced by `SettingsIndexPage` as the navigation layer |
| `SettingsBreadcrumb.tsx` | **Keep** — still needed inside individual settings pages |
| `SettingsGearIcon.tsx` | **Keep with minor update** — keep `router.push("/settings")`; remove any active-state dropdown logic |

---

## 18. Updated Component Manifest (v2)

### 18A — If Option 1 (Dropdown + Redesigned Sidebar) is approved

| File | Status | Description |
|---|---|---|
| `apps/web/src/components/SettingsNavControl.tsx` | **New** | Wrapper owning dropdown open/close state; renders gear button + SettingsDropdownPanel |
| `apps/web/src/components/SettingsDropdownPanel.tsx` | **New** | Grouped settings quick-access dropdown panel |
| `apps/web/src/components/SettingsGearIcon.tsx` | **Delete** | Replaced by SettingsNavControl |
| `apps/web/src/app/(authed)/layout.tsx` | **Modified** | Swap SettingsGearIcon → SettingsNavControl; add relative wrapper for pill toggle |
| `apps/web/src/components/AppSidebar.tsx` | **Modified** | Width: w-fit min/max guard (§15); pill toggle button (§16A) |
| `apps/web/src/features/settings/components/SettingsSidebar.tsx` | **Modified** | Add icons, section headers, always-visible sub-items |

### 18B — If Option 3 (Settings Index Page) is approved ⭐ Recommended

| File | Status | Description |
|---|---|---|
| `apps/web/src/features/settings/components/SettingsIndexPage.tsx` | **New** | Full settings index with 3-section, 3-column icon+description card grid |
| `apps/web/src/features/settings/components/SettingsShell.tsx` | **Deprecated** | Remove wrapper from all settings page routes |
| `apps/web/src/features/settings/components/SettingsSidebar.tsx` | **Deprecated** | Navigation replaced by SettingsIndexPage |
| `apps/web/src/components/SettingsGearIcon.tsx` | **Keep — minor update** | Remove dropdown logic; retain router.push("/settings") |
| `apps/web/src/app/(authed)/layout.tsx` | **Modified** | Add relative wrapper for pill toggle button |
| `apps/web/src/components/AppSidebar.tsx` | **Modified** | Width: w-fit min/max guard (§15); pill toggle button (§16A) |
| All `/settings/*/layout.tsx` or page files using `<SettingsShell>` | **Modified** | Remove SettingsShell wrapper; render content directly |

---

## 19. Out of Scope for This Batch

- Changes to individual settings page content (Team, Operations, Notifications, etc.)
- Settings search — `SettingsSidebarSearch` behavior unchanged; if Option 3 is chosen, a global search input is added to the `SettingsIndexPage` header area (simple text filter over card titles)
- Adding Profile & Account route/page (noted as dependency; React Engineer to confirm `/settings/my-account/profile` route exists)
- Mobile settings navigation (belongs to `pilot-voice-ui-designer`)
- `SettingsBreadcrumb` label changes (already clean)

---

## 20. ProfileDropdown — Avatar Dropdown Arrow

### 20.1 Current State

The current `ProfileDropdown.tsx` renders a `w-8 h-8 rounded-full` button showing initials (e.g., "TL") in `bg-brand-600 text-white`. There is no visual indicator that the avatar is interactive or opens a menu. The only affordance is the cursor pointer and `aria-expanded`.

### 20.2 Industry Norm — To Arrow or Not?

| App | Avatar treatment | Arrow? |
|---|---|---|
| **Stripe** | Circle avatar, no arrow | No |
| **Linear** | Circle avatar, no arrow | No |
| **Vercel** | Circle avatar + tiny `▾` chevron to the right | Yes |
| **GitHub** | Circle avatar + `▾` on hover only | Hover only |
| **Notion** | Circle avatar, no arrow | No |
| **Clio** | Circle avatar with user initials/photo, no arrow | No |
| **Intercom** | Circle avatar + `▾` | Yes |

**Pattern:** More modern, minimalist B2B apps (Stripe, Linear, Notion) do NOT show an arrow. The circular avatar shape itself is a universal convention for "user menu" — most users recognize it as interactive without an indicator. Apps that show an arrow tend to be older-generation or have the avatar placed in a non-obvious location (e.g., buried in a narrow sidebar).

**For Pilot:** The avatar sits in the top-right header cluster `[Bell] [⚙] [Avatar]` — a well-established header position that users universally scan for profile controls. **No arrow is the cleaner choice.** The `hover:bg-brand-700` state already communicates interactivity through color shift.

### 20.3 Recommendation — No Arrow (Keep Current Pattern, Minor Enhancement)

Keep the avatar circle without a chevron. Instead, add two small polish improvements to make the interactive affordance clearer without adding visual noise:

1. **Hover ring:** On hover, add `ring-2 ring-brand-300 ring-offset-1` — a soft ring appears around the circle, clearly signaling "this is clickable"
2. **Cursor pointer:** Already present via browser default on `<button>`

**Updated avatar button classes:**
```
w-8 h-8 rounded-full flex items-center justify-center
text-xs font-semibold text-white
bg-brand-600
hover:bg-brand-700
hover:ring-2 hover:ring-brand-300 hover:ring-offset-1
transition-all duration-150
focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2
```

This is a minimal, clean change to `ProfileDropdown.tsx` — one class string update.

### 20.4 If Tom Prefers the Arrow Variant

If Tom decides a dropdown indicator is desirable, specify it as follows — **not** a `▾` text glyph, but a `ChevronDownIcon` from Heroicons, sized very small and placed to the right of the avatar, not inside it:

```
Layout: flex items-center gap-0.5
Avatar: w-8 h-8 rounded-full (unchanged)
Chevron: ChevronDownIcon w-3 h-3 text-neutral-400
         rotate-180 when isOpen (transition-transform duration-150)
         hidden on mobile (N/A for web)
```

This "avatar + tiny chevron" pattern is used by Vercel and is clean without being noisy. The chevron animates to `rotate-180` (pointing up) when the dropdown is open, giving visual feedback on state.

---

## 21. ProfileDropdown — User Photo Upload (Profile Avatar)

### 21.1 Feature Overview

The current avatar shows initials only. Tom asked whether a user can upload a profile photo to replace the initials. The answer is **yes — this is a standard, well-supported feature** and should be designed. Here is how it works across the stack:

**UX flow:**
1. User navigates to Profile & Account settings (already linked from `DROPDOWN_ITEMS` as `/settings/my-account/profile`)
2. On the profile page, the current avatar (initials circle) shows with an **"Upload photo"** action on hover
3. User selects an image file (jpg/png, max 2MB)
4. Image is cropped to square via a client-side crop modal
5. Uploaded to storage; user record stores a `avatar_url` string
6. All avatar renders (header `ProfileDropdown`, profile page) display the photo image instead of initials

### 21.2 Avatar Component Spec — Photo vs. Initials

The avatar must handle three visual states:

| State | Visual |
|---|---|
| No photo (default) | `bg-brand-600` circle with white initials (current) |
| Photo uploaded | `<img>` fills the circle, `object-cover object-center`, no background |
| Photo loading/error | Falls back to initials state |

**Updated avatar button interior logic:**
```tsx
{avatarUrl ? (
  <img
    src={avatarUrl}
    alt={user.displayName}
    className="w-full h-full rounded-full object-cover object-center"
  />
) : (
  <span>{initials}</span>
)}
```

When a photo is present, the button background `bg-brand-600` is still applied (fallback if image fails to load), and the `<img>` covers it.

### 21.3 Avatar Upload UI — Profile Settings Page

On the `/settings/my-account/profile` page, the avatar upload control is:

```
┌─────────────────────────────────────────────┐
│  [Avatar 64px]  ← current photo or initials │
│                                              │
│  "Upload photo"  [Change]  [Remove]          │
│  JPG or PNG, max 2MB                         │
└─────────────────────────────────────────────┘
```

**Avatar preview on profile page:**
```
Size:          w-16 h-16 (64px) — 2× the header avatar size
Border-radius: rounded-full
Border:        ring-2 ring-neutral-200
Overflow:      overflow-hidden
```

**"Change" button:**
```
Element:    <label> wrapping a hidden <input type="file" accept="image/jpeg,image/png">
Appearance: border border-neutral-300 text-neutral-700 rounded-md px-3 py-1.5 text-sm
            hover:bg-neutral-50
```

**"Remove" button:**
```
Appearance: text-sm text-fault-600 hover:text-fault-700 hover:underline
            (only visible when a photo currently exists)
Action:     Removes the uploaded photo; reverts to initials
```

**Helper text:**
```
"JPG or PNG, max 2MB"
text-xs text-neutral-500 mt-1
```

### 21.4 Crop Modal Spec

After file selection, a crop modal opens (prevents users from uploading badly-framed photos):

```
Overlay:  fixed inset-0 bg-neutral-900/50 z-50
Panel:    bg-white rounded-lg shadow-xl max-w-sm w-full mx-auto mt-16 p-6
Title:    "Crop photo" — text-h3 font-medium text-neutral-900
```

Crop area:
```
Shape:    circular crop preview (circle mask over square canvas)
Size:     240×240px preview area, centered in modal
Controls: Two buttons below crop area
          [Cancel] border border-neutral-300 text-neutral-700 rounded-md px-4 py-2 text-sm
          [Save photo] bg-brand-600 text-white rounded-md px-4 py-2 text-sm font-medium hover:bg-brand-700
```

**Implementation note for React Engineer:** Use [`react-easy-crop`](https://github.com/ValentinH/react-easy-crop) or [`react-avatar-editor`](https://github.com/mosch/react-avatar-editor) for the crop UI. The crop output should be a square canvas export at 256×256px (downsized to save storage) as a JPEG blob. Upload via `multipart/form-data` to a backend endpoint `PATCH /api/v1/users/me/avatar`. The backend stores in S3 and returns a signed URL or CDN URL stored on the user profile record.

### 21.5 Backend Note (for React Engineer to flag)

The Python backend does not currently have an avatar upload endpoint. This must be scoped with the Python Engineer as a companion task. The frontend can be built to spec with a mock `avatar_url` field on `PilotUser` in the auth context, and the real endpoint wired in when the backend is ready.

**`PilotUser` type addition required** (in `packages/ui/src/auth/types.ts` or equivalent):
```ts
avatar_url?: string | null;
```

### 21.6 Updated Component Manifest Additions (§18B addendum)

| File | Status | Description |
|---|---|---|
| `apps/web/src/components/ProfileDropdown.tsx` | **Modified** | Add hover ring to avatar button; conditionally render `<img>` when `avatar_url` present |
| `apps/web/src/features/settings/components/ProfileSettingsPage.tsx` | **Modified** | Add avatar upload control (64px preview, Change/Remove buttons, 2MB limit helper text) |
| `apps/web/src/components/AvatarCropModal.tsx` | **New** | Circular crop modal for profile photo, 240px preview, Save/Cancel actions |
| `packages/ui/src/auth/types.ts` (or equivalent PilotUser type file) | **Modified** | Add optional `avatar_url?: string \| null` to PilotUser |

---

## 22. Final Decision Summary (Tom's Confirmations Received)

| Decision | Choice |
|---|---|
| Settings navigation pattern | **Option 3 — Settings Index Page (Stripe/Clio)** ✅ Confirmed |
| AppSidebar width | **w-fit min/max guard** (§15) |
| Collapse toggle | **Option A — `«`/`»` pill** (§16A) |
| Avatar dropdown arrow | **No arrow — hover ring only** (§20.3) |
| Profile photo upload | **Yes — implement** (§21) |
| Settings dropdown panel (§5) | **Not needed** — gear navigates directly to `/settings` index |

---

## 23. Out of Scope for This Batch (superseded — see §28)

See §28 for the definitive out-of-scope list after all v2 decisions are captured.

---

## 24. Data Export — IA Clarification & ProfileDropdown Cleanup

### 24.1 Current Route Situation

From reading the existing code:

| Route | File | Status |
|---|---|---|
| `/settings/my-account/data-export` | `data-export/page.tsx` | Exists — "Download a copy of your Pilot data" |
| `/settings/data-privacy` | `data-privacy/page.tsx` | Exists — already links to data-export via an "Export Your Data" card |

**Finding:** `DataPrivacyPage`/settings/data-privacy/page.tsx) already contains an "Export Your Data" card that navigates to `/settings/my-account/data-export`. Data Export is correctly surfaced inside the Data & Privacy settings page — exactly as Tom wants. No change needed there.

**Also confirmed:** The current `ProfileDropdown` `DROPDOWN_ITEMS` does not include a Data Export link. Tom's instruction is an IA design principle for the future, not a current bug fix.

### 24.2 ProfileDropdown Items — Final Approved List

Tom confirmed: keep the profile dropdown to **user-scoped settings only**. The current four items include two tenant/billing items (Subscription, Payment Method) that should not be in a personal user menu.

| Label | Route | Keep? | Reason |
|---|---|---|---|
| Account → My Profile | `/settings/my-account/profile` | ✅ Keep | Personal user setting |
| Subscription | `/settings/billing` | ❌ Remove | Tenant/workspace setting — belongs in Settings Index |
| Payment Method | `/settings/billing/payment-method` | ❌ Remove | Tenant/workspace setting — belongs in Settings Index |
| Security | `/settings/my-account/security` | ✅ Keep | Personal user setting |

Subscription and Payment Method will be accessible via the Settings Index Page → a future Billing card in the Workspace section.

### 24.3 Updated ProfileDropdown Panel Spec

```
┌────────────────────────────────────┐
│  displayName (text-xs font-semibold text-neutral-900, truncate)  │
│  email     (text-xs text-neutral-500, truncate)                  │
│ ─────────────────────────────────  │  border-b border-neutral-100
│   My Profile                       │  → /settings/my-account/profile
│   Security                         │  → /settings/my-account/security
│ ─────────────────────────────────  │  border-t border-neutral-100
│   Sign Out                         │  text-fault-600 font-medium
└────────────────────────────────────┘
```

All other visual specs (width `min-w-[192px]`, position, shadow, z-index, hover states) unchanged from existing implementation.

### 24.4 Code Change Required

`apps/web/src/components/ProfileDropdown.tsx` — update `DROPDOWN_ITEMS`:

```ts
// Before (4 items):
{ label: "Account", href: "/settings/my-account/profile" },
{ label: "Subscription", href: "/settings/billing" },
{ label: "Payment Method", href: "/settings/billing/payment-method" },
{ label: "Security", href: "/settings/my-account/security" },

// After (2 items):
{ label: "My Profile", href: "/settings/my-account/profile" },
{ label: "Security", href: "/settings/my-account/security" },
```

---

## 25. Notifications — Personal vs. Tenant Architecture

### 25.1 Current State — What Exists

Reading `notifications/preferences/page.tsx`:

- **Page heading:** "Choose how you'd like to be notified about activity in Pilot." — **explicitly personal scope**
- **Hook:** `useNotificationPreferences()` — fetches preferences for the logged-in user
- **Code comment (line 9):** `"Owner can also switch to /settings/notifications/tenant-defaults for team-level prefs."` — this route **does not exist yet** (confirmed: no `tenant-defaults/` directory under `notifications/` in the file listing)
- The `NotificationPreferenceMatrix` renders an 8-category × 3-channel (Email / SMS / In-App) grid

**Answer to Tom's question:** The notifications page is **personal/user-scoped only** for all roles. Each user (owner, operator, office_staff, tech) sets their own notification preferences independently. Tenant-level defaults are planned in the codebase comment but not yet built.

### 25.2 How Owner Sets Tenant Defaults

The need Tom is asking about: *"When the owner logs in, how do they set the default tenant-level notification settings versus their own personal settings?"*

The architectural answer is a **scope switcher tab strip** at the top of the Notifications preferences page — visible only to owner/operator roles (`<RoleGate permission="settings.tenant.write">`):

```
My preferences  |  Team defaults          ← tab strip (owner/operator only)
─────────────────────────────────────────
[8×3 NotificationPreferenceMatrix]        ← content swaps based on active tab
```

Non-owner users see no tab strip — the page renders the personal matrix only, exactly as today.

### 25.3 Scope Switcher Tab Strip Spec

```
Container:     flex gap-1 bg-neutral-100 rounded-md p-1 w-fit mb-6
Tab element:   <button> or <Link>
Tab size:      px-4 py-1.5 text-sm rounded-sm
Active tab:    bg-white shadow-sm text-neutral-900 font-medium transition-all duration-100
Inactive tab:  text-neutral-500 hover:text-neutral-700 hover:bg-neutral-50
RBAC wrapper:  <RoleGate permission="settings.tenant.write"> wraps the entire tab strip
```

**Tab 1 — "My preferences"** (active by default for all users):
- Route: `/settings/notifications/preferences`
- Renders `useNotificationPreferences()` matrix (current behavior, unchanged)

**Tab 2 — "Team defaults"** (owner/operator only):
- Route: `/settings/notifications/tenant-defaults`
- Renders a separate `NotificationPreferenceMatrix` fed by `useTeamNotificationDefaults()`
- Sub-label under title: "These preferences apply to new team members. Each user can override their own settings."

### 25.4 Team Defaults Page Spec

**Route:** `/settings/notifications/tenant-defaults` (new page — must be created)
**RBAC:** `<RoleGate permission="settings.tenant.write">` on the route; redirect non-owner to `/settings/notifications/preferences`

```
Page title:    "Team notification defaults"
               text-h2 font-semibold text-neutral-900

Sub-text:      "These preferences apply to new team members.
                Each user can override their own notification settings."
               text-sm text-neutral-500 mt-1 mb-6

Scope tabs:    [My preferences]  [Team defaults ← active]
               Same tab strip component (§25.3)

Matrix:        <NotificationPreferenceMatrix> — same component,
               different data source: useTeamNotificationDefaults()
               isPending prop from mutation state

Footer action: [Reset all to system defaults]
               text-sm text-fault-600 hover:text-fault-700 underline-on-hover
               → triggers ConfirmDialog before resetting
```

**`ConfirmDialog` for reset:**
```
Title:   "Reset to system defaults?"
Body:    "This will reset the team's default notification preferences to
          Pilot's recommended settings. Users who have already set their
          own preferences will not be affected."
Cancel:  border border-neutral-300 (standard secondary button)
Confirm: bg-fault-600 text-white hover:bg-fault-700 (destructive)
```

### 25.5 New Backend Dependency

`useTeamNotificationDefaults()` hook requires a Python Engineer companion task:
- `GET /api/v1/tenants/{id}/notification-defaults` — fetch tenant-level defaults
- `PATCH /api/v1/tenants/{id}/notification-defaults` — save changes
- `DELETE /api/v1/tenants/{id}/notification-defaults` — reset to system defaults

The frontend hook can be scaffolded with mocked data until the backend is ready.

### 25.6 Settings Index Page — Notifications Card (Updated Description)

Update the Notifications card description in the Settings Index (§17.5, Personal section):

```
Old: "Email, SMS, and in-app notification preferences"
New: "Manage your personal notification preferences for email, SMS, and in-app alerts"
```

Owner/operator will discover the Team defaults tab once they land on `/settings/notifications/preferences`.

### 25.7 File Changes for §24–§25

| File | Status | Description |
|---|---|---|
| `apps/web/src/components/ProfileDropdown.tsx` | **Modified** | DROPDOWN_ITEMS: 4 → 2 items (My Profile, Security); label "Account" → "My Profile"; remove Subscription + Payment Method |
| `apps/web/src/app/(authed)/settings/notifications/preferences/page.tsx` | **Modified** | Add scope switcher tab strip (RoleGate: settings.tenant.write); tabs link between `/preferences` and `/tenant-defaults` |
| `apps/web/src/app/(authed)/settings/notifications/tenant-defaults/page.tsx` | **New** | Tenant notification defaults page; same NotificationPreferenceMatrix; RoleGate protected; reset-to-defaults action |
| `apps/web/src/features/notification-preferences/hooks/useTeamNotificationDefaults.ts` | **New** | Hook for tenant-level notification defaults (Python Engineer backend dependency) |

---

## 26. Final Decision Registry

| # | Decision | Choice | Spec Section |
|---|---|---|---|
| 1 | Settings navigation pattern | **Option 3 — Stripe/Clio Settings Index Page** | §17 |
| 2 | AppSidebar expanded width | **w-fit min/max guard (160–200px)** | §15 |
| 3 | Collapse toggle design | **Option A — `«`/`»` pill at top-right sidebar border** | §16A |
| 4 | Avatar dropdown arrow | **No arrow — hover ring (`ring-2 ring-brand-300`)** | §20.3 |
| 5 | Profile photo upload | **Yes — implement** | §21 |
| 6 | Settings dropdown panel | **Not built** — gear navigates to `/settings` index directly | §17.4 |
| 7 | ProfileDropdown items | **My Profile + Security only** (Subscription/Payment Method removed) | §24.2 |
| 8 | Data Export in dropdown | **No** — accessible via Data & Privacy settings page only | §24.1 |
| 9 | Notifications scope | **Personal (existing) + Team Defaults tab (new, owner/operator only)** | §25 |

---

## 27. Updated Complete Component Manifest

| File | Status | Description |
|---|---|---|
| `apps/web/src/features/settings/components/SettingsIndexPage.tsx` | **New** | Full settings index — 3-section, 3-column icon+description card grid (§17.5) |
| `apps/web/src/features/settings/components/SettingsShell.tsx` | **Deprecated** | Remove `<SettingsShell>` wrapper from all settings page routes |
| `apps/web/src/features/settings/components/SettingsSidebar.tsx` | **Deprecated** | Navigation replaced by SettingsIndexPage |
| `apps/web/src/components/SettingsGearIcon.tsx` | **No change** | Already calls router.push("/settings"); no modifications needed |
| `apps/web/src/app/(authed)/layout.tsx` | **Modified** | Add `relative` wrapper div around AppSidebar for pill toggle button |
| `apps/web/src/components/AppSidebar.tsx` | **Modified** | Width: `w-fit min-w-[160px] max-w-[200px]` (§15); pill `«`/`»` toggle replaces bottom Collapse button (§16A) |
| All `/settings/*/layout.tsx` or page files using `<SettingsShell>` | **Modified** | Remove SettingsShell wrapper; render content directly inside AuthedLayout |
| `apps/web/src/components/ProfileDropdown.tsx` | **Modified** | Trim to 2 items (My Profile, Security); hover ring on avatar (§20.3, §24.4) |
| `apps/web/src/features/settings/components/ProfileSettingsPage.tsx` | **Modified** | Add 64px avatar upload control, Change/Remove buttons, 2MB helper text (§21.3) |
| `apps/web/src/components/AvatarCropModal.tsx` | **New** | Circular crop modal — 240px preview, Save/Cancel actions (§21.4) |
| `packages/ui/src/auth/types.ts` (PilotUser) | **Modified** | Add `avatar_url?: string \| null` (§21.5) |
| `apps/web/src/app/(authed)/settings/notifications/preferences/page.tsx` | **Modified** | Add scope-switcher tab strip (RoleGate: settings.tenant.write) (§25.3) |
| `apps/web/src/app/(authed)/settings/notifications/tenant-defaults/page.tsx` | **New** | Tenant notification defaults — NotificationPreferenceMatrix + reset action (§25.4) |
| `apps/web/src/features/notification-preferences/hooks/useTeamNotificationDefaults.ts` | **New** | Hook for tenant-level notification defaults; Python Engineer backend dependency (§25.5) |

---

## 28. Out of Scope for This Batch (Definitive)

- Individual settings page content changes (Team, Operations, Voice & AI, etc.)
- Backend avatar upload endpoint — Python Engineer companion task (`PATCH /api/v1/users/me/avatar`)
- Backend tenant notification defaults endpoints — Python Engineer companion task
- Billing card in the Settings Index — future batch (Subscription/Payment Method accessible from Settings Index once card is built)
- Mobile settings/profile UI — belongs to `pilot-voice-ui-designer`
- `SettingsBreadcrumb` label content — already clean, no changes

---

---

## 29. Decision Revision — Notifications IA (Supersedes §25.2–§25.4)

Tom's confirmed decision changes the notifications architecture. This section supersedes §25.2–§25.4 (the scope-switcher tab approach is **not built**).

### 29.1 Final Notifications Architecture

| Surface | Route | Scope | Who sees it |
|---|---|---|---|
| ProfileDropdown → Notifications | `/settings/notifications/preferences` | **Personal** (this user only) | All authenticated roles |
| Settings Index → Notifications card | `/settings/notifications/tenant-defaults` | **Tenant defaults** | Owner only (`settings.tenant.write`) |

**Key principle:** The two surfaces are completely separate — no tab strip, no scope switcher. Personal preferences are in the profile dropdown. Tenant defaults are in the Settings Index, owner-only.

### 29.2 Updated ProfileDropdown Items (Supersedes §24.2–§24.3)

Adding "Notifications" as the third personal item:

| Label | Route | Notes |
|---|---|---|
| My Profile | `/settings/my-account/profile` | Personal |
| Security | `/settings/my-account/security` | Personal |
| Notifications | `/settings/notifications/preferences` | Personal — links to the existing preferences page |
| *(divider)* | — | |
| Sign Out | — | |

```
┌────────────────────────────────────┐
│  displayName (text-xs font-semibold)             │
│  email     (text-xs text-neutral-500)            │
│ ──────────────────────────────────  │  border-b
│   My Profile                        │  → /settings/my-account/profile
│   Security                          │  → /settings/my-account/security
│   Notifications                     │  → /settings/notifications/preferences
│ ──────────────────────────────────  │  border-t
│   Sign Out                          │  text-fault-600 font-medium
└────────────────────────────────────┘
```

Code change in `ProfileDropdown.tsx`:
```ts
const DROPDOWN_ITEMS = [
  { label: "My Profile", href: "/settings/my-account/profile" },
  { label: "Security", href: "/settings/my-account/security" },
  { label: "Notifications", href: "/settings/notifications/preferences" },
] as const;
```

### 29.3 Settings Index Page — Notifications Card (Supersedes §17.5, §25.6)

The Notifications card in the Settings Index **Personal section is removed**. Instead, Notifications moves to the **Workspace section** and is **owner-only**:

| Section | Card | Icon | Description | RBAC |
|---|---|---|---|---|
| Workspace | Notifications | `BellIcon` | Set default notification preferences for your team | `settings.tenant.write` (owner only for now) |

This card navigates to `/settings/notifications/tenant-defaults` (not `/settings/notifications/preferences`).

**Updated Settings Index Section 2 — Workspace** *(RoleGate: `settings.tenant.write`)*:

| Card | Icon | Description |
|---|---|---|
| Team | `UsersIcon` | Manage team members, roles, and permissions |
| Operations | `AdjustmentsHorizontalIcon` | Margin buckets, profitability rules, and field operation defaults |
| Notifications | `BellIcon` | Set default notification preferences for new team members |
| Branding | `SwatchIcon` | Email branding, SMS compliance, and 10DLC registration |
| Voice & AI | `MicrophoneIcon` | Voice capture settings and AI transcription preferences |

**Personal section** — Notifications card **removed** (personal notifications are reached via the ProfileDropdown):

| Card | Icon | Description |
|---|---|---|
| Profile & Account | `UserCircleIcon` | Your name, email, photo, and account preferences |
| Security | `ShieldCheckIcon` | Password, MFA enrollment, and active sessions |

### 29.4 Tenant Defaults Page Spec (Updated — No Tab Strip)

**Route:** `/settings/notifications/tenant-defaults`
**RBAC:** `<RoleGate permission="settings.tenant.write">` — redirect non-owner to `/settings/notifications/preferences`

```
Page title:    "Team notification defaults"
               text-h2 font-semibold text-neutral-900

Sub-text:      "Set the default notification preferences for new team members.
                Individual users can override their own settings from
                their profile menu."
               text-sm text-neutral-500 mt-1 mb-6

Content:       <NotificationPreferenceMatrix>
               data source: useTeamNotificationDefaults()

Footer:        [Reset all to system defaults]
               text-sm text-fault-600 hover:text-fault-700
               → ConfirmDialog before resetting
```

**No tab strip.** This page stands alone as a tenant-admin settings page. There is no "My preferences" tab here — owners who want their personal preferences use the ProfileDropdown → Notifications link.

### 29.5 Personal Notifications Page — No Changes

`/settings/notifications/preferences` remains exactly as-is — no scope switcher tabs added. The page continues to show the personal `NotificationPreferenceMatrix` for the logged-in user. All roles (owner, operator, office_staff, tech) can reach it via the ProfileDropdown.

### 29.6 Revised §26 Decision Registry (Addendum)

| # | Decision | Choice |
|---|---|---|
| 9 (revised) | Notifications personal access | Via **ProfileDropdown → "Notifications"** → `/settings/notifications/preferences` |
| 10 (revised) | Notifications tenant defaults | Via **Settings Index → Notifications card (Workspace section, owner only)** → `/settings/notifications/tenant-defaults` |
| 11 | Scope switcher tab strip | **Not built** — two completely separate pages, no shared UI |

### 29.7 Final Updated Component Manifest (Supersedes §27)

| File | Status | Description |
|---|---|---|
| `apps/web/src/features/settings/components/SettingsIndexPage.tsx` | **New** | Full settings index — 3-section card grid; Notifications card in Workspace (owner only) |
| `apps/web/src/features/settings/components/SettingsShell.tsx` | **Deprecated** | Remove from all settings page routes |
| `apps/web/src/features/settings/components/SettingsSidebar.tsx` | **Deprecated** | Replaced by SettingsIndexPage |
| `apps/web/src/components/SettingsGearIcon.tsx` | **No change** | Already calls router.push("/settings"); no modifications needed |
| `apps/web/src/app/(authed)/layout.tsx` | **Modified** | Add `relative` wrapper div around AppSidebar for pill toggle |
| `apps/web/src/components/AppSidebar.tsx` | **Modified** | Width: `w-fit min-w-[160px] max-w-[200px]`; pill `«`/`»` toggle replaces bottom Collapse button |
| All settings page routes using `<SettingsShell>` | **Modified** | Remove SettingsShell wrapper |
| `apps/web/src/components/ProfileDropdown.tsx` | **Modified** | DROPDOWN_ITEMS: My Profile + Security + Notifications (3 items); remove Subscription + Payment Method; add hover ring on avatar |
| `apps/web/src/features/settings/components/ProfileSettingsPage.tsx` | **Modified** | Add 64px avatar upload control, Change/Remove, 2MB helper |
| `apps/web/src/components/AvatarCropModal.tsx` | **New** | Circular crop modal — 240px preview, Save/Cancel |
| `packages/ui/src/auth/types.ts` (PilotUser) | **Modified** | Add `avatar_url?: string \| null` |
| `apps/web/src/app/(authed)/settings/notifications/preferences/page.tsx` | **No change** | Personal prefs page unchanged; reached via ProfileDropdown |
| `apps/web/src/app/(authed)/settings/notifications/tenant-defaults/page.tsx` | **New** | Tenant notification defaults — standalone owner-only page; no tab strip |
| `apps/web/src/features/notification-preferences/hooks/useTeamNotificationDefaults.ts` | **New** | Hook for tenant-level notification defaults; Python Engineer backend dependency |

---

## 30. Out of Scope for This Batch (Definitive)

- Individual settings page content changes (Team, Operations, Voice & AI, etc.)
- Backend avatar upload endpoint — Python Engineer companion task (`PATCH /api/v1/users/me/avatar`)
- Backend tenant notification defaults endpoints — Python Engineer companion task (`GET/PATCH/DELETE /api/v1/tenants/{id}/notification-defaults`)
- Billing card in Settings Index (Subscription/Payment Method) — future batch
- Mobile settings/profile UI — belongs to `pilot-voice-ui-designer`
- `SettingsBreadcrumb` label content — no changes

---

*This spec is ready for Tom's review. Implementation starts only after approval.*
