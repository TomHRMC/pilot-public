# Implementation Prompt: UI-FIX-2F — Payment Method Page (Stripe Connect Frontend)

**Mode**: Pilot React Engineer  
**Batch**: UI-FIX-2F (React Engineer half)  
**Source decisions**: `dev-docs/architecture-design/batch-designs/ui-fix-2-decisions.md § FIX-020`  
**Design spec**: `dev-docs/architecture-design/batch-designs/batch-ui-fix-2f-ui-design-spec.md` — read every section  
**Estimated session**: 3–4 hours  
**Platform**: Web only (`apps/web`)  
**Backend companion**: UI-FIX-2F Python Engineer — ✅ **Complete** as of 2026-07-21. Run `pnpm sync-api-types` before writing any code.

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-react-engineer/react-engineer-rules.md`** — in full
- **`dev-docs/architecture-design/batch-designs/ui-fix-2-decisions.md § FIX-020`** — the full FIX-020 section (Payment Method Screen)
- **`dev-docs/architecture-design/batch-designs/batch-ui-fix-2f-ui-design-spec.md`** — all sections (produced by UI Designer, approved by Tom)

**Before rendering any subscription, billing, or entitlement UI:**  
Read `dev-docs/pilot-operations.md` §11 — covers: the Stripe Connect architecture (two payment flows — Pilot's own subscription billing via `STRIPE_SECRET_KEY` vs. tenant card payment routing via `stripe_account=`), subscription status display rules, and the `PaymentNotConfiguredError` manual fallback behavior.

**Critical rules for this batch:**

- **Rule 1.1**: Before writing ANY hook or API call, verify the endpoint exists in `backend/openapi_schema_map.md`. If it is NOT there → **STOP and ask Tom**.
- **Rule 1.2**: Do NOT invent URL patterns or parameter names. Every shape comes from `openapi.json` or the design spec (which was authored from `openapi_schema_map.md`).
- **Rule 1.3**: Run `pnpm sync-api-types` before starting — all TypeScript types for backend payloads come from `@pilot/shared-types`, never hand-written interfaces.
- **Rule 2**: All API calls use `apiClient` from `@pilot/shared-api`. `fetch()` is permanently banned for `/api/v1/...` calls.
- **Rule 7**: Check `packages/ui/src/index.ts` before creating any new component — `<LoadingState>`, `<ErrorState>`, `<EmptyState>`, `<RoleGate>` are already available.
- **Rule 8**: No new npm dependencies without first checking what is already installed in `package.json`.
- **Rule 9**: Route files in `apps/web/src/app/(authed)/` MUST be thin server components — no `"use client"`, no data fetching. One line: `return <PaymentMethodSettingsPage />;`
- **Rule 10**: If ANY test fails during your work — even a pre-existing one — **you must fix it before declaring the batch done**.

---

## Design Decisions (Do Not Re-Litigate)

These decisions were resolved in FIX-020 and the UI Designer spec. They are final:

| Decision | Outcome | Rationale |
|---|---|---|
| RBAC scope | `<RoleGate permission="settings.tenant.write">` — owner only | Only owners manage payment/billing settings |
| Onboarding flow | Browser full-page redirect to Stripe Account Link URL | Stripe Account Links (not OAuth `ca_` flow); user leaves Pilot temporarily |
| Connect button feedback | Loading spinner in button after click, then `window.location.href = account_link_url` | Stripe redirect is not instant — the brief spinner prevents double-clicks |
| Stripe redirect return | Check `?connected=true` and `?retry=true` URL params on component mount | No backend callback endpoint; Stripe sends user back to frontend URL |
| No optimistic update | Re-fetch `useStripeConnectStatus` after disconnect confirms | Status from Stripe is authoritative; do not guess connected state |
| Manual payment info section | Always visible, not collapsed | Informational — users should always know this option exists |
| Disconnect confirmation | Modal before DELETE fires | Destructive action; prevents accidental disconnects |
| `BillingSettingsPage.tsx` | Remove Payment Method placeholder; add direct link to `/settings/billing/payment-method` | Route was split from billing page per FIX-019 nav redesign |
| Settings sidebar | Verify whether `payment-method` appears under Billing — if NOT, do not add it | Per FIX-019: Payment Method is accessed via Profile dropdown, not Settings sidebar |

---

## Pre-Work: Establish Regression Baseline

Before touching any file:

```bash
cd <repo>/frontend
pnpm --filter web test 2>&1 | tail -5
```

Record the exact count. These must still pass at the end of the batch.

> **If any tests are already failing before you start**: Do NOT treat them as "pre-existing" and proceed. Either confirm with Tom that it is a known, accepted failure with a documented reason, OR fix the failure before touching any batch files.

---

## Pre-Work: Sync API Types

```bash
cd <repo>/frontend
pnpm sync-api-types
```

This regenerates `packages/shared-types/src/api-schema.d.ts` from the live backend OpenAPI spec. The UI-FIX-2F Backend batch is complete — the three Stripe Connect endpoints are in `openapi.json`. All backend payload types must come from `@pilot/shared-types`.

> **If `pnpm sync-api-types` fails** → STOP and ask Tom. The backend OpenAPI spec should have been regenerated as part of the backend batch.

---

## Pre-Work: Verify Endpoints

Verify all three endpoints exist before writing any hook code:

```bash
grep -A 5 "stripe-connect" backend/openapi_schema_map.md
```

Expected output — all three must be present:

| Hook | Endpoint | Expected presence |
|---|---|---|
| `useStripeConnectStatus` | `GET /api/v1/settings/billing/stripe-connect/status` | ✅ Confirmed in `openapi_schema_map.md` (UI-FIX-2F BE complete) |
| `useStripeConnectOnboard` | `POST /api/v1/settings/billing/stripe-connect/onboard` | ✅ Confirmed |
| `useStripeConnectDisconnect` | `DELETE /api/v1/settings/billing/stripe-connect` | ✅ Confirmed |

**If any endpoint is NOT in `openapi_schema_map.md` → STOP. Do not invent a URL. Ask Tom.**

---

## Pre-Work: Read These Source Files

Read each of these with `read_file` before writing any code:

```
frontend/apps/web/src/features/settings/components/BillingSettingsPage.tsx
  ← Understand current state — what placeholder/coming-soon content to remove; existing RBAC wiring

