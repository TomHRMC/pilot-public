# Batch FE-B21 Design — Jobs Web Module

**Batch**: FE-B21 (Frontend — React Engineer only)  
**Date**: June 16, 2026  
**Author**: Pilot Architect  
**Status**: DESIGN COMPLETE — Ready for implementation  
**Reference gap analysis**: `dev-docs/analysis/pilot-app-pre-wkstm-3-mvp-ui-api-gap-analysis.md` §1.2, §4.2  
**Prerequisites**: FE-B19 complete (quote → job conversion exists), B17 Part A complete + `pnpm sync-api-types`

---

## Overview

FE-B21 builds the complete web-side Jobs module. Currently there is no `/jobs` route on web at all. This batch delivers:

1. **Jobs list** at `/jobs` — filterable by status, searchable by customer
2. **Job detail** at `/jobs/[id]` — header, profitability section, tabbed sub-sections
3. **Time entries tab** — list with add form (manual clock-in/out for web owners)
4. **Expenses tab** — list with add form
5. **Change orders tab** — list with add/edit/delete
6. **Notes tab** — single textarea, save on blur
7. **Profitability widget** — live margin display from projected-margin endpoint
8. **"Convert to Invoice" button** — on completed jobs, calls `POST /api/v1/invoices/`
9. **Jobs link from dispatch board** — wire existing dispatch board job card click → `/jobs/[id]`
10. **"Add Jobs" nav item** — "Jobs" to `AppSidebar`

All backend endpoints are fully built and confirmed.

---

## A. Input Read Summary

| Input | What was read | Key finding |
|---|---|---|
| PRD §3.4 Field Operations & Jobs | Complete feature list | Web shows live profitability, time entries, expenses, change orders, LOTO, photos, notes |
| `backend/api/routes/jobs.py` (endpoints search) | All 42 route decorators confirmed | Full CRUD for: jobs, time-entries, expenses, change-orders, notes, loto-confirmations, projected-margin |
| `backend/api/schemas/schemas.py` lines 144–273 | `JobCreate`, `JobResponse`, `JobListItem`, `JobTimeEntryCreate/Response`, `JobExpenseCreate/Response`, `ChangeOrderCreate/Update/Response` | `JobResponse` has `actual_labor_cost_cents`, `actual_material_cost_cents`, `actual_profit_cents` — live profitability fields |
| Live DB `job` table | 20 columns confirmed | Has `actual_labor_cost_cents`, `actual_material_cost_cents`, `actual_profit_cents`, `version` |
| `backend/api/routes/photos.py` | Photo upload pipeline | `POST /api/v1/photos/initiate-upload` + `POST /api/v1/photos/complete-upload` — multipart S3 flow; deferred in FE-B21 (complex) |
| Gap analysis §1.2 | No `/jobs` route exists at all on web | Must add "Jobs" to `AppSidebar` and create all routes |
| `features/dispatch-board/components/DispatchBoardPage.tsx` | `onJobSelect` callback exists but navigates nowhere | Wire to `/jobs/[id]` |
| `mocks/handlers/jobs.ts` | Already exists | Review before creating new handlers — extend rather than replace |

---

## B. Migration Plan

**No Alembic migrations. No backend changes.** FE-B21 is purely frontend.

All required endpoints confirmed:

| Endpoint | Description |
|---|---|
| `GET /api/v1/jobs/` | List jobs (has `status_code`, `customer_name` denormalized) |
| `POST /api/v1/jobs/` | Create job |
| `GET /api/v1/jobs/{id}` | Get job detail |
| `GET /api/v1/jobs/{id}/time-entries` | List time entries |
| `POST /api/v1/jobs/{id}/time-entries` | Add time entry |
| `GET /api/v1/jobs/{id}/expenses` | List expenses |
| `POST /api/v1/jobs/{id}/expenses` | Add expense |
| `GET /api/v1/jobs/{id}/notes` | Get notes |
| `PUT /api/v1/jobs/{id}/notes` | Update notes |
| `GET /api/v1/jobs/{id}/change-orders` | List change orders |
| `POST /api/v1/jobs/{id}/change-orders` | Create change order |
| `PATCH /api/v1/jobs/{id}/change-orders/{co_id}` | Update change order |
| `DELETE /api/v1/jobs/{id}/change-orders/{co_id}` | Delete change order |
| `GET /api/v1/jobs/{id}/projected-margin` | Live profitability |
| `POST /api/v1/invoices/` | Create invoice from job (pre-work: verify `job_id` param accepted) |

**Deferred in FE-B21** (too complex for this batch):
- Photo upload (`initiate-upload` → S3 multipart → `complete-upload`) — deferred to FE-B22 or MOB-B6 companion
- LOTO confirmation display — show count only from `GET /api/v1/jobs/{id}/loto-confirmations` (read-only on web)
- Job status transitions — changing job status is owner action via dispatch board; list shows status badge only

