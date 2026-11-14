# Implementation Prompt: MKT-B8 — GTM Alignment: Homepage, Pricing, and Founding Tester Page

**Mode**: Pilot React Engineer
**Batch**: MKT-B8
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §P0 Marketing Website
**Design doc**: `dev-docs/marketing-analysis/design-specs/mkt-b8-design-spec.md`
**GTM authority**: `dev-docs/marketing-analysis/pilot-gtm-strategy-v1.md`
**Estimated session**: 3–4 hours
**Platform**: Marketing site only (`frontend/apps/marketing/`)
**Backend companion**: None — pure frontend, no backend changes
**Pure frontend — no backend changes needed**

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-react-engineer/react-engineer-rules.md`** — in full
- **`dev-docs/marketing-analysis/design-specs/mkt-b8-design-spec.md`** — every section (A–H)

Critical rules for this batch:

- **Marketing app only**: This batch touches ONLY `frontend/apps/marketing/`. Do NOT modify anything in `apps/web/`, `apps/mobile/`, or `packages/ui/`.
- **Delete `PricingToggle.tsx` first**: This file must be deleted before touching `pricing/page.tsx`. The new pricing page is a pure server component with no client island.
- **No `pnpm sync-api-types`**: The marketing site does NOT use `@pilot/shared-types`. Skip that step.
- **No test suite**: The marketing app has zero test files. Regression baseline is 0 tests. Phase 2 verification is build + lint only.
- **CSS token verification is mandatory**: Before using any `var(--white-05)`, `var(--white-55)`, or other token in the muted trade pills, search `globals.css` to confirm the token exists. Fallback to inline `rgba()` if it doesn't.
- **Homepage is 1,042 lines — make only 6 changes**: Do not restructure, reorder, or reformat sections outside the 6 specified changes. The risk of a large-page edit is breaking something that works; make only what the spec describes.
- **`HeroWaitlistForm` import must be removed**: If you replace the `<HeroWaitlistForm />` JSX but leave the import on line 3, the TypeScript compiler will emit an unused import warning. Remove both.
- **Rule 8**: No new npm packages. Everything needed is already installed.

---

## Design Decisions (Do Not Re-Litigate)

From Design Doc §G and `pilot-gtm-strategy-v1.md` — these decisions are final:

| Decision | Outcome | Rationale |
|---|---|---|
| Single pricing plan | $49/month, no tiers shown | Three-tier approach was premature; single price matches buyer psychology for this ICP |
| Annual billing toggle | **Removed entirely** — `PricingToggle.tsx` deleted | No pricing history to validate a discount; reintroduces friction; Founding Tester offer is already the best deal |
| "Get Early Access" CTA | **Replaced with "Be One of the First"** everywhere | Matches GTM §8.3 manifesto language; more natural for tradesperson audience |
| Trade pills | Electrical active, Plumbing/HVAC muted + "Coming Soon" | Electrical-only messaging today; plumbing/HVAC shown as real but not yet |
| Testimonials | All three rewritten as electricians | Plumbing/HVAC testimonials contradict electrical-only positioning |
| "Founding Member Program" | **Replaced with Founding Tester framing** — personal, direct | "Founders" is startup-culture language; "one of the first" is more natural for contractors |
| Hero top padding | Inline `paddingTop` override on homepage hero section only | Reduces top space ~50% without affecting other pages that use `hero-padding-y` |

---

## Pre-Work: Establish Regression Baseline

Before touching any file:

```bash
cd <repo>/frontend

# Marketing has no test suite — verify:
pnpm --filter marketing test 2>&1 | tail -5
# Expected: 0 tests, or "no test files found"
```

Record the output. The Phase 2 verification is build + lint only — no test run.

---

## Pre-Work: Read These Source Files

Read each with `read_file` before writing any code:

```
frontend/apps/marketing/src/app/page.tsx
  ← Read the full 1,042-line file. Identify exact line numbers for:
    (1) HeroWaitlistForm import (line 3)
    (2) hero <section> opening tag (line 72)
    (3) subtitle paragraph (line ~102)
    (4) trade pills div (line ~111)
    (5) HeroWaitlistForm JSX (line ~137)
    (6) testimonials array (line ~897)
    (7) final CTA Link text (line ~1034)

