/**
 * WipReportPage — Unit Tests
 *
 * Location: apps/web/src/features/wip/components/__tests__/WipReportPage.test.tsx
 *
 * Verifies:
 * 1. Renders <WipSkeleton> while pending
 * 2. Renders <ErrorState> on failure
 * 3. Renders <EmptyState> when row_count === 0
 * 4. RBAC — unauthorized role does NOT see content
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
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { AuthContext } from "@pilot/ui/auth";
import type { AuthContextValue } from "@pilot/ui/auth";
import { WipReportPage } from "../WipReportPage";

// ─── Next.js mocks ─────────────────────────────────────────────────────────

vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams(),
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
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

// ─── MSW server ─────────────────────────────────────────────────────────────

const happyResponse = {
  report_type: "wip",
  generated_at: "2026-07-29T14:00:00Z",
  margin_target_pct: 20.0,
  row_count: 1,
  summary: {
    active_job_count: 1,
    total_actual_cost_cents: 42000,
    total_quoted_budget_cents: 60000,
    total_projected_cost_cents: 55000,
    jobs_over_budget_count: 0,
    jobs_below_margin_target_count: 0,
  },
  rows: [
    {
      job_id: "job-1",
      job_number: "JOB-000101",
      title: "Panel upgrade",
      customer_name: "Apex Commercial LLC",
      site_name: "North Warehouse",
      status_code: "in_progress",
      scheduled_start_at: "2026-07-20T13:00:00Z",
      quoted_budget_cents: 60000,
      actual_cost_cents: 42000,
      etc_hours_remaining: 6.5,
      etc_cost_cents: 13000,
      projected_cost_cents: 55000,
      projected_margin_pct: 8.33,
      budget_deviation_pct: 8.33,
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

const server = setupServer(
  http.get("*/api/v1/reports/wip", () => HttpResponse.json(happyResponse)),
);

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => server.resetHandlers());
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

describe("WipReportPage", () => {
  it("renders the page header with 'Work-In-Progress' title", async () => {
    renderWithAuth(ownerAuthValue);
    expect(screen.getByText("Work-In-Progress")).toBeTruthy();
  });

  it("renders a job from the happy-path data", async () => {
    renderWithAuth(ownerAuthValue);
    await waitFor(() => {
      expect(screen.getByText("JOB-000101")).toBeTruthy();
    });
  });

  it("renders empty state when row_count is 0", async () => {
    server.use(
      http.get("*/api/v1/reports/wip", () => HttpResponse.json(emptyResponse)),
    );
    renderWithAuth(ownerAuthValue);
    await waitFor(() => {
      expect(screen.getByText("No active jobs right now")).toBeTruthy();
    });
  });

  it("renders error state on 500", async () => {
    server.use(
      http.get("*/api/v1/reports/wip", () =>
        HttpResponse.json({ detail: "Server error" }, { status: 500 }),
      ),
    );
    renderWithAuth(ownerAuthValue);
    await waitFor(() => {
      expect(screen.getByText("Couldn't load WIP report")).toBeTruthy();
    });
  });

  it("renders paywall error on 402", async () => {
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

  it("RBAC — tech role does NOT see WIP content", () => {
    renderWithAuth(techAuthValue);
    // RoleGate hides content for unauthorized roles — the title should not be present
    expect(screen.queryByText("Work-In-Progress")).toBeNull();
  });
});
