# Implementation Prompt: C-B13 — Marketing Site Charter Availability + Pricing Toggle UI Design Spec

**Mode**: Pilot Marketing UI Designer
**Batch**: C-B13 (Part B prerequisite — UI design spec must be Tom-approved before React Engineer prompt)
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §2.0 row 14r
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-c-b13-design.md` §H (Surface Mockup Reference), §I (Component Manifest)
**Estimated session**: 1–2 hours
**Platform**: Marketing site only (`apps/marketing`) — public-facing pages

---

## ⚠️ MANDATORY STOP: Read These First

Before producing any design, read:

- **`.roo/rules-pilot-marketing-ui-designer/marketing-conversion-ui.md`** — conversion UI rules (above-the-fold mandate, visual hierarchy, trust signals)
- **`.roo/rules-pilot-marketing-ui-designer/brand-consistency-guidelines.md`** — brand consistency (token consumption, UI mirroring, WCAG)
- **`dev-docs/architecture-design/batch-designs/batch-c-b13-design.md`** — §H (Surface Mockup Reference), §I (Component Manifest), §G (Open Questions Resolved)

Critical rules for this batch:

- **Design tokens**: The marketing site uses CSS custom properties (`var(--brand-600)`, `var(--neutral-900)`, etc.) — NOT `pilotPreset` Tailwind tokens (those are for the web app). Follow the existing pattern in the marketing site files.
- **WCAG compliance**: High contrast ratios, visible focus rings, semantic HTML.
- **No new hex codes**: Use the established CSS custom property palette.
- **Component-existence check**: The marketing site has its own component structure — check existing files before proposing new components.

---

## Pre-Work: Read These Source Files

Use `read_file` on each of these before designing:

```
frontend/apps/marketing/src/app/charter/page.tsx          ← why: the /charter page where availability display will be added
frontend/apps/marketing/src/app/pricing/page.tsx          ← why: the /pricing page where annual/monthly toggle + Charter callout will be added
frontend/apps/marketing/src/app/legal/terms/page.tsx      ← why: the legal terms page where D22 + D24 clauses will be added
frontend/apps/marketing/src/app/page.tsx                  ← why: the homepage — verify hero CTA in Charter mode
frontend/apps/marketing/src/app/globals.css               ← why: the CSS custom properties (design tokens) used across the marketing site
frontend/apps/marketing/src/lib/useSiteMode.ts            ← why: the mode-aware hook (Charter vs General Release)
```

Also run:
```bash
grep -rn "var(--brand\|var(--neutral\|var(--surface" frontend/apps/marketing/src/app/globals.css | head -30
grep -rn "btn-primary\|btn-secondary\|card-pricing" frontend/apps/marketing/src/app/ | head -10
```

---

## Background / Context

C-B13 completes the marketing site changes for the Charter program. The backend endpoint `GET /api/v1/public/charter-availability` → `{open: bool, remaining: int}` is live (Part A complete).

**Your task**: Produce a UI design spec for four surfaces:

1. **`/charter` page — availability display**: A small badge/banner showing "X spots remaining" — but ONLY when `remaining <= 8` (GTM §6.8 scarcity rule). When `remaining > 8` or `open == false`, show nothing (or a subtle "Charter program open" without a count).

2. **`/pricing` page — annual/monthly toggle**: The General Release pricing page currently shows static "or $41/mo billed annually" text. Replace with an interactive toggle (Monthly | Annual) that switches the displayed prices. In Charter mode, no toggle (single price $49/mo).

3. **`/pricing` page — Charter callout**: In Charter mode, add a callout banner on the pricing page linking to `/charter` (e.g., "Be one of the first twelve — 90 days free, then $49/mo locked").

4. **`/legal/terms` page — D22 + D24 clauses**: Add the Charter rate clause (D22: "Charter members' rate is locked for as long as they remain continuously subscribed. Canceling or upgrading to Teams forfeits the Charter rate permanently.") and the 10DLC pass-through disclosure (D24: "Carrier registration fees for 10DLC messaging are passed through at cost. Pilot does not mark up carrier fees.").

**Pricing data** (confirmed with Tom 2026-08-07):

| Plan | Monthly | Annual (total) | Annual effective/mo |
|---|---|---|---|
| Starter | $59/mo | $588/yr | $49/mo |
| Teams | $179/mo | $1,788/yr | $149/mo |
| Charter | $49/mo (locked) | N/A | N/A |

**Note**: The existing `/pricing` page shows "$49/mo or $41/mo billed annually" for Starter — this is WRONG (should be $59/mo or $49/mo billed annually). The toggle should display the correct prices.

---

## What to Design

### Surface 1: Charter Availability Display on `/charter`

**Route**: `/charter` (existing page)
**Placement**: Below the hero headline "Twelve spots. I'm filling them now." — a small availability badge

**Design requirements**:
- **When `open == true` and `remaining <= 8`**: Show "Only {remaining} spots remaining" in a subtle badge (e.g., `bg-alert-50 text-alert-700 border-alert-200` equivalent in CSS custom properties)
- **When `open == true` and `remaining > 8`**: Show nothing (or a very subtle "Charter program open" text without a count — per GTM §6.8, suppress the numeric counter until scarcity is real)
- **When `open == false`**: Show "Charter program is full" in a muted style
- **Loading state**: While fetching, show nothing (the badge appears only after data loads — no skeleton needed for such a small element)
- **Error state**: If the API fails, show nothing (fail silently — don't block the page)
- This is a **client component** (`"use client"`) — it fetches the availability endpoint on mount

### Surface 2: Annual/Monthly Toggle on `/pricing` (General Release mode)

**Route**: `/pricing` (existing page, General Release mode only)
**Placement**: Above the 2-column pricing cards

**Design requirements**:
- A segmented control with two options: "Monthly" and "Annual"
- Default: "Monthly" selected
- When "Monthly" is selected: Starter shows $59/mo, Teams shows $179/mo
- When "Annual" is selected: Starter shows $49/mo (billed $588/yr), Teams shows $149/mo (billed $1,788/yr)
- Selected option: `bg-brand-600 text-white` (or equivalent CSS custom property)
- Unselected: `bg-white text-neutral-600 border-neutral-200`
- Target size ≥24×24px for each option
- `role="radiogroup"` with `aria-label="Billing interval"`
- Smooth transition between price displays (fade or slide, 200ms, with `prefers-reduced-motion` fallback)
- This is a **client component** (`"use client"`) — the toggle is pure UI state, no API call

### Surface 3: Charter Callout on `/pricing` (Charter mode)

**Route**: `/pricing` (existing page, Charter mode only)
**Placement**: Below the single pricing card, before the FAQ

**Design requirements**:
- A callout banner: "Be one of the first twelve — 90 days free, then $49/month locked for as long as you stay."
- CTA button: "Join the Charter program" linking to `/charter`
- Style: `bg-brand-50 border-brand-100` (or equivalent), with `brand-700` text
- This is a **server component** (static content, no client-side state needed) — it renders only in Charter mode

### Surface 4: `/legal/terms` — D22 + D24 Clauses

**Route**: `/legal/terms` (existing page)
**Placement**: Add two new sections to the terms page

**D22 — Charter Rate Clause**:
> **Charter Rate.** Charter members receive a locked monthly rate of $49/month for as long as they remain continuously subscribed. This rate is locked at signup and does not change as long as the subscription remains active. Canceling the subscription or upgrading to the Teams plan permanently forfeits the Charter rate — it cannot be reinstated, even if the customer later returns to the Starter plan.

**D24 — 10DLC Pass-Through Disclosure**:
> **10DLC Carrier Fees.** Carrier registration fees for 10DLC (10-digit long code) messaging are passed through at cost. Pilot for Trades does not mark up, add margins to, or profit from carrier registration fees. These fees are set by the carrier (T-Mobile, AT&T, Verizon) and may change without notice. The customer is responsible for all carrier fees associated with their 10DLC messaging registration.

---

## Output

Produce the design spec at:
```
dev-docs/marketing-analysis/design-specs/mkt-c-b13-design-spec.md
```

Follow the output format from the marketing designer rules:
1. Surface overview (route, mode, who sees it)
2. Pixel specs (dimensions, padding, gap, border-radius)
3. CSS custom property colors (no hex codes — use `var(--token)` format)
4. State coverage (loading, empty, error, populated)
5. Interaction spec (hover, focus, active, disabled for every interactive element)
6. Animation spec (with `prefers-reduced-motion` fallback)
7. Component manifest (table of every new/modified file with path + description)
8. Implementation notes (hook names, endpoint URLs, client vs server component)
9. **Accessibility Notes** (contrast ratios, target sizes, focus order, ARIA roles)

**Component manifest** (from design doc §I — reconcile with your spec):

| Component | Destination | Purpose |
|---|---|---|
| `CharterAvailabilityBadge` | `apps/marketing/src/components/CharterAvailabilityBadge.tsx` (NEW) | Client component — fetches `/api/v1/public/charter-availability`, shows "X spots remaining" when `remaining <= 8` |
| `PricingToggle` | `apps/marketing/src/components/PricingToggle.tsx` (NEW) | Client component — annual/monthly segmented control for the General Release pricing page |
| `charter/page.tsx` (updated) | `apps/marketing/src/app/charter/page.tsx` | Add `CharterAvailabilityBadge` below hero headline |
| `pricing/page.tsx` (updated) | `apps/marketing/src/app/pricing/page.tsx` | Add `PricingToggle` (General Release mode) + Charter callout (Charter mode) |
| `legal/terms/page.tsx` (updated) | `apps/marketing/src/app/legal/terms/page.tsx` | Add D22 + D24 clauses |

---

## Handoff Gate

After producing the design spec, **STOP**. Do NOT implement any code. The design spec goes to Tom for approval. Implementation starts only after Tom confirms the spec is approved. State this explicitly at the end of the design spec output.

The React Engineer prompt (C-B13 Part B) will be authored only after Tom approves this spec.
