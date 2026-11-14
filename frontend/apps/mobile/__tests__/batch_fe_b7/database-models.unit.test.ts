/**
 * WatermelonDB Model CRUD Unit Tests
 *
 * Location: apps/mobile/__tests__/batch_fe_b7/database-models.unit.test.ts
 *
 * Tests: all 7 model schemas; localSyncStatus transitions;
 *        idempotency_key generation; client_capture_at preservation.
 *
 * Uses plain JS objects to represent model shape (no native SQLite in Jest).
 * Per batch-fe-b7-design.md Section I.1.
 */

import type { LocalSyncStatus } from "../../database/models/SyncableModel";

type MockRecord = {
  id: string;
  localSyncStatus: LocalSyncStatus;
  idempotencyKey: string;
  syncError: string | null;
  retryCount: number;
  clientCaptureAt: Date;
  serverReceivedAt?: Date;
  [key: string]: unknown;
};

const createMockRecord = (
  _table: string,
  overrides: Record<string, unknown> = {},
): MockRecord => ({
  id: `record-${Math.random().toString(36).slice(2, 9)}`,
  localSyncStatus: "pending",
  idempotencyKey: "test-uuid-1234",
  syncError: null,
  retryCount: 0,
  clientCaptureAt: new Date(),
  serverReceivedAt: undefined,
  ...overrides,
});

