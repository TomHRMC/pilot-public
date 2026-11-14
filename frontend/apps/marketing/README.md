# Pilot for Trades — Marketing Website

**Stack**: Next.js 16 (App Router, static export) · TypeScript · Tailwind CSS v4 · Cloudflare Turnstile
**Domain**: `pilotfortrades.com` — currently serves a static hold page; this site is not deployed
**Dev URL**: `http://localhost:3001` (default marketing dev server port)
**Purpose**: Public marketing site — homepage, features, pricing, trades pages, blog, careers, legal, waitlist/contact/application forms

> **Snapshot note — launch-draft copy.** This site was written for a launch that never happened and is included as source only. It describes the intended product, including features that were never finished (offline mode, offline voice processing), and contains pricing, Charter-signup and careers pages. Testimonials and job listings are labelled placeholders; no testimonial is from a real customer and no roles are open. Marketing and blog imagery is AI-generated; no real people are depicted. The live domain currently serves a static hold page. See [`PROVENANCE.md`](../../../PROVENANCE.md).

---

## Quick Start

```bash
cd frontend
pnpm --filter marketing dev        # start dev server on :3001
pnpm --filter marketing build      # production build
pnpm --filter marketing lint       # ESLint
pnpm --filter marketing exec tsc --noEmit   # TypeScript type check
```

---

## Project Structure

```
frontend/apps/marketing/
├── src/
│   ├── app/                        # Next.js App Router pages
│   │   ├── page.tsx                # Homepage
│   │   ├── features/page.tsx       # Features deep-dive
│   │   ├── pricing/page.tsx        # Pricing ($49/month)
│   │   ├── about/page.tsx          # About / founder story
│   │   ├── careers/page.tsx        # Careers + application form
│   │   ├── contact/page.tsx        # Contact Us form
│   │   ├── early-access/page.tsx   # Waitlist / Beta Founder signup
│   │   ├── blog/                   # Blog index + post pages
│   │   ├── trades/                 # Trade-specific landing pages
│   │   │   ├── electrical/
│   │   │   ├── plumbing/
│   │   │   └── hvac/
│   │   ├── legal/                  # Privacy, ToS, EULA, SMS Terms
│   │   └── sms-opt-in/             # SMS opt-in compliance page
│   ├── components/
│   │   ├── Header.tsx              # Sticky nav (white/frosted glass)
│   │   ├── Footer.tsx              # Footer with newsletter form
│   │   ├── HeroWaitlistForm.tsx    # Homepage hero inline waitlist
│   │   ├── WaitlistForm.tsx        # Full waitlist form (Early Access page)
│   │   ├── forms/
│   │   │   ├── ContactForm.tsx     # Contact Us form
│   │   │   ├── ApplicationForm.tsx # Careers application form (MKT-B6)
│   │   │   ├── NewsletterForm.tsx  # Footer newsletter signup
│   │   │   ├── WaitlistForm.tsx    # Waitlist (full version)
│   │   │   └── TurnstileProtectedForm.tsx  # Security wrapper for all forms
│   │   ├── blog/                   # Blog layout components
│   │   └── trades/
│   │       └── TradePageTemplate.tsx  # Shared template for all 3 trade pages
│   ├── content/
│   │   └── blog/                   # MDX blog post content
│   │       ├── electrical/
│   │       ├── plumbing/
│   │       ├── hvac/
│   │       ├── business/
│   │       └── product/
│   └── lib/
│       └── blog.ts                 # Blog post utilities
├── public/
│   ├── blog/                       # Blog hero images (10 × 1200×630 JPG)
│   ├── trades/                     # Trade hero images (3 × 1200×750 JPG)
│   ├── features/                   # Feature section images (11 × 800×500 JPG)
│   ├── about-hero.jpg              # About page illustration (1:1 square)
│   └── icons/                      # SVG icons
└── .env.local.example              # Environment variable template
```

---

## Environment Variables

All variables are defined in `.env.local.example`. Key ones:

```bash
# Backend API (required for form submissions)
NEXT_PUBLIC_API_URL=http://localhost:8000

# Cloudflare Turnstile (bot protection on all forms)
# Dev: use the always-passes test key shown in .env.local.example
NEXT_PUBLIC_CLOUDFLARE_TURNSTILE_SITE_KEY=1x00000000000000000000AA

# Careers form: open role list (comma-separated, update without code deploy)
NEXT_PUBLIC_CAREERS_OPEN_ROLES=AI / ML Engineer,Full-Stack Engineer (Trades Domain),Customer Success (Trades Background a Plus),Sales / Growth
```

---

## Forms — Backend Endpoints

All forms POST to the backend. The marketing site uses raw `fetch()` — NOT `apiClient` from `@pilot/shared-api`. This is intentional: marketing forms are public and unauthenticated.

