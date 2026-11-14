# Batch Design: FE-B29 — Full-Page Invoice Builder

**Batch**: FE-B29  
**Type**: Frontend only (React Engineer — `apps/web`)  
**Depends on**: B20 ✅ · UI-DS-B1 ✅  
**Engineer**: Pilot React Engineer  
**Platform**: Web only (`frontend/apps/web/`)  
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-fe-b29-design.md`  
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §Phase 1 — FE-B29 row  
**UI Spec**: `dev-docs/architecture-design/batch-designs/batch-ui-ds-b1-design-spec.md` §Surface 1

---

## A. Input Read Summary

| Input | What Was Read | Key Finding |
|---|---|---|
| `pilot-launch-plan.md` §Phase 1 | FE-B29 scope definition | Full-page invoice builder at `/invoices/new`; depends on B20 + UI-DS-B1 |
| `batch-ui-ds-b1-design-spec.md` §Surface 1 | Invoice builder visual spec | Full-page builder mirroring `QuoteCreatePage.tsx`; 5 sections; billing mode toggle; all tokens defined |
| `batch-b20-design.md` | Backend contracts | `GET /api/v1/jobs/{id}/billable-items`; `payment_terms`, `billing_mode`, `progress_pct`, `internal_memo` added to invoice; `card_required` on customer; all 3 fields added to `InvoiceCreate` |
| MCP: `invoice` table | Live DB | All B20 fields confirmed: `payment_terms`, `billing_mode` (NOT NULL default `line_item`), `progress_pct`, `internal_memo` — migration `f7f30492c3e4` ✅ |
| MCP: `job` table | Live DB | `job_number` (VARCHAR, NOT NULL), `customer_id`, `site_id` confirmed |
| MCP: `job_time_entry` table | Live DB | `hours`, `hourly_rate_cents`, `total_cost_cents`, `started_at`, `ended_at`, `notes`, `user_id` confirmed |
| MCP: `job_expense` table | Live DB | `billable_cents`, `is_billable`, `invoice_line_id` (nullable), `description`, `incurred_at`, `cost_cents` confirmed |
| MCP: `customer` table | Live DB | `card_required` (boolean, NOT NULL, default false) confirmed |
| `openapi_schema_map.md` | Endpoint verification | `GET /api/v1/jobs/{job_id}/billable-items` ✅; `POST /api/v1/invoices/` ✅; both confirmed |
| `useCreateInvoice.ts` | Existing hook | `InvoiceCreatePayload` only has: `quote_id`, `job_id`, `customer_notes`, `terms_and_conditions`, `due_at`, `issued_at`, `idempotency_key` — **missing all B20 fields**: `payment_terms`, `billing_mode`, `progress_pct`, `internal_memo`, `customer_id`, `site_id` |
| `InvoiceCreateModal.tsx` | Existing modal | FE-B24 rework: modal with job/quote dropdowns, due_at, issued_at — **to be deprecated** in favor of full-page builder |
| `InvoicesPage.tsx` | Existing list page | Uses `InvoiceCreateModal` on "+ Create Invoice" button click — **to be changed to navigation** |
| `invoiceDetailHandlers.ts` | Existing MSW | Has `POST /api/v1/invoices/` handler; no billable-items handler — **needs addition** |
| Route: `app/(authed)/invoices/` | Existing route dir | `/invoices/page.tsx` (list), `/invoices/[id]/` (detail) — **no `/invoices/new/` yet** |
| `CustomerCombobox.tsx` + `SiteCombobox.tsx` | FE-B28 components | Both exist in `apps/web/src/components/` — **reuse directly** |

---

## B. No Migrations — Frontend-Only Batch

This batch is purely frontend. All backend schema changes (B20) are complete and live at migration `f7f30492c3e4`.

**Pre-work verification for the React Engineer:**
```bash
# Confirm billable-items endpoint is live
grep -A 5 "billable-items" backend/openapi_schema_map.md

