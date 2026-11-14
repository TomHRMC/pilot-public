# Batch FE-B20 Design — Catalog Management UI

**Batch**: FE-B20 (Frontend — React Engineer only)  
**Date**: June 16, 2026  
**Author**: Pilot Architect  
**Status**: DESIGN COMPLETE — Ready for implementation  
**Reference gap analysis**: `dev-docs/analysis/pilot-app-pre-wkstm-3-mvp-ui-api-gap-analysis.md` §1.5, §4.3  
**Prerequisites**: B17 Part A complete + `pnpm sync-api-types`

---

## Overview

FE-B20 builds the Catalog Management UI — a `/catalog` section that allows owners to manage:
1. **Pricebook Items** — materials and labor items used in quote line items (CRUD + price versioning)
2. **Labor Rate Versions** — burdened hourly rates by skill level (create/view, temporal)
3. **Markup % Configuration** — category-specific markup percentages (create/view, temporal)
4. **Supplier Items** — read-only view of synced supplier catalog items

This is a **critical prerequisite** for FE-B19's quote builder to show real material pricing when building quotes. Without catalog data, quote line items can only be entered manually with no price lookup.

No backend changes needed — all endpoints exist at `/api/v1/catalog/` and `/api/v1/settings/markups`, `/api/v1/settings/labor-rates`.

---

## A. Input Read Summary

| Input | What was read | Key finding |
|---|---|---|
| PRD §3.2 Catalog & Pricing | Pricebook, markup by category, labor burden rates, supplier sync modes | Three catalog sync modes (api/scrape/manual) — connector config is complex; MVP scope is manual/CSV import only |
| `mvp-arch.md` §2.2, §16 | Catalog architecture | Pricing is snapshotted at quote creation time; catalog feeds `LineItemEditor` in FE-B19 |
| `backend/api/routes/catalog.py` lines 1–120 | Pricebook CRUD endpoints; `_create_supplier_item_impl`, `_list_supplier_items_impl` | Catalog router at `/api/v1/catalog`; pricebook at `/api/v1/catalog/pricebook` |
| `backend/api/routes/markups.py` lines 1–80 | Markup endpoints at `/api/v1/settings/markups`; temporal GiST constraint | `GET /api/v1/settings/markups` returns active markups; `POST` supersedes via temporal |
| `backend/api/routes/labor_rates.py` lines 1–80 | Labor rates at `/api/v1/settings/labor-rates`; temporal versioning | Schemas defined locally in `labor_rates.py` (not in `schemas.py`) — response is a dict |
| `backend/api/schemas/schemas.py` lines 928–987 | `PricebookItemCreate`, `PricebookItemPatch`, `PricebookItemResponse` (with `current_price` nested), `PricebookItemPriceCreate` | `sku` is immutable after creation; price requires separate `POST /api/v1/catalog/pricebook/{id}/price` |
| Live DB `pricebook_item` columns | 11 columns confirmed | `sku` (required), `name` (required), `description`, `uom_id`, `taxability_code`, `is_active` |
| Live DB tables confirmed | `pricebook_item`, `pricebook_item_version`, `supplier_item`, `supplier_item_category`, `supplier_item_uom`, `tenant_markup_version`, `labor_rate_version` | All tables exist |
| `backend/app/main.py` | Route registrations | Catalog: `/api/v1/catalog`; Markups: `/api/v1/settings`; Labor rates: `/api/v1/settings` |
| `frontend/apps/web/src/components/AppSidebar.tsx` | Existing nav items | No "Catalog" entry — must add |
| `frontend/apps/web/src/features/settings-operations/` | `FieldOperationsPage` uses `default_labor_rate_preset` setting — different from labor rate versions | These are platform settings, not the same as labor_rate_version table |

---

## B. Migration Plan

**No Alembic migrations. No backend changes.** FE-B20 is purely frontend.

All required endpoints confirmed to exist:

| Endpoint | Description |
|---|---|
| `GET /api/v1/catalog/pricebook` | List pricebook items with optional `?search=` |
| `POST /api/v1/catalog/pricebook` | Create pricebook item (with initial price) |
| `PATCH /api/v1/catalog/pricebook/{item_id}` | Update pricebook item metadata (not SKU) |
| `POST /api/v1/catalog/pricebook/{item_id}/price` | Add new price version |
| `GET /api/v1/catalog/supplier-items` | List supplier items for tenant |
| `GET /api/v1/settings/markups` | List active markup versions |
| `POST /api/v1/settings/markups` | Set/update markup for a category (temporal supersession) |
| `GET /api/v1/settings/markups/{category_code}/history` | View markup history |
| `GET /api/v1/settings/labor-rates` | List active labor rates |
| `POST /api/v1/settings/labor-rates` | Create/update labor rate (temporal supersession) |

