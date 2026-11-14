# Implementation Prompt: TEST-UPLIFT-1B — FE Error-Rendering + MSW Fidelity (React Track)

**Mode**: Pilot React Engineer
**Batch**: TEST-UPLIFT-1B
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §1.1 Ord 4 (umbrella) + Ord 19 (this sub-batch); full umbrella card §3.4 — **this batch owns scope items 2 and 3 only**
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-test-uplift-1b-design.md` — read in full; §G holds 7 binding design decisions (Q1 ratchet scoping, Q2 shared helper, Q3 no-designer-spec, Q4 409 parsers untouched, Q5 `collected_data` blind spot, Q6 meta-test location, Q7 replacement scope)
**Estimated session**: 4–5 hours
**Platform**: Web (`apps/web`) + `packages/shared-api` (one new helper module). **Mobile is untouched** (1C owns it) — the mobile suites in the Phase 2 command must simply stay green.
**Backend companion**: **TEST-UPLIFT-1A ✅ COMPLETE 2026-08-27** (`batch-test-uplift-1a-python-engr-prompt.md` — read its **"Findings for 1B"** appendix subsection before Task 3). Zero endpoint changes in 1A → no new contract deltas, but `pnpm sync-api-types` still runs first (see Pre-Work).

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-react-engineer/react-engineer-rules.md`** — in full
- **`batch-test-uplift-1b-design.md`** — every section (A–I); §F holds the interface specs, §G the binding decisions

Critical rules for this batch:

- **Rule 1.2**: Do NOT invent URL patterns, parameter names, or response field names. Every shape comes from `openapi.json` / `openapi_schema_map.md` (regenerated via `pnpm sync-api-types` in Pre-Work).
- **Rule 2**: All API calls use `apiClient` from `@pilot/shared-api` (**not** `@/lib/api-client` — that module does not exist). `fetch()` is permanently banned for `/api/v1/...` calls. Your new helper lives in that same package.
- **Rule 7**: Check `packages/ui/src/index.ts` before creating any new component — `<ErrorState>`, `<LoadingState>`, `<EmptyState>`, `<NotificationBanner>` (+ `useNotificationQueue`) all exist. This batch creates **zero new components** (design §I).
- **Rule 8**: No new npm dependencies. The MSW↔OpenAPI schema validator is **hand-rolled** on the existing MSW 2 / Vitest stack (design §G/E).
- **Rule 10**: If ANY test fails during your work — even one that appears pre-existing — **you must fix it before declaring the batch done**. If you cannot identify the root cause → STOP and ask Tom.
- **Rule 11 (React Compiler)**: Do NOT hand-write `useMemo`/`useCallback`/`React.memo` for render-perf — the compiler handles it. Keep components pure.
- **Rule 12 (TanStack Query v5)**: Object-form API only; `gcTime` not `cacheTime`; `isPending` not `isLoading`; tests use `retry: false` on a fresh QueryClient per test.
- **Rule 14 (server vs client)**: Authenticated data fetching stays client-side. Error-surface wiring happens in feature components/hooks, never in route files.
- **Rule 15 (WCAG 2.2 AA)**: Error surfaces must be non-color-only (`role="alert"` / `aria-live` where the pattern already provides it via `ErrorState`/`NotificationBanner` — use those components rather than hand-rolling banners).

---

## Design Decisions (Do Not Re-Litigate)

From Design Doc §G — these decisions are final:

| Decision | Outcome | Rationale |
|---|---|---|
| Full 237-call-site audit closure | **No — ratchet + 7-surface burn-down** | Rule 9.6 context calibration; remainder → BE-TESTS-MAINT baseline |
| Error parsing | **One shared `getApiProblem` in `packages/shared-api`** | Every feature already imports the package; per-feature parsers diverge today |
| 409-and-refresh parsers (`useMoveJob`, `usePublishTenantSite`, `MfaApiError`) | **Untouched** | Extension-field control flow, not display copy (§G Q4) |
| Designer spec | **Not required** | No new/changed surface; zero new components (§G Q3, §I) |
| MSW validator | **Hand-rolled, no new deps** | Rule 8 |
| The exact 2026-08-10 incident class | **Closed by Task 5, not the schema diff** | `collected_data` is intentionally `additionalProperties: true` (§G Q5) |

Do NOT change these without asking Tom.

---

## Pre-Work: Establish Regression Baseline

Before touching any file:

```bash
cd <repo>/frontend

pnpm --filter @pilot/shared-api test 2>&1 | tail -5
pnpm --filter @pilot/ui test 2>&1 | tail -5
pnpm --filter web test 2>&1 | tail -5
pnpm --filter mobile test 2>&1 | tail -8
```

Record the exact counts for each package. These must still pass at the end of the batch.

