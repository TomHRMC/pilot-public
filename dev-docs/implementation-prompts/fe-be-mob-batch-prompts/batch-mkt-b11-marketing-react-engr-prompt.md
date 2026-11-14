# Implementation Prompt: MKT-B11-C2 — Marketing Site Mode Switch (Founders → General Release)

**Mode**: Pilot React Engineer  
**Batch**: MKT-B11-C2  
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §MKT-B11  
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-mkt-b11-ui-design-spec.md` — the approved UI Designer output
**Estimated session**: 4–6 hours  
**Platform**: Marketing app only (`frontend/apps/marketing/`)  
**Backend companion**: MKT-B11-BE — **must be complete first**. Run `pnpm sync-api-types` after backend closes before starting this batch.

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-react-engineer/react-engineer-rules.md`** — in full
- **The approved UI Designer deliverable** — every artboard in the Figma/design file. Do NOT implement anything not designed. If a state is missing from the design → STOP and ask Tom.
- **`dev-docs/marketing-analysis/gtm-feature-tier-matrix-v1.md` §19** — pricing page feature groups for both Starter and Teams cards

**Critical rules for this batch:**

- **Rule 1.1**: The `useSiteMode()` hook must read **only** from `GET /api/v1/subscription-tiers?active_only=true`. Never hardcode the mode or read from `.env` — the mode must be a live DB flag.
- **Rule 1.2**: Both modes (Founders + General Release) must be **fully built and tested**. The Founders mode is live today. The General Release mode is dormant but must be production-ready. Tom flips a DB flag — no code deploy required.
- **Rule 2**: The marketing app uses Next.js static generation with `cache: 'no-store'` for dynamic content. The mode fetch must use `cache: 'no-store'` so the page re-renders with the live DB value on each request — not a stale cached value from build time.
- **Rule 3**: Do NOT use `apiClient` from `@pilot/shared-api` in the marketing app — that package is for the web app. The marketing app fetches via `fetch()` directly against the backend URL (check existing marketing fetch patterns before writing).
- **Rule 4**: All new styles must use CSS variables from `globals.css` — zero hardcoded hex values. Run `grep -n "hardcoded" result` if you see lint warnings.
- **Rule 8**: Check `frontend/apps/marketing/src/components/` for existing components before creating new ones. The `WaitlistForm` is already built — reuse it for the `/sign-up` page.
- **Rule 10**: If ANY test fails during your work — fix it before declaring the batch done. No exceptions.

---

## Pre-Work: Establish Regression Baseline

Before touching any file:

```bash
cd <repo>/frontend
pnpm --filter marketing test 2>&1 | tail -5
```

Record the exact count. If no test suite exists for marketing, note that baseline is "0 tests" and proceed.

> **Note**: The marketing app is a Next.js static site. TypeScript type checking is the primary verification. Run `pnpm --filter marketing check-types` or `pnpm --filter marketing build` to catch type errors during development.

---

## Pre-Work: Verify Endpoints

The `useSiteMode()` hook calls one endpoint:

```bash
grep -A 5 "subscription-tiers" backend/openapi_schema_map.md
```

Verify `GET /api/v1/subscription-tiers` exists and returns an array with `tier_name`, `is_active`, and `schedule_lanes` fields. After MKT-B11-BE runs, `founders` tier should be the only row with `is_active=true`.

| Hook | Endpoint | Expected Response |
|---|---|---|
| `useSiteMode` | `GET /api/v1/subscription-tiers?active_only=true` | Array of active subscription tiers; `founders` only during Founders cohort |

---

## Pre-Work: Read These Source Files

Read each of these with `read_file` before writing any code:

```
frontend/apps/marketing/src/app/page.tsx                        ← homepage structure
frontend/apps/marketing/src/app/pricing/page.tsx               ← current pricing page
frontend/apps/marketing/src/app/early-access/page.tsx          ← founding member page
frontend/apps/marketing/src/components/Header.tsx              ← nav CTA button
frontend/apps/marketing/src/components/Footer.tsx              ← footer nav
frontend/apps/marketing/src/components/trades/TradePageTemplate.tsx  ← shared trade page component
frontend/apps/marketing/src/components/blog/BlogCta.tsx        ← blog sidebar CTA
frontend/apps/marketing/src/components/blog/BlogPostLayout.tsx ← blog post footer CTA
frontend/apps/marketing/src/components/forms/WaitlistForm.tsx  ← form to reuse for /sign-up
frontend/apps/marketing/src/lib/site-config.ts                 ← existing SiteConfig fetch pattern
```

