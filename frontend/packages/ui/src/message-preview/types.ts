/**
 * MessagePreview shared types — FE-B6
 *
 * Location: packages/ui/src/message-preview/types.ts
 * Exported from: packages/ui/src/index.ts under // ── FE-B6 Exports ──
 *
 * ⚠️ INTERFACE LOCKED — changes require FE-B10 impact review.
 * FE-B10 (SMS inbound) consumes MessagePreviewModal and usePreviewBeforeSend
 * for free-form reply composition.
 */

// ── API Schema Types (mirrors api-schema.d.ts) ────────────────────────────────

export interface EditableVariableResponse {
  /** Variable name, e.g. "eta_minutes" */
  name: string;
  /** Current value */
  value: unknown;
  /** Display label for the UI chip */
  label: string;
  /** Variable type: "time_minutes" | "text" | "number" | "date" */
  type: "time_minutes" | "text" | "number" | "date";
}

/** Server response from POST /api/v1/communications/preview */
export interface CommunicationPreviewResponse {
  rendered_subject: string | null;
  rendered_body: string;
  recipient_name: string;
  recipient_address: string;
  actual_channel: "sms" | "email";
  editable_variables: EditableVariableResponse[];
}

/** Request body for POST /api/v1/communications/preview */
export interface CommunicationPreviewRequest {
  customer_id: string;
  template_code: string;
  variables: Record<string, unknown>;
  channel_override?: string | null;
}

/** Request body for POST /api/v1/communications/send */
export interface CommunicationSendRequest {
  customer_id: string;
  template_code: string;
  job_id?: string | null;
  variables: Record<string, unknown>;
  channel_override?: string | null;
}

/** Server response from POST /api/v1/communications/send */
export interface CommunicationSendResponse {
  communication_id: string;
  template_code: string;
  actual_channel: string;
  channel_override_flag: boolean;
  status: "pending" | "sent" | "failed";
  rendered_message: string;
  rendered_subject: string | null;
  recipient_address: string;
  sent_at: string | null;
}

/** A single item from GET /api/v1/customers/{id}/communications */
export interface CommunicationHistoryItem {
  communication_id: string;
  template_code: string;
  actual_channel: string;
  channel_override_flag: boolean;
  customer_preferred_channel: string | null;
  rendered_message: string;
  rendered_subject: string | null;
  status: string;
  sent_at: string | null;
  sender_user_id: string;
  job_id: string | null;
}

/** Template type from GET /api/v1/communications/comm-template-types */
export interface CommTemplateTypeResponse {
  code: string;
  slug: string;
  name: string;
  description: string | null;
  category: string;
  preferred_channel: string | null;
  initiator: string;
  requires_approval: boolean;
  send_mode: string;
  trigger_event: string | null;
  is_system: boolean;
  sort_order: number;
}

export interface CommTemplateTypeListResponse {
  items: CommTemplateTypeResponse[];
}

export interface CommunicationHistoryResponse {
  items: CommunicationHistoryItem[];
  total: number;
  page: number;
  page_size: number;
}

// ── Free-Form Types (FE-B10 compat) ──────────────────────────────────────────

/**
 * FreeFormPreviewData — locally synthesized preview for free-form sends.
 * Used by FE-B10 when previewData is not server-rendered.
 * The modal renders identically for both server-rendered and free-form cases.
 */
export interface FreeFormPreviewData {
  rendered_subject: null;
  rendered_body: string;
  recipient_name: string;
  recipient_address: string;
  actual_channel: "sms" | "email";
  /** Always empty for free-form — no server-extracted variables */
  editable_variables: [];
}

/** Response for free-form send (FE-B10); same shape as template send for UI */
export interface FreeFormSendResponse {
  communication_id: string;
  actual_channel: string;
  channel_override_flag: boolean;
  status: "pending" | "sent" | "failed";
  rendered_message: string;
  sent_at: string | null;
  thread_id?: string;
}

// ── usePreviewBeforeSend Types ────────────────────────────────────────────────

/**
 * Input to a preview call.
 * Discriminated union supporting both template-based (FE-B6) and free-form (FE-B10) sends.
 */
export type PreviewInput =
  | {
      mode: "template";
      customerId: string;
      templateCode: string;
      jobId?: string;
      variables?: Record<string, unknown>;
      channelOverride?: "sms" | "email" | null;
    }
  | {
      mode: "free-form";
      customerId: string;
      freeFormBody: string;
      /** FE-B10: thread context */
      threadId?: string;
      channelOverride?: "sms" | "email" | null;
    };

