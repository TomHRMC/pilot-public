# FE-B5 Surface Design Session — Quote Approval Workflow (Pass 3 Flow 5)

**Batch**: FE-B5
**Phase**: 1 — Surface Design Session (Architect → React Engineer handoff)
**Date**: 2026-05-22
**Status**: DESIGN COMPLETE — Ready for React Engineer handoff

**Prerequisite batches confirmed complete**: FE-B0, FE-B1, FE-B2, FE-B3, FE-B4
**Backend gate**: BE-B1 (quote approval state machine) — develop against MSW until landed
**Gates downstream**: FE-B8 (`<DiffView variant="calendar-event">`), FE-B9 (`<DiffView variant="qb-entity">`)

**Design sources consumed**:
- `pilot-app-mvp-frontend-impl-plan.md` §5 Phase 1 process, §6 FE-B5 batch detail
- `frontend-pass-3-flow-5-quote-approval-spec.md`
- `frontend-pass-3-flow-5-quote-line-item-architecture.md`
- `mvp-arch.md` §6.2, §14.1–14.6, §16.2, §16.3
- `pilot-react-engineer-methods.md` §8, §9.1, §12
- `frontend/packages/ui/src/index.ts` — current barrel (FE-B5 section does NOT yet exist)
- `frontend/packages/ui/src/voice-confirm-turn/VoiceConfirmTurn.tsx` — FE-B3 output
- `frontend/packages/ui/src/hooks/useStalenessRetry.ts` — FE-B4 output
- `frontend/apps/web/src/app/(authed)/quotes/page.tsx` — stub placeholder from FE-B0
- `frontend/packages/shared-types/src/api-schema.d.ts` — live OpenAPI types

---

## Table of Contents

