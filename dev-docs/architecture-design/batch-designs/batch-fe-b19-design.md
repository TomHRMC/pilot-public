# Batch FE-B19 Design — Quote Builder UI

**Batch**: FE-B19 (Frontend — React Engineer only)  
**Date**: June 16, 2026  
**Author**: Pilot Architect  
**Status**: DESIGN COMPLETE — Ready for implementation  
**Reference gap analysis**: `dev-docs/analysis/pilot-app-pre-wkstm-3-mvp-ui-api-gap-analysis.md` §1.1, §1.6, §1.7, §1.14, §4.1  
**Prerequisites**: FE-B18 complete (customer picker used in create flow), B17 Part A complete + `pnpm sync-api-types`

---

## Overview

FE-B19 builds the complete quote creation and editing surface on the web app. The quote approval workflow (`/quotes/[id]` for pending_approval status, `/quotes/pending` inbox) is already built in `features/quote-approval/`. FE-B19 adds:

1. **"New Quote" button** on the `/quotes` list page
2. **Quote Create flow** at `/quotes/new` — full-page builder with customer/site picker, line item editor, expiry, and submission actions
3. **Quote Edit mode** on `/quotes/[id]` when status = `draft` — extends the existing `QuoteDetailPage` to show edit actions
4. **Send to Customer** action — generates public link + fires `always-preview-before-send` modal
5. **Submit for Approval** action — tech role; transitions quote to `pending_approval`
6. **Convert to Job** action — owner role on accepted quotes; calls `POST /api/v1/quotes/{id}/convert`
7. **Quote → Job button** on list page for accepted quotes

No backend changes needed — all endpoints already exist.

---

## A. Input Read Summary

| Input | What was read | Key finding |
|---|---|---|
| PRD §3.10 Sales & Quoting | Full feature list — voice creation, real-time pricing, 3 presentation styles, approval workflow, send, convert | Presentation styles (`clean`/`line_itemed`/`hybrid`) are on `QuoteVersion`, not `Quote` — deferred to B19 scope clarification below |
| `mvp-arch.md` §14, §16.7 | Quote approval architecture; `always-preview-before-send` pattern | Always-preview-before-send is a platform pattern — must be applied to quote send action |
| `features/quote-approval/QuoteDetailPage.tsx` lines 1–80 | Full approval detail page already built; tabs (Details, Changes, Activity); `useApproveWithEdits` hook | **Do not rebuild** — extend with draft-mode edit actions |
| `features/quotes/components/QuotesPage.tsx` | Read-only list; no create button; client-side status filter | Add "New Quote" button + server-side filter after B17 |
| `backend/api/schemas/quotes.py` | `QuoteCreate` (customer_id, site_id, currency, expires_at), `QuoteLineCreate`, `QuoteListItem` (has status_code + customer_name from B17), `QuoteResponse` | `QuoteCreate` has no `presentation_style` — this is on QuoteVersion; confirmed line items need `POST /api/v1/quotes/{id}/lines` |
| Live DB `quote` table | 29 columns confirmed | `discount_pct`, `discount_expires_at`, `expires_at` all present; `submitted_at`, `approved_at` for approval workflow |
| Live DB `quote_line` table | All columns confirmed | `customer_visible`, `parent_line_id`, `is_section_header`, `display_order` — hierarchical structure supported but MVP simplification: flat list only |
| `backend/api/routes/quotes.py` search | `_create_quote_line_impl`, `_convert_quote_impl`, `_create_public_link_impl`, submit-for-approval endpoint confirmed at `POST /{id}/submit-for-approval` | All needed endpoints exist |
| `frontend/apps/web/src/app/(authed)/quotes/[id]/approve/page.tsx` | Exists — approve route for owner | Don't conflict with this |
| `mocks/handlers/index.ts` | `quotesListHandlers` registered; no quote CRUD or line creation handlers | Must add quote builder MSW handlers |

---

## B. Migration Plan

**No Alembic migrations. No backend changes.** FE-B19 is purely frontend.

