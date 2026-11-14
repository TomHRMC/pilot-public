# Implementation Prompt: FE-B20 — Catalog Management UI

**Mode**: Pilot React Engineer  
**Batch**: FE-B20  
**Source plan**: `dev-docs/analysis/pilot-app-pre-wkstm-3-prep-plan.md` §Phase 0.9 — FE-B20  
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-fe-b20-design.md`  
**Estimated session**: 4–6 hours  
**Platform**: Web only (`apps/web`)  
**Backend companion**: None — all endpoints exist. Prerequisite: B17 Part A complete + `pnpm sync-api-types`.

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-react-engineer/react-engineer-rules.md`** — in full
- **`dev-docs/architecture-design/batch-designs/batch-fe-b20-design.md`** — every section (A–I)

**Critical rules for this batch:**

- **Rule 1.1**: Before writing ANY hook, verify the exact endpoint path in `backend/openapi_schema_map.md`. Catalog endpoint paths are non-obvious (`/catalog/pricebook` vs `/catalog/pricebook-items`). Do not guess.
- **Rule 1.2**: The `labor_rates.py` route returns raw dicts, not Pydantic schemas. Field names must be verified from the actual openapi.json response schema.
- **Rule 1.3**: Run `pnpm sync-api-types` before starting.
- **Rule 2**: All API calls use `apiClient`. `fetch()` is permanently banned.
- **Rule 7**: Check `packages/ui/src/index.ts` before creating any new component.
- **Rule 8**: No new npm packages without checking `package.json` first.
- **Rule 9**: Route files in `app/(authed)/` are thin server components.
- **Rule 10**: Any test failure must be fixed before declaring done.
- **Temporal supersession pattern**: Markups and labor rates use POST (not PUT/PATCH) to update. POSTing a new value for the same category/skill_level supersedes the previous version. Never try to PATCH or DELETE a markup/labor rate row.

---

## Design Decisions (Do Not Re-Litigate)

From Design Doc §G:

| Decision | Outcome | Rationale |
|---|---|---|
| Catalog placement | Top-level nav item (not under Settings) | Used frequently when building quotes |
| Layout | Sub-routes with tab bar: `/catalog`, `/catalog/labor-rates`, `/catalog/markups`, `/catalog/supplier-items` | Mirrors FE-B18 customer detail pattern |
| Markup category source | `GET /api/v1/job-expense-categories` (from B17) with fallback to hardcoded 3 values | Deterministic seed data makes hardcode safe |
| Skill level codes | Dropdown with `master`, `journeyman`, `apprentice` + free-text allowed | No lookup table for skill levels |
| Supplier items | Read-only list only (no CSV import UI in B20) | Import flow is low priority; backend exists for future |
| Price update | `UpdatePriceModal` separate from item edit | Temporal versioning requires separate POST |

---

## Pre-Work: Establish Regression Baseline

```bash
cd <repo>/frontend
pnpm --filter web test 2>&1 | tail -5
pnpm --filter @pilot/ui test 2>&1 | tail -5
```

Record exact counts. Fix pre-existing failures or confirm with Tom before starting.

---

## Pre-Work: Sync API Types

```bash
cd <repo>/frontend
pnpm sync-api-types
```

---

## Pre-Work: Verify Endpoints

Run ALL of these before writing any hook code:

```bash
# 1. Find exact pricebook endpoint path
python3 -c "
import json
spec = json.load(open('backend/openapi.json'))
pb_paths = [p for p in spec['paths'] if 'pricebook' in p.lower() or 'catalog' in p.lower()]
for p in sorted(pb_paths):
    print(p, '->', list(spec['paths'][p].keys()))
"

# 2. Find supplier items path
python3 -c "
import json
spec = json.load(open('backend/openapi.json'))
sup_paths = [p for p in spec['paths'] if 'supplier' in p.lower()]
for p in sorted(sup_paths):
    print(p, '->', list(spec['paths'][p].keys()))
"

# 3. Find markup endpoints and response schema
grep -A 10 "markups" backend/openapi_schema_map.md | head -30

# 4. Find labor rates endpoints and response schema  
grep -A 10 "labor-rates" backend/openapi_schema_map.md | head -30

# 5. Check catalog permissions
python3 -c "
import json
spec = json.load(open('backend/openapi.json'))
# Check what permission the pricebook list requires
pb_get = spec['paths'].get('/api/v1/catalog/pricebook', {}).get('get', {})
print('Pricebook GET security:', pb_get.get('security', 'none specified'))
"

# 6. Check job-expense-categories endpoint (from B17)
python3 -c "
import json
spec = json.load(open('backend/openapi.json'))
cat_path = [p for p in spec['paths'] if 'expense-categor' in p]
print('Job expense categories paths:', cat_path)
"

# 7. Verify labor rates response field names
python3 -c "
import json
spec = json.load(open('backend/openapi.json'))
lr_get = spec['paths'].get('/api/v1/settings/labor-rates', {}).get('get', {})
schema_ref = lr_get.get('responses', {}).get('200', {}).get('content', {}).get('application/json', {}).get('schema', {})
print('Labor rates response:', schema_ref)
"
```

