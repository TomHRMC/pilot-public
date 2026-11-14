/**
 * Cohort Dashboard integration tests — web (C-B11 Part B)
 *
 * Location: apps/web/src/__tests__/batch_c_b11/cohort-dashboard.integration.test.tsx
 *
 * Tests: page renders, table shows members, extend modal flow, close cohort flow, empty state.
 * RULE 14: TanStack Query — retry: false, fresh QueryClient per test.
 * RULE 15: Test data isolation — use per-test MSW overrides, never assert on totals.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { CohortDashboardClient } from "@/components/operator/cohort/CohortDashboardClient";

// ── Mock auth ─────────────────────────────────────────────────────────────────

vi.mock("@pilot/ui/auth", () => ({
  RequireAuth: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  useAuth: () => ({
    isAuthenticated: true,
    role: "accountant",
    user: {
      id: "platform-user-001",
      email: "tom@pilotfortrades.com",
      role: "accountant",
      tenantId: "",
      displayName: "Tom Owner",
      accessToken: "mock-token",
    },
    signOut: vi.fn(),
    signIn: vi.fn(),
    confirmMfaChallenge: vi.fn(),
    refreshSession: vi.fn(),
  }),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    replace: vi.fn(),
    push: vi.fn(),
  }),
}));

vi.mock("@pilot/ui/notification-banner", () => ({
  useNotificationQueue: () => ({
    addNotification: vi.fn(),
    notifications: [],
    dismissNotification: vi.fn(),
    dismissAll: vi.fn(),
  }),
}));

// ── Mock data ─────────────────────────────────────────────────────────────────

const mockCohortOverview = {
  cohort_tier_name: "Charter",
  cohort_is_active: true,
  signup_cap: 12,
  members: [
    {
      tenant_id: "tenant-001",
      business_name: "Acme Electric",
      charter_member_number: 1,
      free_period_ends_at: "2026-11-04T00:00:00Z",
      days_remaining: 90,
      stripe_status: "trialing",
      has_payment_method: false,
      messaging_status: "not_started",
      customer_count: 3,
      invoice_count: 2,
      days_since_last_job: 5,
      last_contact: null,
      alert_level: "none",
    },
    {
      tenant_id: "tenant-002",
      business_name: "Volts & Co",
      charter_member_number: 2,
      free_period_ends_at: "2026-08-14T00:00:00Z",
      days_remaining: 7,
      stripe_status: "trialing",
      has_payment_method: false,
      messaging_status: "active",
      customer_count: 1,
      invoice_count: 0,
      days_since_last_job: 3,
      last_contact: null,
      alert_level: "amber",
    },
    {
      tenant_id: "tenant-003",
      business_name: "Sparky Services",
      charter_member_number: 3,
      free_period_ends_at: "2026-12-01T00:00:00Z",
      days_remaining: 120,
      stripe_status: "trialing",
      has_payment_method: false,
      messaging_status: "not_started",
      customer_count: 0,
      invoice_count: 0,
      days_since_last_job: null,
      last_contact: null,
      alert_level: "red",
    },
  ],
};

const mockAuthMePlatform = {
  user_type: "platform",
  user_id: "uuid-platform",
  email: "tom@pilotfortrades.com",
  first_name: "Tom",
  last_name: "Owner",
  platform_role_code: "owner",
  redirect_to: "/operator/cohort",
};

// ── Server setup ──────────────────────────────────────────────────────────────

const server = setupServer(
  http.get("/api/v1/operator/cohort", () =>
    HttpResponse.json(mockCohortOverview),
  ),
  http.get("/api/v1/operator/auth/me", () =>
    HttpResponse.json(mockAuthMePlatform),
  ),
  http.post("/api/v1/operator/cohort/:tenantId/extend", () =>
    HttpResponse.json({
      tenant_id: "tenant-001",
      previous_free_period_ends_at: "2026-11-04T00:00:00Z",
      new_free_period_ends_at: "2026-12-04T00:00:00Z",
      stripe_subscription_id: "sub_mock_001",
      stripe_trial_end_updated: true,
    }),
  ),
  http.post("/api/v1/operator/cohort/close", () =>
    HttpResponse.json({
      charter_price_archived: true,
      charter_tier_deactivated: true,
      activated_tiers: ["trial", "starter", "teams"],
    }),
  ),
);

beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  }
  return Wrapper;
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("Cohort Dashboard — Integration (C-B11 Part B)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the page header and cohort summary strip", async () => {
    render(<CohortDashboardClient />, { wrapper: createWrapper() });

    // Wait for data-dependent content (summary strip renders only after
    // the cohort query resolves).
    await waitFor(() => {
      expect(screen.getByText("Cohort open")).toBeInTheDocument();
    });

    // C-B15: title simplified from "Pilot Operator — Charter Cohort" to
    // "Charter Cohort" (the operator shell layout now provides the logo +
    // "Operator" badge).
    expect(screen.getByText("Charter Cohort")).toBeInTheDocument();
    expect(screen.getByText(/3 \/ 12 members/i)).toBeInTheDocument();
  });

  it("shows all members in the table with correct data", async () => {
    render(<CohortDashboardClient />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText("Acme Electric")).toBeInTheDocument();
    });

    expect(screen.getByText("Volts & Co")).toBeInTheDocument();
    expect(screen.getByText("Sparky Services")).toBeInTheDocument();
    expect(screen.getByText("Activation risk")).toBeInTheDocument();
    expect(screen.getByText("Expiring soon")).toBeInTheDocument();
    expect(screen.getAllByText("Healthy").length).toBeGreaterThan(0);
  });

  it("opens the extend modal when clicking Extend on a member row", async () => {
    const user = userEvent.setup();
    render(<CohortDashboardClient />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText("Acme Electric")).toBeInTheDocument();
    });

    // Click the first Extend button
    const extendButtons = screen.getAllByRole("button", { name: /extend/i });
    await user.click(extendButtons[0]);

    // The modal title contains "Extend free period" — use heading role
    expect(
      screen.getByRole("heading", { name: /extend free period/i }),
    ).toBeInTheDocument();
    expect(screen.getByText("Current free period ends")).toBeInTheDocument();
    expect(screen.getByText(/November \d, 2026/)).toBeInTheDocument();
  });

  it("opens the close cohort confirmation modal", async () => {
    const user = userEvent.setup();
    render(<CohortDashboardClient />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /close charter cohort/i }),
      ).toBeInTheDocument();
    });

    await user.click(
      screen.getByRole("button", { name: /close charter cohort/i }),
    );

    expect(screen.getByText("Close Charter cohort?")).toBeInTheDocument();
    expect(screen.getByText("This cannot be undone.")).toBeInTheDocument();
  });

  it("renders empty state when no members exist", async () => {
    server.use(
      http.get("/api/v1/operator/cohort", () =>
        HttpResponse.json({
          cohort_tier_name: "Charter",
          cohort_is_active: true,
          signup_cap: 12,
          members: [],
        }),
      ),
    );

    render(<CohortDashboardClient />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText("No Charter members yet")).toBeInTheDocument();
    });

    expect(
      screen.getByText("Members will appear here when they sign up."),
    ).toBeInTheDocument();
  });
});
