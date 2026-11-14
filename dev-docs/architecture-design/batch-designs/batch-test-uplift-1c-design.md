# Batch Design: TEST-UPLIFT-1C — Mobile Jest + MSW Restoration (RN Track)

**Version**: 1.0
**Date**: 2026-08-27
**Author**: Pilot Architect
**Batch**: TEST-UPLIFT-1C (Phase 1 — launch plan §1.1 Ord 20; sub-batch of TEST-UPLIFT-1, Ord 4 / §3.4)
**Owner**: Pilot React Engineer (executing — RN platform; per the MOB-B10 prompt precedent, mobile prompts target the Pilot React Engineer mode)
**Prompt**: `batch-test-uplift-1c-react-native-engr-prompt.md`
**Source plan**: `pilot-launch-plan.md` §3.4 scope item **6** — *"Mobile Jest + MSW incompatibility fix (moved from PLAT-DEBT) — mock the voice WS handler module; restore HTTP-level mocking on mobile per react-inclusions §9"*
**Depends on**: TEST-UPLIFT-1B ✅ 2026-08-27 (its "Findings for 1C" appendix — `getApiProblem`/`parseProblemBody` confirmed RN-safe; mobile MSW wildcard-prefix rule; severity type is `"error"`)
**Estimated session**: 3–4 hours
**Platform**: Mobile only (`apps/mobile`). Web and backend untouched.
**Cost impact**: **$0** — test infrastructure only; no new npm dependencies (MSW 2 is already a mobile devDependency)

---

## A. Input Read Summary

| Input | What was read / verified | Date |
|---|---|---|
| `pilot-launch-plan.md` | §3.4 scope item 6; §1.1 Ord 18/19 (1A/1B ✅); PLAT-DEBT origin row (§6c: "Mobile Jest + MSW incompatibility → Moved to TEST-UPLIFT-1") | 2026-08-27 |
| 1B Completion Summary (`batch-test-uplift-1b-react-engr-prompt.md` Appendix) | Findings for 1C: ① `getApiProblem` + `parseProblemBody` are RN-safe (no DOM APIs) and already importable from `@pilot/shared-api`; ② mobile handlers must use the `*/api/v1/...` wildcard prefix (Rule 18); ③ `NotificationSeverity` is `"error"` (not `"fault"`) on both platforms; ④ `collected_data` blind spot applies to mobile mocks too | 2026-08-27 |
| `frontend/apps/mobile/package.json` | jest-expo preset; `jest.setup.ts` in `setupFilesAfterEnv`; `moduleNameMapper` maps `^msw/(.*)$` → `node_modules/msw/lib/$1/index.js`; `transformIgnorePatterns` already whitelists `msw`, `@mswjs`, `@open-draft`, `until-async` — **MSW-on-Jest plumbing was pre-wired but is unusable via the barrel** (§G Q1) | 2026-08-27 |
| `frontend/apps/mobile/jest.setup.ts` | Global native-module mocks (AsyncStorage, expo-location/image-picker/haptics/clipboard). **No MSW server wiring** — tests opt in per file | 2026-08-27 |
| `frontend/apps/mobile/mocks/handlers/index.ts` | **The incompatibility**: the barrel statically imports `voiceWsHandler` from `./voice` → `ws.link(...).addEventListener(...)` is instantiated **at module evaluation time** → any Jest import of the barrel (or of `mocks/server.ts`) evaluates MSW's `ws` in the Node/jsdom environment → the shared server is effectively unusable in tests | 2026-08-27 |
| `frontend/apps/mobile/mocks/handlers/voice.ts` | Exports `voiceHttpHandlers` (Jest-safe) + `voiceWsHandler` (MSW 2.x `ws.link`, the poison import); comment claims "permanently MSW for all test environments" — in practice **zero Jest tests consume the barrel** | 2026-08-27 |
| `frontend/apps/mobile/mocks/server.ts` | `setupServer(...handlers)` — dead in practice because `handlers` contains the WS poison import | 2026-08-27 |
| `frontend/apps/mobile/mocks/browser.ts` | Dev-runtime path: lazy `startMockServiceWorker()` factory (guards Metro SSR `window` undefined) — **needs the WS handler** for voice dev | 2026-08-27 |
| Mobile test grep (`setupServer` / `jest.mock("@pilot/shared-api"`) | 88 hits: the passing pattern is **per-file inline `setupServer(http.get("*/api/v1/..."))`** (never the barrel); **10 files use the banned `jest.mock("@pilot/shared-api")`** (§C.1 list) — exactly the "restore HTTP-level mocking" gap the card names | 2026-08-27 |
| `frontend/react-engr-std-prompt-inclusions.md` | §9 test standards: "Never mock `apiClient` directly — MSW intercepts at the HTTP level and is the only correct approach"; §8.2 mobile constraints; §10 canonical Phase 2 command | 2026-08-27 |
| `batch-mob-b10-react-native-engr-prompt.md` | RN prompt exemplar: **Mode = Pilot React Engineer**; mobile critical-rule selection pattern; `__tests__/batch_mob_b{N}/` integration-folder rule | 2026-08-27 |
| 1A/1B designs (`batch-test-uplift-1a-design.md`, `batch-test-uplift-1b-design.md`) | Ratchet pattern (house standard for audit-scale gaps) — reused for the anti-regression guard (§F.3) | 2026-08-27 |