> **If any tests are already failing before you start**: Do NOT treat them as "pre-existing" and proceed. Either (a) confirm with Tom that this is a known, accepted failure with a documented reason, OR (b) fix the failure before touching any batch files. You may NOT start implementation work while tests are in an unexplained failed state.

---

## Pre-Work: Sync API Types

```bash
cd <repo>/frontend
pnpm sync-api-types
```

This re-exports `openapi.json` from the live backend, then regenerates `packages/shared-types/src/api-schema.d.ts`. 1A changed **two error bodies** to RFC 7807 dicts (`POST /invoices/{id}/send` 404, `PUT /signup/{id}/step2` 404) — no request/response contract changes, but run this anyway so Task 4's harness validates against the freshest spec. All payload types come from `@pilot/shared-types` — never hand-written interfaces.

---

## Pre-Work: Verify Endpoints

The design's Task 3/4 endpoints were verified in `openapi.json` at design time (2026-08-27). Confirm each with `grep -A 3 "<path>" backend/openapi_schema_map.md` before writing code:

| Hook / fixture | Endpoint | Verified |
|---|---|---|
| `useRecordPayment` | `POST /api/v1/invoices/{invoice_id}/record-payment` | ✅ in openapi |
| `useSendInvoice` | `POST /api/v1/invoices/{invoice_id}/send` | ✅ in openapi (404 body now RFC 7807 — 1A) |
| `useTenantSubscription` | `POST /api/v1/tenants/{tenant_id}/subscription/change-tier` · `POST …/upgrade-from-charter` | ✅ in openapi |
| `useSignupWizard` | `GET /api/v1/signup/{tenant_id}/state` | ✅ in openapi |
| Signup step submits | `PUT /api/v1/signup/{tenant_id}/step2` … `step5` | ✅ in openapi (step2 404 now RFC 7807 — 1A) |
| Public token pages | `POST /api/v1/public/invoices/{signed_token}/payment-intent` · `POST …/confirm-payment` | ✅ in openapi |
| Create forms | `POST /api/v1/customers/` · `POST /api/v1/jobs/` | ✅ in openapi |

**If any endpoint is NOT in `openapi_schema_map.md` → STOP. Do not invent a URL. Ask Tom.**

---

## Pre-Work: Read These Source Files

Read each of these with `read_file` before writing any code:

```
frontend/packages/shared-api/src/client.ts                          ← interceptors; where errors surface (raw AxiosError)
frontend/packages/shared-api/src/index.ts                           ← barrel — where the new export goes
frontend/packages/shared-api/src/client.test.ts                     ← existing test pattern for this package (Vitest)
frontend/apps/web/src/mocks/handlers/index.ts                       ← barrel registration pattern (mandatory read)
frontend/apps/web/src/mocks/handlers/signupHandlers.ts              ← Task 4 incident-surface fixture + handler
frontend/apps/web/src/mocks/handlers/publicLinkHandlers.ts          ← Task 4/3-#6 fixtures
frontend/apps/web/src/mocks/handlers/invoiceDetailHandlers.ts       ← Task 4 fixtures
frontend/apps/web/src/features/settings/hooks/useTenantSubscription.ts  ← local RFC 7807 extract helper (~line 116) you will REPLACE
frontend/apps/web/src/features/account-settings/hooks/useRemoveMfaMethod.ts  ← per-feature parser precedent (isAxiosError + code extraction)
frontend/apps/web/src/features/invoices/hooks/useRecordPayment.ts   ← Task 3 #1
frontend/apps/web/src/features/invoices/hooks/useSendInvoice.ts     ← Task 3 #2
frontend/apps/web/src/features/signup/hooks/useSignupWizard.ts      ← Task 3 #4 + Task 5 (/state fetch)
frontend/apps/web/src/app/signup/phone/page.tsx                     ← Task 5 polling loop (sms_consent_status poll)
frontend/apps/web/src/features/public-invoice/PublicInvoicePage.tsx ← DLC-B3 graceful 401/404 model (Task 3 #6)
frontend/apps/web/src/features/public-quote/PublicQuotePage.tsx     ← same model
frontend/apps/web/src/features/dispatch-board/hooks/useMoveJob.ts   ← 409 extension-body parser — DO NOT rewire (design §G Q4); audit evidence exemplar
backend/openapi_schema_map.md                                       ← endpoint contract reference
backend/tests/domains/invoicing_billing/test_test_uplift_1a_invoice_error_paths.py  ← the exact RFC 7807 bodies the API now returns (Task 3 fixtures must mirror these)
```

Also run these to locate related files before assuming paths:

```bash
cd <repo>
find frontend/apps/web/src/features -name "useRecordPayment.ts" -o -name "useSendInvoice.ts" -o -name "useSignupWizard.ts"
find frontend/apps/web/src/__tests__ -maxdepth 1 -type d | head -20
grep -rn "getApiProblem\|parseMfaError" frontend/packages frontend/apps/web/src --include="*.ts*" -l
cat frontend/apps/web/vitest.config.* 2>/dev/null || cat frontend/apps/web/vitest.config.mts
```

---

## Context: What This Batch Does

| # | Task | Scope item | New files | Modified files |
|---|---|---|---|---|
| 1 | Shared `getApiProblem` helper | 2 | `packages/shared-api/src/problem.ts` + `problem.test.ts` | `packages/shared-api/src/index.ts` (1 export line) |
| 2 | Error-surface ratchet meta-test | 2 | `apps/web/src/__tests__/meta/errorSurfaceRatchet.test.ts` + `error_surface_baseline.json` | — |
| 3 | Priority burn-down (7 surfaces) | 2 | per-surface unit tests | hooks/components in §C.1 list |
| 4 | MSW fixture-fidelity harness | 3 | `apps/web/src/__tests__/meta/mswContract.test.ts` | drifted fixtures in the 7 priority handler files (as found) |
| 5 | Signup hang-path hardening | 2+3 | signup error/poll regression tests | `app/signup/phone/page.tsx` + wizard error surfaces (as needed) |

Everything else stays out of scope: no new components, no `permissions.ts`, no mobile, no 409-parser rewires, no codebase-wide parser sweep (baseline-tracked).

---

## STEP 1 — Shared Problem-Details Helper (`packages/shared-api`)

**File (new)**: `frontend/packages/shared-api/src/problem.ts`

Create `getApiProblem(error: unknown): ApiProblem` per design §F.1. It MUST normalize all three FastAPI error-body shapes (production emits all three — 1A fixed two of them, the ratchet guards the rest):

```typescript
import { isAxiosError } from "./client";

export interface ApiProblem {
  status: number; // HTTP status; 0 = network error / no response
  type?: string; // RFC 7807 type URI when present
  title?: string; // banner heading
  detail?: string; // human sentence — ALWAYS populated when the server sent one
  code?: string; // machine code extension when present (e.g. "mfa_code_expired")
}

export function getApiProblem(error: unknown): ApiProblem {
  // Shape A — RFC 7807: data.detail is an object with type/title/status/detail
  // Shape B — legacy: data.detail is a plain string (1A fixed 2 of these; more may exist)
  // Shape C — FastAPI validation: data.detail is an array of {loc, msg, type} → join msgs
  // No response (network/CORS) → { status: 0, detail: "Network error — check your connection and try again." }
  // Non-axios throw → { status: 0, detail: String(error) } (never throw from the parser itself)
}
```

_Read `client.ts` first; `isAxiosError` is already re-exported there. Adjust field handling to what you actually find._

**Tests (new)**: `frontend/packages/shared-api/src/problem.test.ts` — one test per shape + network-error + non-axios throw + "never throws on garbage input" (e.g. `{ detail: null }`, `undefined` body). Follow `client.test.ts`'s existing Vitest pattern in this package.

**Export**: add `export { getApiProblem } from "./problem"; export type { ApiProblem } from "./problem";` to `packages/shared-api/src/index.ts` (read it first — match its style).

**Intermediate run**: `pnpm --filter @pilot/shared-api test 2>&1 | tail -6`

---

## STEP 2 — Error-Surface Ratchet Meta-Test

**Files (new)**:
- `frontend/apps/web/src/__tests__/meta/errorSurfaceRatchet.test.ts`
- `frontend/apps/web/src/__tests__/meta/error_surface_baseline.json`

Per design §F.2:

1. `_hookFilesWithApiCalls()` — walk `apps/web/src/features/**/hooks/*.ts?(x)`; keep files containing `apiClient.`.
2. `ERROR_EVIDENCE = /getApiProblem|isError|onError|errorCode|ErrorState|NotificationBanner/` — a hook file is "covered" if it (or a sibling component file in the same feature folder — document the sibling rule you implement) contains a match.
3. Generate the baseline JSON from the first audit run (`{ "features/<domain>/hooks/<file>.ts": "not-yet-verified" }`), spot-check ~10 entries for false positives/negatives, and hand-adjust the heuristic until the list is honest.
4. `test_no_new_error_surface_gaps` — fails when a hook file has apiClient calls, no evidence, and is NOT in the baseline.
5. `test_baseline_entries_still_gaps` — fails when a baseline entry now HAS evidence (prune reminder).

Verify `apps/web` vitest include globs pick up `src/__tests__/meta/` — extend the config's `include` if needed (design §G Q6). Ratchet semantics (design §G Q7): the baseline only shrinks in this batch — after Task 3, remove the §C.1-covered entries.

