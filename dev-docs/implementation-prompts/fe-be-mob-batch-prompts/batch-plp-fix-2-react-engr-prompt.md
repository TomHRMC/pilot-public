# Implementation Prompt: PLP-FIX-2 (Part B — Frontend Web) — Dynamic QCO Line Types + Customer-Tab Add Job Modal + Invoice Custom Lines Persistence

**Mode**: Pilot React Engineer
**Batch**: PLP-FIX-2 — Part B (Frontend web) of a mixed batch (runs SECOND per architect-rules §1.3)
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §3.22
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-plp-fix-2-design.md` — read sections A–I in full
**Bug report**: `dev-docs/analysis/PLP-testing-bugs-2026-08-30.md` — Issues 3, 5, and the FE-B29-1 tail of Issue 2
**Estimated session**: 3–4 hours
**Platform**: Web only (`apps/web`)
**Backend companion**: **PLP-FIX-2 Part A (`batch-plp-fix-2-python-engr-prompt.md`) MUST be closed first** — it ships `GET /api/v1/qco-line-types` and regenerates `openapi.json`. If `pnpm sync-api-types` does not deliver `QcoLineTypeResponse`, Part A is not done — **STOP and tell Tom.**

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-react-engineer/react-engineer-rules.md`** — in full
- **`dev-docs/architecture-design/batch-designs/batch-plp-fix-2-design.md`** — every section (A–I)

Critical rules for this batch:

- **Rule 1.1/1.2**: Before writing ANY hook, verify `GET /api/v1/qco-line-types` exists in `backend/openapi_schema_map.md` / `openapi.json`. If it is NOT there → **STOP and ask Tom** (Part A is incomplete).
- **Rule 1.3**: Run `pnpm sync-api-types` FIRST — all payload types (`QcoLineTypeResponse`, `InvoiceLineItemCreate`) come from `@pilot/shared-types`, never hand-written interfaces.
- **Rule 2**: All API calls use `apiClient` from `@pilot/shared-api`. `fetch()` is permanently banned.
- **Rule 10**: If ANY test fails during your work — even one that appears pre-existing — fix it before declaring the batch done.
- **Rule 12 (React Compiler, rules §32)**: Do NOT hand-write `useMemo`/`useCallback`/`React.memo` for render-perf. Keep components pure.
- **Rule 13 (TanStack Query v5, rules §33)**: Object-form `useQuery({ queryKey, queryFn })`; colocated query-key constant; `staleTime` set deliberately (reference data → 1h).
- **Rule 13 (MSW)**: New MSW handlers register in the barrel `index.ts` — this batch extends an EXISTING handler array, so verify the spread is already there instead of adding a duplicate.
- **The Issue-5 lesson (this batch's reason for existing)**: **Never hardcode per-environment seed UUIDs.** Line-type UUIDs differ between dev and prod BY DESIGN; `code` is the only stable key. Any new fixture or default keyed on a hardcoded UUID reintroduces the production 500 this batch fixes.

## Design Decisions (Do Not Re-Litigate)

From Design Doc §G — these decisions are final:

| Decision | Outcome | Rationale |
|---|---|---|
| Line-type source | `useQcoLineTypes()` → `GET /api/v1/qco-line-types` | Endpoint ships in Part A; hardcoded `QCO_LINE_TYPES` / `DEFAULT_LINE_TYPE_ID` consts are **deleted**, not augmented |
| Default line type | `code === "misc"` → else `is_default` row → else first row | Preserves current UI behavior (DB `is_default` flag is `labor`, which serves backend/voice semantics, not the builder default) |
| Dropdown contents | Render **every active type** the API returns (incl. `note`) | Filtering re-encodes a hardcoded list — the anti-pattern being fixed |
| Issue 3 fix shape | Replace the `/jobs/new?customer_id=…` anchor with the **existing `JobFormModal`** + new `prefilledCustomerId` prop | `/jobs/new` does not exist (App Router matched `/jobs/[id]` with `id="new"`); `JobFormModal` is the production-proven create path (JobsPage, QuoteDetailPage) |
| Role gating on "New Job" | Same `RoleGate role={["owner", "office_staff", "operator"]}` JobsPage uses | Hide-not-disable (Rule 6); the customer tab must not offer creates the jobs page hides |
| Invoice custom lines | `line_items: [{ description, quantity: 1, unit_price_cents }]` — **no** `qco_line_type_code` sent | Backend (PLP-FIX-1) defaults `misc` **by code** — environment-safe |
| Issue 4 (Jobs-menu "Network error") | **Out of scope** | Undiagnosed — awaiting Tom's Network-tab capture; separate batch |
| Designer spec (§1.5) | **N/A** | Zero new surfaces; all changes land inside existing approved surfaces (Design §H) |

---

## Pre-Work: Establish Regression Baseline

Before touching any file:

```bash
cd <repo>/frontend
pnpm --filter web test 2>&1 | tail -5
```

Record the exact counts. These must still pass at the end of the batch.

> **If any tests are already failing before you start**: do NOT proceed. Fix them or confirm with Tom first — there is no "pre-existing failure" exception.

## Pre-Work: Sync API Types (FIRST — hard gate)

```bash
cd <repo>/frontend
pnpm sync-api-types
```

Then confirm Part A's schema landed:

```bash
grep -n "QcoLineTypeResponse" packages/shared-types/src/api-schema.d.ts | head -3
grep -n "InvoiceLineItemCreate" packages/shared-types/src/api-schema.d.ts | head -3
```

**`InvoiceLineItemCreate` should already be present (PLP-FIX-1). `QcoLineTypeResponse` is new (Part A). If either is missing → STOP and tell Tom — do not hand-write the interface.**

Consume via the `components` root:

```typescript
import type { components } from "@pilot/shared-types";
type QcoLineTypeResponse = components["schemas"]["QcoLineTypeResponse"];
type InvoiceLineItemCreate = components["schemas"]["InvoiceLineItemCreate"];
```

## Pre-Work: Verify Endpoints

```bash
grep -B2 -A8 "qco-line-types" <repo>/backend/openapi_schema_map.md

cd <repo>/backend
python3 -c "
import json
spec = json.load(open('openapi.json'))
print([p for p in spec['paths'] if 'qco-line-types' in p])
create = spec['components']['schemas']['InvoiceCreate']['properties']
print('line_items' in create)
"
```

Verified endpoints for this batch:

| Hook / call | Endpoint | Verified |
|---|---|---|
| `useQcoLineTypes` | `GET /api/v1/qco-line-types` | ☐ Confirm in openapi_schema_map.md (ships with Part A) |
| `useAddQuoteLine` (existing) | `POST /api/v1/quotes/{quoteId}/lines` | ✅ Already in use |
| `useCreateJob` (existing) | `POST /api/v1/jobs/` | ✅ Already in use |
| `useCreateInvoice` (extend) | `POST /api/v1/invoices/` — `InvoiceCreate.line_items[]` | ✅ Shipped in PLP-FIX-1; confirm `line_items` in schema |

## Pre-Work: Read These Source Files

Read each with `read_file` before writing any code:

| File | Why |
|---|---|
| `frontend/apps/web/src/features/quotes/components/LineItemEditor.tsx` (full, 506 lines) | The Issue-5 site — both `<select>`s (create-flow ~265, edit-flow ~382) and the persisted-row label lookup (~345) render from the const being deleted |
| `frontend/apps/web/src/features/quotes/components/QuoteCreatePage.tsx` lines 30–150 | Imports `DEFAULT_LINE_TYPE_ID` (line 37); per-line POST loop (106–120) |
| `frontend/apps/web/src/features/quotes/hooks/useAddQuoteLine.ts` (full) | Hook style to mirror for `useQcoLineTypes` |
| `frontend/apps/web/src/features/jobs/components/JobFormModal.tsx` (full, 470 lines) | Props interface (27–33), `JobFormContent` state init (50–51), `CustomerCombobox` usage (203–209), shell (430+) |
| `frontend/apps/web/src/features/customers/components/CustomerJobsList.tsx` (full, 403 lines) | Issue-3 site — anchor at 265–272; component receives `customerId` prop (115–119); uses `useJobs({ customer_id })` |
| `frontend/apps/web/src/features/jobs/components/JobsPage.tsx` lines 320–350 + its import block | The exact `RoleGate role={["owner","office_staff","operator"]}` + `JobFormModal` pattern to copy — **copy its `RoleGate` import verbatim** |
| `frontend/apps/web/src/features/jobs/hooks/useCreateJob.ts` (full) | Already invalidates `["jobs"]` — `CustomerJobsList` refreshes automatically on create (no extra invalidation work; verify `JOBS_QUERY_KEY` family starts with `"jobs"` in `useJobs.ts`) |
| `frontend/apps/web/src/features/invoices/hooks/useCreateInvoice.ts` (full) | `InvoiceCreatePayload` (18–33) gets `line_items` |
| `frontend/apps/web/src/features/invoices/components/InvoiceBuilderPage.tsx` lines 42–60, 96–285 | `CustomLineItem` (47–51), `customLines` state (114), `handleAddCustomLine` (257–272), `handleSave` (220–241) |
| `frontend/apps/web/src/mocks/handlers/quoteBuilderHandlers.ts` (full, 197 lines) | `QCO_LINE_TYPE_IDS` (24–29) — extend this file with the new GET handler |
| `frontend/apps/web/src/mocks/handlers/index.ts` (full, 148 lines) | Confirm `...quoteBuilderHandlers` is already spread (line ~106) — extending the array needs **no** barrel edit |
| `frontend/apps/web/src/mocks/handlers/invoiceDetailHandlers.ts` | Confirm the `POST /api/v1/invoices/` handler passes the request body through (needed for the line_items integration assertion) |

Also run:

```bash
# Prove no test file imports the consts being deleted (design-time result: only the 2 component files use them)
grep -rn "QCO_LINE_TYPES\|DEFAULT_LINE_TYPE_ID" <repo>/frontend/apps/web/src --include="*.tsx" --include="*.ts"

# Find existing LineItemEditor / InvoiceBuilder / CustomerJobsList tests to update
find <repo>/frontend/apps/web/src -name "*.test.tsx" | grep -iE "lineitem|quote_create|invoice|customer_job" | head -20
```

---

## Context: What This Batch Does

| # | Change | Files |
|---|---|---|
| 1 | New `useQcoLineTypes` hook + `resolveDefaultLineTypeId` helper + MSW `GET` handler | `hooks/useQcoLineTypes.ts` (new), `quoteBuilderHandlers.ts` |
| 2 | **Issue 5**: `LineItemEditor` renders line types from the API; `QuoteCreatePage` drops the UUID fallback | `LineItemEditor.tsx`, `QuoteCreatePage.tsx` |
| 3 | **Issue 3**: `CustomerJobsList` "New Job" opens `JobFormModal` (new `prefilledCustomerId` prop) instead of routing to a non-existent page | `JobFormModal.tsx`, `CustomerJobsList.tsx` |
| 4 | **FE-B29-1**: invoice custom lines persist via `line_items[]` | `useCreateInvoice.ts`, `InvoiceBuilderPage.tsx` |

## MSW Handlers

**Extend** `frontend/apps/web/src/mocks/handlers/quoteBuilderHandlers.ts` — do not create a new file. Add inside the exported `quoteBuilderHandlers` array, deriving the list from the existing `QCO_LINE_TYPE_IDS` fixture (keeps the fixture the single source of truth — this is what prevents the mock from ever drifting again):

```typescript
  // PLP-FIX-2: GET /api/v1/qco-line-types — line-type lookup consumed by useQcoLineTypes
  http.get("/api/v1/qco-line-types", () =>
    HttpResponse.json([
      { id: QCO_LINE_TYPE_IDS.discount, code: "discount", name: "Discount", is_default: false, is_active: true, is_tenant_override: false },
      { id: QCO_LINE_TYPE_IDS.labor, code: "labor", name: "Labor", is_default: true, is_active: true, is_tenant_override: false },
      { id: QCO_LINE_TYPE_IDS.material, code: "material", name: "Material", is_default: false, is_active: true, is_tenant_override: false },
      { id: QCO_LINE_TYPE_IDS.misc, code: "misc", name: "Misc", is_default: false, is_active: true, is_tenant_override: false },
      { id: "1dd2f395-e703-4247-a57d-08e90e1ffd90", code: "note", name: "Note", is_default: false, is_active: true, is_tenant_override: false },
    ]),
  ),
```

> The fixture UUIDs intentionally stay at the local-dev seed values (MSW mirrors the **local dev DB** — components now resolve types dynamically in tests exactly as in prod). Consider adding `note` to `QCO_LINE_TYPE_IDS` for consistency. **Barrel check**: `mocks/handlers/index.ts` already spreads `...quoteBuilderHandlers` — verify, do not duplicate.

---

## STEP 1 — `useQcoLineTypes` hook

**File (new)**: `frontend/apps/web/src/features/quotes/hooks/useQcoLineTypes.ts`

```typescript
/**
 * useQcoLineTypes — GET /api/v1/qco-line-types
 *
 * PLP-FIX-2: replaces the hardcoded QCO_LINE_TYPES / DEFAULT_LINE_TYPE_ID
 * constants (dev-seed UUIDs) that caused prod Issue 5 (FK violation 500).
 * UUIDs differ per environment BY DESIGN — always resolve from the API;
 * `code` is the only stable cross-environment key.
 */

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";
import type { components } from "@pilot/shared-types";

export type QcoLineType = components["schemas"]["QcoLineTypeResponse"];

export const QCO_LINE_TYPES_QUERY_KEY = ["qco-line-types"] as const;

export function useQcoLineTypes() {
  return useQuery({
    queryKey: QCO_LINE_TYPES_QUERY_KEY,
    queryFn: async (): Promise<QcoLineType[]> => {
      const res = await apiClient.get("/api/v1/qco-line-types");
      return res.data as QcoLineType[];
    },
    staleTime: 60 * 60 * 1000, // reference data — deliberate 1h stale (rules §33)
  });
}

/**
 * Default resolution: code "misc" → is_default row → first row.
 * Preserves the pre-PLP-FIX-2 builder default (misc) without hardcoding a UUID.
 */
export function resolveDefaultLineTypeId(types: QcoLineType[]): string | null {
  if (types.length === 0) return null;
  return (
    types.find((t) => t.code === "misc")?.id ??
    types.find((t) => t.is_default)?.id ??
    types[0]!.id
  );
}
```

## STEP 2 — Issue 5: `LineItemEditor` + `QuoteCreatePage`

**File**: `frontend/apps/web/src/features/quotes/components/LineItemEditor.tsx`

1. **Delete** the `QCO_LINE_TYPES` const (26–39), `DEFAULT_LINE_TYPE_ID` (41), and the stale header comment block (10–15). Keep the exported `LocalLineItem` / `PersistedLineItem` interfaces unchanged.
2. Consume the hook: `const { data: lineTypes, isPending: typesPending, isError: typesError } = useQcoLineTypes();`
3. `emptyLine` takes the default id as a parameter: `function emptyLine(defaultTypeId: string): LocalLineItem`. Compute `const defaultTypeId = resolveDefaultLineTypeId(lineTypes ?? []);` — plain derived value, **no `useMemo`** (React Compiler).
4. Both `<select>`s map over `lineTypes ?? []` (`key={t.id} value={t.id}` → `{t.name}`). The persisted-row label lookup (~345) finds from `lineTypes` and falls back to `"—"`.
5. **Loading/error guards**: while `typesPending`, disable the "Add Line Item" / add-row buttons and show an inline loading hint; if `typesError`, render an inline `<ErrorState>` (from `@pilot/ui`) in place of the editor body — a user must never add a line with no valid type id. `handleAddRow` / `handleStartAddEditRow` no-op when `!defaultTypeId`.
6. Update the file's header docstring to describe the API-driven source.

**File**: `frontend/apps/web/src/features/quotes/components/QuoteCreatePage.tsx`

1. Remove the `import { DEFAULT_LINE_TYPE_ID }` (line 37).
2. In the per-line POST loop (106–120): send `qco_line_type_id: line.qco_line_type_id` directly (no `??` fallback).
3. Add a defensive guard at the top of `handleSave`: if any line has a falsy `qco_line_type_id`, `setSaveError("Line types are still loading — please wait a moment and try again.")` and return `null`. (The editor prevents this state; the guard keeps the contract honest if it ever regresses.)

## STEP 3 — Issue 3: `JobFormModal.prefilledCustomerId` + `CustomerJobsList` modal swap

**File**: `frontend/apps/web/src/features/jobs/components/JobFormModal.tsx`

1. Add `prefilledCustomerId?: string` to `JobFormModalProps` (27–33) with a doc comment (`/** PLP-FIX-2: preselect the customer (e.g. from the customer detail Jobs tab); still editable. */`).
2. Thread it through the shell (430+) into `JobFormContent` exactly as `prefilledQuoteId` is threaded today.
3. In `JobFormContent`: initialize `const [customerId, setCustomerId] = useState(prefilledCustomerId ?? "");`. **No other change** — `SiteCombobox` already cascades from `customerId` (218), and the field stays editable per Design §G.10.

**File**: `frontend/apps/web/src/features/customers/components/CustomerJobsList.tsx`

1. Replace the anchor (265–272) with a `<button type="button">` that opens local modal state (`const [addJobOpen, setAddJobOpen] = useState(false);`). Keep the existing `data-testid="customer-jobs-new-btn"` and visual classes.
2. Wrap the button in the **same** `RoleGate role={["owner", "office_staff", "operator"]}` JobsPage uses — copy JobsPage's exact `RoleGate` import line.
3. Render `<JobFormModal open={addJobOpen} onClose={() => setAddJobOpen(false)} prefilledCustomerId={customerId} />` (import from `../../jobs/components/JobFormModal`). No `onSuccess` needed — `useCreateJob` already invalidates the `["jobs"]` family, which covers this list's `useJobs({ customer_id })` query.
4. Update the header comment line 11 (`"+ New Job" pre-seeded with ?customer_id= query param`) to describe the modal approach.

## STEP 4 — FE-B29-1: invoice custom lines persist

**File**: `frontend/apps/web/src/features/invoices/hooks/useCreateInvoice.ts`

Add to `InvoiceCreatePayload` (after `internal_memo`):

```typescript
  // PLP-FIX-2 / FE-B29-1: custom ad-hoc lines (backend defaults qco_line_type to 'misc' by code)
  line_items?: components["schemas"]["InvoiceLineItemCreate"][] | null;
```

(Add the `import type { components } from "@pilot/shared-types";` line.)

**File**: `frontend/apps/web/src/features/invoices/components/InvoiceBuilderPage.tsx`

In `handleSave` (228–240), add to the `createInvoice({...})` payload:

```typescript
      line_items: customLines.length
        ? customLines.map((cl) => ({
            description: cl.description,
            quantity: 1,
            unit_price_cents: cl.unitPriceCents,
          }))
        : null,
```

Also remove the stale `TODO FE-B29-1` comment near the custom-lines state if present — this batch closes it. Do **not** send `qco_line_type_code` (Design §G — backend resolves `misc` by code, environment-safe).

---

## Test Requirements

### TanStack Query — Required Setup for All Tests

Always `retry: false` on a **fresh** QueryClient per test via a `createWrapper()`; never share instances.

### MSW in Tests — Correct Setup

`setupServer` from `msw/node`; `server.listen({ onUnhandledRequest: "warn" })` in `beforeAll`; **`server.resetHandlers()` in `afterEach`**; `server.close()` in `afterAll`. Never mock `apiClient` directly. Mock `next/navigation` / `next/link` for any component using them.

### Tests to add/update

| # | Test | Location | Type |
|---|---|---|---|
| 1 | `useQcoLineTypes` returns API-shaped data; correct query key; `resolveDefaultLineTypeId` picks `misc` first, falls back to `is_default`, then first row | `features/quotes/hooks/__tests__/useQcoLineTypes.test.ts` | Unit |
| 2 | `LineItemEditor` (create mode): renders one `<option>` per MSW type (incl. Note); new rows default to the `misc` id **from the MSW fixture**; while the endpoint 500s (per-test `server.use` override), the Add button is disabled / error state shows — **proves no hardcoded fallback survives** | `features/quotes/components/__tests__/LineItemEditor.test.tsx` (extend if exists, else create) | Unit |
| 3 | **Issue-5 regression integration**: quote create flow — type dropdown options come from the API; Save Draft POSTs each line with the **MSW-provided** UUID for the selected code (spy on the POST body). This test fails if any hardcoded dev UUID is reintroduced | `apps/web/src/__tests__/batch_plp_fix_2/quote_create_dynamic_line_types.integration.test.tsx` | Integration |
| 4 | **Issue-3 integration**: customer Jobs tab — clicking `customer-jobs-new-btn` opens a `role="dialog"`; customer combobox is preselected with the page's customer; select a site, submit → POST `/api/v1/jobs/` body contains that `customer_id` + `site_id`; tech role does NOT see the button (RoleGate — use the `AuthContext.Provider` pattern from inclusions §9) | `apps/web/src/__tests__/batch_plp_fix_2/customer_jobs_new_job_modal.integration.test.tsx` | Integration |
| 5 | **FE-B29-1 integration**: invoice builder — add a custom line ("Electrical part", $5.00), Save Draft → POST `/api/v1/invoices/` body includes `line_items: [{ description: "Electrical part", quantity: 1, unit_price_cents: 500 }]` and **no** `qco_line_type_code` | `apps/web/src/__tests__/batch_plp_fix_2/invoice_custom_lines_persist.integration.test.tsx` | Integration |
| 6 | Update any existing tests broken by the const deletion / anchor→button swap (run the finds from Pre-Work; known candidates: quote-create, invoice-builder, customer-jobs suites) | existing files | Update |

**Test resilience rules that matter here**: assert option/line identity by code-derived content or MSW fixture IDs, never by total counts; never mutate the shared `QCO_LINE_TYPE_IDS` fixture; integration tests control data via MSW only.

### Modern Stack Standards (rules §32–§36) — applied in these STEPs

- **§32**: `defaultTypeId` and subtotal derivations stay plain — no `useMemo`/`useCallback`.
- **§33**: the new hook uses object-form + the colocated `QCO_LINE_TYPES_QUERY_KEY` + deliberate `staleTime`.
- **§36 (WCAG 2.2 AA)**: the disabled-while-loading state must be perceivable (not color-only); the "New Job" `<button>` keeps ≥24×24px target; the modal already traps focus — verify the prefilled combobox doesn't steal focus from the trap's initial target.

---

## Final Verification

> ❌ **BANNED COMMAND**: `npx vitest run` — NEVER use it. The only correct runner is `pnpm --filter web test` (optionally with `-- <path>`).

### Phase 1 — Targeted tests (run after each task group during development)

```bash
cd <repo>/frontend
pnpm --filter web test 2>&1 | tail -6
pnpm --filter web test -- apps/web/src/__tests__/batch_plp_fix_2/ 2>&1 | tail -10
pnpm --filter web test -- apps/web/src/features/quotes 2>&1 | tail -10
```

Fix any failure before moving on — including failures that appear pre-existing.

### Phase 2 — Full verification (run once at the very end, before DoD sign-off)

```bash
cd <repo>/frontend && echo "=== UI - Type Check ===" && pnpm --filter @pilot/ui check-types && echo "=== Web - Type Check ===" && pnpm --filter web check-types && echo "=== Mobile - Type Check ===" && pnpm --filter mobile build && echo "=== UI - Lint ===" && pnpm --filter @pilot/ui lint && echo "=== Web - Lint ===" && pnpm --filter web lint && echo "=== Mobile - Lint ===" && pnpm --filter mobile lint && echo "=== TYPE+LINT PASS ===" && echo "=== UI - Tests ===" && pnpm --filter @pilot/ui test 2>&1 | tail -6 && echo "=== Web - Tests ===" && pnpm --filter web test 2>&1 | tail -6 && echo "=== Mobile - Tests ===" && pnpm --filter mobile test 2>&1 | tail -8 && echo "=== MVP FINAL VERIFICATION COMPLETE ==="
```

> `pnpm --filter mobile build` IS the mobile type check. Any failure in either phase must be fixed before the batch is declared done. If you cannot identify the root cause → STOP and ask Tom.

---

## Definition of Done — PLP-FIX-2 Part B

Check off each item **in this prompt doc** as it completes:

- [ ] Pre-modification regression baseline captured (zero pre-existing failures, or confirmed with Tom)
- [ ] `pnpm sync-api-types` run — `QcoLineTypeResponse` AND `InvoiceLineItemCreate` present in `api-schema.d.ts` (else STOPPED and told Tom)
- [ ] `GET /api/v1/qco-line-types` verified in `openapi_schema_map.md`
- [ ] Design doc sections A–I read before writing any code
- [ ] All 12 mandatory source files read before modifying
- [ ] **STEP 1**: `useQcoLineTypes.ts` created (hook + `resolveDefaultLineTypeId` + colocated query key + 1h `staleTime`)
- [ ] **STEP 1**: MSW `GET /api/v1/qco-line-types` handler added to `quoteBuilderHandlers.ts`; barrel registration verified (no duplicate)
- [ ] **STEP 2**: `QCO_LINE_TYPES` + `DEFAULT_LINE_TYPE_ID` deleted from `LineItemEditor.tsx`; both selects + persisted-row label render from the hook; loading/error guards in place; `QuoteCreatePage.tsx` fallback removed + defensive guard added
- [ ] Zero remaining references to the deleted consts (`grep` proves it)
- [ ] **STEP 3**: `JobFormModal` accepts `prefilledCustomerId` (editable preselect); `CustomerJobsList` anchor replaced with modal-opening button + `RoleGate` matching JobsPage; header comment updated
- [ ] **STEP 4**: `InvoiceCreatePayload.line_items` added (typed from `@pilot/shared-types`); `handleSave` sends mapped custom lines; stale `TODO FE-B29-1` removed; `qco_line_type_code` NOT sent
- [ ] No hand-written `useMemo`/`useCallback`/`React.memo` for render-perf; components pure (rules §32)
- [ ] New hook uses TanStack Query v5 object-form + colocated key (rules §33)
- [ ] No tenant-data fetching in Server Components (rules §35)
- [ ] WCAG 2.2 AA spot-checks: ≥24px targets, non-color-only disabled state, modal focus intact (rules §36)
- [ ] Tests: hook unit test, editor unit test, 3 integration tests in `__tests__/batch_plp_fix_2/`, existing-suite repairs — all pass (targeted run)
- [ ] No regressions in pre-existing web suite (targeted run confirms)
- [ ] **Phase 2 FULL verification command passes** (`=== MVP FINAL VERIFICATION COMPLETE ===`) — exact command from the Final Verification section
- [ ] Final test count (before → after) documented in the Completion Summary appendix
- [ ] Completion Summary filled in at this prompt doc's ending `## Appendix — Completion Summary` (ADR-0017 — never the launch plan)

---

## Completion Summary

After all Definition of Done items are complete:

1. Fill in the **Completion Summary** in the appendix below using the exact format.
2. This batch closes no task tracked in another source spec — no external spec headers to flip.
3. **Deploy note for Tom in your final message**: the backend (Part A) must already be deployed before this frontend ships — the new hook 404s against a backend without the endpoint.

## Appendix — Completion Summary

### PLP-FIX-2 Part B — Dynamic Line Types + Customer-Tab Add Job + Invoice Custom Lines: Completion Summary

**Completed**: 2026-09-01
**Mode**: Pilot React Engineer
**Baseline**: 2172 passed, 2 flaky (web) — invoice_ui_b1 passes individually; Tom confirmed ignore
**Final**: 2188 passed, 0 failed (+16 new tests)

#### What Was Accomplished

- [Issue 5: quote line types resolved from `GET /api/v1/qco-line-types` — hardcoded dev UUIDs eliminated]
- [Issue 3: customer-tab New Job opens JobFormModal with prefilled customer — broken `/jobs/new` navigation removed]
- [FE-B29-1: invoice custom lines persist via `line_items[]`]

#### Files Changed / Created

| File | Action |
|---|---|
| `frontend/apps/web/src/features/quotes/hooks/useQcoLineTypes.ts` | Created — hook + default resolver |
| `frontend/apps/web/src/features/quotes/components/LineItemEditor.tsx` | Updated — API-driven types; consts deleted |
| `frontend/apps/web/src/features/quotes/components/QuoteCreatePage.tsx` | Updated — fallback removed + guard |
| `frontend/apps/web/src/features/jobs/components/JobFormModal.tsx` | Updated — `prefilledCustomerId` prop |
| `frontend/apps/web/src/features/customers/components/CustomerJobsList.tsx` | Updated — modal swap + RoleGate |
| `frontend/apps/web/src/features/invoices/hooks/useCreateInvoice.ts` | Updated — `line_items` in payload |
| `frontend/apps/web/src/features/invoices/components/InvoiceBuilderPage.tsx` | Updated — custom lines sent + stale TODO removed |
| `frontend/apps/web/src/mocks/handlers/quoteBuilderHandlers.ts` | Updated — line-types GET handler + `note` UUID |

#### Tests Added / Updated

| Test File | Type | Tests | All Pass |
|---|---|---|---|
| `features/quotes/hooks/__tests__/useQcoLineTypes.test.tsx` | Unit | 5 | ✅ |
| `features/quotes/components/__tests__/LineItemEditor.test.tsx` | Unit (updated) | 6 | ✅ |
| `__tests__/batch_plp_fix_2/quote_create_dynamic_line_types.integration.test.tsx` | Integration | 2 | ✅ |
| `__tests__/batch_plp_fix_2/customer_jobs_new_job_modal.integration.test.tsx` | Integration | 4 | ✅ |
| `__tests__/batch_plp_fix_2/invoice_custom_lines_persist.integration.test.tsx` | Integration | 2 | ✅ |
| `features/customers/components/__tests__/CustomerJobsList.test.tsx` | Unit (updated) | 8 | ✅ |
| `__tests__/batch_ui_fix_2d/customer_detail_tabs.integration.test.tsx` | Integration (updated) | 7 | ✅ |
| `__tests__/batch_fe_b19/quoteCreate.integration.test.tsx` | Integration (updated) | 8 | ✅ |

#### Deploy Note for Tom

The backend (Part A) must already be deployed before this frontend ships — the new `useQcoLineTypes` hook 404s against a backend without the `GET /api/v1/qco-line-types` endpoint.
