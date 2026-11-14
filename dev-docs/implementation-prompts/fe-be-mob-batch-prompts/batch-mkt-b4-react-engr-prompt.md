# Implementation Prompt: MKT-B4 — Marketing Website Design & Visual Polish

**Mode**: `pilot-react-engineer`
**Batch**: MKT-B4
**Plan link**: `dev-docs/analysis/pilot-launch-plan.md` — P0 section
**Design doc**: `dev-docs/marketing-analysis/design-specs/mkt-b4-design-spec.md`
**Estimate**: 2–3 hours
**Platform**: Marketing website only (`frontend/apps/marketing/`)
**Backend companion**: None — no new API endpoints
**Prerequisite**: MKT-B3 complete ✅

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-react-engineer/react-engineer-rules.md`** — in full
- **`dev-docs/marketing-analysis/design-specs/mkt-b4-design-spec.md`** — every section (A–I)

**Critical rules for this batch:**

- **Rule 8**: No new npm dependencies. `next/image` is already installed (Next.js built-in). Zero new packages.
- **Rule 10**: Fix any test failure before declaring the batch done.
- **Marketing app scope rule**: ALL changes confined to `frontend/apps/marketing/`. Do NOT touch `apps/web`, `apps/mobile`, or any `packages/` directory.
- **CSS variable rule**: MKT-B4-01 adds variable definitions to `globals.css`. Do NOT change any existing variable values — only ADD new definitions that are currently missing. Changing existing values could break the intentional blue hero sections.
- **Image blocking rule**: MKT-B4-06 (trade page images) requires actual `.jpg` files to exist at `public/trades/`. Before attempting MKT-B4-06, check if the files exist. If they don't — skip MKT-B4-06, add a comment, and notify Tom. Do NOT attempt to implement with missing images.
- **No invented content**: SVG illustrations in the design doc are specifications, not starting points — implement them as written.

---

## What This Batch Does

Six tasks fixing design issues discovered during visual review. MKT-B4-01 alone resolves ~80% of the visual problems (white nav, visible form inputs) by defining missing CSS tokens.

| Task | File | Change Type | Blocks on Tom? |
|---|---|---|---|
| MKT-B4-01 | `src/app/globals.css` | Add 30 missing CSS variable definitions | No |
| MKT-B4-02 | `src/components/HeroWaitlistForm.tsx` | Email placeholder text fix | No |
| MKT-B4-03 | `src/app/page.tsx` | White separator between metrics + CTA sections | No |
| MKT-B4-04 | `src/app/about/page.tsx` | Replace `👤` founder placeholder with company illustration SVG | No |
| MKT-B4-05 | `src/app/features/page.tsx` | Add 4-feature illustration above feature grid | No |
| MKT-B4-06 | `src/components/trades/TradePageTemplate.tsx` | Wire `next/image` for trade hero images | **Yes — needs Tom's JPG files** |

---

## Pre-Work: Establish Regression Baseline

Before touching any file:

```bash
cd <repo>/frontend

pnpm --filter marketing test 2>&1 | tail -8
```

Record exact counts. These must still pass at the end.

---

## Pre-Work: Read These Source Files

Read each of these with `read_file` before writing any code:

```
frontend/apps/marketing/src/app/globals.css
  ← Read the full file — know exactly where to insert new CSS variables

frontend/apps/marketing/src/components/HeroWaitlistForm.tsx
  ← Find the placeholder text and label text locations

frontend/apps/marketing/src/app/page.tsx
  ← Find Section 8 (metrics) and Section 9 (final CTA) to identify insertion point for separator

frontend/apps/marketing/src/app/about/page.tsx
  ← Find the founder photo placeholder div — understand its outer container structure

frontend/apps/marketing/src/app/features/page.tsx
  ← Read the full file — find the hero section and feature grid boundary

frontend/apps/marketing/src/components/trades/TradePageTemplate.tsx
  ← Find the illustration container div — understand its current structure
```

Also check if trade images exist:
```bash
ls frontend/apps/marketing/public/trades/
```

If `.jpg` files are NOT present (only `.svg`), skip MKT-B4-06 entirely.

---

## Task MKT-B4-01 — CSS Variable Definitions

**File**: `frontend/apps/marketing/src/app/globals.css`

Add the following to the `:root {}` block, after the existing variable definitions (after the `--white-30` and `--shadow-drop-md` lines near the end of the `:root` block):

```css
/* White opacity variants — referenced throughout hero sections, nav, and form cards */
--white: #ffffff;
--white-95: rgba(255, 255, 255, 0.95);
--white-85: rgba(255, 255, 255, 0.85);
--white-8: rgba(255, 255, 255, 0.8);
--white-7: rgba(255, 255, 255, 0.7);
--white-6: rgba(255, 255, 255, 0.6);
--white-55: rgba(255, 255, 255, 0.55);
--white-5: rgba(255, 255, 255, 0.5);
--white-4: rgba(255, 255, 255, 0.4);
--white-15: rgba(255, 255, 255, 0.15);
--white-12: rgba(255, 255, 255, 0.12);
--white-1: rgba(255, 255, 255, 0.1);
--white-08: rgba(255, 255, 255, 0.08);
--white-05: rgba(255, 255, 255, 0.05);

