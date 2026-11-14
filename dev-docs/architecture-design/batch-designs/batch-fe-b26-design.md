# Batch Design: FE-B26 — UUID Display Fixes, Job/Quote Number Display, Profitability Drill-Down, Job-from-Quote CTA

**Batch**: FE-B26  
**Type**: Frontend-only (no backend changes)  
**Depends on**: B19 ✅ (adds `job_number`, `quote_number`, `status_code`, `site_name`, `customer_name` to API responses)  
**Engineer**: Pilot React Engineer  
**Platform**: Web only (`apps/web`)  
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-fe-b26-design.md`  
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §Phase 1 — FE-B26 row  
**Source findings**: `dev-docs/testing-support/alpha-testing/ui-testing-status-2026-07-10-v2.md`

---

## A. Input Read Summary

| Input | What Was Read | Key Finding |
|---|---|---|
| `pilot-launch-plan.md` §Phase 1 | FE-B26 task list | 7 tasks: UUID bugs, profitability drill-down, quote → job CTA, quote number display |
| `ui-testing-status-2026-07-10-v2.md` | Full alpha testing doc | Specific bug reports with file paths + line numbers for each fix |
| `backend/openapi_schema_map.md` (generated 2026-07-11T15:50:15Z) | `JobListItem`, `QuoteListItem`, profitability rows | `job_number`, `quote_number`, `customer_name`, `status_code` confirmed in list responses; profitability rows have `customer_name` |
| `JobDetailHeader.tsx` | Full file (89 lines) | `StatusBadge` uses `statusId` (UUID); breadcrumb shows raw `jobId` from URL; site shows `job.site_id` UUID — all three broken |
| `JobDetailPage.tsx` | Lines 1–120 | Line 80: `isTerminalStatus(job.status_id)` — always false because `TERMINAL_STATUSES` contains status codes not UUIDs |
| `JobsPage.tsx` | Lines 1–112 | Line 101: `href={/jobs/${job.id}?action=convert}` — `?action=convert` param is silently ignored by `JobDetailPage` |
| `QuotesPage.tsx` | Lines 1–120 | UUID slice shown in "Quote ID" column; `q.quote_number` field exists in `QuoteListItem` per B19 |
| `QuoteDetailPage.tsx` | Lines 1–180 | `isAccepted` flag present (line 51); no "Create Job" CTA for accepted quotes |
| `DrillDownPanel.tsx` | Full file (144 lines) | Shows `job.title` in "Job" column — renders `group_label` which is a UUID or aggregated label |
| `useProfitability.ts` | Lines 1–76 | `RawProfitabilityRow` has `group_key`, `group_label` but no `customer_name` or `job_number`; `ClosedJob` interface has no `customer_name` or `job_number` |
| B19 completion summary | Full section in launch plan | Confirms: `status_code`/`site_name`/`customer_name` added to `JobResponse`; `job_number` on `JobListItem`; `customer_name` on profitability rows; `quote_number`/`title` on `QuoteListItem`/`QuoteResponse` |

---

## B. Migration Plan

**No database migrations.** This is a pure frontend batch. All required backend fields were added in B19:
- `job_number` on `JobListItem` and `JobResponse` 
- `status_code`, `site_name`, `customer_name` on `JobResponse`
- `customer_name` on profitability aggregated rows (`ProfitabilityRow`)
- `quote_number`, `title` on `QuoteListItem` and `QuoteResponse`

**Pre-Work Verification**: Before writing any code, the React Engineer must run:
```bash
pnpm sync-api-types
```
This regenerates `packages/shared-types/src/api-schema.d.ts` from the backend OpenAPI spec, confirming all B19 fields are present in the TypeScript types. If `pnpm sync-api-types` does not include these fields, the engineer must STOP and notify Tom — the B19 backend completion may not have been deployed to the running backend.

**MCP verification queries** (for Architect reference — not needed by React Engineer since no schema changes):

```sql
-- Confirm B19 columns are live
SELECT column_name, data_type FROM information_schema.columns 
WHERE table_schema = 'public' AND table_name = 'job' 
AND column_name IN ('job_number') ORDER BY column_name;