**Pre-work verification needed:**
- Does `POST /api/v1/invoices/` accept `job_id`? Check `InvoiceCreate` schema.
- Does `GET /api/v1/jobs/` support `?customer_id=` filter? (From FE-B18 pre-work — confirm result here too.)
- What does `GET /api/v1/jobs/{id}/projected-margin` return? Check response schema.

---

## C. Execution Order

| # | Task | Files | Dependency |
|---|---|---|---|
| 1 | Extend existing `mocks/handlers/jobs.ts` with new endpoints | `mocks/handlers/jobs.ts`, verify not replaced | None |
| 2 | Create `useJobs` hook (list) + `useJob` (single) hooks | `features/jobs/hooks/useJobs.ts`, `useJob.ts` | 1 |
| 3 | Create `useJobTimeEntries` + `useAddTimeEntry` | `features/jobs/hooks/useJobTimeEntries.ts` | 1 |
| 4 | Create `useJobExpenses` + `useAddExpense` | `features/jobs/hooks/useJobExpenses.ts` | 1 |
| 5 | Create `useJobChangeOrders` + mutations | `features/jobs/hooks/useJobChangeOrders.ts` | 1 |
| 6 | Create `useJobNotes` + `useUpdateJobNotes` | `features/jobs/hooks/useJobNotes.ts` | 1 |
| 7 | Create `useProjectedMargin` | `features/jobs/hooks/useProjectedMargin.ts` | 1 |
| 8 | Create `useCreateInvoiceFromJob` mutation | `features/jobs/hooks/useCreateInvoiceFromJob.ts` | 1 |
| 9 | Create `JobsPage` (list with status filter + search) | `features/jobs/components/JobsPage.tsx` | 2 |
| 10 | Create `JobDetailHeader` (job ID, status badge, customer, site, dates) | `features/jobs/components/JobDetailHeader.tsx` | 2 |
| 11 | Create `JobProfitabilityWidget` (actuals + ETC + projected margin) | `features/jobs/components/JobProfitabilityWidget.tsx` | 7 |
| 12 | Create `JobTimeEntriesTab` (list + add form) | `features/jobs/components/JobTimeEntriesTab.tsx` | 3 |
| 13 | Create `JobExpensesTab` (list + add form) | `features/jobs/components/JobExpensesTab.tsx` | 4 |
| 14 | Create `JobChangeOrdersTab` (list + add/edit/delete) | `features/jobs/components/JobChangeOrdersTab.tsx` | 5 |
| 15 | Create `JobNotesTab` (textarea + autosave) | `features/jobs/components/JobNotesTab.tsx` | 6 |
| 16 | Create `JobDetailPage` (tabs + profitability + convert-to-invoice) | `features/jobs/components/JobDetailPage.tsx` | 10–15, 8 |
| 17 | Create route files: `/jobs/page.tsx` + `/jobs/[id]/page.tsx` | Route files | 9, 16 |
| 18 | Add "Jobs" to `AppSidebar` | `components/AppSidebar.tsx` | None |
| 19 | Wire dispatch board job card click → `/jobs/[id]` | `features/dispatch-board/components/DispatchBoardPage.tsx` (or `JobBlock.tsx`) | None |
| 20 | Write unit + integration tests | `__tests__/batch_fe_b21/` | All |
| 21 | Full verification | — | 20 |

---

## D. API Endpoints Consumed

| Hook | Endpoint | Method |
|---|---|---|
| `useJobs` | `GET /api/v1/jobs/?status={}&customer_id={}` | GET |
| `useJob` | `GET /api/v1/jobs/{id}` | GET |
| `useJobTimeEntries` | `GET /api/v1/jobs/{id}/time-entries` | GET |
| `useAddTimeEntry` | `POST /api/v1/jobs/{id}/time-entries` | POST |
| `useJobExpenses` | `GET /api/v1/jobs/{id}/expenses` | GET |
| `useAddExpense` | `POST /api/v1/jobs/{id}/expenses` | POST |
| `useJobChangeOrders` | `GET /api/v1/jobs/{id}/change-orders` | GET |
| `useCreateChangeOrder` | `POST /api/v1/jobs/{id}/change-orders` | POST |
| `useUpdateChangeOrder` | `PATCH /api/v1/jobs/{id}/change-orders/{co_id}` | PATCH |
| `useDeleteChangeOrder` | `DELETE /api/v1/jobs/{id}/change-orders/{co_id}` | DELETE |
| `useJobNotes` | `GET /api/v1/jobs/{id}/notes` | GET |
| `useUpdateJobNotes` | `PUT /api/v1/jobs/{id}/notes` | PUT |
| `useProjectedMargin` | `GET /api/v1/jobs/{id}/projected-margin` | GET |
| `useCreateInvoiceFromJob` | `POST /api/v1/invoices/` (with `job_id`) | POST |

