/**
 * Profitability Page Happy Path — Integration Tests
 *
 * Location: apps/web/__tests__/batch_fe_b4/profitability-page-happy-path.integration.test.tsx
 * Per batch-fe-b4-design.md §I.2
 * Target: 2 tests
 */

import {
  describe,
  it,
  expect,
  vi,
  beforeAll,
  afterEach,
  afterAll,
} from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import "@testing-library/jest-dom";
import React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { setupServer } from "msw/node";
import { reportsHandlers } from "../../src/mocks/handlers/reports";

// ── Mock RoleGate to bypass auth checks in integration tests ──────────────────
vi.mock("@pilot/ui/role-gate", () => ({
  RoleGate: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  useRequiresPermission: () => ({ permitted: true }),
  ROLE_PERMISSION_MAP: {},
}));

vi.mock("@pilot/ui/auth", () => ({
  useAuth: () => ({
    user: { id: "user-1", email: "owner@test.com" },
    role: "owner",
    isAuthenticated: true,
    signIn: vi.fn(),
    signOut: vi.fn(),
    refreshSession: vi.fn(),
    confirmMfaChallenge: vi.fn(),
  }),
  AuthContext: { _currentValue: null },
}));

// ── Recharts mock (avoid canvas/SVG issues in jsdom) ─────────────────────────
vi.mock("recharts", () => ({
  BarChart: ({ children }: { children: React.ReactNode }) =>
    React.createElement("div", { "data-testid": "bar-chart" }, children),
  Bar: () => null,
  XAxis: () => null,
  YAxis: () => null,
  Tooltip: () => null,
  Cell: () => null,
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) =>
    React.createElement("div", null, children),
}));

const server = setupServer(...reportsHandlers);

beforeAll(() => server.listen({ onUnhandledRequest: "bypass" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

function makeWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  };
}

describe("Profitability Page — Happy Path Integration", () => {
  it("page loads with Profitability heading and 30d period selector", async () => {
    const { ProfitabilityPage } =
      await import("../../src/features/profitability/components/ProfitabilityPage");

    render(<ProfitabilityPage />, { wrapper: makeWrapper() });

    await waitFor(
      () => {
        expect(screen.getByText("Profitability")).toBeInTheDocument();
      },
      { timeout: 5000 },
    );

    expect(screen.getByText("30 days")).toBeInTheDocument();
  });

  it("period selector allows switching to 7 days", async () => {
    const { ProfitabilityPage } =
      await import("../../src/features/profitability/components/ProfitabilityPage");

    render(<ProfitabilityPage />, { wrapper: makeWrapper() });

    await waitFor(() => {
      expect(screen.getByText("7 days")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("7 days"));

    await waitFor(() => {
      const btn = screen.getByText("7 days");
      expect(btn).toHaveAttribute("aria-pressed", "true");
    });
  });
});
