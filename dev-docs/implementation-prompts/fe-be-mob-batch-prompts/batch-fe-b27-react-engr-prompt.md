# Implementation Prompt: FE-B27 — Comms UX, Auto-Save Fixes, Table Polish, Dispatch Filter Label

**Mode**: Pilot React Engineer  
**Batch**: FE-B27  
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §Phase 1 — Batch #3  
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-fe-b27-design.md`  
**Estimated session**: 3–4 hours  
**Platform**: Web (`apps/web`) + Shared UI (`packages/ui`)  
**Backend companion**: None — pure frontend batch, no B19 dependency

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-react-engineer/react-engineer-rules.md`** — in full
- **`dev-docs/architecture-design/batch-designs/batch-fe-b27-design.md`** — every section (A–I), especially §G Open Questions Resolved

**Critical rules for this batch:**

- **Rule 1.1**: Before any invoice column additions, verify `total_cents` and `issued_at` exist in the `InvoiceListItem` response in `backend/openapi_schema_map.md`. If NOT there → **STOP and ask Tom**.
- **Rule 1.2**: Before adding supplier items price column, check `useSupplierItems` hook response shape. If `price_cents` is NOT in the response → **skip that task** and note it in the completion summary. Do NOT add a column displaying `undefined`.
- **Rule 7**: Check `packages/ui/src/index.ts` before creating any new component — `SmsThreadBubble` is already exported; you are extending it, not replacing it.
- **Rule 8**: No new npm dependencies without first checking `package.json`. This batch adds no new dependencies.
- **Rule 10**: If ANY test fails during your work — even pre-existing — you must fix it before declaring the batch done.

---

## Pre-Work: Establish Regression Baseline

Before touching any file, capture the current baseline:

```bash
cd <repo>/frontend

# Shared UI package (SmsThreadBubble lives here)
pnpm --filter @pilot/ui test 2>&1 | tail -5

# Web app
pnpm --filter web test 2>&1 | tail -5
```

Record both counts: **`@pilot/ui: X passed` and `web: Y passed`**. Both must still pass at the end.

> **If any tests are already failing before you start**: Confirm with Tom before proceeding. You may NOT start implementation while tests are in an unexplained failed state.

---

## Pre-Work: Sync API Types

```bash
cd <repo>/frontend
pnpm sync-api-types
```

This batch does not add new hooks, but running `sync-api-types` ensures the `InvoiceListItem` type is current before you add invoice columns.

---

## Pre-Work: Verify Invoice Fields Exist in API Response

```bash
grep -A 20 "InvoiceListItem\|invoice_summary\|InvoiceSummary" backend/openapi_schema_map.md | head -40
```

Confirm that both `total_cents` and `issued_at` appear in the list response before writing any code. If either is missing → **STOP and ask Tom**.

---

## Pre-Work: Read These Source Files

Read each of these with `read_file` before writing any code:

```
frontend/packages/ui/src/sms-thread-bubble/types.ts
  ← understand current SmsThreadBubbleProps before adding senderLabel

frontend/packages/ui/src/sms-thread-bubble/SmsThreadBubble.tsx
  ← understand current render structure before adding sender label below status row

frontend/packages/ui/src/sms-thread-bubble/SmsThreadBubble.native.tsx
  ← understand RN variant — must apply the same change

frontend/apps/web/src/features/customer-comms/components/CommThreadGroup.tsx
  ← understand how SmsThreadBubble is called and what thread data is available

frontend/apps/web/src/features/jobs/components/JobNotesTab.tsx
  ← understand current auto-save indicator before upgrading it

frontend/apps/web/src/features/invoices/components/InvoicesPage.tsx
  ← understand current table column structure before adding Total + Issued

frontend/apps/web/src/features/dispatch-board/components/FilterSidebar.tsx
  ← find the "Customer" label at line ~189 before renaming

frontend/packages/ui/src/index.ts
  ← confirm SmsThreadBubble export path before modifying

frontend/apps/web/src/mocks/handlers/index.ts
  ← understand handler registration pattern (needed if any MSW update required)
```

Also run these discovery greps before starting:

```bash
# Find the global comms thread list component (the /comms page, not the customer detail tab)
grep -rn "comms\|CommsPage\|thread.*list\|ThreadList" \
  frontend/apps/web/src/features/customer-comms/ --include="*.tsx" -l

# Find the Settings Profile page
grep -rn "Profile\|MyAccount\|my-account\|account.*settings" \
  frontend/apps/web/src/features/settings/ --include="*.tsx" -l

# Find catalog tab components
find frontend/apps/web/src/features/catalog/ -name "*.tsx" | head -20
```

