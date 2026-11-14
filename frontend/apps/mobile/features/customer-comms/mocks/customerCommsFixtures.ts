/**
 * customerCommsFixtures.ts — Mobile SMS Customer Comms Fixture Data
 *
 * Location: apps/mobile/features/customer-comms/mocks/customerCommsFixtures.ts
 * Used by: MSW mobile handlers and mobile integration tests for FE-B10
 */

import type {
  SmsThread,
  SmsMessage,
  SmsThreadListItem,
  SmsQuotaStatus,
} from "@pilot/ui";

// ── Message helpers ───────────────────────────────────────────────────────────

function makeMessage(
  overrides: Partial<SmsMessage> &
    Pick<SmsMessage, "message_id" | "thread_id" | "direction" | "body">,
): SmsMessage {
  return {
    channel: "sms",
    segment_count: 1,
    status: overrides.direction === "outbound" ? "delivered" : "received",
    carrier_message_id: `carrier-${overrides.message_id}`,
    composition_method: "free_form_text",
    template_id: null,
    voice_audio_id: null,
    sent_at: overrides.direction === "outbound" ? "2026-05-26T09:00:00Z" : null,
    delivered_at:
      overrides.direction === "outbound" ? "2026-05-26T09:00:02Z" : null,
    received_at:
      overrides.direction === "inbound" ? "2026-05-26T09:05:00Z" : null,
    audit_user_id: "tech-001",
    ...overrides,
  };
}

// ── Thread 1 messages (10 alternating inbound/outbound) ───────────────────────

export const THREAD_1_MESSAGES: SmsMessage[] = [
  makeMessage({
    message_id: "m01",
    thread_id: "thread-001",
    direction: "outbound",
    body: "Hi John, this is Mike from Pilot Electric.",
  }),
  makeMessage({
    message_id: "m02",
    thread_id: "thread-001",
    direction: "inbound",
    body: "Hi Mike, yes I've been waiting for your call.",
    status: "received",
    sent_at: null,
    delivered_at: null,
    received_at: "2026-05-26T08:01:00Z",
  }),
  makeMessage({
    message_id: "m03",
    thread_id: "thread-001",
    direction: "outbound",
    body: "I'll be at your place around 2pm for the panel upgrade.",
  }),
  makeMessage({
    message_id: "m04",
    thread_id: "thread-001",
    direction: "inbound",
    body: "Sounds great! I'll be home.",
    status: "received",
    sent_at: null,
    delivered_at: null,
    received_at: "2026-05-26T08:02:00Z",
  }),
  makeMessage({
    message_id: "m05",
    thread_id: "thread-001",
    direction: "outbound",
    body: "I'll need access to your basement electrical panel.",
  }),
  makeMessage({
    message_id: "m06",
    thread_id: "thread-001",
    direction: "inbound",
    body: "No problem. The door will be unlocked.",
    status: "received",
    sent_at: null,
    delivered_at: null,
    received_at: "2026-05-26T08:03:00Z",
  }),
  makeMessage({
    message_id: "m07",
    thread_id: "thread-001",
    direction: "outbound",
    body: "Do you have the breaker panel diagram?",
  }),
  makeMessage({
    message_id: "m08",
    thread_id: "thread-001",
    direction: "inbound",
    body: "Yes, I can email it to you.",
    status: "received",
    sent_at: null,
    delivered_at: null,
    received_at: "2026-05-26T08:04:00Z",
  }),
  makeMessage({
    message_id: "m09",
    thread_id: "thread-001",
    direction: "outbound",
    body: "Perfect, see you at 2pm!",
  }),
  makeMessage({
    message_id: "m10",
    thread_id: "thread-001",
    direction: "outbound",
    body: "On my way — ETA 10 mins.",
    status: "pending_send",
    sent_at: null,
    delivered_at: null,
  }),
];

export const THREAD_1: SmsThread = {
  thread_id: "thread-001",
  tenant_id: "tenant-001",
  customer_id: "customer-001",
  customer_name: "John Smith",
  customer_phone: "+15555551234",
  customer_sms_opted_out: false,
  customer_opted_out_at: null,
  tech_id: "tech-001",
  tech_name: "Mike Johnson",
  tenant_phone_number_id: "phone-001",
  status: "active",
  first_message_at: "2026-05-26T08:00:00Z",
  last_message_at: "2026-05-26T08:15:00Z",
  message_count: 10,
  unread_count: 0,
  originating_job_id: "job-001",
  originating_job_display: "Job #1042 — Panel Upgrade",
  created_at: "2026-05-26T08:00:00Z",
  updated_at: "2026-05-26T08:15:00Z",
  messages: THREAD_1_MESSAGES,
};

// ── Thread 2 with unread count ────────────────────────────────────────────────

