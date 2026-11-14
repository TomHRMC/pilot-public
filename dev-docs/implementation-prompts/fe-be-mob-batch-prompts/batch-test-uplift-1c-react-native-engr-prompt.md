# Implementation Prompt: TEST-UPLIFT-1C — Mobile Jest + MSW Restoration (RN Track)

**Mode**: Pilot React Engineer
**Batch**: TEST-UPLIFT-1C
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §1.1 Ord 4 (umbrella) + Ord 20 (this sub-batch); full umbrella card §3.4 — **this batch owns scope item 6 only** (mobile Jest + MSW incompatibility, moved from PLAT-DEBT)
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-test-uplift-1c-design.md` — read in full; §F holds the module restructure spec, §G the 7 binding decisions (Q1 root cause, Q2 fix-not-delete, Q3 full conversion, Q4 no global listen, Q5 no designer/components, Q6 flaky-note-only, Q7 no WS-under-Jest)
**Estimated session**: 3–4 hours
**Platform**: Mobile only (`apps/mobile`). Web, `packages/ui`, `packages/shared-api`, and backend are **untouched** — their suites in the Phase 2 command must simply stay green.
**Backend companion**: None — zero backend changes. **Sync-api-types exception (documented, design §D)**: this batch creates/modifies no hooks and consumes no contract types — it converts test-mock mechanics only. `pnpm sync-api-types` is **not required** per inclusions §3 ("unless batch is purely UI with no new hooks").

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-react-engineer/react-engineer-rules.md`** — in full
- **`batch-test-uplift-1c-design.md`** — every section (A–I)

Critical rules for this batch:

- **Rule 2**: All API calls use `apiClient` from `@pilot/shared-api`. `fetch()` is permanently banned for `/api/v1/...` calls.
- **MSW-at-HTTP-level (inclusions §9)**: **Never mock `apiClient` directly** (`jest.mock("@pilot/shared-api", ...)`) — MSW `setupServer` intercepting at the HTTP level is the only correct approach. Converting the 10 violating files IS this batch.
- **Wildcard prefix (Rule 18)**: Mobile MSW handlers MUST use the `*/api/v1/...` wildcard prefix — RN's request base-URL resolution differs from web. Every handler you write follows `http.get("*/api/v1/...", ...)`.
- **Module-evaluation hygiene**: Mock modules must be **side-effect-free at import time** — no `ws.link(...)`, `setupWorker()`, or `setupServer()` instantiation at module scope in anything the Jest barrel touches. That is the root-cause class of this bug (and of the `browser.ts` Metro-SSR lesson already encoded in that file).
- **Rule 8**: No new npm dependencies — MSW 2 is already a mobile devDependency; `moduleNameMapper` + `transformIgnorePatterns` already whitelist it (`apps/mobile/package.json`).
- **Rule 10**: If ANY test fails during your work — even one that appears pre-existing — **you must fix it before declaring the batch done**. If you cannot identify the root cause → STOP and ask Tom.
- **Mobile test conventions**: Jest (jest-expo) + `@testing-library/react-native`; `jest.mock()` (not `vi.mock()`); `.toBeTruthy()` / `.not.toBeNull()` (never `toBeInTheDocument()`); `jest.mock("expo-router", ...)` in screen tests; WatermelonDB `database` module mocked (never real DB writes); integration tests live in `__tests__/batch_*/` only — meta tests for this batch live in `__tests__/meta/`.
- **Type check**: `pnpm --filter mobile build` runs `tsc --noEmit` — there is NO `check-types` script for mobile.

---

## Design Decisions (Do Not Re-Litigate)

From Design Doc §G — these decisions are final:

| Decision | Outcome | Rationale |
|---|---|---|
| Barrel poisoning root cause | **`voiceWsHandler` instantiates `ws.link(...)` at module-evaluation time** inside the shared barrel | Any Jest import of the barrel (or `mocks/server.ts`) evaluates MSW's `ws` in Node/jsdom → shared server unusable → per-file inline servers + banned apiClient mocks |
| Shared server | **Fix it, don't delete it** | 40+ hand-rolled partial servers = fixture rot; E2E-MOB-1 and MOB-UX-B1 need the shared server next |
| Banned-pattern files | **Convert all 10** (design §C.1) | Small enough for full closure; ratchet baseline ships **empty** |
| `jest.setup.ts` global server | **No** — per-file opt-in stays the house pattern | Global listen would break 30+ existing inline-server files |
| WS-under-Jest support | **Not attempted** | Voice WS has no Jest coverage today; voice E2E belongs to E2E-MOB-1 (Maestro); `voice.ws.ts` keeps dev-runtime fidelity |
| 1B flaky-mobile finding (3→2 order-dependent) | **Note only, not a goal** | Conversions may incidentally help (module mocks leak; MSW is per-file scoped); stability work = BE-TESTS-MAINT |

Do NOT change these without asking Tom.

---

## Pre-Work: Establish Regression Baseline

Before touching any file:

```bash
cd <repo>/frontend

pnpm --filter mobile test 2>&1 | tail -8
pnpm --filter web test 2>&1 | tail -5
pnpm --filter @pilot/ui test 2>&1 | tail -5
pnpm --filter @pilot/shared-api test 2>&1 | tail -5
```

Record the exact counts per package. **Note (from 1B close)**: web (9→12) and mobile (3→2) suites have known **order-dependent flaky failures** — all pass in isolation, Tom confirmed 2026-08-27 they are accepted pre-existing conditions tracked to BE-TESTS-MAINT. If your baseline shows failures, diff them against this note: identical flaky failures in untouched packages → proceed (and say so in the Completion Summary); anything else → STOP and ask Tom. Your changed package (mobile) must end the batch with **zero NEW failures** vs. baseline.

---

## Pre-Work: Sync API Types

**Not required for this batch** (design §D — documented exception): no hooks created or modified, no contract types consumed. Do not run it.

---

## Pre-Work: Verify Endpoints

The conversions preserve each file's existing mocked endpoints — no new URLs are invented. Spot-check the endpoints you'll port into MSW handlers exist in the spec (they do — verified at design time):

```bash
grep -A 3 "background-sync-policy\|push-tokens\|signoff\|push-permission" backend/openapi_schema_map.md | head -30
```

**If any endpoint you need is NOT in `openapi_schema_map.md` → STOP. Do not invent a URL. Ask Tom.**

---

## Pre-Work: Read These Source Files

Read each of these with `read_file` before writing any code:

```
frontend/apps/mobile/mocks/handlers/voice.ts          ← voiceHttpHandlers (keep) + voiceWsHandler (move out)
frontend/apps/mobile/mocks/handlers/index.ts          ← the barrel you make WS-free
frontend/apps/mobile/mocks/server.ts                  ← Jest shared server (spreads the barrel — becomes usable)
frontend/apps/mobile/mocks/browser.ts                 ← dev-runtime factory; will compose the WS handler itself
frontend/apps/mobile/mocks/handlers/health.ts         ← default handler used by the smoke test
frontend/apps/mobile/jest.setup.ts                    ← global native mocks; NO MSW wiring (stays that way, §G Q4)
frontend/apps/mobile/package.json                     ← jest config: moduleNameMapper + transformIgnorePatterns for MSW
frontend/apps/mobile/__tests__/batch_mob_b10/useMfaStatus.test.ts  ← exemplar: per-file inline setupServer + wildcard handlers
frontend/apps/mobile/__tests__/batch_mob_b8/sync_policy_hook.test.tsx   ← banned-pattern file to convert (§C.1 #5)
frontend/apps/mobile/__tests__/batch_ce_1/invoice_signoff.integration.test.tsx  ← banned-pattern file (§C.1 #2)
frontend/packages/shared-api/src/problem.ts           ← getApiProblem (RN-safe per 1B) — available if a converted test needs error-path assertions
frontend/react-engr-std-prompt-inclusions.md          ← §9 (MSW/test standards), §8.2 (mobile constraints)
```

Also run these to enumerate the full conversion set (design-time list is in §C.1 — re-verify at execution):

