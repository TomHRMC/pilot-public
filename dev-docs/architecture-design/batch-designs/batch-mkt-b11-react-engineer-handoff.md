# MKT-B11-C2 — React Engineer Handoff Notes
## Site Mode Switch Implementation

**From:** Pilot Marketing UI Designer (MKT-B11-C1)  
**To:** Pilot React Engineer (MKT-B11-C2)  
**Date:** 2026-07-09  
**Status:** Design complete — ready for implementation  

---

## What Was Built (Designer Deliverables)

### Logo Assets (`/public/brand/`)
All 6 SVG logo files are production-ready in `frontend/apps/marketing/public/brand/`:

| File | Use case |
|------|----------|
| `logo-primary.svg` | Header, hero, email — light bg |
| `logo-icon.svg` | Favicon, app icon, small-space |
| `logo-wordmark.svg` | Header contexts without icon |
| `logo-primary-dark.svg` | Hero gradient, footer, dark sections |
| `logo-icon-dark.svg` | Dark nav, dark headers |
| `logo-wordmark-dark.svg` | Dark sections without icon |

### New Pages (complete TSX)
- `/sign-up/page.tsx` — General Release signup page (production-ready)
- `/pricing-general-release/page.tsx` — General Release pricing (merge into `/pricing/page.tsx` behind mode hook)

### Design Spec
Full component-by-component spec for all 12 affected areas:  
`batch-mkt-b11-ui-design-spec.md`

---

## Implementation Tasks for React Engineer

### Task 1: `useSiteMode()` Hook

Create `src/lib/use-site-mode.ts`:

```typescript
/**
 * Reads the active subscription tiers from the backend to determine site mode.
 * Returns "founders" when founders_plan is active, "general_release" when starter_plan is active.
 * Falls back to "founders" on error (safe default — never accidentally shows billing CTAs).
 */
"use client";

import { useEffect, useState } from "react";

export type SiteMode = "founders" | "general_release";

export function useSiteMode(): SiteMode {
  const [mode, setMode] = useState<SiteMode>("founders"); // safe default

  useEffect(() => {
    fetch("/api/v1/subscription-tiers?active_only=true")
      .then((r) => r.json())
      .then((tiers: Array<{ plan_key: string; is_active: boolean }>) => {
        const hasStarter = tiers.some(
          (t) => t.plan_key === "starter_plan" && t.is_active
        );
        if (hasStarter) setMode("general_release");
      })
      .catch(() => {
        // Fail closed: keep founders mode on any error
        setMode("founders");
      });
  }, []);

  return mode;
}
```

**Important:** The hook must be in a Client Component only. For Server Components (page.tsx files that are `async`), pass the mode as a prop from a Client Component wrapper.

---

### Task 2: `SiteModeCta` Component

Create `src/components/SiteModeCta.tsx` — a drop-in replacement for all CTA links across the site:

```typescript
"use client";

import Link from "next/link";
import { useSiteMode } from "@/lib/use-site-mode";

interface SiteModeCtaProps {
  className?: string;
  children?: never; // text is controlled by mode — do not pass children
}

export default function SiteModeCta({ className }: SiteModeCtaProps) {
  const mode = useSiteMode();

  return (
    <Link
      href={mode === "general_release" ? "/sign-up" : "/early-access"}
      className={className ?? "btn-primary"}
    >
      {mode === "general_release" ? "Start Free Trial" : "Be One of the First"}
    </Link>
  );
}
```

Usage in any component:
```tsx
<SiteModeCta className="btn-primary" />
<SiteModeCta className="btn-white" />
<SiteModeCta className="btn-primary w-full text-center" />
```

---

### Task 3: Header.tsx Update

**File:** `src/components/Header.tsx`

1. Replace the logo inline SVG (lines 39–55) with Next.js `<Image>`:
```tsx
import Image from "next/image";

// In the Link component replacing the SVG + span:
<Link href="/" aria-label="Pilot for Trades — Home">
  {/* Desktop: full lockup */}
  <Image
    src="/brand/logo-primary.svg"
    alt="Pilot for Trades"
    width={160}
    height={36}
    priority
    className="hidden sm:block"
  />
  {/* Mobile: icon only */}
  <Image
    src="/brand/logo-icon.svg"
    alt="Pilot for Trades"
    width={32}
    height={32}
    priority
    className="sm:hidden"
  />
</Link>
```

2. Replace the CTA button (line 149–153) with `<SiteModeCta>`:
```tsx
<div className="ml-4">
  <SiteModeCta className="btn-primary py-2 px-5 text-sm" />
</div>
```

3. Replace the mobile CTA button (lines 287–293):
```tsx
<div className="px-4 pt-3 pb-4">
  <SiteModeCta className="btn-primary w-full text-center" />
</div>
```

4. Do the same for the Footer logo (lines 64–81 in `Footer.tsx`) — use `logo-primary-dark.svg` (white variant).

---

### Task 4: Homepage CTA Updates

**File:** `src/app/page.tsx`

Convert the page to use a Client Component wrapper for mode-aware CTAs, or extract a `HomePageCtaSection` client component.

