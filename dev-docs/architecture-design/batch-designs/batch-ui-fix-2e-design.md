# Batch UI-FIX-2E Design — Navigation Redesign (Design Phase)

**Batch**: UI-FIX-2E  
**Fix**: FIX-019  
**Phase**: Design only — UI Designer produces spec; React Engineer implements after Tom approves  
**Type**: Design → Frontend  
**Estimated effort**: ~2h UI Designer (design spec) + ~6–8h React Engineer (implementation, separate batch)  
**Dependencies**: None for design phase; React Engineer implementation depends on Tom approving the design spec  
**Source decisions**: `ui-fix-2-decisions.md § FIX-019`

---

## A. Input Read Summary

| Input | Key Finding |
|---|---|
| `ui-fix-2-decisions.md` FIX-019 | Full nav redesign spec: collapsible sidebar, logo in header, Profile dropdown, Settings gear, nav reorder, Settings sidebar reorder |
| `AppSidebar.tsx` | 13 nav items with emoji icons; fixed 224px width; "Pilot for Trades" wordmark block; no collapse |
| `layout.tsx` | Header is `h-12`, right-justified only with `NotificationBell`; no logo; no profile icon |
| `SettingsSidebar.tsx` | `My Account` group at top; `Billing` standalone; `Security & MFA` (should become `Security`); `Communications` (should become `Branding`) |
| `dashboard/page.tsx` | Contains a Sign Out button — must be removed in implementation |
| Marketing brand assets | `logo-primary.jpg/.svg` (full wordmark), `logo-icon.jpg/.svg` (icon mark) in `frontend/apps/marketing/public/brand/` |

---

## B. Migration Plan

No DB migration. No API changes.

**Asset copy required (implementation phase)**: Marketing brand assets (`logo-primary.jpg`, `logo-primary.svg`, `logo-icon.jpg`, `logo-icon.svg`) must be copied from `frontend/apps/marketing/public/brand/` to `frontend/apps/web/public/brand/` during implementation. The UI Designer must reference these specific assets in the design spec.

---

## C. Execution Order (Design Phase)

| # | Task | Owner |
|---|---|---|
| 1 | Read all current source files listed in design spec | UI Designer |
| 2 | Design expanded sidebar state (icons + labels, 256px) | UI Designer |
| 3 | Design collapsed sidebar state (icons only, 64px, tooltips) | UI Designer |
| 4 | Design toggle button for collapse/expand | UI Designer |
| 5 | Design top header bar (logo left, NotificationBell + Settings gear + Profile avatar right) | UI Designer |
| 6 | Design Profile dropdown (Account, Subscription, Payment Method, Security, Sign Out) | UI Designer |
| 7 | Design Settings gear active state | UI Designer |
| 8 | Design new Settings sidebar order | UI Designer |
| 9 | Tom reviews and approves design spec | Tom |
| 10 | React Engineer implements (separate batch after approval) | React Engineer |

---

## D. New API Endpoints

None in this batch. The Profile dropdown items navigate to existing routes.

**Note**: `GET /api/v1/users/me/profile` already returns `first_name`, `last_name`, `display_color` for the avatar initials. No new endpoint needed.

---

## E. Pattern Reuse Decisions

- **`pilotPreset` token set only** — no hardcoded colors in the design spec. All colors must reference existing tokens (`brand-600`, `neutral-200`, `fault-600`, etc.)
- **SVG icons** — replace emoji with proper SVGs. Heroicons is the recommended set (standard in Next.js stacks; check `package.json` first). Icon mark: `logo-icon.jpg` for collapsed sidebar.
- **Radix UI `Tooltip`** — check if already in `package.json`; if not, use `title` attribute for collapsed sidebar tooltips
- **`localStorage` persistence** — sidebar collapsed state stored as `pilot.sidebar.collapsed` key
- **`useAuth().user`** — provides `first_name`, `last_name`, `display_color` for avatar initials

---

## F. Shared Module Interfaces (for implementation reference)

