# Batch Design: TEST-UPLIFT-1B — FE Error-Rendering + MSW Fidelity (React Track)

**Version**: 1.0
**Date**: 2026-08-27
**Author**: Pilot Architect
**Batch**: TEST-UPLIFT-1B (Phase 1 — launch plan §1.1 Ord 19; sub-batch of TEST-UPLIFT-1, Ord 4 / §3.4)
**Owner**: Pilot React Engineer (executing)
**Prompt**: `batch-test-uplift-1b-react-engr-prompt.md`
**Source plan**: `pilot-launch-plan.md` §3.4 scope items **2, 3** (item 6 belongs to sub-batch 1C RN); sequential sub-batches per Tom 2026-08-27
**Depends on**: TEST-UPLIFT-1A ✅ 2026-08-27 (its "Findings for 1B" subsection is an input — see §A)
**Estimated session**: 4–5 hours
**Platform**: Web (`apps/web`) + `packages/shared-api` (one new helper module). **Mobile untouched** (1C owns it).
**Cost impact**: **$0** — no AWS, no vendors, no new npm dependencies (Rule 8 — the MSW-schema validator is hand-rolled on the existing MSW 2 / Vitest stack)

---

## A. Input Read Summary

| Input | What was read / verified | Date |
|---|---|---|
| `pilot-launch-plan.md` | §1.1 Ord 4 + Ord 18 (1A ✅); §3.4 card scope items 2–3; §3.18 closed card (1A outcomes) | 2026-08-27 |
| 1A Completion Summary (`batch-test-uplift-1a-python-engr-prompt.md` Appendix) | **Findings for 1B**: ① `POST /invoices/{id}/send` 404 + `PUT /signup/{id}/step2` 404 were plain-string bodies → now RFC 7807 dicts (FE parses `detail.title`/`detail.detail`); ② `POST /public/invoices/{token}/confirm-payment` 401 already RFC 7807; ③ MAP_CACHE TF staged (drive-time ETA cache misses until applied); ④ zero endpoint changes → `pnpm sync-api-types` handoff not strictly required, still run per inclusions §3 (hook-touching batch) | 2026-08-27 |
| `frontend/react-engr-std-prompt-inclusions.md` | Full file (968 lines) — all REQUIRED/CONDITIONAL sections; §16 section order; §17 anti-patterns | 2026-08-27 |
| `packages/shared-api/src/client.ts` | `apiClient` = raw Axios instance: JWT request interceptor + 401-refresh response interceptor. **No RFC 7807 parsing layer** — every call site receives a raw `AxiosError`; `error.response.data.detail` carries the problem body. `isAxiosError` re-exported | 2026-08-27 |
| `apps/web` apiClient grep | **237 call sites** (`apiClient.get/post/put/patch/delete`) across ~40 feature domains — full per-site audit closure impossible in one batch (§G Q1 ratchet) | 2026-08-27 |
| `apps/web/src/mocks/handlers/` | **40 handler files** + barrel `index.ts` | 2026-08-27 |
| Error-handling precedents (grep `rfc 7807` in `frontend/`) | Per-feature ad-hoc parsers exist and diverge: `useTenantSubscription.ts` (local extract helper), `useRemoveMfaMethod.ts` (`code` exposure), `useMoveJob.ts` (409-and-refresh body), `MfaApiError`/`parseMfaError()` in `packages/ui` MFA wizard (web + mobile), `JobEditPage.tsx` (422 inline detail) — **no shared helper** (§G Q2) | 2026-08-27 |
| `packages/ui/src/index.ts` | Component-existence check (Rule 1.5/§3.9): `ErrorState`, `LoadingState`, `EmptyState`, `NotificationBanner` + `NotificationQueueProvider`/`useNotificationQueue`, `CONFLICT_CLASS_TOKENS` all exist — **zero new components** (§I) | 2026-08-27 |
| 2026-08-10 wizard-hang incident | `batch-platform-sms-b1-design.md` v1.1: phone page polls `collected_data.sms_consent_status === "opted_in"`; backend never included the field → infinite "Check your phone" hang. **The MSW mock carried `sms_consent_status` — the mock was ahead of the real API and masked the gap in tests.** Archive row: "MSW mock fidelity: signup `/state` mocks must match real response shape → diff MSW fixtures against `openapi.json` schemas" | 2026-08-27 |
| DLC-B3 graceful-state model | `PublicInvoicePage`/`PublicQuotePage` 401/404 → friendly invalid-link UI (the rendering model for scope item 2); INV-ROUTE-FIX canonical 401/410 RFC 7807 contract | 2026-08-27 |
| 1A design (`batch-test-uplift-1a-design.md`) | Ratchet pattern (§F.3) + §G decision format — reused here (§E, §F.2, §G Q1) | 2026-08-27 |

