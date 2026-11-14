# Implementation Prompt: FE-B19 — Quote Builder UI

**Mode**: Pilot React Engineer  
**Batch**: FE-B19  
**Source plan**: `dev-docs/analysis/pilot-app-pre-wkstm-3-prep-plan.md` §Phase 0.9 — FE-B19  
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-fe-b19-design.md`  
**Estimated session**: 5–7 hours  
**Platform**: Web only (`apps/web`)  
**Backend companion**: None — all endpoints exist. Prerequisites: FE-B18 complete (customer picker), B17 Part A complete + `pnpm sync-api-types`.

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-react-engineer/react-engineer-rules.md`** — in full
- **`dev-docs/architecture-design/batch-designs/batch-fe-b19-design.md`** — every section (A–I)

**Critical rules for this batch:**

- **Rule 1.1**: Before writing ANY hook, verify the endpoint in `backend/openapi_schema_map.md`. The quote line DELETE/PATCH endpoints may not exist — check before coding.
- **Rule 1.2**: Field names for `QuoteLineCreate` come from `openapi.json` — do not invent them.
- **Rule 1.3**: Run `pnpm sync-api-types` first — types must be current.
- **Rule 2**: All API calls use `apiClient`. `fetch()` is permanently banned.
- **Rule 7**: Check `packages/ui/src/index.ts` before creating any new component.
- **Rule 8**: No new npm packages without checking `package.json` first. Use native `<dialog>` element or existing modal pattern for modals.
- **Rule 9**: Route files in `app/(authed)/` are thin server components — no `"use client"`, no data fetching.
- **Rule 10**: If ANY test fails — even pre-existing — fix it before declaring done.
- **Always-preview-before-send is non-negotiable**: The `SendQuotePreviewModal` MUST render before the public link is generated and before any communication is sent. There is no path that skips the preview. This is a platform pattern enforced at the product level.

---

## Design Decisions (Do Not Re-Litigate)

From Design Doc §G:

| Decision | Outcome | Rationale |
|---|---|---|
| Create flow | Full page at `/quotes/new` (not modal) | Too much content (customer picker + site + lines + expiry) for a modal |
| Edit flow | Extend existing `QuoteDetailPage` for draft status | Already built; adds actions contextually on status |
| Presentation styles | Deferred — default `line_itemed` only | `QuoteCreate` has no presentation_style field; QuoteVersion management is complex |
| Pricebook picker | Stretch goal — manual entry is core | Check if `GET /api/v1/catalog/pricebook` exists; add picker only if it does |
| Post-convert navigation | Navigate to `/schedule` | `/jobs/[id]` not built yet; FE-B21 will update |
| Always-preview-before-send | `SendQuotePreviewModal` required on all send paths | Platform pattern — never bypass |

---

## Pre-Work: Establish Regression Baseline

Before touching any file:

```bash
cd <repo>/frontend
pnpm --filter web test 2>&1 | tail -5
pnpm --filter @pilot/ui test 2>&1 | tail -5
```

Record exact counts. Fix any pre-existing failures before starting.

---

## Pre-Work: Sync API Types

```bash
cd <repo>/frontend
pnpm sync-api-types
```

---

## Pre-Work: Verify Endpoints

Run ALL of these before writing any hook code:

```bash
# 1. Check quote line CRUD endpoints
python3 -c "
import json
spec = json.load(open('backend/openapi.json'))
line_paths = [p for p in spec['paths'] if 'quotes' in p and 'lines' in p]
for p in line_paths:
    methods = list(spec['paths'][p].keys())
    print(p, '->', methods)
"

# 2. Check submit-for-approval
grep -A 3 "submit-for-approval" backend/openapi_schema_map.md | head -10

# 3. Check public-link creation
grep -A 3 "public-link" backend/openapi_schema_map.md | head -15

# 4. Check convert endpoint and response schema
python3 -c "
import json
spec = json.load(open('backend/openapi.json'))
convert = spec['paths'].get('/api/v1/quotes/{quote_id}/convert', {})
print('Convert methods:', list(convert.keys()))
if 'post' in convert:
    resp = convert['post'].get('responses', {}).get('200', {})
    print('Convert response:', resp.get('content', {}).get('application/json', {}).get('schema', {}).get('\$ref', 'see inline'))
"

# 5. Check QuoteLineCreate schema field names
python3 -c "
import json
spec = json.load(open('backend/openapi.json'))
schema = spec.get('components', {}).get('schemas', {}).get('QuoteLineCreate', {})
print('QuoteLineCreate fields:', list(schema.get('properties', {}).keys()))
"

# 6. Check if pricebook endpoint exists (stretch goal)
python3 -c "
import json
spec = json.load(open('backend/openapi.json'))
pb_paths = [p for p in spec['paths'] if 'pricebook' in p or 'catalog' in p.lower()]
print('Catalog/pricebook paths:', pb_paths)
"
```