**Hero CTA (lines 157–167) — General Release adds caption:**
```tsx
"use client";
import { useSiteMode } from "@/lib/use-site-mode";

// Inside hero CTA section:
const mode = useSiteMode();

<div className="flex flex-col sm:flex-row gap-4">
  <SiteModeCta className="btn-primary" />
  <Link href="/features#voice-ai" className="text-base font-semibold no-underline flex items-center gap-2" style={{ color: "var(--white-8)" }}>
    See How It Works →
  </Link>
</div>
{mode === "general_release" && (
  <p className="text-caption-lg mt-3" style={{ color: "var(--white-7)" }}>
    14-day free trial · No credit card required
  </p>
)}
```

**Bottom CTA section (Section 9, lines 1042–1068) — update body copy:**
```tsx
<p className="text-body-lg mb-10 max-w-2xl mx-auto" style={{ color: "var(--white-8)" }}>
  {mode === "general_release"
    ? "Start your 14-day free trial today. No credit card required. Voice quoting, live margins, and smart dispatch — try it on a real job."
    : "Join contractors who are done with spreadsheet estimates, stale pricing, and flying blind on job profitability. Pilot gives you the tools — voice quoting, live margins, and smart dispatch — in one platform."
  }
</p>
<SiteModeCta className="btn-white" />
```

---

### Task 5: Pricing Page Merge

**File:** `src/app/pricing/page.tsx`

The General Release layout is fully built in `/pricing-general-release/page.tsx`.

Merge pattern:
```tsx
// pricing/page.tsx — convert to client component
"use client";
import { useSiteMode } from "@/lib/use-site-mode";
import PricingFounders from "./PricingFounders"; // extract current content
import PricingGeneralRelease from "../pricing-general-release/page";

export default function PricingPage() {
  const mode = useSiteMode();
  return mode === "general_release" ? <PricingGeneralRelease /> : <PricingFounders />;
}
```

**FAQ update for General Release:** Replace the "Is there a free trial?" answer:
```
New: "Yes — 14 days free on your chosen plan (Starter or Teams limits), no credit card required.
      After 14 days, continue at $49/month (Starter) or $149/month (Teams), or cancel anytime
      before your trial ends. No surprises."
```

---

### Task 6: New `/sign-up` Page

**File already created:** `src/app/sign-up/page.tsx`

This file is production-ready. The React Engineer needs to:
1. Verify `WaitlistForm` accepts `source="sign_up_page"` (check the prop type in `WaitlistForm.tsx`)
2. Confirm the button label inside `WaitlistForm` updates to "Start Free Trial" — if it doesn't accept a `submitLabel` prop, add one
3. Add the page to the sitemap in `src/app/sitemap.ts` — conditionally include `/sign-up` only in General Release mode (or always include it and redirect in Founders mode)

---

### Task 7: Footer Nav Update

**File:** `src/components/Footer.tsx`

Convert footer to Client Component (currently already `"use client"`). Update the Product column link:

```typescript
// In footerColumns, replace the static Early Access entry:
// Founders: { label: "Early Access", href: "/early-access" }
// General:  { label: "Start Free Trial", href: "/sign-up" }

// Implementation: use SiteModeCta or inline useSiteMode() in Footer:
const mode = useSiteMode();

const footerColumns = [
  {
    heading: "Product",
    links: [
      { label: "Features", href: "/features" },
      { label: "Pricing", href: "/pricing" },
      { label: "Trades", href: "/trades/electrical" },
      mode === "general_release"
        ? { label: "Start Free Trial", href: "/sign-up" }
        : { label: "Early Access", href: "/early-access" },
    ],
  },
  // ... rest unchanged
];
```

Also update the footer logo SVG (lines 64–81) to use `logo-primary-dark.svg`:
```tsx
<Image
  src="/brand/logo-primary-dark.svg"
  alt="Pilot for Trades"
  width={160}
  height={36}
/>
```

---

### Task 8: `TradePageTemplate.tsx` Updates

**File:** `src/components/trades/TradePageTemplate.tsx`

Add `useSiteMode()` and replace all three CTA instances with `<SiteModeCta>`. Update the pricing section body copy:

```tsx
{mode === "general_release" ? (
  <>
    <p>Starter at $49/month · Teams at $149/month</p>
    <p className="text-sm mt-1" style={{ color: "var(--neutral-600)" }}>
      14-day free trial — no credit card required.
    </p>
    <Link href="/pricing" className="text-sm font-medium" style={{ color: "var(--brand-600)" }}>
      See full pricing →
    </Link>
  </>
) : (
  <p>$49/month, everything included.</p>
)}
```

---

### Task 9: `BlogCta.tsx` Update

**File:** `src/components/blog/BlogCta.tsx`

The component already accepts `ctaLabel` and `ctaHref` props. Update the defaults via `useSiteMode()`:

