# MKT-B11 — UI Design Specification
## Site Mode Switch (Founders → General Release) + New Logo

**Designer:** Pilot Marketing UI Designer  
**Batch:** MKT-B11-C1  
**Status:** Ready for React Engineer (MKT-B11-C2)  
**Date:** 2026-07-09  

---

## Overview: The Two-Mode Switch

The site operates in one of two modes, determined by a backend flag read via `GET /api/v1/subscription-tiers?active_only=true`. The React Engineer implements `useSiteMode()` hook — this spec defines both mode states for every affected component.

| Mode | Trigger | Core CTA | Destination |
|------|---------|----------|-------------|
| **Founders Mode** | `founders_plan.is_active = true` | "Be One of the First" | `/early-access` |
| **General Release** | `starter_plan.is_active = true` | "Start Free Trial" | `/sign-up` |

All components below show both states. Design tokens reference `globals.css` — no hardcoded hex values in component code.

---

## 01 — Logo (New Production Mark)

### Icon Concept: "The Ascent Bar"
Four ascending bars with a diagonal upward-trend arrow overlaid. Evokes job profitability tracking and business growth without using clipart trades imagery. Inspired by the Grok v2 logo reference (growth chart metaphor) but simplified to a clean, modern SVG mark.

**Files created:**
- `/public/brand/logo-primary.svg` — Full lockup (280×56 viewBox)
- `/public/brand/logo-icon.svg` — Icon only (56×56 viewBox)
- `/public/brand/logo-wordmark.svg` — Wordmark only (220×56 viewBox)
- `/public/brand/logo-primary-dark.svg` — Dark bg variant
- `/public/brand/logo-icon-dark.svg` — Icon dark bg variant
- `/public/brand/logo-wordmark-dark.svg` — Wordmark dark bg variant

### Logo Token Map
```
Icon background (light): var(--brand-600) = #3b43d6
Icon background (dark):  rgba(255,255,255,0.15)
Wordmark "Pilot" (light): var(--brand-900) = #181d66
Wordmark "Pilot" (dark):  #ffffff
Wordmark "FOR TRADES" (light): var(--brand-600) = #3b43d6
Wordmark "FOR TRADES" (dark):  rgba(255,255,255,0.70)
```

### Header Implementation (replacing placeholder)
Replace the inline SVG in `Header.tsx` line 39–55 with:
```tsx
<Image
  src="/brand/logo-primary.svg"
  alt="Pilot for Trades"
  width={160}
  height={36}
  priority
/>
```
On mobile (< 768px), use the icon-only variant at 32×32.

---

## 02 — Component Design States (A–L)

### A. Header CTA — Desktop + Mobile

**File:** `Header.tsx`

#### Desktop Nav Bar (1440px)
Both modes share identical layout: nav items left, CTA button rightmost.

```
[Logo]  Features  Trades ▾  Pricing  About  [   CTA BUTTON   ]
```

| State | Button text | href | Class |
|-------|------------|------|-------|
| **Founders** | "Be One of the First" | `/early-access` | `btn-primary py-2 px-5 text-sm` |
| **General Release** | "Start Free Trial" | `/sign-up` | `btn-primary py-2 px-5 text-sm` |

No layout change between modes — text and href update only.

#### Mobile Menu (375px)
Full-width button at bottom of nav drawer:

| State | Button text | href | Class |
|-------|------------|------|-------|
| **Founders** | "Be One of the First" | `/early-access` | `btn-primary w-full text-center` |
| **General Release** | "Start Free Trial" | `/sign-up` | `btn-primary w-full text-center` |

---

### B. Homepage Hero Section — `/`

**File:** `page.tsx` lines 156–168

#### Founders Mode (current state — reference)
```
H1: "Build Quotes by Voice. Know Your Margin on Every Job."
CTA: [Be One of the First]  See How It Works →
```

#### General Release Mode (new state)
```
H1: "Build Quotes by Voice. Know Your Margin on Every Job."
(H1 unchanged — it's evergreen copy)

CTA button: [Start Free Trial]  →  /sign-up
  Below button (new element):
  ┌─────────────────────────────────────┐
  │  14-day free trial · No credit card │
  │  required                           │
  └─────────────────────────────────────┘
  Style: text-caption-lg, color: var(--white-7), mt-3
```

