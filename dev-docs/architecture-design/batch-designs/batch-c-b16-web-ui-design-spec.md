# C-B16 Web UI Design Spec — Settings > Website (Tenant Site Configuration Surface)

**Version**: 1.0
**Date**: August 14, 2026
**Author**: Pilot Web UI Designer
**Status**: ✅ Tom-approved 2026-08-14 (Handoff Gate passed — §21 open items resolved: Option 3 ships as the disabled-card treatment per §6.3.6 item (a))
**Batch**: C-B16 (Part B prerequisite — this UI design spec must be Tom-approved before the React Engineer prompt is authored)
**Source design doc**: `batch-c-b16-design.md` — §D (5 authed endpoints + contracts), §E (§16.5/§16.7 consumption), §G-16/17/19/20 (overwrite-confirm, brand-state timing, one-time email + requirements PDF), §H (spec row), §I (component manifest)
**Companion spec**: `mkt-c-b16-design-spec.md` — public tenant-site templates + Requirements Guide PDF layout
**Platform**: Next.js 16 / React 19 web app (`apps/web`) — authenticated settings surface
**Backend dependency**: `GET /api/v1/tenant-site`, `PUT /api/v1/tenant-site`, `GET /api/v1/tenant-site/slug-availability`, `POST /api/v1/tenant-site/publish`, `POST /api/v1/tenant-site/unpublish` (Part A — live before Part B)

---

## Table of Contents

