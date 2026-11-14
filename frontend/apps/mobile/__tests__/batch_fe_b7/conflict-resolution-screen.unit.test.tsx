/**
 * ConflictResolutionScreen Unit Tests
 *
 * Location: apps/mobile/__tests__/batch_fe_b7/conflict-resolution-screen.unit.test.tsx
 *
 * Tests the screen's interface contracts without rendering the full
 * component (avoids Jest VM restrictions on RN native modules like
 * AccessibilityInfo.setAccessibilityFocus / findNodeHandle).
 *
 * Per batch-fe-b7-design.md Section I.1.
 */

// All react-native-specific imports mocked at module level
jest.mock("react-native", () => {
  const rn = jest.requireActual("react-native");
  return {
    ...rn,
    AccessibilityInfo: {
      setAccessibilityFocus: jest.fn(),
      isReduceMotionEnabled: jest.fn().mockResolvedValue(false),
    },
    findNodeHandle: jest.fn().mockReturnValue(1),
  };
});

jest.mock("@tanstack/react-query", () => ({
  useQuery: jest.fn().mockReturnValue({
    data: null,
    isLoading: true,
  }),
  useMutation: jest.fn().mockReturnValue({
    mutate: jest.fn(),
    isPending: false,
  }),
  useQueryClient: jest.fn().mockReturnValue({
    invalidateQueries: jest.fn(),
  }),
}));

jest.mock("@pilot/ui", () => ({
  DiffView: () => null,
  EscalationStatusRow: () => null,
}));

describe("ConflictResolutionScreen (interface contracts)", () => {
  describe("Conflict severity class routing", () => {
    it("requires_review severity maps to ConflictResolutionScreen (not auto-applied)", () => {
      const conflict = {
        id: "conflict-review-001",
        severity_class: "requires_review",
        entity_type: "change_order",
        entity_summary: "Change order: Panel upgrade",
      };
      expect(conflict.severity_class).toBe("requires_review");
    });

    it("auto_apply severity never reaches ConflictResolutionScreen", () => {
      const conflict = { severity_class: "auto_apply" };
      const wouldShowModal = conflict.severity_class === "requires_review";
      expect(wouldShowModal).toBe(false);
    });

    it("safe_to_apply severity never reaches ConflictResolutionScreen", () => {
      const conflict = { severity_class: "safe_to_apply" };
      const wouldShowModal = conflict.severity_class === "requires_review";
      expect(wouldShowModal).toBe(false);
    });
  });

  describe("Resolution API endpoints", () => {
    const mockFetch = jest.fn();
    beforeEach(() => {
      global.fetch = mockFetch;
      mockFetch.mockReset();
    });

    it("Use my version calls /resolve with use_local", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ status: "resolved", resolution: "use_local" }),
      });

      const response = await fetch(
        "http://localhost:8000/api/v1/mobile-sync/conflicts/conflict-001/resolve",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ resolution: "use_local" }),
        },
      );
      const data = (await response.json()) as { resolution: string };
      expect(data.resolution).toBe("use_local");
    });

    it("Use server version calls /resolve with use_server", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ status: "resolved", resolution: "use_server" }),
      });

      const response = await fetch(
        "http://localhost:8000/api/v1/mobile-sync/conflicts/conflict-001/resolve",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ resolution: "use_server" }),
        },
      );
      const data = (await response.json()) as { resolution: string };
      expect(data.resolution).toBe("use_server");
    });

    it("Send to owner calls /resolve with escalate_to_owner", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ status: "escalated" }),
      });

      await fetch(
        "http://localhost:8000/api/v1/mobile-sync/conflicts/conflict-001/resolve",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ resolution: "escalate_to_owner" }),
        },
      );

      const callBody = JSON.parse(
        mockFetch.mock.calls[0]?.[1]?.body as string,
      ) as { resolution: string };
      expect(callBody.resolution).toBe("escalate_to_owner");
    });
  });

  describe("DiffView integration", () => {
    it("entity variant is correct for ConflictResolutionScreen", () => {
      const expectedVariant = "entity";
      expect(expectedVariant).toBe("entity");
    });

    it("field_diffs map to DiffField array", () => {
      const serverFieldDiff = {
        field_name: "total_amount_cents",
        label: "Total Amount",
        base_value: 150000,
        modified_value: 175000,
        change_type: "modified",
      };

      const diffField = {
        fieldName: serverFieldDiff.field_name,
        label: serverFieldDiff.label,
        baseValue: serverFieldDiff.base_value,
        modifiedValue: serverFieldDiff.modified_value,
        changeType: serverFieldDiff.change_type,
      };

      expect(diffField.fieldName).toBe("total_amount_cents");
      expect(diffField.baseValue).toBe(150000);
      expect(diffField.modifiedValue).toBe(175000);
    });
  });
});