**Decision based on results:**
- If quote line DELETE/PATCH exist: build full edit/delete in `LineItemEditor`
- If only line POST exists: build add-only; no inline edit/delete yet
- If pricebook endpoint exists: add optional catalog search in `LineItemEditor`
- If convert returns `job_id`: navigate after convert; if not, navigate to `/schedule`

| Hook | Endpoint | Verified |
|---|---|---|
| `useCreateQuote` | `POST /api/v1/quotes/` | Confirm before coding |
| `useAddQuoteLine` | `POST /api/v1/quotes/{id}/lines` | Confirm before coding |
| `useDeleteQuoteLine` | `DELETE /api/v1/quotes/{id}/lines/{line_id}` | Confirm exists or skip |
| `useSubmitForApproval` | `POST /api/v1/quotes/{id}/submit-for-approval` | Confirm before coding |
| `useGeneratePublicLink` | `POST /api/v1/quotes/{id}/public-link` | Confirm before coding |
| `useConvertQuote` | `POST /api/v1/quotes/{id}/convert` | Confirm + check response shape |

---

## Pre-Work: Read These Source Files

Read each before writing any code:

```
frontend/apps/web/src/features/quotes/components/QuotesPage.tsx
  ← understand current state before adding button + server-side filter

frontend/apps/web/src/features/quotes/hooks/useQuotes.ts
  ← understand existing hook before modifying for server-side status

frontend/apps/web/src/features/quote-approval/QuoteDetailPage.tsx
  ← understand existing approval workflow before extending for draft actions

frontend/apps/web/src/features/quote-approval/components/ (list files first)
  ← understand available components before building new ones

frontend/apps/web/src/app/(authed)/quotes/[id]/page.tsx
  ← understand current route before modifying

frontend/apps/web/src/mocks/handlers/quotesListHandlers.ts
  ← understand existing quotes mock data before adding builder handlers

frontend/apps/web/src/mocks/handlers/index.ts
  ← understand barrel before adding new handler file

frontend/packages/ui/src/index.ts
  ← confirm component imports before use
```

Also run:
```bash
# List all existing quote-approval components
find frontend/apps/web/src/features/quote-approval -type f | sort

# Find any existing modal/dialog patterns
find frontend/apps/web/src/features -name "*Modal*" | head -10

# Check permissions for quotes
grep -n '"quotes' frontend/packages/ui/src/role-gate/permissions.ts | head -20
grep -n '"quote\.' frontend/packages/ui/src/role-gate/permissions.ts | head -20
```

---

## Step 1 — Create Quote Builder MSW Handlers

**File**: `apps/web/src/mocks/handlers/quoteBuilderHandlers.ts` (new)

Read `quotesListHandlers.ts` first to understand the fixture style. Create handlers for:

```typescript
import { http, HttpResponse } from "msw";

// POST /api/v1/quotes/ — create new quote (returns QuoteResponse)
// POST /api/v1/quotes/:quoteId/lines — add line item
// DELETE /api/v1/quotes/:quoteId/lines/:lineId — delete line (if endpoint exists)
// POST /api/v1/quotes/:quoteId/submit-for-approval
// POST /api/v1/quotes/:quoteId/public-link — returns { public_url, token }
// POST /api/v1/quotes/:quoteId/convert — returns { job_id: "..." }
```

