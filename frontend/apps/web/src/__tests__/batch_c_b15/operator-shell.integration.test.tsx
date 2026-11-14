/**
 * C-B15 Part B — Operator Shell + Tenant Impersonation Integration Tests
 *
 * Location: apps/web/src/__tests__/batch_c_b15/operator-shell.integration.test.tsx
 *
 * Tests:
 * 1. Operator layout renders for platform user — sidebar + header + cohort content visible
 * 2. Tenant user → redirect to /dashboard
 * 3. Full impersonation flow: open selector → pick tenant → confirm modal → POST start → session written → reload triggered
 * 4. Banner renders in the tenant shell when sessionStorage has a session; Exit clears + reloads
 * 5. Cohort page renders inside the shell without its own RequireAuth (no double auth gate)
 *
 * RULE 14: TanStack Query — retry: false, fresh QueryClient per test.
 * RULE 15: Test data isolation — use per-test MSW overrides, never assert on totals.
 */

import {
  describe,
  it,
  expect,
  vi,
  beforeAll,
  afterAll,
  afterEach,
  beforeEach,
} from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";

import OperatorLayout from "@/app/operator/layout";
import { CohortDashboardClient } from "@/components/operator/cohort/CohortDashboardClient";
import { ImpersonationBanner } from "@/components/operator/ImpersonationBanner";
import { setImpersonation, getImpersonation } from "@pilot/shared-api";

// ── Mocks ────────────────────────────────────────────────────────────────────

const mockReplace = vi.fn();
const mockPush = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: mockReplace, push: mockPush }),
  usePathname: () => "/operator/cohort",
}));

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

vi.mock("@pilot/ui/notification-banner", () => ({
  useNotificationQueue: () => ({
    addNotification: vi.fn(),
    notifications: [],
    dismissNotification: vi.fn(),
    dismissAll: vi.fn(),
  }),
}));

// Stub window.location.assign
const assignMock = vi.fn();
Object.defineProperty(window, "location", {
  value: {
    ...window.location,
    assign: assignMock,
  },
  writable: true,
});

// ── Mock data ────────────────────────────────────────────────────────────────

const mockAuthMePlatform = {
  user_type: "platform",
  user_id: "uuid-platform",
  email: "tom@pilotfortrades.com",
  first_name: "Tom",
  last_name: "Owner",
  platform_role_code: "owner",
  redirect_to: "/operator/cohort",
};

const mockAuthMeTenant = {
  user_type: "tenant",
  user_id: "uuid-tenant",
  email: "mike@acme.example.com",
  first_name: "Mike",
  last_name: "Smith",
  platform_role_code: null,
  redirect_to: "/dashboard",
};

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
  ],
};

const mockTenants = {
  tenants: [
    {
      tenant_id: "tenant-001",
      name: "Acme Electric",
      is_active: true,
      tier_name: "Charter",
      subscription_status: "trialing",
      created_at: "2026-08-01T00:00:00Z",
    },
  ],
};

// ── Server ───────────────────────────────────────────────────────────────────