---

## E. Pattern Reuse Decisions

| Pattern | Applied in FE-B21 |
|---|---|
| `<LoadingState>`, `<ErrorState>`, `<EmptyState>` | All list tabs and the job detail page |
| `<RoleGate>` | "Add Time Entry" / "Add Expense" / "Add Change Order" gated to `jobs.edit`; "Convert to Invoice" gated to `invoices.create` |
| `apiClient` | All hooks |
| `retry: false` | All test QueryClient wrappers |

---

## F. Shared Module Interfaces

### F.1 `useJobs`

```typescript
// features/jobs/hooks/useJobs.ts
// Query key: ['jobs', status, customerId]
// GET /api/v1/jobs/?status={}&customer_id={}
// Returns: JobListItem[] (has status_code + customer_name)
// staleTime: 30_000
```

### F.2 `useJob`

```typescript
// features/jobs/hooks/useJob.ts
// Query key: ['job', jobId]
// GET /api/v1/jobs/{jobId}
// Returns: JobResponse (has actual_labor/material/profit_cents)
// enabled: !!jobId
```

### F.3 `useProjectedMargin`

```typescript
// features/jobs/hooks/useProjectedMargin.ts
// Query key: ['job-projected-margin', jobId]
// GET /api/v1/jobs/{jobId}/projected-margin
// Returns: { projected_total_cost_cents, projected_margin_pct, etc }  — verify exact shape
// enabled: !!jobId
```

### F.4 `useCreateInvoiceFromJob`

```typescript
// features/jobs/hooks/useCreateInvoiceFromJob.ts
// POST /api/v1/invoices/ with { job_id: jobId }
// Returns: InvoiceResponse (with invoice_id for navigation)
// onSuccess: navigate to /invoices/{invoice_id}
// Required RBAC: invoices.create
```

---

## G. Open Questions Resolved