**Pre-work verification needed** (React Engineer runs before coding):
- Verify `GET /api/v1/catalog/pricebook` path exactly — may be `/pricebook` or `/pricebook-items`
- Verify `GET /api/v1/catalog/supplier-items` exact path
- Verify markup POST supersession: is the response `201` or `200`?
- Verify labor rates response shape — `labor_rates.py` uses raw dict, not Pydantic schema

---

## C. Execution Order

| # | Task | Files | Dependency |
|---|---|---|---|
| 1 | Create catalog MSW handlers | `mocks/handlers/catalogHandlers.ts`, `mocks/handlers/index.ts` | None — first |
| 2 | Create `usePricebook` hook (list + search) | `features/catalog/hooks/usePricebook.ts` | 1 |
| 3 | Create `useCreatePricebookItem` + `useUpdatePricebookItem` + `useAddPricebookItemPrice` mutations | `features/catalog/hooks/` | 1 |
| 4 | Create `useMarkups` + `useSetMarkup` hooks | `features/catalog/hooks/useMarkups.ts` | 1 |
| 5 | Create `useLaborRates` + `useSetLaborRate` hooks | `features/catalog/hooks/useLaborRates.ts` | 1 |
| 6 | Create `useSupplierItems` hook (read-only) | `features/catalog/hooks/useSupplierItems.ts` | 1 |
| 7 | Create `PricebookItemForm` component | `features/catalog/components/PricebookItemForm.tsx` | 3 |
| 8 | Create `PricebookItemsPage` — list with search + add/edit | `features/catalog/components/PricebookItemsPage.tsx` | 2, 7 |
| 9 | Create `LaborRatesPage` — list + add rate form | `features/catalog/components/LaborRatesPage.tsx` | 4, 5 |
| 10 | Create `MarkupsPage` — list + set markup form | `features/catalog/components/MarkupsPage.tsx` | 4 |
| 11 | Create `SupplierItemsPage` — read-only list | `features/catalog/components/SupplierItemsPage.tsx` | 6 |
| 12 | Create `/catalog` route with tab navigation | `app/(authed)/catalog/page.tsx`, `app/(authed)/catalog/layout.tsx` (optional) | 8–11 |
| 13 | Create sub-routes: `/catalog/labor-rates`, `/catalog/markups`, `/catalog/supplier-items` | Sub-page route files | 9–11 |
| 14 | Add "Catalog" to `AppSidebar` | `components/AppSidebar.tsx` | None (can parallel) |
| 15 | Write unit + integration tests | `features/catalog/__tests__/`, `__tests__/batch_fe_b20/` | All above |
| 16 | Full verification | — | 15 |

---

## D. API Endpoints Consumed

| Hook | Endpoint | Method | Permission |
|---|---|---|---|
| `usePricebook` | `GET /api/v1/catalog/pricebook` | GET | `catalog.view` or similar |
| `useCreatePricebookItem` | `POST /api/v1/catalog/pricebook` | POST | `catalog.create` |
| `useUpdatePricebookItem` | `PATCH /api/v1/catalog/pricebook/{id}` | PATCH | `catalog.edit` |
| `useAddPricebookItemPrice` | `POST /api/v1/catalog/pricebook/{id}/price` | POST | `catalog.edit` |
| `useMarkups` | `GET /api/v1/settings/markups` | GET | `settings.view` |
| `useSetMarkup` | `POST /api/v1/settings/markups` | POST | `settings.tenant.write` |
| `useLaborRates` | `GET /api/v1/settings/labor-rates` | GET | `settings.view` |
| `useSetLaborRate` | `POST /api/v1/settings/labor-rates` | POST | `settings.tenant.write` |
| `useSupplierItems` | `GET /api/v1/catalog/supplier-items` | GET | `catalog.view` |

> **Permission note**: Verify exact permission keys in `packages/ui/src/role-gate/permissions.ts` before coding. If `catalog.view` doesn't exist, check what permissions the backend requires for `/api/v1/catalog/*` endpoints.

---

## E. Pattern Reuse Decisions

| Pattern | Applied in FE-B20 |
|---|---|
| `<LoadingState>`, `<ErrorState>`, `<EmptyState>` | All list pages |
| `<RoleGate>` | Add/Edit actions gated to owner; read access for all roles |
| `apiClient` | All hooks |
| `retry: false` | All test QueryClient wrappers |
| Temporal supersession for markups/labor rates | UI creates a new row via POST — does NOT have an edit-in-place pattern; show history as read-only trail |

---

## F. Shared Module Interfaces

### F.1 `usePricebook`

```typescript
// features/catalog/hooks/usePricebook.ts
// Query key: ['catalog-pricebook', search]
// Endpoint: GET /api/v1/catalog/pricebook?search={search}&skip={skip}&limit={limit}
// Returns: PricebookItemResponse[] — each includes current_price nested
```

