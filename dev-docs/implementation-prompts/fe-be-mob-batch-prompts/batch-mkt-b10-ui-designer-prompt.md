# MKT-B10 Part A — Marketing UI Designer Prompt: Coming Soon Page

**Mode**: Pilot Marketing UI Designer  
**Batch**: MKT-B10 Part A  
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §P0 Marketing Website  
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-mkt-b10-design.md`  
**Estimate**: ~2 hours  
**Platform**: `frontend/apps/marketing/` (Next.js static export)  
**React Engineer companion**: `batch-mkt-b10-react-engr-prompt.md` — runs after Part A

---

## ⚠️ MANDATORY STOP: Read These First

Before designing anything, read:

- **`dev-docs/architecture-design/batch-designs/batch-mkt-b10-design.md`** — full design doc (§H Surface Mockup Reference is your brief)
- **`dev-docs/marketing-analysis/design-specs/mkt-coming-soon-design-spec.md`** — full architecture context
- **`frontend/apps/marketing/src/app/globals.css`** — all available CSS tokens (you MUST use only these tokens; do NOT invent new ones)

---

## Context

**Why this page exists**: When `profile-off.sh` runs (shutting down all AWS compute to save ~$510/month), the static marketing site at `pilotfortrades.com` remains live via S3/CloudFront but FastAPI is down. Marketing forms (waitlist, contact, careers) would return 502 errors. The Coming Soon page replaces the full marketing site in this state — a polished placeholder that shows the brand, explains what's coming, and captures leads via email link.

**How it's triggered**: A `site-config.json` file in S3 contains `{"mode": "coming_soon"}`. The marketing site reads this file client-side at page load and conditionally renders either the full site or the Coming Soon page. No rebuild required — just a file change in S3.

---

## Design Brief

Design a **full-page Coming Soon layout** for `apps/marketing/src/components/ComingSoonPage.tsx`.

### Required Elements (all mandatory)

1. **Hero section with brand blue gradient background**
   - Use `--gradient-hero-start` / `--gradient-hero-end` CSS tokens (same gradient as the homepage hero)
   - Full viewport height (`min-height: 100vh`)
   - Vertically centered content

2. **Product identity block**
   - Product name: **"Pilot for Trades"**
   - Tagline: **"AI-Powered Tools for Electrical Contractors"** (or a shorter variant that fits)
   - Logo treatment — consistent with the main site Header (check `Header.tsx` for current logo implementation)

3. **Value proposition** — one or two lines maximum
   - Suggest: *"Voice-controlled quoting, dispatch, and job tracking — built for the field."*
   - Must be ≤ 20 words, readable at a glance

4. **Optional custom message area** — a `<p>` tag that renders `props.message` if provided, otherwise shows a default: *"We're getting ready. Sign up to be first in line when we launch."*

5. **Single CTA button**
   - Label: **"Get Early Access"**
   - Action: `mailto:sales@pilotfortrades.com` link (no form submission — FastAPI is down)
   - Style: primary button using existing brand button tokens

6. **Minimal legal footer** (pinned to bottom or below content)
   - Copyright: `© 2026 Example Holdings, LLC. All rights reserved.`
   - Contact: `legal@pilotfortrades.com`
   - No other links, no nav

7. **Mobile-responsive** — single screen experience on 375px width (iPhone SE), no vertical scroll required

### NOT included (explicitly excluded)

- ❌ No navigation bar (Header component)
- ❌ No footer navigation links
- ❌ No marketing page content (no feature sections, pricing, blog, careers)
- ❌ No form inputs (no email field, no waitlist form) — FastAPI is down
- ❌ No new CSS variables — only tokens defined in `globals.css`
- ❌ No links to other marketing pages

---

## Design Deliverable

Produce a **complete, production-ready JSX component** for `ComingSoonPage.tsx` that:

1. Uses only CSS tokens from `apps/marketing/src/app/globals.css`
2. Accepts `props.message?: string`
3. Renders the mailto CTA without any onClick handler or API call
4. Is mobile-responsive (375px → 1440px)
5. Passes `pnpm --filter marketing build` without TypeScript errors

### Component signature:

```tsx
interface ComingSoonPageProps {
  message?: string;
}

export default function ComingSoonPage({ message }: ComingSoonPageProps) {
  // ...
}
```

### Visual style reference

Look at the homepage hero section in `apps/marketing/src/app/page.tsx` and the `globals.css` hero gradient classes for pattern reference. The Coming Soon page should feel like a single hero section — clean, confident, on-brand — rather than a stripped-down version of the full site.

---

## Existing CSS Tokens to Use

From `globals.css` — these are the relevant tokens for this page:

```css
/* Brand palette */
--brand-600          /* primary brand blue */
--brand-800          /* darker brand blue */
--gradient-hero-start
--gradient-hero-end
.hero-gradient       /* utility class for hero section background */

/* Text on blue backgrounds */
--white              /* #ffffff */
--white-95           /* 95% opacity white */
--white-85           /* 85% opacity white */

/* Shadows */
--shadow-lg
--shadow-xl

/* Button tokens (check existing button implementations for correct class names) */
```

---

## Output

Produce the complete JSX for `ComingSoonPage.tsx` as your deliverable. This file is handed directly to the React Engineer (Part B) who will place it at `apps/marketing/src/components/ComingSoonPage.tsx` and wire it into the `SiteModeGate`.

Also include a brief **design rationale** note (2–3 sentences) explaining your visual decisions for the Architect record.

---

## Definition of Done

- [ ] `ComingSoonPage.tsx` component produced with correct props interface
- [ ] Uses only CSS tokens from `globals.css` — no inline styles with hardcoded colors
- [ ] Mobile-responsive at 375px (iPhone SE) — single screen, no vertical scroll
- [ ] Mailto CTA uses `href="mailto:sales@pilotfortrades.com"` — no form, no API call
- [ ] No Header or Footer navigation components imported
- [ ] Design rationale note written
- [ ] Hand off `ComingSoonPage.tsx` to React Engineer (Part B)
