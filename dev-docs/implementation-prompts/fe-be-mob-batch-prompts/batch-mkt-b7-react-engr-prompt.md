# Implementation Prompt: MKT-B7 — Pricing Page Redesign + Founding Member Program Page

**Mode**: Pilot React Engineer
**Batch**: MKT-B7
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §P0 Marketing Website
**Design doc**: `dev-docs/marketing-analysis/design-specs/mkt-b7-design-spec.md`
**GTM strategy**: `dev-docs/marketing-analysis/gtm-pricing-strategy-v1.md`
**Feature matrix**: `dev-docs/marketing-analysis/gtm-feature-tier-matrix-v1.md`
**Estimated session**: 3–4 hours
**Platform**: Marketing site only (`frontend/apps/marketing/`)
**Backend companion**: None — pure frontend, no backend changes
**Pure frontend — no backend changes needed**

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-react-engineer/react-engineer-rules.md`** — in full
- **`dev-docs/marketing-analysis/design-specs/mkt-b7-design-spec.md`** — every section (A–I)
- **`dev-docs/marketing-analysis/gtm-feature-tier-matrix-v1.md §19`** — the exact feature highlight content for each tier column

Critical rules for this batch:

- **Marketing app is NOT `apps/web`**: This batch touches ONLY `frontend/apps/marketing/`. Do NOT modify anything in `apps/web/`, `apps/mobile/`, or `packages/ui/`. The marketing site uses raw `fetch()` and its own standalone CSS — not `apiClient`, not shared UI components.
- **No `pnpm sync-api-types` needed**: The marketing site does NOT use `@pilot/shared-types` or `@pilot/shared-api`. Skip that step entirely.
- **No existing test suite**: The marketing app has zero test files. The regression baseline is `0 passed, 0 failed`. There is no test runner to run. The Phase 2 verification command is build + lint only (see §Final Verification).
- **`PricingToggle` must be a `"use client"` island**: The pricing page toggle requires client-side state. The parent `pricing/page.tsx` stays a server component. Do NOT add `"use client"` to the page file itself.
- **CSS tokens only**: All styling uses `var(--*)` CSS custom properties defined in `globals.css`. Check what tokens exist before using them. Do NOT hardcode colors, font sizes, or spacing values.
- **Read `globals.css` for the `card-pricing` class**: Do NOT guess or recreate this class. Read the file to understand what it provides before layering additional styles.
- **Rule 8**: Do NOT install any new npm packages. `next/image`, `next/link`, built-in `useState` — everything needed is already available.

---

## Design Decisions (Do Not Re-Litigate)

From Design Doc §G — these decisions are final:

| Decision | Outcome | Rationale |
|---|---|---|
| Annual/monthly toggle as client island | `PricingToggle.tsx` with `"use client"` | Parent page stays static server component; toggle is a JS enhancement |
| Slot counter from env var | `NEXT_PUBLIC_FOUNDING_MEMBER_SLOTS_REMAINING` baked in at build time | Tom updates env var + redeploys to change the counter — no backend API needed |
| "14-day free trial" language | **Removed everywhere** | Replaced with Founding Member offer; FAQ now addresses the absence of a free trial |
| `professionalFeatures` array | **Deleted** — replaced with `teamsFeatures` | Tier is named "Teams", not "Professional" — clean up the old naming completely |
| Feature type coloring | `"shipped"` = green check, `"coming_2026"` = clock icon + muted text, `"future"` = dash + muted text | See §D.1.6 in design doc for icon specs |
| `WaitlistForm` on early-access page | **No changes** — used as-is | Existing form already handles name, email, trade, and company size |

---

## Pre-Work: Establish Regression Baseline

Before touching any file:

```bash
cd <repo>/frontend

