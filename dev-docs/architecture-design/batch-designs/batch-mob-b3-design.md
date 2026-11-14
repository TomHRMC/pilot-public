# MOB-B3 Batch Design — Customers Tab: Customer List + Detail

**Version**: 1.0
**Date**: 2026-06-05
**Batch**: MOB-B3
**Prerequisite Batches**: None (independent — parallel-safe with MOB-B2)
**Estimated Effort**: 2–3 days (frontend only — no backend companion required)
**Test Subfolder**: `apps/mobile/__tests__/batch_mob_b3/`
**Platform**: Mobile-only (Expo / React Native)
**Status**: Design complete — ready for React Engineer implementation

---

## A. Input Read Summary

All source artifacts were read directly before writing this document. No content was assumed.

### A.1 Artifacts Read

| Artifact | Key Findings |
|:---|:---|
| `frontend/apps/mobile/app/(tabs)/customers.tsx` | 10-line stub: `<View><Text style={{fontSize:22,fontWeight:'500'}}>Customers</Text></View>`. Replace entirely. |
| `frontend/apps/mobile/app/(tabs)/customers/[id]/comms.tsx` | ✅ Existing route — Customer comms history screen. Navigation pattern: `router.back()`. Header: `← Back`. Uses raw `fetch()` for `fetchCustomerComms` — **pre-existing violation, NOT in scope for MOB-B3** (separate targeted fix needed). Navigates back via `router.back()`. The new `customers/[id]/index.tsx` will navigate to this via `router.push(/(tabs)/customers/${customerId}/comms)`. |
| `frontend/apps/mobile/features/customer-comms/hooks/useCustomerThreads.ts` | Uses raw `fetch("/api/v1/mobile/inbox/customer-threads")`. Rule C violation. **Fix is in scope for MOB-B3** per v2 impl plan §3.4. |
| `frontend/apps/mobile/app/(tabs)/_layout.tsx` | Suppresses `customers/[id]/comms` from tab bar. **Does NOT suppress `customers/[id]/index`** — must be added. |
| `frontend/apps/mobile/mocks/handlers/index.ts` | MOB-B1 and MOB-B2 handlers already registered. Pattern: `import { xHandlers } from "./xHandlers"; ...xHandlers` in the array. |
| `backend/openapi_schema_map.md` §customers | `GET /api/v1/customers/`: params `skip`, `limit`, `search`. Response: `[{ id, tenant_id, type, display_name, first_name, last_name, company_name, email }]`. **`mobile_phone` NOT in list response.** `GET /api/v1/customers/{customer_id}`: same `CustomerResponse` shape — still no `mobile_phone`. See §A.2 critical finding. |
| `backend/openapi_schema_map.md` §sites | `GET /api/v1/sites/?customer_id=` ✅ exists. Response: `[{ id, tenant_id, customer_id, name, notes, jurisdiction_code, is_active, address: object }]`. `customer_id` query param confirmed. |
| MCP: `customer` table | DB has `mobile_phone`, `preferred_contact_channel`, `sms_opted_out`, `sms_opt_in_consent` — but **none appear in `CustomerResponse` from the API**. `type` column is `text` (not enum). |
| MCP: `site` table | DB has `name`, `notes`, `gate_code`, `access_instructions`, `hazard_notes`, `jurisdiction_code`, `is_active`. Site `address` is stored separately (not a column on `site` table itself — the `address: "object"` in API response is likely a joined address entity). |

### A.2 Critical Design Decisions

#### A.2.1 — `CustomerResponse` Has No `mobile_phone` or Contact Channel

`GET /api/v1/customers/{customer_id}` returns: `{ id, tenant_id, type, display_name, first_name, last_name, company_name, email }`. No phone number, no preferred contact channel.

**Resolution**: Display only what the API returns. Customer detail screen shows: name, type badge, email. Do NOT add a backend companion task to expose `mobile_phone` — it is not a stated MVP requirement for mobile customer list. Add a `// TODO: mobile_phone not in CustomerResponse — expose via backend if needed` comment. See §G.1.

