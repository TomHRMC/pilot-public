# 🖥️ Pilot Web App UI Design Standards

> **Design-time agent rule** — written to steer the AI agents during the build and published as last used. Where it differs from the as-built system, [`PROVENANCE.md`](../../PROVENANCE.md) and [`dev-docs/diligence/`](../../dev-docs/diligence/README.md) are correct.

## 1. Scope — Web App Internal Surfaces Only

This mode designs internal authenticated surfaces of the Pilot for Trades web dashboard (`frontend/apps/web`). Surfaces in scope:

* Navigation shells (sidebar, top header bar, breadcrumbs)
* Settings pages (all groups: Team, Operations, Billing, etc.)
* Dashboard widgets and data panels
* List pages (tables, filters, pagination)
* Detail pages (Job detail, Customer detail, Invoice detail)
* Forms and modals (create/edit flows)
* Onboarding and empty states

**Out of scope — use `pilot-marketing-ui-designer` instead:**
* `frontend/apps/marketing/` — the public marketing/landing site
* Public-facing invoice payment pages (`/i/[token]`)
* The public quote viewer

**Out of scope — use `pilot-voice-ui-designer` instead:**
* React Native mobile app screens (`frontend/apps/mobile/`)
* Voice session feedback UI (listening/processing states)

---

## 2. Mandatory Pre-Work Before Designing Anything

Before producing any design, you MUST read the following using `read_file`:

1. The existing component or page file(s) you are being asked to redesign — understand what is already there
2. `frontend/apps/web/src/features/settings/components/SettingsSidebar.tsx` — if designing any Settings surface
3. `frontend/apps/web/src/components/AppSidebar.tsx` — if designing any navigation surface
4. `frontend/apps/web/src/app/(authed)/layout.tsx` — if designing the top header or global shell
5. `frontend/packages/ui/src/index.ts` — to know what shared components already exist before proposing new ones

If the relevant file does not exist yet, note that in your design spec.

---

## 3. Design Token Rules — No Hardcoded Colors

ALL design specs MUST reference `pilotPreset` token names. Zero hex codes in a design spec. Violation = the React Engineer will hardcode colors and fail the linter.

**Core token reference:**

| Purpose | Token |
|---|---|
| Primary brand | `brand-600`, `brand-700`, `brand-50` |
| Active nav item | `bg-brand-50 text-brand-700` |
| Hover states | `hover:bg-neutral-100` |
| Borders | `border-neutral-200` |
| Body text | `text-neutral-900` |
| Secondary text | `text-neutral-500` |
| Error / destructive | `text-fault-600`, `bg-fault-50`, `border-fault-200` |
| Success / positive | `text-margin-600`, `bg-margin-50` |
| Warning | `text-alert-600`, `bg-alert-50` |
| Page background | `bg-neutral-50` |
| Card/panel background | `bg-white` |
| Shadow | `shadow-sm`, `shadow-md`, `shadow-lg` |

---

## 4. Viewport and Layout Rules

* **Desktop-first**: Minimum design viewport is **1280px wide**. All layout decisions start here.
* **Responsive**: Note how the design should adapt at 1024px and 768px if applicable, but the primary spec is for 1280px+.
* **No mobile specs from this mode**: Mobile is React Native and belongs to `pilot-voice-ui-designer`.

**Layout constraints:**
* Sidebar (expanded): 256px wide
* Sidebar (collapsed): 64px wide
* Top header bar: 48px tall (`h-12`)
* Settings content area: `max-w-4xl` for form-heavy pages; full-width for table pages
* Page content padding: `px-6 py-6` standard

---

## 5. Icon Rules

**Never use emoji as icons in production web UI.** Emoji were used historically in `AppSidebar.tsx` as placeholders — they are being replaced.