---

## Background / Context

This batch fixes several alpha testing issues discovered in the July 10, 2026 testing session. All changes are pure frontend — no backend work required.

**Critical pre-check**: Per the design doc §G, `CustomerOverviewTab.tsx` already uses **explicit Save + Cancel** via the `CustomerForm` component when `isEditing === true`. **Do NOT touch `CustomerOverviewTab.tsx`** — there is nothing to fix there. If you read the component and confirm this, note it in the completion summary and move on.

---

## Task 1 — Add `senderLabel` to `SmsThreadBubble` (packages/ui)

**Why**: Messages in the Comms page have no "From: [Name]" label. With multiple techs, direction-based coloring alone is ambiguous.

**File**: `frontend/packages/ui/src/sms-thread-bubble/types.ts`

Add to `SmsThreadBubbleProps`:

```typescript
/** Optional sender name label displayed below the bubble.
 *  e.g. "From: Jake" (outbound) or "From: John Smith" (inbound).
 *  If undefined, no sender label is rendered. */
senderLabel?: string;
```

**File**: `frontend/packages/ui/src/sms-thread-bubble/SmsThreadBubble.tsx`

Add `senderLabel` to the destructured props. After the status row `<div>` (after the closing `</div>` of the status row), add:

```tsx
{senderLabel && (
  <p
    className={`text-xs text-neutral-400 mt-0.5 ${isOutbound ? "text-right" : "text-left"}`}
    data-testid={`sender-label-${message.message_id}`}
  >
    {senderLabel}
  </p>
)}
```

**File**: `frontend/packages/ui/src/sms-thread-bubble/SmsThreadBubble.native.tsx`

Same change using React Native `<Text>` with equivalent styling from the `tokens` import.

> **This prop is optional.** All existing call sites that do NOT pass `senderLabel` are unaffected — the component renders identically to before when `senderLabel` is `undefined`. Do NOT modify any existing test that doesn't use `senderLabel`.

---

## Task 2 — Pass `senderLabel` from `CommThreadGroup.tsx`

**File**: `frontend/apps/web/src/features/customer-comms/components/CommThreadGroup.tsx`

For each message rendered by `SmsThreadBubble`, pass:

- **Outbound** (tech → customer): `senderLabel={`From: ${thread.tech_name.split(' ')[0]}`}`
- **Inbound** (customer → tech):
  - If `thread.customer_name` (or equivalent) is available in the `SmsThread` type → `senderLabel={`From: ${thread.customer_name}`}`
  - If `customer_name` is NOT in the thread data → **omit `senderLabel`** for inbound messages (do not show "From: undefined")

**Text size fix** (comms thread header):
- Find `text-body` class usage in `CommThreadGroup.tsx` (tech name header line) → change to `text-sm`
- Find `text-caption` class usage (date range, message count, job display) → change to `text-xs`

This makes the comms thread header text match the size of other list pages (`text-sm` = 14px).

---

## Task 3 — Global Comms Page: Customer Name as Primary Identifier

**Find** the global comms page thread list component (the `/comms` route, not the per-customer comms tab). Use the discovery grep from Pre-Work.

On thread list cards, customer name must be the **primary/bold** identifier. Tech name moves to secondary.

**Current order** (wrong): Tech name is prominent, customer name is secondary or absent.  
**New order** (correct):
```
[Customer Name] (bold, text-sm font-medium text-neutral-900)
[Tech Name] · [Date]  (secondary, text-xs text-neutral-500)
```

Make this change in whatever component renders the global thread list cards.

---

## Task 4 — Upgrade `JobNotesTab.tsx` Auto-Save Indicator

**File**: `frontend/apps/web/src/features/jobs/components/JobNotesTab.tsx`

**Keep**: The `onBlur` auto-save behavior. Do NOT remove it.

**Change 1**: Remove the `"Blur to save"` hint text in the `idle` state:
```tsx
// REMOVE this:
<span className="text-neutral-400">Blur to save</span>
// Replace with: nothing (render null or empty fragment for idle state)
```

**Change 2**: Upgrade the `"Saved ✓"` indicator from small corner text to a more prominent inline indicator:

