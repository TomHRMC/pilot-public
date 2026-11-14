# ⚛️ Pilot React Engineer — Hard Rules

> **Design-time agent rule** — written to steer the AI agents during the build and published as last used. Where it differs from the as-built system, [`PROVENANCE.md`](../../PROVENANCE.md) and [`dev-docs/diligence/`](../../dev-docs/diligence/README.md) are correct.

These are non-negotiable constraints. Every rule here was added because violating it caused real rework — wrong endpoint URLs, wrong parameter names, auth failures, broken API calls — in prior development sessions. They are **not** guidelines. They are **stops**.

---

## 1. API Contracts — Verify Before Writing Any Hook

### 1.1 Check `openapi_schema_map.md` FIRST

Before writing ANY TanStack Query hook, Axios call, or MSW handler:

1. **Read [`backend/openapi_schema_map.md`](../../backend/openapi_schema_map.md)** — the human/agent-readable summary of every endpoint with exact paths, required parameters, and response shapes. This is the fast lookup.
2. **If more detail is needed, read [`backend/openapi.json`](../../backend/openapi.json)** — the full machine-readable spec.
3. **If the endpoint is NOT in either file, it does not exist.** Do NOT invent a URL. Do NOT assume it will be added. Stop and ask Tom.

```bash
# Quick endpoint verification from the backend directory:
python3 -c "
import json
spec = json.load(open('openapi.json'))
matches = [p for p in spec['paths'] if 'YOUR_KEYWORD' in p]
print(matches)
"
```

### 1.2 Never Invent Endpoint Shapes

- Do NOT assume parameter names from the surface name or context (e.g., do NOT assume `/reports/profitability` accepts `?period=7d` — check `openapi_schema_map.md`)
- Do NOT infer URL patterns from other endpoints (e.g., do NOT assume `/schedule/board` because `/schedule` exists — the real path is `/scheduling/dispatch-board`)
- Do NOT ship a hand-written TypeScript interface as a permanent type for a backend payload

### 1.3 Use `pnpm sync-api-types` for TypeScript Types

Run after every backend deploy to regenerate `packages/shared-types/src/api-schema.d.ts`:

```bash
pnpm sync-api-types
```

Then import types from `@pilot/shared-types`:

```typescript
import type { components } from '@pilot/shared-types';
type QuoteResponse = components['schemas']['QuoteResponse'];
```

If a needed type is missing because the backend endpoint is still in flight, write a **stub interface** clearly marked `// TODO: delete when pnpm sync-api-types delivers this type`. Never ship a stub as permanent.

---

## 2. API Client — Always Use `apiClient`, Never Raw `fetch()`

**`fetch()` is permanently banned for any `/api/v1/...` call.**

```typescript
// ❌ BANNED — hits Next.js port 3000 not FastAPI; no JWT; no error handling
const res = await fetch('/api/v1/reports/profitability');
const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/reports/profitability`);

// ✅ REQUIRED — correct baseURL, JWT interceptor, 401 refresh, RFC 7807 error parsing
import { apiClient } from '@pilot/shared-api';
const { data } = await apiClient.get('/api/v1/reports/profitability', { params: { date_from, date_to } });
```

> **Import path is `@pilot/shared-api` — NOT `@/lib/api-client`.** Every one of the ~126 web hooks imports `import { apiClient } from "@pilot/shared-api";`. `@/lib/` in `apps/web` contains only `amplify-config.ts` — there is no `api-client` module there. Related exports also live in the same package: `isAxiosError`, `LIST_PAGE_SIZE`, and the shared `queryClient`.

`apiClient` is the single Axios instance from `packages/shared-api`. It:
- Has the correct `baseURL` pointing to FastAPI
- Attaches the Cognito JWT via interceptor
- Catches 401s and refreshes silently
- Parses RFC 7807 error responses

There is no legitimate reason to use raw `fetch()` for any API call to the backend.

---

## 3. SSE Endpoints — Always Append `?token=JWT`

Browser `EventSource` cannot send `Authorization` headers. All backend SSE endpoints require `?token=JWT` as a query parameter.

```typescript
// ❌ WRONG — EventSource ignores Authorization headers
new EventSource('/api/v1/scheduling/board/stream');

// ✅ CORRECT — fetch JWT first, append as query param
const jwt = await getAmplifyJwt();
new EventSource(`/api/v1/scheduling/board/stream?token=${jwt}`);
```

When using `useSseChannel()`, pass the `getToken` prop:

```typescript
useSseChannel('/api/v1/scheduling/board/stream', {
  getToken: () => getAmplifyJwt(),
  onMessage: (event) => { ... },
});
```

---

## 4. Authorization — Role Comes From the DB, Not the JWT

Cognito is **identity only**. Never read `custom:role` or `custom:tenant_id` from the JWT payload for authorization decisions.

After Cognito auth succeeds, call `GET /api/v1/users/me/permissions` to get the user's role and tenant from the local DB. The `AuthProvider` handles this — do not bypass it.

```typescript
// ❌ BANNED — Cognito JWT may be stale if DB role changed
const role = user.attributes['custom:role'];

