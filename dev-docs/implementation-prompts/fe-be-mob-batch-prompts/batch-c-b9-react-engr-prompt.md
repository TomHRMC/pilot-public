# Implementation Prompt: C-B9 — Messaging Setup Page (Web)

**Mode**: Pilot React Engineer
**Batch**: C-B9 (Part B — Frontend)
**Source plan**: `pilot-launch-plan.md` §2.0 row 14n
**Design doc**: `batch-c-b9-design.md` — read §D (endpoints), §H (surface reference), §I (component manifest)
**UI design spec**: `batch-c-b9-ui-design-spec.md` — read ALL 14 sections before writing any code. This is the authoritative UI spec — follow it exactly.
**Estimated session**: 3–5 hours
**Platform**: Web only (`apps/web`)
**Backend companion**: C-B9 Part A (Python Engineer) — **must complete first**. This prompt depends on the backend endpoints being live in `openapi.json`.

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-react-engineer/react-engineer-rules.md`** — in full
- **`dev-docs/architecture-design/batch-designs/batch-c-b9-design.md`** — §D (API endpoints), §H (surface reference), §I (component manifest)
- **`dev-docs/architecture-design/batch-designs/batch-c-b9-ui-design-spec.md`** — ALL 14 sections. This is the authoritative UI spec.

Critical rules for this batch:

- **Rule 1.1**: Before writing ANY hook or API call, verify the endpoint exists in `backend/openapi_schema_map.md`. If it is NOT there → **STOP and ask Tom**.
- **Rule 1.3**: Run `pnpm sync-api-types` before starting — all TypeScript types for backend payloads come from `@pilot/shared-types`, never hand-written interfaces.
- **Rule 2**: All API calls use `apiClient` from `@pilot/shared-api`. `fetch()` is permanently banned for `/api/v1/...` calls.
- **Rule 7**: Check `packages/ui/src/index.ts` before creating any new component — `<LoadingState>`, `<ErrorState>`, `<EmptyState>`, `<RoleGate>` are all available.
- **Rule 9**: Route files in `apps/web/src/app/(authed)/` MUST be thin server components — no `"use client"`, no data fetching. All logic goes in feature components.
- **Rule 10**: If ANY test fails during your work — fix it before declaring the batch done.
- **Rule 11 (React Compiler)**: Do NOT hand-write `useMemo`/`useCallback`/`React.memo` for render-perf — the compiler handles it.
- **Rule 12 (TanStack Query v5)**: Object-form API only (`useQuery({ queryKey, queryFn })`). `gcTime` not `cacheTime`; `isPending` not `isLoading`. Colocate query keys.
- **Rule 13 (Zod v4 + RHF)**: Form validation via `zodResolver`. Infer API types from `@pilot/shared-types`.
- **Rule 14 (server vs client)**: Data fetching stays client-side. Never fetch tenant data in a Server Component.
- **Rule 15 (WCAG 2.2 AA)**: Every new surface must satisfy Focus Not Obscured, Target Size (≥24×24px), Accessible Authentication, non-color-only errors.

---

## Pre-Work: Establish Regression Baseline

Before touching any file:

```bash
cd <repo>/frontend
pnpm --filter web test 2>&1 | tail -5
```

Record the exact count. These must still pass at the end of the batch.

> **If any tests are already failing**: Do NOT proceed. Either confirm with Tom or fix before starting.

---

## Pre-Work: Sync API Types

```bash
cd <repo>/frontend
pnpm sync-api-types
```

This regenerates `packages/shared-types/src/api-schema.d.ts` from the live backend `openapi.json`. All backend payload types must come from `@pilot/shared-types` — never hand-written.

Consume types via the `components` root:
```typescript
import type { components } from "@pilot/shared-types";
type ProvisionResponse = components["schemas"]["ProvisionResponse"];
```

---

## Pre-Work: Verify Endpoints

For each new hook, verify the endpoint exists:

```bash
grep -A 5 "messaging/provision" backend/openapi_schema_map.md
grep -A 5 "messaging/checkout" backend/openapi_schema_map.md
grep -A 5 "messaging/otp" backend/openapi_schema_map.md
grep -A 5 "messaging/status" backend/openapi_schema_map.md
grep -A 5 "messaging/retry" backend/openapi_schema_map.md
grep -A 5 "messaging/verticals" backend/openapi_schema_map.md
grep -A 5 "messaging/available-numbers" backend/openapi_schema_map.md
grep -A 5 "messaging/assign-number" backend/openapi_schema_map.md
```

Verified endpoints for this batch:
| Hook | Endpoint | Verified |
|---|---|---|
| `useInitiateProvisioning` | `POST /api/v1/tenants/{tenant_id}/messaging/provision` | ☐ |
| `useCreateCheckout` | `POST /api/v1/tenants/{tenant_id}/messaging/checkout` | ☐ |
| `useSubmitOtp` | `POST /api/v1/tenants/{tenant_id}/messaging/otp` | ☐ |
| `useProvisioningStatus` | `GET /api/v1/tenants/{tenant_id}/messaging/status` | ☐ |
| `useRetryProvisioning` | `POST /api/v1/tenants/{tenant_id}/messaging/retry` | ☐ |
| `useCarrierVerticals` | `GET /api/v1/tenants/{tenant_id}/messaging/verticals` | ☐ |
| `useAvailablePhoneNumbers` | `GET /api/v1/tenants/{tenant_id}/messaging/available-numbers` | ☐ |
| `useAssignPhoneNumber` | `POST /api/v1/tenants/{tenant_id}/messaging/assign-number` | ☐ |
| `useCarrierQuote` | `GET /api/v1/tenants/{tenant_id}/messaging/quote` (C-B8, reused) | ☐ |

**If any endpoint is NOT in `openapi_schema_map.md` → STOP. Do not invent a URL. Ask Tom.**

---

## Pre-Work: Read These Source Files

Read each of these with `read_file` before writing any code:

```
frontend/apps/web/src/app/(authed)/settings/page.tsx          ← why: understand existing settings route structure
frontend/apps/web/src/features/settings/components/SettingsSidebar.tsx  ← why: add "Messaging Setup" nav item (per UI spec §14 item 2)
frontend/packages/ui/src/index.ts                             ← why: confirm shared component imports before use
frontend/apps/web/src/mocks/handlers/index.ts                  ← why: understand how to register new MSW handlers
frontend/apps/web/src/features/messaging/                      ← why: check if any messaging feature files already exist
```

Also run:
```bash
find frontend/apps/web/src/features -name "use*Messaging*.ts" -o -name "use*Provision*.ts" -o -name "use*Carrier*.ts" | head -10
find frontend/apps/web/src/mocks/handlers -name "*.ts" | head -20
grep -n "RoleGate\|LoadingState\|ErrorState\|EmptyState" frontend/packages/ui/src/index.ts
```

---

## Design Decisions (Do Not Re-Litigate)

From the UI design spec §14 Handoff Gate — these decisions are final:

| Decision | Outcome | Rationale |
|---|---|---|
| Route placement | `(authed)/settings/messaging/` | Matches existing settings route structure (Tom confirmed) |
| SettingsSidebar | Add "Messaging Setup" under "Branding" | Tom confirmed |
| State machine | 13 states incl. `awaiting_number_selection` | UI spec §14 item 5 — tenant picks their number |
| Verticals | `GET /messaging/verticals` proxies Telnyx `/enum/vertical` | Adapter pattern — frontend never calls Telnyx directly |
| Phone number selection | `awaiting_number_selection` state + `GET /available-numbers` + `POST /assign-number` | UI spec §14 item 5 — tenant searches by area code, picks number |
| Millicents | Amounts in millicents (1 millicent = $0.00001) | Display as dollars with 2 decimal places |

These were resolved in the design doc + UI spec. Do NOT change them without asking Tom.

---

## Platform: Web (`apps/web`) — Mandatory Constraints

- **Route files are thin server components**: `app/(authed)/settings/messaging/page.tsx` must NOT have `"use client"`, must NOT fetch data. One line: `return <MessagingSetupPage />;`
- **Feature components own logic**: All `"use client"`, hooks, state, and data fetching belong in `features/messaging/components/` or `features/messaging/hooks/`
- **RBAC gating**: Use `<RoleGate permission="settings.manage">` from `@pilot/ui/role-gate`
- **State lifecycle**: Use `<LoadingState>`, `<ErrorState>`, `<EmptyState>` from `@pilot/ui/states`
- **React Compiler**: Do NOT hand-write `useMemo`/`useCallback`/`React.memo`
- **TanStack Query v5**: Object-form only; colocate query keys; `placeholderData: keepPreviousData` for paginated lists; invalidate after mutations
- **Zod v4 + RHF**: Validate forms with `zodResolver`; infer API types from `@pilot/shared-types`
- **Test framework**: Vitest + `@testing-library/react` — use `vi.mock()`, `toBeInTheDocument()`
- **Mock Next.js in tests**: `vi.mock("next/navigation", ...)` and `vi.mock("next/link", ...)`

---

## Task 1 — Route + Page Shell

Per UI design spec §3 (route placement) + §14 item 1:

1. Create `apps/web/src/app/(authed)/settings/messaging/page.tsx` — thin server component, one line: `return <MessagingSetupPage />;`
2. Create `apps/web/src/features/messaging/components/MessagingSetupPage.tsx` — main orchestrator component (`"use client"`, polls `GET /messaging/status`, switches panels based on status)
3. Add "Messaging Setup" to `SettingsSidebar` under "Branding" (per UI spec §14 item 2)

Run: `pnpm --filter web test 2>&1 | tail -6`

---

## Task 2 — Hooks (8 TanStack Query hooks)

Per UI design spec §10 (hooks table) + design doc §I:

Create in `apps/web/src/features/messaging/hooks/`:

| Hook | File | Type | Query Key | Notes |
|---|---|---|---|---|
| `useInitiateProvisioning` | `useInitiateProvisioning.ts` | Mutation | — | `POST /messaging/provision`, Idempotency-Key |
| `useCreateCheckout` | `useCreateCheckout.ts` | Mutation | — | `POST /messaging/checkout`, Idempotency-Key |
| `useSubmitOtp` | `useSubmitOtp.ts` | Mutation | — | `POST /messaging/otp` |
| `useProvisioningStatus` | `useProvisioningStatus.ts` | Query | `["messaging", "status"]` | Polls when status is pending (brand_submitted, campaign_submitted) |
| `useRetryProvisioning` | `useRetryProvisioning.ts` | Mutation | — | `POST /messaging/retry` |
| `useCarrierVerticals` | `useCarrierVerticals.ts` | Query | `["messaging", "verticals"]` | `staleTime: 3600000` (1h cache) |
| `useAvailablePhoneNumbers` | `useAvailablePhoneNumbers.ts` | Query | `["messaging", "available-numbers", areaCode]` | Enabled when areaCode provided |
| `useAssignPhoneNumber` | `useAssignPhoneNumber.ts` | Mutation | — | `POST /messaging/assign-number`, Idempotency-Key |

Also reuse `useCarrierQuote` from C-B8 (already exists or create if not).

All hooks: `apiClient` from `@pilot/shared-api`, types from `@pilot/shared-types`, `retry: false` in tests.

Run: `pnpm --filter web test 2>&1 | tail -6`

---

## Task 3 — Components (10 components)

Per UI design spec §4 (component specs) + design doc §I:

Create in `apps/web/src/components/settings/messaging/`:

| Component | File | Key behavior |
|---|---|---|
| `EntityTypeSelector` | `EntityTypeSelector.tsx` | "Does your business have an EIN?" Yes/No with help text |
| `BrandRegistrationForm` | `BrandRegistrationForm.tsx` | Form with RHF + Zod, vertical dropdown from `useCarrierVerticals` |
| `CarrierQuoteDisplay` | `CarrierQuoteDisplay.tsx` | Itemized costs in millicents → display as $X.XX |
| `CheckoutRedirectButton` | `CheckoutRedirectButton.tsx` | "Continue to payment" → `useCreateCheckout` → redirect to Stripe URL |
| `OtpEntryPanel` | `OtpEntryPanel.tsx` | PIN input + submit, countdown timer from `otp_requested_at` |
| `ProvisioningStatusIndicator` | `ProvisioningStatusIndicator.tsx` | 6-step visual progress (identity → payment → brand → campaign → number → activate) |
| `ProvisioningErrorPanel` | `ProvisioningErrorPanel.tsx` | 3 variants: payment_failed, rejected, suspended |
| `PhoneNumberSelector` | `PhoneNumberSelector.tsx` | Area code search → available numbers list → select → assign |

Also create `apps/web/src/features/messaging/types.ts` for shared types (`MessagingStatus`, `ProvisioningStatus`, `ProvisioningStep`, `AvailablePhoneNumber`).

Follow the UI design spec EXACTLY for:
- Token usage (zero hex codes, `pilotPreset` tokens)
- Accessibility (WCAG 2.2 AA, ≥24×24px targets, `focus-visible` rings, `prefers-reduced-motion`)
- State-driven panel switching (which component shows for which `status` value — see UI spec §3)
- Icon usage (see UI spec §8 icon table)

Run: `pnpm --filter web test 2>&1 | tail -6`

---

## Task 4 — MSW Handlers

Create `apps/web/src/mocks/handlers/messagingProvisioningHandlers.ts` with handlers for all 8 new endpoints + the C-B8 quote endpoint:

```typescript
import { http, HttpResponse } from "msw";

