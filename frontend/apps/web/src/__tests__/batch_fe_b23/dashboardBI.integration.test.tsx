/**
 * Dashboard BI Integration Tests — FE-B23
 *
 * Location: apps/web/src/__tests__/batch_fe_b23/dashboardBI.integration.test.tsx
 *
 * Verifies AtRiskJobsWidget and PendingApprovalsWidget render on the dashboard.
 */

import { render, screen } from "@testing-library/react";
import React from "react";
import {
  describe,
  it,
  expect,
  vi,
  beforeAll,
  afterEach,
  afterAll,
} from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthContext } from "@pilot/ui/auth";
import type { AuthContextValue } from "@pilot/ui/auth";
import { NotificationQueueProvider } from "@pilot/ui/notification-banner";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import {
  mockAtRiskJobs,
  mockPendingApprovals,
} from "@/mocks/handlers/b23Handlers";

// Minimal dashboard for testing — just the BI widgets
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
}));
vi.mock("next/link", () => ({
  default: ({
    children,
    href,
    ...props
  }: {
    children: React.ReactNode;
    href: string;
    [key: string]: unknown;
  }) => (
    <a href={href} {...props}>
      {children}
    </a>
  ),
}));

// Mock the auth / onboarding hooks used by the real dashboard page
vi.mock("@/hooks/useLogout", () => ({
  useLogout: () => ({ logout: vi.fn() }),
}));
vi.mock("@/features/onboarding/hooks/useTrialStatus", () => ({
  useTrialStatus: () => ({ showSoftGate: false, daysRemaining: 30 }),
}));
vi.mock("@/features/onboarding/hooks/useOnboardingChecklist", () => ({
  useOnboardingChecklist: () => ({ data: null }),
}));
vi.mock("@/features/dashboard/components/RecentCustomerMessagesWidget", () => ({
  RecentCustomerMessagesWidget: () => <div data-testid="recent-messages" />,
}));
vi.mock("@/features/dashboard/components/ArSummaryWidget", () => ({
  ArSummaryWidget: () => <div data-testid="ar-summary" />,
}));

const server = setupServer(
  http.get("/api/v1/dashboard/at-risk-jobs", () =>
    HttpResponse.json({ jobs: mockAtRiskJobs, total: mockAtRiskJobs.length }),
  ),
  http.get("/api/v1/dashboard/pending-approvals-summary", () =>
    HttpResponse.json(mockPendingApprovals),
  ),
);

beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

function makeContext(
  role: "owner" | "office_staff" = "owner",
): AuthContextValue {
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

function Wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return (
    <AuthContext.Provider value={makeContext("owner")}>
      <QueryClientProvider client={qc}>
        <NotificationQueueProvider>{children}</NotificationQueueProvider>
      </QueryClientProvider>
    </AuthContext.Provider>
  );
}

// Import the actual dashboard page
import DashboardPage from "@/app/(authed)/dashboard/page";

describe("Dashboard BI — Integration", () => {
  it("dashboard renders AtRiskJobsWidget", async () => {
    render(<DashboardPage />, { wrapper: Wrapper });
    expect(
      await screen.findByTestId("at-risk-jobs-widget"),
    ).toBeInTheDocument();
  });

  it("dashboard renders PendingApprovalsWidget", async () => {
    render(<DashboardPage />, { wrapper: Wrapper });
    expect(
      await screen.findByTestId("pending-approvals-widget"),
    ).toBeInTheDocument();
  });

  it("at-risk jobs widget shows jobs from MSW", async () => {
    render(<DashboardPage />, { wrapper: Wrapper });
    // Use regex — customer_name may be split across text nodes with site_name
    expect(
      await screen.findByText(new RegExp(mockAtRiskJobs[0].customer_name)),
    ).toBeInTheDocument();
  });

  it("pending approvals widget shows counts from MSW", async () => {
    render(<DashboardPage />, { wrapper: Wrapper });
    // Finds the count badge (2 pending quotes)
    expect(
      await screen.findByText(String(mockPendingApprovals.pending_quotes)),
    ).toBeInTheDocument();
  });
});