| Form                    | Endpoint                             | Notes                                                                                                                                |
| ----------------------- | ------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------ |
| Newsletter (footer)     | `POST /api/v1/marketing/newsletter`  | Email only. Routes to `NEWSLETTER_EMAIL_ADDR`.                                                                                       |
| Early Access / Waitlist | `POST /api/v1/marketing/waitlist`    | Email + trade + company size + optional name. Routes to `SALES_EMAIL_ADDR`.                                                          |
| Contact Us              | `POST /api/v1/marketing/contact`     | Name + email + subject + message. Routes to `CONTACT_US_EMAIL_ADDR`.                                                                 |
| Job Application         | `POST /api/v1/marketing/application` | Name + email + role + LinkedIn (required) + portfolio (optional) + short answer. Routes to `CAREERS_EMAIL_ADDR`. Rate limit: 5/hour. |

All forms use `TurnstileProtectedForm` as a security wrapper — do not remove it. Every POST includes a `cf_turnstile_response` token and a `honeypot` field.

---

## Security

Every form is protected by three layers:

1. **Cloudflare Turnstile** (bot-proof challenge, invisible widget)
2. **Honeypot field** (hidden text input; if non-empty, the backend rejects as bot)
3. **Rate limiting** via SlowAPI on the backend (10 req/IP/hour for most forms; 5/hour for job applications)

**Email validation**: As of MKT-B6, a `validate_email_tld` Pydantic validator on the backend rejects emails with 1-character TLDs (e.g. `me@me.t`). The frontend also validates via regex before submitting. The backend is the authoritative gate.

---

## Testing — Current State

**Test coverage is thin.** The marketing app has 31 test cases (page-copy and pricing-component tests under `src/app/__tests__/` and `src/components/__tests__/`, run with `pnpm --filter marketing test`); everything else was verified by manual smoke testing.

**What tests should eventually exist** (when time permits):

