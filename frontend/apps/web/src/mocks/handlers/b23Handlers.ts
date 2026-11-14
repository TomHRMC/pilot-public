/**
 * FE-B23 MSW Handlers — Dashboard BI + Notifications + Voice Sessions
 *
 * Location: apps/web/src/mocks/handlers/b23Handlers.ts
 *
 * Endpoints covered:
 *   GET  /api/v1/dashboard/at-risk-jobs
 *   GET  /api/v1/dashboard/pending-approvals-summary
 *   GET  /api/v1/notifications/in-app/recent
 *   POST /api/v1/notifications/in-app/mark-read
 *   GET  /api/v1/notifications/sse/notifications  (SSE — mock stream)
 *   GET  /api/v1/voice/sessions
 *   GET  /api/v1/voice/sessions/:sessionId/messages
 *   POST /api/v1/voice/sessions
 */

import { http, HttpResponse } from "msw";

// ── Fixtures ──────────────────────────────────────────────────────────────────

export const mockAtRiskJobs = [
  {
    job_id: "job-atrisk-001",
    customer_name: "Johnson Electrical",
    site_name: "Main Office",
    status_code: "in_progress",
    scheduled_start_at: "2026-06-16T09:00:00Z",
    actual_cost_cents: 48000,
    quoted_budget_cents: 53000,
    projected_margin_pct: 9.4,
  },
  {
    job_id: "job-atrisk-002",
    customer_name: "Smith Residence",
    site_name: null,
    status_code: "scheduled",
    scheduled_start_at: "2026-06-17T14:00:00Z",
    actual_cost_cents: 22000,
    quoted_budget_cents: 25000,
    projected_margin_pct: 12.0,
  },
];

export const mockPendingApprovals = {
  pending_quotes: 2,
  pending_field_issues: 1,
};

export const mockInAppNotifications = [
  {
    notification_id: "notif-001",
    category_id: "quote_status",
    body: "Quote QT-001 was approved by owner",
    deep_link_target: "/quotes/qt-001",
    priority: "standard",
    created_at: new Date(Date.now() - 2 * 60 * 1000).toISOString(),
    read_at: null,
  },
  {
    notification_id: "notif-002",
    category_id: "field_issue",
    body: "Field sync conflict escalated for review",
    deep_link_target: "/dashboard/approvals/field-issues",
    priority: "critical",
    created_at: new Date(Date.now() - 60 * 60 * 1000).toISOString(),
    read_at: null,
  },
  {
    notification_id: "notif-003",
    category_id: "sms",
    body: "New SMS from Johnson Electrical",
    deep_link_target: "/messages",
    priority: "standard",
    created_at: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
    read_at: new Date(Date.now() - 30 * 60 * 1000).toISOString(),
  },
];

export const mockVoiceSessions = [
  {
    session_id: "session-001",
    session_number: 5,
    title: "Johnson 200A panel quote",
    title_auto_generated: true,
    status: "ended",
    created_at: "2026-06-16T14:30:00Z",
    updated_at: "2026-06-16T14:45:00Z",
    archived_at: null,
    message_count: 8,
  },
  {
    session_id: "session-002",
    session_number: 4,
    title: "Davis service call estimate",
    title_auto_generated: true,
    status: "ended",
    created_at: "2026-06-15T10:15:00Z",
    updated_at: "2026-06-15T10:30:00Z",
    archived_at: null,
    message_count: 5,
  },
  {
    session_id: "session-003",
    session_number: 3,
    title: "Martinez properties quote",
    title_auto_generated: false,
    status: "ended",
    created_at: "2026-06-14T16:00:00Z",
    updated_at: "2026-06-14T16:20:00Z",
    archived_at: null,
    message_count: 12,
  },
];

export const mockVoiceMessages = [
  {
    message_id: "msg-001",
    session_id: "session-001",
    role: "user",
    content_text: "I need to quote a 200A panel upgrade for Johnson.",
    structured_content_json: null,
    created_at: "2026-06-16T14:30:10Z",
  },
  {
    message_id: "msg-002",
    session_id: "session-001",
    role: "assistant",
    content_text:
      "I can help with that. A 200A panel upgrade typically includes the panel, breakers, and labor. What's the current panel size?",
    structured_content_json: null,
    created_at: "2026-06-16T14:30:15Z",
  },
  {
    message_id: "msg-003",
    session_id: "session-001",
    role: "user",
    content_text: "It's currently 100A.",
    structured_content_json: null,
    created_at: "2026-06-16T14:30:45Z",
  },
];

// ── Handlers ──────────────────────────────────────────────────────────────────

export const b23Handlers = [
  // GET /api/v1/dashboard/at-risk-jobs
  http.get("/api/v1/dashboard/at-risk-jobs", () => {
    return HttpResponse.json({
      jobs: mockAtRiskJobs,
      total: mockAtRiskJobs.length,
    });
  }),

  // GET /api/v1/dashboard/pending-approvals-summary
  http.get("/api/v1/dashboard/pending-approvals-summary", () => {
    return HttpResponse.json(mockPendingApprovals);
  }),

  // GET /api/v1/notifications/in-app/recent
  http.get("/api/v1/notifications/in-app/recent", () => {
    return HttpResponse.json({ notifications: mockInAppNotifications });
  }),

  // POST /api/v1/notifications/in-app/mark-read
  http.post("/api/v1/notifications/in-app/mark-read", () => {
    return HttpResponse.json({ marked: true });
  }),

  // GET /api/v1/notifications/sse/notifications (SSE mock — return empty stream)
  http.get("/api/v1/notifications/sse/notifications", () => {
    return new HttpResponse("data: {}\n\n", {
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
      },
    });
  }),

  // GET /api/v1/voice/sessions
  http.get("/api/v1/voice/sessions/", () => {
    return HttpResponse.json({
      sessions: mockVoiceSessions,
      next_cursor: null,
      has_more: false,
    });
  }),

  // GET /api/v1/voice/sessions/:sessionId/messages
  http.get("/api/v1/voice/sessions/:sessionId/messages", () => {
    return HttpResponse.json({
      messages: mockVoiceMessages,
      next_cursor: null,
      has_more: false,
    });
  }),

  // POST /api/v1/voice/sessions (create new session)
  http.post("/api/v1/voice/sessions/", () => {
    return HttpResponse.json(
      {
        session_id: `session-new-${Date.now()}`,
        session_number: 6,
        title: null,
        title_auto_generated: false,
        status: "active",
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        archived_at: null,
        message_count: 0,
      },
      { status: 201 },
    );
  }),
];
