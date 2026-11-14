/**
 * C-B5 Dashboard page — CharterMemberBadge owner-only integration test
 *
 * Location: apps/web/src/__tests__/batch_c_b5/dashboard_charter_badge.integration.test.tsx
 *
 * Verifies:
 *  - Owner sees CharterMemberBadge when charterMemberNumber is set
 *  - Non-owner does not see badge
 */

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
import { render, screen, waitFor } from "@testing-library/react";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthContext } from "@pilot/ui/auth";
import type { AuthContextValue, PilotUser } from "@pilot/ui/auth";

const { replace, push } = vi.hoisted(() => ({
  replace: vi.fn(),
  push: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push, replace, back: vi.fn() }),
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
vi.mock("@/features/dashboard/components/AtRiskJobsWidget", () => ({
  AtRiskJobsWidget: () => <div data-testid="at-risk-jobs" />,
}));
vi.mock("@/features/dashboard/components/PendingApprovalsWidget", () => ({
  PendingApprovalsWidget: () => <div data-testid="pending-approvals" />,
}));

import DashboardPage from "@/app/(authed)/dashboard/page";

const server = setupServer();

beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => {
  server.resetHandlers();
});
afterAll(() => server.close());

const TENANT_ID = "tenant-cb5-dash-test-001";

function makeQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
}

function makeAuthValue(role: "owner" | "technician"): AuthContextValue {
  const user: PilotUser = {
    id: "user-001",
    email: "mike@apex.example.com",
    role,
    tenantId: TENANT_ID,
    displayName: "Mike",
    accessToken: "mock-token",
  };
  return {
    user,
    isAuthenticated: true,
    role,
    signIn: vi.fn(),
    confirmMfaChallenge: vi.fn(),
    signOut: vi.fn(),
    refreshSession: vi.fn().mockResolvedValue("mock-token"),
  };
}

function renderDashboard(role: "owner" | "technician") {
  return render(
    <AuthContext.Provider value={makeAuthValue(role)}>
      <QueryClientProvider client={makeQueryClient()}>
        <DashboardPage />
      </QueryClientProvider>
    </AuthContext.Provider>,
  );
}

describe("C-B5 — Dashboard CharterMemberBadge", () => {
  it("owner sees CharterMemberBadge when charterMemberNumber is set", async () => {
    server.use(
      http.get(`/api/v1/signup/${TENANT_ID}/state`, () =>
        HttpResponse.json({
          tenant_id: TENANT_ID,
          signup_state: "complete",
          collected_data: {
            requires_payment_method: false,
            free_period_ends_at: "2026-11-02T18:37:42Z",
            charter_member_number: 7,
          },
        }),
      ),
    );

    renderDashboard("owner");

    await waitFor(() => {
      expect(screen.getByTestId("charter-member-badge")).toBeInTheDocument();
    });

    expect(screen.getByTestId("charter-member-badge")).toHaveTextContent(
      "Charter Member #7",
    );
  });

  it("non-owner does not see badge", async () => {
    server.use(
      http.get(`/api/v1/signup/${TENANT_ID}/state`, () =>
        HttpResponse.json({
          tenant_id: TENANT_ID,
          signup_state: "complete",
          collected_data: {
            requires_payment_method: false,
            free_period_ends_at: "2026-11-02T18:37:42Z",
            charter_member_number: 7,
          },
        }),
      ),
    );

    renderDashboard("technician");

    // Wait a tick for any async rendering
    await waitFor(() => {
      expect(
        screen.queryByTestId("charter-member-badge"),
      ).not.toBeInTheDocument();
    });
  });
});
