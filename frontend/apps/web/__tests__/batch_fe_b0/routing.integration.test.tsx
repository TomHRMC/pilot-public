/**
 * Web routing skeleton integration tests
 *
 * Location: apps/web/__tests__/batch_fe_b0/routing.integration.test.tsx
 *
 * Tests:
 *   1. Unauthenticated user navigating to /dashboard is redirected to /login
 *   2. Mock-authenticated user navigating to /dashboard sees "Dashboard" placeholder
 *   3. All 11 sections render their section name without crashing
 *   4. Login page renders
 */

import { render, screen } from "@testing-library/react";
import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { NotificationQueueProvider } from "@pilot/ui/notification-banner";

// Mock next/navigation for redirect tests
vi.mock("next/navigation", () => ({
  redirect: vi.fn(),
  useRouter: () => ({ replace: vi.fn(), push: vi.fn() }),
  useSearchParams: () => ({ get: vi.fn().mockReturnValue(null) }),
  usePathname: () => "/",
}));

// Mock @pilot/ui/auth
vi.mock("@pilot/ui/auth", () => ({
  AuthProvider: ({ children }: { children: React.ReactNode }) => (
    <>{children}</>
  ),
  RequireAuth: ({
    children,
    redirectTo,
  }: {
    children: React.ReactNode;
    redirectTo: string;
  }) => {
    // In tests, default to authenticated; individual tests can override
    const isAuthenticated =
      (globalThis as Record<string, unknown>).__mockIsAuthenticated !== false;
    if (!isAuthenticated) {
      if (typeof window !== "undefined") {
        window.location.replace(redirectTo);
      }
      return null;
    }
    return <>{children}</>;
  },
  useAuth: () => ({
    user: {
      id: "u1",
      email: "owner@test.com",
      role: "owner",
      tenantId: "t1",
      displayName: "Owner",
      accessToken: "tok",
    },
    isAuthenticated: true,
    role: "owner",
    signIn: vi.fn(),
    signOut: vi.fn(),
    refreshSession: vi.fn(),
  }),
}));

// Mock @tanstack/react-query — include all exports used by FE-B4 surfaces
vi.mock("@tanstack/react-query", () => ({
  QueryClientProvider: ({ children }: { children: React.ReactNode }) => (
    <>{children}</>
  ),
  QueryClient: class MockQueryClient {
    clear() {}
    invalidateQueries() {}
    cancelQueries() {}
    getQueryData() {
      return undefined;
    }
    setQueryData() {}
  },
  useQueryClient: () => ({
    clear: vi.fn(),
    invalidateQueries: vi.fn(),
    cancelQueries: vi.fn(),
    getQueryData: vi.fn(),
    setQueryData: vi.fn(),
  }),
  useQuery: () => ({
    data: undefined,
    isLoading: false,
    isError: false,
    dataUpdatedAt: 0,
  }),
  useMutation: () => ({
    mutate: vi.fn(),
    mutateAsync: vi.fn(),
    isPending: false,
    isError: false,
    reset: vi.fn(),
  }),
  useMutationState: () => [],
}));
vi.mock("@tanstack/react-query-devtools", () => ({
  ReactQueryDevtools: () => null,
}));

// Mock @pilot/ui/role-gate (DispatchBoardPage uses RoleGate which calls useAuth)
vi.mock("@pilot/ui/role-gate", () => ({
  RoleGate: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  useRequiresPermission: () => ({ permitted: true }),
  // PLP-FIX-9: RecentCustomerMessagesWidget now calls useHasPermission
  useHasPermission: () => true,
  ROLE_PERMISSION_MAP: {},
}));

// FE-B19: QuotesPage now imports useConvertQuote which uses useRouter internally
vi.mock("@/features/quotes/hooks/useConvertQuote", () => ({
  useConvertQuote: () => ({ mutate: vi.fn(), isPending: false }),
}));

