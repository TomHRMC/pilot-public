# Implementation Prompt: MKT-B5 — Features Page Section Images

**Mode**: `pilot-react-engineer`
**Batch**: MKT-B5
**Plan link**: `dev-docs/analysis/pilot-launch-plan.md` — P0 section
**Design doc**: `dev-docs/marketing-analysis/design-specs/mkt-b5-design-spec.md`
**Estimate**: 30–45 minutes
**Platform**: Marketing website only (`frontend/apps/marketing/`)
**Backend companion**: None
**Prerequisite**: MKT-B4 complete ✅ + all 11 feature images in `public/features/` + `about-hero.jpg` in `public/`

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-react-engineer/react-engineer-rules.md`** — in full
- **`dev-docs/marketing-analysis/design-specs/mkt-b5-design-spec.md`** — every section (A–H)

**Critical rules for this batch:**

- **Rule 8**: No new npm dependencies. `next/image` is built into Next.js. Zero new packages.
- **Rule 10**: Fix any test failure before declaring done.
- **Marketing app scope**: ALL changes confined to `frontend/apps/marketing/`. Do NOT touch other packages.
- **Image file prerequisite**: Before implementing, verify all 11 image files exist:
  ```bash
  ls frontend/apps/marketing/public/features/
  ```
  You should see: `feature-voice-ai.jpg`, `feature-quoting.jpg`, `feature-dispatch.jpg`, `feature-field-ops.jpg`, `feature-profitability.jpg`, `feature-comms.jpg`, `feature-invoicing.jpg`, `feature-quickbooks.jpg`, `feature-mobile.jpg`, `feature-security.jpg`, `feature-help.jpg`. If any are missing → STOP and notify Tom.
- **Filename mapping**: `communications` feature id maps to `feature-comms.jpg` (shorter filename). The `FEATURE_IMAGE_MAP` constant handles this — do not hardcode paths directly.

---

## What This Batch Does

One file, three tasks. Replaces the emoji placeholder ("Screenshot coming in beta") in all 11 feature sections on the `/features` page with real `next/image` components.

| Task | File | Change |
|---|---|---|
| MKT-B5-01 | `src/app/features/page.tsx` | Add `import Image from "next/image"` |
| MKT-B5-02 | `src/app/features/page.tsx` | Add `FEATURE_IMAGE_MAP` constant |
| MKT-B5-03 | `src/app/features/page.tsx` | Replace all 11 illustration placeholder divs with `next/image` |
| MKT-B5-04 | `src/app/about/page.tsx` | Replace about page SVG illustration with `next/image` loading `about-hero.jpg` |

---

## Pre-Work: Verify Images and Establish Regression Baseline

```bash
cd <repo>/frontend
pnpm --filter marketing test 2>&1 | tail -8
```

Record exact counts. These must still pass at end.

---

## Pre-Work: Verify Images

```bash
# Verify all 11 feature images exist
ls frontend/apps/marketing/public/features/

# Verify about-hero.jpg exists
ls frontend/apps/marketing/public/about-hero.jpg
```

Expected output: 11 `.jpg` files. If any missing → STOP.

Then read the source files:
```
frontend/apps/marketing/src/app/features/page.tsx
  ← Read the full file — understand the features.map() structure before modifying

frontend/apps/marketing/src/app/about/page.tsx
  ← Find the founder section illustration container — the w-56 h-56 div
```

---

## Task MKT-B5-01 — Add Image Import

**File**: `frontend/apps/marketing/src/app/features/page.tsx`

Add at the top of the file after existing imports:

```tsx
import Image from "next/image";
```

---

## Task MKT-B5-02 — Feature Image Map Constant

**File**: `frontend/apps/marketing/src/app/features/page.tsx`

Add after the `features` array and before the `navLabels` array:

```tsx
/**
 * Maps feature section id to the image filename in public/features/.
 * Note: "communications" id maps to "feature-comms.jpg" (shorter filename).
 */
const FEATURE_IMAGE_MAP: Record<string, string> = {
  "voice-ai": "feature-voice-ai.jpg",
  "quoting": "feature-quoting.jpg",
  "dispatch": "feature-dispatch.jpg",
  "field-ops": "feature-field-ops.jpg",
  "profitability": "feature-profitability.jpg",
  "communications": "feature-comms.jpg",
  "invoicing": "feature-invoicing.jpg",
  "quickbooks": "feature-quickbooks.jpg",
  "mobile": "feature-mobile.jpg",
  "security": "feature-security.jpg",
  "help": "feature-help.jpg",
};
```

---

## Task MKT-B5-03 — Replace Illustration Placeholder

**File**: `frontend/apps/marketing/src/app/features/page.tsx`

Inside the `features.map((f, idx) => ...)` loop, find the `{/* Illustration placeholder */}` block. It looks like:

```tsx
{/* Illustration placeholder */}
<div className="flex-1 w-full max-w-md" aria-hidden="true">
  <div
    className="w-full aspect-video rounded-2xl flex items-center justify-center"
    style={{
      background: "var(--neutral-100)",
      border: "var(--divider-thin) solid var(--neutral-200)",
    }}
  >
    <div className="text-center p-8">
      <span className="text-5xl block mb-3">{f.icon}</span>
      <p
        className="text-sm"
        style={{ color: "var(--neutral-400)" }}
      >
        Screenshot coming in beta
      </p>
    </div>
  </div>