Record all findings before writing any hook.

| Hook | Endpoint | Verified |
|---|---|---|
| `usePricebook` | `GET /api/v1/catalog/pricebook` (verify exact path) | Confirm before coding |
| `useCreatePricebookItem` | `POST /api/v1/catalog/pricebook` | Confirm before coding |
| `useMarkups` | `GET /api/v1/settings/markups` | Confirm before coding |
| `useSetMarkup` | `POST /api/v1/settings/markups` | Confirm before coding |
| `useLaborRates` | `GET /api/v1/settings/labor-rates` | Confirm before coding |
| `useSetLaborRate` | `POST /api/v1/settings/labor-rates` | Confirm before coding |
| `useSupplierItems` | `GET /api/v1/catalog/supplier-items` (verify path) | Confirm before coding |

---

## Pre-Work: Read These Source Files

```
frontend/apps/web/src/components/AppSidebar.tsx
  ← understand current nav items before adding "Catalog"

frontend/apps/web/src/app/(authed)/customers/[id]/layout.tsx
  ← reference pattern for tab bar + sub-route layout

frontend/apps/web/src/mocks/handlers/index.ts
  ← understand barrel before adding catalog handler file

frontend/packages/ui/src/index.ts
  ← confirm LoadingState, ErrorState, EmptyState, RoleGate imports

frontend/packages/ui/src/role-gate/permissions.ts
  ← find catalog-related permission keys (or confirm they don't exist yet)
```

Also run:
```bash
# List existing catalog-related hooks or components
find frontend/apps/web/src/features -path "*catalog*" | sort

# Check AppSidebar permissions used
grep -n "permission" frontend/apps/web/src/components/AppSidebar.tsx | head -20

# Find any existing modal/dialog pattern to reuse
find frontend/apps/web/src/features -name "*Modal*" | head -10
```

---

## Step 1 — Create Catalog MSW Handlers

**File**: `apps/web/src/mocks/handlers/catalogHandlers.ts` (new)

Read `mocks/handlers/index.ts` first. Create handlers for all catalog endpoints verified in pre-work.

Key fixtures to include:
```typescript
// Pricebook items — use same items as in seed_scenario_quote_to_cash.py for consistency:
// SW-200A: "200A Service Panel", $450.00
// WIRE-12AWG: "Wire 12 AWG (ft)", $0.85
// LABOR-M: "Master Electrician Labor", $120.00/hr

// Active markups:
// materials: 20%, journeyman: $85/hr, etc.
```

**Register in barrel immediately:**
```typescript
// mocks/handlers/index.ts
import { catalogHandlers } from "./catalogHandlers";  // ADD
// ... existing imports ...
export const handlers = [
  // ... existing ...
  ...catalogHandlers,  // ADD — FE-B20
];
```

> **Test resilience**: Never mutate module-level fixture arrays. Mock POST handlers return new items with generated IDs without modifying shared state.

**Intermediate check:**
```bash
pnpm --filter web test 2>&1 | tail -5
```

---

## Steps 2–7 — Create All Hooks

**Directory**: `apps/web/src/features/catalog/hooks/`

Read the verified endpoint shapes from pre-work before coding any hook. All hooks follow the same pattern as existing hooks in `features/customers/hooks/`.

### `usePricebook.ts`

```typescript
// Query key: ['catalog-pricebook', search]
// Endpoint: GET /api/v1/catalog/pricebook?search={search}&skip={skip}&limit={limit}
// staleTime: 60_000
// Returns: PricebookItemResponse[] (each may include current_price nested)
```

