# Batch FE-B6 Design — Customer Comms Outbound (Pass 3 Flow 4)

**Version**: 1.0  
**Status**: Design Complete — Ready for Implementation  
**Date**: 2026-05-22  
**Batch**: FE-B6  
**Effort estimate**: 12–15 days  
**Test subfolder**: `apps/{web,mobile}/__tests__/batch_fe_b6/`

---

## Source Documents Reviewed

| Document | Sections Read |
|:---|:---|
| `pilot-app-mvp-frontend-impl-plan.md` | §6 FE-B6 batch detail (items, patterns, test focus) |
| `frontend-pass-3-flow-4-customer-comms-spec.md` | Full spec — 12 locked decisions |
| `mvp-arch.md` | §16.7 Always-Preview-Before-Send; §16.3 Confirm-as-Turn; §17.6 SMS Quota |
| `pilot-react-engineer-methods.md` | §8 Shared Component Catalog; §9.6 Always-preview; §12 Voice AI |
| `api-schema.d.ts` | All comms endpoints + schema types |
| `voice-confirm-turn/types.ts` | `VoiceConfirmTurnProps`, `UseVoiceConfirmationReturn` |
| `packages/ui/src/index.ts` | Confirmed FE-B5 is current tail; `MessagePreviewModal` absent |
| `(authed)/comms/page.tsx` | Bare stub — `<h1>Comms</h1>` only |
| `(authed)/customers/page.tsx` | Bare stub |
| `apps/mobile/app/(tabs)/` | `index.tsx`, `jobs.tsx`, `customers.tsx`, `calcs.tsx`, `owner.tsx` |

---

## A. Component Implementation Plan

All 9 items from the FE-B6 execution table, with expanded scope notes.

### A1 — `<MessagePreviewModal>` shared component
**Location**: `packages/ui/src/message-preview/MessagePreviewModal.tsx`  
**Exports from**: `packages/ui/src/index.ts` under `// ── FE-B6 Exports ──`

**Responsibility**: Renders a full-screen modal (mobile) or a centered dialog (web) showing:
- Rendered message body (from `CommunicationPreviewResponse.rendered_body`)
- Optional rendered subject (email only; null for SMS)
- Recipient name + address
- Channel pill with icon (chat-bubble = SMS, envelope = email)
- "Channel overridden" amber badge when `channel_override` is set
- Editable variable chips (amber-tinted, dashed border) per `editable_variables[]`
- "Edit" and "Cancel" buttons in addition to "Send to [name]"

**FE-B10 compatibility note**: Must support both template-based sends (`templateCode` present) and free-form sends (`templateCode` absent, `freeFormBody` present). The modal body field renders whichever is set. Segment count row is always shown for SMS channel.

**Does NOT exist yet**: confirmed absent from `packages/ui/src/index.ts` — FE-B6 creates it.

---

### A2 — `usePreviewBeforeSend()` hook
**Location**: `packages/ui/src/hooks/usePreviewBeforeSend.ts`  
**Exports from**: `packages/ui/src/index.ts` under `// ── FE-B6 Exports ──`

**Responsibility**: Encapsulates the full two-endpoint preview → send contract:
1. Calls `POST /api/v1/communications/preview` — returns rendered content
2. Opens `<MessagePreviewModal>` for user confirmation
3. On confirm: calls `POST /api/v1/communications/send` with same params
4. Enforces that send cannot happen without a prior preview call (see §G Decision 2)

**Does NOT exist yet**: confirmed absent from all frontend TypeScript files — FE-B6 creates it.

---

### A3 — Template selection UI
**Location (mobile)**: `apps/mobile/app/(tabs)/jobs/[jobId]/comms.tsx` (new route)  
**Location (web)**: `apps/web/src/app/(authed)/comms/_components/TemplatePickerPanel.tsx`

**Mobile**: 2×3 card grid per spec §Decision 3. Each card: intent icon + template name + one-line preview text. Above grid: amber-tinted voice CTA panel. Customer channel pill + override link above grid. Entry point: Job Detail primary action button "Communicate."

**Web**: Rendered as a side panel or sheet within the Customer detail Communications tab. Same card grid layout reused (shadcn-ui Card components).

---

### A4 — Channel override
**Location**: `apps/mobile/app/(tabs)/jobs/[jobId]/comms.tsx` inline (above template grid) + `<MessagePreviewModal>` (secondary override path in modal)

Appears in **two places** per spec §Decision 4:
- **Above the template grid** (primary): customer channel pill ("SMS preferred") + discreet link "Send via email instead →"
- **Inside `<MessagePreviewModal>`** (secondary): small "Change channel" link for post-preview adjustment

Override is **not persisted** to the customer record — carried only through hook state for this send operation.

---

### A5 — Communication history view
**Location (web)**: `apps/web/src/app/(authed)/customers/[id]/comms/page.tsx` (new subroute)  
**Location (mobile)**: `apps/mobile/app/(tabs)/customers/[id]/comms.tsx` (new route)

Chronological table of all messages sent to a customer. Columns: Time | Channel | Message | Status. Per-row metadata: template code pill, "voice-triggered" flag, "channel overridden" flag, delivery status.

The standalone `/comms` route (`(authed)/comms/page.tsx`) becomes a cross-customer comms summary (last N messages across all customers). This is minimal in FE-B6; FE-B10 extends it with inbound threading.

