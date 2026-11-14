/**
 * UP-1 (Part B) — WIP Report Page Integration Tests
 *
 * Location: apps/web/src/__tests__/batch_up_1/wip-report.integration.test.tsx
 *
 * Verifies:
 * 1. /reports/wip route renders (not 404) with MSW happy-path data
 * 2. RBAC: authorized role (owner) sees the table; unauthorized role does not
 * 3. Populated table shows a specific job by job_number/content
 * 4. Sort interaction fires the correct URL param change
 * 5. Empty state renders with the row_count:0 fixture
 * 6. Error/paywall state renders <ErrorState> with the 402 fixture
 *
 * Per batch-up-1-react-engr-prompt.md Test Requirements.
 */

import React from "react";
import {
  describe,
  it,
  expect,
  vi,
  beforeAll,
  afterAll,
  afterEach,
} from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { AuthContext } from "@pilot/ui/auth";
import type { AuthContextValue } from "@pilot/ui/auth";
import { WipReportPage } from "../../features/wip/components/WipReportPage";

// ─── Next.js mocks ─────────────────────────────────────────────────────────

const mockReplace = vi.fn();
const mockPush = vi.fn();

vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams(),
  useRouter: () => ({ push: mockPush, replace: mockReplace }),
  usePathname: () => "/reports/wip",
}));

// ─── Auth context ──────────────────────────────────────────────────────────

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

const techAuthValue: AuthContextValue = {
  user: {
    id: "u2",
    email: "tech@example.com",
    role: "technician",
    tenantId: "t1",
    displayName: "Tech",
    accessToken: "tok",
  },
  isAuthenticated: true,
  role: "technician",
  signIn: vi.fn(),
  confirmMfaChallenge: vi.fn(),
  signOut: vi.fn(),
  refreshSession: vi.fn().mockResolvedValue("tok"),
};

// ─── Fixtures ───────────────────────────────────────────────────────────────

const happyResponse = {
  report_type: "wip",
  generated_at: "2026-07-29T14:00:00Z",
  margin_target_pct: 20.0,
  row_count: 2,
  summary: {
    active_job_count: 2,
    total_actual_cost_cents: 72000,
    total_quoted_budget_cents: 180000,
    total_projected_cost_cents: 134000,
    jobs_over_budget_count: 1,
    jobs_below_margin_target_count: 1,
  },
  rows: [
    {
      job_id: "job-1",
      job_number: "JOB-000101",
      title: "Panel upgrade — Office complex",
      customer_name: "Apex Commercial LLC",
      site_name: "North Warehouse",
      status_code: "in_progress",
      scheduled_start_at: "2026-07-20T13:00:00Z",
      quoted_budget_cents: 60000,
      actual_cost_cents: 42000,
      etc_hours_remaining: 6.5,
      etc_cost_cents: 22000,
      projected_cost_cents: 64000,
      projected_margin_pct: -6.67,
      budget_deviation_pct: -6.67,
      has_etc: true,
      below_margin_target: true,
    },
    {
      job_id: "job-2",
      job_number: "JOB-000102",
      title: "EV charger install × 4",
      customer_name: "Green Auto Group",
      site_name: "Main Lot",
      status_code: "scheduled",
      scheduled_start_at: "2026-08-01T08:00:00Z",
      quoted_budget_cents: 120000,
      actual_cost_cents: 30000,
      etc_hours_remaining: 10,
      etc_cost_cents: 40000,
      projected_cost_cents: 70000,
      projected_margin_pct: 41.67,
      budget_deviation_pct: 41.67,
      has_etc: true,
      below_margin_target: false,
    },
  ],
};

const emptyResponse = {
  report_type: "wip",
  generated_at: "2026-07-29T14:00:00Z",
  margin_target_pct: 20.0,
  row_count: 0,
  summary: {
    active_job_count: 0,
    total_actual_cost_cents: 0,
    total_quoted_budget_cents: 0,
    total_projected_cost_cents: 0,
    jobs_over_budget_count: 0,
    jobs_below_margin_target_count: 0,
  },
  rows: [],
};

// ─── MSW server ─────────────────────────────────────────────────────────────

const server = setupServer(
  http.get("*/api/v1/reports/wip", () => HttpResponse.json(happyResponse)),
);

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => {
  server.resetHandlers();
  mockReplace.mockClear();
  mockPush.mockClear();
});
afterAll(() => server.close());

// ─── Helpers ────────────────────────────────────────────────────────────────

function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
}

function renderWithAuth(authValue: AuthContextValue) {
  const client = createQueryClient();
  return render(
    React.createElement(
      AuthContext.Provider,
      { value: authValue },
      React.createElement(
        QueryClientProvider,
        { client },
        React.createElement(WipReportPage),
      ),
    ),
  );
}

// ─── Tests ──────────────────────────────────────────────────────────────────

describe("UP-1 (Part B) — WIP Report Page Integration", () => {
  it("1. renders the page with happy-path data (not 404)", async () => {
    renderWithAuth(ownerAuthValue);
    expect(screen.getByText("Work-In-Progress")).toBeTruthy();
    await waitFor(() => {
      expect(screen.getByText("JOB-000101")).toBeTruthy();
    });
  });

  it("2. RBAC — owner sees the table; tech role does not", async () => {
    const { rerender } = renderWithAuth(ownerAuthValue);
    await waitFor(() => {
      expect(screen.getByText("JOB-000101")).toBeTruthy();
    });

    // Re-render with tech role — content should be hidden by RoleGate
    const client = createQueryClient();
    rerender(
      React.createElement(
        AuthContext.Provider,
        { value: techAuthValue },
        React.createElement(
          QueryClientProvider,
          { client },
          React.createElement(WipReportPage),
        ),
      ),
    );
    expect(screen.queryByText("Work-In-Progress")).toBeNull();
  });

  it("3. populated table shows a specific job by job_number", async () => {
    renderWithAuth(ownerAuthValue);
    await waitFor(() => {
      expect(screen.getByText("JOB-000102")).toBeTruthy();
    });
    // Customer name should also be visible
    expect(screen.getByText("Green Auto Group")).toBeTruthy();
  });

  it("4. sort interaction fires the correct URL param change", async () => {
    const user = userEvent.setup();
    renderWithAuth(ownerAuthValue);
    await waitFor(() => {
      expect(screen.getByText("JOB-000101")).toBeTruthy();
    });

    // Click the "Margin" sortable header
    const marginHeader = screen.getByText("Margin");
    await user.click(marginHeader);

    // router.replace should have been called with sort=projected_margin_pct
    expect(mockReplace).toHaveBeenCalled();
    const callArg = mockReplace.mock.calls[0][0] as string;
    expect(callArg).toContain("sort=projected_margin_pct");
    expect(callArg).toContain("order=desc");
  });

  it("5. empty state renders with row_count:0 fixture", async () => {
    server.use(
      http.get("*/api/v1/reports/wip", () => HttpResponse.json(emptyResponse)),
    );
    renderWithAuth(ownerAuthValue);
    await waitFor(() => {
      expect(screen.getByText("No active jobs right now")).toBeTruthy();
    });
  });

  it("6. error/paywall state renders ErrorState with 402 fixture", async () => {
    server.use(
      http.get("*/api/v1/reports/wip", () =>
        HttpResponse.json(
          { type: "https://errors.pilotfortrades.com/entitlement-exceeded" },
          { status: 402 },
        ),
      ),
    );
    renderWithAuth(ownerAuthValue);
    await waitFor(() => {
      expect(screen.getByText("Billing required")).toBeTruthy();
    });
  });
});
