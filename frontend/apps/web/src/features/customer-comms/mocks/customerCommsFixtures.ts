/**
 * customerCommsFixtures.ts — Web SMS Customer Comms Fixture Data
 *
 * Location: apps/web/src/features/customer-comms/mocks/customerCommsFixtures.ts
 * Used by: MSW handlers and integration tests for FE-B10
 */

import type {
  SmsThread,
  SmsMessage,
  SmsThreadListItem,
  SmsQuotaStatus,
  UnroutedMessage,
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

// ── Thread 1: Active thread between tech-001 and John Smith ───────────────────

export const THREAD_1_MESSAGES: SmsMessage[] = [
  makeMessage({
    message_id: "msg-001",
    thread_id: "thread-001",
    direction: "outbound",
    body: "Hi John, I'll be at your place around 2pm for the panel upgrade.",
    sent_at: "2026-05-26T08:00:00Z",
    delivered_at: "2026-05-26T08:00:03Z",
    received_at: null,
  }),
  makeMessage({
    message_id: "msg-002",
    thread_id: "thread-001",
    direction: "inbound",
    body: "Sounds good! I'll be home.",
    sent_at: null,
    delivered_at: null,
    received_at: "2026-05-26T08:05:00Z",
    status: "received",
  }),
  makeMessage({
    message_id: "msg-003",
    thread_id: "thread-001",
    direction: "outbound",
    body: "Perfect. I'll need access to your electrical panel in the basement.",
    sent_at: "2026-05-26T08:06:00Z",
    delivered_at: "2026-05-26T08:06:02Z",
    received_at: null,
  }),
  makeMessage({
    message_id: "msg-004",
    thread_id: "thread-001",
    direction: "inbound",
    body: "No problem, I'll leave the door unlocked. Do you need anything else?",
    sent_at: null,
    delivered_at: null,
    received_at: "2026-05-26T08:10:00Z",
    status: "received",
  }),
  makeMessage({
    message_id: "msg-005",
    thread_id: "thread-001",
    direction: "outbound",
    body: "Just the access — thanks! See you at 2pm.",
    sent_at: "2026-05-26T08:11:00Z",
    delivered_at: "2026-05-26T08:11:02Z",
    received_at: null,
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
  last_message_at: "2026-05-26T08:11:00Z",
  message_count: 5,
  unread_count: 0,
  originating_job_id: "job-001",
  originating_job_display: "Job 1042 — Panel Upgrade",
  created_at: "2026-05-26T08:00:00Z",
  updated_at: "2026-05-26T08:11:00Z",
  messages: THREAD_1_MESSAGES,
};

// ── Thread 2: Thread with unread count ────────────────────────────────────────

export const THREAD_2_MESSAGES: SmsMessage[] = [
  makeMessage({
    message_id: "msg-010",
    thread_id: "thread-002",
    direction: "outbound",
    body: "Hi Sarah, the quote for your kitchen rewiring is ready. Total: $1,450.",
    sent_at: "2026-05-25T14:00:00Z",
    delivered_at: "2026-05-25T14:00:03Z",
    received_at: null,
  }),
  makeMessage({
    message_id: "msg-011",
    thread_id: "thread-002",
    direction: "inbound",
    body: "That's a bit more than I expected. Can we discuss?",
    sent_at: null,
    delivered_at: null,
    received_at: "2026-05-26T09:30:00Z",
    status: "received",
  }),
  makeMessage({
    message_id: "msg-012",
    thread_id: "thread-002",
    direction: "inbound",
    body: "Actually, can you break down the cost?",
    sent_at: null,
    delivered_at: null,
    received_at: "2026-05-26T09:32:00Z",
    status: "received",
  }),
];

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
  originating_job_display: "Job 1043 — Kitchen Rewire",
  created_at: "2026-05-25T14:00:00Z",
  updated_at: "2026-05-26T09:32:00Z",
  messages: THREAD_2_MESSAGES,
};

// ── Thread 3: Opted-out customer ──────────────────────────────────────────────

export const THREAD_3_MESSAGES: SmsMessage[] = [
  makeMessage({
    message_id: "msg-020",
    thread_id: "thread-003",
    direction: "outbound",
    body: "Hi Robert, we have a follow-up inspection scheduled for tomorrow.",
    sent_at: "2026-05-20T10:00:00Z",
    delivered_at: "2026-05-20T10:00:02Z",
    received_at: null,
  }),
  makeMessage({
    message_id: "msg-021",
    thread_id: "thread-003",
    direction: "inbound",
    body: "STOP",
    sent_at: null,
    delivered_at: null,
    received_at: "2026-05-20T10:05:00Z",
    status: "received",
  }),
];

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
  messages: THREAD_3_MESSAGES,
};

// ── Thread list items ─────────────────────────────────────────────────────────

export const THREAD_LIST_ITEMS: SmsThreadListItem[] = [
  {
    thread_id: "thread-001",
    customer_id: "customer-001",
    customer_name: "John Smith",
    last_message_preview: "Just the access — thanks! See you at 2pm.",
    last_message_at: "2026-05-26T08:11:00Z",
    last_message_direction: "outbound",
    unread_count: 0,
    originating_job_id: "job-001",
    originating_job_display: "Job 1042 — Panel Upgrade",
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
    originating_job_display: "Job 1043 — Kitchen Rewire",
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
  ...QUOTA_NORMAL,
  used_segments: 420,
  remaining_segments: 80,
  // 80 / 500 = 16% remaining — triggers warning at ≤20%
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

// ── Unrouted messages ─────────────────────────────────────────────────────────

export const UNROUTED_MESSAGES: UnroutedMessage[] = [
  {
    unrouted_id: "unrouted-001",
    tenant_id: "tenant-001",
    from_number: "+1 (555) ***-9999",
    to_number: "+15555550100",
    body: "Hi, I need an electrician to look at my breaker box. It keeps tripping.",
    received_at: "2026-05-26T10:00:00Z",
    attempted_customer_match: null,
  },
  {
    unrouted_id: "unrouted-002",
    tenant_id: "tenant-001",
    from_number: "+1 (555) ***-8888",
    to_number: "+15555550100",
    body: "Is this the electrical company? I need to schedule an appointment.",
    received_at: "2026-05-26T10:30:00Z",
    attempted_customer_match: "customer-004",
  },
];

// ── Recent messages widget ────────────────────────────────────────────────────

export const RECENT_MESSAGES = {
  messages: [
    {
      message_id: "msg-012",
      thread_id: "thread-002",
      customer_id: "customer-002",
      customer_name: "Sarah Connor",
      direction: "inbound" as const,
      body_preview: "Actually, can you break down the cost?",
      received_at: "2026-05-26T09:32:00Z",
      tech_name: "Mike Johnson",
    },
    {
      message_id: "msg-011",
      thread_id: "thread-002",
      customer_id: "customer-002",
      customer_name: "Sarah Connor",
      direction: "inbound" as const,
      body_preview: "That's a bit more than I expected. Can we discuss?",
      received_at: "2026-05-26T09:30:00Z",
      tech_name: "Mike Johnson",
    },
    {
      message_id: "msg-005",
      thread_id: "thread-001",
      customer_id: "customer-001",
      customer_name: "John Smith",
      direction: "outbound" as const,
      body_preview: "Just the access — thanks! See you at 2pm.",
      received_at: "2026-05-26T08:11:00Z",
      tech_name: "Mike Johnson",
    },
    {
      message_id: "msg-004",
      thread_id: "thread-001",
      customer_id: "customer-001",
      customer_name: "John Smith",
      direction: "inbound" as const,
      body_preview:
        "No problem, I'll leave the door unlocked. Do you need anything else?",
      received_at: "2026-05-26T08:10:00Z",
      tech_name: "Mike Johnson",
    },
    {
      message_id: "msg-003",
      thread_id: "thread-001",
      customer_id: "customer-001",
      customer_name: "John Smith",
      direction: "outbound" as const,
      body_preview:
        "Perfect. I'll need access to your electrical panel in the basement.",
      received_at: "2026-05-26T08:06:00Z",
      tech_name: "Mike Johnson",
    },
    {
      message_id: "msg-002",
      thread_id: "thread-001",
      customer_id: "customer-001",
      customer_name: "John Smith",
      direction: "inbound" as const,
      body_preview: "Sounds good! I'll be home.",
      received_at: "2026-05-26T08:05:00Z",
      tech_name: "Mike Johnson",
    },
    {
      message_id: "msg-001",
      thread_id: "thread-001",
      customer_id: "customer-001",
      customer_name: "John Smith",
      direction: "outbound" as const,
      body_preview:
        "Hi John, I'll be at your place around 2pm for the panel upgrade.",
      received_at: "2026-05-26T08:00:00Z",
      tech_name: "Mike Johnson",
    },
    {
      message_id: "msg-021",
      thread_id: "thread-003",
      customer_id: "customer-003",
      customer_name: "Robert Davis",
      direction: "inbound" as const,
      body_preview: "STOP",
      received_at: "2026-05-20T10:05:00Z",
      tech_name: "Mike Johnson",
    },
    {
      message_id: "msg-020",
      thread_id: "thread-003",
      customer_id: "customer-003",
      customer_name: "Robert Davis",
      direction: "outbound" as const,
      body_preview:
        "Hi Robert, we have a follow-up inspection scheduled for tomorrow.",
      received_at: "2026-05-20T10:00:00Z",
      tech_name: "Mike Johnson",
    },
    {
      message_id: "msg-010",
      thread_id: "thread-002",
      customer_id: "customer-002",
      customer_name: "Sarah Connor",
      direction: "outbound" as const,
      body_preview:
        "Hi Sarah, the quote for your kitchen rewiring is ready. Total: $1,450.",
      received_at: "2026-05-25T14:00:00Z",
      tech_name: "Mike Johnson",
    },
  ],
};

// ── Customer comms history (web) ──────────────────────────────────────────────

export const CUSTOMER_COMMS_HISTORY = {
  threads: [THREAD_1, THREAD_2],
  customer_opted_out: false,
  opted_out_at: null,
};

export const CUSTOMER_COMMS_HISTORY_OPTED_OUT = {
  threads: [THREAD_3_OPTED_OUT],
  customer_opted_out: true,
  opted_out_at: "2026-05-20T10:05:00Z",
};

// ── SSE events ────────────────────────────────────────────────────────────────

export const SSE_CUSTOMER_MESSAGE_RECEIVED_EVENT = {
  type: "customer_message_received",
  data: {
    thread_id: "thread-002",
    customer_id: "customer-002",
    message_id: "msg-013",
    direction: "inbound",
    body_preview: "Hello, I have a question about the quote.",
    received_at: "2026-05-26T11:00:00Z",
  },
};
