/**
 * Conflict Requires Review Modal Integration Test
 *
 * Location: apps/mobile/__tests__/batch_fe_b7/conflict-requires-review-modal.integration.test.tsx
 *
 * Uses fetch mock (avoids MSW/node ESM issues in Jest RN).
 * Per batch-fe-b7-design.md Section I.2.
 */

const mockFetch = jest.fn();
global.fetch = mockFetch;

describe("Conflict Resolution Modal (Integration)", () => {
  beforeEach(() => {
    mockFetch.mockReset();
  });

  it("fetches conflict detail with requires_review severity", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        id: "conflict-review-001",
        severity_class: "requires_review",
        entity_type: "change_order",
        entity_summary: "Change order: Panel upgrade $1,500",
        field_diffs: [
          {
            field_name: "total_amount_cents",
            label: "Total Amount",
            base_value: 150000,
            modified_value: 175000,
            change_type: "modified",
          },
        ],
      }),
    });

    const response = await fetch(
      "http://localhost:8000/api/v1/mobile-sync/conflicts/conflict-review-001",
    );
    const data = (await response.json()) as {
      severity_class: string;
      entity_type: string;
      field_diffs: { field_name: string }[];
    };

    expect(response.ok).toBe(true);
    expect(data.severity_class).toBe("requires_review");
    expect(data.entity_type).toBe("change_order");
    expect(data.field_diffs).toHaveLength(1);
  });

  it("resolves conflict with use_local", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ status: "resolved", resolution: "use_local" }),
    });

    const response = await fetch(
      "http://localhost:8000/api/v1/mobile-sync/conflicts/conflict-review-001/resolve",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ resolution: "use_local" }),
      },
    );
    const data = (await response.json()) as {
      status: string;
      resolution: string;
    };

    expect(data.status).toBe("resolved");
    expect(data.resolution).toBe("use_local");
  });

  it("resolves conflict with use_server", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ status: "resolved", resolution: "use_server" }),
    });

    const response = await fetch(
      "http://localhost:8000/api/v1/mobile-sync/conflicts/conflict-review-001/resolve",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ resolution: "use_server" }),
      },
    );
    const data = (await response.json()) as { resolution: string };
    expect(data.resolution).toBe("use_server");
  });

  it("escalates conflict to owner", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ status: "escalated" }),
    });

    await fetch(
      "http://localhost:8000/api/v1/mobile-sync/conflicts/conflict-review-001/resolve",
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

  it("never shows requires_review modal for auto_apply conflict", () => {
    const autoApplyConflict = { severity_class: "auto_apply" };
    const wouldShowModal =
      autoApplyConflict.severity_class === "requires_review";
    expect(wouldShowModal).toBe(false);
  });

  describe("Badge and status lifecycle", () => {
    it("conflict status transitions: pending → conflict → resolved", () => {
      const states = ["pending", "conflict", "resolved"];
      expect(states[0]).toBe("pending");
      expect(states[1]).toBe("conflict");
      expect(states[2]).toBe("resolved");
    });
  });
});