---

## B. Migration Plan — **None**

Zero DB/schema/data changes (frontend-only batch). Seed Data Rollout (Rule 11.5) N/A. No Alembic, no MCP queries required beyond optional spot-checks.

---

## C. Execution Order

| # | Task | Scope item | Gate to proceed |
|---|---|---|---|
| 1 | **Shared problem-details helper** — new `packages/shared-api/src/problem.ts`: `getApiProblem(error)` normalizes all three FastAPI error-body shapes (RFC 7807 dict under `detail`, legacy plain-string `detail`, validation-array `detail`) → `ApiProblem { status, type?, title?, detail?, code? }`; export from `packages/shared-api/src/index.ts`; unit tests in `packages/shared-api/src/problem.test.ts` (dict / string / array / network-error-no-response / non-axios throw) | 2 (foundation) | Helper tests green; barrel export resolves |
| 2 | **Error-surface audit + ratchet meta-test** — `apps/web/src/__tests__/meta/errorSurfaceRatchet.test.ts`: scans `apps/web/src/features/**/hooks/*.ts*` for files containing `apiClient.` calls; each such hook file must contain error-handling evidence (`getApiProblem` \| `isError` \| `onError` \| `errorCode` \| `ErrorState` \| `NotificationBanner`) **or** be listed in the checked-in baseline `apps/web/src/__tests__/meta/error_surface_baseline.json`. Same ratchet semantics as 1A: fail on NEW unbaselined gap; fail on stale baseline entry | 2 | Meta-test green against generated baseline |
| 3 | **Priority burn-down — money/founder-path surfaces** (§C.1): wire each listed hook/component chain to `getApiProblem` + a rendered error surface (`ErrorState` for queries, `NotificationBanner` fault severity or inline field-level text for mutations — DLC-B3 model); add per-surface unit tests asserting the MSW 4xx/5xx override renders the problem `detail` (never silent, never raw dump) | 2 | All §C.1 surfaces have ≥1 error-render test |
| 4 | **MSW fixture-fidelity harness** — `apps/web/src/__tests__/meta/mswContract.test.ts`: loads `backend/openapi.json`, resolves each §C.2 priority endpoint's 2xx response schema, and validates the corresponding MSW fixture payload (required keys present, primitive types match, enums respected — hand-rolled recursive checker, no new dep); drift → named failing assertion. Plus the **wizard-hang regression**: signup `/state` fixture validated against `SignupStateResponse` schema + a comment block documenting the `collected_data` `additionalProperties:true` blind spot (PLATFORM-SMS-B1 decision) | 3 | Harness green on §C.2 set; drift fixtures fixed in-batch |
| 5 | **Signup wizard hang-path hardening** — audit the signup feature's manual polling loops (phone page `sms_consent_status` poll, any `setInterval`/`setTimeout` chains): each must be bounded (max attempts → renders a defined error/escape state, never an infinite spinner) and must render a fetch-error state via `getApiProblem` when `/state` fails. Add regression tests: (a) `/state` 500 → error surface; (b) poll exhausts → escape state | 2+3 (incident surface) | Tests prove no unbounded hang path |

### C.1 Task 3 priority surfaces (money + founder path; mirrors the 1A backend burn-down)

| # | Surface (hook → component) | Error UX to wire |
|---|---|---|
| 1 | `useRecordPayment` → record-payment modal/section | 404/422 → inline `detail` via `getApiProblem` (mutation banner) |
| 2 | `useSendInvoice` → invoice detail send CTA | 404/409 → `NotificationBanner` fault severity with problem `detail` |
| 3 | `useTenantSubscription` (change-tier / upgrade-from-charter mutations) → Settings billing | Replace the local extract helper with `getApiProblem`; 404/422 → banner |
| 4 | `useSignupWizard` (`/state` fetch) → wizard shell | fetch error → `ErrorState` with retry (DLC-B3 pattern) |
| 5 | Signup step submits (`step2`/`step3`/`step4`/`step5` call sites in `app/signup/*`) | 404/409/422 → inline problem `detail` (never advance on error) |
| 6 | `PublicInvoicePage` + `PublicQuotePage` (public token pages) | Verify DLC-B3 401/404/410 graceful branches intact; adopt `getApiProblem` internally; lock with tests |
| 7 | `useCreateCustomer` / `useCreateJob` forms | 422 → inline `detail` |