#### A.2.2 — Customer `type` Field Values

`type` is `text` in DB. No enum endpoint found. From PRD context, customer types are `"residential"` and `"commercial"`. Hardcode the type badge label map.

#### A.2.3 — Sites API Exists with `?customer_id=` Filter ✅

`GET /api/v1/sites/?customer_id={customerId}` is confirmed. The customer detail screen can show the customer's sites via this endpoint. Site `address` is an object — display `name` and `address` (if address resolves to a formatted string). See §D.3.

#### A.2.4 — `useCustomerThreads` `apiClient` Migration

The hook calls `fetch("/api/v1/mobile/inbox/customer-threads")` — a Rule C violation. Scope: migrate to `apiClient.get(...)` in this batch. Read the correct `apiClient` import from existing hooks before modifying.

---

## B. Migration Plan

### B.1 No Database Migration Required

MOB-B3 is a pure frontend batch. No schema additions.

### B.2 No Backend Companion Task Required

All required API endpoints exist and are verified:
- `GET /api/v1/customers/` (with `?search=`) ✅
- `GET /api/v1/customers/{customer_id}` ✅
- `GET /api/v1/sites/?customer_id=` ✅

### B.3 `_layout.tsx` Route Suppression Required

`customers/[id]/index` must be added to the tab suppression list in `app/(tabs)/_layout.tsx`. Currently missing — without it, Expo Router would auto-discover the file and attempt to show it as a tab bar item.

```typescript
// Add alongside existing customers/[id]/comms suppression:
<Tabs.Screen name="customers/[id]/index" options={{ href: null }} />
```

---

## C. Execution Order

| # | Task | File(s) | Dependency |
|:---:|:---|:---|:---|
| 1 | Read `useCustomerThreads.ts` + find `apiClient` import path | `features/customer-comms/hooks/useCustomerThreads.ts` + existing hooks | None |
| 2 | Migrate `useCustomerThreads.ts` raw `fetch()` → `apiClient` | `useCustomerThreads.ts` | #1 |
| 3 | Create MSW customers handler | `mocks/handlers/customersHandlers.ts` | None |
| 4 | Register handlers in `handlers/index.ts` | `mocks/handlers/index.ts` | #3 |
| 5 | Create `useCustomers` hook | `features/customers/hooks/useCustomers.ts` | None |
| 6 | Create `useCustomerDetail` hook | `features/customers/hooks/useCustomerDetail.ts` | None |
| 7 | Create `useCustomerSites` hook | `features/customers/hooks/useCustomerSites.ts` | None |
| 8 | Create `CustomerListItem` component | `features/customers/components/CustomerListItem.tsx` | None |
| 9 | Create `CustomersTabScreen` component | `features/customers/components/CustomersTabScreen.tsx` | #5, #8 |
| 10 | Create `CustomerDetailScreen` component | `features/customers/components/CustomerDetailScreen.tsx` | #6, #7 |
| 11 | Replace `customers.tsx` stub | `app/(tabs)/customers.tsx` | #9 |
| 12 | Create `customers/[id]/index.tsx` route | `app/(tabs)/customers/[id]/index.tsx` | #10 |
| 13 | Update `(tabs)/_layout.tsx` | `app/(tabs)/_layout.tsx` | #12 |
| 14 | Write unit + integration tests | `__tests__/batch_mob_b3/` + co-located | #9, #10 |
| 15 | Regression check + TypeScript + lint | — | #14 |

---

## D. New API Endpoints Consumed

### D.1 `GET /api/v1/customers/` (existing)

**Used by**: `useCustomers` hook

```
GET /api/v1/customers/?search={query}&limit=50&skip=0
```

**Response** (confirmed from schema map):
```json
[
  {
    "id": "uuid",
    "tenant_id": "uuid",
    "type": "residential",
    "display_name": "John Smith",
    "first_name": "John",
    "last_name": "Smith",
    "company_name": null,
    "email": "john@example.com"
  }
]
```