frontend/apps/web/src/app/(authed)/settings/billing/page.tsx
  ← Understand the existing billing route structure before adding payment-method sub-route

frontend/packages/ui/src/index.ts
  ← Confirm which shared components are available (LoadingState, ErrorState, RoleGate, etc.)

frontend/packages/ui/src/role-gate/permissions.ts
  ← Confirm the exact string for settings.tenant.write before using in RoleGate

frontend/apps/web/src/mocks/handlers/index.ts
  ← Understand how to register new MSW handlers for Stripe Connect endpoints

frontend/apps/web/src/features/settings/hooks/useNotificationPreferences.ts
  ← Pattern reference for a settings-domain useQuery hook in this folder

frontend/apps/web/src/components/ProfileDropdown.tsx
  ← Confirm Payment Method link already wired from ProfileDropdown (UI-FIX-2E complete)
```

Also run these to locate related files before assuming paths:

```bash
# Find existing settings-domain hooks
find frontend/apps/web/src/features/settings/hooks -name "use*.ts" | head -20

# Find existing MSW handler files
find frontend/apps/web/src/mocks/handlers -name "*.ts" | head -20

# Confirm settings.tenant.write permission key exact string
grep -n "tenant.write\|settings.tenant" frontend/packages/ui/src/role-gate/permissions.ts

# Check if payment-method route already has a page.tsx
find frontend/apps/web/src/app -path "*/billing/payment-method*" | head -5
```

---

## MSW Handlers for Stripe Connect Endpoints

Create an MSW handler file for the three Stripe Connect endpoints so tests can proceed without a live backend.

**Step 1 — Check existing handler structure:**

```bash
cat frontend/apps/web/src/mocks/handlers/index.ts
```

**Step 2 — Create the handler file:**

```typescript
// apps/web/src/mocks/handlers/stripeConnectHandlers.ts
import { http, HttpResponse } from "msw";

