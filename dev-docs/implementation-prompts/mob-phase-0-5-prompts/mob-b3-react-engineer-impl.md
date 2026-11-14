# Implementation Prompt: MOB-B3 — Customers Tab: Customer List + Detail

**Mode**: Pilot React Engineer
**Batch**: MOB-B3
**Source plan**: `dev-docs/analysis/pilot-app-beta-fixes-v2-impl-plan.md` §8 MOB-B3
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-mob-b3-design.md`
**Estimated session**: 2–3 days
**Platform**: Mobile only (`apps/mobile`)
**Backend companion**: None required — all endpoints exist
**Prerequisites**: None — independent batch, parallel-safe with MOB-B2

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:
- **`dev-docs/architecture-design/batch-designs/batch-mob-b3-design.md`** — every section (A–J)
- **`.roo/rules-pilot-react-engineer/react-engineer-rules.md`** — in full

Critical rules for this batch:
- **Rule A**: Verify endpoint shapes from `backend/openapi_schema_map.md`. `CustomerResponse` does NOT have `mobile_phone` — do not attempt to display it.
- **Rule C**: All API calls use `apiClient` — not raw `fetch()`. This batch fixes the `useCustomerThreads.ts` violation.
- **Rule D**: Read every source file before editing it. Never assume contents.
- **No new npm dependencies** without Tom's approval.

---

## Pre-Work: Establish Regression Baseline

```bash
cd <repo>/frontend
pnpm --filter mobile test 2>&1 | tail -8
```

Record the exact test count. Expected starting point: ≥ 57 suites / 369 tests (MOB-B1 final). If MOB-B2 is also complete, count will be higher — record whatever the current baseline is.

---

## Pre-Work: Read These Files First

```bash
# Confirm customers.tsx is the 10-line stub
cat frontend/apps/mobile/app/(tabs)/customers.tsx

# Confirm customers/[id]/index.tsx does NOT exist (only comms.tsx)
ls frontend/apps/mobile/app/(tabs)/customers/[id]/

# Existing comms route (navigation target — do not modify)
cat frontend/apps/mobile/app/(tabs)/customers/[id]/comms.tsx

# Raw fetch violation to fix
cat frontend/apps/mobile/features/customer-comms/hooks/useCustomerThreads.ts

# Layout file — see existing suppression pattern
cat frontend/apps/mobile/app/(tabs)/_layout.tsx

# MSW handler registration pattern
cat frontend/apps/mobile/mocks/handlers/index.ts

# Find correct apiClient import path for mobile
cat frontend/apps/mobile/features/customer-comms/hooks/useReplyToThread.ts

# Verify address sub-schema before implementing site display
python3 -c "import json; d=json.load(open('backend/openapi.json')); print(json.dumps(d.get('components',{}).get('schemas',{}).get('SiteResponse',{}), indent=2))"

