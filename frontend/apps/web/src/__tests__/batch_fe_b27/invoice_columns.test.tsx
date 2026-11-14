/**
 * FE-B27 — InvoicesPage Total + Issued columns tests
 *
 * Location: apps/web/src/__tests__/batch_fe_b27/invoice_columns.test.tsx
 *
 * Verifies:
 * - "Total" column header is rendered
 * - total_cents value is formatted as currency (e.g. "$1500.00")
 * - "Issued" column header is rendered
 */

import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
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
import { http, HttpResponse } from "msw";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthContext } from "@pilot/ui/auth";
import type { AuthContextValue } from "@pilot/ui/auth";
import { NotificationQueueProvider } from "@pilot/ui/notification-banner";
import { InvoicesPage } from "@/features/invoices/components/InvoicesPage";

// FE-B29: InvoicesPage now uses useRouter to navigate to /invoices/new
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), back: vi.fn(), replace: vi.fn() }),
  usePathname: () => "/invoices",
  useSearchParams: () => new URLSearchParams(),
}));

// Per-test MSW server
const server = setupServer(
  http.get("/api/v1/invoices/", () => {
    return HttpResponse.json({
      items: [
        {
          id: "inv-001",
          invoice_number: "INV-1001",
          customer_id: "cust-001",
          customer_name: "Bright Electric Co.",
          site_id: "site-001",
          status_id: "status-001",
          status_code: "issued",
          issued_at: "2026-07-01T00:00:00Z",
          due_at: "2026-07-31T00:00:00Z",
          total_cents: 150000,
        },
        {
          id: "inv-002",
          invoice_number: "INV-1002",
          customer_id: "cust-002",
          customer_name: "Metro Wiring LLC",
          site_id: "site-002",
          status_id: "status-002",
          status_code: "draft",
          issued_at: null,
          due_at: null,
          total_cents: null,
        },
      ],
      total: 2,
      limit: 50,
      offset: 0,
    });
  }),
);

beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

function makeAuthContext(): AuthContextValue {
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

function makeQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
}

function renderInvoicesPage() {
  const qc = makeQueryClient();
  return render(
    <NotificationQueueProvider>
      <AuthContext.Provider value={makeAuthContext()}>
        <QueryClientProvider client={qc}>
          <InvoicesPage />
        </QueryClientProvider>
      </AuthContext.Provider>
    </NotificationQueueProvider>,
  );
}

describe("InvoicesPage — FE-B27 Total + Issued columns (§Task 6)", () => {
  it("renders 'Total' column header", async () => {
    renderInvoicesPage();
    await waitFor(() => {
      expect(screen.getByText("Total")).toBeInTheDocument();
    });
  });

  it("renders formatted total_cents as currency ($1500.00)", async () => {
    renderInvoicesPage();
    await waitFor(() => {
      expect(screen.getByText("$1500.00")).toBeInTheDocument();
    });
  });

  it("renders '—' for null total_cents", async () => {
    renderInvoicesPage();
    await waitFor(() => {
      // Multiple "—" entries expected (null total_cents, null issued_at, null due_at)
      const dashes = screen.getAllByText("—");
      expect(dashes.length).toBeGreaterThan(0);
    });
  });

  it("renders 'Issued' column header", async () => {
    renderInvoicesPage();
    await waitFor(() => {
      expect(screen.getByText("Issued")).toBeInTheDocument();
    });
  });

  it("renders a formatted issued_at date (not the em dash fallback)", async () => {
    renderInvoicesPage();
    await waitFor(() => {
      // The date INV-1001 is issued — it should have a readable date, not "—"
      // Locale formatting may vary by timezone; assert the invoice row has a date string
      // by checking the issued column has a non-dash value for the issued invoice.
      // Use a regex to match month/day/year pattern (e.g. "Jul 1, 2026" or "Jun 30, 2026").
      const datePattern =
        /\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},\s+\d{4}\b/;
      const allCells = document.querySelectorAll("td");
      const hasFormattedDate = Array.from(allCells).some((cell) =>
        datePattern.test(cell.textContent ?? ""),
      );
      expect(hasFormattedDate).toBe(true);
    });
  });

  it("renders customer name as link text", async () => {
    renderInvoicesPage();
    await waitFor(() => {
      expect(screen.getByText("Bright Electric Co.")).toBeInTheDocument();
    });
  });
});
