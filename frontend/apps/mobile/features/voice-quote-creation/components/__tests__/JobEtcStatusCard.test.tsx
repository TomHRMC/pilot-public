/**
 * JobEtcStatusCard unit tests — MOB-B6
 *
 * Location: apps/mobile/features/voice-quote-creation/components/__tests__/JobEtcStatusCard.test.tsx
 */

import React from "react";
import { render, screen, waitFor } from "@testing-library/react-native";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";

import { JobEtcStatusCard } from "../JobEtcStatusCard";

// ── MSW Server ────────────────────────────────────────────────────────────────

const server = setupServer(
  http.get("*/api/v1/jobs/:jobId/projected-margin", ({ params }) => {
    return HttpResponse.json({
      job_id: params.jobId,
      projected_margin_pct: 22.5,
      actual_cost_cents: 125000,
      quoted_budget_cents: 175000,
      hours_remaining: 3.5,
      customer_name: "Sunrise Electric LLC",
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

const SNAPSHOT_PAYLOAD = {
  job_id: "job-snap-001",
  customer_name: "Test Customer",
  actual_cost_cents: 100000,
  quoted_budget_cents: 150000,
  projected_margin_pct: 25.0,
  hours_remaining: 2.0,
};

const LOW_MARGIN_PAYLOAD = {
  ...SNAPSHOT_PAYLOAD,
  projected_margin_pct: 5.0,
};

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("JobEtcStatusCard", () => {
  describe("snapshot mode", () => {
    it("renders cost and margin from payload without API call", () => {
      render(<JobEtcStatusCard mode="snapshot" payload={SNAPSHOT_PAYLOAD} />, {
        wrapper,
      });

      expect(screen.getByTestId("job-etc-status-card")).toBeOnTheScreen();
      expect(screen.getByTestId("customer-name")).toBeOnTheScreen();
      expect(screen.getByText("Test Customer")).toBeOnTheScreen();
      expect(screen.getByTestId("margin-pct")).toBeOnTheScreen();
      expect(screen.getByText("25.0%")).toBeOnTheScreen();
      expect(screen.getByTestId("actual-cost")).toBeOnTheScreen();
      expect(screen.getByTestId("quoted-budget")).toBeOnTheScreen();
    });

    it("shows hours remaining from payload", () => {
      render(<JobEtcStatusCard mode="snapshot" payload={SNAPSHOT_PAYLOAD} />, {
        wrapper,
      });

      expect(screen.getByTestId("hours-remaining")).toBeOnTheScreen();
      expect(screen.getByText("2h remaining")).toBeOnTheScreen();
    });

    it("does NOT show live indicator in snapshot mode", () => {
      render(<JobEtcStatusCard mode="snapshot" payload={SNAPSHOT_PAYLOAD} />, {
        wrapper,
      });

      expect(screen.queryByTestId("live-indicator")).toBeNull();
    });

    it("low margin (< 10%) renders with red/fault color indicator", () => {
      render(
        <JobEtcStatusCard mode="snapshot" payload={LOW_MARGIN_PAYLOAD} />,
        { wrapper },
      );

      expect(screen.getByTestId("margin-pct")).toBeOnTheScreen();
      expect(screen.getByText("5.0%")).toBeOnTheScreen();
      // margin-indicator dot exists with appropriate test ID
      expect(screen.getByTestId("margin-indicator")).toBeOnTheScreen();
    });
  });

  describe("live mode", () => {
    it("shows loading indicator while fetching", () => {
      render(<JobEtcStatusCard mode="live" entityId="job-live-001" />, {
        wrapper,
      });

      expect(
        screen.getByTestId("job-etc-status-card-loading"),
      ).toBeOnTheScreen();
      expect(screen.getByTestId("job-etc-loading-indicator")).toBeOnTheScreen();
    });

    it("renders margin after MSW responds", async () => {
      render(<JobEtcStatusCard mode="live" entityId="job-live-001" />, {
        wrapper,
      });

      await waitFor(() => {
        expect(screen.getByTestId("job-etc-status-card")).toBeOnTheScreen();
      });

      expect(screen.getByText("22.5%")).toBeOnTheScreen();
      expect(screen.getByText("Sunrise Electric LLC")).toBeOnTheScreen();
    });

    it("shows live indicator in live mode after data loads", async () => {
      render(<JobEtcStatusCard mode="live" entityId="job-live-001" />, {
        wrapper,
      });

      await waitFor(() => {
        expect(screen.getByTestId("live-indicator")).toBeOnTheScreen();
      });
    });
  });
});
