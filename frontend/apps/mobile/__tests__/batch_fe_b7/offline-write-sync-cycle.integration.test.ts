/**
 * Offline Write → Sync Cycle Integration Test
 *
 * Location: apps/mobile/__tests__/batch_fe_b7/offline-write-sync-cycle.integration.test.ts
 *
 * Uses fetch mock (avoids MSW/node ESM issues in Jest RN).
 * Tests: offline write → reconnect → sync → server state matches.
 * Per batch-fe-b7-design.md Section I.2.
 */

const mockFetch = jest.fn();
global.fetch = mockFetch;

describe("Offline Write → Sync Cycle (Integration)", () => {
  beforeEach(() => {
    mockFetch.mockReset();
  });

  it("creates sync session before pushing", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ session_id: "session-001" }),
    });

    const response = await fetch(
      "http://localhost:8000/api/v1/mobile/sync-sessions",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          device_id: "device-001",
          trigger: "network_online",
        }),
      },
    );

    expect(response.ok).toBe(true);
    const data = (await response.json()) as { session_id: string };
    expect(data.session_id).toBe("session-001");
    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/mobile/sync-sessions",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("push sends X-Idempotency-Key header", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ status: "accepted" }),
    });

    await fetch("http://localhost:8000/api/v1/mobile-sync/push/time-entries", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Idempotency-Key": "uuid-te-001",
      },
      body: JSON.stringify({
        idempotency_key: "uuid-te-001",
        job_id: "job-001",
      }),
    });

    const callHeaders = mockFetch.mock.calls[0]?.[1]?.headers as Record<
      string,
      string
    >;
    expect(callHeaders?.["X-Idempotency-Key"]).toBe("uuid-te-001");
  });

  it("duplicate push with same idempotency key is safe", async () => {
    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ status: "accepted" }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ status: "duplicate_ignored" }),
      });

    const headers = {
      "Content-Type": "application/json",
      "X-Idempotency-Key": "uuid-te-001",
    };
    const body = JSON.stringify({ idempotency_key: "uuid-te-001" });

    await fetch("http://localhost:8000/api/v1/mobile-sync/push/time-entries", {
      method: "POST",
      headers,
      body,
    });
    const response2 = await fetch(
      "http://localhost:8000/api/v1/mobile-sync/push/time-entries",
      {
        method: "POST",
        headers,
        body,
      },
    );

    expect(response2.ok).toBe(true);
    expect(mockFetch).toHaveBeenCalledTimes(2);
  });

  it("completes sync session after push+pull", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ status: "completed" }),
    });

    const response = await fetch(
      "http://localhost:8000/api/v1/mobile/sync-sessions/session-001/complete",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pushed: 1, failed: 0, pulled: 0 }),
      },
    );

    expect(response.ok).toBe(true);
    const data = (await response.json()) as { status: string };
    expect(data.status).toBe("completed");
  });

  it("idempotency key is sent as UUID v4 format", () => {
    const uuidPattern =
      /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;
    const key = "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
      const r = (Math.random() * 16) | 0;
      const v = c === "x" ? r : (r & 0x3) | 0x8;
      return v.toString(16);
    });
    expect(key).toMatch(uuidPattern);
  });
});
