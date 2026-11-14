# Pilot for Trades — Logo Usage Guide

## Logo Assets Inventory

| File                     | Description                              | Use Case                                      |
| ------------------------ | ---------------------------------------- | --------------------------------------------- |
| `logo-primary.svg`       | Full lockup: icon + wordmark             | Header, hero sections, email headers          |
| `logo-icon.svg`          | Icon only (56×56 artboard)               | Favicon, app icons, small-space use           |
| `logo-wordmark.svg`      | Wordmark only, no icon                   | Certain header contexts, co-branded materials |
| `logo-primary-dark.svg`  | Full lockup on dark/gradient backgrounds | Hero gradient sections, footer, dark UI       |
| `logo-icon-dark.svg`     | Icon only, dark background variant       | Dark nav, dark app headers                    |
| `logo-wordmark-dark.svg` | Wordmark only, dark background variant   | Dark sections                                 |

---

## 1. Logo Design Rationale

### Icon Concept: "The Ascent Bar"

The icon combines two universally understood signals:

- **Ascending bar chart** — financial growth, job profitability, tracking performance
- **Upward trend arrow** — direction, momentum, forward progress

This is deliberately adjacent to the Grok-generated reference logo (v2, July 2026), which uses the same growth-chart metaphor. The bars + diagonal arrow evoke a field tech's "are my margins up?" question answered visually. No clipart tools, no circuit boards, no hard hats.

**Why it works for the target audience (electricians 22–45):**

- Recognizable as "business performance" without being corporate
- The diagonal arrow reads as confidence and precision — a pilot navigating upward
- At 16px (favicon), 4 ascending bars + arrow still read as a coherent mark
- At 300px (hero/header), the metallic-style depth from the bars creates premium feel

### Wordmark

- **"Pilot"** — 800 weight, 28px, navy (#181d66). Heavy, grounded, serious.
- **"FOR TRADES"** — 600 weight, 14px, 1.5 tracking, brand indigo (#3b43d6). Uppercase spaced type acts as a descriptor strip, lighter in visual weight.
- Font stack: Inter → system fallback. Matches the web dashboard exactly.

---

## 2. Color Specifications

| Context          | Icon bg                                 | Wordmark "Pilot" | Wordmark "FOR TRADES"    |
| ---------------- | --------------------------------------- | ---------------- | ------------------------ |
| Light background | `#3b43d6`                               | `#181d66`        | `#3b43d6`                |
| Dark/gradient bg | `rgba(255,255,255,0.15)` + white stroke | `#ffffff`        | `rgba(255,255,255,0.70)` |

**Brand palette (hex, for partner submissions):**

- Primary: `#3b43d6` (brand-600)
- Deep: `#181d66` (brand-900)
- Light accent: `#adb8ff` (brand-200)

---

## 3. Minimum Size Requirements

| Variant               | Minimum Width | Minimum Height |
| --------------------- | ------------- | -------------- |
| Full lockup (primary) | 120px         | 27px           |
| Icon only             | 16px          | 16px           |
| Wordmark only         | 80px          | 27px           |

Do not display the full lockup below 120px wide. At small sizes (< 32px), use icon only.

---

## 4. Clear Space Rules

Maintain a minimum clear space equal to **50% of the icon height** on all four sides of the logo.

For the 56px icon: minimum 28px clearspace on all sides.
For the full 56px-tall lockup: minimum 28px clearspace top/bottom, 28px left of icon, 28px right of wordmark.

---

## 5. Approved Color Combinations

| Background                             | Logo Variant            | Notes                      |
| -------------------------------------- | ----------------------- | -------------------------- |
| White (`#ffffff`)                      | `logo-primary.svg`      | Preferred default          |
| Light neutral (`#fafaf9`, `#f5f5f4`)   | `logo-primary.svg`      | Marketing page backgrounds |
| Brand gradient (`#3b43d6` → `#181d66`) | `logo-primary-dark.svg` | Hero sections              |
| Dark slate (`#1c1917`, `#292524`)      | `logo-primary-dark.svg` | Footer, dark UI            |
| Brand color solid (`#3b43d6`)          | `logo-primary-dark.svg` | CTA banners                |
| Photography with dark overlay          | `logo-primary-dark.svg` | Blog hero images           |

---

## 6. What Not to Do

1. **Do not stretch or distort.** Maintain the original viewBox aspect ratio.
2. **Do not recolor.** Only use the approved color combinations above. Do not apply arbitrary hex colors to the wordmark.
3. **Do not add drop shadows.** The icon has intentional opacity layering; external shadows degrade the mark.
4. **Do not use the full lockup below 120px wide.** Switch to icon-only below that threshold.
5. **Do not place the light variant on dark backgrounds.** Always use the `-dark` SVG on gradients or dark surfaces.
6. **Do not add a border or container to the icon when it is displayed inline.** The rounded-corner square is the container — do not add another.
7. **Do not animate the logo** without explicit brand team approval.
8. **Do not change letter spacing** on the wordmark — the tracking is intentional.

---

## 7. Export Specifications (for partner submissions)

All PNG exports at 512×512 and 1024×1024 should be generated from `logo-icon.svg` with the following settings:

- **Background**: `#3b43d6` fill (no transparency, no alpha channel — required for Apple App Store)
- **Padding**: 10% of canvas dimension on each side (icon occupies 80% of canvas)
- **Color profile**: sRGB
- **File format**: PNG-24

For partner submissions requiring "logo on white" (QuickBooks, Stripe):

- Use `logo-primary.svg`
- Canvas: white background, 1024px wide × 230px tall (logo centered)

---

## 8. Favicon Implementation

Use `logo-icon.svg` as the source for all favicon formats:

```html
<link rel="icon" href="/brand/logo-icon.svg" type="image/svg+xml" />
<link rel="icon" href="/favicon.ico" sizes="any" />
<link rel="apple-touch-icon" href="/brand/apple-touch-icon.png" />
```

The SVG favicon renders at 16px, 32px, and 64px with the 4 ascending bars still legible.