/* White border tokens */
--border-white-20: 1px solid rgba(255, 255, 255, 0.2);
--border-white-15: 1px solid rgba(255, 255, 255, 0.15);
--border-white-12: 1px solid rgba(255, 255, 255, 0.12);

/* Shadow tokens */
--shadow-xs: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
--shadow-sm: 0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px -1px rgba(0, 0, 0, 0.1);
--shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -2px rgba(0, 0, 0, 0.1);
--shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -4px rgba(0, 0, 0, 0.1);
--shadow-xl: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1);
--shadow-2xl: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
```

Do NOT change any existing variable values. Do NOT remove any existing variables. Only ADD these new entries.

**Expected visual effect**: Nav bar becomes white/frosted glass, hero email input becomes visible white, early access form card becomes white background, all hero text and overlay effects render correctly.

---

## Task MKT-B4-02 — Email Placeholder Text

**File**: `frontend/apps/marketing/src/components/HeroWaitlistForm.tsx`

Two changes:
1. `placeholder="Enter your work email"` → `placeholder="Enter your email"`
2. Find the `<label htmlFor="hero-email" className="sr-only">` text → change `Enter your work email` → `Enter your email`

---

## Task MKT-B4-03 — White Separator Between Blue Sections

**File**: `frontend/apps/marketing/src/app/page.tsx`

Find Section 8 (the metrics bar section using `.hero-gradient` class) and Section 9 (the final CTA section using `background: "var(--brand-600)"`). They are adjacent — find the exact boundary between their closing `</section>` and opening `<section` tags.

Insert between them:

```tsx
{/* ── White separator — prevents adjacent blue sections from merging ── */}
<div className="py-8" style={{ background: "var(--white)" }} aria-hidden="true" />
```

---

## Task MKT-B4-04 — About Page Founder Illustration

**File**: `frontend/apps/marketing/src/app/about/page.tsx`

Find the founder photo placeholder — a `<div>` with class `w-56 h-56 rounded-2xl` containing a `text-5xl` emoji `👤` and a `<p>` with "Tom Lang" text.

Keep the outer container div (the `w-56 h-56 rounded-2xl` div with its background and border styles) exactly as-is. Replace ONLY the inner content with this SVG:

```tsx
<svg
  viewBox="0 0 224 224"
  fill="none"
  xmlns="http://www.w3.org/2000/svg"
  className="w-full h-full p-6"
  aria-label="Pilot for Trades — Built for the field"
>
  {/* Background circle */}
  <circle cx="112" cy="112" r="100" stroke="var(--brand-200)" strokeWidth="2" fill="var(--brand-50)" />

  {/* Phone silhouette */}
  <rect x="78" y="50" width="68" height="114" rx="10" stroke="var(--brand-600)" strokeWidth="2" fill="white" />
  <rect x="85" y="62" width="54" height="78" rx="4" fill="var(--brand-50)" />

  {/* Waveform bars on phone screen */}
  <rect x="97" y="84" width="6" height="18" rx="3" fill="var(--brand-600)" opacity="0.7" />
  <rect x="107" y="78" width="6" height="30" rx="3" fill="var(--brand-600)" />
  <rect x="117" y="86" width="6" height="14" rx="3" fill="var(--brand-600)" opacity="0.7" />

  {/* Gear icon top-right */}
  <circle cx="170" cy="60" r="20" stroke="var(--brand-400)" strokeWidth="2" fill="var(--brand-50)" />
  <circle cx="170" cy="60" r="8" stroke="var(--brand-600)" strokeWidth="2" fill="white" />
  <line x1="170" y1="44" x2="170" y2="40" stroke="var(--brand-600)" strokeWidth="2" strokeLinecap="round" />
  <line x1="170" y1="76" x2="170" y2="80" stroke="var(--brand-600)" strokeWidth="2" strokeLinecap="round" />
  <line x1="154" y1="60" x2="150" y2="60" stroke="var(--brand-600)" strokeWidth="2" strokeLinecap="round" />
  <line x1="186" y1="60" x2="190" y2="60" stroke="var(--brand-600)" strokeWidth="2" strokeLinecap="round" />

  {/* Signal arcs */}
  <path d="M58 140 Q112 120 166 140" stroke="var(--brand-200)" strokeWidth="1.5" fill="none" />
  <path d="M48 155 Q112 130 176 155" stroke="var(--brand-100)" strokeWidth="1.5" fill="none" />

  {/* Home bar */}
  <rect x="99" y="154" width="26" height="4" rx="2" fill="var(--brand-200)" />
