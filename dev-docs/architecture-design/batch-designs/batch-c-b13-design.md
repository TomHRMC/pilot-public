# C-B13 — Marketing Site: /charter Availability + /pricing Rebuild + CTA Changes

**Batch**: C-B13
**Mode**: Pilot Python Engineer (Part A — backend endpoint) → Pilot Marketing UI Designer → Pilot React Engineer (Part B — marketing site updates)
**Prerequisite**: C-B2 ✅ (subscription_tier schema with `signup_cap` + `is_active`)
**Source of truth**: `pilot-tech-impl-spec-v1.md` §10 (Marketing Site), §4.3 (Cohort Cap)
**Status**: ✅ COMPLETE — Part A (Python) + Part B (React) done 2026-08-07
**Date**: August 7, 2026

> **Scope note**: Much of C-B13's marketing site work was already done in C-B1 (Charter rename) and prior marketing batches (MKT-B1 through MKT-B11). This batch covers the **remaining gaps**: the public `charter-availability` endpoint, the availability display on `/charter`, the annual/monthly toggle on `/pricing`, the Charter callout on `/pricing`, and the `/legal/terms` updates.

---

## Overview

C-B13 completes the marketing site changes required for the Charter program. The batch has two halves:

1. **Backend (Part A — Python Engineer)**: A single public endpoint `GET /api/v1/public/charter-availability` returning `{open: bool, remaining: int}`. This is a read-only, no-auth endpoint that queries the Charter tier's `is_active` + `signup_cap` and counts Charter-eligible tenants.

2. **Frontend (Part B — React Engineer, gated on Marketing UI Designer spec)**: Marketing site updates:
   - `/charter` page: fetch availability, show "X spots remaining" only when `remaining <= 8` (GTM §6.8 scarcity rule)
   - `/pricing` page: add annual/monthly toggle (interactive, not static text), add Charter callout while Charter mode is active
   - `/legal/terms`: add Charter rate clause (D22) + 10DLC pass-through disclosure (D24)
   - Homepage hero CTA: verify "Be one of the first twelve" in Charter mode

### What's Already Done (verified via codebase audit)

| Item | Status | Location |
|---|---|---|
| `/charter` page | ✅ Exists | `charter/page.tsx` — full Charter program page with hero, "What You Get", exit guarantee, `CharterApplicationForm` |
| `/early-access` → 308 redirect | ✅ Done | `early-access/page.tsx` — `redirect("/charter")` |
| `CharterApplicationForm` | ✅ Done | `forms/CharterApplicationForm.tsx` — renamed from WaitlistForm in C-B1 |
| `/pricing` mode-aware rendering | ✅ Done | `pricing/page.tsx` — Charter mode (single card $49/mo) + General Release mode (2-column Starter/Teams) |
| JSON-LD two offers | ✅ Done | `pricing/page.tsx` General Release mode — SoftwareApplication with Starter ($49) + Teams ($149) offers |
| Homepage mode-aware | ✅ Done | `page.tsx` — `getSiteMode()` switch |

### What C-B13 Adds

| Item | Owner | Description |
|---|---|---|
| `GET /api/v1/public/charter-availability` | Python | Public no-auth endpoint → `{open, remaining}` |
| `/charter` availability display | React | Fetch availability, show "X spots remaining" when `remaining <= 8` |
| `/pricing` annual/monthly toggle | React | Interactive toggle (not static text) for Starter/Teams pricing |
| `/pricing` Charter callout | React | Charter mode: callout banner linking to `/charter` |
| `/legal/terms` D22 + D24 | React | Charter rate clause + 10DLC pass-through disclosure |
| Homepage hero CTA verification | React | Verify "Be one of the first twelve" in Charter mode (may already be correct) |

---

## A. Input Read Summary

