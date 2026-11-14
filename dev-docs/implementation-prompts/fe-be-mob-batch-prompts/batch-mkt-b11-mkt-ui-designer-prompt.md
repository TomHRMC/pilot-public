# Design Brief: MKT-B11-C1 — Site Mode Switch (Founders → General Release) + New Logo

**Mode**: Pilot Marketing UI Designer  
**Batch**: MKT-B11-C1  
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §MKT-B11  
**Pricing decisions**: `dev-docs/marketing-analysis/gtm-feature-tier-matrix-v1.md` §19  
**Brand strategy**: `dev-docs/brand-strategy/pilot-for-trades-brand-strategy.md`  
**Estimated session**: 4–6 hours  
**Platform**: Marketing website (`frontend/apps/marketing/`)  
**Companion**: MKT-B11-C2 (Marketing React Engineer) — implements everything designed here  

---

## Context — The Two-Mode Site

The Pilot for Trades marketing site needs to support two distinct operating modes, controlled by a single database flag (`product_plan.is_active` for `founders_plan`). This is a zero-code-deploy switch — Tom flips the DB flag and the entire site updates automatically.

| Mode | When Active | What customers see |
|---|---|---|
| **Founders Mode** | `founders_plan.is_active = true` | "Be One of the First" — Founding Member Program, 6 months free → $49/mo locked |
| **General Release Mode** | `starter_plan.is_active = true` | "Free Trial Sign Up" — 14-day free trial, then Starter ($49) or Teams ($149) |

**Everything you design in this brief needs both states.** The React Engineer will implement the switch logic — your job is to make sure both states are designed, complete, and production-ready before they start.

---

## Part 1 — New Logo Design

### 1.1 Background

The current logo on the site is a placeholder. Pilot for Trades needs a production-quality logo before any external registrations (app stores, integration partner directories, 10DLC brand registration, etc.) are submitted. This logo will become the permanent brand mark.

### 1.2 Brand Brief for Logo

**Product name**: Pilot for Trades  
**Tagline**: *Master the Craft. Automate the Rest.*  
**Audience**: Solo and small-crew electrical contractors, age 22–45. Tech-forward but blue-collar. Values precision, speed, and professionalism. Distrusts "enterprise" bloat.  
**Tone**: Peer-to-peer. Competent. No-BS. Slightly witty. Not corporate.  
**Primary color palette**: Brand blue (currently `var(--brand-600)` in the design system); must work on white, dark slate, and transparent backgrounds.

### 1.3 Logo Design Requirements

**Deliverables**:

1. **Primary logo** — full horizontal lockup: icon + "Pilot for Trades" wordmark  
2. **Compact logo** — icon only (for favicons, app icons, small-space use)  
3. **Wordmark only** — "Pilot for Trades" text without icon (for certain header contexts)  
4. **Dark-background variant** — all three above in white/light versions for use on hero gradients

**Design direction** (informed by brand strategy doc §4):  
- The icon should evoke both the digital/AI side and the physical trades side without being literal or cliché (no clipart wrenches, no circuit boards)  
- Consider a pilot/navigation metaphor (compass, bearing, heading indicator) paired with a trades texture (panel, tool silhouette, conduit bend)  
- The "P" or a stylized mark can reference the cockpit instrument panel concept — something a field tech would recognize as "precision navigation"  
- Clean and modern — must work at 16px (favicon) and 300px (hero/header) equally  
- Avoid: hard hats, generic bolts/wrenches, tech-bro logos, anything that looks like a generic SaaS product  
- Typographic style: geometric sans-serif for the wordmark (similar weight to the current UI typography)

### 1.4 Logo Deliverable Formats

Produce each logo variant in:
- SVG (primary — what the website uses)
- PNG at 512×512 (app store / favicons)
- PNG at 1024×1024 (high-res partner submissions)