# Marketing has no test suite — verify baseline is empty:
pnpm --filter marketing test 2>&1 | tail -5
# Expected output: 0 passed, 0 failed (or "no test files found")
```

Record the output. This batch does not add tests (marketing test suite is a known gap — see `frontend/apps/marketing/README.md`). The Phase 2 verification is build + lint only.

> **Note**: Do NOT attempt to create a test suite for this batch. Adding tests to the marketing app is out of scope. The verified output is a successful `pnpm --filter marketing build` and `pnpm --filter marketing lint`.

---

## Pre-Work: Read These Source Files

Read each of these with `read_file` before writing any code:

```
frontend/apps/marketing/src/app/pricing/page.tsx
  ← Understand existing structure, CSS classes, component patterns, JSON-LD shape

frontend/apps/marketing/src/app/early-access/page.tsx
  ← Understand existing hero, value bullets, steps section, trust strip patterns

frontend/apps/marketing/src/app/globals.css
  ← REQUIRED: Identify what card-pricing, btn-primary, btn-secondary, section-padding,
    container-marketing, hero-gradient, text-section-title, text-hero classes do.
    Also identify all var(--*) tokens available. Do NOT use a token that isn't defined here.

frontend/apps/marketing/src/components/WaitlistForm.tsx
  ← Understand the existing component API (props, source param) — do NOT modify this file

frontend/apps/marketing/.env.example
  ← Understand existing env vars before adding new ones
```

Also run to confirm the file structure:

```bash
find frontend/apps/marketing/src/app/pricing -type f
find frontend/apps/marketing/src/app/early-access -type f
find frontend/apps/marketing/src/components -name "*.tsx" | head -20
```

---

## Context: What This Batch Does

| # | Change | File | Type |
|---|---|---|---|
| 1 | New `PricingToggle` client component — annual/monthly toggle + all 3 pricing cards | `src/app/pricing/PricingToggle.tsx` | New file |
| 2 | Rewrite pricing page — 3-tier table, usage strip, Founding Member banner, updated FAQs | `src/app/pricing/page.tsx` | Full rewrite |
| 3 | Rewrite early-access page — Founding Member framing, slot counter, commitments section, referral callout | `src/app/early-access/page.tsx` | Full rewrite |
| 4 | Add env var to `.env.example` | `frontend/apps/marketing/.env.example` | Add 2 lines |

---

## STEP 1 — Create `PricingToggle.tsx` (New Client Component)

**File**: `frontend/apps/marketing/src/app/pricing/PricingToggle.tsx`

This is a `"use client"` island that manages the annual/monthly toggle state and renders all three pricing cards. The parent `page.tsx` will import this and render it within the pricing cards section.

**Pricing data** (hardcoded in this file — not a prop, not an API call):

```typescript
type BillingCycle = "annual" | "monthly";

interface FeatureItem {
  label: string;
  type: "shipped" | "coming_2026" | "future";
}