---

## B. Migration Plan — **None**

Zero DB/schema/data changes; zero backend changes; zero production-code changes outside `apps/mobile/mocks/` (test infrastructure) and test files. Seed Data Rollout N/A.

---

## C. Execution Order

| # | Task | Scope item | Gate to proceed |
|---|---|---|---|
| 1 | **Isolate the voice WS handler** — move `voiceWsHandler` (and its `ws.link` machinery) out of `mocks/handlers/voice.ts` into a new `mocks/handlers/voice.ws.ts`; `voice.ts` keeps only `voiceHttpHandlers`; the barrel `index.ts` becomes **WS-free** (`handlers` = HTTP only); `mocks/browser.ts` composes `[...handlers, voiceWsHandler]` itself (dev runtime keeps voice streaming); `mocks/server.ts` needs no change (it spreads the now-safe barrel) | 6 | Barrel + server import cleanly under Jest |
| 2 | **Jest smoke meta-test** — new `apps/mobile/__tests__/meta/mswServerSmoke.test.ts`: imports the shared `server` from `mocks/server.ts`, `listen()` → issues a request against a default barrel handler (e.g. the `health.ts` handler) via `apiClient` → asserts the mocked JSON → `close()`. This is the fail-loud proof the shared server works under jest-expo — and the permanent guard against re-poisoning | 6 | Smoke test green |
| 3 | **Convert the 10 banned-pattern test files to MSW** (§C.1) — replace each `jest.mock("@pilot/shared-api")` with `setupServer` + wildcard `*/api/v1/...` handlers (the established mobile pattern), preserving each file's existing assertions/fixtures | 6 | All 10 files green under MSW; zero `jest.mock("@pilot/shared-api"` remaining |
| 4 | **Anti-regression ratchet** — `apps/mobile/__tests__/meta/noApiClientMock.test.ts`: scans all mobile test files for `jest.mock("@pilot/shared-api"` (both quote styles) and fails on any hit outside a checked-in baseline `no_api_client_mock_baseline.json` (target: **empty baseline** — any justified residue must carry a reason and is tracked to BE-TESTS-MAINT) | 6 | Ratchet green with empty (or reasoned) baseline |
| 5 | **`mocks/README.md`** — short house doc: how to use `mocks/server.ts` in Jest (opt-in per test file, `server.use()` overrides, `resetHandlers()` in `afterEach`), the `*/api/v1/...` wildcard-prefix rule (Rule 18), why `voice.ws.ts` is isolated (module-evaluation poisoning), the no-apiClient-mock rule, and the `getApiProblem` RN-safe pointer for error-path tests | 6 | Doc merged |