```tsx
// REPLACE current success case:
<span className="text-green-600 font-medium">Saved ✓</span>
// WITH (uses design tokens, larger size):
<span className="text-sm font-medium text-margin-600 transition-opacity duration-500">
  Saved ✓
</span>
```

**Change 3**: Add a brief green border flash on the textarea when save succeeds. Add a `saveFlash` state:

```tsx
const [saveFlash, setSaveFlash] = useState(false);
```

On `onSuccess`, set `saveFlash(true)`. Clear it after 800ms with `setTimeout`. Apply to textarea:

```tsx
className={`w-full px-3 py-2.5 border rounded-lg text-sm ... 
  ${saveFlash ? "border-margin-400 ring-1 ring-margin-300" : "border-neutral-300"}
  transition-all duration-300`}
```

**Change 4**: Update the footer hint text:
```tsx
// REPLACE:
<p className="mt-1.5 text-xs text-neutral-400">
  Notes are saved automatically when you click away from this field.
</p>
// WITH:
<p className="mt-1.5 text-xs text-neutral-400">
  Changes save automatically when you click away.
</p>
```

---

## Task 5 — Catalog Monetary Column Right-Alignment

Locate the catalog tab components using the discovery grep from Pre-Work.

For each of these tabs, find the `<th>` and corresponding `<td>` cells for monetary columns and add `text-right`:

| Tab | Column(s) to right-align |
|---|---|
| **Pricebook** | "Current Price" |
| **Labor Rates** | "Hourly Rate", "Burdened Rate" |
| **Markups** | "Current Markup" |

**Implementation**: Pure CSS class addition. Change `text-left` → `text-right` (or just add `text-right` if no alignment class exists). No logic changes.

---

## Task 6 — Invoice List: Add "Total" and "Issued" Columns

**File**: `frontend/apps/web/src/features/invoices/components/InvoicesPage.tsx`

**PREREQUISITE**: Confirm `total_cents` and `issued_at` exist in `InvoiceListItem` via `openapi_schema_map.md` before writing this code.

**Add "Total" column** after the "Status" column:

```tsx
// Table header:
<th className="py-3 px-4 text-right text-caption font-medium text-neutral-600">
  Total
</th>

// Table cell:
<td className="py-3 px-4 text-right text-body text-neutral-900 tabular-nums whitespace-nowrap">
  {formatCents(invoice.total_cents)}
</td>
```

**Add "Issued" column** after "Total":

```tsx
// Table header:
<th className="py-3 px-4 text-left text-caption font-medium text-neutral-600">
  Issued
</th>

// Table cell:
<td className="py-3 px-4 text-left text-body text-neutral-600 whitespace-nowrap">
  {invoice.issued_at
    ? new Date(invoice.issued_at).toLocaleDateString("en-US", {
        month: "short", day: "numeric", year: "numeric"
      })
    : "—"}
</td>
```

Find the `formatCents` utility — it should already be used in the file. If not, import from `@pilot/shared-api` or wherever it lives in the codebase.

---

## Task 7 — Dispatch Board Filter: Rename "Customer" → "Customer Type"

**File**: `frontend/apps/web/src/features/dispatch-board/components/FilterSidebar.tsx`

Find approximately line 189:

```tsx
// CURRENT:
<FilterGroup label="Customer">

// CHANGE TO:
<FilterGroup label="Customer Type">
```

This is a single string change. No logic changes.

---

## Task 8 — Supplier Items: Add "Current Price" Column (Conditional)

**Find** the `SupplierItemsPage.tsx` file using the discovery grep.

**Read** the `useSupplierItems` hook to understand its response shape.

```bash
grep -A 5 "price\|price_cents\|SupplierItem" backend/openapi_schema_map.md | head -20
```

**If `price_cents` is in the API response** → add a "Current Price" column with `text-right` alignment, rendered as `formatCents(item.price_cents)` or `"—"` if null.

**If `price_cents` is NOT in the API response** → skip this task. Note in completion summary: "Supplier Items price column deferred — `price_cents` not in API response. Requires backend change."

---

## Test Requirements

**Phase 1 — After Tasks 1–2** (`@pilot/ui` scope):

```bash
cd <repo>/frontend
pnpm --filter @pilot/ui test 2>&1 | tail -5
```

All existing `SmsThreadBubble` tests must still pass. The new `senderLabel` prop is optional — existing tests must NOT break.