export interface UsePreviewBeforeSendOptions {
  /** Default channel — customer preference applied server-side; this is the UI default */
  defaultChannel?: "sms" | "email";
  /**
   * Called immediately after a successful send.
   * Use to close parent drawer, navigate away, trigger history refetch, etc.
   */
  onSendSuccess?: (
    result: CommunicationSendResponse | FreeFormSendResponse,
  ) => void;
  /** Called on send failure — in addition to the hook's internal error state */
  onSendError?: (error: Error) => void;
}

export interface UsePreviewBeforeSendReturn {
  /**
   * Trigger the preview → modal flow.
   * Calls POST /communications/preview (template) or synthesizes locally (free-form).
   * Populates previewData and opens modal.
   */
  preview: (input: PreviewInput) => Promise<void>;

  /**
   * Execute the actual send.
   * THROWS if called without a prior successful preview() call (previewToken === null).
   * Called automatically by <MessagePreviewModal>'s "Send" button.
   */
  send: () => Promise<CommunicationSendResponse | FreeFormSendResponse>;

  /** Whether POST /preview is in-flight */
  isPreviewLoading: boolean;

  /** Whether POST /send is in-flight */
  isSending: boolean;

  /** Populated after successful preview(); null before or after reset */
  previewData: CommunicationPreviewResponse | FreeFormPreviewData | null;

  /** Whether the preview modal is currently open */
  isModalOpen: boolean;

  /** Programmatically close the modal and reset state */
  closeModal: () => void;

  /**
   * The rendered <MessagePreviewModal> — place this in the component tree.
   * When isModalOpen is true, the modal renders with previewData content.
   */
  MessagePreviewModal: React.FC<Partial<MessagePreviewModalOverrideProps>>;

  /** Null if no send attempted; populated on success or failure */
  sendResult: CommunicationSendResponse | FreeFormSendResponse | null;
  sendError: Error | null;
}

// ── MessagePreviewModal Types ─────────────────────────────────────────────────

export interface MessagePreviewModalProps {
  /** The rendered preview data. Populated by usePreviewBeforeSend. */
  previewData: CommunicationPreviewResponse | FreeFormPreviewData | null;

  /** Whether the modal is visible */
  isOpen: boolean;

  /** Called when user taps "Send to [name]" */
  onConfirm: () => void;

  /** Called when user taps "Cancel" */
  onCancel: () => void;

  /** Called when user taps "Edit" — returns to template picker */
  onEdit?: () => void;

  /** Whether the send mutation is in-flight — disables all action buttons */
  isSending?: boolean;

  /**
   * When true, renders <VoiceConfirmTurn> in the modal footer
   * instead of tap buttons. Used by the voice comms path.
   */
  voiceMode?: boolean;

  /**
   * Callback to update channel override (does NOT persist to customer record).
   */
  onChannelOverride?: (channel: "sms" | "email") => void;

  /** Segment count to display for SMS channel */
  smsSegmentCount?: number;

  /** For Maestro/Detox e2e targeting */
  testID?: string;
}

/**
 * Partial override props for the embedded modal returned by usePreviewBeforeSend().
 */
export type MessagePreviewModalOverrideProps = Pick<
  MessagePreviewModalProps,
  "voiceMode" | "onEdit" | "testID" | "smsSegmentCount"
>;

// ── CustomerDisambiguationList Types ─────────────────────────────────────────

export interface CustomerMatch {
  id: string;
  name: string;
  preferred_channel: "sms" | "email" | null;
  address: string;
}

export interface CustomerDisambiguationListProps {
  /** Multiple customers that matched the voice query */
  matches: CustomerMatch[];
  /** Called when user selects a specific customer */
  onSelect: (customer: CustomerMatch) => void;
  /** The raw query that caused the ambiguity, e.g. "Johnson" */
  query: string;
  /** For Maestro/Detox e2e targeting */
  testID?: string;
}

// ── TimeExtractionEditor Types ────────────────────────────────────────────────

export const TIME_QUICK_PICKS = [5, 10, 15, 20, 30, 45] as const;
export type TimeQuickPick = (typeof TIME_QUICK_PICKS)[number];

export interface TimeExtractionEditorProps {
  /** Initial value extracted by voice AI, in minutes */
  initialMinutes: number;
  /** Called when user confirms the time value */
  onConfirm: (minutes: number) => void;
  /** Called when user cancels — returns to template picker */
  onCancel: () => void;
  /** For Maestro/Detox e2e targeting */
  testID?: string;
}