Document the logo in a **Logo Usage Guide** section in the design file covering:
- Minimum size requirements
- Clear space rules
- Approved color combinations (logo on white, on dark, on brand color)
- What not to do (stretch, recolor, add drop shadow)

### 1.5 Third-Party Integration Partner Submission Materials

Once the logo is finalized, produce ready-to-submit brand kits for each integration partner that requires it during app registration or directory listing:

| Partner | Submission Context | Required Assets |
|---|---|---|
| **QuickBooks / Intuit** | App marketplace listing (developer portal) | App icon 512×512 PNG; logo on white 1024px wide PNG; brand color hex; short description (100 chars) |
| **Google** | Google Calendar API app registration; Google OAuth consent screen | App icon 512×512 PNG; app name text; privacy policy URL |
| **Stripe** | Connect platform registration; Stripe dashboard branding | Logo on white (preferred); brand color hex; business name and URL |
| **Telnyx** | 10DLC brand registration (TCR) | Company logo PNG; brand name; website URL; vertical (electrical contractor) |
| **Apple App Store** | App submission | App icon 1024×1024 PNG (no alpha channel, no rounded corners — Apple applies corners); app name |
| **Google Play Store** | App submission | App icon 512×512 PNG (no alpha channel); feature graphic 1024×500 PNG |
| **AWS Marketplace** (future) | If/when listed | Logo on white 220×220 PNG |

For each partner, produce a single-page PDF or Figma artboard titled "Partner Submission — [Partner Name]" that consolidates all required assets and any text fields with the correct values, so Tom can submit directly without hunting for materials.

---

## Part 2 — Site Mode Switch Design

### 2.1 The Switch Mechanism

Every component below needs a **"Founders Mode"** state (current behavior) and a **"General Release Mode"** state (new behavior when Starter/Teams go live). Design both states in a single Figma file. Label each artboard or frame clearly.

**The `/sign-up` page is new** — it does not exist yet. It replaces `/early-access` as the destination for all "Get Started" CTAs in General Release Mode. It uses the same `WaitlistForm` component but with updated copy.

### 2.2 Component-by-Component Design Spec

---

#### A. Header CTA (affects every page — desktop + mobile)

**File reference**: `frontend/apps/marketing/src/components/Header.tsx`

| State | Button Text | Destination | Style |
|---|---|---|---|
| **Founders Mode** | "Be One of the First" | `/early-access` | `btn-primary` (current) |
| **General Release** | "Start Free Trial" | `/sign-up` | `btn-primary` (same style, new text) |

Design both desktop (nav bar, rightmost button) and mobile (hamburger menu, full-width button) states.

---

#### B. Homepage Hero Section (`/`)

**File reference**: `frontend/apps/marketing/src/app/page.tsx` lines ~156–168

| State | Primary CTA | Secondary element |
|---|---|---|
| **Founders Mode** | "Be One of the First" → `/early-access` | None (current state) |
| **General Release** | "Start Free Trial" → `/sign-up` | Below button: "14-day free trial · No credit card required" in small caption text |

The General Release hero should also update the subtitle copy if needed to reflect that regular signup (not founding member program) is available.

---

#### C. Homepage Bottom CTA Section (`/`)

The final section of the homepage has a CTA strip with a dark background.

| State | Text | Button |
|---|---|---|
| **Founders Mode** | "The first group of electricians gets six months free..." | "Be One of the First" → `/early-access` |
| **General Release** | "Start your 14-day free trial today. No credit card required." | "Start Free Trial" → `/sign-up` |

---

#### D. Pricing Page (`/pricing`) — Full Page Redesign for General Release

**Founders Mode**: Current page (single plan card, Founding Member offer) — **no change needed**. Design for reference only.

**General Release**: New 2-column layout.

