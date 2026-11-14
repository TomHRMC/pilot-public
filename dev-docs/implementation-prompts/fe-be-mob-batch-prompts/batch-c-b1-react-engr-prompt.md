# Implementation Prompt: C-B1 (Part B) — Charter Rename Inventory (Frontend)

**Mode**: Pilot React Engineer
**Batch**: C-B1 (Part B — runs after Part A Python Engineer closes)
**Source plan**: `pilot-launch-plan.md` §2.0 row 14f + §2.1a Order C-1
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-c-b1-design.md`
**Estimated session**: 3–4 hours
**Platform**: Web — Marketing site (`apps/marketing`) + Web app (`apps/web`)
**Backend companion**: C-B1 (Part A — Python Engineer) **MUST be complete before you start**

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-react-engineer/react-engineer-rules.md`** — in full
- **`dev-docs/architecture-design/batch-designs/batch-c-b1-design.md`** — every section (A–I)
- **`dev-docs/marketing-analysis/pilot-gtm-strategy-v3.md`** — §6 (Charter Program), §9.2 (Site Changes Required), §9.3 (Charter Pitch copy)

Critical rules for this batch:

- **Rule 1.2**: Do NOT invent URL patterns or parameter names. The tier name is now `charter` (not `founders`) — Part A already changed the backend data.
- **Rule 7**: Check `packages/ui/src/index.ts` before creating any new component — this batch renames existing components, it does not create new ones.
- **Rule 8**: No new npm dependencies — this is a pure rename batch.
- **Rule 10**: If ANY test fails during your work — even one that appears to be pre-existing — **you must fix it before declaring the batch done**.
- **Rule 11 (React Compiler)**: Do NOT hand-write `useMemo`/`useCallback`/`React.memo` — the compiler handles it.
- **Rule 15 (WCAG 2.2 AA)**: The `/charter` page must satisfy target size, focus management, and non-color-only requirements.

**This is a pure rename batch.** No new hooks, no new endpoints, no new API calls. The backend already returns `tier_name: "charter"` (Part A changed the DB data). Your job is to rename all frontend identifiers, update copy, and rebuild the `/early-access` page as `/charter`.

---

## Design Decisions (Do Not Re-Litigate)

From Design Doc §G — these decisions are final:

| Decision | Outcome | Rationale |
|---|---|---|
| `/early-access` route | **308 permanent redirect** to `/charter` | Preserves inbound links per GTM §9.2 |
| `product_plan.code` | `charter_plan` (not reusing `starter_plan`) | Charter is a distinct plan for reporting/price-lock |
| Site mode type | `"charter" \| "general"` (was `"founders" \| "general"`) | Matches the new tier name |
| CTA text | "Be one of the first twelve" (was "Be One of the First" / "Get Early Access") | Per GTM §9.2 |
| About page / Careers page | **DO NOT RENAME** — "founder" refers to Tom | Per spec §2.3 |

These were resolved in the design doc. Do NOT change them without asking Tom.

---

## Pre-Work: Establish Regression Baseline

Before touching any file:

```bash
cd <repo>/frontend

# Marketing site tests:
pnpm --filter marketing test 2>&1 | tail -5

# Web app tests:
pnpm --filter web test 2>&1 | tail -5
```

Record the exact counts. These must still pass at the end of the batch.

> **If any tests are already failing before you start**: Do NOT treat them as "pre-existing" and proceed. Either confirm with Tom, or fix the failure before touching any batch files.

---

## Pre-Work: Sync API Types

```bash
cd <repo>/frontend
pnpm sync-api-types
```

This regenerates `packages/shared-types/src/api-schema.d.ts` from the live backend. Part A changed the `tier_name` data value from `"founders"` to `"charter"` — the generated types should still compile cleanly (the schema is unchanged, only the data value changed).

> **Note**: `pnpm sync-api-types` is technically not required for this batch (no API shape change), but running it confirms Part A landed correctly and the backend is returning `charter` instead of `founders`.

---

## Pre-Work: Read These Source Files

Read each of these with `read_file` before writing any code:

### Marketing site files:
```
frontend/apps/marketing/src/lib/useSiteMode.ts              ← why: SiteMode type, FOUNDERS_MODE, isFoundersMode — the core mode logic
frontend/apps/marketing/src/app/early-access/page.tsx       ← why: the page to rebuild as /charter
frontend/apps/marketing/src/app/pricing/page.tsx            ← why: foundersFeatures, foundersIncludedItems, foundersFaqs, PricingPageFounders
frontend/apps/marketing/src/components/forms/WaitlistForm.tsx ← why: rename to CharterApplicationForm, source="early_access_page"
frontend/apps/marketing/src/components/HeroWaitlistForm.tsx ← why: rename to HeroCharterForm
frontend/apps/marketing/src/components/Header.tsx           ← why: CTA text + /early-access href
frontend/apps/marketing/src/components/Footer.tsx           ← why: /early-access nav link
frontend/apps/marketing/src/components/ComingSoonPage.tsx   ← why: "Get Early Access" CTA
frontend/apps/marketing/src/components/blog/BlogCta.tsx     ← why: /early-access href
frontend/apps/marketing/src/components/blog/BlogPostLayout.tsx ← why: /early-access href
frontend/apps/marketing/src/components/trades/TradePageTemplate.tsx ← why: siteMode="founders" default, /early-access href
frontend/apps/marketing/src/app/page.tsx                    ← why: CTA text + /early-access href
frontend/apps/marketing/src/app/about/page.tsx              ← why: DO NOT RENAME (founder = Tom)
frontend/apps/marketing/src/app/careers/page.tsx            ← why: DO NOT RENAME (founder = Tom)
frontend/apps/marketing/src/app/sitemap.ts                  ← why: /early-access URL
frontend/apps/marketing/src/app/not-found.tsx               ← why: "Early Access" nav label
```

### Web app files:
```
frontend/apps/web/src/app/signup/plan/page.tsx              ← why: "Join the Founders program" text
frontend/apps/web/src/app/signup/account/page.tsx           ← why: "Join the Founders program" text
frontend/apps/web/src/mocks/handlers/dispatchBoardHandlers.ts ← why: MOCK_FOUNDERS_TIER, tier_name: "founders"
```

### Test/mock files:
```
frontend/apps/web/src/__tests__/batch_signup_ui_fix_1/plan_page_subtitle.integration.test.tsx ← why: FOUNDERS_ONLY_TIERS, "Founders" assertions
frontend/apps/web/src/features/signup/components/__tests__/SignupAccountPage.test.tsx ← why: "Founders" assertions
frontend/apps/web/src/__tests__/batch_dispatch_b1/dispatch_b1.integration.test.tsx ← why: tier_name: "founders" fixtures
frontend/apps/web/src/__tests__/batch_dispatch_b1_25/dispatch_b1_25.integration.test.tsx ← why: tier_name: "founders" fixtures
frontend/apps/web/src/__tests__/batch_dispatch_b2/dispatch_b2.integration.test.tsx ← why: tier_name: "founders" fixtures
frontend/apps/web/__tests__/batch_beta_b7/DispatchBoardMonth.integration.test.tsx ← why: tier_name: "founders" fixtures
frontend/apps/web/src/features/dispatch-board/components/DispatchWeekLaneView.tsx ← why: "Founders cap" comment
```

Also run this to confirm the full blast radius:
```bash
cd <repo>/frontend
grep -rn -i 'founder\|founding\|early.access' --include="*.ts" --include="*.tsx" . | grep -v node_modules | grep -v '.next'
```

---

## Context: What This Batch Does

The GTM strategy v3 retires "Founder/Founding Tester/Founding Member/Early Access" in favor of "Charter" (decision D14). Part A (Python Engineer) already renamed the DB data — `subscription_tier.tier_name` is now `charter`, `product_plan.code` is now `charter_plan`. Your job is to rename all frontend identifiers to match.

**Rename mapping** (from design doc §F.3):