SELECT column_name, data_type FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'quote'
AND column_name IN ('quote_number', 'title') ORDER BY column_name;
```

---

## C. Execution Order

| # | Task | File(s) | Notes |
|---|---|---|---|
| 1 | Fix `isTerminalStatus` bug in `JobDetailPage` | `JobDetailPage.tsx` | Change `job.status_id` → `job.status_code`; requires B19 `status_code` on `JobResponse` |
| 2 | Fix `JobDetailHeader` — 3 UUID display bugs | `JobDetailHeader.tsx` | Breadcrumb: `job_number`; Status badge: `status_code`; Site: `site_name`; add customer name + quote link |
| 3 | Fix `JobsPage` "→ Invoice" link | `JobsPage.tsx` | Change `?action=convert` → `/invoices/new?job_id=` |
| 4 | Fix `QuotesPage` quote number display | `QuotesPage.tsx` | Render `q.quote_number` instead of UUID slice |
| 5 | Add "Create Job" CTA to `QuoteDetailPage` | `QuoteDetailPage.tsx`, `JobFormModal.tsx` | Opens `JobFormModal` with `quoteId` pre-wired |
| 6 | Fix `DrillDownPanel` — job number + customer name | `DrillDownPanel.tsx`, `useProfitability.ts` | Add `job_number`/`customer_name` to interfaces + render in table |
| 7 | Write tests | `__tests__/batch_fe_b26/` | Integration tests for each fixed surface |

**Run these in order.** Steps 1–2 are tightly coupled (same `useJob` hook, same `JobResponse` type). Steps 3–4 are independent. Step 5 depends on `JobFormModal` from FE-B24 (already implemented). Step 6 is independent.

---

## D. Component Changes (No New API Endpoints)

All endpoints used in this batch are already live from B19 and prior batches.

### D.1 — `JobDetailHeader.tsx` (fix 3 UUID bugs + add 2 new display elements)

**Endpoint**: `GET /api/v1/jobs/{job_id}` → `JobResponse`  
**B19 additions confirmed**: `status_code`, `site_name`, `customer_name` (per B19 completion summary)  
**Note**: The `openapi_schema_map.md` snapshot at 15:50 UTC shows the old `JobResponse` shape, but B19 completion confirms these fields were added on 2026-07-11. The engineer must verify via `pnpm sync-api-types` before relying on them.

**Current broken state:**
```typescript
// Line 76: shows raw UUID
<span className="text-neutral-900 font-medium">Job {jobId}</span>

// Line 81: StatusBadge receives UUID — colorMap never matches, label garbled
<StatusBadge statusId={job.status_id} />