---

### A6 — Voice intent UI feedback
**Location (mobile)**: `apps/mobile/app/(tabs)/jobs/[jobId]/comms.tsx` voice overlay layer  
**Location (mobile shared)**: composites `<VoiceConfirmTurn>` from FE-B3 + `<MessagePreviewModal>` from this batch

Voice flow: voice intent → `POST /communications/preview` (server renders) → AI reads preview aloud → `<VoiceConfirmTurn>` prompt → on confirm → `POST /communications/send`. Each step is independently testable. See §G Decision 7 for time-extraction sequence.

---

### A7 — Customer disambiguation UI
**Location**: `packages/ui/src/message-preview/CustomerDisambiguationList.tsx`

Thin list component. Renders when voice or template selection matches multiple customers (e.g., two "Johnsons" in DB). Follows the priority chain in spec §Decision 9. AI never silently picks; always surfaces disambiguation before proceeding to preview.

---

### A8 — Time-extraction inline editor
**Location**: `packages/ui/src/message-preview/TimeExtractionEditor.tsx`

Pre-preview step shown when voice extracts a time variable ("20 out" → 20 minutes). Renders an editable time field (quick-pick scrollwheel: 5/10/15/20/30/45 min + Custom). User confirms or adjusts → variables are finalized → `POST /communications/preview` is called with confirmed variable values.

This step occurs **before** the preview call, not inside `<MessagePreviewModal>`. The amber-chip editable variables in `<MessagePreviewModal>` support post-preview re-adjustment (triggers a re-preview).

---

### A9 — `notification_outbox` status surfacing
**Location**: composited into the send success state within `usePreviewBeforeSend()`

After send, reuses `<NotificationBanner>` from FE-B1. Three states:
1. **Sending**: amber banner "Sending to [name]…"
2. **Sent**: green banner "Sent to [name] via SMS/email" (auto-dismiss 6s)
3. **Failed**: red banner "Message failed to send" with Retry CTA

Status derived from TanStack Query polling of `CommunicationSendResponse.status` via `GET /api/v1/customers/{id}/communications` (see §G Decision 8 for rationale — no SSE endpoint exists for comms delivery).

---

## B. Execution Order

| Step | Item | Rationale |
|:---|:---|:---|
| 1 | `<MessagePreviewModal>` + types | Foundation — all other items depend on this modal being defined |
| 2 | `usePreviewBeforeSend()` hook | Encapsulates the two-endpoint contract; template selection and voice path both consume this hook |
| 3 | Channel override (within hook state + modal) | Defined alongside hook; zero-cost addition at hook design time |
| 4 | Template selection UI (mobile + web) | User-facing entry point; consumes hook from step 2 |
| 5 | Communication history view (web + mobile) | Independent of send path; can be built in parallel with step 4 |
| 6 | Time-extraction inline editor | Pre-preview editing step; consumed by voice path (step 7) |
| 7 | Voice intent UI feedback (composes FE-B3 + this batch) | Composes all prior pieces; testable once steps 1–6 exist |
| 8 | Customer disambiguation UI | Thin layer; can be built alongside step 7 |
| 9 | `notification_outbox` status surfacing | Final closure of send loop; composes `<NotificationBanner>` from FE-B1 |

**Critical path**: items 1 → 2 → 4 gate all user-facing surfaces. Items 3, 5, 8, 9 are parallel-safe once item 2 is locked.

---

## C. New Routes

### Web routes (Next.js App Router)

| Route | File | Description |
|:---|:---|:---|
| `/customers/[id]` | `(authed)/customers/[id]/page.tsx` | Customer detail shell (layout with tabs) |
| `/customers/[id]/comms` | `(authed)/customers/[id]/comms/page.tsx` | **New** — per-customer communication history |
| `/comms` | `(authed)/comms/page.tsx` | **Expanded** from stub — cross-customer comms summary |

The `/customers/[id]` layout gets a tab bar: Overview | Jobs | Quotes | **Comms** | Invoices. The Comms tab renders `CommunicationHistoryPage`.

Template selection on web uses a `<TemplatePickerSheet>` triggered from the customer detail page (not a full-page route). This is consistent with the web being owner/manager-facing rather than field-facing.

### Mobile routes (Expo Router)

| Route | File | Description |
|:---|:---|:---|
| `(tabs)/jobs/[jobId]/comms` | `apps/mobile/app/(tabs)/jobs/[jobId]/comms.tsx` | **New** — comms send flow from job context |
| `(tabs)/customers/[id]/comms` | `apps/mobile/app/(tabs)/customers/[id]/comms.tsx` | **New** — per-customer comm history (mobile) |

The mobile comms send flow is a **full-screen stack route** pushed from the Job Detail screen's "Communicate" primary action button. It contains: template picker → (optionally) time-extraction editor → `<MessagePreviewModal>` → sent confirmation screen with auto-return.

The voice path can also be initiated from the persistent mic button on any screen; the resulting flow navigates programmatically to the `comms` route after intent classification.

---

## D. API Endpoint Consumption

### Endpoints consumed by FE-B6