### `useCreatePricebookItem.ts`

```typescript
// POST /api/v1/catalog/pricebook
// Body: { sku, name, description?, uom_id?, taxability_code?, initial_price_cents }
// onSuccess: invalidate ['catalog-pricebook']
```

### `useUpdatePricebookItem.ts`

```typescript
// PATCH /api/v1/catalog/pricebook/{itemId}
// Body: { name?, description?, taxability_code?, is_active? }
// Note: sku is intentionally NOT in the request body — it's immutable
// onSuccess: invalidate ['catalog-pricebook']
```

### `useAddPricebookItemPrice.ts`

```typescript
// POST /api/v1/catalog/pricebook/{itemId}/price
// Body: { unit_price_cents, effective_from }
// onSuccess: invalidate ['catalog-pricebook']
```

### `useMarkups.ts`

```typescript
// Query key: ['catalog-markups']
// Endpoint: GET /api/v1/settings/markups
// Returns list of active markup versions (one per category_code)
```

### `useSetMarkup.ts`

```typescript
// POST /api/v1/settings/markups
// Body: { category_code, markup_pct, effective_from? }
// This is a TEMPORAL SUPERSESSION — it creates a new version
// Never PATCH/PUT — always POST to update a markup
// onSuccess: invalidate ['catalog-markups']
```

### `useLaborRates.ts`

```typescript
// Query key: ['catalog-labor-rates']
// Endpoint: GET /api/v1/settings/labor-rates
// Response shape verified from pre-work (raw dict, not Pydantic schema)
```

### `useSetLaborRate.ts`

```typescript
// POST /api/v1/settings/labor-rates
// Body: { skill_level_code, hourly_rate_cents, burden_pct, effective_from? }
// Temporal supersession — always POST
// onSuccess: invalidate ['catalog-labor-rates']
```

### `useSupplierItems.ts`

```typescript
// Query key: ['catalog-supplier-items']
// Endpoint: GET /api/v1/catalog/supplier-items (verify path)
// Read-only — no mutations
```

**Intermediate check:**
```bash
pnpm --filter web test -- --testPathPattern="usePricebook|useMarkup|useLaborRate" 2>&1 | tail -6
```

---

## Steps 7–8 — PricebookItemForm + PricebookItemsPage

### `PricebookItemForm.tsx`

**File**: `apps/web/src/features/catalog/components/PricebookItemForm.tsx`

```typescript
interface PricebookItemFormProps {
  initialValues?: Partial<PricebookItemFormValues>;
  isEdit?: boolean;  // when true, SKU is read-only
  onSubmit: (values: PricebookItemFormValues) => void;
  onCancel: () => void;
  isSubmitting: boolean;
}
```

Fields:
- SKU — text input (required, read-only when `isEdit=true`)
- Name — text input (required)
- Description — textarea (optional)
- Initial Unit Price — number in dollars (required on create; shown but not editable on edit — use "Update Price" for that)
- Taxability Code — select: `taxable` / `exempt` / `non_taxable` (verify valid values in pre-work)

> When editing (`isEdit=true`), SKU field renders as `<span>` or `<input readOnly>` — not a functional input. This prevents accidental mutation of the immutable SKU.

### `PricebookItemsPage.tsx`

```typescript
"use client";
// Features:
// - Search bar → updates useQuery({ queryKey: ['catalog-pricebook', search] })
// - Table: SKU, Name, Description, Current Price, Active badge, Actions
// - "Add Item" button → RoleGate → opens PricebookItemForm in create mode
// - "Edit" per row → opens PricebookItemForm in edit mode (isEdit=true)
// - "💲 Update Price" per row → opens UpdatePriceModal
// - EmptyState when no items
// - LoadingState / ErrorState
```

### `UpdatePriceModal.tsx`

```typescript
interface UpdatePriceModalProps {
  open: boolean;
  itemId: string;
  currentPriceCents: number;  // shown as reference
  onClose: () => void;
}
// Fields: new unit price (dollars), effective from (defaults to today)
// On submit: calls useAddPricebookItemPrice
```

**Intermediate check:**
```bash
pnpm --filter web test -- --testPathPattern="PricebookItem|UpdatePrice" 2>&1 | tail -8
```

---