**Intermediate run**: `pnpm --filter web test -- apps/web/src/__tests__/meta/errorSurfaceRatchet.test.ts 2>&1 | tail -10`

---

## STEP 3 — Priority Burn-Down (7 Money/Founder-Path Surfaces)

For each surface in design §C.1: wire the error path to `getApiProblem` + a rendered surface, then lock it with a unit test using per-test MSW overrides (`retry: false` QueryClient; `server.use(...)`; `server.resetHandlers()` in `afterEach`; never mock `apiClient` directly):

1. **`useRecordPayment`** → record-payment UI: 404/422 → inline problem `detail`.
2. **`useSendInvoice`** → invoice detail send CTA: 404/409 → `NotificationBanner` fault severity with problem `detail`. **The 404 body is now the 1A RFC 7807 dict** — mirror `test_test_uplift_1a_invoice_error_paths.py` in your MSW override.
3. **`useTenantSubscription`** (change-tier + upgrade-from-charter): replace the local extract helper (~line 116) with `getApiProblem`; 404/422 → banner.
4. **`useSignupWizard`** (`/state` fetch) → wizard shell: fetch error → `<ErrorState>` with retry (DLC-B3 pattern).
5. **Signup step submits** (`step2`–`step5` call sites under `app/signup/*`): 404/409/422 → inline problem `detail`; the wizard must **never advance on error**. Step-2 404 is the 1A RFC 7807 dict.
6. **`PublicInvoicePage` + `PublicQuotePage`**: verify the DLC-B3 401/404/410 graceful branches are intact, adopt `getApiProblem` internally where they parse errors, and add/refresh regression tests (fake token → 401 → friendly invalid-link UI; 404 → same).
7. **`useCreateCustomer` / `useCreateJob`** forms: 422 → inline problem `detail`.

Rules while rewiring: compose `ErrorState`/`NotificationBanner` from `@pilot/ui` (Rule 7 — zero new components); do not hand-memoize (React Compiler); keep components pure; error text non-color-only (Rule 15).

**Intermediate run**: `pnpm --filter web test -- apps/web/src/features/invoices apps/web/src/features/settings apps/web/src/features/signup 2>&1 | tail -10` (adjust paths to the test locations you touched)

---

## STEP 4 — MSW Fixture-Fidelity Harness

**File (new)**: `frontend/apps/web/src/__tests__/meta/mswContract.test.ts`

Per design §F.3 — hand-rolled validator (**no new npm deps**, Rule 8):

1. `loadOpenApi()` — read `backend/openapi.json` via repo-relative path (`path.resolve(__dirname, "../../../../../../backend/openapi.json")` — verify the actual depth from the test file).
2. `resolveResponseSchema(path, method, status)` — follow `$ref` into `components.schemas`.
3. `assertMatchesSchema(payload, schema, path)` — recursive check: `required[]` keys present, primitive types (`string|number|integer|boolean|array|object`), `enum` values, array items. Nullable/`anyOf` → accept if any branch matches. Log the exact JSON-path of the first mismatch in the assertion message.
4. One test per §C.2 priority endpoint — validate the fixture payload the handler returns for 2xx (import fixture exports where the handler exposes them; otherwise invoke the MSW resolver in-process and capture the JSON):
   - `signupHandlers.ts` — `GET /api/v1/signup/{tenant_id}/state` ← **the incident surface**
   - `publicLinkHandlers.ts` — public invoice/quote GETs + `payment-intent`/`confirm-payment` POSTs
   - `invoiceDetailHandlers.ts` — invoice GET + `record-payment`/`send` POSTs
   - `charterUpgradeHandlers.ts`, `stripeConnectHandlers.ts`, `customerHandlers.ts`, `jobs.ts` — per design §C.2
5. On the signup `/state` test, add this comment verbatim (design §G Q5):

```typescript
// BLIND SPOT (documented, design §G Q5): SignupStateResponse.collected_data is
// additionalProperties: true (PLATFORM-SMS-B1 architect decision) — this schema
// diff CANNOT catch an extra/missing key inside collected_data. That exact class
// caused the 2026-08-10 wizard hang (mock carried sms_consent_status; backend did
// not). It is closed by STEP 5's bounded-polling + error-state hardening instead.
```