| Endpoint | Operation | Schema types | Use |
|:---|:---|:---|:---|
| `POST /api/v1/communications/preview` | `preview_communication_api_v1_communications_preview_post` | `CommunicationPreviewRequest` → `CommunicationPreviewResponse` | Called first; never writes; returns rendered body + editable_variables |
| `POST /api/v1/communications/send` | `send_communication_api_v1_communications_send_post` | `CommunicationSendRequest` → `CommunicationSendResponse` | Called only after user confirms preview; writes `customer_communication` + `notification_outbox` |
| `GET /api/v1/customers/{customer_id}/communications` | `get_customer_communications_api_v1_customers__customer_id__communications_get` | `CommunicationHistoryResponse` | Paginated history list per customer |
| `GET /api/v1/communications/comm-template-types` | `list_comm_template_types_api_v1_communications_comm_template_types_get` | `CommTemplateTypeListResponse` | Template catalog — filter `initiator=tech` for the 6 MVP templates |

### Schema types (from `api-schema.d.ts`)

**`CommunicationPreviewRequest`**
```typescript
{
  customer_id: string;          // UUID
  template_code: string;        // e.g. "on_my_way"
  variables: Record<string, unknown>; // e.g. { eta_minutes: 20 }
  channel_override?: string | null;   // "sms" | "email" | null
}
```

**`CommunicationPreviewResponse`**
```typescript
{
  rendered_subject: string | null;  // null for SMS
  rendered_body: string;
  recipient_name: string;
  recipient_address: string;        // phone or email
  actual_channel: string;           // "sms" | "email"
  editable_variables: EditableVariableResponse[];
}
```

**`CommunicationSendRequest`**
```typescript
{
  customer_id: string;
  template_code: string;
  job_id?: string | null;       // populated when sending from job context
  variables: Record<string, unknown>;
  channel_override?: string | null;
}
```

**`CommunicationSendResponse`**
```typescript
{
  communication_id: string;     // UUID — used for status polling
  template_code: string;
  actual_channel: string;
  channel_override_flag: boolean;
  status: string;               // "pending" | "sent" | "failed"
  rendered_message: string;
  rendered_subject: string | null;
  recipient_address: string;
  sent_at: unknown | null;
}
```

**`CommunicationHistoryItem`**
```typescript
{
  communication_id: string;
  template_code: string;
  actual_channel: string;
  channel_override_flag: boolean;
  customer_preferred_channel: string | null;
  rendered_message: string;
  rendered_subject: string | null;
  status: string;
  sent_at: unknown | null;
  sender_user_id: string;
  job_id: string | null;
}
```

**`CommTemplateTypeResponse`**
```typescript
{
  code: string;         // "on_my_way" | "running_late" | "arrived" | etc.
  slug: string;
  name: string;         // display name: "On my way"
  description: string | null;
  category: string;     // "appointment" | "job_status" | "delay"
  preferred_channel: string | null;
  initiator: string;    // "tech" for all 6 MVP templates
  requires_approval: boolean;
  send_mode: string;
  trigger_event: string | null;
  is_system: boolean;
  sort_order: number;
}
```

### MSW handler specs (develop against until BE-B4 lands)

All handlers live at `apps/{web,mobile}/src/mocks/handlers/communications.ts`.

**1. Preview handler**
```
POST /api/v1/communications/preview
→ 200 CommunicationPreviewResponse (rendered_body populated, editable_variables from template)
Constraint: NEVER returns a communication_id; response has NO side effects
```

**2. Send handler**
```
POST /api/v1/communications/send
Precondition check: in test scenarios, verify that preview was called first via shared MSW state flag
→ 201 CommunicationSendResponse { status: "pending", communication_id: <uuid> }
After 1.5s delay: status transitions to "sent" (simulate Celery dispatch)
Error variant: return 422 with specific failure body to test retry banner
```

**3. History handler**
```
GET /api/v1/customers/{customer_id}/communications?page=1&page_size=20
→ 200 CommunicationHistoryResponse with seeded history items per customer fixture
```

**4. Template types handler**
```
GET /api/v1/communications/comm-template-types?initiator=tech
→ 200 CommTemplateTypeListResponse with all 6 MVP templates in sort_order
```

**MSW two-step enforcement**: The MSW send handler tracks a request-scoped `previewCalled` flag. If `POST /send` is invoked without a preceding `POST /preview` in the same test session, it returns `403 { detail: "preview_not_called" }`. This allows integration tests to assert the enforcement contract.

---

## E. Pattern Reuse Decisions

| Pattern | Source | Import path | Usage in FE-B6 |
|:---|:---|:---|:---|
| `<VoiceConfirmTurn>` | FE-B3 | `@pilot/ui/voice-confirm-turn` | Voice comms path: renders "Send the 'on my way' message to [name]?" confirmation turn |
| `useVoiceConfirmation()` | FE-B3 | `@pilot/ui/voice-confirm-turn` | Manages `pendingConfirmation` state + `confirm()` / `cancel()` lifecycle |
| `useVoiceStream()` | FE-B3 | `@pilot/ui/voice` | Streams audio to GPU; existing WebSocket hook — not reimplemented |
| `<NotificationBanner>` / `useNotificationQueue()` | FE-B1 | `@pilot/ui/notification-banner` | Send status toasts: sending / sent / failed+retry |
| `<ErrorState type="network">` | FE-B1 | `@pilot/ui/states` | Shown when device is offline and user attempts to send |
| `<LoadingState>` | FE-B1 | `@pilot/ui/states` | Preview loading state while `POST /preview` is in-flight |
| `useSseChannel()` | FE-B4 | `@pilot/ui/hooks/useSseChannel` | Not used in FE-B6 for comms delivery (no SSE endpoint exists — polling used instead); available if BE-B4 adds SSE |
| `apiClient` | FE-B0 | `@pilot/ui` or app-local | All HTTP calls |

