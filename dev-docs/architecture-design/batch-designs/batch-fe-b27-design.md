# Batch FE-B27 Design — Comms UX, Auto-Save Fixes, Table Polish, Dispatch Filter Label

**Batch Code**: FE-B27  
**Type**: Frontend web only (`apps/web` + `packages/ui`)  
**Date**: 2026-07-11  
**Author**: Pilot Architect  
**Status**: Ready for implementation  
**Priority**: P1 — alpha testing fixes, no B19 dependency  
**Backend companion**: None — pure frontend batch  
**Design spec**: `dev-docs/architecture-design/batch-designs/batch-ui-ds-b1-design-spec.md` — Surface 4 (JobPropertiesPanel) is in FE-B27 scope  
**Source Issues**: `dev-docs/testing-support/alpha-testing/ui-testing-status-2026-07-10-v2.md`

---

## A. Input Read Summary

| Input | What Was Verified |
|---|---|
| `ui-testing-status-2026-07-10-v2.md` | Confirmed FE-B27 items: comms sender labels, comms text size fix, Job Notes Saved ✓ upgrade, Settings/Profile → explicit Save, CustomerOverviewTab → explicit Save, catalog monetary column align, invoice Total + Issued columns, dispatch filter rename, supplier items price column |
| `ui-testing-status-2026-07-10-v2.md` §TD-1 decision | Auto-save: Job Notes keeps auto-save (upgrade UX only). JobPropertiesPanel, Settings/Profile, CustomerOverviewTab → explicit Save buttons. CustomerOverviewTab already uses explicit Save via `CustomerForm` — no change needed to its edit flow (it already has Cancel/Submit). **Only the view-mode "Edit" button + form submit is already explicit.** |
| `frontend/packages/ui/src/sms-thread-bubble/SmsThreadBubble.tsx` | MCP-confirmed: `SmsThreadBubbleProps` has `message`, `showTimestamp`, `showDeliveryStatus`, `isPending`, `testID` — NO `senderLabel` prop. Must add. |
| `frontend/apps/web/src/features/customer-comms/components/CommThreadGroup.tsx` | Uses `SmsThreadBubble` from `@pilot/ui`. Thread has `tech_name`. No customer name on outbound bubble, no sender label. Thread header uses `text-body` (13px) and `text-caption` (11px). |
| `frontend/apps/web/src/features/jobs/components/JobNotesTab.tsx` | Auto-save on blur confirmed. Current "Saved ✓" indicator uses `text-xs` with `text-green-600` (plain green, not design token). Shows `text-neutral-400 "Blur to save"` hint text — inappropriate for field workers. Needs: (1) remove "Blur to save" hint, (2) upgrade indicator size to `text-sm`, (3) use design tokens `text-margin-600` for success, (4) add border flash on save. |
| `frontend/apps/web/src/features/customers/components/CustomerOverviewTab.tsx` | Already has **explicit** Save + Cancel via `CustomerForm` when `isEditing === true`. **No auto-save issue here.** The "Edit Customer" button already triggers the form, and form has explicit Submit + Cancel. ✅ No change needed. |
| `frontend/apps/web/src/features/dispatch-board/components/FilterSidebar.tsx` line 189 | `<FilterGroup label="Customer">` — must rename to `<FilterGroup label="Customer Type">` |
| `frontend/apps/web/src/features/invoices/components/InvoicesPage.tsx` | Invoice table currently has: Invoice #, Customer, Status, Due. Missing: Total (`total_cents`) and Issued (`issued_at`). Both fields are in `InvoiceListItem` response (confirmed from schema). Pure FE add. |
| Catalog components (to be read by engineer) | `frontend/apps/web/src/features/catalog/` — Pricebook, LaborRates, Markups tabs. Monetary columns need `text-right` on `<th>` and `<td>`. |

---

## B. Migration Plan

**No Alembic migration.** Pure frontend batch — no DB schema changes.

---

## C. Execution Order