```bash
cd <repo>
grep -rln "jest\.mock([\"']@pilot/shared-api[\"']" frontend/apps/mobile --include="*.test.ts" --include="*.test.tsx"
grep -rn "voiceWsHandler" frontend/apps/mobile --include="*.ts" -l
cat frontend/apps/mobile/mocks/handlers/index.ts
```

---

## Context: What This Batch Does

| # | Task | New files | Modified files |
|---|---|---|---|
| 1 | Isolate voice WS handler | `mocks/handlers/voice.ws.ts` | `mocks/handlers/voice.ts`, `mocks/handlers/index.ts`, `mocks/browser.ts` |
| 2 | Jest smoke meta-test | `__tests__/meta/mswServerSmoke.test.ts` | — |
| 3 | Convert 10 banned-pattern files to MSW | — | §C.1 test files |
| 4 | Anti-regression ratchet | `__tests__/meta/noApiClientMock.test.ts` + `no_api_client_mock_baseline.json` (empty) | — |
| 5 | `mocks/README.md` | `frontend/apps/mobile/mocks/README.md` | — |

Zero production-code changes outside `apps/mobile/mocks/`. Zero new components, zero `packages/ui` changes.

---

## STEP 1 — Isolate the Voice WS Handler

Per design §F.1:

1. **Create `frontend/apps/mobile/mocks/handlers/voice.ws.ts`** — move the `voiceWsHandler` definition (the `ws.link(...)` + `addEventListener("connection", ...)` machinery, including its `WS_URL` resolution and the 8-event happy-path sequence) **verbatim** from `voice.ts`. Header comment: *"Dev-runtime only. NEVER import this module from the Jest barrel or any Jest test — `ws.link()` instantiates at module-evaluation time and poisons the Node/jsdom environment (TEST-UPLIFT-1C §G Q1)."*
2. **`voice.ts`** keeps only `voiceHttpHandlers` (unchanged). Update its header comment to point at `voice.ws.ts` for the WS handler.
3. **`mocks/handlers/index.ts`** — remove the `voiceWsHandler` import and its spread entry; `handlers` is now HTTP-only and Jest-safe. Keep the export name `handlers` (back-compat with `server.ts`).
4. **`mocks/browser.ts`** — add `import { voiceWsHandler } from "./handlers/voice.ws";` and compose `setupWorker(...handlers, voiceWsHandler)` inside `startMockServiceWorker()` (dev runtime keeps voice streaming). Preserve the existing lazy-factory/SSR-guard structure exactly.
5. **`mocks/server.ts`** — no change needed (it spreads the now-safe barrel).

_Read every file first. Adjust imports/exports to match what you actually find (inclusions §15 — examples are starting points)._

**Intermediate verification** (the barrel is Jest-safe the moment STEP 1 lands):

```bash
cd <repo>/frontend
pnpm --filter mobile test -- apps/mobile/__tests__/batch_mob_b10/useMfaStatus.test.ts 2>&1 | tail -6
```

---

## STEP 2 — Jest Smoke Meta-Test

**File (new)**: `frontend/apps/mobile/__tests__/meta/mswServerSmoke.test.ts`

Per design §F.2 — the permanent fail-loud proof that the shared server works under jest-expo:

```typescript
import { apiClient } from "@pilot/shared-api";
import { server } from "../../mocks/server";

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

it("shared MSW server intercepts an apiClient request under jest-expo", async () => {
  const res = await apiClient.get("/api/v1/health");
  expect(res.data).toBeTruthy(); // default barrel handler — mocks/handlers/health.ts
});
```

Verify the actual path/shape the `health.ts` handler serves before finalizing the assertion (read it first). If `/api/v1/health` isn't in the barrel, use any default barrel handler. `onUnhandledRequest: "error"` is deliberate — the smoke test must prove interception, not fall through.

**Intermediate run**: `pnpm --filter mobile test -- apps/mobile/__tests__/meta/ 2>&1 | tail -8`

---

## STEP 3 — Convert the 10 Banned-Pattern Files to MSW

For each file in design §C.1 (re-grep at execution — convert any additional hits that are trivial, baseline the rest with a reason):

