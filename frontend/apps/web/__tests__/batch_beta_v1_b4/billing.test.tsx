/**
 * Billing Settings Page Integration Tests — BETA-B4
 *
 * Location: apps/web/__tests__/batch_beta_v1_b4/billing.test.tsx
 * Route: /settings/billing
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
import { render, screen, waitFor } from "@testing-library/react";
import "@testing-library/jest-dom";
import React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { setupServer } from "msw/node";
import { NotificationQueueProvider } from "@pilot/ui/notification-banner";
import { handlers } from "../../src/mocks/handlers";
import { BillingSettingsPage } from "../../src/features/settings/components/BillingSettingsPage";

vi.mock("@pilot/ui/role-gate", () => ({
  RoleGate: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  useRequiresPermission: () => true,
}));

vi.mock("@pilot/ui/auth", () => ({
  useAuth: () => ({
    user: { id: "user-1", email: "owner@test.com", tenantId: "tenant-1" },
    role: "owner",
    isAuthenticated: true,
    signIn: vi.fn(),
    signOut: vi.fn(),
    refreshSession: vi.fn(),
  }),
}));

const server = setupServer(...handlers);

beforeAll(() => server.listen({ onUnhandledRequest: "bypass" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

function makeWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <NotificationQueueProvider>{children}</NotificationQueueProvider>
      </QueryClientProvider>
    );
  };
}

describe("BillingSettingsPage (/settings/billing)", () => {
  it("renders without crashing (not 404)", () => {
    const { container } = render(<BillingSettingsPage />, {
      wrapper: makeWrapper(),
    });
    expect(container).toBeDefined();
  });

  it("shows Billing & Subscription heading", async () => {
    render(<BillingSettingsPage />, { wrapper: makeWrapper() });
    await waitFor(() => {
      // PLP-FIX-5: breadcrumb also contains "Billing & Subscription" — use heading role
      expect(
        screen.getByRole("heading", { name: "Billing & Subscription" }),
      ).toBeDefined();
    });
  });

  it("shows current plan name from MSW fixture (Starter)", async () => {
    render(<BillingSettingsPage />, { wrapper: makeWrapper() });
    await waitFor(() => {
      expect(screen.getByText("Starter")).toBeDefined();
    });
  });

  it("shows trial banner when is_trial=true", async () => {
    render(<BillingSettingsPage />, { wrapper: makeWrapper() });
    await waitFor(() => {
      expect(screen.getByText(/Trial ends/i)).toBeDefined();
    });
  });

  it("shows payment method referral section with link to /settings/billing/payment-method", async () => {
    render(<BillingSettingsPage />, { wrapper: makeWrapper() });
    await waitFor(() => {
      // UI-FIX-2F: placeholder removed — now a link to dedicated payment-method route
      expect(screen.getByText("Payment Method")).toBeDefined();
      expect(screen.getByText("Payment Method settings →")).toBeDefined();
    });
  });
});