All required backend endpoints exist:
- `POST /api/v1/quotes/` ✅
- `GET /api/v1/quotes/` (with `?status=`, `status_code`, `customer_name` from B17) ✅
- `GET /api/v1/quotes/{id}` ✅
- `PATCH /api/v1/quotes/{id}` ✅
- `POST /api/v1/quotes/{id}/lines` ✅
- `DELETE /api/v1/quotes/{id}/lines/{line_id}` — verify existence before coding
- `POST /api/v1/quotes/{id}/submit-for-approval` ✅
- `POST /api/v1/quotes/{id}/convert` ✅
- `POST /api/v1/quotes/{id}/public-link` (create shareable link) ✅
- `POST /api/v1/communications/send` (for quote-sent notification) ✅

**Verify before coding** — run pre-work endpoint checks for:
- `DELETE /api/v1/quotes/{id}/lines/{line_id}` — does it exist?
- `PATCH /api/v1/quotes/{id}/lines/{line_id}` — does it exist?
- `GET /api/v1/catalog/pricebook` — what does the pricebook list endpoint look like for the line item picker?
- What does `QuoteConvertResponse` look like? What does it return (job_id?)?

---

## C. Execution Order

| # | Task | Files | Dependency |
|---|---|---|---|
| 1 | Create quote builder MSW handlers | `mocks/handlers/quoteBuilderHandlers.ts`, `mocks/handlers/index.ts` | None — first |
| 2 | Create `useCreateQuote` mutation hook | `features/quotes/hooks/useCreateQuote.ts` | 1 |
| 3 | Create `useQuoteLines` hook + `useAddQuoteLine` + `useDeleteQuoteLine` mutations | `features/quotes/hooks/useQuoteLines.ts`, etc. | 1 |
| 4 | Create `useSubmitForApproval` mutation | `features/quotes/hooks/useSubmitForApproval.ts` | 1 |
| 5 | Create `useGeneratePublicLink` mutation | `features/quotes/hooks/useGeneratePublicLink.ts` | 1 |
| 6 | Create `useConvertQuote` mutation | `features/quotes/hooks/useConvertQuote.ts` | 1 |
| 7 | Create `QuoteCreatePage` + route `/quotes/new` | `features/quotes/components/QuoteCreatePage.tsx`, `app/(authed)/quotes/new/page.tsx` | 2, 3 |
| 8 | Create `LineItemEditor` — the core add/edit/remove line item table component | `features/quotes/components/LineItemEditor.tsx` | 3 |
| 9 | Wire `LineItemEditor` into `QuoteCreatePage` | `features/quotes/components/QuoteCreatePage.tsx` | 7, 8 |
| 10 | Create `SendQuotePreviewModal` (always-preview-before-send pattern) | `features/quotes/components/SendQuotePreviewModal.tsx` | 5 |
| 11 | Add draft-mode edit actions to `QuoteDetailPage` — "Edit", "Add Line", "Send to Customer", "Submit for Approval", "Convert to Job" | `features/quote-approval/QuoteDetailPage.tsx` | 3, 4, 5, 6, 10 |
| 12 | Add "New Quote" button to `QuotesPage` + update `useQuotes` for server-side status filter | `features/quotes/components/QuotesPage.tsx`, `features/quotes/hooks/useQuotes.ts` | 2 |
| 13 | Add "Convert to Job" action on list row for accepted quotes | `features/quotes/components/QuotesPage.tsx` | 6 |
| 14 | Write unit + integration tests | `features/quotes/__tests__/`, `__tests__/batch_fe_b19/` | All above |
| 15 | `pnpm build` + `pnpm test` full verification | — | 14 |

---

## D. API Endpoints Consumed