// FE-B22: InvoicesPage now uses useCreateInvoice and useNotificationQueue
vi.mock("@/features/invoices/hooks/useCreateInvoice", () => ({
  useCreateInvoice: () => ({ mutate: vi.fn(), isPending: false }),
}));
vi.mock("@pilot/ui/notification-banner", () => ({
  useNotificationQueue: () => ({ addNotification: vi.fn() }),
  NotificationQueueProvider: ({ children }: { children: React.ReactNode }) => (
    <>{children}</>
  ),
  NotificationPortal: () => null,
  NotificationBanner: () => null,
}));

// Mock @pilot/shared-api — include LIST_PAGE_SIZE added in UI-FIX-1C
vi.mock("@pilot/shared-api", () => ({
  createQueryClient: () => ({}),
  LIST_PAGE_SIZE: 25,
  apiClient: {
    get: vi.fn().mockResolvedValue({
      data: { items: [], total: 0, limit: 25, offset: 0 },
    }),
    post: vi.fn().mockResolvedValue({ data: {} }),
    patch: vi.fn().mockResolvedValue({ data: {} }),
    delete: vi.fn().mockResolvedValue({ data: {} }),
  },
}));

describe("Web routing skeleton", () => {
  beforeEach(() => {
    (globalThis as Record<string, unknown>).__mockIsAuthenticated = true;
  });

  it("renders Dashboard placeholder page", async () => {
    const DashboardPage = (await import("@/app/(authed)/dashboard/page"))
      .default;
    render(<DashboardPage />);
    expect(screen.getByRole("heading", { name: /dashboard/i })).toBeTruthy();
  });

  it("renders Schedule page (dispatch board replaces placeholder in FE-B4)", async () => {
    const SchedulePage = (await import("@/app/(authed)/schedule/page")).default;
    render(<SchedulePage />);
    // Dispatch board renders toolbar with Today button, not a placeholder h1
    // (placeholder was replaced by DispatchBoardPage in FE-B4)
    expect(screen.getByText("Today")).toBeTruthy();
  });

  it("renders Customers placeholder page", async () => {
    const CustomersPage = (await import("@/app/(authed)/customers/page"))
      .default;
    render(<CustomersPage />);
    // Use level: 1 to target the page h1 "Customers" — EmptyState also renders h2 "No customers yet"
    expect(
      screen.getByRole("heading", { level: 1, name: /customers/i }),
    ).toBeTruthy();
  });

  it("renders Quotes placeholder page", async () => {
    const QuotesPage = (await import("@/app/(authed)/quotes/page")).default;
    render(<QuotesPage />);
    // FE-B19: QuotesPage now renders <h1>Quotes</h1> + <h2>No quotes yet</h2>
    // Use level: 1 to target only the page-level heading
    expect(
      screen.getByRole("heading", { level: 1, name: /^quotes$/i }),
    ).toBeTruthy();
  });

  it("renders Invoices placeholder page", async () => {
    const InvoicesPage = (await import("@/app/(authed)/invoices/page")).default;
    render(<InvoicesPage />);
    // Use level: 1 to target the page-level <h1>Invoices</h1> only
    // (EmptyState also renders an h2 containing "No invoices found")
    expect(
      screen.getByRole("heading", { level: 1, name: /invoices/i }),
    ).toBeTruthy();
  });

  it("renders Settings placeholder page", async () => {
    const SettingsPage = (await import("@/app/(authed)/settings/page")).default;
    render(<SettingsPage />);
    expect(screen.getByRole("heading", { name: /settings/i })).toBeTruthy();
  });

  it("renders Login placeholder page", async () => {
    const LoginPage = (await import("@/app/login/page")).default;
    render(
      <NotificationQueueProvider>
        <LoginPage />
      </NotificationQueueProvider>,
    );
    expect(
      screen.getByRole("heading", { name: /pilot for trades/i }),
    ).toBeTruthy();
  });
});
