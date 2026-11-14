# Implementation Prompt: C-B13 (Part B — React Engineer) — Marketing Site Charter Availability + Pricing Toggle

**Mode**: Pilot React Engineer
**Batch**: C-B13 (Part B — React Engineer runs AFTER Part A Python Engineer ✅ + Marketing UI design spec Tom-approved)
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §2.0 row 14r, §2.1a C-5
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-c-b13-design.md` §H (Surface Mockup Reference), §I (Component Manifest)
**UI design spec**: `dev-docs/marketing-analysis/design-specs/mkt-c-b13-design-spec.md` ← **Tom must approve this before you start**
**Estimated session**: 2–3 hours
**Platform**: Marketing site only (`apps/marketing`)
**Backend companion**: C-B13 Part A ✅ COMPLETE 2026-08-07 — `GET /api/v1/public/charter-availability` is live in `openapi_schema_map.md`

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-react-engineer/react-engineer-rules.md`** — in full
- **`dev-docs/architecture-design/batch-designs/batch-c-b13-design.md`** — every section (A–L)
- **`dev-docs/marketing-analysis/design-specs/mkt-c-b13-design-spec.md`** — the Tom-approved UI design spec (if not approved → STOP and ask Tom)

Critical rules for this batch:

- **Rule 1.1**: Before writing ANY hook or API call, verify the endpoint exists in `backend/openapi_schema_map.md`. If it is NOT there → **STOP and ask Tom**.
- **Rule 1.3**: Run `pnpm sync-api-types` before starting — all TypeScript types for backend payloads come from `@pilot/shared-types`.
- **Rule 2**: All API calls use `apiClient` from `@pilot/shared-api`. `fetch()` is permanently banned for `/api/v1/...` calls.
- **Rule 7**: Check `packages/ui/src/index.ts` before creating any new component — but note this batch is in `apps/marketing`, not `apps/web`. The marketing site has its own component structure.
- **Rule 10**: If ANY test fails during your work — even one that appears to be pre-existing — **you must fix it before declaring the batch done**.
- **Rule 11 (React Compiler)**: Do NOT hand-write `useMemo`/`useCallback`/`React.memo` for render-perf.
- **Rule 12 (TanStack Query v5)**: Object-form API only. Colocated query keys. Invalidate after mutations.
- **Rule 15 (WCAG 2.2 AA)**: Focus rings, ≥24×24px targets, `prefers-reduced-motion` fallbacks, non-color-only status.

**Marketing site specifics**:
- The marketing site uses **CSS custom properties** (`var(--brand-600)`, `var(--neutral-900)`, etc.) — NOT `pilotPreset` Tailwind tokens. Follow the existing pattern in the marketing files.
- The marketing site is a **static Next.js export** — no server-side data fetching for tenant data. The `charter-availability` endpoint is public (no auth), so it can be called client-side.
- The marketing site uses `getSiteMode()` for Charter vs General Release mode switching.

---

## Design Decisions (Do Not Re-Litigate)

From Design Doc §G — these decisions are final:

| Decision | Outcome | Rationale |
|---|---|---|
| Availability suppression | API always returns true count; frontend suppresses when `remaining > 8` | GTM §6.8 — scarcity is a UX concern, not an API concern |
| Annual/monthly toggle | Client-side state (no API call) | Both prices are static data in the page; toggle is pure UI |
| Charter mode pricing | No toggle (single price $49/mo) | Charter has one price; toggle only applies to General Release |
| Pricing correction | Starter $59/mo monthly / $49/mo annual; Teams $179/mo monthly / $149/mo annual | Tom confirmed 2026-08-07 — existing page has wrong prices ($49/$41) |

---

## Pre-Work: Establish Regression Baseline

```bash
cd <repo>/frontend
pnpm --filter marketing test 2>&1 | tail -5
```

Record the exact count. These must still pass at the end of the batch.

---

## Pre-Work: Sync API Types

```bash
cd <repo>/frontend
pnpm sync-api-types
```

The `charter-availability` endpoint types must be available before writing hooks.

---

## Pre-Work: Verify Endpoints

```bash
grep -A 5 "charter-availability" backend/openapi_schema_map.md
```

Verified endpoints for this batch:
| Hook | Endpoint | Verified |
|---|---|---|
| `useCharterAvailability` | `GET /api/v1/public/charter-availability` | ✅ (Part A complete) |

---

## Pre-Work: Read These Source Files