- [A. Component Implementation Plan](#a-component-implementation-plan)
- [B. Execution Order](#b-execution-order)
- [C. New Routes](#c-new-routes)
- [D. API Endpoint Consumption](#d-api-endpoint-consumption)
- [E. Pattern Reuse Decisions](#e-pattern-reuse-decisions)
- [F. Shared Module Interfaces](#f-shared-module-interfaces)
- [G. Open Questions Resolved](#g-open-questions-resolved)
- [H. External Dependency Status](#h-external-dependency-status)
- [I. Test Plan](#i-test-plan)

---

## A. Component Implementation Plan

### A.1 Shared Components — `packages/ui/`

All shared components are NEW (confirmed via grep: `DiffView` does not appear in any `.tsx` or `.ts` file in `frontend/packages/ui/src/`; only in forward-reference comments in `useStalenessRetry.ts` and `useMoveJob.ts`).

---

#### `<DiffView>` — THE foundational component of this batch

**File**: `packages/ui/src/diff-view/DiffView.tsx`
**Platform**: Cross-platform (web uses Tailwind/shadcn; mobile uses React Native StyleSheet/Gluestack primitives). Follows the same web/mobile variant pattern as `packages/ui/src/states/`.

**Why cross-platform**: FE-B7 (offline sync mobile) uses `<DiffView variant="entity">` in its mobile conflict resolution screens (`requires_review` severity class). This is explicitly called out in `pilot-app-mvp-frontend-impl-plan.md`. The quote approval diff view (amber/green/red per line item) is owner-side web only for the approval surface itself, but the underlying component must be reusable cross-platform for FE-B7's mobile entity diff and FE-B8/B9's web integration conflicts.

**Platform resolution**: barrel export resolves `DiffView` to web or mobile implementation via `package.json` `"exports"` field, same as `packages/ui/src/states/`. Shared types live in `packages/ui/src/diff-view/types.ts`.

**Props interface**: See §F.1 for the full locked TypeScript interface. Summary:
- `variant`: `"quote-line" | "calendar-event" | "qb-entity" | "entity"` — determines field schema and label rendering
- `baseline`: the "before" snapshot (tech-submitted quote lines, or server-computed `field_diffs` payload)
- `modified`: the "after" snapshot, OR the server-side `field_diffs[]` array
- `showToggle`: boolean — enables the mobile "Show changes / Hide changes" toggle (spec §4)
- `onRevertField`: optional callback — enables per-field revert button (owner approval context only)

**Internal components** (not exported from barrel):
- `DiffField.tsx` — renders a single field diff (amber/green/red per §16.2 vocabulary)
- `DiffLineItem.tsx` — renders a single quote line with its diffs (for `variant="quote-line"`)
- `DiffChangesToggle.tsx` — mobile show/hide toggle (used when `showToggle=true`)

---

#### `useApproveWithEdits()` hook

**File**: `packages/ui/src/hooks/useApproveWithEdits.ts`
**Platform**: Web-only (approval editing is owner-side web surface)
**Purpose**: Manages the pending-edit staging lifecycle. Wraps the `/api/v1/quotes/{id}/pending-edits` CRUD endpoints. Composes `useStalenessRetry()` for the final atomic approve call.

**Why shared**: Reused by both the quote detail page and the mobile quote approval surface (if mobile approval editing is added later). Defined in `packages/ui/src/hooks/` rather than surface-scoped because FE-B8/B9 may need analogous hooks.

---

### A.2 Web Surface Components — `apps/web/src/features/quote-approval/`

All components are NEW surface-scoped (not in `packages/ui/`). Confirmed not pre-existing: the quotes route is a stub placeholder with only `<h1>Quotes</h1>` at `apps/web/src/app/(authed)/quotes/page.tsx`.

| Component | File | Purpose |
|:---|:---|:---|
| `PendingQuotesInboxPage` | `features/quote-approval/PendingQuotesInboxPage.tsx` | Owner's list of `pending_approval` quotes. Renders `<PendingQuoteCard>` list + filter bar. |
| `PendingQuoteCard` | `features/quote-approval/components/PendingQuoteCard.tsx` | Single row card: quote number, tech name, customer name, line count, total, submitted age, action buttons. |
| `PendingInboxFilterBar` | `features/quote-approval/components/PendingInboxFilterBar.tsx` | Filter controls: by tech (select), by customer (search), by age (radio: newest/oldest). |
| `QuoteDetailPage` | `features/quote-approval/QuoteDetailPage.tsx` | Unified owner web detail view with role-gated approval action bar. |
| `QuoteReviewModeBar` | `features/quote-approval/components/QuoteReviewModeBar.tsx` | Top review-mode affordance bar showing `N pending edits`, margin delta, Cancel-edits button. Only visible when `quote.status === 'pending_approval'` and user has `quote.approve` permission. |
| `QuoteLineItemTable` | `features/quote-approval/components/QuoteLineItemTable.tsx` | Renders quote line items in table form. Tracks all three quote styles (component/deliverable/lump-sum per line-item-architecture.md). When in review mode, passes `pendingEdits` to compose `<DiffView variant="quote-line">` inline. |
| `QuoteLineItemRow` | `features/quote-approval/components/QuoteLineItemRow.tsx` | Single row. In review mode: shows amber/green/red tint from `<DiffView>`. Has per-row comment button and revert-change button (owner only). |
| `QuoteApprovalActionBar` | `features/quote-approval/components/QuoteApprovalActionBar.tsx` | Bottom action bar: **Approve**, **Approve with N edits**, **Kick back**, **Reject**. RBAC-gated to `quote.approve`. "Approve with N edits" is disabled when no pending edits exist; "Approve" is the default. |
| `MarginDeltaDisplay` | `features/quote-approval/components/MarginDeltaDisplay.tsx` | Shows current projected margin with struck-through pre-edit margin. Per approval spec §11. |
| `KickbackCommentModal` | `features/quote-approval/components/KickbackCommentModal.tsx` | Modal for kickback action. Contains overall comment textarea (required) + per-line-item comment thread (optional). Calls POST `/api/v1/quotes/{id}/kickback`. |
| `RejectCommentModal` | `features/quote-approval/components/RejectCommentModal.tsx` | Modal for reject action. Overall comment textarea (required). Calls POST `/api/v1/quotes/{id}/reject`. |
| `QuoteActivityTab` | `features/quote-approval/components/QuoteActivityTab.tsx` | Renders the audit log: submitted, reviewed, edited, approved, sent events per quote. |
| `QuoteChangesTab` | `features/quote-approval/components/QuoteChangesTab.tsx` | Tech-facing view: renders `<DiffView variant="quote-line">` showing what owner modified (post-approval). Only visible when quote has a prior `pending_approval` version. |
| `EditOnWebDeepLink` | `features/quote-approval/components/EditOnWebDeepLink.tsx` | Mobile "Open this quote on web for full editing" link used on mobile owner approval surface. |

**Surface-scoped hooks** (`features/quote-approval/hooks/`):

| Hook | Purpose |
|:---|:---|
| `usePendingQuotes.ts` | TanStack Query: `GET /api/v1/quotes/pending-approval` with filter params |
| `useQuoteDetail.ts` | TanStack Query: `GET /api/v1/quotes/{id}` with `include_pending_edits=true` |
| `useQuoteApprove.ts` | Mutation: `POST /api/v1/quotes/{id}/approve`, composes `useStalenessRetry()` |
| `useQuoteKickback.ts` | Mutation: `POST /api/v1/quotes/{id}/kickback` |
| `useQuoteReject.ts` | Mutation: `POST /api/v1/quotes/{id}/reject` |

---

### A.3 Mobile Surface Components — `apps/mobile/features/quote-approval-status/`

Tech-side pending quotes status surface. Read-only status view (no approval editing on mobile for MVP tech role). Owner mobile approval is a stretch — see §G.2.

| Component | File | Purpose |
|:---|:---|:---|
| `TechPendingQuotesList` | `features/quote-approval-status/TechPendingQuotesList.tsx` | Mobile list of tech's submitted quotes with status pill. |
| `TechQuoteStatusCard` | `features/quote-approval-status/components/TechQuoteStatusCard.tsx` | Single card: quote number, customer, total, status pill (pending/approved/kicked-back/rejected), submitted timestamp. |
| `TechQuoteStatusDetail` | `features/quote-approval-status/TechQuoteStatusDetail.tsx` | Tap → see kickback comments, owner annotations, and approve/reject rationale. Renders `<QuoteChangesTab>` when approved-with-edits. |
| `QuoteStatusPill` | `features/quote-approval-status/components/QuoteStatusPill.tsx` | Reusable status badge: maps `quote.status` → label + color token. |
| `KickbackCommentThread` | `features/quote-approval-status/components/KickbackCommentThread.tsx` | Renders kickback annotations (overall + per-line comments from owner). Uses `annotation_type` to organize display. |

**Surface-scoped hooks** (`features/quote-approval-status/hooks/`):

| Hook | Purpose |
|:---|:---|
| `useTechQuotes.ts` | TanStack Query: `GET /api/v1/quotes?submitted_by=me&status=pending_approval,approved,rejected,draft` |
| `useQuoteApprovalComments.ts` | TanStack Query: `GET /api/v1/quotes/{id}/comments` |

---

### A.4 Voice Approval Integration — `apps/mobile/features/voice-approval/` and `apps/web/features/voice-approval/`

Thin composition layer over existing FE-B3 patterns. No new shared components — only wires existing `<VoiceConfirmTurn>` from `packages/ui/src/voice-confirm-turn/` to the approval action API calls.

| Component | File | Purpose |
|:---|:---|:---|
| `VoiceApprovalHandler` | `features/voice-approval/VoiceApprovalHandler.tsx` (both platforms) | Listens for `approve_quote`, `reject_quote`, `request_quote_edits` intents from the voice session event stream. Composes `<VoiceConfirmTurn>` before calling the approval API. |

---

## B. Execution Order

| # | Item | Rationale |
|:---|:---|:---|
| 1 | **`<DiffView>` shared component** (cross-platform) | Foundation. Every FE-B5 surface uses it. FE-B8 and FE-B9 will import it directly. Must be implemented and exported from barrel before any approval surface composes it. |
| 2 | **`useApproveWithEdits()` shared hook** | Used by `QuoteLineItemTable` and `QuoteApprovalActionBar`. Depends on `<DiffView>` being defined (its `renderConflictContent` slot passes a `<DiffView>` to `useStalenessRetry()`). |
| 3 | **Pending quotes inbox (web)** — `PendingQuotesInboxPage` + `PendingQuoteCard` + `PendingInboxFilterBar` | Owner's entry point. Implement before detail page so routing is verified end-to-end. |
| 4 | **Quote detail with approval action bar (web)** — `QuoteDetailPage` + `QuoteReviewModeBar` + `QuoteApprovalActionBar` | Core approval surface. Composes `<DiffView>` and `useApproveWithEdits()`. |
| 5 | **Quote line item table with track-changes rendering** — `QuoteLineItemTable` + `QuoteLineItemRow` + `MarginDeltaDisplay` | Implements the inline editing + pending-edit staging + `<DiffView>` composition. Most complex component in the batch. |
| 6 | **Kickback / Reject flows** — `KickbackCommentModal` + `RejectCommentModal` | Depends on item 4's action bar. Short: modal UI + one API call each. |
| 7 | **Tech-side mobile status** — `TechPendingQuotesList` + `TechQuoteStatusCard` + `TechQuoteStatusDetail` + `KickbackCommentThread` | Depends on approval endpoints being mocked (MSW). Standalone mobile surface. |
| 8 | **`QuoteChangesTab` + `QuoteActivityTab`** | Depends on item 4's `QuoteDetailPage` tab shell. Reads `GET /api/v1/quotes/{id}/comments`. |
| 9 | **Voice approval integration** — `VoiceApprovalHandler` (web + mobile) | Last. Thin composition layer over FE-B3 voice patterns + items 4–6. Requires items 4–6 to be stable. |
| 10 | **Tenant setting `require_approval_for_tech_quotes` OFF path** | Final. Cross-cutting concern: remove approval UI affordances from all surfaces when OFF. Validate via MSW handler returning `require_approval = false` in the tenant settings response. |

---

## C. New Routes

### Web (Next.js App Router)

| Route File | URL Pattern | Auth | Permission Gate | Purpose |
|:---|:---|:---|:---|:---|
| `apps/web/src/app/(authed)/quotes/pending/page.tsx` | `/quotes/pending` | Required | `<RoleGate role="owner">` wrapping entire page | Owner pending quotes inbox |
| `apps/web/src/app/(authed)/quotes/[id]/page.tsx` | `/quotes/[id]` | Required | Auth required; action bar gated to `<RoleGate role="owner">` | Quote detail (unified — owner sees approval actions, tech sees status) |
| `apps/web/src/app/(authed)/quotes/[id]/approve/page.tsx` | `/quotes/[id]/approve` | Required | `<RoleGate role="owner">` | Direct deep-link to quote in approval mode (resolves to same `QuoteDetailPage` with `mode=review`) |

**Route placement note**: The existing `/quotes/page.tsx` stub remains as-is for now — it becomes the general quotes list. The pending inbox is a sub-route `/quotes/pending`. This creates a clean IA: `/quotes` = all quotes, `/quotes/pending` = owner's approval queue, `/quotes/[id]` = detail.

**Top-nav update**: `/quotes/pending` gets a badge in the web navigation (shows count of pending quotes for owners) — wired to the `usePendingQuotes()` hook result length.

### Mobile (Expo Router)

| Route File | URL Pattern | Auth | Permission Gate | Purpose |
|:---|:---|:---|:---|:---|
| `apps/mobile/app/(tabs)/(home)/quotes/pending.tsx` | `(home)/quotes/pending` | Required | None — tech role only sees their own submitted quotes | Tech-side pending quotes status list |
| `apps/mobile/app/(tabs)/(home)/quotes/[id].tsx` | `(home)/quotes/[id]` | Required | None (reads own quotes only) | Tech-side quote detail with status + comments |
| `apps/mobile/app/(tabs)/owner.tsx` | `(tabs)/owner` | Required | `<RoleGate role="owner">` (already exists) | Owner tab — gets pending quote count badge added to existing owner tab |

**Mobile owner approval note**: The mobile approval surface (owner side) uses the `(tabs)/owner` tab as the entry point. The pending quote count badge appears on the owner tab when `require_approval_for_tech_quotes = true`. Full line-item editing on mobile is in-scope per the spec's capability parity decision, but the implementation is the same route/component — `TechQuoteStatusDetail` is tech-side; the owner mobile path reuses `QuoteDetailPage` logic adapted for mobile (this is FE-B5 scope, not deferred).

---

## D. API Endpoint Consumption

All endpoints confirmed present in `frontend/packages/shared-types/src/api-schema.d.ts` as of current `pnpm sync-api-types` output.

| Method | Endpoint | Operation ID | TanStack Query Hook | MSW Handler |
|:---|:---|:---|:---|:---|
| `GET` | `/api/v1/quotes/pending-approval` | `list_pending_approval_quotes_api_v1_quotes_pending_approval_get` | `usePendingQuotes()` (surface-scoped) | `apps/web/mocks/handlers/quotes.ts` |
| `GET` | `/api/v1/quotes/{id}` | (existing) | `useQuoteDetail(id)` (surface-scoped) | (existing quote handler; extend with `pending_approval` status) |
| `POST` | `/api/v1/quotes/{id}/approve` | `approve_quote_api_v1_quotes__id__approve_post` | `useQuoteApprove(id)` (surface-scoped) | `apps/web/mocks/handlers/quotes.ts` |
| `POST` | `/api/v1/quotes/{id}/reject` | `reject_quote_api_v1_quotes__id__reject_post` | `useQuoteReject(id)` | `apps/web/mocks/handlers/quotes.ts` |
| `POST` | `/api/v1/quotes/{id}/kickback` | `kickback_quote_api_v1_quotes__id__kickback_post` | `useQuoteKickback(id)` | `apps/web/mocks/handlers/quotes.ts` |
| `GET` | `/api/v1/quotes/{id}/pending-edits` | `list_pending_edits_api_v1_quotes__id__pending_edits_get` | Part of `useApproveWithEdits()` | `apps/web/mocks/handlers/quotes.ts` |
| `POST` | `/api/v1/quotes/{id}/pending-edits` | `create_pending_edit_api_v1_quotes__id__pending_edits_post` | Part of `useApproveWithEdits()` | `apps/web/mocks/handlers/quotes.ts` |
| `PATCH` | `/api/v1/quotes/{id}/pending-edits/{edit_id}` | `update_pending_edit_api_v1_quotes__id__pending_edits__edit_id__patch` | Part of `useApproveWithEdits()` | `apps/web/mocks/handlers/quotes.ts` |
| `DELETE` | `/api/v1/quotes/{id}/pending-edits/{edit_id}` | `delete_pending_edit_api_v1_quotes__id__pending_edits__edit_id__delete` | Part of `useApproveWithEdits()` | `apps/web/mocks/handlers/quotes.ts` |
| `DELETE` | `/api/v1/quotes/{id}/pending-edits` | `delete_all_pending_edits_api_v1_quotes__id__pending_edits_delete` | Part of `useApproveWithEdits()` (cancel all) | `apps/web/mocks/handlers/quotes.ts` |
| `GET` | `/api/v1/quotes/{id}/comments` | `get_quote_comments_api_v1_quotes__id__comments_get` | `useQuoteApprovalComments(id)` | `apps/web/mocks/handlers/quotes.ts` + `apps/mobile/mocks/handlers/quotes.ts` |
| `GET` | `/api/v1/quotes?submitted_by=me&status=…` | (existing list w/ filter params) | `useTechQuotes()` (mobile surface-scoped) | `apps/mobile/mocks/handlers/quotes.ts` |

**MSW handler file**: `apps/web/mocks/handlers/quotes.ts` — create new file. `apps/mobile/mocks/handlers/quotes.ts` — create new file. Both are added to their respective `mocks/handlers/index.ts` registries.

**Staleness check field**: All approval mutation endpoints accept `expected_quote_version_id?: string | null` (confirmed in `api-schema.d.ts` at lines 13930, 13997, 14102, 14360). The `useStalenessRetry()` hook is wired with this field as the version key.

**Voice intent handlers** (no direct HTTP consumption — routed through voice session WebSocket):
- `approve_quote` → `approve_quote_via_voice` (§6.2) — confirm-as-turn → `POST /api/v1/quotes/{id}/approve`
- `reject_quote` → `reject_quote_via_voice` — confirm-as-turn → `POST /api/v1/quotes/{id}/reject`
- `request_quote_edits` → `request_quote_edits_via_voice` — confirm-as-turn → `POST /api/v1/quotes/{id}/kickback`
- `list_pending_quotes` (implied by spec) — query intent → `GET /api/v1/quotes/pending-approval` (no confirm-as-turn needed — read-only)

**MSW WebSocket mock extension**: extend existing `apps/mobile/mocks/handlers/voice.ts` with approval intent event sequences (mock `intent_detected: approve_quote` → `response_streaming` confirmation prompt → user says "yes" → `action_committed`).

---

## E. Pattern Reuse Decisions

### E.1 `<VoiceConfirmTurn>` from FE-B3

**Import**: `import { VoiceConfirmTurn } from '@pilot/ui/voice-confirm-turn'`

**Usage in FE-B5**: `VoiceApprovalHandler` renders `<VoiceConfirmTurn>` when a `pending_confirmation` state is detected in the voice session context for `approve_quote`, `reject_quote`, or `request_quote_edits` intents.

**Implementation note**: `VoiceConfirmTurn.tsx` is currently a React Native component (uses `View`, `Pressable`, `StyleSheet`). For web voice approval (owner on desktop), the web variant in `packages/ui/src/voice-confirm-turn/web/VoiceConfirmTurn.tsx` must be verified to exist from FE-B3. If the web variant was not built in FE-B3 (mobile-only batch), FE-B5 creates `packages/ui/src/voice-confirm-turn/web/VoiceConfirmTurn.tsx` using shadcn/Tailwind primitives — same props interface, platform-appropriate implementation.

**Exact import path**: `import { VoiceConfirmTurn, useVoiceConfirmation } from '@pilot/ui/voice-confirm-turn'` (subpath export per `packages/ui/package.json`).

---

### E.2 `useStalenessRetry()` + `<StalenessRefreshDialog>` from FE-B4

**Import**: `import { useStalenessRetry } from '@pilot/ui/hooks'`

**Usage in FE-B5**:

```tsx
// Inside useApproveWithEdits() or QuoteApprovalActionBar:
const { mutate: approveQuote, StalenessDialog } = useStalenessRetry({
  mutationFn: (vars) =>
    apiClient.post(`/api/v1/quotes/${quoteId}/approve`, vars),
  onConflict: (refreshedState, prevVars) => ({
    ...prevVars,
    expected_quote_version_id: refreshedState.quote_version_id,
  }),
  renderConflictContent: ({ refreshedState }) => (
    <DiffView
      variant="quote-line"
      baseline={prevApprovalSnapshot}
      modified={refreshedState.line_items}
    />
  ),
});
```

The `renderConflictContent` slot in `useStalenessRetry()` was specifically designed for FE-B5 (per `useStalenessRetry.ts` comment: "Used by FE-B5+ to render `<DiffView>`"). This is the first batch to use that slot.

**Staleness scenario**: Owner is reviewing a quote (has staged pending edits) when the tech resubmits an amended version. The backend returns 409 with a refreshed `quote_version`. The `StalenessDialog` shows a `<DiffView variant="quote-line">` of what changed, and the owner decides to retry their approval against the new version or cancel.

---

### E.3 `useSseChannel()` from FE-B4

**Import**: `import { useSseChannel } from '@pilot/ui/hooks'`

**Usage**: Not a primary concern for FE-B5 (quote approval is primarily request/response, not SSE-driven). However, the pending quotes inbox should refresh when a new quote is submitted. Wire `useSseChannel('/schedule/board/stream')` or a quotes-specific SSE channel if BE-B1 provides one. If no SSE endpoint for quotes, use TanStack Query `refetchInterval` of 30s as fallback for the pending inbox. **This is a minor dependency — do not block implementation on it.**

---

### E.4 `CONFLICT_CLASS_TOKENS` from FE-B4

**Import**: `import { CONFLICT_CLASS_TOKENS } from '@pilot/ui/conflict-severity'`

Not directly used in FE-B5 approval flow (conflict severity classes are for dispatch/calendar/offline conflicts, not quote approval states). Quote approval uses its own amber/green/red diff vocabulary from §16.2. Do not conflate these two systems.

---

## F. Shared Module Interfaces

### F.1 `<DiffView>` — FULL TypeScript Interface (LOCKED — FE-B8 and FE-B9 must consume this without changes)

**File**: `packages/ui/src/diff-view/types.ts`

```typescript
// packages/ui/src/diff-view/types.ts
// ⚠️ LOCKED — established FE-B5. FE-B7 ("entity"), FE-B8 ("calendar-event"), FE-B9 ("qb-entity")
// import and compose this interface. Adding optional props is acceptable;
// renaming or removing existing props is NOT permitted without a multi-batch impact review.

/**
 * The four valid variant values.
 *
 * "quote-line"     → FE-B5: owner diff of quote line items pre/post edit
 * "calendar-event" → FE-B8: Pilot-vs-external calendar event diff
 * "qb-entity"      → FE-B9: Pilot-vs-QB entity diff (customer, quote, invoice, expense)
 * "entity"         → FE-B7: generic mobile sync conflict entity diff (requires_review class)
 */
export type DiffViewVariant =
  | 'quote-line'
  | 'calendar-event'
  | 'qb-entity'
  | 'entity';

/**
 * A single field diff entry. Normalizes the §16.2 server-computed payload and the
 * FE-B5 client-side quote pending-edit representation into a common shape.
 *
 * §16.2 server payload uses pilot_value / external_value / base_value (for integrations).
 * quote_pending_edit uses old_value / new_value (for approval review).
 * Both map into this single DiffField interface.
 */
export interface DiffField {
  /** The machine-readable field name (e.g., "unit_price_cents", "scheduled_start_at") */
  fieldName: string;

  /**
   * Human-readable label. When omitted, DiffView generates one from fieldName
   * (snake_case → Title Case with domain-specific overrides per variant).
   */
  label?: string;

  /**
   * The "before" value. For quote-line: old_value from quote_pending_edit.
   * For calendar/qb: pilot_value or base_value from §16.2 server payload.
   * null means "this field did not exist before" (added case → green).
   */
  baseValue: string | number | boolean | null;

  /**
   * The "after" value.
   * For quote-line: new_value from quote_pending_edit.
   * For calendar/qb: external_value or modified_value from §16.2 server payload.
   * null means "this field was removed" (deleted case → red).
   */
  modifiedValue: string | number | boolean | null;

  /**
   * Explicit change type override. When provided, overrides the auto-derived type.
   * When absent, DiffView derives: baseValue=null → "added"; modifiedValue=null → "removed";
   * values equal → "unchanged"; else → "modified".
   */
  changeType?: 'unchanged' | 'modified' | 'added' | 'removed';

  /**
   * Optional: annotation text appended below the field value pair.
   * Used for owner comments per line in kickback mode; also used for
   * "Added by Owner" / "Removed by Owner" auto-annotations.
   */
  annotation?: string;

  /**
   * For quote-line variant only: the UUID of the quote_pending_edit row that
   * produced this diff. Required when onRevertField is provided. Ignored for
   * calendar-event and qb-entity variants.
   */
  pendingEditId?: string;
}

/**
 * A single line item with its associated field diffs. Used by "quote-line" variant.
 * Represents one quote_line row (customer-visible or internal cost-tracking).
 */
export interface DiffLineItem {
  /** UUID of the quote_line row */
  lineItemId: string;

  /**
   * Display label for this line item (description or section header text).
   * Shown above the field diffs.
   */
  label: string;

  /**
   * Whether this line item is customer-visible (per quote-line-item-architecture.md).
   * Internal cost-tracking lines are rendered with a subdued visual treatment.
   */
  customerVisible: boolean;

  /**
   * change type for the entire line: "added" (new line owner added),
   * "removed" (line marked for deletion), "modified" (existing line with field edits),
   * "unchanged" (no edits on this line — included for context).
   */
  lineChangeType: 'added' | 'removed' | 'modified' | 'unchanged';

  /** The individual field diffs within this line. Empty array for unchanged lines. */
  fields: DiffField[];
}

/**
 * Full props interface for <DiffView>.
 *
 * The three variant shapes correspond to:
 * - "quote-line": uses lineItems[] (client-constructed from quote_pending_edit rows)
 * - "calendar-event" | "qb-entity": uses fieldDiffs[] (server-computed §16.2 payload)
 * - "entity": uses fieldDiffs[] (mobile sync conflict, server-computed BE-B7b/A40)
 */
export type DiffViewProps =
  | QuoteLineDiffViewProps
  | IntegrationDiffViewProps
  | EntityDiffViewProps;

/**
 * Props for variant="quote-line" (FE-B5 owner approval diff).
 * Used inline within QuoteLineItemTable — one DiffView instance per modified line.
 */
export interface QuoteLineDiffViewProps {
  variant: 'quote-line';

  /**
   * The structured line items to render. Include ALL lines (not just changed ones)
   * so unchanged lines provide context. Lines with lineChangeType="unchanged" render
   * with neutral background.
   */
  lineItems: DiffLineItem[];

  /**
   * When provided, each modified/removed field renders a "Revert this change" button.
   * Callback receives the pendingEditId of the DiffField. Only valid for variant="quote-line".
   */
  onRevertField?: (pendingEditId: string) => void;

  /**
   * Mobile "Show changes / Hide changes" toggle. Default: false (no toggle; always shows diffs).
   * Set to true for mobile owner approval surface per spec §4.
   */
  showToggle?: boolean;

  /** Initial visibility when showToggle=true. Default: true (changes visible). */
  defaultShowChanges?: boolean;

  /** Test ID for e2e and unit tests */
  testID?: string;
}

/**
 * Props for variant="calendar-event" (FE-B8) or "qb-entity" (FE-B9).
 * Consumes the server-computed §16.2 field_diffs payload directly.
 */
export interface IntegrationDiffViewProps {
  variant: 'calendar-event' | 'qb-entity';

  /**
   * Server-computed §16.2 field_diffs payload.
   * fieldName, pilot_value, external_value, base_value, pilot_change, external_change
   * are mapped to DiffField's baseValue/modifiedValue/changeType.
   *
   * For FE-B8/B9 the caller maps from the raw API response using the
   * `normalizeSectionFieldDiffs()` utility exported from packages/ui/src/diff-view/utils.ts.
   */
  fieldDiffs: DiffField[];

  /**
   * Human-readable label for the entity being compared.
   * Shown as the section heading.
   * e.g., "Johnson Panel Upgrade — April 30, 9:00 AM" for calendar-event.
   */
  entityLabel: string;

  /**
   * Labels for the two sides of the diff.
   * Default for "calendar-event": { base: 'Pilot', modified: 'Google Calendar' }
   * Default for "qb-entity": { base: 'Pilot', modified: 'QuickBooks' }
   * Overrideable for custom contexts.
   */
  sideLabels?: { base: string; modified: string };

  /** Test ID for e2e and unit tests */
  testID?: string;
}

/**
 * Props for variant="entity" (FE-B7 mobile offline sync conflict review).
 * Simplified integration version without side labels.
 */
export interface EntityDiffViewProps {
  variant: 'entity';

  /** Server-computed field diffs from BE-B7b/A40 conflict detail. */
  fieldDiffs: DiffField[];

  /** Entity display name (e.g., "Time Entry — Mon, 4.5 hrs") */
  entityLabel: string;

  /** Test ID */
  testID?: string;
}
```

**Utility exports** (`packages/ui/src/diff-view/utils.ts`):

```typescript
// packages/ui/src/diff-view/utils.ts

/**
 * Normalizes a raw §16.2 server field_diffs array into DiffField[].
 * Used by FE-B8 and FE-B9 to map from API response to <DiffView> props.
 */
export function normalizeFieldDiffs(
  rawDiffs: Array<{
    field_name: string;
    pilot_value: unknown;
    external_value: unknown;
    base_value: unknown;
    pilot_change: 'unchanged' | 'modified' | 'added' | 'removed';
    external_change: 'unchanged' | 'modified' | 'added' | 'removed';
  }>,
  perspective: 'pilot' | 'external' = 'external',
): DiffField[];

/**
 * Converts quote_pending_edit rows into DiffLineItem[] for <DiffView variant="quote-line">.
 * Used by QuoteLineItemTable to build the diff from the pending edits API response.
 */
export function buildQuoteLineDiff(params: {
  allLines: QuoteLineResponse[];
  pendingEdits: QuotePendingEditResponse[];
}): DiffLineItem[];
```

---

### F.2 `useApproveWithEdits()` — Hook Interface

**File**: `packages/ui/src/hooks/useApproveWithEdits.ts`

```typescript
// packages/ui/src/hooks/useApproveWithEdits.ts

export interface UseApproveWithEditsOptions {
  quoteId: string;
  quoteVersionId: string;
  onSuccess?: (response: QuoteApproveResponse) => void;
  onError?: (error: unknown) => void;
}

export interface UseApproveWithEditsReturn {
  /** Stage a field-level edit. Creates or updates a quote_pending_edit row. */
  stagePendingEdit: (params: QuotePendingEditCreate) => Promise<QuotePendingEditResponse>;

  /** Revert a single pending edit by its edit_id. */
  revertPendingEdit: (editId: string) => Promise<void>;

  /** Cancel all pending edits for this reviewer (DELETE all). */
  cancelAllEdits: () => Promise<void>;

  /** Current pending edits for the current reviewer. */
  pendingEdits: QuotePendingEditResponse[];

  /** Whether any pending edits have been staged. */
  hasPendingEdits: boolean;

  /** Commit all pending edits and approve. Wraps useStalenessRetry(). */
  approveWithEdits: () => void;

  /** Approve without applying any edits. Also wraps useStalenessRetry(). */
  approveAsIs: () => void;

  /** True when approval mutation is in-flight. */
  isApproving: boolean;

  /** True when staging/reverting edits. */
  isStagingEdit: boolean;

  /**
   * The staleness dialog component from useStalenessRetry().
   * Must be rendered in the same component tree.
   */
  StalenessDialog: React.FC;
}
```

---

### F.3 Barrel Export Additions (to `packages/ui/src/index.ts`)

Add a new `// ── FE-B5 Exports ──` section to `packages/ui/src/index.ts` after the FE-B4 section:

```typescript
// ── FE-B5 Exports ─────────────────────────────────────────────────────────────
// DiffView is the canonical track-changes diff renderer (§16.2).
// Consumed by FE-B7 (entity), FE-B8 (calendar-event), FE-B9 (qb-entity).
// ⚠️ Interface locked — changes require FE-B7/B8/B9 impact review.

export { DiffView } from './diff-view';
export type {
  DiffViewProps,
  DiffViewVariant,
  DiffField,
  DiffLineItem,
  QuoteLineDiffViewProps,
  IntegrationDiffViewProps,
  EntityDiffViewProps,
} from './diff-view/types';
export { normalizeFieldDiffs, buildQuoteLineDiff } from './diff-view/utils';

export { useApproveWithEdits } from './hooks/useApproveWithEdits';
export type {
  UseApproveWithEditsOptions,
  UseApproveWithEditsReturn,
} from './hooks/useApproveWithEdits';
```

**`package.json` subpath export** (add to `packages/ui/package.json` `"exports"` field):
```json
"./diff-view": {
  "react-native": "./src/diff-view/mobile/index.ts",
  "default": "./src/diff-view/web/index.ts"
}
```

---

## G. Open Questions Resolved

### G.1 `<DiffView>` component API — locked interface

**Decision**: The full TypeScript props interface is defined in §F.1 above. It is locked.

Key decisions within the interface:
- **Polymorphic via `variant` prop** using a discriminated union — same pattern as `<EmptyState type="...">` from FE-B1.
- **`"quote-line"` uses `lineItems: DiffLineItem[]`** (client-constructed from `quote_pending_edit` rows) rather than the server-side `field_diffs` format, because quote approval pending edits are staged client-side incrementally as the owner makes changes.
- **`"calendar-event"` and `"qb-entity"` use `fieldDiffs: DiffField[]`** (directly from server-computed §16.2 payload via `normalizeFieldDiffs()` utility).
- **`"entity"` uses `fieldDiffs: DiffField[]`** (from BE-B7b/A40 mobile conflict detail) — same shape as calendar/qb variants.
- **`onRevertField` is `"quote-line"`-only** — calendar and QB conflicts have their own resolution mechanism, not per-field revert.
- **`showToggle`** enables the mobile "Show changes / Hide changes" affordance per spec §4.

---

### G.2 `<DiffView>` platform scope

**Decision**: Cross-platform with web and mobile implementations at `packages/ui/src/diff-view/web/` and `packages/ui/src/diff-view/mobile/`, resolved via `package.json` `"exports"` condition. Single shared `types.ts`.

**Rationale**: FE-B7 explicitly requires a mobile `<DiffView variant="entity">` in mobile conflict resolution screens (see `pilot-app-mvp-frontend-impl-plan.md`). The web implementation uses Tailwind utility classes and shadcn `Badge`/`Tooltip` primitives. The mobile implementation uses React Native `View`/`Text` + Gluestack tokens. The props interface is identical — platform difference is purely visual implementation.

**Owner approval mobile web escalation**: The mobile owner approval surface (owner reviewing on phone) uses the mobile `<DiffView>` implementation. Per spec §5, a "More edits to make? Open on web →" deep-link is included for owners who want full editing ergonomics.

---

### G.3 Pending quotes inbox layout

**Decision**: Dedicated sub-route `/quotes/pending` under the existing `/quotes` section.

**Rationale**: A query-param approach (`/quotes?status=pending_approval`) would require the general quotes list page to handle both list-all and approval-queue modes. The pending approval queue has distinct affordances (bulk actions planned for Phase 2, filter bar for tech/customer/age, urgency indicators). A dedicated route gives it a clean URL and a clean component boundary.

**Navigation**: A "Pending Approval" item is added to the `/quotes` section sidebar nav (web). The count badge (`N pending`) is visible in the navigation. When `require_approval_for_tech_quotes = false` OR the logged-in user is not an owner, the "Pending Approval" nav item is hidden via `<RoleGate>`.

---

### G.4 Quote detail web view structure

**Decision**: Single `/quotes/[id]` route with role-based conditional rendering. The same `QuoteDetailPage` renders for both owner and tech, with role-gated components:

- `<QuoteReviewModeBar>` — visible to owner when `quote.status === 'pending_approval'`
- `<QuoteApprovalActionBar>` — visible to owner, hidden from tech via `<RoleGate role="owner">`
- **Changes tab**: visible to tech after approval (when `quote.has_owner_edits === true`); visible to owner always when viewing an approved quote with edits
- **Activity tab**: visible to all roles

**Rationale**: The spec explicitly states the approval surface is "essentially the quote editor with an approval-mode affordance bar" (spec §1). A single parameterized component with role-gated sections is cleaner than two separate route variants.

---

### G.5 Approve-with-edits atomic write UX

**Decision**: Inline table editing with track-changes rendering (not a modal).

**Flow**:
1. Owner clicks a line item field → inline edit input appears in `QuoteLineItemRow`
2. On blur, `stagePendingEdit()` fires → `POST /api/v1/quotes/{id}/pending-edits` → row in `quote_pending_edit` table
3. `QuoteReviewModeBar` updates: "1 pending edit" → "2 pending edits" etc.
4. `QuoteLineItemTable` re-renders the edited field with amber track-changes treatment via `<DiffView variant="quote-line">`
5. Owner clicks **Approve with N edits** → single atomic commit: `POST /api/v1/quotes/{id}/approve` with `apply_pending_edits: true` in the request body
6. Backend atomically: applies all `quote_pending_edit` rows → creates new `quote_version` → deletes `quote_pending_edit` rows → sets `quote.status = 'approved'`
7. UI shows success state; redirect to updated quote detail (clean view, no diff markers)

**No intermediate half-applied state visible**: the atomic backend commit (step 6) ensures the quote is never in a state where some edits are applied and some aren't. If the backend returns an error, all pending edits remain staged and the owner can retry.

---

### G.6 Kickback/reject comment audience

**Decision**: All kickback and rejection comments are tech-visible. Owner-only notes are NOT supported in MVP.

**Rationale**: The `quote_approval_annotation` schema (mvp-arch §14.4) has `annotation_type` (`'line_item' | 'header' | 'overall'`) but NO audience field. Adding an audience field is a backend schema change outside FE-B5 scope. Per the "do not invent endpoint shapes" rule (react-engineer-methods §10.1), the UI cannot implement an audience toggle that has no backend support. All kickback comments are tech-visible — this is the correct behavior (the point of kickback is to communicate with the tech). Owner-only notes are Phase 2.

**UI**: `KickbackCommentModal` has:
- "Overall comment" textarea (required — at least this or a line comment must be present per API: `Requires at least one of overall_comment or line_comments`)
- Per-line comment button on each `QuoteLineItemRow` in kickback mode (optional)
- No audience selector

---

### G.7 Tenant setting `require_approval_for_tech_quotes` OFF path

**Decision**: When `require_approval_for_tech_quotes = false`, the pending quotes inbox shows `<EmptyState type="not-yet-set-up">` with explanatory copy: *"Approval workflow is disabled. Quotes submitted by your team go directly to customers."* A link to Settings lets the owner enable it. No separate code branch — the empty state handles the UX gracefully.

**Quote submission button label**: When the setting is OFF, the mobile tech's quote submission button reads **"Send to Customer"** (not "Submit for Approval"). The label is conditionally set based on the tenant setting resolved at page load. The tech never sees a `pending_approval` state in their quote list when the setting is OFF.

**Implementation**: The tenant setting is included in the quote detail API response as `require_approval` boolean (or resolved from the tenant-settings endpoint). The `QuoteApprovalActionBar` checks this flag: if `false`, the bar does not render at all.

---

### G.8 Voice approval intent integration

**Decision**: Voice approval is surfaced through the **global voice session** on both web and mobile. There is NO dedicated mic button on the pending quotes screen or quote detail page for FE-B5.

**Rationale**: The global voice session is already established (FE-B3's voice session infrastructure). Adding surface-specific mic buttons would fragment the voice UX and require per-surface voice session context wiring. The spec says "owners can voice-trigger approval actions from any Pilot surface" — this is exactly the global voice session behavior.

**Mobile tech-side**: The mobile tech has no approval voice intents — only the owner can `approve_quote`. The `list_pending_quotes` intent is owner-only and routed to show the pending approval count.

**`VoiceApprovalHandler` placement**: The handler component is mounted at the quote detail page level (web: `QuoteDetailPage`; mobile: accessible via the global voice session shell). It subscribes to the voice session event stream and when it detects `intent_detected: approve_quote | reject_quote | request_quote_edits` with a `quote_id` matching the current page, it renders `<VoiceConfirmTurn>` with the appropriate confirmation prompt.

**Line-item voice edits refused**: Per spec §12 constraint, voice cannot commit line-item edits. If the owner tries to describe a line edit via voice, the AI responds with a `refusal_with_redirect` pattern: "Voice can approve, reject, or kick back a quote, but line edits need to be done on the review screen." No `<VoiceConfirmTurn>` is rendered for edit intents — the AI response text alone handles it.

---

## H. External Dependency Status

| Dependency | Status | Mock Strategy | Owner Action |
|:---|:---|:---|:---|
| **BE-B1 (quote approval state machine)** | ⚠️ Backend gate — may be in flight | MSW handlers for all 11 approval endpoints listed in §D. Handler file: `apps/web/mocks/handlers/quotes.ts`. Mock returns realistic payloads including `QuotePendingEditResponse`, `QuoteApproveResponse`, `QuoteKickbackRequest`. | Coordinate with backend plan — check BE-B1 completion status before removing MSW handlers from integration tests. |
| **Push notifications (mobile quote status)** | ⚠️ APNs/FCM not configured for production | Mock push notification delivery in dev; `NotificationBanner` renders the in-app version. | Defer to when FE-B13 (push permission flow) ships. |
| **Voice session WebSocket (approval intents)** | ✅ Established in FE-B3 | MSW WebSocket handler extended with approval intent sequence in `apps/mobile/mocks/handlers/voice.ts` | No new action — reuses FE-B3 infrastructure. |
| **Cognito / auth** | ✅ MockAuthProvider active | `USE_MOCK_AUTH=true` — quote approval surfaces require `owner` role mock user | No action needed for FE-B5. |
| **OpenAI / embeddings** | ✅ Not consumed by FE-B5 | N/A | N/A |

**No new external dependencies** are introduced by FE-B5. All APIs consumed are within the existing backend (`/api/v1/quotes/...`).

---

## I. Test Plan

### I.1 Unit Tests (target: 60+)

**`packages/ui/src/diff-view/__tests__/DiffView.test.tsx`** (web) and **`DiffView.native.test.tsx`** (mobile):
- `variant="quote-line"`: renders amber for modified fields, green for added lines, red for removed lines
- `variant="quote-line"`: unchanged lines render with neutral background (no color tint)
- `variant="quote-line"`: per-field revert button calls `onRevertField` with correct `pendingEditId`
- `variant="quote-line"`: `showToggle=true` renders toggle; toggling hides/shows diff markers
- `variant="quote-line"`: `defaultShowChanges=false` renders clean view by default
- `variant="calendar-event"`: renders `sideLabels` correctly; uses pilot/external vocabulary
- `variant="qb-entity"`: renders `sideLabels` correctly; renders `entityLabel` as section heading
- `variant="entity"`: renders correctly on mobile without side labels
- All variants: ARIA live regions and accessibility labels set correctly
- All variants: Pass 1 color tokens used (no hardcoded hex values — ESLint `no-hardcoded-design-values` passes)
- `normalizeFieldDiffs()` utility: maps `pilot_change="modified"` → `changeType="modified"` correctly
- `normalizeFieldDiffs()` utility: maps `external_change="added"` + `pilot_change="unchanged"` → green treatment
- `buildQuoteLineDiff()` utility: groups `quote_pending_edit` rows by `affected_line_item_id` correctly
- `buildQuoteLineDiff()` utility: `edit_type="line_item_add"` produces `lineChangeType="added"`
- `buildQuoteLineDiff()` utility: `edit_type="line_item_remove"` produces `lineChangeType="removed"`

**`apps/web/src/features/quote-approval/components/__tests__/`**:
- `PendingQuoteCard.test.tsx`: renders all data fields; age display (minutes → hours → days)
- `PendingInboxFilterBar.test.tsx`: filter change fires callback; clear resets all filters
- `QuoteReviewModeBar.test.tsx`: renders pending edit count; "Cancel all edits" calls handler
- `QuoteApprovalActionBar.test.tsx`:
  - "Approve" enabled when no pending edits; "Approve with N edits" disabled (N=0)
  - "Approve with N edits" enabled when N>0; "Approve" hidden when N>0
  - All 3 action buttons call correct handlers
  - When `require_approval = false`: action bar does not render
  - When role is not owner: action bar does not render (via `<RoleGate>`)
- `MarginDeltaDisplay.test.tsx`: struck-through original margin + new projected margin render correctly; "below target" renders red token
- `KickbackCommentModal.test.tsx`: submit disabled when no comment; calls kickback handler; per-line comment populates `line_comments`
- `RejectCommentModal.test.tsx`: submit disabled when no comment; calls reject handler
- `QuoteStatusPill.test.tsx`: correct label and color token for each status

**`apps/web/src/features/quote-approval/hooks/__tests__/`**:
- `useApproveWithEdits.test.ts`: `hasPendingEdits` false initially; true after `stagePendingEdit()`; false after `cancelAllEdits()`; `approveWithEdits` calls mutate with `apply_pending_edits: true`

**`apps/mobile/features/quote-approval-status/components/__tests__/`**:
- `TechQuoteStatusCard.test.tsx`: status pill renders correct color per status
- `KickbackCommentThread.test.tsx`: `annotation_type="overall"` renders at top; `annotation_type="line_item"` renders under line label

**`apps/mobile/features/voice-approval/__tests__/`**:
- `VoiceApprovalHandler.test.tsx`: `approve_quote` intent renders `<VoiceConfirmTurn>` with correct prompt; confirm calls approve mutation; cancel clears intent; `request_quote_edits` intent with line-item edit detected renders refusal copy (no `<VoiceConfirmTurn>`)

### I.2 Integration Tests (target: 14+)

File: `apps/web/__tests__/batch_fe_b5/`

- `pending-quotes-inbox.integration.test.tsx`:
  - Owner loads `/quotes/pending` → MSW returns 3 pending quotes → all 3 `PendingQuoteCard` render
  - Filter by tech: only tech A's quotes shown
  - Empty state when `require_approval_for_tech_quotes = false` tenant setting
  - RBAC: tech role cannot access `/quotes/pending` → `<EmptyState type="permission-denied">` rendered (or redirect to `/quotes`)

- `quote-approve-flow.integration.test.tsx`:
  - Load quote detail in `pending_approval` status → action bar visible → click Approve → MSW 200 → success state (status pill changes to "Approved")
  - Staleness: approve call returns 409 → `StalenessDialog` opens with `<DiffView>` showing refreshed state → owner retries → success

- `quote-approve-with-edits.integration.test.tsx`:
  - Stage 2 edits → `QuoteReviewModeBar` shows "2 pending edits" → `DiffView` renders amber tint on 2 lines → click "Approve with 2 edits" → MSW returns new quote version → pending edits cleared → quote renders clean (no diff markers)
  - Revert single edit: stage edit → revert via revert button → pending edit count drops to 0 → amber tint removed
  - Cancel all edits: stage 2 edits → cancel → confirm dialog → all pending edits removed → quote renders clean

- `kickback-flow.integration.test.tsx`:
  - Click Kick Back → modal appears → submit without comment → submit button disabled
  - Add overall comment → submit → MSW 200 → modal closes → quote status changes to "Returned to tech" → tech notification queued
  - Mobile: tech opens quote after kickback → `KickbackCommentThread` shows owner comment

- `reject-flow.integration.test.tsx`:
  - Click Reject → modal → submit with comment → quote transitions to "Rejected" terminal state → action bar disappears

- `mobile-tech-status.integration.test.tsx`:
  - Tech opens `(home)/quotes/pending` → sees their submitted quotes with status pills
  - Tap an approved-with-edits quote → `QuoteChangesTab` renders `<DiffView>` showing owner's changes
  - Tap a kicked-back quote → `KickbackCommentThread` shows owner comment

- `voice-approval.integration.test.tsx`:
  - Mock WebSocket fires `intent_detected: approve_quote` → `<VoiceConfirmTurn>` renders with "Approve the Johnson quote?" → click Confirm → approve mutation fires → success
  - Mock voice intent for line edit → refusal copy renders; no `<VoiceConfirmTurn>`

- `staleness-approval.integration.test.tsx`:
  - Owner starts staging edits; second user (mocked) updates quote simultaneously → approve returns 409 → `StalenessDialog` opens → DiffView shows what changed → owner approves against new version → success

File: `apps/mobile/__tests__/batch_fe_b5/`

- `mobile-voice-approval.integration.test.tsx`: (mobile side) voice approval confirm-as-turn full flow

### I.3 E2E Tests (target: 3+)

**`e2e/web/batch_fe_b5/owner-approval-cycle.e2e.spec.ts`** (Playwright):
- Owner logs in → navigates to `/quotes/pending` → selects a quote → stages 2 edits → reviews `<DiffView>` amber markers → clicks "Approve with 2 edits" → quote status transitions to "Approved" → quote disappears from pending inbox

**`e2e/web/batch_fe_b5/kickback-cycle.e2e.spec.ts`** (Playwright):
- Owner logs in → opens pending quote → kicks back with comment → mobile tech (Maestro) receives push notification → taps → sees kickback comment in `KickbackCommentThread`

**`e2e/mobile/batch_fe_b5/tech-approval-status.e2e.test.ts`** (Maestro):
- Tech opens pending quotes list → submits new quote (via MSW approved instantly) → verifies "Approved" status pill appears → opens quote changes tab → verifies `<DiffView>` renders owner edits

### I.4 Accessibility Checkpoints

- `axe-core` run on `PendingQuotesInboxPage` → zero violations
- `axe-core` run on `QuoteDetailPage` in review mode → zero violations (diff color tints must also meet contrast ratios)
- `<DiffView>` amber/green/red markers: each color-coded field must also have a text label (not color-only) — "Modified", "Added", "Removed" text annotations are required per WCAG 1.4.1
- `KickbackCommentModal`: focus trapped inside modal when open; Escape key closes modal
- `QuoteApprovalActionBar`: all buttons reachable via Tab; focus order matches visual order

---

*Document produced by Pilot Architect mode from pre-implementation reads completed 2026-05-22. No implementation code written — handoff ready for Pilot React Engineer mode.*
