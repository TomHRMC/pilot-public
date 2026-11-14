# Design Prompt: UI-FIX-2E — Navigation Redesign (UI Designer Phase)

**Mode**: Pilot Web UI Designer  
**Batch**: UI-FIX-2E (Design Phase)  
**Source decisions**: `dev-docs/architecture-design/batch-designs/ui-fix-2-decisions.md § FIX-019`  
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-ui-fix-2e-design.md`  
**Estimated session**: 2 hours  
**Platform**: Web (`apps/web`) — desktop-first design, minimum viewport 1280px  
**Output**: A detailed design spec document at `dev-docs/architecture-design/batch-designs/batch-ui-fix-2e-ui-design-spec.md`  
**Next step**: Tom reviews and approves the design spec. React Engineer implements only after approval.

---

## ⚠️ MANDATORY STOP: Read These First

Before producing any design, read:

- **`dev-docs/architecture-design/batch-designs/batch-ui-fix-2e-design.md`** — all sections A–G. This is the Architect's engineering blueprint that the design spec must align with.
- **`dev-docs/architecture-design/batch-designs/ui-fix-2-decisions.md § FIX-019`** — the full FIX-019 section with all design requirements.

Also read these source files to understand what currently exists before designing:

```
frontend/apps/web/src/components/AppSidebar.tsx
  ← Current sidebar structure, nav items, emoji icons

frontend/apps/web/src/app/(authed)/layout.tsx
  ← Current header structure (h-12, right-justified NotificationBell only)

frontend/apps/web/src/features/settings/components/SettingsSidebar.tsx
  ← Current Settings sidebar order and groups
```

And view the brand assets directory listing:
```
frontend/apps/marketing/public/brand/
  ← logo-primary.jpg/.svg (full wordmark)
  ← logo-icon.jpg/.svg (P icon mark for collapsed state)
  ← logo-wordmark.jpg/.svg (wordmark variant)
```

---

## Background: What This Batch Redesigns

The current web app navigation has these problems:
1. **Left sidebar**: Fixed width, no collapse, emoji icons (unprofessional), "Pilot for Trades" text block takes up space, wrong nav order (Jobs before Customers), dead items (Operations, Sync, Notifications, Settings)
2. **Top header**: Only a notification bell on the right, no logo, no profile access, no settings shortcut
3. **Sign Out**: Awkwardly placed on the Dashboard page, not in the nav shell
4. **Settings sidebar**: `My Account` group at top with Profile/Security, `Billing` standalone, `Communications` group not labelled for its real purpose (Branding), `Security & MFA` unnecessarily verbose

This batch redesigns all of these surfaces into a modern, clean SaaS navigation pattern.

---

## Design Requirements

### Requirement 1 — Left Sidebar: Collapsible

**Expanded state** (default):
- Width: 256px
- Shows: icon + label for each nav item
- Logo/wordmark NOT shown (moved to header)
- Top section: just below the header bar, no wordmark block
- Nav item order (top to bottom): Dashboard, Schedule, Customers, Quotes, Jobs, Invoices, Comms, Catalog, Reports
- Active item: highlighted using `bg-brand-50`, `text-brand-700`, left border indicator or background
- Hover state: `hover:bg-neutral-100`
- Bottom: toggle button to collapse

**Collapsed state** (user-triggered):
- Width: 64px
- Shows: icon only (centered), no labels
- Tooltip on hover showing the label text
- Toggle button visible to expand
- Logo in header changes from full wordmark to icon-only mark when sidebar is collapsed

**Toggle button design**:
- Small button anchored to the right edge of the sidebar
- Chevron icon: `‹` when expanded (click = collapse), `›` when collapsed (click = expand)
- Subtle — doesn't dominate the sidebar
- Position: vertically centered, or pinned to bottom of sidebar

**Icons**: Design must use proper SVG icons — NOT emoji. Reference Heroicons 2.0 (solid or outline, your choice — pick one set and be consistent):
- Dashboard → `Squares2X2Icon` or `HomeIcon`
- Schedule → `CalendarDaysIcon`
- Customers → `UsersIcon`
- Quotes → `DocumentTextIcon`
- Jobs → `WrenchScrewdriverIcon`
- Invoices → `ReceiptPercentIcon` or `BanknotesIcon`
- Comms → `ChatBubbleLeftRightIcon`
- Catalog → `CubeIcon` or `Squares2X2Icon`
- Reports → `ChartBarIcon`

---

### Requirement 2 — Top Header Bar

**Current**: `h-12`, right-justified, `NotificationBell` only.

**New layout** (all in the same h-12 bar):

```
LEFT                                    RIGHT
[Pilot Logo ───────────────────]  [🔔] [⚙] [○]
                                  Bell  Gear Profile