Read each of these with `read_file` before writing any code:

```
frontend/apps/marketing/src/app/charter/page.tsx          ← why: the page to modify — add availability badge
frontend/apps/marketing/src/app/pricing/page.tsx          ← why: the page to modify — add toggle + Charter callout + fix prices
frontend/apps/marketing/src/app/legal/terms/page.tsx      ← why: the page to modify — add D22 + D24 clauses
frontend/apps/marketing/src/app/page.tsx                  ← why: verify homepage hero CTA in Charter mode
frontend/apps/marketing/src/app/globals.css               ← why: CSS custom properties (design tokens)
frontend/apps/marketing/src/lib/useSiteMode.ts            ← why: mode-aware hook (Charter vs General Release)
frontend/apps/marketing/src/mocks/handlers/index.ts       ← why: MSW handler registration (if marketing has MSW)
```

Also run:
```bash
find frontend/apps/marketing/src/mocks -name "*.ts" 2>/dev/null | head -10
grep -rn "btn-primary\|card-pricing\|hero-gradient" frontend/apps/marketing/src/app/globals.css | head -10
```

---

## Context: What This Batch Does

| # | Change | File |
|---|---|---|
| 1 | Create `CharterAvailabilityBadge` component | `apps/marketing/src/components/CharterAvailabilityBadge.tsx` (NEW) |
| 2 | Create `PricingToggle` component | `apps/marketing/src/components/PricingToggle.tsx` (NEW) |
| 3 | Update `/charter` page — add availability badge | `apps/marketing/src/app/charter/page.tsx` (updated) |
| 4 | Update `/pricing` page — add toggle + Charter callout + fix prices | `apps/marketing/src/app/pricing/page.tsx` (updated) |
| 5 | Update `/legal/terms` — add D22 + D24 clauses | `apps/marketing/src/app/legal/terms/page.tsx` (updated) |
| 6 | Verify homepage hero CTA | `apps/marketing/src/app/page.tsx` (verify, update if needed) |
| 7 | MSW handler for charter-availability | `apps/marketing/src/mocks/handlers/` (if MSW exists for marketing) |
| 8 | Tests | `apps/marketing/src/__tests__/` or co-located |

---

## STEP 1 — Create `CharterAvailabilityBadge` Component

Create `frontend/apps/marketing/src/components/CharterAvailabilityBadge.tsx`.