export const stripeConnectHandlers = [
  // Default: not connected
  http.get("/api/v1/settings/billing/stripe-connect/status", () =>
    HttpResponse.json({
      connected: false,
      account_id: null,
      account_name: null,
      charges_enabled: false,
      payouts_enabled: false,
    }),
  ),
  // Onboard: returns a mock Stripe Account Link URL
  http.post("/api/v1/settings/billing/stripe-connect/onboard", () =>
    HttpResponse.json({
      account_link_url: "https://connect.stripe.com/setup/s/mock_test_link",
      expires_at: Math.floor(Date.now() / 1000) + 600, // 10 min from now
    }),
  ),
  // Disconnect: returns success
  http.delete("/api/v1/settings/billing/stripe-connect", () =>
    HttpResponse.json({
      disconnected: true,
      message:
        "Stripe account disconnected. Customers will see manual payment instructions.",
    }),
  ),
];
```

**Step 3 — Register in the barrel `index.ts`:**

```typescript
// apps/web/src/mocks/handlers/index.ts
import { stripeConnectHandlers } from "./stripeConnectHandlers";

export const handlers = [
  ...existingHandlers,
  ...stripeConnectHandlers, // ← ADD THIS
];
```

> **This step is mandatory.** Creating the handler file without registering it in `index.ts` means it is never loaded — tests will fall through to unhandled request warnings.

---

## Context: What This Batch Does

| # | File | Action | Notes |
|---|---|---|---|
| 1 | `features/settings/hooks/useStripeConnectStatus.ts` | **Create** | `useQuery` for GET status; returns `StripeConnectStatusResponse` |
| 2 | `features/settings/hooks/useStripeConnectOnboard.ts` | **Create** | `useMutation` for POST onboard; response contains `account_link_url` |
| 3 | `features/settings/hooks/useStripeConnectDisconnect.ts` | **Create** | `useMutation` for DELETE disconnect; invalidates status query on success |
| 4 | `features/settings/components/PaymentMethodSettingsPage.tsx` | **Create** | Full page component — 3 states + banners + disconnect modal |
| 5 | `app/(authed)/settings/billing/payment-method/page.tsx` | **Create** | Thin server component route |
| 6 | `features/settings/components/BillingSettingsPage.tsx` | **Update** | Remove Payment Method placeholder; add link to `/settings/billing/payment-method` |
| 7 | `mocks/handlers/stripeConnectHandlers.ts` | **Create** | MSW handlers for all 3 endpoints |
| 8 | `mocks/handlers/index.ts` | **Update** | Register `stripeConnectHandlers` |

---

## STEP 1 — Create `useStripeConnectStatus` Hook

**File**: `apps/web/src/features/settings/hooks/useStripeConnectStatus.ts`

Read an existing settings hook (e.g., `useNotificationPreferences.ts`) before creating this — match the import pattern, query key convention, and `apiClient` usage exactly.

The hook must:
- Call `GET /api/v1/settings/billing/stripe-connect/status`
- Use `@pilot/shared-types` for the response type (post `pnpm sync-api-types`)
- Export a `STRIPE_CONNECT_STATUS_QUERY_KEY` constant for use in `invalidateQueries`
- Return the raw TanStack Query result (`{ data, isLoading, isError, error, refetch }`)

```typescript
// Read the file first. Adjust import paths to match what you actually find.
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";
// Type from pnpm sync-api-types — verify exact name in @pilot/shared-types:
// import type { StripeConnectStatusResponse } from "@pilot/shared-types";

export const STRIPE_CONNECT_STATUS_QUERY_KEY = ["stripe-connect-status"] as const;