# Confirm B20 invoice fields in openapi.json
python3 -c "
import json
spec = json.load(open('backend/openapi.json'))
invoice_create = spec['components']['schemas']['InvoiceCreate']
print(json.dumps(invoice_create.get('properties', {}), indent=2))
"
```

---

## C. Execution Order

| # | Task | File(s) | Notes |
|---|---|---|---|
| 1 | Create `useBillableItems` hook | `features/invoices/hooks/useBillableItems.ts` | `GET /api/v1/jobs/{job_id}/billable-items`; enabled only when `jobId` is set |
| 2 | Extend `useCreateInvoice` / `InvoiceCreatePayload` | `features/invoices/hooks/useCreateInvoice.ts` | Add B20 fields: `payment_terms`, `billing_mode`, `progress_pct`, `internal_memo`, `customer_id`, `site_id` |
| 3 | Create `InvoiceBuilderPage.tsx` | `features/invoices/components/InvoiceBuilderPage.tsx` | Full-page builder per UI-DS-B1 §Surface 1 |
| 4 | Create route `invoices/new/page.tsx` | `app/(authed)/invoices/new/page.tsx` | Thin server component — `return <InvoiceBuilderPage />;` |
| 5 | Update `InvoicesPage.tsx` — change "+ Create Invoice" button | `features/invoices/components/InvoicesPage.tsx` | `router.push("/invoices/new")` instead of opening modal |
| 6 | Add billable-items MSW handler | `mocks/handlers/invoiceDetailHandlers.ts` | `GET /api/v1/jobs/:job_id/billable-items` |
| 7 | Write integration tests | `__tests__/batch_fe_b29/*.integration.test.tsx` | 4 test files; see §I for minimum count |

---

## D. New API Interactions (Frontend Only)

### D.1 — `useBillableItems(jobId)` — NEW hook

**Endpoint**: `GET /api/v1/jobs/{job_id}/billable-items`  
**Auth**: JWT via `apiClient`  
**Verified**: ✅ confirmed in `openapi_schema_map.md`

```typescript
// features/invoices/hooks/useBillableItems.ts
interface BillableTimeEntry {
  id: string;
  user_id: string;
  tech_name: string | null;
  started_at: string;
  ended_at: string | null;
  hours: string | null;       // Decimal as string from backend
  hourly_rate_cents: number;
  total_cost_cents: number;
  notes: string | null;
  is_already_invoiced: boolean;
}

interface BillableExpense {
  id: string;
  description: string;
  cost_cents: number;
  billable_cents: number;
  is_billable: boolean;
  is_already_invoiced: boolean;
  incurred_at: string;
}

interface BillableItemsResponse {
  job_id: string;
  job_number: string | null;
  customer_name: string | null;
  time_entries: BillableTimeEntry[];
  expenses: BillableExpense[];
}
```

Query key: `["billable-items", jobId]`  
`staleTime`: `60_000`  
`enabled`: `!!jobId`  
`retry: false` (in tests)

### D.2 — `useCreateInvoice` — EXTENDED payload

Add B20 fields to `InvoiceCreatePayload`:

```typescript
// ADDITIONS to existing InvoiceCreatePayload
customer_id?: string | null;       // Required for standalone invoice (no job/quote pre-fill)
site_id?: string | null;           // Required for standalone invoice
payment_terms?: string | null;     // 'due_on_receipt' | 'net_15' | 'net_30' | 'custom_date'
billing_mode?: string;             // 'line_item' | 'progress' (default 'line_item')
progress_pct?: number | null;      // 0–100 when billing_mode='progress'
internal_memo?: string | null;     // Internal note, not on PDF
```

**Note**: `customer_id` and `site_id` are NOT currently in `InvoiceCreatePayload` but ARE required by the backend for standalone (non-job, non-quote) invoices. The B20 backend populates `customer_id`/`site_id` from the linked job/quote when `job_id` or `quote_id` is provided — but the full-page builder must also send them explicitly for standalone creation.

---

## E. Pattern Reuse Decisions

| Pattern | Applied Where | `mvp-arch.md` Reference |
|---|---|---|
| §16.8 Always-Preview-Before-Send | "Send Invoice" in `InvoiceBuilderPage` → triggers existing `SendInvoicePreviewModal` after save | §16.8 — modal confirm before destructive send |
| §16.2 Optimistic UI (checklist) | Line item checkbox toggle updates local state immediately; total recalculated client-side before any API call | §16.2 — UI updates without waiting for network |
| §16.6 Loading/Error/Empty states | `useBillableItems` loading → skeleton rows; error → `<ErrorState>`; empty (no job) → centered empty prompt | `@pilot/ui/states` |
| Reuse `CustomerCombobox` + `SiteCombobox` | Header panel of invoice builder — same components from FE-B28 | `apps/web/src/components/` |
| Reuse `QuoteCreatePage.tsx` layout shell | `InvoiceBuilderPage` mirrors the shell pattern (breadcrumb + action row + section cards + footer) | FE-B19 established pattern |
| §16.5 Two-Tier Config | `square_integration_enabled` flag from `platform_setting` — read via existing settings API; flag-only display (no Square integration in B29 scope) | §16.5 |

---

## F. Shared Module Interfaces

### F.1 — `InvoiceBuilderPage` Props

```typescript
interface InvoiceBuilderPageProps {
  // URL params injected from route (Next.js searchParams)
  jobId?: string | null;      // From ?job_id= — triggers billable items fetch + customer/site pre-fill
  quoteId?: string | null;    // From ?quote_id= — Phase 2.0, not implemented in FE-B29
}
```

**State machine** (page-level):

| State variable | Type | Purpose |
|---|---|---|
| `customerId` | `string \| null` | Selected customer from combobox |
| `siteId` | `string \| null` | Selected site from combobox |
| `billingMode` | `'line_item' \| 'progress'` | Toggle state |
| `progressPct` | `string` | Progress billing % (string for controlled input) |
| `selectedItemIds` | `Set<string>` | IDs of checked line items (time entries + expenses) |
| `customLines` | `CustomLineItem[]` | User-added custom line items |
| `paymentTerms` | `string` | `'due_on_receipt' \| 'net_15' \| 'net_30' \| 'custom_date'` |
| `customDueDate` | `string` | ISO date string — only active when `paymentTerms='custom_date'` |
| `customerNotes` | `string` | Customer-facing note |
| `internalMemo` | `string` | Internal memo |
| `isSaving` | `boolean` | POST in-flight |
| `saveError` | `string \| null` | POST error message |

### F.2 — Custom Line Item Type (local state only, not from API)

```typescript
interface CustomLineItem {
  localId: string;        // client-generated UUID for React key
  description: string;
  unitPriceCents: number;
}
```

Custom lines are built into the `POST /api/v1/invoices/` body as `line_items[]` entries. **Architecture note**: the existing `POST /api/v1/invoices/` accepts line items — verify the exact field shape against `openapi.json` during pre-work.

### F.3 — Computed Invoice Total (client-side, before save)

```typescript
// Pure function — used for display only, no API call
function computeTotal(
  selectedItems: SelectedBillableItem[],
  customLines: CustomLineItem[],
  billingMode: 'line_item' | 'progress',
  progressPct: number,
  totalJobValueCents: number
): number {
  if (billingMode === 'progress') {
    return Math.round(totalJobValueCents * (progressPct / 100));
  }
  const itemsTotal = selectedItems.reduce((sum, item) => sum + item.amountCents, 0);
  const customTotal = customLines.reduce((sum, l) => sum + l.unitPriceCents, 0);
  return itemsTotal + customTotal;
}
```

---

## G. Open Questions Resolved

| Question | Resolution |
|---|---|
| Does the full-page builder **replace** `InvoiceCreateModal` entirely, or run alongside it? | **Navigation replaces modal** — `InvoicesPage.tsx` changes "+ Create Invoice" button to `router.push("/invoices/new")`. `InvoiceCreateModal` is not deleted (it may still be imported in some test files) but is no longer the primary creation path. FE-B29 does not delete it. |
| What happens when `?job_id=` is present — should customer/site be locked (read-only) or editable? | **Pre-filled and editable** — customer/site comboboxes pre-filled from `BillableItemsResponse.customer_name` (display) and the job's `customer_id`/`site_id`, but remain unlocked. This matches the UI-DS-B1 spec: the linked job amber badge is dismissible via `[×]`. |
| Should `customer_id` and `site_id` be required for standalone (no-job) invoices? | **Yes** — both fields required when no `job_id` is passed. Backend `POST /api/v1/invoices/` requires `customer_id` and `site_id`. Client-side validation: block Save/Send if either is null. |
| How does "Save as Draft" vs "Send Invoice" differ? | **Save as Draft** → `POST /api/v1/invoices/` with `status='draft'` (or no status, let backend default) → navigate to `/invoices/{id}`. **Send Invoice** → same POST → then open `SendInvoicePreviewModal` (existing component) if POST succeeds. |
| Preview Invoice button — implement in FE-B29? | **Deferred** — per UI-DS-B1 §Interaction Annotations: "Phase 1.5 detail". In FE-B29, the "Preview Invoice" button in the Action Footer renders a disabled/placeholder state OR is omitted. The design doc explicitly deferred this. Do NOT implement a preview flow in FE-B29. |
| `square_integration_enabled` — does FE-B29 display Square UI? | **Flag-only** — read the `square_integration_enabled` platform setting (via existing `GET /api/v1/settings/platform-settings` endpoint or direct key lookup). If enabled → show a "Card on file required" info badge. No Square SDK integration in FE-B29. |
| Does the `POST /api/v1/invoices/` endpoint accept `line_items[]` for custom lines? | **Must verify** in pre-work. The React Engineer must check `openapi.json` for the `InvoiceCreate` schema during pre-work. If `line_items` is not accepted by the current endpoint, custom lines are a Phase 1.5 feature — implement the UI but disable "Add" functionality with a `// TODO: B29-1 — awaiting invoice line endpoint` comment. |
| Which test folder? | `apps/web/src/__tests__/batch_fe_b29/` — standard batch integration test folder |
| `useBillableItems` — does it also need the `customer_id`/`site_id` from the job to pre-fill comboboxes? | **Yes** — the React Engineer must also call `GET /api/v1/jobs/{id}` via existing `useJob` hook to get the job's `customer_id` and `site_id` for combobox pre-fill. `useBillableItems` only returns customer_name (display), not IDs. Two parallel queries: `useJob(jobId)` + `useBillableItems(jobId)`. |

---

## H. Surface Mockup Reference

| Surface | Spec Location | Platform | Scope in FE-B29 |
|---|---|---|---|
| Invoice Builder `/invoices/new` | UI-DS-B1 §Surface 1 | Web only | ✅ Full implementation |
| Dispatch Board Week View | UI-DS-B1 §Surface 2 | Web only | ❌ FE-B30 only |
| Dispatch Board Month View | UI-DS-B1 §Surface 3 | Web only | ❌ FE-B30 only |
| `JobPropertiesPanel` Save Button | UI-DS-B1 §Surface 4 | Web only | ✅ Already complete — FE-B27 |

**Design token reference** (from UI-DS-B1 §Design Constraints — all confirmed in existing codebase):
- Primary: `bg-brand-500`, `bg-brand-600`, `hover:bg-brand-700`, `text-brand-600`
- Neutral: `bg-neutral-50`, `border-neutral-200`, `text-neutral-700`, `text-neutral-400`
- Amber: `bg-alert-50`, `border-alert-200`, `text-alert-700`
- Success: `bg-margin-50`, `text-margin-600`
- Error: `bg-fault-50`, `border-fault-200`, `text-fault-600`

**§16 patterns consumed by this surface**:
- §16.8 Always-Preview-Before-Send (Send Invoice CTA)
- §16.2 Optimistic UI (line item checkbox totals)
- §16.6 `<LoadingState>` / `<ErrorState>` / `<EmptyState>`

---

## I. Component Manifest

| Component / File | Path | New or Modified | Purpose |
|---|---|---|---|
| `useBillableItems` | `apps/web/src/features/invoices/hooks/useBillableItems.ts` | **New** | TanStack Query hook for `GET /api/v1/jobs/{job_id}/billable-items` |
| `useCreateInvoice` | `apps/web/src/features/invoices/hooks/useCreateInvoice.ts` | **Modified** | Extend `InvoiceCreatePayload` with B20 fields + `customer_id`/`site_id` |
| `InvoiceBuilderPage` | `apps/web/src/features/invoices/components/InvoiceBuilderPage.tsx` | **New** | Full-page invoice builder — all 5 section panels per UI-DS-B1 |
| `invoices/new/page.tsx` | `apps/web/src/app/(authed)/invoices/new/page.tsx` | **New** | Thin server component wrapping `InvoiceBuilderPage` |
| `InvoicesPage` | `apps/web/src/features/invoices/components/InvoicesPage.tsx` | **Modified** | "+ Create Invoice" → `router.push("/invoices/new")` |
| `invoiceDetailHandlers.ts` | `apps/web/src/mocks/handlers/invoiceDetailHandlers.ts` | **Modified** | Add `GET /api/v1/jobs/:job_id/billable-items` MSW handler |
| Integration tests | `apps/web/src/__tests__/batch_fe_b29/` | **New** | 4 test files, minimum 16 tests |

**Integration test files (minimum):**

| Test File | Surface Covered | Min Tests |
|---|---|---|
| `invoice_builder_render.integration.test.tsx` | Page renders, sections visible, RBAC gate | 4 |
| `invoice_builder_job_prefill.integration.test.tsx` | `?job_id=` pre-fills line items, linked job badge shown | 4 |
| `invoice_builder_billing_toggle.integration.test.tsx` | Billing mode toggle switches between checklist/progress views | 4 |
| `invoice_builder_save.integration.test.tsx` | Save as Draft fires POST with correct payload + navigates to detail | 4 |

---

## J. MSW Handler to Add

```typescript
// In invoiceDetailHandlers.ts — add to invoiceDetailHandlers array:

// GET /api/v1/jobs/:job_id/billable-items
http.get("/api/v1/jobs/:job_id/billable-items", ({ params }) => {
  const { job_id } = params as { job_id: string };
  return HttpResponse.json({
    job_id,
    job_number: "JOB-000001",
    customer_name: "Acme Electric",
    time_entries: [
      {
        id: "te-00000001-0000-0000-0000-000000000001",
        user_id: "u-00000001-0000-0000-0000-000000000001",
        tech_name: "Jake Rodriguez",
        started_at: "2026-07-01T08:00:00Z",
        ended_at: "2026-07-01T12:00:00Z",
        hours: "4.00",
        hourly_rate_cents: 8500,
        total_cost_cents: 34000,
        notes: "Panel upgrade labor",
        is_already_invoiced: false,
      },
    ],
    expenses: [
      {
        id: "exp-00000001-0000-0000-0000-000000000001",
        description: "Wire 12AWG 50ft",
        cost_cents: 4800,
        billable_cents: 5280,
        is_billable: true,
        is_already_invoiced: false,
        incurred_at: "2026-07-01T09:30:00Z",
      },
    ],
  });
}),
```

---

*Design doc authored: 2026-07-12 | FE-B29 depends on B20 ✅ + UI-DS-B1 ✅ | FE-B30 follows*