# Styling tokens (use these — do NOT hardcode colors/spacing)
cat frontend/apps/mobile/constants/style-constants.ts
```

---

## Context: What This Batch Does

Replaces the 10-line `customers.tsx` stub with a fully functional customer list with search, and adds a new `customers/[id]/index.tsx` detail screen.

| Item | Change |
|---|---|
| `customers.tsx` | Replace stub with `<CustomersTabScreen />` |
| `(tabs)/_layout.tsx` | Add `customers/[id]/index` href:null suppression |
| `useCustomerThreads.ts` | Migrate raw `fetch()` → `apiClient` |
| New: `useCustomers` hook | `GET /api/v1/customers/?search=&limit=50` |
| New: `useCustomerDetail` hook | `GET /api/v1/customers/{id}` |
| New: `useCustomerSites` hook | `GET /api/v1/sites/?customer_id=` |
| New: `CustomerListItem` component | Customer row: name, type badge, email, chevron |
| New: `CustomersTabScreen` component | Search bar + FlatList + states |
| New: `CustomerDetailScreen` component | Header + contact + sites + Message button |
| New: `customers/[id]/index.tsx` | Route file rendering `<CustomerDetailScreen />` |
| New: `customersHandlers.ts` | MSW fixtures for customers + sites endpoints |

---

## Step 0: Fix `useCustomerThreads.ts` Raw `fetch()` Violation

Read `useCustomerThreads.ts` first. Then:

1. Identify the `apiClient` import path for mobile (read `useReplyToThread.ts` — this is the same path used in MOB-B1's `useTechQuotes` migration)
2. Replace the `fetchCustomerThreads` function:
   ```typescript
   // ❌ Before
   const res = await fetch("/api/v1/mobile/inbox/customer-threads");

   // ✅ After — verify exact import path from useReplyToThread.ts
   import { apiClient } from "@/lib/api-client"; // verify path

   const { data } = await apiClient.get<CustomerThreadsResponse>(
     "/api/v1/mobile/inbox/customer-threads"
   );
   return data;
   ```
3. Verify the existing inbox MSW handler (`communicationsHandlers.ts`) covers this endpoint — if yes, existing tests should pass unchanged
4. Run existing inbox tests to confirm no regressions:
   ```bash
   pnpm --filter mobile test -- --testPathPattern="inbox|thread|comm" 2>&1 | tail -15
   ```

---

## Step 1: Create MSW Customers Handler

**File**: `frontend/apps/mobile/mocks/handlers/customersHandlers.ts`

Read `mocks/handlers/jobsHandlers.ts` and `mocks/handlers/jobDetailHandlers.ts` first to understand the pattern.

The handler must cover:

```typescript
// GET /api/v1/customers/ — list with optional ?search= param
// Fixtures: 3 customers (2 residential, 1 commercial)
// CustomerResponse shape: { id, tenant_id, type, display_name, first_name, last_name, company_name, email }

// GET /api/v1/customers/:customerId — single customer detail
// Use the first fixture customer's ID

// GET /api/v1/sites/ — with ?customer_id= filter
// Return 2 sites for the first customer's ID
// SiteResponse shape: { id, tenant_id, customer_id, name, notes, jurisdiction_code, is_active, address: {} }
// For address, use the shape confirmed from openapi.json pre-work
```

Register in `mocks/handlers/index.ts`:
```typescript
import { customersHandlers } from "./customersHandlers";
// Add comment: // MOB-B3: Customers list + detail + sites
// Add to handlers array: ...customersHandlers
```

---

## Step 2: Create `useCustomers` Hook

**File**: `frontend/apps/mobile/features/customers/hooks/useCustomers.ts`

Design doc §F.1. Key implementation points:

```typescript
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client"; // verify import path

export interface CustomerListItem {
  id: string;
  tenant_id: string;
  type: string;
  display_name: string;
  first_name: string | null;
  last_name: string | null;
  company_name: string | null;
  email: string | null;
}

export function useCustomers(searchQuery: string = "") {
  return useQuery({
    queryKey: ["customers", searchQuery],
    queryFn: async () => {
      const params: Record<string, unknown> = { limit: 50 };
      if (searchQuery.trim()) params.search = searchQuery.trim();
      const { data } = await apiClient.get<CustomerListItem[]>("/api/v1/customers/", { params });
      return data;
    },
    staleTime: 60_000,
  });
}
```

> **Note**: Debounce is handled in `CustomersTabScreen` — this hook receives the already-debounced query string.

---

## Step 3: Create `useCustomerDetail` Hook

**File**: `frontend/apps/mobile/features/customers/hooks/useCustomerDetail.ts`

```typescript
export function useCustomerDetail(customerId: string) {
  return useQuery({
    queryKey: ["customer-detail", customerId],
    queryFn: async () => {
      const { data } = await apiClient.get<CustomerListItem>(`/api/v1/customers/${customerId}`);
      return data;
    },
    staleTime: 60_000,
  });
}
```

---

## Step 4: Create `useCustomerSites` Hook

**File**: `frontend/apps/mobile/features/customers/hooks/useCustomerSites.ts`

**Before implementing**: Verify the `address` shape from `openapi.json` (pre-work step above). Define the correct `CustomerSite.address` type.

```typescript
export interface CustomerSite {
  id: string;
  tenant_id: string;
  customer_id: string;
  name: string | null;
  notes: string | null;
  jurisdiction_code: string | null;
  is_active: boolean;
  address: Record<string, unknown>; // replace with actual shape from openapi.json
}