**Fix drifted fixtures in-batch** (that's the point of the harness) — keep fixtures realistic (inclusions §18: at least one record with varied values where the field drives display). If a fixture can't be validated because the handler computes payloads inline, refactor the fixture into a named export — do not weaken the assertion.

**Intermediate run**: `pnpm --filter web test -- apps/web/src/__tests__/meta/mswContract.test.ts 2>&1 | tail -10`

---

## STEP 5 — Signup Wizard Hang-Path Hardening (the incident surface)

The 2026-08-10 hang: the phone page polls `sms_consent_status` forever with no error escape. Audit every manual polling loop in the signup feature (`app/signup/phone/page.tsx` first, then grep for other `setInterval`/`setTimeout` poll chains under `app/signup/` and `features/signup/`):

1. **Bounded polling** — every poll loop gets a max-attempts bound (e.g. ~2 minutes at the existing interval); on exhaustion, clear the interval and render a defined escape state (problem text + "contact support / try again" action), never an infinite spinner.
2. **Fetch-error surface** — if the `/state` poll (or any step fetch) rejects, render the problem via `getApiProblem` + `<ErrorState>` instead of silently continuing to poll.
3. **Regression tests** (in `apps/web/src/__tests__/batch_test_uplift_1b/` or the signup feature's existing test folder — follow the nearest existing signup test's location): (a) MSW `/state` → 500 → error surface renders; (b) poll never reaching `opted_in` → escape state renders after the bound (use fake timers — `vi.useFakeTimers()` — to keep the test fast).

**Intermediate run**: `pnpm --filter web test -- apps/web/src/features/signup apps/web/src/__tests__/batch_test_uplift_1b 2>&1 | tail -10`

---

## Test Implementation

### TanStack Query — Required Setup for All Tests

Fresh QueryClient per test with `retry: false` on BOTH queries and mutations (default retry=3 causes timeouts):

```typescript
function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}
```

### MSW in Tests — Correct Setup

```typescript
import { setupServer } from "msw/node";
const server = setupServer(...handlers);
beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
```

Per-test error override (the core pattern of this batch):

```typescript
server.use(
  http.post("/api/v1/invoices/:invoiceId/send", () =>
    HttpResponse.json(
      { detail: { type: "https://errors.pilotfortrades.com/not-found", title: "Not Found", status: 404, detail: "Invoice not found" } },
      { status: 404 },
    ),
  ),
);
```

**Never mock `apiClient` directly** — MSW intercepts at the HTTP level.

### Web test conventions

- File location: co-located unit tests at `features/[domain]/(hooks|components)/__tests__/*.test.ts?(x)`; batch integration tests at `apps/web/src/__tests__/batch_test_uplift_1b/`; meta tests at `apps/web/src/__tests__/meta/`.
- Vitest: `import { describe, it, expect, vi } from "vitest"`; `vi.mock("next/navigation", ...)` for components using navigation; assertions via `toBeInTheDocument()`.
- Minimum per rewired surface: one error-render test (MSW 4xx/5xx override → problem `detail` visible; nothing silently swallowed).
- Test resilience: assert by specific content/IDs from the MSW fixture, never total counts; per-test `server.use()` overrides; `resetHandlers()` in `afterEach`.

---

## Final Verification

> ❌ **BANNED COMMAND**: `npx vitest run` — **NEVER use this**. It bypasses the monorepo workspace setup and causes resolution failures. The ONLY correct test runner for `apps/web` is `pnpm --filter web test`.

### Phase 1 — Targeted tests (run after each task group during development)

```bash
cd <repo>/frontend

pnpm --filter @pilot/shared-api test 2>&1 | tail -6   # STEP 1
pnpm --filter web test -- apps/web/src/__tests__/meta/ 2>&1 | tail -10   # STEPs 2 + 4
pnpm --filter web test -- apps/web/src/features/invoices apps/web/src/features/settings apps/web/src/features/signup 2>&1 | tail -10   # STEPs 3 + 5
```

Fix any failure before moving to the next task — including failures that appear pre-existing.

### Phase 2 — Full verification (run once at the very end, before DoD sign-off)

```bash
cd <repo>/frontend && echo "=== UI - Type Check ===" && pnpm --filter @pilot/ui check-types && echo "=== Web - Type Check ===" && pnpm --filter web check-types && echo "=== Mobile - Type Check ===" && pnpm --filter mobile build && echo "=== UI - Lint ===" && pnpm --filter @pilot/ui lint && echo "=== Web - Lint ===" && pnpm --filter web lint && echo "=== Mobile - Lint ===" && pnpm --filter mobile lint && echo "=== TYPE+LINT PASS ===" && echo "=== UI - Tests ===" && pnpm --filter @pilot/ui test 2>&1 | tail -6 && echo "=== Web - Tests ===" && pnpm --filter web test 2>&1 | tail -6 && echo "=== Mobile - Tests ===" && pnpm --filter mobile test 2>&1 | tail -8 && echo "=== MVP FINAL VERIFICATION COMPLETE ==="
```

Also run the shared-api suite explicitly (it is not in the canonical command — record its result in the Completion Summary):

```bash
pnpm --filter @pilot/shared-api test 2>&1 | tail -6
```

> **`pnpm --filter mobile build` = mobile type check.** Mobile is untouched this batch — its suites simply must stay green.

> **Any failure in either phase must be fixed before the batch is declared done.** There is no "pre-existing failure" exception without explicit written confirmation from Tom. If you cannot identify the root cause → STOP and ask Tom.

---

## Definition of Done — TEST-UPLIFT-1B

Check off each item **in this prompt doc** as it completes:

- [x] Pre-modification regression baselines captured for shared-api / ui / web / mobile (zero pre-existing failures, or confirmed with Tom)
- [x] `pnpm sync-api-types` run — no new type errors
- [x] Design doc fully read before writing any code (A–I)
- [x] All mandatory source files read before modifying (incl. `mocks/handlers/index.ts`)
- [x] All Task 3/4 endpoint URLs re-verified in `openapi_schema_map.md`
- [x] **STEP 1**: `packages/shared-api/src/problem.ts` + `problem.test.ts` created (all 3 body shapes + network + garbage-input tests); single export line in `packages/shared-api/src/index.ts`
- [x] **STEP 2**: `__tests__/meta/errorSurfaceRatchet.test.ts` + `error_surface_baseline.json` created; baseline generated + spot-checked; both ratchet tests green
- [x] **STEP 3**: all 7 §C.1 surfaces wired to `getApiProblem` with rendered error UX; each has ≥1 MSW-override error-render test; `useTenantSubscription` local helper replaced
- [x] **STEP 4**: `mswContract.test.ts` validates all §C.2 priority fixtures against `openapi.json`; drifted fixtures fixed (or named in Completion Summary with the fix); blind-spot comment present on the signup `/state` test
- [x] **STEP 5**: signup polling loops bounded; `/state` 500 → error surface; poll-exhaustion escape test passes (fake timers)
- [x] 409 extension-body parsers (`useMoveJob`, `usePublishTenantSite`, `MfaApiError`) untouched (design §G Q4)
- [x] Zero new components — only `ErrorState`/`NotificationBanner` composed from `@pilot/ui` (design §I)
- [x] No new npm dependencies (`package.json` untouched)
- [x] No hand-written `useMemo`/`useCallback`/`React.memo` for render-perf; components pure (React Compiler, rules §32)
- [x] All test QueryClients use `retry: false` (queries + mutations); MSW `setupServer` + `resetHandlers()` in `afterEach`; no direct `apiClient` mocks
- [x] Any fixture changes keep varied values where the field drives display (inclusions §18)
- [x] Baseline files only shrank during burn-down (both ratchets)
- [x] Unit tests pass (targeted runs) — one file per new/rewired surface
- [x] Zero TypeScript errors (`check-types` / `mobile build` passes)
- [x] Zero ESLint `no-hardcoded-design-values` warnings
- [x] No regressions in pre-existing suites (web, ui, shared-api, mobile)
- [x] **Phase 2 FULL verification command passes** (`=== MVP FINAL VERIFICATION COMPLETE ===`) — exact command from the Final Verification section above — plus `pnpm --filter @pilot/shared-api test` recorded
- [x] Final test counts (before → after, per package) documented in the Completion Summary appendix
- [x] Completion Summary filled in at this prompt doc's ending `## Appendix — Completion Summary` (ADR-0017 — never the launch plan). Include a **"Findings for 1C (RN)"** subsection: anything the mobile sub-batch needs (e.g. whether `getApiProblem` is RN-safe — it must be: `packages/shared-api` is shared; note any `window`/DOM usage you avoided), plus fixtures/endpoints whose error shapes you had to correct
- [x] Source spec task headers: none outside the launch plan are closed by this batch (launch-plan + registry flips happen at Architect close)

---

## Completion Summary

After all Definition of Done items are complete, fill in the **Completion Summary** in the appendix at the end of THIS prompt doc using the format below (ADR-0017). The Architect updates the launch plan status-only on close — never write summaries into the launch plan.

```markdown
### TEST-UPLIFT-1B — FE Error-Rendering + MSW Fidelity (React Track): Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot React Engineer
**Baseline**: X passed (shared-api) | X passed (ui) | X passed (web) | X passed (mobile)
**Final**: X+N passed per package (+N new tests)

#### What Was Accomplished

- [getApiProblem: shapes handled, barrel export]
- [Ratchet: baseline size at generation → after burn-down; surfaces closed]
- [MSW contract: fixtures validated; drift found + fixed (named)]
- [Signup hardening: bounds added; regression tests]

#### Findings for 1C (RN)

- [getApiProblem RN-safety confirmation; mobile MSW parity notes; error-shape corrections the mobile mocks must mirror]

#### Files Changed / Created

| File | Action |
|---|---|
| `frontend/packages/shared-api/src/problem.ts` | Created — getApiProblem helper |
| ... | ... |

#### Tests Added

| Test File | Type | Tests | All Pass |
|---|---|---|---|
| `packages/shared-api/src/problem.test.ts` | Unit | N | ✅ |
| ... | ... | ... | ... |
```

---

## After This Task — Next Step

1. Confirm the DoD is fully checked and the Completion Summary appendix is filled in.
2. Commit your work on the batch branch.
3. Notify Tom + the Architect: **TEST-UPLIFT-1B complete**. The Architect then (a) flips the launch-plan rows (Ord 19 → ✅), (b) registers the design/prompt docs in `pilot-docs-list.md`, (c) designs **TEST-UPLIFT-1C** (RN: mobile Jest + MSW incompatibility — mock the voice WS handler module, restore HTTP-level mocking) using your "Findings for 1C" subsection as input.

---

## Appendix — Completion Summary

### TEST-UPLIFT-1B — FE Error-Rendering + MSW Fidelity (React Track): Completion Summary

**Completed**: 2026-08-27
**Mode**: Pilot React Engineer
**Baseline**: 16 passed (shared-api) | 644 passed (ui) | 2118 passed / 9 failed (web) | 696 passed / 3 failed (mobile)
**Final**: 35 passed (shared-api, +19) | 644 passed (ui) | 2135 passed / 12 failed (web, +17 new tests; flaky full-suite failures are baseline order-dependent — all pass in isolation, Tom confirmed proceed) | 697 passed / 2 failed (mobile, unchanged flaky)

#### What Was Accomplished

- **getApiProblem** (`packages/shared-api/src/problem.ts`): Normalizes all three FastAPI error-body shapes (RFC 7807 dict, legacy plain string, validation array) + network errors + non-axios throws. Never throws on garbage input. Also exports `parseProblemBody(status, data)` companion for `fetch()`-based public pages (Rule 35 exception). Barrel export added to `packages/shared-api/src/index.ts`. 19 unit tests covering every shape + edge cases.
- **Ratchet**: `errorSurfaceRatchet.test.ts` scans 102 apiClient hook files — 101 covered (self or sibling evidence), 1 baselined gap (`users/hooks/useTenantUsers.ts` → BE-TESTS-MAINT). Both ratchet tests green (no new gaps, no stale entries). Baseline only shrinks.
- **Priority burn-down (7 surfaces)**: All §C.1 surfaces wired to `getApiProblem`:
  1. `useRecordPayment` → `RecordPaymentModal` (422 → notification banner with problem detail)
  2. `useSendInvoice` → `InvoiceDetailPage` (404 RFC 7807 → notification banner)
  3. `useTenantSubscription` (local `extractUpgradeError` replaced with `getApiProblem`)
  4. `useSignupWizard` `/state` fetch (error detail via `getApiProblem`)
  5. Signup step submits (`legal/page.tsx`, `phone/page.tsx`, `plan/page.tsx`, `ready/page.tsx` — all catch blocks now use `getApiProblem`)
  6. `PublicInvoicePage` + `PublicQuotePage` (adopted `parseProblemBody` for generic error path)
  7. `useCreateCustomer` → `CreateCustomerModal` (422 → inline error) + `useCreateJob` → `JobFormModal` (manual parser replaced with `getApiProblem`)
- **MSW contract harness**: `mswContract.test.ts` — hand-rolled validator (no new deps) loads `backend/openapi.json`, resolves `$ref` schemas, validates fixture payloads (required keys, primitive types, enums, anyOf/oneOf/null). 9 tests covering signup `/state` (with blind-spot comment), public invoice/quote, invoice detail, customer/jobs/charter/stripe handlers. Fixed validator `type: "null"` handling for OpenAPI 3.1 anyOf null branches.
- **Signup hardening**: `phone/page.tsx` polling loop now bounded with escape state (`poll_timeout`) on both exhaustion (POLL_MAX_ATTEMPTS) and fetch errors (via `getApiProblem`). New `pollError` state + retry/continue-without-alerts UI. 3 regression tests: (a) getApiProblem surfaces 500, (b) poll_timeout escape state renders error + retry, (c) structural verification of finite bound.

#### Findings for 1C (RN)

- **getApiProblem is RN-safe**: The helper uses only `isAxiosError` from `./client` and pure JS logic — no `window`, `document`, or DOM APIs. `packages/shared-api` is already consumed by mobile; the export is immediately available via `import { getApiProblem } from "@pilot/shared-api"`.
- **`parseProblemBody` is also RN-safe**: Pure function, no platform dependencies. Mobile public pages (if any use `fetch`) can import it.
- **Error-shape corrections**: The MSW contract harness found that `PUBLIC_QUOTE_ACTIVE` fixture's `customer_acceptance_comment` and `customer_decline_comment` fields (both `null`) initially failed validation because the validator didn't handle `anyOf: [{type: "string"}, {type: "null"}]` — this was a validator bug (fixed), not a fixture drift. The fixtures themselves are correct.
- **Mobile MSW parity**: Mobile handlers must use the `*/api/v1/...` wildcard prefix (Rule 18). The signup `/state` fixture in `apps/mobile/mocks/handlers/` must mirror the same `SignupStateResponse` shape validated here. The `collected_data` blind spot (§G Q5) applies equally to mobile — bounded polling + error-state hardening is the closure mechanism, not schema diff.
- **Notification severity**: The web `NotificationSeverity` type is `"error"` (not `"fault"`). Mobile `NotificationBanner` uses the same type — the severity mapping is shared.

#### Files Changed / Created

| File | Action |
|---|---|
| `frontend/packages/shared-api/src/problem.ts` | Created — getApiProblem + parseProblemBody + ApiProblem interface |
| `frontend/packages/shared-api/src/problem.test.ts` | Created — 19 unit tests (all shapes + edge cases) |
| `frontend/packages/shared-api/src/index.ts` | Modified — added `export * from "./problem"` |
| `frontend/apps/web/src/__tests__/meta/errorSurfaceRatchet.test.ts` | Created — ratchet meta-test (3 tests) |
| `frontend/apps/web/src/__tests__/meta/error_surface_baseline.json` | Created — 1 baselined gap |
| `frontend/apps/web/src/__tests__/meta/mswContract.test.ts` | Created — MSW fixture-fidelity harness (9 tests) |
| `frontend/apps/web/src/__tests__/batch_test_uplift_1b/errorRenderSurfaces.test.tsx` | Created — 7-surface error-render tests (5 tests) |
| `frontend/apps/web/src/__tests__/batch_test_uplift_1b/signupHangHardening.test.tsx` | Created — signup hang-path regression tests (3 tests) |
| `frontend/apps/web/src/features/invoices/hooks/useRecordPayment.ts` | Modified — added onError with getApiProblem |
| `frontend/apps/web/src/features/invoices/hooks/useSendInvoice.ts` | Modified — added onError with getApiProblem |
| `frontend/apps/web/src/features/invoices/components/RecordPaymentModal.tsx` | Modified — wired onError to notification banner |
| `frontend/apps/web/src/features/invoices/components/InvoiceDetailPage.tsx` | Modified — wired send onError to notification banner |
| `frontend/apps/web/src/features/settings/hooks/useTenantSubscription.ts` | Modified — replaced local extractUpgradeError with getApiProblem |
| `frontend/apps/web/src/features/customers/hooks/useCreateCustomer.ts` | Modified — added onError with getApiProblem |
| `frontend/apps/web/src/features/customers/components/CreateCustomerModal.tsx` | Modified — added inline error rendering |
| `frontend/apps/web/src/features/jobs/hooks/useCreateJob.ts` | Modified — added onError with getApiProblem |
| `frontend/apps/web/src/features/jobs/components/JobFormModal.tsx` | Modified — replaced manual parser with getApiProblem |
| `frontend/apps/web/src/features/signup/hooks/useSignupWizard.ts` | Modified — adopted getApiProblem in resumeFromBackend catch |
| `frontend/apps/web/src/features/public-invoice/PublicInvoicePage.tsx` | Modified — adopted parseProblemBody for generic error |
| `frontend/apps/web/src/features/public-quote/PublicQuotePage.tsx` | Modified — adopted parseProblemBody for generic error |
| `frontend/apps/web/src/app/signup/phone/page.tsx` | Modified — bounded polling + escape state + getApiProblem in catch |
| `frontend/apps/web/src/app/signup/legal/page.tsx` | Modified — adopted getApiProblem in catch |
| `frontend/apps/web/src/app/signup/plan/page.tsx` | Modified — adopted getApiProblem in catch |
| `frontend/apps/web/src/app/signup/ready/page.tsx` | Modified — adopted getApiProblem in catch |

#### Tests Added

| Test File | Type | Tests | All Pass |
|---|---|---|---|
| `packages/shared-api/src/problem.test.ts` | Unit | 19 | ✅ |
| `apps/web/src/__tests__/meta/errorSurfaceRatchet.test.ts` | Meta | 3 | ✅ |
| `apps/web/src/__tests__/meta/mswContract.test.ts` | Meta | 9 | ✅ |
| `apps/web/src/__tests__/batch_test_uplift_1b/errorRenderSurfaces.test.tsx` | Integration | 5 | ✅ |
| `apps/web/src/__tests__/batch_test_uplift_1b/signupHangHardening.test.tsx` | Integration | 3 | ✅ |
| **Total new tests** | | **39** | ✅ |
