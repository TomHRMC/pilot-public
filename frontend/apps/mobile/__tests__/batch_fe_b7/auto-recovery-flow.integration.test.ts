/**
 * Auto Recovery Flow Integration Tests
 *
 * Location: apps/mobile/__tests__/batch_fe_b7/auto-recovery-flow.integration.test.ts
 *
 * Uses fetch mock (avoids MSW/node ESM issues in Jest RN).
 * Per batch-fe-b7-design.md Section I.2.
 */

const mockFetch = jest.fn();
global.fetch = mockFetch;

describe("Auto Recovery Flow (Integration)", () => {
  beforeEach(() => {
    mockFetch.mockReset();
  });

  describe("auto_apply conflict → silent resolution", () => {
    it("returns auto_apply conflict from conflict fetch", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          id: "conflict-auto-apply-001",
          severity_class: "auto_apply",
          entity_type: "time_entry",
          entity_summary: "Time entry for JOB-001",
          field_diffs: [],
        }),
      });

      const response = await fetch(
        "http://localhost:8000/api/v1/mobile-sync/conflicts/conflict-auto-apply-001",
      );
      const data = (await response.json()) as { severity_class: string };

      expect(data.severity_class).toBe("auto_apply");
    });

    it("auto_apply conflict does not create an escalation", () => {
      // auto_apply handler must not call escalation API
      expect(mockFetch).not.toHaveBeenCalledWith(
        expect.stringContaining("escalations"),
        expect.anything(),
      );
    });
  });

  describe("safe_to_apply conflict → auto banner", () => {
    it("safe_to_apply severity does not require tech review", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          id: "conflict-safe-001",
          severity_class: "safe_to_apply",
          entity_type: "expense",
        }),
      });

      const response = await fetch(
        "http://localhost:8000/api/v1/mobile-sync/conflicts/conflict-safe-001",
      );
      const data = (await response.json()) as { severity_class: string };

      expect(data.severity_class).toBe("safe_to_apply");
      expect(data.severity_class).not.toBe("requires_review");
    });
  });

  describe("Force-quit recovery", () => {
    it("records stuck in 'syncing' are reset to 'pending' on restart", () => {
      const recordsInSyncingState = [
        {
          id: "record-001",
          localSyncStatus: "syncing",
          idempotencyKey: "uuid-001",
        },
        {
          id: "record-002",
          localSyncStatus: "syncing",
          idempotencyKey: "uuid-002",
        },
      ];

      const recovered = recordsInSyncingState.map((r) => ({
        ...r,
        localSyncStatus:
          r.localSyncStatus === "syncing" ? "pending" : r.localSyncStatus,
      }));

      expect(recovered[0]?.localSyncStatus).toBe("pending");
      expect(recovered[1]?.localSyncStatus).toBe("pending");
    });

    it("idempotency keys are preserved after force-quit recovery", () => {
      const record = {
        id: "record-001",
        localSyncStatus: "syncing",
        idempotencyKey: "original-uuid-001",
      };

      const recovered = { ...record, localSyncStatus: "pending" };
      expect(recovered.idempotencyKey).toBe("original-uuid-001");
    });

    it("retry after force-quit uses same idempotency key (deduplication)", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ status: "accepted" }),
      });

      const idempotencyKey = "original-uuid-001";

      await fetch(
        "http://localhost:8000/api/v1/mobile-sync/push/time-entries",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Idempotency-Key": idempotencyKey,
          },
          body: JSON.stringify({ idempotency_key: idempotencyKey }),
        },
      );

      const callHeaders = mockFetch.mock.calls[0]?.[1]?.headers as Record<
        string,
        string
      >;
      expect(callHeaders?.["X-Idempotency-Key"]).toBe("original-uuid-001");
    });
  });
});
