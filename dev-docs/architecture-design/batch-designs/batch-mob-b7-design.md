# Batch MOB-B7 Design — LOTO Tenant-Configurable + Create Customer + Today Tab

**Batch**: MOB-B7 (Mixed — Python Engineer then React Native Engineer)  
**Date**: June 17, 2026  
**Author**: Pilot Architect  
**Status**: DESIGN COMPLETE — Ready for implementation  
**Reference gap analysis**: `dev-docs/analysis/pilot-app-pre-wkstm-3-mvp-ui-api-gap-analysis.md` §2.4, §2.6, §2.7  
**Prerequisites**: B17 Part A complete, MOB-B6 complete

---

## Overview

MOB-B7 is the **final Phase 0.9 batch**. It closes 3 remaining P1 mobile gaps:

1. **LOTO Tenant-Configurable** — gate `LotoCheckSection` on the `loto_confirmation_required` tenant setting. The setting exists in `platform_setting_catalog` but there is no endpoint to expose it to the mobile client. Part A adds a lightweight endpoint; Part B wires the gate.

2. **Create Customer on Mobile** — add an "+" button to `CustomersTabScreen` with a create customer form (touch fallback for when voice is unavailable or noisy environments). The `POST /api/v1/customers/` endpoint already exists (same as FE-B18).

3. **Today Tab Schedule Overview** — refactor the Home tab (`(tabs)/(home)/index.tsx`) to show today's job schedule as the primary content, with the voice CTA as a secondary action. PRD §3.14 says the Today tab is the tech's primary schedule view. Currently the Home tab is voice-session-centric with SMS widget below.

**Part A (Python Engineer)**: Adds one lightweight endpoint to expose `loto_confirmation_required` setting to mobile.  
**Part B (React Native Engineer)**: Builds all three UI surfaces.

---

## A. Input Read Summary

| Input | What was read | Key finding |
|---|---|---|
| PRD §3.4 | LOTO is tenant-configurable — `loto_confirmation_required` default `false` | When disabled: LOTO section is optional; when enabled: gates workflow |
| `LotoCheckSection.tsx` lines 1–50 | `TODO: gate on GET /api/v1/settings/tenant/operations?feature=loto` | Currently always renders; needs gating on `loto_confirmation_required` setting |
| Live DB `platform_setting_catalog` | `loto_confirmation_required` confirmed: `value_type=boolean`, description="When enabled, Voice AI gates job completion..." | Setting exists at platform level; need tenant-effective-value endpoint |
| Gap analysis §2.4 | LOTO not tenant-configurable | Clear: add endpoint + wire gate |
| `CustomersTabScreen.tsx` lines 1–50 | Search-enabled list; no "Add Customer" button; has navigation pattern `router.push(...)` | Add "+" header button + create form |
| `(home)/index.tsx` lines 1–40 | Voice-first layout; `useVoiceSessions` for "Start voice session"; `CustomerMessagesSectionRow` below | PRD §3.14 requires Today = jobs first |
| `JobsTabScreen.tsx` lines 1–50 | `useTechJobsList` with today's jobs + upcoming | Today's job list already built — can extract or reuse for Home tab |
| `backend/api/routes/settings.py` (implied by B17/B18 work) | `GET /api/v1/settings/{key}` returns effective tenant setting | Verify this endpoint supports `loto_confirmation_required` — or add a dedicated lightweight endpoint |

---

## B. Migration Plan

### Part A — Python Engineer (New Endpoint)

**New Endpoint: `GET /api/v1/settings/loto-policy`**

Returns the effective `loto_confirmation_required` value for the current tenant (the tenant override if set, otherwise the platform default which is `false`).

```python
class LotoPolicyResponse(BaseModel):
    loto_confirmation_required: bool
    # false = LOTO section is optional (default)
    # true = LOTO gates clock-out and job completion
```

**Alternative**: Verify if `GET /api/v1/settings/loto_confirmation_required` already works (using the existing generic settings endpoint). If yes: Part A is not needed and Part B just calls that generic endpoint. Check in pre-work.

**Pre-work MCP query**:
```sql
SELECT key, default_value, value_type FROM public.platform_setting_catalog
WHERE key = 'loto_confirmation_required';
```