| Hook | Endpoint | Method | Permission |
|---|---|---|---|
| `useCreateQuote` | `POST /api/v1/quotes/` | POST | `quotes.create` |
| `useQuoteLines` | `GET /api/v1/quotes/{id}/lines` (or from detail) | GET | `quotes.view` |
| `useAddQuoteLine` | `POST /api/v1/quotes/{id}/lines` | POST | `quotes.create` |
| `useDeleteQuoteLine` | `DELETE /api/v1/quotes/{id}/lines/{line_id}` | DELETE | `quotes.edit` |
| `useSubmitForApproval` | `POST /api/v1/quotes/{id}/submit-for-approval` | POST | `quote.submit_for_approval` |
| `useGeneratePublicLink` | `POST /api/v1/quotes/{id}/public-link` | POST | `quotes.edit` |
| `useConvertQuote` | `POST /api/v1/quotes/{id}/convert` | POST | `quotes.edit` |
| `useQuoteDetail` (existing) | `GET /api/v1/quotes/{id}` | GET | `quotes.view` |
| `useQuotes` (extend existing) | `GET /api/v1/quotes/?status=` | GET | `quotes.view` |

**Note**: Line items are returned in `QuoteDetailResponse` (the detail endpoint response) — verify in `openapi_schema_map.md` that lines are nested in the detail response rather than a separate endpoint.

---

## E. Pattern Reuse Decisions

| Pattern | Applied in FE-B19 |
|---|---|
| **`always-preview-before-send`** (mvp-arch §16.7) | `SendQuotePreviewModal` renders rendered message, recipient, channel before `useGeneratePublicLink` fires. User must explicitly confirm. |
| **`<RoleGate>`** | "New Quote" button gated to `quotes.create`; "Submit for Approval" gated to `quote.submit_for_approval`; "Convert to Job" gated to `quotes.edit` (or higher) |
| **`<LoadingState>`, `<ErrorState>`, `<EmptyState>`** | All loading/error/empty states in new components |
| **`apiClient`** | All hooks — never raw `fetch()` |
| **Idempotency key** | `useCreateQuote` generates `crypto.randomUUID()` as `idempotency_key` — mobile offline safety |
| **`retry: false`** on QueryClient in tests | All test wrappers |

---

## F. Shared Module Interfaces

### F.1 `useCreateQuote`

```typescript
// features/quotes/hooks/useCreateQuote.ts
export function useCreateQuote() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: {
      customer_id: string;
      site_id: string;
      currency?: string;
      expires_at?: string | null;
    }): Promise<QuoteResponse> => {
      const idempotency_key = crypto.randomUUID();
      const res = await apiClient.post('/api/v1/quotes/', {
        ...data,
        currency: data.currency ?? 'USD',
        idempotency_key,
      }, {
        headers: { 'Idempotency-Key': idempotency_key },
      });
      return res.data as QuoteResponse;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['quotes'] });
    },
  });
}
```

### F.2 `useAddQuoteLine`

```typescript
// features/quotes/hooks/useAddQuoteLine.ts
export function useAddQuoteLine(quoteId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: {
      description: string;
      quantity: number;
      unit_price_cents: number;
      pricebook_item_id?: string;
      customer_visible?: boolean;
    }) => {
      const res = await apiClient.post(`/api/v1/quotes/${quoteId}/lines`, data);
      return res.data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['quote', quoteId] });
    },
  });
}
```

### F.3 `useSubmitForApproval`

```typescript
// features/quotes/hooks/useSubmitForApproval.ts
export function useSubmitForApproval(quoteId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const res = await apiClient.post(`/api/v1/quotes/${quoteId}/submit-for-approval`);
      return res.data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['quote', quoteId] });
      void queryClient.invalidateQueries({ queryKey: ['quotes'] });
    },
  });
}
```

### F.4 `useGeneratePublicLink`

```typescript
// features/quotes/hooks/useGeneratePublicLink.ts
export function useGeneratePublicLink(quoteId: string) {
  return useMutation({
    mutationFn: async (): Promise<{ public_url: string; token: string }> => {
      const res = await apiClient.post(`/api/v1/quotes/${quoteId}/public-link`);
      return res.data as { public_url: string; token: string };
    },
  });
}
```

### F.5 `useConvertQuote`