export function useStripeConnectStatus() {
  return useQuery({
    queryKey: STRIPE_CONNECT_STATUS_QUERY_KEY,
    queryFn: async () => {
      const res = await apiClient.get("/api/v1/settings/billing/stripe-connect/status");
      return res.data; // Adjust to match apiClient response shape you find
    },
  });
}
```

> **Verify the `apiClient` response shape** — read `@pilot/shared-api` source or an existing hook that uses `apiClient.get()` to confirm whether response is `res.data` or `res` directly.

**Intermediate verification:**
```bash
cd <repo>/frontend
pnpm --filter web check-types 2>&1 | tail -5
```

---

## STEP 2 — Create `useStripeConnectOnboard` Hook

**File**: `apps/web/src/features/settings/hooks/useStripeConnectOnboard.ts`

The hook must:
- Call `POST /api/v1/settings/billing/stripe-connect/onboard`
- Return the `account_link_url` in `onSuccess`
- The **caller** (the component) performs the browser redirect via `window.location.href = data.account_link_url` — the hook does NOT do the redirect itself
- Use `useMutation` — no `invalidateQueries` needed (status is checked after returning from Stripe)

```typescript
// Read the file first. Adjust import paths to match what you actually find.
import { useMutation } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";

export function useStripeConnectOnboard() {
  return useMutation({
    mutationFn: async () => {
      const res = await apiClient.post("/api/v1/settings/billing/stripe-connect/onboard");
      return res.data;
    },
  });
}
```

---

## STEP 3 — Create `useStripeConnectDisconnect` Hook

**File**: `apps/web/src/features/settings/hooks/useStripeConnectDisconnect.ts`

The hook must:
- Call `DELETE /api/v1/settings/billing/stripe-connect`
- On `onSuccess`: invalidate `STRIPE_CONNECT_STATUS_QUERY_KEY` so the status card re-fetches immediately
- Import `STRIPE_CONNECT_STATUS_QUERY_KEY` from `useStripeConnectStatus.ts`

```typescript
// Read the file first. Adjust import paths to match what you actually find.
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";
import { STRIPE_CONNECT_STATUS_QUERY_KEY } from "./useStripeConnectStatus";

export function useStripeConnectDisconnect() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const res = await apiClient.delete("/api/v1/settings/billing/stripe-connect");
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: STRIPE_CONNECT_STATUS_QUERY_KEY });
    },
  });
}
```

---

## STEP 4 — Create `PaymentMethodSettingsPage` Component

**File**: `apps/web/src/features/settings/components/PaymentMethodSettingsPage.tsx`

This is the main component. Read the design spec fully before implementing. Key behaviors:

### 4.1 — URL Param Check on Mount

On component mount, check `useSearchParams()` for:
- `?connected=true` → show a **success banner**: "✅ Your Stripe account has been connected. Customers can now pay by card."
- `?retry=true` → show an **info banner**: "Your previous session expired. Click 'Connect Stripe Account' to try again."
- `?error=connect_failed` → show an **error banner**: "Could not connect your Stripe account. Please try again or contact support."

Use `next/navigation`'s `useSearchParams()` for this. Banners are dismissible (show an ✕ button).

### 4.2 — Connection Status Card

Based on `useStripeConnectStatus()` data, render one of three states. Read the design spec for exact token classes, copy, and layout:

| Condition | State to render |
|---|---|
| `isLoading` | Loading skeleton/spinner within the card |
| `isError` | Error message: "Unable to load payment status. Refresh the page." |
| `!data.connected` | **Disconnected state** — "Connect Stripe Account" primary CTA |
| `data.connected && !data.charges_enabled` | **Incomplete onboarding state** — "Resume Setup" CTA |
| `data.connected && data.charges_enabled` | **Connected state** — account name, "Disconnect" button |

### 4.3 — Connect / Resume Stripe Button

When the user clicks "Connect Stripe Account" or "Resume Setup":
1. Show a loading spinner inside the button; disable the button (prevent double-click)
2. Call `useStripeConnectOnboard().mutate()` 
3. In `onSuccess`: `window.location.href = data.account_link_url` — **full page redirect to Stripe**
4. In `onError`: show an inline error inside the card (do not crash the page)

### 4.4 — Disconnect Flow

"Disconnect" button opens a **confirmation modal** before calling `useStripeConnectDisconnect`. The modal must include:
- Warning text (read design spec for exact copy)
- Cancel button (secondary style)
- "Disconnect Stripe" button styled `fault-600`

On modal confirm: call `disconnect.mutate()`. On `onSuccess`: close modal (status auto-refreshes via `invalidateQueries`).

### 4.5 — Manual Payment Info Section

Always visible below the status card. Read design spec for layout. This is static content — no data fetching.

### 4.6 — RBAC Gate

The entire page content (both sections) must be wrapped in `<RoleGate permission="settings.tenant.write">`. Read `permissions.ts` to confirm the exact permission key string before using it.

### 4.7 — Token Compliance

All colors must use `pilotPreset` tokens from the design spec. Use the exact classes specified:
- Connected: `text-margin-600`
- Connect button: `bg-brand-600 text-white hover:bg-brand-700`
- Disconnect button: `border border-fault-300 text-fault-700 hover:bg-fault-50`
- Disconnect confirm: `bg-fault-600 text-white hover:bg-fault-700`
- Success banner: `bg-margin-50 border border-margin-200 text-margin-800`
- Error banner: `bg-fault-50 border border-fault-200 text-fault-800`

> **Read the design spec for exact dimensions, padding, border-radius, and typography specs.** Do not guess — the spec was approved by Tom.

**Intermediate verification after this step:**
```bash
cd <repo>/frontend
pnpm --filter web check-types 2>&1 | tail -5
pnpm --filter web test -- apps/web/src/features/settings/components/__tests__/PaymentMethodSettingsPage.test.tsx 2>&1 | tail -10
```

---

## STEP 5 — Create Thin Route File

**File**: `apps/web/src/app/(authed)/settings/billing/payment-method/page.tsx`

Thin server component — no `"use client"`, no data fetching:

```typescript
// Read the existing billing/page.tsx first to match the import pattern exactly
import { PaymentMethodSettingsPage } from "@/features/settings/components/PaymentMethodSettingsPage";

