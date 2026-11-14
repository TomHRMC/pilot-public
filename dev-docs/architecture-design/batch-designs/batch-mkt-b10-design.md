# Batch MKT-B10 Design: Marketing Site Coming Soon Mode

**Version**: 1.0  
**Date**: June 30, 2026  
**Batch**: MKT-B10  
**Status**: READY — design complete; awaiting implementation  
**Platform scope**: `frontend/apps/marketing/` only (React/Next.js static export)  
**Engineers**: Marketing UI Designer (Part A — visual design) → React Engineer (Part B — implementation)  
**Estimate**: Part A ~2 hours design; Part B ~3 hours implementation  
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §P0 Marketing Website  
**Design context**: `dev-docs/marketing-analysis/design-specs/mkt-coming-soon-design-spec.md`  
**Operations context**: `dev-docs/devops/aws-ops-runbook.md` §3 Profile A / Profile OFF

---

## A. Input Read Summary

| Input | Key Finding |
|---|---|
| `aws-ops-runbook.md` §3 Profile A | `profile-a-marketing.sh` scales ECS to 1 task; marketing forms at `/api/v1/marketing/*` still work. `profile-off.sh` scales ECS to 0 tasks — marketing forms return 502/503 |
| `profile-off.sh` | Needs to write `{"mode":"coming_soon"}` to S3 `site-config.json` before shutting down ECS. Also needs `CLOUDFRONT_DIST_ID` variable for cache invalidation |
| `profile-a-marketing.sh` | Needs to write `{"mode":"live"}` to S3 `site-config.json` to re-enable full site |
| `apps/marketing/src/app/layout.tsx` | Root layout — this is where `SiteModeGate` must wrap children |
| `apps/marketing/src/app/globals.css` | CSS design tokens — `--gradient-hero-start`, `--gradient-hero-end`, `--brand-*`, `--white-*` must be used. Do NOT invent new tokens |
| `frontend/react-engr-std-prompt-inclusions.md` | All REQUIRED sections confirmed for Part B React prompt |

---

## B. Migration Plan

**No database migrations.** No backend changes.

**New S3 file**: `s3://pilot-production-marketing/site-config.json` — created by profile scripts, not by a migration.

**New files in `apps/marketing/public/`**: `site-config.json` — for local dev testing (gitignored via content; or explicitly added to `.gitignore`)

---

## C. Execution Order

| Step | Description | Owner | Blocks |
|---|---|---|---|
| 1 | Marketing UI Designer designs `ComingSoonPage.tsx` visual spec | Marketing UI Designer | Step 2 |
| 2 | React Engineer implements `site-config.ts` + `SiteModeGate.tsx` + `ComingSoonPage.tsx` + root layout wiring | React Engineer | Step 3 |
| 3 | React Engineer adds `site-config.json` test fixture to `apps/marketing/public/` | React Engineer | Step 4 |
| 4 | DevOps adds `CLOUDFRONT_DIST_ID` variable + S3 config write commands to `profile-a-marketing.sh` and `profile-off.sh` | Tom / DevOps | — |

---

## D. New API Endpoints

**None.** This batch makes no backend changes. The `site-config.json` file is a static JSON asset served by S3/CloudFront — not a FastAPI endpoint.

---

## E. Pattern Reuse Decisions

| Pattern | Applied? | Notes |
|---|---|---|
| Static export (`output: "export"`) constraint | ✅ Yes | No server-side rendering at request time. All mode detection must be client-side (`useEffect`). This is the critical constraint of this entire design |
| Existing CSS design tokens from `globals.css` | ✅ Yes | `ComingSoonPage` uses brand blue gradient tokens, not new tokens |
| `TurnstileProtectedForm` | ❌ No — not applicable | No form submissions when FastAPI is down |
| `fetch()` for public assets | ✅ Yes | `site-config.json` is a public asset, not a `/api/v1/` endpoint. `fetch('/site-config.json')` is correct here — `apiClient` is NOT used (per comment in marketing README: forms use raw `fetch()` intentionally) |

---

## F. Shared Module Interfaces