```typescript
// features/quotes/hooks/useConvertQuote.ts
export function useConvertQuote(quoteId: string) {
  const queryClient = useQueryClient();
  const router = useRouter();
  return useMutation({
    mutationFn: async (): Promise<{ job_id: string }> => {
      const res = await apiClient.post(`/api/v1/quotes/${quoteId}/convert`);
      return res.data as { job_id: string };
    },
    onSuccess: (data) => {
      void queryClient.invalidateQueries({ queryKey: ['quote', quoteId] });
      void queryClient.invalidateQueries({ queryKey: ['quotes'] });
      // Navigate to the new job once FE-B21 builds the jobs module
      // For now: navigate to /schedule (dispatch board where job will appear)
      router.push('/schedule');
    },
  });
}
```

---

## G. Open Questions Resolved

| Question | Resolution |
|---|---|
| **Quote create: modal or full page?** | Full page at `/quotes/new`. The create flow requires customer picker, site picker, line item editor, and expiry — too much for a modal. |
| **Does `QuoteDetailPage` need full rewrite for edit?** | No. Extend it: when `status === 'draft'`, show action buttons ("Add Line", "Send to Customer", "Submit for Approval") in the existing action bar area. The `QuoteLineItemTable` component already renders lines — add inline "Add Line" row at bottom of the table. |
| **Presentation styles (`clean`/`line_itemed`/`hybrid`) — are they in scope?** | Deferred. `QuoteCreate` has no presentation_style field — it's on `QuoteVersion`. The B17 gap analysis mentioned it; however, adding a QuoteVersion create flow is complex and not core to the "can I create a quote and send it" user story. B19 uses the default presentation (line_itemed) for now. |
| **Line item price lookup — catalog integration?** | Minimal in B19. The `LineItemEditor` supports manual entry (description + quantity + price). Pricebook item picker is a stretch goal: if `GET /api/v1/catalog/pricebook` exists and returns items, add a "Search catalog" button that pre-fills price. If not, manual entry only. Pre-work: check endpoint existence. |
| **Always-preview-before-send: what does the preview show?** | `SendQuotePreviewModal` renders: "You are about to send [Quote ID] to [customer.email]" with the public link URL preview. No full quote render needed — the customer sees the full quote at the public URL. The preview just confirms recipient + channel. |
| **Convert to Job: what does the navigate-after do?** | Navigate to `/schedule` (dispatch board) where the new job will appear. Once FE-B21 builds `/jobs/[id]`, update to navigate there instead. The `QuoteConvertResponse` should return a `job_id` — verify in pre-work. |
| **Update `useQuotes` for server-side status filter?** | Yes. After B17 added `?status=` to the backend, update `useQuotes` to accept a `status` param and remove the client-side `useMemo` filter from `QuotesPage`. |
| **`QuotesPage` — remove "coming soon" comment notes?** | Yes. After B17 Part A adds server-side status + denormalized fields, remove the BE-2/BE-3/BE-4 comments and the client-side filter. |

---

## H. Surface Mockup Reference

**Platform**: Web only (`apps/web`)

### H.1 `/quotes` List Page

```
┌─────────────────────────────────────────────────────────────┐
│  Quotes                               [+ New Quote]         │
│  ─────────────────────────────────────────────────────────  │
│  [All] [Draft] [Pending Approval] [Sent] [Expired]          │
│                                                             │
│  Customer           Status          Total         Actions   │
│  Johnson Elec.      Draft           $2,450        [Edit]    │
│  Smith Residence    Sent            $890                    │
│  Martinez Prop.     Pending Appr.   $5,200        [Review]  │
└─────────────────────────────────────────────────────────────┘
```

- "New Quote" button: `<RoleGate permission="quotes.create">`
- Status filter pills now drive server-side `?status=` param (not client-side useMemo)
- "Edit" action on draft quotes links to `/quotes/[id]` in edit mode
- "Review" action on pending_approval links to `/quotes/[id]/approve` (existing)

### H.2 `/quotes/new` — Quote Create Page