export function useCustomerSites(customerId: string) {
  return useQuery({
    queryKey: ["customer-sites", customerId],
    queryFn: async () => {
      const { data } = await apiClient.get<CustomerSite[]>("/api/v1/sites/", {
        params: { customer_id: customerId, limit: 20 },
      });
      return data;
    },
    staleTime: 60_000,
  });
}
```

---

## Step 5: Create `CustomerListItem` Component

**File**: `frontend/apps/mobile/features/customers/components/CustomerListItem.tsx`

Design doc §F.4. Key implementation points:

```typescript
interface CustomerListItemProps {
  customer: CustomerListItemData;  // use CustomerListItem type from useCustomers.ts
  onPress: (customerId: string) => void;
  testID?: string;
}
```

**Type badge**:
```typescript
// Hardcoded — no enum endpoint
const TYPE_BADGE: Record<string, { label: string; colorStyle: "brand" | "neutral" }> = {
  residential: { label: "Residential", colorStyle: "neutral" },
  commercial: { label: "Commercial", colorStyle: "brand" },
};
// Fallback for unexpected type: show type string with neutral badge
```

**Touch target**: `minHeight: 44` on the pressable wrapper (use `style-constants.ts` value).

---

## Step 6: Create `CustomersTabScreen` Component

**File**: `frontend/apps/mobile/features/customers/components/CustomersTabScreen.tsx`

Design doc §F.5. Key implementation points:

### Debounced search:
```typescript
const [searchInput, setSearchInput] = useState("");
const [debouncedSearch, setDebouncedSearch] = useState("");

useEffect(() => {
  const t = setTimeout(() => setDebouncedSearch(searchInput), 300);
  return () => clearTimeout(t);
}, [searchInput]);

const { data: customers, isLoading, isError, refetch, isFetching } = useCustomers(debouncedSearch);
```

### Navigation to detail:
```typescript
import { router } from "expo-router";

// On customer card press:
router.push(`/(tabs)/customers/${customer.id}` as any);
```

### Empty states:
- **No customers (no search)**: "No customers found"
- **No results for search**: `"No customers match '${searchInput}'"`
- Use `ListEmptyComponent` on `FlatList`

### First 50 note:
```typescript
{customers && customers.length >= 50 && (
  <Text style={styles.limitNote}>
    Showing first 50 customers — search to narrow results
  </Text>
)}
```

---

## Step 7: Create `CustomerDetailScreen` Component

**File**: `frontend/apps/mobile/features/customers/components/CustomerDetailScreen.tsx`

Design doc §F.6. Key implementation points:

### Address formatting (verify shape first):
```typescript
function formatSiteAddress(address: Record<string, unknown>): string {
  // After reading openapi.json, implement with actual field names
  // Fallback if fields not present:
  const line1 = address?.line1 as string | undefined;
  const city = address?.city as string | undefined;
  const state = address?.state as string | undefined;
  if (line1 && city && state) return `${line1}, ${city}, ${state}`;
  // TODO: address rendering when exact shape confirmed
  return "";
}
```

### Message Customer navigation:
```typescript
router.push(`/(tabs)/customers/${customerId}/comms` as any);
// This navigates to the existing customers/[id]/comms.tsx route
```

### Phone placeholder:
```typescript
{/* TODO: mobile_phone not in CustomerResponse — request backend addition if needed */}
<View style={styles.contactRow}>
  <Text style={styles.contactLabel}>📞</Text>
  <Text style={styles.contactValue}>(no phone on record)</Text>
