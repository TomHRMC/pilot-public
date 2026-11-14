/**
 * AtRiskJobsWidget unit tests — FE-B23
 *
 * Location: apps/web/src/features/dashboard/components/__tests__/AtRiskJobsWidget.test.tsx
 */

import { render, screen } from "@testing-library/react";
import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthContext } from "@pilot/ui/auth";
import type { AuthContextValue } from "@pilot/ui/auth";
import { NotificationQueueProvider } from "@pilot/ui/notification-banner";
import { AtRiskJobsWidget } from "../AtRiskJobsWidget";

vi.mock("../../hooks/useAtRiskJobs", () => ({
  useAtRiskJobs: vi.fn(),
}));

import { useAtRiskJobs } from "../../hooks/useAtRiskJobs";
import type { AtRiskJobsResponse } from "../../hooks/useAtRiskJobs";

const mockJobs: AtRiskJobsResponse = {
  jobs: [
    {
      job_id: "job-001",
      customer_name: "Johnson Electrical",
      site_name: "Main Office",
      status_code: "in_progress",
      scheduled_start_at: "2026-06-16T09:00:00Z",
      actual_cost_cents: 48000,
      quoted_budget_cents: 53000,
      projected_margin_pct: 9.4,
    },
  ],
  total: 1,
};

type TestRole = "owner" | "office_staff" | "technician" | "accountant";

function makeContext(role: TestRole): AuthContextValue {
  return {
    user: {
      id: "u1",
      email: "a@b.com",
      role,
      tenantId: "t1",
      displayName: "Test",
      accessToken: "tok",
    },
    isAuthenticated: true,
    role,
    signIn: vi.fn(),
    confirmMfaChallenge: vi.fn(),
    signOut: vi.fn(),
    refreshSession: vi.fn().mockResolvedValue("tok"),
  };
}

function makeQc() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
}

function Wrapper({
  role,
  children,
}: {
  role: TestRole;
  children: React.ReactNode;
}) {
  return (
    <AuthContext.Provider value={makeContext(role)}>
      <QueryClientProvider client={makeQc()}>
        <NotificationQueueProvider>{children}</NotificationQueueProvider>
      </QueryClientProvider>
    </AuthContext.Provider>
  );
}

describe("AtRiskJobsWidget", () => {
  beforeEach(() => {
    vi.mocked(useAtRiskJobs).mockReturnValue({
      data: mockJobs,
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useAtRiskJobs>);
  });

  it("renders at-risk jobs list with margin percentages", () => {
    render(<AtRiskJobsWidget />, {
      wrapper: ({ children }) => <Wrapper role="owner">{children}</Wrapper>,
    });
    expect(
      screen.getByText("Johnson Electrical — Main Office"),
    ).toBeInTheDocument();
    expect(screen.getByText("9.4%")).toBeInTheDocument();
  });

  it("shows empty state when no at-risk jobs", () => {
    vi.mocked(useAtRiskJobs).mockReturnValue({
      data: { jobs: [], total: 0 },
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useAtRiskJobs>);
    render(<AtRiskJobsWidget />, {
      wrapper: ({ children }) => <Wrapper role="owner">{children}</Wrapper>,
    });
    expect(screen.getByText("All jobs are on track")).toBeInTheDocument();
  });

  it("shows View Jobs link", () => {
    render(<AtRiskJobsWidget />, {
      wrapper: ({ children }) => <Wrapper role="owner">{children}</Wrapper>,
    });
    expect(screen.getByTestId("view-jobs-link")).toBeInTheDocument();
  });

  it("is hidden from tech role (RoleGate)", () => {
    render(<AtRiskJobsWidget />, {
      wrapper: ({ children }) => (
        <Wrapper role="technician">{children}</Wrapper>
      ),
    });
    expect(screen.queryByTestId("at-risk-jobs-widget")).not.toBeInTheDocument();
  });
});
