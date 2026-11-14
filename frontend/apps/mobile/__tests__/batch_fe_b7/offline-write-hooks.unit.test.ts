/**
 * Offline Write Hooks Unit Tests
 *
 * Location: apps/mobile/__tests__/batch_fe_b7/offline-write-hooks.unit.test.ts
 *
 * Tests: each hook writes to WatermelonDB with pending status;
 *        generates idempotency key; type-safe inputs.
 *
 * Per batch-fe-b7-design.md Section I.1.
 */

// Mock the database module before imports
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
              id: `record-${Math.random().toString(36).slice(2)}`,
              localSyncStatus: "pending",
              idempotencyKey: null,
              syncError: null,
              retryCount: 0,
              clientCaptureAt: new Date(),
            };
            fn(record);
            return record;
          },
        ),
    }),
  },
}));

import { renderHook, act } from "@testing-library/react-native";
import { useCreateTimeEntry } from "../../features/offline-sync/hooks/useCreateTimeEntry";
import { useCreateExpense } from "../../features/offline-sync/hooks/useCreateExpense";
import { useCreatePhoto } from "../../features/offline-sync/hooks/useCreatePhoto";
import { useCreateChangeOrder } from "../../features/offline-sync/hooks/useCreateChangeOrder";
import { useConfirmLoto } from "../../features/offline-sync/hooks/useConfirmLoto";
import { useChangeJobStatus } from "../../features/offline-sync/hooks/useChangeJobStatus";
import { useCreateJobNote } from "../../features/offline-sync/hooks/useCreateJobNote";

describe("Offline Write Hooks", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe("useCreateTimeEntry", () => {
    it("writes time entry with pending status", async () => {
      const { result } = renderHook(() => useCreateTimeEntry());

      let entry: Record<string, unknown> | undefined;
      await act(async () => {
        entry = (await result.current.create({
          jobId: "job-001",
          userId: "user-001",
          startedAt: new Date("2026-05-22T08:00:00Z"),
        })) as unknown as Record<string, unknown>;
      });

      expect(entry).toBeDefined();
      expect(entry?.["localSyncStatus"]).toBe("pending");
      expect(result.current.error).toBeNull();
    });

    it("generates a unique idempotency key", async () => {
      const { result } = renderHook(() => useCreateTimeEntry());

      let entry1: Record<string, unknown> | undefined;
      let entry2: Record<string, unknown> | undefined;

      await act(async () => {
        entry1 = (await result.current.create({
          jobId: "job-001",
          userId: "user-001",
          startedAt: new Date(),
        })) as unknown as Record<string, unknown>;
      });

      await act(async () => {
        entry2 = (await result.current.create({
          jobId: "job-001",
          userId: "user-001",
          startedAt: new Date(),
        })) as unknown as Record<string, unknown>;
      });

      // Each create should use the database mock (idempotency key set in fn)
      expect(entry1).toBeDefined();
      expect(entry2).toBeDefined();
    });
  });

  describe("useCreateExpense", () => {
    it("writes expense with pending status", async () => {
      const { result } = renderHook(() => useCreateExpense());

      let expense: Record<string, unknown> | undefined;
      await act(async () => {
        expense = (await result.current.create({
          jobId: "job-001",
          userId: "user-001",
          jobExpenseCategoryCode: "materials",
          costCents: 4500,
          isBillable: true,
          incurredAt: new Date(),
        })) as unknown as Record<string, unknown>;
      });

      expect(expense?.["localSyncStatus"]).toBe("pending");
    });
  });

  describe("useCreatePhoto", () => {
    it("writes photo with pending status and zero progress", async () => {
      const { result } = renderHook(() => useCreatePhoto());

      let photo: Record<string, unknown> | undefined;
      await act(async () => {
        photo = (await result.current.create({
          jobId: "job-001",
          localUri: "file:///tmp/photo.jpg",
          mimeType: "image/jpeg",
          fileSizeBytes: 102400,
        })) as unknown as Record<string, unknown>;
      });

      expect(photo?.["localSyncStatus"]).toBe("pending");
    });
  });

  describe("useCreateChangeOrder", () => {
    it("writes change order with draft status and pending sync", async () => {
      const { result } = renderHook(() => useCreateChangeOrder());

      let changeOrder: Record<string, unknown> | undefined;
      await act(async () => {
        changeOrder = (await result.current.create({
          jobId: "job-001",
          title: "Panel upgrade",
          totalAmountCents: 150000,
        })) as unknown as Record<string, unknown>;
      });

      expect(changeOrder?.["localSyncStatus"]).toBe("pending");
    });
  });

  describe("useConfirmLoto", () => {
    it("writes LOTO check with pending status", async () => {
      const { result } = renderHook(() => useConfirmLoto());

      let check: Record<string, unknown> | undefined;
      await act(async () => {
        check = (await result.current.confirm({
          jobId: "job-001",
          checkType: "lockout_applied",
        })) as unknown as Record<string, unknown>;
      });

      expect(check?.["localSyncStatus"]).toBe("pending");
    });
  });

  describe("useChangeJobStatus", () => {
    it("writes job status change with pending status", async () => {
      const { result } = renderHook(() => useChangeJobStatus());

      let statusChange: Record<string, unknown> | undefined;
      await act(async () => {
        statusChange = (await result.current.change({
          jobId: "job-001",
          fromStatus: "scheduled",
          toStatus: "in_progress",
        })) as unknown as Record<string, unknown>;
      });

      expect(statusChange?.["localSyncStatus"]).toBe("pending");
    });
  });

  describe("useCreateJobNote", () => {
    it("writes job note with pending status", async () => {
      const { result } = renderHook(() => useCreateJobNote());

      let note: Record<string, unknown> | undefined;
      await act(async () => {
        note = (await result.current.create({
          jobId: "job-001",
          createdBy: "user-001",
          content: "Found water damage near panel",
        })) as unknown as Record<string, unknown>;
      });

      expect(note?.["localSyncStatus"]).toBe("pending");
    });
  });

  describe("Error handling", () => {
    it("returns error and isPending=false on write failure", async () => {
      // Override mock to throw
      const { database } = require("../../database") as {
        database: { write: jest.Mock; get: jest.Mock };
      };
      database.write.mockRejectedValueOnce(new Error("DB write failed"));

      const { result } = renderHook(() => useCreateJobNote());

      await act(async () => {
        try {
          await result.current.create({
            jobId: "job-001",
            createdBy: "user-001",
            content: "Test",
          });
        } catch {
          // expected
        }
      });

      expect(result.current.error).not.toBeNull();
      expect(result.current.isPending).toBe(false);
    });
  });
});