interface TierConfig {
  name: string;
  tagline: string;
  annualPrice: number;
  monthlyPrice: number;
  badge?: string;
  highlighted?: boolean;  // true = brand-outlined card (Teams)
  features: FeatureItem[];
  addonNote?: string;
  ctaLabel: string;
  ctaHref: string;
  ctaVariant: "primary" | "secondary";
}
```

**Starter tier features** (exact labels from `gtm-feature-tier-matrix-v1.md §19`):
```typescript
[
  { label: "Unlimited customers, jobs, quotes, invoices", type: "shipped" },
  { label: "Voice-to-quote AI — dictate a scope in 30 seconds (60 min/mo included)", type: "shipped" },
  { label: "NEC code calculations via voice", type: "shipped" },
  { label: "iOS + Android app — works offline in basements", type: "shipped" },
  { label: "GPS clock-in / clock-out + photo documentation", type: "shipped" },
  { label: "Customer accepts quotes + pays invoices online", type: "shipped" },
  { label: "QuickBooks sync + Google Calendar sync", type: "shipped" },
  { label: "Dispatch board with conflict detection — up to 5 field techs", type: "shipped" },
  { label: "Customer SMS + automated appointment reminders (100 SMS/mo)", type: "shipped" },
  { label: "Job profitability tracker (real-time ETC)", type: "shipped" },
  { label: "Invoice sign-off with customer signature", type: "coming_2026" },
  { label: "Automated review request after job closes", type: "coming_2026" },
]
```

**Teams tier features**:
```typescript
[
  { label: "Everything in Starter", type: "shipped" },
  { label: "25 field tech dispatch slots (240 Voice AI min/mo, 500 SMS/mo)", type: "shipped" },
  { label: "At-risk jobs dashboard — budget deviation alerts", type: "shipped" },
  { label: "4-class conflict detection (double-booking, drive time, skill, QB sync)", type: "shipped" },
  { label: "Recurring jobs — daily / weekly / monthly / annual", type: "coming_2026" },
  { label: "Live dispatcher GPS map — see every truck in real time", type: "coming_2026" },
  { label: "Good / Better / Best tiered quote presentation", type: "coming_2026" },
  { label: "Revenue by period + tech performance dashboard", type: "coming_2026" },
  { label: "Customer portal — quotes, invoices, service requests", type: "coming_2026" },
  { label: "Automated quote follow-up + late invoice reminders", type: "coming_2026" },
  { label: "Mobile job checklists + safety forms", type: "coming_2026" },
  { label: "Inventory / parts tracking + low-stock alerts", type: "coming_2026" },
]
```

**Enterprise tier features**:
```typescript
[
  { label: "Everything in Teams", type: "shipped" },
  { label: "75 field tech dispatch slots (1,000 Voice AI min/mo, 2,500 SMS/mo)", type: "shipped" },
  { label: "Up to 10 Telnyx phone numbers included", type: "shipped" },
  { label: "Dedicated account manager + onboarding call", type: "shipped" },
  { label: "4-hour SLA support response", type: "shipped" },
  { label: "Location-based inventory (shop stock + per-truck)", type: "coming_2026" },
  { label: "Multi-location job + dispatch management", type: "future" },
  { label: "Public REST API + webhook events", type: "future" },
  { label: "Zapier integration", type: "future" },
  { label: "SSO / SAML single sign-on", type: "future" },
]
```

**Feature list rendering**:
- `"shipped"` items: Green checkmark SVG (copy the existing SVG from `pricing/page.tsx`'s `FeatureList` component). Text color: `var(--neutral-700)`.
- `"coming_2026"` items: Clock icon SVG (design: brand-200 circle background, neutral-400 stroke — create a simple clock SVG inline, or use a simple `⏱` emoji + hide with `aria-hidden`). Item text: `var(--neutral-400)`. Append `" — Coming 2026"` in a `<span>` with `var(--neutral-400)` and `font-style: italic`.
- `"future"` items: Dash/minus icon (neutral-200 circle, neutral-400 stroke — or `—` character). Item text: `var(--neutral-400)`. Append `" — Coming Soon"` in a `<span>`.

**Toggle UI**:
```html
<!-- Two-option pill toggle — centered above cards -->
<div class="flex items-center justify-center gap-0 mb-10 rounded-full p-1"
  style="background: var(--neutral-100); display: inline-flex">
  <button
    onClick={() => setCycle("annual")}
    class="px-5 py-2 rounded-full text-sm font-medium transition-colors"
    style={cycle === "annual"
      ? { background: "var(--white)", color: "var(--neutral-900)", boxShadow: "var(--shadow-sm)" }
      : { background: "transparent", color: "var(--neutral-500)" }
    }
  >
    Billed Annually — Save 17%
  </button>
  <button
    onClick={() => setCycle("monthly")}
    ...same pattern...
  >
    Billed Monthly
  </button>
