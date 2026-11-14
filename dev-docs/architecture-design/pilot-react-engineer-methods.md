# Pilot for Trades React Engineer Methods — Frontend Coding Standards & Patterns

> **Snapshot note:** historical working document, published as last edited during the build and not maintained. Statuses and figures below reflect that date; for current, checked figures see [`PROVENANCE.md`](../../PROVENANCE.md) and [`dev-docs/diligence/`](../diligence/README.md). The product was never released and never carried customer traffic. "Prod" here means the one pre-release AWS environment, used for the author's own tests.

**Version**: 2.2
**Date**: August 20, 2026
**Status**: Aligned to `pilot-app-mvp-frontend-arch-impl-plan.md` v3.0 and `pilot-app-mvp-frontend-impl-plan.md` v1.0. Updated May 21, 2026: 8 codebase alignment fixes applied (shared-types naming, mobile path structure, Gluestack config location, token excerpt format, Tailwind import name, marketing app in tree, catalog version note). **v2.2 refresh review (2026-08-20, Architect)**: targeted review of the highest-drift-risk sections (§3 tech stack, §6 tokens, §10 API integration/MSW, §14 testing, anti-patterns + checklists) against `.roo/rules-pilot-react-engineer/react-engineer-rules.md` (§1–§36, the authority) and the confirmed stack (Next.js 16.2, React 19.2 + React Compiler, TanStack Query v5, Zod v4, RHF 7, Tailwind v4, Vitest 2, MSW 2, pnpm 9 + Turborepo) — **no contradictions found**; this doc remains the how-to catalog companion to the rules file. Registered in `pilot-docs-list.md` §2 the same date.
**Audience**: The Pilot React Engineer mode (and any human contributor working in the frontend)
**Purpose**: This document is the canonical workflow + standards reference for all frontend implementation tasks. The implementation plan tells you **what** to build and **when**; this document tells you **how** to build each item.

---

## Table of Contents

