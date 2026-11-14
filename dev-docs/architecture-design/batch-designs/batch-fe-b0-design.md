# Batch FE-B0 Design — Pre-Implementation Foundation

**Batch**: FE-B0  
**Design Date**: May 21, 2026  
**Architect**: Pilot Architect mode  
**Consumer**: Pilot React Engineer mode (Phase 2 implementation)  
**Source Plan**: `dev-docs/analysis/pilot-app-mvp-frontend-impl-plan.md` §6 FE-B0  
**Prerequisite Batches**: None (Phase 0 Turborepo scaffolding confirmed complete)  
**Gates**: All subsequent FE batches (FE-B1 cannot begin until FE-B0 passes completion gate)

---

## Verification Status Summary

| Check | Result |
|:---|:---|
| V1 — API types regenerated | ✅ Pass — `api-schema.d.ts` is 32,030 lines with full backend schema |
| V2 — Gluestack imports tokens | ✅ Pass — `apps/mobile/theme/gluestack-config.ts` imports from `@pilot/ui/tokens` (actual: `@repo/ui/tokens`) |
| V3 — Web app consumes Tailwind preset | ❌ **FAIL** — `apps/web/src/app/globals.css` uses bare `@import "tailwindcss"` with no `@config` reference; no `tailwind.config.ts` exists in `apps/web/`; `pilotPreset` is NOT wired |
| V4 — All 3 apps build clean | ✅ Pass |
| V5 — Backend health endpoint | ✅ Pass |
| V6 — TanStack Query not yet installed | ✅ Pass — absent from `apps/web/package.json` |
| V7 — MSW not yet installed | ✅ Pass — absent from `apps/web/package.json` |

**V3 Resolution is Item 1 scope.** See Section G for the exact fix.

---

## Critical Package Name Discrepancy

> **Action required by React Engineer before writing any import**: The shared UI package is registered in `frontend/packages/ui/package.json` as `"name": "@repo/ui"`, **not** `@pilot/ui`. The methods doc and impl plan reference `@pilot/ui` throughout. Until the package is renamed (a one-line change to `package.json`), all imports must use `@repo/ui`. This design doc uses `@repo/ui` throughout to match the current codebase reality.
>
> **Recommendation**: Rename the package to `@pilot/ui` in `packages/ui/package.json` as the first act of FE-B0 Item 1. This aligns the codebase with every doc reference, avoids two-name confusion, and is a zero-risk change (no published packages; all consumers are in the same workspace).

---

## A. Component Implementation Plan

All components below are confirmed **new** (grep against current `frontend/` confirms none exist):

### A.1 Shared Components — `packages/ui/src/`

| Component / Hook | File Path | Props Interface Summary | Notes |
|:---|:---|:---|:---|
| `<AuthProvider>` | `packages/ui/src/auth/AuthProvider.tsx` | `{ children: ReactNode; mockUser?: MockUser }` | Wraps `Amplify.configure()` + Cognito; `mockUser` prop enables `MockAuthProvider` via `USE_MOCK_AUTH` env var |
| `useAuth()` | `packages/ui/src/auth/useAuth.ts` | Returns `{ user, signIn, signOut, isAuthenticated, role, accessToken }` | Hook that reads from `AuthContext`; exported from `@repo/ui/auth` |
| `<RequireAuth>` | `packages/ui/src/auth/RequireAuth.tsx` | `{ children: ReactNode; redirectTo: string }` | Used in Next.js `(authed)/layout.tsx` and Expo `(authed)/_layout.tsx`; reads `isAuthenticated` from `useAuth()` |
| `<RoleGate>` | `packages/ui/src/role-gate/RoleGate.tsx` | `{ role: PilotRole \| PilotRole[]; children: ReactNode }` | Renders children only if `useAuth().role` matches; returns `null` otherwise — **hide-not-disable** |
| `useRequiresPermission()` | `packages/ui/src/role-gate/useRequiresPermission.ts` | `(permissionKey: PermissionKey) => boolean` | Returns boolean for inline conditional rendering |
| `permissions.ts` (registry) | `packages/ui/src/role-gate/permissions.ts` | `PermissionKey` union type; `ROLE_PERMISSION_MAP` lookup | Single source of truth for all permission keys; see §F for full interface |

### A.2 Web App Components — `apps/web/src/`

| Component | File Path | Purpose |
|:---|:---|:---|
| `RootProviders` | `apps/web/src/app/providers.tsx` | Composes `<AuthProvider>`, `<QueryClientProvider>`, MSW init (env-gated) |
| `(authed)/layout.tsx` | `apps/web/src/app/(authed)/layout.tsx` | Authenticated route group layout; wraps children in `<RequireAuth redirectTo="/login">` |
| `(dev)/health/page.tsx` | `apps/web/src/app/(dev)/health/page.tsx` | Preserved health-check page behind `NEXT_PUBLIC_SHOW_DEV_ROUTES` env gate |

**Web routing skeleton pages** (all placeholder — render section name only, no functionality):

| Route File | Route Path |
|:---|:---|
| `apps/web/src/app/(authed)/dashboard/page.tsx` | `/dashboard` |
| `apps/web/src/app/(authed)/schedule/page.tsx` | `/schedule` |
| `apps/web/src/app/(authed)/customers/page.tsx` | `/customers` |
| `apps/web/src/app/(authed)/quotes/page.tsx` | `/quotes` |
| `apps/web/src/app/(authed)/invoices/page.tsx` | `/invoices` |
| `apps/web/src/app/(authed)/reports/page.tsx` | `/reports` |
| `apps/web/src/app/(authed)/comms/page.tsx` | `/comms` |
| `apps/web/src/app/(authed)/operations/page.tsx` | `/operations` |
| `apps/web/src/app/(authed)/sync/page.tsx` | `/sync` |
| `apps/web/src/app/(authed)/notifications/page.tsx` | `/notifications` |
| `apps/web/src/app/(authed)/settings/page.tsx` | `/settings` |