Also check how the marketing app currently fetches data from the backend:
```bash
grep -rn "fetch(" frontend/apps/marketing/src --include="*.tsx" --include="*.ts" | grep -v "node_modules" | head -10
```

---

## Background / Context

The marketing site needs to support two operating modes controlled by a DB flag (`product_plan.is_active` for `founders_plan`). Tom flips the flag via a direct DB update — zero code deploy needed.

**Mode resolution logic**:
- Fetch `GET /api/v1/subscription-tiers?active_only=true`
- If result includes a tier with `tier_name === 'founders'` → **Founders Mode**
- If result includes tiers with `tier_name === 'starter'` or `'teams'` → **General Release Mode**

The `useSiteMode()` hook encapsulates this logic and is consumed by every component that needs to switch.

**New page**: `/sign-up` — the General Release CTA destination. Same `WaitlistForm` component, updated copy. Replaces `/early-access` as the "get started" CTA destination in General Release mode. The `/early-access` page itself stays unchanged (Founders Mode).

---

## Task 1 — Create `useSiteMode()` Hook

**File to create**: `frontend/apps/marketing/src/lib/useSiteMode.ts`

This hook is the single source of truth for the current site mode. It fetches once (cached for the request) and returns the mode.

```typescript
// Adjust this implementation to match the marketing app's actual fetch patterns
// Read frontend/apps/marketing/src/lib/site-config.ts first to understand the pattern

export type SiteMode = 'founders' | 'general';

export interface SiteModeResult {
  mode: SiteMode;
  isFoundersMode: boolean;
  isGeneralRelease: boolean;
}

// Server-side fetch (for server components and generateMetadata)
export async function getSiteMode(): Promise<SiteModeResult> {
  // Fetch from the backend subscription-tiers endpoint
  // Use cache: 'no-store' — mode must reflect live DB, not cached build
  const backendUrl = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';
  try {
    const res = await fetch(
      `${backendUrl}/api/v1/subscription-tiers/test?active_only=true`,
      { cache: 'no-store' }
    );
    if (!res.ok) throw new Error('Failed to fetch tiers');
    const tiers: Array<{ tier_name: string; is_active: boolean }> = await res.json();
    const hasFounders = tiers.some(t => t.tier_name === 'founders');
    const hasGeneral = tiers.some(t => t.tier_name === 'starter' || t.tier_name === 'teams');
    const mode: SiteMode = hasGeneral ? 'general' : 'founders';
    return { mode, isFoundersMode: mode === 'founders', isGeneralRelease: mode === 'general' };
  } catch {
    // Fail open to Founders mode — safer than showing the wrong page during an outage
    return { mode: 'founders', isFoundersMode: true, isGeneralRelease: false };
  }
}
```

> **Note**: Verify whether the marketing app uses the authenticated `/api/v1/subscription-tiers` or the test endpoint `/api/v1/subscription-tiers/test`. The marketing site has no user auth, so it should use the test endpoint or an unauthenticated equivalent. Confirm with `grep -rn "subscription-tiers" backend/openapi_schema_map.md` and pick the correct path.

**Intermediate type check:**
```bash
cd frontend && pnpm --filter marketing build 2>&1 | tail -10
```

---

## Task 2 — Create the `/sign-up` Page (General Release CTA destination)

**File to create**: `frontend/apps/marketing/src/app/sign-up/page.tsx`

This is the General Release equivalent of `/early-access`. Use the approved UI Designer design for content. The form component (`WaitlistForm`) is reused with `source="sign_up"`.

