/**
 * Payment Method — Integration Tests (UI-FIX-2F)
 *
 * Location: apps/web/src/__tests__/batch_ui_fix_2f/payment_method.integration.test.tsx
 *
 * Platform: Web (Vitest + @testing-library/react + MSW)
 */

import React from "react";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
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
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import "@testing-library/jest-dom";

import { stripeConnectHandlers } from "../../mocks/handlers/stripeConnectHandlers";
import { PaymentMethodSettingsPage } from "../../features/settings/components/PaymentMethodSettingsPage";
import { AuthContext } from "@pilot/ui/auth";
import type { AuthContextValue, PilotRole } from "@pilot/ui/auth";

// ── Mocks ────────────────────────────────────────────────────────────────────

vi.mock("next/navigation", () => ({
  usePathname: () => "/settings/billing/payment-method",
  useSearchParams: () => new URLSearchParams(""),
  useRouter: () => ({ push: vi.fn(), back: vi.fn() }),
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

// ── MSW ──────────────────────────────────────────────────────────────────────

const server = setupServer(...stripeConnectHandlers);
beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

// ── Helpers ──────────────────────────────────────────────────────────────────

function makeAuthValue(role: PilotRole): AuthContextValue {
  return {
    user: {
      id: "u1",
      email: "test@example.com",
      role,
      tenantId: "t1",
      displayName: "Test User",
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

function renderPage(role: PilotRole = "owner") {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return render(
    React.createElement(
      AuthContext.Provider,
      { value: makeAuthValue(role) },
      React.createElement(
        QueryClientProvider,
        { client: queryClient },
        React.createElement(PaymentMethodSettingsPage),
      ),
    ),
  );
}

// ── Integration Tests ─────────────────────────────────────────────────────────

describe("Payment Method page — Integration (UI-FIX-2F)", () => {
  it("renders page — does NOT 404 (page title visible)", async () => {
    renderPage("owner");
    // PLP-FIX-5: breadcrumb also contains "Payment Method" — use heading role
    expect(
      screen.getByRole("heading", { name: "Payment Method" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Manage how your customers can pay/),
    ).toBeInTheDocument();
  });

  it("RBAC — owner sees status card content", async () => {
    renderPage("owner");

    await waitFor(() =>
      expect(
        screen.getByText("No Stripe account connected"),
      ).toBeInTheDocument(),
    );
  });

  it("RBAC — tech role is blocked by RoleGate (no Connect CTA)", async () => {
    renderPage("technician");
    await new Promise((r) => setTimeout(r, 100));
    expect(
      screen.queryByText("Connect Stripe Account"),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByText("No Stripe account connected"),
    ).not.toBeInTheDocument();
  });

  it("RBAC — accountant is blocked by RoleGate (read-only set — ADR-0010)", async () => {
    renderPage("accountant");
    await new Promise((r) => setTimeout(r, 100));
    expect(
      screen.queryByText("Connect Stripe Account"),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByText("No Stripe account connected"),
    ).not.toBeInTheDocument();
  });

  it("connected state renders full account display", async () => {
    server.use(
      http.get("/api/v1/settings/billing/stripe-connect/status", () =>
        HttpResponse.json({
          connected: true,
          account_id: "acct_integration_test",
          account_name: "Apex Commercial LLC",
          charges_enabled: true,
          payouts_enabled: true,
        }),
      ),
    );

    renderPage("owner");

    await waitFor(() =>
      expect(screen.getByText("Apex Commercial LLC")).toBeInTheDocument(),
    );
    expect(screen.getByText("Connected")).toBeInTheDocument();
    expect(screen.getByText("Disconnect")).toBeInTheDocument();
  });

  it("Connect button fires POST to /stripe-connect/onboard", async () => {
    let postCalled = false;
    // Default GET handler returns disconnected — Connect button is visible.
    // Only override the POST to capture it.
    server.use(
      http.post("/api/v1/settings/billing/stripe-connect/onboard", () => {
        postCalled = true;
        return HttpResponse.json({
          account_link_url: "https://connect.stripe.com/setup/s/test_redirect",
          expires_at: Math.floor(Date.now() / 1000) + 600,
        });
      }),
    );

    renderPage("owner");

    await waitFor(() =>
      expect(screen.getByText("Connect Stripe Account")).toBeInTheDocument(),
    );

    fireEvent.click(screen.getByText("Connect Stripe Account"));

    // POST should be called when button is clicked (even though redirect will fail in jsdom)
    await waitFor(() => expect(postCalled).toBe(true));
  });

  it("Disconnect modal → confirm fires DELETE to /stripe-connect", async () => {
    let deleteCalled = false;

    // Override GET to return connected state + intercept DELETE in one server.use call
    server.use(
      http.get("/api/v1/settings/billing/stripe-connect/status", () =>
        HttpResponse.json({
          connected: true,
          account_id: "acct_disconnect_test",
          account_name: "Beachside Electric",
          charges_enabled: true,
          payouts_enabled: true,
        }),
      ),
      http.delete("/api/v1/settings/billing/stripe-connect", () => {
        deleteCalled = true;
        return HttpResponse.json({
          disconnected: true,
          message: "Stripe account disconnected.",
        });
      }),
    );

    renderPage("owner");

    // Wait for connected state
    await waitFor(
      () => expect(screen.getByText("Beachside Electric")).toBeInTheDocument(),
      { timeout: 5000 },
    );

    // Open disconnect modal
    fireEvent.click(screen.getByText("Disconnect"));

    await waitFor(() =>
      expect(screen.getByText("Disconnect Stripe?")).toBeInTheDocument(),
    );

    // Confirm
    fireEvent.click(screen.getByText("Disconnect Stripe"));

    await waitFor(() => expect(deleteCalled).toBe(true));
  });
});