**Composition diagram for voice comms path**:
```
useVoiceStream()          ← audio streaming (FE-B3)
    ↓ transcript + intent
useVoiceConfirmation()    ← pending confirmation state (FE-B3)
    ↓ intent classified as comms
TimeExtractionEditor      ← editable time variables (FE-B6, new)
    ↓ variables confirmed
usePreviewBeforeSend()    ← calls POST /preview, opens modal (FE-B6, new)
    ↓ preview rendered
<MessagePreviewModal>     ← renders body + VoiceConfirmTurn inside (FE-B6, new)
    ↓ user confirms ("send")
usePreviewBeforeSend()    ← calls POST /send (FE-B6, new)
    ↓ send dispatched
useNotificationQueue()    ← "Sending…" → "Sent" banner (FE-B1)
```

---

## F. Shared Module Interfaces

These interfaces are **locked at FE-B6 design time**. FE-B10 (SMS inbound extension) consumes `<MessagePreviewModal>` and `usePreviewBeforeSend()` for free-form reply composition. **Do not change these interfaces without an FE-B10 impact review.**

### F1 — `usePreviewBeforeSend()` hook

```typescript
// packages/ui/src/hooks/usePreviewBeforeSend.ts

/** Input to a preview call — supports both template-based (FE-B6) and free-form (FE-B10) */
export type PreviewInput =
  | {
      mode: 'template';
      customerId: string;          // UUID
      templateCode: string;        // "on_my_way" | "running_late" | ...
      jobId?: string;              // populated when sending from job context
      variables?: Record<string, unknown>;
      channelOverride?: 'sms' | 'email' | null;
    }
  | {
      mode: 'free-form';
      customerId: string;          // UUID
      freeFormBody: string;        // raw message text (FE-B10 free-form reply)
      threadId?: string;           // FE-B10: thread context
      channelOverride?: 'sms' | 'email' | null;
    };

/** State exposed by the hook */
export interface UsePreviewBeforeSendReturn {
  /**
   * Trigger the preview → modal flow.
   * Calls POST /communications/preview, populates previewData, opens modal.
   * For free-form mode, sends the body directly as the rendered preview (no server render needed).
   */
  preview: (input: PreviewInput) => Promise<void>;

  /**
   * Execute the actual send.
   * WILL THROW if called without a prior successful preview() call in the same flow instance.
   * Called automatically by <MessagePreviewModal>'s "Send" button — consumers rarely call directly.
   */
  send: () => Promise<CommunicationSendResponse | FreeFormSendResponse>;

  /** Whether POST /preview is in-flight */
  isPreviewLoading: boolean;

  /** Whether POST /send is in-flight */
  isSending: boolean;

  /** Populated after a successful preview() call; null before preview or after reset */
  previewData: CommunicationPreviewResponse | FreeFormPreviewData | null;

  /** Whether the preview modal is currently open */
  isModalOpen: boolean;

  /** Programmatically close the modal and reset state (e.g., user navigates away) */
  closeModal: () => void;

  /**
   * The rendered <MessagePreviewModal> — place this in the component tree.
   * When isModalOpen is true, the modal renders with previewData content.
   */
  MessagePreviewModal: React.FC<Partial<MessagePreviewModalOverrideProps>>;

  /** Null if no send has been attempted; populated on success or failure */
  sendResult: CommunicationSendResponse | FreeFormSendResponse | null;
  sendError: Error | null;
}

export interface UsePreviewBeforeSendOptions {
  /** Default channel — customer preference is applied server-side; this is the UI default */
  defaultChannel?: 'sms' | 'email';
  /**
   * Called immediately after a successful send.
   * Use to close parent drawer, navigate away, trigger history refetch, etc.
   */
  onSendSuccess?: (result: CommunicationSendResponse | FreeFormSendResponse) => void;
  /** Called on send failure — in addition to the hook's internal error state */
  onSendError?: (error: Error) => void;
}

/**
 * usePreviewBeforeSend — always-preview-before-send (§16.7) hook.
 *
 * Establishes in FE-B6. Consumed by FE-B10 (free-form SMS reply composer).
 * The hook enforces that send() cannot be called without a prior preview().
 *
 * @example Template-based (FE-B6)
 * const { preview, MessagePreviewModal } = usePreviewBeforeSend();
 * <Button onPress={() => preview({ mode: 'template', customerId, templateCode: 'on_my_way', variables: { eta_minutes: 20 } })} />
 * <MessagePreviewModal />
 *
 * @example Free-form (FE-B10)
 * const { preview, MessagePreviewModal } = usePreviewBeforeSend();
 * <Button onPress={() => preview({ mode: 'free-form', customerId, freeFormBody: text, threadId })} />
 * <MessagePreviewModal />
 */
export function usePreviewBeforeSend(
  options?: UsePreviewBeforeSendOptions,
): UsePreviewBeforeSendReturn;
```