### C.1 Banned-pattern files (design-time grep, 2026-08-27 — engineer re-greps at execution)

| # | Test file | Mocked endpoint(s) to port into MSW handlers |
|---|---|---|
| 1 | `__tests__/batch_fe_b13/usePushPermission.test.ts` | push-permission PUT |
| 2 | `__tests__/batch_ce_1/invoice_signoff.integration.test.tsx` | signoff context GET |
| 3 | `__tests__/batch_mob_b9/recurring_job_indicators.test.tsx` | recurrence-rule endpoints |
| 4 | `__tests__/batch_fe_b7/voice-upload-upgrade.unit.test.ts` | voice upload |
| 5 | `__tests__/batch_mob_b8/sync_policy_hook.test.tsx` | `GET …/settings/background-sync-policy` |
| 6 | `__tests__/batch_mob_b8/background_sync_settings.integration.test.tsx` | same |
| 7 | `__tests__/batch_mob_b8/push_token_registration.test.tsx` | `POST …/mobile/push-tokens` |
| 8 | `features/customer-comms/hooks/__tests__/useCustomerThreads.test.ts` | customer threads GET |
| 9 | `features/jobs/hooks/__tests__/useSignoffContext.test.tsx` | signoff context GET |
| 10 | `features/jobs/components/detail/__tests__/InvoiceSignoffCaptureScreen.test.tsx` | signoff context GET |

---

## D. New API Endpoints

**None.** Zero backend changes → no OpenAPI regeneration; `pnpm sync-api-types` is **not required** (no new/modified hooks consuming contracts — the batch converts test-mock mechanics only). The prompt states this explicitly as the documented exception to inclusions §3 ("purely UI/test-infra batch with no new hooks").

---

## E. Pattern Reuse Decisions

| Pattern / rule | Application |
|---|---|
| **MSW-at-HTTP-level only** (inclusions §9) | The whole point of the batch — never `jest.mock("@pilot/shared-api")`; `setupServer` + wildcard handlers |
| **Ratchet guard** (1A §F.3 / 1B §F.2 house pattern) | Task 4 anti-regression meta-test + checked-in baseline; baseline target is **empty** (full closure fits Rule 9.6 here — only 10 files) |
| **Wildcard URL prefix** (react-engineer Rule 18, per 1B findings) | All mobile MSW handlers use `*/api/v1/...` — RN fetch/axios base-URL resolution differs from web |
| **Lazy-factory MSW worker** (`browser.ts` existing pattern) | WS handler moves to dev-runtime composition; nothing evaluates `ws.link` at Jest module-load time |
| **Module-evaluation hygiene** (the `browser.ts` Metro-SSR lesson) | The root cause class — side effects at module scope break alternate runtimes (Jest, Metro SSR). The fix keeps all handler modules side-effect-free at import time |
| **Cost guardrail** | $0; no new deps (MSW 2 already present) |

---

## F. Shared Module Interfaces

### F.1 Module restructure (Task 1)

```typescript
// mocks/handlers/voice.ws.ts  (NEW — dev-runtime only; NEVER imported by the Jest barrel)
import { ws } from "msw";
export const voiceWsHandler = /* moved verbatim from voice.ts: ws.link(...).addEventListener("connection", ...) */;

// mocks/handlers/voice.ts  (KEEPS only Jest-safe HTTP handlers)
export const voiceHttpHandlers = [ /* unchanged */ ];

// mocks/handlers/index.ts  (WS-free barrel — `handlers` is now Jest-safe)
import { voiceHttpHandlers } from "./voice";
export const handlers = [ ...authHandlers, ...voiceHttpHandlers, /* …all HTTP only… */ ];

// mocks/browser.ts  (dev runtime composes WS itself)
import { handlers } from "./handlers";
import { voiceWsHandler } from "./handlers/voice.ws";
const worker = setupWorker(...handlers, voiceWsHandler);
```

### F.2 Smoke meta-test (Task 2)

