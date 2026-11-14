/**
 * UI-FIX-2E: Nav Redesign Integration Tests
 *
 * Location: apps/web/src/__tests__/batch_ui_fix_2e/nav_redesign.integration.test.tsx
 *
 * Tests:
 *   - AuthedLayout renders logo linking to /dashboard
 *   - AuthedLayout header contains NotificationBell area, SettingsGearIcon, ProfileDropdown
 *   - DashboardPage does NOT render Sign Out button
 */

import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import "@testing-library/jest-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthContext } from "@pilot/ui/auth";
import type { AuthContextValue } from "@pilot/ui/auth";

// ─── Mocks ────────────────────────────────────────────────────────────────────
vi.mock("next/navigation", () => ({
  usePathname: () => "/dashboard",
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
}));

vi.mock("next/link", () => ({
  default: ({
    href,
    children,
    ...rest
  }: {
    href: string;
    children: React.ReactNode;
    [key: string]: unknown;
  }) => React.createElement("a", { href, ...rest }, children),
}));

vi.mock("next/image", () => ({
  default: ({
    src,
    alt,
    ...rest
  }: {
    src: string;
    alt: string;
    [key: string]: unknown;
  }) => React.createElement("img", { src, alt, ...rest }),
}));

// Mock child components to isolate layout structure tests
vi.mock("@/components/AppSidebar", () => ({
  AppSidebar: () =>
    React.createElement("nav", { "data-testid": "app-sidebar" }, "Sidebar"),
}));

vi.mock("@/features/notifications-center/components/NotificationBell", () => ({
  NotificationBell: () =>
    React.createElement(
      "button",
      { "data-testid": "notification-bell" },
      "Bell",
    ),
}));

vi.mock(
  "@/features/notifications-center/components/NotificationDrawer",
  () => ({
    NotificationDrawer: () => null,
  }),
);

vi.mock("@/hooks/useSessionExpiry", () => ({
  useSessionExpiry: () => undefined,
}));

// SIGNUP-UI-FIX-1: SignupCompletionGuard is tested separately; mock it
// to pass-through so layout structure tests aren't blocked by its API fetch.
vi.mock("@/components/SignupCompletionGuard", () => ({
  SignupCompletionGuard: ({ children }: { children: React.ReactNode }) =>
    React.createElement(React.Fragment, null, children),
}));

vi.mock("@/hooks/useLogout", () => ({
  useLogout: () => ({ logout: vi.fn() }),
}));

vi.mock("@pilot/ui/auth", async () => {
  const actual =
    await vi.importActual<typeof import("@pilot/ui/auth")>("@pilot/ui/auth");
  return {
    ...actual,
    RequireAuth: ({ children }: { children: React.ReactNode }) =>
      React.createElement(React.Fragment, null, children),
  };
});

// ─── Shared auth value ────────────────────────────────────────────────────────
const authValue: AuthContextValue = {
  user: {
    id: "u1",
    email: "mike@example.com",
    role: "owner",
    tenantId: "t1",
    displayName: "Mike Johnson",
    accessToken: "tok",
  },
  isAuthenticated: true,
  role: "owner",
  signIn: vi.fn(),
  confirmMfaChallenge: vi.fn(),
  signOut: vi.fn(),
  refreshSession: vi.fn().mockResolvedValue("tok"),
};

function makeQc() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
}

// ─── Tests ────────────────────────────────────────────────────────────────────
describe("UI-FIX-2E — AuthedLayout nav redesign", () => {
  it("header has a link to /dashboard (logo)", async () => {
    const AuthedLayout = (await import("@/app/(authed)/layout")).default;
    render(
      React.createElement(
        QueryClientProvider,
        { client: makeQc() },
        React.createElement(
          AuthContext.Provider,
          { value: authValue },
          React.createElement(
            AuthedLayout,
            null,
            React.createElement("div", null, "page content"),
          ),
        ),
      ),
    );
    const logoLink = screen.getByRole("link", { name: /go to dashboard/i });
    expect(logoLink).toHaveAttribute("href", "/dashboard");
  });

  it("header contains the NotificationBell", async () => {
    const AuthedLayout = (await import("@/app/(authed)/layout")).default;
    render(
      React.createElement(
        QueryClientProvider,
        { client: makeQc() },
        React.createElement(
          AuthContext.Provider,
          { value: authValue },
          React.createElement(
            AuthedLayout,
            null,
            React.createElement("div", null, "page content"),
          ),
        ),
      ),
    );
    expect(screen.getByTestId("notification-bell")).toBeInTheDocument();
  });

  it("header contains the Settings gear button", async () => {
    const AuthedLayout = (await import("@/app/(authed)/layout")).default;
    render(
      React.createElement(
        QueryClientProvider,
        { client: makeQc() },
        React.createElement(
          AuthContext.Provider,
          { value: authValue },
          React.createElement(
            AuthedLayout,
            null,
            React.createElement("div", null, "page content"),
          ),
        ),
      ),
    );
    expect(
      screen.getByRole("button", { name: /settings/i }),
    ).toBeInTheDocument();
  });

  it("header contains the Profile avatar button", async () => {
    const AuthedLayout = (await import("@/app/(authed)/layout")).default;
    render(
      React.createElement(
        QueryClientProvider,
        { client: makeQc() },
        React.createElement(
          AuthContext.Provider,
          { value: authValue },
          React.createElement(
            AuthedLayout,
            null,
            React.createElement("div", null, "page content"),
          ),
        ),
      ),
    );
    expect(
      screen.getByRole("button", { name: /profile menu/i }),
    ).toBeInTheDocument();
  });
});

describe("UI-FIX-2E — DashboardPage Sign Out removed", () => {
  it("DashboardPage does NOT render a Sign Out button", async () => {
    // Mock out all dashboard data hooks
    vi.mock("@/features/onboarding/hooks/useTrialStatus", () => ({
      useTrialStatus: () => ({ showSoftGate: false, daysRemaining: 0 }),
    }));
    vi.mock("@/features/onboarding/hooks/useOnboardingChecklist", () => ({
      useOnboardingChecklist: () => ({ data: null }),
    }));
    vi.mock("@/features/onboarding/components/TrialExpiryBanner", () => ({
      TrialExpiryBanner: () => null,
    }));
    vi.mock(
      "@/features/onboarding/components/OnboardingChecklistWidget",
      () => ({
        OnboardingChecklistWidget: () => null,
      }),
    );
    vi.mock(
      "@/features/dashboard/components/RecentCustomerMessagesWidget",
      () => ({
        RecentCustomerMessagesWidget: () => null,
      }),
    );
    vi.mock("@/features/dashboard/components/ArSummaryWidget", () => ({
      ArSummaryWidget: () => null,
    }));
    vi.mock("@/features/dashboard/components/AtRiskJobsWidget", () => ({
      AtRiskJobsWidget: () => null,
    }));
    vi.mock("@/features/dashboard/components/PendingApprovalsWidget", () => ({
      PendingApprovalsWidget: () => null,
    }));

    const DashboardPage = (await import("@/app/(authed)/dashboard/page"))
      .default;
    render(
      React.createElement(
        QueryClientProvider,
        { client: makeQc() },
        React.createElement(
          AuthContext.Provider,
          { value: authValue },
          React.createElement(DashboardPage),
        ),
      ),
    );

    // Sign Out button should NOT be in the DOM
    expect(
      screen.queryByRole("button", { name: /sign out/i }),
    ).not.toBeInTheDocument();
    expect(screen.queryByText(/sign out/i)).not.toBeInTheDocument();
  });
});