```
┌─────────────────────────────────────────────────────────────┐
│  ← Quotes / New Quote                                       │
│  ─────────────────────────────────────────────────────────  │
│  Customer*  [Search customer...]    Site*  [Site dropdown]  │
│  Expires    [optional date picker]                          │
│  ─────────────────────────────────────────────────────────  │
│  Line Items                                     Subtotal    │
│  ─────────────────────────────────────────────────────────  │
│  Description           Qty   Unit Price   Total             │
│  [Panel upgrade]       [1]   [$1,200]     $1,200  [×]      │
│  [Wire, 12 AWG, 100ft] [100] [$0.85]      $85.00  [×]     │
│  [+ Add Line Item]                                          │
│  ─────────────────────────────────────────────────────────  │
│  Total: $1,285.00                                           │
│                                         [Save Draft] [Send] │
└─────────────────────────────────────────────────────────────┘
```

- Customer picker: searchable dropdown backed by `useCustomers`; once selected, Site picker shows sites for that customer
- "Add Line Item" adds an editable row inline
- "Save Draft": creates quote + all lines via sequential API calls; navigates to `/quotes/[id]`
- "Send": creates quote + lines, then opens `SendQuotePreviewModal` with always-preview-before-send

### H.3 `/quotes/[id]` — Quote Detail with Draft Edit Actions

When status = `draft`, existing `QuoteDetailPage` gains:
- "Add Line" button at bottom of Details tab line item table
- "Edit Line" / "Delete Line" actions on each row (owner/accountant only)
- Action bar: [Submit for Approval] (tech role) | [Send to Customer] (owner role) | [Convert to Job] (only when customer_accepted_at is set)

When status = `pending_approval`: existing approval workflow (unchanged)  
When status = `sent` / `expired` / `converted`: read-only view (no edit actions)

---

## I. Component Manifest

| Component | Path | New or Modify | Notes |
|---|---|---|---|
| `QuoteCreatePage` | `features/quotes/components/QuoteCreatePage.tsx` | **New** | Full-page quote builder; customer/site picker + line item editor + actions |
| `LineItemEditor` | `features/quotes/components/LineItemEditor.tsx` | **New** | Inline table with add/edit/delete rows; used in create page and detail page |
| `SendQuotePreviewModal` | `features/quotes/components/SendQuotePreviewModal.tsx` | **New** | Always-preview-before-send; shows recipient + channel; confirm triggers `useGeneratePublicLink` |
| `QuoteActionBar` | `features/quotes/components/QuoteActionBar.tsx` | **New** | Context-aware action bar — shows different buttons based on status and role |
| `QuotesPage` | `features/quotes/components/QuotesPage.tsx` | **Modify** | Add "New Quote" button; update `useQuotes` to pass `status` param server-side; remove client-side filter; add "Convert to Job" row action for accepted quotes |
| `QuoteDetailPage` | `features/quote-approval/QuoteDetailPage.tsx` | **Modify** | Add draft-mode actions: inline line item editing, `QuoteActionBar` |
| `quotes/new/page.tsx` | `app/(authed)/quotes/new/page.tsx` | **New** | Thin route file: `return <QuoteCreatePage />` |
| `useCreateQuote` | `features/quotes/hooks/useCreateQuote.ts` | **New** | POST mutation with idempotency key |
| `useAddQuoteLine` | `features/quotes/hooks/useAddQuoteLine.ts` | **New** | POST line mutation |
| `useDeleteQuoteLine` | `features/quotes/hooks/useDeleteQuoteLine.ts` | **New** | DELETE line mutation |
| `useSubmitForApproval` | `features/quotes/hooks/useSubmitForApproval.ts` | **New** | POST submit-for-approval |
| `useGeneratePublicLink` | `features/quotes/hooks/useGeneratePublicLink.ts` | **New** | POST public-link |
| `useConvertQuote` | `features/quotes/hooks/useConvertQuote.ts` | **New** | POST convert |
| `useQuotes` | `features/quotes/hooks/useQuotes.ts` | **Modify** | Add `status?: string` param; pass to API; remove client-side filter interim |
| `quoteBuilderHandlers.ts` | `mocks/handlers/quoteBuilderHandlers.ts` | **New** | MSW for quote create, lines CRUD, submit-for-approval, public-link, convert |
| `mocks/handlers/index.ts` | `mocks/handlers/index.ts` | **Modify** | Register `...quoteBuilderHandlers` |