| Step | Task | Primary File(s) |
|---|---|---|
| 1 | `pnpm sync-api-types` — confirm no new backend types needed | — |
| 2 | Regression baseline (web + @pilot/ui) | — |
| 3 | **Task 1**: Add `senderLabel?: string` to `SmsThreadBubbleProps` + render in component | `packages/ui/src/sms-thread-bubble/types.ts`, `SmsThreadBubble.tsx`, `SmsThreadBubble.native.tsx` |
| 4 | **Task 2**: Pass `senderLabel` from `CommThreadGroup.tsx` for outbound (tech name) + inbound (customer name) | `apps/web/src/features/customer-comms/components/CommThreadGroup.tsx` |
| 5 | **Task 3**: Fix comms thread card — customer name as primary on global comms thread list | `apps/web/src/features/customer-comms/` — find global comms thread list component |
| 6 | **Task 4**: Fix comms text size — `text-body`→`text-sm`, `text-caption`→`text-xs` in `CommThreadGroup.tsx` | `apps/web/src/features/customer-comms/components/CommThreadGroup.tsx` |
| 7 | Phase 1 unit test checkpoint | `pnpm --filter @pilot/ui test \| tail -5` + `pnpm --filter web test \| tail -5` |
| 8 | **Task 5**: Upgrade `JobNotesTab.tsx` auto-save indicator UX | `apps/web/src/features/jobs/components/JobNotesTab.tsx` |
| 9 | **Task 6**: Catalog monetary columns — right-align `<th>` + `<td>` for currency columns | Catalog tab components |
| 10 | **Task 7**: Invoice list — add Total + Issued columns | `apps/web/src/features/invoices/components/InvoicesPage.tsx` |
| 11 | **Task 8**: Dispatch board filter — rename "Customer" → "Customer Type" | `apps/web/src/features/dispatch-board/components/FilterSidebar.tsx` |
| 12 | Phase 1 unit test checkpoint | `pnpm --filter web test \| tail -5` |
| 13 | Write/update tests for all changed components | `__tests__/batch_fe_b27/` |
| 14 | Phase 2 full verification | — |

---

## D. New API Endpoints

**None.** All changes are purely frontend. No new backend endpoints required.

All invoice data (`total_cents`, `issued_at`) is already in `InvoiceListItem` from `GET /api/v1/invoices/` — verify in `openapi_schema_map.md` before coding.

---

## E. Pattern Reuse Decisions

| Pattern | Applied Where |
|---|---|
| Optional prop addition to shared component | `SmsThreadBubbleProps` — add `senderLabel?: string` as optional so existing call sites require no changes |
| `text-margin-600` token for success state | `JobNotesTab.tsx` "Saved ✓" — replaces non-standard `text-green-600` |
| `text-right` on `<th>` + `<td>` financial columns | Catalog monetary columns — standard financial table convention |
| `transition-opacity duration-500` fade | "Saved ✓" flash disappears using CSS transition |

---

## F. Shared Module Interfaces

### F1. `SmsThreadBubbleProps` — added field

**File**: `frontend/packages/ui/src/sms-thread-bubble/types.ts`

```typescript
// Add to SmsThreadBubbleProps interface:
/** Optional sender name label displayed below the bubble.
 *  e.g. "From: Jake" (outbound) or "From: John Smith" (inbound)
 *  If undefined, no sender label is shown. */
senderLabel?: string;
```

**Render location** (in `SmsThreadBubble.tsx`): Add below the status row div, above the closing `</div>` of the outer wrapper:

```tsx
{senderLabel && (
  <p className={`text-xs text-neutral-400 mt-0.5 ${isOutbound ? "text-right" : "text-left"}`}>
    {senderLabel}
  </p>
)}
```

Same change applies to `SmsThreadBubble.native.tsx` using the equivalent React Native `<Text>` component.

### F2. `CommThreadGroup.tsx` — sender label passing

For outbound messages (tech → customer):
```tsx
senderLabel={`From: ${thread.tech_name.split(' ')[0]}`}  // First name only
```

For inbound messages (customer → tech):
- Thread data must include `customer_name` or it must be passed from parent context
- Check what data `SmsThread` type includes — if `customer_name` is available: `senderLabel={`From: ${thread.customer_name}`}`
- If not available in thread data: omit `senderLabel` for inbound until B19 or a future batch adds `customer_name` to thread data

---

## G. Open Questions Resolved

| Question | Resolution |
|---|---|
| Does `CustomerOverviewTab` have auto-save to remove? | **No** — it already uses explicit Save (form submit) + Cancel when editing. `setIsEditing(true)` opens `CustomerForm` which has explicit submit. No auto-save behavior exists here. ✅ No change needed. |
| Should `JobNotesTab` auto-save be removed? | **No** — decision confirmed (TD-1): Job Notes KEEPS auto-save on blur. Only upgrade the visual confirmation UX. |
| Does the global comms page need customer name fix? | Yes — the global comms thread list (`/comms`) shows tech name as primary. Need to find and fix the thread list component. Engineer: grep for comms thread list / comms page component to locate it. |
| Is `total_cents` in `InvoiceListItem`? | Assumed yes based on schema. Engineer MUST verify in `openapi_schema_map.md` before coding. If not present → STOP and ask Tom. |
| Is `issued_at` in `InvoiceListItem`? | Same — verify in `openapi_schema_map.md`. |
| Does `SupplierItemsPage` already return price data? | Engineer must check `useSupplierItems` hook response shape. If `price_cents` is in the API response → add column. If not → **defer this task** — it requires a backend change and is out of FE-B27 scope. Do NOT add a column that would show `undefined`. |