Use fixture IDs consistent with `quotesListHandlers.ts` so list and detail views work together.

> **Test resilience**: Fixture objects are read-only — never mutate them. Mock POST handlers return the input merged with generated IDs; they do NOT mutate shared fixture arrays.

**Register in barrel:**
```typescript
// mocks/handlers/index.ts
import { quoteBuilderHandlers } from "./quoteBuilderHandlers";  // ADD

export const handlers = [
  // ... existing handlers ...
  ...quoteBuilderHandlers,  // ADD — FE-B19
];
```

**Intermediate check:**
```bash
pnpm --filter web test 2>&1 | tail -5
```

---

## Step 2–6 — Create New Hooks

**Files**: `apps/web/src/features/quotes/hooks/`

Read `useQuotes.ts` first. Follow exact same pattern for all new hooks.

All hooks must:
- Use `apiClient` (never `fetch()`)
- Return types from `@pilot/shared-types` after `pnpm sync-api-types`
- Use `retry: false` in test wrappers

### `useCreateQuote.ts`

```typescript
// Endpoint: POST /api/v1/quotes/
// Must generate idempotency key: const key = crypto.randomUUID()
// Pass both in body AND as header: { 'Idempotency-Key': key }
// onSuccess: invalidate ['quotes'] queries
```

### `useAddQuoteLine.ts`

```typescript
// Endpoint: POST /api/v1/quotes/{quoteId}/lines
// Field names come from QuoteLineCreate schema (verified in pre-work)
// onSuccess: invalidate ['quote', quoteId]
```

### `useDeleteQuoteLine.ts` (only if endpoint confirmed in pre-work)

```typescript
// Endpoint: DELETE /api/v1/quotes/{quoteId}/lines/{lineId}
// onSuccess: invalidate ['quote', quoteId]
// If endpoint does NOT exist: skip this hook; LineItemEditor will be add-only
```

### `useSubmitForApproval.ts`

```typescript
// Endpoint: POST /api/v1/quotes/{quoteId}/submit-for-approval
// onSuccess: invalidate ['quote', quoteId] + ['quotes']
```

### `useGeneratePublicLink.ts`

```typescript
// Endpoint: POST /api/v1/quotes/{quoteId}/public-link
// Returns: { public_url: string, token: string }
// NOT called from a TanStack Query queryFn — this is a useMutation
// Called from SendQuotePreviewModal ONLY after user clicks "Confirm Send"
```

### `useConvertQuote.ts`

```typescript
// Endpoint: POST /api/v1/quotes/{quoteId}/convert
// Check pre-work for response shape — probably { job_id: string }
// onSuccess: invalidate ['quote', quoteId] + ['quotes'] + navigate to /schedule
```

**Intermediate check:**
```bash
pnpm --filter web test -- --testPathPattern="useCreateQuote|useAddLine|useSubmit|usePublicLink|useConvert" 2>&1 | tail -8
```

---

## Step 7 — Create `QuoteCreatePage` and Route

**Files**:
- `apps/web/src/features/quotes/components/QuoteCreatePage.tsx` (new)
- `apps/web/src/app/(authed)/quotes/new/page.tsx` (new)

### Route file (thin server component):
```typescript
// app/(authed)/quotes/new/page.tsx
import { QuoteCreatePage } from "@/features/quotes/components/QuoteCreatePage";

export default function NewQuotePage() {
  return <QuoteCreatePage />;
}

export const metadata = { title: "New Quote | Pilot" };
```

### `QuoteCreatePage.tsx`

```typescript
"use client";
// State:
// - selectedCustomerId: string | null
// - selectedSiteId: string | null
// - expiresAt: Date | null
// - lines: Array<{ description, quantity, unit_price_cents }> (local state before creating quote)
// - isCreating: boolean

// Customer picker: uses useCustomers({ search }) — searchable dropdown
// Site picker: uses useCustomerSites(selectedCustomerId) — only shown after customer selected
// Line item editor: <LineItemEditor> (built in Step 8)
// 
// "Save Draft" button:
//   1. Call useCreateQuote({ customer_id, site_id, expires_at })
//   2. On success (quoteId returned): sequentially call useAddQuoteLine for each line
//   3. Navigate to /quotes/[quoteId]
//
// "Send" button:
//   1. Same as Save Draft but after all lines added, open SendQuotePreviewModal
//
// RoleGate: entire page behind quotes.create permission
```

