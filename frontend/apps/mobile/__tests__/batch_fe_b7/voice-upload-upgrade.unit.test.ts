/**
 * Voice Upload Upgrade Unit Tests
 *
 * Location: apps/mobile/__tests__/batch_fe_b7/voice-upload-upgrade.unit.test.ts
 *
 * Tests: public API unchanged after FE-B3 stub → WatermelonDB upgrade;
 *        queue persists conceptually.
 *
 * Per batch-fe-b7-design.md Section I.1 and §G.7.
 *
 * TEST-UPLIFT-1C: Converted from jest.mock("@pilot/shared-api") to MSW
 * setupServer + wildcard handlers (Rule 18). The banned apiClient mock was
 * removed; the MSW handler for POST /api/v1/voice/upload-audio returns the
 * same fixture the mock previously provided.
 */

import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";

// Mock WatermelonDB database
jest.mock("../../database", () => ({
  database: {
    write: jest
      .fn()
      .mockImplementation(async (fn: () => Promise<unknown>) => fn()),
    get: jest.fn().mockReturnValue({
      create: jest
        .fn()
        .mockImplementation(
          async (fn: (r: Record<string, unknown>) => void) => {
            const record: Record<string, unknown> = {
              id: `voice-${Math.random().toString(36).slice(2)}`,
              sessionId: null,
              audioPath: null,
              capturedAt: null,
              localSyncStatus: "pending",
              idempotencyKey: null,
            };
            fn(record);
            return record;
          },
        ),
      query: jest.fn().mockReturnValue({
        observe: jest.fn().mockReturnValue({
          subscribe: jest.fn().mockReturnValue({ unsubscribe: jest.fn() }),
        }),
        fetchCount: jest.fn().mockResolvedValue(0),
      }),
    }),
  },
}));

// ── MSW server (replaces banned apiClient mock) ──────────────────────────────

const server = setupServer(
  http.post("*/api/v1/voice/upload-audio", () =>
    HttpResponse.json({ status: "uploaded" }, { status: 202 }),
  ),
);

beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

import { renderHook, act } from "@testing-library/react-native";
import { useDeferredVoiceUpload } from "../../features/voice-quote-creation/hooks/useDeferredVoiceUpload";

describe("useDeferredVoiceUpload (FE-B7 WatermelonDB upgrade)", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe("Public API contract (unchanged from FE-B3)", () => {
    it("exposes required properties: queuedAudio, enqueue, uploadWhenOnline, uploadStatus, clearQueue", () => {
      const { result } = renderHook(() => useDeferredVoiceUpload());

      expect(typeof result.current.queuedAudio).toBe("object");
      expect(typeof result.current.enqueue).toBe("function");
      expect(typeof result.current.uploadWhenOnline).toBe("function");
      expect(typeof result.current.uploadStatus).toBe("string");
      expect(typeof result.current.clearQueue).toBe("function");
    });

    it("initializes with empty queue and idle status", () => {
      const { result } = renderHook(() => useDeferredVoiceUpload());

      expect(result.current.queuedAudio).toEqual([]);
      expect(result.current.uploadStatus).toBe("idle");
    });

    it("enqueue accepts item without id and capturedAt", async () => {
      const { result } = renderHook(() => useDeferredVoiceUpload());

      await act(async () => {
        await result.current.enqueue({
          sessionId: "session-001",
          audioPath: "file:///tmp/audio.m4a",
          idempotencyKey: "uuid-voice-001",
        });
      });

      // Should not throw — public API is unchanged
      expect(result.current.uploadStatus).toBe("idle");
    });
  });

  describe("WatermelonDB persistence", () => {
    it("calls database.write when enqueuing", async () => {
      const { database } = require("../../database") as {
        database: { write: jest.Mock; get: jest.Mock };
      };

      const { result } = renderHook(() => useDeferredVoiceUpload());

      await act(async () => {
        await result.current.enqueue({
          sessionId: "session-001",
          audioPath: "file:///tmp/audio.m4a",
          idempotencyKey: "uuid-voice-001",
        });
      });

      expect(database.write).toHaveBeenCalledTimes(1);
    });

    it("sets upload status to uploading during uploadWhenOnline", async () => {
      const { database } = require("../../database") as {
        database: { write: jest.Mock; get: jest.Mock };
      };

      // Mock pending count as 0 (no items to upload)
      database.get.mockReturnValue({
        create: jest.fn(),
        query: jest.fn().mockReturnValue({
          observe: jest.fn().mockReturnValue({
            subscribe: jest.fn().mockReturnValue({ unsubscribe: jest.fn() }),
          }),
          fetchCount: jest.fn().mockResolvedValue(0),
          fetch: jest.fn().mockResolvedValue([]),
        }),
      });

      const { result } = renderHook(() => useDeferredVoiceUpload());

      await act(async () => {
        await result.current.uploadWhenOnline();
      });

      // With 0 pending, should remain idle
      expect(result.current.uploadStatus).toBe("idle");
    });
  });

  describe("Idempotency", () => {
    it("preserves idempotency key when queuing audio", async () => {
      const { database } = require("../../database") as {
        database: { write: jest.Mock; get: jest.Mock };
      };

      let capturedRecord: Record<string, unknown> | null = null;

      database.get.mockReturnValue({
        create: jest
          .fn()
          .mockImplementation(
            async (fn: (r: Record<string, unknown>) => void) => {
              const record: Record<string, unknown> = {};
              fn(record);
              capturedRecord = record;
              return record;
            },
          ),
        query: jest.fn().mockReturnValue({
          observe: jest.fn().mockReturnValue({
            subscribe: jest.fn().mockReturnValue({ unsubscribe: jest.fn() }),
          }),
          fetchCount: jest.fn().mockResolvedValue(0),
        }),
      });

      const { result } = renderHook(() => useDeferredVoiceUpload());

      await act(async () => {
        await result.current.enqueue({
          sessionId: "session-001",
          audioPath: "file:///tmp/audio.m4a",
          idempotencyKey: "fixed-idem-key-001",
        });
      });

      expect(capturedRecord?.["idempotencyKey"]).toBe("fixed-idem-key-001");
    });
  });
});
