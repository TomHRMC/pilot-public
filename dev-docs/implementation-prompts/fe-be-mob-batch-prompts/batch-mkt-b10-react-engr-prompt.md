# MKT-B10 Part B — React Engineer Prompt: Coming Soon Mode Implementation

**Mode**: Pilot React Engineer  
**Batch**: MKT-B10 Part B  
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §P0 Marketing Website  
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-mkt-b10-design.md`  
**Estimate**: ~3 hours  
**Platform**: `frontend/apps/marketing/` (Next.js static export)  
**UI Designer companion**: `batch-mkt-b10-ui-designer-prompt.md` — **must run before this prompt**

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-react-engineer/react-engineer-rules.md`** — in full
- **`dev-docs/architecture-design/batch-designs/batch-mkt-b10-design.md`** — every section (A–I)

**Critical rules for this batch:**

- **Rule 8**: No new npm dependencies without checking `package.json` first. This batch requires no new dependencies.
- **Rule 9**: `apps/marketing/src/app/layout.tsx` is the root layout. It is a Server Component (`"use server"` or no directive). Do NOT add `"use client"` to the root layout. The `SiteModeGate` wrapper is a Client Component — import it from a separate file.
- **Rule 10**: The marketing app has 0 tests. The regression baseline is 0 tests passing. The only verification is `pnpm --filter marketing build` passing with 0 TypeScript errors and 0 ESLint warnings.

**Critical architecture constraint — MUST read before starting:**
- **Static export constraint**: `apps/marketing/next.config.ts` uses `output: "export"`. This means NO server-side rendering at request time. All HTML is pre-rendered at build time. The `site-config.json` fetch MUST be client-side (`useEffect`) — not in a Server Component, not in `getServerSideProps`, not in a Server Action.
- **`fetch()` for public assets is intentional**: The marketing site README explicitly states that marketing forms use raw `fetch()` — not `apiClient`. The `site-config.json` file is a public S3 asset, not a `/api/v1/` endpoint. Using `fetch('/site-config.json')` here is correct and intentional.

---

## Pre-Work: Establish Regression Baseline

Before touching any file:

```bash
cd <repo>/frontend
pnpm --filter marketing build 2>&1 | tail -10
```

The marketing app has 0 tests. Baseline = build passes with 0 TypeScript errors and 0 ESLint warnings. Record the exact page count from the build output (should be 36 pages from MKT-B9). This number must not decrease after your changes.

> **If the build is already failing before you start**: STOP and ask Tom. Do not proceed with implementation while the build is broken.

---

## Pre-Work: Sync API Types

This batch makes no backend API calls. **Skip `pnpm sync-api-types`** — this batch fetches only a public static asset (`/site-config.json`), not a FastAPI endpoint.

---

## Pre-Work: Verify No New Endpoints Needed

This batch does NOT call any `/api/v1/` endpoints. The `site-config.json` file is a static asset at `/site-config.json` served by S3/CloudFront. Confirm this file does not already exist in `public/`:

```bash
ls frontend/apps/marketing/public/site-config.json 2>/dev/null && echo "EXISTS" || echo "DOES NOT EXIST"
```

Expected: `DOES NOT EXIST` — you will create it as a local dev fixture.

---

## Pre-Work: Read These Source Files

Read each of these before writing any code:

```
frontend/apps/marketing/src/app/layout.tsx
  ← Why: this is the root layout you must modify; understand the existing structure before wrapping {children}

frontend/apps/marketing/src/app/globals.css
  ← Why: all CSS tokens available to ComingSoonPage; do NOT use tokens that don't exist here

frontend/apps/marketing/src/components/Header.tsx
  ← Why: understand how logo is rendered currently; ComingSoonPage should NOT import Header

frontend/apps/marketing/next.config.ts
  ← Why: confirm output: "export" is set (validates the static export constraint)
```

---

## Prerequisite: Receive `ComingSoonPage.tsx` from UI Designer

**This prompt is Part B.** Part A (Marketing UI Designer) produces the visual design for `ComingSoonPage.tsx`.

Before starting implementation:
1. Confirm the UI Designer has delivered `ComingSoonPage.tsx`
2. It should already have the correct props interface: `interface ComingSoonPageProps { message?: string; }`
3. If the UI Designer has not completed Part A → STOP and wait for it

---

## Implementation Tasks