| Question | Resolution |
|---|---|
| **Does `POST /api/v1/invoices/` accept `job_id`?** | Verify in pre-work. If yes: `useCreateInvoiceFromJob` fires directly. If InvoiceCreate requires more fields (customer_id, site_id): pull those from the job object before calling. |
| **When does "Convert to Invoice" appear?** | When `job.status_code` is in `['completed', 'invoice_pending']` (or similar terminal states — verify against `job_status` table). The button is hidden for in-progress or cancelled jobs. Also hidden if job already has an invoice (verify if there's an `invoice_id` on job response). |
| **`JobDetailPage` — tabbed layout or scrollable sections?** | Tabbed layout. Five tabs: Profitability / Time Entries / Expenses / Change Orders / Notes. The profitability widget always shows above the tab bar as a persistent summary. |
| **Should notes autosave or require a Save button?** | Save on blur (textarea blur triggers `PUT /api/v1/jobs/{id}/notes`). This avoids accidental saves of partial text. Show "Saving..." spinner during save; "Saved" confirmation on success. |
| **Add Time Entry form — what fields?** | `started_at` (date + time), `ended_at` (date + time), `hours` (optional, auto-calculated from start/end), `notes` (optional). On web, owners add manual entries for reference — the tech's actual clock-in/out comes from mobile. |
| **Photo section?** | Show read-only photo grid from `job_attachment` records. Display thumbnails with S3 signed URLs. No upload on web in FE-B21. "Upload" button shown as deferred state. |
| **Wire dispatch board job card click to `/jobs/[id]`?** | Yes. Read `DispatchBoardPage.tsx` — it has an `onJobSelect(jobId)` prop that goes nowhere. Change the handler to `router.push('/jobs/${jobId}')`. |
| **Should `/customers/[id]/jobs` tab now show real data?** | Yes — FE-B18 built that tab as a deferred state. After FE-B21 adds `useJobs` with `?customer_id=` filter, update `CustomerJobsList` component to use it (if that endpoint supports the filter — confirm in pre-work). |

---

## H. Surface Mockup Reference

**Platform**: Web only (`apps/web`)

### H.1 `/jobs` — Jobs List

```
┌─────────────────────────────────────────────────────────────┐
│  Jobs                                                       │
│  [All] [Draft] [Scheduled] [In Progress] [Completed]        │
│  [Search by customer...]                                    │
│  ─────────────────────────────────────────────────────────  │
│  Customer          Status       Scheduled        Actions    │
│  Johnson Elec.     In Progress  Jun 16 9am        [View]   │
│  Smith Residence   Scheduled    Jun 17 2pm         [View]  │
│  Martinez Prop.    Completed    Jun 14              [View] [→Invoice]│
└─────────────────────────────────────────────────────────────┘
```

### H.2 `/jobs/[id]` — Job Detail

```
┌─────────────────────────────────────────────────────────────┐
│  Jobs / Johnson Panel Upgrade                               │
│  Status: In Progress  •  Johnson Electrical  •  Jun 16      │
│  ─────────────────────────────────────────────────────────  │
│  PROFITABILITY                                              │
│  Labor: $360 / Est. $480  Material: $200 / Est. $300       │
│  Projected Margin: 24.5%  ✅ Above 20% target              │
│  ─────────────────────────────────────────────────────────  │
│  [Profitability] [Time Entries] [Expenses] [Change Orders] [Notes] │
│  ─────────────────────────────────────────────────────────  │
│  [Tab content]                                              │
│                                          [Convert to Invoice]│
└─────────────────────────────────────────────────────────────┘
```

---

## I. Component Manifest

| Component | Path | New or Modify | Notes |
|---|---|---|---|
| `JobsPage` | `features/jobs/components/JobsPage.tsx` | **New** | List with status filter pills + customer search |
| `JobDetailHeader` | `features/jobs/components/JobDetailHeader.tsx` | **New** | Job ID, status badge, customer name, site, scheduled dates |
| `JobProfitabilityWidget` | `features/jobs/components/JobProfitabilityWidget.tsx` | **New** | Actuals vs estimate, projected margin badge |
| `JobTimeEntriesTab` | `features/jobs/components/JobTimeEntriesTab.tsx` | **New** | List + AddTimeEntryForm |
| `AddTimeEntryForm` | `features/jobs/components/AddTimeEntryForm.tsx` | **New** | start/end datetime + hours + notes |
| `JobExpensesTab` | `features/jobs/components/JobExpensesTab.tsx` | **New** | List + AddExpenseForm |
| `AddExpenseForm` | `features/jobs/components/AddExpenseForm.tsx` | **New** | category + description + cost + vendor |
| `JobChangeOrdersTab` | `features/jobs/components/JobChangeOrdersTab.tsx` | **New** | List + add/edit/delete change orders |
| `JobNotesTab` | `features/jobs/components/JobNotesTab.tsx` | **New** | Textarea with save-on-blur |
| `JobDetailPage` | `features/jobs/components/JobDetailPage.tsx` | **New** | Tab layout + profitability + convert-to-invoice |
| `useJobs` | `features/jobs/hooks/useJobs.ts` | **New** | List hook |
| `useJob` | `features/jobs/hooks/useJob.ts` | **New** | Single job hook |
| `useJobTimeEntries` | `features/jobs/hooks/useJobTimeEntries.ts` | **New** | |
| `useAddTimeEntry` | `features/jobs/hooks/useAddTimeEntry.ts` | **New** | |
| `useJobExpenses` | `features/jobs/hooks/useJobExpenses.ts` | **New** | |
| `useAddExpense` | `features/jobs/hooks/useAddExpense.ts` | **New** | |
| `useJobChangeOrders` | `features/jobs/hooks/useJobChangeOrders.ts` | **New** | |
| `useCreateChangeOrder` | `features/jobs/hooks/useCreateChangeOrder.ts` | **New** | |
| `useUpdateChangeOrder` | `features/jobs/hooks/useUpdateChangeOrder.ts` | **New** | |
| `useDeleteChangeOrder` | `features/jobs/hooks/useDeleteChangeOrder.ts` | **New** | |
| `useJobNotes` | `features/jobs/hooks/useJobNotes.ts` | **New** | |
| `useUpdateJobNotes` | `features/jobs/hooks/useUpdateJobNotes.ts` | **New** | |
| `useProjectedMargin` | `features/jobs/hooks/useProjectedMargin.ts` | **New** | |
| `useCreateInvoiceFromJob` | `features/jobs/hooks/useCreateInvoiceFromJob.ts` | **New** | |
| `jobs/page.tsx` | `app/(authed)/jobs/page.tsx` | **New** | Thin route: `return <JobsPage />` |
| `jobs/[id]/page.tsx` | `app/(authed)/jobs/[id]/page.tsx` | **New** | Thin route: `return <JobDetailPage jobId={id} />` |
| `AppSidebar.tsx` | `components/AppSidebar.tsx` | **Modify** | Add "Jobs" nav item |
| `DispatchBoardPage.tsx` | `features/dispatch-board/components/DispatchBoardPage.tsx` | **Modify** | Wire `onJobSelect` → `router.push('/jobs/${jobId}')` |
| `CustomerJobsList.tsx` | `features/customers/components/CustomerJobsList.tsx` | **Modify** | Replace deferred state with real data if `?customer_id=` supported |
| `mocks/handlers/jobs.ts` | `mocks/handlers/jobs.ts` | **Extend** | Add handlers for time-entries, expenses, change-orders, notes, projected-margin |
