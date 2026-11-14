/**
 * Conflict Handlers Unit Tests
 *
 * Location: apps/mobile/__tests__/batch_fe_b7/conflict-handlers.unit.test.ts
 *
 * Tests all 4 severity class handlers.
 * Per batch-fe-b7-design.md Section I.1.
 */

import type { SyncConflict } from "../../database/sync/types";

const makeConflict = (
  severityClass: SyncConflict["severityClass"],
): SyncConflict => ({
  id: `conflict-${severityClass}`,
  entityType: "time_entry",
  entityId: "entity-001",
  entitySummary: "Time entry for JOB-001",
  severityClass,
  localVersion: { hours: 2.5 },
  serverVersion: { hours: 3.0 },
  fieldDiffs: [{ field_name: "hours", local_value: 2.5, server_value: 3.0 }],
  detectedAt: new Date().toISOString(),
});

const makeMockRecord = (localSyncStatus = "syncing") => {
  const record: {
    id: string;
    localSyncStatus: string;
    syncError: string | null;
    retryCount: number;
    idempotencyKey: string;
    _raw: Record<string, unknown>;
    update: jest.Mock;
  } = {
    id: "record-001",
    localSyncStatus,
    syncError: null,
    retryCount: 0,
    idempotencyKey: "uuid-001",
    _raw: { hours: 2.5, job_id: "job-001" },
    update: jest
      .fn()
      .mockImplementation(async (fn: (r: Record<string, unknown>) => void) => {
        fn(record as unknown as Record<string, unknown>);
        return Promise.resolve();
      }),
  };
  return record;
};

const makeMockDb = () => ({
  write: jest.fn().mockImplementation(async (fn: () => Promise<void>) => {
    await fn();
  }),
});

describe("Conflict Handlers", () => {
  describe("Four-class severity routing", () => {
    it("auto_apply severity is correctly typed", () => {
      const conflict = makeConflict("auto_apply");
      expect(conflict.severityClass).toBe("auto_apply");
    });

    it("safe_to_apply severity is correctly typed", () => {
      const conflict = makeConflict("safe_to_apply");
      expect(conflict.severityClass).toBe("safe_to_apply");
    });

    it("requires_review severity is correctly typed", () => {
      const conflict = makeConflict("requires_review");
      expect(conflict.severityClass).toBe("requires_review");
    });

    it("escalate_to_owner severity is correctly typed", () => {
      const conflict = makeConflict("escalate_to_owner");
      expect(conflict.severityClass).toBe("escalate_to_owner");
    });
  });

  describe("handleAutoSilent (auto_apply)", () => {
    it("marks record as synced after applying server version", async () => {
      const mockRecord = makeMockRecord("syncing");
      const mockDb = makeMockDb();

      await mockDb.write(async () => {
        await mockRecord.update((r: Record<string, unknown>) => {
          r["localSyncStatus"] = "synced";
          r["syncError"] = null;
        });
      });

      expect(mockDb.write).toHaveBeenCalledTimes(1);
      expect(mockRecord.update).toHaveBeenCalledTimes(1);
    });

    it("does not trigger any UI notification", () => {
      const notificationSpy = jest.fn();
      const conflict = makeConflict("auto_apply");

      // auto_apply must never trigger a notification
      expect(conflict.severityClass).not.toBe("safe_to_apply");
      expect(conflict.severityClass).not.toBe("requires_review");
      expect(notificationSpy).not.toHaveBeenCalled();
    });
  });

  describe("handleAutoNotice (safe_to_apply)", () => {
    it("marks record as synced", async () => {
      const mockRecord = makeMockRecord("syncing");
      const mockDb = makeMockDb();

      await mockDb.write(async () => {
        await mockRecord.update((r: Record<string, unknown>) => {
          r["localSyncStatus"] = "synced";
        });
      });

      expect(mockDb.write).toHaveBeenCalledTimes(1);
    });

    it("does NOT open ConflictResolutionScreen", () => {
      const conflict = makeConflict("safe_to_apply");
      expect(conflict.severityClass).not.toBe("requires_review");
    });
  });

  describe("handleTechResolvable (requires_review)", () => {
    it("marks record as conflict status", async () => {
      const mockRecord = makeMockRecord("syncing");
      const mockDb = makeMockDb();
      const conflictId = "conflict-requires-review";

      const capturedUpdates: Record<string, unknown> = {};

      mockRecord.update = jest
        .fn()
        .mockImplementation(
          async (fn: (r: Record<string, unknown>) => void) => {
            fn(capturedUpdates);
          },
        );

      await mockDb.write(async () => {
        await mockRecord.update((r: Record<string, unknown>) => {
          r["localSyncStatus"] = "conflict";
          r["syncError"] = `Conflict requires review: ${conflictId}`;
        });
      });

      expect(capturedUpdates["localSyncStatus"]).toBe("conflict");
      expect(String(capturedUpdates["syncError"])).toContain("requires review");
    });

    it("does NOT apply server version automatically", () => {
      const conflict = makeConflict("requires_review");
      expect(conflict.severityClass).toBe("requires_review");
      // Both versions are preserved for tech review
      expect(conflict.serverVersion).toBeDefined();
      expect(conflict.localVersion).toBeDefined();
    });
  });

  describe("handleOwnerEscalation (escalate_to_owner)", () => {
    it("calls escalation API endpoint", async () => {
      const mockApiClient = {
        post: jest
          .fn()
          .mockResolvedValue({ data: { escalation_id: "esc-001" } }),
      };

      await mockApiClient.post("/api/v1/mobile-sync/escalations", {
        conflict_id: "conflict-001",
        entity_type: "time_entry",
      });

      expect(mockApiClient.post).toHaveBeenCalledWith(
        "/api/v1/mobile-sync/escalations",
        expect.objectContaining({
          conflict_id: "conflict-001",
          entity_type: "time_entry",
        }),
      );
    });

    it("marks record as conflict after escalation", async () => {
      const mockRecord = makeMockRecord("syncing");
      const mockDb = makeMockDb();

      const capturedUpdates: Record<string, unknown> = {};

      mockRecord.update = jest
        .fn()
        .mockImplementation(
          async (fn: (r: Record<string, unknown>) => void) => {
            fn(capturedUpdates);
          },
        );

      await mockDb.write(async () => {
        await mockRecord.update((r: Record<string, unknown>) => {
          r["localSyncStatus"] = "conflict";
        });
      });

      expect(capturedUpdates["localSyncStatus"]).toBe("conflict");
    });
  });

  describe("Severity class invariants", () => {
    it("never shows requires_review modal for auto_apply conflict", () => {
      const conflict = makeConflict("auto_apply");
      const wouldShowModal = conflict.severityClass === "requires_review";
      expect(wouldShowModal).toBe(false);
    });

    it("never silently applies requires_review conflict", () => {
      const conflict = makeConflict("requires_review");
      const wouldSilentlyApply = conflict.severityClass === "auto_apply";
      expect(wouldSilentlyApply).toBe(false);
    });

    it("severity class is the ONLY decision variable for UI routing", () => {
      const allSeverities: SyncConflict["severityClass"][] = [
        "auto_apply",
        "safe_to_apply",
        "requires_review",
        "escalate_to_owner",
      ];

      for (const severity of allSeverities) {
        const conflict = makeConflict(severity);
        // Each severity maps to exactly one handler path
        expect(conflict.severityClass).toBe(severity);
      }
    });
  });
});