### A.3 Mobile App Components — `apps/mobile/`

**Mobile routing skeleton tabs** (all placeholder — render tab name only):

| Route File | Tab | Icon (SF Symbol) | Role Gate |
|:---|:---|:---|:---|
| `apps/mobile/app/(tabs)/index.tsx` | Home | `house.fill` | None (all roles) |
| `apps/mobile/app/(tabs)/jobs.tsx` | Jobs | `briefcase.fill` | None (all roles) |
| `apps/mobile/app/(tabs)/customers.tsx` | Customers | `person.2.fill` | None (all roles) |
| `apps/mobile/app/(tabs)/calcs.tsx` | Calcs | `function` | None (all roles) |
| `apps/mobile/app/(tabs)/owner.tsx` | Owner | `person.badge.key.fill` | `<RoleGate role="owner">` wraps tab content; tab icon still renders for all roles but content is gated |

### A.4 Shared API Package — `packages/shared-api/src/`

| Module | File Path | Exports |
|:---|:---|:---|
| `client.ts` (modified) | `packages/shared-api/src/client.ts` | `apiClient` — Axios instance with JWT interceptor, tenant-id header, retry logic |
| `health.ts` (new) | `packages/shared-api/src/health.ts` | `checkApiHealth()` — migrated from `index.ts` |
| `index.ts` (modified) | `packages/shared-api/src/index.ts` | Re-exports from all domain modules |
| `queryClient.ts` (new) | `packages/shared-api/src/queryClient.ts` | `createQueryClient()` — shared TanStack Query client factory with defaults |

### A.5 MSW Setup Files

| File | Purpose |
|:---|:---|
| `apps/web/src/mocks/browser.ts` | `setupWorker(...)` for web browser — activated in dev via env var |
| `apps/web/src/mocks/handlers/health.ts` | MSW handler for `GET /api/v1/health/celery` |
| `apps/web/src/mocks/handlers/index.ts` | Barrel re-export of all handlers |
| `apps/mobile/mocks/server.ts` | `setupServer(...)` for React Native (Node-based MSW) |
| `apps/mobile/mocks/handlers/health.ts` | Same health handler |
| `apps/mobile/mocks/handlers/index.ts` | Barrel re-export |

### A.6 ESLint Config Extension

| File | Change |
|:---|:---|
| `packages/eslint-config/rules/no-hardcoded-design-values.ts` | New file — custom ESLint rule (warning severity for FE-B0; upgraded to error at FE-B1 close) |

---

## B. Execution Order

Implementation items in strict dependency order within FE-B0:

| Step | Item | Rationale |
|:---|:---:|:---|
| 1 | **Package rename** — `packages/ui/package.json` `"name"` from `@repo/ui` → `@pilot/ui` | Zero-risk; aligns all docs with codebase; must be first so all subsequent imports are correct |
| 2 | **`packages/ui/package.json` exports** — expand `"exports"` field with per-category paths | Required before any component in `packages/ui/` can be imported by correct path |
| 3 | **V3 Fix** — wire `pilotPreset` into `apps/web` (see §G-1 for exact changes) | Token consumption is non-negotiable; every subsequent component depends on Tailwind tokens being live |
| 4 | **`globals.css` overhaul** — replace placeholder CSS vars with token-sourced CSS variables from `packages/ui/src/styles/globals.css` | Closes the token wiring loop on the CSS side |
| 5 | **ESLint `no-hardcoded-design-values` rule** — add to `packages/eslint-config/` | Lock discipline early; configure as **warning** (not error) for FE-B0 duration |
| 6 | **TanStack Query install + `queryClient.ts`** — install in web + mobile; create `createQueryClient()`; wire `<QueryClientProvider>` at root | Must exist before apiClient interceptors can be tested via integration |
| 7 | **`packages/shared-api` refactor** — migrate `checkApiHealth` → `health.ts`; create domain-based module structure; update `index.ts` | Establishes the growth architecture; subsequent domain modules slot in cleanly |
| 8 | **JWT interceptor in `client.ts`** — add Amplify `fetchAuthSession()` request interceptor + 401-catch refresh interceptor | Depends on knowing the auth pattern (Amplify) from step 9; but interceptor logic is independent of provider scaffolding — can be written against the interface |
| 9 | **`<AuthProvider>` + `useAuth()`** — create in `packages/ui/src/auth/`; configure Amplify; create `MockAuthProvider` for `USE_MOCK_AUTH=true` | Auth context must exist before `<RoleGate>` or `<RequireAuth>` can work |
| 10 | **`<RoleGate>` + `useRequiresPermission()` + `permissions.ts`** — create in `packages/ui/src/role-gate/` | Depends on `useAuth()` for role reads |
| 11 | **Web routing skeleton** — create `(authed)/layout.tsx` with `<RequireAuth>`; create 11 placeholder pages; create `providers.tsx` with MSW + QueryClientProvider | Depends on auth primitives from steps 9–10 |
| 12 | **Mobile routing skeleton** — update `(tabs)/_layout.tsx` to 5-tab layout; rename/create tab files; wire `<GluestackUIProvider config={pilotConfig}>` in `app/_layout.tsx` | Note: `pilotConfig` export name — see §G-5 |
| 13 | **MSW setup** — install MSW; create browser/server workers; create health handler | Depends on `shared-api/health.ts` being defined so handler shapes match |
| 14 | **Hello World → dev route** — move health-check content to `(dev)/health/page.tsx`; replace root `page.tsx` with redirect to `/dashboard` | Final routing cleanup; do last so health check remains functional during dev work above |
| 15 | **End-to-end smoke test** — write the integration test (item 10 in impl plan §6 FE-B0) | Can only be written once all above are wired |