// Line 85: shows raw site UUID
<span className="text-sm text-neutral-500">Site: {job.site_id}</span>
```

**Required changes:**
1. **Breadcrumb**: `Job {jobId}` → `{job.job_number ?? `Job ${jobId.slice(0, 8)}…`}`
2. **StatusBadge**: Refactor to accept `statusCode: string` (not `statusId`). Use the same `colorMap` and `labelMap` pattern as `JobsPage.tsx` `StatusBadge` (which already uses status codes correctly). Change call site to `<StatusBadge statusCode={job.status_code ?? job.status_id} />`
3. **Site display**: `Site: {job.site_id}` → `{job.site_name ? \`📍 ${job.site_name}\` : null}` — omit if no `site_name`
4. **Customer name**: Add `{job.customer_name && <span className="text-sm font-medium text-neutral-700">{job.customer_name}</span>}` in the header metadata row
5. **Linked quote**: If `job.quote_id` is present, add a clickable link `<Link href={/quotes/${job.quote_id}}>Quote {job.quote_number || "→"}</Link>` — `quote_id` is already on `JobResponse`; `quote_number` would require a separate lookup unless added to `JobResponse`. **Design decision**: Since `JobResponse` does not include `quote_number` (only `quote_id`), render the link as "View Quote →" without a number. Do not fetch a separate `/quotes/{quote_id}` endpoint — the link itself is sufficient. If `job.quote_id` is null/undefined, render nothing.

**After fix — header should show:**
```
Jobs / JOB-000001
[In Progress badge] 📅 Jul 14, 2026   📍 The Smith Home   Acme Electric   View Quote →
```

### D.2 — `JobDetailPage.tsx` line 80 (fix `isTerminalStatus` bug)

**Current broken state:**
```typescript
// Line 80 — TERMINAL_STATUSES contains "completed", "invoice_pending" 
// but job.status_id is a UUID — always returns false
const showConvertButton = job ? isTerminalStatus(job.status_id) : false;
```

**Required change:**
```typescript
// Use status_code (human-readable string) instead of status_id (UUID)
const showConvertButton = job ? isTerminalStatus(job.status_code ?? "") : false;
```

This also requires confirming `TERMINAL_STATUSES` contains the correct codes. Current set:
```typescript
const TERMINAL_STATUSES = new Set([
  "status-completed",      // wrong format — remove
  "status-invoice-pending", // wrong format — remove  
  "status-invoice_pending", // wrong format — remove
  "completed",             // correct ✅
  "invoice_pending",       // correct ✅
]);
```

**Fix `TERMINAL_STATUSES`** to only include the valid status codes that match `status_code` values:
```typescript
const TERMINAL_STATUSES = new Set(["completed", "invoice_pending"]);
```

**Convert to Invoice action**: The "Convert to Invoice" button that fires `useCreateInvoiceFromJob` should be changed to navigate to `/invoices/new?job_id=${jobId}` instead of firing the mutation directly. This aligns with the full-page invoice builder (FE-B29 spec). The `useCreateInvoiceFromJob` hook can remain but the button navigates to the builder page.

> **Design decision**: The "Convert to Invoice" button should navigate to `/invoices/new?job_id={jobId}` rather than directly posting via `useCreateInvoiceFromJob`. This is consistent with the UI-DS-B1 invoice builder spec which defines `/invoices/new?job_id={id}` as the job detail CTA entry point. The `useCreateInvoiceFromJob` hook can be retained for future use but is not the primary path.

### D.3 — `JobsPage.tsx` line 101 (fix broken "→ Invoice" link)

**Current broken state:**
```typescript
// Line 101 — JobDetailPage never reads ?action=convert
href={`/jobs/${job.id}?action=convert`}
```

**Required change:**
```typescript
// Navigate directly to invoice builder pre-populated with this job
href={`/invoices/new?job_id=${job.id}`}
```

Also update the link label from "→ Invoice" to "Create Invoice" to be clearer:
```typescript
<Link
  href={`/invoices/new?job_id=${job.id}`}
  className="text-sm text-brand-600 hover:text-brand-800 font-medium"
>
  Create Invoice
</Link>
```

> **Design decision**: The link goes directly to `/invoices/new?job_id={id}`, bypassing the job detail page. This is the fastest path for an owner who sees a completed job in the list and wants to immediately invoice it. The `JobFormModal` quote pre-population pattern from FE-B24 is the model.

### D.4 — `QuotesPage.tsx` — render `quote_number` instead of UUID

**Current broken state:**
```typescript
// Quotes list "Quote ID" column shows UUID slice: "3f4a…"
// The exact render location in QuotesPage.tsx needs verification (lines 120+)
```

**Required changes:**
1. Change column header from "Quote ID" → "Quote #"
2. Render `q.quote_number` (e.g., `QUO-000001`) instead of `q.id.slice(0, 8) + "…"` or `q.status_id.slice(0, 8) + "…"`
3. Read the actual `QuotesPage.tsx` lines 120–284 to find the exact cell before modifying

The `QuoteListItem` type from `useQuotes` hook already has `quote_number: string` per B19. Confirm this via `pnpm sync-api-types` before writing.

### D.5 — `QuoteDetailPage.tsx` — "Create Job" CTA on accepted quotes

**Current state**: `isAccepted = quote?.status === "accepted"` flag is already computed (line 51) but no CTA is wired to it.

**Required changes**:
1. Import `JobFormModal` from `../../jobs/components/JobFormModal`
2. Add `const [createJobOpen, setCreateJobOpen] = useState(false)` state
3. Add "Create Job" button visible when `isAccepted && isOwner`:
   ```tsx
   {isAccepted && isOwner && (
     <RoleGate permission="jobs.create">
       <button
         type="button"
         onClick={() => setCreateJobOpen(true)}
         className="px-4 py-2 text-sm font-medium text-white bg-brand-600 rounded-md hover:bg-brand-700 transition-colors"
         data-testid="create-job-from-quote-btn"
       >
         Create Job from Quote
       </button>
     </RoleGate>
   )}
   ```
4. Add `<JobFormModal>` below (or alongside existing `<QuoteMetadataEditModal>`):
   ```tsx
   <JobFormModal
     open={createJobOpen}
     onClose={() => setCreateJobOpen(false)}
     prefilledQuoteId={quoteId}
     onSuccess={() => {
       setCreateJobOpen(false);
       router.push("/jobs");
     }}
   />
   ```

**Important**: `JobFormModal` (FE-B24) must accept an optional `prefilledQuoteId?: string` prop that passes `quote_id` in the `POST /api/v1/jobs/` body. Read `JobFormModal.tsx` to see if this prop exists. If it does not exist yet, add it as part of this task.

> **Design decision**: The "Create Job" CTA uses `JobFormModal` (not a new component). `JobFormModal` already sends `quote_id` in the `JobCreate` payload (`quote_id: "Quote Id"` confirmed in `openapi_schema_map.md` line 7327). If `JobFormModal` does not yet accept a `prefilledQuoteId` prop, add it in this batch. Placement: in the quote header action area, alongside the existing "Edit quote details" link (same row for visual balance).

### D.6 — `DrillDownPanel.tsx` + `useProfitability.ts` — job number + customer name columns

**Current state**: 
- `RawProfitabilityRow` (in `useProfitability.ts` lines 31-42): has `group_key`, `group_label` but NO `job_number` or `customer_name`
- `ClosedJob` interface (lines 69-76): has `id`, `title`, `close_date`, `revenue_cents`, `margin_pct`, `margin_bucket` — NO `job_number` or `customer_name`
- `DrillDownPanel.tsx` "Job" column: renders `job.title` (mapped from `group_label`)
- Profitability API **confirmed to return** `customer_name` per `openapi_schema_map.md` lines 14676-14679

**B19 confirmation**: The profitability endpoint (`GET /api/v1/reports/profitability`) now returns `customer_name` in each row. The `group_label` field is now `job_number` (e.g. `JOB-000001`) when `group_by=job`.

**Required changes to `useProfitability.ts`:**
1. Add `customer_name?: string | null` and `job_number?: string | null` to `RawProfitabilityRow`:
   ```typescript
   interface RawProfitabilityRow {
     group_key: string;
     group_label: string;    // now contains job_number (JOB-000001) when group_by=job
     customer_name?: string | null;  // B19 addition
     job_count: number;
     // ... rest unchanged
   }
   ```
2. Add `job_number: string | null` and `customer_name: string | null` to `ClosedJob`:
   ```typescript
   export interface ClosedJob {
     id: string;
     title: string;         // keep for backward compatibility (group_label fallback)
     job_number: string | null;   // B19: from group_label (when group_by=job)
     customer_name: string | null; // B19: from customer_name field
     close_date: string;
     revenue_cents: number;
     margin_pct: number;
     margin_bucket: MarginBucket;
   }
   ```
3. Update `adaptProfitabilityResponse()` closed_jobs mapping to populate these fields from the raw row.

**Required changes to `DrillDownPanel.tsx`:**
1. Rename "Job" column header → "Job #"
2. Render `job.job_number ?? job.title` in the first column (fallback to `title`/`group_label` if `job_number` is null)
3. Add "Customer" column after "Job #", rendering `job.customer_name ?? "—"`

**Updated table structure:**
```
| Job #       | Customer     | Closed  | Revenue   | Margin  |
|-------------|--------------|---------|-----------|---------|
| JOB-000001  | Smith Home   | Jul 1   | $1,350    | 42%     |
| JOB-000002  | Acme Corp    | Jun 28  | $280      | 31%     |
```

---

## E. Pattern Reuse Decisions

| Pattern | Applied Where | Reference |
|---|---|---|
| `StatusBadge` with `statusCode` | Refactored `JobDetailHeader` | Same pattern already used in `JobsPage.tsx` `StatusBadge` |
| Graceful fallback on null B19 fields | All display fields | Use `?? "—"` or `?? fallback_value` to handle null `job_number`, `site_name`, etc. |
| Route pre-fill via URL param | "Create Invoice" link, "Create Job" CTA | `/invoices/new?job_id=` and `JobFormModal` `prefilledQuoteId` prop pattern |
| `JobFormModal` reuse | `QuoteDetailPage` | FE-B24 already built `JobFormModal` — reuse without duplicating |
| `RoleGate permission="jobs.create"` | Create Job CTA | RBAC gate on new button, same as "Add Job" in `JobsPage.tsx` |

---

## F. Shared Module Interfaces

### F.1 — `ClosedJob` interface (extended)

```typescript
// frontend/apps/web/src/features/profitability/hooks/useProfitability.ts
export interface ClosedJob {
  id: string;
  title: string;           // group_label — keep for backward compat
  job_number: string | null;    // B19: human-readable job ID
  customer_name: string | null; // B19: from profitability JOIN
  close_date: string;
  revenue_cents: number;
  margin_pct: number;
  margin_bucket: MarginBucket;
}
```

### F.2 — `JobFormModal` extended prop (if not already present)

```typescript
// frontend/apps/web/src/features/jobs/components/JobFormModal.tsx
interface JobFormModalProps {
  open: boolean;
  onClose: () => void;
  onSuccess?: (job: JobCreateResponse) => void;
  prefilledQuoteId?: string;   // FE-B26: pre-populate quote_id in POST body
}
```

If this prop does not exist yet in `JobFormModal`, add it and wire it into the `useCreateJob` mutation payload.

### F.3 — `JobDetailHeader` type dependencies

The `JobDetailHeader` reads `job` data from `useJob(jobId)`. After B19, `JobResponse` includes `status_code`, `site_name`, `customer_name`. The `useJob` hook type will be updated by `pnpm sync-api-types`. No new hook needed.

---

## G. Open Questions Resolved

| Question | Resolution |
|---|---|
| `JobResponse` `openapi_schema_map.md` shows old shape (no `status_code`, `site_name`) — is B19 complete? | B19 completion summary (2026-07-11) explicitly states these were added. The schema map timestamp (15:50 UTC) may predate B19's final migration. Engineer must run `pnpm sync-api-types` before starting — if fields are absent, STOP and ask Tom. |
| Should "Convert to Invoice" on `JobDetailPage` use the mutation or navigate to `/invoices/new`? | Navigate to `/invoices/new?job_id={jobId}` — aligned with FE-B29 invoice builder spec. The `useCreateInvoiceFromJob` hook is retained but the button changes to a `<Link>`. |
| Should the "Create Job" CTA in `QuoteDetailPage` open a modal or navigate? | Open `JobFormModal` (modal) — consistent with "Add Job" in `JobsPage`. After success, navigate to `/jobs`. No new route needed. |
| `QuoteDetailPage` — does the "Create Job" button need to close the quote loop (status → "converted")? | No. The `useConvertQuote` hook in `QuotesPage.tsx` handles conversion. The new CTA in `QuoteDetailPage` simply creates a job pre-linked to the quote via `quote_id`. Conversion status update is not required here. |
| `DrillDownPanel` — should `group_by=customer` rows also show `customer_name`? | `group_label` in customer mode already IS the customer name. The fix targets only `group_by=job` mode where `group_label` was previously a UUID. The `DrillDownPanel` always shows a "Job #" column — this is renamed from "Job" but the content changes only when actual job number data is populated. In customer group mode, `job_number` will be null and "—" will render. |
| Should the Quotes list show `quote.title` as well as `quote_number`? | No. The `QuotesPage` is a list — `quote_number` in the first column is sufficient. The `title` field is better surfaced on the quote detail page or as a tooltip. Keep the list clean. |

---

## H. Surface Mockup Reference

**Not a UI-DS batch** — no new surfaces are being designed. All changes are bug fixes and data display corrections on existing surfaces. No UI Designer spec required.

| Surface | Change Type | Platform |
|---|---|---|
| `JobDetailHeader` | Data display fix (3 UUID bugs + 2 new fields) | Web only |
| `JobDetailPage` | Logic fix (isTerminalStatus bug) + button navigation change | Web only |
| `JobsPage` | Link destination fix | Web only |
| `QuotesPage` | Column data display fix | Web only |
| `QuoteDetailPage` | New CTA button (Create Job from Quote) | Web only |
| `DrillDownPanel` + `useProfitability` | New columns + interface extension | Web only |

---

## I. Component Manifest

| Component / File | Location | Action | Notes |
|---|---|---|---|
| `JobDetailHeader.tsx` | `apps/web/src/features/jobs/components/JobDetailHeader.tsx` | Modified | Fix 3 UUID bugs; add customer name + quote link display |
| `JobDetailPage.tsx` | `apps/web/src/features/jobs/components/JobDetailPage.tsx` | Modified | Fix `isTerminalStatus(status_id)` → `isTerminalStatus(status_code ?? "")` line 80; update Convert button to navigate |
| `JobsPage.tsx` | `apps/web/src/features/jobs/components/JobsPage.tsx` | Modified | Fix "→ Invoice" link destination; update label |
| `QuotesPage.tsx` | `apps/web/src/features/quotes/components/QuotesPage.tsx` | Modified | Render `quote_number` not UUID slice; rename column header |
| `QuoteDetailPage.tsx` | `apps/web/src/features/quote-approval/QuoteDetailPage.tsx` | Modified | Add "Create Job from Quote" CTA + `JobFormModal` wiring |
| `JobFormModal.tsx` | `apps/web/src/features/jobs/components/JobFormModal.tsx` | Modified (if needed) | Add `prefilledQuoteId?: string` prop if not already present |
| `useProfitability.ts` | `apps/web/src/features/profitability/hooks/useProfitability.ts` | Modified | Extend `RawProfitabilityRow` + `ClosedJob` interfaces; update adapter |
| `DrillDownPanel.tsx` | `apps/web/src/features/profitability/components/DrillDownPanel.tsx` | Modified | Rename "Job" → "Job #"; add "Customer" column; render `job_number` + `customer_name` |
| `__tests__/batch_fe_b26/*.integration.test.tsx` | `apps/web/src/__tests__/batch_fe_b26/` | Created | Integration tests per surface |

---

## Key Risk: B19 `JobResponse` field availability

The `openapi_schema_map.md` generated at 15:50 UTC 2026-07-11 shows `JobResponse` (single job detail, `GET /api/v1/jobs/{job_id}`) without the B19-added fields (`status_code`, `site_name`, `customer_name`, `job_number`). The B19 completion summary says these were added. This discrepancy is likely due to the schema map being generated before B19's Python changes were committed.

**Engineering gate**: The React Engineer must run `pnpm sync-api-types` FIRST. If `JobResponse` in `@pilot/shared-types` does NOT include these fields, the engineer must STOP and raise this with Tom before implementing steps 1–2. Steps 3–6 (which depend only on `JobListItem`, `QuoteListItem`, and profitability rows) can proceed independently.

---

*Design doc authored: 2026-07-11 | FE-B26 depends on B19 ✅ | No new backend required*