Also check `platform_setting` table to see if a system default exists.

---

## C. Execution Order

### Part A — Python Engineer

| # | Task | File | Dependency |
|---|---|---|---|
| A1 | Verify if `GET /api/v1/settings/{key}` works for `loto_confirmation_required` | `backend/api/routes/settings.py` (read) | Pre-work |
| A2 | If not: Add `GET /api/v1/settings/loto-policy` endpoint | `backend/api/routes/settings.py` | A1 |
| A3 | Run `pytest -q` | — | A2 |
| A4 | Run `python export_openapi_json.py` | — | A3 |
| **Handoff** | `pnpm sync-api-types` | — | A4 |

### Part B — React Native Engineer

| # | Task | Files | Dependency |
|---|---|---|---|
| B1 | Create MSW handlers for new/existing LOTO policy endpoint + customer create | `mocks/handlers/` | None |
| B2 | Create `useLotoPolicy` hook | `features/jobs/hooks/useLotoPolicy.ts` | B1 |
| B3 | Create `useCreateCustomer` mutation hook | `features/customers/hooks/useCreateCustomer.ts` | B1 |
| B4 | Gate `LotoCheckSection` on `loto_confirmation_required` | `features/jobs/components/detail/LotoCheckSection.tsx` | B2 |
| B5 | Create `CreateCustomerBottomSheet` form | `features/customers/components/CreateCustomerBottomSheet.tsx` | B3 |
| B6 | Add "+" button + `CreateCustomerBottomSheet` to `CustomersTabScreen` | `features/customers/components/CustomersTabScreen.tsx` | B5 |
| B7 | Refactor Home tab — add today's job schedule as primary content | `app/(tabs)/(home)/index.tsx` | None |
| B8 | Write tests | `__tests__/batch_mob_b7/` | All |
| B9 | Full verification | — | B8 |

---

## D. New API Endpoints (Part A)

### Option A: Use existing generic settings endpoint

If `GET /api/v1/settings/loto_confirmation_required` already returns the tenant-effective value, no new endpoint is needed.

### Option B: New lightweight endpoint `GET /api/v1/settings/loto-policy`

```python
@router.get("/loto-policy", response_model=LotoPolicyResponse)
def get_loto_policy(
    current_user: AuthenticatedUser = Depends(require_permission("jobs.view")),
    db: Session = Depends(get_db),
) -> LotoPolicyResponse:
    """Returns effective LOTO policy for the tenant. All roles with jobs.view."""
    value, _ = get_effective_setting(
        db, current_user.tenant_id, "loto_confirmation_required", fallback=False
    )
    return LotoPolicyResponse(loto_confirmation_required=bool(value))
```

Also add `/test` mirror endpoint.

---

## E. Pattern Reuse Decisions

| Pattern | Applied in MOB-B7 |
|---|---|
| `get_effective_setting()` service | LOTO policy uses the same three-tier resolution as other tenant settings |
| `useQuery` with `enabled: !!jobId` | `useLotoPolicy` — always enabled (no job dependency needed; policy is tenant-wide) |
| WatermelonDB offline-first | `useCreateCustomer` uses offline queue — customer creation works offline |
| Soft failure / graceful degradation | If LOTO policy endpoint fails: default to showing LOTO section (`loto_confirmation_required = false` = show optional) |

---

## F. Shared Module Interfaces

### F.1 `useLotoPolicy`

```typescript
// features/jobs/hooks/useLotoPolicy.ts
// Query key: ['loto-policy']
// GET /api/v1/settings/loto-policy (or /api/v1/settings/loto_confirmation_required)
// Returns: { loto_confirmation_required: boolean }
// staleTime: 300_000 (5 min — tenant setting rarely changes mid-session)
// Default on error: { loto_confirmation_required: false } (show section as optional)
```

### F.2 `useCreateCustomer` (mobile)

```typescript
// features/customers/hooks/useCreateCustomer.ts
// POST /api/v1/customers/ (same endpoint as FE-B18)
// Same WatermelonDB offline pattern as other mutations (useCreateExpense, etc.)
// Body: { type, display_name, first_name?, last_name?, company_name?, email?, mobile_phone? }
// onSuccess: invalidate customers query + close bottom sheet
```

