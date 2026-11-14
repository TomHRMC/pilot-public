/**
 * StructuredMessage integration tests — MOB-B6
 *
 * Location: apps/mobile/__tests__/batch_mob_b6/structuredMessages.integration.test.tsx
 *
 * Verifies that:
 * 1. job_etc_status messages render JobEtcStatusCard (not raw JSON stub)
 * 2. conflict_summary messages render ConflictSummaryCard (not raw JSON stub)
 * 3. testID="job-etc-stub" is NOT present after MOB-B6
 * 4. testID="conflict-stub" is NOT present after MOB-B6
 */

import React from "react";
import { render, screen, waitFor } from "@testing-library/react-native";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";

import { StructuredMessage } from "../../features/voice-quote-creation/components/StructuredMessage";

// ── MSW Server ────────────────────────────────────────────────────────────────

const server = setupServer(
  http.get("*/api/v1/jobs/:jobId/projected-margin", ({ params }) => {
    return HttpResponse.json({
      job_id: params.jobId,
      projected_margin_pct: 18.5,
      actual_cost_cents: 95000,
      quoted_budget_cents: 120000,
      hours_remaining: 4.0,
      customer_name: "Integration Test Customer",
    });
  }),
);

beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => {
  server.resetHandlers();
  jest.clearAllMocks();
});
afterAll(() => server.close());

// ── Helpers ───────────────────────────────────────────────────────────────────

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return React.createElement(QueryClientProvider, { client: qc }, children);
}

function makeMessage(
  content_type: string,
  render_mode: "live" | "snapshot" = "snapshot",
  entity_id: string | null = null,
  snapshot_payload: Record<string, unknown> | null = null,
) {
  return {
    id: `msg-${content_type}-001`,
    structured_content: {
      render_mode,
      content_type: content_type as
        | "quote_preview"
        | "job_etc_status"
        | "conflict_summary"
        | "text",
      entity_id,
      snapshot_payload,
    },
  };
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("StructuredMessage — MOB-B6 integration", () => {
  it("job_etc_status message renders JobEtcStatusCard (not raw JSON stub)", () => {
    const message = makeMessage("job_etc_status", "snapshot", null, {
      job_id: "job-int-001",
      customer_name: "Test Corp",
      actual_cost_cents: 80000,
      quoted_budget_cents: 110000,
      projected_margin_pct: 20.0,
      hours_remaining: 1.5,
    });

    render(<StructuredMessage message={message} />, { wrapper });

    // Real card renders
    expect(screen.getByTestId("job-etc-status-card")).toBeOnTheScreen();

    // Stub testID NOT present
    expect(screen.queryByTestId("job-etc-stub")).toBeNull();
  });

  it("conflict_summary message renders ConflictSummaryCard (not raw JSON stub)", () => {
    const message = makeMessage("conflict_summary", "snapshot", null, {
      conflict_id: "cid-integration-001",
      entity_type: "invoice",
      conflict_type: "modified_modified",
      summary: "Invoice was modified on both sides.",
    });

    render(<StructuredMessage message={message} />, { wrapper });

    // Real card renders
    expect(screen.getByTestId("conflict-summary-card")).toBeOnTheScreen();

    // Stub testID NOT present
    expect(screen.queryByTestId("conflict-stub")).toBeNull();
  });

  it("testID='job-etc-stub' is NOT present after MOB-B6", () => {
    const message = makeMessage("job_etc_status", "snapshot", null, {
      projected_margin_pct: 15.0,
    });

    render(<StructuredMessage message={message} />, { wrapper });

    expect(screen.queryByTestId("job-etc-stub")).toBeNull();
  });

  it("testID='conflict-stub' is NOT present after MOB-B6", () => {
    const message = makeMessage("conflict_summary", "snapshot", null, {
      entity_type: "quote",
    });

    render(<StructuredMessage message={message} />, { wrapper });

    expect(screen.queryByTestId("conflict-stub")).toBeNull();
  });

  it("job_etc_status live mode renders real data after MSW responds", async () => {
    const message = makeMessage(
      "job_etc_status",
      "live",
      "job-live-int-001",
      null,
    );

    render(<StructuredMessage message={message} />, { wrapper });

    // After MSW responds, real card renders (loading may be very brief in tests)
    await waitFor(() => {
      expect(screen.getByTestId("job-etc-status-card")).toBeOnTheScreen();
    });

    // Stub testID NOT present
    expect(screen.queryByTestId("job-etc-stub")).toBeNull();
  });

  it("text content_type renders null (not a crash)", () => {
    const message = makeMessage("text", "snapshot", null, null);
    const { toJSON } = render(<StructuredMessage message={message} />, {
      wrapper,
    });
    // Should render null — no crash
    expect(toJSON()).toBeNull();
  });
});