---

## C. New Routes

### C.1 Web Routes (Next.js App Router)

| Route | File | Auth Required | RBAC Gate | Notes |
|:---|:---|:---:|:---|:---|
| `/` | `apps/web/src/app/page.tsx` | No | — | Redirects to `/dashboard` if authenticated, `/login` if not |
| `/login` | `apps/web/src/app/login/page.tsx` | No | — | Placeholder in FE-B0; implemented in FE-B2 |
| `/dashboard` | `apps/web/src/app/(authed)/dashboard/page.tsx` | **Yes** | None — all authenticated roles | Placeholder: "Dashboard" heading |
| `/schedule` | `apps/web/src/app/(authed)/schedule/page.tsx` | **Yes** | None | Placeholder |
| `/customers` | `apps/web/src/app/(authed)/customers/page.tsx` | **Yes** | None | Placeholder |
| `/quotes` | `apps/web/src/app/(authed)/quotes/page.tsx` | **Yes** | None | Placeholder |
| `/invoices` | `apps/web/src/app/(authed)/invoices/page.tsx` | **Yes** | None | Placeholder |
| `/reports` | `apps/web/src/app/(authed)/reports/page.tsx` | **Yes** | None | Placeholder |
| `/comms` | `apps/web/src/app/(authed)/comms/page.tsx` | **Yes** | None | Placeholder |
| `/operations` | `apps/web/src/app/(authed)/operations/page.tsx` | **Yes** | None | Placeholder |
| `/sync` | `apps/web/src/app/(authed)/sync/page.tsx` | **Yes** | None | Placeholder |
| `/notifications` | `apps/web/src/app/(authed)/notifications/page.tsx` | **Yes** | None | Placeholder |
| `/settings` | `apps/web/src/app/(authed)/settings/page.tsx` | **Yes** | None | Placeholder |
| `/_dev/health` | `apps/web/src/app/(dev)/health/page.tsx` | No | Env-gated: `NEXT_PUBLIC_SHOW_DEV_ROUTES=true` | Preserved health check; removed from production routing |

**`(authed)/layout.tsx`** applies `<RequireAuth redirectTo="/login">` to all 11 sections. Unauthenticated users are redirected to `/login`.

### C.2 Mobile Routes (Expo Router)

| Route | File | Auth Required | RBAC Gate | Notes |
|:---|:---|:---:|:---|:---|
| `/(tabs)/index` | `apps/mobile/app/(tabs)/index.tsx` | **Yes** | None | Home tab placeholder |
| `/(tabs)/jobs` | `apps/mobile/app/(tabs)/jobs.tsx` | **Yes** | None | Jobs tab placeholder |
| `/(tabs)/customers` | `apps/mobile/app/(tabs)/customers.tsx` | **Yes** | None | Customers tab placeholder |
| `/(tabs)/calcs` | `apps/mobile/app/(tabs)/calcs.tsx` | **Yes** | None | Calcs tab placeholder |
| `/(tabs)/owner` | `apps/mobile/app/(tabs)/owner.tsx` | **Yes** | `<RoleGate role="owner">` wraps page content | Owner tab placeholder; tab itself visible to all roles; content hidden for tech role |

**`app/(authed)/_layout.tsx`** (new): wraps the tabs group in `<RequireAuth>` for mobile. The `app/_layout.tsx` is updated to add `<GluestackUIProvider>` and `<QueryClientProvider>` at root.

---

## D. API Endpoint Consumption

FE-B0 is infrastructure-only. No surface-level API calls are introduced beyond the existing health check.

| Endpoint | Used By | TanStack Query Hook | MSW Handler |
|:---|:---|:---|:---|
| `GET /api/v1/health/celery` | `(dev)/health/page.tsx` only | No hook — raw `apiClient.get()` call (dev-only surface, not subject to TanStack Query conventions) | `apps/web/src/mocks/handlers/health.ts` — returns `{ status: "healthy", workers_active: 2, broker_connected: true, scheduled_tasks: 14, timestamp: "..." }` |

**Schema reference**: `operations['check_celery_health_api_v1_health_celery_get']` in `api-schema.d.ts` — confirmed present in the generated types.

**FE-B0 establishes the API infrastructure** consumed by all subsequent batches:
- `apiClient` in `packages/shared-api/src/client.ts` — all surface API calls route through this
- `createQueryClient()` in `packages/shared-api/src/queryClient.ts` — all `<QueryClientProvider>` instances use this factory
- MSW handler authoring convention: `apps/{web|mobile}/src/mocks/handlers/{domain}.ts` organized by backend domain

---

## E. Pattern Reuse Decisions

FE-B0 establishes the foundational primitives that every §16 cross-cutting pattern depends on. No §16 patterns are directly consumed in FE-B0 surfaces, but these are the infrastructure enablers:

| §16 Pattern | FE-B0 Dependency Established |
|:---|:---|
| §16.3 Confirm-as-turn (voice) | `<AuthProvider>` boundary ensures voice surfaces have authenticated context |
| §16.4 Pre-commit staleness check | `apiClient` JWT interceptor ensures 409 responses reach the retry hook (FE-B4+) correctly authenticated |
| §16.6 Four-class severity | `apiClient` RFC 7807 error parser (established in `client.ts`) will decode `severity` field for future `<NotificationBanner>` wiring |
| §16.8 Optimistic UI with pending badges | TanStack Query `QueryClient` defaults (established in `queryClient.ts`) set `retry: 1`, `staleTime: 5min` |
| §16.11 Mobile-to-web escalation | `<RoleGate>` hide-not-disable pattern; owner-only content hidden at component level |
| §16.13 In-flight sync indicator | `<RoleGate>` and routing skeleton provide the layout slots the sync indicator will occupy in FE-B4/FE-B7 |

**Pattern established in FE-B0 that all batches consume**:

```typescript
// Hide-not-disable RBAC — established here, consumed by every subsequent surface
import { RoleGate, useRequiresPermission } from '@pilot/ui/role-gate';

// Wrapper form:
<RoleGate role="owner">
  <OwnerOnlyContent />   // not rendered, not disabled — simply absent from DOM
</RoleGate>

// Inline form:
const canApprove = useRequiresPermission('quotes.approve');
{canApprove && <ApproveButton />}
```

---

## F. Shared Module Interfaces

### F.1 Auth Module — `packages/ui/src/auth/`

```typescript
// packages/ui/src/auth/types.ts
export type PilotRole = 'owner' | 'tech' | 'office_staff' | 'operator';

export interface PilotUser {
  id: string;
  email: string;
  role: PilotRole;
  tenantId: string;
  displayName: string;
  accessToken: string;
}

export interface AuthContextValue {
  user: PilotUser | null;
  isAuthenticated: boolean;
  role: PilotRole | null;
  signIn: (email: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
  refreshSession: () => Promise<string>;  // Returns fresh accessToken
}

// packages/ui/src/auth/AuthProvider.tsx
export interface AuthProviderProps {
  children: React.ReactNode;
  /**
   * When set (dev only via USE_MOCK_AUTH=true), bypasses Cognito and returns
   * a fake user with the given role. Never set in production.
   */
  mockUser?: Pick<PilotUser, 'role' | 'email' | 'displayName'>;
}

// packages/ui/src/auth/useAuth.ts
export function useAuth(): AuthContextValue;

// packages/ui/src/auth/RequireAuth.tsx
export interface RequireAuthProps {
  children: React.ReactNode;
  redirectTo: string;  // '/login' for web; login screen name for mobile
}
```

### F.2 Role Gate Module — `packages/ui/src/role-gate/`

```typescript
// packages/ui/src/role-gate/permissions.ts
export type PermissionKey =
  | 'quotes.approve'
  | 'quotes.reject'
  | 'quotes.kickback'
  | 'dispatch.move'
  | 'dispatch.assign'
  | 'customers.delete'
  | 'settings.manage'
  | 'reports.view'
  | 'comms.send'
  | 'invoices.approve';
  // Extended by each batch as new permissions are introduced

export const ROLE_PERMISSION_MAP: Record<PilotRole, Set<PermissionKey>> = {
  owner: new Set([/* all permissions */]),
  office_staff: new Set(['quotes.approve', 'quotes.reject', 'dispatch.assign', 'customers.delete', 'comms.send', 'invoices.approve', 'reports.view']),
  tech: new Set(['comms.send']),
  operator: new Set([/* all + admin-only */]),
};

// packages/ui/src/role-gate/RoleGate.tsx
export interface RoleGateProps {
  role: PilotRole | PilotRole[];   // If array, renders if user has ANY of the listed roles
  children: React.ReactNode;
}
export function RoleGate({ role, children }: RoleGateProps): JSX.Element | null;

// packages/ui/src/role-gate/useRequiresPermission.ts
export function useRequiresPermission(permission: PermissionKey): boolean;
```

### F.3 API Client — `packages/shared-api/src/client.ts`

```typescript
// The interceptors added in FE-B0:

// Request interceptor — attaches JWT + tenant ID
apiClient.interceptors.request.use(async (config) => {
  try {
    const session = await fetchAuthSession();  // AWS Amplify v6
    const token = session.tokens?.idToken?.toString();
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`;
    }
  } catch {
    // Not authenticated — let request through; backend will 401
  }
  return config;
});

// Response interceptor — catches 401, refreshes, retries once
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401 && !error.config._retried) {
      error.config._retried = true;
      try {
        const session = await fetchAuthSession({ forceRefresh: true });
        const token = session.tokens?.idToken?.toString();
        if (token) {
          error.config.headers['Authorization'] = `Bearer ${token}`;
          return apiClient(error.config);
        }
      } catch {
        // Refresh failed — caller handles signout
      }
    }
    return Promise.reject(error);
  }
);
```

### F.4 Query Client Factory — `packages/shared-api/src/queryClient.ts`

```typescript
import { QueryClient } from '@tanstack/react-query';