| Was | Now | Files |
|---|---|---|
| `SiteMode = "founders" \| "general"` | `SiteMode = "charter" \| "general"` | `useSiteMode.ts` |
| `FOUNDERS_MODE` | `CHARTER_MODE` | `useSiteMode.ts` |
| `isFoundersMode` | `isCharterMode` | `useSiteMode.ts` |
| `hasFounders` | `hasCharter` | `useSiteMode.ts` |
| `MOCK_FOUNDERS_TIER` | `MOCK_CHARTER_TIER` | `dispatchBoardHandlers.ts` |
| `foundersFeatures` | `charterFeatures` | `pricing/page.tsx` |
| `foundersIncludedItems` | `charterIncludedItems` | `pricing/page.tsx` |
| `foundersFaqs` | `charterFaqs` | `pricing/page.tsx` |
| `PricingPageFounders` | `PricingPageCharter` | `pricing/page.tsx` |
| `WaitlistForm` | `CharterApplicationForm` | rename file + component |
| `HeroWaitlistForm` | `HeroCharterForm` | rename file + component |
| `source = "early_access_page"` | `source = "charter_page"` | form components |
| `/early-access` route | `/charter` (308 redirect from `/early-access`) | new `charter/page.tsx`, update `early-access/page.tsx` |
| "Be One of the First" | "Be one of the first twelve" | all CTA components |
| "Get Early Access" | "Be one of the first twelve" | `ComingSoonPage.tsx`, `not-found.tsx` |
| "Join the Founders program" | "Join the Charter program" | `signup/plan/page.tsx`, `signup/account/page.tsx` |
| `tier_name: "founders"` in mocks | `tier_name: "charter"` | `dispatchBoardHandlers.ts` + all test fixtures |
| `display_label: "Founders"` in mocks | `display_label: "Charter"` | `dispatchBoardHandlers.ts` + all test fixtures |

**Do NOT rename** (per design doc §C):
- `frontend/apps/marketing/src/app/about/page.tsx` — "founder story", "founder-heading", "I'm Tom Lang, the founder" refers to Tom
- `frontend/apps/marketing/src/app/careers/page.tsx` — "founder access", "solo-founder company" refers to Tom
- `frontend/apps/marketing/src/app/legal/terms/page.tsx` — "early access periods" is a generic legal term, not the program name

---

## STEP 1 — Rename Site Mode Type + Logic

File: `frontend/apps/marketing/src/lib/useSiteMode.ts`

Read the file first. Then rename:
- `export type SiteMode = "founders" | "general"` → `export type SiteMode = "charter" | "general"`
- `isFoundersMode` → `isCharterMode` (in the `SiteModeResult` interface + all return objects)
- `const FOUNDERS_MODE: SiteModeResult` → `const CHARTER_MODE: SiteModeResult`
- `const hasFounders = tiers.some(...)` → `const hasCharter = tiers.some(...)`
- `const mode: SiteMode = hasGeneral && !hasFounders ? "general" : "founders"` → `hasGeneral && !hasCharter ? "general" : "charter"`
- All comments referencing "Founders mode" → "Charter mode"
- The fail-open return: `return FOUNDERS_MODE` → `return CHARTER_MODE`

**Intermediate verification:**
```bash
cd <repo>/frontend
pnpm --filter marketing test 2>&1 | tail -6
```

---

## STEP 2 — Create `/charter` Page + Redirect `/early-access`

### 2a. Create `frontend/apps/marketing/src/app/charter/page.tsx`

This is the new Charter program page. Content comes from GTM §6 (Charter Program) and §9.3 (Charter Pitch). Read the existing `early-access/page.tsx` first — the layout structure is retained, only the copy changes.

Key content changes per GTM §6:
- Title: "Be one of the first twelve — Charter for Pilot for Trades"
- Hero: "Twelve spots. I'm filling them now." (GTM §6.8)
- Program details: 90 days free (not 6 months), $49/mo locked after, concierge onboarding, no card at signup
- The Charter Pitch copy from GTM §9.3
- `CharterApplicationForm` (renamed from `WaitlistForm`) with `source="charter_page"`
- EIN question + qualification questions per GTM §9.2 (WaitlistForm → CharterApplicationForm changes)

### 2b. Update `frontend/apps/marketing/src/app/early-access/page.tsx`

Replace the entire page content with a 308 permanent redirect to `/charter`:

```tsx
import { redirect } from "next/navigation";

export default function EarlyAccessPage() {
  redirect("/charter");
}
```

**Keep the route** — inbound links exist (GTM §9.2). The 308 preserves SEO link equity.

**Intermediate verification:**
```bash
pnpm --filter marketing test 2>&1 | tail -6
```

---

## STEP 3 — Rename Marketing CTAs + Routes

Update all files that reference `/early-access` or "Be One of the First" / "Get Early Access":