**Mandatory**: Use [Heroicons 2.0](https://heroicons.com/) — specify the exact icon name from the Heroicons library in your design spec. Example: "Use `Cog6ToothIcon` (outline variant)" — not "use a gear icon."

* **Outline variant** for navigation items, sidebar icons, and secondary actions
* **Solid variant** for primary CTAs and active states where a filled icon adds emphasis
* **Icon size**: 20px (`w-5 h-5`) for navigation; 16px (`w-4 h-4`) for inline/table icons

If Heroicons does not have a suitable icon, specify the visual description and note "custom SVG required."

---

## 6. Component Hierarchy Rules

Before proposing a new component, check if it already exists. **The authoritative list of every shared component is the barrel export at [`frontend/packages/ui/src/index.ts`](../../frontend/packages/ui/src/index.ts)** — read it before proposing any new shared component. A component does not exist until it appears in that barrel. The `packages/ui` library is large (FE-B0 through FE-B16 exports) and includes many locked-interface components you must compose rather than recreate.

Common ones you will reach for first:

| If you need... | Check first... |
|---|---|
| Loading state | `<LoadingState>` from `@pilot/ui/states` |
| Error state | `<ErrorState>` from `@pilot/ui/states` |
| Empty state | `<EmptyState>` / `<FirstTimeUserState>` from `@pilot/ui/states` |
| Role-gated content | `<RoleGate permission="...">` from `@pilot/ui/role-gate` |
| Top-of-page banner | `<NotificationBanner>` from `@pilot/ui` (severity-routed from RFC 7807 errors) |
| Track-changes diff | `<DiffView>` from `@pilot/ui` (§16.2 pattern — do not design a new diff UI) |
| Send-preview modal | `<MessagePreviewModal>` from `@pilot/ui` (§16.7 always-preview-before-send) |
| Optimistic pending marker | `<PendingBadge>` from `@pilot/ui` (§16.8) |
| Settings default/override control | `<SettingControl>` / `<EffectiveSettingDisplay>` from `@pilot/ui` (§16.5) |
| Offline sync status | `<InFlightSyncIndicator>` from `@pilot/ui` (§16.9) |
| Contextual help "?" | `<HelpAnchor>` from `@pilot/ui` |
| Pagination | `<PilotPaginator>` from `apps/web/src/components/PilotPaginator.tsx` |
| Data table | `<PilotTable>` from `apps/web/src/components/PilotTable.tsx` |

> **Never design a new top-level UX pattern that duplicates a locked §16 platform pattern** (track-changes diff, confirm-as-turn, 409-and-refresh, system-default/tenant-override, four-class severity, always-preview-before-send, optimistic UI, mobile escalation, in-flight sync, bilateral conflict resolution). Compose the existing component; if it doesn't fit, note "extend `<Component>` with optional prop X" — never "build new."

**Component placement rule** (for the React Engineer's reference in the spec):
* Generic reusable → `packages/ui/src/`
* Web-app-specific reusable → `apps/web/src/components/`
* Domain-specific (feature-only) → `apps/web/src/features/[domain]/components/`

---

## 7. Typography Scale

Use these class names — do not specify font sizes in px or rem:

| Use | Class |
|---|---|
| Page H1 | `text-h1 font-semibold` |
| Section H2 | `text-h2 font-semibold` |
| Widget H3 | `text-h3 font-medium` |
| Body text | `text-body` |
| Caption / small | `text-caption` |
| Table header | `text-sm font-medium text-neutral-700` |
| Table cell | `text-sm text-neutral-900` |

---

## 8. Output Format — Design Spec Document

Every design task MUST produce a spec file at:

```
dev-docs/architecture-design/batch-designs/[batch-code]-ui-design-spec.md
```

The spec MUST include:
1. **Surface overview** — what page/component this is, route, who sees it (RBAC)
2. **Pixel specs** — exact dimensions (width, height, padding, gap, border-radius) for every new or changed component
3. **Token-only colors** — no hex codes
4. **Icon inventory** — exact Heroicons name for every icon
5. **State coverage** — loading, empty, error, and every data state
6. **Interaction spec** — hover, focus, active, disabled states for every interactive element
7. **Animation spec** — if any transitions, specify CSS property + duration + easing (e.g., `transition: width 200ms ease-in-out`)
8. **Component manifest** — a table of every new or modified file with its exact path and a one-line description of the change
9. **Implementation notes** — anything the React Engineer needs to know that is not visually obvious (e.g., localStorage keys, query params, hook names)

---

## 9. Handoff Gate

After producing the design spec, STOP. Do NOT implement any code. The design spec goes to Tom for approval. Implementation starts only after Tom confirms the spec is approved. State this explicitly at the end of every design spec output.

---

## 10. Accessibility — WCAG 2.2 AA Is the Design Bar (Not an Engineering Afterthought)

The React Engineer's Definition of Done requires **zero axe-core violations** on every new surface. Accessibility failures that originate in the design (color-only status, tiny targets, obscured focus) become the engineer's blocker. Bake these into every spec:

- **Color is never the only signal.** Every status badge (§3 of the design-system reference) pairs a color token with a text label. Never spec "red = overdue" with no accompanying text/icon — fails WCAG 1.4.1 (Use of Color).
- **Contrast ≥ 4.5:1 for body text, ≥ 3:1 for large text and UI component borders.** Our token pairings (e.g., `text-neutral-900 on bg-white`, `text-brand-700 on bg-brand-50`) are pre-validated — if you invent a new pairing, state the contrast ratio in the spec.
- **Target Size ≥ 24×24px (WCAG 2.2 SC 2.5.8).** Every icon button, table row action, pagination control, and the modal close `XMarkIcon` needs at least a 24×24px hit area (prefer 44×44px for primary actions). A bare `w-4 h-4` (16px) icon is never an acceptable sole click target — spec a padded hit area around it.
- **Focus Not Obscured (WCAG 2.2 SC 2.4.11).** With the `h-12` sticky header and any `<NotificationBanner>` portal, verify keyboard focus is never fully hidden. Note scroll-into-view / `scroll-margin-top` behavior in the spec for anchored content beneath the sticky header.
- **Every form field has a visible `<label>` above it** (§5 form pattern). Placeholder-as-label is banned. Error text is spec'd as `text-fault-600` **and** described as linked via `aria-describedby` for the engineer.
- **Accessible Authentication (WCAG 2.2 SC 3.3.8).** Login / MFA specs must allow paste in code fields and must not require memorization puzzles. Note "paste allowed" explicitly on any OTP/MFA input.
- **Consistent Help + Redundant Entry (WCAG 2.2 SC 3.2.6 / 3.3.7).** The `<HelpAnchor>` "?" stays in the same relative position across surfaces. Multi-step flows (signup, onboarding) must not re-ask for data already entered — spec the carry-forward.

Add an **Accessibility Notes** subsection to every design spec (append to the §8 output format) covering: color-independent status, target sizes for all interactive elements, focus order + focus-visible treatment, and modal focus-trap/return behavior.

---

## 11. Interaction States & Motion — Spec All Five States + Respect Reduced Motion

- **Every interactive element must have all five states spec'd**: default, hover, focus-visible, active, disabled. A spec that only describes the default state is incomplete (this is already implied by §8.6 — it is now mandatory, not optional).
- **`focus-visible`, not `focus`** — spec a visible ring (`focus-visible:ring-2 focus-visible:ring-brand-500`) so keyboard users get an indicator while mouse users don't see a persistent ring on click.
- **Disabled ≠ hidden** — recall the engineer's RBAC rule is *hide-not-disable* for unauthorized actions (`<RoleGate>`). Reserve the `disabled` visual state for genuinely-unavailable-but-visible actions (e.g., "Save" until a form is dirty), not for permissions.
- **Motion respects `prefers-reduced-motion`.** Any transition/animation you spec (§8.7) must have a reduced-motion fallback (instant or opacity-only). State this in the animation spec — e.g., `transition: width 200ms ease-in-out; @media (prefers-reduced-motion: reduce) → no transition`.
- **Skeletons over spinners for content-shaped loading.** For list/detail pages prefer a skeleton matching the final layout (reduces layout shift) over a bare centered spinner; `<LoadingState>` covers the spinner case for small regions.

---

## 12. Stack & Data-State Awareness — Design for What the App Actually Renders

The web app is **Next.js 16 / React 19** with **TanStack Query v5** driving all data. Design specs must account for the real runtime states, not just the happy path.

- **Four data states minimum, always** (already §8.5): `isPending` (initial load → skeleton/`<LoadingState>`), `isError` (→ `<ErrorState>` with retry), empty (→ `<EmptyState>`/`<FirstTimeUserState>`), and populated. Every list and detail spec covers all four.
- **"Overdue" is a derived state, not a status** — never spec an "overdue" invoice status badge. Use the `issued` badge plus an aging-bucket overlay (design-system reference §3). The backend has no `overdue` status code; a spec that assumes one will produce a dead filter.
- **Money is displayed from integer cents** — amounts arrive as `_cents` integers. Spec currency formatting as "divide by 100, format as USD"; for annual pricing show the per-month equivalent (`annual_price_cents / 12 / 100`), never the raw annual cents. (Mirrors the React Engineer billing-display rule.)
- **Real-time surfaces use SSE, not polling** — dispatch board, notifications bell, SMS threads update via Server-Sent Events. When speccing a live surface, describe the incremental-update behavior (new row slides in / badge count increments), not a "refresh" button as the primary mechanism.
- **Desktop-first at 1280px stands** (§4) — but note 1024px/768px reflow for any new table or multi-column layout so the engineer isn't guessing. Mobile app UI remains out of scope (React Native → voice-ui-designer).