### F2 — `<MessagePreviewModal>` component

```typescript
// packages/ui/src/message-preview/MessagePreviewModal.tsx

export interface MessagePreviewModalProps {
  /**
   * The rendered preview data from POST /communications/preview.
   * Populated by usePreviewBeforeSend — consumers do NOT pass this manually
   * when using the hook's embedded modal. Exposed for standalone usage (testing).
   */
  previewData: CommunicationPreviewResponse | FreeFormPreviewData | null;

  /** Whether the modal is visible */
  isOpen: boolean;

  /** Called when user taps "Send to [name]" or says "send" */
  onConfirm: () => void;

  /** Called when user taps "Cancel" or says "cancel" */
  onCancel: () => void;

  /** Called when user taps "Edit" — closes modal, returns to template picker for re-selection */
  onEdit?: () => void;

  /**
   * Whether the send mutation is in-flight.
   * Disables all action buttons while true.
   */
  isSending?: boolean;

  /**
   * When true, renders <VoiceConfirmTurn> inside the modal footer
   * instead of tap buttons. Used by the voice comms path.
   * The voice confirmation prompt is auto-generated from previewData.
   */
  voiceMode?: boolean;

  /**
   * Callback to update channel override — shown as a "Change channel" link in modal.
   * Does NOT persist to customer record.
   */
  onChannelOverride?: (channel: 'sms' | 'email') => void;

  /** Segment count to display for SMS channel (FE-B10 compat) */
  smsSegmentCount?: number;

  /** For Maestro/Detox e2e targeting */
  testID?: string;
}

/**
 * FreeFormPreviewData — used by FE-B10 when previewData is locally computed,
 * not server-rendered. The modal renders identically for both cases.
 */
export interface FreeFormPreviewData {
  rendered_subject: null;
  rendered_body: string;
  recipient_name: string;
  recipient_address: string;
  actual_channel: 'sms' | 'email';
  editable_variables: [];         // empty for free-form — no server-extracted variables
}

/**
 * MessagePreviewModalOverrideProps — partial override props for the
 * embedded modal returned by usePreviewBeforeSend().MessagePreviewModal.
 * Consumers can pass voiceMode, onEdit, testID etc.
 */
export type MessagePreviewModalOverrideProps = Pick<
  MessagePreviewModalProps,
  'voiceMode' | 'onEdit' | 'testID' | 'smsSegmentCount'
>;
```

### F3 — Preview state enforcement contract

The hook maintains an internal `previewToken: string | null` (a UUID generated at preview-call time). The `send()` function checks `previewToken !== null` before calling `POST /send`. If `null`, it throws:

```typescript
throw new Error('[usePreviewBeforeSend] send() called before preview() — this is a bug');
```

This is not a user-facing error. It is a programming contract violation that will surface in tests. The `<MessagePreviewModal>`'s "Send to [name]" button calls the hook's internal `send()` directly — so in normal usage this invariant can never be violated by the UI.

The `previewToken` is reset to `null` after a successful send, after `closeModal()`, or after `onCancel()`.

---

## G. Open Questions — All 8 Resolved

### G1 — `<MessagePreviewModal>` and `usePreviewBeforeSend()` API design

**Resolved**: Interfaces defined in §F above. Key design choices:
- `preview()` accepts a **discriminated union** (`mode: 'template' | 'free-form'`) to support both FE-B6 template sends and FE-B10 free-form replies from a single hook. The free-form branch skips the server render call and synthesizes `FreeFormPreviewData` locally.
- The hook **returns an embedded `MessagePreviewModal`** (the `§9.6` pattern from methods doc). This means consumers place one JSX element in their tree and call `preview()` from any event handler — no manual modal state management.
- `onSendSuccess` callback is provided so parent components can trigger history refetch, navigate away, or clear form state without coupling to the hook's internal state.

### G2 — Two-endpoint preview → send enforcement

**Resolved**: The hook tracks `previewToken: string | null` internally. `send()` throws a programming-contract error if `previewToken` is null. In normal UI usage this invariant is enforced structurally — the only path to call `send()` is through the `<MessagePreviewModal>`'s "Send" button, which is only rendered when `isModalOpen === true`, which requires a successful `preview()` call.

The MSW test handler adds a second enforcement layer: `POST /send` without a prior `POST /preview` in the same test session returns `403 { detail: "preview_not_called" }`. This is **test infrastructure only** — the real backend does not enforce call order (the two endpoints are stateless; the backend simply processes each independently).

### G3 — Offline path for customer comms

**Resolved**: Customer comms are **online-only**. There is no offline queue, no "pending intent" storage, no deferred send path.

Per `mvp-arch.md §16.7` and `§15.14`: "customer comms stay online-only per arch doc §15.14." The arch doc is explicit: "captured intent waits for online preview" — but for FE-B6 this means the UI simply **blocks the action** when offline. No intent is captured.

**UI behavior when offline**:
- Template picker screen: "Communicate" button is disabled with tooltip "Online required to send messages"
- If user is mid-flow (template selected, time editor open) and connection drops: `<ErrorState type="network">` replaces the send step with message "Message send requires internet connection"
- `<MessagePreviewModal>` confirm button is disabled with an amber offline indicator
- No "send when online" affordance — user must retry when online