1. [Project Structure Reference](#1-project-structure-reference)
2. [Environment Setup](#2-environment-setup)
   - [2.5 Mobile Three-Runtime Architecture](#25-mobile-three-runtime-architecture--critical-dev-setup-rules)
3. [Tech Stack Reference](#3-tech-stack-reference)
4. [State Management Architecture](#4-state-management-architecture)
5. [Authentication & Authorization](#5-authentication--authorization)
6. [Design Tokens & Visual System](#6-design-tokens--visual-system)
7. [UI Component Standards](#7-ui-component-standards)
   - [7.4 Mobile StyleSheet Patterns](#74-mobile-stylesheet-patterns-react-nativespecific)
8. [Shared Component Catalog](#8-shared-component-catalog)
9. [Platform Patterns Reference](#9-platform-patterns-reference)
10. [API Integration & Mock-Driven Development](#10-api-integration--mock-driven-development)
    - [10.7 Mobile MSW Handler URL Pattern](#107-mobile-msw-handler-url-pattern--wildcard-required)
    - [10.7 Metro Bundle Rules](#107-metro-bundle-rules--preventing-native-code-from-entering-the-web-bundle)
11. [Mobile Offline Database: WatermelonDB](#11-mobile-offline-database-watermelondb)
    - [11.4 WatermelonDB Adapter Selection](#114-watermelondb-adapter-selection--use-lokijs-for-dev-builds-and-web)
    - [11.5 WatermelonDB Babel Configuration](#115-watermelondb-field-decorators--babel-configuration)
12. [Voice AI & Audio Streaming Pipeline](#12-voice-ai--audio-streaming-pipeline)
13. [Accessibility Standards](#13-accessibility-standards)
14. [Testing Strategy & Automation](#14-testing-strategy--automation)
15. [Common Anti-Patterns — Never Do These](#15-common-anti-patterns--never-do-these)
16. [Standard Implementation Task Workflow](#16-standard-implementation-task-workflow)
17. [Stop & Rollback Conditions](#17-stop--rollback-conditions)
18. [Definition of Done Checklist](#18-definition-of-done-checklist)

---

## 1. Project Structure Reference

The frontend is a **Turborepo monorepo** containing two apps (web + mobile) and shared packages. Per `pilot-app-mvp-frontend-arch-impl-plan.md` v3.0 §4.

```text
frontend/                                 # Turborepo root
├── apps/
│   ├── web/                              # Next.js 16 owner/office dashboard
│   │   ├── src/
│   │   │   ├── app/                      # Next.js App Router (file-based routing)
│   │   │   ├── features/                 # Feature folders (per surface)
│   │   │   │   └── {kebab-surface}/      # e.g., quote-approval/, dispatch-board/
│   │   │   │       ├── components/
│   │   │   │       ├── hooks/
│   │   │   │       └── api/              # TanStack Query hooks for this surface
│   │   │   ├── hooks/                    # Web-specific shared hooks
│   │   │   ├── lib/                      # apiClient, utility helpers
│   │   │   └── mocks/                    # MSW handlers (dev + tests)
│   │   │       └── handlers/             # Per backend domain
│   │   ├── __tests__/                    # Integration tests (batch-scoped)
│   │   │   └── batch_fe_b{N}/            # e.g., batch_fe_b4/dispatch.integration.test.tsx
│   │   ├── e2e/                          # Playwright e2e tests
│   │   │   └── batch_fe_b{N}/            # e.g., batch_fe_b4/dispatch.e2e.spec.ts
│   │   └── tailwind.config.ts            # Extends packages/ui Tailwind preset
│   │
│   ├── mobile/                           # Expo SDK 54 React Native field-tech app
│   │   ├── app/                          # Expo Router (file-based routing — no src/ prefix)
│   │   ├── features/                     # Same structure as web (created during FE-B2+)
│   │   ├── database/                     # WatermelonDB (created during FE-B7)
│   │   │   ├── schema.ts
│   │   │   ├── models/                   # Job, TimeEntry, Expense, etc.
│   │   │   └── sync/                     # orchestrator.ts, conflict-handlers.ts
│   │   ├── hooks/                        # Mobile-specific hooks (audio, offline, push)
│   │   ├── theme/                        # Gluestack config consuming tokens
│   │   │   └── gluestack-config.ts       # Imports from @pilot/ui/tokens
│   │   ├── lib/                          # apiClient, utilities
│   │   ├── mocks/                        # MSW handlers (with React Native polyfills)
│   │   ├── __tests__/                    # Integration tests (batch-scoped)
│   │   └── e2e/                          # Maestro e2e tests
│   │
│   └── marketing/                        # Next.js 16 static-export marketing site (separate workstream)
│       └── ...                           # Not part of product frontend batches; see marketing-site-impl-plan.md
│
├── packages/
│   ├── ui/                               # Shared component library (web + mobile)
│   │   ├── src/
│   │   │   ├── tokens.ts                 # Pass 1 design tokens (TS module)
│   │   │   ├── tailwind.preset.ts        # Tailwind preset consuming tokens (exports `pilotPreset`)
│   │   │   ├── globals.css               # CSS variable definitions (web)
│   │   │   ├── states/                   # <EmptyState>, <LoadingState>, <ErrorState>, FTU variants
│   │   │   ├── notification-banner/      # <NotificationBanner>
│   │   │   ├── sync-indicator/           # <InFlightSyncIndicator>
│   │   │   ├── diff-view/                # <DiffView> (track-changes amber/green/red)
│   │   │   ├── voice-confirm-turn/       # <VoiceConfirmTurn>
│   │   │   ├── message-preview/          # <MessagePreviewModal> + usePreviewBeforeSend()
│   │   │   ├── pending-badge/            # <PendingBadge> + useOptimisticMutation()
│   │   │   ├── setting-control/          # <SettingControl>, <RevertToDefaultDialog>, <EffectiveSettingDisplay>
│   │   │   ├── integration-conflict/     # <IntegrationConflictResolver>
│   │   │   ├── role-gate/                # <RoleGate> + useRequiresPermission()
│   │   │   ├── stripe-payment/           # <StripePaymentForm>
│   │   │   ├── hooks/                    # Cross-platform hooks (useStalenessRetry, useFormSaveStrategy, etc.)
│   │   │   └── index.ts                  # Barrel export — single source of public API
│   │   └── __tests__/                    # Co-located component unit tests (Vitest)
│   │
│   ├── eslint-config/                    # Custom ESLint rules
│   │   └── rules/
│   │       └── no-hardcoded-design-values.ts   # Enforces Pass 1 token consumption
│   │
│   ├── tsconfig/                         # Shared tsconfig presets
│   │
│   └── shared-types/                     # Auto-generated TypeScript types from backend OpenAPI
│       └── src/
│           └── api-schema.d.ts           # Generated by `pnpm sync-api-types`
│
├── turbo.json                            # Turborepo task pipeline
├── pnpm-workspace.yaml                   # pnpm workspaces
└── package.json
```

**Critical placement rules**:

| Code goes... | If... |
|:---|:---|
| `packages/ui/src/{category}/` | Component or hook is consumed by both web AND mobile |
| `packages/ui/src/{category}/web/` and `.../mobile/` | Component needs platform-specific implementation but shared API |
| `apps/web/src/features/{surface}/components/` | Component is web-only AND used by exactly one surface |
| `apps/mobile/src/features/{surface}/components/` | Same, mobile-only |
| `apps/{web,mobile}/src/hooks/` | Hook is platform-specific AND used across multiple surfaces |
| `apps/{web,mobile}/src/lib/` | Pure utility (formatters, validators) used across surfaces |

If you're tempted to put a shared component in `apps/`, **stop**. It belongs in `packages/ui/`.

---

## 2. Environment Setup

You must always confirm you are at the correct directory before running commands.

```bash
# From the Turborepo root:

# Install all workspace dependencies (run from root)
pnpm install

# Run web dev server
pnpm --filter web dev

# Run mobile dev server
pnpm --filter mobile dev          # alias for: cd apps/mobile && npx expo start --clear

# ── TEST COMMANDS — READ THIS CAREFULLY ─────────────────────────────────────
#
# ❌ BANNED: npx vitest run ...
#    DO NOT USE "npx vitest run", "cd apps/web && npx vitest", or any npx vitest variant.
#    npx vitest bypasses Turborepo workspace config → monorepo module resolution fails.
#    This is a permanently banned command. Using it wastes time on false failures.
#
# ✅ CORRECT test commands:
pnpm --filter @pilot/ui test      # packages/ui shared components (Vitest via workspace)
pnpm --filter web test            # apps/web (Vitest via workspace) ← ONLY correct web command
pnpm --filter mobile test         # apps/mobile (Jest via workspace)

# ✅ Run a single test file (web):
pnpm --filter web test -- apps/web/src/__tests__/[batch]/[file].test.tsx 2>&1 | tail -10

# ✅ Run all tests in a batch folder (web):
pnpm --filter web test -- apps/web/src/__tests__/[batch]/ 2>&1 | tail -10

# ✅ Run a single test file (mobile):
pnpm --filter mobile test -- [path/to/test.tsx] 2>&1 | tail -10

# Marketing site — pnpm --filter marketing test (31 tests) and lint
pnpm --filter marketing lint

# ── FULL VERIFICATION COMMAND (type-check + lint + all tests) ──────────────
# Run this as the final regression check before marking any batch complete.
# Copy and paste the entire block as a single command:
cd <repo>/frontend && echo "=== UI - Type Check ===" && pnpm --filter @pilot/ui check-types && echo "=== Web - Type Check ===" && pnpm --filter web check-types && echo "=== Mobile - Type Check ===" && pnpm --filter mobile build && echo "=== UI - Lint ===" && pnpm --filter @pilot/ui lint && echo "=== Web - Lint ===" && pnpm --filter web lint && echo "=== Mobile - Lint ===" && pnpm --filter mobile lint && echo "=== TYPE+LINT PASS ===" && echo "=== UI - Tests ===" && pnpm --filter @pilot/ui test 2>&1 | tail -6 && echo "=== Web - Tests ===" && pnpm --filter web test 2>&1 | tail -6 && echo "=== Mobile - Tests ===" && pnpm --filter mobile test 2>&1 | tail -8 && echo "=== MVP FINAL VERIFICATION COMPLETE ==="

# Run web e2e (Playwright)
pnpm --filter web e2e

# Run mobile e2e (Maestro — preferred; Detox available as fallback)
pnpm --filter mobile e2e

# Sync API types from backend OpenAPI spec (run after every backend deploy)
pnpm sync-api-types

# Lint everything (runs the no-hardcoded-design-values rule)
pnpm lint

# Type-check per workspace (no root typecheck script — run individually)
pnpm --filter @pilot/ui check-types   # packages/ui
pnpm --filter web check-types         # apps/web
pnpm --filter mobile build            # apps/mobile (build script runs tsc --noEmit)

# Run an isolated package or app:
pnpm --filter @pilot/ui test
pnpm --filter web test
pnpm --filter mobile test
```

**Environment variables** (`.env.local` in web; `.env` + `eas.json` in mobile):

```bash
# Web (apps/web/.env.local)
NEXT_PUBLIC_API_URL=http://localhost:8000      # Or staging/prod URL
NEXT_PUBLIC_WS_URL=ws://localhost:8000         # Or wss://...
NEXT_PUBLIC_USE_MSW_MOCKS=false                # true to enable MSW in dev
NEXT_PUBLIC_USE_MOCK_AUTH=false                # true for MockAuthProvider
NEXT_PUBLIC_COGNITO_USER_POOL_ID=...
NEXT_PUBLIC_COGNITO_CLIENT_ID=...
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_...

# Mobile (apps/mobile/.env)
EXPO_PUBLIC_API_URL=http://localhost:8000
EXPO_PUBLIC_WS_URL=ws://localhost:8000
EXPO_PUBLIC_USE_MSW_MOCKS=false
EXPO_PUBLIC_USE_MOCK_AUTH=false
EXPO_PUBLIC_COGNITO_USER_POOL_ID=...
EXPO_PUBLIC_COGNITO_CLIENT_ID=...
EXPO_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_...
```

**Never hardcode URLs**. Always use the env vars above.

---

### 2.5 Mobile Three-Runtime Architecture — Critical Dev Setup Rules

The mobile Expo app runs in **three distinct runtime contexts** that share the same `.env` file but behave completely differently. Every new mobile engineer must understand this before writing any code.

| Context | How it runs | Auth | API calls go to |
|:---|:---|:---|:---|
| **Mobile web** (`localhost:8081`) | `Platform.OS === 'web'`, browser via Expo Web | MSW browser worker intercepts | `EXPO_PUBLIC_API_URL` (LAN IP or localhost) |
| **Native simulator** (iOS/Android) | React Native + Metro bundle | Real Cognito (or MSW node in tests) | `EXPO_PUBLIC_API_URL` |
| **Physical device** (Expo Go / EAS build) | React Native device | Real Cognito always | `EXPO_PUBLIC_API_URL` must be LAN IP, not `127.0.0.1` |

#### 2.5.1 EXPO_PUBLIC_ Prefix is Mandatory — NEXT_PUBLIC_ is silently undefined

Metro only injects env vars prefixed with `EXPO_PUBLIC_*`. Any variable named `NEXT_PUBLIC_*` is silently `undefined` in the Expo bundle — **no error, no warning**.

```bash
# ❌ Silently undefined in Metro — Amplify receives empty strings
NEXT_PUBLIC_COGNITO_USER_POOL_ID=...
NEXT_PUBLIC_COGNITO_APP_CLIENT_ID=...

# ✅ Correctly injected by Metro
EXPO_PUBLIC_COGNITO_USER_POOL_ID=...
EXPO_PUBLIC_COGNITO_APP_CLIENT_ID=...
```

#### 2.5.2 `Amplify.configure()` Must Be the Very First Import

`apps/mobile/lib/amplify-config.ts` must be imported before any `aws-amplify/auth` usage. In `app/_layout.tsx`, the import order is locked:

```typescript
// app/_layout.tsx — MUST be in this exact order
import "react-native-get-random-values"; // crypto polyfill for Amplify SRP
import "../lib/amplify-config";           // Amplify.configure() + AsyncStorage storage
// ... all other imports after these two
```

#### 2.5.3 AsyncStorage Is Required as Amplify Token Storage on Native

Without `AsyncStorage` as Amplify's storage backend on React Native, tokens are stored in JS memory only. `fetchAuthSession()` called from the `apiClient` Axios interceptor on the next async tick returns empty tokens → **401 on every API call after successful login**.

```typescript
// lib/amplify-config.ts — mandatory pattern for native
const AsyncStorage = require("@react-native-async-storage/async-storage").default;
Amplify.configure(
  { Auth: { Cognito: { userPoolId, userPoolClientId, loginWith: { email: true } } } },
  { Storage: AsyncStorage },  // ← REQUIRED — without this, all post-login API calls 401
);
```

#### 2.5.4 Expo Go Cannot Use USER_SRP_AUTH — Use USER_PASSWORD_AUTH

`USER_SRP_AUTH` requires `@aws-amplify/react-native` (native pod linking). Expo Go cannot link native modules. Always use `USER_PASSWORD_AUTH` on React Native. Detect platform with `navigator.product === 'ReactNative'` (works in both Expo Go and production builds).

#### 2.5.5 EXPO_PUBLIC_USE_MOCK_AUTH Must Be Platform-Guarded Everywhere

`EXPO_PUBLIC_USE_MOCK_AUTH=true` is intended only for the web dev view (`localhost:8081`). Without a `Platform.OS === 'web'` guard, native builds skip real Cognito and disable all API calls — making the physical device non-functional.

```typescript
// ❌ WRONG — disables native API calls
const isMockMode = process.env.EXPO_PUBLIC_USE_MOCK_AUTH === "true";

// ✅ REQUIRED — web-only mock mode
const isMockMode = Platform.OS === "web" && process.env.EXPO_PUBLIC_USE_MOCK_AUTH === "true";
```

Every hook that uses `enabled: !isMockAuth` must apply this same guard (owner tab hooks, calendar hooks, field issue hooks).

#### 2.5.6 Backend Cognito Pool Must Always Match Frontend

When provisioning a new Cognito pool or migrating regions, update **both** `apps/mobile/.env` AND `backend/.env`. FastAPI verifies JWTs against the JWKS of its configured pool — a mismatch returns 401 on all authenticated endpoints even when the JWT is valid.

```bash
# apps/mobile/.env — must match backend exactly
EXPO_PUBLIC_COGNITO_USER_POOL_ID=us-east-1_XXXXXXXXX
EXPO_PUBLIC_COGNITO_REGION=us-east-1

# backend/.env — must match frontend exactly
COGNITO_USER_POOL_ID=us-east-1_XXXXXXXXX
COGNITO_REGION=us-east-1
```

Also update the comment in `lib/amplify-config.ts` to reflect the current pool — this comment is the canonical reference for which pool is active.

---

## 3. Tech Stack Reference

The canonical stack for the Pilot frontend, per `pilot-app-mvp-frontend-arch-impl-plan.md` v3.0 §3.

| Layer | Web | Mobile |
|:---|:---|:---|
| Language | TypeScript 5.x (strict mode) | TypeScript 5.x (strict mode) |
| Framework | Next.js 16 (App Router) | Expo SDK 54 (Expo Router) |
| UI primitives | shadcn/ui + Radix | Gluestack-UI |
| Styling | Tailwind CSS v4 (consuming Pass 1 token preset) | Gluestack styled-system (consuming Pass 1 tokens) |
| Server state | TanStack Query v5 | TanStack Query v5 |
| Client state | Zustand v5 | Zustand v5 |
| API client | Axios + auto-generated types from `packages/shared-types/` | Axios + auto-generated types from `packages/shared-types/` |
| Auth | AWS Amplify Auth (Cognito JS SDK) | AWS Amplify Auth (Cognito JS SDK) |
| Real-time | EventSource (SSE) + WebSocket (voice) | `react-native-sse` polyfill + WebSocket (voice) |
| Offline DB | n/a | WatermelonDB (JSI SQLite adapter) |
| Forms | React Hook Form + Zod | React Hook Form + Zod |
| Drag-drop | `react-dnd` (HTML5 backend) | n/a (no DnD on mobile MVP) |
| Charts | Recharts | Victory Native |
| Stripe | Stripe.js + Stripe Elements (`<StripePaymentForm>` wrapper) | Stripe React Native |
| API mocking | MSW (browser worker) | MSW (Node-based via `msw/node` + RN polyfills) |
| Unit tests | Vitest + `@testing-library/react` | Jest + `@testing-library/react-native` |
| E2E tests | Playwright | Maestro (preferred) / Detox (fallback) |
| Accessibility audit | `@axe-core/react` | `@axe-core/react-native` (where supported) |
| Build | Turborepo + pnpm | Turborepo + pnpm + EAS |
| Hosting | AWS ECS Fargate (Next.js node server) | EAS Build + App Store / Play Store |

**Versioning rule**: do NOT bump major versions of any of these dependencies without explicit review. The architecture is designed against these specific versions.

---

## 4. State Management Architecture

Strict separation: **Server state** lives in TanStack Query; **client UI state** lives in Zustand. They do not overlap.

### 4.1 Server State: TanStack Query

Use TanStack Query for any data that originates from the backend. It handles caching, background refetching, optimistic updates, and SSE-driven cache invalidation.

**Never put backend data into Zustand.** It will desync on every backend change.

```typescript
// packages/ui/src/hooks/useStalenessRetry.ts (shared example)
// or apps/web/src/features/quotes/api/useQuotes.ts (surface-specific)

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import type { components } from '@pilot/shared-types';

type QuoteResponse = components['schemas']['QuoteResponse'];
type QuoteCreate = components['schemas']['QuoteCreate'];

export const useQuotes = (filters?: { status?: string }) => {
  return useQuery<QuoteResponse[]>({
    queryKey: ['quotes', filters],
    queryFn: async () => {
      const { data } = await apiClient.get('/api/v1/quotes', { params: filters });
      return data;
    },
    staleTime: 1000 * 60 * 5, // 5 minutes
  });
};

export const useCreateQuote = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (newQuote: QuoteCreate) => {
      // Idempotency UUID required for offline-capable mutations
      const idempotencyKey = crypto.randomUUID();
      const { data } = await apiClient.post('/api/v1/quotes', newQuote, {
        headers: { 'X-Idempotency-Key': idempotencyKey },
      });
      return data;
    },
    onSuccess: (newQuote) => {
      queryClient.invalidateQueries({ queryKey: ['quotes'] });
      // Or, for surgical update without refetch:
      // queryClient.setQueryData(['quotes', newQuote.id], newQuote);
    },
  });
};
```

### 4.2 Client State: Zustand

Use Zustand for ephemeral UI state that doesn't belong on the server: open/closed dialog state, multi-step wizard progress, voice session UI state, in-progress form drafts that aren't persisted.

```typescript
// apps/mobile/src/features/voice-quote-creation/store.ts

import { create } from 'zustand';

type VoiceState = 'idle' | 'listening' | 'processing' | 'speaking' | 'waiting-confirm' | 'error';

interface VoiceSessionStore {
  voiceState: VoiceState;
  currentSessionId: string | null;
  setVoiceState: (state: VoiceState) => void;
  setSessionId: (id: string | null) => void;
  reset: () => void;
}

export const useVoiceSessionStore = create<VoiceSessionStore>((set) => ({
  voiceState: 'idle',
  currentSessionId: null,
  setVoiceState: (voiceState) => set({ voiceState }),
  setSessionId: (currentSessionId) => set({ currentSessionId }),
  reset: () => set({ voiceState: 'idle', currentSessionId: null }),
}));
```

### 4.3 Decision tree

When you have data, ask:

1. **Is this data ever fetched from the backend?** → TanStack Query.
2. **Does this data need to survive a page navigation?** → If yes and it's server-derived, refetch via TanStack Query. If yes and it's client-only, Zustand with `persist` middleware.
3. **Is this data only relevant inside one component tree?** → React's `useState`/`useReducer`. No need for Zustand.
4. **Is this voice session UI state, an open dialog, or a multi-step wizard?** → Zustand (typically scoped to the feature folder).

---

## 5. Authentication & Authorization

Auth is established in **FE-B0** (scaffolding) and **FE-B2** (login surface). Every authenticated surface composes the patterns here. Never invent your own auth path.

### 5.1 Auth provider (Cognito via Amplify)

```typescript
// apps/web/src/app/providers.tsx (and equivalent in mobile)
import { Amplify } from 'aws-amplify';
import { AuthProvider } from '@pilot/ui/auth';

Amplify.configure({
  Auth: {
    Cognito: {
      userPoolId: process.env.NEXT_PUBLIC_COGNITO_USER_POOL_ID!,
      userPoolClientId: process.env.NEXT_PUBLIC_COGNITO_CLIENT_ID!,
    },
  },
});

export function RootProviders({ children }: { children: React.ReactNode }) {
  return <AuthProvider>{children}</AuthProvider>;
}
```

### 5.2 `useAuth()` hook

```typescript
// Consume from any client component:
import { useAuth } from '@pilot/ui/auth';

function ProfileMenu() {
  const { user, signOut, isAuthenticated, role } = useAuth();
  if (!isAuthenticated) return null;
  return (
    <div>
      <span>{user.email}</span>
      <span>Role: {role}</span>
      <button onClick={signOut}>Sign out</button>
    </div>
  );
}
```

### 5.3 RBAC via `<RoleGate>` — hide-not-disable

Per Settings IA Decision 8, RBAC is **hide-not-disable**. Unauthorized elements do not render — there is no "you don't have permission" affordance, no greyed-out button.

```tsx
import { RoleGate, useRequiresPermission } from '@pilot/ui/role-gate';

// Wrap entire UI elements:
<RoleGate role="owner">
  <ApproveQuoteButton quoteId={quote.id} />
</RoleGate>

// Or check inline:
function QuoteActions({ quote }) {
  const canApprove = useRequiresPermission('quotes.approve');
  return (
    <div>
      <ViewButton />
      {canApprove && <ApproveButton />}
    </div>
  );
}
```

**Permission key conventions**: `{domain}.{action}` (e.g., `quotes.approve`, `dispatch.move`, `customers.delete`). Permission keys are defined in a single registry in `packages/ui/src/role-gate/permissions.ts`. Adding a new permission = adding a row there.

### 5.4 JWT refresh is silent

`apiClient` has an Axios interceptor that catches 401s, refreshes the JWT via Amplify, and retries the original request. **Surfaces never see 401s during normal operation.** If a refresh fails (refresh token expired), the user is signed out and routed to login with a "Your session expired" banner.

You should not write custom 401 handling at the surface level. If you find yourself doing so, you're working around the wrong layer.

### 5.5 Route protection

In Next.js App Router (`apps/web`), authenticated routes live under `(authed)/` route group with a layout that wraps children in `<RequireAuth>`:

```tsx
// apps/web/src/app/(authed)/layout.tsx
import { RequireAuth } from '@pilot/ui/auth';

export default function AuthedLayout({ children }: { children: React.ReactNode }) {
  return <RequireAuth redirectTo="/login">{children}</RequireAuth>;
}
```

In Expo Router (`apps/mobile`), similar pattern with `(authed)/_layout.tsx`.

---

## 6. Design Tokens & Visual System

### 6.1 The Pass 1 token system is non-negotiable

Every color, font size, spacing value, border radius, and breakpoint comes from `packages/ui/src/tokens.ts`. Tailwind utilities resolve to tokens via the preset. Gluestack themes consume tokens via `gluestack-config.ts`. Raw values are forbidden.

```typescript
// packages/ui/src/tokens.ts (excerpt — actual values per Pass 1 spec)
// Tokens use ramp-based structure: colors.brand[50], colors.alert[400], etc.
export const colors = {
  brand: {
    50: '#EEF1FF',
    100: '#D6DCFF',
    400: '#6875F5',
    600: '#3B43D6',    // Default brand stop — CTA button fill
    800: '#232AA3',
    900: '#181D66',
  },
  alert: { /* ... voice-active, NEC warnings */ },
  margin: { /* ... profit, success, on-budget */ },
  fault: { /* ... over-budget, errors, danger */ },
  neutral: { /* ... text, surfaces, borders */ },
} as const;

export const spacing = {
  0: 0, 1: 4, 2: 8, 3: 12, 4: 16, 5: 20, 6: 24, 8: 32, 10: 40, 12: 48, 16: 64, 20: 80,
} as const;  // 4px grid

// Consumed by Tailwind preset (web) via `pilotPreset` and Gluestack config (mobile)
export const tokens = { colors, lightTheme, darkTheme, fonts, spacing, /* ... */ } as const;
```

### 6.2 ESLint rule: `no-hardcoded-design-values`

This rule is configured in `packages/eslint-config/rules/no-hardcoded-design-values.ts`. It flags:

- Raw hex codes in component files (`#1a1a1a`, `#fff`, etc.)
- Magic pixel values outside the spacing scale (`padding: 13px`, etc.)
- Raw rgb/rgba/hsl color values
- Font-size values not from the type scale

**The rule is configured as `warning` in FE-B0 setup and promoted to `error` at the close of FE-B1.** From FE-B2 onward, any PR with a violation fails CI.

If you encounter a case where Pass 1 tokens don't cover a need, the right action is **not** to hardcode a value. The right action is to (a) confirm the design spec actually requires the new value (it usually doesn't — most "needs" are misuses of existing tokens), (b) raise the question with Tom in a Surface Design Session, and (c) if approved, add the new token to `tokens.ts` and the relevant theme configs.

### 6.3 Tailwind preset (web)

```typescript
// apps/web/tailwind.config.ts
import { pilotPreset } from '@pilot/ui/tailwind.preset';

export default {
  presets: [pilotPreset],
  content: ['./src/**/*.{ts,tsx}'],
} satisfies Config;
```

Use Tailwind utility classes that resolve to tokens:

```tsx
// ✅ Correct — uses Tailwind utility resolving to brand-600 token
<button className="bg-brand-600 hover:bg-brand-800 text-white px-4 py-2 rounded-md">

// ❌ Wrong — hardcodes a hex
<button style={{ backgroundColor: '#3B43D6' }}>

// ❌ Wrong — hardcodes a magic pixel value
<div className="px-[13px]">  {/* 13px is not on the 4px spacing scale */}
```

### 6.4 Gluestack config (mobile)

```typescript
// apps/mobile/app/_layout.tsx
import { GluestackUIProvider } from '@gluestack-ui/themed';
import { gluestackConfig } from '../theme/gluestack-config';  // Local to mobile app

export default function RootLayout() {
  return (
    <GluestackUIProvider config={gluestackConfig}>
      {/* ... */}
    </GluestackUIProvider>
  );
}
```

> **Note**: `gluestack-config.ts` lives at `apps/mobile/theme/gluestack-config.ts` (not in `packages/ui/`). It imports tokens from `@pilot/ui/tokens` and maps them to Gluestack's theme format. This is intentional — the config is mobile-specific and references platform-specific Gluestack APIs.

Use Gluestack style props that resolve to tokens:

```tsx
// ✅ Correct — token-based props
<Box bg="$brand-600" p="$4" rounded="$md">

// ❌ Wrong — hardcoded values
<Box style={{ backgroundColor: '#3B43D6', padding: 16 }}>
```

### 6.5 Cross-platform style consistency

A single source of truth (`tokens.ts`) feeds both Tailwind preset and Gluestack config. The same token name (`brand-indigo-500`) resolves to the same color on web and mobile. **If you ever see a visual divergence between web and mobile for what should be the same value, the bug is upstream of your component — fix it in `tokens.ts` or the platform config, never in a surface-specific component.**

---

## 7. UI Component Standards

### 7.1 Web: shadcn/ui + Tailwind

Use shadcn/ui primitives (`Button`, `Dialog`, `Input`, `Select`, etc.) as the base. Compose Tailwind utility classes; isolate complex class strings via `cn()` (clsx + tailwind-merge).

```tsx
// apps/web/src/features/quotes/components/ApproveButton.tsx
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

interface ApproveButtonProps {
  className?: string;
  onClick: () => void;
  isPending?: boolean;
}

export function ApproveButton({ className, onClick, isPending }: ApproveButtonProps) {
  return (
    <Button
      className={cn(
        'bg-brand-indigo-500 hover:bg-brand-indigo-700 text-white font-semibold',
        isPending && 'opacity-50 cursor-not-allowed',
        className
      )}
      onClick={onClick}
      disabled={isPending}
    >
      {isPending ? 'Approving...' : 'Approve Quote'}
    </Button>
  );
}
```

**Never write standalone CSS files**. If you need a style that Tailwind can't express, the right move is to extend Tailwind via the preset, not write CSS.

### 7.2 Mobile: Gluestack-UI

Use Gluestack primitives (`Button`, `Box`, `Text`, `HStack`, `VStack`, etc.). Style via the props system — no inline `style={{}}` objects.

**Glove-friendly UI rules** (per Pass 1 design spec):
- Minimum touch target: **44 × 44 px** (`size="xl"` on Gluestack `Button` enforces this)
- Touch target spacing: minimum 8 px between adjacent tappable elements
- Field Mode (toggleable per user): high-contrast variant of all interactive elements

```tsx
// apps/mobile/src/features/voice-quote-creation/components/MicButton.tsx
import { Button, ButtonText, Icon } from '@gluestack-ui/themed';
import { Mic } from 'lucide-react-native';

interface MicButtonProps {
  onPress: () => void;
  isListening: boolean;
}

export function MicButton({ onPress, isListening }: MicButtonProps) {
  return (
    <Button
      size="xl"                          // 44x44+ enforced
      action={isListening ? 'negative' : 'primary'}
      onPress={onPress}
      accessibilityLabel={isListening ? 'Stop listening' : 'Start voice input'}
      testID="voice-trigger-btn"         // Required for Maestro/Detox
    >
      <Icon as={Mic} color="$white" size="lg" />
      <ButtonText fontWeight="$bold" ml="$2">
        {isListening ? 'Listening...' : 'Tap to talk'}
      </ButtonText>
    </Button>
  );
}
```

**Every interactive mobile element MUST have**:
- `accessibilityLabel` (or `accessibilityHint` for context)
- `testID` for e2e test targeting
- Minimum 44×44 px touch target

### 7.4 Mobile StyleSheet Patterns (React Native–Specific)

These patterns are mandatory for all `StyleSheet.create` blocks in mobile components. They emerged from real rework during MOB-B6/B7 and the mobile UI fix sessions.

#### 7.4.1 `fontWeight` MUST Be Wrapped in `String(...) as "500"` Cast

`fontWeights.medium` and `fontWeights.regular` from `@pilot/ui/tokens` are **numbers** (`500`, `400`). React Native's `TextStyle.fontWeight` requires **string literals** (`"400"` | `"500"` | `"bold"` etc.). TypeScript will error if you pass the number directly.

```typescript
// ❌ TypeScript error — number not assignable to "100"|"200"|...|"bold"
fontWeight: fontWeights.medium

// ✅ REQUIRED — cast token number to string literal
fontWeight: String(fontWeights.medium) as "500"
fontWeight: String(fontWeights.regular) as "400"
```

The pilot token system has only two weights: `regular` (400) and `medium` (500). **Never hardcode `"bold"`, `"600"`, `"700"`, or `"900"`** — outside the design system.

#### 7.4.2 Always Use `mobileFontSizes.*` and Pair with `mobileLineHeights.*`

Never hardcode pixel font sizes. Use `mobileFontSizes` and always pair with the matching `mobileLineHeights` entry to prevent Android text clipping:

```typescript
import { mobileFontSizes, mobileLineHeights } from "@pilot/ui/tokens";

// ❌ WRONG — hardcoded size, missing lineHeight
fontSize: 22,

// ✅ REQUIRED — token-driven, always pair fontSize + lineHeight
fontSize: mobileFontSizes.h1,         // 22
lineHeight: mobileLineHeights.h1,     // 30
```

Mobile type scale: `caption` (11), `body` (13), `bodyLg` (15), `h3` (17), `h2` (20), `h1` (22), `display` (28).

#### 7.4.3 Import Tokens via Package Alias — Never Relative Paths

```typescript
// ❌ BANNED — fragile, breaks if the component moves to a different directory depth
import { colors } from "../../../../../packages/ui/src/tokens";

// ✅ REQUIRED — stable monorepo package alias
import { colors, mobileFontSizes, mobileLineHeights, fontWeights, spacing, radii } from "@pilot/ui/tokens";
```

#### 7.4.4 Root Container Must Use `SafeAreaView` — Never `View`

For any scrollable screen, the root container must be `SafeAreaView` to handle the iOS notch and Android status bar:

```typescript
// ❌ WRONG — content hidden behind iOS notch or Android status bar
<View style={{ flex: 1 }}>
  <ScrollView>...</ScrollView>
</View>

// ✅ REQUIRED — SafeAreaView → ScrollView for scrollable screens
<SafeAreaView style={{ flex: 1, backgroundColor: colors.neutral[50] }}>
  <ScrollView
    style={{ flex: 1 }}
    contentContainerStyle={{ paddingHorizontal: spacing[4], paddingVertical: spacing[3] }}
  >
    {/* screen content */}
  </ScrollView>
</SafeAreaView>
```

### 7.3 Cross-platform shared components (`packages/ui/`)

When a component is consumed by both apps, it lives in `packages/ui/`. If the implementation differs between web and mobile, organize as:

```text
packages/ui/src/notification-banner/
├── types.ts                  # Shared TypeScript interface
├── web/
│   └── NotificationBanner.tsx     # Uses shadcn Dialog/Toast primitives
├── mobile/
│   └── NotificationBanner.tsx     # Uses Gluestack Toast primitives
└── index.ts                  # Resolves to web or mobile at build time via package.json "exports" field
```

The public API (props) is identical across platforms. Consumers import from `@pilot/ui/notification-banner` without caring which platform they're on.

---

## 8. Shared Component Catalog

These are the canonical shared components in `packages/ui/`. Each is established in a specific batch (per `pilot-app-mvp-frontend-impl-plan.md` v1.0 §1.5 Rule 1) and consumed by subsequent batches. **Do not reimplement these. Do not fork them. Import and compose.**

> **Catalog currency**: This table is current as of FE-B16 completion (all 17 frontend batches shipped). When the React Engineer adds a new shared component in WS3 or beyond, they must add a row to this table and export the component from `packages/ui/src/index.ts`.

| Component | Established In | Consumers | Purpose |
|:---|:---|:---|:---|
| `<RoleGate>`, `useRequiresPermission()` | FE-B0 | All routed surfaces | Hide-not-disable RBAC |
| `<EmptyState>`, `<LoadingState>`, `<ErrorState>` | FE-B1 | Every surface | States catalog (12 entries) |
| FTU variants (8) | FE-B1 | Per-surface FTU | First-time-user onboarding nudges |
| `<NotificationBanner>` | FE-B1 | FE-B6, FE-B7, FE-B9, FE-B10, FE-B12, FE-B13 | In-app toast (6s standard, 12s critical, ARIA `role="alert"`) |
| `<InFlightSyncIndicator>` | FE-B1 (skeleton); FE-B15 (refined) | FE-B4, FE-B7, FE-B8, FE-B9 | Pending count + sync state pill (§16.13) |
| `<EmailBrandingPreview>` | FE-B1 (skeleton); FE-B14 (fleshed) | FE-B11, FE-B14 | Live email rendering preview |
| `<MFAEnrollmentWizard>` | FE-B1 (skeleton); FE-B12 (fleshed) | FE-B12 | TOTP/SMS/Email enrollment paths |
| `<TierPickerCard>` | FE-B1 (skeleton); FE-B13 (fleshed) | FE-B13 | Subscription tier selection |
| `<DiffView>` | FE-B5 | FE-B8, FE-B9 | Track-changes amber/green/red diff (§16.2) — polymorphic via `variant` prop |
| `<MessagePreviewModal>`, `usePreviewBeforeSend()` | FE-B6 | FE-B10 | Always-preview-before-send (§16.7) |
| `<VoiceConfirmTurn>`, `useVoiceConfirmation()` | FE-B3 | FE-B6, FE-B8, FE-B10, FE-B16 | Confirm-as-turn voice UI (§16.3) |
| `<PendingBadge>`, `useOptimisticMutation()` | FE-B7 | FE-B9, FE-B12 | Optimistic UI with pending count badges (§16.8) |
| `<SettingControl>`, `<RevertToDefaultDialog>` | FE-B11 | FE-B12, FE-B13 | System-default + tenant-override visual treatment (Settings IA Mockup A) |
| `useFormSaveStrategy()`, `<SaveOnGroupCompleteIndicator>` | FE-B11 | FE-B12, FE-B13 | Save-on-blur / save-on-group-complete / explicit-save (Mockup B) |
| `<EffectiveSettingDisplay>` | FE-B11 | FE-B12 | Three-tier resolution chain visual (Mockup C) |
| `<IntegrationConflictResolver>` | FE-B8 | FE-B9 | Bilateral integration conflict resolution (§16.10) — polymorphic via `integration` prop |
| `<EscalationStatusRow>` | FE-B9 | (Phase 2) | Mobile-to-web escalation status (§16.11) |
| `useStalenessRetry()`, `<StalenessRefreshDialog>` | FE-B4 | FE-B5, FE-B8, FE-B9, FE-B10 | Pre-commit staleness 409 handling (§16.4) |
| `<StripePaymentForm>` | FE-B13 | FE-B14 | Stripe Elements wrapper (subscription + one-time modes) |
| `apiClient` (Axios + auto-types + JWT) | FE-B0 | Every surface | Standardized API call layer |
| `<AuthProvider>`, `useAuth()` | FE-B0 | All authed surfaces | Cognito-via-Amplify auth |

### 8.1 Component manifest in `packages/ui/src/index.ts`

Every shared component is exported from a single barrel file. The manifest is the public API. **A component does not exist in the shared library until it is exported from `index.ts`.** This is verified at the close of every batch (see §16 workflow).

```typescript
// packages/ui/src/index.ts
export { RoleGate, useRequiresPermission } from './role-gate';
export { EmptyState, LoadingState, ErrorState } from './states';
export { NotificationBanner } from './notification-banner';
export { InFlightSyncIndicator } from './sync-indicator';
export { DiffView } from './diff-view';
// ... and so on
```

### 8.2 The skeleton-vs-fleshed pattern

Some components are introduced in FE-B1 as **skeletons** (with their public API locked) and **fleshed out** in a later batch when their consuming surface ships. Examples: `<EmailBrandingPreview>`, `<MFAEnrollmentWizard>`, `<TierPickerCard>`.

If you're working on a batch that fleshes out a skeleton, **do not change the public API**. The skeleton's prop interface is the contract. Adding new optional props is fine; renaming existing props is not.

---

## 9. Platform Patterns Reference

These are the canonical `mvp-arch.md` §16 platform patterns. Every cross-cutting UX concern in Pilot resolves through one of these. **If you find yourself inventing a new pattern, stop — there's almost certainly an existing one to compose instead.**

### 9.1 Track-changes diff renderer (§16.2)

When showing field-level diff between two states (quote pre/post-edit, calendar Pilot-vs-external, QB Pilot-vs-QB), use `<DiffView>` from FE-B5. Amber = unchanged context, green = added, red = removed.

```tsx
import { DiffView } from '@pilot/ui/diff-view';

<DiffView
  variant="quote-line"        // or "calendar-event" | "qb-entity" | "entity"
  baseline={originalLines}
  modified={editedLines}
/>
```

### 9.2 Confirm-as-turn (§16.3)

When voice triggers a destructive or high-stakes action (send message, approve quote, resolve conflict), the AI says back what it's about to do; user's affirmative voice input commits; anything else cancels.

```tsx
import { VoiceConfirmTurn } from '@pilot/ui/voice-confirm-turn';

<VoiceConfirmTurn
  prompt="Send the 'on my way' message to John Smith?"
  onConfirm={() => sendMessage(...)}
  onCancel={() => clearIntent()}
/>
```

### 9.3 Pre-commit staleness 409 retry (§16.4)

When a mutation could race against another user's change (dispatch move, calendar resolve, QB resolve, settings write, SMS reply), use `useStalenessRetry()`. On 409, the hook fetches refreshed state, surfaces a dialog, allows retry against new state.

```tsx
import { useStalenessRetry } from '@pilot/ui/hooks';

const { mutate, StalenessDialog } = useStalenessRetry({
  mutationFn: moveJob,
  onConflict: (refreshedState) => { /* show diff or just retry */ },
});

return (
  <>
    <Button onClick={() => mutate({ jobId, newSlot, expectedVersion })}>Move</Button>
    <StalenessDialog />
  </>
);
```

### 9.4 System-default + tenant-override (§16.5 / Settings IA Decision 4)

Settings have three states: system-default (subdued visual), tenant-overridden (prominent), revert-pending (transitional). Use `<SettingControl>` from FE-B11.

```tsx
import { SettingControl } from '@pilot/ui/setting-control';

<SettingControl
  settingKey="quote_approval_threshold"
  scope="tenant"
  onSave={async (value) => { /* persists and updates effective value */ }}
/>
```

`<SettingControl>` reads from the BE-B9/A52 catalog endpoint and renders the appropriate input type per the catalog metadata. **You do not write per-setting UI.**

### 9.5 Four-class severity (§16.6)

Conflicts and notifications are classified into four severity classes: `auto_apply` (silent), `safe_to_apply` (banner), `requires_review` (modal), `escalate_to_owner` (escalation queue entry). The visual treatment is encoded in Pass 1 tokens; the behavioral treatment is encoded per surface.

When you receive a `severity` field from the backend, never invent your own UI mapping. Use the canonical class-based component (e.g., the conflict resolver, the notification banner, etc.) which already encodes the right treatment.

### 9.6 Always-preview-before-send (§16.7)

Every customer communication (template, free-form, voice) goes through `<MessagePreviewModal>` from FE-B6. Preview shows rendered template body, channel, recipient, segment count. User confirms → send. **There is no "send without preview" affordance in MVP.**

```tsx
import { usePreviewBeforeSend } from '@pilot/ui/hooks';

const { preview, MessagePreviewModal } = usePreviewBeforeSend({ channel: 'sms' });

return (
  <>
    <Button onClick={() => preview({ templateCode, customerId, variables })}>Send</Button>
    <MessagePreviewModal />
  </>
);
```

### 9.7 Optimistic UI with pending badges (§16.8)

For offline-capable mutations, write to local state immediately, queue the sync push, surface a `<PendingBadge>` next to the entity until the push succeeds.

```tsx
import { useOptimisticMutation, PendingBadge } from '@pilot/ui/pending-badge';

const { mutate, isPending } = useOptimisticMutation({
  mutationFn: createTimeEntry,
  optimisticUpdate: (vars) => addToLocalDb(vars),
});

return <View>...{isPending && <PendingBadge count={1} />}</View>;
```

### 9.8 Mobile-to-web escalation (§16.11)

When a mobile-side conflict has severity `escalate_to_owner`, mobile shows `<EscalationStatusRow>` and creates an entry in the owner's web-side queue (FE-B9). Owner resolves on web; mobile receives push; status updates.

This is the canonical pattern for any cross-platform escalation in MVP.

### 9.9 In-flight sync indicator (§16.13)

Surfaces with sync state (dispatch, mobile sync, calendar, QB) compose `<InFlightSyncIndicator>`. Reads pending count from `services/sync_status.py` (BE-B15/A79); shows surface-aware visual treatment.

```tsx
import { InFlightSyncIndicator } from '@pilot/ui/sync-indicator';

<InFlightSyncIndicator surface="dispatch" />
```

### 9.10 Bilateral integration conflict resolution (§16.10)

Use `<IntegrationConflictResolver>` from FE-B8. Polymorphic via `integration` prop (`calendar`, `quickbooks`). Future Phase 2 integrations inherit.

---

## 10. API Integration & Mock-Driven Development

### 10.1 Auto-generated TypeScript types

The backend exposes an OpenAPI 3.1 spec at `${API_URL}/openapi.json`. The frontend consumes auto-generated TypeScript types via `pnpm sync-api-types`, which writes to `packages/shared-types/src/api-schema.d.ts`.

**Run `pnpm sync-api-types` after every backend deploy.** Stale types lead to silent runtime failures.

```typescript
// Consume types via the schema namespace:
import type { components, operations } from '@pilot/shared-types';

type QuoteResponse = components['schemas']['QuoteResponse'];
type CreateQuoteParams = operations['createQuote']['requestBody']['content']['application/json'];
```

**Never invent endpoint shapes or payload field names.** If a needed endpoint is missing because its backend batch is in flight, draft an interface stub matching the agreed contract and create an MSW handler — the stub is then deleted as soon as the real types land.

#### ⚠️ Verify the endpoint in `openapi_schema_map.md` BEFORE writing any hook

**This is the single most important rule for preventing wrong-URL and wrong-parameter bugs** (root cause of multiple FE-B batch rework incidents). Before coding any TanStack Query hook:

1. **Check `backend/openapi_schema_map.md`** — the human-readable summary of every endpoint with exact paths, required params, and response shapes. This is the fast lookup.
2. **If more detail is needed, check `backend/openapi.json`** — the full machine-readable spec.
3. **If the endpoint is not in either file, it does not exist.** Do NOT assume it will be added. Do NOT invent a URL pattern. Ask Tom.

```bash
# Quick verification from the backend directory:
python3 -c "
import json
spec = json.load(open('openapi.json'))
matches = [p for p in spec['paths'] if 'YOUR_KEYWORD' in p]
print(matches)
"
```

#### Understanding the backend data model via `db_models_map.md`

When building a new list page or surface and you need to understand what entities exist in the backend, consult `backend/db_models_map.md`. It shows which file defines each model and explicitly separates **DB Tables** (queryable via API) from **Enums/Schemas** (not direct API resources). This prevents assumptions like "there must be a `/api/v1/invoice-status` endpoint" when `InvoiceStatus` is just a Python enum.

### 10.2 `apiClient` (Axios)

A single Axios instance lives in `packages/ui/src/api-client.ts` (or `apps/{web|mobile}/src/lib/api-client.ts` if platform-specific concerns dominate). It:

- Reads JWT from `useAuth()` and attaches `Authorization: Bearer ...`
- Attaches `X-Tenant-Id` header (when known) for multi-tenant requests
- Catches 401, refreshes, retries
- Logs errors to the console / CloudWatch (no third-party error reporter is wired)
- Supports request-level `X-Idempotency-Key` for offline-capable mutations

**Never fetch directly via `fetch()` or a fresh Axios instance.** Always go through `apiClient`.

### 10.3 MSW (Mock Service Worker) — mock-driven parallel development

Per `pilot-app-mvp-frontend-impl-plan.md` v1.0 §1.5 Rule 5, frontend batches can develop against MSW handlers while their backend batch is still landing.

```typescript
// apps/web/src/mocks/handlers/quotes.ts
import { http, HttpResponse } from 'msw';
import type { components } from '@pilot/shared-types';

type QuoteResponse = components['schemas']['QuoteResponse'];

export const quotesHandlers = [
  http.get('/api/v1/quotes', () => {
    return HttpResponse.json<QuoteResponse[]>([
      { id: 'q1', status: 'sent', total_cents: 250000, /* ... */ },
    ]);
  }),
  http.post('/api/v1/quotes', async ({ request }) => {
    const body = await request.json();
    return HttpResponse.json<QuoteResponse>({ id: 'q-new', ...body });
  }),
];
```

```typescript
// apps/web/src/mocks/browser.ts
import { setupWorker } from 'msw/browser';
import { quotesHandlers, customersHandlers, /* ... */ } from './handlers';

export const worker = setupWorker(...quotesHandlers, ...customersHandlers);
```

```typescript
// apps/web/src/app/providers.tsx (gated behind env var)
if (typeof window !== 'undefined' && process.env.NEXT_PUBLIC_USE_MSW_MOCKS === 'true') {
  const { worker } = await import('@/mocks/browser');
  await worker.start({ onUnhandledRequest: 'bypass' });
}
```

**MSW handlers are also consumed in unit and integration tests** (via `setupServer` from `msw/node`). The same handler file feeds both dev and tests — single source of mock truth.

### 10.4 SSE (Server-Sent Events)

For real-time updates (dispatch board, calendar conflicts, notifications, SMS threads), use SSE. Web uses native `EventSource`; mobile uses `react-native-sse` polyfill. The pattern is encoded in `useSseChannel()`:

```typescript
import { useSseChannel } from '@pilot/ui/hooks';

useSseChannel('/sse/dispatch-board', {
  onMessage: (event) => {
    const { entity_type, entity_id } = JSON.parse(event.data);
    queryClient.invalidateQueries({ queryKey: [entity_type, entity_id] });
  },
  fallbackToPolling: 60000, // ms — auto-fallback if SSE connection fails
});
```

**SSE messages do not carry full payloads.** They carry "this entity changed, refetch" cues. UI invalidates TanStack Query cache; UI auto-rerenders with fresh data.

### 10.5 RFC 7807 error handling

Backend errors follow RFC 7807 Problem Details format. `apiClient` parses these into a typed error. Surface them via `<NotificationBanner>` with the `severity` field driving visual class.

```typescript
import { isProblemDetails } from '@/lib/api-client';

try {
  await mutate.mutateAsync(payload);
} catch (err) {
  if (isProblemDetails(err)) {
    showNotification({
      severity: err.severity ?? 'error',  // Maps to four-class system
      title: err.title,
      detail: err.detail,
      deepLinkTarget: err.deep_link_target,
    });
  }
}
```

**Never use `alert()`. Never show raw stringified errors.** Always parse + surface via `<NotificationBanner>`.

### 10.6 FastAPI 422 `detail` Is Always an Array — Never a String

FastAPI Pydantic validation errors return `detail` as an **array of objects**, not a plain string:

```json
{
  "detail": [
    { "type": "missing", "loc": ["body", "role"], "msg": "Field required", "input": {}, "ctx": {} }
  ]
}
```

**Rule**: Never store `data?.detail` directly in a React string state variable. Always normalize:

```typescript
// REQUIRED — normalize before setting string state
const detail = data?.detail;
const msg =
  typeof detail === "string"
    ? detail
    : Array.isArray(detail)
      ? detail.map((e: { msg: string }) => e.msg).join(", ")
      : "Something went wrong. Please try again.";
setErrorMsg(msg);
```

BANNED — crashes with "Objects are not valid as a React child" on any 422:
```typescript
setErrorMsg(data?.detail ?? "Something went wrong.");  // data.detail is an array, not a string
```

This applies to **every** `fetch()` or `apiClient` call in the marketing app and the web app. Check every form's error handler for this pattern before shipping.

### 10.7 Mobile MSW Handler URL Pattern — Wildcard Required

The mobile app's `apiClient.baseURL` is a full absolute URL (e.g., `http://192.168.1.50:8000` for LAN/physical device testing). When the MSW browser service worker runs on `localhost:8081`, **relative-path MSW handlers do not match requests to a different origin**.

```typescript
// ❌ BROKEN on mobile web — only matches requests to localhost:8081
// When apiClient sends to http://192.168.1.50:8000/api/v1/jobs/, this handler SILENTLY misses
http.get("/api/v1/jobs/", handler)

// ✅ REQUIRED for all mobile MSW handlers — matches any origin
http.get("*/api/v1/jobs/", handler)
```

Every handler in `apps/mobile/mocks/handlers/` MUST use the `*/api/v1/...` wildcard prefix. The web app (`apps/web`) can use relative paths because `apiClient.baseURL` points to `localhost:8000` (same origin as the Next.js dev server). The mobile app cannot.

### 10.7 Metro Bundle Rules — Preventing Native Code From Entering the Web Bundle

Metro walks **all reachable files** via static import analysis and bundles them. Without explicit exclusions, test files, MSW node server code, and native-only packages will crash the web build.

#### 10.7.1 Test Files Must Be Excluded from Metro

`mocks/server.ts` (which calls `msw/node`'s `setupServer()`) and all `__tests__/` files must be in the Metro `exclusionList` blockList. See `metro.config.js`:

```javascript
// metro.config.js — these patterns must be in exclusionList
// __tests__/ directories, mocks/server.ts, *.test.*, *.spec.*
```

#### 10.7.2 Native-Only Packages Must Return `{ type: 'empty' }` on Web

These packages crash on web at **module factory load time** (not at render time) because they call platform APIs that don't exist in the browser. Add them to `NATIVE_ONLY_PACKAGES` in `metro.config.js`:

- `expo-location`, `expo-haptics`, `expo-image-picker`, `expo-file-system`, `expo-sharing`, `expo-av`
- `better-sqlite3`, `@nozbe/watermelondb/adapters/sqlite/sqlite-node`

#### 10.7.3 Singleton Packages Must Be in `SINGLETON_PACKAGES`

pnpm symlinks can cause `packages/shared-api` and `apps/mobile` to each resolve their own copy of a package. Any package with singleton state MUST be in `SINGLETON_PACKAGES`:

- `@tanstack/react-query` — `"No QueryClient set"` crash if duplicated
- `react-native-svg` — `"Tried to register two views with the same name RNSVGCircle"` crash if duplicated
- `react`, `react-native`

#### 10.7.4 MSW `setupWorker()` Must Be Lazy — Never Module-Level

`setupWorker()` crashes Metro's SSR renderer (`node/render.js`). Always wrap in a lazy async function and guard the call site:

```typescript
// ✅ CORRECT — lazy, never at module evaluation time
export async function startMockServiceWorker(opts?) {
  const { setupWorker } = await import("msw/browser");
  const worker = setupWorker(...handlers);
  await worker.start(opts ?? { onUnhandledRequest: "bypass" });
}

// In _layout.tsx — double guard required
if (Platform.OS === "web" && typeof window !== "undefined" && isMockMode) {
  const { startMockServiceWorker } = require("../mocks/browser");
  startMockServiceWorker({ onUnhandledRequest: "bypass" });
}
```

#### 10.7.5 Never Add `_layout.tsx` to a Directory That Has a Same-Named Tab `.tsx`

In Expo Router v6, having both `jobs.tsx` (tab file) and `jobs/_layout.tsx` creates two conflicting `"jobs"` routes in the Tabs navigator → crash: `"A navigator cannot contain multiple Screen components with the same name"`.

Use `href: null` suppression in the parent `(tabs)/_layout.tsx` for sub-routes instead of adding nested `_layout.tsx` files that conflict with tab-level files.

#### 10.7.6 `expo-file-system` v19 Moved Legacy APIs to `/legacy` Sub-Path

Code using `EncodingType`, `FileSystemUploadType`, `cacheDirectory`, `readAsStringAsync`, `writeAsStringAsync`, `uploadAsync` must import from `expo-file-system/legacy`:

```typescript
// ❌ BROKEN in expo-file-system v19+
import { EncodingType } from "expo-file-system";

// ✅ REQUIRED
import { EncodingType } from "expo-file-system/legacy";
```

Add a `moduleNameMapper` entry in Jest for this sub-path:
```javascript
// jest.config.js or package.json
"moduleNameMapper": {
  "expo-file-system/legacy": "<rootDir>/__mocks__/expo-file-system-legacy.js"
}
```

---

## 11. Mobile Offline Database: WatermelonDB

For the field-tech mobile app, use WatermelonDB. Models map to backend entities; sync is **custom-built**, not WatermelonDB's built-in sync (see `pilot-app-mvp-frontend-arch-impl-plan.md` v3.0 Appendix C).

### 11.1 Model definition

```typescript
// apps/mobile/src/database/models/TimeEntry.ts
import { Model } from '@nozbe/watermelondb';
import { field, date, readonly, relation } from '@nozbe/watermelondb/decorators';

export default class TimeEntry extends Model {
  static table = 'time_entries';
  static associations = {
    jobs: { type: 'belongs_to' as const, key: 'job_id' },
  };

  @field('job_id') jobId!: string;
  @field('description') description!: string;
  @field('duration_minutes') durationMinutes!: number;
  @date('captured_at') capturedAt!: Date;        // client_capture_at preserved per A38
  @field('idempotency_key') idempotencyKey!: string;  // UUID per A39
  @field('sync_status') syncStatus!: 'pending' | 'syncing' | 'synced' | 'failed';
  @field('sync_error') syncError?: string;
  @readonly @date('created_at') createdAt!: Date;

  @relation('jobs', 'job_id') job!: Job;
}
```

### 11.2 Custom sync orchestrator

Per FE arch impl plan v3.0 Appendix C, custom sync logic against BE-B7a/A37 push/pull endpoints. Idempotency UUID with natural-key fallback dedup (BE-B7a/A39); four-class conflict classification (BE-B7b/A40); deferred-voice upload reconnect logic.

```typescript
// apps/mobile/src/database/sync/orchestrator.ts (sketch — FE-B7 fleshes this out)

export class SyncOrchestrator {
  async push(): Promise<SyncPushResult> {
    const pending = await this.db.collections.get('time_entries')
      .query(Q.where('sync_status', 'pending'))
      .fetch();

    for (const entity of pending) {
      const idempotencyKey = entity.idempotencyKey;
      try {
        await apiClient.post('/api/v1/sync/push', {
          entity_type: 'time_entry',
          payload: entity.toJSON(),
          client_capture_at: entity.capturedAt,
        }, {
          headers: { 'X-Idempotency-Key': idempotencyKey },
        });
        await entity.update((e) => { e.syncStatus = 'synced'; });
      } catch (err) {
        if (isConflict(err)) {
          await this.handleConflict(entity, err.severity, err.details);
        } else {
          await entity.update((e) => { e.syncStatus = 'failed'; e.syncError = err.message; });
        }
      }
    }
  }

  private async handleConflict(entity: Model, severity: ConflictSeverity, details: any) {
    switch (severity) {
      case 'auto_apply':       /* silent — apply server version */ break;
      case 'safe_to_apply':    /* show <NotificationBanner> */ break;
      case 'requires_review':  /* surface conflict resolution screen */ break;
      case 'escalate_to_owner':/* create web-side queue entry */ break;
    }
  }

  // ... pull(), reconcile(), etc.
}
```

### 11.3 Sync rules

1. **Every offline write MUST persist locally first**, then queue for sync. No "online-only" mobile mutations in offline-capable surfaces.
2. **Every push includes `X-Idempotency-Key`** (UUID generated at capture time). The backend dedups via this key + natural-key fallback per BE-B7a/A39.
3. **`client_capture_at`** is preserved across the sync boundary. The backend uses it for ordering, not the server-side `created_at`.
4. **Sync status visible to user** via `<PendingBadge>` next to entities with non-`synced` status.
5. **Photo uploads use S3 multipart** (resumable chunked) per arch doc v5 §15.5; not part of the sync orchestrator's push loop.
6. **Deferred voice uploads** trigger on reconnect via the orchestrator, calling `POST /api/v1/voice/upload-audio` (BE-B7a/A37 + A38).

### 11.4 WatermelonDB Adapter Selection — Use LokiJS for Dev Builds and Web

The SQLite adapter (`@nozbe/watermelondb/adapters/sqlite`) requires `WMDatabaseBridge`, a native module that **cannot be linked in Expo Go** and **crashes on web** (it imports `better-sqlite3`, a Node.js native addon).

**Adapter selection rule:**

```typescript
// database/index.ts — mandatory conditional adapter pattern
import { Database } from "@nozbe/watermelondb";
import { Platform } from "react-native";

let adapter: any;

if (Platform.OS === "web" || __DEV__) {
  // Web + all dev builds (covers Expo Go):
  // LokiJS is a pure-JS in-memory adapter with IndexedDB persistence on web
  const { default: LokiJSAdapter } = require("@nozbe/watermelondb/adapters/lokijs");
  adapter = new LokiJSAdapter({ schema, useWebWorker: false, useIncrementalIndexedDB: true });
} else {
  // Production native builds only (EAS Build / App Store):
  const { default: SQLiteAdapter } = require("@nozbe/watermelondb/adapters/sqlite");
  adapter = new SQLiteAdapter({ schema, dbName: "pilot" });
}

export const database = new Database({ adapter, modelClasses: [...] });
```

**Never use a static top-level `import` for either adapter** — use `require()` inside the conditional block. A static import causes Metro to bundle the SQLite adapter into the web bundle, crashing the web build.

### 11.5 WatermelonDB `@field` Decorators — Babel Configuration

`babel-preset-expo@54.0.10+` changed its internal scheduling of `@babel/plugin-transform-class-properties`. **Do NOT add this plugin explicitly** to `babel.config.js` — it causes it to run twice, corrupting React Native's frozen static constants (`Event.NONE` etc.) → `TypeError: Cannot assign to read-only property`.

Use `@babel/plugin-proposal-decorators` (legacy mode) with `assumptions` instead:

```javascript
// babel.config.js — correct pattern for WatermelonDB decorators
module.exports = {
  presets: ["babel-preset-expo"],
  plugins: [
    ["@babel/plugin-proposal-decorators", { legacy: true }],
    // DO NOT add @babel/plugin-transform-class-properties here
  ],
  assumptions: {
    setPublicClassFields: true,
    privateFieldsAsSymbols: true,
  },
};
```

---

## 12. Voice AI & Audio Streaming Pipeline

Voice is core to Pilot. The latency target is **< 200ms perceived**, which requires audio streaming via WebSocket — **never** wait for the full recording before sending.

### 12.1 WebSocket streaming pattern

```typescript
// packages/ui/src/voice/useVoiceStream.ts (FE-B3 establishes this hook)

import { useEffect, useRef, useState } from 'react';

interface VoiceStreamEvent {
  type: 'transcript_partial' | 'transcript_final' | 'intent_detected' | 'response_streaming' | 'response_final' | 'error';
  payload: any;
}

export function useVoiceStream(sessionId: string | null) {
  const wsRef = useRef<WebSocket | null>(null);
  const [events, setEvents] = useState<VoiceStreamEvent[]>([]);

  useEffect(() => {
    if (!sessionId) return;
    const url = `${process.env.NEXT_PUBLIC_WS_URL}/api/v1/voice/stream?session_id=${sessionId}`;
    wsRef.current = new WebSocket(url);

    wsRef.current.onmessage = (event) => {
      const parsed = JSON.parse(event.data) as VoiceStreamEvent;
      setEvents((prev) => [...prev, parsed]);
    };

    wsRef.current.onerror = (err) => {
      console.error('Voice WebSocket error', err);
    };

    return () => {
      wsRef.current?.close();
      wsRef.current = null;
    };
  }, [sessionId]);

  const sendAudioChunk = (chunkBase64: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'audio_chunk', payload: chunkBase64 }));
    }
  };

  return { events, sendAudioChunk };
}
```

**Web audio capture**: use Web Audio API + `AudioWorkletNode` to capture 250ms PCM chunks.
**Mobile audio capture**: use `expo-av` `Audio.Recording.setOnRecordingStatusUpdate` to intercept chunks at 250ms intervals.

### 12.2 Live vs snapshot rendering (BE-B2/A12)

Voice session messages with `structured_content` (e.g., `quote_preview`, `customer_disambiguation`) have a `render_mode` field:

- `render_mode: 'live'` — fetch the current entity by `entity_id`; UI updates as backend updates the entity.
- `render_mode: 'snapshot'` — render from `snapshot_payload` embedded in the message.

The transition `live → snapshot` happens server-side at quote-submission time (or analogous "freeze" event). Once a message is `snapshot`, it stays `snapshot` forever. **The UI must never transition a message from snapshot back to live.** This is tested explicitly in FE-B3.

```tsx
// Pattern (sketch):
function StructuredMessage({ message }: { message: ConversationMessage }) {
  const { structured_content } = message;
  if (structured_content.render_mode === 'live') {
    return <LiveQuotePreview entityId={structured_content.entity_id} />;
  }
  // 'snapshot'
  return <SnapshotQuotePreview payload={structured_content.snapshot_payload} />;
}
```

### 12.3 Offline voice → REST upload fallback

When the device is offline, the WebSocket cannot stream live. Audio is captured locally + queued via the WatermelonDB sync queue (per A38). On reconnect, the orchestrator uploads the audio via `POST /api/v1/voice/upload-audio` (REST, not WebSocket). UI shows "Voice will process when you're back online" affordance.

This pattern is established in FE-B3 (deferred voice path) and integrated into FE-B7 (full offline sync).

### 12.4 Voice UI state machine

The six-state voice indicator (per Pass 1 spec):

```text
idle → listening → processing → (waiting-confirm | speaking) → idle
                                                  ↓
                                                error
```

Encoded in the Zustand `useVoiceSessionStore` (§4.2). UI components subscribe and render appropriate visual state.

### 12.5 Confirm-as-turn (§16.3)

For voice-triggered actions with side effects (send message, approve, resolve, etc.), the AI generates a confirmation prompt; UI renders via `<VoiceConfirmTurn>`; user's affirmative voice input commits via the original intent's commit endpoint; anything else cancels.

```tsx
import { VoiceConfirmTurn } from '@pilot/ui/voice-confirm-turn';

<VoiceConfirmTurn
  prompt={awaitingConfirm.prompt}
  onConfirm={() => commitIntent(awaitingConfirm.intentId)}
  onCancel={() => cancelIntent(awaitingConfirm.intentId)}
/>
```

---

## 13. Accessibility Standards

Pilot targets **WCAG 2.1 AA** as a floor, AAA where reasonable. Accessibility is a Definition of Done item, not a polish phase.

### 13.1 Per-surface requirements

- **Color contrast**: AA minimum (3:1 for large text, 4.5:1 for body, 7:1 for AAA). Pass 1 token palette is pre-vetted; if you stay on tokens, you're compliant.
- **Keyboard navigation**: every interactive element reachable via Tab; focus order matches visual order; visible focus indicators (Pass 1 token: `--ring-color`).
- **Screen reader**: every interactive element has a meaningful accessible name (`aria-label`, `aria-labelledby`, or text content).
- **ARIA live regions**: dynamic content (loading, success, error) announced to screen readers via `aria-live="polite"` (or `assertive` for errors).
- **Mobile touch targets**: 44×44 px minimum (Gluestack `size="xl"` on `Button`).
- **Mobile accessibility**: every interactive element has `accessibilityLabel`; `testID` for e2e targeting.

### 13.2 axe-core integration

```typescript
// apps/web/__tests__/batch_fe_b{N}/{surface}.integration.test.tsx
import { render } from '@testing-library/react';
import { axe, toHaveNoViolations } from '@axe-core/react';

expect.extend(toHaveNoViolations);

it('has no accessibility violations', async () => {
  const { container } = render(<MyNewSurface />);
  const results = await axe(container);
  expect(results).toHaveNoViolations();
});
```

**Zero axe violations is the gate.** A surface with violations does not pass batch completion. Mobile uses `@axe-core/react-native` where supported; manual audit fallback otherwise.

### 13.3 Manual keyboard / screen reader audit

For each new surface:
1. Tab through every interactive element. Focus order matches visual order? Every element reachable?
2. Test with screen reader (VoiceOver on macOS/iOS, TalkBack on Android, NVDA on Windows). Every element has meaningful announcement?
3. Test with browser zoom at 200%. Layout still usable?

These manual audits are part of Phase 2 Step 9 (Visual Review) in the workflow.

---

## 14. Testing Strategy & Automation

> **📖 Authoritative test mechanics references — read these before writing any test:**
> - **Web**: `frontend/apps/web/README-adding-tests.md`
> - **Mobile**: `frontend/apps/mobile/README-adding-tests.md`
>
> Those files contain the canonical run commands, file placement rules, MSW setup patterns, WatermelonDB mock rules, and anti-patterns. The sections below provide the strategic overview. When in doubt about mechanics, the READMEs take precedence.

Per `pilot-app-mvp-frontend-impl-plan.md` v1.0 §5.5. Three test layers; all required.

---

### 14.0 Canonical Run Commands

#### ⚠️ ALWAYS append `| tail -N` to reduce token consumption

```bash
# ── Full suite — run from workspace root ──────────────────────────────────────
cd <repo>/frontend

pnpm --filter @pilot/ui check-types && \
pnpm --filter web check-types && \
pnpm --filter mobile build && \
pnpm --filter @pilot/ui lint && \
pnpm --filter web lint && \
pnpm --filter mobile lint && \
echo "=== TYPE+LINT PASS ===" && \
pnpm --filter @pilot/ui test 2>&1 | tail -6 && \
pnpm --filter web test 2>&1 | tail -6 && \
pnpm --filter mobile test 2>&1 | tail -8 && \
echo "=== MVP FINAL VERIFICATION COMPLETE ==="
```

> **Note on `mobile build`**: The mobile app has no `check-types` script. `pnpm --filter mobile build` runs `tsc --noEmit` (see `apps/mobile/package.json`). This is the correct type-check command for mobile.

#### Targeted runs (faster — use during development)

```bash
# Web tests only
pnpm --filter web test 2>&1 | tail -6

# Mobile tests only
pnpm --filter mobile test 2>&1 | tail -8

# Single web test file
pnpm --filter web test -- __tests__/batch_fe_b5/quote-approval.integration.test.tsx 2>&1 | tail -10

# Single mobile test file
pnpm --filter mobile test -- features/jobs/components/__tests__/JobCardRow.test.tsx 2>&1 | tail -10

# Mobile tests by batch folder
pnpm --filter mobile test -- __tests__/batch_mob_b1/ 2>&1 | tail -10

# Type-check only (no tests)
pnpm --filter web check-types
pnpm --filter mobile build 2>&1 | tail -10
```

#### Always capture regression baseline before making changes

```bash
# Run from frontend/ root
pnpm --filter mobile test 2>&1 | tail -8
pnpm --filter web test 2>&1 | tail -6
```

Record the exact counts (e.g., `Tests: 369 passed, 369 total`). After changes, verify the delta matches exactly what you added.

---

### 14.1 Unit tests (Vitest web; Jest mobile)

Co-located with components. Test in isolation; mock external dependencies (API via MSW, navigation via mocked router, timers via fake timers).

**Per-component coverage MUST cover**:
- Default render with required props
- All prop variants that change visual or behavioral output
- All user interactions (click, hover, focus, keyboard nav)
- All error states
- ARIA roles + accessibility attributes
- Token consumption (no hardcoded design values — verified by ESLint, not test)

**Critical rules for all unit tests:**
- **Web**: Use `@testing-library/react` + Vitest globals (`describe`, `it`, `vi`)
- **Mobile**: Use `@testing-library/react-native` + Jest (`describe`, `it`, `jest.fn()`)
- **Always set `retry: false`** on `QueryClient` — prevents infinite retry loops
- **Always use `findBy*` (async) for data that loads asynchronously** — never `getBy*` for async data
- **MSW handlers always from `msw/node`** — never `msw/browser` in tests

```tsx
// packages/ui/src/notification-banner/web/NotificationBanner.test.tsx
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { NotificationBanner } from './NotificationBanner';

describe('<NotificationBanner>', () => {
  it('renders title and detail', () => {
    render(<NotificationBanner severity="info" title="Hello" detail="World" />);
    expect(screen.getByRole('alert')).toBeInTheDocument();
    expect(screen.getByText('Hello')).toBeInTheDocument();
  });

  it('auto-dismisses standard severity at 6s', async () => {
    vi.useFakeTimers();
    const onDismiss = vi.fn();
    render(<NotificationBanner severity="info" title="Hi" onDismiss={onDismiss} />);
    vi.advanceTimersByTime(6000);
    expect(onDismiss).toHaveBeenCalled();
    vi.useRealTimers();
  });
});
```

### 14.2 Integration tests (Vitest web; Jest mobile, both with MSW)

Live under `apps/{web|mobile}/__tests__/batch_{N}/`. Test a surface's primary user flow with TanStack Query wired against MSW.

**Folder naming**: `batch_fe_b{N}` for web/shared batches, `batch_mob_b{N}` for mobile-only batches, `batch_beta_*` for beta fix batches.

**Per-surface coverage MUST cover**:
- Primary happy path (the design spec's main mockup)
- At least one error/recovery path
- Loading + empty states render correctly
- RBAC: surface gated to expected roles
- Cross-component coordination (banner appears after submit, modal closes on confirm, etc.)

**MSW server setup — always use `msw/node` + reset per test**:

```typescript
import { setupServer } from 'msw/node';  // ← node, not browser
const server = setupServer(...handlers);
beforeAll(() => server.listen({ onUnhandledRequest: 'warn' }));
afterEach(() => server.resetHandlers());   // ← critical — resets per-test overrides
afterAll(() => server.close());
```

**QueryClient — always `retry: false`**:

```typescript
// ✅ CORRECT
const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
});
```

**Mobile-specific: always mock `expo-router`**:

```typescript
const mockPush = jest.fn();
jest.mock('expo-router', () => ({
  useRouter: () => ({ push: mockPush, back: jest.fn(), replace: jest.fn() }),
  useLocalSearchParams: () => ({}),
  router: { push: mockPush, back: jest.fn() },
}));
```

**Mobile-specific: always mock WatermelonDB for offline-write hook tests**:

```typescript
jest.mock('../../../database', () => ({
  database: {
    write: jest.fn((fn) => fn()),
    get: jest.fn(() => ({
      create: jest.fn((fn) => {
        const record = { id: 'mock-id', localSyncStatus: 'pending' };
        fn(record);
        return Promise.resolve(record);
      }),
    })),
  },
}));
```

### 14.3 E2E tests

#### Web: Playwright

See `apps/web/README-playwright.md` for setup.

```bash
pnpm --filter web e2e
```

#### Mobile: Maestro (preferred)

Maestro is YAML-based. See `apps/mobile/README-maestro.md` for setup.

```bash
maestro test e2e/batch_mob_b{N}/my-flow.flow.yaml
```

### 14.4 Test growth targets

Per impl plan v1.0 §5.5, minimums per batch (cumulative end-state: ~1,030 unit + ~236 integration + ~51 e2e by FE-B16). Hit the targets; exceeding them is encouraged where surface complexity warrants.

### 14.5 Anti-patterns to never repeat

| ❌ Wrong | ✅ Correct |
|:---|:---|
| Mock `apiClient` directly with `jest.mock()` | Use MSW to intercept at the HTTP layer |
| `const queryClient = new QueryClient()` (no retry override) | Always set `retry: false` in test `QueryClient` |
| `screen.getByText("data")` for async data | Use `await screen.findByText("data")` |
| `import { setupServer } from 'msw/browser'` in tests | Always `msw/node` in Jest/Vitest |
| Forget `server.resetHandlers()` in `afterEach` | Per-test overrides leak without this |
| Put integration tests co-located with source | Integration tests go in `__tests__/batch_{N}/` |
| Write to real WatermelonDB in mobile tests | Always mock the `database` module |
| Run tests without `2>&1 \| tail -N` | Always tail output to reduce token usage |

---

## 15. Common Anti-Patterns — Never Do These

| ❌ Wrong | ✅ Correct |
|:---|:---|
| Storing API arrays in Zustand | Use TanStack Query for all server-fetched data |
| Hardcoded colors (`#1a1a1a`) or pixel values (`padding: 13px`) | Pass 1 design tokens via Tailwind / Gluestack — ESLint rule blocks violations |
| Hand-writing TypeScript interfaces for backend payloads | Auto-generated types from `pnpm sync-api-types` + `@pilot/shared-types` |
| Hardcoding API URLs in Axios/fetch | Always use `process.env.NEXT_PUBLIC_API_URL` / `EXPO_PUBLIC_API_URL` |
| Direct `fetch()` or fresh Axios instance | Always use the shared `apiClient` (handles JWT, refresh, idempotency, error parsing) |
| Using raw `fetch('/api/v1/...')` relative paths | Use `apiClient` — raw fetch hits Next.js port 3000, not FastAPI, and has no JWT |
| Writing a hook without checking `backend/openapi_schema_map.md` first | Always verify the exact endpoint path + params in `openapi_schema_map.md` before writing any hook |
| Assuming an endpoint URL pattern from context or naming conventions | `backend/openapi.json` is the only truth — check it; do not infer |
| Assuming a TypeScript interface matches the backend response | Run `pnpm sync-api-types`; import from `@pilot/shared-types`; never hand-write a permanent interface |
| Waiting for full audio recording before sending | Stream audio chunks via WebSocket every 250ms |
| `alert()` for errors | `<NotificationBanner>` parsing RFC 7807; severity drives visual class |
| `try { } catch (e) { console.log(e); }` swallowing errors | Re-throw or surface via `<NotificationBanner>`; never swallow silently |
| Disabled / greyed-out unauthorized buttons | Hide-not-disable: use `<RoleGate>` to render nothing |
| Bypassing the JWT refresh interceptor with custom 401 handling | The interceptor handles it; if you see 401s in your code, the bug is upstream |
| Reimplementing a shared component in a feature folder | Import from `@pilot/ui`; if it doesn't exist there yet, escalate or extend the shared one |
| Forking a shared component to fit your edge case | Add a polymorphic `variant` prop to the shared component; never fork |
| Inventing a new visual treatment for a §16 platform pattern | Use the canonical component for that pattern (see §9 of this doc) |
| Skipping `accessibilityLabel` / `testID` on mobile interactive elements | Required on every interactive element — Maestro/Detox depend on it |
| Using `@ts-ignore` or `any` to suppress type errors | Fix the types; if the underlying type is wrong, fix it at the source (often `pnpm sync-api-types`) |
| Adding a CSS file or `style={{}}` inline object | Tailwind utilities (web) or Gluestack props (mobile); extend the preset/config if needed |
| Persisting a backend-derived value in Zustand "for performance" | Trust TanStack Query's cache; if perf is a concern, configure `staleTime` |
| Manually computing field-level diff client-side | Backend computes diff at conflict-detection time (BE-B6/A32, BE-B7b/A40); UI just renders via `<DiffView>` |
| Local timezone arithmetic on `created_at` / `captured_at` | All timestamps server-side are UTC; format via `date-fns-tz` with user's tenant timezone |
| Calling backend without `X-Idempotency-Key` for offline-capable mutations | Always generate UUID idempotency key for mutations that could replay (offline writes, retries) |
| Mixing live and snapshot rendering modes within a single message lifecycle | A message starts `live`, transitions to `snapshot` exactly once; UI honors the transition |
| Skipping the always-preview-before-send step on a comm path | `<MessagePreviewModal>` is mandatory; there is no "send without preview" affordance |

---

## 16. Standard Implementation Task Workflow

Every frontend task — every surface, every component, every feature — follows the same workflow. **Do not skip phases. Do not reorder.**

### 16.1 The three-phase batch process

This workflow integrates with `pilot-app-mvp-frontend-impl-plan.md` v1.0 §5. A "task" is typically a surface within a batch; the batch as a whole moves through the three phases.

```
Phase 1: Surface Design Session  →  Phase 2: Implementation  →  Phase 3: Batch Completion Gate
   (Architect leads; produces        (React Engineer executes      (Tom + React Engineer
    batch design doc)                  Standard Task Workflow)       verify against gates)
```

### 16.2 Phase 1: Surface Design Session — required reads

Before any code is written, complete all required reads. Do not begin the design doc until done.

1. **Read every Pass 1–4 spec doc in `dev-docs/architecture-design/`** referenced by the batch. The impl plan section is a summary; the spec docs are authoritative.
2. **Cross-reference `mvp-arch.md`** for any §16 platform patterns this batch consumes or extends.
3. **Cross-reference this methods doc** to identify which sections of the workflow apply (token consumption, MSW handler authoring, accessibility audit, etc.).
4. **Verify every endpoint this batch will consume** — mandatory, in this order:
   - Check **`backend/openapi_schema_map.md`** for the human-readable endpoint summary (fast lookup of path, params, response shape).
   - If more detail needed, check **`backend/openapi.json`** for the full spec.
   - Run `pnpm sync-api-types` to refresh `packages/shared-types/src/api-schema.d.ts` with the latest generated types.
   - **If an endpoint is not in `openapi.json`, it does not exist. Do not invent a URL. Stop and ask Tom.**
5. **Check `backend/db_models_map.md`** to understand the entity model for any new surfaces (which models drive the API, which are enums vs tables).
6. **Read the actual frontend code** that this batch will extend or consume — mandatory:
   - Relevant feature folders in `apps/{web|mobile}/src/features/`
   - Shared components in `packages/ui/src/`
   - Shared hooks
   - Routing config
7. **Identify all new components, surfaces, routes, and shared utilities** the batch introduces. Write them down. Confirm via codebase grep that anything listed as "new" doesn't already exist.
8. **Identify pattern reuse decisions** — every shared module the batch establishes or consumes, with exact import paths.
9. **Document open questions** with proposed resolutions. No design doc with unresolved interaction questions.

**Output**: `dev-docs/architecture-design/batch-designs/batch-fe-b{N}-design.md` containing sections A–I per impl plan v1.0 §5 Phase 1.

### 16.3 Phase 2: Implementation — Standard Task Workflow per surface

Each surface within the batch is executed using this 9-step loop:

```text
Pre-Work:  Capture regression baseline
   ↓        (run all unit + integration tests; record pass count)
   ↓
Step 1:   Component scaffolding
   ↓        - Files in correct feature folder
   ↓        - Imports from packages/ui/ where shared component exists
   ↓        - TypeScript interfaces drafted for props
   ↓
Step 2:   Pass 1 token consumption
   ↓        - Verified by ESLint rule `no-hardcoded-design-values`
   ↓        - Tailwind utilities resolve to tokens (web)
   ↓        - Gluestack props resolve to tokens (mobile)
   ↓
Step 3:   TanStack Query / MSW wiring
   ↓        - Hooks call apiClient with auto-generated types
   ↓        - MSW handler written for any in-flight backend endpoint
   ↓        - Error handling parses RFC 7807 → <NotificationBanner>
   ↓        - X-Idempotency-Key on offline-capable mutations
   ↓
Step 4:   Surface composition
   ↓        - Page-level component composes feature components
   ↓        - All shared components consumed via packages/ui imports
   ↓        - Loading + empty + error states wired (states catalog)
   ↓
Step 5:   Routing wiring
   ↓        - File-based route added (App Router web / Expo Router mobile)
   ↓        - <RoleGate> applied at appropriate level
   ↓        - Deep links from notifications functional
   ↓
Step 6:   Unit test coverage
   ↓        - Co-located component tests (Vitest web / Jest mobile)
   ↓        - Coverage: default render, all variants, all interactions, all errors, a11y
   ↓
Step 7:   Integration test coverage
   ↓        - Surface-level tests under apps/{web|mobile}/__tests__/batch_fe_b{N}/
   ↓        - MSW for backend; primary happy path + at least one error path
   ↓        - axe-core check returns zero violations
   ↓
Step 8:   E2E test coverage (Playwright web / Maestro mobile)
   ↓        - Critical user journey covered
   ↓        - Cross-platform surfaces: e2e on both platforms
   ↓
Step 9:   Visual review
            - Manual review against design spec mockup
            - Manual keyboard navigation audit
            - Manual screen reader audit (sample, not exhaustive)
```

### 16.4 File path conventions

```text
# Surface-specific components:
apps/{web|mobile}/src/features/{kebab-surface-name}/components/{ComponentName}.tsx

# Shared components:
packages/ui/src/{kebab-component-category}/{ComponentName}.tsx
  (with web/ and mobile/ subfolders if platform-specific implementations needed)

# Surface-specific hooks:
apps/{web|mobile}/src/features/{surface}/hooks/use{HookName}.ts

# Shared hooks:
packages/ui/src/hooks/use{HookName}.ts          (cross-platform)
apps/{web|mobile}/src/hooks/use{HookName}.ts    (platform-specific)

# Tests:
{ComponentFile}.test.tsx                        (co-located unit tests)
apps/{web|mobile}/__tests__/batch_fe_b{N}/{surface}.integration.test.tsx
apps/web/e2e/batch_fe_b{N}/{flow}.e2e.spec.ts
apps/mobile/e2e/batch_fe_b{N}/{flow}.flow.yaml  (Maestro)
```

### 16.5 Phase 3: Batch Completion Gate

A batch is not complete until:

- [ ] All surfaces in the batch are individually complete per the Definition of Done (§18)
- [ ] Every new component consumes Pass 1 design tokens — ESLint `no-hardcoded-design-values` passes with zero warnings
- [ ] Every new component has unit test coverage — target 100% of public component API; minimum 90%
- [ ] Every new surface has at least one integration test covering the primary user flow
- [ ] Cross-platform surfaces have at least one e2e test per platform
- [ ] All shared components introduced by this batch are exported from `packages/ui/src/index.ts`
- [ ] Accessibility audit (axe-core) returns zero violations on every new surface
- [ ] No regressions: full test suite (unit + integration + e2e) passes — pass-count delta recorded
- [ ] Impl plan §7 Tracker updated for this batch with component manifest, test files, test count delta

The frontend equivalent of the backend's "schema-diff = ZERO" gate is:
- ESLint `no-hardcoded-design-values` rule passes with zero warnings
- axe-core returns zero violations on every new surface
- Integration tests pass against real backend (or stable MSW)
- Every shared component added to `packages/ui/src/index.ts` manifest

---

## 17. Stop & Rollback Conditions

Halt immediately and do not proceed if:

- **TypeScript fails** (`pnpm --filter @pilot/ui check-types` / `pnpm --filter web check-types` / `pnpm --filter mobile build` errors). Do not bypass with `@ts-ignore` or `any`. Fix the types — most often the fix is `pnpm sync-api-types` to refresh from backend.
- **ESLint `no-hardcoded-design-values` fires.** Fix the violation by using a Pass 1 token. If a needed value is missing from tokens, raise the question — do not invent a value.
- **E2E timeout** (Playwright / Maestro). UI is likely blocking the main thread or missing a loading state. Add `<LoadingState>` from FE-B1; verify async flows via React DevTools.
- **Memory leak from WebSocket / SSE listener.** Verify `useEffect` cleanup function calls `.close()` (or `EventSource.close()`). React strict mode in dev catches most; production-only leaks signal a missed cleanup.
- **axe-core returns violations.** Fix accessibility issues before progressing. The most common: missing `aria-label` on icon-only buttons; missing `aria-live` on async-updating regions; insufficient color contrast (token mismatch).
- **Backend OpenAPI schema mismatch.** If the auto-generated types don't match what the backend returns, escalate — do not paper over with a hand-written type. The backend or the type-sync script needs fixing.
- **Skeleton component public API change.** If you're fleshing out a skeleton (e.g., `<MFAEnrollmentWizard>` in FE-B12) and the existing prop interface doesn't fit, escalate — do not change the API in ways that break FE-B1 consumers.

---

## 18. Definition of Done Checklist

Every frontend task is **not complete** until every item below is checked:

### Code

- [ ] Component files placed in correct location per §1 placement rules (surface-specific vs shared; web vs mobile vs cross-platform)
- [ ] TypeScript types match backend Pydantic models via auto-generated `@pilot/shared-types`
- [ ] No hand-written interfaces for backend payloads
- [ ] All TypeScript strict-mode errors resolved (no `@ts-ignore`, no `any` without justification)

### State

- [ ] Server state managed entirely by TanStack Query (no API data in Zustand)
- [ ] Client state in Zustand only when ephemeral / cross-component / multi-step
- [ ] `staleTime` configured appropriately for query freshness needs

### API

- [ ] All API calls go through shared `apiClient` (no direct `fetch` or fresh Axios)
- [ ] `X-Idempotency-Key` (UUID) attached to all offline-capable mutations
- [ ] RFC 7807 error responses parsed and surfaced via `<NotificationBanner>` (severity-mapped)
- [ ] MSW handler exists for any backend endpoint not yet deployed (mock-driven dev)

### UI

- [ ] All colors, fonts, spacing values come from Pass 1 tokens (ESLint `no-hardcoded-design-values` passes)
- [ ] No CSS files; no inline `style={{}}` objects
- [ ] Tailwind utilities (web) and Gluestack props (mobile) used for all styling
- [ ] Loading + empty + error states wired via FE-B1 states catalog components
- [ ] Pattern reuse: every §16 platform pattern this surface needs is consumed via the canonical shared component (no reimplementation)
- [ ] Mobile: minimum 44×44 px touch targets via Gluestack `size="xl"` or equivalent

### Auth & RBAC

- [ ] Authenticated routes wrapped in `<RequireAuth>` (or under `(authed)/` route group)
- [ ] Role-gated elements use `<RoleGate>` (hide-not-disable)
- [ ] No custom 401 handling — JWT refresh interceptor handles silently

### Voice (if applicable)

- [ ] WebSocket streaming via `useVoiceStream()` — audio chunks sent at 250ms intervals (no waiting for full recording)
- [ ] Live → snapshot rendering transition honored (no reverse transition)
- [ ] Offline path: deferred-voice queue persists across app restarts; uploads on reconnect via REST
- [ ] Confirm-as-turn pattern used for high-stakes voice actions

### Offline (mobile, if applicable)

- [ ] WatermelonDB models defined; offline writes persist locally first, queue for sync
- [ ] Sync orchestrator handles four-class conflict severity correctly
- [ ] `<PendingBadge>` surfaced for entities with non-`synced` status

### Accessibility

- [ ] axe-core returns zero violations on the surface
- [ ] Manual keyboard nav audit completed: every interactive element reachable; focus order correct; visible focus indicators
- [ ] Manual screen reader audit completed (sample): meaningful announcements
- [ ] Mobile: every interactive element has `accessibilityLabel` and `testID`

### Tests

- [ ] Pre-modification regression baseline captured (test pass count recorded)
- [ ] Unit tests written for new components — coverage minimum 90% of public API
- [ ] Integration test covers primary happy path + at least one error/recovery path
- [ ] E2E test (Playwright web / Maestro mobile) covers critical user journey
- [ ] Cross-platform surfaces: e2e on both platforms
- [ ] Full test suite passes locally: `pnpm --filter @pilot/ui test && pnpm --filter web test && pnpm --filter mobile test`
- [ ] E2E passes locally: `pnpm --filter web e2e && pnpm --filter mobile e2e`

### Build & Lint

- [ ] Type-check passes with zero errors: `pnpm --filter @pilot/ui check-types && pnpm --filter web check-types && pnpm --filter mobile build`
- [ ] `pnpm lint` passes with zero warnings (including `no-hardcoded-design-values` rule)
- [ ] `pnpm build` (web) compiles with zero errors
- [ ] `pnpm --filter mobile expo export` compiles with zero errors

### Component manifest (if shared component added)

- [ ] New shared component exported from `packages/ui/src/index.ts`
- [ ] Component public API (props interface) documented in component file's JSDoc
- [ ] Component listed in §8 catalog of this methods doc *(or escalate to add it)*

### Documentation

- [ ] Batch design doc (`dev-docs/architecture-design/batch-designs/batch-fe-b{N}-design.md`) reflects implemented decisions
- [ ] Impl plan §7 Tracker row updated with completion data (component manifest, test files, test count delta)

---

*This document is version 2.2. It is aligned to `pilot-app-mvp-frontend-arch-impl-plan.md` v3.0 (foundational architecture) and `pilot-app-mvp-frontend-impl-plan.md` v1.0 (batch sequencing). Updates to this doc happen when (a) new platform patterns emerge worth canonicalizing, (b) new shared components are added to the catalog, (c) the workflow steps change based on retrospective learning, or (d) a new tech-stack decision changes the standards.*

*Cross-reference docs*:
- `pilot-app-mvp-frontend-arch-impl-plan.md` v3.0 — tech stack, monorepo structure, Phase 0
- `pilot-app-mvp-frontend-impl-plan.md` v1.0 — batches FE-B0 through FE-B16
- `pilot-app-mvp-implementation-framework.md` v1.1 — cross-workstream coordinator
- `mvp-arch.md` v5 — §16 platform patterns
- `mvp-prd.md` v3.1 — product domains
- `frontend-mvp-design-framework.md` v3 — design phase summary