export function createQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 1000 * 60 * 5,    // 5 minutes — per methods doc §4.1
        retry: 1,
        refetchOnWindowFocus: true,
      },
      mutations: {
        retry: 0,
      },
    },
  });
}
```

### F.5 `packages/ui/package.json` Exports Map

```json
{
  "name": "@pilot/ui",
  "exports": {
    "./tokens": "./src/tokens.ts",
    "./tailwind.preset": "./tailwind.preset.ts",
    "./styles/globals.css": "./src/styles/globals.css",
    "./auth": "./src/auth/index.ts",
    "./role-gate": "./src/role-gate/index.ts",
    "./hooks": "./src/hooks/index.ts",
    "./*": "./src/*.tsx"
  }
}
```

> **Note**: The wildcard `./*` handles individual component files during FE-B1+ growth (e.g., `@pilot/ui/states`, `@pilot/ui/notification-banner`). As new category `index.ts` files are created, they are added to the `exports` map explicitly for clean tree-shaking.

---

## G. Open Questions Resolved

### G-1: V3 Fix — Wire `pilotPreset` into `apps/web`

**Root cause**: `apps/web` uses Tailwind v4 with CSS-first configuration (`@import "tailwindcss"` in `globals.css`, no `tailwind.config.ts`). The `pilotPreset` in `packages/ui/tailwind.preset.ts` is a standard JS config object (`Partial<Config>`) that must be referenced via Tailwind v4's `@config` directive to take effect.

**Exact fix — 3 file changes**:

**Change 1**: Create `frontend/apps/web/tailwind.config.ts`:
```typescript
import type { Config } from "tailwindcss";
import { pilotPreset } from "@pilot/ui/tailwind.preset";

export default {
  presets: [pilotPreset],
  content: [
    "./src/**/*.{ts,tsx}",
    "../../packages/ui/src/**/*.{ts,tsx}",
  ],
} satisfies Config;
```

**Change 2**: Update `frontend/apps/web/src/app/globals.css` — add `@config` directive on line 2:
```css
@import "tailwindcss";
@config "../../tailwind.config.ts";

/* Replace the placeholder :root vars with references to packages/ui/src/styles/globals.css
   token-sourced CSS variables. The pilot CSS variables are defined there and imported here. */
@import "@pilot/ui/styles/globals.css";
```

**Change 3**: Update `frontend/packages/ui/src/styles/globals.css` to define the full shadcn/ui-compatible CSS variable set sourced from `tokens.ts` (e.g., `--background`, `--foreground`, `--primary`, `--ring`, etc.). The current `globals.css` in `apps/web` uses hardcoded hex values (`--background: #ffffff`) that will be replaced by token-sourced variables.

> **Build verification**: After these 3 changes, run `pnpm --filter web build`. Token-sourced Tailwind utility classes (`bg-brand-600`, `text-neutral-900`, `text-fault-600`, etc.) must be available. Also run `pnpm --filter marketing build` to confirm no regressions.

---

### G-2: Hello World Page — Preserve as Dev Route

**Decision**: **Preserve as `/(dev)/health/page.tsx`** behind `NEXT_PUBLIC_SHOW_DEV_ROUTES=true` env gate.

**Rationale**: The health check page (`checkApiHealth()` → Celery endpoint) is actively useful during FE development to verify the backend stack is running. It is the mechanism by which V5 (`curl http://localhost:8000/api/v1/health/celery`) was verified. Discarding it removes a valuable dev tool. Moving it to a dev route prevents it from affecting production routing or appearing as the root landing page.

**Implementation details**:
- Replace `apps/web/src/app/page.tsx` with a simple server component that redirects to `/dashboard` (authenticated) or `/login` (unauthenticated) — no `"use client"` needed
- Move health check content to `apps/web/src/app/(dev)/health/page.tsx`
- The `(dev)` route group does NOT get the `(authed)/layout.tsx` auth wrapper — it is accessible without login
- Gate rendering of the link to this route via `NEXT_PUBLIC_SHOW_DEV_ROUTES === 'true'` in the root layout's nav or a dedicated dev toolbar component
- In production (`NODE_ENV=production`), this page still exists at the route (it is not removed by build flags) but the link to it is hidden; acceptable for MVP since it is not indexed and carries no sensitive data

---

### G-3: JWT Interceptor Location — Shared in `packages/shared-api/`

**Decision**: **Shared in `packages/shared-api/src/client.ts`**.

**Rationale**: Both web and mobile use the same JWT flow (AWS Amplify `fetchAuthSession()` → Cognito ID token → `Authorization: Bearer`). The interceptor logic is identical. Duplicating it in each app's `lib/` creates drift risk — the first time someone fixes a token refresh edge case in web and forgets mobile is a production auth failure. The Axios instance already reads `NEXT_PUBLIC_API_URL || EXPO_PUBLIC_API_URL` in the same shared file, proving the pattern of cross-platform env-var handling in a shared module is established.

**Platform compatibility**: `aws-amplify` package is isomorphic — it runs in Node/browser/React Native. The `fetchAuthSession()` call works identically on both platforms.

---

### G-4: `shared-api` Growth Strategy — Domain-Based Modules from the Start

**Decision**: **Domain-based module files, established in FE-B0**.

**Module structure**:
```
packages/shared-api/src/
├── client.ts           # Axios instance (modified: adds JWT interceptor)
├── queryClient.ts      # QueryClient factory (new)
├── health.ts           # checkApiHealth() — migrated from index.ts
├── index.ts            # Re-exports from all domain modules
└── [FE-B3+]
    ├── quotes.ts       # useQuotes(), useCreateQuote(), etc.
    ├── voice.ts        # useVoiceSession(), etc.
    ├── scheduling.ts   # useDispatchBoard(), etc.
    ├── communications.ts
    └── ...
```

