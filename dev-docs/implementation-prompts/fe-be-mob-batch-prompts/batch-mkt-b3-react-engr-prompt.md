# Implementation Prompt: MKT-B3 — Marketing Website Pre-Launch Polish

**Mode**: `pilot-react-engineer`
**Batch**: MKT-B3
**Plan link**: `dev-docs/analysis/pilot-launch-plan.md` — P0 section
**Design doc**: `dev-docs/marketing-analysis/design-specs/mkt-b3-design-spec.md`
**Estimate**: 2–3 hours
**Platform**: Marketing website only (`frontend/apps/marketing/`)
**Backend companion**: None — no new API endpoints

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-react-engineer/react-engineer-rules.md`** — in full
- **`dev-docs/marketing-analysis/design-specs/mkt-b3-design-spec.md`** — every section (A–I)

**Critical rules for this batch:**

- **Rule 8**: No new npm dependencies without first checking what is already installed in `package.json`. This batch installs zero new packages.
- **Rule 10**: If ANY test fails during your work — fix it before declaring the batch done.
- **Marketing app scope rule**: ALL changes in this batch are confined to `frontend/apps/marketing/`. Do NOT touch `apps/web`, `apps/mobile`, or any `packages/` directory.
- **No invented content**: The design doc specifies exact text replacements. Do not rewrite marketing copy, testimonials, or legal language beyond what is specified. Legal wording in particular must match the spec exactly.
- **No new image files**: The hero illustration is inline SVG only. Do not add files to `public/` or use `next/image`.

---

## Pre-Work: Establish Regression Baseline

Before touching any file:

```bash
cd <repo>/frontend

pnpm --filter marketing test 2>&1 | tail -8
```

Record the exact counts. These must still pass at the end of the batch.

> **If any tests are already failing before you start**: Confirm with Tom that this is a known accepted failure before proceeding. Do NOT start implementation with unexplained failing tests.

---

## Pre-Work: Read These Source Files

Read each of these with `read_file` before writing any code:

```
frontend/apps/marketing/src/app/page.tsx
  ← Understand hero section structure, JSON-LD shape, testimonials section

frontend/apps/marketing/src/components/Footer.tsx
  ← Understand footer columns array and copyright line structure

frontend/apps/marketing/src/app/contact/page.tsx
  ← Understand email card JSX and metadata structure

frontend/apps/marketing/src/components/forms/ContactForm.tsx
  ← Find the error fallback string to update

frontend/apps/marketing/src/app/legal/terms/page.tsx
  ← Full file — find all [Pending] placeholders and legal entity mentions

frontend/apps/marketing/src/app/legal/privacy/page.tsx
  ← Full file — find legal entity mentions and contact references

frontend/apps/marketing/src/app/pricing/page.tsx
  ← Full file — find ALL $149 occurrences in metadata, JSON-LD, and display JSX
```

Also confirm the marketing app package name:
```bash
cat frontend/apps/marketing/package.json | grep '"name"'
```

---

## What This Batch Does

This batch makes **no new components, no new API hooks, and no new dependencies**. It is a set of 12 surgical text/SVG edits to existing files in `frontend/apps/marketing/` only. All changes are required for legal compliance, 10DLC carrier approval, or pricing accuracy.

| Task | File | Change Type |
|---|---|---|
| MKT-B3-01 | `src/app/page.tsx` | Replace hero placeholder box with inline SVG illustration |
| MKT-B3-02 | `src/app/page.tsx` | Fix JSON-LD contact email `support@` → `info@` |
| MKT-B3-03 | `src/app/page.tsx` | Remove testimonials placeholder disclaimer text |
| MKT-B3-04 | `src/components/Footer.tsx` | Add HotRMC DBA attribution to copyright line |
| MKT-B3-05 | `src/components/Footer.tsx` | Remove dead "System Status" footer link |
| MKT-B3-06 | `src/app/contact/page.tsx` | Update contact email display + metadata → `info@` |
| MKT-B3-07 | `src/components/forms/ContactForm.tsx` | Update error fallback email → `info@` |
| MKT-B3-08 | `src/app/legal/terms/page.tsx` | Replace `[Pending]` effective date → January 1, 2026 |
| MKT-B3-09 | `src/app/legal/privacy/page.tsx` | DBA wording + `legal@` contact + mobile data sharing clause |
| MKT-B3-10 | `src/app/legal/terms/page.tsx` | DBA intro clause + `legal@` contact |
| MKT-B3-11 | `src/app/pricing/page.tsx` | All `$149` → `$49` (metadata, JSON-LD, display) |
| MKT-B3-12 | `src/app/page.tsx` | Homepage JSON-LD `offers.price` → `"49"` |

---

## Task List

Implement all 12 tasks in the order specified. Each task is a targeted surgical edit — do not refactor surrounding code.

### MKT-B3-01 — Hero Illustration SVG

**File**: `frontend/apps/marketing/src/app/page.tsx`
**Where**: Replace the entire content of the `<div className="w-full aspect-[4/3] rounded-2xl ...">` illustration container in the hero section (the one with the person SVG and "App interface coming soon" text).

**Replace the inner content with this inline SVG illustration:**

```tsx
{/* Hero illustration — mobile voice quoting */}
<svg
  viewBox="0 0 400 300"
  fill="none"
  xmlns="http://www.w3.org/2000/svg"
  className="w-full h-full p-8"
  aria-hidden="true"