export const THREAD_2: SmsThread = {
  thread_id: "thread-002",
  tenant_id: "tenant-001",
  customer_id: "customer-002",
  customer_name: "Sarah Connor",
  customer_phone: "+15555552345",
  customer_sms_opted_out: false,
  customer_opted_out_at: null,
  tech_id: "tech-001",
  tech_name: "Mike Johnson",
  tenant_phone_number_id: "phone-001",
  status: "active",
  first_message_at: "2026-05-25T14:00:00Z",
  last_message_at: "2026-05-26T09:32:00Z",
  message_count: 3,
  unread_count: 2,
  originating_job_id: "job-002",
  originating_job_display: "Job #1043 — Kitchen Rewire",
  created_at: "2026-05-25T14:00:00Z",
  updated_at: "2026-05-26T09:32:00Z",
  messages: [],
};

// ── Thread 3: Opted-out customer ──────────────────────────────────────────────

export const THREAD_3_OPTED_OUT: SmsThread = {
  thread_id: "thread-003",
  tenant_id: "tenant-001",
  customer_id: "customer-003",
  customer_name: "Robert Davis",
  customer_phone: "+15555553456",
  customer_sms_opted_out: true,
  customer_opted_out_at: "2026-05-20T10:05:00Z",
  tech_id: "tech-001",
  tech_name: "Mike Johnson",
  tenant_phone_number_id: "phone-001",
  status: "active",
  first_message_at: "2026-05-20T10:00:00Z",
  last_message_at: "2026-05-20T10:05:00Z",
  message_count: 2,
  unread_count: 0,
  originating_job_id: null,
  originating_job_display: null,
  created_at: "2026-05-20T10:00:00Z",
  updated_at: "2026-05-20T10:05:00Z",
  messages: [],
};

// ── Thread list items ─────────────────────────────────────────────────────────

export const THREAD_LIST_ITEMS: SmsThreadListItem[] = [
  {
    thread_id: "thread-001",
    customer_id: "customer-001",
    customer_name: "John Smith",
    last_message_preview: "On my way — ETA 10 mins.",
    last_message_at: "2026-05-26T08:15:00Z",
    last_message_direction: "outbound",
    unread_count: 0,
    originating_job_id: "job-001",
    originating_job_display: "Job #1042 — Panel Upgrade",
    customer_sms_opted_out: false,
  },
  {
    thread_id: "thread-002",
    customer_id: "customer-002",
    customer_name: "Sarah Connor",
    last_message_preview: "Actually, can you break down the cost?",
    last_message_at: "2026-05-26T09:32:00Z",
    last_message_direction: "inbound",
    unread_count: 2,
    originating_job_id: "job-002",
    originating_job_display: "Job #1043 — Kitchen Rewire",
    customer_sms_opted_out: false,
  },
  {
    thread_id: "thread-003",
    customer_id: "customer-003",
    customer_name: "Robert Davis",
    last_message_preview: "STOP",
    last_message_at: "2026-05-20T10:05:00Z",
    last_message_direction: "inbound",
    unread_count: 0,
    originating_job_id: null,
    originating_job_display: null,
    customer_sms_opted_out: true,
  },
];

// ── Quota fixtures ────────────────────────────────────────────────────────────

export const QUOTA_NORMAL: SmsQuotaStatus = {
  period_id: "period-2026-05",
  used_segments: 50,
  included_segments: 500,
  remaining_segments: 450,
  overage_segments: 0,
  cap_policy: "soft",
  period_start: "2026-05-01",
  period_end: "2026-05-31",
  blocked_reason: null,
  projected_month_end_segments: 80,
};

export const QUOTA_WARNING_80: SmsQuotaStatus = {
  period_id: "period-2026-05",
  used_segments: 420,
  included_segments: 500,
  remaining_segments: 80,
  overage_segments: 0,
  cap_policy: "soft",
  period_start: "2026-05-01",
  period_end: "2026-05-31",
  blocked_reason: null,
  projected_month_end_segments: 450,
};

export const QUOTA_HARD_BLOCKED: SmsQuotaStatus = {
  period_id: "period-2026-05",
  used_segments: 500,
  included_segments: 500,
  remaining_segments: 0,
  overage_segments: 0,
  cap_policy: "hard",
  period_start: "2026-05-01",
  period_end: "2026-05-31",
  blocked_reason: "monthly_quota_reached",
  projected_month_end_segments: 500,
};

export const QUOTA_SOFT_BLOCKED: SmsQuotaStatus = {
  period_id: "period-2026-05",
  used_segments: 500,
  included_segments: 500,
  remaining_segments: 0,
  overage_segments: 5,
  cap_policy: "soft",
  period_start: "2026-05-01",
  period_end: "2026-05-31",
  blocked_reason: null,
  projected_month_end_segments: 520,
};

export const QUOTA_OPTED_OUT: SmsQuotaStatus = {
  ...QUOTA_NORMAL,
  blocked_reason: "customer_opted_out",
};

// ── SSE event fixtures ────────────────────────────────────────────────────────

export const SSE_NEW_INBOUND_EVENT = {
  type: "customer_message_received",
  data: {
    thread_id: "thread-002",
    customer_id: "customer-002",
    message_id: "msg-sse-001",
    direction: "inbound",
    body_preview: "Hello, I have a question about the quote.",
    received_at: "2026-05-26T11:00:00Z",
  },
};