// ✅ CORRECT — role from DB via /api/v1/users/me/permissions
const { role, tenantId } = useAuth();
```

---

## 5. Design Tokens — Never Hardcode Visual Values

All colors, font sizes, spacing values, and border radii must come from Pass 1 tokens in `packages/ui/src/tokens.ts`. The ESLint rule `no-hardcoded-design-values` is configured as an **error** (not warning) — any violation fails CI.

```tsx
// ❌ BANNED — ESLint error
<div style={{ backgroundColor: '#3B43D6', padding: 13 }}>

// ✅ REQUIRED — token-driven Tailwind utilities
<div className="bg-brand-600 p-3">
```

---

## 6. RBAC — Hide-Not-Disable

Unauthorized UI elements are **hidden**, not disabled or greyed out. There is no "you don't have permission" affordance in MVP. Use `<RoleGate>` from `@pilot/ui/role-gate`:

```tsx
// ❌ WRONG — disabled button is still visible
<button disabled={!canApprove}>Approve</button>

// ✅ CORRECT — element does not exist in the DOM for unauthorized users
<RoleGate permission="quotes.approve">
  <ApproveButton />
</RoleGate>
```

### 6.1 Permission-Only Gating — NEVER Role (Tom, 2026-09-06)

**All UI components, nav items, and affordances gate on a PERMISSION key — never on a role.** `role={...}` gating is banned for UI. This is a hard rule for every engineer (Tom, verbatim: "we have to use ONLY permission for all UI components, NEVER a ROLE at all").

```tsx
// ❌ BANNED — role-list gating (the INV-BUG-13 defect class: a role list drifts
// from the actual grants and hides surfaces from roles that legitimately hold the permission)
<RoleGate role={["owner", "accountant"]}>…</RoleGate>
if (user.role === "accountant") return null;