```

**Logo (left)**:
- When sidebar is expanded: `logo-primary.jpg` (full wordmark) — approx `width: 120px, height: 32px`
- When sidebar is collapsed: `logo-icon.jpg` (P icon mark) — approx `width: 32px, height: 32px`
- The logo width change should feel like a natural extension of the sidebar collapse animation
- Logo is a clickable link to `/dashboard` (acts as "home" button)
- Use `<Image>` with proper `alt="Pilot for Trades"` text

**Right-side icons** (left to right): `NotificationBell` | Settings gear | Profile avatar

**Spacing between right icons**: Consistent `gap-2` or `gap-3`. Vertically centered in the header.

---

### Requirement 3 — Settings Gear Icon

- Standard gear SVG — use `Cog6ToothIcon` from Heroicons (or `CogIcon` if 6-tooth is unavailable)
- Icon size: 20px (consistent with notification bell)
- Click action: navigates to `/settings`
- **Active state**: When `pathname.startsWith("/settings")`, show a subtle background highlight (`bg-brand-50`, icon `text-brand-600`) — same visual pattern as the active sidebar item
- **Hover tooltip**: "Settings" — appears below the icon on hover
- No dropdown — direct navigation

---

### Requirement 4 — Profile Avatar + Dropdown

**Avatar button** (rightmost in header):
- Circular avatar, ~32px diameter
- Shows user's initials (first letter of first name + first letter of last name, or first 2 letters of email)
- Background color: user's `display_color` if set, else `bg-brand-600`
- Text: white, small font weight semibold
- Hover tooltip: "Profile"
- Click: opens dropdown below

**Dropdown menu** (opened by clicking avatar):
- Opens below-right of avatar
- Shadow: `shadow-lg`, border: `border border-neutral-200`
- Background: `bg-white`
- Border-radius: `rounded-lg`
- Width: ~200px

```
┌─────────────────────────┐
│  Account                │  → /settings/my-account/profile
│  Subscription           │  → /settings/billing
│  Payment Method         │  → /settings/billing/payment-method
│  Security               │  → /settings/my-account/security
├─────────────────────────┤
│  Sign Out               │  calls logout()  (text-fault-600)
└─────────────────────────┘
```

- Each menu item: `px-4 py-2.5`, `text-sm`, hover `bg-neutral-50`
- Divider between Security and Sign Out: `border-t border-neutral-100`
- Sign Out: `text-fault-600` (red), hover `bg-fault-50`
- Dropdown dismisses on: outside-click, Escape key, item selection

---

### Requirement 5 — Remove Sign Out from Dashboard

The `DashboardPage` currently has a "Sign Out" button. It must be removed — Sign Out is now exclusively in the Profile dropdown.

---

### Requirement 6 — Settings Sidebar Reorder

The Settings sidebar (`SettingsSidebar.tsx`) must be reordered and renamed:

**New order** (top to bottom):
```
Team
Operations
Notifications
Sync & Storage
Integrations
Branding               ← renamed from "Communications"
Voice & AI
Security               ← renamed from "Security & MFA"
Data & Privacy
```

**Removed**: `My Account` group (Profile + Security moved to Profile dropdown). `Billing` removed (Subscription + Payment Method now in Profile dropdown — linked from the Settings gear page optionally).

---

## Design Token Constraints

ALL colors must use the existing `pilotPreset` design token set. Do NOT hardcode any hex colors. Reference tokens from the current codebase:

| Use | Token |
|---|---|
| Active sidebar item background | `bg-brand-50` |
| Active sidebar item text | `text-brand-700` |
| Active sidebar left border | `border-brand-600` |
| Hover item background | `hover:bg-neutral-100` |
| Neutral icon/text | `text-neutral-600` |
| Main background | `bg-white` |
| Border | `border-neutral-200` |
| Sign Out text | `text-fault-600` |
| Sign Out hover | `hover:bg-fault-50` |
| Profile avatar background (fallback) | `bg-brand-600` |

---

## Output: Design Spec Document

Produce a design spec document at:

**`dev-docs/architecture-design/batch-designs/batch-ui-fix-2e-ui-design-spec.md`**

The design spec must include:

### Required sections:

1. **Overview** — brief description of the redesign goal and approach

2. **Sidebar — Expanded State**
   - Exact dimensions (width, item height, icon size, padding)
   - Icon set decision (Heroicons solid or outline, which specific icons)
   - Active state visual (background, border, text color — in tokens)
   - Hover state (token)
   - Toggle button position, size, icon choice
   - Nav item order with icon mapping

3. **Sidebar — Collapsed State**
   - Exact width (64px)
   - Icon position (centered)
   - Tooltip behavior (which mechanism: title attribute or Radix Tooltip)
   - Toggle button position when collapsed
   - Logo behavior in header (switches to icon-only)

4. **Top Header Bar**
   - Exact height (h-12 = 48px — keep or change with justification)
   - Logo component: which asset file, dimensions, `<Image>` props
   - Logo collapsed-state variant
   - Right-side icon order and spacing
   - Header background, border

5. **Settings Gear Icon**
   - Icon choice (specific Heroicon name)
   - Size
   - Active state (when pathname.startsWith("/settings"))
   - Tooltip

6. **Profile Avatar**
   - Size (32px circle)
   - Avatar initials computation rule
   - Color logic (display_color → brand-600 fallback)
   - Hover state + tooltip

7. **Profile Dropdown**
   - Exact pixel/token dimensions
   - Item list and routes
   - Divider placement
   - Sign Out styling
   - Dismiss behavior (outside-click, Escape)
   - z-index (must be above sidebar and content)

8. **Settings Sidebar**
   - New ordered item list with labels and routes
   - Removed items noted

9. **Animations/Transitions**
   - Sidebar collapse: CSS transition spec (property, duration, easing)
   - Dropdown open/close: fade-in or none

10. **Component Manifest** — list of every new or modified component the React Engineer must create/update, with file paths

11. **Implementation Notes** — anything the React Engineer needs to know that isn't obvious from the spec (e.g., "verify Heroicons is in package.json before using", "localStorage key: `pilot.sidebar.collapsed`")

---

## Quality Bar

This design spec will be given directly to a React Engineer to implement. It must be:
- **Pixel-precise on dimensions** — no "approximately" — specific numbers for widths, heights, padding, font sizes
- **Token-only colors** — no hex codes
- **Component-precise** — exactly which component to create/modify with the exact file path
- **Modern and clean** — matches the quality of current best-in-class SaaS apps (Linear, Vercel dashboard, Stripe dashboard)
- **Consistent with existing Pilot design system** — respects current token usage patterns in the existing components

After completing the design spec, notify Tom that it is ready for review before any implementation begins.
