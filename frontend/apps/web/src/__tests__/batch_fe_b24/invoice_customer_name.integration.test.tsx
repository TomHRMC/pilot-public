/**
 * FE-B24 — Invoice Customer Name Display Integration Tests
 *
 * Location: apps/web/src/__tests__/batch_fe_b24/invoice_customer_name.integration.test.tsx
 *
 * Tests:
 * 1. Invoice list renders customer_name not UUID string
 * 2. customer_name from MSW fixture appears in table
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
import { setupServer } from "msw/node";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthContext } from "@pilot/ui/auth";
import type { AuthContextValue } from "@pilot/ui/auth";
import { NotificationQueueProvider } from "@pilot/ui/notification-banner";
import { handlers } from "../../mocks/handlers";
import { InvoicesPage } from "@/features/invoices/components/InvoicesPage";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), back: vi.fn(), replace: vi.fn() }),
  usePathname: () => "/invoices",
  useSearchParams: () => new URLSearchParams(),
  useParams: () => ({}),
}));

const server = setupServer(...handlers);
beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

function makeQC() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
}

function makeAuth(): AuthContextValue {
  return {
    user: {
      id: "u-1",
      email: "owner@test.com",
      role: "owner",
      tenantId: "t-1",
      displayName: "Test Owner",
      accessToken: "mock-token",
    },
    isAuthenticated: true,
    role: "owner",
    signIn: vi.fn(),
    confirmMfaChallenge: vi.fn(),
    signOut: vi.fn(),
    refreshSession: vi.fn().mockResolvedValue("mock-token"),
  };
}

function renderInvoicesPage() {
  return render(
    <AuthContext.Provider value={makeAuth()}>
      <QueryClientProvider client={makeQC()}>
        <NotificationQueueProvider>
          <InvoicesPage />
        </NotificationQueueProvider>
      </QueryClientProvider>
    </AuthContext.Provider>,
  );
}

describe("FE-B24 Invoice Customer Name Display", () => {
  it("1. Invoice list renders customer_name, not truncated UUID", async () => {
    renderInvoicesPage();
    // "Smith Electric LLC" from the updated MSW fixture — findAllBy handles multiple occurrences
    const matches = await screen.findAllByText("Smith Electric LLC");
    // At least one match
    expect(matches.length).toBeGreaterThan(0);
    // UUID substring should NOT appear for items that have customer_name
    // (c-00000001 falls back to c-000000… — none should appear)
    expect(screen.queryByText(/c-000000…/)).not.toBeInTheDocument();
  });

  it("2. customer_name from MSW fixture appears in invoice table", async () => {
    renderInvoicesPage();
    // Both customer names from the MSW fixture should be visible
    const smithMatches = await screen.findAllByText("Smith Electric LLC");
    expect(smithMatches.length).toBeGreaterThan(0);
    const johnsonMatches = await screen.findAllByText("Johnson Electrical");
    expect(johnsonMatches.length).toBeGreaterThan(0);
  });
});
