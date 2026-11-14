/**
 * PaymentMethodSettingsPage — Unit Tests
 *
 * Location: apps/web/src/features/settings/components/__tests__/PaymentMethodSettingsPage.test.tsx
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

import { stripeConnectHandlers } from "../../../../mocks/handlers/stripeConnectHandlers";
import { billingPaymentContactHandlers } from "../../../../mocks/handlers/billingPaymentContactHandlers";
import { PaymentMethodSettingsPage } from "../PaymentMethodSettingsPage";
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

const server = setupServer(
  ...stripeConnectHandlers,
  ...billingPaymentContactHandlers,
);
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

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("PaymentMethodSettingsPage", () => {
  it("renders without crashing — page title visible", async () => {
    renderPage("owner");
    // PLP-FIX-5: breadcrumb also contains "Payment Method" — use heading role
    expect(
      screen.getByRole("heading", { name: "Payment Method" }),
    ).toBeInTheDocument();
  });

  it("PLP-FIX-5 — breadcrumb renders with Settings link", () => {
    renderPage("owner");
    const settingsLink = screen.getByRole("link", { name: "Settings" });
    expect(settingsLink).toBeInTheDocument();
    expect(settingsLink.getAttribute("href")).toBe("/settings");
  });

  it("RBAC — tech role does NOT see the Connect Stripe Account button", async () => {
    renderPage("technician");
    // Wait for any async render
    await new Promise((r) => setTimeout(r, 50));
    expect(
      screen.queryByText("Connect Stripe Account"),
    ).not.toBeInTheDocument();
  });

  it("disconnected state — shows 'No Stripe account connected' and Connect CTA", async () => {
    // Default MSW handler returns connected: false
    renderPage("owner");

    await waitFor(() =>
      expect(
        screen.getByText("No Stripe account connected"),
      ).toBeInTheDocument(),
    );
    expect(screen.getByText("Connect Stripe Account")).toBeInTheDocument();
  });

  it("incomplete onboarding state — shows 'Setup Incomplete' badge and Resume Setup", async () => {
    server.use(
      http.get("/api/v1/settings/billing/stripe-connect/status", () =>
        HttpResponse.json({
          connected: true,
          account_id: "acct_incomplete123",
          account_name: "Acme Electric LLC",
          charges_enabled: false,
          payouts_enabled: false,
        }),
      ),
    );

    renderPage("owner");

    await waitFor(() =>
      expect(screen.getByText("Setup Incomplete")).toBeInTheDocument(),
    );
    expect(screen.getByText("Resume Setup")).toBeInTheDocument();
  });

  it("connected state — shows account name and Disconnect button", async () => {
    server.use(
      http.get("/api/v1/settings/billing/stripe-connect/status", () =>
        HttpResponse.json({
          connected: true,
          account_id: "acct_1234567890",
          account_name: "Acme Electric LLC",
          charges_enabled: true,
          payouts_enabled: true,
        }),
      ),
    );

    renderPage("owner");

    await waitFor(() =>
      expect(screen.getByText("Acme Electric LLC")).toBeInTheDocument(),
    );
    expect(screen.getByText("Connected")).toBeInTheDocument();
    expect(screen.getByText("Disconnect")).toBeInTheDocument();
  });

  it("loading state — skeleton renders while fetching", () => {
    // Intercept but delay response — skeleton should be visible immediately
    server.use(
      http.get("/api/v1/settings/billing/stripe-connect/status", async () => {
        await new Promise((r) => setTimeout(r, 500));
        return HttpResponse.json({ connected: false });
      }),
    );

    renderPage("owner");

    // While loading, Connect button is NOT yet visible
    expect(
      screen.queryByText("Connect Stripe Account"),
    ).not.toBeInTheDocument();
  });

  it("error state — shows error message when API returns 500", async () => {
    server.use(
      http.get("/api/v1/settings/billing/stripe-connect/status", () =>
        HttpResponse.json({ detail: "server error" }, { status: 500 }),
      ),
    );

    renderPage("owner");

    await waitFor(() =>
      expect(
        screen.getByText("Unable to load payment status. Refresh the page."),
      ).toBeInTheDocument(),
    );
  });

  it("?connected=true param — success banner visible", async () => {
    vi.mock("next/navigation", () => ({
      usePathname: () => "/settings/billing/payment-method",
      useSearchParams: () => new URLSearchParams("connected=true"),
      useRouter: () => ({ push: vi.fn(), back: vi.fn() }),
    }));

    // Since vi.mock is hoisted, we need a different approach for URL params
    // The component reads window.location.search on mount via lazy init
    Object.defineProperty(window, "location", {
      value: {
        ...window.location,
        search: "?connected=true",
        href: "http://localhost/settings/billing/payment-method?connected=true",
      },
      writable: true,
    });

    renderPage("owner");

    await waitFor(() =>
      expect(
        screen.getByText(/Your Stripe account has been connected/),
      ).toBeInTheDocument(),
    );
  });

  it("?retry=true param — retry banner visible", async () => {
    Object.defineProperty(window, "location", {
      value: {
        ...window.location,
        search: "?retry=true",
        href: "http://localhost/settings/billing/payment-method?retry=true",
      },
      writable: true,
    });

    renderPage("owner");

    await waitFor(() =>
      expect(
        screen.getByText(/Your previous session expired/),
      ).toBeInTheDocument(),
    );

    // Clean up
    Object.defineProperty(window, "location", {
      value: { ...window.location, search: "", href: "http://localhost/" },
      writable: true,
    });
  });

  it("Disconnect button — opens confirmation modal", async () => {
    server.use(
      http.get("/api/v1/settings/billing/stripe-connect/status", () =>
        HttpResponse.json({
          connected: true,
          account_id: "acct_1234567890",
          account_name: "Acme Electric LLC",
          charges_enabled: true,
          payouts_enabled: true,
        }),
      ),
    );

    renderPage("owner");

    await waitFor(() =>
      expect(screen.getByText("Disconnect")).toBeInTheDocument(),
    );

    fireEvent.click(screen.getByText("Disconnect"));

    expect(screen.getByText("Disconnect Stripe?")).toBeInTheDocument();
  });

  it("Disconnect modal — Cancel closes modal without firing DELETE", async () => {
    let deleteCalled = false;
    server.use(
      http.get("/api/v1/settings/billing/stripe-connect/status", () =>
        HttpResponse.json({
          connected: true,
          account_id: "acct_1234567890",
          account_name: "Acme Electric LLC",
          charges_enabled: true,
          payouts_enabled: true,
        }),
      ),
      http.delete("/api/v1/settings/billing/stripe-connect", () => {
        deleteCalled = true;
        return HttpResponse.json({
          disconnected: true,
          message: "Disconnected",
        });
      }),
    );

    renderPage("owner");

    await waitFor(() =>
      expect(screen.getByText("Disconnect")).toBeInTheDocument(),
    );

    fireEvent.click(screen.getByText("Disconnect"));
    expect(screen.getByText("Disconnect Stripe?")).toBeInTheDocument();

    // Click Cancel
    fireEvent.click(screen.getByText("Cancel"));

    expect(screen.queryByText("Disconnect Stripe?")).not.toBeInTheDocument();
    expect(deleteCalled).toBe(false);
  });

  it("Manual payment section — always visible", async () => {
    renderPage("owner");

    // Manual payment section is static — visible immediately
    expect(screen.getByText("Manual Payment Options")).toBeInTheDocument();
    expect(
      screen.getByText(/Check — mail to your business address/),
    ).toBeInTheDocument();
  });
});