### Task 1: Create `src/lib/site-config.ts`

Create `frontend/apps/marketing/src/lib/site-config.ts`:

```typescript
export type SiteMode = 'live' | 'coming_soon';

export interface SiteConfig {
  mode: SiteMode;
  message?: string;
}

const DEFAULT_CONFIG: SiteConfig = { mode: 'live' };

export async function fetchSiteConfig(): Promise<SiteConfig> {
  try {
    const res = await fetch('/site-config.json', {
      cache: 'no-store',
    });
    if (!res.ok) return DEFAULT_CONFIG;
    const data = await res.json();
    // Validate that mode is a known value — default to 'live' if invalid
    if (data.mode !== 'live' && data.mode !== 'coming_soon') {
      return DEFAULT_CONFIG;
    }
    return data as SiteConfig;
  } catch {
    // Network error, parse error, or missing file → fail open (show live site)
    return DEFAULT_CONFIG;
  }
}
```

**Why `cache: 'no-store'`**: The `site-config.json` file in S3 changes when profile scripts run. Browser cache must not serve a stale value. CloudFront is already invalidated for this file by the profile scripts; the browser cache is the second layer.

---

### Task 2: Place `ComingSoonPage.tsx` from UI Designer

Place the component delivered by the Marketing UI Designer at:

```
frontend/apps/marketing/src/components/ComingSoonPage.tsx
```

Do NOT modify the visual design. If there are TypeScript errors in the received file, fix them. If the component imports Header or Footer — remove those imports (ComingSoonPage is a standalone full-page layout).

---

### Task 3: Create `src/components/SiteModeGate.tsx`

Create `frontend/apps/marketing/src/components/SiteModeGate.tsx`:

```tsx
'use client';

import { useEffect, useState } from 'react';
import { fetchSiteConfig, type SiteConfig } from '@/lib/site-config';
import ComingSoonPage from './ComingSoonPage';

interface SiteModeGateProps {
  children: React.ReactNode;
}

export function SiteModeGate({ children }: SiteModeGateProps) {
  const [config, setConfig] = useState<SiteConfig | null>(null);

  useEffect(() => {
    fetchSiteConfig().then(setConfig);
  }, []);

  // While loading config: render nothing (brief blank — acceptable for this use case)
  // Alternative: render a minimal skeleton matching the coming soon design
  if (!config) return null;

  if (config.mode === 'coming_soon') {
    return <ComingSoonPage message={config.message} />;
  }

  return <>{children}</>;
}
```

**Why `'use client'`**: `useEffect` and `useState` are client-side React hooks. `SiteModeGate` must be a Client Component. The root `layout.tsx` is a Server Component and must stay that way — it imports `SiteModeGate` from a separate `'use client'` file, which is the correct pattern.

---

### Task 4: Wire `SiteModeGate` into Root Layout

Modify `frontend/apps/marketing/src/app/layout.tsx` to wrap `{children}` with `<SiteModeGate>`:

```tsx
import { SiteModeGate } from '@/components/SiteModeGate';

// In the JSX return:
<body>
  <SiteModeGate>
    {children}
  </SiteModeGate>
</body>
```

**Do NOT add `"use client"` to `layout.tsx`**. Importing a Client Component into a Server Component is valid Next.js — the Server Component stays server-side; the Client Component runs client-side. This is the correct pattern.

---

### Task 5: Create Local Dev Test Fixture

Create `frontend/apps/marketing/public/site-config.json`:

```json
{"mode": "live"}
```

This file enables local testing. To test Coming Soon mode locally, change to `{"mode": "coming_soon", "message": "Test message"}` and reload the page.

> **Do NOT commit `{"mode": "coming_soon"}` to this file.** The default should be `{"mode": "live"}` so the full site renders normally in local dev. The `"coming_soon"` mode is toggled by S3/profile scripts in production, not by committing a different value to git.

---

## Two-Phase Final Verification

### Phase 1 — TypeScript + Build

```bash
cd <repo>/frontend

# TypeScript check
pnpm --filter marketing exec tsc --noEmit 2>&1 | tail -10
# Expected: 0 errors

# ESLint check
pnpm --filter marketing lint 2>&1 | tail -10
# Expected: 0 warnings, 0 errors

# Build
pnpm --filter marketing build 2>&1 | tail -15
# Expected: same page count as baseline (≥ 36 pages), 0 TypeScript errors
```