## Steps 9–11 — Labor Rates, Markups, Supplier Items Pages

### `LaborRatesPage.tsx`

```typescript
"use client";
// Shows table of active rates: Skill Level, Hourly Rate, Burden %, Burdened Rate, Effective From
// Burdened rate = hourly_rate_cents × (1 + burden_pct) — calculate client-side
// "Set Rate" button → RoleGate → opens SetLaborRateModal
// EmptyState when no rates
```

### `SetLaborRateModal.tsx`

```typescript
// Fields:
// - Skill Level: select dropdown with options: master, journeyman, apprentice + "Custom..." text entry
// - Hourly Rate: number in dollars
// - Burden %: decimal (0–99.99)
// - Effective From: date/datetime (defaults to today)
// On submit: calls useSetLaborRate (POST — temporal supersession)
```

### `MarkupsPage.tsx`

```typescript
"use client";
// Shows table of active markups: Category, Markup %, Effective From
// "Set Markup" button → RoleGate → opens SetMarkupModal
// EmptyState when no markups configured
```

### `SetMarkupModal.tsx`

```typescript
// Fields:
// - Category: select dropdown
//   Try to load from GET /api/v1/job-expense-categories (if exists from B17)
//   Fallback: hardcode [materials, equipment, permits]
// - Markup %: number (0–100)
// - Effective From: date (defaults to today)
// On submit: calls useSetMarkup (POST — temporal supersession)
```

### `SupplierItemsPage.tsx`

```typescript
"use client";
// Read-only table: SKU, Name, Description, Category
// Search bar
// EmptyState: "Supplier items appear here after your catalog syncs."
// No create/edit actions
```

---

## Steps 12–14 — Routes + AppSidebar

### Route files (all thin server components)

```typescript
// app/(authed)/catalog/page.tsx
import { PricebookItemsPage } from "@/features/catalog/components/PricebookItemsPage";
export default function CatalogPage() { return <PricebookItemsPage />; }
export const metadata = { title: "Catalog | Pilot" };

// app/(authed)/catalog/labor-rates/page.tsx
import { LaborRatesPage } from "@/features/catalog/components/LaborRatesPage";
export default function LaborRatesRoute() { return <LaborRatesPage />; }

// app/(authed)/catalog/markups/page.tsx
import { MarkupsPage } from "@/features/catalog/components/MarkupsPage";
export default function MarkupsRoute() { return <MarkupsPage />; }

// app/(authed)/catalog/supplier-items/page.tsx
import { SupplierItemsPage } from "@/features/catalog/components/SupplierItemsPage";
export default function SupplierItemsRoute() { return <SupplierItemsPage />; }
```

Consider adding a catalog layout with a shared tab bar (like `customers/[id]/layout.tsx`) so the tabs appear on every catalog sub-page. Read the customers layout before deciding.

### Modify `AppSidebar.tsx`

Read the file first. Add "Catalog" to `NAV_ITEMS`:

```typescript
{ label: "Catalog", href: "/catalog", icon: "📦" },
```

Position it between "Invoices" and "Reports". Add appropriate `<RoleGate>` wrapping if catalog should be owner-only — verify what permission gates the catalog endpoints.

---

## Test Requirements

### Platform: Web (`apps/web`) — Vitest

- `vi.mock()` not `jest.mock()`
- `toBeInTheDocument()` for assertions
- Mock `next/navigation` where needed
- `createWrapper()` with `retry: false` for all TanStack Query tests

### Test Resilience (per `react-engineer-rules.md` Rule 15)

- Never mutate module-level fixture arrays in handlers
- Per-test `server.use(...)` paired with `server.resetHandlers()` in `afterEach`
- Never assert on `toHaveLength(N)` — assert by content or specific ID

### Unit Tests to Write

**`features/catalog/components/__tests__/PricebookItemForm.test.tsx`:**
- Renders without crashing
- SKU input is editable in create mode
- SKU is read-only in edit mode (`isEdit=true`)
- Submit calls onSubmit with correct data shape
- Cancel calls onCancel

**`features/catalog/components/__tests__/SetMarkupModal.test.tsx`:**
- Renders with category dropdown
- Submit calls `useSetMarkup` with `{ category_code, markup_pct }`
- Cancel closes without firing mutation

