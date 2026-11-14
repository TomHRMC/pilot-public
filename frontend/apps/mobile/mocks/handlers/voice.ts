/**
 * MSW handlers — voice domain (mobile) — HTTP only
 *
 * Location: apps/mobile/mocks/handlers/voice.ts
 *
 * Covers (HTTP only — Jest-safe):
 *   - GET /api/v1/voice/sessions/         → SessionListResponse
 *   - POST /api/v1/voice/sessions/        → VoiceSession
 *   - DELETE /api/v1/voice/sessions/:id   → 204
 *   - GET /api/v1/voice/sessions/:id      → VoiceSession
 *   - GET /api/v1/voice/sessions/:id/messages → messages array
 *   - POST /api/v1/voice/upload-audio     → VoiceUploadResponse (202)
 *
 * The WebSocket handler for /api/v1/voice/stream lives in `./voice.ws.ts`
 * (dev-runtime only — NEVER imported by the Jest barrel). See
 * TEST-UPLIFT-1C §G Q1 / §F.1 for the isolation rationale: `ws.link()`
 * instantiates at module-evaluation time and poisons the Node/jsdom
 * environment, making the shared Jest server unusable.
 */

import { http, HttpResponse } from "msw";

// ── REST Handlers ─────────────────────────────────────────────────────────────

export const voiceHttpHandlers = [
  // GET /api/v1/voice/sessions/
  http.get("*/api/v1/voice/sessions/", () =>
    HttpResponse.json({
      sessions: [
        {
          session_id: "s-001",
          session_number: 1,
          title: "Johnson panel upgrade",
          title_auto_generated: true,
          status: "active",
          created_at: "2026-05-21T18:00:00Z",
          updated_at: "2026-05-21T18:05:00Z",
          archived_at: null,
          message_count: 6,
        },
      ],
      next_cursor: null,
      has_more: false,
    }),
  ),

  // POST /api/v1/voice/sessions/
  http.post("*/api/v1/voice/sessions/", () =>
    HttpResponse.json(
      {
        session_id: `s-${Date.now()}`,
        session_number: 2,
        title: null,
        title_auto_generated: false,
        status: "active",
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        archived_at: null,
        message_count: 0,
      },
      { status: 201 },
    ),
  ),

  // DELETE /api/v1/voice/sessions/:id
  http.delete(
    "*/api/v1/voice/sessions/:id",
    () => new HttpResponse(null, { status: 204 }),
  ),

  // GET /api/v1/voice/sessions/:id
  http.get("*/api/v1/voice/sessions/:id", ({ params }) =>
    HttpResponse.json({
      session_id: params.id,
      session_number: 1,
      title: "Johnson panel upgrade",
      title_auto_generated: true,
      status: "active",
      created_at: "2026-05-21T18:00:00Z",
      updated_at: "2026-05-21T18:05:00Z",
      archived_at: null,
      message_count: 2,
    }),
  ),

  // GET /api/v1/voice/sessions/:id/messages
  http.get("*/api/v1/voice/sessions/:id/messages", ({ params }) =>
    HttpResponse.json({
      messages: [
        {
          message_id: "msg-001",
          session_id: params.id,
          role: "user",
          content_text: "Create a quote for Tom Johnson",
          structured_content_json: null,
          created_at: "2026-05-21T18:01:00Z",
        },
        {
          message_id: "msg-002",
          session_id: params.id,
          role: "assistant",
          content_text: "Matched Tom Johnson at 42 Oak Street. Different one?",
          structured_content_json: {
            render_mode: "live",
            content_type: "quote_preview",
            entity_id: "q-mock-001",
            snapshot_payload: null,
            captured_at: "2026-05-21T18:01:05Z",
          },
          created_at: "2026-05-21T18:01:05Z",
        },
      ],
    }),
  ),

  // POST /api/v1/voice/upload-audio
  http.post("*/api/v1/voice/upload-audio", () =>
    HttpResponse.json(
      {
        voice_command_log_id: 42,
        idempotency_uuid: "a1b2c3d4-0000-0000-0000-000000000001",
        processing_status: "transcribing",
      },
      { status: 202 },
    ),
  ),
];