</div>
```

Default state: `"annual"` (annual prices shown by default).

**Price display under each tier name**:
- Price number: `text-section-title font-bold` (matches existing page pattern)
- `/mo` suffix: `text-base mb-2` in `var(--neutral-600)`
- Billing note below price:
  - Annual: `"$[price × 12] billed annually"` — `text-sm` in `var(--neutral-500)`
  - Monthly: `"Cancel anytime"` — `text-sm` in `var(--neutral-500)`

**CTA buttons**:
- `ctaVariant: "primary"` → use `.btn-primary` class
- `ctaVariant: "secondary"` → use `.btn-secondary` class
- Render as `<Link href={ctaHref} className={...}>` (Next.js Link)

**Add-on notes**: Render below the feature list (above the CTA) as a small callout:
```html
<p class="text-xs px-3 py-2 rounded-lg mb-4"
  style="color: var(--neutral-500); background: var(--surface-marketing)">
  {tier.addonNote}
</p>
```

**Intermediate verification** after Step 1 — confirm TypeScript compiles before proceeding:
```bash
cd <repo>/frontend
pnpm --filter marketing exec tsc --noEmit 2>&1 | tail -10
```
Fix any errors before proceeding to Step 2.

---

## STEP 2 — Rewrite `pricing/page.tsx`

**File**: `frontend/apps/marketing/src/app/pricing/page.tsx`

This is a server component (no `"use client"`). It imports `PricingToggle` (from Step 1) and renders it within the pricing cards section.

Read the existing file before rewriting to preserve:
- The outer `<>` fragment wrapper pattern with JSON-LD script injection
- The `section` → `div.container-marketing` nesting pattern
- The existing `FeatureList` inner component (it is used in `PricingToggle` now, not in `page.tsx` directly — but its SVG icon design is the reference for the shipped checkmark)

**New page structure** (implement each section in order):

### Section 1 — Hero (`var(--surface-marketing)` background)

```tsx
<section className="section-padding" style={{ background: "var(--surface-marketing)" }} aria-labelledby="pricing-heading">
  <div className="container-marketing text-center">
    <h1 id="pricing-heading" className="text-section-title mb-4" style={{ color: "var(--neutral-900)" }}>
      Simple Pricing for Every Shop Size.
    </h1>
    <p className="text-section-subtitle mb-10" style={{ color: "var(--neutral-600)" }}>
      No per-user fees. Ever. Pay only for the usage that scales with your crew.
    </p>
  </div>
</section>
```

### Section 2 — Pricing Cards (`var(--white)` background)

```tsx
<section className="section-padding" style={{ background: "var(--white)" }} aria-label="Pricing tiers">
  <div className="container-marketing">
    <PricingToggle />
  </div>
</section>
```

`PricingToggle` renders the toggle + all three cards internally.

### Section 3 — Usage Limits Strip (`var(--surface-marketing-alt)` background)

4 items, `flex flex-wrap justify-center gap-8 py-12`:

| Item | Label | Detail | Overage |
|---|---|---|---|
| Voice AI | "Voice AI Minutes" | "60 / 240 / 1,000 per month by plan" | "+$0.05/min over" |
| SMS | "SMS Segments" | "100 / 500 / 2,500 per month by plan" | "+$0.05/seg over" |
| Dispatch Slots | "Dispatch Slots" | "5 / 25 / 75 field tech slots by plan" | "Add-ons available" |
| Users | "User Accounts" | "Unlimited on all plans" | "Always free" |

Each item renders as a centered `<div>` with: label (sm font-semibold neutral-900), detail (xs neutral-500), overage note (xs neutral-400).

### Section 4 — Founding Member Banner (`var(--alert-50)` background)

Read the `NEXT_PUBLIC_FOUNDING_MEMBER_SLOTS_REMAINING` env var:

```typescript
const slotsRemaining = process.env.NEXT_PUBLIC_FOUNDING_MEMBER_SLOTS_REMAINING ?? "25";
```

Render:
```tsx
<section className="py-8" style={{ background: "var(--alert-50)", borderTop: "1px solid var(--alert-200)" }}>
  <div className="container-marketing text-center">
    <p className="text-base font-semibold mb-1" style={{ color: "var(--neutral-900)" }}>
      🔥 <strong>Founding Member Program — {slotsRemaining} of 25 slots remaining</strong>
    </p>
    <p className="text-sm mb-3" style={{ color: "var(--neutral-600)" }}>
      Teams features at $49/month for your first 12 months. In exchange, quarterly feedback calls.
    </p>
    <Link href="/early-access" className="btn-primary" style={{ display: "inline-block" }}>
      Learn more and claim your slot →
    </Link>
  </div>