**Token refs:**
- Caption text: `var(--white-7)`, `var(--text-caption-lg)`, `var(--lh-caption-lg)`
- No layout change — caption appears below the button row

---

### C. Homepage Bottom CTA Section — `/`

**File:** `page.tsx` lines 1042–1069 (Section 9)

Background: `var(--brand-600)` solid.

#### Founders Mode (current)
```
H2: "Your Evenings Belong to You. Not Your Estimates."
Body: "Join contractors who are done with spreadsheet estimates..."
CTA: [Be One of the First]  class="btn-white"
```

#### General Release Mode
```
H2: "Your Evenings Belong to You. Not Your Estimates."
(H2 unchanged — evergreen)

Body: "Start your 14-day free trial today. No credit card required.
       Voice quoting, live margins, and smart dispatch — try it on a real job."

CTA: [Start Free Trial]  class="btn-white"  href="/sign-up"
```

---

### D. Pricing Page — `/pricing`

**File:** `pricing/page.tsx`

#### Founders Mode (current — no change)
Single centered card. `btn-primary` → `/early-access`. Keep as-is.

#### General Release Mode — New 2-Column Layout

**Page structure:**
```
[Hero: "Simple, transparent pricing."]
[Annual billing toggle — optional, show 17% savings]
[2-column card grid: Starter | Teams]
[Schedule Lane callout banner]
[Feature comparison strip]
[FAQ accordion — updated]
[Bottom CTA strip]
```

**Starter Card (left, $49/mo):**
```
┌─────────────────────────────────┐
│  Starter                        │
│  For solo and small crews       │
│                                 │
│  $49 /month                     │
│  $41/mo billed annually (toggle)│
│                                 │
│  [Start Free Trial]             │
│  14-day free trial · Starter    │
│  limits · No credit card        │
│                                 │
│  ✓ 5 schedule lanes             │
│  ✓ 90 Voice AI min/month        │
│  ✓ 100 SMS segments/month       │
│  ✓ Unlimited users              │
│  ✓ Unlimited jobs & quotes      │
│  ✓ Unlimited invoices           │
│  ✓ Voice-to-quote AI (NEC-aware)│
│  ✓ Real-time job profitability  │
│  ✓ Smart dispatch board         │
│  ✓ QuickBooks Online sync       │
│  ✓ Google Calendar sync         │
│  ✓ Customer SMS + reminders     │
│  ✓ iOS + Android, works offline │
│  ✓ Stripe payments              │
└─────────────────────────────────┘
```

**Teams Card (right, $149/mo) — POPULAR badge:**
```
┌─────────────────────────────────┐
│  ★ Most Popular                 │
│  Teams                          │
│  For growing multi-crew ops     │
│                                 │
│  $149 /month                    │
│  $124/mo billed annually (toggle│
│                                 │
│  [Start Free Trial]             │
│  14-day free trial · Teams      │
│  limits · No credit card        │
│                                 │
│  ✓ 20 schedule lanes            │
│  ✓ 300 Voice AI min/month       │
│  ✓ 500 SMS segments/month       │
│  ✓ Unlimited users              │
│  ✓ Unlimited jobs & quotes      │
│  ✓ Unlimited invoices           │
│  ✓ Voice-to-quote AI (NEC-aware)│
│  ✓ Real-time job profitability  │
│  ✓ Smart dispatch board         │
│  ✓ QuickBooks Online sync       │
│  ✓ Google Calendar sync         │
│  ✓ Customer SMS + reminders     │
│  ✓ iOS + Android, works offline │
│  ✓ Stripe payments              │
│  ✓ Priority support             │
│  ✓ Advanced analytics           │
└─────────────────────────────────┘
```

**Teams card visual distinction:**
- Border: `2px solid var(--brand-600)` (vs `1px solid var(--neutral-200)` for Starter)
- "Most Popular" badge: `background: var(--brand-600)`, white text, positioned top-right, `border-radius: 0 1rem 0 0.75rem`
- Slightly elevated shadow: `var(--shadow-xl)` vs `var(--shadow-md)`