</View>
```

---

## Step 8: Replace `customers.tsx` Stub

**File**: `frontend/apps/mobile/app/(tabs)/customers.tsx`

Read the file first (confirm it is still the 10-line stub), then replace entirely:

```typescript
import { CustomersTabScreen } from "@/features/customers/components/CustomersTabScreen";

export default function CustomersTab() {
  return <CustomersTabScreen />;
}
```

> **Import path**: Use `@/` alias — verify it resolves correctly in `tsconfig.json` for mobile (same alias used in MOB-B1 for `jobs.tsx`).

---

## Step 9: Create `customers/[id]/index.tsx` Route

**File**: `frontend/apps/mobile/app/(tabs)/customers/[id]/index.tsx`

```typescript
import { useLocalSearchParams } from "expo-router";
import { CustomerDetailScreen } from "@/features/customers/components/CustomerDetailScreen";

export default function CustomerDetailRoute() {
  const { id: customerId } = useLocalSearchParams<{ id: string }>();
  return <CustomerDetailScreen customerId={customerId} />;
}
```

> **Note**: The dynamic segment is `[id]` (not `[customerId]`) — confirmed from the existing `comms.tsx` in the same folder which uses `useLocalSearchParams<{ id: string }>()`.

---

## Step 10: Update `(tabs)/_layout.tsx`

Read the file first. Add the customer detail screen suppression alongside the existing `customers/[id]/comms` suppression:

```typescript
{/* MOB-B3: Customer detail screen — suppress from tab bar */}
<Tabs.Screen name="customers/[id]/index" options={{ href: null }} />
```

> **Pattern reference**: Follows the same pattern as `<Tabs.Screen name="customers/[id]/comms" options={{ href: null }} />` already in the file. Place immediately after or before it.

---

## Tests

### Unit Tests (co-located in `features/customers/*/__tests__/`)

**`useCustomers.test.ts`**:
- Calls `GET /api/v1/customers/?limit=50` with no search query
- Calls `GET /api/v1/customers/?search=acme&limit=50` with `searchQuery="acme"`
- Does NOT include `search` param when `searchQuery` is empty string

**`useCustomerDetail.test.ts`**:
- Calls `GET /api/v1/customers/{id}` with correct ID
- Returns customer data on success

**`useCustomerSites.test.ts`**:
- Calls `GET /api/v1/sites/?customer_id={id}&limit=20`
- Returns array of sites

**`CustomerListItem.test.tsx`**:
- Renders `display_name`
- `type="residential"` → "Residential" badge
- `type="commercial"` → "Commercial" badge
- Renders `email` when present; no crash when `email=null`
- Calls `onPress(id)` on tap

**`useCustomerThreads.test.ts`** (update existing if present, create if not):
- Calls `apiClient.get("/api/v1/mobile/inbox/customer-threads")` — not raw `fetch()`

### Integration Tests (`__tests__/batch_mob_b3/`)

**`customers-tab.integration.test.tsx`**:
- MSW returns 3 customers → 3 `CustomerListItem` cards visible
- MSW returns `[]` → empty state copy visible
- Before MSW responds → loading `ActivityIndicator` present
- MSW returns 500 → error state + "Try again" visible
- Type in search bar → after 300ms debounce → MSW called with `?search=<query>`
- MSW returns `[]` for search → search-empty copy shown
- Simulate pull-to-refresh → `refetch` called
- Press customer card → `router.push` called with `customers/${id}`

**`customer-detail.integration.test.tsx`**:
- MSW returns customer fixture → `display_name` visible in header
- MSW returns 2 sites → 2 site rows visible in sites section
- "Message Customer" press → `router.push` called with `customers/${id}/comms`
- MSW returns 500 for customer → error state visible

### Regression Tests

- Existing inbox tests pass after `useCustomerThreads` migration (`communicationsHandlers` MSW still covers the endpoint)
- `(tabs)/_layout.tsx` still suppresses `customers/[id]/comms` and all other suppressed routes after modification
- `customers/[id]/comms.tsx` route still renders correctly (no imports changed)
- MOB-B1 and MOB-B2 handler tests unaffected by adding `customersHandlers`

---

## Final Verification

```bash
cd <repo>/frontend
pnpm --filter mobile check-types && \
pnpm --filter mobile lint && \
echo "=== TYPE+LINT PASS ===" && \
pnpm --filter mobile test 2>&1 | tail -10 && \
echo "=== MOB-B3 FINAL VERIFICATION COMPLETE ==="
```

---

## Definition of Done — MOB-B3

Update `pilot-app-beta-fixes-v2-impl-plan.md` §9 Batch Completion Tracker:

- [ ] Pre-modification regression baseline captured (exact mobile test count)
- [ ] All source files read before modification (`customers.tsx`, `_layout.tsx`, `useCustomerThreads.ts`, `comms.tsx`, `handlers/index.ts`)
- [ ] `apiClient` import path for mobile confirmed from `useReplyToThread.ts`
- [ ] `GET /api/v1/customers/` params verified from `openapi_schema_map.md` — `?search=`, `skip`, `limit` confirmed
- [ ] `GET /api/v1/customers/{id}` response confirmed — no `mobile_phone` (documented §G.1)
- [ ] `GET /api/v1/sites/?customer_id=` confirmed; `address` object shape read from `openapi.json`
- [ ] `useCustomerThreads.ts` migrated from raw `fetch()` to `apiClient` — no raw fetch remaining
- [ ] Existing inbox MSW handler verified — no new handler needed for threads endpoint
- [ ] `customersHandlers.ts` MSW handler created with: 3 customer fixtures + 2 site fixtures
- [ ] `customersHandlers.ts` registered in `mocks/handlers/index.ts`
- [ ] `useCustomers` hook: calls correct endpoint with/without search; no `?search=` when empty
- [ ] `useCustomerDetail` hook: calls `GET /api/v1/customers/{id}`
- [ ] `useCustomerSites` hook: calls `GET /api/v1/sites/?customer_id=`
- [ ] `CustomerListItem`: renders name, type badge (residential/commercial), email; 44pt touch target
- [ ] `CustomersTabScreen`: search bar with 300ms debounce; FlatList; all 3 states (loading/error/empty)
- [ ] `CustomersTabScreen`: 50-customer limit note shown when result count ≥ 50
- [ ] `CustomerDetailScreen`: name + type badge + email + phone placeholder + sites list + "Message Customer"
- [ ] `CustomerDetailScreen`: site `address` formatted correctly (verified from `openapi.json` shape)
- [ ] `CustomerDetailScreen`: "Message Customer" navigates to `customers/${id}/comms`
- [ ] `customers.tsx` stub replaced — no longer shows centered "Customers" text
- [ ] `customers/[id]/index.tsx` route created — renders `<CustomerDetailScreen customerId={id} />`
- [ ] `(tabs)/_layout.tsx` updated — `customers/[id]/index` suppressed from tab bar
- [ ] Unit tests pass (all per §J.1 in design doc)
- [ ] Integration tests pass (all per §J.2 in design doc)
- [ ] Regression tests pass — inbox/comms tests unaffected; layout suppressions intact
- [ ] Zero TypeScript errors (`pnpm --filter mobile check-types`)
- [ ] Zero ESLint warnings
- [ ] No regressions in pre-existing mobile test suite
- [ ] Full verification command passes (`=== MOB-B3 FINAL VERIFICATION COMPLETE ===`)
- [ ] Final test count (before → after) documented in impl plan tracker
- [ ] Summary of work accomplished added to impl plan §9 as new sub-section after MOB-B3 row