> Read the file before coding — adjust to match what you actually find. The above is a starting point.

---

## Step 8 — Create `LineItemEditor`

**File**: `apps/web/src/features/quotes/components/LineItemEditor.tsx`

This is the core interactive table for adding/editing/removing quote lines.

```typescript
interface LineItemEditorProps {
  // For create flow: controlled local state (lines not yet persisted)
  lines: Array<{ description: string; quantity: number; unit_price_cents: number }>;
  onLinesChange: (lines: ...) => void;
  
  // For edit flow on existing quote: quoteId provided; mutations called directly
  quoteId?: string;
  persistedLines?: QuoteLineDetailResponse[];  // from useQuoteDetail
  
  readOnly?: boolean;  // For non-draft status views
}
```

MVP features:
- Add new row with empty inputs at bottom
- Description (text), Quantity (number), Unit Price (cents/dollar display)
- Row total calculated client-side (qty × price)
- Remove row button (❌) — soft delete locally in create flow; calls `useDeleteQuoteLine` in edit flow (if endpoint exists)
- Running subtotal shown at bottom
- `customer_visible: true` default for all lines (internal-only lines are Phase 2)

> **Stretch goal only if pricebook endpoint exists** (verified in pre-work): Add "Search catalog" icon button per row that opens a mini search-and-select popover — pre-fills description + price from pricebook item. If pricebook endpoint does NOT exist, omit this entirely.

---

## Step 9 — Wire LineItemEditor into QuoteCreatePage

Read `QuoteCreatePage.tsx` (from Step 7). Pass local `lines` state to `LineItemEditor` with the `onLinesChange` callback pattern. Calculate the running subtotal displayed below the table.

---

## Step 10 — Create `SendQuotePreviewModal`

**File**: `apps/web/src/features/quotes/components/SendQuotePreviewModal.tsx`

This is the implementation of the **always-preview-before-send** platform pattern (mvp-arch §16.7).

```typescript
interface SendQuotePreviewModalProps {
  open: boolean;
  quoteId: string;
  customerEmail: string | null;
  customerName: string;
  onClose: () => void;
  onConfirm: () => void;  // called when user clicks "Confirm Send"
  isConfirming: boolean;
}
```

The modal renders:
- Recipient: "[customerName] ([customerEmail])"
- Channel: Email
- Action preview: "A link to Quote [quoteId] will be sent. The customer can view and accept from the link."
- "Cancel" button — closes modal, no action
- "Confirm Send" button — calls `onConfirm()` which triggers `useGeneratePublicLink`

> The `useGeneratePublicLink` mutation is called ONLY from the "Confirm Send" button handler — never pre-emptively. This is the always-preview-before-send invariant.

**On confirm flow in `QuoteCreatePage`:**
```typescript
// 1. User clicks "Send" → all lines saved → SendQuotePreviewModal opens
// 2. User confirms → useGeneratePublicLink fires
// 3. On link generated → optionally fire useCommsPreview + send notification
//    (check if communications/preview endpoint exists; if not, skip and just show "Link generated" toast)
// 4. Navigate to /quotes/[quoteId]
```

---

## Step 11 — Extend `QuoteDetailPage` for Draft Actions

Read the full `QuoteDetailPage.tsx` before modifying it. Understand all existing state and component structure.

Add contextual actions based on `quote.status_code`:

**When `status_code === 'draft'`:**

