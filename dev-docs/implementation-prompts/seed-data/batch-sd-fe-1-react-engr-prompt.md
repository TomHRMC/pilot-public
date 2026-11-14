# Implementation Prompt: SD-FE-1 — Invoice Filter Status Bug Fix

**Mode**: Pilot React Engineer  
**Batch**: SD-FE-1  
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §P1 Seed Data Batch  
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-sd-design-sprint-design.md` §SD-06  
**Estimated session**: 1–2 hours  
**Platform**: Web only (`apps/web`)  
**Backend companion**: SD-BE-1 must complete first — this batch depends on the `?overdue=true` query parameter being present in `openapi_schema_map.md`

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-react-engineer/react-engineer-rules.md`** — in full
- **`dev-docs/architecture-design/batch-designs/batch-sd-design-sprint-design.md`** — §SD-06 specifically

**Critical rules for this batch:**

- **Rule 1.1**: Before writing ANY hook or API call, verify the `?overdue=true` parameter exists in `backend/openapi_schema_map.md`. If it is NOT there → **STOP**. SD-BE-1 has not completed yet. Do not invent a URL pattern.
- **Rule 1.2**: Do NOT invent URL patterns or parameter names. Every shape comes from `openapi.json` or the design doc.
- **Rule 1.3**: Run `pnpm sync-api-types` before starting — all TypeScript types come from `@pilot/shared-types`.
- **Rule 2**: All API calls use `apiClient` from `@pilot/shared-api`. `fetch()` is permanently banned.
- **Rule 10**: If ANY test fails during your work — fix it before declaring the batch done. No "pre-existing failure" exception.

---

## Design Decisions (Do Not Re-Litigate)

From `batch-sd-design-sprint-design.md` §SD-06 — these decisions are final:

| Decision | Outcome | Rationale |
|:---|:---|:---|
| DB status code for "Sent" invoices | `issued` (not `sent`) | Live DB confirmed: `invoice_status` has `issued`, not `sent` |
| "Overdue" as filter pill | Remove the `overdue` filter pill | "Overdue" is a derived display property, not a DB status code |
| Derived overdue rule | `due_at < NOW() AND status NOT IN ('paid','void','writeoff')` | Frontend derives this; backend supports via `?overdue=true` param |
| `?overdue=true` param | Added to `GET /api/v1/invoices` in SD-BE-1 | Backend filters by the derived rule server-side |

---

## Pre-Work: Establish Regression Baseline

```bash
cd <repo>/frontend
pnpm --filter web test 2>&1 | tail -5
```

Record the exact count. Fix any pre-existing failures or confirm with Tom before starting.

---

## Pre-Work: Sync API Types

```bash
cd <repo>/frontend
pnpm sync-api-types
```

> **Prerequisite check**: If `pnpm sync-api-types` fails because SD-BE-1 hasn't been deployed yet → STOP. The backend must complete first.

---

## Pre-Work: Verify Endpoints

```bash
grep -A 5 "overdue" <repo>/backend/openapi_schema_map.md
```

If `overdue` query parameter does NOT appear on the `GET /api/v1/invoices` endpoint → **STOP. SD-BE-1 is not complete. Do not proceed.**

Verified endpoints for this batch:
| Hook | Endpoint | Verified |
|:---|:---|:---|
| `useInvoices` (with `overdue=true`) | `GET /api/v1/invoices?overdue=true` | Must confirm in openapi_schema_map.md before proceeding |

---

## Pre-Work: Read These Source Files

```
frontend/apps/web/src/features/invoices/components/InvoicesPage.tsx                      ← the file with the bug
frontend/apps/web/src/features/invoices/components/__tests__/InvoicesPage.test.tsx        ← the test with wrong mock data
frontend/apps/web/src/features/invoices/hooks/useInvoices.ts                              ← current hook signature
frontend/apps/web/src/mocks/handlers/index.ts                                             ← understand handler registration
```

Also run:
```bash
find frontend/apps/web/src/features/invoices -name "*.ts" -o -name "*.tsx" | head -20
grep -rn "invoice_status\|status_code\|issued\|sent\|overdue" frontend/apps/web/src/features/invoices/ --include="*.tsx" --include="*.ts"
```

---

## Context: What This Batch Does

**Bug confirmed by Architect** (live grep + MCP):

`InvoicesPage.tsx` line 29–31 contains:
```typescript
{ label: "Sent", value: "sent" },      // ← BUG: "sent" does not exist in invoice_status
{ label: "Overdue", value: "overdue" }, // ← BUG: "overdue" does not exist in invoice_status
```

When a user clicks "Sent", the filter sends `status=sent` to the API — which returns 0 results (silent bug, no error). Same for "Overdue". Both filters are broken.