frontend/apps/marketing/src/app/pricing/page.tsx
  ← Understand existing structure to rewrite cleanly. Identify:
    - How FeatureList component is defined (copy it for reuse)
    - How allPlansFeatures strip is built (reuse the same pattern)
    - How faq-item / faq-button CSS classes are used

frontend/apps/marketing/src/app/pricing/PricingToggle.tsx
  ← Confirm this file exists before deleting it

frontend/apps/marketing/src/app/early-access/page.tsx
  ← Read the full post-MKT-B7 version before rewriting

frontend/apps/marketing/src/app/globals.css
  ← Search for:
    - `--white-05` — does this token exist?
    - `--white-55` — does this token exist?
    - `--white-8` — confirm (used in existing subtitle)
    - `card-pricing` — what styles does this class provide?
    - `hero-padding` — confirm it uses padding-y (both top and bottom)
    - `btn-primary`, `btn-secondary`, `btn-white` — confirm they exist
```

Also run:
```bash
# Confirm PricingToggle.tsx exists before deleting:
find frontend/apps/marketing/src/app/pricing -type f

# Check which components import HeroWaitlistForm to make sure only page.tsx uses it:
grep -r "HeroWaitlistForm" frontend/apps/marketing/src/ --include="*.tsx"
```

---

## Context: What This Batch Does

| # | Change | File | Type |
|---|---|---|---|
| 1 | Delete `PricingToggle.tsx` | `src/app/pricing/PricingToggle.tsx` | **Delete** |
| 2 | Full rewrite of pricing page — single-plan card, updated FAQ | `src/app/pricing/page.tsx` | Full rewrite |
| 3 | 6 targeted homepage edits (metadata, padding, subtitle, pills, CTA, testimonials) | `src/app/page.tsx` | 6 edits |
| 4 | Full rewrite of early-access page — Founding Tester framing | `src/app/early-access/page.tsx` | Full rewrite |

---

## STEP 1 — Delete `PricingToggle.tsx`

**Action**: Delete the file `frontend/apps/marketing/src/app/pricing/PricingToggle.tsx`.

In the terminal:
```bash
rm frontend/apps/marketing/src/app/pricing/PricingToggle.tsx
```

Confirm deletion:
```bash
find frontend/apps/marketing/src/app/pricing -type f
# Should show only page.tsx remaining
```

After deletion, confirm the build still fails gracefully (it will, because `pricing/page.tsx` still imports `PricingToggle`) — that's expected. The next step fixes it.

---

## STEP 2 — Rewrite `pricing/page.tsx`

**File**: `frontend/apps/marketing/src/app/pricing/page.tsx`

This is a pure server component — no `"use client"`, no imports from `PricingToggle`. Read the existing file before rewriting to preserve:
- The outer `<>` fragment + JSON-LD `<script>` pattern
- The `FeatureList` inner component (copy it into the new file — same green checkmark SVG)
- The `<details>`/`<summary>` FAQ pattern with `faq-item` and `faq-button` CSS classes
- The `allPlansFeatures` pill strip pattern (adapt for the new included-items strip)

**Implement sections in order:**

### Section 1 — Metadata + JSON-LD

Use exact values from design doc §D.2.2.

JSON-LD changes from MKT-B7:
- Keep `BreadcrumbList` — update the position 2 name to "Pricing"  
- Update `FAQPage` with only the 8 new FAQs from design doc §D.2.6
- Remove any `Offer` objects for Teams/Enterprise added in MKT-B7 — keep only the `SoftwareApplication` offer at `price: "49"`

### Section 2 — Hero (`var(--surface-marketing)` background)

```tsx
<section className="section-padding" style={{ background: "var(--surface-marketing)" }} aria-labelledby="pricing-heading">
  <div className="container-marketing text-center">
    <h1 id="pricing-heading" className="text-section-title mb-4" style={{ color: "var(--neutral-900)" }}>
      One price. Everything included.
    </h1>
    <p className="text-section-subtitle mb-0" style={{ color: "var(--neutral-600)" }}>
      $49/month for solo and small electrical contractors — unlimited users, voice AI, offline mobile, QuickBooks sync, and real-time job profitability.
    </p>
  </div>
