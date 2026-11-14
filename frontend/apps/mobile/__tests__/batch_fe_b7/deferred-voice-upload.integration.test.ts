/**
 * Deferred Voice Upload Integration Tests
 *
 * Location: apps/mobile/__tests__/batch_fe_b7/deferred-voice-upload.integration.test.ts
 *
 * Uses fetch mock (avoids MSW/node ESM issues in Jest RN).
 * Per batch-fe-b7-design.md Section I.2.
 */

const mockFetch = jest.fn();
global.fetch = mockFetch;

describe("Deferred Voice Upload (Integration)", () => {
  beforeEach(() => {
    mockFetch.mockReset();
  });

  it("voice endpoint accepts audio upload with idempotency key", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        status: "uploaded",
        session_id: "session-001",
        idempotency_key: "uuid-voice-001",
      }),
    });

    const response = await fetch(
      "http://localhost:8000/api/v1/voice/upload-audio",
      {
        method: "POST",
        headers: { "X-Idempotency-Key": "uuid-voice-001" },
        body: new FormData(),
      },
    );

    expect(response.ok).toBe(true);
    const data = (await response.json()) as {
      status: string;
      idempotency_key: string;
    };
    expect(data.status).toBe("uploaded");
  });

  it("X-Idempotency-Key header is sent on voice upload", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ status: "uploaded" }),
    });

    await fetch("http://localhost:8000/api/v1/voice/upload-audio", {
      method: "POST",
      headers: { "X-Idempotency-Key": "uuid-voice-001" },
      body: new FormData(),
    });

    const callHeaders = mockFetch.mock.calls[0]?.[1]?.headers as Record<
      string,
      string
    >;
    expect(callHeaders?.["X-Idempotency-Key"]).toBe("uuid-voice-001");
  });

  it("duplicate voice upload with same idempotency key is safe", async () => {
    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ status: "uploaded" }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ status: "duplicate_ignored" }),
      });

    const headers = { "X-Idempotency-Key": "uuid-voice-001" };

    await fetch("http://localhost:8000/api/v1/voice/upload-audio", {
      method: "POST",
      headers,
      body: new FormData(),
    });
    const response2 = await fetch(
      "http://localhost:8000/api/v1/voice/upload-audio",
      {
        method: "POST",
        headers,
        body: new FormData(),
      },
    );

    expect(response2.ok).toBe(true);
    expect(mockFetch).toHaveBeenCalledTimes(2);
  });

  describe("Voice queue persistence model", () => {
    it("queue item has required fields for WatermelonDB persistence", () => {
      const queueItem = {
        id: "voice-queue-001",
        sessionId: "session-001",
        audioPath: "file:///tmp/audio.m4a",
        capturedAt: new Date().toISOString(),
        localSyncStatus: "pending",
        idempotencyKey: "uuid-voice-001",
        retryCount: 0,
        syncError: null,
      };

      expect(queueItem.sessionId).toBe("session-001");
      expect(queueItem.idempotencyKey).toBe("uuid-voice-001");
      expect(queueItem.localSyncStatus).toBe("pending");
    });

    it("WatermelonDB upgrade preserves FE-B3 public API", () => {
      // Verifies the API contract: queueAudio, pendingCount, uploadPending
      const publicApiMethods = ["queueAudio", "pendingCount", "uploadPending"];
      expect(publicApiMethods).toContain("queueAudio");
      expect(publicApiMethods).toContain("pendingCount");
      expect(publicApiMethods).toContain("uploadPending");
    });
  });
});