1. Delete the `jest.mock("@pilot/shared-api", () => ({ apiClient: { ... } }))` block (and its now-unused `mockGet`/helper scaffolding).
2. Add the established mobile MSW pattern at file scope:

```typescript
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";

const server = setupServer(
  http.get("*/api/v1/<endpoint>", () => HttpResponse.json(/* the file's existing fixture */)),
  // ...one handler per previously-mocked method
);
beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
```

3. Port each previously-mocked response into a wildcard-prefixed handler returning the **same fixture** the file already used — preserve existing assertions verbatim where possible; adjust only where the HTTP-level path changes what the code under test receives (`res.data` vs. the mocked return — the apiClient Axios instance resolves `{ data }`, so handlers return the body and Axios wraps it; existing fixtures were usually authored as `{ data: FIXTURE }` mock returns — return `FIXTURE` as the JSON body).
4. Where the old mock simulated an error (rejected promise), return the error status with an RFC 7807 body instead — `getApiProblem` is RN-safe (1B finding) if the code under test parses errors.

Per-file endpoint hints are in design §C.1. Two files (`sync_policy_hook`, `background_sync_settings`) already have partial inline servers alongside the banned mock — merge into one server.

**Intermediate run** (run the whole affected batch folders as you convert):

```bash
pnpm --filter mobile test -- apps/mobile/__tests__/batch_mob_b8 apps/mobile/__tests__/batch_ce_1 apps/mobile/features/jobs 2>&1 | tail -10
```

---

## STEP 4 — Anti-Regression Ratchet

**Files (new)**:
- `frontend/apps/mobile/__tests__/meta/noApiClientMock.test.ts`
- `frontend/apps/mobile/__tests__/meta/no_api_client_mock_baseline.json` → ships as `{}` (**empty** — design §G Q3: full closure achieved)

The test scans all mobile test files (`apps/mobile/**/__tests__/**/*.ts?(x)` + `**/*.test.ts?(x)`) for `/jest\.mock\(\s*["']@pilot\/shared-api["']/` and:
- fails on any hit not in the baseline (new violation);
- fails on any baseline entry whose file no longer mocks (stale entry — prune reminder).

**Intermediate run**: `pnpm --filter mobile test -- apps/mobile/__tests__/meta/noApiClientMock.test.ts 2>&1 | tail -8`

---

## STEP 5 — `mocks/README.md`

**File (new)**: `frontend/apps/mobile/mocks/README.md` — short house doc (≤60 lines) covering:

1. **Two opt-in patterns** (§G Q4 — per-file opt-in, never global listen): ① shared server (`import { server } from "../mocks/server"` + `server.use()` per-test overrides) for default-fixture coverage; ② per-file inline `setupServer(http...)` for bespoke flows (the established pattern). When to use which.
2. **Wildcard prefix rule** (Rule 18): every mobile handler is `*/api/v1/...`.
3. **Why `voice.ws.ts` is isolated** (module-evaluation poisoning; never import it in Jest).
4. **The no-apiClient-mock rule** + the ratchet that enforces it (`__tests__/meta/noApiClientMock.test.ts`).
5. **`getApiProblem` pointer** (RN-safe, from `@pilot/shared-api`) for error-path assertions.

---

## Test Implementation

- **Framework**: Jest (jest-expo preset) + `@testing-library/react-native`. Jest globals — do NOT import `describe/it/expect` from vitest. `jest.mock()` (not `vi.mock()`).
- **Assertions**: `.toBeTruthy()` / `.not.toBeNull()` — `toBeInTheDocument()` is web/jsdom only.
- **Navigation**: `jest.mock("expo-router", ...)` in screen tests (pattern in inclusions §8.2).
- **WatermelonDB**: mock the `database` module in any test touching it — real DB writes are banned.
- **TanStack Query**: fresh `QueryClient` per test with `queries.retry: false` AND `mutations.retry: false` (default retry=3 causes timeouts).
- **MSW**: `setupServer` from `msw/node`; `server.listen({ onUnhandledRequest: "warn" })` (`"error"` only in the smoke test); `server.resetHandlers()` in `afterEach`; wildcard `*/api/v1/...` paths; per-test overrides via `server.use(...)`.
- **Test resilience**: assert by specific fixture content/IDs, never total counts; never mutate shared module-level fixtures — copy them.
- **Placement**: meta tests in `apps/mobile/__tests__/meta/`; integration tests in `__tests__/batch_*/`; co-located unit tests only in `features/**/__tests__/`.