| Input | Source | Key findings |
|---|---|---|
| Spec §10 — Marketing Site | `pilot-tech-impl-spec-v1.md` §10 | `/charter` (new), `/early-access` → 308, `/pricing` 2-col + annual/monthly toggle, JSON-LD two offers, `/legal/terms` D22+D24, `GET /api/v1/public/charter-availability` → `{open, remaining}`. Suppress numeric counter until `remaining <= 8` (GTM §6.8). |
| Spec §4.3 — Cohort Cap | Same, §4.3 | `signup_cap` enforcement: `SELECT count(*) ... FOR UPDATE` on tier row. Cap reached → `is_active = false`. |
| Live DB — `subscription_tier` | MCP (this session) | Charter tier: `tier_name="charter"`, `is_active=true`, `signup_cap=12`, `price_locked=true`. |
| Live DB — `tenant` count | MCP (this session) | 1 tenant with `charter_eligible=true` (dev/test data). `remaining = 12 - 1 = 11`. |
| Existing code — public endpoints | `backend/app/main.py` | Public routes registered with `prefix="/api/v1/public"` — `public_quotes.router`, `public_invoices.router`, `public_short_redirect.router`. C-B13 adds a new public router or extends an existing one. |
| Existing code — marketing routes | `backend/api/routes/marketing.py` | Public marketing waitlist signup (no auth, Turnstile + rate limit). Registered with `prefix="/api/v1/marketing"`. |
| Existing code — `/charter` page | `frontend/apps/marketing/src/app/charter/page.tsx` | Full Charter page with hero, "What You Get" (4 items), exit guarantee, `CharterApplicationForm`. No availability check currently. |
| Existing code — `/pricing` page | `frontend/apps/marketing/src/app/pricing/page.tsx` | Mode-aware: Charter mode (single card $49/mo) + General Release mode (2-column Starter $49/mo + Teams $149/mo). General Release has static "or $41/mo billed annually" text — no interactive toggle. |
| Existing code — `/legal/terms` | `frontend/apps/marketing/src/app/legal/terms/page.tsx` | Existing terms page. Needs Charter rate clause (D22) + 10DLC pass-through disclosure (D24) added. |
| Existing code — homepage | `frontend/apps/marketing/src/app/page.tsx` | Mode-aware via `getSiteMode()`. Hero CTA may already say "Be one of the first twelve" in Charter mode — verify. |
| mvp-arch §16 | `mvp-arch.md` §16 | No §16 platform patterns apply to the marketing site (those are for the authenticated web app). The marketing site uses its own design system (CSS custom properties, not pilotPreset tokens). |

---

## B. Migration Plan

### B.1 — DB Changes

**No migration needed.** All required columns already exist:
- `subscription_tier.is_active` — from C-B2
- `subscription_tier.signup_cap` — from C-B2
- `tenant.charter_eligible` — from C-B2

**No new table.** The availability endpoint is a read-only query.

### B.2 — MCP Verification Queries (pre-implementation)

```sql
-- 1. Verify subscription_tier has is_active + signup_cap for Charter
SELECT tier_name, is_active, signup_cap, price_locked
FROM subscription_tier WHERE tier_name = 'charter';

-- 2. Count Charter-eligible tenants
SELECT COUNT(*) as charter_count FROM tenant WHERE charter_eligible = true;

-- 3. Verify tenant has charter_eligible column
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'tenant'
  AND column_name IN ('charter_eligible', 'charter_member_number')
ORDER BY ordinal_position;
```

### B.3 — Pre-Implementation State

- `subscription_tier`: Charter tier `is_active=true`, `signup_cap=12`
- `tenant`: 1 tenant with `charter_eligible=true` (dev/test data)
- No existing `charter-availability` endpoint

### B.4 — 3-Part NOT NULL Pattern

Not applicable — no new columns.

### B.5 — Audit Columns

Not applicable — no new table.

### B.6 — Seed Data Rollout

Not applicable — no new seed data.

---

## C. Execution Order

| # | Task | Files | Description |
|---|---|---|---|
| 1 | Public charter-availability endpoint | `backend/api/routes/public_charter.py` (NEW) | `GET /api/v1/public/charter-availability` — queries Charter tier `is_active` + `signup_cap`, counts `charter_eligible=true` tenants, returns `{open, remaining}`. No auth. |
| 2 | Register router | `backend/app/main.py` | Register `public_charter.router` with `prefix="/api/v1/public"`. |
| 3 | OpenAPI regen | — | `python export_openapi_json.py` — 1 new endpoint. |
| 4 | Tests | `backend/tests/domains/subscriptions_usage/test_cb13_charter_availability.py` (NEW) | Unit tests for the endpoint. |
| 5 | UI design spec | `dev-docs/marketing-analysis/design-specs/mkt-c-b13-design-spec.md` | Pilot Marketing UI Designer authors the spec. Tom approves. |
| 6 | `/charter` availability display | `frontend/apps/marketing/src/app/charter/page.tsx` | Fetch availability, show "X spots remaining" when `remaining <= 8`. |
| 7 | `/pricing` annual/monthly toggle | `frontend/apps/marketing/src/app/pricing/page.tsx` | Interactive toggle for Starter/Teams pricing. |
| 8 | `/pricing` Charter callout | `frontend/apps/marketing/src/app/pricing/page.tsx` | Charter mode: callout banner linking to `/charter`. |
| 9 | `/legal/terms` updates | `frontend/apps/marketing/src/app/legal/terms/page.tsx` | Add D22 (Charter rate clause) + D24 (10DLC pass-through disclosure). |
| 10 | Homepage hero CTA verification | `frontend/apps/marketing/src/app/page.tsx` | Verify "Be one of the first twelve" in Charter mode. |
| 11 | MSW handler | `frontend/apps/marketing/src/mocks/handlers/` | Handler for `GET /charter-availability`. |
| 12 | React tests | `frontend/apps/marketing/src/__tests__/` | Tests for availability display + pricing toggle. |