This is distinct from the voice quote creation flow (FE-B3) which supports offline audio capture + deferred processing.

### G4 — Template selection UI layout

**Resolved**:
- **Mobile**: 2×3 card grid per spec §Decision 3 (two columns, three rows). Gluestack-UI Card components. Each card: 24px intent icon + template name (semibold) + one-line rendered preview text (muted). Voice CTA amber panel above grid. Customer channel pill above grid.
- **Web**: Same logical 2×3 grid in a `<TemplatePickerSheet>` (shadcn-ui Sheet from the right). The web template picker is owner/manager-facing, triggered from the customer detail page. Cards use shadcn-ui Card with identical information density.
- **Variables** appear in the `<MessagePreviewModal>` (as editable amber chips), NOT in the template picker. The picker is purely template selection — variables are resolved server-side via the preview call.
- **Customer inputs**: customer is implicit from job context (mobile) or pre-set from customer detail page (web). No customer picker in the template selection step — customer is always known before opening the picker.

### G5 — Channel override

**Resolved**: Channel override appears in **both** the template selection step and the preview modal.

- **Template picker (primary)**: customer info bar above the card grid shows "SMS preferred" pill and a discreet "Send via email instead →" link. Tapping sets `channelOverride` in hook state. This is the primary override affordance per spec §Decision 4.
- **Preview modal (secondary)**: small "Change channel" link next to the channel display. Same `onChannelOverride` callback — triggers a re-preview call with the new channel (so the rendered preview reflects the correct channel-specific formatting).
- Override is **not persisted**. `channelOverride` lives in hook state only. The `CommunicationSendRequest.channel_override_flag` in the send response (`boolean`) and `CommunicationHistoryItem.channel_override_flag` log the override for audit trail — the customer's stored preference is not modified.
- Implementation: `'sms' | 'email' | null` (null = use customer's stored preference; server resolves). The UI always shows the resolved `actual_channel` from the preview response, so "SMS preferred" vs "email for this message" is always clear.

### G6 — Communication history view placement

**Resolved**: History lives on the **customer detail page** (`/customers/{id}`) as a dedicated **Communications tab**.

Rationale:
1. The `/customers/{id}` route already exists as a stub. Adding a `comms` subroute is minimal work.
2. Spec §Decision 10 explicitly says "the Customer detail page has a Communications tab."
3. The FE-B0 `/comms` route (standalone) is kept but repurposed as a **cross-customer comms summary** — last N messages across all customers, owner-facing. This is minimal in FE-B6; FE-B10 extends it with the inbound thread inbox.

**Web routes added in FE-B6**:
- `(authed)/customers/[id]/page.tsx` — customer detail shell with tabbed navigation
- `(authed)/customers/[id]/comms/page.tsx` — communications history tab

**Mobile routes added in FE-B6**:
- `(tabs)/customers/[id]/comms.tsx` — per-customer comm history (mobile)

### G7 — Voice comms path and time-extraction step

**Resolved**: Time extraction happens **before** the preview call, in a dedicated `<TimeExtractionEditor>` step.

**Full voice comms path sequence**:
1. User speaks: "Tell Johnson I'm 20 out"
2. `useVoiceStream()` streams audio → Whisper transcript → Ollama intent: `send_comm_on_my_way`, customer: "Johnson", time: 20 minutes
3. If customer is ambiguous → `<CustomerDisambiguationList>` shown; user picks
4. **Time extraction step**: `<TimeExtractionEditor>` shown — "20 minutes — ETA [auto-computed time]. Adjust?" with quick-pick 5/10/15/20/30/45/Custom. User confirms or adjusts.
5. After time confirmed: `preview({ mode: 'template', customerId, templateCode: 'on_my_way', variables: { eta_minutes: 20 } })` called
6. `POST /communications/preview` returns `rendered_body`: "On my way, ETA 2:45 PM"
7. AI reads rendered body aloud; `<MessagePreviewModal voiceMode>` opens with `<VoiceConfirmTurn>` in footer: "Send 'On my way, ETA 2:45 PM' to Johnson?"
8. User says "send" → `useVoiceConfirmation().confirm()` → `send()` → `POST /communications/send`
9. Sent confirmation screen: success checkmark, "Sent to Johnson", auto-return to Job Detail after ~2.4s

**Rationale for time extraction before preview**: The preview endpoint needs finalized variable values to render the ETA. If time correction happened inside `<MessagePreviewModal>`, it would require a re-preview call on every chip edit. Instead, the `<TimeExtractionEditor>` collects final variable values once, then a single preview call produces the final rendered message. Post-preview amber chip edits in the modal still trigger re-preview — this handles edge cases where the user wants to further adjust after seeing the rendered result.

### G8 — `notification_outbox` status surfacing

**Resolved**: **TanStack Query polling** (not SSE).

The schema has no `GET /api/v1/communications/{id}/status` endpoint and no SSE endpoint for comms delivery status. The `GET /api/v1/customers/{id}/communications` endpoint returns `CommunicationHistoryItem.status`.

**Implementation**:
1. `POST /send` returns `CommunicationSendResponse` with `{ communication_id, status: "pending" }` immediately
2. On `status === "pending"`, `usePreviewBeforeSend()` starts a TanStack Query `useQuery` polling the history endpoint at 2-second intervals
3. When the matching `communication_id` entry shows `status !== "pending"` (i.e., `"sent"` or `"failed"`), polling stops
4. `<NotificationBanner>` severity transitions: `info` → "Sending…" (amber), then `success` → "Sent to [name]" (green, 6s auto-dismiss) or `error` → "Failed — Retry" (red, persistent)
5. Retry: re-calls `POST /send` with same params (note: preview token must be valid; hook retains it on failure)
6. Polling timeout: 30 seconds. If still `pending` after 30s, show "Message delivery unknown — check history" info banner

**If BE-B4 adds a dedicated delivery SSE endpoint** after FE-B6 ships: the polling strategy is isolated inside `usePreviewBeforeSend()` and can be swapped to `useSseChannel()` from FE-B4 without changing any consumer API.

---

## H. External Dependency Status

### BE-B4 (Customer comms base) — Backend gate

| Endpoint | Status | FE-B6 Strategy |
|:---|:---|:---|
| `POST /api/v1/communications/preview` | Schema confirmed in `api-schema.d.ts` — endpoint exists | MSW handler for dev; real endpoint available |
| `POST /api/v1/communications/send` | Schema confirmed — endpoint exists | MSW handler for dev |
| `GET /api/v1/customers/{id}/communications` | Schema confirmed — endpoint exists | MSW handler for dev |
| `GET /api/v1/communications/comm-template-types` | Schema confirmed — endpoint exists | MSW handler for dev |

**Assessment**: All four endpoints required by FE-B6 are present in `api-schema.d.ts`. BE-B4 appears to have landed (schema types are real, not stubs). MSW handlers are still required for isolated unit/integration testing and for offline development. Confirm with team whether the dev API backend is accessible before removing MSW fallback.

### 10DLC / Telnyx SMS

SMS delivery in production requires 10DLC registration. In development, the backend uses `MockSmsCarrier` (per arch doc §17.1 carrier-agnostic adapter layer). The `CommunicationSendResponse.status` will return `"sent"` immediately in dev via the mock carrier. The frontend does not need to know about carrier implementation — this is backend-internal. FE-B6 ships against the mock; production 10DLC status does not block frontend development.

### FE-B10 (SMS inbound extension) — downstream gate

FE-B10 reuses:
- `<MessagePreviewModal>` — for free-form reply composer preview
- `usePreviewBeforeSend({ mode: 'free-form' })` — for the free-form send path
- `VoiceConfirmTurn` (from FE-B3, also used in FE-B6)

**The interfaces locked in §F are the contract FE-B10 depends on.** Any change to `MessagePreviewModalProps` or `UsePreviewBeforeSendReturn` after FE-B6 ships requires FE-B10 impact review.

### §17.6 SMS Quota — awareness only

FE-B6 sends outbound SMS via the quota system. FE-B6 does **not** build the quota UI (that is FE-B10/FE-B11). FE-B6 must:
1. Show segment count in `<MessagePreviewModal>` when `actual_channel === "sms"` (segment count derived from rendered_body length: 1 segment per 160 chars GSM-7, 1 per 70 chars Unicode)
2. If `POST /send` returns a quota-exhausted error (hard cap policy: all outbound blocked), surface `<NotificationBanner severity="error">` "Monthly SMS quota reached — contact your account owner"
3. Do NOT build the quota dashboard widget or buy-more-segments CTA — those are FE-B10

---

## I. Test Plan

**Targets**: 50+ unit, 12+ integration, 3+ e2e (per `pilot-app-mvp-frontend-impl-plan.md` §6 FE-B6 test focus)

### I1 — Unit tests (target: 50+)

All unit tests in `apps/{web,mobile}/__tests__/batch_fe_b6/unit/`.

| Test group | Key cases |
|:---|:---|
| **`usePreviewBeforeSend` hook** | (1) `preview()` calls `POST /preview` exactly once with correct payload; (2) `send()` throws if called before `preview()`; (3) `send()` succeeds after `preview()`; (4) `previewToken` resets after `closeModal()`; (5) `channelOverride` flows through to both preview and send requests; (6) `isSending` is true during send; (7) `onSendSuccess` fires on 201; (8) `onSendError` fires on 422; (9) free-form mode sends `freeFormBody` as rendered_body without server call; (10) polling starts on `status === "pending"`, stops on `"sent"` |
| **`<MessagePreviewModal>` rendering** | (1) renders `rendered_body` correctly; (2) renders SMS channel pill with chat-bubble icon; (3) renders email channel pill with envelope icon; (4) renders "channel overridden" amber badge when `channel_override_flag` in previewData; (5) editable variable chip renders for each `editable_variables` entry; (6) "Send to [name]" button label includes `recipient_name`; (7) all buttons disabled when `isSending === true`; (8) voiceMode renders `<VoiceConfirmTurn>` footer, not button row; (9) segment count row visible for SMS, hidden for email |
| **Channel override** | (1) tapping override link sets `channelOverride` in hook state; (2) override does NOT trigger any customer PATCH or PUT; (3) preview is re-called with new channel; (4) rendered `actual_channel` reflects override in modal |
| **Template picker UI** | (1) 6 template cards render with correct names/icons; (2) tapping a card calls `preview()` with correct `templateCode`; (3) voice CTA panel renders above grid; (4) customer channel pill renders preferred channel; (5) `<ErrorState type="network">` replaces send step when offline |
| **Time-extraction editor** | (1) renders when `editable_variables` contains a time variable; (2) quick-pick selection updates variable value; (3) "Custom" option shows text input; (4) confirmed value flows to `preview()` call; (5) cancelling editor returns to template picker |
| **Customer disambiguation** | (1) list renders all matching customers when voice matches multiple; (2) tapping a customer proceeds to time editor or preview; (3) "which Johnson" prompt renders correctly for 2-match case |
| **`notification_outbox` status** | (1) "Sending…" banner shown immediately on 201 response; (2) "Sent" banner shown after polling resolves to "sent"; (3) "Failed" banner with Retry shown when status is "failed"; (4) retry re-calls `POST /send`; (5) 30s polling timeout shows "unknown" info banner |
| **Communication history view** | (1) items render with correct template code pills; (2) "voice-triggered" flag visible; (3) "channel overridden" amber chip visible when `channel_override_flag === true`; (4) pagination loads more items; (5) filter by channel hides items of other channel |

### I2 — Integration tests (target: 12+)

All integration tests in `apps/{web,mobile}/__tests__/batch_fe_b6/integration/`.

| Test | Description |
|:---|:---|
| `template-send-web.test.ts` | Full flow: open customer detail → tap template picker → select "On my way" → preview renders → confirm → send → "Sent" banner |
| `template-send-mobile.test.ts` | Full flow: Job Detail → "Communicate" → template picker → "On my way" → time editor (20 min) → preview → confirm → sent confirmation → auto-return |
| `voice-send-full-flow.test.ts` | Mock voice event → intent: `on_my_way`, 20 min → time editor → preview → `<VoiceConfirmTurn>` → confirm → send via `POST /send` |
| `preview-no-db-write.test.ts` | `POST /preview` MSW handler called → verify via test API (`GET /communications`) that NO `customer_communication` row was created |
| `send-failure-retry.test.ts` | `POST /send` returns 422 → "Failed" banner with Retry → retry calls `POST /send` again → success |
| `channel-override-flow.test.ts` | Customer has SMS preference → tap "Send via email" override → preview shows email channel → send → `CommunicationSendResponse.channel_override_flag === true` |
| `offline-block.test.ts` | Toggle network offline → attempt to open template picker → `<ErrorState type="network">` shown → toggle online → template picker available |
| `voice-disambiguation-flow.test.ts` | Voice: "tell Johnson I'm 20 out" → two Johnsons in DB → disambiguation list shown → user picks → continues to preview |
| `comms-history-web.test.ts` | Send a message → navigate to `/customers/{id}/comms` → sent message appears in history with correct rendered_message, channel, template_code |
| `comms-history-mobile.test.ts` | Mobile: send a message from job context → navigate to customer comm history tab → item visible |
| `quota-hard-cap-block.test.ts` | MSW: POST /send returns quota-exhausted error → "Monthly SMS quota reached" error banner shown |
| `preview-token-enforcement.test.ts` | Integration test asserting MSW's `403 preview_not_called` fires if test code bypasses UI and calls `send()` without `preview()` |

### I3 — E2E tests (target: 3+)

All e2e tests in `apps/{web,mobile}/__tests__/batch_fe_b6/e2e/`.

| Test | Platform | Description |
|:---|:---|:---|
| `web-template-send.e2e.ts` | Web (Playwright) | Full cycle against dev backend: customer detail → template picker → "On my way" → preview shows real rendered body → confirm send → `GET /customers/{id}/communications` returns new row with status "sent" |
| `mobile-voice-send.e2e.ts` | Mobile (Maestro) | Real voice: say "Tell [fixture customer] I'm on my way" → time editor → preview modal → say "send" → sent confirmation → history reflects sent message |
| `comms-history-reflects-sends.e2e.ts` | Web (Playwright) | Send 3 messages to same customer via different templates → navigate to `/customers/{id}/comms` → all 3 appear with correct metadata; filter by "SMS only" → correct subset shown |

---

## Appendix — `packages/ui/src/index.ts` additions (FE-B6 section)

The following block is appended to `packages/ui/src/index.ts` at FE-B6 completion:

```typescript
// ── FE-B6 Exports ─────────────────────────────────────────────────────────────
// MessagePreviewModal + usePreviewBeforeSend establish the always-preview-before-send
// pattern (§16.7). Consumed by FE-B10 (SMS reply composer).
// ⚠️ Interfaces locked — changes require FE-B10 impact review.

export { MessagePreviewModal } from './message-preview';
export type {
  MessagePreviewModalProps,
  MessagePreviewModalOverrideProps,
  FreeFormPreviewData,
} from './message-preview/types';

export { usePreviewBeforeSend } from './hooks/usePreviewBeforeSend';
export type {
  UsePreviewBeforeSendReturn,
  UsePreviewBeforeSendOptions,
  PreviewInput,
} from './hooks/usePreviewBeforeSend';

export { CustomerDisambiguationList } from './message-preview/CustomerDisambiguationList';
export type { CustomerDisambiguationListProps } from './message-preview/types';

export { TimeExtractionEditor } from './message-preview/TimeExtractionEditor';
export type { TimeExtractionEditorProps } from './message-preview/types';
```

---

*End of Batch FE-B6 Design Document*