>
  {/* Phone device */}
  <rect x="155" y="30" width="90" height="160" rx="14" stroke="var(--brand-200)" strokeWidth="2" fill="var(--white-05)" />
  <rect x="162" y="42" width="76" height="116" rx="6" fill="var(--white-08)" />

  {/* Waveform bars inside screen */}
  <rect x="174" y="88" width="8" height="24" rx="4" fill="var(--brand-600)" opacity="0.8" />
  <rect x="186" y="78" width="8" height="44" rx="4" fill="var(--brand-600)" />
  <rect x="198" y="84" width="8" height="32" rx="4" fill="var(--brand-600)" opacity="0.9" />
  <rect x="210" y="72" width="8" height="56" rx="4" fill="var(--brand-600)" />
  <rect x="222" y="86" width="8" height="28" rx="4" fill="var(--brand-600)" opacity="0.8" />

  {/* Mic dot below waveform */}
  <circle cx="200" cy="140" r="8" stroke="white" strokeWidth="1.5" fill="var(--white-05)" />
  <circle cx="200" cy="140" r="3" fill="white" opacity="0.7" />

  {/* Phone home indicator */}
  <rect x="185" y="178" width="30" height="4" rx="2" fill="var(--brand-200)" opacity="0.5" />

  {/* Floating card 1 — top right: Quote Ready */}
  <rect x="265" y="45" width="110" height="52" rx="10" fill="var(--white-1)" stroke="var(--brand-200)" strokeOpacity="0.3" strokeWidth="1" />
  <text x="275" y="65" fontSize="18" fontWeight="700" fill="white">$4,250</text>
  <text x="275" y="83" fontSize="11" fill="white" opacity="0.7">Quote Ready</text>

  {/* Floating card 2 — bottom left: Job status */}
  <rect x="25" y="175" width="110" height="52" rx="10" fill="var(--white-1)" stroke="var(--brand-200)" strokeOpacity="0.3" strokeWidth="1" />
  <text x="35" y="196" fontSize="12" fill="white" opacity="0.7">⚡ Job #47</text>
  <text x="35" y="214" fontSize="11" fontWeight="600" fill="white">In Progress</text>

  {/* Floating card 3 — bottom right: Margin */}
  <rect x="265" y="200" width="110" height="52" rx="10" fill="var(--white-1)" stroke="var(--brand-200)" strokeOpacity="0.3" strokeWidth="1" />
  <text x="275" y="221" fontSize="18" fontWeight="700" fill="var(--brand-200)">↑ 34%</text>
  <text x="275" y="239" fontSize="11" fill="white" opacity="0.7">Margin</text>