**`features/catalog/components/__tests__/SetLaborRateModal.test.tsx`:**
- Renders with skill level dropdown showing 3 seeded options
- Burdened rate preview calculates correctly (hourly × (1 + burden))
- Submit calls `useSetLaborRate` with correct payload

### Integration Tests

**`apps/web/src/__tests__/batch_fe_b20/catalogPricebook.integration.test.tsx`:**
1. `/catalog` renders pricebook items table from MSW data
2. "Add Item" visible for owner; hidden for tech
3. Clicking "Add Item" opens PricebookItemForm modal
4. Clicking "💲 Update Price" opens UpdatePriceModal
5. Submitting add form fires POST mutation

**`apps/web/src/__tests__/batch_fe_b20/catalogMarkups.integration.test.tsx`:**
1. `/catalog/markups` renders markup table
2. "Set Markup" opens SetMarkupModal
3. Submitting fires POST to `/api/v1/settings/markups`

---

## Final Verification

### Phase 1 — Targeted

```bash
cd <repo>/frontend

# After hooks:
pnpm --filter web test -- --testPathPattern="usePricebook|useMarkup|useLaborRate" 2>&1 | tail -6

# After components:
pnpm --filter web test -- --testPathPattern="PricebookItem|SetMarkup|SetLaborRate|SupplierItem" 2>&1 | tail -8

# After integration tests:
pnpm --filter web test -- --testPathPattern="batch_fe_b20" 2>&1 | tail -8
```

### Phase 2 — Full Verification

```bash
cd <repo>/frontend && pnpm --filter @pilot/ui check-types && pnpm --filter web check-types && pnpm --filter @pilot/ui lint && pnpm --filter web lint && echo "=== TYPE+LINT PASS ===" && pnpm --filter @pilot/ui test 2>&1 | tail -6 && pnpm --filter web test 2>&1 | tail -6 && echo "=== FE-B20 FINAL VERIFICATION COMPLETE ==="
```

---

## Definition of Done — FE-B20

Update `dev-docs/analysis/pilot-app-pre-wkstm-3-prep-plan.md` §Phase 0.9:

- [ ] Regression baseline captured (zero pre-existing failures, or confirmed with Tom)
- [ ] `pnpm sync-api-types` run
- [ ] Design doc read in full (A–I)
- [ ] All mandatory source files read before modifying (AppSidebar, customers layout as reference, mocks/handlers/index.ts, packages/ui/src/index.ts)
- [ ] All endpoints verified in `openapi_schema_map.md` — exact paths confirmed, labor rates response shape confirmed
- [ ] **Step 1**: `catalogHandlers.ts` created + registered in barrel
- [ ] **Steps 2–7**: All 9 hooks created and tested
- [ ] **Steps 7–8**: `PricebookItemsPage`, `PricebookItemForm`, `UpdatePriceModal` created; pricebook CRUD works end-to-end
- [ ] **Step 9**: `LaborRatesPage` + `SetLaborRateModal` created; temporal supersession via POST works
- [ ] **Step 10**: `MarkupsPage` + `SetMarkupModal` created; category dropdown populated
- [ ] **Step 11**: `SupplierItemsPage` created (read-only)
- [ ] **Steps 12–14**: All 4 route files created; "Catalog" added to AppSidebar nav
- [ ] SKU field is read-only on edit — cannot be mutated after creation
- [ ] Markup/labor rate updates use POST (temporal supersession) — not PATCH/PUT
- [ ] `PricebookItemForm` unit tests pass (create vs edit mode SKU behavior)
- [ ] `SetMarkupModal` unit tests pass
- [ ] `SetLaborRateModal` unit tests pass
- [ ] Integration tests in `__tests__/batch_fe_b20/` pass
- [ ] All new MSW handlers registered in `mocks/handlers/index.ts`
- [ ] No fixture objects mutated in tests
- [ ] Zero TypeScript errors
- [ ] Zero ESLint `no-hardcoded-design-values` warnings
- [ ] **Phase 2 FULL verification passes** (`=== FE-B20 FINAL VERIFICATION COMPLETE ===`):
  ```bash
  cd <repo>/frontend && pnpm --filter @pilot/ui check-types && pnpm --filter web check-types && pnpm --filter @pilot/ui lint && pnpm --filter web lint && echo "=== TYPE+LINT PASS ===" && pnpm --filter @pilot/ui test 2>&1 | tail -6 && pnpm --filter web test 2>&1 | tail -6 && echo "=== FE-B20 FINAL VERIFICATION COMPLETE ==="
  ```