export default function PaymentMethodPage() {
  return <PaymentMethodSettingsPage />;
}
```

> Adjust the import path to match the actual export from the component file.

---

## STEP 6 — Update `BillingSettingsPage.tsx`

**File**: `apps/web/src/features/settings/components/BillingSettingsPage.tsx`

Read the file before editing. Remove the Payment Method placeholder (any "coming soon" or deferred-state content for payment method). Add a card or section that links to `/settings/billing/payment-method`:

```tsx
// Pattern — adjust to match the design and existing component style
<Link href="/settings/billing/payment-method" className="...">
  Payment Method →
</Link>
```

> **Do not remove subscription billing content** — only remove Payment Method placeholder content. Read the existing component carefully before making any change.

---

## Test Requirements

### TanStack Query Setup for All Tests

Always use `retry: false`:

```typescript
function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}
```

### MSW Setup for All Tests

```typescript
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import { stripeConnectHandlers } from "../../../mocks/handlers/stripeConnectHandlers";

const server = setupServer(...stripeConnectHandlers);
beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
```

### Unit Tests

**File**: `apps/web/src/features/settings/components/__tests__/PaymentMethodSettingsPage.test.tsx`

Required test cases:

| Test | What to verify |
|---|---|
| Renders without crashing | Default state (disconnected) renders page title and Connect CTA |
| RBAC — tech role blocked | `<RoleGate permission="settings.tenant.write">` blocks unauthorized role (renderAs "tech" sees access-denied, not the form) |
| Disconnected state | Shows "No Stripe account connected" and "Connect Stripe Account" button |
| Incomplete onboarding state | Override MSW: `connected: true, charges_enabled: false` → "Setup Incomplete" + "Resume Setup" button |
| Connected state | Override MSW: `connected: true, charges_enabled: true, account_name: "Acme Electric LLC"` → shows account name and "Disconnect" button |
| Loading state | `<LoadingState>` / skeleton renders while fetching |
| Error state | Override MSW: GET status 500 → error message renders in status card |
| `?connected=true` param | Mount with `?connected=true` in URL → success banner visible |
| `?retry=true` param | Mount with `?retry=true` in URL → info/retry banner visible |
| Disconnect modal opens | Click "Disconnect" → confirmation modal appears |
| Disconnect modal cancel | Click "Cancel" in modal → modal closes, no DELETE fired |
| Manual payment section | Always visible — static content renders in all states |

**File**: `apps/web/src/features/settings/hooks/__tests__/useStripeConnectStatus.test.ts`

| Test | What to verify |
|---|---|
| Returns data in expected shape | MSW returns connected status; hook returns `{ connected, charges_enabled, ... }` |
| Returns error state on 500 | Override MSW: 500 → `isError: true` |

**File**: `apps/web/src/features/settings/hooks/__tests__/useStripeConnectDisconnect.test.ts`

| Test | What to verify |
|---|---|
| Fires DELETE on mutate | MSW captures DELETE request; mutation completes successfully |
| Invalidates status query on success | After success, verify status query re-fetches (queryClient.invalidateQueries fires) |

### Integration Tests

**File**: `apps/web/src/__tests__/batch_ui_fix_2f/payment_method.integration.test.tsx`

Required:
1. Route does NOT 404 — page renders at `/settings/billing/payment-method`
2. RBAC: owner sees status card; tech role is blocked by `<RoleGate>`
3. Connected state renders full account display (override MSW in test)
4. "Connect" button fires POST to `…/onboard` (spy on MSW handler call)
5. "Disconnect" → modal → confirm fires DELETE to `…/stripe-connect`

### RBAC Test Pattern (Web)

```typescript
import { AuthContext } from "@pilot/ui/auth";
import type { AuthContextValue, PilotRole } from "@pilot/ui/auth";

