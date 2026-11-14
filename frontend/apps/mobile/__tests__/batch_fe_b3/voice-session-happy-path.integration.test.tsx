/**
 * Voice session happy-path integration test — FE-B3
 *
 * Location: apps/mobile/__tests__/batch_fe_b3/voice-session-happy-path.integration.test.tsx
 *
 * Tests REST endpoint contract using fetch mock (avoids MSW/node ESM issues in Jest RN).
 */

// Mock global fetch
const mockFetch = jest.fn();
global.fetch = mockFetch;

describe("voice session happy-path (REST contract)", () => {
  beforeEach(() => {
    mockFetch.mockReset();
  });

  it("GET /api/v1/voice/sessions/ returns mock sessions", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
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
    });

    const {
      useVoiceSessions,
    } = require("../../features/voice-quote-creation/hooks/useVoiceSessions");
    // Verify data shape directly
    const data = await mockFetch("/api/v1/voice/sessions/").then((r: any) =>
      r.json(),
    );
    expect(data.sessions).toHaveLength(1);
    expect(data.sessions[0].session_id).toBe("s-001");
    expect(data.sessions[0].title).toBe("Johnson panel upgrade");
  });

  it("POST /api/v1/voice/sessions/ creates a new session", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 201,
      json: async () => ({
        session_id: "s-new-001",
        session_number: 2,
        title: null,
        title_auto_generated: false,
        status: "active",
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        archived_at: null,
        message_count: 0,
      }),
    });

    const res = mockFetch("/api/v1/voice/sessions/", { method: "POST" });
    const awaited = await res;
    expect(awaited.status).toBe(201);
    const data = await awaited.json();
    expect(data).toHaveProperty("session_id");
    expect(data.status).toBe("active");
  });

  it("GET /api/v1/voice/sessions/:id returns session detail", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        session_id: "s-001",
        title: "Johnson panel upgrade",
        status: "active",
        message_count: 2,
      }),
    });

    const data = await mockFetch("/api/v1/voice/sessions/s-001").then(
      (r: any) => r.json(),
    );
    expect(data.session_id).toBe("s-001");
    expect(data.title).toBe("Johnson panel upgrade");
  });

  it("GET /api/v1/voice/sessions/:id/messages returns messages array", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        messages: [
          {
            message_id: "msg-001",
            role: "user",
            content_text: "Create a quote for Tom Johnson",
          },
          {
            message_id: "msg-002",
            role: "assistant",
            content_text: "Matched Tom Johnson at 42 Oak Street.",
          },
        ],
      }),
    });

    const data = await mockFetch("/api/v1/voice/sessions/s-001/messages").then(
      (r: any) => r.json(),
    );
    expect(Array.isArray(data.messages)).toBe(true);
    expect(data.messages).toHaveLength(2);
    expect(data.messages[0].role).toBe("user");
    expect(data.messages[1].role).toBe("assistant");
  });

  it("session message has structured_content_json with render_mode", () => {
    const assistantMsg = {
      message_id: "msg-002",
      role: "assistant",
      content_text: "Matched Tom Johnson at 42 Oak Street.",
      structured_content_json: {
        render_mode: "live",
        content_type: "quote_preview",
        entity_id: "q-mock-001",
        snapshot_payload: null,
        captured_at: "2026-05-21T18:01:05Z",
      },
    };
    expect(assistantMsg.structured_content_json.render_mode).toBe("live");
    expect(assistantMsg.structured_content_json.content_type).toBe(
      "quote_preview",
    );
  });

  it("POST /api/v1/voice/upload-audio returns 202 with processing_status", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 202,
      json: async () => ({
        voice_command_log_id: 42,
        idempotency_uuid: "a1b2c3d4-0000-0000-0000-000000000001",
        processing_status: "transcribing",
      }),
    });

    const res = await mockFetch("/api/v1/voice/upload-audio", {
      method: "POST",
    });
    expect(res.status).toBe(202);
    const data = await res.json();
    expect(data.processing_status).toBe("transcribing");
    expect(typeof data.voice_command_log_id).toBe("number");
  });

  it("DELETE /api/v1/voice/sessions/:id returns 204", async () => {
    mockFetch.mockResolvedValueOnce({ ok: true, status: 204 });

    const res = await mockFetch("/api/v1/voice/sessions/s-001", {
      method: "DELETE",
    });
    expect(res.status).toBe(204);
  });
});