- [1. Surface Overview](#1-surface-overview)
- [2. Design Principles & Cross-Cutting Requirements](#2-design-principles--cross-cutting-requirements)
- [3. Token & Typography Reference](#3-token--typography-reference)
- [4. Component-Existence Check](#4-component-existence-check)
- [5. Settings Nav Registration](#5-settings-nav-registration)
- [6. Pixel Specs — Page Shell & Option-Selection Cards](#6-pixel-specs--page-shell--option-selection-cards)
- [7. Pixel Specs — Hosted-Site Form (Defaults-from-Profile)](#7-pixel-specs--hosted-site-form-defaults-from-profile)
- [8. Pixel Specs — SlugAvailabilityInput](#8-pixel-specs--slugavailabilityinput)
- [9. Pixel Specs — SitePreviewPanel (§16.7 Preview-Before-Publish)](#9-pixel-specs--sitepreviewpanel-167-preview-before-publish)
- [10. Pixel Specs — PublishConfirmDialog + 409 Overwrite Branch](#10-pixel-specs--publishconfirmdialog--409-overwrite-branch)
- [11. Pixel Specs — BrandStateNotice (§G-17)](#11-pixel-specs--brandstatenotice-g-17)
- [12. Pixel Specs — WebsiteRequirementsPanel + SelfHostEmailNotice (§G-19/20)](#12-pixel-specs--websiterequirementspanel--selfhostemailnotice-g-1920)
- [13. Pixel Specs — Unpublish Flow + Escalated Warning (§G-8)](#13-pixel-specs--unpublish-flow--escalated-warning-g-8)
- [14. C-B9 10DLC Profile Form — WebsiteRequirementsPanel Placement](#14-c-b9-10dlc-profile-form--websiterequirementspanel-placement)
- [15. State Coverage](#15-state-coverage)
- [16. Interaction Spec](#16-interaction-spec)
- [17. Animation Spec](#17-animation-spec)
- [18. Component Manifest](#18-component-manifest)
- [19. Implementation Notes](#19-implementation-notes)
- [20. Accessibility Notes](#20-accessibility-notes)
- [21. Open Items for Tom](#21-open-items-for-tom)
- [22. Handoff Gate](#22-handoff-gate)

---

## 1. Surface Overview

This spec covers the authenticated **Settings > Website** sub-page — a new settings surface where tenants choose how to satisfy TCR 10DLC website vetting. Tenants select between two options (a third is deferred to C-B17), configure their hosted compliance site content, preview it, and publish. The publish flow auto-populates the `website` field on the 10DLC profile, with explicit overwrite confirmation when a tenant-entered URL already exists (§G-16). A brand-state notice banner sequences the tenant's next steps relative to their 10DLC brand registration status (§G-17).

### 1.1 Route & Shell

| Property | Value |
|---|---|
| **Route** | `apps/web/src/app/(authed)/settings/website/page.tsx` → `/settings/website` |
| **Shell** | `SettingsShell` — app sidebar (256px) + settings sidebar (224px) + content area (`max-w-4xl`) |
| **Content width** | `max-w-4xl` (form-heavy settings page per design standards §4) |
| **Page padding** | `px-6 py-6` standard |
| **Mode** | Thin server component (no `"use client"`, no data fetching) — renders `<TenantSiteSettingsForm />` client component |

### 1.2 RBAC

| Permission | Roles | Applied via |
|---|---|---|
| `settings.view` (read) | owner, office_staff, operator | `<RoleGate permission="settings.view">` wraps the page content |
| `settings.manage` (write) | owner, operator | `<RoleGate permission="settings.manage">` wraps form inputs and action buttons; read-only users see the display-only variant |

Per design-system reference §8: `tech` role sees Jobs, Schedule, Comms, Catalog only — **no access to this surface**. The settings sidebar item is hidden for `tech` (hide-not-disable per IA Decision 8).

### 1.3 Data Sources (TanStack Query v5)

| Hook | Endpoint | Purpose |
|---|---|---|
| `useTenantSite` | `GET /api/v1/tenant-site` | Current config + status + computed URL + effective defaults merged from 10DLC profile |
| `useUpsertTenantSite` | `PUT /api/v1/tenant-site` | Save draft (site_kind, slug, display/contact overrides, show_full_address) |
| `useSlugAvailability` | `GET /api/v1/tenant-site/slug-availability?slug=` | Live slug availability feedback (debounced) |
| `usePublishTenantSite` | `POST /api/v1/tenant-site/publish` | Build snapshot, set status=published, auto-populate website (§B.2 three-way rule) |
| `useUnpublishTenantSite` | `POST /api/v1/tenant-site/unpublish` | Set status=unpublished (does NOT clear website — §G-8) |

All hooks: `retry: false`, `apiClient` only (RULE 2). Query keys namespaced under `["tenant-site", ...]`.

---

## 2. Design Principles & Cross-Cutting Requirements

### 2.1 Compose Locked §16 Patterns — Never Invent New Top-Level UX

| Pattern | How this surface composes it |
|---|---|
| **§16.5 System-default + tenant-override** | Form fields default from `tenant_10dlc_profile` / `tenant` (server-merged `defaults` in the GET response). Each field shows its default source annotation + override affordance. Uses the visual language of `SettingControl` (State 1 inheriting / State 2 overridden) but adapted for text fields — see §7.3 for the composition decision. |
| **§16.7 Always-preview-before-send** | Publish is a public one-way-door action. The surface renders a full preview of the exact snapshot payload via `<SitePreviewPanel>` + a confirm step via `<PublishConfirmDialog>` before the `POST .../publish` call. This mirrors the `MessagePreviewModal` precedent (preview → confirm → send) but with a server-data-driven snapshot preview, not an iframe. |
| **§16.6 Four-class severity** | `NotificationBanner` severity routing for success/error toasts. The `<BrandStateNotice>` is a persistent inline banner (not a toast) — see §11. |

### 2.2 Token-Only — Zero Hex Codes

ALL colors use `pilotPreset` token names. No hex codes anywhere in this spec. The React Engineer will fail the linter on any hardcoded color.

### 2.3 Heroicons 2.0 — Exact Names, No Emoji

Every icon is specified by its exact Heroicons 2.0 name and variant (outline or solid). No emoji in production web UI.

### 2.4 Desktop-First at 1280px

Primary spec is 1280px+. Reflow notes at 1024px and 768px where relevant. No mobile specs (React Native → `pilot-voice-ui-designer`).

### 2.5 Money / Data Display

No money on this surface. The `published_at` / `unpublished_at` / `kit_sent_at` timestamps are displayed as formatted dates (`MMMM D, YYYY`).

---

## 3. Token & Typography Reference

All tokens from `packages/ui/src/styles/globals.css` and `packages/ui/tailwind.preset.ts`. No new values.

### 3.1 Color Tokens Used on This Surface

| Token | Tailwind class | Usage |
|---|---|---|
| `brand-50` | `bg-brand-50` | Active option card border accent, slug-available badge bg |
| `brand-600` | `text-brand-600`, `bg-brand-600` | Primary CTA buttons, links, active radio indicator |
| `brand-700` | `text-brand-700`, `hover:bg-brand-700` | Active nav item, CTA hover |
| `brand-100` | `bg-brand-100` | "tenant override" pill bg (from SettingControl) |
| `neutral-50` | `bg-neutral-50` | Page background, option card inactive bg |
| `neutral-100` | `bg-neutral-100` | Inactive badge bg, fieldset bg |
| `neutral-200` | `border-neutral-200` | Card borders, dividers, input borders |
| `neutral-300` | `border-neutral-300` | Disabled card border |
| `neutral-400` | `text-neutral-400` | Default-source annotation (muted), placeholder text |
| `neutral-500` | `text-neutral-500` | Secondary text, helper text, "optional" label |
| `neutral-600` | `text-neutral-600` | Description text, contact labels |
| `neutral-700` | `text-neutral-700` | Form labels, body text |
| `neutral-800` | `text-neutral-800` | Card titles, section headings |
| `neutral-900` | `text-neutral-900` | Page H1, primary text |
| `alert-50` | `bg-alert-50` | Warning banner bg, brand-state in-flight/rejected bg |
| `alert-100` | `bg-alert-100` | Warning badge bg |
| `alert-600` | `text-alert-600` | Warning text, required asterisk, home-address warning |
| `alert-700` | `text-alert-700` | Warning banner title text |
| `alert-200` | `border-alert-200` | Warning banner border |
| `fault-50` | `bg-fault-50` | Error bg, destructive warning bg |
| `fault-100` | `bg-fault-100` | Error badge bg |
| `fault-500` | `text-fault-500` | Destructive text |
| `fault-600` | `text-fault-600` | Error text, destructive button text |
| `fault-200` | `border-fault-200` | Error border, destructive warning border |
| `fault-600` (bg) | `bg-fault-600` | Destructive confirm button bg |
| `margin-50` | `bg-margin-50` | Success bg, slug-available state bg (alt) |
| `margin-600` | `text-margin-600` | Success text, "published" status text |
| `margin-700` | `text-margin-700` | Success banner title |
| `margin-100` | `bg-margin-100` | Published status badge bg |
| `white` | `bg-white` | Card bg, input bg, modal panel bg |

### 3.2 Typography Scale

| Use | Class | Source |
|---|---|---|
| Page H1 | `text-h1 font-semibold` | Design standards §7 |
| Section H2 | `text-h2 font-semibold` | Design standards §7 |
| Card title H3 | `text-h3 font-medium` | Design standards §7 |
| Body text | `text-body` | Design standards §7 |
| Caption / small | `text-caption` | Design standards §7 |
| Form label | `text-sm font-medium text-neutral-700 mb-1` | Design-system reference §5 |
| Helper text | `text-xs text-neutral-500 mt-1` | Design-system reference §5 |
| Error text | `text-xs text-fault-600 mt-1` | Design-system reference §5 |

### 3.3 Spacing & Layout

| Property | Value | Tailwind class |
|---|---|---|
| Content max-width | 896px (56rem) | `max-w-4xl` |
| Page padding | 24px | `px-6 py-6` |
| Card padding | 24px | `p-6` |
| Card border radius | 12px | `rounded-xl` |
| Card border | 1px | `border border-neutral-200` |
| Card shadow | subtle | `shadow-sm` |
| Section gap | 24px | `space-y-6` |
| Form field gap | 16px | `space-y-4` |
| Input padding | 12px horizontal, 8px vertical | `px-3 py-2` |
| Input border radius | 6px | `rounded-md` |

---

## 4. Component-Existence Check

**Performed against**: `frontend/packages/ui/src/index.ts` (465 lines, full barrel export).

### 4.1 Shared Components Composed (NOT recreated)

| Component | Import path | How it's used on this surface |
|---|---|---|
| `RoleGate` | `@pilot/ui` | Wraps the page content (`settings.view`) and the form/action area (`settings.manage`) |
| `LoadingState` | `@pilot/ui/states` | Initial `useTenantSite` load — `type="inline"` skeleton matching the form layout |
| `ErrorState` | `@pilot/ui/states` | `useTenantSite` error — `type="server"` with retry |
| `EmptyState` | `@pilot/ui/states` | `configured: false` first-visit state — guides the tenant to select an option |
| `NotificationBanner` | `@pilot/ui` | Success/error toasts after publish/unpublish/save (severity-routed) |
| `HelpAnchor` | `@pilot/ui` | Contextual "?" on the page header and the slug field |

### 4.2 §16.5 SettingControl — Composition Decision

`SettingControl` is the canonical system-default/tenant-override component. However, its locked interface is optimized for scalar settings (integer/boolean/select) with blur-save or group-save semantics. The hosted-site form fields are **text inputs with explicit-save semantics** (the whole form saves as one PUT), and the "default source" is the 10DLC profile, not a system-default catalog entry.

**Decision**: Do NOT force `SettingControl` onto these fields — its locked `saveMode` and `scope` semantics don't fit a form that saves as a batch. Instead, **compose the visual language** of `SettingControl` (State 1 default-source annotation, State 2 override pill) in a feature-local `DefaultsAnnotatedField` wrapper that renders the standard form input + a `text-caption text-neutral-400` "Default from 10DLC profile: {value}" annotation when the field is inheriting, and a `bg-brand-100 text-brand-700` "overridden" pill when the tenant has changed it. This preserves the §16.5 visual contract without abusing the locked component's save machinery.

> **Note for the React Engineer**: If a future batch adds per-field blur-save to this form, migrate `DefaultsAnnotatedField` fields to `<SettingControl saveMode="blur">` one at a time. The visual treatment is intentionally compatible.

### 4.3 §16.7 MessagePreviewModal — Composition Decision

`MessagePreviewModal` is the locked always-preview-before-send component for communications. Its interface is tightly coupled to `CommunicationPreviewResponse` / `FreeFormPreviewData` shapes (recipient, channel, editable variables). The site publish preview is a **completely different data shape** (snapshot pages payload: landing/privacy/terms with body_paragraphs).

**Decision**: Do NOT reuse `MessagePreviewModal`. Create a feature-local `<SitePreviewPanel>` that renders the snapshot payload server-data-driven (not an iframe — the draft is not publicly accessible pre-publish per the task brief). The **pattern** (preview → confirm → action) is composed; the **component** is not. This is explicitly authorized: "Note what composes from existing components vs a SitePreviewPanel" (task brief §4).

### 4.4 New Feature-Local Components (all in `apps/web/src/features/tenant-site/`)

No new `@pilot/ui` shared components are proposed (confirmed against the barrel — design doc §I: "No new shared components expected"). All new components are feature-local to the `tenant-site` feature directory.

---

## 5. Settings Nav Registration

### 5.1 Sidebar Item

A new top-level item **"Website"** is added to `SIDEBAR_ITEMS` in `SettingsSidebar.tsx`.

**Placement**: After "Branding" (which contains SMS & 10DLC, Email Branding, Messaging Setup) and before "Voice & AI". The Website surface is a compliance sibling to the SMS/10DLC surface — placing it adjacent to Branding groups the 10DLC compliance surfaces together.

```typescript
// Insert after the "Branding" block (line 113), before "Voice & AI" (line 114):
{
  label: "Website",
  href: "/settings/website",
  roleRequired: "settings.view",
},
```

**Rationale for top-level vs sub-item of Branding**: The Website surface is a distinct product area (site hosting + compliance kit), not a branding sub-config. It has its own publish/unpublish lifecycle and brand-state timing matrix. A top-level item gives it the visibility this compliance-critical surface deserves. The `roleRequired: "settings.view"` gates visibility — `tech` role does not see it (hide-not-disable).

### 5.2 No Sub-Items

The Website surface is a single page — no sub-navigation. Direct link to `/settings/website`.

### 5.3 Active State

Per the existing `renderItem` pattern: `isActive("/settings/website")` → `bg-brand-50 font-medium text-brand-700` + `aria-current="page"`.

---

## 6. Pixel Specs — Page Shell & Option-Selection Cards

### 6.1 Page Layout Structure

```
┌──────────────────────────────────────────────────────────────────┐
│  SettingsShell (app sidebar | settings sidebar | content)        │
│                                                                    │
│  ┌─ content (max-w-4xl, px-6 py-6, space-y-6) ─────────────────┐  │
│  │                                                                │  │
│  │  ┌─ page header ──────────────────────────────────────────┐   │  │
│  │  │  Website                              [?] HelpAnchor    │   │  │
│  │  │  Satisfy TCR 10DLC website vetting for SMS compliance.  │   │  │
│  │  └──────────────────────────────────────────────────────────┘   │  │
│  │                                                                │  │
│  │  ┌─ BrandStateNotice (conditional, §11) ──────────────────┐   │  │
│  │  │  [icon] Brand registration: In-flight                   │   │  │
│  │  │  Your brand vetting is checking the URL on file...       │   │  │
│  │  └──────────────────────────────────────────────────────────┘   │  │
│  │                                                                │  │
│  │  ┌─ Section: "Choose your approach" ──────────────────────┐   │  │
│  │  │                                                          │   │  │
│  │  │  ┌─ SiteOptionCard: Compliance Kit ───┐  ┌─ SiteOptionCard: Hosted ─┐  │  │
│  │  │  │  ○  Compliance Kit                  │  │  ●  Hosted Compliance Site │  │  │
│  │  │  │  Self-host with our kit             │  │  We host a 3-page site     │  │  │
│  │  │  │  [status badge]                     │  │  [status badge]            │  │  │
│  │  │  │  ...                                │  │  ...                       │  │  │
│  │  │  └─────────────────────────────────────┘  └────────────────────────────┘  │  │
│  │  │                                                          │   │  │
│  │  │  ┌─ SiteOptionCard: Starter Site (deferred) ───────────┐ │   │  │
│  │  │  │  ○  Starter Site  [Coming in a future update]       │ │   │  │
│  │  │  └──────────────────────────────────────────────────────┘ │   │  │
│  │  └──────────────────────────────────────────────────────────┘   │  │
│  │                                                                │  │
│  │  ┌─ Section: "Configure your hosted site" (conditional) ──┐   │  │
│  │  │  [TenantSiteSettingsForm — §7]                          │   │  │
│  │  └──────────────────────────────────────────────────────────┘   │  │
│  │                                                                │  │
│  │  ┌─ Section: "Preview & publish" (conditional) ───────────┐   │  │
│  │  │  [SitePreviewPanel — §9]  [Publish button]              │   │  │
│  │  └──────────────────────────────────────────────────────────┘   │  │
│  │                                                                │  │
│  └────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘
```

### 6.2 Page Header

| Property | Value | Token / Class |
|---|---|---|
| Container | `mb-2` | — |
| H1 | "Website" | `text-h1 font-semibold text-neutral-900` |
| Description | "Satisfy TCR 10DLC website vetting for SMS compliance. Choose how to publish your business website — self-host with our Compliance Kit or let Pilot host a compliance site for you." | `text-body text-neutral-500 mt-1` |
| HelpAnchor | Positioned top-right of the header row, `ml-auto` | `<HelpAnchor context={{ surface: "settings-website" }} />` |

**Layout**: `flex items-start justify-between` — H1+description block on the left, `HelpAnchor` on the right.

### 6.3 SiteOptionCard Component

Each option is a selectable card with a radio indicator, title, description, status badge, and body content.

#### 6.3.1 Card Container

| Property | Value | Token / Class |
|---|---|---|
| Element | `<div role="radio" aria-checked={selected}>` inside a `<fieldset>` | — |
| Width | Full width of the section; cards stack vertically on <1024px, 2-column grid on ≥1024px for Option 1 + Option 2 | `grid grid-cols-1 lg:grid-cols-2 gap-4` for the first two; Option 3 spans full width below |
| Padding | 24px | `p-6` |
| Border | 1px, `rounded-xl` | `border rounded-xl` |
| Border color (selected) | `border-brand-500` (2px ring effect via `ring-2 ring-brand-500`) | `border-brand-500 ring-2 ring-brand-500` |
| Border color (unselected) | `border-neutral-200` | `border-neutral-200` |
| Background (selected) | `bg-brand-50` | `bg-brand-50` |
| Background (unselected) | `bg-white` | `bg-white` |
| Shadow | `shadow-sm` | `shadow-sm` |
| Cursor | `cursor-pointer` | `cursor-pointer` |
| Min height | ~140px | `min-h-[140px]` |
| Transition | `transition: border-color 150ms ease-in-out, background-color 150ms ease-in-out` | `transition-colors duration-150` |

#### 6.3.2 Radio Indicator

| Property | Value | Token / Class |
|---|---|---|
| Icon | `CircleIcon` (Heroicons 2.0, outline) when unselected; `CheckCircleIcon` (Heroicons 2.0, solid) when selected | — |
| Size | 24px | `w-6 h-6` |
| Color (selected) | `text-brand-600` | `text-brand-600` |
| Color (unselected) | `text-neutral-400` | `text-neutral-400` |
| Position | Top-left of card, `mr-3` | `flex items-start gap-3` |

#### 6.3.3 Card Title & Description

| Property | Value | Token / Class |
|---|---|---|
| Title | Option name (e.g., "Compliance Kit", "Hosted Compliance Site", "Starter Site") | `text-h3 font-medium text-neutral-900` |
| Description | One-line summary | `text-body text-neutral-600 mt-1` |

#### 6.3.4 Status Badge (per option)

The status badge shows the current state of that option for this tenant. Uses the design-system reference §3 badge patterns (color + text label — never color-only).

**Option 1 — Compliance Kit**:

| State | Badge text | Token classes |
|---|---|---|
| Not selected, no kit sent | "Not started" | `bg-neutral-100 text-neutral-700` |
| Kit sent (requirements email triggered) | "Kit emailed" | `bg-blue-100 text-blue-700` |
| Active (tenant selected this option) | "Active" | `bg-brand-100 text-brand-700` |

**Option 2 — Hosted Compliance Site**:

| State | Badge text | Token classes |
|---|---|---|
| Not configured | "Not configured" | `bg-neutral-100 text-neutral-700` |
| Draft saved | "Draft" | `bg-neutral-100 text-neutral-700` |
| Published | "Published" | `bg-margin-100 text-margin-700` |
| Unpublished | "Unpublished" | `bg-neutral-100 text-neutral-500` |
| Active (currently selected) | "Active" + status | `bg-brand-100 text-brand-700` (overrides status badge when selected) |

**Option 3 — Starter Site (deferred)**:

| State | Badge text | Token classes |
|---|---|---|
| Always | "Coming in a future update" | `bg-neutral-100 text-neutral-500` |

#### 6.3.5 Card Body Content

**Option 1 — Compliance Kit** body:

```
Self-host your own website using our Compliance Kit. We email you the
requirements guide and pre-merged Privacy/Terms text. You publish the
pages on your own domain.

[WebsiteRequirementsPanel — §12, shown when this option is selected
 or when a self-managed URL exists in the 10DLC profile]
```

**Option 2 — Hosted Compliance Site** body:

```
Pilot hosts a 3-page compliance site for you: a business-identity
landing page, a Privacy Policy, and Terms of Service — all with the
required SMS disclosure language. We auto-fill from your 10DLC profile.
Your site: {slug}.p4tsites.com (preview before publishing).

[When selected: the hosted-site form (§7) and preview/publish
sections appear below]
```

**Option 3 — Starter Site (deferred)** body:

```
A richer single business website with services, hours, logo, and a
contact form — plus the compliance pages. Pricing and features in
development.
```

#### 6.3.6 Option 3 — Deferred Treatment

**Design**: Option 3 is rendered as a **disabled-appearing card** (not omitted). This is an explicit open question for Tom (§21, item 1) — the task brief says "do not silently ship a 'coming soon' string (Rule 9.4)" but also says "include a treatment for the deferred Option 3 (disabled/unavailable card vs omitted) as an explicit open question."

**Spec'd treatment** (pending Tom's decision):

| Property | Value | Token / Class |
|---|---|---|
| Border | `border-neutral-200` (no ring, no selected state) | `border-neutral-200` |
| Background | `bg-neutral-50` (muted) | `bg-neutral-50` |
| Radio indicator | `CircleIcon` outline, `text-neutral-300` (not clickable) | `text-neutral-300` |
| Cursor | `cursor-not-allowed` | `cursor-not-allowed` |
| Opacity | `opacity-75` | `opacity-75` |
| Badge | "Coming in a future update" | `bg-neutral-100 text-neutral-500` |
| `aria-disabled` | `true` | — |
| `tabIndex` | `-1` (not focusable) | — |
| Click handler | None — card is not selectable | — |

> **Open item for Tom (§21-1)**: Confirm whether Option 3 should be (a) this disabled card treatment, (b) omitted entirely from the page, or (c) a different treatment. The disabled card communicates "this product area exists and is coming" without a bare "coming soon" string — it has a real description of what the starter site will be.

### 6.4 Option-Selection Interaction

Selecting Option 1 or Option 2 calls `useUpsertTenantSite` with `{ site_kind: "compliance_kit" | "hosted_compliance" }`. The PUT is the upsert-draft endpoint (§D-2). On success:

- Option 1 selected → the hosted-site form section (§7) and preview/publish section (§9) are hidden; the `WebsiteRequirementsPanel` (§12) appears inside the Option 1 card.
- Option 2 selected → the hosted-site form section (§7) and preview/publish section (§9) appear below the cards; the `WebsiteRequirementsPanel` is hidden from the Option 1 card (it lives in the C-B9 profile form instead).

**Switching options**: If the tenant switches from Option 2 (published) to Option 1, a confirmation dialog warns: "Switching to the Compliance Kit will not unpublish your hosted site. Unpublish it separately if you no longer want it live." (The hosted site remains published until explicitly unpublished — §G-8.)

---

## 7. Pixel Specs — Hosted-Site Form (Defaults-from-Profile)

### 7.1 Section Container

| Property | Value | Token / Class |
|---|---|---|
| Section heading | "Configure your hosted site" | `text-h2 font-semibold text-neutral-900` |
| Section description | "These fields appear on your public compliance site. Defaults are merged from your 10DLC business profile — override any field to customize what the public sees." | `text-body text-neutral-500 mt-1` |
| Form container | `bg-white rounded-xl border border-neutral-200 shadow-sm p-6 space-y-6` | — |
| Save mode | Explicit save (one PUT for the whole form) | Save button at the bottom |

### 7.2 Form Fields

All fields use the design-system reference §5 form pattern:

- Label: `text-sm font-medium text-neutral-700 mb-1`
- Input: `w-full rounded-md border border-neutral-300 px-3 py-2 text-sm text-neutral-900 focus:ring-2 focus:ring-brand-500 focus:border-brand-500`
- Helper text: `text-xs text-neutral-500 mt-1`
- Error text: `text-xs text-fault-600 mt-1` (with `aria-describedby` linking)

| # | Field | Type | Required | Default source (§16.5) | Helper text |
|---|---|---|---|---|---|
| 1 | Display name | text, `maxLength=200` | Yes | `dba_name` or `legal_business_name` from 10DLC profile | "The business name shown on your public site. Defaults to your DBA or legal name." |
| 2 | Tagline | text, `maxLength=300` | No | None (empty) | "A one-line description of your business (optional)." |
| 3 | Public phone | tel, `maxLength=32` | Conditional (phone OR email) | `support_phone` from 10DLC profile | "A phone number customers can reach you at. Defaults to your support phone." |
| 4 | Public email | email, `maxLength=320` | Conditional (phone OR email) | `support_email` from 10DLC profile | "An email customers can reach you at. Defaults to your support email." |
| 5 | City | text, `maxLength=120` | Yes | `hq_city` from 10DLC profile | "Your service city. Defaults to your HQ city." |
| 6 | State | text, `maxLength=2`, uppercase | Yes | `hq_state` from 10DLC profile | "Your service state (2-letter). Defaults to your HQ state." |
| 7 | Show full address | boolean toggle | No | `false` (never defaulted from HQ address — §G-10) | "Include your street address and ZIP on the public site. Off by default — many sole proprietors register with a home address." |
| 8 | Slug | text, `maxLength=63`, lowercase, regex `^[a-z0-9]([a-z0-9-]{1,61}[a-z0-9])?$` | Yes (for Option 2) | None (tenant chooses) | "Your site URL: {slug}.p4tsites.com. Editable until first publish; immutable after." |

**Required-field validation** (from §D-4 `missing_required_fields`): `display_name`, `public_phone` **or** `public_email`, `public_city`, `public_state` are required to publish. The form shows inline validation on the publish attempt, not on every keystroke.

### 7.3 DefaultsAnnotatedField Wrapper (§16.5 Visual Language)

Each field that has a default source is wrapped in `DefaultsAnnotatedField`, which renders the standard form input plus a provenance annotation below:

**State 1 — Inheriting default** (field value === default value):

```
┌─ Display name * ─────────────────────────────────┐
│  [ Lang Electric                           ]      │
│  Default from 10DLC profile: Lang Electric        │  ← text-caption text-neutral-400
└───────────────────────────────────────────────────┘
```

Annotation: `text-caption text-neutral-400` — "Default from 10DLC profile: {value}"

**State 2 — Overridden** (field value ≠ default value):

```
┌─ Display name * ─────────────────────────────────┐
│  [ Lang Electric LLC                       ]      │
│  [overridden]  Revert to profile default          │  ← pill + link
└───────────────────────────────────────────────────┘
```

- Override pill: `bg-brand-100 text-brand-700 rounded px-2 py-0.5 text-caption font-medium` — "overridden"
- Revert link: `text-caption text-brand-600 hover:text-brand-800 focus:outline-none focus:underline` — "Revert to profile default"
- Clicking "Revert to profile default" resets the field to the default value (client-side state only; persists on form save)

**State 3 — No default** (fields 2, 8): No annotation rendered.

### 7.4 Show Full Address Toggle + Home-Address Privacy Warning

The `show_full_address` toggle uses the `SettingControl` boolean toggle visual (h-6 w-11 switch, `bg-brand-600` when on, `bg-neutral-200` when off).

**Home-address privacy warning** (shown when the toggle is ON and the 10DLC profile's `hq_address_line1` will be published):

```
┌─ Warning (bg-alert-50, border-alert-200, rounded-md, p-3) ──────┐
│  [ExclamationTriangleIcon solid, w-5 h-5, text-alert-600]        │
│  Your street address and ZIP will be public. If your business    │
│  address is your home address, consider keeping this off — the   │
│  city and state are always shown and are sufficient for TCR      │
│  vetting.                                                        │
└──────────────────────────────────────────────────────────────────┘
```

| Property | Value | Token / Class |
|---|---|---|
| Container | `bg-alert-50 border border-alert-200 rounded-md p-3 mt-2` | — |
| Icon | `ExclamationTriangleIcon` (Heroicons 2.0, solid) | `w-5 h-5 text-alert-600 shrink-0` |
| Text | Warning copy (above) | `text-sm text-alert-700` |
| Layout | `flex items-start gap-2` | — |

### 7.5 Slug Field — See §8 (SlugAvailabilityInput)

The slug field is a specialized component with live availability feedback — specced separately in §8.

### 7.6 Form Actions

| Button | Style | Token classes | Behavior |
|---|---|---|---|
| Save Draft | Primary | `bg-brand-600 text-white rounded-md px-4 py-2 text-sm font-medium hover:bg-brand-700 focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2 disabled:opacity-50` | Calls `useUpsertTenantSite`. Disabled when no changes. Shows "Saving…" when pending. |
| Discard Changes | Secondary | `border border-neutral-300 text-neutral-700 rounded-md px-4 py-2 text-sm font-medium hover:bg-neutral-50 focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2` | Resets form to last-saved state. Disabled when no changes. |

**Layout**: `flex justify-end gap-3` at the bottom of the form container.

**Success/error feedback**: After save, a `NotificationBanner` toast (`severity: "success"`, title "Draft saved", auto-dismiss 6s) appears via the notification queue. On error, `severity: "error"`, title "Failed to save draft", auto-dismiss 12s.

---

## 8. Pixel Specs — SlugAvailabilityInput

### 8.1 Overview

The slug input provides real-time availability feedback as the tenant types. It calls `GET /api/v1/tenant-site/slug-availability?slug=` (§D-3) with a **300ms debounce**. The response shape is `{ available: bool, reason?: 'taken'|'invalid'|'reserved', suggestion? }`.

### 8.2 Input Field

| Property | Value | Token / Class |
|---|---|---|
| Label | "Site URL slug" | `text-sm font-medium text-neutral-700 mb-1` |
| Required indicator | `*` in `text-alert-600` | — |
| Input | text, lowercase enforced, `maxLength=63` | `w-full rounded-md border px-3 py-2 text-sm text-neutral-900 focus:ring-2 focus:ring-brand-500 focus:border-brand-500` |
| Border color (default) | `border-neutral-300` | `border-neutral-300` |
| Border color (available) | `border-margin-400` | `border-margin-400` |
| Border color (taken/invalid/reserved) | `border-fault-400` | `border-fault-400` |
| Prefix | `{slug}.p4tsites.com` — the slug input is inline within a URL display | See §8.3 |
| Helper text (default) | "Lowercase letters, numbers, and hyphens. Must start and end with a letter or number." | `text-xs text-neutral-500 mt-1` |
| HelpAnchor | Contextual "?" next to the label | `<HelpAnchor context={{ surface: "settings-website", field: "slug" }} />` |

### 8.3 URL Display Layout

```
┌─ Site URL slug * ────────────────────────────────── [?] ─┐
│                                                            │
│  ┌──────────────────────────────────────────────────────┐ │
│  │ https:// [lang-electric        ] .p4tsites.com        │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                            │
│  Lowercase letters, numbers, and hyphens...                │
│                                                            │
│  [✓ Available]  ← status feedback (below input)            │
└────────────────────────────────────────────────────────────┘
```

| Property | Value | Token / Class |
|---|---|---|
| URL container | `flex items-center rounded-md border border-neutral-300 focus-within:ring-2 focus-within:ring-brand-500 focus-within:border-brand-500` | — |
| "https://" prefix | `px-3 py-2 text-sm text-neutral-500 bg-neutral-50 border-r border-neutral-200 rounded-l-md` | — |
| Slug input | `flex-1 px-3 py-2 text-sm text-neutral-900 outline-none bg-white lowercase` (no border — the container provides it) | — |
| ".p4tsites.com" suffix | `px-3 py-2 text-sm text-neutral-500 bg-neutral-50 border-l border-neutral-200 rounded-r-md` | — |

> **Note**: The domain `p4tsites.com` is read from `NEXT_PUBLIC_TENANT_SITES_DOMAIN` env var — never hardcoded. The suffix displays the env value.

### 8.4 Availability Feedback States

The feedback appears below the input, replacing the helper text when a check is in-flight or has a result.

| State | Trigger | Visual | Token classes |
|---|---|---|---|
| **Idle** (empty input) | Slug is empty | Helper text only | `text-xs text-neutral-500` |
| **Checking** | Debounce in-flight, query loading | `Spinner` (w-4 h-4) + "Checking availability…" | `text-xs text-neutral-500` + `animate-spin` spinner |
| **Available** | `{ available: true }` | `CheckIcon` (solid, w-4 h-4) + "Available" | `text-xs text-margin-700` + icon `text-margin-600` |
| **Taken** | `{ available: false, reason: "taken" }` | `XMarkIcon` (solid, w-4 h-4) + "This slug is taken" + suggestion link | `text-xs text-fault-600` + icon `text-fault-500` |
| **Reserved** | `{ available: false, reason: "reserved" }` | `XMarkIcon` + "This slug is reserved" | `text-xs text-fault-600` + icon `text-fault-500` |
| **Invalid** | `{ available: false, reason: "invalid" }` | `XMarkIcon` + "Invalid slug — use lowercase letters, numbers, and hyphens only" | `text-xs text-fault-600` + icon `text-fault-500` |
| **Suggestion** | `{ suggestion: "..." }` (accompanies taken/invalid) | "Try: {suggestion}" as a clickable link that fills the input | `text-xs text-brand-600 hover:text-brand-800 underline cursor-pointer` |

**Suggestion interaction**: Clicking "Try: {suggestion}" sets the slug input value to the suggestion and triggers a new availability check.

### 8.5 Slug Immutability After Publish

When the site has been published at least once (`status === 'published'` or `published_at !== null`), the slug field becomes **read-only**:

| Property | Value | Token / Class |
|---|---|---|
| Input | `readOnly` | `bg-neutral-50 text-neutral-500 cursor-not-allowed` |
| Lock icon | `LockClosedIcon` (Heroicons 2.0, outline, w-4 h-4) | `text-neutral-400` |
| Helper text | "Slug is locked after first publish. Contact support to change it." | `text-xs text-neutral-500` |

### 8.6 Debounce Implementation Note

The `useSlugAvailability` hook uses a 300ms debounce. TanStack Query `staleTime: 0` (always refetch on new value), `retry: false`. The hook cancels in-flight queries when the slug changes (TanStack Query v5 automatic cancellation on new query key).

---

## 9. Pixel Specs — SitePreviewPanel (§16.7 Preview-Before-Publish)

### 9.1 Overview

Before publishing, the tenant sees a full preview of exactly what will go public. This is a **server-data-driven preview** of the snapshot payload — NOT an iframe to the draft site (the draft is not publicly accessible pre-publish per the task brief). The preview renders the same content structure the public site will serve, using the snapshot fields from the GET response (or a preview-mode snapshot built from current form state).

### 9.2 Preview Trigger

The "Preview" button appears in the "Preview & publish" section. Clicking it calls a preview function that builds the snapshot payload from the current form state (client-side, mirroring the backend `build_snapshot` logic) and renders it in the `SitePreviewPanel`.

> **Implementation note**: The preview is built client-side from the current form values (display_name, tagline, contact, city/state, address, body content from template). The locked SMS disclosure clauses (Privacy/Terms) are rendered from a client-side copy of the template text (same content as the backend `v1/` templates — the React Engineer includes the template text as a constant). This ensures the preview matches what the backend will snapshot at publish time. If the backend exposes a preview endpoint in a future batch, migrate to that — but C-B16 does not have one (§D lists no preview endpoint).

### 9.3 Panel Layout

```
┌─ Section: "Preview & publish" ──────────────────────────────────┐
│                                                                   │
│  ┌─ SitePreviewPanel (bg-white, rounded-xl, border, shadow-sm) ─┐ │
│  │                                                               │ │
│  │  ┌─ tab bar ──────────────────────────────────────────────┐  │ │
│  │  │  [ Landing ]  [ Privacy Policy ]  [ Terms of Service ]  │  │ │
│  │  └──────────────────────────────────────────────────────────┘  │ │
│  │                                                               │ │
│  │  ┌─ preview content (scrollable, max-h-[500px]) ──────────┐  │ │
│  │  │                                                           │  │ │
│  │  │  ┌─ accent bar (bg-brand-600, h-1.5, w-full) ─────────┐ │  │ │
│  │  │  └─────────────────────────────────────────────────────┘ │  │ │
│  │  │                                                           │  │ │
│  │  │  Lang Electric                          (H1, text-2xl)    │  │ │
│  │  │  Residential & commercial — Richmond, VA (tagline)        │  │ │
│  │  │                                                           │  │ │
│  │  │  📞 (804) 555-0142   ✉ tom@langelectric.example.com              │  │ │
│  │  │  📍 Richmond, VA                                          │  │ │
│  │  │                                                           │  │ │
│  │  │  ── divider ───────────────────────────────────────────  │  │ │
│  │  │                                                           │  │ │
│  │  │  About this business                                      │  │ │
│  │  │  [body paragraphs from template]                          │  │ │
│  │  │                                                           │  │ │
│  │  │  Privacy Policy · Terms of Service                        │  │ │
│  │  │                                                           │  │ │
│  │  │  ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ──    │  │ │
│  │  │  Hosted by Pilot for Trades →                             │  │ │
│  │  └───────────────────────────────────────────────────────────┘  │ │
│  │                                                               │ │
│  │  ┌─ preview note ─────────────────────────────────────────┐  │ │
│  │  │  [InformationCircleIcon outline, w-4 h-4, text-neutral-400]│  │
│  │  │  This is a preview of what will go public when you publish.│  │
│  │  │  The URL will be https://lang-electric.p4tsites.com        │  │
│  │  └───────────────────────────────────────────────────────────┘  │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  [Preview & Publish button →]                                     │
│                                                                   │
└───────────────────────────────────────────────────────────────────┘
```

### 9.4 Tab Bar

| Property | Value | Token / Class |
|---|---|---|
| Container | `flex border-b border-neutral-200` | — |
| Tab button | `px-4 py-2 text-sm font-medium` | — |
| Tab (active) | `text-brand-700 border-b-2 border-brand-600` | `text-brand-700 border-b-2 border-brand-600` |
| Tab (inactive) | `text-neutral-500 hover:text-neutral-700 border-b-2 border-transparent` | `text-neutral-500 hover:text-neutral-700 border-b-2 border-transparent` |
| Tab focus | `focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-inset` | — |
| `role` | `tab` (with `role="tablist"` container, `role="tabpanel"` content) | — |
| `aria-selected` | `true` on active tab | — |

### 9.5 Preview Content

The preview content renders the snapshot payload using the **same visual treatment** as the public site (per the companion marketing spec `mkt-c-b16-design-spec.md` §5). This ensures the tenant sees exactly what TCR vets will see.

| Element | Treatment | Token / Class |
|---|---|---|
| Accent bar | `h-1.5 w-full bg-brand-600` | `bg-brand-600` |
| Business name (H1) | `text-2xl font-bold text-neutral-800` | (matches marketing spec §5.2) |
| Tagline | `text-body-lg text-neutral-600 mt-1` | — |
| Contact line | `text-body text-neutral-700` with `PhoneIcon`/`EnvelopeIcon`/`MapPinIcon` (Heroicons 2.0, outline, w-4 h-4, `text-neutral-400`) | — |
| Divider | `border-t border-neutral-200` | — |
| About heading (H2) | `text-h2 font-medium text-neutral-800 mb-4` | — |
| Body paragraphs | `text-body-lg text-neutral-700 space-y-4` | — |
| Legal links | `text-body text-brand-600 hover:text-brand-800 underline` (non-clickable in preview — display only) | — |
| Hosted-by footer | `text-caption text-neutral-400` + link `text-neutral-500` | — |

**Privacy/Terms tabs**: Render the `body_paragraphs` from the template (the locked SMS disclosure clauses). Same `text-body-lg text-neutral-700 space-y-4` treatment as the marketing spec §6.

### 9.6 Preview Note

| Property | Value | Token / Class |
|---|---|---|
| Container | `bg-neutral-50 border border-neutral-200 rounded-md p-3 mt-4` | — |
| Icon | `InformationCircleIcon` (Heroicons 2.0, outline) | `w-4 h-4 text-neutral-400 shrink-0` |
| Text | "This is a preview of what will go public when you publish. The URL will be https://{slug}.{domain}" | `text-xs text-neutral-600` |
| Layout | `flex items-start gap-2` | — |

### 9.7 Publish Button

| Property | Value | Token / Class |
|---|---|---|
| Label | "Preview & Publish" | — |
| Style | Primary CTA | `bg-brand-600 text-white rounded-md px-6 py-2.5 text-sm font-medium hover:bg-brand-700 focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2 disabled:opacity-50` |
| Disabled when | Form has validation errors, or slug is unavailable, or required fields missing | — |
| Click behavior | Opens `<PublishConfirmDialog>` (§10) | — |
| Layout | `flex justify-end mt-4` | — |

---

## 10. Pixel Specs — PublishConfirmDialog + 409 Overwrite Branch

### 10.1 Overview

The publish flow has two branches:
1. **Normal publish** — no tenant-entered URL in the 10DLC profile (or URL is empty/already ours). The confirm dialog shows the preview summary + a single confirm button.
2. **Overwrite-confirm (409)** — a tenant-entered URL exists in the 10DLC profile. The publish call returns 409 `website_overwrite_requires_confirmation` with `{ current_url, new_url, brand_status }`. The dialog shows current vs. new URL + an explicit confirm checkbox before the re-call with `confirm_website_overwrite=true`.

### 10.2 Normal Publish Confirm Dialog

| Property | Value | Token / Class |
|---|---|---|
| Overlay | `fixed inset-0 bg-neutral-900/50 z-50` | `bg-neutral-900/50` |
| Modal panel | `bg-white rounded-lg shadow-xl max-w-lg w-full mx-auto mt-16 p-6` | — |
| Close button | `XMarkIcon` (Heroicons 2.0, outline, w-5 h-5) top-right | `text-neutral-400 hover:text-neutral-600` with 44×44px hit area (`p-2 -m-2`) |
| Title | "Publish your compliance site" | `text-h2 font-semibold text-neutral-900` |
| Body | Summary of what will happen: "Your site will go live at https://{slug}.{domain}. The URL will be saved to your 10DLC profile for carrier vetting." | `text-body text-neutral-600 mt-2` |
| Preview thumbnail | A compact recap of the preview (business name + URL) | `bg-neutral-50 border border-neutral-200 rounded-md p-3 mt-4` |
| Confirm button | "Publish" | `bg-brand-600 text-white rounded-md px-4 py-2 text-sm font-medium hover:bg-brand-700 focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2` |
| Cancel button | "Cancel" | `border border-neutral-300 text-neutral-700 rounded-md px-4 py-2 text-sm font-medium hover:bg-neutral-50 focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2` |
| Button layout | `flex justify-end gap-3 mt-6` | — |
| `isPublishing` | Shows "Publishing…" and disables buttons | `disabled:opacity-50` |

### 10.3 409 Overwrite-Confirm Dialog (§G-16)

When the publish call returns 409 `website_overwrite_requires_confirmation`, the dialog switches to the overwrite-confirm variant. The 409 payload provides `{ current_url, new_url, brand_status }`.

```
┌─ Publish your compliance site ─────────────────────────── [X] ─┐
│                                                                  │
│  [ExclamationTriangleIcon solid, w-6 h-6, text-alert-600]        │
│                                                                  │
│  This will replace the website URL on your 10DLC profile.        │
│                                                                  │
│  ┌─ Current URL (bg-neutral-50, rounded-md, p-3) ──────────────┐ │
│  │  Current:  https://langelectric.example.com                          │ │
│  │  New:      https://lang-electric.p4tsites.com                │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  [BrandStateNotice inline — §11, brand_status from 409 payload]  │
│                                                                  │
│  ┌─ Confirm checkbox ──────────────────────────────────────────┐ │
│  │  ☐ I understand this replaces the URL on my 10DLC profile.   │ │
│  │     My carrier brand registration may need re-submission.    │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  [Cancel]                              [Confirm & Publish]        │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

| Property | Value | Token / Class |
|---|---|---|
| Warning icon | `ExclamationTriangleIcon` (Heroicons 2.0, solid, w-6 h-6) | `text-alert-600` |
| Warning text | "This will replace the website URL on your 10DLC profile." | `text-body text-neutral-900 font-medium` |
| URL comparison container | `bg-neutral-50 border border-neutral-200 rounded-md p-3 mt-4 space-y-2` | — |
| Current URL row | "Current:" label (`text-caption text-neutral-500`) + URL (`text-body text-neutral-900 font-mono`) | — |
| New URL row | "New:" label (`text-caption text-neutral-500`) + URL (`text-body text-neutral-900 font-mono`) | — |
| BrandStateNotice | Inline variant of §11, keyed to `brand_status` from the 409 payload | See §11 |
| Confirm checkbox | Standard checkbox + label | `flex items-start gap-2 mt-4` |
| Checkbox label | "I understand this replaces the URL on my 10DLC profile. My carrier brand registration may need re-submission." | `text-sm text-neutral-700` |
| Confirm button | "Confirm & Publish" — **disabled until checkbox is checked** | `bg-fault-600 text-white rounded-md px-4 py-2 text-sm font-medium hover:bg-fault-700 focus-visible:ring-2 focus-visible:ring-fault-500 focus-visible:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed` |
| Cancel button | "Cancel" | `border border-neutral-300 text-neutral-700 rounded-md px-4 py-2 text-sm font-medium hover:bg-neutral-50` |
| Button layout | `flex justify-end gap-3 mt-6` | — |

**Why the confirm button is `bg-fault-600` (destructive red)**: Overwriting a tenant-entered URL that an in-flight or approved brand registration references is a potentially disruptive action (re-vetting risk). The destructive button color signals the stakes, matching the design-system reference §7 destructive confirm modal pattern.

**Re-call behavior**: When the tenant confirms, the publish hook re-calls `POST .../publish` with `{ confirm_website_overwrite: true }`. On success, the dialog closes and a success `NotificationBanner` appears.

### 10.4 Publish Success Response Handling

The publish response includes `website_action` (`set` | `kept` | `overwritten`), `brand_status`, and `brand_guidance`. After a successful publish:

1. The `BrandStateNotice` (§11) updates to reflect the new `brand_status`.
2. A success `NotificationBanner` toast appears:
   - `website_action === "set"`: "Site published. URL saved to your 10DLC profile."
   - `website_action === "kept"`: "Site published. Your existing profile URL was kept."
   - `website_action === "overwritten"`: "Site published. Profile URL updated to your hosted site."
3. The option card status badge updates to "Published" (`bg-margin-100 text-margin-700`).
4. The slug field becomes read-only (§8.5).

---

## 11. Pixel Specs — BrandStateNotice (§G-17)

### 11.1 Overview

The `BrandStateNotice` is a persistent inline banner that sequences the tenant's next steps relative to their 10DLC brand registration status. It appears at the top of the page (below the page header) and updates after publish/unpublish. The `brand_status` value comes from the GET response and the publish response.

### 11.2 Four State-Keyed Variants

Each variant has a distinct color treatment, icon, title, and body — but **all pair color with a text label** (never color-only, per WCAG 1.4.1).

#### Variant 1: `none` / `draft` — "New URL on first submission"

| Property | Value | Token / Class |
|---|---|---|
| Container | `bg-brand-50 border border-brand-200 rounded-lg p-4` | `bg-brand-50 border-brand-200` |
| Icon | `InformationCircleIcon` (Heroicons 2.0, solid, w-5 h-5) | `text-brand-600` |
| Title | "Ready for brand submission" | `text-sm font-semibold text-brand-700` |
| Body | "Your hosted site URL will be used when you submit your 10DLC brand registration. No action needed yet — publish your site, then complete your brand registration from Messaging Setup." | `text-sm text-brand-700 mt-1` |
| Deep link | "Go to Messaging Setup →" | `text-sm text-brand-600 hover:text-brand-800 underline` → `/settings/messaging` |

#### Variant 2: `in-flight` — "Vet checks OLD URL; advise waiting"

| Property | Value | Token / Class |
|---|---|---|
| Container | `bg-alert-50 border border-alert-200 rounded-lg p-4` | `bg-alert-50 border-alert-200` |
| Icon | `ClockIcon` (Heroicons 2.0, solid, w-5 h-5) | `text-alert-600` |
| Title | "Brand registration in progress" | `text-sm font-semibold text-alert-700` |
| Body | "Your 10DLC brand is currently being vetted by the carrier. The vetting process checks the URL already on file — publishing a new URL now will not update the in-flight review. Wait for the vetting outcome, then re-submit your brand from Messaging Setup if needed." | `text-sm text-alert-700 mt-1` |

#### Variant 3: `brand_rejected` — "Publish then re-submit from Messaging settings"

| Property | Value | Token / Class |
|---|---|---|
| Container | `bg-fault-50 border border-fault-200 rounded-lg p-4` | `bg-fault-50 border-fault-200` |
| Icon | `ExclamationCircleIcon` (Heroicons 2.0, solid, w-5 h-5) | `text-fault-600` |
| Title | "Brand registration was rejected" | `text-sm font-semibold text-fault-600` |
| Body | "Your 10DLC brand registration was rejected. If the rejection was due to website content, publish your hosted compliance site (which includes all required SMS disclosure language), then re-submit your brand from Messaging Setup." | `text-sm text-fault-600 mt-1` |
| Deep link | "Go to Messaging Setup →" | `text-sm text-fault-600 hover:text-fault-700 underline font-medium` → `/settings/messaging` |

> **This is the recovery path** for Tom's failed-registration scenario (§G-17). The tenant publishes the hosted site (which has the compliant Privacy/Terms pages), then re-submits the brand from the existing C-B9 Messaging UI.

#### Variant 4: `active` / `approved` — "Live brand references old URL; re-vetting warning"

| Property | Value | Token / Class |
|---|---|---|
| Container | `bg-alert-50 border border-alert-200 rounded-lg p-4` | `bg-alert-50 border-alert-200` |
| Icon | `ExclamationTriangleIcon` (Heroicons 2.0, solid, w-5 h-5) | `text-alert-600` |
| Title | "Your brand is live — updating the URL may trigger re-vetting" | `text-sm font-semibold text-alert-700` |
| Body | "Your 10DLC brand is approved and currently references the URL on file. Publishing a new URL and updating your profile may cause the carrier to re-vet your brand. Proceed with caution — if your current URL is working, consider keeping it." | `text-sm text-alert-700 mt-1` |

### 11.3 Layout

| Property | Value | Token / Class |
|---|---|---|
| Container | `flex items-start gap-3` | — |
| Icon | `shrink-0 mt-0.5` | — |
| Content | `flex-1` | — |
| Title + body | `space-y-1` | — |
| Deep link | `mt-2` (when present) | — |
| `role` | `status` (not `alert` — this is persistent guidance, not a dynamic announcement) | — |
| `aria-live` | `polite` (updates after publish/unpublish) | — |

### 11.4 When No Brand Registration Exists

When `brand_status` is `none` (no `tenant_messaging_registration` row), Variant 1 renders. This is the default state for new tenants.

---

## 12. Pixel Specs — WebsiteRequirementsPanel + SelfHostEmailNotice (§G-19/20)

### 12.1 WebsiteRequirementsPanel Overview

The strong TCR-requirements warning shown wherever a self-managed URL is entered. It appears in two places:
1. **On this page** — inside the Option 1 (Compliance Kit) card when Option 1 is selected
2. **In the C-B9 10DLC profile form** — below the `website` field when the tenant enters a non-Pilot URL (§14)

### 12.2 Panel Layout

```
┌─ WebsiteRequirementsPanel (bg-alert-50, border-alert-200, rounded-lg, p-4) ─┐
│                                                                                │
│  [ShieldExclamationIcon solid, w-6 h-6, text-alert-600]                        │
│                                                                                │
│  TCR 10DLC Website Requirements                                                │
│                                                                                │
│  To pass carrier vetting, your website must include:                           │
│                                                                                │
│  • A landing page with your business name and contact info visible             │
│  • A Privacy Policy page with SMS disclosure clauses (message types,           │
│    frequency, message and data rates notice, STOP/HELP opt-out, no             │
│    third-party mobile sharing)                                                 │
│  • A Terms of Service page with SMS terms                                      │
│  • All pages accessible at a public URL (no login required)                    │
│  • Pages that load on mobile devices                                           │
│                                                                                │
│  [Download Requirements Guide (PDF) →]   [SelfHostEmailNotice]                 │
│                                                                                │
└────────────────────────────────────────────────────────────────────────────────┘
```

### 12.3 Panel Spec

| Property | Value | Token / Class |
|---|---|---|
| Container | `bg-alert-50 border border-alert-200 rounded-lg p-4` | — |
| Icon | `ShieldExclamationIcon` (Heroicons 2.0, solid, w-6 h-6) | `text-alert-600 shrink-0` |
| Title | "TCR 10DLC Website Requirements" | `text-sm font-semibold text-alert-700` |
| Body | Requirements list (above) | `text-sm text-alert-700 mt-2 space-y-1` |
| List items | `flex items-start gap-2` with `CheckIcon` (outline, w-4 h-4, `text-alert-600`) or bullet | — |
| Layout | `flex items-start gap-3` (icon + content) | — |

### 12.4 Requirements Guide PDF Download Link

| Property | Value | Token / Class |
|---|---|---|
| Label | "Download Requirements Guide (PDF) →" | — |
| Element | `<a>` link to `/resources/tenant-website-requirements-v1.pdf` | — |
| Style | `inline-flex items-center gap-2 text-sm font-medium text-brand-600 hover:text-brand-800 underline focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2 rounded` | — |
| Icon | `DocumentArrowDownIcon` (Heroicons 2.0, outline, w-4 h-4) | `text-brand-600` |
| Target | `_blank` (opens PDF in new tab) | `target="_blank" rel="noopener noreferrer"` |
| Hit area | `py-1` for ≥24px target | — |

> **The PDF is a static committed asset** at `apps/web/public/resources/tenant-website-requirements-v1.pdf` (§G-20). The link is a direct static file path — no API call. The PDF layout is defined in the companion marketing spec §8.

### 12.5 SelfHostEmailNotice

The "Guide emailed on {date}" state shown when the one-time requirements email has been sent (§G-19). This is a **state display, not a resend button** — the email is one-time by design.

**State 1 — Email sent** (`requirements_emailed_at` is non-null):

```
┌─ SelfHostEmailNotice (bg-margin-50, border-margin-200, rounded-md, p-3) ──┐
│  [EnvelopeIcon solid, w-4 h-4, text-margin-600]                             │
│  Requirements guide emailed on August 14, 2026                               │
│  (The guide is always downloadable above — no need to resend.)              │
└──────────────────────────────────────────────────────────────────────────────┘
```

| Property | Value | Token / Class |
|---|---|---|
| Container | `bg-margin-50 border border-margin-200 rounded-md p-3 mt-3` | — |
| Icon | `EnvelopeIcon` (Heroicons 2.0, solid, w-4 h-4) | `text-margin-600 shrink-0` |
| Text | "Requirements guide emailed on {formatted date}" | `text-sm text-margin-700 font-medium` |
| Subtext | "(The guide is always downloadable above — no need to resend.)" | `text-xs text-margin-600 mt-0.5` |
| Layout | `flex items-start gap-2` | — |
| Date format | `MMMM D, YYYY` (e.g., "August 14, 2026") | — |

**State 2 — Email not yet sent** (`requirements_emailed_at` is null):

The `SelfHostEmailNotice` is not rendered. The email is sent automatically on the first self-host signal (Option 1 selection or a self-managed URL saved in the C-B9 profile). The panel shows only the PDF download link.

> **No resend button by design** (§G-19): The one-time email is guarded by `requirements_emailed_at`. There is no resend affordance to rate-limit. The PDF is always downloadable. This is a Tom simplification (2026-08-14) — do not add a resend button.

### 12.6 Panel Placement on This Page

The `WebsiteRequirementsPanel` (including `SelfHostEmailNotice` when applicable) appears **inside the Option 1 card body** when:
- Option 1 is the selected option, OR
- A self-managed (non-Pilot) URL exists in the 10DLC profile (regardless of which option is selected — the tenant needs to know the requirements either way)

When Option 2 is selected and no self-managed URL exists, the panel is hidden from this page (it lives in the C-B9 profile form instead — §14).

---

## 13. Pixel Specs — Unpublish Flow + Escalated Warning (§G-8)

### 13.1 Unpublish Button

When the site is published (`status === 'published'`), an "Unpublish" button appears in the "Preview & publish" section.

| Property | Value | Token / Class |
|---|---|---|
| Label | "Unpublish site" | — |
| Style | Destructive secondary | `border border-fault-300 text-fault-600 rounded-md px-4 py-2 text-sm font-medium hover:bg-fault-50 focus-visible:ring-2 focus-visible:ring-fault-500 focus-visible:ring-offset-2` |
| Position | Below the publish button, `mt-2` | — |
| Icon | `EyeSlashIcon` (Heroicons 2.0, outline, w-4 h-4) | `text-fault-600` |

### 13.2 Unpublish Confirm Dialog

```
┌─ Unpublish your compliance site ────────────────── [X] ─┐
│                                                            │
│  [ExclamationTriangleIcon solid, w-6 h-6, text-alert-600]  │
│                                                            │
│  Unpublishing takes your site offline. Visitors to         │
│  {slug}.p4tsites.com will see a "page not found" page.     │
│                                                            │
│  [Escalated warning — when brand is live and points        │
│   at our hosted URL]                                       │
│                                                            │
│  The URL on your 10DLC profile will NOT be cleared.        │
│  If your brand is live, the carrier may still check        │
│  this URL — an unreachable site could cause issues.        │
│                                                            │
│  [Cancel]              [Unpublish]                         │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

| Property | Value | Token / Class |
|---|---|---|
| Overlay | `fixed inset-0 bg-neutral-900/50 z-50` | — |
| Modal panel | `bg-white rounded-lg shadow-xl max-w-lg w-full mx-auto mt-16 p-6` | — |
| Close button | `XMarkIcon` (outline, w-5 h-5) with 44×44px hit area | `text-neutral-400 hover:text-neutral-600 p-2 -m-2` |
| Title | "Unpublish your compliance site" | `text-h2 font-semibold text-neutral-900` |
| Warning icon | `ExclamationTriangleIcon` (solid, w-6 h-6) | `text-alert-600` |
| Body | "Unpublishing takes your site offline. Visitors to {slug}.{domain} will see a 'page not found' page." | `text-body text-neutral-600 mt-2` |
| URL note | "The URL on your 10DLC profile will NOT be cleared. If your brand is live, the carrier may still check this URL — an unreachable site could cause issues." | `text-sm text-neutral-600 mt-3` |
| Confirm button | "Unpublish" | `bg-fault-600 text-white rounded-md px-4 py-2 text-sm font-medium hover:bg-fault-700 focus-visible:ring-2 focus-visible:ring-fault-500 focus-visible:ring-offset-2` |
| Cancel button | "Cancel" | `border border-neutral-300 text-neutral-700 rounded-md px-4 py-2 text-sm font-medium hover:bg-neutral-50` |

### 13.3 Escalated Warning (§G-8)

When the live brand points at our hosted URL (`brand_status === 'active'` and `website_auto_populated === true`), the dialog shows an **escalated warning** block above the URL note:

```
┌─ Escalated warning (bg-fault-50, border-fault-200, rounded-md, p-3) ──┐
│  [ExclamationCircleIcon solid, w-5 h-5, text-fault-600]                 │
│  Warning: Your live 10DLC brand references this URL. Unpublishing       │
│  will make the site unreachable — the carrier may flag this during      │
│  ongoing monitoring. Consider keeping the site published until you      │
│  have a replacement URL on your profile.                                 │
└──────────────────────────────────────────────────────────────────────────┘
```

| Property | Value | Token / Class |
|---|---|---|
| Container | `bg-fault-50 border border-fault-200 rounded-md p-3 mt-4` | — |
| Icon | `ExclamationCircleIcon` (Heroicons 2.0, solid, w-5 h-5) | `text-fault-600 shrink-0` |
| Text | Escalated warning copy (above) | `text-sm text-fault-600` |
| Layout | `flex items-start gap-2` | — |

### 13.4 Unpublish Response Handling

The unpublish response includes a `warning` string (§D-5). After successful unpublish:

1. The option card status badge updates to "Unpublished" (`bg-neutral-100 text-neutral-500`).
2. A `NotificationBanner` toast (`severity: "warning"`, title "Site unpublished", detail: the `warning` string from the response, auto-dismiss 6s) appears.
3. The `BrandStateNotice` updates if `brand_status` changed.

---

## 14. C-B9 10DLC Profile Form — WebsiteRequirementsPanel Placement

### 14.1 Overview

The `WebsiteRequirementsPanel` is also embedded in the existing C-B9 10DLC profile form (`TenantDlcProfileForm.tsx`) — specifically below the `website` field. The C-B9 form currently does NOT have a `website` field visible in the form (the profile GET returns it, but the PUT in the existing form doesn't include it). The Part A `on_profile_website_changed` hook (§F) touches the C-B9 PUT, so the React Engineer will add a `website` field to the form.

### 14.2 Website Field in the C-B9 Form

A new `website` field is added to `DlcProfileFormInner`, positioned after the Support Contact section and before the Submit button.

| Property | Value | Token / Class |
|---|---|---|
| Label | "Website URL" | `text-sm font-medium text-neutral-700 mb-1` |
| Helper text | "Your business website URL. Used for 10DLC carrier vetting. If you use our hosted compliance site, this is set automatically when you publish." | `text-xs text-neutral-500 mt-1` |
| Input | url, `maxLength=500` | Standard `INPUT_CLASS` from the existing form |
| Placeholder | "https://yourbusiness.com" | — |
| Value | `profile?.website ?? ""` | — |

### 14.3 WebsiteRequirementsPanel Placement

The `WebsiteRequirementsPanel` appears **below the website field** when the tenant enters a non-Pilot URL (a URL that does not match `*.{TENANT_SITES_BASE_DOMAIN}`).

**Condition**: Show the panel when the `website` field value is non-empty AND does not end with `.{TENANT_SITES_BASE_DOMAIN}`.

```
┌─ Website URL ──────────────────────────────────────┐
│  [ https://langelectric.example.com              ]          │
│  Your business website URL. Used for 10DLC...       │
│                                                      │
│  ┌─ WebsiteRequirementsPanel ─────────────────────┐ │
│  │  [ShieldExclamationIcon] TCR 10DLC Website...   │ │
│  │  ...requirements list...                         │ │
│  │  [Download Requirements Guide (PDF) →]           │ │
│  │  [SelfHostEmailNotice: "Guide emailed on ..."]   │ │
│  └──────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────┘
```

**When the URL is a Pilot-hosted URL** (ends with `.{TENANT_SITES_BASE_DOMAIN}`): The panel is hidden. A small info note appears instead: "This is your Pilot-hosted compliance site URL. It was set automatically when you published." (`text-xs text-neutral-500`)

### 14.4 SelfHostEmailNotice in the C-B9 Form

The `SelfHostEmailNotice` (§12.5) appears inside the `WebsiteRequirementsPanel` in the C-B9 form, same as on the Settings > Website page. The `requirements_emailed_at` value comes from the 10DLC profile GET response.

### 14.5 One-Time Email Trigger

When the tenant saves a non-Pilot URL in the C-B9 profile form (PUT), the backend triggers the one-time requirements email (§G-19) if `requirements_emailed_at IS NULL`. The frontend does NOT call a separate email endpoint — the email is sent as a side effect of the PUT. The `SelfHostEmailNotice` appears after the next GET refresh shows `requirements_emailed_at` is non-null.

---

## 15. State Coverage

### 15.1 Page-Level States

| State | Trigger | Visual Treatment |
|---|---|---|
| **Loading** | `useTenantSite` `isPending` | `<LoadingState type="inline" label="Loading website settings..." />` — skeleton matching the form layout (card-shaped placeholder blocks) |
| **Error** | `useTenantSite` `isError` | `<ErrorState type="server" title="Could not load website settings" description="Check your connection and try again." />` with retry button |
| **Empty (not configured)** | GET returns `{ configured: false, defaults: {...} }` | `<EmptyState>` variant: "You haven't set up a website yet. Choose an option below to satisfy TCR 10DLC website vetting." + the option cards are still shown below |
| **Populated** | GET returns `{ configured: true, ... }` | Full page render with option cards, form, preview/publish sections |

### 15.2 Option Card States

| State | Trigger | Visual |
|---|---|---|
| No option selected | `configured: false` | All cards unselected, no form/preview sections |
| Option 1 selected | `site_kind === 'compliance_kit'` | Option 1 card selected (ring + bg-brand-50), WebsiteRequirementsPanel visible in card, no hosted-site form |
| Option 2 selected (draft) | `site_kind === 'hosted_compliance'`, `status === 'draft'` | Option 2 card selected, hosted-site form visible, preview/publish visible, status badge "Draft" |
| Option 2 selected (published) | `status === 'published'` | Option 2 card selected, form visible (editable), preview/publish visible with "Unpublish" button, status badge "Published" |
| Option 2 selected (unpublished) | `status === 'unpublished'` | Option 2 card selected, form visible, preview/publish visible with "Publish" button (re-publish), status badge "Unpublished" |

### 15.3 Form States

| State | Trigger | Visual |
|---|---|---|
| Clean (no changes) | Form values === saved values | Save button disabled |
| Dirty (unsaved changes) | Any field changed | Save button enabled, "Discard Changes" button enabled |
| Saving | `useUpsertTenantSite` pending | Save button shows "Saving…", all inputs disabled |
| Save error | `useUpsertTenantSite` error | `NotificationBanner` error toast, inputs re-enabled |
| Save success | `useUpsertTenantSite` success | `NotificationBanner` success toast, form resets to clean |

### 15.4 Slug Availability States

See §8.4 — idle, checking, available, taken, reserved, invalid, suggestion.

### 15.5 Publish States

| State | Trigger | Visual |
|---|---|---|
| Idle | Not publishing | Publish button enabled (if form valid) |
| Confirm dialog open | User clicked Publish | `<PublishConfirmDialog>` open (§10) |
| 409 overwrite | Publish returned 409 | Dialog switches to overwrite-confirm variant (§10.3) |
| Publishing | `usePublishTenantSite` pending | Confirm button shows "Publishing…", all buttons disabled |
| Publish error (non-409) | `usePublishTenantSite` error | `NotificationBanner` error toast, dialog stays open |
| Publish success | `usePublishTenantSite` success | Dialog closes, success toast, status badge updates, BrandStateNotice updates |

### 15.6 BrandStateNotice States

See §11.2 — four variants keyed on `brand_status`: none/draft, in-flight, brand_rejected, active/approved.

---

## 16. Interaction Spec

### 16.1 Option Card Selection

| Element | State | Behavior |
|---|---|---|
| Option 1 card | default | `border-neutral-200 bg-white` |
| Option 1 card | hover | `border-neutral-300` (subtle) |
| Option 1 card | focus-visible | `ring-2 ring-brand-500` |
| Option 1 card | selected | `border-brand-500 ring-2 ring-brand-500 bg-brand-50` |
| Option 1 card | active (mouse down) | `ring-2 ring-brand-600` |
| Option 2 card | (same as Option 1) | — |
| Option 3 card | all states | `cursor-not-allowed`, not focusable, not clickable |

**Keyboard**: Cards are in a `role="radiogroup"` with `role="radio"` items. Arrow keys move between Option 1 and Option 2. Space/Enter selects. Option 3 is skipped (not focusable).

### 16.2 Form Inputs

All form inputs follow the design-system reference §5 pattern:

| Element | State | Behavior |
|---|---|---|
| Text input | default | `border-neutral-300` |
| Text input | focus-visible | `focus:ring-2 focus:ring-brand-500 focus:border-brand-500` |
| Text input | error | `border-fault-400 focus:ring-2 focus:ring-fault-500` |
| Text input | disabled | `bg-neutral-50 text-neutral-500 cursor-not-allowed` |
| Toggle (show_full_address) | default off | `bg-neutral-200` |
| Toggle | on | `bg-brand-600` |
| Toggle | focus-visible | `focus:ring-2 focus:ring-brand-500 focus:ring-offset-2` |
| Toggle | disabled | `opacity-50 cursor-not-allowed` |

### 16.3 Slug Input

| Element | State | Behavior |
|---|---|---|
| Slug input | typing | Lowercase enforcement (JS `toLowerCase()` on change), 300ms debounce before availability check |
| Slug input | available | `border-margin-400` + "✓ Available" feedback |
| Slug input | taken/invalid/reserved | `border-fault-400` + error feedback + suggestion link |
| Slug input | read-only (post-publish) | `bg-neutral-50 text-neutral-500 cursor-not-allowed` + lock icon |
| Suggestion link | hover | `text-brand-800` |
| Suggestion link | focus-visible | `ring-2 ring-brand-500` |
| Suggestion link | active | Fills input with suggestion, triggers new check |

### 16.4 Preview Tabs

| Element | State | Behavior |
|---|---|---|
| Tab | default | `text-neutral-500 border-b-2 border-transparent` |
| Tab | hover | `text-neutral-700` |
| Tab | focus-visible | `ring-2 ring-brand-500 ring-inset` |
| Tab | active | `text-brand-700 border-b-2 border-brand-600` |
| Tab | keyboard | Arrow Left/Right to move between tabs, Space/Enter to activate |

### 16.5 Publish/Unpublish Buttons

| Element | State | Behavior |
|---|---|---|
| Publish button | default | `bg-brand-600 text-white` |
| Publish button | hover | `bg-brand-700` |
| Publish button | focus-visible | `ring-2 ring-brand-500 ring-offset-2` |
| Publish button | disabled | `opacity-50 cursor-not-allowed` |
| Unpublish button | default | `border-fault-300 text-fault-600` |
| Unpublish button | hover | `bg-fault-50` |
| Unpublish button | focus-visible | `ring-2 ring-fault-500 ring-offset-2` |

### 16.6 Dialog Interactions

| Element | State | Behavior |
|---|---|---|
| Dialog overlay | click | Closes dialog (cancel) |
| Close (XMarkIcon) | click | Closes dialog (cancel) |
| Escape key | press | Closes dialog (cancel) |
| Confirm button (normal) | click | Calls publish, shows "Publishing…" |
| Confirm button (409) | click | Disabled until checkbox checked; calls publish with `confirm_website_overwrite: true` |
| Confirm checkbox (409) | change | Enables/disables confirm button |
| Cancel button | click | Closes dialog |

**Focus trap**: Dialog traps focus within the modal. On open, focus moves to the dialog title or first interactive element. On close, focus returns to the triggering button.

---

## 17. Animation Spec

### 17.1 Transitions

| Element | Property | Duration | Easing | Reduced-motion |
|---|---|---|---|---|
| Option card | `border-color, background-color` | 150ms | `ease-in-out` | No transition (instant) |
| Slug input border | `border-color` | 150ms | `ease-in-out` | No transition |
| Toggle switch | `background-color` | 200ms | `ease-in-out` | No transition |
| Toggle knob | `transform` | 200ms | `ease-in-out` | No transition (instant position change) |
| Tab indicator | `border-color` | 150ms | `ease-in-out` | No transition |
| Dialog overlay | `opacity` | 200ms | `ease-out` | No transition (instant appear) |
| Dialog panel | `opacity, transform (translateY -8px → 0)` | 200ms | `ease-out` | No transition (instant appear) |
| NotificationBanner | `opacity, transform (translateY -100% → 0)` | 300ms | `ease-out` | No transition |
| Slug availability spinner | `transform (rotate)` | 1000ms | `linear` (infinite) | No animation (static dot or text only) |

### 17.2 Reduced Motion

All transitions respect `prefers-reduced-motion: reduce`:

```css
@media (prefers-reduced-motion: reduce) {
  * {
    transition-duration: 0ms !important;
    animation-duration: 0ms !important;
    animation-iteration-count: 1 !important;
  }
}
```

The React Engineer applies this via Tailwind's `motion-reduce:` variant or the global reduced-motion media query. State changes are instant; no layout shift from removed transitions.

### 17.3 No Layout-Shift Animations

No animations change element dimensions (no `width` or `height` transitions). All transitions are color/opacity/transform only — this prevents layout shift during state changes.

---

## 18. Component Manifest

Reconciliation against design doc §I (Web Part B — `apps/web/src/features/tenant-site/`). Every component listed in §I is accounted for. No orphan components. No new `@pilot/ui` shared components (confirmed in §4).

### 18.1 Route File

| File (per §I) | Purpose | Spec Section |
|---|---|---|
| `apps/web/src/app/(authed)/settings/website/page.tsx` | Thin server component. Renders `<TenantSiteSettingsForm />` inside the settings shell. `RoleGate permission="settings.view"` at the page level. | §1, §6 |

### 18.2 Feature-Local Components (all in `apps/web/src/features/tenant-site/`)

| File (per §I) | Purpose | Spec Section | Shared barrel? |
|---|---|---|---|
| `TenantSiteSettingsForm.tsx` | Top-level client component. Manages `useTenantSite` loading/error/empty states. Renders option cards, form, preview/publish sections. `RoleGate permission="settings.manage"` wraps the form/action area. | §6, §7 | No — feature-local |
| `SiteOptionCard.tsx` | Selectable card for each website option (Compliance Kit, Hosted Site, Starter Site). Radio-group semantics. Status-aware. | §6.3 | No — feature-local |
| `SlugAvailabilityInput.tsx` | Slug input with URL prefix/suffix display, debounced availability check, feedback states (available/taken/reserved/invalid + suggestion), post-publish read-only. | §8 | No — feature-local |
| `SitePreviewPanel.tsx` | Server-data-driven preview of the snapshot payload. Tabbed (Landing/Privacy/Terms). Renders the same visual treatment as the public site. NOT an iframe. | §9 | No — feature-local |
| `PublishConfirmDialog.tsx` | Publish confirmation modal. Two branches: normal publish (§10.2) and 409 overwrite-confirm (§10.3). Shows current vs. new URL, BrandStateNotice inline, confirm checkbox for 409. | §10 | No — feature-local |
| `BrandStateNotice.tsx` | Persistent inline banner. Four state-keyed variants from `brand_status`: none/draft, in-flight, brand_rejected, active/approved. Color-independent status (color + text label + icon). | §11 | No — feature-local |
| `WebsiteRequirementsPanel.tsx` | Strong TCR-requirements warning. Requirements list + PDF download link + SelfHostEmailNotice. Reused in the C-B9 profile form (§14). | §12 | No — feature-local |
| `SelfHostEmailNotice.tsx` | "Guide emailed on {date}" state display. No resend button (one-time by design). | §12.5 | No — feature-local |
| `DefaultsAnnotatedField.tsx` | §16.5 visual-language wrapper for form fields with defaults-from-profile. State 1 (inheriting) / State 2 (overridden) annotations. Composes SettingControl's visual contract without its save machinery. | §7.3 | No — feature-local |

### 18.3 Hooks (all in `apps/web/src/features/tenant-site/hooks/`)

| File (per §I) | Purpose | Spec Section |
|---|---|---|
| `useTenantSite.ts` | `GET /api/v1/tenant-site` — TanStack Query, `retry: false`, `apiClient` | §1.3 |
| `useUpsertTenantSite.ts` | `PUT /api/v1/tenant-site` — mutation, `Idempotency-Key` header | §1.3, §7.6 |
| `usePublishTenantSite.ts` | `POST /api/v1/tenant-site/publish` — mutation, handles 409 branch, `Idempotency-Key` | §1.3, §10 |
| `useUnpublishTenantSite.ts` | `POST /api/v1/tenant-site/unpublish` — mutation, `Idempotency-Key` | §1.3, §13 |
| `useSlugAvailability.ts` | `GET /api/v1/tenant-site/slug-availability?slug=` — TanStack Query, 300ms debounce, `retry: false`, `staleTime: 0` | §1.3, §8 |

### 18.4 MSW Handlers

| File (per §I) | Purpose |
|---|---|
| `apps/web/src/mocks/handlers/tenant-site.ts` | MSW handlers for all 5 endpoints (GET, PUT, slug-availability, publish, unpublish) + 409 overwrite branch mock |
| `apps/web/src/mocks/handlers/index.ts` | **EDIT** — add tenant-site handlers to barrel |

### 18.5 Static Assets

| File (per §I) | Purpose | Spec Section |
|---|---|---|
| `apps/web/public/resources/tenant-website-requirements-v1.pdf` | Requirements Guide PDF (committed static asset, versioned filename) | §12.4 |
| `apps/web/public/resources/tenant-website-requirements-v1.md` | Markdown source for regeneration (Architect-authored content) | §12.4 |

### 18.6 Edited Files

| File | Change | Spec Section |
|---|---|---|
| `apps/web/src/features/settings/components/SettingsSidebar.tsx` | **EDIT** — add "Website" top-level item to `SIDEBAR_ITEMS` after "Branding", before "Voice & AI" | §5 |
| `apps/web/src/features/sms-compliance/components/TenantDlcProfileForm.tsx` | **EDIT** — add `website` field + `WebsiteRequirementsPanel` below it (conditional on non-Pilot URL) | §14 |

### 18.7 Orphan Check

**Result**: ✅ **No orphan components.** Every component maps to a file in design doc §I. The §I manifest lists: `TenantSiteSettingsForm`, `SiteOptionCard`, `SlugAvailabilityInput`, `SitePreviewPanel`, `PublishConfirmDialog` (incl. 409 branch), `BrandStateNotice`, `WebsiteRequirementsPanel`, `SelfHostEmailNotice` + hooks. This spec adds one additional feature-local component (`DefaultsAnnotatedField`) not explicitly named in §I — this is a designer-discretion presentational wrapper that composes the §16.5 visual language (§4.2). It is not a new top-level UX pattern and does not duplicate any locked component. **Flagged as a spec open item (§21-2)** for Tom's awareness.

### 18.8 Deviation from §I

| §I component | Spec deviation | Reason |
|---|---|---|
| §I lists `apps/web/src/features/tenant-site/` as the feature directory | This spec adds `DefaultsAnnotatedField.tsx` to that directory | §16.5 visual-language wrapper — designer discretion within the feature directory (per design standards §6 component placement rule) |
| §I does not list `DefaultsAnnotatedField` | Added in §18.2 | Composes SettingControl's visual contract without its locked save machinery (§4.2) — not a new top-level pattern |

No other deviations. All §I components are present and accounted for.

---

## 19. Implementation Notes

### 19.1 Environment Variables

| Variable | Where | Value |
|---|---|---|
| `NEXT_PUBLIC_TENANT_SITES_DOMAIN` | Web app | Dev: `localhost:3000`; QA/prod: the registered domain (e.g., `p4tsites.com`) |

The slug input suffix and the preview URL display read from this env var. Never hardcode the domain.

### 19.2 API Client & Query Configuration

- All hooks use `apiClient` (RULE 2 — never raw `fetch()`)
- TanStack Query `retry: false` on all hooks (per §I)
- Query keys: `["tenant-site", "config"]`, `["tenant-site", "slug-availability", slug]`
- Mutation invalidation: `useUpsertTenantSite` / `usePublishTenantSite` / `useUnpublishTenantSite` invalidate `["tenant-site", "config"]` on success

### 19.3 Idempotency Keys

All mutations (PUT, publish, unpublish) send an `Idempotency-Key` header (UUID v4 generated client-side). The backend has a 24h TTL (§D).

### 19.4 409 Overwrite-Confirm Flow

The `usePublishTenantSite` hook handles the 409 response:

```typescript
// Pseudocode for the React Engineer:
const publish = useMutation({
  mutationFn: (vars: { confirmWebsiteOverwrite?: boolean }) =>
    apiClient.post('/tenant-site/publish', {
      body: { confirm_website_overwrite: vars.confirmWebsiteOverwrite },
      headers: { 'Idempotency-Key': crypto.randomUUID() },
    }),
  onError: (error) => {
    if (error.status === 409 && error.code === 'website_overwrite_requires_confirmation') {
      // Store the 409 payload (current_url, new_url, brand_status)
      // The UI switches PublishConfirmDialog to the overwrite-confirm variant
      setOverwritePayload(error.data);
    }
  },
});
```

The dialog's "Confirm & Publish" button calls `publish.mutate({ confirmWebsiteOverwrite: true })` with a **new** `Idempotency-Key` (the original key was consumed by the 409 response).

### 19.5 Preview Snapshot Construction

The `SitePreviewPanel` builds the preview client-side from the current form state. The template text (Privacy/Terms SMS clauses) is included as a client-side constant — the same content as the backend `v1/` templates. The React Engineer includes this as a TypeScript constant in the feature directory. If the backend adds a preview endpoint in a future batch, migrate to that.

### 19.6 Slug Availability Debounce

The `useSlugAvailability` hook:

```typescript
// Pseudocode:
function useSlugAvailability(slug: string) {
  const debouncedSlug = useDebounce(slug, 300); // 300ms debounce
  return useQuery({
    queryKey: ['tenant-site', 'slug-availability', debouncedSlug],
    queryFn: () => apiClient.get(`/tenant-site/slug-availability?slug=${debouncedSlug}`),
    enabled: debouncedSlug.length > 0,
    staleTime: 0, // always refetch on new value
    retry: false,
  });
}
```

### 19.7 Brand Status Source

The `brand_status` value comes from:
1. The `GET /api/v1/tenant-site` response (initial load)
2. The `POST /api/v1/tenant-site/publish` response (after publish)
3. The 409 `website_overwrite_requires_confirmation` payload (in the overwrite dialog)

The `BrandStateNotice` reads from the most recent source. After a successful publish, the publish response's `brand_status` updates the notice.

### 19.8 WebsiteRequirementsPanel Reuse

The `WebsiteRequirementsPanel` is a single component used in two places:
1. `apps/web/src/features/tenant-site/WebsiteRequirementsPanel.tsx` (this feature)
2. Imported by `apps/web/src/features/sms-compliance/components/TenantDlcProfileForm.tsx` (C-B9 form)

The component accepts props for the `requirements_emailed_at` date (to render `SelfHostEmailNotice`) and the PDF link path (always `/resources/tenant-website-requirements-v1.pdf`).

### 19.9 MSW Handlers

The MSW handlers mock all 5 endpoints. The publish handler includes a 409 branch mock that returns `website_overwrite_requires_confirmation` when the mock profile has a tenant-entered URL and `confirm_website_overwrite` is not set.

### 19.10 Settings Catalog Registration

If the settings catalog (`useSettingsCatalog`) includes the Website surface, add a catalog entry for discoverability via the `SettingsSidebarSearch`. The entry would have `subSurfacePath: "/settings/website"` and appropriate `dataType`/`validationRules`. The React Engineer checks whether the catalog is the right discovery mechanism for this surface (it may be a non-catalog settings page like the C-B9 SMS compliance page, which is not in the catalog).

---

## 20. Accessibility Notes

### 20.1 Color-Independent Status (WCAG 1.4.1)

Every status on this surface pairs color with a text label and/or icon:

| Status | Color | Text label | Icon |
|---|---|---|---|
| Option card selected | `bg-brand-50` + `ring-brand-500` | `aria-checked="true"` on radio | `CheckCircleIcon` (solid) |
| Slug available | `border-margin-400` | "Available" | `CheckIcon` (solid) |
| Slug taken | `border-fault-400` | "This slug is taken" | `XMarkIcon` (solid) |
| Published badge | `bg-margin-100 text-margin-700` | "Published" | — |
| Draft badge | `bg-neutral-100 text-neutral-700` | "Draft" | — |
| BrandStateNotice variants | `bg-alert-50` / `bg-fault-50` / `bg-brand-50` | Title text (e.g., "Brand registration in progress") | State-specific icon |
| Warning panels | `bg-alert-50` / `bg-fault-50` | Warning text | `ExclamationTriangleIcon` / `ShieldExclamationIcon` |

No status is communicated by color alone.

### 20.2 Target Sizes (WCAG 2.5.8 — ≥24×24px AA)

| Element | Target size | Meets 24×24px? |
|---|---|---|
| Option card (clickable area) | Full card (~140px+ tall, full width) | ✅ |
| Radio indicator | 24px (`w-6 h-6`) | ✅ |
| Form inputs | Full width, ~36px tall | ✅ |
| Toggle switch | 44px × 24px (`h-6 w-11`) | ✅ (width ≥24px) |
| Slug suggestion link | `py-1` + text → ~28px tall | ✅ |
| Tab buttons | `px-4 py-2` → ~36px tall | ✅ |
| Publish/Unpublish buttons | `px-4 py-2` / `px-6 py-2.5` → ~36-40px tall | ✅ |
| Dialog close (XMarkIcon) | `p-2 -m-2` → 44×44px hit area around 20px icon | ✅ |
| PDF download link | `py-1` + text → ~28px tall | ✅ |
| HelpAnchor "?" | Inherited from the locked component (≥24×24px per FE-B16) | ✅ |
| "Revert to profile default" link | `text-caption` + `py-0.5` → ~20px ⚠ | **Add `py-1` for 28px** |

> **Note for the React Engineer**: The "Revert to profile default" link in `DefaultsAnnotatedField` should use `inline-block py-1` to achieve a 28px tap target (exceeds WCAG 2.5.8's 24px minimum).

### 20.3 Focus-Visible Rings (WCAG 2.4.11 — Focus Not Obscured)

All interactive elements use `focus-visible:ring-2 focus-visible:ring-brand-500` (or `focus-visible:ring-fault-500` for destructive actions). Keyboard users get a visible ring; mouse users don't see a persistent ring on click.

**Sticky header consideration**: The `h-12` sticky header (48px) could obscure focused content when scrolling. The settings content area has `overflow-y-auto` and `scroll-margin-top: 80px` (or equivalent `scroll-mt-20`) on anchored sections to ensure focused elements are not hidden behind the header. The React Engineer applies `scroll-mt-20` to the section containers.

### 20.4 Form Labels (WCAG 3.3.2)

Every form field has a visible `<label>` above it (design-system reference §5). Placeholder-as-label is banned. Error text is `text-fault-600` and linked via `aria-describedby`:

```html
<label htmlFor="display-name" class="text-sm font-medium text-neutral-700 mb-1">
  Display name <span class="text-alert-600">*</span>
</label>
<input id="display-name" aria-describedby="display-name-error display-name-helper" ... />
<p id="display-name-helper" class="text-xs text-neutral-500 mt-1">...</p>
<p id="display-name-error" class="text-xs text-fault-600 mt-1" role="alert">...</p>
```

### 20.5 Dialog Focus Trap

`PublishConfirmDialog` and the unpublish dialog implement a focus trap:
- On open: focus moves to the dialog title (`tabIndex={-1}`) or the first interactive element
- Tab/Shift+Tab cycles within the dialog
- Escape key closes (cancel)
- On close: focus returns to the triggering button
- `aria-modal="true"` on the dialog panel
- `aria-labelledby` pointing to the dialog title

### 20.6 Radio Group Semantics

The option cards use `role="radiogroup"` with `role="radio"` items:
- `aria-checked="true"` on the selected card
- `aria-disabled="true"` on Option 3
- Arrow keys move between Option 1 and Option 2
- Option 3 is `tabIndex={-1}` (skipped in tab order)
- `aria-label` on each radio: the option name

### 20.7 BrandStateNotice ARIA

- `role="status"` (persistent guidance, not a dynamic alert)
- `aria-live="polite"` (announces updates after publish/unpublish without interrupting)
- The icon is `aria-hidden="true"` (decorative — the title text conveys the state)

### 20.8 Preview Tab Semantics

- `role="tablist"` on the tab container
- `role="tab"` on each tab button, `aria-selected` on active
- `role="tabpanel"` on the preview content, `aria-labelledby` pointing to the active tab
- Arrow Left/Right to move between tabs (WCAG 2.4.3 — predictable focus order)

### 20.9 Contrast Ratios

All token pairings are pre-validated per the design-system reference. Key pairings on this surface:

| Pairing | Contrast | Status |
|---|---|---|
| `text-neutral-900` on `bg-white` | 15.9:1 | ✅ AAA |
| `text-neutral-700` on `bg-white` | 10.3:1 | ✅ AAA |
| `text-neutral-600` on `bg-white` | 7.0:1 | ✅ AAA |
| `text-neutral-500` on `bg-white` | 4.8:1 | ✅ AA |
| `text-neutral-400` on `bg-white` | 2.6:1 | ⚠ Decorative/muted only — never used for essential info |
| `text-brand-600` on `bg-white` | 6.5:1 | ✅ AA |
| `text-brand-700` on `bg-brand-50` | 8.4:1 | ✅ AAA |
| `text-alert-700` on `bg-alert-50` | 8.9:1 | ✅ AAA |
| `text-alert-600` on `bg-alert-50` | 7.1:1 | ✅ AAA |
| `text-fault-600` on `bg-fault-50` | 7.7:1 | ✅ AAA |
| `text-margin-700` on `bg-margin-50` | 9.2:1 | ✅ AAA |
| `text-margin-600` on `bg-white` | 5.9:1 | ✅ AA |

The `text-neutral-400` (2.6:1) is used only for:
- Default-source annotations (supplemental, not essential — the field value itself is `text-neutral-900`)
- Placeholder text (supplemental — replaced by actual input)
- Contact icons in the preview (decorative, `aria-hidden="true"`)

No essential information relies on `text-neutral-400` alone.

### 20.10 Reduced Motion

All transitions respect `prefers-reduced-motion: reduce` (§17.2). State changes are instant. The slug availability spinner is replaced with a static "Checking…" text (no `animate-spin`).

### 20.11 Keyboard Navigation Order

1. Page header → HelpAnchor "?"
2. BrandStateNotice (if deep link present, it's focusable)
3. Option 1 card (radio)
4. Option 2 card (radio)
5. [Option 3 skipped — `tabIndex={-1}`]
6. Form fields (display name → tagline → phone → email → city → state → show_full_address toggle → slug)
7. Save Draft button
8. Discard Changes button
9. Preview tabs (Landing → Privacy → Terms)
10. Publish button
11. Unpublish button (when published)

Dialogs have their own focus order (trapped within the dialog).

---

## 21. Open Items for Tom

1. **Option 3 (Starter Site) treatment**: This spec renders Option 3 as a disabled-appearing card with "Coming in a future update" badge, `aria-disabled="true"`, `tabIndex={-1}`, and `cursor-not-allowed`. The card has a real description of what the starter site will be (not a bare "coming soon" string). **Confirm**: (a) this disabled card treatment, (b) omit Option 3 entirely from the page, or (c) a different treatment? (Task brief §2 explicitly flags this as an open question.)

2. **`DefaultsAnnotatedField` — additional component not in §I**: This spec adds a feature-local `DefaultsAnnotatedField.tsx` to compose the §16.5 visual language (default-source annotation + override pill) without using the locked `SettingControl` save machinery (which doesn't fit batch-save text fields). It is not a new top-level UX pattern — it's a presentational wrapper. **Confirm**: This addition is acceptable, or should the fields use `SettingControl` with `saveMode="group"` (requiring `useFormSaveStrategy` integration)?

3. **Preview snapshot construction**: The `SitePreviewPanel` builds the preview client-side from the current form state + a client-side copy of the template text (Privacy/Terms SMS clauses). C-B16 has no preview endpoint (§D). **Confirm**: Client-side preview construction is acceptable for C-B16, or should the Architect add a preview endpoint to Part A?

4. **Settings catalog registration**: Should the Website surface be discoverable via `SettingsSidebarSearch` (requiring a catalog entry in `useSettingsCatalog`), or is it a non-catalog settings page like the C-B9 SMS compliance page? **Confirm**: Add to catalog, or leave as a direct-nav-only page?

5. **"Revert to profile default" link target size**: The `DefaultsAnnotatedField` revert link uses `text-caption` (~16px text). This spec recommends `inline-block py-1` for a 28px tap target (exceeds WCAG 2.5.8's 24px). **Confirm**: Apply `py-1` for 28px targets, or keep text-sized?

6. **Option switching confirmation**: When switching from Option 2 (published) to Option 1, this spec shows a confirmation dialog: "Switching to the Compliance Kit will not unpublish your hosted site." **Confirm**: This confirmation is needed, or should the switch be silent (the hosted site remains published until explicitly unpublished)?

7. **Slug immutability messaging**: The slug is immutable after first publish (§G-7). This spec shows a lock icon + "Contact support to change it." **Confirm**: Is there a support ticket flow, or should this say "Contact Pilot support" with a mailto link?

---

## 22. Handoff Gate

**⚠️ STOP. This design spec is complete. Do NOT implement any code.**

This spec goes to **Tom for approval**. Implementation (C-B16 Part B — React Engineer) starts only after Tom confirms this spec AND the companion marketing-ui-designer spec (`mkt-c-b16-design-spec.md`) are both approved.

**This spec is ready for Tom's review. Implementation starts only after approval.**

The React Engineer prompt (`batch-c-b16-react-engr-prompt.md`) will be authored only after Tom approves both this spec and the companion marketing spec, and after Part A (backend) merges + `pnpm sync-api-types` completes.