</div>
```

**Replace the entire block with**:

```tsx
{/* Feature illustration image */}
<div className="flex-1 w-full max-w-md">
  <div
    className="w-full aspect-video rounded-2xl overflow-hidden relative"
    style={{ border: "var(--divider-thin) solid var(--neutral-200)" }}
  >
    <Image
      src={`/features/${FEATURE_IMAGE_MAP[f.id]}`}
      alt={`${f.heading} — feature illustration`}
      fill
      className="object-cover object-center"
      sizes="(max-width: 768px) 100vw, 50vw"
      loading={idx === 0 ? "eager" : "lazy"}
    />
  </div>
</div>
```

This replaces the single placeholder block inside the `.map()` — the replacement runs for all 11 features automatically because it's inside the loop.

---

## Task MKT-B5-04 — About Page: Replace SVG with Real Image

**File**: `frontend/apps/marketing/src/app/about/page.tsx`

First, add the import at the top of `about/page.tsx` if not already present:
```tsx
import Image from "next/image";
```

Find the founder section illustration container — a `<div className="shrink-0">` wrapping a `<div className="w-56 h-56 rounded-2xl...">` div (currently containing the SVG illustration added in MKT-B4-04). Replace the entire inner container div and its SVG content with:

```tsx
<div
  className="w-56 h-56 rounded-2xl overflow-hidden relative"
  style={{
    border: "var(--divider-thick) solid var(--brand-200)",
  }}
>
  <Image
    src="/about-hero.jpg"
    alt="Pilot for Trades — built at the intersection of craft and technology"
    fill
    className="object-cover object-center"
    sizes="224px"
    priority
  />
</div>
```

Keep the outer `<div className="shrink-0" aria-hidden="true">` wrapper — only replace the inner container and its contents.

> **Note**: `sizes="224px"` matches the fixed `w-56` (224px) container. `priority` is set because this image is above the fold on the About page and should not lazy-load.

---

## Two-Phase Final Verification

### Phase 1 — Targeted Tests

```bash
cd <repo>/frontend
pnpm --filter marketing test 2>&1 | tail -8
```

### Phase 2 — Full Verification

```bash
cd <repo>/frontend && pnpm --filter marketing exec tsc --noEmit 2>&1 | tail -5 && pnpm --filter marketing build 2>&1 | tail -10 && pnpm --filter marketing lint 2>&1 | tail -5 && echo "=== MKT-B5 FINAL VERIFICATION COMPLETE ==="
```

Pass criteria: `=== MKT-B5 FINAL VERIFICATION COMPLETE ===` appears. Zero TypeScript errors. Build succeeds.

---

## Definition of Done

- [ ] Pre-modification regression baseline captured
- [ ] All 11 feature images verified present in `public/features/`
- [ ] `about-hero.jpg` verified present in `public/`
- [ ] `src/app/features/page.tsx` read in full before modifying
- [ ] `src/app/about/page.tsx` read before modifying
- [ ] MKT-B5-01: `import Image from "next/image"` added to features page
- [ ] MKT-B5-02: `FEATURE_IMAGE_MAP` constant added
- [ ] MKT-B5-03: Illustration placeholder replaced with `next/image` (single change in `.map()` loop covers all 11 features)
- [ ] MKT-B5-04: About page SVG replaced with `next/image` loading `about-hero.jpg`
- [ ] No `aria-hidden` on image containers (real photos are not decorative)
- [ ] No files outside `frontend/apps/marketing/` modified
- [ ] Phase 1: Tests pass (same count as baseline)
- [ ] **Phase 2 FULL verification passes** (`=== MKT-B5 FINAL VERIFICATION COMPLETE ===`):
  ```bash
  cd <repo>/frontend && pnpm --filter marketing exec tsc --noEmit 2>&1 | tail -5 && pnpm --filter marketing build 2>&1 | tail -10 && pnpm --filter marketing lint 2>&1 | tail -5 && echo "=== MKT-B5 FINAL VERIFICATION COMPLETE ==="
  ```

---

## Completion Summary

```
## MKT-B5 Completion Summary

**Date**: [date]
**Phase 1 (tests)**: [X tests, Y pass, Z fail] — baseline was [baseline count]
**Phase 2 (build)**: [Pass / Fail] — TypeScript errors: [N]

**Tasks completed**:
- MKT-B5-01: Image import ✅
- MKT-B5-02: FEATURE_IMAGE_MAP ✅
- MKT-B5-03: Placeholder replaced with next/image (all 11 sections) ✅

**Notes**: [Any deviations, TypeScript warnings, or items for Tom review]
```