</section>
```

### Section 3 — Single Pricing Card (`var(--white)` background)

Implement the single centered card from design doc §D.2.3–D.2.4:
- Copy the `FeatureList` component from the existing file (the green SVG checkmark version)
- Feature list: 12 items, all `✅` shipped — exact labels from design doc §D.2.3
- Card width: `max-w-lg mx-auto`
- Price: `$49` with `/month` suffix
- Sub-note: "Everything included. Cancel anytime."
- CTA: `<Link href="/early-access" className="btn-primary text-center">Be One of the First</Link>`
- Footer note under CTA: `"More plans as we grow — for now, one price for everyone."`

### Section 4 — Included-at-a-Glance Strip (`var(--surface-marketing-alt)` background)

6 items — adapt the existing `allPlansFeatures` pill pattern. New data:
```typescript
const includedItems = [
  { icon: "🎙️", label: "120 Voice AI min/mo" },
  { icon: "💬", label: "200 SMS/mo" },
  { icon: "👥", label: "Unlimited users" },
  { icon: "📋", label: "Unlimited jobs" },
  { icon: "📱", label: "Offline mobile" },
  { icon: "🔄", label: "QuickBooks sync" },
];
```

### Section 5 — FAQ (`var(--white)` background)

Keep the existing `<details>`/`<summary>` markup pattern exactly. Replace `const faqs = [...]` with the 8 new FAQ items from design doc §D.2.6.

### Section 6 — Bottom CTA (`var(--surface-marketing)` background)

```tsx
<h2>Ready to try it on a real job?</h2>
<p>The first group of electricians gets six months free, then $49/month locked in for life.</p>
<div className="flex flex-col sm:flex-row gap-4 justify-center">
  <Link href="/early-access" className="btn-primary">Be One of the First</Link>
  <Link href="/contact" className="btn-secondary">Contact Us</Link>
</div>
```

**Intermediate verification** after Step 2:
```bash
cd <repo>/frontend
pnpm --filter marketing exec tsc --noEmit 2>&1 | tail -10
pnpm --filter marketing build 2>&1 | tail -15
```
Fix any errors before Step 3.

---

## STEP 3 — Homepage `page.tsx`: 6 Targeted Edits

**File**: `frontend/apps/marketing/src/app/page.tsx`

Read the full file first. Make **only** these 6 changes, in order. Do not touch any other section.

### Edit 1 — Metadata: Remove trial language

Update `metadata.description` (line ~9) and `openGraph.description` (line ~14):
```typescript
// New description:
"Pilot for Trades: Voice AI quoting and real-time job profitability for solo and small electrical contractors. Know your margin on every job. $49/month, everything included."

// New openGraph.description:
"Voice AI quoting and real-time job profitability for solo electricians. $49/month, everything included."
```

### Edit 2 — Hero section top padding reduction

Add `style={{ paddingTop: "clamp(3.5rem, 5.5vw, 5.5rem)" }}` to the hero `<section>`:

```tsx
// BEFORE:
<section className="hero-gradient hero-padding" aria-labelledby="hero-heading">

// AFTER:
<section
  className="hero-gradient hero-padding"
  style={{ paddingTop: "clamp(3.5rem, 5.5vw, 5.5rem)" }}
  aria-labelledby="hero-heading"
>
```

### Edit 3 — Subtitle: "solo electricians"

Find the subtitle paragraph (line ~102). Change `solo contractors` to `solo electricians`:
```tsx
// BEFORE:
...so solo contractors can focus on
billable work, not paperwork at 9 PM.

