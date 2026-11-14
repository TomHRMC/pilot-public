/**
 * Payment Method Settings — Integration Tests — STRIPE-CONNECT-1-C
 *
 * Location: apps/web/src/__tests__/batch_stripe_connect_1_c/payment-method-settings.integration.test.tsx
 *
 * - Page renders the payment-contact form hydrated from the GET handler
 * - Editing + saving fires the PATCH (assert URL/method/payload)
 * - payouts_enabled: false status override renders the warning chip
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
import { billingPaymentContactHandlers } from "../../mocks/handlers/billingPaymentContactHandlers";
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

// ── Tests ────────────────────────────────────────────────────────────────────

describe("STRIPE-CONNECT-1-C — Payment Method Settings", () => {
  it("renders the billing-contact form hydrated from the GET handler", async () => {
    renderPage("owner");

    const phoneInput = await screen.findByTestId("billing-contact-phone-input");
    const emailInput = screen.getByTestId("billing-contact-email-input");

    await waitFor(() => {
      expect(phoneInput).toHaveValue("(804) 555-0142");
    });
    expect(emailInput).toHaveValue("billing@example.com");
  });

  it("editing + saving fires the PATCH with correct payload", async () => {
    let capturedBody: Record<string, unknown> | null = null;

    server.use(
      http.patch(
        "/api/v1/settings/billing/payment-contact",
        async ({ request }) => {
          capturedBody = (await request.json()) as Record<string, unknown>;
          return HttpResponse.json({
            billing_contact_phone: capturedBody!.billing_contact_phone,
            billing_contact_email: capturedBody!.billing_contact_email,
          });
        },
      ),
    );

    renderPage("owner");

    const phoneInput = await screen.findByTestId("billing-contact-phone-input");

    // PhoneInput normalizes to E.164 (PLP-FIX-4)
    fireEvent.change(phoneInput, { target: { value: "(555) 999-0000" } });
    fireEvent.click(screen.getByTestId("billing-contact-save-button"));

    await waitFor(() => {
      expect(capturedBody).not.toBeNull();
    });

    expect(capturedBody!.billing_contact_phone).toBe("+15559990000");
    expect(capturedBody!.billing_contact_email).toBe("billing@example.com");
  });

  it("payouts_enabled: false status override renders the warning chip", async () => {
    server.use(
      http.get("/api/v1/settings/billing/stripe-connect/status", () =>
        HttpResponse.json({
          connected: true,
          account_id: "acct_1234567890",
          account_name: "Acme Electric LLC",
          charges_enabled: true,
          payouts_enabled: false,
        }),
      ),
    );

    renderPage("owner");

    await waitFor(() => {
      expect(
        screen.getByTestId("payouts-disabled-warning"),
      ).toBeInTheDocument();
    });

    expect(
      screen.getByText(/payouts are disabled by Stripe/),
    ).toBeInTheDocument();
  });

  it("payouts_enabled: true does NOT render the warning chip", async () => {
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

    await waitFor(() => {
      expect(screen.getByText("Connected")).toBeInTheDocument();
    });

    expect(
      screen.queryByTestId("payouts-disabled-warning"),
    ).not.toBeInTheDocument();
  });
});