- Form submission happy paths (mock the backend endpoint, verify success state renders)
- Form validation — email regex, required field enforcement, LinkedIn URL required on ApplicationForm
- Turnstile mock setup (the test key `1x00000000000000000000AA` always passes in Cloudflare's dev environment)
- Role dropdown renders correctly from `NEXT_PUBLIC_CAREERS_OPEN_ROLES` env var
- Role dropdown falls back to `DEFAULT_ROLES` when env var is missing

**Test framework** (when you write tests): Vitest + `@testing-library/react` — same as `apps/web`. See `frontend/packages/typescript-config/` for the shared config.

---

## CSS Design System

The marketing site uses its own CSS design system defined in `src/app/globals.css`.

**Key token groups**:

- `--brand-{50|100|200|400|600|800|900}` — brand blue palette
- `--neutral-{50|100|200|400|600|700|800|900}` — gray palette
- `--trade-electrical` / `--trade-plumbing` / `--trade-hvac` — trade accent colors
- `--white` and `--white-{95|85|8|7|6|55|5|4|15|12|1|08|05}` — white with opacity variants (used on hero sections)
- `--border-white-{20|15|12}` — white border tokens (used on hero section borders)
- `--shadow-{xs|sm|md|lg|xl|2xl}` — shadow tokens
- `--gradient-hero-start` / `--gradient-hero-end` — hero gradient (brand blue)
- `.hero-gradient` utility class — applies the hero section gradient

**Critical**: If a component renders with an unintended blue/transparent background, the cause is almost always a missing CSS variable (like `--white` or `--white-95`). These were all defined as of MKT-B4. If you add new components referencing CSS variables from the product app (`apps/web`) that don't exist in this globals.css, define them here.

---

## Images

All images live in `public/` and are served by Next.js at runtime.

### Blog Post Heroes

- **Location**: `public/blog/`
- **Format**: JPG, 1200×630px (16:9 — OG image standard)
- **Usage**: Referenced in each blog post's MDX frontmatter as `image: "/blog/[filename].jpg"`
- **No code change needed**: MDX frontmatter already has the correct paths. Drop the file, done.
- **Status**: All 11 blog hero images generated and placed (June 25–26, 2026)

### Trade Page Heroes

- **Location**: `public/trades/`
- **Format**: JPG, 1200×750px (16:9)
- **Usage**: `next/image` with `fill` + `object-cover` in `TradePageTemplate.tsx`
- **Status**: All 3 trade hero images placed (June 25, 2026)

### Feature Section Images

- **Location**: `public/features/`
- **Format**: JPG, 800×500px (3:2) — create `public/features/` dir if missing
- **Usage**: `next/image` wired in `src/app/features/page.tsx` via `FEATURE_IMAGE_MAP`
- **Status**: All 11 feature images placed (June 25–26, 2026)

### About Page

- **File**: `public/about-hero.jpg`
- **Format**: JPG, square (1:1)
- **Usage**: `next/image` in `src/app/about/page.tsx`

The AI image-generation prompts lived in `dev-docs/marketing-analysis/design-specs/` (private, not in this snapshot).

---

## Blog Posts

Blog content lives in `src/content/blog/` as MDX files. The blog system uses `src/lib/blog.ts` to read and parse them.

**Adding a new post**: Create a `.mdx` file in the appropriate category subfolder with the required frontmatter:

```yaml
---
title: "Post Title"
slug: "url-slug"
description: "Meta description"
author: "Tom Lang"
date: "2026-06-XX"
category: "electrical|plumbing|hvac|business|product"
tags: ["tag1", "tag2"]
trade: "electrical|plumbing|hvac|all"
featured: false
image: "/blog/your-hero-image.jpg"
readingTime: 5
---
```

Place the hero image at `public/blog/your-hero-image.jpg` (1200×630px JPG).

---

## Legal Pages

Located in `src/app/legal/`. All legal pages use HotRMC DBA wording:

> "Example Holdings, LLC, doing business as Pilot for Trades"

Legal contact email on all three pages: `legal@pilotfortrades.com`

**Effective Date**: January 1, 2026 (a placeholder date in the launch draft).

The Privacy Policy includes a mandatory 10DLC clause: "We do not share mobile phone numbers or SMS messaging opt-in data with third parties or affiliates for marketing or promotional purposes."

---

## Email Addresses (Google Workspace aliases/groups, as set up during the build)

| Alias                           | Purpose                                                                 |
| ------------------------------- | ----------------------------------------------------------------------- |
| `info@pilotfortrades.com`       | Contact Us form (public-facing general inquiry)                         |
| `support@pilotfortrades.com`    | In-product help and issue reporting                                     |
| `sales@pilotfortrades.com`      | Inbound sales / waitlist signups                                        |
| `billing@pilotfortrades.com`    | Invoicing and subscription questions                                    |
| `legal@pilotfortrades.com`      | Legal pages contact, 10DLC carrier reference                            |
| `careers@pilotfortrades.com`    | Job applications (Google Group, Tom as member)                          |
| `noreply@pilotfortrades.com`    | Transactional email sender (Google Group, Tom as member, no auto-reply) |
| `newsletter@pilotfortrades.com` | Newsletter subscribers                                                  |

All transactional emails sent by the backend use `noreply@pilotfortrades.com` as the From address. All email templates must include: _"This is an automated message. Do not reply — contact `support@pilotfortrades.com` for help."_

---

## UTM Tracking

The newsletter footer form (`NewsletterForm.tsx`) reads UTM parameters from the URL on mount via `getUtmParams()`. If no UTM params are present (organic traffic), it falls back to:

- `utm_source = "website"`
- `utm_medium = "organic"`
- `utm_campaign = null`

External campaigns should use UTM-tagged URLs (e.g., `pilotfortrades.com?utm_source=twitter&utm_medium=social&utm_campaign=launch_2026`) to get proper attribution data in `marketing_newsletter_subscriber`.

---

## Known Issues & Technical Debt

1. **Thin automated tests** — the biggest gap; 31 test cases, the rest manual smoke testing.
2. **Blog post `introducing-pilot-for-trades.mdx`** — present in `src/content/blog/product/`.
3. **`careers@` not in the backend `.env.example` yet** — added in MKT-B6 Part A (Python Engineer batch). Ensure this is deployed before the careers form is live.
4. **Pydantic `EmailStr` TLD validation** — fixed in MKT-B6 Part A (Task A-11). One junk test record (`me@me.t`) was left in the dev database's `marketing_newsletter_subscriber` table.
5. **System Status footer link** — removed (was a dead `#` link). No status page exists yet.
6. **`careers@pilotfortrades.com` previously missing** — was referenced in old careers page `mailto:` link before MKT-B6. Now a real alias.
7. **Site-mode switch reads a test-only endpoint** — `src/lib/useSiteMode.ts` calls `GET /api/v1/subscription-tiers/test`, which is blocked outside dev/qa, so a production build always falls back to Charter mode. A public tiers endpoint is needed before General Release mode can be switched on.

---

## Batch History (Marketing Site)

| Batch  | Description                                                               | Status         |
| ------ | ------------------------------------------------------------------------- | -------------- |
| MKT-B1 | Initial marketing site build (forms backend)                              | ✅ Complete    |
| MKT-B2 | Blog system + MDX content                                                 | ✅ Complete    |
| MKT-B3 | Compliance fixes (pricing, legal, email, JSON-LD)                         | ✅ Complete    |
| MKT-B4 | Design & visual polish (CSS tokens, images, nav fix)                      | ✅ Complete    |
| MKT-B5 | Features page + about page images                                         | ✅ Complete    |
| MKT-B6 | Careers redesign + email routing refactor (Part A: Python, Part B: React) | ⏸ Last recorded as in progress at hibernation |

For design specs: `dev-docs/marketing-analysis/design-specs/` (private, not in this snapshot)
For implementation prompts: `dev-docs/implementation-prompts/fe-be-mob-batch-prompts/batch-mkt-b*`