// AFTER:
...so solo electricians can focus on
billable work, not paperwork at 9 PM.
```

### Edit 4 — Trade pills: Electrical active, Plumbing/HVAC muted

Replace the entire trade pills `<div>` (lines ~111–133) with the new version from design doc §D.1 Change 4.

**Before using `var(--white-05)` and `var(--white-55)`**: Search `globals.css` for these tokens. If they exist, use them. If not, use:
- `var(--white-05)` → `rgba(255,255,255,0.05)`
- `var(--white-55)` → `rgba(255,255,255,0.55)`

The muted pills should be noticeably dimmer than the electrical pill — visually subordinate.

### Edit 5 — Remove HeroWaitlistForm, add two CTA buttons

Two actions:

**Action A**: Remove the import on line 3:
```typescript
// DELETE this line entirely:
import HeroWaitlistForm from "../components/HeroWaitlistForm";
```

**Action B**: Replace line ~137 (`<HeroWaitlistForm />`) with:
```tsx
{/* CTA buttons */}
<div className="flex flex-col sm:flex-row gap-4">
  <Link href="/early-access" className="btn-primary">
    Be One of the First
  </Link>
  <Link
    href="/features#voice-ai"
    className="text-base font-semibold no-underline flex items-center gap-2"
    style={{ color: "var(--white-8)" }}
  >
    See How It Works →
  </Link>
</div>
```

Verify `var(--white-8)` exists in `globals.css` (it's used on the existing subtitle, so it should).

### Edit 6 — Testimonials and final CTA

**Testimonials**: Replace the three testimonial objects in the data array (lines ~897–925) with the three new electrician testimonials from design doc §D.1 Change 6. The rendering code (the `.map()`) stays unchanged — only the data array changes.

**Final CTA**: Find the bottom CTA section (Section 9, line ~1034). Change the Link text:
```tsx
// BEFORE:
<Link href="/early-access" className="btn-white">
  Get Early Access
</Link>

// AFTER:
<Link href="/early-access" className="btn-white">
  Be One of the First
</Link>
```

**Intermediate verification** after Step 3:
```bash
pnpm --filter marketing exec tsc --noEmit 2>&1 | tail -10
pnpm --filter marketing build 2>&1 | tail -15
```
Fix any errors before Step 4.

---

## STEP 4 — Rewrite `early-access/page.tsx`

**File**: `frontend/apps/marketing/src/app/early-access/page.tsx`

Read the existing post-MKT-B7 file in full before rewriting. Preserve:
- The outer `<>` + JSON-LD `<script>` pattern
- The `<WaitlistForm source="early_access_page" />` component import and usage (unchanged)
- The visual style of value bullet cards (icon + title + desc on `var(--surface-marketing)` background)
- The numbered steps visual (brand-600 circle + title + desc)

**New page structure** (implement in order):

### Section 1 — Hero (`.hero-gradient .hero-padding`)

Full hero padding preserved here — **do NOT add the padding-top override** that the homepage uses. Only the homepage hero gets the reduced top padding.

- H1: `"Be One of the First."`
- Subtitle (3 sentences from design doc §D.3.2):
  > "I'm building Pilot myself. I'm an electrical engineer, and I need a small number of electrical contractors willing to run it on real jobs and tell me what I got wrong. No trial period, no complicated setup — six months free, then $49/month locked in for as long as you stay."
- Form card: `<WaitlistForm source="early_access_page" />` (unchanged)

### Section 2 — "What You're Signing Up For" (`var(--white)` background)

3 cards using the same visual style as the existing value bullets. Data from design doc §D.3.3.

**Section heading**: "What You're Signing Up For"

No subtitle needed under the heading.

### Section 3 — "The Deal" (`var(--surface-marketing)` background)

**Section heading**: "The Deal"

Two-column grid. Left column: "What you get". Right column: "What we ask for."

```tsx
<div className="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-2xl mx-auto">
  <div>
    <h3 className="text-base font-semibold mb-4" style={{ color: "var(--neutral-900)" }}>
      What you get
    </h3>
    <ul className="flex flex-col gap-3 list-none p-0 m-0">
      {[
        "Six months free, full access",
        "$49/month locked in after that",
        "Direct line to Tom",
        "Every new feature as it ships",
      ].map((item) => (
        <li key={item} className="flex items-start gap-2">
          <span style={{ color: "var(--margin-600)" }}>✓</span>
          <span className="text-base" style={{ color: "var(--neutral-700)" }}>{item}</span>
        </li>
      ))}
    </ul>
  </div>
  <div>
    <h3 className="text-base font-semibold mb-4" style={{ color: "var(--neutral-900)" }}>
      What we ask for
    </h3>
    <ul className="flex flex-col gap-3 list-none p-0 m-0">
      {[
        "Use it on real jobs — not a sandbox",
        "Be willing to answer 'what's wrong with this?'",
        "Honest feedback, not cheerleading",
        "That's it",
      ].map((item) => (
        <li key={item} className="flex items-start gap-2">
          <span style={{ color: "var(--neutral-400)" }}>→</span>
          <span className="text-base" style={{ color: "var(--neutral-700)" }}>{item}</span>
        </li>
      ))}
    </ul>
  </div>