function makeAuthValue(role: PilotRole): AuthContextValue {
  return {
    user: { id: "u1", email: "test@example.com", role, tenantId: "t1", displayName: "Test", accessToken: "tok" },
    isAuthenticated: true, role,
    signIn: vi.fn(), confirmMfaChallenge: vi.fn(),
    signOut: vi.fn(), refreshSession: vi.fn().mockResolvedValue("tok"),
  };
}

it("tech does NOT see payment method form", () => {
  render(
    React.createElement(AuthContext.Provider, { value: makeAuthValue("tech") },
      React.createElement(PaymentMethodSettingsPage)
    )
  );
  // Should NOT see Connect CTA
  expect(screen.queryByText("Connect Stripe Account")).not.toBeInTheDocument();
});
```

### Mock `next/navigation` in All Tests

```typescript
vi.mock("next/navigation", () => ({
  usePathname: () => "/settings/billing/payment-method",
  useSearchParams: () => new URLSearchParams(""),
}));
```

> For tests verifying `?connected=true` banner, override the mock:
```typescript
vi.mock("next/navigation", () => ({
  usePathname: () => "/settings/billing/payment-method",
  useSearchParams: () => new URLSearchParams("connected=true"),
}));
```

---

## Final Verification

> ❌ **BANNED COMMAND**: `npx vitest run` — **NEVER use this**. The ONLY correct test runner is `pnpm --filter web test`.

### Phase 1 — Targeted (run after each task group)

```bash
cd <repo>/frontend

# Specific test file (fast feedback):
pnpm --filter web test -- apps/web/src/features/settings/components/__tests__/PaymentMethodSettingsPage.test.tsx 2>&1 | tail -10

# All hooks tests:
pnpm --filter web test -- apps/web/src/features/settings/hooks/__tests__/ 2>&1 | tail -10

# Integration batch folder:
pnpm --filter web test -- apps/web/src/__tests__/batch_ui_fix_2f/ 2>&1 | tail -10