**What the live `invoice_status` DB codes actually are** (confirmed MCP 2026-07-06):
- `draft`, `issued`, `paid`, `void`, `writeoff`
- There is NO `sent` code — the correct code for sent invoices is `issued`
- There is NO `overdue` code — "overdue" is derived at render time

**This batch has 3 targeted changes:**
1. Fix `InvoicesPage.tsx` filter array: `"sent"` → `"issued"`, remove `"overdue"` pill, add `isOverdue()` derived display logic
2. Fix `InvoicesPage.test.tsx`: `status_code: "sent"` → `status_code: "issued"` in mock data
3. Add or update an MSW handler so the `?overdue=true` param is supported in tests

---

## STEP 1 — Fix `InvoicesPage.tsx`

Read the file fully before editing.

**Change 1**: Fix the status filter array. Find the `STATUS_FILTERS` constant (or equivalent):

```typescript
// BEFORE (broken):
const STATUS_FILTERS = [
  { label: "Draft", value: "draft" },
  { label: "Sent", value: "sent" },        // ← wrong code
  { label: "Paid", value: "paid" },
  { label: "Overdue", value: "overdue" },  // ← not a DB code
] as const;

// AFTER (correct):
const STATUS_FILTERS = [
  { label: "Draft", value: "draft" },
  { label: "Sent", value: "issued" },     // ← correct DB code
  { label: "Paid", value: "paid" },
  { label: "Void", value: "void" },
  { label: "Write-Off", value: "writeoff" },
] as const;
```

> **Note**: Removing `"overdue"` from the status filter pills. Add `"void"` and `"writeoff"` while you're here — they are valid DB codes that were also missing.

**Change 2**: Add an "Overdue" toggle that uses the `?overdue=true` endpoint parameter (not a status code). The implementation depends on how `useInvoices` is structured — read the hook before writing. The toggle should call:
```typescript
// Example — adjust based on actual hook signature
const { data } = useInvoices({ overdue: true });
// OR
const { data } = useInvoices({ status: selectedStatus, overdue: showOverdueOnly });
```

The "Overdue" toggle should be a separate UI element from the status filter pills (e.g., a checkbox labeled "Show overdue only" or a separate pill that appends `?overdue=true` to the filter). Read the existing component layout before deciding the UI pattern — match whatever pattern is already in use for boolean filters.

**Change 3**: Optionally add a derived `isOverdue()` helper for any inline display (e.g., red "Overdue" badge on individual invoice rows):
```typescript
const isOverdue = (invoice: { due_at: string | null; status_code: string }): boolean =>
  invoice.due_at !== null &&
  new Date(invoice.due_at) < new Date() &&
  !["paid", "void", "writeoff"].includes(invoice.status_code);
```

Run targeted test:
```bash
cd <repo>/frontend
pnpm --filter web test -- InvoicesPage 2>&1 | tail -10
```

---

## STEP 2 — Fix `InvoicesPage.test.tsx`

Read the test file fully before editing.

The test mock data uses `status_code: "sent"` — update to `status_code: "issued"`:

```typescript
// BEFORE:
{
  status_id: "st-001",
  status_code: "sent",   // ← wrong
  ...
}

// AFTER:
{
  status_id: "st-001",
  status_code: "issued", // ← correct
  ...
}
```

Search for ALL occurrences:
```bash
grep -n '"sent"' frontend/apps/web/src/features/invoices/components/__tests__/InvoicesPage.test.tsx
```

Fix every instance where `"sent"` is used as an `invoice_status` code. Leave `"sent"` alone for message delivery status (SMS/email send status) — those are in different test files and contexts.

Also update any test that was asserting on the filter behavior — if a test checks that clicking "Sent" fires a request with `status=sent`, update it to `status=issued`.

---

## STEP 3 — Update MSW Handler for `?overdue=true`

Read `frontend/apps/web/src/mocks/handlers/index.ts` before editing.

Find the existing invoice list MSW handler. Add support for the `overdue=true` query parameter:

```typescript
// In the existing invoices GET handler:
http.get("/api/v1/invoices", ({ request }) => {
  const url = new URL(request.url);
  const overdue = url.searchParams.get("overdue") === "true";
  
  if (overdue) {
    // Return only mock invoices that are overdue (past due_at, not paid)
    return HttpResponse.json({
      items: mockInvoices.filter(inv =>
        inv.due_at &&
        new Date(inv.due_at) < new Date() &&
        !["paid", "void", "writeoff"].includes(inv.status_code)
      ),
      total: overdueCount,
    });
  }
  
  // Default: return all mock invoices
  return HttpResponse.json({ items: mockInvoices, total: mockInvoices.length });
}),
```

> **Adjust to match the actual MSW handler structure** — read the existing handler before writing. The response shape must match whatever `useInvoices` expects.