export const messagingProvisioningHandlers = [
  http.post("/api/v1/tenants/:tenantId/messaging/provision", () => HttpResponse.json({ ... })),
  http.post("/api/v1/tenants/:tenantId/messaging/checkout", () => HttpResponse.json({ ... })),
  http.post("/api/v1/tenants/:tenantId/messaging/otp", () => HttpResponse.json({ ... })),
  http.get("/api/v1/tenants/:tenantId/messaging/status", () => HttpResponse.json({ ... })),
  http.post("/api/v1/tenants/:tenantId/messaging/retry", () => HttpResponse.json({ ... })),
  http.get("/api/v1/tenants/:tenantId/messaging/verticals", () => HttpResponse.json({ ... })),
  http.get("/api/v1/tenants/:tenantId/messaging/available-numbers", () => HttpResponse.json({ ... })),
  http.post("/api/v1/tenants/:tenantId/messaging/assign-number", () => HttpResponse.json({ ... })),
];
```

**Register in barrel `index.ts`**:
```typescript
import { messagingProvisioningHandlers } from "./messagingProvisioningHandlers";
export const handlers = [
  ...existingHandlers,
  ...messagingProvisioningHandlers, // ← ADD THIS
];
```

Run: `pnpm --filter web test 2>&1 | tail -6`

---

## Task 5 — Unit Tests

Per UI design spec + React Engineer test standards:

**Unit tests** (co-located with source in `__tests__/`):
- Each component: renders without crashing, correct RBAC, primary content visible with MSW mock, `<LoadingState>` renders while fetching, `<ErrorState>` on API failure
- Each hook: returns data in expected shape, returns error state, correct query key

**Integration tests** in `apps/web/src/__tests__/batch_c_b9/`:
- `messaging-setup.integration.test.tsx` — route does NOT 404, correct RBAC, primary content appears with MSW mock, mutation fires correct HTTP method + URL + payload

Use `createWrapper()` with `retry: false` QueryClient. Use MSW `setupServer` with `server.resetHandlers()` in `afterEach`.

Run: `pnpm --filter web test 2>&1 | tail -6`

---

## Final Verification

> ❌ **BANNED COMMAND**: `npx vitest run` — NEVER use this. Use `pnpm --filter web test` only.

### Phase 1 — Targeted tests (run after each task group)

```bash
cd <repo>/frontend
pnpm --filter web test 2>&1 | tail -6
```

### Phase 2 — Full verification (run once at the very end)

```bash
cd <repo>/frontend && echo "=== UI - Type Check ===" && pnpm --filter @pilot/ui check-types && echo "=== Web - Type Check ===" && pnpm --filter web check-types && echo "=== UI - Lint ===" && pnpm --filter @pilot/ui lint && echo "=== Web - Lint ===" && pnpm --filter web lint && echo "=== TYPE+LINT PASS ===" && echo "=== UI - Tests ===" && pnpm --filter @pilot/ui test 2>&1 | tail -6 && echo "=== Web - Tests ===" && pnpm --filter web test 2>&1 | tail -6 && echo "=== MVP FINAL VERIFICATION COMPLETE ==="
```

---

## Definition of Done — C-B9 Part B

- [ ] Pre-modification regression baseline captured (zero pre-existing failures)
- [ ] `pnpm sync-api-types` run — no new type errors
- [ ] UI design spec fully read before writing any code
- [ ] All mandatory source files read before modifying
- [ ] All 8 endpoint URLs verified in `openapi_schema_map.md`
- [ ] Route file created: `app/(authed)/settings/messaging/page.tsx` (thin server component)
- [ ] `MessagingSetupPage` orchestrator created with state-driven panel switching
- [ ] "Messaging Setup" added to `SettingsSidebar` under "Branding"
- [ ] 8 hooks created in `features/messaging/hooks/`
- [ ] 8 components created in `components/settings/messaging/`
- [ ] `types.ts` shared types file created
- [ ] MSW handler file created + registered in `index.ts` barrel
- [ ] All components use `pilotPreset` tokens (zero hex codes)
- [ ] WCAG 2.2 AA: ≥24×24px targets, `focus-visible` rings, non-color-only errors, `prefers-reduced-motion` fallbacks
- [ ] No hand-written `useMemo`/`useCallback`/`React.memo` (React Compiler)
- [ ] All hooks use TanStack Query v5 object-form + colocated query keys
- [ ] Form validation uses Zod v4 via `zodResolver`; types from `@pilot/shared-types`
- [ ] No tenant-data fetching in Server Components
- [ ] Unit tests pass (targeted run) — one per component + one per hook
- [ ] Integration test passes in `__tests__/batch_c_b9/`
- [ ] Zero TypeScript errors (`check-types` passes)
- [ ] Zero ESLint `no-hardcoded-design-values` warnings
- [ ] No regressions in pre-existing test suite
- [ ] **Phase 2 FULL verification command passes** (`=== MVP FINAL VERIFICATION COMPLETE ===`)
- [ ] Final test count (before → after) documented
- [ ] Completion Summary added to launch plan §Appendix B

---

## Completion Summary

After all Definition of Done items are complete:

1. Add a **Completion Summary** subsection to `pilot-launch-plan.md` §Appendix B.

```markdown
### C-B9 (Part B — React Engineer) — Messaging Setup Page: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot React Engineer
**Baseline**: X passed, Y failed (web)
**Final**: X+N passed, Y failed (+N new tests)

#### What Was Accomplished

- [Brief description of key change 1]
- [Brief description of key change 2]

#### Files Changed / Created

| File | Action |
|---|---|
| `frontend/apps/web/src/app/(authed)/settings/messaging/page.tsx` | Created — thin route |
| `frontend/apps/web/src/features/messaging/components/MessagingSetupPage.tsx` | Created — orchestrator |
| ... | ... |

#### Tests Added

| Test File | Type | Tests | All Pass |
|---|---|---|---|
| `apps/web/src/__tests__/batch_c_b9/messaging-setup.integration.test.tsx` | Integration | N | ✅ |
| `features/messaging/components/__tests__/[Component].test.tsx` | Unit | N | ✅ |
```