</section>
```

### Section 5 — FAQ (`var(--white)` background)

**Replace all 8 existing FAQs** with the 9 new FAQs from design doc §D.1.9. Copy the exact questions and answers from that section.

Keep the existing `<details>`/`<summary>` pattern and `faq-item` / `faq-button` CSS classes. Just replace the data.

### Section 6 — Bottom CTA (`var(--surface-marketing)` background)

```tsx
<h2>Ready to get started?</h2>
<p>Join the Founding Member program or contact us with questions.</p>
<div class="flex flex-col sm:flex-row gap-4 justify-center">
  <Link href="/early-access" className="btn-primary">Get Founding Member Access</Link>
  <Link href="/contact" className="btn-secondary">Contact Us</Link>
</div>
```

**Updated metadata and JSON-LD** — copy the exact values from design doc §D.1.10. The JSON-LD `FAQPage` must include all 9 new FAQs. Add three `Offer` schema objects to the `@graph` (one per tier) with `priceSpecification` using the annual price as `price`.

**Intermediate verification** after Step 2:
```bash
pnpm --filter marketing build 2>&1 | tail -20
```
Fix any build errors before proceeding to Step 3.

---

## STEP 3 — Rewrite `early-access/page.tsx`

**File**: `frontend/apps/marketing/src/app/early-access/page.tsx`

Server component. Read the existing file before rewriting.

**New page structure** (implement each section in order):

### Hero Section (`.hero-gradient .hero-padding`)

```tsx
const slotsRemaining = process.env.NEXT_PUBLIC_FOUNDING_MEMBER_SLOTS_REMAINING ?? "25";
```

- H1: `"Become a Founding Member"`
- Subtitle: `"We're opening 25 spots for contractors who want Teams features at $49/month for the first year. In exchange, we ask for your honest feedback every quarter. That's the deal."`
- Slot counter badge (between subtitle and form card):
  ```tsx
  <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full text-sm font-semibold mb-8"
    style={{ background: "var(--alert-100)", color: "var(--neutral-900)", border: "1px solid var(--alert-400)" }}>
    🔥 {slotsRemaining} of 25 founding member slots remaining
  </div>
  ```
- Form card: `<WaitlistForm source="early_access_page" />` (unchanged, no props changes)

### Section 2 — What You Get (`var(--white)` background)

4 value cards — use the exact `whatYouGet` data from design doc §D.2.3. Keep the same 2×2 grid layout as the existing page.

### Section 3 — What You Commit To (`var(--surface-marketing)` background) **[NEW]**

Heading: `"Here's What We're Asking For"`
Subtitle: `"This isn't a giveaway. It's a mutual commitment — you give us honest feedback, we give you the best deal we'll ever offer."`

4 commitment cards using same visual style as Section 2 cards. Use the exact `commitments` data from design doc §D.2.4.

### Section 4 — How It Works (`var(--white)` background)

3 numbered steps — use the updated `steps` data from design doc §D.2.5. Keep the existing numbered circle + text layout.

### Section 5 — Referral Incentive Callout (`var(--brand-50)` background) **[NEW]**

```tsx
<section className="py-12" style={{ background: "var(--brand-50)", borderTop: "1px solid var(--brand-200)" }}>
  <div className="container-marketing text-center max-w-2xl mx-auto">
    <p className="text-xl font-semibold mb-2" style={{ color: "var(--neutral-900)" }}>
      Know another contractor who'd benefit?
    </p>
    <p className="text-base" style={{ color: "var(--neutral-600)" }}>
      Refer a contractor who becomes a Founding Member before your year ends, and we'll extend
      your $49/month founding rate for an extra 6 months — automatically, no codes needed.
    </p>
  </div>
