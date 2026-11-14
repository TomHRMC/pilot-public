/**
 * Voice session offline path integration tests — FE-B3
 *
 * Location: apps/mobile/__tests__/batch_fe_b3/voice-session-offline.integration.test.ts
 * Tests deferred voice upload via WatermelonDB queue.
 */

jest.mock("../../database", () => ({
  database: {
    get: jest.fn().mockReturnValue({
      query: jest.fn().mockReturnValue({
        observe: jest.fn().mockReturnValue({
          subscribe: jest.fn((cb) => {
            // Call immediately with empty array
            cb([]);
            return { unsubscribe: jest.fn() };
          }),
        }),
      }),
    }),
  },
}));

let mockQueue: any[] = [];

jest.mock("../../database/sync/voice-upload", () => ({
  queueVoiceAudio: jest.fn(async (db, item) => {
    mockQueue.push({ id: `id-${Date.now()}`, ...item });
  }),
  uploadPendingVoiceAudio: jest.fn(async () => {
    mockQueue = [];
    return { completed: 1, failed: 0 };
  }),
  getPendingVoiceCount: jest.fn(async () => mockQueue.length),
  clearVoiceQueue: jest.fn(async () => {
    mockQueue = [];
  }),
}));

// Mock fetch before static imports to ensure it's available
const mockFetch = jest.fn();
global.fetch = mockFetch;

// Static imports (must be after jest.mock calls)
import { renderHook, act } from "@testing-library/react-native";
import { useDeferredVoiceUpload } from "../../features/voice-quote-creation/hooks/useDeferredVoiceUpload";
import { database } from "../../database";

describe("offline voice deferred upload", () => {
  beforeEach(() => {
    mockQueue = [];
    mockFetch.mockReset();
    mockFetch.mockResolvedValue({
      ok: true,
      status: 202,
      json: async () => ({
        voice_command_log_id: 42,
        idempotency_uuid: "a1b2c3d4-0000-0000-0000-000000000001",
        processing_status: "transcribing",
      }),
    });
  });

  it("enqueue adds item to the queue", async () => {
    const { result } = renderHook(() => useDeferredVoiceUpload());

    await act(async () => {
      await result.current.enqueue({
        sessionId: "s-001",
        audioPath: "file://mock-audio.m4a",
        idempotencyKey: "idem-001",
      });
    });

    expect(mockQueue).toHaveLength(1);
    expect(mockQueue[0].sessionId).toBe("s-001");
  });

  it("upload status transitions after uploadWhenOnline", async () => {
    const { result } = renderHook(() => useDeferredVoiceUpload());

    await act(async () => {
      await result.current.enqueue({
        sessionId: "s-001",
        audioPath: "file://mock-audio.m4a",
        idempotencyKey: "idem-002",
      });
    });

    expect(result.current.uploadStatus).toBe("idle");

    await act(async () => {
      await result.current.uploadWhenOnline();
    });

    // After uploadWhenOnline, status should be completed or failed
    expect(["completed", "failed"]).toContain(result.current.uploadStatus);
  });
});