### F.3 `LotoCheckSection` Gating

```typescript
// Modify LotoCheckSection.tsx:
// 1. Call useLotoPolicy()
// 2. If loto_confirmation_required === false: render section in "optional" mode
//    - Show section header with "Optional" badge
//    - Tapping items still records them (good for audit trail)
//    - Does NOT gate clock-out or job completion
// 3. If loto_confirmation_required === true: render in "required" mode (current behavior)
//    - Gates clock-out: clock-out disabled until all LOTO items confirmed
```

---

## G. Open Questions Resolved

| Question | Resolution |
|---|---|
| **Does `GET /api/v1/settings/loto_confirmation_required` already exist?** | Verify in pre-work (A1). If yes: skip A2. If no: add `GET /api/v1/settings/loto-policy` as a lightweight dedicated endpoint. |
| **Home tab refactor — should it fully replace voice CTA?** | No. PRD §3.14 says "Today tab pulls each tech's assigned jobs... annotated with site address, customer name, and drive time." The jobs list is the primary content. Voice session CTA moves to a secondary compact row at the top. SMS messages row also remains. The Home tab becomes: [Voice CTA compact] → [Today's Jobs] → [Customer Messages]. |
| **Create Customer mobile form — how much of FE-B18's form to replicate?** | Simplified: type selector + display name + mobile phone + email. No sites or payment methods on mobile (those are web). Keep the form minimal — it's a touch fallback for quick customer creation in the field. |
| **What happens if LOTO policy endpoint returns an error?** | Default to `loto_confirmation_required = false` (optional mode). Do NOT show an error or hide the section. Graceful degradation is required — LOTO should always be accessible even if the policy check fails. |
| **Today tab jobs — use `useTechJobsList` directly or copy from `JobsTabScreen`?** | Reuse `useTechJobsList` hook directly. Extract the "today's jobs" section as a shared sub-component or just inline the same pattern from `JobsTabScreen`. Do not duplicate business logic. |

---

## H. Surface Mockup Reference

**Platform**: Mobile only (`apps/mobile`)

### H.1 LOTO Section — Optional Mode

```
┌─────────────────────────────────────────────────────────────┐
│  LOTO Safety (Optional)                                     │
│  ─────────────────────────────────────────────────────────  │
│  ☐  Verify lockout points                                   │
│  ☐  Test de-energized state                                 │
│  ☐  Confirm tag placement                                   │
└─────────────────────────────────────────────────────────────┘
```

### H.2 Home Tab — Today-First Layout

```
┌─────────────────────────────────────────────────────────────┐
│  [🎙 Start Voice Session]  [View Sessions]                  │
│  ─────────────────────────────────────────────────────────  │
│  TODAY — Monday, Jun 17                                     │
│  ─────────────────────────────────────────────────────────  │
│  9:00am  Johnson Panel Upgrade  [→]                        │
│  1:30pm  Smith Residence        [→]                        │
│  ─────────────────────────────────────────────────────────  │
│  Customer Messages (SMS)                                    │
│  [Tom J.] "Running 20 min late?" 2m ago                   │
└─────────────────────────────────────────────────────────────┘
```

---

## I. Component Manifest

| Component | Path | New or Modify | Engineer |
|---|---|---|---|
| `useLotoPolicy` | `features/jobs/hooks/useLotoPolicy.ts` | **New** | React Native |
| `useCreateCustomer` | `features/customers/hooks/useCreateCustomer.ts` | **New** | React Native |
| `LotoCheckSection` | `features/jobs/components/detail/LotoCheckSection.tsx` | **Modify** | React Native — add policy gate |
| `CreateCustomerBottomSheet` | `features/customers/components/CreateCustomerBottomSheet.tsx` | **New** | React Native |
| `CustomersTabScreen` | `features/customers/components/CustomersTabScreen.tsx` | **Modify** | React Native — add "+" button |
| `(home)/index.tsx` | `app/(tabs)/(home)/index.tsx` | **Modify** | React Native — today-first layout |
| LOTO policy endpoint | `backend/api/routes/settings.py` | **Modify or new** | Python — add if generic doesn't work |