</div>
```

### Section 4 — "What Happens Next" (`var(--white)` background)

3 numbered steps — same visual as the existing steps in the current file. Data from design doc §D.3.5.

**Heading**: "What Happens Next"

### Section 5 — Trust Strip (`var(--white)` background)

Single centered line:
```tsx
<section className="py-8" style={{ background: "var(--white)" }}>
  <div className="container-marketing text-center">
    <p className="text-sm" style={{ color: "var(--neutral-500)" }}>
      No credit card required. Tom reviews each signup personally.
    </p>
  </div>
</section>
```

### Metadata + JSON-LD

Use exact values from design doc §D.3.7.

JSON-LD: Update breadcrumb name from "Founding Member Program" to "Be One of the First."

---

## Final Verification

### Phase 1 — Targeted checks (run after each step)

```bash
cd <repo>/frontend

# TypeScript:
pnpm --filter marketing exec tsc --noEmit 2>&1 | tail -10

# Build:
pnpm --filter marketing build 2>&1 | tail -20

# Lint:
pnpm --filter marketing lint 2>&1 | tail -10
```

### Phase 2 — Full canonical verification (run once at the end)

```bash
cd <repo>/frontend && pnpm --filter marketing exec tsc --noEmit && pnpm --filter marketing build && pnpm --filter marketing lint && echo "=== MKT-B8 FINAL VERIFICATION COMPLETE ==="
```

> **Marketing has no test suite** — Phase 2 does not include a test run. TypeScript + build + lint is the complete verification gate.

---

## Definition of Done — MKT-B8

Update `dev-docs/analysis/pilot-launch-plan.md` §P0 Marketing Website when each item is done:

- [ ] Baseline captured (`pnpm --filter marketing test` — expected: 0 tests)
- [ ] Design doc read in full (§A–§H)
- [ ] All mandatory source files read before any edits
- [ ] `globals.css` searched for `--white-05`, `--white-55`, `--white-8` token availability
- [ ] **STEP 1**: `PricingToggle.tsx` deleted — confirmed removed from filesystem
- [ ] **STEP 2**: `pricing/page.tsx` rewritten — single-plan card, 12-item feature list, 8 new FAQs, no client components, no tier comparison
- [ ] **STEP 2**: `PricingToggle` import removed from pricing page (it no longer exists)
- [ ] **STEP 2**: Teams/Enterprise `Offer` JSON-LD objects removed — only $49 SoftwareApplication offer remains
- [ ] **STEP 2**: Build passes after pricing rewrite
- [ ] **STEP 3**: `HeroWaitlistForm` import removed from homepage `page.tsx`
- [ ] **STEP 3**: Homepage metadata trial language removed from `description` and `openGraph.description`
- [ ] **STEP 3**: Hero section top padding reduced via inline `paddingTop` style override
- [ ] **STEP 3**: Subtitle changed to "solo electricians"
- [ ] **STEP 3**: Trade pills: Electrical active (full opacity), Plumbing/HVAC muted + "Coming Soon"
- [ ] **STEP 3**: Hero CTA replaced — "Be One of the First" → `/early-access` + "See How It Works →" → `/features#voice-ai`
- [ ] **STEP 3**: All three testimonials rewritten as electricians (different sub-segments)
- [ ] **STEP 3**: Final CTA button text changed to "Be One of the First"
- [ ] **STEP 3**: Build passes after homepage edits
- [ ] **STEP 4**: `early-access/page.tsx` rewritten — "Be One of the First" H1, founder-voiced subtitle, 3-card "What You're Signing Up For" section, "The Deal" two-column section, 3 updated steps, simple trust strip
- [ ] **STEP 4**: "Founding Member Program" language completely removed from early-access page
- [ ] **STEP 4**: 25-slot counter, `NEXT_PUBLIC_FOUNDING_MEMBER_SLOTS_REMAINING` references removed
- [ ] **STEP 4**: Commitments bullet list and referral incentive section removed
- [ ] **STEP 4**: JSON-LD breadcrumb updated to "Be One of the First"
- [ ] **STEP 4**: `WaitlistForm` component used unchanged — no prop changes
- [ ] Zero TypeScript errors (`tsc --noEmit` clean)
- [ ] Zero ESLint warnings (`lint` clean)
- [ ] Build passes (`pnpm --filter marketing build` succeeds)
- [ ] Manually verify in browser: homepage hero has reduced top space; trade pills show Electrical active + Plumbing/HVAC muted; two CTA buttons visible; pricing page shows single card (no toggle, no tiers); early-access page shows "Be One of the First" framing
- [ ] **Phase 2 FULL verification passes** (`=== MKT-B8 FINAL VERIFICATION COMPLETE ===`):
  ```bash
  cd <repo>/frontend && pnpm --filter marketing exec tsc --noEmit && pnpm --filter marketing build && pnpm --filter marketing lint && echo "=== MKT-B8 FINAL VERIFICATION COMPLETE ==="
  ```