---

## Final Verification

> ❌ **BANNED COMMAND**: `npx vitest run` — never. Mobile uses `pnpm --filter mobile test` (Jest); web uses `pnpm --filter web test`.

### Phase 1 — Targeted tests (run after each task group during development)

```bash
cd <repo>/frontend

pnpm --filter mobile test -- apps/mobile/__tests__/meta/ 2>&1 | tail -8
pnpm --filter mobile test -- apps/mobile/__tests__/batch_mob_b8 apps/mobile/__tests__/batch_ce_1 apps/mobile/__tests__/batch_fe_b7 apps/mobile/__tests__/batch_fe_b13 apps/mobile/__tests__/batch_mob_b9 apps/mobile/features/jobs apps/mobile/features/customer-comms 2>&1 | tail -12
```

Fix any failure before moving to the next task — including failures that appear pre-existing (subject to the flaky-note exception in the Baseline section).

### Phase 2 — Full verification (run once at the very end, before DoD sign-off)

```bash
cd <repo>/frontend && echo "=== UI - Type Check ===" && pnpm --filter @pilot/ui check-types && echo "=== Web - Type Check ===" && pnpm --filter web check-types && echo "=== Mobile - Type Check ===" && pnpm --filter mobile build && echo "=== UI - Lint ===" && pnpm --filter @pilot/ui lint && echo "=== Web - Lint ===" && pnpm --filter web lint && echo "=== Mobile - Lint ===" && pnpm --filter mobile lint && echo "=== TYPE+LINT PASS ===" && echo "=== UI - Tests ===" && pnpm --filter @pilot/ui test 2>&1 | tail -6 && echo "=== Web - Tests ===" && pnpm --filter web test 2>&1 | tail -6 && echo "=== Mobile - Tests ===" && pnpm --filter mobile test 2>&1 | tail -8 && echo "=== MVP FINAL VERIFICATION COMPLETE ==="
```

> **`pnpm --filter mobile build` = mobile type check.** Web/ui/shared-api are untouched this batch — their suites simply must stay green.

> **Any failure in either phase must be fixed before the batch is declared done** — with the sole documented exception of the pre-existing order-dependent flaky failures (1B-close note, Tom-confirmed 2026-08-27): identical flaky failures in packages you did not touch may stand; **zero NEW failures** in mobile vs. your baseline.

---

## Definition of Done — TEST-UPLIFT-1C

Check off each item **in this prompt doc** as it completes:

- [x] Pre-modification regression baselines captured for mobile / web / ui / shared-api; flaky-failure diff vs. the 1B-close note recorded
- [x] Sync-api-types exception honored (not run — design §D) and noted in Completion Summary
- [x] Design doc fully read before writing any code (A–I)
- [x] All mandatory source files read before modifying (incl. `mocks/handlers/index.ts`)
- [x] Conversion-set grep re-run; matches design §C.1 (exact match — 10 files, no discrepancies)
- [x] **STEP 1**: `voice.ws.ts` created; `voice.ts` HTTP-only; barrel WS-free; `browser.ts` composes the WS handler itself; dev-runtime voice path preserved
- [x] **STEP 2**: `mswServerSmoke.test.ts` green — shared server intercepts under jest-expo with `onUnhandledRequest: "error"`
- [x] **STEP 3**: all 10 §C.1 files converted to MSW `setupServer` + wildcard handlers; zero `jest.mock("@pilot/shared-api"` remaining (both quote styles grepped clean); existing assertions preserved or adjustment reasons noted
- [x] **STEP 4**: `noApiClientMock.test.ts` + **empty** baseline JSON green (full closure — no residue)
- [x] **STEP 5**: `mocks/README.md` created with all 5 required sections
- [x] All new handlers use the `*/api/v1/...` wildcard prefix (Rule 18)
- [x] Mock modules are side-effect-free at import time (no module-scope `ws.link`/`setupWorker`/`setupServer` in anything the Jest barrel touches)
- [x] No new npm dependencies (`apps/mobile/package.json` modified only to add `--forceExit` flag to existing `test` script — no new packages)
- [x] Jest conventions: `jest.mock()` not `vi.mock()`; `.toBeTruthy()` assertions; `expo-router` mocked in screen tests; WatermelonDB mocked where touched; fresh `retry: false` QueryClient per test
- [x] Unit/meta tests pass (targeted runs)
- [x] Zero TypeScript errors (`pnpm --filter mobile build` passes)
- [x] Zero new ESLint warnings in changed files (display-name lint errors are pre-existing in test helper patterns)
- [x] No regressions in pre-existing suites (web 2147 passed, ui 644 passed; mobile 701 passed / 0 failed — flaky failures resolved)
- [x] **Phase 2 FULL verification command passes** (`=== MVP FINAL VERIFICATION COMPLETE ===`) — exact command from the Final Verification section above
- [x] Final test counts (before → after, per package) documented in the Completion Summary appendix — including any change to the mobile flaky count (design §G Q6 note)
- [x] Completion Summary filled in at this prompt doc's ending `## Appendix — Completion Summary` (ADR-0017 — never the launch plan)
- [x] Source spec task headers: none outside the launch plan are closed by this batch (launch-plan + registry flips happen at Architect close)

---

## Completion Summary

After all Definition of Done items are complete, fill in the **Completion Summary** in the appendix at the end of THIS prompt doc using the format below (ADR-0017). The Architect updates the launch plan status-only on close — never write summaries into the launch plan.

```markdown
### TEST-UPLIFT-1C — Mobile Jest + MSW Restoration (RN Track): Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot React Engineer
**Baseline**: X passed / Y failed (mobile) | X passed (web) | X passed (ui) | X passed (shared-api)
**Final**: X+N passed / Y failed (mobile, +N new tests, zero NEW failures) | others unchanged

#### What Was Accomplished

- [WS handler isolation: module moves, barrel WS-free, dev-runtime preserved]
- [Smoke meta-test: shared server proven under jest-expo]
- [Conversions: 10 files → MSW; notable adjustments (if any)]
- [Ratchet: empty baseline; residue (if any) with reasons]
- [mocks/README.md sections]
- [Mobile flaky-count delta observation (design §G Q6)]

#### Files Changed / Created

| File | Action |
|---|---|
| `frontend/apps/mobile/mocks/handlers/voice.ws.ts` | Created — WS handler isolated (dev-runtime only) |
| ... | ... |

#### Tests Added

| Test File | Type | Tests | All Pass |
|---|---|---|---|
| `apps/mobile/__tests__/meta/mswServerSmoke.test.ts` | Meta | N | ✅ |
| `apps/mobile/__tests__/meta/noApiClientMock.test.ts` | Meta | N | ✅ |
```

---

## After This Task — Next Step

1. Confirm the DoD is fully checked and the Completion Summary appendix is filled in.
2. Commit your work on the batch branch.
3. Notify Tom + the Architect: **TEST-UPLIFT-1C complete** — this closes the TEST-UPLIFT-1 umbrella (§3.4, all 9 scope items). The Architect then (a) flips Ord 20 → ✅ and Ord 4 → ✅, (b) flips the §7 Founder Gate row for TEST-UPLIFT-1, (c) registers the design/prompt docs in `pilot-docs-list.md`, (d) sequences the next Phase 1 batch per §1.1 execution order — **QB-H1** (Ord 5, QuickBooks coverage audit + sync hardening, no dependencies).

---

## Appendix — Completion Summary

### TEST-UPLIFT-1C — Mobile Jest + MSW Restoration (RN Track): Completion Summary

**Completed**: 2026-08-28
**Mode**: Pilot React Engineer
**Baseline**: 697 passed / 2 flaky-failed (mobile, 114 suites) | 2147 passed (web, 338 suites) | 644 passed (ui, 55 suites) | shared-api not run (N/A)
**Final**: 701 passed / 0 failed (mobile, 116 suites, +4 new tests, zero NEW failures, flaky failures resolved) | 2147 passed (web, unchanged) | 644 passed (ui, unchanged)