| | Starter | Teams |
|---|---|---|
| **Price** | $49/mo | $149/mo |
| **Schedule Lanes** | 5 simultaneous jobs | 20 simultaneous jobs |
| **Voice AI** | 90 min/month | 300 min/month |
| **SMS** | 100 segments/month | 500 segments/month |
| **All other features** | Unlimited users, jobs, quotes, invoices, customers, QB syncs | Same + advanced features |
| **Primary CTA** | "Start Free Trial — 14 days, no credit card" | "Start Free Trial — 14 days, no credit card" |
| **CTA subtext** | "14-day free trial at Starter limits. Converts to $49/month or cancel anytime." | "14-day free trial at Teams limits. Converts to $149/month or cancel anytime." |

Per `gtm-feature-tier-matrix-v1.md §19`: include the 10–12 highest-conversion features per tier in the card body.

The pricing page should also include:
- An optional annual billing toggle (designer's call on whether to include now; if included, show 17% savings)
- FAQ section (reuse existing FAQ questions, update "Is there a free trial?" answer to reflect standard 14-day trial)
- Schedule Lane explanation callout: *"What's a schedule lane? It's one parallel job row on your dispatch board. Assign any team member to any job in any lane."*

---

#### E. Early-Access Page (`/early-access`) — Update for General Release as `/sign-up`

**Founders Mode**: Current page content — "Be One of the First" — **no change**.

**General Release Mode** — The URL becomes `/sign-up`. Same `WaitlistForm` component, updated content:

- **H1**: "Start Your Free Trial"
- **Subheading**: "14 days free. No credit card required. Cancel anytime."
- **What's included block** (3-card section):
  - 🆓 "14 days free at your chosen plan's limits"
  - ⚡ "Full access to Voice AI, dispatch board, invoicing, and QuickBooks sync"
  - 🔒 "No credit card until your trial ends — and you choose to stay"
- **Form**: Same fields as current `WaitlistForm`; button text: "Start Free Trial"
- **Microcopy below button**: "After 14 days, continue at $49/month (Starter) or $149/month (Teams). Cancel anytime before trial ends."

---

#### F. Trade Pages — Pricing Section + CTAs (Electrical, Plumbing, HVAC)

**File reference**: `frontend/apps/marketing/src/components/trades/TradePageTemplate.tsx`

These pages share `TradePageTemplate.tsx`. Three CTA locations per trade page:
1. Hero section CTA button
2. Pricing section CTA button  
3. Bottom strip CTA

| State | All 3 CTA buttons | Pricing section body copy |
|---|---|---|
| **Founders Mode** | "Be One of the First" → `/early-access` | Current copy (e.g., "$49/month, everything included") |
| **General Release** | "Start Free Trial" → `/sign-up` | Update to: "Starter at $49/month · Teams at $149/month · 14-day free trial" |

---

#### G. Features Page CTAs (`/features`)

Two CTA instances:
- Mid-page callout
- Bottom strip

| State | Text | Button |
|---|---|---|
| **Founders Mode** | Current content | "Be One of the First" → `/early-access` |
| **General Release** | "Ready to see it on your jobs?" | "Start Free Trial" → `/sign-up` |

---

#### H. About Page CTA (`/about`)

Bottom CTA strip.

| State | Body | Button |
|---|---|---|
| **Founders Mode** | Current waitlist language | "Be One of the First" → `/early-access` |
| **General Release** | "Join thousands of contractors using Pilot to run tighter operations." | "Start Free Trial" → `/sign-up` |

---

#### I. Contact Page CTA (`/contact`)

The contact page has a sidebar "Join the waitlist" block.

| State | Heading | Link |
|---|---|---|
| **Founders Mode** | "Join the waitlist" | "Be One of the First →" → `/early-access` |
| **General Release** | "Start your free trial" | "Start Free Trial →" → `/sign-up` |

---

#### J. Blog Components (Sidebar + Post Footer)

**Files**: `BlogCta.tsx`, `BlogPostLayout.tsx`

Blog sidebar and post-footer CTAs appear on every blog post.

| State | CTA Label | Destination | Subtext |
|---|---|---|---|
| **Founders Mode** | "Be One of the First →" | `/early-access` | — |
| **General Release** | "Start Free Trial →" | `/sign-up` | "14 days free · No credit card" |

---

#### K. Blog Listing Page Bottom CTA (`/blog`)

| State | Button |
|---|---|
| **Founders Mode** | "Be One of the First" → `/early-access` |
| **General Release** | "Start Free Trial" → `/sign-up` |

---

#### L. Footer Navigation Link

| State | Nav Label | Destination |
|---|---|---|
| **Founders Mode** | "Early Access" | `/early-access` |
| **General Release** | "Start Free Trial" | `/sign-up` |

---

### 2.3 Design File Structure

Organize the Figma file as:

```
MKT-B11 — Site Mode Switch + Logo
├── 01 — Logo
│   ├── Logo Concepts (3+ concepts with rationale)
│   ├── Final Logo — Full Lockup
│   ├── Final Logo — Icon Only
│   ├── Final Logo — Wordmark Only
│   ├── Dark Background Variants
│   └── Logo Usage Guide
├── 02 — Partner Submission Materials
│   ├── QuickBooks / Intuit
│   ├── Google (Calendar + OAuth)
│   ├── Stripe
│   ├── Telnyx / 10DLC
│   ├── Apple App Store
│   └── Google Play Store
├── 03 — Founders Mode (current site states — for reference)
│   ├── Header CTA
│   ├── Homepage Hero
│   ├── Homepage Bottom CTA
│   ├── Pricing Page (current)
│   ├── Early-Access Page (current)
│   └── [other components]
├── 04 — General Release Mode (new states to implement)
│   ├── Header CTA
│   ├── Homepage Hero
│   ├── Homepage Bottom CTA
│   ├── Pricing Page — 2-Column Starter/Teams
│   ├── Sign-Up Page (/sign-up) — NEW
│   ├── Trade Page CTAs (Electrical / Plumbing / HVAC)
│   ├── Features Page CTAs
│   ├── About Page CTA
│   ├── Contact Page CTA
│   ├── Blog Sidebar CTA
│   ├── Blog Post Footer CTA
│   ├── Blog Listing CTA
│   └── Footer Nav Link
└── 05 — Handoff Notes for React Engineer
    ├── Component inventory with Founders/General states
    ├── CSS token references for any new styles
    └── Animation/transition guidance (if any)
```

---

## Definition of Done (Designer)

- [ ] Logo: minimum 3 concepts presented with rationale
- [ ] Logo: final selection in all 4 variants (full lockup, icon, wordmark, dark versions)
- [ ] Logo: all SVG + PNG exports at required sizes
- [ ] Logo: usage guide included in design file
- [ ] Partner materials: all 6 partner submission artboards complete with correct asset dimensions
- [ ] Component designs: all 12 component/page sections above have both Founders and General Release states designed
- [ ] `/sign-up` page: fully designed for General Release mode
- [ ] `/pricing` General Release: 2-column Starter/Teams layout complete with all feature bullets, CTAs, and FAQ
- [ ] Design tokens: all new styles reference existing `globals.css` CSS variables; no hardcoded hex values
- [ ] Responsive coverage: each component/page designed at 375px (mobile) and 1440px (desktop) minimum
- [ ] Handoff notes: complete in §05 of the design file so the React Engineer can implement without clarification
- [ ] File shared with Tom for approval before the React Engineer begins Part C2

---

## After This Design — Next Step

Once Tom approves the design, hand off to the **MKT-B11-C2 Marketing React Engineer** who will implement:
1. The `useSiteMode()` hook (reads `GET /api/v1/subscription-tiers?active_only=true`)
2. All component variants using the hook to switch states
3. The new `/sign-up` page
4. The updated `/pricing` page with both variants
5. Swap the `logo.svg` / `logo.png` assets across the site