### F.2 `useCreatePricebookItem`

```typescript
// mutationFn: POST /api/v1/catalog/pricebook
// Request: { sku, name, description?, uom_id?, taxability_code?, initial_price_cents }
// Response: PricebookItemResponse
// onSuccess: invalidate ['catalog-pricebook']
```

### F.3 `useAddPricebookItemPrice`

```typescript
// mutationFn: POST /api/v1/catalog/pricebook/{itemId}/price
// Request: { unit_price_cents, effective_from }
// Response: PricebookItemCurrentPriceResponse
// onSuccess: invalidate ['catalog-pricebook']
```

### F.4 `useMarkups`

```typescript
// Query key: ['catalog-markups']
// Endpoint: GET /api/v1/settings/markups
// Returns: TenantMarkupVersionListResponse
// Note: returns ALL active markup categories — UI groups by category_code
```

### F.5 `useSetMarkup`

```typescript
// mutationFn: POST /api/v1/settings/markups
// Request: { category_code, markup_pct, effective_from? }
// Response: TenantMarkupVersionResponse
// Pattern: temporal supersession — always POST to update; never PATCH
// onSuccess: invalidate ['catalog-markups']
```

### F.6 `useLaborRates`

```typescript
// Query key: ['catalog-labor-rates']
// Endpoint: GET /api/v1/settings/labor-rates
// Returns: list of dicts (raw schema in labor_rates.py — verify response shape in pre-work)
```

### F.7 `useSetLaborRate`

```typescript
// mutationFn: POST /api/v1/settings/labor-rates
// Request: { skill_level_code, hourly_rate_cents, burden_pct, effective_from? }
// Pattern: temporal supersession — same as markups
// onSuccess: invalidate ['catalog-labor-rates']
```

---

## G. Open Questions Resolved

| Question | Resolution |
|---|---|
| **Should Catalog be a top-level nav item or under Settings?** | Top-level nav item. Catalog is a primary operational tool that the owner uses frequently when building quotes — not a configuration-level item. Add "Catalog" to `AppSidebar` between "Invoices" and "Reports". |
| **Single page with tabs or sub-routes for Pricebook/Markups/Labor Rates?** | Sub-routes with a top-level tab bar: `/catalog` (pricebook default), `/catalog/labor-rates`, `/catalog/markups`, `/catalog/supplier-items`. Mirrors the customer detail pattern from FE-B18. |
| **Markup categories — where does the list of valid categories come from?** | The `job_expense_category` table (seeded by migrations with `materials`, `equipment`, `permits`). Add `GET /api/v1/job-expense-categories` (added in B17 Part A) as the source for the category dropdown in the Set Markup form. If that endpoint isn't available, hardcode the 3 values as a fallback — the seed data is deterministic. |
| **Labor rate `skill_level_code` — where does the list of valid codes come from?** | No separate lookup table for skill_level_codes — they are free-text in the current schema. Show a dropdown with the 3 seeded values: `master`, `journeyman`, `apprentice`. The user can type custom codes. |
| **Supplier Items — is this a management UI or read-only?** | Read-only list for MVP. PRD §3.2 describes supplier sync as an automated background process (Celery). The UI just shows what's been synced. No CSV import UI in FE-B20 — the CSV import endpoint exists but requires a file upload flow that's low priority. |
| **Price update on pricebook items — modal or inline?** | Modal. Clicking "Update Price" on a pricebook item row opens a small `UpdatePriceModal` with unit price + effective_from fields. The existing price (read from `current_price.default_unit_price_cents`) is shown as the current value for reference. |
| **`sku` is immutable — how to handle in edit form?** | Show `sku` as read-only text (not an input) in the edit form. Only `name`, `description`, `taxability_code`, `is_active` are editable via PATCH. |

---

## H. Surface Mockup Reference

**Platform**: Web only (`apps/web`)

### H.1 `/catalog` — Pricebook Items (default tab)

```
┌─────────────────────────────────────────────────────────────────┐
│  Catalog                                                        │
│  [Pricebook] [Labor Rates] [Markups] [Supplier Items]          │
│  ─────────────────────────────────────────────────────────────  │
│  Pricebook Items                    [+ Add Item]               │
│  [Search items...]                                              │
│  ─────────────────────────────────────────────────────────────  │
│  SKU           Name                Current Price    Actions    │
│  SW-200A       200A Service Panel  $450.00          [Edit] [💲]│
│  WIRE-12AWG    Wire 12 AWG (ft)    $0.85            [Edit] [💲]│
│  LABOR-M       Master Electrician  $120.00/hr       [Edit] [💲]│
└─────────────────────────────────────────────────────────────────┘
```

- "Add Item" button: `<RoleGate>` → opens `PricebookItemForm` modal
- "Edit" button: opens same `PricebookItemForm` pre-filled (SKU read-only)
- "💲" (Update Price) button: opens small `UpdatePriceModal`