### `src/lib/site-config.ts`

```typescript
export type SiteMode = 'live' | 'coming_soon';

export interface SiteConfig {
  mode: SiteMode;
  message?: string;  // Optional override message shown on Coming Soon page
}

export async function fetchSiteConfig(): Promise<SiteConfig> {
  // fetch('/site-config.json', { cache: 'no-store' })
  // On error/404: return { mode: 'live' }  ← fail open
}
```

### `src/components/SiteModeGate.tsx`

```typescript
// 'use client' component
// Props: { children: React.ReactNode }
// Behavior:
//   - useEffect → fetchSiteConfig()
//   - While fetching: return null (brief blank — acceptable)
//   - mode === 'coming_soon': return <ComingSoonPage message={config.message} />
//   - mode === 'live': return <>{children}</>
```

### `src/components/ComingSoonPage.tsx`

```typescript
// Props: { message?: string }
// Full-page layout — no nav, no footer links
// Visual design: TO BE DEFINED BY MARKETING UI DESIGNER in Part A
```

---

## G. Open Questions Resolved

| Question | Resolution |
|---|---|
| Can we use server-side rendering to avoid the flash? | No. `output: "export"` pre-renders HTML at build time, not at request time. The config fetch must be client-side. Flash is a brief `return null` — acceptable tradeoff |
| Should forms work in Coming Soon mode? | No. FastAPI is down when `mode === coming_soon`. No form submissions. Use `mailto:sales@pilotfortrades.com` link only |
| What if `site-config.json` doesn't exist yet in S3? | `fetchSiteConfig()` handles 404 by returning `{ mode: 'live' }` — the full site shows. Correct behavior before first deploy |
| Should `site-config.json` be in the Next.js build output? | Yes, place a development version in `apps/marketing/public/site-config.json` for local testing. This file is not committed with sensitive values since it only contains `{"mode":"live"}` |
| Who updates the profile scripts with S3 write commands? | Tom / DevOps after Terraform runs and `CLOUDFRONT_DIST_ID` is known (Step 4 of execution order — not part of this batch's code work) |

---

## H. Surface Mockup Reference (Marketing UI Designer — Part A)

**Platform scope**: `apps/marketing/` — static marketing site  
**Design tokens**: All tokens from `apps/marketing/src/app/globals.css` are available  
**Target component**: `src/components/ComingSoonPage.tsx`

### Required design elements:
1. **Full-page takeover** — no Header nav, no Footer, no marketing page content
2. **Brand blue hero gradient** — use `--gradient-hero-start` / `--gradient-hero-end` (same as homepage hero)
3. **Logo / product name** — "Pilot for Trades" with trademark/product tagline
4. **One-liner description** — what the product does for electrical contractors (≤ 15 words)
5. **Optional custom message** — renders `props.message` if provided (from `site-config.json`)
6. **CTA** — `mailto:sales@pilotfortrades.com` link only. Label: "Get Early Access" or similar
7. **Minimal legal footer** — copyright + `legal@pilotfortrades.com` (no full footer)
8. **Mobile-responsive** — single screen, no scroll needed on mobile

### NOT allowed:
- No form submissions (FastAPI is down)
- No links to other marketing pages (full site is not accessible)
- No nav bar, no footer navigation links
- No new CSS tokens (only use existing `globals.css` tokens)

---

## I. Component Manifest

| Component | File Path | Status |
|---|---|---|
| `SiteConfig` type + `fetchSiteConfig()` | `apps/marketing/src/lib/site-config.ts` | 🆕 Create |
| `SiteModeGate` | `apps/marketing/src/components/SiteModeGate.tsx` | 🆕 Create |
| `ComingSoonPage` | `apps/marketing/src/components/ComingSoonPage.tsx` | 🆕 Create (visual spec from Part A) |
| Root layout wiring | `apps/marketing/src/app/layout.tsx` | ✏️ Modify — wrap `{children}` with `<SiteModeGate>` |
| Local dev test fixture | `apps/marketing/public/site-config.json` | 🆕 Create (content: `{"mode":"live"}`) |
