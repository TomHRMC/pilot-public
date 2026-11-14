/**
 * Pending quotes inbox integration tests
 *
 * Location: apps/web/__tests__/batch_fe_b5/pending-quotes-inbox.integration.test.tsx
 *
 * Updated to match real API: GET /api/v1/quotes?status=pending_approval
 * returns QuoteListItem[] (plain array, not {items, total} wrapper).
 * Client-side filtering applied in usePendingQuotes.
 */

import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import React from "react";
import {
  describe,
  it,
  expect,
  beforeAll,
  afterEach,
  afterAll,
  vi,
} from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { PendingQuotesInboxPage } from "@/features/quote-approval/PendingQuotesInboxPage";
import { AuthContext } from "@pilot/ui/auth";
import type { AuthContextValue } from "@pilot/ui/auth";

const PENDING_QUOTES = [
  {
    id: "q1",
    quote_number: "Q-001",
    title: "Panel Upgrade",
    status_code: "pending_approval",
    customer_id: "c1",
    customer_name: "Johnson Electric",
    total_cents: 450000,
    subtotal_cents: 420000,
    tax_cents: 30000,
  },
  {
    id: "q2",
    quote_number: "Q-002",
    title: "Wiring Repair",
    status_code: "pending_approval",
    customer_id: "c2",
    customer_name: "Riverside Condos",
    total_cents: 1250000,
    subtotal_cents: 1200000,
    tax_cents: 50000,
  },
  {
    id: "q3",
    quote_number: "Q-003",
    title: null,
    status_code: "pending_approval",
    customer_id: "c3",
    customer_name: "Oak Street Apartments",
    total_cents: 180000,
    subtotal_cents: 170000,
    tax_cents: 10000,
  },
];

const server = setupServer(
  // Real endpoint: GET /api/v1/quotes?status=pending_approval → plain array
  http.get("/api/v1/quotes", ({ request }) => {
    const url = new URL(request.url);
    const status = url.searchParams.get("status");
    if (status === "pending_approval") {
      return HttpResponse.json(PENDING_QUOTES);
    }
    return HttpResponse.json([]);
  }),
);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

function ownerContext(): AuthContextValue {
  return {
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
    confirmMfaChallenge: vi.fn(),
    signOut: vi.fn(),
    refreshSession: vi.fn().mockResolvedValue("tok"),
  };
}

function techContext(): AuthContextValue {
  return {
    user: {
      id: "u2",
      email: "tech@test.com",
      role: "technician",
      tenantId: "t1",
      displayName: "Tech",
      accessToken: "tok",
    },
    isAuthenticated: true,
    role: "technician",
    signIn: vi.fn(),
    confirmMfaChallenge: vi.fn(),
    signOut: vi.fn(),
    refreshSession: vi.fn().mockResolvedValue("tok"),
  };
}

function renderWithOwner() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <AuthContext.Provider value={ownerContext()}>
      <QueryClientProvider client={qc}>
        <PendingQuotesInboxPage />
      </QueryClientProvider>
    </AuthContext.Provider>,
  );
}

describe("PendingQuotesInboxPage integration", () => {
  it("owner loads inbox and sees 3 pending quote cards", async () => {
    renderWithOwner();
    await waitFor(() => {
      expect(screen.getByText("Johnson Electric")).toBeTruthy();
      expect(screen.getByText("Riverside Condos")).toBeTruthy();
      expect(screen.getByText("Oak Street Apartments")).toBeTruthy();
    });
  });

  it("shows empty state when no quotes returned", async () => {
    server.use(http.get("/api/v1/quotes", () => HttpResponse.json([])));
    renderWithOwner();
    await waitFor(() => {
      expect(screen.getByTestId("pending-quotes-empty")).toBeTruthy();
    });
  });

  it("tech role sees permission-denied empty state", async () => {
    const qc = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    render(
      <AuthContext.Provider value={techContext()}>
        <QueryClientProvider client={qc}>
          <PendingQuotesInboxPage />
        </QueryClientProvider>
      </AuthContext.Provider>,
    );
    await waitFor(() => {
      expect(screen.getByText(/access restricted/i)).toBeTruthy();
    });
  });

  it("filter by customer search updates display (client-side)", async () => {
    renderWithOwner();
    await waitFor(() =>
      expect(screen.getByText("Johnson Electric")).toBeTruthy(),
    );

    const searchInput = screen.getByLabelText(/search by customer name/i);
    fireEvent.change(searchInput, { target: { value: "Johnson" } });

    await waitFor(() => {
      expect(screen.queryByText("Riverside Condos")).toBeNull();
      expect(screen.getByText("Johnson Electric")).toBeTruthy();
    });
  });
});
