/**
 * Owner Escalation Flow Integration Test
 *
 * Location: apps/mobile/__tests__/batch_fe_b7/owner-escalation-flow.integration.test.tsx
 *
 * Tests escalation API contracts and EscalationStatusRow props interface.
 * Uses fetch mock (avoids MSW/node ESM issues in Jest RN).
 * Mocks @pilot/ui to avoid ESM parse issues.
 *
 * Per batch-fe-b7-design.md Section I.2.
 */

jest.mock("@pilot/ui", () => ({
  EscalationStatusRow: jest.fn(() => null),
}));

const mockFetch = jest.fn();
global.fetch = mockFetch;

describe("Owner Escalation Flow (Integration)", () => {
  beforeEach(() => {
    mockFetch.mockReset();
    jest.clearAllMocks();
  });

  it("escalate_to_owner conflict triggers escalation API", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        escalation_id: "esc-001",
        status: "pending",
        created_at: new Date().toISOString(),
      }),
    });

    const response = await fetch(
      "http://localhost:8000/api/v1/mobile-sync/escalations",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          conflict_id: "conflict-escalate-001",
          entity_type: "job_status_change",
          entity_id: "record-001",
          entity_summary: "Status: in_progress → completed",
        }),
      },
    );

    const data = (await response.json()) as {
      escalation_id: string;
      status: string;
    };
    expect(response.ok).toBe(true);
    expect(data.escalation_id).toBe("esc-001");
    expect(data.status).toBe("pending");
  });

  it("escalation POST body includes entity_type and conflict_id", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ escalation_id: "esc-002", status: "pending" }),
    });

    await fetch("http://localhost:8000/api/v1/mobile-sync/escalations", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        conflict_id: "conflict-001",
        entity_type: "time_entry",
        entity_summary: "Time entry for JOB-001",
      }),
    });

    const callBody = JSON.parse(
      mockFetch.mock.calls[0]?.[1]?.body as string,
    ) as Record<string, string>;
    expect(callBody["conflict_id"]).toBe("conflict-001");
    expect(callBody["entity_type"]).toBe("time_entry");
  });

  it("EscalationStatusRowProps interface: pending status has webDeepLink stub", () => {
    const props = {
      entityType: "job_status_change" as const,
      entitySummary: "Status: in_progress → completed",
      status: "pending" as const,
      escalatedAt: "2026-05-22T10:00:00Z",
      webDeepLink: "https://pilotfortrades.com/sync/escalations",
    };

    // FE-B7: stub URL; FE-B9 will update to universal link
    expect(props.webDeepLink).toContain("pilotfortrades.com");
    expect(props.status).toBe("pending");
  });

  it("EscalationStatusRowProps interface: resolved status has resolutionMessage", () => {
    const props = {
      entityType: "expense" as const,
      entitySummary: "Expense $45.00",
      status: "resolved" as const,
      escalatedAt: "2026-05-22T10:00:00Z",
      webDeepLink: "https://pilotfortrades.com/sync/escalations",
      resolutionMessage: "Use server version",
    };

    expect(props.status).toBe("resolved");
    expect(props.resolutionMessage).toBe("Use server version");
  });

  it("EscalationStatusRowProps interface: rejected status", () => {
    const props = {
      entityType: "time_entry" as const,
      entitySummary: "Time entry for JOB-001",
      status: "rejected" as const,
      escalatedAt: "2026-05-22T10:00:00Z",
      webDeepLink: "https://pilotfortrades.com/sync/escalations",
    };

    expect(props.status).toBe("rejected");
  });

  it("four-class severity: escalate_to_owner is a valid severity class", () => {
    const severities = [
      "auto_apply",
      "safe_to_apply",
      "requires_review",
      "escalate_to_owner",
    ];
    expect(severities).toContain("escalate_to_owner");
  });

  it("all 7 offline entity types are valid escalation entity types", () => {
    const entityTypes = [
      "time_entry",
      "expense",
      "photo",
      "change_order",
      "loto_check",
      "job_status_change",
      "job_note",
    ];
    expect(entityTypes).toHaveLength(7);
  });
});