</svg>
```

**Keep the outer container div exactly as-is** (the `flex-1 max-w-lg w-full hidden lg:flex items-center justify-center` div and the inner `w-full aspect-[4/3] rounded-2xl` div both stay unchanged). Only replace the content inside the inner div.

---

### MKT-B3-02 — JSON-LD Contact Email

**File**: `frontend/apps/marketing/src/app/page.tsx`
**Find**: `email: "support@pilotfortrades.com"` inside the `jsonLd` const
**Replace**: `email: "info@pilotfortrades.com"`

---

### MKT-B3-03 — Remove Testimonials Disclaimer

**File**: `frontend/apps/marketing/src/app/page.tsx`
**Find**: The `<p>` element after the testimonials grid that contains `"* Placeholder testimonials — real quotes from beta users coming soon."`
**Action**: Delete the entire `<p>` element. The testimonial cards themselves are untouched.

---

### MKT-B3-04 — Footer HotRMC Attribution

**File**: `frontend/apps/marketing/src/components/Footer.tsx`
**Find**: `© 2026 Pilot for Trades. All rights reserved.`
**Replace**: `© 2026 Pilot for Trades. A product of Example Holdings, LLC. All rights reserved.`

---

### MKT-B3-05 — Remove Footer Dead Link

**File**: `frontend/apps/marketing/src/components/Footer.tsx`
**Find**: `{ label: "System Status", href: "#" }` in the `footerColumns` array
**Action**: Remove this object from the array entirely. Do not add a replacement link.

---

### MKT-B3-06 — Contact Page Email Update

**File**: `frontend/apps/marketing/src/app/contact/page.tsx`

Two changes:
1. Find `href="mailto:support@pilotfortrades.com"` → `href="mailto:info@pilotfortrades.com"`
2. Find `>support@pilotfortrades.com<` display text → `>info@pilotfortrades.com<`
3. Update metadata `description` to replace `support@pilotfortrades.com` → `info@pilotfortrades.com`

---

### MKT-B3-07 — ContactForm Error Fallback

**File**: `frontend/apps/marketing/src/components/forms/ContactForm.tsx`
**Find**: `"Unable to connect. Please try again or email support@pilotfortrades.com directly."`
**Replace**: `"Unable to connect. Please try again or email info@pilotfortrades.com directly."`

---

### MKT-B3-08 — Terms Effective Date

**File**: `frontend/apps/marketing/src/app/legal/terms/page.tsx`
**Search** the entire file for `[Pending` and `insert before publishing`.
**Replace** all occurrences with `January 1, 2026`.

---

### MKT-B3-09 — Privacy Policy Legal Entity + Contact + Mobile Clause

**File**: `frontend/apps/marketing/src/app/legal/privacy/page.tsx`

Read the full file, then make these changes:

1. **Introductory company clause**: Find the first place the company is named as the data controller or policy owner. Update to use DBA form: `"Example Holdings, LLC, doing business as Pilot for Trades"` — or if inline with surrounding prose: `"Pilot for Trades (operated by Example Holdings, LLC)"`.

2. **Contact email in legal context**: Find any `support@pilotfortrades.com` or `info@pilotfortrades.com` reference in a privacy/data-rights context (e.g., "contact us to exercise your data rights", "privacy inquiries"). Update to `legal@pilotfortrades.com`.

3. **Effective Date placeholder**: If `[Pending` exists → `January 1, 2026`.

4. **Mobile data sharing clause** (REQUIRED for 10DLC): Search for a section covering SMS, phone numbers, or mobile data. Add or confirm this exact sentence exists in that section:
   > `"We do not share mobile phone numbers or SMS messaging opt-in data with third parties or affiliates for marketing or promotional purposes."`
   If no SMS/mobile section exists, add this sentence to the section describing how we use contact information collected via the platform.

---

### MKT-B3-10 — Terms of Service Legal Entity + Contact

**File**: `frontend/apps/marketing/src/app/legal/terms/page.tsx`

Read the full file, then make these changes:

1. **Introductory binding clause**: Find the opening "agreement between you and..." clause. Update to:
   > `"...a legally binding agreement between you and Example Holdings, LLC, doing business as Pilot for Trades ('Company', 'we', 'us', or 'our')..."`

2. **Contact email in legal context**: Find any `support@` reference in a legal context (dispute resolution, notices, governing law, contact for legal questions) → update to `legal@pilotfortrades.com`.

3. **Effective Date**: Confirm it reads `January 1, 2026` (should already be done in MKT-B3-08, but verify here too).

---

### MKT-B3-11 — Pricing Page: $149 → $49

**File**: `frontend/apps/marketing/src/app/pricing/page.tsx`

Read the full file. Find **every occurrence** of:
- `$149`, `149/mo`, `149/month`, `149.00`, `"149"` (in JSON-LD)

Replace each with the appropriate form:
- Display `$149/mo` → `$49/month`
- Display `$149` → `$49`
- JSON-LD `"149"` → `"49"`
- Metadata title `Plans Starting at $149/mo` → `Plans Starting at $49/month`
- Metadata description → update any pricing mention to `$49/month`

**Value framing update**: If the pricing page has language about "per user" or "per seat", update to emphasize flat unlimited-user pricing: `"$49/month — unlimited users, no per-seat fees"` or similar. Preserve the overall structure and layout; update only pricing amounts and related value copy.

---

### MKT-B3-12 — Homepage JSON-LD Price

**File**: `frontend/apps/marketing/src/app/page.tsx`

In the `jsonLd` const, find the `SoftwareApplication` `offers` object:
```ts
offers: {
  price: "149",
  ...
  priceSpecification: {
    price: "149",
    ...
  }
}
```

Update both `"149"` values → `"49"`.

---

## Two-Phase Final Verification

### Phase 1 — Targeted Tests

```bash
cd <repo>/frontend

# Run marketing app tests only
pnpm --filter marketing test 2>&1 | tail -8
```

**Pass criteria**: Same count as regression baseline. Zero new failures.

### Phase 2 — Full Verification (run once at the very end)

```bash
cd <repo>/frontend && pnpm --filter marketing exec tsc --noEmit 2>&1 | tail -5 && pnpm --filter marketing build 2>&1 | tail -10 && pnpm --filter marketing lint 2>&1 | tail -5 && echo "=== MKT-B3 FINAL VERIFICATION COMPLETE ==="
```

**Pass criteria**: Command exits with `=== MKT-B3 FINAL VERIFICATION COMPLETE ===`. Zero TypeScript errors. Build succeeds. Zero lint errors.

> **Note**: The standard Phase 2 command targets `apps/web`, `apps/mobile`, and `packages/ui`. This batch is marketing-app-only — running the standard command against unrelated packages would introduce false failures. The command above is scoped to `frontend/apps/marketing/` only.

---

## Definition of Done

- [ ] Phase 1: Marketing tests pass (same count as baseline)
- [ ] **Phase 2 FULL verification passes** (`=== MKT-B3 FINAL VERIFICATION COMPLETE ===`):
  ```bash
  cd <repo>/frontend && pnpm --filter marketing exec tsc --noEmit 2>&1 | tail -5 && pnpm --filter marketing build 2>&1 | tail -10 && pnpm --filter marketing lint 2>&1 | tail -5 && echo "=== MKT-B3 FINAL VERIFICATION COMPLETE ==="
  ```
- [ ] MKT-B3-01: Hero illustration SVG renders (no "coming soon" placeholder visible)
- [ ] MKT-B3-02: JSON-LD contact email is `info@`
- [ ] MKT-B3-03: Testimonials disclaimer text removed
- [ ] MKT-B3-04: Footer reads "A product of Example Holdings, LLC."
- [ ] MKT-B3-05: "System Status" link removed from footer Resources column
- [ ] MKT-B3-06: Contact page shows `info@pilotfortrades.com`
- [ ] MKT-B3-07: ContactForm error fallback references `info@`
- [ ] MKT-B3-08: Terms effective date is January 1, 2026
- [ ] MKT-B3-09: Privacy Policy has DBA wording + `legal@` + mobile data sharing clause
- [ ] MKT-B3-10: Terms of Service has DBA intro clause + `legal@`
- [ ] MKT-B3-11: All `$149` → `$49` on pricing page (metadata, JSON-LD, display)
- [ ] MKT-B3-12: Homepage JSON-LD `offers.price` is `"49"`
- [ ] No files outside `frontend/apps/marketing/` were modified

---

## Completion Summary

When all work is complete and both verification phases pass, write a completion summary in this exact format:

```
## MKT-B3 Completion Summary

**Date**: [date]
**Phase 1 (tests)**: [X tests, Y pass, Z fail] — baseline was [baseline count]
**Phase 2 (build)**: [Pass / Fail] — TypeScript errors: [N]

**Tasks completed**:
- MKT-B3-01: Hero SVG ✅
- MKT-B3-02: JSON-LD email ✅
- MKT-B3-03: Testimonials disclaimer ✅
- MKT-B3-04: Footer HotRMC attribution ✅
- MKT-B3-05: Footer dead link ✅
- MKT-B3-06: Contact page email ✅
- MKT-B3-07: ContactForm error fallback ✅
- MKT-B3-08: Terms effective date ✅
- MKT-B3-09: Privacy Policy legal entity + mobile clause ✅
- MKT-B3-10: Terms of Service legal entity ✅
- MKT-B3-11: Pricing $149 → $49 ✅
- MKT-B3-12: Homepage JSON-LD price ✅

**Notes**: [Any deviations from spec, edge cases found, or items for Tom review]
```