// ✅ REQUIRED — permission key, server-authoritative (post-FIX-7 the array comes
// from GET /users/me/permissions; the static ROLE_PERMISSION_MAP is mock-fallback only)
<RoleGate permission="schedule.view_all">…</RoleGate>
const canView = useHasPermission("schedule.view_all");
```

- Gate **read** surfaces on the read key (`schedule.view_all`), **write** affordances on the write key (`schedule.manage`) — never one key for both.
- **Single documented exception**: login *routing* (the technician web-block in `usePostLoginRedirect.ts` per ADR-0010/TEAM-INVITE-2) is a role-based routing guard, not a UI-component gate. Any new role-based routing requires Tom's explicit approval.
- Legacy `role={` props found in the wild are converted on sight (the FIX-9/FIX-10 sweep idiom) — a spec or PR that adds a NEW role-gated UI element is a review failure.

---

## 7. Shared Components — Import, Never Reimpliment

If a shared component exists in `packages/ui/`, **import it**. Never copy-paste or rewrite it in a feature folder.

Before creating any new component, check the **authoritative barrel** [`packages/ui/src/index.ts`](../../frontend/packages/ui/src/index.ts) — it is the single source of truth for what is exported and importable. The narrative catalog in [`pilot-react-engineer-methods.md`](../../dev-docs/architecture-design/pilot-react-engineer-methods.md) §8 explains *when* to use each, but `index.ts` is authoritative for *what exists*. If a component is exported from the barrel, it is the canonical implementation — import it.

If the existing component does not cover your use case, **extend it** with a new optional prop or `variant` — never fork it.

---

## 8. Bulk File Migrations — Always Verify With Prettier After

Any automated bulk migration (e.g., `fetch()` → `apiClient` via regex or script) leaves orphaned syntax artifacts (stray `;`, double `;;`, orphaned `catch` blocks) that pass a grep check but fail TypeScript parsing.

After any bulk migration, immediately run:
```bash
cd frontend && npx prettier --check "apps/web/src/features/**/*.ts"
cd frontend && npx prettier --check "apps/web/src/features/**/*.tsx"
```

Fix all Prettier failures before committing. Do not assume the migration was clean without this check.

---

## 9. Database Entity Context — Use `db_models_map.md`

When building a new surface and unsure what backend entities drive the API:

1. Check **[`backend/db_models_map.md`](../../backend/db_models_map.md)** — it shows which classes are real DB tables (`DB Tables` section) vs Python enums/schemas (`Enums / Schemas / Helpers` section).
2. Only `DB Tables` entries map to queryable API resources. Do NOT assume an enum class like `InvoiceStatus` has its own endpoint.
3. The `db_models_map.md` file is regenerated by the Python Engineer after any model change. If it looks stale, ask Tom to regenerate it.

---

## 10. Definition of Done — API Verification Step Is Non-Negotiable

Every batch or surface task is **not complete** until:

- [ ] Every API endpoint consumed by the surface was verified in `openapi_schema_map.md` or `openapi.json` **before** the hook was written (not after)
- [ ] `pnpm sync-api-types` was run and types match the actual backend response shapes
- [ ] No `fetch('/api/v1/...')` calls exist in the added/modified files
- [ ] All SSE connections append `?token=JWT` via `useSseChannel` `getToken` prop
- [ ] ESLint `no-hardcoded-design-values` passes with zero warnings on all new files
- [ ] axe-core returns zero violations on all new surfaces
- [ ] The full canonical verification command passes with `=== MVP FINAL VERIFICATION COMPLETE ===`:
  ```bash
  cd <repo>/frontend && echo "=== UI - Type Check ===" && pnpm --filter @pilot/ui check-types && echo "=== Web - Type Check ===" && pnpm --filter web check-types && echo "=== Mobile - Type Check ===" && pnpm --filter mobile build && echo "=== UI - Lint ===" && pnpm --filter @pilot/ui lint && echo "=== Web - Lint ===" && pnpm --filter web lint && echo "=== Mobile - Lint ===" && pnpm --filter mobile lint && echo "=== TYPE+LINT PASS ===" && echo "=== UI - Tests ===" && pnpm --filter @pilot/ui test 2>&1 | tail -6 && echo "=== Web - Tests ===" && pnpm --filter web test 2>&1 | tail -6 && echo "=== Mobile - Tests ===" && pnpm --filter mobile test 2>&1 | tail -8 && echo "=== MVP FINAL VERIFICATION COMPLETE ==="
  ```

---

## 11. Test Failures — Fix Every Failure You Encounter

If ANY test fails during your work — including tests that appear pre-existing or caused by a previous batch — **you must fix it before declaring the task done**. There is no "not my fault" exception.

- If you cannot identify the root cause → **STOP and ask Tom** before proceeding.
- You may NOT mark a task complete while any test is failing without explicit written confirmation from Tom that the failure is known and accepted.

---

## 12. Test Execution — Targeted Tests During Development, Full Canonical Command at the End

During implementation, run only the package(s) you are touching — fast feedback:

```bash
cd <repo>/frontend
pnpm --filter @pilot/ui test 2>&1 | tail -6    # if touching packages/ui
pnpm --filter web test 2>&1 | tail -6          # if touching apps/web
pnpm --filter mobile test 2>&1 | tail -8       # if touching apps/mobile
```

Run the full canonical command (Rule 10 above) **exactly once** at the very end before declaring done. Never run it repeatedly during development — it is slow and only relevant at the final gate.

---

## 13. MSW Handlers — Always Register New Handler Files in `index.ts`

When creating a new MSW handler file, it MUST be imported and spread into the barrel `index.ts` for its app. A handler file that is not registered is never loaded — tests fall through to unhandled request warnings.

```typescript
// apps/web/src/mocks/handlers/index.ts  (or apps/mobile/mocks/handlers/index.ts)
import { myFeatureHandlers } from "./myFeatureHandlers";   // ← new import

export const handlers = [
  ...existingHandlers,
  ...myFeatureHandlers,   // ← REQUIRED — without this, the handler never fires
];
```

---

## 14. TanStack Query in Tests — Always `retry: false`

Never use a default `QueryClient` in tests. Default retry=3 causes test timeouts when APIs return errors.

```typescript
// ❌ WRONG — default retry=3, test hangs for 3 seconds per failed query
const queryClient = new QueryClient();

// ✅ REQUIRED — fail fast
const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: false },
    mutations: { retry: false },
  },
});
```

Create a fresh `QueryClient` per test — never share one across tests.

---

## 15. Test Data Isolation — Never Mutate Shared Mock Data or Assert on Totals

Frontend tests run against MSW mock handlers. Every test — whether creating new tests or modifying existing ones — MUST be resilient to the shared mock environment.

**These rules apply when writing OR modifying any test:**

- **Never mutate shared module-level fixture objects.** Fixtures defined at module level (e.g., `const mockCustomers = [...]`) are shared state. If a test needs a modified version, create a copy: `const modified = { ...mockCustomers[0], status: 'overdue' }`. Mutating the original causes other tests to see unexpected data.
- **Never assert on a total count from an API response** unless the MSW handler for that test is explicitly set up to return exactly that count. The global MSW handler may return a fixture list that changes over time. Always assert by specific ID or content:
  ```typescript
  // ❌ WRONG — breaks if fixture list ever changes length
  expect(screen.getAllByRole("row")).toHaveLength(3);

  // ✅ CORRECT — resilient to fixture changes
  expect(screen.getByText(mockCustomers[0].display_name)).toBeInTheDocument();
  ```
- **Use per-test MSW overrides for specific states** (error, empty, edge case). Never rely on the global handler for test-specific behavior:
  ```typescript
  it("shows error state", () => {
    server.use(
      http.get("/api/v1/customers", () =>
        HttpResponse.json({ error: "server error" }, { status: 500 }),
      ),
    );
    // ... render and assert error state
  });
  // server.resetHandlers() in afterEach restores the global handler
  ```
- **Always call `server.resetHandlers()` in `afterEach`** when using `server.use(...)` per-test overrides. Without this, the override bleeds into subsequent tests.
- **Integration tests must use MSW** — never write a frontend integration test that hits a real backend API endpoint. `NEXT_PUBLIC_USE_MOCK_AUTH=true` is the default test environment for this reason.

---

## 16. Mobile Type Check — `pnpm --filter mobile build`, Not `check-types`

The `apps/mobile` package has no `check-types` script. The mobile type check is:

```bash
pnpm --filter mobile build   # runs tsc --noEmit
```

`pnpm --filter mobile check-types` will fail with "script not found". Always use `build` for mobile TypeScript validation.

---

## 16b. Mobile Tests — Mock Expo Router and WatermelonDB

**Every mobile screen test** that uses navigation MUST mock Expo Router:

```typescript
const mockPush = jest.fn();
jest.mock("expo-router", () => ({
  useRouter: () => ({ push: mockPush, back: jest.fn(), replace: jest.fn() }),
  useLocalSearchParams: () => ({}),
  router: { push: mockPush, back: jest.fn() },
  Link: ({ children }: { children: React.ReactNode }) => children,
}));
beforeEach(() => { mockPush.mockClear(); });
```

**Every mobile test** involving WatermelonDB MUST mock the database module (real DB writes are banned in tests):

```typescript
jest.mock("../../../database", () => ({
  database: {
    write: jest.fn((fn) => fn()),
    get: jest.fn(() => ({
      create: jest.fn((fn) => {
        const record = { id: "mock-id", localSyncStatus: "pending" };
        fn(record);
        return Promise.resolve(record);
      }),
    })),
  },
}));
```

---

## 17. Web vs Mobile Test Assertions — Never Mix Them

| Concern | Web (Vitest + jsdom) | Mobile (Jest + react-native) |
|---|---|---|
| Mock API | `vi.mock()` | `jest.mock()` |
| Element found | `toBeInTheDocument()` | `.toBeTruthy()` or `.not.toBeNull()` |
| User interaction | `userEvent.click()` | `fireEvent.press()` |
| Navigation mock | `vi.mock("next/navigation", ...)` | `jest.mock("expo-router", ...)` |

`toBeInTheDocument()` is jsdom-only — it throws in a React Native test environment. `.toBeTruthy()` works in mobile but is weaker — prefer `toBeInTheDocument()` for web.

---

## 18. Mobile MSW Handlers — Always Use `*/api/v1/...` Wildcard

`apiClient.baseURL` in the mobile app is an absolute URL (LAN IP like `http://192.168.1.50:8000`). When the MSW browser worker runs at `localhost:8081`, relative-path handlers **silently miss** every request.