**Rationale**: The `api-schema.d.ts` (32,030 lines) already organizes paths by domain prefix (`/api/v1/quotes/*`, `/api/v1/schedule/*`, `/api/v1/communications/*`). The domain module structure mirrors this. Imports are cleaner: `import { checkApiHealth } from '@pilot/shared-api/health'` vs. a growing monolithic file. Adding TanStack Query hooks in FE-B3+ is a matter of creating the domain file — no refactor of existing code.

**`index.ts` barrel pattern**: `index.ts` re-exports everything via `export * from './health'; export * from './client'; export * from './queryClient';` so existing consumers of `@pilot/shared-api` (like `apps/web/src/app/page.tsx`) continue to work unchanged.

---

### G-5: Marketing App Build Safety

**Decision**: **Add `pnpm --filter marketing build` to the FE-B0 batch completion gate checklist** (§5 Phase 3 of the impl plan). Run it before AND after FE-B0 changes.

**Risk assessment of FE-B0 changes on `apps/marketing/`**:

| FE-B0 Change | Marketing App Risk | Mitigation |
|:---|:---|:---|
| Rename `@repo/ui` → `@pilot/ui` | ✅ None — `apps/marketing/` has no `@repo/ui` imports (verified by grep) | No action needed |
| `packages/ui/package.json` exports field change | ✅ None — marketing doesn't import from `@repo/ui` | No action needed |
| `packages/eslint-config` rule addition | ⚠️ Low — marketing has its own `eslint.config.mjs`; shared config is `eslint-config/next.js` | Verify `pnpm --filter marketing lint` passes |
| `packages/shared-types` — no changes in FE-B0 | ✅ None | — |
| `packages/shared-api` restructure | ✅ None — marketing doesn't import from `@pilot/shared-api` (verified by grep) | No action needed |
| TanStack Query install (web + mobile only) | ✅ None — scope-filtered to web and mobile apps | No action needed |

**Marketing app build gate command to add to FE-B0 completion checklist**:
```bash
pnpm --filter marketing build
```

---

### G-6: `packages/ui` Export Strategy — Per-Category Imports

**Decision**: **Per-category imports via `package.json` `"exports"` field** (see §F.5 for the exact exports map).

**Rationale**: FE-B1 alone adds ~25 new components. A single `index.ts` barrel at that scale creates poor tree-shaking and slow TypeScript resolution for consumers. Per-category exports (`@pilot/ui/states`, `@pilot/ui/notification-banner`, `@pilot/ui/role-gate`) mirror the folder structure in `packages/ui/src/` and match the methods doc §7.3 structure description. Each category folder has an `index.ts` that is added to the `exports` map in `package.json` when the category is created.

**Migration path for current `"./*": "./src/*.tsx"` wildcard**: The wildcard remains as a fallback for individual component files during the transition. As category folders with `index.ts` files are created (starting in FE-B1 with `states/`, `notification-banner/`, etc.), those explicit exports shadow the wildcard for their paths. The wildcard catches anything not yet given a named export.

**Components currently in `packages/ui/src/` that need individual exports added**:
- `button.tsx` → covered by wildcard `./button`
- `card.tsx` → covered by wildcard `./card`
- `code.tsx` → covered by wildcard `./code`
- `tokens.ts` → **explicitly added**: `"./tokens": "./src/tokens.ts"` (cannot be covered by `.tsx` wildcard)
- `styles/globals.css` → **explicitly added**: `"./styles/globals.css": "./src/styles/globals.css"`

---

### G-7: `gluestack-config.ts` Export Name Discrepancy

**Finding**: `apps/mobile/theme/gluestack-config.ts` exports `pilotConfig` (and `type PilotConfig`). The current `apps/mobile/app/_layout.tsx` does NOT yet import from this file — it still uses `@react-navigation/native` `DarkTheme`/`DefaultTheme` and has no `<GluestackUIProvider>`. FE-B0 Item 1 must add `<GluestackUIProvider config={pilotConfig}>` to `app/_layout.tsx`.

**Exact `_layout.tsx` update** (FE-B0 Item 1, mobile side):
```typescript
import { GluestackUIProvider } from '@gluestack-ui/themed';
import { pilotConfig } from '@/theme/gluestack-config';

// Add inside return:
<GluestackUIProvider config={pilotConfig} colorMode={colorScheme === 'dark' ? 'dark' : 'light'}>
  <ThemeProvider ...>
    ...
  </ThemeProvider>
</GluestackUIProvider>
```

---

## H. External Dependency Status

| Dependency | Blocks | Mock Strategy | Status | Tom Action |
|:---|:---|:---|:---|:---|
| **AWS Cognito user pool** | FE-B0 production auth (FE-B2+ surfaces) | `MockAuthProvider` returning fake `PilotUser` (role configurable via `NEXT_PUBLIC_USE_MOCK_AUTH=true`) | ⚠️ Not yet provisioned | Provision Cognito user pool before FE-B2 production deployment; FE-B0 + FE-B1 proceed with mock |
| **AWS Amplify CLI** | Amplify `configure()` call with real pool IDs | Dev env vars `NEXT_PUBLIC_COGNITO_USER_POOL_ID=mock-pool` fallback; `MockAuthProvider` short-circuits Amplify calls | ⚠️ Not yet configured | Configure before FE-B2 production delivery |
| **`@gluestack-ui/themed`** (mobile) | Item 12 (mobile layout update) | Already in `apps/mobile/package.json` per Phase 0 scaffolding | ✅ Available | No action |
| **`@tanstack/react-query`** | Item 3 (TanStack Query baseline) | Not yet installed — FE-B0 installs it | ⏳ Install in FE-B0 | No action needed pre-FE-B0 |
| **MSW** | Item 4 (MSW setup) | Not yet installed — FE-B0 installs it | ⏳ Install in FE-B0 | No action needed pre-FE-B0 |
| **`aws-amplify`** | Item 9 (Cognito auth scaffolding) | `MockAuthProvider` bypasses Amplify for `USE_MOCK_AUTH=true` | ⏳ Install in FE-B0 | No action needed pre-FE-B0 |