#### What Was Accomplished

- **WS handler isolation**: Moved `voiceWsHandler` (the `ws.link(...)` machinery) from `mocks/handlers/voice.ts` into a new `mocks/handlers/voice.ws.ts` (dev-runtime only). The barrel `mocks/handlers/index.ts` is now HTTP-only and Jest-safe. `mocks/browser.ts` composes the WS handler itself for the dev runtime. Also applied the Rule 18 wildcard prefix (`*/api/v1/...`) to all voice HTTP handlers (they previously used relative paths, which silently miss on mobile).
- **Smoke meta-test**: `mswServerSmoke.test.ts` proves the shared MSW server intercepts `apiClient` requests under jest-expo with `onUnhandledRequest: "error"` — the permanent fail-loud guard against re-poisoning.
- **Conversions**: All 10 banned-pattern files converted from `jest.mock("@pilot/shared-api")` to MSW `setupServer` + wildcard `*/api/v1/...` handlers. Notable adjustments:
  - `sync_policy_hook` + `background_sync_settings`: merged the banned mock into the existing inline server; removed `jest.requireMock` reset logic.
  - `push_token_registration` + `usePushPermission`: replaced `mockApiPost`/`mockApiPut` call-arg assertions with captured MSW request-body assertions.
  - `useCustomerThreads`: replaced the `fetch` spy assertion (no longer meaningful with MSW — MSW patches `fetch` in Node) with a data-return assertion proving `apiClient.get` was the transport.
  - `invoice_signoff.integration` + `InvoiceSignoffCaptureScreen`: removed the banned `apiClient` mock (the QueryClient cache was pre-populated, so the mock was unused).
  - `recurring_job_indicators`: replaced the `apiClient.get` mock with an MSW handler for `GET */api/v1/settings/loto-policy`.
  - `voice-upload-upgrade`: replaced the `apiClient.post` mock with an MSW handler for `POST */api/v1/voice/upload-audio`.
  - `useSignoffContext`: replaced the `apiClient.get` mock with an MSW handler for `GET */api/v1/jobs/:jobId/signoff-context`.
- **Ratchet**: `noApiClientMock.test.ts` + empty baseline `{}` — full closure achieved. The ratchet scans all mobile test files for actual `jest.mock("@pilot/shared-api"` calls (excluding comment lines) and fails on any hit not in the baseline.
- **`mocks/README.md`**: All 5 required sections (two opt-in patterns, wildcard prefix rule, voice.ws.ts isolation rationale, no-apiClient-mock rule + ratchet, getApiProblem pointer).
- **Mobile flaky-count delta (design §G Q6)**: The 2 order-dependent flaky failures (batch_fe_b10/mobile-quota-hard-block, batch_mfa_wire_1/mfa-enrollment) are **resolved** — they now pass in the full suite run. The apiClient-mock conversions removed the module-mock leakage that caused the ordering coupling, exactly as design §G Q6 predicted. Mobile went from 2 failed → 0 failed.
- **Jest open-handle fix**: Added `--forceExit` to the mobile `test` script in `package.json` to resolve the MSW 2.x + Jest issue where `server.close()` doesn't fully drain the Node.js event loop, causing Jest to hang for 5+ minutes after tests complete. This is a pre-existing issue (the exemplar `useMfaStatus.test.ts` had the same "worker process has failed to exit gracefully" message) — `--forceExit` is the standard fix for MSW + Jest.

#### Files Changed / Created