# Full web suite:
pnpm --filter web test 2>&1 | tail -6
```

Fix any failure before moving to the next task. No "pre-existing failure" exception without Tom confirmation.

### Phase 2 — Full verification (run once at the very end)

```bash
cd <repo>/frontend && echo "=== UI - Type Check ===" && pnpm --filter @pilot/ui check-types && echo "=== Web - Type Check ===" && pnpm --filter web check-types && echo "=== Mobile - Type Check ===" && pnpm --filter mobile build && echo "=== UI - Lint ===" && pnpm --filter @pilot/ui lint && echo "=== Web - Lint ===" && pnpm --filter web lint && echo "=== Mobile - Lint ===" && pnpm --filter mobile lint && echo "=== TYPE+LINT PASS ===" && echo "=== UI - Tests ===" && pnpm --filter @pilot/ui test 2>&1 | tail -6 && echo "=== Web - Tests ===" && pnpm --filter web test 2>&1 | tail -6 && echo "=== Mobile - Tests ===" && pnpm --filter mobile test 2>&1 | tail -8 && echo "=== MVP FINAL VERIFICATION COMPLETE ==="
```

> **`pnpm --filter mobile build` = mobile type check.** There is no separate `check-types` script for mobile.

> **Any failure in either phase must be fixed before the batch is declared done.**

---

## Definition of Done — UI-FIX-2F (React Engineer)

Update `dev-docs/architecture-design/batch-designs/ui-fix-2-decisions.md` Batch Overview table when done:

- [ ] Pre-modification regression baseline captured (zero pre-existing failures, or confirmed with Tom)
- [ ] `pnpm sync-api-types` run — no new type errors
- [ ] Design spec fully read before writing any code
- [ ] All mandatory source files read before modifying
- [ ] All 3 endpoint URLs verified in `openapi_schema_map.md`
- [ ] `stripeConnectHandlers.ts` created + registered in `mocks/handlers/index.ts`
- [ ] **STEP 1**: `useStripeConnectStatus.ts` created — query with `STRIPE_CONNECT_STATUS_QUERY_KEY` export
- [ ] **STEP 2**: `useStripeConnectOnboard.ts` created — mutation returning `account_link_url`
- [ ] **STEP 3**: `useStripeConnectDisconnect.ts` created — mutation + `invalidateQueries` on success
- [ ] **STEP 4**: `PaymentMethodSettingsPage.tsx` created — all 3 status states + banners + disconnect modal + RBAC gate + token-compliant colors
- [ ] `?connected=true` → success banner renders
- [ ] `?retry=true` → info/retry banner renders
- [ ] Disconnect modal opens on "Disconnect" click; fires DELETE only on confirm
- [ ] Manual payment info section is always visible
- [ ] **STEP 5**: `app/(authed)/settings/billing/payment-method/page.tsx` created (thin server component)
- [ ] **STEP 6**: `BillingSettingsPage.tsx` updated — Payment Method placeholder removed; link to new route added
- [ ] `<RoleGate permission="settings.tenant.write">` wraps page content — tech role blocked
- [ ] Zero hardcoded hex colors — all from `pilotPreset` tokens per design spec
- [ ] Unit tests pass in `features/settings/components/__tests__/PaymentMethodSettingsPage.test.tsx`
- [ ] Hook unit tests pass in `features/settings/hooks/__tests__/`
- [ ] Integration tests pass in `__tests__/batch_ui_fix_2f/`
- [ ] Zero TypeScript errors (`pnpm --filter web check-types` passes)
- [ ] Zero ESLint `no-hardcoded-design-values` warnings
- [ ] No regressions in pre-existing test suite
- [ ] **Phase 2 FULL verification command passes** (`=== MVP FINAL VERIFICATION COMPLETE ===`):
  ```bash
  cd <repo>/frontend && echo "=== UI - Type Check ===" && pnpm --filter @pilot/ui check-types && echo "=== Web - Type Check ===" && pnpm --filter web check-types && echo "=== Mobile - Type Check ===" && pnpm --filter mobile build && echo "=== UI - Lint ===" && pnpm --filter @pilot/ui lint && echo "=== Web - Lint ===" && pnpm --filter web lint && echo "=== Mobile - Lint ===" && pnpm --filter mobile lint && echo "=== TYPE+LINT PASS ===" && echo "=== UI - Tests ===" && pnpm --filter @pilot/ui test 2>&1 | tail -6 && echo "=== Web - Tests ===" && pnpm --filter web test 2>&1 | tail -6 && echo "=== Mobile - Tests ===" && pnpm --filter mobile test 2>&1 | tail -8 && echo "=== MVP FINAL VERIFICATION COMPLETE ==="
  ```
- [ ] Final test count (before → after) documented in batch overview

---

## Completion Summary

After all Definition of Done items are complete:

1. Add a **Completion Summary** subsection to `dev-docs/architecture-design/batch-designs/ui-fix-2-decisions.md` under the UI-FIX-2F batch row (after the existing Backend Completion Summary).
2. Update the Batch Overview table row for **UI-FIX-2F** in `ui-fix-2-decisions.md` — change Status from `🔄 Backend ✅ 2026-07-21 — FE ⏳ Pending` to `✅ Complete — YYYY-MM-DD`.
3. Update `dev-docs/analysis/pilot-launch-plan.md` — **three locations**:
   - **Section 2 → UI Fix — Batch 2 table**: change the `UI-FIX-2F` row Status from `🔄 Backend ✅ 2026-07-21 — FE ⏳ Pending` to `✅ Complete — YYYY-MM-DD`.
   - **Appendix A → A-2**: add a row `| UI-FIX-2F (FE) | React Engr | YYYY-MM-DD | Payment Method page — PaymentMethodSettingsPage + 3 Stripe Connect hooks + route + MSW handlers |` immediately after the `UI-FIX-2F (BE)` row.
   - **Appendix B**: add a `UI-FIX-2F (React Engineer) — Payment Method Page` completion summary section (using the template below) immediately after the existing `UI-FIX-2F (Backend)` completion summary.

```markdown
### UI-FIX-2F (React Engineer) — Payment Method Page (Stripe Connect Frontend): Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot React Engineer
**Baseline**: X passed (web)
**Final**: X+N passed (+N new tests)