In the existing action area (find where `QuoteApprovalActionBar` is rendered — it's shown for `pending_approval`), add for `draft`:

```tsx
// Tech role sees:
<RoleGate permission="quote.submit_for_approval">
  <SubmitForApprovalButton quoteId={quoteId} />
</RoleGate>

// Owner role sees:
<RoleGate permission="quotes.edit">
  <SendToCustomerButton quoteId={quoteId} quote={quote} />
</RoleGate>

// Line item editing:
// In the QuoteLineItemTable area, show <LineItemEditor> in edit mode
// with quoteId and persistedLines from quote data
```

**When `status_code === 'sent'` or `converted` or `accepted'`:**

```tsx
// Owner sees:
{quote.customer_accepted_at && (
  <RoleGate permission="quotes.edit">
    <ConvertToJobButton quoteId={quoteId} />
  </RoleGate>
)}
```

> Preserve all existing approval workflow components — do NOT modify `QuoteApprovalActionBar`, `QuoteReviewModeBar`, or the Changes/Activity tabs.

**Intermediate check after Step 11:**
```bash
pnpm --filter web test -- --testPathPattern="QuoteDetail" 2>&1 | tail -8
```

---

## Step 12 — Update `QuotesPage` + `useQuotes`

Read both files before modifying.

**In `useQuotes.ts`:**
- Add optional `status?: string` param
- Pass to API as `?status=` query param (now that B17 Part A added server-side filtering)
- Remove the `QuoteListItemEnhanced` type extension if B17 added `status_code` and `customer_name` natively to `QuoteListItem`

**In `QuotesPage.tsx`:**
- Add "New Quote" button wrapped in `<RoleGate permission="quotes.create">` → navigates to `/quotes/new`
- Remove client-side `useMemo` status filter — pass `activeStatus` to `useQuotes` instead
- Remove BE-2/BE-3/BE-4 comments (those gaps are now closed by B17)
- Add "Convert to Job" row action for quotes with `customer_accepted_at` set

---

## Step 13 — QuotesPage "Convert to Job" Row Action

For each quote row where `status_code === 'sent'` and `customer_accepted_at` is not null (customer accepted via public link), add a small "Convert" button in the Actions column:

```tsx
{q.customer_accepted_at && (
  <RoleGate permission="quotes.edit">
    <button
      onClick={() => void convertQuote({ quoteId: q.id })}
      className="text-xs text-brand-600 hover:underline"
    >
      Convert to Job
    </button>
  </RoleGate>
)}
```

Confirm mutation status with a loading state; on success navigate to `/schedule`.

---

## Test Requirements

### Platform: Web (`apps/web`) — Vitest + `@testing-library/react`

- `vi.mock()` not `jest.mock()`
- `toBeInTheDocument()` for assertions
- Mock `next/navigation` for router:
  ```typescript
  const mockPush = vi.fn();
  vi.mock("next/navigation", () => ({
    usePathname: () => "/quotes/new",
    useRouter: () => ({ push: mockPush }),
  }));
  beforeEach(() => mockPush.mockClear());
  ```
- Mock `crypto.randomUUID` in tests that call `useCreateQuote`:
  ```typescript
  vi.stubGlobal('crypto', { randomUUID: () => 'test-idempotency-key' });
  ```

### TanStack Query Setup

```typescript
function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}
```

### Test Resilience Rules (per `react-engineer-rules.md` Rule 15)

- Never mutate shared fixture objects — copy before modifying
- Per-test `server.use(...)` paired with `server.resetHandlers()` in `afterEach`
- Never assert `toHaveLength(N)` on quote list — assert by specific ID or content

### Unit Tests to Write

**`features/quotes/components/__tests__/LineItemEditor.test.tsx`:**
- Renders empty state ("Add Line Item" button visible)
- Adding a row shows description/qty/price inputs
- Row total calculated correctly (qty × price)
- Remove button removes the row
- Running subtotal updates when rows change

**`features/quotes/components/__tests__/SendQuotePreviewModal.test.tsx`:**
- When `open=false`: modal not visible
- When `open=true`: shows recipient name/email
- "Cancel" calls `onClose` without calling `onConfirm`
- "Confirm Send" calls `onConfirm`
- `isConfirming=true` disables the confirm button

**`features/quotes/components/__tests__/QuoteActionBar.test.tsx`:**
- Draft + owner role: shows "Send to Customer" and not "Submit for Approval"
- Draft + tech role: shows "Submit for Approval" and not "Send to Customer"
- Sent + accepted: shows "Convert to Job" for owner
- Non-draft non-accepted: no action buttons

### Integration Tests

**`apps/web/src/__tests__/batch_fe_b19/quoteCreate.integration.test.tsx`:**
1. `/quotes/new` renders without crashing
2. "New Quote" is visible for owner; hidden for tech
3. Customer picker loads customer list from MSW
4. Adding a line item shows in the table
5. "Save Draft" mutation fires with correct payload

**`apps/web/src/__tests__/batch_fe_b19/quoteSend.integration.test.tsx`:**
1. "Send to Customer" button opens `SendQuotePreviewModal`
2. "Cancel" closes modal without firing `useGeneratePublicLink`
3. "Confirm Send" fires `useGeneratePublicLink` mutation

---

## Final Verification

### Phase 1 — Targeted (after each step group)

```bash
cd <repo>/frontend

# After hooks:
pnpm --filter web test -- --testPathPattern="useCreateQuote|useAddLine|useConvert" 2>&1 | tail -6

# After components:
pnpm --filter web test -- --testPathPattern="LineItemEditor|SendQuotePreview|QuoteActionBar" 2>&1 | tail -8

# After integration:
pnpm --filter web test -- --testPathPattern="batch_fe_b19" 2>&1 | tail -8
```

### Phase 2 — Full Verification

```bash
cd <repo>/frontend && pnpm --filter @pilot/ui check-types && pnpm --filter web check-types && pnpm --filter @pilot/ui lint && pnpm --filter web lint && echo "=== TYPE+LINT PASS ===" && pnpm --filter @pilot/ui test 2>&1 | tail -6 && pnpm --filter web test 2>&1 | tail -6 && echo "=== FE-B19 FINAL VERIFICATION COMPLETE ==="
```

---

## Definition of Done — FE-B19

Update `dev-docs/analysis/pilot-app-pre-wkstm-3-prep-plan.md` §Phase 0.9:

- [ ] Regression baseline captured for `@pilot/ui` and `web`
- [ ] `pnpm sync-api-types` run
- [ ] Design doc read in full (A–I)
- [ ] All mandatory source files read before modifying (QuotesPage, useQuotes, QuoteDetailPage, quote-approval/components, mocks/handlers/index.ts)
- [ ] All endpoint pre-work verification completed — line DELETE/PATCH existence confirmed, convert response shape confirmed, pricebook stretch goal decision made
- [ ] **Step 1**: `quoteBuilderHandlers.ts` created + registered in `mocks/handlers/index.ts`
- [ ] **Steps 2–6**: All 6 new hooks created (`useCreateQuote`, `useAddQuoteLine`, `useDeleteQuoteLine` (if applicable), `useSubmitForApproval`, `useGeneratePublicLink`, `useConvertQuote`)
- [ ] **Step 7**: `QuoteCreatePage` + `quotes/new/page.tsx` created; navigates there from "New Quote" button
- [ ] **Step 8**: `LineItemEditor` built; add/delete rows; running subtotal calculates correctly
- [ ] **Step 10**: `SendQuotePreviewModal` built; always-preview-before-send respected — `useGeneratePublicLink` never called without user confirmation
- [ ] **Step 11**: `QuoteDetailPage` extended — draft actions appear for draft status; existing approval workflow unchanged
- [ ] **Step 12**: `useQuotes` updated with server-side `?status=` param; `QuotesPage` passes status to hook; client-side filter removed; "New Quote" button added
- [ ] **Step 13**: "Convert to Job" row action on accepted quotes in list
- [ ] `LineItemEditor` unit tests pass
- [ ] `SendQuotePreviewModal` unit tests pass — cancel does NOT trigger confirm
- [ ] `QuoteActionBar` unit tests pass — RBAC visibility correct per role/status
- [ ] Integration tests in `__tests__/batch_fe_b19/` pass
- [ ] All new MSW handlers registered in `mocks/handlers/index.ts`
- [ ] No fixture objects mutated in tests
- [ ] Zero TypeScript errors (`pnpm --filter web check-types`)
- [ ] Zero ESLint `no-hardcoded-design-values` warnings
- [ ] **Phase 2 FULL verification command passes** (`=== FE-B19 FINAL VERIFICATION COMPLETE ===`):
  ```bash
  cd <repo>/frontend && pnpm --filter @pilot/ui check-types && pnpm --filter web check-types && pnpm --filter @pilot/ui lint && pnpm --filter web lint && echo "=== TYPE+LINT PASS ===" && pnpm --filter @pilot/ui test 2>&1 | tail -6 && pnpm --filter web test 2>&1 | tail -6 && echo "=== FE-B19 FINAL VERIFICATION COMPLETE ==="
  ```
- [ ] Final test count documented
- [ ] Completion Summary added to impl plan §Phase 0.9

---

## Completion Summary

After all DoD items are complete, add a **Completion Summary** to `dev-docs/analysis/pilot-app-pre-wkstm-3-prep-plan.md` under Phase 0.9 — FE-B19:

```markdown
### FE-B19 — Quote Builder UI: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot React Engineer
**Baseline**: X passed (ui) | X passed (web)
**Final**: X+N passed (ui) | X+N passed (web) (+N new tests)

#### What Was Accomplished

- Created /quotes/new full-page quote builder
- Built LineItemEditor with add/remove rows and running subtotal
- Built SendQuotePreviewModal — always-preview-before-send enforced
- Extended QuoteDetailPage with draft-mode edit actions
- Updated QuotesPage: server-side status filter, New Quote button, Convert to Job action
- 6 new TanStack Query hooks for quote CRUD mutations

#### Files Changed / Created

| File | Action |
|---|---|
| `apps/web/src/mocks/handlers/quoteBuilderHandlers.ts` | Created |
| `apps/web/src/mocks/handlers/index.ts` | Updated |
| `apps/web/src/features/quotes/hooks/useCreateQuote.ts` | Created |
| `apps/web/src/features/quotes/hooks/useAddQuoteLine.ts` | Created |
| `apps/web/src/features/quotes/hooks/useDeleteQuoteLine.ts` | Created (if applicable) |
| `apps/web/src/features/quotes/hooks/useSubmitForApproval.ts` | Created |
| `apps/web/src/features/quotes/hooks/useGeneratePublicLink.ts` | Created |
| `apps/web/src/features/quotes/hooks/useConvertQuote.ts` | Created |
| `apps/web/src/features/quotes/components/QuoteCreatePage.tsx` | Created |
| `apps/web/src/features/quotes/components/LineItemEditor.tsx` | Created |
| `apps/web/src/features/quotes/components/SendQuotePreviewModal.tsx` | Created |
| `apps/web/src/features/quotes/components/QuoteActionBar.tsx` | Created |
| `apps/web/src/features/quotes/components/QuotesPage.tsx` | Updated |
| `apps/web/src/features/quotes/hooks/useQuotes.ts` | Updated |
| `apps/web/src/features/quote-approval/QuoteDetailPage.tsx` | Updated |
| `apps/web/src/app/(authed)/quotes/new/page.tsx` | Created |

#### Tests Added

| Test File | Type | Tests | All Pass |
|---|---|---|---|
| `features/quotes/components/__tests__/LineItemEditor.test.tsx` | Unit | N | ✅ |
| `features/quotes/components/__tests__/SendQuotePreviewModal.test.tsx` | Unit | N | ✅ |
| `features/quotes/components/__tests__/QuoteActionBar.test.tsx` | Unit | N | ✅ |
| `apps/web/src/__tests__/batch_fe_b19/quoteCreate.integration.test.tsx` | Integration | N | ✅ |
| `apps/web/src/__tests__/batch_fe_b19/quoteSend.integration.test.tsx` | Integration | N | ✅ |
```

---

## After This Batch

FE-B19 is complete. Users can create quotes, add line items, send to customers (via preview), submit for approval, and convert accepted quotes to jobs.

**Next batch**: `batch-fe-b20-react-engr-prompt.md` — Catalog Management UI (Pricebook, Markups, Labor Rates, Suppliers).