Write at minimum these new tests in `packages/ui/src/sms-thread-bubble/SmsThreadBubble.test.tsx`:
1. `test_sender_label_renders_outbound` — pass `senderLabel="From: Jake"`, direction=outbound → label appears right-aligned below bubble
2. `test_sender_label_renders_inbound` — pass `senderLabel="From: John Smith"`, direction=inbound → label appears left-aligned
3. `test_sender_label_omitted` — do NOT pass `senderLabel` → no sender label element in DOM

**Phase 1 — After Tasks 3–8** (web scope):

```bash
pnpm --filter web test 2>&1 | tail -5
```

Write new tests in `apps/web/src/__tests__/batch_fe_b27/` (create folder):
1. `job_notes_saved_indicator.test.tsx` — after successful save blur: "Saved ✓" renders with `text-margin-600` class; "Blur to save" text is NOT in the DOM
2. `invoice_columns.test.tsx` — invoice list renders "Total" column header; total_cents value formatted as currency; renders "Issued" column header
3. `filter_sidebar_label.test.tsx` — `FilterSidebar` renders "Customer Type" text; does NOT render "Customer" as a standalone group label

Test file `pytestmark` equivalent for React: use `describe` + `it` blocks; use existing test wrapper patterns from the codebase.

**All test files must use**:
- `vi.mock()` for hooks (same pattern as existing tests in the feature folder)
- MSW handlers if API calls are triggered
- No module-level render calls — all renders inside `it()` blocks

---

## Final Verification

### Phase 1 — Targeted tests (run after each task group during development)

```bash
cd <repo>/frontend

# After Tasks 1-2 (SmsThreadBubble):
pnpm --filter @pilot/ui test 2>&1 | tail -10

# After Tasks 3-8 (web features):
pnpm --filter web test 2>&1 | tail -10
```

### Phase 2 — Full suite (run once at the very end)

```bash
cd <repo>/frontend

pnpm --filter @pilot/ui test 2>&1 | tail -10
pnpm --filter web test 2>&1 | tail -10

# TypeScript check (no type errors)
pnpm --filter @pilot/ui exec tsc --noEmit 2>&1 | tail -5
pnpm --filter web exec tsc --noEmit 2>&1 | tail -5

# Verify key changes
grep -n "senderLabel" frontend/packages/ui/src/sms-thread-bubble/SmsThreadBubble.tsx
grep -n "Customer Type" frontend/apps/web/src/features/dispatch-board/components/FilterSidebar.tsx
grep -n "total_cents\|issued_at" frontend/apps/web/src/features/invoices/components/InvoicesPage.tsx
grep -n "Blur to save" frontend/apps/web/src/features/jobs/components/JobNotesTab.tsx  # should return nothing

echo "=== FE-B27 FINAL VERIFICATION COMPLETE ==="
```

> **Any failure in either phase must be fixed before the batch is declared done.** The "pre-existing failure" exception requires explicit written confirmation from Tom.

---

## Definition of Done

