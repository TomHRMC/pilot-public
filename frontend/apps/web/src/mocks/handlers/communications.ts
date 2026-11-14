/**
 * MSW Handlers — Communications domain
 *
 * Location: apps/web/src/mocks/handlers/communications.ts
 *
 * Implements the four endpoints consumed by FE-B6:
 *   POST /api/v1/communications/preview
 *   POST /api/v1/communications/send
 *   GET  /api/v1/customers/{id}/communications
 *   GET  /api/v1/communications/comm-template-types
 *
 * MSW two-step enforcement (§D Design): The send handler tracks a
 * request-scoped `previewCalled` session flag. Calling POST /send
 * without a prior POST /preview in the same test session returns
 * 403 { detail: "preview_not_called" }.
 *
 * This is TEST INFRASTRUCTURE ONLY — the real backend does not enforce call order.
 */

import { http, HttpResponse } from "msw";
import type {
  CommunicationPreviewResponse,
  CommunicationSendResponse,
  CommunicationHistoryItem,
  CommTemplateTypeResponse,
} from "@pilot/ui";

// ── Session state (test-scoped enforcement) ───────────────────────────────────

/** Tracks whether POST /preview was called before POST /send in the current test */
let previewCalled = false;
/** Tracks whether quota is exhausted (set by test helpers) */
let quotaExhausted = false;
/** Force next send to return failure (set by test helpers) */
let forceSendFailure = false;

/** Call this from test setup to reset enforcement state */
export function resetCommsHandlerState() {
  previewCalled = false;
  quotaExhausted = false;
  forceSendFailure = false;
}
export function setQuotaExhausted(value: boolean) {
  quotaExhausted = value;
}
export function setForceSendFailure(value: boolean) {
  forceSendFailure = value;
}

// ── Fixture data ──────────────────────────────────────────────────────────────

const MVP_TEMPLATES: CommTemplateTypeResponse[] = [
  {
    code: "on_my_way",
    slug: "on-my-way",
    name: "On my way",
    description: "Let customer know you're en route",
    category: "appointment",
    preferred_channel: "sms",
    initiator: "technician",
    requires_approval: false,
    send_mode: "immediate",
    trigger_event: null,
    is_system: true,
    sort_order: 1,
  },
  {
    code: "running_late",
    slug: "running-late",
    name: "Running late",
    description: "Notify customer of delay",
    category: "delay",
    preferred_channel: "sms",
    initiator: "technician",
    requires_approval: false,
    send_mode: "immediate",
    trigger_event: null,
    is_system: true,
    sort_order: 2,
  },
  {
    code: "arrived",
    slug: "arrived",
    name: "Arrived",
    description: "Notify customer you've arrived",
    category: "job_status",
    preferred_channel: "sms",
    initiator: "technician",
    requires_approval: false,
    send_mode: "immediate",
    trigger_event: null,
    is_system: true,
    sort_order: 3,
  },
  {
    code: "job_complete",
    slug: "job-complete",
    name: "Job complete",
    description: "Notify customer job is done",
    category: "job_status",
    preferred_channel: "sms",
    initiator: "technician",
    requires_approval: false,
    send_mode: "immediate",
    trigger_event: null,
    is_system: true,
    sort_order: 4,
  },
  {
    code: "appointment_reminder",
    slug: "appointment-reminder",
    name: "Appointment reminder",
    description: "Send reminder before scheduled job",
    category: "appointment",
    preferred_channel: "sms",
    initiator: "technician",
    requires_approval: false,
    send_mode: "scheduled",
    trigger_event: "before_appointment",
    is_system: true,
    sort_order: 5,
  },
  {
    code: "follow_up",
    slug: "follow-up",
    name: "Follow up",
    description: "Check in after job completion",
    category: "job_status",
    preferred_channel: "sms",
    initiator: "technician",
    requires_approval: false,
    send_mode: "manual",
    trigger_event: null,
    is_system: true,
    sort_order: 6,
  },
];

const TEMPLATE_BODIES: Record<string, string> = {
  on_my_way: "Hi! I'm on my way, ETA about {eta_minutes} minutes.",
  running_late:
    "Hi, I'm running about {eta_minutes} minutes behind. Sorry for the inconvenience!",
  arrived: "Hi! I've arrived. I'll be at your door shortly.",
  job_complete:
    "Hi! The job is complete. Let me know if you have any questions.",
  appointment_reminder:
    "Just a reminder about your appointment tomorrow. See you then!",
  follow_up:
    "Hi! Just checking in after our recent work. Hope everything is working well!",
};

