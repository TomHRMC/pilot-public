/**
 * BETA-B6: Reports custom date range integration test
 *
 * Location: apps/web/src/__tests__/batch_beta_v1_b6/reports-custom-date.integration.test.tsx
 *
 * Verifies that:
 * 1. Selecting "Custom" shows date range inputs
 * 2. The API is NOT called when Custom is selected but dates are incomplete
 * 3. Once both dates are provided, the correct date_from / date_to params are
 *    passed to the /api/v1/reports/profitability endpoint
 */

import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {
  describe,
  it,
  expect,
  vi,
  beforeAll,
  afterAll,
  afterEach,
} from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { AuthContext } from "@pilot/ui/auth";
import type { AuthContextValue } from "@pilot/ui/auth";
import { ProfitabilityPage } from "../../features/profitability/components/ProfitabilityPage";

// ─── Next.js mocks ─────────────────────────────────────────────────────────
vi.mock("next/navigation", () => ({
  usePathname: () => "/reports",
}));

// ─── Auth context — owner role (required by ProfitabilityPage RoleGate) ────
const ownerAuthValue: AuthContextValue = {
  user: {
    id: "u1",
    email: "owner@example.com",
    role: "owner",
    tenantId: "t1",
    displayName: "Owner",
    accessToken: "tok",
  },
  isAuthenticated: true,
  role: "owner",
  signIn: vi.fn(),
  confirmMfaChallenge: vi.fn(),
  signOut: vi.fn(),
  refreshSession: vi.fn().mockResolvedValue("tok"),
};

// ─── MSW server ─────────────────────────────────────────────────────────────
const capturedRequests: URL[] = [];

const server = setupServer(
  http.get("*/api/v1/reports/profitability", ({ request }) => {
    capturedRequests.push(new URL(request.url));
    return HttpResponse.json({
      period: "custom",
      closed_jobs: [],
      summary: {
        total_revenue_cents: 0,
        total_profit_cents: 0,
        avg_margin_pct: 0,
        period_over_period_revenue_delta_pct: 0,
        period_over_period_profit_delta_pct: 0,
        period_over_period_margin_delta_pct: 0,
      },
      margin_distribution: { "below-low": 0, low: 0, medium: 0, high: 0 },
    });
  }),
);

beforeAll(() => server.listen({ onUnhandledRequest: "bypass" }));
afterEach(() => {
  capturedRequests.length = 0;
  server.resetHandlers();
});
afterAll(() => server.close());

// ─── Render helper ───────────────────────────────────────────────────────────
function renderPage() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    React.createElement(
      AuthContext.Provider,
      { value: ownerAuthValue },
      React.createElement(
        QueryClientProvider,
        { client: qc },
        React.createElement(ProfitabilityPage),
      ),
    ),
  );
}

// ─── Tests ────────────────────────────────────────────────────────────────────
describe("ProfitabilityPage — BETA-B6 custom date range", () => {
  it("shows date inputs when Custom pill is clicked", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.click(screen.getByText("Custom"));

    expect(screen.getByLabelText(/from/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/to/i)).toBeInTheDocument();
  });

  it("shows 'select a start and end date' prompt when Custom is selected but dates are empty", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.click(screen.getByText("Custom"));

    expect(
      screen.getByText(/select a start and end date/i),
    ).toBeInTheDocument();
  });

  it("API is NOT called when Custom is selected but only one date is filled in", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.click(screen.getByText("Custom"));
    const fromInput = screen.getByLabelText(/from/i);
    await user.type(fromInput, "2026-05-01");

    // Give any potential API call time to fire
    await new Promise((r) => setTimeout(r, 150));

    // Only the initial 30d query should have fired before the user switched to custom.
    // After switching to custom with incomplete dates, no new request for custom dates.
    const customRequests = capturedRequests.filter(
      (u) =>
        u.searchParams.get("date_from") === "2026-05-01" &&
        !u.searchParams.get("date_to"),
    );
    expect(customRequests).toHaveLength(0);
  });

  it("passes date_from and date_to to the API when both custom dates are provided", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.click(screen.getByText("Custom"));

    const fromInput = screen.getByLabelText(/from/i);
    const toInput = screen.getByLabelText(/to/i);

    await user.type(fromInput, "2026-05-01");
    await user.type(toInput, "2026-05-31");

    await waitFor(
      () => {
        const customReq = capturedRequests.find(
          (u) =>
            u.searchParams.get("date_from") === "2026-05-01" &&
            u.searchParams.get("date_to") === "2026-05-31",
        );
        expect(customReq).toBeDefined();
      },
      { timeout: 3000 },
    );
  });
});