```typescript
// ❌ BANNED in apps/mobile/mocks/handlers/ — silently misses all apiClient requests
http.get("/api/v1/jobs/", handler)
http.post("/api/v1/customers/", handler)

// ✅ REQUIRED — matches requests to any origin including the LAN IP
http.get("*/api/v1/jobs/", handler)
http.post("*/api/v1/customers/", handler)
```

The web app (`apps/web`) can use relative paths because its `apiClient.baseURL` points to `localhost:8000` (same origin). Mobile cannot. Every handler in `apps/mobile/mocks/handlers/` must use the wildcard prefix.

---

## 19. Mobile `fontWeight` — Always Cast Token to String Literal

`fontWeights.medium` and `fontWeights.regular` from `@pilot/ui/tokens` are **numbers** (500, 400). React Native's `TextStyle.fontWeight` requires a **string literal**. Without the cast, TypeScript errors and the style is silently dropped at runtime.

```typescript
// ❌ TypeScript error on mobile — number not assignable to "100"|...|"bold"
fontWeight: fontWeights.medium

// ✅ REQUIRED
fontWeight: String(fontWeights.medium) as "500"
fontWeight: String(fontWeights.regular) as "400"
```

Only these two values exist in the token system. Never hardcode `"bold"`, `"600"`, `"700"`, or `"900"`.

---

## 20. Mobile Token Imports — Always Use Package Alias, Never Relative Paths

```typescript
// ❌ BANNED — breaks when any parent directory is renamed or file moves depth
import { colors } from "../../../../../packages/ui/src/tokens";

// ✅ REQUIRED
import { colors, mobileFontSizes, mobileLineHeights, fontWeights, spacing, radii } from "@pilot/ui/tokens";
```

---

## 21. Mobile `EXPO_PUBLIC_USE_MOCK_AUTH` — Always Guard with `Platform.OS === 'web'`

This flag is intended ONLY for the mobile web view (`localhost:8081`). Without the platform guard, native builds (Expo Go / device) skip real Cognito and disable all API calls.

```typescript
// ❌ BANNED — disables all API calls on native
const isMockAuth = process.env.EXPO_PUBLIC_USE_MOCK_AUTH === "true";

// ✅ REQUIRED — web-only guard
const isMockAuth = Platform.OS === "web" && process.env.EXPO_PUBLIC_USE_MOCK_AUTH === "true";
```

Every hook with `enabled: !isMockAuth` must apply this same guard.

---

## 22. Mobile Env Vars — `EXPO_PUBLIC_` Prefix Is Mandatory

Metro only injects `EXPO_PUBLIC_*` variables. `NEXT_PUBLIC_*` are silently `undefined` in the Expo bundle — no error, no warning. If `Amplify.configure()` receives undefined pool IDs, it silently does nothing → all auth calls fail.

```bash
# ❌ BANNED — silently undefined in Metro
NEXT_PUBLIC_COGNITO_USER_POOL_ID=...

# ✅ REQUIRED
EXPO_PUBLIC_COGNITO_USER_POOL_ID=...
```

---

## 23. Amplify Must Be the First Import — AsyncStorage Is Required on Native

`lib/amplify-config.ts` must be imported before any `aws-amplify/auth` lazy imports. `react-native-get-random-values` must come before `amplify-config`. In `app/_layout.tsx`:

```typescript
// MUST be the first two imports — order is locked
import "react-native-get-random-values";
import "../lib/amplify-config";
```

Without `AsyncStorage` as Amplify's storage backend, tokens are JS-memory-only. `fetchAuthSession()` returns empty tokens on the next async tick → **401 on every post-login API call**.

Use `USER_PASSWORD_AUTH` on React Native — `USER_SRP_AUTH` requires a native module that Expo Go cannot link.

---

## 24. Backend Cognito Pool Must Match Frontend — Always Update Both `.env` Files

When provisioning a new Cognito pool or migrating regions, update **both** files. A mismatch causes 401 on all authenticated endpoints even when the JWT is valid:

| File | Key to update |
|---|---|
| `apps/mobile/.env` | `EXPO_PUBLIC_COGNITO_USER_POOL_ID`, `EXPO_PUBLIC_COGNITO_REGION` |
| `backend/.env` | `COGNITO_USER_POOL_ID`, `COGNITO_REGION` |

Also update the comment in `lib/amplify-config.ts` — it is the canonical reference for which pool is active.

---

## 25. Metro Bundle: Exclude Test Files and Native Packages

Metro walks ALL reachable files. These are non-negotiable metro.config.js rules:

1. **`exclusionList`** must include `__tests__/`, `mocks/server.ts`, `*.test.*`, `*.spec.*` — prevents MSW `setupServer()` from entering the native bundle
2. **`NATIVE_ONLY_PACKAGES`** must return `{ type: 'empty' }` on web for: `expo-location`, `expo-haptics`, `expo-image-picker`, `expo-file-system`, `expo-sharing`, `expo-av`, `better-sqlite3`, `@nozbe/watermelondb/adapters/sqlite/sqlite-node`
3. **`SINGLETON_PACKAGES`** must include `@tanstack/react-query` and `react-native-svg` — pnpm symlinks can create duplicate instances causing `"No QueryClient set"` and `"Tried to register two views with the same name"` crashes

---

## 26. Expo Router — Never Combine `jobs.tsx` Tab File with `jobs/_layout.tsx`

Having both `jobs.tsx` (tab-level file) and `jobs/_layout.tsx` in the same directory creates two conflicting `"jobs"` routes in the Tabs navigator → crash: `"A navigator cannot contain multiple Screen components with the same name"`.

Use `href: null` suppression in `(tabs)/_layout.tsx` for sub-routes instead of adding nested layouts that conflict with tab files.

---

## 27. WatermelonDB — Use LokiJS Adapter for All Dev Builds and Web

`WMDatabaseBridge` (SQLite adapter) requires native pod linking. It cannot be used in Expo Go or on web. A static top-level `import SQLiteAdapter` crashes the web build by pulling in `better-sqlite3`.

```typescript
// ✅ REQUIRED — conditional adapter with require() inside branch (never static import)
if (Platform.OS === "web" || __DEV__) {
  const { default: LokiJSAdapter } = require("@nozbe/watermelondb/adapters/lokijs");
  adapter = new LokiJSAdapter({ schema, useWebWorker: false, useIncrementalIndexedDB: true });
} else {
  const { default: SQLiteAdapter } = require("@nozbe/watermelondb/adapters/sqlite");
  adapter = new SQLiteAdapter({ schema, dbName: "pilot" });
}
```

---

## 28. WatermelonDB Babel — Never Add `@babel/plugin-transform-class-properties` Explicitly

`babel-preset-expo@54.0.10+` already includes this plugin. Adding it explicitly causes it to run twice, corrupting React Native's frozen static constants → `TypeError: Cannot assign to read-only property 'NONE'`.

Use `@babel/plugin-proposal-decorators` (legacy mode) with `assumptions` in `babel.config.js` instead — see [`pilot-react-engineer-methods.md` §11.5](../../dev-docs/architecture-design/pilot-react-engineer-methods.md).

---

## 29. `__DEV__` Is React Native Only — Never Use in Shared Packages

`__DEV__` is a Metro/React Native global. It is **undefined** in `packages/shared-api/` and `packages/ui/` when consumed by web. Use `process.env.NODE_ENV !== 'production'` for cross-platform dev-only logging.

```typescript
// ❌ BANNED in packages/shared-api/, packages/ui/
if (__DEV__) { console.log("..."); }

// ✅ CORRECT for shared packages
if (process.env.NODE_ENV !== "production") { console.log("..."); }

// ✅ CORRECT for apps/mobile only
if (__DEV__) { console.log("..."); }
```

---

## 30. Subscription & Pricing — Master Reference (MANDATORY — never deviate)