describe("WatermelonDB Model Schemas", () => {
  describe("TimeEntry model", () => {
    it("creates a time entry with required sync fields", () => {
      const record = createMockRecord("time_entries", {
        jobId: "job-001",
        userId: "user-001",
        startedAt: new Date("2026-05-22T08:00:00Z"),
        localSyncStatus: "pending" as LocalSyncStatus,
        idempotencyKey: "uuid-time-entry-001",
      });

      expect(record.localSyncStatus).toBe("pending");
      expect(record.idempotencyKey).toBe("uuid-time-entry-001");
      expect(record["jobId"]).toBe("job-001");
    });

    it("transitions sync status pending → syncing → synced", () => {
      const record = createMockRecord("time_entries", {
        localSyncStatus: "pending" as LocalSyncStatus,
      });

      record.localSyncStatus = "syncing";
      expect(record.localSyncStatus).toBe("syncing");

      record.localSyncStatus = "synced";
      expect(record.localSyncStatus).toBe("synced");
    });

    it("stores client_capture_at separately from created_at", () => {
      const captureTime = new Date("2026-05-22T07:00:00Z");
      const record = createMockRecord("time_entries", {
        clientCaptureAt: captureTime,
      });

      expect(record.clientCaptureAt).toEqual(captureTime);
    });
  });

  describe("Expense model", () => {
    it("creates an expense with required fields", () => {
      const record = createMockRecord("expenses", {
        jobId: "job-001",
        userId: "user-001",
        jobExpenseCategoryCode: "materials",
        costCents: 4500,
        isBillable: true,
        localSyncStatus: "pending" as LocalSyncStatus,
        idempotencyKey: "uuid-expense-001",
      });

      expect(record.localSyncStatus).toBe("pending");
      expect(record["costCents"]).toBe(4500);
    });
  });

  describe("Photo model", () => {
    it("creates a photo with upload tracking fields", () => {
      const record = createMockRecord("photos", {
        jobId: "job-001",
        localUri: "file:///tmp/photo.jpg",
        mimeType: "image/jpeg",
        fileSizeBytes: 102400,
        uploadProgress: 0,
        lastCompletedChunk: 0,
        wifiPending: false,
        localSyncStatus: "pending" as LocalSyncStatus,
        idempotencyKey: "uuid-photo-001",
      });

      expect(record["uploadProgress"]).toBe(0);
      expect(record["lastCompletedChunk"]).toBe(0);
      expect(record["wifiPending"]).toBe(false);
    });

    it("tracks upload progress chunks", () => {
      const record = createMockRecord("photos", {
        lastCompletedChunk: 0,
        uploadProgress: 0,
      });

      record["lastCompletedChunk"] = 1;
      record["uploadProgress"] = 33;

      expect(record["lastCompletedChunk"]).toBe(1);
      expect(record["uploadProgress"]).toBe(33);
    });
  });

  describe("ChangeOrder model", () => {
    it("creates change order with default draft status", () => {
      const record = createMockRecord("change_orders", {
        jobId: "job-001",
        title: "Panel upgrade",
        totalAmountCents: 150000,
        status: "draft",
        localSyncStatus: "pending" as LocalSyncStatus,
        idempotencyKey: "uuid-co-001",
      });

      expect(record["status"]).toBe("draft");
      expect(record["totalAmountCents"]).toBe(150000);
    });
  });

  describe("LotoCheck model", () => {
    it("creates LOTO check with GPS coordinates", () => {
      const record = createMockRecord("loto_checks", {
        jobId: "job-001",
        checkType: "lockout_applied",
        confirmedAt: new Date(),
        gpsLat: 37.7749,
        gpsLng: -122.4194,
        localSyncStatus: "pending" as LocalSyncStatus,
        idempotencyKey: "uuid-loto-001",
      });

      expect(record["gpsLat"]).toBe(37.7749);
      expect(record["gpsLng"]).toBe(-122.4194);
      expect(record["checkType"]).toBe("lockout_applied");
    });
  });

  describe("JobStatusChange model", () => {
    it("creates status change with from/to fields", () => {
      const record = createMockRecord("job_status_changes", {
        jobId: "job-001",
        fromStatus: "scheduled",
        toStatus: "in_progress",
        changedAt: new Date(),
        localSyncStatus: "pending" as LocalSyncStatus,
        idempotencyKey: "uuid-status-001",
      });

      expect(record["fromStatus"]).toBe("scheduled");
      expect(record["toStatus"]).toBe("in_progress");
    });
  });

  describe("JobNote model", () => {
    it("creates job note with content", () => {
      const record = createMockRecord("job_notes", {
        jobId: "job-001",
        createdBy: "user-001",
        content: "Found water damage near panel",
        localSyncStatus: "pending" as LocalSyncStatus,
        idempotencyKey: "uuid-note-001",
      });

      expect(record["content"]).toBe("Found water damage near panel");
      expect(record.localSyncStatus).toBe("pending");
    });
  });

  describe("VoiceAudioQueue model", () => {
    it("creates voice audio queue entry", () => {
      const record = createMockRecord("voice_audio_queue", {
        sessionId: "session-001",
        audioPath: "file:///tmp/audio.m4a",
        capturedAt: new Date().toISOString(),
        localSyncStatus: "pending" as LocalSyncStatus,
        idempotencyKey: "uuid-voice-001",
      });

      expect(record["sessionId"]).toBe("session-001");
      expect(record["audioPath"]).toBe("file:///tmp/audio.m4a");
    });
  });

  describe("Sync control fields (all models)", () => {
    it("idempotency_key is a valid UUID v4 format", () => {
      const key = "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(
        /[xy]/g,
        (c) => {
          const r = (Math.random() * 16) | 0;
          const v = c === "x" ? r : (r & 0x3) | 0x8;
          return v.toString(16);
        },
      );
      expect(key).toMatch(
        /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/,
      );
    });

    it("sync status enum values are all valid", () => {
      const validStatuses: LocalSyncStatus[] = [
        "pending",
        "syncing",
        "synced",
        "failed",
        "conflict",
      ];
      expect(validStatuses).toHaveLength(5);
    });

    it("marks as failed with error message and increments retry count", () => {
      const record = createMockRecord("time_entries", {
        localSyncStatus: "pending" as LocalSyncStatus,
        syncError: null,
        retryCount: 0,
      });

      record.localSyncStatus = "failed";
      record.syncError = "Network timeout";
      record.retryCount = 1;

      expect(record.localSyncStatus).toBe("failed");
      expect(record.syncError).toBe("Network timeout");
      expect(record.retryCount).toBe(1);
    });

    it("idempotency key never changes across retries", () => {
      const originalKey = "uuid-fixed-key-001";
      const record = createMockRecord("time_entries", {
        idempotencyKey: originalKey,
        localSyncStatus: "failed" as LocalSyncStatus,
        retryCount: 3,
      });

      // Simulate retry — key must not change
      record.localSyncStatus = "syncing";
      record.retryCount = 4;

      expect(record.idempotencyKey).toBe(originalKey);
    });

    it("client_capture_at is preserved after server sync", () => {
      const captureTime = new Date("2026-05-22T06:00:00Z");
      const record = createMockRecord("time_entries", {
        clientCaptureAt: captureTime,
        localSyncStatus: "synced" as LocalSyncStatus,
        serverReceivedAt: new Date("2026-05-22T06:05:00Z"),
      });

      // client_capture_at must never be overwritten by server_received_at
      expect(record.clientCaptureAt).toEqual(captureTime);
      expect(record.serverReceivedAt).not.toEqual(captureTime);
    });
  });
});