---

## D. New API Endpoints

### D.1 — `GET /api/v1/public/charter-availability`

**Auth**: None (public endpoint — no JWT, no Turnstile)
**Rate limiting**: Standard public endpoint rate limit (same as other public endpoints)
**Response**: `CharterAvailabilityResponse` (200 OK)

```json
{
  "open": true,
  "remaining": 11
}
```

**Logic**:
1. Query `subscription_tier` where `tier_name = 'charter'`
2. If tier not found or `is_active = false` → `{"open": false, "remaining": 0}`
3. Count `tenant` rows where `charter_eligible = true`
4. `remaining = signup_cap - count`
5. If `remaining <= 0` → `{"open": false, "remaining": 0}`
6. Return `{"open": true, "remaining": remaining}`

**No `/test` twin needed** — this is a public endpoint with no auth, so the test suite can call it directly.

**Caching consideration**: This endpoint will be called by every visitor to `/charter`. For MVP, no caching (the query is a simple COUNT). A future optimization can add Redis caching with a 60s TTL.

---

## E. Pattern Reuse Decisions

| Pattern | Source | How it applies |
|---|---|---|
| **Public endpoint pattern** | `public_quotes.py`, `public_invoices.py` | No auth, no tenant context. Registered with `prefix="/api/v1/public"`. |
| **RFC 7807 errors** | Standard pattern | Not needed — this endpoint always returns 200 (even when closed). |

---

## F. Shared Module Interfaces

### F.1 — `api/routes/public_charter.py` (NEW)

```python
"""C-B13 — Public Charter availability endpoint.

GET /api/v1/public/charter-availability → {open: bool, remaining: int}
No auth required. Read-only query.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlmodel import Session, select, func

from app.models.core import Tenant
from app.models.subscription import SubscriptionTier
from core.db import get_db

router = APIRouter()


class CharterAvailabilityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    open: bool
    remaining: int


@router.get(
    "/charter-availability",
    response_model=CharterAvailabilityResponse,
)
def get_charter_availability(db: Session = Depends(get_db)):
    """Public endpoint — returns Charter cohort availability.
    
    Returns {open: false, remaining: 0} when:
    - Charter tier not found
    - Charter tier is_active = false (cohort closed)
    - remaining <= 0 (cap reached)
    """
    charter_tier = db.exec(
        select(SubscriptionTier).where(SubscriptionTier.tier_name == "charter")
    ).first()
    
    if not charter_tier or not charter_tier.is_active:
        return CharterAvailabilityResponse(open=False, remaining=0)
    
    charter_count = db.exec(
        select(func.count(Tenant.id)).where(Tenant.charter_eligible == True)
    ).one()
    
    remaining = charter_tier.signup_cap - charter_count
    
    if remaining <= 0:
        return CharterAvailabilityResponse(open=False, remaining=0)
    
    return CharterAvailabilityResponse(open=True, remaining=remaining)
```

---

## G. Open Questions Resolved

| # | Question | Resolution |
|---|---|---|
| 1 | **Should the endpoint be cached?** | **No for MVP.** The query is a simple COUNT on `tenant` + a single-row lookup on `subscription_tier`. At 12 rows max, this is negligible. A future optimization can add Redis caching with a 60s TTL if the `/charter` page gets significant traffic. |
| 2 | **Should `remaining` be suppressed when > 8?** | **No — the suppression is a frontend concern.** The API always returns the true `remaining` count. The frontend `/charter` page decides whether to display it based on the GTM §6.8 rule (show only when `remaining <= 8`). This keeps the API simple and lets the frontend control the UX. |
| 3 | **Does this endpoint need a `/test` twin?** | **No.** This is a public endpoint with no auth — the test suite can call it directly without any test context bypass. |
| 4 | **Should the annual/monthly toggle on `/pricing` be a client-side state or server-side?** | **Client-side.** The pricing page is a static Next.js export. The toggle is pure UI state (which price to display). No API call needed — both prices are already in the page data. |
| 5 | **What about the `/pricing` page in Charter mode?** | **Charter mode stays as-is** (single card $49/mo). The annual/monthly toggle only applies to General Release mode (Starter/Teams 2-column). In Charter mode, there's only one price ($49/mo locked). |
| 6 | **Does the homepage hero CTA need changes?** | **Verify, don't assume.** The homepage already uses `getSiteMode()`. Read the file to confirm the Charter mode hero says "Be one of the first twelve." If it does, no change needed. If not, update it. |