const HISTORY_FIXTURE: CommunicationHistoryItem[] = [
  {
    communication_id: "comm-001",
    template_code: "on_my_way",
    actual_channel: "sms",
    channel_override_flag: false,
    customer_preferred_channel: "sms",
    rendered_message: "Hi! I'm on my way, ETA about 20 minutes.",
    rendered_subject: null,
    status: "sent",
    sent_at: new Date(Date.now() - 86400000).toISOString(),
    sender_user_id: "user-001",
    job_id: "job-001",
  },
  {
    communication_id: "comm-002",
    template_code: "job_complete",
    actual_channel: "email",
    channel_override_flag: true,
    customer_preferred_channel: "sms",
    rendered_message:
      "Hi! The job is complete. Let me know if you have any questions.",
    rendered_subject: "Job completed",
    status: "sent",
    sent_at: new Date(Date.now() - 3600000).toISOString(),
    sender_user_id: "user-001",
    job_id: "job-001",
  },
];

// ── Recent communications aggregate fixture ───────────────────────────────────
//
// COMMS-UI-B1: Expanded to 55 items with varied customers, both directions,
// and email rows so the Email pill filter is provably exercised (D-1).
// The first 3 items preserve the original fixture data for backward compat.

const RECENT_COMMS_CUSTOMERS = [
  { id: "customer-001", name: "John Smith" },
  { id: "customer-002", name: "Sarah Connor" },
  { id: "customer-003", name: "Bob Davis" },
  { id: "customer-004", name: "Mary Johnson" },
];

const RECENT_COMMS_FIXTURE = Array.from({ length: 55 }, (_, i) => {
  const customer = RECENT_COMMS_CUSTOMERS[i % RECENT_COMMS_CUSTOMERS.length];
  // Mostly SMS; every 7th item is email (D-1: email has no real data, fixture only)
  const channel = i % 7 === 0 ? "email" : "sms";
  const direction = i % 2 === 0 ? "outbound" : "inbound";
  // Spread across last ~55 hours (1 hour apart) — relative to now for date-range tests
  const createdAt = new Date(Date.now() - (i + 1) * 3600000).toISOString();
  return {
    id: `comm-${100 + i}`,
    customer_id: customer.id,
    customer_name: customer.name,
    channel,
    direction,
    body: `Message ${i + 1} from ${customer.name}`,
    created_at: createdAt,
  };
});

// ── Handlers ──────────────────────────────────────────────────────────────────