| File | Change |
|---|---|
| `Header.tsx` | `siteMode = "founders"` default → `"charter"`, CTA href `/early-access` → `/charter`, CTA text "Be One of the First" → "Be one of the first twelve" |
| `Footer.tsx` | `siteMode = "founders"` default → `"charter"`, nav label "Early Access" → "Charter", href `/early-access` → `/charter` |
| `ComingSoonPage.tsx` | "Get Early Access" → "Be one of the first twelve" |
| `page.tsx` (homepage) | CTA href `/early-access` → `/charter`, CTA text "Be One of the First" → "Be one of the first twelve" |
| `BlogCta.tsx` | `siteMode = "founders"` default → `"charter"`, CTA href `/early-access` → `/charter` |
| `BlogPostLayout.tsx` | CTA href `/early-access` → `/charter` |
| `TradePageTemplate.tsx` | `siteMode = "founders"` default → `"charter"`, CTA href `/early-access` → `/charter` |
| `contact/page.tsx` | href `/early-access` → `/charter` |
| `features/page.tsx` | CTA href `/early-access` → `/charter` |
| `blog/page.tsx` | CTA href `/early-access` → `/charter` |
| `about/page.tsx` | CTA href `/early-access` → `/charter` (but DO NOT rename "founder" copy — that's Tom) |
| `sign-up/page.tsx` | Comment referencing `/early-access` pattern → `/charter` |
| `pricing-preview/page.tsx` | All `/early-access` hrefs → `/charter` |
| `sitemap.ts` | `/early-access` URL → `/charter` |
| `not-found.tsx` | "Early Access" label → "Charter", href `/early-access` → `/charter` |

**Also update trade landing pages** that reference "Beta Founder pricing":
- `trades/plumbing/page.tsx` — "Beta Founder pricing" → "Charter pricing"
- `trades/hvac/page.tsx` — "Beta Founder pricing" → "Charter pricing"
- `trades/electrical/page.tsx` — "Beta Founder pricing" → "Charter pricing"

---

## STEP 4 — Rename Pricing Page Components

File: `frontend/apps/marketing/src/app/pricing/page.tsx`

Rename:
- `foundersFeatures` → `charterFeatures`
- `foundersIncludedItems` → `charterIncludedItems`
- `foundersFaqs` → `charterFaqs`
- `PricingPageFounders()` → `PricingPageCharter()`
- All references to these identifiers throughout the file
- Comments referencing "Founders Mode" → "Charter mode"

---

## STEP 5 — Rename Forms

### 5a. Rename `WaitlistForm.tsx` → `CharterApplicationForm.tsx`

- Rename the file: `frontend/apps/marketing/src/components/forms/WaitlistForm.tsx` → `CharterApplicationForm.tsx`
- Rename the component: `WaitlistForm` → `CharterApplicationForm`
- Update `source = "early_access_page"` → `source = "charter_page"`
- Update copy: "We'll email you when early access opens" → "We'll email you when Charter opens"
- Update the default export and all internal references

### 5b. Rename `HeroWaitlistForm.tsx` → `HeroCharterForm.tsx`

- Rename the file: `frontend/apps/marketing/src/components/HeroWaitlistForm.tsx` → `HeroCharterForm.tsx`
- Rename the component: `HeroWaitlistForm` → `HeroCharterForm`
- Update `aria-label="Early access signup"` → `aria-label="Charter signup"`
- Update copy: "We'll email you when early access opens" → "We'll email you when Charter opens"

### 5c. Update all imports

Search for all files that import `WaitlistForm` or `HeroWaitlistForm` and update the import paths + component names:
```bash
grep -rn "WaitlistForm\|HeroWaitlistForm" frontend/apps/marketing/src/ --include="*.tsx" --include="*.ts"
```

---

## STEP 6 — Rename Web App Signup Text

Files: `frontend/apps/web/src/app/signup/plan/page.tsx` and `signup/account/page.tsx`

Update:
- "Join the Founders program — free during development, no credit card required." → "Join the Charter program — 90 days free, no credit card required."
- Comments: "Founders mode" → "Charter mode"
- The mode-derivation logic: `hasFounders` check (if any) → `hasCharter` — but note: the web app's `useSubscriptionTiers` hook returns tier data from the API, and the API now returns `tier_name: "charter"`. The mode-derivation logic checks for the absence of a trial tier, not for the tier name "founders" — so the logic itself may not need changing, only the comments and display text.

---

## STEP 7 — Rename Web App Mock Data + Tests

### 7a. Update `dispatchBoardHandlers.ts`

File: `frontend/apps/web/src/mocks/handlers/dispatchBoardHandlers.ts`

Rename:
- `MOCK_FOUNDERS_TIER` → `MOCK_CHARTER_TIER`
- `tier_name: "founders"` → `tier_name: "charter"`
- `display_label: "Founders"` → `display_label: "Charter"`
- `tier_id: "tier-founders-001"` → `tier_id: "tier-charter-001"` (for consistency)
- Comments referencing "founders tier" → "charter tier"

### 7b. Update all test fixtures

In all 6 test files, rename:
- `tier_name: "founders"` → `tier_name: "charter"`
- `display_label: "Founders"` → `display_label: "Charter"`
- `tier_id: "tier-founders-001"` → `tier_id: "tier-charter-001"`
- `FOUNDERS_ONLY_TIERS` → `CHARTER_ONLY_TIERS` (in `plan_page_subtitle.integration.test.tsx`)
- "Founders" assertion text → "Charter" (in `SignupAccountPage.test.tsx`)
- "Join the Founders program" → "Join the Charter program" (in assertion text)
- "Founders cap" comment → "Charter cap" (in `DispatchWeekLaneView.tsx`)

**Test files:**
1. `frontend/apps/web/src/__tests__/batch_signup_ui_fix_1/plan_page_subtitle.integration.test.tsx`
2. `frontend/apps/web/src/features/signup/components/__tests__/SignupAccountPage.test.tsx`
3. `frontend/apps/web/src/__tests__/batch_dispatch_b1/dispatch_b1.integration.test.tsx`
4. `frontend/apps/web/src/__tests__/batch_dispatch_b1_25/dispatch_b1_25.integration.test.tsx`
5. `frontend/apps/web/src/__tests__/batch_dispatch_b2/dispatch_b2.integration.test.tsx`
6. `frontend/apps/web/__tests__/batch_beta_b7/DispatchBoardMonth.integration.test.tsx`
7. `frontend/apps/web/src/features/dispatch-board/components/DispatchWeekLaneView.tsx` (comment only)

**Intermediate verification after each file:**
```bash
pnpm --filter web test 2>&1 | tail -6
```

---

## Final Verification

> ❌ **BANNED COMMAND**: `npx vitest run` — **NEVER use this**. Use `pnpm --filter web test` or `pnpm --filter marketing test` only.

### Phase 1 — Targeted tests (run after each task group during development)

```bash
cd <repo>/frontend

pnpm --filter marketing test 2>&1 | tail -6
pnpm --filter web test 2>&1 | tail -6
```

Fix any failure before moving to the next task.

### Phase 2 — Full verification (run once at the very end, before DoD sign-off)

```bash
cd <repo>/frontend && echo "=== UI - Type Check ===" && pnpm --filter @pilot/ui check-types && echo "=== Web - Type Check ===" && pnpm --filter web check-types && echo "=== Mobile - Type Check ===" && pnpm --filter mobile build && echo "=== UI - Lint ===" && pnpm --filter @pilot/ui lint && echo "=== Web - Lint ===" && pnpm --filter web lint && echo "=== Mobile - Lint ===" && pnpm --filter mobile lint && echo "=== TYPE+LINT PASS ===" && echo "=== UI - Tests ===" && pnpm --filter @pilot/ui test 2>&1 | tail -6 && echo "=== Web - Tests ===" && pnpm --filter web test 2>&1 | tail -6 && echo "=== Mobile - Tests ===" && pnpm --filter mobile test 2>&1 | tail -8 && echo "=== MVP FINAL VERIFICATION COMPLETE ==="
```

After the verification passes, confirm no `founders`/`founding`/`early-access` references remain (excluding do-not-rename files):

```bash
cd <repo>/frontend
grep -rn -i 'founder\|founding\|early.access' --include="*.ts" --include="*.tsx" . | grep -v node_modules | grep -v '.next' | grep -v 'about/page' | grep -v 'careers/page' | grep -v 'legal/terms'
```

This should return **zero results** (all references renamed, except about/careers/legal which refer to Tom or are generic legal terms).

---

## Definition of Done — C-B1 (Part B)

Update `pilot-launch-plan.md` §2.0 row 14f status when complete:

- [ ] Pre-modification regression baseline captured (marketing + web test counts)
- [ ] `pnpm sync-api-types` run — confirms Part A landed (backend returns `charter`)
- [ ] Design doc fully read before writing any code
- [ ] All mandatory source files read before modifying
- [ ] **STEP 1**: `useSiteMode.ts` — `SiteMode` type, `CHARTER_MODE`, `isCharterMode`, `hasCharter` renamed
- [ ] **STEP 2**: `/charter` page created with GTM §6 content; `/early-access` → 308 redirect
- [ ] **STEP 3**: All marketing CTAs + routes updated (`/early-access` → `/charter`, "Be one of the first twelve")
- [ ] **STEP 4**: Pricing page components renamed (`charterFeatures`, `PricingPageCharter`, etc.)
- [ ] **STEP 5**: `WaitlistForm` → `CharterApplicationForm`, `HeroWaitlistForm` → `HeroCharterForm` (files + components + imports)
- [ ] **STEP 6**: Web app signup text updated ("Join the Charter program")
- [ ] **STEP 7**: Mock data + 6 test files updated (`tier_name: "charter"`, `MOCK_CHARTER_TIER`, etc.)
- [ ] No hand-written `useMemo`/`useCallback`/`React.memo` for render-perf (React Compiler, rules §32)
- [ ] `/early-access` returns 308 redirect to `/charter`
- [ ] `/charter` page renders with GTM §6 copy
- [ ] Pricing page shows "Charter" (not "Founders")
- [ ] Signup pages show "Charter" text (not "Founders")
- [ ] `grep` confirms zero `founders`/`founding`/`early-access` references remain (excluding about/careers/legal)
- [ ] **Phase 2 FULL verification command passes** (`=== MVP FINAL VERIFICATION COMPLETE ===`):

  ```bash
  cd <repo>/frontend && echo "=== UI - Type Check ===" && pnpm --filter @pilot/ui check-types && echo "=== Web - Type Check ===" && pnpm --filter web check-types && echo "=== Mobile - Type Check ===" && pnpm --filter mobile build && echo "=== UI - Lint ===" && pnpm --filter @pilot/ui lint && echo "=== Web - Lint ===" && pnpm --filter web lint && echo "=== Mobile - Lint ===" && pnpm --filter mobile lint && echo "=== TYPE+LINT PASS ===" && echo "=== UI - Tests ===" && pnpm --filter @pilot/ui test 2>&1 | tail -6 && echo "=== Web - Tests ===" && pnpm --filter web test 2>&1 | tail -6 && echo "=== Mobile - Tests ===" && pnpm --filter mobile test 2>&1 | tail -8 && echo "=== MVP FINAL VERIFICATION COMPLETE ==="
  ```

- [ ] Final test count (before → after) documented
- [ ] Completion Summary added to launch plan

---

## Completion Summary

After all Definition of Done items are complete:

1. Add a **Completion Summary** subsection to `pilot-launch-plan.md` Appendix B using the format below.
2. Update `pilot-launch-plan.md` §2.0 row 14f status to `✅ COMPLETE`.

```markdown
### C-B1 (Part B — React Engineer) — Charter Rename Inventory: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot React Engineer
**Baseline**: X passed (marketing) | Y passed (web)
**Final**: X passed (marketing) | Y passed (web) (0 new tests — rename only)

#### What Was Accomplished

- Site mode type renamed: `"founders" | "general"` → `"charter" | "general"`
- `/charter` page created with GTM §6 content; `/early-access` → 308 redirect
- All marketing CTAs updated: "Be one of the first twelve", `/charter` routes
- Pricing page components renamed (charterFeatures, PricingPageCharter, etc.)
- Forms renamed: WaitlistForm → CharterApplicationForm, HeroWaitlistForm → HeroCharterForm
- Web app signup text: "Join the Founders program" → "Join the Charter program"
- Mock data + 6 test files: tier_name "founders" → "charter", MOCK_CHARTER_TIER

#### Files Changed / Created

| File | Action |
|---|---|
| `frontend/apps/marketing/src/lib/useSiteMode.ts` | Updated — type + mode logic renamed |
| `frontend/apps/marketing/src/app/charter/page.tsx` | Created — Charter program page |
| `frontend/apps/marketing/src/app/early-access/page.tsx` | Updated — 308 redirect to /charter |
| `frontend/apps/marketing/src/app/pricing/page.tsx` | Updated — component renames |
| `frontend/apps/marketing/src/components/forms/CharterApplicationForm.tsx` | Renamed from WaitlistForm.tsx |
| `frontend/apps/marketing/src/components/HeroCharterForm.tsx` | Renamed from HeroWaitlistForm.tsx |
| ~12 marketing CTA/route files | Updated — /charter routes + CTA text |
| `frontend/apps/web/src/app/signup/plan/page.tsx` | Updated — Charter text |
| `frontend/apps/web/src/app/signup/account/page.tsx` | Updated — Charter text |
| `frontend/apps/web/src/mocks/handlers/dispatchBoardHandlers.ts` | Updated — MOCK_CHARTER_TIER |
| 6 test files | Updated — tier_name "charter" fixtures + assertions |
```