Read the UI design spec first for exact pixel specs. This is a `"use client"` component that:
1. Fetches `GET /api/v1/public/charter-availability` on mount (using `apiClient` or a simple `fetch` — note: the marketing site may not use `apiClient` from `@pilot/shared-api` since it's a separate app; check the existing marketing code for the API call pattern)
2. Shows "Only {remaining} spots remaining" when `open == true` and `remaining <= 8`
3. Shows nothing when `open == true` and `remaining > 8` (scarcity suppression per GTM §6.8)
4. Shows "Charter program is full" when `open == false`
5. Shows nothing on loading or error (fail silently)

**Important**: Check how the marketing site makes API calls. It may use `fetch()` directly (since it's a public endpoint, not an authenticated one) or it may use `apiClient`. The React Engineer rules ban `fetch()` for `/api/v1/...` calls — but the marketing site is a separate Next.js app that may have its own conventions. Read the existing marketing code to determine the pattern. If the marketing site uses `fetch()` for public endpoints (like the waitlist form), follow that pattern. If it uses `apiClient`, use that.

**Intermediate verification**: `pnpm --filter marketing test 2>&1 | tail -6`

---

## STEP 2 — Create `PricingToggle` Component

Create `frontend/apps/marketing/src/components/PricingToggle.tsx`.

This is a `"use client"` component with:
- A segmented control: "Monthly" | "Annual"
- Default: "Monthly"
- `role="radiogroup"` with `aria-label="Billing interval"`
- Calls `onToggle(interval: "monthly" | "annual")` when changed
- The parent (`pricing/page.tsx`) uses the selected interval to display the correct prices

**Pricing data** (corrected per Tom 2026-08-07):

| Plan | Monthly | Annual (effective/mo) | Annual (total) |
|---|---|---|---|
| Starter | $59/mo | $49/mo | $588/yr |
| Teams | $179/mo | $149/mo | $1,788/yr |

**Note**: The existing `/pricing` page shows "$49/mo or $41/mo billed annually" for Starter — this is WRONG. The toggle should display the correct prices: $59/mo monthly, $49/mo annual.

**Intermediate verification**: `pnpm --filter marketing test 2>&1 | tail -6`

---

## STEP 3 — Update `/charter` Page

In `frontend/apps/marketing/src/app/charter/page.tsx`:

1. Import `CharterAvailabilityBadge`
2. Add it below the hero headline "Twelve spots. I'm filling them now." (around line 110)
3. The badge is a client component inside a server component — this is fine in Next.js App Router (server components can render client components)

**Intermediate verification**: `pnpm --filter marketing test 2>&1 | tail -6`

---

## STEP 4 — Update `/pricing` Page

In `frontend/apps/marketing/src/app/pricing/page.tsx`:

**General Release mode (`PricingPageGeneralRelease`)**:
1. Add `PricingToggle` above the 2-column pricing cards
2. Make the pricing cards client-side aware of the toggle state — the prices switch between monthly and annual
3. Fix the prices: Starter $59/mo (monthly) / $49/mo (annual, $588/yr); Teams $179/mo (monthly) / $149/mo (annual, $1,788/yr)
4. The existing static "or $41/mo billed annually" text should be replaced by the toggle-driven price display

**Charter mode (`PricingPageCharter`)**:
1. Add a Charter callout banner below the single pricing card, before the FAQ
2. Callout: "Be one of the first twelve — 90 days free, then $49/month locked for as long as you stay."
3. CTA button: "Join the Charter program" linking to `/charter`

**Note**: The `PricingPageGeneralRelease` function is currently a server component (no `"use client"`). Adding the toggle requires making the pricing cards section a client component (or extracting it into a client component). The `PricingToggle` itself is a client component — the parent can stay as a server component and render the client `PricingToggle` + a client `PricingCards` component.

**Intermediate verification**: `pnpm --filter marketing test 2>&1 | tail -6`

---

## STEP 5 — Update `/legal/terms` Page

In `frontend/apps/marketing/src/app/legal/terms/page.tsx`:

Add two new sections:

**D22 — Charter Rate Clause** (add near the subscription/pricing section):
> **Charter Rate.** Charter members receive a locked monthly rate of $49/month for as long as they remain continuously subscribed. This rate is locked at signup and does not change as long as the subscription remains active. Canceling the subscription or upgrading to the Teams plan permanently forfeits the Charter rate — it cannot be reinstated, even if the customer later returns to the Starter plan.

**D24 — 10DLC Pass-Through Disclosure** (add near the SMS/messaging section):
> **10DLC Carrier Fees.** Carrier registration fees for 10DLC (10-digit long code) messaging are passed through at cost. Pilot for Trades does not mark up, add margins to, or profit from carrier registration fees. These fees are set by the carrier (T-Mobile, AT&T, Verizon) and may change without notice. The customer is responsible for all carrier fees associated with their 10DLC messaging registration.

Follow the existing terms page structure (heading + paragraph format).

**Intermediate verification**: `pnpm --filter marketing test 2>&1 | tail -6`

---

## STEP 6 — Verify Homepage Hero CTA

Read `frontend/apps/marketing/src/app/page.tsx` and verify the hero CTA in Charter mode says "Be one of the first twelve" (per spec §10). If it already does, no change needed. If not, update it.

---

## STEP 7 — MSW Handler (if applicable)

Check if the marketing site has MSW handlers. If it does, add a handler for `GET /api/v1/public/charter-availability`. If not, skip this step (the marketing site may not use MSW — it's a static export).

```bash
find frontend/apps/marketing/src/mocks -name "*.ts" 2>/dev/null | head -10
```

---

## STEP 8 — Write Tests

### Unit Tests

Create tests for the new components:
- `CharterAvailabilityBadge.test.tsx` — renders nothing when `remaining > 8`, shows count when `remaining <= 8`, shows "full" when `open == false`
- `PricingToggle.test.tsx` — defaults to Monthly, switches to Annual on click, calls `onToggle` with correct value

### Integration Tests

Create `apps/marketing/src/__tests__/batch_c_b13/`:
- `charter-availability.integration.test.tsx` — `/charter` page renders availability badge
- `pricing-toggle.integration.test.tsx` — `/pricing` General Release mode renders toggle, prices switch correctly
- `pricing-charter-callout.integration.test.tsx` — `/pricing` Charter mode renders callout linking to `/charter`

**TanStack Query setup** (if using TQ for the availability fetch):
```typescript
function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}
```

---

## Final Verification

### Phase 1 — Targeted tests

```bash
cd <repo>/frontend
pnpm --filter marketing test 2>&1 | tail -6
```

### Phase 2 — Full verification

```bash
cd <repo>/frontend && echo "=== UI - Type Check ===" && pnpm --filter @pilot/ui check-types && echo "=== Web - Type Check ===" && pnpm --filter web check-types && echo "=== Mobile - Type Check ===" && pnpm --filter mobile build && echo "=== UI - Lint ===" && pnpm --filter @pilot/ui lint && echo "=== Web - Lint ===" && pnpm --filter web lint && echo "=== Mobile - Lint ===" && pnpm --filter mobile lint && echo "=== TYPE+LINT PASS ===" && echo "=== UI - Tests ===" && pnpm --filter @pilot/ui test 2>&1 | tail -6 && echo "=== Web - Tests ===" && pnpm --filter web test 2>&1 | tail -6 && echo "=== Mobile - Tests ===" && pnpm --filter mobile test 2>&1 | tail -8 && echo "=== MVP FINAL VERIFICATION COMPLETE ==="
```

> **Note**: The marketing site may not have a separate `check-types` or `lint` script — check `package.json`. If not, the type check and lint are covered by the web app's build process (since marketing is part of the same Turborepo workspace).

---

## Definition of Done — C-B13 Part B

- [ ] Pre-modification regression baseline captured
- [ ] `pnpm sync-api-types` run
- [ ] UI design spec read and followed (Tom-approved)
- [ ] All mandatory source files read before modifying
- [ ] `charter-availability` endpoint verified in `openapi_schema_map.md`
- [ ] **STEP 1**: `CharterAvailabilityBadge` component created
- [ ] **STEP 2**: `PricingToggle` component created
- [ ] **STEP 3**: `/charter` page updated with availability badge
- [ ] **STEP 4**: `/pricing` page updated with toggle + Charter callout + corrected prices
- [ ] **STEP 5**: `/legal/terms` updated with D22 + D24 clauses
- [ ] **STEP 6**: Homepage hero CTA verified in Charter mode
- [ ] **STEP 7**: MSW handler added (if marketing uses MSW)
- [ ] **STEP 8**: Unit + integration tests written
- [ ] No hand-written `useMemo`/`useCallback`/`React.memo` (React Compiler)
- [ ] All new hooks use TanStack Query v5 object-form (if applicable)
- [ ] WCAG 2.2 AA (focus rings, ≥24px targets, `prefers-reduced-motion`)
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Zero TypeScript errors
- [ ] Zero ESLint warnings
- [ ] No regressions in pre-existing test suite
- [ ] **Phase 2 FULL verification command passes**
- [ ] Final test count (before → after) documented
- [ ] Completion Summary added to launch plan Appendix B

---

## Completion Summary

After all Definition of Done items are complete:

1. Add a **Completion Summary** subsection to `dev-docs/analysis/pilot-launch-plan.md` Appendix B.

```markdown
### C-B13 (Part B — React Engineer) — Marketing Site Charter Availability + Pricing Toggle: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot React Engineer
**Source design doc**: `batch-c-b13-design.md`
**UI design spec**: `mkt-c-b13-design-spec.md`
**Baseline**: X passed, Y failed (marketing)
**Final**: X+N passed, Y failed (+N new tests)

#### What Was Accomplished

- [Brief description]

#### Files Changed / Created

| File | Action |
|---|---|
| `frontend/apps/marketing/src/components/CharterAvailabilityBadge.tsx` | Created — [what it does] |
| `frontend/apps/marketing/src/components/PricingToggle.tsx` | Created — [what it does] |
| `frontend/apps/marketing/src/app/charter/page.tsx` | Updated — [what changed] |
| `frontend/apps/marketing/src/app/pricing/page.tsx` | Updated — [what changed] |
| `frontend/apps/marketing/src/app/legal/terms/page.tsx` | Updated — [what changed] |
| ... | ... |

#### Tests Added

| Test File | Type | Tests | All Pass |
|---|---|---|---|
| `components/__tests__/CharterAvailabilityBadge.test.tsx` | Unit | N | ✅ |
| `components/__tests__/PricingToggle.test.tsx` | Unit | N | ✅ |
| `__tests__/batch_c_b13/charter-availability.integration.test.tsx` | Integration | N | ✅ |
| ... | ... | ... | ... |
```