---

## Test Requirements

### Unit tests — `InvoicesPage`

The existing tests in `InvoicesPage.test.tsx` must pass after the mock data fix. Additionally, add:

1. `test_sent_filter_uses_issued_code` — simulate clicking the "Sent" filter button; assert the API call uses `status=issued` (not `status=sent`)
2. `test_overdue_toggle_uses_overdue_param` — simulate clicking the "Overdue" toggle; assert the API call includes `overdue=true`
3. `test_overdue_pill_not_in_status_filter` — assert no filter pill with `value="overdue"` exists in the rendered component

### Test file location: co-located

`frontend/apps/web/src/features/invoices/components/__tests__/InvoicesPage.test.tsx`

Use Vitest (`import { describe, it, expect, vi } from "vitest"`), `@testing-library/react`, `retry: false` QueryClient.

---

## Final Verification

### Phase 1 — Targeted tests

```bash
cd <repo>/frontend
pnpm --filter web test -- InvoicesPage 2>&1 | tail -10
pnpm --filter web test 2>&1 | tail -6
```

Fix any failure — including pre-existing failures — before Phase 2.

### Phase 2 — Full verification

```bash
cd <repo>/frontend && pnpm --filter @pilot/ui check-types && pnpm --filter web check-types && pnpm --filter mobile build && pnpm --filter @pilot/ui lint && pnpm --filter web lint && pnpm --filter mobile lint && echo "=== TYPE+LINT PASS ===" && pnpm --filter @pilot/ui test 2>&1 | tail -6 && pnpm --filter web test 2>&1 | tail -6 && pnpm --filter mobile test 2>&1 | tail -8 && echo "=== SD-FE-1 FINAL VERIFICATION COMPLETE ==="
```

---

## Definition of Done — SD-FE-1

Update `dev-docs/analysis/pilot-launch-plan.md` §P1 Seed Data Batch when each item is done:

- [ ] Pre-modification regression baseline captured (zero pre-existing failures, or confirmed with Tom)
- [ ] `pnpm sync-api-types` run — no new type errors
- [ ] `?overdue=true` parameter confirmed in `backend/openapi_schema_map.md`
- [ ] All mandatory source files read before modifying
- [ ] **STEP 1**: `InvoicesPage.tsx` — `"sent"` → `"issued"` in filter array; `"overdue"` pill removed; `"void"` and `"writeoff"` added; `isOverdue()` helper added; overdue toggle wired to `?overdue=true`
- [ ] **STEP 2**: `InvoicesPage.test.tsx` — all `status_code: "sent"` mock data updated to `status_code: "issued"`; filter assertion tests updated
- [ ] **STEP 3**: MSW handler updated to support `?overdue=true` query parameter
- [ ] No other occurrences of `invoice_status = "sent"` or `invoice_status = "overdue"` remain in web app (check with `grep`)
- [ ] Unit tests for new filter behavior pass
- [ ] Zero TypeScript errors (`pnpm --filter web check-types`)
- [ ] Zero ESLint warnings
- [ ] **Phase 2 FULL verification command passes** (`=== SD-FE-1 FINAL VERIFICATION COMPLETE ===`)
- [ ] Final test count (before → after) documented
- [ ] Completion Summary added

---

## Completion Summary

After all Definition of Done items are complete, add a **Completion Summary** to `dev-docs/analysis/pilot-launch-plan.md` §P1 Seed Data Batch:

```markdown
### SD-FE-1 — Invoice Filter Status Bug Fix: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot React Engineer
**Baseline**: X passed (web)
**Final**: X+N passed (+N new tests)
**Build**: ✅ Pass — TypeScript errors: 0, ESLint warnings: 0

#### What Was Accomplished
- Fixed `InvoicesPage.tsx` status filter: `"sent"` → `"issued"`; `"overdue"` filter pill removed; added `isOverdue()` derived display logic; wired `?overdue=true` endpoint parameter
- Fixed `InvoicesPage.test.tsx` mock data: `status_code: "sent"` → `status_code: "issued"` throughout
- Updated MSW invoice handler to support `?overdue=true` query parameter

#### Files Changed / Created
| File | Action |
|---|---|
| `frontend/apps/web/src/features/invoices/components/InvoicesPage.tsx` | Updated — filter array fixed, overdue toggle added |
| `frontend/apps/web/src/features/invoices/components/__tests__/InvoicesPage.test.tsx` | Updated — mock data fixed, new filter tests added |
| `frontend/apps/web/src/mocks/handlers/[invoiceHandlers].ts` | Updated — `?overdue=true` support added |
```

---

## After This Task — No Downstream Dependency

SD-FE-1 is a standalone fix. No other batches depend on it.