export const communicationHandlers = [
  // 0. Cross-customer recent communications aggregate
  // COMMS-UI-B1: migrated page/page_size → limit/offset + filter params
  http.get("/api/v1/communications/recent", ({ request }) => {
    const url = new URL(request.url);
    const limit = parseInt(url.searchParams.get("limit") ?? "50", 10);
    const offset = parseInt(url.searchParams.get("offset") ?? "0", 10);
    const customerSearch = url.searchParams.get("customer_search") ?? "";
    const channel = url.searchParams.get("channel") ?? "";
    const sentFrom = url.searchParams.get("sent_from") ?? "";
    const sentTo = url.searchParams.get("sent_to") ?? "";

    let filtered = RECENT_COMMS_FIXTURE;

    // customer_search: case-insensitive match on customer_name
    if (customerSearch) {
      const search = customerSearch.toLowerCase();
      filtered = filtered.filter((item) =>
        item.customer_name.toLowerCase().includes(search),
      );
    }

    // channel: exact match (sms | email)
    if (channel) {
      filtered = filtered.filter((item) => item.channel === channel);
    }

    // sent_from: created_at >= sent_from (start of day)
    if (sentFrom) {
      const fromTime = new Date(sentFrom).getTime();
      filtered = filtered.filter(
        (item) => new Date(item.created_at).getTime() >= fromTime,
      );
    }

    // sent_to: created_at <= sent_to (end of day)
    if (sentTo) {
      const toDate = new Date(sentTo);
      toDate.setHours(23, 59, 59, 999);
      const toTime = toDate.getTime();
      filtered = filtered.filter(
        (item) => new Date(item.created_at).getTime() <= toTime,
      );
    }

    const items = filtered.slice(offset, offset + limit);
    return HttpResponse.json({
      items,
      total: filtered.length,
      limit,
      offset,
    });
  }),

  // 1. Template types
  http.get("/api/v1/communications/comm-template-types", ({ request }) => {
    const url = new URL(request.url);
    const initiator = url.searchParams.get("initiator");
    const templates = initiator
      ? MVP_TEMPLATES.filter((t) => t.initiator === initiator)
      : MVP_TEMPLATES;
    return HttpResponse.json({ items: templates });
  }),

  // 2. Preview — never writes; returns rendered body + editable variables
  http.post("/api/v1/communications/preview", async ({ request }) => {
    const body = (await request.json()) as {
      customer_id: string;
      template_code: string;
      variables: Record<string, unknown>;
      channel_override?: string | null;
    };

    // Set the preview-called flag for enforcement
    previewCalled = true;

    const templateBody =
      TEMPLATE_BODIES[body.template_code] ??
      "Hello! Your message has been sent.";

    const rendered = templateBody.replace(
      /\{eta_minutes\}/g,
      String(body.variables?.eta_minutes ?? 20),
    );

    const actualChannel =
      body.channel_override ??
      MVP_TEMPLATES.find((t) => t.code === body.template_code)
        ?.preferred_channel ??
      "sms";

    const response: CommunicationPreviewResponse = {
      rendered_subject:
        actualChannel === "email" ? `Update from your technician` : null,
      rendered_body: rendered,
      recipient_name: "Test Customer",
      recipient_address:
        actualChannel === "sms" ? "+15555551234" : "customer@test.com",
      actual_channel: actualChannel as "sms" | "email",
      editable_variables:
        body.template_code === "on_my_way" ||
        body.template_code === "running_late"
          ? [
              {
                name: "eta_minutes",
                value: body.variables?.eta_minutes ?? 20,
                label: "ETA (minutes)",
                type: "time_minutes" as const,
              },
            ]
          : [],
    };

    return HttpResponse.json(response);
  }),

  // 3. Send — enforces preview-before-send in tests
  http.post("/api/v1/communications/send", async ({ request }) => {
    const body = (await request.json()) as {
      customer_id: string;
      template_code: string;
      job_id?: string | null;
      variables: Record<string, unknown>;
      channel_override?: string | null;
    };

    // Enforcement: preview must have been called first
    if (!previewCalled) {
      return HttpResponse.json(
        { detail: "preview_not_called" },
        { status: 403 },
      );
    }

    // Quota exhaustion simulation
    if (quotaExhausted) {
      return HttpResponse.json(
        { detail: "Monthly SMS quota exhausted" },
        { status: 429 },
      );
    }

    // Forced failure simulation
    if (forceSendFailure) {
      return HttpResponse.json(
        { detail: "Carrier delivery failed" },
        { status: 422 },
      );
    }

    const templateBody =
      TEMPLATE_BODIES[body.template_code] ??
      "Hello! Your message has been sent.";
    const rendered = templateBody.replace(
      /\{eta_minutes\}/g,
      String(body.variables?.eta_minutes ?? 20),
    );

    const actualChannel =
      body.channel_override ??
      MVP_TEMPLATES.find((t) => t.code === body.template_code)
        ?.preferred_channel ??
      "sms";

    const response: CommunicationSendResponse = {
      communication_id: `comm-${Date.now()}`,
      template_code: body.template_code,
      actual_channel: actualChannel,
      channel_override_flag:
        body.channel_override !== null && body.channel_override !== undefined,
      status: "pending",
      rendered_message: rendered,
      rendered_subject:
        actualChannel === "email" ? "Update from your technician" : null,
      recipient_address:
        actualChannel === "sms" ? "+15555551234" : "customer@test.com",
      sent_at: null,
    };

    // Reset preview flag after successful send
    previewCalled = false;

    return HttpResponse.json(response, { status: 201 });
  }),

  // 4. Customer communications history
  http.get("/api/v1/customers/:customerId/communications", ({ request }) => {
    const url = new URL(request.url);
    const page = parseInt(url.searchParams.get("page") ?? "1", 10);
    const pageSize = parseInt(url.searchParams.get("page_size") ?? "20", 10);

    const start = (page - 1) * pageSize;
    const items = HISTORY_FIXTURE.slice(start, start + pageSize);

    return HttpResponse.json({
      items,
      total: HISTORY_FIXTURE.length,
      page,
      page_size: pageSize,
    });
  }),
];