> **Added 2026-08-30** (Tom mandate, after PLP-FIX-1: a phantom `quotes_per_month` gate 402'd ALL quote creation because it contradicted the pricing model). Everyone touching plans, prices, limits, entitlements, usage quotas, upgrade prompts, or billing surfaces must know and follow this section.

**Master definition (product truth)**: [`dev-docs/product-requirements/mvp-prd.md`](../../dev-docs/product-requirements/mvp-prd.md) **§3.11 "Subscriptions & Usage" → Pricing Table + feature rows** — the ONLY authoritative definition of Pilot's subscription plans, prices, included allowances, limits, enforcement modes, and overage rates.

**Runtime mapping (implementation truth)**: `dev-docs/pilot-operations.md` _(private)_ §2 (Product Plan Hierarchy) · §3 (Subscription Tier Model) · §5 (Founders/Charter Cohort Model) · §6 (Per-Tenant Overrides). Charter mechanics: GTM v3 §6 + locked decisions D16/D17. Stripe price IDs: [`dev-docs/integrations/stripe/stripe-pricing-config.md`](../../dev-docs/integrations/stripe/stripe-pricing-config.md) §4.

**Snapshot (2026-08-30)** — *if this ever disagrees with PRD §3.11, **the PRD wins** — flag the drift to Tom; never "fix" it yourself:*

| Plan | Price | Schedule lanes | Voice AI | SMS segs | Enforcement |
|---|---|---|---|---|---|
| **Charter** (12-cap cohort, formerly "Founders") | $0 × 90 days → **$49/mo locked for life** (billed monthly) | 5 | 90 min/mo | 100/mo | no overages in free period; soft after; free period operator-extendable (case by case; not an advertised offer) |
| **Trial** | $0 × 14 days | 5 | 90 | 100 | **block** (hard cap, no card) |
| **Starter** | **$49/mo** annual · $59/mo month-to-month | 5 | 90 | 100 | **soft** — overage: Voice $0.05/min, SMS $0.05/seg |
| **Teams** | **$149/mo** annual · $179/mo month-to-month | 20 | 300 | 500 | **soft** — same overage rates |

Add-ons: +1 lane $10/mo · +5 lanes pack $40/mo · +100 SMS segs per extra Telnyx number at +$5/mo.

**Unlimited on ALL plans — never gate these**: users, jobs, quotes, invoices, customers, QB syncs, emails, calendar syncs.

**Only three gated/metered features exist**: `schedule_lanes` (block), `voice_ai_minutes` (soft + overage), `outbound_sms_segments` (soft + overage). There is intentionally **no** `quotes_per_month`, job, invoice, or user limit.

**Non-negotiables**:

1. **Never invent** plan names, prices, allowances, limits, enforcement modes, or overage rates. Every value must trace to PRD §3.11 (product) and the seeded `product_plan_product_feature_version` rows (runtime).
2. **Phantom-gate rule**: never build an entitlement gate, paywall branch, or upsell gate for a feature the master marks unlimited. A gate requires BOTH a PRD §3.11 pricing line AND seeded `product_feature` + ppfv rows — a wiring without both is a phantom gate (report it; the backend removes it).
3. Pricing/plan/limit UI (upgrade prompts, billing settings, usage widgets, paywalls) renders values from the API or this master — never hardcode a price, limit, or plan name into copy. An upsell or limit message deviating from the master is a defect.
4. If work seems to require a value not in the master → **STOP and ask Tom**. The master changes only via Tom-approved PRD edits (Architect-owned); the Architect refreshes this snapshot in the same change — that is how updates reach every mode automatically.

### 30.1 Runtime behavior the React Engineer must know (from `pilot-operations.md`)

**Subscription status display logic** (from `subscription_status` codes):

| Code | `is_billing_active` | UI Meaning | Display Treatment |
|---|---|---|---|
| `trialing` | `true` | Free trial active | Green / accessible |
| `active` | `true` | Paid and current | Green / accessible |
| `past_due` | `true` | Payment failed, retrying | Warning / accessible |
| `unpaid` | `false` | Retry exhausted | Red / paywall enforced |
| `canceled` | `false` | Explicitly canceled | Red / paywall enforced |
| `paused` | `false` | Subscription paused | Red / paywall enforced |

When `is_billing_active = false`, the API returns `HTTP 402` — the UI must handle this gracefully on any data-fetching hook.

**`invoice_status` — "overdue" is NOT a DB status**: The `invoice_status` table has: `draft`, `issued`, `partial`, `paid`, `void`, `writeoff`. "Overdue" is a **derived display state** computed at render time from: `due_at < TODAY AND status NOT IN ('paid', 'void', 'writeoff')`. **Never send `status=overdue` to the API** — it will return 0 results. Use a separate `?overdue=true` query parameter if the backend supports it, or compute overdue from `due_at` on the client.

**Annual vs. month-to-month pricing display**: The Stripe annual price charges `annual_price_cents` (e.g., 58800 = $588/yr). The marketing display shows this as `$49/mo` — the per-month equivalent. Never display `annual_price_cents / 100` directly as the price — always divide by 12 for the monthly display. Reference: [`dev-docs/integrations/stripe/stripe-pricing-config.md`](../../dev-docs/integrations/stripe/stripe-pricing-config.md) §2.

**Entitlement gates**: When an API returns 402 with `"type": "https://errors.pilotfortrades.com/entitlement-exceeded"`, the UI should show a plan upgrade prompt — not a generic error. The `<NotificationBanner>` severity routing uses the RFC 7807 `type` field to determine display treatment.

## 31. Seed Data Coverage — Know What's in the DB Before Writing UI Tests

> **Read [`backend/README-seed-data.md`](../../backend/README-seed-data.md) §4 Group D** before writing any Playwright test assertion or UI smoke test expectation.

The seeded test data determines what each list view shows. Key counts after SD-4 + SD-5:

- **Customers**: 8 active (John Smith, Mary Johnson, Apex Commercial LLC, Bob Davis, Inactive Customer, Rachel Kim, Metro Properties LLC, James Torres) + 3 comms customers
- **Quotes**: 10 — 1 per status code (draft, pending_approval, pending, approved, sent, accepted, converted, rejected, expired, void)
- **Invoices**: 7+ — 1 per status code (draft, issued, partial, paid, void, writeoff) + 1 from the QTC chain
- **Jobs**: 13+ — across all statuses (draft, scheduled, in_progress, completed, cancelled)
- **Suppliers**: 3 (Wesco, Graybar, Platt)

**Never assert `expect(rows).toHaveLength(1)`** on a list that has seed data — the count will be wrong. Always assert by specific IDs or filter to the exact record you created.

---

## 32. React 19 + React Compiler — Do Not Hand-Memoize (Stack: Next.js 16, React 19.2)

The web app runs **React 19.2 with the React Compiler enabled** (`babel-plugin-react-compiler@1.0.0` in [`apps/web/package.json`](../../frontend/apps/web/package.json)). The compiler auto-memoizes components and values. Hand-written `useMemo` / `useCallback` / `React.memo` for render-perf are now **noise** and are banned for new code unless one of the narrow exceptions below applies.

```tsx
// ❌ AVOID — the compiler already memoizes this; the wrapper is dead weight
const total = useMemo(() => lines.reduce((s, l) => s + l.cents, 0), [lines]);
const handleClick = useCallback(() => doThing(id), [id]);

// ✅ REQUIRED — write straightforward code; let the compiler optimize
const total = lines.reduce((s, l) => s + l.cents, 0);
const handleClick = () => doThing(id);
```

**Narrow exceptions where `useMemo`/`useCallback` are still REQUIRED** (identity, not perf):
- A value/function is passed to a **non-compiled** boundary (a `useEffect` dependency array, a third-party lib that does referential-equality checks, or a `Context` value consumed widely).
- Expensive **non-render** computation you explicitly want cached across renders (rare in this app).

**The compiler requires pure components.** Never mutate props, state, or a value returned by a hook during render. The `eslint-plugin-react-hooks` (v5+, includes the compiler's rules-of-react checks) runs in `pnpm lint` — a component the compiler cannot compile will surface as a lint error. Fix the purity violation; never disable the rule.

---

## 33. TanStack Query v5 — Object-Form API + Centralized Query Keys

The app uses **@tanstack/react-query v5**. The v4 positional-argument overloads are removed — always use the single-object form.

```tsx
// ❌ BANNED — v4 positional form, does not compile under v5
useQuery(['customers', id], () => fetchCustomer(id));

// ✅ REQUIRED — v5 single-object form
useQuery({ queryKey: customerKeys.detail(id), queryFn: () => fetchCustomer(id) });
```

**Rules for hooks in `apps/web/src/features/*/hooks/`:**
- **`gcTime`, not `cacheTime`** — the option was renamed in v5. `isPending`, not `isLoading`, for the initial-fetch state.
- **Query keys are structured and colocated.** Follow the existing convention: export a `*_QUERY_KEY` constant (e.g. [`CHECKLIST_QUERY_KEY`](../../frontend/apps/web/src/features/onboarding/hooks/useOnboardingChecklist.ts)) or a key-factory object, and always include every variable the `queryFn` reads (filters, pagination, ids) in the key array so caches stay isolated and refetch correctly.
- **Set `staleTime` deliberately.** `staleTime` controls network-request frequency; `gcTime` controls memory lifetime. Default `staleTime: 0` refetches on every mount — set a sensible non-zero `staleTime` for reference/lookup data (labor rates, job types, tiers) so we don't hammer the API. Fast-moving data (dispatch board, SMS threads) may stay at `0` and rely on SSE for freshness.
- **Use `placeholderData: keepPreviousData`** (imported from `@tanstack/react-query`) for paginated list hooks so the table does not flash empty between pages — never the removed `keepPreviousData: true` boolean option.
- **Invalidate, don't hand-patch, after mutations** unless you are deliberately doing an optimistic update via the shared `useOptimisticMutation` (§16.8 pattern). Call `queryClient.invalidateQueries({ queryKey: ... })` in `onSettled`.

---

## 34. Zod v4 — Validation Lives With React Hook Form + `@hookform/resolvers`

The app uses **Zod v4** with **React Hook Form 7** via `@hookform/resolvers/zod`. Zod + React Hook Form are the target for create/edit forms (most existing forms still use hand-rolled state; migration pending).

```tsx
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";

const schema = z.object({
  display_name: z.string().min(1, "Name is required"),
  email: z.email().optional(),           // v4: top-level z.email(), NOT z.string().email()
});
type FormValues = z.infer<typeof schema>;

const form = useForm<FormValues>({ resolver: zodResolver(schema) });
```

**Zod v4 specifics that differ from v3:**
- Use the **top-level string-format helpers** — `z.email()`, `z.uuid()`, `z.url()`. The chained `z.string().email()` form is deprecated in v4.
- Error customization uses the unified **`error`** parameter (e.g. `z.string({ error: "Required" })`), not the v3 `message` / `invalid_type_error` split.
- **Never re-derive a type by hand** when the backend owns the shape — infer request/response types from `@pilot/shared-types` (§1.3). Use Zod schemas for **client-entered form input** validation, not as a substitute for the generated API types.

---

## 35. Server vs Client Components — Data Fetching Stays Client-Side via TanStack Query

The web app is an **authenticated SPA-style dashboard** running on Next.js 16 App Router. The established, non-negotiable data pattern is: **`apiClient` + TanStack Query inside `"use client"` components.** Do not introduce Server-Component data fetching for authenticated app data.

- **Why**: auth is Cognito JWT held client-side (Amplify), and the RBAC role comes from `GET /api/v1/users/me/permissions` (§4). A React Server Component cannot access the browser-held Amplify session, so server-side fetching of tenant data would break auth and tenant scoping.
- **`"use client"` is required** at the top of any file using hooks, `apiClient`, `useAuth`, TanStack Query, Zustand, or event handlers. Feature components and hooks are client components.
- **Server Components are allowed only** for static shells / layout scaffolding that fetch **no tenant data** (e.g., a marketing-style static page, a purely presentational layout). When in doubt, keep it a client component — matching the existing 30+ feature folders.
- **Public pages** (`/i/[token]` invoice pay, public quote viewer) are the marketing/public surface — those may fetch server-side with a token, but they are out of scope for this mode (they belong to the public-pages feature and marketing designer). Do not refactor authenticated surfaces to imitate them.
- Never call `apiClient` (Axios/browser) from a Server Component or a Next.js Route Handler — it has no browser session and will 401.

---

## 36. Accessibility — WCAG 2.2 AA Is the Bar (axe-core Gate in §10 Stands)

The DoD already requires zero axe-core violations (§10). These WCAG 2.2 criteria are the ones most often missed and are now explicit requirements for every new surface:

- **2.4.11 Focus Not Obscured** — sticky headers, toasts (`<NotificationBanner>`/portal), and modals must never fully cover the keyboard-focused element. Verify Tab order keeps focus visible against our `h-12` sticky header and any bottom-anchored banner.
- **2.5.8 Target Size (Minimum 24×24px)** — all interactive controls (icon buttons, table row actions, pagination controls, close `XMarkIcon`) must have at least a 24×24px hit area. Prefer 44×44px for primary touch actions. Never ship a bare 16px icon as the only click target.
- **3.3.8 Accessible Authentication** — login / MFA flows must not require a cognitive test (no un-pasteable fields). Allow paste on all auth and MFA-code inputs; never block `onPaste`.
- **3.2.6 Consistent Help** — the `HelpAnchor` "?" affordance must appear in the same relative location across surfaces (§16 help pattern already enforces this — do not relocate it per-page).
- **3.3.7 Redundant Entry** — do not ask the user to re-enter information already provided earlier in a multi-step flow (signup wizard, onboarding). Carry values forward.
- **Focus management for modals**: on open, move focus into the dialog; trap Tab within it; on close, return focus to the trigger. Every modal/dialog needs `role="dialog"` + `aria-modal="true"` + an accessible name.
- **Forms**: every input has an associated `<label>` (§ Design System form pattern); error text is linked via `aria-describedby` and the field gets `aria-invalid` — a red border alone (color only) fails 1.4.1.

## 37. Next.js 16 Proxy (formerly Middleware) — `proxy.ts`, and Never Trust `nextUrl.hostname` Behind the ALB

**Stack note (TS-BUG-1, 2026-08-26)**: Next.js 16 renamed the `middleware.ts` file convention to **`proxy.ts`** (default-exported `proxy(request: NextRequest)`). `middleware.ts` is deprecated and must not be used for new work. The web app has exactly one proxy — `apps/web/src/proxy.ts` (tenant-site host rewrite, matcher-scoped to `["/", "/privacy", "/terms", "/sites/:path*"]` — never widen the matcher without Architect review).

Two production truths discovered the hard way (3 deploy iterations of TS-BUG-1):

1. **`request.nextUrl.hostname` is NOT reliable behind the AWS ALB** — the standalone server may resolve it to the container bind address / internal hostname instead of the client `Host` header. Any proxy/middleware logic keyed on the host MUST read `request.headers.get("host")` (strip the port) as the primary source, with `nextUrl.hostname` as fallback only.
2. **Next.js inlines `process.env.*` at build time in the proxy bundle — even non-`NEXT_PUBLIC_` vars.** A missing/stale build-arg is baked in permanently; runtime env vars cannot override it. Defense in depth for host/domain checks: proxy runs on the Node.js runtime in Next 16 (runtime env reads work), and host-matching should carry a hard-coded safe fallback candidate list (e.g. `[envDomain, "p4tsites.com", "localhost"]`) so a stale inline can never silently no-op the proxy.

**Verification gap that must not repeat**: an infra canary (`curl -H "Host: x.p4tsites.com" https://<ALB>/api/health` → 200) proves ALB routing only — it does NOT prove the proxy rewrote the host. The app-level canary is `curl -sI https://<slug>.p4tsites.com/` → 200 + `x-middleware-rewrite: /sites/<slug>/` (ops runbook §17.1).