**Packages to install in FE-B0** (add to `apps/web/package.json` and `apps/mobile/package.json` as appropriate):

```bash
# Web
pnpm --filter web add @tanstack/react-query @tanstack/react-query-devtools aws-amplify

# Mobile
pnpm --filter mobile add @tanstack/react-query aws-amplify

# Dev (web only — MSW has separate browser and node packages)
pnpm --filter web add -D msw
pnpm --filter mobile add -D msw
```

---

## I. Test Plan

### I.1 Unit Tests (target: 30+)

Test files and coverage targets:

| Test File | Component/Hook | Key Scenarios |
|:---|:---|:---|
| `packages/ui/src/auth/useAuth.test.ts` | `useAuth()` | (1) Returns `null` user when not authenticated; (2) Returns correct `PilotUser` after mock sign-in; (3) `signOut()` clears context |
| `packages/ui/src/auth/AuthProvider.test.tsx` | `<AuthProvider>` | (1) Renders children; (2) With `mockUser` prop, `useAuth()` returns mock user; (3) Without `mockUser`, Amplify is invoked |
| `packages/ui/src/auth/RequireAuth.test.tsx` | `<RequireAuth>` | (1) Renders children when authenticated; (2) Redirects to `redirectTo` when not authenticated; (3) Shows loading state during auth check |
| `packages/ui/src/role-gate/RoleGate.test.tsx` | `<RoleGate>` | (1) Renders children when user role matches; (2) Returns `null` (no DOM node) when role does not match; (3) Array of roles: renders if user has ANY; (4) `operator` role has access to owner-level content |
| `packages/ui/src/role-gate/useRequiresPermission.test.ts` | `useRequiresPermission()` | (1) Returns `true` for owner + `quotes.approve`; (2) Returns `false` for tech + `quotes.approve`; (3) Returns `true` for owner + every key in PermissionKey; (4) Returns `false` for tech + `dispatch.move` |
| `packages/ui/src/role-gate/permissions.test.ts` | `ROLE_PERMISSION_MAP` | (1) Owner has all permissions; (2) Tech has only `comms.send`; (3) Adding a permission key to registry updates the type check |
| `packages/shared-api/src/client.test.ts` | `apiClient` interceptors | (1) JWT attached when `fetchAuthSession` returns token; (2) No JWT header when not authenticated; (3) 401 triggers refresh + retry; (4) Failed refresh rejects with original error; (5) Request includes `Content-Type: application/json` |
| `packages/shared-api/src/queryClient.test.ts` | `createQueryClient()` | (1) Returns `QueryClient` instance; (2) `staleTime` defaults to 300,000ms; (3) Query `retry` is 1; (4) Mutation `retry` is 0 |
| `packages/eslint-config/rules/no-hardcoded-design-values.test.ts` | ESLint rule | (1) Flags `#1a1a1a` in component file; (2) Allows `bg-brand-600` class; (3) Flags `padding: 13px` (not on 4px scale); (4) Allows `padding: 16px` (spacing[4]); (5) Flags `rgb(59, 67, 214)` |

**Approximate unit test count**: 5 (useAuth) + 3 (AuthProvider) + 3 (RequireAuth) + 4 (RoleGate) + 4 (useRequiresPermission) + 3 (permissions) + 5 (apiClient interceptors) + 4 (queryClient) + 5 (ESLint rule) = **36 unit tests**

### I.2 Integration Tests (target: 5+)

File path: `apps/web/__tests__/batch_fe_b0/` and `apps/mobile/__tests__/batch_fe_b0/`

| Test File | Surface | Scenarios |
|:---|:---|:---|
| `apps/web/__tests__/batch_fe_b0/routing.integration.test.tsx` | Web routing skeleton | (1) Unauthenticated user navigating to `/dashboard` is redirected to `/login`; (2) Mock-authenticated user navigating to `/dashboard` sees "Dashboard" placeholder; (3) All 11 sections render their section name without crashing; (4) Navigation between sections via link preserves auth state |
| `apps/web/__tests__/batch_fe_b0/msw.integration.test.tsx` | MSW + apiClient | (1) Health endpoint intercepted by MSW handler returns mocked response; (2) MSW disabled when `USE_MSW_MOCKS=false`; (3) `apiClient` attaches JWT header visible to MSW handler via `request.headers` |
| `apps/web/__tests__/batch_fe_b0/role-gate.integration.test.tsx` | `<RoleGate>` in layout context | (1) Owner user sees all navigation sections; (2) Tech user does not see Owner-gated content; (3) `<RequireAuth>` layout redirect fires correctly on session expiry |
| `apps/mobile/__tests__/batch_fe_b0/tabs.integration.test.tsx` | Mobile 5-tab layout | (1) All 5 tabs render without crash; (2) Owner tab content hidden for tech role; (3) Tab navigation works; (4) `<GluestackUIProvider>` wraps correctly — token-sourced color accessible in child component |
| `apps/web/__tests__/batch_fe_b0/dev-health.integration.test.tsx` | `(dev)/health` page | (1) Health page renders backend status from MSW mock; (2) `NEXT_PUBLIC_SHOW_DEV_ROUTES=false` removes link to dev route from nav; (3) Root `/` redirects mock-authenticated user to `/dashboard` |