---

## H. Surface Mockup Reference

**Frontend batch**: Part B (React Engineer) — requires a UI design spec from the pilot-marketing-ui-designer before the React prompt is authored.

**Surfaces touched** (all in `apps/marketing`):
1. `/charter` page — add availability display (conditional "X spots remaining" when `remaining <= 8`)
2. `/pricing` page — add annual/monthly toggle (General Release mode only), add Charter callout (Charter mode only)
3. `/legal/terms` page — add D22 (Charter rate clause) + D24 (10DLC pass-through disclosure)
4. Homepage (`/`) — verify hero CTA in Charter mode

**Designer mode**: `pilot-marketing-ui-designer` (not `pilot-web-ui-designer` — this is the marketing site, not the authenticated web app)

**Design spec output**: `dev-docs/marketing-analysis/design-specs/mkt-c-b13-design-spec.md` (per the marketing designer rules)

**§16 pattern consumption**: None — the marketing site does not use the §16 platform patterns (those are for the authenticated web app). The marketing site uses its own design system (CSS custom properties).

**Platform**: Marketing site only (`apps/marketing`). No web app or mobile changes.

---

## I. Component Manifest

| Component | Destination | Purpose |
|---|---|---|
| `CharterAvailabilityBadge` | `apps/marketing/src/components/CharterAvailabilityBadge.tsx` (NEW) | Client component that fetches `/api/v1/public/charter-availability` and shows "X spots remaining" when `remaining <= 8` |
| `PricingToggle` | `apps/marketing/src/components/PricingToggle.tsx` (NEW) | Annual/monthly toggle for the General Release pricing page |
| `public_charter.py` | `backend/api/routes/public_charter.py` (NEW) | Public charter-availability endpoint |

---

## J. Test Plan

### Backend Tests

| Test | Type | Description |
|---|---|---|
| `test_charter_availability_open` | Unit | Charter tier active, 1 Charter tenant → `{open: true, remaining: 11}` |
| `test_charter_availability_closed_tier_inactive` | Unit | Charter tier `is_active=false` → `{open: false, remaining: 0}` |
| `test_charter_availability_closed_cap_reached` | Unit | 12 Charter tenants → `{open: false, remaining: 0}` |
| `test_charter_availability_no_tier` | Unit | Charter tier not found → `{open: false, remaining: 0}` |
| `test_charter_availability_no_auth_required` | Unit | Endpoint returns 200 without any auth headers |

**Domain folder**: `tests/domains/subscriptions_usage/` (Charter availability is subscription-related)

### Frontend Tests (Part B — deferred to React prompt)

| Test | Type | Description |
|---|---|---|
| Availability badge shows when `remaining <= 8` | Integration | `/charter` page renders "X spots remaining" when API returns `remaining <= 8` |
| Availability badge hidden when `remaining > 8` | Integration | `/charter` page does NOT show count when `remaining > 8` |
| Pricing toggle switches prices | Integration | Clicking "Annual" shows annual prices; clicking "Monthly" shows monthly prices |
| Charter callout visible in Charter mode | Integration | `/pricing` in Charter mode shows callout linking to `/charter` |

---

## K. Cost Impact

**$0.** No new AWS services, no new infrastructure. The endpoint is a simple COUNT query on the existing RDS instance. The marketing site is a static Next.js export served from the existing ECS Fargate service.

---

## L. Definition of Done

### Part A (Python Engineer)
- [ ] `api/routes/public_charter.py` created with `GET /charter-availability` endpoint
- [ ] `app/main.py` updated with router registration (`prefix="/api/v1/public"`)
- [ ] OpenAPI regenerated (1 new endpoint)
- [ ] Unit tests written (5 tests minimum) — all passing
- [ ] `pytest -m unit` — 0 new failures
- [ ] Full suite — 0 new failures
- [ ] Ruff — 0 errors on changed/new files
- [ ] MCP-verified: all pre-implementation queries confirmed

### Part B (React Engineer — gated on Marketing UI Designer spec)
- [ ] UI design spec authored by pilot-marketing-ui-designer
- [ ] Tom approves UI design spec
- [ ] `/charter` page updated with availability display
- [ ] `/pricing` page updated with annual/monthly toggle + Charter callout
- [ ] `/legal/terms` updated with D22 + D24 clauses
- [ ] Homepage hero CTA verified in Charter mode
- [ ] MSW handler added + registered
- [ ] Integration tests written
- [ ] `pnpm --filter marketing test` — 0 new failures
- [ ] Type check + lint pass