#### What Was Accomplished

- `useStripeConnectStatus` / `useStripeConnectOnboard` / `useStripeConnectDisconnect` hooks created
- `PaymentMethodSettingsPage.tsx` built — 3 connection states (disconnected / incomplete / connected), URL-param banners, disconnect modal, manual payment info section, `<RoleGate>` RBAC
- Thin route created at `/settings/billing/payment-method`
- `BillingSettingsPage.tsx` updated — Payment Method placeholder removed, link to new route added
- MSW handlers created for all 3 Stripe Connect endpoints; registered in `index.ts`

#### Files Changed / Created

| File | Action |
|---|---|
| `frontend/apps/web/src/features/settings/hooks/useStripeConnectStatus.ts` | Created |
| `frontend/apps/web/src/features/settings/hooks/useStripeConnectOnboard.ts` | Created |
| `frontend/apps/web/src/features/settings/hooks/useStripeConnectDisconnect.ts` | Created |
| `frontend/apps/web/src/features/settings/components/PaymentMethodSettingsPage.tsx` | Created |
| `frontend/apps/web/src/app/(authed)/settings/billing/payment-method/page.tsx` | Created |
| `frontend/apps/web/src/features/settings/components/BillingSettingsPage.tsx` | Updated — removed placeholder, added link |
| `frontend/apps/web/src/mocks/handlers/stripeConnectHandlers.ts` | Created |
| `frontend/apps/web/src/mocks/handlers/index.ts` | Updated — registered stripeConnectHandlers |

#### Tests Added

| Test File | Type | Tests | All Pass |
|---|---|---|---|
| `features/settings/components/__tests__/PaymentMethodSettingsPage.test.tsx` | Unit | N | ✅ |
| `features/settings/hooks/__tests__/useStripeConnectStatus.test.ts` | Unit | N | ✅ |
| `features/settings/hooks/__tests__/useStripeConnectDisconnect.test.ts` | Unit | N | ✅ |
| `__tests__/batch_ui_fix_2f/payment_method.integration.test.tsx` | Integration | N | ✅ |
```