Per the designer's spec:
- **H1**: "Start Your Free Trial"
- **Subheading**: "14 days free. No credit card required. Cancel anytime."
- **3-card "What's included" block**: (see designer's spec for exact icons/text)
- **Form**: Same `WaitlistForm` component, `source="sign_up"`, button text: "Start Free Trial"
- **Microcopy below button**: "After 14 days, continue at $49/month (Starter) or $149/month (Teams). Cancel anytime before trial ends."

> **Note**: The existing `WaitlistForm` component submits to `POST /api/v1/marketing/waitlist`. Verify whether the form accepts a `source` prop to distinguish sign-up vs. early-access submissions. Read `WaitlistForm.tsx` before implementing.

**Also create metadata**:
```typescript
export const metadata: Metadata = {
  title: "Start Your Free Trial — Pilot for Trades",
  description: "14-day free trial. No credit card required. Start using Voice AI quoting, dispatch, and QuickBooks sync for your electrical contracting business today.",
  openGraph: {
    title: "Start Your Free Trial | Pilot for Trades",
    description: "14 days free. No credit card. Cancel anytime.",
    url: "https://pilotfortrades.com/sign-up",
  },
};
```

**Intermediate type check:**
```bash
cd frontend && pnpm --filter marketing build 2>&1 | tail -10
```

---

## Task 3 — Update Header CTA

**File**: `frontend/apps/marketing/src/components/Header.tsx`

The header has two CTA buttons — desktop nav (line ~148) and mobile menu (line ~287).

**Pattern**: Fetch site mode in the Header server component (or pass mode as prop from the layout). Per the design:

| Mode | Button Text | Destination |
|---|---|---|
| Founders | "Be One of the First" | `/early-access` |
| General Release | "Start Free Trial" | `/sign-up` |

Read the existing `Header.tsx` structure before modifying. If the Header is currently a server component, it can call `getSiteMode()` directly. If it's a client component, a different approach is needed — document which it is.

---

## Task 4 — Update Homepage (`/`)

**File**: `frontend/apps/marketing/src/app/page.tsx`

Two CTA locations:

**Hero CTA** (lines ~156–168): Per design spec:
- Founders Mode: unchanged ("Be One of the First" → `/early-access`)
- General Release: "Start Free Trial" → `/sign-up` + subtext below: "14-day free trial · No credit card required"

**Bottom CTA strip** (lines ~1063–1066): Per design spec:
- Founders Mode: unchanged
- General Release: Updated body copy + "Start Free Trial" → `/sign-up`

The `page.tsx` is a server component — call `getSiteMode()` at the top and pass `mode` as a prop or render conditionally inline.

---

## Task 5 — Update Pricing Page (`/pricing`)

**File**: `frontend/apps/marketing/src/app/pricing/page.tsx`

**Founders Mode** (current): Single plan card — no changes to existing content.

**General Release Mode** (new): Full 2-column Starter/Teams layout per the designer's spec and `gtm-feature-tier-matrix-v1.md §19`.

Suggested approach: create two named export components in the same file or in `pricing/` directory:
- `PricingPageFounders` — current single-plan content
- `PricingPageRegularRelease` — new 2-column Starter/Teams layout

The default `PricingPage` component calls `getSiteMode()` and renders the appropriate variant.

**General Release pricing page requirements** (from design and GTM docs):
- 2-column layout: Starter ($49/mo, 5 lanes, 90 min Voice AI, 100 SMS) and Teams ($149/mo, 20 lanes, 300 min Voice AI, 500 SMS)
- "5 simultaneous jobs" / "20 simultaneous jobs" lane count callout per card
- Schedule lane explanation callout: *"What's a schedule lane? One parallel job row on your dispatch board. Any team member. Any job. No extra charge."*
- Primary CTA per card: "Start Free Trial" → `/sign-up` with subtext
- FAQ section updated: "Is there a free trial?" → standard 14-day trial answer
- JSON-LD `offers` schema updated to include both Starter and Teams offers

---

## Task 6 — Update Early-Access Page (`/early-access`)

**No content changes** to the existing Founders mode page.

**Add redirect logic**: In General Release mode, the `/early-access` URL should redirect to `/sign-up`. This prevents SEO/bookmark breakage if someone reaches the old URL after the switch.

**File**: `frontend/apps/marketing/src/app/early-access/page.tsx`

Add at the top of the component:
```typescript
const { isGeneralRelease } = await getSiteMode();
if (isGeneralRelease) {
  redirect('/sign-up'); // from 'next/navigation'
}
```

---

## Task 7 — Update TradePageTemplate (Electrical / Plumbing / HVAC)

**File**: `frontend/apps/marketing/src/components/trades/TradePageTemplate.tsx`

Three CTA locations in the template. Per design spec:

| Mode | Button text | Destination |
|---|---|---|
| Founders | "Be One of the First" | `/early-access` |
| General Release | "Start Free Trial" | `/sign-up` |

Also update the pricing section body copy prop to accept mode-aware content, OR pass `siteMode` as a prop to `TradePageTemplate` from each trade page (`electrical/page.tsx`, `plumbing/page.tsx`, `hvac/page.tsx`).

**Pricing body copy change** for General Release:
> "Starter at $49/month · Teams at $149/month · 14-day free trial, no credit card required."

---

## Task 8 — Update Remaining Pages and Components

Update these remaining locations per the design spec. The pattern is identical: Founders → unchanged, General Release → "Start Free Trial" → `/sign-up`.

| File | Location | What changes |
|---|---|---|
| `src/app/features/page.tsx` | 2 CTA instances | Button text + href |
| `src/app/about/page.tsx` | Bottom CTA strip | Body copy + button text + href |
| `src/app/contact/page.tsx` | Sidebar CTA block | Heading + link text + href |
| `src/app/blog/page.tsx` | Bottom CTA | Button text + href |
| `src/components/blog/BlogCta.tsx` | Default props | `ctaLabel` + `ctaHref` default values |
| `src/components/blog/BlogPostLayout.tsx` | Sidebar + footer CTAs | Button text + href + subtext |
| `src/components/Footer.tsx` | "Early Access" nav link | Label + href in General Release |

**For `BlogCta.tsx`**: The component has default props. In Founders mode, defaults stay as-is. In General Release mode, defaults should switch. Since `BlogCta` is used across many blog posts, the cleanest approach is to accept `siteMode` as a prop (passed from `BlogPostLayout` which gets it from the page) rather than fetching inside each CTA.

---

## Task 9 — Replace Logo Assets

**Files to replace**:
- `frontend/apps/marketing/public/logo.svg` — new primary logo SVG from designer
- `frontend/apps/marketing/public/logo-dark.svg` — dark background variant
- `frontend/apps/marketing/public/favicon.ico` — new favicon
- `frontend/apps/marketing/public/icon-512.png` — new app icon

Also update any hardcoded `alt` text or `src` paths in:
```bash
grep -rn "logo" frontend/apps/marketing/src --include="*.tsx" | grep -v "node_modules"
```

Verify the logo renders correctly at all screen sizes (mobile nav, desktop nav, footer).

---

## Final Verification

### Phase 1 — Type check after each task group

```bash
cd <repo>/frontend
pnpm --filter marketing build 2>&1 | tail -10
```

Fix any TypeScript errors before moving to the next task.

### Phase 2 — Full verification at the end

```bash
cd <repo>/frontend
pnpm --filter marketing build 2>&1 | tail -10
pnpm --filter marketing lint 2>&1 | tail -10
echo "=== MKT-B11-C2 FINAL VERIFICATION COMPLETE ==="
```

**Manual smoke test** (required before declaring done):
1. With Founders mode active (DB default): visit `/`, `/pricing`, `/early-access`, `/trades/electrical`, `/features`, `/about`, `/contact`, `/blog` — verify all CTAs say "Be One of the First" and link to `/early-access`
2. **Simulate General Release mode**: temporarily swap the `getSiteMode()` return to `{ mode: 'general', ... }` — verify all CTAs switch to "Start Free Trial" → `/sign-up`, pricing page shows 2-column layout, `/early-access` redirects to `/sign-up`
3. Revert the mock and confirm Founders mode is the live state

> **Any failure must be fixed before the batch is declared done.**

---

## Definition of Done — MKT-B11-C2

- [ ] Pre-modification regression baseline captured
- [ ] Design doc (UI Designer output) fully read before writing any code
- [ ] All mandatory source files read before modifying
- [ ] `GET /api/v1/subscription-tiers?active_only=true` endpoint verified in `openapi_schema_map.md`
- [ ] **Task 1**: `useSiteMode.ts` + `getSiteMode()` created — both modes return correctly
- [ ] **Task 2**: `/sign-up` page created — WaitlistForm reused, copy correct per design
- [ ] **Task 3**: Header CTA switches on mode — desktop AND mobile menu both updated
- [ ] **Task 4**: Homepage hero CTA + bottom CTA switch — General Release has subtext below CTA
- [ ] **Task 5**: Pricing page — both `PricingPageFounders` and `PricingPageRegularRelease` built and tested; `getSiteMode()` controls which renders
- [ ] **Task 6**: `/early-access` redirects to `/sign-up` in General Release mode
- [ ] **Task 7**: TradePageTemplate — 3 CTA locations + pricing body copy switch
- [ ] **Task 8**: All 8 remaining component/page locations updated per spec
- [ ] **Task 9**: Logo assets replaced in `public/`; logo renders correctly in nav + footer
- [ ] Manual smoke test passed: Founders mode verified live; General Release mode verified via mock
- [ ] Zero TypeScript errors (`pnpm --filter marketing build` clean)
- [ ] Zero ESLint warnings (no hardcoded hex values)
- [ ] **Phase 2 FULL verification passes**:
  ```bash
  cd <repo>/frontend && pnpm --filter marketing build && pnpm --filter marketing lint && echo "=== MKT-B11-C2 FINAL VERIFICATION COMPLETE ==="
  ```
- [ ] Completion Summary added to `pilot-launch-plan.md` §MKT-B11

---

## Completion Summary

After all Definition of Done items are complete, add a Completion Summary to `dev-docs/analysis/pilot-launch-plan.md` §MKT-B11:

```markdown
### MKT-B11-C2 — Marketing Site Mode Switch: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot React Engineer
**Baseline**: X tests (marketing)
**Final**: X+N tests

#### What Was Accomplished

- Created `useSiteMode()` / `getSiteMode()` — reads live DB tier via /subscription-tiers?active_only=true; no-store cache; fails open to Founders mode
- Created `/sign-up` page — WaitlistForm reused, General Release copy per designer spec
- Updated Header (desktop + mobile), Homepage (hero + bottom strip), Pricing page (2-column Starter/Teams General Release variant), Early-access (redirect in General Release), TradePageTemplate (3 CTA locations), Features, About, Contact, Blog CTA, Blog post layout, Footer
- Replaced logo assets (logo.svg, logo-dark.svg, favicon.ico, icon-512.png)
- Both modes verified: Founders mode live; General Release mode tested via getSiteMode() mock

#### Files Changed / Created

| File | Action |
|---|---|
| `frontend/apps/marketing/src/lib/useSiteMode.ts` | Created |
| `frontend/apps/marketing/src/app/sign-up/page.tsx` | Created |
| `frontend/apps/marketing/src/app/page.tsx` | Updated — mode-aware hero + bottom CTAs |
| `frontend/apps/marketing/src/app/pricing/page.tsx` | Updated — PricingPageFounders + PricingPageRegularRelease |
| `frontend/apps/marketing/src/app/early-access/page.tsx` | Updated — redirect in General Release |
| `frontend/apps/marketing/src/components/Header.tsx` | Updated — mode-aware CTA |
| `frontend/apps/marketing/src/components/Footer.tsx` | Updated — mode-aware nav link |
| `frontend/apps/marketing/src/components/trades/TradePageTemplate.tsx` | Updated — 3 CTA locations + pricing copy |
| `frontend/apps/marketing/src/app/features/page.tsx` | Updated |
| `frontend/apps/marketing/src/app/about/page.tsx` | Updated |
| `frontend/apps/marketing/src/app/contact/page.tsx` | Updated |
| `frontend/apps/marketing/src/app/blog/page.tsx` | Updated |
| `frontend/apps/marketing/src/components/blog/BlogCta.tsx` | Updated |
| `frontend/apps/marketing/src/components/blog/BlogPostLayout.tsx` | Updated |
| `frontend/apps/marketing/public/logo.svg` | Replaced — new logo |
| `frontend/apps/marketing/public/favicon.ico` | Replaced |
```
