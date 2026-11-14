# Implementation Prompt: DLC-B3 — Public Invoice/Quote Graceful Error States (404 branch + regression tests + SSR/proxy 500 fix)

**Mode**: Pilot React Engineer
**Batch**: DLC-B3
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §2.0 #9 (DLC-B2 fast-follow) — closes the fast-follow item in the 10DLC submission playbook
**Related playbook**: `dev-docs/integrations/telnyx/telnyx-10dlc-customer-comms-campaign.md` §0 "Post-Submit Fast-Follow"
**Estimated session**: 3–4 hours
**Platform**: Web only (`apps/web`)
**Backend companion — RUNS FIRST**: **INV-ROUTE-FIX** (`batch-inv-route-fix-python-engr-prompt.md`) — a P0 backend route collision must be fixed and OpenAPI regenerated BEFORE this batch. **First Pre-Work step here is `pnpm sync-api-types`.** Do not start until the Python Engineer confirms INV-ROUTE-FIX is merged.

> ⚠️ **This prompt was originally scoped as "tests only" under the assumption the frontend already handled the reviewer-click path. That assumption was DISPROVEN.** A live `curl` returned **404** (not the expected 401), and the browser showed a **500** — because of a backend route collision (INV-ROUTE-FIX) AND two frontend gaps this batch must close: (1) `PublicInvoicePage`/`PublicQuotePage` have **no 404 branch**, and (2) the SSR `generateMetadata` / `/api/v1` rewrite proxy throws a **500** in production. Read the corrected context below.

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-react-engineer/react-engineer-rules.md`** — in full
- **`frontend/react-engr-std-prompt-inclusions.md`** §9 (Test Writing Standards) — this batch is almost entirely tests; the MSW + Vitest patterns there are the source of truth

Critical rules for this batch:

- **Rule (public-page `fetch` exception — DO NOT "FIX")**: The public invoice/quote pages **intentionally use `fetch()`, NOT `apiClient`**. This is a deliberate, established exception: these are *unauthenticated* customer-facing pages and `apiClient` injects a Cognito JWT. Sending a JWT would break the "signed URL is the only credential" model (see the `RULE 1: NEVER calls useAuth()` header in `PublicInvoicePage.tsx`). **Do not refactor these `fetch()` calls to `apiClient`.** The normal "`fetch()` is banned" rule does not apply to `apps/web/src/features/public-invoice/` or `public-quote/`.
- **Rule 9 (thin route files)**: `app/i/[token]/page.tsx` and `app/q/[token]/page.tsx` are already thin server components that render the feature component. Do NOT add logic to them.
- **Rule 10 (no "not my fault" failures)**: If ANY test fails during your work — even one that appears pre-existing — you must fix it before declaring the batch done. If you cannot find the root cause → STOP and ask Tom.
- **Rule (MSW at HTTP level)**: Simulate 401/410/500/network states with MSW `server.use(...)` overrides. NEVER mock `fetch` or `apiClient` directly.

---

## Context: Corrected Root Cause (Do Not Re-Litigate)

The 10DLC sample-link click surfaced a real production failure: `curl https://api.pilotfortrades.com/api/v1/public/invoices/A1b2C3` returned **404**, and the browser page showed **500** — neither is graceful. Investigation (2026-07-25) found **three** distinct defects across two layers. The **backend route collision is fixed by INV-ROUTE-FIX (runs first)**; this batch owns the **two frontend defects**.

**What the existing pages DO handle** (FE-B14, `PublicInvoicePage.tsx`): 410→`QuoteExpiredPage`, 401→"Invalid link" card (`data-testid="invoice-invalid-page"`), other non-OK→generic "Try again", network→generic, 200→ready.

**What is MISSING / BROKEN (this batch fixes):**