**Integration test count**: ~5–7 per file × 5 files = **approx. 25 integration test cases** (minimum 5 integration test files passing the batch gate)

### I.3 E2E Tests (target: 1+)

File path: `apps/web/e2e/batch_fe_b0/`

| Test File | Flow | Steps |
|:---|:---|:---|
| `apps/web/e2e/batch_fe_b0/foundation-smoke.e2e.spec.ts` | Web foundation smoke | (1) Navigate to `http://localhost:3000`; (2) Assert redirect to `/login`; (3) Mock-authenticate (via `USE_MOCK_AUTH=true` env); (4) Assert land on `/dashboard`; (5) Assert "Dashboard" placeholder visible; (6) Navigate to `/schedule` — assert renders; (7) Navigate to `/settings` — assert renders; (8) Assert no TypeScript errors (`pnpm typecheck` in pre-test hook); (9) Assert ESLint passes with zero warnings on all FE-B0 files |

**E2E test count**: 1 spec file with ~9 assertions = satisfies the "1+" target.

### I.4 Accessibility Audit Checkpoints

| Surface | Audit Type | Gate |
|:---|:---|:---|
| All 11 web placeholder pages | `axe-core` in integration test | Zero violations — placeholder pages are minimal but must have correct `<main>`, `<h1>`, landmark structure |
| All 5 mobile tab placeholder screens | Manual audit + `@axe-core/react-native` where supported | `accessibilityLabel` on tab bar items; tab focus order correct |
| `<RoleGate>` | Unit test ARIA | Confirm hidden content truly absent from DOM (not `display:none`) — axe sees what the DOM sees |

### I.5 Token Validation Gate

Before marking FE-B0 complete, run:
```bash
pnpm lint   # ESLint no-hardcoded-design-values rule — must pass with ZERO warnings
pnpm typecheck   # TypeScript strict mode — zero errors
pnpm build       # Web build — zero errors
pnpm --filter marketing build   # Marketing app regression check
```

---

## Appendix: File Change Summary

**Net-new files** created in FE-B0:

```
packages/ui/src/auth/
  AuthProvider.tsx
  RequireAuth.tsx
  useAuth.ts
  types.ts
  index.ts

packages/ui/src/role-gate/
  RoleGate.tsx
  useRequiresPermission.ts
  permissions.ts
  index.ts

packages/ui/src/hooks/
  index.ts    (placeholder — hooks added in FE-B1+)

packages/shared-api/src/
  queryClient.ts
  health.ts   (migrated from index.ts)

packages/eslint-config/rules/
  no-hardcoded-design-values.ts

apps/web/
  tailwind.config.ts
  src/app/providers.tsx
  src/app/(authed)/layout.tsx
  src/app/(authed)/dashboard/page.tsx
  src/app/(authed)/schedule/page.tsx
  src/app/(authed)/customers/page.tsx
  src/app/(authed)/quotes/page.tsx
  src/app/(authed)/invoices/page.tsx
  src/app/(authed)/reports/page.tsx
  src/app/(authed)/comms/page.tsx
  src/app/(authed)/operations/page.tsx
  src/app/(authed)/sync/page.tsx
  src/app/(authed)/notifications/page.tsx
  src/app/(authed)/settings/page.tsx
  src/app/(dev)/health/page.tsx
  src/app/login/page.tsx   (placeholder — implemented in FE-B2)
  src/mocks/browser.ts
  src/mocks/handlers/health.ts
  src/mocks/handlers/index.ts
  __tests__/batch_fe_b0/routing.integration.test.tsx
  __tests__/batch_fe_b0/msw.integration.test.tsx
  __tests__/batch_fe_b0/role-gate.integration.test.tsx
  __tests__/batch_fe_b0/dev-health.integration.test.tsx
  e2e/batch_fe_b0/foundation-smoke.e2e.spec.ts

apps/mobile/
  mocks/server.ts
  mocks/handlers/health.ts
  mocks/handlers/index.ts
  app/(authed)/_layout.tsx
  app/(tabs)/jobs.tsx         (renamed from explore.tsx)
  app/(tabs)/customers.tsx
  app/(tabs)/calcs.tsx
  app/(tabs)/owner.tsx
  __tests__/batch_fe_b0/tabs.integration.test.tsx
```

**Modified files**:
```
packages/ui/package.json                     # name → @pilot/ui; exports field expanded
packages/ui/src/styles/globals.css           # Add token-sourced CSS variables
packages/shared-api/src/client.ts            # Add JWT + 401 interceptors
packages/shared-api/src/index.ts             # Refactor to re-export from domain modules
apps/web/src/app/globals.css                 # Add @config, replace hardcoded vars
apps/web/src/app/layout.tsx                  # Add RootProviders wrapper; update metadata
apps/web/src/app/page.tsx                    # Replace with authenticated redirect
apps/mobile/app/_layout.tsx                  # Add GluestackUIProvider + QueryClientProvider
apps/mobile/app/(tabs)/_layout.tsx           # Restructure to 5 tabs with correct icons
```

---

*Design session complete. This document is the authoritative handoff to the Pilot React Engineer for FE-B0 Phase 2 implementation. All 6 architectural decisions are resolved; V3 failure has an exact 3-change fix specified. No unresolved interaction questions remain.*