### New components the React Engineer will create (after design approval):

| Component | Location | Purpose |
|---|---|---|
| `AppSidebar` (rewrite) | `apps/web/src/components/AppSidebar.tsx` | Collapsible sidebar with SVG icons, localStorage, no wordmark |
| `ProfileDropdown` | `apps/web/src/components/ProfileDropdown.tsx` | Avatar + dropdown menu with Account/Subscription/Payment Method/Security/Sign Out |
| `SettingsGearIcon` | `apps/web/src/components/SettingsGearIcon.tsx` | Gear SVG, active state, tooltip, navigates to /settings |

### `layout.tsx` header change (for implementation reference):

**Before**:
```
<header className="h-12 bg-white border-b border-neutral-200 flex items-center justify-end px-4">
  <NotificationBell />
</header>
```

**After** (approximate — exact layout determined by design spec):
```
<header className="h-12 bg-white border-b border-neutral-200 flex items-center justify-between px-4">
  {/* Left: Logo */}
  <Link href="/dashboard"><Image src="/brand/logo-primary.jpg" ... /></Link>

  {/* Right: NotificationBell | Settings gear | Profile */}
  <div className="flex items-center gap-2">
    <NotificationBell />
    <SettingsGearIcon />
    <ProfileDropdown />
  </div>
</header>
```

### Profile dropdown items:

| Label | Route/Action | Style |
|---|---|---|
| Account | `/settings/my-account/profile` | Normal |
| Subscription | `/settings/billing` | Normal |
| Payment Method | `/settings/billing/payment-method` | Normal |
| Security | `/settings/my-account/security` | Normal |
| — divider — | — | Divider |
| Sign Out | `useLogout().logout()` | `text-fault-600` |

### New left nav order:

```
Dashboard    → /dashboard      icon: grid/home SVG
Schedule     → /schedule       icon: calendar SVG
Customers    → /customers      icon: users SVG
Quotes       → /quotes         icon: document SVG
Jobs         → /jobs           icon: wrench SVG
Invoices     → /invoices       icon: receipt SVG
Comms        → /comms          icon: chat-bubble SVG
Catalog      → /catalog        icon: box SVG       (RBAC: catalog.view)
Reports      → /reports        icon: chart-bar SVG (RBAC: reports.view)
```

### New Settings sidebar order:

```
Team                  → /settings/team
Operations            → /settings/operations
Notifications         → /settings/notifications/preferences
Sync & Storage        → /settings/sync-storage
Integrations          → /settings/integrations
Branding              → /settings/communications       ← renamed from "Communications"
Voice & AI            → /settings/voice-ai
Security              → /settings/security             ← renamed from "Security & MFA"
Data & Privacy        → /settings/data-privacy
```

**Removed from Settings sidebar**: `My Account` group (Profile + Security moved to Profile dropdown); `Billing` removed (Subscription + Payment Method in Profile dropdown).

---

## G. Open Questions Resolved

| Question | Resolution |
|---|---|
| Which logo for collapsed sidebar? | `logo-icon.jpg` (P icon mark) — same as marketing mobile breakpoint |
| Which logo for expanded sidebar / header? | `logo-primary.jpg` (full wordmark) |
| Where does the toggle button live? | Right edge of sidebar, vertically centered — UI Designer decides exact position in spec |
| Are the Heroicons already in the project? | React Engineer must verify with `grep "heroicons" frontend/apps/web/package.json` during implementation |
| What happens to the `Operations`, `Sync`, `Notifications`, `Settings` nav items that are removed? | They remain accessible via the Settings gear icon in the header — the sidebar links are just removed |
| Does `My Account` group in Settings sidebar disappear completely? | Yes — Profile and Security are in the Profile dropdown. `My Account` as a Settings sidebar section is removed. |
| What about `/settings/my-account/profile` and `/settings/my-account/security` routes? | The routes remain — they're just no longer linked from the sidebar. They're linked from the Profile dropdown. |