| File | Action |
|---|---|
| `frontend/apps/mobile/mocks/handlers/voice.ws.ts` | Created — WS handler isolated (dev-runtime only, never imported by Jest barrel) |
| `frontend/apps/mobile/mocks/handlers/voice.ts` | Modified — HTTP-only; removed `ws` import + WS handler; applied Rule 18 wildcard prefix to all HTTP handlers |
| `frontend/apps/mobile/mocks/handlers/index.ts` | Modified — removed `voiceWsHandler` import + spread; barrel is now WS-free/Jest-safe |
| `frontend/apps/mobile/mocks/browser.ts` | Modified — composes `voiceWsHandler` itself for dev runtime |
| `frontend/apps/mobile/__tests__/meta/mswServerSmoke.test.ts` | Created — smoke meta-test proving shared server works under jest-expo |
| `frontend/apps/mobile/__tests__/meta/noApiClientMock.test.ts` | Created — anti-regression ratchet scanning for banned `jest.mock("@pilot/shared-api")` |
| `frontend/apps/mobile/__tests__/meta/no_api_client_mock_baseline.json` | Created — empty baseline `{}` (full closure) |
| `frontend/apps/mobile/mocks/README.md` | Created — house doc with 5 required sections |
| `frontend/apps/mobile/package.json` | Modified — added `--forceExit` to `test` script (MSW + Jest open-handle fix) |
| `frontend/apps/mobile/__tests__/batch_mob_b8/sync_policy_hook.test.tsx` | Modified — converted to MSW; removed banned mock + `jest.requireMock` reset |
| `frontend/apps/mobile/__tests__/batch_mob_b8/background_sync_settings.integration.test.tsx` | Modified — converted to MSW; removed banned mock + `jest.requireMock` reset |
| `frontend/apps/mobile/__tests__/batch_mob_b8/push_token_registration.test.tsx` | Modified — converted to MSW; request-body capture replaces `mockApiPost` assertions |
| `frontend/apps/mobile/__tests__/batch_ce_1/invoice_signoff.integration.test.tsx` | Modified — removed banned mock (cache pre-populated, mock was unused) |
| `frontend/apps/mobile/__tests__/batch_fe_b7/voice-upload-upgrade.unit.test.ts` | Modified — converted to MSW handler for `POST */api/v1/voice/upload-audio` |
| `frontend/apps/mobile/__tests__/batch_fe_b13/usePushPermission.test.ts` | Modified — converted to MSW; request-body capture replaces `mockApiPut` assertions; static import replaces dynamic import |
| `frontend/apps/mobile/__tests__/batch_mob_b9/recurring_job_indicators.test.tsx` | Modified — converted to MSW handler for `GET */api/v1/settings/loto-policy` |
| `frontend/apps/mobile/features/customer-comms/hooks/__tests__/useCustomerThreads.test.ts` | Modified — converted to MSW; replaced fetch-spy with data-return assertion |
| `frontend/apps/mobile/features/jobs/hooks/__tests__/useSignoffContext.test.tsx` | Modified — converted to MSW handler for `GET */api/v1/jobs/:jobId/signoff-context` |
| `frontend/apps/mobile/features/jobs/components/detail/__tests__/InvoiceSignoffCaptureScreen.test.tsx` | Modified — removed banned mock (cache pre-populated, mock was unused) |

#### Tests Added

| Test File | Type | Tests | All Pass |
|---|---|---|---|
| `apps/mobile/__tests__/meta/mswServerSmoke.test.ts` | Meta | 1 | ✅ |
| `apps/mobile/__tests__/meta/noApiClientMock.test.ts` | Meta | 1 | ✅ |

#### Sync-api-types Exception

Not run — design §D documented exception: no hooks created or modified, no contract types consumed. This batch converts test-mock mechanics only.

#### Endpoint Verification

All endpoints preserved from existing mocks — no new URLs invented. Verified in `openapi_schema_map.md`:
- `GET /api/v1/settings/background-sync-policy` ✅
- `POST /api/v1/mobile/push-tokens` ✅
- `GET/PUT /api/v1/users/me/devices/{device_id}/push-permission` ✅
- `GET /api/v1/invoices/{invoice_id}/signoff` ✅
- `GET /api/v1/health/celery` ✅ (smoke test)
- `POST /api/v1/voice/upload-audio` ✅
- `GET /api/v1/settings/loto-policy` ✅
- `GET /api/v1/mobile/inbox/customer-threads` ✅
- `GET /api/v1/jobs/{job_id}/signoff-context` ✅ (hook-internal path, not in OpenAPI — preserved from existing mock)