</section>
```

### Section 6 — Trust Strip (`var(--white)` background)

Replace existing copy with:
```
No credit card required to apply · 12-month commitment at $49/mo · Transitions to $149/mo after founding year · Cancel anytime
```

**Updated metadata and JSON-LD** — copy exact values from design doc §D.2.8. Update breadcrumb name from `"Early Access"` to `"Founding Member Program"`.

---

## STEP 4 — Add Environment Variable to `.env.example`

**File**: `frontend/apps/marketing/.env.example`

Add after the existing `NEXT_PUBLIC_CAREERS_OPEN_ROLES` line:

```bash
# Founding Member Program — slots remaining counter (update + redeploy to change)
# Default: 25 (full capacity). Tom manually decrements as slots fill.
NEXT_PUBLIC_FOUNDING_MEMBER_SLOTS_REMAINING=25
```

Also add to `frontend/apps/marketing/.env.local` (Tom's local file — **not committed to git**):
```bash
NEXT_PUBLIC_FOUNDING_MEMBER_SLOTS_REMAINING=25
```

---

## Final Verification

### Phase 1 — Targeted checks (run after each step)

```bash
cd <repo>/frontend

# TypeScript check (marketing has no separate check-types script — use exec):
pnpm --filter marketing exec tsc --noEmit 2>&1 | tail -10

# Build check:
pnpm --filter marketing build 2>&1 | tail -20