- [ ] Final test count documented
- [ ] Completion Summary added to impl plan §Phase 0.9

---

## Completion Summary

After all DoD items are complete, add a **Completion Summary** to `dev-docs/analysis/pilot-app-pre-wkstm-3-prep-plan.md` under Phase 0.9 — FE-B20:

```markdown
### FE-B20 — Catalog Management UI: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot React Engineer
**Baseline**: X passed (ui) | X passed (web)
**Final**: X+N passed (ui) | X+N passed (web) (+N new tests)

#### What Was Accomplished

- Built /catalog section with 4 tabs: Pricebook, Labor Rates, Markups, Supplier Items
- Pricebook: full CRUD with immutable SKU + temporal price versioning
- Labor Rates: temporal supersession (POST-only) with burdened rate display
- Markups: per-category markup % with temporal supersession
- Supplier Items: read-only list view
- Added "Catalog" to AppSidebar nav

#### Files Changed / Created

| File | Action |
|---|---|
| `apps/web/src/mocks/handlers/catalogHandlers.ts` | Created |
| `apps/web/src/mocks/handlers/index.ts` | Updated |
| `apps/web/src/features/catalog/hooks/usePricebook.ts` | Created |
| `apps/web/src/features/catalog/hooks/useCreatePricebookItem.ts` | Created |
| `apps/web/src/features/catalog/hooks/useUpdatePricebookItem.ts` | Created |
| `apps/web/src/features/catalog/hooks/useAddPricebookItemPrice.ts` | Created |
| `apps/web/src/features/catalog/hooks/useMarkups.ts` | Created |
| `apps/web/src/features/catalog/hooks/useSetMarkup.ts` | Created |
| `apps/web/src/features/catalog/hooks/useLaborRates.ts` | Created |
| `apps/web/src/features/catalog/hooks/useSetLaborRate.ts` | Created |
| `apps/web/src/features/catalog/hooks/useSupplierItems.ts` | Created |
| `apps/web/src/features/catalog/components/PricebookItemsPage.tsx` | Created |
| `apps/web/src/features/catalog/components/PricebookItemForm.tsx` | Created |
| `apps/web/src/features/catalog/components/UpdatePriceModal.tsx` | Created |
| `apps/web/src/features/catalog/components/LaborRatesPage.tsx` | Created |
| `apps/web/src/features/catalog/components/SetLaborRateModal.tsx` | Created |
| `apps/web/src/features/catalog/components/MarkupsPage.tsx` | Created |
| `apps/web/src/features/catalog/components/SetMarkupModal.tsx` | Created |
| `apps/web/src/features/catalog/components/SupplierItemsPage.tsx` | Created |
| `apps/web/src/app/(authed)/catalog/page.tsx` | Created |
| `apps/web/src/app/(authed)/catalog/labor-rates/page.tsx` | Created |
| `apps/web/src/app/(authed)/catalog/markups/page.tsx` | Created |
| `apps/web/src/app/(authed)/catalog/supplier-items/page.tsx` | Created |
| `apps/web/src/components/AppSidebar.tsx` | Updated — added Catalog nav item |

#### Tests Added

| Test File | Type | Tests | All Pass |
|---|---|---|---|
| `features/catalog/components/__tests__/PricebookItemForm.test.tsx` | Unit | N | ✅ |
| `features/catalog/components/__tests__/SetMarkupModal.test.tsx` | Unit | N | ✅ |
| `features/catalog/components/__tests__/SetLaborRateModal.test.tsx` | Unit | N | ✅ |
| `apps/web/src/__tests__/batch_fe_b20/catalogPricebook.integration.test.tsx` | Integration | N | ✅ |
| `apps/web/src/__tests__/batch_fe_b20/catalogMarkups.integration.test.tsx` | Integration | N | ✅ |
```

---

## After This Batch

FE-B20 is complete. The `/catalog` section is fully functional. Owners can now manage pricebook items, set markup percentages, and configure labor rates — all of which feed into the FE-B19 quote builder's line item pricing.

**Next batch**: `batch-fe-b21-react-engr-prompt.md` — Jobs Web Module (List, Detail, Time Entries, Expenses, Profitability).