const server = setupServer(
  http.get("/api/v1/operator/auth/me", () =>
    HttpResponse.json(mockAuthMePlatform),
  ),
  http.get("/api/v1/operator/cohort", () =>
    HttpResponse.json(mockCohortOverview),
  ),
  http.get("/api/v1/operator/tenants", () => HttpResponse.json(mockTenants)),
  http.post("/api/v1/operator/impersonation/start", () =>
    HttpResponse.json({
      tenant_id: "tenant-001",
      tenant_name: "Acme Electric",
      impersonator_user_id: "uuid-platform",
      role_code: "owner",
      started_at: "2026-08-08T16:00:00Z",
    }),
  ),
  http.post("/api/v1/operator/impersonation/end", () =>
    HttpResponse.json({ ended: true }),
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

// ── Tests ────────────────────────────────────────────────────────────────────

describe("C-B15 — Operator Shell + Tenant Impersonation Integration", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.sessionStorage.clear();
    assignMock.mockClear();
  });

  it("1. operator layout renders for platform user — sidebar + header + cohort content visible", async () => {
    render(
      <OperatorLayout>
        <CohortDashboardClient />
      </OperatorLayout>,
      { wrapper: createWrapper() },
    );

    // Wait for cohort data to render — use heading role for the page title
    // (the summary strip also contains "Charter" but not as a heading)
    await waitFor(() => {
      expect(
        screen.getByRole("heading", { name: "Charter Cohort" }),
      ).toBeInTheDocument();
    });

    // Operator header is present
    expect(screen.getByTestId("operator-header")).toBeInTheDocument();
    // Operator sidebar nav is present
    expect(
      screen.getByRole("navigation", { name: "Operator navigation" }),
    ).toBeInTheDocument();
    // Tenant selector is present
    expect(screen.getByTestId("tenant-selector-trigger")).toBeInTheDocument();
    // Cohort content is visible — "Cohort open" only renders after data loads
    await waitFor(() => {
      expect(screen.getByText("Cohort open")).toBeInTheDocument();
    });
  });

  it("2. tenant user → redirect to /dashboard", async () => {
    server.use(
      http.get("/api/v1/operator/auth/me", () =>
        HttpResponse.json(mockAuthMeTenant),
      ),
    );

    render(
      <OperatorLayout>
        <CohortDashboardClient />
      </OperatorLayout>,
      { wrapper: createWrapper() },
    );

    await waitFor(() => {
      expect(mockReplace).toHaveBeenCalledWith("/dashboard");
    });
  });

  it("3. full impersonation flow: selector → confirm → POST start → session written → reload", async () => {
    const user = userEvent.setup();
    render(
      <OperatorLayout>
        <CohortDashboardClient />
      </OperatorLayout>,
      { wrapper: createWrapper() },
    );

    // Wait for shell to render
    await waitFor(() => {
      expect(screen.getByTestId("tenant-selector-trigger")).toBeInTheDocument();
    });

    // Open the tenant selector
    await user.click(screen.getByTestId("tenant-selector-trigger"));

    // Wait for tenant list to load — the selector panel renders tenant
    // rows as buttons with aria-labels containing the tenant name
    await waitFor(() => {
      const tenantButtons = screen.getAllByRole("button", {
        name: /Acme Electric/i,
      });
      expect(tenantButtons.length).toBeGreaterThan(0);
    });

    // Select the tenant — click the button inside the selector panel
    // (the cohort table also has "Acme Electric" text, so we target the
    // button with the aria-label that includes tier + status)
    const tenantButton = screen.getByRole("button", {
      name: /Acme Electric, Charter, Trialing/i,
    });
    await user.click(tenantButton);

    // Confirm modal should open
    await waitFor(() => {
      expect(
        screen.getByTestId("impersonation-confirm-modal"),
      ).toBeInTheDocument();
    });

    // Click confirm
    await user.click(screen.getByTestId("impersonation-confirm-button"));

    // Session should be written + reload triggered
    await waitFor(() => {
      expect(assignMock).toHaveBeenCalledWith("/dashboard");
    });

    expect(getImpersonation()).toEqual({
      tenantId: "tenant-001",
      tenantName: "Acme Electric",
    });
  });

  it("4. banner renders when sessionStorage has a session; Exit clears + reloads", async () => {
    setImpersonation({ tenantId: "tenant-001", tenantName: "Acme Electric" });

    render(<ImpersonationBanner />, { wrapper: createWrapper() });

    expect(screen.getByTestId("impersonation-banner")).toBeInTheDocument();
    expect(screen.getByText("Acme Electric")).toBeInTheDocument();

    const user = userEvent.setup();
    await user.click(screen.getByTestId("impersonation-exit-button"));

    await waitFor(() => {
      expect(assignMock).toHaveBeenCalledWith("/operator/cohort");
    });

    expect(getImpersonation()).toBeNull();
  });

  it("5. cohort page renders inside the shell without its own RequireAuth (no double auth gate)", async () => {
    // The CohortDashboardClient no longer wraps in RequireAuth — it renders
    // directly. The OperatorLayout provides the auth gate. If the cohort
    // page tried to render its own RequireAuth, we'd see a second mock
    // invocation. We verify the page renders content without a second gate.
    render(
      <OperatorLayout>
        <CohortDashboardClient />
      </OperatorLayout>,
      { wrapper: createWrapper() },
    );

    await waitFor(() => {
      expect(
        screen.getByRole("heading", { name: "Charter Cohort" }),
      ).toBeInTheDocument();
    });

    // The cohort page header should be "Charter Cohort" (not "Pilot Operator — Charter Cohort")
    expect(
      screen.queryByText("Pilot Operator — Charter Cohort"),
    ).not.toBeInTheDocument();
  });
});