---

## H. Surface Mockup Reference

**Source**: `batch-ui-ds-b1-design-spec.md` — Surface 4 (JobPropertiesPanel Save Button)

This batch does NOT implement `JobPropertiesPanel` Save button. That surface is in FE-B27 spec but...

Wait — re-checking scope. Per the launch plan, FE-B27 contains:
- Comms sender labels, comms text size fix
- Job Notes "Saved ✓" upgrade  
- Settings/Profile → explicit Save  
- CustomerOverviewTab → explicit Save (confirmed no change needed)
- Catalog monetary alignment
- Invoice Total + Issued columns
- Dispatch filter rename

The `JobPropertiesPanel` Save button is a **more complex UI-designer-spec'd change** — it is separate from FE-B27. Looking at the launch plan Section 3 FE-B27 scope more carefully:

> FE-B27: "Job Notes 'Saved ✓' indicator upgrade; Settings/Profile → explicit Save button; `CustomerOverviewTab` → explicit Save button"

The `JobPropertiesPanel` Save button change was TD-1 and is in the UI-DS-B1 spec. It should be in a batch that implements the UI spec. **Per batch sequence, FE-B27 runs in parallel — it does NOT implement the dispatch board panel.** The dispatch board Panel Save button is part of FE-B30 (which implements dispatch week/month AND the panel save spec), OR it gets its own batch after FE-B27.

**Decision**: Keep FE-B27 focused on the simple no-dep changes listed above. The `JobPropertiesPanel` explicit Save button redesign (which requires full state machine overhaul per the UI spec) is **NOT in FE-B27**. It will be scheduled after FE-B26 in a separate targeted batch.

### Settings/Profile Explicit Save

**Find the Settings/Profile component**. Engineer must:
```bash
grep -rn "Settings.*Profile\|settings.*profile\|MyAccount\|my.*account\|Profile.*settings" \
  frontend/apps/web/src/features/ --include="*.tsx" -l
```

The profile settings page likely has fields that auto-save on blur. If so, convert to explicit Save + Cancel button pattern (same as `CustomerForm` pattern — form with submit handler, no onBlur API calls).

**If profile page already has explicit Save**: note it in completion summary and mark as no-op.

---

## I. Component Manifest

| Component | File Path | Action |
|---|---|---|
| `SmsThreadBubbleProps` | `frontend/packages/ui/src/sms-thread-bubble/types.ts` | Add `senderLabel?: string` |
| `SmsThreadBubble` (web) | `frontend/packages/ui/src/sms-thread-bubble/SmsThreadBubble.tsx` | Render `senderLabel` below status row |
| `SmsThreadBubble` (native) | `frontend/packages/ui/src/sms-thread-bubble/SmsThreadBubble.native.tsx` | Same — RN `<Text>` equivalent |
| `CommThreadGroup` | `frontend/apps/web/src/features/customer-comms/components/CommThreadGroup.tsx` | Pass `senderLabel` + fix text size tokens |
| Global comms thread list | TBD — engineer finds correct file | Customer name as primary identifier on thread cards |
| `JobNotesTab` | `frontend/apps/web/src/features/jobs/components/JobNotesTab.tsx` | Upgrade "Saved ✓" indicator + remove "Blur to save" text |
| Settings/Profile page | TBD — engineer finds correct file | Convert auto-save to explicit Save + Cancel (if applicable) |
| Catalog Pricebook tab | `frontend/apps/web/src/features/catalog/components/PricebookPage.tsx` (or similar) | Right-align "Current Price" `<th>` + `<td>` |
| Catalog Labor Rates tab | Similar catalog component | Right-align "Hourly Rate" + "Burdened Rate" columns |
| Catalog Markups tab | Similar catalog component | Right-align "Current Markup" column |
| `InvoicesPage` | `frontend/apps/web/src/features/invoices/components/InvoicesPage.tsx` | Add "Total" + "Issued" columns |
| `FilterSidebar` | `frontend/apps/web/src/features/dispatch-board/components/FilterSidebar.tsx` | Line 189: `label="Customer"` → `label="Customer Type"` |
| `SupplierItemsPage` | `frontend/apps/web/src/features/catalog/components/SupplierItemsPage.tsx` (find path) | Add "Current Price" column **only if** `price_cents` is in the API response |