**Pagination**: `skip`/`limit` (offset-based). Default `limit=100`. For customer list, use `limit=50` to keep page size reasonable.

**Search**: `?search=` param confirmed in schema map. Debounce at 300ms before calling.

### D.2 `GET /api/v1/customers/{customer_id}` (existing)

**Used by**: `useCustomerDetail` hook

**Response** (same `CustomerResponse` shape):
```json
{
  "id": "uuid",
  "tenant_id": "uuid",
  "type": "commercial",
  "display_name": "Acme Corp",
  "first_name": null,
  "last_name": null,
  "company_name": "Acme Corp",
  "email": "billing@acme.example.com"
}
```

⚠️ No `mobile_phone`, no `preferred_contact_channel` in API response. See §G.1.

### D.3 `GET /api/v1/sites/?customer_id={customerId}` (existing)

**Used by**: `useCustomerSites` hook in customer detail screen

```
GET /api/v1/sites/?customer_id={customerId}&limit=20
```

**Response**:
```json
[
  {
    "id": "uuid",
    "tenant_id": "uuid",
    "customer_id": "uuid",
    "name": "Main Office",
    "notes": null,
    "jurisdiction_code": "CA",
    "is_active": true,
    "address": {}
  }
]
```

⚠️ `address` is typed as `"object"` in schema map. The React Engineer must read `backend/openapi.json` to find the actual address sub-schema (street, city, state, zip) before rendering it. If address is a nested object, display `${address.line1}, ${address.city}, ${address.state}` or equivalent. See §G.2.

---

## E. Pattern Reuse Decisions

### E.1 MOB-B1 `useTechJobsList` Pattern — Debounced Search

`useCustomers` follows the same TanStack Query pattern as `useTechJobsList`. Key difference: add debounced search state. Use `setTimeout`/`clearTimeout` at 300ms for the search input before calling the query.

### E.2 MOB-B1 `JobCardRow` Pattern — `CustomerListItem` Component

`CustomerListItem` follows the same row card pattern as `JobCardRow`: display name, type badge, email, chevron. 44pt minimum touch target. `onPress: (customerId: string) => void`.

### E.3 MOB-B1 `JobsTabScreen` Pattern — `CustomersTabScreen` Component

`CustomersTabScreen` follows the same screen structure: `SafeAreaView` → search bar → `FlatList` with `RefreshControl` → loading/error/empty states.

### E.4 `useCustomerThreads` Migration — BETA-B2 `apiClient` Pattern