### H.2 `/catalog/labor-rates` — Labor Rate Versions

```
┌─────────────────────────────────────────────────────────────────┐
│  Labor Rates                                [+ Set Rate]        │
│  ─────────────────────────────────────────────────────────────  │
│  Skill Level       Rate          Burdened Rate   Effective      │
│  master            $120.00/hr    $138.00/hr       Jun 1, 2026  │
│  journeyman        $85.00/hr     $97.75/hr        Jun 1, 2026  │
│  apprentice        $55.00/hr     $63.25/hr        Jun 1, 2026  │
│                                                                 │
│  History: [View history per skill level]                        │
└─────────────────────────────────────────────────────────────────┘
```

- "Set Rate" button: opens `SetLaborRateModal` — temporal supersession creates new version
- Burdened rate = `hourly_rate_cents × (1 + burden_pct)` calculated client-side for display

### H.3 `/catalog/markups` — Markup % Configuration

```
┌─────────────────────────────────────────────────────────────────┐
│  Markup Percentages                        [+ Set Markup]       │
│  ─────────────────────────────────────────────────────────────  │
│  Category          Current Markup     Effective                 │
│  materials         20%                Jun 1, 2026              │
│  equipment         15%                Jun 1, 2026              │
│  permits           0%                 Jun 1, 2026              │
└─────────────────────────────────────────────────────────────────┘
```

- "Set Markup" button: opens `SetMarkupModal` with category dropdown (from `job-expense-categories`) + markup_pct field
- Temporal supersession: posting a new value for same category supersedes the old one

---

## I. Component Manifest

| Component | Path | New or Modify | Notes |
|---|---|---|---|
| `PricebookItemsPage` | `features/catalog/components/PricebookItemsPage.tsx` | **New** | List + search + add/edit |
| `PricebookItemForm` | `features/catalog/components/PricebookItemForm.tsx` | **New** | Add/edit form (SKU immutable on edit) |
| `UpdatePriceModal` | `features/catalog/components/UpdatePriceModal.tsx` | **New** | Set new price version |
| `LaborRatesPage` | `features/catalog/components/LaborRatesPage.tsx` | **New** | List active rates + set rate form |
| `SetLaborRateModal` | `features/catalog/components/SetLaborRateModal.tsx` | **New** | Temporal supersession form |
| `MarkupsPage` | `features/catalog/components/MarkupsPage.tsx` | **New** | List active markups + set markup form |
| `SetMarkupModal` | `features/catalog/components/SetMarkupModal.tsx` | **New** | Category dropdown + markup_pct |
| `SupplierItemsPage` | `features/catalog/components/SupplierItemsPage.tsx` | **New** | Read-only supplier items list |
| `usePricebook` | `features/catalog/hooks/usePricebook.ts` | **New** | List with optional search |
| `useCreatePricebookItem` | `features/catalog/hooks/useCreatePricebookItem.ts` | **New** | POST mutation |
| `useUpdatePricebookItem` | `features/catalog/hooks/useUpdatePricebookItem.ts` | **New** | PATCH mutation |
| `useAddPricebookItemPrice` | `features/catalog/hooks/useAddPricebookItemPrice.ts` | **New** | POST price version |
| `useMarkups` | `features/catalog/hooks/useMarkups.ts` | **New** | GET active markups |
| `useSetMarkup` | `features/catalog/hooks/useSetMarkup.ts` | **New** | POST temporal supersession |
| `useLaborRates` | `features/catalog/hooks/useLaborRates.ts` | **New** | GET active labor rates |
| `useSetLaborRate` | `features/catalog/hooks/useSetLaborRate.ts` | **New** | POST temporal supersession |
| `useSupplierItems` | `features/catalog/hooks/useSupplierItems.ts` | **New** | GET read-only supplier items |
| `catalog/page.tsx` | `app/(authed)/catalog/page.tsx` | **New** | Default tab → PricebookItemsPage |
| `catalog/labor-rates/page.tsx` | `app/(authed)/catalog/labor-rates/page.tsx` | **New** | LaborRatesPage |
| `catalog/markups/page.tsx` | `app/(authed)/catalog/markups/page.tsx` | **New** | MarkupsPage |
| `catalog/supplier-items/page.tsx` | `app/(authed)/catalog/supplier-items/page.tsx` | **New** | SupplierItemsPage |
| `AppSidebar.tsx` | `components/AppSidebar.tsx` | **Modify** | Add "Catalog" nav item |
| `catalogHandlers.ts` | `mocks/handlers/catalogHandlers.ts` | **New** | MSW for all catalog endpoints |
| `mocks/handlers/index.ts` | `mocks/handlers/index.ts` | **Modify** | Register `...catalogHandlers` |
