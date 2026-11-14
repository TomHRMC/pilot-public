/**
 * MSW Handlers — Customer Communications Preview/Send (Mobile) — FE-B6
 *
 * Location: apps/mobile/mocks/handlers/customerCommsPreviewHandlers.ts
 *
 * Covers the FE-B6 comms flow: template list, preview, send, and history.
 * Identical API contract to apps/web/src/mocks/handlers/communications.ts.
 * Duplicated because apps cannot cross-import each other.
 * Keep in sync manually — both files implement the same MSW spec.
 *
 * Note: This is DIFFERENT from communicationsHandlers.ts (FE-B10 SMS threads/inbox).
 */

import { http, HttpResponse } from "msw";
import type {
  CommunicationPreviewResponse,
  CommunicationSendResponse,
  CommunicationHistoryItem,
  CommTemplateTypeResponse,
} from "@pilot/ui";

// ── Session state (test-scoped) ───────────────────────────────────────────────

let previewCalled = false;
let quotaExhausted = false;
let forceSendFailure = false;

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

// ── Handlers ──────────────────────────────────────────────────────────────────

export const customerCommsPreviewHandlers = [
  http.get("*/api/v1/communications/comm-template-types", ({ request }) => {
    const url = new URL(request.url);
    const initiator = url.searchParams.get("initiator");
    const templates = initiator
      ? MVP_TEMPLATES.filter((t) => t.initiator === initiator)
      : MVP_TEMPLATES;
    return HttpResponse.json({ items: templates });
  }),

  http.post("*/api/v1/communications/preview", async ({ request }) => {
    const body = (await request.json()) as {
      customer_id: string;
      template_code: string;
      variables: Record<string, unknown>;
      channel_override?: string | null;
    };
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
        actualChannel === "email" ? "Update from your technician" : null,
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

  http.post("*/api/v1/communications/send", async ({ request }) => {
    const body = (await request.json()) as {
      customer_id: string;
      template_code: string;
      job_id?: string | null;
      variables: Record<string, unknown>;
      channel_override?: string | null;
    };
    if (!previewCalled)
      return HttpResponse.json(
        { detail: "preview_not_called" },
        { status: 403 },
      );
    if (quotaExhausted)
      return HttpResponse.json(
        { detail: "Monthly SMS quota exhausted" },
        { status: 429 },
      );
    if (forceSendFailure)
      return HttpResponse.json(
        { detail: "Carrier delivery failed" },
        { status: 422 },
      );
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
    previewCalled = false;
    return HttpResponse.json(response, { status: 201 });
  }),

  http.get("*/api/v1/customers/:customerId/communications", ({ request }) => {
    const url = new URL(request.url);
    const page = parseInt(url.searchParams.get("page") ?? "1", 10);
    const pageSize = parseInt(url.searchParams.get("page_size") ?? "20", 10);
    const fixture: CommunicationHistoryItem[] = [
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
        rendered_message: "Hi! The job is complete.",
        rendered_subject: "Job completed",
        status: "sent",
        sent_at: new Date(Date.now() - 3600000).toISOString(),
        sender_user_id: "user-001",
        job_id: "job-001",
      },
    ];
    const start = (page - 1) * pageSize;
    return HttpResponse.json({
      items: fixture.slice(start, start + pageSize),
      total: fixture.length,
      page,
      page_size: pageSize,
    });
  }),
];