**Schedule Lane Callout Banner:**
```
Background: var(--brand-50)
Border: 1px solid var(--brand-100)
Icon: calendar/grid icon (var(--brand-600))
Text: "What's a schedule lane? It's one parallel job row on your dispatch board.
       Assign any team member to any job in any lane."
Style: text-sm, color: var(--brand-800)
```

**Annual Billing Toggle (designer recommends: include):**
```
Monthly  [●────]  Annually (Save 17%)
```
- Toggle pill: `background: var(--brand-600)` when annual active
- "Save 17%" badge: `var(--margin-50)` bg, `var(--margin-600)` text
- Annual prices: Starter = $41/mo, Teams = $124/mo
- Subtext under annual price: "billed as $492/yr" / "billed as $1,488/yr"

**Updated FAQ — "Is there a free trial?" answer:**
```
Old answer (Founders): "We're doing something better than a trial. The first group..."
New answer (General Release): "Yes — 14 days free on your chosen plan (Starter or Teams
limits), no credit card required. After 14 days, continue at $49/month (Starter) or
$149/month (Teams), or cancel anytime before the trial ends. No surprises."
```

**Bottom CTA:**
```
H2: "Ready to try it on a real job?"
Body: "14 days free. No credit card required. Cancel anytime before your trial ends."
CTAs: [Start Free Trial] [Contact Us]
```

---

### E. Sign-Up Page — `/sign-up` (NEW, General Release only)

**File to create:** `/app/sign-up/page.tsx`

This page does NOT exist yet. It replaces `/early-access` as the destination for all General Release CTAs. It reuses the `WaitlistForm` component but with updated copy.

**Layout:** Same two-column layout as `/early-access` — left column copy, right column sticky form card.

**Left column copy:**
```
H1: "Start Your Free Trial"
Subheading: "14 days free. No credit card required. Cancel anytime."
Style: text-hero, color: var(--white)

What's included (3 cards):
┌──────────────────────────────────────┐
│ 🆓  14 days free at your chosen      │
│     plan's limits                    │
├──────────────────────────────────────┤
│ ⚡  Full access to Voice AI,          │
│     dispatch board, invoicing, and   │
│     QuickBooks sync                  │
├──────────────────────────────────────┤
│ 🔒  No credit card until your trial  │
│     ends — and you choose to stay    │
└──────────────────────────────────────┘
Cards: background var(--white-08), border var(--border-white-12)

Below cards:
"After 14 days, continue at $49/month (Starter) or $149/month (Teams).
 Cancel anytime before trial ends."
Style: text-caption-lg, color: var(--white-5)
```

**Right column form card:**
```
Form: Same WaitlistForm component
  source="sign_up_page"
  Button text: "Start Free Trial"
  (override default "Join Waitlist" label)

Trust line below card:
"No credit card required. Cancel anytime."
color: var(--white-4)
```

---

### F. Trade Pages — Pricing Section + CTAs (Electrical, Plumbing, HVAC)

**File:** `TradePageTemplate.tsx`

Three CTA locations per trade page. All three update together.

| Location | Founders Mode | General Release |
|----------|--------------|-----------------|
| Hero CTA | "Be One of the First" → `/early-access` | "Start Free Trial" → `/sign-up` |
| Pricing section CTA | "Be One of the First" → `/early-access` | "Start Free Trial" → `/sign-up` |
| Bottom strip CTA | "Be One of the First" → `/early-access` | "Start Free Trial" → `/sign-up` |

**Pricing section body copy update:**
```
Founders Mode (current):
  "$49/month, everything included."

General Release:
  "Starter at $49/month · Teams at $149/month"
  Below: "14-day free trial — no credit card required."
  Link: "See full pricing →" → /pricing
```

---

### G. Features Page CTAs — `/features`

**File:** `src/app/features/page.tsx`

Two CTA locations: mid-page callout and bottom strip.

| Location | Founders Mode | General Release |
|----------|--------------|-----------------|
| Mid-page heading | (current) | "Ready to see it on your jobs?" |
| Mid-page CTA | "Be One of the First" → `/early-access` | "Start Free Trial" → `/sign-up` |
| Bottom strip CTA | "Be One of the First" → `/early-access` | "Start Free Trial" → `/sign-up` |