| # | Defect | Owner | Fix |
|---|---|---|---|
| 1 | **No 404 branch.** After INV-ROUTE-FIX, a bad token returns **401** (canonical) — but the frontend still has no explicit **404** handling; a 404 (e.g. unknown link) falls through to the generic "Error 404" state, not the friendly invalid-link page. | This batch (STEP 0) | Add a 404 branch that renders the same friendly invalid-link UI as 401. |
| 2 | **Browser 500 on `/i/[token]`.** `page.tsx` `generateMetadata` does a server-side `fetch` using `process.env.NEXT_PUBLIC_API_BASE_URL`, while the rewrite proxy uses `NEXT_PUBLIC_API_URL` (`next.config.ts`). A name mismatch / unset var makes the SSR fetch throw → **500 before the client component ever renders**. | This batch (STEP 0B) + verify with DevOps | Reconcile the env-var name; ensure `generateMetadata` failure is swallowed (it already has a try/catch — confirm it truly can't 500) and the page still renders the client component. |
| 3 | Backend route collision (legacy handler shadowed canonical, returned 404 w/ wrong shape). | **INV-ROUTE-FIX (Python, runs first)** | Not this batch — but this batch depends on its OpenAPI output. |

**Backend contract AFTER INV-ROUTE-FIX** (confirm via `pnpm sync-api-types` + `openapi_schema_map.md`, do not assume): canonical `_resolve_invoice_link_or_401` returns **401** (invalid/tampered token — now RFC 7807), **410** (expired/revoked/not-found/inactive). A garbage token like `A1b2C3` → **401**. The quote route mirrors this.

> **Do not "fix" the `fetch()` exception:** the public pages intentionally use `fetch()` not `apiClient` (unauthenticated; a JWT would break the signed-URL model — see `PublicInvoicePage.tsx`). Keep `fetch()`.

---

## Pre-Work: Establish Regression Baseline

Before touching any file:

```bash
cd <repo>/frontend
pnpm --filter web test 2>&1 | tail -5
```

Record the exact passed/failed counts. These must still pass at the end.

> If any tests are already failing before you start: do NOT treat them as "pre-existing." Either confirm with Tom they are a known accepted failure, or fix them before starting. Do not begin while tests are in an unexplained failed state.

## Pre-Work: Sync API Types — REQUIRED (BE-first handoff)

**INV-ROUTE-FIX changed the public-invoice OpenAPI contract** (removed the legacy route, made 401/410 RFC 7807). Run this FIRST, and do not start until the Python Engineer confirms INV-ROUTE-FIX is merged:

```bash
cd <repo>/frontend
pnpm sync-api-types
```

Then confirm only the signed-token public invoice route exists:

```bash
grep -A 3 "public/invoices" ../backend/openapi_schema_map.md
```

> The public pages use hand-written `fetch()` (not generated hooks), so no hook types change — but running `sync-api-types` confirms the BE handoff landed and guards against drift.

## Pre-Work: Read These Source Files

Read each with `read_file` before writing any test:

```
frontend/apps/web/src/features/public-invoice/PublicInvoicePage.tsx   ← the component under test; note every data-testid and each error branch
frontend/apps/web/src/features/public-quote/PublicQuotePage.tsx        ← quote sibling; identical error-branch structure
frontend/apps/web/src/features/public-quote/QuoteExpiredPage.tsx       ← the 410 page; note data-testid="quote-expired-page" and data-testid="expired-heading"
frontend/apps/web/src/features/public-invoice/types.ts                 ← normalizeInvoiceData shape (for the 200-OK ready-state test fixture)
frontend/apps/web/src/features/public-quote/types.ts                   ← normalizeQuoteData + ExpiredLinkMeta shape
```

Locate any existing test scaffolding and confirm none already cover these pages:

```bash
find frontend/apps/web/src/features/public-invoice -name "*.test.tsx"
find frontend/apps/web/src/features/public-quote -name "*.test.tsx"
grep -rn "invoice-invalid-page\|quote-expired-page" frontend/apps/web/src --include=*.test.tsx
# Expected: no results — this batch adds the first coverage.
```

Confirm the MSW test-server import path used elsewhere in `apps/web`:

```bash
grep -rn "setupServer" frontend/apps/web/src | head -5
```

---

## STEP 0 — Add a 404 branch to both public pages (bug fix)

> Read `PublicInvoicePage.tsx` and `PublicQuotePage.tsx` first. Adjust to the actual branch structure you find.

Both pages branch on `res.status === 410` and `=== 401`, then fall through to a generic `!res.ok`. A **404** (unknown link) currently hits the generic "Error 404" state. Add an explicit **404** branch that renders the **same friendly invalid-link UI as 401** — the customer cannot distinguish "invalid" from "not found," and shouldn't. The simplest correct change: treat 404 the same as 401 by extending the existing condition, e.g.:

```typescript
// Adjust to the real code — this is a starting point, not gospel
if (res.status === 401 || res.status === 404) {
  setPageState({ phase: "error-invalid" });
  return;
}
```

Apply to `PublicInvoicePage` and `PublicQuotePage`. Do NOT add a new `data-testid` — reuse `invoice-invalid-page` (and the quote equivalent) so STEP 1/2/3 tests cover both status codes.

### Intermediate verification (after STEP 0)
```bash
cd <repo>/frontend
pnpm --filter web test -- apps/web/src/features/public-invoice 2>&1 | tail -8
```

---

## STEP 0B — Fix the SSR 500 on `/i/[token]` and `/q/[token]` (bug fix)

> Read `app/i/[token]/page.tsx` and `next.config.ts` first.

The route's `generateMetadata` server-fetches `${process.env.NEXT_PUBLIC_API_BASE_URL ?? ""}/api/v1/public/invoices/${token}` (`page.tsx`), while the client rewrite proxy uses `NEXT_PUBLIC_API_URL` (`next.config.ts`). Two problems to resolve:

1. **Env-var name mismatch.** Standardize on ONE variable. Recommended: make `generateMetadata` use the SAME variable the proxy uses (`NEXT_PUBLIC_API_URL`), or fall back to a relative `/api/v1/...` path so the rewrite handles it. Confirm which var is actually set on the `pilot-web` ECS task before choosing — **coordinate with DevOps/Tom**; if neither is set in prod, that is the 500 and it's an env-config fix, not just code.
2. **Guarantee SSR can't 500.** `generateMetadata` already has a `try/catch` that falls through to generic metadata (`page.tsx`) — verify the throw is actually caught (a bad base URL like `undefined/api/...` can throw a `TypeError` inside `fetch()` that IS caught, but a malformed absolute URL may throw synchronously before `fetch`). Ensure any failure path returns the generic metadata and lets the client `PublicInvoicePage` render (which then shows the friendly 401/404/410 state). The page must NEVER return a 500 for a bad token.

> **This step may require a DevOps env-var change in addition to code.** Note in your Completion Summary exactly which variable you standardized on and whether an ECS task-definition env update is still required. If you cannot verify the prod env var → flag it for Tom, do not guess.

### Intermediate verification (after STEP 0B)
```bash
pnpm --filter web build 2>&1 | tail -15   # SSR route must compile; no runtime fetch at build for dynamic route
```

---

## STEP 1 — Unit tests: `PublicInvoicePage` error + ready states

**Create**: `frontend/apps/web/src/features/public-invoice/__tests__/PublicInvoicePage.test.tsx`

> Read `PublicInvoicePage.tsx` first. Use the actual `data-testid` values and copy strings you find — adjust anything below to match the real file.

Use MSW (`setupServer` from `msw/node`) to intercept `GET /api/v1/public/invoices/:token`. The component uses a relative `fetch("/api/v1/public/invoices/${token}")`, so MSW node interception works without a base URL. Follow the MSW-in-tests setup in `react-engr-std-prompt-inclusions.md` exactly (`server.listen` / `resetHandlers` in `afterEach` / `server.close`).

Required test cases (assert with `findBy*` since state is set from an async effect):

1. **410 → expired page**: handler returns `HttpResponse.json({ detail: "Link has expired" }, { status: 410 })` → `await screen.findByTestId("quote-expired-page")`; assert the "This link has expired" heading is present. Assert the tenant-contact block (`data-testid="tenant-contact-info"`) is **absent** (only `{detail}` returned).
2. **410 WITH tenant metadata → contact block shows**: handler returns `{ tenant_name, tenant_phone, tenant_email }` at status 410 → expired page renders AND `data-testid="tenant-contact-info"` is present with the phone/email links. (Forward-covers a future backend enhancement.)
3. **401 → invalid-link card**: handler returns status 401 → `await screen.findByTestId("invoice-invalid-page")`; assert the "Invalid link" heading and the "check the link in your email" copy.
4. **500 → generic error + retry**: handler returns status 500 → generic "Something went wrong" renders with a "Try again" button. Then override the handler to 200 and `fireEvent.click` "Try again" → assert the ready invoice renders (proves retry re-fetches).
5. **Network error → generic error**: handler uses `HttpResponse.error()` → generic connection error renders.
6. **200 → ready invoice**: handler returns a valid `PublicInvoiceResponse` fixture (unpaid, one line item) → `await screen.findByTestId("public-invoice-page")`; assert customer name and the "Pay …" button (`data-testid="pay-invoice-button"`) render.

Web test conventions: `@testing-library/react`, `import { describe, it, expect, vi, beforeAll, afterEach, afterAll } from "vitest"`, `toBeInTheDocument()`. No `next/navigation` mock needed unless the file imports it (it does not — but if a child does, mock per `inclusions §8.1`).

### Intermediate verification (run after Step 1)

```bash
cd <repo>/frontend
pnpm --filter web test -- apps/web/src/features/public-invoice/__tests__/PublicInvoicePage.test.tsx 2>&1 | tail -12
```

---

## STEP 2 — Unit tests: `PublicQuotePage` error states

**Create**: `frontend/apps/web/src/features/public-quote/__tests__/PublicQuotePage.test.tsx`

Mirror Step 1 for `GET /api/v1/public/quotes/:token`, covering: 410 → `quote-expired-page`; 410-with-tenant-meta → contact block; 401 → the quote's invalid-link state; 500 → generic + retry; network → generic; 200 → ready quote (`data-testid="quote-loading"` disappears, quote content renders). Read `PublicQuotePage.tsx` for the exact `data-testid` used on its 401/ready states and match them.

### Intermediate verification (run after Step 2)

```bash
pnpm --filter web test -- apps/web/src/features/public-quote/__tests__/PublicQuotePage.test.tsx 2>&1 | tail -12
```

---

## STEP 3 — Integration test: the 10DLC reviewer-click scenario (highest-value test)

**Create**: `frontend/apps/web/src/__tests__/batch_dlc_b3/public-invoice-invalid-token.integration.test.tsx`

This test encodes the exact Telnyx-reviewer scenario: a fake token must render a graceful page, never a crash or 404.

- Render `<PublicInvoicePage token="A1b2C3" />` (the literal fake token from the Telnyx sample link).
- MSW handler for `GET /api/v1/public/invoices/A1b2C3` returns **401** (matching what the real backend does for an unparseable token).
- Assert: `data-testid="invoice-invalid-page"` renders; the page does NOT throw; no unhandled error. Assert the friendly copy is visible.
- Add a second case: token that resolves to **410** (expired) → `quote-expired-page` renders. This covers the common real-world case (a genuine expired link).
- Add a third case: token that resolves to **404** → renders the SAME `invoice-invalid-page` (proves STEP 0's 404 branch). This is the exact status the live backend returned pre-fix, so it must be graceful.

> Integration tests for web live in `apps/web/src/__tests__/batch_[code]/` per `inclusions §9` — not co-located.

---

## STEP 4 (Low priority — do ONLY if Steps 1–3 are green and time remains) — Invalid-link copy consistency

The invoice **401 "Invalid link"** card (`PublicInvoicePage.tsx`) is a bare card, while the **410** page (`QuoteExpiredPage.tsx`) has an icon + warmer copy. Optionally align the 401 card's copy to be equally friendly (keep the existing `data-testid="invoice-invalid-page"` and `bg-fault-50` tokens unchanged so Step 1/3 tests still pass). **Do not extract a new shared component or change any testid** — that is scope creep for a fast-follow. If in doubt, skip Step 4; the tests are the deliverable.

---

## Final Verification

### Phase 1 — Targeted (during development)

```bash
cd <repo>/frontend
pnpm --filter web test -- apps/web/src/features/public-invoice/__tests__/PublicInvoicePage.test.tsx 2>&1 | tail -8
pnpm --filter web test -- apps/web/src/features/public-quote/__tests__/PublicQuotePage.test.tsx 2>&1 | tail -8
pnpm --filter web test -- apps/web/src/__tests__/batch_dlc_b3/ 2>&1 | tail -8
```

> ❌ **BANNED**: `npx vitest run` — bypasses the workspace and breaks module resolution. Only `pnpm --filter web test` is correct.

### Phase 2 — Full verification (once, before sign-off)

```bash
cd <repo>/frontend && echo "=== UI - Type Check ===" && pnpm --filter @pilot/ui check-types && echo "=== Web - Type Check ===" && pnpm --filter web check-types && echo "=== Mobile - Type Check ===" && pnpm --filter mobile build && echo "=== UI - Lint ===" && pnpm --filter @pilot/ui lint && echo "=== Web - Lint ===" && pnpm --filter web lint && echo "=== Mobile - Lint ===" && pnpm --filter mobile lint && echo "=== TYPE+LINT PASS ===" && echo "=== UI - Tests ===" && pnpm --filter @pilot/ui test 2>&1 | tail -6 && echo "=== Web - Tests ===" && pnpm --filter web test 2>&1 | tail -6 && echo "=== Mobile - Tests ===" && pnpm --filter mobile test 2>&1 | tail -8 && echo "=== MVP FINAL VERIFICATION COMPLETE ==="
```

> Any failure in either phase must be fixed before the batch is done. No "pre-existing failure" exception without written confirmation from Tom.

---

## Definition of Done — DLC-B3

- [ ] **BE dependency confirmed**: INV-ROUTE-FIX merged; `pnpm sync-api-types` run; only signed-token public invoice route in `openapi_schema_map.md`
- [ ] Pre-modification regression baseline captured (zero pre-existing failures, or confirmed with Tom)
- [ ] All mandatory source files read before writing code/tests
- [ ] Confirmed no `apiClient` refactor was made to public pages (fetch exception preserved)
- [ ] **STEP 0**: 404 branch added to `PublicInvoicePage` AND `PublicQuotePage` (renders same invalid-link UI as 401; no new testid)
- [ ] **STEP 0B**: SSR 500 resolved — env-var name reconciled (`generateMetadata` vs proxy); page never returns 500 for a bad token; DevOps env-var status noted in Completion Summary
- [ ] **STEP 1**: `PublicInvoicePage.test.tsx` created — 7 cases (410, 410+meta, 401, **404**, 500+retry, network, 200) all pass
- [ ] **STEP 2**: `PublicQuotePage.test.tsx` created — mirrored cases incl. 404 pass
- [ ] **STEP 3**: `batch_dlc_b3/public-invoice-invalid-token.integration.test.tsx` created — 401 + 410 + **404** all render graceful pages, no crash
- [ ] **STEP 4** (optional): 401 copy polished OR skipped — no testid/token changes if done
- [ ] Known-limitation (410 tenant-meta plain-string `detail`) reflected in tests
- [ ] Zero TypeScript errors (`web check-types` passes)
- [ ] Zero ESLint warnings (`web lint` passes)
- [ ] No regressions in pre-existing web suite (baseline count preserved)
- [ ] **Phase 2 FULL verification passes** (`=== MVP FINAL VERIFICATION COMPLETE ===`):
  ```bash
  cd <repo>/frontend && echo "=== UI - Type Check ===" && pnpm --filter @pilot/ui check-types && echo "=== Web - Type Check ===" && pnpm --filter web check-types && echo "=== Mobile - Type Check ===" && pnpm --filter mobile build && echo "=== UI - Lint ===" && pnpm --filter @pilot/ui lint && echo "=== Web - Lint ===" && pnpm --filter web lint && echo "=== Mobile - Lint ===" && pnpm --filter mobile lint && echo "=== TYPE+LINT PASS ===" && echo "=== UI - Tests ===" && pnpm --filter @pilot/ui test 2>&1 | tail -6 && echo "=== Web - Tests ===" && pnpm --filter web test 2>&1 | tail -6 && echo "=== Mobile - Tests ===" && pnpm --filter mobile test 2>&1 | tail -8 && echo "=== MVP FINAL VERIFICATION COMPLETE ==="
  ```
- [ ] Final test count (before → after) documented in the Completion Summary
- [ ] Completion Summary added to `pilot-launch-plan.md` Appendix B
- [ ] Fast-follow checkbox in `telnyx-10dlc-customer-comms-campaign.md` §0 "Post-Submit Fast-Follow" marked ✅

---

## Completion Summary

After all DoD items are complete, add a **Completion Summary** to `pilot-launch-plan.md` Appendix B and mark the campaign-doc fast-follow item ✅, using this format:

```markdown
### DLC-B3 (Frontend) — Public Link Graceful-Error Regression Tests: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot React Engineer
**Baseline**: X passed, Y failed (web)
**Final**: X+N passed, Y failed (+N new tests)

#### What Was Accomplished
- Confirmed FE-B14 already renders graceful 401 (invalid) / 410 (expired) / generic-retry pages on /i/[token] and /q/[token] — no rebuild needed.
- Added first regression coverage for these launch-critical, 10DLC-reviewer-visible error states.
- Locked the exact Telnyx reviewer-click scenario (fake token A1b2C3 → 401 → "Invalid link" page) with an integration test.

#### Files Changed / Created
| File | Action |
|---|---|
| `apps/web/src/features/public-invoice/__tests__/PublicInvoicePage.test.tsx` | Created — 6 error/ready-state cases |
| `apps/web/src/features/public-quote/__tests__/PublicQuotePage.test.tsx` | Created — 6 mirrored cases |
| `apps/web/src/__tests__/batch_dlc_b3/public-invoice-invalid-token.integration.test.tsx` | Created — reviewer-click scenario |

#### Tests Added
| Test File | Type | Tests | All Pass |
|---|---|---|---|
| `PublicInvoicePage.test.tsx` | Unit | 6 | ✅ |
| `PublicQuotePage.test.tsx` | Unit | 6 | ✅ |
| `public-invoice-invalid-token.integration.test.tsx` | Integration | 2 | ✅ |
```