- [ ] Completion Summary added to `pilot-launch-plan.md` §P0

---

## Completion Summary

After all Definition of Done items are complete, add a **Completion Summary** subsection to `dev-docs/analysis/pilot-launch-plan.md` §P0 Marketing Website using this format:

```markdown
### MKT-B8 — GTM Alignment: Homepage, Pricing, Founding Tester Page: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot React Engineer
**Baseline**: 0 tests (no marketing test suite)
**Final**: 0 tests (no marketing test suite — out of scope)
**Build**: ✅ Pass — TypeScript errors: 0, ESLint warnings: 0

#### What Was Accomplished

- `PricingToggle.tsx` deleted — three-tier pricing entirely removed
- `pricing/page.tsx` rewritten: single $49/month plan card, 12-item feature list, 8 updated FAQs, no client components
- Homepage: HeroWaitlistForm removed; hero padding reduced; subtitle updated to "solo electricians"; trade pills: Electrical active + Plumbing/HVAC muted; two CTA buttons ("Be One of the First" + "See How It Works →"); all three testimonials rewritten as electricians; trial language removed from metadata
- `early-access/page.tsx` rewritten: Founding Tester framing ("Be One of the First"), founder-voiced hero copy, "What You're Signing Up For" 3-card section, "The Deal" two-column table, updated steps, simple trust strip

#### Files Changed / Created

| File | Action |
|---|---|
| `frontend/apps/marketing/src/app/pricing/PricingToggle.tsx` | Deleted |
| `frontend/apps/marketing/src/app/pricing/page.tsx` | Replaced — single-plan rewrite |
| `frontend/apps/marketing/src/app/page.tsx` | Updated — 6 targeted edits |
| `frontend/apps/marketing/src/app/early-access/page.tsx` | Replaced — Founding Tester rewrite |
```