</svg>
```

---

## Task MKT-B4-05 — Features Page Illustration

**File**: `frontend/apps/marketing/src/app/features/page.tsx`

Read the full file first. Find the hero section (containing the page `<h1>` and subtitle). The feature cards grid starts after it.

Insert this illustration **after the subtitle paragraph and before the feature cards grid**:

```tsx
{/* Features overview illustration */}
<div
  className="flex items-center justify-center mb-14"
  aria-hidden="true"
>
  <svg
    viewBox="0 0 560 180"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    className="w-full max-w-2xl"
  >
    {/* Voice AI card */}
    <rect x="10" y="50" width="90" height="80" rx="14" fill="var(--brand-50)" stroke="var(--brand-200)" strokeWidth="1.5" />
    <path d="M55 73a6 6 0 0 1 6 6v10a6 6 0 0 1-12 0V79a6 6 0 0 1 6-6z" stroke="var(--brand-600)" strokeWidth="1.5" fill="none" />
    <path d="M45 93v2a10 10 0 0 0 20 0v-2" stroke="var(--brand-600)" strokeWidth="1.5" strokeLinecap="round" fill="none" />
    <line x1="55" y1="105" x2="55" y2="110" stroke="var(--brand-600)" strokeWidth="1.5" strokeLinecap="round" />
    <text x="55" y="148" textAnchor="middle" fontSize="10" fill="var(--brand-600)" fontWeight="600">Voice AI</text>

    {/* Arrow */}
    <path d="M100 90h30" stroke="var(--brand-200)" strokeWidth="1.5" strokeDasharray="4 3" />
    <path d="M126 85l8 5-8 5" stroke="var(--brand-400)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" fill="none" />

    {/* Profitability card */}
    <rect x="130" y="50" width="90" height="80" rx="14" fill="var(--brand-50)" stroke="var(--brand-200)" strokeWidth="1.5" />
    <polyline points="145,115 157,100 168,105 180,88 192,92 203,78" stroke="var(--brand-600)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" fill="none" />
    <text x="175" y="148" textAnchor="middle" fontSize="10" fill="var(--brand-600)" fontWeight="600">Profitability</text>

    {/* Arrow */}
    <path d="M220 90h30" stroke="var(--brand-200)" strokeWidth="1.5" strokeDasharray="4 3" />
    <path d="M246 85l8 5-8 5" stroke="var(--brand-400)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" fill="none" />

    {/* Dispatch card */}
    <rect x="250" y="50" width="90" height="80" rx="14" fill="var(--brand-50)" stroke="var(--brand-200)" strokeWidth="1.5" />
    <rect x="262" y="66" width="66" height="46" rx="4" stroke="var(--brand-600)" strokeWidth="1.5" fill="none" />
    <line x1="262" y1="76" x2="328" y2="76" stroke="var(--brand-200)" strokeWidth="1" />
    <rect x="268" y="82" width="14" height="12" rx="2" fill="var(--brand-600)" opacity="0.5" />
    <rect x="286" y="82" width="14" height="12" rx="2" fill="var(--brand-600)" opacity="0.8" />
    <rect x="304" y="82" width="14" height="12" rx="2" fill="var(--brand-600)" opacity="0.4" />
    <text x="295" y="148" textAnchor="middle" fontSize="10" fill="var(--brand-600)" fontWeight="600">Dispatch</text>

    {/* Arrow */}
    <path d="M340 90h30" stroke="var(--brand-200)" strokeWidth="1.5" strokeDasharray="4 3" />
    <path d="M366 85l8 5-8 5" stroke="var(--brand-400)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" fill="none" />

    {/* Customer Comms card */}
    <rect x="370" y="50" width="90" height="80" rx="14" fill="var(--brand-50)" stroke="var(--brand-200)" strokeWidth="1.5" />
    <path d="M380 72h60a4 4 0 0 1 4 4v22a4 4 0 0 1-4 4h-50l-10 8v-8h0a4 4 0 0 1 0-4V76a4 4 0 0 1 4-4z" stroke="var(--brand-600)" strokeWidth="1.5" fill="none" />
    <line x1="390" y1="82" x2="430" y2="82" stroke="var(--brand-200)" strokeWidth="1.5" />
    <line x1="390" y1="90" x2="424" y2="90" stroke="var(--brand-200)" strokeWidth="1.5" />
    <text x="415" y="148" textAnchor="middle" fontSize="10" fill="var(--brand-600)" fontWeight="600">Comms</text>

    {/* Arrow */}
    <path d="M460 90h20" stroke="var(--brand-200)" strokeWidth="1.5" strokeDasharray="4 3" />
    <path d="M476 85l8 5-8 5" stroke="var(--brand-400)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" fill="none" />

    {/* QuickBooks card */}
    <rect x="484" y="50" width="66" height="80" rx="14" fill="var(--brand-50)" stroke="var(--brand-200)" strokeWidth="1.5" />
    <text x="517" y="95" textAnchor="middle" fontSize="22" fontWeight="700" fill="var(--brand-600)">QB</text>
    <text x="517" y="148" textAnchor="middle" fontSize="10" fill="var(--brand-600)" fontWeight="600">QuickBooks</text>
  </svg>