```typescript
// apps/mobile/__tests__/meta/mswServerSmoke.test.ts
// import { server } from "../../mocks/server";
// beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
// afterEach(() => server.resetHandlers());
// afterAll(() => server.close());
// it("shared MSW server intercepts an apiClient request under jest-expo", async () => {
//   const res = await apiClient.get("/api/v1/health");  // default barrel handler (mocks/handlers/health.ts)
//   expect(res.data).toBeTruthy();
// });
```

### F.3 Anti-regression ratchet (Task 4)

```typescript
// apps/mobile/__tests__/meta/noApiClientMock.test.ts
// - scans apps/mobile/**/{__tests__,*.test.ts?(x)} for /jest\.mock\(\s*["']@pilot\/shared-api["']/
// - fails on any hit not in no_api_client_mock_baseline.json (target: empty baseline)
// - fails on stale baseline entries (file no longer mocks → prune)
```

---

## G. Open Questions Resolved

- **Q1 — Why is the barrel the problem if `moduleNameMapper`/`transformIgnorePatterns` already support MSW?** The Jest plumbing was pre-wired for MSW *HTTP* interception (and ~30 test files prove inline `setupServer` works). The poison is `voiceWsHandler`'s **module-evaluation-time** `ws.link(...)` instantiation inside the shared barrel: importing the barrel in Jest evaluates MSW's WebSocket machinery in the Node/jsdom context. The fix is structural isolation (F.1), not config.
- **Q2 — Fix the shared server or delete it?** **Fix it.** The per-file inline-server pattern works but means 40+ hand-rolled partial servers and rotting shared fixtures — the exact fidelity gap TEST-UPLIFT-1 exists to close (and E2E-MOB-1 / MOB-UX-B1 need a working shared server next). The smoke meta-test (Task 2) locks the restoration.
- **Q3 — Convert all 10 banned-pattern files or baseline some?** **Convert all 10** — the set is small enough for full closure inside Rule 9.6 (no remainder baseline needed; the ratchet's baseline ships empty). If the engineer finds an 11th+ file at execution time, it converts too if trivial, or lands in the baseline with a reason → BE-TESTS-MAINT.
- **Q4 — Should `jest.setup.ts` start the shared server globally?** **No.** The established mobile pattern is per-file opt-in (`const server = setupServer(...)` at file scope with file-specific handlers). Global listen would force every existing inline-server file to reconcile with default handlers — scope explosion for zero gain. `mocks/README.md` documents the opt-in patterns (shared server OR inline server) and when to use which.
- **Q5 — Designer spec / new components?** **Neither.** Test-infrastructure batch with zero user-facing surface (Rule 1.5 not triggered; §I zero-component manifest).
- **Q6 — Does this touch the 1B flaky-mobile-tests finding (3→2 order-dependent)?** Not a goal — but the apiClient-mock conversions may incidentally remove ordering coupling (module mocks leak across files; MSW servers are per-file scoped). The engineer notes any flaky-count change in the Completion Summary; stability work itself stays with **BE-TESTS-MAINT**.
- **Q7 — Voice WS test coverage after isolation?** Voice streaming has no Jest coverage today (WS can't run under `msw/node` in jest-expo). This batch does **not** attempt WS-under-Jest support — voice E2E belongs to E2E-MOB-1 (Maestro). The `voice.ws.ts` module keeps full fidelity for the dev runtime (`startMockServiceWorker`), which is its actual consumer.

---

## H. Surface Mockup Reference

**No surfaces** — test-infrastructure batch (§G Q5). Zero visual deltas; no designer spec.

## I. Component Manifest

**Zero new components.** New/changed files are test infrastructure only: `mocks/handlers/voice.ws.ts` (new module), `mocks/handlers/{voice.ts,index.ts}`, `mocks/browser.ts`, `mocks/README.md` (new doc), `__tests__/meta/{mswServerSmoke.test.ts,noApiClientMock.test.ts,no_api_client_mock_baseline.json}` (new), and the §C.1 converted test files. No `packages/ui` changes; no barrel exports beyond the mocks-internal restructure.