- [ ] Regression baseline captured — both `@pilot/ui` and `web` test counts recorded
- [ ] `pnpm sync-api-types` run — `InvoiceListItem` fields confirmed
- [ ] `total_cents` and `issued_at` verified in `openapi_schema_map.md` before writing invoice code
- [ ] All mandatory source files read before writing any code
- [ ] **Task 1**: `senderLabel?: string` added to `SmsThreadBubbleProps` in `types.ts`
- [ ] **Task 1**: `senderLabel` rendered below status row in `SmsThreadBubble.tsx` (web)
- [ ] **Task 1**: Same change in `SmsThreadBubble.native.tsx` (RN `<Text>`)
- [ ] **Task 2**: `senderLabel` passed from `CommThreadGroup.tsx` for outbound (tech first name) + inbound (if available)
- [ ] **Task 2**: Thread header text size fixed — `text-body` → `text-sm`, `text-caption` → `text-xs`
- [ ] **Task 3**: Global comms thread list — customer name is primary (bold), tech name is secondary
- [ ] **Task 4**: `JobNotesTab.tsx` — "Blur to save" text removed from idle state
- [ ] **Task 4**: "Saved ✓" uses `text-sm text-margin-600` (design token, not `text-green-600`)
- [ ] **Task 4**: Textarea border flash on save success (`border-margin-400 ring-1 ring-margin-300`, 800ms)
- [ ] **Task 4**: Footer hint text updated to "Changes save automatically when you click away."
- [ ] **Task 5**: Catalog Pricebook "Current Price" column — `text-right` on `<th>` and `<td>`
- [ ] **Task 5**: Catalog Labor Rates "Hourly Rate" + "Burdened Rate" columns — `text-right`
- [ ] **Task 5**: Catalog Markups "Current Markup" column — `text-right`
- [ ] **Task 6**: Invoice list "Total" column added with right-aligned `formatCents(invoice.total_cents)`
- [ ] **Task 6**: Invoice list "Issued" column added with formatted date or "—" fallback
- [ ] **Task 7**: `FilterSidebar.tsx` — `label="Customer"` → `label="Customer Type"`
- [ ] **Task 8**: Supplier Items price column — either added (if API returns `price_cents`) or skipped + noted
- [ ] **CustomerOverviewTab**: Confirmed already uses explicit Save — no change made, noted in summary
- [ ] 3 new `SmsThreadBubble` tests in `packages/ui/src/sms-thread-bubble/SmsThreadBubble.test.tsx`
- [ ] 3 new web tests in `apps/web/src/__tests__/batch_fe_b27/`
- [ ] No new npm dependencies added
- [ ] **Phase 1**: `@pilot/ui` tests pass — zero failures including any pre-existing
- [ ] **Phase 1**: `web` tests pass — zero failures
- [ ] **Phase 2**: Full suites pass for both packages — zero failures
- [ ] TypeScript `tsc --noEmit` clean for both packages
- [ ] Completion Summary added to `pilot-launch-plan.md` §Phase 1 Batch #3

---

## Completion Summary

After all Definition of Done items are complete:

1. Add a **Completion Summary** to `dev-docs/analysis/pilot-launch-plan.md` §Phase 1 Batch #3.
2. Update Batch #3 status from `☐` → `✅`.

```markdown
### FE-B27 — Comms UX, Auto-Save Fixes, Table Polish, Dispatch Filter: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot React Engineer
**Baseline**: @pilot/ui X passed | web Y passed
**Final**: @pilot/ui X+N passed | web Y+M passed (+N/@pilot/ui, +M/web new tests)

#### What Was Accomplished

- Added `senderLabel?: string` to `SmsThreadBubble` — renders "From: [Name]" below each bubble
- CommThreadGroup passes sender labels; fixed text size (text-body → text-sm, text-caption → text-xs)
- Global comms thread list: customer name now primary identifier on thread cards
- JobNotesTab: removed "Blur to save" hint; "Saved ✓" uses design token + larger text + border flash
- Catalog: right-aligned monetary columns in Pricebook, Labor Rates, and Markups tabs
- InvoicesPage: added "Total" and "Issued" columns
- FilterSidebar: "Customer" → "Customer Type" label
- Supplier Items price column: [added / deferred — reason]
- CustomerOverviewTab: confirmed already explicit Save — no change needed

#### Files Changed / Created

| File | Action |
|---|---|
| `packages/ui/src/sms-thread-bubble/types.ts` | Updated — added `senderLabel?: string` |
| `packages/ui/src/sms-thread-bubble/SmsThreadBubble.tsx` | Updated — render sender label |
| `packages/ui/src/sms-thread-bubble/SmsThreadBubble.native.tsx` | Updated — RN variant |
| `apps/web/src/features/customer-comms/components/CommThreadGroup.tsx` | Updated |
| [global comms component] | Updated — customer name as primary |
| `apps/web/src/features/jobs/components/JobNotesTab.tsx` | Updated |
| [catalog components] | Updated — right-align monetary |
| `apps/web/src/features/invoices/components/InvoicesPage.tsx` | Updated — Total + Issued |
| `apps/web/src/features/dispatch-board/components/FilterSidebar.tsx` | Updated — label rename |
| `packages/ui/src/sms-thread-bubble/SmsThreadBubble.test.tsx` | Updated — 3 new tests |
| `apps/web/src/__tests__/batch_fe_b27/[test files]` | Created — 3 new test files |
```

---

## After This Batch — Next Step

After FE-B27 is complete and Tom has reviewed:

**FE-B26** (React Engineer) is next — it depends on B19 having shipped. FE-B26 fixes all UUID display bugs in the job/quote UI using the new `job_number`, `quote_number`, `status_code`, `site_name`, `customer_name` fields from B19.

Before FE-B26 starts: run `pnpm sync-api-types` to pull the B19 OpenAPI additions.