</div>
```

The exact insertion point depends on the page structure — read the file before placing it.

---

## Task MKT-B4-06 — Trade Page Hero Images (Conditional)

**File**: `frontend/apps/marketing/src/components/trades/TradePageTemplate.tsx`

> ⚠️ **First verify images exist**:
> ```bash
> ls frontend/apps/marketing/public/trades/*.jpg
> ```
> If no `.jpg` files → **skip this task**. Leave a comment `{/* TODO MKT-B4-06: enable next/image when trade hero JPGs are available in public/trades/ */}` and proceed. Do NOT implement with missing files.

**If images exist**, make these changes:

1. Add import at top of file:
```tsx
import Image from "next/image";
```

2. Find the illustration container div (the `<div className="flex-1 max-w-md..."` block with the emoji). The inner container has `aspectRatio: "16/10"` and `role="img"`. Change this container to add `position: "relative"` to its inline style, then replace the inner `<div className="text-center p-8">` with:

```tsx
<Image
  src={`/trades/${trade}-hero.jpg`}
  alt={heroImageAlt}
  fill
  className="object-cover object-center rounded-2xl"
  sizes="(max-width: 768px) 100vw, 50vw"
  priority
/>
```

---

## Two-Phase Final Verification

### Phase 1 — Targeted Tests

```bash
cd <repo>/frontend
pnpm --filter marketing test 2>&1 | tail -8
```

Pass criteria: Same count as baseline. Zero new failures.

### Phase 2 — Full Verification (run once at end)

```bash
cd <repo>/frontend && pnpm --filter marketing exec tsc --noEmit 2>&1 | tail -5 && pnpm --filter marketing build 2>&1 | tail -10 && pnpm --filter marketing lint 2>&1 | tail -5 && echo "=== MKT-B4 FINAL VERIFICATION COMPLETE ==="
```

Pass criteria: `=== MKT-B4 FINAL VERIFICATION COMPLETE ===` appears. Zero TypeScript errors. Build succeeds.

> **Note**: Standard Phase 2 command targets `web/mobile/ui` packages. This batch is marketing-app only — command is correctly scoped to `--filter marketing`.

---

## Definition of Done

- [ ] Pre-modification regression baseline captured
- [ ] Design doc fully read before writing any code
- [ ] All mandatory source files read before modifying
- [ ] MKT-B4-01: All CSS variable definitions added to `globals.css` — nav bar is now white/frosted, form cards are white, hero inputs are visible
- [ ] MKT-B4-02: Email placeholder says "Enter your email" (not "work email")
- [ ] MKT-B4-03: White separator exists between metrics bar and final CTA sections on homepage
- [ ] MKT-B4-04: About page founder placeholder replaced with company/product SVG illustration
- [ ] MKT-B4-05: Features page has illustration above feature grid
- [ ] MKT-B4-06: Trade page images wired (OR skipped with comment + Tom notified if JPGs not present)
- [ ] No files outside `frontend/apps/marketing/` were modified
- [ ] Phase 1: Tests pass (same count as baseline)
- [ ] **Phase 2 FULL verification passes** (`=== MKT-B4 FINAL VERIFICATION COMPLETE ===`):
  ```bash
  cd <repo>/frontend && pnpm --filter marketing exec tsc --noEmit 2>&1 | tail -5 && pnpm --filter marketing build 2>&1 | tail -10 && pnpm --filter marketing lint 2>&1 | tail -5 && echo "=== MKT-B4 FINAL VERIFICATION COMPLETE ==="
  ```

---

## Completion Summary

When all work is complete and both verification phases pass:

```
## MKT-B4 Completion Summary

**Date**: [date]
**Phase 1 (tests)**: [X tests, Y pass, Z fail] — baseline was [baseline count]
**Phase 2 (build)**: [Pass / Fail] — TypeScript errors: [N]

**Tasks completed**:
- MKT-B4-01: CSS variables ✅
- MKT-B4-02: Email placeholder ✅
- MKT-B4-03: White separator ✅
- MKT-B4-04: About SVG illustration ✅
- MKT-B4-05: Features illustration ✅
- MKT-B4-06: Trade images [✅ wired / ⏭️ skipped — awaiting Tom's JPGs]

**Notes**: [Any deviations, edge cases, or items for Tom review]
```