Read `features/customer-comms/hooks/useReplyToThread.ts` to find the `apiClient` import path (same was used for MOB-B1's `useTechQuotes` migration). Replace `fetch("/api/v1/mobile/inbox/customer-threads")` with `apiClient.get("/api/v1/mobile/inbox/customer-threads").then(r => r.data)`.

---

## F. Shared Module Interfaces

### F.1 `useCustomers` — New Hook

```typescript
// frontend/apps/mobile/features/customers/hooks/useCustomers.ts

export interface CustomerListItem {
  id: string;
  tenant_id: string;
  type: string;                      // "residential" | "commercial"
  display_name: string;
  first_name: string | null;
  last_name: string | null;
  company_name: string | null;
  email: string | null;
}

interface UseCustomersReturn {
  customers: CustomerListItem[];
  isLoading: boolean;
  isError: boolean;
  refetch: () => void;
  isFetching: boolean;
}

export function useCustomers(searchQuery: string = ""): UseCustomersReturn
```

**Internal behavior**:
1. TanStack Query key: `["customers", searchQuery]`
2. Fetch `GET /api/v1/customers/?search=${searchQuery}&limit=50` when `searchQuery` is not empty
3. Fetch `GET /api/v1/customers/?limit=50` when `searchQuery` is empty (no search param)
4. `staleTime: 60_000` (1 minute — customer list changes infrequently)

> **Note**: Debouncing of the search query is handled by the `CustomersTabScreen` component (not inside this hook). The hook receives the already-debounced query string.

### F.2 `useCustomerDetail` — New Hook

```typescript
// frontend/apps/mobile/features/customers/hooks/useCustomerDetail.ts

export function useCustomerDetail(customerId: string): {
  customer: CustomerListItem | undefined;
  isLoading: boolean;
  isError: boolean;
  refetch: () => void;
}
```

TanStack Query key: `["customer-detail", customerId]`
`staleTime: 60_000`

### F.3 `useCustomerSites` — New Hook

```typescript
// frontend/apps/mobile/features/customers/hooks/useCustomerSites.ts

export interface CustomerSite {
  id: string;
  tenant_id: string;
  customer_id: string;
  name: string | null;
  notes: string | null;
  jurisdiction_code: string | null;
  is_active: boolean;
  address: Record<string, unknown>;  // shape verified from openapi.json before rendering
}

export function useCustomerSites(customerId: string): {
  sites: CustomerSite[];
  isLoading: boolean;
  isError: boolean;
}
```

TanStack Query key: `["customer-sites", customerId]`

### F.4 `CustomerListItem` Component — New

```typescript
// frontend/apps/mobile/features/customers/components/CustomerListItem.tsx
interface CustomerListItemProps {
  customer: CustomerListItemData;
  onPress: (customerId: string) => void;
  testID?: string;
}
```

**Displays**:
- `display_name` (primary text)
- Type badge: `type === "residential"` → `"Residential"` (neutral badge); `type === "commercial"` → `"Commercial"` (brand badge)
- `email` if not null (secondary text, truncated)
- Right chevron `>` (`accessibilityRole="button"`)
- Minimum touch height: 44pt

### F.5 `CustomersTabScreen` — New Component

```typescript
// frontend/apps/mobile/features/customers/components/CustomersTabScreen.tsx
// Props: none (self-contained)
```

**Renders**:
1. `<SafeAreaView>` wrapper
2. Screen header: "Customers"
3. **Search bar** (`TextInput` with search icon placeholder): controlled `searchInput` state → debounced via `useEffect` + `setTimeout(300ms)` → `debouncedSearch` → passed to `useCustomers(debouncedSearch)`
4. `<FlatList>` of `CustomerListItem` components — on tap: `router.push(\`/(tabs)/customers/${customer.id}\` as any)`
5. Empty state (no customers): `"No customers found"` centered text
6. Empty search state (search returned nothing): `"No customers match '${searchInput}'"` centered text
7. Loading state: `<ActivityIndicator>` while `isLoading`
8. Error state: "Failed to load customers" + "Try again" pressable
9. Pull-to-refresh: `<RefreshControl>` wired to `refetch()`

### F.6 `CustomerDetailScreen` — New Component

```typescript
// frontend/apps/mobile/features/customers/components/CustomerDetailScreen.tsx
interface CustomerDetailScreenProps {
  customerId: string;
}
```

**Renders** (scrollable `<ScrollView>`):
1. **Header**: `← Back` button, `display_name`, type badge
2. **Contact section**: email row (if present). Add `// TODO: mobile_phone not in CustomerResponse` comment placeholder row.
3. **Sites section**: list of sites from `useCustomerSites`. Each site row: site `name`, address (formatted from `address` object — see §G.2). If no sites: `"No sites on record"`.
4. **"Message Customer"** action button → `router.push(\`/(tabs)/customers/${customerId}/comms\` as any)` (navigates to existing `comms.tsx` route)
5. **Loading state**: `<ActivityIndicator>` while customer or sites loading
6. **Error state**: "Failed to load customer" + retry

---

## G. Open Questions Resolved

### G.1 — `CustomerResponse` Missing `mobile_phone`

**Problem**: DB `customer` table has `mobile_phone` column. API `CustomerResponse` does NOT include it in the schema map.

**Resolution**: MVP customer detail screen shows only `email`. Add placeholder comment `// TODO: mobile_phone not in CustomerResponse — request backend addition if needed`. Do NOT add a backend companion — this is not a stated MVP blocker. Tech can message customer via the comms route.

### G.2 — Site `address` is `"object"` — Shape Unknown

**Problem**: `SiteResponse` schema map shows `"address": "object"` — no sub-schema.

**Resolution**: React Engineer MUST read `backend/openapi.json` before implementing the site address display:
```bash
python3 -c "import json; d=json.load(open('backend/openapi.json')); print(json.dumps(d['components']['schemas'].get('SiteResponse', {}), indent=2))"
```

If `address` contains `line1`, `city`, `state`, `zip`: display as `"${address.line1}, ${address.city}, ${address.state} ${address.zip}"`.

If address shape is unexpected, display `site.name` only and add `// TODO: address rendering when shape confirmed` comment.

### G.3 — `customers/[id]/comms.tsx` Raw `fetch()` — Out of Scope

`customers/[id]/comms.tsx` uses raw `fetch(\`/api/v1/customers/${customerId}/communications?...\`)`. This is a pre-existing violation from FE-B6/B10. It is **NOT in scope for MOB-B3** — that screen existed before and works. Adding it would expand scope unnecessarily. Note it in the completion summary for a future targeted fix.

### G.4 — Pagination for Customer List

**Resolution**: No infinite scroll for MVP. Fetch `limit=50` (first page). If response returns 50 items, show a note "Showing first 50 customers — search to narrow results." Do not implement load-more pagination — 50 customers covers typical MVP contractor (most will have < 50 customers in beta).

### G.5 — `customers/[id]/index` Route — Must Suppress in `_layout.tsx`

**Resolution**: Add `<Tabs.Screen name="customers/[id]/index" options={{ href: null }} />` in `_layout.tsx` alongside the existing `customers/[id]/comms` suppression. Without this, Expo Router auto-discovers the file and adds it as a tab item.

### G.6 — `useCustomerThreads` Migration Scope

The raw `fetch()` in `useCustomerThreads.ts` (calls `GET /api/v1/mobile/inbox/customer-threads`) is used by the SMS inbox screen — it is NOT used by the new customers list or detail screen. However, the v2 impl plan §3.4 assigns this fix to MOB-B3. Migrate in Step 1 of the execution order. After migration, verify existing inbox tests still pass.

---

## H. Surface Mockup Reference

### H.1 Customers Tab Screen Layout

```
┌──────────────────────────────────┐
│  Customers                        │  ← Screen header (SafeAreaView)
│ ─────────────────────────────── │
│  🔍 Search customers…            │  ← Search bar (TextInput)
│ ─────────────────────────────── │
│  [John Smith       ] [Resident.] │  ← CustomerListItem (residential)
│   john@example.com             > │
│ ─────────────────────────────── │
│  [Acme Corp        ] [Commerc. ] │  ← CustomerListItem (commercial)
│   billing@acme.example.com             > │
│ ─────────────────────────────── │
│  [Jane Doe         ] [Resident.] │
│   (no email)                   > │
│ ─────────────────────────────── │
│                                   │
│  [Empty state / No results]       │
└──────────────────────────────────┘
```

### H.2 Customer Detail Screen Layout

```
┌──────────────────────────────────┐
│ ← Back    John Smith  [Resident.] │  ← Header
│ ─────────────────────────────── │
│  ✉️  john@example.com            │  ← Email row
│  📞  (no phone on record)        │  ← Phone placeholder (TODO)
│ ─────────────────────────────── │
│  SITES                           │  ← Sites section header
│ ─────────────────────────────── │
│  Main Home                       │  ← Site row
│   123 Main St, Springfield, IL   │
│ ─────────────────────────────── │
│  Rental Property                 │
│   456 Oak Ave, Springfield, IL   │
│ ─────────────────────────────── │
│  [ Message Customer ]            │  ← Action button → comms
└──────────────────────────────────┘
```

---

## I. Component Manifest

| Component / Hook | File Path | Action | Batch |
|:---|:---|:---|:---|
| `useCustomers` | `apps/mobile/features/customers/hooks/useCustomers.ts` | **New** | MOB-B3 |
| `useCustomerDetail` | `apps/mobile/features/customers/hooks/useCustomerDetail.ts` | **New** | MOB-B3 |
| `useCustomerSites` | `apps/mobile/features/customers/hooks/useCustomerSites.ts` | **New** | MOB-B3 |
| `CustomerListItem` | `apps/mobile/features/customers/components/CustomerListItem.tsx` | **New** | MOB-B3 |
| `CustomersTabScreen` | `apps/mobile/features/customers/components/CustomersTabScreen.tsx` | **New** | MOB-B3 |
| `CustomerDetailScreen` | `apps/mobile/features/customers/components/CustomerDetailScreen.tsx` | **New** | MOB-B3 |
| `customers.tsx` (stub) | `apps/mobile/app/(tabs)/customers.tsx` | **Replace** — import `CustomersTabScreen` | MOB-B3 |
| `customers/[id]/index.tsx` | `apps/mobile/app/(tabs)/customers/[id]/index.tsx` | **New** — route file | MOB-B3 |
| `(tabs)/_layout.tsx` | `apps/mobile/app/(tabs)/_layout.tsx` | **Modify** — add `customers/[id]/index` href:null suppression | MOB-B3 |
| `useCustomerThreads.ts` | `apps/mobile/features/customer-comms/hooks/useCustomerThreads.ts` | **Modify** — migrate raw `fetch()` → `apiClient` | MOB-B3 |
| `customersHandlers.ts` | `apps/mobile/mocks/handlers/customersHandlers.ts` | **New** — MSW fixtures for customers list + detail + sites | MOB-B3 |
| `mocks/handlers/index.ts` | `apps/mobile/mocks/handlers/index.ts` | **Modify** — register `customersHandlers` | MOB-B3 |

---

## J. Test Plan

**Test subfolder**: `apps/mobile/__tests__/batch_mob_b3/`

### J.1 Unit Tests

| Test | File | Assertion |
|:---|:---|:---|
| `useCustomers` calls list endpoint | `useCustomers.test.ts` | Calls `GET /api/v1/customers/?limit=50` with no search |
| `useCustomers` with search sends `?search=` | `useCustomers.test.ts` | `searchQuery="john"` → calls `?search=john&limit=50` |
| `useCustomers` empty search → no `?search=` param | `useCustomers.test.ts` | `searchQuery=""` → `?search=` param absent from request |
| `useCustomerDetail` calls correct endpoint | `useCustomerDetail.test.ts` | Calls `GET /api/v1/customers/{id}` |
| `useCustomerSites` calls sites with customer_id | `useCustomerSites.test.ts` | Calls `GET /api/v1/sites/?customer_id={id}` |
| `CustomerListItem` renders display_name | `CustomerListItem.test.tsx` | `display_name="John Smith"` → "John Smith" visible |
| `CustomerListItem` residential badge | `CustomerListItem.test.tsx` | `type="residential"` → "Residential" badge |
| `CustomerListItem` commercial badge | `CustomerListItem.test.tsx` | `type="commercial"` → "Commercial" badge |
| `CustomerListItem` shows email when present | `CustomerListItem.test.tsx` | `email="j@e.com"` → email text visible |
| `CustomerListItem` handles null email | `CustomerListItem.test.tsx` | `email=null` → no email text; no crash |
| `CustomerListItem` onPress called with id | `CustomerListItem.test.tsx` | Press → `onPress("uuid")` called |
| `useCustomerThreads` uses `apiClient` | `useCustomerThreads.test.ts` | No raw `fetch()` call; `apiClient.get` called with `/api/v1/mobile/inbox/customer-threads` |

### J.2 Integration Tests

| Test | File | Assertion |
|:---|:---|:---|
| Customers tab renders list | `batch_mob_b3/customers-tab.integration.test.tsx` | MSW fixture 3 customers → 3 `CustomerListItem` cards visible |
| Customers tab empty state | `batch_mob_b3/customers-tab.integration.test.tsx` | MSW returns `[]` → empty state copy visible; no list |
| Customers tab loading state | `batch_mob_b3/customers-tab.integration.test.tsx` | Before MSW responds → `ActivityIndicator` present |
| Customers tab error state | `batch_mob_b3/customers-tab.integration.test.tsx` | MSW returns 500 → error state + "Try again" visible |
| Search triggers API call | `batch_mob_b3/customers-tab.integration.test.tsx` | Type "acme" → after debounce → MSW handler called with `?search=acme` |
| Search empty state | `batch_mob_b3/customers-tab.integration.test.tsx` | MSW returns `[]` for search → search-specific empty copy |
| Pull-to-refresh triggers refetch | `batch_mob_b3/customers-tab.integration.test.tsx` | Simulate `onRefresh` → `refetch` called |
| Tap customer → navigates to detail | `batch_mob_b3/customers-tab.integration.test.tsx` | Press customer card → `router.push` called with `customers/${customerId}` |
| Customer detail renders name | `batch_mob_b3/customer-detail.integration.test.tsx` | MSW fixture → customer `display_name` visible |
| Customer detail renders sites | `batch_mob_b3/customer-detail.integration.test.tsx` | MSW returns 2 sites → 2 site rows visible |
| "Message Customer" navigates to comms | `batch_mob_b3/customer-detail.integration.test.tsx` | Press → `router.push` with `customers/${id}/comms` |

### J.3 Regression Tests

| Test | Assertion |
|:---|:---|
| Existing inbox/SMS tests pass | `useCustomerThreads` migration to `apiClient` causes no regressions in FE-B10 inbox tests |
| `(tabs)/_layout.tsx` still suppresses `customers/[id]/comms` | After adding `customers/[id]/index` suppression, existing suppression still present |
| `customers/[id]/comms.tsx` route still works | Existing customer comms screen renders correctly; no import changes |
| MOB-B1/B2 handler tests pass | Adding `customersHandlers` to `handlers/index.ts` does not conflict |

---

## Design Doc Quality Gate Checklist

- [x] `customers.tsx` stub confirmed (10-line centered text) — will be replaced entirely
- [x] `customers/[id]/index.tsx` confirmed NOT existing — new file required
- [x] `customers/[id]/comms.tsx` confirmed existing — is the navigation target (not rebuilt)
- [x] `GET /api/v1/customers/` — params (`skip`, `limit`, `search`) and `CustomerResponse` shape documented
- [x] `GET /api/v1/customers/{customer_id}` — same `CustomerResponse` shape (no `mobile_phone`) — gap documented §G.1
- [x] `GET /api/v1/sites/?customer_id=` — exists, response shape documented with `address: object` gap in §G.2
- [x] MCP queries run — `customer` and `site` DB columns confirmed
- [x] `useCustomerThreads.ts` raw `fetch()` violation confirmed — migration scope assigned Step 1
- [x] `customers/[id]/comms.tsx` raw `fetch()` violation confirmed — out of scope per §G.3
- [x] `_layout.tsx` missing suppression for `customers/[id]/index` — fix required §B.3 and Step 13
- [x] Pagination: `limit=50` + "showing first 50" note — no infinite scroll for MVP §G.4
- [x] Debounce: 300ms on search input, handled in component (not hook) §F.5
- [x] Type badge: hardcoded `residential`/`commercial` — no enum endpoint needed §A.2.2
- [x] Address `object` shape: pre-work required (read `openapi.json`) §G.2
- [x] No backend companion required — all endpoints confirmed
- [x] Infrastructure constraint: zero cost impact
- [x] MSW handler registration pattern confirmed — follows MOB-B1/B2 precedent
