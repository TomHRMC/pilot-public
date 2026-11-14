/**
 * SMS Domain Types — Canonical for Phase 2 Reuse
 *
 * Location: packages/ui/src/sms-thread-bubble/types.ts
 * Exported from: packages/ui/src/index.ts under // ── FE-B10 Exports ──
 *
 * ⚠️ TYPES LOCKED after FE-B10. Phase 2 additions are strictly additive optional fields.
 * Mandatory new fields require migration plan for all consumers.
 */

// ── Core SMS domain types ─────────────────────────────────────────────────────

/**
 * A conversation thread keyed by (tenant_id × customer_id × tech_id × tenant_phone_number_id).
 * Canonical type for Phase 2 SMS features. DO NOT extend without impact review.
 */
export interface SmsThread {
  thread_id: string;
  tenant_id: string;
  customer_id: string;
  customer_name: string;
  customer_phone: string; // E.164 format; display-only (never used to dial)
  customer_sms_opted_out: boolean;
  customer_opted_out_at: string | null;
  tech_id: string;
  tech_name: string;
  tenant_phone_number_id: string;
  status: "active" | "archived";
  first_message_at: string;
  last_message_at: string;
  message_count: number;
  unread_count: number;
  originating_job_id: string | null;
  originating_job_display: string | null; // "Job #1042 — Panel Upgrade"
  created_at: string;
  updated_at: string;
  messages: SmsMessage[];
}

/**
 * A single message within a thread.
 * Canonical type for Phase 2 SMS features. DO NOT extend without impact review.
 */
export interface SmsMessage {
  message_id: string;
  thread_id: string;
  direction: "outbound" | "inbound";
  channel: "sms"; // MMS is Phase 2
  body: string;
  segment_count: number;
  status: "pending_send" | "sent" | "delivered" | "failed" | "received";
  carrier_message_id: string | null;
  composition_method: "template" | "free_form_text" | "free_form_voice";
  template_id: string | null;
  voice_audio_id: string | null;
  sent_at: string | null;
  delivered_at: string | null;
  received_at: string | null;
  audit_user_id: string; // tech who sent or was routed to
}

export interface SmsReplyRequest {
  body: string;
  composition_method: "free_form_text" | "free_form_voice";
  voice_audio_id?: string;
}

export interface SmsReplyResponse {
  message_id: string;
  thread_id: string;
  status: "pending_send" | "sent";
  segment_count: number;
  sent_at: string | null;
}

export interface SmsQuotaStatus {
  period_id: string;
  used_segments: number;
  included_segments: number;
  remaining_segments: number;
  overage_segments: number;
  cap_policy: "soft" | "hard";
  period_start: string; // ISO date
  period_end: string; // ISO date
  blocked_reason: "customer_opted_out" | "monthly_quota_reached" | null;
  projected_month_end_segments: number; // for web owner widget
}

export interface SmsThreadListItem {
  thread_id: string;
  customer_id: string;
  customer_name: string;
  last_message_preview: string; // first 50 chars of last message body
  last_message_at: string;
  last_message_direction: "outbound" | "inbound";
  unread_count: number;
  originating_job_id: string | null;
  originating_job_display: string | null;
  customer_sms_opted_out: boolean;
}

export interface UnroutedMessage {
  unrouted_id: string;
  tenant_id: string;
  from_number: string; // masked for display: "+1 (555) ***-1234"
  to_number: string; // tenant's Telnyx number
  body: string;
  received_at: string;
  attempted_customer_match: string | null; // best-guess from threading attempt
}

// ── Quota state machine ───────────────────────────────────────────────────────

/**
 * Derived quota display state for <SmsQuotaIndicator>.
 * Computed by deriveQuotaState() utility — export from packages/ui.
 */
export type QuotaVisualState =
  | { state: "normal"; remaining: number; included: number }
  | { state: "warning"; remaining: number; included: number }
  | { state: "blocked_soft"; used: number; included: number }
  | { state: "blocked_hard"; used: number; included: number }
  | { state: "opted_out" };

// ── Voice dictation state machine ─────────────────────────────────────────────

/**
 * State machine for single-utterance voice transcription in the reply composer.
 * Location: apps/mobile/features/customer-comms/hooks/useVoiceDictation.ts
 */
export type VoiceDictationState =
  | { phase: "idle" }
  | { phase: "recording" }
  | { phase: "transcribing" }
  | { phase: "transcribed"; transcript: string }
  | { phase: "error"; error: string };

export interface UseVoiceDictationReturn {
  state: VoiceDictationState;
  startDictating: () => void;
  stopDictating: () => void;
  reset: () => void;
}

// ── Component props ───────────────────────────────────────────────────────────

/**
 * Location: packages/ui/src/sms-thread-bubble/SmsThreadBubble.tsx
 * Polymorphic: web/mobile variants per DiffView pattern from FE-B5.
 */
export interface SmsThreadBubbleProps {
  message: SmsMessage;
  /** Whether this bubble is from the perspective of the current user */
  isOwnMessage: boolean;
  showTimestamp?: boolean;
  showDeliveryStatus?: boolean;
  /** True for optimistic messages not yet confirmed by server */
  isPending?: boolean;
  testID?: string;
  /** Optional sender name label displayed below the bubble.
   *  e.g. "From: Jake" (outbound) or "From: John Smith" (inbound).
   *  If undefined, no sender label is rendered. */
  senderLabel?: string;
}

/**
 * Location: packages/ui/src/sms-quota-indicator/SmsQuotaIndicator.tsx
 * Mobile only (Gluestack primitives). Web quota shown in owner settings surface.
 */
export interface SmsQuotaIndicatorProps {
  quota: SmsQuotaStatus;
  currentMessageSegmentCount: number; // from useSegmentCount — for real-time preview
  isLoading?: boolean;
  testID?: string;
}

/**
 * Location: packages/ui/src/sms-opt-out-badge/SmsOptOutBadge.tsx
 */
export interface SmsOptOutBadgeProps {
  optedOutAt: string | null; // ISO date; null → "opted out" without date
  compact?: boolean; // compact = no date shown (for tight headers)
  testID?: string;
}