No layout changes — text and href update only.

---

### H. About Page CTA — `/about`

**File:** `src/app/about/page.tsx`

Bottom CTA strip.

| Field | Founders Mode | General Release |
|-------|--------------|-----------------|
| Body | (current waitlist language) | "Join contractors running tighter operations with Pilot." |
| Button | "Be One of the First" → `/early-access` | "Start Free Trial" → `/sign-up` |

---

### I. Contact Page CTA — `/contact`

**File:** `src/app/contact/page.tsx`

Sidebar "join" block.

| Field | Founders Mode | General Release |
|-------|--------------|-----------------|
| Heading | "Join the waitlist" | "Start your free trial" |
| Link text | "Be One of the First →" | "Start Free Trial →" |
| href | `/early-access` | `/sign-up` |

---

### J. Blog Components — Sidebar + Post Footer

**Files:**
- `BlogCta.tsx`
- `BlogPostLayout.tsx`

`BlogCta` already accepts `ctaLabel` and `ctaHref` as props. No layout changes needed.

| Prop | Founders Mode | General Release |
|------|--------------|-----------------|
| `ctaLabel` | `"Be One of the First →"` | `"Start Free Trial →"` |
| `ctaHref` | `"/early-access"` | `"/sign-up"` |
| `body` (optional subtext) | (existing) | Add: `"14 days free · No credit card"` |

**General Release addition:** A small subtext line below the CTA button:
```
"14 days free · No credit card"
Style: text-caption-lg, color: var(--brand-700), mt-2
```

---

### K. Blog Listing Page Bottom CTA — `/blog`

**File:** `src/app/blog/page.tsx`

| State | Button text | href |
|-------|------------|------|
| Founders | "Be One of the First" | `/early-access` |
| General Release | "Start Free Trial" | `/sign-up` |

---

### L. Footer Navigation Link

**File:** `Footer.tsx`

In the "Product" column footer links array (line 13):

| State | Label | href |
|-------|-------|------|
| **Founders** | "Early Access" | `/early-access` |
| **General Release** | "Start Free Trial" | `/sign-up` |

---

## 03 — Responsive Coverage Checklist

| Component | 375px Mobile | 768px Tablet | 1440px Desktop |
|-----------|-------------|-------------|---------------|
| Header CTA | ✓ Full-width btn in drawer | ✓ Same as mobile | ✓ Rightmost nav btn |
| Homepage Hero | ✓ Single column, caption below btn | ✓ | ✓ Two-column |
| Homepage Bottom CTA | ✓ Stacked | ✓ | ✓ Centered |
| Pricing (General) | ✓ Single column cards | ✓ Two col | ✓ Two col max-w-4xl |
| Sign-Up page | ✓ Single col, form below copy | ✓ | ✓ Two-col sticky form |
| Trade pages | ✓ | ✓ | ✓ |
| Blog CTAs | ✓ Full-width | ✓ | ✓ |
| Footer | ✓ | ✓ | ✓ |

---

## 04 — Design Token Reference (new styles only)

No new tokens are introduced. All new styles reference existing `globals.css` variables.

| New element | Token used |
|-------------|-----------|
| Hero caption "14-day free trial" | `var(--text-caption-lg)`, `var(--white-7)` |
| Pricing toggle active state | `var(--brand-600)` background |
| Annual savings badge | `var(--margin-50)` bg, `var(--margin-600)` text |
| Schedule lane callout | `var(--brand-50)` bg, `var(--brand-100)` border, `var(--brand-800)` text |
| Teams card border | `var(--brand-600)` 2px |
| Teams card "Most Popular" badge | `var(--brand-600)` bg, `#ffffff` text |
| Sign-up what's-included cards | `var(--white-08)` bg, `var(--border-white-12)` |
| Blog CTA subtext | `var(--brand-600)` |

---

## 05 — Handoff Notes (see separate file)

See `batch-mkt-b11-react-engineer-handoff.md` for complete implementation notes for the React Engineer.