# Lint check:
pnpm --filter marketing lint 2>&1 | tail -10
```

### Phase 2 — Full canonical verification (run once at the end, before DoD sign-off)

```bash
cd <repo>/frontend && pnpm --filter marketing exec tsc --noEmit && pnpm --filter marketing build && pnpm --filter marketing lint && echo "=== MKT-B7 FINAL VERIFICATION COMPLETE ==="
```

> **Marketing has no test suite** — the Phase 2 command does NOT include a test run. The verification is TypeScript + build + lint only.

> **Any failure must be fixed before declaring the batch done.** Zero tolerance for TypeScript errors, build failures, or ESLint warnings.

---

## Definition of Done — MKT-B7

Update `dev-docs/analysis/pilot-launch-plan.md` §P0 when each item is done:

- [ ] Pre-modification baseline captured (`pnpm --filter marketing test` output recorded — expected: 0 tests)
- [ ] Design doc fully read before writing any code (§A–§I)
- [ ] `gtm-feature-tier-matrix-v1.md §19` read — exact feature labels confirmed
- [ ] All mandatory source files read (`pricing/page.tsx`, `early-access/page.tsx`, `globals.css`, `WaitlistForm.tsx`, `.env.example`)
- [ ] `globals.css` read — `card-pricing`, `btn-primary`, `btn-secondary`, all used CSS tokens verified to exist
- [ ] **STEP 1**: `src/app/pricing/PricingToggle.tsx` created — toggle state + all 3 pricing cards + feature type rendering
- [ ] **STEP 1**: TypeScript compiles clean after `PricingToggle.tsx` created
- [ ] **STEP 2**: `src/app/pricing/page.tsx` rewritten — hero, pricing section (imports PricingToggle), usage limits strip, Founding Member banner with env var slot counter, FAQ (9 new questions), bottom CTA
- [ ] **STEP 2**: "Professional" tier name fully removed — replaced with "Teams" throughout
- [ ] **STEP 2**: "14-day free trial" language fully removed — replaced with Founding Member offer
- [ ] **STEP 2**: Metadata and JSON-LD updated (new title, description, 9-FAQ FAQPage, 3 Offer schema objects)
- [ ] **STEP 2**: Build passes after pricing page rewrite
- [ ] **STEP 3**: `src/app/early-access/page.tsx` rewritten — Founding Member framing, slot counter badge, updated value cards, new commitments section, updated steps, referral callout, updated trust strip
- [ ] **STEP 3**: `NEXT_PUBLIC_FOUNDING_MEMBER_SLOTS_REMAINING` env var used correctly in early-access hero (default `"25"` when not set)
- [ ] **STEP 3**: Metadata updated (Founding Member Program title + description)
- [ ] **STEP 3**: JSON-LD breadcrumb updated from "Early Access" to "Founding Member Program"
- [ ] **STEP 4**: `frontend/apps/marketing/.env.example` updated with `NEXT_PUBLIC_FOUNDING_MEMBER_SLOTS_REMAINING`
- [ ] `frontend/apps/marketing/.env.local` updated with `NEXT_PUBLIC_FOUNDING_MEMBER_SLOTS_REMAINING=25`
- [ ] Zero TypeScript errors (`tsc --noEmit` passes)
- [ ] Zero ESLint warnings (`pnpm --filter marketing lint` clean)
- [ ] Build passes (`pnpm --filter marketing build` succeeds)
- [ ] Pricing page manually verified in browser (dev server): annual/monthly toggle works; all three tiers render; coming-soon features are visually muted; slot counter shows "25 of 25 slots remaining"; Founding Member banner visible
- [ ] Early-access page manually verified in browser: slot counter badge visible in hero; commitments section renders; referral callout renders; trust strip updated
- [ ] **Phase 2 FULL verification command passes** (`=== MKT-B7 FINAL VERIFICATION COMPLETE ===`):
  ```bash
  cd <repo>/frontend && pnpm --filter marketing exec tsc --noEmit && pnpm --filter marketing build && pnpm --filter marketing lint && echo "=== MKT-B7 FINAL VERIFICATION COMPLETE ==="
  ```
- [ ] Completion Summary added to `pilot-launch-plan.md` §P0 Marketing Website section

---

## Completion Summary

After all Definition of Done items are complete, add a **Completion Summary** subsection to `dev-docs/analysis/pilot-launch-plan.md` §P0 using this format:

```markdown
### MKT-B7 — Pricing Page Redesign + Founding Member Program: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot React Engineer
**Baseline**: 0 tests (no marketing test suite)
**Final**: 0 tests (no marketing test suite added — out of scope)
**Build**: ✅ Pass — TypeScript errors: 0, ESLint warnings: 0

#### What Was Accomplished

- Pricing page fully redesigned: 3-tier table (Starter/Teams/Enterprise), annual/monthly toggle, usage limits strip, Founding Member banner with env-var slot counter, 9 updated FAQs
- `PricingToggle.tsx` client island created — manages annual/monthly state, renders all pricing cards with feature type visual treatment (shipped/coming_2026/future)
- "Professional" tier renamed to "Teams" throughout; "14-day free trial" language removed
- Early-access page redesigned as Founding Member Program: slot counter badge, commitments section, updated steps, referral incentive callout
- `NEXT_PUBLIC_FOUNDING_MEMBER_SLOTS_REMAINING` env var added to `.env.example` and `.env.local`
- Metadata and JSON-LD updated on both pages

#### Files Changed / Created

| File | Action |
|---|---|
| `frontend/apps/marketing/src/app/pricing/PricingToggle.tsx` | Created — client island, toggle + pricing cards |
| `frontend/apps/marketing/src/app/pricing/page.tsx` | Replaced — full rewrite |
| `frontend/apps/marketing/src/app/early-access/page.tsx` | Replaced — full rewrite |
| `frontend/apps/marketing/.env.example` | Updated — added `NEXT_PUBLIC_FOUNDING_MEMBER_SLOTS_REMAINING` |
| `frontend/apps/marketing/.env.local` | Updated — added `NEXT_PUBLIC_FOUNDING_MEMBER_SLOTS_REMAINING=25` |
```
