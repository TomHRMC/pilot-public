# Implementation Prompt: INVOICE-UI-B1 — Invoice Builder Job Pre-Population + URL Fix

**Mode**: Pilot React Engineer
**Batch**: INVOICE-UI-B1
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §2.3 — INVOICE-UI-B1 card
**Design doc**: none — small FE batch; this prompt is self-contained
**Estimated session**: 1–2 hours
**Platform**: Web only (`apps/web`)
**Pure frontend — no backend changes needed**

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-react-engineer/react-engineer-rules.md`** — in full

Critical rules for this batch:

- **Rule 1.1**: Before writing ANY hook or API call, verify the endpoint exists in `backend/openapi_schema_map.md`. This batch uses only the **existing** `useJob` hook (`GET /api/v1/jobs/{id}`) — do not add any new hook.
- **Rule 1.3**: Run `pnpm sync-api-types` before starting — `job.title` was added by **JOB-UI-B1 Part A** (already merged); the enhanced badge reads it, so the generated types must be current.
- **Rule 2**: All API calls use `apiClient` from `@pilot/shared-api`. `fetch()` is permanently banned for `/api/v1/...` calls. (This batch adds no new fetch — noted for the regression test.)
- **Rule 7**: Check `packages/ui/src/index.ts` before creating any new component. **Do NOT create a new "Source Job badge" component — the badge already exists** inline in `InvoiceBuilderPage.tsx` (the "Linked Job Badge" block). This batch *enhances* it, not replaces it.
- **Rule 9**: Route files in `apps/web/src/app/(authed)/` MUST be thin server components — no `"use client"`, no data fetching. `invoices/new/page.tsx` is already correct; do not add logic to it.
- **Rule 10**: If ANY test fails during your work — even one that appears pre-existing — you must fix it before declaring the batch done. If you cannot identify the root cause → STOP and ask Tom.

**Invoice status "overdue" rule** (standing awareness — not central here but do not violate): `invoice_status` has NO "overdue" code; overdue is derived. This batch does not filter invoices, so no action needed — just do not introduce a status filter.

---

## Design Decisions (Do Not Re-Litigate)

| Decision | Outcome | Rationale |
|---|---|---|
| The 404 source | `JobPropertiesPanel.tsx` links to `/invoices/create?job_id=...` | The canonical route is `/invoices/new` (`apps/web/src/app/(authed)/invoices/new/page.tsx`). `/invoices/create` does not exist → hard 404. |
| Fix target | Change the `href` to `/invoices/new?job_id=${job.id}` | The `new` route already reads `searchParams.job_id` and pre-fills the builder. |
| "Source Job badge" | **Enhance the EXISTING "Linked Job Badge"** in `InvoiceBuilderPage.tsx` (~line 358) — do NOT build a new component | The badge already renders `job_number`, amber `alert-*` styling, and a `×` dismiss via `handleDismissJob`. Per UI-DS-B1 §Surface 1 it should also show the job **title** (JOB-UI-B1 added `job.title`) and be a **link** to the source job. |
| Dismiss confirmation | Add a lightweight confirm before clearing the linked job (native `window.confirm` is acceptable — no new dependency) | The card asks for "× dismiss with confirmation." Clearing the job also clears pre-filled customer/site, so a guard prevents accidental data loss. |
| No backend work | This batch is FE-only | `job.title` already ships from JOB-UI-B1 Part A (merged); `useJob` already returns it after `pnpm sync-api-types`. |

These are final. Do NOT change them without asking Tom.

---

## Pre-Work: Establish Regression Baseline

```bash
cd <repo>/frontend
pnpm --filter web test 2>&1 | tail -5
```

Record the exact count. It must still pass at the end.

> **If any tests are already failing before you start**: Do NOT treat them as "pre-existing" and proceed. Either (a) confirm with Tom it is a known accepted failure, OR (b) fix it before touching batch files. (Note: a prior run flagged a pre-existing `invoice_builder_job_prefill` navigation failure during DISPATCH-B3 — if you still see it, it is squarely in this batch's scope; fix it here.)

---

## Pre-Work: Sync API Types

```bash
cd <repo>/frontend
pnpm sync-api-types
```

This regenerates `packages/shared-types/src/api-schema.d.ts`. Confirm `job.title` is present on the Job response type (JOB-UI-B1 Part A added it):

```bash
grep -n "title" packages/shared-types/src/api-schema.d.ts | head -20
```

---

## Pre-Work: Verify Endpoints

This batch adds **no new endpoint**. Confirm the only hook it uses already exists:

```bash
grep -A 3 "jobs/{job_id}\|/jobs/{id}" backend/openapi_schema_map.md | head -20
```

| Hook | Endpoint | Verified |
|---|---|---|
| `useJob` (existing) | `GET /api/v1/jobs/{id}` | ☐ confirm in openapi_schema_map.md |

If it is NOT there → STOP and ask Tom (it should be — JOB-UI-B1 relies on it).

---

## Pre-Work: Read These Source Files

Read each with `read_file` before writing any code:

```
frontend/apps/web/src/features/dispatch-board/components/JobPropertiesPanel.tsx   ← the 404 link at ~line 545–550 ("Create Invoice"); this is fix #1
frontend/apps/web/src/features/invoices/components/InvoiceBuilderPage.tsx          ← the existing "Linked Job Badge" (~line 358) + handleDismissJob + useJob usage (line 133); this is fix #2
frontend/apps/web/src/app/(authed)/invoices/new/page.tsx                          ← confirm it reads searchParams.job_id (do NOT modify)
frontend/apps/web/src/features/jobs/hooks/useJob.ts                               ← confirm JobResponse now has title (added by JOB-UI-B1); how job_number/title are typed
frontend/apps/web/src/mocks/handlers/index.ts                                     ← how MSW handlers are registered (for test wiring)
frontend/apps/web/src/mocks/handlers/jobs.ts                                      ← job fixtures (JOB-UI-B1 added title/priority) — reuse for the badge test
```

Also run:

```bash
grep -rn "invoices/create\|/invoices/new" frontend/apps/web/src --include="*.tsx"
grep -rn "handleDismissJob\|Linked Job" frontend/apps/web/src/features/invoices --include="*.tsx"
```

> **Confirm there is only ONE `/invoices/create` reference** (the `JobPropertiesPanel` one). If grep finds others, fix all of them to `/invoices/new`.

---

## Context: What This Batch Does

| # | Change | File |
|---|---|---|
| 1 | Fix live 404: `/invoices/create?job_id=` → `/invoices/new?job_id=` | `JobPropertiesPanel.tsx` |
| 2 | Enhance existing Linked-Job badge: show `title` (fallback `job_number`), make the label a **link** to `/jobs/{id}`, keep the `×` dismiss | `InvoiceBuilderPage.tsx` |
| 3 | Add confirmation to the `×` dismiss (clears pre-filled customer/site) | `InvoiceBuilderPage.tsx` |
| 4 | Regression test locking the URL fix + badge behavior | `__tests__/batch_invoice_ui_b1/` |

---

## STEP 1 — Fix the 404 link

**File**: `frontend/apps/web/src/features/dispatch-board/components/JobPropertiesPanel.tsx` (~line 546)

Read the file first, then change the `Create Invoice` `<Link href>`:

```tsx
// before
href={`/invoices/create?job_id=${job.id}`}
// after
href={`/invoices/new?job_id=${job.id}`}
```

Leave the styling, label, and surrounding JSX exactly as-is. Fix any other `/invoices/create` occurrences grep found.

Intermediate check:

```bash
pnpm --filter web test -- apps/web/src/features/dispatch-board 2>&1 | tail -10
```

---

## STEP 2 — Enhance the existing Linked-Job badge (title + link)

**File**: `frontend/apps/web/src/features/invoices/components/InvoiceBuilderPage.tsx` (~line 358)

The badge already exists and already calls `useJob(activeJobId ?? "")` (line 133 → `job`, `jobLoading`). Read the current block first, then adjust the label so it prefers `job.title`, falls back to `job.job_number`, then to the id slice, and wrap the label text in a `next/link` to the source job. **Adjust prop/field names to match what you actually find** — this is a starting point, not gospel:

```tsx
{activeJobId && (
  <div>
    <span
      data-testid="invoice-source-job-badge"
      className="inline-flex items-center gap-1.5 bg-alert-50 border border-alert-200 text-alert-700 text-caption font-medium rounded-full px-2.5 py-1 mt-3"
    >
      {jobLoading ? (
        "Loading job…"
      ) : (
        <Link
          href={`/jobs/${activeJobId}`}
          className="hover:underline"
          data-testid="invoice-source-job-link"
        >
          {`Source Job: ${job?.title ?? job?.job_number ?? activeJobId.slice(0, 8)}`}
        </Link>
      )}
      <button
        type="button"
        onClick={handleDismissJob}
        className="hover:text-alert-900 leading-none"
        aria-label="Dismiss linked job"
      >
        ×
      </button>
    </span>
  </div>
)}
```

Notes:
- `Link` is `next/link` — confirm it is already imported in this file (it is used elsewhere or will need importing).
- Keep the amber `alert-*` tokens (matches UI-DS-B1). Do not introduce new design tokens or hardcoded hex/px.
- Do not change `useJob`, `handleDismissJob` signatures beyond STEP 3.

---

## STEP 3 — Add dismiss confirmation

**File**: same — `handleDismissJob` (read the current implementation first; it currently clears `activeJobId` and likely resets pre-filled fields).

Guard the clear with a confirmation, since dismissing also drops the pre-filled customer/site:

```tsx
function handleDismissJob() {
  const ok = window.confirm(
    "Remove the linked job? This clears the pre-filled customer, site, and billable items.",
  );
  if (!ok) return;
  // ...existing clear logic unchanged (setActiveJobId(null), etc.)
}
```

`window.confirm` needs no new dependency. In tests, stub it via `vi.spyOn(window, "confirm")`.

Intermediate check:

```bash
pnpm --filter web test -- apps/web/src/features/invoices 2>&1 | tail -10
```

---

## Test Requirements

### TanStack Query setup
Always create a fresh `QueryClient` per test with `retry: false` on both queries and mutations (see the std-inclusions `createWrapper` pattern). Never share a client across tests.

### MSW
Use `setupServer` from `msw/node`; `beforeAll(listen)`, `afterEach(resetHandlers)`, `afterAll(close)`. Never mock `apiClient` directly. Reuse the existing `jobs.ts` handler fixtures (JOB-UI-B1 added `title`); if you need a job with `title: null` to prove the `job_number` fallback, add a per-test `server.use(...)` override — do not mutate module-level fixtures.

### Next.js mocks
Any component here uses `next/navigation` + `next/link` — mock both in the test:

```typescript
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }), usePathname: () => "/invoices/new" }));
vi.mock("next/link", () => ({ default: ({ href, children, ...rest }: any) => React.createElement("a", { href, ...rest }, children) }));
```

### Integration tests — create `apps/web/src/__tests__/batch_invoice_ui_b1/invoice_ui_b1.integration.test.tsx`

Minimum coverage:

1. **URL fix (the headline)**: render `JobPropertiesPanel` with a job; assert the "Create Invoice" link's `href` is `/invoices/new?job_id={id}` and does **not** contain `/invoices/create`.
2. **Badge title**: render `InvoiceBuilderPage` with `jobId` set + MSW job fixture that has a `title`; assert the badge shows `Source Job: {title}` and the link `href` is `/jobs/{id}`.
3. **Badge fallback**: MSW override so the job has `title: null`; assert the badge falls back to `job_number`.
4. **Dismiss confirm — cancel**: `vi.spyOn(window, "confirm").mockReturnValue(false)`; click `×`; assert the badge is still present (job not cleared).
5. **Dismiss confirm — accept**: `mockReturnValue(true)`; click `×`; assert the badge is removed.
6. **RBAC** (co-located or here): `InvoiceBuilderPage` is wrapped in `<RoleGate permission="invoices.create">`; assert a `tech` role does not see the builder content (use the `AuthContext.Provider` `renderAs` pattern from std-inclusions §9).

> Assert by specific content/`data-testid`/`href` — never by total counts. Reset MSW handlers in `afterEach`.

---

## Final Verification

> ❌ **BANNED COMMAND**: `npx vitest run` — NEVER use this. The ONLY correct runner for `apps/web` is `pnpm --filter web test`.

### Phase 1 — Targeted (during development)

```bash
cd <repo>/frontend
pnpm --filter web test -- apps/web/src/__tests__/batch_invoice_ui_b1/ 2>&1 | tail -10
pnpm --filter web test -- apps/web/src/features/invoices 2>&1 | tail -10
pnpm --filter web test -- apps/web/src/features/dispatch-board 2>&1 | tail -10
```

### Phase 2 — Full canonical verification (run once, before DoD sign-off)

```bash
cd <repo>/frontend && echo "=== UI - Type Check ===" && pnpm --filter @pilot/ui check-types && echo "=== Web - Type Check ===" && pnpm --filter web check-types && echo "=== Mobile - Type Check ===" && pnpm --filter mobile build && echo "=== UI - Lint ===" && pnpm --filter @pilot/ui lint && echo "=== Web - Lint ===" && pnpm --filter web lint && echo "=== Mobile - Lint ===" && pnpm --filter mobile lint && echo "=== TYPE+LINT PASS ===" && echo "=== UI - Tests ===" && pnpm --filter @pilot/ui test 2>&1 | tail -6 && echo "=== Web - Tests ===" && pnpm --filter web test 2>&1 | tail -6 && echo "=== Mobile - Tests ===" && pnpm --filter mobile test 2>&1 | tail -8 && echo "=== MVP FINAL VERIFICATION COMPLETE ==="
```

> Any failure in either phase must be fixed before the batch is declared done. No "pre-existing failure" exception without written confirmation from Tom.

---

## Definition of Done — INVOICE-UI-B1

- [ ] Regression baseline captured (zero pre-existing failures, or the `invoice_builder_job_prefill` failure fixed here)
- [ ] `pnpm sync-api-types` run — `job.title` confirmed on the Job response type
- [ ] All mandatory source files read before modifying
- [ ] `GET /api/v1/jobs/{id}` confirmed in `openapi_schema_map.md`
- [ ] **STEP 1**: `JobPropertiesPanel.tsx` "Create Invoice" link → `/invoices/new?job_id=` (all `/invoices/create` occurrences fixed)
- [ ] **STEP 2**: Linked-Job badge shows `title` (fallback `job_number` → id slice) and links to `/jobs/{id}`; amber `alert-*` tokens preserved; `data-testid="invoice-source-job-badge"`
- [ ] **STEP 3**: `handleDismissJob` guarded by `window.confirm`
- [ ] No new component created (existing badge enhanced); no new npm dependency; no new `fetch()`
- [ ] `invoices/new/page.tsx` unchanged (thin server component)
- [ ] Integration tests in `__tests__/batch_invoice_ui_b1/` — all 6 scenarios pass
- [ ] Zero TypeScript errors; zero ESLint `no-hardcoded-design-values` warnings
- [ ] **Phase 2 FULL verification passes** (`=== MVP FINAL VERIFICATION COMPLETE ===`)
- [ ] Final test count (before → after) documented
- [ ] Completion Summary added to `pilot-launch-plan.md` Appendix B + one-row entry to Appendix A; §2.0 #5 and §2.3 card marked ✅

---

## Completion Summary

After all DoD items are complete:

1. Add a **Completion Summary** subsection to `pilot-launch-plan.md` Appendix B using the format below; add a one-row entry to Appendix A (§A-2).
2. Mark INVOICE-UI-B1 ✅ in §2.0 (#5) and the §2.3 card.

```markdown
### INVOICE-UI-B1 — Invoice Builder Job Pre-Pop + URL Fix: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot React Engineer
**Baseline**: X passed (web)
**Final**: X+N passed (+N new tests)

#### What Was Accomplished
- Fixed live 404: dispatch panel "Create Invoice" → `/invoices/new`
- Enhanced Linked-Job badge with title + source-job link; dismiss confirmation
- [any pre-existing failure fixed]

#### Files Changed / Created
| File | Action |
|---|---|
| `apps/web/src/features/dispatch-board/components/JobPropertiesPanel.tsx` | Updated — 404 link fix |
| `apps/web/src/features/invoices/components/InvoiceBuilderPage.tsx` | Updated — badge title/link + dismiss confirm |
| `apps/web/src/__tests__/batch_invoice_ui_b1/invoice_ui_b1.integration.test.tsx` | Created — N tests |

#### Tests Added
| Test File | Type | Tests | All Pass |
|---|---|---|---|
| `__tests__/batch_invoice_ui_b1/invoice_ui_b1.integration.test.tsx` | Integration | N | ✅ |
```

---

## After This Task — Next Step

INVOICE-UI-B1 clears the last Order-1 leftover. The next FE candidate is **UP-1** (UI polish — WIP dashboard, reminders, sync, templates settings), which needs an Architect design doc first, or **COMMS-UI-B1** (mixed BE+FE — Python first).