### C.2 Task 4 priority MSW handlers (incident + money path)

`signupHandlers.ts` (incident surface) · `publicLinkHandlers.ts` · `invoiceDetailHandlers.ts` · `charterUpgradeHandlers.ts` · `stripeConnectHandlers.ts` · `customerHandlers.ts` · `jobs.ts` — the remaining 33 handler files are baselined for **BE-TESTS-MAINT** (launch plan §1.2 row 2), same disposition as the 1A backend remainder.

---

## D. New API Endpoints

**None.** Zero backend changes → no OpenAPI regeneration; `pnpm sync-api-types` is still run as the engineer's first Pre-Work step (inclusions §3 — hook-touching batch; also re-validates the 1A RFC 7807 fixes didn't alter contracts).

---

## E. Pattern Reuse Decisions

| Pattern / rule | Application |
|---|---|
| **Ratchet guard** (1A §F.3 — now the house pattern for audit-scale gaps) | Checked-in baseline + meta-test fails on the delta (new gap) or stale entry. Both Task 2 (error surfaces) and Task 4 (MSW handlers) use it. Burn-down only shrinks baselines |
| **Four-class severity + `<NotificationBanner>`** (§16 locked pattern) | Mutation errors route to fault-severity banner with the RFC 7807 `detail` — never raw `error.message`, never swallowed |
| **DLC-B3 graceful public-link states** (the card's named model) | Query/page-level failures render `ErrorState`/friendly invalid-link UI — Task 3 #6 locks this with regression tests |
| **409-and-refresh** (§16.4) | Untouched — `useMoveJob`/`usePublishTenantSite` already parse their 409 bodies; the audit must not "simplify" them into `getApiProblem` (§G Q4) |
| **`apiClient` mandatory / no `fetch()`** (rules §2) | The helper lives in `packages/shared-api` beside the client — the one import site every feature already uses |
| **TanStack Query v5 `retry: false` test setup + MSW `setupServer`** (inclusions §9) | All new tests; per-test `server.use()` overrides; `resetHandlers()` in `afterEach`; never mock `apiClient` directly |
| **Rule 8 — no new npm deps** | The schema checker is hand-rolled (~100 LOC: type/required/enum recursion over `openapi.json` schemas) |
| **Cost guardrail** | $0 delta |

---

## F. Shared Module Interfaces

### F.1 Problem-details helper (Task 1)

```typescript
// packages/shared-api/src/problem.ts
export interface ApiProblem {
  status: number;           // HTTP status (0 = network error, no response)
  type?: string;            // RFC 7807 type URI when present
  title?: string;           // short summary (banner heading)
  detail?: string;          // human sentence (banner/body copy) — ALWAYS populated when the server sent one
  code?: string;            // machine code extension field when present (e.g. mfa_code_expired)
}

/** Normalize any thrown value from an apiClient call into an ApiProblem.
 *  Handles: RFC 7807 dict in data.detail · legacy string data.detail ·
 *  FastAPI validation-array data.detail (joined msg list) · network errors
 *  (no response → status 0, generic detail) · non-axios throws (status 0). */
export function getApiProblem(error: unknown): ApiProblem;
```

### F.2 Error-surface ratchet (Task 2)

```typescript
// apps/web/src/__tests__/meta/errorSurfaceRatchet.test.ts
// - _hookFilesWithApiCalls(): features/**/hooks/*.ts* containing "apiClient."
// - ERROR_EVIDENCE = /getApiProblem|isError|onError|errorCode|ErrorState|NotificationBanner/
// - baseline: apps/web/src/__tests__/meta/error_surface_baseline.json
// - test_no_new_error_surface_gaps + test_baseline_entries_still_gaps (prune reminder)
```

### F.3 MSW contract harness (Task 4)

```typescript
// apps/web/src/__tests__/meta/mswContract.test.ts
// - loadOpenApi(): backend/openapi.json (repo-relative path)
// - resolveResponseSchema(path, method, status="200"|"201"): deref $ref → component schema
// - assertMatchesSchema(payload, schema, path): required[] present, primitive types, enum values
// - One test per §C.2 endpoint: fixture payload (imported from the handler's fixture exports
//   where available; otherwise captured via the handler in-process) vs its openapi schema
```

**No new Celery tasks, no new shared components, no `permissions.ts` changes.**

---

## G. Open Questions Resolved

- **Q1 — Full 237-call-site audit closure in one batch?** **No** (Rule 9.6). Ratchet + §C.1 priority burn-down (7 surfaces); the remaining hook files go into the checked-in baseline whose burn-down continues in **BE-TESTS-MAINT** (§1.2 row 2) alongside the 1A backend baseline remainder. The durable win is the meta-test: no NEW apiClient hook can ever again ship without error-handling evidence.
- **Q2 — New shared helper vs the existing per-feature parsers?** **One shared `getApiProblem` in `packages/shared-api`** (the package every feature already imports). Per-feature parsers that diverge (`useTenantSubscription:116`) are replaced in the §C.1 burn-down set only; specialty parsers with extension-field semantics (`MfaApiError`, `useMoveJob` 409 bodies) are **left alone** (Q4). The helper handles the three FastAPI body shapes because production still emits all three (1A fixed two plain-string 404s; the baseline guards the rest).
- **Q3 — Designer-mode spec required (Rule 1.5)?** **No.** The Rule 1.5 trigger is "a new or changed surface." 1B changes no visuals and adds no components — it wires existing `ErrorState`/`NotificationBanner` patterns into existing surfaces. §I is an explicit zero-new-components manifest with the existence check recorded in §A. Flagged here for Tom visibility per protocol.
- **Q4 — Does `getApiProblem` replace the 409-and-refresh parsers?** **No.** §16.4 409 bodies carry extension fields (`current_job_version`, `current_state`, `brand_status`) that drive refresh logic — that is a control-flow contract, not display copy. `useMoveJob`, `usePublishTenantSite`, and the MFA wizard's `MfaApiError` keep their bespoke parsing. The audit's evidence regex counts them as covered.
- **Q5 — Can the MSW harness catch the exact 2026-08-10 incident?** **Partially — and the design says so honestly.** `collected_data` is deliberately `additionalProperties: true` (PLATFORM-SMS-B1 architect decision), so schema-diff cannot flag an extra/missing key inside it. The harness catches typed-property drift (required keys, enums, primitives — the common case across 40 handler files); the `collected_data` blind spot is closed by Task 5's bounded-polling + error-state hardening and documented in a comment on the signup contract test so the next drift of that exact kind fails loudly in a different way.
- **Q6 — Where do meta-tests live on the FE?** `apps/web/src/__tests__/meta/` — a new top-level test folder for cross-cutting contract/ratchet tests (distinct from `__tests__/batch_*/` integration folders; `vitest` picks it up under the existing include globs — engineer verifies the glob covers it and extends `vitest.config` include if needed).
- **Q7 — Scope discipline on per-feature parser replacement?** Only the §C.1 seven surfaces get rewired. A codebase-wide "replace every local parser" sweep is explicitly out of scope (baseline-tracked) — same Rule 9.6 calibration as 1A.

---

## H. Surface Mockup Reference

**No new or changed surfaces** — zero visual deltas (§G Q3). Existing surfaces receiving error-state wiring (§C.1): invoice detail (record-payment modal, send CTA), Settings → Subscription & Billing, signup wizard shell + step pages, public `/i/[token]` + `/q/[token]` pages, customer/job create forms. The rendering model for all of them is the already-shipped **DLC-B3 graceful 401/404 invalid-link UI** (query/page level → `ErrorState`; mutation level → `NotificationBanner` fault severity or inline field text). §16 patterns consumed: four-class severity (banner routing), 409-and-refresh (untouched, §G Q4), always-preview-before-send (N/A).

## I. Component Manifest

**Zero new components.** Component-existence check (§A): `ErrorState`, `LoadingState`, `EmptyState`, `NotificationBanner` (+ queue provider/hook) already exist in `packages/ui/src/index.ts`. The only new module is **`packages/shared-api/src/problem.ts`** (a helper, not a component) + its test + the two meta-test files + the baseline JSON. No orphan components; no `index.ts` (ui) export changes; `packages/shared-api/src/index.ts` gains one export line.