**Phase 1 MUST pass before proceeding to Phase 2.**

### Phase 2 — Manual Visual Test

```bash
# Start the marketing dev server
cd <repo>/frontend
pnpm --filter marketing dev
# Browse to http://localhost:3001
```

**Test Case A — Live mode (default)**:
1. Confirm `public/site-config.json` contains `{"mode": "live"}`
2. Browse to `http://localhost:3001`
3. Expected: full marketing site renders (homepage, nav, hero, all sections)

**Test Case B — Coming Soon mode**:
1. Edit `public/site-config.json` to `{"mode": "coming_soon", "message": "Test coming soon"}`
2. Hard-refresh `http://localhost:3001` (⌘+Shift+R to bypass browser cache)
3. Expected: Coming Soon page replaces all site content
4. Verify: no nav bar, no footer links, no form inputs, `mailto:sales@pilotfortrades.com` link present
5. Verify mobile: resize browser to 375px width — single screen, no horizontal scroll

**Test Case C — Missing config file (fail-open)**:
1. Temporarily rename `public/site-config.json` to `public/site-config.json.bak`
2. Hard-refresh `http://localhost:3001`
3. Expected: full marketing site renders (fail open — no config = live mode)
4. Restore: rename back to `public/site-config.json`

**Test Case D — Revert back to live mode**:
1. Restore `public/site-config.json` to `{"mode": "live"}`
2. Hard-refresh `http://localhost:3001`
3. Expected: full marketing site renders again

After all Phase 2 tests pass, restore `public/site-config.json` to `{"mode": "live"}` before committing.

---

## Definition of Done

**Phase 1 (TypeScript + Build):**
- [ ] `pnpm --filter marketing exec tsc --noEmit` → 0 TypeScript errors
- [ ] `pnpm --filter marketing lint` → 0 warnings, 0 errors
- [ ] `pnpm --filter marketing build` → same or higher page count as baseline, 0 errors
- [ ] `public/site-config.json` contains `{"mode": "live"}` in committed state

**Phase 2 (Manual Visual):**
- [ ] Live mode: full marketing site renders at `localhost:3001`
- [ ] Coming Soon mode: ComingSoonPage replaces all content, no nav/footer/forms visible
- [ ] Mobile (375px): single-screen, no horizontal scroll, readable
- [ ] Fail-open: missing `site-config.json` → full site renders (not a blank page or error)
- [ ] Toggle back: `{"mode": "live"}` restores full site

**Completion:**
- [ ] `public/site-config.json` committed as `{"mode": "live"}`
- [ ] Completion Summary added to `dev-docs/analysis/pilot-launch-plan.md` §P0 Marketing Website

---

## Completion Summary Format

After all Definition of Done items are complete, add to `dev-docs/analysis/pilot-launch-plan.md` §P0 Marketing Website:

```markdown
### MKT-B10 — Coming Soon Mode: Completion Summary

**Completed**: [DATE]
**Mode**: Pilot React Engineer
**Baseline**: 0 tests / build passing / 36 pages
**Final**: 0 tests / build passing / [N] pages

#### What Was Accomplished
- `site-config.ts`: `fetchSiteConfig()` utility created; fetches `/site-config.json` with `cache: 'no-store'`; fails open to `{mode: "live"}` on any error
- `SiteModeGate.tsx`: Client Component; reads site config on mount; renders `<ComingSoonPage>` when `mode === "coming_soon"`, children otherwise
- `ComingSoonPage.tsx`: Full-page Coming Soon layout from Marketing UI Designer (Part A); `props.message?: string` optional override
- `layout.tsx`: Root layout wrapped with `<SiteModeGate>`; Server Component preserved (no `"use client"` added)
- `public/site-config.json`: Dev fixture created with `{"mode": "live"}`; committed in live state

#### Files Changed / Created
| File | Action |
|---|---|
| `apps/marketing/src/lib/site-config.ts` | Created |
| `apps/marketing/src/components/ComingSoonPage.tsx` | Created (from UI Designer) |
| `apps/marketing/src/components/SiteModeGate.tsx` | Created |
| `apps/marketing/src/app/layout.tsx` | Modified — `{children}` wrapped with `<SiteModeGate>` |
| `apps/marketing/public/site-config.json` | Created — `{"mode": "live"}` |
```