```tsx
"use client";
import { useSiteMode } from "@/lib/use-site-mode";

export default function BlogCta({
  headline = "Ready to try voice quoting?",
  body = "Pilot builds estimates by voice — NEC-aware, real-time pricing, hands-free.",
  ctaLabel,
  ctaHref,
}: BlogCtaProps) {
  const mode = useSiteMode();
  const resolvedLabel = ctaLabel ?? (mode === "general_release" ? "Start Free Trial →" : "Be One of the First →");
  const resolvedHref = ctaHref ?? (mode === "general_release" ? "/sign-up" : "/early-access");

  return (
    <aside ...>
      ...
      <Link href={resolvedHref} className="btn-primary inline-flex" ...>
        {resolvedLabel}
      </Link>
      {mode === "general_release" && (
        <p className="text-caption-lg mt-2" style={{ color: "var(--brand-600)" }}>
          14 days free · No credit card
        </p>
      )}
    </aside>
  );
}
```

---

### Task 10: Remaining Pages (About, Contact, Features, Blog Listing)

For all remaining pages with CTAs — `/about`, `/contact`, `/features`, `/blog` — the same pattern applies:

1. Add `"use client"` directive (or extract a client wrapper component)
2. Call `useSiteMode()`
3. Replace hardcoded `href="/early-access"` and text `"Be One of the First"` with mode-conditional values

These are simple text/href swaps — no layout changes.

---

## Logo Swap Checklist

| Location | Current | Replace with |
|----------|---------|-------------|
| `Header.tsx` — logo mark | Inline SVG checkmark square | `logo-primary.svg` (light bg, 160×36) |
| `Header.tsx` — mobile | Inline SVG checkmark square | `logo-icon.svg` (32×32) |
| `Footer.tsx` — logo mark | Inline SVG checkmark square | `logo-primary-dark.svg` (160×36) |
| Favicon (`app/layout.tsx`) | Existing | `logo-icon.svg` as SVG favicon |
| OG image | N/A | Use `logo-primary.svg` in OG image generation |

---

## CSS Token Reference — New Additions

No new tokens were introduced. All new styles in the new pages and components reference existing `globals.css` variables:

| Style purpose | Token |
|--------------|-------|
| Hero caption subtext | `var(--text-caption-lg)`, `var(--white-7)` |
| Billing toggle active | `var(--brand-600)` |
| Annual savings badge | `var(--margin-50)` bg, `var(--margin-600)` text |
| Schedule lane callout bg | `var(--brand-50)` |
| Schedule lane callout border | `var(--divider-thin) solid var(--brand-100)` |
| Teams card featured border | `var(--divider-thick) solid var(--brand-600)` |
| Sign-up benefit cards bg | `var(--white-08)` |
| Sign-up benefit cards border | `var(--border-white-12)` |
| Blog CTA subtext (General) | `var(--brand-600)` |

---

## Animation / Transition Guidance

No new animations are introduced. Existing transitions apply:
- Annual toggle: `transition-colors` + `transition-transform` on the thumb (already in Tailwind)
- FAQ accordion: existing `transition: transform 0.2s` on chevron, conditional render (no CSS animation needed — matches existing pattern in `/pricing/page.tsx`)
- Mode switch: no animated transition between modes. The site simply renders the correct mode on initial load. No flash-of-wrong-mode mitigation is needed because `useSiteMode()` defaults to "founders" (the safe state) until the API responds.

---

## Testing Notes for QA

After implementation, verify:

1. **Founders Mode active:** All CTAs show "Be One of the First" → `/early-access`. `/sign-up` should redirect to `/early-access` (or 404 gracefully).
2. **General Release active:** All CTAs show "Start Free Trial" → `/sign-up`. `/early-access` can remain live but should not be promoted.
3. **DB flag flip:** Toggling `founders_plan.is_active = false` + `starter_plan.is_active = true` in the DB should update the site on next page load (no code deploy required).
4. **Logo:** Verify `logo-primary.svg` renders correctly in Header at 375px and 1440px. Verify `logo-primary-dark.svg` renders in Footer.
5. **Pricing page (General Release):** Annual toggle switches prices; both cards CTA links go to `/sign-up`.
6. **Sign-up page:** Form submits correctly with `source="sign_up_page"`.

---

## File Inventory (Designer Outputs)

```
frontend/apps/marketing/
├── public/brand/
│   ├── logo-primary.svg          ← NEW
│   ├── logo-icon.svg             ← NEW
│   ├── logo-wordmark.svg         ← NEW
│   ├── logo-primary-dark.svg     ← NEW
│   ├── logo-icon-dark.svg        ← NEW
│   ├── logo-wordmark-dark.svg    ← NEW
│   ├── logo-usage-guide.md       ← NEW (brand reference)
│   └── partner-submission-materials.md  ← NEW (Tom's submission doc)
└── src/app/
    ├── sign-up/
    │   └── page.tsx              ← NEW (General Release signup)
    └── pricing-general-release/
        └── page.tsx              ← NEW (merge into /pricing behind hook)

dev-docs/architecture-design/batch-designs/
├── batch-mkt-b11-ui-design-spec.md       ← NEW (full component spec)
└── batch-mkt-b11-react-engineer-handoff.md  ← THIS FILE
```
